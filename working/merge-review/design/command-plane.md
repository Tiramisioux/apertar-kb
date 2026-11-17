# The command plane: one dispatcher, one reply shape: final plan

Read at Core `/home/user/wt/core-work` `0d13a6f`, UI `/home/user/wt/ui-work` `ac1fc28`. Measured against Core `/home/user/wt/core-upstream` and UI `/home/user/wt/ui-upstream` at `upstream-1.6.0`. All port line numbers are at these heads. `0d13a6f` is two commits after `d1dcdee`. Those two commits touch `CC`, `WCP`, `Types.hpp` and `README.md` and move no `App` line cited here. Every `App` line below was re-read at `0d13a6f`.

This page is the design after the challenge. Commit numbers are the final ones. The table "What the challenge changed" at the end maps the old numbers to the new ones.

## In short

1. Today, five hardware commands are answered by a second dispatcher, `handleReadOnlyHardwareCommand`, before `handleCommand` takes `commandMutex_`. Two of them (`get_controls`, `controls_history`) only read the hardware file, and `GET /api/config` already serves that file.
2. A third reply builder, `errorReplyBody`, puts machine codes (`"code":"stale"`, `old_page`, `confirm_display`, ...) and arrays into `ok:false` replies, in 14 places. The WebUI branches on those codes in 4 places.
3. Smaller drift: the playback routes build their error JSON by hand. The pre-roll switch sends `value=on|off`. Six new touch-UI invokables return `void`. Boot Config and `set_controls` flags accept `on/yes`. Port switches are written `true/false` in `camera_settings.conf`. The touch UI repeats Core's file-timecode change by guessing it.
4. Which commands must not wait for the lock: none of the reads. Upstream serves a read that must not wait as an HTTP GET route on the web server's per-connection thread, with no `commandMutex_` (`WS:276-287`, `App:7168-7173` @upstream-1.6.0). The hardware-file reads become `GET /api/config` and `GET /api/config/history`. `controls_last_input`, `scan_i2c` and `list_actions` become ordinary blocks under the lock. Two things stay before the lock. `test_input` stays because it re-enters `handleCommand` (deadlock otherwise). `abortSafetyStopFlushForRecord` stays as it is, because it is safety-stop work, not this theme.
5. Every refusal is `errorReply(id, sentence)`. `errorReplyBody` is deleted. A stale save is refused with a sentence. A save that names no revision is saved, as in 1.6.0.
6. Booleans: `enabled=` for the pre-roll switch, the strict `true/false/1/0` test wherever a wrong value would write a file, `bool` invokables, `0/1` in the settings file.
7. 16 commits (12 Core, 4 UI), plus 2 optional ones for the owner (1 Core, 1 UI). Estimated net: Core and WebUI about -239 / +167 lines, UI about -24 / +24.

## How it works in the port today

The command plane is the path a request takes to change or read camera state. Upstream has one door, `handleCommand`, under one mutex. The port has these pieces:

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `handleCommand` entry, `App:12576` | socket `App:8092`, `POST /api/command` `App:9218`, hardware inputs `dispatchHardwareInputCommand` `App:10121`, idle timer `wait()` `App:8289` | - | caller's thread. `commandMutex_` is taken at `App:12588`, after three pre-lock steps at `App:12578-12587` | - | - |
| `get_controls`, `App:12430-12474` | writes `controlsErrors_`/`controlsWarnings_` (`App:12434-12436`). Through `controlsApplyJson` `App:12359-12385` it runs `systemctl show` once per pending unit and erases `pendingUnitSince_`. Parses the file 8 times (`App:12447-12461`) | WCP `loadControls` `:18325-18380`, `controlsRecheckSoon` `:18586-18598` | socket or web thread, **no `commandMutex_`**. Atomics plus `controlsWorkerMutex_` | reads `~/apertar-hardware.conf` through `HardwareConfigStore` | WebUI Settings > Controls and Hardware cards |
| `controls_history`, `App:12475-12491` | `HardwareConfigStore` writes history files on each save | WCP `:18627`, `:18654` (Undo), `:18966` (Config history) | no `commandMutex_` | hardware-history directory | Config history list, Undo |
| `controls_last_input`, `App:12493-12501` | `noteInputSeen` from the input threads, under `lastInputMutex_` | WCP Listen loop, a `setInterval` of 300 ms that does not wait for its reply (`:18695-18720`) | `lastInputMutex_` only | none | Controls "Listen" |
| `scan_i2c`, `App:12503-12549` | - | WCP Hardware card `:18256` | no `commandMutex_`. Checks `recordingGateActive()` once, then makes up to 117 one-byte reads (`I2cProbe.cpp:13-37`) | none | Hardware card bus scan |
| `list_actions`, `App:12551-12572` | static catalog `ActionCatalog.hpp:336-358` + `camera_.settings()` + UI.conf | WCP `:18335`, cached once. Only `actions` is read (`:16751`, `:16823`, `:16877`, `:18056`, `:18505`) | no `commandMutex_` | reads UI.conf | Controls action pickers |
| `test_input`, `App:12582` -> `testInputReply` `App:12399-12424` | - | WCP Try / Remote controls `:16920` | before the lock. It calls `handleHardwareInputAction`, which takes `hardwareActionMutex_` then `commandMutex_` (`App:10121-10126`) | reads hardware file | Try buttons |
| `abortSafetyStopFlushForRecord`, `App:12587`, `App:10123` | - | - | lock-free, before both mutexes | - | - |
| Controls worker `runControlsWorker`, `App:12250-12273` | wakes on a save or every 2 s, compares the file with the applied text, applies outside it during no take | - | own thread, `controlsWorkerMutex_` | - | "applied / waiting for the take" |
| `GET /api/config`, `App:8617`, builder `buildHardwareConfigFileJson` `App:6185-6233` (free function) | - | WCP `fetchConfigFile` `:18803` | web thread, no `commandMutex_` | hardware file | Config text editor |
| `POST /api/config`, `App:8624-8684` | WCP save `:18986-19024`, header `X-Apertar-Revision` | - | web thread, store mutex | hardware file, `.bak`, history | 409 with `code` `old_page`/`stale`/`conflict`/`merge_review` |
| Config "Check", WCP `checkConfigFile` `:18864-18880` | sends `set_controls ... dry_run=true` with `base: state.configRevision \|\| "h"` | reads `issues` also from `ok:false` replies | `commandMutex_` | - | Config issue list |
| `errorReplyBody`, `App:173-184` (anonymous namespace, `App:82`) | Boot Config `App:3780-3835` (`invalid`, `unreadable`, `old_page`, `stale`, `refused`, `confirm_display`, `permission`, `write_failed`). `/api/config` `App:8640`, `:8657`. `set_controls` `:12818`. `set_buffer_mode` `:12858`. `set_frames_per_folder`/`set_clip_merge` `:12898`. `set_storage_preroll` `:12932` | WCP branches on `code` at `:18303`, `:18732`, `:19019`, `:20400`. `issues`/`new_errors` read at `:18302`, `:18731`, `:18869`, `:19018`. `conflicts` read nowhere | - | - | toasts and card messages |
| Store refusal codes, `HardwareConfigStore.hpp:25-38`, `.cpp:250-368` | the store. A dry run with new errors is refused like a save (`.cpp:336-341`) | App maps them to HTTP status (`App:8648-8651`) and sends them on the wire | store mutex + `QtIniLock` | - | - |
| Playback error bodies, `App:8503`, `:8510`, `:8533`, `:8536`, `:8573`, `:8691`, `:8820` | hand-built `"{\"ok\":false,...}"`, with `hold`, `gone`, or `busy` and no sentence. Sentences carry tokens ("Playback held: media_test.") | WCP `pbvFetchFrame` reads only status 409/503/404 and `body.gone` (`:12355-12361`); the viewer maps the hold token itself (`pbvHoldText` `:12156`) | web threads | - | playback viewer |
| `set_boot_config` guard, `bootConfigSet` `App:3775` | `POST /api/boot-config` passes the header and `browser = Origin present` (`App:9194-9197`). The socket command passes `false` (`App:14605-14606`) | - | `bootConfigMutex()` | `/boot/firmware/config.txt` | Boot Config card |
| Boot Config booleans, `boolFieldValue` `App:3709-3718` | WCP `bootConfigRequestBody` (JSON booleans) | `bootConfigRequestFrom` `App:3746`; `dry_run`/`confirm_display` `App:3781-3782` with `.value_or(false)`, so a misspelt `dry_run` writes | - | - | - |
| `set_controls` flags, `App:12786-12812` | WCP sends `"true"` | `restore`, `dry_run`, `force`, `confirm_merge` through `parseBooleanToken` (`App:3319-3335`: any case, `yes/no`) | `commandMutex_` | - | - |
| `set_storage_preroll value=on\|off`, `App:12917-12944` | WCP `:15843`, patch `:14030`. UI `ACB:623-630` | buffer state `storage_preroll_auto` | `commandMutex_` | `[media] preroll=` in the hardware file | WebUI Media card, touch UI Media |
| `set_cdng_log value=auto\|off`, `App:13095` | WCP `:15451`. UI `ACB:716-727` | state `cdng_log` (string) | `commandMutex_` | `camera_settings.conf cdng_log=` | Record settings |
| Port switches in `camera_settings.conf`, writer `CC:963`, `:974-979` | `CameraController` persist | reader `CC:869-896` (accepts `true` or `1`) | CC mutex | `camera_settings.conf` (`true`/`false`) | - |
| Touch UI invokables `UI hpp:194-200`, `ACB:618-630`, `:686-701`, `:716-727` | QML `SettingsPage.qml:3439`, `:3447`, `:3480`, `:5605`, `:5628`, `:5635`, `ClipNameCard.qml:169`, `:335` | - | GUI thread, blocking send | - | `lastError` only |
| Command replies in the touch UI | `sendCoreCommand` passes every line it reads, the reply included, to `applyCoreMessage` (`ACB:1210`), which sends every `ok` message and every `settings` event to `applyCoreState` (`ACB:1411-1412`) | `applyCoreState` sets `m_isoAuto` (`ACB:1505-1506`) and `m_fileTimecodeMode` (`ACB:1698-1707`) | GUI thread | - | camera page, Record page |
| File timecode guess, `ACB:766-769` | `applyTimecodeMode` sets `m_fileTimecodeMode` from `target` after the reply was already applied | - | GUI thread | UI.conf `timecodeMode` | Record page |
| Live-value poll, `ACB:16-20`, `:1015-1016` | - | `get_state` every 1 s while auto ISO or auto WB is on (30 s otherwise) | each poll takes `commandMutex_`. The HDMI process doubles the rate | - | ISO/WB in use on screen |
| `set_value_steps` reply, `App:14178` | - | WCP `:8494` does not read the reply | `commandMutex_` | UI.conf | - |

