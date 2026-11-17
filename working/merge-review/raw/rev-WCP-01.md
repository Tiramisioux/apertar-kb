# Review WCP-01: `src/web/WebControlPage.cpp`, CSS slice 1 (port lines 22-1879), against original Apertar

Stage 2 of 3. Written 2026-11-17. Inputs: `raw/inv-WCP-01.md` (inventory, facts reused, not re-derived), `raw/conv-webui.md`
(rule ids S*, I*, N*, R*), diff `/home/user/build/review/diffs/WCP.part01.diff` read whole.
`P:n` = `/home/user/Apertar-Core/src/web/WebControlPage.cpp` @cinemate-port `01f170c`.
`U:n` = `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0 (= @main for these lines).
All claims confirmed (read in code) unless labelled.

## 0. Verdict in one paragraph

The slice is CSS only. It adds no protocol, route or config. Most of it extends upstream components in place with the
upstream token set and upstream spacing values (status pill, status dot, time card, preview stage, pill states). That part
reads as Apertar. The foreign parts are smaller in effect but visible to the original developer: 8 CSS comments in a
stylesheet that has none (one with a ticket number), a 741-line block wedged inside the `.pill-button` rule group, a
second 560px media block mid-file, about 65 lines of dead rules, two near-identical chip families, a re-styled button
family where upstream has `primary/secondary/danger-button`, and a card-head switch layout where upstream has the
Gyro Data card recipe. One upstream card (Timecode) changes look through a ladder-named class. No blocker.

## 1. Findings

| Id | Sev | Category | Title | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | minor | slop | 8 CSS comments in a comment-free stylesheet; one carries "T33", one names a stale panel | no |
| F2 | minor | mismatch | Speed Ramp card head uses new `.switch-field` + `.wrap-head` instead of the Gyro Data card recipe | no |
| F3 | minor | mismatch | Upstream Timecode card pill grids switched to `.pill-grid.ladder-pair` (fixed 88px, ladder name) | no |
| F4 | minor | mismatch | `.ladder-add`, `.ladder-box`, `.ladder-pool-item` re-create upstream button variants and `.preset-row` | no |
| F5 | minor | slop | About 65 lines of rules with no element at HEAD (drag, handle, icon buttons, thr, pool number, on-ladder, ladder-on) | no |
| F6 | minor | duplication | `.value-chip` and `.clip-pill` share the same base and the same remove-x button, written twice | no |
| F7 | minor | mismatch | 741 new lines split the `.pill-button` group; second `@media (max-width: 560px)` block mid-file; variants before base | no |
| F8 | minor | mismatch | `body.media-browser-open` renamed to the abbreviation `body.pb-open`; rule declared twice | no |
| F9 | minor | bug | Crop thumbnail hard-wired to a 16:9 3840x2160 sensor area; wrong for IMX283 (3:2) | no |
| F10 | minor | new-ground | Clip names drag-and-drop composer (ghost at z-index 9999, long-press) where upstream reorders with buttons | unknown |
| F11 | nit | slop | One-line rules, a selector declared twice, new colour literals and a third monospace stack | no |
| F12 | nit | new-ground | Settings search (`.searching`, `.search-hidden`): keep | yes |

### F1. CSS comments (minor, slop)
- Port: 8 comments added, P:88-89 (diff), P:230 "Storage pre-roll: blue pill and dot (after .no-media so it wins).",
  P:583 area "Recording frame: ...", P:850 "A value the camera decides ...", P:859
  "Mode Ladder, Speed Ramp and Activated sensor modes (Settings > Record), and the ladder in Camera settings",
  P:915 `/* 16:9, the sensor area (3840x2160) ... */`, P:1398 "Value lists (T33): one chip per value, x removes it.",
  P:1841 "Search: every panel shows at once ...".
- Apertar way: conv-webui I9, "none in CSS/HTML"; `grep -c '/\*' U` = 0.
- Also wrong: P:859 says Settings > Record; the ladder cards sit in `data-panel="modes"` P:5151-5199 (inventory section 11).
- Rework: delete all 8. If one must stay, keep the specificity note at P:230 as one line without narrative.

### F2. Speed Ramp card head (minor, mismatch)
- Port: P:4981-4990 `settings-card-head wrap-head` > `div.switch-field` > "Allow speed ramping" + `pill-grid ladder-pair`.
  CSS `.switch-field` P:859-866, `.wrap-head` P:868-876. One use each.
- Apertar way (R1, Gyro Data card U:2939-2948):
  `<div class="settings-card-head"> <div>title+copy</div> <div class="online-pill" id="settingsGyroDataValue">Off</div> </div>`
  then `<div class="pill-grid" id="settingsGyroDataOptions"></div>` below the head.
- Rework: Speed Ramp head = title + copy + `online-pill#settingsSpeedRampValue`; the Off/On grid below it as
  `pill-grid` (`toggleOptions`). Delete `.switch-field` and `.settings-card-head.wrap-head` (P:859-876).

