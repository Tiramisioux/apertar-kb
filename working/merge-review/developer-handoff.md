# Developer handoff: the cinemate port

What this page is: everything the cinemate port adds to Apertar 1.6.0, where it sits in Apertar's code, and what it means for the next developer. For the original developer (knows 1.6.0) and for Patrik (made the port).
State: draft of 2026-11-20. The reworks are partly done; each row says which. The clip-split branch (dual sensor, clip split; 80 Core and 20 UI commits after `cinemate-port`) now joins the review; it is not in this changelog yet.

| Item | Value |
| --- | --- |
| Refs | Port: Core `cinemate-port` `01f170c`, UI `7ea9afc`, imx585 `cd548ef`, imx283 `68b7dc9`. Review fixes: Core `work/improve` `8bfc242` (C1-C30), UI `ac1fc28` (U1-U3), imx283 `36d484b` (D2-1). Upstream: `upstream-1.6.0` Core `35dbe67`, UI `43888e5`. Merge target: fork main Core `f60e301` (1.6.0 + Clear HDR set and sensor probe) |
| Short names | `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `ACB` = UI `src/ApertarControlBridge.cpp` |
| Ids | C/U/D2 = fix log entries (`fix-log.md`). CAM-, REC-, HW-, APP-, WEB-, UI-, TXT- = open items (`fix-list.md`). DA-/DB- = Patrik's recorded decisions. Rule ids (CMD-n, CAM-n, R8 ...) = `apertar-conventions.md` |
| State words | **as ported** = unchanged by the review. **reworked (Cn)** = fixed on `work/improve`. **planned (page)** = rework designed in `design/<page>.md`, not done. **held** = waits on Patrik |
| Tested | Nothing in this review ran on a Pi. Port features ran only on Patrik's CM5 (see "Raspberry Pi models") |

## Changelog in short

60 features, the rows of `feature-list.md`, regrouped. "Relation": **new** (no upstream code), **beside** (added next to upstream code), **extends** (upstream code changed in place), **replaces** (upstream code removed).

### Camera and modes (9)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| Mode Ladder | The chosen FPS picks size, bit depth, Clear HDR and compression between takes, from an ordered list | New: `src/camera/ModeLadder.hpp`, hooks at the top of six `CC` setters (`setResolution`, `setFps`, `setRecordingFormat`, `setRawBitDepth`, `setClearHdr`, `setStillExposureMode`); own file `mode_ladder.conf` | Any new setter that changes size, depth, HDR or compression must call the ladder refusal; new mode fields go into `ladder_*` in all three serialisers | as ported; off. Store moves into `camera_settings.conf` (planned, camera-modes 10; owner row 7) |
| IMX585 modes from tables | 40 SDR sizes per depth, Clear HDR lists, 1:1 and 2.55:1 crops, 10-bit; 1.85:1 renamed 2072/1036 | Replaces upstream's whitelist predicates in `CC` (`isImx585*`) with `src/camera/Imx585Modes.hpp`; a driver-adjusted mode is refused | Size list exists three times (header, `WCP` fallback, driver table). Today Core needs the port driver (blocker CAM-1) | binned 1920x1080 H12 held back (C13). Both 1.85:1 heights, original-driver binned modes (planned, camera-modes 1-5, lane, audit not done) |
| Sensor-probe FPS ceiling | Max fps from the startup probe: 4K SDR to 60, IMX585 lossless past 30; `fps_max` in state | Extends fork main's probe (`min(table, probe)` flipped to probe-wins); `src/camera/FpsCeiling.hpp` | The ceiling rule lives in Core and again in QML; change both | as ported, on. Back to `min(table, probe)` with bench knobs held (camera-modes 6, DB-52; owner row 4) |
| Binning and crop per mode | `list_sensor_modes` and state report binning and crop | Extends fork main's probe struct in `CameraController.hpp` | `list_sensor_modes` is fork main, not 1.6.0. Fields kept only if a tool reads them (owner row 29) | as ported, on |
| Values the camera decides | Clear HDR freezes auto ISO/WB and restores them in SDR; screens show the gain/Kelvin in use in italics; ISO Lock | Extends `setIsoAuto` (now takes a bool), `setClearHdr`, `setWhiteBalanceAuto`; touch: `applyCoreState`, `TopDropdownStat.qml` | A new camera-decided value needs a `...SetByCamera` property and the HDMI `cameraSet` flag; the 1 s `get_state` poll is the only live source | as ported, on in Clear HDR only. Clear HDR ISO caps become constants (planned, storage-settings 2) |
| Preview temporal denoise switch | Lighter preview at 4K Clear HDR 16-bit; DNGs unchanged | Beside `DefaultTuningSelection.hpp`: `src/camera/TuningTdnStrip.hpp` (own JSON parser) wraps the tuning path in `CC` | Use the resolved tuning path for checks, not `activePath` | reworked: on by default, raw formats only (C7, C9, C10). Parser to libyaml like `makeProresIspTuning` (planned, camera-modes 8-9) |
| Raw camera buffer count | One request per raw buffer: 4 SDR, 8 Clear HDR, +2 on FAT/NTFS | Replaces `kActiveRequestCount` in `CC` | The count is also the copy worker's queue depth; no board cap (CAM-7) | as ported, silent. Owner row 20 |
| Frame-rate phase lock | A servo holds the sensor rate against the audio clock on long takes | New header-only servo `src/camera/FramePhaseLock.hpp`, `set_fps_phase_lock` | Its `APERTAR_PHASE_LOCK_*` knobs stay (dual-sensor test, DA-82) | as ported; off |
| Conform FPS | Stored, settable, published project rate; nothing reads it yet | New `CaptureSettings::conformFps` (25) | Patrik's request 21 (DA-92); keep it, it is planned input for later work | as ported; no effect |

### Drivers (4)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| IMX585 driver modes and timing | 187 modes incl. RAW10 4K, crops with real sensor windows, new HMAX/VMAX | Replaces the mode tables of `imx585.c` on `origin/apertar`; 55 commits ahead | Run `tools/replay_mode_table_audit.py` and `check_window_alignment.py` after any table edit. Which Apertar-Studio driver commits were taken: unconfirmed (`fork-log.md:276` vs inventory) | as ported. Back to 3840x2076 / 1920x1038 held (camera-modes 14; owner row 3) |
| IMX585 Clear HDR colour and gate | 12/16-bit binned 1080p Clear HDR, colour by default, mono needs `ccmp`, developer gate for windowed binning | Extends `get_mode_table`, `get_format_code`, `enable_streams`, `update_hmax` | Needs `imx585_clearHDR.json` (outside every repo). Core side of Clear HDR is fork main's | as ported; gate off. 12-bit binned curve: `hdr12/REPORT.md` H1 (probable, needs one capture pair) |
| IMX283 sensor family | An IMX283 works: 57 modes, active-area crops | Core: fifth `SensorFamily` value and its switch cases (recipe R5), `src/camera/Imx283Modes.hpp`; driver: port of Will Whang's driver | Core hard-codes the 57 modes; the Boot Config card does not list it (HW-23). Read the driver's `APERTAR.md` "Open questions" first | per-crop VMAX floors off (D2-1); otherwise as ported; inert without the sensor |
| Mode geometry controls | `v4l2-ctl` shows binning, crop and active area per mode | Beside, in both drivers; read by cinepi-raw, not by Core | A check, not a source: Core keeps its own tables | as ported, on |

### Recording and media (18)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| Pulled-drive survival, media state, record gate | A dead drive ends the take with a named fault; record refused without media or under 1 GiB | Replaces the unconditional writer join in `CC::stop`; media watcher thread and `MediaProbe.hpp`, `MediaFault.hpp`, `CfeHat.hpp` in App | A take now ends three ways; a new writer must honour the abandon rule. The watcher owns media state. Slow drive judged removed after 5 s (REC-8, held) | as ported, on; `media_state` once (C4) |
| Take durability | A pull keeps the take to about the last second | New: 1 s sync thread, per-file writeback, page-cache drop mode (`APERTAR_DNG_*`) in `CdngEncoder` and recorder | Change a writer's flush order only with a Pi pull test | Lossy DNG drop back (C6). Stock defaults back to 1.6.0 planned (storage-settings 24) |
| Media profile, tuning file, kernel tune | Writer count, queue and raw buffers follow the medium; tester file `~/apertar-media-tune.conf`, `apertar-tune` | Extends recorder defaults; new `util/MediaProfile.hpp`, `MediaTune.hpp`; root helper `scripts/apertar-media-tune` | A third config surface; a new write-path knob must pick env, hardware file or tune file | as ported. File kept (2026-11-02 request), statics go (storage-settings 17); kernel helper removal planned (boot-config-helpers 10) |
| Direct DNG payload write | One `write()` per frame instead of a 16.6 MB copy | Extends `writeRawPayload` in `src/cdng/CdngEncoder.cpp` | Keep both paths byte-identical: `tools/dng_payload_write_test.sh` | as ported, on |
| Raw copy hand-off and warm raw pool | Copy leaves libcamera's thread; first frames skip allocations | Beside the capture-complete path in `CC`; pool no longer cleared at stop | Pool memory stays between takes (REC-14); copy worker closures held (camera-modes 11) | as ported, on |
| Log for cDNG, lossless JPEG, Lossy DNG | 16 to 12 bit, inverse curve in LinearizationTable | Beside `compressClearHdrFrame`; `src/cdng/LogCurve.hpp` | The curve is a fixed table shared by encoder and tags; changing it changes every file | as ported; off. Clip label fixed (C14) |
| One black and white level for MLV and cDNG | MLV from 16-bit takes gets black about 3200 | Moves upstream's two private copies into fork main's `BlackLevel.hpp` | Old MLV files differ from new ones; do not re-privatise | as ported, on |
| Audio writer thread, 1 s fsync, drift fit | Fewer audio dropouts; pulled card keeps raw PCM; drift from a least-squares fit | Replaces reader-writes-to-file in `AudioRecordingSession`, `TimestampedAudioCapture` | `APERTAR_AUDIO_BUFFER_MS` stays (NVMe campaign) | queue bounded, WAV sized from bytes written (C18) |
| Speed ramp | FPS changes inside a cDNG/MLV take; WAV and timecode stay right; optional `_stretched.wav` | Extends `observeVideoFrame`, timecode, frame numbering; stretch runs `rubberband` through `/bin/sh` | Run-time dependency `rubberband-cli`; launch to be fixed (owner row 18, CAM-25) | as ported; ramp off |
| Clip name templates | Clip names from tokens and text, live example | Replaces the inline `put_time` + `_C%04d` loop with `src/util/ClipName.hpp` | The folder name feeds playback, delete and the facts cache; a new token goes into Core, WebUI and touch card | example off the medium lock (C16); default name `{format}_{date}_{clip}` unchanged |
| Dropped-frame count, pre-roll mute | UIs show the running drop count | Extends `RecordingDropWarning.hpp` | Every drop path must call the counter | as ported, on |
| RAM write buffer, bar, safety stop | Queue sized from free RAM; red bar in REC; take ends at 90 %; REC in the drain starts a new take | Extends `DngRecordingQueue`; `BufferBudget.hpp`; header singletons, global hooks, own App thread | Safety stop calls `record_stop` from its own thread; keep it out of the command mutex | as ported; off. Settings, latch and hooks to the Apertar shape (planned, storage-settings 3-15) |
| Storage pre-roll | 2 s raw test take at top fps, deleted after, blue PRE-ROLL pill | New App worker and `StoragePreroll.hpp`; a hidden take kind in `CC` | Recorder start-path changes must keep the pre-roll exclusions | automatic off (C5). Through `handleCommand` (planned, preroll 1-11) |
| Split takes and merge worker | Frames go into `part_NNN/` every N frames; Core merges them back while idle | Extends frame paths (`FramePath.hpp`); `ClipMerge.hpp` copies the trim worker; UI reads both layouts (`ClipFrameFiles.hpp`) | Every list, delete, download and zip path must read both layouts; MLV and pre-roll never split | part folders by the writers (C17); split off, merge on |
| Drive trim | Trim after a delete of 1 GiB or more and at mount | New App worker; root helper `scripts/apertar-media-trim` | Trim must stay out of takes; ends by signalling sudo (REC-9) | as ported, **on**. Off by default planned (storage-settings 24); helper replaced by `sudo -n timeout fstrim` (boot-config-helpers 9) |
| Playback hold, yielding downloads and deletes | Playback and downloads stop before a take, photo, standby or eject | Extends `handleCommand` guards and media routes; `PlaybackHold.hpp` | Any new long route must check the hold; a take never waits for a reader | as ported, on |
| Playback of every DNG size | IMX283 and IMX294 clips open in the browser | Beside: size gate in `src/playback/DngTags.hpp` | New larger sensors need this limit and the decode memory checked; 8-bit DNG refused (REC-24) | as ported, on |
| Web preview rate cap in raw takes | MJPEG preview can be capped during a raw take | Extends `captureWebPreviewFrame` in App | Env only; goes (storage-settings 20) | as ported; off (30 fps) |

### Controls and hardware (14)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| One writer for the hardware file | Revisions, 20 versions with Undo, stale page refused, replaced file detected | Replaces `saveHardwareConfigFile` with `src/hardware/HardwareConfigStore.{hpp,cpp}`; per-class readers untouched | Every writer goes through `configStore()`; a plain `ofstream` bypasses history | reworked: key edits in every section copy (C20), `/boot` start (C21), whole-file save writes (C27), checks back (C30), Undo with script paths (C28) |
| Hardware file checker | Errors and warnings with line numbers; error count on the touch chip | New: `src/hardware/HardwareConfigText.hpp` (`hwconf`), a second copy of the readers' rules | Change a reader's keys and the checker together; it advises on whole-file saves (C27), still blocks key edits | split into `.cpp`, per-section aliases (planned, hardware-inputs 19-22) |
| Controls page | Config > Hardware: one row per input with actions, free pins, live state | New: `ControlsModel.hpp`, `GpioChipInfo`, `I2cProbe`; data served on `GET /api/config` | A new input class needs a peripheral spec and a row builder | GPIO chip back (C1); read through `GET /api/config` (C22); page store into `state` (planned, webui-state 6-7) |
| Saves apply without a restart | Only changed driver groups restart, after the take | New controls worker in `App::start`/`stop` | Code that opens a hardware class outside `start()` races the worker | as ported, on |
| Listen, I2C scan, output test | Last control that fired; bus scan; one tally blink or trigger pulse | New third callback on the input classes; `test_output` beside `TriggerOutput::pulse` | A new input class must feed Listen | scan bounded to 1 s (C24); all under the command lock (C26) |
| Remote-only buttons and Try | Buttons with no pin, run from a WebUI card; Try runs a saved action | `[gpio_buttons] remoteN`; `test_input` re-enters `handleCommand` before the lock | Script actions need a real press (C8) | card moves into Settings > Controls (planned, webui-state 24) |
| One action vocabulary | Same action names on every input; "Did you mean" | Replaces three `normalizeSingleAction` copies with `hardware/ActionCatalog.hpp` | Add the dispatcher branch and the catalog row together | `list_actions` slimmer (C25) |
| `clear_hdr` button action | A button toggles Clear HDR | Extends `handleSingleHardwareInputAction` | Mode Ladder may refuse it | as ported; off until mapped |
| Click and Hold gestures | Press, Single, Double, Triple, Hold per push | Extends the button branches of `GpioInput`, `NeoRotary4Input`, `Pcf8574Input`; `ButtonGesture.hpp` | Timing fixed in the header (DA-30); a click action waits out the 0.5 s window | as ported; off until a key is set. Wake press consumed (planned, hardware-inputs 11) |
| 1-0-1 (normally closed) buttons | A button pressed at start is taken as inverted | Extends GPIO and PCF read loops; 1.6.0 ignores it until release | Polarity should come from `active_low` | as ported, **on**. Behind `invert_on_start`, off (planned, hardware-inputs 10; not in code yet) |
| Edge events instead of polling | Input thread sleeps until an edge; `poll_ms` as fallback | Replaces the poll loop in `GpioInput::run` | No switch back; chips without edges unchecked on Pi 4/CM4 | as ported, **on** (kept, DA-35; owner row 13) |
| Two- and three-way switches | Switch positions run actions | New `[gpio_switches]` section in `GpioInput::loadConfig` | A switch moved in Standby wakes the camera and its position is lost (owner question) | as ported; off |
| Default hardware template, no UI-written file | Missing file starts from Core's template; touch UI no longer writes one | Extends `defaultHardwareConfigTemplate` in App; removes UI writers (-578 lines) | Nothing writes a first file today (APP-16) | display 720x720 again (C2, U1). Core writes it once (planned, hardware-inputs 6-9) |
| IMU config through the store | Level, calibration, orientation saves are atomic and in history | Replaces two line editors in `Mpu6050RecordingSession.cpp` | IMU writes within 10 min share one history entry | as ported; never run with a gyro |

### WebUI (6)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| Clip Browser | Card grid with thumbnails, filter, sort, select, download, remove; fast facts cache | Replaces the `mediaBrowser*` list in `WCP`; Core `GET /api/media` grows, new `ClipProbe.hpp` cache | None of 1.6.0's function names remain today; media routes keep the 409 hold rule | upstream names and parts back, Patrik's look kept (planned, webui-state 12-18) |
| Clip Viewer | Play a clip in the browser: scrub, frame step, histogram, timecode, sound | New: second (Qt-free) JPEG decoder in Core (`PlaybackFrames.cpp`, `DngFrameReader.hpp`), vendored `third_party/liblj92`, routes `/api/media/frame`, `/file`, `/clip` | Two decoders exist; a touch-UI rendering change must be mirrored | JPEG handle leak (C15), `audio_url` encoding (C19). Parts rebuilt (planned, webui-state 14) |
| Settings search | Search box over Settings | New in `WCP`, `data-search` words and a `MutationObserver` | A new card needs its `data-search` words | as ported, on |
| Performance card | One card for preview TDN, trim, phase lock, frames per folder, merge | New card in the System pane | Each switch has its own command; env override notes go with the env twins (storage-settings 1) | as ported |
| Presets carry more settings | Presets carry Log, Clear HDR, phase lock, timecode mode, ramp, clip name and indicators | Extends preset import `allowedKeys` and Core's preset writer | A new setting that should survive a preset needs a key in both | as ported. Touch presets carry the same keys (planned, touch-ui; lane) |
| UI timecode and file timecode apart | Files may carry another timecode mode than the screens; labels Time of Day / Clip | Extends `set_timecode_mode` with `target=` | Any reader of `timecode_mode` must pick the UI or file copy | as ported. Tap sets both unless set apart, labels back (planned, touch-ui 9-14; owner row 9) |

### Touch UI (4)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| Value lists and capped pickers | Own ISO, angle, FPS, WB lists; flicker-free angles; values above `iso_max`/`fps_max` greyed | Replaces the hard-coded lists in `CameraPage.qml`; lists in UI.conf via `set_value_steps`, read by `SettingsBridge` | Add picker values in the list builder, not an options array | as ported. Fork main's fallback caps back (planned, touch-ui; lane) |
| Recording indicators | Red frame, red timecode, audio outline, buffer bar; touch, HDMI, WebUI | Extends the `SettingsBridge` toggle chain and Core's `handleUiToggle` (recipe R3) | A UI.conf default lives three times (UI, Core snapshot, WebUI); change all | outline off (C3, U2), HDMI timecode white until set (U3) |
| Raw readout | Bit depth and Clear HDR on the resolution line, Log marker, time left from stored bits, exact shutter angle | Extends `formatDisplayValue` and friends in `CameraPage.qml`, `formatAngle` in `WCP` | Frame-size estimate copies Core's model | as ported, on |
| Touch preview cap while recording | `APERTAR_UI_PREVIEW_RECORDING_FPS=N` caps preview frames in a take | Beside upstream's preview env knobs, `ApertarPreviewSocketClient` | A measuring knob; stalls Rec Run timecode (UI-16) | as ported; off |

### System and tools (5)

| Feature | What it does | Where it sits in Apertar's code | For further development | State |
| --- | --- | --- | --- | --- |
| Boot Config card (`config.txt`) | Sensor per connector, link frequency, overclock, buses, display; review; save and reboot; free-text edit | New: `src/hardware/BootConfigText.hpp` (1355 lines), own HTTP route and lock, root helper `scripts/apertar-boot-config` | Free text reaches `config.txt` as root (blocker HW-1); does not see `include camera-selection.txt` (HW-6) | through `handleCommand`, no free text, `sudo -n install` (planned, boot-config-helpers 1-21; audit not done) |
| Fan mode through Core's writer | Fan changes no longer race a Boot Config save | Extends `applyFanMode`; UI `SystemActionBridge` sends `set_fan_mode` instead of writing | With Core down the touch UI cannot change the fan (1.6.0 could) | as ported (owner row 19) |
| Real-time scheduling switches | Core under SCHED_FIFO on cores 1-3, or only libcamera's completion thread | Extends `scripts/start-apertar-core.sh` and the capture-priority drop-in (`LimitRTPRIO=80`) | Measured with no effect; `taskset` fails on boards with fewer cores | as ported; off. Removal planned (storage-settings 22) |
| Integrator files and host tests | sudoers and tmpfiles for the root helpers; host tests in `tools/` | Beside upstream's two standby helpers (which live in the UI repo) | Root helpers inside Core are new ground; upstream has no tests | as ported; nothing installed. Helpers go (planned, boot-config-helpers 8-10) |
| Build without libcamera | Core builds and runs `--simulate` without libcamera | Extends the existing `APERTARCORE_HAS_LIBCAMERA` guards | Keep new libcamera code behind the guard (rule CAM-28) | as ported; the review checks both builds per commit |

Count: 9 + 4 + 18 + 14 + 6 + 4 + 5 = 60, the same 60 rows as `feature-list.md`.

## Architecture: what is new, and why it stays

| Mechanism | What it is | Why it stays | How it is shaped like Apertar | What to know to maintain it |
| --- | --- | --- | --- | --- |
| Hardware-file store | `HardwareConfigStore`: one writer for `~/apertar-hardware.conf`, revisions, 20 versions plus a pinned "Before Controls", `.bak`, atomic write, file lock, replaced-file detection | Several writers share one file (Config page, Controls page, IMU, storage switches). DA-3 (Core owns the file), DA-25 (history), DA-20 (stale save merged per key after a review, else refused) | Upstream's `.bak` + `.tmp` + rename sit inside it; the empty / 256 KiB / NUL checks stay in App (C30); a whole-file save writes as 1.6.0 did (C27); readers still parse their own section (rule HW-12) | Write only through `configStore()`. The `X-Apertar-Revision` header gives 409 on a stale page. `APERTAR_SCRIPT_PATHS=ssh` turns on the ssh-only rule for `[run_script]` paths (C29, DA-4) |
| `hwconf` checker | `HardwareConfigText.hpp`: parse, key edit, diff, validate | The Controls page must know pins and keys before it writes (owner row 12) | Advisory for whole-file saves; copies each reader's `key ==` chain | A deliberate second copy of every reader's rules: change the reader and the checker in one commit |
| Mode Ladder | Pure logic in `ModeLadder.hpp`; the FPS picks the mode between takes | Patrik's feature; ran on the Pi 2026-10-28 | Header-only std code (rule CAM-4); store moves into `camera_settings.conf` like `tuning_file` (planned) | Setters that change size, depth, HDR or compression refuse while it is on |
| RAM write buffer and safety stop | Byte-budget queue, red bar, take ends at 90 % with every frame written; REC in the drain discards and starts | Measured on the Pi 5 2026-11-01; DB-61 (discard and start), DB-65, DB-101 (RAM fraction his choice) | Planned: one camera setting, a latch in the queue that sends one `buffer` event through the session callback (`photoWriter_` shape), `wait()` stops the take (`RecordingFailure`, `requestShutdown` shapes) | Upstream has no queue depth in state; `/api/buffer` and the 4 Hz poll exist because a drain holds the mutex `/api/state` needs. Small boards refuse RAM mode by themselves |
| Split clips and merge worker | `part_NNN/` folders every N frames, merged back while idle | exFAT create cost on long takes; DA-105, DB-66, DB-67 | Merge worker copies the trim worker; planned camera settings `frames_per_folder`, `clip_merge_enabled` | Default 0 = never split. Every media path reads both layouts |
| Storage pre-roll | A raw take written and deleted to warm the drive, hidden from REC and tally | Measured on the Pi 5; Patrik's campaigns use it as a capacity reading | Planned: start and end through `handleCommand`, the automatic start sent by `wait()` like the idle timer's `enter_standby`, state in `CC` like `stillExposureStatus()` | Off by default (C5). Keep the journal line `ApertarCore storage preroll: reason=...` and the command name `storage_preroll` (KB scripts parse them) |
| Boot Config card | Edits sensor overlays in `config.txt` in place, with dry-run review and read-back | Patrik switches IMX585 options from the WebUI; a fenced block cannot turn off an earlier `dtoverlay` | Planned: one `handleCommand` block, `GET /api/boot-config` like `GET /api/config`, written with `sudo -n install` like the fan mode | Never caller text into a boot file (HW-1). Audit against Patrik's decisions not done |
| Gestures and switches | Click/Hold per push (`ButtonGesture.hpp`), `[gpio_switches]` | DA-30 (fixed timings), DA-31, DA-36 | Section keys parsed by each reader; shape of `reset_on_start` | Plain Press stays immediate; a wake press is to be consumed (planned) |
| Clip Browser and Viewer | Card grid, in-browser player, Core-side DNG decoder and facts cache | DA-43 (looks and behaves like the touch Clip Browser), DA-48, DA-49, design D19 (phone Back) | Planned: upstream names, classes, `/icons` PNGs; Patrik's dialog, menus and round transport kept | Two DNG decoders now; history entries only while the overlay is open |
| Media tuning file | `~/apertar-media-tune.conf`, `/run` override, `apertar-tune` | Patrik's request of 2026-11-02 | Shape of upstream's `/home/pi/.apertar-tuning`: a bench file env overrides; absent on a stock camera | Process statics go (storage-settings 17) |
| Edge events, phase lock, per-file sync | `poll()` on GPIO edges; fps servo; writeback and 1 s fsync | Owner row 13; DA-35; measured on the rig | Phase lock and sync defaults off on stock (planned) | Each has a handoff paragraph to write (TXT-9) |
| Host tests in `tools/` | Plain `g++` tests outside CMake | Owner row 14 (keep outside CMake) | No test target, like upstream's "no tests" | Build line is the comment at the top of each file |

Reworked back to the Apertar shape (one line each):

| Mechanism of the port | Becomes | Plan |
| --- | --- | --- |
| Second dispatcher before the command lock; `get_controls`, `controls_history` | One chain under `commandMutex_`; reads as GET routes (done C22-C26); `errorReplyBody` codes become one-sentence `errorReply` | `design/command-plane.md` |
| Storage switches in `[storage]`/`[media]`, env twins, `CC` opening the hardware file, header singletons, global hooks | `CaptureSettings` fields in `camera_settings.conf`, store-only setters, queue members | `design/storage-settings.md` |
| Pre-roll worker outside `handleCommand` | Commands from `wait()` | `design/preroll.md` |
| Boot Config HTTP door, free text, three root helpers | `handleCommand` block, card fields only, `sudo -n` fixed tools | `design/boot-config-helpers.md` |
| Five page stores, second poll writer, four command doors, second widget set | One `state`, `sendCommand`, upstream parts | `design/webui-state.md` |
| Size rewrite 2076 -> 2072, probe-wins ceilings, `mode_ladder.conf`, own TDN JSON parser, request-release callback | Both heights from the probe, `min(table, probe)`, camera settings, libyaml, per-frame closures | `design/camera-modes.md` |
| `void` invokables, second event path, tinted tiles, presets missing keys, timecode tap | `bool` invokables, `applyCoreState`, dropdowns, full presets, 1.6.0 tap | `design/touch-ui.md` |
| Checker that blocks, auto-inversion, no first file | Advisory checker, `invert_on_start` off, Core writes the first file once | `design/hardware-inputs.md` |

## A stock camera after the merge

Target: a camera with the original drivers, the 720x720 screen and a 1.6.0 hardware file behaves as 1.6.0. On `work/improve` today it does not yet, in these points:

| Still differs on `work/improve` | Fix |
| --- | --- |
| IMX585: longer size list; Core wants 2072/1036; original driver's binned modes refused (probable) | CAM-1, camera-modes 1-5 (lane) |
| Higher FPS ceilings; lossless ISO 1600, auto ISO, IMX585 lossless past 30 | held, camera-modes 6-7 |
| A button held at start is inverted | hardware-inputs 10 (`invert_on_start`) |
| Edge events replace polling | kept (DA-35) |
| Drive trim on; page-cache drop `sync`, 1 s sync thread, writeback; FAT/NTFS writer rows; raw pool kept; one request per buffer | storage-settings 24, REC-14, CAM-7 |
| No first hardware file is written | hardware-inputs 9 |
| Socket `get_controls`, `controls_history` gone (port-only, not 1.6.0) | see Protocol |

Off by default, and the switch that turns it on:

| Behaviour | Switch |
| --- | --- |
| Mode Ladder | `set_mode_ladder enabled=true` (WebUI Modes) |
| Log | `set_cdng_log value=auto` |
| Speed ramp | `set_fps_speed_ramp` |
| Frame-rate phase lock | `set_fps_phase_lock enabled=true` |
| RAM write buffer | `set_buffer_mode value=ram` (today `[storage] buffer=ram`) |
| Buffer bar, red frame, audio outline | `set_frame_buffer_bar_enabled`, `set_recording_frame_enabled`, `set_audio_recorded_outline_enabled` (UI.conf) |
| HDMI red timecode | `recordingRedTimecodeEnabled` written to UI.conf (switch Red Timecode off and on once) |
| Automatic storage pre-roll | `set_storage_preroll value=on`, `[media] preroll=on`, or `APERTAR_STORAGE_PREROLL=1` |
| Split takes | `set_frames_per_folder value=100..100000` |
| Separate file timecode | `set_timecode_mode target=files` |
| Gestures, switches, `clear_hdr`, remote buttons | `dN_single/_double/_triple/_hold`; `[gpio_switches] enabled=true`; an action key `clear_hdr`; `[gpio_buttons] remoteN` |
| ssh-only script paths | `APERTAR_SCRIPT_PATHS=ssh` in Core's environment (C29) |
| Real-time scheduling | `APERTAR_RT=1`, `APERTAR_RT_CAPTURE_PRIORITY=N` |
| Kernel media tuning, tuning file | `APERTAR_MEDIA_TUNE=1` or `kernel_tune=on`; `apertar-tune init` |
| Preview caps in a take | `APERTAR_WEB_PREVIEW_RECORDING_FPS=N`, `APERTAR_UI_PREVIEW_RECORDING_FPS=N` |
| Fork main's ceiling rule | `APERTAR_FPS_LIMIT=table`; `APERTAR_LOSSLESS_FPS_LIMIT=30` |
| IMX585 windowed Clear HDR gate; IMX283 VMAX floors | module parameters `clearhdr_windowed_binning=1`; `crop_vmax=1` (D2-1) |
| Boot Config save | needs the root helper and sudoers installed (card reads without them) |

Defaults the review put back to 1.6.0: 720x720 square display template and fallback (C2, U1); audio outline off (C3, U2); HDMI timecode white (U3); automatic pre-roll off (C5); Lossy DNG page drop per file (C6); preview temporal denoise on and never touching H.264, ProRes, photo (C7, C9, C10); scripts need a press (C8); whole-file save writes with 1.6.0's three checks (C27, C30); browser may set script paths (C29); IMX283 VMAX floors off (D2-1).

Patrik's rig needs one step each to keep his values: `set_storage_preroll value=on`, `APERTAR_SCRIPT_PATHS=ssh` drop-in, `preview_tdn=false` saved, `recordingRedTimecodeEnabled` in UI.conf (`STATE.md`, "Before you put the improvement branch on the rig").

## Protocol

| Item | Value |
| --- | --- |
| 1.6.0 fields | Every field 1.6.0 publishes is present with the same type: `shape_subset.py smoke-upstream-h.txt smoke-work6.txt` (simulate mode, `work/improve` at `8bfc242`) prints "every base field present with the same type". Re-run here on the saved outputs |
| Commands added (28) | `controls_last_input get_boot_config get_mode_ladder list_actions preview_clip_name scan_i2c set_boot_config set_buffer_mode set_cdng_log set_clip_merge set_clip_name_template set_conform_fps set_controls set_fps_phase_lock set_fps_speed_ramp set_frames_per_folder set_media_trim set_mode_ladder set_preview_tdn set_storage_preroll set_value_steps storage_preroll test_input test_output`, plus `set_recording_frame_enabled set_frame_buffer_bar_enabled set_recording_red_timecode_enabled set_audio_recorded_outline_enabled`. `list_sensor_modes` and `set_clear_hdr` are fork main's |
| Arguments added | `set_iso_auto enabled=false` (ISO Lock), `set_timecode_mode target=ui\|files\|both`; absent = 1.6.0 meaning |
| HTTP routes added (7) | `/api/buffer`, `/api/boot-config`, `/api/boot-config/parse`, `/api/config/history`, `/api/media/clip`, `/api/media/file`, `/api/media/frame` |
| Fields added | `get_state`: 59 top-level (buffer, cdng_log, clip name, ladder, media, preroll, fps/iso max, phase lock, ramp, sensor binning ...); `/api/state`: 53 top-level, 18 in `ui`, 29 in `system`; `/api/config`: `apply boot_copy dpi_lines errors gpio_chips i2c_buses issues model peripherals replaced revision warnings written_at written_by`; `/api/media` item fields. Events `media`, `controls`, `buffer` |
| Removed from the socket in the review | `get_controls` -> `GET /api/config` (C22); `controls_history [name=]` -> `GET /api/config/history[?name=]` (C23). Over ssh: `curl -s localhost:8000/api/config`. Both were port-only |
| Still to change | `errorReplyBody` codes, `set_storage_preroll enabled=`, strict booleans (command-plane 6-16) |

## Raspberry Pi models

Only Patrik's CM5 (IMX585, CFexpress, HDMI, no touch screen) ran any port feature. This review ran nothing on a Pi.

| | Pi 5 / CM5 | Pi 4 / CM4 / 400 | Pi 3 / Zero 2 W |
| --- | --- | --- | --- |
| Run | CM5 only: takes, pull tests, pre-roll, safety stop, Clear HDR, crops, playback | nothing | nothing |
| Recording gates | upstream's, unchanged | upstream's (uncompressed only) | H.264 only; raw features inert |
| Known risks | Player pacing tuned here only (WEB-36) | Changed raw write path, requests, sync, pool memory never run (REC-23, REC-14, CAM-7); ladder shows compressions the board cannot record (CAM-19); IMX585 tables and probe never run on VC4 (CAM-23); scan bound not measured | Boot Config board filters and link rates (HW-24); Zero 2 W `[pi3]` filter unconfirmed |
| All boards | Checker reads `config.txt` as a Pi 5 (HW-22, APP-40); pins fixed to the 40-pin header (HW-25); any DPI line greys GPIO 0-27 (HW-26); `include camera-selection.txt` unseen (HW-6); 8-bit DNG refused in the viewer (REC-24); `APERTAR_RT` `taskset` (APP-15) | | |

Board test list: `raw/sweep-board-support.md` section 4 (T1-T10).

## Dependencies and build

| Item | Value |
| --- | --- |
| Drivers | imx585 and imx283 `cinemate-port` branches, DKMS, kernel 6.12 or later (`<linux/unaligned.h>`), Pi 5/CM5 4-lane. Which branch ships to Apertar: owner row 31 |
| libcamera | The Pi runs the fork `tiramisioux/libcamera` branch `apertar` `6b0b49f` (CcmpUnwrap for 12-bit Clear HDR, fork main's). Which port features need the fork beyond fork main: not determined |
| Files outside the repos | `imx585_clearHDR.json` tuning file |
| Run time | `rubberband-cli` for the stretched WAV; root helpers and sudoers installed by hand for trim, Boot Config save, kernel tune |
| Build | CMake now `LANGUAGES C CXX` and builds vendored `third_party/liblj92` (new in Core). `cmake -DAPERTARCORE_ENABLE_LIBCAMERA=OFF` builds a `--simulate` Core |
| Host tests | `Apertar-Core/tools/`: 16 `*_test.cpp`, 3 `*_test.sh` (18 runs; `dng_payload_write_test.cpp` runs through its `.sh`). Build one with the line at its top, e.g. `g++ -std=c++20 -O2 -Wall -Wextra -I src -I include tools/clip_name_test.cpp -o /tmp/cnt && /tmp/cnt` |

## Open before merging

- Blockers: HW-1 (Boot Config free text as root), CAM-1 (IMX585 crop names), REC-1 (`CC` reads the hardware file), TXT-1 (Core history not reviewable). HW-2 is addressed by C27.
- Decisions audit unfinished: touch-ui, camera-modes, boot-config-helpers and the fixes made (`design/decisions-audit-summary.md`).
- `owner-decisions.md` must be redone from the audit; open there: rows 3, 4, 7-10, 18-20, 23-31.
- Held: step lists (`lanes/core-bugs/`, request 24), camera-modes 6, 7, 11, 14, touch-ui 17, 19, 20, 22, REC-8.
- Lanes not integrated: camera-modes (5 patches), touch-ui (11 patches), remaining command-plane and hardware-inputs commits.
- 12-bit Clear HDR: one capture pair settles H1 (`hdr12/REPORT.md` P7); three questions to Patrik there.
- A Pi pass of every "Needs the Pi" line, then the clean commit series (`commit-plan.md`, TXT-2 to TXT-6).
- The clip-split branch joins the review and gets its own changelog rows.
