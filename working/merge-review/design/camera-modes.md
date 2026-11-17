# Camera modes and limits: work with the original driver too: design

Read at: Core `/home/user/wt/core-work` `0d13a6f`, UI `/home/user/wt/ui-work` `ac1fc28`, imx585 driver `cinemate-port` `cd548ef` (baseline `origin/apertar` `e5b74d3`), imx283 driver `cinemate-port` `68b7dc9`, upstream `35dbe67` / `43888e5`, fork main `f60e301`, libcamera `apertar` `6b0b49f`. Refs below: `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `App` = `src/ApertarCoreApp.cpp`, `CCH` = `src/camera/CameraController.hpp`; no ref = `@0d13a6f`. This is the final plan: the first design and its challenge were checked against the code and merged; the last section says what the challenge changed.

## In short

1. Today the port Core works only with the cinemate-port imx585 driver. It rewrites 3840x2076 / 1920x1038 to 2072 / 1036 everywhere, has no auto sensor-config fallback for colour IMX585, and (**probable**) refuses every 2x2 binned mode of the original driver, 1920x1080 included, because that driver reports its crop in binned pixels (`CC:8510-8521`; `imx585.c:803-808,2379-2381@e5b74d3`).
2. The fps ceiling is the probe alone, and lossless cDNG lost 1.6.0's ISO 800, manual ISO and IMX585 30 fps. A stock camera offers and records more than 1.6.0 did.
3. Three port mechanisms have their own shape where upstream has one: a second settings file for the ladder, a second JSON parser for the TDN strip, a session-wide request-release callback.
4. Target: Core decides at run time from the startup probe. The 1.85:1 row is whichever height the driver has in that class. Nothing is rewritten on load. Defaults are fork main's `min(table, probe)` and 1.6.0's lossless limits on every driver. The owner's rig gets today's limits back with four bench knobs (R8).
5. The ladder moves into `camera_settings.conf` as camera-wide keys (the `tuning_file` shape). `mode_ladder.conf` is read only while those keys are absent. The TDN strip becomes a libyaml function beside `makeProresIspTuning`. The DNG copy worker gets per-frame closures, like the ProRes and H.264 recorders.
6. Drivers: the imx585 driver advertises 3840x2076 / 1920x1038 again in its 12-bit and 10-bit tables, at crop top 40 (owner decision 2). The imx283 driver defaults `crop_vmax` to 0.
7. 13 Core commits and 2 driver commits. Most remove more lines than they add (about -870 / +310 in total).

## How it works in the port today

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| IMX585 mode tables S12/S10/H12/H16 (62/62/28/34 rows; H12 lost binned 1080 in `a36c52f`) | by hand, `src/camera/Imx585Modes.hpp:40-98` | probe `CC:7171-7176`; `imx585ModeForResolution` `CC:512-518` (mode selection `CC:2671`, normaliser `CC:2832`); `setResolution` class check `CC:10661-10667`; exact-mode check `CC:8513-8521`; ladder pool `CC:11005-11020` | constexpr, no lock | none | WebUI hand copy `WCP:8915-8920` (fallback); touch UI keeps the 1.6.0 lists (`ui-work qml/CameraPage.qml:418`, `qml/SettingsPage.qml:161`) |
| 1.85:1 rewrite `migratedImx585CropResolution` 2076->2072, 1038->1036 | `clampCaptureSettings` `CC:703` (every load, every persist `CC:1016`), `setResolution` `CC:10650`, presets `CC:12665`, ladder load `CC:10516`, `setModeLadder` `CC:11062` | every later lookup | command thread under `mutex_`; persister thread at `CC:1016` | `camera_settings.conf` and `mode_ladder.conf` get the new size at the next save | `width`/`height` in state; WebUI alias `WCP:9091`; WebUI sends 1036/2072 for both labels `WCP:9383-9384`, `9399-9400` |
| Startup probe `probedSensorModes` | `probeSensorModesOnce` `CC:7231-7244`, called in the first `CameraSession::start` `CC:7334`, before the session's sanitise `CC:7445`; IMX585 is probed by table rows only, found by a `properties::Model` substring `CC:7152-7176` | `probedMaximumFps` `CC:3313-3322`; `sensorModes()` `CC:12610` -> `list_sensor_modes` `App:12741`, ladder pool `CC:11005-11033` | configure thread; `probedSensorModesMutex` (file-scope `CC:3307`), taken under `mutex_` by the sanitiser | none (journal `ApertarCore sensor mode:`) | WebUI pills through the ladder pool `WCP:8955-8960` |
| Auto sensor-config fallback | `allowAutoSensorConfigFallback` `CC:8297-8298`: mono, IMX294, IMX577 only | configure loop `CC:8313-8317` | configure, `mutex_` | none | journal rejection log |
| Readout checks after `configure()` | IMX477/577/294 size rule `CC:8464-8483` (upstream's); colour IMX585 exact-mode check `CC:8485-8530` (raw size, bit depth, `ScalerCropMaximum` = active x binning), explicit and auto alike | same loop | configure, `mutex_` | none | journal `adjusted by the driver (...)` |
| Sensor fps ceiling | `maximumSupportedFpsForResolution` `CC:3411-3423` -> `fpsceiling::resolveSensorMaxFps` (`src/camera/FpsCeiling.hpp:14-19`): probe alone; `APERTAR_FPS_LIMIT=table` `CC:3398-3408` and `APERTAR_IMX283_PROBE_FPS` `CC:3391-3395` read once; dead `backendMaximumFps` `CC:3426-3434` wrapped at `CC:3470`, `CC:3488-3490`, `CC:8641` | sanitiser, configure clamp, `fps_max`, storage pre-roll `CC:3486-3491` | `mutex_` | sanitised fps is saved | `fps_max`; WebUI and touch UI fps lists |
| Lossless cDNG limits | `enforceLosslessCaptureLimits` `CC:3146-3157`: `kLosslessMaxIso = 1600` `CC:3100`, auto ISO kept on IMX585, IMX585 fps = mode max unless `APERTAR_LOSSLESS_FPS_LIMIT` (`CC:3115-3142`, `FpsCeiling.hpp:27-45`) | sanitiser; `iso_max` `CC:3161-3167` | `mutex_` | sanitised ISO and fps are saved | `iso_max`, `fps_max`; WebUI comment `WCP:7504-7505` |
| Mode ladder (enabled, ramp_ready, resolutions) | `setModeLadder` `CC:11047-11104` -> `saveModeLadderLocked` `CC:10941-10947`: synchronous `atomicWrite` under `mutex_`; path `modeLadderPath` `CC:404-415` (a copy of `persistedSettingsPath` `CC:417-428`); parsed in the constructor `CC:10511-10517`, before any probe | `modeLadder_` (`CCH:248`): `ladderStatesLocked` `CC:10831-10852`, `ladderActiveForLocked` `CC:10856-10860`, `ladderRewriteLocked` `CC:10864-10889`, `fillLadderFieldsLocked` `CC:10893-10938` | command thread, `mutex_` | `~/.config/apertar-core/mode_ladder.conf` (header line carries "T34", `src/camera/ModeLadder.hpp:317-323`) | `ladder_*` state fields; WebUI Modes card via `get_mode_ladder` |
| Preview tuning without TDN | `loadablePath` `CC:7311-7321` -> `tuning::previewTuningPath` (`src/camera/TuningTdnStrip.hpp`, 451 lines: own recursive JSON parser, own temp+rename writer, `.src` sidecar) | libcamera via `applyProcessTuningFile` | configure thread, `mutex_` | `$HOME/.cache/apertar-core/tuning/<stem>_notdn.json` + `.src` (`README.md:323`) | journal `preview_tdn=off active=...` `CC:7437-7442` |
| DNG request release | `recorder_.setRequestRelease(...)` set once after `makeRequests` `CC:8733-8738` (shared `sessionSettingsMutex_`, `running_` check, `requeueRequest`); hold limit buffers-2 passed with it; `PendingCopy.request` `CC:5032` | copy worker `releaseHeldRequest` `CC:5151-5162` (also decrements `heldRequests_`), stop loop `CC:5176-5183`; `enqueueCopy` refuses without the callback `CC:5070` | completion thread enqueues, copy worker releases; `copyMutex_` | none | none |
| Audio follows written frames | `recorder_.setFrameQueued(...)` `CC:8739-8741` | copy worker after the write queue took the frame `CC:5139-5147` | copy worker, `copyMutex_` | none | WAV length |
| imx585 driver 1.85:1 size | `imx585.c:867`, `:918`, `:1121-1127`, `:1408-1414`, `:2168-2174`, `:2423-2429` @cd548ef: 3840x2072, 1920x1036, crop top 44. The Clear HDR 12-bit list is a range of the same `supported_modes[]` (`imx585.c:3083-3094`), so it holds the 3840x2072 row too. RAW16 1.85:1 is transport 3840x2112, window 2072 (`imx585.c:1766-1773`) | libcamera, Core probe | - | - | `APERTAR.md:145-157` tells users to move saved sizes |
| imx283 `crop_vmax` | `imx283.c:277` @68b7dc9 default true (unmeasured per-crop VMAX floors) | `imx283.c:2430` | - | `/etc/modprobe.d/imx283.conf` (by hand, `APERTAR.md:92-113`) | Core caps at the crop_vmax=0 floor `CC:3333-3337` unless `APERTAR_IMX283_PROBE_FPS=1` |

What the two drivers report (confirmed in code):

| | Original driver `e5b74d3` | cinemate-port driver `cd548ef` |
| --- | --- | --- |
| 1.85:1 | 3840x2076, 1920x1038 binned (`imx585.c:591`, `:817`) | 3840x2072, 1920x1036 binned; Clear HDR 12-bit 3840x2072 |
| Binned crop rectangle (`V4L2_SEL_TGT_CROP` -> `ScalerCropMaximum`, `pipeline_base.cpp:568@6b0b49f`) | the output size: 1920x1080 at (0,0) for 1080 (`imx585.c:803-808`, `:2379-2381`) | native pixels: 3840x2160 |
| Port Core exact-mode check `CC:8513-8521` | wants 3840x2160 for a binned row, gets 1920x1080: **refused** (probable; journal settles it) | passes |
| Other sizes | 1920x1080, 1920 crops (binned), 3840x2160, 3840 crops, 16-bit Clear HDR 3840x2200 | the 4 class tables of `Imx585Modes.hpp` |

## How original Apertar does this kind of thing

| Kind of problem | Precedent | What it says |
| --- | --- | --- |
| A size a client sends that the sensor names differently | `isImx585LowResolutionAlias` `CC:360-364@upstream-1.6.0`; `normalizedResolutionForSensor` `CC:2372-2421@upstream-1.6.0` | The request is mapped to the sensor's size in the per-sensor normaliser, at use. The saved value is never rewritten on load |
| Retiring a saved size | `normalizedImx294ResolutionForBitDepth` `CC:511-532@upstream-1.6.0` | Done in the sensor's normaliser, so other sensors keep the size |
| The driver may lack an explicit mode | `allowAutoSensorConfigFallback` `CC:5993-5996@upstream-1.6.0`, loop `CC:6012-6017` | Explicit sensorConfig first, then auto for mono, IMX294, IMX577 and IMX585 raw12 crops; Core crops in software |
| What the auto config may hand back | `invalidReadout` `CC:6162-6183@upstream-1.6.0` | IMX477/577: same width, height at least the requested height. IMX294: exact. Anything else is refused and the next candidate is tried |
| A client sends the size it shows | `resolutionCommandPayload` `WCP:5467-5468`, `5483-5484@upstream-1.6.0` | Each pill sends its own label |
| Limits found at run time | 1.6.0: none, the table alone (`CC:2629-2681@upstream-1.6.0`). Fork main (merge target): `probed ? std::min(table, *probed) : table` (`CC:2763-2769@f60e301`), commit text "SDR limits unchanged (the probe only lowers them)" | The probe only lowers the hard-coded table. This is fork main's rule, not 1.6.0's |
| Product limits | `enforceLosslessCaptureLimits` `CC:2470-2491@upstream-1.6.0` (ISO 800, `isoAuto = false`, IMX585 30) | Limits are code; `validate()` has the last word |
| Bench knobs | `unsignedEnvValue` / `boolEnvValue` `CC:1027-1061@upstream-1.6.0`, used at `CC:1127`, `CC:1133` | `APERTAR_<AREA>_<KNOB>`, read at use, bounded, default in code, echoed on the take-start line (R8, CAM-24) |
| A camera-wide setting | `tuning_file`: field, loader key, writer line, carried across format profiles `CC:7939-7955@upstream-1.6.0`; debounced persister `CC:742-889@upstream-1.6.0` | One file, written only by Core through the persister (CAM-40) |
| A setter with no stream change | `setTuningFile` no-session branch `CC:8076-8083@upstream-1.6.0` | `settings_ = next; persistSettingsLocked(); emitSettingsEventLocked();` without `applySettingsLocked` |
| Taking over an old value | Same file: `wb_locked` `CC:681-682`, `:727@upstream-1.6.0`. Old location: `SettingsBridge::presetsDirectoryPath` (`ui-upstream src/SettingsBridge.cpp:1937-1958`) reads `~/.config/CinePi/UI/presets` while the new folder is missing; `DefaultTuningSelection.hpp:74@upstream-1.6.0` keeps the old tuning folder "during migration" | The loader reads the retired form and turns it into today's; the old place is read only while the new one is empty. Core itself never reads a second file for a take-over |
| A derived tuning file | `makeProresIspTuning` `src/color/ProresIspProfile.cpp:72-90`, `:221-236@upstream-1.6.0` | libyaml node lookup, byte-range `Edit`s back to front, `$HOME/.cache/apertar-prores/`, written only when changed with `settingsFile::atomicWrite` |
| A recorder holds a camera buffer and gives it back | ProRes `CC:7419-7425@upstream-1.6.0`; H.264 `CC:7456-7465@upstream-1.6.0`; `PreviewJob::release` `CC:3937@upstream-1.6.0`; audio observed after the hand-over `CC:7428-7430@upstream-1.6.0` | One `std::function<void()>` per frame; the recorder never sees a `libcamera::Request` |
| Pure logic in a header | CAM-4: `src/camera/StillBracketing.hpp:8-19@upstream-1.6.0` | `inline` free functions, std only, one includer |
| A list the WebUI fetches once | `state.presetLibrary` `WCP:7439@upstream-1.6.0` | Fetched lists live in `state`; resolution lists are hand-written per sensor |
| An unvalidated driver feature | `experimental_modes` default off, `imx283.c:269` (same driver) | Opt-in module parameter |
| A mode the driver offers | R6 point 1: "The driver must offer the mode; Core installs no driver" | Sizes are documented with the driver, not in Core's README |

## The target

Who owns what:

- **The probe owns "what this driver has".** It runs once in the first session start (`CC:7334`), on every driver. It tries every table row of the class, and the tables now hold both 1.85:1 heights. Each row the driver accepts is kept. The first configure is sanitised after the probe (`CC:7445`), so the first start already sees it.
- **`CameraController` owns the mapping.** A pure function in `Imx585Modes.hpp` turns a 1.85:1 request into the height of the pair that the probe found in that class. Without a probe it keeps the request if the class has it. `imx585ModeForResolution` (the sanitiser's IMX585 step), `setResolution`'s class check and the ladder's rung step call it. It is the upstream alias shape (`isImx585LowResolutionAlias`), applied at use. Saved files keep what the operator chose until the next save writes the effective value, as for every other sanitised field.
- **Code owns the limits.** `min(table, probe)` (fork main) and 1.6.0's lossless limits apply on every driver. A driver does not say whether the storage path or the encoder keeps up. The owner's rig raises the limits with bench knobs in the Core unit's environment. Where that environment lives belongs to the storage-settings theme.
- **`camera_settings.conf` owns the ladder**, as three camera-wide keys, written by the persister and carried across format profiles like `tuning_file`. `setModeLadder` keeps its two paths: a mode change goes through `applySettingsLocked`, a ladder edit alone persists and sends the settings event (the `setTuningFile` shape).

| Item | Before (port) | After | Set by | Reaches |
| --- | --- | --- | --- | --- |
| 1.85:1 size | rewritten to 2072/1036 on load, save, set, preset, ladder | the height the probe found in the class (2072 or 2076; 1036 or 1038); the request unchanged if the probe did not run and the class has it | `set_resolution`, presets, ladder rungs | `width`/`height` in state (fields unchanged); WebUI alias entries removed |
| WebUI 1.85:1 pills | send 2072/1036 for both labels; fallback lists 2072/1036 | each pill sends its label (1.6.0); fallback lists 2076/1038 | - | `set_resolution` |
| IMX585 rows | 4 tables copied from one driver | plus `3840x2076` and `1920x1038b` in S12 and S10, `3840x2076` in H12; the probe keeps what the driver accepts | code | `list_sensor_modes` (adds `active_width`, `active_height`) -> WebUI pills |
| Readout check | every colour config; crop must be native-pixel | explicit: as today, but no crop comparison when the driver's crop equals the output size; auto (colour): upstream's IMX477/577 rule | - | journal |
| Auto fallback | none for colour IMX585 | upstream clause back: IMX585 3840-wide crops | - | journal |
| fps ceiling | probe alone; `APERTAR_FPS_LIMIT=table`; `APERTAR_IMX283_PROBE_FPS` | `min(table, probe)`; `APERTAR_FPS_LIMIT=probe` = probe alone (every sensor) | env, read at use, on the `recording clip:` line | `fps_max` |
| Lossless ISO / auto ISO / IMX585 fps | 1600 / kept on IMX585 / mode max | 800 / off / 30; `APERTAR_LOSSLESS_MAX_ISO`, `APERTAR_LOSSLESS_AUTO_ISO=1`, `APERTAR_LOSSLESS_FPS_LIMIT` raise them (fps within the mode maximum) | env, read at use, on the `recording clip:` line | `iso_max`, `fps_max`, `iso`, `iso_auto` |
| Mode ladder | `mode_ladder.conf`, own writer, synchronous under `mutex_` | keys `mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_resolutions` in every block of `camera_settings.conf`; `mode_ladder.conf` read by the loader only while none of the keys is there; `modeLadder_` stays, set where the keys are written | `set_mode_ladder` | `ladder_*` fields and `get_mode_ladder` unchanged |
| Preview tuning without TDN | `TuningTdnStrip.hpp`, own parser, own writer, sidecar | `makePreviewTuning(source, destination, error)` in `src/color/ProresIspProfile.cpp`; `$HOME/.cache/apertar-prores/<stem>_notdn.json`, written only when changed | `set_preview_tdn` (unchanged) | journal line unchanged |
| DNG request release | set-once `setRequestRelease`, `setFrameQueued` | `PendingCopy::release` and `PendingCopy::written` closures built per frame; hold limit passed to `startAtFolder` | - | - |
| WebUI IMX585 pills | ladder pool (`get_mode_ladder`) | `list_sensor_modes`, fetched once per sensor into `state.sensorModes`; JS tables stay as the fallback | - | WebUI |
| imx585 driver | 2072/1036 at top 44 in the 12-bit and 10-bit tables | 2076/1038 at top 40 (VST 52) in those tables; RAW16 rows unchanged (owner decision 2) | - | 1.6.0 Core works unchanged |
| imx283 `crop_vmax` | default 1 | default 0 | modprobe | Core table = probe |

What a stock camera sees after the series: the original driver, no env knobs, a 1.6.0 `camera_settings.conf`. The probe finds 3840x2076 and 1920x1038. A saved 3840x2076 stays 3840x2076. The WebUI pills send 2076/1038, with or without the probe. 1080p binned configures, because its crop equals the output. 4K offers 30 fps. Lossless keeps ISO 800, manual ISO and 30 fps. No `mode_ladder.conf` exists, so the ladder is off. The touch UI's 1.6.0 lists match the driver. Two differences from 1.6.0 remain. Where the probe reports less than the table, the camera offers less (fork main's accepted rule). The state has the extra field `iso_max`, which only adds.

What the owner's CM5 sees: the cinemate-port driver (or the commit 14 driver) and the four knobs in the unit environment. Everything is as today. One thing differs: a saved 1.85:1 size follows the driver that is installed.

## Commit plan

All Core commits go in `/home/user/wt/core-work` on the improvement branch. "Check here" always includes `/home/user/build/bin/check_core.sh <tree> <tag> both tests` (both builds and the host tests). It also includes `/home/user/build/bin/smoke_core.sh` on the old and new binaries, diffed, to prove every 1.6.0 reply field is still there with the same type. Only extra checks are listed per commit. The order keeps the owner's camera working after each commit. The stock camera starts from commit 4 on.

Installing the original driver for the stock Pi checks (commits 4, 5, 12, 14): build and install `imx585-v4l2-driver` at `e5b74d3` with its `setup.sh`, reboot, run the check, then reinstall `cd548ef`. "Journal" below means `journalctl -u apertar-core -b | grep -E 'sensor mode:|sensor probe:|camera configured|adjusted by the driver|adjusted to too-small'`.

**1. `camera: the IMX585 tables also list the original driver's 1.85:1 sizes`**
- Repo: Core. Files: `src/camera/Imx585Modes.hpp` (`kS12Modes`, `kS10Modes`, `kH12Modes`, the counts comment), `tools/imx585_modes_test.cpp`, `CC` probe.
- Adds `{ 3840, 2076, false }` and `{ 1920, 1038, true }` to S12 and S10, and `{ 3840, 2076, false }` to H12 (the driver's Clear HDR 12-bit list is a range of the same table, `imx585.c:3083-3094`). The probe loop (`CC:7171`) then tries them by itself. Test: counts 62 -> 64, 62 -> 64, 28 -> 29 (`imx585_modes_test.cpp:18-20`); `find(S12, 3840, 2076)`, `find(S10, 1920, 1038)` and `find(H12, 3840, 2076)` exist, binned flags right, and the duplicate check still passes.
- Take along CC-3-F11: in the probe, `tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585` replaces the Model substring (`CC:7152-7158`). Take along Driver-imx585-F8: one journal line per advertised size that no table row covers.
- Lines: -6 / +16.
- Check here: host test. Pi, port driver: journal `sensor mode:` lines are the same as before, the 2076/1038 rows are not among them, and `sensor probe: N modes in M ms` grows by about 5 configures. Original driver: `3840x2076` and `1920x1038` are listed.
- Depends: none. The H1 interim fix is already in this tree (`a36c52f`, H12 = 28).

**2. `camera: a 1.85:1 size follows the height the driver has`**
- Repo: Core.
- `Imx585Modes.hpp` gains one pure function, host-tested: `inline Size driverCropSize(Class cls, Size requested, const std::vector<Size> &probed)`. For 3840x2072/2076 and 1920x1036/1038 it returns the row of the pair whose transport `probed` holds for this class; with `probed` empty, the request if the class has it, else the partner. Other sizes come back as they are. Test: port-driver list -> 2072, original-driver list -> 2076, empty -> request, H16 2076 -> 2072.
- `CC`: delete `migratedImx585CropResolution` and its comment (`CC:440-453`) and its calls at `CC:703`, `CC:10650`, `CC:12665`. Move the `probedSensorModes` declarations (`CC:3307-3310`) above `imx585ModeForResolution` and add a small lookup that returns the probed sizes of a class (bit depth and Clear HDR). `imx585ModeForResolution` (`CC:512`) and the class check in `setResolution` (`CC:10661`) call `driverCropSize` first.
- The rung step stays, with the new mapping: `migrateImx585LadderRungs` (`CC:455-462`) becomes `followDriverCropSizes(rungs)`, using `driverCropSize` per rung class. Its call in `setModeLadder` (`CC:11062`) stays. The constructor call (`CC:10516`) runs before the probe, so it moves to `CameraController::start`, after `settings_ = session_->currentSettings()` (`CC:10555-10556`). The ladder compares each rung with the size the sanitiser returns (`CC:10840-10841`, `10879-10880`, `10921-10926`, `10997-10999`). Without this step, a 2072 rung on a 2076 driver would be "not valid".
- `isImx585LegacyCropResolution` (`CC:497-509`) lists 2076 and 1038 again, so `validateResolution` accepts them for every sensor, as 1.6.0 did (`CC:385-396@upstream-1.6.0`).
- `WCP:9091`: drop the `"3840x2076"` and `"1920x1038"` alias entries, so the page shows what Core reports.
- Lines: -30 / +45.
- Check here: host test of `driverCropSize`. In `--simulate` (sensor Unknown), `set_resolution 3840x2076` -> `get_state` width/height 3840x2076; restart, and the file keeps 2076. `set_resolution 3840x2072` round-trips too.
- Pi, port driver: a `camera_settings.conf` with `resolution_height=2076` starts at 3840x2072 (`camera configured:` line). A ladder with a 3840x2076 rung: `get_mode_ladder` before and after a restart shows the rung as 3840x2072 and valid.
- Depends: 1. The `D2` Clear HDR fix on a parallel branch sets 3840x2160 in `setClearHdr` and does not touch this mapping.

**3. `web: a 1.85:1 pill sends the size it shows`**
- Repo: Core. `WCP:9383-9384` and `9399-9400`: each label returns its own height, as `WCP:5467-5468`, `5483-5484@upstream-1.6.0`. The fallback strings (`WCP:8916-8918`, s12/s10 and the 3840 row of h12) take 3840x2076 and 1920x1038b. The h16 string keeps 3840x2072 (its RAW16 row is unchanged).
- Lines: -6 / +6.
- Check here: headless Chromium in `--simulate`: click 1.85:1 under Full HD and 4K; `get_state` width/height read 1920x1038 and 3840x2076 (sensor Unknown keeps them).
- Pi, port driver: the same clicks give 1920x1036 and 3840x2072 in `get_state` (Core maps them).
- Depends: 2 (Core must map before the page sends 2076 to the port driver).

**4. `camera: the IMX585 readout check accepts the original driver and checks the auto config like the IMX477`**
- Repo: Core. `CC:8464-8530`.
- The colour IMX585 exact-mode block runs only when `useExplicitSensorConfig`. Its `ScalerCropMaximum` comparison is skipped when the crop size equals the configured raw size. Such a driver gives no window (the case `binningFromProperties` calls "inferred", `CC:7104-7111`). One comment line says why.
- A colour IMX585 on the auto path gets the IMX477/577 rule of the block above (`CC:8464-8469`, `CC:6166-6168@upstream-1.6.0`): raw width equal, raw height at least the requested height. The family condition gains `|| (sensorFamily_ == SensorFamily::Imx585 && !monochromeSensor_ && !useExplicitSensorConfig)`. Mono stays as it is, because mono always configures auto (`CC:8314-8316`).
- Lines: -3 / +8.
- Check here: both builds.
- Pi, original driver: Core starts at 1920x1080. The journal has no `scaler crop maximum` rejection. Port driver: `camera configured:` unchanged for 1920x1080, 3840x2160 and 3840x2072.
- Depends: none. This is the commit that lets a stock camera start at all (probable defect, see "Risks").

**5. `camera: colour IMX585 3840-wide crops fall back to the automatic sensor configuration again`**
- Repo: Core. `CC:8297-8298`: add `|| (sensorFamily_ == SensorFamily::Imx585 && sanitized.resolution.width == 3840 && isImx585LegacyCropResolution(sanitized.resolution))`. That is upstream's clause (`CC:5993-5996@upstream-1.6.0`) on the existing helper, with no second size list.
- Lines: -1 / +3.
- Check here: both builds.
- Pi, port driver, `APERTAR_SENSOR_PROBE=0` in the unit environment, then `set_resolution 3840x1744`: configures explicitly as before. Then a hand-edited `resolution_height=2076`: the journal shows `explicit rejected` and then an `auto` configure with raw 3840x2160 (software crop), or the `adjusted to too-small stream 3840x2072` refusal. Never a configured raw 3840x2072. Original driver: `set_resolution 3840x1744` configures.
- Depends: 4 (the auto try needs the size rule first).

**6. `camera: the fps ceiling is the lower of Core's table and the probe again`**
- Repo: Core. In `CC:3389-3423` the ceiling becomes `probed ? (probeOnly ? *probed : std::min(table, *probed)) : table`, with `probeOnly = std::getenv("APERTAR_FPS_LIMIT")` equal to `probe`, read at use. `fps_limit=probe` goes on the `ApertarCore recording clip:` line (`CC:4392`) when set.
- Deleted: `fpsLimitTableOnly`, `imx283ProbeFpsOnly` and `APERTAR_IMX283_PROBE_FPS` (the IMX283 follows the same rule; its table is the crop_vmax=0 floor `CC:3333-3337`). Also deleted: the dead `backendMaximumFps` (`CC:3426-3434`) and its wrappers at `CC:3470`, `CC:3488-3490`, `CC:8640-8641`, and the stale comment at `CC:3378`. In `FpsCeiling.hpp`, `resolveSensorMaxFps` and `applyBackendCap` go, with their test lines.
- Lines: -55 / +12.
- Check here: host tests (`fps_ceiling_test` loses two cases).
- Pi, no env: `get_state` at 3840x2160 12-bit shows `fps_max` 30. With `APERTAR_FPS_LIMIT=probe` in the unit environment: 60, and the take's `recording clip:` line carries `fps_limit=probe`.
- Depends: the owner adds `APERTAR_FPS_LIMIT=probe` to the unit before deploying (storage-settings theme says where). The sanitised fps is saved, so a 4K 50 fps setting saved without the knob comes back as 30. The preroll theme owns `prerollMaximumFps`; this commit only removes the wrapper there.

**7. `camera: lossless cDNG keeps ISO 800, manual ISO and the IMX585 30 fps unless a bench knob raises them`**
- Repo: Core. `CC:3098-3170`: `kLosslessMaxIso` becomes `unsignedEnvValue("APERTAR_LOSSLESS_MAX_ISO", 800, 100, 51200)` at use. `isoAuto = false`, except on the IMX585 with `boolEnvValue("APERTAR_LOSSLESS_AUTO_ISO", false)`. The IMX585 fps becomes `std::min(modeMaximumFps, double(unsignedEnvValue("APERTAR_LOSSLESS_FPS_LIMIT", 30, 1, 280)))`. `maximumIsoForSettings` uses the same cap. The three effective values go on the `recording clip:` line (`CC:4392`).
- Deleted: `losslessFpsOverride`, `FpsCeiling.hpp`, `tools/fps_ceiling_test.cpp` (one host test fewer), and the history comments ("on Patrik's request", "Patrik, 2026-10-28"). `WCP:7504-7505`: the comment says Core's `fps_max` holds the lossless ceiling (30, or the bench knob).
- Lines: -100 / +16.
- Check here: host tests; in `--simulate`, `iso_max` is present and numeric.
- Pi, no env: lossless at 4K has `iso_max` 800, `iso_auto` false and fps 30. With the owner's three knobs: today's values, echoed on the take line.
- Depends: 6 (same file area). The owner adds the knobs first.

**8. `camera: the preview tuning without temporal denoise is derived with libyaml, beside the ProRes tuning`**
- Repo: Core. `src/color/ProresIspProfile.cpp` gains `bool makePreviewTuning(const std::string &source, std::string &destination, std::string &error)`, declared in its header. It reuses `Document`, `member`, `algorithm` and `Edit`. For `rpi.denoise` (each mode mapping when it has `normal`, else the node itself), any mapping holding `tdn` is replaced by its other pairs, copied by byte range and joined with `,`. No comma surgery is needed (KB `V-F6.md:36`). The edits run back to front. It writes `$HOME/.cache/apertar-prores/<stem>_notdn.json` with `settingsFile::atomicWrite` only when the text changed. A source without `tdn` returns the source. `loadablePath` (`CC:7311-7321`) calls it and keeps the fall-back-to-source rule and the journal note. Do NOT use the pipeline's `disable_tdn` (it stalls the back end, `pisp.cpp:1659-1663@6b0b49f`).
- `tools/tuning_tdn_strip_test.cpp`: its build line names `src/color/ProresIspProfile.cpp`, so `check_core.sh` links it (that file compiles alone with libyaml). The test sets `HOME` to a temporary folder itself. With no arguments (as `check_core.sh` runs it) it checks an inline fixture with `normal` and flat `rpi.denoise` forms. With arguments `<pisp data folder> <folder holding imx585_clearHDR.json>`, it checks every file: the new output parses with libyaml, has no `tdn` under `rpi.denoise`, and equals `stripTdn`'s output member by member. Manual command: `/home/user/build/<tag>-tests/tuning_tdn_strip_test /home/user/tiramisioux/libcamera/src/ipa/rpi/pisp/data <golden_dir>`.
- Lines: -12 / +80.
- Check here: the host test with and without arguments; both builds.
- Pi: the journal shows `preview_tdn=off active=/home/pi/.cache/apertar-prores/<stem>_notdn.json`. libcamera starts without a tuning error. 4K Clear HDR 16-bit preview fps is as before. A ProRes Log take still starts.
- Depends: the parallel branch that limits the strip to raw formats (already in this tree, `CC:7309`).

**9. `camera: the TuningTdnStrip header goes`**
- Repo: Core. Delete `src/camera/TuningTdnStrip.hpp` and its include (`CC:20`). The test keeps only the checks of commit 8. Its file name stays. `README.md:323` gives the new cache path, and its test line names the new build line. The old cache `$HOME/.cache/apertar-core/tuning/` is no longer used and stays on disk.
- Lines: -500 / +6.
- Check here: host tests, both builds.
- Pi: nothing new.
- Depends: 8.

**10. `camera: camera_settings.conf holds the mode ladder`**
- Repo: Core.
- `include/apertar/core/Types.hpp`: add `bool modeLadderEnabled = false;`, `bool modeLadderRampReady = false;`, `std::string modeLadderResolutions;` (persisted). `ladderEnabled` and `ladderRampReady` (`Types.hpp:184-185`) stay the derived state fields they are.
- Loader (next to `tuning_file`, `CC:865`): three `else if` keys. After the loop, if none of them was read and `mode_ladder.conf` exists, it is read with `ladder::parseFile` into the current block and every profile (the loop shape of `CC:727@upstream-1.6.0`). Writer (`CC:972`): three lines. Format carry (`CC:11343-11372`): three fields.
- `setModeLadder` (`CC:11047-11104`) keeps its two paths. A rung or format change still goes through `applySettingsLocked(next, ...)`, with the three fields in `next`. Otherwise it sets them in `settings_` and calls `persistSettingsLocked(); emitSettingsEventLocked();` (`setTuningFile`'s no-session shape). So a ladder edit still works in Standby and during a pre-roll, as today. `modeLadder_` stays as the parsed form (`CCH:248`, comment "parsed from settings_.modeLadderResolutions"). It is set where the fields are written: the constructor from `settings_`, `setModeLadder`, and commit 2's rung step, which also writes `modeLadderResolutions = ladder::rungsText(...)`.
- Deleted: `saveModeLadderLocked` (`CC:10941-10947`, `CCH:188`), `ladder::fileText` (`ModeLadder.hpp:316-323`, "T34" header), and the constructor's file read (`CC:10511-10517`). `modeLadderPath` becomes `persistedSettingsPath().parent_path() / "mode_ladder.conf"` (X-knobs-14). It is used only by the take-over.
- When the new place is written: at the next persist (any setting change or `set_mode_ladder`). Until then the old file is read at each start. It is never written or deleted.
- Lines: -55 / +45.
- Check here, in `--simulate`: (a) put a `mode_ladder.conf` in the sim HOME, start, and `get_mode_ladder` shows it; change any setting, and `camera_settings.conf` has `mode_ladder_resolutions=` with the same text; restart without the old file and the ladder is the same. (b) `set_mode_ladder` persists after a restart. (c) A cDNG -> H.264 -> cDNG switch keeps the ladder. (d) `set_mode_ladder enabled=false` while in Standby (`standby` command first) is accepted, as before.
- Pi: the owner's ladder is unchanged after the update (`get_mode_ladder` before and after, diffed).
- Depends: 2 (rung step). Storage-settings theme: same file, same carry block (merge order).

**11. `camera: the DNG copy worker gives each request back through its own closure`**
- Repo: Core. `DngRecordingQueue::PendingCopy` (`CC:5032-5041`): `request` is replaced by `std::function<void()> release` and `std::function<void()> written`.
- The raw frame handler (`CC:9490-9510`) builds `release = [this, request]{ std::shared_lock lock(sessionSettingsMutex_); if (running_.load()) requeueRequest(request); }`. One comment line says why: requeue reads session settings, and the completion callback holds this lock for it. It also builds `written = [this, timestampUs, frameDurationUs]{ audioRecorder_.observeVideoFrame(...); }`.
- `releaseHeldRequest(PendingCopy &copy)` keeps the `heldRequests_` decrement (`CC:5156-5157`) and calls `copy.release()`. The copy worker (`CC:5114`) and the stop loop (`CC:5182-5183`) both call it. The worker calls `copy.written()` where it called `frameQueued_` (`CC:5141-5147`). `heldRequests_` is still reset at take start (`CC:4383`). The hold limit (buffers-2) becomes a `startAtFolder` argument (one caller, `CC:7743`).
- Deleted: `setRequestRelease`, `setFrameQueued`, `releaseRequest_`, `frameQueued_` (`CC:5050-5063`, their members near `CC:5606`, `CC:8730-8741`). `enqueueCopy` no longer refuses on a missing callback (`CC:5070`).
- Lines: -45 / +28.
- Check here: the libcamera build only. `DngRecordingQueue` is inside `#if APERTARCORE_HAS_LIBCAMERA` (`CC:4188`) and no host test reaches it.
- Pi: one 60 s 4K Clear HDR 16-bit take at 30 fps and one 4K 12-bit lossless take, before and after: `journalctl -u apertar-core -b | grep 'drop\[copy-slot\]'` gives the same counts. A stop while the queue is full does not hang. WAV length equals clip length within one frame.
- Depends: none. If the owner picks option B of decision 6, `written` goes and audio is observed after `enqueueCopy` (the ProRes shape).

**12. `core, web: the IMX585 resolution pills come from the sensor modes, not from the Mode Ladder`**
- Repo: Core.
- `CameraController::SensorMode` gains `Resolution active{}`, set by the probe where it already knows it: the table row for the IMX585 (`CC:7172-7176`), `imx283ActiveForTransport` for the IMX283, else the size. The ladder pool (`CC:11008-11020`) reads `mode.active` instead of converting twice. App cannot compute it at serialisation: it knows only the sensor name, and `sensorModes()` is called under `mutex_` (`CC:11004`). `list_sensor_modes` (`App:12741`) adds `active_width` and `active_height`.
- `WCP`: `imx585ClassRows` (`WCP:8955-8970`) reads `state.sensorModes`, fetched once with `sendCommand({cmd:"list_sensor_modes"})` when the snapshot's sensor name first appears or changes (the `state.presetLibrary` shape). The JS tables stay as the fallback. `get_mode_ladder`'s pool stays for the ladder editor only. The comment at `WCP:8911-8914` says so.
- Lines: -20 / +35.
- Check here: `list_sensor_modes` in `--simulate` has the two new fields (empty list). The IMX585 pill code does not run in `--simulate` (`imx585Selected`, `WCP:8935-8937`), so the only check here is a canned reply fed to `imx585ClassRows` in the headless Chromium console.
- Pi: the original driver offers 3840x2076 and no 2880x2160; the port driver offers the port set.
- Depends: 1. webui-state theme: they own the WebUI's stores and poll loop. This adds one fetched list in `state`, and they may fold it into their pattern.

**13. `camera: the 1.85:1 and ladder comments say only what holds`**
- Repo: Core. These comments shrink to one line of why or go: `T34:` at `CC:403`, `// T34: the ladder owns the mode` at `CC:10645` and `CC:11579`, the "(T34)" notes in `Types.hpp:182-189`, `// ---- Mode ladder (T34)` at `CC:10825`, `Imx585Modes.hpp:3,16` (header line: "modes of the Apertar and cinemate-port drivers").
- Lines: -12 / +4.
- Check here: both builds.
- Depends: 2, 10.

**14. `imx585: 1.85:1 is 3840x2076 and 1920x1038 again, at crop top 40`** (driver)
- Repo: `/home/user/imx585-v4l2-driver`. In the 12-bit and 10-bit tables (`imx585.c:867`, `:918`, `:1121-1127`, `:1408-1414`, `:2168-2174`, `:2423-2429` @cd548ef): height 2072 -> 2076, top 44 -> 40. That gives VST 52, a multiple of 4. 2076 passes the `(sensor_height & 3)` rule in `imx585_program_window` (`imx585.c:2959-2966`). Binned output 1036 -> 1038. Enum names follow. The Clear HDR 12-bit range takes the 3840 row with it. The RAW16 rows (`imx585.c:1766-1783`) stay as they are.
- `APERTAR.md:145-157` "Sizes that changed" goes. `APERTAR.md:137` loses the `3840x2072` duplicate warning, which no longer occurs (Driver-imx585-F6, first half). `APERTAR.md:120` stays true (the RAW16 3840x2112 frame is still a 2072 window plus 40). One sentence goes in the modes section: "1.85:1 is 3840x2076 / 1920x1038; Apertar Core also runs the 3840x2072 / 1920x1036 of older cinemate-port builds."
- Lines: -30 / +18.
- Check here: none (no kernel build here).
- Pi: `dmesg` shows no window error. `v4l2-ctl -d /dev/v4l-subdevN --list-subdev-framesizes pad=0,code=<12-bit and 10-bit codes>` lists 3840x2076 and 1920x1038. Make one take per class (SDR 12, SDR 10, Clear HDR 12) at each size, and check that row 0 and the last row are picture, not black. With unmodified 1.6.0 Core, set 1920x1038 and it records.
- Depends: Core commits 1-3 deployed on the owner's camera first. Without them, the old port Core rewrites 2076 to 2072, which this driver no longer has.

**15. `imx283: per-crop VMAX floors are off by default`** (driver)
- Repo: `/home/user/imx283-v4l2-driver`. `imx283.c:271-281`: `static bool crop_vmax;`, a one-line comment, and a `MODULE_PARM_DESC` that says "default 0". `APERTAR.md:92-113`, `:194-196`: drop the modprobe.d instruction; keep one line on how to turn the experiment on.
- Lines: -20 / +4.
- Pi: delete `/etc/modprobe.d/imx283.conf` first, reboot, then `cat /sys/module/imx283/parameters/crop_vmax` prints `N`. Core's `fps_max` is unchanged against today's `crop_vmax=0` setup.
- Depends: none. Core already caps the IMX283 at the crop_vmax=0 floor whatever the driver does (`CC:3333-3337`).

Totals, Core: about -845 / +304. Drivers: -50 / +22.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| Startup sensor probe, IMX585 by table row | As on fork main `f60e301` (already the merge target): a free function in `CC`, a file-scope vector under one mutex, published through `list_sensor_modes` | It is what lets one Core serve both drivers. 1.6.0 has no probe |
| IMX585 class tables and `driverCropSize` (`Imx585Modes.hpp`) | Header-only, `inline`/`constexpr`, std only, one includer plus a host test (CAM-4) | 1.6.0 keeps sizes in predicates in `CC`. 190 rows in four classes do not fit predicates. The probe makes the tables advisory: a row the driver lacks does nothing |
| `min(table, probe)` | Fork main's rule | Where the probe reports less than the table, a stock camera offers less than 1.6.0 |
| `APERTAR_FPS_LIMIT=probe`, `APERTAR_LOSSLESS_*` | R8 bench knobs, read at use, bounded, printed on the take line | They are the owner's measured-but-unproven limits. Upstream raises a limit by editing the table once takes prove it |
| Mode ladder itself | Camera-wide keys in `camera_settings.conf` (commit 10); its reply `get_mode_ladder` is nested JSON | The feature has no upstream counterpart. Its store now has the upstream shape. The nested reply is the command-plane theme's question |
| Reading `mode_ladder.conf` once to take it over | One read in the loader, only while none of the three keys was read | Core never reads a second file for a take-over. The nearest precedent is the UI's presets folder (`SettingsBridge.cpp:1937-1958@upstream`) |
| Preview without temporal denoise | A derived tuning, as ProRes Log | The feature is new; the mechanism is upstream's |
| Per-frame `written` closure for audio | A second `std::function<void()>` on the DNG job | Upstream observes audio at hand-over (ProRes). The port observes at write-queue acceptance on purpose (decision 6) |

## For the owner

1. **How does your rig get today's limits back?**
   - Options: (A) four env knobs in the Core unit's environment (`APERTAR_FPS_LIMIT=probe`, `APERTAR_LOSSLESS_MAX_ISO=1600`, `APERTAR_LOSSLESS_AUTO_ISO=1`, `APERTAR_LOSSLESS_FPS_LIMIT=60`). (B) camera-wide keys in `camera_settings.conf` with no UI. (C) a WebUI switch.
   - Recommendation: A. It is R8, the original developer sees no new setting, and you set it once. Cost: the knobs need a home on the rig (storage-settings theme); until it exists, commits 6-7 must not reach your camera. Re-pick a 4K fps above 30 if it was saved clamped. Long term, raise the IMX585 table rows (`CC:3373-3381`) in a commit with counted takes, and the knob goes.
2. **Should the cinemate-port imx585 driver keep advertising the old sizes?**
   - Options: (A) 2076/1038 at top 40 replace 2072/1036 in the 12-bit and 10-bit tables (commit 14). (B) advertise both sizes. (C) keep 2072/1036 and state that a driver update needs Core 1-3.
   - Recommendation: A. The driver is installed apart from Core (`README.md` "not installed"), so a driver update must not break the 1.6.0 Core in the field, which has no fallback for 1920x1038. A moves the window 2 sensor rows off centre (0.1 %). Its ratio, 1.850, is closer to 1.85:1 than 2072's 1.853. B doubles a mode, and the WebUI shows one 1.85:1 pill either way.
   - Cost of A: one Pi take per size and class (VST 52 is unmeasured). Your saved 2072/1036 become 2076/1038 at the next save. The 1.85:1 rows of `cinemate-port` no longer match `cinemate-modes` (merged in `6f25d7f`), so every later merge of that branch touches the same 4+2 rows. Cinemate's own tests list 3840x2072 (`cinemate/_test/test_aspect_ratio_selection.py:781`). After commits 1-3 Core works with both heights, so C stays possible. C only loses 1.6.0 Core on a new driver (Driver-imx585-F1).
3. **Ladder store: `camera_settings.conf` or its own file?**
   - Options: (A) camera-wide keys (commit 10). (B) keep `mode_ladder.conf`, fix only the path copy and the "T34" header (X-knobs-14 says a separate file is acceptable).
   - Recommendation: A. Upstream keeps camera settings in one Core-written file, and camera-wide values repeat in every profile block (`tuning_file`), so no new block kind is needed. A also moves the write off `mutex_` onto the persister.
   - Cost: one take-over path that stays as long as old cameras exist. Reading a second, older file is new ground in Core (the UI does it for presets).
4. **imx283 `crop_vmax`: default off or delete?**
   - Options: (A) default 0, keep the parameter. (B) delete the parameter, the `crop_min_VMAX` field and the macro argument until measured.
   - Recommendation: A now, B if no measurement is planned. Cost of A: dead-by-default code in the driver.
5. **Lossless ISO 1600 on the IMX585 only?**
   - Options: (A) default 800 everywhere with a knob (commit 7). (B) default 1600 for the IMX585 only, in its own commit with the take numbers, for the original developer to accept.
   - Recommendation: A, then B once you have counted 4K 25/30 lossless takes at ISO 1600 on more than one board. Cost of B: one argued commit.
6. **When does the WAV learn about a frame?**
   - Options: (A) when the write queue took it (today; a second per-frame closure). (B) at hand-over to the copy worker, as ProRes does.
   - Recommendation: A, since it keeps your measured sync. Cost: one extra closure per frame. B deletes about 8 more lines, and a take that ends with drops may have up to the queue depth of extra audio.

## Risks and what was not determined

- **Binned modes on the original driver** are refused by the port Core today. This is probable: the code path is confirmed (`CC:8513-8521`, `imx585.c:803-808,2379-2381@e5b74d3`, `pipeline_base.cpp:568@6b0b49f`; the check runs after `configure()`), but it was not run. The line `adjusted by the driver (scaler crop maximum (0, 0)/1920x1080)` on a stock-driver Pi settles it. Commit 4 fixes it either way.
- **What libcamera's auto config returns for 3840x2076 on the port driver** is probable, not run: `findBestFormat` scores 3840x2072 best (`pipeline_base.cpp:973-1010@6b0b49f`). Commit 4's size rule refuses that stream either way. The commit 5 Pi check settles it.
- **Probe off** (`APERTAR_SENSOR_PROBE=0`, a bench knob, default on): a 1.85:1 size must then be the installed driver's own. On the port driver a saved 2076 no longer configures (explicit refused, auto refused by the size rule), where today the rewrite made it 2072. The WebUI sends what it shows, so the operator picks 1.85:1 again after a probe-off start.
- **VST 52** (commit 14) has no take. Check the first and last rows of a 3840x2076 frame in each class.
- **Probe time** rises by about 5 configures (S12 2, S10 2, H12 1). Pi 4 / VC4 never ran the table probe (X-board-support-14). The `sensor probe: N modes in M ms` line on a Pi 4 settles it.
- **Deploy order on the owner's camera**: env knobs before commits 6-7; Core commits 1-3 before driver commit 14.
- **Sanitised values are saved.** A setting clamped while a knob was missing stays clamped after the knob is set. Re-pick it.
- **WebUI before the mode list arrives**: on the port driver the fallback strings show 2076 while Core reports 2072, so no 1.85:1 pill is lit until `list_sensor_modes` arrives (one round trip). A click in that window still lands on 2072, because Core maps it.
- **Parallel branches.** The 12-bit Clear HDR D1-D3 fixes: D2 sets 3840x2160 in `setClearHdr`, which commit 2 does not touch; rebase commit 2 after it. The H1 interim fix is already in this tree. Preroll owns `prerollMaximumFps` (commit 6 touches one call). Storage-settings owns the carry block and where env knobs live (commits 6, 7, 10).
- **Touch UI.** Its 1.6.0 lists (`CameraPage.qml:418`, `SettingsPage.qml:161`) match the original driver. On the port driver, Core maps a 2076 pick to 2072, and the current value is then not in the list (X-state-consistency-3). The touch-ui theme owns the mode list.
- **libyaml marks on JSON keys** (commit 8): the key's byte range must include its quotes. The host test against the pisp data files and the Clear HDR file settles it before commit 9 deletes the old path.
- **Commit 11** cannot be run here at all. Its release order at stop (the closure must no-op once `running_` is false) is checked only by the Pi stop-under-load step.
- **Not determined:** whether the original driver advertises its crops in 10-bit (the probe decides at run time, so the design does not depend on it). Whether 4K 12-bit at 60 fps records without drops on a Pi 5 with a stock NVMe; that is the measurement the knobs stand in for.
- **Out of this theme**: preview TDN default for RAW preview (X-stock-behaviour-6, CC-3-F7), the hidden 960/1024 families (Driver-imx585-F4), `setResolution` accepting table rows the probe lacks (CC-5-F6), one readout helper for IMX585 and IMX283 (CC-4-F8, slop pass).

## Findings covered

| Finding | Commit |
| --- | --- |
| CC-1-F1 | 1, 2 |
| Driver-imx585-F1 | 14 (Core side: 1, 2, 3) |
| X-stock-behaviour-4 | 1, 2, 3, 4, 5 |
| CC-4-F2 | 4, 5 |
| CC-2-F3 | 7 |
| Camera-headers-F3 | 7 |
| Camera-headers-F4 | 6 |
| X-stock-behaviour-3 | 6, 7 |
| Camera-headers-F1 | 8, 9 |
| Camera-headers-F5 | 10 |
| CC-4-F1 | 11 |
| X-state-consistency-3 | partly: Core and WebUI by 2, 3, 12; the touch UI lists are the touch-ui theme's |
| WCP-04-F1 | 12 |
| Driver-imx283-F2 | 15 |
| X-knobs-14 | 10 |
| X-knobs-17 | 6, 15 |
| Taken along: CC-1-F5 | 10 |
| CC-3-F11 | 1 |
| Driver-imx585-F8 | 1 (log line); the host test parsing `imx585.c` is not covered (new tooling, no precedent) |
| CC-4-F4, CC-2-F10 | 6 |
| Camera-headers-F16 | 7 |
| CC-2-F11, Camera-headers-F11 | 6, 7 for the fps and lossless knobs; `minModeWidth` parsing not covered (belongs with Driver-imx585-F4) |
| X-stock-behaviour-9 | 7 |
| X-stock-behaviour-10 | 7 (Core default back to manual ISO); `iso_auto_allowed` for the UIs not covered (UI themes) |
| WCP-04-F12 | 2 (alias removed), 3, 12 |
| Driver-imx585-F6 | 14 removes the duplicate-size warning; the four copies of the window predicate are not covered (driver slop pass) |
| CC-1-F7, Camera-headers-F12 | 13, and 10 (ladder file header) for this theme's lines; the rest belongs to the slop pass |
| CC-4-F8 | not covered: slop pass |
| Camera-headers-F2 | not covered: done on a parallel branch (strip limited to raw formats) |

## What the challenge changed

Old numbers are the first design's (1-14, D5-1, D2-1). All verdicts were read in code at `0d13a6f`.

| Point | Decision | Why |
| --- | --- | --- |
| Ladder rungs after the rewrite goes (old 2) | Partly right. The rung step stays (now commit 2), but its load call moves from the constructor to `CameraController::start` | The ladder compares rungs with the sanitised size (`CC:10840-10841`, `10879-10880`, `10921-10926`, `10997-10999`), as the challenge says. The constructor reads the ladder (`CC:10511-10517`) before the probe runs (`CC:7334`), so a probe-aware mapping there would do nothing. After `settings_ = session_->currentSettings()` (`CC:10555-10556`) the probe has run |
| WebUI sends port sizes; fallback lists (missing M1) | Right. Added as commit 3 | `WCP:9383-9384`, `9399-9400`, `8916-8918`; 1.6.0 sends the label (`WCP:5467-5468`, `5483-5484@upstream-1.6.0`) |
| Clear HDR 12-bit 1.85:1 after the driver change (old 1, D5-1) | Right, with one correction: H12 goes 28 -> 29, not 30 | Range `imx585.c:3083-3094` holds row `:867`. The H1 interim fix is already in this tree (`a36c52f`, `imx585_modes_test.cpp:20` says 28). RAW16 rows stay (`imx585.c:1766-1783`) |
| Auto fallback without a size check (old 3, 4) | Right, limited to the colour sensor | Upstream rule `CC:6166-6168@upstream-1.6.0`; port block `CC:8464-8469`. Mono IMX585 always configures auto (`CC:8314-8316`), and the rule would be new there, so it is left out |
| `set_mode_ladder` through `applySettingsLocked` (old 9) | Right | Today `CC:11091-11098`; refusals `CC:12744`, `12748`; shape `CC:8076-8083@upstream-1.6.0`. Commit 10 has a Standby check |
| Take-over precedent (old 9) | Partly right. Core has none. The UI reads an old location while the new one is missing, which is the nearest precedent. It stays on the owner's list | `ui-upstream src/SettingsBridge.cpp:1937-1958`; `DefaultTuningSelection.hpp:74@upstream-1.6.0` |
| Stored field names (old 9) | Right | `ladderRampReady` and `ladderEnabled` are derived (`Types.hpp:184-185`, `CC:10897`, `10930`) |
| Commit 10 dropped | Right | After commit 10 (new) the fields change only where `modeLadder_` is set; the carry copies them (`CC:11343-11372`); presets start from `camera_.settings()` (`App:14231`) |
| Copy-worker stop path and counter (old 11) | Right | `CC:5151-5162`, `5176-5183`, `4383`; one caller `CC:7743` |
| Old 11 check here | Right | `DngRecordingQueue` is under `#if APERTARCORE_HAS_LIBCAMERA` (`CC:4188`) |
| Old 7 test arguments and HOME | Right, plus a no-argument fixture so `check_core.sh` still runs the libyaml path | `check_core.sh:31` runs tests with no arguments; `imx585_clearHDR.json` is not in `pisp/data` |
| Docs that name moved things | Partly right. `README.md:323`, `APERTAR.md:137`, `WCP:7504-7505` change. `APERTAR.md:120` stays true | RAW16 3840x2112 is still a 2072 window plus 40 (`imx585.c:1766-1773`) |
| Precedent for run-time limits (old 5) | Right | `Caps` holds board facts; 1.6.0 uses the table alone (`CC:2669-2671@upstream-1.6.0`); `min` is `CC:2763-2769@f60e301` |
| R8 echo (old 5) | Right | `fps_limit=probe` on `CC:4392` |
| No new `SensorMode` field (old 12) | Wrong on the mechanism. The field stays, set by the probe from the row it tries; the pool's two conversions go | App knows only the sensor name (`CC:12600-12608`). `sensorModes()` is called under `mutex_` by the pool (`CC:11004`), so a family lookup at read would take `mutex_` twice. The probe already holds the row (`CC:7172-7176`) |
| Old 12 check here | Right | `imx585Selected` `WCP:8935-8937`; sim sensor is not an IMX585 |
| Old 13 dropped | Right | CC-4-F8 is duplication with no behaviour change; it goes to the slop pass |
| D2-1 dependency | Right | Core caps the IMX283 at the floor regardless (`CC:3333-3337`, `3419-3421`) |
| Owner decision 2 cost | Right. Recommendation stays A, with the cost written down | `6f25d7f`; `test_aspect_ratio_selection.py:781` |
| README sentence (old 2) | Right. It goes to the driver's `APERTAR.md` in commit 14 | R6 point 1 |
| Stock camera summary | Right. Rewritten after commit 3 | Fork main's `min` rule and `iso_max` are named |
| Stock-driver Pi checks | Right. The install step is named once, above the commit list | The rig runs the port driver |
| Found while checking | Added to "Risks": probe off with a saved other-driver size; the WebUI pill not lit until the mode list arrives | Explicit refused + auto size rule (commit 4); fallback strings 2076 vs Core 2072 |
