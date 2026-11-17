# Inventory WCP-09: Controls / Hardware / Remote-controls JS in WebControlPage.cpp

Scope: `/home/user/build/review/diffs/WCP.part09.diff` (2115 lines, one hunk `@@ -10311,26 +16622,2110 @@`),
new-file lines 16622-18740 of `src/web/WebControlPage.cpp` @cinemate-port `01f170c`. Read completely.
Upstream anchor: `/home/user/wt/core-upstream` `src/web/WebControlPage.cpp` @upstream-1.6.0 (`renderHardwareConfig` at :10288).
Stage 1: inventory only, no judgement.

## 1. Shape of the change

- 2084 lines added, 1 hunk, 0 lines deleted. Inserted between `updateConfigEditorControls()` (upstream :10265) and `renderHardwareConfig()` (upstream :10288), plus 5 added lines inside `renderHardwareConfig` (port :18711).
- All JavaScript inside the one C++ raw string. No C++ code in this slice.
- The block is a new client-side application: ~95 functions, ~15 module-level state consts, DOM built by `createElement` (no `innerHTML`). Upstream's WebUI also builds with `createElement` (48 uses, 10 `innerHTML` @upstream-1.6.0), so the building style is the same; the size and the amount of client-side state are new.
- Port line anchors (all @cinemate-port): state `:16633`, `controlsCall :16698`, `buildControlsActionEditor :16799`, `buildControlsRow :17047`, pin ownership `:17162-17430`, `buildControlsNewRow :17440`, tally `:17619-17660`, `buildControlsPeripheral :17650`, `buildControlsOutputRow :17822`, `renderControls :17921`, `buildRemoteButton :17995`, `renderRemoteControls :18047`, `renderHardware :18156`, `saveHardware :18219`, `loadControls :18255`, `controlsPayload :18325`, `renderControlsReview :18439`, `controlsRecheckSoon :18516`, `renderControlsPending :18532`, `loadControlsHistory :18555`, `undoLastControlsSave :18577`, `setControlsListening :18609`, `saveControls :18651`, `showConfigIssues :18686`, `renderHardwareConfig :18711`.

## 2. Authorship by commit (git blame, lines 16622-18740 @cinemate-port)

| Commit | Lines | Subject | fork-log status (`fork-log.md`) |
| --- | --- | --- | --- |
| `d44b177` | 554 | drop-frames squash (19 commits): includes WebUI "white GPIO/hardware dropdowns, a Tally LED card on Controls", "Controls GPIO in/out cards" (fork-log :138) | fork-only; squash holds many unrelated features |
| `8be1ab5` | 444 | T40-T43: Listen, review, Undo, chips, Turn adjusts, Scan, Test, text editor with diff | fork-only (:130); no test recorded |
| `fa3a798` | 225 | one card per device, gesture dropdowns, add buttons for buttons and switches | fork-only (:126) |
| `d282de9` | 211 | Controls card, a dropdown of actions per button/knob/pin (part 2) | fork-only (:118) |
| `1319967` | 192 | Remote controls card, Try buttons, `test_input` | fork-only; "on the Pi only (another session, 2026-11-04 01:22)" (:148) |
| `f5fe41b` | 157 | Controls for detected hardware, + for clicks, Hardware card on Config | fork-only (:123) |
| `b74b4aa` | 134 | push actions on knobs and PCF pins, + Add GPIO rotary encoder | fork-only (:128) |
| `166cc4d` | 62 | GPIO buttons as a peripheral with settings and detection (part 3) | fork-only (:120) |
| `9b5ea14` | 59 | GPIO button remote only (`remote<N>`), DPI-held pins greyed | fork-only; Pi only; "built clean 01:26" (:150) |
| `^35dbe67` | 35 | upstream context lines | upstream |
| `effb804` | 28 | T38 part 2: Config page revision, issues with line numbers | fork-only (:111) |
| `b64e6f6` | 17 | GPIO out row gets a Remove | fork-only; Pi only (:149) |
| `8a56545` | 1 | Boot Config card (one line) | PR #1 merge area |

