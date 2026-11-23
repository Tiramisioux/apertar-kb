# Feature list: WebUI page

Area: what the cinemate port added to the WebUI of original Apertar 1.6.0 (`src/web/WebControlPage.cpp`, one page in one C++ string, port 8000).
Sources: inventories WCP-01 to WCP-10, `raw/FEATURES.json`, `fork-log.md`, commit messages. Names of commands, routes, keys and element ids were re-checked by grep in `/home/user/Apertar-Core` @cinemate-port `01f170c` (`WCP` = the page file, `App` = `src/ApertarCoreApp.cpp`).

"Stock camera" = a camera running `cinemate-port` with no config edits. Already done on the improvement branch (`/home/user/wt/core-work`), do not list as open: the GPIO chip setting is back on the Controls page and its checks are per chip (`04fe197`). Nothing else in this area is fixed yet.

Relation words: extends in place / beside upstream / replaces upstream / new area. "Desk" = headless Chrome, `node --check`, host test; no camera. "Pi" = run on the camera. The page itself has no unit tests; every "tested" below is the commit message or fork-log, not proof (BRIEF rule 5).

## Table

| # | Feature | Default for a stock camera | Relation to 1.6.0 | Tested |
| --- | --- | --- | --- | --- |
| 1 | Clip Browser (card grid, select, download, remove) | on, replaces the media list | replaces | desk, headless Chrome against a Pi's Core 2026-10-29 |
| 2 | Clip Viewer with frame stepping, histogram, info and sound | on | new area | Pi 2026-10-29 (Chrome only) |
| 3 | Settings search | on | new area | desk (`node --check`); "Not run yet" in the commit |
| 4 | Clip names composer | on; default name unchanged | new area | host test of the Core part; page not run |
| 5 | Recording indicators: red frame, red timecode, frame buffer bar, audio outline | frame off, bar off, red timecode on, outline on | extends in place | frame and red timecode Pi 2026-10-28; others not |
| 6 | Status pill states: buffer bar, safety-stop drain, blue PRE-ROLL | invisible until the buffer bar or pre-roll is used | extends in place + beside | not run on the camera in a browser |
| 7 | Performance card (preview TDN, drive trim, phase lock, frames per folder, clip merge) | trim on, merge on, TDN off, phase lock off, split off | new area (new card) | desk; builds on the Pi; not run |
| 8 | UI timecode and file timecode, named Time of Day and Clip | both follow one setting until changed | extends in place + renames | built, not tested; labels `node --check` |
| 9 | Readout and preset changes: exact shutter angle, time left rounded down, bit depth in the resolution badge, Log in the codec label, presets carry the new keys | on | extends / rewrites in place | mostly Pi 2026-10-27/28 |

Left to other areas (one line each at the end): Mode Ladder pages, Speed Ramp card, Value Lists card, IMX585 and IMX283 resolution pills, camera-decided values and ISO Lock, Controls pane, Hardware card, Remote controls, Config editor aids, Boot Config card, Log / write buffer / storage pre-roll controls, yanked-drive display.

## 1. Clip Browser

- **Operator gets:** the folder button opens a grid of clip cards (thumbnail, duration, dropped-frame count, name, format, shot date, timecode) with a filter (Clips, Stills, Timelapse, Audio), a newest/oldest sort, long-press selection, Select All, Download Selected and Remove Selected.
- **How used:** folder button on the main page (greyed during a take or timelapse); the live view steps aside while it is open; the phone Back button closes it. Opens on Stills in photo mode. In a playback hold (Core busy with a take) the cards come from Core's cache and no thumbnails are asked for.
- **HTTP / socket:** `GET /api/media` (payload grew: `held`, `shot_ms`, `first_number`, `token`, `playable`, `format`, `ramp`, `missing_frames`, `empty_frames`, `timecode_start`), `GET /api/media/frame?kind=folder&id=&n=&w=&v=` (thumbnails, two at a time, lazy), `GET /api/media/clip`, `POST /api/media/delete-selected`, `GET /api/media/download-selected`. The last two routes exist in 1.6.0 (`App` upstream, the old list called them); the port calls them from new buttons.
- **State fields:** page-only `state.pb` (nested object), `state.previewPausedForPlayback`; from Core `playback_hold`, `ui.photo_mode_enabled`. Config keys: none. Env vars: none on the page (Core: `APERTAR_PLAYBACK_WORKERS`, see recording list).
- **Touches in 1.6.0:** `WCP` media list overlay (`#mediaBrowserOverlay` and 14 ids, the `.media-browser-*` CSS, 36 rules) is removed. `#playbackOverlay`, `pbGrid`, `pbShowButton`, `pbSortButton`, `pbSelectionActions`, `pbRemoveScrim` take its place. `setMediaBrowserOpen` is rewritten, `body.media-browser-open` becomes `body.pb-open` (declared twice). Upstream function names and `mediaBrowser*` state are replaced by `pb*` functions and `state.pb`. First use of the History API in the page. Relation: replaces upstream code. What the 1.6.0 list had and the port dropped: per-row Download and Delete, size, fps and frame-count lines (WCP-02-F8, WCP-03-F3, WCP-06-F4).
- **Needs:** Core of the same build (frame route, facts cache, hold). Thumbnails are drawn by Core; nothing in the browser decodes DNG.
- **Tested:** `bc12c0a` "desk (headless Chrome against the Pi's Core, read-only); Pi build pending"; `27eac5a` desk, laptop and 390 px; `a40112a` desk (`node --check`), Pi build. fork-log:101 "Pi only; tested 2026-10-29". Safari, Firefox, phone not recorded.
- **Commits:** `bc12c0a` `27eac5a` `a40112a`.
- **For development:** a developer who knows 1.6.0 finds none of the old function names; the media list is now a sub-application with its own state, scrim dialog, history entries and `.pb-*` CSS (review items WCP-03-F1, WCP-06-F1). Any change to the media routes must also keep the hold rule (409 in a hold), see the recording list items 16 to 18.

