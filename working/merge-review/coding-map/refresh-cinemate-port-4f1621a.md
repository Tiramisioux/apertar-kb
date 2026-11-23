# Coding map refresh to cinemate-port 4f1621a / 41da93a

Phase `refresh`. Map repo `/home/user/apertar-coding-map`, branch `claude/awesome-pasteur-qzsiow`, on top of `098602a`. Not pushed.
Trees read: Core `/home/user/wt/core-now` (4f1621a), UI `/home/user/wt/ui-now` (41da93a), official `/home/user/wt/core-upstream` (35dbe67), `/home/user/wt/ui-upstream` (43888e5). The map's fork side was last checked at Core 01f170c, UI 7ea9afc. Driver `/home/user/imx585-v4l2-driver` cinemate-port cd548ef (unchanged).
Note: the local branch `cinemate-port` in the Core and UI worktrees is stale (01f170c, 7ea9afc). The heads are `origin/cinemate-port` / HEAD. `git ls-remote origin cinemate-port` gives Core 4f1621a, UI 41da93a, driver cd548ef.

Commits:

| Commit | Subject |
| --- | --- |
| `1d47680` | Refresh fork code lines and tips against Core 4f1621a, UI 41da93a |
| `66be503` | FORKDATA: recount the fork against Core 4f1621a, UI 41da93a |
| `b533ceb` | README: the fork's second Core for cam1 |

(`66a4131`, "Dual sensor startup: a separate page", was committed in the same checkout by another session while I worked. It only adds `dual-sensor.html`; I did not touch it.)

## 1. Code lines and tips (`1d47680`)

Every fork value was read against core-now / ui-now: all node and arrow `path`, `code`, `what`, `tip` fields, the five tours, the six recipes (note, file, diff context). Official values were not changed; where a fork text changed, the old text stays in `up`.

### Changed

| # | Item | Was | Now | Source |
| --- | --- | --- | --- | --- |
| 1 | E.i2.code (fork) | `if (recordRawFrame(request, whiteBalance)) return;` (no longer in the tree) | `if (recordProcessedPreviewFrame(request) \|\| recordRawFrame(request, whiteBalance)) {` | `src/camera/CameraController.cpp:10050`; `recordRawFrame` at :10244 |
| 2 | E.i3.what, E.i3.code (fork) | only the flat clip folder | adds: with `[storage] frames_per_folder` set the frames go into `part_000`, `part_001` ... inside the clip folder and a merge worker flattens them while idle; second code line `cDNG_yy-mm-dd_C0001/part_000/<clip>_000000001.dng   // split on`. Official text and code kept in `up` | `src/cdng/FramePath.hpp:3-8, 74-76`; `CameraController.cpp:5214` (`framepath::framePath`), :4446 (`.parts` marker); default name unchanged: `src/util/ClipName.hpp:21-22` |
| 3 | N.HUB.what (fork) | one long function, every changing command under commandMutex_ | `handleCommand` takes `commandMutex_` and, with the Dual sensor switch on, also relays to the second Core (cam1); `handleCommandLocal` is the one long function with the if-branches. `code` (`if (command.name == "set_iso") {`) is now in `handleCommandLocal` | `src/ApertarCoreApp.cpp:13466` (handleCommand), :13469 (secondary gate), :13478 (lock), :13510 (`cam1ForwardAfter`), :13777 (handleCommandLocal), :14253 (`set_iso`) |
| 4 | N.CAM.what (fork) | fps normally control-only | adds: with Dynamic resolution on (the default) a new fps can also pick another sensor mode, between takes. The old Mode Ladder is not on the page, so nothing else to remove | `CameraController.cpp:11651` (`ladderRewriteLocked` in `setFps`), :11891-11893 (`recording_` returns false); `include/apertar/core/Types.hpp:210` (`dynresEnabled = true`) |
| 5 | N.BTN.what (fork) | PCF8574, NeoRotary4, GPIO buttons | adds GPIO encoders and two- and three-way switches, Grove knobs | `src/hardware/GpioInput.cpp:294` (`gpio_switches`), `src/hardware/GroveAnalogInput.hpp` |
| 6 | N.HWIN.what (fork) | all inputs make an action name | adds: a Grove knob skips the action name, `handleHardwareAnalogInput` sets the value (`set_iso`, `set_fps`, `set_wb` ...) itself | `ApertarCoreApp.cpp:10822`, :10848 |
| 7 | N.SENSOR.what (fork) | IMX585; modes come from the driver | IMX585 or IMX283; Core also keeps a table of the modes it offers and the startup probe keeps the rows the installed driver accepts | `src/camera/Imx585Modes.hpp:3-9`, `src/camera/Imx283Modes.hpp:1-3` |
| 8 | N.WEBPAGE.tip (fork) | about 21k lines | about 23k lines (23076; upstream 11618, its "about 12k" kept) | `src/web/WebControlPage.cpp` (`wc -l`) |
| 9 | N.DISK.tip (fork) | "less than 1 GB is free" | "1 GiB" (the floor is 1024 MiB, `APERTAR_MEDIA_MIN_FREE_MB` overrides) | `ApertarCoreApp.cpp:12136-12158` (`mediaGateError`, :12155) |
| 10 | E.c7.title (both modes) | "Dispatch on the poll thread" | "Dispatch on the input thread" (GPIO waits for edges; the earlier pass made the same change on HWIN.what) | `src/hardware/GpioInput.cpp:465-488`; `ApertarCoreApp.cpp:10799` |
| 11 | R2.forget (fork) | three state copies | adds: on a two-sensor camera the command also goes into `kBoth` in `src/ipc/CommandClasses.hpp`, or cam1 does not follow. Official text kept in `up.forget` | `src/ipc/CommandClasses.hpp:4-7, 27, 56-62, 322-327` (unlisted name = Primary, `planForward` sends only Both) |

