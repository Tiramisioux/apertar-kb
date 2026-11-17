# Fix list: recording pipeline, encoders, audio, media, playback

Editor's list for the merge review of the cinemate port. Domain: the DNG/MLV write queue, raw copy and sync threads,
safety stop, buffer, pre-roll, media probe/profile/tune, trim, encoders (`src/cdng`, `src/lossydng`, `src/mlv`),
audio (`src/audio`), clip naming, and WebUI clip playback (`src/playback`, the playback routes in App). Units CC-2,
CC-3, CC-6, Encoders-audio, Media-fault-tune, Media-buffer-split, Playback, plus the findings of the sweeps
board-support, stock-behaviour, protocol-security and knobs that lie in these files. Port refs: Core `cinemate-port`
`01f170c`, UI `7ea9afc`. Yardstick: `apertar-conventions.md` (rule ids CAM-, CMD-, PLT-, STY-; older C1-/C2- and
N/S/I ids where the reports used them).

Ids: REC-n, most severe first. `check_core.sh` and `smoke_core.sh` are in `/home/user/build/bin/`.

## Already done on the improvement branch

Branch `claude/awesome-pasteur-qzsiow`, worktree `/home/user/wt/core-work`. Not listed as open.

| Commit | What | Findings closed |
| --- | --- | --- |
| Core `04fe197` | GPIO chip is a Controls setting again, checks per chip | owner request 16 (other domain) |
| Core `05eaafa` | Preview TDN strip only for raw formats and photo mode; H.264 and ProRes load the tuning file unchanged, ProRes derives from it | CC-3-F7, CC-6-F2, X-board-support-15, X-stock-behaviour-6, X-knobs-4 (format half). The default question for raw formats stays open as APP-6 |
| Core `615b48c` | Lossy DNG drops each file's pages after the write again in sync and writer mode | X-stock-behaviour-7, Lossy half of Encoders-audio-F2 |
| Core `0977dd6` | Automatic storage pre-roll off by default | X-stock-behaviour-5, X-knobs-3, pre-roll half of Media-buffer-split-F6 (APP-2) |
| Core `e4246ee` | get_state sends media_state once | Media-fault-tune-F8, X-protocol-security-6 (APP-22) |

## Twins in other lists

Several problems here have an App half in `fix-list-core-app.md`. One commit should fix both halves. Where a twin
exists the item says so; this list holds the CameraController, encoder, audio and playback side.

| REC | Twin | Split |
| --- | --- | --- |
| REC-1 | APP-10, APP-11, HW-36 | REC-1: CC stops reading the hardware file. APP-11: where the keys live (owner) |
| REC-2 | APP-10 steps 3-4, APP-31 | REC-2: the latch, gauge and media profile as controller members. APP-10: App's call sites |
| REC-3 | APP-13 | APP-13 replaces the trim helper; REC-3 makes sure the default is off before that lands |
| REC-9 | APP-13 step 1, APP-30 step 5 | REC-9: which pid gets the signal and the wait under the lock |
| REC-10 | APP-12 | REC-10: CC exclusions; APP-12: the worker enters through handleCommand |
| REC-11 | APP-14 | Same owner decision; REC-11 lists the read sites in CC and CdngEncoder |
| REC-12 | APP-17 | REC-12: comments in CC, encoders, audio, media, playback |
| REC-17 | APP-23 | APP-23: the opt-out flag; REC-17: stills under the floor |
| REC-18 | APP-5 | errorReplyBody's fate decides the `gone` reply |
| REC-30 | APP-38 | APP-38: parsed twice; REC-30: token set and placement |
| REC-37 | APP-42 | Host-test policy is APP-42; REC-37 lists this domain's files |

## Summary

| Id | Title | Kind | Sev | Effort | Rec |
| --- | --- | --- | --- | --- | --- |
| REC-1 | CameraController reads apertar-hardware.conf: [storage] at every take, [camera] Clear HDR ISO caps | mismatch | blocker | L | fix-now |
| REC-2 | Safety stop, flush abort, buffer gauge, buffer setting and media snapshot are process-wide statics and std::function registries, with two polling threads | mismatch | major | L | fix-now |
| REC-3 | Media trim on by default: deleted takes become unrecoverable once trim works on a stock image | stock | major | S | fix-now |
| REC-4 | Lossless cDNG limits and FPS ceilings changed: ISO 1600 on every sensor, auto ISO on IMX585, IMX585 lossless 30 fps cap gone, probe-only ceilings | stock | major | S | ask-owner |
| REC-5 | Playback leaks one TurboJPEG handle per decoded frame | bug | major | S | fix-now |
| REC-6 | Clip-name example stats up to 9999 paths on the media under mutex_ at every settings read and event | bug | major | S | fix-now |
| REC-7 | Write queue stop: copy workers joined without a bound; detached writers outlive the queue | bug | major | S | fix-now |
| REC-8 | A slow but live medium is judged Removed after 5 s and the clip is not finalised | bug | major | S | fix-now |
| REC-9 | Ending a trim signals sudo, fstrim runs on into the take; commands wait up to 3.5 s under commandMutex_ | bug | major | S | fix-now |
| REC-10 | Storage pre-roll is a hidden second take kind; setTuningFile and enterStandby not excluded; unlocked public getter | mismatch | major | M | fix-now |
| REC-11 | Media tune file read inside the recorder and the cDNG encoder | duplication | major | M | ask-owner |
| REC-12 | Ticket ids, dates, clip ids, KB paths, Cinemate hashes and the 'CineMate Log' brand in comments and log lines | slop | major | M | fix-later |
| REC-13 | Per-filesystem writer table changes upstream writer, queue and raw buffer defaults on vfat, NTFS and other | removed | minor | S | fix-now |
| REC-14 | Raw copy pool kept between takes (about 100 MB at 16-bit 4K) | removed | minor | S | fix-now |
| REC-15 | UI automounter unmounts and PCIe-removes the drive on one HAT read | bug | minor | S | fix-now |
| REC-16 | Audio writer queue unbounded; after a write failure the WAV is built from bytes never written | bug | minor | S | fix-now |
| REC-17 | The 1 GiB free-space floor also refuses a single still | removed | minor | S | fix-now |
| REC-18 | Playback routes hand-write JSON error bodies; hold rule built twice and parsed back from a string | mismatch | minor | S | fix-now |
| REC-19 | Sensor probe tells IMX585 by a Model substring; second sysfs subdev walk | mismatch | minor | S | fix-now |
| REC-20 | Ladder refusals are constants that name a wrong menu path; ladder compression handled as strings | mismatch | minor | S | fix-now |
| REC-21 | A/B and restore env knobs left in the recorder and encoders | knob | minor | S | fix-later |
| REC-22 | Per-file writeback, 1 s fsync sweep and syncfs at stop: keep, but fix the shared cv and the DONTNEED fallback | new-ground | minor | S | keep-and-document |
| REC-23 | Raw write path changed for every board and run on one CM5 | board | minor | M | fix-later |
| REC-24 | Clip viewer refuses the 8-bit DNGs Core writes | bug | minor | S | fix-later |
| REC-25 | FORMAT row guesses the lossy ratio from the clip name | bug | minor | S | fix-later |
| REC-26 | Playback memory: JPEG caches never trimmed, unused slot buffer, wrong memory comment | board | minor | S | fix-later |
| REC-27 | Playback text helpers and clocks duplicate App's | duplication | minor | S | fix-later |
| REC-28 | Frame-number rule in two C++ copies | duplication | minor | S | fix-later |
| REC-29 | Second /proc/mounts parser beside upstream's | duplication | nit | S | fix-later |
| REC-30 | Clip-name template: constant tokens, src/util placement, second sensorName | new-ground | minor | S | fix-later |
| REC-31 | Early safety-stop recording event carries a stale lastError_ | bug | minor | S | fix-later |
| REC-32 | Safety stop ends a take; record during the flush discards queued frames | new-ground | minor | S | keep-and-document |
| REC-33 | Dropped-frame count in state and event; unused fault field | new-ground | nit | S | keep-and-document |
| REC-34 | Extra settings event helper for cdng_log_applied | mismatch | nit | S | fix-later |
| REC-35 | wavSampleRate rejects RF64 | bug | nit | S | fix-later |
| REC-36 | Audio drift fit, 10 ms ALSA period, MLV black level differ from 1.6.0 | new-ground | nit | S | keep-and-document |
| REC-37 | Host tests and desk tools of this domain | new-ground | nit | S | keep-and-document |
| REC-38 | Placement and namespace names (BufferBudget, StoragePreroll, UI clipframes) | mismatch | nit | S | fix-later |
| REC-39 | Diagnostic response headers no page reads | slop | nit | S | fix-later |
| REC-40 | GET /api/buffer polled at 4 Hz beside /api/state | new-ground | minor | S | keep-and-document |

---

## REC-1. CameraController reads apertar-hardware.conf: [storage] at every take, [camera] Clear HDR ISO caps

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | blocker | L | yes | fix-now | Media-buffer-split-F1, CC-2-F2, CC-3-F2, CC-2-F1, X-knobs-13, X-knobs-7 |

**Where.** `src/camera/CameraController.cpp:2933-2984` (CameraSection, loadCameraSection), `:2986-3007` (loadBufferConf), `:4285-4313`, `:4297`, `:5505`; `src/util/BufferBudget.hpp:97-194`; `src/ApertarCoreApp.cpp:272-284`, `:5074-5079` @cinemate-port.

**Problem.** At every take `DngRecordingQueue` opens the hardware file (its own candidate path list, twice in CC) and parses [storage] buffer, buffer_stop_percent, RAM fraction/floor/max and frames_per_folder. App already parses the same section from `configStore()` and publishes `framesPerFolderRequest()`, which the queue ignores, so state and recorder can disagree after a save. A second CC parser reads [camera] clear_hdr_iso_max_12bit/16bit, driver gain facts turned into operator config, with no command and no UI.

**Apertar way.** CAM-19: the camera side never reads apertar-hardware.conf (0 hits in `src/camera` @upstream-1.6.0). CAM-17: per-take inputs that are not camera settings travel as option structs App builds: `startRecording(const AudioRecordingOptions &, const GyroRecordingOptions &)` (`src/camera/CameraController.hpp:77-78`, `include/apertar/core/Types.hpp:184,199`, `src/ApertarCoreApp.cpp:10626-10633` @upstream-1.6.0). Sensor limits are literals in the sanitiser: `settings.iso = std::min<uint32_t>(settings.iso, 800u);` (`CC:2483` @upstream-1.6.0).

**Rework.**

1. `include/apertar/core/Types.hpp`: add `struct StorageRecordingOptions { BufferMode buffer; unsigned stopPercent; unsigned framesPerFolder; };` beside `GyroRecordingOptions`.
2. `CameraController::startRecording` gains a third defaulted parameter `const StorageRecordingOptions &storageOptions = {}` and hands it to `DngRecordingQueue::startAtFolder` (and `planQueueBuffer`), copying the Gyro path.
3. App's `record_start` block builds the struct from what App already parses (`refreshBufferRequest` data, App:272-284), like `gyroOptions` at App:10633@upstream. If the owner picks camera_settings.conf in APP-11 (answer B), the struct is not needed: the fields are `CaptureSettings` members and the queue reads `settings_`.
4. RAM fraction, floor and max fraction become env-only, read at the point of use with `unsignedEnvValue` (CAM-24); they leave the hardware template and README.
5. Delete `loadBufferConf`, both inline candidate path lists and the `parseBufferConf` call in CC.
6. Clear HDR caps: `constexpr uint32_t kClearHdrMaxIso12 = 720, kClearHdrMaxIso16 = 1585;` next to `kLosslessMaxIso` (CC:3100). `clearHdrIsoCap` returns them. Delete `CameraSection`, `loadCameraSection`, `cameraSection`, the [camera] block in `defaultHardwareConfigTemplate()` (App:5074-5079) and its README text.
7. Note for the coordinator: APP-10 step 1 makes CameraController the [storage] owner and parser. That keeps a hardware-file reader in CC and breaks CAM-19. This item puts the parse in App and passes the result in; APP-10 step 1 should follow it.

