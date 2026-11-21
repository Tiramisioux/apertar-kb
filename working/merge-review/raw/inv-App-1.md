# Inventory App-1: `src/ApertarCoreApp.cpp`, port lines 1-4401

Stage 1 of 3. What the port added or changed in this slice. No judgement.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Slice | `/home/user/build/review/diffs/App.part01.diff`, 1408 lines, 20 hunks. Equal to the first 1408 lines of `git diff --minimal -U10 origin/main cinemate-port -- src/ApertarCoreApp.cpp` (checked with `diff`) |
| Size | +742 / -78 lines, of the file's +4250 / -259 |
| Refs | `@port` = `cinemate-port` `01f170c`. `@main` = `origin/main` `f60e301`. `@up` = `upstream-1.6.0` `35dbe67` |
| Paths | `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`. Port: `/home/user/Apertar-Core`. Upstream: `/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream` |
| Line map | `@up` line = `@main` line up to main 200; main - 5 for main 206..881; main - 9 from main 893 on (main inserts 201-205, 882-883, 891-892; `diff` of the first 4000 lines) |
| Labels | Every row is **confirmed** (read in code at the ref given) unless it says **probable** or **unconfirmed** |
| Commits | `git blame -s cinemate-port` per added range. Tests = the commit's `Tested:` line and the fork-log row. Both are claims, not proof |
| What the slice holds | Includes, anonymous-namespace helpers: reply builders, state JSON fragments, hardware step lists, UI.conf snapshot, config.txt (fan mode, Boot Config), media mount and eject |

## 1. The 20 hunks

| # | `@port` lines | `@main` lines | `@up` lines | What | Commits (blame) |
| --- | --- | --- | --- | --- | --- |
| H1 | 1-37 | 1-26 | 1-26 | 10 project includes, `<cerrno>` | `0b1632f` `438a342` `d44b177` `014a2bf` `916c1dd` `07afbc6` `166cc4d` `0a98868` `f5a61b8` `2955ef8` |
| H2 | 45-116 | 34-73 | 34-73 | 4 system includes; a second include block (`<csignal>`, `<functional>`, 5 project headers); `webPreviewRecordingFps()` | `ba0658d` `d44b177` `a37a902` `f91fafa` `d7dd337` `1af26c8` `fb557e9` `766aba8` |
| H3 | 163-195 | 120-139 | 120-139 | `errorReplyBody()` | `f5a61b8` |
| H4 | 213-403 | 157-229 | 157-224 | `sensorBinningBody`, buffer and storage state fragments, `refreshBufferRequest`, `abortSafetyStopFlushForRecord`, 27 new members in `settingsBody` plus one appended call | `4ab1057` `e16033e` `d44b177` `c5db8b2` `d7dd337` `ba0658d` `d7ff071` `646a194` `6d217c7` `97adea0` `0041ba0` `cdf83cd` `8175273` `80ddac1` `e625c68` `faa2958` `ca7b7c2` `014a2bf` |
| H5 | 475-507 | 301-320 | 296-315 | `jsonNumberArray()` | `b0e90ad` |
| H6 | 1262-1332 | 1075-1094 | 1066-1085 | `selectableValueSteps`, `flickerFreeShutterAngles`, `freeStepValue` | `b0e90ad` |
| H7 | 1376-1442 | 1138-1201 | 1129-1192 | IMX585 25 fps line in `maximumPcfFpsForSettings`; `builtInFpsSteps`; `availablePcfFpsOptions` rewritten; `availablePcfResolutionOptions` gets `settings` | `b5847c7` `b0e90ad` `caa0153` `f95567d` |
| H8 | 1483-1524 | 1242-1261 | 1233-1252 | IMX283 resolution list | `f95567d` |
| H9 | 1541-1603 | 1278-1310 | 1269-1301 | `builtInIsoSteps`, `builtInShutterAngleSteps`, `builtInWhiteBalanceSteps`, new `pcfIsoOptions`, `pcfShutterAngleOptions` | `b0e90ad` |
| H10 | 1606-1628 | 1313-1339 | 1304-1330 | `pcfWhiteBalanceOptions(steps)` | `b0e90ad` |
| H11 | 1630-1664 | 1341-1388 | 1332-1379 | `prefixViews`; `hardwareActionSuffix` and `parseHardwareActionNumber` become one-line calls into `ActionCatalog.hpp` | `916c1dd` |
| H12 | 1893-1917 | 1617-1636 | 1608-1627 | 4 recording-indicator fields in `SharedUiSettingsSnapshot` | `f4fb084` `d44b177` `92d0970` |
| H13 | 1919-1992 | 1638-1659 | 1629-1650 | 14 value-list fields; `parseValueStepsList`, `valueStepsJson` | `b0e90ad` |
| H14 | 2084-2111 | 1751-1770 | 1742-1761 | 4 UI.conf keys read | `f4fb084` `d44b177` `92d0970` |
| H15 | 2149-2201 | 1808-1827 | 1799-1818 | 14 UI.conf keys read | `b0e90ad` |
| H16 | 3492-3850 | 3118-3196 | 3109-3187 | Boot Config: `writeBootConfigText`, `bootConfigGet`, `bootConfigSet` and helpers; `currentFanMode` and `applyFanMode` changed | `2955ef8` `3b87d99` |
| H17 | 4198-4222 | 3544-3568 | 3535-3559 | Mount options in the embedded Python re-insert watcher | `04bac89` (diff), `e0fa852` (message) |
| H18 | 4269-4296 | 3615-3639 | 3606-3630 | `noatime` in `mountDeviceAtMediaPath` | `26da30e` |
| H19 | 4345-4365 | 3688-3707 | 3679-3698 | `clearEjectIntent` after a mount | `438a342` |
| H20 | 4376-4401 | 3718-3737 | 3709-3728 | `writeEjectIntent` before an eject | `438a342` |

Lines by commit in this slice: `2955ef8` 292, `b0e90ad` 197, `d44b177` 65, `f95567d` 25, `c5db8b2` 16, `3b87d99` 15, `f5a61b8` 14, `fb557e9` 14, `4ab1057` 10, `ba0658d` 9, `438a342` 8, `916c1dd` 8, `d7dd337` 7, `f4fb084` 7, `e16033e` 6, others 1-5 each.

## 2. Features touching this slice

"Slice part" = what of the feature lives in lines 1-4401. Handlers named with a line are outside the slice.

