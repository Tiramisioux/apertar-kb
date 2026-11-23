# Inventory WCP-04 (WebControlPage.cpp, new-file lines 7442-8900, JS: state rendering, pills, value lists)

Refs: port = `cinemate-port` 01f170c; upstream = `upstream-1.6.0` 35dbe67. Diff: `/home/user/build/review/diffs/WCP.part04.diff` (3 hunks, 1679 lines). Blame of 7442-8900: 586 lines `1ef94fe`, 210 `ff33d2d`, 122 original (`35dbe67`), 116 `9a081dd`, 83 `d44b177`, 51 `920beb0`, 41 `e472b1b`, 41 `da8ca9f`, 28 `8bcc5dd`, 27 `e7367ec`, 25 `b8ee23f`, 21 `ac00fb0`, 20 `af22759`, 15 `e25fd2b`, 15 `4b14a79`, rest under 13 each.
All of it is JS inside the one C++ raw string. Statuses are from `fork-log.md` (not proof of behaviour).

## 1. Commits and their recorded status (fork-log.md)

| Commit | What (this unit) | fork-log status |
| --- | --- | --- |
| ff33d2d | T33 Value Lists: `valueStepsFromSnapshot`, `cappedValueEntries`, `fpsOptionEntriesForSnapshot`, `shutterAngleEntriesForSnapshot`, `whiteBalanceStepsForSnapshot`, `flickerFreeShutterAngles`, `renderValueListsEditor`, `valueListDefinitions`, `sendValueSteps`, `buildOptionButtonsInto` | fork-only; tested 2026-10-28 (Patrik) (log l.77) |
| 920beb0 | T34 first Mode Ladder editor + FPS capped by `fps_take_max` | built, not tested (l.94) |
| 1ef94fe, e472b1b, d93a7e3, e7367ec, af22759, da8ca9f, b8ee23f, 8bcc5dd, 25f553e, 4b04a1d, b2c15af, 392e812 (+ others in l.97) | Mode Ladder / Speed Ramp / Activated sensor modes cards per "approved design"; ladder guards, auto-save, ordering by quality, default maxes, Activate/Deactivate, lock warning | fork-only; desk-tested, Pi check pending (l.97) |
| 4b14a79, 854fe43 | multi-ratio aspect filter; Modes pane | branch `drop-frames`, Pi only (l.145-146) |
| 66b324d | imx585 families, ratio row, ladder groups | in `drop-frames` set (l.138 text) |
| 9a081dd | IMX283 pills, ratios, fps floors (JS tables) | not located by hash in fork-log; probable: part of the imx283 driver work, check log by subject |
| ac00fb0 | first Speed Ramp block (T32 pt 2); `renderSpeedRamp` skeleton | tested 2026-10-28, ramp works (l.65) |
| ca7b7c2 | stretched-audio switch in Speed Ramp card | experimental; tested (hardware-log) (l.69) |
| e25fd2b, 15bba86, f81108d | camera-set values green / white auto; ISO list from `iso_max`; Lock | tested 2026-10-28 (l.72, 83, 88) |
| b5b787e | Auto ISO in IMX585 lossless, Auto everywhere but Clear HDR | built; **unverified** (l.85) |
| b5847c7 | 4K Clear HDR 16-bit capped at 25 fps (JS line 7456) | tested 2026-10-28 (l.59) |
| 900d282 | imx585 1.85:1 crops 3840x2072 / 1920x1036 (JS 7459, 7462) | not tested per log text; needs cinemate-port driver |
| d44b177 | drop-frames: fps max from probe, storage pre-roll (`shownFps`, `markPrerollFps`, `showPrerollFpsText`), lossless cap lifted | fork-only, Pi; "not run yet" for later rebuild (l.138, 152) |

## 2. Features (operator-visible)

