# C6 conventions: the touch UI's QML (Apertar-UI upstream-1.6.0)

Source: `/home/user/wt/ui-upstream` at tag `upstream-1.6.0` (`43888e5`). All refs below are `@upstream-1.6.0` unless marked.
Paths are repo-relative (`qml/...`, `src/...`). Every line was read in code (confirmed) unless labelled.
Giant files (`SettingsPage.qml` 9851, `CameraPage.qml` 4160) were read only around grep anchors.

Strength: **always** = no counter-example found (search named); **usually** = exceptions named; **once** = one precedent.
Kind: **S** structure, **I** idiom, **N** intent.

---

## 1. Page structure

| Page | File | How it lives | Evidence |
| --- | --- | --- | --- |
| Root window | `qml/Main.qml` (945) | `Window`; no StackView. `currentPage` string `"camera"/"browser"/"player"` + `settingsOpen` bool | `Main.qml:16-18` |
| Camera | `qml/CameraPage.qml` | Always instantiated, never in a Loader | `Main.qml:496-517` |
| Settings | `qml/SettingsPage.qml` | Overlay `Loader` over the camera page, retained after first open, preloaded by timer, faded/slid in | `Main.qml:535-578` (`active: currentPage==="camera" && settingsPageRetained` `:539`), scrim `:519` |
| Clip browser | `qml/ClipBrowserPage.qml` | `Loader { active: currentPage === "browser" }`, clears thumb cache on deactivate | `Main.qml:580-607` |
| Clip player | `qml/ClipPlayerPage.qml` | `Loader { active: currentPage === "player" }`, stops playback on deactivate | `Main.qml:609-640` |
| HDMI monitor | `qml/ExternalMonitorWindow.qml` | Separate root `Window`, loaded by C++ (`ExternalMonitorManager`) or as the root of the monitor-only process | ui-map 1.5; `src/main.cpp:155` |

Page contract: each page gets `displayLayout: root.displayLayout` from Main (`Main.qml:502`, `:571`, `:595`, `:625`), emits
`backRequested` / `*Requested` signals, and Main switches `currentPage` (`Main.qml:506-509`, `:574`, `:597`, `:627-631`).

## 2. Rules

### STRUCTURE

| id | Rule | Strength | Evidence |
| --- | --- | --- | --- |
| S1 | Navigate by setting `Main.currentPage` / `Main.settingsOpen` from a child signal; never push pages, never let a page switch itself. | always (grep `StackView`, `push(` in `qml/`: 0 hits) | `Main.qml:16-17`; `Main.qml:506-509` `onOpenClipBrowserRequested: { root.settingsOpen = false; root.currentPage = "browser" }`; `Main.qml:314-322` hardware `settings`/`clip_browser` actions route the same way |
| S2 | Non-camera pages are `Loader`s that are inactive (destroyed) when not shown and free their caches in `onActiveChanged`; only Settings is retained. | always (all 3 page Loaders) | `Main.qml:584-590` `clearCache()`; `Main.qml:613-621` `playbackController.stop()`; `Main.qml:539` retained settings |
| S3 | A settings item is one `Component { id: <section><Name>Component }` in `SettingsPage.qml`, found through a `<section>ComponentForId(itemId)` if-chain and built by a `Loader` inside a section `Column` whose `Repeater` runs over `normalizedSectionOrder("<Section>")`. | always (9 dispatch functions, 31+16 item cards) | dispatch `SettingsPage.qml:2216-2229`, `:2318-2384`; Column `:6647-6692` (`Repeater` `:6684-6691`); same shape `systemColumn` `:6695-6740` |
| S4 | The list of items in a section is declared three or four times by hand and must agree: `default<Section>Order` (`:771-837`), `sectionItemTitle` (`:1064-1124`), `<section>ComponentForId` (`:2216-2384`), and optionally `favoriteCandidateOrder` (`:838-878`). | always (rough edge: the lists drift, see S4-gaps) | `SettingsPage.qml:771`, `:1064`, `:2216`, `:838` |
| S4-gaps | Drift that exists upstream: `lutPreview` has no `sectionItemTitle` entry (falls back to the id, `:1121-1123`); `lutPreview`, `exposureCompensation`, `displayCalibration` are not in `favoriteCandidateOrder`. Do not "fix" unasked. | once each | `SettingsPage.qml:1065-1076` vs `:772-783`; `:838-878` |
| S5 | A section is wired by hand in about 10 if-chains keyed by the section's display name string (`"Monitoring"`, `"Wi-Fi"`, `"Power"`...). | always | `defaultOrderForSection` `:954-972`, `storedOrderForSection` `:974-996`, `applySectionOrder` `:1040-1062`, `sidebarIconForId` `:1126-1137`, `sourceSectionForItemId` `:1161-1170`, `favoriteComponentForId` `:2373-2383`, `defaultSidebarOrder` `:827-837`, Column `:6647` |
| S6 | Per-section order lists persist in `UI.conf` through `SettingsBridge` `QStringList` properties (`monitoringOrder` ... `favoritesOrder`), loaded, saved and serialised into presets like any other UI setting. | always (9 lists) | `src/SettingsBridge.hpp:81-89`; load `src/SettingsBridge.cpp:399-407`; setter `:1574-1582`; preset `:2097-2105`, `:2178-2186` |
| S7 | Monitoring aids and UI preferences are `SettingsBridge` `Q_PROPERTY(... READ WRITE NOTIFY)`; QML writes them by plain assignment (`root.settingsState.zebraEnabled = ...`); the bridge persists to `UI.conf`. No socket command. | always for Monitoring (ui-map 1.1 bridge column) | `SettingsPage.qml:2704-2707`; `src/SettingsBridge.hpp:17`; `src/SettingsBridge.cpp:597-607` |
| S8 | Camera settings that Core owns are changed only through `apertarControlBridge.apply<Thing>(displayString)`; QML never builds a command or JSON. | always (grep `sendCoreCommand` in `qml/`: 0) | `SettingsPage.qml:3209-3211` `applyRecordingFormat(v)`; `CameraPage.qml:2908-2910` `applyFps(v)`, `:2940-2942` `applyIso(v)` |
| S9 | QML hands display strings (`"1/48"`, `"172.8°"`, `"800"`, `"5600K"`) to the bridge; the C++ bridge parses them into Core units. | always for top stats | `CameraPage.qml:492-511` option lists; `src/ApertarControlBridge.cpp:291-311` `applyIso` → `parseIsoValue` → `set_iso` |
| S10 | Per-sensor resolution / crop tables are copied into both `CameraPage.qml` and `SettingsPage.qml` (and Core); the copies must be edited together. | always (rough edge) | `CameraPage.qml:377-381` and `SettingsPage.qml:110-114`, identical `imx477ResolutionOptions` |
| S11 | `ExternalMonitorWindow.qml` re-derives camera-page values itself from the bridges (format, fps, iso, shutter, wb, remaining, guides, status colours, timecode formatting) instead of reading the camera page; only recording/timelapse/timecode come from the camera page, via `Main.monitor*` and `monitorRuntimeBridge`. | always | `ExternalMonitorWindow.qml:44-169`; `Main.qml:36-38` `monitorRecordingActive: cameraPage.recording`; `ExternalMonitorWindow.qml:26-31`, `:172-175` |
| S12 | A visual element shared by touch UI and HDMI is a small standalone `.qml` file used in both (`DroppedFrameWarning`, `StillExposureOverlay`, `HorizontalLevelOverlay`, `FalseColorLegend`); the HDMI window otherwise re-draws its own HUD (no `StatusChip`, no `InfoLine`). | usually (exception: status pill duplicated, `ExternalMonitorWindow.qml:150-161` vs `StatusChip.qml:44-48`) | `CameraPage.qml:2569-2577` and `ExternalMonitorWindow.qml:1103-1107` `DroppedFrameWarning` |
| S13 | Bridges are context properties. Pages receive the main ones as properties (`settingsState`, `bridge`, `controlBridge`); components and the settings page use the rest as bare globals guarded by `typeof X !== "undefined"`. | usually (SettingsPage uses bare `apertarControlBridge`, CameraPage uses `root.controlBridge`) | `Main.qml:498-501`; `SettingsPage.qml:3198` bare global; typeof guards: 39 in SettingsPage, 20 CameraPage, 13 ExternalMonitorWindow, 4 in each leaf component |
| S14 | Leaf components compute their own layout flags from `displayConfigBridge.uiLayout`; pages compute them from the `displayLayout` property. | always (all 7 sized leaf components) | `TogglePill.qml:7-17`, `ActionTile.qml:14-23`, `SystemSectionCard.qml:7-16`, `SettingsChoice.qml:17-27`, `InlineDropdownField.qml:16-26`, `MonitoringRow.qml:14-22`, `AdjustNumberTile.qml:8-17`; pages `SettingsPage.qml:18-27`, `CameraPage.qml:38-54` |
| S15 | Each QML file is registered twice: `APERTAR_QML_FILES` in `CMakeLists.txt` (AOT build, `qt_add_qml_module` `:137-147`) and `qml.qrc` (non-AOT/cross build, `:150`). Fonts and icons are in `resources.qrc`. | always as a practice; drift exists | `CMakeLists.txt:19-52`, `:137-151`; `qml.qrc` |
| S15-drift | `DroppedFrameWarning.qml` is in CMake (`CMakeLists.txt:40`) but not in `qml.qrc` (non-AOT build would fail to resolve the type: **probable**, settle with a `-DAPERTAR_QML_AOT=OFF` build). `InlineChoice.qml` is on disk, in neither list, used nowhere. `GyroOrientationIndicator.qml` is in both lists and used nowhere. | once each | grep results; `qml.qrc` |