| # | Feature | Operator gets | Slice part (`App:` `@port`) | Commits | Relation to upstream |
| --- | --- | --- | --- | --- | --- |
| F1 | Boot Config card | Choose sensor per CSI port, link frequency, I2C / I2S / SPI / audio, RP1 clock and DPI display in `config.txt` from the WebUI, or edit the file as text, with a review before saving | 3502-3610, 3651-3841 | `f19b245` `dda1713` `2955ef8` `8a56545` `afa00e8` `496817f` `3b87d99` `b3e7f52` `2a4266e`, merge `4581a69` | entirely new area; replaces the write half of upstream `applyFanMode` |
| F2 | Fan mode through the one config.txt writer | Fan mode still works; each change now leaves `config.txt.apertar.bak` | 3612-3649 | `2955ef8` | replaces upstream code |
| F3 | Value lists, free stepping, flicker-free shutter angles | Own ISO / shutter angle / FPS / WB lists for dials, buttons and pickers; step by a fixed increment instead; shutter angles that do not flicker on 50 or 60 Hz mains | 485-496, 1272-1321, 1398-1416, 1551-1592, 1616-1619, 1929-1981, 2159-2191 | `b0e90ad` `ff33d2d` `c232196` `f81108d` `b2c15af` `6777ebe` `60645d4` `caa0153` | extends upstream functions in place |
| F4 | Write-buffer level, RAM write buffer, safety stop | A buffer bar while recording; a RAM-sized write queue; the take ends cleanly at a fill threshold; record during the flush starts at once | 235-311, 393 | `d44b177` `fb5801c` `c5db8b2` | entirely new area |
| F5 | Storage pre-roll | A short throwaway take warms the card when Core starts or a card is inserted; a button runs it by hand | 260-264, 277-279 | `d44b177` | entirely new area |
| F6 | Split long takes into part folders | Long takes write `part_NNN/` folders so exFAT creates stay fast | 265-266, 280-283; includes 77 | `d7dd337` | entirely new area |
| F7 | Merge worker for split clips | Split clips are flattened back while the camera idles | 267-268, 284-285; includes 55, 56, 58, 76 | `ba0658d` `68516f1` `01f170c` | entirely new area |
| F8 | Sensor binning in the state | Socket clients see the mode's binning factor and crop | 223-231 | `4ab1057` | extends an upstream function in place (`get_state`) |
| F9 | Mode ladder | FPS picks the sensor mode between takes; the state says which | 233, 326-334 | `0041ba0` `cdf83cd` `e16033e` `62c1711` `d44b177` | extends an upstream function in place (`settingsBody`) |
| F10 | Clear HDR holds ISO and WB; `iso_actual`, `iso_max`, `fps_max` | UIs show the gain in use and the mode's ceilings; auto ISO / WB return after Clear HDR | 323-325, 335, 347 | `8175273` `646a194` `6d217c7` `97adea0` `bcedbe5` | extends an upstream function in place |
| F11 | Log encoding in cDNG | The state says whether Log is set, available and applied | 356-359 | `d44b177` | extends an upstream function in place |
| F12 | Speed ramp | FPS changes inside a take; the state carries the switch and its policies | 369-372 | `faa2958` `ca7b7c2` `d44b177` | extends an upstream function in place |
| F13 | Frame-rate phase lock | State field for the switch | 367 | `80ddac1` | extends an upstream function in place |
| F14 | Preview temporal denoise switch | State field for the switch | 368 | `e625c68` | extends an upstream function in place |
| F15 | Conform FPS (project rate) | State field; set over the socket only | 320 | `d7ff071` | extends an upstream function in place |
| F16 | Clip names from a template | State carries the template and an example name | 373-374; include 5 | `014a2bf` | extends an upstream function in place |
| F17 | Web preview rate cap during a raw take | An env var lowers or pauses the browser preview while recording | 89-106 | `fb557e9` `766aba8` | adds a parallel path beside upstream code |
| F18 | Error replies with extra members | The WebUI gets a `code`, a `revision` or an issue list with an error | 173-184 | `f5a61b8` | adds a parallel path beside upstream `errorReply` |
| F19 | 4K Clear HDR 16-bit stops at 25 fps on dials and buttons | The fallback FPS table for hardware steps returns 25 there | 1386, 1389 | `b5847c7` | extends an upstream function in place |
| F20 | IMX283 on the resolution step | The resolution button cycles the IMX283 sizes for the running bit depth and format | 1430-1432, 1493-1513 | `f95567d` | extends an upstream function in place |
| F21 | One action vocabulary | Action names parse the same in every driver; `list_actions` | 1640-1655; include 9 | `916c1dd` | replaces upstream code (bodies moved to a header) |
| F22 | Recording indicator switches | Red frame, buffer bar, red timecode, audio outline can be switched | 1903-1907, 2094-2101 | `f4fb084` `d44b177` `92d0970` | extends upstream functions in place |
| F23 | `noatime` mounts | Recording drives mount with `noatime` (and `umask=0002` in the re-insert watcher) | 4208, 4210, 4212, 4279-4286 | `26da30e`, `04bac89` / `e0fa852` | extends upstream functions in place |
| F24 | Eject intent flag | A flag file tells an automounter that an unmount was deliberate | 4355, 4386-4391; include 3 | `438a342` | extends upstream functions in place |
| F25 | Controls page backend (include lines only) | Code is in later slices | includes 9-13 | `916c1dd` `07afbc6` `166cc4d` `0a98868` `f5a61b8` | entirely new area |
| F26 | Clip browser and playback backend (include lines only) | Code is in later slices | includes 72-79 | `f91fafa` `1af26c8` `a37a902` | entirely new area |
| F27 | CFexpress card-pull detection (include line only) | Code is in later slices | include 2 | `0b1632f` | entirely new area |

### 2.1 What the commits and the fork-log say was tested

| Feature | Commit `Tested:` line | Fork-log row |
| --- | --- | --- |
| F1, F2 | `f19b245`: "Host test with the dev Pi's file". `dda1713`: "Host test on a scratch copy". `2955ef8`: no `Tested:` line. `3b87d99`: "desk only (boot_config_test 73 checks, helper test, node --check)" | Row `d44b177`: host tests, Pi build, `--simulate` serving the WebUI; "Not yet run on the camera". UI `41ff827` (fan mode through `set_fan_mode`): "builds on the Pi, not tried by hand" |
| F3 | `b0e90ad`: "desk only (built on the Pi next)" | "tested 2026-10-28 (Patrik)" |
| F4 | `d44b177`: host tests; "Not run yet: the ram queue, the safety stop, the buttons, the Controls page, the fps ceilings". `c5db8b2`: no `Tested:` line | "Not yet run on the camera" (2026-11-01) |
| F5 | `d44b177`: "Not compiled or run yet: the pre-roll and the Clear HDR override" | same row |
| F6 | `d7dd337`: desk (`tools/frame_path_test.cpp`, `tools/storage_buffer_conf_test.cpp`); Pi build rc 0 | on GitHub; the camera runs this build since 2026-11-08 13:00 with `frames_per_folder=0` |
| F7 | `ba0658d`: desk; "pi build rc 0, not yet run on the camera". `68516f1`: "pi verify step 6 again, both clips flat". `01f170c`: "pi restart with clip_merge=off, no merge line" | on GitHub |
| F8 | `4ab1057`: "desk only (not built)" | "built and running 21:39, list_sensor_modes + get_state verified" |
| F9 | `0041ba0`: "desk only (ModeLadder host test 28/28)". `e16033e`, `cdf83cd`: desk only | `0041ba0` "tested 2026-10-28 (socket, two takes, presets)"; `e16033e` "built, not tested" |
| F10 | `8175273`: Pi preview. `646a194`: Pi preview. `6d217c7`, `97adea0`, `bcedbe5`: desk only | tested 2026-10-28 (rows `8175273`, `646a194`, `6d217c7`, `bcedbe5`) |
| F11 | `d44b177`: Log 16 to 12 run on the Pi on an earlier build | same row |
| F12 | `faa2958`: Pi, C0030-C0032. `ca7b7c2`: desk only | tested 2026-10-28 |
| F13 | `80ddac1`: "desk only (servo passes phase_lock_sim.cpp on the Mac; not built)" | "built 22:04 with 8f7dc39" |
| F14 | `e625c68`: "desk only (not built: no libcamera on the Mac)"; strip test passes | "Pi only"; the source commit `6bd002b` "built 2026-11-04" |
| F15 | `d7ff071`: "desk only (built on the Pi next)" | "tested 2026-10-28 (hardware-log)" |
| F16 | `014a2bf`: no `Tested:` line | row `d44b177` names `tools/clip_name_test.cpp`; UI card `606f137` "untested by hand" |
| F17 | `fb557e9`: syntax-check; "Not run on the Pi" | in the `dd00206` merge; "Not yet run on the camera" |
| F18 | `f5a61b8`: "desk only (Pi build and a read of the live file not yet run)" | fork-only, no test note |
| F19 | `b5847c7`: Pi, "Clear HDR 16-bit set_fps 30 -> 25, 24 accepted" | "tested 2026-10-28" |
| F20 | `f95567d`: "desk only (host tests, Pi -fsyntax-only, node --check)" | in the `a47dc28` merge; "Not yet run on the camera" |
| F21 | `916c1dd`: "desk only (host test 20 of 20 against this tree; Pi build not yet run)" | fork-only, no test note |
| F22 | `f4fb084`: "desk only (built on the Pi next)". `92d0970`: no `Tested:` line | `f4fb084` "tested 2026-10-28 (Patrik)" |
| F23 | `26da30e`: "pi build (see next run)". `e0fa852`: "syntax-checks on the host ... Not run on the Pi" | `26da30e` "built 23:04, not tested" |
| F24 | `438a342`: "desk only (not built yet)" | "built 22:27 with e8bb1b7" |

## 3. Interface items

### 3.1 Socket commands and HTTP routes

New in the port unless the Change column says "upstream". For reference: `set_fan_mode` is upstream (`App:10568 @up`); `list_sensor_modes` is in fork main (`App:9231 @main`).

