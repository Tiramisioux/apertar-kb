# WebUI playback in the touch UI's shape: how it works, what to build, what to measure first

2026-10-28, cloud session, designer pass (v1). Built from the four reader reports in this folder (`r1-cinemate-playback.md`,
`r2-apertar-ui-player.md`, `r3-apertar-core-media-web.md`, `r4-kb-playback.md`). Every point the design rests on was reopened in
the code; points taken from a report without reopening are marked "(rN)". Read-only on every repository. Nothing ran on the Pi.
One sketch was compiled and run on this host: a Qt-free DNG reader and a copy of the touch UI's render look, checked against
Core's own encoder and against the touch UI's own decoder (§2.2, Appendix A).

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `App`, `App.hpp`, `WS`, `Web` | `src/ApertarCoreApp.cpp`, `.hpp`, `src/web/WebServer.cpp`, `src/web/WebControlPage.cpp` | Core, Patrik's GitHub `cinemate-port` tip `eb9cc39` (`scratchpad/controls/core-tip`) |
| `CC`, `Cdng`, `LJE`, `IFD`, `Mlv`, `CMake` | `src/camera/CameraController.cpp`, `src/cdng/CdngEncoder.cpp`, `src/cdng/LosslessJpegEncoder.cpp`, `src/cdng/IfdBuilder.hpp`, `src/mlv/MlvEncoder.cpp`, `CMakeLists.txt` | same |
| `CBP`, `CPP`, `Main`, `CamP` | `qml/ClipBrowserPage.qml`, `qml/ClipPlayerPage.qml`, `qml/Main.qml`, `qml/CameraPage.qml` | touch UI, GitHub `cinemate-port` tip `d8098d0` (`scratchpad/controls/ui-tip`) |
| `PC`, `CLM`, `CIP`, `DD`, `MLR`, `VPL`, `VPA` | `src/playbackcontroller.cpp`, `src/cliplistmodel.cpp`, `src/cdngimageprovider.cpp`, `src/dngdecoder.cpp`, `src/MlvReader.cpp`, `src/VideoPlaybackLibav.cpp`, `src/VideoPlaybackApi.h` | same |
| `cm:` | Cinemate `dev` | `d6cc93e` (`/home/user/tiramisioux/cinemate`) |
| `kb:` | Apertar KB | `e35ffa7` |
| `sketch/` | design sketch, not in any repository | `scratchpad/playback/sketch/` |

Labels: **CONFIRMED** = I opened the line or ran the command. **CONFIRMED (rN)** = reader N opened it; I did not reopen it.
**PROBABLE** = derived; the derivation is given. **UNCONFIRMED** = not checked, or only the Pi can settle it. A bare
"(rN §x)" without a label points to where a report explains the point.

Tutorial numbers: T33-T35 are taken and the controls project uses T36-T39, so this project starts at **T40** (Patrik may
renumber). `tutorial.py` needs `T` + two digits, so no "T42a" (T34 design §0, CONFIRMED there).

