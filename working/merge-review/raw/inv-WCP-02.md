# Inventory WCP-02: WebControlPage.cpp, CSS slice 2 (port lines 1969-3991)

Stage 1 of 3: inventory. Facts only, no verdicts. Written 2026-11-17.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/WCP.part02.diff`: 1697 lines, 4 hunks, read whole. Equal to lines 1013-2705 of `git -C /home/user/Apertar-Core diff --minimal -U10 origin/main cinemate-port -- src/web/WebControlPage.cpp` (`diff`: exit 0) |
| Port file | `/home/user/Apertar-Core/src/web/WebControlPage.cpp` @cinemate-port `01f170c`, lines 1969-3991. The task names 1969-3960: hunk 4 starts at 3960 and ends at 3991. Evidence was read from `git show cinemate-port:<path>` copies, so the line numbers hold if the shared checkout moves. At the time of reading the working tree file was equal to `cinemate-port` (`cmp`: exit 0) |
| Original | `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0 `35dbe67`, lines 1112-2011 |
| Merge target | `/home/user/wt/core-main/src/web/WebControlPage.cpp` @main `f60e301`: lines 1-4040 byte-identical to upstream (`diff`: exit 0). Every `U:` line below holds @main too |
| Content | CSS only. The `<style>` block is U:15-2420 and P:15-4393. The slice holds no HTML, no JavaScript, no C++ |
| Size | git `--minimal`: +1300 / -177. By position: 1434 lines inserted in four blocks (P:1979-2945, 3086-3445, 3484-3578, 3970-3981) and 311 upstream lines removed in one block (U:1122-1432). Net +1123 either way |
| Kept verbatim | P:1969-1978 = U:1112-1121. P:2946-3085 = U:1433-1572. P:3446-3483 = U:1573-1610. P:3579-3969 = U:1611-2001. P:3982-3991 = U:2002-2011. Five `diff` runs, exit 0 |
| Counts | 182 rules, 9 `@media` blocks, 11 comments (10 on their own lines, 1 inline at P:3320) in the inserted blocks. 36 upstream rules removed |
| Shorthand | `P:n` = port file line @cinemate-port. `U:n` = upstream file line @upstream-1.6.0 (= @main). `App:n` = `src/ApertarCoreApp.cpp` @cinemate-port. `UApp:n` = the same file @upstream-1.6.0. `CM:n` = `src/hardware/ControlsModel.hpp` @cinemate-port. `fork-log:n` = `/home/user/apertar-kb/fork-log.md` line n |
| Labels | confirmed = read in code. probable = inferred, reason given. unconfirmed = not settled here, command given. A row without a label is confirmed |
| Not done | No browser run. How a rule looks on screen is unconfirmed. Settle: start Core with `--simulate`, open port 8000 in headless Chrome, screenshot |

Blame command: `git -C /home/user/Apertar-Core blame -s -L <a>,<b> cinemate-port -- src/web/WebControlPage.cpp` over each inserted block.
`git log -L <a>,<b>:src/web/WebControlPage.cpp origin/main..cinemate-port` over the same blocks lists the same commits.
17 port commits wrote the slice (section 12).

## 1. The four hunks

| # | Old (U) | New (P) | Lines | What | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | 1112-1440 | 1969-2953 | +833 -177 | The media list overlay CSS goes (U:1122-1431, 36 rules). Playback CSS comes: Clip Browser `.pb-*` (P:1979-2503) and Clip Viewer `.pb-viewer`, `.pbv-*` (P:2505-2944) | `bc12c0a`, `27eac5a`, `4629de2` |
| 2 | 1563-1582 | 3076-3455 | +360 | After upstream `.config-editor`: editor gutter and diff box, Boot Config review lines, Controls page families, Hardware card lines, issues box, Remote controls | 12 commits, section 12 |
| 3 | 1601-1620 | 3474-3588 | +95 | After upstream `.settings-select:disabled`: white selects for the Controls panel and `#hardwareDevices`, dark pin selects, GPIO out field grid, `.settings-action-row[hidden]` | `d44b177`, `b64e6f6` |
| 4 | 1992-2011 | 3960-3991 | +12 | Between upstream `.toast.visible` and `.toast.error`: `.toast.with-link`, `.toast .ladder-link`, `[data-ladder-lock] select:disabled` | `392e812` |

Inserted lines per topic (blank lines included): Clip Browser 526 (P:1979-2504), Clip Viewer 441 (P:2505-2945),
editor gutter and diff box 89 (P:3086-3174), Controls review, Listen, chips, Scan 82 (P:3175-3256), issues box 22 (P:3257-3278),
Controls cards, rows, lines 134 (P:3279-3412), Remote controls 13 (P:3413-3425), add buttons and the 720px block 20 (P:3426-3445),
white and dark selects 77 (P:3484-3560), GPIO out fields 14 (P:3561-3574), hidden action row 4 (P:3575-3578), toast link 12 (P:3970-3981). Sum 1434.

## 2. Features that touch this slice

"Tested" quotes the commit message and the fork-log. That is intent, not proof (BRIEF rule 5).
"Lines" = lines the blame gives the commit inside this slice.

| Id | Feature | The operator gets | CSS here | Commits (lines) | Relation to upstream | Tested, as recorded |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Clip Browser in the WebUI (internal number T49) | The folder button opens a grid of cards: thumbnail, duration, dropped-frame count, name, format, shot date, timecode. A long press starts a selection: Remove Selected, Download Selected, Select All | P:1979-2503 | `bc12c0a` (401), `27eac5a` (5) | Replaces upstream code. U:1122-1431 is removed. `.pb-overlay` P:1984-2002 is `.media-browser-overlay` U:1122-1140 under a new name, declarations identical. `.pb-shell` P:2004-2016 is `.media-browser-shell` U:1142-1154 changed (section 4) | `bc12c0a`: "Tested: desk (headless Chrome against the Pi's Core, read-only); Pi build pending". `27eac5a`: "Tested: desk (headless Chrome, laptop and 390 px); Pi build". fork-log:101: "fork-only, Pi only; tested 2026-10-29 (headless Chrome against Core; live page served)" |
| F2 | Clip Viewer in the WebUI (T50) | A tap on a card plays the clip in the browser: picture on a canvas, play and pause, frame step, scrub bar, previous and next clip, histogram, clip metadata, Download, Remove | P:2505-2944 | `4629de2` (441) | Entirely new area in the WebUI. Upstream WebUI has no viewer. The upstream touch UI has one: `qml/ClipPlayerPage.qml` @upstream-1.6.0 in `/home/user/wt/ui-upstream` ("Clip Viewer" :234, "Clip Metadata" :729) | `4629de2`: "Tested: desk (headless Chrome against the Pi's Core, read-only): C0021 24 fps of 25, C0016 9 fps; Pi build pending". fork-log:102: "fork-only, Pi only; tested 2026-10-29 (24 fps Clear HDR 16-bit, 9 fps lossless; Patrik: works well)" |
| F3 | Config text editor aids (T38 part 2, T43) | In Settings, Config: line numbers beside the text, a Check button, a list of what Core found with line numbers, a diff before Save, a picker of saved versions | P:3086-3105, 3114-3143, 3167-3173, 3257-3277 | `8be1ab5` (part of 141), `effb804` (18), `d282de9` (`.config-issues.info`) | Extends an upstream function in place. The upstream card "Apertar Config" and its textarea stay (U:3840-3872, `.config-editor` U:1562-1571 = P:3075-3084). The textarea is wrapped (P:6222-6225) | `8be1ab5`: "Tested: desk (Chrome page test 60/60 against a mock)". `effb804`: "Tested: desk only (node --check on the page script, and the save function run against a mock fetch and page for five replies; not yet tried in a browser on the Pi)". fork-log:111, 130: "fork-only", no test recorded |
| F4 | Boot Config card (System panel) | A card that edits `/boot/firmware/config.txt`: Save shows the lines that change, notes and a tick box for a display change; View file and Edit file mark the lines the card sets in italics | P:3107-3112, 3144-3165. Reuses F3's `.config-diff`, `.config-gutter`, `.config-editor-wrap`, `.config-issues` (P:5868-5869, 5924, 5936-5941) | `8a56545` (16), `afa00e8` (7), `2a4266e` (7) | Entirely new area. Upstream has no config.txt editor. Upstream's System panel has the fan mode field (note U:3651) | `8a56545`, `afa00e8`: no "Tested:" line. `2a4266e`: "Tested: desk only (boot_config_test 75 checks, node --check, legend on the dev Pi's file)". fork-log:138 (merge `4581a69`): "Host tests, Pi build (libcamera ON and OFF), `--simulate` serving the WebUI ... Not yet run on the camera" |
| F5 | Controls page (Settings, Controls; T40-T43) | One card per detected device. Each button, switch, knob and pin is a row; each gesture is a line with a dropdown of actions. Add and Remove buttons, several actions as chips, a list of unsaved changes, Listen (the row of the control you press lights up), Try (run a line's saved action), Undo last save | P:3175-3236, 3279-3285, 3303-3309, 3328-3411, 3426-3444. Shares the issues box P:3257-3277 | `d282de9` (53), `fa3a798` (32), `8be1ab5` (part of 141), `166cc4d` (27), `1319967` (part of 30), `b74b4aa` (9), `f5fe41b` (5) | Entirely new area. Upstream edits the hardware file as text only (U:3840-3872) | `d282de9`: "Tested: pi (apertar.local) the page against the camera: rows match the file, a change to GPIO 10 wrote only that line ...; headless Chrome against a mock backend ...: 20 of 20 checks". `166cc4d`: "Tested: pi (apertar.local) the real chip and pins in get_controls; the page in Chrome against a mock: 26 of 26". `f5fe41b`: "desk only ... 33 of 33". `fa3a798`: "desk (Chrome page test 39/39 against a mock with switches)". `b74b4aa`: "desk (Chrome page test 43/43)". `8be1ab5`: "desk (Chrome page test 60/60 against a mock)". `1319967`: "pi (apertar.local) ... Try on the Controls card". fork-log:118-130, 148: "fork-only" |
| F6 | GPIO out row on the Controls page (tally light) | A row with a pin dropdown (None, GPIO n, PCF8574 pin n), function, active level, Test, Remove | P:3363-3364 (`[data-output]`), 3561-3573. P:3287-3301 was written for it and has no element (section 7) | `d44b177` (part of 109), `b64e6f6` (1) | Entirely new area on the page. The file section `[recording_indicator]` is upstream (UApp:4388-4399) | `d44b177`: "Not run yet: ... the Controls page ...; nothing opened in Resolve or a browser". `b64e6f6`: "Tested: desk only (headless page with the Controls fixture)". fork-log:149: "fork-only; on the Pi only" |
| F7 | Hardware card (Settings, Config) | Above the text editor: the I2C buses with a Scan button each, then every supported device with a state pill, greyed when not found, and its settings as fields. Save Hardware | P:3238-3255, 3279-3290, 3303-3326. Selects white by P:3486-3523 | `8be1ab5` (Scan, bus line), `166cc4d` (card, settings grid), `f5fe41b` (`.undetected`), `b74b4aa` (field alignment) | Entirely new area: a new card inside upstream's Config panel, above the upstream card (P:6172-6191) | `f5fe41b`: "Tested: desk only (headless Chrome against a mock with the live file's rows: 33 of 33)". `8be1ab5`: "desk (Chrome page test 60/60 against a mock)" |
| F8 | Remote controls card (main page) | Under Camera settings: pills that run what each saved button, switch position and knob does. A held arrow keeps turning | P:3413-3424 | `1319967` (part of 30) | Entirely new area. Reuses upstream `.select-block`, `.select-topline`, `.pill-grid`, `.pill-button` (U:698, 719; P:18054-18065) | `1319967`: "Tested: pi (apertar.local) Remote controls buttons and held knob turns, Try on the Controls card". fork-log:148: "fork-only; on the Pi only (another session, 2026-11-04 01:22)" |
| F9 | White dropdowns on Controls and Hardware | Every dropdown in the Controls panel and in the Hardware card is white with dark text. Pin dropdowns of saved rows stay dark | P:3484-3559 | `d44b177` (part of 109) | Adds a parallel path beside upstream code: container-scoped rules after upstream `.settings-select:disabled` (U:1603-1609 = P:3476-3482). Upstream has one dark select look (U:1519-1555) | `d44b177`: "Not run yet: ... the Controls page". Message lists "node --check of the page JavaScript". fork-log:138: "WebUI: white GPIO/hardware dropdowns" |
| F10 | Storage pre-roll rows (Settings, System, card "Media Speed" P:5749) | The Storage pre-roll button and the Automatic pre-roll switch stay hidden until Core reports the feature | P:3575-3577 | `d44b177` (part of 109) | Extends an upstream function in place: a hidden state for upstream `.settings-action-row` (U:1611-1616 = P:3579-3584). The rows follow the upstream Run Speed Test row (U:3622; P:5765-5777) | `d44b177`: "Not compiled or run yet: the pre-roll and the Clear HDR override", and "host tests on the Mac (... pre-roll)" |
| F11 | Mode Ladder lock warning | A click on a control the Mode Ladder has greyed shows the red toast with a "Mode Ladder" link that opens the card | P:3970-3980 | `392e812` (12) | Extends an upstream function in place: upstream `.toast` (U:1979-2005) gains a state that takes clicks | `392e812`: "Tested: desk (headless Chrome against the Pi, read only: ladder on and off); Pi build". fork-log:97: "desk-tested, Pi check pending" |

