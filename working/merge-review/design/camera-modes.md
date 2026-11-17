# Camera modes and limits: work with the original driver too: design

Read at: Core `/home/user/wt/core-work` `7dc6f7a`, UI `/home/user/wt/ui-work` `ac1fc28`, imx585 driver `cinemate-port` `cd548ef` (baseline `origin/apertar` `e5b74d3`), imx283 driver `cinemate-port` `68b7dc9`, upstream `35dbe67` / `43888e5`, fork main `f60e301`. Refs below: `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `App` = `src/ApertarCoreApp.cpp`; no ref = `@7dc6f7a`.

## In short

1. Today the port Core works only with the cinemate-port imx585 driver. It rewrites 3840x2076 / 1920x1038 to 2072 / 1036 everywhere, has no auto sensor-config fallback for colour IMX585, and (new in this design, **probable**) refuses every 2x2 binned mode of the original driver, 1920x1080 included, because that driver reports its crop in binned pixels (`CC:8510-8517`).
2. The fps ceiling is the probe alone, and lossless cDNG lost 1.6.0's ISO 800, manual ISO and IMX585 30 fps. A stock camera offers and records more than 1.6.0 did.
3. Three port mechanisms have their own shape where upstream has one: a second settings file for the ladder, a second JSON parser for the TDN strip, a session-wide request-release callback.
4. Target: Core decides at run time from the startup probe. The 1.85:1 row is whichever height the driver advertises in that class. Nothing is rewritten on load. Defaults are 1.6.0's limits on every driver. The owner's rig gets today's limits back with four bench knobs (R8).
5. The ladder moves into `camera_settings.conf` as camera-wide keys (the `tuning_file` shape). `mode_ladder.conf` is read once to take it over. The TDN strip becomes a libyaml function beside `makeProresIspTuning`. The DNG copy worker gets per-frame closures, like the ProRes and H.264 recorders.
6. Drivers: the imx585 driver advertises 3840x2076 / 1920x1038 again, at crop top 40 (owner decision 2). The imx283 driver defaults `crop_vmax` to 0.
7. 14 Core commits and 2 driver commits. Most remove more lines than they add (about -945 / +330 in total).

## How it works in the port today

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| IMX585 mode tables S12/S10/H12/H16 (62/62/29/34 rows, copied from the cinemate-port driver) | by hand, `src/camera/Imx585Modes.hpp:39-98` | probe `CC:7171-7176`; `imx585ModeForResolution` `CC:512-518` (sanitiser, mode selection `CC:2670-2672`, normaliser `CC:2832`); `setResolution` class check `CC:10659-10665`; exact-mode check `CC:8511-8517`; ladder `CC:10965`, `CC:11011` | constexpr, no lock | none | WebUI hand copy `WCP:8915-8920` (fallback); touch UI keeps the 1.6.0 lists (`ui-work qml/CameraPage.qml:418`, `qml/SettingsPage.qml:161`) |
| 1.85:1 rewrite `migratedImx585CropResolution` 2076->2072, 1038->1036 | called in `clampCaptureSettings` `CC:703` (every load, every persist `CC:1016`, every apply), `setResolution` `CC:10648`, presets `CC:12663`, ladder load `CC:10514` and `setModeLadder` `CC:11060` | every later lookup | command thread under `mutex_`; persister thread at `CC:1016` | `camera_settings.conf` and `mode_ladder.conf` are rewritten at the next save | `width`/`height` in state; WebUI alias `WCP:9085` |
| Startup probe `probedSensorModes` | `probeSensorModesOnce` `CC:7232-7244`, called at the first configure `CC:7334`; IMX585 is probed by table rows only, found by a `properties::Model` substring `CC:7152-7176` | `probedMaximumFps` `CC:3313-3322`; `sensorModes()` `CC:12608` -> `list_sensor_modes` `App:12741`, ladder pool `CC:11005-11033` | configure thread; `probedSensorModesMutex` (file-scope global `CC:3307`) | none (journal lines `ApertarCore sensor mode:`) | WebUI pills through the ladder pool `WCP:8955-8960` |
| Auto sensor-config fallback | `allowAutoSensorConfigFallback` `CC:8295-8296`: mono, IMX294, IMX577 only | configure loop `CC:8311-8315` | configure, `mutex_` | none | journal rejection log |
| Colour IMX585 exact-mode check (raw size, bit depth, `ScalerCropMaximum` = active x binning) | `CC:8485-8530`, explicit and auto alike | same loop | configure, `mutex_` | none | journal `adjusted by the driver (...)` |
| Sensor fps ceiling | `maximumSupportedFpsForResolution` `CC:3411-3423` -> `fpsceiling::resolveSensorMaxFps` (`src/camera/FpsCeiling.hpp:14-19`): probe alone; `APERTAR_FPS_LIMIT=table` `CC:3398-3408` and `APERTAR_IMX283_PROBE_FPS` `CC:3391-3395` read once; dead `backendMaximumFps` `CC:3426` wrapped at `CC:3470`, `CC:3488`, `CC:8636` | sanitiser, configure clamp `CC:8636-8643`, `fps_max` (`settings()` `CC:12592`), storage pre-roll `CC:3486-3491` | `mutex_` | sanitised fps is saved | `fps_max`; WebUI and touch UI fps lists |
| Lossless cDNG limits | `enforceLosslessCaptureLimits` `CC:3146-3157`: `kLosslessMaxIso = 1600` `CC:3100`, auto ISO kept on IMX585, IMX585 fps = mode max unless `APERTAR_LOSSLESS_FPS_LIMIT` (`CC:3115-3142`, parsed by `FpsCeiling.hpp:29-45`) | sanitiser; `iso_max` `CC:3161-3167`, `CC:12591` | `mutex_` | sanitised ISO and fps are saved | `iso_max`, `fps_max` |
| Mode ladder (enabled, ramp_ready, resolutions) | `setModeLadder` `CC:11044-11101` -> `saveModeLadderLocked` `CC:10939-10945`: synchronous `atomicWrite` under `mutex_`; path `modeLadderPath` `CC:404-415` (a copy of `persistedSettingsPath` `CC:417-428`); parsed in the constructor `CC:10509-10515` with `ladder::parseFile` (`src/camera/ModeLadder.hpp:327-342`) | `modeLadder_` (`CameraController.hpp:248`): `ladderActiveForLocked` `CC:10860`, `ladderRewriteLocked` `CC:10870-10876`, `fillLadderFieldsLocked` `CC:10895-10928` | command thread, `mutex_` | `~/.config/apertar-core/mode_ladder.conf` (header line carries "T34", `ModeLadder.hpp:319`) | `ladder_*` fields (`App:330-333`, `App:9498-9501`); WebUI Modes card via `get_mode_ladder` |
| Preview tuning without TDN | `loadablePath` `CC:7311-7321` -> `tuning::previewTuningPath` (`src/camera/TuningTdnStrip.hpp:384-449`): own recursive JSON parser `:43-249`, own temp+rename writer `:350-378`, `.src` sidecar with size+mtime | libcamera via `applyProcessTuningFile`; ProRes/Log derivation reads it `CC:7413` | configure thread, `mutex_` | `$HOME/.cache/apertar-core/tuning/<stem>_notdn.json` + `.src` | journal `preview_tdn=off active=...` `CC:7437`; `preview_tdn` in state |
| DNG request release | `recorder_.setRequestRelease(...)` installed once after `makeRequests` `CC:8731-8736` (takes `sessionSettingsMutex_` shared, then `requeueRequest`); hold limit buffers-2 passed with it; `PendingCopy.request` `CC:5033` | copy worker `releaseHeldRequest` `CC:5151-5162`; enqueue refuses when no callback `CC:5070` | completion thread enqueues, copy worker releases; `copyMutex_` | none | none |
| Audio follows written frames | `recorder_.setFrameQueued(...)` `CC:8737-8739` | copy worker after the write queue took the frame `CC:5139-5147` | copy worker, `copyMutex_` to copy the function | none | WAV length |
| imx585 driver 1.85:1 size | `imx585.c:1121-1127`, `:1408-1414`, `:2168-2174`, `:2423-2429` @cd548ef: 3840x2072, 1920x1036 at crop top 44 | libcamera, Core probe | - | - | `APERTAR.md:145-157` tells users to move saved sizes |
| imx283 `crop_vmax` | `imx283.c:277` @68b7dc9 default true (unmeasured per-crop VMAX floors) | `imx283.c:2430` | - | `/etc/modprobe.d/imx283.conf` (by hand, `APERTAR.md:92-113`) | Core caps at the crop_vmax=0 floor `CC:3333-3337` unless `APERTAR_IMX283_PROBE_FPS=1` |

What the two drivers report, side by side (confirmed in code):

| | Original driver `e5b74d3` | cinemate-port driver `cd548ef` |
| --- | --- | --- |
| 1.85:1 | 3840x2076, 1920x1038 binned (`imx585.c:591`, `:817`) | 3840x2072, 1920x1036 binned |
| Binned crop rectangle (`V4L2_SEL_TGT_CROP` -> libcamera `ScalerCropMaximum`, `pipeline_base.cpp:568` @6b0b49f) | binned pixels: 1920x1080 at (0,0) for the 1080 mode (`imx585.c:803-808`, `:2129`) | native pixels: 3840x2160 |
| Port Core exact-mode check `CC:8510-8517` | wants 3840x2160 for a binned row, gets 1920x1080: **refused** (probable; journal settles it) | passes |
| Other sizes | 1920x1080, 1920 crops (binned), 3840x2160, 3840 crops, 16-bit Clear HDR 3840x2200 | the 4 class tables of `Imx585Modes.hpp` |

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent | What it says |
| --- | --- | --- |
| A size a client sends that the sensor names differently | `isImx585LowResolutionAlias` `CC:360-364@upstream-1.6.0`; `normalizedResolutionForSensor` `CC:2372-2421@upstream-1.6.0` | The request is mapped to the sensor's size in the per-sensor normaliser, at use. The saved value is never rewritten on load |
| Retiring a saved size | `normalizedImx294ResolutionForBitDepth` `CC:511-532@upstream-1.6.0` ("Retire the small central RAW windows, including saved selections") | Done in the sensor's normaliser, so other sensors keep the size |
| The driver may lack an explicit mode | `allowAutoSensorConfigFallback` `CC:5993-5996@upstream-1.6.0`, loop `CC:6012-6017` | Explicit sensorConfig first, then auto for mono, IMX294, IMX577 and IMX585 raw12 crops; Core crops in software |
| Limits found at run time | `Caps` board detection (CAM-13); fork main probe `CC:5446-5545@f60e301`, ceiling `probed ? std::min(table, *probed) : table` `CC:2766-2770@f60e301` | Probe only lowers the hard-coded table. Commit `f60e301`: "SDR limits unchanged (the probe only lowers them)" |
| Product limits | `enforceLosslessCaptureLimits` `CC:2470-2491@upstream-1.6.0` (ISO 800, `isoAuto = false`, IMX585 30); table `CC:2669-2671@upstream-1.6.0` (IMX585 4K 30) | Limits are code; `validate()` has the last word |
| Bench knobs | `unsignedEnvValue` / `boolEnvValue` `CC:1027-1061@upstream-1.6.0`, used at `CC:1127`, `CC:1133` | `APERTAR_<AREA>_<KNOB>`, read at use, bounded, default in code, not a setting (R8, CAM-24) |
| A camera-wide setting | `tuning_file`: `CaptureSettings` field, loader key, writer line, carried across format profiles `CC:7939-7955@upstream-1.6.0`; debounced persister `CC:742-889@upstream-1.6.0` | One file, written only by Core through the persister (CMD-12, CMD-14, CAM-40) |
| Taking over an old value | `wb_locked` read at `CC:682@upstream-1.6.0`, applied after the loop `CC:727@upstream-1.6.0` | The loader reads the retired form and turns it into today's; the file gets today's form at the next save |
| A derived tuning file | `makeProresIspTuning` `src/color/ProresIspProfile.cpp:72-90`, `:221-236@upstream-1.6.0`; header `:7` "Writes an internal derived tuning, never the user's selected source file" | libyaml node lookup, byte-range `Edit`s back to front, `$HOME/.cache/apertar-prores/`, write only when changed with `settingsFile::atomicWrite` |
| A recorder holds a camera buffer and gives it back | ProRes `[this, request, cachedFd]{ ... requeueRequest(request); }` `CC:7419-7425@upstream-1.6.0`; H.264 `CC:7456-7465@upstream-1.6.0`; `PreviewJob::release` `CC:3937@upstream-1.6.0`; audio observed after the hand-over `CC:7428-7430@upstream-1.6.0` | One `std::function<void()>` per frame; the recorder never sees a `libcamera::Request` |
| A list the WebUI fetches once | `state.presetLibrary` `WCP:7439@upstream-1.6.0`, `state.mediaLibraryPayload` `WCP:7674@upstream-1.6.0`; resolutions as JS arrays `WCP:5112-5121`, `5249-5290@upstream-1.6.0` | Fetched lists live in `state`; resolution lists are hand-written per sensor |
| An unvalidated driver feature | `experimental_modes` default off, `imx283.c:269` (same driver) | Opt-in module parameter |

## The target

Who owns what:

- **The probe owns "what this driver has".** It runs once at the first configure (`CC:7334`), on every driver, and tries every table row of the class plus the original driver's two 1.85:1 rows. Each row the driver accepts is kept. Both UIs and every lookup follow from it.
- **`CameraController` owns the mapping.** In `imx585ModeForResolution` (the IMX585 step of the sanitiser), a 1.85:1 request becomes the height the probe found *in that class*. Without the probe, the request stays as it is. It is the upstream alias shape (`isImx585LowResolutionAlias`), done at use. Saved files keep what the operator chose until the next save writes the effective value, the same as today for every other sanitised field.
- **Code owns the limits.** `min(table, probe)` and 1.6.0's lossless limits apply on every driver. A driver does not report whether the storage path or the encoder keeps up. So "the original driver gets 1.6.0's limits" holds by default, and the same is true for the port driver until the owner raises the limits. The owner's rig raises them with bench knobs set in the Core unit's environment. Where that environment lives belongs to the storage-settings theme.
- **`camera_settings.conf` owns the ladder**, as three camera-wide keys. They are written by the persister and carried across format profiles like `tuning_file`. `set_mode_ladder` commits through `applySettingsLocked`, so it gets the persist and the `settings` event like every other setter.

| Item | Before (port) | After | Set by | Reaches |
| --- | --- | --- | --- | --- |
| 1.85:1 size | rewritten to 2072/1036 on load, save, set, preset, ladder | the height the probe found in the class (2072 or 2076, 1036 or 1038); the request unchanged if the probe did not run | `set_resolution`, presets, ladder rungs; mapped in `imx585ModeForResolution` | `width`/`height` in `settingsBody`/`settingsEvent`/web state (fields unchanged); WebUI alias entry removed |
| IMX585 rows | 4 tables copied from one driver | same tables plus `3840x2076` and `1920x1038b` in S12 and S10; the probe keeps what the driver accepts | code | `list_sensor_modes` (adds `active_width`, `active_height`) -> WebUI pills |
| Exact-mode check | every colour config; crop must be native-pixel | explicit configs only; skipped when the driver's crop equals the output size (the rule `binningFromProperties` uses, `CC:7104-7110`) | - | journal |
| Auto fallback | none for colour IMX585 | upstream clause back: IMX585 3840-wide crops | - | journal |
| fps ceiling | probe alone; `APERTAR_FPS_LIMIT=table`; `APERTAR_IMX283_PROBE_FPS` | `min(table, probe)`; `APERTAR_FPS_LIMIT=probe` = probe alone (every sensor) | env, read at use | `fps_max` |
| Lossless ISO / auto ISO / IMX585 fps | 1600 / kept on IMX585 / mode max | 800 / off / 30; `APERTAR_LOSSLESS_MAX_ISO`, `APERTAR_LOSSLESS_AUTO_ISO=1`, `APERTAR_LOSSLESS_FPS_LIMIT` raise them (fps within the mode maximum) | env, read at use, printed on the `recording clip:` line | `iso_max`, `fps_max`, `iso`, `iso_auto` |
| Mode ladder | `mode_ladder.conf`, own parser and writer, `modeLadder_` | keys `mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_resolutions` in every block of `camera_settings.conf`; `mode_ladder.conf` read by the loader only while the new keys are absent | `set_mode_ladder` | `ladder_*` fields unchanged; `get_mode_ladder` unchanged |
| Preview tuning without TDN | `TuningTdnStrip.hpp`, own parser, own writer, sidecar | `makePreviewTuning(source, destination, error)` in `src/color/ProresIspProfile.cpp`; `$HOME/.cache/apertar-prores/<stem>_notdn.json`, written only when changed | `set_preview_tdn` (unchanged) | journal line unchanged |
| DNG request release | set-once `setRequestRelease`, `setFrameQueued` | `PendingCopy::release` and `PendingCopy::written` closures built per frame in the raw frame handler; hold limit passed to `startAtFolder` | - | - |
| WebUI IMX585 pills | ladder pool (`get_mode_ladder`) | `list_sensor_modes`, fetched once per sensor into `state.sensorModes`; JS tables stay as the fallback | - | WebUI |
| imx585 driver | 2072/1036 at top 44 | 2076/1038 at top 40 (VST 52), every class (owner decision 2) | - | 1.6.0 Core works unchanged |
| imx283 `crop_vmax` | default 1 | default 0 | modprobe | Core table = probe |

What a stock camera sees after the series: the original driver, no env knobs, a 1.6.0 `camera_settings.conf`. The probe finds 3840x2076 and 1920x1038. A saved 3840x2076 stays 3840x2076. 1080p binned configures, because its crop equals the output. 4K offers 30 fps. Lossless keeps ISO 800, manual ISO and 30 fps. No `mode_ladder.conf` exists, so the ladder is off. The touch UI's 1.6.0 lists match the driver. This is 1.6.0 behaviour.

What the owner's CM5 sees: the cinemate-port driver (or the D5-1 driver) and the four knobs in the unit environment. Everything is as today. The one difference: a saved 1.85:1 size follows the driver installed.

## Commit plan

All Core commits go in `/home/user/wt/core-work` on the improvement branch. "Check here" always includes `check_core.sh <tree> <tag> both tests`, which builds with and without libcamera and runs the host tests. It also includes `smoke_core.sh` on old and new binaries, diffed, which proves every 1.6.0 reply field is still there with the same type. Only extra checks are listed per commit. The order keeps the owner's camera working after each commit. The stock camera works from commit 4 on.

**1. `camera: the IMX585 tables also list the original driver's 1.85:1 sizes`**
- Repo: Core. Files: `src/camera/Imx585Modes.hpp` (`kS12Modes`, `kS10Modes`, the counts comment), `tools/imx585_modes_test.cpp`.
- Adds `{ 3840, 2076, false }` and `{ 1920, 1038, true }` to S12 and S10. The probe loop (`CC:7171`) then tries them by itself. Test: counts 62 -> 64, `find(S12, 3840, 2076)` and `find(S10, 1920, 1038)` exist, binned flag right.
- Take along CC-3-F11: in the probe, `tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585` replaces the Model substring (`CC:7152-7158`). Take along Driver-imx585-F8: one journal line per advertised size that no table row covers.
- Lines: -8 / +16.
- Check here: host test. Pi: `journalctl -u apertar-core -b | grep 'sensor mode:'`. The original driver lists `3840x2076` and `1920x1038`; the port driver does not, and nothing else changes.
- Depends: none. Merges beside the H1 interim fix (it edits `kH12Modes` and test line 20; this commit edits S12/S10 and lines 18-19).