| Number | What |
| --- | --- |
| T40 | Measure first: what a playback frame costs on the Pi, what Core's server delivers, what the browsers play. No code |
| T41 | Core knows its clips: per-clip facts from the files (fixes the list's FPS and duration), `/api/media/clip`, `playback_hold` |
| T42 | Core draws a frame: `/api/media/frame` for cDNG, with the touch UI's look |
| T43 | WebUI Clip Browser in the touch UI's shape (cards, thumbnails, sort, select, remove, download kept) |
| T44 | WebUI Clip Viewer (preview, badges, scrub, transport, histogram, metadata, remove, holds) |
| T45 | Sound: the WAV in the browser, with HTTP Range in Core |
| T46 | MLV clips |
| T47 | ProRes and H.264 clips, through the touch UI's own video plugin |

---

## 0. Short answer

1. The WebUI's folder button opens a full-screen **Clip Browser** and **Clip Viewer** laid out, worded and behaving like the
   touch UI's (`CBP`, `CPP`), drawn with the WebUI's buttons, pills and cards. It replaces today's list overlay; Download stays.
2. Pictures: **Core decodes on demand** and sends one JPEG per request. Nothing changes in the recording path or in the DNGs.
3. Same look as the touch screen: Core gets a Qt-free copy of the touch UI's decoder rules and render look, plus the **same
   liblj92 file**. Checked here: 0 differing pixels and identical histograms against the touch UI's own code (§2.2).
4. Cost per 4K frame on this host, one thread: uncompressed ~37-41 ms (about 25 fps), lossless ~160-170 ms (about 6 fps).
   The touch UI's own path costs the same. The Pi is slower (PROBABLE ~2×): Clear HDR 16-bit uncompressed takes should play
   near 25 fps with two workers; SDR 12-bit lossless takes will skip frames, as they probably do on the touch screen today.
5. Recording wins. Every playback route answers 409 while recording, sound recording, timelapse, pending writes, standby or
   missing media. One Core function decides; `/api/state` carries it as `playback_hold`. The list is served from cache in a take.
6. Sound plays in the browser from the take's WAV. Core gains HTTP Range for that one route. The audio clock drives the
   frame index, as on the touch UI.
7. Shared with the touch UI: liblj92 (same file), the video plugin (same `.so`, T47), the rules for render, histogram and
   per-clip text (named copies with a parity test). Not shared: QML vs HTML, caches, audio output. The touch UI is unchanged.
8. Core API, in the style of `/api/media/*`: list (fixed), `clip`, `frame`, `file` (Range), the existing delete, plus
   `get_clip_info` on the socket. No change in `CameraController.cpp`.
9. Plan: T40 measure, T41-T47 build. About 3,100 lines (PROBABLE); ~600 of them are already written and host-tested in the sketch.
10. Cinemate's extras are options O1-O10 (step, loop, conform rate, honest rate row, DROP N, filmstrip, ...). Its
    "recorder writes a preview" is O11, to decide after T40 if lossless playback is too choppy. Your calls: Q1, Q2, Q9.

---

## 1. How the system works today

### 1.1 Operator view: three playback surfaces

| Surface | Where | What you get | What it lacks |
| --- | --- | --- | --- |
| Touch UI Clip Browser and Clip Viewer | Folder button on the camera page (greyed in a take, `CamP:3754`), or the hardware action `clip_browser` (`Main:319-322`) | Grid of 16:9 cards (2/3/4 columns), sort Newest/Oldest, long-press selection, Remove Selected. Viewer: preview with FPS, PLAYING/PAUSED and FRAME i / N badges; scrub bar; prev clip / play / next clip; Remove; 48-bar histogram; Clip Metadata (9 fields). Sound out of the Pi via `aplay`. Opens paused on frame 1, loops forever | Frame step, speed, loop toggle, a recording hold, a timecode. CONFIRMED (r2 §2-3), spot-checked `CBP:179`, `CPP:234`, `PC:749-775`, `PC:996` |
| WebUI Clip Browser | Folder button `mediaBrowserButton` in the top bar (`Web:2447`) | Centred overlay: Clips / Stills / Timelapse / Audio filters, count, Refresh Media, sort, rows with Download and Delete, Select All (`Web:3979-4030`) | Thumbnails, any picture, any player. CONFIRMED |
| Cinemate Playback pane | Settings editor tab "Playback" | Take strip, black stage, filmstrip scrub, first/prev/play/next/last, loop, HUD, rate row (Achieved, Frames skipped), conform rate. Locked in a take | Sound, delete, the touch UI's shape. CONFIRMED (r1 §1) |

The WebUI list is wrong today in two ways a player would inherit:

- Every clip's FPS is the camera's **current** FPS, and a cDNG duration is frames ÷ that FPS (`App:6490-6493`, `App:7821-7824`).
  A 50 fps take listed while the camera is at 25 shows "25 FPS" and twice its length. CONFIRMED code; the example is arithmetic.
- MLV, H.264 and ProRes show duration `--` (`App:6490-6491`). CONFIRMED.

### 1.2 Code view: where clips, frames and sound come from today

| Step | Touch UI (`d8098d0`) | Core / WebUI (`eb9cc39`) | Cinemate |
| --- | --- | --- | --- |
| Clip list | `ClipListModel` scans `/media/RAW` itself (hard-coded, `CLM:174`), on the GUI thread, on every open; reads the **whole** first DNG of each take to find its frame rate (`DD:1523-1530`, `readAll`) | `GET /api/media` → `discoverMediaLibraryItems` walks and stats every file on each call (`App:6422-6497`) | index from first-frame tags, every 3 s (r1 §2.4) |
| A picture | full raw decode in the UI process: libtiff + liblj92, quad debayer, fixed look (`CIP:577-698`) | none: no reader, no decoder; DNGs carry no preview (§1.3 F1) | the JPEG cinepi-raw embeds in each DNG (IFD1), served as is (r1 §2.3) |
| Sound | `aplay` subprocess fed from the WAV (`PC:996`) | none | a WAV route nobody calls (r1 §0) |
| In a take | browser button greyed; hardware action, playback and delete not blocked (r2 §7) | media delete refused (`App:7660-7666`); downloads allowed | frames and WAV answer 409 (r1 §2.6) |

### 1.3 Facts every design must respect

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | Core's DNG: 8-byte header, payload at offset 8, IFD0 + EXIF at the **end**; `NewSubFileType` 0; next-IFD word 0. No thumbnail, no SubIFD | CONFIRMED `Cdng:1384-1392`, `Cdng:1528-1529`, `IFD:123` |
| F2 | Uncompressed payload: 16-bit little-endian, or 12/10-bit packed MSB first | CONFIRMED `Cdng:1155-1184`, `Cdng:1849-1858` |
| F3 | Lossless payload: SOF3, 2 components, full-width tiles of 128 rows (`APERTAR_CDNG_TILE_ROWS`) | CONFIRMED `Cdng:52-67`, `Cdng:1237-1241`, `Cdng:1540-1543`, `LJE:111-162` |
| F4 | A frame's number comes from its timestamp, so a drop leaves a gap in the file numbers | CONFIRMED `CC:3780-3788`, `CC:4214-4221` |
| F5 | Tags a player needs are all in IFD0/EXIF: size, bits, compression, CFA, black/white, LinearizationTable, ColorMatrix1/2, ForwardMatrix1/2, AsShotNeutral, AnalogBalance, DateTimeOriginal, TimeCodes, FrameRate, PageName | CONFIRMED `Cdng:1529-1627`, `Cdng:1644-1652` |
| F6 | The web server: one detached thread per connection, max 32, 5 s socket timeouts, `Connection: close`, `Cache-Control: no-store` written before the handler's headers, no Range, reason phrases only for 200/204/400/403/404/405/413/500/503 | CONFIRMED `WS:59-73`, `WS:127-154`, `WS:263-273` |
| F7 | Core's main binary links no libav; libav lives only in lazily loaded plugins | CONFIRMED `CMake:69-130`, `CMake:140-170` |
| F8 | Core has a TurboJPEG (FASTDCT) encoder from YUV planes, inside App's anonymous namespace | CONFIRMED `App:4165-4214` |
| F9 | The touch UI's decoders are Qt-bound (`QVector`, `QImage`, `QFile`), except **liblj92** (MIT, plain C) and the **movie plugin** (C ABI v2, BGRA out, ≤1920 px) | CONFIRMED `rawframe.h:3`, `dngdecoder.h:3-4`, `MlvReader.hpp:5-7`, `VPA:1-27`, `VPL:1-8`, `VPL:137-142`, `third_party/liblj92/README.apertar.md` |
| F10 | Clip folders: `cDNG_yy-mm-dd_C0001/<clip>_<9 digits>.dng`; `MLV_…/<clip>.MLV`; `H264_…/<clip>.mp4` (`.mp4.writing` in a take); `ProRes_…/<clip>.mov`; `<clip>.wav` beside any of them; containers carry no audio | CONFIRMED (r3 §1.2-1.3) |
| F11 | Signals a playback route can read without the command lock: `isRecording`, `soundRecordingActive`, `timelapseActive`, `mediaWritesPending`, `state()`, `mediaSnapshot()` | CONFIRMED `App:7860-7871` (state builder), `App:9487-9489` (pending writes), `App:9605` (standby) |
| F12 | Media delete is refused while recording, sound recording or timelapse, but not while writes are pending | CONFIRMED `App:7660-7666`, `App:7732` |
| F13 | Only commands count as activity for standby; the WebUI pings `user_activity` on pointerdown/keydown | CONFIRMED `App:9508-9514`, `Web:11546-11559` |
| F14 | The live MJPEG downscale runs on libcamera's completion thread while a viewer is connected; opening the media overlay does not stop it | CONFIRMED (r3 §3.5) for the thread; CONFIRMED `Web:6176-6184` for the overlay |
| F15 | Touch UI player: opens paused on frame 0 (badge "FRAME 1 / N"), plays at 75 % of the preview box, loops, cDNG fps clamped 1-60, audio clock drives frames when a WAV plays | CONFIRMED `PC:560-571`, `PC:619-621`, `PC:749-775`; 75 % (r2 §4.3) |
| F16 | Touch UI histogram: 48 bins, ~16,000 raw samples on a square grid, step `floor(sqrt(N/16000))`, bin = (count/max)^0.65 | CONFIRMED `DD:488-491`, `DD:505-536`, `PC:262-263` |
| F17 | On a 4K frame that step is 22, an even number, so every sample lands on the same CFA site (red in RGGB) | PROBABLE (arithmetic from F16) |
| F18 | Lossless 4K SDR at 25 fps already drops frames in the encoder; 30 fps is limited by libcamera's thread; memory traffic alone costs frames | CONFIRMED (r3 §4.1, `kb:lessons/hardware-log.md:87,108-113,158-165`) |
| F19 | Pi 5 NVMe: 437 MB/s at Gen 2, 818 MB/s burst at Gen 3; a 16-bit 4K frame is 16.6 MB, so 25 fps of them is 415 MB/s | CONFIRMED (T34 design F9; `kb:lessons/hardware-log.md:140`) |
| F20 | The web icons `play`, `pause`, `next`, `previous`, `film`, `refresh`, `delete`, `info`, `folder` are already in `src/web/icons` | CONFIRMED (`ls`) |

---

## 2. The decisions

### 2.1 Frames: where the picture comes from

| | A. Core decodes on demand | B. Recorder writes a JPEG per DNG (Cinemate, IFD1) | C. Recorder writes a preview track per take (sidecar) | D. Touch UI serves frames | E. Browser decodes raw |
| --- | --- | --- | --- | --- | --- |
| Change in the recording path | none | per-frame JPEG in the copy worker, IFD patch in `CdngEncoder` (both uncompressed template and lossless) | per-frame JPEG + one appended file per take | none | none |
| Takes already on the card | all play | only new takes | only new takes | all | all |
| DNG files | unchanged | changed (+10-25 KB, chained IFD1; Resolve/Adobe acceptance UNCONFIRMED, r1 §3.2) | unchanged | unchanged | unchanged |
| Look | the touch UI's (same rules, §2.2) | the ISP preview look | the ISP preview look | the touch UI's | whatever the page codes |
| Lossless 4K playback rate | low (PROBABLE ~5-8 fps on the Pi with two workers) | full | full | low, and in the UI process | impractical: 7.7-16.6 MB per frame over Wi-Fi |
| MLV / movies | MLV yes (T46); movies via the plugin (T47) | no | yes | yes | no |
| Front door | Core | Core | Core | **the UI process** (no HTTP server, no command for frames; absent in monitor-only mode) | Core serves files only |
| Risk | decode code inside Core's process (§9 R6) | the hot path of every take (F18) | the hot path of every take | breaks "Core is the one front door" | — |

**Recommendation: A**, with C kept as option O11.

- A changes nothing that can cost a take. The record path is already at its limit (F18), and Cinemate itself measured +4 ms
  (+18 %) of encode per frame for its JPEG (r1 §3.3).
- A plays every take already on the card, and plays it with the touch screen's look, which is what "similar to the touch UI" asks.
- A's weak point is lossless 4K. The touch UI has the same weak point today (§2.2). If T40 shows it is too choppy for you,
  O11 (C) fixes it for both UIs at once, because both could read the preview track.
- C over B, if it is ever built: the DNGs stay byte-identical (no Resolve question), and MLV and movies are covered too.
- D and E are rejected for the reasons in the table.

### 2.2 What the sketch measured (this host, not the Pi)

The sketch (`sketch/`, Appendix A) has three parts. `src/playback/DngFrameReader.hpp` (372 lines) reads Core's DNGs
without Qt or libtiff. `src/playback/RawRender.hpp` (226 lines) copies the touch UI's look and histogram. `third_party/liblj92`
is the touch UI's file, copied and checked with `cmp`.

**Correctness.** Core's own `CdngEncoder` wrote 4K frames: 12-bit and 16-bit, each uncompressed and lossless.

| Check | Result | Label |
| --- | --- | --- |
| Reader round trip: size, bits, compression, FrameRate 25, PageName, DateTimeOriginal, matrices, every sample bit-exact | 36 of 36 | CONFIRMED (run here) |
| Tags cost one read of the file's tail | 1,448 B uncompressed, 1,596 B lossless | CONFIRMED |
| The same frames through the **touch UI's own** `DngDecoder` + `renderRawFramePreview` (built with Qt 6 here) vs the copy | samples differ 0; 640x360 pixels differing 0; histogram max bin difference 0.0000; black and white levels equal | CONFIRMED (run here, `sketch/parity/parity_test.cpp`) |
| Fuzz: 480 truncated or byte-flipped copies, AddressSanitizer + UBSan | 306 rejected with an error, 174 decoded, no sanitizer report | CONFIRMED (after adding the size checks now in the sketch) |

**Cost per frame, one thread, warm page cache** (Xeon 2.1 GHz; synthetic scene with sensor-like noise; 12-bit lossless at 62 % of raw, the 16-bit synthetic hardly compresses, 93 %):

| Frame | Payload | Read + unpack/decode | Render 640 w | Render 1920 w | Histogram | JPEG q80 | One 640 w frame | Per worker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4K SDR 12-bit uncompressed | 12.4 MB | 19.5 ms | 15.5 ms | 142 ms | 0.15 ms | ~1.5 ms (26.5 KB at 960 w) | 37 ms | 27 fps |
| 4K SDR 12-bit lossless | 7.7 MB | 139 ms | 18.2 ms | 147 ms | 0.17 ms | ~1.5 ms | 159 ms | 6.3 fps |
| 4K Clear HDR 16-bit uncompressed | 16.6 MB | 22.7 ms | 16.2 ms | 160 ms | 0.16 ms | ~1.5 ms | 41 ms | 24.6 fps |
| 4K 16-bit lossless | 15.4 MB | 154 ms | 15.5 ms | 132 ms | 0.15 ms | ~1.3 ms | 171 ms | 5.8 fps |
| The touch UI's own path, same files | | decode 16-19 ms uncompressed, 133-170 ms lossless | render 19-25 ms | | | | | |

All rows CONFIRMED on this host (`sketch/results-host.txt`). For the Pi (PROBABLE, not measured): a Pi 5 core is roughly half
as fast as this one (published single-core scores), and a cold 16.6 MB read from NVMe takes 24-40 ms more (F19). So about
55-100 ms per uncompressed 640 w frame (two workers: ~20-35 fps) and 250-450 ms per lossless one (two workers: ~5-8 fps). T40
measures it with the same tool on real takes.

### 2.3 What is shared with the touch UI, and what is not

| Thing | Shared how | Why |
| --- | --- | --- |
| Lossless JPEG decoder | **Same file**: `ApertarUI/third_party/liblj92/lj92.c` copied to `ApertarCore/third_party/liblj92/`, `cmp` shows it identical | Plain C, MIT, already carries the touch UI's local fix (README.apertar.md). A copy of a vendored file is how both repos already work |
| Movie decoder (ProRes, H.264) | **Same binary**: Core loads the touch UI's `apertar-video-libav.so` through its C ABI v2 (T47) | Qt-free, versioned ABI (F9). Core already loads libav lazily (F7). No second FFmpeg decoder to keep |
| DNG reading, render look, histogram, metadata text, clip rules, MLV rules | **Named copies** in `src/playback/*.hpp`, each with a comment naming its touch-UI source, and a parity test that builds both | The touch UI's versions are Qt-bound (F9). KB rule M5: name every copy, give it a check (`kb:llm/README.md:102-106`). The parity test exists (§2.2) |
| Thumbnails | Not shared by default. Core renders and caches its own; the touch UI keeps its own | Option U4 lets the touch UI load Core's over `http://127.0.0.1:8000` (one cache) |
| Toolkit, layout code | Not shared: QML vs HTML/CSS/JS | Different runtimes; the design copies the layout, not the code |
| Sound | Not shared: `aplay` on the Pi vs `<audio>` in the browser | The WebUI viewer is on your phone or laptop |
| Media root | Not shared today: touch UI `/media/RAW` hard-coded (`CLM:174`), Core `--media` | Same folder on your Pi (PROBABLE); R9 |

### 2.4 MLV, H.264 and ProRes

| Format | Picture in the WebUI | Facts | When |
| --- | --- | --- | --- |
| cDNG uncompressed, lossless, lossy 3:1/5:1 | Core decode (§2.1 A) | first-frame tail (F5) | T41, T42 |
| DNG still | same decoder, one frame | same | T42 |
| JPEG still | Core scales the JPEG (TurboJPEG decode at 1/2, 1/4, 1/8) and re-encodes | file size, date | T42 |
| PNG / TIFF still | "NO PREVIEW", as a still the WebUI cannot show yet | file | later |
| MLV (single file, uncompressed) | Core reads frame N through a block index built once per clip (a named copy of `MLR:153-216` rules), renders with the touch UI's MLV "ISP" path (`CIP:655-662`) | MLVI/RAWI header | T46 |
| MLV not finalized (count 0) | not playable: "MLV is not finalized or its frame count is invalid." (touch UI wording, `MLR:176-177`) | | T46 |
| ProRes `.mov` | Core asks the touch UI's video plugin for BGRA frames, encodes JPEG | plugin `probe` | T47 |
| H.264 `.mp4` | same as ProRes (default). Option O12: the browser's own `<video>` with Range | plugin `probe` | T47 |
| `.mp4.writing`, ProRes without `moov` | not playable, with the reason | | T47 |

Why the plugin for H.264 too, and not `<video>`: one viewer path, exact frame numbers and the FRAME i / N badge, the same
histogram as the touch UI, and the same hold rule. `<video>` would decode on the phone for free and is listed as O12.

### 2.5 Sound

- The browser plays `<clip>.wav` through an `<audio>` element. Core serves it on `/api/media/file` with **HTTP Range** (206,
  `Content-Range`, `Content-Length`). Range is needed to seek, and Safari plays media only from servers that answer Range
  (PROBABLE, general web knowledge).
- The audio element's `currentTime` is the clock: frame = `floor(currentTime × fps)`. The touch UI does the same with its audio
  clock (`PC:769-772`). Without a WAV, a wall clock runs.
- A paused `<audio>` stops reading. Core's 5 s send timeout then drops the connection (F6), and the browser resumes with a
  new Range request (PROBABLE). That is why Range comes before sound.
- Browser support for your WAV (s24 stereo 48 kHz, with `bext` and `iXML` chunks; `kb:lessons/hardware-log.md:456`) is
  UNCONFIRMED: T40 M6. If a browser refuses it, the viewer plays silently with a one-line notice (O13 would transcode in Core).
- MLV-embedded audio does not exist in Core's files (`kAudioClassNone`, r3 §1.3). Nothing to do.

### 2.6 Interlocks: recording, standby, pulled media

One Core function, `playbackHoldReason()`, answers for every playback route and for `/api/state`:

| Order | Condition (all exist, F11) | `playback_hold` | Why |
| --- | --- | --- | --- |
| 1 | `camera_.isRecording() \|\| soundRecordingActive() \|\| camera_.timelapseActive()` | `recording` | reading the card during a take competes for the same memory and drive (F18, F19) |
| 2 | `camera_.mediaWritesPending()` | `writing` | the last take is still draining; Cinemate also holds on buffer flush and pre-roll (r1 §2.6) |
| 3 | `camera_.state() == CameraState::Standby` | `standby` | the touch UI stops playback on standby (r2 §1.1); the governor is on powersave then (r3 §4.4) |
| 4 | `!mediaSnapshot().mounted()` (not the mount table) | `media` | a pulled NVMe can block reads for 30-60 s (r3 §4.5) |
| — | otherwise | `""` | |

Rules:

- The check runs **in each request**, not when the page opens (Cinemate lesson C10: a guard that reads the present cannot defend
  against a job that starts later; r4 §5.2).
- Recording is never refused because someone is watching. Playback yields.
- The list (`/api/media`) is not refused in a take: it answers from its cache with `"held":"recording"` and reads nothing on
  the card (Cinemate's index was never gated, r1 §5.5).
- Delete gains the `writing` check (F12), with Core's existing wording "Wait for the current capture to finish writing to media."
  (`App:9489`).
- The WebUI folder button is greyed in a take, like the touch UI's (`CamP:3754`). An open viewer stays open and shows the hold.
- Standby: while a clip **plays**, the page sends `user_activity` every 20 s, so watching counts as use (F13). Paused, it does not.

### 2.7 CPU and I/O budget on the Pi 5

| Situation | Playback work allowed | Cost (PROBABLE unless marked) |
| --- | --- | --- |
| A take, sound recording, timelapse, writes draining | none: frames, thumbnails and WAV answer 409; list from cache | ~0. The 1 s `/api/state` poll continues, as today |
| Standby | none (409) | 0 |
| Idle, browser open, thumbnails filling | ≤ 2 decodes at once, nice 10, in-memory LRU | one decode per card the first time: ~0.1 s uncompressed, ~0.3-0.4 s lossless; cached afterwards |
| Idle, playing 4K Clear HDR 16-bit uncompressed at 25 fps, 640 w | 2 workers | ~1.5-2.5 cores; 415 MB/s of reads (at the Gen 2 link limit, F19). Thermal load: watch `vcgencmd measure_temp` in T40 |
| Idle, playing 4K SDR 12-bit lossless | 2 workers | 2 cores busy, frames skipped (~5-8 fps shown); ~40-60 MB/s of reads (only decoded frames are read) |
| Idle, paused | one 1920 w frame per pause | ~0.3-0.6 s of one core |
| Live preview | the page stops `/preview.mjpeg` while the overlay is open (F14) | removes the MJPEG downscale from libcamera's thread |

Knobs: `APERTAR_PLAYBACK_WORKERS` (default 2, 1-3), `APERTAR_PLAYBACK_CACHE_MB` (default 32). Same pattern as
`APERTAR_CDNG_TILE_ROWS` (`Cdng:52-67`). Decode threads lower their own priority with `setpriority(PRIO_PROCESS, gettid(), 10)`
for the decode and restore it after, so camera threads win. Memory: ~33 MB of scratch per worker (samples + payload) plus the
32 MB cache, ~100 MB at most (PROBABLE; 4 GB Pi).

### 2.8 Where the WebUI deliberately differs from the touch UI

| # | Touch UI | WebUI | Why | Ask |
| --- | --- | --- | --- | --- |
| D1 | "CAPTURE Clip Mode / Still Mode" switches the **camera's** photo mode (`CBP:115-119`, r2) | Same button place and look, labelled "SHOW Clips"; it opens Clips, Stills, Timelapse, Audio and filters the list only | A list filter should not change the camera from a phone; the WebUI already has four categories | Q2 |
| D2 | "1 ITEMS" | "1 item" | wording bug (r2 §10 #4) | Q7 |
| D3 | no download | Download (single, selected) kept from today's WebUI browser | existing WebUI feature (P7 in r4) | Q3 |
| D4 | long press only | long press, plus a click on the card's selection badge with a mouse | a mouse has no comfortable long press | — |
| D5 | live refresh by a file watcher | refresh when the browser opens, on Refresh, after a delete, when a take ends | no event channel to the browser (r4 §3.3) | — |
| D6 | no hold in a take | hold with a named reason (§2.6) | Cinemate's mechanic; you asked for its mechanics | Q4 |
| D7 | sound out of the Pi | sound out of the phone or laptop | the viewer is remote | — |
| D8 | without a WAV, a slow decode stretches time (`PC:774`, timer-driven `nextFrame()`) | a wall clock runs and late frames are skipped | over Wi-Fi a stretched clock would make the length meaningless | Q8 |
| D9 | BIT DEPTH "16-bit" for any DNG with a LinearizationTable (r2 §10 #5) | the stored depth from tag 258, e.g. "12-bit", plus "companded" when a table exists | the file is the witness | Q6 |
| D10 | Back rebuilds the browser: rescan, scroll to top | Back returns to the same grid and scroll | the page keeps the grid in memory | — |
| D11 | 4K histogram samples one CFA site (F17) | copied as is, so both screens draw the same bars | parity first; fix both later (U6) | Q7 |

### 2.9 What each measurement would change (T40)

| Result | Then |
| --- | --- |
| M1: uncompressed 16-bit 640 w frame ≤ 80 ms per worker on the Pi | defaults stand: 2 workers, play 640 w |
| M1: > 80 ms | play at 480 w (the touch UI's square layout plays ~459 px wide, r2 §3.1 ×75 %); try 3 workers |
| M1: cold read dominates (`--cold` read > render) | read only the rows the render needs (~2/3 of the strip at 640 w) |
| M1: lossless ≤ 4 fps with 2 workers, and M2 shows the touch screen as choppy | offer O11 (preview track) now; else keep it as an option |
| M3: < 40 small requests/s through Core's server | look-ahead window 1 instead of 2, and keep-alive becomes a task |
| M6: a browser cannot play the s24 WAV | O13: Core streams a 16-bit copy |
| M5: standby comes during passive playback on the touch UI too | U2: the touch UI sends `user_activity` while playing |
| M7: reading an old take during a take costs no frames | thumbnails could be allowed in a take (Q4); default stays "hold" |

---

## 3. The WebUI pane

### 3.1 Map: the browser

| Touch UI element (`CBP`, r2 §2) | WebUI counterpart | Component |
| --- | --- | --- |
| Black full-screen page, Inter | full-screen overlay `#playbackOverlay` (replaces `#mediaBrowserOverlay`), page background, Inter; content max 1320 px wide, centred | `--bg-bottom`, `--content-width` |
| "PLAYBACK" eyebrow + "Clip Browser" / "Still Browser" | same strings | `.pb-eyebrow`, `h2.section-title` |
| Refresh Media (refresh icon) / "Scanning..." | same; "Scanning..." now paints, the fetch is async | `.secondary-button` + `/icons/refresh.png`; icon only below 420 px |
| CAPTURE Clip Mode / Still Mode | SHOW Clips (D1): two lines, opens Clips / Stills / Timelapse / Audio | `.secondary-button.pb-two-line`, accent `#3fd0ff` like the touch UI's still state |
| Back / Cancel (in selection) | same | `.icon-button.settings-back-button` |
| Sheet `#151515`, radius 28, runs off the bottom | same | `.pb-sheet`, `--radius-xl` |
| Film icon + "CLIPS" / "STILLS" / "SELECTION" | same | `/icons/film.png`, `.pb-sheet-label` |
| Count chip "N ITEMS" / "N SELECTED" | "12 items", "1 item", "3 selected" (D2) | `.media-stat` pill |
| Sort chip "NEWEST FIRST" / "OLDEST FIRST" (accent) | same, toggles | `.pb-chip.accent` |
| Remove Selected (red, selection mode) | same, plus Download Selected (D3) | `.danger-button`, `.secondary-button` |
| Status line ("Found 12 clip(s) in /media/RAW.", "No cDNG, ProRes, H.264 or MLV clips found in /media/RAW.", "/media/RAW is not available.", selection hint) | same strings, root from the reply's `media_root` | `.settings-card-copy` |
| Grid 2 / 3 / 4 columns | `< 720 px` 2, `720-1099` 3, `≥ 1100` 4 | CSS grid |
| Card r24 `#181818`: 16:9 thumbnail r18, duration pill bottom-left, selection badge top-left; name (bold), format label, shot date | same | `.pb-card`, `<img loading=lazy>`, `.badge` |
| "NO PREVIEW" while not ready | same; also for a held or unplayable clip | `.pb-thumb-empty` |
| Last-opened card lighter | same | `.pb-card.last` |
| Selected card `#241c1f`, red border | same | `.pb-card.selected` |
| Tap opens; long press (Qt default 800 ms) selects | same (800 ms, pointer events); D4 | |
| "Remove Selected Clips?" dialog, scrim 80 %, card r26, "Remove Clips" | same strings | `.pb-dialog`, `.danger-button` |

### 3.2 Map: the viewer

| Touch UI element (`CPP`, r2 §3) | WebUI counterpart | Component |
| --- | --- | --- |
| "PLAYBACK" + "Clip Viewer", Back (stops, returns) | same | as the browser |
| Preview r24 16:9, letterboxed on black, previous frame kept while the next loads | `<canvas>` in a 16:9 box; a frame is drawn only when decoded (`createImageBitmap`), so there is no flash | `.pb-stage` |
| Badges: "25.000 FPS" top-right, "PLAYING"/"PAUSED" bottom-left, "FRAME i / N" bottom-right | same text, same corners | `.badge` (WebUI preview badge style) |
| Title row (stacked): name, "cDNG sequence • 250 frames", Info button | same; the info line is Core's `info_line` | `/icons/info.png` |
| Scrub bar: rail, fill, handle; press or drag seeks | same look; pointer capture; one request in flight, newest wins (Cinemate's coalescing scrub) | `.pb-scrub` |
| Remove (red) | same | `.danger-button` + `/icons/delete.png` |
| Previous clip / Play-Pause / Next clip circles | same; clip skips, not frame steps (frame steps are O1) | round `.icon-button`s with `previous`/`play`/`pause`/`next` PNGs (F20) |
| HISTOGRAM card, 48 bars, white gradient | same drawing; bins from Core's `X-Histogram` header, so they equal the touch UI's | `<canvas>` in `.pb-hist` |
| Clip Metadata: CAPTURED, TYPE, RESOLUTION, BIT DEPTH, FRAME RATE, DURATION, FRAMES, CLIP SIZE, PATH; "Unavailable" | same labels; values formatted by Core (`meta` object) | split: side `.settings-card`; stacked/compact: overlay with Close |
| "Remove Clip?" dialog | same strings; then the clip at the same index, or the browser if none | `.pb-dialog` |
| Clip change: slide from ±44 px, fade 260 ms, scale 320 ms | same timings in CSS | |
| Status text only when a clip has no frames | same, with Core's `play_reason` | |

### 3.3 Layouts

Browser width and height choose the touch UI's layout family (`CPP:28`, `:306-345`, r2 §3.1, not reopened):

| Browser | Touch UI family | Viewer shape |
| --- | --- | --- |
| width ≥ 1024 and wider than 4:3 (laptop, tablet landscape) | split (`landscape*`) | preview left (height ≤ sheet − 132), scrub under it, control row; Clip Metadata panel right, 27 % of the sheet |
| height < 500 in landscape (phone on its side) | compact (`landscape_compact`) | preview, full-width scrub, row: Remove, transport, Info icon, histogram |
| otherwise (phone portrait) | stacked (`square`) | preview, title row with Info, scrub, row: Remove, transport, histogram; metadata in the overlay |

Phone portrait, browser and viewer (text sketch):

```
PLAYBACK                       [↻] [SHOW ] [← Back]
Clip Browser                        Clips
┌─────────────────────────────────────────────┐
│ ▣ CLIPS              [NEWEST FIRST] 12 items│
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
│ [🗑 Remove]   (⏮) ( ▶ ) (⏭)   [HISTOGRAM ▁▃▆▇▅▂] │
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
│        [🗑 Remove]   (⏮) ( ⏸ ) (⏭)   [HISTOGRAM ▁▃▆▇▅▂]  │ PATH [/media/RAW/..] │
└───────────────────────────────────────────────────────────┴──────────────────────┘
```

Phone traps from the handbook apply: use `100dvh` with a fallback, cap the preview with a definite `max-height`, test on a
real phone; no fullscreen button (iOS has none for `<canvas>`; the touch UI has none either) (r4 §6).

### 3.4 Behaviour

| Topic | Rule |
| --- | --- |
| Open | Folder button (greyed in a take) → stop `#previewStream` (remove `src`; the error handler must not reconnect, `Web:8613-8616`) → `GET /api/media` → render cards → thumbnails for visible cards, 2 in flight (`IntersectionObserver`) |
| Close | Back from the browser or Escape → `loadPreviewStream()` (`Web:8597`) restarts the live view with a new nonce |
| Open a clip | `GET /api/media/clip` → paused on frame 1 → `w=1920` frame (sharper paused frame, like the touch UI's full-size paused decode, r2 §3.4) |
| Play | audio clock if a WAV exists, else wall clock. Each tick: `want` = clock frame. Keep `want … want+1` requested at `w=640` (look-ahead = workers). Draw the newest decoded frame ≤ `want`; drop older ones |
| 503 busy | skip that frame, never pause (Cinemate paused, r1 §5.5) |
| 409 hold | pause, stop audio, show the hold card (§4.8) |
| End | loop to frame 1 and keep playing, like the touch UI (`PC:567`). Play-once is O2 |
| Pause | stop the clock, ask `w=1920` for the current frame after 150 ms |
| Scrub | pointerdown pauses; each move asks `w=640` with one request in flight and the newest position wins; pointerup asks `w=1920` |
| Prev/next clip | index ± 1 in the browser's current sort and filter (`Main:426-443`, r2) |
| Remove | dialog → `POST /api/media/delete` → open the clip at the same index, or return to the browser |
| Hidden tab | pause ("Paused: tab in the background" toast), as Cinemate (r1 §1.5) |
| Hold from the poll | `renderSnapshot` (`Web:9366`) reads `playback_hold` once a second: pause and show the card; when it clears, redraw the current frame, do not resume; refetch the list if a take ended |
| Keep awake | while playing, `user_activity` every 20 s |

### 3.5 Walkthroughs (operator and code)

**A. The last take, with sound, on the laptop.**

| You do | You see | Core does |
| --- | --- | --- |
| Folder button | Clip Browser, newest first, the last take top-left with "00:10", "cDNG clip", "28 Oct 2026  14:03" | `/api/media` from its folder cache; thumbnails: `frame=0&w=320`, decode, LRU, `immutable` |
| Click the card | Clip Viewer, paused, "25.000 FPS", "PAUSED", "FRAME 1 / 250"; metadata panel right | `/api/media/clip`; `frame=0&w=1920` |
| Play | picture at ~25 fps (PROBABLE, M1), sound from the laptop, "PLAYING" | `<audio>` Range requests; frames `w=640`, 2 workers |
| Wait to the end | loops to frame 1 | browser cache serves the second loop (immutable URLs) |
| Back, Back | browser, then the camera page with live view | `/preview.mjpeg?stream=n+1` |

**B. Someone presses record while you watch.** Within ~1 s (poll) or at the next frame (409): the picture pauses, sound stops,
the card says "Recording" (§4.8). The grid stops loading thumbnails. Take ends, writes drain: the card goes, the frame redraws,
the list refetches and the new take appears first. Playback does not restart by itself. Core: every request runs
`playbackHoldReason()`; `/api/state` shows `"playback_hold":"recording"`, then `"writing"`, then `""`.

**C. Remove from the viewer.** Remove → "Remove Clip?" → "Remove Clip" → the next clip at the same index opens. In a take or
while writes drain, Core refuses with its existing words and the dialog shows them.

**D. A 4K SDR 12-bit lossless take shot at 50 fps.** The FRAME counter jumps in steps of ~4-8 (PROBABLE), the sound stays in time.
With O4 the rate row says what happened ("Achieved 7.8 fps · skipped 312"). The second loop is smoother if the browser kept
the frames. The touch screen is probably the same today (M2).

**E. The card is pulled.** Within ~2 s: the card says "Media was removed. Insert or mount media to play clips."; the browser
shows "/media/RAW is not available." (touch UI wording). Core's watcher snapshot says not mounted; routes answer 409 `media`.

---

## 4. Core API, data and state

### 4.1 Routes

| Method and path | Answer | Refused | New / changed |
| --- | --- | --- | --- |
| `GET /api/media` | today's list, each clip with the facts of §4.2; top level `held` | never; in a hold it answers from cache | changed (T41) |
| `GET /api/media/clip?kind=folder\|still&id=…` | §4.3 | 404 unknown id | new (T41) |
| `POST /api/command {"cmd":"get_clip_info","kind":…,"clip_id":…}` (also on the socket) | same JSON as `/api/media/clip` | as above | new (T41); in `help`. `clip_id`, because the protocol reads `id` as the command's number (`src/ipc/ControlProtocol.cpp:228`, CONFIRMED) |
| `GET /api/media/frame?kind=…&id=…&frame=N&w=320\|480\|640\|960\|1920&v=TOKEN` | `image/jpeg`; headers §4.4 | 409 hold, 503 busy, 404, 400 | new (T42) |
| `GET /api/media/file?kind=folder&id=…&name=X.wav` | `audio/wav`, Range → 206 | 409 hold, 404, 416, 400 (not a `.wav`) | new (T45) |
| `POST /api/media/delete`, `/api/media/delete-selected` | today's | + `writing` (F12) | changed (T44) |
| `GET /api/state` | + `"playback_hold":"…"` | | changed (T41) |

Apertar style: the `/api/media/*` family, `kind` + `id` like the download route (`App:7343-7360`), flat JSON for lists, one
command for the socket. All ids go through `isSafeMediaRelativeId` / `resolveMediaLibraryPath` (`App:5640`, `App:5790`).

### 4.2 `/api/media` item: new and fixed fields

```json
{"id":"cDNG_26-10-28_C0007","kind":"folder","category":"clip","type":"cDNG Clip","name":"cDNG_26-10-28_C0007",
 "size_bytes":4150000000,"size_text":"3.9 GB","file_count":251,"frame_count":250,
 "duration_text":"00:10","fps_text":"25 FPS",
 "modified_text":"…","modified_ms":1761660180000,"download_url":"/api/media/download?kind=folder&id=cDNG_26-10-28_C0007",
 "format":"cdng","format_label":"cDNG clip","playable":true,"play_reason":"",
 "fps":25.0,"shot_date_text":"28 Oct 2026  14:03","empty_frames":0,"dropped_frames":0,"has_audio":true,
 "token":"9f3c2a17","thumb_url":"/api/media/frame?kind=folder&id=cDNG_26-10-28_C0007&frame=0&w=320&v=9f3c2a17"}
```

- `fps_text` and `duration_text` now come from the clip's own first frame (fix of §1.1). Old fields keep their names.
- `frame_count` = non-empty frames. `empty_frames` = 0-byte DNGs (a pulled take leaves ~21-23, `kb:lessons/hardware-log.md:440-460`).
- `dropped_frames` = (last index − first index + 1) − files (F4; Cinemate's rule, r1 §2.2). With T31 ramp takes it reads 0 (R10).
- `token` = FNV-1a of (folder name, first frame mtime ns, first frame size, file count). It changes when a folder name is reused
  after a delete, so a cached frame can never show the wrong take (Cinemate's render-token lesson, r1 §4.2 #7).
- Facts are cached per folder, keyed by (folder mtime, entry count). Unchanged folders cost a `readdir`, not a stat per file.
- In a hold the reply is the last cache plus `"held":"recording"` (or `writing`, `standby`, `media`).

### 4.3 `/api/media/clip` and `get_clip_info`

```json
{"ok":true,"kind":"folder","clip_id":"cDNG_26-10-28_C0007","name":"cDNG_26-10-28_C0007",
 "format":"cdng","playable":true,"play_reason":"","frame_count":250,"empty_frames":0,"dropped_frames":0,
 "fps":25.0,"token":"9f3c2a17","width":3840,"height":2160,"bits":16,"compression":"uncompressed","companded":false,
 "timecode_start":"14:03:12:05","has_audio":true,"audio_text":"24-bit 48 kHz stereo",
 "audio_url":"/api/media/file?kind=folder&id=cDNG_26-10-28_C0007&name=cDNG_26-10-28_C0007.wav",
 "fps_badge":"25.000 FPS","info_line":"cDNG sequence • 250 frames",
 "meta":{"captured":"28 Oct 2026  14:03","type":"cDNG sequence","resolution":"3840 x 2160","bit_depth":"16-bit",
         "frame_rate":"25.000 fps","duration":"00:10","frames":"250","clip_size":"3.9 GB",
         "path":"/media/RAW/cDNG_26-10-28_C0007"}}
```

The folder is `clip_id`, not `id`: on the socket `okReply` already writes the command's `"id":<n>` (`App:110-120`, CONFIRMED),
and one body serves both doors. The `meta` values use the touch UI's formats (`PC:1149-1205`): date "dd MMM yyyy  HH:mm" (two spaces), "%1 x %2", "%.3f fps",
mm:ss / h:mm:ss, base-1024 sizes, "Unavailable" when missing. Core formats them so both screens show one answer (the precedent
of `87011d4` and `6ae70b5`, r4 P4). WAV search order as the touch UI: `<clip>.wav`, `audio.wav`, then any `*.wav` (r2 §4.2).

### 4.4 `/api/media/frame`

- `frame` = 0-based position in the sorted list of non-empty frames (not the number in the name; gaps are skipped, r1 §2.2).
- `w` from a whitelist, so the cache stays small: 320 and 480 (cards), 640 and 960 (playing), 1920 (paused; a 4K quad image).
- JPEG quality 80 (75 for 320/480). RGB → TurboJPEG `tjCompress2` with FASTDCT, libjpeg fallback, as `App:4165-4230`.
- Headers on 200:

| Header | Value |
| --- | --- |
| `Cache-Control` | `private, max-age=31536000, immutable` when `v` equals the token; else `no-store` |
| `X-Frame-Index`, `X-Frame-Count` | position, count |
| `X-Histogram` | 48 integers 0-255, the touch UI's recipe (F16) |
| `X-Frame-Source` | `cache` or `decode` |
| `X-Decode-Ms` | the decode time, so logs and the page carry values (Cinemate lesson C7, r4 §5.2) |

- Errors are JSON `{"ok":false,"error":"…","hold":"recording"}` with 409, `{"ok":false,"busy":true}` with 503.

### 4.5 `/api/media/file` (T45)

- Only `name` ending in `.wav` (case-insensitive), no `/`, `\`, `..`, resolved inside the clip folder, regular file, no symlink
  (Cinemate's symlink lesson, r1 §2.7).
- `Range: bytes=a-b` or `a-` → 206 with `Content-Range` and `Content-Length`; no Range → 200 with `Content-Length` and
  `Accept-Ranges: bytes`; unsatisfiable → 416. Body read with `pread`, 64 KiB chunks (`App:6333-6348` pattern).
- `Content-Length` is always sent, so a cut stream is visible (r3 §3.3).

### 4.6 State

| Field | Where | Meaning |
| --- | --- | --- |
| `playback_hold` | `buildWebStateJson` only (`App:7860-8075`): the WebUI polls it; socket clients ask `get_clip_info` or watch `recording` events | §2.6 |

Not persisted, no settings file, no new settings event. Sort, filter and the last-opened clip live in the page (`localStorage`
is not used; the touch UI does not persist them either, r2 §2.4).

### 4.7 Caches, slots, priorities

| Cache | Key | Size | Lives |
| --- | --- | --- | --- |
| Folder facts | folder name → (mtime, entry count) | one entry per take | Core process |
| Frame list per clip | folder → sorted names and sizes | one per opened clip, last 8 | Core process |
| JPEG LRU | (id, frame, w, token) | 32 MB | Core process |
| Browser HTTP cache | the frame URL (`immutable`) | the browser's | the browser |

Slots: a counting semaphore of `APERTAR_PLAYBACK_WORKERS` (default 2), taken without waiting; full → 503 (Cinemate's
"refuse rather than queue", r1 §2.5). Decoding runs on the HTTP client thread that holds the slot, at nice 10.

### 4.8 Refusals and messages

| When | Kind | Text |
| --- | --- | --- |
| hold `recording` | 409 + viewer card | title "Recording", body "The card is busy with a take. Playback resumes when recording stops." |
| hold `writing` | 409 + card | "Writing to media", "Finishing the last take. One moment." |
| hold `standby` | 409 + card with a **Wake** button (`wake`) | "Standby", "Wake the camera to play clips." |
| hold `media` | 409 + card | "Media not available", "Media was removed. Insert or mount media to play clips." (after `App:9426`) |
| decoder busy | 503 | none shown; the frame is skipped (counted for O4) |
| no frames | `play_reason` | "No DNG frames found in cDNG_….", the touch UI's wording (`PC`, r2 Appendix B) |
| all frames empty | `play_reason` | "Every frame of this take is empty (0 bytes); the card was probably pulled." |
| MLV not finalized | `play_reason` | "MLV is not finalized or its frame count is invalid." (`MLR:177`) |
| H.264 in progress | `play_reason` | "H.264 take is still being written." |
| ProRes without index | `play_reason` | "ProRes take was interrupted; it has no index." |
| format not built yet | `play_reason` | "MLV playback arrives with T46." / "ProRes and H.264 playback arrive with T47." |
| plugin missing | `play_reason` | "Video playback decoder unavailable." (touch UI, `VideoPlayback.cpp:35`) |
| decode error | frame drawn as the touch UI's placeholder | "Decode failed: <reader error>" |
| delete in a take | existing | "Stop recording before deleting media." (`App:7664`) |
| delete while writing | new | "Wait for the current capture to finish writing to media." (`App:9489` words) |
| WAV refused by the browser | toast | "This browser cannot play the take's WAV. Playing without sound." |

### 4.9 Safety

- Ids: existing validators (`App:5640`, `App:5690`, `App:5790`). Frame files are never named by the client: `frame=N` indexes
  Core's own sorted list. Names go into the page with `textContent` (Cinemate's stored-XSS lesson, r1 §2.7).
- A reader bug must not take Core down. The reader checks every offset against the file size before allocating (sketch); the
  web server already catches exceptions per client thread (`WS:277-283`); the T42 gate re-runs the fuzz of §2.2.
- No auth, as today: keep port 8000 on a trusted network (r4 K21).

---

## 5. Implementation plan, file by file

Order = build order. Lines are at `eb9cc39`; **use the search string**, lines move. Risk: **low** = host-checkable (header
with its test, `ApertarCoreApp.cpp` with `g++ -fsyntax-only`, the page with `node --check` and a mocked Chromium);
**medium** = touches every web response or the existing browser; there is no high-risk row: **no change in
`CameraController.cpp`**.

### T41: Core knows its clips

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 41.1 | new `src/playback/DngFrameReader.hpp` | | part 1: `DngInfo`, tail read, IFD parse, `readDngInfo` with the bounds checks (sketch lines 1-298) | low (host test) |
| 41.2 | new `src/playback/ClipProbe.hpp` | | `ClipFacts`; `listFrames(dir)` (names, sizes, first/last index, empty, dropped); `readWavFormat(path)`; `readMlvHeader(path)` (52 bytes); `clipToken`; formatters: shot date, duration, size base 1024, fps, type labels, `info_line`, `meta` | low |
| 41.3 | KB `working/tools/playback/clip_probe_test.cpp` | | writes 3 frames with Core's encoder plus a gap and a 0-byte file; checks every fact and string | low |
| 41.4 | `App.hpp:104` | `MediaSnapshot mediaSnapshot() const;` | `std::string playbackHoldReason() const;` + `mutable std::mutex mediaFactsMutex_; mutable std::map<std::string, CachedClipFacts> mediaFacts_;` | low |
| 41.5 | after `App:9413` block | `std::string ApertarCoreApp::mediaGateError() const` | `playbackHoldReason()` (§2.6) | low |
| 41.6 | `App:5609` | `struct MediaLibraryItem` | add the §4.2 fields | low |
| 41.7 | `App:6422-6497` | `std::vector<MediaLibraryItem> discoverMediaLibraryItems(` and `: durationTextForFrameCount(stats.frameCount, fps);` | facts from `ClipProbe` through the cache; `fps_text`, `duration_text` from the clip | low |
| 41.8 | `App:7819` | `std::string ApertarCoreApp::buildMediaLibraryJson() const` | write the new fields; `held` | low |
| 41.9 | after `App:7307` | `if (request.method == "GET" && request.path == "/api/media") {` | route `/api/media/clip` → `buildClipInfoJson(kind, id)` | low |
| 41.10 | after `App:9612`; `App:9633` | `if (command.name == "list_sensor_modes") {`; `if (command.name == "help")` | `get_clip_info`; add it to the help list | low |
| 41.11 | `App:8071` | `<< ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")` | `<< ",\"playback_hold\":\"" << playbackHoldReason() << "\""` | low |

### T42: Core draws a frame

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 42.1 | new `third_party/liblj92/` | | `cp ~/ApertarUI/third_party/liblj92/{lj92.c,lj92.h,LICENSE,README.apertar.md}`; check with `cmp` | low |
| 42.2 | `CMake:6`, `CMake:76` | `    LANGUAGES CXX`; `    src/cdng/LosslessJpegEncoder.cpp` | `LANGUAGES C CXX`; add `src/playback/PlaybackFrames.cpp`, `third_party/liblj92/lj92.c`; include dir `third_party/liblj92`; re-run cmake (r4 K6) | low |
| 42.3 | `DngFrameReader.hpp` | | part 2: `readDngSamples` (16-bit LE, 12/10 packed, LJ92 tiles, LinearizationTable) | low (host test) |
| 42.4 | new `src/playback/RawRender.hpp` | | the touch UI's look and histogram (sketch, 226 lines) | low (parity test) |
| 42.5 | new `src/playback/PlaybackFrames.hpp/.cpp` | | slots, LRU, `frameJpeg(dir, frame, w, token, out, headers)`, RGB → JPEG, nice 10, frame lists | low (host-compilable) |
| 42.6 | `WS:70` | `case 503: return "Service Unavailable";` | add 206 "Partial Content", 409 "Conflict", 416 "Range Not Satisfiable" | medium |
| 42.7 | `WS:127`, `WS:142` | `std::string buildHttpResponse(const WebServer::Response &response)`; `std::string buildStreamingHttpHeader(const WebServer::Response &response)` | write `Cache-Control: no-store` only when the handler did not set `Cache-Control` | medium (every response) |
| 42.8 | after the T41 route | `request.path == "/api/media/clip"` | route `/api/media/frame` with hold, slots, headers (§4.4) | low |

### T43: WebUI Clip Browser

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 43.1 | `Web:1137` (the overlay CSS block `Web:1122-1432`) | `.media-browser-overlay.hidden {` | `.pb-*` rules: page, title, top buttons, sheet, chips, status, grid, card, thumb, duration pill, select badge, dialog; breakpoints 720/1100/420 | low |
| 43.2 | `Web:3979-4030` | `<div class="media-browser-overlay hidden" id="mediaBrowserOverlay">` | replace with `#playbackOverlay`: title block, Refresh/Show/Back, sheet head, chips, status, grid, Remove dialog, (T44) viewer container | medium (the old browser goes) |
| 43.3 | `Web:4246` | `mediaSelection: new Set(),` | `pb: {page, filter, sort, selecting, lastOpenedId, thumbQueue, …}` | low |
| 43.4 | `Web:6176` | `function setMediaBrowserOpen(open) {` | stop the live view with `removeAttribute("src")` and a `previewPausedForPlayback` flag that the `<img>` error handler respects (it retries after 1.5 s, `Web:8613-8616`, CONFIRMED); restart with `loadPreviewStream` (`Web:8597`) on close; open on the browser page | low |
| 43.5 | `Web:7707` | `function renderMediaLibrary(payload) {` | build cards instead of rows; `buildClipCard`, `formatPlaybackStatus`, count "1 item" | medium |
| 43.6 | near `Web:10403` | `async function fetchMediaLibrary(silent) {` | thumbnail queue (2 in flight, `IntersectionObserver`), long press 800 ms, badge click, Remove Selected dialog → existing `deleteSelectedMediaItems`; Download Selected kept | low |
| 43.7 | `Web:2447` | `<button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">` | disabled while `snapshot.recording` (in `renderSnapshot`, `Web:9366`) | low |

### T44: WebUI Clip Viewer

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 44.1 | the T43 CSS block | `.pb-card {` | viewer rules: stage, badges, title row, scrub, transport, histogram card, metadata panel and overlay, hold card; split/compact/stacked queries | low |
| 44.2 | inside `#playbackOverlay` | `id="pbViewer"` | viewer markup (§3.2) | low |
| 44.3 | after the T43 JS | `function buildClipCard(` | `openClip`, `fetchClipInfo`, `requestFrame` (fetch → `createImageBitmap`, headers), `drawFrame`, `drawHistogram`, clock and look-ahead, `playClip`, `pauseClip`, `installScrub`, `stepClip`, `showClipMetadata`, `removeCurrentClip` | low |
| 44.4 | `Web:9366` | `function renderSnapshot(snapshot) {` | `applyPlaybackHold(snapshot)`; refetch the list when `recording` goes false | low |
| 44.5 | `Web:11558` | `document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});` | 20 s `user_activity` while playing; `visibilitychange` pause | low |
| 44.6 | `Web:11620` | `if (event.key === "Escape" && state.mediaBrowserOpen)` | Escape closes the metadata overlay, then the viewer, then the browser | low |
| 44.7 | `App:7649`, `App:7721` | `if (request.method == "POST" && request.path == "/api/media/delete") {` and `…/delete-selected") {` | add `camera_.mediaWritesPending()` to the gate (F12) | low |

### T45: Sound

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 45.1 | after `App:6333` | `void streamFileToClient(int clientFd, const std::filesystem::path &path)` | `streamFileRangeToClient(fd, path, first, last)` with `pread` | low |
| 45.2 | after the frame route | `request.path == "/api/media/frame"` | `/api/media/file`: name rules, hold, Range parse, 200/206/416 | low |
| 45.3 | viewer JS | `function playClip(` | `<audio preload="none">`, audio clock, seek on scrub, error → silent notice | low |

### T46: MLV, T47: ProRes and H.264

| # | File | Change | Risk |
| --- | --- | --- | --- |
| 46.1 | new `src/playback/MlvFrameReader.hpp` | named copy of `MLR:153-278` rules: header, block walk to the first `VIDF`, frame index (one pass over block headers, cached), 12-bit unpack, WBAL/DEBG-APCM/EXPO | low (host test with Core's `MlvEncoder`) |
| 46.2 | `RawRender.hpp` | the ISP path (`CIP:655-662`, CONFIRMED): clip × common gain, CCM, sRGB OETF | low (parity test) |
| 46.3 | `ClipProbe.hpp`, `PlaybackFrames.cpp` | MLV facts and frames | low |
| 47.1 | new `src/playback/VideoFrames.hpp/.cpp` | `dlopen` of `apertar-video-libav.so` (`APERTAR_VIDEO_PLAYBACK_PLUGIN`, then the UI's install folder), ABI v2 check, one open decoder per clip, BGRA → JPEG | low |
| 47.2 | `ClipProbe.hpp` | facts from the plugin's `probe`; `.mp4.writing`; ProRes without `moov` | low |

### Size (PROBABLE, counted as T34 counted)

| Part | Lines | Checked before the Pi |
| --- | --- | --- |
| T41 | ~500 (reader part 1, ~300 lines, is in the sketch) | host test, `g++ -fsyntax-only` |
| T42 | ~730 (reader part 2, ~75 lines, and `RawRender.hpp`, 226, are in the sketch) | round trip, parity, fuzz, syntax |
| T43 | ~420 | `node --check`, mocked Chromium |
| T44 | ~700 | same |
| T45 | ~200 | syntax, `curl` with Range on the Pi |
| T46 | ~300 | host test with `MlvEncoder` |
| T47 | ~210 | syntax; the Pi |
| **Total** | **~3,100** | none waits for the Pi to compile except the CMake run |

---

## 6. Tutorial outlines (KB format)

Each note: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T4x <topic>.md`, frontmatter as `kb:tutorials/README.md`
(`datum`, `kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext`, `typ: digital anteckning`), sections 0-9, numbered steps,
one **Check** per step, a `%% tutor` block, tags `#CINEMATE` `#APERTAR`. Reading assignments name lines at `eb9cc39` /
`d8098d0`; run `tutorial.py refs T4x` on the Pi before starting (lines move).

### T40. Measure first: what a playback frame costs on this Pi

- **You will learn**: what a 4K frame costs to read, decode and draw; how Core's server behaves with many small requests;
  what your browsers can play. **Risk**: none to the camera (read-only commands; M5 needs one setting you restore; M7 records).
  **Time**: 1.5 h.
- §1: the WebUI list shows the camera's FPS for every take (`curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`).
- §3: M1-M7 of §7, each with a prediction. §4: none. §5: fill the result table into `lessons/hardware-log.md` after you
  confirm the reading (r4 K15).

### T41. Core knows its clips: per-clip facts from the files

- **You will learn**: (1) how a DNG is laid out and why Core can read its tags with one small read; (2) why a fact about a take
  must come from the take (Cinemate's "the file is the witness"); (3) one guard function used everywhere.
  **Risk**: Core rebuild and restart. The list changes its FPS and duration text. Undo: `git revert`. **Time**: 2.5 h.
- §2 reading: `Cdng:1384-1392`, `Cdng:1522-1560`, `IFD:113-125`, `App:6422-6497`, `App:7819-7855`, `PC:1149-1205`.
- §3 find it yourself: 3.1 `tail -c 1600 <first.dng> | xxd | head` (prediction: the tag directory); 3.2 why does the list say 25
  for a 50 fps take (`App:6493`); 3.3 `ls <take> | head -3; ls <take> | tail -3` (gaps).

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | reader part 1 (41.1) | `grep -c 'inline bool readDngInfo' src/playback/DngFrameReader.hpp` → 1 |
| 4.2 | `ClipProbe.hpp` facts (41.2) | `grep -c 'inline ClipFacts probeClipFolder' src/playback/ClipProbe.hpp` → 1 |
| 4.3 | formatters (41.2) | `grep -c 'dd MMM yyyy' src/playback/ClipProbe.hpp` → 1 or more |
| 4.4 | host test (41.3), on the Pi: build and run | `./clip_probe_test` ends `all ok` |
| 4.5 | `playbackHoldReason` (41.4, 41.5) | `grep -c 'std::string ApertarCoreApp::playbackHoldReason' src/ApertarCoreApp.cpp` → 1 |
| 4.6 | item fields, scan, cache (41.6, 41.7) | `grep -c 'probeClipFolder(' src/ApertarCoreApp.cpp` → 1 or more |
| 4.7 | JSON (41.8) | `grep -c 'shot_date_text' src/ApertarCoreApp.cpp` → 1 |
| 4.8 | route and command (41.9, 41.10) | `grep -c 'command.name == "get_clip_info"' src/ApertarCoreApp.cpp` → 1 |
| 4.9 | state field (41.11); `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude src/ApertarCoreApp.cpp` | `grep -c 'playback_hold' src/ApertarCoreApp.cpp` → 1 or more |

- §5: build, restart (you), then `curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`
  (each take its own rate), `python3 -I ~/apertar-kb/working/tools/core.py get_clip_info kind=folder clip_id=<take>` (the 9 fields),
  `curl -s http://127.0.0.1:8000/api/state | grep -o '"playback_hold":"[^"]*"'` → `""`; start a take, repeat → `"recording"`.
- §7: list empty → `media_root`; a take shows "No DNG frames" → `ls -la` the folder; Core does not start → the journal.

### T42. Core draws a frame, with the touch UI's look

- **You will learn**: (1) lossless JPEG tiles and why they cost more than uncompressed; (2) how the touch UI turns raw into a
  picture, line by line; (3) how a server stays responsive by refusing work (slots, 503) instead of queueing it; (4) a parity
  test that keeps two copies honest. **Risk**: Core rebuild; the web server's header code changes for every response. Undo:
  `git revert`. **Time**: 2 sessions, 4 h.
- §2 reading: `CIP:577-698`, `DD:455-536`, `Cdng:1237-1351` (the tile writer), `WS:127-154`, the sketch's `results-host.txt`.
- §3: 3.1 `cmp ~/ApertarUI/third_party/liblj92/lj92.c ~/apertar-kb/working/tools/playback/third_party/liblj92/lj92.c`;
  3.2 run `playback_bench --cold` on one of your lossless frames (from T40) and predict the per-worker fps.

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | copy liblj92 (42.1) | `cmp third_party/liblj92/lj92.c ~/ApertarUI/third_party/liblj92/lj92.c` → no output |
| 4.2 | CMake (42.2) | `grep -c 'third_party/liblj92/lj92.c' CMakeLists.txt` → 1 |
| 4.3 | reader part 2 (42.3) | `grep -c 'inline bool readDngSamples' src/playback/DngFrameReader.hpp` → 1 |
| 4.4 | render look (42.4) | `grep -c 'inline Rgb8Image renderPreview' src/playback/RawRender.hpp` → 1 |
| 4.5 | histogram (42.4) | `grep -c 'inline std::array<float, 48> rawHistogram' src/playback/RawRender.hpp` → 1 |
| 4.6 | host round trip + fuzz (KB tools) | `./playback_bench --synthetic /tmp/pb` ends `all ok`; `./reader_fuzz …` ends `no crash` |
| 4.7 | `PlaybackFrames` (42.5) | `grep -c 'PlaybackFrames::frameJpeg' src/playback/PlaybackFrames.cpp` → 1 |
| 4.8 | reason phrases (42.6) | `grep -c 'Range Not Satisfiable' src/web/WebServer.cpp` → 1 |
| 4.9 | `Cache-Control` only once (42.7) | `grep -c 'handlerSetsCacheControl' src/web/WebServer.cpp` → 3 |
| 4.10 | route (42.8) | `grep -c 'request.path == "/api/media/frame"' src/ApertarCoreApp.cpp` → 1 |

- §5: build, restart, then
  `curl -s -o /tmp/f.jpg -D - "http://127.0.0.1:8000/api/media/frame?kind=folder&id=<take>&frame=0&w=640" | grep -E 'HTTP|X-Decode-Ms|X-Histogram'`
  (200, a decode time, 48 numbers), open `/tmp/f.jpg` beside the touch screen's frame (same look), ask three frames at once
  with `xargs -P 3` (one 503), start a take and ask again (409).
- §7 includes: "every response lost its `Cache-Control`" → 4.9; "Core crashed on a frame" → keep the file, run `reader_fuzz` on it.

### T43-T47 (outline)

| Tutorial | Steps (plan rows) | Gate |
| --- | --- | --- |
| T43 Clip Browser | 4.1 CSS (43.1), 4.2 markup (43.2), 4.3 state (43.3), 4.4 open/close + live view (43.4), 4.5 cards (43.5), 4.6 thumbnails, select, remove, download (43.6), 4.7 button in a take (43.7) | `node --check` of the page script; the mocked Chromium run (as T32/T34) with 0, 1, 12 clips, a held list, a refused delete; then the Pi on a phone and a laptop |
| T44 Clip Viewer | 4.1-4.2 CSS and markup, 4.3 frames and clock, 4.4 scrub, 4.5 transport and prev/next, 4.6 histogram, 4.7 metadata, 4.8 remove, 4.9 holds and keep-awake, 4.10 Escape, 4.11 delete gate (44.7) | as T43, plus: play a Clear HDR take, a lossless take, record during playback, pull nothing (use `eject_media` only if you choose to) |
| T45 Sound | 4.1 range streamer, 4.2 route, 4.3 audio clock | `curl -s -D - -H 'Range: bytes=0-99' …/api/media/file?…` → `206`, `Content-Range: bytes 0-99/…`; the phone plays and seeks |
| T46 MLV | 4.1 reader, 4.2 ISP render, 4.3 facts and frames | host test with Core's `MlvEncoder`; parity test against `MlvReader` |
| T47 ProRes/H.264 | 4.1 plugin loader, 4.2 facts, 4.3 frames | `find / -name apertar-video-libav.so 2>/dev/null` first (M8); then one ProRes and one H.264 take |

### Tutor blocks (anchors checked here: each string occurs once in its file at `eb9cc39` / `d8098d0`)

T41 note:

```
%% tutor
ref core src/ApertarCoreApp.cpp 6422 std::vector<MediaLibraryItem> discoverMediaLibraryItems(
ref core src/ApertarCoreApp.cpp 6492 : durationTextForFrameCount(stats.frameCount, fps);
ref core src/ApertarCoreApp.cpp 5609 struct MediaLibraryItem
ref core src/ApertarCoreApp.cpp 7819 std::string ApertarCoreApp::buildMediaLibraryJson() const
ref core src/ApertarCoreApp.cpp 7307 if (request.method == "GET" && request.path == "/api/media") {
ref core src/ApertarCoreApp.cpp 9413 std::string ApertarCoreApp::mediaGateError() const
ref core src/ApertarCoreApp.cpp 9612 if (command.name == "list_sensor_modes") {
ref core src/ApertarCoreApp.cpp 9633 if (command.name == "help")
ref core src/ApertarCoreApp.cpp 8071 << ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")
ref core src/ApertarCoreApp.hpp 104 MediaSnapshot mediaSnapshot() const;
ref ui src/playbackcontroller.cpp 1149 void PlaybackController::updateClipMetadata()
ref ui src/dngdecoder.cpp 1523 double DngDecoder::detectFrameRate(const QString &filePath)
check 4.1 | grep -c 'inline bool readDngInfo' /home/pi/ApertarCore/src/playback/DngFrameReader.hpp | ^1$
check 4.2 | grep -c 'inline ClipFacts probeClipFolder' /home/pi/ApertarCore/src/playback/ClipProbe.hpp | ^1$
check 4.5 | grep -c 'std::string ApertarCoreApp::playbackHoldReason' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.8 | grep -c 'command.name == "get_clip_info"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.9 | grep -c 'playback_hold' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[1-9]
check 5.1 | curl -s -m 5 http://127.0.0.1:8000/api/state | "playback_hold":"
%%
```

T42 note:

```
%% tutor
ref core src/web/WebServer.cpp 70 case 503: return "Service Unavailable";
ref core src/web/WebServer.cpp 127 std::string buildHttpResponse(const WebServer::Response &response)
ref core src/web/WebServer.cpp 142 std::string buildStreamingHttpHeader(const WebServer::Response &response)
ref core CMakeLists.txt 6     LANGUAGES CXX
ref core CMakeLists.txt 76     src/cdng/LosslessJpegEncoder.cpp
ref core src/ApertarCoreApp.cpp 4199 const int rc = tjCompressFromYUVPlanes(compressor.handle,
ref ui src/cdngimageprovider.cpp 578 QImage renderRawPreviewImpl(const RawFrame &frame, const QSize &requestedSize, const Sample &sample,
ref ui src/dngdecoder.cpp 534 bins.append(std::pow(normalized, 0.65));
check 4.2 | grep -c 'third_party/liblj92/lj92.c' /home/pi/ApertarCore/CMakeLists.txt | ^1$
check 4.3 | grep -c 'inline bool readDngSamples' /home/pi/ApertarCore/src/playback/DngFrameReader.hpp | ^1$
check 4.4 | grep -c 'inline Rgb8Image renderPreview' /home/pi/ApertarCore/src/playback/RawRender.hpp | ^1$
check 4.8 | grep -c 'Range Not Satisfiable' /home/pi/ApertarCore/src/web/WebServer.cpp | ^1$
check 4.10 | grep -c 'request.path == "/api/media/frame"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
%%
```

T43 and T44 notes (refs; their checks follow the step tables the same way):

```
%% tutor
ref core src/web/WebControlPage.cpp 1137 .media-browser-overlay.hidden {
ref core src/web/WebControlPage.cpp 3979 <div class="media-browser-overlay hidden" id="mediaBrowserOverlay">
ref core src/web/WebControlPage.cpp 4246 mediaSelection: new Set(),
ref core src/web/WebControlPage.cpp 6176 function setMediaBrowserOpen(open) {
ref core src/web/WebControlPage.cpp 7707 function renderMediaLibrary(payload) {
ref core src/web/WebControlPage.cpp 8597 function loadPreviewStream() {
ref core src/web/WebControlPage.cpp 9366 function renderSnapshot(snapshot) {
ref core src/web/WebControlPage.cpp 10403 async function fetchMediaLibrary(silent) {
ref core src/web/WebControlPage.cpp 10422 async function deleteMediaLibraryItem(item) {
ref core src/web/WebControlPage.cpp 11558 document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});
ref core src/web/WebControlPage.cpp 11620 if (event.key === "Escape" && state.mediaBrowserOpen)
ref core src/web/WebControlPage.cpp 2447 <button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">
ref core src/ApertarCoreApp.cpp 7649 if (request.method == "POST" && request.path == "/api/media/delete") {
ref core src/ApertarCoreApp.cpp 7721 if (request.method == "POST" && request.path == "/api/media/delete-selected") {
ref ui qml/ClipBrowserPage.qml 179 text: root.stillMode ? "Still Browser" : "Clip Browser"
ref ui qml/ClipPlayerPage.qml 234 text: "Clip Viewer"
ref ui qml/CameraPage.qml 3754 enabled: !root.recording
ref ui src/playbackcontroller.cpp 749 void PlaybackController::handlePlaybackTick()
%%
```

`tutorial.py` keeps a check only with exactly three ` | ` fields (T34 design, `TP:119-123`), so no check pipes one command into another.

---

## 7. Measurements on the Pi first (T40)

Shorthand `K=~/apertar-kb/working/tools`. All read-only except M5 (one setting, you restore it) and M7 (records). Order: M1,
M2, M3, M4, M6, then M5 and M7 if you want them. The sketch has to be in the KB first (`working/tools/playback/`); it is not
there yet: this pass wrote nothing into the KB.

**M1. What one frame costs on the Pi.** The bench needs Core's three source files and libjpeg/libyaml headers (Core already
builds with them, PROBABLE).

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

Prediction: synthetic ≈ 2× the host table (§2.2); `--cold` adds 25-40 ms of read to the uncompressed 16-bit frame. Decides
workers, play width, row-selective reads, and whether O11 is needed (§2.9).

**M2. The touch screen today, the baseline you are matching.** Open the same two takes on the touch screen. For 10 s count how
far "FRAME i / N" moves (stopwatch). Meanwhile, from SSH:

```bash
top -b -n 3 -d 2 -H -p "$(pgrep -f apertar-ui | head -1)" | head -30     # which threads, how much CPU
```

Prediction: the 16-bit uncompressed take near its rate; the lossless take well below (PROBABLE from §2.2).

**M3. How many small requests per second Core's server answers.** From the laptop on the camera's network, then on the Pi
against `127.0.0.1` (network vs server):

```bash
time (for i in $(seq 100); do curl -s -o /dev/null http://<pi>:8000/icons/play.png; done)            # one at a time
time (seq 100 | xargs -P 3 -I{} curl -s -o /dev/null http://<pi>:8000/icons/play.png)              # three at once
```

Prediction: well above 40 requests/s on the LAN (PROBABLE: one thread spawn and one TCP connect each, F6). Decides look-ahead.

**M4. What the list costs today.**

```bash
find /media/RAW -mindepth 1 -maxdepth 1 -type d | wc -l; find /media/RAW -type f | wc -l     # takes, files
for i in 1 2 3; do curl -s -o /dev/null -w '%{time_total}\n' http://127.0.0.1:8000/api/media; done
```

Decides whether the folder cache in T41 matters on your card (it scales with the file count).

**M5. Does passive playback hit standby?** (one change; you restore it)

```bash
python3 -I $K/core.py get_state | grep -o '"standby_timeout_seconds":[0-9]*'     # note it
python3 -I $K/core.py set_standby_timeout value=60                              # Patrik
# play a take on the touch screen, touch nothing for 90 s
python3 -I $K/core.py get_state | grep -oE '"(standby|state)":[^,]*'
python3 -I $K/core.py set_standby_timeout value=<noted>                         # Patrik: restore
```

Prediction: standby comes (F13). Decides U2 and confirms §2.6's keep-awake.

**M6. Do your browsers play the take's WAV?**

```bash
scp pi@<pi>:/media/RAW/<take>/<take>.wav ~/Desktop/       # on the laptop
```

Open it in Chrome, Safari and Firefox (drag into a tab), and on the phone (Files / AirDrop). Note: plays, seeks, length right.
Decides O13.

**M7 (optional; it records two takes, so you run it). Does reading an old take cost frames during a take?**

```bash
bash $K/takes.sh 1 60                                                                  # baseline: missing=0
( while true; do cat /media/RAW/<old take>/*_00000001?.dng > /dev/null; sleep 0.1; done ) &  # ~10 frames/s of reads
bash $K/takes.sh 1 60; kill %1
```

Decides Q4 (thumbnails in a take). The default holds everything, so this only matters if you want more.

**M8 (before T47).** `find / -name 'apertar-video-libav.so' 2>/dev/null` and the touch UI's launch environment
(`systemctl cat apertar-ui-direct | grep -i plugin`). Decides the plugin path Core uses.

**M9 (after T42, T44).** Frame route timing (`X-Decode-Ms` over 50 frames), `top -H -p $(pgrep apertar-core)` while the browser
plays, `cat /proc/diskstats` read MB/s, temperature. With O4 the page shows Achieved and Skipped; without it, count requests in
the browser's network panel.

---

## 8. Options for Patrik

### 8.1 Cinemate's features (not defaults)

| # | Option | Cinemate source | Cost (PROBABLE) | My suggestion |
| --- | --- | --- | --- | --- |
| O1 | Frame step ◀ ▶ and first / last frame, arrow keys and space on a laptop | `cm:…/settings_editor.html:2618-2627`, `6716-6720` (r1) | ~60 lines WebUI | yes |
| O2 | Loop toggle (off = stop on the last frame) | r1 §1.5 | ~20 | if you want play-once |
| O3 | Conform-rate playback with "0.50× SLOMO" / "2.00× FAST" | r1 §1.4 | ~60 WebUI + a conform setting | later, with T31 ramp takes |
| O4 | Honest rate row: Recorded, Playing at, Achieved, Frames skipped | r1 §1.4, lesson 2 | ~50 | yes: lossless takes will skip |
| O5 | DROP N badge on the card and in the viewer | r1 §1.4; Core's `dropped_frames` exists after T41 | ~20 | yes |
| O6 | Filmstrip scrubber (16 frames under the bar) | r1 §1.2 | ~80 + 16 thumbnail decodes per clip | no |
| O7 | Sort "Largest first"; "One row" strip view | r1 §1.2 | ~30 | no |
| O8 | Card hover / drag mini-scrub (24-frame flip) | r1 §1.6 | ~70 + decodes | no |
| O9 | Mode boxes: 12b/16b, HDR/SDR, LIN/companded, WAV | r1 §1.4 | ~30 (facts exist after T41) | maybe, in the metadata panel |
| O10 | Timecode overlay: the **recorded** SMPTE start (tag 51043) + frame offset, not Cinemate's position ÷ rate | r1 §1.5 (Cinemate's is not the recorded TC) | ~40 | yes |
| O11 | The recorder writes a preview: a per-take preview track (sidecar), full-rate playback of lossless takes in both UIs | r1 §3 (Cinemate: IFD1 per DNG) | ~400 Core incl. the copy worker; per-frame CPU in every take (UNCONFIRMED; Cinemate +4 ms) | only if M1/M2 say lossless playback is too choppy for you |
| O12 | H.264 through the browser's `<video>` (decodes on the phone, full rate) | — | ~60 WebUI; Range from T45 | if T47's H.264 is slow |
| O13 | Core streams a 16-bit copy of the WAV for browsers that refuse s24/float | — | ~80 | only if M6 fails |

### 8.2 Touch UI changes (not in T40-T47)

| # | Change | Why | Size |
| --- | --- | --- | --- |
| U1 | "1 item", and "Stills" wording in the still-mode dialog | wording bugs (r2 §10 #4) | ~5 |
| U2 | Pause playback when a take starts; ignore the hardware `clip_browser` action in a take; `user_activity` while playing | the touch UI has no hold (r2 §7) | ~30 |
| U3 | Delete through Core (`POST /api/media/delete`) instead of `removeClip` | one gate for every delete; the touch UI's delete has no recording check (`CLM:382-441`, r2) | ~40 |
| U4 | Card thumbnails from Core over `http://127.0.0.1:8000/api/media/frame?…&w=320` | one cache, faster revisits; today every visit decodes every card again (r2 §9 #2) | ~10 |
| U5 | BIT DEPTH from tag 258 (D9) | the file is the witness | ~10 |
| U6 | Histogram sampling across all four CFA sites, in both copies at once (F17) | today 4K histograms show one colour channel (PROBABLE) | ~5 + parity test |
| U7 | Read only the DNG tail for the frame rate when scanning (today `readAll` of the first DNG per take, `DD:1530`) | the touch browser's scan time | ~20 |

---

## 9. Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Lossless 4K plays at ~5-8 fps on the Pi | PROBABLE (§2.2) | the touch UI has the same limit; O4 makes it visible; browser cache smooths replays; O11 if you want full rate |
| R2 | 16-bit uncompressed playback at 25 fps reads 415 MB/s and keeps ~2 cores busy; heat | PROBABLE (F19, §2.2) | only when idle; 2 workers at nice 10; T40 M1 temperature; row-selective reads; 480 w |
| R3 | A new TCP connection and thread per frame (`Connection: close`) | CONFIRMED mechanism (F6); cost UNCONFIRMED | M3; look-ahead 1-2; keep-alive later |
| R4 | A browser cannot play the s24 WAV | UNCONFIRMED | M6; silent with a notice; O13 |
| R5 | Safari needs Range for media | PROBABLE | T45 adds Range |
| R6 | A reader bug in Core's process | PROBABLE risk; mitigations CONFIRMED in the sketch | bounds checks, fuzz in the gate (480 runs clean here), exceptions caught per client thread (`WS:277-283`). If the Pi ever crashes on a file, move decoding into a helper process |
| R7 | The two copies (render, histogram, meta text) drift | PROBABLE over time | parity test in the KB; both files name each other; U-changes go into both |
| R8 | Changing `Cache-Control` handling touches every response | CONFIRMED (F6) | write the default only when a handler did not set one; check `curl -D -` on `/` and `/api/state` |
| R9 | Touch UI root `/media/RAW` vs Core `--media` | CONFIRMED facts (r4 K20) | same on your Pi (PROBABLE); `media_root` is in every reply |
| R10 | T31 ramp takes number frames by count: `dropped_frames` reads 0 | PROBABLE (r4 F8) | note in the metadata; O5 says "drops unknown" for ramp takes once T31 lands |
| R11 | Replacing the WebUI browser could lose today's download/delete flows | PROBABLE | T43 keeps the existing fetch/download/delete functions and only replaces rendering; mocked Chromium gate |
| R12 | Viewer open while the touch UI also plays: two decoders | PROBABLE, rare | slots bound Core's share |
| R13 | Keep-awake while playing costs battery | PROBABLE, small | only while playing |

---

## 10. Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Is a WebUI viewer that shows lossless 4K takes at ~5-8 fps (the touch screen's limit too) good enough for now, with O11 later if not? | yes; decide after T40 |
| Q2 | Should the WebUI's "Show" button only filter the list, or switch the camera's photo mode like the touch UI? | filter only (D1) |
| Q3 | Keep Download (single and selected) in the new browser? | yes (D3) |
| Q4 | In a take, hold everything (frames, thumbnails, sound), or allow cached thumbnails? | hold everything |
| Q5 | Should the WebUI folder button be greyed in a take like the touch UI's (downloads in a take then need the browser opened before)? | greyed |
| Q6 | BIT DEPTH: the stored depth ("12-bit, companded") in the WebUI, and fix the touch UI later (U5)? | yes (D9) |
| Q7 | Touch-UI quirks: fix the wording ("1 item"), copy the one-channel 4K histogram for parity until U6 fixes both? | yes, yes |
| Q8 | Without a WAV, skip late frames (wall clock) instead of slowing down like the touch UI? | skip (D8) |
| Q9 | Which Cinemate options do you want? | O1, O4, O5, O10 |
| Q10 | Your phone: iPhone (Safari) or Android (Chrome)? | design for both; test on yours |
| Q11 | Keep the camera awake while a clip plays (not while paused)? | yes |
| Q12 | Numbering T40-T47, and type the reader and renderer (~600 lines) or copy them from the KB after reading? | T40-T47; your call on typing |
| Q13 | Commit format: house format (area, imperative, Why, Tested, no Co-Authored-By) or what your recent commits use (`What:` + Co-Authored-By)? (r4 K18) | ask |
| Q14 | Later: should the touch UI take its clip facts, thumbnails and deletes from Core (U3, U4), so both screens share one truth? | later, after T44 |

---

## Appendix A. The sketch

Folder: `scratchpad/playback/sketch/` (not in any repository).

| File | Lines | What |
| --- | --- | --- |
| `src/playback/DngFrameReader.hpp` | 372 | tail-IFD reader, payload unpack, LJ92 tiles, bounds checks |
| `src/playback/RawRender.hpp` | 226 | the touch UI's look (`CIP:380-698`) and histogram (`DD:455-536`) |
| `third_party/liblj92/` | — | the touch UI's files; `cmp` identical |
| `playback_bench.cpp` | 251 | `--synthetic DIR` (Core's encoder → reader, 36 checks, timings) and `[--cold] FILE.dng…` (timings on real frames) |
| `reader_fuzz.cpp` | 45 | truncated and byte-flipped copies under ASan/UBSan |
| `parity/parity_test.cpp`, `parity/ui_time.cpp` | 45, 28 | the copy vs the touch UI's own `DngDecoder` and renderer (Qt 6), and the touch UI's own timings |
| `results-host.txt` | | the numbers in §2.2 |

Build lines are at the top of `playback_bench.cpp`. The parity test needs Qt 6 (Core, Gui, Quick), libtiff and `moc`
(`moc ui/src/cdngimageprovider.h`). On this host: g++ 13.3, Qt 6.4.2, 4 threads of a Xeon at 2.1 GHz.