Tests recorded: fork-log has no unit or desk test for any of these WebUI commits. Only `9b5ea14` says "built clean" and the Pi evening tests of drop-frames. Everything else: not recorded. Reading the JS only; no browser run here.

## 3. Features (operator-visible)

| # | Feature | Where (port lines) | Commits | Operator gets |
| --- | --- | --- | --- | --- |
| F1 | Controls page: one card per detected device (GPIO in, NeoRotary 4, PCF8574) with groups of rows | `renderControls :17921`, `buildControlsGroup :17788`, `controlsGroups :16652`, `controlsSourcesByPeripheral :16660` | d282de9, fa3a798, f5fe41b | Sees only hardware that is there; Config lists the rest. GPIO card titled "GPIO in" on the page, Core label stays "GPIO buttons" (:17939) |
| F2 | Action dropdown per line | `controlsActionGroups :16747`, `buildControlsSelect :16763` | d282de9 | Picks an action from `list_actions` catalog, grouped; turns get only stepping actions; unknown value shown "(as written in the file)" |
| F3 | Gesture dropdown per button line, + Add action, per-line Remove | `appendButtonLines :16986`, `controlsPushGestures :16669`, `controlsAddOrder :16667` | fa3a798, b74b4aa | Press / Single / Double / Triple / Hold per line, used ones greyed, next free gesture added |
| F4 | Several actions on one line as chips (drag to reorder, x, "+ action") | `buildControlsActionEditor :16799`, `controlsChipLines :16798` | 8be1ab5 (T41) | A line holds `iso200,fps24` run in order; chip box acts as a select (`.value`, `.disabled`, `change`) |
| F5 | "Turn adjusts": a knob's two turns as one pair | `controlsTurnPairs :16875`, in `buildControlsRow :17047`, `controlsSeparateTurns :16881` | 8be1ab5 (T41) | One dropdown "ISO (clockwise up)" etc.; "Separate actions for each direction..." escape |
| F6 | Move a control to another pin; pin dropdowns with owner text; claim a pin held by another control (confirm, then the other is removed) | `controlsRowPinInfo :17163`, `controlsPinOwners :17252`, `controlsPinChoices :17284`, `controlsClaimPin :17312`, `fillControlsPinHead :17358`, `setControlsRowPins :17411` | f5fe41b, b74b4aa, d44b177, 9b5ea14 | Picks GPIO from dropdown; pins held outside Core or by the DPI display disabled; another control's pin: confirm, replace |
| F7 | Add rows: GPIO button, two-way switch, three-way switch, rotary encoder | `buildControlsAddBar :17564`, `addControlsRow :17543`, `buildControlsNewRow :17440`, `switchLineSpecs :16673` | fa3a798, b74b4aa | "+ Add GPIO ..." buttons; first free pins preselected; "No free GPIO pin left." toast |
| F8 | Remote-only GPIO button (`remote<N>`, no pin) | `controlsRemoteValue :17292`, `controlsRemoteBase :17294` | 9b5ea14 | A button with no pin, run from the Remote controls card |
| F9 | Remove / Undo per row or line (marked, applied on Save) | `buildControlsRemove :16954`, `controlsState.removed`, `line.removed` | f5fe41b, fa3a798 | Removal is unsaved until Save Controls; Undo restores; Undo blocked if the pin was taken meanwhile |
| F10 | Try buttons per line and per turn (arrows) | `sendTestInput :16916`, `buildControlsTry :16942`, `controlsTryWhy :16931` | 1319967 | Runs the SAVED action as if the control moved; disabled with a reason when unsaved / off / nothing assigned |
| F11 | Remote controls card on the main page | `renderRemoteControls :18047`, `buildRemoteButton :17995` | 1319967 | Pills for buttons, switch positions, knob blocks with left/right arrows; arrows repeat while held (450 ms delay, 140 ms interval, one step per answer) |
| F12 | GPIO out card with the Tally LED row: pin (None/GPIO n/PCF8574 pin n), function, Active high/low, Test, Remove | `buildControlsOutputRow :17822`, tally helpers `:17619-17660`, `setTallyField :17809`, `controlsPcfPinsInUse :17595` | d44b177, b64e6f6 | Tally LED set up on Controls; no On field: on = a pin is set; saves with Save Controls |
| F13 | Hardware card on Config: I2C buses, every supported device with settings, Scan, Test output, DPI display note | `renderHardware :18156`, `buildControlsPeripheral :17650`, `saveHardware :18219` | f5fe41b, 166cc4d, 8be1ab5 (T40, T42), 9b5ea14 | Edits `[section] key` settings per device with its own Save Hardware; Scan lists addresses on a bus; Test blinks one output |
| F14 | Review box "Not saved yet:" in plain words | `renderControlsReview :18439`, `controlsDescribe :18398`, `controlsActionWords :18432` | 8be1ab5 (T42) | Lists each unsaved change ("GPIO 6 -> GPIO 5: Eject media") |
| F15 | Save Controls as one `set_controls` request | `controlsPayload :18325`, `saveControls :18651` | d282de9, fa3a798, 8be1ab5 | Revision-checked save; stale/conflict keeps the page edits; switches a group on when a new row is saved into a switched-off group |
| F16 | Undo last save and history list | `loadControlsHistory :18555`, `undoLastControlsSave :18577` | 8be1ab5 (T42) | Undo restores the version before the last non-"adopted" save; also fills Config's "Load an earlier version..." select (`configHistorySelect`) |
| F17 | Listen: press a control, its row lights and scrolls into view | `setControlsListening :18609`, `controlsRowForKey :18603` | 8be1ab5 (T42) | Polls every 300 ms, stops after 120 s or when the page is hidden; "Heard: ..." note |
| F18 | Apply state and pending notes | `renderControlsPending :18532`, `controlsRecheckSoon :18516`, `controlsAppliedText :18509` | 8be1ab5 (T39) | "Saved. Core applies it when the take ends." / "now"; lists services outside Core that still read the old file with a shell command to run |
| F19 | Load / dirty / buttons / message plumbing | `loadControls :18255`, `controlsDirty :16693`, `updateControlsButtons :16707`, `showControlsMessage :16718`, `hardwareDirty :18114`, `updateHardwareButtons :18118`, `showHardwareMessage :18129` | d282de9, f5fe41b | Reload with discard confirm; "The file has N errors. Config shows where."; "The file was replaced ..." notice |
| F20 | Config text editor: issues box with line numbers, revision, loaded-text baseline | `showConfigIssues :18686`; +5 lines in `renderHardwareConfig :18711` | effb804, 8be1ab5 | Core's issues with line numbers under the editor. Gutter, Check, diff, history UI live in other slices (`updateConfigGutter :18759`, `hideConfigDiff :18845`, dry_run `set_controls` at :18795) |