## 2. Clip Viewer with sound

- **Operator gets:** a tap on a card plays the clip in the browser like the touch UI: picture, play/pause, scrub, frame step with hold-to-repeat, previous/next clip, histogram, recorded timecode, a frame-rate badge that tells the truth, black for dropped frames, an Info panel, Download and Remove. The take's recorded WAV plays with it and is the clock.
- **How used:** tap a card in the Clip Browser. Space plays and pauses, arrows step, Escape backs out one level, the tab pauses when hidden, Back on a phone leaves the viewer first. During a hold a card offers Live view and Wake.
- **HTTP / socket:** `GET /api/media/clip?kind=folder&id=`, `GET /api/media/frame` (answers with `X-Frame-Number`, `X-Frame-Index`, `X-Histogram`; 409 in a hold, 503, 404), `GET /api/media/file?kind=folder&id=&name=<clip>.wav` (Range: 200, 206, 416; 409 in a hold). Socket commands `user_activity` (via `POST /api/command`, every min(20 s, standby/3) while playing) and `wake`.
- **State fields:** page `state.pb.viewer`, `state.pb.page`; from Core `standby_timeout_seconds`; clip reply `audio_url`, `sound_text`. A ramp take plays silent (sound off) and shows a timeline. Config keys, env vars: none on the page.
- **Touches in 1.6.0:** nothing in the old page had a viewer (only list and download links). New area, the touch UI already had `qml/ClipPlayerPage.qml` in 1.6.0. Beside: `WCP` Clip Browser (feature 1) whose overlay hosts it. Core side: `PlaybackFrames`, `DngFrameReader`, `streamFileRangeToClient` (recording list items 16 to 19).
- **Needs:** Core playback code and liblj92 (`third_party/`); a browser that can play the WAV (else the viewer continues silent with a toast). Player pacing (0.35 s look-ahead, two lanes at 640 px) was measured on a Pi 5 only.
- **Tested:** `4629de2` desk (24 fps and 9 fps clips); fork-log:102 "tested 2026-10-29 (24 fps Clear HDR 16-bit, 9 fps lossless; Patrik: works well)"; fork-log:104 Range, 416 and Chrome playback with sound tested; Safari, Firefox, phone not tested. `4fa0432` has no test line.
- **Commits:** `4629de2` `4fa0432` `fa19856`.
- **For development:** the page keeps its own clock and picture queue; open bugs in the review (stale badges for non-cDNG items, blank clip opened in a hold, freeze when the WAV is shorter, WCP-06-F5 to F7) are in `fix-list-webui.md`. The WAV route serves only a `.wav` inside the clip folder; widening that name check opens file download by path.

## 3. Settings search

- **Operator gets:** a search box above the Settings sidebar; typing shows all panels at once and keeps only the cards (or rows of large cards) that match all words.
- **How used:** type in `#settingsSearchInput`; Escape clears the search before it closes Settings. "No setting matches" shows when nothing fits.
- **HTTP / socket / state / config / env:** none. 17 `data-search` keyword attributes and a `MutationObserver` that re-runs the filter after each 1 Hz render.
- **Touches in 1.6.0:** `.settings-panel` one-panel display (overridden while searching), the Settings keydown and nav click handlers (extended). Relation: new area; classes `.searching`, `.search-hidden`.
- **Needs:** nothing.
- **Tested:** `d44b177` "node --check of the page script; nothing opened in a browser". No later record.
- **Commits:** `d44b177` (inside the 19-commit squash).
- **For development:** a new card is found only by its visible text plus its `data-search` words; add keywords with every new card. The touch UI has no search; it is a WebUI-only aid.

