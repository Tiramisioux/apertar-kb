# Changes from the critiques: design-playback v1 → v2

2026-10-29, designer pass v2. One row per critic point. Each row says whether the point was **accepted**, **changed**
(accepted, but with a different fix or corrected evidence) or **rejected**, why, and where it landed in
`design-playback.md` (v2).

I checked every point against the code before accepting it, at Core `eb9cc39` (`scratchpad/controls/core-tip`), touch UI
`d8098d0` (`scratchpad/controls/ui-tip`), Cinemate `d6cc93e` and the KB (`b137ae8`; HEAD `11dad27`). "Checked" below means I
opened the line or ran the command in this pass. Where I ran something, the run is named; the outputs are in
`sketch/v2-*-host.txt`.

Sources: `critique-code.md` (CC), `critique-operator.md` (CO), `design-playback-v1.md` (v1), `design-playback.md` (v2).

## 0. Summary

| | Code critique | Operator critique |
| --- | --- | --- |
| Rows below (points and sub-points, measurements, risks, questions, options, plan rows) | 67 | 67 |
| Accepted | 57 (m11 needs no change) | 55 |
| Changed (accepted with a different fix, or with corrected evidence) | 9 (M1d, M3b, M5, M7, M8, M9, m15, rows 47.4 and 47.11) | 9 (P5, P12, P15a, P16b, P20, P21b, Q20, Q27, the R-mapping) |
| Rejected | 0 | 3 (P6b "PLAYING · NO SOUND"; P7c Wake Lock over plain HTTP; P7d the 500 ms long press) |
| No change needed | 1 (the critic's "checked and correct" list) | 0 |

What I ran to check them (this host, nothing on the Pi):

- **Sketch v2, `v2_test`: 38 of 38.** New headers `DngTags.hpp`, `ClipFrames.hpp`, `PlaybackHold.hpp`,
  `DecodeSlots.hpp`; the reader split in two and given chunked reads, a stop callback and the page-cache drop.
- **Page sketch `page/playclock_test.js`: 16 of 16** (node 22).
- **Reproduced the code critic's runs:** B2 (`lj92.h: No such file` without the include path); M9 on the v1 reader (515 MB
  max RSS on a 16384² lie); A.3 on the v1 reader (16-bit 4K on a new thread: 37-43 ms with fresh buffers, 23-25 ms kept);
  A.1 (24 of 24 sizes, on the v2 reader).
- **The v1 checks on the v2 reader:** bench 36 of 36, parity 6 frames with 0 differences, fuzz 640 runs under ASan/UBSan
  with no report, plus 20 size lies all refused by `readDngInfo` (max RSS 47 MB).
- **Inside Core:** the T47 headers force-included into `ApertarCoreApp.cpp` with Core's warning flags, libcamera on and no
  liblj92 path: 0 diagnostics; the T48 set with the path: 0.
- **Anchors:** 79 tutor `ref` lines (each once at its line) and 14 `check` lines (through `tutorial.py`'s own
  `tutor_block()` and `unsafe_reason()`): 0 problems; 47 plan search strings: each once, except the two rows that say so.

**Three critic claims were wrong in their evidence or fix, though the conclusion stands:**

- **CC M9's cap** of 4096 × 2304 would refuse real frames: Core writes the IMX477's 4056 × 3040
  (`CC:417`, `CC:471-472`). v2 caps at 4096 × 3072 and the sizes test passes a Core-written 4056 × 3040 frame.
- **CC row 47.11's search string** `std::lock_guard<std::mutex> commandLock(commandMutex_);` occurs twice (`App:9355`, in the
  media watcher, and `App:9485`). v2 anchors on `std::string ApertarCoreApp::handleCommand(const ControlCommand &command)`.
- **CC M8's fix** (a bool set by `handleCommand`, cleared by the hold function "when the hold is gone") lets a request that
  arrives after the command starts but before `recording_` is true clear the flag and read during the take. v2 uses a
  time window, extended by the media watcher while any hold lasts (`v2_test` hold, 8 checks).

**Three operator fixes were rejected:**

