# The command plane: one dispatcher, one reply shape: design

Read at Core `/home/user/wt/core-work` `d1dcdee` (with uncommitted preview-TDN edits by another lane, not touching this theme), UI `/home/user/wt/ui-work` `ac1fc28`; measured against Core `/home/user/wt/core-upstream` and UI `/home/user/wt/ui-upstream` at `upstream-1.6.0`. All port line numbers are at these heads.

## In short

1. Today, five hardware commands are answered by a second dispatcher, `handleReadOnlyHardwareCommand`, before `handleCommand` takes `commandMutex_`. Two of them (`get_controls`, `controls_history`) only read the hardware file, which `GET /api/config` already serves.
2. A third reply builder, `errorReplyBody`, puts machine codes (`"code":"stale"`, `old_page`, `confirm_display`, ...) and arrays into `ok:false` replies, in 14 places. The WebUI branches on those codes in 4 places.
3. Smaller drift: playback routes hand-build their error JSON. The pre-roll switch sends `value=on|off`. Six new touch-UI invokables return `void`. The Boot Config fields accept `on/yes`. Port switches are written `true/false` in `camera_settings.conf`. The touch UI trusts its own guess after ISO Lock and the timecode target.
4. Target: reads of the hardware file become `GET /api/config` and `GET /api/config/history`. These are lock-free web routes, as upstream serves every read that must not wait. `controls_last_input`, `scan_i2c` and `list_actions` become ordinary blocks under the lock. `test_input` stays the one pre-lock branch, because it re-enters `handleCommand`.
5. Every refusal is `errorReply(id, sentence)`. `errorReplyBody` is deleted. A stale save is refused with a sentence, and the page reloads.
6. Booleans travel as `enabled=true|false`, invokables return `bool`, and the file writes `0/1`.
7. 18 commits (15 Core, 3 UI), plus 2 optional ones for the owner (1 Core, 1 UI). Estimated net: Core about -170 / +150 lines, UI about -25 / +35.

## How it works in the port today

The command plane is the path a request takes to change or read camera state. Upstream has one door, `handleCommand`, under one mutex. The port has these pieces:

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| `handleCommand` entry, `App:12576` | socket `App:8092`, `POST /api/command` `App:9218`, hardware inputs `dispatchHardwareInputCommand` `App:10121`, idle timer `wait()` `App:8289` | - | caller's thread. `commandMutex_` is taken at `App:12588`, after three pre-lock steps at `App:12578-12587` | - | - |
| `get_controls`, `App:12430-12474` | writes `controlsErrors_`/`controlsWarnings_` (`App:12434-12436`). Through `controlsApplyJson` `App:12359-12385` it runs `systemctl show` once per pending unit and erases `pendingUnitSince_`. Parses the file 8 times (`App:12447-12461`) | WCP `loadControls` `:18334`, `controlsRecheckSoon` `:18589` | socket or web thread, **no `commandMutex_`**. Atomics plus `controlsWorkerMutex_` | reads `~/apertar-hardware.conf` through `HardwareConfigStore` | WebUI Settings > Controls and Hardware cards |
| `controls_history`, `App:12475-12491` | `HardwareConfigStore` writes history files on each save | WCP `:18627`, `:18654` (Undo), `:18966` (Config history) | no `commandMutex_` | hardware-history directory | Config history list, Undo |
| `controls_last_input`, `App:12493-12501` | `noteInputSeen` from the input threads, under `lastInputMutex_` | WCP Listen loop, every 300 ms, `:18700` | `lastInputMutex_` only | none | Controls "Listen" |
| `scan_i2c`, `App:12503-12549` | - | WCP Hardware card `:18256` | no `commandMutex_`. Checks `recordingGateActive()` once, then makes up to 117 one-byte reads | none | Hardware card bus scan |
| `list_actions`, `App:12551-12572` | static catalog `ActionCatalog.hpp:336-358` + `camera_.settings()` + UI.conf | WCP `:18335`, cached once. Only `actions` is read (`:16751`, `:16823`, `:16877`, `:18056`, `:18505`) | no `commandMutex_` | reads UI.conf | Controls action pickers |
| `test_input`, `App:12582` -> `testInputReply` `App:12399-12424` | - | WCP Try / Remote controls `:16920` | before the lock. It calls `handleHardwareInputAction`, which takes `hardwareActionMutex_` then `commandMutex_` (`App:10121`) | reads hardware file | Try buttons |
| `abortSafetyStopFlushForRecord`, `App:12587`, `App:10123` | - | - | lock-free, before both mutexes | - | - |
| `GET /api/config`, `App:8617`, builder `buildHardwareConfigFileJson` `App:6185-6233` | - | WCP `fetchConfigFile` `:18812` | web thread, no `commandMutex_` | hardware file | Config text editor |
| `POST /api/config`, `App:8624-8684` | WCP save `:18994` with header `X-Apertar-Revision` `:18993` | - | web thread, store mutex | hardware file, `.bak`, history | 409 with `code` `old_page`/`stale`/`conflict`/`merge_review` |
| `errorReplyBody`, `App:173-184` | Boot Config `App:3780-3835` (`invalid`, `unreadable`, `old_page`, `stale`, `refused`, `confirm_display`, `permission`, `write_failed`). `/api/config` `App:8640`, `:8657`. `set_controls` `:12818`. `set_buffer_mode` `:12858`. `set_frames_per_folder`/`set_clip_merge` `:12898`. `set_storage_preroll` `:12932` | WCP branches on `code` at `:18303`, `:18732`, `:19019`, `:20400`. `issues`/`new_errors` read at `:18302`, `:18731`, `:18869`, `:19018`. `conflicts` read nowhere | - | - | toasts and card messages |
| Store refusal codes, `HardwareConfigStore.hpp:25-38`, `.cpp:261-368` | the store | App maps them to HTTP status (`App:8648-8651`) and sends them on the wire | store mutex + `QtIniLock` | - | - |
| Playback error bodies, `App:8503`, `:8510`, `:8533`, `:8536`, `:8573`, `:8691`, `:8820` | hand-built `"{\"ok\":false,...}"`, with `hold`, `gone`, or `busy` and no sentence | WCP `pbvFetchFrame` reads only status 409/503/404 and `body.gone` (`:12355-12361`) | web threads | - | playback viewer |
| `set_boot_config` guard, `bootConfigSet` `App:3775` | `POST /api/boot-config` passes `browser = Origin present` (`App:9197`). The socket command passes `false` (`App:14606`) | - | `bootConfigMutex()` `App:3513` | `/boot/firmware/config.txt` | Boot Config card |
| Boot Config booleans, `boolFieldValue` `App:3709-3718` | WCP `bootConfigRequestBody` `:20057` (JSON booleans) | `bootConfigRequestFrom` `App:3746`, `dry_run`/`confirm_display` `App:3781-3782` | - | - | - |
| `set_storage_preroll value=on\|off`, `App:12917-12944` | WCP `:15843`, patch `:14030`. UI `ACB:627` | buffer state `storage_preroll_auto` `App:261` | `commandMutex_` | `[media] preroll=` in the hardware file | WebUI Media card, touch UI Media |
| `set_cdng_log value=auto\|off`, `App:13095` | WCP `:15451`. UI `ACB:718` | state `cdng_log` (string) `App:356` | `commandMutex_` | `camera_settings.conf cdng_log=` | Record settings |
| Port switches in `camera_settings.conf`, writer `CC:963`, `:974-979` | `CameraController` persist | reader `CC:870`, `:886-896` (accepts `true` or `1`) | CC mutex | `camera_settings.conf` (`true`/`false`) | - |
| Touch UI invokables `UI hpp:194-200`, `ACB:618-630`, `:686-701`, `:716-727` | QML `SettingsPage.qml:3439`, `:3447`, `:3480`, `:5605`, `:5628`, `:5635`, `ClipNameCard.qml:169`, `:335` | - | GUI thread, blocking send | - | `lastError` only |
| ISO Lock `ACB:300-308`, timecode target `ACB:750-771` | QML | m_isoAuto not changed after Lock. `m_fileTimecodeMode` set from `target`, not from Core | GUI thread | UI.conf `timecodeMode` | camera page |
| Live-value poll, `ACB:16-20`, `:1015-1016` | - | `get_state` every 1 s while auto ISO or auto WB is on (30 s otherwise) | each poll takes `commandMutex_`. The HDMI process doubles the rate | - | ISO/WB in use on screen |
| `set_value_steps` reply, `App:14178` | - | WCP `:8494` does not read the reply | `commandMutex_` | UI.conf | - |

