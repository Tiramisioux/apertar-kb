# Inventory App-5: ApertarCoreApp.cpp, handleCommand (port lines 12727-14875)

Scope: `/home/user/build/review/diffs/App.part05.diff` (901 lines, 16 hunks) read completely. Refs: `@cinemate-port` (`01f170c`),
`@upstream-1.6.0` (`35dbe67`, upstream `handleCommand` starts at `ApertarCoreApp.cpp:9091`). Stage 1: no judgement.
All blame data from `git blame -s cinemate-port`. Fork-log status from `/home/user/apertar-kb/fork-log.md`.
Context line (first 10 lines of hunk 1, `list_sensor_modes`) was written by `f60e301` (already on fork main); only the binning fields are port.

## 1. Hunk map

| # | Port lines | Hunk | Commits (blame) |
| --- | --- | --- | --- |
| 1 | 12727-12975 | `list_sensor_modes` +binning; new `test_output`, `set_controls`, `set_buffer_mode`, `set_frames_per_folder`/`set_clip_merge`, `set_storage_preroll`; `help` list rewritten; `get_state` new keys | `4ab1057`, `dcf09ee`, `f5a61b8`, `014fa22`, `07afbc6`, `4d80a35`, `d44b177`, `ba0658d`, `d7dd337`, `70e8376`, `64bbbaa`, `438a342`, `916c1dd` (help list) |
| 2 | 12986-13015 | `set_iso_auto` takes `enabled` | `646a194` |
| 3 | 13069-13100 | new `set_cdng_log` | `d44b177` |
| 4 | 13184-13310 | new `set_media_trim`, `set_preview_tdn`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_clip_name_template`, `preview_clip_name`, `set_conform_fps`; `set_timecode_mode` `target=` | `ce0bd90`, `e625c68`, `80ddac1`, `faa2958`, `ca7b7c2`, `014a2bf`, `d7ff071`, `909aaa5` |
| 5 | 13495-13525 | four new `handleUiToggle` lines | `f4fb084`, `92d0970` |
| 6 | 14080-14180 | new `get_mode_ladder`, `set_mode_ladder`, `set_value_steps` | `0041ba0`, `cdf83cd`, `b0e90ad` |
| 7 | 14266-14290 | apply-preset: `cameraCdngLog` | `d44b177` (+ `631721d` ctx) |
| 8 | 14313-14395 | apply-preset: speed ramp x4, clip name template, phase lock, `cameraTimecodeMode`, conform fps, Clear HDR + 4 knobs | `8e8ea2e`, `014a2bf`, `d7ff071`, `909aaa5`, `ca7b7c2`, `faa2958`, `80ddac1` |
| 9 | 14419-14470 | apply-preset: `timecodeMode` (UI copy) guarded; 4 new `addBoolUpdate` keys | `909aaa5`, `f4fb084`, `92d0970` |
| 10 | 14518-14550 | apply-preset: mode-ladder check before `applyCapturePreset` | `0041ba0` |
| 11 | 14576-14650 | new `get_boot_config`, `set_boot_config`; new `storage_preroll`; `format_media` pre-roll hooks | `2955ef8`, `d44b177` |
| 12 | 14751-14780 | `record_start` reply +`recording_dropped_frames` | `64bbbaa` |
| 13 | 14823-14870 | `record_stop` pre-roll early stop; reply +`recording_dropped_frames` | `d44b177`, `64bbbaa` |
| 14 | 14875-14905 | `publishEvent`: 4 event names broadcast to all clients | `086443c`, `d44b177`, `dcf09ee`, `438a342` |

## 2. Features seen in this unit (operator view)

| Feature | Commit(s) | Operator gets | fork-log status / tested |
| --- | --- | --- | --- |
| Hardware file save through a store: revisions, stale/lock refusal, `.bak`, merge, dry run, restore of a replaced file, single-key edits | `f5a61b8`, `07afbc6`, `014fa22`, `4d80a35` | Controls page saves with conflict handling and restore; `controls_errors/_warnings` in state | fork-only; no test line recorded |
| Apply saves without restart (controls worker), never in a take | `dcf09ee` | Edit hardware conf, drivers restart on their own after the take | fork-only |
| Output test (tally LED / trigger pulse) | `dcf09ee` (T42) | One blink or pulse from the UI | fork-only |
| Write-buffer mode `frames`/`ram`, buffer status, safety stop | `d44b177` | Switch from WebUI and touch buttons, effect next take | fork-only; Pi only (`00f2327` line: "built 2026-11-04") |
| `frames_per_folder` (part folders) and clip merge worker | `d7dd337`, `ba0658d` | Split takes into `part_NNN/`, auto-flatten when idle | fork-only; on GitHub 2026-11-08, no test recorded beyond host tests |
| Storage pre-roll (auto on start/insert/format, manual command, `record_stop` ends it) | `d44b177` | Warms the card before a take; switch `[media] preroll` | fork-only |
| Media state in socket state | `70e8376`, `438a342` | `media_state`, `media_alive` for touch UI; yank survival | fork-only; built, not run |
| Recording fault / dropped-frame count | `64bbbaa`, `438a342` | `recording_fault`, `recording_dropped_frames` in state and record replies | fork-only |
| Sensor binning in mode list and state | `4ab1057` | `binning`, `binning_source`, `sensor_binning*` | fork-only; list+state verified on Pi 2026-10-26 |
| ISO lock (`set_iso_auto enabled=false`) | `646a194` | Lock gain at the one in use | fork-only; tested 2026-10-28 |
| Log curve On/Off for DNG (`set_cdng_log`, preset key) | `d44b177` | Log in the files | fork-only |
| Media trim switch | `ce0bd90` | Performance card switch, env `APERTAR_MEDIA_TRIM=0` forces off | fork-only; Pi only |
| Preview temporal denoise (TDN) switch | `e625c68` | Toggle, default off | fork-only; Pi only |
| Frame-rate phase lock | `80ddac1` | Switch, default off | fork-only; built 22:04 |
| FPS speed ramp (+ shutter/audio/after policy, stretched WAV) | `faa2958`, `ca7b7c2` | FPS change during cDNG/MLV take | fork-only; tested 2026-10-28 |
| Clip name templates | `014a2bf` | Composable clip names, preview command | fork-only |
| Conform FPS (timeline rate) | `d7ff071` | Project rate, default 25 | fork-only; tested 2026-10-28 |
| UI timecode vs file timecode | `909aaa5` | `set_timecode_mode target=` | fork-only; Pi only, built, not tested |
| Recording frame, frame buffer bar, red timecode, audio outline toggles | `f4fb084`, `92d0970` | Four UI switches | fork-only; tested by Patrik 2026-10-28 |
| Value lists / free stepping / flicker-free angles | `b0e90ad` (T33) | Lists for iso, shutter angle, fps, wb | fork-only; tested 2026-10-28 |
| Mode ladder (FPS picks sensor mode) | `0041ba0`, `cdf83cd` (T34) | Ladder commands; presets checked against ladder | fork-only; tested 2026-10-28 |
| Presets carry operating-mode switches | `8e8ea2e` + above | Presets set Clear HDR, phase lock, ramp, etc. | fork-only; tested 2026-10-28 |
| Boot config (config.txt) read/write | `2955ef8` | Boot config card in System pane | fork-only |

## 3. Socket commands in this unit

New (handler in `handleCommand`, `@cinemate-port`):

| Command | Port line | Params | Notes |
| --- | --- | --- | --- |
| `test_output` | 12746 | `which=recording_indicator\|trigger_output` | refused during `recordingGateActive()`; calls `pulseCapture()` / `testPulse()` |
| `set_controls` | 12766 | `base`, `text` or `restore=true` or `set.<sec>.<key>` / `unset.*`; `dry_run`, `force`, `confirm_merge`, `by` | writes via `hardware::configStore()`; errors use `errorReplyBody` with `code`, `revision`, `issues`, `new_errors`, `conflicts` |
| `set_buffer_mode` | 12829 | `value=frames\|ram`, `base`, `by` | writes `[storage] buffer` via store, `flags.trusted=true`, allowed while recording |
| `set_frames_per_folder` | 12857 | `value` 0 or 100..100000 | writes `[storage] frames_per_folder` |
| `set_clip_merge` | 12857 | `enabled=true\|false\|1\|0` | writes `[storage] clip_merge`; calls `clipMerge("switch")` |
| `set_storage_preroll` | 12900 | `value=on\|off` (+ true/false/1/0) | writes `[media] preroll` |
| `storage_preroll` | 14597 | `seconds` 1..10 | manual pre-roll via `storagePrerollGuard` + `requestStoragePreroll` |
| `set_cdng_log` | 13078 | `value` off/on | |
| `set_media_trim` | 13194 | `enabled` | also stores `mediaTrimSetting_` atomic |
| `set_preview_tdn` | 13205 | `enabled` | |
| `set_fps_phase_lock` | 13214 | `enabled` | |
| `set_fps_speed_ramp` | 13223 | `enabled`, `shutter=angle\|exposure`, `audio=real\|stretch`, `after=stay\|return` | |
| `set_clip_name_template` | 13241 | `value` | reply adds `corrected`, `example` |
| `preview_clip_name` | 13258 | `value` (optional) | reply `example`, `template`, `corrected` |
| `set_conform_fps` | 13270 | `value` | |
| `get_mode_ladder` | 14087 | none | |
| `set_mode_ladder` | 14090 | `resolutions`, `enabled`, `ramp_ready`, `dry_run` | |
| `set_value_steps` | 14107 | `name=iso\|shutter_angle\|fps\|wb`, `values`, `free`, `increment`, `flicker_free`, `mains_hz` | writes UI.conf via `updateSharedUiGeneralSettings` |
| `get_boot_config` | 14587 | none | free functions `bootConfigGet/Set` defined at 3766/3775 |
| `set_boot_config` | 14590 | `cam0_sensor`, `cam1_sensor`, `*_link_frequency`, toggles, `rp1`, `display`, `text`, `revision`, `dry_run`, `confirm_display` | |
| `set_recording_frame_enabled`, `set_frame_buffer_bar_enabled`, `set_recording_red_timecode_enabled`, `set_audio_recorded_outline_enabled` | 13505-13512 | `value` | via existing `handleUiToggle` |

Changed existing commands:

| Command | Change |
| --- | --- |
| `list_sensor_modes` | +`binning`, `binning_source` per mode |
| `get_state` | +`recording_fault`, `media_state` (emitted twice, port lines 12948 and 12962), `recording_dropped_frames`, `controls_errors`, `controls_warnings`, `sensor_binning`, `sensor_binning_source`, `sensor_crop`, `sensor_mono`, `media_alive`, `clip_merge_*` members |
| `set_iso_auto` | `enabled=false` locks; default still auto |
| `set_timecode_mode` | `target=both\|ui\|files`; default `both` keeps old behaviour |
| `apply preset` (handler around 14250-14470; command name not in diff context) | 15 new preset keys, see section 4 |
| `format_media` | `FormatScope` RAII sets `storagePrerollFormatRunning_`, records `storagePrerollFormatDoneMs_`; ends with `requestStoragePreroll(Format)` |
| `record_start`, `record_stop` | reply +`recording_dropped_frames`; `record_stop` early-ends a running pre-roll (`storagePrerollStop_`) |
| `help` | list grows (also names `list_actions`, `controls_history`, `controls_last_input`, `scan_i2c`, handled earlier in the file at 12420-12540, not in this slice) |
| `publishEvent` | broadcast list +`recording`, `media`, `buffer`, `controls` events |

Preset keys added (apply-preset handler): `cameraCdngLog`, `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter`, `cameraFpsSpeedRampAudio`, `cameraFpsSpeedRampAfter`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraConformFps`, `cameraClearHdr`, `cameraHdrThresholdHigh`, `cameraHdrThresholdLow`, `cameraHdrBlend`, `cameraHdrGainAdder`; UI keys `recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`.

