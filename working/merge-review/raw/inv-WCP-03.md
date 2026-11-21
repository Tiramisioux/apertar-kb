# Inventory WCP-03: WebControlPage.cpp, HTML body slice (port lines 4041-7162)

Stage 1 of 3: inventory. Facts only, no verdicts. Written 2026-11-17.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/WCP.part03.diff`, 1224 lines, 20 hunks (CSS tail 1, HTML 17, JS tail 3 incl. `state`, `settingsPanelMeta`, `formatAngle`), read whole |
| Port file | `/home/user/Apertar-Core/src/web/WebControlPage.cpp` @cinemate-port `01f170c`, lines 4041-7162 (hunk 20 runs to 7190: `formatAngle`) |
| Original | `/home/user/wt/core-upstream/src/web/WebControlPage.cpp` @upstream-1.6.0 `35dbe67`. Port lines 4041-7162 map to about U:2061-4870 |
| Content | One CSS tail (the 720px media block), the whole HTML body (Camera settings, Settings overlay: nav, Record, Modes, Monitoring, System, Controls, Config panes, Playback overlay) and the start of the JS (`settingsPanelMeta`, `state`, `formatAngle`) |
| Blame | `git blame -s -L 4041,7162 cinemate-port`: 2543 lines unchanged from `35dbe67`, 579 lines written by 34 port commits (section 11) |
| Shorthand | `P:n` = port file @cinemate-port. `U:n` = upstream file @upstream-1.6.0. `App:n` = `src/ApertarCoreApp.cpp` @cinemate-port. `CC:n` = `src/camera/CameraController.cpp` @cinemate-port |
| Labels | confirmed = read in code. probable = inferred, reason given. unconfirmed = not settled, command given. No label = confirmed |
| Not done | No browser run. How the page looks and whether each handler works is unconfirmed. Settle: `--simulate` Core, headless Chrome on port 8000. The JS that drives these elements sits in WCP-04 onward; the handler lines below are pointers only |
| Tested column | Quotes commit message and fork-log. Intent, not proof (BRIEF rule 5) |

## 1. Hunks (new-file line ranges)

| # | Port lines | What | Commits |
| --- | --- | --- | --- |
| 1 | 4041-4104 | 720px `@media`: `.media-browser-*` selectors dropped from five grouped rules | `bc12c0a` |
| 2 | 4502-4529 | Camera settings card: ladder pill, ladder note under Frame rate | `5dfbc6c` |
| 3 | 4558-4590 | New "Remote controls" card after Camera settings | `1319967` |
| 4 | 4722-4783 | Settings nav: search box, Modes and Controls items | `d44b177`, `854fe43`, `f5fe41b` |
| 5 | 4892-5018 | Record pane: Compression id, Log, Write buffer, Clip names card, Speed Ramp card | `392e812`, `d44b177`, `1ef94fe`, `014a2bf`, `24355d3` |
| 6 | 5074-5104 | Record pane: Timecode card split into UI timecode and File timecode | `2c259b9`, `909aaa5` |
| 7 | 5141-5200 | New Modes pane (Activated sensor modes, Mode Ladder) | `854fe43` (moved from Record), `1ef94fe`, `920beb0`, `da8ca9f`, `4b14a79` |
| 8 | 5264-5301 | Monitoring pane: four recording-indicator switches | `f4fb084`, `d44b177`, `92d0970` |
| 9 | 5659-5742 | System pane: `data-search` on three Media cards | `d44b177` |
| 10 | 5759-5838 | System pane: storage pre-roll rows, new Performance card | `d44b177`, `ce0bd90`, `e625c68`, `c810f85`, `d7dd337`, `ba0658d` |
| 11 | 5849-5961 | System pane: new Boot Config card | `8a56545`, `3b87d99`, `2a4266e` |
| 12 | 6127-6246 | New Controls pane (Controls card, Value Lists); Config pane: Hardware card, saved versions, gutter, issues, diff, Check | `f5fe41b`, `d282de9`, `8be1ab5`, `6777ebe`, `effb804` |
| 13 | 6335-6494 | Media list overlay removed; Playback overlay (Clip Browser, Clip Viewer, Remove dialog) added | `bc12c0a`, `4629de2`, `fa19856` |
| 14 | 6618-6686 | `settingsPanelMeta` gets `modes` and `controls` | `854fe43`, `f5fe41b` |
| 15 | 6712-6735 | `state`: ladder fields, `valueListsSignature`, `fpsSwitchingTo`, `configRevision`, `pb`; media fields removed | `1ef94fe`, `920beb0`, `da8ca9f`, `ff33d2d`, `effb804`, `bc12c0a`, `4629de2` |
| 16 | 7162-7190 | `formatAngle`: nearest-stop snap replaced by exact angle; new `formatAngleValue` | `ff33d2d` |

## 2. Features that touch this slice

| Id | Feature | Operator gets | Elements here | Commits | Relation to upstream | Tested, as recorded |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Clip Browser (T49) | A card grid of clips with thumbnails, drop counts, long-press select, Remove/Download Selected, Show filter, sort chip | `#playbackOverlay`, `#pbBrowserPage` P:6335-6385 | `bc12c0a`, `27eac5a` | Replaces upstream code: U media list overlay `#mediaBrowserOverlay` removed (0 refs left at HEAD) | `bc12c0a`: "desk (headless Chrome against the Pi's Core, read-only); Pi build pending". fork-log:101 "Pi only; tested 2026-10-29" |
| F2 | Clip Viewer (T50, T51) | Plays a clip in the browser: canvas, badges, scrub, frame step, prev/next clip, histogram, metadata panel, audio from the WAV | `#pbViewerPage` P:6393-6474, `#pbvAudio` P:6410 | `4629de2`, `fa19856` | New ground in the WebUI. The touch UI has `qml/ClipPlayerPage.qml` @upstream-ui | `4629de2`: desk, 24 fps and 9 fps clips. `fa19856`: "Pi build pending". fork-log:102, 104 "Pi only; tested 2026-10-29" |
| F3 | Settings search | A search box in the Settings sidebar filters cards by `data-search` words | `#settingsSearchInput` P:4732-4736; 12 `data-search` attributes | `d44b177` | New ground. Upstream has no search and no `data-search` | `d44b177`: "Not run yet" for the page parts. fork-log:138 "WebUI Settings search" |
| F4 | Mode Ladder | Resolution switches by FPS: on/off, running-now, editable list of resolutions, greyed controls with link, ladder line under Frame rate, pill on the card | Modes pane P:5151-5200 (`#settingsModeLadderCard`, `#settingsModeLadderOptions`, `#settingsModeLadderList`, `#settingsModeLadderNow*`), `#quickLadderPill`, `#fpsLadderLine` P:4512, 4519, `#settingsCdngCompressionLockField` P:4902 | `1ef94fe`, `920beb0`, `da8ca9f`, `5dfbc6c`, `392e812`, `854fe43` | New ground. Upstream has fixed resolution pick only | `1ef94fe`: "desk (headless Chrome against the Pi's Core state); Pi build pending". `920beb0`: "node --check only". fork-log:94, 97 "desk-tested, Pi check pending" |
| F5 | Activated sensor modes | Aspect-ratio filter, collapsible groups, crop thumbnails, per-mode toggle | `#settingsSensorModesCard`, `#settingsSensorModeAspectFilters`, `#settingsSensorModeGroups` P:5153-5163 | `1ef94fe`, `da8ca9f`, `4b14a79`, `854fe43` | New ground | `4b14a79`: "desk only (node --check)". fork-log:146 "on the Pi" |
| F6 | Speed Ramp | Change FPS during a take; Shutter Sync, Audio (stretched WAV), After the take | `#settingsSpeedRampCard` and four option rows P:4980-5001, note P:5002-5008 | `24355d3`, `d44b177` ("After the take") | New ground | `24355d3`: "Pi build". fork-log:97 |
| F7 | Log and Write buffer | Log On/Off in the cDNG file; Frames/RAM write queue with info and safety-stop notes | `#settingsCdngLogField`, `#settingsCdngLogOptions`, `#settingsBufferModeField` (hidden until Core reports it) P:4912-4926 | `d44b177` | New ground (two fields in the Record card) | `d44b177`: "host tests on the Mac ... Not run yet: the ram queue, the safety stop, the buttons". fork-log:138 "offer ... Log and the RAM queue are the upstream candidates" |
| F8 | Clip names | Presets and drag-and-drop pills compose the clip, frame, sound, video names; live preview | `#settingsClipNamesCard`, `#clipNamePresets`, `#clipNameRow`, `#clipNamePalette`, `#clipNamePreview`, `#clipNameSaved`, `#clipNameStatus` P:4937-4961 | `014a2bf`, `1ef94fe` (P:4935-4936) | New ground | `014a2bf`: no "Tested:" line; 8 files, +1421. fork-log:138 "configurable clip names" |
| F9 | UI timecode and File timecode | Two timecode switches; modes named Time of Day and Clip; the value pill removed | `#settingsTimecodeOptions`, `#settingsFileTimecodeOptions` P:5087-5094 (copy P:5084) | `909aaa5`, `2c259b9` | Extends upstream card in place and removes `#settingsTimecodeValue` | `909aaa5`: "desk (page loads, labels); Pi build pending". fork-log:98 "Pi only; built, not tested". `2c259b9`: "node --check" |
| F10 | Recording indicators | Switches: Recording frame, Frame buffer bar, Red timecode, Audio recording outline | P:5274-5291 (`#settingsRecordingFrameOptions`, `#settingsFrameBufferBarOptions`, `#settingsRecordingRedTimecodeOptions`, `#settingsAudioRecordedOutlineOptions`) | `f4fb084`, `d44b177`, `92d0970` | New ground, inside upstream's Live preview card | `f4fb084`: "desk only (built on the Pi next)". fork-log:81 "tested 2026-10-28 (Patrik)". `92d0970`: no test line |
| F11 | Storage pre-roll | Button and Auto switch warm up the card; last result line; rows hidden until Core reports the feature | `#storagePrerollRow`, `#storagePrerollAutoRow`, `#storagePrerollLast` P:5769-5778 in the "Media Speed" card | `d44b177` | Extends upstream card in place | `d44b177`: "Not compiled or run yet: the pre-roll" |
| F12 | Performance card | Preview temporal denoise, Trim the recording drive, Frame-rate phase lock, Frames per folder (+Apply), Merge split clips | `#settingsPerformanceCard` P:5780-5830 | `ce0bd90` (trim, card), `e625c68` (TDN), `c810f85` (phase lock), `d7dd337` (frames per folder), `ba0658d` (merge) | New ground (a new card in System) | `ce0bd90`: "desk only". `e625c68`, `c810f85`: "desk only (not built: no libcamera on the Mac)". `d7dd337`, `ba0658d`: host tests. fork-log:170-172, 186-188 "fork-only; Pi only" |
| F13 | Boot Config | Edits `/boot/firmware/config.txt` by card (two camera ports, link frequency, RP1 clock, display, I2C, I2S, SPI, onboard audio) or as text; View, Edit, Download, Upload; diff first; Save & Reboot | `#settingsBootConfigCard` P:5859-5951 | `8a56545`, `3b87d99`, `2a4266e` (+ merge `4581a69`) | New ground. Upstream has no config.txt editor; fan mode there is read-only on some boards (note U:3651) | `8a56545`: no test line. `3b87d99`: "desk only (boot_config_test 73 checks)". `2a4266e`: "desk only (75 checks)". fork-log:138 "Not yet run on the camera" |
| F14 | Controls pane | Choose the action of each button, switch, knob, pin for detected GPIO and I2C devices; Listen, review list, Undo last save, Save | `<section data-panel="controls">` P:6137-6168: `#controlsRows`, `#controlsMessage`, `#controlsPending`, `#controlsListenNote`, `#controlsReview`, four buttons | `f5fe41b`, `d282de9`, `8be1ab5` | New ground. Upstream edits `apertar-hardware.conf` as text only | `d282de9`: "pi (apertar.local) the page against the camera". `8be1ab5`: "desk (Chrome page test 60/60 against a mock)". fork-log:118-130 "fork-only" |
| F15 | Value Lists | Per-list steps for FPS, ISO, shutter and so on (container only; JS fills it) | `#settingsValueLists` P:6161-6169 | `ff33d2d` (T33), moved by `6777ebe` | New ground | `6777ebe`: "desk only". fork-log:144 |
| F16 | Hardware card on Config | Per-device state pill and fields, Save Hardware | `#hardwareStatePill`, `#hardwareMessage`, `#hardwarePending`, `#hardwareDevices`, two buttons P:6176-6191 | `f5fe41b` | New ground, a new card above upstream's "Apertar Config" card | `f5fe41b`: "desk only (33 of 33)" |
| F17 | Config text editor aids | Saved versions dropdown, line-number gutter, Check, issues list, diff before save | `#configHistorySelect`, `#settingsConfigGutter`, `#settingsConfigIssues`, `#settingsConfigDiff`, `#checkConfigButton` P:6213-6235 | `8be1ab5`, `effb804` | Extends upstream card in place (textarea wrapped; `<label>` becomes `<div>`) | `8be1ab5`: 60/60 mock. `effb804`: "desk only (node --check ... mock fetch)" |
| F18 | Remote controls | A card of pills that run what each saved button, switch and knob does; held arrow repeats | `#remoteControlsRows` P:4568-4580 | `1319967` | New ground; reuses upstream pill classes | `1319967`: "pi (apertar.local) Remote controls buttons and held knob turns". fork-log:148 |
| F19 | Exact shutter angle | The angle shown is the running angle, not the nearest stop (86.4 deg shows as 86.4) | `formatAngle`, `formatAngleValue` P:7172-7181 | `ff33d2d` | Rewrites an upstream function (U:4690) | `ff33d2d`: "desk only (node --check)" |
| F20 | 4K Clear HDR and 16-bit in Bit Depth | 16-bit first in `rawBitDepthOptions` (P:6511, outside diff; only blame) | P:6511 | `9fa7918` | Extends upstream list | `9fa7918`: "pi (apertar.local) ... checked by eye". fork-log:28 |