Why `get_controls` was put before the lock (comment `App:12578`): "so a slow one never holds up a button". It is not read-only. It spawns `systemctl` and writes counters.

Why `test_input` must stay before the lock (confirmed): `handleHardwareInputAction` -> `dispatchHardwareInputCommand` (`App:10121`) -> `handleCommand` -> `commandMutex_`. A `std::mutex` is not re-entrant, so running `test_input` under the lock would deadlock.

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent |
| --- | --- |
| One command door | `handleCommand` takes `commandMutex_` on its first line (`App:9091-9093`). It is one flat `if (command.name == ...)` chain ending in "Unknown command" (`App:10820`). Socket `handleRequest`, `handleWebCommand` (`App:7085-7091`), hardware inputs (`App:8458-8466`) and the idle timer all enter it. |
| An entry that calls `handleCommand` from outside | `dispatchHardwareInputCommand` takes `hardwareActionMutex_`, then calls `handleCommand` (`App:8458-8466`). `handleWebCommand` parses, then calls it (`App:7085-7091`). This is the shape `test_input` has: a source of commands, not a command body. |
| A read that must not wait for the command lock | An HTTP GET route on the web server's per-connection thread (`WS:276-287`), with no `commandMutex_`. Examples: `GET /api/state` -> `buildWebStateJson() const` (`App:7711`), `GET /api/config` -> `buildHardwareConfigFileJson()` (`App:7168-7173`, `App:5290-5321`), `GET /api/media`, `GET /api/presets` (`App:7360`). In upstream only three places take `commandMutex_`: `App:7032`, `App:9093` and, indirectly, `App:8460`. |
| Slow work that must not hold the lock | A worker thread with its own state group; the client polls a status command. Example: the media speed test, `startMediaSpeedTest` `App:8957-9009`, status reply `App:10610-10614`. Slow work that does hold the lock is an accepted rough edge (format, gyro calibration; conventions section 4). |
| Route parameters | The query string, read with `queryParameterValue` (`App:7198-7199`, `App:7396`, `App:7441`). No route reads a custom header. |
| Replies | `okReply(id, fragment)` and `errorReply(id, sentence)` only (`App:108-128`). Routes reuse them with id -1 and set an HTTP status 400/404/500/503 (`App:7178-7183`, `App:7647`). No reply carries a `code` member. |
| A whole-file save | `POST /api/config` -> `saveHardwareConfigFile(text, &backup, &errorMessage)` (`App:5323`, `App:7175-7195`). It is a fallible helper with `bool` + `std::string *errorMessage`, and returns 400 + `errorReply` on failure. |
| Booleans in a command | `enabled` tested `*enabled == "true" \|\| *enabled == "1"` (`App:9482-9486`), with a strict form where a wrong value must be refused (`App:9130-9133`). Commands are named `set_<thing>_enabled`. |
| Enum settings in a command | `value=<toString(enum)>`, e.g. `set_cdng_compression` (`App:9340`). The state key carries the same string. |
| Booleans in `camera_settings.conf` | `output << prefix << "iso_auto=" << s.isoAuto` writes `0/1` (`CC:749`). Read with `std::stoul(value) != 0` (`CC:659-660`). |
| Touch UI command invokables | Return `bool`. Thin variants are `return sendCoreCommand(...)` (`UI ACB:736-741`). Booleans go out as `enabled="true"/"false"` (`UI hpp:133-136`). Only `notifyUserActivity` and `refresh` are `void` (`UI hpp:100`, `:110`). |
| UI takes Core's reply as the truth | After `apply_preset`, the UI calls `applyCoreState(reply.value("state"))` (`UI ACB:1155-1162`). Events whose fields are state keys go whole to `applyCoreState` (`UI ACB:1191-1195`). |
| Periodic supervision and periodic events | The 1 Hz loop in `wait()` (`App:7025-7040`). Live values pushed as literal events, e.g. `audio_level` (`App:8383`). |
| Mixed versions | Core and UI ship together. There is no protocol version; missing fields default (`README.md:306`, CMD-30). |

