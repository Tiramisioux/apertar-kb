# WebUI playback: plan on one page

2026-10-28, designer pass v1 (resumed after the pause). Full design: `design-playback.md` in this folder; what changed from
the paused draft is its §12. Trees: Core `0296ed1`, touch UI `5aab7e2`, Cinemate `d6cc93e`, KB `e8eeef2`. Nothing ran on
the Pi.

## Recommendation

1. **Same shape as the touch screen.** The WebUI folder button opens a full-screen Clip Browser and Clip Viewer with the
   touch UI's layout, controls, flow, wording and nine metadata fields, drawn with the WebUI's shell, buttons, pills and
   badges. It replaces today's list overlay. Download, Select All, Timelapse and Audio stay. A phone gets the touch UI's
   stacked viewer; a laptop (≥ 1120 px) gets the split viewer with the Clip Metadata panel.
2. **Core decodes on demand** and sends one JPEG per request. No change in the recording path, the DNG files or
   `CameraController.cpp`. Every take already on the card plays.
3. **Same picture as the touch screen.** Core gets a Qt-free copy of the touch UI's DNG rules, look and histogram, plus the
   same liblj92 file. On Core-written uncompressed, lossless and lossy frames: 0 differing samples, 0 differing pixels,
   identical histograms against the touch UI's own code; 480 fuzzed files, no sanitizer report. CONFIRMED (host).
4. **Cost.** One 4K frame on this host: ~37-42 ms uncompressed, ~160-190 ms lossless, the same as the touch UI's path. The
   Pi is about 2× slower (PROBABLE). Two workers: Clear HDR 16-bit uncompressed near 25 fps (if the NVMe link gives
   415 MB/s), SDR 12-bit lossless ~5-8 fps with frames skipped, probably what the touch screen shows today. T46 measures.
5. **Recording wins.** `playbackHoldReason()` refuses every frame and sound request (409) in a take, while writes drain,
   in a media test, in standby, or with the media gone; a decode in flight stops at the next tile. `/api/state` says why
   (`playback_hold`), the viewer shows it in words. No playback read touches the card during a take.
6. **Sound plays in the browser** from the take's WAV, with HTTP Range in Core; `<audio>` is the clock, as on the touch UI.
7. **API in Apertar's style:** HTTP routes `/api/media` (fixed: each clip's own FPS and duration), `/api/media/clip`,
   `/api/media/frame`, `/api/media/file`; delete stays with one more gate. No socket command: commands run under the
   camera's command lock, and a slow read on a pulled card would block `record_stop`.
8. **Shared with the touch UI:** liblj92 (same file), the movie decoder (same two source files, built by Core, T53),
   named copies of the render, histogram and text rules kept honest by a parity test. **The touch UI does not change**;
   eight small fixes (U1-U8) are options.
9. **Not chosen:** Cinemate's recorder-written JPEG in every DNG (adds work to a record path that already drops lossless
   frames, changes every file, shows the ISP look); the touch UI serving frames (not the front door); raw decode in the
   browser (16 MB a frame over Wi-Fi). A recorder-written preview track stays option O11 if lossless is too choppy.
10. **Size:** about 3,000 lines (PROBABLE); ~600 are already written and host-tested in the sketch.

## Tutorials (controls uses T36-T45, so this starts at T46; renumber as you like)

| # | Title | What you type and test | Time |
| --- | --- | --- | --- |
| T46 | Measure first | No code. The bench and the parity test on your Pi and your takes (cold reads, temperature); the touch screen's rate; small requests through Core; your browsers and the WAV; the NVMe link; the locale. Optional: standby during passive playback, reads during a take | 1.5 h |
| T47 | Core knows its clips | DNG tag reader (part 1), `ClipProbe.hpp`, per-clip facts in `/api/media` (fixes FPS and duration), `/api/media/clip`, `playback_hold` in the state | 2.5 h |
| T48 | Core draws a frame | liblj92 copy, reader part 2, the touch UI's look (`RawRender.hpp`), `PlaybackFrames` (2 workers, LRU, 503, abort on a hold), JPEG stills, reason phrases, `/api/media/frame` | 2 × 2 h |
| T49 | WebUI Clip Browser | the touch UI's grid of cards, thumbnails, Show / sort / Refresh, long-press selection, Remove / Download Selected, Select All; live view stopped while open; button greyed in a take | 2.5 h |
| T50 | WebUI Clip Viewer | preview with badges, scrub, prev/play/next, Remove, Download, histogram, Clip Metadata (panel or dialog), holds, keep-awake while playing, keys; delete waits for pending writes | 2 × 2 h |
| T51 | Sound | `/api/media/file` with Range (206/416); `<audio>` as the clock; sound recordings play | 1.5 h |
| T52 | MLV clips | MLV frame reader (copy of the touch UI's rules), the MLV colour path | 2 h |
| T53 | ProRes and H.264 | Core builds the touch UI's movie decoder as its own lazy plugin; facts and frames | 1.5 h |

Each step has one check. Each tutorial ends in a host or Pi gate: host test, parity test and fuzz for Core; `node --check`
and the mocked Chromium run for the page; then the Pi with a phone and a laptop. All 52 tutor refs and 11 checks were run
through `tutorial.py`'s own parser and safety filter here: all valid.

## Options (not defaults)

From Cinemate: O1 frame step and keys, O2 loop toggle, O3 conform-rate playback, O4 honest rate row, O5 DROP N, O6
filmstrip, O7 Largest first and the one-row view, O8 card mini-scrub, O9 mode boxes, O10 the recorded timecode. Also O11
the preview track (written by the recorder), O12 H.264 in the browser's own `<video>`, O13 a 16-bit WAV copy, O14
thumbnails kept on the system drive; W1 today's stat chips on the cards. Suggested: **O1, O4, O5, O10**.

## Your calls first

**Q1** is ~5-8 fps on lossless 4K acceptable for now? **Q2** should "Show" only filter the list, or switch the camera's
photo mode like the touch UI? **Q9** which options? Then Q4 (hold thumbnails in a take), Q5 (grey the folder button in a
take), Q6 (BIT DEPTH as stored), Q10 (your phone), Q12 (type the 600 sketched lines or copy them), Q13 (commit format),
Q16 (Core's own movie plugin), Q17 (after the controls project).