| Item | Handler `@port` | Slice part | Change |
| --- | --- | --- | --- |
| `get_boot_config` | `App:14586` | `bootConfigGet` `App:3766` | new. Reply `boot_config{path, readable, revision, helper, backup_path, state, drm[], text}` |
| `set_boot_config` | `App:14589` | `bootConfigSet` `App:3775` | new. Fields `cam0_sensor`, `cam1_sensor`, `cam0_link_frequency`, `cam1_link_frequency`, `i2c`, `i2s`, `spi`, `audio`, `rp1`, `display`, `text`, `dry_run`, `confirm_display`, `revision`. Reply `changes[]`, `display_changed`, `text`, `state`, `written`, `dry_run`, `via`, `revision`, `reboot_required`, `drm[]`. Error `code`: `invalid`, `unreadable`, `old_page`, `stale`, `refused`, `confirm_display`, `permission`, `write_failed` |
| `GET /api/boot-config` | `App:9161` | `bootConfigGet` | new |
| `POST /api/boot-config` | `App:9170` | `bootConfigSet` | new. Header `X-Apertar-Revision`. Status 200 / 400 / 403 / 409 / 500 from `BootConfigReply.status`. The route calls `bootConfigSet` itself, not through `/api/command`; it takes `bootConfigMutex()`, not `commandMutex_` |
| `POST /api/boot-config/parse` | `App:9200` | `bootConfigFacts` `App:3653` | new. Reads an uploaded file, writes nothing |
| `set_fan_mode` | `App:14592` (same text as `@up 10568`) | `applyFanMode` `App:3620` | upstream command; behaviour changed: see section 4, row 17 |
| `set_value_steps` | `App:14110` | `parseValueStepsList` `App:1948`, `valueStepsJson` `App:1963` | new. `name=iso` or `shutter_angle` or `fps` or `wb`; `values`, `free`, `increment`, `flicker_free`, `mains_hz`. Reply `ui{...}` |
| `list_actions` | `App:12534` | `pcfIsoOptions`, `pcfShutterAngleOptions`, `pcfWhiteBalanceOptions`, `availablePcfFpsOptions`, `availablePcfResolutionOptions`, `jsonNumberArray` | new. `values{iso, shutter_angle, shutter_speed, wb, fps, resolution}` come from the slice's lists |
| `GET /api/buffer` | `App:8419` | `bufferMembers` `App:301` | new. Lock-free; polled at about 4 Hz by the WebUI |
| `set_buffer_mode` | `App:12829` | `refreshBufferRequest`, `bufferSettingMembers`, `errorReplyBody` | new |
| `set_frames_per_folder`, `set_clip_merge` | `App:12857-12858` | same three helpers | new |
| `set_storage_preroll` | `App:12900` | same three helpers | new |
| `storage_preroll` | `App:14603` | none | new (state fields only in the slice) |
| `set_controls`, `POST /api/config` | `App:12763`, `App:8620` | `errorReplyBody`, `refreshBufferRequest` | `set_controls` new; `/api/config` is upstream (`App:7175 @up`), its error replies now carry extra members |
| `record_start` | `App:12570`, `App:10119` | `abortSafetyStopFlushForRecord` `App:291` | upstream command; a call before the command lock (and before `hardwareActionMutex_`) aborts a safety-stop flush |
| `get_state` | `App:12932` | `sensorBinningBody`, `settingsBody` | upstream command; 3 + 27 + 14 new members from this slice |
| every command that replies `settingsBody` (48 call sites `@port`, 38 `@up`) | `App:12964-14544` | `settingsBody` `App:313` | upstream and new commands; the reply grows by 27 + 14 members |
| `eject_media`, `mount_media` | `App:14637`, `App:14644` | `ejectMediaAtPath`, `mountMediaDeviceAtPath` | upstream commands; flag file written or removed; `noatime` added |

### 3.2 State fields added in this slice

`settingsBody` (`App:313-395 @port`, `App:167-217 @up`). Upstream keeps the same field list in three places: `settingsBody`, `settingsEvent` (`CC:136 @up`) and `buildWebStateJson`. All 27 fields below are in all three at the port (`settingsEvent` `CC:163-246`, `buildWebStateJson` `App:9298-9720`; one `grep` per field). The 14 `bufferSettingMembers` are in `settingsBody` only, not in `settingsEvent`.

| Field | Line | Source | Commit | Feature | Readers found by `grep` (`WCP` hits / touch UI `src`+`qml` hits) |
| --- | --- | --- | --- | --- | --- |
| `conform_fps` | 320 | `settings.conformFps` | `d7ff071` | F15 | 0 / 0 (`WCP:19111` names only the preset key `cameraConformFps`) |
| `iso_actual` | 323 | `settings.isoMeasured` | `646a194` | F10 | 5 / 1 |
| `iso_max` | 324 | `settings.isoMax` | `6d217c7` | F10 | 6 / 2 |
| `fps_max` | 325 | `settings.fpsMax` | `97adea0` | F10 | 6 / 4 |
| `fps_take_max` | 326 | `settings.fpsTakeMax` | `0041ba0` | F9 | 3 / 0 |
| `ladder_active` | 327 | `settings.ladderActive` | `0041ba0` | F9 | 7 / 2 |
| `ladder_resolution` | 328 | `settings.ladderRung` | `cdf83cd` | F9 | 6 / 0 |
| `ladder_ramp_ready` | 329 | `settings.ladderRampReady` | `0041ba0` | F9 | 2 / 0 |
| `ladder_enabled` | 330 | `settings.ladderEnabled` | `e16033e` | F9 | 4 / 0 |
| `ladder_override` | 331 | `settings.ladderOverride` | `d44b177` | F9 | 0 / 0 |
| `ladder_count` | 332 | `settings.ladderCount` | `e16033e` | F9 | 3 / 0 |
| `ladder_text` | 333 | `settings.ladderText` | `e16033e` | F9 | 4 / 0 |
| `ladder_tops` (array of numbers) | 334 | `settings.ladderTops` | `e16033e` | F9 | 4 / 0 |
| `iso_auto_after_clear_hdr` | 335 | `settings.isoAutoAfterClearHdr` | `8175273` | F10 | 3 / 2 |
| `wb_auto_after_clear_hdr` | 347 | `settings.whiteBalanceAutoAfterClearHdr` | `8175273` | F10 | 3 / 2 |
| `cdng_log` | 356 | `toString(settings.cdngLog)` | `d44b177` | F11 | 6 / 3 |
| `cdng_log_bits` | 357 | `cdngLogBits(settings)` | `d44b177` | F11 | 4 / 3 |
| `cdng_log_available` | 358 | `cdngLogAvailable(...)` | `d44b177` | F11 | 4 / 3 |
| `cdng_log_applied` | 359 | `settings.cdngLogApplied` | `d44b177` | F11 | 4 / 4 |
| `fps_phase_lock` | 367 | `settings.fpsPhaseLock` | `80ddac1` | F13 | 2 / 0 |
| `preview_tdn` | 368 | `settings.previewTdn` | `e625c68` | F14 | 2 / 0 |
| `fps_speed_ramp` | 369 | `settings.fpsSpeedRamp` | `faa2958` | F12 | 9 / 3 |
| `fps_speed_ramp_keep_exposure` | 370 | `settings.fpsSpeedRampKeepExposure` | `faa2958` | F12 | 5 / 2 |
| `fps_speed_ramp_stretch_audio` | 371 | `settings.fpsSpeedRampStretchAudio` | `ca7b7c2` | F12 | 4 / 0 |
| `fps_speed_ramp_after` (`return` or `stay`) | 372 | `settings.fpsSpeedRampReturn` | `d44b177` | F12 | 4 / 0 |
| `clip_name_template` | 373 | `settings.clipNameTemplate` | `014a2bf` | F16 | 8 / 4 |
| `clip_name_example` | 374 | `settings.clipNameExample` | `014a2bf` | F16 | 3 / 3 |
| the 14 members of `bufferSettingMembers()` | 393 | see next table | `d44b177` | F4-F7 | see next table |

`bufferSettingMembers()` (`App:252-269`). In `settingsBody`, `GET /api/buffer`, the `buffer` event, the web state, and the replies of `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll`.

