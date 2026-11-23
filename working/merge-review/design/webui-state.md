# The WebUI: one state, one poll loop, its own parts: final plan

Read: Apertar-Core `/home/user/wt/core-work` at `0d13a6f` (port `01f170c` + 10 fixes; `git diff 7dc6f7a HEAD -- src/web/WebControlPage.cpp` changes 2 lines in place at P:5792 and P:16157, so every line number below holds), Apertar-UI `/home/user/wt/ui-work` at `ac1fc28`; measuring stick `/home/user/wt/core-upstream` `upstream-1.6.0` `35dbe67`. `P:` = `src/web/WebControlPage.cpp@0d13a6f`, `U:` = the same file `@upstream-1.6.0`, `App:` = `src/ApertarCoreApp.cpp@0d13a6f`, `CC:` = `src/camera/CameraController.cpp@0d13a6f`. All rows **confirmed** in code unless marked.

## In short

1. Today the page has five stores where upstream has one: `state`, `frameBufferBar`, `controlsState` (plus 5 module-level sets and lets), `bootConfig`, `clipUi`/`settingsSearch`, and a nested `state.pb`.
2. It has two network loops for camera state: `fetchState` at 1 Hz and `pollFrameBufferBar` at 4 Hz. The second one edits the REC pill outside `renderSnapshot`, and 1000 ms freshness windows decide which writer wins.
3. It has four doors to `/api/command`: `sendCommand`, `controlsCall`, `ladderRequest`, `clipRawCommand`.
4. The Clip Browser and Viewer bring a second widget set (round buttons, a pop-up menu, a chip, a modal dialog, inline SVG, browser history, hold-to-repeat), and the Controls panel brings white dropdowns.
5. Target: one `state` with flat fields. One loop that renders everything (`fetchState`), plus the lock-free `/api/buffer` poll, kept as documented new ground: it merges into `state.snapshot` and redraws only the pill, through one function, in the shape of upstream's `updateTimecodeDisplay` (`U:9168-9238`). One door (`sendCommand`); a raw `fetch` only for background traffic, like upstream's `user_activity`. Upstream's parts and names.
6. Every feature stays. Nothing in Core, in any reply, or in any file on the camera changes. Only `src/web/WebControlPage.cpp` changes.
7. 21 commits in a chain plus 4 leaf commits that are owner options (22-25; take 24 or 25, not both). All are in Apertar-Core and change only the page. About 1 040 lines removed and 480 added, plus about 1 500 lines of pure renames in 7 mechanical commits.
8. Six owner decisions: phone Back, hold-to-repeat, where Remote controls lives, the Clip Browser renames, nested or flat `state.clipViewer`, and white dropdowns.
9. Left to other themes, with the facts below: the IMX585 resolution pills' source (camera-modes; deleting the pool costs a mono IMX585 its sizes) and the render-driven Mode Ladder fetch (camera-modes; `ladderRequest` stays until then).

## How it works in the port today

Thread and lock: the page is single-threaded browser JS, so "thread" below means the browser timer or event that runs the code. On the Core side, the web server runs one detached thread per request (`src/web/WebServer.cpp:279-290`), so `/api/buffer` answers while `/api/state` waits.

### Recording pill and write buffer

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Buffer gauge (`used`, `capacity`, `active`, `ram`) | Raw writer queue | `CameraController::frameBufferStatus()` `CC:12527` | Relaxed atomics, plus one `try_lock` that never waits | none | `system.buffer_*` in `/api/state`; `/api/buffer`; socket event `buffer` (touch UI) |
| Safety stop, stop percent, flush-discarded count | `bufferbudget::safetyStopState()` | `bufferSettingMembers()` `App:252-269` | Atomics, read when the reply string is built | none | Same three places. `buffer_flush_discarded` is "kept until the next safety stop" (`App:247-250`) |
| Pre-roll active, fps, auto | `storagepreroll::*` | `bufferSettingMembers()` `App:260-264` | Atomics | `[storage]` of `apertar-hardware.conf` (preroll theme) | Same three places |
| `GET /api/state` | `buildWebStateJson()` `App:9302`, route `App:8432-8437` | `fetchState` `P:16377` | Reads the gauge first (`App:9306`), then waits on CC `mutex_` in `camera_.state()` (`App:9307`, `CC:12573-12576`) while a stopped take drains; safety stop and pre-roll come from `bufferSettingMembers()` at string build (`App:9591`). **So after a drain the reply's `buffer_fill` can be seconds old, while its `buffer_safety_stop` is fresh** | none | Whole page via `renderSnapshot` `P:15213`, which lifts `system.buffer_*`/`storage_preroll_*` to the top level `P:15215-15221` |
| `GET /api/buffer` | Route `App:8423-8430`: `bufferMembers(...)` + `recording` = gauge recording and not safety stop | `pollFrameBufferBar` `P:16491-16539` | Lock-free (comment `App:8422`) | none | REC pill only |
| `frameBufferBar` (14 fields `P:16419-16421`) | `pollFrameBufferBar`, `updateFrameBufferBar` `P:16547`, `noteBufferSafetyStop` `P:16458`, `notePrerollRequested` `P:16435` | `applyCommandSnapshotPatch` record_start `P:14381`; `renderSnapshot` `P:15389`, `P:15757-15759`; fps pills `P:15917`; `toggleRecord` `P:19272` | Second timer: `window.setInterval(pollFrameBufferBar, 250)` at `P:16432` and `P:16587`; stopped in `.finally` `P:16533-16538` | none | REC pill |
| `state.snapshot.storage_preroll_*` | `renderSnapshot`, and directly by the 4 Hz poll `P:16505-16512` | `renderSnapshot` `P:15391`, `markPrerollFps` `P:8696` | Both timers | none | Pill text, FPS badge |
| `.status-pill` classes, `#statusDot` classes, `#recordingStatus` text | `renderSnapshot` `P:15388-15392`, `P:15752-15768`; outside it `applyPrerollPill` `P:16441-16456` and `applyFrameBufferPillClasses` `P:16473-16489` (removes `recording`, rewrites "REC" to "READY") | browser | Two writers; `P:16553` (pre-roll), `P:16560-16562` (safety stop) and `P:16575-16578` (fill) pick the poll's value while it is under 1000 ms old | none | Main page header pill |
| Toasts "Recording stopped: the write buffer reached N %." and "Record pressed during the flush..." | `noteBufferSafetyStop` `P:16458-16471`, from both timers; de-duplicated by `stopSeen`, and `discardedSeen` starts at -1 so the first value seen never toasts (`P:16420`, `P:16460`) | toast | Both timers | none | Toast |
| Frame buffer bar option | `set_frame_buffer_bar_enabled`, patch `P:14241` | `updateFrameBufferBar` `P:16550`; with the option off, `watchStop` `P:16566` still polls `/api/buffer` during a queue-backed take so the red pill drops at a safety stop | 1 Hz | `UI.conf` `frameBufferBarEnabled` (`App:2096`) | Settings pill; touch UI via bridge (`SettingsBridge.cpp:369`) |
| `mergeCameraStateFields` `P:13784-13933` (upstream function `U:8595`, port added buffer lines) | `sendCommand` replies | - | - | - | Copies `buffer_setting`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_mode`, `storage_preroll_*`, `buffer_note` (`P:13841-13860`) and `recording` (`P:13889`); **not** `buffer_fill`, `buffer_flush_discarded` |

### Command doors

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| `sendCommand(payload)` `P:14415-14450` | Every upstream handler | `/api/command` -> `handleCommand` under the command lock | Patches and renders before the request and again after it (`applyCommandSnapshotPatch` returns `true` for every command, `P:14408-14412`, so 2 renders per call); rolls back on `ok:false`; throws `Error(result.error)`; schedules `/api/state` in 140 ms. While in flight: `commandInFlightCount > 0` disables REC when not recording (`P:15770-15772`), `toggleRecord` returns early when not recording and not flushing (`P:19272-19275`), `fetchState` drops its reply (`P:16396`) | - | - |
| `controlsCall(payload)` `P:16699-16705` | 16 call sites (`P:16920`, `17735`, `17966`, `18256`, `18300`, `18334-18335`, `18589`, `18627`, `18654`, `18659`, `18700`, `18729`, `18866`, `18966`) | Same route | Returns the JSON; callers test `ok` by hand; 7 sites have no try/catch | - | Controls, Hardware and Config cards |
| `ladderRequest(payload)` `P:8005-8015` | One caller: `fetchModeLadder` `P:8017-8031` (`get_mode_ladder`). No dry run is sent from JS | Same route; `get_mode_ladder` takes CC `mutex_` (`CC:11041`) | Started from `renderModeLadder` `P:8395-8400` on every render: first fetch, 5 s retry, refetch on `ladder_active` change | `mode_ladder.conf` | Modes panel; main-page IMX585 pills via the pool |
| `clipRawCommand(payload)` `P:14577-14586` | `clipPreviewThenSave` `P:14607` (`preview_clip_name`), after a 350 ms debounce | Same route | Like `ladderRequest` | - | Record panel, clip-name composer |
| The port's `/api/config` save | `P:18999-19003` | `/api/config` | Throws `failure` with `failure.payload = payload` | - | Config card |
| Listen poll | `setControlsListening` `P:18680-18720`: `setInterval(..., 300)` calling `controlsCall({cmd:"controls_last_input"})` | Controls rows | Third timer; `let controlsListenTimer/Seq` at module level `P:18672-18673`; no in-flight guard | - | Controls panel |

### Stores beside `state`

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `controlsState` (18 fields) `P:16633-16652`; `controlsChipLines` `P:16799`, `controlsSeparateTurns` `P:16882`, `controlsReplaced` `P:17253` | `loadControls` `P:18325-18360` from `get_controls` and `list_actions`; editors | 165 `controlsState.` references | Events | `apertar-hardware.conf` via `set_controls` | Controls panel, Hardware card (Config), Remote controls card |
| Remote controls card `P:4569-4580` | `renderRemoteControls` `P:18117`; buttons `buildRemoteButton` `P:18065-18112` (pointer capture, 450 ms delay, 140 ms repeat) | `test_input` | Bootstrap loop inside `installInteractions` `P:20940-20949`: `loadControls` every 5 s until `controlsState.model`; the timer is not stored | - | **Main page**, under Camera settings |
| `bootConfig` (11 fields) `P:19943-19955`; `BOOT_CONFIG_*` constants `P:19956-19960` | `loadBootConfig` `P:20265` from `/api/boot-config` | 66 `bootConfig.` references; listeners in `installBootConfigInteractions` `P:20624-20678`, **called from inside `installInteractions`** `P:20923` | Events | `/boot/firmware/config.txt` (boot-config-helpers theme) | System panel, Boot Config card |
| `clipUi` (20 fields) `P:14491-14495`; `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO` `P:14457-14490` | Composer handlers; `clipPreviewThenSave` | 92 `clipUi.` references | Events; 350 ms debounce timer `clipUi.saveTimer` | `camera_settings.conf` via `set_clip_name_template` | Record panel |
| `settingsSearch` `P:10184` | Search field, MutationObserver | 17 references | Events | none | Settings search |
| `state.ladderServer` `P:6674`, filled by `applyModeLadder` `P:8034-8045` | `get_mode_ladder` | Ladder editor; `imx585ClassRows` `P:8955-8968` (main-page resolution and crop pills); fps pill sub-labels `P:15912` | Fetched from `renderModeLadder` | `mode_ladder.conf` | Modes panel; main-page resolution pills. A mono IMX585 gets its sizes only from the pool: without it, `imx585ClassRows` returns the running size only (`P:8961-8964`) and `imx585BaseResolutionOptions` hides families without rows (`P:9020-9028`) |
| `state.pb` (22 keys, nested) `P:6723-6728`, and `state.pb.viewer` (about 40 fields incl. a `lanes` array, built by `pbvNewState`, dropped on close `P:12772`, `P:12862`) | 70 `pb*`/`pbv*` functions `P:11685-12940` | 144 `state.pb` references | Events; `requestAnimationFrame` tick; `v.awakeTimer` keep-awake `user_activity` fetch `P:12504-12509` | none (listing from `/api/media`) | Clip Browser and Clip Viewer overlay |

### Parts in the touch-UI look

| Part | Where | Upstream part it stands beside |
| --- | --- | --- |
| Overlay `#playbackOverlay`, eyebrow "PLAYBACK", `h1.pb-h1` "Clip Browser" | `P:6345-6491` | `#mediaBrowserOverlay`, folder icon, `h2.section-title`, one-line copy `U:3979-3991` |
| Refresh / Back `.pb-top-button` with inline SVG (2 SVGs in the header: `P:6355`, `P:6371`) | `P:6354-6373`, CSS `P:2061-2094` | `secondary-button#refreshMediaBrowserButton` "Refresh Media", **text only** `U:4008`; `icon-button settings-back-button#closeMediaBrowserButton` `U:3993-3995` |
| SHOW pop-up `.pb-show-button` + `.pb-menu` (cyan active) | `P:6358-6369`, CSS `P:2086-2140` | Visible `#mediaBrowserFilters` row of `.media-filter-button`, white active `U:3999-4004`, CSS `U:1224-1242` |
| Sort chip `.pb-chip#pbSortButton` | `P:6380`, CSS `P:2167` | `select.settings-select.media-sort-select#mediaBrowserSortSelect` `U:4009-4012`, CSS `U:1244-1253` |
| Selection actions without Clear | `P:6382-6386` | Select All, Clear, Download Selected, Delete Selected `U:4019-4022` |
| Remove modal `#pbRemoveScrim` `role=alertdialog` | `P:6475-6486`, open/close `P:12036-12052`, `P:12108`, guards `P:10137`, `P:12966`, `P:20705` | `window.confirm` `U:10434` |
| Browser history | `history.pushState` `P:10129`, `P:12777`; `popstate` `P:20708` | none upstream |
| Viewer `.pbv-circle`, `.pbv-icon-button`, `.pbv-info-button`; 4 SVGs in markup (`P:6401`, `6433`, `6449`, `6455`), 1 in JS `P:11833` | `P:6400-6456`, CSS `P:2743-2775` | `.icon-button` `U:194-215`, button variants `U:1632-1706`, PNGs in `src/web/icons` |
| Hold-to-repeat | frame step `pbvRepeat` `P:12718-12729` (no pointer capture, 400 ms / 90 ms); knob arrows `P:18086-18110` (pointer capture `P:18102`, 450 ms / 140 ms) | none upstream |
| White dropdowns `[data-panel="controls"] .settings-select, #hardwareDevices .settings-select` + dark exception `.controls-pin-select`; tokens `--select-bg/--select-fg` | CSS `P:3484-3559`, `P:35-36`; class added `P:17388` | One `.settings-select` look `U:1532-1555` |
| Inline SVG elsewhere | Mode Ladder `ladderIcons` `P:7644-7650`; search magnifier `P:4733` | 0 `<svg>` in U (WEB-9) |
| `body.pb-open` declared twice | `P:69`, `P:1980` | `body.media-browser-open` `U:66` |

