# Conventions C3: the WebUI inside Core (upstream 1.6.0)

Scope: how the original developer builds the WebUI. Read only in `/home/user/wt/core-upstream` (tag `upstream-1.6.0`, `35dbe67`) and, for comparison with the touch UI, `/home/user/wt/ui-upstream` (`43888e5`). All line numbers `@upstream-1.6.0`. `WCP` = `src/web/WebControlPage.cpp`, `App` = `src/ApertarCoreApp.cpp`, `WS` = `src/web/WebServer.cpp`. All claims **confirmed** (read in code) unless labelled.

## 0. Counts

| What | Count | How counted |
| --- | --- | --- |
| `WCP` lines | 11 618 | `wc -l` |
| CSS / HTML / JS spans | 15-2420 / 2422-4037 / 4038-11611 | `grep -nE '<style>\|</style>\|<script>\|</script>'` |
| Main-page cards (`class="card`) | 4 (preview, Camera settings, System, Current capture) | `grep -n 'class="card'` -> 2458, 2532, 2596, 2700 |
| Settings nav entries / panels | 9 / 9 | `data-panel=` 2745-2777, panels 2796-3874 |
| Settings cards (`class="settings-card`) | 45 | `grep -c` |
| Overlays | 3 (settings 2731, clip browser 3979, loading 4032) + toast 4036 | |
| JS functions | 323, all at 4-space indent (flat) | `grep -cE '^\s*(async )?function [a-zA-Z]'` |
| Top-level `const` (option lists, meta, `state`) | ~40 lists 4039-4127 | read |
| `buildOptionButtons(` calls | 34 | `grep -c` |
| `case "set_...":` in client patch switch | 76 | `grep -c 'case "set_'` |
| `await sendCommand(` calls | 95 | `grep -c` |
| `showToast(` calls / of which `showToast(error.message, true)` | 157 / 86 | `grep -c` |
| Element ids / ids starting `settings` | 310 / 201; none contain `-` or `_` | `grep -oE 'id="..."'` |
| `getElementById` calls | 205 | `grep -c` |
| Inline `style="..."` attributes | 31 | `grep -c 'style="'` |
| JS comments | 2 lines (8474-8475); no CSS comments; no `/* */` | `grep -cE '^\s*//'` |
| `window.confirm` | 8 (10307, 10385, 10434, 10672, 11266, 11278, 11325, 11337) | `grep -n` |
| Colours in CSS | 36 `var(--...)`, 130 hex, 100 `rgba(` | count over 15-2420 |
| Icons | 45 PNG in `src/web/icons/` | `ls \| wc -l` |
| HTTP routes | 18 branches in one function (`App:7093-7650`) | read |

Typical size of one feature in the WebUI:

| Feature | HTML | JS | Places touched in `WCP` |
| --- | --- | --- | --- |
| SMPTE Bars toggle | 8 lines (3262-3270) | render 7 (10109-10115), patch 3 (8918-8920), favourite 5 (6913-6917), list + meta 2 (4092, 4142) | 5 |
| Fan mode select | 16 lines (3641-3656) | apply 11 (11088-11098), patch (9051), favourite (7245), listener (installInteractions) | 5 |
| Media speed test | 25 lines (3602-3626) | request 8 (11305-11312), listener 1 | 3 |

A small feature is 20-40 lines spread over 3-5 places in the one file. A feature never gets its own file.

## 1. STRUCTURE

### S1. The whole WebUI is one C++ function returning one raw string. Strength: always (only one such place).
- `WCP:5-7` `std::string_view webControlPageHtml()` / `static const char page[] = R"APERTAR(<!DOCTYPE html>`; `WCP:11614-11615` `)APERTAR"; return std::string_view(page, sizeof(page) - 1);`
- `src/web/WebControlPage.hpp:7` declares only that function.
- Served by `App:7102-7107` (`GET /` and `/index.html`).
- No `.js`, `.css` or `.html` file exists in `src/web/` (`ls`: only `.cpp`, `.hpp`, `icons/`). The only other served static files are PNG icons (S8).

### S2. Inside the string: CSS, then HTML, then JS, in that order; no `<link>` to CSS, no `<script src>`. Strength: always.
- `WCP:15` `<style>`, `2420` `</style>`, `4038` `<script>`, `11611` `</script>`. One of each (grep).
- `grep -nE 'https?://|cdn|googleapis'` finds no external URL. No web font is loaded; `font-family: "Inter", "Segoe UI", sans-serif` (`WCP:42`) relies on local fonts.

### S3. Page regions: top bar, two-column main grid of cards, then full-screen overlays. Strength: always.
| Region | Lines | Notes |
| --- | --- | --- |
| Top bar | `WCP:2424-2454` | brand + host, date pill, REC status pill, two icon buttons (clip browser, settings) |
| `main.main-grid` left `section.column` | `2457-2593` | preview card, "Camera settings" card (fps, ISO, shutter, resolution, crop, WB) |
| `main.main-grid` right `aside.column` | `2595-2726` | "System" telemetry card, "Current capture" card |
| Settings overlay | `2731-3978` | sidebar nav + 9 panels |
| Clip browser overlay | `3979-4031` | |
| Loading overlay + toast | `4032-4036` | "Connecting to ApertarCore..." |
The main page holds only the camera-critical controls (exposure, resolution, record). Everything else is in the settings overlay.

### S4. Navigation = one sidebar of `button.settings-nav-item[data-panel]` and one `section.settings-panel[data-panel]` per entry, switched by class `active`; titles and subtitles come from `settingsPanelMeta`. Strength: always.
- Nav `WCP:2744-2780`; panels `2796, 3075, 3121, 3359, 3457, 3673, 3800, 3840, 3874`.
- `setSettingsPanel` `WCP:6149-6170` toggles `active` on both lists and sets `settingsPageTitle` / `settingsPageCopy` from `settingsPanelMeta` (`WCP:4164-4201`).
- Panel load hooks live in `setSettingsPanel`: presets fetch (6164), config fetch (6166), IMU redraw (6168), audio caps (6162). There is no router, no URL hash, no history.
- Order mirrors the touch UI sidebar: Favorites, Monitoring, Record, Audio, Power/Media, System, Presets, [Wi-Fi -> Config], Info (`ui-upstream qml/SettingsPage.qml:827-837` `defaultSidebarOrder`). The WebUI replaces Wi-Fi with Config (hardware-config editor).

### S5. Rough edges in navigation that are "the Apertar way" and must not be fixed unasked. Strength: once each.
- Panel id `power` is labelled "Media" (`WCP:2761-2764`, `settingsPanelMeta.power.title = "Media"` 4186-4188); touch UI calls it "Power".
- Cards are declared in one panel and moved at runtime: `arrangeSettingsPanels` (`WCP:6119-6128`) moves `settingsMediaCard`, `settingsFormatMediaCard`, `settingsMediaSpeedCard` into the `power` panel and the battery cards into `system`. HTML position therefore does not equal display position.
- `settingsPanelMeta` declares `record` first (4165) while the HTML default active panel is `favorites` (2745, 3075); `setSettingsPanel` falls back to `"record"` for unknown names (6150).