### F3. Timecode card grids (minor, mismatch)
- Port: P:5089, 5093 `pill-grid ladder-pair` on `settingsTimecodeOptions`, `settingsFileTimecodeOptions` (`909aaa5`).
  `.pill-grid.ladder-pair { grid-template-columns: repeat(2, 88px) }` P:1184-1186.
- Apertar way: U:3018 `<div class="pill-grid" id="settingsTimecodeOptions">` (4 equal columns, U:749-753); size modifiers
  are `three-col` / `two-col` U:755-761.
- Rework: `pill-grid two-col` (or plain `pill-grid`) on the Timecode card; with F2 done `.ladder-pair` has one user left
  (Mode Ladder Off/On P:5176), which also takes `two-col` or the R1 head layout. Delete `.pill-grid.ladder-pair`.

### F4. Ladder buttons and tiles re-create upstream components (minor, mismatch)
- Port: `.ladder-add` P:1275-1292 (white fill, own size 72x44, radius 14) and `.ladder-add.remove` P:1308-1312 (red
  outline); `.ladder-box` P:883-893 = border `#27272a`, background `rgba(9,9,11,0.72)`, radius 18, padding `14px 16px`;
  `.ladder-pool-item` P:1235-1244 and `.ladder-row` P:1017-1026 another tile on `#202024`.
- Apertar way: I12 button variants U:1632-1706 (`primary-button`, `secondary-button`, `danger-button`) with the list
  size modifier `.preset-action { min-width: 108px }` U:1932-1935; list tile `.preset-row` U:1887-1896 with the same
  border, background, radius and padding as `.ladder-box`.
- Rework: Activate = `secondary-button preset-action`, Deactivate = `danger-button preset-action`; delete `.ladder-add*`.
  `.ladder-box` -> `preset-row` (delete the rule). Keep `.ladder-row` and `.ladder-pool-item` only for what differs
  (badge, crop frame), as modifiers of `preset-row`.

### F5. Dead rules (minor, slop)
- Port, no element at HEAD (inventory section 7, grep-checked): `.ladder-row.dragging`, `.drop-target` P:1028-1034,
  `.ladder-handle` P:1045-1055, `.ladder-row-controls .settings-input`, `.settings-input.problem` P:1120, 1127-1129,
  `.ladder-thr` P:1131-1134, `.ladder-row-buttons` P:1156-1161, `.ladder-icon-button*` P:1163-1182, `.ladder-pool-number`
  P:1301-1306, `.ladder-add.on-ladder` P:1314-1319, `.select-note.ladder-on` P:1339-1342. Script leftovers outside the
  slice: `createLadderIconButton` P:8106-8114 (no caller), `ladderIcons.handle` P:7645 (never read).
- Apertar way: no dead CSS families in U (conv-webui counts; every upstream class family has an element).
- Rework: delete the listed rules and the two script leftovers.

### F6. Two chip families (minor, duplication)
- Port: `.value-chip` P:1410-1426 and `.clip-pill` P:1476-1491 share `inline-flex; gap 6px; radius 999px; border 1px
  solid #27272a; background rgba(9,9,11,0.72); color #f4f4f5; font-size 13px`. Remove buttons `.value-chip button`
  P:1439-1453 and `.clip-pill .clip-x` P:1521-1535: round, muted, `:hover { color: var(--danger) }`, sizes 22 vs 18.
  Outside the slice `.pb-chip` P:2167 and `.action-chip` P:3208 add two more.
