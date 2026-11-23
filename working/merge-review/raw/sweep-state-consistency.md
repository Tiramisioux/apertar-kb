# Sweep X5: hand-copied truths (state fields, option lists, presets)

Refs: port Core `cinemate-port` `01f170c`, port UI `cinemate-port` `7ea9afc`, upstream `upstream-1.6.0` (`/home/user/wt/*-upstream`), fork main `/home/user/wt/core-main`.
Method: key lists pulled by script from `settingsBody` (App:313), `settingsEvent` (CC:163), `buildWebStateJson` (App:9298), socket `get_state` (App:12932), preset writer `buildCurrentPresetPayload` (App:7697), preset reader `apply_preset` (App:14176), WebUI `buildPresetApplyPayload` (WCP:19018); readers by grep in `Apertar-UI/src/ApertarControlBridge.cpp` and `WebControlPage.cpp`. Abbreviations as in BRIEF.md. All claims confirmed unless marked.

## 1. Field table: state keys the port added

Columns: B = `settingsBody` (get_state and every `set_*` reply), E = `settings` event, W = web state, G = extra member of socket `get_state`, UI = read in `ApertarControlBridge.cpp`, Web = references in WCP JS. "n/a" = not a camera setting.

| Key | B | E | W | G | UI | Web | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| conform_fps | Y | Y | Y | | - | - | No reader, no control in either UI (only socket and presets). X-10 |
| iso_actual | Y | Y (always 0) | Y | | Y | Y | Event value never filled. X-9 |
| iso_max | Y | Y | Y | | Y | Y | single source, see section 2 |
| fps_max | Y | Y | Y | | Y | Y | single source, see section 2 |
| fps_take_max | Y | Y | Y | | **-** | Y | Touch UI and buttons ignore it. X-3 |
| ladder_active | Y | Y | Y | | Y | Y | |
| ladder_resolution, ladder_ramp_ready, ladder_enabled, ladder_count, ladder_text, ladder_tops | Y | Y | Y | | - | Y | Ladder editor is WebUI-only (by design). `ladder_tops` printed by two helpers. X-11 |
| ladder_override | Y | Y | Y | | - | - | No reader. X-10 |
| iso_auto_after_clear_hdr, wb_auto_after_clear_hdr | Y | Y | Y | | Y | Y | |
| cdng_log, cdng_log_bits, cdng_log_available, cdng_log_applied | Y | Y | Y | | Y | Y | |
| clear_hdr (fork main) | Y | Y | Y | | Y | Y | |
| hdr_threshold_high/low, hdr_blend, hdr_gain_adder (fork main) | Y | Y | Y | | - | - | No reader, no control. X-10 |
| fps_phase_lock | Y | Y | Y | | - | Y | WebUI-only control |
| preview_tdn | Y | Y | Y | | - | Y | WebUI-only control; not in presets. X-14 |
| fps_speed_ramp, fps_speed_ramp_keep_exposure | Y | Y | Y | | Y | Y | |
| fps_speed_ramp_stretch_audio, fps_speed_ramp_after | Y | Y | Y | | - | Y | Speed-ramp card is WebUI-only |
| clip_name_template, clip_name_example | Y | Y | Y | | Y | Y | |
| buffer_setting, buffer_note, buffer_safety_stop, buffer_stop_percent, buffer_flush_discarded, storage_preroll_active/auto/auto_env/fps/last, frames_per_folder(_env), clip_merge_enabled, clip_merge_env_off (`bufferSettingMembers` App:252) | Y | **-** | Y | | partly | Y | In settingsBody but not the settings event; also in the `buffer` event (App:10839). X-7 |
| recording_fault | | | Y | Y | - | - | No reader. X-10 |
| media_state | | | Y | Y (**twice**) | Y | Y | Duplicate key in get_state. X-8 |
| media_alive | | | Y | Y | Y | Y | `media` event calls the same facts `state` / `mounted` (App:10827). Upstream precedent: `recording` event `active` vs state `recording` |
| recording_dropped_frames | | | Y | Y | Y | - | also rides on `buffer` event |
| controls_errors, controls_warnings | | | Y | Y | Y | - | `controls` event names them `errors`/`warnings` (App:12346) |
| sensor_mono | | | Y | Y | - | Y | |
| sensor_binning, sensor_binning_source, sensor_crop | | | Y | Y | - | - | No reader. X-10 |
| clip_merge_pending/active/last | | | Y | Y | - | Y | |
| fps_phase_lock_active/err_us/dur_us/pushes/saturated | | | Y | | - | - | No reader. X-10 |
| tuning_file_active | | | Y | | - | - | No reader. X-10 |
| media_device/fstype/class/profile | | | Y | | - | - | No reader. X-10 |
| media_trim_enabled, media_trim_env_off | | | Y | | - | Y | WebUI-only control |
| recording_frame_enabled, frame_buffer_bar_enabled, recording_red_timecode_enabled, audio_recorded_outline_enabled (`ui` object) | n/a | | Y | | SettingsBridge reads UI.conf | Y | |

