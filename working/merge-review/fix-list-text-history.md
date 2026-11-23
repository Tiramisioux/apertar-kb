# Fix list: comments, UI text, README, commit series

Editor's list for the merge review. Domain: the text the original developer reads that is not code: comments as a
whole-port rule, operator-visible strings that leave the source, the READMEs and driver docs, and the commit series of
Core, UI and both drivers. No units; built from the sweeps `slop`, `commits-core-1`, `commits-core-2`,
`commits-ui-drivers` and the documentation side of `knobs`. Refs: Core `cinemate-port` `01f170c`, UI `7ea9afc`,
imx585 `cd548ef`, imx283 `68b7dc9`, upstream `upstream-1.6.0`, fork main Core `f60e301`. Yardstick:
`apertar-conventions.md` (STY-8, STY-9, STY-14, STY-15, WEB-18, R8).

## Already done on the improvement branch

| What | Where |
| --- | --- |
| GPIO chip setting back on the Controls page, checks per chip | Apertar-Core `04fe197` (worktree `/home/user/wt/core-work`) |

Nothing in this domain is done yet. The improvement branch (`work/improve`, 14 commits past `01f170c`) still holds 85
`cinemate` mentions and 122 `T<nn>` tokens in `src include scripts config README.md` (`git grep -c`, confirmed), and its
own commits follow the pattern TXT-6 asks the owner about (author `Claude`, `Claude-Session:` lines).

## How this list splits the work with the other editors

The per-file comment and text rewrites are already items in the domain lists. This list owns the rule they share,
the gate that proves them done, the files no list names, the driver doc entry point, and the commit history.

| Text | Owned by |
| --- | --- |
| Camera comments, ladder file header, `CineMate Log` naming, driver comments and docs body | CAM-11, CAM-12 |
| Driver commit histories (imx585 55, imx283 93) | CAM-38 |
| Recorder, encoder, playback, media comments and log lines | REC-12 |
| App, header, scripts, config comments; hardware-file template comments | APP-17 |
| Core README | APP-18 |
| Hardware classes comments | HW-38 |
| UI comments; UI commit series and its Core pairing | UI-20, UI-9 |
| WebUI comments, card copy, hints, glyphs, `data-search` keyword | WEB-33, WEB-34 |

## Summary

| Id | Title | Kind | Sev | Eff | Rec |
| --- | --- | --- | --- | --- | --- |
| TXT-1 | Core history cannot be reviewed: a 12-feature squash, 10 merges with conflict work inside, swapped hunks | commit | blocker | L | fix-later |
| TXT-2 | No single clean series: experiment chains, flip-flops and four rewrites of one card stay in history | commit | major | L | fix-later |
| TXT-3 | Commits that do not build alone; Tested: lines describe a later run; tests cited that are not in the tree | commit | major | M | fix-later |
| TXT-4 | Behaviour changes against 1.6.0 hidden inside unrelated commits | commit | major | S | fix-later |
| TXT-5 | Commit messages carry tutorial and work-package ids, dead SHAs, KB paths, names and branch prefixes | commit | major | M | fix-later |
| TXT-6 | Authors and trailers: 11 + 14 commits authored "Claude", three model names, session URLs, cherry-pick lines | commit | major | S | ask-owner |
| TXT-7 | One comment rule and one gate for all four repos; density 3x to 26x upstream | slop | major | L | fix-later |
| TXT-8 | Driver docs: stale 7-mode README section, no link to APERTAR.md, three branch names, image pulls the old branch | docs | major | S | ask-owner |
| TXT-9 | New ground arrives as ordinary feature commits with no note for the original developer | new-ground | minor | S | keep-and-document |
| TXT-10 | Developer-only knobs that stay have no home once the README table goes | docs | minor | S | keep-and-document |

Order of work: TXT-7 runs per domain after the structural fixes; TXT-8 and TXT-10 after CAM-12 and APP-18; the commit
items (TXT-1 to TXT-6, TXT-9) are the last step, because the series follows the final code.

---

## TXT-1. Core history cannot be reviewed: a 12-feature squash, 10 merges with conflict work inside, swapped hunks

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | blocker | L | no | fix-later | X-commits-core-2-1, X-commits-core-2-5, X-commits-core-2-2, X-commits-core-1-8 |

**Where.** Core `d44b177`; merges `4581a69 4b2eeac 389f8a7 57519a2 0f4d06d 5e25f69 1944995 a47dc28 dd00206 d08b88f`;
`04bac89`, `e0fa852`, `766aba8`; mixed commits `438a342 26da30e 0358fcf ebdcd08 8175273 ac00fb0 e25fd2b b0e90ad b5b787e
1ef94fe 909aaa5 1af26c8`.