- Apertar way: one class per visual component, modifiers by extra class (I7, `.pill-button` + `.active/.disabled`).
- Rework: one `.chip` base and one `.chip-remove` button; `.clip-pill.token/.text/.sep` and `.value-chip.flicker-free`
  become colour modifiers of `.chip`.

### F7. Placement (minor, mismatch)
- Port: P:850-1590 sits between `.pill-button.active` (U:783-788) and `.pill-button.disabled` (U:790-797); the pill
  group is now split by 741 lines. `@media (max-width: 560px)` P:1371-1380 mid-file. `.online-pill.off` P:878 and
  `.section-head .online-pill` P:1321 precede the base `.online-pill` P:1632.
- Apertar way: I10, one block per breakpoint at the end of the stylesheet (U:2034, 2062, 2190, 2319, 2391); rules of
  one component together (`.pill-button` U:763-803).
- Rework: keep the `.pill-button.*` modifiers (`system-value`, `ladder-switch`, `.active .pill-sub`) next to
  U:783; move the Mode Ladder, Value list and Clip name blocks after the settings-card rules (near `.preset-row`);
  move `.online-pill.*` after its base; merge the 560px rules into the U:2319 block.

### F8. `pb-open` (minor, mismatch)
- Port: P:68-71 `body.settings-open, body.pb-open`; again P:1980-1982 `body.pb-open { overflow: hidden }` (both `bc12c0a`).
- Apertar way: U:65-68 `body.settings-open, body.media-browser-open`; I7 names are full words.
- Rework: comes with the playback overlay rework (rev-WCP-03 F1). For this slice: one rule, a full-word class
  (`media-browser-open` if the overlay keeps the upstream role), delete the duplicate at P:1980.

### F9. Crop thumbnail sensor area (minor, bug, probable)
- Port: `.crop-frame` 78x44 / 160x90 / 64x36 P:912-930 with "16:9, the sensor area (3840x2160)"; script
  `const ladderCropArea = { width: 3840, height: 2160 }` P:7642, used P:7686 and P:7905.
- Failing input: an IMX283 mode (sensor 5472x3648, 3:2; the port carries IMX283, `a47dc28`). The window is clamped
  to 3840x2160 and drawn in a 16:9 frame; a full-sensor mode shows as cropped or overflows. Probable (read from code,
  not run); settle with `get_mode_ladder` on an IMX283 and compare.
- Apertar precedent for a geometry value from script: `--preview-aspect-ratio` U:266, set U:5447.
- Rework: read the full area from the mode list (largest `window_w/h` or a sensor field), set `--crop-aspect` on the
  frame, size with `aspect-ratio: var(--crop-aspect)`; drop the fixed heights.

### F10. Clip names composer (minor, new-ground, simplify)
- Port: P:1455-1589 drag-and-drop row, `.clip-ghost { position: fixed; z-index: 9999 }` P:1548-1556, long-press with
  `touch-action: none`, palette groups, inline text input inside a pill.
- Apertar way: no drag in U (`draggable`, `dragstart` 0 hits); ordered lists reorder with Up / Down / Remove buttons
  (favourites, U:7354-7375, `moveFavoriteItem` U:6505). Highest upstream z-index 100 (U:1994).
- KB: `working/drop-frames/README.md:102` "WebUI composer and touch card untested by hand". No record of weighing
  buttons vs drag.
- Verdict simplify: tap a palette chip to append, x to remove, Up/Down like favourites; or keep the composer and drop
  z-index to the upstream scale (<= 100). Core side (`ClipName.hpp`) is not in this unit.

### F11. Small style drift (nit, slop)
- One-line rules P:1832-1833 (`.settings-search svg { ... }`, `:focus-within`), P:1848 `.search-hidden`, P:1858,
  1863-1864; upstream writes every rule over several lines.