| Feature | Where (@cinemate-port WCP.cpp) | Commits | Core side |
| --- | --- | --- | --- |
| FPS pills from Core's `fps_max`; values above ceiling greyed, ceiling added green | 7475-7553 `fpsOptionEntriesForSnapshot`, 7634-7650 `cappedValueEntries` | ff33d2d, d44b177, 920beb0 | state `fps_max`, `fps_take_max`, `ladder_active` |
| Operator value lists (ISO, shutter angle, FPS, WB): chips, Add/Reset, List/Free, increment, flicker-free angles on/off, mains 50/60 | 7580-7666, 8481-8650 `renderValueListsEditor` | ff33d2d, f81108d, b2c15af | cmd `set_value_steps` (App 14110); state `ui.*_steps`, `ui.*_free`, `ui.*_free_increment`, `ui.flicker_free_shutter_angles`, `ui.mains_hz`; stored in UI.conf |
| Flicker-free shutter angles (JS copy of Core maths) | 7648-7660, also in chips | ff33d2d | `flickerFreeShutterAngles` App 1294 |
| ISO pills follow `iso_max`; Auto + Lock; no Auto in Clear HDR; camera-set ISO shown green | 8660-8690 `availableIsoOptionsForSnapshot`, `isoSetByCamera` | e25fd2b, b5b787e, 15bba86 | state `iso_max`, `iso_auto`, `iso_auto_after_clear_hdr`, `clear_hdr` |
| Speed Ramp card: allow on/off, shutter angle/exposure, audio real/stretched, after take stay/return | 7531-7563 `renderSpeedRamp`, `speedRampFormatSupported` | ac00fb0, ca7b7c2, 1ef94fe, d44b177 | cmd `set_fps_speed_ramp` (App 13223) params `enabled`,`shutter`,`audio`,`after`; state `fps_speed_ramp`, `_keep_exposure`, `_stretch_audio`, `_after` |
| Mode Ladder editor: rows, compression select, max-fps input, auto-arranged by quality, default maxes 25/33/50/+25, crop graphic, MB/frame, card-speed warning, locked in a take, auto-save 200 ms | 7668-8480 | 920beb0, e472b1b, e7367ec, da8ca9f, b8ee23f, 8bcc5dd, 1ef94fe, 392e812 | cmds `get_mode_ladder`, `set_mode_ladder` (resolutions, enabled, dry_run) App 14090-14108; state `ladder_enabled`, `ladder_active`, `ladder_count`, `ladder_resolution`, `ladder_text` |
| Activated sensor modes: probe pool in collapsible groups, aspect filter (multi-select), Activate/Deactivate tile with reason | 8260-8420 | 1ef94fe, da8ca9f, af22759, 4b04a1d, 4b14a79, 25f553e, d93a7e3 | `mode_ladder.pool` from sensor probe |
| Lock warning toast with link "Mode Ladder"; opens Modes pane and scrolls to card | 7981-8000 | 392e812, 854fe43 | none |
| "Running now" line + crop frame of current mode | 8430-8480 `renderModeLadder` | 1ef94fe | `ladder_text` |
| FPS-stop toast text | 7971-7978 `fpsStopToastText` | 1ef94fe | |
| Storage pre-roll readouts italic, show pre-roll fps | 8700-8740 `shownFps`, `showPrerollFpsText`, `markPrerollFps`, `markActiveSystemValue` | d44b177, f81108d | state `storage_preroll_active`, `storage_preroll_fps`; Core: `StoragePreroll.hpp` |
| IMX283 resolution pills (bases 5.5K / 2.7K 2x2 / 1.8K 3x3 12-bit; 5.5K / 4K UHD 10-bit), ratio rows, fps floors, normalise | 8900-9050 region (hunk 3 start 8742-8870) | 9a081dd | Core `Imx283Modes.hpp` kModes, `apertar::imx283::normalise` |
| IMX585 resolution families (Full HD binned, 4K, 2K crop, HD crop, each +HDR), ratio row, aliases for old 1.85:1 sizes, mono sensor | 8900-9140 | 66b324d, 900d282, 1ef94fe | Core `Imx585Modes.hpp`; state `sensor_mono`, pool |
| IMX585 Clear HDR chosen inside the resolution pill (sends `set_clear_hdr` then resolution) | `imx585BaseCommands` | 66b324d | cmd `set_clear_hdr` (existing) |
| Clear HDR 16-bit ceiling 25 fps in JS table | 7456-7458 | b5847c7 | |
| IMX585 lossless fixed 30 fps cap removed; Core's `fps_max` rules | 7518-7520 | d44b177 | env `APERTAR_LOSSLESS_FPS_LIMIT` (CameraController 3115) |

## 3. Socket commands, routes, state fields, events, config, env, files, UI

