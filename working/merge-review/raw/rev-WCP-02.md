# Review WCP-02: `src/web/WebControlPage.cpp`, port lines 1969-3991 (CSS, part 2), against original Apertar

Stage 2 of 3. Input: `/home/user/build/review/diffs/WCP.part02.diff` (4 hunks), `raw/inv-WCP-02.md` (stage 1, used as the map).
Yardstick: `raw/conv-webui.md` (final rule ids C3-S*, C3-I*, C3-N*). No `apertar-conventions.md` yet.

| Item | Value |
| --- | --- |
| Refs | `P:n` = port `cinemate-port` `01f170c` (read from `git show cinemate-port:src/web/WebControlPage.cpp`). `U:n` = `upstream-1.6.0` `35dbe67` (`/home/user/wt/core-upstream`); U:1-4040 equals fork `main` |
| Labels | confirmed unless marked. No browser run: how a rule renders is probable |
| Scope | CSS only: Clip Browser `.pb-*` (P:1979-2503), Clip Viewer `.pbv-*` (P:2505-2944), config editor aids, Boot Config diff, Controls page and Hardware card, Remote controls, white selects, GPIO out, toast link (P:3086-3577, 3970-3980). Markup is WCP-03, script WCP-04+ |
| Cross-refs | WCP-03 F1 (overlay widget layer, markup side), F2 (Boot Config), F3 (per-row media actions), F5 (`hidden` attribute, markup side) |

## 1. Findings

| Id | Sev | Cat | Title | Deliberate |
| --- | --- | --- | --- | --- |
| WCP-02-F1 | major | mismatch | Clip Browser and Viewer bring a second button and dialog set (touch-UI look) instead of the WebUI's own parts | yes |
| WCP-02-F2 | major | mismatch | White dropdowns in Controls and Hardware, scoped by panel and id, "like CineMate's web GUI" | yes |
| WCP-02-F3 | minor | mismatch | Upstream `.media-browser-*` rules renamed to abbreviated `.pb-*` / `.pbv-*` with identical bodies | yes (planned, not weighed) |
| WCP-02-F4 | minor | mismatch | Nine `@media` blocks placed beside their components, at 1119/719/419 px and `min-width`, not in upstream's end-of-sheet 1120/720/420 blocks | no |
| WCP-02-F5 | minor | mismatch | Attribute and id selectors (`[hidden]`, `[data-panel]`, `[data-used]`, `[data-output]`, `[data-ladder-lock]`, `#hardwareDevices`, `#remoteControlsRows`); upstream CSS has none | no |
| WCP-02-F6 | minor | slop | 11 CSS comments: T49, T50, "CineMate", two that no longer match the code | no |
| WCP-02-F7 | minor | bug | A newly added GPIO in row gets a white pin dropdown; saved rows get dark ones | no |
| WCP-02-F8 | minor | removed-upstream-behaviour | Media list facts and always-visible tools gone with the 36 removed rules | yes |
| WCP-02-F9 | nit | slop | Two rules and one selector with no element (`.controls-output-item`, `.controls-output-title`) | no |
| WCP-02-F10 | nit | duplication | `body.pb-open` twice; eight `.x.hidden { display: none }` rules repeat the global `.hidden` | no |

### WCP-02-F1. Second widget set in the playback overlay (major, mismatch)