## 3. Rule table

Columns: lines, kind, commits that last touched the lines, selector (or the selectors inside an `@media` block), first place in the
markup or script that uses it (`P:n (+k)` = k more uses). The tables are generated from the file and the blame.

### 3a. Clip Browser (P:1979-2504)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:1979-1979 | comment | `bc12c0a` | /* Playback (T49): the touch UI's Clip Browser, in the WebUI's shell. */ |  |
| P:1980-1982 | rule | `bc12c0a` | `body.pb-open` | P:10120 |
| P:1984-1997 | rule | `bc12c0a` | `.pb-overlay` | P:6345 |
| P:1999-2002 | rule | `bc12c0a` | `.pb-overlay.hidden` | P:6345 |
| P:2004-2016 | rule | `bc12c0a` | `.pb-shell` | P:6346 |
| P:2018-2025 | rule | `bc12c0a` | `.pb-page` | P:6347 |
| P:2027-2030 | rule | `bc12c0a` | `.pb-page.hidden, .pb-viewer.hidden` | P:6347 |
| P:2032-2038 | rule | `bc12c0a` | `.pb-header` | P:6348 (+1) |
| P:2040-2045 | rule | `bc12c0a` | `.pb-eyebrow` | P:6350 (+1) |
| P:2047-2052 | rule | `bc12c0a` | `.pb-h1` | P:6351 (+1) |
| P:2054-2059 | rule | `bc12c0a` | `.pb-actions` | P:6353 (+1) |
| P:2061-2075 | rule | `bc12c0a` | `.pb-top-button, .pb-show-button` | P:6354 (+2) |
| P:2077-2080 | rule | `bc12c0a` | `.pb-top-button:disabled` | P:6354 (+2) |
| P:2082-2084 | rule | `bc12c0a` | `.pb-show-wrap` | P:6358 |
| P:2086-2094 | rule | `bc12c0a` | `.pb-show-button` | P:6359 |
| P:2096-2101 | rule | `bc12c0a` | `.pb-show-label` | P:6360 |
| P:2103-2117 | rule | `bc12c0a` | `.pb-menu` | P:6363 |
| P:2119-2121 | rule | `bc12c0a` | `.pb-menu.hidden` | P:6363 |
| P:2123-2134 | rule | `bc12c0a` | `.pb-menu button` | P:6363 |
| P:2136-2139 | rule | `bc12c0a` | `.pb-menu button.active` | `active` toggled P:11977 |
| P:2141-2152 | rule | `bc12c0a` | `.pb-sheet` | P:6376 |
| P:2154-2159 | rule | `bc12c0a` | `.pb-sheet-head` | P:6377 |
| P:2161-2165 | rule | `bc12c0a` | `.pb-section` | P:6379 |
| P:2167-2178 | rule | `bc12c0a` | `.pb-chip` | P:6380 |
| P:2180-2182 | rule | `bc12c0a` | `.pb-spacer` | P:6381 |
| P:2184-2189 | rule | `bc12c0a` | `.pb-selection-actions` | P:6382 |
| P:2191-2193 | rule | `bc12c0a` | `.pb-selection-actions.hidden` | P:6382 |
| P:2195-2201 | rule | `bc12c0a` | `.pb-selection-actions .danger-button, .pb-selection-actions .primary-button, .pb-selection-actions .secondary-button` | P:6382 |
| P:2203-2213 | rule | `bc12c0a` | `.pb-count` | P:6387 |
| P:2215-2218 | rule | `bc12c0a` | `.pb-status` | P:6389 |
| P:2220-2230 | rule | `27eac5a+bc12c0a` | `.pb-grid` | P:6390 |
| P:2232-2250 | rule | `27eac5a+bc12c0a` | `.pb-card` | P:11820 |
| P:2252-2254 | rule | `bc12c0a` | `.pb-card:active` | P:11820 |
| P:2256-2259 | rule | `bc12c0a` | `.pb-card.last` | `last` P:11820 |
| P:2261-2264 | rule | `bc12c0a` | `.pb-card.selected` | `selected` P:11820 |
| P:2266-2272 | rule | `27eac5a+bc12c0a` | `.pb-thumb` | P:11765 (+1) |
| P:2274-2284 | rule | `bc12c0a` | `.pb-thumb img` | P:11765 (+1) |
| P:2286-2296 | rule | `bc12c0a` | `.pb-nopreview` | P:11766 (+1) |
| P:2298-2309 | rule | `bc12c0a` | `.pb-pill` | P:11837 (+1) |
| P:2311-2313 | rule | `bc12c0a` | `.pb-pill.duration` | P:11837 (+1) |
| P:2315-2319 | rule | `bc12c0a` | `.pb-pill.drop` | P:11837 (+1) |
| P:2321-2334 | rule | `bc12c0a` | `.pb-badge` | P:11832 |
| P:2336-2339 | rule | `bc12c0a` | `.pb-grid.selecting .pb-badge, .pb-card:hover .pb-badge` | `selecting` toggled P:11983 |
| P:2341-2345 | rule | `bc12c0a` | `.pb-card.selected .pb-badge` | P:11832 |
| P:2347-2349 | rule | `bc12c0a` | `.pb-badge svg` | P:11832 |
| P:2351-2353 | rule | `bc12c0a` | `.pb-card.selected .pb-badge svg` | P:11832 |
| P:2355-2361 | rule | `27eac5a+bc12c0a` | `.pb-foot` | P:11851 |
| P:2363-2369 | rule | `bc12c0a` | `.pb-name` | P:11855 |
| P:2371-2376 | rule | `bc12c0a` | `.pb-name-head` | P:11859 |
| P:2378-2380 | rule | `bc12c0a` | `.pb-name-tail` | P:11862 |
| P:2382-2385 | rule | `bc12c0a` | `.pb-fmt` | P:11866 |
| P:2387-2392 | rule | `bc12c0a` | `.pb-date, .pb-tc` | P:11869 |
| P:2394-2396 | rule | `bc12c0a` | `.pb-tc` | P:11874 |
| P:2398-2407 | rule | `bc12c0a` | `.pb-scrim` | P:6475 |
| P:2409-2411 | rule | `bc12c0a` | `.pb-scrim.hidden` | P:6475 |
| P:2413-2422 | rule | `bc12c0a` | `.pb-dialog` | P:6476 |
| P:2424-2427 | rule | `bc12c0a` | `.pb-dialog h2` | P:6476 |
| P:2429-2434 | rule | `bc12c0a` | `.pb-dialog p` | P:6476 |
| P:2436-2439 | rule | `bc12c0a` | `.pb-dialog .pb-dialog-name` | P:6479 |
| P:2441-2445 | rule | `bc12c0a` | `.pb-dialog-buttons` | P:6481 |
| P:2447-2450 | rule | `bc12c0a` | `.pb-dialog-buttons button` | P:6481 |
| P:2452-2456 | `@media (max-width: 1119px)` | `bc12c0a` | .pb-grid |  |
| P:2458-2497 | `@media (max-width: 719px)` | `bc12c0a` | .pb-overlay; .pb-shell; .pb-page; .pb-h1; .pb-grid; .pb-sheet; .pb-name; .pb-top-button; .pb-show-button |  |
| P:2499-2503 | `@media (max-width: 419px)` | `bc12c0a` | .pb-top-button span |  |

