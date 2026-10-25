# Fork log: Tiramisioux forks vs Apertar-Studio

How my forks differ from Apertar-Studio, and what has gone upstream. One row per fork commit.
For talking to the maintainer: each row points at a commit on GitHub (`Tiramisioux/<repo>`).

Kept current by the `apertar-dev` skill, on the Mac and on the Pi, in the same session as the
commit, PR or upstream release. Check: `scripts/fork_log_check.sh` (skill folder).

**Status:** `fork-only` (stays in the fork) · `offer` (worth a PR or issue) · `PR <link>` ·
`upstream <version>` (landed: move the row to "Landed upstream") · `dropped`.
`#N` = row N in `lessons/upstream-issues.md`.

## Apertar-Core · base `upstream-1.6.0` (`35dbe67`)

| Commit | Change | Status |
| --- | --- | --- |
| `65ccfa8` | `.gitignore` for build dirs and editor state | fork-only |
| `ed400ba` | Executable bit back on `scripts/start-apertar-core.sh` (lost in the web upload, #6) | offer |

## Apertar-UI · base `upstream-1.6.0` (`43888e5`)

| Commit | Change | Status |
| --- | --- | --- |
| `66d6d19` | Stop tracking the committed `build/` tree (551 files, 18 MB, #5) | offer |
| `29ed99b` | Executable bits and `mesa-minimal` symlinks restored (#6) | offer |

## imx585-v4l2-driver · branch `apertar` · base will127534 `qbc-pisp-handler` (`1644466`)

| Commit | Change | Status |
| --- | --- | --- |
| `e5b74d3` | 18 aspect-ratio crop modes, exactly as shipped on the 1.6.0 image, which is in no published commit (#12) | offer |

Not taken: Apertar-Studio `main` is 4 commits past the base (`3680bf4`, `c0f5404`, `11178c8`,
`70bdb26`: format hardening, HMAX table, RAW10 4K, CCMP Clear HDR gate).

## Not in any commit

| What | Where | Status |
| --- | --- | --- |
| `src/prores/README.md`, `src/prores/ffmpeg/` ship on the 1.6.0 image but are missing from upstream git (#7) | Pi `~/ApertarCore`, untracked | offer (issue) |

## Pull requests

None yet (checked 2026-10-25: `gh pr list --repo Apertar-Studio/<repo> --author Tiramisioux --state all`).

## Landed upstream

None yet.
