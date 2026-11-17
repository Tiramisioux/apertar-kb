# Review WCP-10: WebControlPage.cpp JS tail (new-file lines 18748-20840)

Stage 2. Diff `/home/user/build/review/diffs/WCP.part10.diff` read whole (1415 lines, 7 hunks). Port refs `@cinemate-port` (`01f170c`), upstream refs `@upstream-1.6.0`. Rule ids from `raw/conv-webui.md` (C3-...). `WCP` = `src/web/WebControlPage.cpp`, `App` = `src/ApertarCoreApp.cpp`. All claims confirmed (read in code) unless labelled.

## Summary

The slice extends upstream code in place well where it touches upstream code (preset `allowedKeys`, `saveConfigFile`, `toggleRecord`, `installInteractions`, Escape chain, panel load hooks). The foreign part is the Boot Config card: about 800 lines of JS for one card (upstream feature = 20-40 lines, C3 section 0), its own store object `bootConfig` beside `state` (C3-I2), its own POST route that wraps a JSON body into the `set_boot_config` command by string insertion although the command already exists on `/api/command` (C3-S7), a checkbox gate (C3-I6/N4), a reboot wait loop on the port's `/api/buffer` route, and a live-typing re-parse of the text every 500 ms. 32 added comment lines (upstream JS has 2, C3-I9), four of them with the tutorial tag `T43` and one narrating "Port of Cinemate's settings-editor config.txt tab".

## Findings

| Id | Sev | Cat | Title | Where @cinemate-port |
| --- | --- | --- | --- | --- |
| F1 | major | mismatch | Boot Config talks to its own POST route, not `/api/command` | WCP:20004-20016; App:9170-9196 |
| F2 | major | mismatch | `bootConfig` page-side store and own timers beside `state` | WCP:19872-19884, 20503-20514, 20553-20606 |
| F3 | major | new-ground | Boot Config card over-built (Edit file, live marks, legend, own-lines hint) | WCP:19868-20606 |
| F4 | major | security | Edit file posts whole config.txt to a root-write route; guard is Origin presence only | WCP:19999 (`body.text`), App:3790-3794 |
| F5 | minor | mismatch | Display-change checkbox gate instead of `window.confirm` | WCP:20268-20290 |
| F6 | minor | bug / new-ground | Reboot wait polls `/api/buffer`, 60 s "never-down" misreports a slow shutdown | WCP:20356-20403 |
| F7 | minor | mismatch | Config Check goes through `set_controls` on `/api/command` with `base: ... || "h"`; Save goes through `POST /api/config` | WCP:18795, 18918-18927 |
| F8 | minor | duplication | Two diff renderers and two inline action rows; `bootConfigOption` re-implements `ensureSelectEntries` | WCP:18854-18887, 20225-20317, 20038-20044 |
| F9 | minor | mismatch | Remote controls loader: own untracked 5 s `setTimeout` loop | WCP:20869-20878 |
| F10 | minor | new-ground | `toggleRecord` decides "flushing" from the page-side `frameBufferBar` | WCP:19199-19204, 19237 |
| F11 | minor | slop | `T43` tags, Cinemate history, section banner; 32 comment lines | WCP:18758, 18792, 18811, 18889, 19868-19871 |
| F12 | nit | new-ground | Save Config is now two clicks (diff, then "Save these changes") | WCP:18854-18887, 20884 |
| F13 | nit | mismatch | Toast "Storage pre-roll started" lacks the period | WCP:19828 |

### F1 Boot Config uses its own POST route, not `/api/command`

- Port: `bootConfigPost` does `fetch("/api/boot-config", { method: "POST", headers, body: JSON.stringify(body) })` (WCP:20004-20016). Core: `payload.insert(brace + 1, "\"cmd\":\"set_boot_config\",")` then `parseControlCommand(payload)` (App:9178-9181). The command `set_boot_config` already exists in `handleCommand` (App:14589) and accepts `revision` as a field (App:9190-9192). Body values are JSON booleans and numbers (`body[key] = form.toggles[key]`, `dry_run: true`, `confirm_display: !!(...)`, WCP:19995, 20246, 20325).
- Upstream: "every camera action through `POST /api/command`"; dedicated routes "only for things that are not commands: file transfer, library listings, the config file" (C3-S7, App:7637-7642@upstream-1.6.0). Booleans travel as strings: `{ cmd: "set_smpte_enabled", enabled: value === "On" ? "true" : "false" }` (C3-I5, WCP:10111@upstream-1.6.0).
- Rework: `bootConfigPost` -> `controlsCall`-style `fetch("/api/command")` with `{ cmd: "set_boot_config", cam0_sensor, ..., i2c: "true"/"false", dry_run: "true", revision }`. Delete `POST /api/boot-config` and its string insertion (App:9170-9196). Keep `GET /api/boot-config` (parallel to `GET /api/config`) or switch to `get_boot_config`. `/api/boot-config/parse` may stay as a text-upload route (like `POST /api/config`). The `old_page` check moves to the `/api/command` route or is dropped (F4).

