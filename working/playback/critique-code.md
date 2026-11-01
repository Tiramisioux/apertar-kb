# Code critique: `design-playback.md` (v1, WebUI playback in the touch UI's shape)

2026-10-29, cloud session, code critic. Read-only on every repository; nothing ran on the Pi. Checked against the trees
and commits named in the design: Core `0296ed1`, touch UI `5aab7e2`, Cinemate `d6cc93e`, KB `e8eeef2`. KB HEAD is now
`9bf388f` (two autosaves that touch only `working/playback/`). The design file is the same as the one at 23:57 (md5
`c00bf903…`).

Short names are the design's: `App`, `App.hpp`, `WS`, `Web`, `CC`, `Cdng`, `CMake`, `H264C` are Core `0296ed1`. `CBP`,
`CPP`, `Main`, `CamP`, `PC`, `CLM`, `CIP`, `DD`, `VP`, `VPL`, `VPA`, `UCMake` are the touch UI `5aab7e2`. `cm:` is
Cinemate `d6cc93e`, `kb:` is the KB `e8eeef2`, and `sketch/` is `scratchpad/playback/sketch/`.

Labels: **CONFIRMED** means I opened the line or ran the command in this session. **PROBABLE** means derived, and the
derivation is given. **UNCONFIRMED** means only the Pi or a browser can settle it.

---

## 0. Verdict

The anchors are sound. All 52 tutor `ref` lines and every search string in §6 occur exactly once at the stated line.
The 11 `check` lines get through `tutorial.py`'s parser and safety filter. The facts table F1-F29 holds, apart from the
wording fixes in §5. I re-ran the sketch's bench and parity test and both reproduce: 0 differing samples and 0 differing
pixels on 6 frames. A new run of the reader on all six of Core's sensor sizes was bit-exact (§1).

These must change before v2. Severity: **B** = it breaks the build or the page, **M** = wrong behaviour or a broken
promise, **m** = small.

| # | Sev | One line |
| --- | --- | --- |
| B1 | B | Replacing `#mediaBrowserOverlay` (49.2) kills the whole WebUI script at load. `installInteractions()` wires the old ids without null checks, and no plan row changes it |
| B2 | B | T47 does not compile. Reader part 1 includes `lj92.h`, which arrives only in T48 |
| M1 | M | With dropped frames, sound and picture drift apart and durations come out short. Frames are indexed by position, but Core numbers them by time |
| M2 | M | `/api/media/clip` has no hold but reads the card (folder scan, tail, WAV header) |
| M3 | M | A WAV stream already running and every Download keep reading the card in a take |
| M4 | M | Playback fills the page cache, which Core's writer deliberately keeps empty (`POSIX_FADV_DONTNEED`) |
| M5 | M | Buffers are made per request. With a new thread per connection, a 16-bit frame costs +65 % on the host. They must belong to the slot |
| M6 | M | The movie decoder handle is not thread-safe. With "one decoder per clip" and 2 slots, two threads can use one libav context |
| M7 | M | The touch UI counts 0-byte frames in FRAMES, FRAME i / N and DURATION; the design does not. This parity gap is missing from §2.9 |
| M8 | M | Three of the hold signals take `CameraController::mutex_`, which record start and stop hold for the whole setup or drain. Walkthrough B's `"writing"` is never seen for a video take, and the per-tile check is slow |
| M9 | M | A corrupt DNG makes the reader allocate 512 MB before it rejects the file. §4.9 claims bounds come before allocation |
| M10 | M | §2.1 does not answer Cinemate's own lesson: Cinemate turned raw decode off after hardware tests |
| M11 | M | Remove would ask twice: the new dialog, then the old `window.confirm` |
| M12 | M | A 33rd connection is closed with no reply. The page then sees a network error, not a 503 |
| m1-m20 | m | §4 |
| w1-w9 | w | citations and wording, §5 |

The operator critic (`critique-operator.md`) reached M1, M3 and M4 on its own (its P1, P3, P19). This file adds the code
evidence for them.

---

## 1. What I ran on this host