- `.settings-search-empty` declared twice (P:1863 `display: none` and P:1866-1869 padding).
- New literals: `#fbbf24` x6, `#f59e0b`, `#90ee90`, `#8a8a8a`, `#131210`; ladder badge `#4ade80` disc. Upstream warning
  yellow is `#ffd54a` (U `.status-dot.writing`), OK green is `--ok`. `.clip-pill.token/.text` write `--info` / `--ok` as
  rgba literals P:1494-1501. Third monospace stack `ui-monospace, Menlo, Consolas, monospace` P:1509, 1578 (upstream
  stacks U:526, U:1567).
- Rework: multi-line rules, merge the two `.settings-search-empty`, reuse `#ffd54a` and the upstream mono stack.

### F12. Settings search (nit, new-ground, keep)
- Port P:1814-1868. `.search-hidden` is separate from upstream `.hidden` (U:1975-1977) on purpose: render code toggles
  `.hidden` for "not for this configuration" (I11) and the filter must not clobber that. `.settings-panels.searching
  .settings-panel { display: flex }` overrides U:1111-1120 only while text is in the box.
- KB: `working/drop-frames/README.md:87` describes the design (`data-search` keywords, MutationObserver).
- Verdict keep. Only F1 (comment) and F11 (one-line rules) apply. Missing: no small-screen rule in the 720/480 blocks;
  check on a phone width before merge (unconfirmed).

## 2. Abstractions (inventory section 5)

| # | Family | Verdict | Reason |
| --- | --- | --- | --- |
| A1 | `--info`, `--select-bg`, `--select-fg` | keep | Same mechanism as U:16-42; `--info` names an upstream literal (`#38bdf8` U:1796) |
| A2 | Pill fill bar (`::before`, `--buffer-fill`) | keep | Pseudo-element and script-set property both have precedent (U:1308, U:266/5447); drop the comment (F1) |
| A3 | `.status-pill.preroll`, `.status-dot.preroll` | keep | One more state in the upstream state list U:181-192 |
| A4 | `.recording-frame::after`, `.plain-timecode` | keep | State class on `.preview-stage` and `.time-card` like U:292-352, 520-535; default unchanged (red timecode on) |
| A5 | `.system-value` | keep | 8 lines, extends in place; move next to the pill group (F7) |
| A6 | `.switch-field` + `.wrap-head` | rework-to-upstream-pattern | F2, R1 Gyro Data card |
| A7 | `.ladder-box` | rework-to-upstream-pattern | F4, identical to `.preset-row` |
| A8 | `.crop-frame`, `.crop-window`, `.crop-tag` | simplify | New and useful; size from the sensor area (F9), use upstream yellow |
| A9 | `.ladder-list`, `.ladder-row*`, `.ladder-transition`, `.ladder-fps-input` | simplify | Delete dead parts (F5); base the row on `.preset-row` |
| A10 | `.ladder-groups`, `.ladder-group-head[aria-expanded]` | keep | No upstream collapsible; small; part of the approved design (`1ef94fe` message, `UI-DESIGN.md`) |
| A11 | `.ladder-pool-item`, `.ladder-add` | rework-to-upstream-pattern | F4, upstream button variants |
| A12 | `.select-note`, `.ladder-line`, `.ladder-link` | keep | Sits in `.select-topline` like `.select-value` U:719-747; delete `.ladder-on` (F5) |
| A13 | `.pill-sub`, `.ladder-switch`, `.ladder-locked` | keep | Modifiers on the upstream pill; locked grey follows I11 intent |
| A14 | `.online-pill.off` | keep | Class instead of upstream inline recolour (U:9828); harmless; move after the base rule (F7) |
| A15 | `.value-chip*` | simplify | Merge with `.clip-pill` (F6) |
| A16 | `.clip-row`, `.clip-pill*`, `.clip-ghost`, `.clip-palette-*` | simplify | F10, F6 |
| A17 | `.settings-search*`, `.searching`, `.search-hidden` | keep | F12 |

## 3. Conforms

- Every hunk except one inserts; one upstream line changed (U:66). No upstream rule deleted.
- New colours as `:root` tokens (P:32-36) in the upstream token block; 29 `var(--...)` uses in 858 lines.
- Status pill and dot states follow the upstream state-class pattern (`.status-dot.preroll` after `.no-media`, P:230-238).
- Take cues are state classes on existing elements (`.time-card.recording.plain-timecode`, `.preview-stage.recording-frame`), default unchanged (App:1906).
- Spacing, radii and pill sizes match the upstream scale (gaps 8-16, radius 14/18/999, 44-50 px targets).
- Locked and disabled looks follow I11 (grey, `cursor: not-allowed`, `.settings-card.locked .clip-pill`).
- Kebab-case class names, state by extra class (I7).
- The page stays one raw string (S1, S2); no `<link>`, no external CSS.