### F2 `bootConfig` store beside `state`

- Port: `const bootConfig = { payload, form, loading, saving, waiting, savedPendingReboot, review, text, previewState, editorMarks, editorTimer }` (WCP:19872-19884). Same shape as the port's `controlsState` (16633), `frameBufferBar` (16419), `settingsSearch` (10184). Separate sub-installer `installBootConfigInteractions()` (WCP:20553) called from `installInteractions` (20852).
- Upstream: one global `state` with flat fields, busy flags `<thing>InFlight`, timers `state.<thing>Timer` (C3-I2; `configFetchInFlight`, `configSaveInFlight`, `configDirty`, `toastTimer` WCP:4204-4266@upstream-1.6.0). All listeners inline in `installInteractions` (WCP:11348-11610@upstream-1.6.0).
- Rework: `state.bootConfigPayload`, `state.bootConfigForm`, `state.bootConfigFetchInFlight`, `state.bootConfigSaveInFlight`, `state.bootConfigRebootWaiting`, `state.bootConfigReview`, `state.bootConfigText`. Move the listeners of `installBootConfigInteractions` into `installInteractions` next to `restartSystemButton`. Same treatment as rev-WCP-08 asks for `frameBufferBar`.

### F3 Boot Config card over-built

- Port: View file, Edit file with its own gutter and italic managed-line marks, a legend of runs (`bootConfigManagedSummary`), an own-lines hint (`bootConfigOwnLinesHint`), re-parse of the text through `/api/boot-config/parse` 500 ms after each keystroke (`bootConfigEditorEdited`, WCP:20501-20515), Use This Text, Upload, Download, review, Save Only / Save and Reboot, reboot wait. About 800 lines.
- Upstream: a feature is 20-40 lines in 3-5 places (C3 section 0); the one text-file editor (`apertar-hardware.conf`) is a plain textarea with Reload/Save (`fetchConfigFile`/`saveConfigFile` WCP:10304-10359@upstream-1.6.0). Upstream has no config.txt editing at all.
- Commits: `8a56545` (card), `3b87d99` "Why: the card only reached the lines it has controls for; anything else in config.txt still needed ssh or a card reader", `2a4266e` (marks). Reason stated (deliberate yes), cost against Apertar's size not weighed.
- Verdict: simplify. Keep the controls (sensor per port, link, toggles, RP1, display), the dry-run review, Save, View file and Download. Drop the live marks, legend and own-lines hint (`2a4266e`, about 80 lines plus Core `state.managed`). Drop Edit file / Use This Text (`3b87d99`): it is the only client of `set_boot_config text=` (F4), and hand edits remain possible through Download, edit, Upload-then-Save if Upload is kept, or by ssh as upstream assumes.

### F4 Whole-file root write from the page

- Port: `if (bootConfig.text !== null) body.text = bootConfig.text;` (WCP:19999). Core writes the file as root through `scripts/apertar-boot-config` (sweep-knobs.md:250). Guard: `if (!revision && browser) return 409 old_page` where `browser = request.headers.count("origin") > 0` (App:3790-3794, 9193); a request without `Origin` (curl, LAN script) writes with no revision.
- Upstream: no route writes a system file outside `apertar-hardware.conf`; README: "The WebUI is not an authenticated internet-facing service." (C3-S9).
- Already reported as sweep-protocol-security.md:17 (a). This slice is the client. Rework: F3 (drop Edit file) removes the client; Core then drops `text=` from `set_boot_config`.

### F5 Checkbox gate

- Port: `gate = document.createElement("input"); gate.type = "checkbox"; ... " Change the display anyway"`; Save buttons disabled until ticked (WCP:20282-20314).
- Upstream: no checkbox anywhere (`grep -c 'type="checkbox"'` = 0, C3-I6); system-level actions ask with `window.confirm`, e.g. `if (!window.confirm("Restart the Apertar system now?"))` (WCP:11315@upstream-1.6.0, C3-N4).
- Rework: drop the checkbox; when `review.display_changed`, `saveBootConfig` asks `window.confirm("Change the display and reboot? <the DPI sentence>")`. The notes stay as `diff-note` lines.