Checks that passed:

- Camera keys of B and E are identical (74 keys each, script diff; E adds only `event`). Every camera key of B is also in W. Names agree. Types agree (bools as `true/false`, `fps`/`fps_max`/`conform_fps` with 3 decimals in all three).
- Persisted keys: `writeCaptureSettings` and `loadPersistedCaptureSettings` agree (50 written, all read; reader also takes legacy `wb_locked`). 17 keys new versus upstream.
- `emitSettingsEventLocked` (CC:12856) refreshes `isoMax`, `fpsMax`, ladder fields, clip name example and log state before each event, so these follow changes by event, not only by poll.
- Live values (`iso_actual`, `wb_actual_*`) reach the touch UI by poll only; the port shortened the poll to 1 s while auto ISO/WB is on (`kLiveValuePollIntervalMs`, UI ApertarControlBridge.cpp:20, :1014). Upstream polls every 30 s (ui-upstream ApertarControlBridge.cpp:18).

KB drift: `llm/core-map.md` §4.4 says the three settings copies hold "the same 42 keys"; the port's copies hold 74, and settingsBody now also carries 14 non-camera keys (X-7). §4.5 says the Clear HDR ISO cap still has to be copied into the UI first-run template: the port removed that template from the UI (`c9d841f`, `DisplayConfigBridge.cpp` -297 lines), so Core's template is the only one.

## 2. List table: option lists and limits