## 4. Interfaces

### 4.1 Socket commands called from this slice (all via POST `/api/command`)

| Command | Fields sent | Used by | Core handler @cinemate-port |
| --- | --- | --- | --- |
| `get_controls` | none | `loadControls`, `controlsRecheckSoon` | `ApertarCoreApp.cpp:12420` |
| `list_actions` | none (once, cached in `controlsState.catalog`) | `loadControls` | `:12534` |
| `set_controls` | `base` (revision), `by` = `webui` / `webui_undo`, `set.<section>.<key>`, `unset.<section>.<key>`, or `text` (undo) | `saveControls`, `saveHardware`, `undoLastControlsSave` (dry_run use is in another slice :18795) | `:12763` |
| `controls_history` | none / `name` | `loadControlsHistory`, `undoLastControlsSave` | `:12458` |
| `controls_last_input` | none; reads `seq`, `section`, `key` | `setControlsListening` | `:12476` |
| `test_input` | `section`, `key` | `sendTestInput` | `:12565` |
| `test_output` | `which` (peripheral id) | Test buttons in `buildControlsPeripheral`, `buildControlsOutputRow` | `:12745` |
| `scan_i2c` | `bus` | Scan button in `renderHardware` | `:12486` |

All 8 are new; none exists @upstream-1.6.0 (handlers are outside this slice; see `inv-App-*`, `inv-HW-controls-model.md`). Reply fields the JS depends on: `controls.{revision, model{rows[], sections[], gpio_pins{free[],used[]}}, peripherals[], i2c_buses[], dpi_lines[], apply{state,detail,pending[]}, errors, issues[], replaced{replaced,reason,saved_at}}`, `ok`, `error`, `code` (`stale`/`conflict`), `new_errors`, `issues`, `apply` (`after_take`), `found[]` (`address, guess, by`), `history[]` (`name, by, saved_at`), `text`.

