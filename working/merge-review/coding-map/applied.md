# Coding map corrections applied

Map commit `c9834a4` on `claude/awesome-pasteur-qzsiow` (`/home/user/apertar-coding-map`), on top of `bff7bd5`. Not pushed.
Sources: the "Final discrepancies" sections of the six `verify-*.md` files in this folder. Each item was re-read in both
trees (`/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream` @upstream-1.6.0; `/home/user/Apertar-Core` 01f170c,
`/home/user/Apertar-UI` 7ea9afc @cinemate-port) before the edit.

Checks after the edit: `node /home/user/build/bin/check_map.js` = 147 code lines, 36 hits, all path-format or pseudo-line
artefacts (multi-file `file` fields such as `SettingsBridge.hpp / .cpp`, the `…  copy zebra's` lines, the hardware conf and
exiftool lines that are not code); every flagged context line was found by grep in both trees. Playwright load, both modes:
11 boxes, 4 arrows, 5 tours, 6 recipe rows, mode switch, `#fork` hash: no page errors, no console errors.

One mechanism change: `render()` printed `what` as written, so an `up:{what}` override had no effect. It now reads
`val(it,"what")` like `code` and `tip`. Needed for E.i2 and E.i3.

## Nodes (verify-nodes.md)

| # | Item | What changed |
| --- | --- | --- |
| 1 | N.RENDER.tip | Both modes: the WebUI draws its own zebra, peaking, false colour, greyscale in a WebGL shader in WebControlPage.cpp; a change goes into both; LUT only here |
| 2 | N.DISK.tip | Fork: media gate before record_start (mediaGateError, /media/RAW, 1 GB floor). Official text kept in `up.tip` |
| 3 | N.WEBPAGE.tip | Fork: about 21k lines. Official 12k in `up.tip` |
| 4 | N.RECS.path | `src/camera/CameraController.cpp (DngRecordingQueue) + encoders in src/cdng/, src/lossydng/, src/mlv/, src/prores/, src/video/` |
| 5 | N.RECS.what | One encoder per format, each in its own folder; DngRecordingQueue runs the cDNG, lossy DNG and MLV workers |
| 6 | N.HWIN.up.tip | Official: three files hold the alias table, unlisted names pass through, behaviour is in handleSingleHardwareInputAction |
| 7 | N.HWIN.tip | Fork: "upstream has a copy in GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp" |
| 8 | N.HWIN.what | "Poll threads" -> "Input threads" (both modes) |
| 9 | N.BTN.what | "Core polls them" -> "Core reads them" (both modes) |
| 10 | N.BRIDGE.tip | Adds the 10 s timeout for reconfiguring commands |
| 11 | N.BRIDGE.code | Fork: adds `"Lock" → set_iso_auto enabled=false`. Old line kept as new `up.code` |
| 12 | N.HUB.what | "Every command that changes something runs under commandMutex_" |
| 13 | N.HUB.tip | Chapter map path: `~/apertar-kb/llm/core-map.md` in the knowledge base |
| 14 | N.CAM.what | fps normally control-only; reconfigure for resolution, bit depth, RAW <-> H.264/ProRes |
| 15 | N.CAM.tip | "about 25 ms after a change" |
| 16 | N.SENSOR.tip | Controls leave Core within one frame; picture change is up to libcamera and the sensor |
| 17 | N.PUB.tip | Adds: a socket client that stops reading is disconnected |
| 18 | Legend line 221 | Applied through the report's alternative: FORKDATA.SENSOR now counts the driver's `cinemate-port`, so the legend text "(branch cinemate-port)" is true and stays unchanged |

## Arrows and static text (verify-edges-cs.md, verify-edges-other-tours.md)