### S6. Option lists live as top-level `const` arrays at the top of the script, and several are duplicated from Core and from the touch UI. Strength: always for location; duplication is usual.
- `WCP:4039-4085`: `fpsPresets`, `isoOptions`, `shutterOptions`, `recordFormatOptions`, ..., `sleepModeOptions`. Labels, not wire values (e.g. `"1.33x"`, `"Free Run"`, `"Exposure Based"`).
- `favoriteCandidateOrder` exists three times with different contents: `WCP:4086-4122` (35 items), `App:727-760` (Core copy), `ui-upstream qml/SettingsPage.qml:838+`. `cameraStandby` is in `App:744` and the QML list but not in `WCP` (`grep -c cameraStandby WCP` = 0).
- Sensor/fps/resolution caps are mirrored client-side (`WCP:4810-5510`, e.g. `imx477MaximumSupportedFps`, `sensorResolutionOptions`) from the copies in `CameraController.cpp` (`CC:2493-2706`, `CC:355-533`). Where Core reports capabilities, the page prefers them: `recordingFeatureSupported` (`WCP:5570-5572`) reads `snapshot.recording_capabilities` from `/api/state`.

### S7. HTTP routes: one function, one flat `if (method && path)` chain, the page's own JSON endpoints under `/api/`, every camera action through `POST /api/command`. Strength: always.
- `App:7093` `WebServer::Response ApertarCoreApp::handleWebRequest(const WebServer::Request &request)`; branches 7095 (OPTIONS), 7102 (`/`), 7109 (`/preview.mjpeg`), 7124 (`/icons/` prefix), 7154 (`/api/state`), 7161 (`/api/media`), 7168/7175 (`/api/config`), 7197, 7318, 7360, 7367, 7392, 7440, 7477, 7503, 7575, 7637 (`/api/command`), fallthrough 7644-7649.
- Exact match `request.path == "..."` (7154); prefix with `request.path.rfind("/icons/", 0) == 0` (7124).
- Parameters come from the query string through `queryParameterValue(request.query, "kind")` (7198, 7441, 7478, 7504); bodies are raw text (`POST /api/config`, 7175) or the flat command JSON.
- `POST /api/command` (7637-7642) does nothing but `handleWebCommand(request.body)` -> `parseControlCommand` -> `handleCommand` (`App:7083-7089`). So the WebUI uses the same command vocabulary, mutex and refusals as the socket (`App:9093` `std::lock_guard<std::mutex> commandLock(commandMutex_);`). README: "Native UI commands, WebUI requests and hardware actions reach the same controller and busy-state checks." (`README.md:271`).
- Dedicated routes exist only for things that are not commands: file transfer (media download/zip, preset download/import), library listings (`/api/media`, `/api/presets`), the config file, the MJPEG stream, icons. Media delete is a route (7503) and repeats the recording refusal itself (7514-7520).
- The JSON bodies of these routes are built by free helpers in the anonymous namespace (`buildHardwareConfigFileJson`, `saveHardwareConfigFile` App:5290-5387) or by `ApertarCoreApp::build*Json` members (`App:7651-8047`); the route body only calls them and wraps a `Response`.

### S8. Static assets = PNG icons only, read from the source tree at runtime, no install step. Strength: always.
- `App:7124-7151` serves `/icons/<name>`; `webIconsDirectory()` `App:2420-2440` searches `src/web/icons` relative to cwd and to the executable (5 candidates). `CMakeLists.txt:94-95` compiles `WebControlPage.cpp`, `WebServer.cpp`; no install rule for icons (`grep -n icons CMakeLists.txt` empty).
- Icons are referenced as `<img class="icon-image" src="/icons/settings.png" alt="">` (`WCP:2446-2451`, `2536`, nav 2746-2778). Icon names reuse the touch UI's names (`favorites.png`, `monitoring.png`, `record.png`, ...).
- Glyphs instead of icons in a few spots: `●` status dot (2442), `▣` preview placeholder (2513), `•` separators (2432, 6473).

### S9. The web server is a minimal hand-written HTTP/1.1 server; no library, no TLS, no auth. Strength: always (only one).
- `WS` 394 lines; `WebServer::start(bindAddress, port, handler)` (`WS:185`); one detached thread per client (`WS:276-287`); `Connection: close` and `Cache-Control: no-store` on every reply (`WS:133-134`, `147-148`); 1 MiB request cap -> 413 (`WS:23`, `360-363`).
- Security is a same-origin check in the server, not in routes: `allowedBrowserOrigin` (`WS:156-171`) rejects `Sec-Fetch-Site: cross-site` and an `Origin` that differs from `http://<Host>`; no `Origin` (curl, native) passes. Rejection text: "Cross-origin camera control is not allowed. Open the camera WebUI directly." (`WS:372`). Interrupted bodies are never passed to a handler ("Never pass an interrupted config upload to a handler that saves it." `WS:366`).
- Bind/port from CLI: `--web-bind`, `--web-port` (default 8000, 0 disables) `main.cpp:35, 65-76`; `ApertarCoreApp.hpp:35-36`. Started in `App:6869-6880`.
- README states the threat model plainly: "The WebUI is not an authenticated internet-facing service." (`README.md:130`).

## 2. IDIOM

### I1. JS is plain ES2017 in one flat script: `const`, `let`, arrow callbacks, `async/await`, `fetch`. No framework, no modules, no classes, no build step, no storage. Strength: always.
- `grep -nE 'class [A-Z]|import |export |require\(|React|Vue|jQuery|\$\('` finds only error-message strings (10478, 10485).
- `grep -nE 'localStorage|sessionStorage|WebSocket|EventSource'`: none. All state comes from Core.
- 323 functions all at 4-space indent; helpers are named functions, not methods.

### I2. One global mutable `state` object holds every piece of client state, including timers and WebGL handles. Strength: always.
- `WCP:4204-4266` `const state = { snapshot: null, fetchInFlight: false, ..., toastTimer: null, ..., previewProcessingGl: null, ... }`.
- `state.snapshot` is the last `/api/state` JSON (`WCP:9334`); render reads only from it. Timers are stored as `state.<thing>Timer` (`wbCommitTimer` 4219, `inputVolumeCommitTimer`, `toastTimer` 4222, `previewRetryTimer` 4223) and cleared with `clearTimeout` before re-arming (`WCP:7809`, `8562`, `11594`).
- Busy flags are `state.<thing>InFlight` / `...Busy` / `...Running` (`fetchInFlight`, `presetsFetchInFlight`, `configSaveInFlight`, `audioCapabilitiesBusy`, `gyroCalibrationRunning`).