Measured in `--simulate` (`/home/user/build/work-nolc/apertar-core`): `/api/state` carries the buffer and pre-roll fields under `system.*`; `/api/buffer` carries the same keys flat plus `recording`. The replies of `get_controls`, `list_actions`, `controls_history`, `controls_last_input`, `get_mode_ladder`, `preview_clip_name` carry no key that `mergeCameraStateFields` copies (their top-level keys were listed).

## How original Apertar does this kind of thing

| Precedent | Where `@upstream-1.6.0` | What it shows |
| --- | --- | --- |
| One store | `U:4204-4266` | `const state = {` with flat fields: `<x>Timer`, `<x>InFlight`, `<x>Dirty`, library payloads. No nested object. Even a dozen WebGL handles that live and die together are flat `previewProcessing*` fields (`U:4255-4266`) (WEB-12) |
| One loop, one renderer | `U:11609` `window.setInterval(() => fetchState(true), 1000)`; `fetchState` -> `renderSnapshot` `U:9327`; REC pill classes in `renderSnapshot` `U:9794-9802` | WEB-7, WEB-13 |
| A small draw function outside `renderSnapshot`, driven by a second timer, reading only `state.snapshot` | `updateTimecodeDisplay` `U:9168-9216`, called from `updateLiveReadouts` `U:9219-9222`, run by `startLiveReadoutLoop` (`requestAnimationFrame`) `U:9224-9238`, started `U:11608` | The shape of `renderRecordingStatus`. Upstream has no second **network** poll |
| Event toasts from a snapshot comparison | `U:9328-9333` | `if (snapshot.recording_error && snapshot.recording_error !== previousError) showToast(...)`; no "seen" flags |
| One command door | `sendCommand` `U:9109-9145`; handlers `try { await sendCommand(...) } catch (error) { showToast(error.message, true) }` | WEB-3, WEB-14 |
| A user-started read through the same door, its list in a flat field | `refreshAudioCaptureCapabilities` `U:11100-11113` -> `state.audioCaptureModes`; started on panel open `U:6162`, never from a render | Clip preview and Controls reads take this shape |
| Raw `fetch` for background traffic only | `user_activity` `U:11509-11513` | Listen poll, viewer keep-awake and the render-driven ladder read take this shape |
| Library editor state | Config editor `U:10265-10359`: `state.configDirty`, `configFetchInFlight`, `configSaveInFlight` | Controls and Boot Config cards |
| Panel data loads with the panel | `setSettingsPanel` `U:6149-6166` | Remote controls in the Controls panel |
| Retry timer stored on `state` | `state.previewRetryTimer` `U:8561`, `U:8578` | The Remote controls loader if it stays on the main page |
| Listeners | `installInteractions` `U:11348-11603`, plus a second feature installer `installPreviewStream` `U:8566`, called beside it `U:11606-11607` | A feature installer is upstream's shape; `installBootConfigInteractions` stays |
| Clip Browser parts | Markup `U:3979-4030`; CSS `U:1156-1253`; state `U:4237-4243`; `renderMediaLibrary` `U:7669`, `fetchMediaLibrary` `U:10361`, `setMediaBrowserOpen` `U:6139` | Names, ids and parts the Clip Browser returns to |
| Destructive asks | `window.confirm` `U:10307`, `U:10385`, `U:10434`, `U:10672`, `U:11266-11337` (8 confirms) | WEB-21 |
| Buttons and selection | `.icon-button` `U:194-215`; `.primary-/.secondary-/.danger-button` `U:1632-1706`; white active `U:1238-1242`; `.media-select-control.selected` `U:1294-1330` | WEB-19 |
| Icons | PNGs from `src/web/icons` via `GET /icons/<name>`, 0 `<svg>` | WEB-9 |
| `.hidden` class | `U:790-803`; the one property use is `option.hidden` on an `<option>` `U:9526` | No `hidden` attribute elsewhere |

No upstream precedent: a second network poll, browser history, a modal dialog, hold-to-repeat, a mutation observer, a client-side playback engine. Those are new ground (section below).

## The target

Core is untouched: who owns each value in Core and which command sets it stay as today.