**Owner decision.** Shared with APP-11 (keys stay in [storage] or move to camera_settings.conf). Either answer keeps this item's core: CC stops reading the file. Recommendation: whichever APP-11 picks, the camera receives values, it never opens the file.

**Check here.** `check_core.sh /home/user/wt/core-work core-work both tests`; `grep -n 'apertar-hardware\|hardwareConfig' src/camera/*.cpp` gives 0 hits; `--simulate`: set_buffer_mode ram then a sim take logs `buffer=ram` on the `recording clip:` line.

**Needs the Pi.** cDNG take with buffer=ram and frames_per_folder=1000: `journalctl -u apertar-core | grep 'recording clip'` shows the values; part folders appear on the card.

**Risk.** An operator who edited [camera] ISO keys loses them (none recorded).

**Depends on.** APP-11 (answer), APP-10.

---

## REC-2. Safety stop, flush abort, buffer gauge, buffer setting and media snapshot are process-wide statics and std::function registries, with two polling threads

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | L | unknown | fix-now | CC-3-F1, CC-2-F7, CC-2-F8, Media-buffer-split-F2, Media-buffer-split-F3, Media-fault-tune-F3 |

**Where.** `src/camera/CameraController.cpp:4169-4186` (frameBufferGauge), `:4211`, `:4271`, `:4594`, `:4611-4636`, `:5011-5022`, `:1467`, `:7735`, `:10543`; `src/util/BufferBudget.hpp:221-334`; `src/util/StoragePreroll.hpp:221-271`; `src/util/MediaProbe.hpp:257-290`; `src/util/MediaProfile.hpp:212-234`; `src/cdng/CdngEncoder.cpp:91`; `src/ApertarCoreApp.cpp:286-299`, `:7988-7995`, `:10993-11050`, `:11083-11110` @cinemate-port.

**Problem.** Per-take state lives in function-local statics in headers: `frameBufferGauge()`, `safetyStopState()`, `flushAbortFunction()` (holds the queue's `this`), `safetyStopHook()` (assigned in App's constructor), `bufferSettingStorage()`, `cachedMediaSnapshot`, `configuredMediaRoot()`. App calls `abortSafetyStopFlush()` around the controller, and CameraController.hpp shows none of it. Two App threads poll: `runBufferEvents` (250 ms / 1 s) and `runBufferSafetyStop` (cv with a 100 ms backstop).

**Apertar way.** CAM-27 and CMD-18: cross-thread signals are owned objects passed by pointer. `RecordingDropWarning recordingDropWarning_;` is a controller member (`CameraController.hpp:113` @upstream-1.6.0) handed to the queue: `explicit DngRecordingQueue(RecordingDropWarning *warning = nullptr)` (`CC:3251` @upstream-1.6.0). A background condition that ends a take is latched and polled by App's 1 Hz `wait()` loop, which dispatches through `handleCommand` (`App:7021-7053` @upstream-1.6.0, `src/util/RecordingFailure.hpp`). Function-local statics hold only process-lifetime caches (`captureSettingsPersister`, CC:885-889@upstream).

**Rework.**

1. New `src/util/RecordingSafetyStop.hpp` shaped like `RecordingDropWarning.hpp`: atomics `active`, `stopPercent`, `flushDiscarded`, a `requested` latch, and the five gauge counters now in `FrameBufferGauge`.
2. `CameraController` gets a member `RecordingSafetyStop recordingSafetyStop_;` beside `recordingDropWarning_`; `DngRecordingQueue(RecordingDropWarning *, RecordingSafetyStop *)`.
3. Public `CameraController::abortSafetyStopFlush()` that sets the atomic and does not take `mutex_` (the drain holds it during stop); one header comment line says so. Public `takeSafetyStopRequest()` and the existing `frameBufferStatus()` read the member.
4. App: in `wait()`, next to `camera_.checkRecordingFailure()`, call `takeSafetyStopRequest()` and dispatch `record_stop` through `handleCommand`; publish the buffer event there at 1 Hz. Delete `runBufferEvents`, `runBufferSafetyStop` and their members. If the bar must be smoother see REC-40.
5. Media profile: `CameraController::setMediaProfile(const MediaProfile &)` under a small dedicated mutex (not `mutex_`), called from `runMediaWatcher` where `mediaProfile_` changes (App:10935-10940). `rawCameraBufferCount` and `recorder_.setMediaProfile` (CC:7735) use that copy; CdngEncoder gets the page-cache mode through its options.
6. Delete `flushAbortMutex`, `flushAbortFunction`, `registerFlushAbort`, `unregisterFlushAbort`, `safetyStopHook`, `safetyStopState`, `frameBufferGauge`, `bufferSettingStorage`, `cachedMediaSnapshot*`, `updateCachedMediaSnapshot`, `configuredMediaRoot`, `mediaExtraRawBuffersForConfiguredRoot`. BufferBudget.hpp keeps only `planBuffer` and its pure maths (CAM-4).

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests` (buffer_budget_test still passes); `grep -n 'static std::function\|static std::optional<MediaSnapshot>' src` gives 0; `--simulate` ram-mode take with `APERTAR_CDNG_BUFFER_STOP_PERCENT=5` ends by itself and the journal shows `record_stop` from the supervisor.

**Needs the Pi.** 16-bit 4K cDNG, buffer=ram, slow card: the safety stop fires once within about 1 s, the clip closes; `journalctl -u apertar-core | grep -i safety`.

**Risk.** Reaction goes from 100 ms to 1 s; at 90 % of a GiB-sized budget that is seconds of headroom. Say so in the commit. Before the first watcher cycle the media profile is empty, which gives upstream defaults.

**Depends on.** REC-1.

---

## REC-3. Media trim on by default: deleted takes become unrecoverable once trim works on a stock image

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | fix-now | Media-buffer-split-F6 (trim half), X-stock-behaviour-11 |

**Where.** `include/apertar/core/Types.hpp:140`; `src/camera/CameraController.cpp:889-890`, `:976`; `src/ApertarCoreApp.cpp:8077`, `:11447`, `:11467` @cinemate-port (same @core-work).

**Problem.** `bool mediaTrimEnabled = true;`. The trim runs after any delete of 1 GiB or more, at every mount and after a format, so deleted takes cannot be undeleted. Today a stock image has no helper, so nothing is trimmed and only the switch lies. APP-13 replaces the helper with a direct `sudo -n fstrim`, which works on a stock image (pi has NOPASSWD: ALL). From that commit on, a stock camera discards free space by itself.

**Apertar way.** 1.6.0 never discards free space and never writes to the media without an operator action. The port's own pre-roll default was turned off for the same reason (0977dd6).

**Rework.**

1. `Types.hpp:140`: `bool mediaTrimEnabled = false;` with the comment 'Off by default: trimmed space cannot be undeleted.'
2. Loader at CC:889-890 stays (an existing `media_trim=true` keeps working).
3. App: `mediaTrimSetting_` already starts from `camera_.settings()` (App:8077); nothing else.
4. README storage paragraph (lands with APP-18): what turning trim on costs.
5. Land this before or with APP-13 step 1.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`; `--simulate` with no camera_settings.conf: get_state `media_trim_enabled=false`.

**Needs the Pi.** Fresh settings, mount a card, delete a 2 GB clip: `journalctl -u apertar-core | grep -i trim` shows no fstrim.

**Risk.** The rig that relies on trim sets `media_trim=true` once.

**Depends on.** none; ordering with APP-13.

---

## REC-4. Lossless cDNG limits and FPS ceilings changed: ISO 1600 on every sensor, auto ISO on IMX585, IMX585 lossless 30 fps cap gone, probe-only ceilings

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | ask-owner | CC-2-F3, X-stock-behaviour-3, X-stock-behaviour-9, X-stock-behaviour-10, CC-2-F10, CC-2-F11, CC-2-F13 (fps comments) |

**Where.** `src/camera/CameraController.cpp:3098-3158`, `:3389-3434`, `:3464-3491`, `:8634-8639`; `src/camera/FpsCeiling.hpp:10-47`; `tools/fps_ceiling_test.cpp` @cinemate-port.