## 4. State fields, events, config, env, files, UI

| Kind | Item | Where in slice |
| --- | --- | --- |
| state | `recording_fault`, `recording_dropped_frames`, `media_state`, `media_alive`, `controls_errors`, `controls_warnings`, `sensor_binning`, `sensor_binning_source`, `sensor_crop`, `sensor_mono`, `clip_merge_*` (via `clipMergeStateJson`), `buffer_setting`, `buffer_note`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, `storage_preroll_*` (via `bufferSettingMembers`, defined 252) | get_state, set_buffer_mode replies |
| reply fields | `revision`, `written`, `merged`, `needs_review`, `diff`, `errors`, `issues`, `apply` (`now`/`after_take`/`next_take`), `text`, `storage_preroll_started`, `storage_preroll_stopped`, `corrected`, `example` | set_* replies |
| events | `recording`, `media`, `buffer`, `controls` added to the all-clients broadcast set | publishEvent |
| config keys | `apertar-hardware.conf` `[storage] buffer`, `frames_per_folder`, `clip_merge`; `[media] preroll`; UI.conf `isoSteps`, `isoFree`, `isoFreeIncrement`, `shutterAngleSteps`, `shutterAngleFree`, `shutterAngleFreeIncrement`, `fpsSteps`, `fpsFree`, `fpsFreeIncrement`, `wbSteps`, `wbFree`, `wbFreeIncrement`, `flickerFreeShutterAngles`, `mainsHz`, `recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`; `mode_ladder.conf` (CC:408-414, in `~/.config/apertar-core/`); camera_settings key `preview_tdn` (CC:887) | 
| env vars (named in or behind this slice) | `APERTAR_MEDIA_TRIM`, `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_BUFFER_STOP_PERCENT`, `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_RAM_FLOOR_MB`, `_RAM_MAX_FRACTION` | defined in headers, not in this slice |
| files on disk | `<file>.bak` (store backup), `config.txt.apertar.bak` (boot config helper), `fps-ramp.txt` in clip folder, `<clip>_stretched.wav`, `part_NNN/` folders, `.parts` marker | behind commands |
| HTTP routes | none added inside this slice. Same commits add `/api/buffer`, `/api/boot-config`, `/api/boot-config/parse`, `/api/media/clip`, `/frame`, `/file` elsewhere in the file | not scope |
| UI elements | none in this file (WebUI/QML are other units); commands exist for: Controls page, Performance card, Boot config card, Timecode card, value lists, ladder, clip name | |

