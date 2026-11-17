# Review WCP-05: WebControlPage.cpp JS, settings / presets / favourites (new-file lines 9168-11399)

Diff: `/home/user/build/review/diffs/WCP.part05.diff` read whole. Inventory: `raw/inv-WCP-05.md`.
Refs: port `@cinemate-port` (`/home/user/Apertar-Core`), upstream `@upstream-1.6.0` (`/home/user/wt/core-upstream`).
Yardstick: no `apertar-conventions.md` yet; `conv-core-*.md` cover Core only, so WebUI comparisons below are read directly in the upstream file.
About 2000 of the 2230 lines are unchanged upstream code. Preset code is untouched.

## Verdict

The slice mostly extends upstream functions in place, in upstream's own shape (if-chains, per-sensor helper
families, lazy loads in `setSettingsPanel`). Foreign pieces: a generic `locked` flag wired to one feature's
warning inside the generic pill builder, a second lock mechanism next to it, a MutationObserver-driven
search module, the History API in the media overlay, the renamed timecode labels, a new separator glyph,
dead "older Core" fallbacks and one ticket token (`Q2`).

## Findings

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | Ladder lock: feature-specific warning inside generic `createPillGrid`; two lock mechanisms | mismatch | minor | yes |
| F2 | Timecode labels "Free Run"/"Rec Run" renamed to "Time of Day"/"Clip" | removed-upstream-behaviour | minor | yes |
| F3 | One timecode setting split into UI and file timecode (two favourites blocks) | new-ground | minor | yes |
| F4 | Settings search: 110-line module with MutationObserver and DOM insertion | new-ground | minor | yes |
| F5 | History API (`pushState`/`go`/`popstate`) in `setMediaBrowserOpen` | new-ground | minor | yes |
| F6 | `imx585Selected()` predicate and top-of-function early return; imx283 uses inline `indexOf` | mismatch | nit | unknown |
| F7 | New labels use "·" separator; upstream uses "•" everywhere | mismatch | nit | no |
| F8 | "older Core" fallbacks in a page served by the same Core (`media_alive`, `wb_steps`) | slop | nit | no |
| F9 | Ticket token `Q2` in a code comment | slop | nit | no |
| F10 | Favourites Bit Depth lock reaches into `bitDepthBlock.lastChild` | slop | nit | no |

### F1 Ladder lock in the generic pill builder (mismatch, minor)

Port `WebControlPage.cpp:10728-10733@cinemate-port`:
```
button.disabled = !option.enabled && !option.locked;
button.addEventListener("click", () => {
  if (option.locked) { showLadderLockWarning(false); return; }
```
plus `normalizeChoiceOptions` gains `locked` (`:10447`). Selects use a second mechanism: `dataset.ladderLock` on
fields (`:11144`, `:11158`, `:15929`) and a document click delegate (`:20687-20689`).
Upstream: generic builders stay generic; a reason for refusal is given by the caller's `onSelect` with
`showToast`, e.g. Sound Recorder `@upstream-1.6.0` (favourites, port `:11109-11112` unchanged):
`if (!audioOptions.hasInputDevices) { showToast("No audio input device detected.", true); return; }`.
Upstream `createPillGrid` (`@upstream-1.6.0 ~6629`): `button.disabled = !option.enabled;` only.
Rework: drop `locked` from `normalizeChoiceOptions` and `createPillGrid`; `ladderLockedOptions` keeps options
enabled but styled (class); the Bit Depth `onSelect` starts with `if (snapshot.ladder_active === true) { showLadderLockWarning(false); return; }`
as upstream does for Sound Recorder. One mechanism (the `data-ladder-lock` delegate) for selects stays, or both
become onSelect guards.

### F2 Timecode labels renamed (removed-upstream-behaviour, minor)

Port `:9786-9788`: `timecodeDisplayName` maps "Rec Run" -> "Clip", else "Time of Day"; used in favourites
(`:11186-11190`), summary (`:10558`). Touch UI renamed too (`Apertar-UI/qml/SettingsPage.qml:21, :1220`).
Upstream `:5852`: `timecodeModeLabel` -> "Rec Run" / "Free Run", shown as is (`:7042`).
Commit 2c259b9 gives the reason (Rec Run normally continues across clips). Stored values unchanged, protocol unchanged.
Why it matters: upstream's operator-visible names change in both UIs; an upstream maintainer may disagree with the naming.
Rework: keep the upstream labels in the port; offer the rename as a separate small upstream proposal (commit 2c259b9 is already isolated).

