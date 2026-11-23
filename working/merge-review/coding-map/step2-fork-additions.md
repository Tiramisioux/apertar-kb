# Coding map step 2: what the fork adds (Core 4f1621a, UI 41da93a)

Map repo `/home/user/apertar-coding-map`, branch `claude/awesome-pasteur-qzsiow`, on top of `b533ceb`. Not pushed. Trees read: `/home/user/wt/core-now`, `/home/user/wt/core-upstream`.

| Commit | Subject |
| --- | --- |
| `c0a0652` | Fork-only boxes, arrows, tours and recipes |
| `b724878` | Dynamic resolution on the fork side: known limits and the fps tour |
| `f043bca` | Clip folder split and the merge worker on the fork side |
| `98b530f` | Dual sensor: the second Core on the fork side, linked to its page |
| `45bf630` | Boot Config card on the fork side: config.txt and the root helper |
| `f811adf` | Hardware config store and the Controls page: fork text on Hardware inputs |
| `7f85f92` | Two fork-only recipes: a Dynamic resolution lever, a hardware input class |

## Mechanism (c0a0652)
The page had only fork-only code lines and steps (`fork:true`). Added `forkOnly:true` on a node, edge, tour or recipe: hidden in official mode (`svg.official .forkonly`, tour button `hidden`, recipe row skipped), dashed box outline / pink label border and a "fork only" tag in the panel in fork mode; switching to official closes a fork-only pin, tour or recipe. Also `link:{href,text}` on a node (panel link). Legend line says a dashed box or arrow is not in official Apertar.

## New boxes (4 of 8 allowed)
| Box | Source | Fork pill (commits touching its files since upstream-1.6.0) |
| --- | --- | --- |
| Known limits (LIMITS) | `src/camera/SustainedFps.hpp` (row line :54 area, `kCells` :38; `capFor` :261) | 5 |
| Clip merge worker (MERGE) | `ApertarCoreApp.cpp:12586` runClipMerge, :12667 mergeSplitClip, :12684 `clipmerge::plan`; `src/cdng/ClipMerge.hpp`, `FramePath.hpp` | 2 |
| Second Core (cam1) (CORE2) | `config/apertar-core-cam1.service` (ExecCondition, socket, port 8001), `src/main.cpp:42,64,107` | 31 |
| config.txt (BOOTCFG) | `/boot/firmware/config.txt`; `ApertarCoreApp.cpp:3646` helper path, :3726-3728 sudo call, :3796-3967 card, :3905 `bootConfigSet`, :9765 `/api/boot-config`; `scripts/apertar-boot-config`, `config/apertar-boot-config.sudoers` | 7 |

The root helper is the text and path of the arrow HUB to config.txt, not a box (right side of the page was full).

## New arrows (all fork-only)
- d1 HUB to Camera `set_fps()`: `CameraController.cpp:11651` (`ladderRewriteLocked(requested)`), :11891 rewrite, `ModeLadder.hpp:318-366` (`tryOrder`, `chooseMode`).
- d2 Camera to Known limits: `CameraController.cpp:11876` (`capFor`), `SustainedFps.hpp:185` `limitFor`.
- d3 Camera to sensor "new mode": `CameraController.cpp:11718` (`applySettingsLocked(next, rung != nullptr, commit)`), log line :11705.
- m1 Merge worker to /media/RAW "renames": `ApertarCoreApp.cpp:12709-12745`, `ClipMerge.hpp` Plan.
- r1 HUB to Second Core "relay": `ApertarCoreApp.cpp:13510` `cam1ForwardAfter`, :13543; `ipc/CommandClasses.hpp:27-62`. r2 Second Core to HUB `get_state` 1 s: `ipc/ControlClient.cpp:27, 413`.
- b1 HUB to config.txt "sudo helper": `ApertarCoreApp.cpp:3726-3728`.

## Tours
- "Set 33 fps with Dynamic resolution on": TOUCH, c1, QML, BRIDGE, HUB, d1, CAM, d2, LIMITS, d3, SENSOR. Check of the claim: on NVMe at 33 fps the table gives 4K HDR16 cap 20, 2K HDR16 30, 4K HDR12 20, 4K SDR12 40 (step 33): picks 4K SDR12 lossless (`SustainedFps.hpp:38-60`, `stepDown` :153).
- "A long take on exFAT": SENSOR, i2, RECS, i3, DISK, MERGE, m1.

## Corrections to older fork text
- i3 (files arrow, fork text and code): the refresh pass said the split needs `frames_per_folder` set. Wrong since `2628040`: split defaults to on for every cDNG and lossy DNG take, 5000 frames per part (`util/BufferBudget.hpp:107, 331-364`), `split=auto` only on exFAT/FAT above 32 fps (`SustainedFps.hpp:167`), MLV never (`CameraController.cpp:4416-4431`). Official text kept in `up`.

## Existing boxes reused
- Hardware config store, Controls page, Listen: fork tip on Hardware inputs (HWIN). Store `src/hardware/HardwareConfigStore.hpp:1-5, 63-115`, atomic writes `HardwareConfigStore.cpp:379-399`, history `hardware-history` :422, `set_controls` `ApertarCoreApp.cpp:14034-14098`, `wakeControlsWorker` :14085, Listen `controls_last_input` :13952, `noteInputSeen` :13346, Controls page markup `web/WebControlPage.cpp:6894-6905`. No box: the right side had no room for a fifth box with a readable arrow.
- Dynamic resolution chooser: the existing Camera box.
- Link: `dual-sensor.html` from the Second Core panel and from the README ("Dual sensor startup"). The page itself was not edited.

## Recipes (fork-only rows, 8 rows in fork mode, 6 in official)
- r7 "Add a lever to Dynamic resolution's table": `ApertarCoreApp.cpp:12198-12199` (`refreshLadderContext`), `CameraController.cpp:11825-11827` (`limitContextLocked`), `SustainedFps.hpp:117, capFor`; `handleUiToggle` calls `refreshLadderContext` at :14675. The gyro lever and its 1 fps are invented, said so on the page.
- r8 "Add a new hardware input class": `HardwareConfigText.hpp:54-58` (`kSections`), `ControlsModel.hpp:345-346`, `ApertarCoreApp.cpp:8309-8311, 8702-8706, 13134-13141` (`hardwareGroupOf`).

## Checks
- `node /home/user/build/bin/check_map.js index.html core-now ui-now`: 195 lines, 60 hits. Baseline 38 (all artefacts, see refresh report). The 22 extra are all `[official]` hits on fork-only items (they do not exist in 1.6.0 and are hidden in official mode): N.LIMITS, E.d1-d3, N.MERGE, E.m1, N.CORE2, E.r1-r2, N.BOOTCFG, E.b1 and the context lines of r7/r8, which the script checks in both modes. A copy of the script that skips `forkOnly` items in official mode (scratchpad `check_map_fo.js`) gives exactly 38, the same hits as before. Original script untouched.
- Playwright, chromium, both modes, after every commit: 0 page errors, 0 console errors. Official: 17 boxes, 21 arrows, 5 tours, 6 recipes, 0 pills (unchanged). Fork: 21 boxes, 28 arrows, 7 tours, 8 recipes, 14 pills; every tour stepped to the end, every box/arrow clicked, every recipe hovered. Switching to official with a fork-only box, recipe or tour open resets cleanly.