### I3. Data flow: poll `/api/state` every second, re-render the whole page from the snapshot; commands patch the snapshot optimistically and re-render; a refresh follows. Strength: always.
- Bootstrap `WCP:11606-11610`: `installInteractions(); installPreviewStream(); startLiveReadoutLoop(); window.setInterval(() => fetchState(true), 1000); fetchState(false);`
- `fetchState` `WCP:10207-10244`: `fetch("/api/state", { cache: "no-store" })`, drops a reply that raced a command (`commandEpoch`, 10226-10230), queues one follow-up fetch.
- `renderSnapshot(snapshot)` `WCP:9327-10206`, ~880 lines, one function: sets text, toggles classes, disables controls, rebuilds every pill grid on every poll.
- `sendCommand(payload)` `WCP:9109-9145`: clone snapshot -> `applyCommandSnapshotPatch(payload, null, true)` -> `renderSnapshot` -> `POST /api/command` -> on `!result.ok` re-render the previous snapshot and `throw new Error(result.error || "Command failed.")` -> patch again with Core's reply -> `scheduleStateRefresh(80|140 ms)`.
- `applyCommandSnapshotPatch` `WCP:8679-9108`: one `switch (cmd)` (8696) with 76 `case "set_..."` arms, the client-side copy of each command's effect.
- Core returns a nested object for `/api/state` (`"capture":{`, `"ui":{` `App:7965`, `"system":{`, `"audio":{`, `"device":{`); socket replies stay flat. `ensureSnapshotShape` (`WCP:4276-4292`) guarantees the sub-objects exist.

### I4. Every control handler is `async`, wraps `await sendCommand({ cmd: "...", ... })` in try/catch, and reports failure with `showToast(error.message, true)`. Strength: usually (86 of 95 `sendCommand` callers; exceptions: favourites route through `dispatchFavoriteCommand` `WCP:7307-7313`, which is the same try/catch; `notifyStandbyActivity` uses a raw `fetch(...).catch(() => {})` `WCP:11503-11515`).
- Examples: `WCP:9876-9882` (fps), `10109-10115` (SMPTE), `10791-10799` (`applySelectCommand`), `11088-11098` (fan).
- Error text shown is Core's `errorReply` message verbatim; the page does not translate errors.

### I5. Command payloads mirror the socket protocol: flat object, `cmd` + scalar fields; booleans for UI toggles are sent as the strings `"true"` / `"false"` in the field `enabled`. Strength: usually.
- `{ cmd: "set_smpte_enabled", enabled: value === "On" ? "true" : "false" }` (`WCP:10111`, 6915); Core reads `command.string("enabled")` and accepts `"true"`/`"1"` (`App:9482-9486`).
- Values: `value` for a single scalar (`{ cmd: "set_fps", value: Number(value) }` 9878), named fields where Core needs them (`kelvin` 9908, `filesystem` 11270, `device_path` 11294, `width`/`height` in `resolutionCommandPayload`).
- Exception: `set_standby_usb_power_off` sends a real boolean `enabled: event.target.value === "true"` (`WCP:11530`), part of the later standby code, which also drops the spaces inside braces (`{cmd: "user_activity"}` 11512, `{cmd: ...}` 11316). Counter-example to formatting, not a rule.

### I6. Choice controls are pill grids built by `buildOptionButtons(containerId, options, currentValue, onClick, columns)`; selects are filled by `ensureSelectOptions` / `ensureSelectEntries`. Strength: always for pills on static pages; favourites use parallel `createFavorite*` builders.
- `buildOptionButtons` `WCP:9147-9167`: clears the container, one `button.pill-button` per option, adds `active` when `option.value === String(currentValue)`, adds `disabled` and `button.disabled` when `option.enabled === false`.
- Options may be strings or `{ value, label, enabled }` objects (`normalizeChoiceOptions` `WCP:6317-6336`). Unavailable choices are passed with `enabled: false`, not removed: `rawBitDepthOptions.map((value) => ({ value, label: value, enabled: rawBitDepthOptionEnabled(...) }))` (`WCP:9950-9954`), WB `enabled: whiteBalanceAvailable` (9905-9906).
- On/Off toggles are a two-pill grid over `const toggleOptions = ["Off", "On"]` (`WCP:4066`) with `formatToggleLabel(bool)` (`5901-5903`); 17 static (9964-10169) and 17 favourite (6850-7172) uses. There is no checkbox or switch widget anywhere (`grep -c 'type="checkbox"'` = 0).
- Selects: `ensureSelectOptions(id, values)` rebuilds only when the list changed (`WCP:6191-6208`); `setFormValue` never overwrites the focused element (6178-6183).
- Favourites build the same widgets from code: `createFavoriteSelectBlock` (`WCP:6619-6628`, uses `select-block` / `select-topline` / pill grid), `createFavoriteSelectField` (6634+).

### I7. Naming. Strength: always (checked by grep).
| Thing | Pattern | Evidence |
| --- | --- | --- |
| Element ids | camelCase, region prefix; settings controls `settings<Thing><Kind>` with Kind = `Options` (pill grid), `Select`, `Range`, `Value`, `Button`, `Card`, `Note`, `Field` | `settingsSmpteOptions` 3268, `settingsFanModeSelect` 3650, `settingsMediaSpeedResultValue` 3612, `runMediaSpeedTestButton` 3622, `settingsThermalCard` 3628; 0 ids with `-`/`_` |
| Main-page ids | `<thing>Options`, `<thing>Badge`, `<thing>Value` | `fpsOptions` 2549, `isoBadge` 2505, `timecodeValue` 2522 |
| CSS classes | kebab-case, block-element by hyphen, state by extra class `active`, `disabled`, `hidden`, `recording`, `error`, `visible`; size modifiers `three-col`, `two-col`, `field-span-2` | `pill-button.active` 783, `.hidden` 1975, `pill-grid.three-col` 755 |
| JS option lists | `<thing>Options` (labels) | 4040-4085 |
| JS senders | `apply<Thing>Selection` for select-driven commands, `request<Action>` for buttons with side effects, `adjust<Thing>` / `reset<Thing>` for steppers, `schedule<Thing>Commit` for debounced sliders | `applyFanModeSelection` 11088, `requestFormatMedia` 11262, `adjustCustomBatteryVoltage`, `scheduleInputVolumeCommit` |
| JS fetchers | `fetch<Thing>`, `save<Thing>`, `delete<Thing>`, `import<Thing>` | 10207, 10246, 10304, 10330, 10426, 10457 |
| Renderers / setters | `render<Thing>`, `set<Thing>Open`, `set<Thing>Panel`, `setText`, `setFormValue`, `setElementDisabled` | 9327, 7315, 6130, 6149, 6172-6189 |
| Label mappers | `<thing>Label`, `<thing>CommandValue`, `<a>To<b>` | `recordingFormatCommandValue` 5511+, `zebraLevelToThreshold`, `opacityLabelToValue` |
| Wire command names | `snake_case` verbs: `set_*`, `apply_*`, `*_start`/`*_stop`, plain verbs | `App:9216` help list |

### I8. Formatting: 2-space HTML/CSS indent inside the string, 4-space base indent for JS bodies with 2-space nesting; double quotes; semicolons; single-statement `if` without braces. Strength: usually (standby code at 11316, 11503-11535 drops spaces in braces).
- `if (!container)\n        return;` (`WCP:9149-9150`), `if (!result.ok) {` with braces only for multi-line bodies (9129).

### I9. Almost no comments. Strength: always (2 JS comment lines in 7573 lines; none in CSS/HTML).
- Only `WCP:8474-8475` ("Freeze source luminance before overlays change data in place..."). In `WS`, comments state a safety reason in one line (`WS:161` "Native clients/CLI have no Origin.", `WS:366`).
- A contribution that adds section-banner comments or JSDoc blocks is out of style.