## The target

| Thing | Before (port today) | After |
| --- | --- | --- |
| Command entry | `handleReadOnlyHardwareCommand` (5 commands) + `test_input` + safety-stop abort before the lock | One chain under `commandMutex_`. Before the lock: `test_input` (it re-enters `handleCommand`), with one comment line, and `abortSafetyStopFlushForRecord` (unchanged; see Risks) |
| Hardware file + Controls model, for the page | socket command `get_controls`, nested `"controls":{...}`, not under the lock, spawns `systemctl` | `GET /api/config`, the upstream route. Upstream fields stay (`path`, `display_path`, `exists`, `size_bytes`, `size_text`, `modified_text`, `text`), plus the port fields the page reads: `revision`, `written_by`, `written_at`, `errors`, `warnings`, `issues`, `replaced`, `model`, `peripherals`, `i2c_buses`, `apply`, `dpi_lines`, `gpio_chips`. Built by the member `buildHardwareConfigFileJson()` in App. It parses once and writes nothing |
| Which services still read the old file | probed by `systemctl show` inside `get_controls` | probed by the controls worker every 2 s while a unit is pending (`runControlsWorker`). `controlsApplyJson` only reads |
| Saved versions | `controls_history [name=]` | `GET /api/config/history` (list) and `GET /api/config/history?name=<file>` (one text), like `GET /api/presets` + `?name=` |
| Last input (Listen) | pre-lock command | same command, ordinary block under the lock |
| I2C scan | pre-lock; a take can start mid-scan | ordinary block under the lock, refused during a take. It stops at the first transfer error that is not "no answer" |
| Action catalog | pre-lock. Reply also carries `values`, `values_for`, `gestures`, which nobody reads | ordinary block under the lock, `"actions":[...]` plus the catalog's own members |
| Error replies | `errorReplyBody` with `code`, `revision`, `issues`, `new_errors`, `conflicts`, `drm` | `errorReply(id, sentence)` everywhere. The sentence says what to do ("Reload, then change it again."). HTTP routes keep their status (400/409/500/503, 410 for a removed clip). The store's refusal kind stays inside Core; it only picks the HTTP status |
| Validation details | in `ok:false` replies | in `ok:true` replies only. A `dry_run` (the Config "Check" button) answers `ok` with `issues` and `new_errors`. A refused save says how many new errors there are and names the first |
| Revision of a config text save | `X-Apertar-Revision` header, `old_page` when an Origin is present and the header is missing | `POST /api/config?revision=<r>`. Stale -> 409 + sentence. Missing -> last-writer-wins, as in 1.6.0 |
| `set_boot_config` revision | needed only on the HTTP door with an Origin header | needed on every save that is not a dry run, on both doors. The `browser` parameter and `old_page` go. Deleting the route is the boot-config-helpers theme's job |
| Boot Config booleans | `boolFieldValue` accepts `on/yes/off/no` | the strict upstream test: `true`/`1`, `false`/`0`, otherwise "`<field>` must be true or false." |
| Pre-roll auto switch | `set_storage_preroll value=on\|off` (lower-cased) | `set_storage_preroll_enabled enabled=true\|false`, strict test. Stored value and state key unchanged |
| CinemaDNG log | `set_cdng_log value=auto\|off` | unchanged on the wire: it is an enum setting with a string state key (`cdng_log`), like `set_cdng_compression`. Only the invokable changes |
| Touch UI invokables | six `void` | `bool`. `startStoragePreroll()`, `applyStoragePrerollAutoEnabled(bool enabled)`; the rest keep their names |
| Port switches in `camera_settings.conf` | `true`/`false` | `0`/`1`, as `iso_auto`. Readers keep accepting both |
| ISO Lock, file timecode in the UI | set from the UI's own guess | set from Core's reply (`iso_auto`, `iso`, `timecode_mode`) |
| `set_value_steps` reply | `"ui":{...}` | the same members, flat, like `set_sleep_mode` / `set_favorites_order` |
| Live ISO/WB in use (optional) | `get_state` every 1 s | Core's 1 Hz loop publishes one event when the value in use changes. The UI keeps the 30 s poll |

