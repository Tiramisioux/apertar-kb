# Inventory: unit App-2 (`src/ApertarCoreApp.cpp`, port lines 4954-8205)

Stage 1 of 3. What the port added or changed in this slice. No judgement.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/App.part02.diff`, all 1457 lines, 15 hunks, +691 / -102 |
| Port file | `/home/user/Apertar-Core/src/ApertarCoreApp.cpp` @cinemate-port `01f170c` (15 083 lines) |
| Diff base | fork main `origin/main` `f60e301` |
| Original | `/home/user/wt/core-upstream/src/ApertarCoreApp.cpp` @upstream-1.6.0 `35dbe67` (11 025 lines) |
| Base vs original inside this slice | One fork-main change only: 2 lines in `estimatedStillFrameSizeMiB` (`rawBitDepth == 16`, commit `631721d`). All other text the port touched here is upstream 1.6.0 text. `git diff --minimal -U0 upstream-1.6.0 origin/main -- src/ApertarCoreApp.cpp`, hunk `@@ -4779,0 +4789,2`. confirmed |
| Blame | Every added line: `git blame -s -L 4964,8189 cinemate-port -- src/ApertarCoreApp.cpp`. 28 commits |
| Short names | `App` = `src/ApertarCoreApp.cpp`. `@port` = cinemate-port `01f170c`. `@up` = upstream-1.6.0. `WCP` = `src/web/WebControlPage.cpp` |
| Labels | Every row is **confirmed** (read in code at the ref given) unless it says probable or unconfirmed |

KB chapters this slice covers (`llm/core-map.md` rows, upstream lines): 4231-4449 hardware file paths and template, 4450-4715 INA219,
4716-4836 estimates, 5290-5387 `/api/config` backends, 5954-6281 streaming, 6282-6449 clip library scan, 6450-6778 presets,
6781-6937 constructor, `start()`, `stop()`.

## 1. Hunk map

| # | Port lines | Upstream anchor (@up) | + / - | Content | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | 4954-5168 | `defaultHardwareConfigTemplate` `App:4291-4404` | +127 / -12 | 5 new helper functions above the template; template edits | `f5a61b8` `2955ef8` `014fa22` `d44b177` `d7dd337` `ba0658d` `8175273` `7af9f13` `4d80a35` `c34f844` |
| 2 | 5286-5356 | after `loadIna219HardwareConfig` `App:4450-4506` | +51 / -0 | `loadCfeHatConfig()` | `0b1632f` |
| 3 | 5572-5684 | `estimatedRawBytesPerSecond` `App:4743-4763`; `estimatedStillFrameSizeMiB` `App:4765` | +62 / -12 | new byte-rate model, `timeLeftEstimateLabel`, IMX283 | `3c4f07d` `d44b177` `c48e693` |
| 4 | 6174-6260 | `buildHardwareConfigFileJson` `App:5290-5321`; `saveHardwareConfigFile` `App:5323-5386` | +22 / -47 | GET body read through the store; save function cut down to its three checks | `5395fa4` |
| 5 | 6325-6471 | `struct MediaLibraryItem` `App:5469-5486` | +110 / -0 | playback statics, 16 item fields, trim helpers, `MediaDeleteScope` | `f91fafa` `a37a902` `d44b177` `ce0bd90` |
| 6 | 6657-6681 | `clipContainerTypeLabel` `App:5685-5696` | +4 / -2 | own-container rule | `014a2bf` |
| 7, 8 | 6754-6869 | `wavDurationTextForFile` `App:5786-5853` | +34 / -5 | `WavFormat`, `wavFormatForFile`, `wavSoundText` | `fa19856` |
| 9 | 7190-7292 | `streamFileToClient` `App:6193-6208`; `streamZipArchiveToClient` `App:6215-6280` | +60 / -2 | stop callback, range streamer, range parser | `a37a902` `fa19856` |
| 10 | 7324-7417 | zip function tail; before `discoverMediaLibraryItems` `App:6282` | +61 / -1 | zip stop + SIGTERM; `clipInfoJson`; new list signature | `a37a902` `f91fafa` `fa19856` `ab4cc92` |
| 11 | 7432-7538 | `discoverMediaLibraryItems` `App:6282-6448` | +71 / -21 | facts-cache path, hold | `f91fafa` `ab4cc92` |
| 12, 13 | 7776-7878 | `buildCurrentPresetPayload` `App:6522` (after `:6610`, `:6664`, `:6675`) | +18 / -0 | 18 preset keys | `f4fb084` `d44b177` `92d0970` `8e8ea2e` `ca7b7c2` `014a2bf` `d7ff071` |
| 14 | 7977-8004 | constructor `App:6781-6794` | +8 / -0 | safety-stop hook | `d44b177` |
| 15 | 8017-8199 | `start()` `App:6801-6903`; `stop()` `App:6905` | +63 / -0 | 7 threads, validation at start, callbacks, stop order | `d44b177` `ba0658d` `01f170c` `438a342` `ce0bd90` `dcf09ee` `4d80a35` `014fa22` |

## 2. Commits that wrote this slice

Lines = added lines of this slice that blame gives the commit. "Commit says" = the `Tested:` line of the commit message.
"Fork log" = `/home/user/apertar-kb/fork-log.md`. Neither proves behaviour (BRIEF rule 5). Dates are 2026.

| Commit | Date | Subject (short) | Lines | Commit says | Fork log |
| --- | --- | --- | --- | --- | --- |
| `f91fafa` | 10-29 | Core knows its clips: facts, hold rule, yield window (T47) | 114 | Pi build pending | fork-only, Pi only; tested 2026-10-29 (live list 4.2 s then 20 ms; hold and 409 in a 4 s take) |
| `ab4cc92` | 10-29 | the list asks the facts cache before it scans a folder (T47) | 32 | Pi build pending | same row as `f91fafa` |
| `d44b177` | 10-31 | drop-frames squash (19 commits): trim, Log, RAM buffer, safety stop, buffer bar, pre-roll | 108 | host tests on the Mac; branch compiles on the Pi; run on the Pi: trim at mount, Log 16 to 12; not run: ram queue, safety stop, buttons, Controls page; pre-roll not compiled or run | offer in pieces after the Pi tests; "Not yet run on the camera" |
| `fa19856` | 10-29 | sound in the Clip Viewer: `/api/media/file` with Range (T51) | 101 | Pi build pending | fork-only, Pi only; tested 2026-10-29 (Range and 416; Chrome playback with sound; Safari/Firefox/phone not tested) |
| `3c4f07d` | 10-27 | time left follows format and bit depth | 55 | pi build (see next run) | fork-only, on GitHub; T21 tested (agrees with HDMI up to rounding) |
| `f5a61b8` | 10-29 | `get_controls`, `set_controls` (T37 part 3) | 52 | desk only | fork-only |
| `0b1632f` | 10-26 | see a pulled CFexpress card at once | 51 | pi build (see next run) | fork-only, on GitHub; built 22:43 |
| `4d80a35` | 10-29 | validate the hardware file at start, pin the adopted version, fix the default template (T37 part 4) | 35 | desk only (host test 88 of 89; Pi build not yet run) | fork-only |
| `a37a902` | 10-29 | downloads and deletes yield to a take (T50 Core) | 26 | Pi build pending | fork-only, Pi only; tested 2026-10-29 (download stopped within 0.3 s of a take; Q23 not tested live) |
| `5395fa4` | 10-29 | Config page file goes through the store (T38 part 1) | 22 | desk only | fork-only |
| `014fa22` | 10-29 | spot a hardware file replaced by a default, restore it (T38 part 3) | 17 | pi: store test 52 of 52; live mv test restored byte for byte | fork-only |
| `dcf09ee` | 10-30 | saves apply without a restart, Listen, history, I2C scan, output tests | 11 | desk (host 120/121); pi build | fork-only |
| `8e8ea2e` | 10-28 | presets carry every operating-mode switch | 9 | pi preview: saved and restored Clear HDR, knobs, phase lock, rec_run, speed ramp | fork-only, on GitHub; tested 2026-10-28 |
| `ba0658d` | 11-08 | merge worker flattens split clips while idle | 7 | desk (clip_merge_test); pi build rc 0, not yet run on the camera | fork-only; on GitHub |
| `c34f844` | 10-30 | two- and three-way GPIO switches; CFexpress hat in `get_controls` | 7 | desk (host 118/119); pi build | fork-only |
| `8175273` | 10-28 | Clear HDR holds ISO and WB, caps ISO per mode | 6 | pi preview: ISO 1600 -> 720 (12-bit), 1585 (16-bit) | fork-only, on GitHub; tested in preview 2026-10-28 |
| `438a342` | 10-26 | survive a yanked or unmounted recording drive | 6 | desk only (not built yet) | fork-only, on GitHub; built 22:27 with `e8bb1b7` |
| `7af9f13` | 10-29 | default template shows HDMI 1080p (T38 part 5) | 5 | desk only | fork-only |
| `014a2bf` | 11-01 | clip names you can compose | 5 | no Tested line | named inside the `d44b177` row |
| `d7dd337` | 11-08 | split a take into part folders, `frames_per_folder` | 4 | desk (frame_path_test, storage_buffer_conf_test); pi build rc 0 | fork-only; on GitHub |
| `ce0bd90` | 11-04 | switch for the drive trim (`set_media_trim`) | 4 | desk only | fork-only; Pi only |
| `01f170c` | 11-08 | read the clip merge switch before the worker's first scan | 3 | pi restart with `clip_merge=off`, no merge line | fork-only; on GitHub |
| `c48e693` | 11-01 | IMX283 sensor family | 2 | desk only (host tests, Pi -fsyntax-only) | named inside the `d44b177` row (merge `a47dc28`); "Not yet run on the camera" |
| `f4fb084` | 10-28 | recording frame and red timecode switches | 2 | desk only | fork-only, on GitHub; tested 2026-10-28 (Patrik) |
| `2955ef8` | 11-01 | `get/set_boot_config`, `/api/boot-config` (author "Claude") | 1 | no Tested line | no row for this sha; inside merge `4581a69`, named in the `d44b177` row |
| `92d0970` | 11-01 | Audio recording outline switch | 1 | no Tested line | named inside the `d44b177` row |
| `ca7b7c2` | 10-28 | experimental stretched WAV after a speed-ramp take | 1 | desk only | fork-only, on GitHub; tested 2026-10-28 |
| `d7ff071` | 10-28 | `conform_fps` | 1 | desk only | fork-only, on GitHub; tested 2026-10-28 |

## 3. Features that touch this unit

"Here" = what of the feature sits in this slice. Line numbers `App:` are @port.
"What the operator gets" is the intent stated by the commit message and the fork log, checked against the code named in "Here". Nothing was run on a camera.

| # | Feature | What the operator gets | Here | Commits | Relation to upstream |
| --- | --- | --- | --- | --- | --- |
| F1 | Hardware file check and Controls replies | Core checks `apertar-hardware.conf` at start, logs errors and warnings, counts them in the state; Controls and Config pages show issues with line numbers; a file replaced by a default is reported | `hardwareConfigFacts` `App:4965-4978`; `controlsIssuesJson` `:4980`; `controlsConflictsJson` `:4997`; `controlsReplacedJson` `:5012`; `controlsErrorCount` `:5026`; start block `:8136-8154` | `f5a61b8` `4d80a35` `014fa22` `2955ef8` | entirely new area; `start()` extended in place |
| F2 | Config page saves through one writer | A save from an old or stale page is refused (409) and keeps the text; a missing file shows the `/boot` copy when there is one | `buildHardwareConfigFileJson` `App:6181-6228`; `checkHardwareConfigText` `:6231-6252` | `5395fa4` | replaces upstream code (`saveHardwareConfigFile`) |
| F3 | Saved hardware file applies without a restart; Listen | A save restarts only the drivers whose sections changed; the Controls page can show the last input that moved | `start()` `App:8117-8120`, `:8156-8157`; `stop()` `:8172-8175` | `dcf09ee` | entirely new area; `start()`/`stop()` extended in place |
| F4 | Default hardware template | The template shown for a missing file is HDMI 1080p, lists NeoRotary, GPIO encoders, GPIO switches, Grove analog, and the new `[storage]`, `[media]`, `[camera]` keys | `App:5031-5192` | `4d80a35` `7af9f13` `c34f844` `d44b177` `d7dd337` `ba0658d` `8175273` | extends an upstream function in place; changes defaults |
| F5 | Pulled CFexpress card seen at once | An empty HAT slot marks the medium removed before a write hangs | `loadCfeHatConfig` `App:5296-5346` | `0b1632f` | adds a parallel path beside upstream code (copy of the INA219 loader) |
| F6 | Media watcher (yanked drive) | Media state follows a pulled or dead drive | thread start `App:8043-8044`; `stopMediaWatcher()` on 3 failure paths `:8068`, `:8094`, `:8107` and in `stop()` `:8189` | `438a342` | entirely new area; `start()`/`stop()` extended in place |
| F7 | Time left follows format and bit depth | Minutes left in the WebUI match the touch UI; the sub-label names the format assumed | `estimatedRawBytesPerSecond` `App:5586-5625`; `timeLeftEstimateLabel` `:5628-5651` | `3c4f07d` `d44b177` | replaces upstream code (raw and H.264 branches) |
| F8 | IMX283 still size | Stills-left estimate knows the IMX283 | `App:5661`, `:5674` | `c48e693` | extends an upstream function in place |
| F9 | Clip facts in the media list and per clip (T47) | Each cDNG clip shows its own FPS, span duration, dropped frames, recorded timecode, shot date; the list is fast after the first call; in a take the clip rows come from the cache | statics `App:6335-6359`; item fields `:6378-6390`; `clipInfoJson` `:7354-7405`; `discoverMediaLibraryItems` `:7407-7532` | `f91fafa` `ab4cc92` | adds a parallel path inside an upstream function; new route helper |
| F10 | Downloads and deletes yield to a take (T50 Core) | A running download stops when a take starts; no take while a delete runs | `playbackYieldActive` `App:6349`; `MediaDeleteScope` `:6454-6462`; stop callbacks `:7200-7217`, `:7279-7352` | `a37a902` | extends upstream functions in place |
| F11 | Sound in the Clip Viewer (T51) | The viewer plays the take's WAV and can seek; a SOUND row | `WavFormat` `App:6765-6776`; `wavFormatForFile` `:6778-6845`; `wavSoundText` `:6853-6860`; `streamFileRangeToClient` `:7219-7243`; `parseSingleByteRange` `:7245-7272`; sound fields in `clipInfoJson` `:7373-7387`, `:7398` | `fa19856` | extends upstream WAV parser in place; new route helpers |
| F12 | Composable clip names | ProRes and H.264 clips are labelled right under any clip-name template; presets carry the template | `clipContainerTypeLabel` `App:6667-6671`; preset key `:7848` | `014a2bf` | extends upstream functions in place |
| F13 | Trim of the recording drive | Core trims the drive at mount and after big deletes; a switch turns it off | trim helpers `App:6393-6452`; thread start `:8027-8030`; setting `:8073` | `d44b177` `ce0bd90` | entirely new area |
| F14 | RAM write buffer, safety stop, buffer events | A switchable RAM write queue; the take ends cleanly when the buffer is nearly full; buffer level events | template `App:5051-5059`; hook `:7987-7994`; threads `:8045-8052` | `d44b177` | entirely new area |
| F15 | Storage pre-roll | A short test take warms the card at start, on insert and after a format | template `App:5067-5072`; thread `:8039-8042`; `stop()` `:8185` | `d44b177` | entirely new area |
| F16 | Split takes and merge worker | Long takes can be split into part folders and merged back while idle | template `App:5060-5065`; thread `:8031-8038` | `d7dd337` `ba0658d` `01f170c` | entirely new area |
| F17 | Clear HDR ISO cap per mode | Highest ISO in Clear HDR is set in the hardware file | template `App:5074-5079` | `8175273` | extends an upstream function in place (template text) |
| F18 | Presets carry more settings | A preset saves and restores Clear HDR, its four knobs, phase lock, timecode mode, speed ramp, conform fps, Log, clip-name template, four UI switches | `App:7786-7789`, `:7844-7856`, `:7868` | `8e8ea2e` `ca7b7c2` `d7ff071` `f4fb084` `92d0970` `d44b177` `014a2bf` | extends an upstream function in place |
| F19 | GPIO switches | Two- and three-way switches on GPIO pins | template `App:5146-5151` | `c34f844` | extends an upstream function in place (template text) |

## 4. Interfaces added or changed

### 4.1 Socket commands served or fed by code in this slice

| Command | New / changed | In this slice | Handler (other unit) |
| --- | --- | --- | --- |
| `get_controls` | new | `hardwareConfigFacts`, `controlsIssuesJson`, `controlsReplacedJson`, `controlsErrorCount` | `App:12420-12457` |
| `set_controls` (also `restore=true`) | new | same, plus `controlsConflictsJson` | `App:12763-12825` |
| `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll` | new | replies built with `controlsIssuesJson`, `controlsErrorCount`, facts from `hardwareConfigFacts` | `App:12829`, `:12857`, `:12900` |
| `record_stop` | changed: also dispatched by the safety-stop thread | hook set in the constructor `App:7987-7994`; thread started `:8049-8052` | `runBufferSafetyStop` `App:11083-11111` |
| `record_start`, `capture_photo`, `timelapse_start` | changed: refused with "Deleting media. One moment." while a delete runs | `MediaDeleteScope` `App:6454-6462` sets the flag | `App:12585-12587` |
| `apply_preset` | changed: reads the 18 new keys | writer side `App:7786-7789`, `:7844-7856`, `:7868` | `App:14276-14456` |
| `get_state` | changed: `controls_errors`, `controls_warnings` | counts set at start `App:8141-8143` | `App:12947-12948` |

### 4.2 HTTP routes

| Route | New / changed | In this slice | Route code (other unit) |
| --- | --- | --- | --- |
| `GET /api/config` | changed: adds `revision`, `boot_copy`; text of a missing file comes from a `/boot` copy when one exists, else the template | `buildHardwareConfigFileJson` `App:6181-6228` | `App:8613-8618` |
| `POST /api/config` | changed: three input checks stay; write goes through `HardwareConfigStore`; header `X-Apertar-Revision`; 409 with `code` `old_page`, `merge_review`, `stale`, `conflict`, `being_written`, `locked`; 400 with `issues`; reply adds `revision`, `written`, `errors`, `issues` | `checkHardwareConfigText` `App:6231-6252`; JSON helpers `:4980-5029` | `App:8620-8679` |
| `GET /api/media` | changed: 16 new fields per item, top-level `held`; cDNG folders answer from the facts cache | `MediaLibraryItem` `App:6361-6391`; `discoverMediaLibraryItems` `:7407-7623` | `App:8435-8440`; serialised `:9250-9296` |
| `GET /api/media/clip?kind=folder&id=` | new | `clipInfoJson` `App:7354-7405`; `clipFactsCache` `:6354-6359` | `App:8442-8473` |
| `GET /api/media/file?kind=folder&id=&name=<clip>.wav` | new: 200 / 206 / 416, `Accept-Ranges`, `Content-Range`, `Content-Length`, 409 in a hold | `parseSingleByteRange` `App:7245-7272`; `streamFileRangeToClient` `:7219-7243` | `App:8550-8611` |
| `GET /api/media/frame` | new (other unit) | uses `clipFactsCache()`, `playbackYield()` | `App:8475-8548` |
| `GET /api/media/download`, `GET /api/media/download-selected` | changed: a running file or ZIP stream stops within one 64 KiB chunk when the yield window opens; the zip child gets SIGTERM | `streamFileToClient` `App:7200-7217`; `streamZipArchiveToClient` `:7279-7352` | routes `App:8682`, `:8811`; stream calls `:8742`, `:8767`, `:8799`, `:8856` |
| `GET /api/state` | changed fields fed from here: `time_left_label` (new), `record_time_left_minutes` (new model), `controls_errors`, `controls_warnings`, `media_trim_env_off` | `timeLeftEstimateLabel`, `estimatedRawBytesPerSecond`, `mediaTrimEnvOff` | `App:9410`, `:9458-9459`, `:9585`, `:9595` |

### 4.3 Reply and state fields

| Where | Fields | Evidence |
| --- | --- | --- |
| `GET /api/config` | `revision`, `boot_copy` | `App:6220-6221` |
| `/api/media` item | `format`, `format_label`, `playable`, `play_reason`, `fps`, `fps_fallback`, `shot_date_text`, `shot_ms`, `first_number`, `last_number`, `missing_frames`, `empty_frames`, `ramp`, `has_audio`, `token`, `timecode_start` | struct `App:6378-6390`; serialised `App:9284-9291` |
| `/api/media` top level | `held` | `App:9263` |
| `/api/media/clip` | `ok`, `kind`, `id`, `name`, `format`, `playable`, `play_reason`, `frame_count`, `first_number`, `last_number`, `holes` (array of `[first,length]` pairs), `missing_frames`, `empty_frames`, `fps`, `fps_fallback`, `ramp` (`{"present":true}` or `null`), `token`, `width`, `height`, `bits`, `compression`, `companded`, `timecode_start`, `has_audio`, `sound_text`, `audio_url`, `fps_badge`, `info_line`, `meta{captured,type,resolution,bit_depth,frame_rate,duration,frames,clip_size,path}`, `extra{sound,format,dropped}`, `held` | `App:7358-7403` |
| issues array (`get_controls`, `set_controls`, `POST /api/config`, buffer and pre-roll setters) | objects `{line, error, rule, section, key, message}` | `App:4986-4991` |
| conflicts array | objects `{section, key, base, current}` | `App:5003-5006` |
| `replaced` object | `{replaced, reason, saved_at, source, restore_revision}` | `App:5015-5021` |
| `/api/state`, `get_state` | `controls_errors`, `controls_warnings` | set `App:8142-8143`; read `App:9458-9459`, `:12947-12948` |
| `/api/state` | `time_left_label` = e.g. `cDNG 16-bit lossless estimate (bar: 2 h)` | `App:5650`, `:9595` |

### 4.4 Events

None added in this slice. `camera_state` `ready` / `stopping` are unchanged (`App:8159`, `:8171`).
New stderr lines at start: `ApertarCore controls: <path> <revision>: N errors, M warnings` and up to ten issue lines (`App:8146-8153`).

### 4.5 Config keys

`apertar-hardware.conf`, as Core's default template now lists them (`App:5031-5192`). Readers are in other units.

| Section | Key | Template value | Status | Reader |
| --- | --- | --- | --- | --- |
| `[storage]` | `buffer` | `frames` | new | `src/util/BufferBudget.hpp:119-190` |
| `[storage]` | `buffer_ram_fraction` | `0.6` | new | same |
| `[storage]` | `buffer_ram_floor_mb` | `512` | new | same |
| `[storage]` | `buffer_ram_max_fraction` | `0.5` | new | same |
| `[storage]` | `buffer_stop_percent` | `# 90` (commented) | new | same |
| `[storage]` | `frames_per_folder` | `# 0` (commented) | new | same |
| `[storage]` | `clip_merge` | `# on` (commented) | new | same |
| `[media]` | `preroll` | `# on` (commented) | new section | `src/util/StoragePreroll.hpp:32-111` |
| `[media]` | `preroll_seconds` | `# 2` (commented) | new | same |
| `[camera]` | `clear_hdr_iso_max_12bit` | `720` | new section | `src/camera/CameraController.cpp:2976-2978` |
| `[camera]` | `clear_hdr_iso_max_16bit` | `1585` | new | same |
| `[display]` | `ui_width`, `ui_height`, `ui_layout` | `1920`, `1080`, `landscape_large` (were `720`, `720`, `square`) | default changed | touch UI `src/DisplayConfigBridge.cpp` |
| `[display]` | `hdmi_external_only` | `true` (was `false`) | default changed | touch UI |
| `[imu]` | `sync_mode` | `free_run` | added to template | `Mpu6050RecordingSession.cpp:894 @up` |
| `[imu]` | `bus`, `address`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation` | removed from template | removed | upstream reads these in the driver section, not in `[imu]`: `Mpu6050RecordingSession.cpp:939-954`, `:957-985 @up` |
| `[pcf8574]` | `bus` | `1` (was `10`) | default changed | reader default is 1: `src/hardware/Pcf8574Input.hpp:31 @up` |
| `[neorotary4]` | `enabled`, `bus`, `address` | `false`, `1`, `0x49` | section added to template (reader is upstream: `NeoRotary4Input.cpp:383 @up`) | upstream |
| `[gpio_encoders]` | `enabled` | `false` | section added to template (reader is upstream: `GpioInput.cpp:409 @up`) | upstream |
| `[gpio_switches]` | `enabled`; comment names `switchN_pins`, `switchN_on`, `switchN_off`, `switchN_position0..2` | `false` | new section and new reader | `src/hardware/GpioInput.cpp:311-336 @port` |
| `[grove_analog]` | `enabled`, `bus`, `address` | `false`, `1`, `0x04` | section added to template (reader is upstream: `GroveAnalogInput.cpp:276 @up`) | upstream |
| `[cfexpress_hat]` | `enabled`, `bus` (`channel`, `i2c_bus`), `address` (`addr`) | template unchanged (`true`, `10`, `0x34`) | new C++ reader | `loadCfeHatConfig` `App:5296-5346` |

Other stores:

| Store | Key | Evidence |
| --- | --- | --- |
| `camera_settings.conf` | `media_trim` (read into `mediaTrimSetting_` at start) | `App:8073`; `CameraController.cpp:889`, `:976` |
| Preset JSON, UI part (from `UI.conf`) | `recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled` | `App:7786-7789` |
| Preset JSON, camera part | `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter`, `cameraFpsSpeedRampAudio`, `cameraFpsSpeedRampAfter`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraConformFps`, `cameraClearHdr`, `cameraHdrThresholdHigh`, `cameraHdrThresholdLow`, `cameraHdrBlend`, `cameraHdrGainAdder`, `cameraCdngLog` | `App:7844-7856`, `:7868` |

