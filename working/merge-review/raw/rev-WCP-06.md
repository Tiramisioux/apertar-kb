# Review WCP-06 (WebControlPage.cpp new lines 11639-13870: Playback JS, snapshot merge)

Refs: port `cinemate-port` 01f170c (`P` = `/home/user/Apertar-Core/src/web/WebControlPage.cpp`), upstream `upstream-1.6.0` 35dbe67 (`U` = `/home/user/wt/core-upstream/src/web/WebControlPage.cpp`), upstream touch UI `ui-upstream` 43888e5 (`QML` = `/home/user/wt/ui-upstream/qml`).
Input: `diffs/WCP.part06.diff` (read whole), `raw/inv-WCP-06.md`, `raw/conv-core-command-plane.md`, `raw/conv-core-camera.md`. No `apertar-conventions.md` yet; rule ids cited from C1 where they apply.
The hint "mode ladder, sensor modes" does not apply to this slice (inventory says the same).

## Key upstream facts used

| Fact | Evidence | Status |
| --- | --- | --- |
| Upstream touch UI already has a Clip Browser and Clip Player with the shape the port copies (CLIPS/STILLS/SELECTION header, Back/Cancel, `N selected` / `N items`, NO PREVIEW, Remove Selected Clips? dialog, `+N more`, `This action cannot be undone.`, PLAYING/PAUSED, `FRAME i / N`) | `QML/ClipBrowserPage.qml:340,418,468,545,679,878,929,1008`; `QML/ClipPlayerPage.qml:178,480,2128,2170,2250` @upstream-1.6.0 | confirmed |
| Upstream touch UI greys the clip browser button in a take | `QML/CameraPage.qml:3689-3697` `enabled: !root.recording` | confirmed |
| Upstream WebUI `state` is one flat object; media fields use a `media` prefix: `mediaBrowserOpen`, `mediaFetchInFlight`, `mediaLibrary`, `mediaLibraryPayload`, `mediaBrowserFilter`, `mediaBrowserSort`, `mediaSelection` | `U:4204-4265` | confirmed |
| Upstream WebUI function names are verb-first camelCase (`apply*` 26, `format*` 24, `set*` 15, `render*` 10) or full-noun prefix (`media*` 9, `sensor*` 7, `preview*` 5, `imu*` 5). No 2-3 letter abbreviation families | `grep -oE "^    (async )?function [a-z]+[A-Z]" U` | confirmed |
| Upstream WebUI confirms every destructive action with `window.confirm` (8 sites) | `U:10307,10385,10434,10672,11266,11278,11325,11337` | confirmed |
| Upstream sends `user_activity` with a raw `fetch("/api/command")`, not `sendCommand` | `U:11509-11513` | confirmed |
| Upstream timecode helpers `pad2`, `formatTimecode(totalFrames, fpsInt)` | `U:4635`, `U:4678`; kept in port `P:7117`, `P:7160` | confirmed |
| Upstream snapshot merge checks numbers with `isFiniteNumber(source.x)` (18 sites), never `typeof source.x === "number"` (0 sites) | `grep -c` on U | confirmed |
| Upstream WebUI has no `history.pushState`, `IntersectionObserver`, `createImageBitmap` | `grep -n` on U: 0 hits | confirmed |
| `/api/state` is nested JSON already upstream (`snapshot.ui`, `.system`, `.capture` ...); the flat rule binds the socket, not the HTTP JSON | `U:4273-4291` `ensureSnapshotShape` | confirmed |

## Findings

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | Upstream media state and function names replaced by `state.pb` / `pb*` / `pbv*` | mismatch | major | no |
| F2 | Remove dialog is a custom scrim; the WebUI way is `window.confirm` | mismatch | minor | yes (touch UI wording) |
| F3 | Tracker words and history narration in comments | slop | minor | n/a |
| F4 | Non-cDNG items lost size, fps, frame count in the WebUI; single Download only via viewer | removed-upstream-behaviour | minor | partly |
| F5 | Viewer keeps the previous clip's badges and Info rows when a non-cDNG item opens | bug | minor | no |
| F6 | Clip opened during a hold stays blank after the hold ends | bug | minor | no |
| F7 | WAV shorter than the frame span freezes playback at the end | bug | minor | no |
| F8 | Failed remove from the viewer closes the viewer | bug | nit | no |
| F9 | `pbvTimecodeAt` / `pbvClock` re-implement `formatTimecode` / `pad2` | duplication | minor | no |
| F10 | Snapshot merge uses `typeof === "number"`; upstream uses `isFiniteNumber`; env knob field | mismatch | nit | no |
| F11 | Dead indirection and unused fields | slop | nit | no |
| F12 | `state.previewPausedForPlayback` not declared in `state` | mismatch | nit | no |
| F13 | Player pacing tuned on Pi 5 only | pi-compat | minor | yes |

### F1 Upstream media state and names replaced (mismatch, major)

Port: `P:6723-6727` `pb: { payload, items, filter, sort, selecting, selection, ..., viewer, viewerPushed, ignorePop, removeTargets }`; 70 functions named `pb*` / `pbv*` (`P:11653-12928`), among them renames of upstream functions with the same job:

| Upstream (U) | Port (P) |
| --- | --- |
| `state.mediaLibraryPayload` | `state.pb.payload` |
| `state.mediaLibrary` | `state.pb.items` |
| `state.mediaSelection` | `state.pb.selection` |
| `state.mediaBrowserFilter`, `mediaBrowserSort` | `state.pb.filter`, `state.pb.sort` |
| `state.mediaFetchInFlight` | `state.pb.fetching` (+ `queued`) |
| `renderMediaLibrary` | `pbRender` `P:11950` |
| `sortedMediaItems` | `pbSorted` `P:11690` |
| `selectedMediaItems` | `pbSelectedItems` `P:11704` |
| `toggleMediaSelection` | `pbToggle` `P:11801` |
| `setMediaBrowserFilter` | `pbSetFilter` `P:12125` |
| `pruneMediaSelection` | inlined in `pbRender` |
| `selectAllVisibleMedia` | inline listener `P:20627` |
| `downloadSelectedMediaItems` | `pbDownloadSelected` `P:12084` |
| `deleteSelectedMediaItems` | `pbRemoveSelected` `P:12050` |

Upstream: flat `state` `U:4233-4246`; names `U:7600-7700`, `U:10361-10460`. Kept names (`mediaSelectionKey`, `mediaSelectionQuery`, `mediaItemCategory`, `fetchMediaLibrary`, `setMediaBrowserOpen`) show the upstream names fit the new job.
Why it matters: the diff reads as a rewrite of the whole media feature (317 lines out, 1366 in) when a large part is the same job renamed. The original developer has to relearn his own feature. `pb` and `pbv` are abbreviations nothing else in the page uses.
Rework:
1. Browser state back to flat upstream fields: `mediaLibraryPayload`, `mediaLibrary`, `mediaSelection`, `mediaBrowserFilter`, `mediaBrowserSort`, `mediaFetchInFlight`; new ones flat with the same prefix: `mediaFetchQueued`, `mediaSelecting`, `mediaThumbCache`, `mediaThumbQueue`, `mediaThumbsInFlight`, `mediaThumbObserver`, `mediaHold`, `mediaSnapshotHold`, `mediaError`, `mediaRemoving`, `mediaHistoryPushed`, `mediaLastOpenedKey`, `mediaRemoveTargets`, `mediaBrowserPage`.
2. Viewer: one field `state.clipViewer` holding the per-clip object from `pbvNewState` is acceptable (it is reset per clip, like `previewProcessing*` is a group); rename `pbvNewState` -> `createClipViewerState`.
3. Restore upstream function names where the job is the same (table above). New ones verb-first: `buildMediaCard`, `queueMediaThumbnail`, `updateMediaStatusLine`, `openClipViewer`, `closeClipViewer`, `playClip`, `pauseClip`, `stepClipFrame`, `seekClip`, `fetchClipFrame`, `drawClipFrame`, `drawClipHistogram`, `applyClipHold`, `installClipViewerInteractions` ... and helpers of the clock as `clipTimeline`, `clipNumberAtTime`, `clipFrameInHole`.
Mechanical; no behaviour change. Effort M (one commit, about 600 identifiers). Risk: the HTML ids `pb*`/`pbv*` in another slice; rename them in the same commit or leave ids alone (ids are less visible).

### F2 Custom remove dialog (mismatch, minor)

Port: `pbOpenRemoveDialog` `P:12036-12048` fills `#pbRemoveScrim`; `pbRemoveSelected` `P:12050`; Escape ladder `P:12107`; the viewer's Download still uses `window.confirm` `P:12914`.
Upstream WebUI: `window.confirm("Delete " + label + "? This cannot be undone.")` `U:10434`, same at 7 other sites.
Upstream touch UI: the scrim dialog `QML/ClipBrowserPage.qml:878-1008`. The port copied the touch UI's look into the WebUI.
Why: two dialog styles in one page; extra HTML, CSS, focus and Escape code. The WebUI's own convention is the browser confirm.
Rework: `window.confirm((items.length === 1 ? "Remove " + name : "Remove " + n + " selected clips") + "? This cannot be undone.")` inside `deleteSelectedMediaItems`; delete `pbRemoveScrim` markup/CSS, `pbOpenRemoveDialog`, `state.pb.removeTargets`, the scrim branches in `pbEscape` and the keydown guard `P:12966`. Keep only if the owner wants the touch UI look in the WebUI; then document it as the one custom dialog. Effort S.

### F3 Tracker words and history narration (slop, minor)

`P:11649` "(T49)", `P:11651` "The Clip Viewer is T50.", `P:11689` "(CLM:559-568)", `P:12151` "(T50)", `P:12153` "(design §2.6)", `P:12154` "(R2)", `P:12155` "The rules are the sketch's playclock.js (node-tested, 16 checks). Sound is T51.", `P:12270` "(R2)", `P:12332` "O4:", `P:12440` "(design §2.6)", `P:12706` "O1:", `P:12817` "(P2)", also `P:10123` "(filter only, Q2)" in `setMediaBrowserOpen`.
Upstream WebUI comments: none carry tracker ids (`grep -nE "\bT[0-9]{2}\b" U` 0 hits in JS).
Why: meaningless to the original developer; `playclock.js` and its 16 checks are not in this repository, so the claim cannot be checked.
Rework: drop the ids and the history ("is T50", "Sound is T51"); keep the rule sentences. Either add the clock tests to `tools/` as a host test (port precedent exists in `tools/*_test.cpp`) or remove the reference. Effort S.

