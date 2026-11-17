# Inventory WCP-01: WebControlPage.cpp, CSS slice 1 (port lines 22-1879)

Stage 1 of 3: inventory. Facts only, no verdicts. Written 2026-11-17.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/WCP.part01.diff`: 1012 lines, 7 hunks, read whole |
| Port file | `/home/user/Apertar-Core/src/web/WebControlPage.cpp` @cinemate-port `01f170c`, lines 22-1879. Working tree = `cinemate-port` for this file (`git diff cinemate-port` empty) |
| Original | `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0 `35dbe67`, lines 22-1022 |
| Merge target | `/home/user/wt/core-main/src/web/WebControlPage.cpp` @main `f60e301`: lines 1-1100 byte-identical to upstream (`diff` of the two ranges: exit 0). Every `U:` line below holds @main too |
| Content | CSS only. The `<style>` block is U:15-2420 and P:15-4393. The slice holds no HTML, no JavaScript, no C++ |
| Size | +858 / -1 lines. Upstream CSS: 2406 lines. Port CSS: 4379 lines |
| Page shape | Still one raw string literal: `R"APERTAR(` P:7 to `)APERTAR"` P:20959 (upstream U:7 to U:11614). confirmed |
| Shorthand | `P:n` = port file line @cinemate-port. `U:n` = upstream file line @upstream-1.6.0 (= @main). `App:n` = `src/ApertarCoreApp.cpp` @cinemate-port |
| Labels | confirmed = read in code. probable = inferred, reason given. unconfirmed = not settled here, command given |
| Not done | No browser run. How a rule looks on screen is unconfirmed. Settle: start Core with `--simulate`, open port 8000 in headless Chrome, screenshot |

Blame command used: `git -C /home/user/Apertar-Core blame -s -L 22,1880 origin/main..cinemate-port -- src/web/WebControlPage.cpp`.
18 port commits wrote the 858 lines (section 12).

## 1. The seven hunks

| # | Old (U) | New (P) | Lines | What | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | 22-43 | 22-46 | +3 | `:root` gets `--info`, `--select-bg`, `--select-fg` | `d44b177` |
| 2 | 56-76 | 59-79 | +1 -1 | `body.media-browser-open` becomes `body.pb-open` | `bc12c0a` |
| 3 | 160-179 | 163-215 | +33 | `.status-pill` gets a fill bar (`buffer-bar`, `buffer-drain`) | `d44b177` |
| 4 | 184-203 | 220-249 | +10 | `.status-pill.preroll`, `.status-dot.preroll` (blue) | `d44b177` |
| 5 | 527-546 | 573-606 | +14 | `.plain-timecode` override, `.preview-stage.recording-frame::after` | `f4fb084` |
| 6 | 780-799 | 840-1600 | +741 | `.system-value`, Mode Ladder family, Value Lists chips, Clip names composer | 15 commits, section 12 |
| 7 | 1003-1022 | 1804-1879 | +56 | `.settings-search` and the search-state rules | `d44b177` |

Lines per topic: root variables 3, scroll lock 1, buffer bar 33, pre-roll 10, recording frame and timecode 14,
system value 9, Mode Ladder 539 (P:859-1397), Value Lists 57 (P:1398-1454), Clip names 136 (P:1455-1590), search 56. Sum 858.

## 2. Features that touch this slice

All rows confirmed in code unless marked. "Tested" quotes the commit message and `/home/user/apertar-kb/fork-log.md` (intent, not proof).