- Port: own buttons `.pb-top-button, .pb-show-button` (P:2061-2094: pill radius 999px, 48 px, `rgba(255,255,255,0.06)`), `.pbv-icon-button, .pbv-info-button` (P:2657-2678), round transport `.pbv-circle` (P:2743-2775), toggle chip `.pb-chip` (P:2167-2178), pop-up menu `.pb-menu` (P:2103-2139), modal `.pb-scrim` + `.pb-dialog` (P:2398-2450). Accent cyan `#3fd0ff` / `#79ddff` for active and chip (P:2092, 2100, 2137-2138, 2171-2173): "`.pb-menu button.active { background: rgba(63, 208, 255, 0.12); color: #79ddff; }`".
- Apertar way: C3-I12 button variants `.primary-button`, `.secondary-button`, `.danger-button` (U:1632-1706, 50 px, radius 18 px) and `.icon-button` (U:194-215, 44 px, radius 18 px). C3-I8: "white for selected" - `.media-filter-button.active { background: #f4f4f5; color: #09090b; }` (U:1238-1242), `.pill-button.active` (U:783-788). The upstream overlay reused page parts: `<button class="icon-button settings-back-button" id="closeMediaBrowserButton">` and `<h2 class="section-title">` (U:3979-3995), and shared its phone rules with `.settings-overlay` / `.settings-shell` (U:2071-2080). Upstream CSS has no dialog, modal or scrim rule; destructive asks are `window.confirm` (C3-N3, U:10385, 10434). Cyan exists once, only for the standby button (U:1664-1668).
- Why: the overlay reads as the touch UI's QML ported into the WebUI. The original developer finds 110 rules that restyle buttons, selection and dialogs a second way; a change to `.secondary-button` or `.icon-button` no longer reaches the playback screens.
- Rework (CSS side; markup and script in WCP-03 F1):
  - Top buttons (Refresh, Show, Back) and viewer Info/Download: `class="icon-button"` / `secondary-button` with `<img class="icon-image">`. Delete `.pb-top-button`, `.pb-show-*`, `.pbv-icon-button`, `.pbv-info-button`.
  - SHOW menu: the four categories as the upstream row (a `pill-grid` or `.media-filter-button` row, active = white). Delete `.pb-menu*`.
  - Newest/Oldest: `select.settings-select` as upstream `media-sort-select` (U:1244-1253). Delete `.pb-chip`.
  - Remove dialog: `window.confirm`. Delete `.pb-scrim`, `.pb-dialog*`.
  - Transport: keep one round play button if wanted, but base it on `.icon-button` sizes; selected/active states white, not cyan.
  - Keep: grid, card, thumb, pills, badge, stage, scrub, histogram, metadata panel (`.pb-grid`, `.pb-card*`, `.pbv-stage`, `.pbv-scrub`, `.pbv-hist`, `.pbv-meta*`): no upstream WebUI part does these jobs.
- Effort M. Deliberate: yes. `bc12c0a` "the Clip Browser, in the touch UI's shape (T49)"; `working/playback/design-playback.md:568` B23 "the old `window.confirm` is removed"; design tables mark each part "same" as the touch UI.

### WCP-02-F2. White dropdowns scoped by panel (major, mismatch)

- Port: P:3484-3559, ten rules. "`/* The GPIO and hardware dropdowns ... are white and dark-texted, like CineMate's web GUI, so they are easy to see. Every other dropdown keeps the dark look. */`" then `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select { background-color: var(--select-bg); color: var(--select-fg); ... color-scheme: light; }`. A second exception turns the pin dropdowns dark again: `[data-panel="controls"] .settings-select.controls-pin-select { background-color: rgba(9, 9, 11, 0.72); ... color-scheme: dark; }` (P:3526-3559). New tokens `--select-bg`, `--select-fg` (P:35-36, WCP-01).
- Apertar way: one `.settings-select` look for every select (U:1519-1555, `:disabled` U:1603-1609). C3-I8 "dark zinc vocabulary"; violation example "A light theme, new colour system". Upstream CSS scopes no rule by panel (0 attribute selectors, 0 id selectors in U:15-2420).
- Why: three looks for one control class in one panel, driven by a Cinemate preference. It already went wrong once (F7). A maintainer changing `.settings-select` has to know about two override layers.
- Rework: delete P:3484-3559 and the two tokens; drop `controls-pin-select` from `buildControlsPinSelect` (P:17348). If the dark select is hard to read, change `.settings-select` for the whole page in one upstream-candidate commit, not per panel.
- Effort S. Deliberate: yes (`d44b177` message "WebUI: the GPIO and hardware dropdowns are white (the others stay dark)"; fork-log:138).

### WCP-02-F3. Abbreviated class family, renamed upstream rules (minor, mismatch)

- Port: `.pb-overlay` (P:1984-2002) is upstream `.media-browser-overlay` (U:1122-1140) with the same declarations; `.pb-shell` (P:2004-2016) is `.media-browser-shell` (U:1142-1154) with width 1320 px. The script still uses upstream names: `state.mediaBrowserOpen` toggles `pb-open` (P:10120); the opener is upstream `#mediaBrowserButton`.
- Apertar way: C3-I6 classes kebab-case in full words with a region prefix (`media-browser-*`, `settings-*`, `preset-*`); no abbreviations like `pb`/`pbv` in U:15-2420.
- Why: the diff shows the original developer's overlay rules deleted and re-added under a two-letter prefix, so the real change (shell size) is hidden; JS and CSS now use two names for one overlay.
- Rework: keep `.media-browser-overlay`, `.media-browser-shell` (change only width/height in place); name the new parts `media-browser-*` (grid, card, sheet) and `clip-viewer-*` for the viewer. Mechanical rename with the markup and script (WCP-03, WCP-04+).
- Effort S (search and replace over three slices). Deliberate: planned (`design-playback.md:1044` "`.pb-*` rules"), no reason recorded for leaving upstream names.