## 3. Socket commands and routes the new elements drive

Defined in `App`; WebUI calls them in JS outside this slice. Command set diff = port `cmd:` strings minus upstream `cmd:` strings in the WebUI (confirmed by grep); handler lines at `App:` @cinemate-port.

| Command | Element in this slice | Handler | New or changed |
| --- | --- | --- | --- |
| `set_cdng_log` | `#settingsCdngLogOptions` | App:13079 | new |
| `set_buffer_mode` | `#settingsBufferModeOptions` | App:12829 | new |
| `set_clip_name_template`, `preview_clip_name` | Clip names card | App:13241 | new |
| `set_fps_speed_ramp` | Speed Ramp card | App:13223 | new |
| `get_mode_ladder`, `set_mode_ladder` | Mode Ladder card | App:14093 | new |
| `set_clear_hdr` | Mode Ladder rows, Record | in port JS | new in WebUI (upstream Core may have it, see WCP-04) |
| `set_value_steps` | Value Lists | App:14110 | new |
| `set_timecode_mode` target=ui/files/both | Timecode card | App:13279 | changed (target) |
| `set_recording_frame_enabled`, `set_frame_buffer_bar_enabled`, `set_recording_red_timecode_enabled`, `set_audio_recorded_outline_enabled` | four switches | App:13505-13511 via `handleUiToggle` | new |
| `storage_preroll`, `set_storage_preroll` | pre-roll rows | App:12900 | new |
| `set_preview_tdn` | Performance | App:13205 | new |
| `set_media_trim` | Performance | App:13194 | new |
| `set_fps_phase_lock` | Performance | App:13214 | new |
| `set_frames_per_folder`, `set_clip_merge` | Performance | App:12857 | new |
| `get_boot_config`, `set_boot_config` | Boot Config | App:14586; header comment App:3773 | new |
| `get_controls`, `set_controls`, `list_actions`, `controls_history`, `controls_last_input`, `scan_i2c`, `test_input`, `test_output` | Controls, Remote controls, Hardware | App:12486, 12565, 12745, 12763 | new |
| `wake` | `#pbvWakeButton` | in port JS | new in WebUI |