**2. `camera: a 1.85:1 size follows the height the driver has`**
- Repo: Core. `CC`: delete `migratedImx585CropResolution` and `migrateImx585LadderRungs` (`CC:441-462`, comment included). Delete their calls at `CC:703`, `CC:10514`, `CC:10648`, `CC:11060`, `CC:12663`. `imx585ModeForResolution(cls, requested)` (`CC:512`) gains a few lines: for 3840x2072/2076 and 1920x1036/1038, return the row of the pair whose transport the probe holds for this class (`bitDepthOf(cls)`, `clearHdrClass(cls)`). If the probe holds neither, return the requested row. Move the `probedSensorModes` declarations (`CC:3307-3310`) above it. `isImx585LegacyCropResolution` (`CC:497-509`) lists 2076 and 1038 again, so `validateResolution` and the clamp accept them for every sensor, as 1.6.0 did (`CC:385-396@upstream-1.6.0`).
- `WCP:9085`: drop the `"3840x2076"` and `"1920x1038"` alias entries, so the page shows what Core reports. `README.md:80`: one line, "IMX585 1.85:1 is 3840x2076 / 1920x1038 or 3840x2072 / 1920x1036, whichever the driver offers."
- Lines: -34 / +24.
- Check here: in `--simulate` (sensor Unknown), `set_resolution 3840x2076` -> `get_state` width/height 3840x2076; restart; the file keeps 2076. `set_resolution 3840x2072` round-trips too.
- Pi, port driver: a `camera_settings.conf` with `resolution=3840x2076` starts at 3840x2072 (`ApertarCore camera configured:` line).
- Depends: 1.