### 3b. Clip Viewer (P:2505-2945)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:2505-2505 | comment | `4629de2` | /* Playback (T50): the Clip Viewer. */ |  |
| P:2506-2514 | rule | `4629de2` | `.pb-viewer` | P:6393 |
| P:2516-2522 | rule | `4629de2` | `.pbv-body` | P:6406 |
| P:2524-2530 | rule | `4629de2` | `.pbv-main` | P:6407 |
| P:2532-2540 | rule | `4629de2` | `.pbv-stage` | P:6408 |
| P:2542-2548 | rule | `4629de2` | `.pbv-stage canvas` | P:6408 |
| P:2550-2562 | rule | `4629de2` | `.pbv-badge` | P:6411 (+3) |
| P:2564-2564 | rule | `4629de2` | `.pbv-badge.tr` | P:6411 (+3) |
| P:2565-2565 | rule | `4629de2` | `.pbv-badge.tl` | P:6411 (+3) |
| P:2566-2566 | rule | `4629de2` | `.pbv-badge.bl` | P:6411 (+3) |
| P:2567-2567 | rule | `4629de2` | `.pbv-badge.br` | P:6411 (+3) |
| P:2568-2568 | rule | `4629de2` | `.pbv-badge.hidden` | P:6411 (+3) |
| P:2570-2580 | rule | `4629de2` | `.pbv-hole` | P:6415 |
| P:2582-2584 | rule | `4629de2` | `.pbv-hole.hidden` | P:6415 |
| P:2586-2594 | rule | `4629de2` | `.pbv-hold` | P:6416 |
| P:2596-2598 | rule | `4629de2` | `.pbv-hold.hidden` | P:6416 |
| P:2600-2611 | rule | `4629de2` | `.pbv-hold-card` | P:6417 |
| P:2613-2616 | rule | `4629de2` | `.pbv-hold-title` | P:6418 |
| P:2618-2621 | rule | `4629de2` | `.pbv-hold-body` | P:6419 |
| P:2623-2627 | rule | `4629de2` | `.pbv-hold-buttons` | P:6420 |
| P:2629-2631 | rule | `4629de2` | `.pbv-hold-buttons .hidden` | P:6420 |
| P:2633-2637 | rule | `4629de2` | `.pbv-title` | P:6427 |
| P:2639-2642 | rule | `4629de2` | `.pbv-title-text` | P:6428 |
| P:2644-2650 | rule | `4629de2` | `.pbv-name` | P:6429 |
| P:2652-2655 | rule | `4629de2` | `.pbv-info` | P:6430 |
| P:2657-2673 | rule | `4629de2` | `.pbv-icon-button, .pbv-info-button` | P:6432 |
| P:2675-2678 | rule | `4629de2` | `.pbv-icon-button:disabled` | P:6432 |
| P:2680-2685 | rule | `4629de2` | `.pbv-scrub` | P:6439 |
| P:2687-2692 | rule | `4629de2` | `.pbv-rail` | P:6440 |
| P:2694-2699 | rule | `4629de2` | `.pbv-fill` | P:6440 |
| P:2701-2711 | rule | `4629de2` | `.pbv-handle` | P:6440 |
| P:2713-2720 | rule | `4629de2` | `.pbv-time` | P:6442 |
| P:2722-2727 | rule | `4629de2` | `.pbv-controls` | P:6443 |
| P:2729-2735 | rule | `4629de2` | `.pbv-remove` | P:6444 |
| P:2737-2741 | rule | `4629de2` | `.pbv-transport` | P:6447 |
| P:2743-2754 | rule | `4629de2` | `.pbv-circle` | P:6448 (+4) |
| P:2756-2761 | rule | `4629de2` | `.pbv-circle.big` | P:6448 (+4) |
| P:2763-2765 | rule | `4629de2` | `.pbv-circle.big img` | P:6448 (+4) |
| P:2767-2770 | rule | `4629de2` | `.pbv-circle.small` | P:6448 (+4) |
| P:2772-2775 | rule | `4629de2` | `.pbv-circle:disabled` | P:6448 (+4) |
| P:2777-2783 | rule | `4629de2` | `.pbv-hist` | P:6458 |
| P:2785-2790 | rule | `4629de2` | `.pbv-hist-label` | P:6459 |
| P:2792-2797 | rule | `4629de2` | `.pbv-hist canvas` | P:6458 |
| P:2799-2809 | rule | `4629de2` | `.pbv-meta` | P:6464 |
| P:2811-2819 | rule | `4629de2` | `.pbv-meta-head` | P:6465 |
| P:2821-2832 | rule | `4629de2` | `.pbv-meta-close` | P:6468 |
| P:2834-2838 | rule | `4629de2` | `.pbv-meta-name` | P:6470 |
| P:2840-2844 | rule | `4629de2` | `.pbv-meta-grid` | P:6471 |
| P:2846-2850 | rule | `4629de2` | `.pbv-meta-row` | P:12472 (+1) |
| P:2852-2857 | rule | `4629de2` | `.pbv-meta-label` | P:12474 (+1) |
| P:2859-2863 | rule | `4629de2` | `.pbv-meta-value` | P:12475 (+1) |
| P:2865-2877 | `@media (min-width: 1120px)` | `4629de2` | .pbv-body; .pbv-meta; .pbv-info-button |  |
| P:2879-2892 | `@media (max-width: 1119px)` | `4629de2` | .pbv-meta.open; .pbv-meta.open .pbv-meta-close |  |
| P:2894-2927 | `@media (max-width: 719px)` | `4629de2` | .pb-viewer; .pbv-stage; .pbv-name; .pbv-controls; .pbv-transport; .pbv-hist canvas |  |
| P:2929-2944 | `@media (max-height: 499px) and (orientation: landscape)` | `4629de2` | .pb-viewer > .pb-header; .pbv-title-text; .pb-viewer; .pbv-stage |  |

### 3c. Editor gutter, diff box, Controls review, Listen, chips, Scan, issues box (P:3086-3278)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:3086-3091 | rule | `8be1ab5` | `.config-editor-wrap` | P:5939 (+1) |
| P:3093-3105 | rule | `8be1ab5` | `.config-gutter` | P:5940 (+1) |
| P:3107-3107 | comment | `2a4266e` | /* Boot Config: a line the card's controls or the fan mode set (italic, as other system values) */ |  |
| P:3108-3112 | rule | `2a4266e` | `.config-gutter .managed, .config-diff .diff-managed` | `managed` P:18777; `diff-managed` P:20431 |
| P:3114-3116 | rule | `8be1ab5` | `.config-editor-wrap .config-editor` | P:5941 (+1) |
| P:3118-3122 | rule | `8be1ab5` | `.config-tools` | P:6213 |
| P:3124-3135 | rule | `8be1ab5` | `.config-diff` | P:5924 (+2) |
| P:3137-3139 | rule | `8be1ab5` | `.config-diff[hidden]` | P:5924, 5936, 6229 |
| P:3141-3141 | rule | `8be1ab5` | `.config-diff .diff-add` | P:18866 (+2) |
| P:3142-3142 | rule | `8be1ab5` | `.config-diff .diff-del` | P:18866 (+2) |
| P:3143-3143 | rule | `8be1ab5` | `.config-diff .diff-gap` | P:18866 (+1) |
| P:3144-3149 | rule | `8a56545` | `.config-diff .diff-note` | P:20274 (+2) |
| P:3151-3156 | rule | `afa00e8` | `.config-diff .diff-info` | P:20281 |
| P:3158-3165 | rule | `8a56545` | `.config-diff .diff-confirm` | P:20283 |
| P:3167-3173 | rule | `8be1ab5` | `.config-diff .diff-actions` | P:18871 (+1) |
| P:3175-3182 | rule | `8be1ab5` | `.controls-review` | P:6151 |
| P:3184-3187 | rule | `8be1ab5` | `.controls-review[hidden], .controls-listen-note[hidden]` | P:6151, 6149 |
| P:3189-3193 | rule | `8be1ab5` | `.controls-listen-note` | P:6149 |
| P:3195-3199 | rule | `8be1ab5` | `.controls-row.heard` | `heard` P:18644 |
| P:3201-3206 | rule | `8be1ab5` | `.action-chips` | P:16818 |
| P:3208-3218 | rule | `8be1ab5` | `.action-chip` | P:16839 |
| P:3220-3222 | rule | `8be1ab5` | `.action-chip.dragging` | `dragging` P:16842 |
| P:3224-3231 | rule | `8be1ab5` | `.action-chip button` | P:16839 |
| P:3233-3236 | rule | `8be1ab5` | `.action-chips .settings-select` | P:16818; select P:16766 |
| P:3238-3242 | rule | `8be1ab5` | `.controls-scan` | P:18195 (+2) |
| P:3244-3249 | rule | `8be1ab5` | `.controls-bus-line` | P:17681 (+1) |
| P:3251-3255 | rule | `8be1ab5` | `.controls-bus-line .preset-action` | P:17681 (+1) |
| P:3257-3264 | rule | `effb804` | `.config-issues` | P:5868 (+6) |
| P:3266-3268 | rule | `effb804` | `.config-issues[hidden]` | P:5868 (+6) |
| P:3270-3273 | rule | `effb804` | `.config-issues ul` | P:5868 (+6) |
| P:3275-3277 | rule | `d282de9` | `.config-issues.info` | P:5868 (+6) |