### IDIOM

| id | Rule | Strength | Evidence |
| --- | --- | --- | --- |
| I1 | Sizes are inline nested ternaries per layout flag, largest first: `largeLandscape ? A : (standardLandscape ? B : (compact ? C : D))`; the last value is the square layout. No theme file, no scale factor. | always (grep `pragma Singleton`: 0) | `TogglePill.qml:20-21`; `SystemSectionCard.qml:26-27`; `SettingsPage.qml:28-59`; `CameraPage.qml:109-125` |
| I2 | Page-wide size tokens are `readonly property int <area><Thing>` at the top of the page (`settingsSidebarWidth`, `topStatHeight`, `topDropdownPopupOptionHeight`), passed into components as properties. | always on pages | `SettingsPage.qml:28-59`; `CameraPage.qml:107-213`; `CameraPage.qml:2886-2898` passes tokens into `TopDropdownStat` |
| I3 | Layout flag names differ per file and `standardLandscape` does not mean the same everywhere: SettingsPage = `landscape` only, CameraPage/Main = `landscape` or `landscape_large`. Copy the flag block of the file you are in. | always (rough edge) | `SettingsPage.qml:23`; `CameraPage.qml:46-47`; `Main.qml:43-44` |
| I4 | Colours are inline hex literals; translucency is `#AARRGGBB`. The working palette: card `#181818`/`#171717`/`#151515`, card border `#1affffff` (167 uses), secondary text `#66ffffff`/`#8cffffff`/`#8f9096`, pressed `#20ffffff`/`#24ffffff`, idle fill `#14ffffff`, accent cyan `#3fd0ff` (+ fill `#1f2c36`/`#123d59`), danger `#8d2020`/`#a32828`/`#ba4a4a`, favourite gold `#e0b447`, scrim `#cc000000`, status green `#00c951`, red `#fb2c36`, amber `#ffd54a`. | always (no colour constants file) | frequency count over `qml/*.qml`; `ActionTile.qml:30-39`; `StatusChip.qml:44-45`; `Main.qml:522` scrim |
| I5 | Fonts: Inter (Regular/Medium/Bold) via a `FontLoader` declared in each file that uses it (`id: interRegular/interMedium/interBold`); Gotham Bold only for two big display numerals. Titles Bold, labels Medium, body Regular. | usually (`SettingsMenuItem.qml:44` uses `interMedium` without its own loader, relying on the parent scope) | `SystemSectionCard.qml:30-32`; `ActionTile.qml:42`; `Main.qml:469-472`; `CameraPage.qml:2098`, `Main.qml:825` Gotham |
| I6 | Every `Text` sets `renderType: Text.NativeRendering`. | usually (389 of 403 `Text {` blocks) | `TogglePill`-family; e.g. `SystemSectionCard.qml:166`, `AdjustNumberTile.qml:36` |
| I7 | Radii: pills use `height / 2`; cards 18-30, fields 14-24, tiles 15-24, all layout-scaled by I1. | always for pills | `TogglePill.qml:22`; `DroppedFrameWarning.qml:7`; `MonitoringRow.qml:108`; `SettingsChoice.qml:66` |
| I8 | Ids are camelCase with a role suffix: `...Area` (MouseArea, 90), `...Component` (42), `...Column` (41), `...Overlay`, `...Timer`, `...Anim`, `...Card`, `...Flick`; root is always `id: root`. | always for `root`; usually for suffix | id survey; `SettingsPage.qml:2686`, `CameraPage.qml:3690` `clipBrowserBtn` (exception: `Btn`) |
| I9 | Signals are past-tense events or `<thing>Requested`: `toggleRequested`, `backRequested`, `pressAndHoldRequested`, `favoriteToggleRequested`, `valueSelected(string value)`, `optionSelected(string value)`, `clicked()`. Components emit; the owner decides. | always | `MonitoringRow.qml:93-102`; `SettingsChoice.qml:33`; `TopDropdownStat.qml:22-23`; `ClipPlayerPage.qml:64-67` |
| I10 | Functions are verb-first: `apply<X>`, `open<X>Confirmation`, `execute<X>`, `normalized<X>`, `update<X>`, `refresh<X>`, `sync<X>FromBridge`, `<x>Label`, `<x>To<y>` converters. | always in the inspected chapters | `SettingsPage.qml:999`, `:1282`, `:1657`, `:1695`; `CameraPage.qml:1555`, `:1583` |
| I11 | Bridge reactions use `Connections { target: ...; function on<Signal>(args) {...} }` (Qt 6 form), and each handler re-checks the bridge and empty strings before copying into a local mirror property. | always (no old-style `onFoo:` inside `Connections` seen) | `CameraPage.qml:1824-1860`; `CameraPage.qml:1555-1581` `syncControlValuesFromBridge` |
| I12 | Bridge reads are null-guarded with a default: `root.settingsState ? root.settingsState.zebraEnabled : false`. | always | `SettingsPage.qml:2697`; `CameraPage.qml:1981-1982`; `ExternalMonitorWindow.qml:374-375` |
| I13 | Handlers for choice signals use `function(v) { ... }`. | always in SettingsPage/CameraPage | `SettingsPage.qml:2708`, `:3209`; `CameraPage.qml:2907` |
| I14 | No logging from QML. | always (grep `console.` in `qml/`: 0) | grep |
| I15 | Comments are rare: banner blocks `// =====` / `// NAME` / `// =====` to mark page chapters, plus one-line "why" notes on non-obvious constraints. | usually (only 7 files carry comments) | `CameraPage.qml:1961-1963`, `:2546-2547`; why-notes `CameraPage.qml:1356`, `:1391`, `:2580` |
| I16 | Formatting is inconsistent in the big files: column-0 functions inside `Item { id: root }`, tab-indented lines, mis-indented blocks. Match surrounding code; do not reformat. | always (rough edge) | `CameraPage.qml:8` (tab), `:1555` (col 0), `:3024-3027` (tabs); `Main.qml:487-494` (wrong indent inside `uiScene`) |
| I17 | Animations: `Behavior on <prop>` with `NumberAnimation`/`ColorAnimation`, 120-240 ms, `Easing.OutCubic` (218 of 231 easing uses). Press feedback = `scale: area.containsPress ? 0.95..0.985 : 1.0` plus colour change. Page overlay 360-520 ms. | always for easing family; usually for duration | `TogglePill.qml:30-56`; `AdjustNumberTile.qml:67-71`; `Main.qml:526-562`; count: 66x `140`, 38x `220`, 34x `180` |
| I18 | Option lists are either plain string arrays or arrays of `{ value, label, enabled }` objects; components accept both (`optionLabel` / `optionValue` / `optionEnabled`). | always (InlineDropdownField, CameraPage quick menu) | `InlineDropdownField.qml:41-63`; `SettingsPage.qml:3199-3206`, `:3225-3229`; `CameraPage.qml:378-381` |
| I19 | UI-only setting values are stored as their display strings (`"1 min"`, `"Assist Feed"`, `"Thirds"`, `"Light"`); converters exist only where the renderer needs a number (zebra `%` → threshold, false-colour name → int). | usually (exception: standby timeout stores seconds behind `{value: "60", label: "1 min"}`, `SettingsPage.qml:4570`) | `SettingsPage.qml:4538` sleepMode; `ExternalMonitorWindow.qml:49`; converters `SettingsPage.qml:1282-1347`, `:2709-2711` |

### INTENT