### 4.6 Environment variables

| Variable | Status | Evidence |
| --- | --- | --- |
| `APERTAR_MEDIA_TRIM` (`0` forces the trim off) | new, read in this slice | `App:6399-6404` |
| `APERTAR_BOOT_CONFIG` | new (other unit), read here through `bootConfigPath()` | `App:4976`, `:3505-3510` |
| `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE` | new (other unit), read at start through `refreshBufferRequest()` | `App:8034`, `:8145`, `:273-286` |
| `APERTAR_HARDWARE_CONFIG`, `HOME` | upstream, unchanged | `App:4927`, `:4946`, `:4954` |

### 4.7 Files on disk

| Path | Use | Evidence |
| --- | --- | --- |
| `/home/pi/apertar-hardware.conf` (or `APERTAR_HARDWARE_CONFIG`) | validated at start; read through the store | `App:8138-8140` |
| `/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf` | shown as the text of a missing file | `App:6188-6202` |
| `~/.config/apertar-core/hardware-history/adopted-<revision>.conf` | written once at start by `store.adopt()` | `App:8144`; `src/hardware/HardwareConfigStore.cpp:451-462` |
| `~/.config/apertar-core/hardware-state.conf` | store state, read for `replacedByDefault()` | `App:8149`; `HardwareConfigStore.cpp:102`, `:410` |
| `/boot/firmware/config.txt` (or `APERTAR_BOOT_CONFIG`) | read for DPI overlay lines | `App:4976`, `:3228` |
| `/dev/i2c-N` | listed | `App:4969-4973` |
| `/usr/local/libexec/apertar-media-trim` (`scripts/apertar-media-trim`), `/etc/sudoers.d/apertar-media-trim` (`config/apertar-media-trim.sudoers`) | run by `runTrimHelperProcess` as `sudo -n <helper> <mountpoint>` | `App:6415-6452`, `:11484` |
| `<media>/<clip>/<clip>.wav`, `<clip>/audio_capture.raw` | read for the SOUND row | `App:7376`, `:7380` |