| # | Item | What changed |
| --- | --- | --- |
| F1 | E.c3.code | `"value":800` (a JSON number) |
| F2 | E.c3.tip | Flat parser keeps every value as text, so 800 and "800" both work; nested objects and arrays do not |
| F3 | E.s2.what | Adds: this request skips handleCommand, handleWebRequest calls buildWebStateJson |
| F4 | Static hint above the curl lines | "Core's parser is flat and keeps every value as text, so "800" and 800 both work." curl lines unchanged |
| 1 | E.i2.what | Fork: copy worker copies, gives the camera buffer back, queues. Official text in `up.what` |
| 2 | E.i3.what | Fork: adds "During an fps speed ramp frames are counted instead." Official text in `up.what` |

## Recipes (verify-recipes-a.md, verify-recipes-b.md)

| # | Item | What changed |
| --- | --- | --- |
| a1 | r1 QML note + diff | ActionTile under the full top Row (x/y from topControlsSideMargin, topControlsTopMargin, topStatHeight); note says the page has no QtQuick.Controls |
| a2 | r2 QML note + diff | Guarded `if (root.controlBridge)` block at the real indent, else branch removed; note: own dropdown key, drop displayValue/valueItalic, /4 -> /5 |
| a3 | r2 BRIDGE note + diff | Getter, signal, setter, member next to their iso twins, plus the setSharpness body |
| a4 | r2 CAM note + diff | Reader `loadPersistedCaptureSettings` (above the writer) with the iso context and a sharpness branch; "saving and loading it" |
| a5 | r3 WEBPAGE note + diff + up.diff | Badge and picker element; picker via buildOptionButtons with try/showToast. Official diff keeps its own isoBadge line (indent corrected to the real 6 spaces) |
| b1 | r6 example + CAM, RECS, DISK diffs | Artist (315) instead of ImageDescription (270), which Core already writes from the clip name |
| b2 | r6 RECS note | IfdBuilder sorts tags itself |
| b3 | r5 RENDER file + note + diff | Both .hpp/.cpp files; PreviewCacheState field, currentPreviewState copy, uniform, location, needsProcessing, glUniform1i |
| b4 | r5 UICONF note + diff | Adds the setter line that writes UI.conf; serializeCurrentSettings and presets in the note |
| b5 | r5 example + QML diff | "A new aid: invert the preview" (the centre cross exists in QML); names invertPreviewEnabled / uInvertPreview throughout |
| b6 | r4 up.forget | Aliases go into the three *Input.cpp files; the name itself only needs the hub |
| b7 | r4 HWIN up.note | "Upstream keeps the aliases in each input class ... A name with no aliases passes through as is." |

## Fork data, links, README (verify-forkdata-links.md)

| # | Item | What changed |
| --- | --- | --- |
| 1 | SRC.fork.foot Core SHA | f4a1393 -> 01f170c |
| 2 | SRC.fork.foot UI SHA | 7029db1 -> 7ea9afc |
| 3 | Fork footer driver link + README.md:27 | `tree/cinemate-port`, branch `cinemate-port` |
| 4 | FORKDATA.SENSOR | 50 commits over Studio main 70bdb26, newest five cd548ef..24172e6, branch cinemate-port |
| 5-13 | FORKDATA QML, BRIDGE, RENDER, UICONF, WEBPAGE, HWIN, HUB, CAM, RECS | Regenerated: 24/12/8/4/82/20/73/73/18, newest five per box, all on origin/cinemate-port (linked). `git rev-list --count --no-merges upstream-1.6.0..cinemate-port -- <paths>` and `git log --no-merges -5`; identical to the report's block |
| extra | srcNote (fork recipe intro), seen in passing by the forkdata recheck | "(Apertar-Core 01f170c, Apertar-UI 7ea9afc)" |

## Not applied

| Item | Why |
| --- | --- |
| E.c9.what "lands about one frame later" | Same imprecision as N.SENSOR.tip (D16) but not in any final list; left for the next pass |
| imx283 driver link (forkdata item 3, first checker) | Dropped by the recheck: fork growth, nothing false today. The later step that adds what the fork brought can add it |
| Official footer driver link (forkdata 14) | Dropped by the recheck: not false |
| TOURS.frame / TOURS.zebra steps | Dropped by the recheck: style, both destinations are lit |