| id | Rule | Strength | Evidence |
| --- | --- | --- | --- |
| N1 | Show only what the hardware/Core supports: unsupported choices are removed from the option list, driven by a bridge capability property. | usually | `SettingsPage.qml:3198-3206` (`rawRecordingSupported`, `proresSupported`); `CameraPage.qml:484-490` per-sensor resolution list; `SettingsPage.qml:3178` crop field `visible:` only with `sensorCropControlsAvailable`; README.md:152 "Options depend on what the connected hardware actually supports" |
| N2 | When a whole item is not usable now, keep it visible but dimmed (`available: false`, card opacity 0.42, choice 0.38, tile 0.45), block input, and say why in the description. | always for the three mechanisms | `MonitoringRow.qml:110`, `:478-482` input shield; `SettingsChoice.qml:43`; `ActionTile.qml:40`; `SettingsPage.qml:3040-3043` "No audio input device detected" |
| N3 | A single value that is not allowed in the current mode is greyed inside the list (`enabled:` per option) and the handler re-checks before applying. | once-plus (bit depth) | `SettingsPage.qml:3226-3228`, re-check `:3237-3238`; `InlineDropdownField.qml:201`, `:215` |
| N4 | During a take, recording-format, audio-device and power-state controls are disabled in the UI (`fieldEnabled: ... && !apertarControlBridge.recording`); the clip browser button is disabled while recording. | usually (exception: the hardware `clip_browser` action, `Main.qml:320-323`, and the settings button `CameraPage.qml:3030-3036` are not gated) | `SettingsPage.qml:3230`, `:3257`, `:3281`, `:3303`, `:3945-3988`, `:5418`; `CameraPage.qml:3697` |
| N5 | Destructive actions need two steps: a red `tone: "danger"` tile and a confirmation popup; Format Media adds hold-to-activate. | always (Format, Eject, Restart, Shutdown, Delete Preset) | `SettingsPage.qml:5177-5184` (hold 950 ms → `openFormatConfirmation`); `:5428-5438` `openPowerConfirmation`; popups `:8711`, `:8948`, `:9180`, `:8016` |
| N6 | Failures are loud and modal on the camera page: a warning card with title, subtitle, detail title and detail body (`showRecordWarning`). Settings failures get their own result popup (`...ErrorOpen`). | always for capture failures | `CameraPage.qml:1656-1662`, `:1827-1836`; `SettingsPage.qml:9315`, `:9468`, `:9622`, `:9699`, `:9776` |
| N7 | Hidden UI does no background work: section-specific polling starts only when that section is visible and the page is open, Repeaters build cards only for the visible section, and pages release work when closed. | always | `SettingsPage.qml:2139-2151` `updateSectionActivity`; `:889-910`; `:6684-6686` model `[]` unless selected; `Main.qml:93` `releaseSettingsBackgroundWork`; `Main.qml:584-590` |
| N8 | The HDMI monitor has two modes: Clean Feed (no aids) and Assist Feed (aids on); info HUD is separate and suppressed by SMPTE. Monitoring aids never reach the recording. | always | `ExternalMonitorWindow.qml:48-53`, `:374-387` every aid ANDed with `overlayFeedEnabled`, `:785`; README.md:107 |
| N9 | Status vocabulary is fixed and colour-coded: `NO MEDIA` amber, `TIMELAPSE`/`REC` red, `WRITING` amber, `READY` green; the same words on touch UI and HDMI. | always | `StatusChip.qml:44-48`; `ExternalMonitorWindow.qml:154-161` |
| N10 | The operator customises the settings UI (reorder by long press, favourites) and that layout is a persisted, preset-able setting. | always | `SettingsPage.qml:6677` hint text; `MonitoringRow`/`SystemSectionCard` `pressAndHoldRequested` + `favoriteToggleRequested`; `src/SettingsBridge.cpp:2097-2105` |
| N11 | Text style: card titles in Title Case, 1-3 words (`"Auto Power Off"`, `"Focus Peaking"`); descriptions are one short sentence fragment in sentence case without a final period (37 of 42; the 5 with periods are multi-sentence); section eyebrow + title + hint header per section; labels on dark HUD are UPPERCASE via `font.capitalization: Font.AllUppercase` and letter spacing 1.8-2.8; progress labels end with three ASCII dots (`"Scanning..."`, `"Hold..."`); units are glued to the value (`"70%"`, `"5600K"`, `"172.8°"`, `"1 min"`). | usually (exceptions named) | `SettingsPage.qml:2694-2695`, `:4526-4528`; eyebrow `:6659-6675`; `AdjustNumberTile.qml:234-235`; `SettingsPage.qml:5571`; `ActionTile.qml:11` |

## 3. Reusable components, when each is used

| Component | Use it for | Used in | Key API |
| --- | --- | --- | --- |
| `MonitoringRow` | A settings card whose primary control is an on/off toggle, with up to 4 dropdown choices and up to 3 secondary toggles (any section, not only Monitoring) | 16x SettingsPage | `title`, `titleIconSource`, `description`, `enabled`, `available`, `choiceN{Label,Value,Options,Available}`, signals `toggleRequested`, `choiceNSelected`, `secondary/tertiary/quaternaryToggleRequested` (`MonitoringRow.qml:6-102`) |
| `SystemSectionCard` | A settings card without a header toggle; free content goes into its default property (dropdowns, tiles, data rows) | 31x SettingsPage | `title`, `titleIconSource`, `description`, `default property alias contentData` (`SystemSectionCard.qml:19`) |
| `TogglePill` | The on/off switch; emits `toggled(!checked)`, owner writes state | MonitoringRow (4), SettingsPage (3), DisplayCalibrationPanel (1) | `checked`, `toggled(bool)` |
| `SettingsChoice` | A dropdown inside a `MonitoringRow` (internal to it) | MonitoringRow only | `options`, `optionDisplayFormatter`, `available`, `valueSelected` |
| `InlineDropdownField` | A dropdown inside a `SystemSectionCard` or a free layout; supports per-option `enabled`; `fieldEnabled` for the whole field | 33x SettingsPage, 1x DisplayCalibrationPanel | `options` (strings or `{value,label,enabled}`), `fieldEnabled`, `openUpwards`, `popupParent: dropdownOverlay`, `dropdownController: sharedDropdownController` |
| `ActionTile` | A button inside a card; `tone: "default"/"accent"/"danger"`; optional hold-to-activate | 23x SettingsPage | `label`, `tone`, `actionEnabled`, `holdToActivate`, `holdDuration`, `clicked` |
| `AdjustNumberTile` | A `- value +` stepper | 6x SettingsPage, 1x DisplayCalibrationPanel | `label`, `value`, `decrementRequested`, `incrementRequested` |
| `InfoDataRow` | Read-only label/value row in Info cards | 10x SettingsPage | |
| `SettingsMenuItem` | Sidebar entry | 1x SettingsPage (sidebar delegate) | `label`, `iconSource`, `active`, `compact/large/oversized` |
| `TopDropdownStat` | The four top camera stats (FPS, ISO, shutter, WB) with their popups | 4x CameraPage | `value`, `options`, `isOpen`, size tokens from the page, `toggleRequested`, `optionSelected` |
| `StatusChip` | REC/READY/NO MEDIA chip on the touch UI | 1x CameraPage | `recording`, `timelapse`, `writing`, `mediaMounted`, scale flags |
| `InfoLine` | Bottom-corner stats (FORMAT, MEDIA, CPU, POWER) | 4x CameraPage | `label`, `value`, `sub`, `iconSource`, size tokens |
| `DroppedFrameWarning` | Shared warning badge | CameraPage + ExternalMonitorWindow | `height`, `visible` |
| `InlineChoice` | Unused (dead file) | none | |

Dropdowns in Settings share one popup layer and one "only one open" controller: `popupParent: dropdownOverlay` +
`dropdownController: sharedDropdownController` on every card (`SettingsPage.qml:2690-2691`, `:3206-3207`, `:4537-4538`;
overlay `:7198`). CameraPage uses a string `root.openDropdown` for the same purpose (`CameraPage.qml:2898-2911`).

## 4. Layout modes and size derivation

- `DisplayConfigBridge` normalises `ui_layout` to one of `square`, `landscape_compact` (640x480/800x480), `landscape_medium` (1024x600), `landscape` (1280x720), `landscape_large` (1920x1080), `portrait_compact`, `portrait`, `portrait_large`; default `square` (720x720). `src/DisplayConfigBridge.cpp:307-316`, `:480-523`.
- Main publishes `displayLayout` (`Main.qml:41`) and rotation (`Main.qml:56-61`, `uiScene` `Rotation` `:481-485`). `uiOrientation` (`"Left Side"`, `"Right Side"`, `"Upside Down"`) adds to the panel rotation.
- Square is the "else" branch of every ternary and the original design target: CameraPage hard-codes it (`previewTopOffset: rectangularLayout ? 0 : 157`, `previewVisibleHeight: ... : 405`, `CameraPage.qml:107-108`).
- Portrait is handled on CameraPage only (`CameraPage.qml:50-54`); Settings/components treat portrait like square (no portrait flag in them). **probable**: settle by grepping `portrait` in `SettingsPage.qml` (0 hits found).
- HDMI window has no layout modes: fixed pixel sizes (font 13/20/34/42), positions as fractions of the window (`ExternalMonitorWindow.qml:249-265`).