### I10. CSS: a small token set on `:root`, then mostly literal colours; zinc greys, white as "selected", red for danger/record, green for OK; large radii; 4 fixed breakpoints. Strength: usually (tokens exist but literals dominate: 36 `var(` vs 130 hex + 100 `rgba(`).
- Tokens `WCP:15-43`: `--bg-*`, `--card-bg`, `--card-border`, `--surface*`, `--text`, `--muted`, `--muted-2`, `--ok #34d399`, `--danger #ef4444`, `--radius-xl 28px` ... `--radius-sm 14px`, `--content-width 1320px`; `color-scheme: dark`. Dark only; no light theme.
- Most used literals: `#27272a` (24), `#ffffff` (18), `#f4f4f5` (12), `#d4d4d8` (8), `#3f3f46` (6) (Tailwind zinc scale).
- Spacing steps seen: gaps 8 / 10 / 12 / 14 / 16 / 18 / 20 / 24 px; card padding 20 px (`.card-body` 255, `.settings-card` 1433-1441); pill padding `11px 10px`, radius 18 px (763-774); buttons `min-height: 50px`, radius 18 px (1632-1640); `select`/`input` `min-height: 50px` (1519-1530).
- Selected state = white fill, dark text: `.pill-button.active { background: #ffffff; color: #09090b; }` (`WCP:783-788`).
- Breakpoints `@media (max-width: 1120px | 720px | 480px | 560px | 420px)` at 2034, 2062, 2190, 2319, 2391 (out of order; one block each, at the end of the stylesheet).
- Inline `style=` is used for one-offs (31): still-exposure overlay `WCP:2461-2462`, SMPTE bar colours 2465-2491, title margins `style="margin:0;"` 2601, 2702, 2737.

### I11. Disabled and unavailable look. Strength: always.
| Control | Look | Line |
| --- | --- | --- |
| `.pill-button.disabled, :disabled` | grey text `rgba(228,228,231,0.34)`, darker `#17171b`, no shadow, `cursor: not-allowed`, no hover change | `WCP:790-803` |
| `.primary/.secondary/.danger-button:disabled` | `opacity: 0.45; cursor: default; transform: none` | `1700-1706` |
| `.settings-select:disabled` | `opacity: 0.56; cursor: not-allowed`, greyed chevron | `1603-1608` |
| `.settings-input:disabled` | own rule | `1557` |
| `.record-button:disabled` | own rule | `558` |
| Not applicable to this sensor/format | element hidden with `.hidden` (`display: none !important`, 1975) | `cropRatioBlock` toggled `WCP:9918-9920`; `settingsProresColorField` 9507 |
Rule of thumb in the code: "exists but not now" -> disabled; "does not exist for this configuration" -> hidden. Placeholder `--` for unknown values (`WCP:2434` "Loading...", 3142 `--`, `formatFps` returns `"--"`).

### I12. Button variants: `primary-button` (light, main positive action), `secondary-button` (dark outline), `danger-button` (red tint, destructive), plus one special `secondary-button standby-button` (blue). Strength: always.
- `WCP:1632-1706`; Power Actions: Standby (secondary standby), Restart Camera (secondary), Shutdown (danger) `WCP:3662-3665`.

## 3. INTENT

### N1. Core is the source of truth; the WebUI is a mirror that never keeps its own settings. Strength: always.
- No browser storage (I1). Every value rendered comes from `/api/state`; optimistic patches are discarded on error (`WCP:9130-9131`) and overwritten by the next poll.
- README: "ApertarCore is the source of truth for camera and capture state." (`README.md:271`).

### N2. Safety rules are enforced in Core; the page only mirrors them by disabling controls and shows Core's refusal text. Strength: always.
- Core: media actions refused while recording/writing/testing (`App:9098-9107` "Stop recording, still captures and media tests before changing media."); capture refused while writes pending (`App:9095-9097`); media delete route refuses while recording (`App:7514-7520`).
- Page: `setElementDisabled("settingsProresColorSelect", isRecording || !!snapshot.timelapse_active)` (`WCP:9510`), same for CDNG preview colour (9513), compression (9529), standby button (9584), IMU calibrate (`imuCanCalibrate = !isRecording && ...` 9425), record button (9805). Favourite controls pass the same `disabled` flag (`WCP:7026`, 7255).
- `toggleRecord` refuses locally only for obvious cases ("No media mounted." toast, `WCP:10709-10712`) and otherwise lets Core decide.

### N3. During a take the operator can stop, not reconfigure: capture-format and media controls lock; monitoring aids stay live. Strength: usually (lock list above; monitoring toggles 10069-10147 carry no recording gate).

### N4. Destructive or system-level actions ask with a native `window.confirm`, worded as a question naming the effect; routine settings never ask. Strength: always (8 confirms, all destructive/system: delete media x2, delete preset, discard config edits, format, eject, restart, shutdown).
- `"Format the mounted media as " + formatLabel + " now? This will erase it and keep the current drive name where possible."` (`WCP:11266`); `"Shut down the Apertar system now?"` (11337).

### N5. Feedback: one toast element, bottom-right, auto-hides (2.6 s info, 4.6 s error); success toasts only for actions with lasting or system effect; pill changes give no toast (the pill itself turns white). Strength: usually.
- `showToast(message, isError)` `WCP:7804-7813`.
- Success toasts list (grep `showToast("...", false)`): "Fan mode updated.", "Media ejected.", "Restart requested.", "Date and time applied.", "Battery profile updated.", "Timelapse started." ... ; none in the 34 `buildOptionButtons` handlers.
- Recording and still failures from Core surface once as an error toast on change: `"Recording stopped: " + snapshot.recording_error` (`WCP:9331-9333`), `"Still not saved: " ...` (9328-9330). Poll failure: "Could not reach ApertarCore web control." only on non-silent fetch (10233-10234).
- Connection state is a full-screen loading overlay "Connecting to ApertarCore..." until the first snapshot (`WCP:4032-4034`, removed 9338-9339). Preview loss is an overlay "Preview unavailable. Retrying..." with a 1.5 s retry (`WCP:8576-8580`).

### N6. Wording mirrors the touch UI and the operator's vocabulary. Strength: always for shared features.
- Same favourite titles and section names as the touch UI ("External Monitor", "Focus Peaking", "Controls Transparency", "Auto Power Off") `WCP:4123-4163`; panel copy says it outright: "Manage the same quick access favorites list used by the on-device UI." (4171), "Download the same preset files saved by the native camera UI." (4192).
- Camera words: "Frame rate", "ISO", "Shutter angle" / "Shutter speed" switching with still mode (`WCP:9501`), "White balance", "Crop mode", status pill "READY", "REC", "TIMELAPSE", "SOUND REC", "WRITING", "NO MEDIA" (9491).
- Case: card titles are Title Case in newer cards ("Media Speed", "Power Actions") and sentence case in older ones ("Live preview", "Assist tools", "Camera settings"). Both occur; neither is enforced.

