# Review: UI-control-bridge (stage 2 of 3)

Unit: `Apertar-UI/src/ApertarControlBridge.cpp` (+ header where the diff needs it), port diff `origin/main` -> `cinemate-port`,
scope file `/home/user/build/review/diffs/UI-ControlBridge.part01.diff` (new-file lines 9-2642, 12 hunks).
Inventory: `raw/inv-UI-control-bridge.md`. Yardstick: `raw/conv-ui-cpp.md` (rule ids UI-*), code in `/home/user/wt/ui-upstream`
and `/home/user/wt/core-upstream` at `upstream-1.6.0`.
Refs: `@port` = `cinemate-port`, `@up` = `upstream-1.6.0`. `B.cpp` / `B.hpp` = `src/ApertarControlBridge.{cpp,hpp}`,
`Core:App` = `Apertar-Core/src/ApertarCoreApp.cpp`. All claims confirmed (read in code) unless marked.

## Verdict in one paragraph

The bridge keeps Apertar's shape: read-only `Q_PROPERTY` + NOTIFY, one `applyCoreMessage` if-chain, flat snake_case keys,
all commands through `sendCoreCommand`, no threads, no logging, no board probe. The foreign parts are in the plumbing:
six `void` invokables, a second state path (dedicated event branches and reply re-application beside `applyCoreState`),
a key-name-parameterised setter because Core's new events spell the same value two ways, tolerant string parsing that
answers a problem Core does not have, a `target` string on `applyTimecodeMode` that breaks upstream's one-argument call,
and a 1 s full-state poll where upstream pushes live values as events. All are S/M reworks inside this file plus small
Core event changes. No blocker.

## Findings

| Id | Title | Cat | Sev | Effort | Deliberate |
| --- | --- | --- | --- | --- | --- |
| F1 | Six new invokables return `void`; bool args spelled `value=on/off`; action named `apply*` | mismatch | major | S | no |
| F2 | Second state path: dedicated `buffer`/`controls`/`media` branches and a key-name-parameterised setter | mismatch | major | M | no |
| F3 | Replies applied twice (`applyClipNameTemplate`, `applyBufferMode`, `applyCdngLog`) | duplication | minor | S | no |
| F4 | String-or-number tolerant parsing justified by "KB trap 7"; Core emits typed JSON | slop | minor | S | no |
| F5 | `applyTimecodeMode(displayValue, target)`: upstream one-argument call gone, tap no longer sets file timecode | removed-upstream-behaviour | major | M | yes |
| F6 | 1 s `get_state` poll while auto ISO/WB; `updateRefreshTimer()` on every state pass | mismatch | minor | M | yes |
| F7 | ISO "Lock" overloads `set_iso_auto enabled=false`; original Core turns auto ON | protocol | minor | S | unknown |
| F8 | `shutterSetByCamera` read before `setRecordingState` in the same pass | bug | minor | S | no |
| F9 | Presence latches `storagePrerollAutoKnown`, `clipNameKnown` for "older Core" | new-ground | minor | S | no |
| F10 | Internal vocabulary and stale comments; `std::clamp` beside `qBound`; setter declared among members | slop | nit | S | no |

### F1 `void` invokables (mismatch, major)

Port: `B.hpp:194-198,200@port`
```cpp
Q_INVOKABLE void applyBufferMode(const QString &value);
Q_INVOKABLE void applyStoragePreroll();
Q_INVOKABLE void applyStoragePrerollAuto(bool on);
Q_INVOKABLE void applyClipNameTemplate(const QString &value);
Q_INVOKABLE void requestClipNamePreview(const QString &value);
Q_INVOKABLE void applyCdngLog(bool on);
```
`applyStoragePrerollAuto` sends `{"value": on ? "on" : "off"}` (`B.cpp:624-630@port`); `applyStoragePreroll` starts an action.

Upstream: every command invokable returns `bool`; thin variants `return sendCoreCommand(...)`; booleans go as `enabled` = `"true"`/`"false"`
and the method is named `apply<Thing>Enabled(bool enabled)` (`B.cpp:736-741@up`):
```cpp
bool ApertarControlBridge::applyPhotoLongExposureEnabled(bool enabled)
{
    return sendCoreCommand(QStringLiteral("set_photo_long_exposure_enabled"), {
        {QStringLiteral("enabled"), enabled ? QStringLiteral("true") : QStringLiteral("false")}
    });
}
```
Only `notifyUserActivity` and `refresh` are `void` upstream. Actions use verbs (`capturePhoto`, `calibrateGyro`). Rules UI-I1, UI-I2, UI-I4.

Why: QML cannot tell success from refusal; the original developer reads `void apply*` as fire-and-forget, which upstream never does
for a command. `on`/`off` is a third boolean spelling on the wire.

Rework (B.hpp/B.cpp, QML callers unchanged because they ignore the result):
- `bool applyBufferMode(const QString &value)`, `bool applyClipNameTemplate(const QString &)`, `bool applyCdngLog(bool)`:
  `return false` after `setLastError`/failed send, `return true` at the end.
