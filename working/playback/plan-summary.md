# WebUI playback: plan on one page (v2)

2026-10-29, designer pass v2, after the code and operator critiques. Full design: `design-playback.md` in this folder; every
critic point, accepted, changed or rejected with its evidence: `changes-from-critique.md`; v1 is `design-playback-v1.md`
(its summary `plan-summary-v1.md`). Trees: Core `eb9cc39`, touch UI `d8098d0`, Cinemate `d6cc93e`, KB `b137ae8` (HEAD
`11dad27`). Nothing ran on the Pi.

## Recommendation

1. **Same shape as the touch screen.** The WebUI folder button opens a full-screen Clip Browser and Clip Viewer with the
   touch UI's layout, controls, flow, wording and nine metadata fields, drawn with the WebUI's shell, buttons, pills and
   badges. It replaces today's list overlay. Download (in the title row, away from Remove), Select All, Timelapse and Audio
   stay. A laptop (≥ 1120 px) gets the split viewer; a phone gets the stacked viewer with its rows rearranged for 390 px,
   names elided in the middle, and the phone's Back closing the viewer.
2. **Core decodes on demand** and sends one JPEG per request. No change in the recording path, the DNG files or
   `CameraController.cpp`. Every take already on the card plays. (Cinemate turned its raw decode off, but that was a NumPy
   decoder for uncompressed frames only; Apertar's is C++ at the touch UI's own cost.)
3. **Same picture and same numbers as the touch screen.** Core gets a Qt-free copy of the touch UI's DNG rules, look and
   histogram, plus the same liblj92 file: 0 differing samples and 0 differing pixels against the touch UI's own code on
   Core-written uncompressed, lossless and lossy frames (CONFIRMED, host). The nine fields copy the touch UI's values;
   three extra rows (SOUND, FORMAT, DROPPED) say what the touch UI does not.
4. **Sound and picture stay together.** Frames are numbered by sensor time and the WAV spans the same time, so the viewer
   asks for the frame **number** at the clock. The touch UI's "n-th file" rule puts the picture 1.0 s ahead at 5 s on a
   typical lossless take and ends it 1.7 s early (host arithmetic). DURATION is the span. Speed-ramp takes (T31) play as
   their timeline with sound off.
5. **Cost.** One 4K frame on this host: 34-42 ms uncompressed, 159-202 ms lossless; lossy between the two. The Pi is about
   2× slower (PROBABLE). Two workers: Clear HDR 16-bit uncompressed near 25 fps if the NVMe gives the reads; SDR 12-bit
   lossless ~5-8 fps with frames skipped, probably what the touch screen shows today. T46 measures.
6. **Recording wins, on every path.** One pure rule answers every frame, clip, sound and download request (409 in a take,
   while writes drain, in a media test, in standby, with the media gone). A lock-free **yield window**, opened at the top of
   `handleCommand` by the commands that start a take, a capture, a test, standby or an eject, and kept open by the media
   watcher while a hold lasts, stops a decode, a WAV stream or a ZIP download within one chunk, before the take's first
   frame. Reads drop their pages, so the next take finds the page cache as the writer left it.
7. **API in Apertar's style:** HTTP routes `/api/media` (fixed: each clip's own FPS, frame numbers, span duration),
   `/api/media/clip`, `/api/media/frame?n=` (by frame number), `/api/media/file` (Range); delete waits for pending writes;
   downloads yield to a take (your call, Q21). No socket command: commands run under the command lock.
8. **Shared with the touch UI:** liblj92 (same file), the movie decoder (same two source files, built by Core, one request
   at a time per movie), named copies kept honest by a parity test. **T54 (recommended)** makes the touch UI pause in a take
   and use the same clock and duration, so both screens agree.
9. **Not chosen:** Cinemate's recorder-written JPEG in every DNG (adds work to a record path that already drops lossless
   frames, changes every file, shows the ISP look); the touch UI serving frames (not the front door); raw decode in the
   browser (16 MB a frame over Wi-Fi). A recorder-written preview track stays option O11 if lossless is too choppy.
10. **Size:** about 3,900 lines (PROBABLE); ~1,150 are already written and host-tested in the sketch.

