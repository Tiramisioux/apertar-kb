# Merge review: paused on 2026-11-20 (first paused 2026-11-17)

Patrik asked to pause. All worker agents are stopped. Nothing is half-written on a pushed branch: every pushed
commit passed its gate. Work that was still in flight is saved as patches in `lanes/`. This page says where things
stand and how to pick the campaign up again.

## Since the first pause (2026-11-20, a short session)

| What | Result |
| --- | --- |
| 11 more Core commits, integrated and pushed | C20 to C30 in `fix-log.md`: two hardware-store bugs, the first five command-plane commits (`get_controls` and `controls_history` become `GET /api/config` and `GET /api/config/history`; the I2C scan gives up after 1 s; `list_actions` slimmer; three commands take the command lock), three hardware-file commits |
| Your Q2 (script paths over ssh only) | Kept, as a switch: `APERTAR_SCRIPT_PATHS=ssh` in Core's environment. Unset, a stock camera behaves as 1.6.0 (C28, C29) |
| Your KB tools | `working/tools/controls_page_test.js` serves both the old commands and the new routes and can run with any Chrome (`CHROME=<path>`); `tutorials/tutorial.py` lets `GET /api/config` through and still refuses writes. The page test stops at the same check on `cinemate-port` and on the improvement branch: it was out of date before this review |
| Checks | Both Core builds, the 18 host tests, and the 1.6.0 reply-shape check (`tools/bin/shape_subset.py`: every 1.6.0 field present with the same type) pass at the pushed tip `8bfc242` |
| Audit of touch-ui, camera-modes, boot-config-helpers and the fixes made | Started again and stopped again at your pause, while still reading. Nothing written. To be re-run first on resume |
| Held | The step-list fix (FPS and ISO lists end at the last listed value, `lanes/core-bugs/`): it reverses something marked as your request 24 (T33), so it waits for the audit |
| Tooling | The workflow runner is switched off in this session; work runs through individual agents instead. The implementer instructions are saved in `tools/workflows/implementer-prompt.md`. The brief now points agents at read-only `cinemate-port` checkouts (`/home/user/wt/core-port`, `/home/user/wt/ui-port`); the checkouts `/home/user/Apertar-Core` and `/home/user/Apertar-UI` sit at an older improvement tip and are not used |

## In short

- **Is `cinemate-port` ready to merge into Apertar main? No, not yet.** The review found 598 issues, merged into 240
  fix items: 5 blockers, 66 major, 142 minor, 22 nit (`fix-list.md`). 24 fixes are made and pushed. The large reworks
  are designed (eight plans in `design/`), and the first of them were being implemented when the pause came.
- **One thing changed the plan late in the session.** The rework plans were written from the code and the review
  findings, without your earlier decisions in this KB (`working/controls/decisions.md`,
  `working/playback/decisions.md`, the fork log and others). I found that by chance (script paths, see fix log
  C8 and the rewritten hardware-inputs commit 2), stopped, and started an audit of every plan against all 211
  decisions you recorded. The audit is five-eighths done. Its rule: **a decision of yours stays. Where it makes a
  stock camera behave differently from Apertar 1.6.0, it becomes something the operator turns on, not something
  that is removed.**
- **Nothing you run today has been changed.** `cinemate-port` and `main` are untouched in every repo. All work is on
  `claude/awesome-pasteur-qzsiow` branches behind draft pull requests.

## What is pushed

| Repo | Draft PR | Base | Holds |
| --- | --- | --- | --- |
| Apertar-Core | #7 | `cinemate-port` | 30 commits: fix log C1 to C30 (C3, C9, C10, C28, C29 are the lead's) |
| Apertar-UI | #1 | `cinemate-port` | 3 commits: fix log U1 to U3 |
| imx283-v4l2-driver | #1 | `cinemate-port` | 1 commit: fix log D2-1 |
| apertar-coding-map | #1 | `main` | 2 commits: 50 corrections to the existing map (step 1 of 2) |
| apertar-kb | #16 | `main` | This folder: review, findings, plans, logs, tools, lanes |

The pushed Core fixes, by kind (the reasoning for each is in `fix-log.md`):

