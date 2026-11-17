# Review: unit App-2 (`src/ApertarCoreApp.cpp`, port lines 4954-8205)

Stage 2 of 3. Judged against Apertar-Studio 1.6.0. Inventory: `raw/inv-App-2.md`. Yardstick: `raw/conv-core-command-plane.md` (C1-*), `raw/conv-core-camera.md` (C2 R5).

| Item | Value |
| --- | --- |
| Port | `/home/user/Apertar-Core` @cinemate-port `01f170c` (working tree = cinemate-port for this file, `git diff --stat cinemate-port` empty) |
| Upstream | `/home/user/wt/core-upstream` @upstream-1.6.0; `/home/user/wt/ui-upstream` @upstream-1.6.0 |
| Short names | `App` = `src/ApertarCoreApp.cpp`; `@port`, `@up` |
| Labels | confirmed unless marked probable |

## 1. Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| App-2-F1 | blocker | removed-upstream-behaviour | Template `[display]` switched from the stock 720x720 panel to the contributor's HDMI 1080p rig |
| App-2-F2 | major | removed-upstream-behaviour | Core's template is now the only default file, but lacks what upstream's first-run file held (`chip=auto`, `[gpio_buttons]`, `[mpu6050]`, input tuning) |
| App-2-F3 | major | mismatch | Buffer safety stop reaches App through a process-global `std::function` hook |
| App-2-F4 | major | mismatch | Seven new worker threads, three start styles, one omnibus `stopMediaWatcher()` |
| App-2-F5 | major | mismatch | Env-var knobs reach state and WebUI; storage switches split over three stores; App keeps a settings copy |
| App-2-F6 | minor | removed-upstream-behaviour | `/api/media` in a hold hides folders; cDNG `size_bytes` / `file_count` change meaning |
| App-2-F7 | minor | bug | `audio_url` is JSON-escaped, not URL-encoded |
| App-2-F8 | minor | slop | Ticket tags, Cinemate names and a Cinemate tool (`raw2wav.py`) in comments and operator text |
| App-2-F9 | minor | new-ground | `clipInfoJson` nests `meta` / `extra` objects that repeat top-level values as display strings |
| App-2-F10 | minor | mismatch | C++ `[cfexpress_hat]` reader defaults to off; upstream's reader of the same section defaults to on |
| App-2-F11 | minor | new-ground | `HardwareConfigStore` replaces upstream's one save function with revisions, history, merge review, adopt-at-start |
| App-2-F12 | minor | pi-compat | `hardwareConfigFacts()` feeds `parseConfigTxt`, which honours only `[all]` and `[pi5]` |
| App-2-F13 | minor | security | Root trim helper takes a path argument; upstream rule is fixed arguments only |
| App-2-F14 | nit | mismatch | Success lines logged at every start |
| App-2-F15 | nit | duplication | Three identical now-ms helpers, a second `/boot` candidate list, `refreshBufferRequest()` twice, unread `boot_copy` |

### App-2-F1 Template `[display]` defaults (blocker, removed-upstream-behaviour, deliberate yes)

| Side | Evidence |
| --- | --- |
| Port | `App:5089-5098 @port`: `ui_width=1920`, `ui_height=1080`, `ui_layout=landscape_large`, `hdmi_external_only=true`; comment `# Resolutions: 1920x1080(Default), 720x720, ...` |
| Upstream Core template | `App:4313`, `:4320-4322`, `:4329 @up`: `ui_width=720`, `ui_height=720`, `ui_layout=square`, `hdmi_external_only=false` |
| Upstream UI first-run file | `ui-upstream/src/DisplayConfigBridge.cpp:314`, `:323`: `ui_width=720`, `hdmi_external_only=false` |
| Upstream UI reader defaults | `ui-upstream/src/DisplayConfigBridge.cpp:14-15` `kDefaultUiWidth = 720`, `kDefaultUiHeight = 720`; `:647-650` `hdmi_external_only` default `false` |
| Commit | `7af9f13` "the 720x720 square layout of the old Hyperpixel screen, which is not what this camera uses" |

Why: the template is what the Config page shows for a missing file. An operator of a stock Apertar camera who opens the page and saves (for example to set one button) writes 1920x1080 and `hdmi_external_only=true`; the touch UI restarts in the 1080p layout with the panel handed to HDMI. The default now describes one contributor's rig.
Rework: restore the four upstream lines and the upstream resolutions comment in `defaultHardwareConfigTemplate()`. An HDMI rig sets its own values. Effort S.

### App-2-F2 Default file content lost (major, removed-upstream-behaviour, deliberate partly)