## 5. How QML calls bridges and reacts

| Direction | Pattern | Evidence |
| --- | --- | --- |
| UI setting write | `root.settingsState.<prop> = v` | `SettingsPage.qml:2706` |
| Core setting write | `apertarControlBridge.apply<X>(displayString)` / `root.controlBridge.apply<X>(v)` with a local fallback when the bridge is absent | `CameraPage.qml:2938-2943` |
| Read for display | direct binding to a bridge NOTIFY property, null-guarded | `ExternalMonitorWindow.qml:89-91` |
| Read with local mirror | page keeps `property string iso`, filled by `Connections` + `syncControlValuesFromBridge` | `CameraPage.qml:341`, `:1844-1847`, `:1555` |
| Bridge events | `Connections { function onRecordingFailed(error) }` → modal warning | `CameraPage.qml:1827-1830` |
| C++ reads QML by name | `objectName: "previewItem"`, `"previewContainer"`, `"externalPreviewItem"`; `Main.monitor*` properties | ui-map 2.1 "Implicit name contracts"; `Main.qml:35-38` |

## 6. HDMI window repeats camera-page information

| Camera page | HDMI window | Shared? |
| --- | --- | --- |
| `TopDropdownStat` FPS/ISO/SHUTTER/WB + FORMAT InfoLine | `topMonitorInfoItems` (5 fixed entries) in a Repeater; X positions hard-coded for 5 slots (`positions = [0.29, 0.50, 0.71]`) | No. Own copy `ExternalMonitorWindow.qml:163-169`, `:249-265` |
| `StatusChip` | `statusRow` with `externalStatus*` properties | No. Duplicate logic `:150-161`, `:1063-1108` |
| `DroppedFrameWarning` | same component | Yes `:1103` |
| Timecode (computed in CameraPage) | `monitorRuntimeBridge.timecode` or own `formatTimecode` fallback | Copy `:214`, `:172-175` |
| MEDIA remaining | `remainingColumn` | Own `:119-121`, `:1140` |
| Aids in preview | `CameraPreviewItem` bindings, ANDed with `overlayFeedEnabled` | Same C++ type, own bindings `:367-389` |

Monitor-only process: `gyroConfigBridge` absent, `audioMeterBridge` null (ui-map 1.5; `src/main.cpp:147-154`), so every HDMI use is `typeof`-guarded (13 guards).

## 7. qml.qrc versus disk

| File | Disk | `qml.qrc` | `CMakeLists` `APERTAR_QML_FILES` | Used |
| --- | --- | --- | --- | --- |
| 31 others | yes | yes | yes | yes |
| `DroppedFrameWarning.qml` | yes | **no** | yes (`:40`) | CameraPage, HDMI |
| `InlineChoice.qml` | yes | no | no | no |
| `GyroOrientationIndicator.qml` | yes | yes | yes | no |
| fonts/icons | yes | `resources.qrc` (48 icons = 48 on disk) | via `resources.qrc` in `add_executable` (`:63-68`) | |

---

## 8. Recipes

### R1. Add a settings toggle (UI-only, e.g. a new monitoring aid)
1. `src/SettingsBridge.hpp:17-92`: add `Q_PROPERTY(bool fooEnabled READ fooEnabled WRITE setFooEnabled NOTIFY fooEnabledChanged)`, getter (`:99`), signal (`:307`), member `m_fooEnabled = false` (`:414`).
2. `src/SettingsBridge.cpp`: load in the constructor (`:324` pattern), re-read in `pollExternalSettings` (`:520`), setter copied from `setZebraEnabled` (`:597-607`), preset save (`:2033`) and preset apply (`:2121`).
3. `qml/SettingsPage.qml`: add the id to `default<Section>Order` (`:771-826`), a title in `sectionItemTitle` (`:1064-1124`), and to `favoriteCandidateOrder` (`:838-878`) if it may be a favourite.
4. Same file: add a `Component { id: <section>FooComponent; MonitoringRow {...} }` copied from `monitoringSmpteComponent` (`:2785-2805`): `reorderSectionName`, `title`, `titleIconSource`, one-line `description`, `enabled:` bound to `root.settingsState.fooEnabled`, favourite wiring, `onToggleRequested` assignment.
5. Same file: add the id → Component line to `<section>ComponentForId` (`:2216-2229`).
6. Icon: PNG into `qml/icons/` and `resources.qrc`.
7. Consume the property where it acts: `CameraPreviewItem` binding on `CameraPage.qml:1981-1995` and, if HDMI should show it, `ExternalMonitorWindow.qml:374-387` ANDed with `root.overlayFeedEnabled`.
8. Optional quick-menu slot: see R3b.
If the toggle is a Core setting, replace steps 1-2 with an `apply<Foo>` invokable on `ApertarControlBridge` (ui-map 2.2 table) and bind `enabled` to its read-only property; gate with `!apertarControlBridge.recording` if it must not change during a take (N4).

### R2. Add a settings section
1. `src/SettingsBridge.hpp:81-89` / `.cpp:399-407`, `:1569-1690`, `:2097-2105`, `:2178-2186`: add `fooOrder` `QStringList` property, load, setter, preset save/apply.
2. `qml/SettingsPage.qml:771-837`: add `defaultFooOrder` and the section name in `defaultSidebarOrder` (`:827`).
3. Same file, extend each if-chain: `defaultOrderForSection` (`:954`), `storedOrderForSection` (`:974`), `applySectionOrder` (`:1040`), `sectionItemTitle` (`:1064`), `sidebarIconForId` (`:1126`), `sourceSectionForItemId` (`:1161`), `favoriteComponentForId` (`:2373`).
4. Add `fooComponentForId` next to the others (`:2318-2371`) and one Component per item (R1 step 4).
5. Add a section `Column` inside `sectionFlick` copied from `monitoringColumn` (`:6647-6692`): eyebrow text (uppercase via `font.capitalization`), title, the "Long press an option tile to reorder this section" hint, `Repeater` with model `[]` unless selected.
6. If the section needs polling, start/stop it in `updateSectionActivity` (`:2139-2151`) and `onSelectedSectionChanged` (`:889-910`), never unconditionally.
7. Sidebar icon PNG in `qml/icons/` + `resources.qrc`.

### R3. Add a value to a quick-menu picker
a) Top stat picker (FPS/ISO/shutter/WB):
1. Add the display string to the option list in `qml/CameraPage.qml:492-513` (`shutterOptions`, `isoOptions`; FPS via `availableFpsOptions` `:802` and the per-sensor limit tables `:646-828`).
2. Make sure the bridge parses it: `src/ApertarControlBridge.cpp` `parse<X>Value` (`:1761-2216`) and `apply<X>` (`:255-408`); Core must accept the converted value.
3. If a mode limits it, add the limit to the mode gate (`losslessIsoLimitedMode` `:499-513`), not to the handler.
4. HDMI shows the value through `topMonitorInfoItems` automatically (bridge property); no change unless the label format changes.
b) Quick-menu slot toggle (6 fixed slots, `quickMenuButtonCount: 6` `:552`): add a branch to `quickMenuSlotIconSource` (`:583`), `quickMenuSlotActive` (`:599`), `triggerQuickMenuSlot` (`:617`) and raise `quickMenuButtonCount`; slots write `settingsState.*Enabled` only.
c) Resolution/crop picker: add the entry to the per-sensor table in **both** `CameraPage.qml:377-483` and `SettingsPage.qml:110-225` (they are copies), plus `parseResolutionValue` (`src/ApertarControlBridge.cpp:1797-2006`) and the FPS limit for it (`CameraPage.qml:646-828`).