| Run | Result | Label |
| --- | --- | --- |
| Every `ref` line of the four tutor blocks: is the string at the stated line, and does it occur once (same `grep -nF` as `tutorial.py refs`) | 52 of 52 at their lines, each once | CONFIRMED |
| The tutor blocks through `tutorial.py`'s own `tutor_block()` and `unsafe_reason()` | 52 refs, 11 checks, none refused | CONFIRMED |
| `t34/hostcheck-core.sh` on `core-tip` (baseline: the tree before any change) | 0 errors, 0 warnings in CC, App, Web | CONFIRMED |
| The page script pulled out of `Web` (the raw string, `<script>`; 7,616 lines), then `node --check` (v22.22.0) | ok (baseline for the T49/T50 gate) | CONFIRMED |
| `sketch/playback_bench` on the sketch frames | 37 / 161 / 26 / 183 / 74 ms per 640 w frame (SDR12 unc, SDR12 LJ, HDR16 unc, HDR16 LJ, lossy 3:1); "all ok". Matches §2.3 within the stated ±10 %, except HDR16 unc, which came out faster here (samples 9.3 ms against 22.7 ms) | CONFIRMED |
| `sketch/parity/parity_test` on the same 6 frames (offscreen Qt) | `parity ok (0)`: samples, 640×360 pixels and histogram all 0 | CONFIRMED |
| **New:** Core's `CdngEncoder` writes 6 sizes × 12/16-bit × uncompressed/lossless (1928×1090, 2028×1520, 2028×1080, 1332×990, 3856×2180, 1920×1080); the sketch reader reads them back | 24 of 24 bit-exact, including two tile columns (976×128 ×18 tiles for 1928×1090) and a partial last tile row | CONFIRMED (Appendix A.1) |
| **New:** two words of a Core DNG changed (width and height to 16384) | `readDngInfo` accepts the file; `readDngSamples` allocates 512 MB and then refuses ("Strip is shorter than the image."). maxrss 515 MB, against 30 MB for the good frame | CONFIRMED (A.2) |
| **New:** one frame decoded on a fresh thread with fresh buffers, against buffers that are kept | HDR16 unc 40.4 ms against 24.5 ms; SDR12 unc 25.7 against 24.9; SDR12 LJ 153.5 against 154.8 (medians of 7) | CONFIRMED (A.3) |
| **New:** both sketch headers force-included into `ApertarCoreApp.cpp` with Core's flags (`-Wall -Wextra -Wpedantic`, libcamera on) | 0 errors, 0 warnings: no name clashes | CONFIRMED |
| **New:** the same without `-I third_party/liblj92` (the state of the tree at T47) | `fatal error: lj92.h: No such file or directory` | CONFIRMED (B2) |
| `gcc -Wall -Wextra -Wpedantic -c lj92.c` (the touch UI's file; it compares equal to the sketch copy with `cmp`) | no warnings | CONFIRMED |
| `cmp` of the 9 web icons against `ui/qml/icons` | all identical (F27) | CONFIRMED |

The touch UI needs no build here: the design does not change it, and the parity test already compiles its `DngDecoder`
and renderer against Qt 6.4.2. The scratch tests I wrote are in Appendix A, and their folder is deleted, so this file is
the only one this pass leaves behind.

---

## 2. Blockers

### B1. Replacing `#mediaBrowserOverlay` kills the whole WebUI script at load

- **Evidence (CONFIRMED).** `installInteractions()` calls `document.getElementById(...).addEventListener` with no null
  check on these ids: `closeMediaBrowserButton`, `refreshMediaBrowserButton`, `mediaBrowserSortSelect`,
  `selectAllMediaButton`, `clearMediaSelectionButton`, `downloadSelectedMediaButton` and `deleteSelectedMediaButton`
  (`Web:11396-11407`), and the overlay itself (`Web:11610-11613`).
- **Why it matters.** `installInteractions()` runs at top level, ahead of `installPreviewStream()`, the 1 s
  `fetchState` poll and the first `fetchState` (`Web:11649-11653`).
- **What breaks.** Row 49.2 removes that markup (`Web:3979-4030`). The page then throws `TypeError` at `Web:11397`, and
  every listener after it is never installed: Settings close, still selects, config editor, Escape, resize, and so on.
  There is no live view and no state poll, so the camera page is dead. No plan row covers this. The rows that do touch
  the old functions (`setMediaBrowserOpen` 49.4, `renderMediaLibrary` 49.6) leave the wiring alone.
- **What does not throw.** `updateMediaSelectionControls` (`Web:7649-7671`), `setMediaBrowserSort` (`Web:7588-7594`)
  and `renderMediaLibrary` (`Web:7707-7725`) check for null. After the change they silently do nothing.
- **Fix.**
  - Add a row **49.2b** in `installInteractions`, at search strings
    `document.getElementById("closeMediaBrowserButton").addEventListener` and
    `document.getElementById("mediaBrowserOverlay").addEventListener("click"`.
  - Replace the old wiring with the new overlay's; keep `mediaBrowserButton` (`Web:11396`).
  - In 49.6, delete or rewrite the four list helpers above.
  - The T49 gate in the mocked Chromium must fail on any `pageerror` at load, and must check that `#previewStream` has a
    `src` after load.

### B2. T47 does not compile

- **Evidence (CONFIRMED).** Row 47.1 takes "sketch lines 1-298". Those lines include `extern "C" { #include "lj92.h" }`
  (`sketch/src/playback/DngFrameReader.hpp:24-26`). The liblj92 copy and its include directory arrive in T48 (48.1,
  48.2). Row 47.4 then puts `playback::ClipFactsCache` into `App.hpp`, so `main.cpp` and `ApertarCoreApp.cpp` pull the
  chain in too.
- **Host run.** The sketch header in `ApertarCoreApp.cpp` without the include path gives
  `fatal error: lj92.h: No such file or directory`.
- **Fix.** Pick one:
  - (a) Move 48.1 and 48.2 to the start of T47: copy liblj92, change `LANGUAGES CXX` to `LANGUAGES C CXX`, add the
    include directory, and add `lj92.c` to the target.
  - (b) Split the header: `DngTags.hpp` (part 1, no lj92) for T47, and `DngFrameReader.hpp` (part 2, includes `lj92.h`)
    for T48.

  Either way, keep the cache out of `App.hpp`: a file-scope object in `App`'s anonymous namespace, or
  `std::unique_ptr<playback::ClipFactsCache>` with a forward declaration. Then `App.hpp` changes by one declaration
  (`playbackHoldReason`), and its users do not rebuild against the reader.
- **Also.** Add `-I$C/third_party/liblj92` to `t34/hostcheck-core.sh`, and add `src/playback/PlaybackFrames.cpp` and
  `src/web/WebServer.cpp` to its file list.
- **Good news.** With the path in place, both sketch headers inside `App`, under Core's warning flags, give 0 errors and
  0 warnings.

---

## 3. Major

### M1. With dropped frames, sound and picture drift apart and durations come out short

- **The design.** `frame` is the "0-based position in the sorted list of non-empty frames (not the number in the name;
  gaps are skipped)" (§4.4). The page asks for `floor(audio.currentTime × fps)` (§2.6).