| Fact | Evidence |
| --- | --- |
| Upstream wrote a full default file on first run from the touch UI: `[gpio_buttons]` with `chip=auto`, `active_low`, `pull`, `poll_ms`, `debounce_ms`, examples; `[gpio_encoders]` with `chip=auto`; `[mpu6050]` with `bus`, `address`, `sample_rate_hz`, `orientation`, level reference; `[neorotary4]` with knob mappings | `ui-upstream/src/DisplayConfigBridge.cpp:57-330` (`:156-172`, `:206-225`, `:131-155`) |
| The port removed that writer; Core's template is the only one left | UI commit `c9d841f` (inventory 9.3) |
| Core's template @port has `[gpio]` with `enabled=false` only, `[gpio_encoders]` `enabled=false` only, no `[mpu6050]`, no `chip=` in any input section | `App:5137-5151 @port` |
| `[imu]` lost `bus=10`, `address`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation` (correctly: the reader ignores them there) but they were not moved to `[mpu6050]`, where the reader takes them | `Mpu6050RecordingSession.cpp:938-985 @up` (driver section branch `:956-981`) |
| `[gpio_switches]` comment says it is "read like [gpio] (chip, ...)"; a `chip=` inside `[gpio_switches]` is not read | `App:5147 @port`; inventory 9.1 |
| The port's PCF8574 `bus=1`, `[imu] sync_mode`, `[neorotary4]` address match the upstream UI file: good | `ui-upstream/src/DisplayConfigBridge.cpp:88`, `:204`, `:137` |

Rework: make `defaultHardwareConfigTemplate()` the upstream UI first-run text (`DisplayConfigBridge.cpp:57-330 @up`) plus the port's new sections. Concretely: rename `[gpio]` to `[gpio_buttons]` with `chip=auto`, `active_low=true`, `pull=up`, `poll_ms=12`, `debounce_ms=60`; `[gpio_encoders]` with `chip=auto` and its defaults; add `[mpu6050]` with the keys removed from `[imu]`; fix the `[gpio_switches]` comment to "chip, pull, active_low and debounce_ms come from [gpio_buttons]". This is also the insertion point for the owner's GPIO-chip request. Effort S.

### App-2-F3 Safety-stop hook (major, mismatch, deliberate unknown)

| Side | Evidence |
| --- | --- |
| Port | `App:7987-7994 @port` `bufferbudget::safetyStopHook() = [this](...) {...}`; hook is a function-static `std::function` in a header, `src/util/BufferBudget.hpp:262-266`; called from `CameraController.cpp:5018`. A thread `runBufferSafetyStop` (`App:11083-11111`) waits on a cv with a 100 ms backstop and dispatches `record_stop` |
| Upstream | C1-S19: parts talk to App through `std::function` callbacks passed in the constructor; `App:6783-6785 @up` `camera_(..., [this](const std::string &eventJson) { publishEvent(eventJson); }, ...)`. C1-N05: camera failures are latched in the camera and picked up by App (`App:9094`, `:7033 @up`) |

Why: a global hook that captures `this` is a second, hidden wiring path between camera and App; it outlives App and any second `ApertarCoreApp` overwrites it. The original developer looks for camera-to-app wiring in the constructor's initialiser list.
Rework: add a `std::function<void(const SafetyStopHit &)>` parameter to `CameraController`'s constructor (beside the event and preview callbacks), pass it down to the write queue as a member; delete `safetyStopHook()`. Keep `runBufferSafetyStop` (its dispatch through `dispatchHardwareInputCommand` -> `handleCommand` follows C1-S01/S11). Effort M. Risk: write-queue construction path inside `CC` must carry the callback.

### App-2-F4 Worker threads (major, mismatch)

| Port | Evidence |
| --- | --- |
| 6 threads in `start()` before the camera, 1 after | `App:8027-8052`, `:8156-8157 @port` |
| Three start styles: `!running.load() && !joinable()`, `!joinable()` only, no guard (`mediaWatcherThread_`) | `App:8027`, `:8039`, `:8043-8044 @port` |
| Flags set with atomic stores, not under the group mutex | same |
| `stopMediaWatcher()` stops pre-roll, merge, trim, media watcher, buffer events and safety stop | `App:11054-11077 @port` |
| `stop()` calls `stopStoragePreroll()` and then `stopMediaWatcher()`, which calls it again | `App:8185`, `:8189`, `:11056 @port` |
| `start()` cannot run twice (`running_.exchange(true)`), so the guards are dead | `App:8004 @port` |

| Upstream | Evidence |
| --- | --- |
| C1-S17: start = flag under the group's mutex, then `std::thread(&ApertarCoreApp::runX, this)`; stop = one `stopX()` per worker | `App:6821-6825`, `App:10988-11014 @up` |
| C1-S21: periodic supervision lives in `wait()`'s 1 Hz loop | `App:7021-7053 @up` |
| 2 workers in `start()` plus 1 on demand | `AppH:147`, `:157`, `:176 @up` |

Rework: one `startX()` / `stopX()` pair per worker, named for what it stops (`stopMediaTrim`, `stopClipMerge`, `stopBufferEvents`, `stopBufferSafetyStop`, `stopMediaWatcher`), called in `stop()` in the C1-S25 order; flags set under each group's mutex; drop the dead `joinable()` guards; remove the double `stopStoragePreroll()`. Look at whether `runBufferEvents` and the trim scheduler can live in `wait()`'s 1 Hz loop (C1-S21); keep separate threads only for the media watcher (sub-second pull detection) and the safety stop. Verdict simplify. Effort M.

### App-2-F5 Env knobs and store split (major, mismatch)

| Port | Evidence |
| --- | --- |
| `APERTAR_MEDIA_TRIM=0` forces the trim off; exposed as `media_trim_env_off` in `/api/state`; the WebUI greys the switch | `App:6399-6404 @port`; inventory 4.2, `WCP:16184` |
| `refreshBufferRequest()` reads `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`; the state carries `frames_per_folder_env`, `clip_merge_env_off` | `App:266-285 @port` |
| Trim switch lives in `camera_settings.conf` (`CaptureSettings::mediaTrimEnabled`); buffer, split, merge in `[storage]` of the hardware file; pre-roll in `[media]` | `App:8073 @port`; template `App:5051-5072 @port` |
| App copies the trim setting into a member at start | `mediaTrimSetting_.store(camera_.settings().mediaTrimEnabled)` `App:8073 @port` |

| Upstream | Evidence |
| --- | --- |
| C1-S24: App reads only `APERTAR_HARDWARE_CONFIG`; process options are `Options` members | `App:4254 @up` |
| C2 R5: a bench knob `APERTAR_<AREA>_<KNOB>` is read where used and is NOT added to the socket API, `camera_settings.conf` or the hardware file | `raw/conv-core-camera.md` R5 step 4 |
| C1-S08: App keeps no copy of settings; `camera_.settings()` each time | `App:7715 @up` |

Rework: delete `mediaTrimEnvOff()`, `media_trim_env_off`, `frames_per_folder_env`, `clip_merge_env_off` and the env inputs of `refreshBufferRequest()` (keep only knobs that are true bench knobs, read where used, absent from state). Read `camera_.settings().mediaTrimEnabled` where the trim decides instead of `mediaTrimSetting_`. Pick one store for the four storage switches set by commands (`set_media_trim`, `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`): per C1-R2 a command-set persisted switch goes to `camera_settings.conf`; the hardware file keeps board facts (`mount_path`, `pcie_controller`). Effort M (store move touches handlers in another unit).

### App-2-F6 `/api/media` in a hold and cDNG numbers (minor, removed-upstream-behaviour)

- `App:7451-7454 @port`: `if (held && !haveFacts) continue;` drops ProRes, H.264, MLV, timelapse and unprobed cDNG folders from the list while a take runs. Upstream lists every folder (`App:6282-6448 @up`).
- The comment above `App:7488-7490` says "the last cached answer, or the bare entry"; the bare entry never happens, and `else if (!held)` at `:7520` is always true.
- cDNG `size_bytes` = frames + WAV + stretched WAV + `fps-ramp.txt`, `file_count` = frame count (`src/playback/ClipProbe.hpp:123-130`). Upstream = every file (`mediaStatsForPath` `App:5915 @up`). The download zips every file, so the shown size undercounts (for example a `.gcsv` gyro sidecar).
Rework: in a hold, push the bare entry (id, kind, name, type, sizes `--`) instead of `continue`; delete the duplicate comment; let the facts cache sum all files for `size_bytes` and keep `file_count` as files. Effort S.

### App-2-F7 `audio_url` not URL-encoded (minor, bug)

`App:7387 @port`: `"/api/media/file?kind=folder&id=" + escapeJson(id) + "&name=" + escapeJson(f.name) + ".wav"`. Upstream builds media URLs with `urlEncodeComponent` (`mediaDownloadUrl` `App:7147-7150 @port`, same at `@up`). Failing input (probable: clip names are composable since `014a2bf`): folder `A&B_001` gives `id=A&B_001`, the route reads `id=A`, 404. Also `#`, `%`, `+`, space. Rework: `escapeJson("/api/media/file?kind=folder&id=" + urlEncodeComponent(id) + "&name=" + urlEncodeComponent(f.name + ".wav"))`. Effort S.