| Truth | Copies in the port | Agree? |
| --- | --- | --- |
| ISO built-in steps | Core `builtInIsoSteps` App (100..51200, 10 values); QML `builtInIsoSteps` CameraPage.qml:519; WCP `isoOptions` :6498 (fallback for an older Core, else `ui.iso_steps`) | Yes |
| Shutter angle built-in steps | Core `builtInShutterAngleSteps`; QML :520; WCP `shutterOptions` :6499 | Yes (20 values) |
| WB built-in steps | Core `builtInWhiteBalanceSteps`; QML :521; WCP `whiteBalanceOptions` :6501 | Yes (19 values) |
| FPS built-in steps | Core `builtInFpsSteps` App:1398 (IMX585 24..120 7 values; IMX477/577 24..100 6; other 24..60 5); QML `fpsOptionEntries` CameraPage.qml:923 (IMX477 27 values to 280; IMX577 6; other incl. IMX585 5); WCP `fpsPresets` :6497 (fallback only) | **No**. X-4 |
| UI.conf value-step limits | `readSharedUiSettings` App:2159-2166 and `set_value_steps` App:14119-14122 (ISO 50-51200, angle 1-360, fps 1-280, WB 1500-12000) | Yes |
| ISO ceiling (Clear HDR, lossless) | Core `maximumIsoForSettings` CC:3162 -> `iso_max`; consumers WCP :8661/:8674, QML :526/:535, ExternalMonitorWindow.qml:103, buttons `pcfIsoOptions` App | Yes; QML keeps a 1600 fallback (:526). X-5 |
| Clear HDR ISO limits 720/1585 | `[camera] clear_hdr_iso_max_*` read CC:2976; Core template App:5078-5079 | Yes (one copy; UI template gone) |
| FPS ceiling | Core `maximumFpsForSettings` CC:3495 (mode table + IMX477 uncompressed + lossless) -> `fps_max`; old copies QML `maximumSupportedFpsForResolution` :778, `imx477MaximumUncompressedFpsForResolution` :750, fallback in `fpsCeiling` :907-917; WCP `maximumSupportedFpsForSnapshot` :7404, `imx477MaximumUncompressedFps` :7333 and caps re-applied after `fps_max` :7490-7509; App `maximumPcfFpsForSettings` :1323 | Values agree today; old copies remain and are still edited (UI `d1efb67`). X-5 |
| FPS ceiling in a ladder take | Core clamps to rung ceiling CC:10715-10719 -> `fps_take_max`; WCP uses it :7485; QML and buttons do not | **No**. X-3 |
| IMX585 sizes | Core `src/camera/Imx585Modes.hpp` (`caa0153`); WCP hand copy `imx585ClassModes` :8915-8920 (fallback until the ladder pool arrives); QML `imx585Raw12ResolutionOptions` CameraPage.qml:418 and SettingsPage.qml:161 = upstream list unchanged; `list_sensor_modes` has no consumer | **No**. X-6 |
| Raw bit depths | Core `supportedRawBitDepthForSensor` CC (IMX585 Clear HDR 12/16, else 10/12; IMX477/577 8/10/12); WCP `rawBitDepthOptionEnabled`; QML SettingsPage.qml:658-672; UI `formatRawBitDepthValue` (16 added) | Yes |
| cDNG Log values | `toString(CdngLog)` Types.hpp:326 (`off`/`auto`); `cdngLogFromString` accepts on/12/10/8; UI reads `!= "off"` (ApertarControlBridge.cpp:2792); WCP :13833 | Yes |
| Speed-ramp options | command `set_fps_speed_ramp` (`shutter=angle|exposure`, `audio=real|stretch`, `after=stay|return`) App:13223; preset keys same words App:7844-7847, reader :14323-14339; state uses booleans `fps_speed_ramp_keep_exposure` / `_stretch_audio` | Yes (two vocabularies, upstream has the same split between commands and state) |
| Conform fps range | CC:696 (1-120, default 25); preset reader App:14353 (1-120) | Yes |
| Clear HDR knob ranges | preset reader App:14361-14369 (thresholds 0-4095, blend 0-7, gain adder 0-5); setters via table App:13166 | not compared in depth |
| Timecode mode in presets | `timecodeMode` (UI.conf words, upstream) and new `cameraTimecodeMode` (`free_run`/`rec_run`) App:7850, reader :14348 and :14428 | Two keys for one fact. X-13 |
| Favourites ids | Core `favoriteCandidateOrder`; WCP :`favoriteCandidateOrder`; QML SettingsPage.qml:859 | Port did not change any copy (upstream drift stays, core-map §4.4) |
| Command list (`help`) | dispatcher vs list App:12930 | Port-new `test_input` (App:12565) missing from the list. X-12. Upstream already lacks 12 |
| Button actions | `src/hardware/ActionCatalog.hpp` (new); Gpio/Pcf8574/NeoRotary4 via `normalizeButtonMapping(action, actions::canonicalAction)` (GpioInput.cpp:114, Pcf8574Input.cpp:144, NeoRotary4Input.cpp:125), Grove via `canonicalAnalogTarget` (GroveAnalogInput.cpp:128); WebUI editor reads `list_actions` (WCP:18265) | Yes: all consumers switched; no old alias table left in the drivers |
| Hardware file template | Core `defaultHardwareConfigTemplate` only; UI copy deleted `c9d841f` | Yes (port reduced a copy) |

## 3. Presets

