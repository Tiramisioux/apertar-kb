# R4: playback in the KB and the Cinemate handbook

This is the reader report for the playback project. Patrik's brief: "port the playback function from cinemate, in the most
Apertar like style". His decision of 2026-10-28: "make the playback in web ui similar to the current touch ui".

This report covers what the **Apertar KB** and the **Cinemate handbook** already record about four things:

- Apertar's touch-UI clip browser and player (structure, bugs, limits).
- Apertar's WebUI and its HTTP server (what playback would sit on).
- What Apertar's recorder writes that a player must cope with.
- Cinemate's playback lessons and browser traps, plus Patrik's stated preferences, plus every KB rule that constrains the work.

It does not re-read Cinemate's code (see `working/playback/r1-cinemate-playback.md` in the KB) or the touch UI in depth (see
`r2-apertar-ui-player.md` next to this file). It adds a few checks against the two GitHub tips, but only where a KB line
needed confirming or had gone stale. Each of those is marked "(tip check)".

## Sources and labels

| Short | Tree | Commit |
| --- | --- | --- |
| `kb:` | Apertar KB `/home/user/apertar-kb` | `019fb72` (HEAD). STATUS.md last changed `dbcbfca`. working/controls and working/playback last changed `a08da9a` |
| `hb:` | Cinemate handbook `/home/user/tiramisioux/cinemate-handbook` | `c99ff77` |
| `core:` | Apertar-Core, Patrik's GitHub `cinemate-port` tip | `eb9cc39` |
| `ui:` | Apertar-UI, Patrik's GitHub `cinemate-port` tip | `d8098d0` |

- **CONFIRMED**: I opened the cited line and it says this. For a `kb:` or `hb:` line, that means *the KB or handbook records
  this*. When the KB's own label for the underlying code fact is weaker, I say so in brackets: [KB: probable],
  [KB: unconfirmed].
- **PROBABLE**: derived. The derivation is given.
- **UNCONFIRMED**: nothing settles it. The command that would settle it is given.
- Most `kb:` code refs are against `upstream-1.6.0` (kb:llm/README.md:16, :57-58).
  - **Touch-UI player refs still hold at `ui:d8098d0`** (tip check, CONFIRMED). `git log` on `qml/ClipBrowserPage.qml`,
    `qml/ClipPlayerPage.qml`, `qml/Main.qml`, `src/playbackcontroller.*`, `src/cliplistmodel.*`, `src/cdngimageprovider.cpp`,
    `src/dngdecoder.cpp`, `src/MlvReader.*`, `src/VideoPlayback*.cpp` and `src/main.cpp` shows only the 1.6.0 import commits
    (`8847105`, `ac2b412`, `665657c`). The line counts match the KB: 1025 / 2272 / 1294 / 642.
  - **Core refs have drifted.** `WebControlPage.cpp` has 7 commits since 1.6.0, and `ApertarCoreApp.cpp` is now 11 493 lines.
    I re-grepped the WebUI anchors at `eb9cc39` (§3.1).

---

## 0. In one screen

1. **Patrik's decision** (CONFIRMED, kb:working/ramp-ladder/build/STATUS.md:22-25): "the WebUI playback mirrors the touch
   UI's clip browser and player; Cinemate gives the browser mechanics". Playback tutorials start at **T40**.
2. **Precedent** (CONFIRMED, core:`6ae70b5`, `87011d4` commit bodies). Twice already, Patrik settled a WebUI vs touch-UI
   disagreement the same way: the touch UI's model wins, and it moves into Core so the WebUI renders Core's answer.
   - "time left rounds down, like the touch UI"
   - "estimatedRawBytesPerSecond is the touch UI's per-frame model"
3. **Playback lives in the UI process today.** Every decoder sits in Apertar-UI: DNG/LJ92, MLV, and the FFmpeg movie plugin.
   Core has writers only. The WebUI is a C++ string inside Core and talks only to Core over HTTP. Sources: kb:architecture/overview.md:12,
   kb:architecture/ui.md:51-54, kb:llm/core-map.md:442-452 (CONFIRMED). So a WebUI player needs Core to read clips. Core has
   no reader for them today (PROBABLE: the KB's map of Core's small dirs lists only encoders).
4. **The WebUI already has a "Clip browser" overlay**: list, filter, sort, select, download, delete. It is backed by
   `GET /api/media`, but there is no frame view (CONFIRMED, kb:llm/core-map.md:170, :196, :218, :242-250; anchors re-found at
   `core:eb9cc39`, §3.1).
5. **Apertar's DNGs carry no embedded thumbnail** (PROBABLE, tip check). Cinemate's whole browser mechanism serves the DNG's
   IFD1 thumbnail and refuses to raw-decode (hb:lessons/hardware-log.md:1523-1532). So Cinemate's mechanics cannot be copied
   unchanged. They need either a thumbnail in Core's writer, which costs write bandwidth, or a server-side decode.
6. **Core's HTTP server is minimal** (CONFIRMED kb + tip check):
   - one thread per connection, at most 32 connections, 5 s socket timeouts;
   - `Connection: close` and `Cache-Control: no-store` on every response;
   - no Range support;
   - no authentication.
   Frame and audio serving must fit inside that.
7. **The WebUI has no event channel.** It polls `/api/state` once a second, and each poll is expensive. So Core's
   `hardware_action clip_browser` (a knob press) can reach the touch UI but not a browser (PROBABLE, §3.3).
8. **Takes a player must survive** (CONFIRMED kb):
   - frame-index gaps after drops;
   - 0-byte trailing DNGs and a raw-only audio file after a pulled card;
   - `.mp4.writing` files;
   - unrepaired ProRes;
   - MLV frame counts that are patched only at close;
   - if T31 is applied, speed-ramp takes with a constant `FrameRate` and an `fps-ramp.txt`.
9. **Cinemate's lessons** (CONFIRMED hb):
   - Gate playback while recording.
   - Derive per-clip facts from the file, never from live settings.
   - Fail loud.
   - Put a render token in frame URLs.
   - Expect stale pages after an update ("ask the API before the encoder").
   - A half-resolution thumbnail flatters image quality.
   - Every MJPEG `<img>` trap applies to any streamed `<img>`.
10. **House rules** (CONFIRMED kb):
    - tutorial first;
    - Patrik types every change and builds on the Pi;
    - no change commands without his ask;
    - nothing pushed;
    - labels and `path:line@commit` on every claim;
    - duplicated truths named.

---

## 1. Patrik's stated preferences and decisions