### F4 Item details and single download narrowed (removed-upstream-behaviour, minor)

Upstream row: frame count, `Duration`, fps text, `size_text`, "Updated ..." and a per-row Download link `download_url` (`U:7740-7790` region, diff lines 1229-1321).
Port card `pbBuildCard` `P:11816-11926`: duration pill, `format_label`, shot date, TC. Size, fps and frame count only in the viewer's Info panel, and that panel is filled only for cDNG (`pbvOpen` returns early for `format !== "cdng"`, `P:12792`). Single download: open the item in the viewer, then a `window.confirm` (`P:12909-12922`).
Effect: for ProRes, H.264, MLV, stills, audio the WebUI no longer shows size, fps or frame count anywhere.
Deliberate: the card copies the touch UI (`QML/ClipBrowserPage.qml`), which has no download (no network). The WebUI-only columns were dropped with it; the commit message does not mention it.
Rework: put `size_text` and `fps_text` in the card foot (one span each, upstream `media-stat` style), or fill the Info rows from the `/api/media` item for non-cDNG items (`meta` fallback from `item.size_text`, `item.fps_text`, `item.frame_count`). Download of one item is covered by Download Selected (zip); state that in the handoff. Effort S.

### F5 Stale viewer badges for non-cDNG (bug, minor)

`pbvOpen` `P:12766-12832`: for `item.format !== "cdng"` it returns after `setText("pbvInfo")`, `setText("pbvFrame","NO FRAMES")`. It does not clear `#pbvFps`, `#pbvDrop`, `#pbvTime`, `#pbvTc`, `#pbvMetaGrid`.
Failing input: open a cDNG clip with drops (DROP 3, 25.000 FPS), press Next onto a ProRes clip: the ProRes viewer shows DROP 3, 25.000 FPS, the old time, and the Info panel lists the cDNG clip's rows under the new name (`pbvMetaName` is updated, the grid is not). Confirmed by reading.
Fix: in `pbvOpen` before the format branch: `setText("pbvFps","")`, hide `#pbvDrop`, `setText("pbvTime","")`, `setText("pbvTc","")`, `pbvMetaGrid.replaceChildren()` (or fill from the list item, F4).

### F6 Clip opened in a hold stays blank (bug, minor)

`pbvOpen` `P:12800-12805`: on 409 from `/api/media/clip` it calls `pbvApplyHold` and returns with `v.clip = null`, `v.tl = null`. When the hold ends, `pbvApplyHold("")` `P:12879-12886` redraws only `if (wasHeld && v.tl)`; `pbvPlay` returns when `!v.tl` `P:12481`.
Failing input: browser open on a phone, operator starts a take on the touch UI, taps a card in the WebUI (cards stay clickable), take ends: hold card disappears, stage stays black, Play does nothing, until Back and reopen. Confirmed by reading.
Fix: in `pbvApplyHold("")`, `if (wasHeld && !v.tl) void pbvReload();`.

### F7 Playback freezes when the WAV ends before the frame span (bug, minor, probable)

`pbvTick` `P:12551-12560`: with sound on, `t` comes from the audio only while `!audio.ended`; otherwise `t = v.t`. The loop to frame one fires only at `t >= pbvDuration(tl)` (`(last-first+1)/fps`, `P:12189`). The WAV is served raw (`ApertarCoreApp.cpp:7387`, no trim or pad).
Failing input: a take whose WAV is more than 0.25 s shorter than the frame span (audio start/stop not frame-aligned): at the WAV end `audio.ended` is true, `t` stops below the duration, badge says PLAYING, the picture stands; `pbvPlay` again sets `currentTime` past the end and stalls again. The 5 s fallback does not fire (`audioLive` is already true). Probable; settle with a take whose WAV is shorter than its frames.
Fix: in the else branch, when `audio.ended`, fall back to the wall clock from `v.t` (`v.audioOn = false; v.clockBase = v.t; v.clockStart = now`) and re-enable audio on the loop.

### F8 Failed remove from the viewer closes it (bug, nit)

`pbRemoveSelected` `P:12072-12081`: after a failed POST, `next` is the same item, which is in `items`, so `pbvClose()` runs. Fix: return from the viewer branch when the request failed.

### F9 Timecode and clock formatting duplicated (duplication, minor)

`pbvTimecodeAt` `P:12228-12238` and `pbvClock` `P:12220-12226` define local `pad` lambdas and their own h:m:s:f arithmetic. Upstream has `pad2` `U:4635` and `formatTimecode(totalFrames, fpsInt)` `U:4678`, both still in the port (`P:7117`, `P:7160`).
Rework: `pbvTimecodeAt` = parse start to frames, add `number - tl.first`, `return formatTimecode(frames % (nominal * 86400), nominal)`; `pbvClock` uses `pad2`. Effort S.