Why `get_controls` was put before the lock (comment `App:12578`): "so a slow one never holds up a button". It is not read-only. It spawns `systemctl` and writes counters.

Why `test_input` must stay before the lock (confirmed): `testInputReply` -> `handleHardwareInputAction` -> `dispatchHardwareInputCommand` (`App:10121-10126`) -> `handleCommand` -> `commandMutex_`. A `std::mutex` is not re-entrant, so running `test_input` under the lock would deadlock.

The hardware file has one path (confirmed): `HardwareConfigStore::defaultPath()` (`HardwareConfigStore.cpp:118-123`) and `editableHardwareConfigPath()` (`App:4944-4949`) both return `$APERTAR_HARDWARE_CONFIG`, else `/home/pi/apertar-hardware.conf`.

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent |
| --- | --- |
| One command door | `handleCommand` takes `commandMutex_` on its first line (`App:9091-9093`). It is one flat `if (command.name == ...)` chain ending in "Unknown command" (`App:10820`). Socket `handleRequest`, `handleWebCommand` (`App:7085-7091`), hardware inputs (`App:8458-8466`) and the idle timer all enter it. |
| An entry that calls `handleCommand` from outside | `dispatchHardwareInputCommand` takes `hardwareActionMutex_`, then calls `handleCommand` (`App:8458-8466`). `handleWebCommand` parses, then calls it (`App:7085-7091`). This is the shape `test_input` has: a source of commands, not a command body. |
| A read that must not wait for the command lock | An HTTP GET route on the web server's per-connection thread (`WS:276-287`), with no `commandMutex_`. Examples: `GET /api/state` -> `buildWebStateJson() const` (`App:7711`), `GET /api/config` -> `buildHardwareConfigFileJson()` (`App:7168-7173`, `App:5290-5321`), `GET /api/media`, `GET /api/presets` (`App:7360`). Only `App:7032` and `App:9093` take `commandMutex_` directly. |
| A read that runs a shell probe | `scanMountableMediaDrives` runs `lsblk` from a read and keeps its own cache under a function-local mutex (`App:2266-2283`; CMD-25). A read may refresh its own cache. |
| Slow work that must not hold the lock | A worker thread with its own state group; the client polls a status command. Example: the media speed test, `startMediaSpeedTest` `App:8957-9009`, status reply `App:10610-10614`. Slow work that does hold the lock is an accepted rough edge (format, gyro calibration; conventions section 4). |
| A bounded wait | `const auto deadline = std::chrono::steady_clock::now() + timeout; while (now() < deadline)` (`waitForTimedatectlNetworkSync`, `App:2979-2980`). |
| Route parameters | The query string, read with `queryParameterValue` (`App:7198-7199`, `App:7396`, `App:7441`). Beside a raw body, a header: `POST /api/presets/import` reads `?name=`, else `x-preset-filename` (`App:7396-7400`), and the page sends `X-Preset-Filename` (`WCP:10472`). |
| Replies | `okReply(id, fragment)` and `errorReply(id, sentence)` only (`App:108-128`). Routes reuse them with id -1 and set an HTTP status 400/404/500/503 (`App:7178-7183`, `App:7647`). No reply carries a `code` member. |
| A whole-file save | `POST /api/config` -> `saveHardwareConfigFile(text, &backup, &errorMessage)` (`App:5323`, `App:7175-7195`). Last writer wins. Refused with 400 + `errorReply`. |
| Booleans in a command | Ten hand parsers. Eight lenient, `*enabled == "true" \|\| *enabled == "1"` after refusing a missing field (`App:9480-9486`); conventions section 4 makes this the rule for a plain switch. Two strict, `true/false/1/0` else refused (`App:9130-9133`), where a wrong value must not pass. Lone switches take `enabled=`, with or without the `_enabled` suffix (`set_standby_usb_power_off`, `App:9128`; CMD-7 "usually"). `parseBooleanToken` (`App:2936-2956`) reads `timedatectl` output only (`App:2969`). |
| Enum settings in a command | `value=<toString(enum)>`, e.g. `set_cdng_compression` (`App:9340`). The state key carries the same string. |
| Booleans in `camera_settings.conf` | `output << prefix << "iso_auto=" << s.isoAuto` writes `0/1` (`CC:749`). Read with `std::stoul(value) != 0` (`CC:659-660`). |
| Touch UI command invokables | Return `bool`. Thin variants are `return sendCoreCommand(...)` (`UI ACB:736-741`). Booleans go out as `enabled="true"/"false"` (`UI hpp:133-136`). Only `notifyUserActivity` and `refresh` are `void` (`UI hpp:100`, `:110`). |
| UI takes Core's reply as the truth | After `apply_preset`, the UI calls `applyCoreState(reply.value("state"))` (`UI ACB:1155-1162`). After a plain set, upstream sets its own value after the send (`applyIso`, `UI ACB:297-299`, `:312-313`). |
| Periodic supervision and periodic events | The 1 Hz loop in `wait()` (`App:7025-7040`). Live values pushed as literal events, e.g. `audio_level` (`App:8383`). |
| Mixed versions | Core and UI ship together. There is no protocol version; missing fields default (`README.md:306`, CMD-30). |

