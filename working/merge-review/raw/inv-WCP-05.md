# Inventory WCP-05: WebControlPage.cpp JS, settings / presets / favourites (new-file lines 9168-11399)

Diff: `/home/user/build/review/diffs/WCP.part05.diff` (origin/main -> cinemate-port, 975 lines, 20 hunks). Read whole.
Refs: `@cinemate-port` = port, `@upstream-1.6.0` = `/home/user/wt/core-upstream`, `@main` = fork origin/main.
Blame run on port lines 9168-11399. Status/tests from `apertar-kb/fork-log.md`. No judging here.
Note: the diff base is fork `main`, so removed lines (IMX585 Clear HDR, imx585 helpers) are the contributor's earlier Clear HDR set, not upstream 1.6.0 code. Upstream 1.6.0 has no Clear HDR in the WebUI.

## Commits that wrote the slice (changed lines only)

| Commit | Subject | Lines in slice | fork-log status / tests |
| --- | --- | --- | --- |
| d44b177 | drop-frames (squash of 19 commits): Log, buffer, trim, Settings search | 125 | fork-only, branch drop-frames; desk |
| 909aaa5 | core, web: UI timecode and file timecode set apart | 24 | Pi build 2026-10-29, not tested |
| bc12c0a | web: Clip Browser in the touch UI's shape (T49) | 19 | tested 2026-10-29 headless Chrome vs Core, Pi build pending |
| 9a081dd | web: IMX283 resolution pills, ratio rows, fps floors | 19 | desk only (host tests, -fsyntax-only, node --check); no fork-log row found |
| 66b324d | web: imx585 resolution families, ratio row, ladder groups | 18 | desk only; no fork-log row found |
| 9fa7918 | web: 4K Clear HDR as resolution, 16-bit bit depth | 14 | "offer (with the Clear HDR set)"; this slice REMOVES most of its WebUI parts |
| 2c259b9 | web: timecode modes called Time of Day and Clip | 13 | desk only (node --check) |
| 392e812 | web: locked control answers with red warning | 12 | desk (headless Chrome vs Pi, read only) |
| 1ef94fe | web: Mode Ladder, Speed Ramp, Activated sensor modes cards | 11 | desk-tested, Pi check pending |
| ff33d2d | T33 web: Value Lists card; pills follow lists | 8 | tested 2026-10-28 (Patrik) |
| 4629de2 | web: Clip Viewer, frame-number clock (T50, page part) | 7 | tested 2026-10-29 on Pi Core (Patrik: works well) |
| 900d282 | camera, web: imx585 1.85:1 crops 3840x2072 / 1920x1036 | 5 | compile only (-fsyntax-only) |
| f5fe41b | web: Controls for detected hardware, Hardware card on Config | 3 | desk only (headless Chrome mock) |
| bda2066 | web: time left rounds down | 3 | Pi build; done (Patrik 2026-10-27) |
| 8a56545 | WebUI: Boot Config card in System pane | 3 | no fork-log row found |
| 854fe43 | web: Modes pane (Activated sensor modes, Mode Ladder) | 2 | desk only |
| d282de9 | web: Controls card at top of Config | 1 | pi + headless Chrome mock 20/20 |
| 438a342 | media: survive a yanked recording drive | 1 | built, Pi |

Most of the slice (about 2000 of 2230 lines) is unchanged upstream-1.6.0 code (`^35dbe67`). This slice holds only the hooks, dispatch edits and function bodies below.

## Hunk table