### F10 Snapshot merge details (mismatch, nit)

Hunks 3 and 4 follow the upstream flat copy-field-by-field pattern (`P:13802-13860`), which conforms. Two details:
- `typeof source.cdng_log_bits === "number"` `P:13835`, `buffer_stop_percent` `P:13845`, `storage_preroll_fps` `P:13855`. Upstream checks numbers with `isFiniteNumber(source.x)` everywhere (`U:8645-8660` region, 18 sites, 0 `typeof === "number"`). Use `isFiniteNumber` and `Number(...)` as in the e25fd2b lines just above.
- `storage_preroll_auto_env` `P:13853` carries an environment-variable state to the page (Core `ApertarCoreApp.cpp:262` `storagepreroll::prerollAutomaticFromEnv()`). An experiment knob surfacing in the UI; judge with `raw/sweep-knobs.md`, not here.

### F11 Dead indirection and unused fields (slop, nit)

`pbOpenClip` `P:11812` only calls `pbvOpen` (left from the stage where a tap opened a new tab, commit bc12c0a message). `pbvEls().hist` unused (`pbvDrawHistogram` looks the canvas up itself). `pbvLookAhead(tl, rttMs)` and `pbvFillMeta(clip, tl)` ignore `tl`. `pbvTimeline().ramp`, `.count` partly unused. Remove.

### F12 `previewPausedForPlayback` not in `state` (nit)

Set at `P:12138`, `P:12146`, read `P:13763`; absent from the `state` literal `P:6670-6748`. Upstream declares every `state` field in the literal (`U:4204-4265`, `previewStreamStarted` etc.). Add `previewPausedForPlayback: false` next to `previewStreamStarted`.

### F13 Pacing tuned on Pi 5 (pi-compat, minor, unconfirmed)

`pbvLookAhead` caps 0.35 s, two lanes at 640 w (`P:12209`, `P:12247-12255`). Values were measured on a Pi 5 (commit 4fa0432: lossless decode 180 ms). On Pi 4 / CM4 the Core decode is slower; the page degrades to the honest "PLAYING · N FPS" badge rather than failing, so the shape is safe. Settle on a Pi 4. Pi-model stage.

## Verdicts on the inventory's abstractions

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `state.pb` sub-object | rework-to-upstream-pattern | Flat `media*` fields as upstream `U:4233-4246`; the per-clip viewer object may stay as one field (F1) |
| `pb*` / `pbv*` function families | rework-to-upstream-pattern | Upstream names for the same jobs, verb-first names for new ones (F1) |
| Thumbnail loader (2 in flight, IntersectionObserver, blob cache) | keep | Core decodes each thumbnail; native `loading="lazy"` cannot cap concurrency or stop in a hold. Small and commented. Blob URLs never revoked: fine for the list size (320 w) |
| Frame-number clock (timeline, holes, look-ahead, two lanes, ready queue, rAF) | keep | Needed because Core serves single decoded frames; drops drawn black follows Core's N3 intent (report, do not hide). Strip tracker words (F3); move the off-repo playclock tests in or drop the reference |
| Audio as clock | keep, fix F7 | Standard A/V approach; fallback to the wall clock exists |
| `history.pushState` two-level back stack | keep | No upstream precedent; small (`P:10129-10143`, `P:12776-12779`, `P:12866-12869`, popstate `P:20637`); gives the phone's Back the touch UI's Back. Document it |
| Custom remove scrim (`pbOpenRemoveDialog`) | simplify | `window.confirm` is the WebUI way (F2) |

## Removed or narrowed: judgement

| Item | Judgement |
| --- | --- |
| Per-row Delete with confirm | fine: selection Remove and viewer Remove, as the touch UI |
| Per-row Download | minor (F4): zip of one item still works |
| Row stats size/fps/frames | minor (F4) |
| Filter buttons and sort `<select>` | fine: SHOW menu and sort chip, touch UI shape |
| Row click toggles selection -> long press | fine: touch UI shape (`QML/ClipBrowserPage.qml:784`) |
| Live view stops while the browser is open | keep, deliberate (commit bc12c0a, comment `P:12135`); Core decodes for the page |
| Browser button greyed in a take | conforms to upstream touch UI `enabled: !root.recording` |
| Non-cDNG playback "arrives later" | new limitation of a new feature, not an upstream loss (upstream WebUI had no playback) |

## Protocol

No socket change in this slice. The page consumes new HTTP routes (`/api/media/frame`, `/api/media/clip`, `/api/media/file`) and new fields of `/api/media`; additive. An unmodified original UI is not affected. Nested JSON in `/api/media/clip` (`meta`, `extra`, `holes`, `ramp`) is judged in the App unit; HTTP JSON is nested upstream too (`/api/state`).

## Conforms