### App-2-F8 Slop (minor)

| Text | Where @port |
| --- | --- |
| Tags T21, T37, T39, T42, T47, T50, T51, Q23, R1, "design §4.3", "kb working/dng-chain, R4" | `App:5585`, `:6335`, `:6378`, `:6390`, `:6454`, `:6764`, `:7208`, `:7219`, `:7336`, `:7354`, `:7442`, `:7488`, `:8032`, `:8117`, `:8118`, `:8136`, `:8172`, `:10897` |
| Operator text names a Cinemate tool that Apertar does not ship: "Not finalised: audio_capture.raw is on the media (raw2wav.py makes a WAV)" | `App:7381 @port`; `grep -rln raw2wav` over both upstream trees: none |
| "CineMate style", "CineMate's warm-up" in the template the operator reads on the Config page | `App:5052`, `:5068 @port` |
| History narration: "the old model assumed 12-bit packed ...", "the atomic starts as true, and the T37 block below ..." | `App:5585`, `:8032-8033 @port` |

Upstream: C1-I14, comments are rare, state a hazard or reason, no ticket numbers. Rework: delete tags and narration; operator text "Audio not finalised (audio_capture.raw)"; template text without product names. Effort S.

### App-2-F9 `clipInfoJson` shape (minor, new-ground, verdict simplify)

`App:7354-7405 @port`. Top level is flat snake_case (good), plus `holes` (array of pairs), `ramp` (`{"present":true}` or `null`), `meta{...}` and `extra{...}`. `meta.frame_rate` repeats `fps_badge`; `extra.sound` repeats `sound_text`; `meta.frames` repeats `frame_count`; `info_line` and `meta.*` are display strings ("in the touch UI's words"). Upstream HTTP replies are flat with a fixed short list of nested values (C1 5.5); the media list items are flat objects. Rework: drop `meta` and `extra`; add the two missing facts (`captured`, `clip_size`, `path`, `format_text`, `dropped_text`) as top-level snake_case strings; `ramp` as a boolean; keep `holes` as the one array. The WebUI formats. Effort S (plus `WCP` reader in another unit).

### App-2-F10 `[cfexpress_hat]` default (minor, mismatch, deliberate yes)

Port: `loadCfeHatConfig()` turns the HAT on only when the section header exists (`App:5314-5318 @port`; `src/util/CfeHat.hpp:19` `bool enabled = false;`). Upstream's reader of the same section, the embedded reinsert helper, defaults on: `CFE_HAT_ENABLED = True` `App:3393 @up`, overridden by `enabled` at `:3451`. The loader itself is a hand-written copy of `loadIna219HardwareConfig` (`App:4450-4506 @up`), which is the Apertar way (one reader per section, written out). With no hardware file (the UI no longer writes one, F2), the Python helper watches the slot and the C++ watcher does not. Rework: default `enabled = true` like the upstream reader, or document the difference in the commit; the stock template has the section on. Effort S.

### App-2-F11 `HardwareConfigStore` (minor, new-ground, verdict simplify, deliberate yes)

Upstream: one function `saveHardwareConfigFile` (`App:5323-5386 @up`): checks, `.bak`, `.tmp` + rename. C1-S07 allows the editor to write the whole file. The port keeps the three checks as `checkHardwareConfigText` (`App:6231-6252 @port`, good) and moves the write into a class with revisions, history, `adopt()` at every start (`App:8144`), merge review and six 409 codes. The second writer (Controls page) makes one writer defensible. Revision check plus atomic write plus `.bak` is enough; history files, adopt-at-start and the merge-review path are more than upstream would carry. Scripts without `Origin` keep last-writer-wins (`App:8630-8634 @port`), so no protocol break. Commits `5395fa4`, `014fa22`, KB T38 show it was weighed.

### App-2-F12 `parseConfigTxt` filters (minor, pi-compat)

`hardwareConfigFacts()` `App:4965-4978 @port` passes `/boot/firmware/config.txt` to `hwconf::parseConfigTxt`, which applies only `[all]` and `[pi5]` blocks (`src/hardware/HardwareConfigText.hpp:1037`, `:1051`). On Pi 4 / CM4 / CM5 a DPI overlay under `[pi4]`, `[cm4]` or `[cm5]` is missed and a `[pi5]`-only overlay is wrongly applied, so pin warnings are wrong. Rework: pass the board model into the parser (read `/proc/device-tree/model`) and honour the matching filter. Effort S.

