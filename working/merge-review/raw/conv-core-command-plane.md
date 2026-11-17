# Conventions study C1: Core's command plane and state

How the original developer builds the command plane of `apertar-core`. Read from Apertar-Studio 1.6.0 only.
This page is the yardstick for the cinemate port and the rule book for later work. It describes. It does not judge.

| Item | Value |
| --- | --- |
| Refs | Core `/home/user/wt/core-upstream`, tag `upstream-1.6.0` `35dbe67`. UI `/home/user/wt/ui-upstream`, tag `upstream-1.6.0` `43888e5` |
| Read | `src/ApertarCoreApp.cpp` (11 025 lines, in ranges), `src/ApertarCoreApp.hpp`, `src/ipc/ControlProtocol.{hpp,cpp}`, `src/ipc/ControlServer.{hpp,cpp}`, `src/main.cpp`, `include/apertar/core/*.hpp`, `src/web/WebServer.{hpp,cpp}`, `src/util/SettingsFile.hpp`, `src/camera/ExposureMetering.hpp`, `src/camera/CameraController.{hpp,cpp}` (persistence, setters, commit path only), `README.md`, `CMakeLists.txt` |
| Not read | The port, the fork. `WebControlPage.cpp` only at the functions named here |
| Status | Every claim is **confirmed** (read at the cited line) unless marked **probable** or **unconfirmed** |
| Short names | `App` = `src/ApertarCoreApp.cpp`, `AppH` = `src/ApertarCoreApp.hpp`, `CC` = `src/camera/CameraController.cpp`, `CCH` = `src/camera/CameraController.hpp`, `CP` = `src/ipc/ControlProtocol.cpp`, `CS` = `src/ipc/ControlServer.cpp`, `WS` = `src/web/WebServer.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `Types` = `include/apertar/core/Types.hpp`, `SF` = `src/util/SettingsFile.hpp`, `CB` = `Apertar-UI/src/ApertarControlBridge.cpp` |
| Line numbers | All `@upstream-1.6.0`. Every number came from `grep -n` or a read of that worktree on 2026-11-17 |
| Strength words | **always** = no counter-example found, the search is named. **usually** = exceptions named. **once** = one precedent |
| Rule ids | `C1-Sxx` structure, `C1-Ixx` idiom, `C1-Nxx` intent, `C1-Rx` recipe |

---

## 1. The shape in one table

| Surface | Thread | Path into Core | Line |
| --- | --- | --- | --- |
| Touch UI, HDMI process, `socat` | one detached thread per socket client, at most 32 (`CS:208`, `CS:215-227`) | `ControlServer::clientLoop` -> `handleRequest` -> `handleCommand` | `CS:252`, `App:7055`, `App:7067` |
| WebUI | one detached thread per HTTP connection, at most 32 (`WS:271`, `WS:276-287`) | `WebServer::clientLoop` -> `handleWebRequest` -> `POST /api/command` -> `handleWebCommand` -> `handleCommand` | `WS:380`, `App:7637-7640`, `App:7085-7090` |
| Buttons, encoders, analog knobs, power key | each input class's own thread | `handleHardwareInputAction` -> `handleSingleHardwareInputAction` -> `dispatchHardwareInputCommand` -> `handleCommand` | `App:8630`, `App:8660`, `App:8458-8462` |
| Idle timer | main thread, 1 Hz | `wait()` builds `enter_standby` with `idle_timeout` -> `handleCommand` | `App:7045-7049` |

Numbers that define the shape:

| Fact | Value | How counted |
| --- | --- | --- |
| `handleCommand` | `App:9091-10821`, 1731 lines | read |
| Commands | 110 = 95 `if (command.name == "...")` blocks + 15 `handleUiToggle(...)` lines | `awk 'NR>=9118 && NR<=10821' App \| grep -oE '^    if \(command\.name == "[a-z_0-9]+"'` plus `grep -oE 'handleUiToggle\("[a-z_]+"'`, `sort -u \| wc -l` = 110 |
| `else if (command.name`, `switch` in the dispatcher | 0, 0 | `grep -nE 'else if \(command\.name'`; `awk` range + `grep switch` |
| Lock sites of `commandMutex_` | 2 (`App:9093`, `App:7032`) | `grep -n commandMutex_` |
| Camera mutations (`camera_.set*`, `apply*`, record, photo, timelapse, standby) | 49 call sites inside `handleCommand`; outside only lifecycle `App:6838`, `:6849`, `:6856`, `:6862`, `:6874`, `:6923` | `grep -nE 'camera_\.(set[A-Z]\|apply\|startRecording\|...)'` split by line range |
| `updateSharedUiGeneralSettings(` call sites | 44, all inside `handleCommand` | `grep -n`, split by line range |
| `readSharedUiSettings()` call sites | 23 | `grep -c` minus the definition |
| HTTP route branches | 18 | `grep -cE '^    if \(request\.method =='` in `App:7093-7649` |
| Event names | 15 | `grep -rnoE 'event\\":\\"[a-z_]+' src` |
| Files with `command.name ==`, `okReply(`, `errorReply(`, `handleCommand`, UI.conf access | `src/ApertarCoreApp.cpp` only | `grep -rlE` over `src include` |
| Files with `camera_settings.conf` | `src/camera/CameraController.cpp` only | `grep -rl` |

---

## 2. Rules: STRUCTURE (where things go, who owns what)

| Id | Rule | Strength | Evidence | Exceptions and notes | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C1-S01 | Once Core runs, every change of camera state or of `UI.conf` enters through `ApertarCoreApp::handleCommand`. Socket, HTTP, hardware inputs and the idle timer all call it | always (49 + 44 call sites checked, see table above) | `App:7067` `std::string reply = handleCommand(parsed.command);`; `App:7090` `return handleCommand(parsed.command);`; `App:8462` `const std::string reply = handleCommand(command);`; `App:7049` `handleCommand(command);`; README:271 "Native UI commands, WebUI requests and hardware actions reach the same controller and busy-state checks." | None after start. `start()` itself applies the still-mode values from UI.conf once (`App:6845-6857`) | An HTTP route, a hardware callback or a worker thread that calls `camera_.setX()` or writes UI.conf itself |
| C1-S02 | The dispatcher is one flat chain of `if (command.name == "...") { ... return ...; }` blocks. Each block returns. The last line is the unknown-command error | always | `App:9242` `if (command.name == "set_iso") {`; `App:10815` `if (command.name == "shutdown") {`; `App:10820` `return errorReply(command.id, "Unknown command: " + command.name);` | None. The 15 toggles are one line each in the same chain, through the `handleUiToggle` lambda (`App:9493-9512`) | A `std::map<std::string, Handler>`, a `switch` on a hash, a handler class per command, a second dispatcher function |
| C1-S03 | One lock serialises all commands: `commandMutex_`, taken on the first line of `handleCommand`. No finer lock exists for commands | always (2 lock sites in the file) | `App:9093` `std::lock_guard<std::mutex> commandLock(commandMutex_);`; `App:7032` `std::lock_guard commandLock(commandMutex_);` (1 Hz supervisor) | none | A per-feature command mutex, or a command body that runs before the lock |
| C1-S04 | Guards that cover several commands sit at the top of `handleCommand` as `\|\|` lists of command names, each with its own operator sentence. A guard for one command opens that command's block | usually | Top: `App:9095-9097` (pending writes), `App:9098-9107` (media actions), `App:9108-9110` (speed test), `App:9111-9117` (idle reset), `App:9208-9211` (Standby). In-block: `App:9706`, `App:9541`, `App:10032`, `App:10053`, `App:10077` | Camera-side guards live in the `CameraController` setter (`CC:7714-7717`, `CC:7976-7979`) | A new capture command that is not added to the three capture gates; a guard helper called from many blocks |
| C1-S05 | The whole command plane is one file pair: `src/ApertarCoreApp.{cpp,hpp}`. `src/ipc/` holds only the line parser and the socket server | always (`grep -rl` above) | `CMakeLists.txt:69-96` (flat source list, one App file); `src/ipc/` has 4 files: `ControlProtocol.{hpp,cpp}`, `ControlServer.{hpp,cpp}` | none | `src/commands/`, a command file per feature, command code inside `ControlServer` |
| C1-S06 | Helpers are free functions in the anonymous namespace above the members (`App:58-6779`, about 282 functions). A function becomes a member only when it needs `this` (39 members) | usually | `App:57-58` `namespace apertar {` / `namespace {`; `App:6779` `} // namespace`; `AppH:74-108` (private members) | 3 free functions sit between members with external linkage: `App:8410`, `:8434`, `:8442` | Private static member helpers, a new `*Utils` class, a helper header for one caller |
| C1-S07 | Each store has one owner. `camera_settings.conf`: `CameraController` only. `UI.conf` (Core side): `ApertarCoreApp` only. A single key of `apertar-hardware.conf`: the hardware class that parses that section | always (`grep -rl` above) | `CC:342-353` `persistedSettingsPath()`; `App:341-348` `sharedUiSettingsPath()`; `App:9652` `Mpu6050RecordingSession::setConfiguredDriver(*value, &errorMessage)`; `App:9662` `...setConfiguredOrientation(...)` | None for single keys. The WebUI editor saves the whole file as text: `App:7175-7178` -> `saveHardwareConfigFile` `App:5323` | `CameraController` reading `UI.conf`; App writing `camera_settings.conf`; App editing one hardware key by itself |
| C1-S08 | App keeps no copy of settings. Camera settings come from `camera_.settings()` each time. UI.conf is parsed again on every use | always (no `CaptureSettings` or `SharedUiSettingsSnapshot` member in `AppH:110-176`; 23 read sites) | `App:7715` `const CaptureSettings settings = camera_.settings();`; `App:7728` `const SharedUiSettingsSnapshot uiSettings = readSharedUiSettings();`; `App:7037` (read every second in `wait()`) | None. Probe results, not settings, are cached inside their own function (C1-I19) | A `uiSettings_` member, a settings cache with invalidation, a file watcher in Core |
| C1-S09 | The WebUI changes state only through `POST /api/command` with the same JSON command as the socket. Other routes exist for the page, icons, the MJPEG stream, the state JSON and file work (media, presets, hardware config) | always (18 branches read) | `App:7637-7641` `if (request.method == "POST" && request.path == "/api/command") {` ... `response.body = handleWebCommand(request.body);`; `WCP:9123` `fetch("/api/command", {` | none | `POST /api/iso`, `GET /api/record/start`, a route that calls `camera_.setX` |
| C1-S10 | The HTTP router is one function, `handleWebRequest`, with a flat chain `if (request.method == "<M>" && request.path == "<p>")`. Prefix routes use `request.path.rfind("<prefix>", 0) == 0`. `/api/command` is the last branch. Unmatched: 404 for GET/POST, else 405. Methods: GET, POST, OPTIONS only | always | `App:7154` `if (request.method == "GET" && request.path == "/api/state") {`; `App:7124` `request.path.rfind("/icons/", 0) == 0`; `App:7644-7647` (404/405) | none | A route table, a router class, `PUT`/`DELETE` verbs, routes registered from other files |
| C1-S11 | A hardware input never touches the camera. It builds a `ControlCommand` and sends it through `dispatchHardwareInputCommand`. A UI-only action is a `hardware_action` event | always (`App:8660-8955` read) | `App:8505` `dispatch("set_iso", { { "value", std::to_string(iso) } });`; `App:8858` `dispatch("record_start");`; `App:8909` `toggleSharedUiBoolAction(action, "set_focus_peaking_enabled", uiSettings.focusPeakingEnabled);`; `App:8950` (event) | `run_script` slots go to `hardwareScriptRunner_.request` (`App:8662-8664`) | A GPIO callback that calls `camera_.startRecording()` |
| C1-S12 | Events are JSON strings built at the emit site and handed to `publishEvent`. `publishEvent` first feeds `handleTriggerEvent` (tally LED, trigger pulse), then decides by substring whether to broadcast now or to append to the current socket reply | usually | `App:10823-10852`; `App:6784` `[this](const std::string &eventJson) { publishEvent(eventJson); }`; `App:8394` (sound recorder) | 3 direct `controlServer_.broadcast` calls: `prepare_recording` `App:10692`, `:10705`; single-shot `photo_capture` `App:10730-10732` (calls `handleTriggerEvent` by hand first) | An event class hierarchy, a subscriber list, an output driven by a direct call from capture code |
| C1-S13 | Camera state is serialised by three hand-written functions with the same keys in the same order: `settingsBody` (reply), `settingsEvent` (event), the inline block in `buildWebStateJson` (HTTP). A new camera field is added to all three, at the same position | usually (key sets diffed: 42 literal keys in body = 42 in event; web has 38 of them) | `App:167-216`; `CC:136-187`; `App:7857-7897` | The web copy has no top-level `photo_mode_enabled`, `photo_long_exposure_enabled`, `photo_bracketing_enabled`, `photo_bracketing_ev`; it carries them inside `"ui":{}` (`App:7994-7997`) | One shared serialiser called by all three; a field present in the reply but missing from the event |
| C1-S14 | Two state shapes exist. Socket `get_state`: flat status keys plus `settingsBody` (`App:9218-9240`). HTTP `GET /api/state`: the same keys plus the groups `system`, `capture`, `ui`, `audio`, `imu`, `device` (`App:7835-8044`). UI.conf values are sent only in `"ui":{}`; the touch UI reads the file itself | always | `App:9238` `<< "," << settingsBody(camera_.settings());`; `App:7965` `<< ",\"ui\":{"`; UI: `Apertar-UI/src/SettingsBridge.cpp:413` (file watcher) | none | UI.conf values added to `get_state` or to the `settings` event |
| C1-S15 | Camera settings persist on every commit: setter -> `applySettingsLocked` -> `persistSettingsLocked` -> `CaptureSettingsPersister` (25 ms debounce, whole file, atomic). The file holds the active set plus one profile per record format and one for stills | always | `CC:8719` `if (commit) persistSettingsLocked();`; `CC:8725-8731`; `CC:853` `cv_.wait_for(lock, std::chrono::milliseconds(25), ...`; `CC:789` `settingsFile::atomicWrite(path, output.str())` | `setTuningFile` commits by hand (`CC:8081`, `:8108`) | A setting saved from App, a second settings file, a write on a timer |
| C1-S16 | A UI.conf write is a read-modify-write of the `[General]` section under a QLockFile-compatible lock, then an atomic rename. It runs synchronously inside the command. Other sections and unknown keys are kept | always (one writer function) | `App:1850-1935`; `App:1861` `settingsFile::QtIniLock settingsLock(path);`; `App:1934` `return settingsFile::atomicWrite(path, output.str());`; `SF:58` "QSettings uses QLockFile on <file>.lock. Cooperate without linking Qt into Core." | none | `std::ofstream` straight onto UI.conf, a debounced UI.conf writer, linking Qt into Core |
| C1-S17 | App owns its threads as `std::thread` members. Start: set the running flag under the group's mutex, then `std::thread(&ApertarCoreApp::runX, this)`. Stop: clear the flag under the mutex, `notify_all`, `join` if joinable, then clean up under the mutex | always (5 constructions, 0 `detach()` in App) | Start `App:6821-6825`, `App:6829-6834`, `App:9188-9198`. Stop `App:10988-11014`, `App:8238-8260` | None in App. `ControlServer` and `WebServer` detach one thread per client and count them (`CS:215-227`, `WS:276-287`) | `std::async`, `std::jthread`, a thread pool, a detached thread in App, a thread stored in a global |
| C1-S18 | Members in `AppH`: owned components by value first, then state groups. Each group starts with its mutex and ends with its thread. Groups are split by a blank line. Flags read across threads without the mutex are `std::atomic<T> name_{init};` | always | `AppH:110-124` (components); `AppH:140-147` (preview group: mutex, cv, queues, flag, thread); `AppH:168-176` (speed-test group) | none | `std::unique_ptr` members for owned parts, an Impl struct, a lone mutex far from its data |
| C1-S19 | Parts talk to App through `std::function` callbacks passed in the constructor's initialiser list. No part holds a pointer to App | always | `App:6783-6785` (`camera_` gets event and preview lambdas); `App:6786-6792` (inputs get action lambdas); `CCH:19-20`, `:31` | none | An observer interface, a singleton App pointer, a signal/slot layer |
| C1-S20 | A slow job that must not hold the command lock becomes a worker thread with its own state group and mutex. The command only starts it; clients poll the result | once (media speed test; it is the only such job) | `App:8957-9010` (start), `App:9012-9083` (worker), `App:10608-10621` (`get_media_test_state`, `run_media_speed_test`), `App:7745-7761` (web state copy) | Everything else that is slow runs under the lock (5.13; rough edge 18) | A generic job queue, a future returned to the client |
| C1-S21 | Periodic supervision lives in the 1 Hz loop of `wait()` on the main thread. There is no timer thread | once (only one such place) | `App:7021-7053` | none | A new `std::thread` that sleeps and polls |
| C1-S22 | A preset is one flat `apply_preset` command. Keys are camelCase: UI.conf keys as they are, camera values as `camera<Name>`. Core writes preset files (`buildCurrentPresetPayload`) and applies them in one transaction (`applyCapturePreset` with a UI.conf commit callback) | once (one preset feature; writer and reader are the two places) | Writer `App:6522-6697`; reader `App:10230-10527`; `App:10519-10522` | none | Applying a preset as a list of `set_*` commands; a nested `settings` object in the command |
| C1-S23 | Favourites are an ordered list of ids. Core keeps the allowed ids in `favoriteCandidateOrder()` and drops unknown ids on write and on read | once | `App:727-763`; `App:10224` `parseFavoritesOrderValue(*value)`; `App:1808` | Presets pass `favoritesOrder` through unfiltered (`App:10513-10515`) | A second favourites store |
| C1-S24 | A launch option is an `Options` member with its default, a hand-written `if (arg == "--x" ...)` in `main`, a usage line and a README row | always (5 options) | `AppH:32-38`; `src/main.cpp:52-82`; `src/main.cpp:32-37`; README:252-257 | none | `getopt`, a config file for process options, an environment variable switch in the command plane (0 `APERTAR_*` reads in `handleCommand`; `App` reads only `APERTAR_HARDWARE_CONFIG`, `App:4254`) |
| C1-S25 | `start()` brings parts up in a fixed order (preview and MJPEG threads, camera, socket, web, trigger output, inputs, tally LED) and undoes the earlier ones by hand when a required part fails. Optional hardware that fails logs "... disabled: <reason>" and start continues. `stop()` stops inputs first, then outputs, sound recorder, camera, preview threads, web, socket | usually | `App:6838-6843`, `App:6859-6867` (unwind); `App:6881-6884`, `App:6893-6896` (optional); `App:6913-6929` (stop order) | Input classes' `start()` results are ignored (`App:6886-6891`) | A part that aborts Core start because an optional accessory is missing |

---

## 3. Rules: IDIOM (how the code is written)

| Id | Rule | Strength | Evidence | Exceptions and notes | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C1-I01 | A camera setter command has this shape: read the field, one presence check, call `camera_.setX(...)`, reply `settingsBody` on success and `camera_.lastError()` on failure. See 5.1 | always (33 success replies, 41 `camera_.lastError()` replies) | `App:9242-9249`; `App:9275-9282`; `App:9439-9446` | None. `set_timecode_mode` adds a UI.conf mirror to the same shape (`App:9433-9435`) | Range checks duplicated in App for a value the camera already validates; a reply that echoes only the new value |
| C1-I02 | A UI.conf value command has this shape: read `value`, normalise, refuse when the trimmed input differs from the normalised label, write one pair, echo `"snake_key":value`. See 5.1 | usually (11 round-trip checks) | `App:9802-9813`; `App:9739-9750`; `App:10206-10217` | `set_ui_orientation`, `set_camera_controls_mode`, `set_battery_type` accept anything and fall back to the default (`App:10003`, `:10025`, `:10129`). `set_ui_orientation`, `set_camera_controls_opacity`, `set_camera_controls_mode` reply `settingsBody` (`App:10006`, `:10017`, `:10028`) | Writing the raw client string into UI.conf |
| C1-I03 | The single argument is named `value` (53 reads). A boolean argument is named `enabled`. Other field names are snake_case | usually | `App:9243` `command.number("value")`; `App:9482` `command.string("enabled")`; `App:10597` `command.string("device_path")` | `set_wb` uses `kelvin` (`App:9300`), `set_tuning_file` uses `path` (`App:9389`). `apply_preset` fields are camelCase preset keys (`App:10270`) | `{"cmd":"set_x","x":1}`, camelCase fields in an ordinary command |
| C1-I04 | Command names are snake_case. 82 of 110 are `set_<thing>`. Booleans are `set_<thing>_enabled` (19). An "auto" variant is its own command without fields. Actions are `<noun>_<verb>` or `<verb>_<noun>` | usually | `App:9269` `set_iso_auto`; `App:9293` `set_shutter_auto`; `App:9493` `set_focus_peaking_enabled`; `App:10623` `record_start` | `set_standby_usb_power_off` is a boolean without `_enabled` (`App:9129`) | `setIso`, `iso`, `toggle_x`. Note: the prefix has an effect, `set_` and `timelapse_` reset the idle timer (`App:9112-9114`) |
| C1-I05 | Booleans arrive as strings and are tested by hand: `*enabled == "true" \|\| *enabled == "1"`. `ControlCommand` has no boolean accessor | always (10 sites in `handleCommand`) | `App:9486`; `App:9518`; `App:10630` | None. Two commands add a strict check before the same test (`App:9131`, `App:9602`) | `command.number("enabled")`, a new `command.boolean()` accessor |
| C1-I06 | Replies come only from `okReply(command.id, fragment)` and `errorReply(command.id, sentence)`. A fragment is a brace-less list of `"snake_key":value` pairs. `id` is echoed when it is 0 or more | always (`grep` finds both helpers only in `App`) | `App:108-118`; `App:120-128`; `App:9213` `return okReply(command.id, "\"pong\":true");` | None. HTTP file routes reuse the helpers with id -1 (`App:7188`, `:7647`) | A reply built without the helpers, a camelCase key, an error without the `error` key |
| C1-I07 | An error is one sentence for the operator: capital first letter (or the command name), full stop, no "!", no "please", no "error"/"failed". It says what is wrong or what to do first. See 5.3 for the families | always (173 literal sentences read; 170 end in a period, 3 are prefixes joined to a detail) | `App:9097` "Wait for the current capture to finish writing to media."; `App:9211` "Wake the camera before capturing."; `App:9245` "set_iso requires value."; `CC:7715` "Resolution changes are blocked while recording." | None. Spelling is mixed: "ProRes colour" (`App:9373`) and "focus peaking color" (`App:9746`) | Error codes, exception text, "Error: ...", debug detail meant for a developer |
| C1-I08 | JSON is written by hand with `std::ostringstream` and `<<`. Booleans: `(x ? "true" : "false")` (80 sites). Free text: `escapeJson(...)` (142 uses). Numbers: `jsonNumber(v, precision)`, `compactNumber(v)`, `std::to_string`. Optional telemetry: `jsonNumberOrNull`. There is no JSON library in Core | always (`grep -rnE 'nlohmann\|rapidjson\|QJson\|json\.hpp' src include CMakeLists.txt` = 0) | `App:9222-9238`; `App:167-215`; `App:279-304` | none | Adding a JSON dependency; `std::boolalpha`; an unescaped user string in JSON |
| C1-I09 | A command is one line with one flat JSON object. Every value is stored as text. Nested objects and arrays do not parse. A list travels as one string, split on `\|` or `,` | always | `CP:204` `result.command.fields[*key] = *value;`; `CP:124` `while (pos < text.size() && text[pos] != ',' && text[pos] != '}')`; `App:771-792` `splitSimpleListValue`; `WCP:10504-10514` `scalarPresetValue` (client flattens) | None for commands. Replies and state are not flat everywhere, see 5.5 | `{"cmd":"x","window":{"x":0}}`, `{"cmd":"x","values":[1,2]}` |
| C1-I10 | A helper that can fail returns `bool` and writes the operator sentence through `std::string *errorMessage` (null-checked). A parser returns `std::optional`. No exception crosses `handleCommand` (0 `try` in the dispatcher) | usually (22 `errorMessage` parameters, 65 null-checked writes) | `App:3127` `bool applyFanMode(const std::string &mode, std::string *errorMessage)`; `App:8957` `bool ApertarCoreApp::startMediaSpeedTest(std::string *errorMessage)`; `App:892` `std::optional<double> parseDoubleValue(...)` | `allocateSoundRecordingFolder` throws (`App:1448`, `:1476`, `:1479`), caught at `App:8369-8375` | Exceptions for control flow, error enums, `std::expected` |
| C1-I11 | A set of allowed labels gets a free function `normalize<Name>Value(const std::string &)` that returns the canonical label, or the default label for unknown input. The same function is used when reading UI.conf and when handling the command | usually (19 such functions, `grep -nE '^std::string normalize[A-Za-z]+(Value\|Label)\('`; 18 return a default) | `App:669-677` `normalizeGuidesTypeValue`; `App:1701` (read); `App:9807` (command) | `normalizeRecordingFormatValue` returns an empty string for unknown input, which the command refuses (`App:824-844`, `App:9331-9333`) | An enum plus a string table for a UI.conf label; validation written inline twice |
| C1-I12 | A numeric UI value is clamped without an error and the clamped value is echoed. A camera value is checked for presence in App and for range in the `CameraController` setter | usually | Clamp: `App:9733`, `App:10108`. Camera: `App:9244-9245` and `CC:7777-7780` "ISO must be between 50 and 51200." | Newer commands also check `std::isfinite` and a range in App (`App:9122`, `:9253`, `:9286`, `:9614`) | An out-of-range volume answered with an error |
| C1-I13 | Logging is `std::cerr` only, for failures and ignored input. A line starts with a fixed prefix, carries the detail, ends with `'\n'`. Success is silent. No levels, no `std::endl` (0 in `src`) | always (14 `std::cerr` sites in 11 025 lines) | `App:1863` "ApertarCore could not lock shared settings: "; `App:8954` "Hardware input action ignored: unknown action '"; `App:9156` "Apertar standby: " | None. The prefix varies: "ApertarCore ...", "Apertar ...", "Hardware input ..." | A log line per command, a logging class, debug output left in |
| C1-I14 | Comments are rare and state a hazard or a reason, as a sentence. No doc comments, no section banners, no TODO (10 comment lines in `App`, 0 `///`, 0 TODO/FIXME in `src`) | always | `App:10827-10828` "Settings must also reach the separate HDMI process immediately, not just the command's requester."; `App:8103-8104`; `App:1543` "Fixed executable and arguments only; never accept paths from WebUI/config."; `CS:24`; `src/main.cpp:89-90` | None. Trailing field notes in `Types:132-150` follow the same rule ("// Runtime libcamera capability.") | A comment that repeats the code, a ticket number, a banner |
| C1-I15 | Layout: 4 spaces, no tabs. Function brace on its own line; control brace on the same line. A one-statement `if` has no braces and its body sits on the next line (201 lines are a bare `return errorReply(...)` under their `if`; 8 are `if (...) return ...;` one-liners). A blank line separates command blocks (75 of 95). Locals are `const auto` (187 in the dispatcher). No `.clang-format` in the repo | usually | `App:9242-9249`; `App:9802-9813` | Denser blocks without blank lines: `App:9118-9211` (standby), `App:9537-9639` (capture mode, stills), `App:10031-10074` (audio) | Reformatting untouched code, tabs, `else` after `return` |
| C1-I16 | Names. Types: PascalCase. Functions, locals: camelCase. Members: trailing underscore. Constants: `kName`. Wire JSON and `camera_settings.conf`: snake_case. UI.conf and preset keys: camelCase. Read-once structs end in `Snapshot`. JSON fragment builders end in `Body` or start with `json` | always (0 camelCase keys in dispatcher replies) | `App:1581` `struct SharedUiSettingsSnapshot`; `App:60` `kWebPreviewMaxWidth`; `AppH:132` `commandMutex_`; `App:9487` `{ settingKey, value ? "true" : "false" }` with key `focusPeakingEnabled`; `App:7967` `focus_peaking_enabled` | none | `focusPeakingEnabled` in a reply; `focus_peaking_enabled` in UI.conf |
| C1-I17 | A shape that repeats inside one function becomes a local lambda defined just before first use. It is not promoted to a member or a free function | usually (4 precedents) | `App:9478` `auto handleUiToggle = [this, &command](const char *name, const char *settingKey) -> std::optional<std::string> {`; `App:10232` `auto addBoolUpdate = [&](const char *key) -> bool {`; `App:8671` `auto dispatch = [this](std::string commandName,`; `App:6541` `auto addBool = [&](const char *key, bool value) {` | The 13 UI.conf value blocks (`App:9729-9888`) and the 8 IMU blocks (`App:9646-9704`) are written out in full | A template or macro for command blocks |
| C1-I18 | A command that changes the camera and UI.conf together keeps both in step. Either the UI.conf write is the commit callback of `applyCapturePreset`, or the camera is put back when the write fails | usually | `App:9607-9609`; `App:9594-9597` `camera_.applyCapturePreset(previous);`; `App:10519-10522`; `CC:8634-8656` | `set_timecode_mode` ignores the write result (`App:9433` `(void)updateSharedUiGeneralSettings`); `set_sound_recorder_enabled` does not restore (`App:9527-9534`) | Camera changed, UI.conf write failed, reply says ok |
| C1-I19 | A probe that shells out and is needed by the 1 Hz state poll caches its result inside its own function: function-local `static std::mutex cacheMutex`, a time stamp and a short fixed lifetime | usually (2 precedents) | `App:2266-2283` (lsblk, 3 s); `App:2786-2800` (ALSA devices, 2 s) | Other probes in `buildWebStateJson` run every call (`App:7735-7743`) | A member cache in App, a background poller |
| C1-I20 | An event is a literal `{"event":"<name>",...}` with the `event` key first and no spaces. Receivers inside Core match it with `find("\"event\":\"<name>\"")` | always (15 names) | `App:6901` `publishEvent("{\"event\":\"camera_state\",\"state\":\"ready\"}");`; `CC:139` `out << "{\"event\":\"settings\""`; `App:10862` | none | An event built with a different key order or with spaces; routing by a parsed field |
| C1-I21 | Locks: `std::lock_guard<std::mutex> lock(mutex_);` (34 sites) in the smallest brace scope. A worker loop unlocks before I/O and locks again after | usually | `App:10971-10974` `lock.unlock(); publishPreviewFrame(frame); ... lock.lock();`; `App:8214-8223` | 3 CTAD forms `std::lock_guard lock(...)` (`App:7032`, `:9102`, `:10609`) | `std::scoped_lock` over several mutexes, a lock held across a socket send in a worker |

---

## 4. Rules: INTENT (product decisions the code encodes)

| Id | Rule | Strength | Evidence | Exceptions and notes | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C1-N01 | Core is the single source of truth. The three control surfaces are equal: same commands, same busy checks, same replies | always | README:271; README:3 "keeps the camera's settings in sync with the touchscreen interface, hardware buttons and WebUI"; `App:7090`, `App:8462` | None. Note: a failed hardware-made command is only logged (`App:8463-8464`) | A feature that works from the WebUI only because its logic sits in a route or in JS |
| C1-N02 | A refusal talks to the operator and is shown as written. The touch UI stores it as the last error; the WebUI shows it as a toast | always | `CB:1084-1086` `setLastError(message.value(QStringLiteral("error")).toString(...))`; `WCP:9128-9132` `throw new Error(result.error \|\| "Command failed.")`; sentences in 5.3 | none | A reply the UI has to translate; a silent no-op for a refused action |
| C1-N03 | During a take, nothing that changes the stream, the file format or the media is allowed. Exposure stays adjustable | always (all `setErrorLocked` lines read) | Refused: `CC:7715` resolution, `CC:7745` fps, `CC:7928` format, `CC:7977` compression, `CC:8118` bit depth, `CC:8052` tuning file, `CC:8608` preset; `App:9105-9107` format/eject/mount/speed test; `App:7514-7519`, `App:7586-7591` media delete; `App:9706-9707` gyro calibration; `App:10053-10054` audio capture options. Allowed: `CC:7774-7786` ISO, `CC:7796-7825` shutter, `CC:7888-7904` white balance, `CC:8184-8217` autofocus (no `recording_` check) | None found. `setTimecodeMode` has no take guard (`CC:8176-8182`); it does not shape the stream | A new stream-shaping setting without a `recording_` check; a media operation outside the `mediaAction` gate |
| C1-N04 | No new capture starts while data from the last one is still being written, or while a speed test runs | always | `App:9095-9097`; `App:9108-9110`; `CC:8243-8245`; `CC:8269-8271`; README:102 "prevents another capture from starting before the previous work is complete" | none | A capture command missing from these lists |
| C1-N05 | Failures are reported, not hidden. Core checks for a failed recording before every command and once a second, and state carries the error text and the dropped-frame flag | always | `App:9094` `if (camera_.checkRecordingFailure()) syncRecordingTracking(false);`; `App:7033`; `App:9226-9227` `recording_error`, `recording_has_dropped_frames`; `App:9234` `photo_write_error`; README:299 | none | A recording error that only reaches the log |
| C1-N06 | A change that fails leaves the camera in its last working state. Core says what failed and stays usable | always | `CC:8693-8705` (reconfigure back to the previous settings); `CC:8248-8253` ("Keep the controller ready so the user can retry"); `App:9200-9204` (wake failure); `App:9151-9172` (standby power saving skipped with a `warning`, command still ok) | none | `state_ = Error` after a refused setting; Core exit on a failed mode switch |
| C1-N07 | Settings outlive a restart, and every client sees a settings change at once, also clients that did not ask for it | always | `CC:8719-8721` (persist, then event); `App:10827-10840` (always-broadcast list); README:18 | None for `settings`. Events off that list are appended to the requester's reply only (`App:10843-10848`), for example `recording` after a socket `record_start` | A setting that changes without a `settings` event |
| C1-N08 | In Standby any input only wakes the camera. A capture is refused with a sentence. Operator activity resets the idle timer | always | `App:8642-8649`; `App:9208-9211`; `App:9111-9117`; `App:8616-8617` | none | A button that records straight out of Standby |
| C1-N09 | The frame path never waits. Sends are non-blocking and a stalled client is dropped; only the newest preview frame is kept; code on libcamera's thread does not call back into the controller | always | `CS:24-25` "Never let a stalled preview client block camera event delivery." `MSG_NOSIGNAL \| MSG_DONTWAIT`; `App:6977-6987` (replace pending frame); `App:8103-8104` | none | A blocking write or a `camera_.x()` call inside a preview callback |
| C1-N10 | The WebUI is a tool for a trusted LAN. It has an origin check, fixed helper command lines and path checks. It has no accounts | always | `WS:156-170`; `App:1543`; `App:7126-7129`; `App:5157-5165` `isSafePresetFileName`; README:130 | none | Shell commands built from request text; a route that takes a file path |
| C1-N11 | Core and the UI ship together. The protocol has no version. A missing field falls back to a default; an unknown key is ignored | always (no `version` key in any reply or state; only preset files carry `"version":1`, `App:6530`) | README:306 "Update Core and Apertar-UI together so their controls and capabilities match."; `CC:721-723` "Ignore malformed values and keep defaults for resilience."; `App:10820` | none | Capability negotiation, version handshakes |
| C1-N12 | Monitoring aids and UI preferences are UI state, not camera state. They live in UI.conf, may change during a take, and are not written into the footage | always | `App:9478-9491` (toggle lambda has no take guard); 56 keys in `App:1581-1639`; README:155 "Preview LUTs, monitoring overlays and display calibration are not baked into RAW recordings."; README:267 | None for monitoring aids. Still mode, long exposure and bracketing are capture state kept in both stores; UI.conf wins at start (`App:6845-6857`) | A zebra or LUT flag added to `CaptureSettings` |

---

## 5. Reference: how each piece works

### 5.1 The two canonical command blocks

Camera setter (`App:9242-9249`):

```cpp
    if (command.name == "set_iso") {
        const auto value = command.number("value");
        if (!value)
            return errorReply(command.id, "set_iso requires value.");
        return camera_.setIso(static_cast<uint32_t>(*value))
            ? okReply(command.id, settingsBody(camera_.settings()))
            : errorReply(command.id, camera_.lastError());
    }
```

UI.conf value (`App:9802-9813`):

```cpp
    if (command.name == "set_guides_type") {
        const auto value = command.string("value");
        if (!value)
            return errorReply(command.id, "set_guides_type requires value.");

        const std::string normalized = normalizeGuidesTypeValue(*value);
        if (trimAscii(*value) != normalized)
            return errorReply(command.id, "Unsupported guides type.");
        if (!updateSharedUiGeneralSettings({ { "guidesType", normalized } }))
            return errorReply(command.id, "Could not update shared UI settings.");
        return okReply(command.id, "\"guides_type\":\"" + escapeJson(normalized) + "\"");
    }
```

UI.conf toggle, one line per command (`App:9495-9496`):

```cpp
    if (const auto reply = handleUiToggle("set_zebra_enabled", "zebraEnabled"))
        return *reply;
```

### 5.2 `handleRequest`, `handleWebCommand`, `handleCommand`

| Step | What | Line |
| --- | --- | --- |
| Parse | `parseControlCommand(line)`; a parse error is `errorReply(-1, parsed.error)` | `App:7057-7059`, `App:7087-7089` |
| Socket only: collect | `collectingCommandEvents_ = true` under `eventMutex_`; after the command the collected events are appended to the reply, one per line | `App:7061-7080` |
| Web: no collect | `handleWebCommand` returns the reply only. HTTP status is 200 also for `ok:false` | `App:7085-7091`, `App:7637-7641` |
| Lock | `commandMutex_` | `App:9093` |
| Supervisor | recording failure check | `App:9094` |
| Gate 1 | `capture_photo`, `record_start`, new `timelapse_start` refused while media writes are pending | `App:9095-9097` |
| Gate 2 | `format_media`, `eject_media`, `mount_media`, `run_media_speed_test` refused while recording, sound recording, timelapse, pending writes or a running speed test | `App:9098-9107` |
| Gate 3 | `record_start`, `capture_photo`, `timelapse_start`, `enter_standby` refused during a speed test | `App:9108-9110` |
| Idle reset | `user_activity`, `wake`, every `set_*`, `capture_photo`, `record_start`, `record_stop`, every `timelapse_*` | `App:9111-9117` |
| Standby family | `user_activity`, `set_standby_timeout`, `set_standby_usb_power_off`, `enter_standby`, `wake` | `App:9118-9207` |
| Gate 4 | Standby: `record_start`, `capture_photo`, `timelapse_start` refused | `App:9208-9211` |
| Chain | `ping`, `help`, `get_state`, camera setters, toggles, stills, IMU, UI.conf values, audio, battery, favourites, preset, system, media, record/photo/timelapse, `preview_subscribe`, power, `shutdown` | `App:9212-10818` |
| End | unknown command | `App:10820` |

Family order in the chain (**probable**: order of growth; newer families are denser and several are missing from `help`):

| Lines | Family | Reply |
| --- | --- | --- |
| `App:9242-9476` | camera setters | `settingsBody` |
| `App:9478-9512`, `:9640-9645`, `:9724-9727` | 15 UI.conf toggles | `settingsBody` |
| `App:9513-9639` | sound recorder, capture mode, stills | `settingsBody` (+ extra keys) |
| `App:9646-9723` | IMU, writes `apertar-hardware.conf` through `Mpu6050RecordingSession` | `imuStatusBody(false)` |
| `App:9729-10029` | UI.conf values (monitoring, stills, orientation, opacity) | `"snake_key":value` |
| `App:10031-10122` | audio | `"snake_key":value` |
| `App:10124-10228` | battery, sleep, favourites | `"snake_key":value` |
| `App:10230-10527` | `apply_preset` | `"applied_preset":..,"state":{settingsBody}` |
| `App:10529-10621` | date/time, fan, media | `"<thing>_<done>":true` flags |
| `App:10623-10794` | record, photo, timelapse | status keys |
| `App:10796-10818` | preview subscribe, restart, power off, shutdown | flags |

### 5.3 `ControlCommand`, the parser, replies and error sentences

| Item | Fact | Line |
| --- | --- | --- |
| Type | `struct ControlCommand { int id = -1; std::string name; std::map<std::string, std::string> fields; }` | `src/ipc/ControlProtocol.hpp:9-16` |
| Accessors | `number(key)` -> `std::optional<double>` (`std::stod`, must consume the whole text). `string(key)` -> `std::optional<std::string>`. No boolean, no integer accessor | `CP:139-162` |
| Optional argument | `command.string("format").value_or(uiSettings.photoFormat)` (11 `.value_or(` sites) | `App:10718`, `App:10580` |
| Present but malformed | `command.fields.count("count") && (!requestedCount \|\| ...)` | `App:10720` (once) |
| Parser | one object; a quoted string or a bare token up to `,` or `}`; duplicate key: last wins; `cmd` required; `id` optional | `CP:164-233` |
| Parser errors | "Expected JSON object.", "Expected object key.", "Expected ':' after object key.", "Expected value for key '<k>'.", "Expected ',' or '}'.", "Missing command name." | `CP:170`, `:183`, `:188`, `:200`, `:216`, `:224` |
| Line limits | 64 KiB per line, `\r` dropped, empty line ignored | `CS:260-263`, `CS:249` |
| `okReply` | `{"ok":true[,"id":N][,<fragment>]}` | `App:108-118` |
| `errorReply` | `{"ok":false[,"id":N],"error":"<escaped sentence>"}` | `App:120-128` |
| Client contract | The UI opens a connection per command, sends `cmd` + `id`, reads lines until the `id` matches, and feeds every line (reply and events) to `applyCoreMessage` | `CB:1044-1090` |

Reply families:

| Family | Fragment | Example |
| --- | --- | --- |
| Camera state | `settingsBody(camera_.settings())` (33 sites) | `App:9247` |
| Echo | `"snake_key":<normalised value>` | `App:9749`, `App:10111` |
| IMU | `imuStatusBody(false)` = `"imu":{...}` | `App:9654` |
| Done flag | `"media_ejected":true`, `"date_time_applied":true`, `"pong":true`, `"restarting":true` | `App:10593`, `:10549`, `:9213`, `:10805` |
| Capture status | `"recording":true,"recording_has_dropped_frames":..`; `"photo_capture":true,"photo_count":N,"media_writes_pending":..,"media_write_revision":N` | `App:10712`, `App:10735-10737` |

Error sentence families (173 literal sentences in `handleCommand`; 0 with "!", "?", "please", "error" or "failed"):

| Family | Count | Example | Line |
| --- | --- | --- | --- |
| `<command> requires <field>.` | 58 | "set_fps requires value." | `App:9278` |
| "Could not update shared UI settings." | 36 | same text each time | `App:9488` |
| `Could not <verb> ...` (other) | 5 | "Could not save standby timeout." | `App:9126` |
| `Invalid preset <thing>.` | 23 | "Invalid preset ISO." | `App:10369` |
| `Invalid <thing>.` | 3 | "Invalid audio sample rate." | `App:10062` |
| `Unsupported <thing>.` | 15 | "Unsupported guides type." | `App:9809` |
| `<Thing> must be <range or list>.` | 9 | "ProRes profile must be proxy, lt, 422 or hq." | `App:9381` |
| `Stop <activity> before <action>.` | 7 | "Stop recording before calibrating gyro." | `App:9707` |
| `Wait for <thing> ...` | 2 | "Wait for the media speed test to finish first." | `App:9110` |
| Other operator sentences | about 15 | "Enable a timelapse interval first."; "Sound Recorder requires an audio input device." | `App:10746`, `App:9520` |
| Passed through | 41 + 18 + 1 | `camera_.lastError()`, helper `errorMessage`, `error` | `App:9248`, `App:10575`, `App:10040` |

Camera-side sentences use the same voice: "<Thing> changes are blocked while recording." (`CC:7715`, `:7928`, `:7977`, `:8118`, `:8154`), "Stop ... before ...", "Wait for ... before ...", "<Thing> must be between A and B." (`CC:7749`, `:7778`, `:7896`).

### 5.4 Events

| Step | Fact | Line |
| --- | --- | --- |
| Source | `CameraController` calls the `EventCallback` given at construction; App emits its own with `publishEvent` | `App:6784`, `CC:8782-8783` |
| 1. Outputs | `handleTriggerEvent` drives the tally LED and the trigger pulse by substring match | `App:10825`, `App:10854-10889` |
| 2. Always broadcast | `settings`, `recording_health`, `standby`, `still_exposure`, `media_write_state`, `photo_write_error`, `timelapse_progress`, and `hardware_action` with action `standby_power_wake`, `standby_power_sleep`, `power_button_press` | `App:10829-10841` |
| 3. Else collect | while a socket request is being handled, the event is appended to that reply and not broadcast | `App:10843-10849` |
| 4. Else broadcast | `controlServer_.broadcast(eventJson)` | `App:10851` |
| Transport | each client has a write mutex; send is non-blocking; a failed send removes the client | `CS:172-179`, `CS:15-35` |
| Preview | `preview_buffer` (with dmabuf fds) and `preview_frame` go straight to `broadcastWithFds` / `broadcast` from the publisher thread | `App:10891-10944` |

Event names and emit sites (`grep -rnoE 'event\\":\\"[a-z_]+' src`):

| Event | Emitted at |
| --- | --- |
| `camera_state` | `App:6901`, `App:6913` |
| `settings` | `CC:139` (via `emitSettingsEventLocked` `CC:8777`) |
| `recording` | `CC:8792`; sound recorder `App:8394`, `App:8406` |
| `recording_health` | `CC:7582` |
| `audio_level` | `CC:7592`, `App:8383` |
| `media_write_state` | `CC:7560` |
| `still_exposure` | `CC:7570` |
| `photo_capture` | `CC:7177`, `App:10730` |
| `photo_write_error` | `CC:5248`, `CC:7029` |
| `standby` | `CC:7688`, `CC:7707` |
| `timelapse`, `timelapse_frame`, `timelapse_progress` | `CC:8804`, `CC:8830`, `CC:8443` |
| `prepare_recording` | `App:10692`, `App:10705` |
| `hardware_action` | `App:8476`, `:8612`, `:8619`, `:8623`, `:8667`, `:8904`, `:8950` |

UI.conf writes send no event. The touch UI sees them through a file watcher (`Apertar-UI/src/SettingsBridge.cpp:413-419`), the WebUI through its 1 Hz `GET /api/state` (`WCP:11609`).

### 5.5 The state serialisers and the "flat JSON" rule

| Serialiser | Where | Used by | Keys |
| --- | --- | --- | --- |
| `settingsBody` | `App:167-216` | every camera setter reply, 15 toggle replies, `get_state`, `apply_preset` | 42 literal keys + `exposure_metering`, `exposure_metering_modes` from `exposureMeteringJson` (`src/camera/ExposureMetering.hpp:28-39`) |
| `settingsEvent` | `CC:136-187` | `settings` event | the same 44 + `event`; `recording_capabilities` comes first |
| inline block in `buildWebStateJson` | `App:7857-7897` | `GET /api/state` | 38 of the 42 (the four `photo_*` keys are in `"ui":{}`) |
| status keys of `get_state` | `App:9223-9237` | socket | 15 keys |
| status keys of `/api/state` | `App:7836-7856` | HTTP | the same 15 + `standby_timeout_seconds`, `standby_usb_power_off`, `standby_usb_powered_off`, `recording_elapsed_seconds`, `timecode_local_ms_of_day`, `backend_name` |
| `"system":{}`, `"capture":{}`, `"ui":{}`, `"audio":{}`, `"imu":{}`, `"device":{}` | `App:7901-7949`, `:7950-7964`, `:7965-8021`, `:8022-8027`, `:8028`, `:8029-8043` | HTTP only | `ui` has 54 of the 56 UI.conf keys + `lut_preview_options` |

How a camera field gets into each copy: one more `<< ",\"snake_key\":" << ...` line in the existing `<<` chain, at the same relative position in all three.

"Flat JSON" stated exactly:

| Direction | Rule | Nested members that exist |
| --- | --- | --- |
| Command in | flat, always (the parser cannot do more, `CP:120-135`) | none |
| Reply and `settings` event | flat, with a fixed short list of nested values | `recording_capabilities` (object, `include/apertar/core/RecordingCapabilities.hpp:52-62`), `preview_exposure_reference` (object or `null`), `exposure_metering_modes` (string array), `imu` (object, `App:130-165`), `modes` (array of objects, `App:10042-10048`), `favorites_order` (string array, `App:10227`), `commands` (`App:9216`), `state` (object, `App:10526`) |
| `/api/state` | top-level camera and status keys flat; six fixed groups; a few arrays | `media_drives`, `time_zone_options`, `lut_preview_options`, `input_devices`, `output_devices` |

Number formats differ between the copies. `settingsBody` streams `exposure_compensation` after a sticky `std::fixed << std::setprecision(3)` (`App:173`, `:178`). The web copy uses `jsonNumber(settings.fps, 3)` and streams `exposure_compensation` with default formatting (`App:7860`, `:7865`).

### 5.6 The help text

| Fact | Line |
| --- | --- |
| One string literal on one line, 98 names, grouped by topic | `App:9216` |
| 12 handled commands are missing: `apply_preset`, `audio_capabilities`, `enter_standby`, `get_media_test_state`, `help`, `ping`, `set_audio_capture_options`, `set_capture_mode`, `set_standby_timeout`, `set_standby_usb_power_off`, `user_activity`, `wake` | diff of the literal against the dispatcher |
| No name in `help` is unhandled | same diff |

Rule strength for "add the new name to `help`": **usually** (98 of 110). All 15 toggles and all camera setters are listed.

### 5.7 HTTP routes (`handleWebRequest`, `App:7093-7649`)

| Method + path | Line | Does | Takes the command lock |
| --- | --- | --- | --- |
| `OPTIONS *` | 7095 | 204 | no |
| `GET /`, `/index.html` | 7102 | `webControlPageHtml()` | no |
| `GET /preview.mjpeg` | 7109 | `streamMjpeg` on the client thread; 503 without JPEG support | no |
| `GET /icons/<name>` | 7124 | PNG from the icons folder, name checked | no |
| `GET /api/state` | 7154 | `buildWebStateJson()` | no |
| `GET /api/media` | 7161 | `buildMediaLibraryJson()` | no |
| `GET /api/config` | 7168 | `buildHardwareConfigFileJson()` | no |
| `POST /api/config` | 7175 | body is the raw file text -> `saveHardwareConfigFile` (backup `.bak`) | no |
| `GET /api/media/download?kind=&id=` | 7197 | file or zip stream | no |
| `GET /api/media/download-selected?...` | 7318 | zip stream | no |
| `GET /api/presets` | 7360 | `buildPresetLibraryJson()` | no |
| `GET /api/presets/download/<file>` | 7367 | preset file | no |
| `POST /api/presets/import[/<name>]` | 7392 | body is the preset JSON -> `importPresetFileToCamera` | no |
| `POST /api/presets/save?name=` | 7440 | `saveCurrentPresetToCamera(..., camera_.settings(), ...)` | no |
| `POST /api/presets/delete?file=` | 7477 | `deletePresetFileFromCamera` | no |
| `POST /api/media/delete?kind=&id=` | 7503 | refused while recording, sound recording or timelapse | no |
| `POST /api/media/delete-selected?...` | 7575 | same guard | no |
| `POST /api/command` | 7637 | `handleWebCommand` -> `handleCommand` | yes |

Route idiom: every branch declares its own `WebServer::Response response;` (51 times), sets `response.contentType = "application/json; charset=utf-8";` (44 times), fills `response.body` with `okReply(-1, ...)`, `errorReply(-1, ...)` or a `build*Json()` result, and returns. Parameters travel in the query string (`queryParameterValue(request.query, "kind")`, `App:7198`) or the path tail. The body is the raw payload. Status codes used: 204, 400, 404, 500, 503 (and 413, 403 from `WS:360-373`).

### 5.8 Camera settings persistence (`camera_settings.conf`)

| Item | Fact | Line |
| --- | --- | --- |
| Path | `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf`, else `~/.config/apertar-core/camera_settings.conf`, else a temp file | `CC:342-353` |
| Format | `key=value` lines, no sections, snake_case keys, booleans as `0`/`1`, enums as wire strings | `CC:742-778` |
| Keys | 33 written, 34 read (legacy `wb_locked` is read and turned into auto white balance) | `CC:681-682`, `CC:726-728` |
| Profiles | active set without prefix, then `profile.<cdng\|mlv\|h264\|prores>.<key>` and `profile.still.<key>`. Lossy DNG shares the `cdng` profile | `CC:605-608`, `CC:634-648`, `CC:784-788` |
| Load | in the `CameraController` constructor; unknown keys ignored; a bad value is skipped inside `try`/`catch (...)`; then `clampCaptureSettings` | `CC:7598`, `CC:650-723`, `CC:729-739` |
| Commit | `applySettingsLocked(next, requiresReconfigure)` -> session reconfigure or controls -> `persistSettingsLocked()` -> `emitSettingsEventLocked()` | `CC:8659-8723` |
| What is stored where | photo mode: `stillSettings_ = settings_`; else `formatSettings_[profile] = settings_`; then `schedule(...)` | `CC:8725-8731` |
| Debounce | lazy worker thread; waits 25 ms for more changes; writes the whole file with `atomicWrite`; `flush()` in `~CameraController` | `CC:793-883`, `CC:853`, `CC:7616-7620` |
| Format switch | the saved profile of the new format replaces the settings; tuning file, timecode mode and metering are carried over | `CC:7939-7955` |
| Not persisted | runtime members marked with a trailing comment | `Types:132`, `:134`, `:139`, `:142`, `:150` |

### 5.9 The shared `UI.conf`

| Item | Fact | Line |
| --- | --- | --- |
| Path | `$XDG_CONFIG_HOME/CinePi/UI.conf`, else `~/.config/CinePi/UI.conf`. The UI opens the same file as `QSettings("CinePi", "UI")` | `App:341-348`; `Apertar-UI/src/SettingsBridge.cpp:287` |
| Defaults | `struct SharedUiSettingsSnapshot`, 56 members with in-class defaults | `App:1581-1639` |
| Read | `readSharedUiSettings()`: only `[General]`; one `else if (key == "camelKey")` per member; each value normalised or clamped on the way in | `App:1641-1813` |
| Raw read | `readSharedUiGeneralSettingsMap()` for keys Core does not model (`lastPhotoTimelapse`, `*Order`, `horizontalLevel*`) | `App:1815-1848`, `App:9549`, `App:6691-6693` |
| Write | `updateSharedUiGeneralSettings({ { "key", "value" }, ... })`: lock, read lines, replace or append in `[General]`, atomic write. Returns `bool` | `App:1850-1935` |
| Value text | booleans `true`/`false`; numbers via `compactNumber`, `jsonNumber(v, 2)` or `std::to_string`; labels in the form the UI shows ("Rec Run", "Clean Feed", "DNG + JPEG") | `App:9487`, `App:9734`, `App:9434` |
| Lock | `<file>.lock` in QLockFile format, 2 s deadline, dead owners removed | `SF:59-118` |
| Who sees a change | touch UI: file watcher; WebUI: `"ui":{}` in the 1 Hz state poll; hardware actions: read before each action (`App:8684`) | see 5.4 |

All 15 toggles appear in the same seven places (checked one by one): struct member, parse branch, `handleUiToggle` line, `help`, `"ui":{}`, preset writer, preset reader. 10 of 15 also have a hardware action.

### 5.10 Presets and favourites

| Item | Fact | Line |
| --- | --- | --- |
| File | `<name>.apertar-preset.json`: `{"type":"apertar-preset","version":1,"name":..,"createdAt":..,"settings":{...}}` | `App:6527-6533`, `App:5157-5165` |
| Folders searched | `$XDG_DATA_HOME/Apertar-UI/presets`, `.../ApertarUI/presets`, `~/.local/share/Apertar-UI/presets`, `~/.local/share/ApertarUI/presets`, `~/.config/CinePi/UI/presets` | `App:5216-5242` |
| Writer | `buildCurrentPresetPayload`: UI.conf keys through `addBoolFromMap` / `addIntFromMap` / `addDoubleFromMap` / `addStringFromMap`, camera values as `camera*` | `App:6522-6697` |
| Reader | `apply_preset`: camera fields validated one by one ("Invalid preset <thing>."), UI.conf pairs collected with `addBoolUpdate` / `addIntegerUpdate` / `addDoubleUpdate` / `addStringUpdate`, then one `camera_.applyCapturePreset(presetSettings, commit)` | `App:10230-10527` |
| Nested to flat | done by the client: the browser downloads the file, keeps allow-listed keys of `settings`, sends them as fields of `apply_preset` | `WCP:10516-10600`, `WCP:10649-10660` |
| Core never parses the nested file | only `extractJsonStringField(payload, "name")` | `App:5392`, `App:6480` |
| `*Order` key list | written twice by hand | `App:6691-6692`, `App:10513-10514` |
| Favourites | allow-list `favoriteCandidateOrder()` (31 ids); `set_favorites_order` stores `"a, b, c"` in `favoritesOrder`; state returns a JSON array | `App:727-763`, `App:10219-10228`, `App:8020` |

### 5.11 Threads and locks owned by App

| Thread | Started | Loop | Stopped |
| --- | --- | --- | --- |
| Preview publisher `previewThread_` | `start()` `App:6821-6825`; `wake` `App:9188-9192` | `runPreviewPublisher` `App:10946-10986`, waits on `previewCv_` | `stopPreviewPublisher` `App:10988-11014`; called in `stop()` and in `enter_standby` (`App:9149`) |
| MJPEG encoder `mjpegThread_` | `start()` when `webPort != 0` and JPEG is built `App:6827-6836`; `wake` `App:9193-9199` | `runMjpegEncoder` `App:8194-8236`, waits on `mjpegCv_` | `stopMjpegEncoder` `App:8238-8260` |
| Media speed test `mediaSpeedThread_` | `startMediaSpeedTest` `App:9008` | `runMediaSpeedTest` `App:9012-9083`, runs once | `joinMediaSpeedTest` `App:9085-9089`; before the next start `App:8968`; in `stop()` `App:6929` |
| Main thread | `wait()` `App:7021-7053` | 1 Hz: recording failure check, idle standby | `requestShutdown` `App:11016-11023` (signal thread `src/main.cpp:113-120`, or `shutdown` command `App:10815-10818`) |
| Not owned by App | socket clients, HTTP clients, input classes, sound recorder, camera workers, settings persister | - | their own classes |

| Mutex | Declared | Guards | Lock sites |
| --- | --- | --- | --- |
| `commandMutex_` | `AppH:132` | command execution; the 1 Hz failure check | `App:9093`, `:7032` |
| `hardwareInputSequenceMutex_` | `AppH:131` | one button's action list, across all input classes | `App:8485`, `:8641` |
| `hardwareActionMutex_` | `AppH:130` | one hardware-made command at a time | `App:8460` |
| `eventMutex_` | `AppH:136` | `collectingCommandEvents_`, `pendingCommandEvents_` | `App:7062`, `:7071`, `:10844` |
| `previewMutex_` | `AppH:140` | preview queues, registrations, `previewPublisherRunning_` | `App:6822`, `:6956`, `:6996`, `:9189`, `:10948`, `:10991`, `:10999` |
| `mjpegMutex_` | `AppH:149` | web preview slots, pending and latest JPEG, `mjpegEncoderRunning_` | `App:6830`, `:8084`, `:8109`, `:8124`, `:8200`, `:8241`, `:8249`, `:8277`, `:9195` |
| `telemetryMutex_` (mutable) | `AppH:161` | CPU sample, recording start time | `App:7765`, `:8312`, `:8324` |
| `mediaSpeedMutex_` (mutable) | `AppH:168` | speed-test state | `App:7753`, `:8960`, `:9001`, `:9076`, `:9102`, `:10609` |
| `waitMutex_` | `AppH:128` | wait loop and shutdown | `App:6908`, `:7023`, `:11019` |

Lock order seen: `hardwareInputSequenceMutex_` -> `hardwareActionMutex_` -> `commandMutex_` -> (camera `mutex_`, `eventMutex_`, `previewMutex_`, `mjpegMutex_`, `mediaSpeedMutex_`, `telemetryMutex_`). Nothing takes `commandMutex_` while holding one of the inner ones.

### 5.12 Member state in the header (`AppH:110-176`)

| Lines | Group | Pattern |
| --- | --- | --- |
| 110-124 | `options_`, `camera_`, `controlServer_`, `webServer_`, input and output classes, `soundRecorder_`, `std::atomic<bool> soundRecordingActive_{false}`, `soundRecordingFolder_` | owned by value, no pointers |
| 126-134 | `running_`, `shutdownRequested_`, `waitMutex_`, `waitCv_`, the three command-side mutexes, `lastUserActivityMs_`, `standbyUsbPoweredOff_` | atomics with `{init}` |
| 136-138 | event collection | mutex first, then plain members with `= value` |
| 140-147 | preview | mutex, cv, queues, `bool previewPublisherRunning_ = false;`, `std::thread previewThread_;` |
| 149-159 | MJPEG | same pattern, plus `std::atomic<uint32_t> mjpegClientCount_{0}` |
| 161-166 | telemetry | `mutable` because `buildWebStateJson() const` updates the CPU sample |
| 168-176 | media speed test | `mutable` mutex, plain state, thread last |

No comments in the header. Private methods are one unsorted block (`AppH:74-108`). Nested helper structs come before the methods (`AppH:50-72`). `friend struct HardwareInputTestAccess;` (`AppH:49`) names a type that is not in the published tree (**probable**: private tests exist; the same line is in `GpioInput.hpp:28`, `Pcf8574Input.hpp:27`, `NeoRotary4Input.hpp:35`).

### 5.13 What runs under the command lock, and what does not

| Under `commandMutex_` | Line |
| --- | --- |
| Field parsing, validation, the camera call (may reconfigure the sensor) | whole of `App:9091-10821` |
| UI.conf read-modify-write, lock wait up to 2 s, fsync | `App:1850-1935` |
| Shell commands through `popen`: standby helpers (`timeout 6s` / `8s`), `timedatectl`, format, mount, eject | `App:1541-1550`, `App:9153`, `App:10582`, `App:10540` |
| `calibrate_gyro` sampling (default 2.5 s), ALSA capability probe, audio device scan | `App:9709-9712`, `App:10039`, `App:10625` |
| A 220 ms sleep after `prepare_recording` before audio recording starts | `App:10692-10693`, `App:10705-10706` |
| Start and join of the preview and MJPEG threads in `wake` / `enter_standby` | `App:9149-9150`, `App:9188-9199` |
| Events the camera emits during the call (broadcast or collected) | `App:10823-10852` |
| The 1 Hz recording failure check | `App:7032-7033` |

| Outside `commandMutex_` | Line |
| --- | --- |
| Every HTTP route except `/api/command`, including `buildWebStateJson` (camera getters, UI.conf read, `lsblk`, ALSA scan, I2C power read) and media delete | `App:7093-7636` |
| Hardware action decisions: they read UI.conf and camera state, then dispatch; the command checks again under the lock | `App:8684-8685`, `App:8855-8859` |
| Preview publisher, MJPEG encoder and its client streams, speed-test worker, sound recorder level events | `App:10946`, `App:8194`, `App:8262`, `App:9012`, `App:8381-8384` |
| Event collection flag and reply assembly in `handleRequest` | `App:7061-7080` |
| The idle check's UI.conf read | `App:7037` |

---

## 6. Rough edges that are part of the Apertar way

A contribution that tidies these without being asked is a mismatch of its own kind.

| # | Rough edge | Line |
| --- | --- | --- |
| 1 | `ApertarCoreApp.cpp` is 11 025 lines; `handleCommand` is 1731 lines | `App:9091-10821` |
| 2 | Camera state is written out three times by hand; status keys twice | 5.5 |
| 3 | The web copy lacks the four top-level `photo_*` keys; number formats differ between copies | `App:7857-7897`, `App:178` vs `App:7865` |
| 4 | `help` lacks 12 commands | 5.6 |
| 5 | Booleans are parsed by hand at 10 sites; two sites are strict, eight are not | `App:9131`, `App:9486` |
| 6 | "Could not update shared UI settings." is typed 36 times | `App:9488` and on |
| 7 | 13 near-identical UI.conf value blocks and 8 IMU blocks are not factored | `App:9729-9888`, `App:9646-9704` |
| 8 | 51 `WebServer::Response response;` declarations, 44 content-type literals | `App:7093-7649` |
| 9 | One process-wide `collectingCommandEvents_` flag, set before the command lock is taken. Events off the always-broadcast list that a socket command causes (for example `recording`) reach only the requester (**confirmed**, `return` after `push_back`). With two socket requests in flight, events of one can land in the other's reply (**probable**: follows from the single flag, not run) | `App:7061-7065`, `App:10843-10848` |
| 10 | Two lower-case helpers in one file (`lowerAscii` `App:333`, `toLowerAsciiCopy` `App:5167`, forward-declared at `App:360`); two `escapeJson` (`CP:235`, `CC:95`; only the second escapes control characters) | - |
| 11 | Three free functions with external linkage between member definitions | `App:8410-8456` |
| 12 | `wake` starts the MJPEG thread whenever JPEG is built; `start()` starts it only when `webPort != 0` | `App:9193-9199` vs `App:6827-6836` |
| 13 | `(void)updateSharedUiGeneralSettings(...)` ignores one write result | `App:9433` |
| 14 | A failed hardware-input command is only logged | `App:8463-8464` |
| 15 | Spelling: "colour" and "color" both occur in operator sentences | `App:9373`, `App:9746` |
| 16 | No protocol or Core version in any state; CMake says `VERSION 0.1.0` for the 1.6.0 release | `CMakeLists.txt:3-4` |
| 17 | Two layout densities (**probable**: older and newer code): blank-line-separated blocks vs dense blocks with one-line `if (...) return ...;` | `App:9242-9476` vs `App:10031-10074` |
| 18 | Slow work (format, gyro calibration, shell helpers, a 220 ms sleep) holds the one command lock | 5.13 |
| 19 | `friend struct HardwareInputTestAccess;` without published tests; upstream Core has no test target | `AppH:49`; `CMakeLists.txt:69`, `:143`, `:152` |
| 20 | Older setters cast `*value` to `uint32_t` without a finite/range check in App | `App:9246`, `App:9303` |

---

## 7. Recipes

### C1-R1. Add a socket command the Apertar way

| # | Do | Anchor |
| --- | --- | --- |
| 1 | Name it: snake_case; `set_<thing>` for a value, `set_<thing>_enabled` for a boolean, `<noun>_<verb>` for an action. Remember that `set_` and `timelapse_` reset the idle timer | `App:9111-9114` |
| 2 | Insert one `    if (command.name == "<name>") { ... }` block next to its family in `handleCommand`, before the final unknown-command line. No new file, no CMake change | family table in 5.2; `App:10820` |
| 3 | Read fields with `command.number("value")` / `command.string("value")`; booleans as `command.string("enabled")` and `== "true" \|\| == "1"`; optional fields with `.value_or(default)`. Missing field: `"<name> requires <field>."` | `App:9243-9245`, `App:9482-9486`, `App:10580` |
| 4 | If it starts a capture, add its name to the three capture gates. If it changes media, add it to `mediaAction` | `App:9095-9097`, `App:9108-9110`, `App:9208-9211`, `App:9098-9099` |
| 5 | A guard for this command only goes on the first line of its block, with a "Stop ... before ..." sentence | `App:9706-9707` |
| 6 | Do the work through the owner: `camera_.x()` (error text: `camera_.lastError()`), `updateSharedUiGeneralSettings({...})`, or a free helper `bool f(..., std::string *errorMessage)` placed in the anonymous namespace above | `App:9246-9248`, `App:9810-9811`, `App:10589-10594` |
| 7 | Reply with `okReply(command.id, <fragment>)`: `settingsBody(camera_.settings())` when camera state may have changed, else `"\"snake_key\":<value>"` or a `"<thing>_<done>":true` flag. Refuse with `errorReply(command.id, "<Sentence>.")` | 5.3 |
| 8 | Append the name to the `help` literal | `App:9216` |
| 9 | Slow and not part of a take: follow the speed-test precedent (worker thread, own mutex group in the header, status command) | `App:8957-9089`, `AppH:168-176` |
| 10 | Clients: touch UI `Q_INVOKABLE` that calls `sendCoreCommand("<name>", {{"value", v}})`, and the reconfigure timeout list when the command restarts the camera; WebUI `sendCommand({cmd: "<name>", value})` plus a `case` in `applyCommandSnapshotPatch`; hardware action via the `dispatch` lambda | `CB:1108-1111`, `CB:1016-1028`, `WCP:9109`, `WCP:8678`, `App:8671-8677` |

### C1-R2. Add a persisted camera setting

Worked precedent: exposure compensation touches exactly these places (`grep -rnE 'exposureCompensation\b|exposure_compensation'`).

| # | Do | Anchor (precedent line) |
| --- | --- | --- |
| 1 | Member with default in `CaptureSettings`. An enum gets an `enum class` and an `inline const char *toString(...)` in the same header | `Types:124-162` (`:131`); `Types:254-337` |
| 2 | Range rule in `clampCaptureSettings` | `CC:534-601` (`:538-539`) |
| 3 | Load: `else if (key == "snake_key")` | `CC:650-720` (`:665-666`) |
| 4 | Save: `output << prefix << "snake_key=" << s.member << '\n';` | `CC:742-778` (`:752`) |
| 5 | Apply to libcamera (camera topic) | `CC:2005` (`:2041`) |
| 6 | Setter: declare in `CCH`; body = lock, validate with `setErrorLocked("<Sentence>.")`, copy `settings_` to `next`, set the member, `return applySettingsLocked(next, <needs reconfigure>);`. Refuse while recording when it shapes the stream or the file | `CCH:39-63` (`:45`); `CC:7835-7849`; `CC:7976-7979` |
| 7 | Decide the scope. Settings are stored per record-format profile. A value that must survive a format switch is carried over by hand | `CC:8725-8731`; `CC:7945-7951` |
| 8 | `settingsEvent`: one `<<` line | `CC:136-187` (`:149`) |
| 9 | `settingsBody`: the same line, same position | `App:167-216` (`:178`) |
| 10 | `buildWebStateJson`: the same line | `App:7857-7897` (`:7865`) |
| 11 | Command `set_<name>` among the camera setters, shape 5.1; add to `help` | `App:9242-9476` (`:9251-9258`); `App:9216` |
| 12 | Presets: writer `addString("camera<Name>", ...)` or `addNumberString(...)`; reader `if (const auto value = command.string("camera<Name>"))` with "Invalid preset <thing>."; the JS allow-list | `App:6663-6690` (`:6665`); `App:10270-10424` (`:10275-10280`); `WCP:10526+` |
| 13 | Hardware action, when buttons should reach it | `App:8687-8696` |
| 14 | Clients read it: touch UI `applyCoreState`; WebUI `mergeCameraStateFields` and the patch `case` | `CB:1261`; `WCP:8595`, `WCP:8678` |

### C1-R3. Add a `UI.conf` toggle

| # | Do | Anchor (zebra precedent) |
| --- | --- | --- |
| 1 | Member with default in `SharedUiSettingsSnapshot` | `App:1581-1639` (`:1586`) |
| 2 | Parse branch `else if (key == "<name>Enabled")` with `parseUiSettingsBool(value, snapshot.<name>Enabled)` | `App:1672-1809` (`:1679-1680`) |
| 3 | One line `if (const auto reply = handleUiToggle("set_<name>_enabled", "<name>Enabled")) return *reply;` beside the other toggles | `App:9493-9512` (`:9495-9496`) |
| 4 | Add `set_<name>_enabled` to `help` | `App:9216` |
| 5 | `"ui":{}` line `<< ",\"<name>_enabled\":" << (uiSettings.<name>Enabled ? "true" : "false")` | `App:7965-8021` (`:7970`) |
| 6 | Preset writer `addBoolFromMap("<name>Enabled", uiSnapshot.<name>Enabled);` and preset reader `!addBoolUpdate("<name>Enabled") \|\|` in the chain | `App:6578-6659` (`:6578`); `App:10431-10459` (`:10431`) |
| 7 | Hardware action (10 of 15 toggles have one): `if (action == "<name>") { toggleSharedUiBoolAction(action, "set_<name>_enabled", uiSettings.<name>Enabled); return; }` | `App:8908-8947` (`:8912-8915`) |
| 8 | Touch UI: `SettingsBridge` property with the byte-identical key, and its external-settings poll. WebUI: control, patch `case`, preset allow-list | `Apertar-UI/src/SettingsBridge.hpp:17`; `Apertar-UI/src/SettingsBridge.cpp:502`; `WCP:8678`, `WCP:10526+` |
| - | Nothing else: no event, no member in `ApertarCoreApp`, no cache, no take guard | C1-S08, C1-N12 |

### C1-R4. Add a field to the state

| Kind of field | Touch | Anchor |
| --- | --- | --- |
| Camera setting or camera capability | the three parallel serialisers, same position. A runtime-only value is a `CaptureSettings` member with a trailing `// Runtime ...` comment, filled in `CameraController::settings()` or `emitSettingsEventLocked()` | `App:167-216`, `CC:136-187`, `App:7857-7897`; `Types:132-150`; `CC:8566-8574`, `CC:8777-8784` |
| Capture status (recording, pending writes, an error text) | `get_state` and the top of `/api/state`, same key. If it changes outside a command, emit `{"event":"<name>",...}` through the camera callback, and add the name to the always-broadcast list when every client must see it | `App:9223-9237`, `App:7836-7856`; `App:10829-10838` |
| UI.conf value | `"ui":{}` only | `App:7965-8021` |
| System telemetry, device info | `"system":{}` or `"device":{}`; value from a `read*Snapshot()` free helper; optional numbers through `jsonNumberOrNull`; a probe that shells out caches itself (C1-I19) | `App:7901-7949`, `App:8029-8043`; `App:2266-2283` |

Rules for the line itself: snake_case key; `(x ? "true" : "false")`; `escapeJson(...)` around free text; `toString(enum)` for enums; a scalar unless it joins the short nested list in 5.5; no new group unless a new topic needs one.
Readers: touch UI `applyCoreState` (`CB:1261`, called for `settings` events and for every reply, `CB:1257-1258`); WebUI `mergeCameraStateFields` (`WCP:8595`) and `renderSnapshot` (`WCP:9327`).

---

## 8. Corrections to starting hints and to the KB map

| Source | Says | Code says |
| --- | --- | --- |
| BRIEF hint | "flat JSON, every value a scalar" | True for commands coming in. Replies, the `settings` event and `/api/state` carry a fixed short list of nested members (5.5) |
| `llm/core-map.md` 4.4 | camera settings JSON: "Same 42 keys today" in all three copies | `settingsBody` = `settingsEvent` (42 literal keys). The web copy has 38 of them; the four `photo_*` keys are under `"ui":{}` (`App:7994-7997`) |
| `llm/core-map.md` 2.2 and 5 | `POST /api/config` uses `extractJsonStringField(text)` | The body is the raw file text: `saveHardwareConfigFile(request.body, ...)` (`App:7178`), sent as `text/plain` (`WCP:10341-10345`). `extractJsonStringField` is used only for a preset's `name` (`App:5392`, `App:6480`) |

---

## 9. Side note for the relayed user request (GPIO chip definition)

Outside topic C1. Recorded here because the request that started this run asks to bring the chip definition back, and the upstream evidence is short.

| Fact | Line (`@upstream-1.6.0`) |
| --- | --- |
| Core's GPIO input accepts the chip as a config key with three spellings; default `auto` | `src/hardware/GpioInput.cpp:431-432` `} else if (key == "chip" \|\| key == "gpiochip" \|\| key == "gpio_chip") {`; `src/hardware/GpioInput.hpp:48` `std::string chipPath = "auto";` |
| An explicit chip is used as given; `auto` scans `/dev/gpiochip0` to `9` | `src/hardware/GpioInput.cpp:507-513` |
| The same key exists for the tally LED and the trigger output | `src/hardware/RecordingIndicatorOutput.cpp:319`, `:347`; `src/hardware/TriggerOutput.cpp:311` |
| Core's config template writes `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]`; its `[gpio]` block has no chip line | `App:4380`, `App:4394`; `App:4366-4369` |
| The UI's first-run template writes `chip=auto` in `[gpio_buttons]` and `[gpio_encoders]`, and `gpiochip=auto` in the two output sections | `Apertar-UI/src/DisplayConfigBridge.cpp:161`, `:172`, `:110`, `:123` |

So a selectable GPIO chip is original Apertar design. A control surface that keeps the chip field follows upstream.

---

## 10. Search log (how "always" was checked)

| Claim | Command (run in `/home/user/wt/core-upstream`) | Result |
| --- | --- | --- |
| One dispatcher | `grep -rlE 'command\.name ==' src include` | `src/ApertarCoreApp.cpp` only |
| No `else if` / `switch` dispatch | `grep -nE 'else if \(command\.name' src/ApertarCoreApp.cpp`; `awk 'NR>=9091 && NR<=10821' ... \| grep -nE '\bswitch\b'` | 0, 0 |
| One command lock | `grep -n commandMutex_ src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp` | 2 lock sites + declaration |
| Mutations only in `handleCommand` | `grep -nE 'camera_\.(set[A-Z]\|apply\|startRecording\|stopRecording\|capturePhoto\|startTimelapse\|stopTimelapse\|enterStandby\|wakeFromStandby\|start\(\|stop\(\))'` and `grep -n 'updateSharedUiGeneralSettings('`, split at lines 9091 and 10821 | outside: lifecycle lines only |
| Store ownership | `grep -rlE 'readSharedUiSettings\|UI\.conf\|sharedUiSettingsPath' src include`; `grep -rl 'camera_settings.conf' src include` | App only; CC only |
| No JSON library | `grep -rnE 'nlohmann\|rapidjson\|json\.hpp\|QJson\|jsoncpp\|simdjson\|boost/json' src include CMakeLists.txt` | 0 |
| No async primitives | `grep -rnE 'std::async\|std::jthread\|std::future\|packaged_task\|std::promise' src include` | 0 |
| No detached thread in App | `grep -n 'detach()' src/ApertarCoreApp.cpp` | 0 |
| Reply keys snake_case | keys in `App:9091-10821` filtered by `[A-Z]` | 0 |
| Error sentence style | 173 literals extracted from `errorReply(command.id, "...")` | 170 end with ".", 0 with "!", "?", "please", "error", "failed" |
| Serialiser key sets | keys of `App:167-216`, `CC:136-187`, `App:7835-7900` sorted and diffed | 42 = 42; web lacks four `photo_*` |
| Help coverage | names in `App:9216` vs handled names | 98 of 110 |
| Toggle coverage | per toggle (15 `handleUiToggle` lines): struct, parser, preset writer, preset reader, `"ui":{}`, help, hardware action | 15/15 for the first six, 10/15 for the last |
| Logging | `grep -c 'std::cerr' src/ApertarCoreApp.cpp`; `grep -rn 'std::endl' src include` | 14; 0 |
| Comments | `grep -cE '^\s*//' src/ApertarCoreApp.cpp`; `grep -rnE '///\|/\*\*' src include`; `grep -rnE 'TODO\|FIXME' src include` | 10; 0; 0 |
| No tests upstream | `find . -iname '*test*' -not -path './.git/*'`; `grep -nE 'add_test\|enable_testing' CMakeLists.txt` | none; none |

---

## Challenge

Challenger pass on 2026-11-17. Read only `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream` at `upstream-1.6.0`. Every line below is **confirmed** (read at the cited line) unless marked. `ACB` = `Apertar-UI/src/ApertarControlBridge.cpp`, `SB` = `Apertar-UI/src/SettingsBridge.cpp`.

### Verdict per rule

| Id | Verdict | Counter-example or check (path:line@upstream-1.6.0) |
| --- | --- | --- |
| C1-S01 | holds, rescoped | Inside Core it holds: `grep -nE 'camera_\.(set[A-Z]\|apply\|start\(\|stop\()'` outside `App:9091-10821` = lifecycle lines 6838, 6849, 6856, 6862, 6874, 6923 only; `updateSharedUiGeneralSettings(` outside = the definition only. But "every change of UI.conf" is false for the system: the touch UI writes `[General]` itself with `QSettings` (`SB:603` `m_settings.setValue("zebraEnabled", value);`). Rule now says "Core's own UI.conf writes". See new C1-S27 |
| C1-S02 | holds | `awk 9091-10821 \| grep command.name` filtered for the canonical form: only the gate lines (`App:9095-9117`), the brace-less `user_activity`/`ping`/`help` one-liners (`App:9118`, `:9212`, `:9214`), the toggle lambda (`App:9479`) and the final error remain. No `else if`, no `switch`, no command handled in `handleRequest` (`App:7055-7083` read) |
| C1-S03 | holds | `grep -n commandMutex_` = 2 lock sites |
| C1-S04 | holds (usually) | no new evidence |
| C1-S05 | holds | `grep -rlE 'command\.name ==' src include` = App only |
| C1-S06 | holds (usually), violation text wrong | In App the rule holds. Outside App the developer **does** put pure logic in a small header-only file with one includer: `src/camera/StillBracketing.hpp` (only `CC`), `src/camera/ScalerCropGeometry.hpp` (only `CC`), `src/camera/DefaultTuningSelection.hpp` (only `CC`), `src/hardware/PowerButtonGesture.hpp` (only `StandbyPowerButtonInput.cpp`), `src/util/AtomicStillFile.hpp` (only `CC`). "A helper header for one caller" is removed from the violation column |
| C1-S07 | holds, note added | Core side holds (`grep -rl`). System-wide, UI.conf has a second writer (the touch UI, `SB:603`, `ACB:633`, `ACB:982`) and preset files have a second writer (`SB:2205` `rootObject.insert("type", "apertar-preset")`). Cooperation is by the QLockFile lock (`App:1861`) and by Core touching only `[General]` |
| C1-S08 | holds | `AppH:110-176` read: no settings member |
| C1-S09 | holds | 8 POST branches read (`App:7175`, `:7392`, `:7440`, `:7477`, `:7503`, `:7575`, `:7637`); none sets camera state |
| C1-S10 | holds | `grep -noE 'request\.method == "[A-Z]+"'`: GET 11, POST 8, OPTIONS 1 |
| C1-S11 | holds | `App:8560-8605` (analog) and `App:8607-8628` (power button) read: all paths `dispatch(...)` or `dispatchHardwareInputCommand` |
| C1-S12 | holds (usually) | `grep -n controlServer_\.broadcast`: the three named direct sites plus preview (`App:10940-10942`) |
| C1-S13 | holds (usually), exceptions added | Key sets re-diffed: body 42, event 42 + `event`, web 38. Order is **not** identical: the event puts `recording_capabilities` first (`CC:140`, body has it 22nd); the web copy puts `timecode_mode` 14th (`App:7871`), the body 31st (`App:207`) |
| C1-S14 | weaken to usually | UI.conf values at the top level of `/api/state`, outside `"ui":{}`: `App:7838` `standby_timeout_seconds` (`uiSettings.standbyTimeoutSeconds`), `App:7839` `standby_usb_power_off`. Also the key `timecode_mode` appears twice in `/api/state` with different values: camera enum at top level (`App:7871`), UI.conf label inside `"ui":{}` (`App:7966`) |
| C1-S15 | holds, strengthened | All 5 `persistSettingsLocked()` calls are followed by `emitSettingsEventLocked()`: `CC:7646-7647`, `:8081-8083`, `:8108-8110`, `:8636-8637`, `:8719-8721` |
| C1-S16 | holds | one writer function |
| C1-S17 | holds | 5 `std::thread(&ApertarCoreApp::...)` sites; `detach()` only in `WS:287`, `CS:227` |
| C1-S18 | weaken to usually | `AppH:123-124` an atomic and a string (state, not components) sit in the component block; `AppH:158-159` `mjpegClientCount_`, `lastWebPreviewCaptureAt_` come after `mjpegThread_`; the telemetry group `AppH:161-166` has no thread |
| C1-S19 | holds, wording fixed | No other file names `ApertarCoreApp` except `src/main.cpp`. But not all callbacks go through the initialiser list: the socket and web handlers are passed to `start()` (`App:6859`, `App:6870`), the sound recorder's level callback to `soundRecorder_.start(...)` (`App:8378`) |
| C1-S20 | holds (once) | no second worker found (`grep std::thread`) |
| C1-S21 | holds (once) | - |
| C1-S22 | holds (once), wording fixed | Core is one of **two** preset writers. The touch UI writes presets itself (`SB:2205`) and applies one by sending `apply_preset` with only the `camera*`, `timecodeMode`, `photoBracketingEv` keys (`ACB:1152-1163`); it writes the UI.conf part itself. Core's one-transaction path is the WebUI path |
| C1-S23 | holds (once) | - |
| C1-S24 | holds for the command plane | Launch options: holds. "0 `APERTAR_*` reads in the command plane" holds. But the capture pipeline is configured by many `APERTAR_*` variables, see new C1-I22 |
| C1-S25 | holds (usually) | `App:6836-6905` re-read |
| C1-I01 | holds | - |
| C1-I02 | holds (usually) | - |
| C1-I03 | holds (usually), exceptions added | `grep -noE 'command\.(number\|string)\("[a-z_]+"\)'`: besides `kelvin`/`path`, also `width`/`height` (`set_h264_resolution`, `App:9412-9414`; `set_resolution`, `App:9315`), `x`/`y`, date parts `year`..`minute`, and booleans named `<thing>_enabled` (`gyro_enabled`, `audio_monitoring_enabled`, `audio_enabled`) |
| C1-I04 | holds (usually) | - |
| C1-I05 | holds | - |
| C1-I06 | holds | - |
| C1-I07 | weaken to usually | Literal sentences in `handleCommand` obey. Text that reaches the operator through `camera_.lastError()` or a helper's `errorMessage` does not always: `CC:8100` "Could not apply tuning file: ...; recovery failed: ..."; `App:1537` raw shell output or "Command failed."; `App:9070` "The write speed test failed." or raw `fio` output; `App:3262`, `:3304` "...writing it to the RTC failed." |
| C1-I08 | holds | `grep` for JSON libraries = 0 |
| C1-I09 | holds | - |
| C1-I10 | holds (usually) | Scope is App. Exceptions are common below App: `throw` in `CC` (13), `CdngEncoder.cpp` (30), `MlvEncoder.cpp` (20), `ColorProfileConfig.cpp` (16), `ProresIspProfile.cpp` (16); `CS:219` catches them per client |
| C1-I11 | holds (usually) | - |
| C1-I12 | holds (usually) | - |
| C1-I13 | weaken to usually, rescoped | "Success is silent" holds in App only. `src/main.cpp:122-139` prints start and stop banners with `std::cout`. `CameraController` logs on success, one `key=value` line per event: `CC:3353` "ApertarCore recording clip: ... workers= queue=", `CC:6264` "ApertarCore camera configured: sensor= stream=", `CC:3416` "recording stats:", `CC:5370` "tuning file:" (74 `std::cerr` in `CC`). Prefix "ApertarCore " dominates |
| C1-I14 | holds | `grep -cE '^\s*//'`: App 10 / 11 025, CC 78 / 8 834, GpioInput 0 / 746; 0 banners, 0 `///`, 0 TODO/FIXME |
| C1-I15 | holds (usually) | Brace init spacing also varies: `{ { "k", v } }` 48 vs `{{"k", v}}` 8 (newer standby code, `App:9125`, `:9134`). Newer header-only files use same-line bodies (`src/hardware/PowerButtonGesture.hpp:16`) |
| C1-I16 | holds | camelCase strings outside UI.conf/preset code are favourite ids (values, not keys), `App:730-760` |
| C1-I17 | holds (usually) | - |
| C1-I18 | holds (usually) | - |
| C1-I19 | holds (usually) | - |
| C1-I20 | holds | `grep -rnE '[^{]\\"event\\":' src` hits only the `find(...)` receivers |
| C1-I21 | holds (usually) | - |
| C1-N01 | weaken to usually | Camera and capture commands: equal on all surfaces. UI.conf values: not. The touch UI sends 29 distinct `set_*` names, all camera or capture (`grep -rhoE '"set_[a-z_]+"' src qml` in ui-upstream); it changes zebra, guides, audio, battery, favourites, standby by writing UI.conf itself (`SB:597-607`). Core's UI.conf commands serve the WebUI and hardware inputs. README:267 "shared UI settings and presets are managed by the Apertar application" |
| C1-N02 | holds | - |
| C1-N03 | holds | All 24 `CameraController::set*` bodies checked for a recording guard. Unguarded: ISO, ISO auto, shutter, shutter auto, EV, metering, WB, WB auto, timecode, 4 AF setters (exposure, colour, focus, timecode). Guarded: everything that shapes stream, format or file, incl. `setH264Resolution` |
| C1-N04 | holds | - |
| C1-N05 | holds | - |
| C1-N06 | holds, nuance added | `state_ = CameraState::Error` exists (`CC:7631`, `:8099`, `:8708`) but only when restoring the previous settings also fails (`CC:8693-8708`, `CC:8094-8101`) |
| C1-N07 | holds | camera settings only; UI.conf changes have no event (see C1-S26) |
| C1-N08 | holds | - |
| C1-N09 | holds | - |
| C1-N10 | holds | - |
| C1-N11 | holds | `grep version`: only preset `"version":1` (`App:6530`) and OS/kernel strings (`App:8032-8033`) |
| C1-N12 | holds | - |

### Missed rules

| Id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| C1-S26 | structure | The WebUI has no push channel. It polls `GET /api/state` once a second; events go to socket clients only | always (`grep -nE 'EventSource\|WebSocket\|text/event-stream\|Upgrade' src/web/*.cpp` = 0) | `WCP:11609` `window.setInterval(() => fetchState(true), 1000);`; `App:10851` `controlServer_.broadcast(eventJson);` |
| C1-S27 | structure | The touch UI writes UI.conf `[General]` itself and sends Core only camera and capture commands. Core's UI.conf commands exist so the WebUI and hardware inputs reach the same keys; both writers share the QLockFile lock | always (UI command names grepped; UI.conf write sites in UI read) | `SB:603`; `ACB:633` `m_settings.setValue("timecodeMode", displayValue)`; ui-upstream `grep '"set_'` = 29 camera/capture names; `App:1861`; README:267 |
| C1-S28 | structure | The touch UI caches camera values in UI.conf `camera/*` as display placeholders. Core never reads them; Core restores camera settings from `camera_settings.conf` | once | `ACB:886` "Cached values are placeholders only. Core owns restart/format restoration."; `ACB:982`; Core reads only `[General]` (`App:1641-1813`) |
| C1-S29 | structure | A helper program or file template Core needs is a raw string literal inside `ApertarCoreApp.cpp`, run with `python3 -c` or written out on demand. Core ships no helper script files besides the start script | usually | `App:3382` `R"PY(` NVMe remount watcher, run at `App:3595`; `App:4293` `R"CONFIG(` hardware config template; `scripts/` holds only `start-apertar-core.sh`. Exception: the privileged standby helpers are expected at `/usr/local/libexec/apertar-standby-*` and are not in the repo (`App:1544`, `:1549`) |
| C1-I22 | idiom | Engineering knobs of the capture pipeline are `APERTAR_*` environment variables read where they are used, not settings, not commands, not in README | usually | `CC:3343` `APERTAR_CDNG_WORKERS`; `CC:6321` `APERTAR_RAW_CACHED_DMABUF`; `src/prores/ProresRecorder.cpp:61`; `src/cdng/CdngEncoder.cpp:55`; `src/lossydng/LossyDngEncoder.cpp:325`; README has 0 of them. Exceptions: `APERTAR_HARDWARE_CONFIG` (a path, `App:4254`); start-script variables (`scripts/start-apertar-core.sh:4-6`) |
| C1-N13 | intent | System actions never prompt. Privileged work runs `sudo -n` (or `systemctl --no-ask-password`); a missing sudo rule becomes an operator sentence "<Action> needs sudo permission."; an optional OS helper is probed with `std::filesystem::exists` and skipped when absent | usually | `App:3170` "Changing the fan mode needs sudo permission."; `App:3698`; `App:3826`; `App:3205`; `App:9152` `std::filesystem::exists("/usr/local/libexec/apertar-standby-low-power")`; `App:6815`. Exception: raw shell output is passed through when a helper fails (`App:1537`) |

### Recipe corrections

| Recipe | Step | Correction |
| --- | --- | --- |
| C1-R1 | 10 | The touch UI gets a `Q_INVOKABLE` only for a camera or capture command. For a UI.conf value it does not send the command; it writes the key itself (C1-S27) |
| C1-R3 | 8 | The `SettingsBridge` setter writes the key with `m_settings.setValue(...)` and `sync()` (`SB:597-607`); no Core command is sent from the touch UI |
| C1-R2 | 9-10 | "Same position" is the intent; place the line next to its neighbour key in each copy, the copies already differ in order (C1-S13) |

---

## Final rules

Corrected rule list for topic C1, after the challenge. Line numbers `@upstream-1.6.0`. Short names as in the header table, plus `ACB`, `SB` from the Challenge section.

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C1-S01 | structure | Inside Core, every change of camera state and every Core write of UI.conf enters through `ApertarCoreApp::handleCommand`; socket, `POST /api/command`, hardware inputs and the idle timer all call it. Only `start()` applies the UI.conf still-mode values once | always | `App:7067`; `App:7090`; `App:8462`; `App:7049`; `App:6845-6857`; README:271 | An HTTP route, hardware callback or worker that calls `camera_.setX()` or writes UI.conf |
| C1-S02 | structure | The dispatcher is one flat chain of `if (command.name == "...") { ... return ...; }` blocks ending in `errorReply(..., "Unknown command: " + command.name)` | always | `App:9242`; `App:10815`; `App:10820` | A handler map, a `switch`, a class per command, a second dispatcher |
| C1-S03 | structure | One lock, `commandMutex_`, taken on the first line of `handleCommand`, serialises all commands | always | `App:9093`; `App:7032` | A per-feature command mutex |
| C1-S04 | structure | Multi-command guards sit at the top of `handleCommand` as `\|\|` lists with their own sentence; a one-command guard opens that command's block | usually | `App:9095-9117`; `App:9208-9211`; `App:9706`; camera-side guards in `CC:7714-7717` | A new capture command missing from the gates |
| C1-S05 | structure | The command plane is `src/ApertarCoreApp.{cpp,hpp}`; `src/ipc/` holds only the parser and socket server | always | `CMakeLists.txt:69-96`; `src/ipc/` 4 files | `src/commands/`, command code in `ControlServer` |
| C1-S06 | structure | In App, helpers are free functions in the anonymous namespace above the members; members only when they need `this`. Pure subsystem logic may live in a small header-only file next to its owner | usually | `App:57-58`, `App:6779`; `src/camera/StillBracketing.hpp`, `src/hardware/PowerButtonGesture.hpp`. Exception: `App:8410`, `:8434`, `:8442` | Private static helpers or a `*Utils` class in App |
| C1-S07 | structure | Each store has one owner inside Core: `camera_settings.conf` = `CameraController`; UI.conf = App; a single `apertar-hardware.conf` key = the class that parses that section. UI.conf and preset files also have the touch UI as writer | always | `CC:342-353`; `App:341-348`; `App:9652`; `SB:603`; `SB:2205`; whole-file editor `App:7175-7178` | `CameraController` reading UI.conf; App writing `camera_settings.conf` |
| C1-S08 | structure | App keeps no copy of settings: `camera_.settings()` and `readSharedUiSettings()` each time | always | `App:7715`; `App:7728`; `App:7037`; `AppH:110-176` | A `uiSettings_` member, a cache, a file watcher in Core |
| C1-S09 | structure | The WebUI changes camera/UI state only through `POST /api/command`; other routes serve the page, icons, MJPEG, state and file work | always | `App:7637-7641`; `WCP:9123` | `POST /api/iso`, a route calling `camera_.setX` |
| C1-S10 | structure | One router `handleWebRequest`: flat `if (request.method == ... && request.path == ...)`; prefixes with `rfind(...,0)==0`; GET/POST/OPTIONS only; 404/405 at the end | always | `App:7154`; `App:7124`; `App:7644-7647` | A route table, `PUT`/`DELETE`, routes from other files |
| C1-S11 | structure | A hardware input never touches the camera; it builds a `ControlCommand` via `dispatch`/`dispatchHardwareInputCommand`; UI-only actions are `hardware_action` events | always | `App:8505`; `App:8858`; `App:8909`; `App:8950`; `run_script` `App:8662-8664` | A GPIO callback calling `camera_.startRecording()` |
| C1-S12 | structure | Events are JSON strings built at the emit site and passed to `publishEvent` (trigger outputs first, then broadcast or append to the socket reply) | usually | `App:10823-10852`; `App:6784`. Exceptions `App:10692`, `:10705`, `:10730-10732` | An event class hierarchy, a subscriber list |
| C1-S13 | structure | Camera state is serialised by three hand-written copies (`settingsBody`, `settingsEvent`, inline web block); a new field goes into all three, next to the same neighbour | usually | `App:167-216`; `CC:136-187`; `App:7857-7897`. Exceptions: web lacks four `photo_*` keys (`App:7994-7997`); order differs (`CC:140`, `App:7871` vs `App:207`) | One shared serialiser; a field in the reply but not in the event |
| C1-S14 | structure | Socket `get_state` = status keys + `settingsBody`; `/api/state` = the same + groups `system`, `capture`, `ui`, `audio`, `imu`, `device`; UI.conf values go in `"ui":{}` | usually | `App:9238`; `App:7965`. Exceptions: `App:7838-7839` standby keys at top level; `timecode_mode` twice (`App:7871`, `App:7966`) | UI.conf values in `get_state` or the `settings` event |
| C1-S15 | structure | Camera settings persist on every commit: setter -> `applySettingsLocked` -> `persistSettingsLocked` (25 ms debounce, whole file, atomic) -> `emitSettingsEventLocked`. Persist is always followed by the event | always | `CC:8719-8721`; `CC:853`; `CC:789`; pairs at `CC:7646-7647`, `:8081-8083`, `:8108-8110`, `:8636-8637` | A setting saved from App, a second settings file, a persist without event |
| C1-S16 | structure | Core's UI.conf write is a synchronous read-modify-write of `[General]` under a QLockFile-compatible lock, then an atomic rename; other sections and keys kept | always | `App:1850-1935`; `App:1861`; `App:1934`; `SF:58` | `std::ofstream` onto UI.conf; linking Qt into Core |
| C1-S17 | structure | App owns its threads as `std::thread` members; start sets the flag under the group mutex then `std::thread(&ApertarCoreApp::runX, this)`; stop clears, notifies, joins | always | `App:6825`, `:6834`, `:9008`, `:9192`, `:9198`; `App:10988-11014`. Detached per-client threads only in `CS:227`, `WS:287` | `std::async`, `std::jthread`, a detached thread in App |
| C1-S18 | structure | Header members: owned components by value first, then state groups split by blank lines, mutex first, thread usually last; cross-thread flags are `std::atomic<T> name_{init};` | usually | `AppH:110-124`; `AppH:140-147`; `AppH:168-176`. Exceptions `AppH:123-124`, `:158-159`, `:161-166` | `std::unique_ptr` parts in App, an Impl struct |
| C1-S19 | structure | Parts talk to App only through `std::function` callbacks (constructor initialiser list for camera and inputs, `start(handler)` for servers and sound recorder); no part holds an App pointer | always | `App:6783-6792`; `App:6859`; `App:6870`; `App:8378`; only `src/main.cpp` names `ApertarCoreApp` | An observer interface, a singleton App pointer |
| C1-S20 | structure | A slow job that must not hold the command lock becomes a worker thread with its own state group; the command starts it, clients poll | once | `App:8957-9089`; `App:10608-10621`; `App:7745-7761` | A job queue, a future returned to the client |
| C1-S21 | structure | Periodic supervision lives in the 1 Hz loop of `wait()`; no timer thread | once | `App:7021-7053` | A sleeping poll thread |
| C1-S22 | structure | A preset is applied with one flat `apply_preset` command with camelCase keys (`camera<Name>` for camera values) and one `applyCapturePreset` transaction. Preset files have two writers: Core (`buildCurrentPresetPayload`) and the touch UI; the touch UI sends only the camera keys and writes UI.conf itself | once | `App:6522-6697`; `App:10230-10527`; `App:10519-10522`; `SB:2205`; `ACB:1152-1163` | A preset applied as a list of `set_*` commands; a nested object in the command |
| C1-S23 | structure | Favourites are an ordered id list; Core keeps the allowed ids in `favoriteCandidateOrder()` and drops unknown ids | once | `App:727-763`; `App:10224`; `App:1808` | A second favourites store |
| C1-S24 | structure | A launch option is an `Options` member, a hand-written `if (arg == "--x")` in `main`, a usage line and a README row; the command plane reads no `APERTAR_*` switch | always | `AppH:32-38`; `src/main.cpp:52-82`; `src/main.cpp:32-37`; README:252-257 | `getopt`, an env switch inside `handleCommand` |
| C1-S25 | structure | `start()` brings parts up in fixed order and unwinds by hand on a required failure; optional hardware logs "... disabled: <reason>" and start continues; `stop()` reverses | usually | `App:6838-6843`; `App:6859-6878`; `App:6881-6897`; `App:6913-6929`. Exception: input `start()` results ignored `App:6886-6891` | Core start aborting for a missing accessory |
| C1-S26 | structure | The WebUI has no push channel; it polls `GET /api/state` at 1 Hz; events reach socket clients only | always | `WCP:11609`; `App:10851`; 0 `EventSource`/`WebSocket` in `src/web` | An SSE or websocket endpoint |
| C1-S27 | structure | The touch UI writes UI.conf `[General]` itself and sends Core only camera and capture commands; Core's UI.conf commands serve WebUI and hardware inputs | always | `SB:597-607`; `ACB:633`; 29 `set_*` names in ui-upstream, all camera/capture; README:267 | The touch UI routing a monitoring aid through Core; a UI.conf key Core writes that the UI does not read |
| C1-S28 | structure | The touch UI caches camera values in UI.conf `camera/*` as display placeholders; Core never reads them | once | `ACB:886`; `ACB:982`; `App:1641-1813` | Core restoring camera settings from UI.conf |
| C1-S29 | structure | A helper program or file template Core needs is a raw string literal in App, run with `python3 -c` or written on demand; no helper script files ship with Core | usually | `App:3382`; `App:3595`; `App:4293`; `scripts/` = start script only. Exception: `/usr/local/libexec/apertar-standby-*` not in repo (`App:1544`, `:1549`) | A new `scripts/helpers/` tree installed beside Core |
| C1-I01 | idiom | Camera setter command: read field, one presence check, `camera_.setX(...)`, reply `settingsBody` or `camera_.lastError()` | always | `App:9242-9249`; `App:9275-9282`; `App:9439-9446` | Range checks in App duplicating the setter |
| C1-I02 | idiom | UI.conf value command: read `value`, normalise, refuse if trimmed input differs, write one pair, echo `"snake_key":value` | usually | `App:9802-9813`; `App:9739-9750`. Exceptions `App:10003`, `:10025`, `:10129` | Raw client string written to UI.conf |
| C1-I03 | idiom | The single argument is `value`; a lone boolean is `enabled`; other fields snake_case | usually | `App:9243`; `App:9482`; exceptions `kelvin`, `path`, `width`/`height`, `x`/`y`, date parts, `gyro_enabled`, camelCase in `apply_preset` | camelCase fields in an ordinary command |
| C1-I04 | idiom | Command names snake_case; `set_<thing>`, `set_<thing>_enabled`, auto variants as own commands; actions `<noun>_<verb>`/`<verb>_<noun>`; `set_` and `timelapse_` reset the idle timer | usually | `App:9269`; `App:9493`; `App:10623`; `App:9112-9114`. Exception `set_standby_usb_power_off` | `setIso`, `toggle_x` |
| C1-I05 | idiom | Booleans arrive as strings, tested `== "true" \|\| == "1"`; no boolean accessor | always | `App:9486`; `App:9518`; `App:10630` | `command.boolean()` |
| C1-I06 | idiom | Replies only from `okReply(id, fragment)` / `errorReply(id, sentence)` | always | `App:108-128`; `App:9213` | A hand-built reply |
| C1-I07 | idiom | Error literals in Core are one operator sentence: capital, full stop, no "!", "please", "error", "failed"; they say what is wrong or what to do | usually | `App:9097`; `App:9211`; `CC:7715`. Exceptions passed through: `CC:8100`, `App:1537`, `App:9070`, `App:3262` | Error codes, "Error: ...", developer detail in a literal |
| C1-I08 | idiom | JSON is written by hand with `std::ostringstream`; `(x ? "true" : "false")`, `escapeJson`, `jsonNumber`; no JSON library | always | `App:9222-9238`; `App:167-215`; grep = 0 | A JSON dependency, `std::boolalpha` |
| C1-I09 | idiom | A command is one line with one flat object; values are text; lists travel as one string | always | `CP:204`; `CP:124`; `App:771-792`; `WCP:10504-10514` | Nested objects or arrays in a command |
| C1-I10 | idiom | In App a fallible helper returns `bool` and writes `std::string *errorMessage`; parsers return `std::optional`; no exception crosses `handleCommand` | usually | `App:3127`; `App:8957`; `App:892`. Exception `App:1448` caught `App:8369-8375`; encoders below App throw | Exceptions for control flow in App, `std::expected` |
| C1-I11 | idiom | A label set gets `normalize<Name>Value()` returning the canonical or default label, shared by UI.conf read and command | usually | `App:669-677`; `App:1701`; `App:9807`. Exception `App:824-844` | Enum + string table for a UI.conf label |
| C1-I12 | idiom | UI numeric values are clamped silently and echoed; camera values range-checked in the `CameraController` setter | usually | `App:9733`; `App:10108`; `CC:7777-7780`. Newer commands check in App (`App:9122`) | Out-of-range volume answered with an error |
| C1-I13 | idiom | Logging is `std::cerr` with a fixed prefix ("ApertarCore ..."), detail, `'\n'`; no levels, no `std::endl`. App logs failures and ignored input only; the capture pipeline logs one `key=value` line per clip or configuration; `main` prints start/stop with `std::cout` | usually | `App:1863`; `App:8954`; `CC:3353`; `CC:6264`; `src/main.cpp:122`, `:139` | A logging class, a log line per command, `std::endl` |
| C1-I14 | idiom | Comments are rare sentences stating a hazard or reason; no doc comments, banners, TODO | always | `App:10827-10828`; `App:8103-8104`; `App:1543`; 0 `///`, 0 TODO in `src` | Comments restating code, ticket numbers |
| C1-I15 | idiom | 4 spaces; function brace on own line; one-statement `if` body on next line without braces; blank line between command blocks; `const auto` locals; no `.clang-format` | usually | `App:9242-9249`; `App:9802-9813`. Exceptions: dense blocks `App:9118-9211`; `{{` spacing at `App:9125` | Reformatting untouched code |
| C1-I16 | idiom | Types PascalCase, functions camelCase, members `name_`, constants `kName`; wire JSON and `camera_settings.conf` snake_case; UI.conf and preset keys camelCase; `*Snapshot`, `*Body`, `json*` | always | `App:1581`; `App:60`; `AppH:132`; `App:9487`; `App:7967` | camelCase in a reply, snake_case in UI.conf |
| C1-I17 | idiom | A shape repeated inside one function becomes a local lambda before first use | usually | `App:9478`; `App:10232`; `App:8671`; `App:6541`. Unfactored: `App:9729-9888`, `App:9646-9704` | A template or macro for command blocks |
| C1-I18 | idiom | A command changing camera and UI.conf keeps both in step (commit callback or restore on failure) | usually | `App:9594-9609`; `App:10519-10522`; `CC:8634-8656`. Exceptions `App:9433`, `App:9527-9534` | Camera changed, UI.conf write failed, reply ok |
| C1-I19 | idiom | A shell probe used by the 1 Hz poll caches itself with a function-local static mutex and a short lifetime | usually | `App:2266-2283`; `App:2786-2800`. Exception `App:7735-7743` | A member cache, a background poller |
| C1-I20 | idiom | An event is a literal `{"event":"<name>",...}`, `event` first, no spaces; receivers match with `find` | always | `App:6901`; `CC:139`; `App:10829-10862` | Other key order, parsed routing |
| C1-I21 | idiom | `std::lock_guard<std::mutex> lock(m);` in the smallest scope; worker loops unlock around I/O | usually | `App:10971-10974`; `App:8214-8223`. CTAD at `App:7032`, `:9102`, `:10609` | A lock held across a socket send |
| C1-I22 | idiom | Capture-pipeline engineering knobs are `APERTAR_*` environment variables read at the point of use; not settings, not commands, not in README | usually | `CC:3343`; `CC:6321`; `src/prores/ProresRecorder.cpp:61`; `src/cdng/CdngEncoder.cpp:55`. Exceptions `App:4254`; `scripts/start-apertar-core.sh:4-6` | A tuning knob added as a camera setting or a socket command |
| C1-N01 | intent | Core is the source of truth for camera and capture state; all three surfaces use the same camera/capture commands and busy checks. UI.conf values are reached by command from WebUI and hardware, and written directly by the touch UI | usually | README:271; README:267; `App:7090`; `App:8462`; `SB:603` | Camera logic in a route or in JS |
| C1-N02 | intent | A refusal is an operator sentence shown as written (touch UI last error, WebUI toast) | always | `CB:1084-1086`; `WCP:9128-9132` | A reply the UI must translate; a silent no-op |
| C1-N03 | intent | During a take nothing that shapes the stream, file format or media may change; exposure, white balance, focus and timecode stay adjustable | always | `CC:7715`, `:7745`, `:7928`, `:7977`, `:8118`, `:8052`, `:8608`, `setH264Resolution`; `App:9105-9107`; `App:9706-9707`; unguarded `CC:7774-7849`, `:7888-7916`, `:8176-8217` | A stream-shaping setter without a `recording_` check |
| C1-N04 | intent | No new capture starts while the last one is still writing or a speed test runs | always | `App:9095-9097`; `App:9108-9110`; `CC:8243-8245`; README:102 | A capture command missing from the gates |
| C1-N05 | intent | Failures are reported: recording failure checked before every command and once a second; state carries the error text and dropped-frame flag | always | `App:9094`; `App:7033`; `App:9226-9227`; `App:9234` | A recording error only in the log |
| C1-N06 | intent | A failed change leaves the camera in its last working state; the Error state is used only when restoring the previous settings also fails | always | `CC:8693-8708`; `CC:8094-8101`; `CC:8248-8253`; `App:9200-9204` | `state_ = Error` after a refused setting |
| C1-N07 | intent | Camera settings outlive a restart and every socket client sees a change at once via the always-broadcast `settings` event | always | `CC:8719-8721`; `App:10827-10840`; README:18 | A setting change without a `settings` event |
| C1-N08 | intent | In Standby any input only wakes; capture is refused with a sentence; operator activity resets the idle timer | always | `App:8642-8649`; `App:9208-9211`; `App:9111-9117` | A button recording straight out of Standby |
| C1-N09 | intent | The frame path never waits: non-blocking sends, stalled clients dropped, newest preview frame only, no call back into the controller from libcamera's thread | always | `CS:24-25`; `App:6977-6987`; `App:8103-8104` | A blocking write in a preview callback |
| C1-N10 | intent | The WebUI is for a trusted LAN: origin check, fixed helper command lines, path checks, no accounts | always | `WS:156-170`; `App:1543`; `App:7126-7129`; `App:5157-5165` | Shell commands built from request text |
| C1-N11 | intent | Core and UI ship together; no protocol version; missing fields default, unknown keys ignored | always | README:306; `CC:721-723`; `App:10820`; only `App:6530` carries a version | Version handshakes |
| C1-N12 | intent | Monitoring aids and UI preferences are UI state in UI.conf, may change during a take, never written into footage | always | `App:9478-9491`; `App:1581-1639`; README:155 | A zebra or LUT flag in `CaptureSettings` |
| C1-N13 | intent | System actions never prompt: `sudo -n` / `--no-ask-password`; a missing rule becomes "<Action> needs sudo permission."; optional OS helpers are probed with `std::filesystem::exists` and skipped | usually | `App:3170`; `App:3698`; `App:3826`; `App:3205`; `App:9152`; `App:6815`. Exception `App:1537` | An interactive `sudo`, a hard failure when an optional helper is missing |

Recipes C1-R1 to C1-R4 stand as written in section 7, with the three corrections in the Challenge section.
