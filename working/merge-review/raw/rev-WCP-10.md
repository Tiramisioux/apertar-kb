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

## Skeptic

Stage 3. Every finding re-read on both sides (`@cinemate-port` `01f170c`, `@upstream-1.6.0`), commits checked with `git show -s`, `fork-log.md`, `architecture/config.md` §7.1.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Route and string insertion confirmed (App:9170-9196). JS sets `result.httpStatus` (WCP:20011) but nothing reads it; it branches on `result.code` (WCP:20329), so `/api/command` carries the same information. Upstream precedent is closer than stated: upstream writes config.txt's fan block through `set_fan_mode` on `/api/command` (WCP:11093@upstream-1.6.0, App:10568@upstream-1.6.0). Deliberate changed no -> unknown: `2955ef8` says the POST copies `/api/config` ("409 when stale, as /api/config"), no reason against `/api/command`. Rework must keep the revision guard: `set_boot_config` on `/api/command` passes `browser=false` (App:14589), see F4. |
| F2 | stands | `bootConfig` object (WCP:19872-19884) and `installBootConfigInteractions` (20553, called 20852) confirmed. Upstream: one `state` (4204) and one `installInteractions` (11348) for listeners; `installPreviewStream` (8566) is the only other installer and holds no listeners of a card. |
| F3 | corrected | Size, 500 ms re-parse (WCP:20500-20515) and commits confirmed. "No precedent for config.txt editing" is wrong: upstream edits config.txt through one select (fan mode, `set_fan_mode`, App:3042-3178@upstream-1.6.0 per config.md, WCP:11093@upstream-1.6.0). That precedent is a fixed managed block from one control, which supports the simplify verdict. |
| F4 | corrected | Guard is weaker than stated: on `/api/command` `set_boot_config` calls `bootConfigSet(command, command.string("revision"), false)` (App:14589), so any client there writes without revision whether or not it sends Origin; on `/api/boot-config` only an Origin-less request skips it (App:3792). "Upstream writes no system file except apertar-hardware.conf" is wrong: upstream writes the config.txt fan block, sets date/time and formats media from the WebUI. What upstream never does is write caller-supplied text into a root file. Dropping `text=` reduces the risk but does not remove it (a wrong `dtoverlay` from the controls can also stop boot); the revision guard must hold on every path. |
| F5 | stands | Checkbox and `syncGate` confirmed (WCP:20283-20311). Upstream: 0 `checkbox`; `window.confirm` at WCP:11325@upstream-1.6.0 (not 11315). |
| F6 | stands | Loop and 60 s branch confirmed (WCP:20355-20374, 20396). Port shutdown stops `camera_` before `webServer_` (App:8185-8190), so the page keeps getting answers while the camera stops; a stop longer than 60 s gives the false message. Drain length on a Pi stays probable. `/api/buffer` is a port route (fork-log `d44b177`). Upstream `requestRestartSystem` WCP:11324-11334@upstream-1.6.0. |
| F7 | corrected | Both paths end in `HardwareConfigStore::replace` (App:12763 `set_controls`, App:8644 `/api/config`), so it is one validation path with two transports, not two validation paths. The `"h"` fallback is a real defect: with `dry_run` the store still compares `base` and answers `stale` (HardwareConfigStore.cpp:282-295), so Check before the file has loaded always fails. Severity stays minor. |
| F8 | stands | Diff boxes at WCP:18854-18887, 20225-20317, 20418-20436 confirmed. Upstream line refs corrected: `ensureSelectOptions` 6191, `normalizeSelectEntries` 6210, `ensureSelectEntries` 6221, `normalizeChoiceOptions` 6317 @upstream-1.6.0. |
| F9 | stands | Loop confirmed (WCP:20870-20877). Closer upstream precedent for a retry: `state.previewRetryTimer = window.setTimeout(loadPreviewStream, 1500)` (WCP:8578@upstream-1.6.0). Either rework is fine. |
| F10 | corrected | Code confirmed (WCP:19201-19204, 19240). Downgraded minor -> nit: behaviour is kept by owner decision and the only change is the input, which rev-WCP-08 already reworks; this is a dependency note. |
| F11 | stands | Four `T43` lines (18758, 18792, 18811, 18889) and the banner/history (19868-19871) confirmed. Upstream JS comment lines: 2 (8474-8475). |
| F12 | corrected | Confirmed. Upstream line: `saveConfigButton` -> `saveConfigFile` at WCP:11556@upstream-1.6.0 (saveConfigFile 10330). |
| F13 | stands | WCP:19828 confirmed; upstream "Write speed test started." WCP:11307@upstream-1.6.0. |