**3. `camera: the IMX585 exact-mode check accepts a driver that reports its crop as the output size`**
- Repo: Core. `CC:8485-8530`: the block runs only when `useExplicitSensorConfig`. The `ScalerCropMaximum` test is skipped when the crop size equals the configured raw size: such a driver gives no window, so there is nothing to compare. Comment: one line of why.
- Lines: -3 / +6.
- Check here: both builds. Pi, original driver: Core starts at 1920x1080, and the journal has no `adjusted by the driver (scaler crop maximum`. Port driver: 1920x1080 still checked and configured.
- Depends: none. This is the commit that lets a stock camera start at all (probable defect, see "Risks").

**4. `camera: colour IMX585 3840-wide crops fall back to the automatic sensor configuration again`**
- Repo: Core. `CC:8295-8296`: add `|| (sensorFamily_ == SensorFamily::Imx585 && isImx585Raw12CropResolution(sanitized.resolution))`. Restore the helper as upstream's list (`CC:385-396@upstream-1.6.0`) plus 2072. With commit 3, the exact-mode refusal no longer blocks the auto try.
- Lines: -1 / +16.
- Check here: both builds. Pi: `APERTAR_SENSOR_PROBE=0` on the port driver, then `set_resolution 3840x2076`. The camera configures through `sensorConfig=auto` and records the software crop, as 1.6.0 did.
- Depends: 3.