## 5. ORIGINAL code modified

| Region | Where (`@upstream-1.6.0` line -> port) | Change | Kind |
| --- | --- | --- | --- |
| `list_sensor_modes` loop | -> 12727 | 2 fields appended | extended-in-place |
| `help` command string | upstream ~9091+ -> 12929 | one literal replaced by a longer one (~30 names added) | rewritten (literal) |
| `get_state` body | -> 12945+ | 12 `<<` lines inserted, `mediaSnapshot()` called twice, `media_state` key duplicated | extended-in-place |
| `set_iso_auto` | -> 12986-13015 | `setIsoAuto()` -> `setIsoAuto(bool)`; default arg semantics changed in CC | extended-in-place |
| `set_timecode_mode` | -> 13279 | `target` branch, UI write conditional | extended-in-place; `both` default keeps behaviour |
| `handleUiToggle` chain | -> 13505 | 4 lines added | extended-in-place |
| apply-preset handler | -> 14266-14550 | 15 keys, 4 `addBoolUpdate`, `timecodeMode` guarded, ladder check call | extended-in-place; `timecodeMode` now conditional on `cameraTimecodeMode` (behaviour-changed for new presets, same for old) |
| `format_media` | -> 14620 | RAII flag struct, post-format `requestStoragePreroll` | extended-in-place |
| `record_start` / `record_stop` replies | -> 14751, 14823 | +`recording_dropped_frames`; `record_stop` first branch checks pre-roll | extended-in-place; `record_stop` behaviour-changed while a pre-roll runs |
| `publishEvent` | -> 14875 | 4 event-name tests | extended-in-place |