- `bool startStoragePreroll()` { `return sendCoreCommand("storage_preroll", {});` } (action verb, like `capturePhoto`).
- `bool applyStoragePrerollAutoEnabled(bool enabled)` sending `enabled="true"|"false"`; Core `set_storage_preroll` already accepts
  `true`/`false` (`Core:App:12903-12904@port`), so read `enabled` there and keep `value` as alias only if the WebUI sends it.
- `bool requestClipNamePreview(const QString &)` returns the send result.

### F2 Second state path and two key spellings (mismatch, major)

Port (`B.cpp:1332-1349@port`, diff 296-313): three branches that bypass `applyCoreState`:
```cpp
if (event == QStringLiteral("controls")) {
    setControlsStatus(message, QStringLiteral("errors"), QStringLiteral("warnings"));
    return;
}
if (event == QStringLiteral("media")) {
    setCoreMediaState(message.value(QStringLiteral("state")).toString(),
                      message.value(QStringLiteral("mounted")).toBool(true));
    return;
}
...
if (event == QStringLiteral("buffer")) {
    applyBufferState(message);
    applyRecordingDroppedFrames(message);
    return;
}
```
and `applyCoreState` calls the same mappers again with the state spellings (`B.cpp:1439-1442,1457,1732-1734@port`).
`setControlsStatus(object, errorsKey, warningsKey)` exists only because Core's `controls` event says `errors`/`warnings` while
`get_state` says `controls_errors`/`controls_warnings` (`Core:App:12346-12348` vs `:9458-9459@port`); `media` says `state`/`mounted`
while state says `media_state`/`media_alive` (`Core:App:10826-10828` vs `:9555-9556@port`).