### WCP-02-F4. Media queries beside components, off-by-one breakpoints (minor, mismatch)

- Port: nine blocks inside the slice: `@media (max-width: 1119px)` P:2452, 2879; `(max-width: 719px)` P:2458, 2894; `(max-width: 419px)` P:2499; `(min-width: 1120px)` P:2865; `(max-height: 499px) and (orientation: landscape)` P:2929; `(max-width: 720px)` P:3439, 3569.
- Apertar way: C3-I10/I8 "4 fixed breakpoints ... one block each, at the end of the stylesheet": U:2034 `(max-width: 1120px)`, U:2062 `(max-width: 720px)`, U:2190, 2319, U:2391 `(max-width: 420px)`. `max-width` only. The overlay's phone rules lived in the 720 block (U:2071-2080). The contributor's own design said so: `design-playback-v1.md:1242` C7 "Apertar style: one set of breakpoints".
- Why: at exactly 720 px (and 1120, 420) the settings overlay is in phone layout while the playback overlay is not (`max-width: 719px` vs `720px`). Eleven extra blocks scattered through the sheet.
- Rework: move each block's rules into upstream's end blocks: 1119 -> `(max-width: 1120px)`, 719 -> `(max-width: 720px)`, 419 -> `(max-width: 420px)`; write the `min-width: 1120px` rules as the base and undo them in the 1120 block; move the Controls 720 rules into the 720 block. The landscape block has no precedent; keep it as one block at the end.
- Effort S. Deliberate: no (contradicts the design note).

### WCP-02-F5. Attribute and id selectors (minor, mismatch)

- Port: `[hidden]` P:3137, 3184-3185, 3266, 3575; `[data-panel="controls"]` P:3486-3559; `[data-used]` P:3542; `[data-output]` P:3364; `[data-ladder-lock] select:disabled` P:3978; ids `#hardwareDevices` P:3487-3515, `#remoteControlsRows .pill-button` P:3420.
- Apertar way: 0 attribute selectors and 0 id selectors in U:15-2420 (grep). Hiding is the class `.hidden { display: none !important; }` U:1975 (C3-I8 "non-applicable controls `.hidden`"); states are classes (`active`, `selected`, `disabled`).
- Rework: `[hidden]` rules go with WCP-03 F5 (`classList.toggle("hidden", ...)`). `[data-output]` -> class `controls-row output`; `[data-used]` -> option class `used`; `#remoteControlsRows .pill-button` -> class `remote-pill` on the pills; `[data-panel]`/`#hardwareDevices` disappear with F2. `[data-ladder-lock] select:disabled { pointer-events: none }` -> class `ladder-locked` set beside the data attribute.
- Effort S. Deliberate: no.

### WCP-02-F6. Comments in the CSS (minor, slop)

- Port: 11 comments. "`/* Playback (T49): the touch UI's Clip Browser, in the WebUI's shell. */`" P:1979; "`/* Playback (T50): the Clip Viewer. */`" P:2505; "like CineMate's web GUI" P:3484-3485. Two are wrong: P:3561 "`GPIO out: pin | function | active | Test`" while the grid holds function, active, Test, Remove (pin is in the row head, P:17841-17916); P:3525 "The pin dropdowns (GPIO in rows, GPIO out rows) keep the page's normal dark look" does not hold for new rows (F7).
- Apertar way: C3-I7 "Do not add comments, banners or JSDoc to the page" (0 `/*` in U:15-2420).
- Rework: delete all 11. If one must stay, the inline note at P:3320 (why `justify-content: flex-end`) is the only reason-type one; drop it too to match upstream.
- Effort S. Deliberate: no.

### WCP-02-F7. New row's pin dropdown is white (minor, bug)

- Port: dark pin rules need `.controls-pin-select` (P:3526-3559). `buildControlsPinSelect` sets `"settings-select controls-pin controls-pin-select"` (P:17348); the new-row builder sets `"settings-select controls-pin"` (P:17453), so the white rule P:3486 applies.
- Failing input: Settings, Controls, "+ Add GPIO button": the new row's pin dropdown(s) are white, every saved row's pin dropdown is dark. After Save and reload the same pin turns dark. Class names confirmed; render probable.
- Rework: none needed once F2 removes the white look. If F2 is not taken: add `controls-pin-select` at P:17453.
- Effort S. Deliberate: no.

### WCP-02-F8. Media list facts and tools gone with the removed rules (minor, removed-upstream-behaviour)