**5. `camera: the fps ceiling is the lower of Core's table and the probe again`**
- Repo: Core. In `CC:3389-3423` the ceiling becomes `probed ? (probeOnly ? *probed : std::min(table, *probed)) : table`, with `probeOnly` = `APERTAR_FPS_LIMIT` equal to `probe`, read at use.
- Deleted: `fpsLimitTableOnly`, `imx283ProbeFpsOnly` and `APERTAR_IMX283_PROBE_FPS` (IMX283 follows the same rule, and its table is the crop_vmax=0 floor `CC:3333-3337`). Also deleted: the dead `backendMaximumFps` (`CC:3426-3434`) and its wrapper at `CC:3470`, `CC:3488-3490`, `CC:8636-8641`, plus the stale comment at `CC:3378`. In `FpsCeiling.hpp`, `resolveSensorMaxFps` and `applyBackendCap` go, with their test lines.
- Lines: -55 / +10.
- Check here: host tests (fps_ceiling_test loses two cases). Pi, no env: `get_state` at 3840x2160 12-bit shows `fps_max` 30. With `APERTAR_FPS_LIMIT=probe` in the unit environment: 60.
- Depends: the owner adds `APERTAR_FPS_LIMIT=probe` to the unit before deploying (storage-settings theme says where). The sanitised fps is saved, so a 4K 50 fps setting saved without the knob comes back as 30. The preroll theme owns `prerollMaximumFps`; this commit only removes the wrapper there.