## 4. Clip names composer

- **Operator gets:** pick a preset or drag token, separator and text pills into a row to name clip folders, frames, sound and video files; a live example name and an ok or error line.
- **How used:** Settings, Record, Clip names card (`#settingsClipNamesCard`). Auto-saves; locked while recording ("Clip names cannot be changed while recording.").
- **Socket:** `set_clip_name_template`, `preview_clip_name`. State: `clip_name_template`, `clip_name_example`. Config: `clip_name_template` in `camera_settings.conf`. Env: none. Preset import knows the key (`cameraClipNameTemplate`).
- **Touches in 1.6.0:** the 1.6.0 clip-name card (upstream reorders by buttons) is replaced by a drag and long-press composer of about 570 lines; the Core naming code is replaced by `src/util/ClipName.hpp` (recording list item 10). The touch UI has `qml/ClipNameCard.qml`, `ClipNamePill.qml`. Relation: replaces the page part, new area for the engine.
- **Needs:** nothing extra. The page keeps its own composer state outside `state`.
- **Tested:** `014a2bf` has no Tested line; `tools/clip_name_test.cpp` host test for the Core part; KB `working/drop-frames/README.md:102` "WebUI composer and touch card untested by hand".
- **Commits:** `014a2bf`.
- **For development:** the composer and Core's `ClipName.hpp` must accept the same tokens; a new token goes into both and into the touch card. Review item WCP-07-F1 (570 lines for one string) is open.

## 5. Recording indicators