### 3d. Controls cards, settings grid, rows, lines, Try, Remote controls (P:3279-3445)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:3279-3285 | rule | `166cc4d` | `.controls-peripheral` | P:17654 (+2) |
| P:3287-3290 | rule | `d44b177+f5fe41b` | `.controls-peripheral.undetected, .controls-output-item.undetected` | `undetected` P:17654; `.controls-output-item`: none (section 7) |
| P:3292-3295 | rule | `d44b177` | `.controls-output-item` | none (section 7) |
| P:3297-3301 | rule | `d44b177` | `.controls-output-title` | none (section 7) |
| P:3303-3309 | rule | `166cc4d` | `.controls-peripheral-head` | P:17656 (+1) |
| P:3311-3315 | rule | `166cc4d` | `.controls-settings` | P:17701 |
| P:3317-3321 | rule | `b74b4aa` | `.controls-settings .field-stack` | P:17701 |
| P:3323-3326 | rule | `166cc4d` | `.controls-settings .field-stack.changed .settings-select, .controls-settings .field-stack.changed .settings-input` | fields P:17709-17710 |
| P:3328-3330 | rule | `d282de9+fa3a798` | `.controls-group` | P:17797 |
| P:3332-3339 | rule | `d282de9+fa3a798` | `.controls-group-title` | P:17799 |
| P:3341-3341 | comment | `fa3a798` | /* Rows sit inside their device's card, one rule between them. */ |  |
| P:3342-3349 | rule | `d282de9+fa3a798` | `.controls-row` | P:17141 (+3) |
| P:3351-3355 | rule | `d282de9+f5fe41b` | `.controls-row.off, .controls-row.removed, .controls-line.removed` | `off`, `removed` P:17141, 17825; line `removed` P:16896 |
| P:3357-3361 | rule | `d282de9+fa3a798` | `.controls-row-head` | P:16967 |
| P:3363-3366 | rule | `b74b4aa+d44b177` | `.controls-row.new .controls-row-head, .controls-row[data-output] .controls-row-head` | `new` P:17442; `data-output` P:17826 |
| P:3368-3370 | rule | `d282de9` | `.controls-row-title` | P:16970 (+4) |
| P:3372-3375 | rule | `d282de9` | `.controls-row-detail` | P:16976 (+8) |
| P:3377-3377 | comment | `1319967` | /* Gesture or label \| action \| Try and Remove: the same three columns on every line, so actions and Removes line up. */ |  |
| P:3378-3384 | rule | `1319967+d282de9+fa3a798` | `.controls-line` | P:16896 |
| P:3386-3388 | rule | `d282de9+fa3a798` | `.controls-line:last-child` | P:16896 |
| P:3390-3393 | rule | `d282de9` | `.controls-line-label` | P:16899 |
| P:3395-3398 | rule | `1319967` | `.controls-line-remove` | P:16907 |
| P:3400-3403 | rule | `1319967+fa3a798` | `.controls-line-remove > button` | P:16907 |
| P:3405-3407 | rule | `1319967` | `.controls-line-remove > button.controls-try` | P:16944 |
| P:3409-3411 | rule | `1319967` | `.controls-line-remove > button.controls-try-turn` | P:16944 |
| P:3413-3413 | comment | `1319967` | /* Remote controls (main page, under Camera settings): the Camera settings blocks and pills. */ |  |
| P:3414-3418 | rule | `1319967` | `.remote-note` | P:4577 |
| P:3420-3424 | rule | `1319967+fa3a798` | `#remoteControlsRows .pill-button` | host P:4578; pills built P:17993-18042 |
| P:3426-3428 | rule | `fa3a798` | `.controls-add-action` | P:17034 |
| P:3430-3437 | rule | `d282de9+fa3a798` | `.controls-add-bar` | P:17566 |
| P:3439-3444 | `@media (max-width: 720px)` | `d282de9+fa3a798` | .controls-row; .controls-line |  |

### 3e. White selects, dark pin selects, GPIO out, hidden action row (P:3484-3578)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:3484-3485 | comment | `d44b177` | /* The GPIO and hardware dropdowns (the Controls panel, and the Hardware card on the Config page) are white and dark-texted, like CineMate's web GUI, so they are easy to see. Every other dropdown keeps the dark look. */ |  |
| P:3486-3495 | rule | `d44b177` | `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select` | selects built at P:16766, 16991, 17078, 17453, 17718, 17730, 17860, 17874 |
| P:3497-3501 | rule | `d44b177` | `[data-panel="controls"] .settings-select option, #hardwareDevices .settings-select option` | same selects |
| P:3503-3506 | rule | `d44b177` | `[data-panel="controls"] .settings-select option:disabled, #hardwareDevices .settings-select option:disabled` | same selects |
| P:3508-3512 | rule | `d44b177` | `[data-panel="controls"] .settings-select:focus, #hardwareDevices .settings-select:focus` | same selects |
| P:3514-3523 | rule | `d44b177` | `[data-panel="controls"] .settings-select:disabled, #hardwareDevices .settings-select:disabled` | same selects |
| P:3525-3525 | comment | `d44b177` | /* The pin dropdowns (GPIO in rows, GPIO out rows) keep the page's normal dark look. */ |  |
| P:3526-3534 | rule | `d44b177` | `[data-panel="controls"] .settings-select.controls-pin-select` | class set P:17348 (`buildControlsPinSelect`: saved GPIO in rows P:17376, GPIO out row P:17842) |
| P:3536-3539 | rule | `d44b177` | `[data-panel="controls"] .settings-select.controls-pin-select option` | as P:3526 |
| P:3541-3541 | comment | `d44b177` | /* A pin another control holds: greyed, with its function in the label. */ |  |
| P:3542-3544 | rule | `d44b177` | `[data-panel="controls"] .settings-select.controls-pin option[data-used]` | P:17348, 17453; `data-used` set P:17222 |
| P:3546-3549 | rule | `d44b177` | `[data-panel="controls"] .settings-select.controls-pin-select:focus` | as P:3526 |
| P:3551-3559 | rule | `d44b177` | `[data-panel="controls"] .settings-select.controls-pin-select:disabled` | as P:3526 |
| P:3561-3561 | comment | `d44b177` | /* GPIO out: pin \| function \| active \| Test, in the second column of a row like GPIO in's. */ |  |
| P:3562-3567 | rule | `b64e6f6+d44b177` | `.controls-output-fields` | P:17858 |
| P:3569-3573 | `@media (max-width: 720px)` | `d44b177` | .controls-output-fields |  |
| P:3575-3577 | rule | `d44b177` | `.settings-action-row[hidden]` | `#storagePrerollRow` P:5769, `#storagePrerollAutoRow` P:5773 |

### 3f. Toast link (P:3970-3981)

| P lines | Kind | Commits | Selector | Used at |
| --- | --- | --- | --- | --- |
| P:3970-3972 | rule | `392e812` | `.toast.with-link` | set P:7990; cleared P:7992, 12994, 20693 |
| P:3974-3976 | rule | `392e812` | `.toast .ladder-link` | P:7985 |
| P:3978-3980 | rule | `392e812` | `[data-ladder-lock] select:disabled` | `data-ladder-lock` set P:11144, 11158, 15929 |