| Value | Owner and setter (unchanged) | Before (page) | After (page) |
| --- | --- | --- | --- |
| Buffer fill, safety stop, stop percent, flush-discarded, pre-roll active/fps | Core atomics; `record_start`, `record_stop`, `set_buffer_mode` | `frameBufferBar.*`, plus `state.snapshot.*` written by two timers | `state.snapshot.buffer_fill`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `storage_preroll_active`, `storage_preroll_fps`: from `/api/state` via `renderSnapshot`, and from `/api/buffer` via `applyBufferSnapshotPatch` -> `mergeCameraStateFields` (which gains `buffer_fill` and `buffer_flush_discarded`) |
| One freshness rule | page | Three 1000 ms windows | While `state.bufferPollTimer` runs, `renderSnapshot` keeps `buffer_fill` from the previous `state.snapshot` (the poll owns the fill; `/api/state`'s fill can be seconds old after a drain) |
| "Frames still queued" from `/api/buffer` | Core gauge | `frameBufferBar.recording` | `state.snapshot.buffer_recording`, never written over `snapshot.recording` (the merge copies `recording`, `P:13889`, so the patch renames it first) |
| Buffer poll bookkeeping | page | `frameBufferBar.timer/inFlight/prerollUntilMs/...` | `state.bufferPollTimer`, `state.bufferPollInFlight`, `state.prerollPollUntilMs` |
| REC pill classes and text | page | `renderSnapshot` + `applyPrerollPill` + `applyFrameBufferPillClasses` | `renderRecordingStatus(snapshot)`, called by `renderSnapshot` and by `fetchBufferState` |
| Buffer toasts | page | `noteBufferSafetyStop` with seen flags | Previous-vs-new comparison, like `recording_error`; the discard toast only when a previous snapshot exists |
| Controls model, edits, catalog, history, listen | Core `get_controls`/`set_controls`, `apertar-hardware.conf` | `controlsState.*`, 3 module sets/maps, 2 module lets | `state.controlsModel`, `controlsRevision`, `controlsPeripherals`, `controlsCatalog`, `controlsEdits`, `controlsButtons`, `controlsRemoved`, `controlsAdded`, `hardwareEdits`, `controlsBuses`, `controlsScans`, `controlsDpiLines`, `controlsGpioChips`, `controlsApply`, `controlsHistory`, `controlsLoadInFlight`, `controlsSaveInFlight`, `controlsListening`, `controlsListenTimer`, `controlsListenSeq`, `controlsListenInFlight`, `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced`. Label tables stay where they are |
| Boot Config card | Core `/api/boot-config` (boot-config-helpers theme) | `bootConfig.*` | `state.bootConfigPayload`, `bootConfigForm`, `bootConfigFetchInFlight`, `bootConfigSaveInFlight`, `bootConfigRebootWaiting`, `bootConfigSavedPendingReboot`, `bootConfigReview` (+ editor fields if boot-config-helpers keeps Edit file). `installBootConfigInteractions` stays |
| Clip-name composer | Core `set_clip_name_template`, `camera_settings.conf` | `clipUi.*`, `CLIP_*` | `state.clipName*`; `clipNamePresets`, `clipNameTokenGroups`, `clipNameTokenInfo`, `clipNameDefaultTemplate` in place |
| Settings search | page | `settingsSearch.*` | `state.settingsSearchActive`, `settingsSearchObserver`, `settingsSearchTimer`, `settingsSearchApplying` |
| Clip Browser | Core `/api/media*` routes | `state.pb.*` (22 keys) | Upstream fields `state.mediaLibraryPayload`, `mediaLibrary`, `mediaBrowserFilter`, `mediaBrowserSort`, `mediaSelection`, `mediaFetchInFlight`, plus flat `mediaFetchQueued`, `mediaSelecting`, `mediaThumbCache`, `mediaThumbQueue`, `mediaThumbsInFlight`, `mediaThumbObserver`, `mediaHold`, `mediaSnapshotHold`, `mediaError`, `mediaRemoving`, `mediaLastOpenedKey`, `mediaBrowserPage`, `previewPausedForPlayback` (declared); `mediaBrowserHistoryPushed`, `clipViewerHistoryPushed`, `mediaBrowserIgnorePop` until commit 22 |
| Clip Viewer | page | `state.pb.viewer` | `state.clipViewer`, one object per open clip (owner decision 5) |
| IMX585 resolution pills | Core class tables; `set_resolution` | `state.ladderServer.pool`, else `imx585ClassModes` | Unchanged here (camera-modes theme) |
| Command doors | Core `handleCommand` | `sendCommand`, `controlsCall`, `ladderRequest`, `clipRawCommand` | `sendCommand` (its error carries `error.payload`, the name `P:19002` already uses); raw `fetch` for `controls_last_input` (Listen) and `user_activity` (viewer keep-awake); `ladderRequest` stays for the render-driven `get_mode_ladder` until camera-modes moves that fetch |
| Parts | - | `.pb-*`, `.pbv-*`, SVG, modal, history, hold-to-repeat, white selects | Upstream header, ids and CSS (`U:3979-4022`, `U:1156-1253`); `.media-browser-*`, `.clip-viewer-*` for the port's grid and viewer; buttons from `.icon-button`/`.primary-/.secondary-/.danger-button`; `/icons/*.png`; `window.confirm`; one `.settings-select`; `.hidden` |
| Remote controls | Core `test_input` | Main-page card, loaded at start, 5 s untracked retry | Owner decision 3: a `settings-card` in Controls loaded by `setSettingsPanel("controls")` (commit 24), or the main-page card with `state.controlsRetryTimer` (commit 25) |

What reaches the touch UI does not change: it reads the socket (`get_state`, events `buffer`, `settings`), not the page. No reply field, file key or command changes, so requirement 4 (files on existing cameras) has nothing to take over. A stock camera and the owner's rig see the same page behaviour as today, except where an owner option (22-25) is taken.

## Commit plan

All commits: repo Apertar-Core, file `src/web/WebControlPage.cpp` only, subject prefix `web:`. Order: the camera-critical pill first, then the command doors, then the stores, then the Clip Browser parts (deletions before renames, so the renames touch fewer lines), then the small parts. Commits 22-25 are leaves: nothing depends on them, so an owner "keep it" drops the commit and nothing else.

**Standard check here (every commit):**
1. `/home/user/build/bin/check_core.sh /home/user/wt/core-work work both tests`: both builds and the 17 host tests PASS.
2. `/home/user/build/bin/smoke_core.sh /home/user/build/work-nolc/apertar-core 18741 > after.txt`, then `diff <(grep -v '^== GET / ' before.txt) <(grep -v '^== GET / ' after.txt)`: empty. The `GET /` line prints the page's byte count (`smoke_core.sh:41`) and changes on every page commit.
3. Extract the page script from `curl -s http://127.0.0.1:18741/` (text between `<script>` and `</script>`) and run `node --check` on it.
4. Node Playwright (`/opt/node22/lib/node_modules/playwright`) with `/usr/bin/google-chrome` headless against `--simulate`: load `/`, open every settings panel and the Clip Browser, fail on any `pageerror` or `unhandledrejection`, take a screenshot.
5. The grep named in the commit gives the stated count.

**What a Pi adds in general:** the buffer and pre-roll paths need a real raw take (`--simulate` reports `buffer_mode: "none"`). The rest is page logic that `--simulate` drives fully. Every change runs in the client's browser; Core work per request and request rates stay as today, so there is no Pi-model difference in Core (CM5, Pi 5, Pi 4, CM4 alike).

### 1. web: the recording pill is drawn in one function, renderRecordingStatus

- Functions: `renderSnapshot`. Moves the `#recordingStatus` text block `P:15388-15392` and the pill/dot class block `P:15752-15768` (with its `updateFrameBufferBar` call) into `function renderRecordingStatus(snapshot)`, next to `renderSnapshot`. `renderSnapshot` calls it at the old place. The record button block `P:15769-15772` stays in `renderSnapshot`. Pure extraction.
- Precedent: `updateTimecodeDisplay` `U:9168-9216`, a small draw function that reads only `state.snapshot` and is run by a second timer (`U:9219-9238`). The rest of `renderSnapshot` stays whole (WEB-24).
- Lines: -30 +36.
- Check here: standard; screenshot of the pill READY / NO MEDIA in `--simulate` identical to before (pixel diff).
- Pi: nothing new.
- Depends on: none.

### 2. web: the buffer poll merges its reply into the snapshot and redraws the pill

- Deletes `const frameBufferBar` `P:16419-16421`. Adds to the `state` literal only the fields that survive: `bufferPollTimer`, `bufferPollInFlight`, `prerollPollUntilMs`, and, until commit 3, `bufferStopSeen`, `bufferDiscardSeen: -1`.
- `pollFrameBufferBar` is renamed `fetchBufferState` (async, `try/catch/finally`, `state.bufferPollInFlight`, the 800 ms `AbortController` kept). New `applyBufferSnapshotPatch(payload)`, about 8 lines: move `payload.recording` to `payload.buffer_recording` and delete `recording` (the merge would copy it over `snapshot.recording`, `P:13889`; `/api/buffer` says `false` during a safety stop, `App:8428`, while Core still refuses some controls), then `mergeCameraStateFields(state.snapshot, payload)`, then `renderRecordingStatus(state.snapshot)` and `showPrerollFpsText`.
- `mergeCameraStateFields` gains 4 lines: `buffer_fill` (clamped 0..1) and `buffer_flush_discarded`, beside the existing `buffer_*` lines `P:13841-13848`. Without them the bar would not move at 4 Hz.
- One freshness rule replaces the three windows `P:16553`, `P:16560-16562`, `P:16575-16578`: in `renderSnapshot`, right after the `system.*` lift `P:15215-15221`: `if (state.bufferPollTimer && state.snapshot && isFiniteNumber(state.snapshot.buffer_fill)) snapshot.buffer_fill = state.snapshot.buffer_fill;`. The same condition keeps the buffer toasts with the poll (`noteBufferSafetyStop` is called from `renderSnapshot` only while no poll runs). This is the old `P:16560` rule, now keyed on the timer.
- `noteBufferSafetyStop` stays (commit 3 removes it); it reads and writes `state.bufferStopSeen`/`bufferDiscardSeen` and no longer writes a safety flag.
- Deletes `applyPrerollPill` `P:16441-16456`, `applyFrameBufferPillClasses` `P:16473-16489`, the READY/PRE-ROLL label rewrites, and the direct `state.snapshot.storage_preroll_*` writes `P:16505-16512`.
- `renderRecordingStatus` reads only `snapshot`: `pillRecording = isRecording && !snapshot.buffer_safety_stop`; `buffer-drain` = bar active and `buffer_safety_stop` and `buffer_fill > 0`; `preroll` = `storage_preroll_active && !pillRecording && !buffer_recording`. The 5 outside readers (`P:14381`, `15389`, `15757-15759`, `15917`, `19272`) read `state.snapshot.buffer_safety_stop` and `storage_preroll_active`.
- Lines: -150 +60.
- Check here: standard; `grep -cE 'frameBufferBar|applyPrerollPill|applyFrameBufferPillClasses|fillAtMs|prerollAtMs'` = 0. Playwright with `page.route` replies, five scenes: (a) `/api/state` recording, `system.buffer_mode: "ram"`, `ui.frame_buffer_bar_enabled: true`, `/api/buffer` fill 0.4: pill REC red, `--buffer-fill: 40.0%`; (b) `/api/buffer` `buffer_safety_stop: true`, fill 0.3, `/api/state` held (the route never answers): pill READY green with `buffer-drain`, record button enabled; (c) `storage_preroll_active: true`, not recording: PRE-ROLL blue, FPS badge shows `storage_preroll_fps`; (d) all false: READY; (e) the poll says 0.3, then a late `/api/state` says `system.buffer_fill: 0.9`: bar stays 30 %. Scenes (a) and (b) again with `ui.frame_buffer_bar_enabled: false`: pill red, then READY green at the stop, no bar.
- Pi (CM5 + CFexpress, then a Pi 4 + SD card, the slow drain): RAM buffer mode, cDNG 16-bit 4K at the highest fps. Run twice, with the frame buffer bar on and off (Settings > Record). Beside the page run `while :; do curl -s http://<pi>:8000/api/buffer | jq -c '{buffer_fill,buffer_safety_stop,buffer_flush_discarded,recording}'; sleep 0.25; done`. Record until the safety stop. Look for: the bar fills smoothly (bar on); the pill turns READY green within 0.5 s of `buffer_safety_stop: true`; the bar never jumps back up when `/api/state` answers after the drain; one toast. Then press REC during the flush: one flush-discard toast, and a new take starts. Pre-roll: press the pre-roll button: the PRE-ROLL pill appears within half a second.
- Depends on: 1. Preroll theme: if it renames `storage_preroll_*` fields, rebase; after this commit the pill reads them in one place.

### 3. web: buffer toasts and the buffer poll timer follow the snapshot

- Deletes `noteBufferSafetyStop`, `state.bufferStopSeen`, `state.bufferDiscardSeen` and the toast half of the timer rule from commit 2. Adds one function `noteBufferEvents(previous, next)` (6 lines), called in `renderSnapshot` after the `system.*` lift with `state.snapshot` as `previous`, and in `applyBufferSnapshotPatch` before the merge. Shaped like `U:9331-9333`: `if (next.buffer_safety_stop && !(previous && previous.buffer_safety_stop)) showToast(...)` (toasts on page load during a stop, as today); `if (previous && next.buffer_flush_discarded > 0 && next.buffer_flush_discarded !== previous.buffer_flush_discarded) showToast(...)` (no toast on load, as `discardedSeen: -1` does today; the count stays in Core until the next safety stop, `App:247-250`). Both writers share `state.snapshot`, so a stop seen by the poll does not toast again when `/api/state` answers.
- Replaces `startFrameBufferTimer`, `stopFrameBufferPolling`, `prerollPollWanted` and the start/stop sites with one `updateBufferPolling(snapshot)`, called at the end of `renderRecordingStatus`: poll while (queue mode and (`recording` or `buffer_safety_stop` or (bar active and `buffer_fill > 0`))) or `storage_preroll_active` or `performance.now() < state.prerollPollUntilMs`. This is today's rule (`P:16533-16538`, `P:16566-16570`, `P:16586-16587`) in one place. `notePrerollRequested` sets `state.prerollPollUntilMs` and calls it.
- Lines: -60 +35.
- Check here: standard; `grep -cE 'noteBufferSafetyStop|stopSeen|discardedSeen'` = 0. Playwright: scene (b) of commit 2 for 3 s: exactly one toast; `buffer_flush_discarded` 0 -> 12: one toast; page loaded with `buffer_flush_discarded: 12` already set: no toast; after all false, `state.bufferPollTimer` = 0 within 250 ms (`page.evaluate`).
- Pi: the commit 2 steps; also leave the page open idle for 5 min and check in the browser network tab that `/api/buffer` requests stop.
- Depends on: 2.

### 4. web: Controls and Hardware commands go through sendCommand

- `sendCommand`: `const error = new Error(result.error || "Command failed."); error.payload = result; throw error;` (+2; the name the port's config save uses, `P:19002`). Callers: `loadControls`, `saveControls`, `saveHardware`, `undoControls`, `loadControlsHistory`, `loadConfigVersion`, `checkConfigFile`, the Scan handler, the three Test handlers, `buildRemoteButton`'s `fire` (returns `true`/`false` from try/catch, so the repeat still stops on a refusal).
- Each user action: `try { const result = await sendCommand(...) } catch (error) { showControlsMessage(error.message, error.payload && error.payload.issues, false) } finally { <flag> = false }`. Saves read `error.payload.issues` / `error.payload.code`. Scan resets "Scanning..." in `finally`. Undo sets the save flag.
- The Listen poll stays a raw `fetch` (background traffic like `user_activity`; through `sendCommand` it would render twice, schedule `/api/state` and push `deferFetchUntilMs` every 300 ms), now inside `try/catch` with `state.controlsListenInFlight`.
- Deletes `controlsCall` `P:16699-16705`.
- Lines: -45 +80 (try/catch at 15 sites).
- Check here: standard; `grep -c controlsCall` = 0. Playwright: open Controls; `page.route("/api/command")` fails `scan_i2c` once: the Scan button is usable again, a toast shows, no unhandled rejection. Save with a stale revision shows Core's "The file changed since you loaded it..." (reproduced in `--simulate` with `set_controls base=x`).
- Pi: Controls > Listen, press a GPIO button: its row lights up. Remote controls: one tap on Record starts a take.
- Depends on: none. Command-plane theme: if replies gain machine codes, `error.payload.code` carries them.

### 5. web: the clip-name preview goes through sendCommand

- `clipPreviewThenSave` calls `sendCommand({cmd: "preview_clip_name", value})`. Deletes `clipRawCommand` `P:14577-14586`. Precedent: `audio_capabilities` through `sendCommand` `U:11109`, a user-started read.
- Cost: each preview renders twice from the unchanged snapshot and schedules one `/api/state` 140 ms later; REC is gated for the request's duration (tens of ms; the composer is disabled while recording, `P:14569`).
- `ladderRequest` stays: its one caller, `get_mode_ladder`, is started from a render (`P:8395-8400`), not by the operator, and through `sendCommand` it would gate REC and drop `/api/state` replies while it waits on CC `mutex_` (`CC:11041`). It goes when camera-modes moves the fetch to panel open (WCP-04-F3) together with the pool question (WCP-04-F1).
- Lines: -12 +1.
- Check here: standard; `grep -c clipRawCommand` = 0; Playwright: Record panel composer shows the example name after a drag.
- Pi: nothing new.
- Depends on: 4 (the `error.payload` line).

### 6. web: the Controls page keeps its state in state

- Moves the 18 fields of `controlsState` to flat `state.controls*` fields (names in the target table; `settingEdits` -> `hardwareEdits`, `loading`/`saving` -> `controlsLoadInFlight`/`controlsSaveInFlight`). Deletes `const controlsState`. The label tables stay where they are (upstream keeps meta tables beside the code that uses them too: `favoriteItemMeta` `U:4128`, `settingsPanelMeta` `U:4165`). Mechanical: one `sed` map, listed in the commit body.
- Lines: -22 +20 declarations; about 165 lines edited in place.
- Check here: standard; `grep -c controlsState` = 0; Playwright: Controls renders the same rows as before (DOM text diff of the Controls panel).
- Pi: nothing new.
- Depends on: 4.

### 7. web: the Controls page's sets, maps and Listen timer live in state

- Moves `controlsChipLines`, `controlsSeparateTurns`, `controlsReplaced` (`P:16799`, `16882`, `17253`), `let controlsListenTimer`, `let controlsListenSeq` (`P:18672-18673`) to `state`. Deletes the 5 module-level declarations.
- Lines: -5 +5; about 25 lines edited.
- Check here: standard; `grep -nE '^    (let|const) controls(ChipLines|SeparateTurns|Replaced|Listen)'` = 0.
- Pi: nothing.
- Depends on: 6.

### 8. web: the Boot Config card keeps its state in state

- Moves `bootConfig.*` to `state.bootConfig*` (target table); renames `BOOT_CONFIG_TOGGLES`, `BOOT_CONFIG_MANAGED` to `bootConfigToggles`, `bootConfigManaged` in place. Deletes `const bootConfig`. `installBootConfigInteractions` stays: it is called from inside `installInteractions` (`P:20923`), and upstream has a feature installer of its own (`installPreviewStream` `U:8566`).
- Lines: -16 +12 declarations; about 70 lines edited.
- Check here: standard; `grep -cE '\bbootConfig\.|BOOT_CONFIG_'` = 0; Playwright: the System panel shows the Boot Config card filled from `/api/boot-config` (`--simulate` answers it).
- Pi: nothing new (nothing new is written).
- Depends on: boot-config-helpers theme first (it moves the route and may delete Edit file, which removes `text`, `previewState`, `editorMarks`, `editorTimer`). Move only the fields that survive.

### 9. web: the clip-name composer keeps its state in state

- Moves `clipUi.*` to `state.clipName*` (`clipNameItems`, `clipNameSavedTemplate`, `clipNameDirty`, `clipNameSaveTimer`, `clipNameSeq`, `clipNameDragSource`, `clipNameStatusText`, ...); renames `CLIP_PRESETS`, `CLIP_TOKEN_GROUPS`, `CLIP_TOKEN_INFO`, `CLIP_DEFAULT_TEMPLATE` to camelCase in place. Deletes `const clipUi`.
- Lines: -6 +18 declarations; about 92 lines edited.
- Check here: standard; `grep -cE 'clipUi|CLIP_'` = 0; Playwright: the composer saves `{format}_{date}_{clip}`.
- Pi: nothing.
- Depends on: 5.

### 10. web: settings search keeps its state in state

- Moves `settingsSearch.*` to `state.settingsSearchActive`, `settingsSearchObserver`, `settingsSearchTimer`, `settingsSearchApplying`. Deletes `const settingsSearch` `P:10184`.
- Lines: -2 +5; about 17 lines edited.
- Check here: standard; `grep -c 'settingsSearch\.'` = 0; Playwright: type "iso" in settings search, the ISO unit stays visible.
- Pi: nothing.
- Depends on: none.

### 11. web: Remove in the Clip Browser asks with window.confirm

- `pbOpenRemoveDialog` becomes `if (!window.confirm("Remove " + n + " clips? This cannot be undone.")) return;` inside `pbRemoveSelected` (one clip: "Remove <name>? This cannot be undone."). "Removing..." goes to the status line `#pbStatus`. Deletes the `#pbRemoveScrim` markup `P:6475-6486`, `.pb-scrim`/`.pb-dialog*` CSS, the open/close code `P:12036-12052`, `P:12108`, the scrim guards `P:10137`, `P:12966`, `P:20705`, and `pb.removeTargets`. WEB-21 settles the wording shape (8 upstream confirms), so this is no owner question.
- Lines: -95 +10.
- Check here: standard; `grep -c pbRemoveScrim` = 0; Playwright with `page.on("dialog", d => d.accept())`: put a folder in the `--simulate` media dir, select it, Remove: it is gone; with `d.dismiss()`: it stays.
- Pi: nothing.
- Depends on: none.

### 12. web: the Clip Browser header uses upstream's title, Back, Refresh, filter row and sort select

- Markup: the header and toolbar become a copy of `U:3981-4012` with its ids: folder icon, `h2.section-title` "Clip Browser", the one-line copy, `icon-button settings-back-button#closeMediaBrowserButton`, `#mediaBrowserFilters` with four `.media-filter-button[data-media-filter]`, `secondary-button#refreshMediaBrowserButton` "Refresh Media" (text only, as `U:4008`), `select.settings-select.media-sort-select#mediaBrowserSortSelect`. The count pill keeps `#pbCount` until commit 15. The port's grid, sheet and selection actions stay.
- CSS: re-adds upstream's header, toolbar, filter and sort rules `U:1156-1253` verbatim (the port deleted every `.media-browser-*`, `.media-filter-button`, `.media-sort-select` rule: 0 matches in P). Deletes `.pb-eyebrow`, `.pb-h1`, `.pb-top-button`, `.pb-show-*`, `.pb-menu*`, `.pb-chip` and their media-query copies (`P:2047-2178`, `P:2475-2500` in part).
- Functions: `pbSetFilter` reads `data-media-filter`; `pbSetShowMenu` and its document click handler deleted; sort reads the select's `change`; listeners use the upstream ids. The 2 header SVGs (`P:6355`, `P:6371`) go.
- Lines: -220 +100 (about 95 of the adds are upstream's CSS).
- Check here: standard; `grep -cE 'pb-show|pb-menu|pb-chip|pb-top-button'` = 0; Playwright: the filter row switches Clips/Stills/Timelapse/Audio; the sort select reorders; screenshots at 1280 and 390 px width.
- Pi: nothing.
- Depends on: none.

### 13. web: the Clip Browser has a Clear button beside Select All

- Adds `secondary-button media-select-button#clearMediaSelectionButton` "Clear" (as `U:4020`) to the selection actions; its click empties the selection and leaves selection mode. Fixes WCP-03-F3 in part.
- Lines: -0 +8.
- Check here: standard; Playwright: select two clips, Clear: the count shows 0 and the actions hide.
- Pi: nothing.
- Depends on: 12.

### 14. web: the Clip Viewer uses the page's buttons and /icons PNGs

- Markup: Back -> `icon-button settings-back-button`; Download -> `secondary-button` "Download"; Info -> `secondary-button` "Info"; previous/next clip and play keep their PNGs on `icon-button`; frame step -> `icon-button` with `/icons/previous.png` / `/icons/next.png` and `aria-label` "Previous frame"/"Next frame"; the card's selected check (SVG built in JS `P:11833`) -> a `media-select-control` element with `.selected` (`U:1294-1330`). Ids stay.
- Deletes CSS: `.pbv-circle*`, `.pbv-icon-button`, `.pbv-info-button` (`P:2398-2450` in part, `P:2657-2678`, `P:2743-2775`); 4 inline SVGs in markup, 1 in JS.
- Lines: -130 +35.
- Check here: standard; `grep -c '<svg'` = 6 (Mode Ladder 5 and search 1, gone in commit 20); Playwright: open a clip from the simulate media dir (a cDNG folder made by `tools/flatten_clip.py`, or a `.wav` for the audio path): Play, Pause, step, Info.
- Pi: open a 4K cDNG clip on a phone over Wi-Fi: play, step and scrub as before.
- Depends on: 12.

### 15. web: the Clip Browser's classes and ids use the media-browser and clip-viewer names

- Mechanical rename with a sed map in the commit body: `.pb-*` -> `.media-browser-*`, `.pbv-*` -> `.clip-viewer-*`, `body.pb-open` -> `body.media-browser-open` (declared once; the second rule `P:1980` deleted), ids `pb*` -> `mediaBrowser*`, `pbv*` -> `clipViewer*`, `#playbackOverlay` -> `#mediaBrowserOverlay`.
- Lines: about 620 lines edited, -4 +0.
- Check here: standard; `grep -cE '\.pbv?-|id="pbv?[A-Z]'` = 0; Playwright screenshots identical to commit 14's (pixel diff). Review: rerun the published sed map on the parent and diff against the commit (empty), instead of reading 620 lines.
- Pi: nothing.
- Depends on: 14. Owner decision 4.

### 16. web: the Clip Browser's state is flat on state under upstream names

- Moves `state.pb.*` to the flat fields in the target table; `state.pb.viewer` -> `state.clipViewer`; declares `previewPausedForPlayback` (WCP-06-F12). Deletes the nested `pb: {...}`.
- Lines: -5 +22 declarations; about 150 lines edited.
- Check here: standard; `grep -c 'state\.pb\b'` = 0; Playwright as commit 14.
- Pi: nothing.
- Depends on: 15. Owner decision 5 (if "flat": the viewer's 40 fields become `clipViewer*` on `state`, plus a reset in `closeClipViewer`; about +50 lines more).

### 17. web: the Clip Browser's upstream jobs have their upstream names again

- Renames `pbRender` -> `renderMediaLibrary`, `pbSorted` -> `sortedMediaItems`, `pbSelectedItems` -> `selectedMediaItems`, `pbToggle` -> `toggleMediaSelection`, `pbSetFilter` -> `setMediaBrowserFilter`, the sort setter -> `setMediaBrowserSort`, `pbDownloadSelected` -> `downloadSelectedMediaItems`, `pbRemoveSelected` -> `deleteSelectedMediaItems`, selection pruning -> `pruneMediaSelection`, select-all -> `selectAllVisibleMedia`.
- Lines: about 60 lines edited.
- Check here: standard; Playwright as commit 14.
- Pi: nothing.
- Depends on: 16.

### 18. web: the Clip Viewer's functions have verb-first names

- Renames the remaining `pb*`/`pbv*` functions and constants (map in the commit body), e.g. `pbBuildCard` -> `buildMediaCard`, `pbQueueThumb` -> `queueMediaThumbnail`, `pbvOpen` -> `openClipViewer`, `pbvClose` -> `closeClipViewer`, `pbvPlay` -> `playClip`, `pbvPause` -> `pauseClip`, `pbvStep` -> `stepClipFrame`, `pbvRepeat` -> `repeatClipFrameStep`, `pbvSeekTo` -> `seekClip`, `pbvFetchFrame` -> `fetchClipFrame`, `pbvDraw` -> `drawClipFrame`, `pbvNewState` -> `newClipViewerState`, `pbvInstall` -> `installClipViewerInteractions`, `pbvTimeline` -> `clipTimeline`; `pbFilters`, `pbvHoldText`, `pbvWidths` -> `mediaFilterLabels`, `clipHoldText`, `clipFrameWidths`.
- Lines: about 300 lines edited.
- Check here: standard; `grep -cE '\bpbv?[A-Z]\w*'` = 0; Playwright as commit 14.
- Pi: nothing.
- Depends on: 17.

### 19. web: dropdowns have one look on every panel

- Deletes CSS `P:3484-3559` except the used-pin grey rule (kept as `.settings-select option[data-used]`), the tokens `--select-bg/--select-fg` `P:35-36`, and the class `controls-pin-select` at `P:17388`. Fixes WCP-02-F7 (a new GPIO-in row got a white pin dropdown).
- Lines: -80 +3.
- Check here: standard; `grep -cE 'select-bg|select-fg|controls-pin-select'` = 0; Playwright screenshots of Controls and Config > Hardware.
- Pi: nothing.
- Depends on: none. Owner decision 6.

### 20. web: the Mode Ladder and settings search draw no inline SVG

- Replaces `ladderIcons` `P:7644-7650` (handle, up, down, remove, chevron) with text in `secondary-button`s ("Up", "Down", "Remove"; the handle and chevron become the row itself and a `.hidden` toggle), and drops the search field's magnifier SVG `P:4733` (upstream fields carry no icon).
- Lines: -12 +10.
- Check here: standard; `grep -c '<svg'` = 0 (WEB-9); Playwright: ladder rows move up and down.
- Pi: nothing.
- Depends on: 14. Camera-modes theme: if it rewrites the ladder editor (WCP-04-F5) first, only the search icon is left.

### 21. web: hidden elements use the .hidden class

- Replaces 25 of the 26 `element.hidden = x` with `element.classList.toggle("hidden", x)` and the `hidden` attributes in markup (about 17) with `class="... hidden"`; deletes the 5 `[hidden]` CSS patches. Keeps upstream's own `option.hidden` line `P:15437` (= `U:9526`; on an `<option>` a class does not hide in every browser).
- Lines: -45 +35.
- Check here: standard; `grep -c '\.hidden = '` = 1, `grep -c '\[hidden\]'` = 0; Playwright: every panel opens with the same visible text as before (text diff).
- Pi: nothing.
- Depends on: 8, 9, and the preroll theme (its rows `P:15830-15860`) and boot-config-helpers theme (its card `P:20095-20554`) landed first.

### 22. web: the Clip Browser adds no browser history entries (leaf, owner decision 1)

- `setMediaBrowserOpen(open)` loses `fromHistory`; `openClipViewer` loses its push; `closeClipViewer` loses its pop. Deletes both `history.pushState` (`P:10129`, `P:12777`), the `popstate` listener `P:20708-...`, `state.mediaBrowserHistoryPushed`, `clipViewerHistoryPushed`, `mediaBrowserIgnorePop`. The Back buttons and Escape close as today.
- Lines: -30 +3.
- Check here: standard; `grep -cE 'pushState|popstate'` = 0; Playwright: open the browser, open a clip, Back, Back: overlay closed, `history.length` unchanged.
- Pi: nothing.
- Depends on: 18 (it uses the new names). Nothing depends on it.

### 23. web: frame step and knob arrows send one step per click (leaf, owner decision 2)

- Deletes `repeatClipFrameStep` (today `pbvRepeat` `P:12718-12729`) and its two calls (a click calls `stepClipFrame`; the left/right keys already repeat by key auto-repeat in the keydown handler `P:12961`); deletes the `repeat` branch of `buildRemoteButton` `P:18086-18110` (pointer capture, 450 ms delay, 140 ms interval).
- Lines: -45 +4.
- Check here: standard; `grep -c repeatClipFrameStep` = 0, and `setPointerCapture` remains only in the scrub (`P:12678`) and the composer drag (`P:14730`): count = 2. Playwright: one click = one `test_input` (count requests) and one frame.
- Pi: turn ISO up from the Remote controls pad: one step per click.
- Depends on: 18. Nothing depends on it.

### 24. web: Remote controls is a card in the Controls panel (leaf, owner decision 3a)

- Moves the card `P:4569-4580` into the Controls `settings-panel` as `div.settings-card` > `settings-card-head` > `h3.settings-card-title` "Remote controls" + a one-sentence `p.settings-card-copy`. Data: already loaded by `setSettingsPanel("controls")` `P:10166`. Deletes the main-page card, the bootstrap loop `P:20940-20949`, and the `#remoteControlsRows .pill-button` override `P:3420` if the pills render through `pill-grid`.
- Lines: -30 +18.
- Check here: standard; Playwright: the main page has the four upstream cards; no `get_controls` request before Controls opens (`page.on("request")`); Controls shows the pad; one click on a button pill sends one `test_input`.
- Pi: from the Controls panel, press "Record" on the pad: the camera records as with the hardware button.
- Depends on: 7. Nothing depends on it. Not with 25.

### 25. web: the Remote controls loader keeps its retry timer in state (leaf, owner decision 3b)

- For the case the card stays on the main page: the 5 s retry `P:20943-20948` stores its timer as `state.controlsRetryTimer` (shape of `state.previewRetryTimer` `U:8578`), clears it before re-arming and when `state.controlsModel` arrives. Fixes WCP-10-F9.
- Lines: -3 +5.
- Check here: standard; Playwright: route `get_controls` to fail twice, then answer: exactly 3 requests, then none for 20 s.
- Pi: nothing.
- Depends on: 7. Nothing depends on it. Not with 24.

Totals: about -1 040 / +480 lines (chain and commits 22-24), plus about 1 500 lines edited by renames in commits 6-10 and 15-18.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| The lock-free `/api/buffer` poll at 4 Hz (WCP-08-F4) | One async `fetchBufferState`, its timer and in-flight flag on `state`, started and stopped by one `updateBufferPolling(snapshot)`, merging into `state.snapshot` through upstream's `mergeCameraStateFields` and drawing only through `renderRecordingStatus`; one freshness rule (the poll owns `buffer_fill` while it runs) | `/api/state` waits on the controller mutex while a stopped take drains (`App:9307`), so at 1 Hz the page would show a safety stop seconds late and the bar would jump. The draw side has upstream's shape (`updateTimecodeDisplay`); only a second network poll has no precedent |
| Clip Viewer playback engine (frame fetch lanes, `requestAnimationFrame` tick, keep-awake `user_activity` interval) | `state.clipViewer`, one object per open clip, created by `openClipViewer` and dropped by `closeClipViewer` (owner decision 5) | Upstream flattens long-lived handles (`previewProcessing*`, created once); the viewer's 40 fields are created per clip and must all reset on close, which a fresh object does in one line |
| Listen (300 ms `controls_last_input` while the operator listens, max 2 min) | Raw `fetch`, timer and in-flight flag on `state` | No upstream feature waits for a hardware press; a push channel would be bigger new ground (WEB-7) |
| Settings search with a MutationObserver (WCP-05-F4, WCP-01-F12) | Flat `state.settingsSearch*` | Kept as reviewed |
| Remote controls pad (`test_input`) | A settings-card in Controls (24) or the main-page card with a stored retry (25); pills | The feature the owner restored (`/home/user/apertar-kb/fork-log.md:162-164`); upstream has no remote pad |
| Clip card grid with thumbnails (replaces upstream's list) | Grid and card CSS kept under `.media-browser-*` names | The reviewed rework keeps the grid, cards, thumbs, stage, scrub, histogram and metadata (WCP-02-F1) |
| Browser history and hold-to-repeat, if the owner keeps them | Under the new names, documented | Owner decisions 1 and 2 |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Should the phone's Back button close the Clip Browser? | a) Delete the history entries (commit 22). b) Keep `pushState`/`popstate` as documented new ground (about 25 lines) | a). Cost: on a phone, Back leaves the WebUI page instead of closing the overlay; the overlay's own Back and Escape still close it. Upstream uses no history at all |
| 2 | Keep hold-to-repeat on the Remote controls knob arrows and on frame step? | a) One step per click (commit 23). b) Keep both, documented as the one new widget behaviour | a). Cost: turning ISO by five steps takes five taps; on a desktop the arrow keys still repeat in the viewer. With b), each repeat goes through `sendCommand` after commit 4, so `/api/state` pauses while a knob arrow is held |
| 3 | Where does Remote controls live? | a) A card in the Controls panel (commit 24). b) The main page, as today, with its retry timer stored (commit 25) | a). Cost: one more tap (Settings > Controls) from the main page. Upstream keeps the main page for the four camera-critical cards (WEB-2) |
| 4 | Do the Clip Browser renames (commits 15-18, about 1 130 lines touched, no behaviour change) go in? | a) Yes. b) Keep the `pb`/`pbv` names and document them | a). The original developer finds his own names (`renderMediaLibrary`, `state.mediaSelection`) instead of an abbreviation no other part of the page uses. Cost: four large mechanical diffs, reviewed by rerunning the sed maps; open Playback branches must rebase |
| 5 | Clip Viewer state: one nested `state.clipViewer` or flat `clipViewer*` fields? | a) Nested, the one nested object on `state`. b) Flat, like `previewProcessing*` `U:4255-4266`, plus a 40-field reset on close | a). Cost: one exception to "no nested object" (WEB-12), documented. b) costs about 50 more lines and a reset that must list every field |
| 6 | White dropdowns for readability? | a) Delete (commit 19). b) Make `.settings-select` easier to read page-wide, in its own upstream-candidate commit | a) now; b) later if wanted. Cost of a): the Controls dropdowns look like every other dropdown again |