| # | New-file lines | Function / region | Change | Feature | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | 9168-9189 | `normalizedResolutionForSnapshot` tail | IMX585 block (12 sizes, mapping) deleted; IMX283 early return `imx283NormalizedResolution(snapshot, value)` added | IMX283 resolutions; IMX585 families | 9a081dd, 66b324d |
| 2 | 9219-9324 | `imx585CropControlsAvailableForSnapshot`, `imx585CropRatioOptionsForSnapshot`, `imx585BaseResolutionOptions()` (no-arg), `clearHdrAvailableForSnapshot`, `isImx585FourKResolution`, `isImx585FullHdResolution` deleted | Replaced by `imx585Selected(snapshot)` early returns into `imx585BaseResolutionOptions(snapshot)`, `imx585BaseCommands`, `imx585BaseResolutionValueFromSnapshot`, `imx585CropRatioOptions`, `imx585ResolutionForBaseAndRatio`; `imx283*` branches added in `sensorBaseResolutionOptionsForSnapshot`, `sensorBaseResolutionValueFromSnapshot`, `sensorCropRatioOptionsForSnapshot`, `sensorResolutionForBaseAndRatio`; `sensorCropControlsAvailableForSnapshot` gains imx283; hard-coded 3840/1920 ratio tables in `sensorResolutionForBaseAndRatio` deleted (generic tail now `[]`) | IMX585 family pills (HD, 4K, 2K crop, HD crop, each + HDR version); IMX283 pills; fork-main "4K Clear HDR" pill removed | 66b324d, 9a081dd, 9fa7918 (removed) |
| 3 | 9373-9411 | `resolutionCommandPayload` (label to `set_resolution`) | 1920x1038 -> 1920x1036, 3840x2076 -> 3840x2072; old labels still accepted | imx585 1.85:1 crop sizes | 900d282 |
| 4 | 9419-9462 | `nearestWhiteBalance`, `whiteBalanceIndexFromKelvin`, `whiteBalanceFromSliderValue` | `whiteBalanceOptions` constant replaced by `whiteBalanceStepsForSnapshot(state.snapshot)` (state field `wb_steps`) | Value Lists (WB steps) | ff33d2d |
| 5 | 9587-9610 | `rawBitDepthAvailableForSensor` | imx283 added | IMX283 | 9a081dd |
| 6 | 9647-9680 | `cropRatioLabelForResolutionValue` | `imx283CropRatioLabel` lookup added; 3840x2072 and 1920x1036 added to the 1.85:1 row | IMX283; crop renames | 9a081dd, 900d282 |
| 7 | 9773-9840 | after `captureCodecLabel`: new `codecDisplayLabel`; `timecodeDisplayName`, `timecodeChoices`, `uiTimecodeLabel`, `fileTimecodeLabel`, `timecodeSummaryLabel`, `timecodeCommand` | new functions | Log suffix on codec; Time of Day / Clip names; UI vs file timecode | d44b177, 2c259b9, 909aaa5 |
| 8 | 9904-9915 | `formatMinutes` | `Math.round` -> `Math.floor`, comment names `MediaStatusBridge::remainingMinutesText` | time left rounds down | bda2066 |
| 9 | 10101-10113 | `setSettingsOpen` | two lines: open on "modes" pane calls `fetchModeLadder(false)`; open on "system" pane calls `loadBootConfig(true)` | Modes pane; Boot Config | 854fe43, 8a56545 |
| 10 | 10115-10145 | `setMediaBrowserOpen(open, fromHistory)` | rewritten body: toggles `pb-open` and `#playbackOverlay` (was `media-browser-open`, `#mediaBrowserOverlay`); filter Still in photo mode else Clip; `pbSetShowMenu`, `pbPauseLive`, `history.pushState({pb:1})`, `pbRender`; close path: `pbvClose`, `pbResumeLive`, `history.go(-steps)` | Clip Browser, Clip Viewer, phone Back | bc12c0a, 4629de2 |
| 11 | 10147-10176 | `setSettingsPanel` | loads on pane switch: system -> `loadBootConfig`; controls -> `loadControls`; config -> `loadControls` (when no dirty controls/hardware); modes -> `fetchModeLadder` | Boot Config, Controls, Hardware card, Modes | 8a56545, d282de9, f5fe41b, 854fe43, 1ef94fe |
| 12 | 10178-10300 | new `settingsSearch` object, `settingsSearchHaystack`, `settingsSearchGroups`, `applySettingsSearch`, `clearSettingsSearch` (about 110 lines) | new; MutationObserver with 250 ms debounce; toggles `.search-hidden` only; builds `#settingsSearchEmpty` and per-panel `.settings-search-label` in DOM | Settings search | d44b177 |
| 13 | 10436-10462 | `normalizeChoiceOptions` | option gains `system` and `locked` booleans | Mode Ladder lock; GPIO/hardware dropdown colouring | 392e812, d44b177 (`system`), ff33d2d |
| 14 | 10557-10560 | favourites summary `case "timecode"` | `timecodeText` -> `timecodeSummaryLabel(snapshot)` | UI/file timecode | 909aaa5 |
| 15 | 10596-10606 | favourites summary `case "camera"` | codec through `codecDisplayLabel` | Log suffix | d44b177 |
| 16 | 10719-10745 | `createPillGrid` | `button.disabled = !enabled && !locked`; click on a locked option calls `showLadderLockWarning(false)` | Mode Ladder lock warning | 392e8120 |
| 17 | 10881-10883 | `renderFavoritesPane` setup | `hasMedia` uses `snapshot.media_alive` when present, else `media_mounted` | media fault latch | 438a342 |
| 18 | 10928-10945 | `cropRatioEnabled` | `&& !snapshot.clear_hdr` removed (crop row is live in Clear HDR) | IMX585 families | 66b324d |
| 19 | 11116-11195 | favourites `case "format"` | `ladderActive = snapshot.ladder_active`; Resolution, Crop, Compression greyed and tagged `dataset.ladderLock`; Bit Depth options through `ladderLockedOptions`, class `ladder-locked`; `case "timecode"` now two blocks "UI Timecode" and "File Timecode" | Mode Ladder lock; UI/file timecode | 1ef94fe, 392e812, 909aaa5 |
| 20 | 11399-11402 | favourites `case "camera"` | Codec value through `codecDisplayLabel` | Log suffix | d44b177 |

