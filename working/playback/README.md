# Playback project: WebUI playback like the touch UI's clip browser and player (design v2, 2026-10-29)

Patrik's brief: port Cinemate's playback in the most Apertar-like style. His decision (2026-10-28): the WebUI playback looks
and behaves like the touch UI's Clip Browser and Clip Viewer; Cinemate supplies the browser-side mechanics and optional
extras.

Status (cloud, 2026-10-29): designed, critiqued and revised in a cloud session. Trees read:
Core `0296ed1`, Apertar-UI `5aab7e2`, Cinemate `d6cc93e`, the KB. Hand-over to Claude in VS Code: `HANDOFF-PROMPT.md`.
Tutorials are numbered T46-T54 because the controls project uses T36-T45.

**Built since (VS Code session, 2026-10-29): T47-T51, Claude on the Pi's `cinemate-port`, Patrik's choice.** See `HANDOFF-next.md` (where it stands, what is
open), `decisions.md` (Patrik's answers and requirements), `measurements.md` (what ran on the Pi). Core `f91fafa`/`ab4cc92` (T47), `1af26c8` (T48),
`bc12c0a`/`27eac5a` (T49), `4629de2`/`a37a902` (T50), `fa19856`/`4fa0432` (T51); fork-log has the rows. Not built: T52 MLV, T53 ProRes and H.264, T54
touch UI (no touch screen on this Pi), the extras W2 and O19.

| File | What |
| --- | --- |
| `plan-summary.md` | one page: the recommendation, the tutorials T46-T54, the Cinemate options O1-O22, the questions |
| `design-playback.md` | the design (v2): how both players work today, the decision, Core's routes and frame decoder, the yield-to-recording rule, the touch-UI-to-WebUI element map, the plan file by file, tutorial outlines with tutor blocks, measurements, risks, questions |
| `changes-from-critique.md` | each critic point, accepted, changed or rejected, with its evidence |
| `critique-code.md`, `critique-operator.md` | the two critiques of v1 |
| `r1-cinemate-playback.md` … `r4-kb-playback.md` | the reader reports: Cinemate's Playback pane, the touch UI's Clip Browser and Clip Viewer (its anatomy, the model for the WebUI), Core's media layout and web server, the KB and the Cinemate handbook |
| `design-playback-v1.md`, `plan-summary-v1.md` | v1, kept for reference |
| `sketch/` | host-tested sketch (~1,150 of the ~3,900 planned lines): `src/playback/*.hpp` (DNG tag reader, frame numbers and holes, decode slots, the hold rule, the touch UI's look), `third_party/liblj92/` (the touch UI's lossless JPEG decoder, with its LICENSE), `page/playclock.js` (the number clock, 16 checks with `node page/playclock_test.js`), `v2_test.cpp` (38 checks), `parity/` (0 differing pixels against the touch UI's own code), `reader_fuzz.cpp`, `sizes_test.cpp`, `playback_bench.cpp`, the host results `*-host.txt`. Build lines are at the top of each `.cpp`. The test DNG frames (4-25 MB each) are left out of the KB; design §6 row 4.7 says how the host checks make and use them |
| `mockup/` | the WebUI playback mockup (laptop Clip Browser and split Clip Viewer, phone browser, viewer and the hold during a take), live at https://claude.ai/artifact/L2GAEjYDob8aPh1m6qRWZU (private to Patrik); `.dc.html` design files |

| `decisions.md`, `measurements.md`, `HANDOFF-next.md` | Patrik's decisions (Q1-Q30 defaults, R1 timecode on the card, R2 dropped frames black), the measurements on his Pi, and where to pick up |