### F3 UI vs file timecode split (new-ground, minor)

Upstream `ApertarCoreApp.cpp:9424-9437@upstream-1.6.0`: one `set_timecode_mode` sets camera and writes UI.conf `timecodeMode`.
Port: `target=ui|files|both`, default both (commit 909aaa5); WebUI `timecodeCommand(value, target)` (`:9802`), favourites now two blocks.
Protocol: additive scalar field, default keeps original behaviour, so an unmodified UI still works. Flat JSON kept.
Verdict keep, simplify: the favourite could stay one "Timecode" block (target both) with the split only on the
Timecode card, so the default operator sees upstream's single control. `timecodeSummaryLabel` fine.

### F4 Settings search (new-ground, minor)

Port `:10203-10289`: `settingsSearch` object, haystack, groups, `applySettingsSearch` builds `.settings-search-label`
and `#settingsSearchEmpty` in the DOM, MutationObserver on `.settings-panels` (subtree, characterData) with 250 ms debounce.
Upstream: no search; no MutationObserver, IntersectionObserver or pushState in the whole file. Upstream has one
central render, `renderSnapshot` (`@upstream-1.6.0 :9327`).
Commit d44b177 lists it ("a search box like CineMate's"); squash of 19 commits, so weighed but bundled.
Cost: while a query is active, every 1 Hz text update re-runs the full filter.
Verdict simplify: put the label and empty-state elements in the static HTML; replace the observer by one
`if (settingsSearch.active) applySettingsSearch();` at the end of `renderSnapshot` (and after async loaders
that rebuild cards); keep the class-only toggling, which is sound. Move to its own commit.

### F5 History API in the media overlay (new-ground, minor)

Port `:10115-10145` `setMediaBrowserOpen(open, fromHistory)`; `popstate` handler `:20637`; `state.pb.ignorePop`.
Upstream `:6139-6148`: toggle class and `#mediaBrowserOverlay`, `fetchMediaLibrary`. No history use anywhere.
Verdict keep (small, phone Back is a real need); it belongs to the Playback unit. Note the overlay replacement removes
upstream's row list with Download/Delete (`@upstream-1.6.0 :3979`); replaced by grid with Download/Remove (commit bc12c0a), judged in the Playback unit.

### F6 imx585Selected (mismatch, nit)

Port `:8935` `imx585Selected(snapshot)`; dispatchers start with `if (imx585Selected(snapshot)) return imx585...(snapshot);`
while the imx283 branch in the same functions uses `sensorNameLower(snapshot).indexOf("imx283") !== -1` (`:9241`, `:9264`).
Upstream: inline `sensorNameLower(snapshot).indexOf("imx294") !== -1` in each dispatcher (`@upstream-1.6.0 :5288-5356`).
Rework: inline `indexOf("imx585")` like the others, or nothing; consistency is the point.

### F7 Separator glyph (mismatch, nit)

Port `codecDisplayLabel` " · Log" (`:9788`), `timecodeSummaryLabel` "UI x · Files y", crop label "2.39:1 · 3840x1608" (`:9045`).
Upstream file: 0 uses of "·", 31 of "•" (summary lines, e.g. `return recordFormatText + " • " + ...`).
Rework: use " • ".

### F8 Dead "older Core" fallbacks (slop, nit)