**6. `camera: lossless cDNG keeps ISO 800, manual ISO and the IMX585 30 fps unless a bench knob raises them`**
- Repo: Core. `CC:3098-3170`: `kLosslessMaxIso` becomes `unsignedEnvValue("APERTAR_LOSSLESS_MAX_ISO", 800, 100, 51200)` at use. `isoAuto = false` except on the IMX585 with `boolEnvValue("APERTAR_LOSSLESS_AUTO_ISO", false)`. The IMX585 fps becomes `min(modeMaximumFps, unsignedEnvValue("APERTAR_LOSSLESS_FPS_LIMIT", 30, 1, 280))`. `maximumIsoForSettings` uses the same cap. The three effective values go on the `recording clip:` line (`CC:4392`).
- Deleted: `losslessFpsOverride`, `FpsCeiling.hpp`, `tools/fps_ceiling_test.cpp` (16 host tests remain), and the history comments ("on Patrik's request", "Patrik, 2026-10-28").
- Lines: -100 / +14.
- Check here: host tests; in `--simulate`, the `iso_max` field is present and numeric. Pi, no env: lossless at 4K has `iso_max` 800, `iso_auto` false and fps 30. With the owner's three knobs: today's values.
- Depends: 5 (same file area). The owner adds the knobs first.

**7. `camera: the preview tuning without temporal denoise is derived with libyaml, beside the ProRes tuning`**
- Repo: Core. `src/color/ProresIspProfile.cpp` gains `bool makePreviewTuning(const std::string &source, std::string &destination, std::string &error)`, declared in its header. It reuses `Document`, `member`, `algorithm` and `Edit`. For `rpi.denoise` (each mode mapping when it has `normal`, else the node itself), any mapping holding `tdn` is replaced by its other pairs, copied by byte range and joined with `,`. No comma surgery is needed (KB `V-F6.md:36`). The edits run back to front, through the existing `byteIndex`. It writes `$HOME/.cache/apertar-prores/<stem>_notdn.json` with `settingsFile::atomicWrite` only when the text changed. A source without `tdn` returns the source. `loadablePath` (`CC:7311-7321`) calls it and keeps the fall-back-to-source rule and the journal note.
- `tools/tuning_tdn_strip_test.cpp`: for every `libcamera/src/ipa/rpi/pisp/data/*.json`, the new output parses with libyaml, has no `tdn` under `rpi.denoise`, and equals `stripTdn`'s output member by member. Do NOT use the pipeline's `disable_tdn` (it stalls the back end, `pisp.cpp:1659-1663@6b0b49f`).
- Lines: -12 / +70.
- Check here: host test against the pisp data files; both builds. Pi: the journal shows `preview_tdn=off active=/home/pi/.cache/apertar-prores/<stem>_notdn.json`. libcamera starts without a tuning error. 4K Clear HDR 16-bit preview fps is as before. A ProRes Log take still starts.
- Depends: the parallel branch that limits the strip to raw formats (already in this tree, `CC:7309`).

**8. `camera: the TuningTdnStrip header goes`**
- Repo: Core. Delete `src/camera/TuningTdnStrip.hpp` and its include (`CC:20`). The test keeps only the libyaml checks of commit 7; its file name stays, so `check_core.sh` still links libyaml. The old cache `$HOME/.cache/apertar-core/tuning/` is no longer used and is left on disk.
- Lines: -500 / +5.
- Check here: host tests, both builds. Pi: nothing new.
- Depends: 7.