- Upstream: 36 rules U:1122-1431 styled a list with, per row, stat pills (frames or files, duration, fps, size; `.media-stat` U:1402-1416), "Updated ..." (`.media-row-detail`), Download and Delete (`.media-row-actions` U:1418-1431), plus four filter buttons and a selection bar always in view (U:1203-1292). Selected row cyan border (U:1353).
- Port: the card shows duration (and DROP) only (`.pb-pill.duration`, `.pb-pill.drop` P:2311-2319); fps and frame count are in the viewer, file size only in the download question; the filters are behind SHOW (P:2103); the selection bar shows only after a long press (`.pb-selection-actions.hidden` P:2191). Inventory 6b.
- Why: an operator who used the WebUI to check sizes before downloading over Wi-Fi loses that at a glance.
- Rework: add the size text to the card foot (`.pb-foot`, P:2355) as a `.pb-fmt`-style line, and the fps beside the format; per-row actions and Clear per WCP-03 F3. Filters per F1 (visible row).
- Effort S. Deliberate: yes (`bc12c0a` "the WebUI's media list was rows with Download and Delete; the touch UI's Clip Browser is a grid of cards").

### WCP-02-F9. Rules with no element (nit, slop)

- Port: `.controls-output-item` P:3292-3295, `.controls-output-title` P:3297-3301, selector `.controls-output-item.undetected` P:3288. No such class in markup or script (grep over the file: only these CSS lines).
- Rework: delete them (11 lines).

### WCP-02-F10. Repeated rules (nit, duplication)

- Port: `body.pb-open { overflow: hidden; }` at P:69 (beside `body.settings-open`, the upstream place) and again at P:1980-1982. `.pb-page.hidden, .pb-viewer.hidden`, `.pb-menu.hidden`, `.pb-selection-actions.hidden`, `.pb-scrim.hidden`, `.pbv-badge.hidden`, `.pbv-hole.hidden`, `.pbv-hold.hidden`, `.pbv-hold-buttons .hidden` (P:2027, 2119, 2191, 2409, 2568, 2582, 2596, 2629) all set `display: none`, which the global `.hidden { display: none !important; }` (U:1975, P:3943) already does.
- Upstream has one such repeat (`.settings-card.hidden` U:1971). Rework: delete P:1980-1982 and the eight rules.

## 2. Checked and not reported

| Item | Why not |
| --- | --- |
| Literal `#27272a` 6 times beside `var(--card-border)` | Upstream mixes too: 36 `var(` vs 130 hex (C3-I8 "literals dominate") |
| Red selection on cards (P:2261-2264, 2341-2345) | Reuses the `.danger-button` tint; selection means "to be removed". Taste |
| Toast link `.toast.with-link`, `.toast .ladder-link` (P:3970-3976) | Small state on the upstream toast, after its base rule. `showToast` clears `with-link` (P:12994), so an invisible toast never catches clicks |
| `.config-editor-wrap .config-editor` (P:3114) and `.settings-action-row[hidden]` placed beside upstream rules | Extend in place; the `[hidden]` part is in F5 |
| Board or Pi-model assumptions | None in any added declaration (inventory 9) |
| Protocol, security | CSS only: no route, command, file or helper |
| GPIO chip field (owner request) | No CSS needed: a `text` chip field uses `.settings-input` in `.controls-settings` (inventory 10). Already reinstated on the improvement branch |

## 3. Abstraction verdicts

