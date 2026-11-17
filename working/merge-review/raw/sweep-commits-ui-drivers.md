# Sweep X7c: commit series, UI and drivers

Read at: UI `cinemate-port` 7ea9afc vs `origin/main` 4415a55 (39 commits); imx585 `cinemate-port` cd548ef vs `origin/apertar` e5b74d3 (55); imx283 `cinemate-port` 68b7dc9 vs `origin/master` (93). Claims are **confirmed** (read in git) unless marked.

## 1. UI series (39 commits, all Patrik Eriksson, 2026-10-26 to 11-08)

Classes: F feature, X fix of an earlier port commit, W appearance/wording churn, R revert, E experiment (added, later dropped), S squash of earlier commits.

### 1.1 Classification and Core pairing

| # | sha | subject (short) | class | Core commit(s) it needs |
| - | --- | --------------- | ----- | ----------------------- |
| 1 | 160898c | follow Core's media state | F | 70e8376 (media_state in get_state), 0b1632f, a3ac8da |
| 2 | dc471c1 | automounter releases a pulled card | F, UI only | none; same theme as Core 438a342, 0b1632f |
| 3 | 2d27c46 | 16-bit counts as 16 bits in frame-size estimate | X (of fork-main 16-bit work) | none |
| 4 | d1efb67 | 4K Clear HDR 16-bit FPS up to 25 | F, now wrong (1.4) | b5847c7; undone in Core by 31d5418 |
| 5 | ec9f109 | FPS picker sends only set_fps in a ramp take | F | faa2958, 92b4be3 (fps_speed_ramp) |
| 6 | f1edf96 | camera-set values green; ISO list follows iso_max; ISO lock | F | 8175273, 646a194, 6d217c7, e25fd2b |
| 7 | 1367b7f | bit depth + Clear HDR on resolution line | F | eaf9538 |
| 8 | 2475626 | "16 b" not "16-bit" | W | e58ae40 |
| 9 | ed0d7b5 | pickers follow value lists, greyed above ceiling (T33) | F | b0e90ad, ff33d2d |
| 10 | 1a691a9 | "16-bit" again | R of #8 | fee41e6 |
| 11 | b4591dc | lossless ISO fallback 1600 | X of #6 | 2f43ecc |
| 12 | da2a9b5 | recording frame + red timecode switches | F | f4fb084, 4d5fdd1 |
| 13 | 7840438 | auto values white, cap green only if camera added | W, reworks #6 | 15bba86 |
| 14 | 682a186 | ISO Auto everywhere but Clear HDR | X of #6 | b5b787e |
| 15 | 35b31f6 | camera-decided values italic, not green | W, reworks #6 and #13 | e58e7e5 |
| 16 | c716dec | compression greyed while Mode Ladder active | F | 0041ba0, e6ee751 (T34) |
| 17 | 7029db1 | UI timecode vs file timecode, set_timecode_mode target | F | 909aaa5 |
| 18 | c9d841f | stop writing a default hardware file (T38 p4) | F, 578 deletions | 4d80a35, 014fa22 (Core restores the file) |
| 19 | 7c41a27 | HDMI 1080p display fallback (T38 p5) | F | 7af9f13 (same default in Core's template) |
| 20 | 08cefcf | timecode modes called Time of Day and Clip | W | 2c259b9 |
| 21 | ea44bd7 | Controls chip + read-only Controls card | F | f5a61b8, 07afbc6 (controls_errors/warnings) |
| 22 | 841d0ed | drop-frames: buffer bar, safety-stop pill, Frames/RAM, Log, pre-roll | S (7 commits, says so) | d44b177 |
| 23 | 4959513 | pill READY green while buffer empties | X of #22 | fb5801c |
| 24 | 96a7aa4 | record button/pill during safety-stop flush | X of #22 | c5db8b2 |
| 25 | 606f137 | Clip names card (858 lines) | F | 014a2bf |
| 26 | 5697b54 | red outline on audio meter + switch | F | 92d0970 |
| 27 | e061be8 | outline red only while recording | X of #26 | none |
| 28 | 41ff827 | fan mode via Core's set_fan_mode | F (removes UI config.txt writer) | 2955ef8, dda1713, f19b245 (Boot Config engine) |
| 29 | 68e1a41 | dropped-frames chip shows the number | F | 64bbbaa |
| 30 | c234d77 | APERTAR_UI_PREVIEW_RECORDING_FPS caps preview while recording | E, **kept** (1.3) | fb557e9 (Core web twin) |
| 31 | a51c95e | PREVIEW_PEAKING=fast | E, dropped by #38 | none |
| 32 | 322d329 | PREVIEW_DIRECT | E, dropped by #37 | none |
| 33 | 4724007 | PREVIEW_PEAKING=cpu | E, dropped by #36 | none |
| 34 | c13b846 | PREVIEW_PLANE (DRM plane, 805 lines) | E, dropped by #35 | none |
| 35 | 010f8ad | drop PREVIEW_PLANE | R of #34 | none |
| 36 | b333343 | drop PEAKING=cpu | R of #33 | none |
| 37 | 1c7a3ad | drop PREVIEW_DIRECT | R of #32 | none |
| 38 | c153c33 | drop PEAKING=fast | R of #31 | none |
| 39 | 7ea9afc | clip browser/player read split clips | F | d7dd337, ba0658d, 68516f1, 01f170c |

Counts: F 18, S 1, X 6, W 4, R 5 (incl. #10), E 5 (4 dropped, 1 kept) = 39. Back-and-forth that disappears in a clean series: #8/#10, #6/#13/#15 (green, white, italic), #31-#38.

### 1.2 Net effect of the eight preview experiments: nil (confirmed)

- `git diff c234d77 c153c33` is empty. c234d77 is the last commit before a51c95e; c153c33 is the last of the eight. Nothing else lies between them.
- `git diff c234d77 c153c33 -- CMakeLists.txt src/main.cpp` is empty, so the libdrm link and the `DrmPreviewPlane` hook in main.cpp are gone too.
- No leftover names at cinemate-port: grep for `PREVIEW_PLANE`, `PREVIEW_DIRECT`, `PREVIEW_PEAKING`, `uFastPeaking`, `uOverlayOnly`, `DrmPreviewPlane`, `DMA_BUF_IOCTL` in `src/` and `qml/` finds nothing. `#include <libdrm/drm_fourcc.h>` at `src/PreviewWindowRenderer.cpp:24` is also at `origin/main` (line 24), so it is not residue.

Residue, all outside the code:

| Residue | Where |
| ------- | ----- |
| Commit messages of #35, #36, #38 say "park it on preview-plane" / "park it on drop-count". Neither branch exists in `/home/user/Apertar-UI` (`git branch -a`: cinemate-port, clip-split, main, claude/..., work/improve). **unconfirmed** whether they exist on GitHub; `git ls-remote origin` would settle it | git history |
| The eight commits add 1 037 and remove 1 037 lines (1 023 plus 14 modified); reviewers read 8 commits for nothing | history |

### 1.3 The ninth experiment stays: c234d77

`APERTAR_UI_PREVIEW_RECORDING_FPS` (`src/ApertarPreviewSocketClient.cpp:26-33,488`, `.hpp:35,96`) is the same kind of A/B knob as the eight, "desk only", but it was not dropped. Its commit says "A/B knob like Core's APERTAR_WEB_PREVIEW_RECORDING_FPS". It is the only `APERTAR_*` env var the port adds to the UI; the others in the UI (`APERTAR_HARDWARE_CONFIG`, `APERTAR_PREVIEW_FORCE_*`) are original. Decide: drop it with its twins, or keep it and document it with Core's knob (see `sweep-knobs.md`).

### 1.4 UI offers a cap that Core removed (bug, confirmed)

- `qml/CameraPage.qml:820-822@cinemate-port`: `imx585Max = root.clearHdrActive && root.rawBitDepthValue === "16-bit" ? 25.0 : 30.0`, comment "as in Core's tableMaximumFpsForResolution()".
- Core 31d5418 (11-03) "Clear HDR 16-bit on the IMX585 runs to the driver's maximum fps (no 25 cap)": 4K is 30, crops 31.9-42.4. The UI commit d1efb67 (10-27) was never revisited.
- Consequence: touch UI stops at 25 where Core and the WebUI allow 30. A clean series folds d1efb67 into nothing (drop it) and the picker follows Core's `fps_max` from state (Core 97adea0/bcedbe5 added `fps_max`).
- Also, `src/ApertarCoreApp.cpp:1386@cinemate-port` has the same stale comment text (copy of the QML comment). Check in the Core file review.

### 1.5 Other notes on UI commits

| Note | Evidence |
| ---- | -------- |
| T-numbers in subjects (T33, T38 p4, T38 p5) and in bodies (T31, T45) mean nothing to Apertar-Studio | #9, #18, #19, #5, #21 |
| Subjects "drop-frames:" are a branch name, not a feature | #22-#26 |
| #22 body says "Tested: not compiled or run here"; #3, #4 "not built here"; #18, #19 "UI build on the Pi not yet run" | commit bodies |
| Every commit carries `Co-Authored-By: Claude Opus 5.5` or `Sonnet 5.5`; #1-#15 also a `Claude-Session:` line | commit bodies |
| #28 removes 103 lines of UI config.txt writing (`sudo -n install`); it is the UI half of the Core Boot Config work, so it cannot merge before Core 2955ef8 + dda1713 | `git show 41ff827` |
| #18 deletes the two `ensureDefaultHardwareConfigFile` templates (578 lines); needs Core 4d80a35/014fa22 or a missing hardware file is never created | `git show c9d841f` |
| #39 adds `src/ClipFrameFiles.hpp`; works only with Core's split clips (d7dd337); a flat clip still reads as before | commit body |
| UI total vs main: 30 files, +2414/-824; biggest: ClipNameCard.qml 601, ApertarControlBridge.cpp 388, SettingsPage.qml 377 | `git diff --stat` |

### 1.6 Proposed clean UI series (39 -> 15)

Each line is one commit; Core partner must be merged first or in the same release.

| # | Clean commit | Folds | Needs Core |
| - | ------------ | ----- | ---------- |
| 1 | Show media state from Core (MEDIA REMOVED / ERROR) | #1 | media_state, media_alive in get_state |
| 2 | Automounter: release a card pulled while mounted | #2 | none |
| 3 | 16-bit in the frame-size estimate | #3 | none |
| 4 | FPS picker in a speed-ramp take sends set_fps only | #5 | fps_speed_ramp |
| 5 | Value lists: pickers follow Core's lists and ISO ceiling, lock, resolution line with bit depth | #6, #7, #9, #11, #14 (final text 16-bit, final style italic; no green/white step) | iso_max, iso_actual, value lists |
| 6 | Recording frame and red timecode switches | #12 | recording_frame, red timecode keys |
| 7 | Compression greyed while the Mode Ladder is active | #16 | Mode Ladder |
| 8 | Separate UI timecode and file timecode (Time of Day, Clip) | #17, #20 | set_timecode_mode target |
| 9 | Do not write a default hardware file; 1080p HDMI fallback | #18, #19 | hardware file store, restore |
| 10 | Controls chip and read-only Controls card | #21 | get_state controls_errors |
| 11 | Write buffer, Log, pre-roll, buffer bar, safety-stop pill, flush behaviour | #22, #23, #24 | drop-frames Core commits |
| 12 | Clip names card | #25 | clip name presets |
| 13 | Audio outline switch; dropped-frame count | #26, #27, #29 | audio outline, recording_dropped_frames |
| 14 | Fan mode through Core's set_fan_mode | #28 | Boot Config engine + helper |
| 15 | Clip browser and player read split clips | #39 | frames_per_folder, merge worker |

Left out: #4 (wrong, 1.4), #30 to #38 (experiments; #30 only if the knob is kept, as its own commit 16). Within a clean commit the subject loses T-numbers and the "drop-frames:" prefix.

## 2. imx585 driver: `origin/apertar..cinemate-port` (55 commits)

Structure (confirmed from `git log --format=%p`):

| Part | Commits | Author |
| ---- | ------- | ------ |
| Will Whang base (hardening, HMAX table, RAW10 4K, CCMP gate) | 3680bf4, c0f5404, 11178c8, 70bdb26 (4) | Will Whang |
| Cinemate 7-mode work, README | b6a6f5b..bd57617 (6) | Patrik |
| Crop mode family, experimental | e711fc9..7061c74, 27c7cb4 (22) | Patrik |
| WP-585-n series | 5c7fb79..18c1eb2 (14, incl. merge PR #2 90eef64) | Patrik |
| On the Apertar line | 24172e6 (parent e5b74d3 = origin/apertar) | Patrik |
| Merge of cinemate-modes | 6f25d7f | Claude |
| Port fixes and docs | c18f162, 97649ba, 56de0cc, cd548ef | Claude |

Diff vs `origin/apertar`: 9 files, +3637/-689; `imx585.c` +3477 lines.

### 2.1 Pure back-and-forth

| Commits | What happens |
| ------- | ------------ |
| 475c3ea "Restore experimental small centered crop modes" after 234cccb "remove sub-960 crop modes" | removed, then restored |
| 8f508fb (WP-585-6) "drop ad-hoc small crops" | drops what 475c3ea restored |
| b050b7c "add cropped 16-bit ClearHDR modes" -> fdd767a (WP-585-8) "withdraw the binned 16-bit ClearHDR crops" | added, withdrawn 2 days later |
| 663449a, b46cc47, 9a44a4d, d3253b5, a09ac49, 4949b06 | six "experimental:" fixes of b050b7c's table ordering and window height |
| 7061c74 "Fix mode enum and array ordering" then 27c7cb4 "Restore 12-bit mode table ordering" | fix then restore |
| b703f46 + 85555d0 (fix) -> 74ed4c6 -> 951aeee (WP-585-1) -> 24172e6 -> 97649ba | crop metadata reported five times (V4L2 controls, native coords, sensor coords, window rectangle, read-only flag) |
| b6a6f5b "12-bit CCMP default on" over 70bdb26 "gate behind a dtoverlay param" | policy flip, both stay |
| e9d5759, 0af0293, bd57617 | three README commits on one paragraph (blend default) |
| 74b9b73 -> aa6c723 "stop mutating shared mode tables from probe() (rework)" | fix of the audit commit |

### 2.2 Unclear subjects and internal numbers

- `WP-585-1` to `WP-585-10` in 13 subjects (5c7fb79, 951aeee, 047c8a9, fff39ae, ceb7367, 74b9b73, aa6c723, d47cbd8, 8f508fb, fdd767a, 00059f6, 0a99f14, 18c1eb2). WP-585-7 appears twice; WP-585-9 gets its own PR #2 and the `tools/clearhdr-gate` kit.
- `experimental:` in 11 subjects (b050b7c..4949b06) with no sentence on what stage that means.
- Vague: "Fix C control metadata initialization" (85555d0), "Complete centred RAW10 crop family", "Fix IMX585 mode enum and array ordering".
- Merge subject 6f25d7f names two branches (`cinemate-modes`, `cinemate-port`), neither known to Apertar.

### 2.3 What a maintainer would need

Recommended: keep Will Whang's 4 commits as they are (authorship), then ONE squashed commit "imx585: Cinemate mode set" (tables, crop family, geometry controls, probe audit; about +3400 lines of `imx585.c`), ONE commit for `tools/` (`check_window_alignment.py`, `replay_mode_table_audit.py`, `clearhdr-gate/`), ONE docs commit (`README.md`, `APERTAR.md`). Reason: no commit between 3680bf4 and 24172e6 leaves a table that is right alone (mode order and crop windows change in ten steps), so bisecting history finds nothing. If history must stay: keep the WP-585-n commits, drop the 22 "experimental:" commits into the squash, and rewrite the subjects without WP numbers.

## 3. imx283 driver: `origin/master..cinemate-port` (93 commits)

Structure: `origin/cinemate-modes` is an ancestor of `cinemate-port` and holds 84 of the 93 commits (`git rev-list --count origin/master..origin/cinemate-modes` = 84); the 9 above it are Claude's port fixes and docs (d810aa7..68b7dc9). The first 8 commits (050e2e3 2024-03 ... fea3d35 2025-10) are old Will Whang/"Your Name" history that `origin/master` lacks, so `origin/master` is not Will's current master (**probable**; `git merge-base origin/master origin/cinemate-modes` and `git log --oneline origin/master -3` would settle it). Diff vs master: 8 files, +1993/-110; `imx283.c` +1723.

### 3.1 Pure back-and-forth

| Commits | What happens |
| ------- | ------------ |
| 24f7bf0 "Fix Linux 6.12 external module build" -> 146d24f "Revert" -> 16de05f, 6f6410d, 5d1c193 | same fix done, reverted, redone in three steps |
| 0700acd, 4eb1bea, 8648db4 (18 fixed Mode-0 crops) -> 773c5bb "replace ad-hoc Mode-0 crops with the aspect-ratio family" | first design discarded |
| 8f2b230 "gate unvalidated modes behind experimental_modes" -> 2070416 "expose aspect-ratio modes without experimental flag" | gate then open |
| 134455d "gate per-crop VMAX behind crop_vmax" -> 94eb7e2 "enable by default" -> 8315435 "keep Mode-0 crop timing at full-frame VMAX" -> 2d4f0f0 | default flipped, then partly undone |
| 07b1aab "add cropped-in 2K 1920 and 720p" -> 3f9891b -> 06890e5 "remove cropped-in 1280 modes" | added, partly removed |
| 4350e3e and 4612d68 (identical subject "experimental: emit active-only frames") then 4123dd2, efe2463, 0f42ebe, a01a6e6, 3890ce6, c590017, 58fdcaf, bbbd49b, **a852cfe "revert: restore IMX283 sensor crop window"** | 11 commits of one experiment, ended by a revert |
| MODE_1C window: c20c603, 5828d5b, 3c2310e (back to 236), 812c058 (924, untested), de6693c (back to 236), cb925e5 (924 again) | value flips 236/924/236/924 |
| 7e98970/b67ea62 (WP-283-3), e8c7093, d9915be, 4948e70, 05d1493, 4761af3 "remove the 2704 correction", d1763e0, ad7082b, 2947d23 | table rebuilt four times in 6 days |
| c3fae40 "restore the 10-bit UHD mode, and retire its crop family" | restore after earlier removal |

### 3.2 Unclear subjects and internal numbers

- `WP-283-1` to `WP-283-6` (1177922, 7e98970, 835cf14, 8f2b230, 4ef5277, 773c5bb).
- Subjects with only "fix:" or "experimental:" (efe2463 "repair active-crop helper syntax", a01a6e6 "restore cropped mode macro continuation", 1d28494, 211e0e9, 3f9891b "fix crop macro definition order"): they repair a prior commit's compile or macro error.
- 050e2e3 author "Your Name", 289131a author "Your Name".
- 4a1662e "stop oopsing the kernel on an ACTIVE S_FMT" is a real fix and should keep its own commit, with the wording "oopsing" changed.
- 235a58c and 805a773 carry the Apertar docs; 68b7dc9 corrects 805a773 (squash).

### 3.3 What a maintainer would need

One squashed "imx283: Cinemate mode set (aspect-ratio crops, MODE_1C, geometry controls)" on top of the 8 old base commits, kept as they are. Separate small commits worth keeping: 4a1662e (kernel oops fix), d810aa7 (CROP_DEFAULT is the active area), d6ec1c7 (bounds check), 4064e88 (debug level), 257c9cf (overlay link-frequency parameter), and one docs commit (`README.md`, `APERTAR.md`, `EXPERIMENTAL_CROPS.md` marked stale). Everything between 95183c8 and cb925e5 (about 70 commits) collapses into the squash. Reason: the final tables are the product; a reader cannot tell from the steps which of 924/236 is current.

## 4. Which driver branch to install, and do the READMEs agree

| Item | imx585 | imx283 |
| ---- | ------ | ------ |
| Branch to install after the merge | `cinemate-port` (`APERTAR.md` "Which branch"; `README.md` clone `-b cinemate-port`; Core `CameraController.cpp:441-442` and `Imx283Modes.hpp:1-2` name `cinemate-port`) | `cinemate-port` (same three places) |
| Branch NOT to install | `apertar` (shipped on Apertar-Beta 1.6.0; its 1.85:1 crops are 3840x2076/1920x1038, Core now expects 3840x2072/1920x1036 per `CameraController.cpp:441-442`) | `master` |
| `README.md` mentions `APERTAR.md` | no | no |
| README clone URL and branch | agrees with APERTAR.md | agrees with APERTAR.md (235a58c) |
| README mode statement | **disagrees**: section "CineMate branch (`cinemate-7modes`)" at `README.md:148` says seven modes (lines 155, 160, 208, 251); `APERTAR.md` says 187 modes in four families and `cinemate-port` holds them | `EXPERIMENTAL_CROPS.md` marked STALE; `APERTAR.md` says tables in `imx283.c` rule; README agrees |
| Branch name in README | `cinemate-7modes` is a third branch name next to `cinemate-modes` and `cinemate-port`; it is not in `git branch -a` here | none |

Result: for imx585 the README has a stale 7-mode matrix under a branch name that is gone; a user who reads only `README.md` is told 7 modes while the driver offers 187. Fix: rewrite or delete the `cinemate-7modes` section, add one line "Apertar users: see APERTAR.md" in both READMEs. Also the three-branch history (apertar, cinemate-modes, cinemate-port) should end in one named branch; Apertar's image must be rebuilt to pull `cinemate-port`, since Beta 1.6.0 ships `apertar`.

## 5. Findings

See structured result: X-commits-ui-drivers-1 to -9.