| What | Where |
| --- | --- |
| Browser and viewer copy the upstream touch UI's Clip Browser / Clip Player wording and layout (CLIPS/SELECTION, Back/Cancel, NO PREVIEW, Remove Selected Clips?, PLAYING/PAUSED, FRAME i / N) | `P:11653-11660`, `P:11950-11975` vs `QML/ClipBrowserPage.qml:340-545,679,878-1008`, `QML/ClipPlayerPage.qml:178,480` |
| Folder button greyed in a take, as the touch UI | `P:12021-12024` vs `QML/CameraPage.qml:3697` |
| Kept upstream helpers and flow: `setText`, `showToast`, `mediaSelectionKey`, `mediaSelectionQuery`, `mediaItemCategory`, `fetchMediaLibrary` (same name and silent arg), the same `/api/media/delete-selected` and `/api/media/download-selected` URLs, then `fetchMediaLibrary(true)` + `fetchState(true, {forceImmediate:true})` | `P:11663-11683`, `P:12050-12095` vs `U:10361-10460` |
| `user_activity` sent with a raw `fetch("/api/command")`, the upstream idiom | `P:12505` vs `U:11509-11513`; C1-S09 |
| `wake` through `sendCommand` | `P:12941` ; C1-S09 |
| Snapshot merge: one flat `if (typeof/isFiniteNumber) snapshot.x = source.x` line pair per field | `P:13802-13860` vs `U:8635-8680` |
| `installPreviewStream` change is a 2-line guard in place | `P:13763-13764` |
| Escape extends the upstream keydown chain in `installInteractions` instead of a second handler | `P:20919-20921` vs `U:11576-11580` |
| No GPIO, I2C, Pi-5-only API in this slice | read |

## Skeptic

Checked against `git show cinemate-port:src/web/WebControlPage.cpp` (P) and `git show upstream-1.6.0:src/web/WebControlPage.cpp` (U).

| Id | Verdict | Why |
| --- | --- | --- |
| WCP-06-F1 | corrected | Confirmed: `pb: {...}` at P:6723-6727, 70 `function pb*` at P:11685-12928; U state is flat `media*` (U:4233-4246) and no nested object sits in U's `state` literal. Added: the port keeps some upstream names (`fetchMediaLibrary`, `setMediaBrowserOpen`, `mediaSelectionKey`, `mediaSelectionQuery`, `state.mediaBrowserOpen` P:6714) and drops the rest, so one feature now uses two naming schemes. |
| WCP-06-F2 | stands | U uses `window.confirm` for every destructive action (U:10307, 10385, 10434, 10672, 11266, 11278, 11325, 11337); U has no scrim or modal at all; port viewer Download still uses `window.confirm` (P:12914). bc12c0a: "Remove Selected (dialog)". |
| WCP-06-F3 | corrected | Comments confirmed (P:10123, 11649, 11651, 11689, 12151-12155, 12270, 12332, 12440, 12706, 12817); U has 0 tracker ids. Correction: `playclock.js` and `playclock_test.js` exist, but in the KB (`apertar-kb/working/tools/playback/page/`), not in the code repo. |
| WCP-06-F4 | corrected | Card fields confirmed (P:11816-11926: duration, DROP, name, format_label, shot date, TC; no size, fps, frame count); U row had frame count, Duration, fps, size, "Updated", per-row Download and Delete (U:7735-7790). Correction: single Download from the viewer works for non-cDNG too (`pbvDownload` enabled on `download_url`, P:12784); per-row Delete is also gone (single remove only via viewer Remove). |
| WCP-06-F5 | stands | P:12784-12789: non-cDNG branch sets only `pbvInfo`, `pbvFrame`, note; `pbvFps`, `#pbvDrop`, `#pbvMetaGrid`, time/TC are written only on the cDNG path (P:12819-12826). |
| WCP-06-F6 | stands | 409 path returns before `v.tl` is set (P:12795-12798); `pbvApplyHold('')` redraws only `if (wasHeld && v.tl)` (P:12884); `pbvPlay` returns on `!v.tl` (P:12481); `pbSnapshotChanged` only calls `pbvApplyHold(hold)` (P:12030), no reload. |
| WCP-06-F7 | stands | `pbvTick` uses `t = v.t` once `audio.ended` (P:12553-12558); loop only at `t >= pbvDuration` (P:12562); no `ended` listener; the 5 s fallback is gated on `!v.audioLive`. WAV served raw (App P:7387, 8551). Probable. |
| WCP-06-F8 | stands | On failure the catch only toasts (P:12066-12068); `items.some(...)` is then true for the same clip and `pbvClose()` runs (P:12073-12080). |
| WCP-06-F9 | stands | `pad2` P:7117 and `formatTimecode` P:7160 present; `pbvClock`/`pbvTimecodeAt` define local `pad` (P:12220-12238). Rework keeps the 24 h wrap via `% (nominal*86400)` because `formatTimecode` does not wrap hours. |
| WCP-06-F10 | stands | P:13835, 13845, 13855 use `typeof === "number"`; U merge uses `isFiniteNumber` (U:8640-8676) and no `typeof source.x === "number"`. `storage_preroll_auto_env` P:13853 and read at P:15839. |
| WCP-06-F11 | stands | `pbOpenClip` is a one-line wrapper (P:11812-11814, one caller P:11915); `hist` from `pbvEls()` never destructured (callers P:12258, 12272, 12304); `tl` unused in `pbvLookAhead` (P:12209) and `pbvFillMeta` (P:12742). |
| WCP-06-F12 | stands | No `previewPausedForPlayback` in the literal; first assigned P:12138, read P:13763. |
| WCP-06-F13 | stands | `pbvFetchFrame(n, 640)` with two lanes and 0.35 s cap (P:12209-12212, 12599); 4fa0432 measured on Pi 5 only. Unconfirmed on Pi 4. |