| Abstraction (inventory 5) | Verdict | Reason |
| --- | --- | --- |
| `.pb-*` Clip Browser family | rework-to-upstream-pattern | Keep the grid and card. Buttons, menu, chip, dialog to upstream parts (F1); names to `media-browser-*` (F3); phone rules to the end blocks (F4) |
| `.pbv-*` Clip Viewer family | rework-to-upstream-pattern | Stage, scrub, histogram, metadata are new ground with the touch UI as model (C3-N5) and stay. Buttons to `.icon-button`/`secondary-button`, prefix `clip-viewer-*` |
| `.pb-scrim` + `.pb-dialog` modal | rework-to-upstream-pattern | `window.confirm` (C3-N3, U:10385, 10434) |
| `.pb-menu` pop-up | rework-to-upstream-pattern | Visible filter row as upstream (U:1203-1242) |
| `.pb-chip` sort toggle | rework-to-upstream-pattern | `settings-select` as upstream `.media-sort-select` |
| `.config-editor-wrap` + `.config-gutter` | keep | Line numbers for an editor whose errors cite line numbers; extends upstream `.config-editor` in place; same monospace stack (U:1567) |
| `.config-diff` + `.diff-*` | keep | Review before save; no upstream part does it. `.diff-note`, `.diff-confirm`, `.diff-managed` follow the Boot Config verdict (WCP-03 F2) |
| `.config-issues` (+ `.info`) | keep | A list with line numbers cannot be a toast. Use the `.hidden` class (F5) |
| `.controls-*` family | keep | Controls page is new ground (WCP-03 F10/F11). Delete dead rules (F9), selectors to classes (F5) |
| `.controls-settings` auto-fill grid | simplify | Use upstream `.settings-field-grid` (U:1494-1498, two columns) unless a device has more fields than two columns hold well; then keep and say so |
| `.action-chips` with drag reorder | simplify | No drag anywhere upstream. HTML5 drag (P:16840-16850) is unreliable on phone browsers (probable; unconfirmed, settle with a phone). Order by add order, or two small arrow buttons |
| Container-scoped select look, `--select-bg`/`--select-fg` | rework-to-upstream-pattern | Delete (F2) |
| Attribute selectors in CSS | rework-to-upstream-pattern | Classes (F5) |
| Toast that takes clicks | keep | Smallest extension of the upstream toast; selector `[data-ladder-lock]` to a class (F5) |
| `@media` beside components | rework-to-upstream-pattern | End-of-sheet blocks, upstream breakpoints (F4) |
| CSS comments | rework-to-upstream-pattern | Delete (F6) |

## 4. Conforms

- 589 upstream lines of this range kept byte for byte (P:1969-1978, 2946-3085, 3446-3483, 3579-3969, 3982-3991). `.config-editor`, `.settings-select`, `.settings-action-row`, `.toast` untouched; additions follow their base rule (inventory 4).
- Tokens used where upstream has them: `var(--card-border)`, `--muted`, `--surface*`, `--radius-*`; other colours are zinc literals as upstream (C3-I8).
- Reuse of upstream parts: `.danger-button`/`.primary-button`/`.secondary-button` in the selection bar (P:2195-2201), `.preset-action` in the Scan line (P:3251), `.field-stack`, `.settings-select`, `.settings-input` in the settings grid, `.pill-button`/`.pill-grid` for Remote controls (P:3420).
- Overlay keeps upstream's `z-index: 84`, backdrop and fade (P:1984-2002 = U:1122-1140); no `!important` added.
- Class names kebab-case with `active`/`selected`/`hidden`/`disabled`/`changed` states (C3-I6), apart from the prefix in F3.
- Controls blocks use upstream's 720 px breakpoint (P:3439, 3569).
- Monospace stack copied from upstream `.config-editor` (U:1567).
- No board-specific value in any declaration.

## Skeptic

Stage 3. Port read from `git show cinemate-port:src/web/WebControlPage.cpp` (`01f170c`), upstream from `/home/user/wt/core-upstream` (`upstream-1.6.0`). Every verdict re-read in code.

| Id | Verdict | Why |
| --- | --- | --- |
| WCP-02-F1 | corrected | Lines and cyan confirmed. "110 rules" is wrong: 28 of the 136 `.pb-*`/`.pbv-*` rules are the second button/menu/chip/dialog set. The dialog's own buttons already use upstream `.secondary-button`/`.danger-button` (P:6482-6483), only scrim and card are new. The port itself still asks with `window.confirm` for Download (P:12914), GPIO replace (P:17317) and more, so the modal is also inconsistent inside the port |
| WCP-02-F2 | stands | P:3484-3559 and tokens P:35-36 confirmed; upstream `.settings-select` one look (U:1519-1555, U:1603-1609); no attribute or id selector in U:15-2420. Deliberate per `d44b177` body ("the GPIO and hardware dropdowns are white (the others stay dark)") |
| WCP-02-F3 | stands | `.pb-overlay` body = `.media-browser-overlay` (U:1122-1140) byte for byte after the rename; `.pb-shell` differs only in size/position/border token. Also `body.media-browser-open` (U:66) became `body.pb-open` (P:69) while JS keeps `state.mediaBrowserOpen` (P:10117-10120) |
| WCP-02-F4 | corrected | Nine blocks confirmed. Upstream has five end blocks (1120, 720, 480, 560, 420; U:2034, 2062, 2190, 2319, 2391), not four. Deliberate is not "no": design-playback.md:558 B13 writes the grid as "< 720 px 2, 720-1119 px 3, >= 1120 px 4", so 719/1119 were chosen on purpose, but against upstream's inclusive `max-width: 720px`; the placement beside components was never discussed (49.1 at :1044 only says "breakpoints 1120 / 720 / 420"). Set to unknown |
| WCP-02-F5 | stands | All nine selectors confirmed at the cited lines; U:15-2420 has 0 `[` and 0 id selectors. Upstream JS sets `option.hidden` once (U:9526), never in CSS |
| WCP-02-F6 | corrected | 11 comments confirmed (P:1979, 2505, 3107, 3320, 3341, 3377, 3413, 3484, 3525, 3541, 3561); 3 of them carry T49/T50/CineMate, not all 11. Both stale comments confirmed: P:3561 grid holds function, active, Test, Remove (P:17858-17917); P:3525 false for new rows (F7). Upstream 0 `/*` |
| WCP-02-F7 | stands | P:17348 vs P:17453 confirmed; unsaved rows always come from `buildControlsNewRow` (P:17803), so they stay white until Save+reload. Render probable (no browser run) |
| WCP-02-F8 | stands | Upstream stat pills with size (U:7743-7757, `.media-stat` U:1402-1416); port shows size only in the Download confirm (P:12914). Deliberate per `bc12c0a` body. Markup/script side overlaps WCP-03 F3 |
| WCP-02-F9 | stands | `.controls-output-item`, `.controls-output-title` appear only at P:3288-3301 |
| WCP-02-F10 | stands | P:69 and P:1980-1982 both set `body.pb-open { overflow: hidden }`; eight `.x.hidden { display: none }` at the cited lines; global `.hidden` at P:3943 |