Upstream: events whose fields are state keys go whole through `applyCoreState` (`B.cpp:1191-1195@up`):
```cpp
if (event == QStringLiteral("standby") || event == QStringLiteral("still_exposure") ||
    event == QStringLiteral("timelapse_progress") || event == QStringLiteral("media_write_state")) {
    applyCoreState(message);
    return;
}
```
and `recording_health` the same (`:1213-1216@up`). No setter takes key names. Rule UI-S4 ("a second state-parsing path outside
`applyCoreState`" is the listed violation).

Rework:
- Core: `controls` event emits `controls_errors`, `controls_warnings`; `media` event emits `media_state`, `media_alive` (keep
  `state`/`mounted` too only if the WebUI reads them). `buffer` already uses state spellings.
- UI: add `controls`, `media`, `buffer` to the upstream list at `B.cpp:1328-1329@port`; delete the three branches;
  delete `setControlsStatus`, put an inline compare/assign/emit for `controls_errors`/`controls_warnings` in `applyCoreState`
  (upstream form `recording_has_dropped_frames`, `B.cpp:1270-1276@up`).
Risk: `applyCoreState` on a partial event runs every block; upstream already does this for `standby` etc., and the port's blocks
are `contains`-guarded. The photo fallback reads UI.conf on every pass (`B.cpp:1527-1554@up`); the `buffer` event is "small and rare"
(`Core:App:10838@port`), so cost is the upstream cost.

### F3 Replies applied twice (duplication, minor)

`sendCoreCommand` hands every reply to `applyCoreMessage` -> `applyCoreState` (`B.cpp:1210`, `:1411-1412@port`), which already calls
`applyClipNameState`, `applyBufferState`, `applyCdngLogState`. Then:
- `applyClipNameTemplate` calls `applyClipNameState(reply)` again (`B.cpp:640@port`);
- `applyBufferMode` sets `m_bufferSetting` (`:697-700`) although the reply carries `buffer_setting` (`Core:App:12851-12852`);
- `applyCdngLog` sets `m_cdngLogOn` (`:723-726`) although the reply is `settingsBody`, which carries `cdng_log`.
Upstream thin variants rely on the reply alone (`applyCaptureMode`, `B.cpp:731-734@up`). Rework: drop the three post-send blocks;
the functions become `return sendCoreCommand(...)` (with F1). The comment at `:633-634` then reads true without the extra call.

### F4 Tolerant parsing (slop, minor)

Port `B.cpp:2666@port`: `// Core's flat JSON delivers scalars as strings (KB trap 7); accept numbers too.` followed by
`raw.isString() ? raw.toString().toDouble() : raw.toDouble(0.0)` six times and an `asBool` lambda (`:2768-2774`).
Core emits typed JSON: `"buffer_safety_stop":` `true`/`false`, `"buffer_stop_percent":` `std::to_string(...)`,
`"storage_preroll_active":` `true`/`false` (`Core:App:257-263@port`); `"buffer_fill":` number (`:306`). "KB trap 7" is about Core's
request parser, not its output (inventory O5). Upstream reads typed with a default: `state.value("iso_auto").toBool(m_isoAuto)`
(`B.cpp:1321@up`). Rework: replace each with `.toDouble()`, `.toInt()`, `.toBool()`; delete the lambda and the comment
(about 40 lines fewer).

### F5 Timecode target (removed-upstream-behaviour, major)

Port `B.cpp:750-771@port`: `applyTimecodeMode(const QString &displayValue, const QString &target)`, `target` in `ui|files|both`,
no default; QML calls it with `"ui"` from the camera tap (`qml/CameraPage.qml:1842@port`) and both Settings dropdowns
(`qml/SettingsPage.qml:4011,4026@port`). Upstream: one argument, sets camera mode and UI.conf (`B.cpp:622-636@up`), tap sets both
(`qml/CameraPage.qml:1712-1714@up`).

Removed: the one-argument call (any upstream QML or third-party caller breaks with "Insufficient arguments"); the tap on the camera
page no longer changes the timecode written to clips (R3). The `"ui"` round trip is also redundant: QML already wrote
`settingsState.timecodeMode` (SettingsBridge, upstream UI-S5 owner, `SettingsBridge.cpp:1145-1155@up`), then the bridge writes the key
again (`:762-765`), then Core writes it a third time (`Core:App:13294-13298@port`).

Deliberate: yes (`7029db1` message: "the tap on the camera screen toggles the UI timecode only").

Rework (bridge side; QML side in `rev-UI-settings-qml.md` F2):
- Restore `bool applyTimecodeMode(const QString &displayValue)` with upstream meaning (Core `target` absent = both).
- Add `bool applyFileTimecodeMode(const QString &displayValue)` sending `target="files"` and setting `fileTimecodeMode`.
- A UI-only change is `settingsState.timecodeMode = v` with no Core call. Delete the `target` parameter and its validation.
- Camera tap: back to upstream (both), unless the owner decides otherwise; then document it for the original developer.

### F6 1 s full-state poll for live values (mismatch, minor)

Port `B.cpp:19-20`, `:1016`, `:1621@port`: `kLiveValuePollIntervalMs = 1000`; interval is 1 s while `m_isoAuto || m_whiteBalanceAuto`;
`updateRefreshTimer()` added at the end of the camera-set block, so every state pass (replies, `settings`, events) resets the interval.
Upstream: two tiers, 1 s only while disconnected, 30 s steady (`B.cpp:17-18`, `:875-882@up`); a live value is pushed by Core as its
own event and mapped in one line (`audio_level`, `B.cpp:1196-1199@up`). Core's `settings` event carries `iso_actual`
(`Core:CC:175@port`) but is emitted on settings changes, not on gain movement, so the poll is the only feed today.
Cost: one full `get_state` JSON parsed and the whole `applyCoreState` run on the GUI thread every second whenever auto ISO or auto WB
is on (async, so not blocking, UI-N1 holds).
Deliberate: yes (`f1edf96` message).
Rework: Core publishes a small event, e.g. `{"event":"exposure_measured","iso_actual":..,"wb_actual_kelvin":..,"wb_measured":..}`, rate
limited and only on change, as it does `audio_level`; UI adds it to the `applyCoreState` list (F2). Delete `kLiveValuePollIntervalMs`,
the ternary at `:1016` and the call at `:1621`.

### F7 ISO Lock wire shape (protocol, minor)

Port `B.cpp:302-309@port` sends `set_iso_auto` with `enabled="false"`; port Core reads it as "auto off at the gain in use"
(`Core:App:12995-13001@port`). Original Core's handler takes no argument and enables auto (`Core:App:9269-9273@up`):
port UI + original Core = Lock turns auto ISO on, the opposite. Upstream already has "auto off at a given gain": `set_iso value=<iso>`
(`B.cpp:305-313@up`, `Core:App:9242-9249@up`). `"Lock"` is also compared exactly while `"Auto"` goes through `isAutoSelection`.
Rework: QML's Lock item calls `applyIso(controlBridge.isoInUse)`; delete the Lock branch and Core's `enabled` argument.
Risk: Core `setIso` may snap to the ISO list; check `CameraController::setIso` before deleting the Core side.

### F8 `shutterSetByCamera` lags a pass (bug, minor, plausible)

`shutterSet = m_recording && m_fpsSpeedRamp && m_fpsSpeedRampKeepExposure` at `B.cpp:1610@port` reads `m_recording` before
`setRecordingState` at `:1730-1731`; in the `recording` event branch `applyCoreState(message)` runs before `setRecordingState`
(`:1352`, `:1357`). Failing input: ramp take with Exposure policy, auto ISO/WB off (30 s poll): at stop the shutter stays marked as
camera-set until the next state pass (next `settings` event or up to 30 s). Effect on screen unconfirmed (needs the Pi).
Rework: compute `m_shutterSetByCamera` in `setRecordingState` as well (emit `cameraSetValuesChanged` there), or move the block below
the `recording` key in `applyCoreState` and set recording first in the event branch.

### F9 Presence latches (new-ground, minor)

`storagePrerollAutoKnown`, `clipNameKnown`, empty `bufferSetting` hide controls until Core sends the key ("older Core never does",
`B.hpp:417,430@port`). Upstream has no "key was absent" latch; feature presence comes from Core flags (`recording_capabilities`,
`wb_available`, `exposure_compensation_available`, `B.cpp:1286-1304,1331,1360-1366@up`). After the merge UI and Core ship together,
so the latch only matters for mixed versions. Verdict simplify: drop the two `*Known` properties and show the controls; if mixed
versions must be supported, have Core send one capability flag in `recording_capabilities`.

### F10 Vocabulary and small idiom drift (slop, nit)

| Text | Where @port |
| --- | --- |
| "(T31)" | `B.cpp:275`, `B.hpp:435` |
| "T45:" | `B.hpp:82` |
| "(KB trap 7)" | `B.cpp:2666` (deleted by F4) |
| "CineMate Log" (another product's name; the UI says "Log") | `B.hpp:424` |
| "shown green" (QML shows italics since `35b31f6`) | `B.cpp:1582`, `B.hpp:18` |
| "older Core" (5 comments) | `B.cpp:662`, `B.hpp:417,427,430` |
| `std::clamp<qint64>` (no `<algorithm>` include) where the file uses `qBound` | `B.cpp:2655` |
| `setControlsStatus` declared among data members | `B.hpp:453` (deleted by F2) |

Rework: rewrite comments to say why in plain terms ("speed ramp"), drop ticket ids and product names, use `qBound`.

## Abstractions (inventory section 10)

| # | Abstraction | Verdict | Reason |
| --- | --- | --- | --- |
| A1 | State sub-mappers `applyBufferState`, `applyCdngLogState`, `applyClipNameState`, `applyRecordingDroppedFrames` | simplify | Private helpers called only from `applyCoreState` are tolerable in a 300-line function; the extra call sites (event branch, reply) are the foreign part (F2, F3). Inline is the strict upstream form |
| A2 | `setControlsStatus(object, errorsKey, warningsKey)` | rework-to-upstream-pattern | Exists only for two spellings; Core uses state keys in the event, bridge maps inline (F2) |
| A3 | Relay `coreMediaStateChanged(state, alive)` -> `MediaStatusBridge::setCoreMediaState` in `main.cpp` | keep | Same as upstream signal-to-slot wiring in `main()` (`externalRecordingPreparationRequested`, `src/main.cpp:324-327@up`); monitor-only process has no `MediaStatusBridge`, nothing to wire there |
| A4 | Third poll tier `kLiveValuePollIntervalMs` | rework-to-upstream-pattern | Live values are pushed as events upstream (F6) |
| A5 | In-use / set-by-camera display state, group signal `cameraSetValuesChanged` | keep | New ground, deliberate (`f1edf96` "User's rule"); display strings (UI-I3) and group NOTIFY (`recordingCapabilitiesChanged`) are upstream forms. Fix stale comment (F10) and F8 |
| A6 | Presence latches | simplify | F9 |
| A7 | String-or-number tolerant parsing | rework-to-upstream-pattern | Delete; typed accessors with default (F4) |
| A8 | `target` selector on `applyTimecodeMode` + `fileTimecodeMode` | rework-to-upstream-pattern | One-arg upstream call plus a separate `applyFileTimecodeMode`; UI-only through SettingsBridge (F5) |
| A9 | `void` invokables | rework-to-upstream-pattern | `bool` return, `enabled` true/false strings, action verb (F1) |
| A10 | `bufferSafetyStopped(message)` one-shot signal, text built in bridge | keep | Same shape as `gyroCalibrationFinished(ok, message)` (`B.cpp:846-851@up`); text is a full sentence |

## Conforms

- All 32 new properties are read-only with NOTIFY; related ones share one signal (`cameraSetValuesChanged`, `cdngLogChanged`, `clipNameChanged`) as upstream does (`B.hpp:34-39@up`).
- New Core keys are flat snake_case and read with `state.contains(...)` guards in `applyCoreState` (`B.cpp:1511-1515,1589-1600@port`).
- Every new command goes through `sendCoreCommand` with flat scalar args; no new socket, thread, timer or logging (UI-S3', UI-N1, UI-I6).
- Error text is a full sentence through `lastError` ("Invalid write buffer mode.", `B.cpp:688@port`).
- `applyFps` speed-ramp guard (`B.cpp:275-281@port`) is a thin "let the reply bring the state" path with a why-comment, like upstream's thin variants; deliberate and explained in `ec9f109`.
- New event branches keep the upstream `if (event == ...) { ...; return; }` chain style; unknown events still fall through harmlessly, so an original UI ignores `buffer`, `controls`, `media`.
- No board probe; feature presence comes from Core (UI-S6). The monitor-only process gets the new properties for free because it builds its own `ApertarControlBridge` (UI-S8).
- Removal of the `timecode_mode` -> UI.conf mirror in `applyCoreState` is consistent once the split exists; Core still writes UI.conf for `ui`/`both`.

## Cross-unit notes (not findings here)

- `set_buffer_mode` and `set_storage_preroll` make Core write `apertar-hardware.conf` (`[storage] buffer`, `[media] preroll`,
  `Core:App:12839,12913@port`); upstream keeps operator recording choices in `camera_settings.conf`. Judge in the Core units.
- Env knobs `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE` ride into the
  `buffer` event as `*_env` fields (`Core:App:262,266,268`); the bridge ignores them. Covered by `sweep-knobs.md`.
- QML timecode rework: `rev-UI-settings-qml.md` F2 and F10 agree with F5 here.

## Skeptic

Checked at UI `7ea9afc`, Core `01f170c` (cinemate-port) against the `*-upstream` worktrees.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Void returns and `value=on/off` confirmed (`B.hpp:194-198,200@port`). The rework was wrong on the wire: Core `set_storage_preroll` reads `value`, not `enabled` (`Core:App:12901@port`), and the WebUI sends `value` too (`WCP:15843@port`). Sending `enabled` needs a Core change. `applyCdngLog` should become `applyCdngLogEnabled` for the same naming reason |
| F2 | stands | Branches confirmed (`B.cpp:1332-1349@port`); Core spells the same counts `errors`/`warnings` in the event (`Core:App:12346-12348`) and `controls_errors`/`controls_warnings` in state (`:9458-9459`); media `state`/`mounted` vs `media_state`/`media_alive` (`:10826-10828` vs `:9555-9556`). `applyCoreState` already calls `applyBufferState` and `applyRecordingDroppedFrames` (`B.cpp:1457,1732@port`), so the `buffer` event can go into the list unchanged |
| F5 | stands | Two-arg signature, `"ui"` from the camera tap (`qml/CameraPage.qml:1842@port`) and Core triple write (`Core:App:13286-13298@port`) confirmed. Port `SettingsBridge::setTimecodeMode` persists UI.conf itself (`SettingsBridge.cpp:1223-1233@port`), so the UI-only path needs no Core call. Deliberate per `7029db1` and fork-log `909aaa5`; the split stays, only its API shape changes |
| F6 | stands | Third tier and the call in the camera-set block confirmed (`B.cpp:19-20,1016,1621@port`); upstream has two tiers (`B.cpp:17-18,875-882@up`) |
| F3 | corrected, minor -> nit | Upstream itself sets the member after a successful send in the camera-setting invokables (`applyH264Resolution`: `setH264ResolutionValue(...)` after send, `B.cpp:616-618@up`; `applyTimecodeMode` writes UI.conf after send, `:632-633@up`). Setting `m_bufferSetting`/`m_cdngLogOn` after the send is that form, though it bypasses a setter. Only `applyClipNameState(reply)` at `B.cpp:640@port` is a true double apply (the reply already went through `applyCoreMessage` -> `applyCoreState` -> `applyClipNameState`, `B.cpp:1210,1411-1412,1734@port`) |
| F4 | stands | Comment at `B.cpp:2666@port`, six string-or-number branches and the `asBool` lambda (`:2771-2777`) confirmed; Core emits all those fields unquoted/typed (`Core:App:257-263,306@port`; `CC:207-210@port`) |
| F7 | dropped | The rework loses the feature: Core's lock reads the measured gain under the controller mutex at that instant (`CC:11146-11165@port`, rounding fixed in `e5757d7`), while the UI's `isoInUse` can be up to 1 s old. `enabled=true/false` is the upstream boolean spelling (`set_photo_*_enabled`, `Core:App:9482,9514@up`). The mixed "port UI + original Core" case does not arise once UI and Core ship together (same reasoning as F9) |
| F8 | stands | Camera-set block is unconditional (`B.cpp:1582-1622@port`); on the `recording` event `applyCoreState(message)` runs before `setRecordingState` (`B.cpp:1352-1357@port`), and `setRecordingState` does not recompute (`setRecordingState` body, no `cameraSetValuesChanged`). On-screen effect unconfirmed: during a ramp, fps changes likely bring settings events quickly |
| F9 | corrected | `clipNameKnown` shares `clipNameChanged`; only `storagePrerollAutoKnown` has its own signal (`B.hpp:67,76,256@port`). Member line is `B.hpp:434`, not 430. `clipNameKnown` also hides the card until the first non-empty template arrives (`B.cpp:670-673@port`) |
| F10 | corrected | `std::clamp` is upstream style too (`AudioMeterBridge.cpp:179,203,205@up`); drop the qBound point, keep only the missing `<algorithm>` include. Clamp line is `B.cpp:2656`, not 2655. Comments with T31/T45/KB trap 7/CineMate/green confirmed (`B.cpp:275,1582,2666@port`; `B.hpp:18,82,424,435@port`) |

## Final findings

### UI-control-bridge-F1 [mismatch, major] Six new invokables return void; bool args sent as value=on/off and auto/off; names not in the upstream form
- where: src/ApertarControlBridge.hpp:194-198@cinemate-port ; src/ApertarControlBridge.hpp:200@cinemate-port ; src/ApertarControlBridge.cpp:618-630@cinemate-port ; src/ApertarControlBridge.cpp:686-701@cinemate-port ; src/ApertarControlBridge.cpp:716-727@cinemate-port
- port: `Q_INVOKABLE void` applyBufferMode / applyStoragePreroll / applyStoragePrerollAuto(bool on) / applyClipNameTemplate / requestClipNamePreview / applyCdngLog(bool on). set_storage_preroll sends `{"value": on ? "on" : "off"}`; set_cdng_log sends `value = on ? "auto" : "off"`.
- apertar way: Every command invokable returns bool; thin variants `return sendCoreCommand(...)`; booleans as `enabled="true"/"false"` with `apply<Thing>Enabled(bool enabled)` (src/ApertarControlBridge.cpp:736-741@upstream-1.6.0, applyPhotoLongExposureEnabled; Core reads `command.string("enabled")`, Core:App:9482,9514@upstream-1.6.0). Only notifyUserActivity/refresh are void (B.hpp:100,110@upstream-1.6.0). Actions are verbs (capturePhoto, calibrateGyro).
- why it matters: QML cannot tell success from refusal; the original developer reads `void apply*` as fire-and-forget, which upstream never does; on/off and auto/off are extra boolean spellings on the wire.
- rework: Make all six `bool`: `return false` after setLastError or a failed send, `return true` at the end, or `return sendCoreCommand(...)`. Rename applyStoragePreroll -> startStoragePreroll(). Replace applyStoragePrerollAuto(bool on) with applyStoragePrerollAutoEnabled(bool enabled) sending `enabled="true"/"false"`, and applyCdngLog(bool on) with applyCdngLogEnabled(bool enabled). Core: `set_storage_preroll` and `set_cdng_log` read `enabled` (today they read `value`, Core:App:12901,13080@cinemate-port); the WebUI senders (WCP:15451,15843@cinemate-port) switch to `enabled` in the same change. QML callers ignore the result; only the renamed names change there.
- effort: S
- deliberate: no. 841d0ed and 606f137 do not discuss return type or argument spelling.

### UI-control-bridge-F2 [mismatch, major] Second state path: dedicated buffer/controls/media event branches and a key-name-parameterised setter
- where: src/ApertarControlBridge.cpp:1332-1349@cinemate-port ; src/ApertarControlBridge.cpp:1424-1442@cinemate-port ; src/ApertarControlBridge.hpp:453@cinemate-port
- port: applyCoreMessage has branches `controls` -> setControlsStatus(message, "errors", "warnings"), `media` -> setCoreMediaState(state, mounted), `buffer` -> applyBufferState + applyRecordingDroppedFrames. applyCoreState calls the same mappers with the state spellings controls_errors/controls_warnings and media_state/media_alive. Core spells one value two ways (Core:App:12346-12348 vs :9458-9459; :10826-10828 vs :9555-9556 @cinemate-port).
- apertar way: Events whose fields are state keys go whole to applyCoreState: `if (event == "standby" || event == "still_exposure" || event == "timelapse_progress" || event == "media_write_state") { applyCoreState(message); return; }` (src/ApertarControlBridge.cpp:1191-1195@upstream-1.6.0); recording_health likewise (:1213-1216). No setter takes key names. Rule UI-S4.
- why it matters: State reaches properties through two paths with two key spellings. A maintainer who adds a key to applyCoreState misses the event path, or the other way round.
- rework: Core: the controls event emits controls_errors/controls_warnings, the media event emits media_state/media_alive (keep old names only if another reader needs them). UI: add `controls`, `media`, `buffer` to the upstream applyCoreState event list (applyCoreState already runs applyBufferState and applyRecordingDroppedFrames, B.cpp:1457,1732@cinemate-port). Delete the three branches. Delete setControlsStatus; put an inline compare/assign/emit for controls_errors/controls_warnings in applyCoreState in the form of recording_has_dropped_frames (B.cpp:1270-1276@upstream-1.6.0).
- effort: M
- deliberate: no. ea44bd7/160898c/841d0ed describe what is read, not why a separate path.

### UI-control-bridge-F5 [removed-upstream-behaviour, major] applyTimecodeMode gained a required target: upstream one-arg call gone, camera tap no longer sets file timecode
- where: src/ApertarControlBridge.cpp:750-771@cinemate-port ; src/ApertarControlBridge.hpp:202-203@cinemate-port ; src/ApertarControlBridge.cpp:1698-1708@cinemate-port ; qml/CameraPage.qml:1837-1843@cinemate-port
- port: `bool applyTimecodeMode(const QString &displayValue, const QString &target)`, target ui|files|both, no default. The camera tap and the "UI timecode" dropdown send "ui": QML writes settingsState.timecodeMode (which persists UI.conf, SettingsBridge.cpp:1223-1233@cinemate-port), the bridge writes UI.conf timecodeMode again, and Core writes it a third time (Core:App:13293-13298@cinemate-port).
- apertar way: `bool applyTimecodeMode(const QString &displayValue)` sets the camera mode and UI.conf (src/ApertarControlBridge.cpp:622-636@upstream-1.6.0; Core:App:9424-9437@upstream-1.6.0). The camera tap changes both (qml/CameraPage.qml:1709-1715@upstream-1.6.0). The UI-side value is SettingsBridge.timecodeMode, READ/WRITE (rule UI-S5).
- why it matters: A one-argument caller fails with "Insufficient arguments". The operator's tap no longer changes the timecode written into clips, which the original developer would not expect. A stringly `target` selector on an apply* has no precedent.
- rework: Restore the one-argument applyTimecodeMode(displayValue) (Core: no target = both). Add `bool applyFileTimecodeMode(displayValue)` sending target="files" and setting fileTimecodeMode. A UI-only change is `settingsState.timecodeMode = v` with no Core call. Delete the target parameter and its validation. The camera tap returns to upstream behaviour unless the owner keeps the split tap; then document it for the original developer. QML side: rev-UI-settings-qml.md F2.
- effort: M
- deliberate: yes. 7029db1: "the tap on the camera screen toggles the UI timecode only"; fork-log 909aaa5.

### UI-control-bridge-F6 [mismatch, minor] 1 s full get_state poll while auto ISO/WB; updateRefreshTimer on every state pass
- where: src/ApertarControlBridge.cpp:19-20@cinemate-port ; src/ApertarControlBridge.cpp:1016@cinemate-port ; src/ApertarControlBridge.cpp:1621@cinemate-port
- port: kLiveValuePollIntervalMs = 1000; the steady interval is 1 s while m_isoAuto || m_whiteBalanceAuto. updateRefreshTimer() is called at the end of the camera-set block in applyCoreState.
- apertar way: Two tiers: 1 s while disconnected, 30 s steady (src/ApertarControlBridge.cpp:17-18,875-882@upstream-1.6.0). Core pushes a live value as its own event, mapped in one line: audio_level (B.cpp:1196-1199@upstream-1.6.0).
- why it matters: While auto ISO or WB is on, the GUI thread parses the whole state and runs all of applyCoreState every second, 30x upstream's cadence. The settings event carries iso_actual (CC:175@cinemate-port) but fires only on settings changes, so the poll is the only feed today.
- rework: Core publishes a small rate-limited event only on change, e.g. {"event":"exposure_measured","iso_actual":..,"wb_actual_kelvin":..,"wb_measured":..}, as it publishes audio_level. The UI adds it to the applyCoreState event list (F2). Delete kLiveValuePollIntervalMs, the ternary at :1016 and the call at :1621.
- effort: M
- deliberate: yes. f1edf96: "While auto ISO or WB runs the bridge asks for the state every second (30 s otherwise)".

### UI-control-bridge-F4 [slop, minor] String-or-number tolerant parsing justified by "KB trap 7"; Core emits typed JSON
- where: src/ApertarControlBridge.cpp:2666@cinemate-port ; src/ApertarControlBridge.cpp:2692-2759@cinemate-port ; src/ApertarControlBridge.cpp:2768-2783@cinemate-port
- port: `// Core's flat JSON delivers scalars as strings (KB trap 7); accept numbers too.` then `raw.isString() ? raw.toString().toDouble() : raw.toDouble(0.0)` and string-or-bool branches six times, plus an asBool lambda in applyCdngLogState.
- apertar way: Typed accessors with a default: `state.value("iso_auto").toBool(m_isoAuto)` (src/ApertarControlBridge.cpp:1321@upstream-1.6.0). Core emits these fields typed: buffer_safety_stop, buffer_stop_percent, storage_preroll_active/auto/fps (Core:App:257-263@cinemate-port), buffer_fill (:306), cdng_log_bits/available/applied (CC:207-210@cinemate-port).
- why it matters: About 40 lines of dead generality; the comment cites an internal KB trap about Core's request parser, not its output.
- rework: Use .toDouble()/.toInt()/.toBool() with the member as default; delete the lambda and the comment.
- effort: S
- deliberate: no

### UI-control-bridge-F8 [bug, minor] shutterSetByCamera reads m_recording before setRecordingState in the same pass
- where: src/ApertarControlBridge.cpp:1610@cinemate-port ; src/ApertarControlBridge.cpp:1730-1731@cinemate-port ; src/ApertarControlBridge.cpp:1352-1357@cinemate-port
- port: `shutterSet = m_recording && m_fpsSpeedRamp && m_fpsSpeedRampKeepExposure` in the unconditional camera-set block. The `recording` event calls applyCoreState(message) first and setRecordingState(active) after; setRecordingState does not recompute or emit cameraSetValuesChanged.
- apertar way: no precedent
- why it matters: In a speed-ramp take with the Exposure policy, the shutter's camera-set mark lags one state pass at start and stays after stop until the next pass (30 s poll if auto ISO/WB is off and nothing else changes). On-screen effect unconfirmed: needs the Pi; ramp fps changes probably bring settings events sooner.
- rework: Recompute m_shutterSetByCamera in setRecordingState and emit cameraSetValuesChanged there, or move the camera-set block below the `recording` key handling.
- effort: S
- deliberate: no

### UI-control-bridge-F9 [new-ground, minor] Presence latches storagePrerollAutoKnown / clipNameKnown for "older Core"
- where: src/ApertarControlBridge.cpp:670-673@cinemate-port ; src/ApertarControlBridge.cpp:2746-2749@cinemate-port ; src/ApertarControlBridge.hpp:67,76,256@cinemate-port ; src/ApertarControlBridge.hpp:417@cinemate-port ; src/ApertarControlBridge.hpp:434@cinemate-port ; qml/SettingsPage.qml:2031,5611@cinemate-port
- port: Two extra properties that go true once Core has sent the key (clipNameKnown: a non-empty template); QML hides the controls until then. storagePrerollAutoKnown has its own signal; clipNameKnown rides on clipNameChanged.
- apertar way: Feature presence comes from flags Core sends: recording_capabilities, wb_available, exposure_compensation_available (src/ApertarControlBridge.cpp:1286-1304,1331,1360-1366@upstream-1.6.0). No "key was absent" latch.
- why it matters: After the merge UI and Core ship together, so the latches only matter for mixed versions. Two properties and one signal for little benefit.
- rework: Drop the *Known properties and show the controls. If mixed versions must work, Core sends one capability flag inside recording_capabilities.
- effort: S
- deliberate: no

### UI-control-bridge-F10 [slop, nit] Ticket ids, other product name, stale comments; missing include; setter among members
- where: src/ApertarControlBridge.cpp:275@cinemate-port ; src/ApertarControlBridge.cpp:1582@cinemate-port ; src/ApertarControlBridge.cpp:2656@cinemate-port ; src/ApertarControlBridge.cpp:2666@cinemate-port ; src/ApertarControlBridge.hpp:18@cinemate-port ; src/ApertarControlBridge.hpp:82@cinemate-port ; src/ApertarControlBridge.hpp:424@cinemate-port ; src/ApertarControlBridge.hpp:435@cinemate-port ; src/ApertarControlBridge.hpp:453@cinemate-port
- port: Comments carry "(T31)", "T45:", "(KB trap 7)", "CineMate Log", "shown green" (QML shows italics since 35b31f6) and "older Core". std::clamp<qint64> is used without `#include <algorithm>` (compiles through transitive includes). setControlsStatus is declared among the data members.
- apertar way: Comments are rare, one or two lines, and say why (conv-ui-cpp section 11; e.g. B.cpp:861-862@upstream-1.6.0). std::clamp is upstream style too, with its include (AudioMeterBridge.cpp:179@upstream-1.6.0).
- why it matters: Internal ticket numbers and another product's name mean nothing to the original developer; the stale colour comment misdescribes the UI.
- rework: Rewrite the comments in plain terms ("speed ramp", "hardware file check"); drop the ids and "CineMate". Add `#include <algorithm>`. setControlsStatus goes away with F2.
- effort: S
- deliberate: no

### UI-control-bridge-F3 [duplication, nit] Clip-name reply applied twice
- where: src/ApertarControlBridge.cpp:635-641@cinemate-port
- port: applyClipNameTemplate calls applyClipNameState(reply) after sendCoreCommand, which already fed the reply to applyCoreMessage -> applyCoreState -> applyClipNameState (B.cpp:1210,1411-1412,1734@cinemate-port). applyBufferMode and applyCdngLog set m_bufferSetting / m_cdngLogOn directly after the send (B.cpp:697-700,723-726), bypassing a setter.
- apertar way: Thin variants rely on the reply: applyCaptureMode `return sendCoreCommand(...)` (B.cpp:731-734@upstream-1.6.0). Older camera-setting invokables set the value through a setter after the send (applyH264Resolution, B.cpp:616-618@upstream-1.6.0), so the post-send set in applyBufferMode/applyCdngLog is an upstream form, not a mismatch.
- why it matters: The double apply suggests the reply is not applied automatically, which misleads the next maintainer.
- rework: Delete `applyClipNameState(reply)` and the reply object; with F1 it becomes `return sendCoreCommand(...)`. Optional: route the buffer/cdng post-send assignments through the same compare/emit used by the state mappers, or drop them as F1 makes the bodies thin.
- effort: S
- deliberate: no

Dropped: F7 (see Skeptic table).