HTTP routes used by these elements and new in the WebUI JS: `/api/boot-config`, `/api/boot-config/parse`, `/api/buffer` (write buffer level), `/api/media/clip`, `/api/media/frame`; `/api/media/file` (WAV, `fa19856`, built in a template string, not matched by grep). Reused from upstream: `/api/media`, `/api/media/delete-selected`, `/api/media/download-selected`, `/api/config` (now sends a revision header per `effb804`).

## 4. State fields read by these elements (from `/api/state`, `state` object)

| Field | Where it appears |
| --- | --- |
| `preview_tdn`, `fps_phase_lock` (snapshot) | Performance card, JS P:16165-16172 |
| `media_trim_enabled`, `media_trim_env_off`, `clip_merge_enabled`, `clip_merge_*`, `frames_per_folder` (system state) | Performance card, JS P:16184-16211 |
| `ui.frame_buffer_bar_enabled`, `ui.audio_recorded_outline_enabled`, `recording_frame_enabled`, `recording_red_timecode_enabled` | switches, App:9663-9666 |
| `ui.fps_steps` and the other `ui.*_steps` | Value Lists, App:1968 |
| `timecode_mode` (+ UI copy) | Timecode card, App:9635 |
| `mode_ladder` reply (`ladderServer`) | Modes pane |
| JS page `state` additions (P:6693-6735): `valueListsSignature`, `fpsSwitchingTo`, `ladderServer`, `ladderError`, `ladderDraft`, `ladderSaveAgain`, `ladderRecordingSeen`, `ladderCheckTimer`, `ladderSaving`, `ladderToggling`, `ladderFetching`, `ladderFetchedMs`, `ladderSeenActive`, `ladderAspects`, `ladderOpen`, `configRevision`, `pb` (browser and viewer, 22 keys) | page-local |