### App-2-F13 Trim helper arguments (minor, security)

Port: `execl("/usr/bin/sudo", "sudo", "-n", helper, mountPoint, ...)` (`App:6432 @port`); sudoers `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` with any arguments (`config/apertar-media-trim.sudoers`); "the script itself validates its argument". Upstream: `App:1543 @up` "Fixed executable and arguments only; never accept paths from WebUI/config." The mount point comes from `[storage] mount_path`, which the Config page writes. fork/exec without a shell (needed to kill the helper) is fine. Rework: the helper takes no path (it trims the mount from its own fixed config or `findmnt` of the RAW label), or the sudoers line pins the argument. Effort S.

### App-2-F14 Start-up log (nit, mismatch)

`App:8146-8153 @port` logs "N errors, M warnings; adopted, nothing changed" every start; `runMediaWatcher` logs the HAT settings every start (`App:10861`). C1-I13: success is silent. Rework: log only issues and the replaced-file notice.

### App-2-F15 Small duplication (nit)

- `playbackNowMs()` `App:6337`, `trimNowMs()` `:6394`, `clipMergeNowMs()` `:11630 @port` are the same function. Keep one.
- `/boot` paths written again in `buildHardwareConfigFileJson` (`App:6188-6202 @port`) although `hardwareConfigCandidatePaths()` lists them (`App:4258-4259 @up`). Iterate the candidate list.
- `refreshBufferRequest()` twice in `start()` (`App:8034`, `:8145 @port`) with a comment explaining the order. Call it once before the first worker.
- `boot_copy` in `GET /api/config` has no reader (inventory 10). Drop or use.

## 2. Abstraction verdicts

| Name | Verdict | Reason |
| --- | --- | --- |
| `hwconf` (`Facts`, `Issue`, `validate`, `parseConfigTxt`) | simplify | New ground (upstream has no validator). Fine as a header beside the readers; fix the board filter (F12); the readers stay the truth |
| `HardwareConfigStore`, `configStore()` | simplify | F11 |
| `hardwareConfigFacts()` | keep | Free function in the anonymous namespace (C1-S06); fix F12 |
| `controlsIssuesJson`, `controlsConflictsJson`, `controlsReplacedJson`, `controlsErrorCount` | keep | Same shape as upstream `json*Array` helpers (`jsonMediaDriveArray` `App:2392 @up`), hand-written `ostringstream`, `escapeJson` (C1-I08) |
| `CfeHatConfig`, `CfeHatReader`, `loadCfeHatConfig()` | keep | Loader copies the INA219 loader pattern; fix the default (F10) |
| `playback::PlaybackYield`, `playbackYield()` | keep | Function-local static, same idiom as upstream probe caches (C1-I19); drop the T47 tag |
| `ClipFactsCache`, `clipFactsCache()` | keep | Same idiom; F6 for list semantics |
| `clipInfoJson()` | simplify | F9 |
| `MediaDeleteScope` | keep | Six-line RAII on an atomic; drop the Q23 tag |
| `runTrimHelperProcess`, `trimNowMs`, `mediaTrimEnvOff`, `mediaFreeBytesNow` | simplify | Drop the env knob (F5) and `trimNowMs` (F15); fixed helper args (F13) |
| `scripts/apertar-media-trim`, sudoers | simplify | F13 |
| `WavFormat`, `wavFormatForFile`, `wavSoundText` | keep | Upstream parser returns `std::optional` now (C1-I10); old name kept as a wrapper |
| `streamFileRangeToClient`, `parseSingleByteRange` | keep | Needed for seeking; free functions beside `streamFileToClient` |
| `bufferbudget::safetyStopHook()` | rework-to-upstream-pattern | F3: constructor callback (C1-S19) |
| 7 worker threads | simplify | F4 |
| `refreshBufferRequest()` | simplify | F5 (env inputs), F15 (called twice) |

## 3. Conforms

- `estimatedRawBytesPerSecond` now uses the touch UI's own per-frame model: constants equal `ui-upstream/qml/CameraPage.qml:870-937` (`rawFrameSizeMiB`, `losslessCdngRatio`, `h264EstimatedMbps`, MLV / lossy / lossless / uncompressed lines). Core and touch UI now agree; upstream's two models disagreed. `App:5586-5625 @port`.
- `estimatedStillFrameSizeMiB` adds `imx283` by substring beside the other sensors, same idiom (`App:5657-5662 @port` vs `App:4765-4783 @up`).
- `buildCurrentPresetPayload` adds keys with the existing `addBool` / `addString` / `addNumberString` / `addBoolFromMap` lambdas, camelCase, `camera<Name>` (C1-S22, C1-I17). `App:7786-7789`, `:7844-7856`, `:7868 @port`.
- `checkHardwareConfigText` keeps upstream's three checks and their exact operator sentences (C1-I07). `App:6231-6252 @port`.
- Showing the `/boot` copy for a missing home file matches what upstream readers already do (`hardwareConfigCandidatePaths` `App:4251-4259 @up`); upstream showed the template while the readers used the `/boot` copy.
- `clipContainerTypeLabel` extended in place, prefix rule kept (`App:6667-6671 @port`).
- `wavFormatForFile` refactor keeps `wavDurationTextForFile` output identical.
- `streamFileToClient` / `streamZipArchiveToClient` get a defaulted `stop` parameter; existing callers unchanged.
- The safety stop ends a take through `dispatchHardwareInputCommand` -> `handleCommand("record_stop")` (C1-S01, C1-S11).
- Template: `[pcf8574] bus=1`, `[imu] sync_mode`, `[neorotary4] address=0x49` now match upstream's UI first-run file (`DisplayConfigBridge.cpp:88`, `:204`, `:137 @up`).
- `start()` failure paths undo the new watcher by hand, as C1-S25 does for the other parts.
- `POST /api/config` without `Origin` keeps upstream's last-writer-wins for scripts (`App:8630-8634 @port`).