Note on shape: replies nest an object (`controls`, `model`, arrays of objects) and requests send dotted keys `set.<section>.<key>`. The Apertar flat-scalar-JSON hint is not followed in the replies; the requests are flat.

### 4.2 HTTP routes

| Route | Use in slice | New? |
| --- | --- | --- |
| `POST /api/command` | `controlsCall` (:16698), a bare `fetch`, not `sendCommand` | existing route |
| `GET/POST /api/config` | not in this slice (`fetchConfigFile :18732` onward) | existing @upstream-1.6.0 |

No new HTTP route in this slice.

### 4.3 State fields (client side)

| Object | Fields added |
| --- | --- |
| `controlsState` (new, :16633) | `loading, saving, revision, model, peripherals, catalog, edits(Map), buttons(Map), removed(Set), added[], settingEdits(Map), buses[], scans{}, dpiLines[], apply, history[], listening` |
| Module-level | `controlsChipLines(Set), controlsSeparateTurns(Set), controlsReplaced(Map), controlsListenTimer, controlsListenSeq, controlsGroups, controlsSourcesByPeripheral, controlsNewTitles, controlsAddOrder, controlsStateNames, controlsDetectedStates, controlsTallySection="recording_indicator", controlsOutputFunctions, controlsKindNames, controlsRemoteValue, controlsPinSources, controlsSaveFirst` |
| Existing `state` object (upstream) | added reads/writes: `state.configLoadedText`, `state.configRevision` (set in `renderHardwareConfig :18711`), and reads of `state.configDirty` after saves |

Controls state lives in its own object, not in `state`. Upstream keeps page state in the single `state` object (`state.configDirty`, `state.configFetchInFlight`, `updateConfigEditorControls` upstream :10265).

### 4.4 Events and timers

| Kind | Name | Value |
| --- | --- | --- |
| Core event | none consumed | no websocket / SSE event added; all data by polling |
| Timer | Listen poll | `setInterval` 300 ms, auto-off 120 s or hidden panel |
| Timer | `controlsRecheckSoon` | one `setTimeout` 2500 ms after a save |
| Timer | remote knob repeat | 450 ms delay then 140 ms interval, flash 250 ms |
| Browser | pointer capture, drag and drop (chips), `window.confirm` (pin claim, reload discard, undo) | upstream uses `window.confirm` for destructive actions too (:10307, :10385, :11266) |

### 4.5 Config keys written (file `apertar-hardware.conf`, via `set_controls`; Core owns parsing)

| Section | Keys the JS writes or unsets |
| --- | --- |
| `[gpio_buttons]` | `d<pin>`, `d<pin>_single`, `_double`, `_triple`, `_hold`; `remote<N>` + same suffixes; `enabled` |
| `[gpio_switches]` | `switch<N>_pins` (`6,13`), `switch<N>_off`, `_on` (2-way), `_position0`, `_position1`, `_position2` (3-way); `enabled` |
| `[gpio_encoders]` | `encoder<N>_a`, `_b`, `_press_gpio`, `_cw`, `_ccw`, `_press`, `_press_single` ...; `enabled` |
| `[neorotary4]`, `[pcf8574]` | line keys as the model returns them (`*_cw`, `*_ccw`, push keys); device settings by `setting.key` from `peripherals[].settings` |
| `[recording_indicator]` | `enabled, target (gpio\|pcf8574), line, pcf_pin, active_high` |
| any peripheral section | settings from `peripherals[i].settings` (types `bool`, `choice`, `number`, `text`, `pcf_pin`) written as `set.<section>.<key>` |