## 5. Config keys, env vars, files

| Item | Where named | Notes |
| --- | --- | --- |
| `[storage] buffer`, `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent` | App:5048-5061 default conf text | `apertar-hardware.conf`; Write buffer card |
| `[storage] frames_per_folder` | App:5060 | Frames per folder field; env `APERTAR_CDNG_FRAMES_PER_FOLDER` named in the markup P:5813 |
| `[storage] clip_merge` | App:11626 | env `APERTAR_CLIP_MERGE=0` |
| `[storage] pcie_controller=1000110000.pcie` | App:5048 region | Pi 5 PCIe address in default conf (not in this slice, relevant to card/SSD rows) |
| `media_trim=`, `preview_tdn=`, `fps_phase_lock=`, `cdng_log=`, `clip_name_template=`, `fps_speed_ramp=`, `fps_speed_ramp_keep_exposure=`, `fps_speed_ramp_stretch_audio=`, `fps_speed_ramp_after=` | CC:883-973 region | `camera_settings.conf` (Core). `timecode_mode=` exists upstream |
| UI.conf: `frameBufferBarEnabled`, `audioRecordedOutlineEnabled`, `recordingFrameEnabled`, `recordingRedTimecodeEnabled` | App:2096-2101, 7787 | `~/.config/CinePi/UI.conf` (App:536) |
| `mode_ladder.conf` | App:408, 412 | `~/.config/apertar-core/mode_ladder.conf`, new file |
| env `APERTAR_MEDIA_TRIM`, `APERTAR_STORAGE_PREROLL`, `APERTAR_PHASE_LOCK_*`, `APERTAR_FPS_LIMIT`, `APERTAR_LOSSLESS_FPS_LIMIT`, `APERTAR_CDNG_BUFFER*` | App/CC | only `APERTAR_CDNG_FRAMES_PER_FOLDER` is shown in this markup |
| `/boot/firmware/config.txt`, backup `config.txt.apertar.bak`, root helper `/usr/local/libexec/apertar-boot-config` | P:5859-5951 text, App:3502 | Boot Config |
| `<clip>/part_NNN/`, `.parts` marker, `_stretched.wav`, `tools/flatten_clip.py` | P:5809-5819, 5004 | split clips and speed-ramp audio |
| Controls history ("kept in the file's history"), "Saved versions" of the hardware file | P:6213-6220 | files written by Core; path not named in markup (unconfirmed, see WCP-04+) |