No finding dropped. No new finding.

## Final findings

### WCP-10-F1 [mismatch, major] Boot Config posts to its own route instead of /api/command
- where: src/web/WebControlPage.cpp:20004-20016@cinemate-port ; src/ApertarCoreApp.cpp:9170-9196@cinemate-port ; src/ApertarCoreApp.cpp:14589@cinemate-port
- port way: `bootConfigPost` does `fetch("/api/boot-config", {method:"POST", body: JSON.stringify(body)})` with JSON booleans/numbers. Core inserts `"cmd":"set_boot_config"` into the body string and calls `parseControlCommand`. `set_boot_config` already exists in `handleCommand` (App:14589) and takes `revision` as a field. `result.httpStatus` is set (WCP:20011) and never read; the card branches on `result.code` (WCP:20329).
- Apertar way: every camera action goes through `POST /api/command` -> `handleCommand` (App:7637-7642@upstream-1.6.0); dedicated routes only for file transfer, listings and the config file. The upstream config.txt writer (fan mode) is a command: `sendCommand({ cmd: "set_fan_mode", value })` (WCP:11093@upstream-1.6.0, App:10568@upstream-1.6.0). Booleans travel as "true"/"false" (WCP:10111@upstream-1.6.0, C3-S7, C3-I5).
- why it matters: a second command entry point that builds JSON by string insertion, for a command the regular path already accepts.
- rework: `bootConfigPost` becomes a `sendCommand`/`controlsCall`-style POST to `/api/command`: `{cmd:"set_boot_config", camN_sensor, camN_link_frequency, i2c:"true"/"false", ..., dry_run:"true", confirm_display:"true"/"false", revision}`. Delete the POST `/api/boot-config` branch (App:9170-9196). In Core, make `set_boot_config` require `revision` for every non-dry-run write (today App:14589 passes `browser=false`, which skips it), so the `old_page` guard is not lost. Keep GET `/api/boot-config` (parallels GET `/api/config`) and `/api/boot-config/parse` (a text upload).
- effort: M
- deliberate: unknown. `2955ef8` models the POST on `/api/config` ("409 when stale, as /api/config"); no reason given for not using `/api/command`. Code comment: "the command parser wants a name, so it gets one".

### WCP-10-F2 [mismatch, major] bootConfig page-side store and own installer beside state
- where: src/web/WebControlPage.cpp:19872-19884@cinemate-port ; src/web/WebControlPage.cpp:20553-20606@cinemate-port ; src/web/WebControlPage.cpp:20852@cinemate-port
- port way: `const bootConfig = { payload, form, loading, saving, waiting, savedPendingReboot, review, text, previewState, editorMarks, editorTimer }`, wired by a separate `installBootConfigInteractions()`. Same shape as the port's `controlsState` (16633), `frameBufferBar` (16419), `settingsSearch` (10184).
- Apertar way: one global `state` with flat fields, `<thing>InFlight` busy flags and `state.<thing>Timer` timers (WCP:4204-4266@upstream-1.6.0: `configFetchInFlight`, `configSaveInFlight`, `configDirty`, `toastTimer`). All listeners inline in `installInteractions` (WCP:11348-11610@upstream-1.6.0). C3-I2.
- why it matters: a fourth parallel store makes the page read as several mini-apps rather than one state-driven page.
- rework: move the fields to `state.bootConfigPayload`, `bootConfigForm`, `bootConfigFetchInFlight`, `bootConfigSaveInFlight`, `bootConfigRebootWaiting`, `bootConfigReview`, `bootConfigText`, `bootConfigEditorTimer` (the last two go away with F3). Inline the listeners of `installBootConfigInteractions` into `installInteractions` next to `restartSystemButton`.
- effort: M
- deliberate: no