| Setting (preset key) | Core writer App:7697+ | Core reader App:14176+ | WebUI import allow-list WCP:19028 | Touch UI writer `cameraPresetSettings` ApertarControlBridge.cpp:1254 / SettingsBridge |
| --- | --- | --- | --- | --- |
| cameraClearHdr, cameraHdrThresholdHigh/Low, cameraHdrBlend, cameraHdrGainAdder | Y | Y | Y | **-** |
| cameraCdngLog | Y | Y | Y | **-** |
| cameraFpsSpeedRamp, ...Shutter, ...Audio, ...After | Y | Y | Y | **-** |
| cameraFpsPhaseLock | Y | Y | Y | **-** |
| cameraConformFps | Y | Y | Y | **-** |
| cameraClipNameTemplate | Y | Y | Y | **-** |
| cameraTimecodeMode | Y | Y | Y | - (writes `timecodeMode` only) |
| recordingFrameEnabled, recordingRedTimecodeEnabled, audioRecordedOutlineEnabled | Y | Y | Y | Y (SettingsBridge.cpp:2170-2173, read :2262-2265) |
| frameBufferBarEnabled | Y (:7787) | Y (:14454) | **-** | Y |
| preview_tdn, media_trim (persisted) | - | - | - | - | 

Touch UI loading: `applyCameraPreset` (ApertarControlBridge.cpp:1288) forwards every `camera*` key to `apply_preset`, so a preset written by Core loads fully on the touch UI. The gap is only in the touch UI's writer. Pre-existing upstream drift (JS allow-list lacks `cameraControlsMode`, `cameraControlsOpacity`, `cameraExposureCompensation`, `cameraExposureMetering`, `dateTimeOverlayEnabled`, `photoFormat`, `photoTimelapse`) is unchanged by the port.

## 4. Findings

| Id | Severity | Title |
| --- | --- | --- |
| X-state-consistency-1 | major | Touch UI presets omit every camera setting the port added |
| X-state-consistency-2 | major | Touch UI and buttons ignore fps_take_max during a ladder take |
| X-state-consistency-3 | major | IMX585 mode table has a single source in Core, but the touch UI keeps the upstream list and the WebUI a hand copy |
| X-state-consistency-4 | minor | Touch UI built-in FPS list differs from Core's builtInFpsSteps |
| X-state-consistency-5 | minor | Old FPS/ISO ceiling copies stay beside fps_max / iso_max |
| X-state-consistency-6 | minor | WebUI import allow-list drops frameBufferBarEnabled |
| X-state-consistency-7 | minor | settingsBody carries 14 hardware-file keys the settings event lacks |
| X-state-consistency-8 | minor | settings event always sends iso_actual 0 |
| X-state-consistency-9 | minor | Published state fields with no reader in either UI |
| X-state-consistency-10 | minor | Timecode mode stored twice in presets |
| X-state-consistency-11 | nit | get_state emits media_state twice |
| X-state-consistency-12 | nit | Two array serialisers print ladder_tops with different precision |
| X-state-consistency-13 | nit | help list lacks test_input |
| X-state-consistency-14 | nit | preview_tdn persisted but not in presets |

Details are in the structured result; the key evidence:

1. `cameraPresetSettings` ApertarControlBridge.cpp:1254-1286 @cinemate-port is byte-identical to ui-upstream. Core's writer adds 14 camera keys (App:7844-7868 and the HDR knobs). Operator: a preset saved on the touch screen does not store Clear HDR, Log, speed ramp, phase lock, conform fps, clip name template or HDR knobs; loading it leaves those as they are. The same preset saved from the WebUI restores them.
2. WCP:7485 `const takeMax = snapshot.recording && snapshot.ladder_active ? fps_take_max : 0`. QML `fpsCeiling` CameraPage.qml:904-906 returns `fpsMax` only; `availablePcfFpsOptions` App uses `settings.fpsMax` only. Core clamps a take's fps to `fpsTakeMax` CC:10715-10719 and reports success. Operator: during a ladder take the touch screen or a button offers e.g. 100 fps; the take stays at the rung's ceiling.
3. `imx585Raw12ResolutionOptions` CameraPage.qml:418 and SettingsPage.qml:161 equal ui-upstream. WebUI offers 2880x2160, 2160x2160, 2976x2160, 2048x1152 ... (WCP:8915-8920, ladder pool). Operator: the touch UI cannot pick the 2K crop, 4:3 and 1:1 modes.

## Skeptic

Re-read every claim at port Core `01f170c`, port UI `7ea9afc`, `upstream-1.6.0`, fork main `f60e301`.

