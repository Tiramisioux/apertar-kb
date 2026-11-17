# Inventory: Playback (stage 1, no judging)

Refs: port = `cinemate-port` Core `01f170c` / UI `7ea9afc`; upstream = `upstream-1.6.0`; main = fork `origin/main`.
Status column quotes `fork-log.md` lines 99-104, 148-152, 186, 205. All playback work is "fork-only, Pi only; not offered upstream".

## 1. Commits

| Commit | Subject | Recorded test |
| --- | --- | --- |
| f91fafa, ab4cc92 | T47 Core knows its clips: hold rule, yield window, facts cache, /api/media/clip | Pi 2026-10-29, list 4.2 s then 20 ms; host tests 41 + 22 checks |
| 1af26c8 | T48 /api/media/frame, liblj92 vendored, decode slots, JPEG caches, CMake C | Pi 2026-10-29, 64-271 ms/frame, 0.8 ms cached |
| bc12c0a, 27eac5a | T49 WebUI Clip Browser (WCP, outside this scope) | headless Chrome vs Core |
| 4629de2 | T50 WebUI Clip Viewer page part (WCP) | Pi, Patrik "works well" |
| a37a902 | T50 Core part: downloads 409 in hold and stop in 64 KB chunk; deletes wait for writes, `mediaDeleteActive_` | download stop 0.3 s; Q23 not tested live |
| fa19856 | T51 /api/media/file WAV with Range | Chrome only; Safari/Firefox/phone not tested |
| 618b2f1 | playback opens DNG up to 5472x3648 (merged by 4b2eeac) | `tools/dng_limits_test.cpp` on host; Pi not recorded |
| d7dd337 | frames_per_folder: `listFrames`, facts cache read `part_NNN` (playback part of a drop-frames/cdng commit) | host; camera runs it since boot 13:00 per fork-log 181 |
| 7ea9afc (UI) | clip browser, player, prefetch read split clips; `ClipFrameFiles.hpp` | not recorded as run on the camera UI |

## 2. Features seen by the operator

| Feature | Where | Commits |
| --- | --- | --- |
| Clip list shows each cDNG take's own fps, span duration, holes, timecode, shot date, format, dropped | `/api/media` items, WebUI cards | f91fafa ab4cc92 |
| Clip info (nine meta rows + SOUND, FORMAT, DROPPED) | `GET /api/media/clip` | f91fafa |
| Any frame of a take as JPEG with histogram, in the touch UI's raw look | `GET /api/media/frame` | 1af26c8 |
| Sound of a take streamed with Range | `GET /api/media/file` | fa19856 |
| Playback stops when a take, photo, timelapse, media test, standby, eject, format starts | yield window + hold rule | f91fafa |
| Folder button greyed in a take; downloads/deletes refuse (409) in a hold | WCP `pbSnapshotChanged`, download routes | bc12c0a a37a902 |
| "Deleting media. One moment." blocks record/photo/timelapse during a delete | handleCommand | a37a902 |
| Clip browser/player in the touch UI sees split clips | UI `ClipFrameFiles.hpp` | 7ea9afc |
| Playback opens every frame size Core writes (IMX283 5472x3648) | `DngTags.hpp` caps | 618b2f1 |

## 3. Interfaces added or changed

