# Playback T46: measurements on Patrik's Pi

Pi 5 (CM5), Core `2f4f0f6`, touch UI `92125a7`, 2026-10-29. Bench: `working/tools/playback/playback_bench`, built on the Pi
from the sketch against the Pi's current Core sources (compiled without changes). Camera idle, nothing recording.

## M1. One 4K frame, one worker (Patrik ran it; CONFIRMED)

`playback_bench --synthetic /tmp/pb-frames`: 36 of 36 checks, every sample bit-exact. Temperature 56.5 → 58.2 °C.

| Frame (synthetic, in RAM) | samples | render 640 w | one worker (640 w play frame) | paused 1920 w |
| --- | --- | --- | --- | --- |
| SDR 12-bit uncompressed (12.4 MB) | 12.9 ms | 35.0 | 50 ms = 19.8 fps | 307 ms |
| SDR 12-bit lossless (7.7 MB) | 138.6 | 31.7 | 173 ms = 5.8 fps | 406 ms |
| HDR 16-bit uncompressed (16.6 MB) | 13.4 | 33.9 | 50 ms = 20.0 fps | 286 ms |
| HDR 16-bit lossless (15.4 MB) | 156.3 | 34.5 | 193 ms = 5.2 fps | 459 ms |

`playback_bench --cold` on real takes (page cache dropped first):

| Take | samples | render 640 w | one worker | paused 1920 w |
| --- | --- | --- | --- | --- |
| C0021, Clear HDR 16-bit uncompressed (16.6 MB) | 28.3 ms (warm 13.4: the card adds about 15 ms) | 32.3 | 64 ms = 15.7 fps | 330 ms |
| C0016, SDR 12-bit lossless (7.5 MB) | 149.8 ms | 35.0 | 188 ms = 5.3 fps | 452 ms |

Reading: the Pi is about as fast as the host (the design guessed 2× slower). Reading a clip's tags cold: 0.5 ms. With two
workers: uncompressed and Clear HDR 16-bit reach the 25 fps of the take; lossless about 10 fps (PROBABLE, not run yet).
Q1 stays "yes"; O11 (preview track) not needed on this evidence. Still to measure: two workers together, a long scroll of
real frames (M7-style), M2-M19.

## M2, M5, M12 (touch half), M13: not done

No touch screen on this Pi (Patrik, 2026-10-29). See `decisions.md`, "Constraint".

## M3. Small requests per second (Patrik ran it; CONFIRMED)

`/icons/play.png`, 100 requests, one at a time and three at once (`xargs -P 3`).

| From | one at a time | three at once |
| --- | --- | --- |
| the Pi, `127.0.0.1` | 1.14 s = 88 req/s | 0.47 s = 213 req/s |
| the Mac over the LAN, `apertar.local` | 1.9-2.1 s = about 50 req/s | 0.97-1.03 s = about 100 req/s |

Reading: about 20 ms per request over the LAN (a new TCP connection each); the Pi's numbers are mostly `curl` start-up, so
Core's server is at least that fast. The prediction (well above 40 req/s) holds. Decision: the look-ahead of two lanes is
safe on the network; the decode (50-190 ms a frame) is the limit, not the server.

## M4. What the clip list costs today (Patrik ran it; CONFIRMED)

41 take folders, 105,676 files on `/media/RAW`. `GET /api/media` three times: **6.81 s, 6.81 s, 6.80 s**.

Reading: the list takes 6.8 s *every* time, warm or not, because it reads the first DNG of every take and stats every file;
nothing is cached today. With 105,676 files that is the cost T47's folder cache removes (an unchanged folder should cost one
`readdir`). Probable side effect to check in T47: while the list runs, Core's other web requests wait (the page's 1 s state
poll would stall for 6.8 s). T47's check: the list time after the cache (cold after a Core restart, warm), and `/api/state`
answering during a list.

## M8, M9, M10 (Patrik ran them; CONFIRMED)

| | Result | Decides |
| --- | --- | --- |
| M8 NVMe link | **8.0 GT/s PCIe x1** (Gen 3; the design guessed Gen 2, 5.0 GT/s) | |
| M8 one cold 16.6 MB frame, `dd iflag=direct` | 0.0207 s = **800 MB/s** | Clear HDR 16-bit at 25 fps needs 415 MB/s: not read-bound, with room for the take's own writes to be a separate question (M7/M16) |
| M9 locale | `en_GB.UTF-8` | month names are English ("28 Oct 2026"); Q15's `strftime_l` is not needed |
| M10 `libswscale` | 8.3.100; `~/ApertarUI/build/apertar-video-libav.so` exists | T53 (ProRes and H.264 in Core) has what it needs on the Pi |

