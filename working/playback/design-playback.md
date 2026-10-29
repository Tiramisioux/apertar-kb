# WebUI playback in the touch UI's shape: how it works, what to build, what to measure first (v2)

**v2**, 2026-10-29, cloud session, designer pass after the two critiques (`critique-code.md`, `critique-operator.md`). Every
critic point was checked against the code before it was accepted; point by point, with the evidence:
`changes-from-critique.md`. v1 is kept as `design-playback-v1.md` and its sketch as `sketch-v1/`. Read-only on every
repository. Nothing ran on the Pi.

Run on this host in this pass (this machine, not the Pi):

- **Sketch v2, `v2_test`: 38 of 38 checks.** New headers `DngTags.hpp` (T47, no liblj92), `ClipFrames.hpp` (frame
  numbers, holes, 0-byte frames, the time → frame map), `PlaybackHold.hpp` (the hold rule as a pure function, the yield
  window), `DecodeSlots.hpp` (slots that own their buffers). Among the checks: a decode in flight stops after one chunk or
  tile when a take starts; a frame read leaves 0 % of the file in the page cache (v1: 100 %); a 4056 × 3040 IMX477 frame and
  a 3840 × 2200 Clear HDR frame from Core's encoder pass the new size cap bit-exact.
- **Page sketch, `page/playclock_test.js` (node 22): 16 of 16.** The number clock over holes, the ramp rule, the
  look-ahead cap, the 503/network back-off, scrub resume, the keep-awake interval, middle elide, the hold texts.
- **The v1 checks again, on the v2 reader:** bench round trip 36 of 36; parity against the touch UI's own decoder and
  renderer on 6 Core-written frames (uncompressed, lossless, lossy 3:1/5:1): 0 differing samples, 0 differing pixels, 0
  histogram difference; fuzz under ASan/UBSan, 640 runs, no report; the code critic's 24-size round trip, 24 of 24.
- **New fuzz case (critic M9):** 20 size lies in IFD0, all refused by `readDngInfo` before any buffer exists; max RSS 47 MB
  (v1 reader on the same 16384 × 16384 lie: 515 MB, reproduced).
- **Critic A.3 reproduced on the v1 reader** (a frame per new thread: 37-43 ms with fresh buffers, 23-25 ms with kept
  ones, 16-bit 4K). The v2 reader reads in chunks, so fresh buffers now cost 22.9 ms against 21.8 ms with slot buffers.
- **Inside Core:** the T47 headers force-included into `ApertarCoreApp.cpp` with Core's flags (`-Wall -Wextra -Wpedantic`,
  libcamera on) and **no** liblj92 path: 0 errors, 0 warnings. The T48 set with the path: 0/0. `DngFrameReader.hpp`
  without the path gives `lj92.h: No such file` (critic B2, reproduced).
- Every new search string and tutor `ref` in §6-§7 was checked to occur once at its line (§7 end).

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `App`, `App.hpp`, `WS`, `Web`, `CP` | `src/ApertarCoreApp.cpp`, `.hpp`, `src/web/WebServer.cpp`, `src/web/WebControlPage.cpp`, `src/ipc/ControlProtocol.cpp` | Core, Patrik's GitHub `cinemate-port` tip `eb9cc39` (`scratchpad/controls/core-tip`) |
| `CC`, `Cdng`, `IFD`, `LJE`, `Lossy`, `Mlv`, `Audio`, `CMake`, `H264C` | `src/camera/CameraController.cpp`, `src/cdng/CdngEncoder.cpp`, `src/cdng/IfdBuilder.hpp`, `src/cdng/LosslessJpegEncoder.cpp`, `src/lossydng/LossyDngEncoder.cpp`, `src/mlv/MlvEncoder.cpp`, `src/audio/AudioRecordingSession.cpp`, `CMakeLists.txt`, `src/video/LibavH264EncoderClient.cpp` | same |
| `CBP`, `CPP`, `Main`, `CamP` | `qml/ClipBrowserPage.qml`, `qml/ClipPlayerPage.qml`, `qml/Main.qml`, `qml/CameraPage.qml` | touch UI, GitHub `cinemate-port` tip `d8098d0` (`scratchpad/controls/ui-tip`) |
| `PC`, `CLM`, `CIP`, `DD`, `MLR`, `VP`, `VPL`, `VPA`, `UCMake` | `src/playbackcontroller.cpp`, `src/cliplistmodel.cpp`, `src/cdngimageprovider.cpp`, `src/dngdecoder.cpp`, `src/MlvReader.cpp`, `src/VideoPlayback.cpp`, `src/VideoPlaybackLibav.cpp`, `src/VideoPlaybackApi.h`, `CMakeLists.txt` | same |
| `cm:` | Cinemate `dev` | `d6cc93e` (`/home/user/tiramisioux/cinemate`) |
| `kb:`, `TP` | Apertar KB; `tutorials/tutorial.py` | `b137ae8`; HEAD is now `11dad27`, two autosaves of `working/playback/` only (critic w9) |
| `sketch/` | design sketch v2, in no repository | `scratchpad/playback/sketch/` (v1: `sketch-v1/`) |

Labels: **CONFIRMED** = I opened the line or ran the command in a designer pass (v1 or v2), or reproduced a critic's run.
**CONFIRMED (rN)** = reader N opened it; not reopened. **PROBABLE** = derived; the derivation is given. **UNCONFIRMED** =
not checked, or only the Pi, a real phone or a browser can settle it.

Tutorial numbers. T33-T35 are taken and the controls project uses T36-T45, so this project starts at **T46** (Patrik may
renumber). `tutorial.py` finds a note by `T` + two digits (`TP:98`), so no "T48a". The KB status line "Tutorials start at
T40" (`kb:working/ramp-ladder/build/STATUS.md:25`) needs a one-line fix when this design lands.

| Number | What | Repo |
| --- | --- | --- |
| T46 | Measure first: what a frame costs on the Pi, what the touch screen shows today, Core's server, your browsers and phone, sync. No code | none |
| T47 | Core knows its clips: per-clip facts from the files (each take's own FPS, frame numbers and holes, the span duration), the hold rule and the yield window, `/api/media/clip`, `playback_hold` | Core |
| T48 | Core draws a frame: `/api/media/frame` by frame number, decode slots, the touch UI's look | Core |
| T49 | WebUI Clip Browser in the touch UI's shape | Core (page) |
| T50 | WebUI Clip Viewer, with the number clock; downloads and deletes yield to a take | Core (page) + gates |
| T51 | Sound: the WAV in the browser, HTTP Range in Core, the stream yields to a take | Core + page |
| T52 | MLV clips | Core |
| T53 | ProRes and H.264 clips, with the touch UI's own movie decoder source | Core |
| T54 | The touch UI yields to a take and keeps time (U2 + U9), so both screens agree. Recommended (Q22) | touch UI |

---

## 0. Short answer

1. The WebUI folder button opens a full-screen **Clip Browser** and **Clip Viewer** with the touch UI's layout, controls,
   flow, wording and nine metadata fields (`CBP`, `CPP`), drawn with the WebUI's shell, buttons, pills and badges. It
   replaces today's list overlay. Download, Select All and the Timelapse and Audio categories stay. On a phone the rows are
   rearranged to fit 390 px (§3.5); the touch UI's sizes are for a 720 × 720 screen.
2. **Core decodes on demand** and sends one JPEG per request. The recording path and the DNG files do not change, so every
   take already on the card plays. Cinemate turned its raw decode off after hardware tests; that decoder was Python/NumPy
   and read uncompressed frames only. Apertar's copy is C++ and costs what the touch UI's own path costs (§2.1).
3. **Same picture and same numbers as the touch screen.** Core gets a Qt-free copy of the touch UI's DNG rules, look and
   histogram, plus the same liblj92 file: 0 differing samples, 0 differing pixels on Core-written uncompressed, lossless and
   lossy frames. CONFIRMED (host). The nine metadata fields carry the touch UI's values. Facts the touch UI does not show go
   into three extra rows (SOUND, FORMAT, DROPPED) and never change one of the nine (§2.4).
4. **Sound and picture stay together on takes with dropped frames.** Core numbers each frame by its sensor time, and the
   WAV spans the same time. The viewer asks for the frame **number** at the clock, not the n-th file. Copying the touch UI's
   "n-th file" rule would put the picture 1.0 s ahead of the sound at 5 s on a typical lossless take, and end it 1.7 s
   early (host arithmetic, §2.6). DURATION is the span, which is also the WAV's length. T54 gives the touch UI the same rule.
5. **What it costs.** One 4K frame, one thread, this host: uncompressed 34-42 ms, lossless 159-202 ms, lossy at least
   70-85 ms (synthetic; a real lossy frame is about four times larger, so expect between lossy and lossless). The Pi is
   about 2× slower (PROBABLE). Two workers: Clear HDR 16-bit uncompressed near 25 fps if the NVMe gives the reads; SDR
   12-bit lossless about 5-8 fps with frames skipped, probably what the touch screen shows today. T46 measures both screens.
6. **Recording wins, on every path.** One rule, `playbackHoldFor()`, answers every playback route, the WAV stream, the clip
   facts and the two download routes: 409 in a take, while writes drain, during a media test, in standby, or with the media
   gone. A **yield window**, set at the top of `handleCommand` for the commands that start a take, a capture, a media test,
   standby or an eject, stops a decode, a WAV stream or a ZIP download within one chunk, before the take's first frame is
   written. Playback reads leave nothing in the page cache. `/api/state` carries the reason as `playback_hold`.
7. **Sound plays in the browser** from the take's WAV, through one new route with HTTP Range. The `<audio>` element is the
   clock (interpolated between its coarse steps), as the touch UI's audio clock is.
8. **Shared with the touch UI:** the liblj92 file, the movie decoder's two source files (built by Core as one more lazy
   plugin, T53), and named copies of the render, histogram and text rules, kept honest by a parity test. The touch UI
   changes only in T54 (recommended): it stops playing when a take starts, and it uses the number clock and the span
   duration.
9. **Core's API** follows today's media library: HTTP routes under `/api/media/*` with `kind` + `id`. The list is fixed;
   new are `clip`, `frame` (by frame number) and `file` (Range); delete gains the writes-pending gate; the downloads yield
   to a take (Q21). No new socket command, because every command runs under the command lock (§2.7). **No change in
   `CameraController.cpp` or in any writer.**
10. **Plan:** T46 measures, T47-T53 build, T54 aligns the touch UI. About 3,900 lines (PROBABLE), of which ~1,150 are
    written and host-tested in the sketch. Your calls first: **Q1** (is the lossless rate acceptable), **Q19** (the
    number clock on both screens), **Q21** (downloads in a take), **Q22** (T54), **Q9** (which Cinemate options).

---

## 1. How the system works today

### 1.1 Operator view: three playback surfaces

| Surface | Where | What you get | What it lacks |
| --- | --- | --- | --- |
| Touch UI Clip Browser and Clip Viewer | Folder button on the camera page, greyed in a take (`CamP:3754`); or the hardware action `clip_browser` (`Main:319-322`), which works in a take | Grid of 16:9 cards (2/3/4 columns), sort Newest/Oldest, long-press selection, Remove Selected. Viewer: preview with FPS, PLAYING/PAUSED and FRAME i / N badges; scrub bar; previous clip / play / next clip; Remove; 48-bar histogram; Clip Metadata (9 fields). Sound out of the Pi through `aplay`. Opens paused on frame 1, loops forever; a seek while playing plays on (`PC:589-609`) | Frame step, speed, loop toggle, a recording hold, a timecode, download; time is the n-th file, so takes with drops drift (§2.6). CONFIRMED |
| WebUI Clip Browser | Folder button `mediaBrowserButton` in the top bar (`Web:2447`) | Centred 900×760 overlay: Clips / Stills / Timelapse / Audio filters, count pill, Refresh Media, sort select, rows with Download and Delete, Select All / Clear / Download Selected / Delete Selected (`Web:3979-4030`) | Thumbnails, any picture, any player. CONFIRMED |
| Cinemate Playback pane | Settings editor tab "Playback" | Take strip, black stage, filmstrip scrub, first/prev/play/next/last frame, loop, HUD, rate row (Achieved, Frames skipped), conform rate. Locked in a take | Sound, delete, the touch UI's shape; downloads were never gated. CONFIRMED (r1 §1) |

The WebUI list is wrong today in two ways a player would inherit:

- Every clip's FPS is the camera's **current** FPS, and a cDNG duration is files ÷ that FPS (`App:6490-6493`, call site
  `App:7821-7824`). A 50 fps take listed while the camera is at 25 shows "25 FPS" and twice its length. CONFIRMED.
- MLV, H.264 and ProRes show duration `--` (`App:6490-6491`). CONFIRMED.

### 1.2 The model: the touch UI's flow today, step by step

| You do | You see | Code | Label |
| --- | --- | --- | --- |
| Tap the folder button | "PLAYBACK / Clip Browser" (or "Still Browser" in photo mode), newest first; "Found 12 clip(s) in /media/RAW." | `ClipListModel` rescans `/media/RAW` on the GUI thread on every open (`CLM:443-586`); the mode follows `photoModeEnabled` (`Main:206`, `:237`); every thumbnail is a full raw decode (`CIP:733-743`) | CONFIRMED |
| Tap a card | "Clip Viewer", paused, "25.000 FPS", "PAUSED", "FRAME 1 / 250" | `selectClip` → `loadClip` (`Main:417-424`); paused on frame 0 (`PC:720`); every `*.dng`, 0-byte files included, is a frame (`PC:696-706`) | CONFIRMED |
| Play | frames at 75 % of the preview box; sound from the Pi's output | `sourceSize` 0.75 while playing (`CPP:393-398`); `aplay` (`PC:996`); frame = floor(ms × fps) as a **position** in the file list, clamped at the last (`PC:849-851`) | CONFIRMED |
| Wait | wraps to frame 1 and keeps playing; with a WAV it wraps at the WAV's end (`PC:834-846`) | `% frameCount()` (`PC:567`) | CONFIRMED |
| Drag the bar | the frame follows the finger; if it was playing it plays on from there | `seekToFrame` (`CPP:95-103`, `PC:589-609`) | CONFIRMED |
| Remove → Remove Clip | the clip at the same index opens | `removeSelectedClip` (`Main:445-467`) | CONFIRMED |
| Back, Back | browser (rescanned, scrolled to top), then camera | Loaders rebuild the pages (`Main:580-640`) | CONFIRMED (r2 §1.3) |
| Someone starts a take | nothing changes on the open page; playback, Remove and the hardware action still work | no `recording` use in either page or in `PlaybackController`; `Main:511-516` only cancels an auto power-off warning | CONFIRMED |

### 1.3 Code view: where clips, frames and sound come from today

| Step | Touch UI (`d8098d0`) | Core / WebUI (`eb9cc39`) | Cinemate |
| --- | --- | --- | --- |
| Clip list | `ClipListModel` scans `/media/RAW` itself (hard-coded, `CLM:174`), on the GUI thread; reads the **whole** first DNG of each take for its frame rate (`DD:1523-1530`); also lists movies copied to the root (`CLM:540-556`) | `GET /api/media` → `discoverMediaLibraryItems(mediaRoot, fps)` walks and stats every file on each call (`App:6422-6497`, `App:6055-6090`); folders only | index from first-frame tags, every 3 s (r1 §2.4) |
| A picture | full raw decode in the UI process: libtiff + liblj92, quad debayer, fixed look (`CIP:577-698`) | none: no reader, no decoder; the DNGs carry no preview (F1) | the JPEG cinepi-raw embeds in each DNG (IFD1), served as is; raw decode turned off (`cm:src/module/app/playback.py:227-236`) |
| Sound | `aplay` subprocess fed from the WAV (`PC:996`) | none | a WAV route nobody calls (r1 §0) |
| In a take | browser button greyed; hardware action, playback and delete not blocked | media delete refused (`App:7660-7666`); downloads not gated (`App:7343-7505`) | frames and WAV answer 409 (r1 §2.6); downloads not gated |