| Id | Verdict | Why |
| --- | --- | --- |
| 1 | stands, major | `cameraPresetSettings` ApertarControlBridge.cpp:1254-1286 is byte-identical to ui-upstream (diff empty). Core writer App:7844-7862 adds the 14 keys. Fork main Core writer had no `cameraClearHdr` either, so all 14 are port-added on one side only. Bridge already reads `clip_name_template` (:664), `fps_speed_ramp` (:1511), `fps_speed_ramp_keep_exposure` (:1599), `clear_hdr` (:1681), `timecode_mode` (:1698), `cdng_log` (:2791); not `fps_phase_lock`, `conform_fps`, `hdr_*`, ramp audio/after. |
| 2 | stands, lowered to minor | Clamp CC:10715-10719 and WCP:7484-7485 confirmed; QML `fpsCeiling` CameraPage.qml:904-906 and App:1410-1415 use `fpsMax` only. Lowered: the reply carries the clamped fps, so the screen shows the real value right after; the defect is offered values that snap back, not a wrong take. |
| 3 | stands, fix corrected | Lists at CameraPage.qml:418 and SettingsPage.qml:161 equal ui-upstream. Extra: they still offer 3840x2076 and 1920x1038, which Core migrates (CC:442-450, :10648) to 2072/1036, a value then missing from the touch list. Fix reworded: state is flat scalars upstream, so no array in get_state; `list_sensor_modes` is port-new. |
| 4 | half right, corrected | IMX477 27-value QML list vs Core 6 values is upstream drift (ui-upstream CameraPage.qml:804 vs core-upstream App:1154-1157; the upstream WebUI fallback `fpsPresets` WCP:4039 is the 27-value list too). Port-new part: Core added 100/120 for IMX585 (App:1401) and the QML fallback did not follow. |
| 5 | stands | `maximumFpsForSettings` CC:3495 = min(modeMaximumFps incl. IMX477 uncompressed, losslessMaximumFps incl. 4K 30/24, 2K 60). WCP:7490-7509 re-applies the same caps. UI d1efb67 edited the QML copy. Fix note: the QML fallback is the upstream mechanism for a Core without `fps_max`; keeping it is acceptable, editing it in parallel is not. |
| 6 | stands | Script diff of writer keys vs `allowedKeys`: port-missing = upstream-missing (7 keys, core-map 4.4) + `frameBufferBarEnabled`. Only that one is port drift. `loadPresetFromLibrary` WCP:19155-19166 is the only caller. |
| 7 | stands | `settingsBody` ends with `bufferSettingMembers()` (App:393); 14 keys counted. Event `settingsEvent` CC:163-250 has none of them. |
| 8 | stands, lowered to nit | Confirmed: `isoMeasured` only set on the copy in `settings()` CC:12586. Upstream does the same for `wb_measured`/`wb_actual_*` (core-upstream CC:159, :8572), so the port follows upstream's pattern; no UI shows a wrong value. |
| 9 | half right, corrected | No reader for the listed port keys (grep count 0 in UI src/qml and WCP). Dropped `hdr_threshold_*`, `hdr_blend`, `hdr_gain_adder`: fork main already publishes them (core-main App:202-205), not the port. Dropped "upstream carries only fields the UIs use": upstream `settingsBody` has `wb_measured`, `wb_actual_kelvin/red_gain/blue_gain` with no reader in ui-upstream or the upstream WebUI. Lowered to nit except `conform_fps`, which is a setting with no control in either UI. |
| 10 | dropped | Not duplication. Port commit 909aaa5 "the UI timecode and the file timecode are set apart": `set_timecode_mode target=ui|files|both` (App:13283-13299). `cameraTimecodeMode` is the files' mode, `timecodeMode` the UI's; the reader falls back to `timecodeMode` for old presets (App:14428-14434). The touch UI not writing `cameraTimecodeMode` is covered by 1. Whether splitting the timecode is wanted is a new-ground question for the file review of 909aaa5, not this sweep. |
| 11 | stands | App:12944 and App:12961 both write `media_state`. Both port-new (upstream has no `media_state`). |
| 12 | stands, nit | `ladderTopsJson` CC:153-161 default precision 6; `jsonNumberArray` App:486-496 precision 10. Differs only past 6 significant digits (e.g. 119.880119...). |
| 13 | stands | `test_input` dispatched App:12565, `test_output` App:12745; help App:12930 lists only `test_output`. |
| 14 | stands, widened | Also `media_trim` (camera_settings.conf, kept across format switch CC:11349 with `previewTdn`) is in no preset. Both are camera-wide switches; product decision. |