### N7. UI text is short and factual: card copy one sentence (~6-15 words) ending with a period; notes explain consequences for the operator, often the post-production consequence. Strength: usually.
- "Configure HDMI monitoring controls." (`WCP:3153`); "Fan control and temperature management." (3632); "Measure sequential write performance for the mounted recording media." (3606).
- Longer notes only where a wrong choice costs footage or grading time: "Preview only. Linear has no display gamma and looks darker; 8-bit preview precision is limited. DNG RAW is unchanged." (`WCP:9515`); Bracketing note (2819).
- Errors from Core are full sentences with the remedy ("Stop recording before deleting media." `App:7518`).

### N8. What the WebUI deliberately does not do. Strength: always (each shown in code).
| Not done | Evidence |
| --- | --- |
| Wi-Fi / hotspot control | favourites render a placeholder: "Wi-Fi control is still handled in the native UI. This web app currently mirrors the network readout only." `WCP:7262-7266`; "Managed from the DPI UI" 6476-6481 |
| Authentication, TLS, internet exposure | `README.md:130`; `WS` has no auth code |
| Commands Core lacks | KB `core-map.md` 1.3: "The WebUI sends no command Core lacks"; every `cmd:` appears in `App:9216` help list or handleCommand |
| Diagnostic / raw commands | never sends `set_tuning_file`, `set_capture_mode`, `set_imu_sync_offset` (absolute), `get_state`, `shutdown` (KB 1.3 list; `"set_tuning_file"` and `"set_capture_mode"` occur 0 times in WCP, the rest from the KB list) |
| Live push (WebSocket/SSE) | 1 s polling only (`WCP:11609`) |
| Client persistence | no storage API (I1) |
| Its own command semantics | `POST /api/command` is `handleCommand` (S7) |

### N9. Same-origin protection is server-wide and fails loudly with an instruction, not silently. Strength: once (single server).
- `WS:370-373`; payload `{"ok":false,"error":"Cross-origin camera control is not allowed. Open the camera WebUI directly."}`.

### N10. Every HTTP JSON reply uses the socket's `okReply` / `errorReply` shape with id `-1`, and HTTP status codes 400 / 404 / 405 / 500 / 503 on route failures; `/api/command` always returns 200 with `ok:false` on a refused command. Strength: always for routes.
- `errorReply(-1, "Icon not found.")` `App:7133`; `okReply(-1, "\"deleted_name\":...")` 7499; 400 `App:7445`, 404 7529, 500 7563, 405/404 fallthrough 7644-7649; 503 for MJPEG without JPEG build 7117-7119.
- Route error texts: short sentence with period ("Preset name is missing.", "Media item not found.").

## 4. RECIPES

### R1. Add an On/Off toggle (a UI.conf preference such as a monitoring aid)
1. Core: add the key to `SharedUiSettingsSnapshot` and its parser (`App:1581-1936`), expose it in `/api/state` under `"ui":{` (`App:7965-8021`, e.g. 7985 `",\"smpte_enabled\":"`).
2. Core: one line in `handleCommand`: `if (const auto reply = handleUiToggle("set_<x>_enabled", "<x>Enabled")) return *reply;` next to `App:9507`; add the name to the `help` list `App:9216`.
3. WCP HTML: inside the right `settings-panel`, a `settings-option-group` > `section.select-block` > `div.select-topline > span` + `<div class="pill-grid" id="settings<X>Options"></div>` (pattern `WCP:3263-3269`).
4. WCP render: in `renderSnapshot` near 10109: `buildOptionButtons("settings<X>Options", toggleOptions, formatToggleLabel(<x>Enabled), async (value) => { try { await sendCommand({ cmd: "set_<x>_enabled", enabled: value === "On" ? "true" : "false" }); } catch (error) { showToast(error.message, true); } });`
5. WCP patch: `case "set_<x>_enabled": uiState.<x>_enabled = boolValue; break;` in `applyCommandSnapshotPatch` (`WCP:8918-8920`).
6. If it is a favourite in the touch UI: add the id to `favoriteCandidateOrder` and `favoriteItemMeta` (`WCP:4086`, 4123), a `case` in `renderFavoriteControls` (pattern 6913-6917), and keep `App:727` and `ui-upstream qml/SettingsPage.qml:838` in step.
7. Gate during a take only if Core refuses it during a take (`setElementDisabled` in `renderSnapshot`, 9510).
No success toast.

### R2. Add a pill list (one value of N)
1. Core: command `set_<x>` with `value` in `handleCommand` (flat `if (command.name == ...)`), value in `/api/state` (top-level camera field near `App:7835+` or `"ui":{`).
2. WCP: `const <x>Options = ["Label A", "Label B", ...];` in the list block `WCP:4039-4085` (labels as the operator reads them; a `<x>CommandValue(label)` / `<x>Label(value)` mapper next to the related helpers if wire values differ, pattern 5511-5651).
3. WCP HTML: `section.select-block` with `select-topline` (label + optional `span.select-value.select-value-pill` current value, 2581-2584) and `<div class="pill-grid [three-col|two-col]" id="settings<X>Options">`.
4. WCP render: `buildOptionButtons(id, options, currentLabel, async handler, columns)`; for options that the sensor/format cannot use, map to `{ value, label, enabled: false }` (9950-9954); hide the whole block with `.hidden` when it does not apply (9918-9920).
5. WCP patch: `case "set_<x>":` in `applyCommandSnapshotPatch`.
6. Favourites: as R1 step 6 using `createFavoriteSelectBlock`.

### R3. Add a settings card with a command behind it (button action)
1. Core: command in `handleCommand`; put busy-state refusals in Core, early in the function next to `App:9095-9110`, with a remedy sentence.
2. WCP HTML: in the right panel, `<div class="settings-card" id="settings<X>Card">` > `div.settings-card-head` > `div` > `h3.settings-card-title` + `p.settings-card-copy` (one sentence); body with `capture-list`/`capture-row` read-outs or `settings-field-grid`/`field-stack`; then `div.settings-action-row` with `<button class="secondary-button|primary-button|danger-button" id="<verb><X>Button" type="button">Label</button>` and optional `span.subtle-note` (pattern `WCP:3602-3626`, 3658-3671).
3. WCP JS: `async function request<X>()` next to `requestFormatMedia` (`WCP:11262-11347`): `window.confirm("...?")` first if destructive or system-level; `try { await sendCommand({ cmd: "<x>" }); showToast("<Done>.", false); } catch (error) { showToast(error.message, true); }`.
4. WCP wiring: one line in `installInteractions` (`WCP:11348-11605`): `document.getElementById("<verb><X>Button").addEventListener("click", request<X>);`
5. WCP render: read-outs with `setText("settings<X>Value", ...)`, disabling with `setElementDisabled("<verb><X>Button", isRecording || ...)` in `renderSnapshot`.
6. If the card belongs to a panel other than where it is easiest to declare, the existing code moves cards with `arrangeSettingsPanels` (6119); prefer declaring it in its panel.
7. Panel-specific loading: add to `setSettingsPanel` (6149-6170). New panel: nav button (2744-2780, icon from `/icons/`), `section.settings-panel[data-panel]`, entry in `settingsPanelMeta` (4164-4201), keep the touch UI order.