## 6. UI elements added (id inventory, 192 ids in the added lines)

Counts by area, ids listed in section 2. Other additions: classes `ladder-line`, `ladder-pair`, `ladder-aspects`, `ladder-groups`, `ladder-box`, `crop-frame large`, `remote-note`, `settings-search`, `clip-row`, `controls-listen-note`, `controls-review`, `config-gutter`, `config-editor-wrap`, `config-issues`, `config-diff`, `config-tools`, `pb-*` (about 45), `pbv-*` (about 50). Attributes: `data-ladder-link` (2), `data-pb-filter` (4), `data-search` (12 including on existing cards). Inline SVG icons: search, refresh, back, download, step arrows (all inline, P:4734, 6345-6430). Icons used: `/icons/resolution.png`, `/icons/film.png`, `/icons/previous.png`, `/icons/next.png`, `/icons/play.png`, `/icons/delete.png` (the last four and film are new references; confirm files exist outside this slice).

## 7. Original code regions modified

| Region | Where (P / U) | Kind | Change |
| --- | --- | --- | --- |
| 720px media query rules | P:4041-4104 / U:2061-2130 | rewritten (removal) | `.media-browser-*` selectors dropped from `.settings-overlay`, `.settings-shell`, `.settings-header`, `.settings-panels`, `.preset-row`, `.preset-actions` groups |
| Camera settings card header and Frame rate topline | P:4512, 4519 / U:2540 region | extended in place | ladder pill and ladder note |
| Settings sidebar | P:4732-4783 | extended in place | search label before `<nav>`; Modes after Record; Controls after Presets (Modes icon `resolution.png`, Controls reuses `settings.png`) |
| Record: Compression label | P:4902 | extended in place | `<label>` gets an id for the lock |
| Record: Timecode card | P:5084-5094 / U:3010-3017 | rewritten | copy text replaced, `#settingsTimecodeValue` pill removed, one pill row becomes two labelled rows |
| Media, Format Media, Media Speed cards | P:5669, 5723, 5746 | extended in place | `data-search` attribute |
| Media Speed card | P:5769-5778 | extended in place | three pre-roll rows |
| Live preview card | P:5274-5291 | extended in place | four switch rows |
| Config pane | P:6172-6235 | extended in place and rewritten | Hardware card inserted before; `<label class="field-stack">` around the textarea becomes `<div>` with a gutter wrapper; helper copy text rewritten |
| Media list overlay | U (about 40 lines of markup) / P:6335 | removed and replaced | whole `#mediaBrowserOverlay` removed |
| `state` | P:6712-6735 | rewritten | `mediaFetchInFlight`, `mediaLibrary`, `mediaLibraryPayload`, `mediaBrowserFilter`, `mediaBrowserSort`, `mediaSelection` removed; `pb` added; `mediaBrowserOpen` kept |
| `formatAngle` | P:7174 / U:4690 | behaviour changed | no snap to `shutterOptions`; result is the exact angle (2 decimals) |

