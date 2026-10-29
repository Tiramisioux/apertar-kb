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

## Defaults accepted (Patrik, 2026-10-29: "accept the defaults")

| # | Question | Answer (the design's default) |
| --- | --- | --- |
| Q2 | "Show" filters only, or switches photo mode? | filter only (opens on Stills in photo mode) |
| Q3 | Keep Download, Select All, Timelapse and Audio categories? | yes |
| Q4 | In a take: hold everything or let cached thumbnails through? | hold everything |
| Q5 | Grey the folder button in a take and a timelapse? | greyed |
| Q6 | BIT DEPTH wording | copy the touch UI's now; fix both later (U5) |
| Q7 | Touch-UI quirks | fix the "1 item" wording; copy the one-channel 4K histogram for parity until U6 |
| Q8 | Without a WAV, late frames | skip them (wall clock), do not slow down |
| Q10 | Phone | design for iPhone and Android; test on Patrik's own (tell me which when T46 asks) |
| Q11 | Keep the camera awake while a clip plays | yes (not while paused) |
| Q12 | Numbering; type or copy the sketch | T46-T54; Patrik types the changes, the sketch is a reference (his standing rule) |
| Q13 | Commit format | the house format (area, imperative, Why, Tested). A commit Patrik types from a tutorial has no Co-Authored-By (apertar-dev skill) |
| Q14 | Touch UI takes clip facts from Core | later, after T50 |
| Q15 | Month names | follow the Pi's locale |
| Q16 | Movie decoder | Core builds its own copy |
| Q17 | Order | after the controls project (T36-T45) |
| Q18 | Space = play/pause on a laptop | yes |
| Q20 | Playback in standby and long-interval timelapses | hold |
| Q23 | Refuse `record_start` while a delete runs | yes ("Deleting media. One moment.") |
| Q24 | O4 and O5 with T50 | yes (matches Q9) |
| Q25 | SOUND, FORMAT, DROPPED rows | yes |
| Q26 | Recovered frames of an unfinalised MLV | yes, with the line |
| Q27 | H.264 through the browser's `<video>` | decide after measurement M19 |
| Q28 | "Review last take" chip (W2) | yes |
| Q29 | Fullscreen (O19) | yes, hidden on iPhone |
| Q30 | Ramp takes | timeline view, sound off |

With Q28 and Q29: W2 and O19 are now also in, in addition to O1, O4, O5, O10.

## New requirements (Patrik, 2026-10-29)

| # | Requirement | What it changes in the plan |
| --- | --- | --- |
| R1 | **The Clip Browser card also shows the clip's timecode.** | T47: each `/api/media` item gets `timecode_start` ("14:03:22:07"), read from the first frame's DNG TimeCodes tag (51043, the same read O10 uses in the viewer); MLV from its timecode record, ProRes/H.264/sound from their own tag where there is one, else the field is empty and the line hidden. T49: one more line in the card footer (B18) after the shot date, in the touch UI's small muted style. Open: whether the touch UI's card gets it too (T54). It is the *File timecode* the take was recorded with (Free Run = time of day, Rec Run = starts at 00:00:00:00), so a Rec Run take shows 00:00:00:00. |

## Note for O10 (added 2026-10-29)

The timecode the DNGs carry is now its own setting: **File timecode** (Free Run or Rec Run), apart from the UI timecode
(Core `2f4f0f6`, UI `92125a7`, `set_timecode_mode target=ui|files|both`). O10 shows the recorded start from DNG tag 51043,
so it shows what File timecode was set to for that take.

## Trees moved since the design

Design: Core `eb9cc39`, touch UI `d8098d0`. The Pi on 2026-10-29: Core `2f4f0f6`, touch UI `92125a7`. Re-check every
`path:line` against the Pi trees before T47 (the WebUI page `WebControlPage.cpp` grew by about 1,500 lines).

## Still open

nothing in the design's list. Open for T46: which phone (Q10).
