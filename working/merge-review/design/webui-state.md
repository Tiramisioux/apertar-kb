# The WebUI: one state, one poll loop, its own parts: design

Read: Apertar-Core `/home/user/wt/core-work` at `7dc6f7a` (port `01f170c` + 2 fixes), Apertar-UI `/home/user/wt/ui-work` at `ac1fc28`; measuring stick `/home/user/wt/core-upstream` `upstream-1.6.0` `35dbe67`. `P:` = `src/web/WebControlPage.cpp@7dc6f7a`, `U:` = the same file `@upstream-1.6.0`, `App:` = `src/ApertarCoreApp.cpp@7dc6f7a`, `CC:` = `src/camera/CameraController.cpp@7dc6f7a`.

## In short

1. Today the page has five stores where upstream has one: `state`, `frameBufferBar`, `controlsState` (plus 5 module-level sets and lets), `bootConfig`, `clipUi`/`settingsSearch`, and a nested `state.pb`.
2. It has two network loops for camera state: `fetchState` at 1 Hz and `pollFrameBufferBar` at 4 Hz, and the second one edits the REC pill outside `renderSnapshot`, with 1000 ms freshness windows deciding which writer wins.
3. It has four doors to `/api/command`: `sendCommand`, `controlsCall`, `ladderRequest`, `clipRawCommand`.
4. The Clip Browser and Viewer bring a second widget set (round buttons, a pop-up menu, a chip, a modal dialog, inline SVG, browser history, hold-to-repeat) and the Controls panel white dropdowns.
5. Target: one `state` with flat fields; one loop that renders (`fetchState`), plus the lock-free `/api/buffer` poll kept as documented new ground that only merges into `state.snapshot` and redraws the pill through one function; one door (`sendCommand`, raw `fetch` only for background traffic, as upstream's `user_activity`); upstream's parts and names.
6. Every feature stays. Nothing in Core, in any reply, in any file on the camera changes. Only `src/web/WebControlPage.cpp`.
7. 24 commits, all in Apertar-Core, all page-only. About 1 100 lines removed, 450 added, plus about 1 400 lines of pure renames in 5 mechanical commits.
8. Four owner decisions: phone Back in the Clip Browser, hold-to-repeat, where Remote controls lives, and whether the 1 500-line rename is worth it.

## How it works in the port today

Thread and lock: the page is single-threaded browser JS, so "thread" below is the browser timer or event that runs the code. On the Core side, the web server runs one detached thread per request (`src/web/WebServer.cpp:279-290`), so `/api/buffer` answers while `/api/state` waits.

### Recording pill and write buffer

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Buffer gauge (`used`, `capacity`, `active`, `ram`) | Raw writer queue (`CC:12520-12550` reads it) | `CameraController::frameBufferStatus()` `CC:12525` | Relaxed atomics; mode read under `try_lock` of `mutex_`, last answer reused while the command path holds it | none | `system.buffer_*` in `/api/state`; `/api/buffer`; socket event `buffer` `App:10845` (touch UI) |
| Safety stop, stop percent, flush-discarded count | `bufferbudget::safetyStopState()` | `bufferSettingMembers()` `App:252-269` | Atomics | none | Same three places |
| Pre-roll active, fps, auto | `storagepreroll::*` | `bufferSettingMembers()` `App:260-264` | Atomics | `[storage]` of `apertar-hardware.conf` (preroll theme) | Same three places |
| `GET /api/state` | `buildWebStateJson()` `App:9302`, route `App:8432-8437` | `fetchState` `P:16377` | Takes CC `mutex_` (`camera_.state()` `CC:12571-12574`); blocks while a stopped take drains | none | Whole page via `renderSnapshot` `P:15214` |
| `GET /api/buffer` | Route `App:8422-8430`: `bufferMembers(...)` + `recording` = gauge active and not safety stop | `pollFrameBufferBar` `P:16491-16539` | Lock-free (comment `App:8422`) | none | REC pill only |
| `frameBufferBar` (14 fields: `fill fillAtMs timer inFlight recording active safetyStop stopPercent stopSeen discardedSeen preroll prerollFps prerollAtMs prerollUntilMs`) | `pollFrameBufferBar` `P:16491`, `updateFrameBufferBar` `P:16547`, `noteBufferSafetyStop` `P:16458`, `notePrerollRequested` `P:16435` | `applyCommandSnapshotPatch` record_start `P:14381`; `renderSnapshot` `P:15389`, `P:15757-15759`; fps pills `P:15917`; `toggleRecord` `P:19272` | Second timer: `window.setInterval(pollFrameBufferBar, 250)` at `P:16432` and `P:16587`; stopped in `.finally` `P:16533-16538` | none | REC pill |
| `state.snapshot.storage_preroll_*` | `fetchState` -> `renderSnapshot`, and directly by the 4 Hz poll `P:16505-16512` | `renderSnapshot` `P:15391`, `markPrerollFps` `P:8696` | Both timers write it | none | Pill text, FPS badge |
| `.status-pill` classes `recording timelapse no-media buffer-bar buffer-drain preroll`, `#statusDot` classes, `#recordingStatus` text | `renderSnapshot` `P:15392`, `P:15752-15768`; and outside it `applyPrerollPill` `P:16441-16456` (writes "PRE-ROLL", rewrites to "READY") and `applyFrameBufferPillClasses` `P:16473-16489` (removes `recording`, rewrites "REC" to "READY") | browser | Two writers; `P:16553` and `P:16561` pick the poll's value when it is under 1000 ms old | none | Main page header pill |
| Toasts "Recording stopped: the write buffer reached N %." and "Record pressed during the flush..." | `noteBufferSafetyStop` `P:16458-16471`, from both timers, de-duplicated by `stopSeen`/`discardedSeen` | toast | both timers | none | Toast |
| Frame buffer bar option | `set_frame_buffer_bar_enabled` `P:16145`, patch `P:14241` | `updateFrameBufferBar` `P:16550` | 1 Hz | `UI.conf` `frameBufferBarEnabled` (`App:2096`, `App:7791`) | Settings pill; touch UI via bridge |

### Command doors

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| `sendCommand(payload)` `P:14416-14448` | Every upstream handler | `/api/command` -> `handleCommand` under the command lock | Patches the snapshot, rolls back on `ok:false`, throws `Error(result.error)`, schedules `/api/state` in 140 ms | - | - |
| `controlsCall(payload)` `P:16699-16705` | 16 call sites (`P:16920`, `17735`, `17966`, `18256`, `18300`, `18334-18335`, `18589`, `18627`, `18654`, `18659`, `18700`, `18729`, `18866`, `18966`) | Same route | Returns the JSON; callers test `ok` by hand; 7 sites without try/catch | - | Controls, Hardware and Config cards |
| `ladderRequest(payload)` `P:8005-8015` | `fetchModeLadder` `P:8017`, ladder save and dry runs | Same route | Throws like `sendCommand`, no patch, no refresh | - | Modes panel |
| `clipRawCommand(payload)` `P:14577-14586` | `clipPreviewThenSave` `P:14598` (`preview_clip_name`) | Same route | Same as `ladderRequest` | - | Record panel, clip-name composer |
| Listen poll | `setControlsListening` `P:18680-18720`: `setInterval(..., 300)` calling `controlsCall({cmd:"controls_last_input"})` | Controls rows | Third timer; `let controlsListenTimer/Seq` at module level `P:18672-18673`; no in-flight guard | - | Controls panel |

### Stores beside `state`

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `controlsState` (18 fields) `P:16633-16652`; `controlsChipLines` `P:16799`, `controlsSeparateTurns` `P:16882`, `controlsReplaced` `P:17253` | `loadControls` `P:18325-18360` from `get_controls` (`App:12426`) and `list_actions`; editors | 165 `controlsState.` references | Events | `apertar-hardware.conf` via `set_controls` | Controls panel, Hardware card (Config), Remote controls card |
| Remote controls card `P:4569-4580` | `renderRemoteControls` `P:18117`, buttons `buildRemoteButton` `P:18065-18112` (pointer capture, 450 ms delay, 140 ms repeat) | `test_input` | Bootstrap loop `P:20940-20949`: `loadControls` every 5 s until `controlsState.model` | - | **Main page**, under Camera settings |
| `bootConfig` (11 fields) `P:19943-19955`; `BOOT_CONFIG_*` constants `P:19956-19960` | `loadBootConfig` `P:20265` from `/api/boot-config` (`App:9165-9216`) | 66 `bootConfig.` references; listeners in `installBootConfigInteractions` `P:20624-20678`, called from `P:20923` | Events | `/boot/firmware/config.txt` (boot-config-helpers theme) | System panel, Boot Config card |
| `clipUi` (20 fields) `P:14491-14495`; `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO` `P:14457-14490` | Composer handlers; `clipPreviewThenSave` | 92 `clipUi.` references | Events, 350 ms debounce timer `clipUi.saveTimer` | `camera_settings.conf` via `set_clip_name_template` | Record panel |
| `settingsSearch` `P:10184` | Search field, MutationObserver | 17 references | Events | none | Settings search |
| `state.ladderServer` `P:6674`, filled by `applyModeLadder` `P:8034-8045` | `get_mode_ladder` (`App:14103`); pool built from the probe in `CC:11002-11034` | Ladder editor; **`imx585ClassRows` `P:8955-8968`** (main-page resolution and crop pills); fps pill sub-labels `P:15912` | Fetched from inside `renderModeLadder` `P:8395-8400`, which runs on every 1 Hz render | `mode_ladder.conf` beside `camera_settings.conf` (`CC:404-414`) | Modes panel; main-page resolution pills |
| `state.pb` (22 keys, nested) `P:6723-6727`, and `state.pb.viewer` | 70 `pb*`/`pbv*` functions `P:11685-12940` | 144 `state.pb` references | Events; `requestAnimationFrame` tick; `v.awakeTimer` keep-awake `user_activity` fetch `P:12504-12509` | none (media listing from `/api/media`) | Clip Browser and Clip Viewer overlay |

### Parts in the touch-UI look

| Part | Where | Upstream part it stands beside |
| --- | --- | --- |
| Overlay `#playbackOverlay`, `h1.pb-h1` "Clip Browser" | `P:6345-6491` | `#mediaBrowserOverlay` with `h2.section-title` `U:3979-4030` |
| Refresh / Back `.pb-top-button` with inline SVG | `P:6354-6373`, CSS `P:2061-2094` | `secondary-button` "Refresh Media", `icon-button settings-back-button` `U:3993`, `U:4008` |
| SHOW pop-up `.pb-show-button` + `.pb-menu` (cyan active) | `P:6358-6369`, CSS `P:2086-2140` | Visible `.media-filter-button` row, white active `U:3999-4004`, `U:1238-1242` |
| Sort chip `.pb-chip` | `P:6380`, CSS `P:2167` | `select.settings-select.media-sort-select` `U:4009-4012`, `U:1244-1253` |
| Remove modal `#pbRemoveScrim` `role=alertdialog` | `P:6475-6486`, `pbOpenRemoveDialog` `P:12036`, guards `P:10137`, `P:12966` | `window.confirm` `U:10434` |
| Browser history: `history.pushState` | `P:10129`, `P:12777`, `popstate` `P:20708` | none upstream |
| Viewer `.pbv-circle`, `.pbv-icon-button`, `.pbv-info-button`; 4 SVGs in markup, 1 in JS `P:11833` | `P:6400-6456`, CSS `P:2743-2775` | `.icon-button` `U:194-215`, button variants `U:1632-1706`, PNGs in `src/web/icons` |
| Hold-to-repeat: frame step `pbvRepeat` `P:12718-12729`; knob arrows `P:18090-18110` | - | none upstream |
| White dropdowns: `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select` + dark exception `.controls-pin-select`; tokens `--select-bg/--select-fg` | CSS `P:3484-3559`, `P:35-36`; class added `P:17388` | One `.settings-select` look `U:1532-1555` |
| `body.pb-open` declared twice | `P:69`, `P:1980` | `body.media-browser-open` `U:66` |

Measured in `--simulate` (`/home/user/build/work-nolc/apertar-core`, this session): `/api/state` carries the buffer and pre-roll fields under `system.*` (`system.buffer_safety_stop`, `system.storage_preroll_active`, ...); `/api/buffer` carries the same keys flat plus `recording`. The replies of `get_controls`, `list_actions`, `controls_history`, `controls_last_input`, `get_mode_ladder`, `preview_clip_name` carry no key that `mergeCameraStateFields` (`P:13784`) copies (`state`, `resolution`, `width`, `fps`, ...): confirmed by listing their top-level keys.

## How original Apertar does this kind of thing

| Precedent | Where `@upstream-1.6.0` | What it shows |
| --- | --- | --- |
| One store | `U:4204-4266` | `const state = {` with flat fields: `<x>Timer`, `<x>InFlight`, `<x>Dirty`, library payloads (`mediaLibraryPayload`, `presetLibrary`). No nested object, no second `const` store (WEB-12) |
| One loop, one renderer | `U:11609` `window.setInterval(() => fetchState(true), 1000)`; `fetchState` -> `renderSnapshot` `U:9327` | Every DOM class on the REC pill is set in `renderSnapshot` `U:9794-9802` (WEB-7, WEB-13) |
| Event toasts from a snapshot comparison | `U:9328-9333` | `if (snapshot.recording_error && snapshot.recording_error !== previousError) showToast(...)`: no "seen" flags |
| One command door | `sendCommand` `U:9109-9145`; handlers `try { await sendCommand(...) } catch (error) { showToast(error.message, true) }` | WEB-3, WEB-14 |
| A read-only command through the same door, its list in a flat field | `refreshAudioCaptureCapabilities` `U:11100-11113`: `sendCommand({cmd: "audio_capabilities"})` -> `state.audioCaptureModes`, `state.audioCapabilitiesBusy`; loaded on panel open `U:6162` | The Mode Ladder, clip preview and Controls reads take this shape |
| Raw `fetch` for background traffic only | `user_activity` `U:11509-11513` | The Listen poll and the viewer keep-awake take this shape |
| Library editor state | Config editor `U:10265-10359`: `state.configDirty`, `configFetchInFlight`, `configSaveInFlight` | Controls and Boot Config cards take this shape |
| Panel data loads with the panel | `setSettingsPanel` `U:6149-6166` | Remote controls loads here, not at page start |
| All listeners in one installer | `installInteractions` `U:11348-11610` | No second installer |
| Clip Browser parts | Markup `U:3979-4030`; state `U:4237-4243` (`mediaFetchInFlight mediaLibrary mediaLibraryPayload mediaBrowserFilter mediaBrowserSort mediaSelection`); functions `renderMediaLibrary` `U:7669`, `fetchMediaLibrary` `U:10361`, `setMediaBrowserOpen` `U:6139` | Names and parts the Clip Browser returns to |
| Destructive asks | `window.confirm` `U:10307`, `U:10385`, `U:10434`, `U:10672`, `U:11266-11337` (8 confirms) | WEB-21 |
| Buttons and selection | `.icon-button` `U:194-215`; `.primary-/.secondary-/.danger-button` `U:1632-1706`; white active `U:1238-1242`; `.media-select-control.selected` `U:1294-1330` | WEB-19: white = selected |
| Icons | PNGs from `src/web/icons` via `GET /icons/<name>`, 0 `<svg>` in the page | WEB-9 |
| Option lists | `const <x>Options` block `U:4039-4127` | Hand copies of Core's lists (WEB-8) |
| `.hidden` class | `U:790-803` | No `hidden` attribute |

No upstream precedent: a second network poll, browser history, a modal dialog, hold-to-repeat, a mutation observer, a client-side playback engine. Those are new ground (section below).

## The target

Where each value lives after the plan. Core is untouched: who owns each value in Core and which command sets it stay as today.

| Value | Owner and setter (unchanged) | Before (page) | After (page) |
| --- | --- | --- | --- |
| Buffer fill, safety stop, stop percent, flush-discarded, pre-roll active/fps | Core atomics; `record_start`, `record_stop`, `set_buffer_mode` | `frameBufferBar.fill/safetyStop/stopPercent/discardedSeen/preroll/prerollFps`, plus `state.snapshot.*` written by two timers | `state.snapshot.buffer_fill`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `storage_preroll_active`, `storage_preroll_fps`: merged from `/api/state` by `renderSnapshot` and from `/api/buffer` by `applyBufferSnapshotPatch` |
| "Frames still queued" from `/api/buffer` | Core gauge | `frameBufferBar.recording` | `state.snapshot.buffer_recording` (page-side name, never over `snapshot.recording`) |
| Buffer poll bookkeeping | page | `frameBufferBar.timer/inFlight/prerollUntilMs/fillAtMs/prerollAtMs/stopSeen/active` | `state.bufferPollTimer`, `state.bufferPollInFlight`, `state.prerollPollUntilMs`; the other four are deleted |
| REC pill classes and text | page | `renderSnapshot` + `applyPrerollPill` + `applyFrameBufferPillClasses` | `renderRecordingStatus(snapshot)`, called by `renderSnapshot` and by `fetchBufferState` |
| Buffer toasts | page | `noteBufferSafetyStop` with seen-flags | Previous-vs-new comparison in `renderRecordingStatus`'s caller, like `recording_error` |
| Controls model, edits, catalog, history, listen | Core `get_controls`/`set_controls`, `apertar-hardware.conf` | `controlsState.*`, 3 module sets/maps, 2 module lets | `state.controlsModel`, `controlsRevision`, `controlsPeripherals`, `controlsCatalog`, `controlsEdits`, `controlsButtons`, `controlsRemoved`, `controlsAdded`, `hardwareEdits`, `controlsBuses`, `controlsScans`, `controlsDpiLines`, `controlsGpioChips`, `controlsApply`, `controlsHistory`, `controlsLoadInFlight`, `controlsSaveInFlight`, `controlsListening`, `controlsListenTimer`, `controlsListenSeq`, `controlsListenInFlight`, `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced` |
| Boot Config card | Core `/api/boot-config` (boot-config-helpers theme) | `bootConfig.*`; `installBootConfigInteractions` | `state.bootConfigPayload`, `bootConfigForm`, `bootConfigFetchInFlight`, `bootConfigSaveInFlight`, `bootConfigRebootWaiting`, `bootConfigSavedPendingReboot`, `bootConfigReview` (+ editor fields if boot-config-helpers keeps Edit file); listeners in `installInteractions` |
| Clip-name composer | Core `set_clip_name_template`, `camera_settings.conf` | `clipUi.*`, `CLIP_*` | `state.clipName*` fields; `clipNamePresets`, `clipNameTokenGroups`, `clipNameTokenInfo` in the option-list block |
| Settings search | page | `settingsSearch.*` | `state.settingsSearchActive`, `settingsSearchObserver`, `settingsSearchTimer`, `settingsSearchApplying` |
| Clip Browser | Core `/api/media*` routes | `state.pb.*` (22 keys) | Upstream fields `state.mediaLibraryPayload`, `mediaLibrary`, `mediaBrowserFilter`, `mediaBrowserSort`, `mediaSelection`, `mediaFetchInFlight`, plus flat `mediaFetchQueued`, `mediaSelecting`, `mediaThumbCache`, `mediaThumbQueue`, `mediaThumbsInFlight`, `mediaThumbObserver`, `mediaHold`, `mediaSnapshotHold`, `mediaError`, `mediaRemoving`, `mediaLastOpenedKey`, `mediaBrowserPage`, `previewPausedForPlayback` (declared) |
| Clip Viewer | page | `state.pb.viewer` | `state.clipViewer` (one object per open clip; new ground, see below) |
| IMX585 resolution pills | Core class tables `src/camera/Imx585Modes.hpp`; set by `set_resolution` | `state.ladderServer.pool`, else `imx585ClassModes` | `imx585ClassModes` only (hand copy, WEB-8); `state.ladderServer` serves the Mode Ladder card and fps sub-labels only |
| Command doors | Core `handleCommand` | `sendCommand`, `controlsCall`, `ladderRequest`, `clipRawCommand` | `sendCommand` (its error carries `error.result`); raw `fetch` for `controls_last_input` (Listen) and `user_activity` (viewer keep-awake) only |
| Parts | - | `.pb-*`, `.pbv-*`, SVG, modal, history, hold-to-repeat, white selects | `.media-browser-*`, `.clip-viewer-*` for layout only; buttons from `.icon-button`/`.primary-/.secondary-/.danger-button`; `/icons/*.png`; `window.confirm`; one `.settings-select` |
| Remote controls | Core `test_input` | Card on the main page, loaded at start, 5 s retry | `settings-card` in the Controls panel, loaded by `setSettingsPanel("controls")` |

What reaches the touch UI does not change: it reads the socket (`get_state`, events `buffer`, `settings`), not the page. No reply field, no file key, no command changes, so requirement 4 (files on existing cameras) has nothing to take over.

## Commit plan

All commits: repo Apertar-Core, file `src/web/WebControlPage.cpp` only, subject prefix `web:`. Order: the camera-critical pill first, then the command doors, then the stores, then the Clip Browser parts (deletions before renames, so the renames touch fewer lines), then the small parts.

**Standard check here (every commit):**
1. `/home/user/build/bin/check_core.sh /home/user/wt/core-work work both tests`: both builds and the host tests PASS.
2. `/home/user/build/bin/smoke_core.sh /home/user/build/work-nolc/apertar-core 18741 after.txt` and `diff before.txt after.txt`: empty (the page is the only change, so reply shapes must be identical).
3. Extract the page script from `curl -s http://127.0.0.1:18741/` (text between `<script>` and `</script>`) and run `node --check` on it.
4. Node Playwright (`/opt/node22/lib/node_modules/playwright`) with `google-chrome` headless against `--simulate`: load `/`, open every settings panel and the Clip Browser, fail on any `pageerror` or `unhandledrejection`, take a screenshot.
5. The grep named in the commit returns 0.

**What a Pi adds in general:** the buffer and pre-roll paths need a real raw take (`--simulate` reports `buffer_mode: "none"`). The rest is page logic that `--simulate` drives fully.

### 1. web: the buffer poll keeps its fields in state

- Files and functions: `state` literal; `startFrameBufferTimer`, `notePrerollRequested`, `prerollPollWanted`, `applyPrerollPill`, `noteBufferSafetyStop`, `applyFrameBufferPillClasses`, `pollFrameBufferBar`, `stopFrameBufferPolling`, `updateFrameBufferBar`, and the 5 outside readers (`P:14381`, `15389`, `15757-15759`, `15917`, `19272`).
- Moves: the 14 fields of `frameBufferBar` to `state.buffer*`/`state.preroll*` with the same meaning (`state.bufferFill`, `state.bufferPollTimer`, ...). Deletes: `const frameBufferBar` `P:16419-16421`. Adds: the fields to the `state` literal. Pure move, no behaviour change.
- Lines: -3 +14, about 55 lines edited in place.
- Check here: standard; `grep -c frameBufferBar` = 0. Playwright with `page.route("/api/buffer")` returning a canned reply (`buffer_fill 0.5`, `recording true`) while `/api/state` is routed to a snapshot with `recording: true` and `ui.frame_buffer_bar_enabled: true`, `system.buffer_mode: "ram"`: the pill has `buffer-bar` and `--buffer-fill: 50.0%`.
- Pi: nothing new (same behaviour).
- Depends on: none.

### 2. web: the recording pill is drawn in one function, renderRecordingStatus

- Functions: `renderSnapshot`. Moves: the `#recordingStatus` text line `P:15388-15392` and the pill/dot class block `P:15752-15768` (with its `updateFrameBufferBar` call) into `function renderRecordingStatus(snapshot)`, next to `renderSnapshot`. `renderSnapshot` calls it at the old place. Pure extraction.
- Why this split is allowed: WEB-24 says do not split `renderSnapshot` unasked. Here the pill has a second writer that cannot call all of `renderSnapshot` (880 lines, 4 times a second); the only way to keep one writer is to give the pill its own function. The rest of `renderSnapshot` stays whole.
- Lines: -30 +36.
- Check here: standard; screenshot of the pill READY / NO MEDIA in `--simulate` identical to before (pixel diff).
- Pi: nothing new.
- Depends on: 1.

### 3. web: the buffer poll merges its reply into the snapshot and redraws the pill

- Functions: `pollFrameBufferBar` renamed `fetchBufferState` (async, `try/catch/finally`, `state.bufferPollInFlight`, `AbortController` 800 ms kept); new `applyBufferSnapshotPatch(payload)` (about 10 lines: copy the flat keys the reply shares with `/api/state system.*` through the existing `mergeCameraStateFields`, after moving `payload.recording` to `buffer_recording`); then `renderRecordingStatus(state.snapshot)` and `showPrerollFpsText`.
- Deletes: `applyPrerollPill` `P:16441-16456`, `applyFrameBufferPillClasses` `P:16473-16489`, the READY/PRE-ROLL label rewrites, the direct `state.snapshot.storage_preroll_*` writes `P:16505-16512`, the 1000 ms freshness windows `P:16553`, `P:16561`, `P:16575`, and the derived fields `bufferFill`, `bufferRecording`, `bufferSafetyStop`, `bufferStopPercent`, `prerollActive`, `prerollFps`, `bufferFillAtMs`, `prerollAtMs`, `bufferBarActive` from commit 1.
- `renderRecordingStatus` reads only `snapshot`: pill `recording` = `isRecording && !snapshot.buffer_safety_stop`; `buffer-drain` = bar active and `buffer_safety_stop` and `buffer_fill > 0`; `preroll` = `storage_preroll_active && !recording`. The 5 outside readers read `state.snapshot.buffer_safety_stop` and `storage_preroll_active`.
- Why `buffer_recording`: `/api/buffer` reports `recording:false` during a safety stop (`App:8428`) while the take still drains; writing it over `snapshot.recording` would enable controls Core still refuses.
- Lines: -150 +55.
- Check here: standard; `grep -c 'applyPrerollPill\|applyFrameBufferPillClasses\|fillAtMs\|prerollAtMs'` = 0. Playwright with routed replies, four scenes: (a) `/api/state` recording, `/api/buffer` fill 0.4: pill REC red, bar 40 %; (b) `/api/buffer` `buffer_safety_stop: true`, fill 0.3, `/api/state` held (route never answers): pill READY green with `buffer-drain`, record button enabled; (c) `storage_preroll_active: true`, not recording: PRE-ROLL blue, FPS badge shows `storage_preroll_fps`; (d) all false: READY.
- Pi (CM5 + CFexpress, then a Pi 4 + SD card, the slow case): RAM buffer mode, cDNG 16-bit 4K at the highest fps, frame buffer bar on in Settings > Record. Record until the safety stop. Look for: bar fills smoothly (4 Hz), at the stop the pill turns READY green with the drain bar before `/api/state` answers again, the toast appears once. Then press REC during the flush: the flush-discard toast appears once and a new take starts. Pre-roll: press the pre-roll button: PRE-ROLL pill within half a second.
- Depends on: 2. Preroll theme: if it renames `storage_preroll_*` fields, rebase; the pill reads them in one place after this commit.

### 4. web: buffer toasts and the buffer poll timer follow the snapshot

- Functions: delete `noteBufferSafetyStop` and the seen flags (`stopSeen`, `discardedSeen`); add a 6-line comparison where the previous snapshot is known (top of `renderSnapshot`, and in `applyBufferSnapshotPatch` before the merge), shaped like `U:9331-9333`: `if (next.buffer_safety_stop && !previous.buffer_safety_stop) showToast(...)`; `if (next.buffer_flush_discarded > 0 && next.buffer_flush_discarded !== previous.buffer_flush_discarded) showToast(...)`. Replace `startFrameBufferTimer`, `stopFrameBufferPolling`, `prerollPollWanted` and the three start/stop sites with one `updateBufferPolling(snapshot)`: poll while (queue mode and (recording or safety stop or fill > 0)) or pre-roll active or `performance.now() < state.prerollPollUntilMs`; `notePrerollRequested` sets `state.prerollPollUntilMs` and calls it.
- Lines: -60 +35.
- Check here: standard; Playwright scene (b) of commit 3 repeated for 3 s: exactly one toast; scene with `buffer_flush_discarded` 0 -> 12: one toast; after all false, `state.bufferPollTimer` = 0 within 250 ms (read via `page.evaluate`).
- Pi: the commit 3 steps; also leave the page open idle 5 min and check in the browser network tab that `/api/buffer` requests stop.
- Depends on: 3.

### 5. web: Controls and Hardware commands go through sendCommand

- Functions: `sendCommand` (2 lines: `const error = new Error(result.error || "Command failed."); error.result = result; throw error;`, the same shape the port's `/api/config` save uses); `loadControls`, `saveControls`, `saveHardware`, `undoControls`, `loadControlsHistory`, `loadConfigVersion`, `checkConfigFile`, the Scan handler, the three Test handlers.
- Each user action: `try { const result = await sendCommand(...) } catch (error) { showControlsMessage(error.message, error.result && error.result.issues, false) } finally { <flag> = false }`. Saves read `error.result.issues` / `error.result.code`. Scan resets "Scanning..." in `finally`. Undo sets the save flag.
- Listen poll stays a raw `fetch` (it is background traffic like `user_activity`; through `sendCommand` it would schedule an `/api/state` refresh and push `deferFetchUntilMs` every 300 ms), now inside `try/catch` with an in-flight guard.
- Deletes: `controlsCall` `P:16699-16705`.
- Lines: -45 +80 (try/catch at 15 sites).
- Check here: standard; `grep -c controlsCall` = 0. Playwright: open Controls, `page.route("/api/command")` to fail `scan_i2c` once: Scan button usable again, toast shown, no unhandled rejection; Save with a stale revision shows Core's "The file changed since you loaded it..." (reproduced above in `--simulate` with `set_controls base=x`).
- Pi: Controls > Listen, press a GPIO button: its row lights up.
- Depends on: none. Command-plane theme: if replies gain machine codes, `error.result.code` already carries them.

### 6. web: the Mode Ladder and the clip-name preview go through sendCommand

- Functions: `fetchModeLadder`, the ladder save and dry-run callers, `clipPreviewThenSave`. Deletes: `ladderRequest` `P:8005-8015`, `clipRawCommand` `P:14577-14586`. Precedent: `audio_capabilities` through `sendCommand` `U:11109`.
- Cost accepted: each call renders once from the unchanged snapshot and schedules one `/api/state` 140 ms later (the composer debounces at 350 ms; the ladder fetches on panel open and on `ladder_active` change).
- Lines: -24 +3.
- Check here: standard; `grep -c 'ladderRequest\|clipRawCommand'` = 0; Playwright: Modes panel lists the ladder; Record panel composer shows the example name after a drag.
- Pi: nothing new.
- Depends on: 5 (the `error.result` line).

### 7. web: the Controls page keeps its state in state

- Moves: the 18 fields of `controlsState` to flat `state.controls*` fields (names in the target table; `settingEdits` -> `hardwareEdits`, `loading`/`saving` -> `controlsLoadInFlight`/`controlsSaveInFlight`). Deletes: `const controlsState`. Label tables (`controlsGroups`, `controlsNewTitles`, `controlsKindNames`, `controlsStateNames`, `controlsOutputFunctions`, ...) move to the option-list block after `sleepModeOptions` (WEB-8). Mechanical, run as one `sed` map listed in the commit body.
- Lines: -22 +20 declarations; about 165 lines edited in place; about 40 lines moved.
- Check here: standard; `grep -c controlsState` = 0; Playwright: Controls panel renders the same rows as before (DOM text diff of `#controlsRows` before/after).
- Pi: nothing new.
- Depends on: 5.

### 8. web: the Controls page's sets, maps and Listen timer live in state

- Moves: `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced` (`P:16799`, `16882`, `17253`), `let controlsListenTimer`, `let controlsListenSeq` (`P:18672-18673`) to `state`. Deletes: the 5 module-level declarations.
- Lines: -5 +5; about 25 lines edited.
- Check here: standard; `grep -nE '^    let ' P` lists no Controls name.
- Pi: nothing.
- Depends on: 7.

### 9. web: the Boot Config card keeps its state in state and its listeners in installInteractions

- Moves: `bootConfig.*` to `state.bootConfig*` (target table); `BOOT_CONFIG_TOGGLES`, `BOOT_CONFIG_MANAGED` to camelCase in the option-list block; the body of `installBootConfigInteractions` into `installInteractions` next to `restartSystemButton`. Deletes: `const bootConfig`, `installBootConfigInteractions` and its call `P:20923`.
- Lines: -16 +14 declarations; about 70 lines edited; about 50 lines moved.
- Check here: standard; `grep -c 'bootConfig\.\|installBootConfigInteractions'` = 0; Playwright: System panel shows the Boot Config card filled from `/api/boot-config` (`--simulate` answers it).
- Pi: nothing new (no change in what is written).
- Depends on: boot-config-helpers theme first (it moves the route and may delete Edit file, which removes `text`, `previewState`, `editorMarks`, `editorTimer`). Move only the fields that survive.

### 10. web: the clip-name composer and settings search keep their state in state

- Moves: `clipUi.*` to `state.clipName*` (e.g. `clipNameItems`, `clipNameSavedTemplate`, `clipNameDirty`, `clipNameSaveTimer`, `clipNameSeq`, `clipNameDrag*`, `clipNameStatusText`, ...), one-letter fields get words (`src` -> `clipNameDragSource`, `v` -> `value` in the token table); `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO`, `CLIP_DEFAULT_TEMPLATE` -> camelCase in the option-list block; `settingsSearch.*` -> `state.settingsSearch*`. Deletes: `const clipUi`, `const settingsSearch`.
- Lines: -8 +24 declarations; about 110 lines edited.
- Check here: standard; `grep -cE 'clipUi|settingsSearch\.|CLIP_'` = 0; Playwright: type "iso" in settings search, the ISO unit stays; composer saves `{format}_{date}_{clip}`.
- Pi: nothing.
- Depends on: 6.

### 11. web: Remove in the Clip Browser asks with window.confirm

- Functions: `pbOpenRemoveDialog` becomes `if (!window.confirm("Remove " + n + " clip(s)? This cannot be undone.")) return;` inside `pbRemoveSelected` (single clip: "Remove <name>? This cannot be undone."); "Removing..." goes to the status line `#pbStatus`. Deletes: `#pbRemoveScrim` markup `P:6475-6486`, `.pb-scrim`/`.pb-dialog*` CSS, the scrim guards `P:10137`, `P:12966`, `pb.removeTargets`.
- Lines: -95 +10.
- Check here: standard; `grep -c pbRemoveScrim` = 0; Playwright with `page.on("dialog", d => d.accept())`: put a folder in the `--simulate` media dir, select it, Remove: it is gone; with `d.dismiss()`: it stays.
- Pi: nothing.
- Depends on: none.

### 12. web: the Clip Browser adds no browser history entries

- Functions: `setMediaBrowserOpen(open)` loses `fromHistory`; `pbvOpen` loses `keepHistory`'s push; `pbvClose` loses its pop. Deletes: both `history.pushState` (`P:10129`, `P:12777`), the `popstate` listener `P:20708-...`, `pb.pushed`, `pb.viewerPushed`, `pb.ignorePop`. Back buttons and Escape close as today.
- Lines: -30 +3.
- Check here: standard; `grep -c 'pushState\|popstate'` = 0; Playwright: open browser, open a clip, Back, Back: overlay closed, `history.length` unchanged.
- Pi: nothing. Owner decision 1 (phone Back).
- Depends on: 11.

### 13. web: the Clip Browser header uses the page's buttons, filter row and sort select

- Markup: `h1.pb-h1` -> `h2.section-title`; Back -> `icon-button settings-back-button` (as `closeMediaBrowserButton` `U:3993`); Refresh -> `secondary-button` "Refresh Media" with `/icons/refresh.png`; the SHOW pop-up -> a visible row of `media-filter-button` (`data-media-filter`, white active, `U:3999-4004`); the sort chip -> `select.settings-select.media-sort-select` (`U:4009-4012`); the Clear button returns beside Select All (`U:4020`, finding WCP-03-F3 in part).
- Functions: `pbSetFilter` reads the row; `pbSetShowMenu` and its document click handler deleted; sort reads the select's `change`.
- Deletes CSS: `.pb-h1`, `.pb-top-button`, `.pb-show-*`, `.pb-menu*`, `.pb-chip` and their media-query copies (`P:2047-2178`, `P:2475-2500` in part). 3 inline SVGs gone.
- Lines: -220 +45.
- Check here: standard; Playwright: filter row switches Clips/Stills/Timelapse/Audio; sort select reorders; screenshots at 1280 and 390 px width.
- Pi: nothing.
- Depends on: 12.

### 14. web: the Clip Viewer uses the page's buttons and /icons PNGs

- Markup: Back -> `icon-button settings-back-button`; Download -> `secondary-button` "Download"; Info -> `secondary-button` with `/icons/info.png`; previous/next clip and play keep their PNGs on `icon-button`; frame step -> `icon-button` with `/icons/previous.png` / `/icons/next.png` at 18 px and `aria-label` "Previous frame"/"Next frame"; the card's selected check (SVG built in JS `P:11833`) -> a `media-select-control` element with `.selected` (`U:1294-1330`).
- Deletes CSS: `.pbv-circle*`, `.pbv-icon-button`, `.pbv-info-button` (`P:2398-2450` in part, `P:2657-2678`, `P:2743-2775`); 4 inline SVGs in markup, 1 in JS.
- Lines: -130 +35.
- Check here: standard; `grep -c '<svg'` in the overlay range = 0; Playwright: open a clip from the simulate media dir (a cDNG folder made by `tools/flatten_clip.py` or any `.wav` for the audio path), Play, Pause, step, Info.
- Pi: open a 4K cDNG clip on a phone over Wi-Fi: play, step, scrub as before.
- Depends on: 13.

### 15. web: frame step and knob arrows send one step per click

- Deletes: `pbvRepeat` `P:12718-12729` and its two calls (click calls `pbvStep`; the left/right keys already repeat by key auto-repeat in the existing keydown handler `P:12961`); the `repeat` branch of `buildRemoteButton` `P:18090-18110` (pointer capture, 450 ms delay, 140 ms interval).
- Lines: -45 +4.
- Check here: standard; `grep -c 'setPointerCapture\|pbvRepeat'` = 0; Playwright: one click = one `test_input` (count requests) and one frame.
- Pi: turn ISO up from the Remote controls card: one step per click.
- Depends on: 14. Owner decision 2: if hold-to-repeat stays, skip this commit and document `buildRemoteButton` as new ground.

### 16. web: the Clip Browser's classes and ids use the media-browser and clip-viewer names

- Mechanical rename (map in the commit body): `.pb-*` -> `.media-browser-*`, `.pbv-*` -> `.clip-viewer-*`, `body.pb-open` -> `body.media-browser-open` (declared once; the second rule `P:1980` deleted), ids `pb*` -> `mediaBrowser*`, `pbv*` -> `clipViewer*`, `#playbackOverlay` -> `#mediaBrowserOverlay`.
- Lines: about 650 lines edited, -4 +0.
- Check here: standard; `grep -cE '\.pbv?-|id="pbv?[A-Z]'` = 0; Playwright screenshots identical to commit 15's (pixel diff).
- Pi: nothing.
- Depends on: 15. Owner decision 4.

### 17. web: the Clip Browser's state is flat on state under upstream names

- Moves: `state.pb.*` to the flat fields in the target table; `state.pb.viewer` -> `state.clipViewer`; declares `previewPausedForPlayback` (WCP-06-F12). Deletes: the nested `pb: {...}`.
- Lines: -5 +22 declarations; about 150 lines edited.
- Check here: standard; `grep -c 'state\.pb\b'` = 0; Playwright as commit 14.
- Pi: nothing.
- Depends on: 16.

### 18. web: the Clip Browser's upstream jobs have their upstream names again

- Renames: `pbRender` -> `renderMediaLibrary`, `pbSorted` -> `sortedMediaItems`, `pbSelectedItems` -> `selectedMediaItems`, `pbToggle` -> `toggleMediaSelection`, `pbSetFilter` -> `setMediaBrowserFilter`, sort setter -> `setMediaBrowserSort`, `pbDownloadSelected` -> `downloadSelectedMediaItems`, `pbRemoveSelected` -> `deleteSelectedMediaItems`, selection pruning -> `pruneMediaSelection`, select-all -> `selectAllVisibleMedia`.
- Lines: about 60 lines edited.
- Check here: standard; Playwright as commit 14.
- Pi: nothing.
- Depends on: 17.

### 19. web: the Clip Viewer's functions have verb-first names

- Renames the remaining `pb*`/`pbv*` functions and constants (map in the commit body): e.g. `pbBuildCard` -> `buildMediaCard`, `pbQueueThumb` -> `queueMediaThumbnail`, `pbvOpen` -> `openClipViewer`, `pbvClose` -> `closeClipViewer`, `pbvPlay` -> `playClip`, `pbvPause` -> `pauseClip`, `pbvStep` -> `stepClipFrame`, `pbvSeekTo` -> `seekClip`, `pbvFetchFrame` -> `fetchClipFrame`, `pbvDraw` -> `drawClipFrame`, `pbvApplyHold` -> `applyClipHold`, `pbvInstall` -> `installClipViewerInteractions`, `pbvTimeline` -> `clipTimeline`, `pbvNumberAtTime` -> `clipNumberAtTime`, `pbvInHole` -> `clipFrameInHole`; `pbFilters`, `pbvHoldText`, `pbvWidths` -> `mediaFilterLabels`, `clipHoldText`, `clipFrameWidths`.
- Lines: about 300 lines edited.
- Check here: standard; `grep -oE '\bpbv?[A-Z]\w*'` = 0; Playwright as commit 14.
- Pi: nothing.
- Depends on: 18.

### 20. web: dropdowns have one look on every panel

- Deletes: CSS `P:3484-3559` except the used-pin grey rule (kept as `.settings-select.controls-pin option[data-used]`), tokens `--select-bg/--select-fg` `P:35-36`, class `controls-pin-select` at `P:17388`. Fixes WCP-02-F7 (a new GPIO-in row got a white pin dropdown).
- Lines: -80 +3.
- Check here: standard; `grep -c 'select-bg\|controls-pin-select'` = 0; Playwright screenshot of Controls and Config > Hardware.
- Pi: nothing.
- Depends on: none (can go first).

### 21. web: Remote controls is a card in the Controls panel

- Moves: the card `P:4569-4580` into the Controls `settings-panel` as `div.settings-card` > `settings-card-head` > `h3.settings-card-title` "Remote controls" + one-sentence `p.settings-card-copy`. Data: already loaded by `setSettingsPanel("controls")` `P:10166`. Deletes: the main-page card and the bootstrap loop `P:20940-20949`; the `#remoteControlsRows .pill-button` override `P:3420` if the pills render through `pill-grid`.
- Lines: -30 +18.
- Check here: standard; Playwright: main page has the four upstream cards; no `get_controls` request before Controls opens (`page.on("request")`); Controls shows the pad; one click on a button pill sends one `test_input`.
- Pi: from the Controls panel, press "Record" on the pad: the camera records as with the hardware button.
- Depends on: 15 if taken. Owner decision 3. Hardware-inputs theme: `test_input` refusing script actions lands in parallel; the pad shows its refusal through `showToast`.

### 22. web: the IMX585 resolution pills read the page's class table

- Deletes: the pool branch in `imx585ClassRows` `P:8956-8960` and in `imx585LadderFamily`; the comment `P:8911-8914` that names the pool. The mono branch (`snapshot.sensor_mono`) stays. `state.ladderServer` keeps serving the Mode Ladder card and the fps sub-labels.
- Lines: -9 +1.
- Check here: standard; `grep -c 'ladderServer.pool'` in the pill functions = 0; Playwright with `/api/state` routed to an IMX585 snapshot (`sensor: "imx585"`, `raw_bit_depth: "12-bit"`, `clear_hdr: false`): resolution pills and crop row as the class table `s12`.
- Pi: on the owner's camera (port driver), Settings > Record shows the same pills as before; on a stock IMX585 (original driver) see Risks.
- Depends on: camera-modes theme for the table's content (which sizes exist, the 1.85:1 names). The touch UI's IMX585 lists (`qml/CameraPage.qml:418`, `qml/SettingsPage.qml:161`) are the touch-ui theme's ("mode list").

### 23. web: the Mode Ladder and settings search draw no inline SVG

- Replaces: `ladderIcons` `P:7644-7650` (handle, up, down, remove, chevron) with text in `secondary-button`s ("Up", "Down", "Remove"; the handle and chevron become the row itself and a `.hidden` toggle), the search field's magnifier SVG `P:4733` with nothing (upstream fields carry no icon). After this, `grep -c '<svg'` on the page = 0 (WEB-9).
- Lines: -12 +10.
- Check here: standard; Playwright: ladder rows move up/down.
- Pi: nothing.
- Depends on: camera-modes theme if it rewrites the ladder editor (WCP-04-F5) first; then only the search icon is left.

### 24. web: hidden elements use the .hidden class

- Replaces: 26 `element.hidden = x` with `element.classList.toggle("hidden", x)` and the `hidden` attributes in markup (about 17) with `class="... hidden"`; deletes the 5 `[hidden]` CSS patches.
- Lines: -45 +35.
- Check here: standard; `grep -c '\.hidden = \|\[hidden\]'` = 0; Playwright: every panel opens with the same visible text as before (text diff).
- Pi: nothing.
- Depends on: 9, 10, 21 (they touch the same lines).

Totals: about -1 100 / +450 lines, plus about 1 400 lines edited by renames in commits 1, 7, 16-19.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| The lock-free `/api/buffer` poll at 4 Hz (WCP-08-F4) | One async `fetchBufferState`, its timer and in-flight flag on `state`, started and stopped by one `updateBufferPolling(snapshot)`, merging into `state.snapshot` and redrawing only through `renderRecordingStatus` | `/api/state` blocks on the controller mutex while a stopped take drains (`CC:12571-12574`), so at 1 Hz the page would show a safety stop seconds late and the buffer bar would jump. The shape is upstream's: one store, one renderer for the pill, raw `fetch` like `user_activity` |
| Clip Viewer playback engine (frame fetch lanes, `requestAnimationFrame` tick, keep-awake `user_activity` interval) | `state.clipViewer`, one object per open clip, created and dropped by `openClipViewer`/`closeClipViewer` | A per-clip object keeps the timeline, lanes and timers that all die together; flattening 20 viewer fields onto `state` would scatter them. It is the one nested object left on `state` |
| Listen (300 ms `controls_last_input` while the operator listens, max 2 min) | Raw `fetch`, timer and in-flight flag on `state` | No upstream feature waits for a hardware press; a push channel would be bigger new ground (WEB-7) |
| Settings search with a MutationObserver (WCP-05-F4, WCP-01-F12) | Flat `state.settingsSearch*` | Kept as reviewed ("keep") |
| Remote controls pad (`test_input`) | A settings-card in Controls, pills, one command per click | The feature the owner restored (fork-log.md:163-164); upstream has no remote pad |
| Clip card grid with thumbnails (replaces upstream's list) | Grid and card CSS kept under `.media-browser-*` names | The reviewed rework keeps the grid, cards, thumbs, stage, scrub, histogram and metadata (WCP-02-F1) |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Should the phone's Back button close the Clip Browser? | a) Delete the history entries (commit 12). b) Keep `pushState`/`popstate` as documented new ground (about 25 lines) | a). Cost: on a phone, Back leaves the WebUI page instead of closing the overlay; the overlay's own Back and Escape still close it. Upstream has no history use at all |
| 2 | Keep hold-to-repeat on the Remote controls knob arrows and on frame step? | a) One step per click (commit 15). b) Keep both, document as the one new widget behaviour | a). Cost: turning ISO by five steps takes five taps; on a desktop the arrow keys still repeat in the viewer |
| 3 | Where does Remote controls live? | a) A card in the Controls panel (commit 21). b) Main page, as today | a). Cost: one more tap (Settings > Controls) from the main page. Upstream keeps the main page for the four camera-critical cards (WEB-2) |
| 4 | Do the Clip Browser renames (commits 16-19, about 1 150 lines touched, no behaviour change) go in? | a) Yes. b) Keep the `pb`/`pbv` names and document them | a). The original developer finds his own names (`renderMediaLibrary`, `state.mediaSelection`) instead of an abbreviation no other part of the page uses. Cost: four large mechanical diffs; any open Playback branch must rebase (rerun the sed map) |
| 5 | Where do the IMX585 resolution pills get their sizes? | a) The page's class table only (commit 22, upstream WEB-8). b) `list_sensor_modes` once through `sendCommand` into `state.sensorModes`, like `audio_capabilities` (needs Core to add the active size per mode, because the 16-bit frame carries optical-black rows) | a), with camera-modes deciding the table. Cost: a camera whose driver lacks a size shows the pill and gets Core's refusal or fallback (see Risks) |
| 6 | White dropdowns for readability? | a) Delete (commit 20). b) Make `.settings-select` easier to read page-wide, as its own upstream-candidate commit | a) now; b) later if wanted. Cost of a): the Controls dropdowns look like every other dropdown again |
| 7 | Remove dialog text | a) `window.confirm` one line (commit 11). b) Keep the modal | a). Cost: the confirm cannot list the clip names on several lines |