### R4. Add an HTTP route
1. First ask whether it is a command; if so it goes through `POST /api/command` and needs no route (S7). Routes are for files, listings and the config text.
2. Write the work as a free helper in the anonymous namespace of `App` (pattern `buildHardwareConfigFileJson` / `saveHardwareConfigFile` `App:5290-5387`) or a `build<X>Json() const` member next to `App:7651-7710` (declare in `ApertarCoreApp.hpp`).
3. Add one branch to `handleWebRequest` before the `/api/command` branch (`App:7637`): `if (request.method == "GET" && request.path == "/api/<x>") { WebServer::Response response; response.contentType = "application/json; charset=utf-8"; response.body = build<X>Json(); return response; }`. Query params via `queryParameterValue(request.query, "<p>")`; reply `okReply(-1, ...)` / `errorReply(-1, "<Sentence.>")` with status 400/404/500.
4. If it touches media or files, repeat Core's busy refusal in the route (`App:7514-7520`) and reuse path guards (`resolveMediaLibraryPath`, `pathIsInsideRoot` `App:5469-5666`).
5. No auth, CORS or header work in the route: the origin check is in `WebServer` (`WS:156-171`, 370).
6. WCP: `async function fetch<X>(silent)` near `WCP:10207-10503` with a `state.<x>FetchInFlight` guard, `const payload = await response.json(); if (!payload.ok) throw new Error(payload.error || "Could not ...");`, error to `showToast(..., true)` unless `silent` (pattern `saveConfigFile` 10330-10359).

## Challenge

Challenger pass against `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream` (`upstream-1.6.0`). Rule ids are the C3 ids from the challenge brief. Searches: `grep -n` over `src/web/WebControlPage.cpp` (WCP), `src/ApertarCoreApp.cpp` (App), `src/web/WebServer.cpp` (WS); the JS block WCP:4038-11611 extracted and grepped for globals, `cmd:` payloads, `case` labels, `fetch(`, `innerHTML`, `console.`.

| Id | Verdict | Counter-example / note |
| --- | --- | --- |
| C3-S1 | holds | One `<style>` (WCP:15-2420), one `<script>` (4038-11611), no `<script src>`, no CSS `<link>`. The only `<link>` tags are the favicon and touch icon at WCP:13-14, both `/icons/apertar.png` served by Core. Not a counter-example, but a contribution may add more `<link rel="icon">`-style local links. |
| C3-S2 | holds | Main grid WCP:2456-2700 has the preview card, the exposure/resolution card and two telemetry cards; settings sidebar at 2733. 9 `data-panel` nav buttons (2745-2777) and 9 panels. Rough edge: panel declaration order in HTML (record 2796, favorites 3075, monitoring 3121, audio 3359, system 3457, power 3673, ...) differs from nav order; match it, do not reorder. |
| C3-S3 | weaken to usually; evidence fixed | (a) `sendCommand` is not the single `/api/command` caller: `notifyStandbyActivity` posts `{cmd:"user_activity"}` with a raw `fetch` (WCP:11509-11513). (b) Write actions on stored files go through dedicated POST routes, not commands: `/api/presets/save` (App:7440), `/api/presets/delete` (App:7477), `/api/presets/import` (App:7392), `/api/media/delete` (App:7503), `/api/media/delete-selected` (App:7575), `POST /api/config` (App:7175). The real boundary: camera and system state -> command; reading or writing files in the media/preset/config libraries -> route. `apply_preset` stays a command (App:10230, WCP:10521). |
| C3-S4 | holds; detail added | All 20 branches sit before `/api/command` (App:7637). Statuses used: 204 (App:7097), 400, 404, 405 (fallthrough 7645), 500, 503 (MJPEG not compiled, App:7117). The body is usually written inline in the branch (media delete App:7503-7574 inlines the filesystem work), not always delegated to a helper: "delegate to a helper" is usually. Each branch spells out `WebServer::Response response; ... contentType = "application/json; charset=utf-8"` itself (51 `WebServer::Response response;` in App:7080-7650, no reply helper). |
| C3-S5 | strengthen to always (single place) | `kMaxRequestSize = 1024 * 1024` WS:23, 413 at WS:360-361, origin check WS:156-171 and 370-373. grep `Origin|Access-Control|auth|token` in App finds no route-level header work. Only one server, so "always (only one such place)". |
| C3-S6 | holds as usually; exception added | Top-level option arrays WCP:4040-4090. Exception: many `<select>` lists are literal `<option>` elements in the HTML (42 `<option` lines, e.g. colour pipeline WCP:2881-2896, DNG compression 2904-2907, UI orientation 3468-3471, format filesystem 3590), and some lists are built inside functions (`const options = [{ value: "none", label: "Uncompressed" }]` WCP:5584, `evOptions` 9672). Favourites list is in three places: WCP:4091, App:727, ui-upstream `qml/SettingsPage.qml:838`. |
| C3-S7 | holds | 45 files in `src/web/icons`, all `.png`; all but `apertar.png` exist with the same name in ui-upstream `qml/icons/`. Classes vary: `icon-image` (11), `settings-nav-icon-image` (2746-2778), `brand-logo` (2427); no inline `<svg>`, no `data:image`. |
| C3-I1 | holds | No `class`, `import`, `export`, `var`, `.then(`, `function(` in the script block; only module-level bindings are `const` arrays, `favoriteItemMeta`, `settingsPanelMeta` and `state`. No storage, WebSocket or EventSource. |
| C3-I2 | holds | Module-level names: option arrays + `state` only. 65 distinct `state.<x> = ` fields; all timers stored on `state` (WCP:7810, 8578, 8589, 9237, ...). Only closure-local state found: `let lastStandbyActivity` inside `installInteractions` (WCP:11503). Minor; rule stays always for module-level state. |
| C3-I3 | weaken the "add a case" part to usually | Poll loop holds (WCP:11609 `setInterval(() => fetchState(true), 1000)`, `sendCommand` 9109-9145 rollback at 9130-9131). But four `set_*` commands have no `case` in `applyCommandSnapshotPatch` (8678-9108): `set_exposure_compensation` (11392), `set_exposure_metering` (11396), `set_standby_timeout` (11519), `set_standby_usb_power_off` (11527); they rely on the post-command refresh. |
| C3-I4 | holds as usually | 99 `catch (error) {`, 86 `showToast(error.message, true)`. Exceptions: fire-and-forget `user_activity` (11513 `.catch(() => {})`); compact one-line form without spaces `try { await sendCommand({cmd:"set_exposure_compensation",value:...}); }` (11392-11397). |
| C3-I5 | weaken to usually | Toggle-as-pills holds for every UI.conf On/Off (WCP:9966-10171, and the favourites copies 6851-7173). Counter-example: Standby USB power-off is a `<select>` that sends a JSON boolean, `enabled: event.target.value === "true"` (11527). Continuous values use `input.slider type="range"` (2583, 3436, 3448), not pills. |
| C3-I6 | holds | Spot-checked ids `settings*Options/Select/Card/Value`, `*Button`; functions `apply*Selection`, `request*`, `fetch*`, `render*`. No counter-example found. |
| C3-I7 | holds | 2 `//` lines (WCP:8474-8475), 0 `/*`, 0 `<!--` in WCP. WS comments are 1-2 lines of safety reason (WS:161, 263-264, 365). |
| C3-I8 | holds as usually | Not re-measured beyond the reader's count; no counter-example looked for beyond tokens vs literals. |
| C3-N1 | holds | No storage API. Local-only fields on `state` are editing state (`configDirty`, `customIntervalEditing`), not settings. |
| C3-N2 | holds | Busy refusals in Core (App:9095-9107, route App:7514-7520); page disables only. |
| C3-N3 | holds | Exactly 8 `window.confirm` (WCP:10307 discard config edits, 10385, 10434 delete media, 10672 delete preset, 11266 format, 11278 eject, 11325 restart, 11337 shutdown). `apply_preset`, `mount_media`, `calibrate_gyro` do not confirm. |
| C3-N4 | holds as usually; criterion corrected | "Lasting or system effect" is not the line: routine System-panel settings toast on success (`"Fan mode updated."` 11094, `"UI orientation updated."` 10805, `"Camera standby updated."` 11520, battery 11203-11256). Observed line: select-, field- and button-driven settings in System/Power/Info cards toast on success; pill grids and main-page controls never do. |
| C3-N5 | weaken to usually | Nav order mirrors `defaultSidebarOrder` (ui-upstream `qml/SettingsPage.qml:827-837`) except that the WebUI puts its own `config` panel (WCP:2773, 3840) where the touch UI has `Wi-Fi`. WebUI-only features exist where a browser adds value: config text editor (3845), media download (App:7197, 7318), preset download/import (App:7367, 7392), MJPEG preview (App:7109). Native-only Wi-Fi gets a read-only note (WCP:7265). |
| C3-N6 | holds as usually | No counter-example checked beyond the reader's. |
| C3-N7 | holds as once | Rough edges confirmed: `arrangeSettingsPanels` moves cards (WCP:6119-6128), power panel titled Media, three favourites lists, `renderSnapshot` 9327-10206, favourite toggles have duplicate handlers (see M5). |