- **Wake Lock** (P7): `navigator.wakeLock` exists only in secure contexts, and the WebUI is plain HTTP on port 8000. v2
  feature-detects it and offers O20 (the muted inline-video trick) instead.
- **Long press 500 ms** (P7): with the callout switched off (`-webkit-touch-callout: none`, `contextmenu` prevented), the
  system menu no longer fires first, so the touch UI's 800 ms can stay.
- **"PLAYING · NO SOUND"** (P6): the SOUND row says why there is no sound; the badge keeps the touch UI's words.

**v1 → v2 tutorials.** T46-T53 keep their topics; **T54** is new (the touch UI yields to a take and keeps time, U2 + U9,
recommended). Size ~2,960 → ~3,900 lines; the sketch ~600 → ~1,150 lines of product code.

---

## 1. Code critique (`critique-code.md`)

### Blockers

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| B1 replacing `#mediaBrowserOverlay` kills the page script | **accepted** | `installInteractions()` wires seven old ids with no null check (`Web:11397-11407`), the filter buttons (`Web:11409`) and the overlay click (`Web:11610-11613`); it runs at top level before `installPreviewStream()` and the poll (`Web:11649-11653`). `setMediaBrowserOpen` also toggles the overlay with no null check (`Web:6181`), which the critic did not list | row 49.3 (new), 49.5 (`Web:6181`), 49.7 (the three helpers that silently do nothing); T49 gate fails on any `pageerror` and checks `#previewStream` has a `src`; F35; R8 |
| B2 T47 does not compile (`lj92.h` arrives in T48) | **accepted**, option (b) | `sketch-v1/src/playback/DngFrameReader.hpp:24-26`; reproduced: `fatal error: lj92.h`. Split: `DngTags.hpp` (T47, no lj92) and `DngFrameReader.hpp` (T48). With the split, the T47 set inside App: 0 diagnostics | rows 47.1, 48.3; cache not a member of `App.hpp` (47.6, §4.7); `hostcheck-core.sh` gains the include path and two files (48.10) |