## Risks and what was not determined

| Risk | What settles it |
| --- | --- |
| Commits 3-4 change the REC pill, the most camera-critical element of the page. Routed replies in Playwright prove the logic, not the timing on a real drain | Pi steps in commit 3, on CM5 and on a Pi 4 with an SD card (the slowest drain). Until done, keep commits 3-4 on their own branch |
| `sendCommand` merges each reply through `mergeCameraStateFields`. A routed command whose reply gains a top-level `state`, `resolution`, `fps`, ... would overwrite the snapshot | Checked in `--simulate` for the 6 read replies (no such key). On the Pi: `curl -s -X POST -d '{"cmd":"get_controls"}' http://<pi>:8000/api/command \| jq 'keys'` and the same for `get_mode_ladder`, `preview_clip_name` |
| A stock IMX585 (original driver `origin/apertar` `e5b74d3`) with commit 22 shows the class table's sizes; whether the driver offers them, and what Core does when it does not, is not determined. With the pool it showed only the driver's modes, which may also differ from 1.6.0's 20 crop sizes | On a stock camera: `curl ... get_mode_ladder \| jq '.mode_ladder.pool'` against the table; `git -C /home/user/imx585-v4l2-driver grep -n 2072 origin/apertar`. Owned by camera-modes |
| Splitting `renderRecordingStatus` out of `renderSnapshot` touches a rough edge upstream keeps (WEB-24) | Argued in commit 2; the original developer may object. Fallback: keep the pill block inline and call `renderSnapshot(state.snapshot)` from the buffer poll at most once per second |
| Renames (commits 7, 16-19) conflict with any branch that edits the same lines (Playback bugs WCP-06-F5..F8, preroll theme's pre-roll button, boot-config-helpers' card) | Land renames last within their area; publish each sed map so a branch can replay it |
| Pi-model compatibility: all changes run in the client's browser; Core work per request is unchanged (same routes, same rates). The 4 Hz poll cost on a Pi Zero 2 / Pi 3 was not measured, today or after | `top` on the Pi while a phone keeps the page open during a take, before and after commit 4 |
| Line estimates are from reading, not from doing the edits | - |