## 8. New abstractions in this slice

| Name | What | Upstream equivalent |
| --- | --- | --- |
| `#playbackOverlay` page model (`state.pb`, `pbBrowserPage`, `pbViewerPage`, history push/pop flags) | Two-page overlay with its own back-stack | Upstream WebUI: one flat overlay (`#mediaBrowserOverlay`, U:2061 region). Touch UI has `qml/ClipPlayerPage.qml` |
| Settings search (`data-search` attribute contract + `applySettingsSearch`) | Keyword filter over cards | none |
| `.ladder-pair` On/Off pill pair, `ladder-*` families | Reused for switches (Speed Ramp, Timecode, Mode Ladder) | upstream `.pill-grid` + `buildOptionButtons` for the same job |
| Hidden-until-capable rows (`hidden` on pre-roll rows, `settingsBufferModeField`) | Core reports support, JS reveals | upstream hides fan note text only |
| Controls / Hardware / Boot Config card pattern (`#controlsRows`, `#hardwareDevices`, `config-diff` review step, "Save & Reboot") | Generated forms with a review diff before save | upstream: raw textarea for `apertar-hardware.conf` (U:3840-3872) |

## 9. Removed, narrowed or hidden (from upstream)

| What | Where | Effect |
| --- | --- | --- |
| Media list overlay and its 14 ids (`mediaBrowserOverlay`, `closeMediaBrowserButton`, `mediaBrowserFilters`, `mediaBrowserCountPill`, `refreshMediaBrowserButton`, `mediaBrowserSortSelect`, `mediaSelectionToolbar`, `mediaSelectionCount`, `selectAllMediaButton`, `clearMediaSelectionButton`, `downloadSelectedMediaButton`, `deleteSelectedMediaButton`, `mediaBrowserList`) | U media overlay, 0 refs at P | Replaced by the Playback overlay. Per-item Download and Delete buttons and the count pill become selection-mode actions. "Clear" selection button gone. Sort select becomes a chip (`NEWEST FIRST`) |
| `#settingsTimecodeValue` pill | U:3016 | Current timecode mode no longer shown as a pill. Free Run / Rec Run labels renamed Time of Day / Clip by `2c259b9` |
| Nearest-stop shutter angle | U:4690 | A value between the built-in stops now shows exactly |
| Record: "Bit Depth" / resolution / crop / Clear HDR / Compression controls | P:4902, `data-ladder-lock` | greyed while the Mode Ladder is on (JS P:15924); red toast with link on click |
| Controls pane nav title for the "power" panel stays "Media" (nav label), cards for media sit in the System panel | P:5189 | Unchanged from upstream. Noted because the Performance card sits in System, not in the "Media" nav item |