Handed to camera-modes for its owner list: where the IMX585 resolution pills get their sizes (WCP-04-F1). Deleting the pool read (`P:8956-8960`) takes resolution choice away from a mono IMX585 in the WebUI (`P:8961-8964`, `P:9020-9028`), and what a stock driver offers is not determined.

## Risks and what was not determined

| Risk | What settles it |
| --- | --- |
| Commits 2-3 change the REC pill, the most camera-critical element of the page. Routed replies in Playwright prove the logic, not the timing on a real drain | The commit 2 Pi steps on CM5 and on a Pi 4 with an SD card (the slowest drain), bar on and off. Until done, keep commits 2-3 on their own branch |
| The stale-fill rule assumes the poll runs during every drain the bar shows. If the poll stops (an abort, a lost reply) while `/api/state` still carries an old fill, the bar shows the old fill for up to one second | On the Pi, the `curl` loop from commit 2 beside the page: the bar never shows a fill above the loop's last value for more than 1 s |
| `sendCommand` merges each reply through `mergeCameraStateFields`. A routed command whose reply gains a top-level `state`, `resolution`, `fps`, `recording`, `buffer_*` ... would overwrite the snapshot | Checked in `--simulate` for the 6 read replies (no such key). On the Pi: `curl -s -X POST -d '{"cmd":"get_controls"}' http://<pi>:8000/api/command \| jq 'keys'`, the same for `list_actions`, `controls_history`, `preview_clip_name` |
| `sendCommand` gates REC while a Controls command or a clip preview is in flight (`P:15772`). A slow `scan_i2c` or `test_output` gates REC for its whole run | On the Pi: Controls > Scan on a bus with devices, and press REC on the main page in another tab during the scan. If REC stays grey for more than a second, the Scan handler goes back to a raw `fetch` as background traffic |
| Splitting `renderRecordingStatus` out of `renderSnapshot` touches a rough edge upstream keeps (WEB-24) | Argued with `updateTimecodeDisplay` as the precedent; the original developer may still object. Fallback: keep the pill block inline and call `renderSnapshot(state.snapshot)` from the buffer poll at most once per second |
| Renames (commits 6-10, 15-18) conflict with any branch that edits the same lines (Playback bugs WCP-06-F5..F8, the preroll theme's pre-roll button, boot-config-helpers' card) | Land renames last within their area; publish each sed map so a branch can replay it |
| Pi-model cost of the 4 Hz poll on a Pi Zero 2 / Pi 3 was not measured, today or after. Request rates and Core work per request are unchanged | `top` on the Pi while a phone keeps the page open during a take: `apertar-core` CPU % before commit 2 and after commit 3, on a Pi 4 and a Pi 5 |
| Line estimates come from reading, not from doing the edits | - |

