# Merge review of the cinemate port (campaign, started 2026-11-17)

Is `cinemate-port` ready to merge into Apertar `main`, and what has to change so the original developer reads it
as Apertar and not as a second code base inside it? This folder holds the review, its raw notes and its results.

Status: **paused on 2026-11-17 at Patrik's request.** `STATE.md` says where everything stands, what is pushed, what is saved
as patches, what the audit against his recorded decisions found, and how to resume. Read that page first.

## What Patrik asked for (2026-11-17)

| # | Request | Where it lands |
| --- | --- | --- |
| 1 | Review the port, say whether it is ready for merge into Apertar main | `REPORT.md` (verdict), `fix-list.md` |
| 2 | Reduce AI slop, make every commit clear | `raw/sweep-slop.md`, `raw/sweep-commits-*.md`, `commit-plan.md` |
| 3 | Keep the Apertar style and the original developer's intent, so further development is not spaghetti | `apertar-conventions.md` (the yardstick), `raw/rev-*.md` |
| 4 | A clear fix list | `fix-list.md` |
| 5 | A list of the features the port introduces | `feature-list.md` |
| 6 | What the original developer needs to know, architecture first | `developer-handoff.md` |
| 7 | Mismatches are to be re-implemented the Apertar way, not only reported. New architecture stays only where it was carefully considered | commits on the improvement branches, logged in `fix-list.md` |
| 8 | It worked on the CM5. Make sure it works on other Pi models | `raw/sweep-board-support.md`, fixes |
| 9 | Work in steps. First milestone: compatibility with the original Apertar design | this page, "Steps" |
| 10 | Use this KB and the Cinemate handbook (the "LLM manual", `Tiramisioux/cinemate-handbook`) | read by every agent |
| 11 | A separate investigation: why 12-bit Clear HDR shows strange output | `hdr12/REPORT.md` |
| 12 | Add all findings and rules for further development to this KB | `apertar-conventions.md`, then `llm/` and `architecture/` |
| 13 | Verify the coding map (`Tiramisioux/apertar-coding-map`) and bring it up to date with the port | `coding-map/`, a PR on that repo |
| 14 | The developer handoff carries a very short changelog: every feature, easy to read, with its relation to the original Apertar code and what it means for further development. Part of the final delivery | `developer-handoff.md`, section "Changelog in short" |
| 15 | A branch off the `cinemate-port` branches for the improvements | `claude/awesome-pasteur-qzsiow` in each code repo (cut from the `cinemate-port` heads) |
| 16 | Put the GPIO chip definition back: GPIO lines can sit on another chip, for example a microcontroller | fix on the Core improvement branch |
| 17 | Keep a log of all slop and bad solutions, how each is fixed and why, with brief code examples | `fix-log.md` |

## The branches

| Repo | Reviewed | Merge target | Improvement branch |
| --- | --- | --- | --- |
| Apertar-Core | `cinemate-port` `01f170c` (187 commits past `main`) | `main` `f60e301` = `upstream-1.6.0` + 8 | `claude/awesome-pasteur-qzsiow` |
| Apertar-UI | `cinemate-port` `7ea9afc` (39 commits past `main`) | `main` `4415a55` = `upstream-1.6.0` + 3 | `claude/awesome-pasteur-qzsiow` |
| imx585-v4l2-driver | `cinemate-port` `cd548ef` (55 past `apertar`) | `apertar` `e5b74d3` | `claude/awesome-pasteur-qzsiow` |
| imx283-v4l2-driver | `cinemate-port` `68b7dc9` (93 past `master`) | `master` | `claude/awesome-pasteur-qzsiow` |

Apertar-Studio `main` is still 1.6.0 (checked 2026-11-17: Core `35dbe67`, UI `43888e5`), so nothing upstream moved
under the port. `cinemate-port` and `main` are not touched by this campaign.

## Steps

| Step | Goal | State |
| --- | --- | --- |
| 1 | Compatibility with the original Apertar design: find every mismatch, rework it the Apertar way | running |
| 2 | Bugs found on the way, and compatibility with other Raspberry Pi models | findings collected in step 1, fixes after it |
| 3 | Slop out, comments in the original developer's style | after step 1 |
| 4 | A clear commit series | plan in step 1, the rewrite last (it follows the code changes) |
| 5 | Handoff: fix list, feature list, developer handoff with the short changelog, coding map | last |

## How the review is done

| Part | What | Output |
| --- | --- | --- |
| Conventions | Eight readers describe how original Apertar 1.6.0 is built, each challenged by a second reader | `apertar-conventions.md`, `raw/conv-*.md` |
| Unit review | 37 units cover every changed line: slices of the three giant files, the new file groups, the UI, the drivers. Each unit: inventory, review against the original, skeptic | `raw/inv-*.md`, `raw/rev-*.md` |
| Sweeps | Nine whole-port sweeps: knobs, board support, stock-behaviour changes, protocol and privileged surface, hand-copied state, slop, commit series (three) | `raw/sweep-*.md` |
| 12-bit Clear HDR | Nine readers, ranked hypotheses, a skeptic per hypothesis | `hdr12/` |
| Coding map | Six checkers and a recheck | `coding-map/verify-*.md` |

