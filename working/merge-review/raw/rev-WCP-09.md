# Review WCP-09: Controls / Hardware / Remote controls JS in WebControlPage.cpp (stage 2)

Scope: `/home/user/build/review/diffs/WCP.part09.diff`, read completely. One hunk, +2084 lines, new-file
lines 16622-18740 of `src/web/WebControlPage.cpp` @cinemate-port `01f170c` (diff line N = port line N+16616).
Upstream: `/home/user/wt/core-upstream` @upstream-1.6.0. Yardstick: `raw/conv-webui.md` (C3-*),
`raw/conv-core-command-plane.md` (C1-*). `P:` = port WCP, `U:` = upstream WCP. All claims confirmed (read in
code) unless labelled. No browser run here; commits record desk Chrome tests against a mock (d282de9 20/20,
fa3a798 39/39, 8be1ab5 60/60, f5fe41b 33/33) and Pi tests for 1319967, 9b5ea14.

## Summary

The slice is a client-side application of 74 functions and 19 module-level bindings: a structured editor of
`apertar-hardware.conf` (Controls panel, Hardware card on Config), a Remote controls card on the main page,
Listen, a review-in-words, undo, history. It builds DOM the upstream way (createElement, textContent, no
innerHTML), confirms destructive actions with `window.confirm`, sends flat scalar commands and shows Core's
refusal text. It departs from upstream in four structural ways: its own store (`controlsState` + 18 module
consts/lets) instead of `state` (C3-I2); its own fetch wrapper `controlsCall` instead of `sendCommand`
(C3-S3, C3-I4); a non-camera-critical card on the main page (C3-S2); a third poll loop (C3-I3). The feature
is deliberate and valuable (d282de9 "Why"), but at ~2100 lines it is 50x upstream's typical feature size
(conv-webui 0: "20-40 lines in 3-5 places"). Recommended: keep the rows/action-dropdown/add/remove/save core,
re-home its state and calls, drop or shrink the extras (chips, remote card, review re-derivation, tally
function dropdown).

## Findings

| Id | Cat | Sev | Title | Deliberate | Effort |
| --- | --- | --- | --- | --- | --- |
| WCP-09-F1 | mismatch | major | Second client store `controlsState` + 18 module-level consts/lets | unknown | M |
| WCP-09-F2 | mismatch | major | Second fetch wrapper `controlsCall`; hand-checked `ok`, no try/catch at 7 call sites | unknown | S |
| WCP-09-F3 | mismatch | major | Remote controls card on the main page, with hold-to-repeat pills | yes | S |
| WCP-09-F4 | new-ground | major | A 2100-line structured editor with extras; size and shape foreign to upstream | yes | L |
| WCP-09-F5 | bug | minor | Saving Controls or Hardware silently drops the other card's unsaved edits | no | S |
| WCP-09-F6 | bug | minor | Pins recovered by regex from Core's display text | no | S |
| WCP-09-F7 | bug | minor | Unhandled rejections: Scan sticks at "Scanning...", Listen overlaps requests | no | S |
| WCP-09-F8 | mismatch | minor | Listen is a third poll loop (300 ms) with its own timer outside `state` | yes | S |
| WCP-09-F9 | new-ground | minor | Chip editor: a duck-typed fake `<select>` with drag and drop | yes | S |
| WCP-09-F10 | mismatch | minor | Inline message/review/pending boxes duplicate toasts (second notification area) | yes | S |
| WCP-09-F11 | removed-upstream-behaviour | minor | Tally `enabled` hidden and derived from the pin; None/Remove erases the wiring | yes | S |
| WCP-09-F12 | mismatch | minor | Hardware-file writes through commands while upstream's door is `/api/config` | yes | M |
| WCP-09-F13 | pi-compat | minor | Any DPI line greys GPIO 0-27 regardless of overlay | yes | S |
| WCP-09-F14 | duplication | minor | Issues box x3, Test handler x2, kind-name map x3, DPI loop x2, pin-taken vs pin-owners | no | S |
| WCP-09-F15 | slop | minor | 127 comment lines incl. T39-T42 ticket ids and "as in Cinemate" | no | S |
| WCP-09-F16 | mismatch | nit | bool settings as Yes/No `<select>`; inline grid style; "GPIO in" vs "GPIO buttons" | no | S |
| WCP-09-F17 | slop | nit | One-entry "Function" dropdown (`controlsOutputFunctions`, "add more") | no | S |

### F1 mismatch, major. Second client store

- Port: `P:16633` `const controlsState = { loading, saving, revision, model, peripherals, catalog, edits: new Map(), buttons: new Map(), removed: new Set(), added: [], settingEdits: new Map(), buses, scans, dpiLines, apply, history, listening }`.
  Module-level mutable state besides it: `controlsChipLines` P:16798, `controlsSeparateTurns` P:16881,
  `controlsReplaced` P:17216, `let controlsListenTimer` / `controlsListenSeq` P:18601-18602. Plus 13 const
  tables (P:16652-16669, 16688, 16928, 17162, 17232, 17292, 17581-17585, 17821).
- Upstream: one `const state = {` U:4204-4266; timers `state.<x>Timer`, busy `state.<x>InFlight`
  (C3-I2 "always"; violation example "New module-level `let` variables; state kept in ... a second store").
  The config editor next door keeps `state.configDirty`, `state.configFetchInFlight`, `state.configSaveInFlight`
  (U:10265-10285, 10304-10359). The port itself follows this for the config text: `state.configLoadedText`,
  `state.configRevision` (P:18716, 18720).
- Why it matters: the original developer finds page state in two places; WCP-08 (`frameBufferBar`) and
  WCP-06 (`pb`) add more stores; the page then has four.