## Tutorials (controls uses T36-T45, so this starts at T46; renumber as you like)

| # | Title | What you type and test | Time |
| --- | --- | --- | --- |
| T46 | Measure first | No code. The bench, parity and v2 checks on your Pi and your takes (cold reads, temperature); the touch screen's rate and clap sync; small requests from the laptop and the phone; your browsers and the WAV; the NVMe link; the locale; a long take's list; a real lossy frame. Optional, recording: standby, reads in a take, downloads in a take, a take right after a review | 2 h + 1 h |
| T47 | Core knows its clips | DNG tag reader (no liblj92), frame numbers and holes, the hold rule and yield window, per-clip facts in `/api/media` (each take's own FPS and span duration), `/api/media/clip`, `playback_hold` | 2 × 2 h |
| T48 | Core draws a frame | liblj92 copy, chunked sample reader that stops for a take and drops its pages, the touch UI's look, decode slots with their own memory, `/api/media/frame` by number, reason phrases | 2 × 2 h |
| T49 | WebUI Clip Browser | the touch UI's grid of cards, the old overlay's wiring replaced, thumbnails, Show / sort / Refresh, long-press selection without the phone's image menu, confirm-free Remove, Download Selected, Select All; live view stopped while open; button greyed in a take or timelapse | 2.5 h |
| T50 | WebUI Clip Viewer | badges, the number clock, scrub (plays on), prev/play/next, Remove, Download, histogram, Clip Metadata + SOUND/FORMAT/DROPPED, holds with Live view, keep-awake, keys; deletes wait for writes; downloads yield to a take | 2 × 2 h |
| T51 | Sound | `/api/media/file` with Range (206/416), stopping for a take; `<audio>` as the clock; sound recordings play | 1.5 h |
| T52 | MLV clips | MLV frame reader (copy of the touch UI's rules, VIDF frame numbers), the MLV colour path | 2 h |
| T53 | ProRes and H.264 | Core builds the touch UI's movie decoder as its own lazy plugin; one decoder per movie with a lock | 1.5 h |
| T54 | Touch UI yields and keeps time | pause in a take, hardware browser action and Remove off in a take; the number clock and span duration (recommended, Q22) | 1.5 h |

Each step has one check. Each tutorial ends in a host or Pi gate: host tests, parity and fuzz for Core; `node --check`,
the page clock test and the mocked Chromium run (no load error, 390 px and landscape screenshots) for the page; then the
Pi with a phone and a laptop. All 79 tutor refs and 14 checks were run through `tutorial.py`'s own parser and safety
filter here, and the 47 plan search strings were checked: all valid.

## Options (not defaults)

From Cinemate: O1 frame step and keys, O2 loop toggle, O3 conform-rate playback (O3b a ramp take in real time), O4 honest
rate row, O5 DROP N, O6 filmstrip, O7 Largest first and the one-row view, O8 card mini-scrub, O9 mode boxes (covered by
FORMAT), O10 the recorded timecode. Also O11 the preview track, O12 H.264 in the browser's own `<video>` (if M19 says the
plugin is slow), O13 a 16-bit WAV copy, O14 thumbnails kept on the system drive, O15 waveform, O16 1:1 zoom (half
resolution), O17 save this frame, O18 histogram in stops, O19 fullscreen, O20 keep the phone's screen on, O21 recovered
frames of an unfinalised MLV, O22 a per-device A/V offset; W1 stat chips, W2 a "Review last take" chip. Suggested: **O1,
O4, O5, O10**, and W2.

## Your calls first

**Q1** is ~5-8 fps on lossless 4K acceptable for now? **Q19** the number clock and span duration on both screens?
**Q21** refuse and stop downloads in a take? **Q22** bring the touch UI along in T54? **Q9** which options? Then Q23
(no take while a delete runs), Q25 (the three extra rows), Q2 (Show only filters), Q4 (hold thumbnails in a take), Q6 (BIT
DEPTH as the touch UI says it), Q10 (your phone), Q12 (type the 1,150 sketched lines or copy them), Q13 (commit format),
Q16 (Core's own movie plugin), Q17 (after the controls project), Q30 (ramp takes as their timeline).