Shared brief for every agent: `BRIEF.md`.

## What can be verified without the camera

Checked in the review container (x86_64 Linux) on 2026-11-17, at `cinemate-port` heads:

| Check | Result |
| --- | --- |
| Core builds without libcamera (`-DAPERTARCORE_ENABLE_LIBCAMERA=OFF`, `-Wall -Wextra`) | **confirmed**: 39/39 targets, 5 warnings (unused function or parameter) |
| Core builds with libcamera (the Pi's fork `Tiramisioux/libcamera@apertar`, built here with the vc4 pipeline only: its PiSP pipeline needs ARM NEON) | **confirmed**: 39/39 targets |
| UI builds (Qt 6.4.2, QML compiled ahead of time) | **confirmed**: 167/167 targets |
| The port's 17 host tests (`tools/*_test.cpp`, `tools/*_test.sh`) | **confirmed**: 17 pass |
| Anything that needs a sensor, GPIO, the CFexpress hat, a recording drive, HDMI | **not possible here**: every such claim in this campaign is labelled, with the Pi command that settles it |

## Where the campaign stands (updated 2026-11-17, late in the first session)

| Part | State |
| --- | --- |
| Conventions (8 topics, each challenged) | done: `apertar-conventions.md` (audited), topic files in `raw/conv-*.md` |
| Unit review (37 units) and sweeps (9) | done: 598 verified findings (8 blockers, 133 major). `raw/FINDINGS.md` lists each in one line; `raw/FINDINGS.json` holds the full text |
| Fix list, feature list, owner decisions | domain lists done (`fix-list-core-app.md`, `-hardware.md`, `-camera.md`, `-recording.md`, `-webui.md`, `-touch-ui.md`, `-text-history.md`); the one-page `fix-list.md`, `feature-list.md` and `owner-decisions.md` are being written |
| 12-bit Clear HDR | done: `hdr12/REPORT.md`. Three confirmed defects fixed (fix log C11, C12, C14), the probable cause held back as an interim (C13) until a capture pair from the camera confirms it |
| Coding map | step 1 done: 50 corrections applied and re-checked (`coding-map/applied.md`), draft PR apertar-coding-map #1. Step 2 (what the port added) follows |
| Designs for the large reworks | eight pages in `design/`: each written, challenged against the code, and rewritten as a commit plan. Final: command-plane, boot-config-helpers, webui-state, touch-ui, hardware-inputs, camera-modes, preroll. In work: storage-settings |
| Fixes | on the improvement branches, one commit per fix, each logged in `fix-log.md`: Core C1 to C14, UI U1 to U3, imx283 driver D2-1. In work: bug fixes, command plane, hardware file and inputs, touch UI, camera modes |

Draft pull requests (all from `claude/awesome-pasteur-qzsiow`):

| Repo | PR | Base |
| --- | --- | --- |
| Apertar-Core | #7 | `cinemate-port` |
| Apertar-UI | #1 | `cinemate-port` |
| imx283-v4l2-driver | #1 | `cinemate-port` |
| apertar-coding-map | #1 | `main` |
| apertar-kb | #16 | `main` |

How a fix is made: a worker (Opus) implements one item in its own worktree and runs the gate (both Core builds, the host
tests, or the UI build); a second worker reviews the commit against the item and the conventions; the lead reads every
commit before it goes onto the improvement branch, runs the gate and the reply-shape comparison again, and writes or
corrects the fix-log entry. Two of the lead's corrections so far are themselves in the log (C8, C10).

Workers: Opus for reviews, skeptics, designs and implementation, Sonnet for inventories and mechanical sweeps (asked for
by Patrik, to save tokens). The scripts that drive the agents are not in this repo; the reports are.

## Results (filled in as they land)

| Page | Holds |
| --- | --- |
| `apertar-conventions.md` | The original developer's rules, with evidence. The yardstick, and the rule book for later work |
| `fix-list.md` | Every finding: severity, state (fixed with commit, open, deferred with reason) |
| `fix-log.md` | The running log of what was wrong and how it was fixed, with before/after code |
| `feature-list.md` | Every feature of the port |
| `developer-handoff.md` | For the original developer: architecture changes, the short changelog, what to know before merging |
| `commit-plan.md` | The clean commit series |
| `hdr12/REPORT.md` | 12-bit Clear HDR |
| `coding-map/` | What was wrong in the coding map, what was added |
| `design/` | One page per large rework: how the port does it, how original Apertar does that kind of thing, the target, the commit plan, decisions for the owner. `design/decisions-audit-summary.md`: the plans checked against Patrik's recorded decisions |
| `STATE.md` | Where the campaign stands at the pause, and how to resume |
| `owner-decisions.md` | The review's open questions to Patrik (to be redone after the audit: several are already answered by his recorded decisions) |
| `owner-recorded-decisions-a.md`, `-b.md` | Every decision Patrik recorded in this KB, collected with source lines (211 rows) |
| `lanes/` | Worker commits not yet on the improvement branch, as patches |
| `tools/` | The gate scripts and agent workflows of the review |