Nothing new and serious found beyond the corrections above.

## Final findings

### X-state-consistency-1 [mismatch, major, effort M] Touch UI presets omit every camera setting the port added
- where: Apertar-UI/src/ApertarControlBridge.cpp:1254-1286@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:7844-7862@cinemate-port ; Apertar-UI/src/SettingsBridge.cpp:2203-2208@cinemate-port
- detail: The touch UI writes its own preset files; camera keys come from `cameraPresetSettings`, byte-identical to ui-upstream. Core's `buildCurrentPresetPayload` (WebUI save) adds cameraFpsSpeedRamp, cameraFpsSpeedRampShutter/Audio/After, cameraClipNameTemplate, cameraFpsPhaseLock, cameraTimecodeMode, cameraConformFps, cameraClearHdr, cameraHdrThresholdHigh/Low, cameraHdrBlend, cameraHdrGainAdder, cameraCdngLog. Upstream precedent: both writers carry the same camera* set (fork main had neither with Clear HDR). Operator: a preset saved on the touch screen does not record Clear HDR, Log, speed ramp, phase lock, conform fps, file timecode or clip name template; loading it leaves current values. The same preset saved from the WebUI restores them. Loading works either way: `applyCameraPreset` (:1288) forwards every camera* key.
- fix: In ApertarControlBridge keep the missing fields from `applyCoreState` as members (it already keeps clip_name_template, fps_speed_ramp, keep_exposure, clear_hdr, timecode_mode, cdng_log; add fps_speed_ramp_stretch_audio/return, fps_phase_lock, conform_fps, hdr_*). Insert them in `cameraPresetSettings` under Core's keys and value words (angle/exposure, real/stretch, stay/return, free_run/rec_run, off/<log>).