### 4.8 UI elements fed by this slice (WebUI, other units)

| Element | Evidence |
| --- | --- |
| Time-left sub-label `#timeLeftLabel` shows `time_left_label` | `WCP:4679`, `:9945`, `:16366` |
| Config pane sends `X-Apertar-Revision`, keeps the text on `stale`, `conflict`, `merge_review` | `WCP:18922`, `:18948` |
| Clip Browser `#playbackOverlay`; card shows DROP count and `TC <timecode_start>` | `WCP:6345`, `:11840`, `:11872-11875` |
| Clip Viewer: fetches `/api/media/clip`, metadata rows TIMECODE, SOUND, FORMAT, plays `audio_url` | `WCP:12800`, `:12747`, `:12817` |
| Performance card trim switch (greys when `media_trim_env_off`) | `WCP:16184` |

## 5. Original code that was modified

Upstream lines are @up. Kind: extended-in-place, rewritten, removed, moved, behaviour-changed.

| Region | Upstream | Port | Kind | Change |
| --- | --- | --- | --- | --- |
| `defaultHardwareConfigTemplate()` | `App:4291-4404` | `App:5031-5192` | behaviour-changed | `[storage]` +15 lines; new `[media]`, `[camera]`; `[display]` defaults to 1920x1080 `landscape_large`, `hdmi_external_only=true`; `[imu]` loses 6 keys, gains `sync_mode`; `[pcf8574] bus` 10 -> 1; new `[neorotary4]`, `[gpio_encoders]`, `[gpio_switches]`, `[grove_analog]` |
| `estimatedRawBytesPerSecond()` | `App:4743-4763` | `App:5586-5625` | rewritten | ProRes branch kept. H.264: fixed 25 Mbit/s -> ladder 14/24/42/70 Mbit/s by output pixels, scaled by fps. Raw: `pixels * 1.5 * fps * (1.08 or 1.03)` -> per-frame model by `rawBitDepth` (Log bits when applied), per format (MLV, Lossy 3:1 / 5:1, lossless, uncompressed). Constants equal the touch UI's `estimatedFrameSizeMB` (`/home/user/wt/ui-upstream/qml/CameraPage.qml:870-937`) |
| `estimatedStillFrameSizeMiB()` | `App:4765` (branch `:4783`) | `App:5653` (`:5661`, `:5674`) | extended-in-place | `imx283` joins the `imx294` branch |
| `buildHardwareConfigFileJson()` | `App:5290-5321` | `App:6181-6228` | behaviour-changed | `exists` and text come from `hardware::configStore().info()`; a missing file shows a `/boot` copy before the template; adds `revision`, `boot_copy` |
| `saveHardwareConfigFile()` | `App:5323-5386` | gone; `checkHardwareConfigText()` `App:6231-6252` | removed | The three input checks (empty, > 256 KiB, NUL byte) stay under a new name. The write (create parent directory, `.bak` copy, `.tmp` + rename) is removed here; `HardwareConfigStore` writes instead (`src/hardware/HardwareConfigStore.cpp:256`, `:357`) |
| `struct MediaLibraryItem` | `App:5469-5486` | `App:6361-6391` | extended-in-place | 16 fields |
| `clipContainerTypeLabel()` | `App:5685-5696` | `App:6661-6674` | behaviour-changed | `.mov` / `.mp4` also count as ProRes / H.264 when the file stem equals the folder name; the `prores_` / `h264_` prefix rule stays |
| `wavDurationTextForFile()` | `App:5786-5853` | `wavFormatForFile()` `App:6778-6845` + wrapper `:6847-6851` | extended-in-place | The RIFF parser now returns `std::optional<WavFormat>`; the old name is a 3-line wrapper with the same output |
| `streamFileToClient()` | `App:6193-6208` | `App:7200-7217` | extended-in-place | New parameter `const std::function<bool()> &stop = {}`; checked before each 64 KiB read |
| `streamZipArchiveToClient()` | `App:6215-6280` | `App:7279-7352` | extended-in-place | Same `stop` parameter; on stop the loop ends and the zip child gets `SIGTERM` before `waitpid` |
| `discoverMediaLibraryItems()` | `App:6282-6448` | `App:7407-7623` | behaviour-changed | New parameter `bool held`. Non-`Timelapse_` folders ask `clipFactsCache()` first; with facts the folder scan and `mediaStatsForPath` are skipped and size, count, duration, fps, time come from the facts. In a hold a folder without cached facts is skipped. `Photos/` and `Audio/` loops unchanged |
| `buildCurrentPresetPayload()` | `App:6522` | `App:7697` | extended-in-place | 4 UI switches after `dateTimeOverlayEnabled`; 13 camera keys after `cameraIso`; `cameraCdngLog` after `cameraCdngCompression` |
| `ApertarCoreApp::ApertarCoreApp()` | `App:6781-6794` (empty body) | `App:7974-7995` | extended-in-place | Body sets `bufferbudget::safetyStopHook()` |
| `ApertarCoreApp::start()` | `App:6801-6903` | `App:8002-8161` | extended-in-place | 6 threads started before `camera_.start()`; `stopMediaWatcher()` added to the 3 failure paths; `mediaTrimSetting_` from the camera settings; `appliedHardwareText_` and three `setSeenCallback` calls before the input drivers start; validation and adopt block; controls worker thread |
| `ApertarCoreApp::stop()` | `App:6905` | `App:8163-8205` | extended-in-place | Controls worker stopped and joined first; `stopStoragePreroll()` before `camera_.stop()`; `stopMediaWatcher()` after `stopPreviewPublisher()` (it also stops the merge, trim, buffer-event and safety-stop threads, `App:11054-11077`) |