**Problem.** `d44b177` is one commit of 25 files, +5170 -100 (confirmed, `git show --shortstat`), "Squashed from 19
commits"; its subject names 7 of the 12 features it holds, and its body says "Not compiled or run yet: the pre-roll and
the Clear HDR override" (body line 43, confirmed). Ten merges make the series non-linear (`git log --merges` = 10,
confirmed); `a47dc28` and `dd00206` resolve conflicts in `CameraController.cpp` and `WebControlPage.cpp` inside the
merge, where no reviewer sees them; `389f8a7` and `5e25f69` bring the same content a second time. `04bac89` ("trim after
a delete made outside Core ...") holds the mount-option change and the free-space trim, and `e0fa852` ("noatime and
umask on the re-insert mount") holds the pre-roll trim change: each carries part of the other's content (confirmed;
correction to the sweep, which said `04bac89` held only the trim hunk). Twelve more commits mix two to five features.
The original developer cannot review or bisect this.

**Apertar way.** STY-15: upstream history is linear on `main`, one plain self-contained change per commit, no merges of
work branches. Fork main follows it: 8 linear one-topic commits, prefix style `camera:`, `core:`, `web:`, `build:`
(`git log 35dbe67..f60e301`).

**Rework.**

1. Write `working/merge-review/commit-plan.md`: one ordered table for Core that joins the first-half plan
   (`raw/sweep-commits-core-1.md` "CLEAN SERIES", new 1-34) and the second-half plan (`raw/sweep-commits-core-2.md`
   section 6, blocks B N D E W S P). Put `B1` (build without libcamera) first. Add a column with the UI commit that pairs
   with each Core commit (UI-9 holds the 15-commit UI plan).
2. Split `d44b177` in the order D4, D2, D1, D3, D5, D6-D10 (`sweep-commits-core-2.md` 5.1-5.2). New files go by path
   (`LogCurve.hpp`, `BufferBudget.hpp`, `StoragePreroll.hpp`, `FpsCeiling.hpp`, `scripts/apertar-media-trim`, their
   tests); the hunks in `ApertarCoreApp.cpp`, `CameraController.cpp`, `WebControlPage.cpp`, `Types.hpp` and `README.md`
   go with `git add -p`. Fallback if hunk work is refused: D3, D5, D7, D8 in one commit whose subject names all four.
3. Linearise: rebuild on a new branch from `origin/main` by cherry-picking the plan order; drop `389f8a7` and `5e25f69`;
   redo the conflict hunks of `a47dc28` and `dd00206` by hand inside the sensor commits S1 and S4.
4. Put the mount options alone in W3 and both trim hunks in D1.
5. Split the other mixed commits along the "Folds" column of the first-half plan (old 11, 16, 19, 25, 29, 55, 71, 93
   need `git add -p`).
6. The end tree must equal the reviewed tree: the series is a re-cut, not a change.

**Owner decision.** None here (trailers are TXT-6; the fallback in step 2 needs no decision).

**Check here.** `git log --merges origin/main..<clean-tip>` prints nothing; `git diff <final-improvement-tip> <clean-tip>`
is empty; `git show --shortstat` of every new commit is one topic; TXT-3's build loop passes.

**Needs the Pi.** Nothing beyond TXT-3's per-commit libcamera build, which runs here.

**Risk.** Force-push of `cinemate-port`, which Cinemate also tracks: publish the clean series on a new branch and keep
the old one.

**Depends on.** All code fixes of milestone 1 (the series is cut from the final tree).

---

## TXT-2. No single clean series: experiment chains, flip-flops and four rewrites of one card stay in history

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | L | no | fix-later | X-commits-core-1-2, X-commits-core-1-3, X-commits-core-1-4, X-commits-core-1-12, X-commits-core-2-4, X-commits-core-2-6, X-commits-core-2-7, X-commits-core-2-12 |

**Where.** Core commits 58-89 (Mode Ladder page, 36 commits, mostly `WebControlPage.cpp`); `4ce382e 441e42a 7d9dd60
5b68f1f b606c4f` (write-through chain); `e58ae40`/`fee41e6`, `97adea0`/`bcedbe5`, `e25fd2b`/`15bba86`/`e58e7e5`,
`1ef94fe`/`b21c76a`/`8050d56`; Controls card `d282de9 f5fe41b fa3a798 b74b4aa` (four rewrites); gestures `0a98868` then
`0c49601`; `d44b177`/`caa0153` then `31d5418` (25 fps cap added then removed); `0ed07ea` then `adac040` (DONTNEED default
flipped); env-knob commits made moot (`c57c284 6ef0ddc e55557d 4abbef0 fb557e9`); the 14 improvement-branch commits,
of which `0d13a6f` corrects `b923c06` (`fix-log.md` C10).

**Problem.** The history records how each design was found, not what it is. The Mode Ladder page is rebuilt across 36
commits (`1ef94fe` alone +1537/-493); the Controls card is written four times (about +1345 -446); a 25 fps cap is added
in two commits and removed in a third that leaves `(void)settings; (void)sensorFamily;`; `e58ae40` + `fee41e6` net to
nil; `97adea0` + `bcedbe5` do not net to nil and leave a rename. A reader must read every intermediate design to learn
the final one.

**Apertar way.** STY-15: one plain, self-contained change per commit. Fork main has no fix-of-fix commits (8 commits, 8
topics).