- **How Core numbers frames.** By time: `timeIndex = llround((ts − first) × fps / 1e6)` (`CC:3780-3787`). Any frame not
  written leaves a gap in the file numbers.
- **How often that happens.**
  - KB: "lossless at 25 fps (queue fills, 20-35 % lost)" (`kb:lessons/hardware-log.md:113`).
  - At 30 fps, about 50 of ~285 indices "never arrive" (`:113-114`).
  - The gap pattern is one frame every 5-9 frames (`:165`).
- **Effect (PROBABLE, arithmetic).** A 10 s lossless take with 30 % lost has 175 files. At 25 fps the file list ends at
  7 s while the sound runs to 10 s. Walkthrough D's "the sound stays in time" is false for exactly the take it describes.
- **Durations.** `duration_text` = files ÷ fps is short by the same amount. So is the touch card (`CLM:530-534`), and so
  is the touch metadata (`PC:1200`).
- **Same flaw elsewhere.**
  - The touch UI: `floor(ms × fps)` into `m_frameFiles` (`PC:849-851`, list built at `PC:696-706`).
  - Cinemate: "a position, not a filename number" (`cm:src/module/app/playback.py:265`).

  Copying them copies the flaw.
- **Fix.**
  - `/api/media/clip` returns `first_index`, `last_index` and the gaps as ranges, from the frame list Core already builds
    for `dropped_frames`.
  - `/api/media/frame` takes `n=<frame number>` and serves the present frame at or before `n`, with headers
    `X-Frame-Number` and `X-Frame-Index`.
  - The page asks for `n = first + floor(t × fps)`.
  - DURATION = `(last − first + 1) ÷ fps`.
  - "FRAME i / N": either timeline numbers (`n − first + 1` / span) or file positions. Add that as a question for Patrik.
  - The same fix for the touch UI is a new option U9.
  - T31 ramp takes number by count (R10), so they keep the position rule. The operator critique's P2 covers their timing.

### M2. `/api/media/clip` has no hold but reads the card

- **The design.** §4.1 lists only 404 and 400 for the route. What the route reads:
  - `listFrames(dir)`: a `readdir` of up to ~15,000 entries for a 10-minute take, plus a stat per file on the first scan;
  - the first frame's tail;
  - the WAV header (row 47.2).
- **Scenario.** §2.7 keeps an open browser open in a take ("An open browser or viewer stays open"). A tap on a card, or
  prev/next in the viewer, then reads the card during the take.
- **Fix.**
  - Run `playbackHoldReason()` first in this route as well.
  - In a hold, answer from the facts cache with `"held":"…"` (the viewer opens on the hold card), or 409 when nothing is
    cached.
  - Add the route to the §2.7 table, to §4.1 and to row 47.9.

### M3. A running WAV stream and every Download keep reading the card in a take

- **(a) The WAV stream.** The hold is checked once, when the request starts (§4.5). The stream writer keeps reading in
  64 KiB chunks for as long as the browser reads. A paused `<audio>` can keep its connection until the 5 s send timeout
  (`WS:265-267`). Browsers also buffer ahead while paused (UNCONFIRMED per browser).
- **(b) Downloads.**
  - `/api/media/download` and `/api/media/download-selected` have no gate at all (`App:7343-7505`).
  - The design keeps Download in the viewer and for a selection (D3, V7, C11).
  - A ZIP of a 4 GB take during a 16-bit take is the heaviest card read Core can do.
  - §0 point 5 ("No playback read touches the card during a take") is then true only of frames.
- **Fix.**
  - (a) `streamFileRangeToClient(fd, path, first, last, hold)` checks the hold between chunks and stops. On a hold, the
    page runs `audio.pause(); audio.removeAttribute("src"); audio.load();` so the connection drops at once.
  - (b) The page disables Download and Download Selected while `playback_hold` is non-empty.
  - Whether Core should also gate the two download routes is a question for Patrik. It changes today's behaviour, and
    Q5 already assumes downloads in a take.

### M4. Playback fills the page cache, which Core's writer keeps empty on purpose

- **Core's writer (CONFIRMED).**
  - It opens each DNG with `O_CLOEXEC` (`Cdng:1748-1751`).
  - It drops the DNG from the cache when done: `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` (`Cdng:1779`).
  - The KB: "Memory traffic alone (dd to tmpfs, no NVMe) costs frames" (`kb:lessons/hardware-log.md:87`).
  - The Pi has 4 GB (`:319`).
- **Effect (PROBABLE, unmeasured).** Playing a 16-bit take at 415 MB/s fills the page cache with clean pages in ~8 s.
  The next take's writes must reclaim them, a source of direct reclaim at take start that `kb:lessons/hardware-log.md:87-88` measured as
  0 for ordinary takes.
