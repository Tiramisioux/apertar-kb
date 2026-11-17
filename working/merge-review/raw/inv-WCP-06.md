# Inventory WCP-06 (WebControlPage.cpp new lines 11639-13823, JS: media browser / viewer)

Refs: port = `cinemate-port` 01f170c, upstream = `upstream-1.6.0` 35dbe67. Diff: `diffs/WCP.part06.diff` (4 hunks).
Note: the hint "mode ladder, sensor modes" does not apply to this slice. It holds the Playback JS (Clip Browser, Clip Viewer, sound) plus three small hunks.

## Commits that wrote the region (git blame, new lines 11639-13823)

| Commit | Lines | Subject | fork-log status |
| --- | --- | --- | --- |
| 35dbe67 (upstream) | 904 | unchanged context | n/a |
| bc12c0a | 397 | web: Clip Browser, touch UI's shape (T49) | fork-only, Pi only; tested 2026-10-29 headless Chrome against Core (fork-log.md:101) |
| 4629de2 | 766 | web: Clip Viewer, frame-number clock (T50, page part) | fork-only, Pi only; tested 2026-10-29 24 fps Clear HDR 16-bit, 9 fps lossless; "Patrik: works well" (fork-log.md:102) |
| fa19856 | 87 | core, web: sound in the Clip Viewer (T51), audio is the clock | fork-only, Pi only; Range/416 and Chrome playback tested; Safari, Firefox, phone NOT tested (fork-log.md:104) |
| a40112a | 15 | web: browser says Loading while list and thumbnails load | fork-only (fork-log.md:131), no test recorded |
| 4fa0432 | 5 | web: viewer asks for the frame due when the answer arrives (`pbvLookAhead`) | fork-only (fork-log.md:116), no test recorded |
| e25fd2b | 10 | web: camera-set values green, ISO list follows iso_max, ISO lock (snapshot merge hunk) | fork-only, tested 2026-10-28 (fork-log.md:72) |
| d44b177 | 27 | drop-frames: Log, RAM write buffer, storage pre-roll (snapshot merge hunk) | fork-only, Pi only (fork-log.md:138) |
| 392e812 | 1 | locked control red warning (stray line in region) | fork-only |

## Hunks

| Hunk | New lines | What |
| --- | --- | --- |
| 1 | 11639-13005 (+1366/-317) | upstream media list overlay JS replaced by Playback (browser + viewer) |
| 2 | 13753 | `installPreviewStream` error handler: ignore error while paused for playback |
| 3 | 13792-13821 | `mergeSnapshot` style block: 5 fields for e25fd2b |
| 4 | 13823-13870 | same function: 15 fields for d44b177 |

## Features (operator view)