## 10. Board assumptions in the slice

| Assumption | Where | Label |
| --- | --- | --- |
| Pi 5 / CM5 with RP1: "RP1 overclock" (`dtoverlay=rp1-clk-333mhz`), "Camera 0 sensor" and "Camera 1 sensor" (two CSI ports) | P:5878-5902 | confirmed in text. Pi 4 / CM4 have no RP1 |
| Boot file `/boot/firmware/config.txt`, backup `config.txt.apertar.bak` | P:5864, 5935 | confirmed (Bookworm layout) |
| Sensors named: imx477, imx577, imx585, imx294, mono, link frequency | P:5860 (`data-search`) | confirmed |
| I2C bus on GPIO 2/3, DPI panel takes GPIO 0-27, CFE hat, NeoRotary 4, PCF8574, INA219 | P:5906-5912, 5915 | confirmed |
| I2S, SPI buses, onboard audio | P:5918-5930 | confirmed |
| GPIO 21 given as search example | P:4734 | confirmed |
| `/home/pi/apertar-hardware.conf` as default path text | P:6203 | unchanged upstream text |
| "Off makes the image processor about six times faster per frame at 4K Clear HDR 16-bit" (PiSP/Pi 5 ISP) | P:5792 | probable Pi 5 only; no measurement cited in markup |
| Phase lock "follows the Pi's clock" | P:5805 | confirmed text |
| exFAT / SSD / card: "exfat", "ssd" in `data-search`; exFAT folder-walk reason for `frames_per_folder` (App:5060 comment) | P:5742, 5812 | confirmed |
| RAM buffer: "ram" mode sized from free memory (App:5052) | P:4912 | confirmed. Depends on RAM size |
| Fan: Fan Mode note unchanged | P:5845 | unchanged upstream |
| Thermal, PCIe, gpiochip numbering | not in the markup of this slice | gpiochip in Controls JS (WCP-05) |

## 11. Commits that wrote the slice (lines in slice)