## Final findings

### WCP-06-F1 [mismatch, major] Upstream media state and function names replaced by nested state.pb and pb*/pbv* families
- where: src/web/WebControlPage.cpp:6723-6727@cinemate-port ; src/web/WebControlPage.cpp:11653-12928@cinemate-port
- port way: All Playback state in a nested `state.pb` object (payload, items, filter, sort, selection, fetching, viewer ...); 70 functions with pb/pbv prefixes, many renames of upstream functions with the same job (renderMediaLibrary->pbRender, sortedMediaItems->pbSorted, selectedMediaItems->pbSelectedItems, toggleMediaSelection->pbToggle, setMediaBrowserFilter->pbSetFilter, downloadSelectedMediaItems->pbDownloadSelected, deleteSelectedMediaItems->pbRemoveSelected). At the same time some upstream names stay (fetchMediaLibrary, setMediaBrowserOpen, mediaSelectionKey, mediaSelectionQuery, state.mediaBrowserOpen P:6714), so the feature mixes two schemes.
- Apertar way: Flat state literal with media prefix, src/web/WebControlPage.cpp:4233-4246@upstream-1.6.0 (mediaBrowserOpen, mediaFetchInFlight, mediaLibrary, mediaLibraryPayload, mediaBrowserFilter, mediaBrowserSort, mediaSelection); no nested objects in `state`. Function names verb-first or full-noun prefix; no 2-3 letter prefix families. Media functions at src/web/WebControlPage.cpp:7511-7700, 10361-10460@upstream-1.6.0.
- why it matters: The diff reads as a rewrite of the whole media feature where much is the same job renamed; the original developer must relearn his own feature; pb/pbv is an abbreviation no other part of the page uses.
- rework: Restore upstream names for the same jobs (renderMediaLibrary, sortedMediaItems, selectedMediaItems, toggleMediaSelection, setMediaBrowserFilter, setMediaBrowserSort, downloadSelectedMediaItems, deleteSelectedMediaItems, pruneMediaSelection, selectAllVisibleMedia). Flatten browser state to state.mediaLibraryPayload/mediaLibrary/mediaSelection/mediaBrowserFilter/mediaBrowserSort/mediaFetchInFlight plus new flat media* fields (mediaFetchQueued, mediaSelecting, mediaThumbCache, mediaThumbQueue, mediaThumbsInFlight, mediaThumbObserver, mediaHold, mediaSnapshotHold, mediaError, mediaRemoving, mediaHistoryPushed, mediaLastOpenedKey, mediaBrowserPage). Keep the per-clip viewer object as one field state.clipViewer (createClipViewerState). Name new functions verb-first: buildMediaCard, queueMediaThumbnail, openClipViewer, closeClipViewer, playClip, pauseClip, stepClipFrame, seekClip, fetchClipFrame, drawClipFrame, applyClipHold, installClipViewerInteractions; clock helpers clipTimeline, clipNumberAtTime, clipFrameInHole. Mechanical, no behaviour change.
- effort: M
- deliberate: no. Commits bc12c0a/4629de2 describe features only; nothing on naming or departing from upstream state layout.

### WCP-06-F2 [mismatch, minor] Custom remove scrim dialog where the WebUI convention is window.confirm
- where: src/web/WebControlPage.cpp:12036-12048@cinemate-port ; src/web/WebControlPage.cpp:12107-12118@cinemate-port ; src/web/WebControlPage.cpp:12966@cinemate-port ; src/web/WebControlPage.cpp:6475@cinemate-port ; src/web/WebControlPage.cpp:2398-2409@cinemate-port
- port way: pbOpenRemoveDialog fills a custom #pbRemoveScrim (title, count, name, more, confirm/cancel, focus, Escape branch, keydown guard); the viewer's Download in the same feature uses window.confirm (P:12914).
- Apertar way: Every destructive action in the WebUI uses window.confirm: src/web/WebControlPage.cpp:10434@upstream-1.6.0 `if (!window.confirm("Delete " + label + "? This cannot be undone."))`, also 10307, 10385, 10672, 11266, 11278, 11325, 11337. Upstream WebUI has no scrim or modal. The scrim is the touch UI's dialog (Apertar-UI qml/ClipBrowserPage.qml@upstream-1.6.0).
- why it matters: Two dialog styles in one page; extra HTML, CSS, focus and Escape handling for one confirm.
- rework: In deleteSelectedMediaItems use window.confirm("Remove " + label + "? This cannot be undone."); delete #pbRemoveScrim markup/CSS, pbOpenRemoveDialog, state.pb.removeTargets, the scrim branch in pbEscape, the scrim lines at P:10137 and P:20634 and the scrim guard in the viewer keydown handler. Viewer Remove calls the same function with [item].
- effort: S
- deliberate: yes. bc12c0a: "Remove Selected (dialog)" in "the touch UI's shape".