## 6. New abstractions seen from this slice

| Name | Files | Purpose | Upstream equivalent |
| --- | --- | --- | --- |
| `hardware::HardwareConfigStore` (`configStore()`), `StoreFlags`, `StoreResult`, `ReplacedInfo` | `src/hardware/HardwareConfigStore.{hpp,cpp}` | revisioned, backed-up, locked write of `apertar-hardware.conf` with diff/merge/restore | none: upstream WebUI/Python saves the file directly (`WCP` / `core.py`, candidate paths at `ApertarCoreApp.cpp:3397-3410, 4248-4258` upstream); no C++ writer |
| `hwconf::` namespace (`Edit`, `parseEdits`, `Issue`, `Conflict`, `Facts`, `validate`) | `src/hardware/HardwareConfigText.hpp` (1141 lines) | parse, validate, edit the hardware file | none upstream (each hardware class parses its own section) |
| Controls worker thread `controlsThread_` + `wakeControlsWorker`, `applyHardwareText`, `controlsErrors_/_Warnings_` | `ApertarCoreApp.{hpp,cpp}` (cpp 12228-12330) | restart only changed driver groups after a save, poll every 2 s | none: upstream reads sections at start only |
| `bufferbudget::` namespace | `src/util/BufferBudget.hpp` (382) | RAM pool sizing from `/proc/meminfo`, safety stop, setting snapshot; worker `bufferEventThread_`, `bufferSafetyStopThread_` | none (fixed queue upstream) |
| `framepath::` | `src/cdng/FramePath.hpp` | part-folder layout | none |
| Clip merge worker `clipMergeThread_`, `ClipMerge.hpp`, `clipMerge()`, `waitForClipMerge` | `src/cdng/ClipMerge.hpp` | flatten split clips when idle | none |
| `storagepreroll::` + `storagePrerollThread_`, `requestStoragePreroll`, `storagePrerollGuard` | `src/util/StoragePreroll.hpp` (273) | pre-roll the card | none |
| Media watcher/probe: `MediaSnapshot`, `mediaWatcherThread_`, `MediaFault/Intent/Probe/Profile/Tune.hpp` | `src/util/Media*.hpp` | media state, yank survival, tuning | none; upstream has `mediaSpeedThread_` only |
| Media trim worker `mediaTrimThread_`, helper `scripts/apertar-media-trim` (+ `apertar-media-tune`, `apertar-tune`) | `scripts/` | fstrim-style helper via sudo | none; upstream has no privileged helpers in `scripts/` beyond start script (verify before stating) |
| `apertar::clipname::parse` | `src/util/ClipName.hpp` (296) | template parse/normalise | none |
| `ModeLadder.hpp`, `camera_.modeLadderJson/setModeLadder/applyLadderToPreset`, `mode_ladder.conf` | `src/camera/ModeLadder.hpp` (344) | FPS picks sensor mode | none; upstream picks mode only by `set_resolution` |
| `bootconf::` + `bootConfigGet/Set` free functions, helper `scripts/apertar-boot-config` | `src/hardware/BootConfigText.hpp` (1355), `scripts/apertar-boot-config` | edit `/boot/firmware/config.txt` through `sudo -n /usr/local/libexec/apertar-boot-config` | none upstream (upstream has `set_fan_mode` / `applyFanMode`) |
| `errorReplyBody`, `controlsIssuesJson`, `controlsConflictsJson` | `ApertarCoreApp.cpp:173, 4980, 4997` | error replies with a structured body | upstream: `errorReply(id,msg)` only (`:120`); `okReply` flat. Port breaks "flat scalar JSON": `issues`, `conflicts` are arrays/objects |
| `FormatScope` local RAII struct | in `format_media` handler | guard flag | none |
| `hardware::ActionCatalog.hpp` | `src/hardware/ActionCatalog.hpp` | single action vocabulary behind `list_actions` | upstream: `normalizeSingleAction` copies (per `916c1dd` log row) |