### Major

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| M1a sound and picture drift on takes with holes | **accepted** | numbering by time `CC:3780-3787`; the WAV spans first to last frame + one period (`Audio:367-385`, `:606-626`); the touch UI maps time to a position (`PC:849-851`). Host arithmetic (`v2_test` drift): 208 of 250 files, the picture 1.04 s ahead at 5 s, the last file at 8.32 s; the number clock never ahead, ≤ 0.08 s behind | §0.4, §2.6, `ClipFrames.hpp`, `playclock.js`; `/api/media/frame?n=`; F5, F30; walkthrough D |
| M1b durations short | **accepted** | all three duration texts divide the file count (`CLM:530-534`, `PC:1200`, `App:6492`) | DURATION = span ÷ fps (§4.2, §4.3); D15; U9 in T54 |
| M1c same flaw in the touch UI and Cinemate | **accepted** | `PC:849-851`; `cm:src/module/app/playback.py:265` | U9 in T54 (rows 54.4-54.5) |
| M1d "FRAME i / N": timeline numbers or file positions — a question | **changed**: decided, no question | the touch UI shows the position among the files; the operator critic (P1) asks to keep it. v2: i = the position of the frame on screen (`X-Frame-Index`), N = the file count | V3, §4.4 |
| M2 `/api/media/clip` reads the card with no hold | **accepted** | v1 §4.1 listed only 404/400 for the route; it scans the folder, reads a tail and the WAV header | the hold first; in a hold from the cache with `held`, or 409 (row 47.14, §2.7 table, §4.1) |
| M3a a running WAV stream keeps reading | **accepted** | `streamFileToClient` checks nothing per chunk (`App:6333-6348`); the 5 s send timeout (`WS:265-267`) | the range streamer asks the yield window between chunks; the page drops `src` (§2.6, row 51.1, 51.3) |
| M3b downloads are not gated | **changed** (the operator's stronger fix) | `App:7343-7505`: no recording check; ZIP from a forked `zip -0` with no `Content-Length` (`App:6355-6420`). The critic proposed disabling the buttons and asking; v2 has Core refuse new downloads in a hold and stop running ones (the operator's P3), as a default you can overrule (Q21) | rows 50.8, 50.9; §2.7 table; §4.8 texts; R17 |
| M4 playback fills the page cache the writer keeps empty | **accepted** | writer: `O_CLOEXEC` (`Cdng:1748-1751`), `POSIX_FADV_DONTNEED` (`Cdng:1779`); KB: memory traffic costs frames, direct I/O does not (`kb:lessons/hardware-log.md:87`). Host (`v2_test` cache, `mincore`): v1 reader leaves 100 % of a frame cached, v2 0 % | `openDngFrame`/`closeDngFrame`, per-chunk drop (47.1, 48.3); M11 and M16 record `/proc/vmstat` and `free` |
| M5 buffers must belong to the slot | **changed** (evidence refined) | reproduced A.3 on the v1 reader: 37-43 ms fresh vs 23-25 ms kept (16-bit 4K). On the v2 reader the gap is mostly gone (22.9 vs 21.8 ms), because chunked reads no longer allocate a 16.6 MB scratch per frame. Slots with their own buffers are still adopted: bounded memory, one place to trim | `DecodeSlots.hpp` (48.5); trim from the watcher loop `App:9383` (48.9); §4.7 |
| M6 the movie decoder handle is not thread-safe | **accepted** | `Decoder` keeps packet, frame, swscale context, `lastFrame` (`VPL:25-44`); `read()` changes them (`VPL:148-216`); `thread_count = 4` (`VPL:128-129`); install rules exist for the two encoder plugins (`CMake:190-196`); `H264C:17-31` search order checked | row 53.3: a mutex per decoder (503 on contention), opened after `setpriority`, closed by the idle trim; 53.2 install rule; F10, F12 |
| M7 the touch UI counts empty frames; the design did not | **changed** | `PC:696-706` (no size filter), `CLM:502`, `:530`. Instead of adding a difference, v2 removes it: FRAMES and N count 0-byte files as the touch UI does; the picture holds over them (D22), DROPPED says how many | §2.4 table, §4.2 `frame_count`, `ClipFrames.hpp` |
| M8 three hold signals take the camera's mutex; "writing" not seen for video | **changed** (different fix) | `CC:9844-9848`, `:9868-9872`, `:9908-9912`; `stopRecording()` holds `mutex_` across the drain (`CC:9785-9798`), `startRecording` across the session start (`CC:9508-9545`). Fix: the pure rule `playbackHoldFor()` (as the critic proposed) and a **time window** instead of a flag cleared by the next request (race above); the watcher extends it while a hold lasts, so streams that check only the atomic stop for a take begun while their client was stalled | `PlaybackHold.hpp`; rows 47.3, 47.7-47.9, 47.15; §2.7; F32; walkthrough B text; R24 |
| M9 a corrupt DNG makes the reader allocate 512 MB | **changed** (the cap) | reproduced: 515 MB max RSS on the v1 reader. The critic's 4096 × 2304 cap would refuse IMX477 4056 × 3040 frames (`CC:417`, `:471-472`). v2: 4096 × 3072 and the strip check moved into `readDngInfo`; 20 size lies refused before any buffer, 47 MB max RSS; Core-written 4056 × 3040 and 3840 × 2200 frames pass bit-exact | `DngTags.hpp`; fuzz size lies; §4.9; F37 |
| M10 §2.1 does not answer Cinemate's lesson | **accepted** | `cm:src/module/app/playback.py:227-236`, commit `5124a1d`; the decoder is NumPy + Pillow (`dng_preview.py:43`) and refuses compression ≠ 1 (`:488`) | §0.2, §2.1 |
| M11 Remove would ask twice | **accepted** | `window.confirm` at `Web:10427` and `Web:10476`; `fetchMediaLibrary` drops a call in flight (`Web:10404-10405`); `fetchState` queues (`Web:10257-10261`) | row 49.8; B23; §3.6 "Library fetch" |
| M12 a 33rd connection is closed with no reply | **accepted** | `WS:271-272` (`continue`), `WS:174-178` (shutdown and close in the destructor) | a rejected fetch = a 503 for the lane; back-off; look-ahead cap 2 frames (§2.2, `playclock.js laneAfter`, tested); F8 |