| Field | Line | Source | Commit | Readers (`WCP` / touch UI) |
| --- | --- | --- | --- | --- |
| `buffer_setting` | 256 | `bufferbudget::bufferSettingSnapshot().setting` | `d44b177` | 4 / 3 |
| `buffer_note` | 256 | `...snapshot.note` | `d44b177` | 3 / 3 |
| `buffer_safety_stop` | 257 | `bufferbudget::safetyStopState().active` | `d44b177` | 7 / 2 |
| `buffer_stop_percent` | 258 | `...stopPercent` | `d44b177` | 4 / 2 |
| `buffer_flush_discarded` | 259 | `...flushDiscarded` | `c5db8b2` | 2 / 0 |
| `storage_preroll_active` | 260 | `storagepreroll::prerollActive()` | `d44b177` | 12 / 3 |
| `storage_preroll_auto` | 261 | `prerollAutomatic()` | `d44b177` | 7 / 5 |
| `storage_preroll_auto_env` | 262 | `prerollAutomaticFromEnv()` | `d44b177` | 5 / 0 |
| `storage_preroll_fps` | 263 | `prerollFps()` | `d44b177` | 6 / 3 |
| `storage_preroll_last` | 264 | `prerollLast()` | `d44b177` | 3 / 3 |
| `frames_per_folder` | 265 | `bufferbudget::framesPerFolderRequest()` | `d7dd337` | 2 / 4 |
| `frames_per_folder_env` | 266 | `getenv("APERTAR_CDNG_FRAMES_PER_FOLDER")` | `d7dd337` | 1 / 0 |
| `clip_merge_enabled` | 267 | `bufferbudget::clipMergeRequest()` | `ba0658d` | 1 / 0 |
| `clip_merge_env_off` | 268 | `clipMergeEnvOff(getenv("APERTAR_CLIP_MERGE"))` | `ba0658d` | 1 / 0 |

`bufferMembers()` (`App:301-311`): `GET /api/buffer`, the `buffer` event, the web state.

| Field | Line | Readers (`WCP` / touch UI) |
| --- | --- | --- |
| `buffer_used` | 304 | 0 / 0 |
| `buffer_capacity` | 305 | 0 / 0 |
| `buffer_fill` (3 decimals, capped at 1) | 306 | 2 / 3 |
| `buffer_mode` | 307 | 6 / 3 |
| `buffer_unit` (`bytes` in `ram` mode, else `frames`) | 308 | 0 / 0 |

`sensorBinningBody()` (`App:224-231`): `get_state` (`App:12959`) and the web state (`App:9478`).

| Field | Readers (`WCP` / touch UI) |
| --- | --- |
| `sensor_binning`, `sensor_binning_source`, `sensor_crop` | 0 / 0 |

`valueStepsJson()` (`App:1963-1981`): web state `ui` object (`App:9694`) and the `set_value_steps` reply.

| Field | Readers (`WCP` / touch UI) |
| --- | --- |
| `iso_steps`, `shutter_angle_steps`, `fps_steps`, `wb_steps` (arrays of numbers) | 4, 2, 2, 2 / 0 |
| `iso_free`, `iso_free_increment`, `shutter_angle_free`, `shutter_angle_free_increment`, `fps_free`, `fps_free_increment`, `wb_free`, `wb_free_increment` | 1 each / 0 |
| `flicker_free_shutter_angles`, `mains_hz` | 6, 4 / 0 |

The touch UI reads the same lists straight from UI.conf (`Apertar-UI/src/SettingsBridge.cpp`, keys `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles`, `mainsHz`). It has no hit for `isoFree`: free stepping is used by Core's hardware inputs only.

Web state `ui` object, defined outside the slice (`App:9663-9666`), fed by the snapshot fields added here: `recording_frame_enabled`, `frame_buffer_bar_enabled`, `recording_red_timecode_enabled`, `audio_recorded_outline_enabled`.

Reader counts are `grep -c` on `WCP @port` and `git grep -c` on `Apertar-UI cinemate-port -- src qml`. A count is lines that contain the name, so a command name such as `set_buffer_mode` is counted too; 0 means no reader. Socket clients outside the two repos were not checked.

### 3.3 Events

| Event | Where | Change |
| --- | --- | --- |
| `{"event":"buffer", ...}` | built at `App:10839` from `bufferMembers` (`App:301`) | new. Carries the 5 + 14 members above plus `recording_dropped_frames` |

Upstream has 15 event names (`grep` on `App` and `CC @up`): `audio_level`, `camera_state`, `hardware_action`, `media_write_state`, `photo_capture`, `photo_write_error`, `prepare_recording`, `recording`, `recording_health`, `settings`, `standby`, `still_exposure`, `timelapse`, `timelapse_frame`, `timelapse_progress`. No `buffer`.

### 3.4 Config keys

`UI.conf [General]` (`~/.config/CinePi/UI.conf`, `sharedUiSettingsPath` `App:341 @up`). Upstream keeps monitoring aids and UI preferences here and already stores a list (`favoritesOrder`, `App:1807 @up`).

| Key | Default | Range | Parsed at `@port` | Commit |
| --- | --- | --- | --- | --- |
| `recordingFrameEnabled` | false | bool | `App:2094` | `f4fb084` |
| `frameBufferBarEnabled` | false | bool | `App:2096` | `d44b177` |
| `recordingRedTimecodeEnabled` | true | bool | `App:2098` | `f4fb084` |
| `audioRecordedOutlineEnabled` | true | bool | `App:2100` | `92d0970` |
| `isoSteps` | empty = built-in | 50..51200 | `App:2159` | `b0e90ad` |
| `shutterAngleSteps` | empty = built-in | 1..360 | `App:2161` | `b0e90ad` |
| `fpsSteps` | empty = built-in | 1..280 | `App:2163` | `b0e90ad` |
| `wbSteps` | empty = built-in | 1500..12000 | `App:2165` | `b0e90ad` |
| `isoFree`, `shutterAngleFree`, `fpsFree`, `wbFree` | false | bool | `App:2167-2174` | `b0e90ad` |
| `isoFreeIncrement` | 100 | 1..10000 | `App:2175-2186` | `b0e90ad` |
| `shutterAngleFreeIncrement` | 1 | 0.1..180 | `App:2175-2186` | `b0e90ad` |
| `fpsFreeIncrement` | 1 | 0.001..100 | `App:2175-2186` | `b0e90ad` |
| `wbFreeIncrement` | 100 | 10..5000 | `App:2175-2186` | `b0e90ad` |
| `flickerFreeShutterAngles` | false | bool | `App:2187` | `b0e90ad` |
| `mainsHz` | 50 | 50 or 60 | `App:2189` | `b0e90ad` |

`apertar-hardware.conf`, read in this slice through `hardware::configStore().currentText()` (`App:276-281`). The parsers are in the headers, not in a hardware class.

| Section | Key | Parser | Upstream has the section |
| --- | --- | --- | --- |
| `[storage]` | `buffer` (`frames` or `ram`), `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent` | `bufferbudget::parseBufferConf` (`src/util/BufferBudget.hpp:141`) | yes, with `mount_path`, `pcie_controller` only (`App:4308-4310 @up`) |
| `[storage]` | `frames_per_folder` (0 or 100..100000) | same | yes |
| `[storage]` | `clip_merge` (`on` or `off`) | same | yes |
| `[media]` | `preroll` (`on` or `off`), `preroll_seconds` (1..10) | `storagepreroll::parsePrerollConf` (`src/util/StoragePreroll.hpp:47`) | no `[media]` section upstream |

`/boot/firmware/config.txt`: the lines Boot Config sets (`src/hardware/BootConfigText.hpp:15-20`): `dtoverlay=<sensor>[,cam0][,mono][,link-frequency=<Hz>]`, `dtparam=i2c_arm=on`, `dtparam=i2s=on`, `dtparam=spi=on`, `dtparam=audio=on`, `dtoverlay=rp1-clk-333mhz`, the DPI display overlays. Upstream writes only the fan block (`fanModeBlock` `App:3042 @up`).

### 3.5 Environment variables read in this slice