Who owns what after the change: the hardware file stays owned by `HardwareConfigStore` (writes) and App (reads for the page). UI.conf and `camera_settings.conf` ownership is unchanged. No value moves to another file, so no key needs taking over. The only file change is how six booleans are spelled, and both spellings stay readable.

How values reach the UIs: the WebUI reads the hardware file and model only through `GET /api/config`, and commands only through `POST /api/command`. The touch UI never used the moved commands (`grep` in `ui-work/src`, `ui-work/qml`: no hits), so it sees no change except the invokables and the pre-roll command name.

## Commit plan

Checks named below:
- **build**: `/home/user/build/bin/check_core.sh /home/user/wt/core-work <tag> both tests`. This builds with and without libcamera and runs the 17 host tests.
- **smoke**: `/home/user/build/bin/smoke_core.sh <build>/apertar-core <port>`, diffed against the previous commit's output. Every 1.6.0 field must keep its type.
- **page**: `apertar-core --simulate` plus headless Chromium on the named card.
- **ui build**: `/home/user/build/bin/check_ui.sh`.

1. **core: the controls worker checks which services picked up a save**
   - Repo: Core. Files: `App` `runControlsWorker` (`:12250`), `controlsApplyJson` (`:12359`).
   - Moves: the `systemctl show -p ActiveEnterTimestampMonotonic` loop and the `pendingUnitSince_.erase` from `controlsApplyJson` into the worker's 2 s turn. The worker runs it before its `if (text == applied) continue;`, only when `pendingUnitSince_` is not empty. `controlsApplyJson` then only copies state under `controlsWorkerMutex_`.
   - Lines: -14 / +16.
   - Here: build; smoke (the `apply` object keeps its shape).
   - Pi only: save a `[ina219]` change in Controls, then `sudo systemctl restart <unit>`. The "still reads the old file" row must clear within 2-4 s.
   - Depends on: nothing.

2. **core, web: the Controls page reads the hardware file through GET /api/config**
   - Repo: Core. Files: `App` `buildHardwareConfigFileJson` (`:6185`) becomes the member `std::string buildHardwareConfigFileJson()`, declared in `AppH` next to the other `build*Json`. The `get_controls` block (`:12430-12474`) is deleted, and `"get_controls"` comes out of the `help` literal. WCP: `loadControls` (`:18334`) and `controlsRecheckSoon` (`:18589`) call `fetch("/api/config", { cache: "no-store" })`. `controls.controls.X` becomes `payload.X`.
   - Moves: the member list of `get_controls` into the builder. `hwconf::parse(info.text)` runs once into `const hwconf::Document doc`. The model, peripherals and issues are of the file Core runs (`info.text`). `text` stays upstream's editor text (file, `/boot` copy or template).
   - Deletes: the counter writes `controlsErrors_ = ...` (`:12434-12436`). The worker (`:12337`) and the saves keep them current.
   - Lines: App -50 / +40, WCP -8 / +8.
   - Here: build; smoke (all 1.6.0 `/api/config` fields present, same types); page: Settings > Controls loads, rows render, Hardware card lists peripherals; `curl /api/config | jq .model.rows[0]`.
   - Pi only: open Controls while a take runs. The page loads and the take drops no frames (`recording_dropped_frames` stays 0 in `/api/state`).
   - Depends on: 1 (so the route spawns no process).

3. **core, web: saved hardware-file versions come from GET /api/config/history**
   - Repo: Core. Files: `App` `handleWebRequest`, one branch before `/api/command`: `GET /api/config/history`, with `queryParameterValue(request.query, "name")` for one version. `okReply(-1, ...)`, or 404 + `errorReply(-1, "No saved version called <name>.")`. The `controls_history` block (`:12475-12491`) is deleted, and it comes out of `help`. WCP: `:18627`, `:18654`, `:18966` use one `async function fetchConfigHistory(name)` in the R10 step 6 shape.
   - Lines: App -18 / +20, WCP -6 / +12.
   - Here: build; page: Config > History lists versions, picking one loads its text, Undo in Controls restores.
   - Pi only: nothing beyond the page check.
   - Depends on: nothing.

4. **hw: an I2C scan stops when the bus does not answer**
   - Repo: Core. Files: `src/hardware/I2cProbe.cpp` (`probeI2cAddress`) and `App` `scan_i2c`.
   - Adds: when `read` fails with an errno other than `ENXIO`/`EREMOTEIO` (the "nobody at this address" answers), set `probe.error`. `scan_i2c` returns `errorReply` with "I2C bus N does not answer: check the wiring." at the first such error.
   - Why: after commit 5 the scan holds the command lock. A stuck bus (SDA held low) costs one adapter timeout per address, up to 117 of them.
   - Lines: -1 / +6.
   - Here: build. The probe needs real `/dev/i2c-*`, so here only the compile is checked.
   - Pi only: `python3 ~/apertar-kb/working/tools/core.py scan_i2c bus=1` on a healthy bus lists the same addresses as `i2cdetect -y -r 1`. Time it: `time core.py scan_i2c bus=1` should be well under 1 s on Pi 4 and Pi 5. With the bus shorted to ground (bench only), it must return the sentence after one timeout.
   - Depends on: nothing.

5. **core: controls_last_input, scan_i2c and list_actions take the command lock like every command**
   - Repo: Core. Files: `App`.
   - Moves: the three blocks (`:12493-12572`) into the chain next to `test_output` (`:12762`).
   - Deletes: `handleReadOnlyHardwareCommand` and its declaration (`AppH:83`), and the call at `:12579`.
   - Keeps: `test_input` before the lock, with one comment line: "test_input runs a control's actions, which enter handleCommand themselves." The refusal becomes "scan_i2c requires bus." (C1-I07 form). `"test_input"` is added to `help`, next to `test_output`.
   - Lines: -12 / +8 (the rest is a move).
   - Here: build; page: Listen highlights a row on `test_input`; scan and pickers work.
   - Pi only: start a take, press Listen and turn a knob. The row lights within about 0.3 s and the take is unaffected. A scan during a take is refused with the existing sentence.
   - Depends on: 4.