### Checked and left as it is

- Code lines: all `N.*` and `E.*` code lines and every recipe context line are in core-now / ui-now. The ISO flow still holds: `ApertarControlBridge::applyIso` (`ApertarControlBridge.cpp:301`, "Lock" branch :304), `sendCoreCommand` (:1200; 3 s, 10 s reconfigure, 60 s `record_stop`, plus 8 s `calibrate_gyro`, not worth a mention), `setIso` emits `isoChanged` only on change (:2725), `settingsBody` (`ApertarCoreApp.cpp:312`), `settingsEvent` (`CameraController.cpp:166`), `buildWebStateJson` (:9877), `handleWebCommand` -> `handleCommand` (:8937), `handleWebRequest` skips handleCommand for `GET /api/state` (:9042). Three copies of the state still stand.
- Unchanged since 01f170c: `src/ipc/ControlServer.*`, `ControlProtocol.cpp` (flat parser, a stalled client is dropped).
- Dynamic resolution: `set_mode_ladder` takes `modes` (old name `resolutions`), `enable_mode`, `disable_mode`, `enabled`, `aspects`, `tdn`, `dry_run` (`ApertarCoreApp.cpp:15536-15553`). The page names neither the Mode Ladder nor these fields, so no value needed correcting there. Same for resolution labels, the timecode `target`, and Boot Config through `/api/command`: none of them is on the page today (grep `ladder|timecode|boot` in index.html finds nothing). They belong to the later phases.
- Hardware conf (`[neorotary4]`, `encoder0_cw`), `ActionCatalog.hpp` rows (`{"iso_up", "ISO", "ISO up", ...}` at :39), `handleSingleHardwareInputAction`, `pcfSettingStepMode`, controls worker (`ApertarCoreApp.cpp:8738`, :13193) all hold. Recipe r4's new row uses group "Image", which the catalog does not have today; groups are free text there, so the example stays.
- `N.PUB` (`broadcastWithFds`, :16547), `N.UICONF`, `f2` (`handleUiToggle` -> `updateSharedUiGeneralSettings`, :14663, :2377), `f1`/`f3` (`SettingsBridge.cpp:324, 420, 509, 686`), i4 events (`publishPreviewFrame`, :16496), i6 (640x360, quality 75, :93-96) hold.

### check_map.js

`node /home/user/build/bin/check_map.js /home/user/apertar-coding-map/index.html /home/user/wt/core-now /home/user/wt/ui-now`: 149 lines checked, **38 hits** (baseline before my edits: 39; the one that went away is the real stale line, item 1). Every remaining hit is a checker artefact, as in `applied.md`, and I re-grepped each in both trees:

- `N.PUB` (fork and official): the path field `src/ApertarCoreApp.cpp (publishPreviewFrame, streamMjpeg)` is split at the comma. The line is at `ApertarCoreApp.cpp:16547` (fork) and `core-upstream ApertarCoreApp.cpp:10940`.
- `E.f1` (`zebraEnabled=true`, an INI line) and `E.f3` (`QFileSystemWatcher::fileChanged → pollExternalSettings()`, a pseudo line): not code. Names are at `SettingsBridge.cpp:324, 420, 509` in both trees.
- `RECIPES.r4.steps[0]` (hardware conf lines): the file is not in a source tree. Keys parsed at `NeoRotary4Input.cpp:310-335`.
- `RECIPES.r5.steps[1]` and `[2]`, `RECIPES.r6.steps[1]` (multi-file `A.hpp / .cpp` path fields): each flagged line was found by grep in the `.cpp` of both trees (`SettingsBridge.cpp:324, 527, 686`; `PreviewWindowRenderer.cpp:1123, 2077`; `CdngEncoder.cpp:1679-1680` fork, :1559-1560 upstream) plus the `... getter, signal, member` pseudo line.
- `RECIPES.r6.steps[2]` (`exiftool ...`): a shell line.

Playwright (chromium, file:// page, fonts stubbed), both modes, official and `#fork`: 17 boxes, 21 arrows, 5 tours stepped to the end (43 steps), 6 recipe rows hovered, every box clicked. Page errors 0, console errors 0. Fork mode shows 10 fork pills, official 0.

## 2. FORKDATA (`66be503`)

Rule as in `verify-forkdata-links.md`: `git rev-list --count --no-merges upstream-1.6.0..origin/cinemate-port -- <paths>` and `git log --no-merges -5` with the same path sets (QML `qml`; BRIDGE `src/ApertarControlBridge.{cpp,hpp}`; RENDER `src/PreviewWindowRenderer.{cpp,hpp}`; UICONF `src/SettingsBridge.{cpp,hpp}`; WEBPAGE `src/web`; HWIN `src/hardware`; HUB `src/ApertarCoreApp.{cpp,hpp}`; CAM `src/camera src/util`; RECS `src/cdng src/mlv src/prores src/video src/lossydng src/audio`). Driver: `70bdb26..cinemate-port`, no path filter.

| Box | Was | Now | Newest |
| --- | --- | --- | --- |
| QML | 24 | 48 | 620b01d |
| BRIDGE | 12 | 25 | 620b01d |
| RENDER | 8 | 11 | 9453ea5 |
| UICONF | 4 | 10 | dba1995 |
| WEBPAGE | 82 | 156 | 17fc6f7 |
| HWIN | 20 | 40 | 2628040 |
| HUB | 73 | 146 | ef2d304 |
| CAM | 73 | 128 | 8842cea |
| RECS | 18 | 23 | 7962744 |
| SENSOR (driver) | 50 | 50 | cd548ef |

All 43 distinct (repo, hash) pairs are ancestors of `origin/cinemate-port` of their repo, and the heads match `git ls-remote` on GitHub. All links stay `true` (GitHub). Compare links unchanged (`main...Tiramisioux:<repo>:cinemate-port`).
Same commit hash shows in several boxes where one commit touches several paths (for example `2628040` in HWIN, HUB, CAM); that is how the earlier counts worked too.
Also in this commit: the fork footer SHAs (`01f170c` -> `4f1621a`, `7ea9afc` -> `41da93a`) and the example note in `srcNote()` (`index.html`, same two SHAs). No old SHA is left in the page.

## 3. README (`b533ceb`)

Nothing it says about the fork is false: branch names, driver branch, `#fork`, the fork tags and the compare link all still hold, and it names no commit. One line added: a fork camera with two sensors also runs a second Core for cam1, the map follows the first one. Source: `config/apertar-core-cam1.service` (ExecCondition `apertar-core --camera cam1 --check-dual`, own socket `/tmp/apertar-core-cam1.sock`, port 8001), `src/main.cpp:42, 64`.

## For the lead

- The commit trailer follows COMMON.md (`Claude Opus 5.5`), not the harness reminder's model name.
- The Mode Ladder, resolution labels, timecode target and Boot Config route are not on the page; nothing was removed for them. If they should appear, that is a box/arrow/tour decision for a later phase (the `dual-sensor.html` page from the other session suggests the dual sensor part is already handled there).
- The static line under "Try 3 and 6" (`cmake --build ... then restart that service`) does not mention that cam1 has its own service (`apertar-core-cam1.service` has no `PartOf=`, so a Core restart leaves cam1 on old code). Left alone: the line is the same in both modes and the page has no per-mode static text. Say if you want it.