### Missed rules

| Id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| M1 | idiom | Build DOM nodes with `document.createElement` + `textContent`/`setText`; use `innerHTML` only to clear a container (`= ""`), never to inject markup. | always (all 10 `innerHTML` uses are `= ""`) | WCP:6201, 6237, 6753, 7323, 9151 `container.innerHTML = "";`; `setText` WCP:6172 |
| M2 | idiom | Library fetches use `fetch(url, { cache: "no-store" })`, read `payload = await response.json()`, and throw `new Error(payload.error || "Could not ...")` when `!payload.ok`. | always (5 of 5 GETs) | WCP:10224 `/api/state`, 10252 `/api/presets`, 10313 `/api/config`, 10367 `/api/media` |
| M3 | idiom | No console logging in the page except `console.warn` for WebGL shader failures; errors go to the toast. | always (2 `console.` uses) | WCP:7900, 8077 |
| M4 | idiom | Each route branch writes its own `WebServer::Response` with `contentType = "application/json; charset=utf-8"` and an `okReply(-1, ...)`/`errorReply(-1, ...)` body; there is no response helper. | always | App:7440-7476, 7503-7520, 7637-7649 (51 `WebServer::Response response;` in App:7080-7650) |
| M5 | structure | A control that is also a favourite has two handlers: one in `renderSnapshot` via `sendCommand`, one in `renderFavoriteControls` via `dispatchFavoriteCommand`; add both. | usually (every toggle favourite) | SMPTE WCP:6915 and 10111; zebra 6882 and 10087; `dispatchFavoriteCommand` 7307-7313 |
| M6 | structure | Reading or writing files in the media, preset or config libraries is a dedicated `/api/...` route; camera and system state changes are commands. | always | App:7175, 7440, 7477, 7503, 7575 routes; App:10230 `apply_preset` command |