- **Fix.**
  - In 48.3 and 48.5: open with `O_RDONLY | O_CLOEXEC`, and call `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` after
    the frame is read. The JPEG lives in the LRU anyway.
  - `O_CLOEXEC` also keeps a forked `zip` or `sudo -n` helper (`App:6355+`, `App:9473`) from holding a frame open
    during an eject.
  - M11 records `grep -E 'allocstall|pgscan_direct' /proc/vmstat` and `free -m` before and after the first take that
    follows a playback session.

### M5. Buffers must belong to the slot, not to the request

- **Where decoding runs.** On the HTTP client thread (§4.7), and the server starts a new detached thread per connection
  (`WS:276-287`). If the scratch is per thread (the touch UI's `static thread_local RawFrame scratchFrame`, `CIP:709`) or
  per call, every frame allocates and faults in ~33 MB again.
- **Host result (CONFIRMED, A.3).** A 16-bit 4K uncompressed frame takes 40.4 ms with a fresh thread and fresh buffers,
  against 24.5 ms with kept buffers: +65 % on the one format that can reach 25 fps. glibc's mmap threshold makes this
  uneven: the 12-bit frame showed no cost here.
- **Missing mechanism.** §2.7 says "after 30 s with no playback request, the workers free their scratch" but names
  nothing that runs after those 30 s.
- **Fix.**
  - `struct DecodeSlot { std::mutex busy; std::vector<uint16_t> samples; std::vector<uint8_t> scratch, rgb; };`, with
    `APERTAR_PLAYBACK_WORKERS` of them.
  - A slot is taken with `try_lock`; if none is free, 503.
  - Trim from the media watcher loop, which already wakes every 1 s (`App:9383`): free the buffers when idle for 30 s or
    when a hold starts. No new thread.

### M6. The movie decoder handle is not thread-safe, and it starts threads

- **Evidence (CONFIRMED).**
  - `Decoder` keeps `lastFrame`, the packet and the swscale context (`VPL:25-44`).
  - `read()` changes them (`VPL:148-216`).
  - `avcodec_open2` runs with `thread_count = 4` (`VPL:128-129`).
- **Problem.** "One open decoder per clip" (53.3) with two slots lets two threads call `read()` on one handle: a data
  race in libav, probably a crash.
- **Why not two handles.** For H.264, a second handle would decode every frame twice, because frames depend on their
  predecessors (`VPL:149`, `:182-183`).
- **Fix.**
  - Give each open decoder a mutex; a second request for the same movie gets 503 (`try_lock`).
  - Open the decoder after `setpriority`, so FFmpeg's 4 threads inherit nice 10.
  - Close it on the idle trim (M5).
  - In 53.2, add `install(TARGETS apertar-video-libav LIBRARY DESTINATION lib/apertar-core)` (as `CMake:190-196`).
  - In 53.3, use the search order of `H264C:17-31`: the environment variable first, then next to the binary, then
    `/home/pi/ApertarCore-build/`. The design lists "next to the binary, then `APERTAR_VIDEO_PLAYBACK_PLUGIN`".

### M7. The touch UI counts empty frames; the design does not

- **Evidence (CONFIRMED).** The touch UI's frame list is every `*.dng`, 0-byte files included (`PC:696-706`;
  `CLM:502`, `:530`). FRAMES, "FRAME i / N" and DURATION count them.
- **The design.** `frame_count` = non-empty frames (§4.2). A pulled take has ~21-23 empty frames
  (`kb:lessons/hardware-log.md:440-460`), so the two screens show different numbers for the same take.
- **Fix.** Add D15 to §2.9: the WebUI skips empty frames and says how many ("+ 23 empty"), with a question and a U-fix
  for the touch UI. It belongs with M1, because both change what FRAMES means.

### M8. Three hold signals wait on the camera's own lock

- **Evidence (CONFIRMED).**
  - `isRecording()`, `state()` and `mediaWritesPending()` each take `CameraController::mutex_` (`CC:9908-9912`,
    `:9868-9872`, `:9844-9848`).
  - `CameraController::stopRecording()` holds that lock across the whole writer drain (`CC:9785-9794` →
    `CameraSession::stopRecording`, `CC:6535-6583`).
  - `startRecording()` holds it across `session_->startRecording` (`CC:9508-9545`).
  - `mediaWritesPending()` does cover the drain (`recordingStopInProgress_`, `CC:6265-6271`), but it cannot be read
    until the drain ends and the lock is free.
- **Consequences.**
  - (a) Walkthrough B's sequence `"recording"`, `"writing"`, `""` will not appear for a video take. Readers block for the
    drain, then see `""`. `"writing"` appears only for still writes. This is harmless (the existing `/api/state` already
    blocks the same way, `App:7859-7864`), but the text is wrong.
  - (b) The per-tile check would take that lock ~17 times per lossless frame, and it blocks during `startRecording`.
    It still aborts afterwards, so this is correct, but it is slow at the moment it matters.
- **Fix.**
  - Add `std::atomic<bool> playbackAbort_`.
  - `handleCommand` sets it at the top, before any camera call, for `record_start`, `capture_photo`, `timelapse_start`,
    `run_media_speed_test` and `enter_standby`. The media watcher sets it on loss. The hold function clears it when the
    hold is gone.
  - The decode checks only the atomic between tiles, so it stops **before** the first frame of the take is written.
  - `buildWebStateJson` computes `playback_hold` from the values it has already read (`App:7860-7870`): one snapshot,
    no second set of locks. Put the rule in a pure function `playbackHoldFor(signals)` that both use.