- Rework: move fields into `state` as flat names: `state.controlsModel`, `controlsRevision`, `controlsCatalog`,
  `controlsPeripherals`, `controlsEdits`, `controlsButtons`, `controlsRemoved`, `controlsAdded`,
  `hardwareEdits` (was `settingEdits`), `controlsLoadInFlight`, `controlsSaveInFlight`, `controlsListenTimer`,
  `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced`. Delete `controlsState`. Constant label
  tables (`controlsGroups`, `controlsStateNames`, `controlsNewTitles`) move to the list block at the top of the
  script (C3-S6, U:4039-4127). Effort M (mechanical rename across ~300 references).

### F2 mismatch, major. Second fetch wrapper

- Port: `P:16698-16705` `async function controlsCall(payload) { const response = await fetch("/api/command", {...}); return await response.json(); }`.
  16 call sites; each checks `result.ok` by hand. No try/catch at: Test buttons P:17687, P:17895; Scan P:18183;
  `controlsRecheckSoon` P:18518; `loadControlsHistory` P:18556; `undoLastControlsSave` P:18583, 18588; Listen
  P:18629.
- Upstream: `sendCommand` U:9109-9145 is the one door (C3-S3; violation example "a second fetch wrapper"),
  throws `new Error(result.error || "Command failed.")`; handlers `try { await sendCommand(...) } catch (error) { showToast(error.message, true) }` (C3-I4, 86 of 95).
  For commands with no snapshot patch `applyCommandSnapshotPatch` returns false and only a 140 ms state refresh
  is scheduled, so `sendCommand` is safe for `test_input`, `scan_i2c`, `get_controls` etc.
- Why `controlsCall` exists (probable): `set_controls` failures carry `issues`, `new_errors`, `code`, which
  `sendCommand` drops. The port already solved the same need for `/api/config` by attaching the payload to the
  Error (`failure.payload = payload`, P:18930-18931).
- Rework: in `sendCommand`, `const error = new Error(result.error || "Command failed."); error.result = result; throw error;`
  (two lines). Delete `controlsCall`; every caller becomes `await sendCommand({...})` in the C3-I4 try/catch; the
  save paths read `error.result.issues` / `.code`. Fixes F7 at the same time. Effort S.

### F3 mismatch, major. Remote controls card on the main page

- Port: HTML card in the left main column `P:4569-4580` ("Remote controls", under Camera settings); renderer
  `renderRemoteControls` P:18047-18112 with `buildRemoteButton` P:17995-18042 (pointer capture, 450 ms delay,
  140 ms repeat). Bootstrap fetches `get_controls` every 5 s until it answers so the card can fill (P:20870-20878).
- Upstream: main grid holds only preview, Camera settings, System, Current capture (U:2456-2726; C3-S2 "always";
  violation example "A new main-page card for a non-critical feature"). No hold-to-repeat anywhere (U grep
  `pointerdown`: only the standby activity listener U:11515).
- The same function exists in Settings, Controls as Try buttons on every line (P:16942-16952, 1319967 adds both).
- Rework: delete the main-page card, `renderRemoteControls`, `buildRemoteButton` and the bootstrap retry; Try
  on the Controls rows covers "check what a saved line does from afar". If the owner wants a remote pad, make
  it a `settings-card` in the Controls panel built with `buildOptionButtons` (one command per click, C3-I6) and
  load it in `setSettingsPanel` like the other panel loads (U:6164-6166). Effort S. Deliberate: yes (1319967
  "The main page gets a Remote controls card under Camera settings").

### F4 new-ground, major. Size and shape of the editor

- Port: 74 functions, ~2100 lines for one settings panel plus one Config card. Upstream's whole Config card is
  ~100 lines (U:10265-10360) and a typical feature is 20-40 lines (conv-webui section 0). Upstream edits
  buttons/knobs as text only (`POST /api/config`, U:10330-10359).
- Value is real and weighed: d282de9 "you had to know the action names and the key syntax, and a typo was
  found only when a button did nothing".
