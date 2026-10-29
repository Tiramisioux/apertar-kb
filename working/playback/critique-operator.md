# Critique of design-playback v1 (WebUI playback in the touch UI's shape): operator lens

2026-10-29, cloud session, critic pass. The operator is Patrik on set: a phone or a laptop on the camera's Wi-Fi, and the
camera's own touch screen. Every tree was read only. Nothing was built and nothing ran on the Pi. This file is the only one
written.

Trees I opened (every `path:line` below is at these commits):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `D` | `design-playback.md`, the design under review. `D:n` = its line n, `D§x` = its section | this folder |
| `App`, `CC`, `Web`, `WS`, `Audio` | `src/ApertarCoreApp.cpp`, `src/camera/CameraController.cpp`, `src/web/WebControlPage.cpp`, `src/web/WebServer.cpp`, `src/audio/AudioRecordingSession.cpp` | Core `scratchpad/controls/core-tip` `eb9cc39` |
| `PC`, `CPP`, `CBP`, `CamP`, `DD`, `VPL` | `src/playbackcontroller.cpp`, `qml/ClipPlayerPage.qml`, `qml/ClipBrowserPage.qml`, `qml/CameraPage.qml`, `src/dngdecoder.cpp`, `src/VideoPlaybackLibav.cpp` | touch UI `scratchpad/controls/ui-tip` `d8098d0` |
| `HL`, `RA`, `RL`, `ST` | `lessons/hardware-log.md`, `working/ramp-answer.md`, `working/ramp-ladder/README.md`, `working/ramp-ladder/build/STATUS.md` | KB `/home/user/apertar-kb` `c108731` |
| `R1`-`R4` | the four reader reports | this folder |

Labels:

- **CONFIRMED**: I opened the line.
- **PROBABLE**: derived. The derivation is given.
- **UNCONFIRMED**: only the Pi, a real phone or a browser test can settle it.

A point taken from a reader report without reopening it says so (`R2 §x`).

Design facts I re-checked, all CONFIRMED and all holding:

- The frame number comes from the sensor timestamp (`CC:3780-3787`), so drops leave gaps.
- The 24-frame queue for compressed DNG (`CC:3500-3504`).
- The delete gate at `App:7660-7666`.
- `streamFileToClient` (`App:6333-6347`).
- The touch UI's audio clock (`PC:827-859`) and seek (`PC:589-609`).
- The scrub (`CPP:95-103`, `:658-665`).
- The movie plugin's output limit and seek rule (`VPL:142`, `:149`).
- The H.264 default size (`CC:1053-1054`).
- The card name elide (`CBP:755`).
- The histogram binning (`DD:505-517`).

---

## Verdict

The design gets the big operator things right:

- Every take already on the card plays.
- The picture is the touch screen's own picture, with parity proven on the host.
- Recording wins, checked in each request, and the hold is shown in words.
- The live view stops while the overlay is open.
- No socket command blocks `record_stop`.
- Each of the nine metadata fields comes from the file.

What it misses is mostly **time**:

- Sound and picture drift apart on any take with dropped frames, and Patrik's lossless takes drop 15-35 %.
- A speed-ramped take is cut short and out of sync.
- Three read paths still touch the card in a take: downloads, the WAV stream, and the camera's own screen.

Then come phone and browser realities that the touch UI never meets: Back, sleep, long-press callouts, and a 390 px width.

| Design section | Verdict | Why (one line) |
| --- | --- | --- |
| §0 Short answer | keep, **change** | Item 5 ("no playback read touches the card during a take") is not true yet (P3, P4). Item 6 ("`<audio>` is the clock") needs the number mapping (P1) |
| §1 How it works today | keep | Accurate. Add the touch UI's drift on drop takes to §1.2 (P1) |
| §2.1 Picture source (A, O11 later) | keep | Right for the operator: every take plays, and both screens show one look |
| §2.2 Transport and pacing | **change** | The 503 rule needs a back-off (P16). Frames must be asked for by number, not position (P1) |
| §2.3 Sketch numbers | keep, **change** | The lossy figure is a lower bound. Tell Patrik that lossy may play like lossless (P24) |
| §2.4-2.5 Sharing, formats | **change** | Ramp takes (P2), unfinalised MLV (P13), H.264 through `<video>` (P12), sound-only stage (P6) |
| §2.6 Sound | **change** | Clock → frame number (P1). Output latency check (P25). WAV stream hold (P3) |
| §2.7 Interlocks | **change** | Downloads and the WAV stream (P3). Touch UI hold (P4). Standby and timelapse (P20). Delete-then-record (P11) |
| §2.8 Budget | keep, **change** | Page cache and heat before "going again" (P19) |
| §2.9 Deliberate differences | **change** | D9 vs D11 contradict each other (P15). Missing rows: scrub resume (P18), N without empty frames, sound row, long-press time, number mapping |
| §3.1-3.4 Maps | keep, **change** | The resemblance is close (table below). Download next to Remove (P9). No sound indicator (P6) |
| §3.5 Layouts | **change** | The phone does not fit the square sizes (P8) |
| §3.6 Behaviour | **change** | Back/popstate, Wake Lock, long-press callout (P7). 404 handling (P10). Refetch trigger (P17). Scrub resume (P18) |
| §3.7 Walkthroughs | **change** | D says "the sound stays in time": it does not (P1). B misses downloads and the touch screen (P3, P4) |
| §4 API | **change** | `frame` by number, gap list, `ramp`, `gone`, `sound_state`, download gate, chunked hold check |
| §4.8 Messages | **change** | "Playback resumes when…" promises a resume that is not built (P14) |
| §5 Touch UI changes | **change** | U2 should be in scope. Add U9 (number clock) and U10 (ramp) so both screens agree (P1, P2, P4) |
| §6 Plan | **change** | Rows to add are under "Order" at the end |
| §7 Tutorials | **change** | T50's gate needs a lossless take with sound and a phone at 390 px; T51 needs a hold test while a WAV streams |
| §8 Measurements | **change** | Add M12-M18 (end of this file) |
| §9 Options | **change** | O4/O5 are the minimum honest display (P5). O1/O10 are needed for long takes (P11). Add O15-O19 |
| §10-11 Risks, questions | **change** | Add R16-R25 and Q19-Q30 |

---

## Walkthroughs

Each row points to a problem below. Where the design is fine, the row says so.

### W1. Check the last take right after cut (laptop, then "going again")

The take is 4K SDR 12-bit lossless at 25 fps, 10 s long, with sound.