- **Operator gets:** four switches in the Live preview card: a red border round the preview during a take, the take timecode red or white, the frame buffer bar in the REC pill, and an "Audio recording outline" switch.
- **How used:** Settings, Live preview card (`#settingsRecordingFrameOptions`, `#settingsRecordingRedTimecodeOptions`, `#settingsFrameBufferBarOptions`, `#settingsAudioRecordedOutlineOptions`).
- **Socket:** `set_recording_frame_enabled`, `set_recording_red_timecode_enabled`, `set_frame_buffer_bar_enabled`, `set_audio_recorded_outline_enabled` (all four listed in the `commands` reply, `App:12930`; handled in `App:13505` ff.). State: `ui.recording_frame_enabled`, `ui.recording_red_timecode_enabled`, `ui.frame_buffer_bar_enabled`, `ui.audio_recorded_outline_enabled`. Config: `UI.conf [General] recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `frameBufferBarEnabled`, `audioRecordedOutlineEnabled`. Env: none.
- **Touches in 1.6.0:** `.preview-stage` and `.time-card` (new state classes `recording-frame`, `plain-timecode`), `UiSettings` snapshot in `App` (four fields, `App:1904-1907`), preset `allowedKeys`. Relation: extends in place.
- **Needs:** nothing. The audio outline switch only has an effect in the touch UI and the external monitor (`qml/CameraPage.qml`, `ExternalMonitorWindow.qml` read `audioRecordedOutlineEnabled`); grep finds no WebUI element that reads it, so on the page it is a switch with no visible result.
- **Tested:** `f4fb084` "desk only"; fork-log:81 "tested 2026-10-28 (Patrik)" for frame and red timecode. `92d0970` and the buffer bar switch: no test line.
- **Commits:** `f4fb084` `92d0970` `d44b177`.
- **For development:** the four switches follow the UI.conf pattern of 1.6.0 (monitoring aids); adding a fifth means Core state, command, `UI.conf` key, snapshot copy and preset key. The review notes they sit in the Live preview read-out card (WCP-03-F7).

## 6. Status pill states: buffer bar, safety-stop drain, PRE-ROLL

- **Operator gets:** with the buffer bar switched on, the REC/READY pill fills red as the RAM write buffer fills. After a buffer safety stop the pill turns green READY while the bar drains, with a toast, and pressing record starts a new take at once (queued frames are discarded, a toast says how many). A storage pre-roll turns the pill and dot blue and reads PRE-ROLL.
- **How used:** nothing to press; switch on "Frame buffer bar" (feature 5) and set the write buffer to RAM (recording list item 12). The blue pill needs no switch.
- **HTTP / socket:** `GET /api/buffer` (`App:8419`), polled about 4 Hz only while the bar option is on and a take or drain runs, or for 5 s after the pre-roll button; `storage_preroll`. State: `buffer_mode`, `buffer_fill`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `storage_preroll_active`, `storage_preroll_fps`.
- **Touches in 1.6.0:** `.status-pill` and `.status-dot` (new classes `buffer-bar`, `buffer-drain`, `preroll`; the pill is now `position: relative; overflow: hidden` in every state), `toggleRecord` (changes behaviour during a flush), the 1 Hz snapshot copy. A second poll loop runs beside the page's own 1 Hz state poll (review WEB-4). Relation: extends in place plus a parallel poll.
- **Needs:** Core RAM write buffer and storage pre-roll (recording list items 12 and 13). Pill text, fps italics and toast copy hard-code 60 %, 12 frames and 90 % (WCP-07-F4).
- **Tested:** `d44b177` "host tests, node --check, nothing opened in a browser; ram queue, safety stop, buttons not run yet"; KB drop-frames README:101 a real safety stop measured on the camera 2026-11-01, the READY pill "read from code". `c5db8b2` (record during flush): owner decision 2026-11-01, no test line.
- **Commits:** `d44b177` `c5db8b2` `fb5801c`.
- **For development:** the page infers the state from several fields at two poll rates; the touch UI draws the same states from Core. A change to the safety-stop rule changes both.

## 7. Performance card

- **Operator gets:** one card in Settings, System, with switches for preview temporal denoise, drive trim, frame-rate phase lock, a "frames per folder" field (0 = off, 100 to 100000) and clip merge, with notes where an environment variable overrides the setting and a merge status line.
- **How used:** Settings, System, Performance (`#settingsPerformanceCard`; `#settingsPreviewTdnOptions`, `#settingsMediaTrimOptions`, `#settingsFpsPhaseLockOptions`, `#settingsFramesPerFolderInput` + Apply, `#settingsClipMergeOptions`).
- **Socket:** `set_preview_tdn`, `set_media_trim`, `set_fps_phase_lock`, `set_frames_per_folder`, `set_clip_merge`. State: `preview_tdn`, `media_trim_enabled`, `media_trim_env_off`, `fps_phase_lock`, `frames_per_folder`, `frames_per_folder_env`, `clip_merge_enabled`, `clip_merge_env_off`, `clip_merge_pending`, `clip_merge_active`, `clip_merge_last`. Config: `camera_settings.conf` `preview_tdn`, `media_trim`, `fps_phase_lock`; `apertar-hardware.conf [storage] frames_per_folder`, `clip_merge`. Env: `APERTAR_MEDIA_TRIM`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE` (`APERTAR_PHASE_LOCK_*` for the lock).
- **Touches in 1.6.0:** nothing in the old page; the card is new in the System pane. Core: `CameraSettings` (`Types.hpp:138-140`: `fpsPhaseLock` false, `previewTdn` false, `mediaTrimEnabled` true), tuning selection, trim worker, merge worker (recording list items 14 and 15, camera list item 10). Relation: new area.
- **Needs:** `scripts/apertar-media-trim` and the root helper for trim; a tuning file with `rpi.denoise` for TDN (see camera list); `tools/flatten_clip.py` to flatten split clips by hand.
- **Stock camera sees:** preview TDN off. In 1.6.0 the stock tuning was loaded as is; now it is stripped unless the switch is on, and recorded H.264 and ProRes change too (CC-3-F7). Drive trim on and merge on by default (Media-buffer-split-F6).
- **Tested:** `ce0bd90` "desk only"; `e625c68` and `c810f85` "desk only (not built: no libcamera on the Mac)"; `d7dd337` and `ba0658d` host tests plus a Pi build, "not yet run on the camera". fork-log:170-188 "Pi only".
- **Commits:** `ce0bd90` `e625c68` `c810f85` `f4a1393` `d7dd337` `9ec37b5` `ba0658d` `68516f1` `01f170c`.
- **For development:** the card mixes camera, preview and storage settings (WCP-03-F9); each switch has its own Core command rather than the generic setter path. The page shows the env override note from a state field, so a new env override needs its `_env` state field.

## 8. UI timecode and file timecode

- **Operator gets:** two separate timecode settings, one for what the screen shows and one for what goes into the files, each "Time of Day" or "Clip". Stored values stay `free_run` / `rec_run`.
- **How used:** Favourites (blocks "UI Timecode" and "File Timecode") and the Timecode card (`#settingsTimecodeOptions`, `#settingsFileTimecodeOptions`).
- **Socket:** `set_timecode_mode value=free_run|rec_run target=ui|files|both` (no target = both; `App:13279`). State: `timecode_mode`, `ui.timecode_mode`. Preset: an older preset still sets both, a new `cameraTimecodeMode` no longer overwrites the UI copy. Config / env: none new.
- **Touches in 1.6.0:** `set_timecode_mode` (extended in place), the Favourites timecode block (rewritten into two), the Timecode card (lost its current-value pill, WCP-03-F14), the `Free Run` / `Rec Run` labels (renamed on screen, WCP-05-F2).
- **Needs:** nothing. The Core split is the main part; the touch UI is not covered by this inventory.
- **Tested:** `909aaa5` "desk, Pi build pending"; fork-log:98 "built 2026-10-29, not tested"; `2c259b9` `node --check` only.
- **Commits:** `909aaa5` `2c259b9`.
- **For development:** any code that reads `timecode_mode` must decide between the UI copy and the file copy; the touch UI and the hardware inputs each need the same treatment.