### Minor

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| m1 F3 "full-width tiles of 128 rows" | **accepted** | `Cdng:1240-1241` (two columns when `width % 16 != 0`), `Cdng:52-67` (16-1024 rows) | F3; the stop check runs per tile, whatever its height |
| m2 the sketch had no chunked read, hold callback, slots or `fadvise` | **accepted** | `sketch-v1/…/DngFrameReader.hpp:312-316` (one `pread`) | v2 sketch has all four, tested (`v2_test` stop, cache, slots) |
| m3 M2's `pgrep -f apertar-ui` matches nothing | **accepted** | `OUTPUT_NAME "Apertar-UI"` (`UCMake:256-257`); `run_pi_direct.sh:5` runs `build/Apertar-UI` | M2 uses `pgrep -x Apertar-UI` |
| m4 M7 measures RAM, not the drive | **accepted** | the same ten files are cached after the first pass | M7 uses `dd … iflag=direct` over every frame |
| m5 the folder button stays live in a timelapse | **accepted** | `recording` = camera or sound only (`App:7864`, `App:8000`); `timelapse_active` separate (`App:8009`) | row 49.9; §2.7; §3.4 |
| m6 the date check finds a comment; `%b` and the locale | **accepted** | no `setlocale` in Core's `src/` (grep) | check 4.4 greps the format string; §4.3 `newlocale` + `strftime_l` if Q15 |
| m7 a second RIFF parser | **accepted** | `wavDurationTextForFile` (`App:5926-5993`) | row 47.11 splits it; §2.6 |
| m8 `.mp4.writing` folders are not listed; the message is wrong after a pull | **accepted** | `hasClipContainerExtension` (`App:5819-5823`); `.mp4.writing` kept on a dead mount (`CC:4610`, `CC:4836`) | row 53.4; "H.264 take was not finalized."; F13 |
| m9 DNG + JPEG timelapse pairs counted twice | **accepted** | `mediaStatsForPath` counts every still extension (`App:6086-6087`); timelapse base names (`CC:1038-1047`) | one frame per stem, the DNG first (`ClipFrames.hpp`, `v2_test` frames) |
| m10 a build without JPEG support | **accepted** | `CMake:128-131`; `/preview.mjpeg` 503 (`App:7262-7266`) | row 48.6; §4.4; §4.8 |
| m11 C flags reach `lj92.c` | **accepted** (no change needed) | `CMake:175-188`; `lj92.c` warning-free here | noted in row 48.2 |
| m12 coarse `currentTime`; the touch UI loops at the WAV's end | **accepted** | `PC:834-846` | `makeAudioClock` (interpolation, tested); §2.6 |
| m13 keep-awake vs a 30 s standby | **accepted** | `Web:3780` (30 sec is the shortest) | min(20 s, timeout ÷ 3), tested |
| m14 a read stuck on a dead NVMe holds its slot; no lock across a card read | **accepted** | `WS:247-250` (`stop()` waits for every client) | R16; §2.7 "no lock is held across a card read"; "Waiting for the media to answer…" |
| m15 `X-Histogram` 0-255 is only within 1/255 | **changed** | true; instead of saying so, v2 sends 0-1000 integers | §4.4, V9 |
| m16 the touch UI clamps playback fps to 1-60 | **accepted**, decided | `PC:619-621` clamp; `CLM:153` unclamped | D18: the file's rate everywhere |
| m17 the touch UI lists movies at the media root | **accepted** | `CLM:540-556` | D20, a known gap |
| m18 linearization reject vs clamp | **accepted** | `DD:734` | the comment is in the v2 reader |
| m19 the hold before any validator that stats | **accepted** | `resolveMediaLibraryPath` stats (`App:5790-5805`) | §2.7 rules, §4.1, row 47.14 |
| m20 `errorReply` takes only a message | **accepted** | `App:122-130` | `holdReply` (row 48.8, §4.1) |