| Kind | Name | Detail | File:line @port |
| --- | --- | --- | --- |
| HTTP | `GET /api/media/clip?kind=folder&id=` | 200 facts JSON, 404, 409 "Playback held" (when no cached facts) | App:8442 |
| HTTP | `GET /api/media/frame?kind=folder&id=&n=&w=&v=` | w in 320/480/640/960/1280/1920; 200 image/jpeg; 400, 404, 409 (+`hold`), 503 `{"busy":true}`; headers X-Frame-Number, X-Frame-Index, X-Frame-Count, X-Histogram, X-Frame-Source, X-Decode-Ms | App:8475 |
| HTTP | `GET /api/media/file?kind=folder&id=&name=<x>.wav` | 200/206/416, Accept-Ranges, 409 in hold, 64 KiB pread chunks | App:8550 |
| HTTP | `GET /api/media` | CHANGED: item gains `playable`, `play_reason`, `format`, `fps`, `fps_fallback`, `first_number`, `last_number`, `missing_frames`, `empty_frames`, `ramp`, `token`, `timecode_start`, `has_audio`, `shot_*`; reply gains `held` | App:9250, 9275+ |
| HTTP | `GET /api/media/download`, `/download-selected` | CHANGED: 409 in hold; stream stops in 64 KB chunk on yield window; zip child SIGTERM | App:8682, 8811 |
| HTTP | `POST /api/media/delete`, `/delete-selected` | CHANGED: wait for pending writes (409), set `mediaDeleteActive_` | App:9004, 9087 |
| HTTP | reason phrases 206, 409, 416 | `WebServer.cpp` +3 lines | WebServer.cpp:61-70 |
| State field | `playback_hold` in `/api/state` (and socket state builder `buildWebStateJson`) | "", recording, writing, media_test, standby, media | App:9557 |
| Socket cmd | none added | `handleCommand` top opens the yield window for 7 command names | App:12576 |
| Event | none | WebUI polls `playback_hold` | WCP:12025 |
| Config key | none | | |
| Env var | `APERTAR_PLAYBACK_WORKERS` (default 2, clamp 1-4) | decode slots | PlaybackFrames.cpp:82 |
| Files on disk | none written; reads `<clip>.wav`, `<clip>_stretched.wav`, `fps-ramp.txt`, `audio_capture.raw` (existence), `part_NNN/` | | ClipProbe.hpp:130, App:7390 |
| Build | `LANGUAGES C CXX`; `src/playback/PlaybackFrames.cpp`, `third_party/liblj92/lj92.c`, include dir `third_party/liblj92` | | CMakeLists.txt:6,77-78,106 |
| Tests | `tools/dng_limits_test.cpp` (plain g++, not in CMake) | 98 lines; also KB `working/tools/playback/frames_test.cpp` (outside repo) | |
| UI element (Core WebUI) | `#playbackOverlay`, Clip Browser, Clip Viewer, `<audio>` clock | WCP:6345, 11651, 12152 | outside this unit's file list |
| UI element (touch UI) | none new; three files read split clips | | |

## 4. ORIGINAL code modified

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| `discoverMediaLibraryItems(root, fps)` | App:7437 (upstream App ~6160) | new `held` arg; cDNG folders answered from `clipFactsCache()` before the recursive scan; scan only if no facts; in a hold lists only cached folders | extended in place (scan kept as fallback) |
| `MediaLibraryItem` struct | App:6362 | +~14 fields (playable, fps, numbers, token...) | extended in place |
| `buildMediaLibraryJson` | App:9250 | asks `playbackHoldReason()`, passes `held`, emits new fields and `held` | extended in place |
| `/api/media/download`, `-selected` | App:8682, 8811 | 409 gate + chunked stop | behaviour-changed |
| `/api/media/delete`, `-selected` | App:9004, 9087 | write wait, `mediaDeleteActive_` | behaviour-changed |
| `handleCommand` top | App:12565-12585 | yield window opened before any camera call | extended in place |
| `buildWebStateJson` | App:9363-9372, 9557 | holdSignals from values already read; `playback_hold` | extended in place |
| media watcher loop | App:10905-10980 | yield on media loss; renews window 1.5 s per cycle in a hold; calls `trimIdleFrameSlots` | extended in place |
| storage pre-roll start | App:11264 | `yieldFor(Recording)` before `waitForMediaTrim` | extended in place |
| `WebServer.cpp` reasonPhrase | :61-70 | +206, 409, 416 | extended in place |
| CMake | CMakeLists.txt | `LANGUAGES C CXX` | extended in place |
| UI `neighboringFramePaths`, `resolvePrefetchClip` | cdngimageprovider.cpp:766-806 | dir listing + QCollator sort replaced by `clipframes::dngFramesOfClip`; index by path relative to clip dir | rewritten |
| UI `ClipListModel::scanClips` | cliplistmodel.cpp:502, 525 | listing replaced; sort removed (helper sorts) | rewritten |
| UI `PlaybackController::reloadFrameList` | playbackcontroller.cpp:696 | same | rewritten |
| CameraController, CdngEncoder, writers | | not touched by playback commits (fork-log: "No change in CameraController or any writer") | unchanged |

