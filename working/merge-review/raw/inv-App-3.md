# Inventory: unit App-3 (`src/ApertarCoreApp.cpp`, port lines 8408-10674)

Stage 1 of 3. What the port added or changed in this slice. No judgement.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/App.part03.diff`, all 1327 lines, 20 hunks |
| Port file | `/home/user/Apertar-Core/src/ApertarCoreApp.cpp` @cinemate-port `01f170c` |
| Original | `/home/user/wt/core-upstream/src/ApertarCoreApp.cpp` @upstream-1.6.0 `35dbe67` |
| Blame | `git blame -s -L 8408,10700 cinemate-port`; 112 runs of non-upstream lines, 44 commits |
| What the slice is | `handleWebRequest` tail (HTTP routes), `buildMediaLibraryJson`, `buildWebStateJson`, `captureWebPreviewFrame`, hardware-input dispatch (`normalizeHardwareAnalogTarget`, `dispatchHardwareInputCommand`, `handleHardwareAnalogInput`, `handleSingleHardwareInputAction`). There is no `handleRequest` socket function and no `publishEvent` addition in these lines; the socket chain `handleCommand` is outside the slice |
| Labels | confirmed unless stated. Commit messages and fork-log are intent, not proof (BRIEF rule 5) |

Port lines (@port) for the routes: `/api/buffer` 8419, `/api/media/clip` 8442, `/api/media/frame` 8475, `/api/media/file` 8550,
`/api/config` GET 8613 / POST 8620, `/api/media/download` 8682, `/api/media/delete` 9004, `/api/boot-config` GET 9161 / POST 9170,
`/api/boot-config/parse` 9200. Upstream route list @up `App:7154-7637`: state, media, config GET/POST, media/download,
download-selected, presets, presets/import, presets/save, presets/delete, media/delete, delete-selected, command. Eight of those
survive; the port adds seven route paths (the three boot-config verbs count as 3 entries on 2 paths).

## 1. Hunk map

| # | Port lines | Upstream anchor (@up) | + / - | Content | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | 8418-8427 | before `/api/state` `App:7154` | +10 | `GET /api/buffer` | `d44b177`, `c5db8b2` |
| 2 | 8442-8612 | after `/api/media` `App:7161` | +170 | `GET /api/media/clip`, `/frame`, `/file` | `f91fafa` 33, `1af26c8` 75, `fa19856` 63 |
| 3 | 8620-8680 | `POST /api/config` `App:7175-7196` | +40 / -14 | save through `HardwareConfigStore::replace`, revision header, 409 | `5395fa4`, `dcf09ee`, `d44b177` |
| 4 | 8683-8690 | start of `/api/media/download` `App:7197` | +8 | hold check, 409 | `a37a902` |
| 5 | 8742, 8767, 8799, 8856 | 4 stream callers | +4 / -4 | `playbackYieldActive` passed to `streamZipArchiveToClient`, `streamFileToClient` | `a37a902` |
| 6 | 8812-8819 | start of `download-selected` `App:7318` | +8 | hold check, 409 | `a37a902` |
| 7 | 9022-9031, 9105-9114 | `media/delete` `App:7503`, `delete-selected` `App:7575` | +20 | 409 on pending writes, `MediaDeleteScope`, `waitForClipMerge`, trim after delete | `a37a902`, `ba0658d`, `d44b177` |
| 8 | 9152, 9160-9213 | after `delete-selected`, before `/api/command` `App:7637` | +54 | `/api/boot-config` GET, POST, `/parse` | `2955ef8` 54, `d44b177` |
| 9 | 9250-9291 | `buildMediaLibraryJson` | +14 | hold, cache-only scan, 13 item fields, `held` | `f91fafa` |
| 10 | 9298-9325 | `buildWebStateJson` head | +15 | phase-lock, buffer, binning, media snapshot, profile locals; "Media Removed/Error" label | `80ddac1`, `d44b177`, `4ab1057`, `438a342`, `26da30e`, `3c4f07d` |
| 11 | 9362-9373 | before CPU read | +12 | `playback::HoldSignals` -> `playback_hold` | `f91fafa` |
| 12 | 9413-9418 | record_time_left | +3 / -1 | floor to a tenth | `bda2066` |
| 13 | 9457-9600 | `buildWebStateJson` body | +76 / -1 | about 70 new state members (section 3) | 24 commits |
| 14 | 9663-9666, 9694 | UI settings members | +5 | 4 recording-indicator switches, `valueStepsJson` | `f4fb084`, `d44b177`, `92d0970`, `b0e90ad` |
| 15 | 9778-9784 | `captureWebPreviewFrame` | +7 / -2 | web preview rate while a raw take runs | `fb557e9` |
| 16 | 10090 | `normalizeHardwareAnalogTarget` `App:8410` | +1 / -17 | body replaced by `hardware::actions::canonicalAnalogTarget` | `916c1dd` |
| 17 | 10119 | `dispatchHardwareInputCommand` | +1 | `abortSafetyStopFlushForRecord(command.name)` | `c5db8b2` |
| 18 | 10160-10223 | `handleHardwareAnalogInput` iso/fps/resolution/wb/shutter | +45 / -25 | value lists, free stepping, ladder guard, flicker-free | `b0e90ad`, `09256a7`, `f95567d` |
| 19 | 10441-10566 | `handleSingleHardwareInputAction` fps/clear_hdr/resolution/iso/shutter/wb | +100 / -15 | same plus `clear_hdr` action, Auto below lowest | `b0e90ad`, `243fe2c`, `09256a7`, `f95567d`, `b5b787e`, `60645d4` |
| 20 | 10684-10686 | unknown action log `App:8954` | +3 / -1 | "Did you mean" | `916c1dd` |

## 2. Commits that wrote this slice

Status from fork-log (`/home/user/apertar-kb/fork-log.md`) and commit `Tested:` lines. Dates 2026.

| Commit | Date | Subject | Fork log (row) | Tested |
| --- | --- | --- | --- | --- |
| `f91fafa` | 10-29 | Core knows its clips: facts, hold rule, yield window (T47) | 99: fork-only, Pi only | Pi 2026-10-29: first list 4.2 s then 20 ms; hold and 409 in a 4 s take. Host tests 41 + 22 checks |
| `ab4cc92` | 10-29 | the list asks the facts cache first | 99 | as above |
| `1af26c8` | 10-29 | `/api/media/frame` by frame number (T48) | 100: fork-only, Pi only | Pi 2026-10-29: 64-271 ms a frame, 0.8 ms cached, pictures checked. Commit says "Pi build pending" |
| `fa19856` | 10-29 | `/api/media/file` with Range (T51) | 104: fork-only, Pi only | Pi 2026-10-29: Range and 416, Chrome playback. Safari, Firefox, phone not tested |
| `a37a902` | 10-29 | downloads and deletes yield to a take (T50 Core) | 103 | Pi 2026-10-29: download stopped within 0.3 s of a take; 409/400 in a take; Q23 (record during delete) not tested live |
| `5395fa4` | 10-29 | Config page file goes through the store (T38 part 1) | 110: fork-only | desk only |
| `2955ef8` | 11-01 | `get_boot_config` / `set_boot_config`, `/api/boot-config` (config.txt writer) | not found by short sha in fork-log (grep) | not read in this slice; see commit message |
| `d44b177` | 10-31 | drop-frames squash (19 commits) | 138: offer in pieces after Pi tests | host tests Mac; compiles on Pi; trim at mount and Log 16 to 12 run on Pi; RAM queue, safety stop, buttons not run |
| `c5db8b2` | 11-01 | record during safety-stop flush discards queued frames | 138 text, owner decision 2026-11-01 | not stated |
| `ba0658d` | 11-08 | merge worker flattens split clips while idle | 188 | desk (`clip_merge_test`); Pi build rc 0, not run on camera |
| `ce0bd90` | 11-04 | `set_media_trim` switch, Performance card | 170 | Pi only |
| `b0e90ad` | 10-28 | T33 value lists, free stepping, flicker-free angles | 76 | Patrik 2026-10-28 |
| `243fe2c` | 10-29 | `clear_hdr` action for buttons and knob pushes | 119 | not stated |
| `916c1dd` | 10-29 | one action vocabulary `ActionCatalog.hpp`, `list_actions` (T36) | 105: fork-only | not stated |
| `09256a7` | 10-28 | active ladder blocks manual resolution, bit depth, Clear HDR | 95 | built 2026-10-28 |
| `0041ba0`, `e16033e`, `cdf83cd` | 10-28/29 | mode ladder state members (T34) | 87, 96, 115 | socket, two takes, presets 2026-10-28 |
| `60645d4`, `b5b787e` | 10-28 | WB dial reaches Auto; Auto ISO outside Clear HDR | 84, 85 | built 2026-10-28; Auto ISO in lossless **unverified** |
| `f95567d` | 11-01 | PCF resolution step cycles IMX283 modes | not found | not stated |
| `fb557e9` | 11-01 | `APERTAR_WEB_PREVIEW_RECORDING_FPS` | not found | not stated |
| `3c4f07d`, `bda2066` | 10-27 | storage label "Media Removed"; time left follows format; rounds down | 56, 57 | T21 tested (agrees with HDMI up to rounding); Patrik 2026-10-27 |
| `438a342`, `26da30e` | 10-26 | survive a yanked drive; media profile | 41, 46 | 438a342 built 22:27; 26da30e built, not tested |
| `4ab1057` | 10-26 | sensor-mode binning | 36 | built and run 21:39 |
| `80ddac1` | 10-26 | frame-rate phase lock (off by default) | 37 | built 22:04 |
| `64bbbaa`, `4d80a35` | 11-01, 10-29 | dropped-frame count; controls errors/warnings | 139, 109 | not stated |
| `8175273`, `646a194`, `6d217c7`, `97adea0`, `d7ff071`, `caa0153`, `631721d`, `e625c68`, `faa2958`, `ca7b7c2`, `014a2bf` | 10-25 to 11-01 | one state member each (section 3) | rows 25, 61, 62, 71, 73, 67, 171, 58, 69 | see fork-log |
| `f4fb084`, `92d0970` | 10-28, 11-01 | recording frame, red timecode, audio outline switches | 81 | Patrik 2026-10-28 |
| `dcf09ee` | 10-30 | saves apply without restart (controls worker) | 129 | desk host 120/121; Pi build |

## 3. Features touching this unit

Every feature is fork-only: none exists @upstream-1.6.0.

| Feature (operator view) | Routes / commands | State fields | Config keys / env | Files / UI | Commits |
| --- | --- | --- | --- | --- | --- |
| Clip Browser info for one clip (fps, holes, timecode, audio url) | `GET /api/media/clip?kind=folder&id=` | list items gain `format`, `format_label`, `playable`, `play_reason`, `fps`, `fps_fallback`, `shot_date_text`, `shot_ms`, `first_number`, `last_number`, `missing_frames`, `empty_frames`, `ramp`, `has_audio`, `token`, `timecode_start`; list gains `held` | none | WebUI Media tab (WCP, other unit) | `f91fafa` `ab4cc92` |
| Clip Viewer picture: Core decodes a cDNG frame to JPEG | `GET /api/media/frame?kind=folder&id=&n=&w=&v=`; w in 320/480/640/960/1280/1920; headers `X-Frame-Number`, `X-Frame-Index`, `X-Frame-Count`, `X-Histogram`, `X-Frame-Source`, `X-Decode-Ms`; 400, 404, 409, 503-busy as `{"busy":true}` | none | env `APERTAR_PLAYBACK_WORKERS` (default 2, clamp 1-4, `PlaybackFrames.cpp:82`) | `third_party/liblj92/`, `src/playback/{DngFrameReader,RawRender,DecodeSlots,PlaybackFrames}`; JPEG caches 8 MB + 24 MB | `1af26c8` |
| Clip Viewer sound | `GET /api/media/file?kind=folder&id=&name=<x>.wav`, HTTP Range, 200/206/416, 409 hold | none (`has_audio`, `audio_url` in clip info) | none | streamed from `streamFileRangeToClient` | `fa19856` |
| Playback stands aside for a take | all media routes: 409 `{"hold":"<name>"}`; `playback_hold` in state; hold names recording, writing, media_test, standby, media | `playback_hold` | none | `src/playback/PlaybackHold.hpp` | `f91fafa` |
| Downloads and deletes yield to a take | download, download-selected: 409 in a hold, stream stops within one chunk, zip child gets SIGTERM; delete, delete-selected: 409 "Wait for the current capture", `MediaDeleteScope(mediaDeleteActive_)`, record/photo/timelapse refused during delete | none | none | none | `a37a902` |
| Trim recording drive after a big delete | after delete: `trimMediaAfterDelete(freeBefore)`, runs trim when freed >= 1 GiB | `media_trim_*` via `mediaTrimStateJson()`, `media_trim_enabled`, `media_trim_env_off` | env `APERTAR_MEDIA_TRIM=0` forces off; `[storage] media_trim` (set by `set_media_trim`) | helper `scripts/apertar-media-trim` run as `sudo -n` (`runTrimHelperProcess`, App:6409); WebUI System pane Performance card | `d44b177` `ce0bd90` |
| Merge worker waits out before a delete | `waitForClipMerge("media_delete", 0)` in both delete routes (App:9028, 9111) | `clipMergeStateJson()`: `clip_merge_*`, `clip_merge_enabled`, `clip_merge_env_off`, `frames_per_folder`, `frames_per_folder_env` | `[storage] clip_merge`, env `APERTAR_CLIP_MERGE=0`, env `APERTAR_CDNG_FRAMES_PER_FOLDER` | `src/cdng/ClipMerge.hpp` | `ba0658d` |
| Write-buffer bar polled at 4 Hz | `GET /api/buffer` (lock-free: no `commandMutex_`, no controller mutex) returns `buffer_used`, `buffer_capacity`, `buffer_fill`, `buffer_mode`, `buffer_unit`, `recording` plus `bufferSettingMembers()` | same `buffer_*` members added to `/api/state` (`bufferMembers`, App:301) | `[storage]` keys, env `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL` (read by `refreshBufferRequest`, App:273) | WebUI bar; `bufferbudget::safetyStopState()` | `d44b177` |
| Record during a safety-stop flush starts at once | `abortSafetyStopFlushForRecord` before `hardwareActionMutex_` in `dispatchHardwareInputCommand` (App:10119) | none | none | stderr line "flush aborted by record" | `c5db8b2` |
| Config page save with conflict handling | `POST /api/config` header `x-apertar-revision`; replies 400 `invalid`, 409 `old_page` (browser, no revision), 409 `stale`, `conflict`, `being_written`, `locked`, `merge_review`; body gains `revision`, `written`, `errors`, `issues`, `new_errors`, `conflicts` | `controls_errors`, `controls_warnings` | none | `<cfg>.bak` still written (flags.backup) | `5395fa4` `dcf09ee` `4d80a35` |
| Boot config card (System pane) | `GET /api/boot-config`, `POST /api/boot-config` (header `x-apertar-revision` or body `revision`; injects `"cmd":"set_boot_config"` into the body then `parseControlCommand`), `POST /api/boot-config/parse` (upload, 64 KiB cap, not written) | none | env `APERTAR_BOOT_CONFIG` (path override); `/boot/firmware/config.txt` | `src/hardware/BootConfigText.hpp` 1355 lines; socket `get_boot_config`, `set_boot_config` (App:14586, 14589) | `2955ef8` |
| Time left follows format and bit depth | none | `time_left_label` from `timeLeftEstimateLabel` (was constant "Current format estimate"); `record_time_left_minutes` floored to a tenth | none | none | `3c4f07d` `bda2066` |
| Media removed / error labels | none | `media_type_label` = "Media Removed" / "Media Error"; `media_state`, `media_alive`, `media_device`, `media_fstype`, `media_class`, `media_profile`, `recording_fault` | env `APERTAR_MEDIA_REQUIRE_MOUNT=0` bypass (`mediaGateBypassed`) | media watcher thread (other unit) | `438a342` `26da30e` |
| Frame-rate phase lock | none | `fps_phase_lock`, `fps_phase_lock_active`, `_err_us`, `_dur_us`, `_pushes`, `_saturated` | `[camera]` key via `set_fps_phase_lock` | none | `80ddac1` |
| Mode ladder | none | `ladder_active`, `ladder_resolution`, `ladder_ramp_ready`, `ladder_enabled`, `ladder_override`, `ladder_count`, `ladder_text`, `ladder_tops`, `fps_take_max` | `mode_ladder.conf` | analog resolution and PCF resolution step return when `ladderActive` | `0041ba0` `e16033e` `09256a7` `cdf83cd` |
| Clear HDR extras | action `clear_hdr` (buttons and knob pushes: IMX585, raw formats only; on also sends `set_raw_bit_depth 16`) | `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr`, `iso_actual`, `iso_max` | `[camera] clear_hdr_iso_max_*` | none | `243fe2c` `8175273` `646a194` `6d217c7` |
| Speed ramp, conform | none | `fps_speed_ramp`, `_keep_exposure`, `_stretch_audio`, `_after` (return/stay); `conform_fps`; `fps_max`, `fps_take_max` | as per commits | none | `faa2958` `ca7b7c2` `d7ff071` `97adea0` |
| Log recording | none | `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` | none | none | `d44b177` |
| Clip names | none | `clip_name_template`, `clip_name_example` | none | none | `014a2bf` |
| Preview temporal denoise | none | `preview_tdn`, `tuning_file_active` | none | none | `e625c68` |
| Sensor facts | none | `sensor_binning*` (`sensorBinningBody`, App:224), `sensor_mono` | none | none | `4ab1057` `caa0153` |
| Dropped frames | none | `recording_dropped_frames` | none | none | `64bbbaa` |
| Recording indicator switches | none | `recording_frame_enabled`, `recording_red_timecode_enabled`, `audio_recorded_outline_enabled`, `frame_buffer_bar_enabled` | UI.conf keys | WebUI Live preview switches | `f4fb084` `92d0970` `d44b177` |
| Value lists and free stepping for knobs and buttons | analog and button actions use `isoSteps`, `fpsSteps`, `wbSteps`, `shutterAngleSteps`, free flags and increments, `flickerFreeShutterAngles` with `mainsHz` | `valueStepsJson(uiSettings, sensorName)` inside `ui` (App:1963) | UI.conf (`isoSteps` ... ), socket `set_value_steps` (App:14110) | WebUI and touch pickers | `b0e90ad` |
| Auto below lowest on ISO and WB dials | button step `iso`, `wb`: index 0 = Auto, not allowed while Clear HDR | none | none | none | `b5b787e` `60645d4` |
| Web preview during a raw take | MJPEG frame cap uses `webPreviewRecordingFps()` while `rawTakeActive()` | none | env `APERTAR_WEB_PREVIEW_RECORDING_FPS` (default 30 = unchanged, 0 = off, 0.5..30) | App:93 | `fb557e9` |
| Unknown-action hint | stderr "Did you mean 'x'?" | none | none | `hardware::actions::suggestion` | `916c1dd` |

## 4. Interfaces added or changed

### 4.1 HTTP routes (port)

| Route | New or changed | Locking | Replies |
| --- | --- | --- | --- |
| `GET /api/buffer` | new | none | JSON from `bufferMembers` plus `recording` |
| `GET /api/media/clip` | new | none | `clipInfoJson` or 404 / 409 |
| `GET /api/media/frame` | new | none; two decode slots | `image/jpeg` or 400 / 404 / 409 / 503-style busy |
| `GET /api/media/file` | new | none | `audio/wav`, `streaming = true`, `streamWriter` |
| `POST /api/config` | rewritten (function body replaced) | `HardwareConfigStore` | see 3; 409 added |
| `GET /api/media/download`, `download-selected` | extended in place | none | 409 added; stream stop callback |
| `POST /api/media/delete`, `delete-selected` | extended in place | `MediaDeleteScope` | 409 "Wait for the current capture" added |
| `GET`/`POST /api/boot-config`, `POST /api/boot-config/parse` | new | `bootConfigMutex()` | `BootConfigReply{status, body}` |

Response status vocabulary added: 206, 409, 416 (`WebServer.cpp` reason phrases, +3 lines). `WebServer::Response` fields `streaming`, `streamWriter`,
`headers` already exist @up; `request.headers` are looked up in lower case (`"range"`, `"origin"`, `"x-apertar-revision"`).

### 4.2 Error shapes

Upstream errors: `errorReply(id, message)` flat. Port adds `errorReplyBody(id, message, extraMembers)` (App:173) with `"code"`, `"revision"`, `"issues"`,
`"new_errors"`, `"conflicts"` (arrays of objects inside the reply). Also hand-built bodies `{"ok":false,"error":"Playback held: x.","hold":"x"}`
(`/api/media/frame` 409, `/api/media/file` 409, download 409), `{"ok":false,"busy":true}`, `{"ok":false,...,"gone":true}`.

### 4.3 State fields (`/api/state`)

About 70 new members in `buildWebStateJson` (blame runs 9457-9600 and 9663-9694). Grouped list in section 3. Plus the flat `buffer_*` members
(9 of them, from `bufferMembers` and `bufferSettingMembers()`) and `mediaTrimStateJson()` / `clipMergeStateJson()` strings appended with a leading
comma (a builder that returns a fragment, not a flat member).

### 4.4 Socket commands

None added in this slice's lines. Commands the slice's routes depend on, defined elsewhere: `get_boot_config`, `set_boot_config`, `list_actions`,
`set_value_steps`, `set_media_trim`, `set_clip_merge`, `set_buffer_mode`, `set_fps_phase_lock`, `set_conform_fps`, `set_fps_speed_ramp`.

### 4.5 Events

No `publishEvent` addition in this slice. The `buffer` event (`d44b177`) is outside the scope.

## 5. Upstream code modified in this slice

| Region | @up location | Kind | What changed |
| --- | --- | --- | --- |
| `POST /api/config` handler | `App:7175-7196` | rewritten | `saveHardwareConfigFile(body, &backup, &err)` replaced by `checkHardwareConfigText` then `hardware::configStore().replace(base, body, "webui", flags, hardwareConfigFacts())`; reply gains 6 members; 409 for a browser with no revision header |
| `saveHardwareConfigFile` | `App:5323-5386` | rewritten (in slice App-2) | the writer is the store; this route no longer calls it |
| `/api/media/download` | `App:7197` | extended in place | hold check first; `playbackYieldActive` passed to stream functions |
| `/api/media/download-selected` | `App:7318` | extended in place | same |
| `/api/media/delete`, `delete-selected` | `App:7503`, `7575` | extended in place | 409 on `mediaWritesPending`, `MediaDeleteScope`, merge wait, trim after delete |
| `buildMediaLibraryJson` | `App:5469-5486` item struct | extended in place | signature gets `bool cacheOnly`; item gains 13 members |
| `buildWebStateJson` | `App` | extended in place | about 70 members; `time_left_label` constant replaced; `record_time_left_minutes` truncated; media type label depends on the media snapshot (changed behaviour) |
| `captureWebPreviewFrame` | `App:8100-8110` | behaviour-changed | rate limit no longer the constant 30 fps while a raw take runs |
| `normalizeHardwareAnalogTarget` | `App:8410-8430` | removed, moved | 17-line alias map removed; the aliases live in `hardware/ActionCatalog.hpp` |
| `dispatchHardwareInputCommand` | `App:8470` | extended in place | one call before the mutex |
| `handleHardwareAnalogInput` iso, fps, resolution, wb, shutter | `App:8495-8570` | extended in place | option lists take UI settings; free stepping; ladder guard; flicker-free angles |
| `handleSingleHardwareInputAction` fps, iso, shutter, wb, resolution | `App:8800-8870` | extended in place / behaviour-changed | ISO step: Auto offered only when Clear HDR is off (was always); WB step: Auto added (was never); free stepping |
| unknown action log | `App:8954` | extended in place | suggestion appended |

## 6. New abstractions

| Name | Where | Purpose | Upstream equivalent |
| --- | --- | --- | --- |
| `playback::` header-only module (`PlaybackHold`, `ClipFrames`, `DngTags`, `ClipProbe`, `DngFrameReader`, `RawRender`, `DecodeSlots`, `PlaybackFrames.cpp`) | `src/playback/`, 9 files, 1700 lines of new code | hold rule, per-clip facts cache, DNG decode to JPEG | none for the facts or decode; upstream's `discoverMediaLibraryItems` reads the first DNG on each call (`App:6282-6448`) |
| `playback::PlaybackYield` (atomic window) | `PlaybackHold.hpp` | lets a stream stop with no lock; opened by `handleCommand` for `record_start`, `capture_photo`, `timelapse_start`, `run_media_speed_test`, `enter_standby`, `eject_media`, `format_media`; extended by the media watcher | none; upstream's stream functions have no stop callback |
| `playback::HoldSignals` / `playbackHoldFor` | `PlaybackHold.hpp` | pure function over 8 booleans | none. Header comment says "design sketch v2 (not in any repository)" |
| `playback::ClipFactsCache` and `clipFactsCache()` | `ApertarCoreApp.cpp:6354` | file-scope singleton keyed on folder mtime | none |
| `playbackYield()`, `playbackYieldActive()`, `playbackNowMs()` | `App:6335-6352` | file-scope globals | none |
| `DecodeSlots` | `src/playback/DecodeSlots.hpp` | 2 (env 1-4) decode buffers, ~46 MiB a slot; trimmed by the media watcher | none |
| `third_party/liblj92/` | repo root | lossless JPEG decoder, byte-identical to the touch UI's | upstream Core has no `third_party/` (upstream UI has) |
| `hardware::HardwareConfigStore` (`configStore()`) | `src/hardware/HardwareConfigStore.{hpp,cpp}` 639 lines | revisioned reader and writer of `apertar-hardware.conf` with merge and conflicts | `saveHardwareConfigFile` + `editableHardwareConfigPath` (`App:5290-5386`) |
| `hwconf::` (`HardwareConfigText.hpp`, 1141 lines) | `src/hardware/` | `validate`, `Issue`, `Conflict`, `Facts` | none; upstream has no hardware file validation |
| `bootconf::` (`BootConfigText.hpp`, 1355 lines) | `src/hardware/` | parse and edit `config.txt`, board rules, revision, display guard | upstream edits `config.txt` through `writeBootConfigText` for the fan mode only (`App:2845`, `3138`) |
| `BootConfigReply` and `bootConfigGet` / `bootConfigSet` | `App:3760-3800` | shared by route and socket | none (upstream route and socket each build their own reply) |
| `hardware::actions::` (`ActionCatalog.hpp`, 360 lines) | `src/hardware/` | one action vocabulary: canonical names, analog target aliases, `suggestion` | upstream has three copies of `normalizeSingleAction` and one `normalizeHardwareAnalogTarget` in `App` |
| `bufferbudget::` namespace (`safetyStopState`, `abortSafetyStopFlush`, `parseBufferConf`, `requestedBufferMode`) | outside the slice | safety stop and RAM write buffer | none |
| `storagepreroll::`, `util/ClipName.hpp` | outside the slice | pre-roll, clip names | none |
| `MediaDeleteScope` (RAII atomic flag) | `App:6455` | refuse a take during a delete | none |
| `MediaSnapshot`, `MediaProfile`, `mediaSnapshot()`, `mediaProfile()` | `App:11316`, `11386` | media watcher state, per-filesystem tuning | upstream uses `isMountedPath` directly |
| trim worker thread, clip-merge worker thread, controls worker thread (`wakeControlsWorker`, App:12228), safety-stop thread | other units | background work | none |
| helper scripts | `scripts/apertar-media-trim`, `apertar-media-tune`, `apertar-tune` | run by `sudo -n` from `runTrimHelperProcess` | upstream installs no sudo helper for Core (check against `scripts/` @up before calling it new) |
| `errorReplyBody` | `App:173` | error reply with extra members | upstream `errorReply` only |
| `bufferMembers`, `sensorBinningBody`, `valueStepsJson`, `mediaTrimStateJson`, `clipMergeStateJson` | file scope / members | state fragments joined with `"," <<` | upstream builds members inline (and one helper `exposureMeteringJson(settings)` @up) |

## 7. Removed, narrowed, hidden

| What | Where | Effect |
| --- | --- | --- |
| Last-writer-wins on `POST /api/config` | `App:8620-8680` | a browser without `x-apertar-revision` gets 409 `old_page`; a script (no `Origin`) keeps the old behaviour |
| `saveHardwareConfigFile` call from the route | upstream `App:7175` | route no longer uses it; its own 256 KiB cap now lives in `checkHardwareConfigText` (App:6231) |
| Downloads during a take | download routes | refuse with 409; upstream streamed during a take |
| Deletes during pending writes | delete routes | refuse with 409; record_start, capture_photo, timelapse_start refused during a delete ("Deleting media. One moment.") |
| ISO step with Auto in Clear HDR | `handleSingleHardwareInputAction` iso | Auto not offered in Clear HDR (was always offered) |
| Manual resolution input | analog and button resolution | returns silently while `ladderActive` |
| `normalizeHardwareAnalogTarget` alias map | App | moved to `hardware/ActionCatalog.hpp` |
| `time_left_label` | `/api/state` | constant "Current format estimate" replaced by a computed label |
| Preview rate while a raw take runs | `captureWebPreviewFrame` | default unchanged (30), operator can cap or pause with the env var |
| Control socket line limit | commit `5395fa4` message | 64 KiB to 1 MiB (outside slice, `ControlServer.cpp` 5 lines) |

## 8. Assumptions about the board

| Assumption | Where | Note |
| --- | --- | --- |
| `/boot/firmware/config.txt` (Bookworm layout); overlays in `<dir>/overlays/*.dtbo` | `bootConfigPath`, `bootConfigFacts` App:3653; upstream has the path too (`App:2845`) | upstream fan mode edits the same file |
| Board detection from `/proc/device-tree/compatible` and `/proc/device-tree/model` (`bootconf::boardFromDeviceTree`) | App:3655 | board rules for `/api/boot-config/parse` "read with this Pi's board rules" (App:9199); which Pi models `BootConfigText.hpp` knows is outside this slice; confirm in its stage |
| `/sys/class/drm` card connectors | `drmConnectorsJson` App:3665 | DPI overlay shows a connected connector without a panel; the code says so |
| Media root `/media/RAW`; "Mount /media/RAW to manage media" label | App:9559 | upstream text |
| IMX585 and IMX283 by sensor name substring | `lowerAscii(sensorName()).find("imx585")` App:10453; IMX283 mode cycling `f95567d` | `clear_hdr` action is IMX585 only |
| 4 cores: `"N cores active"` label from `std::thread::hardware_concurrency()` | App:9567 | upstream line, unchanged |
| RAM: 2 decode slots ~46 MiB each (~92 MiB) plus 8 + 24 MB JPEG caches, free until `trimIdle` | `DecodeSlots.hpp:27-29`, `PlaybackFrames.cpp:76-77` | fixed numbers; not scaled by RAM size. Env var raises slots to 4 (~184 MiB) |
| 4K UHD 16-bit frames: kMaxDngSampleBytes 40 MiB | `DngTags.hpp:33-37` | static_assert; a larger sensor frame would be refused |
| sudo without a password for the trim helper (`sudo -n`) | `runTrimHelperProcess` App:6409 | operator must install the helper (fork-log row 46: "root helper added, not installed") |
| Analog and button maps: PCF8574 / Grove / NeoRotary events | handlers in this slice | I2C bus numbers and gpiochip numbering are in other units; none appear in these lines |
| `mainsHz` (50 or 60) for flicker-free angles | `uiSettings.mainsHz` | UI.conf value |
| RP1, PCIe, fan | none in this slice | no new references |

## 9. Observations for stage 2 (facts, not verdicts)

| Fact | Evidence |
| --- | --- |
| The route chain in `handleWebRequest` stays a flat `if (method && path)` chain; seven new route blocks of 10 to 90 lines each sit inline | App:8419-9213 |
| `/api/media/frame` and `/api/media/file` build bodies by string concatenation rather than `okReply` / `errorReply` | App:8497-8505, 8554-8565 |
| `/api/boot-config` POST edits the JSON text of the body to inject `"cmd"` and then calls the socket's `parseControlCommand`, so route and socket share `bootConfigSet` | App:9170-9195 |
| The slice calls helper types defined elsewhere in the same file (`bufferMembers` App:301, `clipInfoJson` App:7355, `parseSingleByteRange` App:7247) and in nine new headers | section 6 |
| `buildWebStateJson` grew by about 70 flat scalar members and 3 fragment-returning helpers | section 3 |
| Fork-log marks `5395fa4`, `916c1dd`, `243fe2c`, `4d80a35` as "desk only" or not stated: no Pi run recorded | section 2 |
| `PlaybackHold.hpp` header comment refers to a "design sketch v2 (not in any repository)" and to line numbers in `CameraController.cpp` | `PlaybackHold.hpp:3-25` |