### Citations and wording

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| w1 sort anchor | **accepted** | `CLM:287` is `setSortMode`; the sort is `CLM:559-568` | §4.2 |
| w2 KB rule M5 | **accepted** | `kb:llm/tutoring.md:70` defines M5; "a check" is this design's rule | §2.4 |
| w3 `streamFileToClient` uses `ifstream` | **accepted** | `App:6333-6348` | §4.5 |
| w4 F17 names the activity commands | **accepted** | `App:9508-9514` | F17 |
| w5 F14 caveat | **accepted** | as M8 | F14 |
| w6 F8 the 33rd connection | **accepted** | `WS:271-272` | F8 |
| w7 walkthrough B "writing" | **accepted** | as M8 | walkthrough B |
| w8 the plugin-missing text is shortened | **accepted** | `VP:35` | §4.8 uses the full string |
| w9 KB autosaves | **accepted** | `git log`: `c108731`, `11dad27` touch only `working/playback/` | the trees table |

### The critic's cost table (§6) and plan rows (§7)

| Point | Verdict | v2 |
| --- | --- | --- |
| §6 Pi factor maybe 1.5× on compute; 437 MB/s is a write figure at QD32 | **accepted** | §2.3, §2.8, F25: "perhaps read-bound at 15-25 fps"; M8 |
| §6 in-take leaks (WAV, clip, downloads) | **accepted** | §2.7 table; §2.8 |
| Row 47.0/47.1 (B2) | **accepted** | 47.1 + 48.3 split |
| Row 47.2 (M1, M7, m7, m9) | **accepted** | 47.2, 47.4, 47.11 |
| Row 47.4 (no cache member; `playbackAbort_`) | **changed** | 47.6: two yield atomics instead of the bool |
| Row 47.5 (pure function) | **accepted** | 47.3, 47.7, 47.15 |
| Row 47.9 (M2) | **accepted** | 47.14 |
| Row 47.11 (`handleCommand` sets the flag; its search string) | **changed** | 47.8, anchored on the function line (the critic's string occurs twice) |
| Row 48.3 (chunks, `fadvise`, M9) | **accepted** | 47.1, 48.3 |
| Row 48.5 (slots, trim, no-JPEG) | **accepted** | 48.5, 48.6, 48.9 |
| Row 48.7 (`n=`, `holdReply`) | **accepted** | 48.8 |
| Row 49.2b (B1) | **accepted** | 49.3 |
| Row 49.7 (M11) | **accepted** | 49.8 |
| Row 49.8 (m5) | **accepted** | 49.9 |
| Row 50.3 (M12, m12, Download in a hold) | **accepted** | 50.3, 50.4 |
| Rows 51.1/51.2 (M3a) | **accepted** | 51.1, 51.3 |
| Rows 53.2/53.3 (M6) | **accepted** | 53.2, 53.3 |
| T46 M2, M7 (m3, m4) | **accepted** | §8 |
| T48/T50 gates (B1, sizes, the A.2 case, hostcheck) | **accepted** | T48 step 4.7, T49 gate, 48.10 |
| "Checked and correct" list | no change | — |

---

## 2. Operator critique (`critique-operator.md`)

### Problems P1-P25

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| P1 drift on takes with dropped frames (both screens) | **accepted** | as CC M1; KB: 37-45 of 250 lost at 25 fps lossless (`kb:lessons/hardware-log.md:104-108`), one hole every 5-9 (`:165`); `v2_test` drift | the number clock (§2.6), `holes` in the clip JSON, `n=` route, span DURATION; U9 in T54; D15; M12 clap test; walkthrough D |
| P2 ramp takes cut short and out of sync | **accepted** | KB: count numbering, start-rate `FrameRate`, real-time WAV, `fps-ramp.txt` (`kb:working/ramp-ladder/README.md:29`, `kb:working/ramp-answer.md:14`, `:77`, `:92`); T31 is **not** on `eb9cc39` (grep `fps_ramp`: 0), so the rule is written against the T31 patch and switches on only when `fps-ramp.txt` exists | §2.5, §2.6, §4.3 `ramp`, D21, walkthrough G, O3b, U10, Q30; `playclock.js` ramp check |
| P3 downloads and the WAV stream read the card in a take | **accepted** (a)-(d) | `App:7343-7360` no gate; `streamFileToClient` (`App:6333-6347`); a cut ZIP has no `Content-Length` (`App:6355-6420`) | §2.7 table (refuse, stop per chunk, end the `zip` child, toast); rows 50.8, 50.9, 51.1; Q21 default yes; M15 |
| P4 the camera's own screen has no hold | **accepted** as T54 | `CamP:3754` greys only the button; `Main:319-322` not gated; `Main:511-516` only cancels a power-off warning; no `recording` in `PlaybackController` | T54 rows 54.1-54.3; §5; Q22 default yes; R18 |
| P5 lossless looks worse than it is; skips vs drops | **changed** | true (`kb:lessons/hardware-log.md:108`, `:113`). Patrik's brief keeps Cinemate's features as options, so O4 and O5 stay options, both recommended; the take's own drops are a fact about the file, so DROPPED is a default metadata row (D16) | D16, O4, O5, Q24 |
| P6a no sound row; four meanings of silence | **accepted** | v1 §4.3 had `has_audio`/`audio_text` but the screens did not show them; pulled takes leave `audio_capture.raw` (`kb:lessons/hardware-log.md:447`, `:457`) | SOUND row (D16, §4.3 `extra`), "SOUND ONLY" stage (V21) |
| P6b "PLAYING · NO SOUND" badge | **rejected** | the SOUND row says why; the badge keeps the touch UI's words (parity rule) | — |
| P7a no `pushState`/`popstate` | **accepted** | grep `Web`: none | D19; rows 49.3, 49.5 |
| P7b long-press callout | **accepted** (callout off) | standard browser behaviour (PROBABLE); grep: no `-webkit-touch-callout`, no `contextmenu` | D4, B15, B22, row 49.1 |
| P7c Wake Lock while playing | **rejected** | the Screen Wake Lock API is secure-context only; the WebUI is `http://<pi>:8000` (F39). Used where it exists; O20 for the rest; R21 | §3.6, O20 |
| P7d long press 500 ms | **rejected** | with the callout off the conflict is gone; 800 ms is the touch UI's (Qt) value | D4 |
| P7e `touch-action: none` on the scrub | **accepted** | existing CSS uses `pan-y` elsewhere (`Web:1108`, `:1191`) | V2, row 50.1 |
| P8 the square sizes do not fit a phone | **accepted** | `square` = 720 × 720 (r2 §3.1); stacked Remove 132, histogram 152 (r2 §3.2); the card name elides right (`CBP:755`), the date middle (`CBP:774`) | §3.5 phone rows and header, middle elide (`playclock.js middleElide`, tested), 390 × 844 / 844 × 390 gate screenshots |
| P9 Download beside Remove | **accepted** | v1 sketches; no auth (r4 K21) | V5, V7, D3, §4.9 |
| P10 a remote delete silently opens another clip | **accepted** | v1 §3.6 reopened by index on any 404 | `gone` (§4.4), reopen by id (§3.6), walkthrough H |
| P11 long takes: coarse scrub; Download and Remove give no feedback; delete vs record | **accepted** | `remove_all` inside the request (`App:7683`); the gate only at the start (`App:7660-7666`) | D17 time readout; O1, O10 recommended; size confirmation; "Removing…"; Q23 `mediaDeleteActive_` (row 50.7) |
| P12 H.264 through the plugin stutters; `<video>` by default | **changed** | the seek-back rule is real (`VPL:149`), GOP = round(fps) (`src/video/LibavH264EncoderPlugin.cpp:140`), 2560 × 1440 (`CC:1053-1054`). But with one request in flight per movie and in order (CC M6's mutex), playing decodes each frame once; only scrubs pay a GOP. v2 keeps the plugin (one path, exact frame numbers, the hold rule) and measures first (M19); O12 if it is slow | §2.5, row 53.3, M19, O12, Q27 "decide after M19" |
| P13 the MLV of a pulled take is unplayable | **accepted** as an option | `MLR:176-177`; Core patches the count at close (r3 §2.4) | O21, Q26 |
| P14 hold texts promise a resume | **accepted** | v1 §4.8 vs §3.6 "do not resume"; Core's word is "media" (`App:7664`) | §4.8 texts, `HOLD_TEXT` (tested) |
| P15 the parity rule is not one rule | **accepted**, (a) changed | v1 D9 vs D11, empty frames. v2's rule (§2.4): the nine fields copy the touch UI; extra rows for extra facts; time is fixed on both screens. (a) changed: BIT DEPTH copies "16-bit" now (the operator's "copy now"), the stored depth goes in FORMAT, and U5 stays optional instead of being pulled into T47 | §2.4, D9, D16, U5, U11/O18 |
| P16a 503 storm with two viewers | **accepted** | v1 §2.2 re-asked at once | `laneAfter` back-off (tested), §2.2 |
| P16b "Shared with another viewer" in the rate line; split LRU | **changed** | the split cache is in (8 + 24 MB, §4.7); the text belongs to O4's rate row, so it comes with O4 | §2.2, §4.7, O4 |
| P17 thumbnails stay blank after a hold; refetch trigger | **accepted** | stills keep `writing` after `recording` goes false (`CC:6265-6271`) | D5, B15, row 50.4 |
| P18 the scrub pauses, the touch UI plays on | **accepted** | `PC:589-609` restarts audio at the new frame while playing | V6, §3.6, `scrubEnd` (tested) |
| P19 "going again" after a 16-bit review | **accepted** | as CC M4 | §2.7, §2.8, M16; `O_DIRECT` if M16 says so |
| P20 no playback in standby or a long timelapse | **changed**: a question, no design change | in standby a capture is refused (r3 §3.7); the default stays "hold" | Q20 |
| P21a the last take is four taps away | **accepted** as option W2 | Cinemate opens on the newest take (r1 §1.5) | W2, Q28 |
| P21b the initial Show filter follows the photo mode | **changed**: a parity default, not an option | the touch browser follows `photoModeEnabled` (`Main:206`, `:237`); `photo_mode_enabled` is in `/api/state` (`App:8172`) | D1, row 49.5 |
| P22 the held viewer hides the live view | **accepted** | — | V20, §2.7 (Live view button) |
| P23 focus cannot be judged | **accepted** as option | half-res render (r2 §4.4); handbook lesson (r4 C6) | O16 |
| P24 lossy cost is a lower bound; the format is not shown | **accepted** | synthetic 1.0 MB vs ~4 MB real (12.4 MB ÷ 3); lossy folders `cDNG_3to1_`/`cDNG_5to1_` (`CC:4191`) | §0.5, §2.3, FORMAT row (D16), M18 |
| P25 sync over Bluetooth unknown | **accepted** | UNCONFIRMED | M12, O22 |

### Smaller points S1-S7

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| S1 the page stalls after a cut; "writing" hardly seen | **accepted** | `CC:9785-9798`, `CC:9908-9912` | "Finishing the take…" (§2.7, §4.8); F32 |
| S2 two decodes stuck after a pull | **accepted** | r3 §4.5 | "Waiting for the media to answer…"; R16 |
| S3 sound-only items stopped only by the poll | **accepted** (covered) | — | the per-chunk stop (§2.6) |
| S4 Space toggles twice with a focused button | **accepted** | — | D12, row 50.6 |
| S5 MLV and cDNG look different | **accepted** | r2 §5 | T52 §7 note |
| S6 the button greys only on `recording` | **accepted** | as CC m5 | row 49.9 |
| S7 fullscreen where it exists | **accepted** as option | — | O19, Q29 |

### Walkthrough findings not covered by a P-point

| Point | Verdict | v2 |
| --- | --- | --- |
| W1 "FRAME 1 / 207 on both screens" | **accepted** (now true by design: both count the files) | V3, §4.2 |
| W2 a 16-bit histogram is a spike at the left | **accepted** as U11/O18 | §5, §9.2 |
| W11 a `readdir` of 15,000 entries per open | **accepted** | M17, §4.2 |
| W12 the touch screen's preview may stutter while a browser plays | **accepted** | M13, R12 |

### Additions for §8, §10, §11, §9, and the order

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| M12 clap sync | **accepted** | — | M12 (with Bluetooth) |
| M13 touch preview during browser playback | **accepted** | — | M13 |
| M14 the phone on the hotspot | **accepted** | — | M14 |
| M15 download during a take | **accepted** | — | M15 |
| M16 record right after a review | **accepted** | — | M16 (plus `/proc/vmstat`, from CC M4) |
| M17 the list with a long take | **accepted** | — | M17 |
| M18 a real lossy take | **accepted** | — | M18; v2 adds M19 (H.264 through the plugin) |
| R16-R25 | **changed** (renumbered, some closed) | R16 drift → fixed in the WebUI, residual R19 (screens differ until T54); R17 ramp → fixed by D21; R18 downloads/WAV → fixed, residual R17 (a behaviour change); R19 touch screen in a take → R18; R20 503 storm → fixed; R21 phone layout → R20; R22 Back/sleep → R21; R23 delete then record → R22; R24 Bluetooth → R23; R25 silent switch → fixed (`gone`) | §10 |
| Q19 number clock on both screens | **accepted** | — | Q19 |
| Q20 standby / timelapse | **changed** default wording | hold stays the default | Q20 |
| Q21 downloads in a take | **accepted** | — | Q21 |
| Q22 T54 | **accepted** | — | Q22 |
| Q23 refuse `record_start` while deleting | **accepted** | — | Q23 |
| Q24 O4 + O5 | **accepted** | — | Q24 |
| Q25 SOUND row | **accepted**, widened | SOUND, FORMAT, DROPPED together | Q25 |
| Q26 unfinalised MLV | **accepted** | — | Q26 |
| Q27 `<video>` for H.264 | **changed** | "decide after M19" instead of "yes" (P12) | Q27 |
| Q28 review chip | **accepted** | — | Q28 |
| Q29 fullscreen | **accepted** | — | Q29 |
| Q30 ramp takes | **accepted** | — | Q30 |
| O15 waveform, O16 zoom, O17 save frame, O18 stops histogram, O19 fullscreen, W2 review chip | **accepted** as options | — | §9.2 |
| Order table (T47-T53 additions, new T54) | **accepted** | — | §6 rows, T54 |
| T50 gate additions (claps, ramp, record during WAV and ZIP, remote delete, two browsers, Back/swipe, screen on, screenshots) | **accepted**; "screen on during a 2-minute take" becomes "the pause toast says why" (P7c) | — | T50 gate, §7 |
| The resemblance tables (§ "Does it resemble the touch UI?", "Where copying would be wrong", "Compared with Cinemate") | **accepted**; each row maps to a P-point above | — | — |

---

## 3. What v2 adds that neither critic asked for

| Addition | Why | Where |
| --- | --- | --- |
| `eject_media` and `format_media` open the yield window | a plain `umount` fails while a frame is open (`App:3779`, `App:3832`) | §2.7, row 47.8, F40 |
| The watcher keeps the yield window open while a hold lasts | a stream whose client stalled past the 3 s window would otherwise read on during the take | §2.7, `PlaybackHold.hpp`, `v2_test` hold |
| 0-byte frames counted as the touch UI counts them, instead of a new difference | removes CC M7's divergence rather than documenting it | §2.4, D22 |
| The chunked reader shrinks the per-request scratch from 16.6 MB to ~1 MB | it is why A.3's +65 % mostly disappears on the v2 reader | §2.3 |
| The size cap covers IMX477 4056 × 3040 | CC M9's cap would have refused it | F37, §4.9 |
| MLV VIDF carries the same time-based `frameIndex` as the DNG names | the number clock applies to MLV too | `CC:7975`, `CC:3998`, `Mlv:1027`; §2.5, row 52.1 |
| JPEG-only timelapse plays (the touch UI does not list these) | Core lists them today; TurboJPEG is already in Core | §2.5 |
| FORMAT text derived from bits, the table and the folder prefix | Clear HDR vs SDR vs lossy is not one tag | §4.3 |
| `fetchState`-style queue for `fetchMediaLibrary` | CC M11 noted the drop; the refetch after a hold depends on it | row 49.8 |
| A tutor-block and search-string checker | 79 refs, 14 checks, 47 search strings validated | `v2tmp/check_tutor.py`, `v2tmp/check_search.py` |
