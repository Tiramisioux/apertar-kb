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