### M9. A corrupt DNG makes the reader allocate 512 MB before it rejects the file

- **Evidence (CONFIRMED, A.2).**
  - `readDngInfo` checks only that `stripOffset + stripBytes` fits the file (`DngFrameReader.hpp:278-282`).
  - `readDngSamples` then runs `samples.resize(w * h)` (`:305`) before checking `rowBytes × h > stripBytes` (`:308`).
  - With width and height set to 16384: 512 MB allocated. With two slots that is 1 GB on a 4 GB Pi.
  - §4.9's "checks every offset against the file size before allocating" is not true for this buffer.
  - The ASan fuzz cannot see it, because it is a legal allocation.
- **Lossless is safe.** The tile-count check (`:284-289`) rejects the same corruption.
- **Fix.**
  - Move the `rowBytes × h ≤ stripBytes` check into `readDngInfo`.
  - Cap `width × height` at, say, 4096 × 2304 (Core's largest mode is 3856 × 2180, `CC:395`).
  - Add a changed-dimension case to `reader_fuzz`.

### M10. §2.1 does not answer Cinemate's own lesson

- **Evidence (CONFIRMED).** Cinemate's operator turned raw decode off after hardware tests: "raw decode is far more
  demanding on the Pi than serving the embedded thumbnail", with `_RAW_DECODE_FALLBACK_ENABLED = False`
  (`cm:src/module/app/playback.py:227-236`, commit `5124a1d`). r1 §6 #1 and r4 C4 report it.
- **The gap.** The design picks A (decode in Core) against that lesson without saying why it does not apply.
- **Fix (two sentences in §2.1).** Cinemate's decoder is Python/NumPy and handles uncompressed frames only (r1 §2.8).
  Apertar's is C++ and costs the same as the touch UI's path, which already plays these takes (§2.3). T46 M1 confirms it
  on the Pi, and O11 is the way out if it does not.

### M11. Remove would ask twice

- **Evidence (CONFIRMED).**
  - Row 49.7 sends Remove Selected to the existing `deleteSelectedMediaItems` (`Web:10468`), which runs its own
    `window.confirm(...)` (`Web:10476`).
  - The viewer's Remove would reuse `deleteMediaLibraryItem`, which also confirms (`Web:10427`).
  - So the touch-style dialog would be followed by the browser's own confirm box.
- **Fix.**
  - Split the two functions into `postDeleteSelected(items)` and `postDeleteItem(item)`, with no confirm, and call them
    from the new dialogs.
  - Show Core's reply in the status line (B24).
  - `fetchMediaLibrary` drops a call that arrives while another is in flight (`Web:10404-10405`). The "refetch when a
    take ended" must therefore queue, as `fetchState` does (`Web:10257-10261`).

### M12. Network errors are not 503s

- **Evidence (CONFIRMED).**
  - At 32 clients the accept loop `continue`s (`WS:271-272`).
  - The dropped `shared_ptr` shuts the socket and closes it with no reply (`WS:174-178`).
  - `fetch()` then rejects with `TypeError`.
- **What counts.** The 32 include every streaming connection: the MJPEG of other tabs, the WAV stream and ZIP downloads.
- **The page.** §3.6 handles only 409 and 503.
- **The browser.** It allows 6 connections per host over HTTP/1.1 (PROBABLE, standard). Two playing tabs plus a live
  view can queue requests in the browser, which inflates the measured round trip that drives the look-ahead.
- **Fix.**
  - Treat a rejected fetch like a 503: skip the frame and count it.
  - After 3 in a row, back off for 500 ms.
  - Cap the look-ahead at 2 frame periods.

---

## 4. Minor

| # | Point and evidence | Fix |
| --- | --- | --- |
| m1 | F3 says "full-width tiles of 128 rows". Full width only when `width % 16 == 0` (`Cdng:1240-1241`); the 1928, 2028 and 1332 modes write two tile columns. The tile height is tag 323, set by `APERTAR_CDNG_TILE_ROWS` (16-1024, `Cdng:52-67`). The sketch reads all of these bit-exact (A.1) | Correct F3. The hold check interval follows the tag, so it is not always "128 rows" |
| m2 | The uncompressed path reads the whole strip in one `pread` (`DngFrameReader.hpp:312-316`). The "check every 128 rows" (§2.7) is not in the sketch, and neither are the hold callback, the slots or `fadvise` (M4, M5) | 48.3: chunked `pread`s of `tileRows × rowBytes` with the atomic check (M8) between them. Say that the ~600 sketched lines lack these parts |
| m3 | M2's command is wrong. The touch UI's binary is `Apertar-UI` (`UCMake:256-257` `OUTPUT_NAME`; `kb:architecture/ui.md:371`), run from `~/ApertarUI/build` or `~/.cache/apertar-runtime/bin` (`run_pi_direct.sh:13`). `pgrep -f apertar-ui` is case-sensitive and matches nothing, so `top -p ""` fails | `top -b -n 3 -d 2 -H -p "$(pgrep -x Apertar-UI)" \| head -30` |
| m4 | M7 measures RAM. `cat …/*_00000001?.dng` reads the same 10 frames every 0.1 s; after the first pass they are in the page cache, and the drive sees no reads | `( for f in /media/RAW/<old take>/*.dng; do dd if="$f" of=/dev/null bs=4M iflag=direct status=none; sleep 0.1; done ) &` gives ~10 frames/s straight from the drive |
| m5 | The folder button is greyed on `snapshot.recording`, which is `isRecording() \|\| soundRecording` (`App:7864`, `:8000`). Hold #1 also covers a timelapse, so in a timelapse the button stays live and opens onto a hold | Grey it on `snapshot.recording \|\| snapshot.timelapse_active` (`App:8009`), or on `playback_hold === "recording"` |
| m6 | T47 step 4.3 checks `grep -c 'dd MMM yyyy' ClipProbe.hpp`, which would find only a comment: the C++ is `strftime("%d %b %Y  %H:%M")`. Core never calls `setlocale` (no hit in `src/`), so `%b` gives English names | Check for the format string itself. For Q15, "follow the locale" needs `newlocale()` + `strftime_l`, never `setlocale(LC_ALL, "")`, which would change `strtod`/`printf` decimals in Core's config parsing (`sv_SE`: "1,5") |
| m7 | `readWavFormat` (47.2) would be Core's second RIFF parser. `wavDurationTextForFile` already reads the header (`App:5926-5993`) | Extend that one to return format and duration; one parser |
| m8 | A folder holding only `.mp4.writing` + `.wav` is not listed at all today: only `.mp4/.m4v/.mov/.mlv` count (`App:5819-5823`). A pulled H.264 take keeps `.mp4.writing` forever (`CC:4610`, `:4836`). "H.264 take is still being written." is then wrong after a pull | Message "H.264 take was not finalized."; T53 adds `.writing` to the scan |
| m9 | A timelapse can be DNG+JPEG pairs: the still format through `queuePhotoCaptureLocked` (`CC:9740-9760`), base name from `CC:1038-1047`. Today's `frameCount` counts both files (`App:6086-6087`) | 47.2: one frame per stem, the DNG first (as the touch UI's `dngNameFilters`, `PC:696`). For a still pair, decode the DNG (the touch UI takes the first in collator order, `CLM:468-480`) |
| m10 | `APERTARCORE_HAS_JPEG=0` is a supported build (`CMake:128-131`); `/preview.mjpeg` answers 503 there (`App:7262-7266`) | `PlaybackFrames` compiles out the same way; `/api/media/frame` answers 503 "JPEG support was not compiled in." |
| m11 | `LANGUAGES C CXX`: `-Wall -Wextra -Wpedantic` and Release `-mtune=native` are target-wide (`CMake:175-188`) and also apply to `lj92.c` | Nothing to change: `lj92.c` is warning-free here. Say so in 48.2 so a C warning on the Pi is not a surprise |
| m12 | `audio.currentTime` advances in coarse steps in some browsers (UNCONFIRMED per browser). The touch UI loops at the **WAV's** duration (`PC:834-846`), not at frames ÷ fps | Interpolate between `currentTime` samples with `performance.now()` while playing; resync on `seeked`/`timeupdate`. State which end wins when WAV and picture differ (M1 changes that) |
| m13 | Keep-awake every 20 s against a shortest standby of 30 s (`Web:3780`): fine today | Ping every `min(20 s, standby_timeout_seconds / 3)` (`App:7997`) |
| m14 | A frame read in flight when the NVMe goes away can block its HTTP thread in D state for the device timeout. The slot stays taken, and `WebServer::stop` waits for every client thread (`WS:247-250`). Today's download route has the same exposure | New R16. Never hold the LRU or facts-cache mutex while reading the card: scan outside the lock and swap the result in under it. Otherwise `/api/media`, which must answer from cache in a hold, blocks behind a stuck scan |
| m15 | `X-Histogram` as 48 integers 0-255 equals the touch UI's bins only to within 1/255 | Say "match to 1/255", or send 3 decimals |
| m16 | The touch UI clamps cDNG playback fps to 1-60 (`PC:621`), while its card uses the file's rate unclamped (`CLM:153`) | State whether the WebUI clamps the badge and the clock (parity) or not, and add a D-row |
| m17 | The touch UI also lists movies copied to the media root (`CLM:540-556`); Core lists folders only (`App:6443-6497`) | List it in §2.9 as a known gap |
| m18 | The touch UI's linearization rejects an out-of-range sample (`DD:734`); the copy clamps to the last entry (`DngFrameReader.hpp:366-367`). The two differ only on corrupt files | A comment in the copy, so the parity test does not flag it later |
| m19 | `/api/media/clip` and the routes read `kind`/`id`, then call `resolveMediaLibraryPath`, which stats the root and the candidate (`App:5790-5805`). §3.7's order has the hold first, which is right | Keep that order in code: the hold before any validator that stats |
| m20 | The 409 body carries `"hold"` beside `"error"`; `errorReply` takes only a message (`App:122-130`) | A small `holdReply(reason, text)` |

