# Prompt for the Mac-side Claude: publish the Clear HDR UI commits

Written on the Pi 2026-10-25. Paste the block below into Claude Code on the Mac.

---

Publish two commits from the Pi to GitHub, one per repo, following the workspace contract (`~/.claude/skills/apertar-dev/references/workspace-contract.md`, "Sync contract"). Patrik asked for this.

**State on the Pi (checked 2026-10-25):** each repo is exactly one commit ahead of `origin/main`.

| Mac repo | Pi commit to publish | Already on GitHub |
| --- | --- | --- |
| `~/Documents/Apertar/Apertar-Core` | `9fa7918` web: add 4K Clear HDR as a resolution and 16-bit as a bit depth | `631721d`, `e1c10cd`, `57c8fb0` (Clear HDR core) |
| `~/Documents/Apertar/Apertar-UI` | `4415a55` ui: add 4K Clear HDR as a resolution and 16-bit as a bit depth | — |

**For each repo** (use `git -C <repo>`; `cd` does not persist):

1. `git -C <repo> status --short` must show no tracked changes. If it does, stop and ask Patrik.
2. `git -C <repo> fetch origin && git -C <repo> fetch pi`, then `git -C <repo> log --oneline origin/main..pi/main`. Expect exactly the one commit above. Anything else: stop and report.
3. `git -C <repo> pull pi main` (`pull.rebase=true`; a fast-forward is expected). If the Mac has local commits that are not on the Pi, report them before going on.
4. `git -C <repo> log --oneline origin/main..main` must list only that commit. Then `git -C <repo> push`.
5. Confirm: `git -C <repo> log --oneline -1 origin/main` shows the same sha as the Pi (`9fa7918` / `4415a55`). The sha must not change: no rebase onto other work, no amend.

**Then bring the Pi level** (a no-op fast-forward): `ssh apertar 'git -C ~/ApertarCore pull && git -C ~/ApertarUI pull'`, and check both report `main` up to date with `origin/main`.

**Knowledge base:** pull it from the Pi first (`git -C ~/Documents/Apertar/apertar-kb pull pi main`). In `working/handoff-clearhdr-buffering.md`, section "Housekeeping", replace the "Unpublished commits" line with "All Clear HDR commits are on GitHub (Core `631721d`, `e1c10cd`, `57c8fb0`, `9fa7918`; UI `4415a55`)." Commit (`kb: Clear HDR UI commits published`) and push to the Pi (`git -C ~/Documents/Apertar/apertar-kb push pi main`). The fork-log rows stay as they are (status `offer`).

**Do not:**
- squash, amend or rebase the already published commits, or force-push. That would rewrite public history on `Tiramisioux/Apertar-Core`; the contract forbids it. If Patrik wants a single squashed Clear HDR commit, that belongs in the upstream PR, not on `main`.
- push to `upstream` (Apertar-Studio).
- add the Pi's untracked `src/prores/README.md`, `src/prores/ffmpeg/`.

**Not in git, mention it in your reply:** `~/Tuning-Files/defaults-pisp/imx585_clearHDR.json` on the Pi. Every image needs it, or 16-bit Clear HDR records black.

Report back: the GitHub sha of each repo's `main`, and anything that did not go as described.
