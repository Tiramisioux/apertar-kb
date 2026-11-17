# Apertar conventions: the yardstick for the cinemate port

The rule book of original Apertar 1.6.0, merged from eight topic studies after their challenge pass. Use it to review
a contribution and to write new code the Apertar way. It describes upstream. It does not judge the port.

| Item | Value |
| --- | --- |
| Measured on | Core `/home/user/wt/core-upstream` tag `upstream-1.6.0` `35dbe67`; UI `/home/user/wt/ui-upstream` tag `upstream-1.6.0` `43888e5` |
| Evidence refs | **Every `path:line` on this page is `@upstream-1.6.0`.** Re-grep the anchor on any other ref |
| Sources | `raw/conv-core-command-plane.md` (C1), `conv-core-camera.md` (C2), `conv-webui.md` (C3), `conv-hardware-config.md` (C4), `conv-ui-cpp.md` (C5), `conv-ui-qml.md` (C6), `conv-platform-build.md` (C7), `conv-style-commits.md` (C8). All eight present and read, "Final rules" in full |
| Rule set | Only the "Final rules" tables (rules as corrected by the challenger). Challenger downgrades kept. Duplicates merged; the source ids are in brackets after each id |
| Strength | **always** = no counter-example, search named in the source. **usually** = exceptions named. **once** = one precedent |
| Status | Every rule is **confirmed** (read in code) unless marked **probable** |

Short names. Core: `App` = `src/ApertarCoreApp.cpp`, `AppH` = `src/ApertarCoreApp.hpp`, `CC` = `src/camera/CameraController.cpp`,
`CCH` = `src/camera/CameraController.hpp`, `WCP` = `src/web/WebControlPage.cpp`, `WS` = `src/web/WebServer.cpp`,
`CS` = `src/ipc/ControlServer.cpp`, `CP` = `src/ipc/ControlProtocol.cpp`, `Types` = `include/apertar/core/Types.hpp`,
`Caps` = `include/apertar/core/RecordingCapabilities.hpp`. UI: `ACB` = `src/ApertarControlBridge.cpp`, `SB` = `src/SettingsBridge.cpp`,
`SP` = `qml/SettingsPage.qml`, `CPg` = `qml/CameraPage.qml`, `EMW` = `qml/ExternalMonitorWindow.qml`. Other paths are repo-relative,
prefixed `Core/` or `UI/` where the repo is not obvious.