## 4. Original code that was changed

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| Media list overlay rules, 36 rules | U:1122-1431 | All removed. No `media-browser-*`, `media-filter-*`, `media-sort-*`, `media-select-*`, `media-selection-*`, `media-row*`, `media-stat` name is left in the port file (grep over P:1-20963: 0 hits) | removed |
| `.media-browser-overlay`, `.media-browser-overlay.hidden` | U:1122-1140 -> P:1984-2002 | Renamed `.pb-overlay`. Declarations identical (`diff` after renaming: no difference) | rewritten (rename only) |
| `.media-browser-shell` | U:1142-1154 -> P:2004-2016 | Renamed `.pb-shell`. `width: min(900px, ...)` -> `min(1320px, ...)`. `height: min(760px, calc(100dvh - 32px))` and `max-height` -> `height: calc(100dvh - 32px)`. `border: 1px solid #27272a` -> `var(--card-border)` (same colour, U:22). `position: relative` added | rewritten |
| `.config-editor` | U:1562-1571 = P:3075-3084 | Rule untouched. A later rule narrows it inside the new wrapper: `.config-editor-wrap .config-editor { border-radius: 0 18px 18px 0; }` P:3114-3116 | extended-in-place |
| `.settings-select`, `.settings-select:disabled` | U:1519-1555, 1603-1609 = P:3032-3068, 3476-3482 | Rules untouched. 10 new rules follow that override colour, border, arrow, focus and disabled look inside `[data-panel="controls"]` and `#hardwareDevices` (P:3486-3559). Both containers are port-only (P:6137, 6184), so no upstream element changes look | extended-in-place |
| `.settings-action-row` | U:1611-1616 = P:3579-3584 | Rule untouched. `.settings-action-row[hidden] { display: none; }` added before it (P:3575-3577) | extended-in-place |
| `.toast`, `.toast.visible`, `.toast.error` | U:1979-2005 = P:3947-3968, 3982-3985 | Rules untouched. Three rules inserted between `.toast.visible` and `.toast.error` (P:3970-3980). `.toast.with-link` sets `pointer-events: auto`; upstream `.toast` has `pointer-events: none` (U:1992) | extended-in-place |
| Place of the overlay's phone rules | U:2072-2125 (inside `@media (max-width: 720px)`, U:2062) | Not in this slice (next slice, hunk `-2061,71 +4041,64`). Named here because the replacement rules are inline in this slice: P:2452-2503, 2865-2944 | moved |

Nothing else of the original 900 lines (U:1112-2011) is touched: 589 lines are kept byte for byte (section 0).

## 5. New CSS component families and patterns, and what upstream uses for the same job

| New in the port | Where | Purpose | Upstream for the same job |
| --- | --- | --- | --- |
| `.pb-*` family, 60 rules + 3 `@media` | P:1980-2503 | Playback overlay: shell, header, SHOW menu, sheet, card grid, card, selection badge, remove dialog | `.media-browser-*`, `.media-filter-button`, `.media-sort-select`, `.media-select-*`, `.media-row*`, `.media-stat` U:1122-1431 (removed). The touch UI has the same screen: `qml/ClipBrowserPage.qml` @upstream-1.6.0 ("PLAYBACK" :169, "Clip Browser" :179, "Refresh Media" :286, "Remove Selected" :468, "NO PREVIEW" :679) |
| `.pbv-*` family (with `.pb-viewer`), 50 rules + 4 `@media` | P:2506-2944 | Clip Viewer: stage, badges, hold card, scrub bar, transport buttons, histogram, metadata panel | None in the WebUI. Touch UI: `qml/ClipPlayerPage.qml` @upstream-1.6.0 |
| In-page confirm dialog `.pb-scrim` + `.pb-dialog` | P:2398-2450; markup P:6475-6486 | "Remove Selected Clips?" with Cancel and Remove | `window.confirm(...)` U:10385 (single delete), U:10434 (selected). Upstream CSS has no dialog, modal or scrim rule (grep over U:15-2420: 0 hits) |
| Pop-up menu `.pb-menu` | P:2103-2139; markup P:6363-6368 | SHOW: Clips, Stills, Timelapse, Audio | A row of four `.media-filter-button` U:1224-1242, markup U:3999-4004 |
| Toggle chip `.pb-chip` | P:2167-2178; markup P:6380 | NEWEST FIRST / OLDEST FIRST | `<select class="settings-select media-sort-select">` U:1244-1253, markup U:4009-4012 |
| Gutter beside a textarea: `.config-editor-wrap` + `.config-gutter` | P:3086-3116; markup P:6222-6225, 5939-5942 | Line numbers that scroll with the editor (script `updateEditorGutter` P:18764-18790) | A bare `<textarea class="settings-input config-editor">` inside `label.field-stack` U:3861-3864 |
| Review box `.config-diff` + `.diff-add`, `.diff-del`, `.diff-gap`, `.diff-note`, `.diff-info`, `.diff-confirm`, `.diff-actions`, `.diff-managed` | P:3108-3173 | Show the changed lines, notes and the confirm buttons before a save (hardware file P:18854-18887; config.txt P:20242-20300) | None. Upstream saves at once (`saveConfigFile` U:10330) and asks with `window.confirm` where it asks (U:10307, 11266-11337) |
| Message box `.config-issues` (+ `.info`) | P:3257-3277; 7 elements (P:5868-5869, 6147-6148, 6182-6183, 6228) | A bordered list of errors or notes that stays on the page | `showToast(message, isError)` U:7804 and `.subtle-note` text |
| `.controls-*` family, 33 rules + 2 `@media` | P:3175-3199, 3238-3255, 3279-3411, 3426-3444, 3562-3573 | Controls page and Hardware card: device card, head, settings grid, group, row, line, add bar, review, Listen note, Scan lines | None. Nearest upstream list styles: `.preset-row`, `.preset-meta`, `.preset-actions` (U:1881-1947) and `.settings-field-grid` + `.field-stack` for field grids (U:1494-1509) |
| `.controls-settings` grid | P:3311-3326 | Settings fields in an auto-fill grid, `minmax(190px, 1fr)` | `.settings-field-grid`, two fixed columns, U:1494-1498 |
| Draggable chips `.action-chips`, `.action-chip`, `.action-chip.dragging` | P:3201-3236; script P:16817-16860 | Several actions on one line, reordered by drag | None. Upstream CSS and script have no drag (grep `dragging`, `draggable` @upstream: 0 hits) |
| Container-scoped look for an upstream class: `[data-panel="controls"] .settings-select`, `#hardwareDevices .settings-select`, with `--select-bg`, `--select-fg` | P:3486-3559; variables P:35-36 (slice WCP-01) | White selects in two containers, dark pin selects as an exception | One look for `.settings-select` everywhere, U:1519-1555, 1603-1609. Upstream has no rule scoped by a panel |
| Attribute selectors in CSS: `[hidden]` (4 rules, 5 selectors), `[data-panel="controls"]`, `[data-output]`, `[data-used]`, `[data-ladder-lock]` | P:3137, 3184-3185, 3266, 3364, 3486-3559, 3575, 3978 | Hide by the `hidden` attribute; style by data attributes | Upstream CSS has no attribute selector (awk over U:15-2420: 0 hits). Upstream hides with the class `.hidden { display: none !important; }` U:1975-1977 (= P:3943-3945) |
| Toast that takes clicks: `.toast.with-link`, `.toast .ladder-link` | P:3970-3976; script P:7982-7993 | A link inside the toast | Upstream toast is text only, `pointer-events: none` U:1979-1995, `showToast` U:7804 |
| `@media` blocks next to their component, 9 blocks | P:2452, 2458, 2499, 2865, 2879, 2894, 2929, 3439, 3569 | Breakpoints 1119 / 719 / 419 px (max), 1120 px (min), landscape under 500 px high, 720 px (max) | All `@media` blocks at the end of the CSS: U:2034 (1120px), 2062 (720px), 2190 (480px), 2319 (560px), 2391 (420px). Upstream uses `max-width` only |
| CSS comments, 11 | P:1979, 2505, 3107, 3320, 3341, 3377, 3413, 3484-3485, 3525, 3541, 3561 | Section notes | Upstream CSS has no comment (awk over U:15-2420: 0 hits; the KB says the same, `llm/core-map.md:156`) |

No class, namespace, header, worker thread or helper script is in this slice.

## 6. Removed, narrowed or hidden

### 6a. The 36 upstream rules that are gone

Columns: upstream lines, selector, first upstream use in markup or script, lines of its phone rule in U:2034-2420 (next slice).

| U lines | Selector | Used at (U) | Phone rule (U) |
| --- | --- | --- | --- |
| U:1122-1135 | `.media-browser-overlay` | 3979 | 2072 |
| U:1137-1140 | `.media-browser-overlay.hidden` | 3979 | 2072 |
| U:1142-1154 | `.media-browser-shell` | 3980 | 2077 |
| U:1156-1163 | `.media-browser-header` | 3981 | 2089 |
| U:1165-1170 | `.media-browser-title-row` | 3983 | - |
| U:1172-1182 | `.media-browser-icon` | 3984 | - |
| U:1184-1192 | `.media-browser-body` | 3997 | 2094 |
| U:1194-1201 | `.media-browser-toolbar` | 3998 | - |
| U:1203-1208 | `.media-browser-filters` | 3999 (+1) | - |
| U:1210-1218 | `.media-browser-tools` | 4005 | - |
| U:1220-1222 | `.media-browser-tools-row` | 4006 | - |
| U:1224-1236 | `.media-filter-button` | 4000 (+6) | - |
| U:1238-1242 | `.media-filter-button.active` | 4000 (+6) | - |
| U:1244-1253 | `.media-sort-select` | 4009 | - |
| U:1255-1266 | `.media-selection-toolbar` | 4016 | - |
| U:1268-1275 | `.media-selection-count` | 4017 | - |
| U:1277-1283 | `.media-selection-actions` | 4018 | - |
| U:1285-1292 | `.media-select-button` | 4019 (+3) | - |
| U:1294-1306 | `.media-select-control` | 7719 | - |
| U:1308-1316 | `.media-select-control::after` | 7719 | - |
| U:1318-1321 | `.media-select-control.selected` | 7719 | - |
| U:1323-1325 | `.media-select-control.selected::after` | 7719 | - |
| U:1327-1329 | `.media-select-control:active` | 7719 | - |
| U:1331-1333 | `.media-filter-button:active` | 4000 (+6) | - |
| U:1335-1339 | `.media-browser-list` | 4025 | - |
| U:1341-1351 | `.media-row` | 7710 | 2108 |
| U:1353-1356 | `.media-row.selected` | 7710 | 2108 |
| U:1358-1370 | `.media-row-type` | 7730 | - |
| U:1372-1378 | `.media-row-meta` | 7735 | - |
| U:1380-1386 | `.media-row-name` | 7738 | - |
| U:1388-1392 | `.media-row-detail` | 7743 | - |
| U:1394-1400 | `.media-row-stats` | 7748 | - |
| U:1402-1411 | `.media-stat` | 7757 | - |
| U:1413-1416 | `.media-stat strong` | 7757 | - |
| U:1418-1425 | `.media-row-actions` | 7765 | 2114 |
| U:1427-1431 | `.media-row-action` | 7768 (+1) | 2121 |