## 4. Protocol, security, Pi compatibility

- Protocol: none in this slice (CSS only).
- Security: none.
- Pi model: no board assumption in CSS. Sensor assumption: F9.

## Skeptic

Stage 3, 2026-11-17. Every finding re-read in code on both sides (`P:` @cinemate-port `01f170c`, `U:` @upstream-1.6.0),
commits checked with `git show -s`, intent checked in `fork-log.md`, `working/drop-frames/README.md` and
`working/ramp-ladder/ui-design/UI-DESIGN.md` (the "approved design" named in `1ef94fe`).

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | 8 comments confirmed (P:196, 230, 587, 850, 859, 916, 1398, 1841; U has 0 `/*`). The review's P:88-89 and P:583 are wrong lines; the set is the one above. Rest stands |
| F2 | corrected | Head layout confirmed P:4981-4990 vs Gyro U:2939-2948. UI-DESIGN.md:71 fixes the label "Allow speed ramping" and Off/On buttons, not the head layout; rework now keeps that label as an `input-label` above the grid |
| F3 | stands | P:5089/5093 `ladder-pair` from `909aaa5` (blame), U:3018 plain `pill-grid`, `two-col` at U:759 |
| F4 | corrected | `.ladder-box` = `.preset-row` values confirmed (U:1887-1896). `.ladder-add` is a white fill, i.e. `primary-button` (U:1643-1647), not `secondary-button`; rework changed |
| F5 | corrected | Script scan confirms no use outside CSS for `drop-target`, `ladder-handle`, `ladder-thr`, `ladder-row-buttons`, `ladder-pool-number`, `on-ladder`, `ladder-on`, `.ladder-row.dragging`; `ladder-icon-button` only from dead `createLadderIconButton`. `.ladder-row-controls .settings-input` P:1120-1129 is not shown dead (the class is built at P:8151): removed from the list. Deleting the function also orphans `ladderIcons.up` and `.remove` (only read at P:8109) |
| F6 | corrected | Same family confirmed; "identical declarations" overstated: padding and line-height differ, remove buttons differ in size (22/18) and background. Still one chip drawn twice |
| F7 | stands | `.pill-button.active` P:843, `.disabled` P:1591; 560px block P:1371; `.online-pill.off` P:879 vs base P:1632. Note: the port has many more mid-file media blocks (P:2452-4364) in later slices |
| F8 | corrected | Confirmed P:68-71, P:1980-1982, toggle P:10120 on the same `state.mediaBrowserOpen` as U:6143. Count of `pb-` lines is 134, not 116 |
| F9 | corrected | Code confirmed P:7642, 7905. `6707b08` (fork-log) made the thumbnails 16:9 on purpose for IMX585; UI-DESIGN.md:89 asks for "the full readout area". The IMX283 family came later (`a47dc28`) and the constant was not revisited. Bug probable, deliberate no for the IMX283 case |
| F10 | corrected | Facts confirmed (no drag in U, U z-index max 100, P:1552 9999). Deliberate is yes: README:102 specifies drag + long-press + tap-to-add in the WebUI and a QML `Drag`/`DropArea` twin in the touch UI (`606f137`). Still new-ground and untested by hand |
| F11 | corrected | Line numbers fixed (one-line rules P:1838-1839, 1848, 1860, 1862-1863). The crop and amber literals (`#8a8a8a`, `#131210`, `#90ee90`, `#fbbf24`) are specified in UI-DESIGN.md:88-90 (Cinemate cropDiagram): rework now names them as `:root` tokens instead of replacing them. "`--info`/`--ok` as rgba" dropped: upstream tints `--ok` the same way (U:833) |
| F12 | stands | `.search-hidden` mirrors upstream `.hidden { display: none !important }` (U:1976); design in README:87. No `settings-search` rule in any media block (grep) |