The upstream tree has 52 distinct `APERTAR_*` names (some are build macros); 26 are read with `getenv` directly in `src @up`. `App @up` reads one, `APERTAR_HARDWARE_CONFIG` (`App:4254 @up`). None of the names below exist upstream.

| Variable | Line `@port` | Effect | Commit |
| --- | --- | --- | --- |
| `APERTAR_WEB_PREVIEW_RECORDING_FPS` | `App:96` | Web preview rate while a raw take runs. 0..30, below 0.5 = no frames. Read once (static) | `fb557e9` |
| `APERTAR_CDNG_FRAMES_PER_FOLDER` | `App:266`, `App:283` | Wins over `[storage] frames_per_folder` | `d7dd337` |
| `APERTAR_CLIP_MERGE` | `App:268`, `App:285` | `0` forces the merge worker off | `ba0658d` |
| `APERTAR_CDNG_BUFFER` | `App:276` | Wins over `[storage] buffer` | `d44b177` |
| `APERTAR_STORAGE_PREROLL` | `App:278` | Wins over `[media] preroll` | `d44b177` |
| `APERTAR_BOOT_CONFIG` | `App:3507` | Path of a config.txt copy (dev machine, test). The root helper never writes it | `2955ef8` |
| `APERTAR_MEDIA_RUN_DIR` | `src/util/MediaIntent.hpp:23` (included at `App:3`) | Directory of the eject flag, default `/run/apertar-media` | `438a342` |

### 3.6 Files on disk

| File | Access | Line `@port` | New |
| --- | --- | --- | --- |
| `/boot/firmware/config.txt` | read, replace | `App:3536-3609`, `App:3614`, `App:3629`, `App:3770`, `App:3787` | upstream wrote it for the fan mode only |
| `/boot/firmware/config.txt.apertar.bak` | written before every replace | `App:3538`, `App:3549`, `App:3595`; `scripts/apertar-boot-config:19`, `:56` | new |
| `<dir>/.config.txt.apertar-<pid>.tmp` | temp for the direct write | `App:3552` | new |
| `/tmp/apertar-boot-config-<pid>.txt` | staged text for the helper or `install` | `App:3571-3572` | replaces upstream `/tmp/apertar-fan-mode-<pid>.tmp` (`App:3147 @up`) |
| `/usr/local/libexec/apertar-boot-config` | run with `sudo -n`, text on stdin | `App:3502`, `App:3580-3582` | new. Source `scripts/apertar-boot-config`; installed by hand (`App:3605-3607`) |
| `/etc/sudoers.d/apertar-boot-config` | install step | `config/apertar-boot-config.sudoers` | new |
| `/boot/firmware/overlays/*.dtbo` | directory listing | `App:3660` | new read |
| `/proc/device-tree/compatible`, `/proc/device-tree/model` | read | `App:3656-3657` | new read |
| `/sys/class/drm/card*-*/status`, `.../modes` | read | `App:3674-3679` | new read |
| `~/.config/CinePi/UI.conf` | 18 new `[General]` keys | `App:2094-2189` | upstream file |
| `~/apertar-hardware.conf` | `[storage]`, `[media]` keys through the store | `App:276-281` | upstream file |
| `/run/apertar-media/eject/<device>` | written before an eject, removed after a mount | `App:4355`, `App:4389`; `src/util/MediaIntent.hpp:28-58` | new. Directory from `config/apertar-media.tmpfiles.conf` |

### 3.7 UI elements that use the slice's items (outside the slice)

| Element | Where `@port` | Feature |
| --- | --- | --- |
| WebUI System pane, "Boot Config" card `#settingsBootConfigCard`, "Edit file" button | `WCP:5859-5862`, `WCP:5929`, script `WCP:19868+` | F1 |
| WebUI "Value Lists" card (Controls pane) | `WCP:6165`, `sendCommand set_value_steps` `WCP:8494` | F3 |
| Touch UI pickers from the lists | `Apertar-UI/src/SettingsBridge.cpp`, `qml/CameraPage.qml` (probable: fork-log `ed0d7b5`; files found by `git grep`) | F3 |
| WebUI "Write buffer" select; buffer bar | `WCP:4921`; `/api/buffer` poll `WCP:16417` | F4 |
| WebUI "Storage pre-roll" button, auto options, blue pill | `WCP:5769-5778`, `WCP:230` | F5 |
| WebUI Performance card "Frames per folder", "Merge split clips" | `WCP:5809-5811`, `WCP:5822` | F6, F7 |
| WebUI switches "Recording frame", "Frame buffer bar", "Red timecode while recording", "Audio recording outline" | `WCP:5275`, `WCP:5279`, `WCP:5284`, `WCP:5288` | F22 |
| Touch UI Settings switches and overlays for the same four keys | `qml/SettingsPage.qml`, `qml/CameraPage.qml`, `qml/ExternalMonitorWindow.qml`, `src/SettingsBridge.cpp` | F22 |
| Touch UI fan mode through `set_fan_mode` | `Apertar-UI/src/SystemActionBridge.cpp` | F2 |

## 4. Original code modified

`@up` lines are upstream 1.6.0; the same text is in fork main at the mapped line.

| # | Region | `@up` | `@port` | Kind | Change |
| --- | --- | --- | --- | --- | --- |
| 1 | Include block | `App:1-55` | `App:1-79` | extended-in-place | 4 `util/` includes placed before `<apertar/core/...>` (2-5); 6 `hardware/` includes among the upstream ones (9-13, 15); `<cerrno>` (27); 4 `<sys/...>` (55-58); a second block after the JPEG `#if`: `<csignal>`, `<functional>`, `playback/` and `cdng/` headers (72-79) |
| 2 | Constants at the top of the anonymous namespace | `App:60-64` | `App:84-107` | extended-in-place | `webPreviewRecordingFps()` (89-106) sits between `kWebPreviewJpegQuality` and `kMaxEditableHardwareConfigBytes` |
| 3 | Reply builders `okReply`, `errorReply` | `App:108-128` | `App:151-184` | extended-in-place | third builder `errorReplyBody(id, message, body)` (173-184); the two upstream ones unchanged |
| 4 | `settingsBody` | `App:167-217` | `App:313-395` | extended-in-place | 27 members inserted between upstream ones; last line now `<< "," << bufferSettingMembers();` (393), so storage and buffer state rides in every settings reply |
| 5 | `jsonStringArray` neighbourhood | `App:293-304` | `App:472-496` | extended-in-place | `jsonNumberArray` added after it; forward-declared at `App:233` because `settingsBody` uses it earlier |
| 6 | `maximumPcfFpsForSettings`, IMX585 4K | `App:1141` (`return 30.0;`) | `App:1386-1389` | behaviour-changed | `return settings.clearHdr && settings.rawBitDepth == 16 ? 25.0 : 30.0;` |
| 7 | `availablePcfFpsOptions` | `App:1150-1168` | `App:1398-1416` | rewritten | Preset choice moved to new `builtInFpsSteps` (IMX585 gets 100 and 120). New third argument `steps`. Ceiling = `settings.fpsMax` when > 0, else the table. Filter replaced by `selectableValueSteps`: values up to the ceiling, plus the ceiling itself when a value lies above it. Upstream kept presets <= max and added the max only when none was left |
| 8 | `availablePcfResolutionOptions` | `App:1182` (1 argument) | `App:1432` | extended-in-place | New argument `settings`; IMX283 block `App:1493-1513` |
| 9 | `pcfIsoOptions()` | `App:1279-1282` | `App:1551-1554`, `App:1574-1577` | rewritten | Body renamed `builtInIsoSteps()`. The name now takes `(steps, isoMax)` and cuts at `iso_max` |
| 10 | `pcfShutterAngleOptions()` | `App:1284-1290` | `App:1556-1562`, `App:1581-1592` | rewritten | Body renamed `builtInShutterAngleSteps()`. The name now takes `(steps, fps, flickerMainsHz)` and merges the flicker-free angles |
| 11 | `pcfWhiteBalanceOptions()` | `App:1314-1321` | `App:1564-1571`, `App:1616-1619` | moved | List moved up as `builtInWhiteBalanceSteps()`. The name now takes `(steps)` |
| 12 | `hardwareActionSuffix` | `App:1342-1356` | `App:1645-1649` | moved | Body now in `src/hardware/ActionCatalog.hpp:135-144` (`suffixAfter`); App keeps a one-line wrapper and `prefixViews` (1640-1643) |
| 13 | `parseHardwareActionNumber` | `App:1358-1370` | `App:1651-1655` | behaviour-changed | Body now `actions::numberAfter` (`ActionCatalog.hpp:157-163`). Number parse changed from `parseDoubleValue` (`std::stod`, trims, `App:892 @up`) to `strtod` with `inf` / `nan` refused (`ActionCatalog.hpp:146-155`) |
| 14 | `SharedUiSettingsSnapshot` | `App:1581-1639` | `App:1866-1945` | extended-in-place | +4 fields (1903-1907), +14 fields (1929-1944) |
| 15 | `readSharedUiSettings` | `App:1641-1813` | `App:1983-2196` | extended-in-place | +4 keys (2094-2101), +14 keys (2159-2191), same `else if (key == ...)` chain |
| 16 | `currentFanMode` | `App:3119-3125` | `App:3612-3618` | extended-in-place | Reads `bootConfigPath()` (env override) instead of `kBootConfigPath` |
| 17 | `applyFanMode` | `App:3127-3178` | `App:3620-3649` | rewritten | Validation and block building kept. The write half (temp file, `sudo -n install -m 644`, error mapping; `App:3147-3177 @up`, 31 lines) replaced by `bootConfigMutex()` + `writeBootConfigText()`: direct write when writable, else the root helper, else `sudo -n install` as before. New side effects: `config.txt.apertar.bak` on every change; an extra `sudo -n install` for that backup on the old route. Message "Could not prepare the fan mode update." is gone |
| 18 | Embedded Python `mount_partition` in `startNvmeReinsertWatcherAtPath` | `App:3545`, `:3547`, `:3549` | `App:4208`, `:4210`, `:4212` | behaviour-changed | ntfs3 and exfat: `uid=1000,gid=1000` becomes `uid=1000,gid=1000,umask=0002,noatime`; ext4 gets `-o noatime` |
| 19 | `mountDeviceAtMediaPath` | `App:3604-3647` | `App:4267-4313` | behaviour-changed | `noatime` appended to the NTFS and FAT options; new `else { options = "noatime"; }` so every other filesystem mounts with it too (upstream: no options) |
| 20 | `mountMediaDeviceAtPath` | `App:3657-3708` | `App:4323-4375` | extended-in-place | `clearEjectIntent(normalizedDevicePath)` after a successful mount (4355) |
| 21 | `ejectMediaAtPath` | `App:3710-3761` | `App:4377-4434` | extended-in-place | `writeEjectIntent` before `flushMediaPath`; a failure only logs (4386-4391) |