- Verdict: simplify. Keep: one row per control, action dropdown from `list_actions`, gesture dropdown, add/remove,
  pin dropdowns, revision-checked `set_controls` save, Hardware card fields. Drop or defer: chip editor (F9),
  remote card (F3), review re-derivation of moved rows (P:18452-18486, the Config text diff already shows the
  change), Turn-adjusts pairing by `_up`/`_down` id convention and label regex (P:16875-16880, 17066-17119:
  keep only if Core's catalog sends the pair), pin-claim cascade that removes another control
  (`controlsClaimPin` P:17312-17343: a disabled option with "used by ..." is the upstream disabled-not-hidden
  rule, C3-I11, and is enough), the one-entry function dropdown (F17). Estimated result: under 1000 lines.
  Effort L.

### F5 bug, minor. One card's save drops the other card's unsaved edits

- Port: `saveHardware` P:18240 and `saveControls` P:18668 call `loadControls(true)`; `loadControls` resets
  `settingEdits`, `edits`, `added`, `removed`, `buttons` (P:18283-18297) without asking (`discard` undefined).
  `saveHardware` sends only non-tally `settingEdits` (P:18223-18226); `saveControls` sends only Controls edits
  and tally settings (P:18332-18333).
- Failing input: on Controls change GPIO 6 Press to "Eject media" (unsaved); open Config, change a NeoRotary
  setting, press Save Hardware. GPIO 6 edit is gone, no prompt. Reverse also holds for Hardware fields.
- The port guards this on the text-editor path (`if (!controlsDirty() && !hardwareDirty()) await loadControls(true);` P:18938-18939),
  so the two save paths are inconsistent with it.
- Rework: after a save, reload only when the other card is clean, else re-read revision and model and keep the
  other card's edits (or ask with `window.confirm`, C3-N3). Effort S.

### F6 bug, minor. Pins parsed from display text

- Port: `controlsRowPinInfo` P:17163-17189 reads switch pins from `row.title` with `/^GPIO (\d+)(?: \+ (\d+))?$/`
  and encoder pins from `row.detail` with `/^A (\d+), B (\d+), push (\d+|none)$/`; `controlsPcfPinsInUse`
  takes the PCF pin from the title's last digits (P:17598). Core builds those strings for display:
  `ControlsModel.hpp:163` `row.title = "GPIO " + first + " + " + second;`, `:193-194` `"A " + ... value_or("?")`.
- Failing input: `[gpio_encoders] encoder0_b` missing -> detail "A 5, B ?, push none" -> regex fails ->
  `controlsRowPinInfo` null -> the encoder has no pin dropdowns and is absent from `controlsPinOwners`, so a
  new button is offered GPIO 5 without a "used by" mark (Core then refuses on save; probable).
- Upstream: render reads fields from the snapshot, never parses its own labels (C3-I3; `state.snapshot` U:9334).
- Rework: Core adds `"pins":"5,6,13"` (one string, C1-I09 style) per row next to the existing `"pin"`
  (`ControlsModel.hpp:353`); `controlsRowPinInfo` splits it. Effort S.

### F7 bug, minor. Unhandled rejections and overlapping polls

- Port: Scan P:18183-18189 sets `scans[bus] = { loading: true }` then awaits `controlsCall` with no catch; a
  network error or a non-JSON reply (`response.json()` throws) leaves "Scanning..." and a disabled Scan button
  until Reload. Listen `setInterval(async ..., 300)` P:18624-18648 has no in-flight guard; a slow Core stacks
  requests. Same missing catch at the sites listed in F2.
- Upstream: every fetch has try/catch/finally and `*InFlight` guards (U:10304-10327).
- Rework: comes with F2; Listen gets `state.controlsListenInFlight`. Effort S.

### F8 mismatch, minor. Listen: a third poll loop

- Port: P:18609-18649, `setInterval` 300 ms on `controls_last_input`, stops after 120 s or when the panel is hidden.
- Upstream: one 1 s poll (U:11609, C3-I3, C3-N8 "1 s polling only"). WCP-08 adds a second (4 Hz `/api/buffer`).
- Verdict simplify: short-lived and user-started, so the poll itself is acceptable; put the timer and seq on
  `state` and go through `sendCommand`. Alternative with no new loop: add `controls_last_input_seq/section/key`
  to `/api/state` and highlight from `renderSnapshot` (1 s latency). Effort S. Deliberate: yes (8be1ab5).

### F9 new-ground, minor. Chip editor as a fake select

- Port: `buildControlsActionEditor` P:16799-16872: a `div` that defines `value` and `disabled` with
  `Object.defineProperty` (P:16831-16835) and dispatches a synthetic `change`, draggable chips, "x" buttons,
  a "Several actions..." sentinel option (`__several__`).
- Upstream: no custom widget; choices are pill grids or native selects (C3-I5, violation example "custom
  dropdown components"). A value the dropdown does not know is already shown "(as written in the file)"
  by the port's own `buildControlsSelect` (P:16785-16790).
- Verdict simplify: drop the chip box; a multi-action line shows as "(as written in the file)" and is edited
  in Config text. If kept, a plain `settings-input` holding `iso200,fps24` is the least foreign form. Effort S.

### F10 mismatch, minor. Second notification area

- Port: inline boxes `controlsMessage`, `hardwareMessage`, `controlsPending`, `hardwarePending`,
  `controlsReview`, `settingsConfigIssues`; a save shows "Saved. Core applies it now." inline AND toasts
  "Controls saved." (P:18671-18673, 18243-18245).
- Upstream: one toast (C3-N4, violation example "inline success banners; a second notification area");
  upstream `saveConfigFile` toasts only (U:10351).
- Verdict: keep one inline box for Core's issue list with line numbers (no toast can hold it; new ground, worth
  it); success and "applies after the take" go to the toast only. Effort S.

### F11 removed-upstream-behaviour, minor. Tally enabled derived from the pin

- Port: `enabled` field skipped (P:17704-17705); `syncTallyEnabled` P:17637-17646 writes `enabled` from "pin
  set"; pin None and Remove write `line=-1`, `pcf_pin=-1` (P:17847-17851, 17907-17909).
- Upstream: `RecordingIndicatorOutput.cpp:339` reads `enabled` and `:349` `line` independently, so an operator
  can switch the LED off and keep its wiring.
- Effect: from Controls, switching the tally off erases its pin; turning it back on needs the pin re-entered.
  (Its `chip` key is not shown either; covered by rev-HW-controls-model F1, fixed on work/improve.)
- Rework: show `enabled` as an On/Off pill pair (`toggleOptions`, C3-I5) and leave `line`/`pcf_pin` alone.
  Deletes `tallyFileEnabled`, `syncTallyEnabled`, the `keepEdit` special cases (P:17756-17757, 17812). Effort S.

### F12 mismatch, minor. Two doors to the same file

- Port: the page reads and writes `apertar-hardware.conf` through commands `get_controls`, `set_controls`
  (incl. whole-file `text` for Undo, P:18588), `controls_history`, while the text editor uses `GET/POST /api/config`.
- Upstream: file work in the config library is a route, `POST /api/config` (U:10336-10340; C3-S9 "always").
  Key-level edits through a command have precedent too (`set_imu_*` write one key, conv-hardware-config 7), so
  `set_controls` with `set.` / `unset.` keys is acceptable; the whole-file `text` write via a command is the
  duplicate door (rev-HW-config-text-store F5: it skips `/api/config`'s checks).
- Rework: Undo posts the history text through `POST /api/config` like the editor; `set_controls` loses `text`.
  Effort M (Core side in other units). Protocol: no break of an unmodified original UI (new commands only;
  the parser unescapes `\n`, `ControlProtocol.cpp:86`).

### F13 pi-compat, minor (probable)

- Port: `if (controlsState.dpiLines.length > 0) for (let pin = 0; pin <= 27; ++pin) taken.add(pin);` P:17198-17200,
  again P:17261-17264; text P:18209 "it holds GPIO 0 to 27".
- 24-bit DPI uses GPIO 0-27; 18-bit and 16-bit modes (`dpi18`, `rgb565` variants) leave the upper pins free
  (probable, from Raspberry Pi DPI docs; settle by reading `hwconf::parseConfigTxt` and the overlays used).
- Rework: Core sends the held pins (`dpi_pins`) per overlay; the page greys exactly those. Effort S.

### F14 duplication, minor

- `showControlsMessage` P:16718, `showHardwareMessage` P:18129, `showConfigIssues` P:18686: same body, different id.
- Test-output click handler P:17687-17690 and P:17895-17898 identical.
- Kind-name map three times: `controlsKindNames` P:17232, literal maps P:17388, P:17445.
- DPI 0-27 loop in `controlsPinsTaken` P:17193 and `controlsPinOwners` P:17252; the two functions compute
  nearly the same set (owners minus row/entry bookkeeping).
- Turn-pair edit write P:17096-17101 repeats `setControlsValue` P:16883-16890.
- Rework: one `showIssueBox(id, title, issues, isInfo)`; one `requestTestOutput(peripheral)` (C3-I6 `request<Action>`);
  use `controlsKindNames` everywhere; `controlsPinsTaken = new Set(controlsPinOwners(...).keys())`. Effort S.

### F15 slop, minor

- 95 full-line and 32 trailing `//` comments in the slice. Upstream page: 2 comment lines in 7573 (C3-I7).
- Ticket ids: `T41` P:16795, 16874, 17066; `T42` P:17679, 18397, 18554, 18600; `T40` P:18176; `T39` P:18531.
  Cinemate reference: P:16983 "as in Cinemate". Narration: P:18338 "a pin edited before the row was removed".
- Rework: delete ticket ids and Cinemate references; keep at most one-line reasons where a rule is not obvious
  (e.g. P:16744-16746 turns get only stepping actions). Effort S.

### F16 mismatch, nit

- bool settings render as a Yes/No `<select>` (P:17716-17726); upstream On/Off is a two-pill grid over
  `toggleOptions` (U:4066, C3-I5).
- `grid.style.gridTemplateColumns = "repeat(" + ... + ")"` P:18065; upstream uses `pill-grid two-col|three-col` classes (U:755).
- GPIO card retitled "GPIO in" on Controls (P:17936-17940) while Config shows Core's "GPIO buttons" (C3-N5 wording).
- `loadControls` vs upstream `fetch<X>` naming (C3-I6). Effort S.

### F17 slop, nit

- `const controlsOutputFunctions = [["tally", "Tally light"]];` P:17821 with comment "Tally light for now; add more";
  a select with one fixed option (P:17859-17870). Rework: drop the select, title the row "Tally light". Effort S.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `controlsCall` | rework-to-upstream-pattern | `sendCommand` with `error.result` (F2) |
| `controlsState` + module consts | rework-to-upstream-pattern | flat fields in `state`, label tables in the list block (F1) |
| Edit model `edits/buttons/removed/added/settingEdits` -> `controlsPayload` | keep | key-level edits need a staging model; output is flat `set.`/`unset.` scalars (C1-I09); merge `buttons` into `edits` if F4 trims gestures |
| Pin ownership (`controlsPinOwners`, `controlsRowPinInfo`, `controlsPinChoices`, `controlsClaimPin`) | simplify | pins from a Core field (F6), one owners function (F14), disabled "used by" options instead of claim-and-remove (F4) |
| Chip box `buildControlsActionEditor` | simplify | drop or plain text field (F9) |
| `buildRemoteButton` | rework-to-upstream-pattern | goes with the main-page card; pills via `buildOptionButtons` if kept (F3) |
| Tally helpers | simplify | `enabled` as On/Off pills; helpers deleted (F11) |
| Listen poller | simplify | timer on `state`, in-flight guard, `sendCommand` (F8) |
| `renderControlsReview` + `controlsDescribe` | simplify | list payload keys with `controlsDescribe`; drop the moved-row re-derivation (F4) |
| Message boxes x3 | rework-to-upstream-pattern | one issue-box helper for issue lists; everything else toast (F10, F14) |

## Conforms

- DOM built with `createElement` + `textContent`; no `innerHTML` in the slice (C3-I9; e.g. P:16718-16742).
- Destructive actions ask with `window.confirm` worded as a question: reload-discard P:18258 (mirrors U:10307),
  pin replace P:17317, undo P:18581 (C3-N3).
- Status pill Loading / Saving / Unsaved / Ready and Save/Reload enabling copy `updateConfigEditorControls`
  (U:10265-10285) in `updateControlsButtons` P:16707 and `updateHardwareButtons` P:18118.
- Requests are flat scalar objects; booleans as `"true"`/`"false"` strings (`set(section, "enabled", "true")`
  P:18387; C1-I09, C3-I5).
- Core is the source of truth: action catalog from `list_actions`, pins from `gpio_pins`, Try runs the saved
  file, saves revision-checked, Core's refusal text shown verbatim (C3-N1, C3-N2, C3-I4).
- Unavailable vs absent: undetected devices hidden on Controls, greyed on Config; held pins disabled, not removed (C3-I11).
- Success toast for button-driven saves ("Controls saved.", "Hardware settings saved."; C3-N4).
- Upstream classes reused: `settings-select`, `settings-input`, `field-stack`, `input-label`, `secondary-button`,
  `danger-button`, `pill-button`, `select-block`, `select-topline`, `online-pill` (C3-I8).
- `renderHardwareConfig` extended by 5 lines, new fields on `state` (P:18716-18721; C3-I2).
- ids camelCase with kind suffix: `saveControlsButton`, `reloadHardwareButton`, `controlsRows` (C3-I6).

## Skeptic

Checked at `cinemate-port` `01f170c` (P:) against `upstream-1.6.0` (U:). Commits read with `git show -s`; fork-log and `working/controls/decisions.md` read for intent.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | `controlsState` P:16633-16651 confirmed; module-level `controlsChipLines` P:16798, `controlsSeparateTurns` P:16881, `let controlsListenTimer/Seq` P:18601-18602. Upstream has only `const state` U:4204 plus constant option lists U:4039-4091. |
| F2 | corrected | 15 call sites (not 16). Rework fixed: Listen must not go through `sendCommand`, which schedules a 140 ms `/api/state` refresh and moves `state.deferFetchUntilMs` on every call (U:9112-9141); at 300 ms that adds about 3 state fetches/s. Background polls keep a plain fetch, precedent U:11509-11513 (`user_activity`, `.catch(() => {})`). |
| F3 | corrected | Card, retry loop and pointer capture confirmed (P:4569-4580, 20870-20878, 18032-18038). Owner chose to keep Remote controls on 2026-11-04 ("everything back", fork-log.md:163-164). Rework moves the pad into the Controls panel instead of deleting it. |
| F4 | stands | 74 functions in P:16622-18740 confirmed; `controlsClaimPin` removes another control after a confirm (P:17312-17343). Deliberate (decisions.md:47 "T39-T45 built lean"). |
| F5 | stands | `saveHardware`/`saveControls` call `loadControls(true)` with `discard` undefined, so no confirm, and it resets `settingEdits`, `edits`, `added`, `removed`, `buttons` (P:18240, 18256-18297, 18667). |
| F6 | stands | Regexes P:17174, 17183 confirmed; Core builds `detail` with `value_or("?")` (ControlsModel.hpp:193-194) and only a numeric `pin` per row (:353). |
| F7 | corrected | Scan stays stuck until the page is reloaded, not until Reload: `scans` is written only at P:18184/18187 and `loadControls` does not clear it. Also: Undo (P:18577-18597) sets no busy flag, so Save can run during it. |
| F8 | corrected | Loop confirmed (P:18620-18648). Rework no longer routes it through `sendCommand` (see F2). |
| F9 | stands | `Object.defineProperty` value/disabled, synthetic change, `draggable`, `__several__` (P:16799-16872). No draggable or defineProperty anywhere upstream. |
| F10 | corrected | Severity nit. Persistent status lines have upstream precedent (`settingsImuCalibrationStatus` U:3007, set U:9572), so the issues list and pending note stay; only the inline success sentence duplicates the toast. |
| F11 | corrected | Category bug, not removed-upstream-behaviour: Core still reads `enabled` and `line` independently (RecordingIndicatorOutput.cpp:339, 349); the port card cannot express "off, wiring kept" and writes `line=-1`/`pcf_pin=-1` (P:17900-17913). |
| F12 | corrected | Where adds Check: `set_controls ... text=... dry_run=true` (P:18795) is a third text path through the command. |
| F13 | corrected | The 0-27 rule is Core's too (HardwareConfigText.hpp:844-845, 869-871); the page mirrors it. Rework starts in Core. |
| F14 | stands | Three identical issue-box bodies (P:16718, 18129, 18686), two literal kind maps beside `controlsKindNames` (P:17232, 17388, 17445), two `test_output` handlers (P:17688, 17896). |
| F15 | stands | 95 full-line + 32 trailing comments in P:16622-18740; T39-T42 and "as in Cinemate" confirmed; upstream script has 2 comment lines. |
| F16 | corrected | Bool-as-select dropped: upstream uses selects for on/off (U:3791-3794 "Keep On"/"Off"; `createFavoriteSelectBlock` with `toggleOptions` U:6850). Inline `gridTemplateColumns` (P:18065 vs class toggle U:9150), "GPIO in" retitle (P:17936-17940) and `loadControls` vs `fetch*` (U:10207-10361) stand. |
| F17 | stands | `controlsOutputFunctions` one entry, fixed select (P:17821, 17859-17870). |

## Final findings

### WCP-09-F1 [mismatch, major] Second client store `controlsState` plus module-level mutable state
- where: src/web/WebControlPage.cpp:16633@cinemate-port; :16798; :16881; :17216; :18601-18602
- port way: `const controlsState = { loading, saving, revision, model, peripherals, catalog, edits, buttons, removed, added, settingEdits, buses, scans, dpiLines, apply, history, listening }`; besides it `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced`, `let controlsListenTimer`/`controlsListenSeq`, and 13 const tables.
- Apertar way: one `const state = {` src/web/WebControlPage.cpp:4204-4266@upstream-1.6.0; timers `state.<x>Timer`, busy `state.<x>InFlight`; config editor `state.configDirty/configFetchInFlight/configSaveInFlight` (:10265-10359). C3-I2.
- why it matters: the original developer looks for page state in `state` and finds a second store (four with WCP-06 `pb` and WCP-08 `frameBufferBar`).
- rework: flat fields on `state`: `controlsModel`, `controlsRevision`, `controlsCatalog`, `controlsPeripherals`, `controlsEdits`, `controlsButtons`, `controlsRemoved`, `controlsAdded`, `hardwareEdits`, `controlsLoadInFlight`, `controlsSaveInFlight`, `controlsListenTimer`, `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced`. Delete `controlsState`. Label tables go to the option-list block at the top of the script (C3-S6, U:4039-4127).
- effort M; deliberate unknown (no commit discusses it; the port itself keeps config-text state on `state`, P:18716, 18720).

### WCP-09-F2 [mismatch, major] Second fetch wrapper `controlsCall`; hand-checked `ok`, missing try/catch
- where: src/web/WebControlPage.cpp:16698-16705@cinemate-port; :17687; :18183; :18556; :18583-18588
- port way: `async function controlsCall(payload)` posts to `/api/command` and returns the JSON; 15 call sites test `result.ok` by hand; 7 have no try/catch.
- Apertar way: `sendCommand` src/web/WebControlPage.cpp:9109-9145@upstream-1.6.0 is the door for actions; it throws `new Error(result.error || "Command failed.")`; handlers `try { await sendCommand(...) } catch (error) { showToast(error.message, true) }` (C3-S3, C3-I4). A plain fire-and-forget fetch exists only for background traffic (`user_activity`, :11509-11513).
- why it matters: two command paths with different error semantics; failures at unguarded sites become unhandled rejections (F7).
- rework: in `sendCommand`: `const error = new Error(result.error || "Command failed."); error.result = result; throw error;` (same as the port's `/api/config` save, P:18930-18931). User-action calls (save, undo, scan, test, history, get_controls, list_actions) use `sendCommand` in try/catch; save paths read `error.result.issues/.code`. The Listen poll stays a plain fetch (sendCommand would schedule a `/api/state` refresh per poll) wrapped in try/catch with an in-flight flag on `state`. Delete `controlsCall`.
- effort S; deliberate unknown (probable reason: `set_controls` failures carry `issues`/`code` that `sendCommand` drops).

### WCP-09-F3 [mismatch, major] Remote controls card on the main page with hold-to-repeat pills
- where: src/web/WebControlPage.cpp:4569-4580@cinemate-port; :17995-18042; :18047-18112; :20870-20878
- port way: a "Remote controls" card under Camera settings in the main grid; pills call `test_input`; knob arrows repeat while held (pointer capture, 450 ms delay, 140 ms interval); bootstrap retries `get_controls` every 5 s until Core answers.
- Apertar way: the main grid holds only preview, Camera settings, System, Current capture (src/web/WebControlPage.cpp:2456-2726@upstream-1.6.0; C3-S2). No hold-to-repeat anywhere upstream. Panel data loads in `setSettingsPanel` (:6164-6166).
- why it matters: changes the camera-critical main page; duplicates the Try buttons on every Controls line; adds a load-time request loop.
- rework: keep the feature (owner restored it 2026-11-04, fork-log.md:163-164) but move it off the main page: a settings-card in the Controls panel, pills built with `buildOptionButtons`, one command per click, data loaded from `setSettingsPanel("controls")`. Delete the main-page card and the bootstrap retry loop. Hold-to-repeat goes, or stays as the one documented new-ground widget.
- effort S; deliberate yes (1319967: "The main page gets a Remote controls card under Camera settings").

### WCP-09-F4 [new-ground, major] 2100-line structured hardware editor with extras
- where: src/web/WebControlPage.cpp:16622-18740@cinemate-port; :16875-16880; :17312-17343; :18452-18486
- port way: 74 functions: per-device cards, gesture dropdowns, chips, Turn-adjusts pairing by `_up/_down` id and label regex, a pin claim that removes another control after a confirm, a review in words that re-derives moved rows, Listen, Undo, history, Scan, Test.
- Apertar way: no precedent for a structured editor; upstream edits `apertar-hardware.conf` as text via `POST /api/config` (src/web/WebControlPage.cpp:10330-10359@upstream-1.6.0); a typical WebUI feature is 20-40 lines in 3-5 places (conv-webui section 0).
- why it matters: the original developer must maintain a client application larger than any upstream feature, with pin-ownership rules duplicated from Core's validator.
- rework: simplify. Keep rows, action dropdown from `list_actions`, gesture dropdown, add/remove, pin dropdowns with disabled "used by" options, revision-checked `set_controls` save, Hardware card fields. Drop the chip editor (F9), the main-page card (F3), the moved-row re-derivation in `renderControlsReview` (the Config diff shows the change), the `controlsClaimPin` cascade (a disabled option is the upstream rule, C3-I11), the one-entry function dropdown (F17); keep Turn adjusts only if Core's catalog sends the pair. Document what stays as new ground for the original developer.
- effort L; deliberate yes (d282de9 Why; extras in fa3a798, 8be1ab5, 1319967; decisions.md:47).

### WCP-09-F5 [bug, minor] Saving Controls or Hardware silently drops the other card's unsaved edits
- where: src/web/WebControlPage.cpp:18240@cinemate-port; :18667; :18256-18297
- port way: `saveHardware` and `saveControls` call `loadControls(true)` (no `discard`, so no confirm), which resets `settingEdits`, `edits`, `added`, `removed`, `buttons`; each save sends only its own card's edits. The text-editor save guards with `if (!controlsDirty() && !hardwareDirty())` (P:18938).
- Apertar way: no precedent for two editors; upstream asks before discarding edits: `window.confirm("Reload Apertar config and discard unsaved edits?")` src/web/WebControlPage.cpp:10307@upstream-1.6.0 (C3-N3).
- why it matters: change GPIO 6 Press on Controls (unsaved), change a NeoRotary setting on Config, press Save Hardware: the GPIO 6 change is gone without a prompt.
- rework: after a save, reload the model only if the other card is clean; otherwise update the revision and keep the other card's edits (they are key-level), or ask with `window.confirm`.
- effort S; deliberate no.

### WCP-09-F6 [bug, minor] Pins recovered by regex from Core's display text
- where: src/web/WebControlPage.cpp:17163-17189@cinemate-port; :17598; src/hardware/ControlsModel.hpp:163@cinemate-port; :193-194; :353
- port way: `controlsRowPinInfo` parses `row.title` `/^GPIO (\d+)(?: \+ (\d+))?$/` and `row.detail` `/^A (\d+), B (\d+), push (\d+|none)$/`; `controlsPcfPinsInUse` takes the PCF pin from the title's trailing digits. Core builds those strings for display, with `value_or("?")`.
- Apertar way: render reads data fields from the snapshot (`state.snapshot` src/web/WebControlPage.cpp:9334@upstream-1.6.0; C3-I3); no label parsing.
- why it matters: `encoder0_b` missing gives detail "A 5, B ?, push none", the regex fails, the encoder gets no pin dropdowns and its pins are absent from `controlsPinOwners`, so GPIO 5 is offered unmarked to another control (Core refuses on save; probable).
- rework: Core adds `"pins":"5,6,13"` (one string) per row next to `"pin"` (ControlsModel.hpp:353); `controlsRowPinInfo` splits it; delete the regexes.
- effort S; deliberate no.

### WCP-09-F7 [bug, minor] Unhandled rejections: Scan sticks at "Scanning...", Listen overlaps, Undo unguarded
- where: src/web/WebControlPage.cpp:18183-18189@cinemate-port; :18620-18648; :18516-18528; :18577-18597
- port way: Scan sets `scans[bus]={loading:true}` then awaits `controlsCall` with no catch; a network error or non-JSON reply leaves Scan disabled and "Scanning..." until the page is reloaded (`loadControls` never clears `scans`). Listen `setInterval(async, 300)` has no in-flight guard. Undo awaits two calls without try/catch and without a busy flag.
- Apertar way: every fetch in try/catch/finally with `state.<x>InFlight` guards (`fetchConfigFile` src/web/WebControlPage.cpp:10304-10327@upstream-1.6.0).
- why it matters: stuck UI after one failed request; a slow Core receives stacked Listen requests; Save can run during an Undo.
- rework: with F2: `sendCommand` in try/catch, `loading` cleared in `finally`; `state.controlsListenInFlight` for the poll; Undo sets `state.controlsSaveInFlight`.
- effort S; deliberate no.

### WCP-09-F8 [mismatch, minor] Listen is a second network poll loop (300 ms) with its timer outside `state`
- where: src/web/WebControlPage.cpp:18600-18649@cinemate-port
- port way: `setInterval` 300 ms on `controls_last_input`, auto-off after 120 s or when the panel is hidden; timer and seq in module-level `let`.
- Apertar way: one network poll: `window.setInterval(() => fetchState(true), 1000)` src/web/WebControlPage.cpp:11609@upstream-1.6.0 (C3-I3, C3-N8); timers on `state`.
- why it matters: with WCP-08's `/api/buffer` poll the page has three loops; timing state is scattered.
- rework: either keep the short user-started poll with timer, seq and in-flight flag on `state`, as a plain fetch in try/catch (not `sendCommand`, see F2); or add `controls_last_input_seq/section/key` to `/api/state` and highlight from `renderSnapshot` (1 s latency, no new loop).
- effort S; deliberate yes (8be1ab5 "Listen lights the row of the control you press"; decisions.md:24).

### WCP-09-F9 [new-ground, minor] Chip editor: duck-typed fake select with drag and drop
- where: src/web/WebControlPage.cpp:16799-16872@cinemate-port; :16831-16835
- port way: a div that defines `value` and `disabled` via `Object.defineProperty`, dispatches a synthetic `change`, draggable chips with x buttons, a `__several__` sentinel option.
- Apertar way: no precedent; choices are pill grids or native selects (C3-I5, violation example "custom dropdown components"). The port's own `buildControlsSelect` already shows an unknown value as "(as written in the file)" (P:16785-16790).
- why it matters: a widget behaviour no other control on the page has; hard to maintain.
- rework: drop the chip box; multi-action lines show "(as written in the file)" and are edited in Config text. If kept, a plain `settings-input` holding `iso200,fps24`.
- effort S; deliberate yes (8be1ab5, T41).

### WCP-09-F10 [mismatch, nit] Inline success message duplicates the toast
- where: src/web/WebControlPage.cpp:18671-18673@cinemate-port; :18243-18245; :18509-18513
- port way: a save writes "Saved. Core applies it now." into `controlsMessage`/`hardwareMessage` and toasts "Controls saved."/"Hardware settings saved.".
- Apertar way: one toast, `showToast` src/web/WebControlPage.cpp:7804-7813@upstream-1.6.0; `saveConfigFile` toasts only (:10351); C3-N4 ("inline success banners"). Persistent status lines do exist upstream (`settingsImuCalibrationStatus` :3007, :9572).
- why it matters: two feedback channels for one event.
- rework: success and "applies after the take" go into the toast text; keep the issue list (line numbers) and the pending note as status lines.
- effort S; deliberate yes (8be1ab5 "Saves say Core applies them now, or after the take").

### WCP-09-F11 [bug, minor] Tally card cannot switch off with wiring kept: None/Remove erases the pin
- where: src/web/WebControlPage.cpp:17617-17646@cinemate-port; :17704-17705; :17900-17913
- port way: `enabled` field hidden; `syncTallyEnabled` writes `enabled` from "pin set"; pin None and Remove write `line=-1`, `pcf_pin=-1`; a file with `enabled=false` shows its pin as None.
- Apertar way: Core reads `enabled` (RecordingIndicatorOutput.cpp:339@upstream-1.6.0) and `line` (:349) independently, so the LED can be off with its wiring kept.
- why it matters: switching the tally off from Controls erases its pin; turning it on again needs the pin re-entered.
- rework: show `enabled` as an On/Off control over `toggleOptions`; leave `line`/`pcf_pin` untouched; delete `tallyFileEnabled`, `syncTallyEnabled` and the special cases in `tallyShown` and Remove.
- effort S; deliberate yes (comment P:17617-17618).

### WCP-09-F12 [mismatch, minor] Whole-file text through a command while upstream's door is `/api/config`
- where: src/web/WebControlPage.cpp:18588@cinemate-port; :18795; :18264
- port way: Undo sends the whole history text via `set_controls text=`; Check sends the editor text via `set_controls text= dry_run=true`; the text editor saves through `POST /api/config`.
- Apertar way: whole-file work is a route: `POST /api/config` src/web/WebControlPage.cpp:10336-10340@upstream-1.6.0, App:7175-7195@upstream-1.6.0 (C3-S9). Key-level command writes have precedent (`set_imu_*`, conv-hardware-config 7).
- why it matters: two doors with different checks for the same file (`set_controls text=` skips the `/api/config` empty/size/NUL checks, rev-HW-config-text-store F5).
- rework: Undo posts the history text through `POST /api/config`; Check uses a dry-run on the same route (header or query flag); `set_controls` drops `text`. Key-level `set_controls` stays.
- effort M; deliberate yes (8be1ab5).

### WCP-09-F13 [pi-compat, minor] Any DPI line greys GPIO 0-27, in the page and in Core's validator
- where: src/web/WebControlPage.cpp:17198-17200@cinemate-port; :17260-17264; :18209; src/hardware/HardwareConfigText.hpp:844-845@cinemate-port; :869-871
- port way: `if (dpiLines.length > 0) for (pin = 0; pin <= 27; ++pin) taken.add(pin)`; Core's validator refuses any `gpio <= 27` when a DPI line exists; the note says "it holds GPIO 0 to 27".
- Apertar way: no precedent.
- why it matters: probable: 16/18-bit DPI modes leave upper GPIO free; those pins become unusable for buttons. Settle by reading the overlays in use and their pin maps.
- rework: Core computes the pins each detected overlay holds and sends them (`dpi_pins`); validator and page use that set; the page drops its own 0-27 loops.
- effort S; deliberate yes (9b5ea14; DPI greying tested desk only).

### WCP-09-F14 [duplication, minor] Issue box x3, Test handler x2, kind-name map x3, pin sets x2
- where: src/web/WebControlPage.cpp:16718@cinemate-port; :18129; :18686; :17687-17690; :17895-17898; :17232; :17388; :17445
- port way: `showControlsMessage`/`showHardwareMessage`/`showConfigIssues` have the same body; `test_output` click handler twice; kind names in `controlsKindNames` and two literal maps; `controlsPinsTaken` and `controlsPinOwners` compute nearly the same set.
- Apertar way: shared helpers by role: `setText`, `setFormValue`, `buildOptionButtons`, `showToast` (src/web/WebControlPage.cpp:6172-6189, 9147-9167, 7804@upstream-1.6.0); `request<Action>` naming (C3-I6).
- why it matters: every fix must be made in several places.
- rework: one `showIssueBox(id, title, issues, isInfo)`; one `requestTestOutput(peripheral)`; `controlsKindNames` everywhere; `controlsPinsTaken` = keys of `controlsPinOwners`.
- effort S; deliberate no.

### WCP-09-F15 [slop, minor] 127 comment lines incl. T39-T42 ticket ids and "as in Cinemate"
- where: src/web/WebControlPage.cpp:16795@cinemate-port; :16874; :16983; :17066; :17679; :18176; :18397; :18531; :18554; :18600
- port way: 95 full-line and 32 trailing `//` comments; T41 x3, T42 x4, T40, T39; "as in Cinemate".
- Apertar way: 2 JS comment lines in the whole upstream script (src/web/WebControlPage.cpp:8474-8475@upstream-1.6.0); C3-I7.
- why it matters: ticket ids and Cinemate references mean nothing to the original developer.
- rework: delete ticket ids, Cinemate references and narration; keep at most one-line reasons where a rule is not obvious.
- effort S; deliberate no.

### WCP-09-F16 [mismatch, nit] Inline grid style, "GPIO in" vs "GPIO buttons", `loadControls` naming
- where: src/web/WebControlPage.cpp:18065@cinemate-port; :17936-17940; :18256
- port way: `grid.style.gridTemplateColumns` set inline; the GPIO card retitled "GPIO in" on Controls only; `loadControls`.
- Apertar way: column classes toggled on the pill grid (`three-col`, src/web/WebControlPage.cpp:9150@upstream-1.6.0, CSS :755); `fetch<X>` for loaders (:10207, 10246, 10304, 10361) (C3-I6).
- why it matters: small deviations from the page's own layout and naming vocabulary.
- rework: column classes instead of inline style; one name for the GPIO card; rename `loadControls` to `fetchControls`.
- effort S; deliberate no.

### WCP-09-F17 [slop, nit] One-entry Function dropdown for outputs
- where: src/web/WebControlPage.cpp:17821@cinemate-port; :17859-17870
- port way: `const controlsOutputFunctions = [["tally", "Tally light"]]` with comment "Tally light for now; add more"; a select with one fixed option.
- Apertar way: no precedent.
- why it matters: over-built generality; a control that cannot change anything.
- rework: drop the select and the constant; title the row "Tally light".
- effort S; deliberate no.