## 5. New abstractions

| Name | Files | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| namespace `apertar::playback`, 9 header-only modules + 1 .cpp (1629 lines) | `src/playback/` | Core-side DNG decode and render | none in Core; touch UI owns it: `ui-upstream/src/dngdecoder.cpp`, `cdngimageprovider.cpp`, `playbackcontroller.cpp` (Qt, libtiff) | App routes |
| `PlaybackYield` (atomic window), `HoldSignals`, `playbackHoldFor`, `Hold` enum | PlaybackHold.hpp | one hold rule, lock-free stop signal for a decode in flight | none; upstream gates by per-command checks under `commandMutex_` | handleCommand, watcher, 6 routes, state |
| `FrameList`, `listFrames` | ClipFrames.hpp | frame numbers, holes, time->frame map | UI `dngNameFilters()` + QCollator sort (`playbackcontroller.cpp:696`, `cliplistmodel.cpp:502`) | probe, frame route |
| `DngInfo`, `readDngInfo`, size caps | DngTags.hpp | Qt-free tag reader (tail pread) | `dngdecoder.cpp` via libtiff (`tiffio.h`) | probe, reader |
| `readDngSamples`, `ReadOptions` | DngFrameReader.hpp | chunked read, lossless tiles via lj92, stop callback, fadvise | `dngdecoder.cpp` | PlaybackFrames |
| `renderPreview`, `rawHistogram` | RawRender.hpp | Qt-free copy of touch UI look; named copy: "change one, change the other" | `cdngimageprovider.cpp:380-698` | PlaybackFrames |
| `DecodeSlots` + `Lease` | DecodeSlots.hpp | buffers owned by slot, try_lock, 503 when busy, trim idle | none (UI decodes in Qt thread pool) | PlaybackFrames |
| `JpegCache` (two LRU, 8 + 24 MB) | PlaybackFrames.cpp | frame cache | none in Core; UI has own prefetch cache in `cdngimageprovider.cpp` | frameJpeg |
| `ClipFacts`, `probeClip`, `ClipFactsCache` | ClipProbe.hpp | per-clip facts keyed on folder mtime (one stat) | none; upstream list does `mediaStatsForPath` scan per request | list, clip route |
| text helpers `durationCardText`, `sizeText`, `shotDate`, `timecodeText`, `clipToken` | ClipProbe.hpp | copies of touch UI card text (CLM:147-169) | `cliplistmodel.cpp` | ClipProbe |
| `encodeRgbJpeg` | PlaybackFrames.cpp | turbojpeg or libjpeg RGB->JPEG, `thread_local tjhandle` | upstream already uses turbojpeg (`App:4157` preview encode, `CameraController.cpp:63`) | frameJpeg |
| `niceThread` | PlaybackFrames.cpp | `setpriority(+10)` on the HTTP client thread, via `SYS_gettid` | none | frameJpeg |
| `parseSingleByteRange`, `wavFormatForFile`, `wavSoundText` | App:7246+ | Range parser, RIFF parse | none | /api/media/file |
| file-scope statics `playbackYield()`, `clipFactsCache()`, `playbackNowMs()` | App:6335-6360 | process-wide singletons in the App .cpp ("header does not pull in readers") | upstream App has file-scope helpers and `static` singletons too (probe: unconfirmed, grep `static ` in upstream App) | App |
| `ApertarCoreApp::playbackHoldReason(bool)` | App.hpp:125, App:11341 | hold rule from live camera values | none | routes, watcher |
| `third_party/liblj92/` (lj92.c/h, LICENSE, README.apertar.md) | Core | lossless JPEG decoder | `ui-upstream/third_party/liblj92/` (same lj92.c/h, diff empty). Core upstream has no `third_party/` and decodes nothing | CMake |
| `apertar::clipframes` (UI) | UI `ClipFrameFiles.hpp` 66 lines | flat/split/partly-merged frame listing | the three inline `entryList` blocks it replaced | 3 UI files |
| worker threads | none new | decode runs on the web server's per-connection detached thread; slot trim on the existing media watcher | | |
| helper scripts | none | | | |

