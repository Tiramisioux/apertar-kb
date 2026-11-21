# Sweep X7b: commit series, Core, second half (commits 96 to 187)

Read-only plan. Written 2026-11-17. Ref: Core `cinemate-port` `01f170c`, `origin/main` `f60e301`.
Command: `git log --reverse --format=... origin/main..cinemate-port`, rows 96 to 187 (92 commits). Messages read with
`git show -s`, diffs with `--stat` and hunk headers. Labels: **confirmed** = read in git output, **probable** = inferred.

## 1. Result in short

| Fact | Value |
| --- | --- |
| Commits in this half | 92 (81 by Patrik Eriksson, 11 by "Claude") |
| Merges | 10 (146, 152, 153, 154, 155, 156, 162, 163, 164, 167); 3 carry only a PR title |
| Tutorial or work-package numbers in a subject | 12 (T36, T37 x4, T38 x3, T50 x2, T51); all in rows 96 to 108 |
| Same numbers (T, Q, R, "design §") in a body | 21 commits |
| Mixed-purpose commits | d44b177 (12 features), 114, 121, 122, 117, 170 partly |
| Message disagrees with diff | 137 and 138 (hunks swapped, confirmed), 124 (subject names 7 of 12 features), 179 (cites a commit not in the repo) |
| Prefix is a branch name, not a component | rows 124 to 128 (`drop-frames:`) |
| Trailers | 89 `Co-Authored-By` lines naming three model names (Opus 5.5 x54, Sonnet 5.5 x26, Fable 5.1 x9); 20 `Claude-Session` URLs; 3 `(cherry picked from ...)` lines to commits not in the repo |
| Env-knob commits later made moot | 132, 134, 139, 140, 141, 144 by 168, 170, 175 (section 4.5) |
| Clean series proposed | 52 commits for 92 (section 6) |

Upstream style reference: `upstream-1.6.0` is one commit ("1.6.0 Release"). The prefix style comes from fork `origin/main`:
`camera: ...`, `web: ...`, `core: ...`, `scripts: ...`, `build: ...`, lower case, imperative, no numbers, no branch names.

## 2. Merge graph (the series is not linear)

The log shows 92 rows in date order, but parents form side branches. A clean series is one line, so merges go away.
Merge conflict resolutions (163, 164) are hidden inside merge commits: not reviewable as they are.