### X-state-consistency-2 [mismatch, minor, effort S] Touch UI and hardware buttons ignore fps_take_max during a ladder take
- where: Apertar-UI/qml/CameraPage.qml:904-906@cinemate-port ; Apertar-UI/src/ApertarControlBridge.cpp:1589-1594@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:1410-1415@cinemate-port ; Apertar-Core/src/web/WebControlPage.cpp:7484-7485@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:10715-10719@cinemate-port
- detail: In a ladder take Core clamps `set_fps` to `fpsTakeMax` (the rung's ceiling) and replies ok. The WebUI cuts its list at `fps_take_max` when recording && ladder_active. The bridge never reads `fps_take_max`; `fpsCeiling` uses `fpsMax`; `availablePcfFpsOptions` uses `settings.fpsMax`. Operator: the touch picker and FPS buttons offer values above the rung (e.g. 100); the take stays at the rung maximum and the display snaps back. New ground (ladder), internal inconsistency.
- fix: Read `fps_take_max` in `applyCoreState` next to `fps_max`, expose `fpsTakeMax` on `cameraSetValuesChanged`; `fpsCeiling` uses it when recording && ladderActive && > 0, as WCP:7485. In `availablePcfFpsOptions` use `settings.fpsTakeMax` when `settings.ladderActive` and recording.

### X-state-consistency-3 [duplication, major, effort M] IMX585 mode table has one source in Core; touch UI keeps the upstream list, the WebUI a hand copy
- where: Apertar-Core/src/camera/Imx585Modes.hpp@cinemate-port ; Apertar-Core/src/web/WebControlPage.cpp:8910-8920@cinemate-port ; Apertar-UI/qml/CameraPage.qml:418,1062-1070@cinemate-port ; Apertar-UI/qml/SettingsPage.qml:161@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:442-450@cinemate-port
- detail: caa0153 moved Core's IMX585 sizes into per-class tables (s12/s10/h12/h16). The WebUI repeats them as strings (`imx585ClassModes`, fallback until the ladder pool arrives). The touch UI lists equal ui-upstream: no 2880x2160, 2160x2160, 2976x2160, 2048x* crops, 1440x1080, 1920x1040. They still offer 3840x2076 and 1920x1038, which Core migrates to 2072/1036, so after picking one the current value is not in the list. Operator: the touch UI cannot select the 2K crop, 4:3 or 1:1 modes the WebUI offers. Upstream had per-UI hand lists too (core-map 4.5); the port made a single source and left two consumers off it.
- fix: Upstream style (flat scalar state, per-UI lists): update the QML imx585 lists to Core's class tables (bit depth and Clear HDR pick the class, as WCP does) and add a comment in Imx585Modes.hpp naming WCP:8915 and CameraPage.qml/SettingsPage.qml as copies. If a shared source is wanted, the bridge calls the port's `list_sensor_modes` once per sensor and the QML list stays as fallback; document that as new ground.

### X-state-consistency-4 [mismatch, minor, effort S] Touch UI built-in FPS list lacks Core's IMX585 100/120
- where: Apertar-Core/src/ApertarCoreApp.cpp:1398-1406@cinemate-port ; Apertar-UI/qml/CameraPage.qml:923-930@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:1968@cinemate-port
- detail: With no fpsSteps in UI.conf, Core uses `builtInFpsSteps` for the buttons and sends it to the WebUI as `ui.fps_steps`: IMX585 {24,25,30,50,60,100,120}. The touch UI falls back to {24,25,30,50,60} for the IMX585. Operator: on an IMX585 the touch picker lacks 100 and 120, which the WebUI and buttons offer. The IMX477 difference (QML 27 values vs Core 6) is upstream drift (ui-upstream CameraPage.qml:804 vs core-upstream App:1154-1157), not port.
- fix: Add 100 and 120 to the QML fallback for `imx585Detected`, with a comment naming App `builtInFpsSteps` as the source.

### X-state-consistency-5 [duplication, minor, effort S] Old FPS ceiling copies stay beside fps_max
- where: Apertar-UI/qml/CameraPage.qml:904-918@cinemate-port ; Apertar-Core/src/web/WebControlPage.cpp:7490-7509@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:1413@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:3495-3500@cinemate-port
- detail: `fps_max` = min(modeMaximumFps incl. IMX477 uncompressed table, losslessMaximumFps incl. 4K 30/24 and 2K 60, IMX585 mode). The WebUI re-applies the IMX477 uncompressed and 4K/2K lossless caps on top of `fps_max`. QML and App keep the old per-sensor tables as fallback for a Core without `fps_max` (upstream mechanism), and the port still edits that copy (UI d1efb67, Clear HDR 16-bit 25 fps). Values agree today; core-map 4.5 records 33/50 fps once blocked by four caps.
- fix: Delete the re-application in WCP:7490-7509 when `fps_max > 0`. Keep the QML/App fallbacks only for an older Core, mark them frozen, and stop editing them. Comment next to `maximumFpsForSettings` that it is the one table.

### X-state-consistency-6 [mismatch, minor, effort S] WebUI preset load allow-list drops frameBufferBarEnabled
- where: Apertar-Core/src/web/WebControlPage.cpp:19028-19112@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:7787@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:14454@cinemate-port
- detail: d44b177 added frameBufferBarEnabled to Core's writer and reader; the touch UI writes and reads it. `buildPresetApplyPayload` (only caller `loadPresetFromLibrary` :19155) lacks it, though its siblings are at :19109. All other keys missing from the list are missing upstream too (core-map 4.4). Operator: a preset loaded through the WebUI library leaves the buffer bar unchanged.
- fix: Add "frameBufferBarEnabled" next to "recordingFrameEnabled" at WCP:19109.

### X-state-consistency-7 [mismatch, minor, effort S] settingsBody carries 14 hardware-file keys the settings event lacks
- where: Apertar-Core/src/ApertarCoreApp.cpp:393@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:252-269@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:163-250@cinemate-port
- detail: Upstream `settingsBody` (core-upstream App:167-216) is CaptureSettings only, the same set as `settingsEvent`. The port appends `bufferSettingMembers()` (buffer_setting, buffer_note, buffer_safety_stop, buffer_stop_percent, buffer_flush_discarded, storage_preroll_active/auto/auto_env/fps/last, frames_per_folder(_env), clip_merge_enabled, clip_merge_env_off). Every set_* reply carries [storage] state; the event does not. The buffer event and web state carry them via `bufferMembers`.
- fix: Remove `bufferSettingMembers()` from `settingsBody`; append it in get_state's body only.

### X-state-consistency-8 [bug, nit, effort S] settings event always sends iso_actual 0
- where: Apertar-Core/src/camera/CameraController.cpp:12856-12870@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:12583-12587@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:175@cinemate-port
- detail: `isoMeasured` is filled only on the copy in `settings()`; `emitSettingsEventLocked` serialises `settings_`, so the event's `iso_actual` is 0. The touch UI treats 0 as unknown (ApertarControlBridge.cpp:1602-1603). Upstream does the same for `wb_measured`/`wb_actual_*` (core-upstream CC:159, :8572); the port follows that pattern.
- fix: Leave `iso_actual` out of `settingsEvent` (live value from get_state only), or fill measured ISO and WB in `emitSettingsEventLocked` as `settings()` does.

### X-state-consistency-9 [slop, nit, effort S] Published port state fields with no reader in either UI
- where: Apertar-Core/src/ApertarCoreApp.cpp:309-400@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:9298-9720@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:12932-12965@cinemate-port
- detail: No reader in Apertar-UI src/qml or WCP for conform_fps, ladder_override, fps_phase_lock_active/err_us/dur_us/pushes/saturated, tuning_file_active, media_device/fstype/class/profile, recording_fault, sensor_binning/_source, sensor_crop. Only the KB test rig reads them. Upstream has some unread fields too (wb_measured, wb_actual_*), so diagnostic fields are not foreign; the `hdr_*` knobs are fork main, not port. `conform_fps` is the one with operator effect: a setting with no control in either UI, changed silently by a preset.
- fix: List the diagnostic fields as diagnostic in Core's README state section. For conform_fps, add a WebUI control or document it as socket/preset only.

### X-state-consistency-11 [bug, nit, effort S] get_state emits media_state twice
- where: Apertar-Core/src/ApertarCoreApp.cpp:12944@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:12961@cinemate-port
- detail: Written from `mediaSnapshot()` at :12944 and from `mediaState` at :12961; duplicate JSON key, two reads of the watcher.
- fix: Delete :12944, keep the one next to media_alive.

### X-state-consistency-12 [duplication, nit, effort S] Two array serialisers print ladder_tops with different precision
- where: Apertar-Core/src/camera/CameraController.cpp:153-161@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:486-496@cinemate-port
- detail: Event uses `ladderTopsJson` (6 significant digits), get_state and web state `jsonNumberArray` (10). Differs only for values like 119.880119.
- fix: One helper in a shared header next to `escapeJson`, used by both.

### X-state-consistency-13 [mismatch, nit, effort S] help list lacks test_input
- where: Apertar-Core/src/ApertarCoreApp.cpp:12930@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:12565@cinemate-port
- detail: `test_input` is dispatched, its pair `test_output` is listed, `test_input` is not. Upstream's list already lacks 12 commands (core-map 2.1).
- fix: Add "test_input" next to "test_output".

### X-state-consistency-14 [mismatch, nit, effort S] preview_tdn and media_trim persisted but not in presets
- where: Apertar-Core/src/camera/CameraController.cpp:887,975@cinemate-port ; Apertar-Core/src/camera/CameraController.cpp:11348-11368@cinemate-port ; Apertar-Core/src/ApertarCoreApp.cpp:7697@cinemate-port
- detail: Both are camera_settings.conf keys, kept as camera-wide switches across format changes. Neither is in any preset copy, while `cameraCdngPreviewColorProfile` (upstream) is. Product decision.
- fix: Add cameraPreviewTdn (and cameraMediaTrim if wanted) to writer, reader and WCP allow-list, or comment in the writer that they are deliberately not preset fields.

Dropped: X-state-consistency-10 (see Skeptic table).