---

## 5. Citations and wording

| # | Design says | Code says | Fix |
| --- | --- | --- | --- |
| w1 | Sort rule at `CLM:287-299` | That is `setSortMode`; the sort is `CLM:559-568` | correct the anchor |
| w2 | "KB rule M5: name every copy and give it a check" (`kb:llm/README.md:102-106`) | M5 is defined at `kb:llm/tutoring.md:70` ("Copies … one change, several places"); `README.md:102-104` is the note that state is copied by hand. "Give it a check" is the design's own addition | cite `tutoring.md:70` and call the check the design's rule |
| w3 | §4.5 "`pread` in 64 KiB chunks (the `streamFileToClient` pattern)" | `streamFileToClient` uses `std::ifstream::read` (`App:6333-6348`) | "64 KiB chunks as `streamFileToClient`; `pread` is new" |
| w4 | F17 "Only commands count as activity" | Only `user_activity`, `wake`, `set_*`, `capture_photo`, `record_*` and `timelapse_*` (`App:9508-9514`) | name them |
| w5 | F14 "can read without the command lock" | True, but three of them take `CameraController::mutex_` (M8) | add the caveat |
| w6 | F8 lists the limits | Add: a 33rd connection is closed with no reply (`WS:271-272`, M12) | |
| w7 | Walkthrough B: `"recording"`, then `"writing"`, then `""` | `"writing"` shows only for still writes (M8) | reword |
| w8 | "plugin missing" quotes `VP:35` as "Video playback decoder unavailable." | The full string ends "Build apertar-video-libav (libswscale-dev required)." | say it is shortened |
| w9 | KB at `e8eeef2`; "this pass wrote nothing into the KB" | The KB's autosaves `457ad0d` and `9bf388f` committed `working/playback/` (the design file is identical) | note the autosave |