### R4. Add a status element to the camera page and the HDMI window
1. Expose the state as a bridge NOTIFY property (Core state → `ApertarControlBridge::applyCoreState`, ui-map 1.6), or a `SettingsBridge` property for a UI preference.
2. If the element looks the same on both screens, make a small standalone `qml/Foo.qml` like `DroppedFrameWarning.qml` (`Rectangle`, own `FontLoader`, size from `height`, `Accessible.name`), register it in **both** `CMakeLists.txt` `APERTAR_QML_FILES` (`:19-52`) and `qml.qrc`.
3. Camera page: place it in the STATUS CHIP chapter next to `captureStatusChip` (`CameraPage.qml:2549-2577`), anchored to the chip, `opacity: root.effectiveControlsOpacity`, sized from page tokens, `visible:` from `root.controlBridge ? ... : false`.
4. HDMI window: place it in `statusRow` (`ExternalMonitorWindow.qml:1063-1108`) inside the info HUD (`visible: infoOverlayEnabled && !smpteEnabled` `:785`), fixed pixel size, bridges guarded with `typeof`/null checks (monitor-only process lacks some bridges).
5. A new text stat on the HDMI top row means a 6th `topMonitorInfoItems` entry (`:163-169`) and new positions in `topHudX` (`:256-265`, hard-coded for 5 slots); on the camera page a new corner stat is another `InfoLine` in BOTTOM STATS (`CameraPage.qml:3563-3659`).
6. If the HDMI needs a value that only the camera page computes, publish it as a `readonly property` on `Main.qml` (`:35-38` pattern) and read it in `ExternalMonitorRuntimeBridge` (C++), not by reaching into `cameraPage` from the HDMI QML.

---

## Challenge

Challenger pass over the rules above, against `/home/user/wt/ui-upstream` at `upstream-1.6.0` (`43888e5`). All refs `@upstream-1.6.0`.
`qml/` holds 32 `.qml` files plus `TimelapseIntervals.js` (not 34).

### Verdict per rule

| id | Verdict | Counter-example / added evidence |
| --- | --- | --- |
| S1 | holds (always) | grep `StackView`, `SwipeView`, `Drawer {` in `qml/`: 0. No page writes `currentPage`/`settingsOpen` (grep outside `Main.qml`: 0). Main also closes Settings itself on leaving the camera page (`Main.qml:74-84`) and on standby (`Main.qml:194-199`); clip selection state lives in Main (`selectClip` `Main.qml:417-424`, page emits `clipOpened` `Main.qml:602-604`). |
| S2 | holds (always) | 3 page Loaders, all `active:` bound to `currentPage` (`Main.qml:539`, `:584`, `:613`); settings retention is cleared when leaving camera (`Main.qml:80`). |
| S3 | weaken to usually | Presets section is built inline: hand-written cards and a `Repeater` over `settingsState.presetNames`, no `presetsComponentForId`, no order list (`SettingsPage.qml:6745-6933`). Component id prefix does not always name the section: System section items `battery`/`batteryInfo`/`autoPowerOff` return `power*Component`, Power section items `media`/`formatMedia`/`mediaSpeed` return `system*Component` (`SettingsPage.qml:2336-2353`). |
| S4 | holds (always, reorderable sections) | Reason it is safe to add: `normalizedSectionOrder` drops stored ids not in the default list and appends new defaults at the end (`SettingsPage.qml:999-1036`), so no migration is needed for a new id. |
| S5 | holds (always), chain list incomplete | More section-name chains: `contentHeight` ternary on `sectionFlick` (`SettingsPage.qml:6485-6501`), `updateSectionActivity` (`:2139-2151`), `onSelectedSectionChanged` (`:889-917`), each section `Column` `visible:`/`model:` (`:6651`, `:6685`, ... `:7162`). |
| S6 | holds (always) | 9 lists = 7 reorderable sections + Sidebar + Favorites. Presets has none. |
| S7 | holds (always) | All 25 writes in the Monitoring components are `root.settingsState.<prop> = ...` (`SettingsPage.qml:2386-2915`); System preferences the same (`:4544`, `:4630`, `:4679`). |
| S8 | weaken to usually | `ClipBrowserPage.qml:115-119` `toggleCaptureMode()` writes `settingsState.photoModeEnabled` without `applyPhotoModeEnabled`; the Settings toggle calls Core first (`SettingsPage.qml:2983-2989`). No QML builds commands (grep `sendCommand`, `JSON.stringify` in `qml/`: 0). Not every call is `apply<X>`: actions are verbs (`capturePhoto`, `setRecording`, `setTimelapseActive`, `calibrateGyro`, `enterStandby`). |
| S10 | holds (always) | Tables byte-identical; the derived properties around them are renamed copies (`CameraPage.qml:448` `root.resolution` vs `SettingsPage.qml:181` `root.recordResolution`), so a blind copy-paste between the files breaks. |
| S11 | holds (always), list incomplete | C++ also reads `currentPage`, `standbyActive` and `powerButtonShutdown*` from Main by name (`src/ExternalMonitorRuntimeBridge.cpp:137-153`, `src/ExternalMonitorManager.cpp:113-121`, `:288-300`). |
| S12 | holds (usually) | Extra exception: audio meter is `AudioMeterOverlay` on the touch UI (CameraPage only) and an own `hdmiAudioMeterPanel` on HDMI (`ExternalMonitorWindow.qml:945`). Shared files are exactly 4: `DroppedFrameWarning`, `FalseColorLegend`, `HorizontalLevelOverlay`, `StillExposureOverlay`. |
| S13 | weaken wording (stays usually) | `typeof` guards are only for bridges that can be absent. Always-present globals are used bare: `wifiBridge` 81 uses / 0 guards, `powerBridge` 11/0, `mediaBridge` 53/2 in SettingsPage (`SettingsPage.qml:239-242`, `:4984`). |
| S14 | weaken to usually | Camera-page and sidebar components receive flags from the parent instead: `StatusChip.qml:13-14` (`compact`, `largeCompact`), `SettingsMenuItem.qml:10-11`, `TimelapseIntervalPicker.qml:14-15`, `TopDropdownStat` tokens (`CameraPage.qml:2886-2898`). The rule holds for the settings-card family. |
| S15 | holds (usually) | Drift as listed. |
| I1 | weaken to usually | Fixed sizes exist: 32 `font.pixelSize: <n>` in SettingsPage (e.g. Presets hint `:6776` 13 px), 25 in ClipPlayerPage, 20 in ExternalMonitorWindow (HDMI has no layout modes). |
| I2 | weaken to usually | ClipPlayerPage uses fixed literals rather than top-of-page tokens (25 fixed pixel sizes). |
| I3 | holds (always) | Also: SettingsPage `compactLandscapeLayout` is true for every landscape (`SettingsPage.qml:24-26`), so its third ternary branch covers medium too. |
| I4 | weaken to usually | Primary text is the named colour `"white"` (213 uses), `"transparent"` 10; computed colours via `Qt.rgba`/`fadedColor()` in 7 files (`StatusChip.qml:26-27`, `:40-44`). Hex palette still holds for fills and borders. |
| I5 | holds (usually) | Exceptions are 3 files with 0 loaders that rely on the parent's ids: `MonitoringRow.qml`, `SettingsChoice.qml`, `SettingsMenuItem.qml`. |
| I6 | holds (usually) | |
| I8 | holds | `id: root` in all 32 files (grep -L: none missing): always. Suffix: usually (`recordBtn`, `...Button`, `...Text`, `...Label`). |
| I9 | holds (always) | Minor: `RecordButton.qml:19` `signal pressAndHold()`, `AudioLevelCard.qml:24` `levelAdjusted(int)`; both events, owner decides. |
| I10 | weaken to usually, restate | Actions are verb-first, but computed getters are noun phrases (`sectionItemTitle` `SettingsPage.qml:1064`, `sidebarIconForId` `:1128`, `sourceSectionForItemId` `:1161`, `sensorCropOptionsForBase` `CameraPage.qml:1098`) and predicates `is/has/can` (`isFourKResolution` `CameraPage.qml:956`, `hasPreviousClip` `Main.qml:437`). Prefix survey over the 3 big files: `on` 31, `is` 12, `open` 11, `apply` 11, then many noun prefixes (`sensor` 8, `wifi` 6, `lut` 4). |
| I11 | holds (always for syntax) | 23 `Connections` blocks, all `function on<Signal>()`; two leaf components add `ignoreUnknownSignals: true` (`InlineDropdownField.qml:303`, `SettingsChoice.qml:307`). Re-check-before-mirror: usually (CameraPage only keeps mirrors). |
| I12 | weaken to usually | Bare reads of always-present globals: `SettingsPage.qml:239-242` `powerBridge.sensorAvailable`, `Main.qml:205-206` `settingsBridge.sleepMode`, `SettingsPage.qml:6917` `actionEnabled: mediaBridge.mediaMounted`. Guards are reliable for `root.settingsState`, `root.controlBridge` and optional bridges. |
| I14 | holds (always) | grep `console.`, `print(` over `qml/`: 0. |
| I15 | holds (usually), sharpen | Banners exist only in CameraPage (34 comment lines). SettingsPage (9851 lines) has 0 comment lines. Only 7 files carry any comment. grep `TODO|FIXME|XXX` in `qml/`: 0. |
| I16 | holds (always) | More tab lines: `SettingsPage.qml:5764-5765`. |
| I17 | weaken to usually, restate | OutCubic is for entering/state changes. Popup close uses `Easing.InCubic` (`InlineDropdownField.qml:280-296`, `SettingsChoice.qml:284-300`, `TopDropdownStat.qml:180-196`); hold progress uses `Easing.Linear` (`ActionTile.qml:167`, `Main.qml:405`); record pulse `InOutSine` (`RecordButton.qml:116-124`). Durations: 140 (66), 220 (38), 180 (34), 240 (23), 120 (15). |
| I18 | wrong as stated, replace | Only `InlineDropdownField` accepts `{value,label,enabled}` (`InlineDropdownField.qml:41-63`). `SettingsChoice` and `TopDropdownStat` take string arrays and use `modelData` directly (`SettingsChoice.qml:188-198`, label via `optionDisplayFormatter`/`displayTextForValue`; `TopDropdownStat.qml:103`, `:113`). CameraPage builds `{value,label}` for its own crop picker (`CameraPage.qml:1104`). |
| I19 | holds (usually) | |
| N1 | holds (usually) | |
| N2 | holds (always) | |
| N3 | holds (once) | |
| N4 | holds (usually) | Extra exception: the top stats FPS/ISO/SHUTTER/WB are not gated in QML (`CameraPage.qml:2886-2912`); Core decides. `canSelectCaptureMode` gates mode change (`CameraPage.qml:539`). |
| N5 | weaken, restate | `tone: "danger"` does not always mean confirmation: hotspot "Stop" calls `wifiBridge.stopHotspot()` directly (`SettingsPage.qml:5759-5766`). Data-loss and power actions always confirm: Format, Restart, Shutdown, Delete preset, delete clip (`ClipPlayerPage.qml:1041` -> `deleteConfirmOpen` popup `:2060`), delete selected clips (`ClipBrowserPage.qml:478` -> confirm `:1019`). |
| N6 | holds (always) | Also mode-change failure: `CameraPage.qml:1496-1499` `showRecordWarning("Mode Change Failed", controlBridge.lastError, ...)`. |
| N7 | holds (always), extend | All 7 `repeat: true` timers run only under a condition or when started: `CameraPage.qml:1738` (`dateTimeOverlayEnabled && !standby`), `ExternalMonitorWindow.qml:346` (`!standby && ... "Free Run"`), `InlineDropdownField.qml:233` (`isOpen`), `StillExposureOverlay.qml:22` (`visible`), `Main.qml:368` (`running: false`). |
| N8 | holds (always) | |
| N9 | holds (always) | Same words and colours, computed twice (`StatusChip.qml:44-48`, `ExternalMonitorWindow.qml:155-162`). |
| N10 | weaken to usually | `recordExposureCompensationComponent` (`SettingsPage.qml:3068`) and `systemDisplayCalibrationComponent` (`:4637`) have no favourite toggle; Presets cards are neither reorderable nor favouritable (`:6895-6931`). `lutPreview` has a favourite toggle but is not in `favoriteCandidateOrder` (`:838-878`), so `normalizedSectionOrder` drops it from Favorites (`:1006-1012`). Rough edge; do not fix unasked. |
| N11 | holds (usually) | |