## 6. New abstractions used or defined here

| Name | Kind | Where | Purpose | Upstream uses for the same job |
| --- | --- | --- | --- | --- |
| `hwconf` (`Facts`, `Issue`, `Conflict`, `validate`, `parseConfigTxt`) | header-only namespace | `src/hardware/HardwareConfigText.hpp` (`:668-682`, `:738`, `:1040`) | The hardware file as text: parse, key edits, merge, validator | No validator. Each hardware class parses its own section: `GpioInput::loadConfig` `src/hardware/GpioInput.cpp:373 @up`; `loadIna219HardwareConfig` `App:4450-4506 @up` |
| `hardware::HardwareConfigStore`, `configStore()` | class + function-static singleton | `src/hardware/HardwareConfigStore.hpp:68-132`, `.cpp:499-503` | One writer of the hardware file: revision, history, backup, atomic write | `saveHardwareConfigFile` `App:5323-5386 @up`; IMU writes `writeHardwareConfigValue` `src/hardware/Mpu6050RecordingSession.cpp:604`, `:1300 @up` |
| `hardwareConfigFacts()` | free function | `App:4965-4978` | What the validator needs: I2C buses, DPI overlay lines | none |
| `controlsIssuesJson`, `controlsConflictsJson`, `controlsReplacedJson`, `controlsErrorCount` | free functions | `App:4980-5029` | JSON for Controls and Config replies | Same shape of helper: `jsonMediaDriveArray` `App:2392 @up`, `jsonStringArray` `App:293 @up` |
| `CfeHatConfig`, `CfeHatReader`, `loadCfeHatConfig()` | header-only struct + class; free function | `src/util/CfeHat.hpp`; `App:5296-5346` | Read the CFexpress HAT slot bit over I2C | C++: none. Upstream's only reader of `[cfexpress_hat]` is the embedded Python reinsert helper `App:3449-3450 @up`. Loader pattern: `loadIna219HardwareConfig` `App:4450-4506 @up` |
| `playback::PlaybackYield`, `playbackYield()`, `playbackYieldActive()`, `playbackNowMs()` | header-only class + file-scope singleton accessors | `src/playback/PlaybackHold.hpp:69-89`; `App:6337-6352` | Lock-free "a take is starting" window that streams and decodes check | none (upstream Core has no playback). Function-static state inside one function exists: `App:2269-2272 @up`, `App:2788-2790 @up` |
| `playback::ClipFacts`, `ClipFactsCache`, `clipFactsCache()` | header-only struct + class + file-scope singleton | `src/playback/ClipProbe.hpp:93-244`; `App:6354-6359` | Per-clip facts from the files, cached on the folder mtime | `mediaStatsForPath` `App:5915 @up` and `durationTextForFrameCount` `App:5747 @up`, recomputed on each `/api/media` call |
| `clipInfoJson()` | free function | `App:7354-7405` | Body of `GET /api/media/clip` | none (no per-clip route) |
| `MediaDeleteScope` | RAII struct | `App:6454-6462` | Sets `mediaDeleteActive_` for the length of a delete | none |
| `runTrimHelperProcess()`, `trimNowMs()`, `mediaTrimEnvOff()`, `mediaFreeBytesNow()` | free functions | `App:6393-6452` | Run `sudo -n <helper> <mountpoint>` with fork/exec, publish the pid so another thread can end it | `runShellCommandCapture` (popen) `App:1501 @up`; `standbyUsbPower` `App:1541-1545 @up` |
| `scripts/apertar-media-trim`, `config/apertar-media-trim.sudoers` | root helper script + sudoers file | repo root | The trim itself | Upstream calls root helpers the same way (`/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power`, `App:1544`, `:1549 @up`); the scripts are not in upstream's Core repo (`scripts/` holds `start-apertar-core.sh` only) |
| `WavFormat`, `wavFormatForFile()`, `wavSoundText()` | struct + free functions | `App:6765-6860` | One RIFF parser for the length and the SOUND row | `wavDurationTextForFile` `App:5786-5853 @up` |
| `streamFileRangeToClient()`, `parseSingleByteRange()` | free functions | `App:7219-7272` | HTTP Range for a WAV: `pread` from an `O_CLOEXEC` descriptor, `posix_fadvise(DONTNEED)` behind it | `streamFileToClient` `App:6193-6208 @up` (whole file, `ifstream`) |
| `bufferbudget::safetyStopHook()` | process-global `std::function` | `src/util/BufferBudget.hpp:256-266`; set `App:7987-7994`; called `src/camera/CameraController.cpp:5018` | The write queue tells the app that the buffer reached the stop level | Camera-to-app calls go through the callbacks given to `CameraController`'s constructor: `App:6781-6785 @up` |
| Worker threads `runMediaTrim`, `runClipMerge`, `runStoragePreroll`, `runMediaWatcher`, `runBufferEvents`, `runBufferSafetyStop`, `runControlsWorker` | 7 member threads | started `App:8027-8052`, `:8156-8157`; members `src/ApertarCoreApp.hpp:184`, `:257-313` | Background work off the command path | Upstream App has 2 workers started in `start()` plus 1 on demand: `runPreviewPublisher`, `runMjpegEncoder`, `runMediaSpeedTest` (`src/ApertarCoreApp.hpp:88`, `:90`, `:99`, `:147`, `:157`, `:176 @up`) |
| `refreshBufferRequest()` | free function (other unit) | `App:273-286`; called `App:8034`, `:8145` | Publishes `[storage]` and `[media]` requests as atomics | none |