Call-site changes that follow from rows 7-11 are in later slices (`App:10220`, `App:10443-10555`, `App:12538-12548 @port`; upstream `App:8500-8552`, `App:8771-8832`).

## 5. New abstractions

| # | Name | Kind | Where `@port` | Purpose | Upstream uses for the same job | Used by |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `errorReplyBody` | free function | `App:173-184` | Error reply with extra JSON members | `errorReply(id, message)`, `App:120-128 @up`: errors carry `error` only | `set_controls`, `/api/config`, `set_buffer_mode`, `set_frames_per_folder`, `set_storage_preroll`, Boot Config (14 call sites) |
| 2 | `sensorBinningBody`, `bufferMembers`, `bufferSettingMembers`, `valueStepsJson` | JSON fragment builders | `App:224`, `:301`, `:252`, `:1963` | Flat `"key":value` members shared by several replies | Same style: `imuStatusBody` `App:130 @up`, `settingsBody` `App:167 @up` | state, routes, events |
| 3 | `jsonNumberArray` | free function | `App:485-496` | Array of doubles as JSON | `jsonStringArray` `App:293 @up` (strings only) | `ladder_tops`, value lists, `list_actions` |
| 4 | `refreshBufferRequest` + process-wide request state | function + header-level singletons | `App:273-286`; `src/util/BufferBudget.hpp:224-333`, `src/util/StoragePreroll.hpp:224-249` | Parse `[storage]` / `[media]` and env, publish the result into atomics that `CameraController` and the workers read | Each hardware class opens the file and parses its own section at start (`src/hardware/GpioInput.cpp:382-436 @up`); App hands values to the camera through `camera_.set*`. Function-local statics exist upstream only as file-private caches (`App:2269 @up`). No header-level mutable shared state found upstream (`grep` for `static std::atomic`, `static std::mutex`, `static std::function` on `src`, `include @up`: hits in `.cpp` files only) | `ApertarCoreApp::start` (`App:8034`, `:8145`), `/api/config`, `set_controls`, `set_buffer_mode`, `set_frames_per_folder`, `set_storage_preroll` |
| 5 | `abortSafetyStopFlushForRecord` | free function | `App:291-299` | Abort the safety-stop drain before any lock is taken | none (upstream has no safety stop; every command runs under `commandMutex_`) | `handleCommand` `App:12570`, `dispatchHardwareInputCommand` `App:10119` |
| 6 | `webPreviewRecordingFps` | cached env read (static lambda) | `App:93-106` | Preview rate during a raw take | Constant `kWebPreviewMaxFps` `App:62 @up`; env knobs read in place, for example `CC:4333 @up` | `captureWebPreviewFrame` `App:9780` |
| 7 | Value-step helpers: `selectableValueSteps`, `flickerFreeShutterAngles`, `freeStepValue`, `builtIn*Steps`, `parseValueStepsList` | free functions | `App:1274-1321`, `:1398`, `:1551-1571`, `:1948` | Operator lists cut at the mode ceiling; free stepping; flicker-free angles | Fixed lists `pcfIsoOptions()`, `pcfShutterAngleOptions()`, `pcfWhiteBalanceOptions()` (`App:1279`, `:1284`, `:1314 @up`), stepped with `nextPcfPresetIndex` (`App:1059 @up`) | hardware inputs, `list_actions`, `set_value_steps`, web state |
| 8 | `writeBootConfigText` | free function, three write routes | `App:3533-3610` | One writer for config.txt with backup | `sudo -n install -m 644 <tmp> /boot/firmware/config.txt` inside `applyFanMode` (`App:3155-3158 @up`). For a user-owned file: `saveHardwareConfigFile` (`.bak` copy, `.tmp`, rename, `App:5323 @up`), no fsync | `applyFanMode`, `bootConfigSet` |
| 9 | `bootConfigMutex`, `bootConfigPath`, `fsyncPath` | file-local helpers | `App:3505-3527` | Serialise config.txt writers; env path override; fsync a path | `kBootConfigPath` constant `App:2845 @up`; no mutex (upstream Core and the touch UI each write the fan block: `Apertar-UI/src/SystemActionBridge.cpp:23-25 @up`); no fsync helper | fan mode, Boot Config |
| 10 | `BootConfigReply {status, body}` | struct | `App:3761-3764` | One function serves the socket command and the HTTP route with a status | Routes fill `WebServer::Response` in `handleWebRequest` (`App:7175-7195 @up`); commands return a string | `bootConfigGet`, `bootConfigSet` |
| 11 | `bootConfigFacts`, `drmConnectorsJson`, `bootConfigJson`, `bootConfigRequestFrom`, `boolFieldValue` | free functions | `App:3653-3759` | Board, overlays and DRM facts; request parsing | none (new area). Bool parsing upstream: `parseUiSettingsBool` `App:350 @up` (`true`, `1`, `false`, `0` only) | Boot Config |
| 12 | `apertar::bootconf` (`src/hardware/BootConfigText.hpp`, 1355 lines, header-only, no I/O) | namespace | included at `App:15` | config.txt parser, state, edit engine, JSON | none. Upstream edits config.txt only by replacing the fan block (`stripManagedFanBlock` `App:3084 @up`) | Boot Config; host test `tools/boot_config_test.cpp` |
| 13 | `scripts/apertar-boot-config` + `config/apertar-boot-config.sudoers` | root helper (POSIX sh) + sudoers rule with no arguments | repo files | Replace config.txt as root from stdin | Upstream root helpers are compiled programs in the UI repo with argument-pinned sudoers: `Apertar-UI/src/StandbyUsbPower.cpp`, `systemd/apertar-standby-usb.sudoers @up`, called at `App:1544`, `:1549 @up`. Upstream Core ships no helper script (`scripts/` holds `start-apertar-core.sh` only) | `writeBootConfigText` |
| 14 | `apertar::hardware::actions` (`src/hardware/ActionCatalog.hpp`, 360 lines) | namespace, header-only | included at `App:9` | One action vocabulary; `suffixAfter`, `numberAfter` | `hardwareActionSuffix`, `parseHardwareActionNumber` in App (`App:1342-1370 @up`) and a `normalizeSingleAction` per driver (commit message `916c1dd`; drivers not read here: **probable**) | App wrappers `App:1645-1655` |
| 15 | `apertar::hwconf` (`ControlsModel.hpp` 390 lines, `HardwareConfigText.hpp` 1141 lines) and `hardware::configStore()` (`HardwareConfigStore.hpp/.cpp`) | namespaces, a singleton store | included at `App:10`, `:13` | The hardware file as text, key edits, validator, one writer with history | `saveHardwareConfigFile` `App:5323 @up`; each class parses its own section | slice: `App:276-281` only |
| 16 | `hardware::GpioChipInfo`, `gpioChipScore`, `headerGpioChipPath` (`GpioChipInfo.hpp/.cpp`) | struct + free functions | included at `App:11` | Read a GPIO chip's name, label, line holders; score chips for `chip=auto` | Same scoring as a file-private function in `src/hardware/GpioInput.cpp:238-262 @up` and again in `RecordingIndicatorOutput.cpp:198 @up` | later slices (`App:11987-11989`) |
| 17 | `hardware::probeI2cAddress` (`I2cProbe.hpp/.cpp`) | free function | included at `App:12` | One-byte I2C presence probe | none in this form. The IMU class probes its own addresses (`Mpu6050RecordingSession.cpp:1587-1589 @up`; **probable**: only the `grep` hit was read) | later slices |
| 18 | `CfeHatReader`, `CfeHatConfig` (`src/util/CfeHat.hpp`) | class, header-only | included at `App:2` | Read the CFexpress HAT status byte in C++ | The embedded Python watcher reads it with `smbus` (`App:3391-3392`, `read_insert_state @up`) | later slices |
| 19 | `writeEjectIntent`, `clearEjectIntent` (`src/util/MediaIntent.hpp`) | inline functions | included at `App:3` | Eject flag file under `/run/apertar-media` | none. Upstream run-state directories exist (`/run/apertar-cfe/ready`, `Apertar-UI/src/CfeAutomounter.cpp:40 @up`) | `App:4355`, `:4389`, `:10917` |
| 20 | `apertar::storagepreroll` (`StoragePreroll.hpp`), `apertar::bufferbudget` (`BufferBudget.hpp`), `apertar::clipname` (`ClipName.hpp`), `apertar::framepath`, `apertar::clipmerge`, `apertar::playback` | namespaces, header-only "pure logic" modules with host tests in `tools/` | included at `App:4-5`, `:75-79` | Decisions without I/O, testable on a host | Upstream has header-only modules (`camera/DefaultTuningSelection.hpp` in `apertar::tuning`, `cdng/IfdBuilder.hpp` in `apertar::tiff`, `util/SettingsFile.hpp`). Upstream has no `tools/` tests and no `third_party/` in Core | later slices |

