# Sweep X7a: commit series, Core, first half (commits 1-95)

Range: `git log --reverse origin/main..cinemate-port`, commits 1-95 = `db17860` .. `27eac5a`, 2026-10-26 .. 2026-10-29.
Ref: @cinemate-port 01f170c. Upstream comparison: `/home/user/wt/core-upstream` @upstream-1.6.0.

## Summary

| Fact | Value | Evidence |
| --- | --- | --- |
| Commits in half | 95, all linear, 0 merges (the 10 merges of the series are commits 146-167, second half) | `git log --merges` |
| Authors | Patrik Eriksson (author field) on all; model named only in trailer | log |
| Trailer `Co-Authored-By` | 95 of 95 (Claude Opus 5.5 on 2-55, Claude Sonnet 5.5 on 1 and 56-95) | `git show -s` |
| Trailer `Tested:` | 95 of 95; 55 of 95 are "desk only" or "pi build (see next run)" or "built on the Pi next" | confirmed |
| `Why:` / `What:` body | on nearly all; all 95 have a body | confirmed |
| Upstream history | 1 commit, "1.6.0 Release", no trailers, no body. Fork main: 8 commits, prefix style `camera:` `core:` `web:` `scripts:` `build:`, lower case, one line, no trailers | `git -C core-upstream log`, `git log origin/main` |
| Subjects with tutorial number | 46 (T33), 47 (T33), 56 (T34), 57 (T34), 91 (T47), 92 (T47), 93 (T48), 94 (T49) | subjects |
| Bodies with T/Q numbers | 2,3,6,7,11,16,17,19,25,26,28,43,46,47,56,57,61,67,69,91-94 | grep `\b[TQ][0-9]+\b` |
| Bodies citing SHAs that do not exist in the repo | 9 SHAs (7e9fef0 is a libcamera sha, not counted): 775083f, 76094a9, 47d44ff, 71487c5, 84081f7, a89a5df, 6c34e8a, 5d06b67, 753f181 (commits 7d9dd60, 4f7975f, ac00fb0, 117065d, 6d217c7, ff33d2d, fee41e6, 2f43ecc) | `git cat-file -t` fatal |
| Bodies citing clip ids / dates / "User" | C0001..C0106, "User, 2026-10-28", "apertar.local", "on the Mac", KB path `working/research-30fps-answer.md` | grep |
| Tests named in `Tested:` but absent from the tree | `phase_lock_sim.cpp` (80ddac1), "ModeLadder host test 28/28 .. 38 checks" (56, 57, 62-64, 69) | `git ls-tree`: no `tools/*ladder*`, `*phase*` |
| Commits that do not build alone (stated in the series' own text) | 80ddac1 (fixed by 8f7dc39); 438a342 (fixed by e8bb1b7); 4f7975f and ab972fe are warning fixes | confirmed from bodies of 8f7dc39, e8bb1b7 |
| Probable non-building | e16033e adds `std::vector` to `Types.hpp` without the include; 62c1711 adds `#include <vector>` | probable (include order dependent) |

Upstream has nothing like `Co-Authored-By` or `Tested:`. Original Apertar's history is one release commit. No upstream precedent for per-commit trailers, so they are new ground. `Tested: desk only (built on the Pi next)` is a claim that a later commit makes true; it does not describe the commit.

## Classification, commits 1-95

Class key: F feature, FIX(n) fix of commit n, REV undo of n, WORD wording churn, BUILD build fix, DOC, TEST.

| # | sha | class | note |
| --- | --- | --- | --- |
| 1 | db17860 | F | one libcamera request per raw buffer, 8 buffers in Clear HDR. Subject fine |
| 2 | 43a54f3 | F (refactor) | dma-buf sync into a free helper; prep for 3,4 |
| 3 | fc7eb16 | F | copy hand-off API; unused until 4. Body: T24,T25 |
| 4 | 351a3ee | F | copy on a recorder worker |
| 5 | d9f00d4 | F | audio recorder told when queued |
| 6 | 4ab1057 | F | sensor mode binning. Body T26 |
| 7 | 80ddac1 | F, does not build | phase lock; `phaseLockStatus` private. Body T27, "not built", "T27 reference patch, applied unchanged" |
| 8 | 8f7dc39 | FIX(7) BUILD | compile error |
| 9 | 3a18db0 | FIX(7) | pin history 4 to 16; cause is 1 (8 requests in flight) |
| 10 | 114bfb9 | FIX(7) | seed history; "A deeper history (3a18db0) alone does not cover" |
| 11 | 438a342 | F, does not build, mixes | MediaFault, MediaProbe, MediaIntent, 3 writers, audio, App watcher, WCP; 14 files, +810. Body T28; "two context lines re-applied by hand" |
| 12 | e8bb1b7 | FIX(11) BUILD | hunk landed in the wrong worker loop |
| 13 | 0b1632f | FIX(11) / F | CFexpress HAT slot bit (new `CfeHat.hpp`), bounded stop. Touches a hardware class |
| 14 | a3ac8da | FIX(13) | card stays removed until remounted |
| 15 | 70e8376 | F | 4 lines, `media_state`, `media_alive` in `get_state`; belongs to 11 (11's body already says "state media_state/media_alive") |
| 16 | 26da30e | F, mixes | MediaProfile, root helper `apertar-media-tune`, sudoers, tmpfiles; T24,T29 |
| 17 | 60ce8e9 | F | audio writer thread, 1 s ring; T28,T30 |
| 18 | 4ce382e | F | take pushed to the card once a second via syncfs |
| 19 | 0358fcf | FIX(16)+FIX(17) REV partial | exFAT row back to {4,12,0}; audio ring back to 100 ms. Two unrelated reverts in one commit |
| 20 | 441e42a | F | sync_file_range after each DNG |
| 21 | 7d9dd60 | FIX(18) | syncfs -> folder fsync |
| 22 | 086443c | F (fix of 1 line) | `recording` event broadcast. Unrelated to the media chain, sits inside it |
| 23 | 5b68f1f | FIX(21) | per-file fsync, then the folder |
| 24 | b606c4f | FIX(17) | audio_capture.raw fsync once a second |
| 25 | ebdcd08 | REV partial + F, mixes | `APERTAR_MEDIA_TUNE=1` opt-in (undoes 16's default) AND audio drift fit (changes 17). Two unrelated subjects joined by `;` |
| 26 | 3c4f07d | F | prefix `web:` but diff is only `ApertarCoreApp.cpp` (state JSON). T20,T21 |
| 27 | bda2066 | FIX(26) | rounding; touches App and WCP |
| 28 | faa2958 | F | speed ramp behind `fps_speed_ramp`; 7 files, +396. T31 |
| 29 | b5847c7 | F | 25 fps cap for 4K Clear HDR 16-bit; App + CC + WCP |
| 30 | 4f7975f | BUILD(28) | `-Wformat-truncation`; body cites missing sha 76094a9 |
| 31 | 8175273 | F, mixes | Clear HDR holds ISO and WB AND caps ISO per mode |
| 32 | 646a194 | F | `iso_actual`; `set_iso_auto enabled=false` locks gain |
| 33 | 8e8ea2e | F | presets carry every operating-mode switch (Core half; web half is in 35) |
| 34 | e5757d7 | FIX(31,32) | round-up of gain to ISO code |
| 35 | ac00fb0 | F, mixes | WebUI speed-ramp block AND preset switches |
| 36 | 92b4be3 | FIX(28) | ramp switch carried across formats |
| 37 | d7ff071 | F | `conform_fps`. Unrelated to the ramp or ladder; in the middle of both |
| 38 | 117065d | FIX(7) | phase-lock switch carried across formats; sibling of 36 |
| 39 | ca7b7c2 | F | experimental stretched WAV; 5 files |
| 40 | b858d04 | FIX(39) | drop `0 0` key-frame line |
| 41 | 6d217c7 | F | `iso_max` in the state |
| 42 | e25fd2b | F, mixes | WebUI: green values, ISO list follows `iso_max`, ISO lock |
| 43 | 97adea0 | F | `[camera] max_fps` ceiling and `fps_max` |
| 44 | bcedbe5 | REV(43) | "User does not want a build-wide FPS ceiling after all" |
| 45 | eaf9538 | F | bit depth and Clear HDR on the resolution line |
| 46 | b0e90ad | F, mixes, tutorial no. | value lists + free stepping + flicker-free angles in one subject; 311 lines App only. T33 in subject |
| 47 | ff33d2d | F, tutorial no. | Value Lists card. T33 in subject |
| 48 | e58ae40 | WORD | `16 b` |
| 49 | fee41e6 | REV(48) | "reverts 5d06b67" (= 48, old sha) |
| 50 | 2f43ecc | F (tiny) | lossless ISO 1600 |
| 51 | f4fb084 | F | recording-frame and red-timecode switches |
| 52 | 4d5fdd1 | WORD | removes explanatory text of 51's switches |
| 53 | 15bba86 | WORD/F | white instead of green for auto ISO, WB, shutter (re-colours 42) |
| 54 | 60645d4 | F | WB dial reaches Auto. Prefix `hw:`, file is `ApertarCoreApp.cpp` |
| 55 | b5b787e | F, mixes | auto ISO in IMX585 lossless AND "Auto everywhere but Clear HDR" (WCP). "Unverified" in its own Tested line |
| 56 | 88e644d | F, tutorial no. | `ModeLadder.hpp`, 283 lines; no test file in tree despite "28 of 28" |
| 57 | 0041ba0 | F, tutorial no. | wires the ladder in |
| 58 | c232196 | WORD | removes explanation under Value Lists (1 deletion; compare 52) |
| 59 | f81108d | WORD | Stepping / Increment labels |
| 60 | e58e7e5 | WORD | italic, not green (undoes 42 and 53) |
| 61 | f2ebe6e | F | "Clear HDR records uncompressed, SDR lossless"; ladder's compression rule. T34 |
| 62 | a7b6f82 | WORD | "rung" -> "resolution" in messages |
| 63 | cdf83cd | WORD | "rung" -> "resolutions" in the API; follow-up of 62; file key still `rungs=` read |
| 64 | 3cae990 | F | each ladder resolution names its compression; ladder owns it |
| 65 | ab972fe | BUILD(64) | warning |
| 66 | e6ee751 | F | compression greyed while the ladder is active |
| 67 | 920beb0 | F | Mode Ladder editor, 451 lines. T34 |
| 68 | 09256a7 | F / REV partial | active ladder blocks manual resolution/bit depth/HDR; deletes 34 lines |
| 69 | e16033e | F, build risk | "the ladder tells the editor more (T34 UI design)": vague; adds `ladderTops` without `<vector>` |
| 70 | 62c1711 | BUILD(69) | `<vector>` |
| 71 | 1ef94fe | F, mixes | three cards in one commit; +1537/-493; rewrites 67 |
| 72 | 24355d3 | WORD | card order |
| 73 | 65e049e | F | threshold chips between rows |
| 74 | 2424a1f | F | picture size and class under pills |
| 75 | e472b1b | FIX(73) | chip becomes editable max (replaces 73) |
| 76 | 21a7b7f | WORD | label "Resolutions array" |
| 77 | d93a7e3 | F | grey out sensor modes not on the ladder |
| 78 | e7367ec | F | guard: maxes rise down the list |
| 79 | af22759 | F | tile reasons, insert, remove |
| 80 | da8ca9f | F | ladder autosaves; aspect filter (replaces Save button of 67) |
| 81 | b8ee23f | F | ladder orders itself; default maxes |
| 82 | b21c76a | REV(71) partial | removes FPS coverage bar that 71 added; -141 lines |
| 83 | 8bcc5dd | FIX(81) | order and default maxes again |
| 84 | 25f553e | FIX(81/83) | order inside group |
| 85 | 4b04a1d | WORD | Activate/Deactivate naming |
| 86 | b2c15af | WORD | button text |
| 87 | 8050d56 | REV | removes the red x added in 67/71 |
| 88 | 392e812 | F | locked control answers with red warning |
| 89 | 5dfbc6c | F | ladder line opens the card |
| 90 | 909aaa5 | F, mixes | UI timecode vs file timecode; Core + web |
| 91 | f91fafa | F, large, tutorial no. | clip facts cache, hold rule, yield window; 5 new headers, +1047. T47 |
| 92 | ab4cc92 | FIX(91) | list asks the cache first; subject says it is the change |
| 93 | 1af26c8 | F, mixes, tutorial no. | `/api/media/frame` (+ 6 files) AND vendored `third_party/liblj92` (4 files, 1400 lines incl. LICENSE). T48 |
| 94 | bc12c0a | F, tutorial no. | Clip Browser, +930/-586. T49 |
| 95 | 27eac5a | FIX(94) | thumbnail fill |

Counts: F about 45, fixes of an earlier commit of this half about 20 (8,9,10,12,14,21,23,24,27,30,34,36,38,40,52,65,70,75,83,84,92,95 and parts of 13,25), reverts 4 (44, 49, 82 partial, 87), wording churn about 15 (48,52,53,58,59,60,62,63,72,76,85,86 plus 19,25 partials), build fixes 7 (8,12,30,65,70 and the two warnings), merges 0.

## Findings by kind

### Add-then-remove pairs and chains

| Chain | Commits | Net effect | Verdict |
| --- | --- | --- | --- |
| max_fps | 97adea0 then bcedbe5 | not nil. Leaves: `fps_max` in both state JSONs, `losslessMaximumFps()`, `modeMaximumFps()`, `maximumFpsForSettings()`, and the struct `ClearHdrIsoLimits` renamed `CameraSection` (`loadCameraSection`, `cameraSection`) which now holds only the two ISO maxima. Verified by `git diff 97adea0^ bcedbe5` | keep one commit "publish fps_max"; drop the rename (the name is wrong for a struct with two ISO fields) |
| 16 b | e58ae40 then fee41e6 | exactly nil (4 lines flipped back) | both vanish |
| green values | e25fd2b (green), 15bba86 (auto white), e58e7e5 (italic) | the final state is italic; green is gone | fold into one commit that states the final rule |
| red x | 920beb0 / 1ef94fe add, 8050d56 removes | nil for the x | vanish from the series |
| FPS coverage bar | 1ef94fe adds, b21c76a removes | nil | vanish |
| Threshold chip | 65e049e adds read-only chip, e472b1b makes it editable | first is replaced | fold |
| Ladder Save button | 920beb0, 1ef94fe, da8ca9f autosave | Save replaced | fold |
| Value Lists note | ff33d2d adds text, c232196 removes; f4fb084 adds, 4d5fdd1 removes | nil for the text | fold |
| rung naming | a7b6f82, cdf83cd | rename of messages and API keys | fold into the commit that adds the ladder; the final names only |
| fsync chain | 4ce382e syncfs, 441e42a writeback, 7d9dd60 folder fsync, 5b68f1f per-file fsync, b606c4f audio raw fsync | four strategies tried one after another against measured drops (C0001..C0011). Final design = 441e42a + 7d9dd60 + 5b68f1f + b606c4f; 4ce382e's syncfs-per-second is gone | fold into one commit and keep the measurement in the body |
| media tuning | 26da30e default on, 0358fcf exFAT row reverted, ebdcd08 opt-in | helper + sudoers + tmpfiles are in the tree but "not installed and not needed" (ebdcd08's own words) | decision for owner, see X-commits-core-1-5 |
| audio ring | 60ce8e9 1 s ring, 0358fcf back to 100 ms, ebdcd08 fit | ring size net unchanged (100 ms); the writer thread stays | fold |
| ISO rounding | 8175273, 646a194, e5757d7 | e5757d7 fixes both | fold |
| ISO auto in lossless | b5b787e reverses 1.6.0 behaviour ("Upstream kept lossless on manual ISO") | changes stock behaviour | see X-commits-core-1-9 |
| phase lock | 80ddac1, 8f7dc39, 3a18db0, 114bfb9, 117065d | one feature | fold |

### Commits that do not compile on their own

| Commit | Defect | Fixed by | Evidence |
| --- | --- | --- | --- |
| 80ddac1 | `phaseLockStatus` private ("is private within this context") | 8f7dc39 | 8f7dc39 body (confirmed) |
| 438a342 | `encoder.abandon()` call put in `dngWorkerLoop`, `CdngEncoder` has no `abandon()` | e8bb1b7 | e8bb1b7 body (confirmed); 438a342 diff contains both `encoder.abandon()` and `LossyDngEncoder::abandonWrites()` |
| 4f7975f | not a break, `-Wformat-truncation` from 28 | itself | body |
| e16033e | `std::vector<double> ladderTops` in `Types.hpp` without `#include <vector>` | 62c1711 | diff of both (confirmed); breaks only where nothing earlier includes `<vector>` (probable) |
| 3cae990 | warning on `Rung` init | ab972fe | body |
| Many "desk only (built on the Pi next)" commits | not built when committed | later "pi build" commits | `Tested:` lines; 45 commits |

Unconfirmed for the rest: the claim "each new commit builds" needs a per-commit compile. Command: `for c in $(git rev-list --reverse origin/main..<plan-tip>); do git worktree ... ; cmake -DAPERTARCORE_ENABLE_LIBCAMERA=OFF ... ; done`. Note that a no-libcamera build hides errors inside `#if APERTARCORE_HAS_LIBCAMERA` (80ddac1's error was in that guard's counterpart; 8f7dc39 moved it under `#if/#else`). The series must be built with libcamera on a Pi at every step.

### Trailers

- `Co-Authored-By: Claude Opus 5.5` / `Claude Sonnet 5.5` on every commit. Original Apertar has none. The fork's own 8 earlier commits have none. Two model names flip at commit 56.
- `Tested:` on every commit; text is a per-run log, not a property of the commit: "pi build (see next run)" (25 commits), "desk only (built on the Pi next)" (20), "Pi build pending" (4: 90-93).
- `Why:` / `What:` is good style in itself and the one thing worth keeping. Bodies are long (up to 20 lines) and carry internal ids: T20..T51, Q2, clip ids C0001..C0106, "User, 2026-10-28", KB paths, "on the Mac", "apertar.local". These mean nothing to the original developer.
- Stale SHAs: 9 body references to SHAs that no longer exist (list above); the series was rebased or cherry-picked after the bodies were written.

### Subjects that do not say what changed

| Commit | Subject | Better |
| --- | --- | --- |
| e16033e | "the ladder tells the editor more (T34 UI design)" | name the state fields added |
| 1ef94fe | "Mode Ladder, Speed Ramp and Activated sensor modes cards per the approved design" | "per the approved design" is not a change; three cards |
| 909aaa5 | "the UI timecode and the file timecode are set apart" | say which setting was added |
| 0041ba0 | "the mode ladder, FPS picks the sensor mode between takes (T34)" | ok minus number |
| 8e8ea2e | "presets carry every operating-mode switch" | ok; list the switches |
| 7d9dd60, 441e42a, 5b68f1f | accurate but each is one step of one experiment | fold |
| 4b04a1d | "one naming pattern for sections and modes" | vague |

Message vs diff: 3c4f07d is prefixed `web:` but touches only `ApertarCoreApp.cpp` (state JSON; no page file). b5b787e subject says "auto ISO in IMX585 lossless" and also changes the WebUI offer (WCP). 60645d4 is prefixed `hw:` but the diff is `ApertarCoreApp.cpp` only. 438a342's body says "the WebUI follows media_alive" (WCP, 11 lines): true. 92 (ab4cc92) is "list asks the facts cache" which is in 91's body already ("/api/media answers from a cache"). No commit message was found that contradicts its diff in substance; the mismatches are prefix-level.

### Mixed-purpose commits

11 (writers + audio + probe + watcher + WCP), 16 (profile + root helper + sudoers + tmpfiles), 19 (two reverts), 25 (opt-in + drift), 31 (hold + caps), 35 (ramp block + preset switches), 42 (colour + ISO list + lock), 46 (three controls), 55 (core + web), 71 (three cards), 90 (core + web), 93 (frame render + vendored library).

### No precedent upstream (new ground)

| Item | Commit | Upstream check |
| --- | --- | --- |
| `third_party/liblj92` with LICENSE in Core | 1af26c8 | upstream Core has no `third_party/` (brief) |
| root helper `scripts/apertar-media-tune`, `config/apertar-media.sudoers`, `.tmpfiles.conf` | 26da30e | confirmed: upstream `scripts/` holds only `start-apertar-core.sh`, `config/` only `apertar-core-capture-priority.conf`; no sudoers, no root helper |
| host tests as `tools/*_test.cpp` | later commits | upstream has none |
| `src/util/*.hpp` pure-logic headers (MediaFault, MediaProbe, MediaIntent, CfeHat, MediaProfile), `src/camera/FramePhaseLock.hpp`, `ModeLadder.hpp`, `src/playback/*.hpp` | 11,13,16,7,56,91,93 | upstream has `.cpp` per class, `src/util` mostly small |

## CLEAN SERIES, first half

Style: lower-case prefix as in fork main (`camera:`, `core:`, `web:`, `rec:`, `media:`, `audio:`, `build:`), no tutorial numbers, no `Co-Authored-By`, no `Tested:`; body = what and why in plain words, measurements allowed without clip ids. Every commit is built on the Pi (libcamera on) before the next one. The list covers old commits 1-95; old commits 96-99 belong to the second-half plan.

| New | Subject | Folds | One-line body |
| --- | --- | --- | --- |
| 1 | camera: one libcamera request per raw buffer, 8 buffers in Clear HDR | 1 db17860 | Eight raw buffers keep 4K Clear HDR 16-bit from starving the sensor. |
| 2 | camera: copy raw frames on a recorder worker, not on libcamera's thread | 2 43a54f3, 3 fc7eb16, 4 351a3ee | The dma-buf copy moves to a worker so the libcamera callback returns at once. |
| 3 | rec: tell the audio recorder about a raw frame once it is queued | 5 d9f00d4 | Audio start follows the frame that was really queued. |
| 4 | camera: report each sensor mode's binning | 6 4ab1057 | The state carries the binning of the current mode. |
| 5 | camera: frame-rate phase lock, off by default (fps_phase_lock) | 7 80ddac1, 8 8f7dc39, 9 3a18db0, 10 114bfb9, 38 117065d | A PI servo pins FrameDurationLimits so a long take stays in step with the audio clock; the setting survives a format switch. |
| 6 | media: stop writing and abandon the take when the recording drive is gone | 11 438a342 (writer/audio/probe/App part), 12 e8bb1b7, 15 70e8376 | MediaFault classes errno, writers latch the first fault, state reports media_state and media_alive. |
| 7 | media: notice a pulled CFexpress card at once and stop without hanging | 13 0b1632f, 14 a3ac8da, 11's WCP hunk | The HAT slot bit marks the medium removed before I/O blocks; a pulled card stays removed until remounted. |
| 8 | media: profile the recording medium; per-filesystem writer settings | 16 26da30e (profile part), 19 0358fcf (exFAT row), 25 ebdcd08 (opt-in half) | Writers, queue and buffers follow the filesystem; exFAT keeps 4 writers. Root helper and sudoers stay out, or opt-in only (owner decision). |
| 9 | rec: write the take through to the card once a second | 18 4ce382e, 20 441e42a, 21 7d9dd60, 23 5b68f1f, 24 b606c4f | Per-file writeback, then fsync of finished files and the clip folder each second; a pulled card loses at most about a second. |
| 10 | audio: capture writer thread; drift from a least-squares fit | 17 60ce8e9, 19 0358fcf (ring default), 25 ebdcd08 (drift half) | PCM is written off the capture thread; ring stays at 100 ms; drift is the slope over every block. |
| 11 | core: broadcast the recording event to every client at once | 22 086443c | The touch UI hears a take started elsewhere without waiting for a poll. |
| 12 | core: storage label says Media Removed; time left follows format and bit depth | 26 3c4f07d, 27 bda2066 | Minutes truncate to a tenth, like the touch UI. |
| 13 | camera: speed ramping, FPS changes during cDNG and MLV takes (fps_speed_ramp) | 28 faa2958, 30 4f7975f, 36 92b4be3 | One switch for every format; the log timecode buffer fits -Wformat-truncation. |
| 14 | rec: experimental stretched WAV after a speed-ramp take | 39 ca7b7c2, 40 b858d04 | Rubber Band stretches the audio to the ramp map. Marked experimental. |
| 15 | camera: cap 4K Clear HDR 16-bit at 25 fps | 29 b5847c7 (incl. its WCP and PCF hunks) | The back end delivers about 28 fps at 30; 25 is the observed limit. |
| 16 | camera: Clear HDR holds ISO and WB; ISO limits per mode; iso_actual and iso_max in the state | 31 8175273, 32 646a194, 34 e5757d7, 41 6d217c7 | Auto ISO and WB freeze at the measured value; the locked gain rounds up so the gain code stays. |
| 17 | camera: lossless cDNG allows ISO 1600; auto ISO stays on in IMX585 lossless | 50 2f43ecc, 55 b5b787e (Core part) | Changes 1.6.0 behaviour (lossless forced manual ISO); owner to confirm. |
| 18 | hw: the WB dial reaches Auto below the lowest value, as ISO does | 54 60645d4 | Dial symmetry. |
| 19 | camera: conform_fps, the project's timeline rate | 37 d7ff071 | Default 25. |
| 20 | camera: publish fps_max, the current mode's FPS ceiling | 43 97adea0, 44 bcedbe5 (net) | Shares the sanitiser's ceilings; no [camera] max_fps, no rename of ClearHdrIsoLimits. |
| 21 | core: presets carry every operating-mode switch | 33 8e8ea2e | Speed ramp, phase lock, timecode mode, Clear HDR and HDR knobs are saved and restored. |
| 22 | core: value lists, free stepping, flicker-free angles | 46 b0e90ad | Split in three if possible: value lists; free stepping; angles. |
| 23 | core, web: recording frame and red timecode switches | 51 f4fb084, 52 4d5fdd1 | Two indicator switches. |
| 24 | core, web: separate the UI timecode from the file timecode | 90 909aaa5 | Say which setting is new. |
| 25 | camera: ModeLadder, the pure logic of the mode ladder | 56 88e644d, 62 a7b6f82, 63 cdf83cd, 65 ab972fe | Resolutions, FPS limits and compression per resolution; final names only. Commit the host test it was measured with. |
| 26 | camera: the mode ladder picks the sensor mode from the FPS between takes | 57 0041ba0, 61 f2ebe6e, 64 3cae990, 68 09256a7, 69 e16033e, 70 62c1711 | An active ladder blocks manual resolution, bit depth and Clear HDR; the state lists ladder fields. |
| 27 | web: show what the camera decides in italic; ISO list follows iso_max | 42 e25fd2b, 53 15bba86, 60 e58e7e5, 45 eaf9538, 55 b5b787e (WCP part) | One rule, final state only; resolution line shows bit depth and Clear HDR. Drops 48/49. |
| 28 | web: Value Lists card | 47 ff33d2d, 58 c232196, 59 f81108d, 86 b2c15af | Stepping, Increment, flicker-free angles on/off. |
| 29 | web: Speed Ramp card | 35 ac00fb0, 72 24355d3, speed-ramp part of 71 | Ramp and preset switches on one card. |
| 30 | web: Mode Ladder and Activated sensor modes cards | 66 e6ee751, 67 920beb0, rest of 71 1ef94fe, 73-85, 87-89 | Autosaves, orders itself, defaults 25/33/50/+25. Final design only; 82, 87 vanish. |
| 31 | core: cache per-clip facts for /api/media; hold rule and yield window | 91 f91fafa, 92 ab4cc92 | List takes 7 ms after the first 4.2 s scan on 105,000 files. |
| 32 | build: vendor liblj92 | 93 1af26c8 (third_party part) | New third-party dependency, with LICENSE; owner decision. |
| 33 | core: draw a frame on demand, /api/media/frame | 93 1af26c8 (rest) | Frame number to image. |
| 34 | web: the Clip Browser in the touch UI's shape | 94 bc12c0a, 95 27eac5a | Replaces the old media list. |

Result: 95 old commits to 34 new. Of the old 95: 24 are folded as fixes, 4 vanish or reduce to nil (44 with 43 as a net; 48+49; 82; 87), 14 wording commits are folded, 0 merges to linearise in this half.
Needs a split or interactive staging because one old commit feeds several new ones: 11, 16, 19, 25, 29, 55, 71, 93.

## Open points for the owner

1. Trailers: keep `Co-Authored-By` / `Tested:` or drop. Upstream has neither.
2. Root helper `apertar-media-tune` + sudoers + tmpfiles: ship, ship opt-in, or drop.
3. `third_party/liblj92`: accept a vendored library or replace with an in-tree decoder.
4. Reverting auto ISO behaviour in lossless (new 17).
5. Host tests named in `Tested:` (phase lock, ladder) are not in the tree.