| Kind | Item | Added or changed | Evidence |
| --- | --- | --- | --- |
| Command used (new in Core) | `set_value_steps` (name, values, free, increment, flicker_free, mains_hz) | added | WCP 8478-8650; App 14110 |
| Command used (new) | `get_mode_ladder`, `set_mode_ladder` (resolutions, enabled, dry_run, ramp_ready) | added | WCP 8040-8140; App 14090 |
| Command used (new) | `set_fps_speed_ramp` (enabled, shutter, audio, after) | added | WCP 7545-7555; App 13223 |
| Command used (existing) | `set_clear_hdr` | called from JS family pills | WCP imx585BaseCommands |
| HTTP route | `POST /api/command` via private `ladderRequest()` | no new route; bypasses `sendCommand` snapshot patching (7716-7725) | upstream `sendCommand` at WCP@upstream:9109 patches snapshot |
| State (snapshot) fields read | `fps_max`, `fps_take_max`, `fps_steps`, `iso_max`, `iso_auto`, `iso_auto_after_clear_hdr`, `ladder_enabled/_active/_count/_resolution/_text`, `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `_stretch_audio`, `_after`, `storage_preroll_active`, `storage_preroll_fps`, `sensor_mono`, `system.write_speed_result_text`, `ui.iso_steps/shutter_angle_steps/fps_steps/wb_steps`, `ui.*_free`, `ui.*_free_increment`, `ui.flicker_free_shutter_angles`, `ui.mains_hz` | added | grep in WCP 7442-8900; App 260-372, 9479-9534 |
| State arrays/nested | `ui.*_steps` are JSON arrays; `mode_ladder` reply is a nested object with `resolutions[]`, `pool[]`, `ceilings{}`, `errors[]` | new shape | upstream replies flat scalars (BRIEF) |
| JS page state (`state.*`) | `valueListsSignature`, `valueListFps`, `fpsSwitchingTo`, `ladderServer`, `ladderError`, `ladderDraft`, `ladderSaveAgain`, `ladderRecordingSeen`, `ladderCheckTimer`, `ladderSaving`, `ladderToggling`, `ladderFetching`, `ladderFetchedMs`, `ladderSeenActive`, `ladderAspects`, `ladderOpen` | added | WCP 6670-6686 |
| Config keys | none written from this unit directly; lists persisted by Core in UI.conf (`isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `*Free`, `*FreeIncrement`) | | App 14110 |
| Env vars (referenced in comment) | `APERTAR_LOSSLESS_FPS_LIMIT` (comment only, 7519), `APERTAR_FPS_LIMIT=table` (Core) | | CC 3115, 3397 |
| Files on disk | none from this unit; Speed Ramp card refers to the stretched-WAV result of `rubberband` (Core, ca7b7c2) | | |
| DOM ids used (HTML in other parts) | `settingsSpeedRampNote/Options/ShutterOptions/AudioOptions/AfterOptions`, `settingsModeLadderCard/List/Value/Options/SwitchNote/Now/NowNote/NowCrop`, `settingsSensorModes*`, `settingsSensorModeAspectFilters/Groups`, `settingsValueLists`, `fpsBadge`, `settingsFpsSummary`, `fpsOptions`, `toast` | added | |
| CSS classes used | `.system-value`, `.ladder-*`, `.crop-frame`, `.crop-window`, `.crop-tag`, `.value-chip(-row)`, `.value-chip.flicker-free`, `.with-link` | added (CSS in other unit) | |
| UI elements | Value Lists card; Speed Ramp card; Mode Ladder card; Activated sensor modes card; ladder lock toast; Modes pane; italic pre-roll readouts; green camera-set pills | added | |

## 4. ORIGINAL code regions modified (this unit)

| Region (@upstream-1.6.0 WCP) | Change | Kind |
| --- | --- | --- |
| `maximumSupportedFpsForSnapshot` imx585 branch (@upstream 4966-5005): `30.0` for 4K, heights 2076/1038 | 4K Clear HDR 16-bit returns 25; heights 2076->2072, 1038->1036; new imx283 branch delegating to `imx283MaximumSupportedFps` | extended in place, constants changed |
| `availableFpsOptionsForSnapshot` (@upstream 4992-5021) | Body moved to new `fpsOptionEntriesForSnapshot`; old one is a filter over it. Preset list from `ui.fps_steps`, ceiling from Core `fps_max`/`fps_take_max`, table only as fallback. IMX585 lossless fixed 30 removed (empty if-branch with comment). Lists no longer drop values above the ceiling: they are kept and greyed | rewritten, returns changed from strings to entries (new `enabled`/`system`) |
| `availableIsoOptionsForSnapshot` (@upstream 5023-5027) | Fixed `["100","200","400","800"]` for lossless removed; now list from `ui.iso_steps`, capped by `iso_max`, Auto/Lock rules by `clear_hdr`/`iso_auto` | rewritten, behaviour changed |
| `sensorResolutionOptions` (@upstream 5112) | imx585 hard-coded 20-size list replaced by `imx585ResolutionOptions` (pool or class tables); new imx283 branch; imx585 branch moved first | rewritten (imx585), extended (imx283) |
| `normalizedResolutionForSnapshot` (@upstream 5124) | prepends `if (imx585Selected) return imx585NormalizedResolution` | extended in place |
| imx294 helpers (@upstream 5060) | untouched; imx283 helpers copy their shape (`imx283CropOptionsForBase` mirrors `imx294CropOptionsForBase`) | parallel path |

## 5. New abstractions in this unit

