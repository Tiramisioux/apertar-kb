# Review: Playback (stage 2)

Refs: port = Core `cinemate-port` `01f170c`, UI `cinemate-port` `7ea9afc`; upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream`).
Yardstick: `raw/conv-core-command-plane.md` (C1-*). `apertar-conventions.md` does not exist yet.
Read completely: `src/playback/*` (9 files), `tools/dng_limits_test.cpp`, `third_party/liblj92/README.apertar.md`. App at the grep anchors. UI diff of the four files.
Host check: `tools/dng_limits_test.cpp` compiles with plain g++ and passes ("all passed", 2026-11-17).

## Verdict in one paragraph

Decoding DNGs in Core is new ground, and the contributor weighed it. `design-playback.md` section 2.1 compares six options (A-F) and picks "A. Core decodes on demand". `decisions.md` records the owner's answers (Q16, Q21, Q20). The module layout is close to upstream's: a subsystem folder with its own `apertar::<sub>` namespace, header-only helpers, routes in the flat `handleWebRequest` chain, and the guard at the top of `handleCommand`. What a maintainer would refuse is the surface:
- Every header carries tutorial and critic vocabulary ("design sketch v2 (not in any repository)", "critic M8", T47, R2, D15).
- The tjhandle in `encodeRgbJpeg` leaks once per decoded frame.
- The playback routes write JSON error bodies by hand where upstream always calls `errorReply`.
- Two text helpers duplicate App's formatters.
- Some code exists only for tests kept in the KB.
- In a hold, the media list narrows: H.264 and timelapse folders and uncached takes drop out.

## Findings

| Id | Cat | Sev | Title | Port (confirmed) | Upstream (confirmed) | Rework | Effort | Deliberate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | slop | major | Comments narrate tutorial/critic history | `PlaybackHold.hpp:3` "design sketch v2 (not in any repository)"; `ClipProbe.hpp:3` "reference for the tutorial; not in any repository until you type it"; "critic M5/M8/M9/m14/m18", "operator P15/P19", D15, U9, T31, T47, T48, R2, F22, "design §4.7", "KB rule M5" across all 9 files and App routes (`App:6335`, `App:7354`, `App:8476`, `App:8551`, `App:10915`, `App:10967`, `App:12574`); `AppH:173` "T50, Q23" | C1-I14: comments are rare, state a hazard or reason as a sentence; 10 comment lines in upstream App, 0 TODO | Strip ids and history. Keep one-sentence hazards: why the yield window is lock-free (camera mutex held across stop drain), why the facts cache keys on mtime (exFAT readdir cost), why fadvise DONTNEED, why the render is a copy of `cdngimageprovider.cpp` (name the UI function, drop "critic"). Delete the multi-paragraph header essays | M | no |
| F2 | bug | major | tjhandle leaks once per decoded frame | `PlaybackFrames.cpp:92` `thread_local tjhandle handle = tjInitCompress();` is never `tjDestroy`ed. Decode runs on the per-connection detached thread, and the server answers `Connection: close`, so every decoded frame is a new thread and a new leaked handle | `App:4108-4134@upstream` `struct TurboJpegCompressor { ... ~TurboJpegCompressor() { if (handle) tjDestroy(handle); } }` and `thread_local TurboJpegCompressor compressor;`. `WebServer.cpp:276@upstream` one detached thread per client, `:133` `Connection: close` | Use the upstream RAII wrapper. Better: reuse it. Move `TurboJpegCompressor` to a small shared header (or expose an `encodeRgbToJpeg` beside `encodeYuv420ToJpeg` in App) and call that from playback | S | no |
| F3 | mismatch | minor | Hand-written JSON error bodies in playback routes | `App:8499`, `App:8530`, `App:8571`, `App:8687` `response.body = "{\"ok\":false,\"error\":\"Playback held: " + hold + ...`; `App:8505` `{"ok":false,"error":"This clip was removed.","gone":true}`; `App:8533` `{"ok":false,"busy":true}` (no error sentence) | C1-I06: replies only from `okReply`/`errorReply`. Upstream has no `response.body = "{` literal (grep in upstream App: 0 hits); every media route uses `errorReply(-1, ...)` (`App:7203`, `App:7217@upstream`) | One local lambda in `handleWebRequest` (C1-I17), e.g. `heldResponse(hold)`, that builds the 409 with `errorReplyBody(-1, sentence, "\"hold\":\"" + hold + "\"")` (`App:173@port`). Busy: `errorReplyBody(-1, "Busy. Try again.", "\"busy\":true")`. Gone: same with `"gone":true`. The hold check repeats in 5 routes, so this collapses them | S | no |
| F4 | removed-upstream-behaviour | major | In a hold, `/api/media` drops non-cached items | `App:7448-7453` `if (held && !haveFacts) { continue; }`: during a take, write drain, standby, media test or 3 s yield, H.264/ProRes container folders, every `Timelapse_*` folder and every take not yet in the facts cache vanish from the list. `Photos/` is still read from the card (`App:7529`), so "nothing may read the card" is not kept either | `App:6282-...@upstream` `discoverMediaLibraryItems` lists every folder whenever media is mounted; no hold | Keep the cached answer for cDNG takes. For folders without facts in a hold, list the bare entry (name, kind, category from the folder name, `size_text` "--") without the recursive scan, as the comment at `App:7488` already promises ("or the bare entry"). Or say plainly in the reply (`held`) that the list is partial and let the page show that | S | partly (Q4 "hold everything"; the vanishing items are not discussed) |
| F5 | removed-upstream-behaviour | minor | Downloads refused in every hold, also in standby | `App:8683-8689`, `App:8812`: 409 for recording, writing, media_test, standby, media; running streams stop within one 64 KiB chunk (`App:7297-7300` zip SIGTERM) | `App:7197-7330@upstream`: downloads have no recording gate | Keep (owner chose Q21, Q20). Document in README's WebUI section. Use the `errorReply` path from F3 | S | yes (decisions.md Q21, Q20) |
| F6 | duplication | minor | Text helpers duplicate App formatters, with different output | `ClipProbe.hpp:41` `sizeText` = same rule as `formatBytesHuman` (`App:4595@port`); `ClipProbe.hpp:30` `durationCardText` gives "01:02:03" and "00:00" where App's `durationTextForFrameCount` gives "1:02:03" and "--"; `fpsText` via `%g` vs `compactNumber(fps) + " FPS"` | `App:3922@upstream` `formatBytesHuman`; `App:5747@upstream` `durationTextForFrameCount`; `discoverMediaLibraryItems` uses `compactNumber(fps) + " FPS"` | `ClipFacts` carries numbers only (bytes, fps, span seconds). `discoverMediaLibraryItems`/`clipInfoJson` format with App's existing helpers (C1-S06: helpers are free functions in App). Then cDNG items and other items in one list read alike | S | partly (comment says "copies of touch UI card text"; upstream Core's own formatters not mentioned) |
| F7 | slop | minor | Code that exists only for KB tests, and dead code | `DecodeSlot::rgb` (`DecodeSlots.hpp:32`) never filled: `renderPreview` allocates a fresh `Rgb8Image` per request (`RawRender.hpp:141`), so the "7 MiB rgb kept per slot" in the comment is false; `DecodeSlots::bytesHeld()` (total), `ClipFactsCache::probes()`, `FrameList::numberAtTime`, `DngInfo::tailBytesRead`, `FrameOut::decodeMs` used only by headers; `PlaybackFrames.hpp:4` cites `working/tools/playback/frames_test.cpp` (KB, not in repo) | Upstream Core keeps no test hooks in `src` (no tests at all, BRIEF) | Either render into `slot->rgb` (pass the buffer into `renderPreview`), which is what the slot was for, or delete the member and fix the comment. Delete the unused API or move the KB test into `tools/` so the hooks have a caller | S | no |
| F8 | mismatch | minor | Hold rule built twice; string round-trips back to enum | `App:9363-9372` fills `HoldSignals` by hand in `buildWebStateJson`; `App:11341-11357` fills it again in `playbackHoldReason`; `App:10970-10976` parses the returned string back into `playback::Hold` with an if-chain; the comment at `App:9362` ("a second read of the camera would wait on its mutex") sits above `camera_.isRecording()` read a second time (`App:9364`); the watcher calls `playbackHoldReason(false)` twice per cycle (`App:10970`, `App:10979`) | Upstream gates inline: `if (camera_.isRecording() \|\| soundRecordingActive() \|\| camera_.timelapseActive())` (`App:7514`, `App:7586@upstream`) | `playbackHoldReason` returns `playback::Hold`; callers use `holdName()` only when they write JSON. Watcher: one call, reuse the value. Drop the stale comment or the second `isRecording()` read | S | no |
| F9 | bug | minor | FORMAT row guesses lossy from the clip name | `ClipProbe.hpp:168-178`: `lossy3` iff name contains "cDNG_3to1"/"lossy3". Lossy DNG is written as compression 7 + LinearizationTable (`LossyDngEncoder.cpp:537`, `:545`). Failing input: clip-name template without `{format}`/`{comp}` (for example `{date}_{take}`) recorded as lossy 3:1 -> FORMAT "Clear HDR 12-bit companded · lossless" | no precedent | Read the ratio from a tag Core writes (or add a private tag/ImageDescription at write time), or show "12-bit companded" without lossless/lossy when the name does not tell | S | no |
| F10 | slop | nit | Diagnostic response headers no page reads | `App:8541-8545` `X-Frame-Source`, `X-Decode-Ms`, `X-Frame-Count`: WCP reads only `X-Frame-Number`, `X-Frame-Index`, `X-Histogram` (`WCP:12368-12370`) | Upstream routes send no X- headers | Drop the three unused headers and `fromCache`/`decodeMs` | S | no |
| F11 | new-ground | nit | `APERTAR_PLAYBACK_WORKERS` env knob, undocumented | `PlaybackFrames.cpp:82-87` | Precedent exists: `APERTAR_LOSSYDNG_WRITER_BYTES` (`LossyDngEncoder.cpp:100@upstream`). Launch options are `Options` + `--x` + README row (C1-S24) | Fix to 2 slots (memory budget is sized for it), or add a README line. No `--option` needed | S | no |
| F12 | slop | nit | `third_party/liblj92/README.apertar.md` describes the UI's use | "Used to decode lossless JPEG tiles in the UI and independently verify the Apertar encoder." Byte-identical to `ui-upstream/third_party/liblj92/` (`diff -r` empty) | UI upstream owns that README | Change the sentence for Core: "Core decodes lossless tiles for WebUI playback (`src/playback/DngFrameReader.hpp`)." Keep the rest | S | no |
| F13 | pi-compat | minor | RAM held by playback on small boards | `DecodeSlots.hpp:24-30`: ~38 MiB samples per slot at IMX283 size, 2 slots default, up to 4; plus 8 + 24 MiB JPEG LRU that is never trimmed (`PlaybackFrames.cpp:79-80`). Slots trim after 30 s idle or in a hold; caches do not | Upstream Core holds no decode memory | Trim the JPEG caches in the hold too (same `trimIdleFrameSlots` call). Note the peak in README for 1-2 GB boards (Pi 4 2 GB, CM4 1 GB). Unconfirmed on a Pi: `free -m` during a 4-tab scrub | S | partly (memory is costed in the comments, cache trim not) |
| F14 | duplication | nit | Two millisecond clocks | `DecodeSlots.hpp:47` `steadyMs()` and `App:6336` `playbackNowMs()`, same steady clock | - | Keep one (`playbackNowMs` beside the yield in `PlaybackHold.hpp`) | S | no |
| F15 | mismatch | nit | UI helper namespace style | UI `ClipFrameFiles.hpp:17` `namespace apertar::clipframes` | UI upstream free-helper headers use one PascalCase/camel namespace: `VideoPlayback.hpp:13` `namespace VideoPlayback`; `lowPower`, `standbyUsb`. No `apertar::` namespace in ui-upstream `src` | `namespace ClipFrameFiles` (file name = namespace, as `VideoPlayback`) | S | no |

Notes on items checked and not reported:
- `/api/media` new item fields, `held`, and `playback_hold` in `/api/state`: additive flat keys. Unknown keys are ignored (C1-N11), and `/api/state` already mixes flat keys and groups (C1-S14). No protocol break. The socket protocol is untouched: no new command or event.
- `clipInfoJson` nests (`holes` array, `meta`, `extra`, `ramp`). This is HTTP only, and `/api/media` upstream already nests `items`. The flat-socket rule C1-I09 does not apply.
- `mediaDeleteActive_` guard at the top of `handleCommand` (`App:12585`) follows C1-S04 (a guard covering several commands, `errorReply` sentence "Deleting media. One moment.", C1-I07).
- File-scope singletons `playbackYield()`, `clipFactsCache()` (`App:6342-6359`) have precedent: `captureSettingsPersister()` (`CC:885@upstream`) and function-local caches (C1-I19).
- Race: the delete route checks `isRecording()` without `commandMutex_`, then sets `mediaDeleteActive_` (`App:9015-9029`). A `record_start` between the two still starts. The window is microseconds and upstream has the same unlocked check. Not reported.
- Frame width is parsed as uint64 and cast to uint32 before `allowedFrameWidth` (`App:8491-8492`). 2^32+320 passes as 320. Harmless.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `src/playback/` + `apertar::playback` (Core decodes DNG) | keep | Weighed against 5 alternatives (`design-playback.md` 2.1). Fits upstream's subsystem-folder layout (`src/cdng`, `src/lossydng`, `src/mlv`, `apertar::<sub>`). Needs F1 cleanup and one README paragraph for the original developer |
| `PlaybackYield` (atomic window) | keep | A decode between chunks cannot take the camera mutex (held across stop drain). Lock-free stop is the one way. Opened at the top of `handleCommand` like a C1-S04 guard |
| `HoldSignals` + `playbackHoldFor` + `Hold` | simplify | One member `Hold playbackHold() const` in App with inline ifs (upstream gating style). Drop the string round-trip (F8). Keep `holdName` for JSON |
| `FrameList` / `listFrames` | keep | No Core precedent. The number clock (frame number, not position) is the documented reason. Drop unused `numberAtTime` or give it a caller |
| `DngInfo` / `readDngInfo` + size caps | keep | Qt-free and bounds-checked before allocation. `dng_limits_test.cpp` covers the caps |
| `readDngSamples` / `ReadOptions` | keep | `stop` callback and fadvise are the take-safety point |
| `renderPreview` / `rawHistogram` (named copy of UI look) | keep | Parity with the touch screen was the owner's requirement. The comment must name the UI functions without KB ids, and say where the parity check lives |
| `DecodeSlots` + `Lease` | simplify | Purpose holds (buffer reuse, 503 instead of queue). `rgb` is dead (F7) and `bytesHeld()` total is unused |
| `JpegCache` (two LRU) | keep, trim in hold | Small, local to the .cpp. Add trim on hold (F13) |
| `ClipFacts` / `probeClip` / `ClipFactsCache` | keep | Replaces a recursive scan per request with one stat. Facts should be numbers, with formatting in App (F6) |
| text helpers `durationCardText`, `sizeText`, `shotDate`, `timecodeText`, `clipToken` | simplify | `sizeText` and `durationCardText` -> App's `formatBytesHuman`/`durationTextForSeconds`. `shotDate`, `timecodeText`, `clipToken` stay |
| `encodeRgbJpeg` | rework-to-upstream-pattern | Use upstream's `TurboJpegCompressor` RAII and share one encoder (F2) |
| `niceThread` | keep | One `setpriority` on a thread that dies with the request. Linux-only like the rest of Core |
| `parseSingleByteRange`, `wavFormatForFile`, `wavSoundText` | keep | Free functions in App's anonymous namespace (C1-S06), returning bool/optional (C1-I10) |
| file-scope `playbackYield()`, `clipFactsCache()`, `playbackNowMs()` | keep | Precedent `captureSettingsPersister()` (CC:885). Drop the "header does not pull in readers" history line |
| `ApertarCoreApp::playbackHoldReason(bool)` | simplify | Return `Hold` (F8) |
| `third_party/liblj92/` in Core | keep | Byte-identical to upstream UI's vendored copy, license kept. Fix README (F12) |
| UI `apertar::clipframes` / `ClipFrameFiles.hpp` | keep | Replaces three copy-pasted listing blocks with one helper. Flat clips are listed and ordered as before. Namespace style nit (F15) |

## Conforms

- Routes are added to the flat `handleWebRequest` chain as `if (request.method == "GET" && request.path == "/api/media/...")` (`App:8442`, `:8475`, `:8550`) (C1-S10).
- Playback changes no state through HTTP. It reads files only. The commands that start a take still enter through `handleCommand` (C1-S01, C1-S09).
- The yield and delete guards sit at the top of `handleCommand` under `commandMutex_`. The delete refusal is an operator sentence through `errorReply` (C1-S04, C1-I06, C1-I07).
- No new thread. Slot trim rides an existing loop (C1-S20/S21 intent).
- `discoverMediaLibraryItems` and `buildMediaLibraryJson` are extended in place. The upstream scan stays as the fallback, and JSON is written with `ostringstream` + `escapeJson` (C1-I08).
- `WebServer.cpp` reasonPhrase gains three lines in the existing switch.
- CMake: two source lines and one include dir. No new target.
- The new subsystem folder and namespace match `src/cdng`, `src/lossydng`, `src/mlv` and `apertar::<sub>`. Header-only modules have precedent (`util/SettingsFile.hpp`).
- Helpers return `bool` + error string and never throw across the routes (C1-I10).
- Opening with `O_CLOEXEC` and `POSIX_FADV_DONTNEED` mirrors the writer.
- `dng_limits_test.cpp` builds with plain g++ and passes, in the style of the other `tools/*_test.cpp` (it has no README line, unlike `frame_path_test`).
- UI: the three inline `entryList` + QCollator blocks become one helper. Behaviour for flat clips is unchanged.

## Skeptic

Stage 3. Every finding re-read in code at port `01f170c` and `upstream-1.6.0` (`/home/user/wt/core-upstream`), UI at `7ea9afc`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: all 9 `src/playback/*` headers open with "design sketch v2 (not in any repository)" / "T47 part B1 (reference for the tutorial ...)" / "T48"; App:6335 "T47: ...", App:12572 "T47 ... (design §2.7)", AppH:173 "T50, Q23". Upstream App has 12 `//` lines in 13 k |
| F2 | stands | Confirmed: `PlaybackFrames.cpp:92` raw `thread_local tjhandle`, no destroy. `WebServer.cpp:279-290@port` one detached thread per connection, `clientLoop` (`:298`) serves one request, `:136/:150` `Connection: close`. Upstream RAII `TurboJpegCompressor` at App:4108-4121@upstream, still present at App:4807@port |
| F3 | corrected | Sites confirmed (8499, 8506, 8529, 8532, 8569, 8687, plus 8816 missed). Two corrections: `errorReplyBody` is not upstream, the port added it in `f5a61b8` (Controls unit); and the page reads only the status code for hold/busy (`WCP:12355-12358`) and only `body.gone` (`WCP:12361`), so `hold`/`busy` keys are unused. The "unescaped" point is weak: `hold` is a fixed `holdName` token |
| F4 | corrected | Code confirmed (App:7448-7453, Photos still scanned App:7529). Not silent: the page shows "Playback held: recording. Pictures return when it ends." (`WCP:11939-11941`), and the browser button is greyed in a take (`WCP:12022-12024`, owner Q5). So the visible loss is: browser already open when a take starts, items drop out while the line says pictures return. Severity major -> minor |
| F5 | stands | Confirmed App:8682-8689, 8811-8818. Q21 covers takes, Q20 standby; the writing/media_test/media holds are an inferred extension (media = card unusable, downloads fail anyway) |
| F6 | corrected | `sizeText` gives the same output as `formatBytesHuman` (App:4595@port): delete it. `durationCardText` differs on purpose: its comment says it copies the touch UI card (`ClipProbe.hpp:29`, design §4.2 "both screens say one thing"). Rework must pick one rule for the whole list, not silently change cDNG to App's "1:02:03"/"--". Deliberate: unknown |
| F7 | stands | Confirmed: `DecodeSlot::rgb` never written (only `bytesHeld`/`release` touch it, `DecodeSlots.hpp:37,43`); `renderPreview` builds its own `Rgb8Image` (`RawRender.hpp:136-141`). `DecodeSlots::bytesHeld()` total (`:105`), `probes()` (`ClipProbe.hpp:236`), `numberAtTime` (`ClipFrames.hpp:76`), `tailBytesRead` (`DngTags.hpp:67,238`) have no caller. `decodeMs`/`fromCache` do have a caller (F10 headers), so they move to F10. Upstream has no `tools/` at all |
| F8 | stands | Confirmed App:9362-9372, 11341-11357, 10970-10979 (two `playbackHoldReason(false)` calls per watcher cycle, each 4 camera-mutex reads) |
| F9 | stands | Confirmed `ClipProbe.hpp:168-178`; lossy written as `CdngCompression::LosslessJpeg` + `linearizationTable` (`LossyDngEncoder.cpp:537,544`). Custom templates may drop `{format}` (token picker `WCP:14462+`), so the guess fails |
| F10 | corrected | Headers confirmed unread. But "upstream sends no X- headers" is wrong: upstream sends `X-Accel-Buffering` (App:7114@upstream). Upstream sends no diagnostic headers |
| F11 | dropped | Upstream does the same: `APERTAR_LOSSYDNG_WRITER_BYTES` (`LossyDngEncoder.cpp:100@upstream`) is an undocumented env knob too (no README hit in upstream). Not a mismatch |
| F12 | stands | `diff -r` against ui-upstream empty; README line 8-9 "decode lossless JPEG tiles in the UI" |
| F13 | corrected | Per-slot figure is ~39 MiB held (samples 38 + scratch 1.3), not 46: the 7 MiB `rgb` is never filled (F7) and is a per-request allocation instead. JPEG caches 8 + 24 MiB (`PlaybackFrames.cpp:76-77`), no clear path; `trimIdleFrameSlots` (`:244-247`) trims slots only |
| F14 | corrected | Three identical clocks, not two: `steadyMs` (`DecodeSlots.hpp:47`), `playbackNowMs` (App:6336), and `trimNowMs` (App:6394, port `d44b177`). Upstream writes the expression inline (App:7036, 8617@upstream) |
| F15 | stands | `namespace apertar::clipframes` (`ClipFrameFiles.hpp:17`); ui-upstream free-helper namespaces are `VideoPlayback`, `lowPower`, `standbyUsb`, never `apertar::` |

## Final findings

### Playback-F1 [slop, major] Comments narrate tutorial and critic history across all playback files
- where: `src/playback/PlaybackHold.hpp:3`, `ClipProbe.hpp:3`, `DngTags.hpp:3`, `DecodeSlots.hpp:3`, `DngFrameReader.hpp:3`, `ClipFrames.hpp:3`, `RawRender.hpp:3`, `PlaybackFrames.hpp:3`, `PlaybackFrames.cpp:1`, `src/ApertarCoreApp.cpp:6335`, `:12572`, `src/ApertarCoreApp.hpp:173` @cinemate-port
- port: multi-paragraph header essays citing "design sketch v2 (not in any repository)", "reference for the tutorial; not in any repository until you type it", critic M1/M5/M8/M9/m14, operator P1, T47/T48/T50, Q23, "design §2.7/§4.x", "KB rule M5", KB test paths
- apertar way: comments are rare, one sentence on a hazard or reason (C1-I14); upstream App has about a dozen `//` lines in 13 k lines, no ticket ids
- why it matters: the original developer cannot resolve the ids; the subsystem reads as a tutorial transcript
- rework: strip ids and history from `src/playback/*` and the App/AppH playback lines. Keep one-sentence hazards: lock-free yield (camera mutex held across the stop drain), mtime-keyed facts cache (readdir cost on exFAT), `POSIX_FADV_DONTNEED`, frame number vs position clock, `RawRender` is a named copy of the UI's `cdngimageprovider.cpp` preview (name the function, drop "critic"/"KB rule")
- effort: M. deliberate: no

### Playback-F2 [bug, major] tjhandle leaks once per decoded frame
- where: `src/playback/PlaybackFrames.cpp:92@cinemate-port`
- port: `thread_local tjhandle handle = tjInitCompress();` never `tjDestroy`ed. Decode runs on the web connection thread; `WebServer.cpp:279-290@cinemate-port` starts one detached thread per connection and `clientLoop` serves one request (`Connection: close`, `:136`), so every decoded (non-cached) frame leaks one handle with its libjpeg state
- apertar way: `src/ApertarCoreApp.cpp:4108-4121@upstream-1.6.0` `struct TurboJpegCompressor { ... ~TurboJpegCompressor() { if (handle) tjDestroy(handle); } }` used as `thread_local TurboJpegCompressor compressor;` (`:4134`)
- why it matters: Core memory grows with every scrub and play session
- rework: move `TurboJpegCompressor` (unchanged) to a small shared header or expose an `encodeRgbToJpeg` next to `encodeYuv420ToJpeg` in App; playback calls it. Delete the raw handle
- effort: S. deliberate: no

### Playback-F3 [mismatch, minor] Playback routes hand-write JSON error bodies
- where: `src/ApertarCoreApp.cpp:8499`, `:8506`, `:8529`, `:8532`, `:8569`, `:8687`, `:8816@cinemate-port`
- port: `response.body = "{\"ok\":false,\"error\":\"Playback held: " + hold + ...`, `{"ok":false,"busy":true}` with no sentence, `{"ok":false,"error":"This clip was removed.","gone":true}`; the hold block is repeated in five routes
- apertar way: upstream web routes set the body only through `errorReply(-1, sentence)` / `okReply` (e.g. `src/ApertarCoreApp.cpp:7204,7218@upstream-1.6.0`); zero `response.body = "{` literals in upstream App. `errorReplyBody` is not upstream (added by the port in `f5a61b8`)
- why it matters: foreign reply construction; a busy reply with no operator sentence
- rework: hold and busy: `errorReply(-1, sentence)`; the page reads only the status (409/503, `WCP:12355-12358`), so the `hold`/`busy` keys can go. Gone: the page needs `gone` (`WCP:12361`); answer 410 with `errorReply`, or keep the one extra key via `errorReplyBody` if that helper survives the Controls review. One local lambda in `handleWebRequest` (C1-I17) for the repeated hold check
- effort: S. deliberate: no

### Playback-F4 [removed-upstream-behaviour, minor] In a hold, /api/media drops items without cached facts
- where: `src/ApertarCoreApp.cpp:7448-7453`, `:7529@cinemate-port`
- port: `if (held && !haveFacts) continue;` during a take, write drain, standby, media test or yield window, H.264/ProRes container folders, every `Timelapse_*` folder and every take not yet probed vanish from the list; `Photos/` is still read from the card. The page shows "Playback held: ... Pictures return when it ends." (`WCP:11939-11941`), which promises thumbnails back, not missing items. The browser button is greyed in a take (`WCP:12022-12024`, owner Q5), so the case is a browser already open when the take starts
- apertar way: `discoverMediaLibraryItems` (`src/ApertarCoreApp.cpp:6282@upstream-1.6.0`) lists every folder whenever media is mounted
- why it matters: items disappear from an open list during a take, and the hold's own goal (no card reads) is not met for `Photos/`
- rework: in a hold list the bare entry (name, kind, category from the folder name, size "--") without the recursive scan, as the comment at App:7488 already says ("or the bare entry"); or skip `Photos/` too and say in the status line that the list is partial
- effort: S. deliberate: unknown (Q4 "hold everything" and Q5 greyed button are owner decisions; vanishing entries are not discussed)

### Playback-F5 [removed-upstream-behaviour, minor] Downloads refused in every hold, also standby
- where: `src/ApertarCoreApp.cpp:8682-8689`, `:8811-8818`, zip stop `:7349@cinemate-port`
- port: 409 for recording, writing, media_test, standby, media; running downloads stop within one 64 KiB chunk, zip child gets SIGTERM
- apertar way: `/api/media/download` (`src/ApertarCoreApp.cpp:7197-7330@upstream-1.6.0`) has no recording gate
- why it matters: upstream behaviour narrowed; the original developer must find it documented
- rework: keep; one README line in the WebUI section; reply through `errorReply` (F3)
- effort: S. deliberate: yes (`working/playback/decisions.md` Q21 takes, Q20 standby; the writing/media_test cases are an extension of Q21)

### Playback-F6 [duplication, minor] Clip text helpers duplicate App formatters
- where: `src/playback/ClipProbe.hpp:30`, `:41@cinemate-port`
- port: `sizeText` gives the same text as `formatBytesHuman` (App:4595@cinemate-port); `durationCardText` gives "01:02:03"/"00:00" (copy of the touch UI card, comment `ClipProbe.hpp:29`) while other list items use `durationTextForFrameCount` "1:02:03"/"--"; fps via `%g`
- apertar way: `formatBytesHuman` `src/ApertarCoreApp.cpp:3922@upstream-1.6.0`; `durationTextForFrameCount` `:5747`, `durationTextForSeconds` `:5767`; `compactNumber(fps) + " FPS"` in `discoverMediaLibraryItems`
- why it matters: two formatting rules in one list; maintenance in two places
- rework: delete `sizeText`, use `formatBytesHuman`. `ClipFacts` carries numbers (bytes, fps, span seconds); App formats. For duration, choose one rule for the whole WebUI list (touch-UI parity or App's) and use it for every item, not one per item kind
- effort: S. deliberate: unknown (touch-UI parity is stated; the clash with App's own helpers is not)

### Playback-F7 [slop, minor] Dead code and hooks for tests kept outside the repo
- where: `src/playback/DecodeSlots.hpp:26-32,105`, `src/playback/RawRender.hpp:136-141`, `src/playback/ClipProbe.hpp:236`, `src/playback/ClipFrames.hpp:76`, `src/playback/DngTags.hpp:67`, `src/playback/PlaybackFrames.hpp:4@cinemate-port`
- port: `DecodeSlot::rgb` is never filled (`renderPreview` allocates its own `Rgb8Image` per request), so the "rgb 7 MiB per slot" comment is false; `DecodeSlots::bytesHeld()` (total), `ClipFactsCache::probes()`, `FrameList::numberAtTime`, `DngInfo::tailBytesRead` have no caller in the repo; header cites KB `working/tools/playback/frames_test.cpp`
- apertar way: upstream Core has no tests and no `tools/`; no test hooks in `src`
- why it matters: unused API and a wrong memory claim
- rework: render into `slot->rgb` (pass the buffer to `renderPreview`) or delete the member and fix the comment; delete the unused API, or move the KB test into `tools/` beside `dng_limits_test.cpp` so the hooks have a caller
- effort: S. deliberate: no

### Playback-F8 [mismatch, minor] Hold rule built twice; name string parsed back into enum
- where: `src/ApertarCoreApp.cpp:9362-9372`, `:11341-11357`, `:10970-10979@cinemate-port`
- port: `HoldSignals` filled by hand in `buildWebStateJson` and again in `playbackHoldReason`; the watcher maps the returned string back to `playback::Hold` with an if-chain and calls `playbackHoldReason(false)` twice per cycle (4 camera-mutex reads each); the comment at :9362 says the builder avoids a second camera read, then calls `camera_.isRecording()` again at :9364
- apertar way: upstream gates inline: `if (camera_.isRecording() || soundRecordingActive() || camera_.timelapseActive())` (`src/ApertarCoreApp.cpp:7514,7586@upstream-1.6.0`)
- why it matters: over-built indirection and a comment the next line contradicts
- rework: `playbackHoldReason` returns `playback::Hold`; `holdName()` only where JSON is written; one call per watcher cycle, reused for the yield and the trim; fix or drop the stale comment
- effort: S. deliberate: no

### Playback-F9 [bug, minor] FORMAT row guesses the lossy ratio from the clip name
- where: `src/playback/ClipProbe.hpp:168-178@cinemate-port`
- port: lossy 3:1/5:1 iff the folder name contains `cDNG_3to1`/`lossy3` (`cDNG_5to1`/`lossy5`). Lossy DNGs are written as compression 7 + LinearizationTable (`src/lossydng/LossyDngEncoder.cpp:537,544@cinemate-port`), the same tags as lossless companded
- apertar way: no precedent
- why it matters: a custom clip-name template without `{format}`/`{comp}` (e.g. `{date}_{clip}`, allowed by the token picker) recorded lossy 3:1 shows FORMAT "Clear HDR 12-bit companded · lossless"
- rework: derive the ratio from something Core writes (a tag or ImageDescription at write time), or drop the lossless/lossy suffix when the name does not say
- effort: S. deliberate: no

### Playback-F13 [pi-compat, minor] Playback RAM on 1-2 GB boards; JPEG caches never trimmed
- where: `src/playback/DecodeSlots.hpp:26-30`, `src/playback/PlaybackFrames.cpp:76-87`, `:244-247@cinemate-port`
- port: ~39 MiB held per slot at IMX283 size (samples 38 + scratch 1.3; the comment's 46 counts the unused `rgb`), 2 slots default, 4 max, plus ~7 MiB per in-flight render; JPEG LRU 8 + 24 MiB with no clear path. Slots trim after 30 s or in a hold; caches never
- apertar way: upstream Core holds no decode memory
- why it matters: up to 32 MiB stays resident through takes on Pi 4 2 GB / CM4 1 GB (unconfirmed on a Pi: `free -m` during a 4-tab scrub, then during a take)
- rework: clear both JPEG caches in `trimIdleFrameSlots` when `hold` is true; fix the slot comment; note peak memory in README
- effort: S. deliberate: unknown (slot memory costed in comments; cache trim not discussed)

### Playback-F10 [slop, nit] Diagnostic response headers no page reads
- where: `src/ApertarCoreApp.cpp:8540-8546@cinemate-port`, `src/playback/PlaybackFrames.hpp:29-30`
- port: `X-Frame-Count`, `X-Frame-Source`, `X-Decode-Ms` sent; WCP:12368-12370 reads only `X-Frame-Number`, `X-Frame-Index`, `X-Histogram`; no UI reader
- apertar way: upstream sends one functional header (`X-Accel-Buffering`, `src/ApertarCoreApp.cpp:7114@upstream-1.6.0`) and no diagnostic ones
- why it matters: debug leftovers
- rework: drop the three headers and `FrameOut::fromCache`/`decodeMs`
- effort: S. deliberate: no

### Playback-F12 [slop, nit] liblj92 README describes the UI's use
- where: `third_party/liblj92/README.apertar.md:8@cinemate-port`
- port: byte-identical copy (`diff -r` against ui-upstream empty): "Used to decode lossless JPEG tiles in the UI and independently verify the Apertar encoder."
- apertar way: ui-upstream `third_party/liblj92/README.apertar.md` owns that sentence
- why it matters: misleads about Core's use
- rework: state Core's use (`src/playback/DngFrameReader.hpp`, WebUI playback); keep the provenance and local-fix lines
- effort: S. deliberate: no

### Playback-F14 [duplication, nit] Three identical millisecond steady clocks
- where: `src/playback/DecodeSlots.hpp:47`, `src/ApertarCoreApp.cpp:6336`, `:6394@cinemate-port`
- port: `steadyMs()`, `playbackNowMs()` and `trimNowMs()` (port `d44b177`) are the same expression
- apertar way: upstream writes the `steady_clock` expression inline where needed (`src/ApertarCoreApp.cpp:7036,8617@upstream-1.6.0`)
- why it matters: small duplication
- rework: keep one (`playbackNowMs` in `PlaybackHold.hpp`, or inline as upstream); delete the others
- effort: S. deliberate: no

### Playback-F15 [mismatch, nit] UI helper namespace style
- where: `/home/user/Apertar-UI/src/ClipFrameFiles.hpp:17@cinemate-port`
- port: `namespace apertar::clipframes`
- apertar way: ui-upstream free-helper namespaces `VideoPlayback` (`src/VideoPlayback.hpp:13`), `lowPower`, `standbyUsb`; no `apertar::` namespace in ui-upstream `src`
- why it matters: small style drift in the UI
- rework: `namespace ClipFrameFiles` (file name = namespace, as `VideoPlayback`)
- effort: S. deliberate: no

Dropped: F11 (upstream's own `APERTAR_LOSSYDNG_WRITER_BYTES` is the same undocumented env-knob pattern).