**9. `camera: camera_settings.conf holds the mode ladder`**
- Repo: Core.
- `include/apertar/core/Types.hpp`: `ladderEnabled` (today runtime, `:185`) becomes persisted. Add `bool modeLadderRampReady = false;` and `std::string modeLadderResolutions;`.
- `CC` loader (next to `tuning_file`, `CC:865`): three `else if` keys. After the loop, if none of them was read and `mode_ladder.conf` exists, read it with `ladder::parseFile` (the `wb_locked` take-over shape).
- Writer (`CC:972`): three lines. Carry block (`CC:11343-11372`): three fields.
- `setModeLadder` (`CC:11044-11101`): writes the three fields into `next` and commits with `applySettingsLocked` (persist and event). `saveModeLadderLocked` (`CC:10939-10945`, `CCH:188`) and `ladder::fileText` (`ModeLadder.hpp:316-324`, "T34" header) are deleted.
- `modeLadderPath` becomes `persistedSettingsPath().parent_path() / "mode_ladder.conf"` (X-knobs-14). The constructor sets `modeLadder_` from `settings_` instead of reading the file (`CC:10509-10515`).
- The old file is never written again. It is read at each start until the first save puts the keys in `camera_settings.conf`.
- Lines: -45 / +40.
- Check here, in `--simulate`: (a) put a `mode_ladder.conf` in the sim HOME, start, and `get_mode_ladder` shows it; change any setting, and `camera_settings.conf` has `mode_ladder_resolutions=` with the same text; restart without the old file and the ladder is the same. (b) `set_mode_ladder` persists after a restart. (c) A cDNG -> H.264 -> cDNG switch keeps the ladder.
- Pi: the owner's ladder is unchanged after the update (`get_mode_ladder` before and after, diffed).
- Depends: none in this theme. Storage-settings theme: same file and same carry block (merge order).

**10. `camera: the ladder is read from the settings, not from a second copy`**
- Repo: Core. Replace `modeLadder_` (`CCH:248`, 29 uses in `CC:10860-11100`) with `ladder::Ladder ladderOf(const CaptureSettings &)` in `ModeLadder.hpp`: it parses `modeLadderResolutions` (`parseRungs`) and takes the two flags. Each Locked function reads the ladder of the settings it is given (`base`, `next`, `out`).
- Lines: -40 / +30.
- Check here: as commit 9, plus `get_mode_ladder` diffed before and after on the sim.
- Pi: a ladder take with Speed Ramp chooses the same rungs as before.
- Depends: 9.

**11. `camera: the DNG copy worker gives each request back through its own closure`**
- Repo: Core. `DngRecordingQueue::PendingCopy` (`CC:5032-5042`): `request` is replaced by `std::function<void()> release` and `std::function<void()> written`.
- The raw frame handler (`CC:9498-9516`) builds `release = [this, request]{ std::shared_lock lock(sessionSettingsMutex_); if (running_.load()) requeueRequest(request); }`. A one-line comment says why: requeue reads session settings, and the completion callback holds this lock for it. It also builds `written = [this, timestampUs, frameDurationUs]{ audioRecorder_.observeVideoFrame(...); }`.
- The copy worker calls them where it called `releaseHeldRequest` (`CC:5151-5162`) and `frameQueued_` (`CC:5139-5147`). The hold limit (buffers-2) becomes a `startAtFolder` argument.
- Deleted: `setRequestRelease`, `setFrameQueued`, `releaseRequest_`, `frameQueued_` (`CC:5050-5063`, `CC:5607-5609`, `CC:8731-8739`). `enqueueCopy` no longer refuses on a missing callback (`CC:5070`).
- Lines: -45 / +25.
- Check here: both builds; `frame_path_test` and `buffer_budget_test` still pass.
- Pi: a 4K Clear HDR 16-bit take at 30 fps and a 4K 12-bit lossless take give the same `drop[copy-slot]` counts as before. Stop during a full queue does not hang. WAV length equals clip length within one frame.
- Depends: none. If the owner picks option B of decision 6, `written` goes and audio is observed after `enqueueCopy` (the ProRes shape).

**12. `core, web: the IMX585 resolution pills come from the sensor modes, not from the Mode Ladder`**
- Repo: Core.
- `CameraController::SensorMode` gains `Resolution active{}`, filled by the probe: the table row for IMX585, else the size. `list_sensor_modes` (`App:12741`) adds `active_width` and `active_height`.
- `WCP`: `imx585ClassRows` (`WCP:8955-8970`) reads `state.sensorModes`, fetched once with `sendCommand({cmd:"list_sensor_modes"})` when the snapshot's sensor name first appears or changes (the `state.presetLibrary` shape). The JS tables stay as the fallback. `get_mode_ladder`'s pool stays for the ladder editor only.
- Lines: -10 / +30.
- Check here: in `--simulate` the reply is empty, so the page shows the fallback (headless Chromium: pills render, no console error). A host check feeds a canned reply to the page function through the console.
- Pi: the original driver offers 3840x2076 and no 2880x2160; the port driver offers the port set.
- Depends: 1. webui-state theme: they own the WebUI's stores and poll loop; this adds one fetched list in `state`, and they may fold it into their pattern.

**13. `camera: one readout check for IMX585 and IMX283`**
- Repo: Core. CC-4-F8: one helper returns the reason a candidate was adjusted (raw size, bit depth with the PiSP COMP1 exception), used at `CC:8485-8560`. The IMX585 crop line stays sensor-specific.
- Lines: -30 / +20.
- Check here: both builds. Pi: IMX283 and IMX585 configure lines unchanged.
- Depends: 3.

**14. `camera: the 1.85:1 and ladder comments say only what holds`**
- Repo: Core. These comments shrink to one line of why or go: the "cinemate-modes, Apertar-Beta 1.6.0 driver" narration (if any is left after 2), `T34:` at `CC:403`, `// T34: the ladder owns the mode` at `CC:10644`, `ladderEnabled` "(T34)" in `Types.hpp:185`, `Imx585Modes.hpp:3,16`.
- Lines: -12 / +4.
- Check here: both builds.
- Depends: 2, 9.