## 6. Removed, narrowed, hidden

| # | What | Where | Effect |
| --- | --- | --- | --- |
| 1 | Zero-argument `pcfIsoOptions()`, `pcfShutterAngleOptions()`, `pcfWhiteBalanceOptions()` | `App:1279`, `:1284`, `:1314 @up` | Names reused with new signatures; the fixed lists live on as `builtIn*Steps()` |
| 2 | The per-sensor FPS table as the ceiling for hardware steps | `maximumPcfFpsForSettings`, `App:1076 @up`; `App:1414 @port` | Now a fallback for `settings.fpsMax <= 0` only. `fpsMax` is filled at `CC:12590`, `CC:12864 @port` (**probable**: the fallback is not reached in normal runs; `maximumFpsForSettings` returning 0 was not read) |
| 3 | Upstream FPS filter "presets <= max" | `App:1159-1167 @up` | Replaced by `selectableValueSteps`: the dial can land on the ceiling value itself (for example 41.08) |
| 4 | Bodies of `hardwareActionSuffix`, `parseHardwareActionNumber` | `App:1345-1355`, `:1361-1369 @up` | Moved to `ActionCatalog.hpp`; `inf` / `nan` suffixes no longer parse |
| 5 | Upstream fan-mode write code and one message | `App:3147-3177 @up` | Replaced by `writeBootConfigText`; "Could not prepare the fan mode update." no longer appears |
| 6 | Mounts without options | `App:3545-3549`, `:3614-3621 @up` | Every filesystem now mounts `noatime`; the re-insert watcher adds `umask=0002` |
| 7 | (Reached through the include at `App:10`, not in the slice) The "GPIO chip" setting and "Poll every (ms)" on the Controls card | `src/hardware/ControlsModel.hpp:257-263 @port`; added by `166cc4d`, removed by `c140c4f` | The chip can only be set in the text editor. See section 9 |

Nothing upstream had in the state, the socket API or UI.conf was removed in this slice.

## 7. Board assumptions

| # | Assumption | Where `@port` | Upstream has it too |
| --- | --- | --- | --- |
| 1 | No device tree = "read as a Pi 5" | `src/hardware/BootConfigText.hpp:80`, `:95`, called at `App:3656` | new |
| 2 | Board family from `bcm2712` / `bcm2711` / `bcm2837` / `bcm2710` in `/proc/device-tree/compatible` | `BootConfigText.hpp:91-93` | new |
| 3 | Two CSI ports `cam0`, `cam1` in the request fields | `App:3724`; `boardPorts` `BootConfigText.hpp:125` (Pi 5 and compute modules have `cam0`) | new |
| 4 | `rp1` field: RP1 clock overlay `rp1-clk-333mhz`, Pi 5 family only | `App:3741`, `App:3751`; `BootConfigText.hpp:1023` | new |
| 5 | DPI display owns GPIO 0-27 and I2C bus 1 | message at `App:3825-3826` | new |
| 6 | config.txt at `/boot/firmware/config.txt` with a `[pi5]`, `[pi4]` or `[all]` section | `App:3228` (`@up 2845`); `scripts/apertar-boot-config:18`, `:51` | path yes; section check new |
| 7 | Core runs as user `pi`; checkout at `~/ApertarCore` | `config/apertar-boot-config.sudoers:4`; message `App:3605-3607` | `pi` yes (`Apertar-UI/systemd/apertar-standby-usb.sudoers:1 @up`); checkout path in a message is new |
| 8 | `/sys/class/drm/card*-*` connectors exist (KMS) | `App:3674` | new |
| 9 | Built-in FPS steps by sensor name: imx585 to 120, imx477 / imx577 to 100, others to 60 | `App:1398-1406` | lists for imx477 / imx577 and others yes (`App:1154-1157 @up`); imx585 100 / 120 new (`caa0153`) |
| 10 | IMX585 4K Clear HDR 16-bit = 25 fps | `App:1386-1389` | new (`b5847c7`) |
| 11 | IMX283 sizes of the cinemate-port driver: 12-bit 5472x3648, 5472x3080, 2736x1824, 2736x1540, 1824x1216, 1820x1024; 10-bit 5472x3648, 5472x3076, 3840x2160; ProRes / H.264 3840x2160 only | `App:1493-1513` | new |
| 12 | Mount ownership `uid=1000,gid=1000`; `ntfs3` kernel driver | `App:4208-4212`, `App:4281-4284` | yes (`App:3545-3549`, `:3617-3620 @up`); the port adds only `umask` / `noatime` |
| 13 | CFexpress HAT on I2C bus 10 at 0x34; PCIe controller `1000110000.pcie`, `brcm-pcie` | Python `App:4054-4058`; C++ copy of bus and address `src/util/CfeHat.hpp:20-21` | yes in the script (`App:3391-3395 @up`); the C++ default is a second copy |
| 14 | Web preview downsample costs "0.2 to 0.5 ms per frame measured idle" | comment `App:89-92` | new. The comment names no board |
| 15 | GPIO header chip scoring: "rp1" +100, BCM pin controllers +90, 28 lines | `src/hardware/GpioChipInfo.cpp:31-55` (included at `App:11`) | yes (`src/hardware/GpioInput.cpp:238-262 @up`) |