### WCP-06-F3 [slop, minor] Tracker ids and history narration in Playback comments
- where: src/web/WebControlPage.cpp:10123, 11649, 11651, 11689, 12151-12155, 12270, 12332, 12440, 12706, 12817@cinemate-port
- port way: Comments carry T49, T50, T51, O1, O4, R2, P2, Q2, CLM:559-568, "design §2.6", "The Clip Viewer is T50", "Sound is T51", and "the sketch's playclock.js (node-tested, 16 checks)". playclock.js and playclock_test.js live only in the KB (apertar-kb/working/tools/playback/page/), not in Apertar-Core.
- Apertar way: Upstream WebUI JS comments carry no tracker ids (src/web/WebControlPage.cpp@upstream-1.6.0: 0 hits for T/R/O/P/Q-numbers outside "P3-D60").
- why it matters: Meaningless to the original developer; the test claim points outside the repository.
- rework: Delete ids and history phrases, keep the rule sentences. Either port the clock rules as a host test under tools/ (from the KB's playclock_test.js) or drop the playclock.js reference.
- effort: S
- deliberate: no

### WCP-06-F4 [removed-upstream-behaviour, minor] Clip cards lost size, fps, frame count and per-row Download/Delete; non-cDNG items show them nowhere
- where: src/web/WebControlPage.cpp:11816-11926@cinemate-port ; src/web/WebControlPage.cpp:12784-12789@cinemate-port ; src/web/WebControlPage.cpp:12909-12922@cinemate-port
- port way: Card shows duration, DROP, name, format label, shot date, TC. Size/fps/frames only in the viewer Info panel, filled only for cDNG (pbvOpen returns early for other formats). Single Download only from the viewer (works for every format, behind window.confirm); single delete only from the viewer's Remove.
- Apertar way: Upstream media row showed frame count, Duration, fps_text, size_text, "Updated ..." plus per-row Download and Delete, src/web/WebControlPage.cpp:7735-7790@upstream-1.6.0 (mediaFrameCountLabel :7571, mediaFpsLabel :7584). Core still sends size_text and fps_text (ApertarCoreApp.cpp:9276-9280@cinemate-port).
- why it matters: For ProRes, H.264, MLV, stills and audio the WebUI no longer shows size, fps or frame count anywhere.
- rework: Add size_text and fps_text spans (mediaFpsLabel) to the card foot, or fill the Info rows from the /api/media item for non-cDNG items (size_text, fps_text, frame_count). Note in the handoff that per-item actions moved into the viewer.
- effort: S
- deliberate: unknown. Card copies the touch UI; bc12c0a does not mention dropping the WebUI-only columns.

### WCP-06-F5 [bug, minor] Viewer keeps previous clip's FPS/DROP badges, time and Info rows when a non-cDNG item opens
- where: src/web/WebControlPage.cpp:12766-12797@cinemate-port
- port way: pbvOpen returns for format !== "cdng" after setting pbvInfo, pbvFrame and the note; pbvFps, #pbvDrop, pbvTime, pbvTc and #pbvMetaGrid keep the previous clip's content while pbvMetaName shows the new name.
- Apertar way: no precedent
- why it matters: Open a cDNG clip with drops, press Next onto a ProRes clip: DROP N, the cDNG fps badge and cDNG metadata rows appear under the ProRes name.
- rework: Before the format branch in pbvOpen: clear pbvFps/pbvTime/pbvTc, hide #pbvDrop, clear #pbvMetaGrid (or fill it from the list item, F4).
- effort: S
- deliberate: no

### WCP-06-F6 [bug, minor] Clip opened during a hold stays blank after the hold ends
- where: src/web/WebControlPage.cpp:12795-12798@cinemate-port ; src/web/WebControlPage.cpp:12875-12886@cinemate-port ; src/web/WebControlPage.cpp:12021-12033@cinemate-port
- port way: On 409 from /api/media/clip pbvOpen applies the hold and returns with v.tl null; pbvApplyHold("") redraws only if v.tl is set; pbvPlay returns when !v.tl; pbSnapshotChanged does not reload the viewer.
- Apertar way: no precedent
- why it matters: Browser open on a phone, a take starts from the touch UI, operator taps a card, take ends: hold card disappears, stage stays black, Play does nothing until Back and reopen.
- rework: In pbvApplyHold(""): `if (wasHeld && !v.tl) void pbvReload();`
- effort: S
- deliberate: no

### WCP-06-F7 [bug, minor] Playback freezes at the end when the WAV is shorter than the frame span (probable)
- where: src/web/WebControlPage.cpp:12545-12575@cinemate-port ; src/web/WebControlPage.cpp:12189@cinemate-port
- port way: With sound on, t comes from audio only while !audio.ended; otherwise t = v.t. The loop fires only at t >= (last-first+1)/fps. No `ended` listener. The WAV is served raw (ApertarCoreApp.cpp:7387, 8551@cinemate-port).
- Apertar way: no precedent
- why it matters: A take whose WAV ends before the frame span: at WAV end the picture stands, badge says PLAYING, the 5 s fallback does not fire (audioLive already true), Play again stalls again. Probable; settle with such a take.
- rework: In pbvTick's waiting branch, when audio.ended, switch to the wall clock from v.t (audioOn=false, clockBase=v.t, clockStart=now) and re-enable audio after the loop.
- effort: S
- deliberate: no

### WCP-06-F8 [bug, nit] Failed remove from the viewer closes the viewer
- where: src/web/WebControlPage.cpp:12050-12081@cinemate-port
- port way: After a failed POST the catch only toasts; the same item is at the index and in the removed list, so pbvClose() runs.
- Apertar way: no precedent
- why it matters: Remove from the viewer while Core refuses (busy): the error toast shows and the viewer closes although the clip still exists.
- rework: Track success; on failure leave the viewer open.
- effort: S
- deliberate: no

### WCP-06-F9 [duplication, minor] pbvTimecodeAt and pbvClock re-implement formatTimecode and pad2
- where: src/web/WebControlPage.cpp:12220-12238@cinemate-port
- port way: Local pad lambdas and own h:m:s:f arithmetic.
- Apertar way: pad2 src/web/WebControlPage.cpp:4635@upstream-1.6.0 and formatTimecode(totalFrames, fpsInt) :4678@upstream-1.6.0, both still in the port (P:7117, P:7160).
- why it matters: Two timecode formatters in one page drift apart.
- rework: pbvTimecodeAt: parse start to frames, add number - tl.first, return formatTimecode(frames % (nominal*86400), nominal) (keeps the 24 h wrap). pbvClock: use pad2.
- effort: S
- deliberate: no

### WCP-06-F10 [mismatch, nit] Snapshot merge uses typeof === "number" instead of isFiniteNumber; env-knob field reaches the page
- where: src/web/WebControlPage.cpp:13835@cinemate-port ; src/web/WebControlPage.cpp:13845@cinemate-port ; src/web/WebControlPage.cpp:13853-13856@cinemate-port
- port way: `if (typeof source.cdng_log_bits === "number") snapshot.cdng_log_bits = source.cdng_log_bits;` (also buffer_stop_percent, storage_preroll_fps); storage_preroll_auto_env copied to the snapshot (read at P:15839).
- Apertar way: Upstream merge checks numbers with `if (isFiniteNumber(source.x)) snapshot.x = Number(source.x);`, src/web/WebControlPage.cpp:8640-8676@upstream-1.6.0; no `typeof source.x === "number"` anywhere.
- why it matters: Small inconsistency inside one function; the env flag exposes an experiment knob (see sweep-knobs).
- rework: Use isFiniteNumber + Number() for the three numeric fields. Decide storage_preroll_auto_env with the knob sweep.
- effort: S
- deliberate: no

### WCP-06-F11 [slop, nit] Dead indirection and unused parameters
- where: src/web/WebControlPage.cpp:11812@cinemate-port ; src/web/WebControlPage.cpp:12209@cinemate-port ; src/web/WebControlPage.cpp:12240@cinemate-port ; src/web/WebControlPage.cpp:12742@cinemate-port
- port way: pbOpenClip only calls pbvOpen (left from the new-tab stage); pbvEls().hist never used; tl unused in pbvLookAhead and pbvFillMeta.
- Apertar way: no precedent
- why it matters: Noise for a reader.
- rework: Remove pbOpenClip (call the viewer open directly), drop hist from pbvEls and the unused tl parameters.
- effort: S
- deliberate: no

### WCP-06-F12 [mismatch, nit] state.previewPausedForPlayback not declared in the state literal
- where: src/web/WebControlPage.cpp:12138@cinemate-port ; src/web/WebControlPage.cpp:13763@cinemate-port
- port way: Field created on first assignment in pbPauseLive.
- Apertar way: Every state field is declared in the literal, e.g. previewStreamStarted: false, src/web/WebControlPage.cpp:4227@upstream-1.6.0.
- why it matters: Reader cannot see the field in the state list.
- rework: Add previewPausedForPlayback: false next to previewStreamStarted (P:6708).
- effort: S
- deliberate: no

### WCP-06-F13 [pi-compat, minor] Player pacing (0.35 s look-ahead, two lanes at 640 w) measured on Pi 5 only
- where: src/web/WebControlPage.cpp:12209-12218@cinemate-port ; src/web/WebControlPage.cpp:12247-12255@cinemate-port ; src/web/WebControlPage.cpp:12599@cinemate-port
- port way: Constants tuned against Pi 5 decode times (4fa0432: 180 ms lossless).
- Apertar way: no precedent
- why it matters: On Pi 4/CM4 Core decodes slower; the page degrades to "PLAYING · N FPS" rather than failing. Unconfirmed; settle on a Pi 4.
- rework: None now; record measured behaviour on Pi 4 in the Pi-model stage.
- effort: S
- deliberate: yes. 4fa0432 message gives the measurements.