## Skeptic

Stage 3. Every claim re-read at `@cinemate-port` `01f170c` (`/home/user/Apertar-Core`) and `@upstream-1.6.0` (`/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream`).

| Id | Verdict | Why |
| --- | --- | --- |
| App-2-F1 | stands (matters corrected) | Lines confirmed `App:5089`, `:5098 @port` vs `App:4313-4329 @up`. The UI side changed with it: UI `7c41a27` sets `kDefaultUiWidth=1920` and `hdmi_external_only` fallback true (`Apertar-UI/src/DisplayConfigBridge.cpp:11-12 @port`). So a stock 720x720 camera with no file already boots in 1080p; the Core template repeats it. The fix must be done on both sides |
| App-2-F2 | corrected | Upstream's Core template was just as thin (`[gpio] enabled=false` only, no `[gpio_encoders]`, no `[mpu6050]`, `App:4377-4380 @up`). What was lost is the UI first-run writer (`c9d841f`, deliberate: stop resurrecting a moved file). The `[mpu6050]` values to restore are the UI writer's (`bus=1`, `gyro_range_dps=1000`, `dlpf_hz`, `use_fifo`, ...), not the `bus=10` keys 4d80a35 dropped from `[imu]`. `[gpio]` and `[gpio_buttons]` are aliases in both readers (`GpioInput.cpp:291 @port`, `:407 @up`; `HardwareConfigText.hpp:54`), so the rename is for matching the UI writer and the Controls code, not for function. `[gpio_switches]` chip claim confirmed (`GpioInput.cpp:311-336 @port`: switches section consumes only `enabled` and `switchN_*`). Where corrected (`[imu]` is `App:5112`) |
| App-2-F3 | stands | Confirmed `App:7987-7994`, `BufferBudget.hpp:262-266`, `CC:5018 @port`. Upstream has 0 `static std::function` in `src`; the port has two (`safetyStopHook`, `flushAbortFunction` `BufferBudget.hpp:246`, set from `CC:4629`). CC already passes callbacks to its own parts (`CC:7254` `EventCallback exposureEvent`), so the rework is possible |
| App-2-F4 | corrected (major -> minor, rework narrowed) | `stopClipMerge`, `stopMediaTrim`, `stopStoragePreroll` already exist; only buffer events and safety stop lack their own stop and are inlined in `stopMediaWatcher()` (`App:11054-11077`). Double `stopStoragePreroll()` confirmed but harmless (idempotent, `App:11172-11181`). "Move buffer events into wait()" is wrong: `runBufferEvents` ticks at 250 ms while busy (`App:11049`) for the buffer bar; trim, merge, pre-roll are request-driven cv workers, not periodic. Structure and naming issue, not architecture |
| App-2-F5 | corrected | Confirmed. Missing from the list: `storage_preroll_auto_env` (`App:262 @port`, 7 WCP uses). `raw/sweep-knobs.md` rows 3, 5, 10, 25, 40 reach the same verdict ("remove, twin"). Store move touches handlers (`App:12829-12920`, `:13194`), CC readers and WCP: effort L |
| App-2-F6 | stands | `App:7451-7454`, `:7488-7520 @port`, `ClipProbe.hpp:120-130` confirmed. The bare entry needs no card read: the root `directory_iterator` already gave the name |
| App-2-F7 | stands | `App:7387 @port` confirmed; WCP uses `clip.audio_url` as the `<audio>` source (`WCP:12817`) |
| App-2-F8 | stands (detail) | Tags confirmed at the listed lines. Note: `audio_capture.raw` is upstream's own file (`AudioRecordingSession.cpp:233 @up`); only the `raw2wav.py` pointer is foreign |
| App-2-F9 | corrected | Upstream Core does send display strings (`size_text`, `duration_text` `App:7697`, `:7700 @up`), so "the WebUI formats" is not the Apertar way. The real mismatch is the nesting and the duplicates. Rework: flatten `meta`/`extra` into top-level `*_text` keys, drop the copies |
| App-2-F10 | stands | `CfeHat.hpp:19` `enabled = false`, `App:5315-5317 @port`; upstream's only reader of the section defaults on (`App:3393`, `:3451 @up`) |
| App-2-F11 | corrected | `adopt()` runs every start but writes `adopted-<rev>.conf` once ever (`HardwareConfigStore.cpp:451-463`). History plus adopt is what `014fa22` "restore a replaced file" stands on, and that feature is the reason UI `c9d841f` dropped the UI writer. Dropping them loses a considered feature. Keep; trim only the merge-review path if unused, and document the store for the original developer |
| App-2-F12 | corrected | Confirmed `HardwareConfigText.hpp:1051`. Firmware `[pi5]` also matches CM5, so on CM5 only `[cm5]` lines are missed; `[pi5]` lines are wrongly applied only on Pi 4 / CM4 |
| App-2-F13 | dropped | The path is `options_.mediaRoot` (`App:11495 @port`), the `--media-root` launch option (`main.cpp:61 @up`, default `/media/RAW`), not `[storage] mount_path`. No WebUI/config path reaches the helper. The script accepts only a canonical mount point under `/media/` and runs `fstrim` |
| App-2-F14 | corrected | The summary line logs every start; the "adopted" suffix only on the one start that writes the adopted file. The HAT line logs every start (`App:10861`) |
| App-2-F15 | stands | `App:6337`, `:6394`, `:11630`; `/boot` list `App:6192` vs `hardwareConfigCandidatePaths()` `App:4931-4932 @port`; `boot_copy` `App:6221` has no reader in WCP or UI |

## Final findings

