# Merge review of the cinemate port: shared brief for every agent

Read this page first. It says what the campaign is, where everything lives in this container, and the rules.

## What this is

Patrik (Tiramisioux) ported Cinemate features into his forks of Apertar (branch `cinemate-port`). The port must
become mergeable into Apertar `main` and readable for Apertar's **original developer** (Apertar-Studio). Owner's
words: the changes must follow "the Apertar style and intentions of original developer so it is not perceived as
spaghetti, when we try to do further development". Where the port brought its own architecture into Apertar, the
mismatch is to be **re-implemented the Apertar way**, not just reported. New architecture stays only where it was
carefully considered and is worth it; then it is documented for the original developer.

Milestone 1 (now): compatibility with the original Apertar design. Later steps: bugs, Pi-model compatibility,
commit clarity, handoff documents.

## Where things are (this container, x86_64 Linux, not a Pi)

| What | Path | Ref |
| --- | --- | --- |
| Port, Core | `/home/user/wt/core-port` | `cinemate-port` `01f170c` (read-only checkout) |
| Port, UI | `/home/user/wt/ui-port` | `cinemate-port` `7ea9afc` (read-only checkout) |
| Port with the review's fixes, Core | `/home/user/wt/core-work` | branch `work/improve` = `claude/awesome-pasteur-qzsiow` on GitHub |
| Port with the review's fixes, UI | `/home/user/wt/ui-work` | branch `work/improve` = `claude/awesome-pasteur-qzsiow` on GitHub |
| Original developer's Core 1.6.0 | `/home/user/wt/core-upstream` | tag `upstream-1.6.0` `35dbe67` (= Apertar-Studio `main` today) |
| Original developer's UI 1.6.0 | `/home/user/wt/ui-upstream` | tag `upstream-1.6.0` `43888e5` (= Apertar-Studio `main` today) |
| Merge target, Core | `/home/user/wt/core-main` | fork `origin/main` `f60e301` = upstream 1.6.0 + 8 commits (Clear HDR set, sensor probe) |
| Merge target, UI | `/home/user/wt/ui-main` | fork `origin/main` `4415a55` = upstream 1.6.0 + 3 commits |
| imx585 driver | `/home/user/imx585-v4l2-driver` | HEAD = `cinemate-port` `cd548ef`; Apertar baseline `origin/apertar` `e5b74d3` |
| imx283 driver | `/home/user/imx283-v4l2-driver` | HEAD = `cinemate-port` `68b7dc9`; baseline `origin/master` |
| Knowledge base | `/home/user/apertar-kb` | start at `llm/README.md`, then `README.md` (routing table) |
| Cinemate | `/home/user/cinemate` | `main` `4990afc` |
| Cinemate handbook (the "LLM manual") | `/home/user/tiramisioux/cinemate-handbook` | `c99ff77` |
| cinepi-raw (Cinemate's recorder) | `/home/user/tiramisioux/cinepi-raw` | `63a08d5` |
| libcamera fork the Pi runs | `/home/user/tiramisioux/libcamera` | branch `apertar` `6b0b49f` |
| Coding map | `/home/user/apertar-coding-map` | `main` `bff7bd5`, one file `index.html` |
| This campaign's files | `/home/user/apertar-kb/working/merge-review/` | `raw/` holds agent reports |

The port diff: `git -C /home/user/wt/core-port diff --minimal origin/main cinemate-port -- <paths>` (187 commits,
about +40 600 / -8 200 lines; use `--minimal`, the default heuristic overstates deletions in `WebControlPage.cpp`).
UI: `git -C /home/user/wt/ui-port diff --minimal origin/main cinemate-port` (39 commits). Commit list:
`git -C <repo> log --reverse --format='%h %s' origin/main..cinemate-port`. One commit: `git -C <repo> show <sha>`.

## Vocabulary

| Word | Meaning |
| --- | --- |
| upstream, original Apertar, "the Apertar way" | Apertar-Studio 1.6.0 as in the `*-upstream` worktrees. The measuring stick |
| fork main | The merge target. Its commits on top of 1.6.0 are the contributor's earlier Clear HDR work |
| the port | Everything in `origin/main..cinemate-port` |
| Core | `apertar-core`, C++20: sensor, recording, socket `/tmp/apertar-core.sock`, WebUI on port 8000 |
| UI | `Apertar-UI`, Qt 6 / QML touch UI and HDMI monitor |
| WebUI | HTML/CSS/JS inside one C++ string, `Apertar-Core/src/web/WebControlPage.cpp` |
| `App`, `CC`, `WCP` | `src/ApertarCoreApp.cpp`, `src/camera/CameraController.cpp`, `src/web/WebControlPage.cpp` |
| T33, T47, Q21, R2, O10, WP-585-9 ... | Patrik's tutorial and work-package numbers. Internal. Meaningless to the original developer |

## Rules for agents

1. **Never read the giant files whole** (`ApertarCoreApp.cpp` 15 083 lines, `CameraController.cpp` 12 931,
   `WebControlPage.cpp` 20 963, `SettingsPage.qml`, `CameraPage.qml`). `grep -n` for an anchor, then read 60-200
   lines around it. The KB chapter maps (`llm/core-map.md`, `llm/ui-map.md`) give anchors; their line numbers are
   against `upstream-1.6.0`, so use them on the `*-upstream` worktrees and re-grep on the port.
2. **Evidence or it does not count.** Every claim carries `path:line` plus the ref it was read at
   (`@upstream-1.6.0`, `@main`, `@cinemate-port`). Quote the line when it matters. Label claims **confirmed**
   (read in code), **probable** (inferred, say why) or **unconfirmed** (say which command would settle it).
3. **Compare before judging.** A port pattern is a mismatch only if you can show how upstream does the same kind
   of thing differently (file:line in the `*-upstream` worktree). No upstream precedent at all = "new ground",
   which is a different category from "mismatch".
4. **Read-only unless your task says otherwise.** No edits to the code repos, no `git commit`, no `git checkout`
   of another ref in the shared checkouts, no `git stash`. To see another ref use `git show <ref>:<path>` or the
   worktrees above. Write only the report file your task names.
5. **Do not trust a commit message or a KB page as proof of behaviour.** They tell you intent. The code tells
   you what happens.
6. **This machine cannot run the camera.** No Pi, no sensor, no GPIO. What can be done here: Core compiles
   without libcamera (`/home/user/build/core-port`, `cmake -DAPERTARCORE_ENABLE_LIBCAMERA=OFF`), the UI compiles
   (`/home/user/build/ui-port`), the host tests in `Apertar-Core/tools/*_test.cpp` compile with plain `g++`.
   Do not start builds in the shared build directories unless your task says so.
7. **Write like the KB:** short sentences, tables over prose, no filler, no praise, no hedging words.
   Plain ASCII punctuation.

## What counts as "the Apertar way" (hints, verify in the upstream worktrees)

- One command entry point: `ApertarCoreApp::handleCommand`, a flat `if (command.name == "...")` chain under one
  mutex; replies via `okReply` / `errorReply`; flat JSON, every value a scalar.
- Each hardware class parses its own section of `apertar-hardware.conf` at start.
- Camera settings live in Core's `camera_settings.conf`; monitoring aids and UI preferences in `UI.conf`.
- The WebUI is one page in one C++ string; the touch UI talks to Core through C++ bridges with
  `Q_PROPERTY` / `Q_INVOKABLE`.
- Upstream Core has no unit tests and no `third_party/` tree (upstream UI has a `third_party/`). Check what
  privileged helpers and install steps upstream really has before calling a port helper "new".

These are starting points, not conclusions. The conventions study (`raw/conv-*.md`) is the reference once written.
