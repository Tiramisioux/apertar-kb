# Inventory WCP-07 (stage 1, no judgement)

Scope: `/home/user/build/review/diffs/WCP.part07.diff` (1587 lines, 17 hunks), new-file lines 13893-16360 of
`src/web/WebControlPage.cpp` @cinemate-port. Original file: `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0.
Content is the JS inside `webControlPageHtml()`: `mergeCameraStateFields`, `applyCommandSnapshotPatch`, the new clip-name composer,
`buildOptionButtons`, and (most of the slice) `renderSnapshot`. Playback overlay / viewer code is NOT in this slice
except one call `pbSnapshotChanged(snapshot)` at 16029 (bc12c0a); the function body is at 12021 (other unit).
Of the 2468 new-file lines, 1480 are unchanged upstream lines (`^35dbe67`); 988 were written by the port.
Line numbers: new-file (port). Hunks in the diff header use mixed numbering; ignore them.

## 1. Features touching this unit

| # | Feature | Lines (port) | Commits (fork-log status) |
| --- | --- | --- | --- |
| F1 | Clip names: pill composer in Settings > Record (drag and drop, long-press on touch, presets, live preview, auto-save after 350 ms) | 14453-15024 (572 lines, new block between `sendCommand` and `buildOptionButtons`), 15487 (`renderClipNames` call), 13929-13932 + 13978-13981 (snapshot fields + `set_clip_name_template` optimistic patch) | 014a2bf (fork-log:138 inside d44b177 row; Core host test `tools/clip_name_test.cpp`; fork-log: "Not yet run on the camera") |
| F2 | Mode Ladder: lock UI, FPS pill sub-lines "Resolution n", switch text, quick pill, locked selects/option rows, snapshot fields | 13907-13920 (fields), 15008-15024 neighbours; 15670-15671, 15877-15935, 15990, 16014-16030 | 1ef94fe, 920beb0, e6ee751, 2424a1f, 392e812, 66b324d, 9fa7918 (fork-log:93,94,97; "desk-tested, Pi check pending") |
| F3 | Speed Ramp state: snapshot fields, `set_fps_speed_ramp` optimistic patch, `renderSpeedRamp()` call, shutter green during ramp | 13921-13926, 13973-13977, 16026-16030, 15933-15935 | ac00fb0 (tested C0022 on camera), ca7b7c2 (experimental audio stretch, tested hardware-log), 1ef94fe |
| F4 | Value Lists: `renderValueListsEditor()` call, shutter options from `shutterAngleEntriesForSnapshot`, WB range max from steps list | 15029-15046 (`ff33d2d`/`392e812` at 15026-15046), 15258, 15288, 15744, 16027 | ff33d2d (tested 2026-10-28 Patrik) |
| F5 | Camera-set values green (`.system-value`): ISO shows `iso_actual`, WB shows `wb_actual_kelvin`, ISO Lock pill, `set_iso_auto enabled=false`, WB Auto greyed in Clear HDR | 13961-13963, 15399-15407, 15507, 15941-15966 | e25fd2b (tested), 15bba86 (built) |
| F6 | Write buffer: Frames/RAM switch card, buffer note parser, buffer safety stop pill logic, record button live during flush, record_start patch | 13975-13976, 14024-14032 (`set_buffer_mode`, `set_storage_preroll`, `set_cdng_log`), 14381-14386, 15215-15222, 15442-15486, 15754-15775, 15767-15768 | d44b177 (not run on camera), fb5801c, c5db8b2 (owner decision 2026-11-01) |
| F7 | Log (cDNG log) On/Off card + note | 15442-15470 | d44b177 |
| F8 | Storage pre-roll: PRE-ROLL status text/pill, pre-roll button disabling, auto On/Off row, last-result line, `markPrerollFps` | 15395-15398, 15757-15764, 15827-15861, 15917 | d44b177 |
| F9 | Media survive yanked drive: `media_alive` replaces `media_mounted` for `hasMedia`, "MEDIA REMOVED", record button gated on `!hasMedia`, eject sets `media_alive=false` | 14405, 15253-15255, 15388-15392 | 438a342 (fork-only, built) |
| F10 | UI timecode vs file timecode split (two pill rows) | 14069-14076, 16088-16098 | 909aaa5 (Pi only, "not tested"), 2c259b9 (labels) |
| F11 | Recording indicators: red frame, red timecode, frame-buffer bar, audio recorded outline | 14238-14249, 16132-16164 | f4fb084 (tested 2026-10-28), d44b177, 92d0970 |
| F12 | Performance card switches: Preview TDN, FPS phase lock, drive trim (+ env note), frames per folder, clip merge (+ env note, status, last) | 16165-16229 | e625c68, c810f85, ce0bd90, d7dd337, ba0658d (all "Pi only"; fork-log:170-188) |
| F13 | Resolution badge detail: "4K . 16-bit . Clear HDR" for raw | 15393-15397 | eaf9538, fee41e6 (tested) |
| F14 | Display fps `shownFps()`, codec label `codecDisplayLabel()`, `fpsStopToastText` on capped set_fps | 15440-15441 area, 15498, 15506, 15510, 15877-15932, 16360 | d44b177, 1ef94fe |
| F15 | Clip Browser hook `pbSnapshotChanged(snapshot)` in `renderSnapshot` | 16029 | bc12c0a (T49; tested with headless Chrome) |
| F16 | `/api/state` "system" fields copied to top level (`buffer_*`, `storage_preroll_*`) | 15222-15230 area (d44b177) | d44b177 |

## 2. Commands, routes, state, events, config, env, files, UI

### Socket commands sent from this slice (all via `POST /api/command`)

| Command | Payload | New or changed | Core handler @port (ApertarCoreApp.cpp) |
| --- | --- | --- | --- |
| `set_clip_name_template` | value | new | :13241 |
| `preview_clip_name` | value | new; sent by raw `fetch` not `sendCommand` | :13258 |
| `set_mode_ladder` | enabled | new (optimistic patch only here) | :14093 |
| `set_fps_speed_ramp` | enabled, shutter=exposure/..., audio=stretch/..., after=stay/return | new | :13223 |
| `set_cdng_log` | value auto/off | new | :13079 |
| `set_buffer_mode` | value frames/ram | new | :12829 |
| `set_storage_preroll` | value on/off | new | :12900 |
| `set_media_trim` | enabled | new | :13194 |
| `set_clip_merge` | enabled | new | :12857 |
| `set_frames_per_folder` | (Apply handler elsewhere) | new | :12857 |
| `set_preview_tdn` | enabled | new | :13205 |
| `set_fps_phase_lock` | enabled | new | :13214 |
| `set_recording_frame_enabled`, `set_frame_buffer_bar_enabled`, `set_recording_red_timecode_enabled`, `set_audio_recorded_outline_enabled` | enabled | new | :13505-13511 via `handleUiToggle` |
| `set_timecode_mode` | value, **target** ui/files (none = both) | changed (new `target` field) | :13279 |
| `set_iso_auto` | **enabled="false"** = Lock | changed | existing handler |
| `set_fps` | reply field `fps` compared with request | reply use changed | existing |

HTTP routes touched: `/api/command` (raw fetch in `clipRawCommand`). `/api/state` field handling changed (`system.*` copy). `/api/buffer`, `/api/media/frame` appear in other units.

### State fields read (all new in this slice unless noted)
`ladder_active, ladder_resolution, ladder_enabled, ladder_count, ladder_text, ladder_tops[], ladder_ramp_ready, fps_take_max, fps_max, fps_speed_ramp, fps_speed_ramp_keep_exposure, fps_speed_ramp_stretch_audio, fps_speed_ramp_after, clip_name_template, clip_name_example, cdng_log, cdng_log_available, cdng_log_bits, cdng_log_applied, buffer_setting, buffer_mode, buffer_note, buffer_safety_stop, buffer_* (from system), storage_preroll_active, storage_preroll_auto, storage_preroll_auto_env, storage_preroll_last, storage_preroll_* (from system), media_alive, media_state ("removed"), iso_actual, wb_actual_kelvin, wb_measured, wb_auto_after_clear_hdr, preview_tdn, fps_phase_lock, ui.recording_frame_enabled, ui.frame_buffer_bar_enabled, ui.recording_red_timecode_enabled, ui.audio_recorded_outline_enabled, system.media_trim_enabled, media_trim_env_off, frames_per_folder, frames_per_folder_env, clip_merge_enabled, clip_merge_env_off, clip_merge_pending, clip_merge_active, clip_merge_last`. Existing fields reused: `clear_hdr`, `timecode_mode`.

Browser-only state objects: `clipUi` (composer), `frameBufferBar` (defined 16419, used here), `state.fpsSwitchingTo`, `state.ladderServer`.

### Events / polling
None added in this slice. `updateFrameBufferBar` (16547) polls `/api/buffer` ~4 Hz (other unit; read here as consumer).

### Config keys, env vars, files
Config keys are not touched in this slice (UI shows them): `[storage] frames_per_folder`, `[storage] clip_merge`, `[media]` pre-roll auto, media trim.
Env vars named in UI strings: `APERTAR_STORAGE_PREROLL` (15861-15862 note + disables buttons), `APERTAR_MEDIA_TRIM=0`, `APERTAR_CLIP_MERGE=0`, frames-per-folder env (flag `frames_per_folder_env`, var `APERTAR_CDNG_FRAMES_PER_FOLDER`).
Files on disk: none from this slice. Clip file names are produced by Core (`src/util/ClipName.hpp`).

### UI elements (HTML ids used here; markup in other units)
Clip names: `settingsClipNamesCard, settingsClipNamesValue, clipNamePresets, clipNameRow, clipNamePalette, clipNamePreview, clipNameSaved, clipNameStatus`; css `.clip-pill .token/.text/.sep/.dragging/.clip-ghost/.clip-x/.clip-row-hint/.clip-example/.drop-before/.drop-end/.clip-status-error/.clip-status-ok/.clip-palette-group/.clip-palette-title`.
Log/buffer: `settingsCdngLogField, settingsCdngLogOptions, settingsCdngLogNote, settingsBufferModeField, settingsBufferModeOptions, settingsBufferModeInfo, settingsBufferModeNote`.
Pre-roll: `storagePrerollRow, storagePrerollButton, storagePrerollAutoRow, storagePrerollAutoOptions, storagePrerollAutoNote, storagePrerollLast`.
Ladder: `fpsLadderLine, quickLadderPill, resolutionOptions/cropRatioOptions/settingsRawBitDepthOptions .ladder-locked, settingsCdngCompressionLockField, data-ladder-lock, .ladder-switch, .pill-sub`.
Timecode: `settingsTimecodeOptions` (now "UI"), `settingsFileTimecodeOptions` (new); `settingsTimecodeValue` text removed.
Indicators: `previewStage .recording-frame`, `timecodeBlock .plain-timecode`, `settingsRecordingFrameOptions, settingsFrameBufferBarOptions, settingsRecordingRedTimecodeOptions, settingsAudioRecordedOutlineOptions`, status pill/dot `.preroll`, `.buffer-bar`.
Performance card: `settingsPreviewTdnOptions, settingsFpsPhaseLockOptions, settingsMediaTrimOptions, settingsMediaTrimNote, settingsFramesPerFolderInput/Apply/EnvNote, settingsClipMergeOptions/Note/Status/Last`.
Status text new: "PRE-ROLL", "MEDIA REMOVED"; ISO pill "Lock"; ISO/WB badges show the number, not "Auto".

## 3. Original (upstream 1.6.0) code modified in this slice

| Region (port line) | Upstream (@upstream-1.6.0 line) | Change | Kind |
| --- | --- | --- | --- |
| `mergeCameraStateFields` tail 13893-13985 | 8595 | 15 new `if (source.x)` blocks appended in the existing style | extended-in-place |
| `applyCommandSnapshotPatch` `set_iso_auto` 13961-13963 | 8703 | was `iso_auto = true`; now honours `enabled`, copies `iso_actual` into `iso` on Lock | behaviour-changed |
| same, new cases `set_fps_speed_ramp`, `set_clip_name_template`, `set_mode_ladder`, `set_cdng_log`, `set_buffer_mode`, `set_storage_preroll`, 4 UI toggles | switch at 8678 | extra `case` arms | extended-in-place |
| same, `set_timecode_mode` 14069-14076 | 8784 | single mode -> `target` ui/files; wrapped in braces | rewritten |
| same, `record_start` 14381-14386 | 8678 area | extra branch for safety-stop flush | extended-in-place |
| same, `eject_media` 14405 | 8678 area | also `media_alive=false` | extended-in-place |
| `buildOptionButtons` 15215-15222 | 9146 | body moved to new `buildOptionButtonsInto(container,...)`; wrapper kept; options get `system` (green) and `locked` (red warning on click) flags | moved + extended |
| `renderSnapshot` `cropRatioEnabled` 15249 | 9354 (upstream: `h264 \|\| cropControlsAvailable`) | port equals upstream; the fork-main `&& !snapshot.clear_hdr` removed | behaviour-changed vs fork main, same as upstream |
| `hasMedia` 15253-15255 | 9358 `!!snapshot.media_mounted` | `media_alive` first, fall back to `media_mounted` | behaviour-changed |
| `displayWhiteBalance` 15258 | 9361 `nearestWhiteBalance(kelvin)` | `Math.round(Number(kelvin)\|\|5600)`; `nearestWhiteBalance` no longer used here | rewritten |
| `shutterOptionSet` 15288 | `shutterOptions` const | `shutterAngleEntriesForSnapshot(snapshot)` | rewritten |
| `recordingStatus` text 15388-15392 | 9491 | PRE-ROLL, MEDIA REMOVED, pillRecording, WRITING guard | rewritten |
| resolution/fps/iso/wb badges 15393-15407 | 9492-9496 | detail text, `shownFps`, `iso_actual`, `wb_actual_kelvin`, `.system-value` | rewritten |
| `settingsTimecodeValue` setText | upstream has it | removed | removed |
| `settingsFpsSummary`, `settingsPreviewSourceValue`, `settingsIsoSummary`, `settingsCodecSummary`, `captureCodec` | various | `shownFps()`, `isoLabel`, `codecDisplayLabel()` | rewritten (1-line each) |
| CDNG compression disabled 15440-15441 | existing | added `\|\| ladderActive` | extended-in-place |
| `settingsRecordResolutionSelect` / `settingsRecordCropSelect` disabled 15670-15671 | `false` / `!cropRatioEnabled` | `ladderActive` added | behaviour-changed |
| `whiteBalanceRange` 15744 | 9788 | `max` set from `whiteBalanceStepsForSnapshot` | extended-in-place |
| status pill/dot/record button 15754-15775 | 9840-9870 | `isRecording` -> `pillRecording`; `recordButton.disabled` adds `!hasMedia` and flush clause | behaviour-changed |
| `fpsOptions` build 15877-15935 | `buildOptionButtons("fpsOptions", fpsOptions,...)` | `fpsOptionEntriesForSnapshot`, ladder sub-lines, switching state, toast on capped fps | rewritten |
| ISO options handler 15941-15942 | existing | extra `Lock` branch | extended-in-place |
| WB mode options 15966 | existing | Auto disabled when `clear_hdr` | behaviour-changed |
| resolution/crop/bit-depth option builders 15978-16014 | existing | wrapped in `ladderLockedOptions`, `locked` flag | extended-in-place |
| `settingsTimecodeOptions` 16088-16098 | 10021 | one builder -> loop over two (ui/files) | rewritten |
| `renderSnapshot` entry 15222-15230 | 9327 | `system.*` copied to top level | extended-in-place |

## 4. New abstractions in this slice

| Name | What | Upstream equivalent |
| --- | --- | --- |
| `clipUi` + `clip*` function family (22 functions, 572 lines) | pill composer: parse/serialize template, HTML5 DnD + Pointer-Events long-press drag, ghost element, text-pill editor, debounce save | none. No drag and drop anywhere in upstream WCP (`grep dragstart` upstream: 0; port: 2). Closest: plain `buildOptionButtons` pill rows (upstream :9146) |
| `clipRawCommand` | second `fetch("/api/command")` wrapper beside `sendCommand` (to avoid toasts and optimistic patch) | `sendCommand` upstream (8678 region) is the only caller |
| `buildOptionButtonsInto(container,...)` | element-based variant of `buildOptionButtons` | none (upstream takes an id only) |
| `frameBufferBar` object (defined 16419) | client-side buffer fill/pre-roll/safety-stop state, own 4 Hz poll timer | none |
| `.system-value` class + `markActiveSystemValue`, `isoSetByCamera` | green = camera decided | none; upstream has no such colour language |
| option flags `locked`, `system` | per-option red-warning and green styling | none |
| State fields `fpsSwitchingTo`, `ladderServer` | ladder UI state on `state` | none |

## 5. Upstream behaviour removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| `Auto` text on ISO/WB badges | 15399-15407 | shows the number when Core reports `iso_actual` / `wb_actual_kelvin` |
| White balance Auto choice | 15966 | disabled in Clear HDR |
| `nearestWhiteBalance` snapping | 15258 | WB shown unsnapped (rounded Kelvin) |
| Single `Timecode` mode row / `settingsTimecodeValue` pill | 16088, removed setText | replaced by UI + File rows |
| Resolution, crop, bit depth, compression controls | 15440, 15670, 15990 | greyed while ladder active; click shows warning |
| Record button during `media_writes_pending` | 15763 | enabled during a safety-stop flush |
| Record state | 15754-15764 | REC pill hidden while `buffer_safety_stop` though `recording` is true |
| `Math.round(snapshot.fps)` badge | 15405 | `shownFps()` (may differ from `snapshot.fps` in ramp/pre-roll) |
| fork-main `clear_hdr` crop lock | 15249 | removed (matches upstream) |

## 6. Board and hardware assumptions in this slice

| Assumption | Where | Note |
| --- | --- | --- |
| Pi model / cores / RP1 / PCIe / gpiochip / I2C | none in this slice | confirmed by reading the diff |
| RAM size | 15485-15486 text "up to 60 % of free memory", "12 frames", "90 % full"; parse of `buffer_note` regex `ram budget (\d+) MiB .*frame ([\d.]+) MiB = (\d+) frames` (15461) | numbers are Core constants hardcoded in UI strings; UI breaks silently if Core rewords the note |
| Sensor | 15492-15493 "in SDR the sensor chip already compresses the raw stream ... Log works in Clear HDR (16-bit)" | IMX585-specific text; token sample "IMX585" 14470 |
| Sample clip tokens | 14452-14485 | static examples only |
| Touch / haptics | `navigator.vibrate`, long-press 300 ms, move tolerance 10 px | browser, not board |
| Drive | trim note: "Deleted takes cannot be recovered afterwards" 16179 | SSD / SD generic |
| `APERTAR_*` env names mirrored in UI text | 15861, 16183, 16222 | env var names appear in operator-visible strings |

## 7. Notes for stage 2

- Fork-log marks F10 (909aaa5) "not tested", F2 "Pi check pending", d44b177 "Not yet run on the camera"; F11, F5, F4, F3, F13 tested on camera by Patrik.
- fork-log:101 says the Clip Browser (bc12c0a) replaces the media list overlay; only the hook line is in this slice.
- The hint "playback overlay, viewer, system pane" does not match the slice; the System pane part is F8/F12 (16165-16229, 15827-15861).
- No Core handler needed an upstream compare; upstream has no `preview_clip_name`, `set_clip_name_template`, etc. (confirmed by grep earlier is limited to port file; upstream App not grepped for all, unconfirmed for the 16 commands, command: `grep -c` each name in `/home/user/wt/core-upstream/src/ApertarCoreApp.cpp`).