### 6b. What the operator had with those rules, and where it is now

The markup and script are in other slices. They are named here because these CSS rules went with them.

| Upstream (media list) | Port (Clip Browser) | Effect |
| --- | --- | --- |
| A list of rows, one per item, 900 px wide shell (U:1142-1154, 1335-1351) | A grid of cards, 4 / 3 / 2 columns, shell 1320 px wide and full height, full screen on a phone (P:2004-2016, 2220-2230, 2452-2468) | Different layout |
| Four filter buttons always in view (U:3999-4004) | SHOW pop-up menu with the same four entries (P:6358-6368) | One more tap to change the category |
| Sort `<select>`: Newest First, Oldest First, by `modified_ms` (U:4009-4012, 7558-7569) | A chip that flips the order; the key is `shot_ms`, then `modified_ms` (P:6380, 11685-11698) | Same two orders, other key |
| Selection bar always in view: "N items selected", Select All, Clear, Download Selected, Delete Selected (U:4016-4024) | Hidden until a selection starts (P:6382-6386, 11973). A selection starts with an 800 ms press (P:11889-11896). No Clear button: Back turns into Cancel (P:11969, 12097-12103). "Delete" is worded "Remove" | Selection is hidden until a long press |
| A tick box on every row; a click on the row toggles it (U:7712-7727) | A tap opens the clip; a tick badge shows while selecting or on hover (P:2336-2339, 11907-11916) | A tap no longer selects |
| Stat pills per row: frame or file count, duration, fps, file size (U:7747-7760) | The card shows the duration only (P:11836-11839). Frame count and fps are in the viewer (P:6411-6414). File size appears only in the viewer's download question (P:12914) | File size, frame count and fps are not on the list |
| "Updated <modified_text>" per row (U:7742-7745) | `shot_date_text`, else `modified_text` (P:11868-11870) | Shot date, not modified time |
| Download link on every row, `item.download_url` (U:7767-7779) | Download button in the viewer (P:6432, 12909-12917), or select and Download Selected | One step more for a single file |
| Delete button on every row -> `window.confirm` -> `POST /api/media/delete?kind=&id=` (U:7781-7788, 10380-10389) | Remove in the viewer or Remove Selected -> in-page dialog -> `POST /api/media/delete-selected` (P:12036-12082) | The page no longer calls `/api/media/delete`. The route stays in Core (App:9004) |
| Sub-title "Download or delete clips, stills, timelapses, and audio recordings from mounted media." (U:3989) | Gone. A status line `#pbStatus` (P:6389, 11928-11948) | |
| Selected row cyan: `rgba(34, 211, 238, 0.72)` border (U:1353-1356) | Selected card red: `rgba(239, 68, 68, 0.7)` border, red badge (P:2261-2264, 2341-2345) | Other selection colour |
| Live preview keeps running behind the overlay (`setMediaBrowserOpen` U:6139-6147 does not touch the preview) | The preview `src` is removed while the overlay is open (P:12137-12143) | No live picture behind the overlay |
| Folder button always enabled (U:2447) | Disabled in a take or a timelapse (P:12022-12024) | No media list during a take |

### 6c. Narrowed or hidden by the features this slice styles (outside the slice)

| What | Where | Effect |
| --- | --- | --- |
| The GPIO chip as a field and as a shown fact | Section 10 | See section 10 |
| Pin dropdowns offer GPIO 4 to 27 | CM:381 ("2 and 3 are the I2C bus 1 lines"); output `line` field -1 to 27, CM:268 | The readers accept lines 0 to 63 on the chip named by `chip=` (`src/hardware/GpioInput.cpp:233`, `:431-432`, `:507-510` @upstream-1.6.0; `:141`, `:343-344` @cinemate-port). The page offers header pins 4 to 27 only |

## 7. Rules with no element at HEAD

Fact check by `grep` over P:4394-20963 (markup and script).

| P lines | Selector | Note |
| --- | --- | --- |
| 3288 | `.controls-output-item.undetected` (second selector of the rule P:3287-3290) | `d44b177`. No `controls-output-item` in markup or script |
| 3292-3295 | `.controls-output-item` | `d44b177`. Same |
| 3297-3301 | `.controls-output-title` | `d44b177`. No `controls-output-title` in markup or script. The GPIO out row is built with `.controls-row` + `.controls-output-fields` (P:17822-17919) |

Two whole rules and one selector of a third, about 11 lines. The other 180 rules have a user (section 3).
Both classes came with the squash `d44b177` and have no user in that commit either (`git show d44b177:src/web/WebControlPage.cpp | grep controls-output`: CSS lines and `controls-output-fields` only).

The reverse case, a class set by the script with no rule in the CSS: `controls-row changed` (P:17141, 17442, 17825). `b74b4aa` removed
`.controls-row.changed` ("No grey bar on changed rows"). Also `controls-gesture` (P:16991) and `controls-turn` (P:17078): no rule in P:15-4393.

## 8. What drives these classes (defined outside the slice; cross-reference only)

The slice adds no socket command, HTTP route, state field, event, config key, env var or file. The items below are what the
script binds to the classes above. They belong to other units. "new" = no handler @upstream-1.6.0 (`grep 'command.name == "<name>"'` in UApp: 0 hits; route list @upstream: `api/command`, `api/config`, `api/media`, `api/media/delete`, `api/media/delete-selected`, `api/media/download`, `api/media/download-selected`, `api/presets*`, `api/state`).