## Final findings

### WCP-02-F1 [mismatch, major] Clip Browser and Viewer bring a second button/menu/chip/dialog set in the touch-UI look instead of the WebUI's own parts
- Where: src/web/WebControlPage.cpp:2061-2094, 2103-2178, 2398-2450, 2657-2678, 2743-2775@cinemate-port
- Port way: 28 of the 136 `.pb-*`/`.pbv-*` rules form an own widget set: `.pb-top-button`/`.pb-show-button` (pill radius 999px, 48 px), `.pbv-icon-button`/`.pbv-info-button`, round transport `.pbv-circle` (52 px, 999px), toggle chip `.pb-chip`, pop-up `.pb-menu`, modal `.pb-scrim` + `.pb-dialog`; active/selected cyan (`.pb-menu button.active { background: rgba(63, 208, 255, 0.12); color: #79ddff; }`). The dialog's buttons themselves reuse `.secondary-button`/`.danger-button` (P:6482-6483).
- Apertar way: `.primary-button`/`.secondary-button`/`.danger-button` U:1632-1706 (50 px, radius 18) and `.icon-button` U:194-215 (44 px, radius 18); selected = white (`.media-filter-button.active { background: #f4f4f5; color: #09090b; }` U:1238-1242); the old overlay reused `icon-button settings-back-button` and `h2.section-title` (U:3979-3995); no dialog/scrim/modal rule in U:15-2420; destructive asks via `window.confirm` (U:10385, 10434, 10672 and five more). Cyan only on the standby button (U:1664-1668).
- Why it matters: the overlay reads as QML transplanted into the WebUI; a change to `.icon-button` or selection colours no longer reaches playback. The port is inconsistent with itself too: Download (P:12914) and GPIO replace (P:17317) still use `window.confirm`, Remove uses a modal.
- Rework: Refresh/Show/Back and viewer Info/Download -> `icon-button` / `secondary-button` with `img.icon-image`; delete `.pb-top-button`, `.pb-show-*`, `.pbv-icon-button`, `.pbv-info-button`. SHOW menu -> visible filter row like `.media-filter-button` (active white); delete `.pb-menu*`. Newest/Oldest chip -> `select.settings-select` like `media-sort-select` (U:1244-1253); delete `.pb-chip`. Remove dialog -> `window.confirm` with the same text (count, first name, "cannot be undone"); "Removing..." goes to the status line; delete `.pb-scrim`, `.pb-dialog*`. Transport sized from `.icon-button`, active white. Keep grid, card, thumb, pills, stage, scrub, histogram, metadata. Markup/script side in WCP-03 F1.
- Effort: M. Deliberate: yes (`bc12c0a` "the Clip Browser, in the touch UI's shape (T49)"; design-playback.md:568 B23 "the old `window.confirm` is removed").

