# Inventory WCP-10: WebControlPage.cpp JS tail (new-file lines 18748-20840)

Diff: /home/user/build/review/diffs/WCP.part10.diff (1415 lines, 7 hunks). All refs @cinemate-port `01f170c` unless noted; upstream = `upstream-1.6.0` (`WebControlPage.cpp` there).
Status words: confirmed = read in code. Fork-log status from `/home/user/apertar-kb/fork-log.md`.

## 1. Hunks and the port commits that wrote them

| Hunk (new lines) | What | Commits (blame) |
| --- | --- | --- |
| 18748-18968 | config editor gutter, Check, diff, history, revision header on save; removal of 5 media-list functions | `8be1ab5` (125 lines), `effb804` (21), `2a4266e` (20, generalised gutter `marks`), `3b87d99` (5), `f5fe41b` (2) |
| 19080-19121 | `allowedKeys` list of preset import | `d44b177` (cameraCdngLog, cameraHdr*, cameraFpsPhaseLock ...), `ac00fb0` (speed-ramp keys), `92d0970` (audioRecordedOutlineEnabled), `014a2bf` (cameraClipNameTemplate) |
| 19189-19250 | `toggleRecord`: flush case | `c5db8b2` |
| 19814-19843 | `requestStoragePreroll` | `d44b177` |
| 19858-20660 | Boot Config card JS (about 800 lines, whole block new) | `8a56545` (583 lines), `2a4266e` (80), `3b87d99` (70), `bc12c0a` (23, mis-attributed: blame on shared lines), `4629de2` (10), `b3e7f52` (7), `afa00e8` (1) |
| 20663-20712 | `installInteractions`: frames-per-folder Apply, ladder-link click and key handlers | `d7dd337` (11), `5dfbc6c` (8), `392e812` (6), `1ef94fe` (4) |
| 20840-20933 | `installInteractions` tail: Playback overlay wiring, Controls/Hardware/Config buttons, settings search | `8be1ab5`, `1319967`, `d44b177`, `f5fe41b`, `d282de9`, `bc12c0a`, `8a56545` |

## 2. Features (operator view)