## 7. Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| `help` still lists every command but gets the pre-roll/ladder names; nothing removed | 12929 | none |
| fps limit table replaced by sensor probe (`APERTAR_FPS_LIMIT=table` restores) | in `d44b177`; effect visible via `set_fps` limits, not this slice | upstream cap 30 fps for 4K SDR lifted; narrowed only by env |
| `record_stop` can end a pre-roll instead of a take | 14847 | a stop request during pre-roll does not reach `camera_.stopRecording()` |
| Read-only hardware commands run before `commandMutex_` (`f5a61b8`) | handleCommand head (outside slice) | `get_controls` etc. bypass the one-mutex rule of upstream |
| `set_timecode_mode` writes UI.conf only when target != files | 13290 | with `target=files` UI.conf timecode is no longer set (default unchanged) |
| Old presets: `timecodeMode` only sets file timecode if `cameraTimecodeMode` absent | 14430 | same result for old presets, divergent for new |

## 8. Board assumptions (in or behind this slice)

| Assumption | Where | Confidence |
| --- | --- | --- |
| Pi 5 / RP1: `rp1` clock overlay, `board.family == "pi5"`, `[pi5]`/`[pi4]`/`[all]` config.txt sections | `BootConfigText.hpp:18, 232, 1023`; `scripts/apertar-boot-config` | confirmed |
| `/boot/firmware/config.txt`, `/boot/firmware/overlays/*.dtbo` (Bookworm layout) | `BootConfigText.hpp:621, 854`; helper `DEST=` | confirmed |
| Display overlay warning: "GPIO 0-27 (I2C bus 1 included) belong to the panel" | `ApertarCoreApp.cpp` set_boot_config helper, near 3830-3850 (unconfirmed line) | confirmed |
| I2C buses from `/dev/i2c-N`; `known=false` when none | `hardwareConfigFacts` 4965 | confirmed |
| `/proc/meminfo` MemAvailable for RAM write buffer; fraction/floor/cap | `BufferBudget.hpp:6, 35, 83` | confirmed |
| `/usr/local/libexec/apertar-boot-config` with sudoers entry, user `pi` | `apertar-boot-config` header | confirmed |
| Fan: `config.txt` carries fan mode ("config.txt changed since the card loaded it (the fan mode...)") | `ApertarCoreApp.cpp:3790` | confirmed |
| TDN switch: libcamera RPi tuning file `rpi.denoise` blocks | `CameraController.cpp:7307` | confirmed |
| Four cores / gpiochip numbering | not in this slice | n/a; see GPIO units |
| Sensor family dependence of ladder / Clear HDR (IMX585, IMX283 mode tables) | `ModeLadder.hpp`, `Imx585Modes.hpp`, `Imx283Modes.hpp` | probable (behind `set_mode_ladder`, `cameraClearHdr`) |

## 9. Observations worth stage 2 (no judgement)

- Each new `[storage]`/`[media]` setter (`set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll`) repeats a 15-line block (store edit, error body, error counters, wake worker, refresh).
- `handleCommand` already has a bool parse in two spellings (`"true"||"1"` inline, `parseBooleanToken`, `parseUiSettingsBool`, local `boolField`); the slice adds more of each.
- `get_state` writes key `media_state` twice (port 12948 and 12962).
- `set_value_steps` carries range tables as a static struct inside the command branch.
- Commit messages carry Patrik's tutorial codes in comments (`T33`, `T34`, `T39`, `T42`, `Q10`) at 12746, 12790, 14107, 14090, 14528.