### Missed rules

| id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| S16 | structure | Treat settings item ids and section names as persisted keys (UI.conf order and favourites lists); never rename one; when an item moved section the old component id was kept. | always (persistence) / once (move precedent) | `SettingsPage.qml:974-996` stored orders by section name; `:999-1036` unknown ids dropped; `:2336-2353` `media` -> `systemMediaComponent` in Power, `battery` -> `powerBatteryComponent` in System; `:1134` "Power" uses `media.png` |
| S17 | structure | Key sensor-specific UI on `imxNNNDetected` flags derived by substring from `sensorName` (controlBridge first, deviceInfoBridge fallback), declared in each page separately. | always (2 pages, same 4 flags) | `CameraPage.qml:362-376`; `SettingsPage.qml:78-90` |
| S18 | structure | Treat `Main.qml` property names and `objectName`s as a C++ contract: C++ reads them by string. | always | `src/ExternalMonitorRuntimeBridge.cpp:137-153`; `src/ExternalMonitorManager.cpp:113-121`, `:231`; `src/main.cpp:502-503` `findChild("previewContainer"/"previewItem")`; `CameraPage.qml:1967`, `:1975` |
| S19 | structure | Register a bridge as a context property in `src/main.cpp` for the full UI, and also in the monitor-only process block if `ExternalMonitorWindow.qml` reads it; otherwise guard it with `typeof` in HDMI QML. Monitor-only process aliases `mediaBridge` to `monitorRuntimeBridge`. | always | `src/main.cpp:147-153` (monitor-only, `mediaBridge` = `&monitorRuntimeBridge` `:150`); `src/main.cpp:374-396` (full UI) |
| S20 | structure | Presets is a special section: hand-built Column, list from `settingsState.presetNames`, no order list, not reorderable. Do not model new sections on it. | once | `SettingsPage.qml:6745-6933` |
| I20 | idiom | Change a Core setting in this order: `if (bridge && !bridge.apply<X>(v)) { show lastError / return }`, then write the UI-side mirror in `settingsState`; when the bridge is absent, write the local fallback only. | usually (exception `ClipBrowserPage.qml:115-119`) | `SettingsPage.qml:2980-2994`; `CameraPage.qml:1495-1506`; `CameraPage.qml:2907-2912` |

---

## Final rules

Strength: always / usually / once. Kind: S structure, I idiom, N intent. All refs `@upstream-1.6.0`; paths repo-relative to `Apertar-UI`.