### App-2-F1 [removed-upstream-behaviour, blocker, deliberate yes] Template [display] defaults are an HDMI 1080p rig, not the stock 720x720 panel
- where: `src/ApertarCoreApp.cpp:5081-5098@cinemate-port`
- port: `defaultHardwareConfigTemplate()` writes `ui_width=1920`, `ui_height=1080`, `ui_layout=landscape_large`, `hdmi_external_only=true`, comment names 1920x1080 as default. Together with UI `7c41a27` (`DisplayConfigBridge.cpp:11-12@cinemate-port` fallback 1920x1080, `hdmi_external_only` true).
- apertar way: `src/ApertarCoreApp.cpp:4313,4320-4322,4329@upstream-1.6.0` 720x720, `square`, `hdmi_external_only=false`; UI `DisplayConfigBridge.cpp:14-15,314,323,647-650@upstream-1.6.0`.
- why it matters: A stock camera with no hardware file boots the touch UI in the 1080p layout with the panel handed to HDMI; saving the Config page writes the same. The default describes one contributor's rig.
- rework: Restore the four upstream `[display]` lines and the upstream resolutions comment in `defaultHardwareConfigTemplate()`; revert the UI fallback of `7c41a27` in the same change. An HDMI rig sets its own keys.
- effort S. deliberate yes: `7af9f13` "the 720x720 square layout of the old Hyperpixel screen, which is not what this camera uses"; fork-log rows `7af9f13`, `7c41a27`.

### App-2-F2 [removed-upstream-behaviour, major, deliberate no] With the UI first-run writer gone, the only default lacks chip=auto, input tuning and [mpu6050]
- where: `src/ApertarCoreApp.cpp:5112-5116@cinemate-port`; `src/ApertarCoreApp.cpp:5137-5151@cinemate-port`
- port: UI `c9d841f` removed the first-run writer; Core never writes its template, only shows it. Template has `[gpio] enabled=false`, `[gpio_encoders] enabled=false`, no `chip=`, no `[mpu6050]`. `[gpio_switches]` comment says chip is read "like [gpio]", but `GpioInput.cpp:311-336` reads only `enabled` and `switchN_*` there.
- apertar way: `Apertar-UI/src/DisplayConfigBridge.cpp:57-330@upstream-1.6.0` wrote the first-run file: `[gpio_buttons]` `chip=auto`, `active_low=true`, `pull=up`, `poll_ms=12`, `debounce_ms=60` (:156-166); `[gpio_encoders]` `chip=auto` and tuning (:168-183); `[mpu6050]` `bus=1`, `address=0x68`, `sample_rate_hz`, `gyro_range_dps=1000`, `dlpf_hz`, `use_fifo`, `orientation`, level reference (:206-232). Upstream Core's own template was as thin as the port's (`App:4377-4380@upstream-1.6.0`).
- why it matters: A fresh camera gets no file and the shown default no longer documents `chip=`, the input tuning or the IMU section. The owner's GPIO-chip request needs the definition in the default.
- rework: Fold the upstream UI first-run sections into `defaultHardwareConfigTemplate()`: `[gpio_buttons]` (the alias the UI writer and the Controls code use) with chip/active_low/pull/poll_ms/debounce_ms; `[gpio_encoders]` with chip and its tuning; `[mpu6050]` with the UI writer's values, `enabled=false`. Fix the `[gpio_switches]` comment: "chip, pull, active_low and debounce_ms come from [gpio_buttons]".
- effort S. deliberate no: `c9d841f` removed the writer on purpose (moved file came back) but did not carry its content; `4d80a35` dropped the `[imu]` keys as ignored and did not move them.

### App-2-F3 [mismatch, major, deliberate unknown] Buffer safety stop wired through a process-global std::function hook
- where: `src/ApertarCoreApp.cpp:7987-7994@cinemate-port`; `src/util/BufferBudget.hpp:262-266@cinemate-port`; `src/camera/CameraController.cpp:5018@cinemate-port`
- port: The App constructor body assigns `bufferbudget::safetyStopHook()`, a function-static `std::function` in a header; the DNG write queue calls it under its mutex; `runBufferSafetyStop` waits on a cv. Same idiom: `flushAbortFunction()` (`BufferBudget.hpp:246`, set at `CC:4629`).
- apertar way: C1-S19, `src/ApertarCoreApp.cpp:6783-6785@upstream-1.6.0` `camera_([this](const std::string &eventJson){ publishEvent(eventJson); }, ...)`; CC hands callbacks to its own parts (`CC:7254@cinemate-port` `EventCallback exposureEvent`). Upstream `src` has no `static std::function`.
- why it matters: A hidden second wiring path; captures `this`, outlives App, overwritten by a second instance. The original developer looks for camera-to-app wiring in the initialiser list.
- rework: Add a `std::function<void(const SafetyStopHit&)>` parameter to `CameraController`'s constructor beside the event and preview callbacks, store it, pass it to `DngRecordingQueue` as a member. Delete `safetyStopHook()`. Keep `runBufferSafetyStop` (dispatches `record_stop` through `handleCommand`). Treat `flushAbortFunction()` the same way.
- effort M. Risk: the queue construction path in CC must carry the callback.

### App-2-F4 [mismatch, minor, deliberate unknown] Worker start styles differ and stopMediaWatcher() also stops five other workers
- where: `src/ApertarCoreApp.cpp:8027-8052@cinemate-port`; `src/ApertarCoreApp.cpp:8185-8189@cinemate-port`; `src/ApertarCoreApp.cpp:11054-11077@cinemate-port`
- port: Six workers started with atomic stores and three guard styles (`!running && !joinable`, `!joinable`, none); the guards never fire (stop joins every thread). `stopMediaWatcher()` calls `stopStoragePreroll`, `stopClipMerge`, `stopMediaTrim` and inlines the buffer-events and safety-stop joins. `stop()` calls `stopStoragePreroll()` and then again via `stopMediaWatcher()` (harmless, idempotent).
- apertar way: C1-S17, start = flag under the group mutex then `std::thread(&ApertarCoreApp::runX, this)`, stop = one `stopX()` per worker (`src/ApertarCoreApp.cpp:6821-6825,10988-11014@upstream-1.6.0`).
- why it matters: Thread lifetimes cannot be read from `start()`/`stop()`; the name `stopMediaWatcher` hides five joins.
- rework: Add `stopBufferEvents()` and `stopBufferSafetyStop()`; make `stopMediaWatcher()` stop only the watcher; call every `stopX()` from `stop()` in the C1-S25 order, once. One start style: flag under the group mutex, no guard. Keep all workers as threads (buffer events tick at 250 ms while busy; the others are request-driven).
- effort S.