No new finding added. Side note for the HTML unit: the port's Timecode card (P:5080-5095) also dropped upstream's
`online-pill#settingsTimecodeValue` (U:3016).

## Final findings

### WCP-01-F1 [slop, minor] 8 CSS comments in a comment-free stylesheet; one carries T33, one names a stale panel
- where: P:196, P:230, P:587, P:850, P:859, P:916, P:1398, P:1841 (src/web/WebControlPage.cpp@cinemate-port)
- port: Narrative block comments, e.g. P:1398 `/* Value lists (T33): one chip per value, x removes it. */`, P:859
  "... (Settings > Record) ...". The Mode Ladder cards sit in `data-panel="modes"` (P:5151-5199).
- apertar way: no CSS comments; `grep -c '/\*' U` = 0 (conv-webui I9).
- matters: T33 means nothing to the original developer; the panel name is already wrong; comments stand out as narration.
- rework: delete all 8. At most keep P:230 as one line: `/* after .no-media so it wins */`.
- effort S; deliberate no.

### WCP-01-F2 [mismatch, minor] Speed Ramp card head uses new .switch-field + .wrap-head instead of the Gyro Data card recipe
- where: P:860-876 (CSS), P:4980-4990 (HTML)
- port: `settings-card-head wrap-head` > `div.switch-field` > "Allow speed ramping" + `pill-grid ladder-pair` inside the head.
  One user each.
- apertar way: Gyro Data card U:2939-2948: head = title/copy + `<div class="online-pill" id="settingsGyroDataValue">Off</div>`,
  then `<div class="pill-grid" id="settingsGyroDataOptions">` below the head (conv-webui R1).
- matters: a second On/Off card layout next to the established one.
- rework: head = title + copy + note + `online-pill#settingsSpeedRampValue`. Below it a `field-stack` with
  `<span class="input-label">Allow speed ramping</span>` and `pill-grid two-col#settingsSpeedRampOptions` (same shape as
  the Shutter Sync block right under it). Keeps the label and Off/On buttons of UI-DESIGN.md:71. Delete `.switch-field`
  and `.settings-card-head.wrap-head*`; render code sets the pill text as for Gyro.
- effort S; deliberate no (UI-DESIGN.md fixes the label and buttons, not the layout).

### WCP-01-F3 [mismatch, minor] Upstream Timecode card grids switched to ladder-named .pill-grid.ladder-pair
- where: P:1184-1186, P:5089, P:5093, P:5176
- port: `.pill-grid.ladder-pair { grid-template-columns: repeat(2, 88px) }` on `settingsTimecodeOptions` and
  `settingsFileTimecodeOptions` (`909aaa5`, blame) and on the Mode Ladder Off/On grid.
- apertar way: U:3018 `<div class="pill-grid" id="settingsTimecodeOptions">`; size modifiers `.three-col` / `.two-col` U:755-761.
- matters: an upstream card changes look through a class named after an unrelated feature.
- rework: `pill-grid two-col` (or plain `pill-grid`) on both Timecode grids and the ladder Off/On grid; delete `.pill-grid.ladder-pair`.
- effort S; deliberate no.

### WCP-01-F4 [mismatch, minor] Ladder buttons and tiles re-create upstream button variants and .preset-row
- where: P:883-893, P:1236-1245, P:1275-1312; script P:8361, P:8370
- port: `.ladder-add` white fill, 72x44, radius 14 ("Activate"); `.ladder-add.remove` red outline ("Deactivate");
  `.ladder-box` border `#27272a`, background `rgba(9,9,11,0.72)`, radius 18, padding `14px 16px`.
- apertar way: `primary-button` (white fill `#f4f4f5`), `secondary-button`, `danger-button` U:1632-1706, list size
  modifier `.preset-action { min-width: 108px }` U:1932; tile `.preset-row` U:1887-1896 has exactly the `.ladder-box` values.
- matters: a parallel button and tile vocabulary; later upstream button changes would not reach the ladder card.
- rework: Activate = `primary-button preset-action`; Deactivate = `danger-button preset-action`; `.ladder-box` -> `preset-row`
  (delete the rule). Keep `.ladder-row` / `.ladder-pool-item` only for what differs (badge, crop frame). Delete `.ladder-add*`.