### WCP-02-F2 [mismatch, major] White dropdowns scoped by panel and id, with a dark exception for pin selects
- Where: src/web/WebControlPage.cpp:3484-3559, 35-36, 17348@cinemate-port
- Port way: `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select { background-color: var(--select-bg); color: var(--select-fg); ... color-scheme: light; }` with the comment "like CineMate's web GUI"; then `[data-panel="controls"] .settings-select.controls-pin-select` turns pin selects dark again. New tokens `--select-bg`, `--select-fg`.
- Apertar way: one `.settings-select` look everywhere (U:1519-1555, `:disabled` U:1603-1609); no panel- or id-scoped rule in U:15-2420 (C3-I8: violation "a light theme, new colour system").
- Why it matters: three looks for one control class in one panel, from a Cinemate preference; already produced F7; a maintainer editing `.settings-select` must know two override layers.
- Rework: delete P:3484-3559 and the two tokens; drop `controls-pin-select` from `buildControlsPinSelect` (P:17348). If readability is the problem, change `.settings-select` page-wide in a separate upstream-candidate commit.
- Effort: S. Deliberate: yes (`d44b177` body "WebUI: the GPIO and hardware dropdowns are white (the others stay dark)"; fork-log:138).

### WCP-02-F3 [mismatch, minor] Upstream `.media-browser-*` rules renamed to abbreviated `.pb-*`/`.pbv-*`
- Where: src/web/WebControlPage.cpp:1984-2016, 69, 10120@cinemate-port
- Port way: `.pb-overlay` = `.media-browser-overlay` declarations unchanged; `.pb-shell` = `.media-browser-shell` with width 1320 px, full height, `position: relative`, `var(--card-border)`; `body.media-browser-open` became `body.pb-open`; script keeps `state.mediaBrowserOpen` and `#mediaBrowserButton`.
- Apertar way: full-word kebab-case region prefixes: `.media-browser-overlay` U:1122, `.media-browser-shell` U:1142, `body.media-browser-open` U:66, `settings-*`, `preset-*` (C3-I6).
- Why it matters: the diff shows the original developer's overlay deleted and re-added under a two-letter prefix, hiding the real change (shell size); one overlay has two names across CSS and JS.
- Rework: keep `.media-browser-overlay`/`.media-browser-shell`/`body.media-browser-open`, change only size in place; name new parts `media-browser-*` and `clip-viewer-*`; same rename in markup (WCP-03) and script.
- Effort: S. Deliberate: yes (design-playback.md:1044 plans "`.pb-*` rules"; no reason recorded for dropping upstream names).

