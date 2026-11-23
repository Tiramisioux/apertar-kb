# Inventory: UI-settings-qml (stage 1, no judging)

Refs: port = Apertar-UI `cinemate-port` `7ea9afc`; upstream = `upstream-1.6.0` `43888e5`.
Sources read completely: `/home/user/build/review/diffs/UI-SettingsPage.part01.diff` (921 lines), `qml/ClipNameCard.qml` (601), `qml/ClipNamePill.qml` (115), `qml/ControlsWarning.qml` (30). Bridge side checked for the commands: `src/ApertarControlBridge.cpp:618-775`, `src/SettingsBridge.cpp:368-371,1150-1215,2170-2173`.

## 1. Port commits touching the unit (fork-log status)

| Commit | Subject | Touches | Recorded status / test |
| --- | --- | --- | --- |
| `5697b54` | faint red outline on audio meter + switch | SettingsPage (+21), AudioMeterOverlay, CameraPage, ExternalMonitorWindow, SettingsBridge | no test line in message; fork-log: part of drop-frames line |
| `606f137` | Clip names card | new ClipNameCard, ClipNamePill; SettingsPage (+71), CMakeLists, qml.qrc, ApertarControlBridge | fork-log:240 "untested by hand"; message has no Tested line |
| `841d0ed` | drop-frames (7 squashed): buffer bar, Frames/RAM, Log, storage pre-roll | SettingsPage (+175), CameraPage, ExternalMonitorWindow, StatusChip, bridges | "not compiled or run here; compiles on the Pi; not yet seen on screen" |
| `ea44bd7` | T45 Controls chip + read-only Controls card | new ControlsWarning; SettingsPage (+34), CameraPage, CMakeLists, bridge | "pi build, qmllint of the chip; not seen on a touch screen" |
| `08cefcf` | timecode modes named Time of Day / Clip | SettingsPage (+12/-3) | "desk only" |
| `7029db1` | UI timecode vs File timecode | SettingsPage (+18/-2), CameraPage, bridge | "Pi build pending"; fork-log:204 "building 2026-10-29, not tested" |
| `c716dec` | compression greyed while Mode Ladder active | SettingsPage (3 lines), bridge | "desk only"; fork-log:215 built 2026-10-28 |
| `da2a9b5` | recording frame + red timecode switches | SettingsPage (+44), CameraPage, ExternalMonitorWindow, SettingsBridge | "desk only"; fork-log:219 "tested 2026-10-28 (Patrik)" |

Hunks of the diff not attributable to one commit alone: the clip-text popup reuse (606f137), the `defaultInfoOrder`/favourite candidate lists (ea44bd7).

## 2. Operator-visible features

| Feature | Where | Commits |
| --- | --- | --- |
| Monitoring switches: Recording Frame, Red Timecode, Audio Recording Outline, Frame Buffer Bar | Settings > Monitoring, 4 new rows | da2a9b5, 5697b54, 841d0ed |
| Timecode split: "UI timecode" and "File timecode" dropdowns; stored values "Free Run"/"Rec Run" shown as "Time of Day"/"Clip"; card description reworded; field label "Mode" -> "UI timecode" | Settings > Record > Timecode | 7029db1, 08cefcf |
| Write Buffer: Frames / RAM tiles + status text | Settings > Record > Format card, visible for CDNG or MLV when Core reports `bufferSetting` | 841d0ed |
| Log On/Off tile + status text (incl. "Not applied" message for SDR) | same card, visible for CDNG when `cdngLogAvailable` | 841d0ed |
| Compression field disabled with label "Compression (set by Mode Ladder)" | same card | c716dec |
| Clip Names card: 3 presets, pill row (tap select, long-press drag, remove, move left/right), palette (Time, Camera, Format, Text, Separators), free-text pill via the keyboard popup, live "Next clip:" preview, auto-save after 1 s, locked while recording | Settings > Record > Clip Names (new item id `clipNames`, hidden until Core reports a template) | 606f137 |
| Storage Pre-roll tile, "Automatic pre-roll" On/Off, explanatory texts, last result line | Settings > Media > Media Speed card | 841d0ed |
| Controls card (read-only: error / warning count, WebUI address) | Settings > Info, new item id `controls`, favouritable | ea44bd7 |
| Controls chip "Controls: N errors" on camera page | `ControlsWarning.qml` (placed by CameraPage, outside this unit) | ea44bd7 |
| Clip-text keyboard: the preset-name popup reused with another title/hint/placeholder, filtered to `[A-Za-z0-9._-]`, max 24 | Settings popup | 606f137 |