| Step | Design (cite) | Operator sees | Problem |
| --- | --- | --- | --- |
| Cut | Core stop: queue drain (≤ 24 frames, `CC:3500-3504`), WAV finalise (`Audio:559-626`), sync. The whole stop runs with `CameraController::mutex_` held (`CC:9785-9798`), and `isRecording()` takes the same mutex (`CC:9908-9912`). The 1 s poll and every hold check wait | the WebUI page freezes for ~1-2 s, then the folder button enables. The `writing` hold (`D:294`) is mostly never seen after a take, because the poll returns only once the stop is done (PROBABLE) | small, S1 |
| Folder button | the overlay opens, `/api/media`, thumbnails 2 at a time (`D:529`) | the last take top-left, "00:10", "cDNG clip". Its thumbnail arrives in ~0.3-0.4 s (`D:329`) | fine |
| | the card name is elided at the right (`CBP:755`) | on a laptop: fine. On a phone: "cDNG_26-10…" on every card | P8 |
| Tap the card | paused on frame 1, paused-size frame (`D:531`) | "FRAME 1 / 207" on both screens, because both count the files present. The take's 43 missing frames (`HL:108`) show nowhere | P5 |
| Play | wanted frame = `floor(currentTime × fps)` by **position** (`D:276`, `D:656`) | the picture runs ahead of the sound. At 5 s it is ~0.9 s ahead. At 8.3 s it reaches its last frame and holds for 1.7 s while the sound plays on | **P1** |
| | ~5-8 fps shown (`D:331`) | jerky playback. Is it the take or the player? Nothing says | P5 |
| Did the mic record? | nine fields, no sound row (`D:437`) | silence could mean no WAV, a refused WAV, or a muted laptop | P6 |
| Back, Back | the live view restarts (`D:530`) | fine | — |
| "Going again": record | 16-bit review reads ~415 MB/s through the page cache (`D:330`); 2 cores busy for minutes | the take starts with a full page cache and a warmer Pi. Any cost is unmeasured | P19 |