## Findings covered

| Finding | Commit |
| --- | --- |
| WCP-02-F1 | 13, 14 (Remove dialog part: 11) |
| WCP-02-F2 | 20 |
| WCP-03-F1 | 11 (dialog), 12 (history), 13 and 14 (SVG, h1), 17 (nested `state.pb`) |
| WCP-04-F1 | 22 |
| WCP-06-F1 | 17, 18, 19 |
| WCP-08-F1 | 1, 2, 3, 4 |
| WCP-09-F1 | 7, 8 |
| WCP-09-F2 | 5 |
| WCP-09-F3 | 21 (hold-to-repeat: 15) |
| WCP-10-F2 | 9 |
| X-state-consistency-3 | 22 for the WebUI side only. QML lists: touch-ui theme ("mode list"). Table content and the comment in `Imx585Modes.hpp`: camera-modes theme |
| WCP-01-F8 | 16 |
| WCP-02-F3 | 16 |
| WCP-02-F7 | 20 |
| WCP-02-F10 | 16 (body rule; the `.x.hidden` repeats in 24) |
| WCP-03-F3 | 13 (Clear button). Per-row Download/Delete: not covered, the viewer offers both per clip; see WCP-06-F4 |
| WCP-03-F5 | 24 |
| WCP-03-F8 | 21 |
| WCP-04-F2 | 6 |
| WCP-04-F3 | not covered: the render-driven ladder fetch also feeds the fps pill sub-labels; it goes with the Mode Ladder editor rework (camera-modes, WCP-04-F5) |
| WCP-04-F9 | 14, 23 |
| WCP-05-F5 | 12 |
| WCP-06-F2 | 11 |
| WCP-06-F12 | 17 |
| WCP-07-F2 | 10 |
| WCP-07-F10 | 6 |
| WCP-08-F2 | 3, 4 |
| WCP-08-F3 | 3 (freshness windows), 4 |
| WCP-08-F4 | kept as new ground (section above) |
| WCP-09-F7 | 5 |
| WCP-09-F8 | 5, 8 (timer and in-flight flag on `state`); the poll itself stays as new ground |
| WCP-10-F9 | 21 |
| WCP-10-F10 | 3 |
| WCP-02-F8, WCP-06-F4 | not covered: the card grid replaced upstream's list on purpose; restoring size/fps/frame facts on cards is a feature choice, not a store or part. Owner list of the Playback fix list |
| WCP-06-F9 (timecode helpers duplicated) | not covered: Playback internals, separate small commit in the Playback fix list |
| WCP-02-F9, WCP-01-F5 (rules with no element) | not covered: slop pass (commit-clarity work) |
| WCP-10-F1 (Boot Config route) | not covered: boot-config-helpers theme |