### WCP-10-F3 [new-ground, major] Boot Config card over-built: Edit file, live managed-line marks, legend, own-lines hint
- where: src/web/WebControlPage.cpp:19868-20606@cinemate-port ; src/web/WebControlPage.cpp:20490-20515@cinemate-port
- port way: about 800 lines: controls, dry-run review, Save Only / Save and Reboot, View, Download, Upload, Edit file with its own gutter, italic managed marks re-read by POST `/api/boot-config/parse` 500 ms after each keystroke (`bootConfigEditorEdited`), a legend of runs, an own-lines hint, Use This Text, and a reboot wait.
- Apertar way: upstream touches config.txt only through one control, the fan-mode select, which rewrites one managed block (`set_fan_mode`, WCP:11093@upstream-1.6.0; writer App:3042-3178@upstream-1.6.0 per architecture/config.md). A typical upstream feature is 20-40 lines in 3-5 places (C3 section 0). The one text editor upstream has is a plain textarea with Reload/Save (WCP:10304-10359@upstream-1.6.0).
- why it matters: the size and the live re-parse are far from the code base's scale. The text path is the only client of the whole-file root write (F4).
- rework: simplify. Keep the controls (sensor per port, link frequency, toggles, RP1, display), the dry-run review, Save, View file and Download. Delete `BOOT_CONFIG_MANAGED`, `bootConfigManagedMap/Summary`, `bootConfigOwnLinesHint`, `bootConfigEditorEdited`, `showBootConfigEditorMarks` (commit `2a4266e`) plus Core `state.managed`. Delete Edit file / Use This Text (`3b87d99`) and Core's `text=` field.
- effort: M
- deliberate: yes. `3b87d99`: "the card only reached the lines it has controls for; anything else in config.txt still needed ssh or a card reader". `2a4266e` states a reason for the marks. Neither weighs the size against Apertar.

### WCP-10-F4 [security, major] Edit file sends the whole config.txt to a root write; set_boot_config has no revision guard on /api/command
- where: src/web/WebControlPage.cpp:19999@cinemate-port ; src/ApertarCoreApp.cpp:3790-3794@cinemate-port ; src/ApertarCoreApp.cpp:14589@cinemate-port ; src/ApertarCoreApp.cpp:9193@cinemate-port
- port way: `body.text = bootConfig.text`. Core writes `/boot/firmware/config.txt` as root via `scripts/apertar-boot-config`. A missing revision is refused only when `browser` is true; `/api/boot-config` sets it from `Origin` presence (App:9193), and `/api/command` always passes `false` (App:14589). So curl, a LAN script or a POST to `/api/command` writes any text with no guard.
- Apertar way: upstream writes root-owned system state from the WebUI only through fixed actions (config.txt fan block from a select, date/time, format media); it never writes caller-supplied text into a system file. README:130@upstream-1.6.0: the WebUI is not an authenticated internet-facing service.
- why it matters: anyone on the LAN can make the Pi unbootable with one request. Already reported in sweep-protocol-security.md (new root paths, item a); this slice is the client.
- rework: drop Edit file (F3), then remove `text=` from `set_boot_config` so only the card's fields can be written. Require `revision` for every non-dry-run `set_boot_config`, on every path (F1). The controls alone can still write a non-booting overlay, so the backup (`config.txt.apertar.bak`) stays.
- effort: S
- deliberate: unknown (the text write is deliberate, `3b87d99`; the missing guard on `/api/command` is not discussed)

### WCP-10-F5 [mismatch, minor] Display-change checkbox gate instead of window.confirm
- where: src/web/WebControlPage.cpp:20282-20314@cinemate-port
- port way: `gate = document.createElement("input"); gate.type = "checkbox";` " Change the display anyway". Both Save buttons stay disabled until it is ticked (`syncGate`).
- Apertar way: no checkbox anywhere (0 hits, C3-I6). System-level actions ask with `window.confirm`: `if (!window.confirm("Restart the Apertar system now?"))` (WCP:11325@upstream-1.6.0, C3-N4).
- why it matters: a new widget and a new confirmation idiom for one case.
- rework: delete the checkbox and `syncGate`. In `saveBootConfig`, when `review.display_changed`, call `window.confirm("Change the display and reboot? <DPI consequence sentence>")`. Keep the diff-note lines.
- effort: S
- deliberate: yes. `8a56545`: "a display change needs a tick that names what it costs".