6. **core: list_actions answers the action list only**
   - Repo: Core. Files: `App` `list_actions`; `src/hardware/ActionCatalog.hpp` `catalogJson` (`:336`).
   - Deletes: `values`, `values_for`, `gestures`, and the `substr(1, size-2)` brace strip (`:12558`). `catalogJson` returns members without braces, so the reply is `okReply(id, catalogJson())`. The command no longer reads UI.conf or camera settings.
   - Lines: -16 / +2.
   - Here: build; page: action pickers list the same actions.
   - Pi only: nothing.
   - Depends on: 5.

7. **core, web: hardware-file refusals are one sentence**
   - Repo: Core. Files: `App` `set_controls` (`:12816-12822`), `set_buffer_mode` (`:12856-12860`), `set_frames_per_folder`/`set_clip_merge` (`:12896-12900`), `set_storage_preroll` (`:12930-12934`). Store: `HardwareConfigStore.cpp:336`. WCP: `saveHardwareSettings` (`:18300-18306`), `saveControls` (`:18729-18735`).
   - In App: `errorReplyBody(...)` becomes `errorReply(command.id, result.error)` in all four commands.
   - In the store: the "new errors" refusal is skipped on a dry run (`&& !flags.dryRun`), so Check gets `ok:true` with `issues` and `new_errors`. The `set_controls` ok body adds `"new_errors":...`. The conflict sentence gains "Reload, then change it again.", as the two stale sentences already say.
   - In WCP: the `kept` code branches and the `found` lists on refusal are deleted; the message is Core's sentence. `checkConfigFile` (`:18864`) needs no change: its `!result.ok` branch now only sees real refusals.
   - Lines: App -22 / +5, store -1 / +2, WCP -8 / +2.
   - Here: build; page: save a Controls edit with a pin clash, which is refused with "Not saved: 1 new error. ..."; Check on the same text lists the errors; save from two tabs, and the second is refused with "... Reload, then change it again."
   - Pi only: nothing.
   - Depends on: 2 (the cards reload through `/api/config`). Coordinate with **storage-settings**: if it moves `set_buffer_mode`/`set_frames_per_folder`/`set_storage_preroll` out of the hardware store first, only `set_controls` is left here.

8. **core, web: the config text save names its revision in the query string**
   - Repo: Core. Files: `App` `POST /api/config` (`:8624-8684`), WCP `saveConfigFile` (`:18988-19024`).
   - Moves: the revision from the `X-Apertar-Revision` header to `?revision=` via `queryParameterValue`.
   - Deletes: the Origin/`old_page` 409 (`:8635-8643`), `errorReplyBody` at `:8657`, and the WCP `code` branch (`:19019`). A refusal keeps its status (409 for stale/locked/being written/conflict/merge review, 400 otherwise), and the body is `errorReply(-1, message)`.
   - Lines: App -14 / +6, WCP -8 / +3.
   - Here: build; page: save, then save again from a second tab, which is refused with a sentence and the text stays in the box; `curl -X POST --data-binary @f 'http://127.0.0.1:PORT/api/config'` without a revision still saves (1.6.0 behaviour).
   - Pi only: nothing.
   - Depends on: 7.

9. **core, web: playback routes refuse through errorReply**
   - Repo: Core. Files: `App` `handleWebRequest` sites `:8503`, `:8510`, `:8533`, `:8536`, `:8573`, `:8691`, `:8820`; WCP `pbvFetchFrame` (`:12355-12361`).
   - Adds: one local lambda `holdResponse(const std::string &hold, const char *what)`, which returns a 409 `WebServer::Response` with `errorReply(-1, sentence)` (CMD-25 named local lambda).
   - Changes: busy becomes 503 + `errorReply(-1, "Playback is busy. Try again in a moment.")`. A removed clip becomes 410 + `errorReply(-1, "This clip was removed.")`. WCP: `if (response.status === 410) return { outcome: "gone" };`, and 404 means stale.
   - Lines: App -14 / +16, WCP -3 / +2.
   - Here: build; page: start playback in `--simulate`, delete the clip from another tab, and the viewer shows "removed". Start a take and the viewer holds.
   - Pi only: play a clip, press record; playback stops before the first frame is written and the take has no drops.
   - Depends on: nothing.

10. **core: Boot Config refusals are one sentence and every save names its revision**
    - Repo: Core. Files: `App` `bootConfigSet` (`:3775-3841`), its two callers `:9197`, `:14606`; WCP `saveBootConfig` (`:20390-20405`).
    - Changes: every `errorReplyBody` becomes `errorReply`. The status in `BootConfigReply` stays for the route until boot-config-helpers deletes it. The `browser` parameter goes. A non-dry-run save without a revision is refused: "config.txt changed since the card loaded it. Reload the card and choose again." `old_page` is gone. The display guard keeps refusing, with "This changes the display overlays (...). set_boot_config needs confirm_display=true for that." The card always sends `confirm_display` from its review, so the card never sees it. WCP: on any refused save the card reloads (`loadBootConfig(true, false, true)`, which keeps the choices). The `code` test goes.
    - Lines: App -20 / +10, WCP -2 / +1.
    - Here: build; host test `boot_config_test` passes; page: Boot Config review and save in `--simulate` (writes to the simulated path), and a stale save from a second tab reloads the card.
    - Pi only: the owner's CM5: change a sensor link, save, reboot, and check `vcgencmd get_config` / `/boot/firmware/config.txt`. A Pi 4 with the stock 720x720 DPI screen: a change that drops the DPI overlay must be refused by `core.py set_boot_config ...` without `confirm_display=true`.
    - Depends on: nothing. **boot-config-helpers** deletes `POST /api/boot-config` and `BootConfigReply`; either order works.