No assumption about core count, RAM size or fan hardware was added in this slice. The fan block (`dtparam=cooling_fan=on`, `fan_temp*`) is upstream text (`App:3042-3082 @up`), unchanged.

## 8. Facts for the later stages (no judgement)

| # | Fact | Evidence |
| --- | --- | --- |
| 1 | Commit message and content are crossed. `04bac89` ("trim after a delete made outside Core ...") holds the three mount-option lines; `e0fa852` ("noatime and umask on the re-insert mount ...") holds the pre-roll trim change | `git show 04bac89 -- src/ApertarCoreApp.cpp` (hunk `mount_partition`); `git show e0fa852 -- src/ApertarCoreApp.cpp` (hunk `runStoragePrerollOnce`) |
| 2 | Comment out of date: "Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution()" | `App:1386 @port`. `CC:3379-3380 @port` returns 25 for any Clear HDR when the sensor limit is unknown; the 16-bit cap was removed from `backendMaximumFps` (`CC:3426-3434 @port`, commit `31d5418`) |
| 3 | No reader of the eject flag in the port's two repos | `git grep "run/apertar"` on `Apertar-UI cinemate-port` finds `/run/apertar-ui`, `/run/apertar-cfe`, `/run/apertar-network`, `/run/apertar-standby-*`, no `/run/apertar-media`; in Core only `MediaIntent.hpp` and `scripts/apertar-media-tune:30` (the `tune` subfolder) name the directory |
| 4 | State fields with no reader in `WCP` or the touch UI | `conform_fps`, `ladder_override`, `buffer_used`, `buffer_capacity`, `buffer_unit`, `sensor_binning`, `sensor_binning_source`, `sensor_crop` (section 3.2, 0 / 0) |
| 5 | `refreshBufferRequest` reads the store text three times and parses `[storage]` twice per call | `App:276`, `:279`, `:281` |
| 6 | `bufferSettingMembers` calls `getenv` three times and runs for every settings reply | `App:266`, `:268`, `:393` |
| 7 | Internal references in comments | `App:91-92` ("kb working/dng-chain, V/H4"), `App:1272` ("T33 (request 24)"), `App:1293` ("Cinemate's two versions ... both are off"), `App:1308`, `:1929`, `:1961` ("T33"), `App:4387` ("Cinemate f01b6cd") |
| 8 | One comment line holds two sentences run together (about 250 characters) | `App:250` |
| 9 | The `[storage]` and `[media]` parsers skip a value with a trailing `#` or `;` comment; upstream parsers strip the comment and keep the value | `src/util/BufferBudget.hpp:176`, `src/util/StoragePreroll.hpp:81 @port`; `src/hardware/GpioInput.cpp:399-401 @up` |
| 10 | `boolFieldValue` accepts `true/1/on/yes` and `false/0/off/no`; upstream `parseUiSettingsBool` accepts `true/1`, `false/0` | `App:3709-3718 @port`; `App:350-357 @up` |
| 11 | `bootConfigSet` distinguishes a browser by the `Origin` header | `App:9193`, `App:3792` |
| 12 | Seen in passing, outside the slice: `get_state` writes `media_state` twice | `App:12944`, `App:12961 @port` |
| 13 | `settingsBody` and `settingsEvent` no longer carry the same set: the 14 buffer and storage members are in the reply body only | `App:393 @port`; `grep '"buffer_setting"'` in `CC:163-246 @port` = 0 |
| 14 | The second include block sits after the JPEG `#if`, outside upstream's grouping (own header, public headers, project headers, std, system) | `App:72-79 @port`; `App:1-55 @up` |
| 15 | New nested values in replies built in this slice: `ladder_tops` (array) in `settingsBody`; `boot_config{...}`, `state{...}`, `changes[]`, `drm[]` in the Boot Config replies; `ui{...}` with four arrays in the `set_value_steps` reply. Upstream's own list of nested members is in `raw/conv-core-command-plane.md`, 5.5 | `App:334`, `App:3701-3706`, `App:3817-3822`, `App:14162 @port` |

## 9. Owner request: the GPIO chip definition

Request relayed with this run: put the chip definition back, because GPIOs of another chip (a microcontroller) can be chosen.

This slice holds only the include lines (`App:10-11 @port`). The facts below were read while following those includes.

| # | Fact | Evidence |
| --- | --- | --- |
| 1 | Upstream lets the operator name the chip per section: key `chip`, aliases `gpiochip`, `gpio_chip`; `auto` scores `/dev/gpiochip0..9` | `src/hardware/GpioInput.cpp:431-432`, `:507-535 @up`; `RecordingIndicatorOutput.cpp:319`, `:347 @up`; `TriggerOutput.cpp:311 @up`; template `gpiochip=auto` `App:4380`, `:4394 @up` |
| 2 | Upstream has no dedicated chip field in the WebUI or touch UI; the key is edited as text on the Config page. The touch UI's first-run template writes `chip=auto` in `[gpio_buttons]` and `[gpio_encoders]` and `gpiochip=auto` in the two output sections | 0 hits for `gpiochip` or `"chip"` in `WCP @up`; `Apertar-UI/src/DisplayConfigBridge.cpp:161`, `:172`, `:110`, `:123 @up` |
| 3 | The port's drivers still read the key | `src/hardware/GpioInput.cpp:343`, `:465 @port`; `RecordingIndicatorOutput.cpp:312`, `:340 @port`; `TriggerOutput.cpp:305 @port`; template `App:5168`, `:5182 @port` |
| 4 | The port's Controls card had a "GPIO chip" text setting (default `auto`), added in `166cc4d`, and a "Poll every (ms)" setting. `c140c4f` removed both | `git show 166cc4d`: `+{"chip", "GPIO chip", "text", "auto", "", 0, 0},`. `git show c140c4f -- src/hardware/ControlsModel.hpp`: the same line and `{"poll_ms", ...}` with `-`. Message: "The GPIO card's settings drop poll and chip (edge events need neither)" |
| 5 | What is left is a comment | `src/hardware/ControlsModel.hpp:263 @port`: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" |
| 6 | The card's status line "Chip /dev/gpiochipN (label), N lines" was added in `166cc4d` and removed in `f5fe41b`. Core still sends `status.chip` | `git log -S'chipLine' -- src/web/WebControlPage.cpp`; `App:11997-11999 @port`; 0 hits for `status.chip` in `WCP @port` |
| 7 | `get_controls` reads only the first 28 lines of the chip and names the peripheral "Raspberry Pi GPIO". With `chip=auto` it shows the single best-scoring chip; the driver tries every candidate in score order | `App:11987-11989`, `App:11994 @port`; `src/hardware/GpioChipInfo.cpp:57-72 @port`; `src/hardware/GpioInput.cpp:470-490 @port` |
| 8 | The tally and trigger settings on the card have no chip field and limit `line` to -1..27 | `src/hardware/ControlsModel.hpp:264-271 @port` |
| 9 | The validator knows `chip` in `[gpio_buttons]`, `[recording_indicator]`, `[trigger_output]`, not in `[gpio_encoders]`, where the driver accepts it | `src/hardware/HardwareConfigText.hpp:456-457`, `:460-462`, `:475-476 @port`; `GpioInput.cpp:302-343 @port` (**probable**: what the validator does with an unknown key was not read) |
| 10 | The alias `gpiochip` / `gpio_chip` is mapped to `chip` by the port's text model | `src/hardware/HardwareConfigText.hpp:172 @port` |
| 11 | The port's touch UI no longer writes a first-run template, so its `chip=auto` lines are gone. Core's template keeps `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]`; its `[gpio]` block has no chip line, as upstream | 0 hits for `chip=auto` in `Apertar-UI cinemate-port -- src` (fork-log `c9d841f`); `App:5137`, `:5168`, `:5182 @port`; `App:4366-4369 @up` |

The upstream side of this is also in `raw/conv-core-command-plane.md`, section 9.