## 9. Readout and preset changes

- **Operator gets:** the shutter angle shows the running angle (86.4 deg) instead of the nearest stop; time left rounds down to match the touch UI; the resolution badge reads for example "4K . 16-bit . Clear HDR" on raw takes; the codec reads "CinemaDNG RAW . Log" while Log is applied; imported presets carry Log, Clear HDR, phase lock, timecode mode, conform fps, speed ramp, clip-name template and the recording-indicator switches.
- **How used:** automatic; presets through the existing Presets pane.
- **HTTP / socket:** `POST /api/presets/import` (existing route; the page's `allowedKeys` list, `WCP:19028` ff., grew by 17 keys). State read: `cdng_log_available`, `cdng_log_bits`, `cdng_log_applied`, `record_time_left_minutes`. Config / env: none.
- **Touches in 1.6.0:** `formatAngle` (rewritten: upstream snapped to the nearest `shutterOptions` entry; now `formatAngleValue` prints the exact value, 2 decimals), `formatMinutes` (floor instead of round), resolution badge helpers, Favourites codec label (helper beside upstream labelling), preset import `allowedKeys`. Relation: extends or rewrites in place.
- **Needs:** nothing.
- **Tested:** `bda2066` done (Patrik 2026-10-27); `eaf9538` tested 2026-10-28; `ff33d2d` (angle) tested 2026-10-28; `fee41e6` reverted a "16 b" label after Patrik's request; Log suffix and preset keys desk only.
- **Commits:** `ff33d2d` `bda2066` `eaf9538` `e58ae40` `fee41e6` `d44b177` `ac00fb0` `92d0970` `014a2bf`.
- **For development:** an exact angle matches no pill, for example 60 fps at 22.5 deg leaves no pill active (WCP-03-F4); keep the pill match tolerance in mind when the pills are rebuilt. Every new setting that should survive a preset needs a line in `allowedKeys` and a Core preset key.

## Seen in these units, main home is another area

| Feature seen on the page | Main home |
| --- | --- |
| Mode Ladder card, Activated sensor modes card, Modes pane, ladder lock on Resolution / Crop / Bit Depth / Compression, FPS pill resolution lines, lazy load of the Modes pane | camera modes list, item 1 |
| IMX585 resolution families, 3840x2072 and 1920x1036 sizes, ratio row, 25 fps Clear HDR cap; IMX283 pills and 10/12-bit depth | camera modes list, items 2 and 5 |
| Camera-decided values in italics, ISO Lock, ISO list to `iso_max`, WB Auto greyed in Clear HDR | camera modes list, item 9 |
| Speed Ramp card, ramp shutter marking | recording list, item 9 |
| Log switch, write buffer mode and note, storage pre-roll button and Auto switch, the media-fault display (NO MEDIA, MEDIA REMOVED, record greyed) | recording list, items 1, 6, 12, 13 |
| Value Lists card (chips, free stepping, flicker-free angles, mains 50 / 60 Hz), `set_value_steps` | hardware config and inputs area |
| Controls pane, Hardware card with I2C scan, GPIO out and Tally LED row, Remote controls card, Try buttons, Listen, Undo last save; `get_controls`, `set_controls`, `list_actions`, `test_input`, `test_output`, `scan_i2c`, `controls_history` | hardware config and inputs area (`fix-list-hardware.md`) |
| Config editor aids (gutter, Check, diff before save, history, revision header, 409 on a stale save) | hardware config and inputs area |
| Boot Config card, `/api/boot-config`, `/api/boot-config/parse`, the root helper `apertar-boot-config` | hardware config area; the free-text write to root is blocker WEB-1 in `fix-list-webui.md` |