## 7. Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| `saveHardwareConfigFile()` | `App:5323-5386 @up`; removed by `5395fa4` | `POST /api/config` no longer writes the file itself. Backup and atomic write happen in `HardwareConfigStore`. The three input checks remain |
| Template `[imu]` keys `bus=10`, `address=0x68`, `sample_rate_hz=500`, `gyro_range_dps=2000`, `accel_range_g=8`, `orientation=XYZ` | `App:4346-4351 @up`; removed by `4d80a35` | The template no longer shows them. Upstream's `[imu]` reader takes only `driver`, `sync_mode`, `enabled`, `sync_offset_ms` (`Mpu6050RecordingSession.cpp:939-954 @up`) |
| Template `[display]` defaults `720x720`, `square`, `hdmi_external_only=false` | `App:4313`, `:4320-4322`, `:4329 @up`; changed by `7af9f13` | The template describes an HDMI 1080p monitor, not the 720x720 panel |
| Template `[pcf8574] bus=10` | `App:4363 @up`; changed by `4d80a35` | Template says bus 1 |
| Upstream raw byte-rate model and the fixed H.264 rate | `App:4752-4762 @up`; removed by `3c4f07d` | `record_time_left_minutes` changes for every raw format and for H.264 |
| `/api/media` in a hold: folders without cached facts | `App:7451-7454 @port` | While a take or another hold lasts, ProRes, H.264, MLV and timelapse folders and unprobed cDNG clips are missing from the list. Upstream always listed every folder |
| `/api/media` numbers for cDNG folders | `App:7491-7519 @port`; `src/playback/ClipProbe.hpp:123-130`, `:157-161` | `size_bytes` = frames + WAV + stretched WAV + `fps-ramp.txt` (was every file); `file_count` = frame count (was every file); `duration_text` = number span at the clip's own fps (was frames / current camera fps); `fps_text` = the clip's FrameRate tag, 24 when absent (was the current camera fps); `modified_*` = folder mtime (was newest file time) |
| GPIO chip definition | see section 9 | Not removed in this slice. Absent from the GPIO input sections of Core's template |