### F6 Reboot wait

- Port: `waitForCameraAfterReboot` polls `fetch("/api/buffer")` every 2.5 s up to 240 s; if the page never saw a failure within 60 s it returns `"never-down"` and says "The camera kept answering, so it did not reboot." (WCP:20356-20376, 20396-20397).
- Failing input (probable): Save and Reboot during a take with a full RAM buffer. `restart_system` calls `invokeSystemPowerAction("reboot")` (App:14855-14859); systemd stops Core, which drains the take first; a drain longer than 60 s makes the page report "did not reboot" and stop waiting while the reboot follows. Settle on a Pi: record at 4K, fill the buffer, Save and Reboot.
- Upstream: `requestRestartSystem` sends `restart_system`, toasts "Restart requested." (WCP:11314-11324@upstream-1.6.0); reconnection is the 1 s `fetchState` poll and the "Connecting to ApertarCore..." overlay (C3-N5).
- Verdict simplify: poll `/api/state` (upstream route) instead of the port route `/api/buffer`, drop the 60 s "never-down" branch (the `restarting:true` reply already says the reboot was accepted).

### F7 Check and Save use two transports for one file

- Port: Check: `controlsCall({ cmd: "set_controls", base: state.configRevision || "h", text, dry_run: "true", by: "webui" })` (WCP:18795). Save: `fetch("/api/config", { method: "POST", headers: { ..., "X-Apertar-Revision": state.configRevision } })` (WCP:18918-18927). `"h"` is no revision: the absent-file revision is `"h0000000000000000"` (`src/hardware/HardwareConfigText.hpp:315`).
- Upstream: the file has one path, `GET/POST /api/config` (App:7168/7175@upstream-1.6.0); query parameters through `queryParameterValue` (C3-S7).
- Rework: one transport. Either Check posts to `/api/config?dry_run=1` with the same header, or Save uses `set_controls base= text=` too. Disable Check until `state.configRevision` is set; delete the `"h"` fallback.

### F8 Duplication

- `showConfigDiff` (WCP:18854-18887) and `reviewBootConfig` + `bootConfigDiffLine` + `toggleBootConfigFile` (20225-20317, 20418-20436) each build a diff box, lines with `.diff-add/.diff-del/.diff-gap`, and an action row of JS-created buttons.
- `bootConfigOption` + `select.innerHTML = ""` (WCP:20038-20044, 20070, 20096, 20174) repeats `ensureSelectEntries` (WCP:10340@cinemate-port, `ensureSelectOptions` 6191-6208@upstream-1.6.0) to add a `disabled` flag.
- Rework: one `renderDiffBox(boxId, lines, actions)`; extend `normalizeSelectEntries` with `enabled` (as `normalizeChoiceOptions` already has, C3-I6) and use `ensureSelectEntries`.

### F9 Remote controls loader

- Port: `const loadRemoteControls = () => { if (controlsState.model) return; void loadControls(true); setTimeout(loadRemoteControls, 5000); };` inside `installInteractions` (WCP:20869-20878). Timer not stored, never cleared.
- Upstream: one poll loop, `window.setInterval(() => fetchState(true), 1000)` (WCP:11609@upstream-1.6.0); timers in `state.<x>Timer`, cleared before re-arming (C3-I2); per-panel loads in `setSettingsPanel` (C3-S4).
- Rework: in `fetchState` after a good snapshot: `if (!controlsState.model && !controlsState.loading) void loadControls(true);`. Delete the loop.

### F10 `toggleRecord` flushing

- Port: `const flushing = frameBufferBar.safetyStop === true && !state.snapshot.timelapse_active;` bypasses the `media_writes_pending` guard and the `record_stop` branch (WCP:19201-19204, 19237). Commit `c5db8b2`; owner decision 2026-11-01 (inventory).
- Upstream: guard on `state.snapshot` fields only; Core decides (C3-N2, WCP:10690-10695@upstream-1.6.0).
- Verdict keep the behaviour; read `state.snapshot.buffer_safety_stop` once rev-WCP-08's rework folds `frameBufferBar` into the snapshot. Cross-ref CC-3-F12, App-1-F13.