### WCP-10-F6 [bug, minor] Reboot wait polls /api/buffer; the 60 s never-down rule misreports a slow shutdown
- where: src/web/WebControlPage.cpp:20355-20403@cinemate-port
- port way: every 2.5 s for up to 240 s it fetches `/api/buffer` (a port route). If no failure is seen within 60 s, it reports "The camera kept answering, so it did not reboot." and stops waiting.
- Apertar way: `requestRestartSystem` sends `restart_system` and toasts "Restart requested." (WCP:11324-11334@upstream-1.6.0). Reconnection is the 1 s `fetchState` poll plus the loading overlay (C3-N5).
- why it matters: Core's stop stops `camera_` before `webServer_` (App:8185-8190@cinemate-port), so the page keeps getting answers while a take drains. Probable failing input: Save and Reboot during a take with a full RAM buffer; a drain over 60 s gives a false "did not reboot" message while the reboot follows. Settle on a Pi: record 4K, fill the buffer, Save and Reboot.
- rework: poll `/api/state` (the upstream route) or reuse `fetchState`. Drop the never-down branch: the `restart_system` reply already confirms the request.
- effort: S
- deliberate: no

### WCP-10-F7 [mismatch, minor] Config Check and Save use two transports; Check falls back to base "h" and then always fails
- where: src/web/WebControlPage.cpp:18795@cinemate-port ; src/web/WebControlPage.cpp:18918-18927@cinemate-port
- port way: Check: `controlsCall({cmd:"set_controls", base: state.configRevision || "h", text, dry_run:"true"})` on `/api/command`. Save: POST `/api/config` with an `X-Apertar-Revision` header. Both end in `HardwareConfigStore::replace` (App:12763, App:8644). `"h"` is not a revision (absent file = `h0000000000000000`, HardwareConfigText.hpp:315); the store compares `base` also on a dry run and answers `stale` (HardwareConfigStore.cpp:282-295), so Check before load fails.
- Apertar way: one path per file: GET/POST `/api/config` (App:7168/7175@upstream-1.6.0). Route options come from the query via `queryParameterValue` (C3-S7).
- why it matters: one file, two transports for the same store call, plus a magic value that cannot succeed.
- rework: Check posts to `/api/config?dry_run=1` with the same header and body as Save (Core reads the flag with `queryParameterValue` and sets `flags.dryRun`). Disable Check until `state.configRevision` is set and delete the `"h"` fallback.
- effort: S
- deliberate: no

### WCP-10-F8 [duplication, minor] Two diff renderers; bootConfigOption re-implements ensureSelectEntries
- where: src/web/WebControlPage.cpp:18854-18887@cinemate-port ; src/web/WebControlPage.cpp:20225-20317@cinemate-port ; src/web/WebControlPage.cpp:20418-20436@cinemate-port ; src/web/WebControlPage.cpp:20038-20044@cinemate-port
- port way: `showConfigDiff`, `reviewBootConfig`/`bootConfigDiffLine` and `toggleBootConfigFile` each build a diff box (`.diff-add/.diff-del/.diff-gap`) and a row of JS-created buttons. Selects are rebuilt with `innerHTML = ""` + `bootConfigOption` to get a `disabled` flag.
- Apertar way: selects are filled through `ensureSelectOptions` / `normalizeSelectEntries` / `ensureSelectEntries` (WCP:6191, 6210, 6221@upstream-1.6.0). Disabled choices pass as `enabled:false` (`normalizeChoiceOptions` WCP:6317@upstream-1.6.0).
- why it matters: the same behaviour lives in two or three places.
- rework: one `renderDiffBox(boxId, lines, actions)`. Extend `normalizeSelectEntries` with `enabled` and call `ensureSelectEntries` from `renderBootConfigPort` and the display select; delete `bootConfigOption`.
- effort: S
- deliberate: no