## 8. Board assumptions

| What | Where |
| --- | --- |
| I2C bus numbers in the template: `[pcf8574] bus=1` (port), `[neorotary4] bus=1`, `[grove_analog] bus=1` (port); `[ina219] bus=4`, `[cfexpress_hat] bus=10` (upstream, unchanged) | `App:5127`, `:5134`, `:5156`; `:5040`, `:5045 @port` |
| CFexpress HAT default: I2C bus 10, address 0x34, off unless the section exists | `src/util/CfeHat.hpp:18-22`; `App:5314-5318 @port` |
| PCIe controller `pcie_controller=1000110000.pcie` (upstream, unchanged) | `App:5050 @port` = `App:4310 @up` |
| Display default is an HDMI 1920x1080 monitor (`hdmi_external_only=true`) | `App:5089-5091`, `:5098 @port` |
| RAM: `buffer_ram_fraction=0.6`, `buffer_ram_floor_mb=512`, `buffer_ram_max_fraction=0.5`; "sized from the free memory at the start of a take" | `App:5051-5057 @port` |
| IMX585 gain codes: `clear_hdr_iso_max_12bit=720` (code 57), `clear_hdr_iso_max_16bit=1585` (code 80) | `App:5074-5079 @port` |
| Validator facts: I2C buses = the `/dev/i2c-N` that exist; DPI overlays from `/boot/firmware/config.txt` | `App:4969-4976`, `:3228 @port` |
| `parseConfigTxt` applies only `[all]` and `[pi5]` filter blocks of `config.txt` (not `[cm5]`, `[pi4]`, `[cm4]`); called from this slice | `src/hardware/HardwareConfigText.hpp:1037`, `:1051`; call `App:4976 @port` |
| Validator pin rules assume the Pi header: BCM 0..27, GPIO 2/3 = I2C bus 1, a DPI overlay holds every GPIO <= 27, messages say "this Pi"; none looks at `chip=`; fed by the facts built here | `src/hardware/HardwareConfigText.hpp:693-705`, `:851`, `:865-871 @port` |
| GPIO chip in the template: `gpiochip=auto` for both outputs only; comment "target=gpio uses a Raspberry Pi GPIO line" (upstream text) | `App:5161`, `:5168`, `:5182 @port` |
| User `pi` and home path: `/home/pi/apertar-hardware.conf` (upstream, unchanged); trim sudoers rule names user `pi` | `App:4921 @port`; `config/apertar-media-trim.sudoers` |
| Root helper by absolute path: `/usr/bin/sudo -n /usr/local/libexec/apertar-media-trim <mountpoint>` | `App:6432`, `:11484 @port` |
| Sensor names by substring: `imx283` added beside `imx477`, `imx577`, `imx294`, `imx585` | `App:5657-5662 @port` |
| Threads: `start()` now creates 7 more long-lived threads (upstream: 2). No core pinning or priority in this slice | `App:8027-8052`, `:8156-8157 @port` |
| Fan, core count, RP1, gpiochip numbers | none in this slice |