| # | Preference / decision | Source | Label |
| --- | --- | --- | --- |
| P1 | Brief: "port the playback function from cinemate, in the most Apertar like style" | kb:working/playback/r1-cinemate-playback.md:3 (quoting the brief) | CONFIRMED (as recorded) |
| P2 | Decision 2026-10-28: "make the playback in web ui similar to the current touch ui"; KB status: "Patrik's decision: the WebUI playback mirrors the touch UI's clip browser and player; Cinemate gives the browser mechanics." | kb:working/playback/r2-apertar-ui-player.md:3; kb:working/ramp-ladder/build/STATUS.md:22-25 | CONFIRMED |
| P3 | Playback tutorials start at T40, after reader reports, design, critiques and v2 | kb:working/ramp-ladder/build/STATUS.md:24 | CONFIRMED |
| P4 | When the WebUI and the touch UI disagree, the WebUI follows the touch UI, and the shared logic moves into Core. Patrik's own commits: `87011d4` "web: time left rounds down, like the touch UI" ("the HDMI display (touch UI) truncated 35.96 min to 35 while the WebUI showed 36"); `6ae70b5` "estimatedRawBytesPerSecond is the touch UI's per-frame model" | core:`87011d4`, `6ae70b5` commit bodies (author Patrik Eriksson, 2026-10-27) | CONFIRMED (commits); the general rule is PROBABLE (two instances) |
| P5 | A knob press that opens the clip browser is on his learning path (T13, "UI-only action", planned) | kb:llm/tutoring.md:89 | CONFIRMED |
| P6 | Hardware action `clip_browser` already has the alias **`playback`** (also `browser`) | kb:working/controls/r2-apertar-core-hw.md:355 | CONFIRMED (as recorded) |
| P7 | Adjacent WebUI preference: **keep** the WebUI "Camera settings" pane as a quick-access menu in the field ("it is not replaced") | kb:working/ramp-ladder/README.md:28-29 | CONFIRMED. That this extends to "add playback without replacing existing panes" is PROBABLE |
| P8 | Adjacent style pattern: "Cinemate-style, adapted to the Apertar style"; Patrik wants authored, ordered values rather than derived ones | kb:working/ramp-ladder/README.md:18; kb:working/ramp-ladder/r2-cinemate.md:205-206 | CONFIRMED (other projects) |
| P9 | His medium is exFAT on the CFE NVMe ("yes, lets keep exfat") | kb:lessons/hardware-log.md:61 | CONFIRMED |
| P10 | His shooting modes are 4K Clear HDR 16-bit at 25 fps (uncompressed) and 4K SDR 12-bit up to 50 (lossless). The player must handle both | kb:working/ramp-ladder/README.md:12-16; core:`eb9cc39` title "Clear HDR on = uncompressed, off = lossless" | CONFIRMED |
| P11 | He wants to learn by typing changes himself; the work stays off GitHub | kb:tutorials/README.md:3-5; kb:working/prompt-start-port-tutorials.md:4-7, :13; kb:working/ramp-ladder/build/STATUS.md:3 | CONFIRMED |

Nothing else in the KB states a playback-specific preference: wording, colour handling, audio, or which Cinemate extras he wants.
These are open for the design to ask (§9).

---

## 2. Apertar's touch-UI clip browser and player (what the KB knows)

### 2.1 Structure and flow

| Fact | Source | Label |
| --- | --- | --- |
| Clip playback is owned by the **UI** process (`apertar-ui-direct.service`), not Core | kb:architecture/overview.md:12 | CONFIRMED |
| Files: `cliplistmodel` (642), `playbackcontroller` (**1294**), `cdngimageprovider` / `dngdecoder` / `tiffhelper` / `RawPreview.hpp` (DNG decode incl. LJ92 via `third_party/liblj92`, thumbnails, CPU debayer), `VideoPlayback` + `MlvReader`, separate FFmpeg module `apertar-video-libav.so` | kb:architecture/ui.md:51-54 | CONFIRMED |
| Screens: `ClipBrowserPage.qml` (1025, "Clip grid over `/media/RAW`") and `ClipPlayerPage.qml` (2272, "DNG/MLV/movie playback") | kb:architecture/ui.md:67-68 | CONFIRMED |
| No StackView. `currentPage` = `"camera"` / `"browser"` / `"player"` plus Loaders. `CameraPage` is always alive | kb:llm/ui-map.md:169; kb:architecture/ui.md:280 | CONFIRMED |
| Browser Loader `active: currentPage === "browser"`, back goes to camera. Player Loader `"player"`, back goes to browser. `selectClip` sets `"player"` | kb:llm/ui-map.md:182, :186-187; kb:architecture/ui.md:288-289 | CONFIRMED |
| Entry points: the `clipBrowserBtn` on the camera page (`CameraPage.qml:3690`, signal `openClipBrowserRequested` `:9`), and the `hardware_action` router `clip_browser` (`Main.qml:320-321`) | kb:llm/ui-map.md:141, :164, :180 | CONFIRMED. Tip check: at `ui:d8098d0` `qml/Main.qml:319-322` toggles `currentPage = root.browserLayerVisible ? "camera" : "browser"` and closes settings |
| Browser: signals `backRequested`, `clipOpened`; `clipModel.browserOpen` follows visibility; refresh; sort toggle; multi-select delete via `clipModel.removeClip`; **clears the thumbnail cache on hide** | kb:sources/research-2026-10-25/ui-structure-notes.md:297-301 | CONFIRMED |
| Player chapters: header + back, `playerPanel`, `playbackImage`, fps chip, play state, `frameBadge`, info button, progress bar + handle. **Split landscape** has an info panel, controls and a histogram. **Compact/square** has a progress bar, `deleteButton`, histogram, `compactInfoButton` and `transportControls`. Then `clipRevealAnim`, the info overlay (`infoColumn`) and the delete confirm | kb:llm/ui-map.md:191-208 | CONFIRMED |
| Player API: only `playbackController` (`playing`, `frameCount`, `currentClipName`, `videoClip`, `currentFrameIndex`, `frameSource`, `fastFrameSource`, `histogramBins`, `clipMetadata`, `seekToFrame()`, `togglePlayback()`, `stop()`); signals back/previous/next/delete | kb:llm/ui-map.md:193, :198 | CONFIRMED |
| Image providers: `cdng` (exact frame), `cdngthumb` (96 items / 24 MiB), `cdngplay` (prefetching, `previewOnly`, 32 / 32 MiB), `video`, `videothumb`. Movie frames arrive via `frameDecoded` (queued) | kb:sources/research-2026-10-25/ui-structure-notes.md:112-120 | CONFIRMED |
| URL shapes: `image://cdngthumb/thumb?path64=…`, `image://cdng/frame?path64=…&token=`, `image://cdngplay/frame?path64=`, `image://video\|videothumb/frame?path64=&frame=` | kb:sources/research-2026-10-25/ui-structure-notes.md:305-309 | CONFIRMED |
| `ClipListModel` scans `/media/RAW`: DNG sequences, stills (dng/jpg/png/tif/tiff), MLV, movies | kb:sources/research-2026-10-25/ui-structure-notes.md:657-661 | CONFIRMED |
| `PlaybackController`: frames advance on a timer; DNG via `cdng` + `cdngplay`; histogram from `DngDecoder::decodeHistogramBins`; WAV sidecar search `<clip>.wav`, `<dir>.wav`, `audio.wav`, then any `*.wav`; audio streamed to an **`aplay` subprocess** | kb:sources/research-2026-10-25/ui-structure-notes.md:662-667 | CONFIRMED |
| MLV: Apertar's single-file uncompressed layout only. Movies: `isMovie` = mov/mp4/mlv; the plugin must be ABI `version==2` | kb:sources/research-2026-10-25/ui-structure-notes.md:670-671 | CONFIRMED |
| The movie plugin is built only if libavcodec/format/util/swscale are found. Lookup: `<app dir>/apertar-video-libav.so`, then `../lib/apertar-ui/`. Env override `APERTAR_VIDEO_PLAYBACK_PLUGIN` | kb:architecture/build.md:123, :130; kb:architecture/config.md:385 | CONFIRMED |
| Standby: on enter, stop playback, clear all three cdng caches, deactivate the video provider | kb:sources/research-2026-10-25/ui-structure-notes.md:108, :120-121; kb:architecture/ui.md:91 | CONFIRMED |