## 3. Interfaces added or changed (as seen from this unit)

### Socket commands sent (by the bridge, triggered from these QML items)

| Command | Args | Sender (bridge) | QML trigger |
| --- | --- | --- | --- |
| `set_buffer_mode` | `value` frames/ram | `applyBufferMode` `ApertarControlBridge.cpp:686` | Write Buffer tiles |
| `set_cdng_log` | `value` auto/off | `applyCdngLog` `:716` | Log tile |
| `storage_preroll` | none | `applyStoragePreroll` `:618` | Storage Pre-roll tile |
| `set_storage_preroll` | `value` on/off | `applyStoragePrerollAuto` `:624` | Automatic pre-roll tiles |
| `set_clip_name_template` | `value` | `applyClipNameTemplate` `:632` | ClipNameCard.saveNow |
| `preview_clip_name` | `value` | `requestClipNamePreview` `:644` | ClipNameCard previewTimer |
| `set_timecode_mode` (changed: new arg `target` ui/files/both) | `value`, `target` | `applyTimecodeMode(value, target)` `:750` | UI timecode / File timecode dropdowns |

### Bridge properties and methods read or called from this unit (all new, on `apertarControlBridge` unless stated)

`ladderActive`, `bufferSetting`, `bufferMode`, `bufferNote`, `cdngLogAvailable`, `cdngLogOn`, `cdngLogApplied`, `cdngLogBits`, `storagePrerollActive`, `storagePrerollAuto`, `storagePrerollAutoKnown`, `storagePrerollLast`, `clipNameKnown`, `clipNameTemplate`, `clipNameExample`, `clipNamePreview`, `fileTimecodeMode`, `controlsErrors`, `controlsWarnings`; signals `clipNameChanged`, `recordingChanged`. On `settingsBridge` (`settingsState`): `recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`, `frameBufferBarEnabled`.

### State fields consumed from Core (via the bridge)

`ladder_active`, `buffer_setting`, `cdng_log_available`, `cdng_log_bits`, `storage_preroll_active`, `storage_preroll_auto`, `storage_preroll_fps`, `storage_preroll_last`, `clip_name_template`, `clip_name_example`, `controls_errors`, `controls_warnings`, `file_timecode_mode` (name from fork-log; not read here). Event: `"controls"` (ea44bd7 message).

### Config keys (UI.conf, QSettings via SettingsBridge)

| Key | Default | Also in preset export/import |
| --- | --- | --- |
| `recordingFrameEnabled` | false | yes (`SettingsBridge.cpp:2170`, `:2262`) |
| `frameBufferBarEnabled` | false | yes |
| `recordingRedTimecodeEnabled` | true | yes |
| `audioRecordedOutlineEnabled` | true | yes |
| `timecodeMode` (existing key) | "Free Run" | now written only when target != files (`ApertarControlBridge.cpp:758-762`) |