| # | Merge | Parents | What it brought | Verdict |
| --- | --- | --- | --- | --- |
| 146 | 4581a69 Merge claude/cool-volta-y7fiw7: Boot Config | 900d282, 496817f | 129, 130, 131, 133, 135, 136 (2790 lines) | linearise |
| 152 | 4b2eeac Merge claude/keen-bardeen-qbe3wg | 2a4266e, 618b2f1 | 147 MLV black level, 148 playback size | linearise |
| 153 | 389f8a7 Merge drop-frames into keen-bardeen (author Claude) | 618b2f1, 2a4266e | the same, other direction (3187 lines): made only to shrink a PR | drop |
| 154 | 57519a2 Merge pull request #3 | 4b2eeac, 6ef0ddc | DNG write chain: 132, 134, 137, 138, 139, 140, 141, 143, 144 | linearise |
| 155 | 0f4d06d Merge pull request #4 | 57519a2, 5f5cea2 | 145 build without libcamera | linearise, move first |
| 156 | 5e25f69 Merge pull request #5 | 0f4d06d, 389f8a7 | 147, 148 again, via 153 | drop |
| 162 | 1944995 Merge imx585-modes | 4b2eeac, 66b324d | 157, 158 | linearise |
| 163 | a47dc28 Merge imx283-support | 1944995, f95567d | 159, 160, 161; conflicts in CameraController.cpp and WebControlPage.cpp | linearise, redo conflicts by hand |
| 164 | dd00206 Merge origin/drop-frames (PRs #3-#5 ...) | a47dc28, 5e25f69 | PR #3 to #5 on the sensor branches; conflict in CameraController.cpp | linearise, redo conflict by hand |
| 167 | d08b88f Merge the Pi's drop-frames | 6707b08, 64bbbaa | 165 (made on the Pi) | linearise |

## 3. Per-commit table

Class: F feature, X fix of an earlier commit, R revert/undo, W wording/layout churn, M merge, B build fix, D docs.
"New" = target commit in section 6. Size = files, +/- lines. Rows 142 and 145 sit before their merges because the log is by date.

| # | sha | Author | Subject (short) | Class | Size | Flags | New |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 96 | 4629de2 | Patrik | web: the Clip Viewer, frame-number clock (T50, page part) | F | 1, +1313 -18 | number; "page part" half | N2 |
| 97 | a37a902 | Patrik | core: downloads and deletes yield to a take (T50, Core part) | F | 2, +71 -6 | number; body "design §2.7, Q21, Q23"; "Pi build pending" | N1 |
| 98 | fa19856 | Patrik | core, web: sound in the Clip Viewer, /api/media/file with Range (T51) | F | 2, +252 -9 | number; "Pi build pending" | N3 |
| 99 | 4fa0432 | Patrik | web: viewer asks for the frame that will be due | X of 96/98 | 1, +5 -4 | | N2 |
| 100 | 916c1dd | Patrik | core: one action vocabulary in ActionCatalog.hpp, list_actions (T36) | F | 8, +410 -380 | number; touches 3 input drivers, Grove, trigger, tally; "isoinf and isonan are refused now" is a behaviour change inside a refactor | N4 |
| 101 | 3526e4b | Patrik | core: HardwareConfigText and HardwareConfigStore (T37, part 1) | F | 4, +1617 | number; body: "Nothing in Core calls the new code yet" | N5 |
| 102 | c509e9f | Patrik | core: IMU config writes go through the store (T37, part 2) | F | 1, +46 -257 | number | N5 |
| 103 | f5a61b8 | Patrik | core: get_controls and set_controls, read-only commands before the lock (T37, part 3) | F | 4, +155 -21 | number; two changes | N6 |
| 104 | 4d80a35 | Patrik | core: validate at start, pin adopted version, fix template (T37, part 4) | F+X | 2, +47 -7 | number; template fix mixed in | N6 |
| 105 | 5395fa4 | Patrik | core: Config page file through the store, 409, socket 1 MiB (T38, part 1) | F | 2, +74 -58 | number; socket limit unrelated | N7 |
| 106 | effb804 | Patrik | web: Config page names the revision it loaded (T38, part 2) | F | 1, +70 -3 | number; page half of 105 | N7 |
| 107 | 014fa22 | Patrik | core: spot a hardware file replaced by a default, restore it (T38, part 3) | F | 3, +93 -3 | number; "part 4" missing | N8 |
| 108 | 7af9f13 | Patrik | core: default template shows HDMI 1080p (T38, part 5) | X of 104 | 1, +5 -5 | number; template fixed twice (104, 108) | N6 |
| 109 | 07afbc6 | Patrik | core: set_controls single-key edits, get_controls rows (Controls page, part 1) | F | 2, +215 -5 | "part 1" | N9 |
| 110 | d282de9 | Patrik | web: the Controls card at the top of Config (Controls page, part 2) | F | 1, +472 -1 | "part 2"; rewritten by 115, 118, 120 | N9 |
| 111 | 243fe2c | Patrik | core: a Clear HDR on / off action, an honest label for resolution | F+W | 2, +19 -2 | two changes; "temp branch" in body | N4b |
| 112 | 166cc4d | Patrik | core, web: Pi GPIO buttons as a peripheral (Controls page, part 3) | F | 8, +386 -30 | moves chip scoring out of GpioInput | N9 |
| 113 | 2c259b9 | Patrik | web: timecode modes are called Time of Day and Clip | W | 1, +15 -5 | unrelated to its neighbours | N10 |
| 114 | 0a98868 | Patrik | core: clicks and hold on GPIO buttons like Cinemate, 1-0-1, I2C devices | F | 10, +341 -30 | three features | N11, N12 |
| 115 | f5fe41b | Patrik | web: Controls for the hardware that is there, + for clicks, Hardware card | F+X | 1, +348 -89 | rewrites 110; two cards | N9, N12 |
| 116 | 0c49601 | Patrik | hw: GPIO buttons and encoders wait for edge events | F (rewrite of 114) | 4, +160 -74 | prefix `hw:` not used elsewhere | N11 |
| 117 | c34f844 | Patrik | hw: two- and three-way GPIO switches, CFexpress hat in get_controls | F | 5, +261 -15 | two features | N13, N12 |
| 118 | fa3a798 | Patrik | web: one card per device, gesture dropdowns, add buttons and switches | X of 110/115 | 1, +367 -267 | third rewrite of the page | N9 |
| 119 | c140c4f | Patrik | hw: clicks and hold on NeoRotary pushes, PCF pins, encoder pushes | F | 9, +180 -64 | extends 114 | N11 |
| 120 | b74b4aa | Patrik | web: push actions on knobs and PCF pins, + Add GPIO rotary encoder | F+W | 1, +158 -89 | fourth rewrite | N9 |
| 121 | dcf09ee | Patrik | core: saves apply without a restart, Listen, history, I2C scan, output tests | F | 13, +528 -16 | five features; T39, T40, T42 in body | N14 |
| 122 | 8be1ab5 | Patrik | web: Listen, review, undo, chips, Turn adjusts, Scan, Test, text editor with diff | F | 1, +755 -25 | eight features; "the rest of T40-T43" | N14 |
| 123 | a40112a | Patrik | web: clip browser says Loading | F | 1, +15 -2 | unrelated | N2 |
| 124 | d44b177 | Patrik | drop-frames: trim, Log, RAM write buffer with safety stop, buffer bar, fps max, storage pre-roll | F x12 | 25, +5170 -100 | section 5 | D1 to D11 |
| 125 | fb5801c | Patrik | drop-frames: the pill is READY green while the buffer empties | X of 124 | 1, +3 -2 | | D3 |
| 126 | c5db8b2 | Patrik | drop-frames: record during a safety-stop flush discards queued frames | F on 124 | 4, +142 -23 | new behaviour | D3 |
| 127 | 014a2bf | Patrik | drop-frames: clip names you can compose | F | 8, +1421 -50 | prefix wrong, unrelated to drops | N15 |
| 128 | 92d0970 | Patrik | drop-frames: Audio recording outline switch | F | 2, +25 -2 | prefix wrong, unrelated | N16 |
| 129 | f19b245 | Claude | config.txt engine: read and edit the boot config in place | F | 2, +1596 | author Claude; no prefix; no caller yet | E1 |
| 130 | dda1713 | Claude | apertar-boot-config: root helper | F | 3, +108 | author Claude; no prefix | E1 |
| 131 | 2955ef8 | Claude | Core: get/set_boot_config and /api/boot-config | F | 1, +356 -28 | author Claude; also rewrites the fan write path | E2 |
| 132 | e55557d | Patrik | cdng: write unpacked payloads straight from the frame | F | 3, +246 -2 | adds 2 env knobs | W1 |
| 133 | 8a56545 | Claude | WebUI: Boot Config card in the System pane | F | 1, +691 -1 | author Claude; prefix `WebUI:` | E3 |
| 134 | 4abbef0 | Patrik | rec: allocate raw copies outside the queue mutex, warm the pool | F | 1, +90 -20 | adds 1 env knob | W2 |
| 135 | afa00e8 | Claude | WebUI: wrap the DRM note in the Boot Config review | X of 133 | 1, +8 -1 | no body | E3 |
| 136 | 496817f | Claude | README: Boot Config card, its lines, the root helper | D | 1, +32 | author Claude | E3 |
| 137 | 04bac89 | Patrik | media: trim after a delete made outside Core, after every pre-roll clip delete | F | 1, +10 -3 | message disagrees with diff (4.2) | D1 |
| 138 | e0fa852 | Patrik | media: noatime and umask on the re-insert mount | F | 1, +3 -2 | message disagrees with diff (4.2) | D1, W3 |
| 139 | c57c284 | Patrik | scripts: APERTAR_RT=1 runs Core under SCHED_FIFO | F (knob) | 3, +42 -2 | knob; replaced by 144 | drop |
| 140 | 0ed07ea | Patrik | cdng, rec: APERTAR_DNG_DONTNEED; dropped_copy_slot in the stats line | F (knob) | 4, +43 -1 | two things; default flipped by 168 | W4 |
| 141 | fb557e9 | Patrik | web: APERTAR_WEB_PREVIEW_RECORDING_FPS | F (knob) | 4, +32 -2 | prefix `web:` but touches CC, App | W5 |
| 142 | 900d282 | Claude | camera, web: imx585 1.85:1 crops are 3840x2072 and 1920x1036 | F | 2, +53 -19 | author Claude; whitelists replaced by tables in 157 | S1 |
| 143 | 766aba8 | Patrik | rec, web, cdng: fixes from the review of the seven commits above | X of 132, 134, 137-141 | 4, +19 -16 | no change named in subject; body admits 137/138 swap | folded |
| 144 | 6ef0ddc | Patrik | rec: APERTAR_RT_CAPTURE_PRIORITY=N | F (knob) | 3, +30 -8 | replaces 139, leaves 139 behind | drop |
| 145 | 5f5cea2 | Claude | camera: build without libcamera again (--simulate) | B | 1, +32 | author Claude | B1 |
| 146 | 4581a69 | Patrik | Merge claude/cool-volta-y7fiw7 | M | | section 2 | |
| 147 | 5e9dd1a | Claude | mlv: black and white level as the cDNG | F/X | 4, +88 -39 | author Claude | S2 |
| 148 | 618b2f1 | Claude | playback: open every DNG size Core writes | F | 3, +128 -10 | author Claude | S3 |
| 149 | 3b87d99 | Patrik | web: Boot Config card edits config.txt as text too | F | 5, +257 -9 | touches 5 files, not only the page | E3 |
| 150 | b3e7f52 | Patrik | web: Boot Config keeps the link rate for the twin sensor | X of 133 | 1, +7 -2 | | E3 |
| 151 | 2a4266e | Patrik | web: Boot Config marks the lines the card sets | F | 3, +150 -11 | | E3 |
| 152 | 4b2eeac | Patrik | Merge claude/keen-bardeen-qbe3wg | M | | | |
| 153 | 389f8a7 | Claude | Merge drop-frames into keen-bardeen | M | | author Claude | drop |
| 154 | 57519a2 | Patrik | Merge pull request #3 | M | | title only | |
| 155 | 0f4d06d | Patrik | Merge pull request #4 | M | | | |
| 156 | 5e25f69 | Patrik | Merge pull request #5 | M | | | |
| 157 | caa0153 | Patrik | camera: imx585 modes from tables, not whitelists | F | 6, +587 -109 | replaces 142; flat 25 fps for 16-bit Clear HDR, removed by 175 | S1 |
| 158 | 66b324d | Patrik | web: imx585 resolution families, ratio row, ladder groups | F | 1, +235 -154 | | S1 |
| 159 | c48e693 | Patrik | camera: add the IMX283 sensor family (57 driver modes) | F | 5, +595 -18 | also changes Clear HDR start order (unrelated) | S4 |
| 160 | 9a081dd | Patrik | web: IMX283 resolution pills, ratio rows and fps floors | F | 1, +137 -1 | | S4 |
| 161 | f95567d | Patrik | core: PCF resolution step cycles the IMX283 modes | F | 1, +28 -4 | | S4 |
| 162 | 1944995 | Patrik | Merge imx585-modes | M | | | |
| 163 | a47dc28 | Patrik | Merge imx283-support | M | | conflicts CC, WCP | |
| 164 | dd00206 | Patrik | Merge origin/drop-frames | M | | conflict CC | |
| 165 | 64bbbaa | Patrik | rec: count the take's dropped frames | F | 4, +32 -12 | made on the Pi | D11 |
| 166 | 6707b08 | Patrik | web: crop thumbnails are 16:9 | X of first-half Mode Ladder page | 1, +4 -4 | | S5 |
| 167 | d08b88f | Patrik | Merge the Pi's drop-frames | M | | | |
| 168 | adac040 | Patrik | cdng: drop a DNG's pages after the fsync by default | R of 140's default | 3, +10 -10 | flips a default set 28 rows earlier | W4 |
| 169 | 48f8b8c | Patrik | cdng: the clip line names the dontneed mode, writeback, sync_ms | F | 1, +8 -2 | | W4 |
| 170 | 2edc6d0 | Patrik | config: a media tuning file with a test-night override | F | 7, +455 -20 | new config file; env still wins | W6 |
| 171 | 46d0e8c | Patrik | scripts: apertar-tune | F | 1, +487 | CLI for 170 | W6 |
| 172 | 6777ebe | Patrik | web: Value Lists card moves from Record to Controls | W | 1, +9 -9 | | N17 |
| 173 | 854fe43 | Patrik | web: a Modes pane holds the sensor modes and the Ladder | W | 1, +61 -51 | | N17 |
| 174 | 4b14a79 | Patrik | web: Activated sensor modes filters on several ratios | F | 1, +16 -8 | | N17 |
| 175 | 31d5418 | Patrik | camera: Clear HDR 16-bit on the IMX585 runs to the driver's maximum fps | R of 124 and 157 | 1, +5 -5 | leaves `(void)settings; (void)sensorFamily;`; comment names "User" | D8 |
| 176 | 1319967 | Patrik | web: Remote controls card and Try buttons | F | 3, +275 -11 | prefix `web:`, adds Core `test_input` | N18 |
| 177 | b64e6f6 | Patrik | web: GPIO out row gets a Remove | X/F | 1, +18 -1 | | N9 |
| 178 | 9b5ea14 | Patrik | web: a GPIO button can be remote only; DPI pins greyed | F | 1, +18 -1 | adds key `remoteN` | N18 |
| 179 | ce0bd90 | Patrik | media: a switch for the drive trim and a Performance card | F | 6, +66 -6 | cites `00f2327`, not in repo | D1 |
| 180 | e625c68 | Patrik | camera: a Preview temporal denoise switch, off by default | F | 8, +694 -5 | cherry-pick trailer to absent commit; +451-line header | S6 |
| 181 | c810f85 | Patrik | web: frame-rate phase lock on the Performance card | F | 1, +14 | cherry-pick trailer | S7 |
| 182 | f4a1393 | Patrik | camera: phase lock pins {d, d+1} | X of first-half 80ddac1 | 2, +16 -7 | cherry-pick trailer | S7 |
| 183 | d7dd337 | Patrik | cdng: split a take into part folders with frames_per_folder | F | 11, +445 -15 | | P1 |
| 184 | 9ec37b5 | Patrik | tools: flatten_clip.py | F | 2, +285 -1 | | P1 |
| 185 | ba0658d | Patrik | media: a merge worker flattens split clips | F | 9, +796 -16 | | P2 |
| 186 | 68516f1 | Patrik | media: rescan for split clips after a merge pauses | X of 185 | 1, +4 | | P2 |
| 187 | 01f170c | Patrik | media: read the clip merge switch before the first scan | X of 185 | 1, +3 | | P2 |

## 4. Flags

### 4.1 Subjects that do not say what changed, or carry numbers

| Commit | Problem |
| --- | --- |
| 124 d44b177 | Subject names 7 of 12 features; the body adds a "Squashed from 19 commits" line |
| 143 766aba8 | "fixes from the review of the seven commits above": no change named; "above" is a position |
| 135 afa00e8 | "wrap the DRM note": no body, a layout fix of 133 |
| 129 f19b245 | "config.txt engine": no prefix, jargon |
| 154 to 156 | "Merge pull request #N": body is a PR title |
| 164, 167 | merge subjects name PRs, not what the conflict resolution decided |
| 96 to 108 | tutorial numbers in subjects (T36, T37, T38, T50, T51) and "part N"; T38 has parts 1, 2, 3, 5 (no 4) |
| 109, 110, 112 | "Controls page, part 1/2/3" |
| 124 to 128 | prefix `drop-frames:` is a branch name; 127 and 128 have nothing to do with dropped frames |

### 4.2 Message disagrees with the diff (confirmed)

| Commit | Message says | Diff holds |
| --- | --- | --- |
| 137 04bac89 | trim after outside delete and after every pre-roll clip delete | only the media-watcher `trimMedia("free-space")` hunk (App +10 -3) |
| 138 e0fa852 | noatime and umask on the re-insert mount | the mount strings and the pre-roll change `if (result.bytes >= (1ULL << 30)) trimMedia("delete")` to `trimMedia("delete")` |
| 143 766aba8 | body: "the messages are right, the split is not. The branch is not rewritten here" | admits the swap |
| 124 d44b177 | 7 features | 12 (section 5) |
| 179 ce0bd90 | "the clean cut (00f2327) ... ported by hand" | `git cat-file -t 00f2327` fails here |
| 180 e625c68 | `(cherry picked from commit 6bd002b...)` | object absent here (181 and 182 carry the same kind of line: a344376, 69a700e) |
| 175 31d5418 | "no 25 cap" | removes the cap and leaves `(void)settings; (void)sensorFamily;`; comment says "Removed (User, 2026-11-03)" |
| 141 fb557e9 | prefix `web:` | also CameraController.cpp/.hpp (`rawTakeActive()`) and README |
| 176, 178 | prefix `web:` | add Core command `test_input` and key `remoteN` |

### 4.3 Patterns inside this half

| Pattern | Commits |
| --- | --- |
| Page and Core halves of one feature | 96+97, 105+106, 109+110 |
| Controls page rewritten four times | 110, 115, 118, 120 (about +1345 -446 lines in `WebControlPage.cpp`) |
| Gestures written twice | 114 polls, 116 replaces polling in the same files |
| Template fixed twice | 104, 108 |
| Behaviour added then flipped | 140 default `writer`, 168 default `sync`; 124 and 157 cap 16-bit Clear HDR at 25 fps, 175 removes it; 142 whitelists replaced by 157 tables |
| Knob added then superseded | 139 by 144; env knobs 132/134/140 by file 170 ("the environment variables still win") |

### 4.4 Authors and trailers

| Fact | Evidence |
| --- | --- |
| Authored "Claude" (11) | f19b245, dda1713, 2955ef8, 8a56545, afa00e8, 496817f, 900d282, 5f5cea2, 5e9dd1a, 618b2f1, 389f8a7 |
| Trailers | `Co-Authored-By: Claude Opus 5.5` x54, `Claude Sonnet 5.5` x26, `Claude Fable 5.1` x9; `Claude-Session: https://claude.ai/code/session_...` x20 |
| Test claims | "Pi build pending" (97, 98); d44b177 body: "Not compiled or run yet: the pre-roll and the Clear HDR override" |
| Words the original developer will not know | KB paths (`working/dng-chain`, `working/drop-frames`), "the campaign branch", "the temp branch", "the Pi's drop-frames", "findings 2026-11-03", "User" |

Policy for the owner: one trailer form (or none), no model-name variants, no session URLs. Decide together with the first-half sweep.

### 4.5 Env-knob commits later made moot (confirmed with `git grep` at cinemate-port)

| Knob | Added | Fate |
| --- | --- | --- |
| APERTAR_RT | 139 | superseded by 144; remove |
| APERTAR_RT_CAPTURE_PRIORITY | 144 | A/B lever; remove or make one fixed capture-thread priority |
| APERTAR_DNG_PAYLOAD_COPY, APERTAR_DNG_WRITE_ROWS | 132 | A/B levers for a fixed behaviour; remove |
| APERTAR_RAW_POOL_WARM | 134 | A/B lever; remove |
| APERTAR_DNG_DONTNEED | 140, default flipped by 168 | keep only "sync" behaviour; remove the knob |
| APERTAR_WEB_PREVIEW_RECORDING_FPS | 141 | body says the test decides if it is needed; decide, then remove |
| APERTAR_MEDIA_TRIM | 124 | moot by `set_media_trim` (179): two ways to set one thing |
| APERTAR_FPS_LIMIT, APERTAR_LOSSLESS_FPS_LIMIT | 124 | A/B levers; remove |
| APERTAR_IMX283_PROBE_FPS | 159 | A/B lever; remove |
| APERTAR_CDNG_FRAMES_PER_FOLDER | 183 | duplicates the `[storage]` key; remove |
| APERTAR_STORAGE_PREROLL | 124 | duplicates `[media] preroll`; remove |
| `~/apertar-media-tune.conf`, `apertar-tune` | 170, 171 | new config surface; owner decision (see sweep-knobs.md) |

Removing these makes 139, 141, 144 empty and shrinks 132, 134, 140, 168, 169, 183. This sweep maps commits only; verdicts are in sweep-knobs.md.

## 5. d44b177 split plan

One commit, 25 files, +5170 -100, "Squashed from 19 commits". Read with `git show d44b177 --stat`, `-U0` hunk headers and added-line counts.

### 5.1 Separable pieces

| # | Piece | Own files (split by path) | Shared files (hunks) | Functions |
| --- | --- | --- | --- | --- |
| D1 | Trim the recording drive | `scripts/apertar-media-trim` (90), `config/apertar-media-trim.sudoers` (4), `tools/media_trim_test.sh` (41) | App.cpp (about 140 lines), README (12) | `trimMedia`, `trimMediaAfterDelete`, `mediaTrimMayRun`, `runMediaTrim`, `stopMediaTrim`, `waitForMediaTrim`; hooks in `runMediaWatcher`, `start`, `stop`, `handleCommand` block list |
| D2 | Log | `src/cdng/LogCurve.hpp` (205), `tools/gen_log_curve.py` (46), `tools/log_curve_test.cpp` (304) | Types.hpp (`CdngLog`, `toString`, `cdngLogFromString`, `cdngLogStoredBits`, `cdngLogAvailable`); LossyDngEncoder.cpp/.hpp (+53); CC (`setCdngLog`, `cdngLogApplicableLocked`, `emitLogAppliedIfChangedLocked`, `CdngLogTake`, `CdngLogPlan`, settings load/save); ModeLadder.hpp (log words); App `set_cdng_log`; WCP | |
| D3 | RAM write buffer, safety stop, buffer bar | `src/util/BufferBudget.hpp` (324), `tools/buffer_budget_test.cpp` (133), `tools/storage_buffer_conf_test.cpp` (141) | HardwareConfigText.hpp (+17, `[storage]` keys); CC (`FrameBufferGauge`, `frameBufferStatus`, queue sizing); App (`runBufferEvents`, `runBufferSafetyStop`, `set_buffer_mode`, `GET /api/buffer`, `buffer` event); WCP (bar, Frames/RAM, pill rules) | |
| D4 | Max fps from the sensor probe | `src/camera/FpsCeiling.hpp` (47), `tools/fps_ceiling_test.cpp` (47) | CC (`fpsLimitTableOnly`, `tableMaximumFpsForResolution`, `maximumSupportedFpsForResolution`, `modeMaximumFps`) | |
| D5 | Storage pre-roll | `src/util/StoragePreroll.hpp` (273), `tools/storage_preroll_test.cpp` (138) | App (`requestStoragePreroll`, `stopStoragePreroll`, `runStoragePreroll`, `runStoragePrerollOnce`, `set_storage_preroll`, `storage_preroll`); CC (`startStoragePreroll`, `storagePrerollError`, `finishStoragePreroll`, `prerollMaximumFps`, `PrerollMeasure`); WCP (PRE-ROLL pill); RecordingDropWarning.hpp (+5) | |
| D6 | Lossless JPEG fps cap lifted | none | CC `losslessCaptureLimited`, `losslessMaximumFps` | |
| D7 | Speed ramp "After the take" | none | Types.hpp `fpsSpeedRampReturn`; CC `setFpsSpeedRamp`, `restoreFpsAfterRampLocked`; App `set_fps_speed_ramp`; WCP | |
| D8 | Clear HDR explicit on/off overrides the ladder | none | Types.hpp `ladderOverride`; CC `ladderActiveForLocked`, `setClearHdr`, `setModeLadder`, `fillLadderFieldsLocked`; ModeLadder.hpp | |
| D9 | WebUI Settings search box | none | WCP only | |
| D10 | WebUI: GPIO dropdowns white, Tally card, "GPIO in/out" | none | WCP only | |

### 5.2 Practical by path, and not

| Question | Answer |
| --- | --- |
| Practical by path (whole-file `git add`) | The new files of D1, D2, D3, D4, D5 and their tests: about 2 000 of 5 170 lines |
| Not practical by path | The big files carry about 3 200 interleaved lines: `ApertarCoreApp.cpp` (+881; 15 hunks in `handleCommand`, 6 each in `handleWebRequest` and `buildWebStateJson`, 4 in `settingsBody`), `CameraController.cpp` (+882; settings load/save carry Log, ramp and buffer keys in the same hunks), `WebControlPage.cpp` (+1422; 97 hunks, all inside the one function `webControlPageHtml`), Types.hpp, README |
| Needs hunk work | `git add -p` per feature, build and host tests after each. Mixed hunks: `buildWebStateJson` and `settingsBody` (state keys of Log, buffer, pre-roll, ladder_override side by side), the `handleCommand` record/media gate (D1, D3, D5 share one condition), settings persistence (Log, ramp, buffer mode) |
| Order that keeps each step buildable | D4, D2, D1, D3, D5, then D6 to D10 (D5 needs D3's buffer gauge and D1's trim) |
| Estimate | D4, D1, D2: practical. D3 and D5: practical only with hunk surgery (probable; both change `record_start` gating and web state). D9, D10: line ranges inside one string. Fallback if hunk work is refused: keep D3, D5, D7, D8 as one commit under an honest subject, split only D1, D2, D4, D6, D9, D10 |

## 6. The clean series for this half

Rules: one complete, buildable, explainable change per commit; upstream prefix style; no tutorial numbers, no branch names, no KB paths;
Core and web halves of a feature in the same commit; tests inside their feature commit; no merges; build fix first.
"(decision)" waits for an owner decision recorded in other sweeps. 52 commits for 92.

### Block B

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| B1 | `build: compile Core without libcamera again (--simulate)` | 145 | The helpers outside the libcamera half were compiled only with libcamera; the guard closes before them |

### Block N: controls, hardware file, viewer, layout

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| N1 | `media: downloads and deletes yield to a take` | 97 | A download waits during a take; a delete blocks record_start, capture_photo, timelapse_start |
| N2 | `web: the Clip Viewer, with a frame-number clock` | 96, 99, 123 | Opens a clip in a viewer that counts frame numbers and asks for the frame due when the answer arrives; list says Loading |
| N3 | `media: serve a clip's WAV with Range; the viewer plays it as the clock` | 98 | GET /api/media/file, 206 and 416, audio_url and sound_text |
| N4 | `core: one action catalog (ActionCatalog.hpp) and list_actions` | 100 | Replaces three copies of the names; unknown action logs "Did you mean"; isoinf, isonan refused |
| N4b | `core: a Clear HDR on / off action for buttons and knob pushes` | 111 | (decision) action clear_hdr; label "Resolution: next" |
| N5 | `core: one writer for apertar-hardware.conf (HardwareConfigText, HardwareConfigStore)` | 101, 102 | Lock, revision, validation, atomic write, 20 versions; IMU writes use it |
| N6 | `core: get_controls and set_controls; validate the hardware file at start` | 103, 104, 108 | Read-only commands answer before the command lock; the template corrected once to HDMI 1080p |
| N7 | `core, web: the Config page saves through the store with its revision` | 105, 106 | A stale page gets 409 and keeps its text; the control socket takes 1 MiB lines |
| N8 | `core: spot a hardware file replaced by a default, and restore it` | 107 | |
| N9 | `core, web: the Controls card, a dropdown of actions per button, knob and pin` | 109, 110, 112, 115 (Controls part), 118, 120, 177 | Single-key set_controls, GPIO peripheral card, add and remove rows; the four page rewrites squashed to their last form |
| N10 | `web: name the timecode modes Time of Day and Clip` | 113 | Shown words only; stored values stay free_run and rec_run |
| N11 | `core: clicks and hold on buttons, knob pushes and PCF pins; GPIO waits for edge events` | 114 (gestures, 1-0-1), 116, 119 | One gesture counter for every push; no 12 ms polling |
| N12 | `core, web: detect I2C devices and show them on a Hardware card` | 114 (I2C probe), 115 (Hardware card), 117 (CFexpress entry) | Probe once, never an address a driver uses |
| N13 | `core: two- and three-way GPIO switches` | 117 (switches) | `[gpio_switches]`; rows come with N9 |
| N14 | `core, web: apply saved controls without a restart; Listen, history, scan, output tests` | 121, 122 | Splitting by hunk into (a) apply without restart, (b) Listen and history, (c) scan and output tests is practical; if not, keep one commit and say so |
| N15 | `core, web: compose clip names from presets, pills and free text` | 127 | set_clip_name_template, preview_clip_name |
| N16 | `web: an Audio recording outline switch beside the red timecode` | 128 | |
| N17 | `web: a Modes pane for sensor modes and the Mode Ladder; Value Lists under Controls` | 172, 173, 174 | Layout moves; filter on several ratios |
| N18 | `core, web: Remote controls card and Try buttons; a GPIO button can be remote only` | 176, 178 | test_input, remoteN |

### Block D: dropped frames, media, drive (needs the d44b177 split)

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| D4 | `camera: take the maximum fps from the sensor probe` | d44b177 FpsCeiling hunks | 4K SDR 60 was capped at 30 by a table; the table stays as fallback |
| D2 | `cdng: Log, a log curve one step down in bit depth` | d44b177 Log | 16 to 12, 12 to 10, 10 to 8; set_cdng_log |
| D1 | `media: trim the recording drive after deletes, with a switch` | d44b177 trim, 137, 138 (pre-roll trim hunk), 179 | Root helper and idle worker; set_media_trim; trim after a delete made outside Core and after the pre-roll clip |
| D3 | `rec: a RAM write buffer with a safety stop and a buffer bar` | d44b177 buffer, 125, 126 | Frames or RAM; the take ends at 90 % buffer; record during a flush starts a new take |
| D5 | `media: storage pre-roll on start, card insert and format` | d44b177 pre-roll | A 2 s take, its clip deleted afterwards |
| D6 | `camera: lossless JPEG on the IMX585 runs to the mode's own maximum fps` | d44b177 hunks | |
| D7 | `camera: speed ramp "After the take", stay or return` | d44b177 hunks | |
| D8 | `camera: an explicit Clear HDR choice holds the mode against the ladder` | d44b177 hunks, 175 | 175 folded in so the 25 fps cap is never added |
| D9 | `web: a search box in Settings` | d44b177 WCP hunks | |
| D10 | `web: GPIO and hardware dropdowns` | d44b177 WCP hunks | (decision) probably drop: style, not a feature |
| D11 | `rec: count the take's dropped frames` | 165 | recording_dropped_frames in state and events |

### Block E: boot config

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| E1 | `core: read and edit the boot config.txt, with a root helper` | 129, 130 | BootConfigText; helper in the shape of apertar-media-trim; host tests |
| E2 | `core: get_boot_config and set_boot_config; the fan mode writes through the same path` | 131 | /api/boot-config, revision, 409 when stale |
| E3 | `web: a Boot Config card in System, with Edit file` | 133, 135, 136, 149, 150, 151 | Sensor per connector, link frequency, interfaces, display; dry run first; README rows |

### Block W: write path and tuning

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| W1 | `cdng: write unpacked 16-bit and 8-bit payloads straight from the frame` | 132 (no knobs) | One write() or writev, no second copy |
| W2 | `rec: allocate raw copies outside the queue mutex and keep the pool through the take` | 134 (no knob) | |
| W3 | `media: mount CFexpress re-inserts with noatime and umask` | 138 mount strings | |
| W4 | `cdng: drop a DNG's pages from the page cache after the fsync` | 140, 143 (hunks), 168, 169 | Default only; the clip line prints dontneed, writeback, sync_ms; dropped_copy_slot in the stats line |
| W5 | `rec: cap the web preview while a raw take runs` | 141, 143 (hunks) | (decision) only if the two-take test shows it is needed |
| W6 | `config: a media tuning file and apertar-tune` | 170, 171 | (decision) only if the new architecture is accepted; else drop |
| | dropped | 139, 144 | RT knobs; one fixed capture-thread priority if the test shows it helps |

### Block S: sensors and camera

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| S1 | `camera, web: IMX585 modes from tables; resolution families and ratio rows` | 142, 157, 158 | Skip 142's whitelist step; keep its 3840x2072 and 1920x1036 migration |
| S2 | `mlv: declare the cDNG black and white level at every bit depth` | 147 | One definition in BlackLevel.hpp |
| S3 | `playback: open every DNG size Core writes, up to 5472x3648` | 148 | |
| S4 | `camera, web: the IMX283 sensor family (57 modes)` | 159, 160, 161 | Table, transport rule, pills, PCF step |
| S5 | `web: Mode Ladder crop thumbnails are 16:9` | 166 | Fold into the first-half Mode Ladder commit |
| S6 | `camera: a Preview temporal denoise switch, off by default` | 180 | (decision) 451-line header is new ground |
| S7 | `camera, web: frame-rate phase lock pins {d, d+1}; a switch on the Performance card` | 181, 182 | |

### Block P: split clips

| New | Subject | Holds | Body |
| --- | --- | --- | --- |
| P1 | `cdng: split a take into part folders (frames_per_folder), with tools/flatten_clip.py` | 183, 184 | exFAT create cost grows with folder size |
| P2 | `media: a worker flattens split clips while the camera is idle` | 185, 186, 187 | 186 and 187 are fixes of 185 |

(decision) P1 and P2 serve one drive test; keep, off by default, or drop.

## 7. Method and limits

- Read: all 92 messages; `--stat` and shortstat for every row; hunk headers of d44b177; full diffs of 137, 138, 175, 142; `git cat-file` of the referenced shas.
- Not done: no full read of the 5 170-line d44b177 diff; function lists come from hunk headers and added-line searches (probable for sizes, confirmed for the file list).
- Not done: building each proposed commit. This is a plan; nothing was rewritten.
- N-block items depend on first-half commits (ModeLadder, fps phase lock 80ddac1) that must already be in place.