The hunks that look like Settings, presets and favourites content are touch points only. The preset library call (`fetchPresetLibrary(true)` on the presets pane) is unchanged upstream code. No preset-specific lines changed in this slice.

## Operator-visible features touching this slice

| Feature | What the operator gets | Where in slice |
| --- | --- | --- |
| IMX585 resolution families | Family pills Full HD binned, 4K, 2K crop, HD crop, each with an HDR version (sends `set_clear_hdr` then the size); crop row lists ratios of the current family ("2.39:1 - 3840x1608"), also in Clear HDR; "4K Clear HDR" pill from fork-main gone | hunks 1, 2, 18 |
| IMX283 resolution pills | bases per bit depth (12-bit: 5.5K, 2.7K 2x2, 1.8K 3x3; 10-bit: 5.5K, 4K UHD), ratio rows, 10/12-bit depth | hunks 1, 2, 5, 6 |
| IMX585 1.85:1 crops | page offers and sends 3840x2072 and 1920x1036; old 2076/1038 labels still accepted | hunks 3, 6 |
| Value Lists steps | white-balance slider and nearest-Kelvin use Core's `wb_steps` | hunk 4 |
| Log suffix | codec shown as "CinemaDNG RAW . Log" when CineMate Log is stored | hunks 7, 15, 20 |
| Time of Day / Clip | shown names for Free Run / Rec Run; stored values unchanged | hunk 7 |
| UI timecode vs file timecode | two separate settings (Favorites has two blocks; Timecode card in an earlier slice) | hunks 7, 14, 19 |
| Time left rounds down | "35 min" like the touch UI | hunk 8 |
| Clip Browser / Clip Viewer | playback overlay replaces media list; phone Back closes it; live view pauses; opens on Stills in photo mode | hunk 10 |
| Settings search | search field over all panes, narrows cards and rows, "No setting matches" | hunk 12 |
| Modes pane | new settings pane; opening it fetches the ladder | hunks 9, 11 |
| Boot Config card | System pane loads `get_boot_config` on open | hunks 9, 11 |
| Controls / Hardware card | Controls and Config panes load controls on open | hunk 11 |
| Mode Ladder lock | Resolution, Crop, Bit Depth, Compression greyed while ladder active; click shows red warning with a link to the card | hunks 13, 16, 19 |
| Media fault latch | favourites "hasMedia" follows `media_alive` | hunk 17 |

## Socket commands, routes, state fields, config keys