| Feature | Commands | State fields | Routes | Config, env, files | UI elements |
| --- | --- | --- | --- | --- | --- |
| F1 | `user_activity` (upstream) | `playback_hold` (new, App:9557), `recording`, `timelapse_active`, `ui.photo_mode_enabled` (read P:12021-12033, 10126) | `GET /api/media` (upstream route UApp:7161; port App:8435; reply gains `held`, and per item `format_label`, `playable`, `shot_ms`, `shot_date_text`, `first_number`, `missing_frames`, `empty_frames`, `ramp`, `timecode_start`, `token`, App:9262-9291). `GET /api/media/frame` (new, App:8475; thumbnails P:11709-11714). `POST /api/media/delete-selected` (upstream, App:9087). `GET /api/media/download-selected` (upstream, App:8811) | Media root `/media/RAW` named in the status text P:11930 (upstream default `mount_path=/media/RAW`, UApp:4309) | `#playbackOverlay` P:6345; `#pbBrowserPage`, `#pbTitle`, `#pbRefreshButton`, `#pbShowButton`, `#pbShowMenu`, `#pbBackButton`, `#pbSection`, `#pbSortButton`, `#pbSelectionActions`, `#pbRemoveButton`, `#pbDownloadButton`, `#pbSelectAllButton`, `#pbCount`, `#pbStatus`, `#pbGrid` P:6347-6390; `#pbRemoveScrim` P:6475-6486; cards built P:11816-11926. Opened by upstream `#mediaBrowserButton` P:4420 |
| F2 | `user_activity` (P:12508), `wake` (P:12942) | `playback_hold` | `GET /api/media/clip` (new, App:8442; P:12800). `GET /api/media/frame` (reply headers `X-Frame-Number`, `X-Histogram`, P:12368-12370). `GET /api/media/file` (new, App:8550; the take's WAV in `#pbvAudio`). `GET /api/media/download` (upstream, App:8682) | | `#pbViewerPage` P:6393; `#pbvBack`, `#pbvStage`, `#pbvCanvas`, `#pbvAudio`, `#pbvFps`, `#pbvDrop`, `#pbvState`, `#pbvFrame`, `#pbvHole`, `#pbvHold`, `#pbvLiveButton`, `#pbvWakeButton`, `#pbvName`, `#pbvInfo`, `#pbvDownload`, `#pbvInfoButton`, `#pbvScrub`, `#pbvFill`, `#pbvHandle`, `#pbvTime`, `#pbvTc`, `#pbvRemove`, `#pbvStepBack`, `#pbvPrev`, `#pbvPlay`, `#pbvNext`, `#pbvStepFwd`, `#pbvHist`, `#pbvMeta`, `#pbvMetaClose`, `#pbvMetaName`, `#pbvMetaGrid` P:6400-6471 |
| F3 | `set_controls` with `dry_run=true text=` (new, App:12763; Check, P:18795). `controls_history` (new, App:12458; P:18895) | | `GET /api/config`, `POST /api/config` (upstream routes UApp:7168, 7175; port App:8613, 8620; the page now sends `X-Apertar-Revision`, P:18922) | `/home/pi/apertar-hardware.conf` (P:6205, 18723; upstream U:3853) and its saved versions | `#configHistorySelect` P:6216, `#settingsConfigGutter` P:6223, `#settingsConfigEditor` P:6224 (upstream id), `#settingsConfigIssues` P:6228, `#settingsConfigDiff` P:6229, `#checkConfigButton` P:6233 |
| F4 | `get_boot_config`, `set_boot_config` (new, App:14586, 14589), `restart_system` (upstream) | `recording` (P:20290) | `GET /api/boot-config`, `POST /api/boot-config`, `POST /api/boot-config/parse` (new, App:9161, 9170, 9200; P:20009, 20202, 20457) | `/boot/firmware/config.txt` (P:5863, 20427), backup `config.txt.apertar.bak` (P:5934) | `#settingsBootConfigCard` P:5859; `#bootConfigMessage`, `#bootConfigWarnings` P:5868-5869; `#bootConfigDiff` P:5924; `#bootConfigFileView` P:5936; `#bootConfigGutter`, `#bootConfigEditor` P:5940-5941 |
| F5 | `get_controls` (App:12420), `set_controls` (App:12763), `list_actions` (App:12534), `controls_history` (App:12458), `controls_last_input` (App:12476; Listen polls it every 300 ms, P:18624-18648), `test_input` (App:12565; Try, P:16916-16926). All new | none read by this page | `POST /api/command` (`controlsCall` P:16698-16705) | `apertar-hardware.conf` sections `[gpio_buttons]`, `[gpio_switches]`, `[gpio_encoders]`, `[neorotary4]`, `[pcf8574]`, `[grove_analog]`, `[trigger_output]`, `[recording_indicator]` (section list CM:340-341). `[gpio_switches]` is new in the port (0 hits @upstream) | Nav item P:4770; panel P:6137-6160: `#controlsStatePill`, `#controlsMessage`, `#controlsPending`, `#controlsListenNote`, `#controlsRows`, `#controlsReview`, `#reloadControlsButton`, `#listenControlsButton`, `#undoControlsButton`, `#saveControlsButton` |
| F6 | `test_output` (new, App:12745; P:17896), `set_controls` | | `POST /api/command` | `apertar-hardware.conf:[recording_indicator] enabled`, `target`, `line`, `pcf_pin`, `active_high` (CM:264-271; section name P:16688) | Row built P:17822-17919: pin select, function select, active select, Test, Remove |
| F7 | `get_controls`, `set_controls` (P:18222), `scan_i2c` (new, App:12486; P:18186), `test_output` (P:17688) | | `POST /api/command` | Settings per section, CM:255-304: `[gpio_buttons] enabled`, `active_low`, `pull`, `debounce_ms`; `[recording_indicator]`, `[trigger_output] enabled`, `target`, `line`, `pcf_pin`, `active_high`; `[cfexpress_hat] enabled`, `bus`, `address`; `[neorotary4] enabled`, `bus`, `address`, `invert_direction`, `debounce_ms`, `poll_ms`; `[pcf8574] enabled`, `bus`, `address`, `active_low`, `debounce_ms`, `poll_ms`; `[grove_analog] enabled`, `bus`, `address`, `deadband`, `poll_ms` | Card P:6173-6191: `#hardwareStatePill`, `#hardwareMessage`, `#hardwarePending`, `#hardwareDevices`, `#reloadHardwareButton`, `#saveHardwareButton`; built P:18156-18217 |
| F8 | `test_input section= key=` (new, App:12565; P:18072) | | `POST /api/command` | Reads the saved controls model | Card P:4569-4580: `.remote-note`, `#remoteControlsRows`; built P:18047-18112 |
| F9 | none | none | | none | Selects listed in table 3e |
| F10 | `storage_preroll`, `set_storage_preroll` (new, App:14603, 12900; P:15843) | `storage_preroll_active`, `storage_preroll_auto`, `storage_preroll_auto_env` (new, App:260-262; P:15827-15839) | | `apertar-hardware.conf:[media] preroll`, `preroll_seconds` (`src/util/StoragePreroll.hpp:23-38`); env `APERTAR_STORAGE_PREROLL` (App:278) | `#storagePrerollRow` P:5769, `#storagePrerollAutoRow` P:5773 |
| F11 | none | `ladder_active`, `ladder_resolution` (new, App:327-328, 9491-9492) | | | `#toast` P:6494; `data-ladder-lock` on fields P:11144, 11158, 15929; link built P:7985 |

## 9. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| Pi model, core count, RP1, PCIe, gpiochip number, I2C bus number, RAM, fan | Not present in any CSS declaration of the 1434 inserted lines | confirmed by reading every added line |
| A fan block exists in config.txt | Comment P:3107: "a line the card's controls or the fan mode set" | Comment only. Upstream has a fan mode setting too: `set_fan_mode` (1 handler in UApp), note U:3651 "available when supported by the board" |
| GPIO pins are named "GPIO n" on one chip | Comments P:3484-3485, 3525, 3541, 3561 ("GPIO in rows", "GPIO out rows", "A pin another control holds"). The rules style one pin dropdown per control; no chip is part of the row | The lists behind them: free pins 4 to 27 (CM:381), output `line` -1 to 27 (CM:268), chip info read for 28 lines (App:11989). Outside the slice |
| The Pi 5 header needs no chip and no poll setting | CM:263: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" | Outside the slice. This is why the settings grid (P:3311-3326) shows no chip field. Section 10 |
| A DPI display takes GPIO 0 to 27 and I2C bus 1 | Text drawn in `.controls-scan` (P:18209) and in `.config-diff .diff-note` (P:20277) | Outside the slice (script). 40-pin header, any Pi |
| config.txt is at `/boot/firmware/config.txt`; an RP1 overclock overlay exists | Boot Config markup P:5863, 5893-5895 (`dtoverlay=rp1-clk-333mhz`) | Outside the slice. RP1 = Pi 5 / CM5. The commit message of `8a56545` says "one on a Pi 4" for the camera connectors |
| Browser features | `aspect-ratio` P:2268, 2902, 2940; `100dvh` P:2007, 2465; `inset` P:1986, 2276; `clamp()` P:2867; `backdrop-filter` P:1992; `-webkit-touch-callout`, `-webkit-user-drag` P:2249, 2280-2282 | Client side. Upstream already uses `100dvh` (U:1144), `inset: 0` (U:1124), `backdrop-filter` (U:1130), `-webkit-user-drag` (U:1069) |

## 10. Owner request (put the GPIO chip definition back): relation to this slice

The request relayed with this run: put the definition of the GPIO chip back, because GPIO lines of another chip (a microcontroller,
for example) can be chosen too. Stage 1 changes nothing. These are the facts that bear on it.

| Point | Evidence | Label |
| --- | --- | --- |
| The slice removes no chip rule and no chip rule ever existed | All inserted lines read. `chip` appears only in `.action-chip*` (P:3201-3236) and `.pb-chip` (P:2167), which are unrelated. `166cc4d` added no chip-specific CSS; its chip line used `.controls-row-detail` | confirmed |
| Where the chip field went | `166cc4d` added `{"chip", "GPIO chip", "text", "auto", "", 0, 0}` to `peripheralSettings("gpio_buttons")` (`git show 166cc4d:src/hardware/ControlsModel.hpp` :174). `c140c4f` removed it with `poll_ms` ("The GPIO card's settings drop poll and chip (edge events need neither)"). Today CM:257-263 lists `enabled`, `active_low`, `pull`, `debounce_ms` | confirmed |
| Where the chip line went | `166cc4d` drew "Chip <path> (<label>), <n> lines" and "In use: ..." on the GPIO card. `f5fe41b` removed both ("The GPIO card no longer lists the chip and pins"). Core still sends the facts: `status.chip` (`ok`, `path`, `label`, `lines`, `error`) and `status.pins` in `get_controls`, App:11987-12013. The page reads `status.pins` only to mark pins as taken (P:17196, 17255) and shows `status.detail` only when the state is not `running` (P:17662) | confirmed |
| The recorded reason | `/home/user/apertar-kb/working/controls/decisions.md:46`, 2026-10-30 (the user): "GPIO settings card: On, Pressed (low/high), Pull, Debounce; poll_ms and chip stay text-only (edge events need neither)". The request above reverses it | confirmed |
| Upstream has the chip definition | `key == "chip" \|\| key == "gpiochip" \|\| key == "gpio_chip"` -> `config.chipPath`, `src/hardware/GpioInput.cpp:431-432` @upstream-1.6.0; a named chip is used as is, `:507-510`; `auto` scores `/dev/gpiochip0..9`, `:238-260`, `:512-520`. Default text `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]`, UApp:4380, 4394. Upstream's WebUI shows the file as text only, so the chip is defined in the text | confirmed |
| The port's readers still take the key | `src/hardware/GpioInput.cpp:343-344`, `TriggerOutput.cpp:305-306`, `RecordingIndicatorOutput.cpp:312-313, 340-341` @cinemate-port; template App:5168, 5182; validator `src/hardware/HardwareConfigText.hpp:172, 457, 476` | confirmed |
| CSS a reinserted chip field would use (this slice) | The settings grid `.controls-settings` P:3311-3315 and its field rules P:3317-3326. The script builds one field per entry of `peripheral.settings`: `text` and `number` become `input.settings-input`, `bool` and `choice` become `select.settings-select` (P:17702-17745). A `text` chip field takes the upstream dark `.settings-input` look (U:1519-1530); a `choice` chip field would take the white look of P:3486-3495 | confirmed |
| Where the field would show | Settings, Config, Hardware card, device "Raspberry Pi GPIO": `buildControlsPeripheral(peripheral, true)` P:18215. The Controls cards are built without settings: `buildControlsPeripheral(peripheral, false)` P:17935 | confirmed |
| CSS a chip line would use (this slice) | `.controls-row-detail` P:3372-3375, as `166cc4d` did | confirmed |
| No CSS change in this slice is needed for a text chip field | Follows from the three rows above | probable: not rendered here |
| What stays header-only after the field is back | The readers take lines 0 to 63 (`src/hardware/GpioInput.cpp:141` @cinemate-port). Pin dropdowns: free pins 4 to 27 (CM:381); output `line` -1 to 27 (CM:268); chip info read for 28 lines (App:11989); pin labels "GPIO n" (P:17307). The GPIO out row and the `[trigger_output]`, `[recording_indicator]` settings have no chip field either (CM:264-271) | confirmed |

## 11. Other facts for stage 2 (not judged here)

| Fact | Evidence |
| --- | --- |
| Two CSS comments carry internal work-package numbers | "Playback (T49)" P:1979, "Playback (T50)" P:2505 |
| A CSS comment names Cinemate | P:3484-3485: "like CineMate's web GUI" |
| `body.pb-open { overflow: hidden }` exists twice | P:68-71 (the upstream rule U:65-68 with `media-browser-open` renamed) and P:1980-1982. Both `bc12c0a` |
| The comment on the GPIO out grid no longer matches the grid | P:3561 says "pin \| function \| active \| Test". The grid has four cells: function, active, Test, Remove (P:17859-17916, Remove added by `b64e6f6`); the pin select sits in the row head (P:17841-17856) |
| The comment on pin dropdowns does not hold for unsaved rows | P:3525: "The pin dropdowns (GPIO in rows, GPIO out rows) keep the page's normal dark look". The dark rules need `.controls-pin-select` (P:3526-3559). Saved rows and the GPIO out row get it (P:17348). A row just added gets `settings-select controls-pin` only (P:17453), so the white rule P:3486 applies. Class names confirmed; the look on screen is unconfirmed (no browser run) |
| Eight rules repeat `display: none` for `.hidden` | P:2027-2030, 2119-2121, 2191-2193, 2409-2411, 2568, 2582-2584, 2596-2598, 2629-2631. The global rule `.hidden { display: none !important; }` P:3943-3945 (U:1975-1977) already does it. Upstream has the same habit once: `.settings-card.hidden` U:1971-1973 |
| Four of the five `[hidden]` selectors guard a base rule that sets no `display` | `.config-diff` P:3124-3135, `.controls-review` P:3175-3182, `.controls-listen-note` P:3189-3193, `.config-issues` P:3257-3264 set no `display`. `.settings-action-row` sets `display: flex` (P:3580), so its `[hidden]` rule P:3575-3577 is needed |
| Colour literals | Variables used: `--muted` 17, `--card-border` 10, `--text` 9, `--surface` 6, `--muted-2` 3, `--radius-lg` 3, `--radius-xl` 2, `--select-bg` 2, `--select-fg` 2, `--surface-2`, `--surface-3`, `--danger` 1 each. Hex literals not in upstream CSS: `#79ddff` (3), `#8e8e98` (2), `#86efac` (2), `#1d1d21`, `#241c1f`, `#6b6b73`, `#d7d9de`, `#f4f5f7`, `#fcd34d`, `#8b8b94`. `#27272a` is written 6 times as a literal (P:3282, 3294, 3348, 3436, 3529, 3555) and 10 times as `var(--card-border)` |
| The accent `#3fd0ff` / `#79ddff` | P:2092, 2100, 2138, 2171, 2173. It is the upstream touch UI accent (`qml/ClipBrowserPage.qml:200, 222, 494, 511` @upstream-1.6.0). Upstream WebUI CSS has `#3fd0ff` once (U:1666) |
| z-index | Upstream CSS values: 0, 1, 4, 5, 84, 85, 90, 100. Added: 84 (overlay, same as upstream U:1131), 5 (menu P:2116), 10 (scrim P:2406), 8 (metadata panel P:2884) |
| Monospace stack | P:3100, 3129 repeat the upstream `.config-editor` stack U:1567 |
| `!important` | None added |
| Breakpoints differ by one pixel from upstream's | Port: `max-width: 1119px`, `719px`, `419px` paired with `min-width: 1120px` (P:2452-2879). Upstream: `max-width: 1120px`, `720px`, `420px` (U:2034, 2062, 2391). The Controls blocks use upstream's `720px` (P:3439, 3569) |
| Variant before its base rule | `.settings-action-row[hidden]` P:3575 before `.settings-action-row` P:3579 |
| The two dev branches met in one rule | P:3287-3290: selector lines by `d44b177`, body by `f5fe41b` |
| Related rules for these features sit in other slices | `:root --select-bg`, `--select-fg` P:35-36 and `body.pb-open` P:68-71 (WCP-01); `.ladder-link` P:1391 (WCP-01); the phone rules that replace U:2072-2125 (WCP-03) |

## 12. Commits that wrote the slice

Order = order in `git log --reverse origin/main..cinemate-port` (187 commits). Lines = blame inside the inserted blocks.
120 more lines inside P:1979-2945 are blamed on upstream `35dbe67`: generic lines such as `display: flex;` that git matched.

| # of 187 | Commit | Date | Author | Lines | Wrote here | fork-log |
| --- | --- | --- | --- | --- | --- | --- |
| 88 | `392e812` | 2026-10-29 | Patrik Eriksson | 12 | Toast link rules P:3970-3980 | :97, "fork-only, on GitHub (cinemate-port, 2026-10-29) (desk-tested, Pi check pending)" |
| 94 | `bc12c0a` | 2026-10-29 | Patrik Eriksson | 401 | Clip Browser P:1979-2503 | :101, "fork-only, Pi only; tested 2026-10-29" |
| 95 | `27eac5a` | 2026-10-29 | Patrik Eriksson | 5 | Card thumbnail to the edges: P:2226, 2237-2238, 2271, 2359 | :101 |
| 96 | `4629de2` | 2026-10-29 | Patrik Eriksson | 441 | Clip Viewer P:2505-2944 | :102, "fork-only, Pi only; tested 2026-10-29 ... Patrik: works well" |
| 106 | `effb804` | 2026-10-29 | Patrik Eriksson | 18 | `.config-issues` P:3257-3273 | :111, "fork-only" |
| 110 | `d282de9` | 2026-10-29 | Patrik Eriksson | 53 | First `.controls-group`, `-row`, `-line` rules; `.config-issues.info` | :118, "fork-only" |
| 112 | `166cc4d` | 2026-10-29 | Patrik Eriksson | 27 | `.controls-peripheral`, `-head`, `.controls-settings` | :120, "fork-only" |
| 115 | `f5fe41b` | 2026-10-29 | Patrik Eriksson | 5 | `.undetected` body, `.controls-row.removed`, `.controls-line.removed` | :123, "fork-only" |
| 118 | `fa3a798` | 2026-10-30 | Patrik Eriksson | 32 | Rows inside cards, `.controls-add-action`, `.controls-add-bar` | :126, "fork-only" |
| 120 | `b74b4aa` | 2026-10-30 | Patrik Eriksson | 9 | `.controls-settings .field-stack`, new-row head padding | :128, "fork-only" |
| 122 | `8be1ab5` | 2026-10-30 | Patrik Eriksson | 141 | Gutter, tools, diff box, review, Listen, chips, Scan, bus line | :130, "fork-only" |
| 124 | `d44b177` | 2026-10-31 | Patrik Eriksson | 109 | White and dark selects, GPIO out, `.controls-output-item`, `-title`, `[hidden]` row. Squash of 19 commits | :138, "offer (in pieces, after the Pi tests ...)" |
| 133 | `8a56545` | 2026-11-01 | Claude | 16 | `.diff-note`, `.diff-confirm` | No row of its own. Inside merge `4581a69`, named in :138 |
| 135 | `afa00e8` | 2026-11-01 | Claude | 7 | `.diff-info` | Same |
| 151 | `2a4266e` | 2026-11-01 | Patrik Eriksson | 7 | `.managed`, `.diff-managed` | Named in :138 |
| 176 | `1319967` | 2026-11-03 | Patrik Eriksson | 30 | Try buttons in the line grid, Remote controls | :148, "fork-only; on the Pi only" |
| 177 | `b64e6f6` | 2026-11-03 | Patrik Eriksson | 1 | Fourth column of `.controls-output-fields` P:3564 | :149, "fork-only; on the Pi only" |

Two commits that changed what this CSS shows, with no line here: `c140c4f` (#119, drops `poll_ms` and `chip` from the GPIO settings, CM) and
`a40112a` ("Loading..." texts in the Clip Browser status line, script only).

## 13. Open

| Item | Settle with |
| --- | --- |
| How the 182 rules look on screen, on a phone and on a desktop | `--simulate` Core + headless Chrome screenshots at 390, 800 and 1400 px |
| Whether a new row's pin dropdown is white while saved rows' are dark (section 11) | Same run: Settings, Controls, "+ Add GPIO button" |
| Which of the 19 commits squashed into `d44b177` used `.controls-output-item`, `.controls-output-title` | Not in this clone (`git log -S'controls-output-item'` lists `d44b177` only). The Pi or the Mac may hold `400dd1f` and its parents (fork-log:138) |