Other keys appear in the review text only (`controlsDescribe`). Action ids come from `list_actions` (e.g. `iso_up`, `iso_down`, `iso200`, `fps24`), not hard-coded, except the `_up`/`_down` naming rule used to pair turns (:16876).

### 4.6 Env vars, files on disk

None in this slice. File touched through Core: `apertar-hardware.conf` and its history store (`controls_history` returns `name`, `saved_at`, `by`; "adopted" = the version Core first found). Fallback display path string `/home/pi/apertar-hardware.conf` already in upstream (:10299).

### 4.7 DOM ids used (defined in other slices, HTML at port :4578 and :6144-6228)

`controlsRows, controlsReview, controlsMessage, controlsPending, controlsListenNote, controlsStatePill, reloadControlsButton, listenControlsButton, undoControlsButton, saveControlsButton, hardwareStatePill, hardwareMessage, hardwarePending, hardwareDevices, reloadHardwareButton, saveHardwareButton, remoteControlsRows (main page, :4578), configHistorySelect, settingsConfigIssues`. Wired at port :20875-20892. CSS classes used: `controls-*`, `action-chip(s)`, `online-pill`, `pill-button`, `select-block`, `pill-grid` (some reused from Camera settings).

## 5. Original code regions modified

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| `renderHardwareConfig(payload)` | upstream :10288, port :18711 | +5 lines: `state.configLoadedText = text;` `hideConfigDiff();` `updateConfigGutter();` `state.configRevision = String(payload.revision \|\| "");` `showConfigIssues("", []);` | extended-in-place |
| `updateConfigEditorControls()` | upstream :10265, port ends ~:16621 | unchanged in this slice (context only) | none |

Nothing else of upstream is touched in this slice. The new block is inserted whole before `renderHardwareConfig`. `renderHardwareConfig` now depends on `hideConfigDiff` and `updateConfigGutter`, which sit in a later slice (port :18759, :18845).

## 6. New abstractions

| Name | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- |
| `controlsCall(payload)` (:16698) | bare POST to `/api/command`, returns JSON, no snapshot patch, no error throw | `sendCommand` (upstream :9109): snapshot patch, in-flight counters, refresh scheduling, throws on `!ok` | everything in this slice |
| `controlsState` object + 15 module consts | client-side model of the hardware file (edits, removals, adds, history, scans) | single `state` object | whole slice |
| Edit model: `edits` / `buttons` / `removed` / `added` / `settingEdits` -> `controlsPayload()` | stages unsaved edits then builds one `set.`/`unset.` request | upstream presets/config page post a whole value or whole text (`saveConfigFile` posts plain text to `/api/config`, upstream :10338) | Save Controls / Save Hardware |
| Pin ownership model: `controlsPinOwners`, `controlsRowPinInfo`, `controlsPinChoices`, `controlsClaimPin` | who holds each GPIO pin; claims and replaces | none | pin dropdowns, new rows, tally |
| `buildControlsActionEditor` chip box (duck-typed select with `.value`/`.disabled`/`change`) | several actions per line | none | action lines |
| `buildRemoteButton` (pointer capture, repeat) | hold-to-repeat pill | upstream pill buttons (`buildOptionButtons` upstream :9145) fire one command per click | Remote controls card |
| Tally helpers (`tallyRaw/Shown/FileEnabled/syncTallyEnabled/setTallyField`) | the tally has no On field, derived from the pin | none | GPIO out row, Hardware card |
| Listen poller | polls `controls_last_input` | upstream has `window.setInterval(() => fetchState(true), 1000)` (:11609), a single global poller | Controls page |
| Review renderer `renderControlsReview` + `controlsDescribe` | plain-words diff of unsaved edits | none | Controls page |
| Per-feature message boxes `showControlsMessage`, `showHardwareMessage`, `showConfigIssues` | three near-identical copies (head + list of up to 20 issues with "Line N:") | upstream `showToast` (:7804) for messages | Controls, Hardware, Config |