| Kind | Name | Added / changed here | Notes |
| --- | --- | --- | --- |
| Command (used by JS) | `set_timecode_mode` with `target` = ui or files | changed (JS sends `target`); Core accepts ui, files, both, default both | Core `ApertarCoreApp.cpp:13279-13300` @cinemate-port; UI target writes UI.conf `timecodeMode` via `updateSharedUiGeneralSettings`, files target `camera_.setTimecodeMode` |
| Command | `set_clear_hdr` | sent by `imx585BaseCommands` (not defined in this slice) | exists on fork main |
| Command | `set_resolution` | sizes 3840x2072, 1920x1036 | |
| Command | `get_mode_ladder` | via `fetchModeLadder` on pane open | |
| Command | `get_boot_config` | via `loadBootConfig` on pane open | |
| Command | `get_controls` | via `loadControls` on pane open | |
| HTTP | `/api/media/frame`, `/api/media/library` | used by `fetchMediaLibrary`, `pbRender` (not in slice) | |
| State field read | `wb_steps` | read | `ApertarCoreApp.cpp:1969` @cinemate-port |
| State field read | `ladder_active` | read | `ApertarCoreApp.cpp:327, 9491` |
| State field read | `cdng_log_available`, `cdng_log_bits`, `cdng_log_applied` | read | `ApertarCoreApp.cpp:357-359, 9518-9520` |
| State field read | `media_alive` | read, falls back to `media_mounted` | `ApertarCoreApp.cpp:9556`; `media_mounted` still read upstream-style |
| State field read | `snapshot.ui.timecode_mode` vs `snapshot.timecode_mode` | read | UI copy at `ApertarCoreApp.cpp:9635`, file copy 9509 |
| State field read | `snapshot.ui.photo_mode_enabled` | read (browser filter) | |
| JS state added | `state.pb.{selecting, selection, filter, viewer, viewerPushed, pushed, ignorePop}` | used here | defined elsewhere in port |
| JS global added | `settingsSearch {active, observer, timer, applying}` | new | |
| Config keys | none added in this slice | | boot config, storage and media keys belong to other units |
| Env vars | none | | |
| Files on disk | none | | |

## UI elements referenced

| Element | Status |
| --- | --- |
| `#settingsSearchInput`, `#settingsSearchEmpty`, `.settings-search-label`, `.search-hidden`, `.settings-panels.searching` | new (CSS at `WebControlPage.cpp:1814-1860` @cinemate-port) |
| `#playbackOverlay`, `#pbRemoveScrim`, body class `pb-open` | new; replace `#mediaBrowserOverlay` and `media-browser-open` (both still in @main: 2 refs; none in port) |
| settings nav item `data-panel="modes"` and panel | new (`:4750`, `:5151`) |
| `.ladder-locked`, `data-ladder-lock` | new (CSS `:1364`) |
| Favourites "UI Timecode" and "File Timecode" blocks | new, replace single "Timecode Mode" |

## Regions of ORIGINAL (upstream-1.6.0) code modified

| Region | upstream line @upstream-1.6.0 | Kind | What |
| --- | --- | --- | --- |
| `nearestWhiteBalance` / `whiteBalanceIndexFromKelvin` / `whiteBalanceFromSliderValue` | 5511 ff | extended in place | constant array swapped for per-snapshot steps (`whiteBalanceOptions` at upstream 4043 stays as the fallback, now inside `whiteBalanceStepsForSnapshot`) |
| `rawBitDepthAvailableForSensor` | near 5690 | extended in place | one sensor added |
| `cropRatioLabelForResolutionValue` | near 5755 | extended in place | imx283 lookup; two 1.85:1 values |
| `formatMinutes` | 5938 | behaviour-changed | round -> floor (also "1h 60m" case) |
| `setMediaBrowserOpen` | 6139 | rewritten | new overlay, history entry, live-view pause |
| `setSettingsOpen`, `setSettingsPanel` | 6150 ff | extended in place | lazy loads per pane |
| `normalizeChoiceOptions` | 6317 | extended in place | `system`, `locked` flags |
| `createPillGrid` | near 6629 | behaviour-changed | locked option stays clickable (shows warning) |
| `hasMedia` in favourites | 6766 | behaviour-changed | `media_alive` over `media_mounted` |
| favourites `format` and `timecode` cases | 7022-7060 | extended in place (format), rewritten (timecode: one block -> two) | |
| favourites/summary `camera`, `timecode` | 6400-6520 | extended in place | label helpers |
| `normalizedResolutionForSnapshot`, `sensorBaseResolutionOptionsForSnapshot`, `sensorBaseResolutionValueFromSnapshot`, `sensorCropRatioOptionsForSnapshot`, `sensorResolutionForBaseAndRatio`, `resolutionBaseValueFromSnapshot` | 5161-5330 | extended in place with early-return dispatch per sensor | imx585 body removed from each and moved to a new block; imx477 and imx294 paths unchanged |

Upstream 1.6.0 does not contain the IMX585 or Clear HDR bodies removed in hunks 1 and 2 (they are @main). Compare against `@upstream-1.6.0` for those: upstream had `imx585CropRatioOptionsForSnapshot` (5249) and the hard-coded IMX585 tables; the port deletes upstream's version too.

## New abstractions

