# Review WCP-03: `src/web/WebControlPage.cpp`, port lines 4041-7162 (HTML body), against original Apertar

Stage 2 of 3. Input: `/home/user/build/review/diffs/WCP.part03.diff` (1224 lines, 16 hunks, read whole), `raw/inv-WCP-03.md`.
Yardstick: `raw/conv-webui.md` (rule ids S*, I*, N*, R*), `raw/conv-hardware-config.md` (HW 9), `raw/conv-core-command-plane.md` (C1-*). No `apertar-conventions.md` yet.

| Item | Value |
| --- | --- |
| Refs | `P:n` = port `cinemate-port` `01f170c`. `U:n` = `upstream-1.6.0` `35dbe67` (`/home/user/wt/core-upstream`) |
| Labels | confirmed unless marked. No browser run here; rendering claims are probable |
| Scope note | Markup and the start of the JS. The JS that drives these ids is WCP-04+; App/route issues (Boot Config route, env knobs) are App-1 F3/F4/F6/F7 and only cross-referenced |

## 1. Findings

| Id | Sev | Cat | Title | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | major | mismatch | Playback overlay brings its own widget layer: modal dialog, browser history, inline SVG, `h1`, nested `state.pb` | yes |
| F2 | major | new-ground | Boot Config card (config.txt editor) in System pane | yes |
| F3 | minor | removed-upstream-behaviour | Per-row Download/Delete and "Clear" selection gone from the media list | yes |
| F4 | minor | bug | `formatAngle` shows 2-decimal exact angle; no shutter pill is active at e.g. 60 fps 22.5 deg | yes (exactness), no (rounding) |
| F5 | minor | mismatch | `hidden` attribute (17x) plus five `[hidden]` CSS patches instead of the `.hidden` class | no |
| F6 | minor | mismatch | On/Off switches as new widgets (`ladder-pair`, `switch-field`, `ladder-box`) instead of `select-block` + `pill-grid two-col` | no |
| F7 | minor | mismatch | Recording-indicator switches put in the "Live preview" read-out card, not in "Assist tools" | no |
| F8 | minor | mismatch | Remote controls card on the main page | yes |
| F9 | minor | mismatch | Performance card mixes camera, preview and storage settings in System; media settings split from Media | no |
| F10 | minor | new-ground | Two new panels (Modes, Controls) with no touch UI counterpart; Value Lists filed under Controls | yes |
| F11 | minor | new-ground | Three editors for `apertar-hardware.conf` (Controls pane, Hardware card, text) | yes |
| F12 | minor | slop | Operator text carries env var, repo script path, history, Cinemate, programmer words; long copy | no |
| F13 | minor | bug | `<label>` wraps the Log pill grid: a click on "Log" or its note presses the first pill | no |
| F14 | nit | removed-upstream-behaviour | Timecode card lost its current-value pill | yes |
| F15 | nit | slop | Comments in `state` and above `formatAngle` | no |

### F1. Playback overlay brings its own widget layer (major, mismatch)