11. **core: Boot Config switches read true or 1, as every command does**
    - Repo: Core. Files: `App` `boolFieldValue` (`:3709-3718`) and its three callers.
    - Deletes: the lower-casing and `on/yes/off/no`. The strict test stays: `"true"`/`"1"`, `"false"`/`"0"`, else "`<field>` must be true or false."
    - Lines: -8 / +4.
    - Here: build; `boot_config_test`; page: the card's toggles still save (JSON `true` arrives as `true`).
    - Pi only: nothing.
    - Depends on: nothing.

12. **core: errorReplyBody is gone**
    - Repo: Core. Files: `App:173-184`.
    - Deletes: the function. `grep -n errorReplyBody src` must be empty before this commit.
    - Lines: -12 / +0.
    - Here: build.
    - Pi only: nothing.
    - Depends on: 7, 8, 10.

13. **ui: the new control invokables return bool**
    - Repo: UI. Files: `src/ApertarControlBridge.hpp:194-200`, `ACB:618-630`, `:632-659`, `:686-701`, `:716-727`.
    - Changes: `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto`, `applyClipNameTemplate`, `requestClipNamePreview` and `applyCdngLog` return `bool`. They return `false` after `setLastError` or a failed send and `true` at the end. The thin ones are `return sendCoreCommand(...)`. No wire change, and QML ignores the results.
    - Lines: -12 / +16.
    - Here: ui build; the touch UI builds and the QML loads (offscreen).
    - Pi only: on the 720x720 screen and on the owner's HDMI monitor, toggle Log, write buffer, clip name; a refusal still shows its sentence.
    - Depends on: nothing.

14. **core, web: the automatic pre-roll switch is set_storage_preroll_enabled with enabled=**
    - Repo: Core. Files: `App` block `:12917-12944` and `help`; WCP sender `:15843` and patch case `:14030`.
    - Changes: the command reads `enabled` with the strict upstream test. The `tolower` loop goes. The stored `[media] preroll=on|off` and the state key `storage_preroll_auto` are unchanged.
    - Lines: -8 / +6.
    - Here: build; page: the Auto pills switch and survive a reload.
    - Pi only: nothing beyond the touch UI check in 15.
    - Depends on: 7. Lands together with 15 (Core and UI ship together, CMD-30). Coordinate with **preroll** (it may also rename `storage_preroll`; see For the owner) and **storage-settings** (it may move where `preroll=` lives; the command shape here does not depend on that).

15. **ui: the pre-roll switch sends set_storage_preroll_enabled**
    - Repo: UI. Files: `hpp:195-196`, `ACB:618-630`, `qml/SettingsPage.qml:5605`, `:5628`, `:5635`.
    - Renames: `applyStoragePreroll()` becomes `startStoragePreroll()` (an action is a verb, UIC-10). `applyStoragePrerollAuto(bool on)` becomes `applyStoragePrerollAutoEnabled(bool enabled)`, which sends `enabled="true"/"false"`.
    - Lines: -8 / +8.
    - Here: ui build.
    - Pi only: touch UI Media > Pre-roll Auto On/Off, then `core.py get_state`, which shows `storage_preroll_auto` following.
    - Depends on: 13, 14.

16. **ui: ISO Lock and the file timecode follow Core's reply**
    - Repo: UI. Files: `ACB` `applyIso` (`:300-308`), `applyTimecodeMode` (`:750-771`).
    - Changes: both pass `&reply`. Lock sets `m_isoAuto` and the ISO from `reply["iso_auto"]` / `reply["iso"]`, as `applyCoreState` does. The timecode sets `m_fileTimecodeMode` from `reply["timecode_mode"]`, not from `target`. With a 1.6.0 Core the UI then shows what Core did (ISO stays Auto) instead of a false success.
    - Lines: -4 / +10.
    - Here: ui build.
    - Pi only: auto ISO on, Lock. The ISO shown is the locked value and matches `core.py get_state` `iso`. Set the screen timecode only, and the Record page's file timecode is unchanged.
    - Depends on: nothing.