| id | kind | rule | strength | evidence | a violation looks like |
| --- | --- | --- | --- | --- | --- |
| S1 | S | Navigate only by setting `Main.currentPage` / `Main.settingsOpen` in Main, in response to a page's `*Requested` signal, a hardware action or standby; pages never switch themselves; no StackView. | always (grep `StackView`/`SwipeView`/`Drawer`: 0; no `currentPage` write outside Main) | `qml/Main.qml:16`; `:506-509`; `:314-322`; `:74-84`; `:194-199` | A page that sets `currentPage`, a `StackView`, a page pushing another page |
| S2 | S | Make non-camera pages `Loader`s active only while shown and free caches / stop playback in `onActiveChanged`; only Settings is retained, and only while on the camera page. | always (3 Loaders) | `qml/Main.qml:584-590`; `:613-621`; `:539`; `:80` | A new page instantiated permanently, or a Loader that keeps decoders/caches alive when hidden |
| S3 | S | Implement a settings item as one `Component { id: <section><Name>Component }` in `SettingsPage.qml`, returned by `<section>ComponentForId(itemId)` and built by the Loader in the section Column's Repeater over `normalizedSectionOrder`. | usually (Presets hand-built `SettingsPage.qml:6745-6933`; moved items keep old prefix `:2336-2353`) | `qml/SettingsPage.qml:2216-2229`; `:6684-6691`; `:6733-6739` | A card placed directly in a section Column, or a new QML file per settings card |
| S4 | S | When adding an item, add its id by hand to `default<Section>Order`, `sectionItemTitle`, `<section>ComponentForId` and, if it may be a favourite, `favoriteCandidateOrder`. No migration needed: unknown stored ids drop, new defaults append. | always (reorderable sections) | `qml/SettingsPage.qml:771-783`; `:1064-1076`; `:838-878`; `:999-1036` | A generated item registry or model replacing the hand lists; an item missing from one list |
| S5 | S | Wire a settings section through every if-chain keyed by its display-name string: `defaultOrderForSection`, `storedOrderForSection`, `applySectionOrder`, `sidebarIconForId`, `sourceSectionForItemId`, `favoriteComponentForId`, `updateSectionActivity`, `onSelectedSectionChanged`, the `sectionFlick.contentHeight` chain, plus `defaultSidebarOrder` and a copied section Column. | always | `qml/SettingsPage.qml:954-972`; `:1040-1062`; `:1161-1170`; `:6485-6501`; `:2139-2151` | A section missing from one chain (blank page, zero height, wrong icon) or a refactor of the chains into a table |
| S6 | S | Persist each reorderable section's item order as a `SettingsBridge` `QStringList` property in UI.conf, included in preset save/apply. | always (9 lists) | `src/SettingsBridge.hpp:81-89`; `src/SettingsBridge.cpp:399-407`; `:2097-2105` | Order stored in a separate file, in QML `Settings {}`, or left out of presets |
| S7 | S | Make monitoring aids and UI preferences `SettingsBridge` READ/WRITE/NOTIFY properties written from QML by plain assignment, persisted to UI.conf, with no socket command. | always | `qml/SettingsPage.qml:2704-2707`; `src/SettingsBridge.hpp:17`; `src/SettingsBridge.cpp:597-607` | A monitoring aid sent to Core over the socket or stored in Core's `camera_settings.conf` |
| S8 | S | Change Core-owned camera settings only through `ApertarControlBridge` invokables (`apply<X>(displayString)` for settings, verbs like `setRecording`/`capturePhoto` for actions); QML never builds commands or JSON; the bridge parses display strings. | usually (`qml/ClipBrowserPage.qml:115-119` writes `photoModeEnabled` without Core) | `qml/SettingsPage.qml:3209-3211`; `qml/CameraPage.qml:2938-2943`; `src/ApertarControlBridge.cpp:291-311` | QML composing a command string or JSON, or a new bridge talking to the Core socket |
| S10 | S | Edit per-sensor resolution/crop tables in both `CameraPage.qml` and `SettingsPage.qml` together; tables are identical copies, surrounding properties are renamed (`resolution` vs `recordResolution`). | always | `qml/CameraPage.qml:377-381`; `qml/SettingsPage.qml:110-114`; `qml/CameraPage.qml:448` vs `qml/SettingsPage.qml:181` | Table changed in one page only; a shared JS module introduced unasked |
| S11 | S | Have `ExternalMonitorWindow` derive HUD values from the bridges itself; only state that lives in Main or the camera page (recording, timelapse, timecode, shutdown popup, currentPage) reaches it via named Main properties read by `ExternalMonitorRuntimeBridge`. | always | `qml/ExternalMonitorWindow.qml:44-169`; `qml/Main.qml:36-38`; `qml/ExternalMonitorWindow.qml:9-31`; `src/ExternalMonitorRuntimeBridge.cpp:137-153` | HDMI QML reaching into `cameraPage` or the settings page directly |
| S12 | S | Put an element that both touch UI and HDMI show into a small standalone qml file used by both; otherwise the HDMI window draws its own HUD. | usually (status pill and audio meter duplicated: `qml/ExternalMonitorWindow.qml:155-162`, `:945`) | `qml/CameraPage.qml:2569-2577`; `qml/ExternalMonitorWindow.qml:1103-1107`; shared: `DroppedFrameWarning`, `FalseColorLegend`, `HorizontalLevelOverlay`, `StillExposureOverlay` | A shared HUD framework or a component library that both windows must adopt |
| S13 | S | Pass the main bridges into pages as properties (`settingsState`, `bridge`, `controlBridge`); use others as bare context globals, `typeof`-guarded only when the bridge can be absent (monitor-only process, gyro, audio). | usually (SettingsPage uses bare `apertarControlBridge`; `wifiBridge` 81 uses / 0 guards) | `qml/Main.qml:498-501`; `qml/SettingsPage.qml:3198`; `qml/ExternalMonitorWindow.qml:38-40` | A bridge used unguarded in HDMI QML that the monitor-only process does not register |
| S14 | S | Let settings-card components compute layout flags from `displayConfigBridge.uiLayout`; camera-page components get flags/tokens from the page; pages compute from `displayLayout`. | usually (`qml/StatusChip.qml:13-14`, `qml/SettingsMenuItem.qml:10-11`, `qml/TimelapseIntervalPicker.qml:14-15` take flags) | `qml/TogglePill.qml:7-17`; `qml/MonitoringRow.qml:14-22`; `qml/SettingsPage.qml:18-27` | A global scale factor or theme object replacing the flags |
| S15 | S | Register every new qml file in both `CMakeLists.txt` `APERTAR_QML_FILES` (AOT) and `qml.qrc` (non-AOT), and fonts/icons in `resources.qrc`. | usually (`DroppedFrameWarning.qml` missing from `qml.qrc`) | `CMakeLists.txt:19-52`; `:137-151`; `qml.qrc` | New file in one list only; a new resource mechanism |
| S16 | S | Treat settings item ids and section names as persisted keys; never rename them; a moved item keeps its old component id. | always (persistence) / once (move) | `qml/SettingsPage.qml:974-996`; `:999-1036`; `:2336-2353` | Renaming `battery` or `"Power"` to tidy up, silently resetting users' order and favourites |
| S17 | S | Key sensor-specific UI on `imxNNNDetected` substring flags from `sensorName` (controlBridge first, deviceInfoBridge fallback), declared in each page. | always | `qml/CameraPage.qml:362-376`; `qml/SettingsPage.qml:78-90` | Sensor branching by a new enum/capability system, or a flag added to one page only |
| S18 | S | Treat `Main.qml` property names and `objectName`s as a C++ contract read by string. | always | `src/ExternalMonitorRuntimeBridge.cpp:137-153`; `src/main.cpp:502-503`; `qml/CameraPage.qml:1967`, `:1975` | Renaming `monitorTimecode`, `currentPage` or `previewItem` and breaking HDMI/preview silently |
| S19 | S | Register a bridge in `src/main.cpp` for the full UI and, if HDMI QML reads it, also in the monitor-only block (or `typeof`-guard it there). | always | `src/main.cpp:147-153`; `src/main.cpp:374-396` | HDMI-only process crashing or showing blanks because a bridge is undefined |
| S20 | S | Presets is a hand-built special section (list from `presetNames`, no order list, not reorderable); do not model new sections on it. | once | `qml/SettingsPage.qml:6745-6933` | A new section copied from the Presets Column |
| I1 | I | Derive sizes inline as nested ternaries over layout flags, largest layout first and square last; no theme singleton or scale factor. | usually (32 fixed `pixelSize` in SettingsPage e.g. `:6776`; ClipPlayerPage and HDMI fixed) | `qml/TogglePill.qml:20-21`; `qml/SystemSectionCard.qml:26-27`; `qml/SettingsPage.qml:28-59` | A `Theme.qml` singleton, `dp()` helper or scale multiplier |
| I2 | I | Declare page-wide size tokens as `readonly property int <area><Thing>` at the top of the page and pass them into components. | usually (ClipPlayerPage uses literals) | `qml/SettingsPage.qml:28-59`; `qml/CameraPage.qml:2886-2898` | Tokens in a separate file, or component sizes hard-coded inside the page body |
| I3 | I | Copy the layout-flag block of the file you edit: `standardLandscapeLayout` means `landscape` only in SettingsPage but `landscape` or `landscape_large` in CameraPage/Main; SettingsPage `compactLandscapeLayout` is any landscape. | always | `qml/SettingsPage.qml:23-26`; `qml/CameraPage.qml:46-47`; `qml/Main.qml:43-44` | Flag semantics "unified" across files, shifting every size |
| I4 | I | Write fills/borders as inline hex literals from the existing palette (card `#181818`/`#171717`, border `#1affffff`, secondary text `#66ffffff`, accent `#3fd0ff`, danger `#8d2020`/`#ba4a4a`, scrim `#cc000000`) and primary text as `"white"`. | usually (`Qt.rgba`/`fadedColor` in 7 files, `qml/StatusChip.qml:26-27`) | `qml/ActionTile.qml:30-39`; `qml/StatusChip.qml:44-45`; `qml/MonitoringRow.qml:109-112` | A colour constants file, Material/Universal styles, new off-palette colours |
| I5 | I | Load Inter Regular/Medium/Bold with a `FontLoader` in each file that uses it (ids `interRegular/interMedium/interBold`): Bold titles, Medium labels, Regular body. | usually (`MonitoringRow`, `SettingsChoice`, `SettingsMenuItem` rely on parent ids) | `qml/SystemSectionCard.qml:30-32`; `qml/ActionTile.qml:42`; `qml/Main.qml:469-472` | A new font or a font singleton |
| I6 | I | Set `renderType: Text.NativeRendering` on every `Text`. | usually (389/403) | `qml/SystemSectionCard.qml:166`; `qml/AdjustNumberTile.qml:36` | New Text blocks without it |
| I8 | I | Give the file root `id: root`; name other ids camelCase with a role suffix (Area, Component, Column, Overlay, Timer, Anim, Card, Flick). | always (root, 32/32) / usually (suffix) | `qml/SettingsPage.qml:2686`; `qml/CameraPage.qml:3666-3773` | Root ids like `cameraPage`, snake_case ids |
| I9 | I | Name component signals `<thing>Requested` or as events (`valueSelected(string value)`, `optionSelected`, `clicked`); the component emits and the owner writes state. | always | `qml/MonitoringRow.qml:93-102`; `qml/TopDropdownStat.qml:22-23`; `qml/TogglePill.qml:18`, `:61-63` | A component writing a bridge or `settingsState` itself |
| I10 | I | Start action functions with a verb (`apply<X>`, `open<X>Confirmation`, `execute<X>`, `update<X>`, `sync<X>FromBridge`); name getters as noun phrases (`sectionItemTitle`, `<section>ComponentForId`), predicates `is/has/can`, converters `<a>To<b>`. | usually | `qml/SettingsPage.qml:1282`; `:1695`; `:1064`; `qml/CameraPage.qml:1555`; `:956` | `get<X>()`/`handle<X>()` naming, class-like helper objects |
| I11 | I | React to bridges with `Connections { target: ...; function on<Signal>(args) {} }`; where a page keeps a local mirror, re-check bridge and empty strings before copying. | always (syntax, 23 blocks) / usually (mirror) | `qml/CameraPage.qml:1824-1847`; `:1555-1581`; `qml/InlineDropdownField.qml:303` | Old `onFoo:` handlers in Connections, `Qt.binding` hacks |
| I12 | I | Null-guard bridge reads that can be absent with a literal default: `root.settingsState ? root.settingsState.x : default`. | usually (always-present globals read bare: `qml/SettingsPage.qml:239-242`, `qml/Main.qml:205-206`) | `qml/SettingsPage.qml:2697`; `qml/CameraPage.qml:1981-1982`; `qml/ExternalMonitorWindow.qml:374-375` | Unguarded `root.settingsState.x` or `controlBridge.x` |
| I14 | I | Do not log from QML. | always (grep `console.`/`print(` over 32 qml + 1 js: 0) | `qml/*.qml` | `console.log` debugging left in |
| I15 | I | Mark CameraPage chapters with `// =====` banners and add only short one-line why-comments; SettingsPage carries none; no TODO/FIXME markers. | usually | `qml/CameraPage.qml:1961-1963`; `:2580`; `:1356`; grep `TODO|FIXME` in `qml/`: 0 | Doc-comment blocks, ticket/tutorial numbers (T33, WP-...) in comments, TODO lists |
| I16 | I | Match surrounding formatting in big files (column-0 functions, tab lines, odd indentation); do not reformat untouched code. | always | `qml/CameraPage.qml:8`; `:1555`; `qml/Main.qml:487-494`; `qml/SettingsPage.qml:5764-5765` | Whole-file reindent or reformat in a feature commit |
| I17 | I | Animate with `Behavior on <prop>` + `NumberAnimation`/`ColorAnimation`, 120-240 ms: `OutCubic` for enter/state change, `InCubic` for popup close, `Linear` for hold progress; press feedback scale 0.95-0.985 + colour change. | usually (`RecordButton.qml:116-124` InOutSine pulse; page overlay 360-520 ms) | `qml/TogglePill.qml:30-56`; `qml/InlineDropdownField.qml:280-296`; `qml/ActionTile.qml:167` | Springy/bouncy easing, long animations, no press feedback |
| I18 | I | Write option lists as plain string arrays; use `{value,label,enabled}` objects only with `InlineDropdownField` (or a page's own picker); `SettingsChoice` labels go through `optionDisplayFormatter`. | usually | `qml/InlineDropdownField.qml:41-63`; `qml/SettingsChoice.qml:188-198`; `qml/TopDropdownStat.qml:103`, `:113`; `qml/CameraPage.qml:1104` | Object options passed to `SettingsChoice`/`TopDropdownStat` (shows `[object Object]`) |
| I19 | I | Store UI-only setting values as their display strings; add converters only where a renderer needs a number. | usually (standby timeout stores seconds, `qml/SettingsPage.qml:4570`) | `qml/SettingsPage.qml:4538`; `qml/ExternalMonitorWindow.qml:49`; `qml/SettingsPage.qml:1282-1347` | Enum ints in UI.conf for a value the operator reads as text |
| I20 | I | Change a Core setting by calling `apply<X>(v)` first, aborting (with `lastError` shown) on false, then mirroring into `settingsState`; when the bridge is absent write only the local fallback. | usually (`qml/ClipBrowserPage.qml:115-119`) | `qml/SettingsPage.qml:2980-2994`; `qml/CameraPage.qml:1495-1506`; `:2907-2912` | UI state flipped before Core accepted, leaving UI and Core out of sync |
| N1 | N | Show only choices the hardware and Core support, dropping unsupported values from the option list based on a bridge capability property. | usually | `qml/SettingsPage.qml:3198-3206`; `qml/CameraPage.qml:484-490`; `README.md:152` | Offering every value and failing in Core |
| N2 | N | Keep a currently unusable item visible but dimmed (`available:false`), block its input, and explain why in the description. | always | `qml/MonitoringRow.qml:110`; `:478-482`; `qml/SettingsPage.qml:3040-3043` | Hiding the card, or leaving it clickable with no effect |
| N3 | N | Grey a single disallowed value inside its list with a per-option `enabled` flag and re-check in the handler. | once | `qml/SettingsPage.qml:3226-3228`; `:3237-3238` | Handler applying a value the list marked disabled |
| N4 | N | Disable recording-format, resolution, audio-device, capture-mode and power-state controls while recording or timelapse is active; top exposure stats stay live. | usually (hardware `clip_browser` action `qml/Main.qml:320-323`, settings button `qml/CameraPage.qml:3030-3036`) | `qml/SettingsPage.qml:3230`; `:3945`; `:5418`; `qml/CameraPage.qml:539`, `:3697` | A format/resolution/storage control usable during a take |
| N5 | N | Make data-loss and power actions two-step: a `tone: "danger"` control that opens a confirmation popup; Format Media also needs hold-to-activate. Danger tone alone (hotspot Stop) does not imply confirmation. | always (data-loss/power) | `qml/SettingsPage.qml:5177-5184`; `:5428-5438`; `qml/ClipPlayerPage.qml:1041`, `:2060`; `qml/ClipBrowserPage.qml:478`, `:1019` | One-tap delete, format, restart or shutdown |
| N6 | N | Surface capture and mode-change failures loudly through the camera page's modal warning (`showRecordWarning` title, subtitle, detail title, detail body); settings failures get their own `*ErrorOpen` popup. | always | `qml/CameraPage.qml:1656-1662`; `:1827-1836`; `:1496-1499`; `qml/SettingsPage.qml:9315` | A toast, status text or silent failure for a failed take |
| N7 | N | Let hidden UI do no background work: section polling only while that section is visible and the page open, Repeaters get `[]` otherwise, every repeating Timer has a `running:` condition (feature on, not standby), work released on close. | always (7/7 repeating timers) | `qml/SettingsPage.qml:2139-2151`; `:6684-6686`; `qml/Main.qml:93`; `qml/CameraPage.qml:1736-1742`; `qml/ExternalMonitorWindow.qml:344-349` | A free-running timer or poller, polling during standby |
| N8 | N | Show monitoring aids on HDMI only in Assist Feed (each aid ANDed with `overlayFeedEnabled`), hide the info HUD under SMPTE, never bake aids into the recording. | always | `qml/ExternalMonitorWindow.qml:48-53`; `:374-387`; `:785` | An aid drawn on HDMI in Clean Feed, or burnt into the file |
| N9 | N | Use the fixed colour-coded status words NO MEDIA (amber), TIMELAPSE/REC (red), WRITING (amber), READY (green) on touch UI and HDMI. | always | `qml/StatusChip.qml:44-48`; `qml/ExternalMonitorWindow.qml:155-162` | New status words or colours on one screen only |
| N10 | N | Make settings layout customisation (long-press reorder, favourites) a persisted, preset-able setting on the cards of reorderable sections. | usually (no favourite on `:3068` exposureCompensation, `:4637` displayCalibration; Presets cards fixed) | `qml/SettingsPage.qml:6677`; `qml/MonitoringRow.qml:101-102`; `src/SettingsBridge.cpp:2097-2105` | A new card without `pressAndHoldRequested`/`favoriteToggleRequested` wiring in a reorderable section |
| N11 | N | Card titles Title Case 1-3 words; descriptions one short sentence-case fragment without final period; HUD labels uppercase via `font.capitalization`; progress labels end in three ASCII dots; units glued to values. | usually | `qml/SettingsPage.qml:4526-4528`; `qml/AdjustNumberTile.qml:234-235`; `qml/SettingsPage.qml:5571` | Long sentence titles, hard-coded uppercase strings, Unicode ellipsis |