### App-2-F5 [mismatch, major, deliberate unknown] Env knobs surface in state and WebUI; storage switches split over three stores; App keeps a settings copy
- where: `src/ApertarCoreApp.cpp:260-285@cinemate-port`; `src/ApertarCoreApp.cpp:6399-6404@cinemate-port`; `src/ApertarCoreApp.cpp:8073@cinemate-port`; `src/ApertarCoreApp.cpp:5051-5072@cinemate-port`
- port: `APERTAR_MEDIA_TRIM`, `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE` override settings and surface as `media_trim_env_off`, `storage_preroll_auto_env`, `frames_per_folder_env`, `clip_merge_env_off`; the WebUI greys switches from them. Trim is in `camera_settings.conf`; buffer, frames per folder, merge in hardware `[storage]`; pre-roll in `[media]`, each written by its `set_*` command through the store (`App:12829-12920`). `mediaTrimSetting_` copies the camera setting.
- apertar way: C1-S24 (App reads only `APERTAR_HARDWARE_CONFIG`, `App:4254@upstream-1.6.0`); conv-core-camera R5 (bench knob read where used, never in socket API or settings files; upstream example `LossyDngEncoder.cpp:100,325@upstream-1.6.0`); C1-S08 (`App:7715@upstream-1.6.0`); C1-R2 (command-set persisted switch goes to `camera_settings.conf`).
- why it matters: Experiment knobs become product surface; five related switches live in three stores with env overrides on top. Same verdict in `raw/sweep-knobs.md` rows 3, 5, 10, 25, 40.
- rework: Delete `mediaTrimEnvOff()`, the four `*_env*` state fields and the env inputs of `refreshBufferRequest()`. Read `camera_.settings().mediaTrimEnabled` where the trim decides; delete `mediaTrimSetting_`. Move the command-set storage switches (`set_media_trim`, `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll`) into `camera_settings.conf` per C1-R2; the hardware file keeps `mount_path`, `pcie_controller`.
- effort L (handlers, CC readers and WCP in other units).

### App-2-F6 [removed-upstream-behaviour, minor, deliberate yes] /api/media in a hold hides folders; cDNG size_bytes/file_count change meaning
- where: `src/ApertarCoreApp.cpp:7451-7454@cinemate-port`; `src/ApertarCoreApp.cpp:7488-7520@cinemate-port`; `src/playback/ClipProbe.hpp:120-130@cinemate-port`
- port: In a hold, ProRes, H.264, MLV, timelapse and uncached cDNG folders are skipped (`continue`). The comment promises "the bare entry"; `else if (!held)` is always true. cDNG `size_bytes` = frames + WAVs + `fps-ramp.txt`, `file_count` = frame count.
- apertar way: `discoverMediaLibraryItems` lists every folder with `mediaStatsForPath` over all files: `src/ApertarCoreApp.cpp:6282-6448,5915@upstream-1.6.0`.
- why it matters: Clips vanish from the WebUI list during a take; the shown size undercounts what the download zips (e.g. a `.gcsv` sidecar).
- rework: In a hold, push the bare entry (id, kind, name, type, size `--`) instead of `continue`; delete the duplicate comment and the dead branch. Facts cache sums all files for `size_bytes`; `file_count` stays files.
- effort S. deliberate yes: `f91fafa`, `ab4cc92` (hold rule, card must not be read during a take).

### App-2-F7 [bug, minor, deliberate no] audio_url is JSON-escaped, not URL-encoded
- where: `src/ApertarCoreApp.cpp:7387@cinemate-port`
- port: `"/api/media/file?kind=folder&id=" + escapeJson(id) + "&name=" + escapeJson(f.name) + ".wav"`; the WebUI plays it as is (`WCP:12817`).
- apertar way: `mediaDownloadUrl` uses `urlEncodeComponent` (`src/ApertarCoreApp.cpp:5971,7147-7150@cinemate-port`, same helper at upstream-1.6.0).
- why it matters: A folder named `A&B_001` gives `id=A`, 404 (probable: composable clip names since `014a2bf`). `#`, `%`, `+`, space break it the same way.
- rework: `escapeJson("/api/media/file?kind=folder&id=" + urlEncodeComponent(id) + "&name=" + urlEncodeComponent(f.name + ".wav"))`.
- effort S.

### App-2-F8 [slop, minor, deliberate no] Ticket tags, Cinemate names and a Cinemate tool in comments and operator text
- where: `src/ApertarCoreApp.cpp:5052,5068,5585,6335,6378,6390,6454,6764,7208,7219,7336,7354,7381,7442,7488,8032,8117,8118,8136,8172,10870@cinemate-port`
- port: T21/T37/T39/T42/T47/T50/T51/Q23/R1, "design §4.3" in comments; operator text "Not finalised: audio_capture.raw is on the media (raw2wav.py makes a WAV)"; template text "CineMate style", "CineMate's warm-up"; history narration (`App:5585`, `:8032-8033`).
- apertar way: C1-I14, comments rare, state a hazard or reason, no ticket numbers (10 comment lines in App@upstream-1.6.0). `raw2wav` absent from both upstream trees; `audio_capture.raw` itself is upstream's (`AudioRecordingSession.cpp:233@upstream-1.6.0`).
- why it matters: Internal numbers mean nothing to the original developer; the operator is pointed at a tool an Apertar camera does not have.
- rework: Delete tags and narration. Operator text "Audio not finalised (audio_capture.raw)". Remove product names from the template comments.
- effort S.