### WCP-10-F9 [mismatch, minor] Remote controls loader runs its own untracked 5 s setTimeout loop
- where: src/web/WebControlPage.cpp:20869-20878@cinemate-port
- port way: `const loadRemoteControls = () => { if (controlsState.model) return; void loadControls(true); setTimeout(loadRemoteControls, 5000); }`. The timer is never stored or cleared.
- Apertar way: one poll loop, `window.setInterval(() => fetchState(true), 1000)` (WCP:11609@upstream-1.6.0). A retry is a stored timer: `state.previewRetryTimer = window.setTimeout(loadPreviewStream, 1500)` (WCP:8578@upstream-1.6.0). C3-I2.
- why it matters: a second hidden poll loop.
- rework: in `fetchState` after a good snapshot: `if (!controlsState.model && !controlsState.loading) void loadControls(true);` and delete the loop (or, minimally, store it as `state.controlsRetryTimer`).
- effort: S
- deliberate: yes. `1319967` and the code comment: the main page needs the controls before Settings opens.

### WCP-10-F10 [new-ground, nit] toggleRecord decides 'flushing' from page-side frameBufferBar
- where: src/web/WebControlPage.cpp:19199-19204@cinemate-port ; src/web/WebControlPage.cpp:19240@cinemate-port
- port way: `const flushing = frameBufferBar.safetyStop === true && !state.snapshot.timelapse_active;` bypasses the `media_writes_pending` guard and the `record_stop` branch, so a press during the flush starts a new take.
- Apertar way: the guard reads `state.snapshot` fields only (WCP:10690-10695@upstream-1.6.0, C3-N2).
- why it matters: the behaviour is an owner decision (keep it). Only the input is foreign; it is the store rev-WCP-08 reworks.
- rework: keep the behaviour. Read `state.snapshot.buffer_safety_stop` once rev-WCP-08's rework folds `frameBufferBar` into the snapshot. Dependency note, no separate work.
- effort: S
- deliberate: yes. `c5db8b2`; owner decision 2026-11-01 (fork-log).

### WCP-10-F11 [slop, minor] T43 tags, Cinemate history and a banner in comments; 32 comment lines
- where: src/web/WebControlPage.cpp:18758@cinemate-port ; 18792 ; 18811 ; 18889 ; 19868-19871
- port way: "// T43: line numbers...", "// T43 Check:", "// T43: the lines that differ", "// T43 history:", "// ---- Boot Config card (System pane) ... ----", "... Port of Cinemate's settings-editor config.txt tab." This slice adds 32 comment lines.
- Apertar way: the upstream JS has 2 comment lines in total (WCP:8474-8475@upstream-1.6.0, C3-I9).
- why it matters: tutorial numbers and port history mean nothing to the original developer.
- rework: delete the tags, the banner and the history sentence. Keep only one-line safety reasons.
- effort: S
- deliberate: no

### WCP-10-F12 [new-ground, nit] Save Config now takes two clicks (diff, then Save these changes)
- where: src/web/WebControlPage.cpp:20884@cinemate-port ; src/web/WebControlPage.cpp:18854-18887@cinemate-port
- port way: `saveConfigButton` -> `showConfigDiff` (LCS line diff); saving needs a second click.
- Apertar way: `saveConfigButton` -> `saveConfigFile`, one click (WCP:11556@upstream-1.6.0; `saveConfigFile` 10330).
- why it matters: a small change of upstream behaviour. The extra step is useful.
- rework: keep. Render it through the shared diff helper (F8).
- effort: S
- deliberate: yes. `8be1ab5`: "a diff before Save".

### WCP-10-F13 [mismatch, nit] Toast 'Storage pre-roll started' lacks the period
- where: src/web/WebControlPage.cpp:19828@cinemate-port
- port way: `showToast("Storage pre-roll started", false)`
- Apertar way: `showToast("Write speed test started.", false)` (WCP:11307@upstream-1.6.0, C3-N7)
- why it matters: style consistency.
- rework: add the period.
- effort: S
- deliberate: no