| Commit | Subject | Lines | Fork-log status |
| --- | --- | --- | --- |
| `4629de2` | the Clip Viewer, frame-number clock (T50) | 82 | fork-log:102, Pi only, tested 2026-10-29 |
| `8a56545` | Boot Config card in the System pane | 79 | merged `4581a69`, not run on the camera |
| `bc12c0a` | the Clip Browser (T49) | 63 | fork-log:101 |
| `854fe43` | a Modes pane | 58 | fork-log:145, on the Pi |
| `d44b177` | drop-frames squash (trim, Log, buffer, bar, pre-roll, search, GPIO UI) | 44 | fork-log:138, "Not run yet" for parts |
| `f5fe41b` | Controls for detected hardware, Hardware card | 30 | fork-log:123 |
| `8be1ab5` | Listen, review, undo, chips, Scan, text editor | 25 | fork-log:130 |
| `014a2bf` | clip names you can compose | 25 | in fork-log:138 |
| `24355d3` | Speed Ramp card after Value Lists | 24 | fork-log:97 |
| `d282de9` | Controls card on Config, action dropdowns | 16 | fork-log:118 |
| `ce0bd90` | media trim switch, Performance card | 16 | fork-log:170 |
| `1319967` | Remote controls card | 13 | fork-log:148 |
| `3b87d99` | Boot Config Edit file | 12 | fork-log:138 |
| `d7dd337` | split a take into part folders | 10 | fork-log:186 |
| `ba0658d` | merge worker | 10 | fork-log:188 |
| `6777ebe` | Value Lists moves to Controls | 9 | fork-log:144 |
| `1ef94fe` | Mode Ladder, Speed Ramp, sensor modes per approved design | 9 | fork-log:97 |
| `f4fb084` | recording frame and red timecode switches | 8 | fork-log:81 |
| `909aaa5` | UI timecode and file timecode set apart | 8 | fork-log:98 |
| `e625c68` | Preview temporal denoise switch | 7 | fork-log:171 |
| `c810f85` | frame-rate phase lock | 7 | fork-log:172 |
| `92d0970` | Audio recording outline switch | 5 | in fork-log:138 |
| `920beb0` | the Mode Ladder editor | 4 | fork-log:94 |
| `effb804`, `da8ca9f`, `5dfbc6c`, `2a4266e`, `ff33d2d`, `fa19856`, `9fa7918`, `4b14a79`, `392e812`, `2c259b9` | small edits | 1-3 each | fork-log:97, 111, 138, 77, 104, 28, 146, 121 |

All commits are on `cinemate-port`; none is on `origin/main`. fork-log marks them "fork-only". Many say "Pi build pending" or "desk only".

## 12. Facts for stage 2 (not judged here)

| Fact | Evidence |
| --- | --- |
| The slice is HTML that mixes upstream cards with 19 new feature areas; 2543 of 3122 lines are upstream, 579 written by 34 commits | blame |
| One commit (`d44b177`) is a 19-commit squash touching 25 files; its 44 lines here span search, Log, buffer, bar, pre-roll, tally and GPIO UI | fork-log:138 |
| The Playback overlay replaces, not extends, the upstream media list; `state.mediaBrowserOpen` kept as the open flag | P:6714, 10116 |
| `state.pb` carries about 22 keys incl. browser history flags | P:6716-6720 |
| New cards for "what Core reports" are hidden by default and shown by JS | P:4912 (`hidden`), 5769 (`hidden`) |
| Three new buses of text help inline in markup name internal product terms: "Resolution ladder", "Clear HDR", "CFE hat" | P:4512, 4902, 5906 |
| Work-package ids (T33, T49, T50, T51, T38) appear in commit subjects and in JS comments but not in the visible markup of this slice | grep |
| Upstream Apertar-Core has no `data-search`, no Mode Ladder, no Speed Ramp (grep 0 hits U) | grep |
| The `Controls` nav item reuses `settings.png`; `Modes` reuses `resolution.png` | P:4750-4773 |

## 13. Open

| Item | Command to settle |
| --- | --- |
| Is every element id in this slice used by JS (no orphan markup) | `grep -c` per id over the file; list ids with a single hit |
| Do `/icons/film.png`, `previous.png`, `next.png`, `play.png`, `delete.png`, `resolution.png` exist as served assets | `grep -n 'film.png' src/web/*.cpp` and the icon table in `src/web/` |
| Where `set_clear_hdr` is handled in Core vs upstream | `grep -n 'set_clear_hdr' /home/user/wt/core-upstream/src/ApertarCoreApp.cpp` (WCP-04 covers the JS) |
| Which file holds the Controls history and "Saved versions" | read `App:12763` region |
| Rendering of all new cards | headless Chrome screenshot against `--simulate` |