### W2. Scrub a 4K Clear HDR 16-bit uncompressed take (phone, portrait)

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Open | the stacked layout at the touch UI's `square` sizes (`D:472`) | the control row (~546 px at square sizes, ~452 px at compact) does not fit ~320 px. The header (~600 px) does not fit either | **P8** |
| Drag the bar | `pointerdown` pauses; 640 w, one request in flight (`D:538`) | ~10-15 updates/s (55-100 ms per frame on the Pi, `D:237`). Good | — |
| | no `touch-action` rule named for the scrub (`D:433`) | the page may pan or pull to refresh while dragging (UNCONFIRMED: depends on the shell's CSS) | P7 |
| Release | the paused size (≤ 1920 w) | a sharp frame after ~0.4-0.6 s (PROBABLE, `D:228`, `D:332`). Good | — |
| It was playing before the drag | the design pauses (`D:538`) | the touch UI keeps playing from the new frame (`PC:600-608`). Here it stays paused | P18 |
| Is focus right? | 640 w play, 1920 w paused, from a half-resolution debayer (R2 §4.4) | focus cannot be judged on either screen (handbook: "the half-res thumbnail will flatter you", R4 C6) | P23 (option) |
| Read the histogram | 48 linear bins of raw values (`DD:505-517`), one CFA site at 4K (`D:145`) | a Clear HDR 16-bit frame is a spike at the far left (PROBABLE: mid-grey 5-8 stops under clip falls in bin 0 or 1 of 48 linear bins). It looks underexposed on both screens | P15 |

### W3. A lossy DNG take (`cDNG_3to1_…`)

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Card | "cDNG clip" (`D:416`) | the same label as uncompressed and lossless. Only the folder name says 3:1, and on a phone the name is elided away (P8) | P24 |
| Metadata | TYPE "cDNG sequence", BIT DEPTH "12-bit, companded" (D9, `D:354`) | the touch screen says "16-bit" for the same take | P15 |
| Play | 12-15 fps per worker, "synthetic, a lower bound" (`D:230`) | a real 3:1 frame is ~4 MB, not 1.0 MB, so decoding probably costs 2-4× more. Playback is likely as choppy as lossless (~5-8 fps). Patrik may expect lossy to be smooth | P24 |

### W4. An MLV take

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Before T52 | "NO PREVIEW"; "MLV playback arrives with T52." (`D:720`, `D:745`) | clear | — |
| A finalised MLV | block index, the touch UI's ISP look (`D:262`) | plays. It looks different from a cDNG of the same scene (R2 §5), on both screens. One line in the tutorial's §7 avoids a surprise | small, S5 |
| The MLV of a pulled take | header count 0 → "MLV is not finalized or its frame count is invalid." (`D:263`) | the take he most wants to check shows nothing, although its frames are on the card | P13 |
| Sound | `<clip>.wav` beside the MLV, or none after a pull (`HL:447`) | the same ambiguity as W1 | P6 |

### W5. An H.264 take (and ProRes)

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Card | probe through Core's plugin (T53) | fine once T53 is built | — |
| Play | Core decodes 2560×1440 (`CC:1053-1054`) and scales it to ≤ 1920 (`VPL:142`, an output limit, so the input is fine). Two requests in flight (`D:200`) on "one open decoder per clip" (`D:846`) | if frame N+2 is asked before N+1, the plugin seeks back to the keyframe (`VPL:149`). GOP = round(fps) (R3 §2.5), so that is up to 25 frames of software decode. Stutter (PROBABLE) | **P12** |
| Scrub | each position is a seek plus up to one GOP of decode | ~0.3-1 s per position on the Pi (PROBABLE; the Pi 5 has no H.264 decoder, UNCONFIRMED here) | P12 |
| The browser | `<video>` is option O12, "if T53's H.264 is slow" (`D:1167`) | the phone has a hardware H.264 decoder and would play the file at full rate | P12 |
| A take in progress | "H.264 take is still being written." (`D:718`) | clear (and held in a take anyway) | — |
| ProRes | plugin only (Chrome and Firefox cannot play it) | right | — |

### W6. A speed-ramped take

T31 is not on `eb9cc39`, but Patrik is building T31-T34 now (`ST:9-17`).

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Card | FPS and duration from the first frame. T31 pins every frame's `FrameRate` to the start rate (`RL:29`) | "00:30" for 10 s at 25 fps + 10 s at 50 fps (750 frames ÷ 25). It was 20 s on set | **P2** |
| Viewer | "25.000 FPS" | nothing says "ramp" | P2 |
| Play, with a WAV | audio clock, frame = `floor(t × 25)` (`D:276`). The T31 WAV is real time, 20 s (`RA:92`) | the first 10 s are fine. In the 50 fps part the picture runs at half speed against the sound. When the WAV ends at 20 s the picture is at frame 500 of 750 and loops. **Frames 500-749 are never shown.** The touch UI does the same (`PC:836-855`) | **P2** |
| Drops | numbering by count in T31 takes (`RL:29`) | `dropped_frames` = 0 even when frames dropped (R10, `D:1195`) | P2 |

### W7. Audio sync (the clap at the slate)

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Uncompressed 16-bit, no drops (`HL:108` row 1) | the audio clock | in sync. Core trims and pads the WAV so that sample 0 is the first frame and its length is the take's span (`Audio:606-626`, comment `Audio:865-866`) | — |
| Lossless 25 fps, 37-45 frames missing per 10 s (`HL:108`) | by position | the clap is late by about the number of drops before it: ~1 frame per 6 frames of take. A sync test on a lossless take "fails" (PROBABLE arithmetic) | **P1** |
| Find the clap frame | no frame step (O1 is an option, `D:1156`), no sound while paused | he cannot step to the clap frame and hear it | P11, O15 |
| Bluetooth headphones on the phone | `audio.currentTime` drives frames | `currentTime` may lead the sound he hears by the output latency, 100-250 ms on Bluetooth (UNCONFIRMED: browser- and device-specific) | P25 |

### W8. Someone presses record while the director plays a take on the phone

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Record from the rig's button | the next frame request answers 409; the page pauses picture and sound (`D:535`) | stops within ~1 frame plus a round trip. Good | — |
| The phone was playing sound out loud | as above | the new take's mic hears ≤ ~0.1 s of it. Fine. For a **sound-only** item (no frame requests), only the 1 s poll stops it | small, S3 |
| The `<audio>` element's Range stream is still open | the streamer is "the `streamFileToClient` pattern" (`D:679`), which checks nothing per chunk (`App:6333-6347`) | Core keeps reading the WAV for as long as the browser pulls, after the take has started | **P3** |
| The DIT was downloading take 6 | `Download` → folder ZIP (`D:541`). Downloads are not gated (R3 §4.3; `App:7343-7360` has no recording check) | `zip -0` reads the card at Wi-Fi speed during a 415 MB/s take on a ~437 MB/s link (`D:149`) | **P3** |
| The operator reviews on the camera's own screen and presses record | the touch UI is unchanged (`D:751`); its player keeps decoding (R2 §7) | the take records while the touch UI reads and decodes from the card | **P4** |
| The director wants to see the take | the hold card (`D:708`) | the live view stays off under the overlay; he must find Back | P22 |
| The take ends | the card clears; playback does not resume (`D:543`) | the card's text said "Playback resumes when recording stops." | P14 |

### W9. The card is pulled during playback

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Pull | the watcher snapshot, 409 `media` before any read (`D:297`, `D:572-574`) | "Media not available" within ~2 s. Good | — |
| The two decodes in flight | they are in `pread` on a dead NVMe; that can block 30-60 s (R3 §4.5) | after re-insert, frames answer 503 until those threads return. The page shows nothing about it | small, S2 |
| Thumbnails | "NO PREVIEW" for a held clip (`D:413`) | after re-insert, the cards stay blank unless something re-queues them | P17 |
| The pulled take itself | `empty_frames` excluded (`D:620`); no WAV (`HL:447`) | the picture plays to ~1 s before the pull. Sound: silent, with no word that `audio_capture.raw` is there (`HL:457`) | P6 |
| | the WebUI's N excludes 0-byte frames; the touch UI's counts them (R2 §2.3) | the two screens show different N for the same take, with no D row for it | P15 |

### W10. Two browsers at once (director's phone, DIT's laptop)

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Both play | 2 slots, 2 requests in flight per page, 503 → skip (`D:200-202`, `D:700`) | four requests compete for two slots. A refused request frees its lane at once and asks again, so each page cycles through 503s at round-trip rate: a new TCP connection and Core thread each time (`D:132`) | **P16** |
| One long clip plays | one 32 MB LRU for thumbnails and play frames (`D:697`) | a 1,000-frame clip at ~30 KB evicts every thumbnail. The other page's next refresh decodes the grid again | P16 |
| The DIT removes the clip the director is watching | 404 → refetch → "reopen by index" (`D:532`) | the director's viewer silently switches to a different take | **P10** |
| The touch UI deletes (it bypasses Core, R2 §4.1) | same | same | P10 |

### W11. A long take: 10 minutes, 15,000 DNGs, ~250 GB at 16-bit

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| List | facts cached per folder, keyed by (mtime, entry count): one `readdir` per open (`D:626`) | a `readdir` of 15,000 entries per long take on every open, Refresh and delete. Unmeasured | M17 |
| Scrub | 15,000 frames across a ~320 px bar | ~47 frames (~1.9 s) per pixel. "Go to 7:32" cannot be done: there is no time readout and no frame step (O1 and O10 are options) | **P11** |
| Download | a ZIP with no `Content-Length` (R3 §3.3) | 250 GB over Wi-Fi with no size and no progress | P11 |
| Remove | `remove_all` runs synchronously (`App:7683`) | an unknown wait with no "Removing…". The record gate does not see a running delete (`App:7660-7666` checks only at the start), so a take can start while thousands of deletes hit the card | P11 |

### W12. On the camera's own screen

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Review on the touch screen | unchanged (`D:751`) | as today. Fine | — |
| Hardware `clip_browser` in a take | not blocked (R2 §7). U2 is optional (`D:760`) | the touch browser opens mid-take: a full rescan plus a full raw decode for every thumbnail, on the Pi, during the take (R2 §4.1, §4.3) | **P4** |
| The same take on both screens | D9, D11, empty frames, the sync fix (P1) | different BIT DEPTH and different N. With P1 fixed only in the WebUI, a different sync too | P15 |
| A browser plays 16-bit 4K while the operator frames the next shot | Core's 2 workers at nice 10 (`D:338`) | the touch screen's live preview may stutter from memory contention (PROBABLE, `HL:87`) | M13 |

---

## Problems and fixes

They are ordered by how much they hurt on set. Each says what goes wrong, the evidence, the fix, and where the fix goes.

### P1. Sound and picture drift apart on any take with dropped frames (both screens)

- **What.** The clock time is turned into a **position** in the list of frame files (`D:276`, `D:656`).
  - Core numbers each frame from its sensor timestamp: `llround((ts - first) × fps / 1e6)` (`CC:3780-3787`). A dropped frame therefore leaves a hole in the numbers. The hardware log confirms it: files + queue-full + gaps = last index + 1 (`HL:85`).
  - The WAV is trimmed and padded to the span from the first frame's time to the last frame's time (`Audio:606-626`).
  - So sound time t belongs to frame **number** `first + floor(t × fps)`, not to position `floor(t × fps)`. All CONFIRMED.
- **Effect** (PROBABLE arithmetic). Patrik's lossless 25 fps takes miss 37-45 of 250 frames per 10 s (`HL:108`).
  - At 5 s the picture is ~0.9 s ahead of the sound.
  - At ~8.3 s the picture reaches its last file and holds there for 1.7 s.
  - The touch UI does the same (`PC:851-855`, position clamped at `frameCount - 1`).
  - The design's walkthrough D claims "the sound stays in time" (`D:568-569`). It does not.
  - The operator will conclude that the sound recording is broken.
- **Fix** (T47, T48, T50):
  - `/api/media/clip` returns `first_number`, `last_number` and `gaps` (a list of `[number, length]`; this is HTTP JSON, so the flat socket rule K9 does not apply).
  - `/api/media/frame` takes `n=<number>` (or keeps `frame=` and adds `X-Frame-Number`).
  - The page asks for `first + floor(clock × fps)` and shows the stored frame with the largest number at or below it. Over a hole it holds the previous frame and shows a **"DROPPED"** badge, which is also the cheapest form of O5.
  - Without a WAV, the wall clock uses the same mapping, so the take plays in real time and its length matches the slate.
  - DURATION = (last − first + 1) ÷ fps, not files ÷ fps (`D:617`).
  - "FRAME i / N" stays position-based, with the touch UI's words.
  - O10's timecode comes from the shown frame's number (or its own `TimeCodes` tag), never from the position.
- **Touch UI.** Add **U9**: the same mapping in `PC:851-855` (~20 lines), in the same tutorial or the next. Until then this is a deliberate difference, **D15**, and both screens disagree on lossless takes.
- **T31 takes** number frames by count (`RL:29`), so the number equals the position. There, only `fps-ramp.txt` gives time (P2).
- **Test.** T50's gate plays a lossless take with a clap at 2 s and 8 s.

### P2. A speed-ramped take is cut short and out of sync (both screens)

- **What.** With T31:
  - every frame carries the start rate (`RL:29`);
  - the WAV is real time, and "the picture on a 25 fps timeline is longer" (`RA:92`);
  - the design clocks frames from the WAV (`D:276`);
  - the touch UI loops at the WAV's end (`PC:836-845`).

  All CONFIRMED.
- **Effect** (PROBABLE arithmetic). Take 10 s at 25 fps, then 10 s at 50 fps: 750 frames and a 20 s WAV.
  - At the WAV's end the picture is at frame 500. Frames 500-749 are never shown.
  - In the 50 fps part the picture plays at half speed against real-time sound.
  - The card says "00:30" for a 20 s take.
  - `dropped_frames` reads 0, because numbering is by count (R10).
- **Fix** (T47 facts, T50 clock):
  - Core reads `fps-ramp.txt` when it is present and returns `ramp: {base_fps, max_fps, events}` plus `real_duration_text`.
  - The viewer plays a ramp take **as its timeline**: base rate, wall clock, sound off.
  - One line: "Speed ramp 25 → 50 fps: plays as on a 25 fps timeline. The sound is real time, so it is off."
  - Badge "25.000 FPS · RAMP". FRAME RATE "25.000 fps (ramped to 50.000)". DURATION "00:30 (20 s real)". Drops "unknown".
  - Option **O3b** "Real time": map the frames through the ramp events, with sound on.
  - Touch UI: **U10** the same, or at least no loop at the WAV's end.
- **Test.** T50's gate includes one ramp take, once T31 is on the Pi.

### P3. Downloads and the sound stream keep reading the card after a take starts

- **What.**
  - The new range streamer copies `streamFileToClient` (`D:679`), which checks nothing per chunk (`App:6333-6347`).
  - Downloads are not gated (R3 §4.3; `App:7343-7360` has no recording check).
  - The viewer adds a Download button (`D:541`). `D:1212` (Q5) even plans for downloads during a take.

  All CONFIRMED.
- **Effect** (PROBABLE).
  - A 4K 16-bit take at 25 fps writes 415 MB/s on a Gen 2 link measured at 437 MB/s (`D:149`), and "memory traffic alone costs frames" (`HL:87`).
  - A ZIP at Wi-Fi speed (5-30 MB/s), or a WAV that Chrome buffers ahead, takes from that margin.
  - The typical set case: the DIT downloads take 6 while the operator rolls take 7.
  - Section 0's promise ("no playback read touches the card during a take", `D:62`) is broken by the design's own Download button.
- **Fix:**
  - (a) T51: `streamFileRangeToClient` calls `playbackHoldReason()` every 64 KiB chunk and closes the stream on a hold.
  - (b) T50: the download routes answer 409 at start in a hold: "Recording. Downloads are paused until the take ends."
  - (c) T50: a running ZIP is stopped when a take starts (kill the `zip` child at the first hold). Because the stream has no `Content-Length`, the browser would save a cut ZIP that looks complete (R3 §3.3). So the page shows "Download stopped: recording started. Start it again after the take." It can detect this from the hold.
  - (d) If Patrik wants downloads during takes, M15 measures the cost first. The default: refuse.
- Question **Q21**.

### P4. The camera's own screen has no hold, and that is where "review, then roll" happens most

- **What.**
  - The touch UI greys only its on-screen folder button (`CamP:3754`, R2 §7).
  - The hardware `clip_browser` action, the player and delete are not blocked during a take.
  - The player prefetches 8 frames on 2 threads and decodes full raw frames (R2 §4.3).
  - U2 fixes this and is optional (`D:760`).

  CONFIRMED (R2) for the gaps. The effect on a take is PROBABLE, the same budget as F24.
- **Effect.** The operator reviews on the touch screen and presses the rig's record button. The take records while the touch UI reads and decodes from the card.
- **Fix.** Bring U2 into the project as **T54** (~30 lines, before or with T50):
  - `onRecordingChanged` → `playbackController.stop()`;
  - the player shows the same hold text as the WebUI (§4.8);
  - `clip_browser` is ignored while recording;
  - Remove is disabled while recording (or U3).

  "Recording wins" then holds on both screens. Patrik decides (Q22). The default should be yes.

### P5. Lossless takes look worse than they are, and nothing tells player skips from recorded drops

- **What.**
  - On lossless 4K the viewer shows ~5-8 fps and skips (`D:331`, `D:568`).
  - The take itself may miss 15-35 % of its frames (`HL:108`, `:113`).
  - The touch UI shows neither (R2 §2.3: no drops per clip).
  - O4 (rate row) and O5 (DROP N) are options (`D:1159-1160`).
- **Effect.** Jerky playback. He cannot tell whether the take dropped frames or the player cannot keep up, so he either re-shoots a good take or misses a bad one.
- **Fix.** Patrik's brief keeps Cinemate's extras as options, so offer the minimum honest display as the default:
  - the PLAYING badge reads "PLAYING · 7 FPS" while the achieved rate is under 95 % of the clip's rate (a text change in an existing badge);
  - the card and the viewer show "DROPPED 43" when `dropped_frames > 0` (O5, ~20 lines);
  - the full O4 row stays an option.

  Recommend O4 + O5 for T50 (Q24).

### P6. Silence on playback means four different things, and nothing shows which

- **What.**
  - The nine fields have no sound row (R2 §3.2; `D:437`).
  - `has_audio` and `audio_text` exist in the clip JSON (`D:641-642`), but the screens do not show them.
  - A pulled take leaves `audio_capture.raw` and no WAV (`HL:447`, `:457`).
  - A browser may refuse the WAV (toast only, `D:725`).
  - A sound-only item has no picture, and the stage's content is not specified.
- **Fix** (T50/T51). One WebUI-only metadata row, **SOUND**, with one of:
  - "24-bit 48 kHz stereo";
  - "None";
  - "Not finalised: `audio_capture.raw` is on the card (raw2wav.py)";
  - "This browser cannot play it".

  Also:
  - When a clip plays without sound, the PLAYING badge reads "PLAYING · NO SOUND".
  - For sound-only items the stage shows "SOUND ONLY" and the time, plus the waveform if O15 is taken.

  List this as D-row **D16**.

### P7. Browser Back, phone sleep and long-press callouts (the touch UI never meets them)

- **What** (CONFIRMED by grep at `eb9cc39`). `Web` has no `pushState`, `popstate`, `wakeLock`, `-webkit-touch-callout` or `contextmenu`. The viewport is `width=device-width, initial-scale=1` (`Web:11`). The thumbnails are `<img>` (`D:413`), selected by an 800 ms long press (`D:420`).
- **Effect** (UNCONFIRMED: real phones only):
  - Android's Back button and iOS's edge swipe leave the WebUI or close the tab, instead of closing the viewer.
  - The phone's screen locks during a long take, because a canvas plus `<audio>` does not keep it awake. The tab is then hidden, and playback pauses (`D:542`).
  - A long press on a thumbnail opens the system image menu ("Save image" / "Download image") at about 500 ms, before the 800 ms selection fires.
- **Fix** (T49/T50):
  - `history.pushState` when the browser opens and when the viewer opens; `popstate` → the same function as the Back button.
  - `navigator.wakeLock.request("screen")` while playing, released on pause, feature-detected.
  - On cards: `-webkit-touch-callout: none; user-select: none; draggable="false"`, plus `contextmenu` → `preventDefault`.
  - The long press is 500 ms in the browser. This is a deliberate difference, **D17**.
  - `touch-action: none` on the scrub track only.
  - Test on Patrik's real phone (Q10). Emulation cannot show this (R4 §6).

### P8. The touch UI's square sizes do not fit a phone

- **What** (PROBABLE arithmetic from R2's tokens, R2 §2.1 and §3.2). Phone portrait gets the `square` family (`D:472`). The sketch puts everything on one line (`D:480-503`).
- **Effect** (390 px phone, ~320 px inside the sheet):

  | Area | Width it needs | Width there is |
  | --- | --- | --- |
  | Viewer control row, square sizes: Remove 132 + transport 58/78/58 with 14 px gaps + histogram 152 + gaps | ~546 px | ~320 px |
  | Same row at compact sizes, plus Download | ~452 px | ~320 px |
  | Browser header: "Clip Browser" in bold 34 (~240 px) + Refresh/Show/Back (~54 + 136 + 112) | ~600 px | ~390 px |

  - A phone held sideways has ~300 px of height. Title 60 + preview 248 + scrub 22 + row 48 = 378 px.
  - Card names are elided at the right at ~120 px (`CBP:755`), so every card reads "cDNG_26-10…" and the "_C0007" that tells takes apart is lost.
- **Fix** (T49/T50; write the sizes into §3.5):

  | Screen | What changes |
  | --- | --- |
  | Phone portrait | The header takes two rows: the title, then the buttons right-aligned, with Refresh as an icon |
  | Phone portrait, viewer | Row 1: the transport, centred. Row 2: Remove at the left, then Download (see P9), the histogram at the right. Compact sizes |
  | Phone sideways | No title block and no info line. The preview takes the height. One row as in `landscape_compact` |
  | Card names | Middle elide in JS, keeping the counter at the end ("cDNG_26…C0007"). The touch UI's date line already elides in the middle (`CBP:774`) |

  The mocked-Chromium gate adds 390×844 and 844×390 screenshots.

### P9. Download sits beside Remove

- **What.** "[🗑 Remove] [⤓]" is one cluster in both sketches (`D:503`, `D:518`; V7 `D:434`). The WebUI has no authentication, so any phone on the hotspot can delete (R4 K21).
- **Fix:**
  - Remove stays where the touch UI has it: left, alone, red.
  - Download moves to the title row (an icon beside Info), or into the metadata panel.
  - The Download confirmation names the size (P11).

### P10. A clip removed elsewhere makes the viewer open another clip silently

- **What.** A 404 → refetch → "reopen by index" (`D:532`). The same 404 is used for a changed token (`D:669`).
- **Fix** (T48/T50):
  - Core answers `{"ok":false,"error":"…","gone":true}` when the folder is missing.
  - The page shows "This clip was removed on another screen." and returns to the browser.
  - A changed token (same id) refetches and reopens by **id**, never by index.

### P11. Long takes: the scrub is too coarse, and Download and Remove give no feedback

- **What.** 15,000 frames on ~320 px is ~47 frames per pixel. Frame step and timecode are options (`D:1156`, `D:1165`). The ZIP has no size (R3 §3.3). Remove runs `remove_all` synchronously (`App:7683`). The delete gate is checked only at the start (`App:7660-7666`). All CONFIRMED.
- **Fix:**
  - Under the scrub, a time readout "07:32 / 10:00". It costs nothing and keeps the touch UI's controls unchanged.
  - Recommend **O1** (frame step, hold to repeat) and **O10** (recorded timecode) for T50. Long takes and sync checks need them.
  - Download confirmation: "Download cDNG_… (249 GB)? Over Wi-Fi this takes hours. Copying the card is faster."
  - Remove: "Removing… (15,000 files)", buttons disabled, no double send.
  - In Core, a `mediaDeleteActive_` flag that `record_start` refuses with "Deleting media. One moment." This changes a record gate, so it is Patrik's call (Q23).

### P12. H.264 through Core's plugin will stutter and scrub slowly, while the browser plays it natively

- **What.**
  - The default H.264 is 2560×1440 (`CC:1053-1054`). The plugin scales its output to ≤ 1920 (`VPL:142`).
  - Any request for a frame at or before the last decoded one seeks back to a keyframe (`VPL:149`), and GOP = round(fps) (R3 §2.5).
  - The page keeps two requests in flight (`D:200`) on one decoder per clip (`D:846`).

  CONFIRMED.
- **Effect** (PROBABLE). Out-of-order arrivals and every scrub position cost a seek plus up to 25 frames of software decode.
- **Fix.** Make O12 the default for H.264 wherever `video.canPlayType()` accepts the file's codec string:
  - a muted `<video>` paced by the WAV's `<audio>` clock;
  - Range for `.mp4` (`D:675` allows only `.wav`; extend it);
  - FRAME i / N from `currentTime`;
  - the histogram from a 64×36 canvas copy of the video. The touch UI's movie histogram is display luma anyway (R2 §4.2), so the bars stay comparable.

  Keep the plugin for ProRes and as the fallback, with movie requests serialised in order (one in flight per decoder). Q27.

### P13. The MLV of a pulled take is unplayable, although its frames are on the card

- **What.** A header count of 0 is rejected (`D:263`). Core patches the count only at close (R3 §2.4). T52 walks the blocks anyway (`D:841`).
- **Fix** (option, Q26). When the header says 0 and the walk finds VIDF blocks, play them with the line "MLV not finalised (card pulled?): 102 frames recovered." The touch UI rejects such files, so this is a deliberate difference.

### P14. The hold text promises a resume that is not built

- **What.** `D:708` says "Playback resumes when recording stops." `D:710` says "Playback resumes when it ends." But `D:543` says "do not resume". Cinemate had the same mismatch (R1 §1.5).
- **Fix.** "Recording to media. Press Play when the take ends." / "A media speed test is running. Press Play when it ends." Use "media", as Core's own messages do ("Stop recording before deleting media.", `App:7664`), not "card".

### P15. The parity rule is not one rule

- **What.**
  - D9 fixes BIT DEPTH in the WebUI only (`D:354`).
  - D11 copies the one-site histogram so that both screens match (`D:356`).
  - Empty frames are dropped from N in the WebUI only (`D:620`), with no D row.
  - P1 would add a fourth difference.
  - Patrik's precedent is one answer on both screens, moved into Core (R4 P4).
- **Effect.** The same take shows "16-bit" on the camera and "12-bit, companded" on the phone, with different frame totals.
- **Fix.** One rule: **the WebUI copies the touch UI until a U-change fixes both in the same tutorial.** Then:
  - D9 → copy now, and do U5 later together with the WebUI change (or do U5 in T47);
  - the empty-frame N → U-change with T47, or copy;
  - P1 → U9 with T50.
- **Also** (PROBABLE). The linear 48-bin histogram (`DD:505-517`) shows a Clear HDR 16-bit frame as a spike at the far left. Offer **U11/O18**, a histogram in stops, on both screens.

### P16. Two viewers fill Core with refused requests

- **What.** A 503 means "skip, never pause", and the page keeps two requests in flight (`D:200-202`). With two viewers, four requests share two slots (`D:700`). Every request is a new TCP connection and a new Core thread (`D:132`).
- **Effect** (PROBABLE). Each refused lane asks again at round-trip rate, tens of refused requests per second.
- **Fix** (T50):
  - After a 503, the lane waits for its other request to come back, or for one frame interval, before it asks again.
  - The rate line says "Shared with another viewer" when 503s exceed 20 %.
  - Split the LRU: 8 MB for thumbnails (320/480 w) and 24 MB for play frames, so one long clip does not evict the grid (`D:697`).

### P17. After a hold, thumbnails stay blank and the list may miss the new take

- **What.** Held cards show "NO PREVIEW" (`D:413`). The queue's re-arm is not specified (`D:529`). The list refetches when `recording` goes false (`D:824`). Stills and timelapse writes keep `writing` on after that (`CC:6266-6271`), and in a hold the list answers from the cache (`D:628`).
- **Fix.**
  - When `playback_hold` becomes `""`, re-queue every card that has no picture yet.
  - Refetch the list on `playback_hold` → `""`, not on `recording` → false.

### P18. The scrub pauses, but the touch UI keeps playing

- **What.** On the touch UI a seek while playing continues from the new frame, and the sound restarts there (`PC:600-608`). The design pauses at `pointerdown` (`D:538`). This difference is not in §2.9.
- **Fix.** Pause during the drag (frames at 640 w), and resume at `pointerup` if it was playing. That is the touch UI's result and every browser player's habit.

### P19. "Going again" right after a 16-bit review

- **What.**
  - The review reads 415 MB/s through the page cache (`pread`, no `fadvise`, `D:798-800`).
  - It keeps ~2 cores busy (`D:330`).
  - The take then starts with a full page cache and a warmer SoC.
  - Clean-cache reclaim and heat were never measured with a take (the takes in `HL:87` had direct reclaim 0).

  PROBABLE small.
- **Fix.**
  - `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` after each frame read (or `O_DIRECT` reads, as the writers use), so playback leaves memory as it found it.
  - M16 measures it.

### P20. No playback in standby or during a timelapse

- **What.** Standby holds playback (`D:296`), and so does a timelapse of any length (hold 1, `D:293`). Lunch review on battery needs a Wake, which restarts the sensor and the preview. A 2-hour timelapse blocks all review.
- **Fix.** Ask (Q20). In standby the danger is gone: a capture in standby is refused (R3 §3.7). A slower read on the powersave governor may be acceptable. A timelapse with an interval ≥ 2 s writes a few MB per frame. Default stays "hold". Offer "allow in standby" and "allow when the interval is ≥ N s".

### P21. The last take is four taps away, while Cinemate opens on it

- **What.** Cinemate selects the newest take when the pane loads (R1 §1.5). The design needs: folder button → card → wait → Play. The WebUI's Show filter starts on Clips (`D:346`). The touch UI's browser follows the capture mode (R2 §2.4).
- **Fix** (option **W2**):
  - For 60 s after a take ends, the WebUI main page shows a "Review C0007" chip beside the record button. A tap opens the viewer on that take, paused at frame 1.
  - The initial Show filter follows the camera's photo mode (`photo_mode_enabled` is in Core's JSON, `App:193`, PROBABLE in `/api/state`) without switching it.

### P22. A held viewer hides the live view the director now wants

- **Fix.** The `recording` hold card has a second button, "Live view". It closes the overlay, and the live view restarts (`D:530`).

### P23. Focus cannot be checked on either screen (option)

- **What.** The render is a half-resolution quad debayer (R2 §4.4). Play frames are 640 w; paused frames are ≤ 1920 w (`D:657`). The handbook's lesson: "the DNG thumbnail is half-res and will flatter you" (R4 C6).
- **Fix.** Option **O16**: when paused, a pinch or double-click asks Core for a 1:1 crop of the half-resolution render around that point. Label it "Half resolution" so nobody judges critical focus from it.

### P24. Lossy takes: the playback cost is a lower bound, and the format is not shown

- **What.** The lossy row is synthetic, 1.0 MB per frame, "a lower bound" (`D:224-230`). A real 3:1 frame of a 12.4 MB SDR frame is ~4 MB (PROBABLE arithmetic). Lossless decode cost grows with the compressed size (the 7.7 MB lossless frame took 139 ms, `D:229`), so real lossy may play no better than lossless. TYPE says "cDNG sequence" for every DNG take (`D:644`), so the operator cannot tell uncompressed, lossless, 3:1 or 5:1 apart on a phone, where the name is elided (P8).
- **Fix.**
  - Tell Patrik up front: lossy probably plays like lossless (~5-8 fps). M18 measures a real take.
  - Add one metadata line from facts Core already reads (`compression`, `companded`, bits, `D:640`), e.g. "Clear HDR 16-bit · uncompressed" or "SDR 12-bit · lossy 3:1". This is the smallest form of O9.

### P25. Sync over Bluetooth is unknown

- **What.** The page draws the frame for `audio.currentTime` (`D:276`). Whether browsers subtract the output latency for an `<audio>` element on Bluetooth (often 100-250 ms) is UNCONFIRMED here.
- **Fix.** M12 with headphones. If it is off, add a per-device A/V offset in `localStorage` (a per-viewer convenience) with a "Sync −150 ms" control in the metadata panel. Do not build it before M12.

### Smaller points

| # | Point | Fix |
| --- | --- | --- |
| S1 | After a cut, `/api/state` and every hold check wait on `CameraController::mutex_` for the whole stop (`CC:9785-9798`, `CC:9908-9912`, `App:7864`). The `writing` hold is hardly seen after a take; the page just stalls ~1-2 s | When the poll takes > 1.5 s just after a take, the hold card shows "Finishing the take…". Correct §2.7 (the "never waits" claim at `D:289` is true for the command lock only) |
| S2 | After a card pull, two decodes may be stuck in `pread` for 30-60 s and hold both slots | After a `media` hold clears, while every answer is 503, the card says "Waiting for the media to answer…" |
| S3 | Sound-only items are stopped only by the poll | The P3 chunk check ends the stream, and the element stalls at once |
| S4 | Space toggles twice when a button has focus (`D:545`) | Handle Space on `keydown` with `preventDefault`. Ignore it in inputs |
| S5 | MLV and cDNG of one scene look different (two render paths, R2 §5) | One line in T52 §7 |
| S6 | The folder button greys only on `snapshot.recording` (`D:815`). A timelapse is a hold too | Grey it on `playback_hold === "recording"` |
| S7 | The laptop has the Fullscreen API; the phone (iOS) has none for canvas | Feature-detect `requestFullscreen` on the stage; show the button only where it works (R4 §6 trap). Option O19 |

---

## Does it resemble the touch UI? (R2's anatomy against the design)

| Touch UI (R2) | Design | Verdict |
| --- | --- | --- |
| Black page, "PLAYBACK" eyebrow, "Clip Browser" / "Still Browser" (R2 §2.2) | B1-B3 | same |
| Back / Capture mode / Refresh, right to left | B4-B6. Capture becomes "SHOW / Clips" (D1) | good deviation (a phone must not switch the camera's mode). Let the initial filter follow the photo mode (P21) |
| Sheet with "CLIPS" + film icon, count chip, sort chip, status line | B7-B10, B12 | same. "1 item" fix (D2) is fine |
| 2/3/4-column grid of 16:9 cards; duration pill; name / format / date | B13-B18 | same. Card names need a middle elide on phones (P8) |
| Long press 800 ms, Remove Selected, red dialog | B17, B20-B23 | same. In a browser: callout and 500 ms (P7) |
| Viewer: preview with three badges (FPS, PLAYING/PAUSED, FRAME i / N) | V2-V3 | same. Badge text gains "· 7 FPS" / "· NO SOUND" / "DROPPED" (P5, P6, P1) |
| Title row with Info (stacked) | V5 | same |
| Scrub: press or drag seeks, playback continues | V6 pauses | **differs** (P18) |
| Remove (left), prev / play / next (centre), histogram (right) | V7-V9 + Download beside Remove | Download placement **wrong** (P9) |
| Clip Metadata: 9 fields, side panel or overlay | V10-V11 | same, plus a SOUND row (P6) |
| Opens paused on frame 1; loops; prev/next by sort | V15, `D:539` | same |
| Back resets to frame 1 and rescans | Back keeps the grid (D10) | good deviation |
| No hold | hold card (D6) | right for a remote viewer, but fix the wording (P14) |
| Sound out of the Pi, no volume | `<audio>`, the device's volume (D7) | right |
| Square, compact and split layouts | width/height families (`D:466-475`) | the split family is right on a laptop. The square sizes do not fit a phone (P8) |

## Where copying the touch UI would be wrong in a browser

| Touch UI behaviour | Why it is wrong in a browser | Do instead |
| --- | --- | --- |
| Its own Back button is the only way back | the browser has a Back gesture and button (P7) | `pushState` / `popstate` |
| The screen stays on (camera display) | a phone sleeps mid-take (P7) | Wake Lock while playing |
| Long press 800 ms on a picture | the system image menu fires first (P7) | callout off, 500 ms |
| Square sizes | 390 px phones (P8) | phone rows, middle-elided names |
| Position-based clock | wrong on both screens (P1), but over Wi-Fi the error looks like broken sync | number-based clock (and U9) |
| Movie frames decoded by the device itself | the phone's own H.264 decoder is better than the Pi's software decode (P12) | `<video>` for H.264 |
| One viewer at a time | a browser has several (W10) | 503 back-off, `gone` |
| No fullscreen | a laptop has it (S7) | feature-detected button |
| Physically on the camera | the WebUI has no authentication (R4 K21) | Remove kept apart from Download (P9) |

## Compared with Cinemate's Playback pane (R1)

| Cinemate (R1 §1) | This design | Operator view |
| --- | --- | --- |
| Opens on the newest take (R1 §1.5) | opens on the grid | W2 option (P21) |
| First / prev frame / PLAY / next frame / last; Loop | clip skips only; O1, O2 options | O1 needed for long takes and the clap (P11) |
| Timecode overlay (position ÷ rate, wrong) | O10, the recorded TC | O10 yes, from the frame number (P1) |
| Rate row: Achieved, Frames skipped | O4 option | minimum honest badge by default (P5) |
| DROP N from file-name gaps | O5 option | yes. Also used by the sync fix (P1) |
| Mode boxes 12b/16b, HDR/SDR, LIN | O9 "maybe" | one line in the metadata panel ("Clear HDR 16-bit · uncompressed"). It also answers W3's lossy question (P24) |
| Lock overlay that names its reason | hold card with reasons | better than Cinemate (several reasons), once P14 is fixed |
| 409 on frames **and** WAV; the index not gated | per-request hold; the list from the cache | better. But Cinemate also never gated downloads, and this design copies that (P3) |
| Client pauses on any error | skip on 503 | better, once the back-off is added (P16) |
| One thumbnail request at a time | 2 in flight, IntersectionObserver | fine |
| No sound | `<audio>` with Range | better, once P1 and P2 are fixed |
| Delete only in the RAW pane | Remove in the viewer, like the touch UI | right for resemblance; placement (P9) |
| Conform-rate playback | O3 | ramp takes need a rule anyway (P2) |

---

## Additions for §8 (measurements on the Pi)

| # | What | How | Decides |
| --- | --- | --- | --- |
| M12 | Clap sync on a lossless take with drops, and on an uncompressed one | Two 20 s takes with claps at 2 s and 18 s; touch screen now; WebUI after T50; one run with Bluetooth headphones | P1 (U9), P25 (offset nudge) |
| M13 | Touch-screen live preview while a browser plays 16-bit 4K | Count the preview's fps (or `top -H` on Core's preview thread) with and without browser playback | R12, workers |
| M14 | The phone on the camera's hotspot | M3 from the phone; the achieved fps and the arrival time of a paused 1920 w frame | play and pause widths |
| M15 | Download during a take (only if Patrik wants it allowed) | `takes.sh 1 60` baseline, then the same while `curl -s -o /dev/null '…/api/media/download?kind=folder&id=<old take>'` runs from the laptop | P3, Q21 |
| M16 | Record right after a review | Play 60 s of a 16-bit take in the browser, then `takes.sh 1 30`; missing frames and temperature against the baseline, with and without `fadvise` | P19 |
| M17 | The list with a long take | `/api/media` time after a Core restart and warm, with a 10-min take on the card | the facts-cache key |
| M18 | A real lossy take | `playback_bench --cold` on a real `cDNG_3to1_` and `cDNG_5to1_` frame | P24 |

## Additions for §10 (risks)

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R16 | Sound and picture drift on takes with drops | CONFIRMED mechanism (P1); size PROBABLE | number clock; U9 |
| R17 | Ramp takes cut short | CONFIRMED mechanism (P2) | `fps-ramp.txt` rule; U10 |
| R18 | Downloads and the WAV stream read the card in a take | CONFIRMED (P3) | chunk check; download hold |
| R19 | The touch screen plays during a take | CONFIRMED (R2 §7) | T54 (U2) |
| R20 | A 503 storm with two viewers | PROBABLE (P16) | back-off |
| R21 | The phone layout overflows | PROBABLE arithmetic (P8) | phone rows; 390 px gate |
| R22 | Back leaves the page; the phone sleeps | PROBABLE (P7) | `pushState`; Wake Lock |
| R23 | Delete then record on the same card | CONFIRMED gate gap (P11) | `mediaDeleteActive_` (Q23) |
| R24 | Bluetooth output latency | UNCONFIRMED | M12 |
| R25 | A viewer silently switches clips after a remote delete | CONFIRMED design rule (P10) | `gone` |

## Additions for §11 (questions for Patrik)

| # | Question | Suggested default |
| --- | --- | --- |
| Q19 | Map sound time to the frame **number** (real time, honest on takes with drops), on both screens (U9)? | yes |
| Q20 | Playback in standby, and during long-interval timelapses? | hold (as designed); allow in standby as an option |
| Q21 | Downloads during a take: refuse new ones and stop running ones? | yes |
| Q22 | Bring U2 (the touch UI yields to a take) into this project as T54? | yes |
| Q23 | Refuse `record_start` while a delete is still running? | yes |
| Q24 | O4 (rate) + O5 (drops), or at least "PLAYING · 7 FPS" and "DROPPED N"? | O4 + O5 |
| Q25 | A SOUND row in the WebUI metadata (a tenth field)? | yes |
| Q26 | Play the recovered frames of an unfinalised MLV? | yes, with the line |
| Q27 | H.264 through the browser's `<video>` by default (O12)? | yes where the browser can play it |
| Q28 | A "Review last take" chip on the main page (W2)? | yes |
| Q29 | Fullscreen where the browser has it? | yes, hidden on iPhone |
| Q30 | Ramp takes: timeline view with sound off, or real time with sound (O3b)? | timeline view |

## New options (§9)

| # | Option | Cost (PROBABLE) | Suggestion |
| --- | --- | --- | --- |
| O15 | Waveform strip under the scrub (decimated peaks from the WAV, made by Core) | ~120 | yes for sync checks |
| O16 | Zoom 1:1 of the half-resolution picture when paused (a crop route) | ~80 | maybe; say "half resolution" on it |
| O17 | "Save this frame" (the 1920 w JPEG as a download) | ~15 | yes (the director sends a still) |
| O18 | Histogram in stops (both screens, with U11) | ~30 + parity | yes for Clear HDR |
| O19 | Fullscreen where available | ~20 | yes |
| W2 | "Review last take" chip | ~40 | yes |

---

## Order: what moves in the plan (§6)

| Tutorial | Add |
| --- | --- |
| T47 | Facts: `first_number`, `last_number`, `gaps`, duration from the span (P1); `ramp` from `fps-ramp.txt` (P2); `sound_state` (P6); BIT DEPTH and empty-frame rules per Q6 / P15 |
| T48 | `n=` (frame by number) and `X-Frame-Number`; `gone` in the 404 (P10); `fadvise` after each read (P19); a split LRU (P16) |
| T49 | Phone header rows and middle-elided names (P8); `pushState`; callout and `contextmenu` handling, 500 ms (P7); re-queue thumbnails on hold clear (P17); Show follows the photo mode (P21) |
| T50 | Number clock with gap hold and "DROPPED" (P1); the ramp rule (P2); the minimum honest badge, or O4/O5 (P5); the SOUND row (P6); Wake Lock and the scrub `touch-action` (P7); phone viewer rows (P8); Download moved (P9); the 503 back-off (P16); scrub resume (P18); "Live view" on the hold card (P22); hold texts (P14); the download hold and the ZIP stop (P3); the time readout (P11) |
| T51 | Hold check per chunk (P3); Range for `.mp4` if Q27 says yes (P12) |
| T52 | Recovered frames of an unfinalised MLV, if Q26 says yes (P13) |
| T53 | Movie requests serialised in order; `<video>` path if Q27 (P12) |
| T54 (new) | Touch UI: U2 hold (P4); U9 number clock (P1); U10 ramp rule (P2) |

T50's gate adds, on the Pi:

- a lossless take with claps at 2 s and 8 s;
- a ramp take once T31 is there;
- record during a WAV stream and during a ZIP download (the stream must close);
- a remote delete of the open clip;
- two browsers playing at once;
- Android Back and iOS swipe;
- the screen staying on during a 2-minute take;
- 390×844 and 844×390 screenshots in the mocked Chromium.