## Findings covered

| Finding | Commit |
| --- | --- |
| WCP-02-F1 | 12, 14 (Remove dialog part: 11) |
| WCP-02-F2 | 19 |
| WCP-03-F1 | 11 (dialog), 12 and 14 (SVG, h1), 16 (nested `state.pb`), 22 (history) |
| WCP-04-F1 | not here: camera-modes theme, with the mono fact above |
| WCP-06-F1 | 16, 17, 18 |
| WCP-08-F1 | 1, 2, 3 |
| WCP-09-F1 | 6, 7 |
| WCP-09-F2 | 4 |
| WCP-09-F3 | 24 or 25 (hold-to-repeat: 23) |
| WCP-10-F2 | 8 (fields only; the installer stays, precedent `installPreviewStream`) |
| X-state-consistency-3 | not here: table content and the comment in `Imx585Modes.hpp`, camera-modes; QML lists, touch-ui theme ("mode list"). The page's copy stays one hand copy (WEB-8) |
| WCP-01-F8 | 15 |
| WCP-02-F3 | 15 |
| WCP-02-F7 | 19 |
| WCP-02-F10 | 15 (body rule; the `.x.hidden` repeats in 21) |
| WCP-03-F3 | 13 (Clear button). Per-row Download/Delete: not covered, the viewer offers both per clip; see WCP-06-F4 |
| WCP-03-F5 | 21 |
| WCP-03-F8 | 24 |
| WCP-04-F2 | not here: `ladderRequest` goes with the panel-open fetch (camera-modes) |
| WCP-04-F3 | not here: camera-modes, together with WCP-04-F1 (the first fetch and retry exist for the main-page pool) |
| WCP-04-F9 | 14, 20 |
| WCP-05-F5 | 22 |
| WCP-06-F2 | 11 |
| WCP-06-F12 | 16 |
| WCP-07-F2 | 9 |
| WCP-07-F10 | 5 |
| WCP-08-F2 | 2, 3 |
| WCP-08-F3 | 2 (freshness windows), 3 |
| WCP-08-F4 | kept as new ground (section above) |
| WCP-09-F7 | 4 |
| WCP-09-F8 | 4, 7 (timer and in-flight flag on `state`); the poll itself stays as new ground |
| WCP-10-F9 | 24 (loop deleted) or 25 (timer stored) |
| WCP-10-F10 | 2 |
| WCP-02-F8, WCP-06-F4 | not covered: the card grid replaced upstream's list on purpose; restoring size/fps/frame facts on cards is a feature choice. Playback fix list |
| WCP-06-F9 (timecode helpers duplicated) | not covered: Playback internals, a separate small commit in the Playback fix list |
| WCP-02-F9, WCP-01-F5 (rules with no element) | not covered: slop pass (commit-clarity work) |
| WCP-10-F1 (Boot Config route) | not covered: boot-config-helpers theme |