- effort M; deliberate no.

### WCP-01-F5 [slop, minor] About 60 lines of rules with no element at HEAD, plus dead ladder helpers
- where: P:1028-1034, P:1045-1055, P:1131-1134, P:1156-1182, P:1301-1306, P:1314-1319, P:1339-1342; script P:7644-7650, P:8106-8114
- port: `.ladder-row.dragging`, `.ladder-row.drop-target`, `.ladder-handle`, `.ladder-thr`, `.ladder-row-buttons`,
  `.ladder-icon-button*`, `.ladder-pool-number`, `.ladder-add.on-ladder`, `.select-note.ladder-on`: no use outside CSS
  (scan of every class in P:850-1400 against the script and HTML). `createLadderIconButton` P:8106 has no caller; it is
  the only reader of `ladderIcons.up`, `.remove` and nothing reads `.handle`.
- apertar way: every upstream class family has an element (conv-webui counts).
- matters: history left in code; misleads the reader about features that no longer exist.
- rework: delete the listed rules, `createLadderIconButton`, and `ladderIcons.handle/up/remove` (keep `down`, `chevron`).
- effort S; deliberate no.

### WCP-01-F6 [duplication, minor] .value-chip and .clip-pill draw one chip and one remove button twice
- where: P:1416-1453, P:1476-1535 (cross-unit: `.pb-chip` P:2167, `.action-chip` P:3208)
- port: both bases share inline-flex, gap 6, radius 999, border `#27272a`, background `rgba(9,9,11,0.72)`, colour
  `#f4f4f5`, 13px; they differ in padding and line-height. Two round muted x buttons with `:hover { color: var(--danger) }`,
  22px vs 18px.
- apertar way: one class per component, state and variant as extra classes (`.pill-button` + `.active/.disabled`,
  U:763-803, conv-webui I7). Upstream has no chip.
- matters: up to four chip vocabularies for one visual element.
- rework: one `.chip` base and one `.chip-remove`; `.chip.token/.text/.sep`, `.chip.flicker-free` as modifiers; the
  drag-only properties (`cursor: grab`, `touch-action`) on the composer's modifier.
- effort M; deliberate no.

### WCP-01-F7 [mismatch, minor] 741 lines split the .pill-button group; mid-file 560px media block; variants before base
- where: P:850-1590, P:1371-1380, P:879, P:1321
- port: Mode Ladder, Value list and Clip name CSS sit between `.pill-button.active` (P:843) and `.pill-button.disabled`
  (P:1591); a second `@media (max-width: 560px)`; `.online-pill.off` and `.section-head .online-pill` before the base
  `.online-pill` (P:1632).
- apertar way: `.pill-button` rules together U:763-803; one block per breakpoint at the end: U:2034, 2062, 2190, 2319 (560px), 2391 (conv-webui I10).
- matters: the pill states are 741 lines apart; responsive rules no longer in one place.
- rework: keep `.pill-button.*` modifiers next to `.pill-button.active`; move ladder, value-list and clip-name blocks after
  the settings-card / `.preset-row` rules; `.online-pill.*` after the base; merge the 560px rules into the end block.
  The later mid-file media blocks (P:2452-4364) are the same issue in other slices.
- effort S; deliberate no.

### WCP-01-F8 [mismatch, minor] body.media-browser-open renamed to the abbreviation body.pb-open, declared twice
- where: P:68-71, P:1980-1982, P:10120
- port: `body.settings-open, body.pb-open { overflow: hidden }` and again `body.pb-open { overflow: hidden }` (`bc12c0a`);
  toggled from the same `state.mediaBrowserOpen` as upstream.
- apertar way: `body.settings-open, body.media-browser-open` U:65-68, toggled U:6143; class names are full words (conv-webui I7).
- matters: the `pb-` family (134 lines) is foreign naming; the duplicate rule is noise.
- rework: with the playback overlay rework (rev-WCP-03 F1): one rule with `media-browser-open` (same state, same role);
  delete P:1979-1982.
- effort S; deliberate no.

