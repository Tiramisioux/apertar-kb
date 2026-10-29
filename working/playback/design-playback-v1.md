# WebUI playback in the touch UI's shape: how it works, what to build, what to measure first

2026-10-28, cloud session, designer pass (v1, resumed after Patrik's pause). Built from the four reader reports in this
folder (`r1-cinemate-playback.md`, `r2-apertar-ui-player.md`, `r3-apertar-core-media-web.md`, `r4-kb-playback.md`) and the
paused draft (`design-playback-draft-before-pause.md`). Every anchor and every load-bearing claim of that draft was reopened
in the code at the commits below; what changed is in §12. Read-only on every repository. Nothing ran on the Pi.

Host runs in this session (this machine, not the Pi): the sketch's round trip on Core-written frames (36 of 36 checks), the
parity test against the touch UI's own decoder and renderer (4 frames, 0 differing samples, 0 differing pixels), a **new**
lossy-DNG parity check on frames from Core's own `LossyDngEncoder` (2 frames, 0 differing), and the fuzz under ASan/UBSan
(480 runs, no sanitizer report). Sketch: `scratchpad/playback/sketch/` (Appendix A).

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `App`, `App.hpp`, `WS`, `Web`, `CP` | `src/ApertarCoreApp.cpp`, `.hpp`, `src/web/WebServer.cpp`, `src/web/WebControlPage.cpp`, `src/ipc/ControlProtocol.cpp` | Core, Patrik's GitHub `cinemate-port` tip `0296ed1` (`scratchpad/controls/core-tip`) |
| `CC`, `Cdng`, `IFD`, `LJE`, `Lossy`, `Mlv`, `CMake`, `H264C` | `src/camera/CameraController.cpp`, `src/cdng/CdngEncoder.cpp`, `src/cdng/IfdBuilder.hpp`, `src/cdng/LosslessJpegEncoder.cpp`, `src/lossydng/LossyDngEncoder.cpp`, `src/mlv/MlvEncoder.cpp`, `CMakeLists.txt`, `src/video/LibavH264EncoderClient.cpp` | same |
| `CBP`, `CPP`, `Main`, `CamP` | `qml/ClipBrowserPage.qml`, `qml/ClipPlayerPage.qml`, `qml/Main.qml`, `qml/CameraPage.qml` | touch UI, GitHub `cinemate-port` tip `5aab7e2` (`scratchpad/controls/ui-tip`) |
| `PC`, `CLM`, `CIP`, `DD`, `MLR`, `VP`, `VPL`, `VPA`, `UCMake` | `src/playbackcontroller.cpp`, `src/cliplistmodel.cpp`, `src/cdngimageprovider.cpp`, `src/dngdecoder.cpp`, `src/MlvReader.cpp`, `src/VideoPlayback.cpp`, `src/VideoPlaybackLibav.cpp`, `src/VideoPlaybackApi.h`, `CMakeLists.txt` | same |
| `cm:` | Cinemate `dev` | `d6cc93e` (`/home/user/tiramisioux/cinemate`) |
| `kb:`, `TP` | Apertar KB; `tutorials/tutorial.py` | `e8eeef2` (`/home/user/apertar-kb`) |
| `sketch/` | design sketch, in no repository | `scratchpad/playback/sketch/` |

Labels: **CONFIRMED** = I opened the line or ran the command in this session. **CONFIRMED (rN)** = reader N opened it; I did
not reopen it. **PROBABLE** = derived; the derivation is given. **UNCONFIRMED** = not checked, or only the Pi can settle it.

Tutorial numbers. T33-T35 are taken and the controls project uses T36-T45 (`scratchpad/controls/plan-summary.md`), so this
project starts at **T46** (Patrik may renumber). `tutorial.py` finds a note by `T` + two digits (`TP:98`, CONFIRMED), so no
"T48a". The KB status line "Tutorials start at T40" (`kb:working/ramp-ladder/build/STATUS.md:25`, CONFIRMED) needs a one-line
fix when this design lands.

| Number | What | Repo |
| --- | --- | --- |
| T46 | Measure first: what a frame costs on the Pi, what the touch screen shows today, what Core's server and your browsers do. No code | none |
| T47 | Core knows its clips: per-clip facts from the files (the list's FPS and duration fixed), `/api/media/clip`, `playback_hold` | Core |
| T48 | Core draws a frame: `/api/media/frame` for cDNG and stills, with the touch UI's look | Core |
| T49 | WebUI Clip Browser in the touch UI's shape | Core (page) |
| T50 | WebUI Clip Viewer | Core (page) + one gate |
| T51 | Sound: the WAV in the browser, HTTP Range in Core | Core + page |
| T52 | MLV clips | Core |
| T53 | ProRes and H.264 clips, with the touch UI's own movie decoder source | Core |

---

## 0. Short answer

1. The WebUI folder button opens a full-screen **Clip Browser** and **Clip Viewer** with the touch UI's layout, controls,
   flow, wording and nine metadata fields (`CBP`, `CPP`), drawn with the WebUI's shell, buttons, pills and badges. It
   replaces today's list overlay. Download, Select All and the Timelapse and Audio categories stay.
2. **Core decodes on demand** and sends one JPEG per request. The recording path and the DNG files do not change, so every
   take already on the card plays.
3. **Same picture as the touch screen.** Core gets a Qt-free copy of the touch UI's DNG rules, look and histogram, plus the
   same liblj92 file. On Core-written uncompressed, lossless and lossy 3:1/5:1 frames the copy gives 0 differing samples and
   0 differing pixels against the touch UI's own code. CONFIRMED (host).
4. **What it costs.** One 4K frame, one thread, this host: uncompressed 37-42 ms, lossy 70-85 ms (synthetic, a lower bound), lossless 159-189 ms. The
   touch UI's own path costs the same. The Pi is about 2× slower (PROBABLE). With two workers, Clear HDR 16-bit uncompressed
   should play near 25 fps if the NVMe link gives the reads; SDR 12-bit lossless shows about 5-8 fps with frames skipped,
   which is probably what the touch screen shows today. T46 measures both screens.
5. **Recording wins.** One Core function, `playbackHoldReason()`, answers for every frame and sound request: 409 in a take,
   while writes drain, during a media test, in standby, or with the media gone. A decode in flight stops at the next tile.
   `/api/state` carries the reason as `playback_hold`, and the viewer shows it in words. No playback read touches the card
   during a take.
6. **Sound plays in the browser** from the take's WAV, through one new route with HTTP Range. The `<audio>` element is the
   clock, as the touch UI's audio clock is.
7. **Shared with the touch UI:** the liblj92 file, the movie decoder's two source files (built by Core as one more lazy
   plugin, T53), and named copies of the render, histogram and text rules, kept honest by a parity test. **The touch UI does
   not change.** Eight small touch-UI fixes are listed as options (§5).
8. **Core's API** follows today's media library: HTTP routes under `/api/media/*` with `kind` + `id`. The list is fixed
   (each clip's own FPS and duration); new are `clip`, `frame` and `file` (Range); delete stays and gains the writes-pending
   gate. No new socket command, because every command runs under the camera's command lock (§2.7). **No change in
   `CameraController.cpp` or in any writer.**
9. **Not chosen:** Cinemate's recorder-written JPEG (IFD1). It adds work to every frame of a take on a record path that
   already drops lossless frames, it changes every DNG, and it shows the ISP preview look, not the touch screen's. A
   recorder-written preview track stays as option O11 if T46 says lossless playback is too choppy.
10. **Plan:** T46 measures, T47-T53 build, about 3,000 lines (PROBABLE), of which ~600 are written and host-tested in the
    sketch. Your calls first: **Q1** (is the lossless rate acceptable), **Q2** ("Show" only filters the list), **Q9** (which
    Cinemate options).

---

## 1. How the system works today

### 1.1 Operator view: three playback surfaces

| Surface | Where | What you get | What it lacks |
| --- | --- | --- | --- |
| Touch UI Clip Browser and Clip Viewer | Folder button on the camera page, greyed in a take (`CamP:3754`); or the hardware action `clip_browser` (`Main:319-322`) | Grid of 16:9 cards (2/3/4 columns), sort Newest/Oldest, long-press selection, Remove Selected. Viewer: preview with FPS, PLAYING/PAUSED and FRAME i / N badges; scrub bar; previous clip / play / next clip; Remove; 48-bar histogram; Clip Metadata (9 fields). Sound out of the Pi through `aplay`. Opens paused on frame 1, loops forever | Frame step, speed, loop toggle, a recording hold, a timecode, download. CONFIRMED (r2 §2-3); spot-checked `CBP:179`, `CPP:234`, `PC:749-775`, `CamP:3754` |
| WebUI Clip Browser | Folder button `mediaBrowserButton` in the top bar (`Web:2447`) | Centred 900×760 overlay: Clips / Stills / Timelapse / Audio filters, count pill, Refresh Media, sort select, rows with Download and Delete, Select All / Clear / Download Selected / Delete Selected (`Web:3979-4030`) | Thumbnails, any picture, any player. CONFIRMED |
| Cinemate Playback pane | Settings editor tab "Playback" | Take strip, black stage, filmstrip scrub, first/prev/play/next/last frame, loop, HUD, rate row (Achieved, Frames skipped), conform rate. Locked in a take | Sound, delete, the touch UI's shape. CONFIRMED (r1 §1) |

The WebUI list is wrong today in two ways a player would inherit:

- Every clip's FPS is the camera's **current** FPS, and a cDNG duration is frames ÷ that FPS (`App:6490-6493`, call site
  `App:7821-7824`). A 50 fps take listed while the camera is at 25 shows "25 FPS" and twice its length. CONFIRMED code; the
  example is arithmetic.
- MLV, H.264 and ProRes show duration `--` (`App:6490-6491`). CONFIRMED.

### 1.2 The model: the touch UI's flow today, step by step

| You do | You see | Code | Label |
| --- | --- | --- | --- |
| Tap the folder button | "PLAYBACK / Clip Browser", newest first; "Found 12 clip(s) in /media/RAW." | `ClipListModel` rescans `/media/RAW` on the GUI thread on every open (`CLM:443-586`); every thumbnail is a full raw decode (`CIP:733-743`) | CONFIRMED (r2 §4.1, §4.3) |
| Tap a card | "Clip Viewer", paused, "25.000 FPS", "PAUSED", "FRAME 1 / 250" | `selectClip` → `loadClip` (`Main:417-424`); paused on frame 0 (`PC:720`) | CONFIRMED |
| Play | frames at 75 % of the preview box; sound from the Pi's output | `sourceSize` 0.75 while playing (`CPP:393-398`); `aplay` (`PC:996`) | CONFIRMED |
| Wait | wraps to frame 1 and keeps playing | `% frameCount()` (`PC:567`) | CONFIRMED |
| Drag the bar | the frame follows the finger | `seekToFrame` on each move (`CPP:95-103`) | CONFIRMED (r2) |
| Remove → Remove Clip | the clip at the same index opens | `removeSelectedClip` (`Main:445-467`) | CONFIRMED |
| Back, Back | browser (rescanned, scrolled to top), then camera | Loaders rebuild the pages (`Main:580-640`) | CONFIRMED (r2 §1.3) |
| Someone starts a take | nothing changes on the open page; Remove still works | no `recording` use in either page (r2 §7) | CONFIRMED (r2) |

### 1.3 Code view: where clips, frames and sound come from today

| Step | Touch UI (`5aab7e2`) | Core / WebUI (`0296ed1`) | Cinemate |
| --- | --- | --- | --- |
| Clip list | `ClipListModel` scans `/media/RAW` itself (hard-coded, `CLM:174`), on the GUI thread; reads the **whole** first DNG of each take for its frame rate (`DD:1523-1530`, `readAll`) | `GET /api/media` → `discoverMediaLibraryItems(mediaRoot, fps)` walks and stats every file on each call (`App:6422-6497`) | index from first-frame tags, every 3 s (r1 §2.4) |
| A picture | full raw decode in the UI process: libtiff + liblj92, quad debayer, fixed look (`CIP:577-698`) | none: no reader, no decoder; the DNGs carry no preview (F1) | the JPEG cinepi-raw embeds in each DNG (IFD1), served as is (r1 §2.3) |
| Sound | `aplay` subprocess fed from the WAV (`PC:996`) | none | a WAV route nobody calls (r1 §0) |
| In a take | browser button greyed; hardware action, playback and delete not blocked (r2 §7) | media delete refused (`App:7660-7666`); downloads allowed | frames and WAV answer 409 (r1 §2.6) |

### 1.4 Facts every design must respect

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | Core's DNG: 8-byte header, payload at offset 8, IFD0 + EXIF at the **end**; `NewSubFileType` 0; next-IFD word 0. No thumbnail, no SubIFD | CONFIRMED `Cdng:1384-1392`, `Cdng:1525-1529`, `IFD:123` |
| F2 | Uncompressed payload: 16-bit little-endian, or 12/10-bit packed MSB first | CONFIRMED `Cdng:1155-1184`, `Cdng:1849-1858` |
| F3 | Lossless payload: SOF3, 2 components, full-width tiles of 128 rows (`APERTAR_CDNG_TILE_ROWS`). Lossy 3:1/5:1 = the same SOF3 coding of companded codes plus a `LinearizationTable` | CONFIRMED `Cdng:52-67`, `Cdng:1237-1241`, `Cdng:1540-1543`, `Cdng:1586-1588`; `Lossy:509`, `:527` (r3) |
| F4 | Clear HDR 12-bit cDNG is also stored as 12-bit codes with a `LinearizationTable`; Clear HDR 16-bit is linear, no table | CONFIRMED `CC:1348-1355`, `CC:3323-3328` |
| F5 | A frame's number comes from its timestamp, so a drop leaves a gap in the file numbers | CONFIRMED `CC:3780-3787`, `CC:4214-4221` |
| F6 | A new take takes the first free counter, so a deleted folder name can come back with new content | CONFIRMED (r3 §1.2, `CC:4169-4211`) |
| F7 | Every tag a player needs is in IFD0/EXIF at the tail: size, bits, compression, CFA, black/white, LinearizationTable, ColorMatrix1/2, ForwardMatrix1/2, AsShotNeutral, AnalogBalance, DateTimeOriginal, TimeCodes, FrameRate, PageName | CONFIRMED `Cdng:1529-1627`, `Cdng:1644-1652`; sketch reads them in one tail read of 1.4-9.8 KB |
| F8 | The web server: one detached thread per connection, max 32, 5 s socket timeouts, `Connection: close`, `Cache-Control: no-store` written **before** the handler's headers, no Range, reason phrases only for 200/204/400/403/404/405/413/500/503 (else "OK"). A handler exception is caught per client thread; a crash is not | CONFIRMED `WS:59-73`, `WS:127-154`, `WS:263-290` (catch at `WS:279-284`) |
| F9 | Every socket and `/api/command` command runs inside `handleCommand`, which holds `commandMutex_` for the whole command. HTTP routes such as `/api/media` do not | CONFIRMED `App:9485`, `App:7783-7788`; r3 §3.1 |
| F10 | Core's main binary links no libav; libav lives only in two lazily loaded plugins, opened with `RTLD_NOW \| RTLD_LOCAL` | CONFIRMED `CMake:69-131`, `CMake:140-170`, `H264C:105` |
| F11 | Core has TurboJPEG (FASTDCT) and a libjpeg fallback, used for the MJPEG preview, inside App's anonymous namespace | CONFIRMED `App:4165-4230`, `CMake:120-131` |
| F12 | The touch UI's decoders are Qt-bound (`QVector`, `QImage`, `QFile`), except **liblj92** (MIT, plain C) and the **movie decoder** (`VPL` + `VPA`: libav + swscale, C ABI v2, BGRA out, ≤ 1920 px, no Qt) | CONFIRMED `VPA:1-27`, `VPL:1-8`, `VPL:137-142`, `UCMake:136-146`; the Qt-bound list (r2 §12.3) |
| F13 | Clip folders: `cDNG_yy-mm-dd_C0001/<clip>_<9 digits>.dng`; `MLV_…/<clip>.MLV`; `H264_…/<clip>.mp4` (`.mp4.writing` in a take); `ProRes_…/<clip>.mov`; `<clip>.wav` beside any; containers carry no audio | CONFIRMED (r3 §1.2-1.3) |
| F14 | Signals a playback route can read without the command lock: `camera_.isRecording()`, `soundRecordingActive()`, `camera_.timelapseActive()`, `camera_.mediaWritesPending()`, `camera_.state()`, `mediaSnapshot()`, `mediaSpeedTestRunning_` (own mutex) | CONFIRMED `App:7857-7871` (the state builder reads them from the HTTP thread), `App:9487-9501`, `App.hpp:175-176` |
| F15 | `mediaGateError()` is skipped in simulate mode and with `APERTAR_MEDIA_REQUIRE_MOUNT=0` (a desk machine whose root is a plain folder) | CONFIRMED `App:9413-9418` |
| F16 | Media delete is refused while recording, sound recording or timelapse, but not while writes are pending | CONFIRMED `App:7660-7666`, `App:7732-7738` |
| F17 | Only commands count as activity for standby; the WebUI pings `user_activity` on pointerdown/keydown, at most once a second | CONFIRMED `App:9508-9514`, `Web:11546-11559` |
| F18 | The live MJPEG downscale runs on libcamera's completion thread while a viewer is connected; opening the media overlay does not stop it; the `<img>` error handler restarts the stream after 1.5 s | CONFIRMED (r3 §3.5) for the thread; CONFIRMED `Web:6176-6184`, `Web:8612-8616` |
| F19 | Touch UI player: opens paused on frame 0 ("FRAME 1 / N"), plays at 75 % of the box, loops, cDNG fps from the first frame clamped 1-60 (fallback 24), the audio clock drives frames when a WAV plays | CONFIRMED `PC:560-571`, `PC:619-621`, `PC:262`, `PC:760-775`, `CPP:393-398` |
| F20 | Touch UI histogram: 48 bins, ~16,000 raw samples on a square grid, step `floor(sqrt(N/16000))`, bin = (count/max)^0.65 | CONFIRMED `DD:488-536`, `PC:262-263` |
| F21 | On a 4K frame that step is 22, an even number, so every sample lands on the same CFA site (red in RGGB) | PROBABLE (arithmetic from F20, active area at 0,0) |
| F22 | Duration text differs in three places: touch card "00:12" / "01:02:03", rounded, "00:00" for no frames (`CLM:147-169`); touch metadata `mm:ss` / `hh:mm:ss` of the rounded milliseconds, "Unavailable" (`PC:135-146`); Core's list "1:02:03", "--" (`App:5887-5905`) | CONFIRMED |
| F23 | The touch UI writes the shot date with the Pi's **system locale** (`QLocale::system()`, "dd MMM yyyy  HH:mm") | CONFIRMED `CLM:76`, `PC:75` |
| F24 | Lossless 4K SDR at 25 fps already drops frames in the encoder; 30 fps is limited by libcamera's thread; memory traffic alone costs frames | CONFIRMED (r3 §4.1, `kb:lessons/hardware-log.md:87,108-113,158-165`) |
| F25 | NVMe on this Pi: 437 MB/s at PCIe Gen 2, 818 MB/s fio burst at Gen 3 (writes); a 16-bit 4K frame is 16.6 MB, so 25 fps of them is 415 MB/s | CONFIRMED `kb:lessons/hardware-log.md:140`, `:317-321`, `:383` |
| F26 | WebUI tokens and parts: `--surface #18181b`, `--surface-2 #111113`, `--card-border #27272a`, `--radius-xl 28`, `--radius-lg 22`, `--radius-md 18`, `--radius-sm 14`; `.badge` pills on the live preview; `.preview-center-card`; `.primary-/.secondary-/.danger-button`; accent `#3fd0ff` on `.standby-button`; breakpoints 1120 / 720 / 480 | CONFIRMED `Web:22-39`, `Web:443-451`, `Web:469-476`, `Web:1632-1690`, `Web:1664-1668`, `Web:2034`, `Web:2062`, `Web:2190` |
| F27 | The web icons `play`, `pause`, `next`, `previous`, `film`, `refresh`, `delete`, `info`, `folder` are byte-identical to the touch UI's | CONFIRMED (`cmp` of all nine) |
| F28 | `tutorial.py`: a check line is split on ` \| ` into exactly three fields; each pipe stage must start with a read-only command; `curl` may name only `ping`, `help`, `get_state`, `get_media_test_state`, `audio_capabilities`, `list_sensor_modes` | CONFIRMED `TP:42-49`, `TP:119-123`, `TP:167-200` |
| F29 | The controls project's T38 adds `case 409: return "Conflict";` to the same `reasonPhrase` | CONFIRMED `scratchpad/controls/design-controls.md:1283` |

---

## 2. The decisions

### 2.1 Where the picture comes from

| | A. Core decodes on demand | B. Recorder embeds a JPEG in each DNG (Cinemate, IFD1) | C. Recorder writes a preview track per take | D. The touch UI serves frames | E. The browser decodes raw | F. The touch UI's code in a helper process |
| --- | --- | --- | --- | --- | --- | --- |
| Change in the recording path | none | per-frame JPEG in the copy worker; preview buffers mapped in raw mode; IFD0 next-IFD patched in the uncompressed template and the lossless path (r3 §2.2) | per-frame JPEG + one appended file per take | none | none | none |
| Takes already on the card | all play | only new takes | only new takes | all | all | all |
| DNG files | unchanged | changed (+10-25 KB, chained IFD1; Resolve/Adobe acceptance UNCONFIRMED, r1 §3.2) | unchanged | unchanged | unchanged | unchanged |
| Look | **the touch screen's** (same rules, §2.3) | the ISP preview look | the ISP preview look | the touch screen's | whatever the page codes | the touch screen's |
| 4K lossless playback rate | low (PROBABLE ~5-8 fps on the Pi, two workers) | full | full | low, in the UI process | impractical: 7.7-16.6 MB a frame over Wi-Fi | low |
| MLV / movies | yes (T52, T53) | no | yes | yes | no | yes |
| Front door | Core | Core | Core | **the UI process** (no HTTP server, no frame command, absent in monitor-only mode, r2 §12.3, r4 L6) | Core serves files only | a second process beside Core, with Qt |
| Main risk | decode code inside Core's process (R6) | the hot path of every take (F24) | the hot path of every take | breaks "Core is the one front door" | — | a new service, IPC and Qt on Core's side |

**Recommendation: A**, with C kept as option O11.

- A changes nothing that can cost a take. The record path is at its limit (F24). Cinemate measured +4.0 ms (+18 %) of encode
  per frame for its JPEG (r1 §3.3), and Apertar's lossless path is already the bottleneck at 25 fps.
- A plays every take already on the card, with the touch screen's look. That is what "similar to the touch UI" asks, and B
  or C would show a different picture on the phone than on the touch screen.
- A's weak point is lossless 4K. The touch UI has the same weak point today (§2.3). If T46 shows it is too choppy for you,
  O11 (C) fixes it for both screens at once, because both could read the preview track.
- C over B, if it is ever built: the DNGs stay byte-identical (no Resolve question) and MLV and movies are covered too.
- D, E and F are rejected for the reasons in the table. F would avoid the copies, but it adds a long-running Qt process
  beside Core only to keep one render rule in one place; the parity test does that job (§2.4).

### 2.2 How the picture travels to the browser, and how it is paced

| | 1. One JPEG per request, fetched by the page (chosen) | 2. A playback MJPEG stream paced by Core | 3. `<video>` | 4. WebSocket |
| --- | --- | --- | --- | --- |
| Works with Core's server as it is | yes (buffered body, `Content-Length`) | yes (the live preview does it) | needs Range; H.264 only | no WebSocket in Core |
| Per-frame data (index, histogram, decode time) | in response headers | no | no | — |
| Sync with the browser's audio clock | the page asks for the frame the audio clock wants | Core's clock drifts from the phone's audio clock; every pause or seek is a new stream | native | — |
| Skips under load | the page skips (503 → next frame) | Core drops | native | — |
| Browser traps | few | every MJPEG `<img>` trap (silent stream, `load` once per connection; r4 §6) | iOS fullscreen only here | — |

Chosen: **1**, Cinemate's mechanism (r1 §2.1), with three Apertar changes:

- The page uses `fetch()`, not `<img src>`, so it can read the headers (`X-Frame-Index`, `X-Histogram`, `X-Decode-Ms`) and
  draw into a `<canvas>` only when a frame is decoded (`createImageBitmap`). The old frame stays until then, as the touch
  UI's `retainWhileLoading` does (r2 §3.2). Same origin, so every header is readable (PROBABLE, standard fetch rules).
- **The clock wins.** With a WAV, `audio.currentTime` is the clock; without, a wall clock. The wanted frame is
  `floor(clock × fps)`. The page keeps two requests in flight (one per Core worker) and asks **ahead** by the measured
  round trip, so a frame arrives near its due time. A frame that arrives late is drawn only if it is newer than the one on
  screen. A 503 skips that frame and never pauses (Cinemate's client pauses, r1 §5.5).
- **No HTTP caching.** Core keeps `Cache-Control: no-store` on every response (F8). Revisits are cheap anyway: Core keeps
  the JPEGs it made in a 32 MB memory LRU, and the page keeps the thumbnails it fetched in memory while it is open. This
  avoids touching the header code of every response (the paused draft's medium-risk row; §12).

### 2.3 What the sketch measured (this host, not the Pi)

The sketch (`sketch/`, Appendix A) has three parts. `src/playback/DngFrameReader.hpp` (372 lines) reads Core's DNGs without
Qt or libtiff. `src/playback/RawRender.hpp` (226 lines) copies the touch UI's look (`CIP:380-698`) and histogram
(`DD:455-536`). `third_party/liblj92` is the touch UI's file, checked identical with `cmp`.

**Correctness**, on frames written by Core's own encoders (`CdngEncoder`, and `LossyDngEncoder` for 3:1 and 5:1):

| Check | Result | Label |
| --- | --- | --- |
| Reader round trip, 12/16-bit × uncompressed/lossless: size, bits, compression, FrameRate 25, PageName, DateTimeOriginal, matrices, every sample bit-exact | 36 of 36 | CONFIRMED (run in this session) |
| Tags cost one read of the file's tail | 1,448 B uncompressed, 1,596 B lossless, 9,820 B lossy (the 4,096-entry table) | CONFIRMED |
| The same frames through the **touch UI's own** `DngDecoder` + `renderRawFramePreview` (Qt 6 on this host) vs the copy | 6 frames (4 + 2 lossy): samples differ 0; 640x360 pixels differing 0; histogram max bin difference 0.0000 | CONFIRMED (`sketch/parity/parity_test`, `sketch/lossy/`) |
| Fuzz: 480 truncated or byte-flipped copies, AddressSanitizer + UBSan | 303 rejected with an error, the rest decoded, no sanitizer report | CONFIRMED |
| Lossy BIT DEPTH: the copy reads the stored 12 bits; the touch UI reports 16 after applying the table | the difference D9 is real | CONFIRMED (bench prints "12-bit", parity shows white 65535 in both) |

**Cost per frame, one thread, warm page cache** (Xeon 2.1 GHz, 4 threads; synthetic scene with sensor-like noise; the
synthetic lossy frame compresses to 1.0 MB, far smaller than a real scene, so its time is a lower bound):

| Frame | Payload | Read + unpack/decode | Render 640 w | Render 1920 w | Histogram | JPEG q80 | One 640 w frame | Per worker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4K SDR 12-bit uncompressed | 12.4 MB | 19.5 ms | 15.5 ms | 142 ms | 0.15 ms | ~1.5 ms (26.5 KB at 960 w) | 37-40 ms | 25-27 fps |
| 4K SDR 12-bit lossless | 7.7 MB | 139 ms | 18.2 ms | 147 ms | 0.17 ms | ~1.5 ms | 159-168 ms | 6.0-6.3 fps |
| 4K SDR 12-bit lossy 3:1 / 5:1 (synthetic) | 1.0 MB | 72 / 57 ms | 11 ms | 100-108 ms | 0.14 ms | ~1.1 ms | 85 / 69 ms | 12-15 fps |
| 4K Clear HDR 16-bit uncompressed | 16.6 MB | 22.7-23.2 ms | 16.2-16.7 ms | 160 ms | 0.15 ms | ~1.6 ms | 41-42 ms | 24-25 fps |
| 4K 16-bit lossless | 15.4 MB | 154-156 ms | 15.5-15.9 ms | 132-137 ms | 0.15 ms | ~1.3 ms | 171-189 ms | 5.3-5.8 fps |
| The touch UI's own path, same files | | decode 17-19 ms uncompressed, 167-170 ms lossless | render 19-25 ms (640x360) | | | | | |

All rows CONFIRMED on this host (`sketch/results-host.txt`; two re-runs in this session gave the same picture, ±10 %: e.g. 40 ms and 168 ms for the SDR rows, 189 ms for 16-bit lossless). For the Pi (PROBABLE, not measured):
a Pi 5 core with its memory is roughly half as fast as this one for this memory-heavy work, and a cold 16.6 MB read from NVMe
adds 24-40 ms (F25). So about 55-100 ms per uncompressed 640 w frame (two workers: ~20-35 fps) and 250-450 ms per lossless
one (two workers: ~5-8 fps). T46 measures it with the same tool on your takes.

### 2.4 What is shared with the touch UI, and what is not

| Thing | Shared how | Why |
| --- | --- | --- |
| Lossless JPEG decoder | **Same file**: `ApertarUI/third_party/liblj92/{lj92.c,lj92.h,LICENSE,README.apertar.md}` copied to `ApertarCore/third_party/liblj92/`; `cmp` shows it identical | Plain C, MIT, already carries the touch UI's local fix (`README.apertar.md`). Copying a vendored file is how both repos already work |
| Movie decoder (ProRes, H.264) | **Same source files**: `VPA` and `VPL` copied byte-identical into Core's `src/playback/` and built by Core's CMake as `apertar-video-libav.so`, a third lazy plugin next to its two encoder plugins (T53) | Qt-free, versioned C ABI (F12). Core already loads plugins this way (F10). A copy built in Core's tree does not break when only Core is rebuilt or the UI is not installed. Loading the touch UI's installed `.so` instead is Q16 |
| DNG reading, render look, histogram, metadata text, clip rules, MLV rules | **Named copies** in `src/playback/*.hpp`, each with a comment naming its touch-UI source, plus a parity test in the KB that builds both on the Pi | The touch UI's versions are Qt-bound (F12). KB rule M5: name every copy and give it a check (`kb:llm/README.md:102-106`, r4 K13). The parity test exists and passes (§2.3) |
| Decoding work | **Not shared.** The touch UI decodes for the touch screen in its own process; Core decodes for browsers | Two screens may play at once; each has its own budget (R12) |
| Thumbnails | **Not shared** by default. Core renders and keeps its own in memory | Option U4 lets the touch UI load Core's (one cache) |
| Toolkit, layout code | Not shared: QML vs HTML/CSS/JS | Different runtimes; the design copies the layout and the words, not the code |
| Sound | Not shared: `aplay` on the Pi vs `<audio>` in the browser | The WebUI viewer is on your phone or laptop |
| Media root | Not shared today: touch UI `/media/RAW` hard-coded (`CLM:174`), Core `--media` | The same folder on your Pi (PROBABLE); every reply names `media_root` (R9) |

### 2.5 Formats

| Item | Picture in the WebUI | Facts | When |
| --- | --- | --- | --- |
| cDNG uncompressed, lossless, lossy 3:1/5:1, Clear HDR 12-bit companded | Core decode (§2.1 A) | first frame's tail (F7) | T47, T48 |
| Timelapse folder of DNGs | same decoder; plays at the first frame's FrameRate, fallback 24, like the touch UI (`PC:262`) | same | T48 |
| DNG still | same decoder, one frame | same | T48 |
| JPEG still or JPEG timelapse frame | TurboJPEG decode at 1/2, 1/4 or 1/8 scale, then a JPEG at the asked width | file size, date | T48 |
| PNG / TIFF still | "NO PREVIEW" (the WebUI cannot show them yet) | file | later |
| MLV (single file, uncompressed) | Core reads frame N through a block index built once per clip (a named copy of `MLR:153-278`), rendered with the touch UI's MLV "ISP" path (`CIP:655-662`, r2 §5) | MLVI/RAWI header | T52 |
| MLV not finalized (count 0) | not playable: "MLV is not finalized or its frame count is invalid." (`MLR:176-177`) | | T52 |
| ProRes `.mov`, H.264 `.mp4` | Core's copy of the movie plugin gives BGRA frames ≤ 1920 px; Core encodes JPEG | plugin `probe` | T53 |
| `.mp4.writing`, ProRes without `moov` | not playable, with the reason | | T53 |
| Sound recording (`Audio/…/*.wav`) | no picture; the viewer plays the sound | WAV header | T51 |

Why the plugin for H.264 too, and not `<video>`: one viewer path, exact frame numbers for "FRAME i / N", the same histogram
as the touch UI, and the same hold rule. `<video>` would decode on the phone for free; it is option O12.

### 2.6 Sound

- The browser plays the take's WAV through one `<audio>` element. Core serves it on `/api/media/file` with **HTTP Range**
  (206, `Content-Range`, `Content-Length`, `Accept-Ranges: bytes`). Range is needed to seek, and Safari plays media only from
  servers that answer Range (PROBABLE, general web knowledge; T46 M6 checks your browsers).
- `audio.currentTime` is the clock: frame = `floor(currentTime × fps)`. The touch UI does the same with its audio clock
  (`PC:769-772`). Without a WAV a wall clock runs.
- A paused `<audio>` stops reading. Core's 5 s send timeout then closes the connection (F8), and the browser resumes with a
  new Range request (PROBABLE). That is why Range comes with sound, not later.
- WAV search order as the touch UI: `<clip>.wav`, `<dir>.wav`, `audio.wav`, then any `*.wav` by name (r2 §4.2).
- Your WAVs are s24 stereo 48 kHz with `bext` and `iXML` chunks (`kb:lessons/hardware-log.md:456`, r4 F5). Browser support
  for them is UNCONFIRMED: T46 M6. If a browser refuses one, the viewer plays silently with a one-line notice (O13 would
  serve a 16-bit copy). RF64 starts only above 4 GB (about 4 h of s24 stereo), so it does not matter here (PROBABLE).
- MLV-embedded audio does not exist in Core's files (`kAudioClassNone`, r3 §1.3).

### 2.7 Interlocks: recording, standby, pulled media

One Core function, `playbackHoldReason()`, answers for every playback route and for `/api/state`. It reads only the signals
in F14, so it never waits for the command lock.

| Order | Condition | `playback_hold` | Why |
| --- | --- | --- | --- |
| 1 | `camera_.isRecording() \|\| soundRecordingActive() \|\| camera_.timelapseActive()` | `recording` | reading the card during a take competes for the same memory and drive (F24, F25) |
| 2 | `camera_.mediaWritesPending()` | `writing` | the last take is still draining; Cinemate also holds on buffer flush and pre-roll (r1 §2.6) |
| 3 | `mediaSpeedTestRunning_` | `media_test` | a speed test measures the drive; reads would spoil it |
| 4 | `camera_.state() == CameraState::Standby` | `standby` | the touch UI stops playback in standby (r2 §1.1); the governor is on powersave (r3 §4.4) |
| 5 | the watcher says the media is not mounted and answering (`!mediaSnapshot().mounted()`), unless the media gate is switched off (F15) | `media` | a pulled NVMe can block reads for 30-60 s (r3 §4.5) |
| — | otherwise | `""` | |

Rules:

- The check runs **in each request**, before a decode slot is taken, not when the page opens (Cinemate lesson C10: a guard
  that reads the present cannot defend against a job that starts later; r4 §5.2).
- **A decode in flight stops.** The reader checks a hold flag between tiles (lossless, 128 rows) or every 128 rows
  (uncompressed) and gives up with 409. At most one tile is read after a take starts (PROBABLE: 128 rows of 4K 16-bit is
  ~1 MB).
- **Memory goes back.** When a hold starts, or after 30 s with no playback request, the workers free their scratch buffers
  (~33 MB each for 4K 16-bit). The JPEG LRU (32 MB) stays, so thumbnails survive a take.
- **Recording is never refused because someone is watching.** Playback yields; no record gate changes.
- **The list** (`/api/media`) is not refused in a hold. It answers from its cache with `"held":"recording"` and reads
  nothing on the card. Cinemate's index was never gated and scanned during takes (r1 §5.5); this fixes that.
- **Delete** gains the `writing` check (F16), with Core's existing words "Wait for the current capture to finish writing to
  media." (`App:9489`).
- **The WebUI folder button is greyed in a take**, like the touch UI's (`CamP:3754`). An open browser or viewer stays open
  and shows the hold.
- **Standby:** while a clip **plays**, the page sends `user_activity` every 20 s, so watching counts as use (F17). Paused,
  it does not, so a forgotten tab does not keep the camera awake.
- **No socket command.** A `get_clip_info` command would run inside `handleCommand` under `commandMutex_` (F9). On a pulled
  NVMe its folder read could block for 30-60 s, and `record_stop` would wait behind it. The HTTP routes run on their own
  client threads. `tutorial.py` would also refuse a check that calls it (F28). If the touch UI ever takes its facts from
  Core (U8), it reads the same HTTP route on `127.0.0.1:8000`.

### 2.8 CPU and I/O budget on the Pi 5

| Situation | Playback work allowed | Cost (PROBABLE unless marked) |
| --- | --- | --- |
| **A take**, sound recording, timelapse, writes draining, media test | **none**: frames, thumbnails and sound answer 409; the list answers from memory; a decode in flight stops at the next tile | ~0 on the card and the CPU. What remains is today's 1 s `/api/state` poll per open tab (CONFIRMED mechanism, r3 §4.1) and one 409 reply per page poll cycle |
| Standby | none (409) | 0 |
| Idle, browser open, thumbnails filling | ≤ 2 decodes at once, at nice 10, results kept in the LRU | one decode per card the first time: ~0.1 s uncompressed, ~0.3-0.4 s lossless; 50 takes ≈ 5-10 s to fill the grid once after a Core start; then memory |
| Idle, playing 4K Clear HDR 16-bit uncompressed at 640 w | 2 workers | ~1.5-2.5 cores; 415 MB/s of reads at 25 fps, at the Gen 2 link limit (F25), so the rate may be read-bound. Heat: T46 M1 |
| Idle, playing 4K SDR 12-bit lossless | 2 workers | 2 cores busy, ~5-8 fps shown, frames skipped; ~40-60 MB/s of reads (only decoded frames are read) |
| Idle, paused | one frame at the stage's size (≤ 1920 w) | ~0.3-0.6 s of one core per pause |
| Live preview while the overlay is open | **stopped** by the page | removes the MJPEG downscale from libcamera's thread (F18) |
| Memory | | ~33 MB of scratch per worker + 6 MB of RGB + the 32 MB LRU: ~110 MB at most of 4 GB; the scratch (~70 MB) is freed on a hold (above) |

Knobs, read once at start like `APERTAR_CDNG_TILE_ROWS` (`Cdng:52-67`): `APERTAR_PLAYBACK_WORKERS` (default 2, range 1-3) and
`APERTAR_PLAYBACK_CACHE_MB` (default 32). A worker lowers its own thread priority for the decode with
`setpriority(PRIO_PROCESS, gettid(), 10)`, so camera threads win when both run. Nothing needs restoring: the web server
makes a new thread per connection and it ends with the response (F8), and an unprivileged thread could not raise its
priority again anyway (PROBABLE, Linux nice rules; Core's privileges on the Pi are UNCONFIRMED).

### 2.9 Where the WebUI deliberately differs from the touch UI

| # | Touch UI | WebUI | Why | Ask |
| --- | --- | --- | --- | --- |
| D1 | "CAPTURE / Clip Mode · Still Mode" switches the **camera's** photo mode (`CBP:115-119`) | Same place and look, labelled "SHOW / Clips"; it opens a small menu Clips · Stills · Timelapse · Audio and only filters the list | A list filter should not change the camera from a phone; the WebUI already has four categories | Q2 |
| D2 | "1 ITEMS" | "1 item" | wording bug (r2 §10 #4) | Q7 |
| D3 | no download, no select all | Download (in the viewer, and for a selection) and Select All kept from today's WebUI browser | existing WebUI features (r4 P7: keep what the WebUI has) | Q3 |
| D4 | long press only | long press (800 ms) everywhere; with a mouse, the selection badge also shows on hover and a click on it starts selection | a mouse has no comfortable long press | — |
| D5 | live refresh by a file watcher | refresh on open, on Refresh, after a delete, and when a take ends | no event channel to the browser (r4 §3.3) | — |
| D6 | no hold in a take | hold with a named reason (§2.7) | Cinemate's mechanic; the brief asks for its mechanics | Q4 |
| D7 | sound out of the Pi | sound out of the phone or laptop | the viewer is remote | — |
| D8 | without a WAV, a slow decode stretches time (`PC:774`, tick-driven `nextFrame()`) | a wall clock runs and late frames are skipped | over Wi-Fi a stretched clock makes the length meaningless | Q8 |
| D9 | BIT DEPTH "16-bit" for any DNG with a LinearizationTable (§2.3) | the stored depth from tag 258, e.g. "12-bit", plus "companded" when a table exists | the file is the witness (r4 C2) | Q6 |
| D10 | Back rebuilds the browser: rescan, scroll to top | Back returns to the same grid and scroll | the page keeps the grid in memory | — |
| D11 | 4K histogram samples one CFA site (F21) | copied as is, so both screens draw the same bars | parity first; fix both later (U6) | Q7 |
| D12 | no keys | Space plays/pauses, Escape closes (Escape already closes the overlay, `Web:11620`) | a laptop has a keyboard; frame-step keys are O1 | Q18 |
| D13 | no Timelapse or Audio category | kept from today's WebUI; sound recordings play sound only | today's WebUI lists them (`Web:4000-4003`) | Q3 |
| D14 | the hardware action `clip_browser` opens the touch browser | not delivered to browsers | Core broadcasts events only to socket clients (r4 §3.3) | — |

### 2.10 What each measurement would change (T46)

| Result | Then |
| --- | --- |
| M1: uncompressed 16-bit 640 w frame ≤ 80 ms per worker on the Pi | defaults stand: 2 workers, play at 640 w |
| M1: > 80 ms | play at 480 w (the touch UI's square layout plays ~459 px wide: 612 × 0.75, r2 §3.1); try 3 workers |
| M1 `--cold`: the read dominates | read only the rows the render needs (~2/3 of the strip at 640 w); M8 tells whether the link is the limit |
| M1: lossless ≤ 4 fps with 2 workers, and M2 shows the touch screen as choppy too | offer O11 (preview track) now; else keep it as an option |
| M3: < 40 small requests/s through Core's server | ask ahead by one frame only; keep-alive becomes its own task |
| M6: a browser cannot play the s24 WAV | O13: Core serves a 16-bit copy |
| M5: standby comes during passive playback on the touch UI too | U2 adds `user_activity` while playing on the touch UI |
| M7: reading an old take during a take costs no frames | cached thumbnails could be allowed in a take (Q4); the default stays "hold" |
| M9: the Pi's locale is not English | Core writes the month names the touch UI shows (Q15) |
| M10: no `libswscale` on the Pi | T53 starts with `sudo apt install libswscale-dev` (you) |

---

## 3. The WebUI pane

### 3.1 Shape and parts

- **Container:** a full-screen overlay `#playbackOverlay` built like the WebUI's Settings overlay (`.settings-overlay` +
  a shell of `min(1320px, 100vw − 32px) × (100dvh − 32px)`, radius 32, `rgba(9,9,11,.96)`, `Web:954-988`). Below 720 px it
  goes edge to edge (inset 0, radius 0), because the touch UI's page is the whole screen. It replaces
  `#mediaBrowserOverlay` (`Web:3979-4030`).
- **Inside:** the touch UI's two pages, browser and viewer, one at a time, each with the touch UI's title block, top-right
  buttons and one rounded **sheet** (`var(--surface-2)`, border `var(--card-border)`, radius `var(--radius-xl)` = 28, the
  touch sheet's radius).
- **Parts used:** `.secondary-button`, `.danger-button`, `.primary-button`, `.icon-button`, the count pill, `.badge` (the live
  preview's pills), `.preview-center-card` (for the hold card), `.settings-card` (metadata panel), the existing
  `/icons/*.png` (F27). The touch UI's colours are mapped to the nearest WebUI token (Appendix B), not copied as hex.
- **Fonts and motion:** the WebUI's font stack; the touch UI's timings (press scale 0.985, 150-180 ms colour, dialogs 220/240
  ms, clip change 260/320 ms); `prefers-reduced-motion` turns the slides off.

### 3.2 Map: every element of the touch-UI browser and its WebUI counterpart

| # | Touch UI element (`CBP`, r2 §2) | WebUI counterpart | Same / adapted |
| --- | --- | --- | --- |
| B1 | Black full-screen page | the overlay shell (§3.1); full bleed below 720 px | adapted |
| B2 | "PLAYBACK" eyebrow (12 px, 40 % white, letter-spacing 3) | same text, `.pb-eyebrow` in `var(--muted-2)` | same |
| B3 | "Clip Browser" / "Still Browser" (bold 34) | same strings, `h2.section-title`; "Timelapse Browser" / "Audio Browser" for the WebUI's extra categories (D13) | same + D13 |
| B4 | Back (← Back; "Cancel" in selection) | `.icon-button.settings-back-button` "Back" / "Cancel" | same |
| B5 | CAPTURE / Clip Mode · Still Mode, accent in still mode | "SHOW / Clips" two-line `.secondary-button` with the `#3fd0ff` accent border the WebUI already uses (`Web:1664-1668`); opens Clips · Stills · Timelapse · Audio | D1 |
| B6 | Refresh Media / "Scanning..." with `refresh.png` | same strings and icon; "Scanning..." now paints (the fetch is async); icon only below 420 px | same |
| B7 | Sheet `#151515` r28, runs off the bottom | `.pb-sheet` (`--surface-2`, r28), runs to the shell's bottom | same |
| B8 | Film icon + "CLIPS" / "STILLS" / "SELECTION" | `/icons/film.png` + same labels; "TIMELAPSE" / "AUDIO" | same + D13 |
| B9 | Count chip "12 ITEMS" / "3 SELECTED" | the WebUI count pill: "12 items", "1 item", "3 selected" | D2 |
| B10 | Sort chip "NEWEST FIRST" / "OLDEST FIRST", accent, toggles | a pill button with the same words and accent; replaces today's `<select>` (`Web:4009`) | same |
| B11 | Remove Selected (red, trash icon) in selection mode | `.danger-button` "Remove Selected" + `delete.png`; beside it `.primary-button` "Download Selected" and `.secondary-button` "Select All" | same + D3 |
| B12 | Status line: "Found 12 clip(s) in /media/RAW.", "No cDNG, ProRes, H.264 or MLV clips found in /media/RAW.", "/media/RAW is not available.", the selection hint | same strings, root from the reply's `media_root`; a hold adds "Playback held: recording. Pictures return when the take ends." | same |
| B13 | Grid: 2 / 3 / 4 columns by layout | CSS grid at the WebUI's breakpoints: < 720 px 2, 720-1119 px 3, ≥ 1120 px 4 | adapted |
| B14 | Card r24 `#181818`, 1 px border | `.pb-card`: `--surface`, `--card-border`, `--radius-lg` (22) | same |
| B15 | 16:9 thumbnail r18, "NO PREVIEW" until ready | `<img>` from a blob in a 16:9 box, `--radius-md` (18); "NO PREVIEW" also for a held or unplayable clip | same |
| B16 | Duration pill bottom-left ("00:12", "01:02:03", "DNG STILL") | `.badge` with the touch UI's text (F22, card rule) | same |
| B17 | Selection badge top-left (28 px circle; red with ✓ when selected) | same; with a mouse also on hover (D4) | same + D4 |
| B18 | Footer: name (bold 17), format label ("cDNG clip", "ProRes clip", "H.264 clip", "MLV clip", "Video clip"; "DNG still"), shot date ("28 Oct 2026  14:03", "Shot date unavailable") | same three lines and strings, from Core's `format_label` and `shot_date_text` | same |
| B19 | Last-opened card lighter | `.pb-card.last` (border 20 % white) | same |
| B20 | Marked card `#241c1f`, red border | `.pb-card.selected`: the `.danger-button` tint and border | same |
| B21 | Press scale 0.985 | `:active { transform: scale(0.985) }` | same |
| B22 | Tap opens; long press (Qt's 800 ms) starts selection; in selection a tap toggles | pointer events, 800 ms, same rules | same |
| B23 | "Remove Selected Clips?" dialog: scrim 80 %, card r26, "N clip(s) selected", first name, "+N more" / "This action cannot be undone.", Cancel / Remove Clips | same strings; scrim `rgba(0,0,0,.8)`, card in the shell style; `.secondary-button` / `.danger-button` | same |
| B24 | Delete results in the status line ("Removed X.", "Failed to remove X.") | Core's reply in the status line (Core's own words, e.g. "Stop recording before deleting media.") | adapted |

### 3.3 Map: every element of the touch-UI viewer and its WebUI counterpart

| # | Touch UI element (`CPP`, r2 §3) | WebUI counterpart | Same / adapted |
| --- | --- | --- | --- |
| V1 | "PLAYBACK" + "Clip Viewer"; Back stops (frame 1, paused) and returns | same | same |
| V2 | Preview r24, 16:9, letterboxed on black, previous frame kept while the next loads | `<canvas>` in a 16:9 box (`--radius-lg`); a frame is drawn only once decoded | same |
| V3 | Badges: "25.000 FPS" top-right, "PLAYING" / "PAUSED" bottom-left, "FRAME i / N" bottom-right (1-based) | `.badge` pills in the same corners, same text; "SINGLE FRAME" for stills | same |
| V4 | No gesture on the picture | none | same |
| V5 | Title row (stacked only): name (bold 27), "cDNG sequence • 250 frames", Info button | same; the info line is Core's `info_line` | same |
| V6 | Scrub bar: rail, fill, handle; press or drag anywhere seeks; no throttling | same look (rail `--surface`, fill `#d7d9de`, handle `#f4f5f7`); pointer capture; one request in flight, the newest position wins (Cinemate's coalescing scrub, r1 §1.5) | same + mechanic |
| V7 | Remove (red, trash icon) | `.danger-button` "Remove" + `delete.png`; beside it a `.secondary-button` "Download" (D3) | same + D3 |
| V8 | Previous clip / Play-Pause / Next clip, three circles; prev/next disabled at the ends; clip skips, not frame steps | round `.icon-button`s with `previous` / `play` / `pause` / `next` PNGs; same rules (frame steps are O1) | same |
| V9 | HISTOGRAM card, 48 bars, white gradient 0.96 → 0.42, baseline | `<canvas>` card, same drawing; bins from Core's `X-Histogram`, so they equal the touch UI's | same |
| V10 | Clip Metadata: CAPTURED, TYPE, RESOLUTION, BIT DEPTH, FRAME RATE, DURATION, FRAMES, CLIP SIZE, PATH; "Unavailable" | same labels; values formatted by Core in the touch UI's formats (`meta`) | same (+ D9) |
| V11 | Split: metadata as a side panel; stacked/compact: Info overlay with Close | split: a `.settings-card` side panel; stacked/compact: a dialog with Close | same |
| V12 | "Remove Clip?" dialog; then the clip at the same index, or the browser if none | same strings and flow | same |
| V13 | Clip change: slide from ±44 px, fade 260 ms, scale 320 ms; prev/next disabled meanwhile | same timings in CSS | same |
| V14 | Status text only when a clip has no frames ("No DNG frames found in X.") | same, with Core's `play_reason` | same |
| V15 | Opens paused on frame 1; loops at the end | same (play-once is O2) | same |
| V16 | Paused frame is a sharper full-size decode | paused: the smallest width in the list that covers the stage's device pixels (≤ 1920) | same |
| V17 | Opening the delete dialog closes the Info overlay | same | same |
| V18 | Standby stops playback | hold card "Standby" with a Wake button | adapted |
| V19 | Sound through `aplay`, no volume control | `<audio>`, the device's own volume | D7 |
| V20 | — (no hold) | the hold card over the picture: `.preview-center-card` with the reason (§4.8) | D6 |

### 3.4 Map: flow, states and the rest

| Touch UI | WebUI |
| --- | --- |
| Pages browser ↔ player in `Main.qml` Loaders (`Main:580-640`) | two views inside one overlay; `state.pb.page` = `"browser"` / `"viewer"` |
| Folder button greyed in a take (`CamP:3754`) | `mediaBrowserButton` greyed while `snapshot.recording` |
| Hardware `clip_browser` toggles the browser | touch UI only (D14) |
| HDMI window hidden while the browser is up (r2 §6) | not affected: the WebUI does not touch HDMI |
| Audio meter suspended off the camera page (r2 §1.2) | the WebUI's live preview stopped while the overlay is open (F18) |
| Live refresh by a watcher | D5 |
| Scan on every open; thumbnails thrown away | Core's facts cache and LRU; the page keeps the grid and thumbnails (D10) |
| Prev/next in the browser's current sort | prev/next in the browser's current sort **and** filter |
| Still pairs (DNG + JPEG with one stem) shown once; delete removes both | Core's existing still grouping by stem (`Photos/<stem>`, r3 §1.5) and its delete do the same |
| Selection cleared by mode change, sort, Refresh, Back, page change, delete | same events clear it |

### 3.5 Layouts

The browser's width and height choose the touch UI's layout family (`CPP:22-29`, `:306-345`; r2 §3.1):

| Browser | Touch UI family | Viewer shape |
| --- | --- | --- |
| width ≥ 1120 px (laptop, large tablet) | split (`landscape*`) | preview left (height ≤ sheet − 132), scrub under it, control row; Clip Metadata panel right, 27 % of the sheet (340-420 px) |
| landscape and height < 500 px (phone on its side) | compact (`landscape_compact`) | preview, full-width scrub, one row: Remove, transport, Info icon, histogram |
| otherwise (phone portrait, small tablet) | stacked (`square`) | preview, title row with Info, scrub, row: Remove, transport, histogram; metadata in a dialog |

1120 px is the width at which the WebUI's Settings already drops its sidebar (`Web:2034-2041`), so both overlays change shape
at the same point.

Phone portrait, browser and viewer (text sketch):

```
PLAYBACK                       [↻] [SHOW ] [← Back]
Clip Browser                        Clips
┌─────────────────────────────────────────────┐
│ ▣ CLIPS              (NEWEST FIRST) 12 items│
│ Found 12 clip(s) in /media/RAW.             │
│ ┌──────────────┐ ┌──────────────┐           │
│ │ ▒▒▒ thumb ▒▒ │ │ ▒▒▒ thumb ▒▒ │           │
│ │ (00:10)      │ │ (01:02)      │           │
│ │cDNG_..._C0007│ │cDNG_..._C0006│           │
│ │cDNG clip     │ │cDNG clip     │           │
│ │28 Oct 2026 … │ │28 Oct 2026 … │           │

PLAYBACK                              [← Back]
Clip Viewer
┌─────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────┐ │
│ │                          (25.000 FPS)   │ │
│ │              picture                    │ │
│ │ (PAUSED)                (FRAME 1 / 250) │ │
│ └─────────────────────────────────────────┘ │
│ cDNG_26-10-28_C0007                [ⓘ Info] │
│ cDNG sequence • 250 frames                  │
│ ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ [🗑 Remove] [⤓]  (⏮) ( ▶ ) (⏭)  [HISTOGRAM] │
```

Laptop, viewer (split):

```
PLAYBACK                                                                 [← Back]
Clip Viewer
┌───────────────────────────────────────────────────────────┬──────────────────────┐
│ ┌───────────────────────────────────────────────────────┐ │ ⓘ Clip Metadata      │
│ │                                        (25.000 FPS)   │ │ cDNG_26-10-28_C0007  │
│ │                     picture                           │ │ CAPTURED   RESOLUTION│
│ │ (PLAYING)                          (FRAME 118 / 250)  │ │ 28 Oct ..  3840 x 2160│
│ └───────────────────────────────────────────────────────┘ │ TYPE       BIT DEPTH │
│ ━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ ...                  │
│  [🗑 Remove] [⤓ Download]  (⏮) ( ⏸ ) (⏭)   [HISTOGRAM ▁▃▆▇▅▂] │ PATH [/media/RAW/..] │
└───────────────────────────────────────────────────────────┴──────────────────────┘
```

Phone traps from the handbook (r4 §6): `100dvh` with a fallback; a definite `max-height` on the preview box; test on a real
phone; no fullscreen button (iOS has none for `<canvas>`, and the touch UI has none either). Touch targets stay ≥ 44 px.

### 3.6 Behaviour

| Topic | Rule |
| --- | --- |
| Open | Folder button (greyed in a take) → stop `#previewStream` with `removeAttribute("src")` and a `previewPausedForPlayback` flag that the `<img>` error handler and `loadPreviewStream` respect (F18; Cinemate's lesson: `src=''` re-resolves to the page, `cm:4d3bca4`) → `GET /api/media` → render cards → thumbnails for visible cards, 2 in flight (`IntersectionObserver`) |
| Close | Back from the browser, or Escape → clear the flag → `loadPreviewStream()` (`Web:8597`) restarts the live view with a new nonce |
| Open a clip | the thumbnail queue pauses → `GET /api/media/clip` → paused on frame 1 → the paused-size frame (V16) |
| 404 "The clip changed" | refetch the list once (a reused name or a Core restart changed the token, §4.2), then reopen by index |
| Play | audio clock if a WAV exists, else wall clock; two requests in flight at 640 w, asked ahead by the measured round trip (§2.2); draw the newest decoded frame not later than the clock |
| 503 busy | skip that frame; count it (for O4) |
| 409 hold | pause, pause the audio, show the hold card (§4.8); the poll clears it |
| End | loop to frame 1 and keep playing, like the touch UI (`PC:567`) |
| Pause | stop the clock; after 150 ms ask the paused-size frame for the current position |
| Scrub | pointerdown pauses; each move asks 640 w with one request in flight, the newest position wins; pointerup asks the paused size |
| Prev / next clip | index ± 1 in the browser's current sort and filter (`Main:426-443`) |
| Remove | dialog → `POST /api/media/delete` → the clip at the same index opens, or the browser if none |
| Download | `<a download>` to the item's existing `download_url` (a folder ZIP, `App:7343-7462`) |
| Hidden tab | pause; toast "Paused: the tab is in the background." (Cinemate, r1 §1.5) |
| Hold from the poll | `renderSnapshot` (`Web:9366`) reads `playback_hold` once a second: pause and show the card; when it clears, redraw the current frame, do not resume; refetch the list when a take ended |
| Keep awake | while playing, `user_activity` every 20 s |
| Keys | Space play/pause in the viewer; Escape closes the metadata dialog, then the viewer, then the browser (D12) |

### 3.7 Walkthroughs

**A. The last take, with sound, on the laptop.**

| You do | You see | Core does |
| --- | --- | --- |
| Folder button | Clip Browser, newest first, the last take top-left with "00:10", "cDNG clip", "28 Oct 2026  14:03"; the live view stops behind it | `/api/media` from its facts cache; `frame=0&w=320` per visible card: hold check, slot, decode, LRU |
| Click the card | Clip Viewer, paused, "25.000 FPS", "PAUSED", "FRAME 1 / 250"; metadata panel right | `/api/media/clip`; `frame=0&w=1920` |
| Play | picture at about 25 fps (PROBABLE, M1), sound from the laptop, "PLAYING" | `<audio>` Range requests on `/api/media/file`; frames at `w=640`, 2 workers |
| Wait to the end | loops to frame 1 | the second loop comes from the LRU when the frames fit (~250 × 30 KB = 7.5 MB) |
| Back, Back | browser, then the camera page with live view | `/preview.mjpeg?stream=n+1` |

**B. Someone presses record while you watch.** At the next frame (409) or within a second (poll): the picture pauses, sound
stops, the card says "Recording" (§4.8). The grid stops loading thumbnails. The take ends and writes drain: the card goes,
the frame redraws, the list refetches and the new take appears first. Playback does not restart by itself. Core: every
request runs `playbackHoldReason()`; a decode in flight stops at its next tile; `/api/state` shows
`"playback_hold":"recording"`, then `"writing"`, then `""`.

**C. Remove from the viewer.** Remove → "Remove Clip?" → "Remove Clip" → the next clip at the same index opens. In a take
or while writes drain, Core refuses with its existing words and the dialog shows them.

**D. A 4K SDR 12-bit lossless take shot at 50 fps.** "FRAME i / N" jumps in steps of ~6-10 (PROBABLE: 50 fps wanted, ~5-8
shown), and the sound stays in time. With O4 the rate row says so ("Achieved 7.8 fps · skipped 312"). The touch screen is
probably the same today (M2).

**E. The card is pulled.** Within ~2 s: the hold card says "Media not available / Media was removed. Insert or mount media
to play clips."; the browser shows "/media/RAW is not available." (touch UI wording). Core: the watcher's snapshot says not
mounted; routes answer 409 `media` before they read anything.

**F. On the phone, portrait.** Two columns of cards. The viewer stacks: picture, name and Info, scrub, then Remove,
Download, the three circles and the histogram. Info opens the Clip Metadata dialog with Close.

**Code view of one frame request** (T48): route → `playbackHoldReason()` (409) → `kind`/`id` through
`isSafeMediaRelativeId` / `resolveMediaLibraryPath` (404) → the clip's frame list from the cache (404 if `frame` is out of
range) → `w` from the list (400) → LRU hit? send it → try a decode slot (503) → read the tail, then the payload, checking the
hold flag per tile → render at `w` → histogram → JPEG → LRU → 200 with the headers of §4.4.

---

## 4. Core API, data and state

### 4.1 Routes

| Method and path | Answer | Refused | New / changed |
| --- | --- | --- | --- |
| `GET /api/media` | today's list, each clip with the facts of §4.2; top level `held` | never; in a hold it answers from memory | changed (T47) |
| `GET /api/media/clip?kind=folder\|still&id=…` | §4.3 | 404 unknown id, 400 missing | new (T47) |
| `GET /api/media/frame?kind=…&id=…&frame=N&w=320\|480\|640\|960\|1280\|1920&v=TOKEN` | `image/jpeg`; headers §4.4 | 409 hold, 503 busy, 404, 400 | new (T48) |
| `GET /api/media/file?kind=folder&id=…&name=X.wav` | `audio/wav`; Range → 206 | 409 hold, 404, 416, 400 (not a `.wav`) | new (T51) |
| `POST /api/media/delete`, `/api/media/delete-selected` | today's | + `writing` (F16) | changed (T50) |
| `GET /api/state` | + `"playback_hold":"…"` | | changed (T47) |

Apertar style: the `/api/media/*` family; `kind` + `id` exactly like the download route (`App:7343-7360`); query values
through the existing `queryParameterValue` (URL-decoded, `App:5258`); errors as `errorReply(-1, "…")`, i.e.
`{"ok":false,"error":"…"}` (`App:7347-7351`); every id through `isSafeMediaRelativeId` / `resolveMediaLibraryPath`
(`App:5640`, `App:5790`). No socket command (§2.7).

### 4.2 `/api/media` item: new and fixed fields

```json
{"id":"cDNG_26-10-28_C0007","kind":"folder","category":"clip","type":"cDNG Clip","name":"cDNG_26-10-28_C0007",
 "size_bytes":4150000000,"size_text":"3.9 GB","file_count":251,"frame_count":250,
 "duration_text":"00:10","fps_text":"25 FPS",
 "modified_text":"…","modified_ms":1761660180000,"download_url":"/api/media/download?kind=folder&id=cDNG_26-10-28_C0007",
 "format":"cdng","format_label":"cDNG clip","playable":true,"play_reason":"",
 "fps":25.0,"shot_date_text":"28 Oct 2026  14:03","shot_ms":1761660180000,"empty_frames":0,"dropped_frames":0,
 "has_audio":true,"token":"9f3c2a17",
 "thumb_url":"/api/media/frame?kind=folder&id=cDNG_26-10-28_C0007&frame=0&w=320&v=9f3c2a17"}
```

- `fps_text` and `duration_text` come from the clip's own first frame (the fix of §1.1). `duration_text` uses the touch
  card's rule (F22). A clip without a FrameRate tag uses 24, as the touch UI does (`PC:262`), and says so in the metadata.
  Old fields keep their names, so nothing else that reads the list breaks.
- `frame_count` = non-empty frames. `empty_frames` = 0-byte DNGs (a pulled take leaves ~21-23, `kb:lessons/hardware-log.md:440-460`).
- `dropped_frames` = (last index − first index + 1) − files (F5; Cinemate's rule, r1 §2.2). With T31 ramp takes it reads 0 (R10).
- `shot_ms` sorts the cards: the shot time, then a numeric-aware name order, like the touch UI (`CLM:287-299`, r2 §2.4).
- `token` = FNV-1a of (folder name, first frame's mtime in ns, its size, the file count, Core's start time). It changes
  when a folder name is reused (F6) and when Core restarts after a rebuild, so no cache can show the wrong picture
  (Cinemate's render-token lesson, r1 §4.2 #7).
- Facts are cached per folder, keyed by (folder mtime, entry count). An unchanged folder costs one `readdir`, not a `stat`
  per file. Whether exFAT updates a folder's mtime on every new file is UNCONFIRMED; the entry count covers it.
- In a hold the reply is the last cache plus `"held":"recording"` (or `writing`, `media_test`, `standby`, `media`). If
  the cache is empty (Core started during a take), `items` is empty and the page says "Playback held: recording. Pictures
  return when the take ends."
- `mounted` follows the watcher too (`mediaSnapshot()`), not only the mount table, which keeps a pulled medium listed
  (`App:7874-7876`, r3 G7).

### 4.3 `/api/media/clip`

```json
{"ok":true,"kind":"folder","id":"cDNG_26-10-28_C0007","name":"cDNG_26-10-28_C0007",
 "format":"cdng","playable":true,"play_reason":"","frame_count":250,"empty_frames":0,"dropped_frames":0,
 "fps":25.0,"fps_fallback":false,"token":"9f3c2a17","width":3840,"height":2160,"bits":16,
 "compression":"uncompressed","companded":false,"timecode_start":"14:03:12:05",
 "has_audio":true,"audio_text":"24-bit 48 kHz stereo",
 "audio_url":"/api/media/file?kind=folder&id=cDNG_26-10-28_C0007&name=cDNG_26-10-28_C0007.wav",
 "fps_badge":"25.000 FPS","info_line":"cDNG sequence • 250 frames",
 "meta":{"captured":"28 Oct 2026  14:03","type":"cDNG sequence","resolution":"3840 x 2160","bit_depth":"16-bit",
         "frame_rate":"25.000 fps","duration":"00:10","frames":"250","clip_size":"3.9 GB",
         "path":"/media/RAW/cDNG_26-10-28_C0007"}}
```

`meta` values use the touch UI's formats (`PC:121-164`, `PC:1149-1205`): date "dd MMM yyyy  HH:mm" (two spaces), "%1 x %2",
"%.3f fps", the metadata duration rule (F22), sizes base 1024 with one decimal below 100, "Unavailable" when missing. Core
formats them, so both screens show one answer: Patrik's own precedent when the WebUI and the touch UI disagreed
(`bda2066`, `3c4f07d`, r4 P4). `bit_depth` follows D9 ("12-bit, companded") unless Q6 says copy the touch UI.

### 4.4 `/api/media/frame`

- `frame` = 0-based position in the sorted list of non-empty frames (not the number in the name; gaps are skipped, r1 §2.2).
- `w` from a list, so the LRU stays small: 320 and 480 (cards), 640 and 960 (playing), 1280 and 1920 (paused). The height
  follows the frame's aspect.
- JPEG quality 80 (75 for 320 and 480). RGB → TurboJPEG `tjCompress2` with FASTDCT, libjpeg fallback, like `App:4165-4230`.
- Headers on 200:

| Header | Value |
| --- | --- |
| `X-Frame-Index`, `X-Frame-Count` | position, count |
| `X-Histogram` | 48 integers 0-255, the touch UI's recipe (F20) |
| `X-Frame-Source` | `cache` or `decode` |
| `X-Decode-Ms` | the decode time, so logs and the page carry values (Cinemate lesson C7, r4 §5.2) |

- `v` is checked against the clip's token; a stale `v` gets 404 `{"ok":false,"error":"The clip changed. Refresh Media."}`,
  so an old page cannot show a new take's picture under an old name.
- Errors: 409 `{"ok":false,"error":"…","hold":"recording"}`, 503 `{"ok":false,"busy":true}`, 404, 400.

### 4.5 `/api/media/file` (T51)

- Only a `name` ending in `.wav` (any case), with no `/`, `\` or `..`, resolved inside the clip folder, a regular file and no
  symlink (Cinemate's symlink lesson, r1 §2.7).
- `Range: bytes=a-b`, `a-` or `-n` → 206 with `Content-Range` and `Content-Length`; no Range → 200 with `Content-Length`
  and `Accept-Ranges: bytes`; unsatisfiable → 416 with `Content-Range: bytes */size`; several ranges → 200 with the whole
  file. The body is sent with `pread` in 64 KiB chunks (the `streamFileToClient` pattern, `App:6333-6348`).
- `Content-Length` is always sent, so a cut stream is visible (r3 §3.3).

### 4.6 State

| Field | Where | Meaning |
| --- | --- | --- |
| `playback_hold` | `buildWebStateJson` (`App:7857-8224`), next to `media_alive` | §2.7. The WebUI polls it; socket clients already get `recording` and `media` events |

Not persisted, no settings file, no new event. Sort, filter and the last-opened clip live in the page; `localStorage` is not
used (the touch UI does not keep them either, r2 §2.4).

### 4.7 Caches, slots, priorities

| Cache | Key | Size | Lives |
| --- | --- | --- | --- |
| Folder facts | folder name → (mtime, entry count) | one entry per take | Core process |
| Frame list per clip | folder → sorted names and sizes | last 8 opened clips | Core process |
| JPEG LRU | (id, frame, w, token) | 32 MB | Core process; survives holds |
| Thumbnails in the page | the thumbnail URL (it carries the token) | while the page is open | the browser tab |

Slots: a counting semaphore of `APERTAR_PLAYBACK_WORKERS` (default 2), taken without waiting; full → 503 (Cinemate's "refuse
rather than queue", r1 §2.5). Decoding runs on the HTTP client thread that holds the slot, at nice 10. An LRU hit needs no
slot.

### 4.8 Refusals and messages

| When | Kind | Text |
| --- | --- | --- |
| hold `recording` | 409 + hold card | title "Recording", body "The card is busy with a take. Playback resumes when recording stops." |
| hold `writing` | 409 + card | "Writing to media", "Finishing the last take. One moment." |
| hold `media_test` | 409 + card | "Media test", "A media speed test is running. Playback resumes when it ends." |
| hold `standby` | 409 + card with a **Wake** button (`wake`) | "Standby", "Wake the camera to play clips." |
| hold `media` | 409 + card | "Media not available", "Media was removed. Insert or mount media to play clips." (after `App:9426`) |
| decoder busy | 503 | nothing shown; the frame is skipped (counted for O4) |
| stale token | 404 | "The clip changed. Refresh Media." |
| no frames | `play_reason` | "No DNG frames found in cDNG_…." (touch UI wording, r2 Appendix B) |
| all frames empty | `play_reason` | "Every frame of this take is empty (0 bytes); the card was probably pulled." |
| MLV not finalized | `play_reason` | "MLV is not finalized or its frame count is invalid." (`MLR:176-177`) |
| H.264 in progress | `play_reason` | "H.264 take is still being written." |
| ProRes without index | `play_reason` | "ProRes take was interrupted; it has no index." |
| format not built yet | `play_reason` | "MLV playback arrives with T52." / "ProRes and H.264 playback arrive with T53." |
| plugin missing | `play_reason` | "Video playback decoder unavailable." (touch UI, `VP:35`) |
| decode error | the frame is the touch UI's placeholder | "Decode failed: <reader error>" |
| delete in a take | existing | "Stop recording before deleting media." (`App:7664`) |
| delete while writing | new | "Wait for the current capture to finish writing to media." (`App:9489` words) |
| WAV refused by the browser | toast | "This browser cannot play the take's WAV. Playing without sound." |
| hidden tab | toast | "Paused: the tab is in the background." |

### 4.9 Safety

- Ids go through the existing validators (`App:5640`, `App:5690`, `App:5790`). Frame files are never named by the client:
  `frame=N` indexes Core's own sorted list. Names go into the page with `textContent` (Cinemate's stored-XSS lesson,
  r1 §2.7).
- A reader bug must not take Core down. The reader checks every offset against the file size before allocating (sketch);
  the web server catches exceptions per client thread (`WS:279-284`), not crashes; the T48 gate re-runs the fuzz of §2.3.
- No auth, as today: keep port 8000 on a trusted network (r4 K21).

### 4.10 Ways it could look half-done, and why they cannot

| State | What you would see | Why it is safe |
| --- | --- | --- |
| A browser tab from before a Core update | the old page; it knows no new routes | the page is compiled into Core and `/` is `no-store` (F8), so a reload gives the new page; the token changes with Core's start time, so old URLs get 404 "Refresh Media" |
| T47 built, T48 not | the old list overlay with correct FPS and duration | T49 replaces the overlay only after T48 serves frames |
| T49 built, T50 not | cards with thumbnails; a tap shows "The Clip Viewer arrives with T50." | the tap handler calls a stub |
| T50 built, T51 not | the viewer plays silently; no audio element | `has_audio` is ignored until T51 |
| T52 / T53 not built | MLV and movie cards show "NO PREVIEW"; the viewer shows the `play_reason` | `playable:false` with the tutorial's name |

---

## 5. The touch UI: what changes

**Nothing is required.** Patrik's decision makes the touch UI the model; the WebUI copies it. The touch UI's player, browser,
decoders and caches stay as they are, and no T46-T53 step touches `~/ApertarUI` except reading it and building the parity
test against its sources.

Optional fixes, each small, each its own later tutorial (not in T46-T53):

| # | Change | Why | Size |
| --- | --- | --- | --- |
| U1 | "1 item"; "Stills" wording in the still-mode dialog | wording bugs (r2 §10 #4) | ~5 lines |
| U2 | Pause playback when a take starts; ignore the hardware `clip_browser` action in a take; `user_activity` while playing | the touch UI has no hold (r2 §7) and can fall into standby while playing (M5) | ~30 |
| U3 | Delete through Core (`POST /api/media/delete`) instead of `removeClip` | one gate for every delete; the touch UI's delete has no recording check (`CLM:382-441`) | ~40 |
| U4 | Card thumbnails from Core (`http://127.0.0.1:8000/api/media/frame?…&w=320`) | one cache, faster revisits; today every visit decodes every card again (r2 §9 #2) | ~10 |
| U5 | BIT DEPTH from tag 258 (D9) | the file is the witness | ~10 |
| U6 | Histogram sampling across all four CFA sites, in both copies at once (F21) | today 4K histograms show one colour channel (PROBABLE) | ~5 + the parity test |
| U7 | Read only the DNG tail for the frame rate when scanning (today `readAll` of the first DNG per take, `DD:1530`) | the touch browser's scan time | ~20 |
| U8 | Later: the touch UI takes its clip list and facts from `/api/media` | one truth for both screens | ~150 |

---

## 6. Implementation plan, file by file

Order = build order. Lines are at `0296ed1`; **use the search string**, lines move (and the controls project, T36-T45, edits
the same files first). Risk: **low** = checkable on the host (a header with its test, `ApertarCoreApp.cpp` with
`g++ -fsyntax-only`, the page with `node --check` and a mocked Chromium); **medium** = changes what an existing screen does.
No row is high risk: **no change in `CameraController.cpp`, in any writer, or in the web server's header code.**

### T47: Core knows its clips

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 47.1 | new `src/playback/DngFrameReader.hpp` | | part 1: `DngInfo`, tail read, IFD parse, `readDngInfo` with the bounds checks (sketch lines 1-298) | low (host test) |
| 47.2 | new `src/playback/ClipProbe.hpp` | | `ClipFacts`, `ClipFactsCache` (mutex inside); `listFrames(dir)` (names, sizes, first/last index, empty, dropped); `readWavFormat`; `clipToken`; the touch UI's formatters: shot date, card duration, metadata duration, size base 1024, "%.3f fps", type labels, `info_line`, `meta` (each with a comment naming `CLM` / `PC` lines) | low |
| 47.3 | KB `working/tools/playback/clip_probe_test.cpp` | | writes 3 frames with Core's encoder plus a gap and a 0-byte file; checks every fact and every string | low |
| 47.4 | `App.hpp:104-105` | `std::string mediaGateError() const;` | add `std::string playbackHoldReason() const;`, `bool mediaGateBypassed() const;`, `mutable playback::ClipFactsCache clipFacts_;`, `int64_t coreStartMs_;` | low |
| 47.5 | after `App:9413-9440` | `std::string ApertarCoreApp::mediaGateError() const` | `mediaGateBypassed()` (the two early returns of F15, shared) and `playbackHoldReason()` (§2.7) | low |
| 47.6 | `App:5609` | `struct MediaLibraryItem` | add the §4.2 fields | low |
| 47.7 | `App:6422`, `App:6492` | `std::vector<MediaLibraryItem> discoverMediaLibraryItems(` and `: durationTextForFrameCount(stats.frameCount, fps);` | take `ClipFactsCache &` instead of `fps`; facts from `ClipProbe`; `fps_text`, `duration_text` from the clip | low |
| 47.8 | `App:7819` | `std::string ApertarCoreApp::buildMediaLibraryJson() const` | the new fields; `held`; `mounted` also from the watcher (§4.2); answer from the cache in a hold | low |
| 47.9 | after `App:7307-7312` | `if (request.method == "GET" && request.path == "/api/media") {` | route `/api/media/clip` → `buildClipInfoJson(kind, id)` | low |
| 47.10 | `App:8071` | `<< ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")` | `<< ",\"playback_hold\":\"" << playbackHoldReason() << "\""` | low |

### T48: Core draws a frame

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 48.1 | new `third_party/liblj92/` | | `cp ~/ApertarUI/third_party/liblj92/{lj92.c,lj92.h,LICENSE,README.apertar.md}`; `cmp` each | low |
| 48.2 | `CMake:6`, `CMake:76` | `    LANGUAGES CXX`; `    src/cdng/LosslessJpegEncoder.cpp` | `LANGUAGES C CXX`; add `src/playback/PlaybackFrames.cpp` and `third_party/liblj92/lj92.c`; include dir `third_party/liblj92`; re-run cmake (r4 K6) | low |
| 48.3 | `DngFrameReader.hpp` | `inline bool readDngInfo` | part 2: `readDngSamples` (16-bit LE, 12/10 packed, LJ92 tiles, LinearizationTable) with a hold callback per tile | low (host test) |
| 48.4 | new `src/playback/RawRender.hpp` | | the touch UI's look and histogram (sketch, 226 lines) | low (parity test) |
| 48.5 | new `src/playback/PlaybackFrames.hpp/.cpp` | | slots, LRU, `frameJpeg(dir, frame, w, token, hold, out, headers)`, RGB → JPEG (TurboJPEG or libjpeg, as `App:4165-4230`), JPEG stills through TurboJPEG scaled decode, nice 10, frame lists, scratch freed on a hold or after 30 s idle | low (host-compilable) |
| 48.6 | `WS:70` | `case 503: return "Service Unavailable";` | add 206 "Partial Content", 416 "Range Not Satisfiable", and 409 "Conflict" unless controls T38 already added it (F29) | low |
| 48.7 | after the T47 route | `request.path == "/api/media/clip"` | route `/api/media/frame` with the hold, token check, slots and headers (§4.4) | low |

### T49: WebUI Clip Browser

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 49.1 | `Web:1137` (the overlay CSS `Web:1122-1432`) | `.media-browser-overlay.hidden {` | `.pb-*` rules: overlay shell, title, top buttons, sheet, chips, status, grid, card, thumb, duration pill, select badge, dialog; breakpoints 1120 / 720 / 420 | low |
| 49.2 | `Web:3979-4030` | `<div class="media-browser-overlay hidden" id="mediaBrowserOverlay">` | replace with `#playbackOverlay`: title block, Refresh / Show / Back, sheet head, chips, status, grid, Remove dialog, the empty viewer container (T50) | medium (today's browser goes) |
| 49.3 | `Web:4246` | `mediaSelection: new Set(),` | `pb: {page, filter, sort, selecting, lastOpenedId, thumbs, …}` | low |
| 49.4 | `Web:6176` | `function setMediaBrowserOpen(open) {` | stop and restart the live view (§3.6); open on the browser page | low |
| 49.5 | `Web:8616` | `state.previewRetryTimer = window.setTimeout(loadPreviewStream, 1500);` | no retry while `previewPausedForPlayback` | low |
| 49.6 | `Web:7707` | `function renderMediaLibrary(payload) {` | build cards instead of rows; `buildClipCard`, the status strings, "1 item"; sort by `shot_ms` in `sortedMediaItems` (`Web:7596`) | medium |
| 49.7 | near `Web:10403` | `async function fetchMediaLibrary(silent) {` | thumbnail queue (2 in flight, `IntersectionObserver`, blobs kept in memory), long press 800 ms, hover badge, Remove Selected dialog → the existing `deleteSelectedMediaItems` (`Web:10468`); Download Selected → the existing `downloadSelectedMediaItems` (`Web:10446`); Select All | low |
| 49.8 | `Web:2447` | `<button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">` | disabled while `snapshot.recording` (in `renderSnapshot`, `Web:9366`) | low |

### T50: WebUI Clip Viewer

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 50.1 | the T49 CSS block | `.pb-card {` | viewer rules: stage, badges, title row, scrub, transport, histogram card, metadata panel and dialog, hold card; split / compact / stacked queries | low |
| 50.2 | inside `#playbackOverlay` | `id="pbViewer"` | the viewer markup (§3.3) | low |
| 50.3 | after the T49 JS | `function buildClipCard(` | `openClip`, `fetchClipInfo`, `requestFrame` (fetch → `createImageBitmap`, headers), `drawFrame`, `drawHistogram`, the clock and look-ahead, `playClip`, `pauseClip`, `installScrub`, `stepClip`, `showClipMetadata`, `removeCurrentClip`, `downloadCurrentClip` | low |
| 50.4 | `Web:9366` | `function renderSnapshot(snapshot) {` | `applyPlaybackHold(snapshot)`; refetch the list when `recording` goes false | low |
| 50.5 | `Web:11558` | `document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});` | 20 s `user_activity` while playing; pause on `visibilitychange` | low |
| 50.6 | `Web:11620` | `if (event.key === "Escape" && state.mediaBrowserOpen)` | Escape: metadata dialog, then viewer, then browser; Space play/pause | low |
| 50.7 | `App:7649`, `App:7721` | `if (request.method == "POST" && request.path == "/api/media/delete") {` and `…/delete-selected") {` | add `camera_.mediaWritesPending()` to the gate (F16) | low |

### T51: Sound

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 51.1 | after `App:6333` | `void streamFileToClient(int clientFd, const std::filesystem::path &path)` | `streamFileRangeToClient(fd, path, first, last)` with `pread` | low |
| 51.2 | after the frame route | `request.path == "/api/media/frame"` | `/api/media/file`: name rules, hold, Range parse, 200 / 206 / 416 | low |
| 51.3 | viewer JS | `function playClip(` | `<audio preload="none">`, the audio clock, seek on scrub, error → silent notice; sound-only items | low |

### T52: MLV · T53: ProRes and H.264

| # | File | Change | Risk |
| --- | --- | --- | --- |
| 52.1 | new `src/playback/MlvFrameReader.hpp` | named copy of the `MLR:153-278` rules: header, block walk to the first `VIDF`, frame index (one pass over block headers, cached), 12-bit unpack, WBAL / DEBG-APCM / EXPO | low (host test with Core's `MlvEncoder`) |
| 52.2 | `RawRender.hpp` | the ISP path (`CIP:655-662`): clip × common gain, CCM, sRGB OETF | low (parity test against `MlvReader`) |
| 52.3 | `ClipProbe.hpp`, `PlaybackFrames.cpp` | MLV facts and frames | low |
| 53.1 | new `src/playback/VideoPlaybackApi.h`, `src/playback/VideoPlaybackLibav.cpp` | `cp` from `~/ApertarUI/src/`; `cmp` each | low |
| 53.2 | `CMake:140` | `if(LIBAV_FOUND)`: `pkg_check_modules(SWSCALE QUIET IMPORTED_TARGET libswscale)`; `add_library(apertar-video-libav MODULE src/playback/VideoPlaybackLibav.cpp)` linked to LIBAV + SWSCALE, as `UCMake:136-146` | low |
| 53.3 | new `src/playback/VideoFrames.hpp/.cpp` | `dlopen` of Core's own `apertar-video-libav.so` (next to the binary, then `APERTAR_VIDEO_PLAYBACK_PLUGIN`), the `H264C:105` pattern; ABI `version == 2`; one open decoder per clip; BGRA → JPEG | low |
| 53.4 | `ClipProbe.hpp` | facts from the plugin's `probe`; `.mp4.writing`; ProRes without `moov` | low |

### Size (PROBABLE, counted as the T34 design counted)

| Part | Lines | Checked before the Pi |
| --- | --- | --- |
| T47 | ~500 (reader part 1, ~300 lines, is in the sketch) | host test, `g++ -fsyntax-only` |
| T48 | ~650 (reader part 2, ~75, and `RawRender.hpp`, 226, are in the sketch) | round trip, parity, fuzz, syntax |
| T49 | ~430 | `node --check`, mocked Chromium |
| T50 | ~700 | same |
| T51 | ~200 | syntax; `curl` with Range on the Pi |
| T52 | ~300 | host test with `MlvEncoder` |
| T53 | ~180 (the two copied files, 253 lines, are not counted: you copy them) | syntax; the Pi |
| **Total** | **~2,960** | nothing waits for the Pi to compile except the CMake runs |

---

## 7. Tutorial outlines (KB format)

Each note: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T4x <topic>.md`, frontmatter as `kb:tutorials/README.md`
(`datum`, `kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext`, `typ: digital anteckning`), sections 0-9, numbered steps,
one **Check** per step, a `%% tutor` block, the tags `#CINEMATE` `#APERTAR`. Section 6 is "Commit" (house rule: nothing is
pushed). Reading assignments name lines at `0296ed1` / `5aab7e2`; run `tutorial.py refs T4x` on the Pi first (lines move,
and the controls tutorials edit the same files). A pipe inside a check is written `|` with no spaces (F28).

### T46. Measure first: what a playback frame costs on this Pi

- **You will learn**: what a 4K frame costs to read, decode and draw on your Pi; how fast the touch screen plays today;
  how Core's server behaves with many small requests; what your browsers play. **Risk**: none to the camera (read-only;
  M5 changes one setting that you restore; M7 records two takes). **Time**: 1.5 h.
- §1: the WebUI list shows the camera's FPS for every take (`curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`).
- §3: M1-M10 of §8, each with a prediction. §4: none. §5: the result table goes into `lessons/hardware-log.md` after you
  confirm the reading (r4 K15).

### T47. Core knows its clips: per-clip facts from the files

- **You will learn**: (1) how a DNG is laid out and why its tags cost one small read; (2) why a fact about a take must
  come from the take ("the file is the witness"); (3) one guard function used by every route; (4) why it is a route and
  not a command (the command lock). **Risk**: Core rebuild and restart; the list's FPS and duration text change. Undo:
  `git revert`. **Time**: 2.5 h.
- §2 reading: `Cdng:1384-1392`, `Cdng:1522-1560`, `IFD:113-125`, `App:6422-6497`, `App:7819-7855`, `App:9485`,
  `PC:1149-1205`, `CLM:147-169`.
- §3 find it yourself: 3.1 `tail -c 1600 <first.dng> | xxd | head` (prediction: the tag directory); 3.2 why does the list
  say 25 for a 50 fps take (`App:6493`); 3.3 `ls <take> | head -3; ls <take> | tail -3` (gaps); 3.4 what would a slow
  folder read do inside `handleCommand`?

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | reader part 1 (47.1) | `grep -c 'inline bool readDngInfo' src/playback/DngFrameReader.hpp` → 1 |
| 4.2 | `ClipProbe.hpp` facts (47.2) | `grep -c 'inline ClipFacts probeClipFolder' src/playback/ClipProbe.hpp` → 1 |
| 4.3 | formatters (47.2) | `grep -c 'dd MMM yyyy' src/playback/ClipProbe.hpp` → 1 or more |
| 4.4 | host test (47.3), built and run on the Pi | `./clip_probe_test` ends `all ok` |
| 4.5 | `playbackHoldReason` (47.4, 47.5) | `grep -c 'std::string ApertarCoreApp::playbackHoldReason' src/ApertarCoreApp.cpp` → 1 |
| 4.6 | item fields, scan, cache (47.6, 47.7) | `grep -c 'probeClipFolder(' src/ApertarCoreApp.cpp` → 1 or more |
| 4.7 | JSON (47.8) | `grep -c 'shot_date_text' src/ApertarCoreApp.cpp` → 1 |
| 4.8 | route (47.9) | `grep -c 'request.path == "/api/media/clip"' src/ApertarCoreApp.cpp` → 1 |
| 4.9 | state field (47.10); `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude src/ApertarCoreApp.cpp` | `grep -c 'playback_hold' src/ApertarCoreApp.cpp` → 1 or more |

- §5: build, restart (you), then `curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`
  (each take its own rate); `curl -s 'http://127.0.0.1:8000/api/media/clip?kind=folder&id=<take>' | python3 -m json.tool`
  (the nine fields); `curl -s http://127.0.0.1:8000/api/state | grep -o '"playback_hold":"[^"]*"'` → `""`; start a take,
  repeat → `"recording"`.
- §7: list empty → `media_root`; a take shows "No DNG frames" → `ls -la` the folder; Core does not start → the journal.

### T48. Core draws a frame, with the touch UI's look

- **You will learn**: (1) lossless JPEG tiles and why they cost more than uncompressed; (2) how the touch UI turns raw into
  a picture, line by line; (3) how a server stays responsive by refusing work (slots, 503) instead of queueing it; (4) a
  parity test that keeps two copies honest. **Risk**: Core rebuild. Undo: `git revert`. **Time**: 2 sessions, 4 h.
- §2 reading: `CIP:577-698`, `DD:455-536`, `Cdng:1237-1351` (the tile writer), `WS:59-73`, the sketch's `results-host.txt`.
- §3: 3.1 `cmp ~/ApertarUI/third_party/liblj92/lj92.c ~/apertar-kb/working/tools/playback/third_party/liblj92/lj92.c`;
  3.2 run `playback_bench --cold` on one of your lossless frames (from T46) and predict the per-worker fps.

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | copy liblj92 (48.1) | `cmp third_party/liblj92/lj92.c ~/ApertarUI/third_party/liblj92/lj92.c` → no output |
| 4.2 | CMake (48.2) | `grep -c 'third_party/liblj92/lj92.c' CMakeLists.txt` → 1 |
| 4.3 | reader part 2 (48.3) | `grep -c 'inline bool readDngSamples' src/playback/DngFrameReader.hpp` → 1 |
| 4.4 | render look (48.4) | `grep -c 'inline Rgb8Image renderPreview' src/playback/RawRender.hpp` → 1 |
| 4.5 | histogram (48.4) | `grep -c 'inline std::array<float, 48> rawHistogram' src/playback/RawRender.hpp` → 1 |
| 4.6 | host round trip, parity and fuzz (KB tools) | `./playback_bench --synthetic /tmp/pb` ends `all ok`; `./parity_test …` ends `parity ok`; `./reader_fuzz …` ends `no crash` |
| 4.7 | `PlaybackFrames` (48.5) | `grep -c 'PlaybackFrames::frameJpeg' src/playback/PlaybackFrames.cpp` → 1 |
| 4.8 | reason phrases (48.6) | `grep -c 'Range Not Satisfiable' src/web/WebServer.cpp` → 1 |
| 4.9 | route (48.7) | `grep -c 'request.path == "/api/media/frame"' src/ApertarCoreApp.cpp` → 1 |

- §5: build, restart, then
  `curl -s -o /tmp/f.jpg -D - "http://127.0.0.1:8000/api/media/frame?kind=folder&id=<take>&frame=0&w=640&v=<token>"`
  (200, `X-Decode-Ms`, 48 numbers in `X-Histogram`); open `/tmp/f.jpg` beside the touch screen's frame (same look); ask
  three frames at once with `xargs -P 3` (one 503); start a take and ask again (409).
- §7 includes: "Core crashed on a frame" → keep the file, run `reader_fuzz` on it; "the picture differs from the touch
  screen" → the parity test on that file.

### T49-T53 (outline)

| Tutorial | Steps (plan rows) | Gate |
| --- | --- | --- |
| T49 Clip Browser | 4.1 CSS (49.1), 4.2 markup (49.2), 4.3 state (49.3), 4.4 open/close and the live view (49.4, 49.5), 4.5 cards (49.6), 4.6 thumbnails, select, remove, download (49.7), 4.7 the button in a take (49.8) | `node --check` of the page script; the mocked Chromium run (as for T32/T34) with 0, 1 and 12 clips, a held list and a refused delete; then the Pi on a phone and a laptop; count the live-view connections on the Pi before and after opening the browser (`ss -tn state established '( sport = :8000 )'`) |
| T50 Clip Viewer | 4.1-4.2 CSS and markup, 4.3 frames and clock, 4.4 scrub, 4.5 transport and prev/next, 4.6 histogram, 4.7 metadata, 4.8 remove and download, 4.9 holds and keep-awake, 4.10 keys, 4.11 the delete gate (50.7) | as T49, plus: play a Clear HDR take and a lossless take; record during playback; standby with a short timeout |
| T51 Sound | 4.1 range streamer, 4.2 route, 4.3 audio clock and sound-only items | `curl -s -D - -o /dev/null -H 'Range: bytes=0-99' '…/api/media/file?…'` → `206`, `Content-Range: bytes 0-99/…`; the phone plays and seeks |
| T52 MLV | 4.1 reader, 4.2 ISP render, 4.3 facts and frames | host test with Core's `MlvEncoder`; parity test against `MlvReader` |
| T53 ProRes/H.264 | 4.1 copy the two files, 4.2 CMake module, 4.3 loader, 4.4 facts and frames | `pkg-config --modversion libswscale` first (M10); then one ProRes and one H.264 take |

### Tutor blocks (anchors checked here: each string occurs once in its file at `0296ed1` / `5aab7e2`)

T47 note:

```
%% tutor
ref core src/ApertarCoreApp.cpp 6422 std::vector<MediaLibraryItem> discoverMediaLibraryItems(
ref core src/ApertarCoreApp.cpp 6492 : durationTextForFrameCount(stats.frameCount, fps);
ref core src/ApertarCoreApp.cpp 5609 struct MediaLibraryItem
ref core src/ApertarCoreApp.cpp 7819 std::string ApertarCoreApp::buildMediaLibraryJson() const
ref core src/ApertarCoreApp.cpp 7307 if (request.method == "GET" && request.path == "/api/media") {
ref core src/ApertarCoreApp.cpp 9413 std::string ApertarCoreApp::mediaGateError() const
ref core src/ApertarCoreApp.cpp 9489 return errorReply(command.id, "Wait for the current capture to finish writing to media.");
ref core src/ApertarCoreApp.cpp 8071 << ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")
ref core src/ApertarCoreApp.cpp 5887 std::string durationTextForFrameCount(uint64_t frameCount, double fps)
ref core src/ApertarCoreApp.hpp 105 std::string mediaGateError() const;
ref ui src/playbackcontroller.cpp 1149 void PlaybackController::updateClipMetadata()
ref ui src/playbackcontroller.cpp 135 QString formatDurationText(int frameCount, double fps)
ref ui src/playbackcontroller.cpp 121 QString formatByteSize(quint64 bytes)
ref ui src/cliplistmodel.cpp 147 QString durationTextForClip(int frameCount, double fps)
ref ui src/dngdecoder.cpp 1523 double DngDecoder::detectFrameRate(const QString &filePath)
check 4.1 | grep -c 'inline bool readDngInfo' /home/pi/ApertarCore/src/playback/DngFrameReader.hpp | ^1$
check 4.2 | grep -c 'inline ClipFacts probeClipFolder' /home/pi/ApertarCore/src/playback/ClipProbe.hpp | ^1$
check 4.5 | grep -c 'std::string ApertarCoreApp::playbackHoldReason' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.8 | grep -c 'request.path == "/api/media/clip"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.9 | grep -c 'playback_hold' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[1-9]
check 5.1 | curl -s -m 5 http://127.0.0.1:8000/api/state | "playback_hold":"
%%
```

T48 note:

```
%% tutor
ref core src/web/WebServer.cpp 70 case 503: return "Service Unavailable";
ref core CMakeLists.txt 6     LANGUAGES CXX
ref core CMakeLists.txt 76     src/cdng/LosslessJpegEncoder.cpp
ref core src/ApertarCoreApp.cpp 4199 const int rc = tjCompressFromYUVPlanes(compressor.handle,
ref core src/ApertarCoreApp.cpp 5258 std::optional<std::string> queryParameterValue(const std::string &query, const std::string &key)
ref ui src/cdngimageprovider.cpp 578 QImage renderRawPreviewImpl(const RawFrame &frame, const QSize &requestedSize, const Sample &sample,
ref ui src/dngdecoder.cpp 534 bins.append(std::pow(normalized, 0.65));
ref ui src/playbackcontroller.cpp 263 constexpr int kHistogramTargetSamples = 16000;
check 4.2 | grep -c 'third_party/liblj92/lj92.c' /home/pi/ApertarCore/CMakeLists.txt | ^1$
check 4.3 | grep -c 'inline bool readDngSamples' /home/pi/ApertarCore/src/playback/DngFrameReader.hpp | ^1$
check 4.4 | grep -c 'inline Rgb8Image renderPreview' /home/pi/ApertarCore/src/playback/RawRender.hpp | ^1$
check 4.8 | grep -c 'Range Not Satisfiable' /home/pi/ApertarCore/src/web/WebServer.cpp | ^1$
check 4.9 | grep -c 'request.path == "/api/media/frame"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
%%
```

T49 and T50 notes (refs; their checks follow the step tables the same way):

```
%% tutor
ref core src/web/WebControlPage.cpp 1137 .media-browser-overlay.hidden {
ref core src/web/WebControlPage.cpp 3979 <div class="media-browser-overlay hidden" id="mediaBrowserOverlay">
ref core src/web/WebControlPage.cpp 4246 mediaSelection: new Set(),
ref core src/web/WebControlPage.cpp 6176 function setMediaBrowserOpen(open) {
ref core src/web/WebControlPage.cpp 7596 function sortedMediaItems(items) {
ref core src/web/WebControlPage.cpp 7707 function renderMediaLibrary(payload) {
ref core src/web/WebControlPage.cpp 8597 function loadPreviewStream() {
ref core src/web/WebControlPage.cpp 8616 state.previewRetryTimer = window.setTimeout(loadPreviewStream, 1500);
ref core src/web/WebControlPage.cpp 9366 function renderSnapshot(snapshot) {
ref core src/web/WebControlPage.cpp 10403 async function fetchMediaLibrary(silent) {
ref core src/web/WebControlPage.cpp 10446 function downloadSelectedMediaItems() {
ref core src/web/WebControlPage.cpp 10468 async function deleteSelectedMediaItems() {
ref core src/web/WebControlPage.cpp 11558 document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});
ref core src/web/WebControlPage.cpp 11620 if (event.key === "Escape" && state.mediaBrowserOpen)
ref core src/web/WebControlPage.cpp 2447 <button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">
ref core src/ApertarCoreApp.cpp 7649 if (request.method == "POST" && request.path == "/api/media/delete") {
ref core src/ApertarCoreApp.cpp 7721 if (request.method == "POST" && request.path == "/api/media/delete-selected") {
ref ui qml/ClipBrowserPage.qml 179 text: root.stillMode ? "Still Browser" : "Clip Browser"
ref ui qml/ClipPlayerPage.qml 234 text: "Clip Viewer"
ref ui qml/ClipPlayerPage.qml 393 sourceSize.width: playbackController.playing
ref ui qml/CameraPage.qml 3754 enabled: !root.recording
ref ui src/playbackcontroller.cpp 749 void PlaybackController::handlePlaybackTick()
%%
```

T51-T53 notes add:

```
%% tutor
ref core src/ApertarCoreApp.cpp 6333 void streamFileToClient(int clientFd, const std::filesystem::path &path)
ref core src/ApertarCoreApp.cpp 6285 std::string mediaContentTypeForFile(const std::filesystem::path &path)
ref core CMakeLists.txt 140 if(LIBAV_FOUND)
ref core src/video/LibavH264EncoderClient.cpp 105 library_ = ::dlopen(candidate.c_str(), RTLD_NOW | RTLD_LOCAL);
ref ui src/MlvReader.cpp 153 bool MlvReader::open(const QString &path, QString *error)
ref ui src/VideoPlaybackLibav.cpp 137 int read(void *handle, int index, unsigned char *pixels, int width, int height,
ref ui CMakeLists.txt 139 add_library(apertar-video-libav MODULE src/VideoPlaybackLibav.cpp)
%%
```

---

## 8. Measurements on the Pi first (T46)

Shorthand `K=~/apertar-kb/working/tools`. All read-only except M5 (one setting, you restore it) and M7 (it records). Order:
M1, M2, M3, M4, M6, M8, M9, M10, then M5 and M7 if you want them. The sketch has to be in the KB first
(`working/tools/playback/`); this pass wrote nothing into the KB.

**M1. What one frame costs on the Pi.** The bench needs Core's sources and the libjpeg/libyaml headers (Core already builds
with them, PROBABLE).

```bash
cd $K/playback
gcc -O2 -c third_party/liblj92/lj92.c -o lj92.o
g++ -std=c++20 -O2 -DHAVE_JPEG -Isrc/playback -Ithird_party/liblj92 -I$HOME/ApertarCore/src -I$HOME/ApertarCore/include \
    playback_bench.cpp $HOME/ApertarCore/src/cdng/CdngEncoder.cpp $HOME/ApertarCore/src/cdng/LosslessJpegEncoder.cpp \
    $HOME/ApertarCore/src/color/ColorProfileConfig.cpp lj92.o -ljpeg -lyaml -lpthread -o playback_bench
./playback_bench --synthetic /tmp/pb-frames            # 36 ok lines, then per-frame times; "all ok"
ls -d /media/RAW/cDNG_* | tail -4                      # pick one Clear HDR 16-bit take and one SDR 12-bit lossless take
./playback_bench --cold /media/RAW/<hdr take>/*_000000010.dng /media/RAW/<sdr take>/*_000000010.dng
vcgencmd measure_temp                                  # before and after a 2-minute loop of the bench
```

Prediction: the synthetic times ≈ 2× the host table (§2.3); `--cold` adds 25-40 ms of read to the 16-bit uncompressed frame.
Decides the workers, the play width, row-selective reads, and whether O11 is needed (§2.10).

**M1b. Parity on the Pi, on your own frames** (the same test as §2.3, built against `~/ApertarUI`; the build line is at the
top of `parity/parity_test.cpp` in the KB copy). Prediction: `parity ok`. Decides nothing; it proves the copy on real takes.

**M2. The touch screen today, the baseline you are matching.** Open the same two takes on the touch screen. For 10 s count
how far "FRAME i / N" moves (stopwatch). Meanwhile, from SSH:

```bash
top -b -n 3 -d 2 -H -p "$(pgrep -f apertar-ui | head -1)" | head -30     # which threads, how much CPU
```

Prediction: the 16-bit uncompressed take near its rate; the lossless take well below (PROBABLE from §2.3).

**M3. How many small requests per second Core's server answers.** From the laptop on the camera's network, then on the Pi
against `127.0.0.1` (network vs server):

```bash
time (for i in $(seq 100); do curl -s -o /dev/null http://<pi>:8000/icons/play.png; done)            # one at a time
time (seq 100 | xargs -P 3 -I{} curl -s -o /dev/null http://<pi>:8000/icons/play.png)              # three at once
```

Prediction: well above 40 requests/s on the LAN (PROBABLE: one thread and one TCP connect each, F8). Decides the look-ahead.

**M4. What the list costs today.**

```bash
find /media/RAW -mindepth 1 -maxdepth 1 -type d | wc -l; find /media/RAW -type f | wc -l     # takes, files
for i in 1 2 3; do curl -s -o /dev/null -w '%{time_total}\n' http://127.0.0.1:8000/api/media; done
```

Decides whether the folder cache in T47 matters on your card (it scales with the file count).

**M5. Does passive playback hit standby?** (one change; you restore it)

```bash
curl -s http://127.0.0.1:8000/api/state | grep -o '"standby_timeout_seconds":[0-9]*'        # note it
# Patrik: WebUI Settings > Media > Camera Standby > After Inactivity: 1 min
# play a take on the touch screen, touch nothing for 90 s
curl -s http://127.0.0.1:8000/api/state | grep -oE '"(standby|state)":[^,]*'
# Patrik: restore the noted timeout
```

Prediction: standby comes (F17). Decides U2 and confirms §2.7's keep-awake.

**M6. Do your browsers play the take's WAV?**

```bash
scp pi@<pi>:/media/RAW/<take>/<take>.wav ~/Desktop/       # on the laptop
```

Open it in Chrome, Safari and Firefox (drag it into a tab), and on the phone (Files / AirDrop). Note: plays, seeks, length
right. Decides O13.

**M7 (optional; it records two takes, so you run it). Does reading an old take cost frames during a take?**

```bash
bash $K/takes.sh 1 60                                                                  # baseline: missing=0
( while true; do cat /media/RAW/<old take>/*_00000001?.dng > /dev/null; sleep 0.1; done ) &  # ~10 frames/s of reads
bash $K/takes.sh 1 60; kill %1
```

Decides Q4 (thumbnails in a take). The default holds everything, so this matters only if you want more.

**M8. The NVMe link and its read speed.**

```bash
cat /sys/class/nvme/nvme0/device/current_link_speed /sys/class/nvme/nvme0/device/current_link_width   # Gen 2 = 5.0 GT/s (sysfs path PROBABLE)
dd if=/media/RAW/<hdr take>/<take>_000000020.dng of=/dev/null bs=4M iflag=direct     # one cold 16.6 MB read, MB/s
```

Prediction: 5.0 GT/s x1 (the Gen 2 test, F25) and 350-450 MB/s. Decides whether 16-bit at 25 fps is read-bound (§2.8).

**M9. The Pi's locale.** `locale | head -3`. Decides the month names (Q15).

**M10 (before T53).** `pkg-config --modversion libswscale` and `ls ~/ApertarUI/build*/apertar-video-libav.so`. Decides
whether T53 needs `libswscale-dev` installed first (you).

**M11 (after T48 and T50).** The frame route's `X-Decode-Ms` over 50 frames, `top -H -p $(pgrep apertar-core)` while the
browser plays, read MB/s from `cat /proc/diskstats`, the temperature. With O4 the page shows Achieved and Skipped; without
it, count requests in the browser's network panel.

---

## 9. Options for Patrik (not defaults)

### 9.1 Cinemate's features

| # | Option | Cinemate source | Cost (PROBABLE) | My suggestion |
| --- | --- | --- | --- | --- |
| O1 | Frame step ◀ ▶ and first / last frame; arrow keys on a laptop | `cm:…/settings_editor.html:2618-2627`, `6716-6720` (r1) | ~60 lines WebUI | yes |
| O2 | Loop toggle (off = stop on the last frame) | r1 §1.5 | ~20 | if you want play-once |
| O3 | Conform-rate playback with "0.50× SLOMO" / "2.00× FAST" | r1 §1.4 | ~60 WebUI + a conform setting | later, with T31 ramp takes |
| O4 | Honest rate row: Recorded, Playing at, Achieved, Frames skipped | r1 §1.4, lesson 2 | ~50 | yes: lossless takes will skip |
| O5 | DROP N badge on the card and in the viewer | r1 §1.4; Core's `dropped_frames` exists after T47 | ~20 | yes |
| O6 | Filmstrip scrubber (16 frames under the bar) | r1 §1.2 | ~80 + 16 decodes per clip | no |
| O7 | Sort "Largest first"; a "One row" strip view | r1 §1.2 | ~30 | no |
| O8 | Card mini-scrub (24-frame flip) | r1 §1.6 | ~70 + decodes | no |
| O9 | Mode boxes: 12b/16b, HDR/SDR, LIN/companded, LJ92/UNC, WAV | r1 §1.4 | ~30 (facts exist after T47) | maybe, in the metadata panel |
| O10 | Timecode readout: the **recorded** SMPTE start (tag 51043) + frame offset, not Cinemate's position ÷ rate | r1 §1.5 | ~40 | yes |
| O11 | The recorder writes a preview: a per-take preview track (sidecar), full-rate playback of lossless takes on both screens | r1 §3 (Cinemate: IFD1 per DNG) | ~400 Core incl. the copy worker; per-frame CPU in every take (UNCONFIRMED; Cinemate +4 ms) | only if M1/M2 say lossless is too choppy for you |
| O12 | H.264 through the browser's `<video>` (decodes on the phone, full rate) | — | ~60 WebUI; needs T51's Range | if T53's H.264 is slow |
| O13 | Core serves a 16-bit copy of the WAV for browsers that refuse s24 or float | — | ~80 | only if M6 fails |
| O14 | Thumbnails kept on the system drive (`~/.cache/apertar-core/thumbs/`), so a Core restart does not decode every card again | Cinemate keeps them in the browser for an hour (r1 §2.4) | ~60 | if the first fill after a restart annoys you |

### 9.2 Kept from today's WebUI beyond the touch UI

Download (viewer and selection), Select All, and the Timelapse and Audio categories are defaults (D3, D13). One more is an
option:

| # | Option | Cost | My suggestion |
| --- | --- | --- | --- |
| W1 | Today's stat chips (frames, FPS, size) as a fourth card line | ~15 | no: the touch card shows four things; the rest is in Clip Metadata |

---

## 10. Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Lossless 4K plays at ~5-8 fps on the Pi | PROBABLE (§2.3) | the touch UI has the same limit; O4 makes it visible; the LRU smooths replays; O11 if you want full rate |
| R2 | 16-bit uncompressed playback at 25 fps reads 415 MB/s and keeps ~2 cores busy; heat | PROBABLE (F25, §2.3) | only when idle; 2 workers at nice 10; M1 temperature; M8 link; row-selective reads; 480 w |
| R3 | A new TCP connection and thread per frame (`Connection: close`) | CONFIRMED mechanism (F8); cost UNCONFIRMED | M3; look-ahead 1-2; keep-alive later |
| R4 | A browser cannot play the s24 WAV | UNCONFIRMED | M6; silent with a notice; O13 |
| R5 | Safari needs Range for media | PROBABLE | T51 adds Range |
| R6 | A reader bug in Core's process | PROBABLE risk; mitigations CONFIRMED in the sketch | bounds checks; fuzz in the gate (480 runs clean here); exceptions caught per client thread (`WS:279-284`). If the Pi ever crashes on a file, move decoding into a helper process |
| R7 | The named copies (reader, render, histogram, text, MLV) drift from the touch UI | PROBABLE over time | the parity test in the KB; both files name each other; every U-change goes into both |
| R8 | The new list (cards) loses one of today's flows | PROBABLE | T49 keeps today's fetch, download and delete functions and replaces only the rendering; the mocked Chromium gate covers download, delete and Select All |
| R9 | Touch UI root `/media/RAW` vs Core `--media` | CONFIRMED facts (r4 K20) | the same on your Pi (PROBABLE); `media_root` in every reply |
| R10 | T31 ramp takes number frames by count, so `dropped_frames` reads 0 | PROBABLE (r4 F8) | a note in the metadata; O5 says "drops unknown" for ramp takes once T31 lands |
| R11 | The controls project (T36-T45) edits the same files first | CONFIRMED (F29; both edit `App`, `Web`, `WS`) | search strings, not line numbers; `tutorial.py refs` before each tutorial; 409 added once |
| R12 | The WebUI viewer and the touch UI play at once: two decoders | PROBABLE, rare | Core's slots bound its share |
| R13 | Keep-awake while playing costs battery | PROBABLE, small | only while playing |
| R14 | The movie plugin brings a second FFmpeg into Core's process (the ProRes plugin may use a private FFmpeg, `CMake:46-64`) | PROBABLE risk | `RTLD_LOCAL` and versioned FFmpeg sonames keep them apart (PROBABLE); the plugin loads only on the first movie frame, never in a take; T53 tests a ProRes take after a movie was played |
| R15 | Month names differ between the screens (F23) | PROBABLE if the Pi is not English | M9; Q15 |

---

## 11. Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Is a WebUI viewer that shows lossless 4K takes at ~5-8 fps (the touch screen's limit too) good enough for now, with O11 later if not? | yes; decide after T46 |
| Q2 | Should the WebUI's "Show" button only filter the list, or switch the camera's photo mode like the touch UI? | filter only (D1) |
| Q3 | Keep Download, Select All and the Timelapse and Audio categories in the new browser? | yes (D3, D13) |
| Q4 | In a take, hold everything (frames, thumbnails, sound), or let cached thumbnails through? | hold everything |
| Q5 | Grey the WebUI folder button in a take, like the touch UI's? (Then downloads in a take need the browser opened before.) | greyed |
| Q6 | BIT DEPTH: the stored depth ("12-bit, companded") in the WebUI, and fix the touch UI later (U5)? | yes (D9) |
| Q7 | Touch-UI quirks: fix the wording ("1 item"); copy the one-channel 4K histogram for parity until U6 fixes both? | yes, yes |
| Q8 | Without a WAV, skip late frames (wall clock) instead of slowing down like the touch UI? | skip (D8) |
| Q9 | Which Cinemate options do you want? | O1, O4, O5, O10 |
| Q10 | Your phone: iPhone (Safari) or Android (Chrome)? | design for both; test on yours |
| Q11 | Keep the camera awake while a clip plays (not while paused)? | yes |
| Q12 | Numbering T46-T53; and type the reader and renderer (~600 lines) or copy them from the KB after reading? | T46-T53; your call on typing |
| Q13 | Commit format: house format (area, imperative, Why, Tested, no Co-Authored-By) or what your recent commits use (`What:` + Co-Authored-By)? (r4 K18) | ask |
| Q14 | Later: should the touch UI take its clip facts, thumbnails and deletes from Core (U3, U4, U8), so both screens share one truth? | later, after T50 |
| Q15 | Month names: the touch UI uses the Pi's locale (F23). If M9 is not English, should Core follow the locale too? | follow the Pi's locale |
| Q16 | Movie decoder: Core builds its own copy of `apertar-video-libav.so` from the same two files (default), or loads the touch UI's installed one? | Core's own copy |
| Q17 | Order: playback after the controls project (T36-T45), or between? | after controls |
| Q18 | Space for play/pause on a laptop (D12)? | yes |

---

## 12. What changed from the paused draft, and why

The draft's structure, recommendation (A), sketch, interlock table, budget, maps and options were checked and kept. These
points changed:

| # | Draft | Now | Why |
| --- | --- | --- | --- |
| C1 | T40-T47 | T46-T53 | the controls project took T36-T45 |
| C2 | A socket command `get_clip_info` (also via `/api/command`) | HTTP route only | `handleCommand` holds `commandMutex_` for every command (F9): a slow folder read on a pulled NVMe would block `record_stop`; `tutorial.py` would refuse a check that calls it (F28); today's media library is HTTP-only too |
| C3 | Change `buildHttpResponse` / `buildStreamingHttpHeader` to let a handler set `Cache-Control` (medium risk, every response) | no change; Core's JPEG LRU and the page's memory serve revisits | same effect for playback without touching every response |
| C4 | Core `dlopen`s the touch UI's installed `apertar-video-libav.so` | Core builds the same two source files as its own lazy plugin | no runtime dependency on the UI's install path; Core's existing plugin pattern (F10); Q16 keeps the other way open |
| C5 | — | a decode in flight stops at the next tile when a hold starts; scratch freed on a hold | a take starting mid-decode would otherwise read up to a whole frame from the card |
| C6 | Holds: recording, writing, standby, media | + `media_test`; `media` respects the media-gate switch (F15) | a speed test measures the drive; the desk machine has no mount |
| C7 | Breakpoints 720 / 1100 / 1024 | the WebUI's own 720 / 1120 | Apertar style: one set of breakpoints; Settings changes shape at 1120 |
| C8 | Duration "mm:ss / h:mm:ss" | the touch UI's two exact rules (card and metadata, F22) | r2 wrote "1:02:03" for the card; the code writes "01:02:03" (`CLM:159-164`) |
| C9 | Lossy DNG parity PROBABLE | CONFIRMED on Core's own `LossyDngEncoder` frames (0 differing) | new host test in this session |
| C10 | `v` token not checked | a stale `v` gets 404 "The clip changed. Refresh Media." | covers a folder name reused after a delete (F6) with the page's memory cache |
| C11 | Download only in selection | also in the viewer | per-item download exists in today's rows; the touch card has no place for it, the viewer does |
| C12 | — | `mounted` in the list follows the watcher | the mount table keeps a pulled medium listed (`App:7874-7876`) |
| C13 | "no check pipes one command into another" | pipes are allowed, written without spaces | `TP:119-123` splits on ` \| ` only; `TP:167-200` checks each stage |
| C14 | nice 10 for the decode, "restored after" | nice 10, nothing restored | each request has its own thread (F8); an unprivileged thread cannot lower its nice value again |
| C15 | lossless cost 159-171 ms | 159-189 ms | two re-runs in this session; the host varies by ~10 % |

---

## Appendix A. The sketch

Folder: `scratchpad/playback/sketch/` (in no repository; it moves to the KB's `working/tools/playback/` with v2).

| File | Lines | What |
| --- | --- | --- |
| `src/playback/DngFrameReader.hpp` | 372 | tail-IFD reader, payload unpack, LJ92 tiles, LinearizationTable, bounds checks |
| `src/playback/RawRender.hpp` | 226 | the touch UI's look (`CIP:380-698`) and histogram (`DD:455-536`) |
| `third_party/liblj92/` | — | the touch UI's files; `cmp` identical |
| `playback_bench.cpp` | 251 | `--synthetic DIR` (Core's encoder → reader, 36 checks, timings) and `[--cold] FILE.dng…` (timings on real frames) |
| `reader_fuzz.cpp` | 45 | truncated and byte-flipped copies under ASan/UBSan |
| `parity/parity_test.cpp`, `parity/ui_time.cpp` | 45, 28 | the copy vs the touch UI's own `DngDecoder` and renderer (Qt 6), and the touch UI's own timings |
| `lossy/lossy_write.cpp` | 44 | new in this session: 4K 12-bit frames from Core's `LossyDngEncoder` (3:1, 5:1) for the parity test and the bench |
| `results-host.txt` | | the numbers in §2.3 (first run); re-runs in this session vary by up to ~10 % (host load) |

Build lines are at the top of `playback_bench.cpp`. The parity test needs Qt 6 (Core, Gui, Quick), libtiff and `moc`
(`moc ui/src/cdngimageprovider.h`). The lossy writer builds with
`g++ -std=c++20 -O2 -I$CORE/src -I$CORE/include lossy_write.cpp $CORE/src/lossydng/LossyDngEncoder.cpp $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp -lyaml -lpthread`.
This host: g++ 13.3, Qt 6.4.2, 4 threads of a Xeon at 2.1 GHz.

## Appendix B. Touch-UI colours → WebUI tokens

| Touch UI (`CBP`, `CPP`; r2 Appendix A) | Use | WebUI token or part (F26) |
| --- | --- | --- |
| `#000000` page | page | the overlay shell `rgba(9,9,11,.96)`; full bleed below 720 px |
| `#151515` sheet, dialogs | sheet | `--surface-2` `#111113` |
| `#181818` card, summary box, side panel | card | `--surface` `#18181b` |
| `#171717` thumbnail / preview background | picture box | `--surface-3` `#171717` (same) |
| `rgba(255,255,255,.10)` 1 px borders | borders | `--card-border` `#27272a` |
| `rgba(255,255,255,.078)` ghost button, count chip, histogram card | buttons | `.secondary-button` |
| `rgba(0,0,0,.40)` badges, duration pill | pills on pictures | `.badge` (`rgba(0,0,0,.7)`, blur) |
| `#8d2020` / `#a32828` / `#ba4a4a` danger | Remove | `.danger-button` |
| `#3fd0ff` / `#79ddff` / `#1f2c36` accent | sort chip, Show | the `#3fd0ff` border of `.secondary-button.standby-button` |
| `rgba(255,255,255,.40)` eyebrow, metadata labels | labels | `--muted-2` `#71717a` |
| `#8f9096` / `#6f7076` / `#5f6066` secondary, tertiary, date text | text | `--muted` `#a1a1aa`, `--muted-2` |
| `#1e1f23` / `#d7d9de` / `#f4f5f7` scrub rail / fill / handle | scrub | `--surface`, `#d4d4d8`, `#f4f4f5` (the WebUI's light greys) |
| radii 28 / 24 / 18 / 14 | sheet / card / thumb / pill | `--radius-xl` 28 / `--radius-lg` 22 / `--radius-md` 18 / `--radius-sm` 14 |