**D5-1. `imx585: 1.85:1 is 3840x2076 and 1920x1038 again, at crop top 40`**
- Repo: `/home/user/imx585-v4l2-driver`. In every table that has the 1.85:1 row (`imx585.c:867`, `:918`, `:1121-1127`, `:1408-1414`, `:2168-2174`, `:2423-2429` @cd548ef): height 2072 -> 2076, top 44 -> 40. That gives VST 52, a multiple of 4. 2076 passes the `(sensor_height & 3)` rule in `imx585_program_window`. Binned output 1036 -> 1038. Enum names follow.
- `APERTAR.md:145-157` "Sizes that changed" is deleted. This also removes the 3840x2072 duplicate warning (Driver-imx585-F6, first half).
- Lines: -30 / +16.
- Check here: none (no kernel build here). Pi: `dmesg` shows no window error. `v4l2-ctl -d /dev/v4l-subdevN --list-subdev-framesizes pad=0,code=...` lists 3840x2076 and 1920x1038. Make one take per class at each size and check that row 0 and the last row are picture, not black. With unmodified 1.6.0 Core, set 1920x1038 and it records.
- Depends: Core commits 1-2 deployed on the owner's camera first. Otherwise the old port Core rewrites 2076 to 2072, which this driver no longer has.

**D2-1. `imx283: per-crop VMAX floors are off by default`**
- Repo: `/home/user/imx283-v4l2-driver`. `imx283.c:271-281`: `static bool crop_vmax;`, a one-line comment, and the `MODULE_PARM_DESC` saying "default 0". `APERTAR.md:92-113`, `:194-196`: drop the modprobe.d instruction; keep one line on how to turn the experiment on.
- Lines: -20 / +4.
- Pi: `cat /sys/module/imx283/parameters/crop_vmax` prints `N` with no modprobe.d file. Core's `fps_max` is unchanged against today's `crop_vmax=0` setup.
- Depends: Core commit 5 (the Core-side special case goes there).

Totals, Core: about -895 / +310. Drivers: -50 / +20.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| Startup sensor probe, IMX585 by table row | As on fork main `f60e301` (already the merge target). It is a free function in `CC`, its result is a file-scope vector under one mutex, and it is published through `list_sensor_modes` | It is what lets one Core serve both drivers. 1.6.0 has no probe (conventions section 5: "a data-driven sensor mode or capability table, or a mode probe" is absent) |
| IMX585 class tables (`Imx585Modes.hpp`) | Header-only, `inline`/`constexpr`, std only, one includer plus a host test (CAM-4) | 1.6.0 keeps sizes in predicates in `CC`. 190 rows in four classes do not fit predicates. The header is the smallest data form, and the probe makes it advisory: a row the driver lacks does nothing |
| `APERTAR_FPS_LIMIT=probe`, `APERTAR_LOSSLESS_*` | R8 bench knobs, read at use, bounded, printed on the take line | They are the owner's measured-but-unproven limits. Upstream raises a limit by editing the table once takes prove it |
| Mode ladder itself | Camera-wide keys in `camera_settings.conf` (after commits 9-10); its reply `get_mode_ladder` is nested JSON | The feature has no upstream counterpart. Its store now has the upstream shape. The nested reply is the command-plane theme's question |
| Preview without temporal denoise | A derived tuning, as ProRes Log | The feature is new; the mechanism is upstream's |
| Per-frame `written` closure for audio | A second `std::function<void()>` on the DNG job | Upstream observes audio at hand-over (ProRes). The port observes at write-queue acceptance on purpose (decision 6) |

## For the owner

1. **How does your rig get today's limits back?**
   - Options: (A) four env knobs in the Core unit's environment (`APERTAR_FPS_LIMIT=probe`, `APERTAR_LOSSLESS_MAX_ISO=1600`, `APERTAR_LOSSLESS_AUTO_ISO=1`, `APERTAR_LOSSLESS_FPS_LIMIT=60`). (B) camera-wide keys in `camera_settings.conf` with no UI. (C) a WebUI switch.
   - Recommendation: A. It is R8, the original developer sees no new setting, and you set it once. Cost: set it before deploying commits 5-6, and re-pick a 4K fps above 30 if it was saved clamped. Long term, raise the IMX585 table rows (`CC:3373-3381`) in a commit with counted takes, and the knob goes.
2. **Should the cinemate-port imx585 driver keep advertising the old sizes?**
   - Options: (A) 2076/1038 at top 40 replace 2072/1036 (D5-1). (B) advertise both sizes. (C) keep 2072/1036 and state that driver and Core release together.
   - Recommendation: A. The driver is installed apart from Core (`README.md` "not installed"), so a driver update must not break the 1.6.0 Core in the field, which has no fallback for 1920x1038. A is 4 rows (8 lines) off centre by 2 sensor rows (0.1 %). Its ratio, 1.850, is closer to 1.85:1 than 2072's 1.853. B doubles a mode, and the WebUI shows one 1.85:1 pill either way. C ties the releases. Core works with all three after commits 1-2.
   - Cost: one Pi take per size and class (VST 52 is unmeasured). Your saved 2072/1036 settings become 2076/1038 on the next save.
3. **Ladder store: `camera_settings.conf` or its own file?**
   - Options: (A) camera-wide keys (commits 9-10). (B) keep `mode_ladder.conf`, fix only the path copy and the "T34" header (X-knobs-14 says a separate file is acceptable).
   - Recommendation: A. Upstream keeps camera settings in one Core-written file, and camera-wide values repeat in every profile block (`tuning_file`), so no new block kind is needed. A also moves the write off `mutex_` onto the persister.
   - Cost: two commits, and one take-over path that stays as long as old cameras exist.