## What the challenge changed

Each row was checked again at `0d13a6f` / `upstream-1.6.0`. Commit numbers on the right are the new ones.

| Point | Decision | Why |
| --- | --- | --- |
| Precedent for the pill writer outside `renderSnapshot` | Challenger right | `updateTimecodeDisplay` `U:9168-9216`, run from the `requestAnimationFrame` loop `U:9219-9238`, reads only `state.snapshot`. Cited in commit 1; only the network poll stays new ground |
| A second installer | Challenger right | `installPreviewStream` `U:8566`, called `U:11607`; `installBootConfigInteractions` is even called from inside `installInteractions` (`P:20923`). Commit 8 keeps it and moves fields only |
| Flat `state.clipViewer` | Partly right | `previewProcessing*` is flat (`U:4255-4266`), so it is a decision: owner item 5. Recommendation stays nested: the viewer object is made per clip (`P:12772`) and dropped on close (`P:12862`), about 40 fields with a `lanes` array |
| Header copies upstream markup, ids and CSS | Challenger right | `U:3981-4012` ids, Refresh text only `U:4008`, 0 `.media-browser-*` rules in P, 2 header SVGs (`P:6355`, `P:6371`). Commit 12; Clear button split out as commit 13 |
| `buffer_fill` / `buffer_flush_discarded` not merged | Challenger right | `P:13841-13860` copies neither. Commit 2 adds 4 lines to `mergeCameraStateFields`. Also found: the merge copies `recording` (`P:13889`), so the patch must rename it first |
| Stale fill in `/api/state` | Challenger right | `App:9306` reads the gauge before `App:9307` waits; `App:9591` builds safety stop fresh. Commit 2 keeps one rule keyed on `state.bufferPollTimer`, scene (e) added |
| Commit 3/4 split around `noteBufferSafetyStop` | Challenger right | It reads the fields commit 3 deleted and is called from both timers. Commit 2 keeps it on `state` fields; commit 3 removes it with its seen flags |
| First-load discard toast | Challenger right, narrowed | `discardedSeen: -1` (`P:16420`, `P:16460`) skips only the first discard value; the stop toast fires on load today (`stopSeen: false`). Commit 3 guards only the discard comparison on a previous snapshot, so both keep today's behaviour |
| `sendCommand` renders twice, gates REC, drops `/api/state` | Challenger right on the facts | `P:14408-14412`, `P:14427-14443`, `P:15772`, `P:19273-19275`, `P:16396`. Cost text corrected in commit 5 and Risks |
| `get_mode_ladder` through `sendCommand` breaks REC during a safety-stop flush | Partly right | During a flush the stale snapshot still says `recording`, so `P:15770` does not disable REC and `toggleRecord` passes by `flushing` (`P:19272`). The real costs are dropped `/api/state` replies while it waits on `CC:11041` and REC gated outside a take. Still enough: a render-started read is background traffic, so `ladderRequest` stays until camera-modes moves the fetch |
| Split commit 6 into preview + ladder save/dry runs | Partly right | There is no ladder save or dry run through `ladderRequest`: its one caller is `get_mode_ladder` (`P:8023`). Commit 5 is the clip preview alone |
| Missing commit B (ladder fetch to panel open) | Not taken here | The first fetch and 5 s retry exist for the main-page pool (WCP-04-F3's own text), so the move depends on the pool decision; both go to camera-modes as a named dependency |
| `error.result` | Challenger right | `failure.payload` `P:19002`, 0 `error.result`. Commit 4 uses `error.payload` |
| Outside readers | Challenger right (no change) | None outside the page except the UI.conf key |
| Mono IMX585 loses its sizes | Challenger right | `P:8961-8964`, `P:9020-9028`. Old commit 22 dropped; handed to camera-modes with this fact |
| Owner options in the middle of the chain | Challenger right | History, hold-to-repeat and Remote controls are now leaves 22-25 after the renames; nothing depends on them |
| Remote controls option b) needs a commit | Challenger right | Commit 25, `state.controlsRetryTimer` like `U:8578` |
| Commit 1 churn | Challenger right | Dropped; commit 2 declares only surviving fields |
| Label-table move in the Controls commit | Challenger right | Dropped, not split: upstream keeps meta tables beside their code (`U:4128`, `U:4165`); moving them is churn |
| `clipUi` and `settingsSearch` in one commit | Challenger right | Commits 9 and 10 |
| Standard check 2 | Challenger right | `smoke_core.sh:41` prints the page size; the diff filters that line |
| Commit 15 grep | Challenger right | `pbvRepeat` uses no pointer capture; scrub `P:12678` and drag `P:14730` keep theirs. Commit 23 checks the count = 2 |
| Commit 24 grep | Challenger right | `option.hidden` `P:15437` = `U:9526` stays; commit 21 checks the count = 1, after preroll and boot-config-helpers |
| Commit 16 review size | Challenger right | Review by rerunning the sed map (commit 15) |
| Owner item 7 (confirm text) | Challenger right | Settled by WEB-21; dropped from the list |
| Pi checks: bar on and off, a `curl` loop | Challenger right | `watchStop` `P:16566` is a separate path today. Added to commit 2 |
| Pi-model cost reading | Challenger right | The reading to compare is named in Risks |