| Kind | Fixes |
| --- | --- |
| Your request | C1: the GPIO chip is a setting again (pins on another chip, for example a microcontroller) |
| Stock defaults back to 1.6.0 | C2 + U1 display fallback 720x720; C3 + U2 audio outline off; U3 HDMI timecode white until set; C5 automatic pre-roll off; C6 lossy DNG page-cache drop; C7, C9, C10 preview temporal denoise (on by default, never changes H.264 or ProRes) |
| Protocol, security | C4 duplicate `media_state`; C8 `test_input` refuses script actions |
| 12-bit Clear HDR | C11 storage depth after a cDNG/MLV switch; C12 "4K Clear HDR" starts at 3840x2160; C13 binned 1920x1080 held back (interim, probable cause); C14 clip labels |
| Bugs | C15 playback JPEG handle leak; C16 clip-name example without disk probes under the camera lock; C17 part folders made by the writers; C18 audio writer queue bounded; C19 `audio_url` encoding |
| Hardware file and command plane (2026-11-20) | C20, C21 hardware-store bugs; C22 to C26 command plane; C27 to C30 whole-file saves (report instead of refuse, script-path rule as a switch, sanity checks) |

Every one of these passed: Core built with and without libcamera, the host tests (18 now), and a comparison of the
reply shapes against the build before. None was run on a camera. Each fix-log entry names the check to run on the Pi.

## What was in flight (saved as patches in `lanes/`)

These commits exist only in the review container and as `.patch` files here. Each passed its own gate. "Reviewed"
means a second worker accepted it. None is on a pushed code branch yet, because I had not read them all, and
because of the audit below.

| Lane (folder) | Commits | Reviewed | Audit | On resume |
| --- | --- | --- | --- | --- |
| Bugs (`core-bugs/`) | 1 left: FPS/ISO step lists end at the last listed value (the other two are in, C20 and C21) | yes | **held**: may reverse your request 24 | wait for the audit |
| Command plane | the first 5 are in (C22 to C26); commits 6, 7, 8, 10, 15, 16 not started; 9 waits for the Boot Config audit; 11 to 14 overlap the touch UI and storage plans | - | done | next lane |
| Hardware inputs | 3 are in, plus the script-path switch (C27 to C30); commits 4, 6 to 11, 15, 16 not started (5 and 12 dropped by the audit; 13 and 14 were the bug fixes C20, C21) | - | done | next lane |
| Camera modes (`core-camera-modes/`) | 5: tables list both 1.85:1 heights; a size follows the height the driver has; pills send what they show; readout check accepts the original driver; auto fallback back | 4 of 5 | **not done** | audit first, then integrate |
| Touch UI (`ui-touch-ui/`) | 11: invokables return bool; Log and Write Buffer as dropdowns; poll reset; events through `applyCoreState`; presets carry the new settings; timecode (tap sets both again unless set apart); labels; caps | 11 of 11 | **not done** | audit first. You have no touch screen: these are compile-checked only, and each needs a look on HDMI with a mouse |

`lanes/*/uncommitted-work.diff` holds what a worker was in the middle of when it was stopped (command plane commit 8,
touch UI commit 18). Treat those as scraps.

## What the audit found so far

Full tables: the last section of each plan page, and `design/decisions-audit-summary.md`. The ones that change work:

| Plan | Conflict with your decision | What happens instead |
| --- | --- | --- |
| hardware-inputs 2 | Q2: script paths are set over ssh only | Kept. Undo, History and restore may put back a version the camera saved before (done by hand, commit `476ca75` in the lane). Open point from the audit: on a stock camera the rule itself differs from 1.6.0, so it may need a switch that is off by default |
| hardware-inputs 5 | Q17: a stale text save merges per key and is shown as a review | Commit dropped. The merge stays |
| hardware-inputs 10 | "Like Cinemate": a button that reads pressed at start is inverted | Kept as a section key (`invert_on_start`, off by default, shaped like upstream's `reset_on_start`). Your rig turns it on if it has normally-closed buttons |
| storage-settings 17, 18 | You asked for the media tuning file (2026-11-02) | Kept, with its override and `apertar-tune`. Only the process-wide statics go |
| storage-settings 20, 21, 23 | Campaign and dual-sensor plans use `APERTAR_AUDIO_BUFFER_MS` and the phase-lock knobs; `conform_fps` is your request | Those stay. The rest of the knob clean-up stands |
| preroll 13, 14 | `longtakes.py` sends `storage_preroll` | No rename |
| preroll 4 | `e3-unit.sh` and `takes_from_journal.py` parse the pre-roll journal line | The line keeps its form |
| preroll, storage | Dual-sensor plan starts the second Core with `APERTAR_STORAGE_PREROLL=0` | The env switch stays |
| webui-state 11, 12, 14, 22, 23 | Clip Browser and Viewer were designed with you: Remove dialog, eyebrow and titles, SHOW menu, sort chip, round transport buttons, Back closes the viewer, hold-to-repeat on frame step | All kept. The page parts are rebuilt from the WebUI's own classes underneath; what you chose stays as it looks and behaves |
| webui-state 20 | "White SVG blueprint sketches", no manual ladder ordering | No blanket ban on SVG; no Up/Down buttons on the ladder |

Three things already pushed touch a decision of yours. They are right for a stock camera, and your rig needs one
step each (see "Before you put the improvement branch on the rig"):

| Fix | Your decision | Effect on your rig |
| --- | --- | --- |
| C5 pre-roll off by default | Campaigns: "the pre-roll stays ON as in real use" | The copy of your hardware file in this KB (`working/tools/controls_fixture_apertar-hardware.conf`, 2026-11-08) has no `preroll` key, so the pre-roll stops running by itself |
| U3 HDMI timecode white until set | Red timecode on all three screens | HDMI turns white unless `recordingRedTimecodeEnabled` is in `UI.conf` |
| C9 preview temporal denoise on by default | Off, for 4K Clear HDR 16-bit at 25 fps | Stays off only if `preview_tdn=false` is already saved |

The audit of the fixes made, of touch-ui, of camera-modes and of boot-config-helpers was not finished (started twice, stopped at both pauses while still reading).

## Held for you (nothing was done)

| Item | Why held |
| --- | --- |
| FPS ceilings and lossless limits back to 1.6.0 (camera-modes 6, 7) | Your decision DB-52: the ceiling comes from the sensor probe; lossless ISO 1600 and auto ISO are yours. Needs a form where a stock camera keeps 1.6.0 limits and your rig keeps its own |
| imx585 driver back to 3840x2076 / 1920x1038 (camera-modes 14) | New sensor window (start row 52) that nobody has recorded with. Core will work with both heights once the camera-modes lane is in |
| DNG copy worker closures (camera-modes 11) | Changes the recording hot path; only a Pi can show it is safe |
| Clip-name drag and drop removal (touch-ui 19, 20, 22) | Your feature |
| IMX585 fps list ending at 60 (touch-ui 17) | Your rig uses 100 and 120 |
| Slow medium judged removed after 5 s (REC-8) | Changes the dead-medium logic you tested |
| Boot Config: free-text editor, `sudo -n install` route | Security blocker HW-1; plan ready, not audited |
| Everything in `owner-decisions.md` | 31 questions. The audit shows several are already answered by your recorded decisions; that page must be redone after the audit |

## Before you put the improvement branch on the rig

Your camera has no touch screen (HDMI and WebUI only), so check these first:

| Check | Why |
| --- | --- |
| `grep -n "ui_width\|ui_height\|ui_layout\|hdmi_external_only" ~/apertar-hardware.conf` | The display fallback is the stock 720x720 touch panel again (C2, U1). The KB copy of your file (2026-11-08) has all four keys (1920, 1080, landscape_large, true), so nothing should change. If the live file lost them, the HDMI-only layout is gone until they are back |
| `grep preview_tdn ~/.config/apertar-core/camera_settings.conf` | If the line is missing, switch "Preview temporal denoise" off once in the WebUI before a 4K Clear HDR 16-bit take (C9) |
| Send `set_storage_preroll value=on` once, or add `preroll=on` under `[media]` in `~/apertar-hardware.conf` | The automatic pre-roll is off by default now (C5) |
| Add `Environment=APERTAR_SCRIPT_PATHS=ssh` to a drop-in of `apertar-core.service`, then `sudo systemctl daemon-reload` and restart Core | Keeps your Q2 on the rig: the WebUI cannot set a new script path (C29). Without it the rig behaves as a stock camera (1.6.0: the WebUI may change script paths) |
| `grep recordingRedTimecodeEnabled ~/.config/CinePi/UI.conf` | HDMI timecode is red only when the key is in the file (U3). Switching "Red timecode" off and on once in the WebUI writes it |
| Binned 1920x1080 in 12-bit Clear HDR is not offered (C13) | Interim for the probable cause of the strange output. Reverting commit `a36c52f` brings it back |

## The 12-bit Clear HDR question

`hdr12/REPORT.md`. Three defects were confirmed in code and are fixed (C11, C12, C14). The most likely cause of the
strange picture (binned 1920x1080 at 12-bit decoded with the full-resolution curve, mid-tones about 16 times too
dark) is **probable, not confirmed**: it needs one capture pair from the camera. Three answers would settle a lot:

1. Where did the output look strange: the monitor picture, the DNGs in a grading program, or both?
2. At which size, and how did you enter 12-bit Clear HDR (touch "4K Clear HDR", WebUI pill, a button)?
3. Did you switch between cDNG and MLV while in Clear HDR?

## How to resume

Say "resume the campaign". The order I would take (the first step is the audit, which was stopped twice):

1. Finish the audit (touch-ui, camera-modes, boot-config-helpers, fixes made). Redo `owner-decisions.md` from it:
   fewer questions, each with the decision you already made next to it.
2. Apply the audit's variants to the plans. Integrate the audited lanes (bugs, command plane, hardware inputs).
3. Continue the lanes: camera modes, touch UI, then Boot Config (security), then storage settings and the pre-roll
   (both touch recording, so they go last and in small steps), then the WebUI page.
4. Raspberry Pi model fixes (16 findings), then the comment and slop pass, then the clean commit series.
5. Deliverables still to write: `developer-handoff.md` with the short changelog, `commit-plan.md`, coding map
   step 2 (what the port added), and the rules promoted into `llm/` and `architecture/`.

If the review container is gone by then, nothing is lost:

| Thing | Where it is |
| --- | --- |
| Pushed fixes | The `claude/awesome-pasteur-qzsiow` branch of each repo |
| Lane commits | `lanes/<lane>/*.patch`. On a checkout of the improvement branch: `git am <folder>/*.patch` |
| Gate scripts, agent workflows | `tools/` (paths are the container's; adjust) |
| Findings | `raw/FINDINGS.json`, `fix-list*.md` |
| Plans | `design/*.md` |
| Your recorded decisions, collected | `owner-recorded-decisions-a.md`, `owner-recorded-decisions-b.md` |

## Lessons from this session (for the next one)

| Lesson | What to do |
| --- | --- |
| The KB holds decisions the code does not show | Before designing any rework, read the decision pages of the feature. The collected list is now in this folder |
| A finding signed by a reviewer and a skeptic can still be wrong | Open the code before acting (fix log C10: processed stills are developed from the raw frame, not from the ISP) |
| Two gates at once can break a host test that uses a fixed temp folder | Each gate has its own `TMPDIR` now (`tools/bin/check_core.sh`) |
| Save often | `tools/bin/save_all.sh` copies tools and lane patches here and pushes |

## Paused 2026-11-21 (tokens), Dynamic resolution build

- Integrated and pushed: W1 web lever lines (C77), U1 touch lever lines (U18). Core review branch at 57da4eb, UI at 0981e32.
- Lane `lane/dr-core` (/home/user/wt/lane-dr-core), NOT integrated: bd99a8b CM6 fps ceiling, c74016d CM10 ladder in camera_settings.conf, 7588d82 D1 known-limits table, 0817904 D2 limit fields (notes 01-04 in /home/user/build/sim/notes/drcore), then a WIP commit for D3 (unfinished, ungated: finish or drop it first).
- Next: resume a Sonnet worker on lane-dr-core for D3 and D7 (instructions file there), gate, cherry-pick onto work/improve, push, fixlog C78.. Then D4, D5, D6, D8, D9; W2, W3; U2. Put "Automatic turns it on above 32 fps" in the Split lines with D5.
- cinemate-port was fast-forwarded to clip-split on GitHub (Core 05fb8f1, UI 371e1eb), as Patrik asked.
- Setup pages and extra files: setup/ (zips sent). Waiting: Patrik copies his rig files from the Pi (apertar-rig-files.zip) to add unchanged.

## Resumed 2026-11-22: Patrik's test of cinemate-port (screenshots)

His camera runs cinemate-port, not the review branch. Lanes started:
- `lane/web2` (/home/user/wt/lane-web2), notes `notes/web2`: P1 pill names (Clear HDR in full, 1.6.0 names and order), P2 dropdown in hierarchical order, P3 white Active / grey Activate, P4 Clip timecode cannot be selected, P5 Custom clip name cannot be clicked.
- `lane/ui3` (/home/user/wt/lane-ui3), notes `notes/ui3`: T1 HDMI shows Clip timecode although UI timecode is Time of Day.
- `lane/dr-core` resumed: D3 (Activate blocked by the old validator is fixed by the enabled list), D7.
