# Coding map check: arrows c1-c9 and s1-s3 (const E)

Slice: the 12 arrows in `const E` whose id starts with `c` (commands in) or `s` (state back).
Map: `/home/user/apertar-coding-map/index.html` at `bff7bd5`, lines 353-390. Read-only. `index.html` was not edited.

| Mode | Tree | Ref |
| --- | --- | --- |
| official | `/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream` | `@upstream-1.6.0` (Core `35dbe67`, UI `43888e5`) |
| fork | `/home/user/Apertar-Core`, `/home/user/Apertar-UI` | `@cinemate-port` (Core `01f170c`, UI `7ea9afc`) |

Short names: `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`,
`CB` = `src/ApertarControlBridge.cpp` (UI repo), `CP` = `src/ipc/ControlProtocol.cpp`, `CS` = `src/ipc/ControlServer.cpp`.
Line pairs are written `upstream / fork`.

How a field is shown (`index.html:539-559`, `render`): only `code` and `tip` go through `val()`. `what`, `path`, `title`
and the label are printed as written in both modes. An `up:{what:...}` on a box or an arrow would be ignored today.

## Result

103 fields checked (12 arrows), each in both modes. **3 discrepancies in the slice: 2 wrong, 1 imprecise.** All three are
the same in both modes. No arrow needs a new `up` override. No `fork:true` flag is missing or wrong.
One more wrong sentence outside the slice has the same root cause as D2 (static text, line 239).

| # | Item | Mode | Severity | One line |
| --- | --- | --- | --- | --- |
| D1 | `E.c3.code` | both | wrong | The touch UI sends `"value":800` (a number). The map shows `"value":"800"` |
| D2 | `E.c3.tip` | both | wrong | "Values travel as strings" is false. Numbers travel as numbers; Core keeps every value as text after parsing |
| D3 | `E.s2.what` (and `E.s2.t`) | both | imprecise | The arrow ends on the `handleCommand` box, but `GET /api/state` never enters `handleCommand` |
| D4 | static text, `index.html:239` (outside slice) | both | wrong | "Values are strings, because Core's parser is flat": same error as D2 |

## D1. `E.c3.code`: the value is a number, not a string (confirmed)

Map (`index.html:359`): `{"cmd":"set_iso","id":7,"value":"800"}`

Code, identical mechanism in both trees:

| Step | upstream / fork | Line |
| --- | --- | --- |
| `applyIso` builds the argument | `CB:309` / `CB:326` | `if (!sendCoreCommand(QStringLiteral("set_iso"), { { QStringLiteral("value"), qRound64(isoValue) } }))` |
| `sendCoreCommand` adds cmd and id | `CB:1046-1048` / `CB:1182-1184` | `QJsonObject command = arguments;` then `command.insert(QStringLiteral("cmd"), commandName);` and `command.insert(QStringLiteral("id"), commandId);` |
| Serialised, newline added | `CB:1050-1051` / `CB:1186-1187` | `QByteArray payload = QJsonDocument(command).toJson(QJsonDocument::Compact);` `payload.append('\n');` |

`qRound64` returns a `qint64`, so the JSON value is a number. Run here with the same Qt calls (Qt 6.4.2, see "Reproduce"):

```
{"cmd":"set_iso","id":7,"value":800}
```

Second opinion: `apertar-kb/llm/flows.md:27`, `architecture/ui.md:185` and `architecture/core.md:138` all show `"value":800`.

Corrected field text: `{"cmd":"set_iso","id":7,"value":800}`

Source line for `index.html:359`:

```
    code:"{\"cmd\":\"set_iso\",\"id\":7,\"value\":800}",
```

## D2. `E.c3.tip`: "Values travel as strings" is false (confirmed)

Map (`index.html:360`): "Values travel as strings, because Core's parser is flat. A wrong field name is not an error on
the UI side, so check both ends."

