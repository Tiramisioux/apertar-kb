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
| R2 | **Dropped frames show as black holes in the viewer.** | The design holds the frame before over a hole or a 0-byte frame (§2.6, §3.6 Play). Instead: when the clock is on a number in `holes` (never written, or 0-byte), the picture is **black**, no frame request, sound keeps playing on the number clock. A frame the player merely did not manage to draw (a slow decode, skipped) still holds the last picture, and O4 counts it as "skipped", so the two never get mixed up: black = the camera dropped it (DROP N, O5), held = the player was slow. T50. Paused or scrubbed onto a hole: black with the text "Frame 6 dropped". The touch UI keeps holding the previous frame until T54 (open: should T54 make it black too, so both screens agree? ask at T54). |

## Constraint (Patrik, 2026-10-29): no touch screen

Patrik's Pi has **no touch screen**, only the WebUI in a browser and the HDMI output. So T46's M2, M5 (standby while the touch
screen plays), M12's touch half (clap sync today) and M13 (touch preview while a browser plays) are **not measurable**; the
touch UI's per-frame cost is the bench's (same decoder), and the WebUI side is measured in the browser. **T54 (touch UI)
cannot be tried on a touch screen here**: it can only be built and checked by compiling and by a short HDMI/mouse look. Ask at
T54 whether it stays, shrinks to the code changes only, or waits for a touch screen.

## Note for O10 (added 2026-10-29)

The timecode the DNGs carry is now its own setting: **File timecode** (Free Run or Rec Run), apart from the UI timecode
(Core `909aaa5`, UI `7029db1`, `set_timecode_mode target=ui|files|both`). O10 shows the recorded start from DNG tag 51043,
so it shows what File timecode was set to for that take.

## Trees moved since the design

Design: Core `0296ed1`, touch UI `5aab7e2`. The Pi on 2026-10-29: Core `909aaa5`, touch UI `7029db1`. Re-check every
`path:line` against the Pi trees before T47 (the WebUI page `WebControlPage.cpp` grew by about 1,500 lines).

## Still open

nothing in the design's list. Open for T46: which phone (Q10).

## Where the build differs from the design (2026-10-29)

| Design | Built | Why |
| --- | --- | --- |
| facts cache keyed on (folder mtime, entry count) | the folder mtime alone | a readdir of 105,000 entries costs 3.7 s on Patrik's exFAT card; the mtime moves with the newest entry (checked) |
| ask ahead by the round trip, at most two frames | the round trip, at most 0.35 s | two requests are ever in flight; with the sound as the clock a lossless picture trailed it by 7 frames; now 0-2 |
| hold the frame before over a hole | black over a hole (R2); Core's thumbnails still hold | Patrik, 2026-10-29 |
| nine metadata rows + SOUND, FORMAT, DROPPED | plus TIMECODE (R1/O10) | Patrik |
| card: duration pill only | plus DROP N and the recorded timecode | O5, R1 |
| T47-T54 as tutorials Patrik types | Claude built T47-T51 (T46 measured with him) | Patrik, 2026-10-29: "to T48 yourself", "go ahead", "move on" |
| `sketch/` copied from the KB | `working/tools/playback/` (headers, tests, `ClipProbe.hpp` and `PlaybackFrames.*` written new) | the sketch had no ClipProbe or frame service |