### F11 Slop

- `// T43: line numbers beside the editor` (18758), `// T43 Check:` (18792), `// T43: the lines that differ` (18811), `// T43 history:` (18889). `// ---- Boot Config card (System pane): ... ----` banner and "Port of Cinemate's settings-editor config.txt tab." (19868-19871). 32 added `//` lines in this slice; upstream JS has 2 (C3-I9).
- Rework: delete tags, banner and history; keep one-line reasons where they state a safety rule (e.g. "A refused save leaves the text in the box").

### F12 Save Config two clicks

- Port: `saveConfigButton` -> `showConfigDiff`, saving needs "Save these changes" (WCP:20884, 18877). Upstream: `saveConfigButton` -> `saveConfigFile` (one click, backup kept).
- Verdict keep (stale-tab and diff are useful, deliberate in `8be1ab5`), but render through F8's shared helper.

### F13 Toast text

- `showToast("Storage pre-roll started", false)` (WCP:19828). Upstream toasts end with a period: "Write speed test started." (WCP:11307@upstream-1.6.0, C3-N7).

## Protocol

- `POST /api/config` now 409 `old_page` for a browser request without `X-Apertar-Revision` (App:8633-8638); requests without `Origin` keep last-writer-wins. Upstream UI (`ui-upstream`) does not call `/api/config` (grep: no hit). No break for unmodified clients. The upstream WebUI cannot meet a port Core (page is compiled in).
- `/api/media/delete` (single) has no JS caller left (App:9004); route kept, harmless for scripts.

## Abstraction verdicts

| Name | Verdict | Reason |
| --- | --- | --- |
| `bootConfig` object | rework-to-upstream-pattern | flat fields on `state` (F2) |
| `BOOT_CONFIG_TOGGLES` | keep | top-level const list, as C3-S6 |
| `BOOT_CONFIG_MANAGED` + `bootConfigManagedMap/Summary`, `bootConfigOwnLinesHint` | simplify (delete) | live marks/legend over-built (F3) |
| `bootConfigPost`, `loadBootConfig`, `reviewBootConfig`, `saveBootConfig` | rework-to-upstream-pattern | `/api/command` with flat string values (F1) |
| `waitForCameraAfterReboot`, `bootConfigSleep` | simplify | poll `/api/state`, drop never-down (F6) |
| `updateEditorGutter(editorId, gutterId, marks)` | simplify | keep for the Config editor; drop `marks` with F3 |
| `configDiffLines` | keep | small, no upstream equivalent, used once |
| `renderBootConfigPort`, `bootConfigFormFrom`, `bootConfigEffectiveLink`, `bootConfigDirty` | keep | form/state mapping is needed; move storage to `state` |
| `megahertzText`, `drmSummary` | keep | formatter helpers like `formatFps` |
| document-level click/keydown for `[data-ladder-link]` | keep | upstream also listens on `document` (pointerdown/keydown, WCP:11515-11516@upstream-1.6.0); needed for links inside the toast |
| `loadRemoteControls` timer | rework-to-upstream-pattern | piggyback on `fetchState` (F9) |

## Conforms

- `allowedKeys` in preset import: 17 keys appended to the same list, same loop (WCP:19080-19121).
- `requestStoragePreroll` is the `requestMediaSpeedTest` shape: try `sendCommand`, toast, `showToast(error.message, true)` (WCP:19823-19831; C3-I4, I7 `request<Action>`).
- Frames-per-folder Apply copies the custom-interval Apply right above it: local range check, toast, `sendCommand` (WCP:20673-20683).
- Boot Config load is hooked into `setSettingsPanel` / `setSettingsOpen` like presets and config (WCP:10112, 10165; C3-S4).
- Boot Config On/Off uses `buildOptionButtons` with `{ value, enabled }` (WCP:20160-20162; C3-I6).
- Reload with unsaved edits asks `window.confirm` (WCP:20197, 20522; C3-N4).
- Reboot uses the existing `restart_system` command (WCP:20380).
- `saveConfigFile` extended in place; body and content type unchanged (WCP:18905-18950).
- Escape chain and nav click extended in the existing `document` keydown and nav loop (WCP:20913-20928).
- Clip Browser wiring keeps upstream parity: Refresh, filters Clips/Stills/Timelapse/Audio, newest/oldest, Select All over the filtered list (`state.pb.items` filtered at WCP:11958), Download, Remove; single remove in the viewer (WCP:12906).