**Rework.**

1. In `commit-plan.md` (TXT-1 step 1) fold each chain into the one new commit the sweeps name: Mode Ladder page into
   first-half new 27-30; write-through chain into new 9 ("rec: write the take through to the card once a second", final
   design `441e42a + 7d9dd60 + 5b68f1f + b606c4f`, no `syncfs` step); Controls card into N9; gestures into N11; the
   25 fps cap and its removal into D8 so the cap never appears; DONTNEED into W4 with the final default only.
2. Drop the nil pairs (`e58ae40`/`fee41e6`; first-half 48/49) and the reversed UI marks (coverage bar, red x).
3. Drop env-knob commits whose knob the code domains delete (verdicts: CAM-9, REC-21, APP-9, APP-14, APP-15). Commits
   that become empty (`c57c284`, `6ef0ddc`, old 139 and 144) leave the plan.
4. Fold each improvement-branch commit into the feature commit it fixes (for example `0977dd6` pre-roll default into
   D5, `0d13a6f` + `b923c06` + `3650027` into S6). `fix-log.md` keeps the story; the series shows the result.
5. Order by topic, so `086443c`, `d7ff071`, `60645d4`, `2c259b9`, `a40112a` sit beside the feature they belong to.

**Owner decision.** None.

**Check here.** `git log --oneline origin/main..<clean-tip> | wc -l` is about 34 + 52 for Core; no subject repeats a
feature name of an earlier subject with "fix", "again" or "restore"; `git diff` against the final tree is empty.

**Needs the Pi.** Nothing.

**Risk.** Squashing hides the measurement record behind each step. Keep the numbers in the new commit body (TXT-5).

**Depends on.** TXT-1.

---

## TXT-3. Commits that do not build alone; Tested: lines describe a later run; tests cited that are not in the tree

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | M | no | fix-later | X-commits-core-1-1, X-commits-core-1-7 (Tested part), X-commits-core-2-10, X-commits-core-2-13 (tests part) |

**Where.** `80ddac1` (fixed by `8f7dc39`), `438a342` (fixed by `e8bb1b7`), `e16033e` (fixed by `62c1711`),
`3526e4b`, `f19b245`, `a37a902`, `fa19856`, `d44b177`; `Tested:` lines of 101 Core commits.

**Problem.** Three commits do not build on their own: `80ddac1` declares `phaseLockStatus` in the libcamera-only private
section, `438a342` calls `encoder.abandon()` which `CdngEncoder` lacks, `e16033e` puts `std::vector` in `Types.hpp`, whose
includes are `<cstddef> <array> <cmath> <cstdint> <string> <memory>` only (confirmed, `git show e16033e:...`); the next
commit fixes each. 101 `Tested:` lines say "desk only", "see next run", "built on the Pi next", "pending" or "not
compiled/run" (`git log --format=%B | grep -c`, confirmed): they describe a later run. `80ddac1` names
`phase_lock_sim.cpp` and six commits a "ModeLadder host test 28/28"; no `tools/*ladder*` or `*phase*` exists at
`cinemate-port` (`git ls-tree`, confirmed). `3526e4b` and `f19b245` add 1617 and 1228 lines with no caller.

**Apertar way.** STY-15: each merged commit is self-contained. Upstream has no unit tests and no test claims; the port's
host tests are a separate decision (APP-42, CAM-30, REC-37).

**Rework.**

1. Fold `8f7dc39` into `80ddac1`, `e8bb1b7` into `438a342`, `62c1711` into `e16033e` (they land in first-half new 5, 6
   and 26).
2. Put each header in the commit of its first caller: `HardwareConfigStore` with N6, `BootConfigText` with E2.
3. Run a per-commit build loop over the clean series here, both configurations:
   `for c in $(git rev-list --reverse origin/main..<clean-tip>); do git -C /home/user/wt/series checkout -q $c && /home/user/build/bin/check_core.sh /home/user/wt/series series both || echo "BROKEN $c"; done`
   (`check_core.sh` builds with the local libcamera fork too, so the `#if APERTARCORE_HAS_LIBCAMERA` half is compiled;
   `/home/user/wt/series` is a fresh worktree for this loop only).
4. `Tested:` (if TXT-6 keeps it) states what was run on that commit only. Delete "see next run" forms.
5. For `phase_lock_sim` and the ladder test: commit them as `tools/*_test.cpp` under the tests decision of APP-42, or drop
   the claim from the body.

