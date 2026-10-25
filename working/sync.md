# Keeping Mac, Pi and GitHub in sync

Set up 2026-10-25. Branch: `main` only, in every location.

## The three locations

| Location | Path | `origin` (push here) | `upstream` |
| --- | --- | --- | --- |
| GitHub | `Tiramisioux/Apertar-Core`, `Tiramisioux/Apertar-UI` | n/a (the meeting point) | n/a |
| Mac | `~/Documents/Apertar/Apertar-Core`, `…/Apertar-UI` | HTTPS, auth via `gh` keychain token | Apertar-Studio, push disabled |
| Pi | `~/ApertarCore`, `~/ApertarUI` | fetch HTTPS, push SSH (`~/.ssh/id_ed25519_github`) | Apertar-Studio, push disabled |

`upstream` push URL is the literal `NO-PUSH-use-origin`, so a mistaken `git push upstream` fails.

Git config in each repo, both machines: `pull.rebase=true`. A pull with local unpushed commits
replays them on top of GitHub, so `main` stays a straight line.

## The rule

GitHub is the exchange point. The Mac and the Pi never talk git to each other.

1. **Start of a work session, wherever you are:** `git pull`.
2. **Finish a change:** commit, then `git push`.
3. **Before switching machine:** nothing unpushed, nothing uncommitted you need.

Uncommitted edits do not travel. Commit them, or keep working on the same machine.

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
| `ahead N` | `git push` |
| `behind N` | `git pull` |
| `DIVERGED` | `git pull` (rebases your commits on GitHub's), fix any conflict, `git push` |
| push rejected `fetch first` | Someone (the other machine) pushed. Same as DIVERGED |
| modified files on the Pi you didn't mean to change | `git diff` first. Never `git checkout .` blind: the Pi may hold the only copy of a working fix |

## Known untracked files

| Where | Files | Status |
| --- | --- | --- |
| Pi `~/ApertarCore` | `src/prores/README.md`, `src/prores/ffmpeg/` (patch, build script, PROVENANCE) | Shipped on the 1.6.0 image, missing from upstream git. Candidate first commit (tutorial) |

## History notes

- Upstream's UI repo commits its whole `build/` tree. The fork untracks it (`66d6d19`), so a Pi
  rebuild leaves `git status` clean.
- Web uploads lost executable bits and symlinks. Fixed from the Pi's real modes (`ed400ba`
  Core, `29ed99b` UI).
- `upstream-1.6.0` tag in each fork marks the Apertar-Studio commit the fork started from.