17. **camera: the new camera switches are written 0 and 1 in camera_settings.conf**
    - Repo: Core. Files: `CC` `writeCaptureSettings` `:963`, `:974-979`.
    - Changes: `<< s.member` for `clear_hdr`, `fps_phase_lock`, `preview_tdn`, `media_trim`, `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `fps_speed_ramp_stretch_audio`. The readers (`CC:870`, `:886-896`) already accept `true` and `1`, so files written by the port keep loading. A file is rewritten in the new spelling at the next settings commit (the 25 ms debounced persist), the way upstream rewrites the whole file on every change.
    - Lines: -7 / +7.
    - Here: build; `--simulate` with a `camera_settings.conf` holding `preview_tdn=true`; change any setting; the file now says `preview_tdn=1` and `get_state` still says `"preview_tdn":true`.
    - Pi only: nothing.
    - Depends on: nothing. Coordinate with **storage-settings** if it moves any of these keys.

18. **core: set_value_steps echoes the lists flat**
    - Repo: Core. Files: `App:14178`.
    - Changes: `okReply(command.id, valueStepsJson(...))` without the `"ui":{...}` wrapper. Same members, like `set_sleep_mode`. No reader of the reply exists (WCP `:8494` awaits it only).
    - Lines: -1 / +1.
    - Here: build; `curl -d '{"cmd":"set_value_steps","name":"iso","free":"true"}' /api/command`.
    - Pi only: nothing.
    - Depends on: nothing.

19. **(optional, owner) core: the ISO and white balance in use go out as an event**
    - Repo: Core. Files: `App` `wait()` (`:8289-8318`).
    - Adds: after the recording-failure check, when `isoAuto || whiteBalanceAuto` and the measured ISO or kelvin differs from the last one sent, `publishEvent("{\"event\":\"exposure_in_use\",\"iso_actual\":N,\"wb_actual_kelvin\":K}")`. These are state keys; the event is literal (CMD-17). The 1 Hz loop already exists (CMD-21).
    - Lines: +10.
    - Here: build; `--simulate` socket client sees the event only while auto is on.
    - Pi only: auto ISO on, pan from dark to bright; the event follows within 1 s.
    - Depends on: nothing.

20. **(optional, owner) ui: the touch UI keeps the 30 s poll while auto ISO or WB runs**
    - Repo: UI. Files: `ACB:16-20`, `:1015-1016`, and the event list at the `applyCoreState` event branch.
    - Changes: `exposure_in_use` joins the events that go whole to `applyCoreState`. `kLiveValuePollIntervalMs` is deleted.
    - Lines: -4 / +1.
    - Here: ui build.
    - Pi only: auto ISO/WB values on the touch UI and HDMI monitor follow the scene within about 1 s, and `journalctl -u apertar-core` shows no `get_state` storm.
    - Depends on: 19.

Order: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 + 15 (together), 16, 17, 18; 19 + 20 only if the owner says yes. Every Core commit leaves the 1.6.0 fields of `get_state`, `/api/state`, `/api/config` and every 1.6.0 command reply as they are. The port-only commands that move (`get_controls`, `controls_history`) are clients of the WebUI only.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| `test_input` before the lock | one `if` above `std::lock_guard` in `handleCommand`, with one comment line | It is a source of commands, like upstream's `dispatchHardwareInputCommand` (`App:8458-8466`), not a command body. Under the lock it would deadlock. Script actions are already refused (`d1dcdee`) |
| `abortSafetyStopFlushForRecord` before the lock | as is (`App:12587`, `:10123`) | The safety-stop drain holds `commandMutex_`. Moving the abort under the lock needs the drain to stop holding the lock, which is buffer/safety-stop work, not this theme |
| Hardware-file revisions, history and stale-save refusal | `HardwareConfigStore` with a revision in the query string or a `base=` field; refusals as sentences | Upstream's `POST /api/config` is last-writer-wins. The revision guard protects two surfaces editing one file. Kept as small as upstream's shapes allow: query parameter, `errorReply`, HTTP 409 |
| Validation lists (`issues`, `new_errors`) | members of `ok:true` replies and of `GET /api/config` | Upstream has no validator. The lists stay out of error replies, so a refusal stays one sentence |
| HTTP statuses 409 and 410 on routes | `errorReply(-1, sentence)` bodies | Upstream routes use 400/404/500/503. The status is HTTP, not a second error vocabulary in the JSON |
| `set_iso_auto enabled=false` (Lock), `set_timecode_mode target=` | optional fields; without them the 1.6.0 meaning holds | Already judged keep-as-is in App-5-F9 and App-5-F7. Commit 16 makes the UI honest about them |
| `exposure_in_use` event (if 19 is taken) | one literal event from the 1 Hz loop | Nearest upstream: `audio_level` (`App:8383`) and the 1 Hz loop |

## For the owner

| Question | Options | Recommendation and cost |
| --- | --- | --- |
| Socket clients (your `core.py`) lose `get_controls` and `controls_history` | a) move to `GET /api/config` (+ `/history`); b) keep both as ordinary commands under the lock, as well | a). Over ssh it is `curl -s localhost:8000/api/config`. b) keeps two doors to one file, the thing App-4-F1 is about. Cost of a): your scripts change once |
| Validation details on a refused save | a) sentence only, with the count and the first new error; the Check button lists all; b) keep `issues` in error replies as the one documented extension | a). It is what 1.6.0 does for every refusal. Cost: a card shows one problem instead of a list until you press Check |
| `old_page` (a browser tab opened before an update) | a) drop it; b) keep it on Origin presence, as now | a). Core and page ship together (CMD-30), and the new page always sends the revision. Cost: one tab left open across the update can save over a newer file once |
| Rename the four camera switches to `set_*_enabled` (`set_fps_phase_lock`, `set_media_trim`, `set_preview_tdn`, `set_clip_merge`) | a) leave the names, since they already take `enabled=`; b) rename, with no alias | a) now. They take the upstream argument; the name drift is cosmetic. b) is one more Core+UI+WebUI pair of commits |
| `storage_preroll` -> `storage_preroll_start` (App-5-F8) | a) rename in the same pair as 14/15; b) leave it | a), if the preroll theme keeps the command. Cost: 4 lines |
| `set_cdng_log` | a) keep `value=off\|auto` (an enum, like `set_cdng_compression`); b) `enabled=` as UI-control-bridge-F1 suggests | a). The state key is the string `cdng_log`, so the argument matches it. Whether `Auto` should read `On` (Camera-headers-F14) belongs to the camera-modes theme |
| The 1 s `get_state` poll during auto ISO/WB | a) keep it; b) commits 19 + 20 | b), if the HDMI monitor is in use (two processes poll). Cost: about 10 lines and one new event name |
| `scan_i2c` under the lock | a) under the lock with stop-on-timeout (commits 4-5); b) a worker with polled state, like the media speed test | a). Measure on a Pi 4. If a healthy scan takes over about 0.5 s, take b) (about +40 lines) |

## Risks and what was not determined

- **Scan time under the lock** (unconfirmed). `probeI2cAddress` opens the bus device and reads one byte per address. On a healthy bus this should be tens of ms. It is not measured on Pi 4 (`i2c-bcm2835`), Pi 5/CM5 (RP1 `i2c-designware`) or CM4. Settle with `time core.py scan_i2c bus=1` on each.
- **Stuck-bus errno** (probable). The errno for a timed-out transfer differs by adapter (`ETIMEDOUT` on bcm2835; designware may give `EIO` or `ETIMEDOUT`). Commit 4 treats every errno except `ENXIO`/`EREMOTEIO` as "bus does not answer". If an adapter reports a missing device with `EIO`, the scan would stop early. Settle with `strace -e ioctl,read core.py scan_i2c bus=1` on Pi 4 and Pi 5.
- **`/api/config` cost** (probable). It now enumerates I2C buses, GPIO chips and the CFexpress hat (`cfeHatPeripheralJson` probes bus 10 `0x34`). It runs only on page loads and after saves, not in the 1 Hz poll. The hat probe racing the UI's automounter is HW-controls-model-F15, owned by hardware-inputs.
- **Two paths for the hardware file** (probable). `store.path()` (`HardwareConfigStore::defaultPath()`) and `editableHardwareConfigPath()` (`App:4944`) are taken to be the same file; both honour `APERTAR_HARDWARE_CONFIG`. Check `defaultPath()` before commit 2.
- **A missing hardware file**: the model, peripherals and issues are of `info.text` (empty), and `text` is the template or `/boot` copy, as today in the two separate replies. The Controls page then shows "This Apertar Core does not describe its controls yet" only if `model` is absent, which it is not. Check in `--simulate` with no file.
- **Pair 14/15**: a UI built from 15 against a Core before 14 gets "Unknown command" on the pre-roll Auto switch. Under CMD-30 the owner's install builds both; the risk is only in a half-updated tree.
- **Boot Config without a revision** (commit 10): a socket script that saved without `revision=` is now refused. The fan mode (`set_fan_mode`) is unaffected.
- **Not determined**: whether `collectingCommandEvents_` (set before the lock, conventions section 4) mixes events into the replies of the moved commands. It is upstream's rough edge and unchanged.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-4-F1 | 1, 2, 3, 5 |
| App-1-F5 | 7, 8, 9, 10, 12 |
| X-protocol-security-3 | 16 |
| X-protocol-security-4 | 16 |
| X-protocol-security-5 | 1, 2, 4, 5 |
| X-protocol-security-7 | 10 (command guard: revision on every save, no `browser`); the route deletion is the boot-config-helpers theme |
| X-protocol-security-8 | 19, 20 (owner decision) |
| X-protocol-security-9 | not covered: the sudoers files and root helpers are the boot-config-helpers theme |
| UI-control-bridge-F1 | 13, 15 (`set_cdng_log` keeps `value=`, see For the owner) |
| X-knobs-19 | 17 |
| CC-1-F4 | 17 (the writer). `fps_speed_ramp_after=return\|stay` stays: it is an enum word, not a boolean spelling |
| HW-config-text-store-F9 | 7, 8 (the store keeps its refusal kind internally, only to pick the HTTP status) |
| App-3-F4 | 8 |
| App-3-F5 | 9 |
| Playback-F3 | 9 |
| HW-controls-model-F8 | 6 (`analog_targets` / `trigger_events` with no consumer: HW-controls-model-F6, hardware-inputs theme) |
| HW-controls-model-F16 | 2 |
| App-4-F13 | 2 (the parse-once part). The two `[cfexpress_hat]` parsers: hardware-inputs theme |
| App-4-F20 | 2 (no counter writes in a read), 5 (scan sentence), 6 (`catalogJson` members). `errno` in the media sentence and `stopMediaWatcher`: not this theme |
| X-state-consistency-13 | 5 |
| App-1-F18 | 11 |
| App-5-F2 | 14, 15 (the `set_storage_preroll` part). Renaming the four camera switches: owner decision, not planned |
| App-5-F5 | 18 (the reply). Moving the range table to a free function: not this theme (value-step lists) |
| App-5-F8 | owner decision, rides with 14/15 if taken |
| App-1-F8 | 10 (the `confirm_display` sentence). The install command in the helper sentence: boot-config-helpers |
| App-1-F13 | not covered: stays as the second pre-lock step until the safety-stop drain stops holding `commandMutex_` (buffer/safety-stop work) |
| X-protocol-security-6, X-state-consistency-11, App-5-F3 | already fixed by `e4246ee` "core: get_state sends media_state once" |
| X-protocol-security-2 | already fixed by `d1dcdee` (test_input refuses script actions) |
| WCP-09-F2 (`controlsCall`) | not covered: webui-state theme. Commits 2, 3 remove 5 of its call sites |
| UI-control-bridge-F2 (event branches) | not covered: touch-ui theme |
| App-1-F9 (nested Boot Config replies), App-1-F4, App-3-F1, WCP-10-F1, Boot-config-F1 | not covered: boot-config-helpers theme (route and engine). Commit 10 is compatible with either order |
| App-3-F11 (leading comma in state fragments) | not covered: storage-settings rewrites the blocks that use them |
| Camera-headers-F14 | not covered: camera-modes theme. The wire value of `set_cdng_log` does not change here |