### WCP-01-F9 [bug, minor] Crop thumbnail hard-wired to a 16:9 3840x2160 sensor area
- where: P:912-930, P:7642, P:7686, P:7905
- port: `.crop-frame` fixed 78x44 / 160x90 / 64x36; `const ladderCropArea = { width: 3840, height: 2160 }` clamps every window.
- apertar way: geometry passed from script through a custom property: `--preview-aspect-ratio` U:266, set U:5447.
- matters: on IMX283 (5472x3648, 3:2, carried by the port since `a47dc28`) the full sensor is clamped into a 16:9 frame and
  "Crop in" / percent texts are wrong. Probable (read from code, not run; settle with `get_mode_ladder` on an IMX283).
- rework: take the full readout area per sensor (largest `window_w/h` in the `get_mode_ladder` pool, or a sensor field),
  set `--crop-aspect` on the frame, use `aspect-ratio` instead of fixed heights, delete `ladderCropArea`. Keep the IMX585
  rule of UI-DESIGN.md:92 (3840x2200 drawn as 3840x2160).
- effort M; deliberate no (`6707b08` chose 16:9 for IMX585; UI-DESIGN.md:89 asks for "the full readout area"; IMX283 not revisited).

### WCP-01-F10 [new-ground, minor] Clip names drag-and-drop composer where upstream reorders with buttons
- where: P:1455-1589 (`.clip-ghost` P:1548-1556); script around P:14650-14750
- port: HTML5 drag plus pointer long-press, `.clip-ghost { position: fixed; z-index: 9999 }`, inline text inputs in pills,
  tap-to-add palette.
- apertar way: no drag upstream (`draggable`, `dragstart` 0 hits); ordered lists use Up / Down / Remove (favourites
  U:7354-7375, `moveFavoriteItem` U:6505). Highest z-index 100 (U:1994).
- matters: new interaction model, untested by hand (README:102); 9999 is outside the upstream scale.
- rework: preferred: tap a palette chip to append, x to remove, Up/Down like favourites; delete `.clip-ghost` and the drop
  markers. If the owner keeps drag (it mirrors the touch UI's `ClipNameCard.qml`), lower z-index to <= 100 and document it
  for the original developer.
- effort M; deliberate yes (README:102 specifies drag, long-press and tap-to-add, and the touch UI twin `606f137`); no record
  of drag being weighed against upstream's buttons.

### WCP-01-F11 [slop, nit] One-line rules, duplicate selector, untokenised colour literals, third monospace stack
- where: P:1838-1839, P:1848, P:1860, P:1862-1869, P:1509, P:1578; crop/amber literals P:917-918 and slice-wide
- port: rules on one line; `.settings-search-empty` declared twice (P:1862 and P:1865-1869); literals `#fbbf24` x6,
  `#f59e0b`, `#90ee90`, `#8a8a8a`, `#131210` written inline; mono stack `ui-monospace, Menlo, Consolas, monospace`.
- apertar way: every upstream rule spans several lines (0 one-liners in U); colours shared as `:root` tokens (U:16-42);
  mono stacks U:526, U:1567.
- matters: small drift from the house style.
- rework: multi-line rules; merge the two `.settings-search-empty`; reuse an upstream mono stack. The crop and amber colours
  are specified by UI-DESIGN.md:88-90 (Cinemate's cropDiagram): keep the values, declare them once as `:root` tokens.
- effort S; deliberate no (the colour values are deliberate, the formatting is not).

### WCP-01-F12 [new-ground, nit] Settings search (.searching, .search-hidden): keep
- where: P:1814-1869
- port: class-toggle filter; `.search-hidden { display: none !important }` separate from `.hidden`; `.settings-panels.searching`
  shows every panel.
- apertar way: no precedent; closest: `.hidden` U:1975-1977 (same `!important` form) and the one-panel switch U:1111-1120.
- matters: minimal shape; a separate hide class is right because render code owns `.hidden` (conv-webui I11). No
  `settings-search` rule in any media block (unconfirmed on a phone).
- rework: keep. Apply F1 and F11 only. Check the layout at 420-560px.
- effort S; deliberate yes (`working/drop-frames/README.md:87`: `data-search` keywords, MutationObserver).