Checked and correct (CONFIRMED):

- **Facts.** F1, F2, F4, F5, F6 (pattern at `CC:4205-4208`), F8 apart from w6, F9, F10, F11, F12, F13 (`CC:3483`,
  `:4182-4194`, `:4610`), F15, F16, F18 (`App:7098`, `App:8278-8283`), F19, F20, F21 (step 22 at `DD:492`, sampling from
  0,0 when there is no active area), F22, F23, F25, F26, F27, F28 and F29.
- **Touch UI flow.** `CamP:3754`, `Main:319-322`, `Main:417-467`, `PC:550-571`, `PC:619-636`, `PC:714-720`,
  `PC:749-775`, `PC:827-857`, `PC:861-901`, `CPP:168-180` and `CPP:393-398` read as the design says. "SINGLE FRAME" for
  stills is `PC:1196`, upper-cased at `CPP:455`.
- **Web server.** Custom headers go through `Response::headers`, and a handler can read the `range` header from
  `Request::headers` (`WS.hpp:18-34`, `WS:95-112`, `WS:135-136`, `WS:150-151`). C3 ("no header-code change") is
  therefore right.

---

## 6. What the frame path costs on the Pi 5, idle and in a take

The host numbers are from my re-run (§1). The Pi factor is the design's ~2× (PROBABLE). The Cortex-A76 at 2.4 GHz may be
closer to 1.5× on the compute part, and slower on memory bandwidth. T46 M1 settles it.

| Path | Host, one thread | Pi (PROBABLE) | What the design misses |
| --- | --- | --- | --- |
| HDR16 uncompressed, 640 w | 24-26 ms with kept buffers; 40 ms with fresh ones | 50-80 ms + a cold read of 16.6 MB (24-40 ms) | M5 buffers; M4 page cache. 2 workers want 415 MB/s: 437 MB/s was fio **writes** at QD32 (`kb:lessons/hardware-log.md:321`); buffered reads at ~QD2 will likely be lower, so expect a read-bound 15-25 fps (M8 measures) |
| SDR12 lossless, 640 w | 154-161 ms | 250-450 ms | 2 workers give ~5-8 fps shown, as designed. Reads ~40-60 MB/s |
| Per request, constant | tail read 1.4-9.8 KB; thread spawn ≪ 1 ms; JPEG 640 w ~0.5 ms, 960 w 1.3 ms | ×2 | the 33rd connection (M12) |
| Paused 1920 w | 155-309 ms | 0.3-0.6 s | none |
| **In a take, as designed** | frames, thumbnails and new WAV requests answer 409 | ~0 | **leaks:** a running WAV stream (M3a), `/api/media/clip` (M2), every Download (M3b) |
| **In a take, with M2-M4 and M8 fixed** | a 409 costs ≪ 1 ms; `/api/state` 1/s per tab (as today) | ~0 card reads | a decode in flight stops before the take's first frame (M8) |
| **The first take after a playback session** | — | page cache full of clean DNG pages (PROBABLE) | M4 `DONTNEED`; M11 `/proc/vmstat` |

---

## 7. Plan rows to add or change

| Row | Change |
| --- | --- |
| 47.0 (new) or 47.1 | B2: liblj92, `LANGUAGES C CXX` and the include directory move to T47, or part 1 is split into `DngTags.hpp` without lj92 |
| 47.2 | M1: frame numbers, gaps and the span duration; M7: empty frames reported; m7: reuse `wavDurationTextForFile`; m9: one file per stem |
| 47.4 | B2: no cache member in `App.hpp`; M8: `std::atomic<bool> playbackAbort_` |
| 47.5 | M8: `playbackHoldFor(signals)`, a pure function; the state builder passes the values it already read |
| 47.9 | M2: hold first in `/api/media/clip`; in a hold, answer from the cache |
| 47.11 (new) | M8: `handleCommand` sets `playbackAbort_` at the top for the five commands (search `std::lock_guard<std::mutex> commandLock(commandMutex_);`, `App:9485`) |
| 48.3 | m2: chunked `pread`s with the atomic check; M4: `O_CLOEXEC` + `POSIX_FADV_DONTNEED`; M9: dimension and strip checks before any allocation |
| 48.5 | M5: `DecodeSlot` with its own buffers; trim from the media watcher (`App:9383`); m10: build without JPEG |
| 48.7 | M1: the `n=` parameter, `X-Frame-Number`; m20: `holdReply` |
| 49.2b (new) | B1: `installInteractions` wiring (`Web:11396-11411`, `Web:11610-11613`) |
| 49.7 | M11: confirm-free `postDeleteSelected`/`postDeleteItem`; `fetchMediaLibrary` queues |
| 49.8 | m5: grey the folder button in a timelapse too |
| 50.3 | M12: network error = skip, back-off, look-ahead cap; m12: interpolated audio clock; M3: Download disabled in a hold |
| 51.1/51.2 | M3a: hold check between chunks; the page drops `src` on a hold |
| 53.2/53.3 | M6: mutex per decoder, decoder opened after `setpriority`, install rule, H264C search order |
| T46 M2, M7 | m3, m4: corrected commands |
| T48/T50 gates | B1: no `pageerror` at load in the mocked Chromium; A.1 sizes test and the A.2 corrupt case in the reader gate; `hostcheck-core.sh` with `-I third_party/liblj92` |