Env vars: none. Files on disk: none from this unit (clip name template lives in Core; hardware file `~/apertar-hardware.conf` is only named in ControlsWarning's comment).
HTTP routes: none in this unit; the Controls card text points to WebUI "Settings, Controls" on port 8000 (`http://<ip>:8000`).

### UI elements

| Element | File:line (@cinemate-port diff) | Kind |
| --- | --- | --- |
| `monitoringRecordingFrameComponent`, `...FrameBufferBarComponent`, `...RecordingRedTimecodeComponent`, `...AudioRecordedOutlineComponent` | diff 407-477 | Component, `MonitoringRow` |
| `recordClipNamesComponent` (SystemSectionCard wrapping ClipNameCard) | diff 665-687 | Component |
| `infoControlsComponent` (SystemSectionCard + one InfoDataRow) | diff 798-822 | Component |
| Write Buffer Column (2 ActionTile + Text) | diff 520-564 | inline in Format card |
| Log Column (ActionTile + Text) | diff 566-598 | inline in Format card |
| Storage Pre-roll tile, Automatic pre-roll Column, 2 explanatory Text, last-result Text | diff 706-776 | inline in Media Speed card |
| File timecode InlineDropdownField | diff 648-661 | inline in Timecode card |
| `ClipNameCard.qml`, `ClipNamePill.qml`, `ControlsWarning.qml` | new files | components |
| Properties/functions on root: `signal clipTextEntered`, `timecodeChoices`, `timecodeDisplayName()`, `presetPopupPurpose`, `openClipTextPopup()`, `recordItemVisible()` | diff 15,24-26,48,234,259-273 | page-level additions |

## 4. How the port registers its items vs upstream (ui-map section 1.1)

Upstream pattern: item id in `default<Section>Order` -> title in `sectionItemTitle` -> `<section>ComponentForId` -> one `Component { id: xComponent; SystemSectionCard / MonitoringRow {...} }`, Loader in the section Repeater (ui-map.md:17-60; `upstream SettingsPage.qml:2318` recordComponentForId, `:3754` recordTimecodeComponent).

| Aspect | Port | Matches upstream pattern? |
| --- | --- | --- |
| 4 Monitoring rows | ids added to `defaultMonitoringOrder`, titles, `monitoringComponentForId`, one `MonitoringRow` Component each, bound to `settingsState` | yes, same registration chain (confirmed) |
| `clipNames` | added to `defaultRecordOrder`, title, `recordComponentForId`, Component; NOT added to favourite candidates (no `favoriteEnabled`) | chain yes; extra new hook `recordItemVisible()` on the Record Loader (`visible:`), no upstream equivalent (upstream Loaders have no per-item visible hook; confirmed by diff context only) |
| `controls` | added to `defaultInfoOrder`, `favoriteCandidateOrder`, title, `infoComponentForId`, Component with favourite support | yes |
| Write Buffer / Log / Compression / Pre-roll / File timecode | inline in existing cards (no new section/Component) | yes; extend existing cards with `ActionTile`, `InlineDropdownField` (both exist upstream, `qml/ActionTile.qml`, `qml/InlineDropdownField.qml`) |
| Clip text input | reuses the preset-name popup (`presetNameDraft`, preset keyboard) via a purpose flag | new mechanism: a mode flag switching titles, filter and length in 5 places; upstream has one popup per purpose (preset popup, hotspot edit popup, wifi password popup) |
| Timecode display names | `timecodeChoices` array of `{value,label}` + `timecodeDisplayName()` | `InlineDropdownField` options as value/label objects already used upstream (`SettingsPage.qml:3252`) |

Reused components: `SystemSectionCard`, `MonitoringRow`, `InlineDropdownField` (`displayValue`, object options), `ActionTile` (`tone`, `actionEnabled`), `InfoDataRow`, `sharedDropdownController`, `dropdownOverlay`. Not reused: ClipNameCard builds its own Flow/Repeater/Drag layer, its own pills, fixed hex colours (`#123d59`, `#3fd0ff`, `#e0b447`, `#6cc070`) and `font.pixelSize` literals without the page's `largeLandscape/standardLandscape/compact` size tokens (it reads `displayConfigBridge.uiLayout` itself, `ClipNameCard.qml:16-21`). The inline Pre-roll "Automatic" description uses the page text style (Inter, layout-dependent size); the Write Buffer/Log helper texts use fixed sizes 12 and `#9aa5b1`.

## 5. Original code modified

| Region (upstream `SettingsPage.qml`) | Change | Kind |
| --- | --- | --- |
| `signal backRequested` area, line 9 | added `signal clipTextEntered(string)` | extended in place |
| root properties ~16-21 | added `timecodeChoices` | extended in place |
| `presetNamePopupOpen` flags ~739 | added `presetPopupPurpose` | extended in place |
| `defaultMonitoringOrder` ~771, `defaultRecordOrder` ~784, `defaultInfoOrder` ~821, `favoriteCandidateOrder` ~838 | ids appended | extended in place |
| `onSelectedSectionChanged` ~894 | condition `selectedSection !== "Presets"` now depends on purpose (`"Record"` for clipText) | behaviour-changed (small) |
| `sectionItemTitle` ~1064 | 6 titles added; the 4 Monitoring titles inserted before `anamorphicDesqueeze` | extended in place |
| new `timecodeDisplayName()` between favourite helpers | added | new function |
| preset popup open/close/save ~1976-2010 | `closePresetNamePopup()` resets purpose; `savePresetFromDraft()` branches on purpose and emits `clipTextEntered` | behaviour-changed |
| `presetKeyboardInsert` ~2096 | clipText: reject chars outside `[A-Za-z0-9._-]` and length >= 24 | behaviour-changed |
| `monitoringComponentForId`, `recordComponentForId`, `infoComponentForId` | 4 + 1 + 1 branches | extended in place |
| Format card (Compression field, ~3261) | label and `fieldEnabled` read `ladderActive` | behaviour-changed |
| Format card | two Columns inserted after Compression | extended in place |
| `recordTimecodeComponent` ~3754 | description reworded, "Mode" -> "UI timecode", `options` now objects, call `applyTimecodeMode(v, "ui")`, second dropdown | rewritten (partly) |
| Media Speed card ~5340 | 4 elements appended after the speed-test button | extended in place |
| Record column Repeater Loader ~7037 | `visible: root.recordItemVisible(modelData)` | extended in place |
| preset popup texts ~8144-8180 | 4 strings become purpose conditionals | behaviour-changed |

## 6. New abstractions

| Name | Files | Purpose | Upstream equivalent |
| --- | --- | --- | --- |
| `ClipNameCard` | `qml/ClipNameCard.qml` (601 lines) | pattern editor: parses template string `{format}_{date}_{clip}` into a ListModel, edits as pills, serialises, auto-saves (350 ms preview timer, 1000 ms save timer), own drag layer (`Drag.Internal` + `DropArea`), sync with Core via `Connections` | none; upstream has no free-form composer. Upstream drag is reorder only (`SettingsPage.qml:6165` `Drag.active`, `:6282`) |
| `ClipNamePill` | `qml/ClipNamePill.qml` (115) | chip with tap / long-press drag / remove | none; closest is the reorder delegate (`SettingsPage.qml:6111`) |
| `ControlsWarning` | `qml/ControlsWarning.qml` (30) | chip "Controls: N errors" | `StatusChip.qml` exists upstream for camera-page chips (not read for equivalence here: unconfirmed) |
| `presetPopupPurpose` mode flag | SettingsPage | one popup, two jobs | separate popup per job upstream |
| `recordItemVisible()` | SettingsPage | hide an item until Core data exists | none seen |
| Template mini-language `{text:...}`, tokens date, date_, yy, mm, dd, time, time-, tc, tc-, cam, sensor, model, format, clip, res, fps, bits, comp, log | ClipNameCard palette | duplicated knowledge of Core's token list in QML (`paletteGroups`, `isKnownToken`) | none |
| `timecodeChoices` value/label mapping | SettingsPage | rename shown modes, keep stored values | n/a |

New build registrations: `CMakeLists.txt:41,51,52`, `qml.qrc:32,33` (ClipNameCard, ClipNamePill; ControlsWarning in CMakeLists only per diff stat of ea44bd7; qrc entry for ControlsWarning not verified here: unconfirmed, `grep ControlsWarning qml.qrc` returned none).

## 7. Removed, narrowed or hidden vs upstream

| What | Effect |
| --- | --- |
| Timecode dropdown label "Mode" with options "Free Run"/"Rec Run" | replaced by "UI timecode" + "File timecode" with labels "Time of Day"/"Clip"; the names "Free Run"/"Rec Run" no longer shown anywhere in Settings |
| Timecode card description "Timecode behavior" | replaced |
| Preset popup title/hint/placeholder | now conditional (preset text unchanged when purpose is "preset") |
| Compression dropdown | disabled whenever Mode Ladder is active (new restriction) |
| Clip text characters | restricted to `[A-Za-z0-9._-]`, 24 max; spaces rejected |
| `clipNames` item | hidden until Core sends a template (older Core: card never appears) |
| Nothing deleted from upstream otherwise (diff has 5 removed-line groups, all replacements above) | |

## 8. Board assumptions

None in this unit. No GPIO, I2C, RP1, PCIe, RAM size or fan references in the diff or the three new files. Indirect: "Frames" tile text "Original queue: 12 frames" is a hard-coded Core constant (`diff:556`); Pre-roll text "Records 2 seconds at the top frame rate of the current mode" hard-codes Core behaviour (`diff:759`). Controls card names `~/apertar-hardware.conf` (via chip comment) and "Edit them in the WebUI: Settings, Controls" (`diff:805`).

## 9. Observations for stage 2 (not judgements)

- Internal tags in code: `// T45:` in `infoControlsComponent` comment (`diff:798`) and in `ControlsWarning.qml:3`. Meaningless to upstream developer (BRIEF vocabulary).
- Null-safety is inconsistent: Storage Pre-roll block and Write Buffer/Log blocks use `apertarControlBridge.x` bare inside `ActionTile` (diff 540-583, 709-742, 769) while the `visible:` lines guard `!!apertarControlBridge`; Info Controls card and Compression label guard it; timecode card uses `typeof apertarControlBridge !== "undefined"`.
- Two spellings of the Frames/RAM state: `bufferSetting` (requested) vs `bufferMode` (in use) in one text expression (`diff:556-559`).
- `applyBufferMode` and `applyCdngLog` update bridge state optimistically; `applyStoragePrerollAuto` explicitly does not (`:626`).
- Hardcoded colours `#9aa5b1`, `#8cffffff` mixed in the same card (`diff:594` vs `:749`).
- Test status: no commit of the unit records a test on a touch screen; ClipNameCard "untested by hand" (fork-log:240).