## Challenge

Read: `/home/user/wt/core-work` at `3650027` (the design read `7dc6f7a`; `git diff 7dc6f7a HEAD -- src/web/WebControlPage.cpp` is 2 text lines at P:5792 and P:16157, so every `P:` line above still holds). `U:` = `/home/user/wt/core-upstream@upstream-1.6.0`. `--simulate` run here: `/home/user/build/work-nolc/apertar-core` on port 18977. All rows **confirmed** in code unless marked.

| Point | What the design says | What the code says, file:line | What must change |
| --- | --- | --- | --- |
| a. Precedent for the pill writer | Splitting the pill out of `renderSnapshot` is an exception to WEB-24; "No upstream precedent" for DOM edits outside it | Upstream already draws DOM outside `renderSnapshot` from a second timer: `updateTimecodeDisplay` `U:9168`, called by `updateLiveReadouts` `U:9219-9222` from `startLiveReadoutLoop` (requestAnimationFrame) `U:9224-9238`, started at `U:11608`, reading only `state.snapshot` and `state.*Base*` | Commit 2 cites `updateTimecodeDisplay` as the precedent: one small function that reads `state.snapshot`, called by the 1 Hz render and by a second timer. Only the network poll stays new ground |
| a. One installer | "All listeners in one installer; no second installer" (commit 9 deletes `installBootConfigInteractions`) | Upstream has a second feature installer: `installPreviewStream` `U:8566` (adds `load`/`error` listeners), called beside `installInteractions` `U:11606-11608`. The design itself keeps `pbvInstall` `P:12928` (14 listeners) as `installClipViewerInteractions` (commit 19) | Be consistent and smaller: keep `installBootConfigInteractions` (rename only if the owner wants it) like `installPreviewStream`. Commit 9 drops its 50-line listener move |
| a. Flat state for the viewer | `state.clipViewer` stays one nested object, "flattening would scatter" | Upstream flattens even a dozen WebGL handles that live and die together: `previewProcessingGl ... previewProcessingLastFrameMs` `U:4255-4266`. No nested object in `U:4204-4266` | A decision, not a given: put "nested `state.clipViewer` vs flat `clipViewer*`" on the owner's list (commit 17) |
| a. Sort select and filter row | Refresh -> `secondary-button` with `/icons/refresh.png`; the new elements are renamed later in commit 16 | Upstream Refresh is text only `U:4008`; ids are `mediaBrowserFilters`, `refreshMediaBrowserButton`, `mediaBrowserSortSelect`, `closeMediaBrowserButton` `U:3993-4012`. The port deleted all `.media-browser-*`, `.media-filter-button`, `.media-sort-select` CSS (0 matches in P) | Commit 13 copies `U:3993-4012` markup with its ids and re-adds `U:1238-1253` CSS verbatim; commit 16 then has fewer ids to rename. Header SVGs are 2 (`P:6355`, `P:6371`), not 3 |
| b. Merge of `/api/buffer` | `applyBufferSnapshotPatch` copies the reply "through the existing `mergeCameraStateFields`" | `mergeCameraStateFields` copies `buffer_setting`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_mode`, `storage_preroll_*`, `buffer_note` `P:13841-13859`, but not `buffer_fill`, `buffer_flush_discarded`, `buffer_used`, `buffer_capacity` (`/api/buffer` reply `App:301-309`, seen in `--simulate`) | Commit 3 adds the missing `buffer_fill` and `buffer_flush_discarded` lines to `mergeCameraStateFields` (+4), or the bar never moves at 4 Hz and commit 4's discard toast never fires from the poll |
| b. Stale fill in `/api/state` | Delete the 1000 ms freshness windows `P:16553`, `P:16561`, `P:16575`, and `bufferFillAtMs` | `buildWebStateJson` reads the gauge before it blocks: `bufferStatus = camera_.frameBufferStatus()` `App:9306`, then `camera_.state()` `App:9307` waits on the controller mutex while a take drains. Safety stop and pre-roll come from `bufferSettingMembers()` at string build time (`App:9591`, fresh). So a drained-late `/api/state` carries a fill seconds old | Keep one rule, not three: while `state.bufferPollTimer` runs, `renderSnapshot` keeps `buffer_fill` from the previous `state.snapshot` (one line after the `system.*` lift `P:15216-15222`). The finding's own rework kept `bufferPolledAtMs` for this. Add Playwright scene (e): poll says 0.3, a late `/api/state` says 0.9: bar stays 30 % |
| b. Commit 3 vs 4 split | Commit 3 deletes `bufferSafetyStop`, `bufferStopPercent` and the `P:16561` window; commit 4 deletes `noteBufferSafetyStop` | `noteBufferSafetyStop` `P:16458-16471` writes and reads those fields and is called from both timers; `P:16560-16562` is the guard that stops the 1 Hz path from re-feeding it | Commit 3 leaves `noteBufferSafetyStop` and its `stopSeen`/`discardedSeen`/`stopPercent` fields (on `state`) untouched; commit 4 removes them together |
| b. First-load toast | Commit 4: `if (next.buffer_flush_discarded > 0 && next.buffer_flush_discarded !== previous.buffer_flush_discarded) showToast(...)`, "shaped like `U:9331-9333`" | `buffer_flush_discarded` is "kept until the next safety stop" (`App:247-250`). Old code starts `discardedSeen: -1` `P:16420` and skips the first value `P:16460`. Upstream's shape toasts on the first snapshot too (`previousError` undefined `U:9331`) | Guard on a previous snapshot: `state.snapshot && ...`. Without it every page open after a flush discard shows "Record pressed during the flush ..." until the next safety stop. Compare after the `system.*` lift. Playwright: load with `buffer_flush_discarded: 12`: no toast |
| b. sendCommand side effects | Commit 6: each read "renders once from the unchanged snapshot and schedules one `/api/state`" | `applyCommandSnapshotPatch` returns `true` for every command (`default: break; ... return true` `P:14408-14412`), so `sendCommand` renders twice `P:14427-14428`, `P:14442-14443`. While in flight: `commandInFlightCount > 0` disables REC `P:15772`, `toggleRecord` returns early when not recording `P:19273-19275`, `fetchState` drops its reply `P:16396` | Correct the cost text. Real problem is the next row |
| b. Render-driven `get_mode_ladder` through sendCommand | Commit 6 routes `fetchModeLadder` through `sendCommand` like `audio_capabilities` | `fetchModeLadder` is started from `renderModeLadder` on every render (`P:8395-8400`: first fetch, 5 s retry, `ladder_active` change), and `get_mode_ladder` takes the controller mutex (`CC:11041`), which a draining take holds. Through `sendCommand` the REC button goes disabled and `/api/state` is dropped for as long as it waits, also during a safety-stop flush where REC must stay live (`P:15770`). The precedent `audio_capabilities` is loaded on panel open only `U:6162` | Split commit 6: 6a `clipRawCommand` and the ladder save / dry runs go through `sendCommand`. 6b (`ladderRequest` deleted) only after the render-driven fetch moves to `setSettingsPanel("modes")` plus a snapshot comparison (WCP-04-F3), which the design left to camera-modes: name it as a dependency or do it here |
| b. `error.result` | Commit 5 adds `error.result = result`, "the same shape the port's `/api/config` save uses" | The port's config save sets `failure.payload = payload` `P:19001-19003`; 0 `error.result` in P | Use one name: `error.payload` (matches `P:19002`) |
| b. Outside readers | Page only; no other reader | Confirmed: `frameBufferBar`, `controlsState`, `playbackOverlay`, `pbGrid`, `pbRemoveScrim`, `remoteControlsRows` appear nowhere in Core, `tools/`, `/home/user/wt/ui-work` or the coding map except the UI.conf key `frameBufferBarEnabled` (`SettingsBridge.cpp:369`, `App:2096`), which no commit touches | None |
| c. Mono IMX585 | Commit 22: "The mono branch (`snapshot.sensor_mono`) stays" | With the pool deleted, the mono branch returns only the running size `P:8961-8964`, and `imx585BaseResolutionOptions` hides the families without rows for mono `P:9020-9028`. Today a mono IMX585 gets every probed size from the pool `P:8956-8959` | Commit 22 takes resolution choice away from a mono IMX585 in the WebUI, and for a stock driver the design says itself it does not know what is offered (Risks). Drop it from this theme and hand it to camera-modes with these two facts. Owner item 5 is missing the mono cost |
| c. Behaviour on the rig and a stock camera | "Every feature stays" | Commits 12 (phone Back), 15 (hold-to-repeat) and 21 (main-page pad) remove or move features the owner restored (`fork-log.md:162-164`, `1319967`) | Fine as owner options, but the chain makes option b) break the plan: 13 depends on 12, 16 and 21 on 15. Make 12, 15 and 21 leaves: nothing after them depends on them |
| c. Remote controls option b) | Owner item 3 b) "main page, as today" | The 5 s retry loop `P:20940-20949` keeps an untracked timer (WCP-10-F9) | Missing commit for b): keep the card, store the retry as `state.controlsRetryTimer` like `state.previewRetryTimer` (`U:8578`), about -3 +4 |
| d. Commit 1 | Pure move of 14 fields to `state.buffer*` | Commit 3 deletes 9 of the 14 again; commit 4 deletes 4 more | Drop commit 1. Commit 3 deletes `frameBufferBar` and declares only the fields that survive (`bufferPollTimer`, `bufferPollInFlight`, `prerollPollUntilMs`, plus the seen fields until commit 4). Saves about 55 edited lines |
| d. Commit 7 | Moves the Controls label tables (`controlsGroups`, ...) to the option-list block too | WEB-8 is about pill option lists (`U:4039-4127`); upstream keeps meta tables beside `state` (`favoriteItemMeta` `U:4128`, `settingsPanelMeta` `U:4165`). The move is a second idea | Drop the 40-line move from commit 7, or make it its own commit |
| d. Commit 10 | `clipUi` and `settingsSearch` in one commit | Two stores, two features | Split into two commits |
| d. Standard check 2 | `smoke_core.sh` before/after diff is empty | `smoke_core.sh:41` prints `GET / -> 200, <bytes>, <lines>`: it changes on every page commit | Diff with that line removed (`grep -v '^== GET / '`) |
| d. Commit 15 check | `grep -c 'setPointerCapture\|pbvRepeat'` = 0 | `pbvRepeat` `P:12718-12729` uses no pointer capture; `setPointerCapture` is also the scrub `P:12678` and the composer drag `P:14730`, both kept | Check `grep -c 'pbvRepeat'` = 0 and no `setPointerCapture` inside `buildRemoteButton` |
| d. Commit 24 check | Replace 26 `element.hidden = x`; `grep -c '\.hidden = '` = 0 | One of the 26 is upstream's own line: `option.hidden = ...` `P:15437` = `U:9526` (on an `<option>`, where a class does not hide in every browser). `P:15830-15860` are the preroll theme's rows, `P:20095-20554` the boot-config-helpers card | Keep `P:15437`; check `= 1`. Land after preroll and boot-config-helpers |
| d. Commit 16 size | About 650 lines edited | Mechanical | Review by rerunning the published sed map on the parent and diffing against the commit (empty), not by reading 650 lines |
| e. Simpler | 24 commits | See rows above | Commit 1 and commit 22 go; commit 9 shrinks by the listener move; commit 13 copies upstream markup instead of new markup |
| f. Hidden decisions | Owner list items 1-7 | Nested `state.clipViewer` (commit 17) and the mono loss (commit 22) are decided inside commits | Add both to the owner's list. Item 7 (confirm text) is the same decision as item 1 of WCP-02-F1's rework, already settled by WEB-21 (`U:10307` etc., 8 confirms): fold it into commit 11's body, no owner question needed |
| g. Pi checks | Commit 3: RAM mode, frame buffer bar on, record until the safety stop | The bar-off path is separate code today: `watchStop` `P:16566` polls `/api/buffer` with the option off so the red pill drops at the stop | Run the commit 3 steps twice, bar on and bar off. To know a safety stop happened: `while :; do curl -s http://<pi>:8000/api/buffer \| jq -c '{buffer_fill,buffer_safety_stop,buffer_flush_discarded,recording}'; sleep 0.25; done` beside the page. Look for: pill READY green within 0.5 s of `buffer_safety_stop: true`, bar never jumps back up when `/api/state` answers after the drain (the stale-fill row), one toast |
| g. Pi-model cost | `top` before and after commit 4 | Unchanged request rates; Core work per request unchanged | Stands. Say the reading to compare: `apertar-core` CPU % during a take with one phone on the page, Pi 4 and Pi 5 |