**Owner decision.** None (the tests decision is APP-42's).

**Check here.** The loop in step 3 prints no `BROKEN`; `git log --format=%B origin/main..<clean-tip> | grep -ciE 'see next
run|built on the Pi next|pending|not (built|compiled|run)'` = 0.

**Needs the Pi.** One full Pi build at the series tip (`cmake` with libcamera on the CM5 image); the host loop covers the
steps in between.

**Risk.** None; history only.

**Depends on.** TXT-1.

---

## TXT-4. Behaviour changes against 1.6.0 hidden inside unrelated commits

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | S | yes | fix-later | X-commits-core-1-9, X-commits-core-2-11 |

**Where.** `b5b787e` (auto ISO kept in IMX585 lossless, WebUI offers Auto), `2f43ecc` (lossless ISO cap 800 to 1600,
one line), `5395fa4` (socket line limit 64 KiB to 1 MiB inside a Config-page commit), `916c1dd` (`isoinf`/`isonan`
refused inside a refactor), `c48e693` (Clear HDR cleared before `start()` when no imx585 is on the bus, inside the IMX283
commit), `dcf09ee` (renames of Adafruit rotary 0-3 and switch positions after five features), `31d5418` (25 fps cap
removed, comment "Removed (User, 2026-11-03)").

**Problem.** These commits change what a stock camera or an existing client does, and the subject does not say so.
`b5b787e`'s own body says "Upstream kept lossless on manual ISO (1.6.0)" and its `Tested:` line says the cap is
unverified with a higher-gain tuning file. A reviewer reading subjects will not find them, and the handoff changelog
cannot list them.

**Apertar way.** No upstream precedent for the message form (upstream has release commits only). The rule this follows
is STY-15's "plain, self-contained": one change per commit, said in the subject.

**Rework.**

1. In `commit-plan.md` give each its own commit, whose subject names the change against 1.6.0, for example
   `camera: lossless cDNG allows ISO 1600 and keeps auto ISO on the IMX585 (changes 1.6.0)` (first-half new 17),
   `ipc: accept command lines up to 1 MiB (was 64 KiB)`, `hw: refuse the actions isoinf and isonan`,
   `hw: rename the Adafruit rotary and switch-position actions`.
2. Whether each change stays is decided in the code lists: CAM-14 and REC-4 (ISO and fps caps), APP-44 (socket limit),
   HW-12 (action names). Drop the commit if the change is reverted there.
3. Each surviving one gets a line in the handoff changelog under "Changes to 1.6.0 behaviour".

**Owner decision.** None here; CAM-14 asks whether the lossless ISO change stays.

**Check here.** `git log --format=%s origin/main..<clean-tip> | grep -c '1.6.0\|was '` matches the number of surviving
changes; each listed SHA in the plan touches one topic.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** TXT-1, CAM-14, REC-4, APP-44, HW-12.

---

## TXT-5. Commit messages carry tutorial and work-package ids, dead SHAs, KB paths, names and branch prefixes

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | M | no | fix-later | X-commits-core-1-6, X-commits-core-1-10, X-commits-core-2-3, X-commits-core-2-9, X-commits-core-2-13 (ids part), X-commits-ui-drivers-6 (rule for the UI), X-commits-ui-drivers-7 and -8 (subject part) |

**Where.** Core: 21 subjects with `T<nn>` (`git log --format=%s | grep -cE '\bT[0-9]{2}\b'`, confirmed), for example
`b0e90ad ff33d2d 88e644d 0041ba0 f91fafa 4629de2 a37a902 fa19856`; bodies with T20-T51, Q2, R2-R8, clip ids
C0001-C0106, "User, 2026-10-28", "apertar.local", "on the Mac", KB paths (`working/research-30fps-answer.md`,
`working/dng-chain`); nine dead SHAs in bodies (`775083f 76094a9 47d44ff 71487c5 84081f7 a89a5df 6c34e8a 5d06b67
753f181`) plus `00f2327` (`ce0bd90`) and `6bd002b` (cherry-pick line of `e625c68`): `git cat-file -t` fails on all
(confirmed for seven). Prefix errors: `drop-frames:` (a branch name) on rows 124-128, `web:` on Core-only `3c4f07d`,
`fb557e9`, `1319967`, `9b5ea14`, `hw:` on App-only `60645d4`; empty subjects `766aba8` ("fixes from the review of the
seven commits above"), `afa00e8`, `f19b245` ("config.txt engine"), `e16033e`, `1ef94fe` ("per the approved design"),
`4b04a1d`. Drivers: WP-585-n in 13 subjects, WP-283-n in 6, `experimental:` in 11.

**Problem.** The ids, names and paths point into Patrik's knowledge base and test nights; the original developer has
none of it (BRIEF vocabulary). Dead SHAs cannot be followed. A branch name as prefix says where the work was done, not
what it changes.

**Apertar way.** STY-15: plain subjects, no internal numbers. The prefix form comes from fork main:
`camera: probe sensor modes at startup, take fps limits from them` (`f60e301`), `core: give Clear HDR raw streams
CPU-cached buffers` (`94ac68d`); body `Why:` / `What:` in plain words (`631721d`).

**Rework.**

1. Message rule, written once at the top of `commit-plan.md`: subject `<area>: <what changed>` with area one of
   `camera core web rec cdng media audio hw ipc ui qml scripts build docs tools`, `core, web:` when both change, the area
   of the files actually changed; body `Why:` and `What:` in plain words; measurements as numbers without clip ids,
   dates or names; no ticket, work-package, design, critic or KB references; no SHA unless it is in the same series.
2. Write the new subjects from the "Subject" columns of the two Core plans and the UI plan (UI-9); drivers follow CAM-38.
3. Gate the series text: `git log --format=%B origin/main..<clean-tip> | grep -nE '\b(T[0-9]{2}|Q[0-9]+|R[0-9]|WP-[0-9]+-[0-9]+|C0[0-9]{3})\b|working/|kb |critic|design §|User,|Patrik|apertar\.local|drop-frames:|campaign|temp branch'` prints nothing.
4. For every SHA left in a body, `git cat-file -t` must succeed in the same repo.
5. The same rule applies to the 14 improvement-branch commits when they fold in (TXT-2 step 4): their bodies name
   `check_core.sh`, worktree names (`lane-hdr`) and "the port's"; rewrite to what changed.

**Owner decision.** None.

**Check here.** Step 3 and step 4 commands on each repo.

**Needs the Pi.** Nothing.

**Risk.** The measured reasons are useful; move them into the body as numbers, do not delete them.

**Depends on.** TXT-1.

---

## TXT-6. Authors and trailers: 11 + 14 commits authored "Claude", three model names, session URLs, cherry-pick lines

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | S | unknown | ask-owner | X-commits-core-1-7 (trailer part), X-commits-core-2-8, X-commits-ui-drivers-6 (trailer part) |

**Where.** Core `origin/main..cinemate-port`: authors Patrik Eriksson 176, Claude 11 (`f19b245 dda1713 2955ef8 8a56545
afa00e8 496817f 900d282 5f5cea2 5e9dd1a 618b2f1 389f8a7`); trailers `Co-Authored-By: Claude Opus 5.5` 108, `Claude
Sonnet 5.5` 67, `Claude Fable 5.1` 9, `Claude-Session:` URLs 20, three `(cherry picked from ...)` lines to absent
objects (confirmed, `git log --format='%an'` and `%(trailers:only)`). UI: all 39 with `Co-Authored-By`, 15 with
`Claude-Session:`. Improvement branch: 14 of 14 authored `Claude`, each with `Co-Authored-By: Claude Fable 5.2` and a
`Claude-Session:` line. imx283: `050e2e3` and `289131a` authored "Your Name" (CAM-38).

**Problem.** One series carries four model names, session URLs nobody outside can open, and a second author name for
work Patrik owns. Correction to the sweep (X-commits-core-1-7): fork main is not trailer-free. All 8 fork-main commits
carry `Co-Authored-By: Claude ...` and `Why:`/`What:`/`Tested:` bodies (`git log 35dbe67..f60e301`, confirmed), so the
trailer form already exists on the merge target; upstream 1.6.0 has none (one release commit).

**Apertar way.** STY-15: upstream has one author, no bodies, no trailers. The conventions leave AI attribution to the
owner ("AI trailers are the owner's call").

**Rework.**

1. Re-author every commit of the clean series as Patrik Eriksson (`git commit --amend --reset-author` while building
   the series, or `--author` on each cherry-pick); "Your Name" in imx283 goes the same way under CAM-38.
2. Apply the owner's answer below to every new commit in all four repos.
3. Delete `Claude-Session:` lines and `(cherry picked from ...)` lines in every case.
4. Write the chosen rule into `commit-plan.md` and the handoff, so later commits follow it.

**Owner decision.** Do merged commits carry an AI attribution trailer? Recommendation: one line, `Co-Authored-By:
Claude <noreply@anthropic.com>`, no model or version name, no session URL, the form fork main already uses minus the
version. Cost of "keep one line": the history differs from upstream's trailer-free style, but is honest and uniform.
Cost of "drop all": matches upstream exactly; attribution lives only in the handoff. Either way the author field is
Patrik and session URLs go.

**Check here.** `git log --format='%an' origin/main..<clean-tip> | sort -u` prints one name;
`git log --format='%(trailers:only)' origin/main..<clean-tip> | sort -u` prints at most the one chosen line; `grep -c
'Claude-Session\|cherry picked'` = 0.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** TXT-1.

---

## TXT-7. One comment rule and one gate for all four repos; density 3x to 26x upstream

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | major | L | unknown | fix-later | X-slop-6, X-slop-1, X-slop-2, X-slop-3, X-slop-4, X-slop-5, X-slop-7, X-slop-10 |

**Where.** Whole port. Densities (comment lines per 1000, `raw/sweep-slop.md` section D, confirmed):
`CameraController.hpp` 185 vs 7; `CameraController.cpp` 54 vs 9; `ApertarCoreApp.cpp` 28 vs 5; `WebControlPage.cpp` 21
vs 0; the 38 new `src/` files 117 vs upstream mean 7; `imx283.c` 333 vs 109; `imx585.c` 198 vs 133. Ids in 272 added
comment lines, names/dates/clip ids in 79, Cinemate as justification in about 60, history narration in 78, 40 banner
lines. Files with hits that no domain list names: `imx283-overlay.dts:115`, `src/lossydng/LossyDngEncoder.hpp:24` and
`.cpp:51` ("CineMate Log"), `tools/clearhdr-gate/pedestal_check.py:2, :13, :88`.

**Problem.** The per-file rewrites sit in seven domain lists (CAM-11, CAM-12, REC-12, APP-17, HW-38, UI-20, WEB-33).
Without one shared rule each editor cuts to a different depth, and nothing proves the port is clean at the end. The
text that leaves the source matters most: `ApertarCore CineMate Log:` journal lines (`CC:3985, :4008`; `LogCurve::describe()`
reaches only the journal via `CC:4041`, not clip metadata as the sweep said), `(CineMate style)` and
`(CineMate's warm-up)` in Core's hardware-file template (`App:5052, :5068`; this is `apertar-hardware.conf`'s template,
not `camera_settings.conf`), `# Apertar mode ladder (T34).` written into `mode_ladder.conf` (`ModeLadder.hpp:319`), and
the `data-search` keyword `cinemate` (`WCP:4912`).

**Apertar way.** STY-8: rare one- or two-line present-tense statements of a hazard or invariant
(`// Never let a stalled preview client block camera event delivery.`, `src/ipc/ControlServer.cpp:25@upstream-1.6.0`).
STY-9: no ticket numbers or other projects' hashes (0 hits in both upstream trees). WEB-18: no comments in the page.
STY-13: codec islands keep their own register. Banners only in QML (upstream `CameraPage.qml` has 19).

**Rework.**

1. Add the shared rule to `apertar-conventions.md` section 7 as the editors' checklist: one line above a function or
   field, what it does now or why it must; at most one provenance line in the header of a ported file
   (`BootConfigText.hpp`, `ButtonGesture.hpp`, `LogCurve.hpp`), with no hash; no T/Q/R/O/WP ids, request, critic,
   design, KB or private paths; no person, date, clip id or commit id; no history ("used to", "as before", "v1"); no
   `// ----` banners in C++; measurements move to the commit body (TXT-5).
2. First pass, before the density work, the five strings that leave the source (list above): rename to `Log`, drop
   the brand from the template lines, drop `(T34)`, drop `cinemate` from `data-search`. The owning items are CAM-11,
   REC-12, APP-17 and WEB-34; this step only puts them first.
3. Each domain editor does its files under its own item. The three files above with no owner: delete the history
   sentence at `imx283-overlay.dts:115`, name the feature `Log` in `LossyDngEncoder.hpp:24` and `.cpp:51`, and change
   `pedestal_check.py:2, :13` to "Clear HDR windowed-crop gate" with no WP id (line 88 may keep `cinepi-raw` as the
   format it reads).
4. Gate script `/home/user/build/bin/check_text.sh <repo> <base>`: runs the grep below on the added lines of
   `git diff -U0 --minimal <base> HEAD` and prints the density table of `sweep-slop.md` section D. Targets: under 30 per
   1000 in new files, under 15 in the big `.cpp`, 0 in `WebControlPage.cpp` beyond one-line hazards. Leave
   `third_party/liblj92` and the codec islands out.
   `grep -nE '\b(T[0-9]{2}|Q[0-9]+|R[0-9]|O[0-9]|WP-[0-9]+-?[0-9]*)\b|request [0-9]+|critic|design (sketch|§)|working/|[Kk][Bb] |[Cc]ine[Mm]ate [0-9a-f]{7}|Patrik|User, 20|C0[0-9]{3}|test night|campaign|// ----'`

**Owner decision.** None.

**Check here.** `check_text.sh` on Core, UI and both drivers prints zero grep hits and densities under target; both
builds and host tests still pass (`/home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests`,
`check_ui.sh`).

**Needs the Pi.** `journalctl -u apertar-core | grep -c CineMate` = 0 after a take with Log on.

**Risk.** Comment-only, except the renamed journal strings; a script that greps the journal for `CineMate Log` breaks.
Keep every comment that states a register constraint or a lock rule.

**Depends on.** CAM-11, CAM-12, REC-12, APP-17, HW-38, UI-20, WEB-33, WEB-34 (they do the files; this item closes them).

---

## TXT-8. Driver docs: stale 7-mode README section, no link to APERTAR.md, three branch names, image pulls the old branch

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| docs | major | S | no | ask-owner | X-commits-ui-drivers-9, X-slop-13 (driver part) |

**Where.** `imx585-v4l2-driver README.md:37, :148` ("## CineMate branch (`cinemate-7modes`)", 7-mode matrix) and
`APERTAR.md:9-15@cinemate-port`; `imx283-v4l2-driver README.md:32`, `APERTAR.md:12-14@cinemate-port`; Core
`src/camera/CameraController.cpp:441-442`, `src/camera/Imx283Modes.hpp:1-2@cinemate-port` (name the driver branch
`cinemate-port`).

**Problem.** A reader of the imx585 README learns 7 modes; `APERTAR.md` says 187 in four families. Neither README
mentions `APERTAR.md` (`grep APERTAR.md README.md` empty in both, confirmed). The driver has three branch names for one
mode set: `cinemate-modes`, `cinemate-port` and `cinemate-7modes` (correction to the sweep: `cinemate-7modes` exists, as
`remotes/origin/cinemate-7modes`). The Apertar-Beta 1.6.0 image builds the old `apertar` branch, whose 1.85:1 crops
(3840x2076, 1920x1038) are not the sizes Core now expects (3840x2072, 1920x1036, `CC:441-442`), so the docs must say
which branch the image takes.

**Apertar way.** STY-14: the README is for the camera builder, second person, honest limits. The baseline imx585 README
on `origin/apertar` has no Cinemate section. CAM-12 step 3 already deletes the CineMate layer table and the 7-mode
matrix, and CAM-22 replaces the branch name in Core's provenance comments.

**Rework.**

1. After CAM-12 step 3: add at the top of both READMEs one line, "Apertar users: see APERTAR.md for the branch to
   install, the config.txt lines and the modes Apertar offers."
2. Name the install branch in one place per driver (`APERTAR.md` "Which branch"), set by the owner's answer below; the
   README clone line and Core's comments (CAM-22) use that name.
3. Delete or rename `origin/cinemate-7modes` on GitHub if it is not used by Cinemate (owner).
4. Handoff line for the original developer: the image build must pull the named branch; the old `apertar` crops differ.

**Owner decision.** Which branch holds the merged driver for Apertar? Recommendation: merge the clean driver series
into the branch the Apertar image already builds (`apertar` for imx585, `master` for imx283), so the image needs no
change and Cinemate keeps `cinemate-modes`. Cost: Cinemate and Apertar then track two branches of one driver, kept in
step by hand. Alternative: keep `cinemate-port` as the Apertar branch; cost: the image build script changes, and a
third name stays in the docs.

**Check here.** `grep -n 'APERTAR.md' README.md` hits once in each driver; `grep -c 'cinemate-7modes\|seven modes'
README.md` = 0 in imx585; the branch named in `APERTAR.md` exists in `git branch -a`.

**Needs the Pi.** Nothing; an image rebuild is the developer's step.

**Risk.** None.

**Depends on.** CAM-12, CAM-22, CAM-38.

---

## TXT-9. New ground arrives as ordinary feature commits with no note for the original developer

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | unknown | keep-and-document | X-commits-core-1-5, X-commits-core-1-11, X-commits-core-2-14 |

**Where.** `1af26c8` (`third_party/liblj92`, 4 files, about 1400 lines, inside the `/api/media/frame` commit);
`26da30e`/`0358fcf`/`ebdcd08` (root helper, sudoers, tmpfiles); `3526e4b` HardwareConfigStore (1617 lines); `f19b245`
BootConfigText (1228); `e625c68` TuningTdnStrip (451); `ba0658d` ClipMerge worker (796); MediaTune (318); header-only
pure-logic classes (`FramePhaseLock.hpp`, `ModeLadder.hpp`, `MediaProbe.hpp`, `MediaFault.hpp`, `src/playback/*.hpp`).

**Problem.** Each brings a structure 1.6.0 does not have (no `third_party/` in Core, no root helper or sudoers in Core,
no header-only logic classes in upstream `src/`), and each lands as one more feature commit. The original developer
learns it is new architecture only by noticing.

**Apertar way.** No precedent in Core. The closest: upstream UI keeps vendored code in `third_party/` and its root
helpers as C++ programs with sudoers rules that list every argument (`Apertar-UI/systemd/*.sudoers@upstream-1.6.0`, R14).
`liblj92` already carries `LICENSE` (MIT, Andrew Baldwin 2014) and `README.apertar.md` naming the upstream commit
(confirmed), which is the shape to keep.

**Rework.**

1. Whether each piece stays is the code lists' call: APP-13 (root helpers), APP-14 (media tune file), APP-43 (store), HW-11
   (Boot Config engine), CAM-4 (TDN strip), REC-38 (placement of header-only classes), APP-42 (tests), APP-50
   (liblj92 README text).
2. For each survivor, its own commit in `commit-plan.md`, with a body paragraph "New in this fork: <what>; 1.6.0 has no
   counterpart; why it is worth it; how to remove it". `liblj92` gets `build: vendor liblj92 (MIT) for the clip viewer`
   apart from `/api/media/frame` (first-half new 32/33).
3. One table in the handoff, "New architecture", one row per survivor, with the same three facts.

**Owner decision.** None here; each keep-or-drop question sits in the code list named in step 1.

**Check here.** Every survivor's first commit has the "New in this fork" paragraph
(`git log --format=%B | grep -c 'New in this fork'` equals the handoff table's row count).

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** TXT-1, the code items in step 1.

---

## TXT-10. Developer-only knobs that stay have no home once the README table goes

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| docs | minor | S | yes | keep-and-document | X-knobs-15 (documentation side), X-knobs-9 (documentation side) |

**Where.** `Apertar-Core README.md:202-203, :303-310, :329, :333, :337-357@cinemate-port` (13-row env table, three sudo
install recipes, `Apertar-UI 7ea9afc (local branch clip-split)`, dated measurements, "test night", "NVMe campaign").

**Problem.** APP-18 removes the knob table and recipes from the README, and the knob items (CAM-9, REC-21, APP-9,
APP-15) cut 27 names. About 15 developer-only knobs stay (`sweep-knobs.md` section 12). Upstream documents its bench
knobs nowhere, so after the cut the survivors are known only from the code.

**Apertar way.** R8: a bench knob is `APERTAR_<AREA>_<KNOB>`, read at the point of use, its value printed in the existing
take-start line, and absent from `camera_settings.conf`, the hardware file, the socket API and the README
(`grep -c APERTAR_ README.md@upstream-1.6.0` = 0). STY-14: README tables stop at launch flags.

**Rework.**

1. Keep the README as APP-18 leaves it: operator features only, launch options (with `--allow-unmounted-media` from
   APP-23), no env names.
2. In the handoff, section "Bench knobs": one row per surviving knob: name, default, what it changes, where it is read
   (`file:function`), and the log line that prints it (R8 step 4). Fill it from the final code, not from the README.
3. Install steps for any helper that survives APP-13 go in the handoff "Image notes", not the README.

**Owner decision.** None.

**Check here.** `git grep -oh 'APERTAR_[A-Z0-9_]*' -- src scripts | sort -u` minus upstream's names equals the handoff
table's rows; `grep -c APERTAR_ README.md` is what APP-18's check allows.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** APP-18, CAM-9, REC-21, APP-9, APP-13, APP-15.

---

## What conforms (for the handoff)

| What | Evidence |
| --- | --- |
| No AI residue in code or text: no model names, apologies, emoji | `raw/sweep-slop.md` (c), regex over 42 600 added lines |
| No TODO, FIXME, commented-out code or debug prints in port-authored code (only in vendored `lj92.c`, kept as is) | `raw/sweep-slop.md` (d); STY-9 |
| No build warnings from port code (5 warnings, all `#if`-guarded upstream code) | `/home/user/build/core-port-build.log`, `core-port-lc-build.log` |
| Operator error replies keep upstream's length and shape (33 characters mean, one sentence) | `raw/sweep-slop.md` section E; STY-10 |
| Card copy and hints keep the imperative one-sentence tone (except the five long hints in WEB-34) | `raw/sweep-slop.md` section E |
| Most subjects use fork main's `area: what` form and a `Why:`/`What:` body | `git log origin/main..cinemate-port`; `631721d` |
| QML banners match upstream's habit (19 in upstream `CameraPage.qml`) | STY-8 note; `raw/sweep-slop.md` banners row |
| The eight UI preview experiments net to nothing, no leftover names | `git diff c234d77 c153c33` empty (`raw/sweep-commits-ui-drivers.md` 1.2) |
| `third_party/liblj92` is vendored with its licence and a provenance note naming the upstream commit | `third_party/liblj92/LICENSE`, `README.apertar.md` |
| Measured reasons exist for most write-path rules (they belong in commit bodies, not comments) | `raw/sweep-commits-core-1.md` new 9 |

## Findings not taken here, with the reason

| Finding | Reason |
| --- | --- |
| X-commits-ui-drivers-1, -4, -5, -6 (UI series, pairing), X-knobs-18 | Owned by UI-9 (touch UI list); TXT-1 step 1 only adds the pairing column |
| X-commits-ui-drivers-2 | Owned by UI-15; re-checked there: Core always sends `fps_max`, so the QML cap is a fallback only |
| X-commits-ui-drivers-3 | Owned by UI-16 |
| X-commits-ui-drivers-7, -8 (driver histories) | Owned by CAM-38. Add there: `050e2e3`, `289131a` authored "Your Name"; keep `4a1662e` with "oopsing" reworded |
| X-slop-8, X-slop-9 (driver comments and docs) | Owned by CAM-12 |
| X-slop-11 (`directIo`) | Code removal, owned by REC and CAM items (`directIo` in REC-21 / CAM-9 rows) |
| X-slop-12 (long hints) | Owned by WEB-34 |
| X-slop-13, Core README part | Owned by APP-18; driver part is TXT-8 |
| X-knobs-1 to -14, -16, -17, -19 | Code changes in the camera, recording, core-app and hardware lists |
| X-commits-core-1-7, claim "the fork's 8 earlier commits have no trailers" | Not real: 8 of 8 carry `Co-Authored-By` and `Why`/`What`/`Tested` (`git log 35dbe67..f60e301`); kept the rest in TXT-3 and TXT-6 |
| X-commits-ui-drivers-9, claim "`cinemate-7modes` is not a branch" | Not real: `remotes/origin/cinemate-7modes` exists; the finding stands otherwise (TXT-8) |
| X-slop-4, claim "CineMate Log reaches clip metadata" | Not confirmed: `describe()` is used only at `CC:4041` (journal); the template is the hardware file's, not `camera_settings.conf`. Finding kept for the journal and template (TXT-7) |