### WCP-02-F4 [mismatch, minor] Media queries beside components at 1119/719/419 px and min-width, not in upstream's end blocks
- Where: src/web/WebControlPage.cpp:2452, 2458, 2499, 2865, 2879, 2894, 2929, 3439, 3569@cinemate-port
- Port way: nine `@media` blocks inside the component sections: `max-width` 1119 (x2), 719 (x2), 419, `min-width: 1120px`, `(max-height: 499px) and (orientation: landscape)`, `max-width: 720px` (x2, Controls).
- Apertar way: one block per breakpoint at the end of the sheet, `max-width` only: U:2034 (1120), U:2062 (720), U:2190 (480), U:2319 (560), U:2391 (420); the overlay's phone rules sit in the 720 block (U:2071-2080).
- Why it matters: at exactly 720/1120/420 px the settings overlay and the playback overlay take different layouts; blocks scattered through the sheet.
- Rework: move rules into upstream's end blocks (1119 -> 1120, 719 -> 720, 419 -> 420); write the `min-width: 1120px` rules as base and undo them in the 1120 block; Controls 720 rules into the 720 block; the landscape block as one block at the end.
- Effort: S. Deliberate: unknown (design-playback.md:558 B13 chose "< 720 / 720-1119 / >= 1120" on purpose, reading upstream's boundary as exclusive; design-playback-v1.md:1242 C7 asks for "the WebUI's own 720 / 1120"; placement never discussed).

### WCP-02-F5 [mismatch, minor] Attribute and id selectors in CSS where upstream uses classes only
- Where: src/web/WebControlPage.cpp:3137, 3184-3185, 3266, 3364, 3420, 3542, 3575, 3978@cinemate-port
- Port way: `[hidden]` x5, `[data-panel]`, `[data-used]`, `[data-output]`, `[data-ladder-lock] select:disabled`, `#hardwareDevices`, `#remoteControlsRows .pill-button`.
- Apertar way: 0 attribute and 0 id selectors in U:15-2420; hiding via `.hidden { display: none !important; }` (U:1975); states as classes (C3-I6, C3-I8).
- Why it matters: a second hiding mechanism and per-element patches; the original developer's `.hidden` habit no longer covers every element.
- Rework: `[hidden]` rules go with WCP-03 F5 (`classList.toggle("hidden", ...)`); `[data-output]` -> class `output`; `[data-used]` -> option class `used`; `#remoteControlsRows .pill-button` -> class `remote-pill`; `[data-ladder-lock]` -> class `ladder-locked`; panel/id scoping disappears with F2.
- Effort: S. Deliberate: no.

### WCP-02-F6 [slop, minor] 11 CSS comments, 3 with T49/T50/CineMate, 2 no longer true
- Where: src/web/WebControlPage.cpp:1979, 2505, 3107, 3320, 3341, 3377, 3413, 3484-3485, 3525, 3541, 3561@cinemate-port
- Port way: "`/* Playback (T49): the touch UI's Clip Browser, in the WebUI's shell. */`", "`/* Playback (T50)`", "like CineMate's web GUI"; P:3561 says "pin | function | active | Test" but the grid holds function | active | Test | Remove (P:17858-17917); P:3525 "pin dropdowns keep the page's normal dark look" is false for new rows (F7).
- Apertar way: no CSS comments, 0 `/*` in U:15-2420 (C3-I7).
- Why it matters: internal tutorial numbers and a foreign product name in the original developer's file; stale comments mislead.
- Rework: delete all 11.
- Effort: S. Deliberate: no.

### WCP-02-F7 [bug, minor] Newly added GPIO in row gets a white pin dropdown, saved rows dark
- Where: src/web/WebControlPage.cpp:3526-3559, 17453, 17348, 17803@cinemate-port
- Port way: dark pin rules key on `.controls-pin-select`; `buildControlsPinSelect` sets it (P:17348); `buildControlsNewRow` sets only `"settings-select controls-pin"` (P:17453), and every unsaved row is built by it (P:17803), so the white rule P:3486 applies.
- Apertar way: no precedent.
- Why it matters: Settings > Controls > "+ Add GPIO button": the new row's pin select is white, saved rows dark; it turns dark after Save and reload. Class names confirmed, render probable.
- Rework: vanishes with F2; otherwise add `controls-pin-select` at P:17453.
- Effort: S. Deliberate: no.

### WCP-02-F8 [removed-upstream-behaviour, minor] Media list facts and always-visible tools removed with the 36 upstream rules
- Where: src/web/WebControlPage.cpp:2298-2319, 2355-2396, 2191-2193@cinemate-port
- Port way: card shows duration and DROP only; fps/frames only in the viewer; size only in the Download confirm (P:12914); filters behind the SHOW menu; selection bar hidden until an 800 ms press.
- Apertar way: per-row stat pills frames/duration/fps/size (`.media-stat` U:1402-1416, built U:7743-7757), "Updated" time (`.media-row-detail` U:1388), Download/Delete (`.media-row-actions` U:1418-1431), filter buttons and selection bar always visible (U:1203-1292).
- Why it matters: the operator loses file size and fps at a glance before downloading over Wi-Fi; one tap more to filter.
- Rework: add size and fps to the card foot (`.pb-foot`, a line like `.pb-fmt`); visible filter row per F1; per-row actions and Clear per WCP-03 F3.
- Effort: S. Deliberate: yes (`bc12c0a` "the WebUI's media list was rows with Download and Delete; the touch UI's Clip Browser is a grid of cards").

### WCP-02-F9 [slop, nit] Rules with no element: `.controls-output-item`, `.controls-output-title`
- Where: src/web/WebControlPage.cpp:3288-3301@cinemate-port
- Port way: selector `.controls-output-item.undetected` (P:3288) and two rules (P:3292-3301) used nowhere in markup or script.
- Apertar way: no precedent.
- Why it matters: dead CSS from the `d44b177` squash.
- Rework: delete the P:3288 selector and P:3292-3301.
- Effort: S. Deliberate: no.

### WCP-02-F10 [duplication, nit] `body.pb-open` twice; eight `.x.hidden` rules repeat global `.hidden`
- Where: src/web/WebControlPage.cpp:69, 1980-1982, 2027, 2119, 2191, 2409, 2568, 2582, 2596, 2629@cinemate-port
- Port way: `body.pb-open { overflow: hidden }` at P:69 and P:1980; `.pb-page.hidden, .pb-viewer.hidden`, `.pb-menu.hidden`, `.pb-selection-actions.hidden`, `.pb-scrim.hidden`, `.pbv-badge.hidden`, `.pbv-hole.hidden`, `.pbv-hold.hidden`, `.pbv-hold-buttons .hidden` set `display: none`, already done by global `.hidden` (P:3943).
- Apertar way: global `.hidden { display: none !important; }` U:1975; one repeat upstream (`.settings-card.hidden` U:1971).
- Why it matters: noise.
- Rework: delete P:1980-1982 and the eight rules.
- Effort: S. Deliberate: no.