### 1.4 Facts every design must respect

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | Core's DNG: 8-byte header, payload at offset 8, IFD0 + EXIF at the **end**; `NewSubFileType` 0; next-IFD word 0. No thumbnail, no SubIFD | CONFIRMED `Cdng:1384-1392`, `Cdng:1525-1529`, `IFD:123` |
| F2 | Uncompressed payload: 16-bit little-endian, or 12/10-bit packed MSB first | CONFIRMED `Cdng:1155-1184`, `Cdng:1849-1858` |
| F3 | Lossless payload: SOF3, 2 components, tiles of `APERTAR_CDNG_TILE_ROWS` rows (default 128, range 16-1024, tag 323). Tiles are full width only when `width % 16 == 0`; the 1928, 2028 and 1332 modes write two tile columns. Lossy 3:1/5:1 = the same SOF3 coding of companded codes plus a `LinearizationTable`; their folders are `cDNG_3to1_…` / `cDNG_5to1_…` | CONFIRMED `Cdng:52-67`, `Cdng:1237-1241`, `CC:4191`; `Lossy:509`, `:527` (r3); sizes read bit-exact (critic A.1, rerun here) |
| F4 | Clear HDR 12-bit cDNG is also stored as 12-bit codes with a `LinearizationTable`; Clear HDR 16-bit is linear, no table | CONFIRMED `CC:1348-1355`, `CC:3323-3328`, `Cdng:1220` |
| F5 | A frame's number comes from its sensor time, `llround((ts − first) × fps / 1e6)`, so a frame never written leaves a hole in the file numbers | CONFIRMED `CC:3780-3787` |
| F6 | A new take takes the first free counter, so a deleted folder name can come back with new content | CONFIRMED (r3 §1.2, `CC:4169-4211`) |
| F7 | Every tag a player needs is in IFD0/EXIF at the tail: size, bits, compression, CFA, black/white, LinearizationTable, ColorMatrix1/2, ForwardMatrix1/2, AsShotNeutral, AnalogBalance, DateTimeOriginal, TimeCodes, FrameRate, PageName | CONFIRMED `Cdng:1529-1627`, `Cdng:1644-1652`; one tail read of 1.4-9.8 KB |
| F8 | The web server: one detached thread per connection, max 32; the 33rd is closed with **no reply**; 5 s socket timeouts, `Connection: close`, `Cache-Control: no-store` written before the handler's headers, no Range, reason phrases only for 200/204/400/403/404/405/413/500/503 (else "OK"). A handler exception is caught per client thread; a crash is not. `stop()` waits for every client thread | CONFIRMED `WS:59-73`, `WS:127-154`, `WS:174-178`, `WS:247-250`, `WS:263-290` |
| F9 | Every socket and `/api/command` command runs inside `handleCommand`, which holds `commandMutex_` for the whole command. HTTP routes such as `/api/media` do not. Hardware actions and the standby timer also enter `handleCommand` | CONFIRMED `App:9483-9485`, `App:7195`, `App:7213`, `App:7236`, `App:8640` |
| F10 | Core's main binary links no libav; libav lives only in two lazily loaded plugins, opened with `RTLD_NOW \| RTLD_LOCAL`, searched env → next to the binary → `/home/pi/ApertarCore-build/` → bare name, installed to `lib/apertar-core` | CONFIRMED `CMake:69-131`, `CMake:140-170`, `CMake:190-196`, `H264C:17-31`, `H264C:105` |
| F11 | Core has TurboJPEG (FASTDCT) and a libjpeg fallback, used for the MJPEG preview; `APERTARCORE_HAS_JPEG=0` is a supported build and `/preview.mjpeg` then answers 503 | CONFIRMED `App:4165-4230`, `CMake:120-131`, `App:7262-7266` |
| F12 | The touch UI's decoders are Qt-bound, except **liblj92** (MIT, plain C) and the **movie decoder** (`VPL` + `VPA`: libav + swscale, C ABI v2, BGRA out, ≤ 1920 px, no Qt). One decoder handle keeps its packet, frame, swscale context and `lastFrame`; `read()` changes them; libav runs 4 threads per handle; a frame at or before `lastFrame` seeks back to a keyframe | CONFIRMED `VPA:1-27`, `VPL:25-44`, `VPL:128-129`, `VPL:137-216`, `UCMake:136-146` |
| F13 | Clip folders: `cDNG_yy-mm-dd_C0001/<clip>_<9 digits>.dng`; `MLV_…/<clip>.MLV`; `H264_…/<clip>.mp4` (`.mp4.writing` in a take, and **forever** after a pull); `ProRes_…/<clip>.mov`; `<clip>.wav` beside any; containers carry no audio. A folder with only `.mp4.writing` + `.wav` is not listed today | CONFIRMED (r3 §1.2-1.3); `CC:4610`, `CC:4836`, `App:5819-5823` |
| F14 | Signals a playback route can read without the **command** lock: `camera_.isRecording()`, `soundRecordingActive()`, `camera_.timelapseActive()`, `camera_.mediaWriteStatus()`, `camera_.state()`, `mediaSnapshot()`, `mediaSpeedTestRunning_` (own mutex). But `isRecording()`, `state()` and `mediaWritesPending()` take `CameraController::mutex_` (F32) | CONFIRMED `App:7857-7871`, `CC:9844-9872`, `CC:9908-9912` |
| F15 | `mediaGateError()` is skipped in simulate mode and with `APERTAR_MEDIA_REQUIRE_MOUNT=0` (a desk machine whose root is a plain folder) | CONFIRMED `App:9413-9418` |
| F16 | Media delete is refused while recording, sound recording or timelapse (status 400), but not while writes are pending; `remove_all` runs inside the request, and the record gate does not see a delete in progress | CONFIRMED `App:7660-7666`, `App:7683`, `App:7732-7738`, `App:9487-9493` |
| F17 | Activity for standby: only `user_activity`, `wake`, `set_*`, `capture_photo`, `record_*` and `timelapse_*`; the WebUI pings `user_activity` on pointerdown/keydown, at most once a second. The shortest standby is 30 s | CONFIRMED `App:9508-9514`, `Web:11546-11559`, `Web:3780` |
| F18 | The live MJPEG downscale runs on libcamera's completion thread while a viewer is connected; opening the media overlay does not stop it; the `<img>` error handler restarts the stream after 1.5 s | CONFIRMED (r3 §3.5) for the thread; `Web:6176-6184`, `Web:8612-8616` |
| F19 | Touch UI player: opens paused on frame 0 ("FRAME 1 / N"), plays at 75 % of the box, loops, cDNG fps from the first frame clamped 1-60 (fallback 24), the audio clock drives frames when a WAV plays | CONFIRMED `PC:560-571`, `PC:619-621`, `PC:262`, `PC:760-775`, `PC:827-857`, `CPP:393-398` |
| F20 | Touch UI histogram: 48 bins, ~16,000 raw samples on a square grid, step `floor(sqrt(N/16000))`, bin = (count/max)^0.65 | CONFIRMED `DD:488-536`, `PC:262-263` |
| F21 | On a 4K frame that step is 22, an even number, so every sample lands on the same CFA site (red in RGGB) | PROBABLE (arithmetic from F20, active area at 0,0; the code critic agrees, `DD:492`) |
| F22 | Duration text differs in three places: touch card "00:12" / "01:02:03", rounded, "00:00" for no frames (`CLM:147-169`); touch metadata `mm:ss` / `hh:mm:ss` of the rounded milliseconds, "Unavailable" (`PC:135-146`); Core's list "1:02:03", "--" (`App:5887-5905`). All three divide the **file count** by the fps | CONFIRMED |
| F23 | The touch UI writes the shot date with the Pi's **system locale** (`QLocale::system()`, "dd MMM yyyy  HH:mm"); Core never calls `setlocale`, so its `strftime("%b")` writes English months | CONFIRMED `CLM:76`, `PC:75`; grep of `setlocale` in Core's `src/`: no hit |
| F24 | Lossless 4K SDR at 25 fps drops 37-45 of 250 frames per 10 s in the encoder queue; the holes are single frames, one every 5-9; 30 fps is limited by libcamera's thread; memory traffic alone costs frames, direct I/O does not | CONFIRMED `kb:lessons/hardware-log.md:85-88`, `:104-113`, `:165` |
| F25 | NVMe on this Pi: 437 MB/s at PCIe Gen 2, 818 MB/s fio burst at Gen 3 (both **writes**, QD32); a 16-bit 4K frame is 16.6 MB, so 25 fps of them is 415 MB/s | CONFIRMED `kb:lessons/hardware-log.md:140`, `:317-321`, `:383` |
| F26 | WebUI tokens and parts: `--surface #18181b`, `--surface-2 #111113`, `--card-border #27272a`, `--radius-xl 28`, `--radius-lg 22`, `--radius-md 18`, `--radius-sm 14`; `.badge` pills on the live preview; `.preview-center-card`; `.primary-/.secondary-/.danger-button`; accent `#3fd0ff` on `.standby-button`; breakpoints 1120 / 720 / 480 | CONFIRMED `Web:22-39`, `Web:443-451`, `Web:469-476`, `Web:1632-1690`, `Web:2034`, `Web:2062`, `Web:2190` |
| F27 | The web icons `play`, `pause`, `next`, `previous`, `film`, `refresh`, `delete`, `info`, `folder` are byte-identical to the touch UI's | CONFIRMED (`cmp`, both passes) |
| F28 | `tutorial.py`: a check line is split on ` \| ` into exactly three fields; each pipe stage must start with a read-only command; `curl` may name only `ping`, `help`, `get_state`, `get_media_test_state`, `audio_capabilities`, `list_sensor_modes` | CONFIRMED `TP:42-49`, `TP:108-124`, `TP:167-200` |
| F29 | The controls project's T38 adds `case 409: return "Conflict";` to the same `reasonPhrase` | CONFIRMED `scratchpad/controls/design-controls.md:1283` |
| F30 | The take's WAV is trimmed and padded so that its sample 0 is the first frame's time and its length is the span from the first to the last frame plus one period | CONFIRMED `Audio:367-385`, `Audio:606-626` |
| F31 | The touch UI counts 0-byte DNGs as frames in FRAMES, "FRAME i / N" and DURATION (a pulled take leaves 21-23) | CONFIRMED `PC:696-706`, `PC:1196-1200`, `CLM:502`, `CLM:530-534`; `kb:lessons/hardware-log.md:440-460` |
| F32 | `CameraController::stopRecording()` holds `mutex_` across the whole writer drain, `startRecording()` across the session start. A reader of `isRecording()` or `mediaWritesPending()` waits, then sees the take already drained, so `"writing"` shows only for still writes | CONFIRMED `CC:9505-9545`, `CC:9785-9798`, `CC:6265-6271` |
| F33 | Core's DNG writer opens with `O_CLOEXEC` and drops each finished frame from the page cache (`POSIX_FADV_DONTNEED`) | CONFIRMED `Cdng:1748-1751`, `Cdng:1779` |
| F34 | `/api/media/download` and `/download-selected` have no recording gate. A folder streams as `zip -r -0` from a forked child through a pipe, no `Content-Length`; the file stream reads with `std::ifstream` in 64 KiB chunks and checks nothing per chunk | CONFIRMED `App:7343-7505`, `App:6333-6420` |
| F35 | `installInteractions()` wires the old media overlay's ids with no null check, at top level, before the preview stream and the state poll start; `setMediaBrowserOpen` toggles `#mediaBrowserOverlay` with no null check | CONFIRMED `Web:11396-11407`, `Web:11610-11613`, `Web:11649-11653`, `Web:6181` |
| F36 | The WebUI's delete helpers ask `window.confirm` themselves; `fetchMediaLibrary` drops a call while one is in flight | CONFIRMED `Web:10427`, `Web:10476`, `Web:10404-10405` |
| F37 | The largest frame Core writes is the IMX477's 4056 × 3040; IMX585 4K is 3856 × 2180, the 16-bit Clear HDR readout 3840 × 2200 | CONFIRMED `CC:393-395`, `CC:417`, `CC:471-472` |
| F38 | T31 speed ramps (Patrik is building them; **not** on `eb9cc39`): frames numbered by count, every frame's `FrameRate` pinned to the start rate, the WAV in real time, one `fps-ramp.txt` per take with `requested_frame applied_frame frame_us seen tc_at_base boot_us from_fps to_fps shutter_us` | CONFIRMED in the KB (`kb:working/ramp-ladder/README.md:29`, `kb:working/ramp-answer.md:14`, `:77`, `:92`); grep of `fps_ramp` in `eb9cc39`: 0 |
| F39 | The WebUI page has no `pushState`, `popstate`, `wakeLock`, `-webkit-touch-callout` or `contextmenu`; it is served over plain HTTP, where the Screen Wake Lock API does not exist (secure contexts only) | CONFIRMED grep `Web`; the secure-context rule is PROBABLE (W3C spec, general web knowledge) |
| F40 | `eject_media` and `format_media` run a plain `umount`, which fails while any file on the media is open | CONFIRMED `App:3779`, `App:3832`; the EBUSY rule PROBABLE (Linux) |

---

## 2. The decisions

### 2.1 Where the picture comes from

| | A. Core decodes on demand | B. Recorder embeds a JPEG in each DNG (Cinemate, IFD1) | C. Recorder writes a preview track per take | D. The touch UI serves frames | E. The browser decodes raw | F. The touch UI's code in a helper process |
| --- | --- | --- | --- | --- | --- | --- |
| Change in the recording path | none | per-frame JPEG in the copy worker; preview buffers mapped in raw mode; IFD0 next-IFD patched (r3 §2.2) | per-frame JPEG + one appended file per take | none | none | none |
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
- **Cinemate's own lesson.** Cinemate's operator turned raw decode off after hardware tests: "raw decode is far more
  demanding on the Pi than serving the embedded thumbnail" (`cm:src/module/app/playback.py:227-236`, commit `5124a1d`).
  That decoder was NumPy + Pillow and read uncompressed frames only (`cm:src/module/app/dng_preview.py:43`, `:488`).
  Apertar's copy is C++ and costs what the touch UI's own C++ path costs (§2.3), and the touch screen already plays these
  takes that way. T46 M1 checks it on the Pi; O11 is the way out if it does not hold.
- A's weak point is lossless 4K. The touch UI has the same weak point today (§2.3). If T46 shows it is too choppy for you,
  O11 (C) fixes it for both screens at once, because both could read the preview track.
- C over B, if it is ever built: the DNGs stay byte-identical (no Resolve question) and MLV and movies are covered too.
- D, E and F are rejected for the reasons in the table. F would avoid the copies, but it adds a long-running Qt process
  beside Core only to keep one render rule in one place; the parity test does that job (§2.4).

### 2.2 How the picture travels to the browser, and how it is paced

| | 1. One JPEG per request, fetched by the page (chosen) | 2. A playback MJPEG stream paced by Core | 3. `<video>` | 4. WebSocket |
| --- | --- | --- | --- | --- |
| Works with Core's server as it is | yes (buffered body, `Content-Length`) | yes (the live preview does it) | needs Range; H.264 only | no WebSocket in Core |
| Per-frame data (number, index, histogram, decode time) | in response headers | no | no | — |
| Sync with the browser's audio clock | the page asks for the frame the audio clock wants | Core's clock drifts from the phone's audio clock; every pause or seek is a new stream | native | — |
| Skips under load | the page skips (503 → next frame, with back-off) | Core drops | native | — |
| Browser traps | few | every MJPEG `<img>` trap (silent stream, `load` once per connection; r4 §6) | iOS fullscreen only here | — |

Chosen: **1**, Cinemate's mechanism (r1 §2.1), with these Apertar changes:

- The page uses `fetch()`, not `<img src>`, so it can read the headers (`X-Frame-Number`, `X-Frame-Index`, `X-Histogram`,
  `X-Decode-Ms`) and draw into a `<canvas>` only when a frame is decoded (`createImageBitmap`). The old frame stays until
  then, as the touch UI's `retainWhileLoading` does (r2 §3.2). Same origin, so every header is readable.
- **The clock wins, by frame number.** With a WAV, `audio.currentTime` is the clock; without, a wall clock. The wanted
  frame is the **number** `first + floor(clock × fps)` (§2.6); over a hole or a 0-byte frame the picture before it stays
  up and no request is made. The page keeps two requests in flight (one per Core slot) and asks **ahead** by the measured
  round trip, capped at two frame periods (critic M12: the browser's six connections per host can queue requests and
  inflate the round trip). A frame that arrives late is drawn only if it is newer than the one on screen.
- **Refusals cost little.** A 503 or a rejected `fetch()` (the 33rd connection is closed with no reply, F8) skips that
  frame and the lane waits one frame period; three in a row back off 500 ms; a decoded frame resets the lane
  (`page/playclock.js` `laneAfter`, tested). Cinemate's client pauses instead (r1 §5.5); v1 re-asked at round-trip rate,
  which two viewers would turn into a stream of refused connections (operator P16).
- **No HTTP caching.** Core keeps `Cache-Control: no-store` on every response (F8). Revisits are cheap anyway: Core keeps
  the JPEGs it made in memory (8 MB for thumbnails, 24 MB for play and paused frames, so one long clip does not evict the
  grid), and the page keeps the thumbnails it fetched while it is open. Custom headers go through `Response::headers`
  (`WS.hpp:18-34`), so no header code changes.

### 2.3 What the sketch measured (this host, not the Pi)

The sketch (`sketch/`, Appendix A) is about 1,150 lines of product code in six headers and a page module, plus ~750 lines of tests. `DngTags.hpp` (T47)
reads Core's DNG tags without Qt, libtiff or liblj92. `DngFrameReader.hpp` (T48) reads the samples in chunks, asks a stop
callback before each chunk or tile, and drops what it read from the page cache. `RawRender.hpp` copies the touch UI's look
(`CIP:380-698`) and histogram (`DD:455-536`). `third_party/liblj92` is the touch UI's file, identical by `cmp`.

**Correctness**, on frames written by Core's own encoders (`CdngEncoder`, and `LossyDngEncoder` for 3:1 and 5:1):

| Check | Result | Label |
| --- | --- | --- |
| Reader round trip, 12/16-bit × uncompressed/lossless at 4K: size, bits, compression, FrameRate, PageName, DateTimeOriginal, matrices, every sample bit-exact | 36 of 36 (v2 reader) | CONFIRMED |
| The code critic's six sensor sizes × 12/16 × uncompressed/lossless, incl. two tile columns and a partial last tile row | 24 of 24 bit-exact (v2 reader) | CONFIRMED |
| 4056 × 3040 12-bit (IMX477) and 3840 × 2200 16-bit, uncompressed and lossless, against the v2 size cap | 4 of 4 pass, bit-exact | CONFIRMED |
| Tags cost one read of the file's tail | 1,448 B uncompressed, 1,596 B lossless, 9,820 B lossy | CONFIRMED |
| The same frames through the **touch UI's own** `DngDecoder` + `renderRawFramePreview` (Qt 6.4.2) vs the copy | 6 frames: samples differ 0; 640x360 pixels differing 0; histogram max bin difference 0.0000 | CONFIRMED (`sketch/v2-parity-host.txt`) |
| Fuzz: 640 truncated or byte-flipped copies of 4 frames, ASan + UBSan | 395 rejected with an error, the rest decoded, no sanitizer report | CONFIRMED (`sketch/v2-fuzz-host.txt`) |
| Size lies in IFD0 (16384², 4096 × 3072, 8192 × 2, 2 × 65535, 4056 × 3040 on 4K payloads) | 20 of 20 refused by `readDngInfo`, before any buffer; max RSS 47 MB. v1: 515 MB on the 16384² lie | CONFIRMED |
| A take starts mid-frame (the yield window opens after the first chunk) | 16-bit uncompressed: stops after 1 of 17 chunks of 128 rows; lossless: after 1 of 17 tiles | CONFIRMED (`v2_test` stop) |
| What one frame read leaves in the page cache | v1 reader: 100 % of the file; v2: 0 % | CONFIRMED (`v2_test` cache, `mincore`) |
| A frame on a new thread (as the web server runs it), fresh buffers vs kept | v1 reader: 37-43 ms vs 23-25 ms (16-bit unc., critic A.3 reproduced); v2 reader: 22.9 ms vs 21.8 ms with slot buffers | CONFIRMED (`v2_test` alloc, `v2tmp/a3`) |
| Lossy BIT DEPTH: the copy reads the stored 12 bits; the touch UI reports 16 after applying the table | real; the WebUI shows the touch UI's "16-bit" and says "12-bit companded" in FORMAT (§2.4) | CONFIRMED |

**Cost per frame, one thread** (Xeon 2.1 GHz, 4 threads; synthetic scene with sensor-like noise; v2 reader, which reads
from the drive each time because it drops the pages):

| Frame | Payload | Read + unpack/decode | Render 640 w | Render 1920 w | Histogram | JPEG q80 | One 640 w frame | Per worker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4K SDR 12-bit uncompressed | 12.4 MB | 17.6 ms | 17.1 ms | 153 ms | 0.16 ms | ~1.5-2.2 ms (26.5 KB at 960 w) | 37 ms (v1 37-40) | 27 fps |
| 4K SDR 12-bit lossless | 7.7 MB | 150 ms | 17.4 ms | 157 ms | 0.15 ms | ~1.4 ms | 169 ms (v1 159-168) | 5.9 fps |
| 4K SDR 12-bit lossy 3:1 / 5:1 (synthetic, 1.0 MB) | 1.0 MB | 72 / 57 ms (v1) | 11 ms | 100-108 ms | 0.14 ms | ~1.1 ms | 85 / 69 ms (v1) | 12-15 fps; **a real 3:1 frame is ~4 MB** (12.4 MB ÷ 3), so expect between this row and lossless (PROBABLE; T46 M18) |
| 4K Clear HDR 16-bit uncompressed | 16.6 MB | 14.7 ms | 17.8 ms | 152 ms | 0.16 ms | ~1.5 ms | 34 ms (v1 41-42) | 29 fps |
| 4K 16-bit lossless | 15.4 MB | 183 ms | 18.1 ms | 151 ms | 0.15 ms | ~1.4 ms | 202 ms (v1 171-189) | 4.9 fps |
| The touch UI's own path, same files | | decode 17-19 ms uncompressed, 167-170 ms lossless | render 19-25 ms (640x360) | | | | | |