## M4b. ClipProbe on your real card (Claude ran it, read-only, built in /tmp; CONFIRMED)

`ClipFactsCache` over all 39 cDNG takes (105,532 frames), reference implementation `ClipProbe.hpp`:

| | Time |
| --- | --- |
| today's `/api/media` | 6.8 s every call (M4) |
| first pass, with a readdir-count key (the design's idea) | 15.2 s first, **3.8 s cached**: a readdir of 105,000 entries costs about 3.7 s on this exFAT card, so "an unchanged folder costs one readdir" was wrong here |
| first pass, folder-mtime key, no second pass | **4.2 s once** (after a Core restart), then **7 ms** per list |

exFAT folder mtime moves with its newest entry on all three takes checked (C0016, C0022, C0025: the directory's time equals its
newest file's); `stat` of all 39 folders: 36 ms. A file written in place would not move it; frames are never rewritten.
Design change (T47): the cache key is the folder's mtime alone. Sample facts, C0016: 25 fps, 03:29 (the span), 4,913 files,
310 missing in 30 holes, "SDR 12-bit · lossless", timecode 00:00:00:00 (a Rec Run take), 32.0 GB.

## T47 live on the Pi (Claude ran it with Patrik's OK; CONFIRMED), Core `ee246ff`

| Check | Result |
| --- | --- |
| `GET /api/media`, 39 cDNG takes | **4.24 s** the first time after a Core restart, then **0.02 s** (before: 6.8 s every call). First live version, before the cache was asked ahead of the folder scan: 9.6 s, then 1.8 s |
| `GET /api/media/clip` C0016 | 1 ms; 4,913 files, first 0, last 5222, 310 missing in 30 holes, 25 fps, 03:29, "SDR 12-bit · lossless", "310 missing · 0 empty", bit depth 12-bit, size 32.0 GB, has audio; timecode_start 00:00:00:00 (a Rec Run take) |
| unknown clip | 404 "Clip not found." |
| `playback_hold` in `/api/state` | `""` idle; `"recording"` immediately after `record_start` (the yield window, before the camera's own flag) and during the take; back to `""` 2-3 s after stop (the window's 1.5 s tail) |
| in a 4 s take (`cDNG_26-10-29_C0001`, 46 of 46 frames written, 0 dropped) | list answers from the cache in 16 ms with `"held":"recording"` and 39 items; `/api/media/clip` of a cached clip: 200 with `held`; of the take being written: **409** `Playback held: recording.` |
| list after the take | 28 ms; the test take was removed afterwards |

## T48 live on the Pi (Claude ran it; CONFIRMED), Core `8d6aae9`

`GET /api/media/frame?kind=folder&id=&n=&w=`, cold, from the NVMe, Core's own HTTP time and `X-Decode-Ms`:

| Take, number, width | Time | Decode | JPEG |
| --- | --- | --- | --- |
| C0021 (Clear HDR 16-bit uncompressed) n=800, 640 w | 83 ms | 63.5 ms | 9.4 KB |
| C0021 n=800, 1920 w (paused) | 272 ms | 271 ms | 58.9 KB |
| C0016 (SDR 12-bit lossless) n=2000, 640 w | 237 ms | 166 ms | 19.7 KB |
| C0016 n=2000, 960 w | 203 ms | 201 ms | 36.7 KB |
| C0016 n=3, 640 w (frame 3) | 171 ms | 170 ms | 24.6 KB |
| C0016 n=2000, 640 w again | **0.8 ms** | cache | |

Same numbers as the bench (M1): 64 ms vs 64 ms (16-bit uncompressed), 166-170 ms vs 188 ms (lossless). With two workers: about
25 fps for Clear HDR 16-bit, 10-12 fps for lossless (PROBABLE; not yet measured with two clients). Errors: n past the end 404
"Frame not found."; width 500 400; unknown clip 404 `gone`; stale `v` 404 "The clip changed. Refresh Media." The pictures were
looked at: the touch UI's look (flat, ungraded), the right clip, no artefacts. Host test `frames_test.cpp`: 14 of 14 on the Pi.