- Port: `P:6335-6494`. `#pbRemoveScrim` `role="alertdialog"` with Cancel/Remove buttons (`P:6476-6487`) for a destructive action; `history.pushState({ pb: 1 }, "")` `P:10129`, `{ pb: 2 }` `P:12777`, `popstate` `P:20637`; 7 inline `<svg>` in this overlay (`P:6345, 6364, 6413, 6452, 6467, 6474` region; 13 in the file, 0 upstream); `<h1 class="pb-h1">` `P:6341, 6399`; `state.pb` a nested object of 22 keys (`P:6716-6721`), replacing the flat `media*` keys.
- Apertar way: N4 "Destructive or system-level actions ask with a native `window.confirm`" - upstream media delete `U:10385` `if (!window.confirm("Delete " + name + " from media? This cannot be undone."))`, `U:10434`. S4 "There is no router, no URL hash, no history." S8 "Static assets = PNG icons only" - `refresh.png`, `previous.png`, `next.png`, `play.png`, `delete.png`, `film.png` all exist in `src/web/icons` @up. Upstream overlay header `<h2 class="section-title" style="margin:0;">Clip Browser</h2>` (removed lines, diff 916). I2 one flat `state` object (`U` state: `mediaFetchInFlight`, `mediaLibrary`, `mediaSelection` ...).
- Why: the overlay reads like a second app inside the page. The original developer finds a back-stack hooked into the browser history that nothing else in the page uses, a second modal system next to `window.confirm`, and SVG paths where the rest uses the shared icon folder.
- Rework: keep the grid and the viewer (new ground, mirrors the touch UI's Clip Browser, N6). In the overlay: replace `#pbRemoveScrim` with `window.confirm("Remove " + n + " clip(s)? This cannot be undone.")` in `pbOpenRemoveDialog`; delete `history.pushState`/`popstate` and the `pushed`/`viewerPushed`/`ignorePop` keys (Back button closes as upstream `closeMediaBrowserButton` did); swap the SVGs for `<img class="icon-image" src="/icons/refresh.png">` etc. (search/step arrows: glyphs or existing PNGs); `h1` -> `h2.section-title`; flatten `state.pb` to `pb*` top-level keys like the `ladder*` keys.
- Deliberate: yes. `bc12c0a` "the phone's Back closes it", "Remove Selected (dialog)", "in the touch UI's shape (T49)".

### F2. Boot Config card (major, new-ground)

- Port: `P:5859-5951`, `#settingsBootConfigCard`: two camera ports, link frequency, RP1 overclock, display, I2C, I2S, SPI, onboard audio, View/Edit/Download/Upload, "Save & Reboot". Copy names `/boot/firmware/config.txt`, "the RP1 clock", backup `config.txt.apertar.bak`.
- Apertar way: no precedent. Upstream WebUI never writes outside Core's own files; N8 lists what the WebUI does not do; HW 9 "One hand-edited file is the operator's surface for hardware". Core side is App-1 F4 (own route outside `/api/command`), F6 (1355-line editor), F7 (unauthenticated LAN route writes config.txt as root).
- Markup notes: card copy is fixed text that names RP1 for every board while the JS hides the RP1 field when `bootState.rp1.available` is false (`P:20164`) - the copy should follow (pi-compat nit). The card has 9 hidden-until-JS blocks and a 60-word copy (N7).
- Verdict: rework or park. It stays only if App-1 F7 is resolved (helper scope, confirm, origin). If kept: shorten copy to one sentence, move the RP1 sentence into `bootConfigRp1Note` only, `window.confirm` before Save & Reboot (N4: restart is a confirmed action, `U:11325`).
- Deliberate: yes (`8a56545`, `3b87d99`, `2a4266e`; fork-log:138 "Not yet run on the camera").

### F3. Per-row actions removed from the media list (minor, removed-upstream-behaviour)

- Upstream: every row had Download (an `<a download>`) and Delete (`U:7765-7790`), plus Select All / Clear / Download Selected / Delete Selected (removed lines, diff 976-979), and a Newest/Oldest `<select>`.
- Port: one clip is removed or downloaded only after opening it in the viewer (`#pbvRemove`, `#pbvDownload` `P:6431-6442`) or after an 800 ms long press starts a selection (`P:11881-11896`). No "Clear" button. With a mouse, long press is not discoverable. Every item, stills and audio included, opens `pbvOpen` (`P:11812-11814`).
- Rework: add a visible "Select" toggle in the sheet head next to `pbSortButton` that sets `state.pb.selecting`, and a "Clear" when selecting; keep long press as a shortcut.

### F4. Exact shutter angle loses the active pill (minor, bug)

- Port: `P:7172-7181` `return formatAngleValue((Number(us) / (1000000 / safeFps)) * 360);`, `formatAngleValue` = `toFixed(2)`. Pill values come from `formatAngleValue(entry.angle)` (`P:7619-7621`); `buildOptionButtons` marks active by string equality (I6).
- Upstream: `U:4690` snapped to the nearest `shutterOptions` label.
- Failing input: fps 60, operator taps 22.5 deg. `shutterAngleToUs` sends `round(22.5/360 * 16666.67)` = 1042 us. Shown back: 1042*60*360/1e6 = 22.5072 -> "22.51°". Pills hold "22.5°": none is active, the badge reads 22.51. Same for 15 deg at 60 fps ("14.99°"). Probable at runtime; arithmetic confirmed.
- Rework: in `formatAngle`, return the label of a list entry within 0.05 deg of the computed angle (the tolerance `shutterAngleEntriesForSnapshot` already uses, `P:7612`), else the exact value.

### F5. `hidden` attribute instead of `.hidden` (minor, mismatch)

- Port: 17 `hidden>` attributes in this slice (`P:5769, 5773, 5778, 5818, 5827, 5868, 5869, 5924, 5936, 6147-6151, 6182, 6183, 6228, 6229`); needs per-class patches `.config-diff[hidden]` `P:3137`, `.controls-review[hidden], .controls-listen-note[hidden]` `P:3184`, `.config-issues[hidden]` `P:3266`, `.settings-action-row[hidden]` `P:3575`. The same slice also uses class `hidden` (`P:4912`, 5868 area `bootConfigCam0LinkField`).
- Apertar way: I11 "element hidden with `.hidden` (`display: none !important`, 1975)"; I7 state classes include `hidden`. `grep -c ' hidden>'` U = 0.
- Rework: `class="... hidden"` on those 17 elements, `classList.toggle("hidden", ...)` in the JS (26 `.hidden =` sites in the port), delete the five `[hidden]` rules.

### F6. New switch widgets (minor, mismatch)

- Port: `.pill-grid.ladder-pair { grid-template-columns: repeat(2, 88px); }` `P:1184`, used for Speed Ramp `P:4989`, UI and File timecode `P:5089, 5093`, Mode Ladder `P:5176`; `.switch-field` `P:860` (Speed Ramp head); `.ladder-box` (Mode Ladder).
- Apertar way: I6 "On/Off toggles are a two-pill grid over `toggleOptions`"; R1 step 3 `settings-option-group > section.select-block > div.select-topline > span` + `div.pill-grid`; size modifier `two-col` (I7, `U:759`). Upstream: 0 `ladder-pair`, 0 `switch-field`.
- Why: a class named after one feature (ladder) is now the timecode widget.
- Rework: replace `ladder-pair` by `two-col` (or plain `pill-grid`) inside a `select-block`; drop `.switch-field` and put "Allow speed ramping" in a `select-block` under the card head; keep `.ladder-box` only for the running-now crop tile.

### F7. Recording indicators in the wrong card (minor, mismatch)

- Port: `P:5274-5291`, four `field-stack > span.input-label + pill-grid` rows appended inside "Live preview", whose copy is "Current preview transport and monitoring endpoint for the web feed." (a `capture-list` read-out).
- Apertar way: R1 step 3; overlays live in "Assist tools" "Manage monitoring overlays and assist modes." (`U:3183-3215`) as `settings-option-group > select-block`.
- Rework: move the four rows into "Assist tools" as `select-block`s (one `settings-option-group` "Recording indicators").

### F8. Remote controls on the main page (minor, mismatch)

- Port: `P:4558-4590`, a card under Camera settings, icon `settings.png`.
- Apertar way: S3 "The main page holds only the camera-critical controls (exposure, resolution, record). Everything else is in the settings overlay."
- Rework: move `#remoteControlsRows` into the Controls panel (where the Try buttons of the same feature already are, `1319967`). If the owner wants it on the main page, record it as a deliberate exception for the handoff.

### F9. Performance card placement (minor, mismatch)

- Port: `#settingsPerformanceCard` `P:5780-5830` in System: Preview temporal denoise (`camera_settings.conf preview_tdn`), Trim, Frame-rate phase lock (`camera_settings.conf`), Frames per folder and Merge (`apertar-hardware.conf [storage]`). `arrangeSettingsPanels` (`P:10093-10101`) moves Media / Format / Media Speed to the Media panel, not this card.
- Apertar way: S4 panels by topic; S5 the media cards are moved into `power` ("Mounted recording media, eject, format, and write speed tools", `settingsPanelMeta.power`).
- Rework: preview TDN -> Monitoring "Live preview" (it affects preview only); phase lock -> Record; Trim, Frames per folder, Merge -> a "Recording media" card added to the `moveSettingsCards(mediaPanel, [...])` list. Card copy "The defaults are the fastest" goes.

### F10. Modes and Controls panels (minor, new-ground)

- Port: nav `P:4750-4773`, `settingsPanelMeta.modes`, `.controls` `P:6627-6650`; Value Lists card `P:6161-6169` in Controls, no `settings-card-copy`.
- Apertar way: S4 order mirrors the touch UI sidebar; port touch UI `defaultSidebarOrder` (`Apertar-UI/qml/SettingsPage.qml:848-858` @port) has neither. R3 step 2: every card has `h3` + one-sentence copy.
- Verdict: keep both panels (the WebUI already differs with Config, S4). Move Value Lists to Record or Modes (it sets FPS/ISO/shutter/WB lists, not what a button does; Controls copy "What each button, knob and pin does."), give it one copy sentence. Note in the handoff that the touch UI has no Modes/Controls entries.
- Deliberate: yes (`854fe43`, `6777ebe`).

### F11. Three editors for one hardware file (minor, new-ground)

- Port: Controls pane `P:6137-6160`, Hardware card `P:6172-6191` ("The text editor below shows the same file."), text editor with Saved versions / Check / diff `P:6192-6235`.
- Apertar way: HW 9 "One hand-edited file is the operator's surface for hardware; the WebUI offers a raw text editor, not forms" (`U:3840-3870`).
- Verdict: keep Controls (owner-valued; its GPIO chip setting was restored on request). Simplify: the Hardware card and the Controls pane each have their own pill, message, pending box, Reload and Save; one shared message/pending component and one Save path would halve the markup. Keep the text editor and its diff/Check (extends upstream in place, conforms).
- Deliberate: yes (`f5fe41b` Why).

### F12. Operator text (minor, slop)

| Where | Text | Rule |
| --- | --- | --- |
| `P:5818` | "Set by APERTAR_CDNG_FRAMES_PER_FOLDER" | App-1 F3, N7 |
| `P:5813` | "(as before) ... or tools/flatten_clip.py" | history narration, repo path in UI |
| `P:4912` | `data-search="log cinemate encode bit depth"` | foreign product name |
| `P:4734` | placeholder "e.g. log, buffer, tally, GPIO 21, pre-roll" | fine; keep short |
| `P:5792` | "about six times faster per frame at 4K Clear HDR 16-bit" | measurement claim, Pi 5 ISP; `e625c68` says "probable" |
| `P:5195` | "Resolutions array" | programmer word, N6 |
| `P:4996` | "Audio (experimental)" | |
| `P:5864`, `P:5813`, `P:4940` | 40-75-word copies | N7 one sentence ~6-15 words |

Rework: one sentence per card copy, consequences only; no env names, script paths, product names or "as before".

### F13. `<label>` around the Log pill grid (minor, bug)

- Port: `P:4913-4917` `<label class="field-stack field-span-2"><span class="input-label">Log</span><div class="pill-grid" id="settingsCdngLogOptions"></div><p ...>Linear storage.</p></label>`. A `<label>` without `for` labels its first labelable descendant; `button` is labelable. A click on "Log" or on the note text clicks the first pill. Probable (HTML label activation; not run in a browser).
- Upstream has the same shape once (`U:2828-2831`, still Timelapse), so not a mismatch; the port's own Write buffer field next to it uses a `div` (`P:4920`).
- Rework: `<div class="field-stack field-span-2">`.

### F14. Timecode value pill removed (nit, removed-upstream-behaviour)

- Upstream `U:3016` `<div class="online-pill" id="settingsTimecodeValue">Free Run</div>`. Port drops it when splitting the card (`909aaa5`). Cards with a pill list carry the current value in the head (Gyro Data `P:4935`). Rework: one pill "UI: Time of Day - Files: Clip", or accept and note.

### F15. Comments (nit, slop)

- `P:6714-6729` four trailing comments in `state`; `P:7172-7173` comment above `formatAngle`. I9: 2 comment lines in the whole upstream script. Drop the `state` comments; keep at most the one-line reason for the exact angle.

## 2. Abstraction verdicts (inventory section 8)

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `#playbackOverlay` page model (`state.pb`, two pages, history back-stack) | rework-to-upstream-pattern | Keep the two pages; drop history, custom dialog, SVG, nesting (F1) |
| Settings search (`data-search` + `applySettingsSearch`) | keep | Small, UI-only, no Core change; searches text plus keywords. Strip foreign words (F12). Document as new for the original developer |
| `.ladder-pair` / `ladder-*` widget family | rework-to-upstream-pattern | Use `pill-grid two-col` in `select-block` for switches; keep ladder classes for the ladder list only (F6) |
| Hidden-until-capable rows (`hidden` attribute) | rework-to-upstream-pattern | Pattern is right (I11 "does not exist for this configuration -> hidden"); mechanism must be `.hidden` (F5) |
| Controls / Hardware / Boot Config generated forms with review diff | simplify | Controls keep; Hardware card merge its message/save plumbing with Controls; Boot Config park until App-1 F7 (F2, F11). Diff-before-save on the text editor conforms in spirit to N4 |

## 3. Protocol

- No markup-level protocol break. `set_timecode_mode` keeps "no target = both, as before" (`909aaa5`), so an unmodified UI still works. Wire values "Free Run"/"Rec Run" kept; only labels changed (`2c259b9`), and the port touch UI uses the same labels (`SettingsPage.qml:21`), so N6 parity holds.

## 4. Conforms

- New panels follow S4: `button.settings-nav-item[data-panel]`, `section.settings-panel[data-panel]`, entries in `settingsPanelMeta` (`P:4750-4773`, `P:6627-6650`).
- Nav icons reuse PNGs from `/icons/` (`resolution.png`, `settings.png`; S8).
- Ids follow I7 almost everywhere (`settingsSpeedRampOptions`, `settingsPreviewTdnOptions`, `storagePrerollButton`, `reloadControlsButton`).
- Performance card rows use `select-block > select-topline` exactly as R1/R2 (`P:5783-5829`).
- Button variants per I12 (`primary-button` Save, `secondary-button` Reload, `danger-button` Remove).
- Config text editor extended in place: same textarea id, gutter wrapper, Check, diff, revision (`P:6192-6235`).
- Mode Ladder greying is "exists but not now -> disabled" with a link (I11).
- Removal of the `.media-browser-*` 720px rules (`P:4041-4104`) is clean: no dead selectors left.
- Timecode split keeps the old command shape (protocol above).

## Skeptic

Stage 3. Every finding re-read on both sides (`P` = `cinemate-port` `01f170c`, `U` = `upstream-1.6.0` `35dbe67`).

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Holds: `history.pushState` P:10129/12777, `popstate` P:20637, 0 `pushState`/`<svg>` in U, 8 `window.confirm` in U (U:10385 media delete). Details fixed: scrim is P:6475-6487; the overlay markup has 6 inline SVGs (P:6355, 6371, 6401, 6433, 6449, 6455) plus the check badge built in JS (P:11833); `h1` at P:6351, 6397 |
| F2 | corrected | Card and RP1 copy confirmed (P:5863, RP1 field hidden by JS at P:20164). Wrong evidence removed: fork-log:138 "Not yet run on the camera" is the `drop-frames` row, not Boot Config; N8 does not say "writes only Core's own files". Save already sits behind a diff view with Save and Reboot / Save Only / Back (P:20304-20306), so the proposed `window.confirm` is dropped from the rework |
| F3 | stands | U:7767-7790 per-row Download/Delete, U:4020 Clear; P:6380-6390 has no Clear and no per-card action; selection starts only by 800 ms long press (P:11880-11896) |
| F4 | stands | `formatAngle` P:7174-7177 -> `toFixed(2)`; `shutterAngleToUs` rounds to whole us (P:7187); pills are `formatAngleValue(entry.angle)` (P:7618). 22.5 deg at 60 fps -> 1042 us -> 22.51 deg. Probable (assumes Core echoes the sent value; a sensor-quantized value makes it worse) |
| F5 | stands | 17 `hidden` attributes, five `[hidden]` rules (P:3137, 3184-3185, 3266, 3575), 26 `.hidden =` sites in P; U has `.hidden` class (U:1975) and one `option.hidden` on an `<option>` (U:9526), no markup `hidden` |
| F6 | corrected | Apertar way restated: upstream two-state switches are `field-stack` + `input-label` + `pill-grid two-col` (U:2805-2813) or `select-block` (30x in U). The port's timecode rows already have the field-stack shape (P:5087-5094); only the modifier `ladder-pair` (88 px columns, P:1184) and the head `.switch-field` (P:860, P:4987) differ |
| F7 | stands | P:5274-5291 toggles inside the read-out card "Live preview"; U overlays in "Assist tools" select-blocks (U:3180-3215) |
| F8 | stands | P:4567-4580 card in the left main column; conv-webui S3 "main page holds only camera-critical controls"; deliberate per `1319967` |
| F9 | stands | P:5781-5830 Performance card mixes TDN, trim, phase lock, frames per folder, merge; `arrangeSettingsPanels` P:10093-10101 moves only Media/Format/Speed cards |
| F10 | stands | Nav P:4750 (modes), panel P:6137 (controls); Value Lists P:6163-6170 has no copy; touch UI sidebar `defaultSidebarOrder` Apertar-UI qml/SettingsPage.qml:848-858 has no Modes/Controls; `854fe43`, `6777ebe` |
| F11 | stands | Controls card P:6137-6160 and Hardware card P:6172-6191 each own pill/message/pending/Reload/Save; text editor P:6192-6235; conv-hardware-config:221 |
| F12 | stands | Lines confirmed: P:5818 env var, P:5813 "(as before)", P:4912 `data-search="log cinemate ..."`, P:5792 "about six times faster", P:5195 "Resolutions array", P:5863 75-word copy |
| F13 | stands | P:4913-4917 `<label class="field-stack">` wraps `#settingsCdngLogOptions`. Same shape upstream for Timelapse (U:2828-2831 = P:4829-4832): follows Apertar, still a bug. Probable (not run in a browser) |
| F14 | stands | `settingsTimecodeValue` 0x in P, U:3016; `909aaa5` split the card |
| F15 | corrected | State comments are at P:6673-6685 (`fpsSwitchingTo`, `ladderServer`, `ladderDraft`, `ladderAspects`), not P:6714-6729; formatAngle comment P:7172-7173 confirmed |

No findings dropped. None added.

## Final findings

### WCP-03-F1 [mismatch, major] Playback overlay brings its own widget layer: modal dialog, browser history, inline SVG, h1, nested state.pb
- Where: `src/web/WebControlPage.cpp:6335-6494@cinemate-port`; `:6475-6487` (scrim); `:10129`, `:12777` (pushState); `:20637` (popstate); `:6351`, `:6397` (h1); `:6720-6725` (state.pb); `:11833` (SVG badge)
- Port way: `#pbRemoveScrim` `role="alertdialog"` for Remove; `history.pushState({pb:1|2})` + `popstate` back-stack; 6 inline `<svg>` in the overlay markup and one in JS; `<h1 class="pb-h1">`; `state.pb` a nested object of 22 keys.
- Apertar way: N4 destructive actions use `window.confirm` (`src/web/WebControlPage.cpp:10385@upstream-1.6.0` `if (!window.confirm("Delete " + name + " from media? This cannot be undone."))`); S4 no router, no history (0 `pushState` in U); S8 PNG icons only (`refresh.png`, `previous.png`, `next.png`, `play.png`, `delete.png`, `film.png` in `src/web/icons@upstream-1.6.0`; 0 `<svg>` in U); old header `<h2 class="section-title">Clip Browser</h2>`; I2 flat state keys (`mediaLibrary`, `mediaSelection`).
- Why it matters: the overlay reads as a second app: a second modal system, a history hook nothing else uses, SVG paths where the rest uses the icon folder.
- Rework: keep grid and viewer. `pbOpenRemoveDialog` -> `window.confirm("Remove " + n + " clip(s)? This cannot be undone.")`, delete `#pbRemoveScrim` and its CSS/keyboard guard (P:12966, 20634); delete `history.pushState`/`popstate` and `pb.pushed`/`viewerPushed`/`ignorePop` (Back button closes like `closeMediaBrowserButton`); SVGs -> `<img class="icon-image" src="/icons/refresh.png">`, `previous.png`, `next.png` etc.; `h1` -> `h2.section-title`; flatten `state.pb` into top-level `pb*` keys.
- Effort: M. Deliberate: yes (`bc12c0a`: "in the touch UI's shape (T49)", "Remove Selected (dialog)", "the phone's Back closes it").

### WCP-03-F2 [new-ground, major] Boot Config card: a config.txt editor in the System pane
- Where: `src/web/WebControlPage.cpp:5859-5951@cinemate-port`; `:20164` (RP1 field hidden by JS); `:20304-20306` (diff view buttons)
- Port way: a card with sensor per CSI port, link frequency, RP1 overclock, display, I2C/I2S/SPI/audio, View/Edit/Download/Upload; Save shows a diff with Save and Reboot / Save Only / Back. 75-word card copy names the RP1 clock for every board.
- Apertar way: no precedent. Upstream WebUI writes only its own libraries through routes (config, presets, media; conv-webui C3-S3); conv-hardware-config:221 "one hand-edited file is the operator's surface"; system actions confirm with `window.confirm` (`src/web/WebControlPage.cpp:11325@upstream-1.6.0`).
- Why it matters: it writes `/boot/firmware/config.txt` as root through an unauthenticated route (App-1 F4/F6/F7). The static copy names RP1 even where the JS hides the RP1 field.
- Rework: park until App-1 F7 is resolved. If kept: one-sentence card copy; RP1 text only in `bootConfigRp1Note`; keep the diff view as the confirm step (no extra dialog); document as new architecture for the original developer.
- Effort: M. Deliberate: yes (`8a56545`, `3b87d99`, `2a4266e`; came in with PR #1 merge `4581a69`, fork-log).

### WCP-03-F3 [removed-upstream-behaviour, minor] Per-row Download/Delete and the Clear-selection button removed from the media list
- Where: `src/web/WebControlPage.cpp:6376-6390@cinemate-port`; `:11880-11896@cinemate-port`
- Port way: to act on one item, open it in the viewer or long-press 800 ms to start a selection; no Clear button; Newest/Oldest is a toggle chip.
- Apertar way: every row had `<a download>` Download and a Delete button (`src/web/WebControlPage.cpp:7765-7790@upstream-1.6.0`), plus Select All / Clear / Download Selected / Delete Selected (`:4020-4022@upstream-1.6.0`).
- Why it matters: with a mouse the long press cannot be found; deleting one still or audio file goes through the viewer.
- Rework: add a visible Select toggle next to `pbSortButton` that sets the selecting flag, and a Clear button while selecting; keep long press as a shortcut.
- Effort: S. Deliberate: yes (`bc12c0a` "the touch UI's Clip Browser is a grid of cards").

### WCP-03-F4 [bug, minor] Exact shutter angle (2 decimals) leaves no pill active, e.g. 60 fps at 22.5 deg
- Where: `src/web/WebControlPage.cpp:7172-7181@cinemate-port`; `:7605-7621@cinemate-port`; `:15284-15286@cinemate-port`
- Port way: `formatAngle` returns `formatAngleValue(exact)` = `toFixed(2)`; `shutterAngleToUs` rounds to whole us; pills compare labels by string.
- Apertar way: `src/web/WebControlPage.cpp:4690@upstream-1.6.0` snapped the shown angle to the nearest `shutterOptions` label.
- Why it matters: fps 60, tap 22.5 deg -> 1042 us sent -> shown as 22.5072 -> "22.51°" != "22.5°", no pill active; 15 deg at 60 fps shows "14.99°". Probable (assumes Core echoes the sent us).
- Rework: in `formatAngle`, return the label of a list entry within 0.05 deg (the tolerance `shutterAngleEntriesForSnapshot` uses, P:7612), else the exact value.
- Effort: S. Deliberate: no (`ff33d2d` chose the exact angle on purpose; rounding effect not mentioned; tested with node --check only).

### WCP-03-F5 [mismatch, minor] hidden attribute (17x) and five [hidden] CSS patches instead of the .hidden class
- Where: `src/web/WebControlPage.cpp:5769-5827@cinemate-port`; `:5868-5936`; `:6147-6229`; `:3137`; `:3184-3185`; `:3266`; `:3575`
- Port way: `<div ... hidden>` on 17 elements, 26 `.hidden =` JS sites, plus `.config-diff[hidden]`, `.controls-review[hidden]`, `.controls-listen-note[hidden]`, `.config-issues[hidden]`, `.settings-action-row[hidden]` to beat `display:flex`; the same slice also uses the `hidden` class.
- Apertar way: I11/I7 hide with the class (`src/web/WebControlPage.cpp:1975@upstream-1.6.0` `.hidden { display: none !important; }`); no markup `hidden` attribute in U; the one `.hidden =` is on an `<option>` (`:9526@upstream-1.6.0`).
- Why it matters: two hiding mechanisms; every new class with a display rule needs its own `[hidden]` patch or shows by mistake.
- Rework: `class="... hidden"` on the 17 elements, `classList.toggle("hidden", ...)` at the 26 JS sites, delete the five `[hidden]` rules.
- Effort: S. Deliberate: no.

### WCP-03-F6 [mismatch, minor] On/Off switches built from new widget classes (ladder-pair, switch-field)
- Where: `src/web/WebControlPage.cpp:1184@cinemate-port`; `:860`; `:4987-4989`; `:5087-5094`; `:5171-5176`
- Port way: `.pill-grid.ladder-pair` (`repeat(2, 88px)`), commented as the Mode Ladder's, is also the Speed Ramp, UI timecode and File timecode switch; `.switch-field` puts "Allow speed ramping" in the card head.
- Apertar way: two-state switches are `field-stack` + `input-label` + `pill-grid two-col` (`src/web/WebControlPage.cpp:2805-2813@upstream-1.6.0`, `.two-col` at `:759`) or a `section.select-block` (30 in U). 0 `ladder-pair`/`switch-field` in U. The port's timecode rows already have the field-stack shape; only the modifier differs.
- Why it matters: a class named after one feature has become the general switch; these switches look different from upstream ones.
- Rework: `ladder-pair` -> `two-col` on the Speed Ramp and timecode grids; drop `.switch-field` and put "Allow speed ramping" in a field-stack or select-block under the head; keep `ladder-*` classes for the ladder list and its tiles only.
- Effort: S. Deliberate: no.

### WCP-03-F7 [mismatch, minor] Recording-indicator switches placed in the Live preview read-out card
- Where: `src/web/WebControlPage.cpp:5274-5291@cinemate-port`
- Port way: four field-stack + input-label + pill-grid rows (Recording frame, Frame buffer bar, Red timecode, Audio outline) appended to "Live preview" (copy: "Current preview transport and monitoring endpoint for the web feed.").
- Apertar way: overlays are select-blocks in "Assist tools" ("Manage monitoring overlays and assist modes.", `src/web/WebControlPage.cpp:3180-3215@upstream-1.6.0`), R1 step 3.
- Why it matters: toggles end up in a status card.
- Rework: move them into Assist tools (or a "Recording indicators" card in Monitoring) as one `settings-option-group` with four select-blocks.
- Effort: S. Deliberate: no.

### WCP-03-F8 [mismatch, minor] Remote controls card on the main page
- Where: `src/web/WebControlPage.cpp:4567-4580@cinemate-port`
- Port way: a new card under Camera settings in the main grid.
- Apertar way: S3 the main page holds only camera-critical controls; everything else is in the settings overlay (`src/web/WebControlPage.cpp:2457-2726@upstream-1.6.0`).
- Why it matters: widens the main page with a hardware-test tool.
- Rework: move `#remoteControlsRows` into the Controls panel next to the Try buttons, or record it as an owner-approved exception.
- Effort: S. Deliberate: yes (`1319967` "The main page gets a Remote controls card under Camera settings").

### WCP-03-F9 [mismatch, minor] Performance card mixes camera, preview and storage settings in System
- Where: `src/web/WebControlPage.cpp:5781-5830@cinemate-port`; `:10093-10101@cinemate-port`
- Port way: one System card holds `preview_tdn`, `fps_phase_lock` (camera_settings.conf), media trim, `frames_per_folder`, `clip_merge` ([storage]); `arrangeSettingsPanels` moves the media cards to Media but not this one.
- Apertar way: S4 panels by topic; S5 `arrangeSettingsPanels` moves media cards into the "power" (Media) panel (`src/web/WebControlPage.cpp:6119-6128@upstream-1.6.0`).
- Why it matters: media settings split across two panels; "Performance" is not an upstream topic.
- Rework: Preview TDN -> Monitoring / Live preview; phase lock -> Record; Trim, Frames per folder, Merge -> a recording-media card added to `moveSettingsCards(mediaPanel, ...)`.
- Effort: S. Deliberate: no (`c810f85` gives a reason, does not weigh the panel topics).

### WCP-03-F10 [new-ground, minor] Modes and Controls panels have no touch UI counterpart; Value Lists filed under Controls
- Where: `src/web/WebControlPage.cpp:4750-4773@cinemate-port`; `:6137`; `:6163-6170@cinemate-port`
- Port way: two new nav entries; Value Lists (FPS/ISO/shutter/WB lists) at the end of Controls ("What each button, knob and pin does."), no card copy.
- Apertar way: S4 order mirrors the touch UI sidebar (Apertar-UI `qml/SettingsPage.qml:848-858@cinemate-port` has neither entry); R3 every card has an h3 and one copy sentence.
- Why it matters: Value Lists are not hardware controls; operators look for them where the pickers are.
- Rework: keep both panels (WebUI already differs with Config). Move Value Lists to Record or Modes with one copy sentence; note the WebUI-only panels in the handoff.
- Effort: S. Deliberate: yes (`854fe43`, `6777ebe`).

### WCP-03-F11 [new-ground, minor] Three editors for apertar-hardware.conf (Controls pane, Hardware card, text editor)
- Where: `src/web/WebControlPage.cpp:6137-6160@cinemate-port`; `:6172-6191`; `:6192-6235`
- Port way: generated forms in Controls and Hardware, each with its own state pill, message, pending box, Reload and Save, next to the text editor.
- Apertar way: conv-hardware-config:221 "one hand-edited file ... raw text editor, not forms" (`src/web/WebControlPage.cpp:3840-3870@upstream-1.6.0`).
- Why it matters: three save paths to one file; message/pending plumbing duplicated.
- Rework: keep Controls and the text editor; let the Hardware card share one message/pending/save component with Controls; document the forms as new architecture.
- Effort: M. Deliberate: yes (`f5fe41b` "Config the hardware itself, graphically and as text").

### WCP-03-F12 [slop, minor] Operator text: env var name, history narration, Cinemate keyword, programmer words, long copy
- Where: `src/web/WebControlPage.cpp:5818@cinemate-port`; `:5813`; `:4912`; `:5792`; `:5195`; `:5863`
- Port way: "Set by APERTAR_CDNG_FRAMES_PER_FOLDER"; "(as before)" and Resolve/Premiere notes; `data-search="log cinemate ..."`; "about six times faster per frame at 4K Clear HDR 16-bit"; "Resolutions array"; 40-75-word card copies.
- Apertar way: N7 card copy one sentence of ~6-15 words stating the operator consequence ("Fan control and temperature management.", `src/web/WebControlPage.cpp:3632@upstream-1.6.0`); N6 operator vocabulary.
- Why it matters: reads like ticket notes to the original developer and the operator.
- Rework: one sentence per copy; remove env names, "as before", the Cinemate keyword and unmeasured speed claims; "Resolutions array" -> "Resolutions".
- Effort: S. Deliberate: no.

### WCP-03-F13 [bug, minor] A <label> wraps the Log pill grid: clicking "Log" or its note presses the first pill
- Where: `src/web/WebControlPage.cpp:4913-4917@cinemate-port`
- Port way: `<label class="field-stack field-span-2">` around `#settingsCdngLogOptions` buttons and the note.
- Apertar way: upstream has the same shape once (`src/web/WebControlPage.cpp:2828-2831@upstream-1.6.0`, Timelapse; still at P:4829-4832), so not a mismatch; the port's Write buffer field next to it uses a div (P:4920).
- Why it matters: a label without `for` activates its first labelable descendant, a button; a click on the label text or note presses the first pill. Probable (not run in a browser).
- Rework: `<div class="field-stack field-span-2">`; the upstream Timelapse label has the same defect and can take the same one-word fix.
- Effort: S. Deliberate: no.

### WCP-03-F14 [removed-upstream-behaviour, nit] Timecode card lost its current-value pill
- Where: `src/web/WebControlPage.cpp:5080-5094@cinemate-port`
- Port way: `settingsTimecodeValue` removed when the card split into UI and File timecode.
- Apertar way: `src/web/WebControlPage.cpp:3016@upstream-1.6.0` `<div class="online-pill" id="settingsTimecodeValue">Free Run</div>`; card heads show the current value.
- Why it matters: small loss of an at-a-glance value.
- Rework: one pill such as "UI Time of Day / Files Clip", or accept and note it.
- Effort: S. Deliberate: yes (`909aaa5`).

### WCP-03-F15 [slop, nit] Comments in the state object and above formatAngle
- Where: `src/web/WebControlPage.cpp:6673-6685@cinemate-port`; `:7172-7173@cinemate-port`
- Port way: four trailing comments on state fields (`fpsSwitchingTo`, `ladderServer`, `ladderDraft`, `ladderAspects`) and a two-line comment above `formatAngle`.
- Apertar way: I9 two JS comment lines in the whole upstream script.
- Why it matters: style drift.
- Rework: drop the state comments; keep at most one line on why the angle is exact.
- Effort: S. Deliberate: no.