| Fact | upstream / fork | Line |
| --- | --- | --- |
| Touch UI sends numbers as numbers | `CB:309` / `CB:326`; also `set_fps` at `CB:270` / `CB:272` | `{ QStringLiteral("value"), qRound64(isoValue) }`, `{ QStringLiteral("value"), fpsValue }` |
| WebUI sends a number too | `WCP:9888` / `WCP:15944`; body `WCP:9126` / `WCP:14433` | `await sendCommand({ cmd: "set_iso", value: Number(value) });` and `body: JSON.stringify(payload),` |
| Core stores every value as text | `src/ipc/ControlProtocol.hpp:12` (file identical in both trees) | `std::map<std::string, std::string> fields;` |
| Quoted or bare, both accepted | `CP:194-197`, `CP:204` (identical in both trees) | `value = parseStringLiteral(line, pos);` else `value = parseBareValue(line, pos);` then `result.command.fields[*key] = *value;` |
| Number read back with `stod` | `CP:147` | `const double value = std::stod(it->second, &parsed);` |
| Upstream's own README sends a number | `README.md:292` / `README.md:382` | `printf '{"cmd":"set_fps","value":24.0}\n' \| socat - UNIX-CONNECT:/tmp/apertar-core.sock` |

Core's own parser, built from each tree and fed five lines (see "Reproduce"), gives the same output for both trees:

| Line | Result |
| --- | --- |
| `{"cmd":"set_iso","id":7,"value":800}` | ok, value text `800`, number 800 |
| `{"cmd":"set_iso","id":7,"value":"800"}` | ok, value text `800`, number 800 |
| `{"cmd":"set_iso","value":{"n":800}}` | ok, value text `{"n":800`, not a number (the command then fails with "set_iso requires value.") |
| `{"cmd":"set_iso","value":[800,1600]}` | parse error "Expected object key." |

So "flat" means: one level, every value kept as text after parsing. A string works for a number, which is why the curl
in `E.c5.code` (`"value":"800"`) is fine and stays. The second sentence of the tip holds (see "Checked and holds", c3).

Corrected field text:

> Core's parser is flat: one level, every value kept as text. So 800 and "800" both work, and nested objects or arrays do not. A wrong field name is not an error on the UI side, so check both ends.

Source line for `index.html:360`:

```
    tip:"Core's parser is flat: one level, every value kept as text. So 800 and \"800\" both work, and nested objects or arrays do not. A wrong field name is not an error on the UI side, so check both ends."},
```

## D3. `E.s2`: the state request does not pass `handleCommand` (confirmed)

Map (`index.html:384-385`): `f:"WEBPAGE",t:"HUB"`, what = "The arrow points at Core because the page asks.
buildWebStateJson answers with fresh JSON from the camera settings, UI.conf, media, network and power."

The HUB box is titled `handleCommand` and says "Every command from every entry point ends up here ... guarded by
commandMutex_". `GET /api/state` does not go there:

| Fact | upstream / fork | Line |
| --- | --- | --- |
| The route calls the builder directly | `App:7154-7158` / `App:8428-8432` | `if (request.method == "GET" && request.path == "/api/state") {` ... `response.body = buildWebStateJson();` |
| The builder | `App:7711-8046` / `App:9298-9720` | `std::string ApertarCoreApp::buildWebStateJson() const` |
| No `commandMutex_`, no `handleCommand(` inside the builder | same ranges | `awk` over both ranges: 0 hits |
| For contrast, the POST does go through the hub | `App:7637-7641` -> `App:7085-7091` / `App:9214-9218` -> `App:8349-8355` | `response.body = handleWebCommand(request.body);` -> `return handleCommand(parsed.command);` |

The text is right, the box the arrow lands on is not. The map has no box for Core's HTTP handler, so the fix is one clause
in `what` (no layout change). The rest of the sentence was checked and holds: `camera_.settings()`, `readSharedUiSettings()`
(UI.conf), media mount and space, `readNetworkSnapshot`, `readPowerSupplySnapshot` (`App:7715-7737` / `App:9304-9336`).

Corrected field text:

> The arrow points at Core because the page asks. This request skips handleCommand: handleWebRequest calls buildWebStateJson, which answers with fresh JSON from the camera settings, UI.conf, media, network and power.