## 9. GPIO chip definition (`chip=` / `gpiochip=`): owner request

Owner request relayed with this run: reinsert the definition of the GPIO chip, because the GPIO lines may be those of another chip (for example a microcontroller).
This stage changes nothing. This is what the slice holds and where the definition went.

### 9.1 In this slice

| Fact | Evidence |
| --- | --- |
| Core's template keeps `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]`. Unchanged from upstream | `App:5168`, `:5182 @port` = `App:4380`, `:4394 @up` |
| Core's template `[gpio]` has no `chip=` line. Same in upstream's Core template | `App:5137-5140 @port` = `App:4366-4369 @up` |
| The port added `[gpio_encoders]` and `[gpio_switches]` to Core's template without a `chip=` line | `App:5142-5144` (`4d80a35`), `:5146-5151` (`c34f844`) `@port` |
| The `[gpio_switches]` comment names `chip`: "read like [gpio] (chip, pull, active_low, debounce_ms)". The reader takes chip, pull, active_low and debounce from `[gpio_buttons]`; a `chip=` inside `[gpio_switches]` is not read | `App:5147 @port`; `src/hardware/GpioInput.cpp:311-336 @port` |
| The validator facts built here carry I2C buses and DPI lines only. No GPIO chip | `App:4965-4978 @port`; `src/hardware/HardwareConfigText.hpp:668-672` |
| Spelling: the template writes `gpiochip=`; the store's canonical spelling is `chip` | `App:5168 @port`; `src/hardware/HardwareConfigText.hpp:172` |

### 9.2 Where the original defines it (measuring stick)

| Fact | Evidence |
| --- | --- |
| The original developer's default file, written by the touch UI when the file is missing, has `chip=auto` under `[gpio_buttons]` and under `[gpio_encoders]`, and `gpiochip=auto` under both outputs | `ensureDefaultHardwareConfigFile` `/home/user/wt/ui-upstream/src/DisplayConfigBridge.cpp:40-57`; keys `:110`, `:123`, `:156-161`, `:168-172`; second copy `src/Ina219Bridge.cpp:129`, `:142`, `:175-180`, `:187-191 @up` |
| Upstream readers take `chip`, `gpiochip`, `gpio_chip`; `auto` scores `/dev/gpiochip0..9` | `src/hardware/GpioInput.cpp:431-432`, `:505-537`; `TriggerOutput.cpp:311-312`; `RecordingIndicatorOutput.cpp:319-322`, `:347-348 @up` |