| # | Feature | Operator gets | CSS here | Commits | Relation to upstream | Tested, per message and fork-log |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Write-buffer bar in the status pill | A red bar inside the REC pill shows how full the write buffer is. After a buffer safety stop the pill shows only a green bar that empties | P:173-204 | `d44b177` | Extends upstream `.status-pill` (U:155-168) in place | Message: host tests on the Mac, `node --check`; "Not run yet: the ram queue, the safety stop, the buttons"; "nothing opened in ... a browser". KB `working/drop-frames/README.md:101`: a real safety stop measured on the camera 2026-11-01; README:99: the green READY pill "read from code". Fork-log:138 |
| F2 | Storage pre-roll pill | The status pill and dot turn blue and read PRE-ROLL while a storage pre-roll runs | P:32, 230-238 | `d44b177` | Extends upstream status pill and dot states (U:176-192) in place | Message: "Not compiled or run yet: the pre-roll". KB README:127-131: pre-roll measured on the camera 2026-11-01 (Core result). The blue pill itself: no record of a browser check. Fork-log:138 |
| F3 | Recording frame, red timecode switch | A red border around the preview during a take (switch, default off). The take timecode can stay white (switch, default red) | P:583-595 | `f4fb084` | Extends upstream `.time-card` (U:520-535) and `.preview-stage` (U:263-269) in place | Message: "desk only (built on the Pi next)". Fork-log:81: "tested 2026-10-28 (Patrik)" |
| F4 | System-decided values in italics | A value the camera set by itself (held for Clear HDR, an added ceiling, a flicker-free angle, a ramp angle, the pre-roll fps) is shown in italics | P:850-857 | `e58e7e5`, `ff33d2d`, `15bba86`, `d44b177` | Extends upstream `.badge` (U:443), `.pill-button` (U:763), `.settings-summary-value` (U:1486) in place | Messages: "desk only (node --check)". Fork-log:83, 88: "built 2026-10-28" |
| F5 | Mode Ladder editor, Activated sensor modes, Speed Ramp card head, ladder cues in Camera settings | Cards to build a resolution ladder (rows, max fps between rows, compression, crop thumbnails, sensor modes in collapsible groups). FPS pills name the resolution they switch to. Locked Resolution, Crop and Bit Depth pills turn grey. A ladder line and pill link to the card | P:859-1397 | `920beb0`, `1ef94fe`, `65e049e`, `e472b1b`, `d93a7e3`, `af22759`, `da8ca9f`, `b21c76a`, `392e812`, `5dfbc6c`, `6707b08` | New area (`ladder-*`, `crop-*`) plus in-place modifiers on upstream `.pill-button`, `.pill-grid`, `.online-pill`, `.settings-card-head` | `920beb0`: fork-log:94 "built 2026-10-28, not tested". The rest: fork-log:97 "desk-tested, Pi check pending" (headless Chrome against the Pi's Core). `6707b08`: "desk only (node --check)" |
| F6 | Value Lists card | Chips for the ISO, shutter angle, FPS and WB lists. An x removes a value. Camera-added flicker-free angles are greyed, italic and not removable | P:1398-1453 | `ff33d2d`, `d44b177` | New area (`value-*`) | `ff33d2d`: "desk only (node --check)"; fork-log:77 "tested 2026-10-28 (Patrik)". The `d44b177` lines: no separate record |
| F7 | Clip names composer | Drag pills (tokens, separators, free text) into a row to build the clip name. Presets, a live example, an ok or error line | P:1455-1589 | `014a2bf` | New area (`clip-*`) | Message: no "Tested:" line. KB `working/drop-frames/README.md:102`: Core "read from code", host test `tools/clip_name_test.cpp`, "WebUI composer and touch card untested by hand" |
| F8 | Settings search | A search box in the Settings sidebar. While it holds text every panel shows and only matching cards stay | P:1814-1868 | `d44b177` | New area (`settings-search*`, `.search-hidden`); overrides upstream `.settings-panel` display (U:1111-1120) while searching | Message: `node --check`; "nothing opened in ... a browser". Fork-log:138 |
| F9 | Clip Browser scroll lock | Page scroll is locked while the Clip Browser (playback overlay) is open | P:69 | `bc12c0a` | Replaces upstream class `media-browser-open` (U:66) | Message: "desk (headless Chrome against the Pi's Core, read-only)". Fork-log:101 |
| F10 | White GPIO and hardware dropdowns (variables only) | Dropdowns on the Controls panel and in the Hardware card are white with dark text | P:35-36 (the rules that use them: P:3484-3520, part 02) | `d44b177` | Extends upstream `:root` (U:16-42) in place | Message: "Not run yet: ... the Controls page". Fork-log:138 |

## 3. Rule table

"Carried by" = the element or script line that sets the class (@cinemate-port). "none" = no element at HEAD (section 7).

### 3a. Root, body, status pill, take cues

| P lines | Selector, content | Commits | Carried by |
| --- | --- | --- | --- |
| 32 | `--info: #38bdf8` | `d44b177` | Used P:232-233, 237 (pre-roll), P:1468, 1518 (clip composer drop markers) |
| 35-36 | `--select-bg: #ffffff`, `--select-fg: #18181b` | `d44b177` | Used P:3488-3489, 3499-3500 only (outside the slice) |
| 68-71 | `body.settings-open, body.pb-open { overflow: hidden }` | `bc12c0a` (line 69) | `document.body` P:10120 |
| 173-176 | `.status-pill { position: relative; overflow: hidden }` | `d44b177` | `div.status-pill` P:4415 (upstream element U:2442). Applies in every state |
| 178-189 | `.status-pill.buffer-bar:not(.buffer-drain)::before, .status-pill.buffer-drain::before`: bar from the left, `width: var(--buffer-fill, 0%)`, `background: var(--danger)`, opacity 0.8, 0.15 s | `d44b177` | Classes P:16478, 16551. Property P:16526, 16584 |
| 191-194 | `.status-pill.buffer-bar > * { position: relative; z-index: 1 }` | `d44b177` | `#statusDot`, `#recordingStatus` P:4416-4417 |
| 196-204 | `.status-pill.buffer-drain::before { background: var(--ok) }`, `.status-pill.buffer-drain > * { visibility: hidden }` | `d44b177` | P:16476-16478 |
| 230-238 | `.status-pill.preroll { border-color, color: var(--info) }`, `.status-dot.preroll { color: var(--info) }` | `d44b177` | P:15760-15761, 16448-16450 |
| 583-585 | `.time-card.recording.plain-timecode .timecode-value { color: #ffffff }` | `f4fb084` | `#timecodeBlock` P:4494, set P:16135 |
| 587-595 | `.preview-stage.recording-frame::after`: `inset: 0`, `border: 4px solid #ff4d4d`, `z-index: 6`, no pointer events | `f4fb084` | `#previewStage` P:4432, set P:16134 |
| 850-857 | `.badge.system-value, .settings-summary-value.system-value, .pill-button.system-value { font-style: italic }` | `e58e7e5` 4, `ff33d2d` 2, `15bba86` 1, `d44b177` 1 (line 854) | P:8700, 8704, 8711, 15039, 15403, 15407 |

### 3b. Mode Ladder family (P:859-1397)

| P lines | Selector | Commits | Carried by |
| --- | --- | --- | --- |
| 859-866 | `.switch-field` | `1ef94fe`, `920beb0` | Speed Ramp card head P:4987. One use |
| 868-876 | `.settings-card-head.wrap-head`, `> div:first-child` | `1ef94fe`, `920beb0` | Speed Ramp card P:4981. One use |
| 878-881 | `.online-pill.off` (grey) | `1ef94fe` | `#settingsModeLadderValue` P:5169, set P:8410 |
| 883-910 | `.ladder-box`, `.ladder-box-text`, `.ladder-box-title`, `.ladder-now` | `1ef94fe`, `920beb0` | Mode Ladder card P:5171-5185 |
| 912-957 | `.crop-frame` 78x44, `.large` 160x90, `.small` 64x36; `.crop-window`, `.whole`; `.crop-tag` | `1ef94fe`, `6707b08` (the three sizes) | P:5184, 8133, 8347. Filled by `fillCropFrame` P:7926-7938 |
| 959-981 | `.ladder-list-head`, `.ladder-list`, `.ladder-list.off .ladder-row`, `.ladder-item` | `1ef94fe`, `b21c76a` 1 | P:5192-5196, 8128, 8437 |
| 983-1015 | `.ladder-transition`, `.ladder-fps-input`, `.problem`, `.ladder-fps-unit`, `svg` | `1ef94fe`, `65e049e`, `e472b1b` | P:8194-8210 |
| 1017-1026 | `.ladder-row` | `1ef94fe`, `920beb0` | P:8130 |
| 1028-1034 | `.ladder-row.dragging`, `.ladder-row.drop-target` | `920beb0`, `1ef94fe` | none |
| 1036-1043 | `.ladder-row-main` | `1ef94fe`, `920beb0` | P:8131 |
| 1045-1055 | `.ladder-handle` | `1ef94fe`, `920beb0` | none |
| 1057-1069 | `.ladder-badge` (green disc `#4ade80` with the row number) | `1ef94fe`, `920beb0` | P:8132 |
| 1071-1101 | `.ladder-row-text`, `-name`, `-meta`, `-desc`, `-desc.crop-in`, `-range`, `.ladder-problem` | `1ef94fe`, `920beb0` | P:8136-8147, 5188 |
| 1103-1129 | `.ladder-row-controls` and inside it `.field-stack`, `.input-label`, `.settings-input`, `.settings-select`, `.settings-input.problem` | `1ef94fe`, `920beb0` | P:8151-8156. The row holds a select only: the two `.settings-input` selectors match nothing |
| 1131-1134 | `.ladder-thr` | `1ef94fe` | none |
| 1136-1154 | `.ladder-comp`, `.ladder-note`, `.ladder-note.over`, `.ladder-size` | `1ef94fe` | P:8152, 8174-8185, 5194 |
| 1156-1182 | `.ladder-row-buttons`, `.ladder-icon-button`, `.remove`, `:disabled` | `1ef94fe`, `920beb0` | none (`createLadderIconButton` P:8106-8114 has no caller) |
| 1184-1186 | `.pill-grid.ladder-pair` (2 columns of 88px) | `1ef94fe` | Speed Ramp P:4989, Mode Ladder P:5176, Timecode card P:5089 and 5093 (commit `909aaa5`) |
| 1188-1190 | `.pill-grid.ladder-aspects` | `da8ca9f`, `1ef94fe` | P:5159 |
| 1192-1229 | `.ladder-groups`, `.ladder-group-head`, its `svg`, `[aria-expanded="true"] svg`, `.ladder-group-count` | `1ef94fe`, `920beb0` | P:5160, 8304-8310 |
| 1231-1273 | `.ladder-pool`, `.ladder-pool-item`, `.inactive`, `-text`, `-name`, `-why`, `-meta` | `1ef94fe`, `d93a7e3`, `af22759` | P:8317, 8346-8356 |
| 1275-1292, 1308-1312 | `.ladder-add`, `:disabled`, `.remove` | `1ef94fe`, `af22759` | P:8361, 8370 |
| 1294-1299 | `.ladder-pool-actions` | `af22759` | P:8360 |
| 1301-1306 | `.ladder-pool-number` | `af22759` | none |
| 1314-1319 | `.ladder-add.on-ladder` | `1ef94fe` | none |
| 1321-1323 | `.section-head .online-pill { margin-left: auto }` | `1ef94fe` | `#quickLadderPill` P:4512. No other `.online-pill` sits in a `.section-head`, in the port or upstream |
| 1325-1342 | `.select-note`, `.switching`, `.ladder-on` | `1ef94fe` | `#fpsLadderLine` P:4519; `.switching` P:15921; `.ladder-on` none |
| 1344-1362 | `.pill-sub`, `.pill-button.active .pill-sub`, `.pill-button.ladder-switch`, `.ladder-switch .pill-sub` | `1ef94fe`, `920beb0` | FPS pills P:15910-15914 |
| 1364-1369 | `.pill-grid.ladder-locked .pill-button.active` (grey) | `392e812`, `1ef94fe` | P:11166, 15933-15935 |
| 1371-1380 | `@media (max-width: 560px)`: `.ladder-comp`, `.ladder-transition` | `1ef94fe` | |
| 1382-1396 | `.ladder-line`, `.select-note.ladder-line:hover`, `.ladder-link` | `5dfbc6c`, `1ef94fe`, `920beb0` | P:4512, 4519, 7985 |

### 3c. Value Lists, Clip names, search

| P lines | Selector | Commits | Carried by |
| --- | --- | --- | --- |
| 1398-1408 | `.value-list-row`, `:last-child` | `ff33d2d`, `d44b177` | P:8520 |
| 1410-1426 | `.value-chip-row`, `.value-chip` | `ff33d2d` | P:8527, 8538 |
| 1428-1437 | `.value-chip.flicker-free` (opacity 0.5, italic), `.value-chip-note` | `d44b177` | P:8538, 8562 |
| 1439-1453 | `.value-chip button`, `:hover` | `ff33d2d` | P:8545-8557 |
| 1455-1474 | `.clip-row`, `.drop-end`, `.clip-row-hint` | `014a2bf` | P:4948, 14659, 14977 |
| 1476-1519 | `.clip-pill`, `.token`, `.text`, `.sep`, `.dragging`, `.drop-before` | `014a2bf` | P:14657-14658, 14729, 14803 |
| 1521-1546 | `.clip-pill .clip-x`, `:hover`, `.clip-pill input` | `014a2bf` | P:14770 |
| 1548-1556 | `.clip-ghost` (`position: fixed`, `z-index: 9999`) | `014a2bf` | P:14726 |
| 1558-1570 | `.clip-palette-group`, `.clip-palette-title` | `014a2bf` | P:14986-14988 |
| 1572-1575 | `.settings-card.locked .clip-pill` | `014a2bf` | P:14957 |
| 1577-1589 | `.clip-example`, `.clip-status-ok`, `.clip-status-error` | `014a2bf` | P:14559, 14574 |
| 1814-1839 | `.settings-search`, its `input`, `svg`, `:focus-within` | `d44b177` | P:4732-4735 |
| 1841-1846 | `.settings-panels.searching .settings-panel { display: flex; flex-direction: column; gap: 16px }` | `d44b177` | P:10219, 10226 |
| 1848 | `.search-hidden { display: none !important }` | `d44b177` | P:10220-10271 |
| 1850-1868 | `.settings-search-label`, `.settings-search-empty` and their `.searching` variants | `d44b177` | P:10230-10236, 10263-10271 |

## 4. Original code that was changed

One upstream line was edited. The other six hunks insert between upstream rules.

| Region (upstream) | Where | Change | Kind |
| --- | --- | --- | --- |
| `:root` variable block | U:16-42, P:16-45 | Three variables added after `--ok` and `--danger-2` | extended-in-place |
| `body.settings-open, body.media-browser-open` | U:65-68, P:68-71 | Second selector renamed to `body.pb-open`. Same declaration (`overflow: hidden`). The class `media-browser-open` no longer exists in the page (CSS or script) | rewritten |
| `.date-time-pill, .status-pill` base rule | U:155-168 unchanged; new rules P:173-204 | A new `.status-pill` rule adds `position: relative; overflow: hidden` in every state, then the bar states | extended-in-place |
| `.status-dot` states | U:176-192 unchanged; new rules P:230-238 | A `preroll` state. `.status-dot.preroll` is placed after `.status-dot.no-media` (same specificity), so it wins by order; the port comment P:230 says so | extended-in-place |
| `.time-card.recording .timecode-value` | U:533-535 unchanged; new rule P:583-585 | A higher-specificity rule turns the take timecode white when `plain-timecode` is set. Upstream: always red in a take | behaviour-changed |
| `.preview-stage` | U:263-269 unchanged; new rule P:587-595 | A `::after` border for the state `recording-frame`, `z-index: 6`. Upstream children use z-index 0 and 1 (U:288-503) | extended-in-place |
| `.pill-button` rule group | U:763-803; the port inserts P:850-1590 between `.pill-button.active` (U:783-788) and `.pill-button.disabled` (U:790-797) | 741 lines split the upstream group. New modifiers on the upstream class: `.system-value`, `.active .pill-sub`, `.ladder-switch`, `.ladder-locked ... .active` | extended-in-place |
| `.online-pill` | U:831-839 unchanged (P:1632-1640); new rules P:878-881, 1321-1323 | A grey `.off` variant and a `.section-head` placement rule. Both sit about 750 lines before the base rule | extended-in-place |
| `.settings-card-head` | U:1443-1452 unchanged; new rule P:868-876 | A `.wrap-head` modifier | extended-in-place |
| `.pill-grid` | U:749-761 unchanged; new rules P:1184-1190, 1364-1369 | Modifiers `.ladder-pair`, `.ladder-aspects`, `.ladder-locked` | extended-in-place |
| Settings sidebar | U:990-1021; the port inserts P:1814-1868 between `.settings-sidebar-copy` (U:1007-1011) and `.settings-nav` (U:1013-1021) | Search box rules | extended-in-place |
| `.settings-panel` display | U:1111-1120 unchanged (P:1968-1977); new rule P:1842-1846 | While `.settings-panels` has `searching`, every panel is `display: flex`. Upstream: only `.settings-panel.active` shows | behaviour-changed |

## 5. New CSS component families, and what upstream uses for the same job

| # | Family | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| A1 | `--info`, `--select-bg`, `--select-fg` | Named colours | Same mechanism: `:root` variables U:16-42. Upstream writes this blue as a literal (`#38bdf8` U:1796) | F2, F7, F10 |
| A2 | Pill fill bar: `::before` plus the custom property `--buffer-fill` set from script | Level gauge inside the status pill | `.progress-track` and `.progress-fill` U:891-905 (width set inline). Pseudo-element precedent: `.media-select-control::after` U:1308. Custom property set from script: `--preview-aspect-ratio` U:266, U:5447 | F1 |
| A3 | `.status-pill.preroll`, `.status-dot.preroll` | One more status state | `.status-dot.recording`, `.timelapse`, `.writing`, `.no-media` U:181-192. Upstream toggles `recording`, `timelapse`, `no-media` on the pill too (U:9796-9798) and has no `.status-pill.<state>` rule | F2 |
| A4 | `.preview-stage.recording-frame::after`, `.plain-timecode` | Take cue around the picture; optional red timecode | `.time-card.recording` U:520-535, `.status-dot.recording` U:181; `.preview-stage.<state>` classes that show child overlays U:292-352 | F3 |
| A5 | `.system-value` | Marks a value the camera chose | none (no italic and no such marker in upstream; pill states are `.active` U:783 and `.disabled` U:790) | F4 |
| A6 | `.switch-field` with `.wrap-head` | Label plus an Off/On pill pair in a card head | `.settings-card-head` with an `.online-pill` value and a `.pill-grid` under the head: U:1443-1452, markup U:2939-2948 (Gyro Data card) | F5 (Speed Ramp card) |
| A7 | `.ladder-box` | Bordered tile inside a card | `.preset-row` U:1887-1896 (same border, background, radius and padding values), `.config-meta-tile` U:1579-1585, `.settings-summary-tile` U:1474 | F5 |
| A8 | `.crop-frame`, `.crop-window`, `.crop-tag` | Thumbnail of the sensor window a mode reads | none | F5 |
| A9 | `.ladder-list`, `.ladder-item`, `.ladder-row*`, `.ladder-transition`, `.ladder-fps-input` | Ordered editable list with a number field between rows | List rows: `.preset-row`, `.preset-meta`, `.preset-actions`, `.preset-action` U:1887-1936, built at U:7340-7386 with Up, Down, Remove buttons (`moveFavoriteItem` U:6505). Also `.media-row` U:1341-1431 | F5 |
| A10 | `.ladder-groups`, `.ladder-group-head[aria-expanded]` | Collapsible groups | none (`aria-expanded`, `<details>`: 0 hits in upstream) | F5 |
| A11 | `.ladder-pool-item`, `.ladder-add` | Tile with an Activate or Deactivate button | `.preset-row` with `.secondary-button` actions U:1887, U:1653; `.media-row-action` U:1427 | F5 |
| A12 | `.select-note`, `.ladder-line`, `.ladder-link` | Text at the right of a pill block that links to a settings card | `.select-value`, `.select-value-pill` in `.select-topline` U:719-747. A link from the main page into a settings card: none | F5 |
| A13 | `.pill-sub`, `.pill-button.ladder-switch`, `.pill-grid.ladder-locked` | Second line in a pill; dashed "will switch" pill; grey selected pill of a locked group | `.pill-button` states U:763-803. Sub-lines: none | F5 |
| A14 | `.online-pill.off` | Grey value pill | `.online-pill` U:831-839; upstream recolours `#onlinePill` inline (U:9828-9829) | F5 |
| A15 | `.value-chip*` | Chip with a remove button | none in upstream. The port has three more chip or pill families: `.clip-pill` P:1476, `.pb-chip` P:2167, `.action-chip` P:3208 | F6 |
| A16 | `.clip-row`, `.clip-pill*`, `.clip-ghost`, `.clip-palette-*` | Drag-and-drop composer | none (`draggable`, `dragstart`: 0 hits in upstream; upstream reorders with Up and Down buttons, U:7354-7375) | F7 |
| A17 | `.settings-search*`, `.searching`, `.search-hidden` | Class-toggle filter over all settings panels | Hide helper `.hidden { display: none !important }` U:1975-1977; panel switch U:1111-1120. Search: none | F8 |

## 6. Removed, narrowed or hidden (this slice)

| What | Where | Effect |
| --- | --- | --- |
| Class `media-browser-open` | U:66 removed at P:69 (`bc12c0a`) | The scroll lock moves to `pb-open`. Upstream's `#mediaBrowserOverlay` (U:3979) is replaced by `#playbackOverlay` (P:6345), outside the slice |
| Always-red take timecode | U:533-535 overridden by P:583-585 (`f4fb084`) | Now a switch. Default unchanged: `recordingRedTimecodeEnabled = true` App:1906; the page treats a missing value as on (P:16133) |
| One panel at a time | U:1111-1120 overridden by P:1842-1846 (`d44b177`) | Only while the search box holds text |
| Status text and dot | P:202-204 | Hidden (`visibility: hidden`) during the new `buffer-drain` state |

Nothing else of upstream's CSS in U:22-1022 was deleted (confirmed: the diff has one `-` line).

## 7. Rules with no element at HEAD

Fact check by `grep` over P:4394-20963 (markup and script). confirmed.

| P lines | Selector | Last user removed by |
| --- | --- | --- |
| 1028-1030 | `.ladder-row.dragging` | `b8ee23f` (ladder orders itself; drag removed). `dragging` is set only on `.clip-pill` (P:14729, 14803) and `.action-chip` (P:16842) |
| 1032-1034 | `.ladder-row.drop-target` | `b8ee23f` |
| 1045-1055 | `.ladder-handle` | `b8ee23f`. `ladderIcons.handle` P:7645 is defined and never read |
| 1120, 1127-1129 | `.ladder-row-controls .settings-input`, `.settings-input.problem` | `e472b1b` (the max field moved between the rows) |
| 1131-1134 | `.ladder-thr` | `e472b1b` |
| 1156-1161 | `.ladder-row-buttons` | `8050d56` |
| 1163-1182 | `.ladder-icon-button`, `.remove`, `:disabled` | `8050d56`. Helper `createLadderIconButton` P:8106-8114 stays, with no caller |
| 1301-1306 | `.ladder-pool-number` | `b21c76a` |
| 1314-1319 | `.ladder-add.on-ladder` | `af22759` |
| 1339-1342 | `.select-note.ladder-on` | `392e812` |

About 65 lines.

## 8. What drives these classes (defined outside the slice; cross-reference only)

The slice adds no socket command, HTTP route, state field, event, config key, env var or file. The items below are what
the script binds to the classes above. They belong to other units.

| Feature | Commands | State fields | Route | Config, env, files | UI elements |
| --- | --- | --- | --- | --- | --- |
| F1 | `set_frame_buffer_bar_enabled` (App:13507), `set_buffer_mode` | `ui.frame_buffer_bar_enabled` (App:9664), `buffer_mode`, `buffer_fill`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `recording` (read P:16517-16562) | `GET /api/buffer` (App:8419), polled every 250 ms (P:16432, 16497) | `UI.conf:[General] frameBufferBarEnabled` (App:1905 default false, App:2096); `apertar-hardware.conf:[storage] buffer`, `buffer_stop_percent` (`src/util/BufferBudget.hpp:117-123`); env `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_BUFFER_STOP_PERCENT` (port-added, not in upstream) | `.status-pill` P:4415; switch "Frame buffer bar" P:5279-5281 |
| F2 | `storage_preroll`, `set_storage_preroll` | `storage_preroll_active`, `storage_preroll_fps`, `storage_preroll_auto`, `storage_preroll_auto_env` (P:16500-16512) | `GET /api/buffer` | `apertar-hardware.conf:[media] preroll`, `preroll_seconds` (`src/util/StoragePreroll.hpp:22-38`); env `APERTAR_STORAGE_PREROLL` (port-added) | Pill text "PRE-ROLL" P:16453; button `#storagePrerollButton` P:5770 |
| F3 | `set_recording_frame_enabled`, `set_recording_red_timecode_enabled` (App:13505, 13509; P:16138, 16152) | `ui.recording_frame_enabled`, `ui.recording_red_timecode_enabled` (App:9663, 9665) | | `UI.conf:[General] recordingFrameEnabled` (default false), `recordingRedTimecodeEnabled` (default true) (App:1904, 1906, 2094-2099) | Switches `#settingsRecordingFrameOptions` P:5276, `#settingsRecordingRedTimecodeOptions` P:5285 |
| F4 | none | `iso_auto_after_clear_hdr`, `iso_max`, `ui.iso_steps` (P:8673-8677), `wb_auto_after_clear_hdr` (P:15407), `storage_preroll_active` (P:8696-8705) | | | `#isoBadge`, `#wbBadge`, `#fpsBadge`, `#settingsFpsSummary`, active pills |
| F5 | `get_mode_ladder`, `set_mode_ladder` (also `dry_run`, `enabled`), `set_fps`, `set_fps_speed_ramp` | `ladder_active`, `ladder_enabled`, `ladder_resolution`, `ladder_tops`, `ladder_text`, `fps_take_max` (P:13903-13914, 15880-15935) | `/api/command` | File `~/.config/apertar-core/mode_ladder.conf` (`src/camera/CameraController.cpp:404-414`) | Panel "Modes" P:4750, 5151-5199; Speed Ramp card P:4980-5007; `#quickLadderPill` P:4512; `#fpsLadderLine` P:4519 |
| F6 | `set_value_steps` (P:8494) | `ui.iso_steps`, `ui.shutter_angle_steps`, `ui.fps_steps`, `ui.wb_steps`, `ui.*_free`, `ui.*_free_increment`, `ui.flicker_free_shutter_angles`, `ui.mains_hz` (P:8484-8510) | | `UI.conf:[General] isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles`, `mainsHz` (App:2159-2189) | Value Lists card on the Controls panel P:6162-6169 (moved from Record by `6777ebe`) |
| F7 | `set_clip_name_template`, `preview_clip_name` (P:14607, 14629) | `clip_name_template`, `clip_name_example` (P:13929-13932) | | `camera_settings.conf: clip_name_template` (`src/camera/CameraController.cpp:899, 981`) | Clip names card P:4937-4960 |
| F8 | none | none | | none | `#settingsSearchInput` P:4732-4735; `data-search` keywords on cards |
| F9 | none | none | | | `#playbackOverlay` P:6345 |
| F10 | none | none | | | Selects in `[data-panel="controls"]` and `#hardwareDevices` (P:3486-3487) |

## 9. Board and sensor assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| Pi model, core count, RP1, PCIe, gpiochip number, I2C bus, RAM, fan | Not present in the 858 added CSS lines | confirmed by reading every added line |
| Sensor readout area is 3840x2160, 16:9 | CSS: `.crop-frame` 78x44, 160x90, 64x36 with the comment "16:9, the sensor area (3840x2160) the window is drawn in" P:912-930. Script: `const ladderCropArea = { width: 3840, height: 2160 }` P:7642, used P:7686, 7905-7910 (the window is cut to that area with `Math.min`) | A sensor assumption (IMX585 4K area), not a board one. The port also carries IMX283 modes (fork-log:138, `a47dc28`). No per-sensor value for the area or the thumbnail aspect was found |
| Browser features | `:focus-within` P:1839, `:scope` in script P:10230, `touch-action: none` P:1490, `inset` P:182, 591 | Client side. Upstream already uses `inset: 0` (U:273) |

## 10. Owner request 16 (put the GPIO chip definition back): relation to this slice

| Point | Evidence | Label |
| --- | --- | --- |
| The slice holds no GPIO chip rule and removes none | All 858 added lines read; `chip` appears only in `value-chip*` names (P:1398-1451) | confirmed |
| Where the chip definition went (outside this slice) | `166cc4d` added `{"chip", "GPIO chip", "text", "auto", "", 0, 0}` to `peripheralSettings("gpio_buttons")`; `c140c4f` removed it together with `poll_ms`. Today: `src/hardware/ControlsModel.hpp:257-263` @cinemate-port lists `enabled`, `active_low`, `pull`, `debounce_ms`, and the comment "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" | confirmed |
| Upstream keeps the chip key | `key == "chip" \|\| key == "gpiochip" \|\| key == "gpio_chip"` in `src/hardware/GpioInput.cpp:431`, `TriggerOutput.cpp:311`, `RecordingIndicatorOutput.cpp:319` @upstream-1.6.0; default text `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]`, `src/ApertarCoreApp.cpp:4380, 4394` @upstream-1.6.0 | confirmed |
| The port's readers still accept the key | `src/hardware/GpioInput.cpp:343`, `TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:312, 340`; `[gpio_buttons] chip` read for the status text at `src/ApertarCoreApp.cpp:11987-11991` @cinemate-port | confirmed |
| A read-only chip line once showed on the Controls card | `166cc4d` added "Chip <path> (<label>), <n> lines" to the page script; `f5fe41b` removed it. No GPIO chip text is in `WebControlPage.cpp` @cinemate-port | confirmed |
| CSS a reinserted chip field would use | The Controls panel renders a `text` or `number` setting as `input.settings-input` and a `bool` or `choice` setting as `select.settings-select` (P:17716-17745). A select there takes the white look from P:3486-3495, which reads `--select-bg` and `--select-fg` (P:35-36, this slice). An input takes no rule from this slice | confirmed |

## 11. Other facts for stage 2 (not judged here)

| Fact | Evidence |
| --- | --- |
| A CSS comment carries an internal work-package number | "Value lists (T33)" P:1398 |
| A CSS comment names a panel the cards have left | P:859 says "(Settings > Record)". Mode Ladder and Activated sensor modes sit in `data-panel="modes"` P:5151-5199 since `854fe43`; Speed Ramp is in Record P:4980 |
| `body.pb-open { overflow: hidden }` exists twice | P:68-71 and P:1980-1982 (both `bc12c0a`) |
| A ladder-named class serves a card that has no ladder | `.pill-grid.ladder-pair` on the Timecode card P:5089, 5093 |
| A second `@media (max-width: 560px)` block sits mid-file | P:1371-1380. Upstream keeps every `@media` block at the end of the CSS (U:2034, 2062, 2190, 2319, 2391); it has a 560px block at U:2319 |
| No `@media` rule mentions `.settings-search` | grep over P:15-4393 |
| Colour literals | The 858 lines use `var(--muted)` 15 times, `var(--danger)` 6, `var(--info)` 5, `var(--ok)` 3. New literals not in upstream: `#fbbf24` (6 uses), `#f59e0b`, `#90ee90`, `#8a8a8a`, `#131210`. `.clip-pill.token` and `.clip-pill.text` write the `--info` and `--ok` colours as `rgba(56, 189, 248, ...)` and `rgba(52, 211, 153, ...)` P:1494-1501 |
| A third monospace font stack | `ui-monospace, Menlo, Consolas, monospace` P:1509, 1578. Upstream stacks: U:526, U:1567 |
| z-index | Upstream CSS values: 0, 1, 4, 5, 84, 85, 90, 100. `.clip-ghost` uses 9999 P:1552 |
| Variants defined before their base rule | `.online-pill.off` P:878 and `.section-head .online-pill` P:1321, base `.online-pill` P:1632 |
| Related rules for the same features sit outside the slice | `.toast.with-link`, `.toast .ladder-link`, `[data-ladder-lock] select:disabled` P:3970-3980 (`392e812`); white selects P:3484-3520 (`d44b177`) |

## 12. Commits that wrote the slice

Status and tests as recorded (fork-log line numbers; `Tested:` line of the commit message).

| Commit | Date | Subject (short) | Lines here | Fork-log status | Tested, per message |
| --- | --- | --- | --- | --- | --- |
| `1ef94fe` | 2026-10-28 | web: Mode Ladder, Speed Ramp and Activated sensor modes cards per the approved design | 423 | :97 fork-only, "desk-tested, Pi check pending" | desk (headless Chrome against the Pi's Core state); Pi build pending |
| `014a2bf` | 2026-11-01 | drop-frames: clip names you can compose | 136 | :138 (inside the drop-frames row) | no `Tested:` line. KB: host test `tools/clip_name_test.cpp`; WebUI composer untested by hand |
| `d44b177` | 2026-10-31 | drop-frames: trim, Log, RAM write buffer, buffer bar, fps max, storage pre-roll (squash of 19) | 121 | :138 "offer (in pieces, after the Pi tests ...)" | host tests on the Mac, `node --check`; compiles on the Pi; pre-roll "not compiled or run yet"; "nothing opened in Resolve or a browser" |
| `920beb0` | 2026-10-28 | web: the Mode Ladder editor | 44 | :94 "built 2026-10-28, not tested" | desk only (`node --check`) |
| `ff33d2d` | 2026-10-28 | web: Value Lists card (T33) | 42 | :77 "tested 2026-10-28 (Patrik)" | desk only (`node --check`) |
| `af22759` | 2026-10-29 | web: sensor-mode tiles say why Add is off | 26 | :97 | desk (headless Chrome); Pi build |
| `e472b1b` | 2026-10-28 | web: the threshold FPS between ladder rows is the editable max | 15 | :97 | desk (headless Chrome); Pi build |
| `f4fb084` | 2026-10-28 | core, web: recording frame and red timecode switches | 14 | :81 "tested 2026-10-28 (Patrik)" | desk only (built on the Pi next) |
| `5dfbc6c` | 2026-10-29 | web: the ladder line and pill open the Mode Ladder card | 9 | :97 | desk (headless Chrome, read only); Pi build |
| `65e049e` | 2026-10-28 | web: show each threshold FPS as a chip between the ladder rows | 6 | :97 | desk (headless Chrome); Pi build |
| `d93a7e3` | 2026-10-28 | web: grey out the sensor modes that are not on the ladder | 5 | :97 | desk (headless Chrome); Pi build |
| `e58e7e5` | 2026-10-28 | web: values the camera decides are italic, not green | 4 | :88 "built 2026-10-28" | desk only (`node --check`) |
| `6707b08` | 2026-11-01 | web: crop thumbnails are 16:9 | 4 | :138 | desk only (`node --check`); screenshot measured before the fix |
| `392e812` | 2026-10-29 | web: a locked control answers with the red warning | 4 | :97 | desk (headless Chrome, read only); Pi build |
| `da8ca9f` | 2026-10-29 | web: the ladder saves itself; sensor modes filter on aspect ratio | 2 | :97 | desk (headless Chrome: autosave round trip); Pi build |
| `bc12c0a` | 2026-10-29 | web: the Clip Browser, in the touch UI's shape (T49) | 1 | :101 "tested 2026-10-29 (headless Chrome against Core)" | desk (headless Chrome, read-only); Pi build pending |
| `b21c76a` | 2026-10-29 | web: remove the FPS coverage bar and the Resolution n label | 1 | :97 | desk (headless Chrome); Pi build |
| `15bba86` | 2026-10-28 | web: auto ISO, WB and shutter are white | 1 | :83 "built 2026-10-28" | desk only (`node --check`) |

## 13. Open

| Item | Label | Settle with |
| --- | --- | --- |
| How each rule renders (bar inside the pill, frame over the overlays, search layout on a phone) | unconfirmed | Core `--simulate`, headless Chrome screenshots at 1320, 560 and 420 px |
| Whether the crop thumbnail is right for a sensor that is not 3840x2160 | unconfirmed | Read `get_mode_ladder` on an IMX283 and compare the thumbnail with the mode's window |
