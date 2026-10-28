# WebUI playback: plan on one page

2026-10-28. Full design: `design-playback.md` in this folder. Trees: Core `eb9cc39`, touch UI `d8098d0`, Cinemate `d6cc93e`.

## Recommendation

1. **Same shape as the touch screen.** The WebUI folder button opens a full-screen Clip Browser and Clip Viewer with the touch
   UI's layout, controls, flow, wording and nine metadata fields, drawn with the WebUI's buttons, pills and cards. It replaces
   today's list overlay. Download stays. Phone portrait gets the touch UI's stacked viewer; a laptop gets the split viewer.
2. **Core decodes on demand.** Core reads Core's own DNGs and sends one JPEG per request. The recording path and the DNG files
   do not change, and every take already on the card plays.
3. **Same picture as the touch screen.** Core gets a Qt-free copy of the touch UI's decode, look and histogram, plus the same
   liblj92 file. A sketch built here matches the touch UI's own code exactly: 0 differing samples and 0 differing pixels
   at 640x360, identical histograms. It reads Core-written frames bit-exact (36 of 36 checks), and 480 fuzzed files caused no
   sanitizer report. CONFIRMED on this host.
4. **What it costs.** One 4K frame on this host takes ~37-41 ms uncompressed and ~160-170 ms lossless, the same as the touch
   UI's own path. The Pi is roughly 2× slower (PROBABLE). With two workers, Clear HDR 16-bit uncompressed takes should play
   near 25 fps. SDR 12-bit lossless takes should show ~5-8 fps, which is probably what the touch screen shows today. T40 measures it.
5. **Recording wins.** One Core function holds playback in a take, while writes drain, in standby, and when the media is
   gone. Every frame and audio request answers 409 then. `/api/state` says why, and the viewer shows the reason. No
   playback work happens during a take.
6. **Sound plays in the browser** from the take's WAV. Core gains HTTP Range for that one route. The audio clock drives the
   frames, as on the touch UI.
7. **Shared with the touch UI**: the liblj92 file, the movie plugin (`apertar-video-libav.so`, loaded by Core in T47), and
   named copies of the render and text rules, kept honest by a parity test. **The touch UI itself is unchanged.**
8. **Not chosen**: Cinemate's recorder-written JPEG (it changes every take's hot path and every DNG); the touch UI serving
   frames (not the front door); decoding raw in the browser (16 MB a frame over Wi-Fi). A recorder-written preview track
   stays option O11, if lossless playback is too choppy after T40.
9. **No change in `CameraController.cpp`.** About 3,100 lines in all (PROBABLE). ~600 are already written and host-tested.

## Tutorials

| # | Title | What you type and test | Time |
| --- | --- | --- | --- |
| T40 | Measure first | No code. Run the bench on the Pi (real takes, cold reads, temperature). Note the touch screen's rate. Time small requests to Core. Check your browsers with the WAV. Optional: standby and read-during-take checks | 1.5 h |
| T41 | Core knows its clips | DNG tag reader (part 1), `ClipProbe.hpp`, per-clip facts in `/api/media` (fixes the list's FPS and duration), `/api/media/clip` and `get_clip_info`, `playback_hold` in the state | 2.5 h |
| T42 | Core draws a frame | liblj92 copy, reader part 2, the touch UI's look (`RawRender.hpp`), `PlaybackFrames` (2 workers, LRU, 503), `Cache-Control` and reason phrases in the web server, `/api/media/frame` | 2 × 2 h |
| T43 | WebUI Clip Browser | the touch UI's grid of cards, thumbnails, sort, long-press selection, Remove Selected, Download kept, live view paused while open, button greyed in a take | 2.5 h |
| T44 | WebUI Clip Viewer | preview with badges, scrub, prev/play/next, Remove, histogram, Clip Metadata (panel or overlay), holds, keep-awake while playing, delete waits for pending writes | 2 × 2 h |
| T45 | Sound | `/api/media/file` with Range (206/416); `<audio>` as the clock | 1.5 h |
| T46 | MLV clips | MLV frame reader (copy of the touch UI's rules), the MLV colour path | 2 h |
| T47 | ProRes and H.264 | Core loads the touch UI's video plugin; facts and frames | 1.5 h |

Each step has one check. Each tutorial ends in a host or Pi gate: host test, parity test and fuzz for Core;
`node --check` and the mocked Chromium run for the page; then the Pi with a phone and a laptop.

## Options (not defaults)

From Cinemate: O1 frame step and keys, O2 loop toggle, O3 conform-rate playback, O4 honest rate row, O5 DROP N, O6
filmstrip, O7 Largest first and the one-row view, O8 card mini-scrub, O9 mode boxes, O10 the recorded timecode. Also O11 the
preview track (written by the recorder), O12 H.264 in the browser's own `<video>`, O13 a 16-bit WAV copy.
Suggested: **O1, O4, O5, O10**. Touch UI fixes for later: U1-U7 (wording, a hold, delete through Core, Core's thumbnails, bit
depth, the one-channel 4K histogram, a faster scan).

## Your calls first

Q1: is ~5-8 fps on lossless 4K acceptable for now? Q2: should "Show" only filter, or switch the camera mode? Q9: which options?
Also Q4 (hold thumbnails in a take), Q5 (grey the folder button in a take), Q10 (your phone), Q12 (type the 600 sketched lines
or copy them), and Q13 (commit format).