**Problem.** Confirmed in code: `constexpr uint32_t kLosslessMaxIso = 1600;` for every sensor ('on Patrik's request', measured on IMX585 only). `isoAuto` is forced off only for non-IMX585 ('Other sensors are unchecked'). The IMX585 lossless fps cap is the mode maximum unless `APERTAR_LOSSLESS_FPS_LIMIT`. `resolveSensorMaxFps` returns the probe alone; fork main used `min(table, probe)`. A stock D1 now offers and accepts 4K lossless at the driver's figure (about 60, probable), and IMX477 ceilings follow its driver instead of Apertar's measured table. Around this sit four one-line wrappers in their own header, a `backendMaximumFps` that returns nullopt for every input, two restore switches and stale comments ('the 16-bit 25 is backendMaximumFps()').

**Apertar way.** `enforceLosslessCaptureLimits` (`CC:2470-2491` @upstream-1.6.0): `settings.iso = std::min<uint32_t>(settings.iso, 800u); settings.isoAuto = false;` and IMX585 `maximumFps = 30.0`. Fork main: `probed ? std::min(table, *probed) : table` (`CC:2769` @main). CAM-21: sensor limits applied silently in the sanitiser.

**Rework.**

1. `enforceLosslessCaptureLimits` and `losslessMaximumFps`: restore 800, `isoAuto = false` for every sensor, IMX585 lossless 30.
2. If the owner keeps the IMX585 relaxation (answer B): `switch (sensorFamily)` gives 1600 and auto ISO for `SensorFamily::Imx585` only, 800 / manual for the rest, in both `enforceLosslessCaptureLimits` and `maximumIsoForSettings`; IMX585 lossless fps = mode maximum. Move it into its own commit with the measurement (C0013, 2026-10-27 temp run) in the message.
3. `maximumSupportedFpsForResolution`: write `probed ? std::min(table, *probed) : table` inline, as fork main; IMX283 keeps its floor table.
4. Delete `FpsCeiling.hpp`, `tools/fps_ceiling_test.cpp`, `backendMaximumFps`, `applyBackendCap`, `fpsLimitTableOnly` (`APERTAR_FPS_LIMIT`), `imx283ProbeFpsOnly` (`APERTAR_IMX283_PROBE_FPS`) and `losslessFpsOverride`. If a bench override stays, it is `unsignedEnvValue("APERTAR_LOSSLESS_FPS_LIMIT", 30, 1, 120)` at use (CAM-24).
5. If auto ISO stays for IMX585 lossless, Core publishes `iso_auto_allowed` (CAM-18 runtime field) and the WebUI/touch UI read it instead of their own rule (X-stock-behaviour-10; tell the WCP and UI editors).
6. Fix the comments at CC:3378 and CC:3481-3485.

**Owner decision.** Restore 1.6.0's lossless policy (800, manual ISO, 30 fps on IMX585) and min(table, probe) ceilings (A), or keep the IMX585 relaxation behind a per-sensor switch (B)? Recommendation: A for the ceilings in any case; for IMX585 lossless, B only with the measurement in its own commit. A costs the IMX585 rig 1600/auto/60 unless it sets env knobs. B asks the original developer to accept a product-policy change on one rig's numbers.

**Check here.** `check_core.sh ... both tests`; `--simulate` IMX585 sim with lossless cDNG: set_iso 1600 returns iso 800 (A) and get_state `fps_max` = 30.

**Needs the Pi.** Stock D1 (IMX585): lossless 4K, the fps picker tops at 30; IMX477 4K lossless: ISO caps at 800 and Auto is refused.

**Risk.** The Clear HDR tuning work assumed 1600 on IMX585; keep that path under B.

---

## REC-5. Playback leaks one TurboJPEG handle per decoded frame

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | no | fix-now | Playback-F2 |

**Where.** `src/playback/PlaybackFrames.cpp:92` @cinemate-port: `thread_local tjhandle handle = tjInitCompress();` with no `tjDestroy` (confirmed).

**Problem.** The decode runs on the web connection thread. WebServer starts one detached thread per connection and serves one request per connection (`WebServer.cpp:279-298`, `Connection: close` at :136). Every frame decoded rather than served from cache creates a handle and its libjpeg state, and the thread exits without freeing it. Core's memory grows with every scrub and play session; on a 2 GB board that ends in OOM pressure during a later take.

**Apertar way.** `struct TurboJpegCompressor` whose destructor calls `tjDestroy(handle)`, used as `thread_local TurboJpegCompressor compressor;` (`App:4108-4134` @upstream-1.6.0; still at App:4781-4807 @cinemate-port).

**Rework.**

1. Move `TurboJpegCompressor` unchanged from `ApertarCoreApp.cpp` into a small header next to its users (`src/playback/TurboJpegCompressor.hpp` or a static helper exported from App), keeping the `#if APERTARCORE_HAS_TURBOJPEG` guard.
2. `encodeRgbJpeg` uses `thread_local TurboJpegCompressor compressor;` and `compressor.handle`. Delete the raw `tjhandle`.
3. App's own use includes the same header.

**Owner decision.** None.

**Check here.** Build both ways; `--simulate` with a sim DNG clip: scrub 500 frames with `curl` in a loop and watch `ps -o rss` of apertar-core stay flat.

**Needs the Pi.** 5 minutes of scrubbing a 4K clip in the WebUI: `ps -o rss -C apertar-core` before and after differs by less than the JPEG caches (about 32 MB).

**Risk.** Low; same encoder settings.

---

## REC-6. Clip-name example stats up to 9999 paths on the media under mutex_ at every settings read and event

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | no | fix-now | CC-6-F1 |

**Where.** `src/camera/CameraController.cpp:12592` (settings()), `:12866` (emitSettingsEventLocked), `:11825-11833`, `:1191-1204`; `src/util/ClipName.hpp:287-294` @cinemate-port (confirmed).

**Problem.** `settings()` and `emitSettingsEventLocked()` call `fillClipNameExampleLocked` -> `nextClipNumber`, which calls `std::filesystem::exists` for clip 1..9999 until a name is free, with `mutex_` held. It runs on every setter reply and every state poll (WebUI every 1 s per client). With 400 takes on the card that is about 400 stat calls per poll, also during a take. On a hung or pulled USB mount a stat blocks, and `checkRecordingFailure`, `record_stop` and every setter wait on `mutex_`.

**Apertar way.** The clip folder is looked up once, at take start: `clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);` (`CC:5548` @upstream-1.6.0). `settings()` does no I/O (`CC:8566-8573` @upstream-1.6.0). CAM-10: nothing slow under `mutex_`.

**Rework.**

1. Remove `fillClipNameExampleLocked` from `settings()` and `emitSettingsEventLocked()`.
2. Add a member `std::string clipNameExample_`; compute it outside `mutex_` (copy template and root under the lock, probe, store under the lock) in `setClipNameTemplate`, after take start and stop, and when App reports a mount change.
3. `settings()` copies `clipNameExample_` into the runtime field (CAM-18).
4. The WebUI composer keeps `preview_clip_name` (CC:11857-11876) for live typing.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests` (clip_name_test); `--simulate` with 400 dummy clip folders: `strace -c -e trace=newfstatat -p <pid>` during 10 s of WebUI polling shows no stats per poll.

**Needs the Pi.** Card with many clips, WebUI open, pull the card: `record_stop` from a button still answers within 2 s.

**Risk.** The example may be stale for one poll after an external card change; acceptable.

---

## REC-7. Write queue stop: copy workers joined without a bound; detached writers outlive the queue

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | no | fix-now | CC-2-F9, CC-3-F4 |

**Where.** `src/camera/CameraController.cpp:4386-4388`, `:4441-4500`, `:4453`, `:4691-4707`, `:4959-4974`, `:5164-5174`, `:4208-4212` @cinemate-port.

**Problem.** (1) `stop()` calls `stopCopyWorkers()`, a plain join, before the bounded writer wait. Copy threads start with `copyThreads_.emplace_back`, not `spawnWorker`, and `enqueue()` on a copy thread calls `ensurePartFolder()` -> `::mkdir` on the medium. With frames_per_folder > 0 and a card pulled while a copy worker crosses a part boundary, mkdir blocks and `stop(true)` hangs with the controller and command locks held: the hang 0b1632f set out to remove (probable; off by default). (2) A dead-medium stop detaches blocked writers. The destructor's second `stop()` returns early (`active_` false), and the threads later touch `exitMutex_` and `mutex_` of a freed queue (probable).

**Apertar way.** Upstream joins every writer in stop() (`CC:3404-3409` @upstream-1.6.0) and creates folders before the take. The bounded stop is port ground and needed (0b1632f); it must cover every thread.

**Rework.**

1. Create part folders on a writer thread (the writer already waits on the medium and is covered by the bounded wait), or start copy threads through `spawnWorker` and stop them inside the same bounded wait.
2. `~DngRecordingQueue`: wait on `exitCv_` for `liveWorkers_ == 0` with a bound (the dead-medium limit) and log `ApertarCore recording: detached writers still running` if it runs out; or move the state the threads touch into a `shared_ptr` block each thread captures.

**Owner decision.** None.

**Check here.** Build; host: a small test that constructs a queue with a fake blocking write and destroys it (optional). Code read: every thread started in the queue is counted by `liveWorkers_`.

**Needs the Pi.** frames_per_folder=100, cDNG take, pull the card: stop returns within the dead-medium limit; quit Core 10 s later without a crash (`journalctl -u apertar-core -b | grep -i 'segfault\|detached'`).

**Risk.** Moving mkdir to a writer adds one stat per part folder on a writer; negligible.

---

## REC-8. A slow but live medium is judged Removed after 5 s and the clip is not finalised

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | yes | fix-now | CC-3-F8, Media-fault-tune-F10 |

**Where.** `src/camera/CameraController.cpp:4441-4500` (stall rule :4476-4483), `:4833-4842`, `:4859-4861`, `:5372-5377`, `:5424-5432` @cinemate-port.

**Problem.** A full queue with no write for 5 s (`APERTAR_WRITE_STALL_MS`), or the same stall while `stop()` waits, calls `failRecording(..., MediaFault::Removed)`. That sets `mediumGone_`: the MLV header patch is skipped, `syncToMedium` is skipped, writers may be detached, and the finalise steps (rename, fsync) do not run even when the writers return. An untrimmed NVMe or USB disk that pauses 5-10 s (d44b177 documents such stalls) leaves an unfinalised clip although the medium is alive. Footage loss, probable.

**Apertar way.** CAM-33: a write failure ends the take with its first error; there is no 'medium gone' state upstream. The bounded stop is needed (0b1632f), so the fix keeps it.

**Rework.**

1. Add `MediaFault::Stalled` beside `Removed` in `src/util/MediaFault.hpp`. The in-take stall rule (queue full, :4837) fails the take with `Stalled`, which does not set `mediumGone_`.
2. At stop: a stall alone is not a fault. Mark the medium gone only when the writers are still stuck after a separate stop limit (`unsignedEnvValue("APERTAR_DEAD_MEDIUM_STOP_MS", 15000, ...)`, already a port knob), or when the media watcher reports Removed or Error.
3. Writers that return before that limit go through the normal finalise (MLV header patch, rename, folder fsync).
4. Do not make the wait unbounded.

**Owner decision.** None.

**Check here.** Build; code read of `failRecording` callers: only the watcher path and the stop limit pass `Removed`.

**Needs the Pi.** Record MLV to a USB HDD, `kill -STOP` the usb-storage kworker or throttle with `ionice` + a parallel `dd` so writes pause 8 s at stop: the clip is finalised (`mlv_dump` reads the frame count). Pull the card mid-take: stop still returns within the limit.

**Risk.** A hung medium the probe has not seen holds the stop locks up to the new limit.

---

## REC-9. Ending a trim signals sudo, fstrim runs on into the take; commands wait up to 3.5 s under commandMutex_

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | no | fix-now | Media-buffer-split-F5, Media-buffer-split-F7 |

**Where.** `src/ApertarCoreApp.cpp:11941-11963` (waitForMediaTrim), `:6432` (execl sudo), `:12614-12619`; `scripts/apertar-media-trim:75-78` @cinemate-port (confirmed).

**Problem.** `waitForMediaTrim` waits 2 s, then SIGTERM and SIGKILL to the `sudo` pid. sudo relays SIGTERM to the script's sh only; the foreground `timeout 20 /usr/sbin/fstrim` is not exec'd and GNU timeout runs in its own process group, so fstrim gets nothing. SIGKILL is never relayed. Core logs 'ended a trim' and starts the take while fstrim holds the filesystem up to 20 s: the stall the wait exists to prevent (probable). Meanwhile every socket, WebUI and button command waits behind `commandMutex_` for up to 3.5 s.

**Apertar way.** Upstream wraps sudo in `/usr/bin/timeout` and the caller owns the timeout process (`App:1541-1545` @upstream-1.6.0). Upstream refuses with a sentence instead of waiting on a background media job: 'Wait for the media speed test to finish first.' (`App:9108-9110` @upstream-1.6.0).

**Rework.**

1. With APP-13 step 1: fork/exec `/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <root>`; store the `timeout` pid (owned by pi) in `mediaTrimPid_`. timeout forwards SIGTERM to its child.
2. `waitForMediaTrim`: on a take command send SIGTERM at once (no 2 s grace, APP-30 step 5), wait at most 500 ms, then go on. Keep the 5 s hold-off of new trims.
3. Stop-gap if APP-13 is not landed: `exec timeout 20 /usr/sbin/fstrim -v "$MNT"` in the script so sudo's relay reaches fstrim.
4. One handoff line: record always starts, a running trim is ended first.

**Owner decision.** None.

**Check here.** Build; host: run the fork/exec helper against `/bin/sleep 30` in place of fstrim and confirm `kill(pid, SIGTERM)` ends sleep (`pgrep sleep` empty).

**Needs the Pi.** Start a trim on a large card, press record within 1 s: `pgrep -a fstrim` is empty when the take starts; the command answered within 0.6 s.

**Risk.** None beyond APP-13's.

**Depends on.** APP-13.

---

## REC-10. Storage pre-roll is a hidden second take kind; setTuningFile and enterStandby not excluded; unlocked public getter

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | CC-6-F3, CC-6-F8 |

**Where.** `src/camera/CameraController.cpp:11993`, `:12038-12194`, `:12131-12136`, `:12745`, `:11500-11560`, `:10593-10615`; `src/camera/CameraController.hpp:226`; `src/ApertarCoreApp.cpp:12588-12592` @cinemate-port.

**Problem.** `startStoragePreroll` starts a raw take while `recording_` stays false and `state_` stays Ready, changes `settings_` with commit=false, keeps a copy in `prerollSaved_`, and waits up to 1 s in `waitForFramePeriod` with `mutex_` held. The exclusions are split: CC checks `prerollTake_` in `startRecording`, `applySettingsLocked` and `setClipNameTemplate`; App checks a list of 9 command names. `setTuningFile` reconfigures through `session_->reconfigure` with no check, and `set_tuning_file` is not in App's list; `enterStandby` has no check in CC. `storagePrerollError()` is public and reads without `mutex_`, the only reason `prerollTake_` is atomic. The default is now off (0977dd6), which lowers exposure but leaves the manual command.

**Apertar way.** CAM-32: each capture entry in CC refuses the others with a sentence (`CC:8224, 8244, 8329, 7680, 8048, 8608` @upstream-1.6.0). CAM-10: every public method takes `mutex_` first (`recordingError()` does).

**Rework.**

1. Add the `prerollTake_` refusal, with the existing sentence 'Storage pre-roll is running. One moment.' (CC:11993), to `enterStandby`, `capturePhoto`, `startTimelapse` and `setTuningFile`.
2. Delete App's 9-name list at App:12588-12592; CC's refusals cover socket, WebUI and buttons alike.
3. `storagePrerollError()` takes `mutex_` like `recordingError()`; `prerollTake_` becomes a plain bool; drop the `.load()` at CC:12877.
4. Remove the 1 s `waitForFramePeriod` under `mutex_` once the fps override (CC-4-F3, camera editor) is gone.
5. Timer and finish move as APP-12 says (CC thread shaped like `timelapseLoop`, CC:8447@upstream).

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`; `--simulate`: `storage_preroll` then `set_tuning_file` and `enter_standby` within 2 s both answer the pre-roll sentence.

**Needs the Pi.** Manual pre-roll, then set a tuning file during it: refused; after it, the camera is Ready on the original settings.

**Risk.** The pre-roll must stay invisible to the UIs (no REC, no tally).

**Depends on.** APP-12.

---

## REC-11. Media tune file read inside the recorder and the cDNG encoder

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | major | M | yes | ask-owner | Media-fault-tune-F1, CC-2-F6, Encoders-audio-F1, X-knobs-6, Media-fault-tune-F13 |

**Where.** `src/util/MediaTune.hpp:1-318`; `src/util/MediaProfile.hpp:172-181`, `:195`, `:230-234`; `src/camera/CameraController.cpp:1458-1470`, `:4316-4327`, `:4364-4365`, `:4718`; `src/cdng/CdngEncoder.cpp:7,21,84-108`; `scripts/apertar-tune`; `config/apertar-media-tune.conf` @cinemate-port.

**Problem.** Write-path knobs resolve env > /run override > ~/apertar-media-tune.conf > default, with their own key names and per-medium sections. A file-format class (CdngEncoder) includes MediaProfile.hpp and parses the tune file for the page-cache mode. CC reads it per take for sync_ms, once per process for writeback, and for the raw buffer count and writer topology. The template sets `[default] raw_buffers = 8`, so `apertar-tune init` doubles SDR raw buffers. The startup summary logs only the first resolution, often before a medium is mounted. The env names it wraps are port additions too.

**Apertar way.** CAM-24 / R8: a bench knob is an env var read at the point of use; in an encoder a read-once static lambda (`configuredLosslessTileRows`, `src/cdng/CdngEncoder.cpp:51-66` @upstream-1.6.0). The one bench file upstream has is `tuningOverride(name)`: env first, else `NAME=VALUE` from `/home/pi/.apertar-tuning` with the same APERTAR_* names, re-read at clip open (`src/prores/ProresEncoder.cpp:779-818` @upstream-1.6.0, confirmed).

**Rework.**

1. Answer A: move `tuningOverride()` from `ProresEncoder.cpp` into `src/util/TuningOverride.hpp` (header-only, CAM-4); `unsignedEnvValue` and `boolEnvValue` in CC call it, and ProresEncoder includes the header.
2. `CdngEncoder.cpp`: `dngPageCacheDrop()` reads `tuningOverride("APERTAR_DNG_DONTNEED")` in the `configuredLosslessTileRows` shape with silent fallback; delete the `mediaTuneForConfiguredRoot` branch and the `util/MediaProfile.hpp` and `<iostream>` includes. Drop the duplicate include in `LossyDngEncoder.cpp` (its header already includes CdngEncoder.hpp).
3. CC: `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_CAMERA_BUFFERS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES` read through `unsignedEnvValue`/`boolEnvValue` at take start, effective values on the `recording clip:` line.
4. Per-medium defaults stay as code in `writerSettingsFor()` (see REC-13 for the values).
5. Delete `MediaTune.hpp`, `mediaTuneForConfiguredRoot`, the override path, `scripts/apertar-tune`, `config/apertar-media-tune.conf`, `tune_override=` in the clip log line and the README section (APP-14 step 3).
6. Answer B: keep the file, drop the /run override and the CLI; the encoder still gets the mode through its options (REC-2 step 5), not by reading a file.

**Owner decision.** Same question as APP-14: you asked for the media-tune file on 2026-11-02. Replace it with upstream's `.apertar-tuning` (A) or keep it trimmed and documented (B)? Recommendation: A. A loses per-medium override sections and the editor script; test nights write `.apertar-tuning` lines instead. B keeps a second tuning dialect and a file read from inside an encoder that the original developer must accept.

**Check here.** `check_core.sh ... both tests`; `--simulate`: a line `APERTAR_DNG_WRITEBACK=0` in `~/.apertar-tuning` changes the next sim take's `recording clip:` line without restart.

**Needs the Pi.** A/B two cDNG takes with and without a `.apertar-tuning` line; the log line shows both values.

**Risk.** Campaign scripts (b1-arm.sh and others) must write `.apertar-tuning`.

**Depends on.** APP-14 (decision), REC-2.

---

## REC-12. Ticket ids, dates, clip ids, KB paths, Cinemate hashes and the 'CineMate Log' brand in comments and log lines

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | major | M | no | fix-later | Playback-F1, CC-2-F12, CC-2-F13, CC-2-F19, CC-2-F20, CC-3-F10, CC-6-F6, Encoders-audio-F3, Encoders-audio-F4, Media-fault-tune-F11, Media-buffer-split-F8 |

**Where.** Every `src/playback/*.hpp` line 3 essay; `src/camera/CameraController.cpp:3025, 3034, 3070, 3098-3099, 3154, 3428-3430, 3963, 3985, 4008, 4041, 4318, 4357, 4596 (assert), 4674-4734, 4888, 5546, 5591, 11943-11944, 12038-12050`; `src/cdng/CdngEncoder.hpp:13-16, 44`; `src/cdng/LogCurve.hpp:13,18,48,63`; `src/lossydng/LossyDngEncoder.cpp:51`; `src/audio/AudioRecordingSession.cpp:207-211, 382, 588-590, 750-753`; `src/audio/TimestampedAudioCapture.cpp:194-198`; `src/util/MediaProfile.hpp:21,25,133,141,221`; `src/util/MediaProbe.hpp:23,179`; `src/cdng/FramePath.hpp:9-11`; `src/util/BufferBudget.hpp:6-7`; `src/ApertarCoreApp.cpp:6335, 10869-10976, 11114, 11626-11627, 12572`; `src/ApertarCoreApp.hpp:173` @cinemate-port.

**Problem.** Comments cite T24-T50, critic ids (M1, Y8, S11), Q23, design sections, KB paths, clip ids (C0001-C0106), dates, Cinemate and own commit hashes, 'Patrik's rule', 'for the A/B', 'design sketch v2 (not in any repository)'. Several are stale ('the 16-bit 25 is backendMaximumFps()', 'exFAT/NTFS get 2', a test file that does not exist, an O_DIRECT path the fork does not carry). `writtenFiles_` carries another member's comment (CC:5591). One runtime `assert(` (upstream Core has none). 'CineMate Log' is the feature name in `describe()` and in journal lines while the UI calls it 'Log'.

**Apertar way.** STY / CAM-I19 / C1-I14: comments are rare, one to three lines, present tense, a hazard or a reason; no ticket numbers, authors, dates or other projects' hashes (`CC:6927-6928` @upstream-1.6.0). Log lines name Apertar concepts (`ApertarCore recording clip:`, `CC:3353` @upstream-1.6.0). Other projects appear only incidentally and in README credits (`README.md:307-310` @upstream-1.6.0).

**Rework.**

1. Per file in the Where list: delete the id, date, hash and history; keep one constraint line or nothing. Measurements go to the KB and commit messages.
2. Playback: delete the header essays; keep four one-sentence hazards (lock-free yield window because `mutex_` is held during the drain; facts cache keyed on mtime because readdir on exFAT is slow; why `POSIX_FADV_DONTNEED`; frame-number clock, not file position) and one line naming the UI function RawRender copies.
3. Rename 'CineMate Log' to 'Log' in `LogCurve.hpp`, `LossyDngEncoder.cpp:51`, CC log lines; namespace `cdnglog` stays; one README credit line ('the curve matches cinepi-raw's log_lut').
4. Fix the misplaced member comment at CC:5591 and delete the assert at CC:4596.
5. Move the detached `isoForMeasuredGain` comment (CC:2892) to its function; use `plan->` directly in `buildCdngLogTake` (CC:4023-4028).

**Owner decision.** None.

**Check here.** `grep -nE '\b(T[0-9]{2}|C0[0-9]{3}|critic|Patrik|Cinemate|CineMate|kb |apertar-kb|20[0-9]{2}-[0-9]{2}-[0-9]{2})' src/camera/CameraController.cpp src/cdng src/lossydng src/mlv src/audio src/util src/playback` gives 0 hits; build.

**Needs the Pi.** Nothing.

**Risk.** None; comments only (plus one log string).

---

## REC-13. Per-filesystem writer table changes upstream writer, queue and raw buffer defaults on vfat, NTFS and other

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | CC-2-F17, Media-fault-tune-F5, X-knobs-12 (directIo) |

**Where.** `src/util/MediaProfile.hpp:121-150`, `:160`, `:133`; `src/camera/CameraController.cpp:4315-4330` @cinemate-port.

**Problem.** vfat, ntfs and ntfs-fuse get 2 workers, queue 16 and +2 raw buffers; Other (btrfs, xfs, f2fs) gets 2 workers. ext4 and exFAT stay at upstream's 4/12/0. The rows are 'Cinemate's numbers, not measured here' (26da30e); the exFAT row already had to be reverted after drops (C0106). `directIo` is commented 'unused'.

**Apertar way.** `normalWorkerCount = std::max(2u, std::min(4u, hardwareThreads))`, queue 12, env overrides only (`CC:3323-3330` @upstream-1.6.0).

**Rework.**

1. `writerSettingsFor()`: every row returns the upstream values (workers from `hardwareThreads`, queue 12, extra raw buffers 0), or delete `writerSettingsFor` and keep `MediaProfile` for class and filesystem logging only.
2. Delete `MediaWriterSettings::directIo` and the fourth value of each row.
3. Fix the comment at CC:4316-4318.
4. A measured row (Apertar rig, per filesystem) may come back later in its own commit with the numbers.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`; `--simulate --media` on a vfat loop mount: the `recording clip:` line shows workers=4 queue=12.

**Needs the Pi.** FAT32 USB stick: 1 min cDNG take, compare drops with 1.6.0 (`journalctl -u apertar-core | grep 'recording stats'`).

**Risk.** None for ext4/exFAT (unchanged).

---

## REC-14. Raw copy pool kept between takes (about 100 MB at 16-bit 4K)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | CC-3-F5, X-board-support-8 |

**Where.** `src/camera/CameraController.cpp:4502`, `:4596-4606`, `:4892-4899`, `:4935-4945`, `:5547-5550` @cinemate-port.

**Problem.** `stop()` no longer clears `rawPool_`. `trimRawPoolToIdle` keeps `min(queue, max(workers+2, 4))` full-frame copies, 6 x 16.6 MB at 16-bit 4K with 4 writers, until the session reconfigures. On 1-2 GB Pi 4 / CM4 boards this competes with preview and the UI between takes (probable). `APERTAR_RAW_POOL_WARM` restores the old rule 'for the A/B'.

**Apertar way.** `stop(): queue_.clear(); rawPool_.clear(); pooledRawBytes_ = 0; expectedRawBufferSize_ = 0;` (`CC:3486-3489` @upstream-1.6.0).

**Rework.**

1. Restore the upstream clear in `stop()`.
2. Keep `warmRawPool` (allocates outside the lock at take start); that keeps the port's start-up gain.
3. Delete `trimRawPoolToIdle` and `APERTAR_RAW_POOL_WARM`.
4. If the owner wants the idle pool on big boards: keep it only when `MemTotal >= 4 GB`, read as `BufferBudget.hpp:83-95` reads it.

**Owner decision.** None.

**Check here.** Build; code read: `stop()` frees the pool as at upstream.

**Needs the Pi.** Pi 5 16-bit 4K: two takes back to back, the second starts without drops (`recording stats` dropped=0); `free -m` after stop returns to the pre-take value.

**Risk.** First frames of a take allocate if `warmRawPool` is late; it runs before the first frame.

---

## REC-15. UI automounter unmounts and PCIe-removes the drive on one HAT read

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | Media-fault-tune-F9 |

**Where.** `Apertar-UI/src/CfeAutomounter.cpp:549-550`, `:402-420`, `:732-746` @cinemate-port (UI dc471c1).

**Problem.** `if (!lastInsert && insert && m_mounted) handleSurpriseRemoval();` with no debounce. `handleSurpriseRemoval` runs `umount2(MNT_DETACH)` and writes 1 to the PCI device's `remove`. One I2C read with the slot bit set during a take lazily unmounts the recording drive and removes it from PCIe (probable). Footage loss.

**Apertar way.** Upstream acts on single reads only for cheap or user-started edges: insert -> `mountPcie`, eject button -> `unmountPcie` (`ui-upstream/src/CfeAutomounter.cpp:547-550` @upstream-1.6.0). The port's own Core reader of the same byte needs two agreeing reads, 'a glitch must not end a take' (`CfeHat.hpp:35-36` @cinemate-port).

**Rework.**

1. In the poll loop keep a counter `m_emptyReads`; call `handleSurpriseRemoval()` only after the slot reads empty on two consecutive 100 ms polls; reset on any present read.
2. One comment line: why two reads.

**Owner decision.** None.

**Check here.** UI build (`/home/user/build/ui-port` copy); code read.

**Needs the Pi.** CFE HAT, record 5 min while the UI runs: no `surprise removal` in `journalctl -u apertar-ui`; pull the card: removal within 300 ms.

**Risk.** Removal reacts 100 ms later.

---

## REC-16. Audio writer queue unbounded; after a write failure the WAV is built from bytes never written

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | Encoders-audio-F5, Encoders-audio-F9 |

**Where.** `src/audio/AudioRecordingSession.cpp:485-486`, `:534-536`, `:585`, `:709-746`, `:766-779` @cinemate-port.

**Problem.** `enqueueWrite` allocates a `std::vector<char>` per read block and pushes without limit (one log line above 16 MB). `capturedBytes_` grows at enqueue (:536), but the writer discards blocks once `writeFailed_`; `finalizeWav` sizes the file from `capturedBytes_`. After ENOSPC the data chunk is shorter than the header declares (malformed WAV without resample, a silent tail with resample).

**Apertar way.** `capturedBytes_` grew only after a successful `rawStream_.write` in `readerLoop` (`src/audio/AudioRecordingSession.cpp:472-474` @upstream-1.6.0). The encoders' background writer is bounded: `configuredWriterByteCap` (`APERTAR_LOSSYDNG_WRITER_BYTES`) and a take()/give() pool (`src/lossydng/LossyDngEncoder.cpp:96-150` @upstream-1.6.0); CAM-30 queues are bounded.

**Rework.**

1. Add `writtenBytes_`, incremented in `writerLoop` after each successful write; `finalizeWav` and the drift fit use it. Or skip finalisation when `writeFailed_`.
2. Cap `queuedWriteBytes_` with `APERTAR_AUDIO_WRITER_BYTES`, read like `configuredWriterByteCap`; on overflow set `failure_` to 'Audio capture write stalled.' and stop queueing.
3. Optional: a small free list of blocks.

**Owner decision.** None.

**Check here.** Build; host: none for ALSA. Code read: every use of `capturedBytes_` in finalisation replaced.

**Needs the Pi.** Record with audio to a nearly full card: the WAV opens in `ffprobe` without a size warning.

**Risk.** None.

---

## REC-17. The 1 GiB free-space floor also refuses a single still

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | minor | S | yes | fix-now | Media-fault-tune-F6 |

**Where.** `src/ApertarCoreApp.cpp:11331-11384`, `:12597-12600` @cinemate-port.

**Problem.** `mediaGateError()` refuses `record_start`, `capture_photo` and `timelapse_start` under 1024 MiB free. A card with 900 MB free can no longer take one DNG still. APP-23 handles the env opt-out and the floor constant, not the stills case.

**Apertar way.** Upstream records video and stills until the write fails (CAM-33). Mounted-media refusals exist for the Sound Recorder ('Sound Recorder needs mounted media.', `App:8351-8354` @upstream-1.6.0).

**Rework.**

1. In `mediaGateError(commandName)`: apply the free-space floor to `record_start` and `timelapse_start` only.
2. `capture_photo` is refused only when the medium is unmounted, removed or in error.
3. Land with APP-23 (same function).

**Owner decision.** None.

**Check here.** `--simulate` with a tmpfs media root of 500 MB: `capture_photo` succeeds, `record_start` is refused with the sentence.

**Needs the Pi.** Card with under 1 GiB free: a still is written.

**Risk.** None.

**Depends on.** APP-23.

---

## REC-18. Playback routes hand-write JSON error bodies; hold rule built twice and parsed back from a string

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | Playback-F3, Playback-F8 |

**Where.** `src/ApertarCoreApp.cpp:8499, 8506, 8529, 8532, 8569, 8687, 8816` (bodies), `:9362-9372`, `:11341-11357`, `:10970-10979` (hold) @cinemate-port.

**Problem.** Routes set `response.body = "{\"ok\":false,\"error\":\"Playback held: " + ...`, `{"ok":false,"busy":true}` with no sentence, and `{"ok":false,"error":"This clip was removed.","gone":true}`; the hold check is repeated in five routes. `HoldSignals` is filled by hand in `buildWebStateJson` and in `playbackHoldReason`; the watcher maps the returned string back to `playback::Hold` with an if-chain and calls it twice per cycle; the comment at :9362 is contradicted by :9364.

**Apertar way.** Web routes set bodies only through `errorReply(-1, sentence)` or `okReply` (`App:7204, 7218` @upstream-1.6.0). A shape repeated in one function becomes a local lambda (C1-I17, `App:9478` @upstream-1.6.0). Gates are inline: `if (camera_.isRecording() || soundRecordingActive() || camera_.timelapseActive())` (`App:7514` @upstream-1.6.0).

**Rework.**

1. Hold and busy: `errorReply(-1, "Playback is held while ...")` with the 409/503 status; the page reads only the status (WCP:12355-12358).
2. Gone: 410 through `errorReply`; the page reads `body.gone` (WCP:12361), so either switch it to the status or keep one extra key through `errorReplyBody` if APP-5 keeps that helper.
3. One local lambda `playbackHeld(response)` in `handleWebRequest` for the five routes.
4. `playbackHoldReason` returns `playback::Hold`; `holdName()` only where JSON is written; one call per watcher cycle reused for yield and trim; fix the comment.

**Owner decision.** None.

**Check here.** `--simulate`: start a sim take, GET a frame route: 409 with `{"ok":false,"error":"..."}`; the WebUI player shows the held line.

**Needs the Pi.** Nothing beyond the smoke test.

**Risk.** WCP must be checked for `body.busy` readers (WCP editor).

**Depends on.** APP-5.

---

## REC-19. Sensor probe tells IMX585 by a Model substring; second sysfs subdev walk

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-now | CC-3-F11, CC-3-F13 |

**Where.** `src/camera/CameraController.cpp:7152-7158`, `:6955-6972`, `:6985-7002` @cinemate-port.

**Problem.** `tableProbe = lowercase(properties::Model).find("imx585")`, a second way to tell sensors apart in the file (`otherSensorSubdevPresent` uses `detectSensorFamily`). Two loops walk `/sys/class/video4linux/v4l-subdev*/name`; `imx585SubdevPresent` opens a device only to test that it exists.

**Apertar way.** CAM-11: `sensorFamily_ = detectSensorFamily(camera_->id())` (`CC:5375` @upstream-1.6.0) and `switch (family)` in free helpers; Model is read only to pick the default tuning (`CC:5323` @upstream-1.6.0).

**Rework.**

1. `tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585;`.
2. One helper `subdevSensorFamilies()` returning the families found in the sysfs names; `otherSensorSubdevPresent` and `imx585SubdevPresent` call it. The open stays only where the fd is used (`openImx585Subdev`).
3. Optional: one log line for advertised sizes that are not in the table.

**Owner decision.** None.

**Check here.** Build both ways.

**Needs the Pi.** IMX585 boot: `journalctl -u apertar-core | grep -i probe` lists the same modes as before.

**Risk.** None.

---

## REC-20. Ladder refusals are constants that name a wrong menu path; ladder compression handled as strings

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | CC-2-F14, CC-2-F15 |

**Where.** `src/camera/CameraController.cpp:3034-3049`, `:3061-3067`; `src/camera/ModeLadder.hpp:17-44` @cinemate-port.

**Problem.** `constexpr kLadderOwnsMode / kLadderOwnsCompression` (7 uses) tell the operator 'Settings > Record > Mode Ladder'; the card is under Settings > Modes (confirmed by the CC-2 skeptic). `applyRungFormat` compares `ladder::effectiveCompression(rung)` to "lossy_3to1", "lossy_5to1", "none"; a typo in a code literal compiles and falls through to lossless. `Rung::cdngLog` is already an enum.

**Apertar way.** One inline sentence per `setErrorLocked(...)` with no menu path ('Resolution changes are blocked while recording.', `CC:7715` @upstream-1.6.0). Format sub-options are enums with `toString`/`fromString` at the edge (CAM-12, CAM-26).

**Rework.**

1. Inline one sentence at each of the 7 setters, e.g. 'Turn off the Mode Ladder to choose the resolution by hand.'; delete the constants.
2. `ladder::Rung` stores `RecordingFormat`, `CdngCompression` and `LossyDngRatio`; parse the strings once in the ladder loader and in `setModeLadder`.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests` (mode ladder test); `--simulate`: ladder on, set_resolution answers the new sentence.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** Coordinate with the camera editor (CC-5 ladder items).

---

## REC-21. A/B and restore env knobs left in the recorder and encoders

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | minor | S | yes | fix-later | CC-3-F9, CC-2-F11, CC-2-F18, Encoders-audio-F13, Encoders-audio-F10 (ring knob), Media-buffer-split-F9 (recorder side), X-knobs-9 (recorder rows) |

**Where.** `src/camera/CameraController.cpp:3115-3130`, `:3397-3408`, `:4293-4297`, `:4371-4373`, `:4468`, `:4715-4719`, `:4763-4764`, `:4892-4899`, `:5500-5536`; `src/cdng/CdngEncoder.cpp:118,137`; `src/audio/TimestampedAudioCapture.hpp:27-28`; `src/audio/AudioRecordingSession.cpp:212-219` @cinemate-port.

**Problem.** Restore switches and experiment arms: `APERTAR_RAW_POOL_WARM`, `APERTAR_CDNG_BUFFER_STOP_PERCENT` (beats a conf key), `APERTAR_CDNG_FRAMES_PER_FOLDER` (own parser), `APERTAR_AUDIO_BUFFER_MS` (reverted 1 s experiment), `APERTAR_DNG_WRITE_ROWS` / `APERTAR_DNG_PAYLOAD_COPY` (cDNG-only knobs under a DNG name). Several are parsed by hand, read once and logged on their own lines; a `static bool warned` sits inside `startAtFolder`.

**Apertar way.** CAM-24 / R8: one env knob per tuning value, `unsignedEnvValue`/`boolEnvValue` at use (`CC:1027-1061`, use `CC:3329-3330` @upstream-1.6.0), silent fallback, effective value on the `recording clip:` line. One-off warnings use a member flag (`warnedMissingWhiteBalance_`, `CC:6858-6861` @upstream-1.6.0). Area names `APERTAR_CDNG_*` (`CdngEncoder.cpp:55,72` @upstream-1.6.0).

**Rework.**

1. Delete `APERTAR_RAW_POOL_WARM` (with REC-14), `APERTAR_CDNG_BUFFER_STOP_PERCENT` as an override of a file key (it stays only if REC-1 makes the stop percent env-only), `APERTAR_AUDIO_BUFFER_MS`.
2. Keep `APERTAR_DNG_DONTNEED` with all three modes. Do not drop 'sync': it is the measured cDNG default (adac040: 0 lost vs 34-153 with writer). CC-3-F6/F9 asked to drop it; that part is not taken.
3. Rename `APERTAR_DNG_WRITE_ROWS` -> `APERTAR_CDNG_WRITE_ROWS`, `APERTAR_DNG_PAYLOAD_COPY` -> `APERTAR_CDNG_PAYLOAD_COPY` (also in `tools/dng_payload_write_test.sh`).
4. Every remaining CC knob is read with `unsignedEnvValue`/`boolEnvValue` at use; drop the extra log lines; effective values on the `recording clip:` line.
5. `static bool warned` -> member `warnedNoSyncThread_` or drop the warning.
6. Move `#include "util/MediaFault.hpp"` in `MlvEncoder.cpp` below the own header (CAM-I21).
7. App-side env twins go with APP-9.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`; `grep -n 'getenv' src/camera/CameraController.cpp` lists only knobs read through the two helpers.

**Needs the Pi.** Nothing beyond one take with defaults.

**Risk.** Test scripts that set removed names must drop them.

**Depends on.** REC-1, REC-11, REC-14.

---

## REC-22. Per-file writeback, 1 s fsync sweep and syncfs at stop: keep, but fix the shared cv and the DONTNEED fallback

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | CC-2-F5, CC-3-F6, CC-3-F3, Encoders-audio-F2 (cDNG remainder) |

**Where.** `src/camera/CameraController.cpp:4353-4377`, `:4715-4729`, `:4743-4809`, `:5010`, `:5256`, `:5366`; `src/cdng/CdngEncoder.cpp:84-108`, `:1897-1898` @cinemate-port.

**Problem.** `sync_file_range(WRITE)` after each DNG, a sync thread that fsyncs written files, part folders and the clip folder every `APERTAR_MEDIA_SYNC_MS` (default 1000) with the page-cache drop, and `syncfs` at a normal stop. This reverses upstream's stated intent and is backed by measurements (C0105: a pull lost an already-stopped clip; C0004: no drops with writeback alone; syncfs variant rejected after 782 drops). Two defects: (1) `syncLoop` waits on the writers' `cv_`; `enqueue`'s `notify_one` can wake it instead of a writer, so a queued frame waits for the next enqueue (worst with MLV's one writer). (2) DONTNEED 'sync' (default) drops pages only on that thread; with `APERTAR_MEDIA_SYNC_MS=0` cDNG pages are never dropped.

**Apertar way.** CAM-37: 'clip frames are not synced one by one'; `AtomicStillFile.hpp:31-32` @upstream-1.6.0: 'Keep this out of the continuous recording path: syncing each video frame would destroy throughput.' Upstream drops pages in the writer after every file (`CdngEncoder.cpp:1777` @upstream-1.6.0). CAM-27: one cv per worker set.

**Rework.**

1. Give `syncLoop` its own `syncCv_`, notified in `stop()` and `failRecording`.
2. At take start decide the effective page-cache mode: 'sync' without a running sync thread acts as 'writer'; pass it as a bool into the writer, not through a global.
3. Keep the rest. Handoff paragraph for the original developer: a deliberate departure from CAM-37, why (pull safety), the numbers above, and that nothing syncs on the writer path.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`; `--simulate` MLV take: writers wake per frame (no queue depth stuck at 1 in `recording stats`).

**Needs the Pi.** 3 min cDNG 16-bit 4K: dropped=0; `APERTAR_MEDIA_SYNC_MS=0`: `vmstat 1` cache column stays flat.

**Risk.** None.

---

## REC-23. Raw write path changed for every board and run on one CM5

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | M | yes | fix-later | X-board-support-7 |

**Where.** `src/camera/CameraController.cpp:1334-1338`, `:1458-1470`, `:4365-4369`, `:4714-4727`, `:8730-8736` @cinemate-port.

**Problem.** On by default for every board: one request per raw buffer, a copy worker that counts `dropped_copy_slot`, `sync_file_range` per DNG with the 1 s fsync. Upstream keeps three requests in flight for four buffers, copies on libcamera's thread and does no sync. Each change has a switch; nobody ran them on a Pi 4 or CM4. No defect shown.

**Apertar way.** Per-family / per-board defaults where memory matters (`CC:1126`, `CC:6001-6004` @upstream-1.6.0); CAM-13: board capability decided once in `RecordingCapabilities`.

**Rework.**

1. Run a 3 min cDNG take on a Pi 4 (and CM4 if available) with defaults and with each switch off.
2. If no board is available before the merge: default the per-file sync off where `recordingCapabilities().hardwareH264` is true (VC4 boards), one line where the knob is read, in the shape of CC:1126@upstream.
3. README: state the tested boards.

**Owner decision.** None.

**Check here.** Build.

**Needs the Pi.** Pi 4: `journalctl -u apertar-core | grep 'recording stats'` dropped and dropped_copy_slot after a 3 min 2K cDNG take, defaults vs switches off.

**Risk.** None if measured.

---

## REC-24. Clip viewer refuses the 8-bit DNGs Core writes

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | X-board-support-13 |

**Where.** `src/playback/DngTags.hpp:307-312`; `src/playback/DngFrameReader.hpp:67-82` @cinemate-port (confirmed: `info.bits != 10 && != 12 && != 16` -> 'Unsupported DNG layout').

**Problem.** Core writes 8-bit clips with BitsPerSample=8 (`src/cdng/CdngEncoder.cpp:149-152, :1206-1209`); IMX477 has 8-bit modes. Such a clip cannot be opened in the WebUI viewer.

**Apertar way.** No precedent (playback is port ground); the viewer should accept what Core writes.

**Rework.**

1. `DngTags.hpp`: accept `bits == 8`.
2. `DngFrameReader.hpp`: one byte per sample in the row size and one more branch in the row loop.
3. Extend `tools/dng_limits_test.cpp` with an 8-bit case.

**Owner decision.** None.

**Check here.** Host test; `--simulate` 8-bit sim clip opens in the viewer.

**Needs the Pi.** IMX477 8-bit clip plays in the WebUI.

**Risk.** None.

---

## REC-25. FORMAT row guesses the lossy ratio from the clip name

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | Playback-F9 |

**Where.** `src/playback/ClipProbe.hpp:168-178` @cinemate-port.

**Problem.** A clip counts as lossy 3:1 only if its folder name contains `cDNG_3to1` or `lossy3`. Lossy DNGs carry compression 7 plus LinearizationTable, the same tags as lossless companded files (`LossyDngEncoder.cpp:537,544`). With a custom template without `{format}`, a lossy clip reads 'lossless'.

**Apertar way.** CAM-35: metadata is measured, not guessed.

**Rework.**

1. Write the ratio at record time into a tag Core already sets (ImageDescription or a private DNG tag) in `LossyDngEncoder`, and read it in `ClipProbe`.
2. Until then, drop the lossless/lossy suffix when the name does not say.

**Owner decision.** None.

**Check here.** Host: probe a sim lossy clip with a plain name.

**Needs the Pi.** Nothing.

**Risk.** Changing DNG tags is an output change; step 2 alone is safe.

---

## REC-26. Playback memory: JPEG caches never trimmed, unused slot buffer, wrong memory comment

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | unknown | fix-later | Playback-F13, Playback-F7 |

**Where.** `src/playback/DecodeSlots.hpp:26-32`, `:105`; `src/playback/PlaybackFrames.cpp:76-87`, `:244-247`; `src/playback/RawRender.hpp:136-141`; `src/playback/ClipProbe.hpp:236`; `src/playback/ClipFrames.hpp:76`; `src/playback/DngTags.hpp:67` @cinemate-port.

**Problem.** Each slot holds about 39 MiB at IMX283 size (2 by default, up to 4); the comment's 46 MiB counts an `rgb` buffer that is never filled. The JPEG LRU caches (8 + 24 MiB) are never cleared, also through takes, on a Pi 4 2 GB or CM4 1 GB. `bytesHeld()`, `ClipFactsCache::probes()`, `FrameList::numberAtTime`, `DngInfo::tailBytesRead` have no caller; the header cites a KB test file.

**Apertar way.** Upstream Core holds no decode memory; no test hooks in src (conventions section 5).

**Rework.**

1. `trimIdleFrameSlots`: when `hold` is true also clear both JPEG caches.
2. Delete `DecodeSlot::rgb` and fix the slot comment (or render into it; deleting is simpler).
3. Delete the four unused functions and the KB test reference.
4. README: one line with peak playback memory.

**Owner decision.** None.

**Check here.** Build; `--simulate`: scrub, start a sim take, check `ps -o rss` drops.

**Needs the Pi.** Pi 4 2 GB: `free -m` during a 4-tab scrub and then during a take.

**Risk.** First scrub after a take re-decodes.

---

## REC-27. Playback text helpers and clocks duplicate App's

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | unknown | fix-later | Playback-F6, Playback-F14 |

**Where.** `src/playback/ClipProbe.hpp:30,41`; `src/playback/DecodeSlots.hpp:47`; `src/ApertarCoreApp.cpp:6336`, `:6394` @cinemate-port.

**Problem.** `sizeText` equals `formatBytesHuman`; `durationCardText` ('01:02:03'/'00:00') differs from `durationTextForFrameCount` ('1:02:03'/'--') used for other list items. `steadyMs()`, `playbackNowMs()`, `trimNowMs()` are the same expression.

**Apertar way.** `formatBytesHuman` (`App:3922`), `durationTextForFrameCount` (`App:5747`), `durationTextForSeconds` (`App:5767`) @upstream-1.6.0; steady_clock written inline (`App:7036` @upstream-1.6.0).

**Rework.**

1. `ClipFacts` carries numbers only (bytes, fps, span seconds); App formats them with its helpers. Delete `sizeText`.
2. Pick one duration rule for the whole list (touch-UI parity or App's) and use it for every item kind.
3. Keep `playbackNowMs` in `PlaybackHold.hpp` or inline; delete the other two (APP-30 covers trimNowMs).

**Owner decision.** None.

**Check here.** `--simulate`: /api/media rows show one duration style.

**Needs the Pi.** Nothing.

**Risk.** Text change in the list.

---

## REC-28. Frame-number rule in two C++ copies

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | Media-buffer-split-F10 |

**Where.** `src/cdng/ClipMerge.hpp:61-63`; `src/playback/ClipFrames.hpp:96` @cinemate-port.

**Problem.** `detail::frameNumber` is commented 'Same rule as playback/ClipFrames.hpp frameNumberFromName'. Two copies can drift. (The three copied store.edit blocks go with APP-11.)

**Apertar way.** Pure logic in one small header named after the concept (CAM-4).

**Rework.**

1. Move the rule into `src/cdng/FramePath.hpp` (both already include it); call it from ClipMerge and ClipFrames.
2. The Python copy in `tools/flatten_clip.py` may stay.

**Owner decision.** None.

**Check here.** Host tests `frame_path_test`, `clip_merge_test`.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-29. Second /proc/mounts parser beside upstream's

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | nit | S | no | fix-later | Media-fault-tune-F12 |

**Where.** `src/util/MediaProbe.hpp:81-130`, `:154-175` @cinemate-port.

**Problem.** `decodeMountField`, `normalizeMountPathForProbe`, `findMountEntry` re-implement upstream's parsing in the same process.

**Apertar way.** `normalizeMountPath`, `decodeProcMountField`, `isMountedPath`, `mountedDeviceForPath` (`App:1937, 1944, 2014, 2031` @upstream-1.6.0).

**Rework.**

1. Extend `mountedDeviceForPath` (or a sibling next to it) to return the fstype too; the watcher passes that entry to the probe.
2. Delete the three port functions. `rootDiskForDevice` stays with a one-line reason (no lsblk once a second).

**Owner decision.** None.

**Check here.** Build; `--simulate` with a loop mount: media_state and fs type as before.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-30. Clip-name template: constant tokens, src/util placement, second sensorName

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | Encoders-audio-F6, CC-6-F10 |

**Where.** `src/util/ClipName.hpp:10, 29-35, 121, 130-132`; `src/camera/CameraController.cpp:1157-1162`, `:11816-11822`, `:12596-12603` @cinemate-port.

**Problem.** 19 tokens plus `{text:}`: `{cam}` is always 'cam0', `{model}` always the constant `CdngEncoder::Metadata{}.model`, `{date_}` equals `{yy}_{mm}_{dd}`. The header sits in `src/util`. `clipNameSensorLocked` copies `sensorName()` but returns 'Simulated'. The single allocator is kept and the default template gives upstream names (conforms).

**Apertar way.** Pure logic sits with its owner (`src/camera/ExposureMetering.hpp`, included by App; CAM-4, CAM-6). `sensorName()` (`CC:8576` @upstream-1.6.0) is the one place.

**Rework.**

1. Drop `{cam}`, `{model}`, `{date_}` (WCP token picker too; tell the WCP editor).
2. Move to `src/camera/ClipName.hpp`; drop the KB reference.
3. `sensorNameLocked()` used by `sensorName()` and the clip-name code; map the simulated name there if it must differ.
4. Parse-twice: APP-38.

**Owner decision.** None.

**Check here.** `tools/clip_name_test.cpp` passes; build.

**Needs the Pi.** Nothing.

**Risk.** A saved template using a dropped token: the loader maps it to literal text (one line).

---

## REC-31. Early safety-stop recording event carries a stale lastError_

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | CC-6-F4 |

**Where.** `src/camera/CameraController.cpp:12440-12448` @cinemate-port; `Apertar-UI src/ApertarControlBridge.cpp:1350-1362`.

**Problem.** In the safety-stop path `emitRecordingEventLocked()` runs before `lastError_` is set from the session. A setter refused earlier in the take leaves its sentence there, and the bridge emits `recordingFailed` with that unrelated text.

**Apertar way.** `stopRecording` assigns `lastError_ = session_->recordingError()` before the event (`CC:8510-8514` @upstream-1.6.0).

**Rework.**

1. In the `announcedEarly` branch clear `lastError_` and `recordingFaultName_` before `emitRecordingEventLocked()`.

**Owner decision.** None.

**Check here.** Code read; `--simulate` ram-mode safety stop after a refused set_resolution: the event has no error.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-32. Safety stop ends a take; record during the flush discards queued frames

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | CC-3-F12 |

**Where.** `src/camera/CameraController.cpp:4611-4624`, `:5011-5022` @cinemate-port.

**Problem.** In ram mode the take ends cleanly at 90 % of the buffer budget. Pressing record during the drain discards the previous clip's remaining queued frames. Opt-in: frames mode (default) keeps upstream behaviour. Owner decision 2026-11-01 (fork-log:138).

**Apertar way.** No precedent; CAM-33 says a dropped frame does not stop a take.

**Rework.**

1. Keep. Re-shape per REC-2.
2. Handoff: ram mode ends a take at the stop percent, and a new take during the drain discards the rest of the old one.

**Owner decision.** None (decided 2026-11-01).

**Check here.** None.

**Needs the Pi.** Covered by REC-2.

**Risk.** None.

---

## REC-33. Dropped-frame count in state and event; unused fault field

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | CC-6-F9, Encoders-audio-F11, CC-6-F5 |

**Where.** `src/camera/CameraController.cpp:12889`, `:12891`; `src/util/RecordingDropWarning.hpp:11-27` @cinemate-port.

**Problem.** `RecordingDropWarning` gains a running total, and the recording event carries `recording_dropped_frames`; the port UI reads it. Deliberate (64bbbaa, 'the user wants the number'). The event also gains `fault`, which nothing reads; the state key `recording_fault` carries the same value and is read.

**Apertar way.** CAM-33: one warning per clip, counts go to the journal (`RecordingDropWarning.hpp:9` @upstream-1.6.0). Flat scalars, so an unmodified UI ignores both.

**Rework.**

1. Keep the count; handoff line: a deliberate change to 'notify once'; notification still once per clip.
2. Delete `fault` from `emitRecordingEventLocked`; keep `recordingFaultName_`, the getter and `recording_fault`.

**Owner decision.** None.

**Check here.** Build.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-34. Extra settings event helper for cdng_log_applied

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | yes | fix-later | CC-6-F11 |

**Where.** `src/camera/CameraController.cpp:11433`, `:12778`, `:12875-12879`; `src/camera/CameraController.hpp:200,225` @cinemate-port.

**Problem.** `emitLogAppliedIfChangedLocked` plus `lastEmittedLogApplied_` send an extra settings event on the reconfigure-failure path and after `setCdngLog`.

**Apertar way.** Runtime fields ride on the next ordinary settings event (CAM-18); a failed reconfigure that ends in Error sends none (`CC:8692-8710` @upstream-1.6.0).

**Rework.**

1. Delete the helper and the member. If the Error path must inform the UIs, call `emitSettingsEventLocked()` there once; `setCdngLog` already emits through `applySettingsLocked`.

**Owner decision.** None.

**Check here.** Build; `--simulate` set_cdng_log: one settings event.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-35. wavSampleRate rejects RF64

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | nit | S | no | fix-later | CC-2-F16 |

**Where.** `src/camera/CameraController.cpp:2894-2917` @cinemate-port (confirmed: `memcmp(riff, "RIFF", 4)`).

**Problem.** Core writes RF64 above 4 GiB (`AudioRecordingSession.cpp:773`). A speed-ramp take whose WAV passes 4 GiB gives sample rate 0 and no stretched WAV.

**Apertar way.** Upstream's WAV reader accepts RIFF and RF64 (`App:5806` @upstream-1.6.0).

**Rework.**

1. Accept `"RF64"` as well as `"RIFF"`; skip the ds64 chunk like any other.

**Owner decision.** None.

**Check here.** Host: a 12-byte RF64 header plus fmt chunk gives the rate.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-36. Audio drift fit, 10 ms ALSA period, MLV black level differ from 1.6.0

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | Encoders-audio-F8, Encoders-audio-F10 (period), Encoders-audio-F12 |

**Where.** `src/audio/AudioRecordingSession.cpp:486-498`, `:588-608`; `src/audio/TimestampedAudioCapture.cpp:192-219`; `src/mlv/MlvEncoder.cpp:1151-1157` @cinemate-port.

**Problem.** (1) Drift: least-squares slope over per-block stamps in upstream's 20..2000 ppm window instead of the endpoint ratio. (2) ALSA hw params set by hand, period 25 -> 10 ms on every path. (3) MLV declares the black level scaled for every depth via `BlackLevel.hpp`; 1.6.0 scaled only 8/10-bit, so a 16-bit MLV declared about 200 while cDNG declared about 3200.

**Apertar way.** `AudioRecordingSession.cpp:523-531`, `TimestampedAudioCapture.cpp:189-190` (`snd_pcm_set_params(..., 0, 100000)`), `MlvEncoder.cpp:165-175` @upstream-1.6.0.

**Rework.**

1. Keep all three. Handoff lines: drift uses upstream's method with a fitted rate; the capture period is 10 ms; MLV files differ from 1.6.0 at 12/16-bit and now agree with cDNG.
2. Bugs milestone: consider narrowing the drift window to 20..300 ppm.

**Owner decision.** None.

**Check here.** `tools/black_level_test.cpp` passes.

**Needs the Pi.** Nothing new.

**Risk.** None.

---

## REC-37. Host tests and desk tools of this domain

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | Encoders-audio-F14, Media-buffer-split-F11, Media-buffer-split-F14 |

**Where.** `tools/log_curve_test.cpp`, `tools/gen_log_curve.py`, `tools/dng_payload_write_test.{cpp,sh}`, `tools/black_level_test.cpp`, `tools/clip_name_test.cpp`, `tools/buffer_budget_test.cpp`, `tools/storage_preroll_test.cpp`, `tools/storage_buffer_conf_test.cpp`, `tools/clip_merge_test.cpp`, `tools/frame_path_test.cpp`, `tools/dng_limits_test.cpp`, `tools/flatten_clip.py` @cinemate-port.

**Problem.** Standalone g++ tests outside CMake with compile lines that disagree (c++17 vs c++20); a Python re-implementation of LogCurve to paste golden values; a `#!/bin/sh` test script; a 284-line desk script with a statistics report.

**Apertar way.** No tests and no tools/ upstream (conventions section 5); scripts are `#!/bin/bash` + `set -euo pipefail` (STY).

**Rework.**

1. Keep the C++ tests under APP-42's policy (one c++20 compile line, one README line).
2. Delete `storage_buffer_conf_test.cpp` with REC-1, `fps_ceiling_test.cpp` with REC-4, `gen_log_curve.py` (keep it in the KB).
3. `dng_payload_write_test.sh` -> bash idiom.
4. `flatten_clip.py`: keep; drop the statistics report; keep `--unflatten` only if a test uses it.

**Owner decision.** None.

**Check here.** `check_core.sh ... both tests`.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** APP-42.

---

## REC-38. Placement and namespace names (BufferBudget, StoragePreroll, UI clipframes)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | no | fix-later | Media-buffer-split-F13, Playback-F15 |

**Where.** `src/util/BufferBudget.hpp:45`; `src/util/StoragePreroll.hpp:16`; `src/cdng/FramePath.hpp:18`; `src/cdng/ClipMerge.hpp:21`; `Apertar-UI/src/ClipFrameFiles.hpp:17` @cinemate-port.

**Problem.** `src/util` gains planner headers that belong to one owner; namespaces `bufferbudget`, `storagepreroll`, `clipmerge`, `framepath`; the UI uses `apertar::clipframes` while ui-upstream has no `apertar::` namespace.

**Apertar way.** `src/util` @upstream holds only AtomicStillFile, RecordingDropWarning, RecordingFailure, SettingsFile (CAM-6); subsystem logic sits next to its owner (`src/camera/StillBracketing.hpp`); `apertar::settingsFile`; UI helper namespaces named after the file (`VideoPlayback`, `src/VideoPlayback.hpp:13` @ui-upstream).

**Rework.**

1. Move `BufferBudget.hpp` next to the queue (`src/camera`), `StoragePreroll.hpp` next to App (`src/`), after REC-2 has emptied their statics.
2. Optional: camelCase namespaces (`bufferBudget`, `storagePreroll`, `clipMerge`, `framePath`).
3. UI: `namespace ClipFrameFiles`.

**Owner decision.** None.

**Check here.** Both builds; host tests.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** REC-2.

---

## REC-39. Diagnostic response headers no page reads

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | nit | S | no | fix-later | Playback-F10 |

**Where.** `src/ApertarCoreApp.cpp:8540-8546`; `src/playback/PlaybackFrames.hpp:29-30` @cinemate-port.

**Problem.** The frame route sends `X-Frame-Count`, `X-Frame-Source`, `X-Decode-Ms`; the page reads only `X-Frame-Number`, `X-Frame-Index`, `X-Histogram`.

**Apertar way.** Upstream sends one functional header, `X-Accel-Buffering` (`App:7114` @upstream-1.6.0).

**Rework.**

1. Drop the three headers and `FrameOut::fromCache` / `decodeMs`.

**Owner decision.** None.

**Check here.** `curl -I` a frame route in `--simulate`.

**Needs the Pi.** Nothing.

**Risk.** None.

---

## REC-40. GET /api/buffer polled at 4 Hz beside /api/state

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | unknown | keep-and-document | Media-buffer-split-F12 |

**Where.** `src/ApertarCoreApp.cpp:8418-8425`; `src/web/WebControlPage.cpp:16490-16500, 20363` @cinemate-port.

**Problem.** A lock-free read-only route returns the buffer and pre-roll members; the WebUI polls it about 4 times a second while the bar or the pre-roll pill shows. A second state endpoint and a second rate.

**Apertar way.** The WebUI polls GET /api/state at 1 Hz (WEB rules, C1-S26); extra read-only GET routes exist (/api/media, /api/config, /api/presets).

**Rework.**

1. Keep the route; after REC-2 it reads `camera_.frameBufferStatus()` (the controller-owned gauge).
2. Handoff line: a smooth bar during a take without the controller lock; polling the full state at 4 Hz would cost more.
3. The meaning of its `recording` member: APP-27.

**Owner decision.** None.

**Check here.** `--simulate`: `curl /api/buffer` during a sim take.

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** REC-2, APP-27.

---

## Dropped or handled elsewhere

| Finding | Reason |
| --- | --- |
| CC-3-F7, CC-6-F2, X-board-support-15, X-stock-behaviour-6, X-knobs-4 | Done in Core `05eaafa` (strip only for raw formats and photo mode). Default for raw formats: APP-6 owner decision |
| X-stock-behaviour-7 | Done in Core `615b48c`; cDNG remainder of Encoders-audio-F2 is REC-22 step 2 |
| X-stock-behaviour-5, X-knobs-3, pre-roll half of Media-buffer-split-F6 | Done in Core `0977dd6` (APP-2) |
| Media-fault-tune-F8, X-protocol-security-6 | Done in Core `e4246ee` (APP-22) |
| Media-fault-tune-F2, X-knobs-10, X-board-support-10, X-protocol-security-9 | Duplicate of APP-13 step 3 (kernel-tune helper deleted; the dirty_bytes sizing goes with it). Severity: X-knobs-10's minor is right, because pi already has full sudo on a stock image, and the planted-symlink path needs an install step nothing performs |
| Media-buffer-split-F4 | Duplicate of APP-13 step 1 (trim helper -> direct timeout+sudo fstrim). Its kill bug stays as REC-9 |
| Media-fault-tune-F4, X-knobs-11 | Duplicate of APP-29 (eject flag, App code) |
| Media-fault-tune-F6 (opt-out env) | Duplicate of APP-23; the stills half is REC-17 |
| Media-fault-tune-F7 | Duplicate of APP-35 ([cfexpress_hat] reader) |
| Playback-F4 | Duplicate of APP-25 (/api/media in a hold) |
| Playback-F5 | Duplicate of APP-24 (downloads refused in every hold) |
| Playback-F12 | Duplicate of APP-50 (liblj92 README) |
| Media-buffer-split-F7 (keep the wait) | Merged into REC-9 |
| Media-buffer-split-F9 (App side, *_env state) | APP-9; recorder side in REC-21 |
| X-knobs-7 | Merged into REC-1; the home question is APP-11 |
| X-knobs-9 (App, start script, RT) | APP-9 and APP-15; recorder rows in REC-21 |
| X-knobs-12 (conform_fps, hold_ms/double_ms) | Camera and hardware editors (APP-34, HW-16); directIo is REC-13 |
| X-stock-behaviour-4 | Camera domain (IMX585 crop sizes, CC-4); left to that editor |
| X-board-support-9, X-board-support-14 | Camera domain (ladder cards, sensor paths); left to that editor |
| X-stock-behaviour-11 | Merged into REC-3 (default) and APP-13 step 2 (not-available result) |
| CC-3-F6 / CC-3-F9 'drop DONTNEED=sync' | Not taken: contradicted by the cDNG measurement (adac040, 0 lost vs 34-153 with writer); see REC-21 step 2 |
| Encoders-audio-F2 'sync_ms default 0' premise | Not real: rev-CC-2 skeptic keeps sync_ms 1000 (pull safety), and the KB's 'default 0' plan row was dropped (drop-frames README:310) |
| CC-2-F4, Encoders-audio-F7, Playback-F11 | Dropped by the unit skeptics (lossless only on Pi 5-class; borrowed spans are upstream's pattern; undocumented env setting has upstream precedent) |

## What conforms (for the handoff)

| What | Where @cinemate-port | Rule |
| --- | --- | --- |
| IMX283 added case by case in existing switches | `CC:2809-2814, 2858-2859, 3332-3339, 3447, 3665-3735` | R5 |
| Build without libcamera kept: one guard split, signatures kept | CC | CAM-28 |
| Clear HDR exposure rules in `sanitizeSettingsForSensor`, the upstream place for limits | CC | CAM-21 |
| Raw copy hand-off keeps the frame path non-blocking: a frame without a slot is dropped and counted, drop logged first and every 30th, marked on `RecordingDropWarning` | `CC:5067-5085` | CAM-30, CAM-23 |
| `failRecording` keeps first-wins and adds the fault class with `compare_exchange_strong`; yanked drive ends the take through `checkRecordingFailure` | `CC:5424-5444`, `CC:12456-12478` | CAM-33 |
| Lossy DNG background write failures now fail the take (closes an upstream rough edge) | `CC:5280-5290` | CAM-33 |
| New per-take knobs `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_COPY_WORKERS`, `APERTAR_DEAD_MEDIUM_STOP_MS` use `unsignedEnvValue` with bounds; effective values on `recording clip:` | CC | CAM-24 |
| Encoder knobs (`APERTAR_DNG_WRITE_ROWS`, `APERTAR_DNG_PAYLOAD_COPY`, `APERTAR_AUDIO_BUFFER_MS`) read in read-once statics with clamp and silent fallback, not in README | `CdngEncoder.cpp:115-142` | R8 |
| New worker sets: mutex + cv + deque + stop flag, atomics with explicit orders; audio writer thread the same | `CC:5040-5055`; `AudioRecordingSession.hpp:73-85` | CAM-27 |
| Recorder surface call-compatible (`stop(bool finalize = true)`, `open(..., bufferUs, periodUs)`) | audio | CAM-14 |
| New setters `setConformFps`, `setFpsPhaseLock`, `setMediaTrimEnabled`, `setClipNameTemplate`, `setPreviewTdn`: lock, gate with a sentence, copy `settings_`, `applySettingsLocked` | `CC:11804-11922` | CAM-7, CAM-8 |
| Runtime fields `isoMeasured`, `isoMax`, `fpsMax`, `cdngLogApplied` are non-persisted `CaptureSettings` fields | `Types.hpp:177-180` | CAM-18 |
| `media_trim` persists as a `CaptureSettings` field in camera_settings.conf, carried across formats | `CC:889`, `:976`, `:11351-11370` | CAM-25, CAM-40 |
| Default clip template gives the upstream names; one allocator kept | `tools/clip_name_test.cpp` | CAM-14 |
| Log lines keep `ApertarCore <area>: key=value` | CC, audio, App media | CAM-23 |
| Pure logic as small header-only std-only files: `FramePath.hpp`, `ClipMerge.hpp`, `planBuffer` | `src/cdng`, `BufferBudget.hpp:338-380` | CAM-4 |
| Frames mode stays the default; ram mode never blocks capture and refuses itself on small boards | `BufferBudget.hpp:8`, `:352` | CAM-30 |
| Record gate is one guard at the top of `handleCommand` with operator sentences | `App:12597-12600`, `:11359-11384` | CMD-4 |
| `media` event and new state fields are flat scalars built at the emit site | `App:10824-10835`, `:9555-9562` | CMD rules |
| Playback routes added to the flat `handleWebRequest` chain; read-only; no new thread; library listing extended in place with `ostringstream` + `escapeJson` | `App:8442`, `:8475`, `:8550` | WEB, CMD-1 |
| Playback helpers return bool + error string and never throw across routes; files opened `O_CLOEXEC` with `POSIX_FADV_DONTNEED` like the writer | `src/playback` | CAM-22 |
| MLV black level now uses upstream's own shared helper | `MlvEncoder.cpp:1151-1157` | (fixes an upstream inconsistency) |