Source line for `index.html:385`:

```
    what:"The arrow points at Core because the page asks. This request skips handleCommand: handleWebRequest calls buildWebStateJson, which answers with fresh JSON from the camera settings, UI.conf, media, network and power.",
```

## D4. Outside the slice, same root cause as D2: static text `index.html:239` (confirmed)

Map: "The same calls the WebUI makes. Values are strings, because Core's parser is flat."

The WebUI sends `value: Number(value)` (`WCP:9888` / `WCP:15944`). The two curl lines below that text use `"800"` and work,
so they can stay. Only the sentence is false.

Corrected text: `The same calls the WebUI makes. Core's parser is flat and keeps every value as text, so "800" and 800 both work.`

The same sentence and the same `"value":"800"` socket line are in `apertar-kb/architecture/diagrams.md:115-116` and `:128-129`.
Line 116 also says the page JS sends `{"cmd":"set_iso","value":"800"}`; it sends `800`.

## Checked and holds

Every row was read in the code in both trees. "same" = the map text is true as written in both modes.

| Arrow | Field | Verdict | Evidence, upstream / fork |
| --- | --- | --- | --- |
| c1 | `code` (fork) `onClicked: root.optionSelected(optionValue)` | confirmed | fork `qml/TopDropdownStat.qml:123`; not in upstream (0 hits) |
| c1 | `up.code` `onClicked: root.optionSelected(modelData)` | confirmed | upstream `qml/TopDropdownStat.qml:113`; not in the fork (0 hits) |
| c1 | `fork:true` | confirmed | the fork line does not exist upstream, so the "fork only" tag is true |
| c1 | `what`, `path`, `title` | same | `signal optionSelected(string value)` `:23` / `:26`; CameraPage handles it: `onOptionSelected: function(v) {` `qml/CameraPage.qml:2940` / `:3102` |
| c1 | `f`,`t`,`k` TOUCH -> QML, thin | same | a tap handled inside the UI process |
| c2 | `code` `root.controlBridge.applyIso(v)` | same | `qml/CameraPage.qml:2942` / `:3104` |
| c2 | `what` (Q_INVOKABLE, plain call inside the UI process) | same | `Q_INVOKABLE bool applyIso(const QString &displayValue);` `src/ApertarControlBridge.hpp:112` / `:180` |
| c2 | `f`,`t`,`k` QML -> BRIDGE, thin | same | QML calls a C++ method in the same process |
| c3 | `what` (newline-terminated line; same id; ok plus settings) | same | `payload.append('\n');` `CB:1051` / `CB:1187`; Core splits on `\n` `CS:248` / `CS:251`; `okReply` writes `"ok":true`, `"id"`, then the body `App:108-118` / `App:151-161`; id matched `CB:1076` / `CB:1212` |
| c3 | `path` `/tmp/apertar-core.sock` | same | `src/ApertarCoreApp.hpp:33` / `:39`; `CB:1032` / `CB:1168` |
| c3 | `f`,`t`,`k` BRIDGE -> HUB, thick | same | `QLocalSocket socket;` `CB:1034` / `CB:1170` -> `ControlServer::clientLoop` -> `handleRequest` `App:7055` / `App:8319` -> `handleCommand` |
| c3 | `tip`, second sentence (wrong field name, UI side) | same | Core answers `ok:false` (`"set_iso requires value."` `App:9245` / `App:12971`), the bridge only sets `lastError`; the ISO dropdown ignores the return value (`qml/CameraPage.qml:2942` / `:3104`) and no QML shows `lastError` for ISO |
| c4 | `code` `await sendCommand({ cmd: "set_iso", value: Number(value) });` | same | `WCP:9888` / `WCP:15944` |
| c4 | `what`, `path` | same | click handler passed to `buildOptionButtons("isoOptions", ...)`; `sendCommand` `WCP:9109` / `WCP:14416` |
| c4 | `f`,`t`,`k` BROWSER -> WEBPAGE, thin | same | page JavaScript inside the browser |
| c5 | `what` (handleWebCommand -> same handleCommand) | same | `App:7637-7641`, `App:7085-7091` / `App:9214-9218`, `App:8349-8355` |
| c5 | `code` (curl), `path`, `tip` | same | port `uint16_t webPort = 8000;` `src/ApertarCoreApp.hpp:36` / `:42`; a client without an `Origin` header is allowed, `src/web/WebServer.cpp:161` / `:164`; a quoted `"800"` parses to 800 (see D2) |
| c5 | `f`,`t`,`k` WEBPAGE -> HUB, thick | same | HTTP POST from the browser to Core |
| c6 | `code` (`[neorotary4]`, `enabled`, `encoder0_cw`, `encoder0_ccw`) | same | section `src/hardware/NeoRotary4Input.cpp:383` / `:290`; `enabled` `:403` / `:310`; cw / ccw `:424-432` / `:331-339`; `iso_up`, `iso_down` are known names: `NeoRotary4Input.cpp:193-196` upstream, `src/hardware/ActionCatalog.hpp:39-40` fork |
| c6 | `path` `~/apertar-hardware.conf` | same | `return "/home/pi/apertar-hardware.conf";` `NeoRotary4Input.cpp:70` / `:72` |
| c6 | `what` (Core polls the I2C devices itself) | same | poll thread `NeoRotary4Input.cpp:324` / `:231`, sleeps `poll_ms` `:711` / `:647`; same pattern in `Pcf8574Input.cpp:287`, `:523` / `:194`, `:471` |
| c6 | `k` thin | no change proposed | Core's poll thread reads the chip over I2C. No second program is involved, so thin is the closest of the two line kinds |
| c7 | `code` `std::string ApertarCoreApp::dispatchHardwareInputCommand(ControlCommand command)` | same | `App:8458` / `App:10117` |
| c7 | `what` (iso_up -> set_iso; id = -1) | same | `pcfSettingStepMode(action, "iso")` -> `dispatch("set_iso", ...)` `App:8789-8800` / `App:10481-10505`; `command.id = -1;` `App:8461` / `App:10121` |
| c7 | `title` (on the poll thread) | same | the input's callback calls `handleHardwareInputAction` directly: `App:6790-6791` / `App:7983-7984`; called from `run()` at `NeoRotary4Input.cpp:664` / `:584` |
| c7 | `tip` (reply thrown away; failure only in the journal) | same | `std::cerr << "Hardware input action failed: " << reply << "\n";` `App:8464` / `App:10124`; no caller in `handleSingleHardwareInputAction` uses the reply (grep, 0 hits in both) |
| c7 | `f`,`t`,`k` HWIN -> HUB, thin | same | a function call inside Core |
| c8 | `code` (three lines) | same | `App:9246-9248` / `App:12972-12974` |
| c8 | `what`, `path`, label `setIso()` | same | branch `if (command.name == "set_iso") {` `App:9242` / `App:12968` |
| c8 | `f`,`t`,`k` HUB -> CAM, thin | same | `camera_.setIso(...)` is a call inside Core |
| c9 | `code` `request->controls().merge(pendingControls_);` | same | `CC:6506` / `CC:8987` |
| c9 | `what` (merged into the next request that goes back) | same | `applyControls` sets `pendingControls_` `CC:5511` / `CC:7584`; `requeueRequest` merges and clears them `CC:6497-6508` / `CC:8978-8989`, then `camera_->queueRequest(request)` `CC:6569` / `CC:9083` |
| c9 | `f`,`t`,`k` CAM -> SENSOR, thin | same | calls into libcamera inside the Core process |
| s1 | `code` `{"event":"settings",...,"iso":800,"iso_auto":false,...}` | same | `CC:139`, `:145-146` / `CC:166`, `:173-174` (field order matches) |
| s1 | `what` (broadcast to every socket client; the UI's persistent event socket) | same | `setIso` `CC:7774` / `CC:11131` -> `applySettingsLocked` -> `if (commit) emitSettingsEventLocked();` `CC:8721` / `CC:12791` -> `eventCallback_(settingsEvent(settings_));` `CC:8783` / `CC:12870` -> `publishEvent` `App:6784` / `App:7977` -> settings is always broadcast `App:10829-10840` / `App:14883-14898` -> `ControlServer::broadcast` `CS:172` / `CS:175`; UI side `connect(&m_eventSocket, &QLocalSocket::readyRead, ...)` `CB:122` / `CB:124` |
| s1 | `tip` (pushed, WebUI up to 1 s later) | same | WebUI poll `window.setInterval(() => fetchState(true), 1000);` `WCP:11609` / `WCP:20954` |
| s1 | `f`,`t`,`k` CAM -> BRIDGE, thick dashed | same | built in CameraController, sent over the socket to the UI process |
| s2 | `code` (curl + grep), `path`, label | same | `"iso":` occurs once in the state JSON: `App:7861` / `App:9485` |
| s2 | `tip` (three hand-written copies) | same | `settingsBody` `App:167` / `App:313`; `settingsEvent` `CC:136` / `CC:163`; `buildWebStateJson` `App:7711` / `App:9298`, each writes `"iso"` itself |
| s2 | `k` thick dashed | same | HTTP GET between the browser and Core |
| s3 | `code` `function onIsoChanged() { ... }` | same | `qml/CameraPage.qml:1843-1846` / `:1980-1983` |
| s3 | `what` (applyCoreState -> setIso -> isoChanged only on change; CameraPage copies it; the dropdown shows it) | same | `CB:1257-1258` / `CB:1411-1412`; `setIso(formatIsoValue(...))` `CB:1374` / `CB:1561`; `if (m_iso == value) return;` ... `emit isoChanged();` `CB:2239-2246` / `CB:2481-2488`; `root.iso = root.controlBridge.iso` `qml/CameraPage.qml:1845` / `:1982`; `value: root.iso` `:2931` / `:3091` |
| s3 | `f`,`t`,`k` BRIDGE -> QML, thin dashed | same | Qt signal to a QML `Connections` handler inside the UI process; `Q_PROPERTY(QString iso READ iso NOTIFY isoChanged)` `src/ApertarControlBridge.hpp:17` / `:17` |

Notes on two rows:

- c7, fork: `dispatchHardwareInputCommand` gained one line before the lock (`abortSafetyStopFlushForRecord`, `App:10119`). The map's statement is unchanged by it.
- s3, fork: the dropdown also has `displayValue: root.controlBridge ? root.controlBridge.isoInUse : ""` (`qml/CameraPage.qml:3092`). It is empty for a manual ISO (`CB:1603`), so "the dropdown shows it" still holds for ISO 800.

## Reproduce

Both programs are throwaway and live in the session scratchpad. The commands:

```
# D1: the exact Qt calls of applyIso + sendCoreCommand
#   QJsonObject arguments{ { QStringLiteral("value"), qRound64(800.0) } };
#   QJsonObject command = arguments; command.insert("cmd","set_iso"); command.insert("id",7);
#   QJsonDocument(command).toJson(QJsonDocument::Compact)
g++ -std=c++17 -fPIC $(pkg-config --cflags Qt6Core) main.cpp -o qtjson $(pkg-config --libs Qt6Core) && ./qtjson
# -> {"cmd":"set_iso","id":7,"value":800}

# D2: Core's own parser, from each tree
g++ -std=c++20 -I<tree>/src main.cpp <tree>/src/ipc/ControlProtocol.cpp -o parser_test && ./parser_test
# main.cpp calls apertar::parseControlCommand(line), then command.string("value") and command.number("value")
```

Literal checks: `grep -nF '<literal>' <file>` in both trees for every code string in the table above. All hits are listed there.

## Seen in passing, outside this slice (not counted)

| Item | Mode | What | Evidence |
| --- | --- | --- | --- |
| `N.HUB.what` "guarded by commandMutex_" | fork | Six commands answer before the lock: `get_controls`, `controls_history`, `controls_last_input`, `scan_i2c`, `list_actions` (in `handleReadOnlyHardwareCommand`) and `test_input` | `App:12561-12566`, lock at `App:12571`, helper `App:12418-12534` `@cinemate-port`. Upstream locks first: `App:9093` |
| `N.BTN.what` / `N.HWIN.what` "Core polls them" / "Poll threads read I2C or GPIO" | fork | GPIO buttons now wait for edge events and poll only where a chip gives none | `src/hardware/GpioInput.cpp:518`, `:736`, `:823` `@cinemate-port`; commit `0c49601` |
| Fork footer and `srcNote` hashes `f4a1393`, `7029db1` | fork | The branch is at `01f170c` / `7ea9afc` now | `index.html:661`, `:916` |
| `apertar-kb/architecture/diagrams.md:115-116`, `:128-129` | n/a | Same `"value":"800"` and "values are strings" as D1, D2, D4 | compare `architecture/ui.md:185`, `architecture/core.md:138` |
| `render()` | both | `what`, `path`, `title` ignore `up`. A correction that needs a different `what` per mode needs `val(it,"what")` at `index.html:555` | `index.html:554-557` |

## For the user request (GPIO chip definition)

Not part of this slice; noted because c6 and c7 made me read the input code. Nothing in arrows c1-c9 or s1-s3 mentions the
GPIO chip, so the request needs no change to these arrows.

| Fact | Evidence |
| --- | --- |
| Core reads the chip from `[gpio]` in both trees: keys `chip`, `gpiochip`, `gpio_chip`; empty = `auto` | `src/hardware/GpioInput.cpp:431-432` `@upstream-1.6.0`, `:343-344` `@cinemate-port` |
| The port's Controls page had a "GPIO chip" field for one day and dropped it | added in `166cc4d` (2026-10-29), removed in `c140c4f` (2026-10-30): `-            {"chip", "GPIO chip", "text", "auto", "", 0, 0},` in `src/hardware/ControlsModel.hpp` |
| What is there now | `src/hardware/ControlsModel.hpp:258-263` `@cinemate-port`: `enabled`, `active_low`, `pull`, `debounce_ms`, and the comment "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" |
| The file model still knows the key | `src/hardware/HardwareConfigText.hpp:172`, `:457`, `:476` `@cinemate-port` |

## Recheck

Second checker. Each item re-derived from the code in both trees (`@upstream-1.6.0` and `@cinemate-port`). `index.html` not edited.

| # | Verdict | Why |
| --- | --- | --- |
| D1 `E.c3.code` | stands | `applyIso` passes `qRound64(isoValue)` (a `qint64`): `src/ApertarControlBridge.cpp:309` @upstream-1.6.0 / `:326` @cinemate-port. `sendCoreCommand` serialises with `QJsonDocument(command).toJson(QJsonDocument::Compact)` `:1050` / `:1186`. A number serialises bare. KB `llm/flows.md:27` agrees. |
| D2 `E.c3.tip` | stands | `ControlProtocol.cpp` is byte-identical in both trees. `:194-197` takes a quoted string or a bare value, `:204` stores it in `std::map<std::string, std::string> fields` (`ControlProtocol.hpp:12`); `number()` reads it back with `std::stod` (`:147`). Bare value reads up to `,` or `}`, so a nested object yields garbage text and an array fails as "Expected object key.". The touch UI and the WebUI (`WCP:9888` / `:15944`, `value: Number(value)`) both send numbers. "Values travel as strings" is false. Correction text checked, kept as written. |
| D3 `E.s2.what` | stands (imprecise) | `GET /api/state` is handled inside `handleWebRequest` (`App:7093` / `:8357`), route `App:7154-7157` / `:8428-8431`, `response.body = buildWebStateJson();`. `buildWebStateJson` (`App:7711` / `:9298`) takes only `mediaSpeedMutex_` and `telemetryMutex_`, never `commandMutex_`, never calls `handleCommand(`. The arrow lands on the box titled `handleCommand`, so one clause is needed. Sources named in the sentence (settings, `readSharedUiSettings`, media, `readNetworkSnapshot`, `readPowerSupplySnapshot`) confirmed in both builders. Correction kept. |
| D4 static text `index.html:239` | stands | Same root cause as D2. Outside the slice but in the same mechanism; the curl lines under it (`"800"`) work and stay. Correction kept. |

No new discrepancy found in the slice.

## Final discrepancies

### F1. `E.c3.code` (index.html:359), mode: both, severity: wrong

- Map says: `{"cmd":"set_iso","id":7,"value":"800"}`
- Code says: `src/ApertarControlBridge.cpp:309@upstream-1.6.0` / `:326@cinemate-port`: `if (!sendCoreCommand(QStringLiteral("set_iso"), { { QStringLiteral("value"), qRound64(isoValue) } }))`; serialised at `:1050` / `:1186` `QByteArray payload = QJsonDocument(command).toJson(QJsonDocument::Compact);` -> value is a JSON number.
- Corrected text: `{"cmd":"set_iso","id":7,"value":800}`
- Source line: `    code:"{\"cmd\":\"set_iso\",\"id\":7,\"value\":800}",`

### F2. `E.c3.tip` (index.html:360), mode: both, severity: wrong

- Map says: "Values travel as strings, because Core's parser is flat. A wrong field name is not an error on the UI side, so check both ends."
- Code says: `src/ipc/ControlProtocol.hpp:12` (both refs) `std::map<std::string, std::string> fields;`; `src/ipc/ControlProtocol.cpp:194-197` (both) `value = parseStringLiteral(line, pos);` else `value = parseBareValue(line, pos);`; senders use numbers: `ApertarControlBridge.cpp:309@upstream-1.6.0` / `:326@cinemate-port` `qRound64(isoValue)`, `WebControlPage.cpp:9888@upstream-1.6.0` / `:15944@cinemate-port` `await sendCommand({ cmd: "set_iso", value: Number(value) });`
- Corrected text: `Core's parser is flat: one level, every value kept as text. So 800 and "800" both work, and nested objects or arrays do not. A wrong field name is not an error on the UI side, so check both ends.`
- Source line: `    tip:"Core's parser is flat: one level, every value kept as text. So 800 and \"800\" both work, and nested objects or arrays do not. A wrong field name is not an error on the UI side, so check both ends."},`

### F3. `E.s2.what` (index.html:385), mode: both, severity: imprecise

- Map says: "The arrow points at Core because the page asks. buildWebStateJson answers with fresh JSON from the camera settings, UI.conf, media, network and power." (arrow `t:"HUB"`, the box titled handleCommand)
- Code says: `src/ApertarCoreApp.cpp:7154-7157@upstream-1.6.0` / `:8428-8431@cinemate-port`, inside `handleWebRequest` (`:7093` / `:8357`): `if (request.method == "GET" && request.path == "/api/state") {` ... `response.body = buildWebStateJson();`. No `handleCommand(` and no `commandMutex_` in `buildWebStateJson` (`:7711` / `:9298`).
- Corrected text: `The arrow points at Core because the page asks. This request skips handleCommand: handleWebRequest calls buildWebStateJson, which answers with fresh JSON from the camera settings, UI.conf, media, network and power.`
- Source line: `    what:"The arrow points at Core because the page asks. This request skips handleCommand: handleWebRequest calls buildWebStateJson, which answers with fresh JSON from the camera settings, UI.conf, media, network and power.",`

### F4. Static text `index.html:239` ("Try 3 and 6 from the Mac" hint), mode: both, severity: wrong

- Map says: "The same calls the WebUI makes. Values are strings, because Core's parser is flat."
- Code says: `src/web/WebControlPage.cpp:9888@upstream-1.6.0` / `:15944@cinemate-port` `await sendCommand({ cmd: "set_iso", value: Number(value) });`; `src/ipc/ControlProtocol.hpp:12` `std::map<std::string, std::string> fields;`
- Corrected text: `The same calls the WebUI makes. Core's parser is flat and keeps every value as text, so "800" and 800 both work.`