Verdict

| Commit | Verdict | Why |
| --- | --- | --- |
| 1 | dropped | Its fields are deleted again in 3 and 4; 3 declares only the survivors |
| 2 | stands | Cite `updateTimecodeDisplay` `U:9168-9238`; the record button block `P:15769-15772` stays in `renderSnapshot` |
| 3 | changes | Add `buffer_fill`/`buffer_flush_discarded` to `mergeCameraStateFields`; keep one stale-fill rule; leave `noteBufferSafetyStop` for 4; Pi steps with bar on and off |
| 4 | changes | Toasts only when a previous snapshot exists, compared after the `system.*` lift |
| 5 | changes | `error.payload`, not `error.result` |
| 6 | changes | Split: 6a preview and ladder save/dry run; 6b `get_mode_ladder` only after its render-driven fetch moves to panel open (WCP-04-F3) |
| 7 | changes | Without the label-table move |
| 8 | stands | |
| 9 | changes | Keep `installBootConfigInteractions` (precedent `installPreviewStream`); move only the fields |
| 10 | changes | Two commits |
| 11 | stands | Confirm text settled by WEB-21; drop owner item 7 |
| 12 | stands | As a leaf; owner item 1 |
| 13 | changes | Upstream markup and ids `U:3993-4012`, upstream CSS `U:1238-1253` re-added, Refresh text only, 2 SVGs; Clear button its own commit |
| 14 | stands | |
| 15 | changes | Correct check; leaf |
| 16 | stands | Sed-map review; owner item 4 |
| 17 | changes | Nested vs flat `clipViewer` to the owner |
| 18, 19 | stand | |
| 20 | stands | |
| 21 | stands | As a leaf; owner item 3 |
| 22 | dropped | Mono IMX585 loses its sizes; stock offer undetermined; belongs to camera-modes |
| 23 | stands | |
| 24 | changes | Keep upstream's `option.hidden`; after preroll and boot-config-helpers |
| missing | A | Remote controls option b): stored retry timer `state.controlsRetryTimer` (`U:8578` shape) |
| missing | B | The Mode Ladder fetch moves from `renderModeLadder` to `setSettingsPanel("modes")` plus a `ladder_active` comparison (WCP-04-F3), before 6b, or a named dependency on camera-modes |