| Feature | Commits | Fork-log status |
| --- | --- | --- |
| Config editor T43: line-number gutter, Check button, "Save" shows a line diff first ("Save these changes" / "Back to editing"), version history dropdown | `8be1ab5`, `effb804`, `2a4266e` | `8be1ab5` fork-only; `effb804` fork-only. No test line in fork-log; desk only |
| Config save carries revision (`X-Apertar-Revision`); stale / conflict / merge_review / old_page refused, text kept in box; after save reload Controls and Hardware cards | `effb804`, `8be1ab5` | fork-only |
| Boot Config card (System pane): sensor per connector, link frequency, I2C/I2S/SPI/onboard audio toggles, RP1 overclock, display (HDMI / DPI), View file, Edit file (text editor with managed-line marks and own-lines hint), Use This Text, Download, Upload, Save review (diff, display-change gate checkbox), Save and Reboot, Save Only, wait for the camera to come back | `8a56545`, `3b87d99`, `2a4266e`, `b3e7f52`, `afa00e8` | In `d44b177` line of fork-log (PR #1 merge `4581a69`). Pi only; desk-tested not recorded here. Marked as in "Pi's drop-frames" line pushed 2026-11-06 |
| Clip Browser wiring (Playback overlay): Back, Refresh, SHOW menu with filters, newest/oldest chip, Select All, Download, Remove dialog, phone Back via popstate, viewer close | `bc12c0a`, `4629de2` | fork-only, Pi only; tested 2026-10-29 headless Chrome against Core |
| Removal of upstream media-list overlay handlers (see section 6) | `bc12c0a` | same |
| Frames per folder Apply (0 or 100-100000) | `d7dd337` | fork-only, GitHub `cinemate-port`; host test `tools/frame_path_test.cpp` |
| Mode Ladder link: click on `[data-ladder-link]` opens the Mode Ladder card; click on `[data-ladder-lock]` shows red lock warning; Enter/Space on role=link | `5dfbc6c`, `392e812` | fork-only, desk-tested, Pi check pending |
| Storage pre-roll button and toast | `d44b177` | Pi only |
| Record press during safety-stop flush starts a new take (Core discards queued frames) | `c5db8b2` | owner decision 2026-11-01 |
| Preset import accepts new keys (see 4) | several | fork-only |
| Remote controls: load controls at start, retry every 5 s until Core answers; Reload, Save Hardware, Save Controls, Listen toggle, Undo last controls save buttons | `1319967`, `8be1ab5`, `d282de9`, `f5fe41b` | `1319967` on the Pi only (2026-11-04) |
| Settings search: input filters panels; nav click clears search; Escape clears search first, then closes Settings | `d44b177` (WebUI Settings search) | fork-only |

## 3. Interface touched

### Socket commands sent by this slice (all via `sendCommand` / `controlsCall`)

| Command | Added or existing | Core handler @cinemate-port | Upstream |
| --- | --- | --- | --- |
| `set_controls` (`base`, `text`, `dry_run`, `by`) | new | `ApertarCoreApp.cpp:12763` | none |
| `controls_history` (`name`) | new | `:12458` | none |
| `storage_preroll` | new | `:14603` | none |
| `set_frames_per_folder` (`value`) | new | `:12857` | none |
| `restart_system` | existing | `:14855` | `ApertarCoreApp.cpp:10801` |
| `run_media_speed_test`, `enter_standby`, `wake`, `power_off_system`, `record_stop`, `timelapse_stop`, `set_photo_timelapse` | existing, unchanged | | upstream has them |
| `get_boot_config`, `set_boot_config` | new; slice uses HTTP route, not socket | `:14586`, `:14589` | none |
| `test_input` | new (used by Try buttons elsewhere) | `:12565` | none |

### HTTP routes

| Route | Use here | Status |
| --- | --- | --- |
| `POST /api/config` + header `X-Apertar-Revision` | save with revision | route exists upstream (`ApertarCoreApp.cpp:7168/7175`); header, 409 `old_page`, `issues`, `new_errors`, `conflicts` are new |
| `GET/POST /api/boot-config` | Boot Config load/save/dry_run | new; Core `:9161`, `:9170`. POST wraps the JSON body into `set_boot_config` by string insert (`payload.insert(brace+1, "\"cmd\":\"set_boot_config\"")`) |
| `POST /api/boot-config/parse` | Upload, Use This Text, marks while typing (500 ms debounce) | new; `:9200`; max 64 KiB |
| `GET /api/buffer` | poll after reboot to detect camera answering | new route (`:8419`), not upstream. JS uses it as a liveness probe |
| `/api/media/delete-selected`, `/api/media/download-selected` | used by pb* | exist upstream |
| `POST /api/media/delete` (single) | no longer called from JS; route stays in Core (`:9004`) | dead route on the page side |

### State fields read in this slice

`state.snapshot.recording`, `timelapse_active`, `media_writes_pending`, `media_mounted`, `sound_recording`, `state`, `ui.photo_mode_enabled`; `frameBufferBar.safetyStop` (page-side object, `:16419`, not a snapshot field; fed from `buffer_safety_stop`); `state.configRevision`, `state.configLoadedText`, `state.configDirty`, `state.pb.{sort,selection,items,page,ignorePop}`, `controlsState.{model,listening}`, `settingsSearch.active`. Boot Config JSON fields read: `state.{editable,problem,warnings,camera_auto_detect,board{detected,section,family,ports},sensors[]{key,label,installed,link{default_hz,options}},cameras{cam0,cam1}{sensor,link_frequency,line},candidates,toggles{i2c,i2s,spi,audio},rp1{available,on,overlay,line},displays[],display{value,overlays,lines},managed[]{line,what}}`, `drm[]`, `changes[]{line,before,now,after,removed}`, `display_changed`, `written`, `text`, `revision`, `path`, `helper`, `code` (`stale`, `old_page`).

### Preset keys added to `allowedKeys` (import path)

`cameraCdngLog`, `recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`, `cameraClearHdr`, `cameraHdrThresholdHigh`, `cameraHdrThresholdLow`, `cameraHdrBlend`, `cameraHdrGainAdder`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraConformFps`, `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter`, `cameraFpsSpeedRampAudio`, `cameraFpsSpeedRampAfter`, `cameraClipNameTemplate`. Pure extension of an existing list (upstream list at the same place, `payload[key]` loop).

### Config keys, env vars, files

| Item | Where | Note |
| --- | --- | --- |
| `[storage] frames_per_folder` | field `settingsFramesPerFolderInput`, range 0 or 100-100000 | JS validates, Core owns the key (env `APERTAR_CDNG_FRAMES_PER_FOLDER`, in other unit) |
| `/boot/firmware/config.txt` | edited via Core + root helper `scripts/apertar-boot-config` (`sudo -n /usr/local/libexec/apertar-boot-config`) | helper is new; upstream has no config.txt editing |
| `config.txt.apertar.bak` | named in the timeout message as "previous file on the boot partition" | backup written by helper |
| `apertar-hardware.conf` | `/api/config` text; history versions via `controls_history` | exists upstream |
| DOM storage | none new in this slice | |

### UI element ids touched (listeners wired)

Config: `settingsConfigEditor`, `settingsConfigGutter`, `settingsConfigDiff`, `checkConfigButton`, `configHistorySelect`, `saveConfigButton` (now opens diff instead of saving), `reloadConfigButton`, `reloadControlsButton`, `reloadHardwareButton`, `saveHardwareButton`, `saveControlsButton`, `listenControlsButton`, `undoControlsButton`.
Boot Config: `settingsBootConfigCard`, `bootConfigStatePill`, `bootConfigMessage`, `bootConfigWarnings`, `bootConfigDiff`, `bootConfigFileView`, `bootConfigCam0/1{Field,Select,Note,LinkField,LinkSelect,LinkNote}`, `bootConfigRp1Field`, `bootConfigRp1Options`, `bootConfigRp1Note`, `bootConfigI2cOptions`, `bootConfigI2sOptions`, `bootConfigSpiOptions`, `bootConfigAudioOptions`, `bootConfigDisplaySelect`, `bootConfigDisplayNote`, buttons `reload/save/view/edit/download/upload/useBootConfigText/closeBootConfigEditor`, `bootConfigUploadInput`, `bootConfigEditField`, `bootConfigEditor`, `bootConfigGutter`, `bootConfigEditorLegend`.
Playback: `pbBackButton`, `pbRefreshButton`, `pbShowButton`, `pbShowMenu`, `#pbShowMenu button[data-pb-filter]`, `pbSortButton`, `pbSelectAllButton`, `pbDownloadButton`, `pbRemoveButton`, `pbRemoveCancel`, `pbRemoveConfirm`, `pbRemoveScrim`, `playbackOverlay`.
Other: `storagePrerollButton`, `settingsFramesPerFolderInput/Apply`, `settingsSearchInput`, `[data-ladder-link]`, `[data-ladder-lock]`, `toast` (class `with-link`).
CSS classes used: `.managed`, `.diff-add .diff-del .diff-gap .diff-note .diff-info .diff-managed .diff-confirm .diff-actions`.

## 4. Original code modified in this slice (upstream regions)

| Region @upstream-1.6.0 | Where in port | Change | Kind |
| --- | --- | --- | --- |
| `saveConfigFile` (`WebControlPage.cpp` upstream near 10330) | new `18877`-ish | adds revision header, failure payload carried on Error, shows issues, reloads Controls; `fetch` body unchanged | extended-in-place |
| `saveConfigButton` listener | `20870`-ish | click now `showConfigDiff` (opens diff box) instead of `saveConfigFile`; save needs a second click | behaviour-changed |
| `settingsConfigEditor` input listener | | also hides diff, updates gutter | extended-in-place |
| `fetchMediaLibrary` (10361) | kept (port `11991`, rewritten for pb) | outside this slice | rewritten (other unit) |
| `deleteMediaLibraryItem` (10380), `downloadSelectedMediaItems` (10404), `deleteSelectedMediaItems` (10426) | deleted here | replaced by `pbRemoveSelected` (`12050`), `pbDownloadSelected` (`12084`) | removed |
| `installInteractions` media block (upstream 11354-) | `20840` | 9 listeners (`closeMediaBrowserButton`, `refreshMediaBrowserButton`, `mediaBrowserSortSelect`, `selectAllMediaButton`, `clearMediaSelectionButton`, `downloadSelectedMediaButton`, `deleteSelectedMediaButton`, `.media-filter-button`, `mediaBrowserOverlay` click) replaced by `pb*` listeners + `popstate` + `pbvInstall()` | rewritten |
| Escape keydown handler | `20899`-ish | order: Playback (`pbEscape`) > settings search clear > settings close | extended-in-place |
| Settings nav click | | calls `clearSettingsSearch()` first | extended-in-place |
| `allowedKeys` in preset import (hunk 2) | `19080` | 17 keys added | extended-in-place |
| `toggleRecord` | `19230` | `flushing` flag; early-return guard and `record_stop` branch both skip when flushing | behaviour-changed (a press during flush starts a new take) |
| `requestMediaSpeedTest` neighbours | | new `requestStoragePreroll` beside it | extended-in-place |
| `installInteractions` Storage/System | | adds `storagePrerollButton`, `installBootConfigInteractions()` between restart and power-off listeners | extended-in-place |
| `installInteractions` frames-per-folder block and doc-level click/keydown for ladder links | `20663` | two global `document.addEventListener` delegations (click, keydown) added inside `installInteractions` | extended-in-place (new pattern, see 5) |

## 5. New abstractions

| Name | Where | Purpose | Upstream equivalent |
| --- | --- | --- | --- |
| `bootConfig` object (payload, form, review, text, editorMarks, timers) + `BOOT_CONFIG_TOGGLES`, `BOOT_CONFIG_MANAGED` | `19858-19880` | page-side model of the Boot Config card | upstream cards read `state.snapshot` or call `sendCommand` and re-render; no dedicated multi-field form model with dirty tracking found. New ground |
| `bootConfigPost`, `loadBootConfig`, `reviewBootConfig`, `saveBootConfig` | 19858-20660 | direct `fetch("/api/boot-config")` with JSON body, not `sendCommand` | upstream uses `sendCommand` for settings; `fetch("/api/config")` for the text file only. Boot Config goes the config-file way but with `X-Apertar-Revision` |
| `waitForCameraAfterReboot` | | polls `/api/buffer` every 2.5 s up to 240 s | upstream `requestRestartSystem` fires `restart_system` and toasts; no wait loop |
| `updateEditorGutter(editorId, gutterId, marks)` | 18770 | shared gutter for both editors | none |
| `configDiffLines` | 18817 | JS LCS line diff, `Uint16Array` per row | none (no diff UI upstream) |
| `renderBootConfigPort`, `bootConfigFormFrom`, `bootConfigEffectiveLink`, `bootConfigDirty` | | form <-> state mapping | none |
| `megahertzText`, `drmSummary`, `bootConfigSleep` helpers | | small formatters | none |
| document-level delegated click/keydown for `[data-ladder-link]` | 20690 | link inside toast and fields | upstream binds `getElementById(...).addEventListener` per element |
| `remote controls` loader `loadRemoteControls` (5 s retry timer) | 20880 | recurring `setTimeout` until `controlsState.model` | upstream polls via `fetchState` loop only |

Core-side modules named by this slice (other units own them): `src/hardware/BootConfigText.hpp` (about 1340+ lines), `scripts/apertar-boot-config` root helper, `HardwareConfigStore`.

## 6. Upstream removed, narrowed or hidden by this slice

| What | Effect |
| --- | --- |
| Media list overlay `#mediaBrowserOverlay`, its sort select, filter buttons, select-all/clear/download/delete buttons, close/refresh buttons | replaced by `#playbackOverlay` Clip Browser. Upstream's per-item delete (`deleteMediaLibraryItem`, `/api/media/delete`) has no caller left; route remains in Core (`ApertarCoreApp.cpp:9004`) |
| `clearMediaSelection` button (no equivalent button; selection cleared elsewhere) | narrowed |
| Direct save from Save Config button | now two steps (diff, then "Save these changes") |
| Download name `Apertar-Media-Selection.zip` and its pre-check toasts | moved into `pbDownloadSelected` (not verified in this slice; other unit) |
| Config save without revision (last writer wins) | now a stale tab is refused with 409 `old_page` (Core) |

## 7. Assumptions about the board (all in JS text, confirmed)

| Assumption | Line (@cinemate-port) |
| --- | --- |
| `/boot/firmware/config.txt` path default | `toggleBootConfigFile` 20005 (`|| "/boot/firmware/config.txt"`) |
| Pi 5 default section when no device tree: `"pi5"`, "reads config.txt as a Pi 5 would" | `bootConfigOwnLinesHint` 19925; `renderBootConfig` 20000 |
| cam0/cam1 two CSI ports default; single-port boards get one "Camera sensor" | `bootConfigPorts` |
| RP1 overclock `rp1-clk-333mhz`; "RP1 caps out near 43.8 fps at 4K whatever the sensor sends" | `renderBootConfigPort` 19963 |
| Pi 5 family gate for link-frequency lock when RP1 off (`board.family === "pi5"`) | 19960 |
| DPI panel takes GPIO 0-27, "I2C bus 1 (GPIO 2/3)" lost | 19950 and `reviewBootConfig` 20125 |
| Touch UI moves to the DPI panel | `reviewBootConfig` |
| `fan` appears as a managed config.txt line owned by the Thermal card (Fan mode) | `BOOT_CONFIG_MANAGED.fan` |
| `camera_auto_detect` forced 0 | `renderBootConfig` |
| Reboot takes "about half a minute", timeout 240 s | `rebootForBootConfig`, `waitForCameraAfterReboot` |
| `config.txt.apertar.bak` on the boot partition | timeout message |
| No four-core, RAM size or gpiochip number in this slice | |

## 8. Notes for later stages (facts, not judgement)

- The page-side Boot Config card is about 800 lines of JS inside the single C++ string; upstream cards in the System pane are far shorter (button + `sendCommand`).
- `bootConfigPost` uses `fetch` directly; the same file uses `sendCommand` for all Settings commands. The Core route wraps JSON into a command by string insertion (`ApertarCoreApp.cpp:9170-9195`).
- `/api/buffer` is the only route polled for liveness; a Core build without it would report "never-down".
- Two copies of "diff view" code: `showConfigDiff` (text) and `reviewBootConfig` (changes[] from Core); both use `.diff-*` classes.
- Blame attributes 23 lines of the Boot Config block to `bc12c0a` and 10 to `4629de2` (Clip Browser / Viewer commits): probable shared-formatting lines, or those commits touched the block; not settled. `git show bc12c0a -- src/web/WebControlPage.cpp` would settle.
- Fork-log carries no test record for `8a56545`, `2a4266e`, `3b87d99` beyond "Pi only"; unconfirmed.
