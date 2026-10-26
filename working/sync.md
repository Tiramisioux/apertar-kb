# Keeping Mac, Pi and GitHub in sync

Set up 2026-10-25. Branch: `main` for Core and UI; `apertar` for the imx585 driver. One branch per repo, in every location.

## The three locations

| Location | Path | `origin` (push here) | `upstream` |
| --- | --- | --- | --- |
| GitHub | `Tiramisioux/Apertar-Core`, `Tiramisioux/Apertar-UI` | n/a (the meeting point) | n/a |
| Mac | `~/Documents/Apertar/Apertar-Core`, `…/Apertar-UI` | HTTPS, auth via `gh` keychain token | Apertar-Studio, push disabled |
| Pi | `~/ApertarCore`, `~/ApertarUI` | fetch HTTPS only. Push URL `NO-PUSH-from-pi-bring-commits-via-the-mac` | Apertar-Studio, push disabled |
| Driver (Mac `~/Documents/Apertar/imx585-v4l2-driver`, Pi `~/drivers/imx585-v4l2-driver`) | branch `apertar` | `Tiramisioux/imx585-v4l2-driver` (your Cinemate fork, shared) | Apertar-Studio + `will` (will127534), push disabled |

`upstream` push URL is the literal `NO-PUSH-use-origin`, so a mistaken `git push upstream` fails.

Git config in each repo, both machines: `pull.rebase=true`. A pull with local unpushed commits
replays them on top of GitHub, so `main` stays a straight line.

## The rule

GitHub is the exchange point. **Only the Mac pushes.** The Pi holds no GitHub credentials, because
distribution images are made from it (decided 2026-10-25).

Each Mac repo has a remote `pi` (`ssh://apertar/home/pi/<dir>`), fetch only (push URL
`NO-PUSH-to-pi-use-git-pull-on-the-pi`).

1. **Start of a work session, wherever you are:** `git pull`.
2. **Finish a change on the Mac:** commit, `git push`.
3. **Finish a change on the Pi:** commit on the Pi. Then on the Mac, one command:
   `~/.claude/skills/apertar-dev/scripts/apertar_publish.sh`. It pulls the Pi's commits into the Mac
   repo, pushes them to GitHub and fast-forwards the Pi (all three repos, fast-forward only; stops
   with instructions on a divergence; `--dry-run` to preview). This is the standard procedure.
4. **Before switching machine:** nothing uncommitted you need.

Uncommitted edits do not travel. Commit them, or keep working on the same machine.

> **2026-10-26:** code is committed on the Pi, then Pi → Mac → GitHub with `apertar_publish.sh`; Claude runs on the Mac and drives the Pi over ssh
> (`working/mac-driven-loop.md`). `apertar_push_to_pi.sh` (Mac → Pi) is only for a commit that starts on the Mac.

## Which machine to edit on

| Situation | Edit on | Why |
| --- | --- | --- |
| Anything you need to build or test | Pi, via VS Code Remote-SSH | Only the Pi can build (aarch64, Qt6 EGLFS, libcamera 0.7) |
| Reading, docs, planning, reviewing | Mac | Faster, Claude has the full local tree |
| Small edit you'll test later | Either; push, then pull on the Pi | |

## Check state

```bash
~/.claude/skills/apertar-dev/scripts/apertar_status.sh
```

Prints, per repo: GitHub tip, and for Mac and Pi `in sync` / `ahead N (push)` / `behind N (pull)` /
`DIVERGED (pull --rebase, then push)`, plus modified/untracked counts. Read-only.

## When things disagree

| Status says | Do |
| --- | --- |
| `ahead N` (mac) | `git push` |
| `ahead N` (pi) | on the Mac: `apertar_publish.sh` (or by hand: `git pull pi <branch>`, `git push`, then `git pull` on the Pi) |
| `behind N` | `git pull` |
| `DIVERGED` | on the Mac: `git pull`, `git pull pi <branch>`, fix any conflict, `git push`; then `git pull` on the Pi (it fast-forwards to the rebased commits only if the Pi had nothing else; otherwise `git pull` rebases there too) |
| push rejected `fetch first` | Someone (the other machine) pushed. Same as DIVERGED |
| modified files on the Pi you didn't mean to change | `git diff` first. Never `git checkout .` blind: the Pi may hold the only copy of a working fix |

## Known untracked files

| Where | Files | Status |
| --- | --- | --- |
| Pi `~/ApertarCore` | `src/prores/README.md`, `src/prores/ffmpeg/` (patch, build script, PROVENANCE) | Shipped on the 1.6.0 image, missing from upstream git. Candidate first commit (tutorial) |

## The KB on the Pi

Set up 2026-10-25 so Claude Code can run on the Pi (VS Code Remote-SSH) with the KB at hand.

| Side | Path | Remote |
| --- | --- | --- |
| Mac | `~/Documents/Apertar/apertar-kb` | `origin` = `Tiramisioux/apertar-kb` (**private**, since 2026-10-26); `pi` = `ssh://apertar/home/pi/apertar-kb` (fetch **and** push) |
| Pi | `~/apertar-kb` | none. `receive.denyCurrentBranch=updateInstead` |

No GitHub here, so the Mac pushes straight to the Pi. `updateInstead` updates the Pi's checked-out
files on push, and refuses if the Pi has uncommitted KB edits (commit them on the Pi first).

Sync, always from the Mac (either Claude, or `deploy_to_pi.sh` in the skill):

```bash
git -C ~/Documents/Apertar/apertar-kb pull pi main
git -C ~/Documents/Apertar/apertar-kb push pi main
```

Tutorials Claude writes on the Pi land in `~/apertar-kb/tutorials/inbox/` (no Obsidian there).
The Mac moves them into the vault after a sync (`tutorials/README.md`).

## History notes

- Upstream's UI repo commits its whole `build/` tree. The fork untracks it (`66d6d19`), so a Pi
  rebuild leaves `git status` clean.
- Web uploads lost executable bits and symlinks. Fixed from the Pi's real modes (`ed400ba`
  Core, `29ed99b` UI).
- `upstream-1.6.0` tag in each fork marks the Apertar-Studio commit the fork started from.
- Driver: the Pi's `imx585.c` was an uncommitted edit on the image (18 crop modes), in no published
  commit. Committed unchanged as `e5b74d3` on branch `apertar` (base will127534 `qbc-pisp-handler`
  `1644466`), pushed 2026-10-25. Apertar-Studio `main` has 4 commits on top of `1644466` that are not
  merged (`apertar_status.sh` reports them). The fork's `cinemate-*` branches belong to Cinemate.