---

## Appendix A. Scratch tests (sources; their folder is deleted)

Built from `scratchpad/playback/` with the sketch's lines. `CORE` is `scratchpad/controls/core-tip`, `SK` is
`sketch/`. `lj92.o` comes from `gcc -O2 -c $SK/third_party/liblj92/lj92.c`.

### A.1 Sizes test (24 of 24 bit-exact)

```cpp
// g++ -std=c++20 -O2 -I$SK/src/playback -I$SK/third_party/liblj92 -I$CORE/src -I$CORE/include sizes_test.cpp \
//   $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp \
//   lj92.o -lyaml -lpthread -o sizes_test && ./sizes_test /tmp/frames
#include "DngFrameReader.hpp"
#include "RawRender.hpp"
#include "cdng/CdngEncoder.hpp"
#include <cstdio>
#include <random>
#include <fcntl.h>
using namespace apertar::playback;
int main(int argc, char **argv) {
    const std::string dir = argc > 1 ? argv[1] : "/tmp";
    struct Size { uint32_t w, h; } sizes[] = {{1928,1090},{2028,1520},{2028,1080},{1332,990},{3856,2180},{1920,1080}};
    int fails = 0; apertar::CdngEncoder enc; std::mt19937 rng(1);
    for (auto sz : sizes) for (unsigned bits : {12u, 16u}) for (int lossless = 0; lossless < 2; ++lossless) {
        std::vector<uint16_t> s(size_t(sz.w) * sz.h);
        for (auto &v : s) v = uint16_t(rng() % (1u << bits));
        apertar::RawFrameView view;
        view.data = reinterpret_cast<const uint8_t *>(s.data()); view.size = s.size() * 2;
        view.width = sz.w; view.height = sz.h; view.stride = sz.w * 2;
        view.bitDepth = bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
        view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
        view.bayerPattern = apertar::BayerPattern::RGGB;
        apertar::CdngEncoder::Metadata meta;
        meta.compression = lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
        meta.fps = 50.0; meta.clipName = "t"; meta.frameFileName = "t_000000000.dng";
        char name[256]; std::snprintf(name, sizeof name, "%s/s_%ux%u_%u_%s.dng", dir.c_str(), sz.w, sz.h, bits, lossless ? "lj" : "unc");
        enc.writeDngFile(name, view, meta);
        int fd = ::open(name, O_RDONLY | O_CLOEXEC);
        DngInfo info; std::string err; std::vector<uint16_t> back; std::vector<uint8_t> scratch;
        bool ok = readDngInfo(fd, info, err) && readDngSamples(fd, info, back, scratch, err); ::close(fd);
        bool same = ok && back == s;
        std::printf("%s tiles %ux%u x%zu read %s bit-exact %s %s\n", name, info.tileWidth, info.tileLength,
                    info.tileOffsets.size(), ok ? "ok" : "FAIL", same ? "yes" : "NO", err.c_str());
        if (ok) (void)renderPreview(info, back, 640);
        fails += !same;
    }
    std::printf(fails ? "FAILURES %d\n" : "sizes ok\n", fails);
    return fails != 0;
}
```

### A.2 Corrupt dimensions (512 MB before refusal)

```python
# python3 -I patch.py sketch/frames/sdr12_uncompressed.dng /tmp/huge_dims.dng
import sys, struct
b = bytearray(open(sys.argv[1], 'rb').read())
off = struct.unpack_from('<I', b, 4)[0]
for i in range(struct.unpack_from('<H', b, off)[0]):
    p = off + 2 + i * 12
    if struct.unpack_from('<H', b, p)[0] in (256, 257):
        struct.pack_into('<I', b, p + 8, 16384)
open(sys.argv[2], 'wb').write(b)
```

```cpp
// one_read.cpp: readDngInfo + readDngSamples once, then getrusage(RUSAGE_SELF).ru_maxrss
// Result: info=1 samples=0 err='Strip is shorter than the image.' 16384x16384 maxrss=515 MB (good frame: 30 MB)
```

### A.3 Per-request buffers (HDR16 unc 40.4 ms fresh against 24.5 ms kept)

```cpp
// alloc_bench.cpp: per frame open + readDngInfo + readDngSamples + renderPreview(640) + rawHistogram,
// 7 times on a new std::thread with new vectors, against 7 times with vectors kept; medians printed.
```