### App-2-F9 [new-ground, minor, deliberate yes] clipInfoJson nests meta/extra objects that repeat top-level values
- where: `src/ApertarCoreApp.cpp:7354-7405@cinemate-port`; reader `src/web/WebControlPage.cpp:12743@cinemate-port`
- port: Flat top level plus `holes` (array of pairs), `ramp` (`{"present":true}`|`null`), `meta{...}`, `extra{...}`. `meta.frame_rate` repeats `fps_badge`, `meta.frames` repeats `frame_count`, `extra.sound` repeats `sound_text`.
- apertar way: Upstream replies are flat objects with fixed keys and Core-formatted `*_text` strings (`size_text`, `duration_text` `src/ApertarCoreApp.cpp:7697,7700@upstream-1.6.0`; conv C1 5.5).
- why it matters: A reply shape foreign to the codebase, and the same fact sent twice.
- rework: Flatten: `captured_text`, `resolution_text`, `bit_depth_text`, `duration_text`, `clip_size_text`, `path`, `format_text`, `dropped_text` at top level; drop the copies (`meta.frame_rate`, `meta.frames`, `extra.sound`); `ramp` a boolean; `holes` stays the one array. Update the WCP reader.
- effort S. deliberate yes: `f91fafa`, comment "design §4.3".

### App-2-F10 [mismatch, minor, deliberate yes] C++ [cfexpress_hat] reader defaults to off; upstream's reader defaults to on
- where: `src/ApertarCoreApp.cpp:5296-5346@cinemate-port`; `src/util/CfeHat.hpp:19@cinemate-port`
- port: `CfeHatConfig::enabled = false`; `loadCfeHatConfig()` turns it on only when the section header exists.
- apertar way: the embedded helper, upstream's only reader of the section: `CFE_HAT_ENABLED = True` (`src/ApertarCoreApp.cpp:3393@upstream-1.6.0`), overridden by `enabled` (:3451). Loader shape copies `loadIna219HardwareConfig` (`App:4450-4506@upstream-1.6.0`): fine.
- why it matters: With no hardware file (the UI no longer writes one) the Python helper watches the slot and the C++ watcher does not; a pulled card goes unseen.
- rework: `bool enabled = true;` in `CfeHatConfig`; drop the "section exists" switch.
- effort S. deliberate yes: comment "Off when no hardware config has the section." (`0b1632f`).

### App-2-F11 [new-ground, minor, deliberate yes] HardwareConfigStore replaces one save function; keep it, document it, trim merge review
- where: `src/ApertarCoreApp.cpp:6181-6252@cinemate-port`; `src/ApertarCoreApp.cpp:8136-8154@cinemate-port`; `src/hardware/HardwareConfigStore.cpp@cinemate-port`
- port: All writers (Config page, Controls page, `set_buffer_mode` etc.) go through a store with revisions, history files, `adopt()` (writes `adopted-<rev>.conf` once ever), merge review and 409 codes. Upstream's three checks remain as `checkHardwareConfigText`.
- apertar way: `saveHardwareConfigFile`: checks, `.bak`, `.tmp`+rename (`src/ApertarCoreApp.cpp:5323-5386@upstream-1.6.0`); C1-S07.
- why it matters: More machinery than upstream carries, but history and adopt back the "restore a replaced file" feature (`014fa22`) that motivated dropping the UI writer (`c9d841f`). Several writers justify one store.
- rework: Keep revisions, atomic write, `.bak`, history and adopt. Drop the merge-review path if no caller needs it. Write one paragraph for the original developer (what the store owns, the 409 codes, where history lives).
- effort S. deliberate yes: `5395fa4`, `014fa22`, KB T38.

### App-2-F12 [pi-compat, minor, deliberate no] Validator parses config.txt for [all] and [pi5] only
- where: `src/ApertarCoreApp.cpp:4965-4978@cinemate-port`; `src/hardware/HardwareConfigText.hpp:1037-1051@cinemate-port`
- port: `hardwareConfigFacts()` passes `/boot/firmware/config.txt` to `parseConfigTxt`, which applies only `[all]` and `[pi5]`.
- apertar way: no precedent (upstream has no validator).
- why it matters: On Pi 4 / CM4 a DPI overlay under `[pi4]`/`[cm4]` is missed and `[pi5]` lines are applied; on CM5 `[cm5]` lines are missed (firmware `[pi5]` also matches CM5). Pin warnings are wrong.
- rework: Read `/proc/device-tree/model` in `hardwareConfigFacts()`, pass the board to the parser, honour the matching filters (`[pi4]`, `[pi5]`, `[cm4]`, `[cm5]`, `[all]`).
- effort S.

### App-2-F14 [mismatch, nit, deliberate unknown] Success lines logged at every start
- where: `src/ApertarCoreApp.cpp:8146-8148@cinemate-port`; `src/ApertarCoreApp.cpp:10861@cinemate-port`
- port: Every start logs "<path> <rev>: N errors, M warnings" (plus "adopted, nothing changed" on the one start that writes the adopted file) and the CFE HAT settings.
- apertar way: C1-I13, App logs failures and ignored input only (`App:1863`, `:8954@upstream-1.6.0`).
- why it matters: Log noise and a different habit from upstream App.
- rework: Log the summary only when there are issues or a replaced file; log the HAT line only on change.
- effort S.

### App-2-F15 [duplication, nit, deliberate no] Three now-ms helpers, second /boot list, refreshBufferRequest twice, unread boot_copy
- where: `src/ApertarCoreApp.cpp:6337,6394,11630@cinemate-port`; `src/ApertarCoreApp.cpp:6188-6202,6221@cinemate-port`; `src/ApertarCoreApp.cpp:8034,8145@cinemate-port`
- port: `playbackNowMs`, `trimNowMs`, `clipMergeNowMs` identical; `/boot` paths typed again in `buildHardwareConfigFileJson`; `refreshBufferRequest()` called twice in `start()` with a comment on the order; `boot_copy` has no reader in WCP or UI.
- apertar way: `hardwareConfigCandidatePaths()` lists the `/boot` copies (`src/ApertarCoreApp.cpp:4251-4259@upstream-1.6.0`).
- why it matters: Small drift points.
- rework: One now-ms helper; iterate `hardwareConfigCandidatePaths()` skipping the home path; one `refreshBufferRequest()` before the first worker; drop `boot_copy`.
- effort S.

Dropped: App-2-F13 (helper path is the `--media-root` launch option, not config).