| Feature | Commits | What the operator gets |
| --- | --- | --- |
| Clip Browser in WebUI | bc12c0a, a40112a | Grid of cards with thumbnails from Core's decoder, filter Clips/Stills/Timelapse/Audio, newest/oldest chip, long press (800 ms) selects, Remove Selected dialog, Download Selected zip, status line with Loading, DROP N pill, TC, name cut in the middle, phone Back closes it, Escape ladder |
| Clip Viewer in WebUI | 4629de2, 4fa0432 | Canvas player: play/pause, scrub that resumes after seek, frame step with hold-to-repeat, prev/next clip, histogram from `X-Histogram`, recorded timecode, honest FPS badge, black frame for dropped number, Info panel (13 rows), Remove, Download with confirm, hold card (Live view, Wake), keys Space/Left/Right, pause on hidden tab, `user_activity` ping while playing |
| Sound in viewer | fa19856 | `<audio>` plays the take's WAV and is the clock; falls back to wall clock with toast; ramp take plays silent |
| Live view pauses while browser open | bc12c0a | MJPEG `src` removed while Playback is open, restored on close |
| Folder button greyed in a take | bc12c0a | `pbSnapshotChanged` disables `#mediaBrowserButton` while `recording` or `timelapse_active` |
| Snapshot fields (e25fd2b) | e25fd2b | accepts `iso_actual`, `iso_max`, `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr`, `wb_actual_kelvin` |
| Snapshot fields (d44b177) | d44b177 | accepts `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied`, `buffer_setting`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_mode`, `storage_preroll_active/_auto/_auto_env/_fps/_last`, `buffer_note` |

## Interfaces touched by this slice

| Kind | Item | New or changed | Where |
| --- | --- | --- | --- |
| HTTP route (called) | `GET /api/media` (payload now carries `held`, `shot_ms`, `first_number`, `token`, `playable`, `format`, `ramp`, `missing_frames`, `empty_frames`, `timecode_start`, `shot_date_text`, `format_label`) | changed use | WCP:11990 @cinemate-port; route at ApertarCoreApp.cpp:8435 |
| HTTP route (called) | `GET /api/media/frame?kind=folder&id&n&w&v` (headers `X-Frame-Number`, `X-Frame-Index`, `X-Histogram`; 409 hold, 503 busy, 404 gone/stale) | new | ApertarCoreApp.cpp:8475; none upstream |
| HTTP route (called) | `GET /api/media/clip?kind=folder&id` (JSON: tl, holes, meta, extra, audio_url, ramp, info_line, fps_badge) | new | ApertarCoreApp.cpp:8442; none upstream |
| HTTP route (called) | `GET /api/media/file?kind=folder&id&name=<clip>.wav` (Range) | new | ApertarCoreApp.cpp:8550; none upstream |
| HTTP route (called) | `POST /api/media/delete-selected`, `GET /api/media/download-selected` | same routes, new callers (`pbRemoveSelected`, `pbDownloadSelected`) | upstream ApertarCoreApp.cpp:7575, 7318 |
| HTTP route (dropped use) | `item.download_url` -> `/api/media/download` still used by viewer Download | kept | WCP `pbvDownloadCurrent` |
| Socket command (sent via `/api/command`) | `user_activity` every min(20 s, standby_timeout/3) while playing | existing command, new raw `fetch` | WCP:12480 area; ApertarCoreApp.cpp:12620 |
| Socket command | `wake` via `sendCommand` from hold card | existing | `pbvWakeButton` |
| State field read | snapshot `playback_hold`, `recording`, `timelapse_active`, `standby_timeout_seconds`, `ui.photo_mode_enabled` | new reader of `playback_hold` | ApertarCoreApp.cpp:9557 |
| JS state | `state.pb` (payload, items, filter, sort, selecting, selection Set, lastOpenedId, thumbs Map, queue, inFlight, observer, fetching, queued, hold, snapshotHold, error, removing, pushed, page, viewer, viewerPushed, ignorePop, removeTargets), `state.previewPausedForPlayback` | new, replaces `state.mediaLibrary`, `mediaLibraryPayload`, `mediaSelection`, `mediaBrowserFilter`, `mediaBrowserSort` | WCP:6723 |
| UI elements (IDs in JS) | `pbGrid`, `pbTitle`, `pbShowValue`, `pbShowMenu`, `pbShowButton`, `pbSection`, `pbBackLabel`, `pbSortButton`, `pbCount`, `pbStatus`, `pbSelectionActions`, `pbRemoveButton`, `pbDownloadButton`, `pbRemoveScrim` (+Title/Count/Name/More/Confirm/Cancel), `pbBrowserPage`, `pbViewerPage`, `pbvStage`, `pbvCanvas`, `pbvHist`, `pbvFill`, `pbvHandle`, `pbvScrub`, `pbvTime`, `pbvTc`, `pbvFrame`, `pbvState`, `pbvPlay`, `pbvPlayIcon`, `pbvPrev`, `pbvNext`, `pbvStepBack`, `pbvStepFwd`, `pbvRemove`, `pbvDownload`, `pbvInfoButton`, `pbvMeta`, `pbvMetaGrid`, `pbvMetaClose`, `pbvHold` (+Title/Body), `pbvLiveButton`, `pbvWakeButton`, `pbvHole`, `pbvDrop`, `pbvFps`, `pbvName`, `pbvInfo`, `pbvAudio`; classes `.pb-card`, `.pb-thumb`, `.pb-nopreview`, `.pb-badge`, `.pb-pill`, `.pb-foot`, `.pbv-meta-row`; `.toast.with-link` reset in `showToast` | new | HTML at WCP:6345 onward (other slice) |
| Icons | `/icons/pause.png`, `/icons/play.png` | already in origin/main (`src/web/icons/`) | |
| Browser history | `history.pushState({pb:1})` browser, `{pb:2}` viewer; `popstate` handler | new | WCP:10130, 12776, 20634 |
| Config key, env var, file on disk | none in this slice | | |
| Events | none | | |

## ORIGINAL code modified

| Region | Where | Kind | Detail |
| --- | --- | --- | --- |
| Media list overlay JS (`renderMediaLibrary` and 14 helpers) | upstream WCP 7100-7700 region, port WCP:11639-12005 | rewritten (removed and replaced) | Row list with per-row Download link and per-row Delete replaced by card grid; behaviour changed: upstream rows toggled selection on click, port opens viewer on click and selects on long press |
| `mediaSelectionKey`, `mediaSelectionQuery`, `mediaItemCategory` | WCP:11675, 11682, 11655 | extended in place / kept (moved) | same bodies, renamed consumers `state.pb.selection` |
| `fetchMediaLibrary` | upstream WCP:10361 -> port WCP:11990 | rewritten, same name | writes `state.pb.payload`, queues a second fetch while one runs, sets `state.pb.hold` from `payload.held` |
| `downloadSelectedMediaItems` | upstream WCP:10404 | rewritten, renamed `pbDownloadSelected` | same URL; drops "Select media to download" toast and empty-query check |
| `deleteSelectedMediaItems` | upstream WCP:10426 | rewritten, renamed `pbRemoveSelected` | `window.confirm` replaced by custom dialog `pbRemoveScrim`; also reached from viewer |
| `setMediaBrowserOpen` | upstream WCP:6139 -> port WCP:10115 | extended in place + behaviour changed | adds history push/pop, `pbPauseLive`/`pbResumeLive`, filter reset (Stills in photo mode), `fromHistory` arg; overlay id `mediaBrowserOverlay` -> `playbackOverlay`, body class `media-browser-open` -> `pb-open` |
| `showToast` | WCP:12994 | extended in place | adds `toast.classList.remove("with-link")` |
| `installPreviewStream` error handler | WCP:13763 | extended in place | early return when `previewPausedForPlayback` |
| snapshot merge (`mergeSnapshot`-like) | WCP:13802-13860 | extended in place (2 commits, 20 `if` pairs) | flat copy-field-by-field pattern, same as upstream style |

## Removed or narrowed (upstream had, port lacks)

| What | Upstream | Effect |
| --- | --- | --- |
| Per-row Download link for single item | upstream media row, `download_url` anchor | Single download only from viewer, behind `window.confirm` (size warning). Browser has zip download of selection only |
| Per-row Delete button (with `window.confirm`) | `deleteMediaLibraryItem` (WCP upstream ~10361-10400) | gone; selection mode or viewer Remove instead |
| Clear selection button, "N items selected" line, Select All kept (`pbSelectAllButton` in HTML) | `clearMediaSelection`, `updateMediaSelectionControls` | Cancel ends selection |
| Filter buttons `.media-filter-button` and `<select id=mediaBrowserSortSelect>` | `setMediaBrowserFilter`, `setMediaBrowserSort` | replaced by SHOW menu and sort chip |
| Row stats (frame count, FPS, size, "Updated ...") | `mediaFrameCountLabel`, `mediaFpsLabel` | card shows duration, format, date, TC; size and fps only in viewer meta |
| Sort key `modified_ms` | `sortedMediaItems` | now `shot_ms` first, `modified_ms` fallback, natural name order |
| Empty text "No media mounted. Mount a drive..." | | now `<root> is not available.` |
| Live view while browser open | upstream kept MJPEG running | stopped (`previewPausedForPlayback`) |
| Browser button during take | upstream enabled | disabled while recording or timelapse |
| Non-cDNG clip playback | | viewer says "Playback of X arrives later." (ProRes, H.264, MLV, stills, audio, timelapse not playable) |

## New abstractions

| Name | Purpose | Upstream equivalent |
| --- | --- | --- |
| `state.pb` sub-object | all Playback state in one nested object | upstream flat `state.mediaBrowserOpen`, `state.mediaSelection` etc. in `state` (WCP:4233); no nested state objects found for media. Other nested JS objects exist in port (`bootConfig`, in other slices) |
| `pb*` / `pbv*` function families (about 60 functions, about 1300 lines) | browser and viewer logic in the page's global scope | none; upstream media code is about 350 lines in flat functions |
| Thumbnail loader: 2 in-flight, `IntersectionObserver`, blob URL cache in `state.pb.thumbs` | lazy thumbnails | none (upstream rows had no pictures) |
| Frame-number clock: `pbvTimeline`, `pbvMergeHoles`, `pbvInHole`, `pbvNumberAtTime`, `pbvLookAhead`, `pbvLaneWait`, two request "lanes", `ready` queue, `requestAnimationFrame` loop | player scheduling | none; comments say rules come from the sketch's `playclock.js` (node-tested, 16 checks), a file outside this repo |
| Audio-as-clock (`pbvAudioTime`, `pbvAudioFailed`) | A/V sync | none |
| `history.pushState` two-level back stack | phone Back | none found in upstream media code (grep `pushState` upstream to confirm: unconfirmed) |

## Board assumptions

| Assumption | Where |
| --- | --- |
| Frames decoded by Core per request; look-ahead capped at 0.35 s, 2 requests in flight (tuned for Pi 5 decode speed, Clear HDR 16-bit and 9 fps lossless tests) | WCP `pbvLookAhead`, `pbvNewState` lanes |
| Media root default `/media/RAW` | WCP `pbStatusText` |
| Only `format === "cdng"` playable | WCP `pbThumbUrl`, `pbvOpen` |
| No Pi 5 only API, no GPIO, I2C, fan, RAM figure in this slice | confirmed by reading |
| `drop-frames` buffer fields (`buffer_*`, `storage_preroll_*`) assume the RAM write-buffer feature | snapshot hunk, d44b177 |

## Notes for later stages (not judgement)

| Observation | Evidence |
| --- | --- |
| Comments use internal tracker words: T49, T50, T51, O1, O4, O10, P2, R2, Q2, design section 2.6, CLM:559-568, "the sketch's playclock.js" | WCP:11639-13000 @cinemate-port (about 12 hits) |
| Same snapshot-field block mixes two unrelated features (e25fd2b ISO/WB, d44b177 buffer/Log) | WCP:13802, 13833 |
| Upstream `pushState`, `IntersectionObserver`, `createImageBitmap` use not checked | unconfirmed; `grep -n "pushState\|IntersectionObserver" /home/user/wt/core-upstream/src/web/WebControlPage.cpp` settles it |
| 4fa0432 and a40112a: no test recorded in fork-log | fork-log.md:116, 131 |