## 6. Removed, narrowed, hidden vs upstream

| What | Effect |
| --- | --- |
| Touch UI frame-list code (QCollator sort) replaced by the helper | same order for flat clips, now also reads parts; sorting is by file name only, ignoring the part dir |
| `/api/media` for cDNG takes no longer runs `mediaStatsForPath`; size, count, fps, duration come from the facts cache | list values differ from upstream: fps is the clip's own tag (upstream: current camera fps), duration is the span |
| In a hold, the list shows only cached folders; uncached ones vanish | list can be incomplete while recording |
| Media list scan skipped for cDNG folders | folder with 0 valid frames yields facts not ok -> falls back to the scan |
| Downloads and deletes now refuse (409) during a hold (recording, writing, media test, standby, media) | upstream allowed download while recording; standby also blocks |
| `record_start`/`capture_photo`/`timelapse_start` refused while a WebUI delete runs | new refusal |
| Frame width fixed to 6 values; unknown `w` is 400 | |
| Touch UI behaviour: unchanged for flat clips | |

## 7. Board assumptions

| Assumption | Where |
| --- | --- |
| Decode slot RAM ~46 MiB/slot, 92 MiB with 2 slots, 184 MiB with 4 (sized to 5472x3648); static_assert 40 MiB samples | DecodeSlots.hpp:20-24, DngTags.hpp:33-38 |
| Default 2 workers, max 4 (four cores) | PlaybackFrames.cpp:82 |
| Frame size cap = IMX283 5472x3648; other sensors listed by name (IMX477, IMX294, IMX585) | DngTags.hpp:25-31 |
| Linux only: `SYS_gettid`, `setpriority`, `posix_fadvise` | PlaybackFrames.cpp:17, DngTags.hpp:81 |
| Tuned on exFAT card ("105,000 entries readdir 3.7 s"), mtime moves with newest entry (CONFIRMED on three takes, 2026-10-29) | ClipProbe.hpp:7-12, 173 |
| Timings (40.4 vs 24.5 ms, 64-271 ms/frame) measured on a Pi, x86 host for the 40.4 figure ("on this host") | DecodeSlots.hpp:9-12 |
| `mediaGateBypassed()` and media snapshot semantics (fork main) | App:9371, 11348 |
| No RP1, PCIe, gpiochip, I2C or fan reference in this unit | grep clean |

## 8. Comments and naming that carry port-internal vocabulary (for the readability stage)

| Item | Where |
| --- | --- |
| Headers say "design sketch v2 (not in any repository)", "reference for the tutorial; not in any repository until you type it" | PlaybackHold, ClipFrames, DngTags, DngFrameReader, DecodeSlots, ClipProbe, RawRender headers |
| References to "critic M5/M8/m14", "operator P15/P19", "D15", "R2", "F22", "T47/T48", "design §4.7", "Q21", "O10", "U9" | throughout src/playback and App routes |
| Header cites `working/tools/playback/frames_test.cpp` (KB, not in repo); `dng_limits_test.cpp` is in repo but not in CMake | PlaybackFrames.hpp:4 |
| README.apertar.md says lj92 "Used to decode lossless JPEG tiles in the UI and independently verify the Apertar encoder" (not the Core decoder use) and lists a local fix; Core and UI copies are byte-identical, so the fix is also in upstream UI's copy (probable: README upstream identical) | third_party/liblj92/README.apertar.md |
| Core unit tests: upstream Core has none; port adds `tools/*_test.cpp` | |