4. **imx283 `crop_vmax`: default off or delete?**
   - Options: (A) default 0, keep the parameter. (B) delete the parameter, the `crop_min_VMAX` field and the macro argument until measured.
   - Recommendation: A now, B if no measurement is planned. Cost of A: dead-by-default code in the driver.
5. **Lossless ISO 1600 on the IMX585 only?**
   - Options: (A) default 800 everywhere with a knob (commit 6). (B) default 1600 for the IMX585 only, in its own commit with the take numbers, for the original developer to accept.
   - Recommendation: A, then B once you have counted 4K 25/30 lossless takes at ISO 1600 on more than one board. Cost of B: one argued commit.
6. **When does the WAV learn about a frame?**
   - Options: (A) when the write queue took it (today; a second per-frame closure). (B) at hand-over to the copy worker, as ProRes does.
   - Recommendation: A, since it keeps your measured sync. Cost: one extra closure per frame. B deletes about 8 more lines, and a take that ends with drops may have up to the queue depth of extra audio.

## Risks and what was not determined

- **Binned modes on the original driver** are refused by the port Core today. This is probable: the code path is confirmed (`CC:8510-8517`, `imx585.c:803-808,2129@e5b74d3`, `pipeline_base.cpp:568@6b0b49f`), but it was not run. The journal line `adjusted by the driver (scaler crop maximum (0, 0)/1920x1080)` on a stock-driver Pi settles it. Commit 3 fixes it either way.
- **VST 52** (D5-1) has no take. Check the first and last rows of a 3840x2076 frame.
- **Probe time** rises by 4 configures (2 rows x 2 SDR classes). Pi 4 / VC4 never ran the table probe (X-board-support-14). The `sensor probe: N modes in M ms` line on a Pi 4 settles it.
- **Deploy order on the owner's camera**: env knobs before commits 5-6; Core commits 1-2 before driver D5-1.
- **Sanitised values are saved.** A setting clamped while a knob was missing stays clamped after the knob is set. Re-pick it.
- **Parallel branches.** The H1 interim fix edits `kH12Modes` and `imx585_modes_test.cpp` line 20 (merge beside commit 1). The D2 fix ("4K Clear HDR is not 4K") changes how Clear HDR picks its row and may call `imx585ModeForResolution`; rebase commit 2 on it. Preroll owns `prerollMaximumFps` (commit 5 touches one call). Storage-settings owns the carry block and where env knobs live (commits 5, 6, 9).
- **Touch UI.** Its 1.6.0 lists (`CameraPage.qml:418`, `SettingsPage.qml:161`) match the original driver. On the port driver, Core maps a 2076 pick to 2072, and the current value is then not in the list (X-state-consistency-3). The touch-ui theme owns the mode list.
- **libyaml marks on JSON keys** (commit 7): the key's byte range must include its quotes. The host test against the pisp data files settles it before commit 8 deletes the old path.
- **Not determined:** whether the original driver advertises its crops in 10-bit (the probe decides at run time, so the design does not depend on it). Also not determined: whether 4K 12-bit at 60 fps records without drops on a Pi 5 with a stock NVMe. That is the measurement the knobs stand in for.
- **Out of this theme**: preview TDN default off for RAW preview (X-stock-behaviour-6, CC-3-F7), the hidden 960/1024 families (Driver-imx585-F4), and `setResolution` refusing sizes the class lacks (CC-5-F6).

## Findings covered

| Finding | Commit |
| --- | --- |
| CC-1-F1 | 1, 2 |
| Driver-imx585-F1 | D5-1 (Core side: 1, 2) |
| X-stock-behaviour-4 | 1, 2, 4 |
| CC-4-F2 | 3, 4 |
| CC-2-F3 | 6 |
| Camera-headers-F3 | 6 |
| Camera-headers-F4 | 5 |
| X-stock-behaviour-3 | 5, 6 |
| Camera-headers-F1 | 7, 8 |
| Camera-headers-F5 | 9, 10 |
| CC-4-F1 | 11 |
| X-state-consistency-3 | partly: Core and WebUI by 2 and 12; the touch UI lists are not covered (touch-ui theme owns the mode list) |
| WCP-04-F1 | 12 |
| Driver-imx283-F2 | D2-1 |
| X-knobs-14 | 9 |
| X-knobs-17 | 5, D2-1 |
| Taken along: CC-1-F5 | 9 |
| CC-3-F11 | 1 |
| Driver-imx585-F8 | 1 (log line); the host test parsing `imx585.c` is not covered (new tooling, no precedent) |
| CC-4-F4, CC-2-F10 | 5 |
| Camera-headers-F16 | 6 |
| CC-2-F11, Camera-headers-F11 | 5, 6 for the fps and lossless knobs; `minModeWidth` parsing not covered (belongs with Driver-imx585-F4) |
| X-stock-behaviour-9 | 6 |
| X-stock-behaviour-10 | 6 (Core default back to manual ISO); `iso_auto_allowed` for the UIs not covered (UI themes) |
| WCP-04-F12 | 2 (alias removed), 12 |
| CC-4-F8 | 13 |
| Driver-imx585-F6 | D5-1 removes the duplicate-size warning; the four copies of the window predicate are not covered (driver slop pass) |
| CC-1-F7, Camera-headers-F12 | 14 and 9 (ladder file header) for this theme's lines; the rest belongs to the slop pass |
| Camera-headers-F2 | not covered: done on a parallel branch (strip limited to raw formats) |