`hasMedia` (`:10883`): `snapshot.media_alive !== undefined ? snapshot.media_alive : snapshot.media_mounted`.
Core emits both fields in every state (`ApertarCoreApp.cpp:9554, :9556@cinemate-port`), and the page is compiled into
the same binary, so the fallback branch never runs. Same for `valueStepsFromSnapshot` "fallback for an older Core" (`:7568`, outside slice).
Rework: read `media_alive` directly (or keep upstream's `media_mounted` if the two never differ for this use).

### F9 Ticket token (slop, nit)

`:10123` comment "(filter only, Q2)". Outside the slice but same functions: "T33" (`:7568`, `:8483`), "Request 24" (`:7576`), "T34" (`:7636`).
Rework: drop the tokens.

### F10 DOM-structure dependence (slop, nit)

`:11171` `bitDepthBlock.lastChild.classList.toggle("ladder-locked", ladderActive)` depends on the internal shape of
`createFavoriteSelectBlock`. Goes away with F1's rework.

## Checked and not reported

| Point | Result |
| --- | --- |
| Unknown-sensor tail `[]` in `sensorBaseResolutionOptionsForSnapshot` / `sensorCropRatioOptionsForSnapshot` / `sensorResolutionForBaseAndRatio` (upstream fell back to imx585 lists) | unreachable: both callers (`:10934`, `:15245`) only call it when `sensorCropControlsAvailableForSnapshot` is true, i.e. a named sensor. No behaviour change. |
| Clear HDR availability after hunk 2 | kept: `clearHdrAvailableForSnapshot` (`:9035`) gates the HDR family pills (cDNG/MLV, no photo mode). |
| H.264 forced capture size for imx585 | kept: `imx585NormalizedResolution` (`:9080`) checks `processedVideoRecordFormatForSnapshot` first. |
| `cropRatioEnabled` (hunk 18) | now identical to upstream `:6813` (fork-main's Clear HDR clause removed). |
| `formatMinutes` floor (hunk 8) | aligns WebUI with upstream touch UI `MediaStatusBridge::remainingMinutesText` (`m_remainingSeconds / 60`, `ui-upstream/src/MediaStatusBridge.cpp:401`). |
| `set_timecode_mode target` | protocol additive, default both; original UI unaffected. |
| 1.85:1 sizes 3840x2072 / 1920x1036 | old labels still accepted in `resolutionCommandPayload`; upstream if-chain style kept. |

## Abstraction verdicts

| Name | Verdict | Reason |
| --- | --- | --- |
| `imx585*` block + `imx585Selected` | keep (predicate: simplify, F6) | per-sensor helper family is upstream's pattern (`imx294*`, `imx477*`). Its dependency on `state.ladderServer.pool` belongs to the Mode Ladder unit. |
| `imx283*` block | keep | same shape as `imx294*`, dispatched inline like upstream. |
| `whiteBalanceStepsForSnapshot` / `valueStepsFromSnapshot` | keep | constant stays as default; drop "older Core" wording (F8). |
| `settingsSearch` module | simplify | F4. |
| `state.pb` + History API | keep | F5; judged in Playback unit. |
| `codecDisplayLabel`, timecode label helpers | keep / simplify | small label helpers like upstream `timecodeModeLabel`; `timecodeDisplayName` rework per F2. |
| `option.locked` / `ladderLockedOptions` / `showLadderLockWarning` | rework-to-upstream-pattern | F1. |

## Conforms

| What | Where |
| --- | --- |
| Lazy loads per pane in `setSettingsPanel` / `setSettingsOpen` follow upstream's `fetchPresetLibrary(true)` / `fetchConfigFile(true)` / audio refresh lines | `:10101-10113`, `:10172-10184` vs `@upstream-1.6.0 ~6150-6175` |
| `resolutionCommandPayload` extended in upstream's flat if-chain | `:9389-9396` |
| `cropRatioLabelForResolutionValue` extended in place, imx283 lookup placed like upstream's imx294 lookup | `:9655-9660` |
| `imx283*` dispatch branches mirror `imx294*` | `:9241`, `:9264`, `:9278`, `:9300` |
| Hunk 18 restores the upstream `cropRatioEnabled` line | `:10937` vs `@upstream-1.6.0 :6813` |
| `formatMinutes` rounds like the upstream touch UI | `:9904-9915` |
| `set_timecode_mode` keeps flat scalar JSON and old default | `timecodeCommand :9802` |
| Commit messages carry Why/What/Tested and name the stored-value compatibility | 909aaa5, 2c259b9 |

## Skeptic

Each finding re-read on both sides (`@cinemate-port` = `/home/user/Apertar-Core`, `@upstream-1.6.0` = `/home/user/wt/core-upstream`). Several reviewer line numbers were off by about 8-10 lines; corrected below.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Confirmed (`createPillGrid :10728-10735`). Missed the third copy in `buildOptionButtonsInto :15038-15045` (same `locked` -> `showLadderLockWarning(false)`). Upstream builders: `button.disabled = !option.enabled` only (`@upstream-1.6.0 :6608, :9158`). Rework refined: the greyed-but-clickable look Patrik asked for (392e812) must survive, so the builder keeps one generic flag and hands the click to the caller's onSelect, where the guard lives. |
| F2 | stands | `timecodeDisplayName :9798-9800`, `timecodeChoices :9802`; upstream `timecodeModeLabel :5852`, favourite `:7042`. UI side is commit 08cefcf (`qml/SettingsPage.qml:20, :1219`). Lines corrected. |
| F3 | corrected | Confirmed: Core `target` at `ApertarCoreApp.cpp:13284-13294@cinemate-port`, WebUI `timecodeCommand :9825`, favourites `:11176-11182`. Touch UI also split (7029db1). Lines corrected; rework keeps one favourite that shows `timecodeSummaryLabel` (`:9822`) when the two differ. |
| F4 | corrected | Confirmed (`:10204-10281`); upstream has 0 Observer uses. The cost argument is weak (the proposed renderSnapshot hook runs per snapshot too); the point is the foreign pattern and runtime DOM insertion. Matters text corrected. |
| F5 | corrected | "Only history state in the page" is wrong: the clip viewer also does `history.pushState({ pb: 2 })` / `history.back()` (`:12777, :12869`), and the Playback code adds an IntersectionObserver (`:11779`). No rework in this slice, so severity minor -> nit; it is a pointer to the Playback unit. |
| F6 | corrected | Confirmed. Sites corrected: `imx585Selected` at `:8935`, used at `:9036, :9130, :9236, :9247, :9268, :9281, :9293, :9313`; imx294/imx283 inline `indexOf` in the same functions. Upstream inline `sensorLower.indexOf("imx585") !== -1` (`@upstream-1.6.0 :4890, :4976, :5119, :5171`). Deliberate: the early return is stated in 66b324d, the predicate name is not. |
| F7 | corrected | Not slice-local: 32 lines of the port use " · " (ladder `:7965-8354`, Controls `:17307-18571`, playback `:12335`, resolution line `:15396`). Upstream: 0 "·", 30 " • ". Rework is a port-wide sweep. |
| F8 | corrected | Confirmed dead: Core emits `media_mounted` and `media_alive` in every state (`ApertarCoreApp.cpp:9554, :9556@cinemate-port`) and the `ui.*_steps` arrays always (`:1966-1969`). Lines corrected: `hasMedia :10891` and a second copy `:15255`; "older Core" comment `:7568-7569`. |
| F9 | corrected | Confirmed at `:10123`. 23 comment lines in the file carry T/Q/Request tokens; rework is a port-wide sweep, not one comment. |
| F10 | dropped | Upstream does the same thing: `card.lastChild.children[1].disabled = true;` reaches into `createFavoriteActionRow` output (`@upstream-1.6.0 :7116`). Not a mismatch on its own; it disappears with the F1 rework anyway. |

## Final findings

### WCP-05-F1 [mismatch, minor] Mode Ladder lock wired into the generic pill builders; two lock mechanisms
- where: `src/web/WebControlPage.cpp:10446-10447` (`normalizeChoiceOptions` `locked`), `:10728-10735` (`createPillGrid`), `:15038-15045` (`buildOptionButtonsInto`), `:8478-8480` (`ladderLockedOptions`), `:11144`, `:11158`, `:11166` (bitDepthBlock.lastChild), `:15929`, `:20684-20690` (document click delegate) @cinemate-port
- port way: options gain `locked`; both generic pill builders keep locked pills enabled and call the feature toast `showLadderLockWarning(false)` themselves. Select fields use a second mechanism: `dataset.ladderLock` plus a document-level click delegate.
- Apertar way: generic builders are generic: `button.disabled = !option.enabled;` and nothing else (`@upstream-1.6.0 :6608` createPillGrid, `:9158` buildOptionButtons). A refusal reason is the caller's job, in its onSelect: Sound Recorder `if (!audioOptions.hasInputDevices) { showToast("No audio input device detected.", true); return; }` (`@upstream-1.6.0 :6992-6995`).
- why it matters: a feature toast hard-wired into two shared builders, plus a parallel select mechanism, is coupling the original developer has to unpick when the next "greyed, but say why" case arrives.
- rework: rename `locked` to a generic flag (e.g. `blocked`: looks disabled, stays clickable) handled the same way in both builders: add the `disabled` class, keep the button enabled, call `onSelect(option.value)`. Each ladder-locked caller (Resolution/Crop pills `:15978`, `:15990`; favourites Bit Depth `:11161`) starts its onSelect with `if (state.snapshot && state.snapshot.ladder_active === true) { showLadderLockWarning(false); return; }`, as upstream does for Sound Recorder. Selects: keep one mechanism (the `data-ladder-lock` delegate is fine) and pass the class through `createFavoriteSelectBlock` instead of `bitDepthBlock.lastChild`.
- effort: S
- deliberate: yes. 392e812 "a locked control answers with the red warning; the selected one goes grey too" (the behaviour is wanted; the placement is not argued).

### WCP-05-F2 [removed-upstream-behaviour, minor] Upstream timecode labels Free Run / Rec Run shown as Time of Day / Clip
- where: `src/web/WebControlPage.cpp:9796-9803` (`timecodeDisplayName`, `timecodeChoices`), `:9822`, `:11176-11182` @cinemate-port; `Apertar-UI qml/SettingsPage.qml:20, :1218-1220` @cinemate-port
- port way: stored values stay "Free Run"/"Rec Run"; every label shown in the WebUI and touch UI Settings is "Time of Day"/"Clip".
- Apertar way: `timecodeModeLabel` returns "Rec Run"/"Free Run" and is shown as is (`@upstream-1.6.0 :5852`, favourite `:7042`); touch UI uses the same words (`ui-upstream qml/CameraPage.qml:1693-1710`).
- why it matters: operator-visible upstream naming changes in both UIs; the original developer may not share the naming argument.
- rework: keep the upstream labels in the merge. Offer the rename as its own upstream proposal; Core 2c259b9 and UI 08cefcf are isolated commits and can be held back.
- effort: S
- deliberate: yes. 2c259b9 / 08cefcf: Rec Run normally continues across clips, Apertar restarts per clip.

### WCP-05-F3 [new-ground, minor] One timecode setting split into UI and file timecode; favourite became two blocks
- where: `src/web/WebControlPage.cpp:9819-9823` (`timecodeSummaryLabel`), `:9825-9827` (`timecodeCommand`), `:11176-11182` (favourites) @cinemate-port; `src/ApertarCoreApp.cpp:13284-13294@cinemate-port`; UI commit 7029db1
- port way: `set_timecode_mode target=ui|files|both` (no target = both); favourites show "UI Timecode" and "File Timecode".
- Apertar way: one `set_timecode_mode` sets the camera and UI.conf `timecodeMode` together (`ApertarCoreApp.cpp:9424-9437@upstream-1.6.0`); one "Timecode Mode" favourite (`WebControlPage.cpp:7042@upstream-1.6.0`).
- why it matters: protocol is additive and default-compatible, but the quick-access favourite now exposes a power-user split by default.
- rework: keep `target` in Core and on the Timecode card. Favourite back to one "Timecode Mode" block sending `target=both`, value text from `timecodeSummaryLabel` so a split state stays visible.
- effort: S
- deliberate: yes. 909aaa5 Why/What.

### WCP-05-F4 [new-ground, minor] Settings search with a MutationObserver and runtime DOM insertion
- where: `src/web/WebControlPage.cpp:10183-10289` (`settingsSearch`, `applySettingsSearch`, observer `:10272-10279`) @cinemate-port
- port way: `applySettingsSearch` inserts `.settings-search-label` per panel and `#settingsSearchEmpty` at runtime; a MutationObserver (childList, subtree, characterData) on `.settings-panels` re-runs the filter 250 ms after any change while a query is active.
- Apertar way: no search upstream (no precedent for the feature). Upstream uses no Mutation/Intersection/Resize Observer anywhere (0 hits) and refreshes the page from one `renderSnapshot` (`@upstream-1.6.0 :9327`); static elements live in the HTML string.
- why it matters: the observer is a refresh path the original developer will not expect next to `renderSnapshot`; elements that exist only after a search are not in the HTML he reads.
- rework: put the per-panel label and the empty-state div in the static HTML (hidden by class). Drop the observer; call `if (settingsSearch.active) applySettingsSearch();` at the end of `renderSnapshot` (`:15214`) and after the async card loaders in `setSettingsPanel`. Keep the class-only show/hide. Put it in its own commit (now inside squash d44b177).
- effort: M
- deliberate: yes. d44b177: "a search box like CineMate's (filters cards on every page)", bundled in a 19-feature squash.

### WCP-05-F5 [new-ground, nit] History API for phone Back in the media overlay (pointer to Playback unit)
- where: `src/web/WebControlPage.cpp:10115-10145` (`setMediaBrowserOpen`), `:12777`, `:12869` (viewer), `:20637-20649` (popstate) @cinemate-port
- port way: `history.pushState` on open (and again for the viewer), `history.go(-steps)` on close, a popstate listener with `state.pb.ignorePop`.
- Apertar way: `setMediaBrowserOpen` toggles a class and `#mediaBrowserOverlay` and fetches the library (`@upstream-1.6.0 :6139-6147`); no history use in the file.
- why it matters: small and meets a real need, but it is a second navigation model the original developer has to know about.
- rework: none in this slice; document it in the Playback handoff and judge it in the Playback unit.
- effort: S
- deliberate: yes. bc12c0a: "the phone's Back closes it".

### WCP-05-F6 [mismatch, nit] `imx585Selected` predicate next to inline `indexOf` for the other sensors
- where: `src/web/WebControlPage.cpp:8935`; uses `:9036, :9130, :9236, :9247, :9268, :9281, :9293, :9313` @cinemate-port
- port way: dispatchers start with `if (imx585Selected(snapshot)) return imx585...(snapshot);`, the imx294/imx283/imx477 branches in the same functions use `sensorNameLower(snapshot).indexOf("...") !== -1`.
- Apertar way: inline `indexOf` per sensor, imx585 included (`@upstream-1.6.0 :4890, :4976, :5119, :5171`).
- why it matters: two styles for the same dispatch in one function.
- rework: inline `sensorNameLower(snapshot).indexOf("imx585") !== -1` and drop `imx585Selected`; keep the early returns.
- effort: S
- deliberate: unknown. 66b324d states the early return per dispatcher; the predicate is not discussed.

### WCP-05-F7 [mismatch, nit] Port labels use the " · " separator; upstream uses " • "
- where: slice `src/web/WebControlPage.cpp:9044, :9791, :9822`; port-wide 32 lines incl. `:7965-8354` (ladder), `:12335`, `:15396`, `:15914`, `:17307-18571` (Controls) @cinemate-port
- port way: " · Log", "UI x · Files y", "2.39:1 · 3840x1608", ladder and Controls meta lines.
- Apertar way: summaries join with " • " (30 uses, 0 uses of "·") e.g. favourites summary `recordFormatText + " • " + ...` (`@upstream-1.6.0 ~6440`).
- why it matters: mixed glyphs in the same summary lines.
- rework: one port-wide replace of " · " with " • " in user-visible strings (comments may follow).
- effort: S
- deliberate: no

### WCP-05-F8 [slop, nit] "Older Core" fallbacks in a page served by the same Core binary
- where: `src/web/WebControlPage.cpp:10891`, `:15253-15255` (`hasMedia`), `:7568-7569` (`valueStepsFromSnapshot` comment) @cinemate-port
- port way: `snapshot.media_alive !== undefined ? snapshot.media_alive : snapshot.media_mounted`; value lists "the fallback for an older Core".
- Apertar way: `const hasMedia = !!(snapshot && snapshot.media_mounted);` (`@upstream-1.6.0 :6766, :9358`); page and Core ship as one binary.
- why it matters: the fallback branch is dead (Core emits both media fields, `ApertarCoreApp.cpp:9554, :9556@cinemate-port`, and the `ui.*_steps` arrays always, `:1966-1969`); the wording invents a compatibility need.
- rework: `const hasMedia = !!(snapshot && snapshot.media_alive);` in both places; reword the comment to "the constants are the default lists".
- effort: S
- deliberate: no

### WCP-05-F9 [slop, nit] Ticket tokens (Q2, T33, T34, Request 24) in comments
- where: `src/web/WebControlPage.cpp:10123`, `:7568`, `:7576`, `:7636`, `:8483` @cinemate-port; 23 comment lines in the file
- port way: "// Opens on Stills in photo mode (filter only, Q2) ...", "// T33: ...", "// Request 24: ...".
- Apertar way: no precedent; upstream comments carry no ticket numbers.
- why it matters: the tokens mean nothing to the original developer.
- rework: drop the tokens, keep the sentences; one sweep over the file.
- effort: S
- deliberate: no