| Name | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- |
| `imx585Selected(snapshot)` + `imx585*` block (about 60 functions, `WebControlPage.cpp:8935-9100+`) | per-sensor resolution logic in one block, early return from each dispatcher | none: upstream uses `sensorNameLower(snapshot).indexOf("imx585")` inline in each function (`@upstream-1.6.0 :5161-5330`) | hunks 1, 2 |
| `imx283*` block (`:8813-8935`) | same for IMX283 | none (upstream has no imx283 UI); same inline `indexOf` pattern for imx477 and imx294 | hunks 1, 2, 5, 6 |
| `whiteBalanceStepsForSnapshot` / `valueStepsFromSnapshot` | steps from Core state | upstream constant `whiteBalanceOptions` (`:4043`) | hunk 4 |
| `settingsSearch` module (JS, about 110 lines) | filter every settings pane by words; MutationObserver | none | hunk 12 |
| `state.pb` + `pb*` function family (`pbRender`, `pbPauseLive`, `pbvClose`, ...) | Clip Browser and Viewer | upstream `#mediaBrowserOverlay` list with Download and Delete (`@upstream-1.6.0 :3979, :6139`) | hunk 10 |
| History API use (`history.pushState`, `history.go`, `ignorePop`, `popstate` at `:20637`) | phone Back closes overlay | none: upstream has no `pushState` or `popstate` | hunk 10 |
| `codecDisplayLabel`, `timecodeDisplayName`, `timecodeChoices`, `uiTimecodeLabel`, `fileTimecodeLabel`, `timecodeSummaryLabel`, `timecodeCommand` | label helpers | upstream `timecodeModeLabel` (`:5852`) and inline command (`:7043`) | hunks 7, 14, 19 |
| `option.locked` / `ladderLockedOptions` / `showLadderLockWarning` | Mode Ladder lock | none | hunks 13, 16, 19 |

## Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| "4K Clear HDR" base pill (`clearhdr` value), `clearHdrAvailableForSnapshot`, `resolutionBaseCommands` Clear-HDR branch | hunk 2 | replaced by per-family HDR pills; availability rule (cDNG/MLV, no photo mode) not seen in the replacement in this slice: unconfirmed, check `imx585BaseResolutionOptions` |
| Crop row disabled in Clear HDR (`snapshot.clear_hdr` checks) | hunks 2, 18 | crop row live in Clear HDR |
| `#mediaBrowserOverlay` media list with per-row Download and Delete | hunk 10 | replaced by `#playbackOverlay` grid |
| Single "Timecode Mode" favourite | hunk 19 | now two blocks |
| `whiteBalanceOptions` as only source | hunk 4 | now fallback |
| IMX585 hard-coded 12 resolution sizes in `normalizedResolutionForSnapshot` | hunk 1 | falls through to the generic tail for sensors other than imx283 (`value || fallbackResolutionOptions[0]`) |
| Generic IMX585-lists-for-unknown-sensor tail in `sensorBaseResolutionOptionsForSnapshot` and `sensorResolutionForBaseAndRatio` | hunk 2 | unknown sensors now get `[]` (no base pills, no crop row) |
| Rounded minutes left | hunk 8 | floors |

## Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| Sensor identity from the string in `snapshot.capture.sensor` (imx283, imx294, imx477, imx577, imx585) | whole slice | no Pi-model dependency in this slice |
| "touch UI" and DPI wording in favourites summaries ("Managed from the DPI UI") | `:10596-10600` | unchanged upstream text |
| Boot Config card, loaded on System pane open | hunks 9, 11 | the card itself (Pi 4 one camera connector, RP1 overclock, DPI) is in another unit; this slice only calls `loadBootConfig` |
| Time left floors "like the touch UI" | hunk 8 | comment names a UI C++ class |
| None of: gpiochip numbers, I2C bus numbers, RAM size, fan, PCIe | slice | none seen here |

## Open points for stage 2

| Point | Command to settle |
| --- | --- |
| Where Clear HDR availability (cDNG/MLV only, no photo mode) lives after hunk 2 | `grep -n "function imx585BaseResolutionOptions" -A30 src/web/WebControlPage.cpp` |
| Fork-log has no row for 9a081dd, 66b324d, 8a56545 | `grep -n` in `apertar-kb/fork-log.md` returned none (checked) |
| Whether `media_alive` fallback is still needed | grep Core `media_mounted` emit sites |
