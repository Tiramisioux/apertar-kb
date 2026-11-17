# Review: UI-settings-qml (stage 2)

Refs: port = Apertar-UI `cinemate-port` `7ea9afc`; upstream = `/home/user/wt/ui-upstream` `upstream-1.6.0` `43888e5`.
Read completely: `build/review/diffs/UI-SettingsPage.part01.diff`, `qml/ClipNameCard.qml`, `qml/ClipNamePill.qml`, `qml/ControlsWarning.qml`, inventory `raw/inv-UI-settings-qml.md`.
Yardstick: no `apertar-conventions.md` and no UI `conv-*.md` exist yet. Every comparison below is against upstream code read here.
Diff line numbers ("diff:N") are lines of the part01 diff file.

## Summary

The port registers its new items the upstream way (order array -> title -> `*ComponentForId` -> one Component; `MonitoringRow`, `SystemSectionCard`, `InlineDropdownField`, `ActionTile`, `InfoDataRow` reused). `ControlsWarning.qml` is a clone of upstream `DroppedFrameWarning.qml`. The deviations are in widget choice and in two new mechanisms:

- Choices are drawn as `ActionTile`s whose `tone` flips to `accent` for the selected one. Upstream never does this: on/off is a `TogglePill` row, a choice of values is an `InlineDropdownField`, an `ActionTile` is a verb with a fixed tone.
- The Timecode card changes what the upstream "Mode" control does (it no longer sets the files' timecode) and renames Free Run / Rec Run.
- `ClipNameCard` is a 601 + 115 line drag-and-drop composer, untested on a touch screen, with its own drag layer and colours.
- `recordItemVisible()` hides a card; upstream keeps cards and says "unavailable" in the description.
- UI text restates Core constants that Core lets the operator change (pre-roll seconds, WebUI port).

## Upstream patterns used as the yardstick

| Pattern | Upstream evidence (@upstream-1.6.0) |
| --- | --- |
| Boolean in a card = title, description, `TogglePill` | `qml/SettingsPage.qml:3562` `TogglePill { id: gyroRecordToggle; checked: ...recordGyroEnabled }`; `:4885` `dateTimeOverlayToggle` |
| Choice of values = `InlineDropdownField` with value/label options | `qml/SettingsPage.qml:3250-3262` Compression: `options: [{ value: "none", label: "Uncompressed" }]...` |
| `ActionTile` = a verb, `tone` constant | `qml/SettingsPage.qml:3640,3650` `tone: "default"` (Set Level / Clear Level); `:5416` `tone: "accent"` (Standby). No conditional `tone:` anywhere in `qml/*.qml` (grep `tone: .*?` returns nothing) |
| Helper text in the Format card | `qml/SettingsPage.qml:3309-3318` `color: "#9aa5b1"; font.pixelSize: 12` |
| Card sub-label | `qml/SettingsPage.qml:5221-5228` "Write Test": `#66ffffff`, Inter Medium, uppercase, letterSpacing 2.0, layout-dependent size |
| One card per feature, every card has an icon and favourite support | 39 of 42 Components have `titleIconSource` and `favoriteEnabled` (awk over `qml/SettingsPage.qml`; exceptions: anamorphic no icon, exposureCompensation none, displayCalibration no favourite) |
| Unavailable feature: card stays, description says why | `qml/SettingsPage.qml:3039` sound recorder `description: hasAudioInput ? ...`; `:3071` exposure compensation `!apertarControlBridge || !...exposureCompensationAvailable` |
| One keyboard popup, two jobs, via a target flag | `qml/SettingsPage.qml:732` `hotspotEditTarget`; `:1862` `return root.hotspotEditTarget === "password" ? "Hotspot Password" : "Hotspot Name"` (helper functions) |
| One timecode mode for files and UI | `src/ApertarControlBridge.cpp:622-635` `applyTimecodeMode(displayValue)`; Core `src/ApertarCoreApp.cpp:9424-9435` sets the camera and `updateSharedUiGeneralSettings({"timecodeMode", ...})` |
| Camera-page warning chip | `qml/DroppedFrameWarning.qml:1-26` (30 px, `#e63b2a13`, `#bfaa7937`, Inter Bold, CMake only, not in `qml.qrc`) |
| Components read layout from `displayConfigBridge` themselves | `qml/ActionTile.qml:14-23`, `qml/TogglePill.qml:7-17` |

## Findings

| Id | Title | Cat | Sev | Effort | Deliberate |
| --- | --- | --- | --- | --- | --- |
| F1 | ActionTiles with flipping tone used as radio buttons | mismatch | major | M | no |
| F2 | Timecode card: upstream "Mode" no longer sets file timecode; Free Run / Rec Run renamed | removed-upstream-behaviour | major | M | yes |
| F3 | ClipNameCard drag-and-drop composer | new-ground | major | M | partly |
| F4 | `recordItemVisible()` hides the Clip Names card | mismatch | minor | S | no |
| F5 | Storage pre-roll put inside the Media Speed card | mismatch | minor | S | unknown |
| F6 | UI text restates Core settings as constants | bug | minor | S | no |
| F7 | New items skip icon and favourite registration | mismatch | minor | S | no |
| F8 | Clip-name card drops unknown tokens on save | bug | minor | S | no |
| F9 | Clip-name edit lost if recording starts within 1 s | bug | minor | S | no |
| F10 | `set_timecode_mode target` with an original Core | protocol | minor | S | unknown |
| F11 | Hand-sized sub-labels and fixed font sizes in the new blocks | mismatch | minor | S | no |
| F12 | Ticket tag T45 in code | slop | nit | S | no |
| F13 | Clip-text popup strings inlined; `timecodeDisplayName` duplicates `timecodeChoices` | duplication | nit | S | no |

### F1 ActionTiles as radio buttons (mismatch, major)

Port: `tone: apertarControlBridge.bufferSetting === "frames" ? "accent" : "default"` (diff:540, :548, Frames/RAM); Log `label: cdngLogOn ? "On" : "Off"; tone: cdngLogOn ? "accent" : "default"` (diff:580-583); Automatic pre-roll On/Off tiles (diff:731-743); clip-name presets `tone: card.currentTemplate === modelData.template ? "accent" : "default"` (`ClipNameCard.qml:364-371`).
Upstream: booleans are `TogglePill` rows (`SettingsPage.qml:3562`, `:4885`); value choices are `InlineDropdownField` (Compression `:3250`); ActionTile tone is constant.
Why: the original developer reads an accent ActionTile as "the primary action" (Standby). Four new places teach a third widget idiom.
Rework (`qml/SettingsPage.qml` Format card, Media Speed card; `qml/ClipNameCard.qml`):
- Write Buffer: one `InlineDropdownField { label: "Write Buffer"; options: [{value:"frames",label:"Frames"},{value:"ram",label:"RAM"}]; onValueSelected: apertarControlBridge.applyBufferMode(v) }`, placed in the Bit Depth / Compression `Row` grid; keep the `#9aa5b1` helper text below.
- Log: `InlineDropdownField` "Log" with Off / On (value off/auto), same row; or a TogglePill row. Keep the status text.
- Automatic pre-roll: title + description + `TogglePill` row like `gyroRecordToggle`.
- Clip-name presets: `InlineDropdownField { label: "Pattern"; options: presetList (value/label) }` with "Custom" as displayValue when no preset matches; delete the "Custom pattern" Text.
- Keep `ActionTile` only for the verb "Storage Pre-roll".

### F2 Timecode card semantics and names (removed-upstream-behaviour, major)

Port (diff:614-663): label "Mode" -> "UI timecode", call `applyTimecodeMode(v, "ui")`; new "File timecode" calls `applyTimecodeMode(v, "files")`; labels "Time of Day"/"Clip" via `timecodeChoices` (diff:26); description reworded. Bridge `src/ApertarControlBridge.cpp:750-771@cinemate-port`; Core `src/ApertarCoreApp.cpp:13279-13300@cinemate-port` (`target` default "both").
Upstream: one dropdown "Mode" with "Free Run"/"Rec Run"; one call `applyTimecodeMode(v)` that sets the camera and UI.conf (`SettingsPage.qml:3753-3782`, `ApertarControlBridge.cpp:622-635`, Core `:9424-9435`).
Effect: an operator who sets "Rec Run" in the first dropdown, as in upstream, gets Rec Run on screen and Free Run in the files. Free Run / Rec Run are the industry terms the original developer chose; they no longer appear in Settings.
Deliberate: yes, commits `7029db1` and `08cefcf` explain it ("Rec Run normally continues from the previous clip, so the name was wrong").
Rework: keep the upstream dropdown as is: label "Mode", options `["Free Run", "Rec Run"]`, `applyTimecodeMode(v)` (target both). If a separate file timecode is kept, add it as a second dropdown "Files" whose first option is "Same as Mode" (sends nothing extra), so the default equals upstream. Delete `timecodeChoices` and `timecodeDisplayName()`; if the owner wants clearer names, put them in `description`, not in the values.
Risk: CameraPage tap toggles only the UI timecode on the port (commit `7029db1`); revert that in the same change (unit UI-camera-qml).

### F3 ClipNameCard composer (new-ground, major)

Port: `qml/ClipNameCard.qml` (601) + `qml/ClipNamePill.qml` (115). Own ListModel parser/serialiser (`:76-115`), 350 ms preview + 1000 ms auto-save timers (`:330-343`), own drag layer (`ghost` with `Drag.Internal` `:579-600`, `DropArea` `:392-402`, insertion marker `:449-471`, `indexAt` `:242-254`, begin/move/endDrag `:256-313`), long-press in the pill with `preventStealing` and a 0 ms reset Timer (`ClipNamePill.qml:53-94`), colours `#1d2a1d`, `#6cc070`, `#e0b447` new (accent `#3fd0ff`/`#123d59` match ActionTile).
Upstream: no free-form composer. Drag exists only for the reorder popup (`SettingsPage.qml:6111` `reorderDelegate`, DelegateModel). Settings edits are applied on selection, not by timers.
Test: none on a touch screen (fork-log:240 "untested by hand"; drop-frames README:102, :158).
Deliberate: partly. The KB documents the feature and the WebUI twin; no note weighs a simpler touch UI.
Verdict: simplify. Keep: preset dropdown (F1), the pill row as a read-only Flow, tap a palette pill to append, tap a row pill to select, the existing selection tiles (move left/right, Edit text, Remove), the "Next clip:" line. Delete: ghost, DropArea, insertion marker, `indexAt`, `beginDrag/moveDrag/endDrag`, the drag signals and long-press logic in ClipNamePill, `dragActive`-related properties. The arrows already do what drag does. Save on each edit (as upstream fields do) or keep one save timer; drop the preview timer if `preview_clip_name` can be sent on save. Estimate: about 200 lines less.

### F4 recordItemVisible (mismatch, minor)

Port: diff:269-273 `recordItemVisible(itemId)`; diff:845 `visible: root.recordItemVisible(modelData)` on the Record Loader.
Upstream: Loaders have no `visible:` (`SettingsPage.qml:7018-7023`); unavailable features keep their card and explain in `description` (`:3039`, `:3071`).
Side effect: the reorder popup still lists "Clip Names" while the card is hidden.
Rework: delete `recordItemVisible` and the Loader line; in `recordClipNamesComponent` set `description: apertarControlBridge && apertarControlBridge.clipNameKnown ? "How clip folders and files are named" : "Not available with this Core version"` and `ClipNameCard { enabled/visible: clipNameKnown }`.

### F5 Storage pre-roll inside Media Speed (mismatch, minor)

Port: diff:706-776 appends a tile, an Automatic block and three Texts to `systemMediaSpeedComponent`, whose description is "Measure sequential write performance".
Upstream: one card per feature, registered in `defaultPowerOrder` / `favoriteCandidateOrder` (`SettingsPage.qml:798-801`, `:838-878`).
Rework: new item id `storagePreroll` in `defaultPowerOrder` and `favoriteCandidateOrder`, title "Storage Pre-roll" in `sectionItemTitle`, branch in `powerComponentForId`, Component `systemStoragePrerollComponent` (SystemSectionCard, icon `media-speed.png`) holding the tile, the TogglePill row (F1) and the last-result text. Guard the card with `storagePrerollAutoKnown` as for F4 (the manual tile has no guard today: an original Core gets `storage_preroll` and replies "unknown command").

### F6 UI text restates Core settings (bug, minor)

| Text | Where | Core |
| --- | --- | --- |
| "Records 2 seconds at the top frame rate ..." | diff:759 | `preroll_seconds` 1..10, default 2 (`Apertar-Core src/util/StoragePreroll.hpp:23`) |
| "... Also runs when a card is inserted or formatted." | diff:759 | wrong when Automatic is Off (diff:748 says "Off: only the tile runs it") |
| "WebUI: http://<ip>:8000" | diff:819 | `--web-port PORT` (`core-upstream src/main.cpp:35`, `ApertarCoreApp.hpp:36`) |
| "Original queue: 12 frames" | diff:556 | Core constant, not reported in state (unconfirmed: `grep -rn "12" Apertar-Core/src/cdng/*Queue*`) |
Failing input: `preroll_seconds=5` -> card says 2 seconds; Core started with `--web-port 8080` -> card points to a dead address.
Rework: drop the numbers from the text, or read them from state (`storage_preroll_seconds`, a `web_port` field); drop the second sentence of diff:759.

### F7 Incomplete registration of new items (mismatch, minor)

Port: the 4 Monitoring rows (diff:407-477) have no `titleIconSource`, no `favoriteEnabled/favorited/onFavoriteToggleRequested`, and their ids are not in `favoriteCandidateOrder` (diff:122-136 adds only `controls`). `recordClipNamesComponent` (diff:665-687): no favourite. `infoControlsComponent` (diff:799-822): no icon.
Upstream: 39 of 42 Components carry both (see yardstick table).
Rework: add the 4 ids and `clipNames` to `favoriteCandidateOrder`, the three favourite lines to each Component, an icon each (existing `record.png`, `timecode.png`, `audio.png`, `media.png`, `config.png`).

### F8 Unknown tokens dropped (bug, minor)

Port: `ClipNameCard.qml:86-93` keeps a `{x}` only if `isKnownToken(x)` (QML copy of the list, `:28-34`); `saveNow` writes the reduced string back (`:156-170`).
Failing input: Core gains a token (`{iso}`) and the WebUI writes `{format}_{iso}_{clip}`; opening the touch card and moving one pill saves `{format}_{clip}`.
Token list is held three times: Core `src/util/ClipName.hpp:29-34`, WebUI `WebControlPage.cpp:14456-14472`, QML. Duplicating lists in QML has upstream precedent (resolution tables, ui-map section 4), so only the drop is the bug.
Rework: in `parseTemplate` keep any `{name}` as a token pill; the palette stays the QML list.

### F9 Edit lost when recording starts (bug, minor)

Port: `saveNow` returns when `!editable` (`ClipNameCard.qml:159`); on recording stop `syncFromBridge(true)` reloads Core's template (`:320-326`).
Failing input: move a pill, press record within 1 s: the save is skipped, the edit is replaced after the take.
Rework: save at once on each edit (F3), or call `saveNow()` from `onRecordingChanged` when recording starts and a save is pending (Core accepts it before the take begins, or refuses it with an error).

### F10 set_timecode_mode target with an original Core (protocol, minor)

Port UI + original Core: Core ignores `target` (`core-upstream src/ApertarCoreApp.cpp:9424-9435`), so "UI timecode" also sets the files and "File timecode" also writes UI.conf `timecodeMode`. Original UI + port Core: no `target` = both, unchanged. Flat JSON kept.
Rework: resolved by F2 (no `target` on the default path).

### F11 Sub-labels and font sizes (mismatch, minor)

Port: "Write Buffer", "Log", "Automatic pre-roll", "Pattern" as `Text { color: "white"; font.pixelSize: 14 }` without `font.family` (diff:526-531, :571-576, :720-725; `ClipNameCard.qml:350-355`); ClipNameCard texts 12-14 px fixed, layout only large/standard (`:16-21`), compact/medium layouts get the smallest sizes.
Upstream: sub-label style `SettingsPage.qml:5221-5228`; text sizes from layout tokens (`root.largeLandscapeLayout ? ... : root.standardLandscapeLayout ? ... : root.compactLandscapeLayout ? ...`).
Rework: mostly removed by F1 (dropdown labels). Remaining sub-labels: copy the "Write Test" style. ClipNameCard: take a `layout` flag from the page or add the compact/medium branches like `ActionTile.qml:14-23`.

### F12 T45 (slop, nit)

`// T45:` at diff:798 and `qml/ControlsWarning.qml:3`. Delete the tag, keep the sentence.

### F13 Duplication and inline conditionals (duplication, nit)

`timecodeDisplayName()` (diff:234-236) repeats the mapping in `timecodeChoices` (diff:26); gone with F2. The clip-text popup switches 4 strings inline (diff:868-910); upstream puts such switches in helper functions (`hotspotEditTitle`-style, `SettingsPage.qml:1862-1866`). Rework: `presetPopupTitle()`, `presetPopupHint()`, `presetPopupFieldLabel()`.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `ClipNameCard` | simplify | Keep presets, palette tap, selection tiles, preview; delete the drag layer (F3) |
| `ClipNamePill` | simplify | Keep as a display chip with tap; delete long-press drag, `preventStealing`, reset Timer |
| `ControlsWarning` | keep | Same shape, colours, size, registration as upstream `DroppedFrameWarning.qml`; remove T45 |
| `presetPopupPurpose` flag | keep | Upstream precedent `hotspotEditTarget`; move strings into helper functions (F13) |
| `recordItemVisible()` | rework-to-upstream-pattern | Upstream keeps the card and explains in `description` (F4) |
| Template mini-language mirror in QML | keep | Core owns it; QML list mirrors it as upstream mirrors resolution tables; stop dropping unknown tokens (F8) |
| `timecodeChoices` / `timecodeDisplayName` | rework-to-upstream-pattern | Return to the upstream "Mode" dropdown with Free Run / Rec Run (F2) |

## What conforms

- Item registration chain for all 6 new ids: order array, `sectionItemTitle`, `*ComponentForId`, one Component each (diff:59-136, :164-213, :327-386).
- 4 Monitoring switches are `MonitoringRow`s bound to `settingsState` (UI.conf), the same as the other aids (diff:407-477).
- Write Buffer and Log helper texts use the Format card's own helper style `#9aa5b1` / 12 px (upstream `SettingsPage.qml:3315-3316`).
- Compression greyed while Mode Ladder is active via `fieldEnabled` and label, the way upstream greys it while recording (diff:501, :511-512).
- Info Controls card: `SystemSectionCard` + `InfoDataRow`, favourite support, read-only, points to the WebUI for editing.
- `ControlsWarning.qml` copies `DroppedFrameWarning.qml` and is registered in CMake only, like it.
- Clip text input reuses the existing keyboard popup with a purpose flag, as upstream does for hotspot name / password.
- Clip-name presets and default (`{format}_{date}_{clip}` = "Original") agree with Core `ClipName.hpp:23` and the WebUI; names unchanged by default.
- No board assumptions, no env vars, no files written from this unit.

## Notes

- `qml.qrc` lists ClipNameCard/ClipNamePill but not ControlsWarning. Upstream `qml.qrc` already lacks `DroppedFrameWarning.qml` (it is only used when `APERTAR_QML_AOT` is off, `CMakeLists.txt:197-199`), so this is upstream drift, not a port defect.
- Bare `apertarControlBridge.x` next to guarded uses: upstream does the same (`SettingsPage.qml:3988` `!apertarControlBridge.recording`). Not reported.

## Skeptic

Checked at Apertar-UI `cinemate-port` `7ea9afc`, Apertar-Core `cinemate-port`, `/home/user/wt/ui-upstream` and `/home/user/wt/core-upstream` (`upstream-1.6.0`). "diff:N" = line of `/home/user/build/review/diffs/UI-SettingsPage.part01.diff`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: upstream `tone:` is constant everywhere (`grep -n "tone:" qml/*.qml` @upstream-1.6.0: 3640, 3650, 3712, 3723 default; 5179, 5437, 5763, 6924 danger; 5416 accent Standby). Booleans are TogglePill rows (`:3562`, `:4885`). Port diff:540, :548, :580-583, :735, :742, `ClipNameCard.qml:368` flip tone. |
| F2 | stands | Confirmed: port `src/ApertarControlBridge.cpp:750-771` sends `target`; upstream `:622-635` value only; upstream Core `ApertarCoreApp.cpp:9424-9435` sets camera + UI.conf; port Core `:13279-13299` keeps "both" as default. Commits `7029db1`, `08cefcf` state the intent. |
| F3 | corrected | Code confirmed. Apertar way was too strong: upstream does have long-press drag (reorder `SettingsPage.qml:6165-6211`, sidebar `:6282-6297` @upstream-1.6.0: `held`, `drag.target`, `Drag.active`, `pressAndHoldInterval: 260`, `preventStealing: false`). The port's ghost + manual `mapToItem` + `preventStealing = true` + 0 ms Timer is a different drag idiom from that precedent. Rework now names it. |
| F4 | stands | Confirmed: upstream section Loaders have no `visible` (`:7017-7024`); no upstream card hides itself; sound recorder (`:3039`) and exposure compensation (`:3071`) explain in `description`. |
| F5 | stands | Confirmed: `defaultPowerOrder` = media, formatMedia, mediaSpeed (`:798-802` @upstream-1.6.0); tile at diff:706-713 has no support guard; upstream Core replies `Unknown command: storage_preroll` (`ApertarCoreApp.cpp:10820`). Pre-roll is related to the card (warm-up/test) but has its own setting, so a separate card still fits. |
| F6 | corrected | "Original queue: 12 frames" removed: 12 is a hard Core constant (`CameraController.cpp:5628`, `:6944` `maxQueuedFrames_ = 12` @cinemate-port), not an operator setting. The pre-roll seconds (`StoragePreroll.hpp:17-23`, `[media] preroll_seconds=1..10`), the always-shown "Also runs when a card is inserted" (diff:759, outside the Automatic block) and `:8000` (`--web-port`, core-upstream `main.cpp:35,68`) stand. |
| F7 | stands | Confirmed: diff:407-477 four MonitoringRows without `titleIconSource`/favourite lines; `favoriteCandidateOrder` @cinemate-port lacks the 4 Monitoring ids and `clipNames`; `infoControlsComponent` (diff:799-822) has no icon. |
| F8 | corrected | Code confirmed (`ClipNameCard.qml:86-93`). Today the QML palette and Core `tokenNames()` (`src/util/ClipName.hpp:29-34`) hold the same 19 tokens, so no loss now; it is latent (newer Core, older UI). Severity minor -> nit. |
| F9 | stands | Confirmed: `saveNow` returns on `!editable` (`ClipNameCard.qml:156-160`); `onRecordingChanged` on stop stops timers and `syncFromBridge(true)` reloads Core's template (`:320-327`). |
| F10 | stands | Confirmed: original Core ignores `target` and sets both (`core-upstream ApertarCoreApp.cpp:9424-9435`); port UI's `fileTimecodeMode` has no source with an original Core. |
| F11 | corrected | The `#9aa5b1` / 12 px helper texts copy upstream's Format card (`:3309-3318`, no `font.family` there either), so they are not a mismatch. What remains: the white 14 px sub-labels "Write Buffer", "Log", "Automatic pre-roll", "Pattern" and the "Next clip" line, against the Write Test label style (`:5224-5230`); ClipNameCard pill sizes handle only large/standard (`ClipNameCard.qml:16-21`) where ActionTile handles four layouts (`ActionTile.qml:14-23`). |
| F12 | stands | Confirmed: `qml/SettingsPage.qml:6455` and `qml/ControlsWarning.qml:3` @cinemate-port. |
| F13 | dropped | Upstream itself inlines the per-target popup conditionals next to its helpers (`hotspotEditTarget` inline at `:8224`, `:8225`, `:8231`, `:8349` @upstream-1.6.0), so the inline switches are not a mismatch. The `timecodeDisplayName` / `timecodeChoices` duplication is deleted by F2's rework. |

No new finding added.

## Final findings

### UI-settings-qml-F1 ActionTiles with a flipping accent tone used as radio buttons
- category: mismatch; severity: major; effort: M; deliberate: no (commit `841d0ed` calls them "Frames / RAM buttons", "Log buttons"; no reasoning about widget choice)
- where: qml/SettingsPage.qml diff:537-551 (Write Buffer Frames/RAM)@cinemate-port; diff:578-584 (Log On/Off)@cinemate-port; diff:731-743 (Automatic pre-roll On/Off)@cinemate-port; qml/ClipNameCard.qml:364-371 (presets)@cinemate-port
- port way: `tone: apertarControlBridge.bufferSetting === "frames" ? "accent" : "default"`; the selected value is drawn as an accent ActionTile.
- Apertar way: booleans are title + description + `TogglePill` (qml/SettingsPage.qml:3562 `gyroRecordToggle`, :4885 `dateTimeOverlayToggle` @upstream-1.6.0); a value choice is `InlineDropdownField` with value/label options (Compression :3250); `ActionTile` is a verb with a constant tone (:3640 default, :5416 accent Standby); no conditional `tone:` in any upstream qml/*.qml.
- why it matters: the original developer reads an accent ActionTile as the primary action. Four places introduce a third widget idiom for a choice.
- rework: Write Buffer -> `InlineDropdownField { label: "Write Buffer"; options frames/ram; onValueSelected: applyBufferMode(v) }` in the Bit Depth / Compression row; Log -> TogglePill row (or dropdown Off/On); Automatic pre-roll -> TogglePill row like `gyroRecordToggle`; clip-name presets -> `InlineDropdownField` "Pattern" with `displayValue` "Custom" when none matches. Keep ActionTile only for the Storage Pre-roll verb. Keep the `#9aa5b1` status texts.

### UI-settings-qml-F2 Timecode card: upstream Mode no longer sets file timecode; Free Run / Rec Run renamed
- category: removed-upstream-behaviour; severity: major; effort: M; deliberate: yes (commits `7029db1`, `08cefcf`: split and renaming, "Rec Run normally continues from the previous clip, so the name was wrong")
- where: qml/SettingsPage.qml diff:614-663@cinemate-port; diff:24-26, 234-236@cinemate-port; src/ApertarControlBridge.cpp:750-771@cinemate-port
- port way: first dropdown relabelled "UI timecode", calls `applyTimecodeMode(v, "ui")`; new "File timecode" dropdown calls `applyTimecodeMode(v, "files")`; options shown as "Time of Day" / "Clip" via `timecodeChoices`.
- Apertar way: one dropdown "Mode", options ["Free Run", "Rec Run"], `applyTimecodeMode(v)` (qml/SettingsPage.qml:3753-3782 @upstream-1.6.0); bridge sends `set_timecode_mode` value only (src/ApertarControlBridge.cpp:622-635); Core sets camera and UI.conf together (core-upstream src/ApertarCoreApp.cpp:9424-9435).
- why it matters: an operator who picks Rec Run in the first dropdown, as in upstream, gets Rec Run on screen and Free Run in the files. The original developer's terms disappear from Settings.
- rework: restore the upstream dropdown verbatim (label Mode, Free Run / Rec Run, `applyTimecodeMode(v)` with no target). If a separate file timecode stays, add a second dropdown "Files" whose first option "Same as Mode" sends nothing, so the default equals upstream. Delete `timecodeChoices` and `timecodeDisplayName`; put clearer wording in `description`. Revert the CameraPage tap to toggle both (unit UI-camera-qml).

### UI-settings-qml-F3 ClipNameCard: drag-and-drop composer with its own drag layer, untested on touch
- category: new-ground; severity: major; effort: M; deliberate: unknown (KB working/drop-frames/README.md:102 documents the feature, "QML Drag / DropArea with tap fallbacks", and the WebUI twin; no note weighs a simpler touch UI)
- where: qml/ClipNameCard.qml:238-313, 392-471, 578-600@cinemate-port; qml/ClipNamePill.qml:53-94@cinemate-port
- port way: 601 + 115 lines: ListModel parser/serialiser, 350 ms preview and 1000 ms save timers, ghost Rectangle with `Drag.Internal` positioned by hand through `mapToItem`, DropArea, insertion marker, `indexAt`, begin/move/endDrag, long-press that sets `preventStealing = true` plus a 0 ms reset Timer, new colours `#123d59`/`#3fd0ff`/`#e2f6ff`.
- Apertar way: no precedent for a composer. Upstream drag exists only in the reorder and sidebar popups (qml/SettingsPage.qml:6111-6211 `reorderDelegate`, :6282-6297 sidebar @upstream-1.6.0): `held` flag, `drag.target` on the delegate's content item, `Drag.active: held`, `pressAndHoldInterval: 260`, `preventStealing: false`, DelegateModel moves. Fields apply on selection without timers.
- why it matters: largest new QML in the unit, never run on a touch screen (fork-log `841d0ed` row: "untested by hand"; drop-frames README:102, :158). The selection tiles (move left/right, Edit text, Remove) already do what drag does, so the drag layer is a second way to the same result in a second drag idiom.
- rework: simplify. Keep the preset dropdown (F1), the pill row as a Flow of tappable chips, palette tap to append, the selection tiles, the "Next clip" line. Delete ghost, DropArea, marker, `indexAt`, begin/move/endDrag, drag signals and long-press code in ClipNamePill, `drag*` properties. Save on each edit instead of the two timers if the preview can follow the save. About 200 lines less. If drag is kept, rebuild it on the reorderDelegate pattern (`drag.target`, `held`), not a hand-positioned ghost.

### UI-settings-qml-F4 recordItemVisible() hides the Clip Names card
- category: mismatch; severity: minor; effort: S; deliberate: no
- where: qml/SettingsPage.qml diff:269-273, 845@cinemate-port
- port way: the Record Repeater Loader gets `visible: root.recordItemVisible(modelData)`; `clipNames` is hidden until Core reports a template.
- Apertar way: section Loaders have no visible hook (qml/SettingsPage.qml:7017-7024 @upstream-1.6.0); unavailable features keep the card and explain in `description` (:3039 sound recorder, :3071 exposure compensation).
- why it matters: a new per-item hook in the section machinery; the reorder popup still lists the hidden item.
- rework: delete `recordItemVisible` and the Loader line; in `recordClipNamesComponent` set `description` to "Not available with this Core version" when `!clipNameKnown` and hide/disable the ClipNameCard inside the card.

### UI-settings-qml-F5 Storage pre-roll placed inside the Media Speed card
- category: mismatch; severity: minor; effort: S; deliberate: unknown
- where: qml/SettingsPage.qml diff:706-776@cinemate-port
- port way: tile, Automatic On/Off block and three Texts appended to `systemMediaSpeedComponent` (description "Measure sequential write performance"); the manual tile has no Core-support guard.
- Apertar way: one card per feature, registered in `defaultPowerOrder`, `favoriteCandidateOrder`, `sectionItemTitle`, `powerComponentForId` (qml/SettingsPage.qml:798-802, :838-878, :2336 @upstream-1.6.0).
- why it matters: a separate feature with its own setting hidden in another card, not reorderable or favouritable; with an original Core the tile sends `storage_preroll` and gets "Unknown command: storage_preroll" (core-upstream ApertarCoreApp.cpp:10820).
- rework: new id `storagePreroll` in `defaultPowerOrder` and `favoriteCandidateOrder`, title "Storage Pre-roll", branch in `powerComponentForId`, Component `systemStoragePrerollComponent` (SystemSectionCard, icon media-speed.png) with the tile, a TogglePill row for Automatic, the last-result text; unavailable description and disabled tile when `!storagePrerollAutoKnown`.

### UI-settings-qml-F6 UI text states Core settings as fixed values
- category: bug; severity: minor; effort: S; deliberate: no
- where: qml/SettingsPage.qml diff:759@cinemate-port; diff:819@cinemate-port
- port way: "Records 2 seconds ... Also runs when a card is inserted or formatted." (always shown, outside the Automatic block); "WebUI: http://<ip>:8000, Settings, Controls".
- Apertar way: Core lets the operator change these: `[media] preroll_seconds=1..10` (Apertar-Core src/util/StoragePreroll.hpp:17-23 @cinemate-port); `--web-port PORT` (core-upstream src/main.cpp:35,68; ApertarCoreApp.hpp:36 @upstream-1.6.0). Upstream UI nowhere prints the WebUI port.
- why it matters: `preroll_seconds=5` -> the card says 2 s; Core started with `--web-port 8080` -> the card points to a dead address; with Automatic Off the text still says it runs on card insert.
- rework: drop the number from the pre-roll text or read it from state; drop the second sentence of diff:759 (the Automatic block already says it); drop ":8000" or read the port from Core state.
- (Not part of the finding: "Original queue: 12 frames" diff:556 matches Core's fixed `maxQueuedFrames_ = 12`, CameraController.cpp:5628.)

### UI-settings-qml-F7 New items skip icon and favourite registration
- category: mismatch; severity: minor; effort: S; deliberate: no
- where: qml/SettingsPage.qml diff:407-477@cinemate-port; diff:665-687@cinemate-port; diff:799-822@cinemate-port
- port way: 4 Monitoring rows: no `titleIconSource`, no `favoriteEnabled`, ids not in `favoriteCandidateOrder`; clipNames: no favourite and not in `favoriteCandidateOrder`; controls: no icon.
- Apertar way: 39 of 42 upstream Components carry `titleIconSource` and `favoriteEnabled`/`favorited`/`onFavoriteToggleRequested` (e.g. `monitoringGreyscaleComponent` qml/SettingsPage.qml:2865-2885 @upstream-1.6.0).
- why it matters: new items behave unlike their neighbours in the Favorites manager and the section list.
- rework: add the 4 Monitoring ids and `clipNames` to `favoriteCandidateOrder`, the three favourite lines to each Component, and an existing icon to each (record.png, timecode.png, audio.png, media.png, config.png).

### UI-settings-qml-F8 Clip-name card drops unknown tokens when it saves
- category: bug; severity: nit; effort: S; deliberate: no
- where: qml/ClipNameCard.qml:28-34, 66-93, 156-170@cinemate-port
- port way: `parseTemplate` keeps `{x}` only if it is in the QML `paletteGroups` copy; `saveNow` writes the reduced string.
- Apertar way: duplicating Core lists in QML has precedent (per-sensor resolution tables, ui-map section 4); the token list is also in Core src/util/ClipName.hpp:29-34 and WebControlPage.cpp:14456-14472. Today both lists hold the same 19 tokens.
- why it matters: latent. A newer Core gains a token, the WebUI writes `{format}_{iso}_{clip}`; one pill move on this touch card saves `{format}_{clip}`.
- rework: in `parseTemplate` keep any `{name}` as a token pill; the palette remains the QML list.

### UI-settings-qml-F9 Clip-name edit lost when recording starts within the 1 s save delay
- category: bug; severity: minor; effort: S; deliberate: no
- where: qml/ClipNameCard.qml:156-160, 317-327@cinemate-port
- port way: `saveNow` returns when `!editable`; on recording stop `syncFromBridge(true)` reloads Core's template.
- Apertar way: no precedent (upstream applies settings at once).
- why it matters: move a pill, press record within 1 s: the save is skipped, the edit is silently replaced after the take.
- rework: save on each edit (with F3), or save a pending edit from `onRecordingChanged` when recording starts.

### UI-settings-qml-F10 set_timecode_mode target ignored by an original Core
- category: protocol; severity: minor; effort: S; deliberate: unknown
- where: src/ApertarControlBridge.cpp:758-760@cinemate-port; qml/SettingsPage.qml diff:644, 659@cinemate-port
- port way: adds a `target=ui|files` argument; port Core defaults to "both" (Apertar-Core ApertarCoreApp.cpp:13279-13299), so the original UI keeps working.
- Apertar way: `set_timecode_mode` with value only, sets camera and UI.conf (core-upstream src/ApertarCoreApp.cpp:9424-9435 @upstream-1.6.0).
- why it matters: port UI + original Core: each dropdown changes both file and UI timecode, so the two dropdowns fight, and "File timecode" has no state source. Flat JSON is kept; original UI + port Core is fine.
- rework: resolved by F2 (default path sends no target).

### UI-settings-qml-F11 Hand-sized sub-labels and fixed sizes in the new blocks
- category: mismatch; severity: minor; effort: S; deliberate: no
- where: qml/SettingsPage.qml diff:526-531, 571-576, 720-725@cinemate-port; qml/ClipNameCard.qml:16-21, 350-355, 512-519@cinemate-port
- port way: `Text { color: "white"; font.pixelSize: 14 }` without `font.family` as sub-headings ("Write Buffer", "Log", "Automatic pre-roll", "Pattern") and for "Next clip"; pill height/font only for large/standard layouts.
- Apertar way: sub-label "Write Test": `#66ffffff`, Inter Medium, uppercase, letterSpacing 2.0, layout-dependent size (qml/SettingsPage.qml:5224-5230 @upstream-1.6.0); components handle four layouts (qml/ActionTile.qml:14-23). The `#9aa5b1` / 12 px helper texts copy upstream's Format card (:3309-3318) and are fine.
- why it matters: the new sub-labels render in the default font and do not scale with the layout like the rest of the page.
- rework: mostly removed by F1 (dropdown labels). Remaining sub-labels copy the Write Test style; ClipNameCard adds compact/medium branches (as ActionTile does) for pill size.

### UI-settings-qml-F12 Ticket tag T45 in code comments
- category: slop; severity: nit; effort: S; deliberate: no
- where: qml/SettingsPage.qml:6455@cinemate-port (diff:798); qml/ControlsWarning.qml:3@cinemate-port
- port way: `// T45: ...`
- Apertar way: no ticket tags in upstream comments.
- why it matters: internal work-package number, meaningless to the original developer.
- rework: delete "T45: ", keep the sentence.