### 9.3 Where the port dropped it (outside this slice)

| Fact | Evidence |
| --- | --- |
| The touch UI no longer writes a default file. Its two templates, with `chip=auto`, are gone. Core's template (this slice) is the only one left | UI commit `c9d841f` "ui: stop writing a default hardware file when it is missing (T38, part 4)": `src/DisplayConfigBridge.cpp` -298, `src/Ina219Bridge.cpp` -280 |
| The Controls page had a `chip` setting for the GPIO buttons: `{"chip", "GPIO chip", "text", "auto", "", 0, 0}` | added by `166cc4d` (`src/hardware/ControlsModel.hpp:174 @166cc4d`) |
| That setting and `poll_ms` were removed. Comment left: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" | removed by `c140c4f`; `src/hardware/ControlsModel.hpp:257-263 @port` |
| The page's status line "Chip <path> (<label>), <n> lines" was removed | added by `166cc4d`, removed by `f5fe41b` ("The GPIO card no longer lists the chip and pins") in `WCP` |
| `get_controls` still reports the chip: `status.chip{ok,path,label,lines,error}`; the card title is "Raspberry Pi GPIO" | `App:11987-11999 @port` |
| The key model still accepts `chip` for `[gpio_buttons]` and both outputs; not for `[gpio_encoders]` or `[gpio_switches]` | `src/hardware/HardwareConfigText.hpp:457`, `:460-464`, `:475-476 @port` |
| The readers still take the key | `src/hardware/GpioInput.cpp:343-344`; `TriggerOutput.cpp:305-306`; `RecordingIndicatorOutput.cpp:312-315`, `:340-341 @port` |
| Output settings on the page have `line` 0..27 and no chip | `src/hardware/ControlsModel.hpp:264-271 @port` |

### 9.4 Insertion points in this slice for the reinsert stage

| Place | Line @port |
| --- | --- |
| `[gpio]` block of Core's template | `App:5137-5140` |
| `[gpio_encoders]` block | `App:5142-5144` |
| `[gpio_switches]` comment that names `chip` | `App:5147` |
| `hardwareConfigFacts()` if the validator is to know the chip | `App:4965-4978` |

## 10. Facts noted for later stages (not judged)

| Fact | Evidence |
| --- | --- |
| `boot_copy` in `GET /api/config` has no reader in Core, Core tools or the UI | `grep -rn boot_copy` over `Apertar-Core/src`, `Apertar-Core/tools`, `Apertar-UI/src`, `Apertar-UI/qml`: only `App:6221` |
| `audio_url` is built with `escapeJson(id)`, not URL-encoded. The upstream helper for media URLs encodes | `App:7387` vs `mediaDownloadUrl` `App:7147-7150 @port` |
| `else if (!held)` is always true when reached: a held folder without facts was skipped earlier. The comment above it still says "or the bare entry" | `App:7451-7454`, `:7488-7490`, `:7520 @port` |
| In a hold the list still iterates the media root, stats each folder and scans `Photos/` and `Audio/`. The comment says "In a hold nothing may read the card" | `App:7428`, `:7444`, `:7499`, `:7534-7615 @port` |
| `loadCfeHatConfig()` turns the HAT on when the section header exists (`enabled` starts false); `loadIna219HardwareConfig()` starts true | `App:5314-5318`; `src/util/CfeHat.hpp:19`; `App:4914 @port` |
| `StoreInfo::exists` means "stat ok and a regular file", the same test upstream's `exists` made | `src/hardware/HardwareConfigStore.cpp:134-139`, `:225-234 @port`; `App:5294 @up` |
| The 14 new camera preset keys do not occur in the touch UI. The four UI switches are `SettingsBridge` properties | `grep -rln -e cameraClearHdr -e cameraCdngLog -e cameraClipNameTemplate -e cameraFpsSpeedRamp -e cameraConformFps -e cameraFpsPhaseLock -e cameraHdr -e cameraTimecodeMode Apertar-UI/src Apertar-UI/qml`: no file; `Apertar-UI/src/SettingsBridge.cpp:368-371 @cinemate-port` |
| `refreshBufferRequest()` runs twice in `start()` | `App:8034`, `:8145 @port` |
| `mediaWatcherThread_` is started without the `joinable()` guard the other five threads have | `App:8043-8044` vs `:8027`, `:8031`, `:8039`, `:8045`, `:8049 @port` |
| `clipInfoJson` has nested values: `holes` array of pairs, `ramp` object or null, `meta` and `extra` objects | `App:7362-7367`, `:7390-7400 @port` |
| `playback::sizeText` formats like upstream `formatBytesHuman` | `src/playback/ClipProbe.hpp:41-52`; `App:3922-3936 @up` |
| Upstream had the hardware template in three places (Core, two in the UI). The port edited Core's and removed the UI's | `App:4291 @up`; `ui-upstream/src/DisplayConfigBridge.cpp:57`; `src/Ina219Bridge.cpp:85`; UI `c9d841f` |
| Internal tags in comments of this slice: T21 `:5585`; T47 `:6335`, `:6378`, `:7354`, `:7442`, `:7488`; R1 `:6390`; Q23 `:6454`; T51 `:6764`, `:7219`; T50 `:7208`, `:7336`; "design 4.3" (written with a section sign) `:7354`; T37 `:8032`, `:8136`; T39 `:8117`, `:8172`; T42 `:8118` | `App @port` |
| "CineMate" in template text an operator reads | `App:5052`, `:5068 @port` |
| Header comments of new files: "design sketch v2 (not in any repository)"; "reference for the tutorial; not in any repository until you type it" | `src/playback/PlaybackHold.hpp:3`; `src/playback/ClipProbe.hpp:3 @port` |
| Commit messages of `f91fafa`, `ab4cc92`, `a37a902`, `fa19856` say "Pi build pending"; the fork log says tested on the Pi 2026-10-29 | section 2 |

## 11. Unconfirmed

| Item | Command that settles it |
| --- | --- |
| Behaviour on a Pi (threads, trim helper, HAT read, `/api/media` in a hold): this container has no camera, GPIO or I2C | run on the Pi |
| Whether the touch UI's preset apply passes unknown `camera*` keys through to Core's `apply_preset` | read the preset apply path in `/home/user/Apertar-UI/src` (`grep -rn 'apply_preset' /home/user/Apertar-UI/src`) |