Sizes upstream: `App` 11 025 lines, `CC` 8 834, `WCP` 11 618, `SP` 9 851, `CPg` 4 160. (The 15 083 / 12 931 / 20 963 in
`BRIEF.md` are the port's sizes.)

---

## 1. The original developer's intent in ten lines

1. Core is the single source of truth for camera and capture state. Every surface (touch UI, WebUI, buttons, idle timer) sends the same flat command to one `handleCommand` and gets the same refusals.
2. A take is sacred: the frame path never waits, nothing that shapes the stream or the file changes while recording, and a failure stops the take loudly within a second.
3. The operator is told what is wrong and what to do, in one plain English sentence ("Stop recording before deleting media.").
4. Board and sensor limits are detected at run time, enforced in Core and mirrored in both UIs; nothing is silently downgraded.
5. Few files, few layers, few dependencies: giant owner files, free helpers in an anonymous namespace, no class hierarchies, no frameworks, hand-written JSON and file formats.
6. Duplication is accepted over abstraction: three settings serialisers, three hardware-config templates, per-class INI parsers, option lists copied into Core, WebUI and QML.
7. Each store has one owner: `camera_settings.conf` (Core camera), `UI.conf` (UI preferences, shared live with Core), `apertar-hardware.conf` (wiring, one section per device class).
8. The camera must boot fast and stay up: FFmpeg and other heavy code are lazy plugins, optional hardware never blocks start, boot gates always exit 0.
9. Root access is narrow and never prompts: `sudo -n` with fixed verbs, never a path from the WebUI or config; the WebUI is for a trusted LAN.
10. Code says only what must hold: rare one-line "why" comments, no TODO, no Doxygen, no ticket numbers, no history narration; releases are plain code drops.

---

## 2. Rules

### 2.1 Core command plane (CMD)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| CMD-1 (C1-S01, C1-S05) | Inside Core every change of camera state and every Core write of UI.conf enters through `ApertarCoreApp::handleCommand`. Socket, `POST /api/command`, hardware inputs and the idle timer all call it. The command plane is `src/ApertarCoreApp.{cpp,hpp}`; `src/ipc/` holds only parser and socket server | always | `App:7067`; `App:8462` | An HTTP route, GPIO callback or worker calling `camera_.setX()` or writing UI.conf; a `src/commands/` dir |
| CMD-2 (C1-S02) | The dispatcher is one flat chain of `if (command.name == "...") { ... return ...; }` ending in `errorReply(..., "Unknown command: " + command.name)` | always | `App:9242`; `App:10820` | A handler map, a `switch`, a class per command, a second dispatcher |
| CMD-3 (C1-S03) | One lock, `commandMutex_`, taken on the first line of `handleCommand`, serialises all commands | always | `App:9093`; `App:7032` | A per-feature command mutex |
| CMD-4 (C1-S04) | Guards shared by several commands sit at the top of `handleCommand` as `\|\|` lists with their own sentence; a one-command guard opens that command's block | usually | `App:9095-9117`; `App:9706` | A new capture command missing from the top gates |
| CMD-5 (C1-I01) | Camera setter command: read field, one presence check, `camera_.setX(...)`, reply `settingsBody(camera_.settings())` or `camera_.lastError()` | always | `App:9242-9249`; `App:9439-9446` | Range checks in App duplicating the setter |
| CMD-6 (C1-I02, C1-I11) | UI.conf value command: read `value`, normalise with `normalize<Name>Value()`, refuse if trimmed input differs, write one pair, echo `"snake_key":value` | usually | `App:9802-9813`; `App:669-677` | Raw client string written to UI.conf; an enum + string table for a label |
| CMD-7 (C1-I03, C1-I04) | Command names snake_case: `set_<thing>`, `set_<thing>_enabled`, auto variants as own commands, actions `<noun>_<verb>`. The single argument is `value`, a lone boolean `enabled`, other fields snake_case | usually | `App:9269`; `App:9493`; exceptions `kelvin`, `width`/`height` `App:9315` | `setIso`, `toggle_x`, camelCase fields (outside `apply_preset`) |
| CMD-8 (C1-I05, C1-I09) | A command is one line, one flat object, values are text; booleans arrive as strings and are tested `== "true" \|\| == "1"`; lists travel as one string | always | `App:9486`; `CP:204` | Nested objects or arrays in a command; `command.boolean()` |
| CMD-9 (C1-I06, C1-I08) | Replies only via `okReply(id, fragment)` / `errorReply(id, sentence)`. JSON is written by hand with `std::ostringstream`, `(x ? "true" : "false")`, `escapeJson`; no JSON library | always | `App:108-128`; `App:9222-9238` | A JSON dependency, `std::boolalpha`, a hand-built reply |
| CMD-10 (C1-S13, C2-I13) | Camera state is serialised by three hand-written copies (`settingsBody`, `settingsEvent`, the inline web block in `buildWebStateJson`); a new field goes into all three, next to the same neighbour | usually (web copy lacks four `photo_*` keys `App:7994-7997`; order differs `CC:140`) | `App:167-216`; `CC:136-187` | One shared serialiser written unasked; a field in the reply but not the event |
| CMD-11 (C1-S14) | `get_state` = status keys + `settingsBody`. `/api/state` = the same + groups `system`, `capture`, `ui`, `audio`, `imu`, `device`; UI.conf values go in `"ui":{}` | usually (standby keys top-level `App:7838-7839`) | `App:9238`; `App:7965` | UI.conf values in `get_state` or the `settings` event |
| CMD-12 (C1-S07, C2-S20) | Each store has one owner in Core: `camera_settings.conf` = `CameraController`, UI.conf = App, one `apertar-hardware.conf` section = the class that parses it. UI.conf and preset files also have the touch UI as writer | always | `CC:342-353`; `App:341-348` | `CameraController` reading UI.conf; App writing `camera_settings.conf` |
| CMD-13 (C1-S08) | App keeps no copy of settings: it calls `camera_.settings()` and `readSharedUiSettings()` each time | always | `App:7715`; `App:7037` | A `uiSettings_` member, a cache, a file watcher in Core |
| CMD-14 (C1-S15, C1-N07) | Camera settings outlive a restart: every commit persists the whole file (25 ms debounce, atomic) and is always followed by the broadcast `settings` event | always | `CC:8719-8721`; `App:10827-10840` | A persist without event; a setting saved from App |
| CMD-15 (C1-S16) | Core's UI.conf write is a synchronous read-modify-write of `[General]` under a QLockFile-compatible lock, then an atomic rename; other keys kept | always | `App:1850-1935`; `App:1861` | `std::ofstream` onto UI.conf; Qt linked into Core |
| CMD-16 (C1-S27) | The touch UI writes UI.conf `[General]` itself and sends Core only camera and capture commands. Core's UI.conf commands exist so the WebUI and hardware inputs reach the same keys | always | `UI/src/SettingsBridge.cpp:597-607`; `UI/src/ApertarControlBridge.cpp:633` | The touch UI routing a monitoring aid through Core |
| CMD-17 (C1-S12, C1-I20) | Events are literal JSON strings `{"event":"<name>",...}` (`event` first, no spaces) built at the emit site and passed to `publishEvent`; receivers match with `find` | always (literal shape); usually (one path) | `App:10823-10852`; `CC:139` | An event class hierarchy, a subscriber list, parsed routing |
| CMD-18 (C1-S19, C2-S25) | Parts talk to App only through `std::function` callbacks (constructor for camera and inputs, `start(handler)` for servers); no part holds an App pointer; `CameraController` includes no App, socket, WebUI or input header | always (App side); usually (CC: gyro sidecar `CC:17`) | `App:6783-6792`; `CCH:19-31` | An observer interface, a singleton App pointer |
| CMD-19 (C1-S17, C1-I21) | App owns its threads as `std::thread` members: start sets the flag under the group mutex, stop clears, notifies, joins. `std::lock_guard` in the smallest scope; no lock across a socket send | always (threads); usually (scope) | `App:6825`, `App:10988-11014` | `std::async`, `std::jthread`, a detached thread in App |
| CMD-20 (C1-S18) | Header members: owned components by value first, then state groups split by blank lines, mutex first; cross-thread flags `std::atomic<T> name_{init};` | usually | `AppH:110-124`; `AppH:140-147` | `std::unique_ptr` parts in App, an Impl struct |
| CMD-21 (C1-S20, C1-S21) | A slow job that must not hold the command lock becomes a worker thread with its own state group; clients poll. Periodic supervision lives in the 1 Hz loop of `wait()` | once | `App:8957-9089`; `App:7021-7053` | A job queue, futures returned to the client, a sleeping poll thread |
| CMD-22 (C1-S22, C1-S23) | A preset is applied with one flat `apply_preset` (camelCase keys, `camera<Name>` for camera values) and one `applyCapturePreset` transaction. Favourites are an ordered id list; Core drops ids not in `favoriteCandidateOrder()` | once | `App:10230-10527`; `App:727-763` | A preset applied as a list of `set_*` commands |
| CMD-23 (C1-S24) | A launch option is an `Options` member, a hand-written `if (arg == "--x")` in `main`, a usage line and a README row | always | `AppH:32-38`; `src/main.cpp:52-82` | `getopt`, an env switch read in `handleCommand` |
| CMD-24 (C1-S25) | `start()` brings parts up in fixed order and unwinds by hand on a required failure; optional hardware logs "... disabled: <reason>" and start continues | usually | `App:6838-6878`; `App:6881-6897` | Core start aborting for a missing accessory |
| CMD-25 (C1-I17, C1-I19) | A shape repeated inside one function becomes a named local lambda; a shell probe used by the 1 Hz poll caches itself with a function-local static mutex | usually | `App:9478`; `App:2266-2283` | A template or macro for command blocks; a member cache or background poller |
| CMD-26 (C1-I18) | A command changing camera and UI.conf keeps both in step (commit callback or restore on failure) | usually (`App:9433` ignores a write result) | `App:9594-9609`; `CC:8634-8656` | Camera changed, UI.conf write failed, reply ok |
| CMD-27 (C1-N01, C2-N1) | Every client uses the same setter and busy checks and gets the effective value back | always | `README.md:271`; `CC:8713-8715` | Camera logic in a route or in JS; UI state Core does not know |
| CMD-28 (C1-N02) | A refusal is an operator sentence shown as written (touch UI `lastError`, WebUI toast) | always | `UI/src/ApertarControlBridge.cpp:1084-1086`; `WCP:9128-9132` | A reply the UI must translate; a silent no-op |
| CMD-29 (C1-N05) | Failures are reported: the recording failure is checked before every command and once a second; state carries the error text and the dropped-frame flag | always | `App:9094`; `App:7033` | A recording error only in the log |
| CMD-30 (C1-N11, C7-N10) | Core and UI ship together: no protocol version, missing fields default, unknown keys ignored | always | `README.md:306`; `App:10820` | A version handshake |

### 2.2 Camera and recorders (CAM)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| CAM-1 (C2-S1) | libcamera is used only in `CC`; no header includes a libcamera header | always | `CC:69-79`; `CCH:3-13` | A new `.cpp`/`.hpp` with `<libcamera/...>` |
| CAM-2 (C2-S2) | No class hierarchy for sensors, recorders, encoders: no `virtual`, base class, interface or factory. Dispatch is `if`/`switch` on the format | always | `CC:7507-7511`; `CC:5589-5647` | `class ISensor`, a recorder base class |
| CAM-3 (C2-S3) | New camera behaviour goes into `CC`: a free helper in the anonymous namespace plus a `CameraSession` member. Only a file format or a new library gets its own directory | usually (`src/prores`, `src/cdng`, `src/mlv`) | `CC:1797-1880`; `CC:8302-8500` | A new `src/camera/Foo.cpp` for logic that needs no new library |
| CAM-4 (C2-S4, C1-S06) | Pure logic is a small header-only file named after the concept, `inline` free functions in `namespace apertar`, often with one includer | usually | `src/camera/StillBracketing.hpp:8-19`; `src/hardware/PowerButtonGesture.hpp` | A stateful class for pure maths; a `utils.cpp` grab bag |
| CAM-5 (C2-S5) | A type goes in `include/apertar/core/` only if it crosses the App/CC or plugin boundary | always (4 files) | `Types:124-162`; `Caps:11-106` | Internal recorder types in `include/` |
| CAM-6 (C2-S6) | `src/util/` stays small (clip latches, `atomicWrite`). Small string helpers are copied per `.cpp`; shared only where two areas already share (`escapeJson`, `atomicWrite`) | usually | `src/util/SettingsFile.hpp:25-56`; `CC:95` | A new `StringUtils.hpp`; merging the copies unasked |
| CAM-7 (C2-S7, C2-I1) | The public surface is `bool` setters on `CameraController`, one per command, plus `lastError()`. Setter shape: lock, gate with `setErrorLocked("..."); return false;`, range check, copy `settings_`, `applySettingsLocked` | always (surface); usually (shape) | `CCH:39-64`; `CC:7774-7786` | A setter returning an error code; App poking session state |
| CAM-8 (C2-S8, C2-S9) | Every setter commits through `applySettingsLocked(next, reconfigure)`: controls for the next request (`false`) or full reconfigure (`true`). No third apply path | usually (`setTuningFile` own path `CC:8044-8112`) | `CC:8659-8723`; `CC:5495-5524` | A direct V4L2 control write, a partial restart |
| CAM-9 (C2-S10) | `controlsForSettings` is the one function that turns settings into libcamera controls | usually (bracket shots `CC:6522-6526`) | `CC:2005-2144` | Controls set from settings in several places |
| CAM-10 (C2-I24) | Every public `CameraController` method takes `mutex_` first; helpers that need it end in `Locked`; events leave under the lock | usually | `CC:8178`; `CC:8773-8779` | A second settings mutex; an unlocked public method |
| CAM-11 (C2-S11, C2-S12) | Sensors are told apart by the private `SensorFamily` enum, detected by substring of the camera id; sensor knowledge is `switch (sensorFamily)` in free functions. Each layer (CC, App, WCP, QML) keeps its own sensor tables and matches the published `"sensor"` name | usually (S11); always (S12) | `CC:1882-1888`; `CC:2151-2167` | A sensor class or table file; a new sensor in one layer only; a shared capability API replacing the copies |
| CAM-12 (C2-S13) | Record formats are one flat enum; a sub-option is its own enum + field + setter + command | always | `Types:45-68`; `App:9326-9386` | A generic `set_format_option` command |
| CAM-13 (C2-S14, C2-S15, C7-S5) | Board capability is decided once in `Caps` from the device tree, published as `recording_capabilities`, enforced at setter, sanitise and record start. Sanitise order: board, absolute ranges, sensor | always | `Caps:18-35`; `CC:2707-2744` | Pi-model checks inline in setters; UI detecting the board to allow a format |
| CAM-14 (C2-S16, C2-S17) | A recorder is a self-contained class: `start...(folder, settings, ..., std::string *error)`, `enqueue...() -> bool`, `stop()`, `active()`, `error()`. Clip folders come from one allocator, `reserveClipFolder` | usually (S16); once (S17) | `CC:3268`; `CC:3646-3675` | A recorder calling back into the session; a second folder allocator |
| CAM-15 (C2-S18, C7-S3, C7-S16) | Anything linking libav is a `MODULE` plugin, `PREFIX ""`, loaded by `dlopen` at first use with an ABI check; search env, exe dir, fixed path. Runtime-only system libs (ALSA) are dlopened by soname | always | `Core/CMakeLists.txt:143-169`; `src/prores/ProresRecorder.cpp:25-50` | `target_link_libraries(apertar-core ... avcodec)` |
| CAM-16 (C2-I23) | A plugin exports `apertar_<plugin>_{abi,create,encode,finish,destroy}` with a POD config in `...PluginApi.hpp` | always | `src/prores/ProresPlugin.cpp:13-56` | C++ classes across the plugin boundary |
| CAM-17 (C2-S19) | Per-take inputs that are not camera settings travel as option structs built by App | always | `Types:184-201`; `App:10624-10709` | Audio or gyro take options added to `CaptureSettings` |
| CAM-18 (C2-S21) | A runtime capability is a non-persisted `CaptureSettings` field with a trailing `// Runtime ...` comment, filled before settings leave Core | always | `Types:132`; `CC:8779-8781` | A separate capabilities command; a capability saved to disk |
| CAM-19 (C2-S22, C2-N11) | The camera side never reads `apertar-hardware.conf`; internal tuning stays out of operator files and the README | always | `CC:745-777`; `LossyDngEncoder.cpp:322-324` | A recorder knob in a hardware-conf section or the settings UI |
| CAM-20 (C2-S23) | Few dependencies; file formats are written by hand | usually (JPEG, libav) | `Core/CMakeLists.txt:25-45`; `src/cdng/IfdBuilder.hpp` | A new library for a container or still format |
| CAM-21 (C2-I2, C1-I12) | Out-of-absolute-range values are rejected with a sentence; sensor, board and format limits are applied silently and the effective value is returned | always | `CC:7777-7780`; `CC:2740-2741` | Rejecting a value that is only above the mode's fps cap |
| CAM-22 (C2-I4) | Encoders throw; the worker loop or public boundary catches and latches the first error; plugins return `int` + `char *error` | always | `CC:3747-3752`; `src/prores/ProresPluginApi.hpp:22-25` | An exception escaping a `CameraController` method |
| CAM-23 (C2-I7, C2-I8) | Log take start (all knobs), take stop (stats), drops, write failures, configure, tuning chosen, fallbacks; never setter calls or normal frames. Repeats are rate-limited by `n == 1 \|\| n % N == 0` | always (I7); usually (I8) | `CC:3353-3374`; `CC:3538` | Per-frame or per-setter log lines; time-based throttling helpers |
| CAM-24 (C2-I9, C1-I22, C7-I1) | A bench knob is an env var `APERTAR_<AREA>_<KNOB>` read at the point of use with default and bounds (`unsignedEnvValue`, `boolEnvValue`), echoed in the take-start log line; not a setting, not a command, not in README | usually (`QRAW_LOSSYDNG_ASYNCWRITE`; `CC:3981-3985` fails the start) | `CC:1027-1061`; `CC:3329-3330` | A tuning config file, socket command or settings card for an internal knob |
| CAM-25 (C2-I14, C2-I15) | Defaults are `CaptureSettings` member initialisers. Loading is one `else if (key == ...)` chain in `try/catch(...)`; a malformed line keeps the default; retired keys are still read | always | `Types:124-161`; `CC:650-723` | A second defaults table; strict parsing that fails start |
| CAM-26 (C2-I11) | Wire names snake_case; `toString` at the foot of the enum's header; reverse parser in the `.cpp`, lowercases by hand, unknown maps to default | usually (App rejects unknown `App:824-844`) | `Types:254-285`; `CC:199-219` | A generic enum-reflection helper |
| CAM-27 (C2-I16, C2-I17) | Worker threads are `std::thread` members with a mutex, condition variable(s), `std::deque` queue(s) and a stop flag; counters `std::atomic<uint64_t>`. Process-wide one-offs are function-local statics | usually (I16); always (I17) | `CC:3922-3927`; `Caps:37-50` | A thread-pool library, lock-free queues, global singletons |
| CAM-28 (C2-I18) | Build options are `#if APERTARCORE_HAS_X` with an `#else` that keeps the signature and returns neutral; Core builds without libcamera | always | `CC:5393-5397`; `CC:1708-1795` | Code that only compiles with libcamera or libav |
| CAM-29 (C2-I25) | Persisted text files are written with `settingsFile::atomicWrite` (temp, fsync, rename, dir fsync) | usually (`App:1561-1566`) | `src/util/SettingsFile.hpp:37-56`; `CC:789` | `std::ofstream(path, trunc)` on a settings file |
| CAM-30 (C2-N2, C1-N09) | The frame path never waits: callbacks never block on storage or encoders, queues are bounded, a full queue drops before copying, stalled clients are dropped, no call back into the controller from libcamera's thread | always | `CC:6927-6930`; `App:8103-8104` | Blocking `push`, unbounded queue, blocking write in a preview callback |
| CAM-31 (C2-N5, C1-N03) | During a take only exposure, white balance, focus and timecode change; stream, file, fps, format, media and colour-pipeline changes are refused with a sentence | usually (`setTimecodeMode` ungated but feeds DNG metadata `CC:8176-8182`, **probable**) | `CC:7715`; `App:9105-9107` | A stream-shaping setter without a `recording_` check |
| CAM-32 (C2-N17, C1-N04, C2-N15) | Recording, timelapse, pending still writes, standby, media actions and the speed test exclude each other. Each entry point refuses with "Stop/Wait/Wake ... before ..." | always | `CC:8224`; `App:9095-9110` | A new capture mode that starts while another runs |
| CAM-33 (C2-N4, C2-N3) | A write or encode failure stops the take within about a second with the first error; a failed start leaves the camera ready. Dropped frames are reported once per clip and do not stop the take | usually (lossy DNG write errors only logged `LossyDngEncoder.cpp:228-232`; WebUI shows no drop warning) | `src/util/RecordingFailure.hpp:7-16`; `CC:7580-7584` | Errors only logged; stopping the take on a drop |
| CAM-34 (C2-N9, C1-N06) | A failed change restores the previous mode; `Error` state only when that also fails | always | `CC:8692-8709`; `CC:8087-8105` | A reconfigure failure that leaves the camera stopped |
| CAM-35 (C2-N6, C2-N7) | Metadata is measured, not guessed (a RAW frame without measured WB is not written); capabilities are detected at run time | usually (fallback black level `CC:2933-2940`; sensor tables are code) | `CC:6857-6863`; `CC:5812-5835` | Hard-coded WB in DNGs; a config switch telling Core its board |
| CAM-36 (C2-N8) | No silent downgrade of what is recorded; the operator gets a sentence naming the hardware | usually | `Caps:64-77`; `CC:5535-5537` | Quietly recording another format or size |
| CAM-37 (C2-N10) | Media is never overwritten; stills are durable before announced; clip frames are not synced one by one | always | `CC:3667-3673`; `src/util/AtomicStillFile.hpp:85-88` | Fixed clip names; `fsync` per video frame |
| CAM-38 (C2-N12) | The same source builds against different libcamera forks, without libcamera, without libav; only mainline controls | always | `CC:3084-3086`; `Core/CMakeLists.txt:133-173` | `controls::rpi::` without a guard |
| CAM-39 (C2-N13, C1-N12, C6-N8) | Monitoring looks and aids are UI state: never baked into RAW or into footage, changeable during a take | always | `README.md:58`; `CC:3213-3224` | A preview LUT applied to DNG data; a zebra flag in `CaptureSettings` |
| CAM-40 (C2-N14) | Each record format and still mode remembers its own settings; tuning, timecode, metering stay global | always | `CC:7939-7955`; `CC:8725-8749` | A new global setting not carried over at `CC:7945-7951` |
| CAM-41 (C2-N16) | RAW capture is one YUV monitoring stream plus one RAW stream; only H.264 and ProRes change the stream set | once | `CC:6031-6037` | A third stream for RAW formats |

### 2.3 WebUI (WEB)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| WEB-1 (C3-S1) | All WebUI HTML, CSS and JS live in the single raw string of `webControlPageHtml()` in `WCP`, ordered style, body, script; no separate files, no external links | always | `WCP:5-7`; `App:7102-7107` | `src/web/foo.js`, `<script src>`, a CDN link, a second page string |
| WEB-2 (C3-S2) | The main page holds only camera-critical cards; everything else is a `settings-card` in one of the 9 `settings-panel[data-panel]` sections, listed in the nav and in `settingsPanelMeta` | always | `WCP:2456-2700`; `WCP:4164-4201` | A main-page card for a non-critical feature; a panel without nav and meta entries |
| WEB-3 (C3-S3, C1-S09) | Camera and system actions go through `POST /api/command` with the socket's flat command via `sendCommand` | usually (`user_activity` raw `fetch` `WCP:11509`) | `App:7637-7642`; `WCP:9109-9145` | `POST /api/iso`, a REST resource per setting, a second fetch wrapper |
| WEB-4 (C3-S9) | Reading or writing files in the media, preset or config libraries is a dedicated `/api/...` route; camera and system state changes are commands | always | `App:7440`; `App:10230` | A `delete_media` socket command used by the page; a route that changes camera settings |
| WEB-5 (C3-S4, C1-S10, C3-I12) | A route is one more `if (request.method == "X" && request.path == "/api/...")` branch in `handleWebRequest` before `/api/command`; GET/POST/OPTIONS only; query via `queryParameterValue`; each branch builds its own `WebServer::Response` with `contentType = "application/json; charset=utf-8"` and `okReply(-1, ...)`/`errorReply(-1, ...)` | always (shape); usually (helper delegation) | `App:7154-7159`; `App:7644-7649` | A router table, regex routing, `PUT`/`DELETE`, a new `jsonResponse()` helper refactoring all routes |
| WEB-6 (C3-S5, C1-N10) | Security is server-wide in `WebServer`: same-origin check and 1 MiB cap. Routes add only busy refusals and path guards. The WebUI is for a trusted LAN: no accounts, no TLS | always | `WS:156-171`; `README.md:130` | CORS headers, tokens or auth in a route; a raised cap for one route |
| WEB-7 (C1-S26) | No push channel: the page polls `GET /api/state` at 1 Hz; events reach socket clients only | always | `WCP:11609`; `App:10851` | An SSE or WebSocket endpoint |
| WEB-8 (C3-S6) | Pill option lists are top-level `const <x>Options` label arrays near `const fpsPresets`; fixed `<select>` choices may be literal `<option>` HTML; lists shared with Core and QML are duplicated by hand | usually | `WCP:4040-4090`; `WCP:4091` vs `App:727` | Option lists fetched from a new endpoint; centralising the copies unasked |
| WEB-9 (C3-S7) | Static assets are PNG icons only, from `src/web/icons` via `GET /icons/<name>`, reusing the touch UI's icon names | always | `App:7124-7151`; `WCP:2746-2778` | Inline SVG, icon fonts, `data:` images |
| WEB-10 (C3-S8) | A control that is also a favourite has two handlers, in `renderSnapshot` (via `sendCommand`) and in `renderFavoriteControls` (via `dispatchFavoriteCommand`); add both | usually | `WCP:6915`; `WCP:10111` | A favourite toggle that works on its panel only |
| WEB-11 (C3-I1) | Plain flat JS: named functions at one indent level, `const`/`let`, arrow callbacks, `async/await`, `fetch`; no framework, module, class, bundler, `var`, `.then` chains or browser storage | always | `WCP:4038-11611` (grep) | A framework, an ES module, `localStorage` |
| WEB-12 (C3-I2) | All client state lives in the one global `state` object; render only from `state.snapshot` | always (module level) | `WCP:4204-4266` | New module-level `let`; state in DOM attributes |
| WEB-13 (C3-I3) | Poll, render, command: `fetchState` every 1 s -> `renderSnapshot`; `sendCommand` patches via `applyCommandSnapshotPatch`, rolls back on `ok:false`, refreshes. A new `set_*` command gets a patch `case` | always (loop); usually (case: 4 missing) | `WCP:9109-9145`; `WCP:8678-9108` | Per-control polling; optimistic update without rollback |
| WEB-14 (C3-I4) | Each handler is `async`, `try { await sendCommand({ cmd: "...", ... }) } catch (error) { showToast(error.message, true) }`, Core's text verbatim | usually | `WCP:11088-11098`; 86 `showToast(error.message, true)` | Swallowed errors, `alert()`, rewritten error text |
| WEB-15 (C3-I5) | Choice controls are pill grids via `buildOptionButtons`; On/Off is a two-pill grid over `toggleOptions` sending `enabled: "true"/"false"`; selects via `ensureSelectOptions`; continuous values via `input.slider` | usually (standby USB select sends a JSON bool `WCP:11527`) | `WCP:9147-9167`; `WCP:10109-10115` | Checkboxes, switch widgets, custom dropdowns |
| WEB-16 (C3-I9, C3-I10, C3-I11) | DOM is built with `createElement` + `textContent`/`setText`; `innerHTML` only to clear. Library fetches use `{ cache: "no-store" }` and throw `new Error(payload.error \|\| "Could not ...")`. No console logging except WebGL `console.warn` | always | `WCP:6201`; `WCP:10224` | Template-literal HTML into `innerHTML`; `console.log` traces |
| WEB-17 (C3-I6) | Ids camelCase with region prefix and kind suffix (`settings<Thing>Options/Select/Value/Button/Card`); classes kebab-case with `active`/`disabled`/`hidden`; functions `apply<X>Selection`, `request<Action>`, `fetch<X>`, `render<X>` | always | `WCP:3268`; `WCP:11262` | snake_case ids, BEM, `is-active`, `handleXClick` |
| WEB-18 (C3-I7) | No comments, banners or JSDoc in the page | always (2 comment lines in 7 573 JS lines) | `WCP:8474-8475` | Section banners, HTML comments |
| WEB-19 (C3-I8) | Dark zinc look: `:root` tokens where they exist, literal zinc hex otherwise, white = selected, red tint = danger, large radii; unavailable choices `disabled`, non-applicable controls `.hidden` | usually | `WCP:15-43`; `WCP:790-803` | A light theme; removing unavailable choices |
| WEB-20 (C3-N2) | Busy and during-take rules are enforced in Core; the page only disables matching controls and shows Core's refusal | always | `App:7514-7520`; `WCP:9510` | Page-only checks |
| WEB-21 (C3-N3) | Only destructive or system-level actions ask, with `window.confirm` phrased as a question naming the effect | always (8 confirms) | `WCP:10307`; `WCP:11266` | Custom modal confirms; confirms on routine settings |
| WEB-22 (C3-N4) | One toast: error toast for every failure; success toast for select/field/button settings in System, Power, Info cards and system actions; none for pills or main-page controls | usually | `WCP:7804-7813`; `WCP:11094` | Toasts on every pill tap |
| WEB-23 (C3-N5, C3-N6) | Mirror the touch UI's concepts, order and wording; WebUI-only features only where a browser adds value (config editor, downloads, MJPEG). Card copy is one sentence ending in a period | usually | `UI/qml/SettingsPage.qml:827-837` vs `WCP:2745-2777`; `WCP:3606` | Diverging wording or order; a half-working Wi-Fi control |
| WEB-24 (C3-N7) | Leave the page's structural rough edges (see section 4) | once each | `WCP:6119-6128`; `WCP:9327-10206` | Splitting `renderSnapshot`, renaming panels as a side effect |

### 2.4 Hardware and config (HW)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| HW-1 (C4-S1) | Each input device is a class pair `src/hardware/<Device>.{hpp,cpp}`, held by value in `ApertarCoreApp`, built with a callback lambda, started in `start()`, stopped in `stop()`; outputs are default-constructed members | usually (IMU in `CC:7517`; INA219 free functions `App:4450`; script runner on demand) | `AppH:114-121`; `App:6881-6898` | A device manager or registry; a device started from a command |
| HW-2 (C4-S2) | Each class parses its own section(s) in a `static loadConfig()` with its own file-local helpers (`trimAscii`, `normalizeToken`, `parseConfigInteger`, `parseConfigBool`, `hardwareConfigCandidatePaths`); no shared INI parser | always (no shared parser); usually (shape) | `src/hardware/GpioInput.cpp:27-106`; `:373` | A `HardwareConfig` class all devices call; deduping the copies |
| HW-3 (C4-S3, C1-S11) | Every camera or setting change from hardware ends in `dispatchHardwareInputCommand` -> `handleCommand` (id -1); the hardware path only reads camera state. UI-only actions are `hardware_action` events | always (end point); usually (entry chain) | `App:8458-8466`; `App:8949-8951` | A GPIO callback calling `camera_.startRecording()` |
| HW-4 (C4-S4) | Outputs (tally LED, trigger) are driven only from published events in `handleTriggerEvent`; initial state seeded once after `start()` | always | `App:10854-10889`; `App:6897-6898` | `pulse()` called inside recording code |
| HW-5 (C4-S7, C4-N2) | Take-protection guards live in the command handler or the `CameraController` setter; inputs inherit them. In Standby a press only wakes and is consumed; rotation never wakes | always | `App:9105-9107`; `App:8642-8656` | A guard only in a hardware branch; a Standby press also firing its action |
| HW-6 (C4-S8) | `src/hardware/` has no app knowledge: includes only std, Linux and hardware headers; reaches the app through injected callbacks | always | `src/hardware/GpioInput.hpp:15-17`; `App:6785-6792` | A hardware class including `CameraController.hpp` |
| HW-7 (C4-S5) | `apertar-hardware.conf` templates are C++ strings in three places (Core `defaultHardwareConfigTemplate`, UI `DisplayConfigBridge`, UI `Ina219Bridge`); a new section or key goes into all three by hand | always | `App:4291-4404`; `UI/src/DisplayConfigBridge.cpp:41-326` | A `config/*.example` as source of truth; a key in one template only |
| HW-8 (C4-S6) | Programmatic writes edit one key in place (comments and order kept) and replace via `.tmp` + `rename` / `QSaveFile`; the WebUI writes the raw text with a `.bak` | always | `src/hardware/Mpu6050RecordingSession.cpp:604-713`; `App:5323-5385` | Regenerating the file from a struct |
| HW-9 (C4-S10, C7-S11) | Write only to the editable path (`$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf`), never `/boot`; read via the copied list env -> `/home/pi` -> `/boot/firmware` -> `/boot` | usually (`UI/src/WifiBridge.cpp:21-23`) | `App:4251-4276`; `src/hardware/GpioInput.cpp:60` | Writing `/boot/...`; a new `/etc/apertar/` |
| HW-10 (C4-S11) | The hardware file holds wiring; operator preferences go to UI.conf and buttons flip them with `set_*_enabled` | usually (`[network]`, `[display]`) | `App:344-347`; `App:8468-8478` | A UI preference stored in `apertar-hardware.conf` |
| HW-11 (C4-I1) | Section and key aliases are flat `key == "a" \|\| key == "b"` chains after `normalizeToken`; common sets `bus/channel/i2c_bus`, `address/addr`, `chip/gpiochip/gpio_chip` | always (shape); usually (set) | `src/hardware/Pcf8574Input.cpp:366-371`; `src/hardware/GpioInput.cpp:431` | An alias map or schema |
| HW-12 (C4-I2, C4-N7) | Defaults are in-class initialisers of a private `struct Config`; numbers clamped with `std::clamp`; unparsable values keep the default silently; unknown keys ignored; only mapping errors, unknown actions and script problems are logged | usually (INA219 range-rejects `App:4493-4498`; script runner throws) | `src/hardware/GpioInput.hpp:45-57`; `src/hardware/GpioInput.cpp:441-445` | Refusing to start on an unknown key |
| HW-13 (C4-I3) | Hardware problems are one plain `std::cerr` line with a device prefix: `"<Device> input: "` deduped by `setLastError` for inputs; `"ApertarCore <device>: "` for outputs, IMU, scripts | always (prefix, cerr); usually (which prefix) | `src/hardware/GpioInput.cpp:611-619`; `src/hardware/TriggerOutput.cpp:695` | A logging framework, a log line per poll |
| HW-14 (C4-I4) | Button and encoder inputs poll on their own `std::thread` with `sleep_for(pollMs)`, retry open every 1000 ms and reads every 250 ms forever, debounce with the copied observed/stable state machine | usually (power key evdev; Grove deadband; outputs worker + condvar) | `src/hardware/GpioInput.cpp:643-710`; `src/hardware/Pcf8574Input.cpp:479-523` | An async framework; giving up after N failures; a shared debounce class |
| HW-15 (C4-I5) | Each input normalises action names with its own `normalizeSingleAction` wrapped by `hardware::normalizeButtonMapping`; unknown tokens pass through; parametric names (`iso200`) are parsed only in the handler | always | `src/hardware/GpioInput.cpp:108-206`; `src/hardware/ButtonActionList.hpp:110-116` | Validating action names at load; an action enum |
| HW-16 (C4-I6) | C++ talks to hardware through raw Linux interfaces: `/dev/i2c-N` + `ioctl(I2C_SLAVE)`, GPIO char-dev v2 ioctls, evdev | usually (embedded Python uses `smbus`) | `src/hardware/Pcf8574Input.cpp:392-424`; `src/hardware/GpioInput.cpp:530-570` | `find_package(libgpiod)`, sysfs GPIO |
| HW-17 (C4-I7) | GPIO chip default `auto`: scan `/dev/gpiochip0..9`, score `rp1` +100, `pinctrl_bcm*` +90, `raspberrypi_exp` -50; an explicit path skips the scan. Each GPIO user has its own `gpioChipScore` | always | `src/hardware/GpioInput.cpp:238-262`; `:431-432` | A hard-coded `/dev/gpiochip4`; a board-model key |
| HW-18 (C4-N1) | Device wiring is read once at process start; a change needs a Core or UI restart, and the WebUI says so. IMU and `[run_script]` are read per use | usually | `App:6881-6898`; `WCP:3868` | A file watcher or hot reload added unasked |
| HW-19 (C4-N3) | `apertar-hardware.conf` is the operator's one hand-edited surface for wiring; behaviour (action semantics, step lists, battery curve, chip scoring, limits 6 actions / 5 scripts) is fixed in code. The WebUI offers a raw text editor, not forms | usually | `src/hardware/ButtonActionList.hpp:14-15`; `WCP:3840-3870` | Step lists in config; a forms-based hardware editor |
| HW-20 (C4-N4) | Control and output accessories ship disabled in the templates; INA219 (bus 4) and the CFexpress hat (bus 10) ship enabled | usually (IMU default differs per template) | `App:4298-4305`; `App:4343-4344` | A new accessory enabled by default |
| HW-21 (C4-N5) | Two processes may touch the same hardware: Core and UI each read `[ina219]` and program the chip, each write `[imu]` keys; no IPC lock | usually | `App:4602-4626`; `UI/src/Ina219Bridge.cpp:490-568` | A lock daemon or moving INA219 into one process unasked |
| HW-22 (C4-N6) | Hardware-input health stays out of state JSON and UIs; problems go to the journal. IMU status is the exception | usually | `App:6881-6896`; `App:9681` | New `hardware_status` fields |
| HW-23 (C4-S9, C7-S1) | Each new `.cpp` is listed by name in `add_executable(apertar-core ...)`; no glob | always (Core) | `Core/CMakeLists.txt:69-96`; `:83-91` | `file(GLOB ...)`; a static library for hardware |

### 2.5 UI C++ (UIC)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| UIC-1 (C5-S1) | QML-facing objects are stack objects in `main()`, wired by setter injection and `QObject::connect` there, exposed by `setContextProperty`; `qmlRegisterType` only for visual QQuickItems; no singletons | usually | `UI/src/main.cpp:291-311`; `:374-396` | `qmlRegisterSingletonType`, `QML_ELEMENT` bridge, a bridge built inside another |
| UIC-2 (C5-S2, C8-M2) | One concern per `<Concern>Bridge.hpp/.cpp` pair (class = file name), both in `add_executable(ApertarUI ...)`. Lowercase legacy playback files stay as they are | usually | `UI/CMakeLists.txt:63-125`; `UI/src/WifiBridge.hpp:10` | A new concern added into an existing bridge; renaming `cliplistmodel.h` |
| UIC-3 (C5-S3') | Camera and control commands go through `ApertarControlBridge::sendCoreCommand(name, flat args, &reply)`; a bridge with its own long Core operation may keep a small private socket client, same JSON-line protocol and `APERTAR_CONTROL_SOCKET` override | usually | `ACB:1013-1106`; `UI/src/MediaStatusBridge.cpp:20-42` | A generic shared Core client class; a new IPC channel |
| UIC-4 (C5-S4) | Core state reaches QML in `applyCoreState`: display-string settings as `if (state.contains("snake_key")) setXValue(formatXValue(...))`; bools, counters, objects by inline compare/assign/emit | usually | `ACB:1475-1476`; `ACB:1263-1312` | QML reading a raw JSON blob; a second state parser |
| UIC-5 (C5-S5, C5-S10) | UI preferences are `SettingsBridge` READ/WRITE/NOTIFY properties backed by `QSettings("CinePi","UI")`. Core camera values are cached only under `camera/*` by `saveCurrentCameraSettings`, as placeholders | usually | `SB:287`; `ACB:886` | A preference in a new file or QML `Settings`; cached camera values treated as truth |
| UIC-6 (C5-S6, C5-N3) | Recording capability comes from Core's `recording_capabilities`; the bridge repeats Core's limit as an operator message before sending. Local model reads only for render path, display info, helper safety | usually | `ACB:1285-1303`; `ACB:432-441` | UI probing the Pi model to enable a recording format |
| UIC-7 (C5-S8, C6-S19) | The HDMI monitor process (`runMonitorOnly`) builds its own bridge set; every context property shared QML uses must exist there too, real or `nullptr`, or be `typeof`-guarded | once (only place) | `UI/src/main.cpp:131-154` | A new context property only in `main()`, giving ReferenceErrors on HDMI |
| UIC-8 (C5-S9) | A hardware bridge reads its own `apertar-hardware.conf` section read-only via `QSettings(path, IniFormat)`; UI-private state gets its own `QSettings(org, app)` store | usually | `UI/src/DisplayConfigBridge.cpp:595`; `UI/src/SleepManager.cpp:56` | A central hardware-config class |
| UIC-9 (C5-I1, C5-I9) | Command invokables return `bool`; on failure they set an error property (usually `lastError`) to a full sentence that says what failed and what to do, and return `false`; no throw, no log | usually | `ACB:257-261`; `UI/src/MediaStatusBridge.cpp:25` | `void` invokables, `qWarning` instead of a message, "Failed" |
| UIC-10 (C5-I2) | `ApertarControlBridge` command invokables are `apply<Thing>(const QString &displayValue)`; actions are verbs (`setRecording`, `capturePhoto`, `calibrateGyro`) | usually | `UI/src/ApertarControlBridge.hpp:111-141` | `changeFoo`/`updateFoo` for a camera setting |
| UIC-11 (C5-I3) | Camera settings reach QML as display strings; the bridge owns `parse*Value`/`format*Value` pairs | always (ACB) | `UI/src/ApertarControlBridge.hpp:211-243`; `ACB:1711-1716` | QML formatting raw Core numbers |
| UIC-12 (C5-I4) | Flat scalar arguments; booleans as `"true"`/`"false"` strings | usually | `ACB:727`; `ACB:791-794` | Nested JSON in a command |
| UIC-13 (C5-I5, C5-N5) | UI.conf key = camelCase property name; default inline in the constructor read; setter writes under `if (!m_externalSettingsSyncing)`; every key is re-read in `pollExternalSettings` and included in presets | always (I5); usually (N5: `*Order` keys except favourites) | `SB:324-407`; `SB:502-590` | snake_case keys; a key read only at construction |
| UIC-14 (C5-I7) | App-owned Pi paths are literals with an `APERTAR_*` env override next to them; kernel `/sys` paths are plain literals | usually | `ACB:1032`; `UI/src/SystemStatsBridge.cpp:68` | A central path config class; a new socket path without override |
| UIC-15 (C5-I8) | Small lists and file-search helpers are copied where needed; QML holds option lists, the bridge mirrors only what it parses | usually | `ACB:92-105`; `UI/src/GyroConfigBridge.cpp:198-211` | A shared utility library refactor across bridges |
| UIC-16 (C5-N1) | The GUI thread blocks on Core commands, bounded per command (connect 350 ms, default 3 s, reconfigure list 10 s, gyro 8 s, `record_stop` 60 s; media eject 60 s, format 360 s); only the status poll is async | always | `ACB:1015-1031`; `ACB:861-862` | Worker threads or futures for commands; an unbounded wait |
| UIC-17 (C5-N2) | Core owns camera truth; UI caches are placeholders overwritten by Core state | always | `ACB:886`; `ACB:1256-1258` | UI deciding a camera value without reconciling |
| UIC-18 (C5-N4, C7-N4) | Cold-boot time is a constraint: FFmpeg in a lazy module, a libproxy stub, `-z,lazy`, AOT QML, readiness files | always | `UI/CMakeLists.txt:132-147`; `:169-182` | Linking FFmpeg or another large stack into `ApertarUI` |
| UIC-19 (C5-I10) | Embedded Python run by `python3 -c` from a C++ raw string exists once (media watcher); a rough edge, not a pattern to extend | once | `UI/src/MediaStatusBridge.cpp:762-963` | Copying it for new work, or removing it unasked |

### 2.6 QML (QML)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| QML-1 (C6-S1) | Navigate only by setting `Main.currentPage` / `Main.settingsOpen` in Main, in response to a page's `*Requested` signal, a hardware action or standby; no StackView | always | `qml/Main.qml:16`; `:506-509` | A page setting `currentPage`; a `StackView` |
| QML-2 (C6-S2, C6-N7) | Non-camera pages are `Loader`s active only while shown; hidden UI does no work: section polling only while visible, Repeaters get `[]` otherwise, every repeating Timer has a `running:` condition | always | `qml/Main.qml:584-590`; `SP:2139-2151` | A page instantiated permanently; a free-running timer |
| QML-3 (C6-S3) | A settings item is one `Component { id: <section><Name>Component }` in `SP`, returned by `<section>ComponentForId(itemId)` and built by the section Repeater | usually (Presets hand-built) | `SP:2216-2229`; `SP:6684-6691` | A card placed directly in a Column; a QML file per card |
| QML-4 (C6-S4, C6-S16) | A new item id goes by hand into `default<Section>Order`, `sectionItemTitle`, `<section>ComponentForId` and, if favouritable, `favoriteCandidateOrder`. Ids and section names are persisted keys: never rename; a moved item keeps its old component id | always | `SP:771-783`; `SP:999-1036` | A generated item registry; renaming `battery` or `"Power"` |
| QML-5 (C6-S5) | A settings section is wired through every if-chain keyed by its display name (`defaultOrderForSection`, `storedOrderForSection`, `applySectionOrder`, `sidebarIconForId`, `sourceSectionForItemId`, `favoriteComponentForId`, `updateSectionActivity`, `onSelectedSectionChanged`, `sectionFlick.contentHeight`) | always | `SP:954-972`; `SP:6485-6501` | A section missing from one chain; the chains refactored into a table |
| QML-6 (C6-S6, C6-N10) | Each reorderable section's order is a `SettingsBridge` `QStringList` in UI.conf, included in presets; cards in reorderable sections carry reorder and favourite wiring | always (S6); usually (N10) | `UI/src/SettingsBridge.hpp:81-89`; `SB:2097-2105` | Order in QML `Settings {}`; a card without `pressAndHoldRequested` |
| QML-7 (C6-S7) | Monitoring aids and UI preferences are `SettingsBridge` properties written from QML by plain assignment `root.settingsState.<prop> = v`; no socket command | always | `SP:2704-2707`; `SB:597-607` | A monitoring aid sent to Core |
| QML-8 (C6-S8, C6-I20) | Core-owned camera settings change only through `ApertarControlBridge` invokables: `if (bridge && !bridge.apply<X>(v))` show `lastError` and stop, then mirror into `settingsState`. QML never builds commands or JSON | usually (`qml/ClipBrowserPage.qml:115-119`) | `SP:2980-2994`; `CPg:2938-2943` | QML composing JSON; UI state flipped before Core accepted |
| QML-9 (C6-S10, C6-S17) | Sensor-specific UI keys on `imxNNNDetected` substring flags declared in each page; per-sensor resolution tables are identical copies in `CPg` and `SP` and change together (surrounding names differ: `resolution` vs `recordResolution`) | always | `CPg:362-381`; `SP:78-114` | A table changed in one page; a shared JS module introduced unasked |
| QML-10 (C6-S11, C6-S18) | The HDMI window derives its HUD from bridges; only Main/camera-page state reaches it via named Main properties read by `ExternalMonitorRuntimeBridge`. `Main.qml` property names and `objectName`s are a C++ contract read by string | always | `qml/Main.qml:36-38`; `UI/src/ExternalMonitorRuntimeBridge.cpp:137-153` | HDMI QML reaching into `cameraPage`; renaming `previewItem` |
| QML-11 (C6-S12) | An element both screens show is a small standalone QML file used by both; otherwise HDMI draws its own HUD | usually | `qml/DroppedFrameWarning.qml`; `EMW:1103-1107` | A shared HUD framework |
| QML-12 (C6-S13, C6-I12) | Main bridges are passed into pages as properties (`settingsState`, `controlBridge`); others are bare context globals, `typeof`-guarded only when they can be absent; reads that can be absent use `x ? x.y : default` | usually | `qml/Main.qml:498-501`; `EMW:374-375` | An unguarded bridge on the HDMI path |
| QML-13 (C6-S14, C6-I1, C6-I2, C6-I3) | Sizes are inline nested ternaries over layout flags, largest layout first, square last; page tokens are `readonly property int` at the top of the page; copy the layout-flag block of the file you edit (flag meanings differ per file); no theme singleton | usually (I1, I2, S14); always (I3) | `qml/TogglePill.qml:20-21`; `SP:23-59` | `Theme.qml`, `dp()` helper; "unified" flag semantics |
| QML-14 (C6-S15, C7-S2) | A new QML file goes into both `APERTAR_QML_FILES` (`UI/CMakeLists.txt`) and `qml.qrc`; fonts and icons into `resources.qrc` | usually (`DroppedFrameWarning.qml` missing from `qml.qrc`) | `UI/CMakeLists.txt:19-52`; `UI/qml.qrc:3-33` | A file in one list only |
| QML-15 (C6-S20) | Presets is a hand-built special section; new sections are not modelled on it | once | `SP:6745-6933` | A new section copied from Presets |
| QML-16 (C6-I4) | Fills and borders are inline hex from the existing palette (card `#181818`, border `#1affffff`, secondary text `#66ffffff`, accent `#3fd0ff`, danger `#8d2020`); primary text `"white"` | usually | `qml/ActionTile.qml:30-39`; `qml/MonitoringRow.qml:109-112` | A colour constants file; off-palette colours |
| QML-17 (C6-I5, C6-I6) | Inter via a `FontLoader` per file (Bold titles, Medium labels, Regular body); `renderType: Text.NativeRendering` on every `Text` | usually | `qml/SystemSectionCard.qml:30-32`; `:166` | A new font; Text without NativeRendering |
| QML-18 (C6-I8, C6-I9, C6-I10) | Root `id: root`; other ids camelCase with a role suffix. Component signals are `<thing>Requested` or events; the owner writes state. Action functions verb-first, getters noun phrases, predicates `is/has/can` | always (root, signals); usually (names) | `qml/MonitoringRow.qml:93-102`; `SP:1064` | A component writing `settingsState` itself; `getX()`/`handleX()` |
| QML-19 (C6-I11) | `Connections { target: ...; function on<Signal>(args) {} }`; local mirrors re-check bridge and empty strings before copying | always (syntax) | `CPg:1824-1847`; `CPg:1555-1581` | Old `onFoo:` handlers in Connections |
| QML-20 (C6-I14, C6-I15) | No logging from QML. Comments: `// =====` chapter banners in `CPg` only, short why-lines, none in `SP`, no TODO | always (I14); usually (I15) | `CPg:1961-1963`; grep `console.` = 0 | `console.log` left in; ticket numbers in comments |
| QML-21 (C6-I16) | Match surrounding formatting in big files; never reformat untouched code | always | `CPg:1555`; `SP:5764-5765` | A whole-file reindent in a feature commit |
| QML-22 (C6-I17) | `Behavior on <prop>` + `NumberAnimation`, 120-240 ms: `OutCubic` enter, `InCubic` popup close, `Linear` hold progress; press scale 0.95-0.985 | usually | `qml/TogglePill.qml:30-56`; `qml/ActionTile.qml:167` | Springy easing, long animations |
| QML-23 (C6-I18, C6-I19) | Option lists are plain string arrays; `{value,label,enabled}` only with `InlineDropdownField`. UI-only values are stored as their display strings | usually | `qml/InlineDropdownField.qml:41-63`; `SP:4538` | Object options passed to `SettingsChoice` (`[object Object]`) |
| QML-24 (C6-N1, C6-N2, C6-N3) | Offer only choices Core and the hardware support; keep a currently unusable item visible but dimmed (`available:false`) with the reason in its description; grey a single value with a per-option `enabled` | usually (N1); always (N2); once (N3) | `SP:3198-3206`; `qml/MonitoringRow.qml:110` | Hiding the card; a clickable item with no effect |
| QML-25 (C6-N4) | Recording format, resolution, audio device, capture mode and power controls are disabled during a take; the top exposure stats stay live | usually | `SP:3230`; `CPg:539` | A format control usable during a take |
| QML-26 (C6-N5) | Data-loss and power actions are two-step (danger tone, confirmation popup); Format Media also needs hold-to-activate | always | `SP:5177-5184`; `SP:5428-5438` | One-tap delete, format or shutdown |
| QML-27 (C6-N6) | Capture and mode-change failures go to the camera page's modal warning (`showRecordWarning`); settings failures get their own `*ErrorOpen` popup | always | `CPg:1656-1662`; `CPg:1496-1499` | A toast or silent failure for a failed take |
| QML-28 (C6-N8, C6-N9) | HDMI shows aids only in Assist Feed (ANDed with `overlayFeedEnabled`), hides the HUD under SMPTE. Status words are fixed: NO MEDIA amber, REC/TIMELAPSE red, WRITING amber, READY green, on both screens | always | `EMW:374-387`; `qml/StatusChip.qml:44-48` | An aid on Clean Feed; a new status word on one screen |
| QML-29 (C6-N11) | Card titles Title Case 1-3 words; descriptions one short sentence-case fragment without period; HUD labels uppercase via `font.capitalization`; progress labels end in three ASCII dots | usually | `SP:4526-4528`; `SP:5571` | Long titles; hard-coded uppercase; Unicode ellipsis |
| QML-30 (C8-M3) | A fixed list needed by several QML files goes into a `.pragma library` JS file under `qml/`, imported `as <Name>`, listed in CMake | once | `qml/TimelapseIntervals.js:1-4`; `CPg:3` | A C++ singleton for a static list |

### 2.7 Platform and build (PLT)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| PLT-1 (C7-S1) | List every new translation unit by hand in the main target (Core `.cpp` only; UI `.cpp` and `.hpp`); never glob | usually (`UI/src/PreviewExposureReference.hpp` unlisted) | `Core/CMakeLists.txt:69-96`; `UI/CMakeLists.txt:63-130` | `file(GLOB ...)`; a new library target for app code |
| PLT-2 (C7-S4) | Optional deps are found QUIET; absence becomes `<PROJECT>_HAS_X=0`, usually with `message(STATUS)` naming the package, and the disabled path returns an operator error | usually | `Core/CMakeLists.txt:114-138`; `CC:3990-3995` | REQUIRED for an optional feature; `#ifdef` without a `_HAS_X=0` define |
| PLT-3 (C7-S6) | Core detects the platform with header-only inline functions: a pure `...FromCompatible(string)` plus a static-cached reader of `/sys/firmware/devicetree/base/compatible`, then `/proc/device-tree/compatible`. UI and helpers read `/proc/device-tree/model` | usually | `Caps:18-50`; `src/camera/DefaultTuningSelection.hpp:18-50` | A Core board check reading `model` or `/proc/cpuinfo` |
| PLT-4 (C7-S7, C7-I6) | Root work goes into a single-file, Qt-free helper `UI/src/<Name>.cpp`, target `apertar-<name>`, copied by hand to `/usr/local/libexec`, called by Core as `/usr/bin/timeout Ns /usr/bin/sudo -n <abs path> <literal verb>`, with a one-line `UI/systemd/apertar-<name>.sudoers` listing every verb. Shape: `Paths` struct, verb whitelist, `geteuid`, root-owned `/run/apertar-<name>`, `flock(LOCK_NB)`, `main` under `#ifndef APERTAR_*_TEST`. Core checks the helper exists | always (2 instances) | `App:1541-1550`; `UI/src/StandbyLowPower.cpp:13-17` | A root daemon; sudo with a wildcard; a helper taking a path |
| PLT-5 (C7-S8, C1-N13) | Simple privileged system tools are called directly with `sudo -n` (or `systemctl --no-ask-password`); a missing rule becomes "<Action> needs sudo permission."; an optional OS helper is probed with `std::filesystem::exists` and skipped | usually (`App:1537` passes raw shell output) | `App:3170`; `App:9152` | Interactive sudo, `pkexec`, raw stderr to the operator |
| PLT-6 (C7-S9) | System integration files live flat in `UI/systemd/`; Core holds only `config/` and `scripts/`. CMake `install()` covers binaries and modules only; units, sudoers, polkit, udev and helpers are installed by the image or by hand | always | `Core/CMakeLists.txt:190-196`; `UI/CMakeLists.txt:144` | An installer script; `install(FILES ... /etc/systemd)` |
| PLT-7 (C7-S15) | `pi` gets narrow rights via polkit actions and udev group permissions; services run `User=pi` | usually | `UI/systemd/49-apertar-network.rules:1-12`; `UI/systemd/apertar-network.service:7-8` | A root service to reach NetworkManager |
| PLT-8 (C1-S29) | A helper program or file template Core needs is a raw string literal in `App` (`R"PY(`, `R"CONFIG(`), run with `python3 -c` or written on demand; Core ships no helper script files | usually (standby helpers live in the UI repo) | `App:3382`; `App:4293` | A `scripts/helpers/` tree installed beside Core |
| PLT-9 (C7-S10, C7-I7) | Launch and deployment scripts are bash at the UI root or in `Core/scripts/`, configured by `${1:-default}` and `${APERTAR_X:-default}`; `set -euo pipefail` in launchers, `set -u` and unconditional `exit 0` in boot gates | usually (S10); always (I7) | `UI/run_pi_direct.sh:3-14`; `UI/wait_for_ui_core_start.sh:3,56` | A Python launcher; a gate that exits non-zero |
| PLT-10 (C7-S11) | The image layout is assumed: user `pi`; hardware config search env -> `/home/pi` -> `/boot/firmware` -> `/boot`; build dirs and tuning under `/home/pi`; settings under `$XDG_CONFIG_HOME` or `$HOME/.config` | usually | `CC:346-350`; `src/video/LibavH264EncoderClient.cpp:29` | A new config root `/etc/apertar` |
| PLT-11 (C7-S12) | Each process and hardware class carries its own copy of shared plumbing (config path list, templates, chip scorer, fan writer, power-error text, CFE watcher) | always | `src/hardware/TriggerOutput.cpp:201`; `App:3042` vs `UI/src/SystemActionBridge.cpp:64` | A shared library refactor of these copies |
| PLT-12 (C7-S13) | No test targets and no CI; test hooks only as `#ifndef APERTAR_*_TEST` around helper `main` | always | `UI/src/StandbyUsbPower.cpp:241`; `Core/.github/FUNDING.yml` | gtest/ctest targets, `.github/workflows` (new ground, see section 5) |
| PLT-13 (C7-S14) | UI builds in-tree to a tracked `build/` (551 files) and ships prebuilt `mesa-minimal/`, no `.gitignore`; Core builds in `../ApertarCore-build`. Do not commit rebuilt artifacts or delete the tracked ones unasked | once | `UI/README.md:249-260`; `Core/README.md:206-207` | A diff full of `build/` churn; deleting `build/` and adding `.gitignore` |
| PLT-14 (C7-I2) | Thread counts are derived from `hardware_concurrency()` and clamped (or fixed); no affinity, no RT scheduling, only bounded nice (camera thread -5 via `LimitNICE=-5`) | usually (ProRes fixed 4) | `CC:3323-3340`; `CC:6590-6599` | `SCHED_FIFO`, `pthread_setaffinity_np` |
| PLT-15 (C7-I4, C7-I9) | `-Wall -Wextra -Wpedantic` per target. Core is C++20 with extensions off; UI is C++17 | usually (warnings: not on `ApertarUI`); always (standards) | `Core/CMakeLists.txt:21-23`; `UI/CMakeLists.txt:4-5` | A target without warnings; C++20 in UI code |
| PLT-16 (C7-I5) | Each non-obvious build or script choice gets a 1-3 line why-comment above it | usually | `UI/CMakeLists.txt:132-133`; `UI/run_pi_direct.sh:41-44` | Unexplained linker flags |
| PLT-17 (C7-I8, C8-S13) | Vendored source goes under `third_party/<name>/` with LICENSE and `README.apertar.md` naming upstream, commit, licence, purpose and every local fix | once | `UI/third_party/liblj92/README.apertar.md:1-11` | Copied source in `src/` without provenance |
| PLT-18 (C7-I10) | Legacy `CinePi` settings names stay: `QSettings("CinePi","UI")`, `~/.config/CinePi/UI.conf` | always (5 sites) | `UI/src/SettingsBridge.cpp:287`; `App:344-347` | Renaming storage to `Apertar` (loses operator settings) |
| PLT-19 (C7-N1) | Three board classes are supported; a format the board cannot sustain is refused with a message naming the board class; saved settings are coerced at load | always | `Caps:64-106`; `CC:2709` | A Pi 5-only feature reachable on Pi 4 without refusal |
| PLT-20 (C7-N2) | On an unrecognised platform Core does not guess Pi behaviour; tuning is left to libcamera and reported "unknown" | usually | `src/camera/DefaultTuningSelection.hpp:53,66-69` | Defaulting to PiSP on unknown boards |
| PLT-21 (C7-N3) | Hardware is probed by identity, not index (DRM by type, H.264 by driver, gpiochip by label score, IMU by bus scan); I2C default buses stay overridable | usually | `src/video/H264Hardware.hpp:37`; `src/hardware/Pcf8574Input.hpp:31` | Hard-coded `/dev/video11`, `card1`, `gpiochip4` |
| PLT-22 (C7-N5, C7-N6) | Startup gates never block the camera or recovery (bounded timeouts, skip without screen, exit 0); headless operation is first-class | always | `UI/wait_for_ui_core_start.sh:7-10`; `UI/run_pi_direct.sh:168-186` | `ExecStartPre=` without `-`; a Core feature needing the touch UI |
| PLT-23 (C7-N7) | Root access stays narrow: helpers take literal verbs only; never a path from WebUI or config; WebUI values reach root only as `shellQuote`d arguments to fixed tools; user scripts run as `pi` without sudo | usually (timezone after empty check `App:3270-3290`) | `App:1543`; `README.md:177` | sudo with a WebUI path or unquoted value |
| PLT-24 (C7-N8) | Building installs nothing system-wide; the READMEs say so and warn against replacing a working camera stack | always | `Core/README.md:87`; `UI/README.md:295` | A build step that writes `/etc`, `/boot`, overlays or libcamera |
| PLT-25 (C7-N9) | Board-specific power features verify the exact expected topology and refuse, keeping the safe state, when anything differs | once | `UI/src/StandbyUsbPower.cpp:59-80` | Power-off without a topology check |
| PLT-26 (C7-N11, C7-N12) | Release when no build type; `-mtune=native` only for native Release builds. No version string in code; `project(VERSION 0.1.0)` is stale; the release commit is the identity | once | `Core/CMakeLists.txt:4`; `:183-188` | Forcing `-march`; adding a version scheme unasked |

### 2.8 Style and commits (STY)

| Id | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- |
| STY-1 (C8-S1, C1-I15) | 4 spaces; function-body brace on its own line; `if/for/while/switch (...) {` on the same line; one-statement bodies may be unbraced; `&`/`*` bind to the name; no formatter config. Two layout densities coexist; match the one around you | usually (`src/lossydng/` K&R; stray UI tabs) | `src/ipc/ControlServer.cpp:15-36`; `App:9242-9249` | `void f() {` in app code; reformatting untouched lines |
| STY-2 (C8-S2, C8-M4) | Private class members `name_` in Core, `m_name` in UI; never mix within a repo. Plain public structs use bare camelCase fields with in-class defaults | always (S2); usually (M4) | `CCH:107-133`; `UI/src/SettingsBridge.hpp:489-491` | `m_state` in a Core class; `state_` in a UI bridge |
| STY-3 (C8-S3, C1-I16) | Types PascalCase; functions camelCase verb-first; constants `kCamelCase`; `...Locked` for methods needing the held mutex; macros UPPER_CASE. Wire JSON, commands, `camera_settings.conf` keys snake_case; UI.conf and preset keys camelCase; env `APERTAR_<AREA>_<NAME>` | usually | `App:60-64`; `CCH:92,96` | `MAX_WIDTH`; camelCase in a reply; snake_case in UI.conf; `CINEMATE_*` env |
| STY-4 (C8-S4) | Core app code in `namespace apertar`, file helpers in an anonymous namespace inside it; plugin C ABIs, `main.cpp`, codec C outside. UI: no project namespace. `.hpp` uses `#pragma once`; C `.h` codec headers use guards | usually | `App:57-58,6779`; `src/lossydng/fastent.h:17` | A Core class outside `namespace apertar`; `#ifndef` in a new `.hpp` |
| STY-5 (C8-S5, C8-M5) | Includes: own header, project headers, blank, system headers. UI: own header, Qt group, std group, POSIX group | usually | `src/hardware/GpioInput.cpp:1-22`; `UI/src/Ina219Bridge.cpp:1-21` | System headers first; reorder-only churn |
| STY-6 (C8-S6, C1-I10, C2-I3) | Codecs and writers may throw `std::runtime_error`/`std::system_error`; component boundaries return `bool` plus nullable `std::string *error(Message)` or `setErrorLocked` + `lastError()`; parsers return `std::optional`; no exception crosses `handleCommand`. No `std::expected`, no error enums | usually | `src/hardware/GpioInput.cpp:534-535`; `App:3127` | `Result<T,E>`, `enum class GpioError`, exceptions for control flow |
| STY-7 (C8-S7, C1-I13, C2-I6, C7-I3) | Core logs `std::cerr << "ApertarCore <subject>: " ... << '\n'` (hardware: `"<Device> input: "`; standby: `"Apertar standby: "`), one line per event, `key=value` for stats; no `std::endl`, no levels, no library. App logs failures and ignored input only. UI uses `qInfo()/qWarning()` with `"Apertar <area>: "`, never `qDebug` | usually | `CC:3353`; `src/hardware/GpioInput.cpp:618` | `spdlog`, `std::endl`, a log line per command, `qDebug()` |
| STY-8 (C8-S8, C1-I14, C2-I19) | App comments are rare one- or two-line present-tense statements of a hazard or invariant ("never", "must", "only"); never narration of the next line; headers uncommented | usually (`UI/src/PreviewWindowRenderer.cpp:805-866` banners) | `src/ipc/ControlServer.cpp:25`; `App:8103-8104` | Paragraph comments, history narration, "Now we ..." |
| STY-9 (C8-S9) | No TODO/FIXME/XXX/HACK, commented-out code, `#if 0`, Doxygen, ticket numbers or other projects' commit hashes in source | always | grep both trees: 0 hits (only `mkstemp` `XXXXXX`, `src/util/SettingsFile.hpp:41`) | `// TODO(T33)`, `/** @brief */`, `// see cinemate abc1234` |
| STY-10 (C8-S10, C1-I07, C2-I5) | Operator-facing errors are one full sentence: capital, full stop, no "!", "please", "error", "failed"; say what is wrong or what to do. Missing argument: `"<command> requires <field>."`. Busy: `"Stop ... before ..."`. Deeper encoder text may be terse and is passed through | usually | `App:9097`; `App:9245` | `"ERR_FPS"`, `"error: invalid value"`, `"Failed"` |
| STY-11 (C8-S10) | UI text: settings titles and buttons Title Case; descriptions short sentence case, usually no period; status chips ALL CAPS; no `qsTr` | usually | `SP:2392-2394`; `qml/StatusChip.qml:48-49` | Lowercase titles; `qsTr("...")` |
| STY-12 (C8-S11) | Keep the rough edges (section 4): giant owner files, inline literals, duplicated helpers and lists, hand JSON, `CinePi` paths. Do not refactor unasked | always (no refactor precedent) | `CPg:271` vs `SP:1529`; `App:9216` | `Theme.qml`, splitting `App`, a JSON library |
| STY-13 (C8-M1) | Codec islands (`src/lossydng/`, `src/prores/`) keep their C-flavoured register (guards, `/* */` essays, snake_case, K&R). Do not normalise them; do not bring that register into app code | always | `src/lossydng/fastent.h:1-18`; `src/prores/ProresEncoder.cpp:77-83` | Reformatting `fastent.h`; essays in `CC` |
| STY-14 (C8-S12) | README is for the camera builder: Title Case headings (some questions), second person, honest limits, one short For Developers section; tables stop at CLI launch flags | usually | `README.md:60`; `README.md:248-257` | A table of every env knob or socket command |
| STY-15 (C8-S14) | Upstream history is linear on `main`, one author, plain subjects (GitHub web defaults or `1.6.0 Release`), no bodies, no trailers, no tags. Merged work: plain, self-contained, linear; no internal numbers, no `claude/*` merges. AI trailers are the owner's call | always (facts) | UI `8847105 Updated to version 1.6.0`; Core `35dbe67 1.6.0 Release` | Subjects with `T33`/`WP-585-9`; bodies citing reviews |
| STY-16 (C8-S15) | Shell: `#!/bin/bash`, `set -euo pipefail` (`set -u` for gates), UPPER_CASE vars from `${APERTAR_X:-...}`, `[[ ]]`, snake_case functions, errors to stderr then `exit 1` | usually | `UI/sync_pi_runtime.sh:3-14`; `Core/scripts/start-apertar-core.sh:1-11` | `#!/bin/sh`, `[ ]` tests, camelCase functions |

---

## 3. Recipes

Each step: file, then an anchor to `grep -nF`. Anchors were checked on the upstream worktrees. Do the steps in order.
Precedent for every camera recipe: exposure compensation (`grep -rnE 'exposureCompensation\b|exposure_compensation'`).

### R1. Add a socket command (CMD)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Name it (CMD-7). `set_` and `timelapse_` reset the idle timer | `App` | `const bool mediaAction` (gates just above and below) |
| 2 | One `if (command.name == "<name>") { ... }` block next to its family, before the unknown-command line. No new file, no CMake change | `App` | `Unknown command: ` |
| 3 | Read fields: `command.number("value")`, `command.string("enabled")` tested `== "true" \|\| == "1"`; missing field -> `"<name> requires <field>."` | `App` | `if (command.name == "set_exposure_compensation")` |
| 4 | Capture starter: add the name to the top gates. Media action: add it to `mediaAction` | `App` | `const bool mediaAction` |
| 5 | Work through the owner: `camera_.x()` + `camera_.lastError()`, `updateSharedUiGeneralSettings({...})`, or a free helper `bool f(..., std::string *errorMessage)` in the anonymous namespace | `App` | `updateSharedUiGeneralSettings(` |
| 6 | Reply `okReply(command.id, settingsBody(camera_.settings()))` or a snake_case fragment; refuse with `errorReply(command.id, "<Sentence>.")` | `App` | `std::string okReply(int id` |
| 7 | Add the name to the `help` literal | `App` | `\"commands\":[\"get_state\"` |
| 8 | Slow and not part of a take: worker thread + state group + status command (CMD-21) | `App`, `AppH` | `run_media_speed_test` |
| 9 | Touch UI, camera/capture command only: `Q_INVOKABLE bool apply<Thing>(const QString &)`; add to the 10 s reconfigure list if it restarts the camera. A UI.conf value is not sent from the touch UI (CMD-16) | `UI/src/ApertarControlBridge.{hpp,cpp}` | `bool ApertarControlBridge::sendCoreCommand` |
| 10 | WebUI: `sendCommand({ cmd: "<name>", value })` plus a `case` in the patch switch | `WCP` | `applyCommandSnapshotPatch` |
| 11 | Hardware action if buttons should reach it (R11 step 7) | `App` | `void ApertarCoreApp::handleHardwareInputAction` |

### R2. Add a persisted camera setting or per-frame control (CMD, CAM)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Member with default in `CaptureSettings`; an enum gets `enum class` + `toString` in the same header. A control the pipeline may lack gets a `...Available` runtime field (CAM-18) | `Types` | `struct CaptureSettings {` |
| 2 | Range rule (clamp or reset to `CaptureSettings{}`) | `CC` | `CaptureSettings clampCaptureSettings(` |
| 3 | Load: `else if (key == "snake_key")` | `CC` | `else if (key == "exposure_compensation")` |
| 4 | Save: `output << prefix << "snake_key=" << s.member << '\n';` | `CC` | `"exposure_compensation="` |
| 5 | Apply to libcamera, guarded by `controlInfoHas` / `intControlSupportsValue` | `CC` | `controlsForSettings` |
| 6 | Setter: declare in `CCH`; body = lock, validate with `setErrorLocked("<Sentence>.")`, copy, set, `return applySettingsLocked(next, <needs reconfigure>);`. Gate on `recording_` if it shapes stream or file (CAM-31) | `CC`, `CCH` | `bool CameraController::setExposureCompensation` |
| 7 | Scope: settings are per record-format profile; a value that must survive a format switch is carried over by hand (CAM-40) | `CC` | `settingsProfileFormat` |
| 8 | Three serialisers, one line each, next to the same neighbour | `CC`; `App`; `App` | `std::string settingsEvent`; `std::string settingsBody(const CaptureSettings &settings)`; `buildWebStateJson` |
| 9 | Command `set_<name>` (R1) | `App` | `if (command.name == "set_exposure_compensation")` |
| 10 | Presets: writer `addString("camera<Name>", ...)`, reader `command.string("camera<Name>")` with "Invalid preset <thing>.", the JS allow-list | `App`; `WCP` | `buildCurrentPresetPayload`; `apply_preset` |
| 11 | If it belongs in file metadata, read what the frame used from request metadata, not settings | `CC` | `metadataFromRequest` |
| 12 | Touch UI reads it in `applyCoreState` (R4); WebUI in `mergeCameraStateFields` and the patch `case` | `ACB`; `WCP` | `void ApertarControlBridge::applyCoreState`; `mergeCameraStateFields` |

### R3. Add a UI.conf toggle, end to end (monitoring aid or UI preference)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | `Q_PROPERTY(bool fooEnabled READ fooEnabled WRITE setFooEnabled NOTIFY fooEnabledChanged)`, getter, signal, `bool m_fooEnabled = false;` | `UI/src/SettingsBridge.hpp` | `zebraEnabled` |
| 2 | Constructor read `m_settings.value("fooEnabled", false)`; re-read in `pollExternalSettings`; setter copied from `setZebraEnabled` (guard, `sync()`, `updateSettingsFileState()`, emit); presets save and apply | `SB` | `void SettingsBridge::setZebraEnabled`; `void SettingsBridge::pollExternalSettings`; `serializeCurrentSettings`; `applySettingsObject` |
| 3 | QML: id into `default<Section>Order`, `sectionItemTitle`, `favoriteCandidateOrder` if favouritable | `SP` | `defaultMonitoringOrder`; `function sectionItemTitle`; `favoriteCandidateOrder` |
| 4 | QML: `Component { id: monitoringFooComponent; MonitoringRow {...} }` copied from the SMPTE card, `onToggleRequested` assigns `root.settingsState.fooEnabled`; add to `<section>ComponentForId` | `SP` | `monitoringSmpteComponent`; `function monitoringComponentForId` |
| 5 | Icon PNG into `qml/icons/` and `resources.qrc` | `UI/resources.qrc` | `icons/` |
| 6 | Consume it where it acts (`CameraPreviewItem` binding); on HDMI AND it with `root.overlayFeedEnabled` | `CPg`; `EMW` | `zebraEnabled`; `overlayFeedEnabled` |
| 7 | Core: member in `SharedUiSettingsSnapshot`; parse branch `else if (key == "fooEnabled")` with `parseUiSettingsBool` | `App` | `struct SharedUiSettingsSnapshot`; `parseUiSettingsBool(value, snapshot.zebraEnabled)` |
| 8 | Core: one line `if (const auto reply = handleUiToggle("set_foo_enabled", "fooEnabled")) return *reply;`; add to `help` | `App` | `handleUiToggle(` |
| 9 | Core: `"ui":{}` line `",\"foo_enabled\":"` | `App` | `smpte_enabled` |
| 10 | Core: preset writer `addBoolFromMap("fooEnabled", ...)` and reader `addBoolUpdate("fooEnabled")` | `App` | `addBoolFromMap(`; `addBoolUpdate(` |
| 11 | Core: hardware action via `toggleSharedUiBoolAction` (10 of 15 toggles have one) | `App` | `toggleSharedUiBoolAction` |
| 12 | WebUI: `section.select-block` with `<div class="pill-grid" id="settingsFooOptions">`; render with `buildOptionButtons(..., toggleOptions, ...)` sending `enabled: "true"/"false"`; patch `case "set_foo_enabled":`; favourite copy in `renderFavoriteControls` (WEB-10) | `WCP` | `settingsSmpteOptions`; `function renderSnapshot`; `applyCommandSnapshotPatch`; `function renderFavoriteControls` |
| - | Nothing else: no event, no App member, no cache, no take guard, no success toast | | CMD-13, CAM-39 |

### R4. Add a field to the state and show it in the touch UI

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Pick the place: camera setting or capability -> three serialisers (R2 step 8); capture status -> `get_state` and top of `/api/state`, same key, plus an event if it changes outside a command; UI.conf value -> `"ui":{}` only; telemetry -> `"system":{}` / `"device":{}` from a `read*Snapshot()` helper | `App`, `CC` | `std::string settingsBody(const CaptureSettings &settings)`; `buildWebStateJson` |
| 2 | The line: snake_case key, `(x ? "true" : "false")`, `escapeJson(...)` for free text, `toString(enum)`, a scalar | `App` | `escapeJson` |
| 3 | `Q_PROPERTY(QString fooBar READ fooBar NOTIFY fooBarChanged)`, getter, signal, `setFooBarValue`, member with display default | `UI/src/ApertarControlBridge.hpp` | `Q_PROPERTY(QString` |
| 4 | `formatFooBarValue()` (and `parseFooBarValue()` if QML sends it back); setter compare/assign/emit | `ACB` | `formatFpsValue` |
| 5 | `if (state.contains("foo_bar")) setFooBarValue(formatFooBarValue(...));` | `ACB` | `void ApertarControlBridge::applyCoreState` |
| 6 | Optional placeholder cache under `camera/fooBar` | `ACB` | `saveCurrentCameraSettings` |
| 7 | QML: bind to `controlBridge.fooBar`; the camera page keeps a mirror via `Connections` + `syncControlValuesFromBridge` | `CPg` | `function syncControlValuesFromBridge` |
| 8 | HDMI: a status element shown on both screens is a small standalone QML file in both QML lists (QML-11, QML-14); a new top-row stat is a 6th `topMonitorInfoItems` entry with new positions | `EMW` | `topMonitorInfoItems` |
| 9 | WebUI: `mergeCameraStateFields` and `renderSnapshot` | `WCP` | `mergeCameraStateFields` |

### R5. Add a sensor (CAM)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Enumerator; detection `if (lower.find("imxnnn") != std::string::npos)`; display name (becomes `"sensor"`) | `CC` | `enum class SensorFamily`; `detectSensorFamily`; `sensorFamilyName` |
| 2 | `isImxNNNResolution(const Resolution &)` as `resolutionMatches(...) \|\|`; add to both allow-lists | `CC` | `isImx585LowResolutionAlias`; `CaptureSettings clampCaptureSettings(` |
| 3 | Mode mapping `case`s | `CC` | `sensorModeForRequestedResolution`; `normalizedResolutionForSensor` |
| 4 | fps per mode, bit depths, H.264 capture size, 4K check (switches without `default`) | `CC` | `maximumSupportedFpsForResolution`; `supportedRawBitDepthForSensor`; `h264CaptureResolutionForSensor` |
| 5 | Quirks only where the driver needs them (software crop, fallback black level, lossless caps) | `CC` | `sanitizeSettingsForSensor` |
| 6 | Tuning file `<model>.json` in `/home/pi/Tuning-Files/defaults-pisp/` or `defaults-vc4/` (not in the repo) | `src/camera/DefaultTuningSelection.hpp` | `APERTAR_DEFAULT_TUNING_DIR` |
| 7 | App copies | `App` | `maximumPcfFpsForSettings`; `availablePcfResolutionOptions` |
| 8 | WebUI copies (fps tables, sizes, crop options, payload) | `WCP` | `imx477MaximumSupportedFps`; `sensorResolutionOptions` |
| 9 | Touch UI copies in both pages: `imxNNNDetected` flag, resolution table, fps limits | `CPg`; `SP` | `Detected:` |
| 10 | README sensor list | `Core/README.md` | `IMX585` |
| 11 | Check on the Pi: the configure line | `CC` | `ApertarCore camera configured: ` |

### R6. Add a resolution, crop or fps option

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | The driver must offer the mode; Core installs no driver | `Core/README.md` | `not installed` |
| 2 | Add the size to the sensor's predicate; add its fps cap | `CC` | `isImx585LowResolutionAlias`; `maximumSupportedFpsForResolution` |
| 3 | fps menu value: no Core change unless above a cap (`setFps` takes 0 < fps <= 280, lowers to the mode maximum) | `CC` | `bool CameraController::setFps` |
| 4 | Mirror caps and lists: App, WebUI, both QML pages (tables are identical copies, QML-9) | `App`; `WCP`; `CPg`, `SP` | `availablePcfResolutionOptions`; `const fpsPresets`; `availableFpsOptions` |
| 5 | Touch UI parses the new display string | `ACB` | `parseResolutionValue` |
| 6 | H.264 output sizes are a different list | `CC`; `Caps` | `kSupportedSizes` |

### R7. Add a record-format option (CAM)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | `enum class`, field with default, `toString` | `Types` | `struct CaptureSettings {` |
| 2 | Board-dependent: sentence, fallback, flag for the UIs | `Caps` | `recordingCapabilitiesFromCompatible` |
| 3 | Persist load and save (per profile automatically) | `CC` | `recordingFormatFromString` |
| 4 | Setter like `setProresProfile`: capability check, `recording_` gate with "... changes are blocked while recording.", `applySettingsLocked` | `CC` | `bool CameraController::setProresProfile` |
| 5 | Limits on fps, ISO, bit depth in the sanitise chain | `CC` | `sanitizeSettingsForSensor` |
| 6 | Use it at take start and print it in the start log line; folder prefix only if clips must be told apart | `CC` | `reserveClipFolder`; `ApertarCore recording clip: ` |
| 7 | A new mode or capture action adds the N17 refusals at its entry and in `startRecording`/`startTimelapse` (CAM-32) | `CC` | `Stop timelapse before recording.` |
| 8 | Three serialisers; command `set_...`; `help`; presets | `App`, `CC` | `setProresProfile`; `\"commands\":[\"get_state\"` |
| 9 | WebUI value mapper, sender, patch | `WCP` | `const recordFormatOptions`; `recordingFeatureSupported` |
| 10 | Touch UI `Q_PROPERTY` + `Q_INVOKABLE apply...` | `UI/src/ApertarControlBridge.hpp` | `Q_INVOKABLE bool apply` |
| - | A new top-level `RecordingFormat` also touches `recordingFormatFromString`, `isProcessedVideoFormat`, stream roles, writer start, `normalizeRecordingFormatValue`, `recordFormatOptions`, CMake sources or a `MODULE` plugin (CAM-15) | `CC`, `App`, `WCP` | `bool isProcessedVideoFormat` |

### R8. Add a bench knob or environment variable (CAM, PLT)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Name it `APERTAR_<AREA>_<KNOB>` | - | - |
| 2 | Read at the point of use (take start or configure) with bounds and default | `CC` | `unsignedEnvValue` |
| 3 | In an encoder `.cpp`: a read-once `static const` lambda | `src/cdng/CdngEncoder.cpp` | `APERTAR_CDNG_TILE_ROWS` |
| 4 | Print the effective value in the existing take-start or startup line, not a new log | `CC` | `ApertarCore recording clip: ` |
| 5 | UI: `qEnvironmentVariable`/`qgetenv` next to the literal it overrides | `UI/src/*.cpp` | `APERTAR_CONTROL_SOCKET` |
| 6 | Scripts: `NAME="${APERTAR_X:-default}"` at the top; when renaming keep the old name as inner fallback | `UI/run_pi_direct.sh` | `APERTAR_USE_NVME_RUNTIME` |
| - | Not in `camera_settings.conf`, `apertar-hardware.conf`, the socket API or README | | CAM-19, CAM-24 |

### R9. Add a WebUI pill list or settings card (WEB)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Core first: command (R1); busy refusals in Core with a remedy sentence | `App` | `const bool mediaAction` |
| 2 | Pill list: `const <x>Options = ["Label A", ...]` in the list block; mapper if wire values differ | `WCP` | `const fpsPresets` |
| 3 | HTML in the right panel: `section.select-block` + `pill-grid`, or `div.settings-card` > `settings-card-head` > `h3.settings-card-title` + one-sentence `p.settings-card-copy`, `settings-action-row` with `primary-/secondary-/danger-button` | `WCP` | `class="settings-card"` |
| 4 | Pills: `buildOptionButtons(id, options, currentLabel, async handler, columns)`; unusable options `enabled: false`; hide the block with `.hidden` when it does not apply | `WCP` | `function buildOptionButtons` |
| 5 | Button card: `async function request<X>()`; `window.confirm("...?")` only if destructive or system-level; success toast only in System/Power/Info cards | `WCP` | `requestFormatMedia` |
| 6 | Wire one listener line | `WCP` | `function installInteractions` |
| 7 | Render read-outs with `setText`, disable with `setElementDisabled(..., isRecording \|\| ...)` | `WCP` | `function renderSnapshot` |
| 8 | Patch `case "set_<x>":` | `WCP` | `applyCommandSnapshotPatch` |
| 9 | New panel: nav button with a `/icons/` PNG, `section.settings-panel[data-panel]`, `settingsPanelMeta` entry, loading hook in `setSettingsPanel`; keep the touch UI order | `WCP` | `const settingsPanelMeta`; `function setSettingsPanel` |

### R10. Add an HTTP route (WEB)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Ask first whether it is a command. Routes are for files, listings and the config text (WEB-4) | - | - |
| 2 | Work as a free helper in the anonymous namespace or a `build<X>Json() const` member declared in `AppH` | `App` | `std::string buildHardwareConfigFileJson()` |
| 3 | One branch before `/api/command`, own `WebServer::Response`, JSON content type, `okReply(-1, ...)`/`errorReply(-1, ...)`, status 400/404/500 | `App` | `WebServer::Response ApertarCoreApp::handleWebRequest` |
| 4 | Query params via `queryParameterValue`; for media and files repeat Core's busy refusal and reuse the path guards | `App` | `queryParameterValue`; `pathIsInsideRoot` |
| 5 | No auth, CORS or header work in the route (WEB-6) | `WS` | `allowedBrowserOrigin` |
| 6 | Page side: `async function fetch<X>(silent)` with a `state.<x>FetchInFlight` guard, `{ cache: "no-store" }`, `if (!payload.ok) throw new Error(payload.error \|\| "Could not ...")` | `WCP` | `async function fetchState` |

### R11. Add a hardware input device, action or config key (HW)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Header shaped like `Pcf8574Input.hpp`: callback ctor, `start/stop/enabled/configPath/lastError`, private `struct Config` with defaults, `static Config loadConfig()`. No app includes | `src/hardware/MyInput.hpp` | `class Pcf8574Input` |
| 2 | `.cpp`: copy the anonymous-namespace helpers, `normalizeSingleAction` (wrapped by `hardware::normalizeButtonMapping`), `loadConfig` with section aliases, poll/debounce loop, `setLastError`; start log `"MyDevice input enabled: ... config=..."` | `src/hardware/Pcf8574Input.cpp` | `normalizeSingleAction` |
| 3 | List the `.cpp` by name | `Core/CMakeLists.txt` | `src/hardware/Pcf8574Input.cpp` |
| 4 | Include and member by value | `AppH` | `Pcf8574Input` |
| 5 | Ctor lambda to `handleHardwareInputAction` (`, false` for rotation); `start()` and `stop()` calls | `App` | `handleHardwareInputAction(` |
| 6 | Config key: field in `Config`, `else if (key == "my_key" \|\| key == "alias")` with `parseConfigInteger`/`parseConfigBool` + `std::clamp`; a key shared with another process goes into that parser too | the owning class | `parseConfigInteger` |
| 7 | Action: branch before the unknown-action line, ending in `dispatch(...)` or `toggleSharedUiBoolAction`; guards stay in the command handler (HW-5). UI-only action: publish `hardware_action` and handle it in `qml/Main.qml`. Aliases in all three `normalizeSingleAction` copies | `App`; `src/hardware/{Gpio,Pcf8574,NeoRotary4}Input.cpp` | `Hardware input action ignored: unknown action` |
| 8 | Templates: commented section with `enabled=false` (and the new action name in the comment lists) in all three | `App`; `UI/src/DisplayConfigBridge.cpp`; `UI/src/Ina219Bridge.cpp` | `defaultHardwareConfigTemplate`; `ensureDefaultHardwareConfigFile` |
| 9 | README hardware paragraph if operator-facing; say a restart is needed | `Core/README.md` | `run_script` |

### R12. Add an output driven by camera state (HW)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Class pair shaped like `TriggerOutput` (worker thread + condvar, `"ApertarCore <device>: "` errors) | `src/hardware/TriggerOutput.{hpp,cpp}` | `ApertarCore trigger output: ` |
| 2 | Default-constructed member; `start()` with error print; `stop()` | `AppH`; `App` | `triggerOutput_` |
| 3 | Feed it only in `handleTriggerEvent` by matching an existing event string; seed state after `start()` | `App` | `handleTriggerEvent` |
| 4 | Templates with `enabled=false` and a wiring-safety comment | `App` + 2 UI templates | `optocoupler` |

### R13. Add a settings section, quick-menu slot or picker value (QML)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Section: `fooOrder` `QStringList` property, load, setter, preset save/apply | `UI/src/SettingsBridge.{hpp,cpp}` | `monitoringOrder` |
| 2 | `defaultFooOrder` and the name in `defaultSidebarOrder` | `SP` | `defaultSidebarOrder` |
| 3 | Extend every if-chain of QML-5; add `fooComponentForId`; copy the section `Column` from `monitoringColumn` (not from Presets) | `SP` | `function defaultOrderForSection`; `monitoringColumn` |
| 4 | Polling only in `updateSectionActivity` and `onSelectedSectionChanged` | `SP` | `function updateSectionActivity` |
| 5 | Top stat value: add the display string to the option list; the bridge must parse it; a mode limit goes into the mode gate | `CPg`; `ACB` | `isoOptions`; `losslessIsoLimitedMode` |
| 6 | Quick-menu slot: branches in `quickMenuSlotIconSource`, `quickMenuSlotActive`, `triggerQuickMenuSlot`, raise `quickMenuButtonCount` | `CPg` | `quickMenuButtonCount` |

### R14. Add a source file, optional dependency or root helper (PLT)

| # | Do | File | Anchor |
| --- | --- | --- | --- |
| 1 | Core source: `src/<area>/<Name>.{hpp,cpp}` in `namespace apertar`; list the `.cpp` by name next to its area. UI: list `.cpp` and `.hpp`; QML-facing class `<Thing>Bridge` | `Core/CMakeLists.txt`; `UI/CMakeLists.txt` | `add_executable(apertar-core`; `add_executable(ApertarUI` |
| 2 | QML file: `APERTAR_QML_FILES` and `qml.qrc` | `UI/CMakeLists.txt`; `UI/qml.qrc` | `APERTAR_QML_FILES` |
| 3 | Optional dep: QUIET inside the `if(PkgConfig_FOUND)` block; small -> link + `<PROJECT>_HAS_X=1/0` + `message(STATUS "... disabled: install <pkg>-dev")`; large or slow to load -> `MODULE` plugin with C ABI header and ABI symbol (CAM-15, CAM-16) | `Core/CMakeLists.txt` | `APERTARCORE_HAS_LIBAV` |
| 4 | Guard code `#if <PROJECT>_HAS_X`; the `#else` returns an operator error naming the dev package; add the package to the README `apt install` line | `CC`; `README.md` | `requires libavcodec/libavformat development libraries` |
| 5 | Root helper: one Qt-free file shaped like `StandbyLowPower.cpp`; target `Apertar<Name>` with `OUTPUT_NAME "apertar-<name>" AUTOMOC OFF AUTORCC OFF` and warnings | `UI/src/<Name>.cpp`; `UI/CMakeLists.txt` | `ApertarStandbyLowPower` |
| 6 | One-line sudoers listing every verb; Core calls it with a literal command after an `exists` check; restore state at Core start when its `/run` file exists; README says install is manual | `UI/systemd/apertar-<name>.sudoers`; `App` | `/usr/local/libexec/apertar-standby-low-power` |
| 7 | No test target, no CI file (PLT-12); no `UI/build/` churn (PLT-13) | | |

---

## 4. Rough edges that are part of the Apertar way

These are not bugs to tidy. A contribution that "fixes" one unasked changes code the original developer knows by
heart, enlarges the diff he must read, and breaks the "match what is there" contract that every rule above relies on.
That is a mismatch of its own kind (STY-12). Extend each in place: add your line to every copy, in the same shape.
If one is a real bug, raise it as its own small, labelled change, not as a side effect.

| Rough edge | Where | What a contributor does |
| --- | --- | --- |
| Giant owner files: `App` 11 025 lines (`handleCommand` 1 731), `CC` 8 834, `WCP` 11 618, `SP` 9 851, `CPg` 4 160; UI bridges 1 700-2 460 | `App:9091-10821` | Add code to the owner file, next to its family. Do not split |
| Camera state serialised three times by hand, already drifted (web copy lacks `photo_*`, order and number formats differ) | `App:167-216`, `CC:136-187`, `App:7857-7897` | Add the field to all three next to the same neighbour (CMD-10) |
| Option and sensor lists copied across CC, App, WCP, both QML pages; favourites list three times with different contents | `CC:355-532`, `App:1076-1260`, `WCP:4824-5028`, `CPg:377-490`; `App:727`, `WCP:4091`, `SP:838` | Edit every copy; no shared capability API |
| Per-class config parsers and 12-13 copies of the hardware-config candidate list; three `normalizeSingleAction` alias tables; three `gpioChipScore` | `src/hardware/GpioInput.cpp:60`, `:108`, `:238` and siblings | Copy the helpers into a new class; add aliases to all three tables |
| Three hand-kept hardware-config templates that drift (`[pcf8574] bus`, `open_drain`, dead `[imu]` keys) | `App:4291-4404`; `UI/src/DisplayConfigBridge.cpp:41-326`; `UI/src/Ina219Bridge.cpp:69-342` | Add new keys to all three; do not reconcile old drift unasked |
| Two parser families for the same file (hand C++ vs `QSettings`); comment stripping differs by class | `src/hardware/TriggerOutput.cpp:56-66` | Keep the class's own stripping |
| Two processes program the INA219 and write `[imu]` keys; no lock | `App:4602-4626`; `UI/src/Ina219Bridge.cpp:568` | Leave as is (HW-21) |
| `help` lacks 12 of 110 commands; the list is one 2 400-char line | `App:9216` | Append your command; do not reformat the line |
| "Could not update shared UI settings." typed 36 times; 13 near-identical UI.conf blocks, 8 IMU blocks unfactored; 51 `WebServer::Response response;` declarations | `App:9488`; `App:9729-9888`; `App:7093-7649` | Copy the block; no helper or macro |
| Booleans parsed by hand at 10 sites, two strict, eight lenient | `App:9131`, `App:9486` | Use the lenient form `== "true" \|\| == "1"` |
| Names kept from first use: `H264PreviewRecorder` and `h264Stream_` also serve ProRes; `isImx585LowResolutionAlias` maps IMX477/577; `Pcf` prefix covers every hardware input | `CC:7377`; `CC:450`; `App:1030-1322` | Keep the names |
| Two layout densities (spaced vs dense blocks), two hardware-class styles (older `lastError` classes vs newer dense, throwing files) | `App:9242-9476` vs `App:10031-10074`; `src/hardware/HardwareScriptRunner.cpp` | Match the surrounding block |
| Small bugs left in place: `discardedOnStopFrames_` never incremented; `uniqueCameraModelForSensor` ignores its arguments; lossy DNG write errors do not fail the take; requeue failures never reach the operator; `(void)updateSharedUiGeneralSettings(...)` at `App:9433` | `CC:3304`; `CC:3017-3022`; `LossyDngEncoder.cpp:228-232` | Fix only as a separate, named change |
| Dead or orphan files: `src/lossydng/LossyJpeg12.{h,cpp}`, `fastent.h` not built; `qml/InlineChoice.qml` in no list; README points to absent `src/prores/ffmpeg/` | `Core/CMakeLists.txt:69-96`; `Core/README.md:225` | Leave them |
| WebUI: `arrangeSettingsPanels` moves cards at run time; panel `power` titled "Media"; HTML panel order differs from nav order; `renderSnapshot` 880 lines; favourite toggles have duplicate handlers; WebUI shows no dropped-frame warning | `WCP:6119-6128`; `WCP:4186-4188`; `WCP:9327-10206` | Declare a card in its panel; add both handlers |
| QML: no theme; 136 hex literals in `SP`; 22 JS functions duplicated between `CPg` and `SP`; aspect-ratio list 21 times; layout flags mean different things per file; moved items keep old component prefixes (`battery` -> `powerBatteryComponent`); stray tab lines | `CPg:271` vs `SP:1529`; `SP:2336-2353` | Copy the file's own block; never rename ids |
| Process-wide `collectingCommandEvents_` flag set before the command lock (events of one socket request can land in another's reply, **probable**); slow work (format, gyro calibration, shell helpers) holds the command lock | `App:7061-7065`; `App:10843-10848` | Do not restructure the lock unasked |
| UI blocks the GUI thread on Core commands (bounded) | `ACB:1013-1106` | Use the timeout lists (UIC-16) |
| UI tracks its `build/` tree and prebuilt `mesa-minimal/`; no `.gitignore` | `UI/README.md:249-260` | No `build/` churn; do not delete |
| Legacy `CinePi` names for settings storage | `App:344-347`; `SB:287` | Never rename (PLT-18) |
| Stale `project(VERSION 0.1.0)`; `friend struct HardwareInputTestAccess;` without published tests | `Core/CMakeLists.txt:4`; `AppH:49` | Leave |
| Spelling: "colour" and "color" both in operator text | `App:9373`, `App:9746` | Follow the neighbouring string |

---

## 5. What original Apertar does not have

A contribution that brings one of these is **new ground**, not a mismatch. New ground must be argued and documented
for the original developer. "Sure" = how strongly the absence is established.

| Absent upstream | Sure | How searched |
| --- | --- | --- |
| Unit tests, test targets, CI (both repos). Only hooks: `#ifndef APERTAR_USB_POWER_TEST` / `APERTAR_LOW_POWER_TEST` around helper `main`; `friend struct HardwareInputTestAccess;` with no test | confirmed | `git ls-files` (Core 137 files, no test file); `grep -nE 'enable_testing\|add_test'` in both `CMakeLists.txt` = 0; `.github/` = `FUNDING.yml` only |
| `third_party/` or any provenance-declared vendored code in Core. (UI has `third_party/liblj92` with `README.apertar.md`; UI also ships prebuilt `mesa-minimal/` without licence file) | confirmed | `git ls-files`; `ls` of both roots |
| Root helpers inside the Core repo. Upstream root helpers exist only in the UI repo (2: `apertar-standby-usb`, `apertar-standby-low-power`) with sudoers files; Core calls them via `sudo -n` | confirmed | `git ls-files Core`; `grep -n libexec App` -> `App:1544`, `:1549` |
| Env knobs for tuning: **present**, not absent. 43 `APERTAR_*` knobs in Core, 16 in UI, none in README. A new knob in that form is not new ground | confirmed | `grep -rhoE 'APERTAR_[A-Z_]+' src` both repos |
| A JSON library in Core; `std::format` | confirmed | `grep -rnE 'nlohmann\|rapidjson\|json\.hpp\|jsoncpp\|simdjson\|boost/json'` = 0 |
| A logging library, log levels, `syslog`, debug switch; `qDebug` in UI; `console.log` in QML | confirmed | `grep -c 'std::clog\|syslog\|spdlog'` = 0; `qDebug` 0; `console.` 0 in `qml/` |
| Class hierarchies, `virtual`, interfaces, factories, DI on the camera side | confirmed | `grep -rnE '\bvirtual\b\|\boverride\b'` (2 word hits in a string and a comment) |
| `std::async`, `std::jthread`, futures, promises; RT scheduling, CPU affinity | confirmed | `grep -rnE 'std::async\|std::jthread\|std::future\|packaged_task\|std::promise'` = 0; `grep -rn 'sched_setaffinity\|SCHED_FIFO\|SCHED_RR\|nproc'` = 0 |
| A shared INI parser; a hardware-config file watcher or reload command | confirmed | `grep -n 'inotify\|last_write_time' src/hardware/*.cpp` = 0; inputs touched only in `start()`/`stop()` |
| Push channel to the WebUI (WebSocket, SSE) | confirmed | `grep -nE 'EventSource\|WebSocket\|text/event-stream\|Upgrade' src/web/*.cpp` = 0 |
| Authentication, TLS, CORS headers, tokens | confirmed | `WS` read; `grep 'Origin\|Access-Control\|auth\|token' App` |
| Browser storage, JS framework, modules, classes, build step for the page | confirmed | grep over `WCP:4038-11611` |
| A protocol or Core version in state or replies; a version string in code | confirmed | `grep version` -> only preset `"version":1` (`App:6530`); `grep -rn '1\.6' src qml` = 0 |
| Hardware-input health in state JSON or UIs (IMU only) | confirmed | `grep -n 'Input_\.lastError' App` = 0 |
| Free-space or mounted-drive check before a take | confirmed | `grep -nE 'statvfs\|filesystem::space\|is_mount\|/proc/mounts' CC` = 0 |
| Frame counts or queue depth in the socket API (only the dropped-frame boolean leaves Core) | confirmed | read of the state serialisers |
| Vendor `controls::rpi::` or driver-specific libcamera controls | confirmed | the 43 control names used in `CC` are all mainline |
| A data-driven sensor description table or mode probe | confirmed | sensor knowledge is `switch` code (CAM-11) |
| A config file or section for recorder tuning | confirmed | `grep` over topic dirs for `apertar-hardware` = 0 |
| libgpiod, libi2c, wiringPi, pigpio, sysfs GPIO | confirmed | `grep -rln 'gpiod\|wiringPi\|pigpio'` both repos = 0 |
| Formatter config, `.editorconfig`, `.gitignore`, CONTRIBUTING, CHANGELOG, `docs/`, API reference | confirmed | `ls -a` of both roots |
| TODO/FIXME/XXX/HACK, `#if 0`, commented-out code, Doxygen, per-file licence or SPDX headers, ticket numbers | confirmed | `grep -rnE '\b(TODO\|FIXME\|XXX\|HACK)\b'`; `///\|/\*\*\|@brief`; `Copyright\|SPDX` = 0 |
| Theme singleton, `qsTr`, StackView/SwipeView/Drawer in QML | confirmed | `grep 'pragma Singleton'` = 0; `qsTr` 0; `StackView` 0 |
| An installer: nothing installs units, sudoers, polkit, udev or helpers; building installs nothing system-wide | confirmed | `git ls-files`; `install(` rules read; `Core/README.md:87` |
| Sensor driver, overlay or libcamera installation | confirmed | `Core/README.md:87` |
| Helper script files beside Core (only `scripts/start-apertar-core.sh`) | confirmed | `git ls-files scripts` |
| Commit-message convention, feature-level commits, branches, merges, tags | confirmed | `git log upstream-1.6.0` both repos: 1 + 10 commits, no bodies, no merges |
| Feature history of how a rule came to be (Core is one squashed commit) | confirmed | `git log` = `35dbe67` only. Which of two coexisting styles is newer is **probable** only |
| Mesa `dri/` directory that `LIBGL_DRIVERS_PATH` points to | confirmed | `ls UI/mesa-minimal/lib/aarch64-linux-gnu` |

---

## 6. Board support

Upstream tells boards apart in Core by the device-tree **SoC compatible string** (`Caps:18-50`, cached in a static),
publishes the result as `recording_capabilities`, and enforces it at setter, sanitise and record start (CAM-13).
The UI and a few helpers read the **model string** instead, only for non-recording behaviour (PLT-3).
README claims: `Core/README.md:60-72`, `UI/README.md:57-67`.

| Model | SoC in code | README claim | Recording capabilities (code) | Tuning pipeline | Other model-specific code |
| --- | --- | --- | --- | --- | --- |
| Pi 5 | `brcm,bcm2712` | Pi 5 / CM5-class: cDNG uncompressed, lossless, lossy 3:1 / 5:1, MLV, H.264 (software), ProRes | `rawCompression=true`, `prores=true`, `rawRecording=true`, software H.264 via libav plugin (`Caps:25-26`) | PiSP, `defaults-pisp`, target `pisp` (`DefaultTuningSelection.hpp:56-75`) | GPIO chip `rp1` scores +100 (`src/hardware/GpioInput.cpp:247-253`); USB power-off helper accepts only model "Raspberry Pi 5 Model" and the exact 4-hub topology (`UI/src/StandbyUsbPower.cpp:59-80`); NVMe reset default `1000110000.pcie`, overridable (`App:3395`); fan mode shown; 6 H.264 camera buffers (`CC:1125-1129`) |
| CM5 | `brcm,bcm2712` | as Pi 5 | as Pi 5 | as Pi 5 | as Pi 5, except the USB power-off helper refuses (model is "Raspberry Pi Compute Module 5", **probable**; settle with `cat /proc/device-tree/model`) |
| Pi 500 | `brcm,bcm2712` (**probable**) | not named; "Pi 5-class" | as Pi 5 (**probable**) | as Pi 5 | USB power-off refuses (model string, **probable**) |
| Pi 4 B | `brcm,bcm2711` | Pi 4 / Pi 400 / CM4-class: uncompressed cDNG, MLV, H.264 hardware, max 1080p30 | `usb3=true`, `legacy=true` -> `rawRecording=true`, `rawCompression=false`, `prores=false`, `hardwareH264=true` (`Caps:27-34`, cap `Caps:102-103`) | VC4, `defaults-vc4`, target `bcm2835` | H.264 through `bcm2835-codec` V4L2 M2M, encoder must be `h264_v4l2m2m` (`CC:3969-3989`); 4 H.264 camera buffers; VC4 memory guard in YUV mode search (`CC:6001-6004`); fan mode hidden (model contains "raspberry pi 4", `SP:97`, `WCP:4821`); GPIO chip `pinctrl_bcm2711` +90 |
| Pi 400 | `brcm,bcm2711` | as Pi 4 | as Pi 4 | VC4 | as Pi 4; fan mode hidden because "Raspberry Pi 400" contains "raspberry pi 4" (**probable**) |
| CM4 | `brcm,bcm2711` | as Pi 4 | as Pi 4 | VC4 | as Pi 4, but fan mode shown (model "Compute Module 4" does not match the Pi 4 test, **probable**) |
| Pi 3 B / 3 B+ / 3 A+ | `brcm,bcm2837` | Pi 3 / 3A+ / Zero 2 W, "USB 2.0-only": H.264 only; RAW clips and ProRes disabled; stills separate | `legacy`, no `usb3` -> `rawRecording=false`, hardware H.264 (`Caps:29-34`) | VC4 | Touch UI preview uses the planar YUV path when the model contains "raspberry pi 3" (`UI/src/PreviewWindowRenderer.cpp:33-41`); GPIO chip `pinctrl_bcm2835` +90 |
| Zero 2 W | `brcm,bcm2837` | as Pi 3 | as Pi 3 | VC4 | Preview planar path not taken: model "Raspberry Pi Zero 2 W" lacks "raspberry pi 3" (**probable**) |
| CM3 | `brcm,bcm2837` | not named | as Pi 3 (**probable**) | VC4 | Same model-string caveat as Zero 2 W (**probable**) |
| Pi 2 / Pi 1 / Zero | `brcm,bcm2836` / `brcm,bcm2835` | not named; "other supported USB 2.0-only boards" | legacy, no `usb3` -> H.264 only (`Caps:29-34`) | VC4 | none |
| Unknown (no DT match) | - | not claimed | default `RecordingCapabilities{}`: RAW allowed, no compression, no ProRes, software H.264 (`Caps:11-16`, `:47`) | `Unknown`: no guess, libcamera decides (`DefaultTuningSelection.hpp:67`) | - |

Platform assumptions common to all boards: aarch64 only (`UI/mesa-minimal/lib/aarch64-linux-gnu`); worker counts from
`hardware_concurrency()`, clamped, no core count hard-coded (`CC:3323-3340`, `CC:4448-4451`); CPU temperature from
`thermal_zone0`; NVMe by `/dev/nvme` prefix; CFexpress hat on I2C bus 10 / 0x34 and INA219 on bus 4 / 0x40, both
overridable in `apertar-hardware.conf`; other I2C devices default to bus 1; HDMI audio filtered by `vc4`/`vc4-hdmi`
names (`UI/src/AudioDeviceBridge.cpp:103`); displays chosen by DRM connector type, 720x720 square layout default.
Sensors claimed: IMX477, IMX577, IMX585, IMX294 (`Core/README.md:76-83`); drivers and tuning files are not installed
by the build.

---

## 7. Style card

One line per item, each with a real upstream example. All refs `@upstream-1.6.0`.

| Item | Rule | Example |
| --- | --- | --- |
| Indent, braces | 4 spaces; function brace on own line; `if (...) {` same line; one-statement body unbraced | `src/ipc/ControlServer.cpp:15-36` |
| Core class | `class X {` on one line; members `name_` | `class CameraController {` (`CCH:17`); `mutex_`, `lastError_` (`CCH:107,119`) |
| UI class | `class X : public QObject` then `{`; members `m_name` | `SettingsBridge.hpp:13-14`; `m_presetStatusText` (`:489`) |
| Names | Types PascalCase; functions camelCase verb-first; `kCamelCase` constants; `...Locked` | `kWebPreviewMaxWidth` (`App:60`); `applySettingsLocked` (`CCH:92`) |
| Wire and file keys | snake_case on the wire and in `camera_settings.conf`; camelCase in UI.conf | `"set_iso"`; `exposure_compensation=` (`CC:752`); `zebraEnabled` (`SB:603`) |
| Env knobs | `APERTAR_<AREA>_<KNOB>` | `APERTAR_CDNG_QUEUE_FRAMES` (`CC:3330`) |
| Namespaces | Core in `namespace apertar`, helpers in `namespace {` | `App:57-58` ... `App:6779` |
| Headers | `#pragma once`; own header, project, blank, system | `src/hardware/GpioInput.cpp:1-22` |
| Errors in code | `bool f(..., std::string *errorMessage)`; `setErrorLocked(...)` + `lastError()` | `src/hardware/GpioInput.cpp:534-535`; `CC:8773` |
| Error strings | One sentence, capital, full stop, says what to do | `"Stop recording before deleting media."`; `"set_iso requires value."` (`App:9245`); `"Changing the fan mode needs sudo permission."` (`App:3170`) |
| Core log line | `std::cerr << "ApertarCore <subject>: " ... << '\n';`, `key=value` | `"ApertarCore camera configured: sensor= stream="` (`CC:6264`) |
| Hardware log line | `"<Device> input: "` / `"<Device> input enabled: ... config="` | `src/hardware/GpioInput.cpp:337`, `:618` |
| UI log line | `qInfo().noquote() << QStringLiteral("Apertar UI startup: ... in %1 ms")` | `UI/src/main.cpp:265-268` |
| Comments | Rare, one or two lines, why or never/must | `// Never let a stalled preview client block camera event delivery.` (`src/ipc/ControlServer.cpp:25`); `// Fixed executable and arguments only; never accept paths from WebUI/config.` (`App:1543`) |
| No markers | No TODO, Doxygen, `#if 0`, ticket numbers, project hashes | 0 hits in both trees |
| JSON | Hand-written, `okReply`/`errorReply`, `(x ? "true" : "false")` | `App:108-128`; `App:178-179` |
| Events | `{"event":"<name>",...}`, `event` first | `CC:139` |
| QML file | PascalCase, `id: root`, properties first, inline hex, `Text.NativeRendering` | `qml/StatusChip.qml:3-4`; `qml/SystemSectionCard.qml:166` |
| QML UI text | Title Case title; short sentence-case description without period; ALL CAPS chips | `"Focus Peaking"` / `"Highlight in-focus edges"` (`SP:2657-2659`); `"REC"`, `"READY"` (`qml/StatusChip.qml:48`) |
| Empty-state help | Full sentences, concrete path, ends with the action | `"No .cube LUTs found yet.\nAdd files to /home/pi/LUTs or media /LUTs, then tap Refresh."` (`SP:2528`) |
| WebUI text | One-sentence card copy with period; confirm as a question | `WCP:3606`; `window.confirm` (`WCP:11266`) |
| WebUI JS | Flat `async` function, try/catch, toast Core's text | `showToast(error.message, true)` (`WCP:11088-11098`) |
| Shell | `#!/bin/bash`, `set -euo pipefail`, `${APERTAR_X:-...}`, `[[ ]]`, errors to stderr | `UI/sync_pi_runtime.sh:3-14`; `printf 'Apertar <component>: ...: %s\n' "$X" >&2; exit 1` |
| README | Title Case headings, some questions; second person; honest limits | `## Which Raspberry Pi Can I Use?` (`Core/README.md:60`); "A selectable frame rate is not a promise ..." (`:20`) |
| Commit subject | Plain, self-contained, no internal numbers, no trailers; upstream itself only has release drops | `35dbe67 1.6.0 Release`; `8847105 Updated to version 1.6.0` |

---

## Index

| Section | Contents |
| --- | --- |
| 1 | Intent in ten lines |
| 2.1 | CMD-1 to CMD-30: command plane |
| 2.2 | CAM-1 to CAM-41: camera and recorders |
| 2.3 | WEB-1 to WEB-24: WebUI |
| 2.4 | HW-1 to HW-23: hardware and config |
| 2.5 | UIC-1 to UIC-19: UI C++ |
| 2.6 | QML-1 to QML-30: QML |
| 2.7 | PLT-1 to PLT-26: platform and build |
| 2.8 | STY-1 to STY-16: style and commits |
| 3 | Recipes R1-R14 |
| 4 | Rough edges |
| 5 | What upstream does not have |
| 6 | Board support |
| 7 | Style card |