No new C++ class, header, worker thread or helper script in this slice. The Controls model and Core side are in other units (`inv-HW-controls-model.md`, `inv-HW-input-classes.md`, `inv-HW-config-text-store.md`).

## 7. Upstream removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| Nothing deleted in this slice (0 deletions) | - | - |
| Hardware config text is no longer the only way to edit button/knob/pin mapping | Config page | The raw text editor stays; its load/save path gains revision, issues, diff (other slices) |
| Peripherals not detected are hidden on Controls | `renderControls :17921` (`detected` gate) | Undetected devices only visible on Config's Hardware card (`controlsDetectedStates = running, found, restart`); a switched-off group is hidden on Controls unless rows were added (:17795) |
| Core's label "GPIO buttons" shown as "GPIO in" | :17939 | display rename |
| Turn lines of a knob collapsed into one "Turn adjusts" pair line | :17118 area | per-direction lines only via "Separate actions..." |

## 8. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| A DPI display holds GPIO 0 to 27 | `controlsPinsTaken :17193`, `controlsPinOwners :17252`, text at `renderHardware :18156` ("holds GPIO 0 to 27, so buttons and I2C bus 1 cannot use them") | 40-pin header GPIO 0-27; any Pi with that header. `dpi_lines` comes from Core (config.txt scan) |
| I2C bus 1 named in text | DPI note | bus number text only; buses listed come from Core (`i2c_buses`) |
| PCF8574 has 8 pins | `pcf_pin` select, `[0..7]` in `buildControlsPeripheral`, `buildControlsOutputRow` | chip fact, not Pi |
| Pin list from Core (`gpio_pins.free/used`) | `controlsPinChoices :17284` | board-specific data is in Core, not hard-coded here |
| No gpiochip numbers, no RP1, no PCIe, no RAM, no fan, no core-count in this slice | - | confirmed by reading the whole diff |
| Hint text refers to "System, Boot Config (Display)" and `config.txt` | `renderHardware` | Boot Config card exists in the port only (`8a56545`, PR #1) |
| `/home/pi/apertar-hardware.conf` | `renderHardwareConfig :18711` | upstream line, unchanged |
| Pending services text: "To do it now: <command>" | `renderControlsPending` | the command string comes from Core (`apply.pending[].command`); content not in this slice |

## 9. Open points for stage 2

- Fork-log records no test of any WebUI Controls commit; only a Pi build. Unconfirmed in a browser. Command to settle: load the page from a Core built with `-DAPERTARCORE_ENABLE_LIBCAMERA=OFF` and drive it.
- `d44b177` is one squashed commit holding 554 lines of this slice among unrelated features; blame cannot separate Tally LED / GPIO in-out cards from the buffer bar work.
- `controlsCall` skips `sendCommand` (snapshot patch, `commandInFlightCount`, deferred refresh). Effect on the 1 s state poll while saving: unconfirmed.
- The `set.<section>.<key>` / `unset.` dotted-key request and nested JSON reply differ from the flat-scalar-reply hint in BRIEF; check `conv-core-command-plane.md`.
- `renderHardwareConfig` calls two functions defined in a later slice; confirm order is safe (function declarations are hoisted in one script; confirmed by syntax: both are `function` declarations at :18759 and :18845).
- Three copies of the same issues-box builder (`showControlsMessage`, `showHardwareMessage`, `showConfigIssues`).
- Slice contains 1-line `8a56545` (Boot Config, System pane) only through the DPI note's cross-reference; not a feature of this slice.