## Final rules

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C3-S1 | structure | Put all WebUI HTML, CSS and JS in the single raw string of `webControlPageHtml()` in `src/web/WebControlPage.cpp`, ordered style, body, script; no separate .js/.css/.html files, no external script or style links. | always (only one such place) | WCP:5-7 `R"APERTAR(`; WCP:15, 2420, 4038, 11611; App:7102-7107 | A new `src/web/foo.js`, a `<script src>`, a CDN link, a second page string |
| C3-S2 | structure | Keep the main page to the camera-critical cards; every other control is a `settings-card` in one of the 9 `settings-panel[data-panel]` sections, listed in the nav and in `settingsPanelMeta`. | always | WCP:2456-2700 main grid; 2745-2777 nav; 4164-4201 `settingsPanelMeta` | A new main-page card for a non-critical feature; a tenth panel without nav and meta entries; a modal settings dialog |
| C3-S3 | structure | Send camera and system actions through `POST /api/command` with the socket's flat command via `sendCommand`; use dedicated routes only for file transfer, library listings/writes (media, presets, config) and the preview stream or icons. | usually (exceptions: raw `fetch` for `user_activity` WCP:11509; library writes are routes, see M6) | App:7637-7642; App:7083-7089; WCP:9109-9145 | A `/api/set_iso` route; a REST resource per setting; a second fetch wrapper |
| C3-S4 | structure | Add a route as one more `if (request.method == "X" && request.path == "/api/...")` branch in `handleWebRequest` before `/api/command`; query params via `queryParameterValue`; reply `okReply`/`errorReply(-1, ...)` with 204/400/404/405/500/503; delegating the work to a helper is usual, not required. | always (branch shape); usually (helper) | App:7154-7159; App:7440-7475; App:7503-7574 inline; App:7644-7649 | A router table, regex routing, a handler class per route, routes after the `/api/command` branch |
| C3-S5 | structure | Leave security to `WebServer`: the same-origin check and the 1 MiB cap are server-wide; routes add only busy-state refusals and path guards. | always (only one server) | WS:23, 156-171, 360-373; README.md:130; no header work in App | CORS headers, tokens or auth in a route; raising the size cap for one route |
| C3-S6 | structure | Declare pill option lists as top-level `const <x>Options` label arrays in WCP:4040-4090; fixed `<select>` choices may be literal `<option>` HTML; accept that lists shared with Core and the touch UI are duplicated by hand. | usually (exceptions: literal `<option>` lists WCP:2881-2907, 3468-3471; in-function lists 5584, 9672) | WCP:4040-4090; WCP:4091 vs App:727 vs ui `qml/SettingsPage.qml:838` | Fetching option lists from a new endpoint; a shared generated JSON; centralising the duplicated lists unasked |
| C3-S7 | structure | Serve static assets only as PNG icons from `src/web/icons` via `GET /icons/<name>`, referenced by `<img ... src="/icons/x.png" alt="">`, reusing the touch UI's icon names. | always | App:7124-7151; App:2420-2440; WCP:2427, 2746-2778; 45/45 icons are PNG, 44 share names with ui `qml/icons/` | Inline SVG, icon fonts, `data:` images, new asset routes |
| C3-S8 (M5) | structure | A control that is also a favourite has two handlers: in `renderSnapshot` via `sendCommand` and in `renderFavoriteControls` via `dispatchFavoriteCommand`; add both. | usually | WCP:6915 and 10111; 6882 and 10087; 7307-7313 | A new favourite toggle that only works on its own panel, or a refactor that merges the two paths unasked |
| C3-S9 (M6) | structure | Reading or writing files in the media, preset or config libraries is a dedicated `/api/...` route; camera and system state changes are commands. | always | App:7175, 7440, 7477, 7503, 7575; App:10230 `apply_preset` | A `delete_media` socket command used by the page; a `/api/...` route that changes camera settings |
| C3-I1 | idiom | Write plain flat JS: named functions at one indent level, `const`/`let`, arrow callbacks, `async/await`, `fetch`; no framework, module, class, bundler, `var`, `.then` chains or browser storage. | always | WCP:4038-11611 grep: no `class`/`import`/`export`/`var`/`.then(`/`localStorage`/`WebSocket` | A framework, an ES module, a class, `localStorage` |
| C3-I2 | idiom | Keep all client state in the single global `state` object (snapshot, `*InFlight`, `*Timer`); render only from `state.snapshot`. | always (module level; one closure-local `let`, WCP:11503) | WCP:4204-4266; 9334; 7804-7813 | New module-level `let` variables; state kept in DOM attributes or a second store |
| C3-I3 | idiom | Follow poll-render-command: `fetchState` every 1 s -> `renderSnapshot`; controls call `sendCommand`, which patches via `applyCommandSnapshotPatch`, rolls back on `ok:false`, schedules a refresh; add a patch `case` for a new `set_*` command. | always (loop); usually (patch case; missing for 4 commands WCP:11392, 11396, 11519, 11527) | WCP:11609; 9109-9145; 8678-9108 | Push channels, per-control polling, DOM-only optimistic updates, no rollback |
| C3-I4 | idiom | Write each handler as `async` with `try { await sendCommand({ cmd: "...", ... }) } catch (error) { showToast(error.message, true) }`, showing Core's error text verbatim. | usually (exceptions: `user_activity` fire-and-forget WCP:11513) | WCP:9876-9882; 10791-10799; 11088-11098; 86 `showToast(error.message, true)` | Swallowed errors, `alert()`, rewritten error text, `console.error` |
| C3-I5 | idiom | Build choice controls as pill grids with `buildOptionButtons`; On/Off toggles as a two-pill grid over `toggleOptions` sending `enabled` as `"true"`/`"false"`; selects via `ensureSelectOptions`/`ensureSelectEntries`; continuous values via `input.slider`. | usually (exception: standby USB select sends a boolean, WCP:11527) | WCP:9147-9167; 4066; 10109-10115; sliders 2583, 3436, 3448; WCP:6191, 6221 | Checkboxes or switch widgets, custom dropdown components, toggles sending JSON booleans |
| C3-I6 | idiom | Name ids camelCase with region prefix and kind suffix (`settings<Thing>Options/Select/Value/Button/Card/Note/Field`), CSS classes kebab-case with `active`/`disabled`/`hidden` states, functions `apply<X>Selection`/`request<Action>`/`fetch<X>`/`render<X>`. | always | WCP:3268; 3622, 3628, 3646; 11088, 11262, 10207 | `snake_case` ids, BEM classes, `is-active`, `handleXClick` names |
| C3-I7 | idiom | Do not add comments, banners or JSDoc to the page; C++ comments in the web server are one or two lines giving a safety reason. | always | WCP:8474-8475 only; 0 `/*`, 0 `<!--`; WS:161, 263-264, 365 | Section banners, JSDoc blocks, HTML comments |
| C3-I8 | idiom | Style with the dark zinc vocabulary: `:root` tokens where they exist, literal zinc hex/rgba otherwise, white for selected, red tint for danger, large radii, 50 px controls, 20 px card padding; unavailable choices `disabled`, non-applicable controls `.hidden`. | usually | WCP:15-43; 783-788; 790-803, 1700-1706, 1603-1608 | A light theme, new colour system, removing unavailable choices instead of disabling |
| C3-I9 (M1) | idiom | Build DOM with `createElement` + `textContent`/`setText`; `innerHTML` only to clear (`= ""`). | always (10/10 uses) | WCP:6201, 6237, 6753, 7323, 9151; `setText` 6172 | Template-literal HTML assigned to `innerHTML` |
| C3-I10 (M2) | idiom | Library fetches use `{ cache: "no-store" }`, parse `payload`, and throw `new Error(payload.error || "Could not ...")` when `!payload.ok`. | always (5/5) | WCP:10224, 10252, 10313, 10367 | Unchecked `response.json()`, cached GETs, status-code-only checks |
| C3-I11 (M3) | idiom | No console logging in the page except `console.warn` for WebGL shader failures. | always (2 uses) | WCP:7900, 8077 | `console.log` debug traces |
| C3-I12 (M4) | idiom | Each route branch builds its own `WebServer::Response` with `contentType = "application/json; charset=utf-8"`; no reply helper. | always | App:7440-7476, 7503-7520, 7637-7649; 51 occurrences | A new `jsonResponse()` helper refactoring all routes unasked |
| C3-N1 | intent | Core is the only source of truth: the page stores no settings and shows values from `/api/state`. | always | README.md:271; WCP:9130-9131; no storage API | Browser-side preferences, cached settings that survive reload |
| C3-N2 | intent | Enforce during-take and busy-state rules in Core with a remedy sentence; the page only disables matching controls and shows Core's refusal. | always | App:9095-9107; App:7514-7520; WCP:9510, 9513, 9529, 9584 | Page-only checks; Core accepting a change during a take that the page merely hides |
| C3-N3 | intent | Confirm only destructive or system-level actions with `window.confirm` phrased as a question naming the effect; routine settings and preset apply never ask. | always (8 confirms) | WCP:10307, 10385, 10434, 10672, 11266, 11278, 11325, 11337 | Custom modal confirms; confirms on routine settings; destructive action without a confirm |
| C3-N4 | intent | Feedback through the single toast: an error toast for every failure; a success toast for select/field/button settings in System/Power/Info cards and system actions; no toast for pill grids or main-page controls. | usually | WCP:7804-7813; 10805, 11094, 11520, 11283, 11331; pill handlers 9876-9882, 10109-10115 | Toasts on every pill tap; inline success banners; a second notification area |
| C3-N5 | intent | Mirror the touch UI's concepts, order and wording; WebUI-only features are allowed where a browser adds value (config editor, downloads/imports, MJPEG preview); native-only features (Wi-Fi) get a short read-only note. | usually (WebUI `config` panel takes the touch UI's `Wi-Fi` slot) | WCP:4123-4163; ui `qml/SettingsPage.qml:827-837` vs WCP:2745-2777; WCP:7265; 3845 | WebUI wording or order that diverges from the touch UI; a half-working Wi-Fi control in the browser |
| C3-N6 | intent | Keep UI text short and factual: one-sentence card copy ending with a period; notes state the operator or post-production consequence; errors are full sentences with the remedy. | usually | WCP:3153, 3606, 3632; 9515; App:9107 | Marketing copy, multi-paragraph help, error codes without a remedy |
| C3-N7 | intent | Do not fix the page's structural rough edges unasked (runtime card moves, power panel titled Media, triple favourites lists, duplicate favourite handlers, giant `renderSnapshot`, HTML panel order differing from nav order); match them. | once (each a single precedent) | WCP:6119-6128; 2761-2764, 4186-4188; 9327-10206; 2796 vs 3075 | A contribution that splits `renderSnapshot`, renames panels or reorganises the HTML as a side effect |