All rows CONFIRMED on this host (`sketch/v2-bench-host.txt`; v1's `results-host.txt`). The host varies by ±10-15 % between
runs. For the Pi (PROBABLE, not measured): a Pi 5 core with its memory is roughly half as fast as this one for this
memory-heavy work, and a cold 16.6 MB read from NVMe adds 24-40 ms (F25; buffered reads at a queue depth of 2 may be slower
than the write figures, critic §6). So about 55-100 ms per uncompressed 640 w frame (two workers: ~20-35 fps, perhaps
read-bound at 15-25 fps) and 250-450 ms per lossless one (two workers: ~5-8 fps). T46 measures it with the same tool on
your takes.

### 2.4 What is shared with the touch UI, and the parity rule

**The rule (v2, operator P15).** Both screens give one answer for the same take. The WebUI shows the touch UI's nine
metadata fields with the touch UI's **values and words**, the touch UI's badges and its histogram. Where the touch UI's
answer is wrong about the take (time on takes with holes, F5/F30), the fix goes into both screens in this project: the
WebUI from T47/T50, the touch UI in T54 (U9). Facts the touch UI does not show go into **extra rows** that only the WebUI
has, and never change one of the nine values. So:

| Point | v1 | v2 |
| --- | --- | --- |
| BIT DEPTH of a companded or lossy take | the stored depth "12-bit, companded" (D9) | the touch UI's "16-bit"; the stored form goes in the extra row FORMAT ("12-bit companded · lossy 3:1") |
| 4K histogram on one CFA site (F21) | copied (D11) | copied; U6 fixes both later |
| 0-byte frames | left out of FRAMES and N | counted, as the touch UI counts them (F31); shown like a hole; DROPPED says how many |
| Time on takes with holes | position (copied flaw) | frame number on the WebUI now, on the touch UI with T54 (D15 until then) |
| DURATION | files ÷ fps | the span ÷ fps, on both screens after T54 (D15 until then) |

| Thing | Shared how | Why |
| --- | --- | --- |
| Lossless JPEG decoder | **Same file**: `ApertarUI/third_party/liblj92/{lj92.c,lj92.h,LICENSE,README.apertar.md}` copied to `ApertarCore/third_party/liblj92/` in T48; `cmp` shows it identical; warning-free under Core's `-Wall -Wextra -Wpedantic` (critic m11) | Plain C, MIT, already carries the touch UI's local fix. Copying a vendored file is how both repos already work |
| Movie decoder (ProRes, H.264) | **Same source files**: `VPA` and `VPL` copied byte-identical into Core's `src/playback/` and built by Core's CMake as `apertar-video-libav.so`, a third lazy plugin next to its two encoder plugins (T53) | Qt-free, versioned C ABI (F12). Core already loads plugins this way (F10). Loading the touch UI's installed `.so` instead is Q16 |
| DNG reading, render look, histogram, metadata text, clip rules, MLV rules | **Named copies** in `src/playback/*.hpp`, each with a comment naming its touch-UI source, plus a parity test in the KB that builds both on the Pi | The touch UI's versions are Qt-bound (F12). KB rule M5, "copies: one change, several places" (`kb:llm/tutoring.md:70`); the parity test is this design's own rule for keeping such copies honest |
| Decoding work | **Not shared.** The touch UI decodes for the touch screen in its own process; Core decodes for browsers | Two screens may play at once; each has its own budget (R12) |
| Thumbnails | **Not shared** by default. Core renders and keeps its own in memory | Option U4 lets the touch UI load Core's (one cache) |
| Toolkit, layout code | Not shared: QML vs HTML/CSS/JS | Different runtimes; the design copies the layout and the words, not the code |
| Sound | Not shared: `aplay` on the Pi vs `<audio>` in the browser | The WebUI viewer is on your phone or laptop |
| Media root | Not shared today: touch UI `/media/RAW` hard-coded (`CLM:174`), Core `--media` | The same folder on your Pi (PROBABLE); every reply names `media_root` (R9) |

### 2.5 Formats

| Item | Picture in the WebUI | Facts | When |
| --- | --- | --- | --- |
| cDNG uncompressed, lossless, lossy 3:1/5:1, Clear HDR 12-bit companded | Core decode (§2.1 A) | first frame's tail (F7); frame numbers from the names (F5) | T47, T48 |
| Timelapse folder of DNGs (counter-numbered, `CC:1038-1047`) | same decoder; plays at the first frame's FrameRate, fallback 24, like the touch UI (`PC:262`) | same; DNG + JPEG pairs count once per stem, the DNG first (critic m9) | T48 |
| JPEG-only timelapse | TurboJPEG decode at 1/2, 1/4 or 1/8 scale | file sizes, dates; name order | T48 (the touch UI does not list these) |
| DNG still | same decoder, one frame | same | T48 |
| JPEG still | TurboJPEG decode, then a JPEG at the asked width | file size, date | T48 |
| PNG / TIFF still | "NO PREVIEW" (the WebUI cannot show them yet) | file | later |
| T31 speed-ramp take (when T31 is in your tree) | as a cDNG take, played **as its timeline** at the start rate (F38) | `fps-ramp.txt`: start and peak rate, the real length | T47 facts, T50 rule |
| MLV (single file, uncompressed) | Core reads frame N through a block index built once per clip (a named copy of `MLR:153-278`), rendered with the touch UI's MLV "ISP" path (`CIP:655-662`, r2 §5); VIDF carries the same time-based `frameIndex` that names the DNGs (`CC:7975`, `CC:3998`, `Mlv:1027`), so the number clock applies | MLVI/RAWI header | T52 |
| MLV not finalized (count 0) | not playable: "MLV is not finalized or its frame count is invalid." (`MLR:176-177`); O21 plays the recovered frames | | T52 |
| ProRes `.mov`, H.264 `.mp4` | Core's copy of the movie plugin gives BGRA frames ≤ 1920 px; Core encodes JPEG; one request at a time per movie, in order (F12) | plugin `probe` | T53 |
| `.mp4.writing` (also after a pull, F13), ProRes without `moov` | listed (T53 adds `.writing` to the scan), not playable: "H.264 take was not finalized." / "ProRes take was interrupted; it has no index." | | T53 |
| Movie copied to the media root | not listed (Core lists folders, `App:6443-6497`; the touch UI lists them, `CLM:540-556`): known gap D20 | | later |
| Sound recording (`Audio/…/*.wav`) | no picture; the stage says "SOUND ONLY" and the time; the viewer plays the sound | WAV header | T51 |

Why the plugin for H.264 too, and not `<video>` by default: one viewer path, exact frame numbers for "FRAME i / N", the
same histogram rule as the touch UI, and the same hold rule. With one request in flight per movie and in order, playing
decodes each frame once; a scrub position costs a seek plus up to one GOP (= round(fps), `src/video/LibavH264EncoderPlugin.cpp:140`)
of software decode at 2560 × 1440 (`CC:1053-1054`). If T46 M19 shows that is too slow, O12 (`<video>` on the phone's own
decoder) is the next step (Q27).

### 2.6 Sound and time

- The browser plays the take's WAV through one `<audio>` element. Core serves it on `/api/media/file` with **HTTP Range**
  (206, `Content-Range`, `Content-Length`, `Accept-Ranges: bytes`). Range is needed to seek, and Safari plays media only from
  servers that answer Range (PROBABLE, general web knowledge; T46 M6 checks your browsers).
- **The clock maps to frame numbers.** The WAV starts at the first frame and spans to the last (F30); frames are numbered
  by time (F5). So sound time *t* belongs to frame number `first + floor(t × fps)`. The viewer asks Core for that number;
  Core serves the frame at or before it. Over a hole (a frame never written) or a 0-byte frame the frame before stays up.
- **Why it matters (host arithmetic, `v2_test` drift).** A 10 s, 25 fps lossless take that lost 42 of 250 frames in the
  KB's pattern (one hole every 5-7 frames): with the touch UI's rule (the n-th file), the picture at 5.0 s shows 6.04 s,
  1.04 s ahead of the sound; the last file is reached at 8.32 s and held for 1.7 s while the sound plays on. With the number
  clock the picture is never ahead and at most one hole (0.08 s) behind. Your lossless 25 fps takes lose 37-45 of 250
  frames (F24), so this is every lossless take.
- `audio.currentTime` moves in coarse steps in some browsers (UNCONFIRMED per browser); the page interpolates with
  `performance.now()` between changes and resyncs on each change and on `seeked` (critic m12). The picture follows the
  sound; when the WAV ends, playback wraps, as the touch UI wraps at the WAV's end (`PC:834-846`).
- **Without a WAV**, a wall clock runs through the same map, so the take plays in real time and its length matches the
  slate (D8).
- **T31 ramp takes** (F38) are numbered by count, every frame says the start rate, and the WAV is real time. Played by the
  WAV clock, the 50 fps part would run at half speed against the sound and the picture would be cut off when the WAV ends
  (operator P2, arithmetic: 10 s at 25 + 10 s at 50 → 750 frames, a 20 s WAV, frames 500-749 never shown; the touch UI does
  the same, `PC:836-855`). Default: play a ramp take **as its timeline** (the start rate, a wall clock, sound off) with one
  line: "Speed ramp 25 → 50 fps: plays as on a 25 fps timeline. The sound is real time, so it is off." O3b plays it in real
  time through `fps-ramp.txt` with sound on (Q30).
- A paused `<audio>` stops reading. Core's 5 s send timeout then closes the connection (F8), and the browser resumes with a
  new Range request (PROBABLE). That is why Range comes with sound, not later.
- **The stream yields to a take.** The range streamer asks the yield window and the hold rule between 64 KiB chunks and
  ends the stream on a hold; the page then runs `audio.pause(); audio.removeAttribute("src"); audio.load();` so the
  connection drops at once (critic M3a, operator P3).
- WAV search order as the touch UI: `<clip>.wav`, `<dir>.wav`, `audio.wav`, then any `*.wav` by name (r2 §4.2). One RIFF
  parser: Core's existing `wavDurationTextForFile` (`App:5926-5993`) is extended to return the format too (critic m7).
- Your WAVs are s24 stereo 48 kHz with `bext` and `iXML` chunks (`kb:lessons/hardware-log.md:456`, r4 F5). Browser support
  is UNCONFIRMED: T46 M6. If a browser refuses one, the viewer plays silently and the SOUND row says so (O13 would serve a
  16-bit copy). RF64 starts only above 4 GB (about 4 h of s24 stereo), so it does not matter here (PROBABLE).
- **Bluetooth headphones** may lag the clock by their output latency (UNCONFIRMED; T46 M12). If they do, O22 adds a
  per-device A/V offset kept in the browser (`localStorage`, a per-viewer convenience).
- MLV-embedded audio does not exist in Core's files (`kAudioClassNone`, r3 §1.3).

### 2.7 Interlocks: recording, standby, pulled media

**One rule.** `playbackHoldFor(signals)` is a pure function (`sketch/src/playback/PlaybackHold.hpp`, tested). Its two
callers fill the same small struct: `buildWebStateJson` passes the values it has already read (`App:7859-7870`), so the
state reply asks the camera once, not twice (critic M8); every playback route calls `playbackHoldReason()`, which reads
each signal once. Neither waits for the command lock (F9).

| Order | Condition | `playback_hold` | Why |
| --- | --- | --- | --- |
| 1 | `camera_.isRecording() \|\| soundRecordingActive() \|\| camera_.timelapseActive()` | `recording` | reading the card during a take competes for the same memory and drive (F24, F25) |
| 2 | the **yield window** is open (below) | its reason | a take, a capture, a media test, standby or an eject is starting, before the camera says so |
| 3 | `camera_.mediaWriteStatus().pending` | `writing` | a still or the last take is still being written; seen for still writes only, because a video take's drain holds the camera's mutex until it is done (F32) |
| 4 | `mediaSpeedTestRunning_` | `media_test` | a speed test measures the drive; reads would spoil it |
| 5 | `camera_.state() == CameraState::Standby` | `standby` | the touch UI stops playback in standby (r2 §1.1); the governor is on powersave (r3 §4.4) |
| 6 | the watcher says the media is not mounted and answering (`!mediaSnapshot().mounted()`), unless the media gate is switched off (F15) | `media` | a pulled NVMe can block reads for 30-60 s (r3 §4.5) |
| — | otherwise | `""` | |

**The yield window** (critic M8, changed). At the top of `handleCommand`, right after it takes the command lock and before
any camera call, these commands open a 3 s window: `record_start`, `capture_photo`, `timelapse_start` (reason
`recording`), `run_media_speed_test` (`media_test`), `enter_standby` (`standby`), `eject_media` and `format_media`
(`media`; a plain `umount` fails while a frame is open, F40). The media watcher opens it when the media goes away. The
window is two atomics (`untilMs`, `reason`). A decode, a WAV stream and a ZIP download ask only `yield.active(now)` between
chunks, so they stop within one chunk, **before** the take's first frame is written, and never touch the camera's mutex
(which `startRecording` holds, F32). Hardware buttons and the standby timer enter `handleCommand` too (F9), so every path
is covered. After 3 s the real signal is visible, or the command failed and playback may go on. While any hold lasts,
the media watcher (every 250 ms in a take, 1 s otherwise, `App:9383`) extends the window by 1.5 s, so a long stream that
checks only the atomic also stops for a take that began while its client was stalled; the window closes at most 1.5 s
after the hold ends (`v2_test` hold). Why not the critic's "flag cleared by the next request": a request that arrives after
the command starts but before `recording_` is true would clear it and read during the take.

| Reader | In a hold | Mid-read when a hold starts | Plan |
| --- | --- | --- | --- |
| `/api/media/frame` | 409 + reason | stops at the next chunk (128 rows) or tile | T48 |
| `/api/media/clip` | answers from the facts cache with `"held":"…"`, reads nothing; 409 when the clip is not cached (critic M2) | — | T47 |
| `/api/media` | answers from the cache with `"held":"…"`, reads nothing | — | T47 |
| `/api/media/file` (WAV) | 409 | the streamer stops between 64 KiB chunks; the page drops `src` (critic M3a) | T51 |
| `/api/media/download`, `/download-selected` | 409 "Recording. Downloads wait until the take ends." | the ZIP and file streams stop between chunks; the `zip` child is ended; the page says "Download stopped: recording started. Start it again after the take." because a cut ZIP has no `Content-Length` and looks complete (F34; operator P3) | T50, Q21 |
| Thumbnails, sound-only items | as frames and file | as frames and file | T49, T51 |

Rules:

- The check runs **in each request**, first, before any validator that stats the media (critic m19) and before a decode
  slot is taken (Cinemate lesson C10: a guard that reads the present cannot defend against a job that starts later; r4 §5.2).
- **The page cache stays as the writer leaves it.** Frames open with `O_CLOEXEC`, each chunk or tile is dropped with
  `POSIX_FADV_DONTNEED` once it is in memory, and the whole file at close, as Core's writer does (F33). On the host one
  frame read now leaves 0 % of the file cached (v1: 100 %). A 16-bit review at 415 MB/s would otherwise fill the 4 GB Pi's
  cache with clean pages in ~8 s (PROBABLE; critic M4, operator P19). T46 M16 measures the first take after a review.
- **Memory goes back.** The decode slots own their buffers (§4.7). The media watcher loop, which already wakes every second
  (`App:9383`), frees them after 30 s with no frame or as soon as a hold starts. The JPEG caches stay, so thumbnails survive
  a take.
- **No lock is held across a card read** (critic m14): a folder scan or a frame read runs outside the facts-cache and LRU
  mutexes and swaps its result in under them, so `/api/media` can still answer from the cache while a read on a dead NVMe
  hangs.
- **Recording is never refused because someone is watching.** Playback yields; no record gate changes for playback.
- **Delete** gains the `writing` check (F16), with Core's existing words "Wait for the current capture to finish writing to
  media." (`App:9489`). **Q23** (default yes): `record_start` is refused with "Deleting media. One moment." while a
  delete runs, because `remove_all` of a long take can take seconds and the record gate does not see it (F16, operator P11).
  This is a change to a record gate, so it is your call.
- **The WebUI folder button is greyed in a take or a timelapse**, like the touch UI's (`CamP:3754`): on
  `snapshot.recording || snapshot.timelapse_active` (`App:8000`, `App:8009`; critic m5). An open browser or viewer stays
  open and shows the hold; its card has a **Live view** button that closes the overlay (operator P22).
- **After a video take** `/api/state` waits for the drain (F32), so the page sees `recording`, then `""`. If a poll or a
  frame request takes over 1.5 s while the card says Recording, the card says "Finishing the take…" (operator S1).
- **Standby:** while a clip **plays**, the page sends `user_activity` every min(20 s, timeout ÷ 3), so watching counts as use
  (F17; critic m13). Paused, it does not, so a forgotten tab does not keep the camera awake.
- **No socket command.** A `get_clip_info` command would run inside `handleCommand` under `commandMutex_` (F9). On a pulled
  NVMe its folder read could block for 30-60 s, and `record_stop` would wait behind it. The HTTP routes run on their own
  client threads. `tutorial.py` would also refuse a check that calls it (F28). If the touch UI ever takes its facts from
  Core (U8), it reads the same HTTP route on `127.0.0.1:8000`.

### 2.8 CPU and I/O budget on the Pi 5

| Situation | Playback work allowed | Cost (PROBABLE unless marked) |
| --- | --- | --- |
| **A take**, sound recording, timelapse, writes draining, media test | **none**: frames, thumbnails, clip facts, sound and downloads answer 409; the list answers from memory; a decode, a WAV stream or a ZIP in flight stops within one chunk | ~0 on the card and the CPU. What remains is today's 1 s `/api/state` poll per open tab (CONFIRMED mechanism, r3 §4.1) and one 409 per page poll cycle |
| The first take after a review | — | the page cache as the writer left it (v2 drop; CONFIRMED on the host); the SoC maybe warmer: T46 M16 |
| Standby | none (409) | 0 |
| Idle, browser open, thumbnails filling | ≤ 2 decodes at once, at nice 10, results kept in the 8 MB thumbnail cache | one decode per card the first time: ~0.1 s uncompressed, ~0.3-0.4 s lossless; 50 takes ≈ 5-10 s to fill the grid once after a Core start; then memory |
| Idle, playing 4K Clear HDR 16-bit uncompressed at 640 w | 2 workers | ~1.5-2.5 cores; 415 MB/s of reads at 25 fps, at the Gen 2 link limit (F25, which is a write figure), so the rate may be read-bound at 15-25 fps. Heat: T46 M1 |
| Idle, playing 4K SDR 12-bit lossless | 2 workers | 2 cores busy, ~5-8 fps shown, frames skipped; ~40-60 MB/s of reads (only decoded frames are read) |
| Idle, paused | one frame at the stage's size (≤ 1920 w) | ~0.3-0.6 s of one core per pause |
| Live preview while the overlay is open | **stopped** by the page | removes the MJPEG downscale from libcamera's thread (F18) |
| Two browsers playing | the same 2 slots | each lane waits a frame period after a refusal, 500 ms after three (§2.2); no 503 storm (operator P16) |
| Memory | | per slot ≤ 25 MB of samples + ~2 MB scratch + ≤ 6 MB RGB; + 32 MB of JPEG caches: ~100 MB at most of 4 GB; the slots' share is freed on a hold or after 30 s idle |

Knobs, read once at start like `APERTAR_CDNG_TILE_ROWS` (`Cdng:52-67`): `APERTAR_PLAYBACK_WORKERS` (default 2, range 1-3) and
`APERTAR_PLAYBACK_CACHE_MB` (default 32, split 1:3 between thumbnails and play frames). A worker lowers its own thread
priority for the decode with `setpriority(PRIO_PROCESS, gettid(), 10)`, so camera threads win when both run. Nothing needs
restoring: the web server makes a new thread per connection and it ends with the response (F8), and an unprivileged thread
cannot raise its priority again anyway (PROBABLE, Linux nice rules). The movie decoder is opened after that call, so its
four libav threads inherit nice 10 (critic M6).

### 2.9 Where the WebUI deliberately differs from the touch UI

| # | Touch UI | WebUI | Why | Ask |
| --- | --- | --- | --- | --- |
| D1 | "CAPTURE / Clip Mode · Still Mode" switches the **camera's** photo mode (`CBP:115-119`) | Same place and look, labelled "SHOW / Clips"; it opens a small menu Clips · Stills · Timelapse · Audio and only filters the list. It **opens** on Stills when the camera is in photo mode, as the touch browser follows the mode (`Main:206`, `:237`; `photo_mode_enabled` in `/api/state`, `App:8172`) | A list filter should not change the camera from a phone; the WebUI already has four categories | Q2 |
| D2 | "1 ITEMS" | "1 item" | wording bug (r2 §10 #4) | Q7 |
| D3 | no download, no select all | Download (in the viewer's title row, away from Remove; and for a selection) and Select All kept from today's WebUI browser | existing WebUI features (r4 P7); the WebUI has no login, so Download stays apart from Remove (operator P9) | Q3 |
| D4 | long press only | long press (Qt's 800 ms) everywhere, with the system image menu switched off on cards (`-webkit-touch-callout: none`, `contextmenu` prevented, `draggable="false"`); with a mouse the selection badge also shows on hover and a click on it starts selection | a phone's image menu would fire first (operator P7); with it off, the touch UI's 800 ms can stay | Q10 |
| D5 | live refresh by a file watcher | refresh on open, on Refresh, after a delete, and when `playback_hold` returns to `""` | no event channel to the browser (r4 §3.3); `recording` going false is too early for stills (operator P17) | — |
| D6 | no hold in a take | hold with a named reason (§2.7) | Cinemate's mechanic; the brief asks for its mechanics | Q4 |
| D7 | sound out of the Pi | sound out of the phone or laptop | the viewer is remote | — |
| D8 | without a WAV, a slow decode stretches time (`PC:774`, tick-driven `nextFrame()`) | a wall clock runs and late frames are skipped | over Wi-Fi a stretched clock makes the length meaningless | Q8 |
| D9 | BIT DEPTH "16-bit" for any DNG with a LinearizationTable | **the same** "16-bit"; the stored depth goes in FORMAT (D16) | v2 parity rule (§2.4) | Q6 |
| D10 | Back rebuilds the browser: rescan, scroll to top | Back returns to the same grid and scroll | the page keeps the grid in memory | — |
| D11 | 4K histogram samples one CFA site (F21) | copied as is, so both screens draw the same bars | parity first; fix both later (U6) | Q7 |
| D12 | no keys | Space plays/pauses (on `keydown`, `preventDefault`, ignored in inputs; operator S4), Escape closes (Escape already closes the overlay, `Web:11620`) | a laptop has a keyboard; frame-step keys are O1 | Q18 |
| D13 | no Timelapse or Audio category | kept from today's WebUI; sound recordings play sound only | today's WebUI lists them (`Web:4000-4003`) | Q3 |
| D14 | the hardware action `clip_browser` opens the touch browser | not delivered to browsers | Core broadcasts events only to socket clients (r4 §3.3) | — |
| D15 | time = the n-th file; DURATION = files ÷ fps | time = frame number; DURATION = span ÷ fps (§2.6) | the touch UI's rule drifts on every take with holes (F5, F30); **until T54** the two screens differ on lossless takes | Q19 |
| D16 | nine fields | the same nine, then three WebUI-only rows: **SOUND** ("24-bit 48 kHz stereo", "None", "Not finalised: audio_capture.raw is on the media", "This browser cannot play it"), **FORMAT** ("Clear HDR 16-bit · uncompressed", "SDR 12-bit · lossless", "12-bit companded · lossy 3:1"), **DROPPED** ("43 missing · 0 empty", "none", "unknown (speed ramp)") | silence and choppiness each mean several things; the tags and folder say which (operator P5, P6, P24) | Q25 |
| D17 | no time readout | "07:32 / 10:00" under the scrub (span-based) | a 15,000-frame take has ~47 frames per pixel of a phone's bar (operator P11) | — |
| D18 | cDNG playback fps clamped to 1-60 (`PC:621`); the card uses the file's rate (`CLM:153`) | the file's rate everywhere, badge and clock | a clamp desynchronises sound on a take above 60 fps (critic m16) | — |
| D19 | its own Back button only | the browser's Back gesture and button close the viewer, then the browser (`history.pushState` / `popstate`) | a phone's Back would leave the WebUI (F39, operator P7) | — |
| D20 | movies copied to the media root are listed (`CLM:540-556`) | not listed (Core lists folders) | known gap, not built here (critic m17) | — |
| D21 | a ramp take plays by the WAV clock and is cut off (`PC:836-855`) | plays as its timeline, sound off, with one line (§2.6) | F38; U10 for the touch UI once T31 lands | Q30 |
| D22 | a 0-byte frame shows "Decode failed: …" (`CIP:969-974`) | the last picture stays; DROPPED counts the empty frames | a pulled take's tail is 0.8-0.9 s of empty files (F31); U9 brings the touch UI along | — |

### 2.10 What each measurement would change (T46)

| Result | Then |
| --- | --- |
| M1: uncompressed 16-bit 640 w frame ≤ 80 ms per worker on the Pi | defaults stand: 2 workers, play at 640 w |
| M1: > 80 ms | play at 480 w (the touch UI's square layout plays ~459 px wide: 612 × 0.75, r2 §3.1); try 3 workers |
| M1 `--cold`: the read dominates | read only the rows the render needs (~2/3 of the strip at 640 w); M8 tells whether the link is the limit |
| M1: lossless ≤ 4 fps with 2 workers, and M2 shows the touch screen as choppy too | offer O11 (preview track) now; else keep it as an option |
| M3/M14: < 40 small requests/s through Core's server, from the laptop or the phone | ask ahead by one frame only; keep-alive becomes its own task |
| M6: a browser cannot play the s24 WAV | O13: Core serves a 16-bit copy |
| M5: standby comes during passive playback on the touch UI too | T54 adds `user_activity` while playing on the touch UI |
| M7: reading an old take during a take costs no frames | cached thumbnails could be allowed in a take (Q4); the default stays "hold" |
| M9: the Pi's locale is not English | Core writes the month names the touch UI shows (Q15) |
| M10: no `libswscale` on the Pi | T53 starts with `sudo apt install libswscale-dev` (you) |
| M12: the clap is off by more than a frame on the touch screen today, on a lossless take | confirms D15 and T54; with Bluetooth off by > 100 ms: O22 |
| M13: the touch screen's live preview stutters while a browser plays 16-bit | 1 worker by default, or play at 480 w |
| M15: a download during a take costs frames | Q21 stays "refuse" |
| M16: the first take after a review drops more than the baseline | `O_DIRECT` reads instead of the page cache (the writers' way, F24) |
| M17: `/api/media` with a 10-minute take takes > 300 ms warm | the facts cache keys on the folder's mtime alone, and a full rescan only on Refresh |
| M18: a real lossy frame costs as much as lossless | tell yourself lossy plays like lossless; O11 covers both |
| M19: H.264 through the plugin plays < 20 fps or scrubs > 1 s | O12 (`<video>`) for H.264 (Q27) |

---

## 3. The WebUI pane

### 3.1 Shape and parts

- **Container:** a full-screen overlay `#playbackOverlay` built like the WebUI's Settings overlay (`.settings-overlay` +
  a shell of `min(1320px, 100vw − 32px) × (100dvh − 32px)`, radius 32, `rgba(9,9,11,.96)`, `Web:954-988`). Below 720 px it
  goes edge to edge (inset 0, radius 0), because the touch UI's page is the whole screen. It replaces
  `#mediaBrowserOverlay` (`Web:3979-4030`), and the old overlay's wiring in `installInteractions` is replaced in the same
  step (F35; critic B1), or the page script would stop at load.
- **Inside:** the touch UI's two pages, browser and viewer, one at a time, each with the touch UI's title block, top-right
  buttons and one rounded **sheet** (`var(--surface-2)`, border `var(--card-border)`, radius `var(--radius-xl)` = 28).
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
| B4 | Back (← Back; "Cancel" in selection) | `.icon-button.settings-back-button` "Back" / "Cancel"; the browser's Back does the same (D19) | same + D19 |
| B5 | CAPTURE / Clip Mode · Still Mode, accent in still mode | "SHOW / Clips" two-line `.secondary-button` with the `#3fd0ff` accent border the WebUI already uses (`Web:1664-1668`); opens Clips · Stills · Timelapse · Audio; opens on Stills in photo mode | D1 |
| B6 | Refresh Media / "Scanning..." with `refresh.png` | same strings and icon; "Scanning..." now paints (the fetch is async); icon only below 420 px | same |
| B7 | Sheet `#151515` r28, runs off the bottom | `.pb-sheet` (`--surface-2`, r28), runs to the shell's bottom | same |
| B8 | Film icon + "CLIPS" / "STILLS" / "SELECTION" | `/icons/film.png` + same labels; "TIMELAPSE" / "AUDIO" | same + D13 |
| B9 | Count chip "12 ITEMS" / "3 SELECTED" | the WebUI count pill: "12 items", "1 item", "3 selected" | D2 |
| B10 | Sort chip "NEWEST FIRST" / "OLDEST FIRST", accent, toggles | a pill button with the same words and accent; replaces today's `<select>` (`Web:4009`) | same |
| B11 | Remove Selected (red, trash icon) in selection mode | `.danger-button` "Remove Selected" + `delete.png`; beside it `.primary-button` "Download Selected" and `.secondary-button` "Select All" | same + D3 |
| B12 | Status line: "Found 12 clip(s) in /media/RAW.", "No cDNG, ProRes, H.264 or MLV clips found in /media/RAW.", "/media/RAW is not available.", the selection hint | same strings, root from the reply's `media_root`; a hold adds "Playback held: recording. Pictures return when the take ends." | same |
| B13 | Grid: 2 / 3 / 4 columns by layout | CSS grid at the WebUI's breakpoints: < 720 px 2, 720-1119 px 3, ≥ 1120 px 4 | adapted |
| B14 | Card r24 `#181818`, 1 px border | `.pb-card`: `--surface`, `--card-border`, `--radius-lg` (22) | same |
| B15 | 16:9 thumbnail r18, "NO PREVIEW" until ready | `<img draggable="false">` from a blob in a 16:9 box, `--radius-md` (18); "NO PREVIEW" also for a held or unplayable clip; re-queued when the hold clears (operator P17) | same |
| B16 | Duration pill bottom-left ("00:12", "01:02:03", "DNG STILL") | `.badge` with the touch UI's text rule (F22, card rule) on the span duration (D15) | same + D15 |
| B17 | Selection badge top-left (28 px circle; red with ✓ when selected) | same; with a mouse also on hover (D4) | same + D4 |
| B18 | Footer: name (bold 17, elided right), format label ("cDNG clip", "ProRes clip", "H.264 clip", "MLV clip", "Video clip"; "DNG still"), shot date ("28 Oct 2026  14:03", "Shot date unavailable") | same three lines and strings, from Core's `format_label` and `shot_date_text`; below 720 px the name is elided in the **middle** so the counter stays ("cDNG_26…C0007"), as the touch UI's date line already is (`CBP:755`, `CBP:774`; operator P8) | same + phone |
| B19 | Last-opened card lighter | `.pb-card.last` (border 20 % white) | same |
| B20 | Marked card `#241c1f`, red border | `.pb-card.selected`: the `.danger-button` tint and border | same |
| B21 | Press scale 0.985 | `:active { transform: scale(0.985) }` | same |
| B22 | Tap opens; long press (Qt's 800 ms) starts selection; in selection a tap toggles | pointer events, 800 ms, same rules, callout off (D4) | same |
| B23 | "Remove Selected Clips?" dialog: scrim 80 %, card r26, "N clip(s) selected", first name, "+N more" / "This action cannot be undone.", Cancel / Remove Clips | same strings; scrim `rgba(0,0,0,.8)`, card in the shell style; `.secondary-button` / `.danger-button`; the old `window.confirm` is removed from the delete helpers (F36; critic M11), and while Core deletes the button says "Removing… (N files)" and is disabled (operator P11) | same |
| B24 | Delete results in the status line ("Removed X.", "Failed to remove X.") | Core's reply in the status line (Core's own words, e.g. "Stop recording before deleting media.") | adapted |

### 3.3 Map: every element of the touch-UI viewer and its WebUI counterpart

| # | Touch UI element (`CPP`, r2 §3) | WebUI counterpart | Same / adapted |
| --- | --- | --- | --- |
| V1 | "PLAYBACK" + "Clip Viewer"; Back stops (frame 1, paused) and returns | same; the browser's Back too (D19) | same |
| V2 | Preview r24, 16:9, letterboxed on black, previous frame kept while the next loads | `<canvas>` in a 16:9 box (`--radius-lg`); a frame is drawn only once decoded; `touch-action: none` only on the scrub, so the page does not pan while dragging | same |
| V3 | Badges: "25.000 FPS" top-right, "PLAYING" / "PAUSED" bottom-left, "FRAME i / N" bottom-right (1-based; N = every frame file) | `.badge` pills in the same corners, same text; i from `X-Frame-Index` of the frame on screen, N = `frame_count` (0-byte files included, as the touch UI counts); "SINGLE FRAME" for stills (`PC:1196`, `CPP:455`); with O4 the PLAYING badge can read "PLAYING · 7 FPS" | same |
| V4 | No gesture on the picture | none | same |
| V5 | Title row (stacked only): name (bold 27), "cDNG sequence • 250 frames", Info button | same; the info line is Core's `info_line`; a Download icon button sits beside Info (D3) | same + D3 |
| V6 | Scrub bar: rail, fill, handle; press or drag anywhere seeks; playing plays on after the seek (`PC:589-609`) | same look (rail `--surface`, fill `#d7d9de`, handle `#f4f5f7`); pointer capture; one request in flight, the newest position wins (Cinemate's coalescing scrub, r1 §1.5); frames at 640 w while dragging; on release the paused size, and **play on if it was playing** (operator P18); under the bar the time readout (D17) | same + D17 |
| V7 | Remove (red, trash icon) | `.danger-button` "Remove" + `delete.png`, alone on the left as on the touch UI (operator P9) | same |
| V8 | Previous clip / Play-Pause / Next clip, three circles; prev/next disabled at the ends; clip skips, not frame steps | round `.icon-button`s with `previous` / `play` / `pause` / `next` PNGs; same rules (frame steps are O1) | same |
| V9 | HISTOGRAM card, 48 bars, white gradient 0.96 → 0.42, baseline | `<canvas>` card, same drawing; bins from Core's `X-Histogram` (48 values 0-1000; equal to the touch UI's within 1/1000, critic m15) | same |
| V10 | Clip Metadata: CAPTURED, TYPE, RESOLUTION, BIT DEPTH, FRAME RATE, DURATION, FRAMES, CLIP SIZE, PATH; "Unavailable" | the same nine labels and the touch UI's values (`meta`), then SOUND, FORMAT, DROPPED (D16); DURATION is the span (D15) | same + D15, D16 |
| V11 | Split: metadata as a side panel; stacked/compact: Info overlay with Close | split: a `.settings-card` side panel; stacked/compact: a dialog with Close | same |
| V12 | "Remove Clip?" dialog; then the clip at the same index, or the browser if none | same strings and flow | same |
| V13 | Clip change: slide from ±44 px, fade 260 ms, scale 320 ms; prev/next disabled meanwhile | same timings in CSS | same |
| V14 | Status text only when a clip has no frames ("No DNG frames found in X.") | same, with Core's `play_reason` | same |
| V15 | Opens paused on frame 1; loops at the end | same (play-once is O2) | same |
| V16 | Paused frame is a sharper full-size decode | paused: the smallest width in the list that covers the stage's device pixels (≤ 1920) | same |
| V17 | Opening the delete dialog closes the Info overlay | same | same |
| V18 | Standby stops playback | hold card "Standby" with a Wake button | adapted |
| V19 | Sound through `aplay`, no volume control | `<audio>`, the device's own volume; without sound the PLAYING badge stays as is, and SOUND says why | D7 |
| V20 | — (no hold) | the hold card over the picture: `.preview-center-card` with the reason (§4.8), a **Live view** button for `recording` (operator P22) | D6 |
| V21 | — | sound-only item: the stage shows "SOUND ONLY" and the time (operator P6) | D13 |

### 3.4 Map: flow, states and the rest

| Touch UI | WebUI |
| --- | --- |
| Pages browser ↔ player in `Main.qml` Loaders (`Main:580-640`) | two views inside one overlay; `state.pb.page` = `"browser"` / `"viewer"`; each opening pushes a history entry (D19) |
| Folder button greyed in a take (`CamP:3754`) | `mediaBrowserButton` greyed while `snapshot.recording \|\| snapshot.timelapse_active` |
| Hardware `clip_browser` toggles the browser | touch UI only (D14) |
| HDMI window hidden while the browser is up (r2 §6) | not affected: the WebUI does not touch HDMI |
| Audio meter suspended off the camera page (r2 §1.2) | the WebUI's live preview stopped while the overlay is open (F18) |
| Live refresh by a watcher | D5 |
| Scan on every open; thumbnails thrown away | Core's facts cache and LRU; the page keeps the grid and thumbnails (D10) |
| Prev/next in the browser's current sort | prev/next in the browser's current sort **and** filter |
| Still pairs (DNG + JPEG with one stem) shown once; delete removes both | Core's existing still grouping by stem (`Photos/<stem>`, r3 §1.5) and its delete do the same |
| Selection cleared by mode change, sort, Refresh, Back, page change, delete | same events clear it |

### 3.5 Layouts

The browser's width and height choose the touch UI's layout family (`CPP:22-29`, `:306-345`; r2 §3.1), and on a phone the
rows are rearranged, because the touch UI's `square` sizes are for a 720 × 720 screen (r2 §3.1) and do not fit 390 CSS px
(operator P8, PROBABLE arithmetic: the stacked control row needs ~546 px, the header ~600 px):

| Browser | Touch UI family | Viewer shape |
| --- | --- | --- |
| width ≥ 1120 px (laptop, large tablet) | split (`landscape*`) | preview left (height ≤ sheet − 132), scrub and time under it, control row; Clip Metadata panel right, 27 % of the sheet (340-420 px) |
| 720-1119 px | stacked (`square`) at the touch UI's sizes | preview, title row with Info and Download, scrub and time, one row: Remove, transport, histogram; metadata in a dialog |
| < 720 px, portrait (phone) | stacked, at the `landscape_compact` sizes (Remove 100×38, histogram 92×48, `CPP` tokens r2 §3.2) | preview; title row; scrub and time; **row 1** the three transport circles, centred; **row 2** Remove left, histogram right |
| landscape and height < 500 px (phone on its side) | compact (`landscape_compact`) | no title block, no info line; the preview takes the height; one row: Remove, transport, Info icon, histogram |

Browser header below 720 px: two rows, the title block on the first, the buttons right-aligned on the second, Refresh as
an icon. 1120 px is the width at which the WebUI's Settings already drops its sidebar (`Web:2034-2041`), so both overlays
change shape at the same point.

Phone portrait, browser and viewer (text sketch, 390 px):

```
PLAYBACK
Clip Browser
                         [↻] [SHOW ] [← Back]
┌──────────────────────────────────────┐
│ ▣ CLIPS        (NEWEST FIRST) 12 items│
│ Found 12 clip(s) in /media/RAW.      │
│ ┌────────────────┐ ┌────────────────┐│
│ │ ▒▒▒ thumb ▒▒▒  │ │ ▒▒▒ thumb ▒▒▒  ││
│ │ (00:10)        │ │ (01:02)        ││
│ │cDNG_26…C0007   │ │cDNG_26…C0006   ││
│ │cDNG clip       │ │cDNG clip       ││
│ │28 Oct 2026 …   │ │28 Oct 2026 …   ││

PLAYBACK                       [← Back]
Clip Viewer
┌──────────────────────────────────────┐
│ ┌──────────────────────────────────┐ │
│ │                    (25.000 FPS)  │ │
│ │            picture               │ │
│ │ (PAUSED)        (FRAME 1 / 207)  │ │
│ └──────────────────────────────────┘ │
│ cDNG_26-10-28_C0007      [⤓] [ⓘ Info]│
│ cDNG sequence • 207 frames           │
│ ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 00:00 / 00:10                        │
│          (⏮)   ( ▶ )   (⏭)           │
│ [🗑 Remove]              [HISTOGRAM] │
```

Laptop, viewer (split):

```
PLAYBACK                                                                 [← Back]
Clip Viewer
┌───────────────────────────────────────────────────────────┬──────────────────────┐
│ ┌───────────────────────────────────────────────────────┐ │ ⓘ Clip Metadata  [⤓] │
│ │                                        (25.000 FPS)   │ │ cDNG_26-10-28_C0007  │
│ │                     picture                           │ │ CAPTURED   RESOLUTION│
│ │ (PLAYING)                          (FRAME 118 / 207)  │ │ 28 Oct ..  3840 x 2160│
│ └───────────────────────────────────────────────────────┘ │ ...  PATH            │
│ ━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ SOUND  24-bit 48 kHz │
│ 00:05 / 00:10                                             │ FORMAT SDR 12 · LJ   │
│  [🗑 Remove]          (⏮) ( ⏸ ) (⏭)       [HISTOGRAM ▁▃▆▇▅▂] │ DROPPED 43 missing   │
└───────────────────────────────────────────────────────────┴──────────────────────┘
```

Phone traps from the handbook (r4 §6): `100dvh` with a fallback; a definite `max-height` on the preview box; test on a real
phone; no fullscreen button by default (iOS has none for `<canvas>`; O19 adds one where the browser has it). Touch targets
stay ≥ 44 px. The mocked-Chromium gate takes 390 × 844 and 844 × 390 screenshots.

### 3.6 Behaviour

| Topic | Rule |
| --- | --- |
| Open | Folder button (greyed in a take or timelapse) → `history.pushState` → stop `#previewStream` with `removeAttribute("src")` and a `previewPausedForPlayback` flag that the `<img>` error handler and `loadPreviewStream` respect (F18; Cinemate's lesson: `src=''` re-resolves to the page, `cm:4d3bca4`) → `GET /api/media` → render cards → thumbnails for visible cards, 2 in flight (`IntersectionObserver`) |
| Close | Back from the browser, the browser's Back, or Escape → clear the flag → `loadPreviewStream()` (`Web:8597`) restarts the live view with a new nonce |
| Open a clip | the thumbnail queue pauses → `pushState` → `GET /api/media/clip` → paused on the first frame → the paused-size frame (V16) |
| 404 `gone` | "This clip was removed on another screen." and back to the browser (operator P10) |
| 404 stale token (same id) | refetch the list once, then reopen **by id**, never by index (a reused name or a Core restart changed the token, §4.2) |
| Play | audio clock if a WAV plays, else wall clock; the **number** at the clock (§2.6); over a hole or 0-byte frame no request; two lanes at 640 w, asked ahead by the round trip capped at two frames (§2.2); draw the newest decoded frame not later than the clock |
| 503 or rejected fetch | skip that frame; the lane waits one frame period, 500 ms after three in a row; count it (for O4) |
| 409 hold | pause, drop the audio's `src`, show the hold card (§4.8); the poll clears it |
| End | loop to the first frame and keep playing, like the touch UI (`PC:567`) |
| Pause | stop the clock; after 150 ms ask the paused-size frame for the current number |
| Scrub | pointerdown remembers whether it was playing and pauses; each move asks 640 w with one request in flight, the newest position wins; pointerup asks the paused size and plays on if it was playing (P18) |
| Prev / next clip | index ± 1 in the browser's current sort and filter (`Main:426-443`) |
| Remove | dialog → `postDeleteItem` (no `confirm`) → the clip at the same index opens, or the browser if none |
| Download | a confirmation that names the size ("Download cDNG_… (249 GB)? Over Wi-Fi this takes hours; copying the card is faster.") → `<a download>` to the item's existing `download_url` (a folder ZIP, `App:7343-7462`); disabled while `playback_hold` is set |
| Hidden tab | pause; toast "Paused: the tab is in the background." (Cinemate, r1 §1.5). The screen may lock during a long take: the WebUI is plain HTTP, so `navigator.wakeLock` is missing there (F39); it is used where it exists, and O20 covers the rest |
| Hold from the poll | `renderSnapshot` (`Web:9366`) reads `playback_hold` once a second: pause and show the card; when it clears, redraw the current frame, re-queue missing thumbnails and refetch the list, do not resume |
| After a media hold clears | while every frame answers 503, the card says "Waiting for the media to answer…" (operator S2) |
| Keep awake | while playing, `user_activity` every min(20 s, timeout ÷ 3) |
| Keys | Space play/pause in the viewer (`keydown`, `preventDefault`, not in inputs); Escape closes the metadata dialog, then the viewer, then the browser (D12) |
| Library fetch | `fetchMediaLibrary` queues a call that arrives while one is in flight, as `fetchState` does (`Web:10257-10261`), instead of dropping it (`Web:10404-10405`; critic M11) |

### 3.7 Walkthroughs

**A. The last take, with sound, on the laptop.**

| You do | You see | Core does |
| --- | --- | --- |
| Folder button | Clip Browser, newest first, the last take top-left with "00:10", "cDNG clip", "28 Oct 2026  14:03"; the live view stops behind it | `/api/media` from its facts cache; `n=<first>&w=320` per visible card: hold check, slot, decode, cache |
| Click the card | Clip Viewer, paused, "25.000 FPS", "PAUSED", "FRAME 1 / 207"; metadata panel right with SOUND "24-bit 48 kHz stereo", FORMAT "SDR 12-bit · lossless", DROPPED "43 missing · 0 empty" | `/api/media/clip`; `n=0&w=1920` |
| Play | picture at about 25 fps for uncompressed, ~5-8 for lossless (PROBABLE, M1), in time with the sound from the laptop, "PLAYING" | `<audio>` Range requests on `/api/media/file`; frames by number at `w=640`, 2 slots |
| Wait to the end | loops to frame 1 | the second loop comes from the play cache when the frames fit (~250 × 30 KB = 7.5 MB) |
| Back, Back | browser, then the camera page with live view | `/preview.mjpeg?stream=n+1` |

**B. Someone presses record while you watch.** The record button's command opens the yield window at once: the decode in
flight stops after its current chunk, the WAV stream ends at its next 64 KiB, a ZIP download stops. The next frame request
answers 409 `recording`; the picture pauses, sound stops, the card says "Recording", "Recording to media. Press Play when
the take ends.", with Live view. The grid stops loading thumbnails. When the take is cut, `/api/state` waits for the drain
(the card may say "Finishing the take…"), then `playback_hold` is `""`: the card goes, the frame redraws, the list
refetches and the new take appears first. Playback does not restart by itself.

**C. Remove from the viewer.** Remove → "Remove Clip?" → "Remove Clip" → "Removing…" → the next clip at the same index
opens. In a take or while writes drain, Core refuses with its existing words and the dialog shows them.

**D. A 4K SDR 12-bit lossless take shot at 25 fps, 43 frames lost.** "FRAME i / 207" jumps in steps of ~3-5 (PROBABLE:
25 fps wanted, ~5-8 decoded), and the picture stays in time with the sound: the clap at 8 s is on the clap. DURATION
"00:10" (the touch screen says "00:08" until T54). DROPPED "43 missing · 0 empty". With O4 the rate row says "Achieved
6.8 fps · skipped 180".

**E. The card is pulled.** Within ~2 s: the hold card says "Media not available / Media was removed. Insert or mount media
to play clips."; the browser shows "/media/RAW is not available." (touch UI wording). Core: the watcher's snapshot says not
mounted and opens the yield window; routes answer 409 `media` before they read anything. A read already stuck in the
kernel holds its slot until the device times out (R16); after re-insert the card says "Waiting for the media to answer…"
until it returns.

**F. On the phone, portrait.** Two columns of cards, names elided in the middle. The viewer stacks: picture, name with
Download and Info, scrub and time, the three circles, then Remove and the histogram. Info opens the Clip Metadata dialog
with Close. The phone's Back closes the viewer.

**G. A speed-ramped take (once T31 is on the Pi).** 10 s at 25 fps, then 10 s at 50: the card says "00:30"; the viewer
badge "25.000 FPS", one line "Speed ramp 25 → 50 fps: plays as on a 25 fps timeline. The sound is real time, so it is
off.", FRAME RATE "25.000 fps", DURATION "00:30", DROPPED "unknown (speed ramp)". It plays all 750 frames in 30 s, the
50 fps part as slow motion, as your NLE will show it.

**H. The DIT removes the clip the director is watching.** The director's next frame request gets 404 `gone`; the viewer
says "This clip was removed on another screen." and returns to the browser, which refetches.

**Code view of one frame request** (T48): route → `playbackHoldReason()` (409) → `kind`/`id` through
`isSafeMediaRelativeId` / `resolveMediaLibraryPath` (404, `gone` if the folder is missing) → the clip's frame list from the
cache (404 if `n` is outside first..last) → `w` from the list (400) → `v` against the token (404 stale) → cache hit? send it
→ try a decode slot (503) → open with `O_CLOEXEC`, read the tail, then the payload in chunks, asking the yield window and
dropping each chunk from the page cache → render at `w` → histogram → JPEG → cache → 200 with the headers of §4.4.

---

## 4. Core API, data and state

### 4.1 Routes

| Method and path | Answer | Refused | New / changed |
| --- | --- | --- | --- |
| `GET /api/media` | today's list, each clip with the facts of §4.2; top level `held` | never; in a hold it answers from memory | changed (T47) |
| `GET /api/media/clip?kind=folder\|still&id=…` | §4.3 | in a hold: from the cache with `held`, or 409 when not cached; 404 unknown id (`gone` when the folder is missing), 400 missing | new (T47) |
| `GET /api/media/frame?kind=…&id=…&n=NUMBER&w=320\|480\|640\|960\|1280\|1920&v=TOKEN` | `image/jpeg`; headers §4.4 | 409 hold, 503 busy or no JPEG support compiled in, 404, 400 | new (T48) |
| `GET /api/media/file?kind=folder&id=…&name=X.wav` | `audio/wav`; Range → 206 | 409 hold, 404, 416, 400 (not a `.wav`) | new (T51) |
| `GET /api/media/download`, `/download-selected` | today's | + 409 in a hold; the stream stops when a hold starts (Q21) | changed (T50) |
| `POST /api/media/delete`, `/api/media/delete-selected` | today's | + `writing` (F16) | changed (T50) |
| `GET /api/state` | + `"playback_hold":"…"` | | changed (T47) |

Apertar style: the `/api/media/*` family; `kind` + `id` exactly like the download route (`App:7343-7360`); query values
through the existing `queryParameterValue` (URL-decoded, `App:5258`); errors as `errorReply(-1, "…")`, i.e.
`{"ok":false,"error":"…"}` (`App:122-130`), and a small `holdReply(reason, text)` beside it for the 409 body, which adds
`"hold":"recording"` (critic m20); every id through `isSafeMediaRelativeId` / `resolveMediaLibraryPath` (`App:5640`,
`App:5790`), **after** the hold check. No socket command (§2.7).

### 4.2 `/api/media` item: new and fixed fields

```json
{"id":"cDNG_26-10-28_C0007","kind":"folder","category":"clip","type":"cDNG Clip","name":"cDNG_26-10-28_C0007",
 "size_bytes":4150000000,"size_text":"3.9 GB","file_count":208,"frame_count":207,
 "duration_text":"00:10","fps_text":"25 FPS",
 "modified_text":"…","modified_ms":1761660180000,"download_url":"/api/media/download?kind=folder&id=cDNG_26-10-28_C0007",
 "format":"cdng","format_label":"cDNG clip","playable":true,"play_reason":"",
 "fps":25.0,"shot_date_text":"28 Oct 2026  14:03","shot_ms":1761660180000,
 "first_number":0,"last_number":249,"missing_frames":43,"empty_frames":0,"ramp":false,
 "has_audio":true,"token":"9f3c2a17",
 "thumb_url":"/api/media/frame?kind=folder&id=cDNG_26-10-28_C0007&n=0&w=320&v=9f3c2a17"}
```

- `fps_text` and `duration_text` come from the clip's own first frame (the fix of §1.1). `duration_text` uses the touch
  card's text rule (F22) on the **span**, `(last_number − first_number + 1) ÷ fps` (D15). A clip without a FrameRate tag
  uses 24, as the touch UI does (`PC:262`), and says so in the metadata. Old fields keep their names, so nothing else that
  reads the list breaks.
- `frame_count` = every frame file, 0-byte ones included, one per stem (F31; critic m9: a DNG + JPEG timelapse counts each
  frame once, the DNG first). `empty_frames` = 0-byte DNGs. `missing_frames` = span − files (F5; Cinemate's rule, r1 §2.2).
  For T31 ramp takes (numbered by count) `missing_frames` is 0 and the viewer says "unknown (speed ramp)" (R10).
- `shot_ms` sorts the cards: the shot time, then a numeric-aware name order, like the touch UI (`CLM:559-568`).
- `token` = FNV-1a of (folder name, first frame's mtime in ns, its size, the file count, Core's start time). It changes
  when a folder name is reused (F6) and when Core restarts after a rebuild, so no cache can show the wrong picture
  (Cinemate's render-token lesson, r1 §4.2 #7).
- Facts are cached per folder, keyed by (folder mtime, entry count). An unchanged folder costs one `readdir`, not a `stat`
  per file. Whether exFAT updates a folder's mtime on every new file is UNCONFIRMED; the entry count covers it. A
  10-minute take is 15,000 entries per `readdir` (T46 M17).
- In a hold the reply is the last cache plus `"held":"recording"` (or `writing`, `media_test`, `standby`, `media`). If
  the cache is empty (Core started during a take), `items` is empty and the page says "Playback held: recording. Pictures
  return when the take ends."
- `mounted` follows the watcher too (`mediaSnapshot()`), not only the mount table, which keeps a pulled medium listed
  (`App:7874-7876`, r3 G7).
- `.mp4.writing` counts as a container in the scan (T53), so a pulled H.264 take is listed, with its reason (F13).

### 4.3 `/api/media/clip`

```json
{"ok":true,"kind":"folder","id":"cDNG_26-10-28_C0007","name":"cDNG_26-10-28_C0007",
 "format":"cdng","playable":true,"play_reason":"","frame_count":207,
 "first_number":0,"last_number":249,"holes":[[6,1],[12,1],[19,1]],"missing_frames":43,"empty_frames":0,
 "fps":25.0,"fps_fallback":false,"ramp":null,"token":"9f3c2a17","width":3840,"height":2160,"bits":12,
 "compression":"lossless","companded":false,"timecode_start":"14:03:12:05",
 "has_audio":true,"sound_text":"24-bit 48 kHz stereo",
 "audio_url":"/api/media/file?kind=folder&id=cDNG_26-10-28_C0007&name=cDNG_26-10-28_C0007.wav",
 "fps_badge":"25.000 FPS","info_line":"cDNG sequence • 207 frames",
 "meta":{"captured":"28 Oct 2026  14:03","type":"cDNG sequence","resolution":"3840 x 2160","bit_depth":"12-bit",
         "frame_rate":"25.000 fps","duration":"00:10","frames":"207","clip_size":"3.9 GB",
         "path":"/media/RAW/cDNG_26-10-28_C0007"},
 "extra":{"sound":"24-bit 48 kHz stereo","format":"SDR 12-bit · lossless","dropped":"43 missing · 0 empty"}}
```

(The `holes` list is shortened here; this take has 43 one-frame holes.)

- `holes` = `[first number, length]` for every run of numbers never written **and** every run of 0-byte frames, merged
  (HTTP JSON, so the socket's flat-reply rule K9 does not apply). The page needs them to avoid asking for a frame that has
  no picture; `X-Frame-Index` gives the badge.
- `meta` values use the touch UI's formats and values (`PC:121-164`, `PC:1149-1205`): date "dd MMM yyyy  HH:mm" (two
  spaces), "%1 x %2", "%.3f fps", the metadata duration rule (F22) on the span (D15), sizes base 1024 with one decimal below
  100, "Unavailable" when missing; `bit_depth` as the touch UI reports it, "16-bit" for a companded or lossy take (D9). Core
  formats them, so both screens show one answer: Patrik's own precedent when the WebUI and the touch UI disagreed
  (`87011d4`, `6ae70b5`, r4 P4). The date is `strftime("%d %b %Y  %H:%M")`; Core never calls `setlocale`, so the months are
  English (F23). If Q15 says follow the Pi's locale: `newlocale()` + `strftime_l` on this one call, never
  `setlocale(LC_ALL, "")`, which would change number parsing in Core's config files (`sv_SE`: "1,5"; critic m6).
- `extra` holds the three WebUI-only rows (D16). FORMAT: 16-bit → "Clear HDR 16-bit"; 12-bit with a LinearizationTable in
  a `cDNG_3to1_`/`cDNG_5to1_` folder → "12-bit companded · lossy 3:1/5:1" (F3); 12-bit with a table elsewhere → "Clear HDR
  12-bit companded"; 12-bit without → "SDR 12-bit"; then "· uncompressed" or "· lossless" (PROBABLE rule from F3, F4; the
  T47 host test pins the strings). SOUND: the WAV's format, "None", "Not finalised: audio_capture.raw is on the media
  (raw2wav.py makes a WAV)" (`kb:lessons/hardware-log.md:447`, `:457`), or, filled in by the page, "This browser cannot
  play it". DROPPED: "N missing · M empty", "none", or "unknown (speed ramp)".
- `ramp` (only when T31's `fps-ramp.txt` is in the folder and names an applied change): `{"base_fps":25,"max_fps":50,
  "events":[[applied_frame,to_fps],…],"real_duration_text":"00:20"}` (F38). Then DURATION reads "00:30 (00:20 real)".

### 4.4 `/api/media/frame`

- `n` = the frame **number** (from the file name, F5). Core serves the frame with the largest number ≤ `n` that has bytes;
  for stills and unnumbered sequences the number is the position. `n` outside first..last → 404.
- `w` from a list, so the cache stays small: 320 and 480 (cards), 640 and 960 (playing), 1280 and 1920 (paused). The height
  follows the frame's aspect.
- JPEG quality 80 (75 for 320 and 480). RGB → TurboJPEG `tjCompress2` with FASTDCT, libjpeg fallback, like `App:4165-4230`.
  Built without JPEG support (F11), the route answers 503 "JPEG support was not compiled in." (critic m10).
- Headers on 200:

| Header | Value |
| --- | --- |
| `X-Frame-Number` | the number served (≤ `n`) |
| `X-Frame-Index`, `X-Frame-Count` | its 0-based position among the frame files, and their count (the badge's i − 1 and N) |
| `X-Histogram` | 48 integers 0-1000, the touch UI's recipe (F20) |
| `X-Frame-Source` | `cache` or `decode` |
| `X-Decode-Ms` | the decode time, so logs and the page carry values (Cinemate lesson C7, r4 §5.2) |

- `v` is checked against the clip's token; a stale `v` gets 404 `{"ok":false,"error":"The clip changed. Refresh Media."}`;
  a folder that is gone gets 404 `{"ok":false,"error":"This clip was removed.","gone":true}` (operator P10).
- Errors: 409 `{"ok":false,"error":"…","hold":"recording"}`, 503 `{"ok":false,"busy":true}`, 404, 400.

### 4.5 `/api/media/file` (T51)

- Only a `name` ending in `.wav` (any case), with no `/`, `\` or `..`, resolved inside the clip folder, a regular file and no
  symlink (Cinemate's symlink lesson, r1 §2.7).
- `Range: bytes=a-b`, `a-` or `-n` → 206 with `Content-Range` and `Content-Length`; no Range → 200 with `Content-Length`
  and `Accept-Ranges: bytes`; unsatisfiable → 416 with `Content-Range: bytes */size`; several ranges → 200 with the whole
  file. The body is sent in 64 KiB chunks, as `streamFileToClient` does (`App:6333-6348`, which uses `std::ifstream`); the
  new streamer uses `pread` from an `O_CLOEXEC` descriptor, asks the yield window and the hold between chunks, and drops
  what it sent from the page cache.
- `Content-Length` is always sent, so a cut stream is visible (r3 §3.3).

### 4.6 State

| Field | Where | Meaning |
| --- | --- | --- |
| `playback_hold` | `buildWebStateJson` (`App:7857-8224`), next to `media_alive`, from `playbackHoldFor()` over the values the builder already read | §2.7. The WebUI polls it; socket clients already get `recording` and `media` events |

Not persisted, no settings file, no new event. Sort, filter and the last-opened clip live in the page; `localStorage` is not
used for them (the touch UI does not keep them either, r2 §2.4). O22's per-device A/V offset would be the one
`localStorage` value, a per-viewer convenience.

### 4.7 Caches, slots, priorities

| Cache | Key | Size | Lives |
| --- | --- | --- | --- |
| Folder facts | folder name → (mtime, entry count) | one entry per take | Core process; a file-scope object in `App`'s anonymous namespace, not a member in `App.hpp` (critic B2), filled outside its mutex |
| Frame list per clip | folder → numbers, names, sizes, holes | last 8 opened clips | Core process |
| Thumbnail JPEGs | (id, n, w, token), w ≤ 480 | 8 MB | Core process; survives holds |
| Play and paused JPEGs | (id, n, w, token), w ≥ 640 | 24 MB | Core process; survives holds |
| Thumbnails in the page | the thumbnail URL (it carries the token) | while the page is open | the browser tab |

Slots: `APERTAR_PLAYBACK_WORKERS` (default 2) `DecodeSlot`s, each with its own sample, scratch and RGB buffers, taken with
`try_lock` without waiting; none free → 503 (Cinemate's "refuse rather than queue", r1 §2.5; `sketch/src/playback/DecodeSlots.hpp`,
tested). Decoding runs on the HTTP client thread that holds the slot, at nice 10. A cache hit needs no slot. The media
watcher trims idle slots (§2.7). A movie decoder has its own mutex: a second request for the same movie gets 503, so
frames are asked one at a time and in order (critic M6, operator P12).

### 4.8 Refusals and messages

| When | Kind | Text |
| --- | --- | --- |
| hold `recording` | 409 + hold card with **Live view** | title "Recording", body "Recording to media. Press Play when the take ends." (operator P14: no promise of a resume that is not built; Core's word is "media") |
| hold `recording`, poll slow after the cut | card | "Finishing the take…" |
| hold `writing` | 409 + card | "Writing to media", "Finishing the last take. Press Play when it is done." |
| hold `media_test` | 409 + card | "Media test", "A media speed test is running. Press Play when it ends." |
| hold `standby` | 409 + card with a **Wake** button (`wake`) | "Standby", "Wake the camera to play clips." |
| hold `media` | 409 + card | "Media not available", "Media was removed. Insert or mount media to play clips." (after `App:9426`) |
| after a media hold, every frame 503 | card | "Waiting for the media to answer…" |
| decoder busy, connection closed | 503 / network error | nothing shown; the frame is skipped (counted for O4) |
| stale token | 404 | "The clip changed. Refresh Media." |
| clip gone | 404 `gone` | "This clip was removed on another screen." |
| no frames | `play_reason` | "No DNG frames found in cDNG_…." (touch UI wording, r2 Appendix B) |
| all frames empty | `play_reason` | "Every frame of this take is empty (0 bytes); the media was probably pulled." |
| MLV not finalized | `play_reason` | "MLV is not finalized or its frame count is invalid." (`MLR:176-177`) |
| H.264 not finalized (in a take, or after a pull) | `play_reason` | "H.264 take was not finalized." (critic m8) |
| ProRes without index | `play_reason` | "ProRes take was interrupted; it has no index." |
| format not built yet | `play_reason` | "MLV playback arrives with T52." / "ProRes and H.264 playback arrive with T53." |
| plugin missing | `play_reason` | "Video playback decoder unavailable. Build apertar-video-libav (libswscale-dev required)." (the touch UI's full string, `VP:35`) |
| no JPEG support | 503 | "JPEG support was not compiled in." |
| decode error | the frame is the touch UI's placeholder | "Decode failed: <reader error>" (`CIP:969-974`) |
| speed ramp | viewer line | "Speed ramp 25 → 50 fps: plays as on a 25 fps timeline. The sound is real time, so it is off." |
| delete in a take | existing | "Stop recording before deleting media." (`App:7664`) |
| delete while writing | new | "Wait for the current capture to finish writing to media." (`App:9489` words) |
| record while a delete runs (Q23) | new, `record_start` | "Deleting media. One moment." |
| download in a take (Q21) | 409 | "Recording. Downloads wait until the take ends." |
| download cut by a take | page toast | "Download stopped: recording started. Start it again after the take." |
| WAV refused by the browser | SOUND row + toast | "This browser cannot play the take's WAV. Playing without sound." |
| hidden tab | toast | "Paused: the tab is in the background." |

### 4.9 Safety

- Ids go through the existing validators (`App:5640`, `App:5690`, `App:5790`). Frame files are never named by the client:
  `n` indexes Core's own frame list. Names go into the page with `textContent` (Cinemate's stored-XSS lesson, r1 §2.7).
- A reader bug must not take Core down. `readDngInfo` checks every offset against the file size **and** caps the frame at
  4096 × 3072 (F37) and checks that the strip holds every row, before anything is allocated (critic M9; 20 size lies refused,
  §2.3); the web server catches exceptions per client thread (`WS:279-284`), not crashes; the T48 gate re-runs the fuzz,
  size lies included.
- No auth, as today: keep port 8000 on a trusted network (r4 K21). Download stays apart from Remove (D3).

### 4.10 Ways it could look half-done, and why they cannot

| State | What you would see | Why it is safe |
| --- | --- | --- |
| A browser tab from before a Core update | the old page; it knows no new routes | the page is compiled into Core and `/` is `no-store` (F8), so a reload gives the new page; the token changes with Core's start time, so old URLs get 404 "Refresh Media" |
| T47 built, T48 not | the old list overlay with correct FPS and duration | T49 replaces the overlay only after T48 serves frames |
| T49 built, T50 not | cards with thumbnails; a tap shows "The Clip Viewer arrives with T50." | the tap handler calls a stub |
| T50 built, T51 not | the viewer plays silently, on the wall clock; SOUND says "Arrives with T51" | `has_audio` is ignored until T51 |
| T52 / T53 not built | MLV and movie cards show "NO PREVIEW"; the viewer shows the `play_reason` | `playable:false` with the tutorial's name |
| T54 not built | the touch screen shows a shorter DURATION on lossless takes, and plays on in a take | D15, D22; T54 is recommended, not required |

---

## 5. The touch UI: what changes

**Required: nothing for T46-T53.** Patrik's decision makes the touch UI the model; the WebUI copies it.

**Recommended: T54, "the touch UI yields to a take and keeps time"** (Q22, default yes; operator P4, P1). The camera's own
screen is where "review, then roll" happens most, and today the take records while its player reads and decodes from the
card (§1.2). With T54 "recording wins" holds on both screens, and both show the same time:

| # | Change | Where (`d8098d0`, search string) | Size |
| --- | --- | --- | --- |
| U2 | Stop playback when a take starts; ignore the hardware `clip_browser` action in a take; Remove disabled in a take; the player shows the WebUI's hold text; `user_activity` while playing (if M5 says so) | `Main:511` `onRecordingChanged: {`; `Main:319` `if (action === "clip_browser") {`; `PC:542` `void PlaybackController::stop()` | ~40 |
| U9 | The number clock (time → frame number → the frame at or before it, holding over holes and 0-byte frames) and the span DURATION | `PC:827` `void PlaybackController::updateFrameFromPlaybackClock()`, `PC:849` `const int newFrameIndex = qBound(0,`; `PC:1200` `: formatDurationText(m_frameFiles.size(), m_fps));`; `CLM:147` `QString durationTextForClip(int frameCount, double fps)` | ~50 |

Optional fixes, each small, each its own later tutorial:

| # | Change | Why | Size |
| --- | --- | --- | --- |
| U1 | "1 item"; "Stills" wording in the still-mode dialog | wording bugs (r2 §10 #4) | ~5 lines |
| U3 | Delete through Core (`POST /api/media/delete`) instead of `removeClip` | one gate for every delete; the touch UI's delete has no recording check (`CLM:382-441`) | ~40 |
| U4 | Card thumbnails from Core (`http://127.0.0.1:8000/api/media/frame?…&w=320`) | one cache, faster revisits; today every visit decodes every card again (r2 §9 #2) | ~10 |
| U5 | BIT DEPTH from tag 258, on both screens at once | the file is the witness; both screens then say "12-bit" | ~10 + one Core string |
| U6 | Histogram sampling across all four CFA sites, in both copies at once (F21) | today 4K histograms show one colour channel (PROBABLE) | ~5 + the parity test |
| U7 | Read only the DNG tail for the frame rate when scanning (today `readAll` of the first DNG per take, `DD:1530`) | the touch browser's scan time | ~20 |
| U8 | Later: the touch UI takes its clip list and facts from `/api/media` | one truth for both screens | ~150 |
| U10 | Ramp takes as their timeline, sound off (once T31 lands) | the same as D21 on the touch screen | ~20 |
| U11 | A histogram in stops, on both screens (O18) | a Clear HDR 16-bit frame is a spike at the left of 48 linear bins (PROBABLE, operator P15) | ~30 + parity |

---

## 6. Implementation plan, file by file

Order = build order. Lines are at `eb9cc39` / `d8098d0`; **use the search string**, lines move (and the controls project,
T36-T45, edits the same files first). Every search string below occurs once in its file at that commit (checked here),
except where a row says otherwise. Risk: **low** = checkable on the host (a header with its test, `ApertarCoreApp.cpp`
with `g++ -fsyntax-only`, the page with `node --check` and a mocked Chromium); **medium** = changes what an existing screen
or route does. No row is high risk: **no change in `CameraController.cpp`, in any writer, or in the web server's header
code.**

### T47: Core knows its clips

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 47.1 | new `src/playback/DngTags.hpp` | | the sketch's reader part 1: `DngInfo`, tail read, IFD parse, `readDngInfo` with the 4096 × 3072 cap and the strip check before any allocation, `openDngFrame` (`O_CLOEXEC`) / `closeDngFrame` (`POSIX_FADV_DONTNEED`). 326 lines, no liblj92 (critic B2, M4, M9) | low (host test) |
| 47.2 | new `src/playback/ClipFrames.hpp` | | frame numbers from the names, holes, 0-byte frames, one frame per stem (DNG first), `numberAtTime`, `positionAtNumber`, `pictureAtPosition`. 159 lines (critic M1, M7, m9) | low (host test) |
| 47.3 | new `src/playback/PlaybackHold.hpp` | | `HoldSignals`, `playbackHoldFor()`, `PlaybackYield` (extend-only window). 91 lines (critic M8) | low (host test) |
| 47.4 | new `src/playback/ClipProbe.hpp` | | `ClipFacts` (fps, span, holes, FORMAT and DROPPED text, `ramp` from `fps-ramp.txt` when present), `ClipFactsCache` (mutex inside; a scan runs outside it and swaps in, critic m14), `clipToken`; the touch UI's formatters: shot date, card duration, metadata duration, size base 1024, "%.3f fps", type labels, `info_line`, `meta` (each with a comment naming its `CLM` / `PC` lines) | low |
| 47.5 | KB `working/tools/playback/clip_probe_test.cpp` | | frames from Core's encoder with a hole, a 0-byte file, a DNG + JPEG pair, a `cDNG_3to1_` folder and an `fps-ramp.txt`; checks every fact and every string; the date by its format string `%d %b %Y  %H:%M`, not by a comment (critic m6) | low |
| 47.6 | `App.hpp:105`, `App.hpp:140` | `std::string mediaGateError() const;` and `std::atomic<int64_t> lastUserActivityMs_{0};` | add `std::string playbackHoldReason() const;`, `bool mediaGateBypassed() const;`; add `std::atomic<int64_t> playbackYieldUntilMs_{0};`, `std::atomic<int> playbackYieldReason_{0};`, `std::atomic<bool> mediaDeleteActive_{false};` (Q23). **No cache member**: the facts cache is a file-scope object in `App`'s anonymous namespace, so `App.hpp`'s users do not rebuild against the reader (critic B2) | low |
| 47.7 | after `App:9413-9440` | `std::string ApertarCoreApp::mediaGateError() const` | `mediaGateBypassed()` (the two early returns of F15, shared); `playbackHoldReason()`: one read of each signal into `HoldSignals`, then `playbackHoldFor()` | low |
| 47.8 | `App:9483` | `std::string ApertarCoreApp::handleCommand(const ControlCommand &command)` | right after the command lock (`App:9485`): open the yield window for `record_start`, `capture_photo`, `timelapse_start` (`recording`), `run_media_speed_test` (`media_test`), `enter_standby` (`standby`), `eject_media`, `format_media` (`media`). The critic's search string `std::lock_guard<std::mutex> commandLock(commandMutex_);` occurs twice (`App:9355`, `App:9485`), so this row uses the function line | low |
| 47.9 | `App:9347`, `App:9383` | `const bool lost = havePrevious && previous.mounted() &&` and `mediaWatcherCv_.wait_for(lock, std::chrono::milliseconds(camera_.isRecording() ? 250 : 1000),` | on `lost`: open the window (`media`); before the wait: extend it by 1.5 s while `playbackHoldReason()` is not empty | low |
| 47.10 | `App:5609` | `struct MediaLibraryItem` | the §4.2 fields | low |
| 47.11 | `App:5926` | `std::string wavDurationTextForFile(const std::filesystem::path &path)` | split out `wavFormatForFile` (rate, bits, channels, data bytes) under the text function: one RIFF parser (critic m7) | low |
| 47.12 | `App:6422`, `App:6492` | `std::vector<MediaLibraryItem> discoverMediaLibraryItems(` and `: durationTextForFrameCount(stats.frameCount, fps);` | take the facts cache instead of `fps`; facts from `ClipProbe`; `fps_text` and the span `duration_text` from the clip | low |
| 47.13 | `App:7819` | `std::string ApertarCoreApp::buildMediaLibraryJson() const` | the new fields; `held`; `mounted` also from the watcher (§4.2); answer from the cache in a hold | low |
| 47.14 | after `App:7307-7312` | `if (request.method == "GET" && request.path == "/api/media") {` | route `/api/media/clip`: the hold first (from the cache with `held`, or 409; critic M2, m19), then the validators, then `buildClipInfoJson(kind, id)`; `gone` when the folder is missing | low |
| 47.15 | `App:7857`, `App:8071` | `std::string ApertarCoreApp::buildWebStateJson() const` and `<< ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")` | `playbackHoldFor()` over the values the builder already read (`App:7859-7870`) plus the yield window and the speed-test flag; `<< ",\"playback_hold\":\"" << holdName(...) << "\""` | low |

### T48: Core draws a frame

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 48.1 | new `third_party/liblj92/` | | `cp ~/ApertarUI/third_party/liblj92/{lj92.c,lj92.h,LICENSE,README.apertar.md}`; `cmp` each | low |
| 48.2 | `CMake:6`, `CMake:76` | `    LANGUAGES CXX`; `    src/cdng/LosslessJpegEncoder.cpp` | `LANGUAGES C CXX`; add `src/playback/PlaybackFrames.cpp` and `third_party/liblj92/lj92.c`; include dir `third_party/liblj92`; the target's `-Wall -Wextra -Wpedantic` and Release `-mtune=native` (`CMake:175-188`) also reach `lj92.c`, which is warning-free under them (critic m11); re-run cmake (r4 K6) | low |
| 48.3 | new `src/playback/DngFrameReader.hpp` | | the sketch's part 2: `readDngSamples` in chunks of rows / one tile at a time, `ReadOptions{stop, chunkRows, dropPages}`, `ReadStatus{Ok, Failed, Stopped}`, LJ92 tiles, LinearizationTable (with the m18 comment). 125 lines (critic m2, M4, M8) | low (host test) |
| 48.4 | new `src/playback/RawRender.hpp` | | the touch UI's look and histogram (sketch, 226 lines) | low (parity test) |
| 48.5 | new `src/playback/DecodeSlots.hpp` | | slots that own their buffers, `tryTake`, `trimIdle` (sketch, 115 lines; critic M5) | low (host test) |
| 48.6 | new `src/playback/PlaybackFrames.hpp/.cpp` | | `frameJpeg(dir, n, w, token, out, headers)`: the frame at or before `n`, the two JPEG caches (8 + 24 MB), a slot, the reader with `stop` = the yield window, render, histogram, RGB → JPEG (TurboJPEG or libjpeg, as `App:4165-4230`), JPEG stills through TurboJPEG scaled decode, nice 10; built out with `APERTARCORE_HAS_JPEG=0` (503, critic m10) | low (host-compilable) |
| 48.7 | `WS:70` | `case 503: return "Service Unavailable";` | add 206 "Partial Content", 416 "Range Not Satisfiable", and 409 "Conflict" unless controls T38 already added it (F29) | low |
| 48.8 | after the T47 route | `request.path == "/api/media/clip"` | route `/api/media/frame`: the hold, the validators, `n`, `w`, `v`, cache, slot (503), headers (§4.4); `holdReply(reason, text)` beside `errorReply` (`App:122`, critic m20) | low |
| 48.9 | `App:9383` | `mediaWatcherCv_.wait_for(lock, std::chrono::milliseconds(camera_.isRecording() ? 250 : 1000),` | before the wait: `slots.trimIdle(now, 30000, hold)` (critic M5: no new thread) | low |
| 48.10 | KB `working/tools/playback/hostcheck-core.sh` (from `t34/hostcheck-core.sh`) | | add `-I$C/third_party/liblj92`, and `src/playback/PlaybackFrames.cpp` and `src/web/WebServer.cpp` to its file list (critic B2) | low |

### T49: WebUI Clip Browser

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 49.1 | `Web:1137` (the overlay CSS `Web:1122-1432`) | `.media-browser-overlay.hidden {` | `.pb-*` rules: overlay shell, title, top buttons (two rows below 720 px), sheet, chips, status, grid, card, thumb (`-webkit-touch-callout: none; user-select: none`), duration pill, select badge, dialog; breakpoints 1120 / 720 / 420 | low |
| 49.2 | `Web:3979-4030` | `<div class="media-browser-overlay hidden" id="mediaBrowserOverlay">` | replace with `#playbackOverlay`: title block, Refresh / Show / Back, sheet head, chips, status, grid, Remove dialog, the empty viewer container (T50) | medium (today's browser goes) |
| 49.3 | `Web:11397-11411`, `Web:11610-11613` | `document.getElementById("closeMediaBrowserButton").addEventListener` and `document.getElementById("mediaBrowserOverlay").addEventListener("click"` | **critic B1**: remove the old overlay's wiring (seven ids, the filter buttons and the overlay click) and wire the new overlay's buttons; keep `mediaBrowserButton` (`Web:11396`); add `popstate` → the Back handler (D19). Without this row the page script stops at load: no live view, no state poll | medium |
| 49.4 | `Web:4246` | `mediaSelection: new Set(),` | `pb: {page, filter, sort, selecting, lastOpenedId, thumbs, …}` | low |
| 49.5 | `Web:6176` | `function setMediaBrowserOpen(open) {` | toggle `#playbackOverlay` (today `#mediaBrowserOverlay` with no null check, `Web:6181`); `history.pushState`; stop and restart the live view (§3.6); open on the browser page, filter from `photo_mode_enabled` (D1) | low |
| 49.6 | `Web:8616` | `state.previewRetryTimer = window.setTimeout(loadPreviewStream, 1500);` | no retry while `previewPausedForPlayback` | low |
| 49.7 | `Web:7707` | `function renderMediaLibrary(payload) {` | build cards instead of rows; `buildClipCard`, the status strings, "1 item", middle elide below 720 px; sort by `shot_ms` in `sortedMediaItems` (`Web:7596`); rewrite or delete `setMediaBrowserFilter` (`Web:7579`), `setMediaBrowserSort` (`Web:7588`) and `updateMediaSelectionControls` (`Web:7649`), which look up the old ids and would silently do nothing | medium |
| 49.8 | `Web:10403`, `Web:10422`, `Web:10468` | `async function fetchMediaLibrary(silent) {`, `async function deleteMediaLibraryItem(item) {`, `async function deleteSelectedMediaItems() {` | `fetchMediaLibrary` queues a call that arrives in flight, as `fetchState` does (`Web:10257-10261`); the delete helpers become `postDeleteItem` / `postDeleteSelected` with no `window.confirm` (`Web:10427`, `Web:10476`; critic M11) and "Removing…"; thumbnail queue (2 in flight, `IntersectionObserver`, blobs kept, re-queued when a hold clears); long press 800 ms; hover badge; Remove Selected dialog; Download Selected → `downloadSelectedMediaItems` (`Web:10446`) after the size confirmation; Select All | low |
| 49.9 | `Web:2447`, `Web:9366` | `<button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">` and `function renderSnapshot(snapshot) {` | disabled while `snapshot.recording \|\| snapshot.timelapse_active` (critic m5) | low |

### T50: WebUI Clip Viewer; downloads and deletes yield

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 50.1 | the T49 CSS block | `.pb-card {` | viewer rules: stage, badges, title row, scrub (`touch-action: none`), time readout, transport, histogram card, metadata panel and dialog, hold card; split / stacked / phone / compact queries | low |
| 50.2 | inside `#playbackOverlay` | `id="pbViewer"` | the viewer markup (§3.3): Download icon in the title row, Remove alone on the left, the hold card with Live view and Wake | low |
| 50.3 | after the T49 JS | `function buildClipCard(` | `openClip`, `fetchClipInfo`, the clock from `sketch/page/playclock.js` (`clipTimeline`, `numberAtTime`, `shownNumber`, `lookAheadSeconds`, `laneAfter`, `makeAudioClock`, `scrubEnd`, `keepAwakeIntervalMs`, `middleElide`, `HOLD_TEXT`), `requestFrame` (fetch → `createImageBitmap`, headers), `drawFrame`, `drawHistogram`, `playClip`, `pauseClip`, `installScrub`, `stepClip`, `showClipMetadata` (nine + three rows), `removeCurrentClip`, `downloadCurrentClip`, the ramp line | low |
| 50.4 | `Web:9366` | `function renderSnapshot(snapshot) {` | `applyPlaybackHold(snapshot)`; when `playback_hold` returns to `""`: refetch the list, re-queue thumbnails, redraw (operator P17); "Finishing the take…"; Download disabled in a hold | low |
| 50.5 | `Web:11558` | `document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});` | `user_activity` every min(20 s, timeout ÷ 3) while playing; pause on `visibilitychange`; `navigator.wakeLock` where it exists | low |
| 50.6 | `Web:11620` | `if (event.key === "Escape" && state.mediaBrowserOpen)` | Escape: metadata dialog, then viewer, then browser; Space play/pause on `keydown` with `preventDefault`, not in inputs | low |
| 50.7 | `App:7649`, `App:7721` | `if (request.method == "POST" && request.path == "/api/media/delete") {` and `…/delete-selected") {` | add `camera_.mediaWritesPending()` to the first recording gate after each (the gate's own text occurs three times, `App:7660`, `:7732`, `:9085`, so search the route). If Q23: `mediaDeleteActive_` set around `remove_all` (`App:7683`) and the selected loop, and `record_start` refused with "Deleting media. One moment." beside the writes-pending refusal (`App:9487-9489`) | low; Q23 part medium (a record gate) |
| 50.8 | `App:7343`, `App:7464` | `if (request.method == "GET" && request.path == "/api/media/download") {` and `…/download-selected") {` | Q21: `holdReply` 409 at the start in a hold; the stream writers capture `this` and pass a stop callback (the yield window) | medium (changes today's downloads) |
| 50.9 | `App:6355`, `App:6410` | `void streamZipArchiveToClient(int clientFd,` and `const ssize_t bytesRead = ::read(pipeFds[0], buffer.data(), buffer.size());` | a `stop` parameter checked before each chunk; on stop: close the pipe, `kill(child, SIGTERM)`, `waitpid`; the same parameter in `streamFileToClient` (`App:6333`) | low |

### T51: Sound

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 51.1 | after `App:6333` | `void streamFileToClient(int clientFd, const std::filesystem::path &path)` | `streamFileRangeToClient(fd, path, first, last, stop)`: `pread` from an `O_CLOEXEC` descriptor, 64 KiB chunks, the stop callback between chunks, DONTNEED behind it | low |
| 51.2 | after the frame route | `request.path == "/api/media/frame"` | `/api/media/file`: name rules, hold, Range parse, 200 / 206 / 416 | low |
| 51.3 | viewer JS | `function playClip(` | `<audio preload="none">`, the interpolated audio clock, seek on scrub, `removeAttribute("src")` + `load()` on a hold, error → SOUND row + toast; sound-only items ("SOUND ONLY") | low |

### T52: MLV · T53: ProRes and H.264 · T54: the touch UI

| # | File | Change | Risk |
| --- | --- | --- | --- |
| 52.1 | new `src/playback/MlvFrameReader.hpp` | named copy of the `MLR:153-278` rules: header, block walk to the first `VIDF`, frame index (one pass over block headers, cached) **with each VIDF's frame number** (`Mlv:1027`), 12-bit unpack, WBAL / DEBG-APCM / EXPO; reads in chunks with the stop callback and DONTNEED | low (host test with Core's `MlvEncoder`) |
| 52.2 | `RawRender.hpp` | the ISP path (`CIP:655-662`): clip × common gain, CCM, sRGB OETF | low (parity test against `MlvReader`) |
| 52.3 | `ClipProbe.hpp`, `PlaybackFrames.cpp` | MLV facts and frames; O21 (recovered frames of an unfinalised MLV) only if you say yes (Q26) | low |
| 53.1 | new `src/playback/VideoPlaybackApi.h`, `src/playback/VideoPlaybackLibav.cpp` | `cp` from `~/ApertarUI/src/`; `cmp` each | low |
| 53.2 | `CMake:140`, `CMake:195` | in `if(LIBAV_FOUND)`: `pkg_check_modules(SWSCALE QUIET IMPORTED_TARGET libswscale)`; `add_library(apertar-video-libav MODULE src/playback/VideoPlaybackLibav.cpp)` linked to LIBAV + SWSCALE, as `UCMake:136-146`; after `install(TARGETS apertar-prores-libav LIBRARY DESTINATION lib/apertar-core)`: the same for `apertar-video-libav` (critic M6) | low |
| 53.3 | new `src/playback/VideoFrames.hpp/.cpp` | `dlopen` with `H264C:17-31`'s order: `APERTAR_VIDEO_PLAYBACK_PLUGIN`, next to the binary, `/home/pi/ApertarCore-build/`, the bare name; `H264C:105`'s flags; ABI `version == 2`; one decoder per movie **with its own mutex** (a second request gets 503, so frames come one at a time and in order); opened after `setpriority`, so libav's 4 threads run at nice 10; closed by the idle trim; BGRA → JPEG (critic M6, operator P12) | low |
| 53.4 | `ClipProbe.hpp`; `App:5819` `bool hasClipContainerExtension(const std::filesystem::path &path)` | facts from the plugin's `probe`; `.mp4.writing` counts as a container (F13, critic m8), "H.264 take was not finalized."; ProRes without `moov` | low |
| 54.1 | `Main:511` `onRecordingChanged: {` | `if (cameraPage.recording && playbackController.playing) playbackController.togglePlayback()`; the player shows the WebUI's hold text while recording | low (touch UI rebuild) |
| 54.2 | `Main:319` `if (action === "clip_browser") {` | ignore the action while `cameraPage.recording` | low |
| 54.3 | `CPP:1030`, `CPP:1359` (the two Remove buttons; `text: "Remove"` occurs twice, so search each layout) | `enabled: !recording` | low |
| 54.4 | `PC:696-706`, `PC:827`, `PC:849` `const int newFrameIndex = qBound(0,` | `loadClip` keeps each frame's number (from the name) and size; `updateFrameFromPlaybackClock` maps ms → number → the position at or before it, holding over holes and 0-byte frames (U9) | low |
| 54.5 | `PC:1200` `: formatDurationText(m_frameFiles.size(), m_fps));`; `CLM:534` `clip.durationText = durationTextForClip(clip.frameCount, detectedFps);` | DURATION and the card's pill from the span | low |
| 54.6 | KB `working/tools/playback/parity/` | add the clock map and the duration rule to the parity test, both copies | low |

### Size (PROBABLE, counted as the T34 design counted)

| Part | Lines | Of which in the sketch | Checked before the Pi |
| --- | --- | --- | --- |
| T47 | ~800 | `DngTags` 326, `ClipFrames` 159, `PlaybackHold` 91 | `v2_test`, `g++ -fsyntax-only` with the headers in App (0 diagnostics) |
| T48 | ~800 | `DngFrameReader` 125, `RawRender` 226, `DecodeSlots` 115 | round trip, sizes, parity, fuzz with size lies, syntax |
| T49 | ~500 | — | `node --check`, mocked Chromium (no `pageerror` at load, `#previewStream` has a `src`) |
| T50 | ~950 | `playclock.js` 118 | `playclock_test.js`, `node --check`, mocked Chromium at 390 × 844, 844 × 390, 1440 × 900 |
| T51 | ~220 | — | syntax; `curl` with Range on the Pi |
| T52 | ~320 | — | host test with `MlvEncoder` |
| T53 | ~220 (the two copied files, 253 lines, are not counted: you copy them) | — | syntax; the Pi |
| T54 | ~110 | — | the touch UI builds on the host (Qt 6.4.2); parity test |
| **Total** | **~3,900** | **~1,150** | nothing waits for the Pi to compile except the CMake runs |

---

## 7. Tutorial outlines (KB format)

Each note: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T4x <topic>.md`, frontmatter as `kb:tutorials/README.md`
(`datum`, `kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext`, `typ: digital anteckning`), sections 0-9, numbered steps,
one **Check** per step, a `%% tutor` block, the tags `#CINEMATE` `#APERTAR`. Section 6 is "Commit" (house rule: nothing is
pushed). Reading assignments name lines at `eb9cc39` / `d8098d0`; run `tutorial.py refs T4x` on the Pi first (lines move,
and the controls tutorials edit the same files). A pipe inside a check is written `|` with no spaces (F28).

### T46. Measure first: what a playback frame costs on this Pi

- **You will learn**: what a 4K frame costs to read, decode and draw on your Pi; how fast and how in-sync the touch screen
  plays today; how Core's server behaves with many small requests from the laptop and the phone; what your browsers play.
  **Risk**: none to the camera (read-only; M5 changes one setting that you restore; M7, M12, M15 and M16 record takes).
  **Time**: 2 h (M1-M10), plus 1 h for the recording ones.
- §1: the WebUI list shows the camera's FPS for every take (`curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`).
- §3: M1-M19 of §8, each with a prediction. §4: none. §5: the result table goes into `lessons/hardware-log.md` after you
  confirm the reading (r4 K15).

### T47. Core knows its clips: per-clip facts from the files

- **You will learn**: (1) how a DNG is laid out and why its tags cost one small read; (2) why a fact about a take must come
  from the take ("the file is the witness"): its own FPS, its frame numbers, its holes; (3) why sound time maps to a frame
  **number**, and what the touch UI's n-th-file rule does on a lossless take; (4) one pure rule for "may playback read
  now", and a lock-free window that stops a read before a take's first frame; (5) why it is a route and not a command (the
  command lock). **Risk**: Core rebuild and restart; the list's FPS and duration text change. Undo: `git revert`.
  **Time**: 2 × 2 h.
- §2 reading: `Cdng:1384-1392`, `Cdng:1522-1560`, `IFD:113-125`, `CC:3780-3787`, `Audio:367-385`, `Audio:606-626`,
  `App:6422-6497`, `App:7819-7855`, `App:9483-9500`, `CC:9785-9798`, `PC:827-857`, `PC:1149-1205`, `CLM:147-169`.
- §3 find it yourself: 3.1 `tail -c 1600 <first.dng> | xxd | head` (prediction: the tag directory); 3.2 why does the list
  say 25 for a 50 fps take (`App:6493`); 3.3 `ls <lossless take> | head -12` (prediction: a number missing every 5-9);
  3.4 at 5 s into that take, which file does the touch UI show, and which frame did the sound record (`PC:849-851`,
  `CC:3780-3787`)?; 3.5 what would a slow folder read do inside `handleCommand`?

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | reader part 1 (47.1) | `grep -c 'inline bool readDngInfo' src/playback/DngTags.hpp` → 1 |
| 4.2 | frame list (47.2) | `grep -c 'inline FrameList listFrames' src/playback/ClipFrames.hpp` → 1 |
| 4.3 | hold rule and window (47.3) | `grep -c 'inline Hold playbackHoldFor' src/playback/PlaybackHold.hpp` → 1 |
| 4.4 | facts and formatters (47.4) | `grep -c '%d %b %Y  %H:%M' src/playback/ClipProbe.hpp` → 1 |
| 4.5 | host test (47.5), built and run on the Pi | `./clip_probe_test` ends `all ok` |
| 4.6 | `playbackHoldReason`, the window (47.6-47.9) | `grep -c 'std::string ApertarCoreApp::playbackHoldReason' src/ApertarCoreApp.cpp` → 1 |
| 4.7 | WAV parser, item fields, scan, cache (47.10-47.12) | `grep -c 'probeClipFolder(' src/ApertarCoreApp.cpp` → 1 or more |
| 4.8 | JSON (47.13) | `grep -c 'shot_date_text' src/ApertarCoreApp.cpp` → 1 |
| 4.9 | route (47.14) | `grep -c 'request.path == "/api/media/clip"' src/ApertarCoreApp.cpp` → 1 |
| 4.10 | state field (47.15); `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude src/ApertarCoreApp.cpp` | `grep -c 'playback_hold' src/ApertarCoreApp.cpp` → 1 or more |

- §5: build, restart (you), then `curl -s http://127.0.0.1:8000/api/media | grep -o '"fps_text":"[^"]*"' | sort | uniq -c`
  (each take its own rate); `curl -s 'http://127.0.0.1:8000/api/media/clip?kind=folder&id=<lossless take>' | python3 -m json.tool`
  (prediction: `missing_frames` 37-45 per 250, `holes` one frame each, DURATION the span); `curl -s
  http://127.0.0.1:8000/api/state | grep -o '"playback_hold":"[^"]*"'` → `""`; start a take, repeat → `"recording"`; stop
  it → `""` within about 2 s.
- §7: list empty → `media_root`; a take shows "No DNG frames" → `ls -la` the folder; Core does not start → the journal.

### T48. Core draws a frame, with the touch UI's look

- **You will learn**: (1) lossless JPEG tiles and why they cost more than uncompressed; (2) how the touch UI turns raw into
  a picture, line by line; (3) how a server stays responsive by refusing work (slots, 503) instead of queueing it, and why
  the slots own their memory; (4) reading without filling the page cache; (5) a parity test that keeps two copies honest.
  **Risk**: Core rebuild. Undo: `git revert`. **Time**: 2 sessions, 4 h.
- §2 reading: `CIP:577-698`, `DD:455-536`, `Cdng:1237-1351` (the tile writer), `Cdng:1748-1779` (the writer's `O_CLOEXEC`
  and `DONTNEED`), `WS:59-73`, `WS:263-290`, the sketch's `v2-bench-host.txt`.
- §3: 3.1 `cmp ~/ApertarUI/third_party/liblj92/lj92.c ~/apertar-kb/working/tools/playback/third_party/liblj92/lj92.c`;
  3.2 run `playback_bench --cold` on one of your lossless frames (from T46) and predict the per-worker fps; 3.3 `free -m`
  before and after `cat <a 16-bit take>/*.dng > /dev/null` (prediction: buff/cache grows by the take's size).

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| 4.1 | copy liblj92 (48.1) | `cmp third_party/liblj92/lj92.c ~/ApertarUI/third_party/liblj92/lj92.c` → no output |
| 4.2 | CMake (48.2) | `grep -c 'third_party/liblj92/lj92.c' CMakeLists.txt` → 1 |
| 4.3 | reader part 2 (48.3) | `grep -c 'inline ReadStatus readDngSamples' src/playback/DngFrameReader.hpp` → 1 |
| 4.4 | render look (48.4) | `grep -c 'inline Rgb8Image renderPreview' src/playback/RawRender.hpp` → 1 |
| 4.5 | histogram (48.4) | `grep -c 'inline std::array<float, 48> rawHistogram' src/playback/RawRender.hpp` → 1 |
| 4.6 | slots (48.5) | `grep -c 'class DecodeSlots' src/playback/DecodeSlots.hpp` → 1 |
| 4.7 | host round trip, sizes, parity, fuzz, v2 checks (KB tools) | `./playback_bench --synthetic /tmp/pb` ends `all ok`; `./sizes_test /tmp/sz` ends `sizes ok`; `./parity_test …` ends `parity ok`; `./reader_fuzz …` ends `size lies 20, refused by readDngInfo 20`; `./v2_test frames /tmp/v2` ends `v2 ok` |
| 4.8 | `PlaybackFrames` (48.6) | `grep -c 'PlaybackFrames::frameJpeg' src/playback/PlaybackFrames.cpp` → 1 |
| 4.9 | reason phrases (48.7) | `grep -c 'Range Not Satisfiable' src/web/WebServer.cpp` → 1 |
| 4.10 | route, trim (48.8, 48.9) | `grep -c 'request.path == "/api/media/frame"' src/ApertarCoreApp.cpp` → 1 |

- §5: build, restart, then
  `curl -s -o /tmp/f.jpg -D - "http://127.0.0.1:8000/api/media/frame?kind=folder&id=<take>&n=0&w=640&v=<token>"`
  (200, `X-Frame-Number`, `X-Decode-Ms`, 48 numbers in `X-Histogram`); open `/tmp/f.jpg` beside the touch screen's frame
  (same look); ask three frames at once with `xargs -P 3` (one 503); `free -m` before and after 100 frames (buff/cache
  unchanged); start a take and ask again (409).
- §7 includes: "Core crashed on a frame" → keep the file, run `reader_fuzz` on it; "the picture differs from the touch
  screen" → the parity test on that file.

### T49-T54 (outline)

| Tutorial | Steps (plan rows) | Gate |
| --- | --- | --- |
| T49 Clip Browser | 4.1 CSS (49.1), 4.2 markup (49.2), **4.3 the wiring in `installInteractions` (49.3)**, 4.4 state (49.4), 4.5 open/close and the live view (49.5, 49.6), 4.6 cards (49.7), 4.7 fetch queue, delete helpers, thumbnails, select, remove, download (49.8), 4.8 the button in a take (49.9) | `node --check` of the page script; the mocked Chromium run (as for T32/T34): **fails on any `pageerror` at load and checks that `#previewStream` has a `src`**; 0, 1 and 12 clips, a held list, a refused delete, one `confirm`-free Remove; 390 × 844 and 844 × 390 screenshots; then the Pi on a phone and a laptop; count the live-view connections on the Pi before and after opening the browser (`ss -tn state established '( sport = :8000 )'`) |
| T50 Clip Viewer | 4.1-4.2 CSS and markup, 4.3 the clock (number map, lanes, back-off), 4.4 scrub with resume, 4.5 transport and prev/next, 4.6 histogram, 4.7 metadata with the three extra rows, 4.8 remove and download (size confirmation), 4.9 holds, Live view, keep-awake, 4.10 keys, 4.11 the delete gate (50.7), 4.12 downloads yield (50.8, 50.9) | as T49, plus `node playclock_test.js`; on the Pi: a lossless take with claps at 2 s and 8 s (picture and sound together; the touch screen drifts until T54); a Clear HDR take; record during playback and during a ZIP download (both stop, the toast shows); a remote delete of the open clip (`gone`); two browsers playing at once; Android Back and the iOS swipe; standby with a short timeout; a ramp take once T31 is there |
| T51 Sound | 4.1 range streamer with the stop callback, 4.2 route, 4.3 audio clock and sound-only items | `curl -s -D - -o /dev/null -H 'Range: bytes=0-99' '…/api/media/file?…'` → `206`, `Content-Range: bytes 0-99/…`; the phone plays and seeks; record while a WAV streams: the stream closes within a second |
| T52 MLV | 4.1 reader with VIDF numbers, 4.2 ISP render, 4.3 facts and frames | host test with Core's `MlvEncoder`; parity test against `MlvReader`; §7 note: an MLV and a cDNG of one scene look different on both screens (two render paths, r2 §5; operator S5) |
| T53 ProRes/H.264 | 4.1 copy the two files, 4.2 CMake module and install, 4.3 loader with the decoder mutex, 4.4 facts, `.writing` and frames | `pkg-config --modversion libswscale` first (M10); then one ProRes and one H.264 take; M19 |
| T54 Touch UI yields and keeps time | 4.1 pause in a take (54.1), 4.2 hardware action (54.2), 4.3 Remove (54.3), 4.4 the number clock (54.4), 4.5 the span duration (54.5), 4.6 parity (54.6) | the touch UI builds; the parity test; on the Pi: the same clap take on both screens, in time; record from the rig while the touch screen plays (it pauses) |

### Tutor blocks (each `ref` string occurs once in its file at `eb9cc39` / `d8098d0`, at the stated line; each `check` gets through `tutorial.py`'s parser and safety filter; both checked here)

T47 note:

```
%% tutor
ref core src/ApertarCoreApp.cpp 6422 std::vector<MediaLibraryItem> discoverMediaLibraryItems(
ref core src/ApertarCoreApp.cpp 6492 : durationTextForFrameCount(stats.frameCount, fps);
ref core src/ApertarCoreApp.cpp 5609 struct MediaLibraryItem
ref core src/ApertarCoreApp.cpp 5926 std::string wavDurationTextForFile(const std::filesystem::path &path)
ref core src/ApertarCoreApp.cpp 7819 std::string ApertarCoreApp::buildMediaLibraryJson() const
ref core src/ApertarCoreApp.cpp 7307 if (request.method == "GET" && request.path == "/api/media") {
ref core src/ApertarCoreApp.cpp 7857 std::string ApertarCoreApp::buildWebStateJson() const
ref core src/ApertarCoreApp.cpp 9413 std::string ApertarCoreApp::mediaGateError() const
ref core src/ApertarCoreApp.cpp 9483 std::string ApertarCoreApp::handleCommand(const ControlCommand &command)
ref core src/ApertarCoreApp.cpp 9347 const bool lost = havePrevious && previous.mounted() &&
ref core src/ApertarCoreApp.cpp 9383 mediaWatcherCv_.wait_for(lock, std::chrono::milliseconds(camera_.isRecording() ? 250 : 1000),
ref core src/ApertarCoreApp.cpp 9489 return errorReply(command.id, "Wait for the current capture to finish writing to media.");
ref core src/ApertarCoreApp.cpp 8071 << ",\"media_alive\":" << (mediaSnap.mounted() ? "true" : "false")
ref core src/ApertarCoreApp.cpp 5887 std::string durationTextForFrameCount(uint64_t frameCount, double fps)
ref core src/ApertarCoreApp.hpp 105 std::string mediaGateError() const;
ref core src/ApertarCoreApp.hpp 140 std::atomic<int64_t> lastUserActivityMs_{0};
ref core src/camera/CameraController.cpp 3780 uint64_t nextFrameIndex(int64_t timestampUs)
ref core src/audio/AudioRecordingSession.cpp 367 void AudioRecordingSession::observeVideoFrame(uint64_t sensorBootUs, int64_t frameDurationUs)
ref ui src/playbackcontroller.cpp 1149 void PlaybackController::updateClipMetadata()
ref ui src/playbackcontroller.cpp 827 void PlaybackController::updateFrameFromPlaybackClock()
ref ui src/playbackcontroller.cpp 135 QString formatDurationText(int frameCount, double fps)
ref ui src/playbackcontroller.cpp 121 QString formatByteSize(quint64 bytes)
ref ui src/cliplistmodel.cpp 147 QString durationTextForClip(int frameCount, double fps)
ref ui src/dngdecoder.cpp 1523 double DngDecoder::detectFrameRate(const QString &filePath)
check 4.1 | grep -c 'inline bool readDngInfo' /home/pi/ApertarCore/src/playback/DngTags.hpp | ^1$
check 4.2 | grep -c 'inline FrameList listFrames' /home/pi/ApertarCore/src/playback/ClipFrames.hpp | ^1$
check 4.3 | grep -c 'inline Hold playbackHoldFor' /home/pi/ApertarCore/src/playback/PlaybackHold.hpp | ^1$
check 4.6 | grep -c 'std::string ApertarCoreApp::playbackHoldReason' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.9 | grep -c 'request.path == "/api/media/clip"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.10 | grep -c 'playback_hold' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[1-9]
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
ref core src/ApertarCoreApp.cpp 122 std::string errorReply(int id, const std::string &message)
ref core src/ApertarCoreApp.cpp 7265 response.body = errorReply(-1, "MJPEG preview support was not compiled in.");
ref ui src/cdngimageprovider.cpp 578 QImage renderRawPreviewImpl(const RawFrame &frame, const QSize &requestedSize, const Sample &sample,
ref ui src/dngdecoder.cpp 534 bins.append(std::pow(normalized, 0.65));
ref ui src/playbackcontroller.cpp 263 constexpr int kHistogramTargetSamples = 16000;
check 4.2 | grep -c 'third_party/liblj92/lj92.c' /home/pi/ApertarCore/CMakeLists.txt | ^1$
check 4.3 | grep -c 'inline ReadStatus readDngSamples' /home/pi/ApertarCore/src/playback/DngFrameReader.hpp | ^1$
check 4.4 | grep -c 'inline Rgb8Image renderPreview' /home/pi/ApertarCore/src/playback/RawRender.hpp | ^1$
check 4.6 | grep -c 'class DecodeSlots' /home/pi/ApertarCore/src/playback/DecodeSlots.hpp | ^1$
check 4.9 | grep -c 'Range Not Satisfiable' /home/pi/ApertarCore/src/web/WebServer.cpp | ^1$
check 4.10 | grep -c 'request.path == "/api/media/frame"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
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
ref core src/web/WebControlPage.cpp 10249 async function fetchState(silent, options) {
ref core src/web/WebControlPage.cpp 10403 async function fetchMediaLibrary(silent) {
ref core src/web/WebControlPage.cpp 10422 async function deleteMediaLibraryItem(item) {
ref core src/web/WebControlPage.cpp 10446 function downloadSelectedMediaItems() {
ref core src/web/WebControlPage.cpp 10468 async function deleteSelectedMediaItems() {
ref core src/web/WebControlPage.cpp 11397 document.getElementById("closeMediaBrowserButton").addEventListener
ref core src/web/WebControlPage.cpp 11610 document.getElementById("mediaBrowserOverlay").addEventListener("click"
ref core src/web/WebControlPage.cpp 11558 document.addEventListener("pointerdown", notifyStandbyActivity, {passive: true});
ref core src/web/WebControlPage.cpp 11620 if (event.key === "Escape" && state.mediaBrowserOpen)
ref core src/web/WebControlPage.cpp 2447 <button class="icon-button" id="mediaBrowserButton" aria-label="Open clip browser">
ref core src/ApertarCoreApp.cpp 7649 if (request.method == "POST" && request.path == "/api/media/delete") {
ref core src/ApertarCoreApp.cpp 7721 if (request.method == "POST" && request.path == "/api/media/delete-selected") {
ref core src/ApertarCoreApp.cpp 7343 if (request.method == "GET" && request.path == "/api/media/download") {
ref core src/ApertarCoreApp.cpp 7464 if (request.method == "GET" && request.path == "/api/media/download-selected") {
ref core src/ApertarCoreApp.cpp 6355 void streamZipArchiveToClient(int clientFd,
ref core src/ApertarCoreApp.cpp 6410 const ssize_t bytesRead = ::read(pipeFds[0], buffer.data(), buffer.size());
ref ui qml/ClipBrowserPage.qml 179 text: root.stillMode ? "Still Browser" : "Clip Browser"
ref ui qml/ClipPlayerPage.qml 234 text: "Clip Viewer"
ref ui qml/ClipPlayerPage.qml 393 sourceSize.width: playbackController.playing
ref ui qml/CameraPage.qml 3754 enabled: !root.recording
ref ui src/playbackcontroller.cpp 749 void PlaybackController::handlePlaybackTick()
%%
```

T51-T54 notes add:

```
%% tutor
ref core src/ApertarCoreApp.cpp 6333 void streamFileToClient(int clientFd, const std::filesystem::path &path)
ref core src/ApertarCoreApp.cpp 6285 std::string mediaContentTypeForFile(const std::filesystem::path &path)
ref core src/ApertarCoreApp.cpp 5819 bool hasClipContainerExtension(const std::filesystem::path &path)
ref core CMakeLists.txt 140 if(LIBAV_FOUND)
ref core CMakeLists.txt 195 install(TARGETS apertar-prores-libav LIBRARY DESTINATION lib/apertar-core)
ref core src/video/LibavH264EncoderClient.cpp 17 std::vector<std::filesystem::path> pluginCandidates()
ref core src/video/LibavH264EncoderClient.cpp 105 library_ = ::dlopen(candidate.c_str(), RTLD_NOW | RTLD_LOCAL);
ref ui src/MlvReader.cpp 153 bool MlvReader::open(const QString &path, QString *error)
ref ui src/VideoPlaybackLibav.cpp 137 int read(void *handle, int index, unsigned char *pixels, int width, int height,
ref ui CMakeLists.txt 139 add_library(apertar-video-libav MODULE src/VideoPlaybackLibav.cpp)
ref ui qml/Main.qml 511 onRecordingChanged: {
ref ui qml/Main.qml 319 if (action === "clip_browser") {
ref ui src/playbackcontroller.cpp 849 const int newFrameIndex = qBound(0,
ref ui src/playbackcontroller.cpp 1200 : formatDurationText(m_frameFiles.size(), m_fps));
ref ui src/cliplistmodel.cpp 534 clip.durationText = durationTextForClip(clip.frameCount, detectedFps);
check 54.1 | grep -c 'playbackController.togglePlayback' /home/pi/ApertarUI/qml/Main.qml | ^[1-9]
%%
```

---

## 8. Measurements on the Pi first (T46)

Shorthand `K=~/apertar-kb/working/tools`. All read-only except M5 (one setting, you restore it) and M7, M12, M15, M16
(they record). Order: M1, M2, M3, M4, M6, M8, M9, M10, M14, M17, M18, then the recording ones if you want them. The sketch
has to be in the KB first (`working/tools/playback/`); this pass wrote nothing into the KB.

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

**M1b. Parity and the v2 checks on the Pi, on your own frames** (the same tests as §2.3; the build lines are at the top of
each file in the KB copy). Prediction: `parity ok`, `sizes ok`, `v2 ok`. Decides nothing; it proves the copy on real takes.

**M2. The touch screen today, the baseline you are matching.** Open the same two takes on the touch screen. For 10 s count
how far "FRAME i / N" moves (stopwatch). Meanwhile, from SSH:

```bash
top -b -n 3 -d 2 -H -p "$(pgrep -x Apertar-UI)" | head -30     # which threads, how much CPU (the binary is Apertar-UI, UCMake:256)
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

Prediction: standby comes (F17). Decides T54's keep-awake and confirms §2.7's.

**M6. Do your browsers play the take's WAV?**

```bash
scp pi@<pi>:/media/RAW/<take>/<take>.wav ~/Desktop/       # on the laptop
```

Open it in Chrome, Safari and Firefox (drag it into a tab), and on the phone (Files / AirDrop). Note: plays, seeks, length
right. Decides O13.

**M7 (optional; it records two takes, so you run it). Does reading an old take cost frames during a take?** The reads go to
the drive, not the page cache (critic m4: `cat` of the same ten frames is served from memory after the first pass).

```bash
bash $K/takes.sh 1 60                                                                  # baseline: missing=0
( for f in /media/RAW/<old take>/*.dng; do dd if="$f" of=/dev/null bs=4M iflag=direct status=none; sleep 0.1; done ) &
bash $K/takes.sh 1 60; kill %1
```

Decides Q4 (thumbnails in a take). The default holds everything, so this matters only if you want more.

**M8. The NVMe link and its read speed.**

```bash
cat /sys/class/nvme/nvme0/device/current_link_speed /sys/class/nvme/nvme0/device/current_link_width   # Gen 2 = 5.0 GT/s (sysfs path PROBABLE)
dd if=/media/RAW/<hdr take>/<take>_000000020.dng of=/dev/null bs=4M iflag=direct     # one cold 16.6 MB read, MB/s
```

Prediction: 5.0 GT/s x1 and 350-450 MB/s. Decides whether 16-bit at 25 fps is read-bound (§2.8).

**M9. The Pi's locale.** `locale | head -3`. Decides the month names (Q15).

**M10 (before T53).** `pkg-config --modversion libswscale` and `ls ~/ApertarUI/build*/apertar-video-libav.so`. Decides
whether T53 needs `libswscale-dev` installed first (you).

**M11 (after T48 and T50).** The frame route's `X-Decode-Ms` over 50 frames, `top -H -p $(pgrep apertar-core)` while the
browser plays, read MB/s from `cat /proc/diskstats`, the temperature, and `free -m` before and after (buff/cache should not
grow). With O4 the page shows Achieved and Skipped; without it, count requests in the browser's network panel.

**M12 (records two takes). Clap sync, today and after T50.** Two 20 s takes with a clap at 2 s and 18 s, one uncompressed and
one lossless. Play both on the touch screen now and note how far picture and sound are apart at the second clap (prediction:
uncompressed together; lossless picture ~1 s early or held at the end, §2.6). After T50, the same in the WebUI (prediction:
together within a frame), once with Bluetooth headphones on the phone. Decides T54 and O22.

**M13. The touch screen's live preview while a browser plays 16-bit 4K.** Count the preview's smoothness (or `top -H` on
Core's preview thread) with and without browser playback. Decides the default worker count (R12).

**M14. The phone on the camera's network.** M3 from the phone (a terminal app, or the browser's network panel over 100
thumbnail loads), and after T50 the achieved fps and the arrival time of a paused 1920 w frame. Decides the play and pause
widths on the phone.

**M15 (only if you want downloads during takes; it records).** `takes.sh 1 60` as a baseline, then the same while
`curl -s -o /dev/null 'http://<pi>:8000/api/media/download?kind=folder&id=<old take>'` runs from the laptop. Decides Q21.

**M16 (after T50; it records). Record right after a review.** Play 60 s of a 16-bit take in the browser, then
`takes.sh 1 30`; missing frames, temperature and `grep -E 'allocstall|pgscan_direct' /proc/vmstat` against the baseline.
Decides whether `O_DIRECT` reads are needed beyond the v2 drop (§2.10).

**M17. The list with a long take.** `/api/media` time after a Core restart and warm, with a 10-minute take on the card
(15,000 entries). Decides the facts-cache key.

**M18. A real lossy take.** `playback_bench --cold` on a frame of a real `cDNG_3to1_` and `cDNG_5to1_` take. Decides what
to tell yourself about lossy playback (§2.3).

**M19 (after T53).** One H.264 take: the achieved fps while playing and the time per scrub position through the plugin.
Decides O12 (Q27).

---

## 9. Options for Patrik (not defaults)

### 9.1 Cinemate's features

| # | Option | Cinemate source | Cost (PROBABLE) | My suggestion |
| --- | --- | --- | --- | --- |
| O1 | Frame step ◀ ▶ (hold to repeat) and first / last frame; arrow keys on a laptop | `cm:…/settings_editor.html:2618-2627`, `6716-6720` (r1) | ~60 lines WebUI | **yes**: long takes and finding the clap need it (operator P11) |
| O2 | Loop toggle (off = stop on the last frame) | r1 §1.5 | ~20 | if you want play-once |
| O3 | Conform-rate playback with "0.50× SLOMO" / "2.00× FAST" | r1 §1.4 | ~60 WebUI + a conform setting | later, with T31 ramp takes |
| O3b | A ramp take in real time with sound, through `fps-ramp.txt` | — (operator P2) | ~80 | if you want to check the performance, not the edit |
| O4 | Honest rate row: Recorded, Playing at, Achieved, Frames skipped; at least "PLAYING · 7 FPS" while under 95 % | r1 §1.4, lesson 2 | ~50 (the badge alone ~10) | **yes**: lossless takes will skip, and DROPPED alone does not say what the player skipped (operator P5) |
| O5 | DROP N badge on the card and in the viewer | r1 §1.4; `missing_frames` exists after T47 | ~20 | **yes** |
| O6 | Filmstrip scrubber (16 frames under the bar) | r1 §1.2 | ~80 + 16 decodes per clip | no |
| O7 | Sort "Largest first"; a "One row" strip view | r1 §1.2 | ~30 | no |
| O8 | Card mini-scrub (24-frame flip) | r1 §1.6 | ~70 + decodes | no |
| O9 | Mode boxes: 12b/16b, HDR/SDR, LIN/companded, LJ92/UNC, WAV | r1 §1.4 | ~30 | the FORMAT row covers it (D16) |
| O10 | Timecode readout: the **recorded** SMPTE start (tag 51043) + the shown frame's **number**, not Cinemate's position ÷ rate | r1 §1.5 | ~40 | **yes** |
| O11 | The recorder writes a preview: a per-take preview track (sidecar), full-rate playback of lossless takes on both screens | r1 §3 (Cinemate: IFD1 per DNG) | ~400 Core incl. the copy worker; per-frame CPU in every take (UNCONFIRMED; Cinemate +4 ms) | only if M1/M2 say lossless is too choppy for you |
| O12 | H.264 through the browser's `<video>` (the phone's own decoder, full rate), muted, paced by the WAV clock; Range for `.mp4` | — (operator P12) | ~100 WebUI + `.mp4` in T51's route | if M19 says the plugin is too slow |
| O13 | Core serves a 16-bit copy of the WAV for browsers that refuse s24 or float | — | ~80 | only if M6 fails |
| O14 | Thumbnails kept on the system drive (`~/.cache/apertar-core/thumbs/`), so a Core restart does not decode every card again | Cinemate keeps them in the browser for an hour (r1 §2.4) | ~60 | if the first fill after a restart annoys you |

### 9.2 New options from the operator review, and the WebUI extras

| # | Option | Cost (PROBABLE) | My suggestion |
| --- | --- | --- | --- |
| O15 | Waveform strip under the scrub (decimated peaks from the WAV, made by Core) | ~120 | yes for sync checks, after T51 |
| O16 | Zoom 1:1 of the half-resolution picture when paused (a crop route), labelled "Half resolution" so nobody judges critical focus from it (r4 C6) | ~80 | maybe |
| O17 | "Save this frame" (the 1920 w JPEG as a download) | ~15 | yes (the director sends a still) |
| O18 | Histogram in stops (both screens, with U11) | ~30 + parity | yes for Clear HDR |
| O19 | Fullscreen where the browser has it (feature-detected; hidden on iPhone) | ~20 | yes |
| O20 | Keep the phone's screen on while playing over plain HTTP (a muted, looping, tiny inline `<video>`, the usual trick where the Wake Lock API is missing, F39) | ~25 | test on your phone first (Q10) |
| O21 | Play the recovered frames of an unfinalised MLV, with "MLV not finalised (media pulled?): 102 frames recovered." (the touch UI refuses such files) | ~40 | yes, if you shoot MLV |
| O22 | Per-device A/V offset ("Sync −150 ms") in the metadata panel, kept in the browser | ~30 | only if M12 shows Bluetooth lag |
| W1 | Today's stat chips (frames, FPS, size) as a fourth card line | ~15 | no: the touch card shows four things; the rest is in Clip Metadata |
| W2 | A "Review C0007" chip beside the record button for 60 s after a take ends; a tap opens the viewer on it, paused | ~40 | yes (Cinemate opens on the newest take, r1 §1.5) |

---

## 10. Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Lossless 4K plays at ~5-8 fps on the Pi | PROBABLE (§2.3) | the touch UI has the same limit; O4 makes it visible; the play cache smooths replays; O11 if you want full rate |
| R2 | 16-bit uncompressed playback at 25 fps reads 415 MB/s and keeps ~2 cores busy; heat | PROBABLE (F25, §2.3) | only when idle; 2 workers at nice 10; M1 temperature; M8 link; row-selective reads; 480 w |
| R3 | A new TCP connection and thread per frame (`Connection: close`) | CONFIRMED mechanism (F8); cost UNCONFIRMED | M3, M14; look-ahead capped at 2 frames; keep-alive later |
| R4 | A browser cannot play the s24 WAV | UNCONFIRMED | M6; silent with the SOUND row and a toast; O13 |
| R5 | Safari needs Range for media | PROBABLE | T51 adds Range |
| R6 | A reader bug in Core's process | PROBABLE risk; mitigations CONFIRMED in the sketch | bounds and the size cap before allocation; fuzz with size lies in the gate; exceptions caught per client thread (`WS:279-284`). If the Pi ever crashes on a file, move decoding into a helper process |
| R7 | The named copies (reader, render, histogram, text, clock, MLV) drift from the touch UI | PROBABLE over time | the parity test in the KB (T54 adds the clock); both files name each other; every U-change goes into both |
| R8 | The new list (cards) loses one of today's flows, or the page stops at load | CONFIRMED trap (F35) | row 49.3; the mocked Chromium gate fails on any `pageerror` at load; T49 keeps today's fetch, download and delete paths |
| R9 | Touch UI root `/media/RAW` vs Core `--media` | CONFIRMED facts (r4 K20) | the same on your Pi (PROBABLE); `media_root` in every reply |
| R10 | T31 ramp takes number frames by count, so `missing_frames` reads 0 | CONFIRMED in the T31 patch notes (F38) | DROPPED says "unknown (speed ramp)" |
| R11 | The controls project (T36-T45) edits the same files first | CONFIRMED (F29; both edit `App`, `Web`, `WS`) | search strings, not line numbers; `tutorial.py refs` before each tutorial; 409 added once |
| R12 | The WebUI viewer and the touch UI play at once: two decoders | PROBABLE, rare | Core's slots bound its share; M13 |
| R13 | Keep-awake while playing costs battery | PROBABLE, small | only while playing |
| R14 | The movie plugin brings a second FFmpeg into Core's process (the ProRes plugin may use a private FFmpeg, `CMake:46-64`) | PROBABLE risk | `RTLD_LOCAL` and versioned FFmpeg sonames keep them apart (PROBABLE); the plugin loads only on the first movie frame, never in a take; T53 tests a ProRes take after a movie was played |
| R15 | Month names differ between the screens (F23) | PROBABLE if the Pi is not English | M9; Q15 |
| R16 | A read stuck on a dead NVMe holds its slot (and its HTTP thread) for the device timeout; `WebServer::stop` waits for it (F8) | PROBABLE (r3 §4.5); today's downloads have the same exposure | no lock held across a card read (§2.7); "Waiting for the media to answer…"; the slots refuse instead of queueing |
| R17 | Downloads refused in a take change today's behaviour (a DIT used to copy take 6 while take 7 rolled) | CONFIRMED change (F34) | Q21; M15 if you want them allowed |
| R18 | The touch screen keeps playing during a take until T54 | CONFIRMED (§1.2) | T54 (Q22) |
| R19 | The two screens disagree on DURATION and sync for lossless takes until T54 | CONFIRMED (D15) | T54; M12 shows it |
| R20 | The phone layout overflows somewhere not sketched | PROBABLE | the 390 × 844 and 844 × 390 gate screenshots; your phone (Q10) |
| R21 | The phone's screen locks during a long take (no Wake Lock over HTTP) and the tab pauses | PROBABLE (F39) | O20; the pause toast says why |
| R22 | A take starts while thousands of files are being deleted | CONFIRMED gate gap (F16) | Q23 |
| R23 | Bluetooth output latency shifts sync | UNCONFIRMED | M12; O22 |
| R24 | The yield window refuses playback for up to 1.5 s after a hold ends, and for 3 s after a command that then failed | CONFIRMED by design (`v2_test` hold) | the hold card says why; the user presses Play again |

---

## 11. Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Is a WebUI viewer that shows lossless 4K takes at ~5-8 fps (the touch screen's limit too) good enough for now, with O11 later if not? | yes; decide after T46 |
| Q2 | Should the WebUI's "Show" button only filter the list (opening on Stills in photo mode), or switch the camera's photo mode like the touch UI? | filter only (D1) |
| Q3 | Keep Download, Select All and the Timelapse and Audio categories in the new browser? | yes (D3, D13) |
| Q4 | In a take, hold everything (frames, thumbnails, sound), or let cached thumbnails through? | hold everything |
| Q5 | Grey the WebUI folder button in a take and a timelapse, like the touch UI's? | greyed |
| Q6 | BIT DEPTH: show the touch UI's "16-bit" for companded and lossy takes, with the stored depth in FORMAT; or do U5 so both screens say "12-bit"? | copy now; U5 later (D9) |
| Q7 | Touch-UI quirks: fix the wording ("1 item"); copy the one-channel 4K histogram for parity until U6 fixes both? | yes, yes |
| Q8 | Without a WAV, skip late frames (wall clock) instead of slowing down like the touch UI? | skip (D8) |
| Q9 | Which Cinemate options do you want? | O1, O4, O5, O10 |
| Q10 | Your phone: iPhone (Safari) or Android (Chrome)? It decides the long-press, Back and screen-lock tests | design for both; test on yours |
| Q11 | Keep the camera awake while a clip plays (not while paused)? | yes |
| Q12 | Numbering T46-T54; and type the sketched code (~1,150 lines) or copy it from the KB after reading? | T46-T54; your call on typing |
| Q13 | Commit format: house format (area, imperative, Why, Tested, no Co-Authored-By) or what your recent commits use (`What:` + Co-Authored-By)? (r4 K18) | ask |
| Q14 | Later: should the touch UI take its clip facts, thumbnails and deletes from Core (U3, U4, U8), so both screens share one truth? | later, after T50 |
| Q15 | Month names: the touch UI uses the Pi's locale (F23). If M9 is not English, should Core follow the locale too (`strftime_l` on one call)? | follow the Pi's locale |
| Q16 | Movie decoder: Core builds its own copy of `apertar-video-libav.so` from the same two files (default), or loads the touch UI's installed one? | Core's own copy |
| Q17 | Order: playback after the controls project (T36-T45), or between? | after controls |
| Q18 | Space for play/pause on a laptop (D12)? | yes |
| Q19 | Map sound time to the frame **number** (real time, in sync on takes with drops), with DURATION the span, on both screens (U9 in T54)? | yes |
| Q20 | Playback in standby, and during long-interval timelapses? | hold (as designed); "allow in standby" is a small change if you want it |
| Q21 | Downloads during a take: refuse new ones and stop running ones? | yes |
| Q22 | Bring the touch UI along in this project as T54 (it pauses in a take; the number clock and the span duration)? | yes |
| Q23 | Refuse `record_start` while a delete is still running ("Deleting media. One moment.")? | yes |
| Q24 | O4 (rate) and O5 (drops) with T50, or at least "PLAYING · 7 FPS"? | O4 + O5 |
| Q25 | The three WebUI-only metadata rows SOUND, FORMAT, DROPPED (D16)? | yes |
| Q26 | Play the recovered frames of an unfinalised MLV (O21)? | yes, with the line |
| Q27 | H.264 through the browser's `<video>` (O12), if M19 says the plugin is slow? | decide after M19 |
| Q28 | A "Review last take" chip on the main page (W2)? | yes |
| Q29 | Fullscreen where the browser has it (O19)? | yes, hidden on iPhone |
| Q30 | Ramp takes: timeline view with sound off (default), or real time with sound (O3b)? | timeline view |

---

## 12. What changed in v2, and why

Point by point, with the evidence: `changes-from-critique.md`. In short:

| # | v1 | v2 | From |
| --- | --- | --- | --- |
| V1 | `#mediaBrowserOverlay` replaced; the wiring left as is | row 49.3 rewires `installInteractions`; the gate fails on a load error | critic B1 |
| V2 | T47's reader included `lj92.h`; the cache was a member in `App.hpp` | `DngTags.hpp` without liblj92 for T47; the cache is file-scope in App | critic B2 |
| V3 | the clock picked the n-th file; DURATION files ÷ fps; 0-byte frames left out | the clock picks the frame **number**; DURATION the span; 0-byte frames counted as the touch UI counts them and shown as holes; T54 does the same on the touch UI | critic M1, M7; operator P1, P15 |
| V4 | hold on frames and new WAV requests only | the clip facts, the WAV stream (per chunk) and the downloads (start and per chunk) yield too | critic M2, M3; operator P3 |
| V5 | hold signals read with the camera's mutex in the decode; "writing" promised after every take | a pure rule + a lock-free yield window opened by `handleCommand` and kept open by the watcher; "writing" for stills only | critic M8; operator S1 |
| V6 | reads filled the page cache; buffers per request; size checked after allocation | `O_CLOEXEC` + `DONTNEED` per chunk; slots own their buffers, trimmed by the watcher; a 4096 × 3072 cap and the strip check before allocation (the critic's 4096 × 2304 cap would have refused IMX477 frames) | critic M4, M5, M9; operator P19 |
| V7 | one movie decoder shared by two slots | one decoder per movie with its own mutex, in-order requests, install rule, the H.264 plugin's search order | critic M6; operator P12 |
| V8 | 503 → retry at once; network errors unhandled | back-off per lane; a closed connection counts as a 503; look-ahead capped at two frames; split thumbnail and play caches | critic M12; operator P16 |
| V9 | the parity rule was not one rule | one rule (§2.4): the nine fields copy the touch UI; three extra rows; time fixed on both screens | operator P15, P5, P6, P24 |
| V10 | the touch UI does not change | T54 (recommended): it pauses in a take and keeps time | operator P4, P1 |
| V11 | phone = the touch UI's square sizes; Download beside Remove; no browser Back; long-press callouts | phone rows and middle-elided names; Download in the title row; `pushState`/`popstate`; callout off, 800 ms kept; no Wake Lock over HTTP (O20 instead) | operator P7, P8, P9 |
| V12 | scrub paused playback; hold texts promised a resume; a 404 reopened by index | scrub plays on as on the touch UI; "Press Play when…"; `gone` and reopen by id | operator P10, P14, P18 |
| V13 | ramp takes not handled | played as their timeline with sound off; O3b real time | operator P2 |
| V14 | §2.1 did not answer Cinemate's lesson | it does (NumPy, uncompressed only, vs C++ at the touch UI's cost) | critic M10 |
| V15 | confirm twice; fetch dropped; minor anchors and wording | confirm-free delete helpers, queued fetch; m1-m20 and w1-w9 folded in; eject and format yield too (new) | critic M11, m1-m20, w1-w9 |
| V16 | T46 had M1-M11 | M2 and M7 commands fixed; M12-M19 added | critic m3, m4; operator |

v1's own history (what changed from the paused draft) is `design-playback-v1.md` §12.

---

## Appendix A. The sketch (v2)

Folder: `scratchpad/playback/sketch/` (in no repository; it moves to the KB's `working/tools/playback/` when this design
lands). v1 is kept as `sketch-v1/`.

| File | Lines | What |
| --- | --- | --- |
| `src/playback/DngTags.hpp` | 326 | T47: tail-IFD reader, the size cap and strip check before allocation, `openDngFrame` / `closeDngFrame` |
| `src/playback/DngFrameReader.hpp` | 125 | T48: payload in chunks, LJ92 tiles, LinearizationTable, stop callback, page-cache drop |
| `src/playback/ClipFrames.hpp` | 159 | frame numbers, holes, 0-byte frames, one per stem, the time → frame map |
| `src/playback/PlaybackHold.hpp` | 91 | `playbackHoldFor()`, `PlaybackYield` |
| `src/playback/DecodeSlots.hpp` | 115 | slots with their own buffers, `tryTake`, `trimIdle` |
| `src/playback/RawRender.hpp` | 226 | the touch UI's look (`CIP:380-698`) and histogram (`DD:455-536`); now includes `DngTags.hpp` only |
| `third_party/liblj92/` | — | the touch UI's files; `cmp` identical |
| `page/playclock.js`, `page/playclock_test.js` | 118, 46 | the viewer's clock and request rules; node test, 16 checks |
| `v2_test.cpp` | 333 | 38 checks: frames, drift, hold, stop, cache, slots, alloc, sizes (build line at the top) |
| `playback_bench.cpp` | 251 | `--synthetic DIR` (Core's encoder → reader, 36 checks, timings) and `[--cold] FILE.dng…` |
| `sizes_test.cpp` | 40 | the code critic's six sensor sizes × 12/16 × uncompressed/lossless (its Appendix A.1), on the v2 API |
| `reader_fuzz.cpp` | 82 | truncated and byte-flipped copies under ASan/UBSan, plus five size lies per input |
| `parity/parity_test.cpp`, `parity/ui_time.cpp` | 45, 28 | the copy vs the touch UI's own `DngDecoder` and renderer (Qt 6), and the touch UI's own timings |
| `lossy/lossy_write.cpp` | 44 | 4K 12-bit frames from Core's `LossyDngEncoder` (3:1, 5:1) |
| `v2-results-host.txt`, `v2-bench-host.txt`, `v2-parity-host.txt`, `v2-fuzz-host.txt`, `v2-page-host.txt`, `v2-appcheck-host.txt` | | this pass's outputs; `results-host.txt` is v1's |

Build lines are at the top of `playback_bench.cpp` and `v2_test.cpp`. The parity test builds with
`g++ -std=c++20 -O2 -fPIC -Isrc/playback -Ithird_party/liblj92 -I$UI/src $(pkg-config --cflags Qt6Core Qt6Gui Qt6Quick libtiff-4) parity/parity_test.cpp $UI/src/dngdecoder.cpp $UI/src/cdngimageprovider.cpp $UI/src/tiffhelper.cpp parity/moc_cdngimageprovider.cpp lj92.o $(pkg-config --libs Qt6Core Qt6Gui Qt6Quick libtiff-4)`
and runs with `QT_QPA_PLATFORM=offscreen`. The fuzz builds with `-fsanitize=address,undefined` and `lj92_asan.o`. This
host: g++ 13.3, Qt 6.4.2, node 22, 4 threads of a Xeon at 2.1 GHz.

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
