# Playback project: Patrik's decisions

Answers to the questions in `design-playback.md` §11 and the options in §9. Each row: the question, the answer, the date.
A row marked *default* means Patrik accepted the design's default.

## Answered (2026-10-29, in the VS Code session)

| # | Question | Answer | What it means |
| --- | --- | --- | --- |
| Q1 | ~5-8 fps for lossless 4K acceptable for now? | **Yes, decide after T46** (default) | No preview track (O11) now. T46 measures the lossless rate on the Pi; O11 only if it is too choppy. |
| Q19 | Sound and picture follow the frame number, DURATION is the span, on both screens? | **Yes, both screens** (default) | WebUI uses the number clock. The touch UI gets it in T54. |
| Q21 | Downloads in a take: refuse new, stop running? | **Yes** (default) | Downloads (file, ZIP) yield to a take: 409 while a take runs, a running download stops within one chunk. |
| Q22 | Bring the touch UI along as T54? | **Yes** (default) | T54 stays: pause in a take, number clock, span duration. |
| Q9 | Which Cinemate options? | **O1, O4, O5, O10** (default) | O1 frame step and keys; O4 honest rate row; O5 DROP N badge; O10 the recorded timecode. W2 and the rest not chosen yet. |

## Note for O10 (added 2026-10-29)

The timecode the DNGs carry is now its own setting: **File timecode** (Free Run or Rec Run), apart from the UI timecode
(Core `2f4f0f6`, UI `92125a7`, `set_timecode_mode target=ui|files|both`). O10 shows the recorded start from DNG tag 51043,
so it shows what File timecode was set to for that take.

## Trees moved since the design

Design: Core `eb9cc39`, touch UI `d8098d0`. The Pi on 2026-10-29: Core `2f4f0f6`, touch UI `92125a7`. Re-check every
`path:line` against the Pi trees before T47 (the WebUI page `WebControlPage.cpp` grew by about 1,500 lines).

## Still open

Q2-Q8, Q10-Q18, Q20, Q23-Q30.