## Checked against the owner's recorded decisions

Audit 2026-11-17. Sources: `owner-recorded-decisions-a.md` (DA-*), `owner-recorded-decisions-b.md` (DB-*), and the pages they cite, read around the rows: `working/playback/design-playback.md` §2.9 (D1-D22), §3.2 (B1-B24), §3.3 (V1-V21), §9 (O1); `working/playback/decisions.md`; `working/playback/measurements.md:107-126`; `working/controls/decisions.md`; `fork-log.md:102`, `:138`, `:148`, `:162-165`; `working/drop-frames/README.md:72`, `:87`, `:99`; `working/tools/controls_page_test.js`. Code: `P7:` = `src/web/WebControlPage.cpp@7f188a5` (core-work HEAD; markup lines equal the plan's `P:`, script lines after `P:10100` sit about 6 higher), `U:` = `@upstream-1.6.0`. All rows **confirmed** in the KB text and the code unless marked.

The rule used: a recorded decision stays unless it makes a stock camera (original driver, 720x720 screen, a 1.6.0 hardware file, no port keys) behave differently from 1.6.0; then it becomes an operator setting, not a deletion.

The main finding: the Clip Browser and Clip Viewer are not loose port parts. They are the element-by-element map Patrik approved (DA-43 "the WebUI playback looks and behaves like the touch UI's Clip Browser and Clip Viewer", DB-75; all Q1-Q30 answered or "accept the defaults", `working/playback/decisions.md:7-46`), built and tried by him (T49, T50 "works well", `fork-log.md:102`). Commits 11, 12, 14, 22 and 23 as written take parts of that map back to the 1.6.0 list overlay. The fix in each case is to keep the touch-UI part and build it from upstream's classes, ids and `/icons` PNGs, which is what the playback design itself prescribed (§3.1 "Parts used").

| commit | touches decision (id, his words) | verdict | what changes in the commit |
| --- | --- | --- | --- |
| 1 pill in `renderRecordingStatus` | none | fine | none |
| 2 buffer poll merges into the snapshot | Pill READY green while the buffer drains, also with the bar off (`working/drop-frames/README.md:99`, `fb5801c`); "Frame buffer bar" option, off by default (`README.md:72`); DB-61 "discard, the old clip is cut short" | fine | none. Scenes (a)/(b) with the bar off and the Pi step "press REC during the flush: a new take starts" already cover them. Keep `toggleRecord`'s flush pass reading `state.snapshot.buffer_safety_stop` |
| 3 buffer toasts from the snapshot | DB-61 (the flush-discard toast reports his choice) | fine | none |
| 4 Controls through `sendCommand` | DA-6 "Save during a take: allowed"; DA-20 stale save "merge per key ... otherwise refuse"; T43 Check reads `issues` from an `ok:false` dry run (`checkConfigFile` `P7:18870-18885`); DA-23 "Listen + phone covers it" | fine | Keep in every catch: `error.payload.code` `stale`/`conflict` -> "Your settings stay on the page" (`P7:18309`, `:18738`), and `error.payload.new_errors` / `issues` for Check. Listen stays a raw fetch (already planned). Rerun `working/tools/controls_page_test.js` (60/60, `working/controls/HANDOFF-next.md:31`): its mock must answer the `/api/state` refresh that `sendCommand` now schedules |
| 5 clip-name preview through `sendCommand` | clip names kept (DA-104 "everything back") | fine | none |
| 6 `controlsState` -> `state.controls*` | Patrik's Controls test harness `working/tools/controls_page_test.js:240`, `:246` evaluates `controlsState.added.length`, `controlsState.removed.size`, `controlsState.edits.size` in the page | conflict (breaks a KB test) | Same change set: apply the commit's sed map to `controls_page_test.js` (KB commit, 3 expressions -> `state.controlsAdded.length`, `state.controlsRemoved.size`, `state.controlsEdits.size`) and rerun it; ids it reads (`saveControlsButton`, `controlsStatePill`, `hardwareDevices`, ...) do not change |
| 7 Controls sets and Listen timer on `state` | none | fine | none |
| 8 Boot Config fields on `state` | DA-21 DPI box, DA-78..DA-81 config.txt rules (Core side) | fine | none (fields only) |
| 9 clip-name composer on `state` | none | fine | none |
| 10 settings search on `state` | none | fine | none |
| 11 Remove asks with `window.confirm` | DA-43, design B23: "Remove Selected Clips?" dialog, "the old `window.confirm` is removed from the delete helpers (F36)", button "Removing... (N files)" and disabled; V12 "Remove Clip?" dialog; V17 the dialog closes the Info overlay; tried in T49 (`measurements.md:115-116`) | conflict | Drop commit 11. The dialog stays as documented new ground (row added below), renamed in commit 15 (`.media-browser-dialog*`, `#mediaBrowserRemoveDialog`); its buttons already are `.secondary-button` / `.danger-button`. Stock: the dialog exists only inside the port's Clip Browser (see last row) |
| 12 header becomes upstream's | DA-43, B2 "PLAYBACK" eyebrow; B3 "Clip Browser" / "Still Browser" / "Timelapse Browser" / "Audio Browser"; B5 "SHOW / Clips" button opening Clips, Stills, Timelapse, Audio; DA-49 (Q2) "filter only (opens on Stills in photo mode)" (`P7:10132`); B6 Refresh "with `refresh.png`", "Scanning..."; B10 sort chip "NEWEST FIRST / OLDEST FIRST" "replaces today's `<select>`" | conflict | Reshape, do not copy `U:3981-4012`. Keep eyebrow, per-category title, the SHOW button and its menu, the sort chip, Refresh's "Scanning...". Take upstream parts: Back = upstream's own markup `icon-button settings-back-button` with the text "Back" / "Cancel" (`U:3993-3995`; no arrow SVG); Refresh = `secondary-button` + `/icons/refresh.png` (the touch UI's icon, design F27) + "Refresh Media"; SHOW and the chip = `secondary-button` (B5). Upstream ids where the job is the same (`closeMediaBrowserButton`, `refreshMediaBrowserButton`, `mediaBrowserCountPill`). Deleted: the 2 header SVGs, `.pb-top-button`, `.pb-h1` (title -> `h2.section-title`, as B3 says). Not added: the filter row, the `<select>`, the copy line. Check grep becomes `grep -cE 'pb-top-button|pb-h1'` = 0; Playwright: SHOW menu filters, photo mode opens on Stills, chip toggles order. About -60 +25 |
| 13 Clear button | DA-43, B4 "Back (... 'Cancel' in selection)": Back already reads Cancel and leaves selection (`P7:11975`); DA-50 keeps Download and Select All, Clear is not in the touch UI | needs his answer | Recommend drop: Cancel does Clear's job. WCP-03-F3's Clear point is met by B4 |
| 14 viewer buttons and PNGs | DA-43, V8 "three circles ... round `.icon-button`s with `previous` / `play` / `pause` / `next` PNGs"; DA-48 (Q9) O1 "Frame step ◀ ▶ (hold to repeat)"; V5 Info button | conflict in part | Base class `.icon-button` (upstream) plus one round modifier for the transport row (`border-radius: 50%`, renamed `.clip-viewer-transport .icon-button`), instead of `.pbv-circle*`. Frame step: text glyphs in `.icon-button`, not `/icons/previous.png` / `next.png`, which already mean previous/next clip in V8. Info keeps `info.png` + "Info" on `secondary-button` (as built `P7:6435-6437`). Download as a text `secondary-button` is fine (no download icon in `src/web/icons`). The selected-check SVG -> `.media-select-control.selected` is fine (B17 asks only for a red circle with a check) |
| 15 class and id renames | none (operator-visible strings unchanged) | fine | Owner Q4 stays open. The sed map also covers the kept dialog, menu, chip and history names |
| 16 flat Clip Browser state | none | fine | Owner Q5 stays open |
| 17 upstream job names | none | fine | none |
| 18 verb-first viewer names | none | fine | `repeatClipFrameStep` survives (see 23) |
| 19 one dropdown look | No recorded decision. The white look came in `d44b177` (under his name, built by Claude in the drop-frames work he directed, DB-91): "like CineMate's web GUI, so they are easy to see"; `working/drop-frames/README.md:87` later describes the pins as "a dark dropdown" | needs his answer (owner Q6) | none. Stock: Controls and Config > Hardware exist only in the port, so either answer leaves a stock camera as 1.6.0 |
| 20 no inline SVG in the Mode Ladder | DB-51 "no drag and drop, the ladder orders itself by quality", "'Max' boxes between rows"; DB-49 "one column of collapsible groups"; DA-32 "the Controls card gets white SVG blueprint sketches of each accessory" (wish, not built: 0 matches for a sketch in `P7`) | conflict (in the plan text) | Only `ladderIcons.down` (the arrow on the Max line, `P7:8195`) and `.chevron` (group head, `P7:8307`) are used; `handle`, `up`, `remove` are dead. Do **not** add "Up"/"Down"/"Remove" buttons (that brings back the manual order DB-51 removed). Delete the 3 dead icons; the Max line loses its arrow; the chevron becomes a CSS triangle drawn like `.settings-select`'s arrow (`U:1535-1541`, two `linear-gradient`s), turned by `[aria-expanded="true"]`. Do not state "0 `<svg>`" as a page rule: DA-32's sketches, when built, are files in `src/web/icons` served by `GET /icons/<name>` like every other icon |
| 21 `.hidden` class | none | fine | none |
| 22 no browser history | DA-43, design D19 "the browser's Back gesture and button close the viewer, then the browser (`history.pushState` / `popstate`)", reason "a phone's Back would leave the WebUI"; DA-56 (Q10) "design for iPhone and Android"; built and tried: "phone Back leaves the viewer first" (`fork-log.md:102`, `measurements.md:132`) | conflict | Drop commit 22 (owner Q1 option b): history stays as documented new ground under the new names (about 25 lines). Stock: `pushState` runs only when the overlay or the viewer opens (`P7:10135`, `P7:12783`), so the rest of the page behaves as 1.6.0 |
| 23 one step per click | Frame step: DA-48 (Q9) O1 "Frame step ◀ ▶ (hold to repeat)" (`design-playback.md:1473`, "long takes and finding the clap need it"; built `fork-log.md:102`). Knob arrows: from `1319967` ("another session", `fork-log.md:148`), no decision recorded | conflict in part | Split: keep `repeatClipFrameStep` and its two calls (`P7:12940-12941`). Owner Q2 shrinks to the Remote controls knob arrows. If he removes their repeat, the same commit changes the card copy "Hold an arrow to keep turning." (`P7:4577`) |
| 24 Remote controls in the Controls panel | DA-104 / DB-65 "everything back" keeps Remote controls; where it lives is not decided | fine (the stock rule picks it) | none. Today the card is on every camera's main page (`P7:4569-4580`, never hidden) and fetches `get_controls` every 5 s until a model arrives: a stock main page differs from 1.6.0. Commit 24 makes it 1.6.0 again and keeps the feature |
| 25 Remote controls stays on the main page | as 24 | conflict with the stock rule (not with a decision) | Take 24. If he still wants the main-page card, it must be an operator option off by default, a `UI.conf` key in the shape of `frameBufferBarEnabled` (`App:1905`, `:2096`, `:7791`; command `set_frame_buffer_bar_enabled`); that needs Core and is outside this page-only plan |
| Plan as a whole | DA-43 vs the stock rule: the port's Clip Browser and Viewer replace 1.6.0's list overlay (`U:3979-4030`) on every camera, stock included | needs his answer (playback theme) | Not in this plan. This plan keeps the feature as built. If he wants a stock camera to open 1.6.0's list, the shape is one `UI.conf` switch like `frameBufferBarEnabled`, default 1.6.0, and keeping upstream's overlay beside the port's (about 400 lines kept, not deleted) |

Plan claims corrected by this audit:
- "Every feature stays" (In short 6) holds only with commits 11, 12, 14, 22 and 23 changed as above.
- "WEB-21 settles the wording shape, so this is no owner question" (commit 11): a recorded decision settles it the other way (B23).
- Commit 20's "Up", "Down", "Remove" buttons describe controls the ladder does not have.
- What a Pi adds: his camera is a CM5 with the CFexpress hat and an HDMI monitor, no touch screen (DA-77). The Pi 4 + SD-card steps (commit 2, Risks) and the "Pi 4 and Pi 5" CPU reading need another board; on his rig they read "not run".
- His NVMe campaign ran with `frameBufferBarEnabled=true` (`working/drop-frames/nvme-campaign/run-20261110/audio-forensics/*/UI.conf:34`), and in real use a WebUI client is connected (`working/drop-frames/nvme-campaign/plan.md:92`). Commits 2-3 must keep the `/api/buffer` request rate and its start/stop rule exactly as today, or a later campaign is not comparable with his. `working/tools/webui_client.py` mirrors only `/api/state` 1 Hz and the preview, so it stays valid.
- No tutorial (`tutorials/`) and no other tool in `working/tools` or `working/drop-frames` names a page function, id or store this plan renames (grep for `pb*`, `playbackOverlay`, `controlsState`, `frameBufferBar`, `bootConfig`, `clipUi`, `settingsSearch`: only `controls_page_test.js`).

Rows to add to "What stays as new ground":

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| The touch UI's browser header: "PLAYBACK" eyebrow, per-category title, SHOW pop-up menu, sort chip | Upstream parts (`h2.section-title`, `secondary-button`, `icon-button settings-back-button`, `/icons/refresh.png`), the menu as the one pop-up, under `.media-browser-*` names | DA-43, DA-49; design B2-B6, B10 |
| Remove dialog (browser and viewer) | Scrim and card under `.media-browser-dialog*`, `secondary-button` / `danger-button`, "Removing... (N files)" | DA-43; design B23, V12, V17 |
| Round transport circles in the viewer | `.icon-button` with one round modifier | DA-43; design V8 |
| Frame step hold-to-repeat | `repeatClipFrameStep`, no pointer capture, 400 ms / 90 ms | DA-48 (O1) |

### Decisions this plan must keep

1. The Clip Browser and Viewer look and behave like the touch UI's (DA-43, DB-75): eyebrow "PLAYBACK", "Clip / Still / Timelapse / Audio Browser", SHOW menu, sort chip, Back that reads Cancel in selection, round transport, Remove dialog. Change the parts to upstream classes, ids and `/icons` PNGs, not the shape.
2. SHOW only filters; it opens on Stills when the camera is in photo mode (DA-49).
3. The phone's Back closes the viewer, then the browser (design D19; tried, `fork-log.md:102`).
4. Frame step repeats while held (DA-48, O1).
5. Download, Select All, Timelapse and Audio stay (DA-50); "1 item" wording (DA-54); thumbnails fill the card to the top and sides (DA-74); keep-awake `user_activity` only while playing (DA-57); Space plays and pauses (DA-64).
6. The REC pill turns READY green while the buffer drains after a safety stop, with the bar on or off; REC during the flush discards and starts a new take at once, with its toast (DB-61, `drop-frames/README.md:99`). The "Frame buffer bar" stays an option, off by default.
7. The `/api/buffer` poll rate and its start/stop rule stay as today (his campaigns ran with the bar on).
8. The Mode Ladder orders itself, has Max boxes between rows and collapsible groups (DB-49, DB-51); no manual Up/Down.
9. Controls: Save during a take is allowed (DA-6); a stale save keeps the operator's edits on the page (DA-20); Listen stays (DA-23); Check shows Core's issues with line numbers (T43).
10. Remote controls stays as a feature (DA-104); off the stock main page.
11. Do not make "no SVG" a rule that blocks DA-32's accessory sketches; they go to `src/web/icons`.
12. Rerun `working/tools/controls_page_test.js` after commits 4, 6 and 7, updated by the same sed map.

### Open questions a recorded decision already answers

| Question (For the owner) | Decision | The answer |
| --- | --- | --- |
| 1. Should the phone's Back close the Clip Browser? | DA-43 + design D19; DA-56; tried (`fork-log.md:102`, "works well") | Yes: option b, keep `pushState` / `popstate` as new ground. Commit 22 goes |
| 2. Hold-to-repeat on frame step and knob arrows? | DA-48 (Q9: O1 "Frame step ◀ ▶ (hold to repeat)") | Frame step: keep. The knob arrows have no decision: the question stays, for them only |
| 3. Where does Remote controls live? | DA-104 keeps the feature; the stock rule (the card changes a stock main page) | Controls panel (commit 24). Not a decision of his on the place: tell him, do not ask again unless he objects |
| 7 (dropped by the plan). Remove: `window.confirm` or the dialog? | DA-43 + design B23, V12 ("the old `window.confirm` is removed") | The dialog stays. Commit 11 goes |
| Header: upstream filter row and sort `<select>`, or SHOW and the chip? (not asked by the plan) | DA-43 + design B5, B10; DA-49 | SHOW menu and the chip stay, built from `secondary-button` |
| 4, 5, 6 (renames, nested `state.clipViewer`, white dropdowns) | none recorded | still open |
| New: Clear button beside Select All (commit 13) | DA-43 + B4 (Cancel already clears) | not answered; recommend drop |
| New: should a stock camera keep 1.6.0's media list? | DA-43 vs the stock rule | not answered; playback theme |