## The target

| Thing | Before (port today) | After |
| --- | --- | --- |
| Command entry | `handleReadOnlyHardwareCommand` (5 commands) + `test_input` + safety-stop abort before the lock | One chain under `commandMutex_`. Before the lock: `test_input` (it re-enters `handleCommand`), with one comment line, and `abortSafetyStopFlushForRecord` (unchanged) |
| Hardware file + Controls model, for the page | socket command `get_controls`, nested `"controls":{...}`, not under the lock | `GET /api/config`, the upstream route. Upstream fields stay (`ok`, `path`, `display_path`, `exists`, `size_bytes`, `size_text`, `modified_text`, `text`) and the port's `revision`, `boot_copy`, plus the members the page reads: `written_by`, `written_at`, `errors`, `warnings`, `issues`, `replaced`, `model`, `peripherals`, `i2c_buses`, `apply`, `dpi_lines`, `gpio_chips`. Built by the member `buildHardwareConfigFileJson()`. It parses once and writes no counter |
| Which services still read the old file | `systemctl show` inside `get_controls`, erasing `pendingUnitSince_` | unchanged in place: `controlsApplyJson` keeps the probe, now called from the builder. It is a read refreshing its own cache, as `scanMountableMediaDrives` |
| Saved versions | `controls_history [name=]` | `GET /api/config/history` (list) and `GET /api/config/history?name=<file>` (one text), like `GET /api/presets` + `?name=` |
| Last input (Listen) | pre-lock command, polled by a `setInterval` that does not wait | same command, ordinary block under the lock. The page asks again only after each reply (a `setTimeout` chain) |
| I2C scan | pre-lock; a take can start mid-scan | ordinary block under the lock, refused during a take. It gives up after 1 s of scanning |
| Action catalog | pre-lock. Reply also carries `values`, `values_for`, `gestures`, which nobody reads | ordinary block under the lock, `"actions":[...]` plus the catalog's own members |
| Error replies | `errorReplyBody` with `code`, `revision`, `issues`, `new_errors`, `conflicts`, `drm` | `errorReply(id, sentence)` everywhere. The sentence says what to do ("Reload, then change it again."). HTTP routes keep their status (400/409/500/503, 410 for a removed clip). The store's refusal kind stays inside Core; it only picks the HTTP status |
| Validation details | in `ok:false` replies | in `ok:true` replies only. A `dry_run` (the Config "Check" button) answers `ok` with `issues`. A refused save says how many new errors there are and names the first |
| Revision of a config text save | `X-Apertar-Revision` header; `old_page` 409 when an Origin is present and the header is missing | the same header (upstream's `x-preset-filename` shape). Stale -> 409 + sentence. Missing -> saved over the current file, as in 1.6.0, for every client |
| `set_boot_config` revision | needed only on the HTTP door with an Origin header | checked when sent, on both doors; missing -> saved, as the config text save. The `browser` parameter and `old_page` go. Deleting the route is the boot-config-helpers theme's job |
| Boot Config and `set_controls` flags | `boolFieldValue` and `parseBooleanToken` accept `on/yes/off/no`, any case; `dry_run`/`confirm_display` fall back to `false` on a typo | the strict upstream form (`App:9130-9133`): `true`/`1`, `false`/`0`, otherwise "`<field>` must be true or false." These flags decide whether a file is written |
| Pre-roll auto switch | `set_storage_preroll value=on\|off` (lower-cased) | `set_storage_preroll enabled=true\|false`, the lenient upstream form for a plain switch (missing field refused). Name, stored value and state key unchanged |
| CinemaDNG log | `set_cdng_log value=auto\|off` | unchanged on the wire: an enum setting with a string state key (`cdng_log`), like `set_cdng_compression`. Only the invokable changes |
| Touch UI invokables | six `void` | `bool`. `startStoragePreroll()`, `applyStoragePrerollAutoEnabled(bool enabled)`; the rest keep their names |
| Port switches in `camera_settings.conf` | `true`/`false` | `0`/`1`, as `iso_auto`. Readers keep accepting both |
| ISO Lock in the UI | already set from Core's reply (`ACB:1210` -> `:1411`) | unchanged |
| File timecode in the UI | set from Core's reply, then again from the UI's guess | from Core's reply only |
| `set_value_steps` reply | `"ui":{...}` | the same members, flat, like `set_sleep_mode` / `set_favorites_order` |
| Live ISO/WB in use (optional) | `get_state` every 1 s | Core's 1 Hz loop publishes one event when the value in use changes. The UI keeps the 30 s poll |

Who owns what after the change: the hardware file stays owned by `HardwareConfigStore` (writes) and App (reads for the page). UI.conf and `camera_settings.conf` ownership is unchanged. No value moves to another file, so no key needs taking over. The only file change is how seven booleans are spelled in `camera_settings.conf`, and both spellings stay readable.

How values reach the UIs: the WebUI reads the hardware file and model only through `GET /api/config`, and commands only through `POST /api/command`. The touch UI never used the moved commands (`grep` in `ui-work/src`, `ui-work/qml`: no hits), so it sees no change except the invokables and the pre-roll argument.

## Commit plan

Checks named below:
- **build**: `/home/user/build/bin/check_core.sh /home/user/wt/core-work <tag> both tests`. This builds with and without libcamera (`-Wall -Wextra`, the warning count is printed and must not grow) and runs the 17 host tests.
- **smoke**: `/home/user/build/bin/smoke_core.sh <build>/apertar-core <port>`, diffed against the previous commit's output. Every 1.6.0 field must keep its type.
- **page**: `apertar-core --simulate` plus headless Chromium on the named card, and `/home/user/apertar-kb/working/tools/controls_page_test.js`. The page check runs against `--simulate`, not only against the test's mock.
- **ui build**: `/home/user/build/bin/check_ui.sh`.

The two check tools live outside the repos. Where a commit changes what they call, they change alongside it (named in the commit), not inside the commit.

"Rig" means the owner's CM5 with IMX585, CFexpress hat and HDMI monitor. "Stock" means the original driver, the 720x720 screen and no port keys in any file.

1. **core, web: the Controls page reads the hardware file through GET /api/config**
   - Repo: Core. Files: `App` `buildHardwareConfigFileJson` (`:6185`) becomes the member `std::string buildHardwareConfigFileJson()`, declared in `AppH` next to the other `build*Json`. The `get_controls` block (`:12430-12474`) is deleted, and `"get_controls"` comes out of the `help` literal (`:12946`). WCP: `loadControls` (`:18333-18343`) and `controlsRecheckSoon` (`:18589`) call `fetch("/api/config", { cache: "no-store" })`. `controls.controls.X` becomes `payload.X`.
   - Moves: the member list of `get_controls` into the builder. `hwconf::parse(info.text)` runs once into `const hwconf::Document doc`. The model, peripherals and issues are of the file Core runs (`info.text`). `text` stays upstream's editor text (file, `/boot` copy or template); the Controls page does not read `text`. The `systemctl` probe stays in `controlsApplyJson`, called from the builder.
   - Deletes: the counter writes `controlsErrors_ = ...` (`:12434-12436`). The worker and the saves keep them current.
   - Cost named: `GET /api/config` gets heavier for every caller. On Settings > Config the page calls both `fetchConfigFile` and `loadControls` (`WCP:10167-10171`), and after each save both again (`WCP:18310-18312`, `:18739-18741`, `:19008-19010`). Each is now a full build: the I2C probe per peripheral row, the hat status byte and `/sys/class/nvme` reads (`cfeHatPeripheralJson`, `App:12091-12128`), and one `systemctl show` per pending unit. No lock, no take path. Letting one fetch feed both cards is the webui-state theme's poll work.
   - Check tools: drop `get_controls` from `smoke_core.sh:35-36` (`/api/config` is already in its route list, `:38`). Move the `get_controls` mock in `controls_page_test.js:67` onto `GET /api/config` (`:60`).
   - Lines: App -50 / +40, WCP -8 / +8.
   - Here: build; smoke (all 1.6.0 `/api/config` fields present, same types); page: Settings > Controls loads, rows render, Hardware card lists peripherals; `curl /api/config | jq .model.rows[0]`; `--simulate` with no hardware file: Controls shows the template rows' model, not "does not describe its controls yet".
   - Pi only: open Controls while a take runs. The page loads and the take drops no frames (`recording_dropped_frames` stays 0 in `/api/state`).
   - Rig sees: the same Controls and Hardware cards. Stock sees: the same, plus the hat row ("Bus 10 does not exist on this Pi." on Pi 4/CM4) now in every `curl /api/config` too; App-4-F19 (hardware-inputs) removes the row when the file has no `[cfexpress_hat]`.
   - Depends on: nothing.

2. **core, web: saved hardware-file versions come from GET /api/config/history**
   - Repo: Core. Files: `App` `handleWebRequest`, one branch next to `GET /api/config`: `GET /api/config/history`, with `queryParameterValue(request.query, "name")` for one version. `okReply(-1, ...)`, or 404 + `errorReply(-1, "No saved version called <name>.")`. The `controls_history` block (`:12475-12491`) is deleted, and it comes out of `help`. WCP: `:18627`, `:18654`, `:18966` use one `async function fetchConfigHistory(name)` in the R10 step 6 shape.
   - Check tools: drop `controls_history` from `smoke_core.sh:35-36`, add `/api/config/history` to its route list (`:38`). Move the mock at `controls_page_test.js:68-70` onto `GET /api/config/history`.
   - Lines: App -18 / +20, WCP -6 / +12.
   - Here: build; smoke; page: Config > History lists versions, picking one loads its text, Undo in Controls restores (`controls_page_test.js:267-270` checks the history request and the save).
   - Pi only: nothing beyond the page check.
   - Rig sees: the same history and Undo. Stock sees: nothing new (the card it lives on is the same).
   - Depends on: nothing.

3. **core: an I2C scan gives up after one second**
   - Repo: Core. Files: `App` `scan_i2c` (`:12503-12549`).
   - Adds: `const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);` before the address loop, and after each probe `if (std::chrono::steady_clock::now() >= deadline) return errorReply(command.id, "I2C bus " + std::to_string(bus) + " does not answer: check the wiring.");`. Precedent: the bounded wait at `App:2979-2980` @upstream-1.6.0. `I2cProbe.cpp` is unchanged.
   - Why a time bound and not an errno list: after commit 5 the scan holds the command lock. A stuck bus (SDA held low) costs one adapter timeout per address, up to 117 of them. Which errno a stuck or empty address gives differs by adapter (bcm2835, RP1 designware, i2c-gpio) and is not measured. A time bound holds on every Pi model without knowing the errno: worst case 1 s plus one adapter timeout.
   - Lines: -0 / +4.
   - Here: build. The probe needs real `/dev/i2c-*`, so here only the compile is checked.
   - Pi only: on Pi 4, Pi 5/CM5, and CM4 if at hand: `time python3 ~/apertar-kb/working/tools/core.py scan_i2c bus=1` lists the same addresses as `i2cdetect -y -r 1` and takes well under 1 s. Shorted-bus bench check (optional): jumper SDA (GPIO 2) to GND through a 1 kOhm resistor, never directly; the scan returns the sentence within about 1 s plus one adapter timeout.
   - Rig sees: the same scan. Stock sees: the same scan.
   - Depends on: nothing.

4. **core: list_actions answers the action list only**
   - Repo: Core. Files: `App` `list_actions` (`:12551-12572`); `src/hardware/ActionCatalog.hpp` `catalogJson` (`:336-358`, its only caller is `list_actions`).
   - Deletes: `values`, `values_for`, `gestures`, and the `substr(1, size-2)` brace strip (`:12557-12558`). `catalogJson` returns members without braces, so the reply is `okReply(id, catalogJson())`. The command no longer reads UI.conf or camera settings.
   - Lines: -16 / +2.
   - Here: build; page: action pickers list the same actions.
   - Pi only: nothing.
   - Rig sees: the same pickers. Stock sees: the same.
   - Depends on: nothing.

5. **core, web: controls_last_input, scan_i2c and list_actions take the command lock like every command**
   - Repo: Core. Files: `App`; WCP Listen loop (`:18695-18720`).
   - Moves: the three blocks (`:12493-12549` and the 3-line `list_actions` block left by commit 4) into the chain next to `test_output` (`:12762`).
   - Deletes: `handleReadOnlyHardwareCommand` and its declaration (`AppH:83`), and the call at `:12579`.
   - Keeps: `test_input` before the lock, with one comment line: "test_input runs a control's actions, which enter handleCommand themselves." The refusal becomes "scan_i2c requires bus." (C1-I07 form). `"test_input"` is added to `help`, next to `test_output`.
   - WCP: the Listen loop becomes a `setTimeout` chain: each tick awaits its reply, then schedules the next 300 ms later. While a long command holds the lock (the safety-stop drain, `record_start`), at most one `controls_last_input` waits, and the tab's lock-free `GET /api/state` keeps its connection slots.
   - Lines: App -12 / +8 (the rest is a move), WCP -2 / +4.
   - Here: build; page: Listen highlights a row on `test_input` (`controls_page_test.js:264-266`); scan and pickers work.
   - Pi only: start a take, press Listen and turn a knob. The row lights within about 0.3 s and the take is unaffected. Press Listen, start and stop a take: at the stop the page's REC state updates within 1 s and DevTools > Network shows at most one pending `controls_last_input`. A scan during a take is refused with the existing sentence.
   - Rig sees: the same Listen, scan and pickers; during a take stop the Listen highlight can wait for the drain. Stock sees: the same.
   - Depends on: 3, 4.

6. **core, web: hardware-file refusals are one sentence**
   - Repo: Core. Files: `App` `set_controls` (`:12816-12822`), `set_buffer_mode` (`:12856-12860`), `set_frames_per_folder`/`set_clip_merge` (`:12896-12900`), `set_storage_preroll` (`:12930-12934`). Store: `HardwareConfigStore.cpp:336-341`. WCP: `saveHardwareSettings` (`:18300-18306`), `saveControls` (`:18729-18735`), `checkConfigFile` (`:18864-18880`).
   - In App: `errorReplyBody(...)` becomes `errorReply(command.id, result.error)` in all four commands.
   - In the store: the "new errors" refusal is skipped on a dry run (`&& !flags.dryRun`), so Check gets `ok:true` with `issues` (the dry run then returns at `.cpp:349`). The conflict sentence gains "Reload, then change it again.", as the two stale sentences already say (`.cpp:285`, `:294`).
   - In WCP: the `kept` code branches and the `found` lists on refusal are deleted; the message is Core's sentence. `checkConfigFile` keeps its `!result.ok` branch, which now only sees real refusals. Its `|| "h"` fallback goes: Check is disabled until `state.configRevision` is set (WCP-10-F7, the fallback part).
   - Lines: App -22 / +5, store -1 / +2, WCP -10 / +4.
   - Here: build; page: save a Controls edit with a pin clash, which is refused with "Not saved: 1 new error. ..."; Check on the same text lists the errors; save from two tabs, and the second is refused with "... Reload, then change it again."
   - Pi only: nothing.
   - Rig sees: one sentence instead of a sentence plus a list on a refused save; Check still lists all. Stock sees: the same.
   - Depends on: 1 (the cards reload through `/api/config`). Coordinate with **storage-settings**: if it moves `set_buffer_mode`/`set_frames_per_folder`/`set_storage_preroll` out of the hardware store first, only `set_controls` is left here.

7. **core, web: a config text save names its revision only to be refused when stale**
   - Repo: Core. Files: `App` `POST /api/config` (`:8624-8684`), WCP `saveConfigFile` (`:18986-19024`).
   - Keeps: the `X-Apertar-Revision` header (upstream `x-preset-filename` shape, `App:7396-7400` @upstream-1.6.0). The Boot Config card sends the same header (`WCP:20076-20078`).
   - Deletes: the Origin/`old_page` 409 (`:8633-8643`). A missing header means base = the current revision for every client, as 1.6.0 saves. `errorReplyBody` at `:8657` becomes `errorReply(-1, message)`. The WCP `code` branch (`:19017-19021`) goes; the message is Core's sentence. A refusal keeps its status (409 for stale/locked/being written/conflict/merge review, 400 otherwise).
   - Lines: App -12 / +3, WCP -3 / +1.
   - Here: build; page: save, then save again from a second tab, which is refused with a sentence and the text stays in the box; `curl -X POST --data-binary @f 'http://127.0.0.1:PORT/api/config'` without a header saves (1.6.0 behaviour), and with `-H 'Origin: x'` too.
   - Pi only: nothing.
   - Rig sees: the same editor. Stock sees: the same editor; a tab left open across an update saves instead of being refused.
   - Depends on: 6.

8. **core, web: playback routes refuse through errorReply**
   - Repo: Core. Files: `App` `handleWebRequest` sites `:8503`, `:8510`, `:8533`, `:8536`, `:8573`, `:8691`, `:8820`; WCP `pbvFetchFrame` (`:12355-12361`).
   - Adds: one local lambda `holdResponse(const std::string &hold)` (CMD-25 named local lambda), which returns a 409 `WebServer::Response` with `errorReply(-1, sentence)`. The sentence comes from upstream's families (App-3-F6): recording "Stop recording before playing or downloading media." (`App:7514` family), writing "Wait for the current capture to finish writing to media.", media_test "Wait for the media speed test to finish first." (`App:9110`), standby "Wake the camera first.", media "Mount media first.". The `hold` member goes; the viewer still maps the hold from the state (`pbvHoldText`).
   - Changes: busy becomes 503 + `errorReply(-1, "Playback is busy. Try again in a moment.")`. A removed clip becomes 410 + `errorReply(-1, "This clip was removed.")`. WCP: `if (response.status === 410) return { outcome: "gone" };`, and 404 means stale.
   - Lines: App -14 / +16, WCP -3 / +2.
   - Here: build; page: start playback in `--simulate`, delete the clip from another tab, and the viewer shows "removed". Start a take and the viewer holds. `curl -i` a download during a take: 409 and the "Stop recording" sentence.
   - Pi only: play a clip, press record; playback stops before the first frame is written and the take has no drops.
   - Rig sees: the same viewer. Stock sees: the same viewer.
   - Depends on: nothing.

9. **core, web: Boot Config refusals are one sentence and the last machine-code reply goes**
   - Repo: Core. Files: `App` `bootConfigSet` (`:3775-3841`), its two callers `:9194-9197`, `:14605-14606`, `errorReplyBody` (`:173-184`); WCP `saveBootConfig` (`:20390-20405`).
   - Changes: every `errorReplyBody` becomes `errorReply`. The status in `BootConfigReply` stays for the route until boot-config-helpers deletes it. The `browser` parameter goes, and with it `old_page`. The revision is checked when sent, on both doors; a save without one is saved, as the config text save (commit 7). The display guard keeps refusing, with "This changes the display overlays (...). set_boot_config needs confirm_display=true for that." The card always sends `confirm_display` from its review, so the card never sees it. WCP: on any refused save the card reloads (`loadBootConfig(true, false, true)`, which keeps the choices). The `code` test goes.
   - Deletes: `errorReplyBody`. `grep -n errorReplyBody src` is empty after this commit, and no commit leaves it unused (it is in the anonymous namespace, `App:82`, so an unused copy would raise the `-Wunused-function` count).
   - Lines: App -32 / +8, WCP -2 / +1.
   - Here: build (warning count not higher than before 6); host test `boot_config_test` passes; page: Boot Config review and save in `--simulate` (writes to the simulated path), and a stale save from a second tab reloads the card.
   - Pi only: the owner's CM5: change a sensor link, save, reboot, and check `/boot/firmware/config.txt` and `vcgencmd get_config`. A Pi 4 with the stock 720x720 DPI screen: a change that drops the DPI overlay is refused by `core.py set_boot_config ...` without `confirm_display=true`.
   - Rig sees: the same card. Stock sees: the same card.
   - Depends on: 6, 7 (the other `errorReplyBody` callers). **boot-config-helpers** deletes `POST /api/boot-config` and `BootConfigReply`; either order works.

10. **core: Boot Config and set_controls switches read true or false, 1 or 0**
    - Repo: Core. Files: `App` `boolFieldValue` (`:3709-3718`) and its callers (`:3746`, `:3781-3782`); `set_controls` (`:12786-12812`).
    - Changes: `boolFieldValue` loses the lower-casing and `on/yes/off/no`: `"true"`/`"1"`, `"false"`/`"0"`, else `nullopt`. `dry_run` and `confirm_display` are refused when present and not one of those ("dry_run must be true or false.") instead of falling back to `false`, so a typo never writes `config.txt`. `set_controls` `restore`, `dry_run`, `force`, `confirm_merge` use the same test instead of `parseBooleanToken`, which goes back to reading `timedatectl` output only (`App:3352`). This is upstream's strict form (`App:9130-9133` @upstream-1.6.0): these flags decide whether a file is written.
    - Lines: -12 / +14.
    - Here: build; `boot_config_test`; page: the card's toggles still save, Check and Save in Config still work (the page sends `"true"`, `WCP:18866`); `curl` `set_controls ... dry_run=yes` is refused.
    - Pi only: nothing.
    - Rig sees: nothing different. Stock sees: nothing different.
    - Depends on: nothing.

11. **ui: the new control invokables return bool**
    - Repo: UI. Files: `src/ApertarControlBridge.hpp:194-200`, `ACB:618-630`, `:632-659`, `:686-701`, `:716-727`.
    - Changes: `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto`, `applyClipNameTemplate`, `requestClipNamePreview` and `applyCdngLog` return `bool`. They return `false` after `setLastError` or a failed send and `true` at the end. The thin ones are `return sendCoreCommand(...)`. No wire change, and QML ignores the results.
    - Lines: -12 / +16.
    - Here: ui build; the touch UI builds and the QML loads (offscreen).
    - Pi only: on the 720x720 screen and on the owner's HDMI monitor, toggle Log, write buffer, clip name; a refusal still shows its sentence.
    - Rig sees: nothing different. Stock sees: nothing different.
    - Depends on: nothing.

12. **core, web: set_storage_preroll takes enabled=**
    - Repo: Core. Files: `App` block `:12917-12944` and `help`; WCP sender `:15843` and patch case `:14030`.
    - Changes: the command reads `enabled` in the lenient upstream form for a plain switch (`App:9480-9486` @upstream-1.6.0): missing -> "set_storage_preroll requires enabled.", `true`/`1` -> on, else off. The `tolower` loop goes. The name, the stored `[media] preroll=on|off` and the state key `storage_preroll_auto` are unchanged. A script that still sends `value=` is refused with that sentence, not switched off.
    - Lines: -8 / +5.
    - Here: build; page: the Auto pills switch and survive a reload.
    - Pi only: nothing beyond the touch UI check in 13.
    - Rig sees: the same switch. Stock sees: the same switch (off by default, `0977dd6`).
    - Depends on: 6. Lands together with 13 (Core and UI ship together, CMD-30). Coordinate with **preroll** and **storage-settings** (it may move where `preroll=` lives; the argument here does not depend on that).

13. **ui: the pre-roll invokables send enabled= and start is a verb**
    - Repo: UI. Files: `hpp:195-196`, `ACB:618-630`, `qml/SettingsPage.qml:5605`, `:5628`, `:5635`.
    - Renames: `applyStoragePreroll()` becomes `startStoragePreroll()` (an action is a verb, UIC-10). `applyStoragePrerollAuto(bool on)` becomes `applyStoragePrerollAutoEnabled(bool enabled)`, which sends `set_storage_preroll enabled="true"/"false"`.
    - Lines: -8 / +8.
    - Here: ui build.
    - Pi only: touch UI Media > Pre-roll Auto On/Off, then `core.py get_state`, which shows `storage_preroll_auto` following.
    - Rig sees: the same buttons. Stock sees: the same buttons.
    - Depends on: 11, 12.

14. **ui: the file timecode follows Core's reply**
    - Repo: UI. Files: `ACB` `applyTimecodeMode` (`:766-769`).
    - Deletes: the four lines that set `m_fileTimecodeMode` from `target`. `sendCoreCommand` already passed the reply (`settingsBody`, with `timecode_mode`, `App:13295-13335`) through `applyCoreMessage` (`ACB:1210`) to `applyCoreState` (`ACB:1411-1412`, `:1698-1707`) before it returns. The ISO Lock path needs no change: it already takes `iso_auto` and `iso` the same way.
    - Lines: -4 / +0.
    - Here: ui build.
    - Pi only: set the screen timecode only, and the Record page's file timecode is unchanged; set both, and it follows.
    - Rig sees: nothing different. Stock sees: nothing different.
    - Depends on: nothing.

15. **camera: the new camera switches are written 0 and 1 in camera_settings.conf**
    - Repo: Core. Files: `CC` `writeCaptureSettings` `:963`, `:974-979`.
    - Changes: `<< s.member` for `clear_hdr`, `fps_phase_lock`, `preview_tdn`, `media_trim`, `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `fps_speed_ramp_stretch_audio`. The readers (`CC:869-896`) already accept `true` and `1`, so files written by the port keep loading. A file is rewritten in the new spelling at the next settings commit (the debounced persist), the way upstream rewrites the whole file on every change. `fps_speed_ramp_after=return|stay` stays: it is an enum word.
    - Downgrade: fork main reads `clear_hdr` as `true` or `1` (`core-main CC:710-711`); 1.6.0 ignores the port keys.
    - Lines: -7 / +7.
    - Here: build; `--simulate` with a `camera_settings.conf` holding `preview_tdn=true`; change any setting; the file now says `preview_tdn=1` and `get_state` still says `"preview_tdn":true`.
    - Pi only: nothing.
    - Rig sees: its settings kept across the update. Stock sees: no port keys until the first settings change, then the port keys in `0/1`.
    - Depends on: nothing. Coordinate with **storage-settings** if it moves any of these keys.

16. **core: set_value_steps echoes the lists flat**
    - Repo: Core. Files: `App:14178`.
    - Changes: `okReply(command.id, valueStepsJson(...))` without the `"ui":{...}` wrapper. Same members, like `set_sleep_mode`. No reader of the reply exists (WCP `:8494` awaits it only).
    - Lines: -1 / +1.
    - Here: build; `curl -d '{"cmd":"set_value_steps","name":"iso","free":"true"}' /api/command`.
    - Pi only: nothing.
    - Rig sees: nothing different. Stock sees: nothing different.
    - Depends on: nothing.

17. **(optional, owner) core: the ISO and white balance in use go out as an event**
    - Repo: Core. Files: `App` `wait()` (`:8289-8318`).
    - Adds: after the recording-failure check, when `isoAuto || whiteBalanceAuto` and the measured ISO or kelvin differs from the last one sent, `publishEvent("{\"event\":\"exposure_in_use\",\"iso_actual\":N,\"wb_actual_kelvin\":K}")`. These are state keys; the event is literal (CMD-17). The 1 Hz loop already exists (CMD-21).
    - Why not the `settings` event: it already names `iso_actual`, but sends 0, because `emitSettingsEventLocked` serialises `settings_`, not the copy `settings()` fills (X-state-consistency-8, not fixed here). Using it would need that fixed and would send the whole settings body every second.
    - Lines: +10.
    - Here: build; `--simulate` socket client sees the event only while auto is on.
    - Pi only: auto ISO on, pan from dark to bright; the event follows within 1 s.
    - Rig sees: one more event. Stock sees: one more event, ignored by a client that does not know it (CMD-30).
    - Depends on: nothing.

18. **(optional, owner) ui: the touch UI keeps the 30 s poll while auto ISO or WB runs**
    - Repo: UI. Files: `ACB:16-20`, `:1015-1016`, and the event branch at `ACB:1411`.
    - Changes: `exposure_in_use` joins the events that go whole to `applyCoreState`. `kLiveValuePollIntervalMs` is deleted.
    - Lines: -4 / +1.
    - Here: ui build.
    - Pi only: auto ISO/WB values on the touch UI and HDMI monitor follow the scene within about 1 s, and `journalctl -u apertar-core` shows no `get_state` storm.
    - Rig sees: the same live values, fewer polls. Stock sees: the same.
    - Depends on: 17.

Order: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 + 13 (together), 14, 15, 16; 17 + 18 only if the owner says yes. Every Core commit leaves the 1.6.0 fields of `get_state`, `/api/state`, `/api/config` and every 1.6.0 command reply as they are. The port-only commands that move (`get_controls`, `controls_history`) are clients of the WebUI only.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| `test_input` before the lock | one `if` above `std::lock_guard` in `handleCommand`, with one comment line | It is a source of commands, like upstream's `dispatchHardwareInputCommand` (`App:8458-8466`), not a command body. Under the lock it would deadlock. Script actions are already refused (`d1dcdee`). Its placement is on the owner's list |
| `abortSafetyStopFlushForRecord` before the lock | as is (`App:12587`, `:10123`) | The safety-stop drain holds `commandMutex_`. Moving the abort under the lock needs the drain to stop holding the lock, which is buffer/safety-stop work, not this theme |
| Hardware-file revisions, history and stale-save refusal | `HardwareConfigStore`; a revision in the `X-Apertar-Revision` header or a `base=` field, checked when sent; refusals as sentences | Upstream's `POST /api/config` is last-writer-wins. The revision guard protects two surfaces editing one file. Kept as small as upstream's shapes allow: a header beside a raw body (`x-preset-filename`), `errorReply`, HTTP 409. Without a revision the save is 1.6.0's |
| Validation lists (`issues`, `new_errors`) | members of `ok:true` replies and of `GET /api/config` | Upstream has no validator. The lists stay out of error replies, so a refusal stays one sentence |
| HTTP statuses 409 and 410 on routes | `errorReply(-1, sentence)` bodies | Upstream routes use 400/404/500/503. The status is HTTP, not a second error vocabulary in the JSON. 410 replaces the `gone` member |
| A time bound on the I2C scan | one `deadline` in the loop | Upstream has no bus scan. The bound is upstream's bounded-wait shape (`App:2979-2980`) |
| `set_iso_auto enabled=false` (Lock), `set_timecode_mode target=` | optional fields; without them the 1.6.0 meaning holds | Already judged keep-as-is in App-5-F9 and App-5-F7. The UI already shows Core's reply |
| `exposure_in_use` event (if 17 is taken) | one literal event from the 1 Hz loop | Nearest upstream: `audio_level` (`App:8383`) and the 1 Hz loop |

## For the owner

| Question | Options | Recommendation and cost |
| --- | --- | --- |
| Socket clients (your `core.py`) lose `get_controls` and `controls_history` | a) move to `GET /api/config` (+ `/history`); b) keep both as ordinary commands under the lock, as well | a). Over ssh it is `curl -s localhost:8000/api/config`. b) keeps two doors to one file, the thing App-4-F1 is about. Cost of a): your scripts change once |
| Validation details on a refused save | a) sentence only, with the count and the first new error; the Check button lists all; b) keep `issues` in error replies as the one documented extension | a). It is what 1.6.0 does for every refusal. Cost: a card shows one problem instead of a list until you press Check |
| `old_page` (a browser tab opened before an update) | a) drop it; b) keep it on Origin presence, as now | a). Core and page ship together (CMD-30), and the new page always sends the revision. Cost: one tab left open across the update can save over a newer file once |
| `set_boot_config` without a revision | a) saved, the revision is checked only when sent, on both doors (commits 7 and 9 treat both saves alike); b) refused on both doors, as X-protocol-security-7 proposes | a). Your scripts keep working; the card always sends one. Cost of b): every script calls `get_boot_config` first, and the card and the config text save then follow two rules |
| `set_storage_preroll` -> `set_storage_preroll_enabled`, and the four camera switches (`set_fps_phase_lock`, `set_media_trim`, `set_preview_tdn`, `set_clip_merge`) | a) leave the names: they take the upstream argument, and upstream has lone-`enabled` commands without the suffix (`set_standby_usb_power_off`, `App:9128`); b) rename all five, with no alias | a). Cost of b): one more Core+UI+WebUI pair of commits |
| `storage_preroll` -> `storage_preroll_start` (App-5-F8) | a) rename in the same pair as 12/13; b) leave it | a), if the preroll theme keeps the command. Cost: 4 lines |
| `set_cdng_log` | a) keep `value=off\|auto` (an enum, like `set_cdng_compression`); b) `enabled=` as UI-control-bridge-F1 suggests | a). The state key is the string `cdng_log`, so the argument matches it. Whether `Auto` should read `On` (Camera-headers-F14) belongs to the camera-modes theme |
| Where `test_input` sits | a) one `if` above the lock in `handleCommand` (commit 5); b) a branch in `handleWebCommand`, so the socket gets "Unknown command" | a). b) keeps `handleCommand`'s first statement as upstream's but takes the command from `core.py`. The only page client is `WCP:16920` |
| The 2 s file check in the Controls worker (App-4-F7) | a) keep it: an ssh edit applies within 2 s; b) wake the worker only on a save and at take end, drop the timeout; an ssh edit applies at the next save or restart, as upstream | Your call: it was designed in (decisions.md:47). Not planned here; if b), it goes with **hardware-inputs**, which owns the file's apply. This plan adds no work to that turn |
| The 1 s `get_state` poll during auto ISO/WB | a) keep it; b) commits 17 + 18 | b), if the HDMI monitor is in use (two processes poll). Cost: about 10 lines and one new event name |
| `scan_i2c` under the lock | a) under the lock with a 1 s bound (commits 3, 5); b) a worker with polled state, like the media speed test | a). Measure on a Pi 4. If a healthy scan takes over about 0.5 s, take b) (about +40 lines) |

## Risks and what was not determined

- **Scan time under the lock** (unconfirmed). `probeI2cAddress` opens the bus device and reads one byte per address. On a healthy bus this should be tens of ms. It is not measured on Pi 4 (`i2c-bcm2835`), Pi 5/CM5 (RP1 `i2c-designware`) or CM4. Settle with `time core.py scan_i2c bus=1` on each. If a healthy scan comes near 1 s on any board (an `i2c-gpio` bus is the slow case), the bound refuses a working bus: raise it or take owner option b).
- **Stuck-bus cost** (probable). With the bound, a stuck bus holds the lock for 1 s plus one adapter timeout plus the i2c core's retries. The adapter timeout and the errno differ by adapter and are not measured. Settle on Pi 4 and Pi 5 with `strace -f -e trace=ioctl,read -p $(pidof apertar-core)` while `core.py scan_i2c bus=1` runs, and with the 1 kOhm bench short of commit 3.
- **`/api/config` cost** (probable). Commit 1 makes every `GET /api/config` a full build: I2C buses, GPIO chips, the hat (`cfeHatPeripheralJson` probes bus 10 `0x34`) and one `systemctl show` per pending unit. It runs on Settings page opens and after saves (twice each), not in the 1 Hz poll, and takes no lock. The hat probe racing the UI's automounter is HW-controls-model-F15, owned by hardware-inputs.
- **A missing hardware file**: the model, peripherals and issues are of `info.text` (empty), and `text` is the template or `/boot` copy, as today in the two separate replies. Check in `--simulate` with no file (commit 1's check).
- **Pair 12/13**: a UI from before 13 against a Core with 12 is refused with "set_storage_preroll requires enabled." on the Auto switch. A UI with 13 against a Core before 12 sends `enabled=` and gets "set_storage_preroll needs value=on or value=off.". Under CMD-30 the owner's install builds both; the risk is only in a half-updated tree.
- **Listen during a long locked command** (probable). After commit 5 a Listen highlight waits while the safety-stop drain or `record_start` holds the lock. The `setTimeout` chain keeps it to one waiting request. Checked on the Pi with commit 5's take-stop step.
- **Not determined**: whether `collectingCommandEvents_` (set before the lock, conventions section 4) mixes events into the replies of the moved commands. It is upstream's rough edge and unchanged.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-4-F1 | 1, 2, 5 |
| App-1-F5 | 6, 7, 8, 9 |
| X-protocol-security-3 | no change: Core and UI ship together (CMD-30), and the UI already takes `iso_auto`/`iso` from the reply (`ACB:1210`, `:1411`, `:1505`) |
| X-protocol-security-4 | 14 (the guess goes; the reply already sets the file timecode). The mixed-install case: no change (CMD-30) |
| X-protocol-security-5 | 1, 3, 5. The `systemctl` probe stays in the read, in the upstream `scanMountableMediaDrives` shape |
| X-protocol-security-7 | 9 (one guard on both doors, no `browser`; revision checked when sent, owner row). The route deletion is the boot-config-helpers theme |
| X-protocol-security-8 | 17, 18 (owner decision) |
| X-protocol-security-9 | not covered: the sudoers files and root helpers are the boot-config-helpers theme |
| UI-control-bridge-F1 | 11, 13 (`set_cdng_log` keeps `value=`, see For the owner) |
| X-knobs-19 | 15 |
| CC-1-F4 | 15 (the writer). `fps_speed_ramp_after=return\|stay` stays: it is an enum word, not a boolean spelling |
| HW-config-text-store-F9 | 6, 7 (the store keeps its refusal kind internally, only to pick the HTTP status) |
| HW-config-text-store-F8 | 7 |
| App-3-F4 | 7 (`old_page` goes; the header stays, upstream `x-preset-filename` shape) |
| App-3-F5 | 8 |
| App-3-F6 | 8 (the sentences) |
| Playback-F3 | 8 |
| WCP-10-F7 | 6 (the `"h"` fallback). Check stays on `set_controls` and Save on `POST /api/config`: both are upstream doors |
| HW-controls-model-F8 | 4 (`analog_targets` / `trigger_events` with no consumer: HW-controls-model-F6, hardware-inputs theme) |
| HW-controls-model-F16 | 1 |
| App-4-F13 | 1 (the parse-once part). The two `[cfexpress_hat]` parsers: hardware-inputs theme |
| App-4-F20 | 1 (no counter writes in a read), 5 (scan sentence), 4 (`catalogJson` members). `errno` in the media sentence and `stopMediaWatcher`: not this theme |
| App-4-F7 | not planned: owner decision; if taken, hardware-inputs theme |
| App-4-F19 | not covered: hardware-inputs theme; named at commit 1 |
| X-state-consistency-13 | 5 |
| X-state-consistency-8 | not fixed: named at commit 17 |
| App-1-F18 | 10 |
| Boot-config-F10 | 10 (the boolean part). The two `config.txt` readers: boot-config-helpers theme |
| App-5-F2 | 12, 13 (the `set_storage_preroll` argument). Renaming it and the four camera switches: owner decision, not planned |
| App-5-F5 | 16 (the reply). Moving the range table to a free function: not this theme (value-step lists) |
| App-5-F8 | owner decision, rides with 12/13 if taken |
| App-1-F8 | 9 (the `confirm_display` sentence). The install command in the helper sentence: boot-config-helpers |
| App-1-F13 | not covered: stays as the second pre-lock step until the safety-stop drain stops holding `commandMutex_` (buffer/safety-stop work) |
| X-protocol-security-6, X-state-consistency-11, App-5-F3 | already fixed by `e4246ee` "core: get_state sends media_state once" |
| X-protocol-security-2 | already fixed by `d1dcdee` (test_input refuses script actions) |
| WCP-09-F2 (`controlsCall`) | not covered: webui-state theme. Commits 1, 2 remove 5 of its call sites |
| UI-control-bridge-F2 (event branches) | not covered: touch-ui theme |
| App-1-F9 (nested Boot Config replies), App-1-F4, App-3-F1, WCP-10-F1, Boot-config-F1 | not covered: boot-config-helpers theme (route and engine). Commit 9 is compatible with either order |
| App-3-F11 (leading comma in state fragments) | not covered: storage-settings rewrites the blocks that use them |
| App-5-F1 (storage switches inline the store edit) | not covered: storage-settings theme. Commits 6 and 12 touch the same blocks; whoever lands second rebases |
| Camera-headers-F14 | not covered: camera-modes theme. The wire value of `set_cdng_log` does not change here |

## What the challenge changed

Old commit numbers are the first design's (1-20). New numbers are this page's.

| Point | Decision | Why |
| --- | --- | --- |
| a. Custom headers: "no route reads a custom header" | challenger right. Old 8 (new 7) keeps `X-Apertar-Revision`; only `old_page`, the codes and the WCP `code` branch go | Upstream reads `x-preset-filename` beside a raw body (`App:7396-7400`, `WCP:10472` @upstream-1.6.0). The precedent table now says so |
| a. Shell probe in a read | challenger right. Old 1 dropped; the probe stays in `controlsApplyJson` | `scanMountableMediaDrives` runs `lsblk` from a read with its own cache under its own mutex (`App:2266-2283` @upstream-1.6.0) |
| b. The 2 s worker turn | challenger right. Old 1 dropped; App-4-F7 goes on the owner's list, owner theme hardware-inputs | No take gate before `if (text == applied) continue;` (`App:12264-12266`); a unit stays pending until restarted (`App:12376-12381`), so old 1 would fork `systemctl` every 2 s during takes |
| b. Listen poll under the lock | challenger right. New 5 turns the loop into a `setTimeout` chain, plus a take-stop Pi check | `setInterval(async ...)` does not await (`WCP:18695-18720`) |
| b. Second lenient parser | challenger right, and more: new 10 also refuses a misspelt `dry_run`/`confirm_display` | `parseBooleanToken` reads four `set_controls` flags (`App:12786-12812`); `.value_or(false)` at `App:3781-3782` turns a typo into a write |
| a. Which boolean form | challenger right. Strict for flags that decide a write (new 10), lenient for the plain pre-roll switch (new 12), each named | Conventions section 4: lenient for a plain switch (`App:9486`), strict where a wrong value must be refused (`App:9131`) |
| f. Rename hidden in old 14 | challenger right. New 12 keeps `set_storage_preroll`, takes `enabled=`; the rename joins the four camera switches on the owner's list | `set_standby_usb_power_off enabled=` (`App:9128` @upstream-1.6.0); CMD-7 is "usually" |
| c. Old 16 and mixed installs | challenger right, and more. ISO part dropped; new 14 deletes only the file-timecode guess | The reply itself goes through `applyCoreMessage` (`ACB:1210`) to `applyCoreState` (`ACB:1411`) before `sendCoreCommand` returns, so Lock already shows Core's value; the guess at `ACB:766-769` repeats what the reply set |
| d. Order of old 5 and 6 | challenger right. `list_actions` trim (new 4) before the lock move (new 5) | 5 then moves a 3-line block |
| d. Old 12 leaves a warning | challenger right. Folded into new 9, the last caller's commit | `errorReplyBody` is in the anonymous namespace (`App:82`, `:173`); `check_core.sh:13-16` builds with `-Wall -Wextra` and counts warnings |
| b. Check tools read the moved commands | challenger right. New 1 and 2 name the `smoke_core.sh:35-36` and `controls_page_test.js:67-70` changes; the page check runs against `--simulate` | Both tools call `get_controls`/`controls_history` today |
| b. `GET /api/config` gets heavier | partly right. The cost is named in new 1; the one-fetch-for-both-cards option is left to webui-state | Confirmed two builds per Settings open (`WCP:10167-10171`) and after saves. No lock, no take path. Merging the two fetches is that theme's poll work |
| c. Stock Pi 4 hat row | challenger right. Named in new 1's stock line; App-4-F19 stays with hardware-inputs | `cfeHatPeripheralJson` always emits a row (`App:12091-12103`) |
| f. Hidden owner decision in old 10 | partly right. Not left as a hidden rule and not required on both doors: new 9 checks the revision when sent, on both doors, as new 7 does for the config text; the stricter rule is an owner row | One rule for both whole-file saves, nearest 1.6.0 (last writer wins without a revision); the owner's scripts keep working (`App:14605-14606`) |
| f. Two paths for the hardware file | challenger right. Risk deleted; the one-path fact is in "How it works" | `HardwareConfigStore.cpp:118-123` and `App:4944-4949` name the same file |
| e. App-3-F6 left behind | challenger right. New 8's lambda writes upstream-family sentences | Same seven bodies (`App:8503`, `:8573`, `:8691`, `:8820`) |
| a. 410 for a removed clip | challenger right (stands as new ground) | An HTTP status replaces the `gone` member |
| g. Optional event vs `settings` event | challenger right. New 17 says why; X-state-consistency-8 named, not fixed | `emitSettingsEventLocked` serialises `settings_` (X-state-consistency-8) |
| g. Pi checks that cannot run as written | partly right. The safe wiring is in new 3. The errno list is dropped instead of measured: new 3 bounds the scan by time, which holds on every adapter | Which errno each adapter gives is unknown here; a time bound (`App:2979-2980` @upstream-1.6.0) needs no errno list. The `strace` measurement stays in Risks to size the worst case |
| e. `test_input` inside `handleCommand` | challenger right. Stands; placement is an owner row | Only page client `WCP:16920`; moving it to `handleWebCommand` takes it from `core.py` |
| c. Rig and stock per commit | challenger right. Every commit has a "Rig sees / Stock sees" line; new 15 has the downgrade note | `core-main CC:710-711` reads `true` or `1` |
| Not raised: WCP-10-F7, HW-config-text-store-F8, Boot-config-F10, App-5-F1 | taken along (6, 7, 10) or named (App-5-F1, storage-settings) | Same mechanism, found with `finding.py --grep` |