### 2.2 Bugs and limits recorded in the KB (and the UI README)

| # | Bug / limit | Source | Label |
| --- | --- | --- | --- |
| L1 | **`/media/RAW` is hard-coded** in `ClipListModel` (`cliplistmodel.cpp:174`), `MediaStatusBridge` and `SettingsBridge`. `[storage] mount_path` is honoured only by the automounter | kb:architecture/ui.md:440; kb:lessons/upstream-issues.md:33 (#26) | CONFIRMED [KB: open (desk)] |
| L2 | **Same flag, different meaning**: `standardLandscapeLayout` includes `landscape_large` in `ClipPlayerPage.qml:24-25` and Main, but not in SettingsPage | kb:llm/ui-map.md:580; kb:lessons/upstream-issues.md:32 (#25) | CONFIRMED [KB: open (desk)] |
| L3 | `updateVideoFrame` (`ClipPlayerPage.qml:141`) has a comment at `:146` on **decoder starvation** | kb:llm/ui-map.md:199 | CONFIRMED (that the comment exists) |
| L4 | UI README: "Playback is software-decoded, so large clips may **skip display frames** to keep the timeline moving, especially on older boards". ProRes/H.264 need the optional FFmpeg plugin. MLV supports only Apertar's single-file uncompressed layout. "Movie playback currently supports matching PCM16 WAV sidecars rather than embedded MOV audio" | ui:README.md:142-144@d8098d0 (tip check) | CONFIRMED |
| L5 | The KB generalises L4 to "**Only PCM16 sidecars are supported**". That is **too broad**: the controller accepts PCM (format 1) at any bit depth and 32-bit float. It starts `aplay -f` with `S24_3LE` / `S32_LE` / `FLOAT_LE` / `S16_LE` by the WAV's bit depth. The README sentence is about movie playback | kb:sources/research-2026-10-25/ui-structure-notes.md:666 vs ui:src/playbackcontroller.cpp:963-964, :996-1001@d8098d0 (tip check) | CONFIRMED (KB line is stale/over-broad) |
| L6 | The player and browser do **not exist in the monitor-only process**: `clipModel`, `playbackController` and the providers are absent there | kb:llm/ui-map.md:325-328 | CONFIRMED |
| L7 | The HDMI `ExternalMonitorWindow` shows only on the `"camera"` page (`ExternalMonitorManager.cpp:111-126`), so it is not shown while the touch UI is in browser/player | kb:architecture/ui.md:426 ("Add a page" row) | CONFIRMED (KB row). What HDMI then shows is UNCONFIRMED: look at HDMI with the player open |
| L8 | The touch UI blocks its GUI thread on slow Core commands, up to 60 s (`record_stop`) or 360 s (`format_media`). The player itself reads files directly, so this hits playback only through those commands | kb:lessons/upstream-issues.md:25 (#18); kb:llm/ui-map.md:579 | CONFIRMED [KB: open (desk)]. "Only through those commands" is PROBABLE (the player API in §2.1 calls no Core command) |
| L9 | `ClipPlayerPage.qml` is a "read only a chapter" file (2 200-2 500 lines) | kb:llm/README.md:46 | CONFIRMED |

The KB records **nothing** about these, so each is UNCONFIRMED (settle in r2 or on the Pi):

- whether the touch UI refuses the browser or player while recording;
- how it handles 0-byte DNGs or gaps;
- what it shows for a take with only `audio_capture.raw`.

Commands are in §9.

---

## 3. Apertar's WebUI today

### 3.1 What exists (KB anchors re-found at `core:eb9cc39`)

| Thing | KB (upstream-1.6.0) | At `eb9cc39` (tip check, CONFIRMED) |
| --- | --- | --- |
| Clip browser CSS `.media-browser*`, `.media-filter`, `.media-row`, `.media-stat` | `WCP:1122-1432` (kb:llm/core-map.md:170) | `.media-browser-title-row {` at `WebControlPage.cpp:1165` |
| Clip browser HTML `mediaBrowserOverlay`, `mediaBrowserList` | `WCP:3979-4031` (kb:llm/core-map.md:196) | `id="mediaBrowserOverlay"` at `:3979` |
| Clip browser JS: filter, sort, selection, render | `WCP:7511-7794` (kb:llm/core-map.md:218) | `sortedMediaItems` `:7596`, `renderMediaLibrary` `:7707`, delete call `:7824` |
| Fetchers `fetchMediaLibrary`, `deleteMediaLibraryItem`, `deleteSelectedMediaItems`, download | `WCP:10361-10444` (kb:llm/core-map.md:242-245) | `fetchMediaLibrary` `:10403`, `deleteMediaLibraryItem` `:10422` |
| 1 s state poll | `WCP:11609` (kb:llm/flows.md:48) | `:11652` |
| `GET /api/media` → `buildMediaLibraryJson` → `discoverMediaLibraryItems` | `App:7161`, `:7651-7710`, `:6282-6449` (kb:llm/core-map.md:61, :68, :420) | route `App:7307`; JSON `:7819`; scan `:6422` |
| Download / download-selected / delete / delete-selected | `App:7197`, `:7318`, `:7503`, `:7575` (kb:architecture/core.md:338-342) | `:7343`, `:7464`, `:7649`, `:7721` |
| Route list | kb:sources/research-2026-10-25/core-control-plane-notes.md:521-541 | Same set at `eb9cc39` (`App:7248-7783`): no frame, thumbnail, audio or range route exists |

Other KB facts about the WebUI that a playback pane would build on:

| Fact | Source | Label |
| --- | --- | --- |
| `/api/media` item fields: `id, kind, category, type, name, size_bytes, size_text, file_count, frame_count, duration_text, fps_text, modified_text, modified_ms, download_url`; plus `ok`, `mounted`, `media_root` | kb:sources/research-2026-10-25/core-control-plane-notes.md:429 | CONFIRMED |
| Clip library scan covers `Photos/`, `Audio/`, `Timelapse_*` and clip folders. Folder prefixes: `cDNG_`, `MLV_`, `H264_`, `cDNG_3to1_` / `cDNG_5to1_`, `ProRes_`, `Still_`, `Audio/Audio_` | kb:llm/core-map.md:61, :564 | CONFIRMED |
| **Not in the KB**: the WebUI list labels **every clip with the camera's current fps** (`settings.fps`), and computes cDNG durations as frame count ÷ that fps. Container clips (MLV/MOV/MP4) show duration `--` | core:src/ApertarCoreApp.cpp:7824, :6490-6493@eb9cc39 (tip check) | CONFIRMED (code). Consequence: a 50 fps clip listed while the camera is at 25 shows "25 FPS" and twice its real duration (PROBABLE arithmetic). The touch UI reads per-clip metadata (`clipMetadata`, §2.1), so the two lists disagree today |
| Media delete is refused while recording, sound-recording or in timelapse. It does **not** check `mediaWritesPending` or a running speed test, and it runs **outside** `commandMutex_` | KB: kb:sources/research-2026-10-25/core-control-plane-notes.md:538, :663 (#22); tip: core:src/ApertarCoreApp.cpp:7660, :7732@eb9cc39 | CONFIRMED (KB + tip). The KB line "checks `isRecording()` only" (kb:architecture/core.md:342) is now partly stale: the tip adds sound recorder and timelapse |
| Folder download streams a zip and needs the `zip` tool | kb:sources/research-2026-10-25/core-control-plane-notes.md:531 | CONFIRMED |
| WebUI page = one raw string compiled into Core, so **any WebUI edit needs a Core rebuild and restart** | kb:architecture/core.md:325; kb:architecture/build.md:63; kb:llm/README.md:107-108 | CONFIRMED |
| Icons are PNGs served **from disk** (`src/web/icons`, search order `App:2420-2440`), not compiled in. A new icon needs the file on the Pi | kb:architecture/build.md:54-63 | CONFIRMED |
| WebGL preview processing (peaking, zebra, false colour, exposure LUT) already exists in the page | kb:llm/core-map.md:220 | CONFIRMED |
| Settings overlay with 9 panels plus a sidebar | kb:llm/core-map.md:186 | CONFIRMED |

### 3.2 The HTTP server playback would run on

| Limit | Source | Label |
| --- | --- | --- |
| Bind `0.0.0.0:8000`, IPv4 only, backlog 16 | kb:sources/research-2026-10-25/core-control-plane-notes.md:508 | CONFIRMED |
| **Thread per connection, max 32**; `SO_SNDTIMEO` / `SO_RCVTIMEO` 5 s | kb:…/core-control-plane-notes.md:509; tip: core:src/web/WebServer.cpp:266, :271@eb9cc39 | CONFIRMED |
| 10 s request deadline; max request 1 MiB; `Transfer-Encoding` rejected | kb:…/core-control-plane-notes.md:510; tip: `WebServer.cpp:23` | CONFIRMED |
| **Every response** carries `Connection: close` and `Cache-Control: no-store`; streaming responses add `Pragma: no-cache` and have no `Content-Length` | kb:…/core-control-plane-notes.md:511; tip: `WebServer.cpp:127-154`@eb9cc39 | CONFIRMED. Consequences: every frame is a new TCP connection, and the browser cannot cache frames, so Cinemate's cache-friendly frame URLs would not cache here (PROBABLE). A handler can add headers, but `no-store` is always written first, so a second `Cache-Control` would conflict (PROBABLE, from `buildHttpResponse`) |
| **No Range support**: no `Range`, `Accept-Ranges` or `206` anywhere in `WebServer.cpp` or `ApertarCoreApp.cpp` | tip: grep at `eb9cc39` | CONFIRMED (absence by grep). Browsers' `<audio>`/`<video>` seeking normally relies on Range: PROBABLE (general web knowledge, not KB) |
| Path not percent-decoded except preset file names | kb:…/core-control-plane-notes.md:518 | CONFIRMED |
| **No auth**; only an origin check. A request without an `Origin` header passes. The README warns not to expose port 8000 | kb:…/core-control-plane-notes.md:512-516, :639 (#10); kb:lessons/upstream-issues.md:44 (#37) | CONFIRMED [KB: open (desk)] |
| MJPEG preview: max 640×360, 30 fps, JPEG q75. The downsample runs **on libcamera's completion thread** whenever a browser viewer is connected | kb:…/core-control-plane-notes.md:544-548; kb:working/compare-raw/b3-core-completion.md:27, :106 | CONFIRMED. A browser that leaves the live `<img>` streaming while it plays back keeps that cost on the camera (PROBABLE) |
| `/api/state` **per tab per second** shells out to `lsblk`, scans ALSA, re-reads UI.conf and reprograms the INA219 | kb:architecture/core.md:349; kb:…/core-control-plane-notes.md:670 (#26) | CONFIRMED |
| Standby stops the preview publisher and the MJPEG encoder | kb:…/core-control-plane-notes.md:138 | CONFIRMED |
| The WebUI pings `user_activity` only on `pointerdown`, at most once a second | kb:llm/core-map.md:237; kb:…/core-control-plane-notes.md:553 | CONFIRMED. A viewer watching a clip without touching the page sends no activity, so Core's idle timer can send the camera to standby mid-playback (PROBABLE). Settle on the Pi with a short standby timeout and a passive playback |

### 3.3 How the WebUI learns things

- The WebUI polls `GET /api/state` every second and sends commands via `POST /api/command`, then re-polls after 80-140 ms
  (CONFIRMED, kb:architecture/core.md:326-327; kb:…/core-control-plane-notes.md:552).
- It has **no socket and no event stream**. Events such as `hardware_action` go to socket clients (CONFIRMED,
  kb:architecture/overview.md:41, "Core → all socket clients").
- So a knob press mapped to `clip_browser` opens the touch UI's browser but cannot open a browser tab's playback, unless
  Core adds a state field (PROBABLE).
- Since `a070e1b` (in `eb9cc39`'s history, tip check), the `recording` event is broadcast at once
  (kb:lessons/hardware-log.md:420-428; kb:lessons/upstream-issues.md:51 #43). The WebUI still learns of a take start only
  from its next poll (PROBABLE, same mechanism).
- WebUI commands go through the same `handleCommand` and obey the same gates. Their events are broadcast to socket clients
  (CONFIRMED, kb:architecture/core.md:347).

---

## 4. What Apertar writes that a player must handle

| # | Fact | Source | Label |
| --- | --- | --- | --- |
| F1 | cDNG layout `<media>/cDNG_yy-mm-dd_C####/<clip>_#########.dng`. **The frame index comes from the timestamp, so drops leave gaps** | kb:architecture/core.md:425; kb:llm/flows.md:87, :91 | CONFIRMED |
| F2 | MLV: `MLV_…/<clip>.MLV`, single file, uncompressed. **Frame count patched at close**. Mono rejected | kb:architecture/core.md:427 | CONFIRMED. A take whose MLV never closed (pulled card) has a wrong header count (PROBABLE). `e8bb1b7` "abandon the MLV file on a dead medium" is in the tip's history |
| F3 | H.264: `<clip>.mp4`, written as `.mp4.writing` then renamed. No audio track (WAV sidecar) | kb:architecture/core.md:428 | CONFIRMED |
| F4 | ProRes: `<clip>.mov` + `_recovery.json`; **`ProresRepair` is never called** | kb:architecture/core.md:429; kb:lessons/upstream-issues.md:46 (#39) | CONFIRMED [KB: open (desk)] |
| F5 | Audio: `<clip>/<clip>.wav` built at stop from `<clip>/audio_capture.raw` (BWF `bext` + `iXML`). Capture formats S16, S24_3LE, S24, S32, FLOAT. Patrik's rig records **s24 stereo 48 kHz** | kb:architecture/core.md:432; kb:sources/research-2026-10-25/core-internals-notes.md:580; kb:lessons/hardware-log.md:456 | CONFIRMED |
| F6 | **A pulled take** (per-file fsync, `6fee0e4` / `7a545d9`, both in the tip) keeps readable DNGs to about 0.8-0.9 s before the pull. **The last ~21-23 DNGs exist with 0 bytes.** No WAV is built on a dead medium; `audio_capture.raw` is kept and `working/tools/raw2wav.py` makes `<clip>.recovered.wav` | kb:lessons/hardware-log.md:440-460 | CONFIRMED |
| F7 | Before `6fee0e4`, a pulled take left a folder whose 48 `.dng` names were **all 0 bytes** | kb:lessons/hardware-log.md:430-438 | CONFIRMED |
| F8 | T31 speed ramping (a patch, **not in `eb9cc39`**: no `fps_ramp` / `fps-ramp.txt` in `src/`, tip check) pins every frame's `FrameRate` and timecode to the take's start rate, numbers frames by count, and writes `fps-ramp.txt` into the clip folder | kb:working/ramp-answer.md:14, :73, :77; kb:llm/tutoring.md:107 | CONFIRMED (KB). If T31 is applied, a player reading the first frame's `FrameRate` plays a ramp as conform (slow motion), as intended. Count-based numbering then hides drops from a "span − files" counter (PROBABLE, from F1 + F8) |
| F9 | Sizes: 4K Clear HDR 16-bit = 16.59 MB/frame, 415 MB/s at 25 fps. 4K SDR 12-bit = 12.44 MB/frame | kb:working/ramp-mode-ladder.md:40-41 [KB: probable arithmetic] | CONFIRMED (as recorded) |
| F10 | This Pi's NVMe/exFAT: O_DIRECT `dd` 733-759 MB/s with 0 gaps; buffered 561 MB/s with gaps | kb:working/ramp-mode-ladder.md:46 | CONFIRMED |
| F11 | **No embedded thumbnail**: `CdngEncoder.cpp` contains no "thumbnail" string. IFD0 is written with `NewSubFileType` (254) = full resolution | core:src/cdng/CdngEncoder.cpp:1529@eb9cc39 (tip check) | PROBABLE (grep absence; no IFD1 writer found). Not recorded in the KB |
| F12 | Lossy DNG is written with `compression = LosslessJpeg` (tag 7), which the UI's decoder accepts (`COMPRESSION_NONE` or `COMPRESSION_JPEG`) | core:src/lossydng/LossyDngEncoder.cpp:509@eb9cc39; ui:src/dngdecoder.cpp:659@d8098d0 (tip check) | PROBABLE that lossy takes decode in the touch UI. UNCONFIRMED on the Pi |
| F13 | Core records with **no mount or free-space check**; with nothing mounted, files land in `/media/RAW` on the root filesystem. That is upstream behaviour; T28 added gates on `cinemate-port` | kb:architecture/core.md:419; kb:llm/tutoring.md:104 | CONFIRMED |
| F14 | Core's media root is `--media /media/RAW` (CLI); `/api/state` `media_label` says "/media/RAW" even when `--media` differs | kb:llm/flows.md:87; kb:…/core-control-plane-notes.md:653 | CONFIRMED |

---

## 5. Cinemate's playback: lessons recorded in the handbook and KB

### 5.1 What Cinemate's playback is (handbook)

| Fact | Source | Label |
| --- | --- | --- |
| Playback is a pane of the **settings editor** (`settings_editor_bp`), next to the RAW pane (`raw_files.py`: browse, download, delete, format takes). It does per-clip DNG/WAV frame serving for in-browser review and is "**gated off whenever a recording is in progress**" | hb:architecture/cinemate.md:79-83 | CONFIRMED |
| `playback.py` reads DNGs straight off the card (via `raw_files` / `dng_preview`) and serves frames over its own `/api/playback/clips` routes, "deliberately independent of Redis and `populate_values()`" | hb:working/changing-the-gui.md:95-99; hb:architecture/gui-state-model.md:10 | CONFIRMED |
| The RAW pane reads the filesystem directly (`storage_summary()`, `list_takes()`), not the live `SSDMonitor`, "so it can list and serve takes even when the monitor itself is unhealthy" | hb:architecture/cinemate.md:161-164 | CONFIRMED |
| JS-rewritten lock strings `pbLockBody` / `pbLockTitle` (the recording lock) stay in the template; all other pane prose lives in `resources/gui-text/*.md` | hb:working/changing-the-gui.md:67-83 | CONFIRMED |
| Per-clip `source` = `thumbnail` when `dng_preview.read_metadata()` finds an IFD1 chained after the raw image, else `decode` | hb:lessons/hardware-log.md:1522-1527 | CONFIRMED |
| `_RAW_DECODE_FALLBACK_ENABLED = False`: a thumbnail-less take **raises**, and the operator sees `NO EMBEDDED THUMBNAIL` | hb:lessons/hardware-log.md:1529-1532 | CONFIRMED |
| Frame URLs carry `playback.RENDER_TOKEN` (mixed from `dng_preview.py`'s mtime and size), so an updated decoder never serves a cached frame | hb:working/browser-side-traps.md:243-250 | CONFIRMED |
| Post-hoc drop count = (max index − min index + 1) − number of files; docs show "DROP N" | kb:working/compare-raw/a3-handbook-history.md:116, :183 (citing `playback.py:109-134@d6cc93e`) | CONFIRMED (as recorded) |
| Playback reads `FrameRate` from the take's **first frame only**; ramps replay as conform "with no rate logic" | kb:working/port-raw/r1-ramp-cinemate.md:57, :169; kb:working/ramp-answer.md:31 | CONFIRMED (as recorded) |

### 5.2 Lessons (each with what it means here)

| # | Lesson (handbook wording, shortened) | Source | Here (PROBABLE unless marked) |
| --- | --- | --- | --- |
| C1 | **Gate playback while recording.** Cinemate's pane is locked during a take | hb:architecture/cinemate.md:82-83 | Apertar's only existing gate is on media delete (§3.1). Reading 16.6 MB DNGs from the card that is taking 415 MB/s of writes competes for the medium. No KB measurement of read-during-write exists (UNCONFIRMED) |
| C2 | "**The file is the witness**, not the control that was supposed to configure it": per-clip facts come from the take's own file, never from live settings | hb:lessons/what-the-pi-taught-us.md:136-143; hb:lessons/hardware-log.md:1522-1527; kb:working/cinemate-lessons.md:31 | The WebUI list today breaks this: fps and duration come from the camera's current fps (§3.1, CONFIRMED code) |
| C3 | **Fail loud.** A missing thumbnail raised instead of silently decoding; "A silent degradation would have been a slower pane nobody filed" | hb:lessons/hardware-log.md:1529-1532; hb:conventions/philosophy.md:28-30 ("Fail visible, never silent … never shown a plausible wrong number") | A player should say why a clip will not play, for example a 0-byte frame, `.writing` or a missing plugin |
| C4 | "Playback wants a thumbnail on every take, and **raw decode on the Pi costs far more than serving one**" | hb:lessons/hardware-log.md:1579-1583 | Apertar has no thumbnail (F11). Choice: a Core-side decode and downscale per frame, or an IFD1 in Core's writer. The writer option costs bandwidth (C5) |
| C5 | Thumbnail cost, measured: colour shift 1 = 640×360, **691 200 B/frame, +4.0 % on 4K 16-bit ClearHDR**. Chosen because "320×180 is small for judging a take in the Playback pane, which is the pane's only path to a picture". JPEG mode 9-16 KB/frame but the highest CPU, so opt-in. Encode +4.0 ms/frame (+18 %) at 25 fps with four workers, zero drops | hb:architecture/cinepi-raw.md:147-157, :189-195; kb:working/compare-raw/a3-handbook-history.md:107, :181 | Numbers are Cinemate's (cinepi-raw writer), comparison only (kb:llm/README.md:118, trap 3) |
| C6 | "**The DNG thumbnail is half-res and will flatter you**": an agent's claim was made off it and was wrong | hb:lessons/hardware-log.md:2386-2420 | A reduced-size WebUI frame is fine for review, not for judging focus or HDR artefacts. The touch UI's `cdng` exact-frame path exists for that (§2.1) |
| C7 | "**A log line is only evidence if one build could have printed it**"; log values, not conclusions; prove the running binary has the feature | hb:lessons/what-the-pi-taught-us.md:122-134; hb:lessons/hardware-log.md:1565-1577 | Any playback log line should carry values (path, frame, ms) |
| C8 | **A stale page after an update.** The pane reported NO EMBEDDED THUMBNAIL on every take; a hard reload fixed it. "When the pane disagrees with the file, **ask the API before you read the encoder**"; "A render token on the payload does not protect the page that fetches it" | hb:working/browser-side-traps.md:243-276; hb:lessons/hardware-log.md:2064-2096 | Apertar sends `no-store` on `/` too (§3.2), so a stale page is less likely (PROBABLE). The "curl the API first" check still belongs in the tutorial's §7 |
| C9 | **Page-tab wiring**: the playback tab offered to save a `settings.jsonc` it did not edit, because five hand-kept mechanisms wire each page | hb:working/repository-and-tooling-traps.md:198-207 | Adding a pane to the WebUI's settings overlay or topbar has the same "missing association is silent" risk |
| C10 | "**A guard that reads the present cannot defend against a job that runs later**" | hb:lessons/what-the-pi-taught-us.md:194-211 | A recording gate checked when the page opens does not cover a take that starts mid-playback. The gate belongs in each frame/audio request, or playback must stop on the `recording` state |
| C11 | Erase/format raced the scanner; a recording guard was added. Destructive media ops need the recording guard and the intent flag | kb:working/cinemate-lessons.md:127 | Applies to delete from the player |
| C12 | Two dispatch paths, only one serialised; "do not assume two inputs cannot arrive at once" | hb:orientation/the-traps.md:19-27 | Apertar's analogue: WebUI media delete bypasses `commandMutex_` (§3.1) |
| C13 | Web GUI deltas measured at **~7.5 Hz**, not ~12; "don't design an animation or a fast-changing indicator around a higher number without measuring" | hb:working/changing-the-gui.md:17-22 | Measure frame delivery through Core's server on the Pi before choosing the browser player's frame rate |
| C14 | Web vs HDMI parity is a choice: integrity counts are raw numbers on HDMI and latched badges on the web, "a real capability difference, not an oversight … worth confirming deliberately" | hb:architecture/gui-state-model.md:21-26 | "Same information per clip" needs an explicit list of where the WebUI may differ |
| C15 | "Duplicated truth must be deleted, or carry a named reason *and* a check. A comment is not a check." "When this project routes, it wins" | hb:conventions/philosophy.md:80-91; kb:working/cinemate-lessons.md:28 | Clip type labels, durations and fps already exist in Core (`clipContainerTypeLabel`, `durationTextForFrameCount`) and in the UI (`cliplistmodel`, `playbackController.clipMetadata`). A WebUI copy would make a third (M5) |
| C16 | "Degrade in ladders whose last rung still produces a usable answer" | hb:conventions/philosophy.md:73; kb:working/cinemate-lessons.md:30 | e.g. exact frame, then a reduced frame, then metadata only with a reason |
| C17 | Things Cinemate got wrong, not to copy: a post-take verdict that counts a short DNG with size > 0 as present | kb:working/cinemate-lessons.md:139 | Relevant to F6/F7: a 0-byte or short DNG is not a frame |

---

## 6. Browser-side traps (handbook), mapped to Apertar

All are hb:working/browser-side-traps.md@c99ff77, "measured in a browser on real hardware" (:5-6), Chromium only, Safari
untested (:158). Each is CONFIRMED as recorded. The "Apertar" column is PROBABLE unless marked.

| Trap | Lines | Apertar |
| --- | --- | --- |
| An MJPEG `<img>` can be **accepted and then silent**, and that fires nothing (`error` never, `load` never) | :54-62 | Applies to any streamed `<img>` (a frame stream, or the live view returning after playback) |
| `load` fires **once per connection**, not per frame; clear the first-frame flag on every reconnect | :82-93 | Do not use `load` as a playback heartbeat |
| **Identical-URL `src` reset issues no request** (the browser joins the pending one). The fix is tear down, settle 250 ms, re-request; replacing the element does not help | :122-148 | Apertar's live view already uses a nonce URL `/preview.mjpeg?stream=<nonce>` (kb:llm/flows.md:153). Frame URLs need a unique part per request |
| A **cross-port** subresource can be refused outright | :42-50 | N/A while frames come from the same `:8000` origin as the page |
| **Do not add a cache-buster** to a server that does exact path lookups | :112-120 | Core's server splits path and query (`queryParameterValue` is used by routes, tip), so this is not the same server. Check before relying on it |
| **iOS has no Fullscreen API** except on `<video>`. Probe methods, never the user agent; hide a control that cannot work ("A button that appears to do something and does nothing is worse than no button") | :160-183 | A WebUI player drawing to `<img>` or `<canvas>` cannot go fullscreen on iPhone |
| `height: 100%` on a phone resolves against the large viewport; use `100dvh` with an `@supports` fallback. **Emulation cannot reproduce it** | :185-200 | Player transport rows at the bottom of a phone screen are at risk. Test on a real phone |
| CSS grid: `align-items` on the container squeezes the preview; a grid item's automatic minimum size is its content (cap with a definite `max-height`) | :202-241 | Applies to a player layout that mirrors the touch UI's split-landscape panel |
| "A missing event is not the same as a working stream"; "**A retry that runs is not a retry that happened**"; "**Measure the box, not the CSS**" | :278-296 | Verify recovery at the server (count connections), not by logging the retry |
| "None of these is checkable in CI today" | :298-300 | Apertar has no browser checks either (no KB mention). The Playwright mock used for T33/T34 (kb:working/ramp-ladder/build/STATUS.md:13) is the nearest tool |

Related stack trap: the web GUI has no state of its own and freezes with the HDMI draw loop (hb:orientation/the-traps.md:59-67).
That is Cinemate-specific. Apertar's WebUI polls Core directly (§3.3).

---

## 7. Every KB rule that constrains the project

| # | Rule | Source | Label |
| --- | --- | --- | --- |
| K1 | Label every claim **confirmed / probable / unconfirmed** (with the settling command). Every code claim has `path:line` against a named commit or release. Short sentences, tables over prose | kb:README.md:47-50; kb:llm/README.md:177 | CONFIRMED |
| K2 | **Tutorial first**: the skill does not make the change unless Patrik asks ("just do it") | kb:tutorials/README.md:3-5; kb:llm/tutoring.md:13, :17 | CONFIRMED |
| K3 | **Patrik types and builds every change himself.** Do not apply reference patches; do not edit, build or restart for him; give hints before answers (hint ladder) | kb:working/prompt-start-port-tutorials.md:4-7; kb:llm/tutoring.md:19-31 | CONFIRMED |
| K4 | **Builds happen on the Pi only**: the Mac cannot build (aarch64, Qt 6, libcamera 0.7) | kb:llm/README.md:132 (trap 17) | CONFIRMED |
| K5 | **Everything is compiled in**: the WebUI needs a Core rebuild + `sudo systemctl restart apertar-core`; QML is AOT-compiled, so a UI rebuild + `restart apertar-ui-direct` is needed. Editing QML and restarting without a rebuild does nothing | kb:llm/README.md:107-108, :119 (trap 4); kb:llm/change-recipes.md:22-25, :143 | CONFIRMED |
| K6 | New Core source files need `CMakeLists.txt` plus a cmake re-configure (`cmake -S . -B ../ApertarCore-build`); use `-j1` on 2 GB boards. A new touch-UI page needs `APERTAR_QML_FILES` **and** `qml.qrc` | kb:architecture/build.md:69-73 (rebuild block); kb:architecture/ui.md:426 | CONFIRMED |
| K7 | **Patrik alone runs sudo, reboots and edits `/boot/firmware/config.txt`** (task house rules). In the KB: tutorial checks are read-only (no `set_*`, no `sudo`, no `>`, no `git checkout`) | kb:tutorials/README.md:83; task brief | CONFIRMED (KB part) |
| K8 | **One front door**: touch, WebUI and hardware all end in `handleCommand` (M1). WebUI commands obey the same gates | kb:llm/README.md:99-100; kb:llm/tutoring.md:66; kb:architecture/core.md:347 | CONFIRMED |
| K9 | The socket parser is **flat**: scalars only; nested objects or arrays break it silently | kb:llm/README.md:122 (trap 7); kb:llm/change-recipes.md:45 | CONFIRMED |
| K10 | Every socket client receives **every** event, including per-frame `preview_frame`. Core drops clients whose buffer fills | kb:llm/README.md:123 (trap 8); kb:lessons/upstream-issues.md:26 (#19) | CONFIRMED [#19 KB: probable] |
| K11 | Any `set_*`, `record_*`, `capture_photo`, `format_media`, `eject_media`, `apply_preset`, `POST /api/config` is **a change: only when Patrik asked**. `get_state`, `/api/state` and file reads are fine | kb:llm/README.md:159-166 | CONFIRMED. `POST /api/media/delete` is a change by the same logic (PROBABLE) |
| K12 | Before telling Patrik anything works, **verify on the Pi with a read-only check**. Never `git checkout` / `reset` / `clean` on the Pi; a dirty tree may be his work | kb:llm/README.md:19; kb:llm/tutoring.md:44, :190 | CONFIRMED |
| K13 | **Copies (M5)**: state and option lists are hand-copied. One change, several places; name every copy | kb:llm/README.md:102-106; kb:llm/tutoring.md:70 | CONFIRMED |
| K14 | Cinemate findings are **comparison only**: shared vocabulary, not shared code paths | kb:llm/README.md:118 (trap 3) | CONFIRMED |
| K15 | The hardware log is append-only; an entry goes in only after **Patrik confirms the interpretation** | kb:README.md:51-52; kb:lessons/hardware-log.md:3 | CONFIRMED |
| K16 | Tutorial shape (sections 0-9), numbered steps, `%% tutor` block with `ref` and read-only `check` lines; checks must FAIL before the change; Obsidian frontmatter and tags; written on the Pi → `tutorials/inbox/` | kb:tutorials/README.md:12-33, :34-90; kb:llm/tutoring.md:118-132 | CONFIRMED |
| K17 | **Nothing is pushed**: "The work stays OFF GitHub"; "Nothing here is on Apertar-Core or Apertar-UI GitHub" | kb:working/prompt-start-port-tutorials.md:13; kb:working/ramp-ladder/build/STATUS.md:3 | CONFIRMED |
| K18 | Commit house format: area, imperative, Why, Tested; "No Co-Authored-By on his commits" | kb:llm/tutoring.md:41 | CONFIRMED. Discrepancy: Patrik's commits on the GitHub tips (`87011d4`, `6ae70b5`, `ui:160898c`) carry `What:` and `Co-Authored-By: Claude` (tip check). Ask which he wants |
| K19 | Find code via the chapter maps; never read `WebControlPage.cpp` / `ApertarCoreApp.cpp` whole; re-grep anchors on the **Pi tree** before writing a tutorial | kb:llm/README.md:18, :41-50; kb:llm/tutoring.md:124 | CONFIRMED |
| K20 | Media root is not one truth: the UI hard-codes `/media/RAW`, Core uses `--media`. A WebUI player served by Core and the touch UI could list different roots if they differ | kb:architecture/ui.md:440; kb:llm/flows.md:87 | CONFIRMED (facts). The consequence is PROBABLE |
| K21 | Keep port 8000 on a trusted network (no auth) | kb:lessons/upstream-issues.md:44 (#37) | CONFIRMED |
| K22 | Measure before you argue from resources; the Pi is the runtime truth; predictions written before a command runs | kb:working/cinemate-lessons.md:19-20; kb:llm/tutoring.md:30-31; hb:conventions/philosophy.md:22 | CONFIRMED |
| K23 | Mark every recipe or trace walked on the Pi as **confirmed** with the date. A new trap that bites goes into `llm/README.md` §5 | kb:llm/README.md:168-175 | CONFIRMED |

---

## 8. KB lines found stale or over-broad while reading (for the KB fixer)

| KB line | Says | Now | Label |
| --- | --- | --- | --- |
| kb:sources/research-2026-10-25/ui-structure-notes.md:666 | "Only PCM16 sidecars are supported (`README.md:144`)" | The README limits *movie* playback to PCM16 sidecars. The controller plays PCM 16/24/32 and float 32 (`ui:src/playbackcontroller.cpp:963-964`, `:996-1001`@d8098d0) | CONFIRMED |
| kb:architecture/core.md:342 | Media delete "checks `isRecording()` only" | Also checks the sound recorder and timelapse (`core:src/ApertarCoreApp.cpp:7660`, `:7732`@eb9cc39). Still no `mediaWritesPending` check, still outside `commandMutex_` | CONFIRMED |
| kb:llm/core-map.md WCP / App line numbers (§3.1) | upstream-1.6.0 lines | Shifted at `eb9cc39` (new lines in §3.1). Anchors still hit once | CONFIRMED |
| kb:llm/ui-map.md:180 | `clip_browser` at `Main.qml:320-321` | `Main.qml:319-322` at `d8098d0`. It toggles browser ↔ camera via `browserLayerVisible` and closes settings | CONFIRMED (the KB range is the body lines; no drift in the file) |
| (missing) | — | The WebUI clip list uses the **current** camera fps for every clip's fps and duration (`core:src/ApertarCoreApp.cpp:7824`, `:6490-6493`@eb9cc39) | CONFIRMED (code). Not in the KB |
| (missing) | — | Core's DNGs carry no IFD1 thumbnail (F11) | PROBABLE. Not in the KB |
| (missing) | — | Core's HTTP server has no Range support (§3.2) | CONFIRMED (grep). Not in the KB |

---

## 9. Questions the KB cannot answer (for the design)

| # | Question | Why it matters | Settle with |
| --- | --- | --- | --- |
| Q1 | Does the touch UI block the browser or player while recording? | Mirror its behaviour (P2), and Cinemate gates (C1) | `grep -n 'recording' ~/ApertarUI/qml/ClipBrowserPage.qml ~/ApertarUI/qml/ClipPlayerPage.qml ~/ApertarUI/qml/Main.qml` (r2 may already answer) |
| Q2 | How does the touch UI list and play a take with 0-byte trailing DNGs (F6), index gaps (F1), or only `audio_capture.raw` (F6)? | A WebUI clone must match or improve | Play `cDNG_26-10-27_C0001` (the pulled take, kb:lessons/hardware-log.md:452-460) on the touch UI if it is still on the card |
| Q3 | Does reading clips during a take cost frames? | Gate vs allow (C1) | `takes.sh 1 180` with a browser fetching frames vs without; compare queue peak and drops. Not measured anywhere in the KB |
| Q4 | Does passive playback let the camera fall into standby, on either surface? | §3.2 `user_activity` only on pointerdown | Short standby timeout, play a clip without touching, then read `get_state` `standby` |
| Q5 | What frame rate can Core's server deliver to a phone? | `Connection: close`, `no-store`, a 32-thread cap shared with MJPEG; Cinemate measured its web cadence at ~7.5 Hz (C13) | Measure on the Pi once a frame route exists: count frames per second in the browser's network panel |
| Q6 | Which per-clip fields must the WebUI show to count as "the same information" as the touch UI's info overlay? | P2, C14 | r2's report on `infoColumn` (`ClipPlayerPage.qml:1739`), then Patrik decides |
| Q7 | Colour: the touch UI's fixed render, or Core's `cdng_preview_color_profile` / LUTs? | Raised by r2 (kb:working/playback/r2-apertar-ui-player.md:721) | Patrik |
| Q8 | Audio in the browser: a Core-served WAV needs Range for seeking (§3.2). Or keep the touch UI's model (audio out of the Pi's own output via `aplay`)? | P2 vs browser mechanics | Patrik decides. Range support would be new Core code |
| Q9 | Which Cinemate extras does Patrik want as options (thumbnail mode in the writer, DROP N badge, conform-mode notes)? | P2 ("listed as options") | Ask him, with C5's costs |