| Abstraction | Purpose | Upstream equivalent |
| --- | --- | --- |
| `valueStepsFromSnapshot` / `cappedValueEntries` / `fpsOptionEntriesForSnapshot` | one list-plus-ceiling mechanism for FPS/ISO | upstream: constants `fpsPresets`, `isoOptions`, `shutterOptions`, `whiteBalanceOptions` (WCP@upstream 4039-4043) filtered in `availableFpsOptionsForSnapshot` |
| Entry objects `{value,label,enabled,system,locked}` | greyed and camera-set pills | upstream pill options are `{value,label,enabled}`; `buildOptionButtons` has no `system`/`locked` (WCP@upstream 9146) |
| `buildOptionButtonsInto(container,...)` | draw pills into an element not an id (also `showLadderLockWarning` hook on `locked`) | upstream `buildOptionButtons(containerId...)` only |
| Mode Ladder editor (`ladder*` ~45 functions, ~800 lines) | draft/normalise/arrange/dry-run editor of Core's ladder | none (new ground); Core `ModeLadder.hpp` new too |
| Crop diagram (`ladderCrop`, `fillCropFrame`) | picture of sensor window | none |
| `ladderRequest` | raw fetch to `/api/command` w/o snapshot patch | upstream `sendCommand` (WCP@upstream 9109) is the one call path |
| `renderValueListsEditor` with signature + typing guard | redraw only on change | upstream has no list editor |
| JS mirrors of Core tables: `imx283Bases`, `imx283ModeOrder`, `imx585ClassModes`, `flickerFreeShutterAngles`, `imx283NormalizedResolution`, `imx585NormalizedResolution`, ladder default maxes | offline fallback and instant pills | upstream JS keeps per-sensor resolution arrays (`imx477ResolutionOptions`, `imx294ResolutionOptionsForSnapshot`) hand-copied from Core; the port repeats that pattern but adds a second source (probe pool) |
| `imx585Families` / class keys `s12 s10 h12 h16` | Clear HDR as part of resolution pill | none: upstream imx585 had one flat list |

## 6. Removed, narrowed or hid (upstream behaviour)

| What | Where | Effect |
| --- | --- | --- |
| IMX585 fixed 20-size resolution list | `sensorResolutionOptions` | list now from probe pool or class tables; 1.85:1 sizes 3840x2076 / 1920x1038 renamed 2072 / 1036 (aliases kept in `imx585NormalizedResolution`); tables drop widths under 1280 |
| IMX585 lossless ISO list 100-800, lossless 4K/2K FPS 30/24/60 caps | ISO/FPS functions | IMX585 lossless FPS cap removed (Core decides, env override); ISO list no longer cut for lossless unless `iso_max` set; IMX585-only |
| `availableFpsOptionsForSnapshot` fallback `[max]` | | now `system` green single entry |
| Clear HDR 30 fps in JS table | | now 25 at 16-bit |
| FPS list format | return type of `fpsOptionEntriesForSnapshot` is entries, `availableFpsOptionsForSnapshot` still strings | callers elsewhere must use entries to see greyed values |
| Pills during ladder | `ladderLockedOptions` | resolution / compression / bit-depth / Clear HDR pills disabled while ladder is active (also in Recording format and Favorites per log) |

## 7. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| IMX585 lossless encoder "about 69 fps measured at 4K 12-bit", warns above 30 | 7947-7950 (text in `createLadderRow`) | Pi 5 four-core CPU number hard-coded in UI text |
| Card write speed from Core media test `system.write_speed_result_text` "412 MB/s" parsed by regex | `ladderCardWriteSpeed` | depends on Core text format |
| IMX283 driver: modes, floors 21.401, 51.796, 60.271 etc. are numbers of the cinemate-port imx283 driver | `imx283Bases` | tied to the port's driver; stock driver modes differ (unconfirmed) |
| Sensor window readout area 3840x2160 for crop diagram | `ladderCropArea` | IMX585 only; used for any sensor |
| `ladderUnknownCeiling = 280`, max 8 resolutions | | no board link |
| Pi model, RP1, PCIe, gpiochip, I2C bus, RAM size, fan | none in this unit | confirmed absent in the diff |

## 8. Notes for later stages (not judgements)

- 4 sources of the same facts: Core C++ tables, JS tables, probe `pool`, `fps_max`; JS comments say "as in Core's ..." in 7 places.
- Ladder text format `WxH:BITS:hdr|sdr[:FPS[:COMP]]` built in JS (`ladderDraftText`) and parsed in Core.
- Two places call Core without `sendCommand`: `ladderRequest` only (get_mode_ladder).
- Ticket labels in comments: "T31", "T33", "T34", "Request 24" (7 occurrences in this unit; meaningless to upstream per BRIEF).
- `ladderIcons` inline SVG strings; upstream uses no inline icon objects in JS (unconfirmed, grep `<svg` in upstream not done).
