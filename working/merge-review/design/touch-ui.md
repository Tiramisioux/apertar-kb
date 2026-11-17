# The touch UI: bridge idioms, presets, timecode, first start: design

Read at Apertar-UI `work/improve` `ac1fc28` (`/home/user/wt/ui-work`) and Apertar-Core `work/improve` `d1dcdee` (`/home/user/wt/core-work`, line numbers from `git show HEAD:`), against `upstream-1.6.0` (`/home/user/wt/ui-upstream` `43888e5`, `/home/user/wt/core-upstream` `35dbe67`).

## In short

- Today: six new bridge invokables return `void` and two send booleans as `value=on|off` and `value=auto|off`. Core's `controls`, `media` and `buffer` events take a second route into the bridge, with their own key spellings and a setter that takes key names. Three choices (Write Buffer, Log, automatic pre-roll) and the clip-name presets are ActionTiles whose accent colour flips like a radio button.
- Touch presets do not save the settings the port added (Clear HDR knobs, speed ramp, phase lock, file timecode). The timecode tap and the Settings "Mode" row no longer change the timecode written into clips. The touch UI's IMX585 sizes are not Core's. A dead fallback still caps 4K Clear HDR 16-bit at 25 fps. Nothing writes the first hardware file.
- Target: every invokable that sends a command returns `bool` (UIC-9). Booleans go as `enabled=`, enums as `value=` (UIC-12, C1-I05). Every event made of state keys goes whole to `applyCoreState`, as in 1.6.0. A choice is a TogglePill or an InlineDropdownField, never a tinted ActionTile. Both preset writers carry the same `camera*` keys again. `applyTimecodeMode(v)` has one argument and sets both timecodes, as in 1.6.0. Keeping the file timecode apart is opt-in through one UI.conf switch.
- The fps fallback goes back to 1.6.0's numbers. The IMX585 lists become hand copies of Core's per-class tables (QML-9) once the camera-modes theme has fixed the sizes. The first-start file is written by Core (hardware-inputs theme); the UI only stops naming a file that does not exist.
- 24 commits: 19 in Apertar-UI, 5 in Apertar-Core. All are small; about -510 / +350 lines in all. The largest is the deletion of the clip-name drag layer (-210).

## How it works in the port today

Paths: `ACB` = `Apertar-UI/src/ApertarControlBridge.cpp`, `ACBH` = its `.hpp`, `SB` = `src/SettingsBridge.cpp`, `SP` = `qml/SettingsPage.qml`, `CPg` = `qml/CameraPage.qml`, `CNC` = `qml/ClipNameCard.qml`, `App` = `Apertar-Core/src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `CC` = `src/camera/CameraController.cpp`. "GUI thread" = the Qt main thread; the bridge blocks it on each command for at most 3 s (UIC-16). Core commands run under `commandMutex_` in `handleCommand`.

### Bridge invokables and their wire form

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Write buffer `frames`/`ram` | QML `applyBufferMode(v)`, `void`, then sets `m_bufferSetting` itself (`ACB:686-700`); Core `set_buffer_mode value=` (`App:12846`) | Core recorder at the next take; bridge `applyBufferState` (`ACB:2664`) | GUI thread; Core command lock, then the hardware-config store | `apertar-hardware.conf` `[storage] buffer=` (storage-settings theme) | Touch: two ActionTiles, accent on the chosen one (`SP:3430-3449`). WebUI: Media card |
| cDNG Log `off`/`auto` | QML `applyCdngLog(!on)`, `void`, sends `value=auto|off` (`ACB:716-727`); Core `cdngLogFromString` accepts `off/auto/on/12/10/8` (`App:13095`, `include/apertar/core/Types.hpp:338-344`) | `CC` per take; state `cdng_log` string (`App:356`) -> `applyCdngLogState` (`ACB:2769`) | GUI thread; command lock -> `camera_.setCdngLog` | `camera_settings.conf` `cdng_log=` (`CC:959`) | Touch: one ActionTile labelled On/Off, accent when on (`SP:3476-3482`). WebUI: `value: value === "On" ? "auto" : "off"` (`WCP:15451`) |
| Automatic pre-roll on/off | QML `applyStoragePrerollAuto(bool)`, `void`, sends `value=on|off` (`ACB:623-629`); Core lower-cases and accepts six spellings (`App:12917-12923`) | Core at start, card insert, format; state `storage_preroll_auto` -> `ACB:2738-2749`, which also latches `storagePrerollAutoKnown` | as above | `apertar-hardware.conf` `[media] preroll=` (storage-settings theme) | Touch: On / Off ActionTiles, hidden until the latch (`SP:5608-5640`). WebUI: `value: value === "On" ? "on" : "off"` (`WCP:15843`) |
| Storage pre-roll take | QML `applyStoragePreroll()`, `void` (`ACB:617-621`) -> `storage_preroll` | Core (preroll theme) | as above | none | ActionTile "Storage Pre-roll" (`SP:5600-5606`) |
| Clip-name template | `CNC` save timer -> `applyClipNameTemplate`, `void`; feeds the reply through `applyClipNameState` a second time (`ACB:631-641`) although `sendCoreCommand` already did (`ACB` loop calls `applyCoreMessage`, which ends in `applyCoreState` for any reply with `ok`) | Core `set_clip_name_template`; state `clip_name_template` -> `applyClipNameState` (`ACB:659-680`), which latches `clipNameKnown` | GUI thread; command lock | `camera_settings.conf` | `CNC` (601 lines) + `ClipNamePill.qml` (115), card hidden until `clipNameKnown` (`SP:2031`). WebUI composer (webui-state theme) |
| Clip-name preview | `CNC` 350 ms timer -> `requestClipNamePreview`, `void` (`ACB:643-657`) | `clipNamePreview` | GUI thread | none | "Next clip" line in `CNC` |

### The second state path

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Controls error and warning counts | Core: `controls` event spells them `errors`/`warnings` (`App:12352-12354`); state spells them `controls_errors`/`controls_warnings` (`App:9462`, `:12963`) | `applyCoreMessage` branch -> `setControlsStatus(message,"errors","warnings")` (`ACB:1332-1335`); `applyCoreState` -> `setControlsStatus(state,"controls_errors",...)` (`ACB:1439`). The setter takes the key names (`ACB:1424-1435`) | Event socket on the GUI thread; Core publishes from the controls worker through `publishEvent` (`App:14890-14910`) | none | `ControlsWarning.qml` |
| Media state | Core: `media` event spells `state`/`mounted` (`App:10828-10838`); state spells `media_state`/`media_alive` (`App:9559-9560`, `:12977-12978`) | event branch `setCoreMediaState(state, mounted)` (`ACB:1336-1340`); `applyCoreState` (`ACB:1440-1442`); signal to `MediaStatusBridge` (`src/main.cpp:319`) | as above, from Core's media watcher thread | none | media chip, NO MEDIA |
| Buffer fill and setting | Core `buffer` event = `bufferMembers` + `recording_dropped_frames` (`App:10843-10847`, `:301-311`) | event branch calls `applyBufferState` and `applyRecordingDroppedFrames` by hand (`ACB:1344-1349`); `applyCoreState` calls the same two (`ACB:1457`, `:1732`) | as above, from Core's buffer poller | none | buffer bar, dropped-frames chip |

### Presets

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Touch preset, camera part | `ACB::cameraPresetSettings` (`ACB:1254-1286`), byte-identical to 1.6.0; merged into `SB::serializeCurrentSettings` (`SB:2209-2214`) | load: `applyCameraPreset` forwards every `camera*` key and `timecodeMode` to Core `apply_preset` (`ACB:1288-1300`) | GUI thread; Core command lock | the preset JSON the touch UI writes | Settings > Presets |
| WebUI preset | `buildCurrentPresetPayload` (`App:7701`; camera keys `App:7846-7887`) adds `cameraFpsSpeedRamp*`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraConformFps`, `cameraClearHdr`, `cameraHdr*` (4), `cameraCdngLog` | `apply_preset` (`App:14339-14395`); `timecodeMode` alone also sets the files' mode (`App:14443-14448`) | HTTP thread, command lock | preset JSON written by Core | WebUI preset library |

### Timecode

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| UI timecode (screens) | tap `toggleTimecodeMode` -> `settingsState.timecodeMode` + `applyTimecodeMode(next,"ui")` (`CPg:1837-1843`); Settings "UI timecode" row (`SP:3995-4012`); bridge writes UI.conf again (`ACB:762-765`); Core writes it a third time for `target != files` (`App:13295-13315`) | `SB` property `timecodeMode` (`SB:372`, `:1234`); Core `readSharedUiSettings` reads UI.conf on each use (`App:1983`) | GUI thread | `UI.conf` `timecodeMode` | top bar timecode, HDMI |
| File timecode (clips, WAV) | Settings "File timecode" row -> `applyTimecodeMode(v,"files")` (`SP:4014-4028`); Core `camera_.setTimecodeMode` unless `target=ui` (`App:13295-13315`) | state `timecode_mode` -> `m_fileTimecodeMode` (`ACB:1698-1707`) | GUI thread; command lock | `camera_settings.conf` | Settings row; WebUI two blocks (`WCP:9809-9826`) |
| Labels | `timecodeChoices` "Time of Day"/"Clip" (`SP:21`), `timecodeDisplayName` (`SP:1219`) | dropdowns | - | stored values stay "Free Run"/"Rec Run" | Settings, WebUI |

### Lists, caps, first start

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| IMX585 sizes | Core per class S12/S10/H12/H16 (`src/camera/Imx585Modes.hpp`, commit `caa0153`); Core migrates `3840x2076` -> `2072`, `1920x1038` -> `1036` (`CC:441-450`); WebUI hand copy `imx585ClassModes` (`WCP:8915-8920`) | touch lists are 1.6.0's: `imx585Raw12ResolutionOptions`, `imx585CropRatioOptions`, `imx585FullHdCropRatioOptions` (`CPg:418-446`, `SP:161-189`) | QML | `camera_settings.conf` `resolution=` | Touch offers 2076/1038 and lacks 2K crop, 4:3, 1:1; after a pick of 2076 Core reports 2072, which is not in the list |
| IMX585 fps fallback | `maximumSupportedFpsForResolution` 25 for 4K Clear HDR 16-bit (`CPg:818-842`, commit `d1efb67`); same in App's fallback (`App:1386-1389`) | `fpsCeiling()` uses it only when Core's `fps_max` is 0 (`CPg:904-918`); `availablePcfFpsOptions` likewise (`App:1411-1416`) | QML / command lock | none | dead with the port Core, wrong against a 1.6.0 Core (30) |
| IMX585 built-in fps list | QML `{24,25,30,50,60}` (`CPg:923-930`) vs Core `{24,25,30,50,60,100,120}` (`App:1398-1406`) | fps picker when UI.conf has no `fpsSteps` | QML | - | touch lacks 100/120 |
| First hardware file | nobody since UI `c9d841f` removed both writers; Core only shows `defaultHardwareConfigTemplate()` in the editor (`App:5035`, `:6205`) | `DisplayConfigBridge` and `Ina219Bridge` skip a missing file and use their compiled defaults (`src/DisplayConfigBridge.cpp:17-35`, `src/Ina219Bridge.cpp:262-267`) | UI start | `/home/pi/apertar-hardware.conf` (absent) | INA219 log says "using defaults in /home/pi/apertar-hardware.conf", a file that does not exist |

## How original Apertar does this kind of thing

| Kind | Precedent (`@upstream-1.6.0`) |
| --- | --- |
| Invokables return `bool` | `ui-upstream src/ApertarControlBridge.hpp:111-141`: every command invokable is `bool`; only `notifyUserActivity()` and `refresh()` are `void` (`:100`, `:110`). Thin form: `bool applyCaptureMode(mode) { return sendCoreCommand(...); }` (`ACB:731-734`). Rule UIC-9 |
| Boolean on the wire | `applyPhotoLongExposureEnabled(bool enabled)` sends `enabled = "true"/"false"` (`ACB:736-741`); Core `const bool value = (*enabled == "true" || *enabled == "1");` after a presence check (`core-upstream App:9482-9486`). Rules UIC-12, C1-I05 |
| Enum on the wire | `applyCdngCompression(const QString &value)` sends `value=` (`ACB:516-535`); Core `set_cdng_compression` refuses an unknown value (`App:9340-9346`) |
| An event made of state keys | `if (event == "standby" || ... || event == "media_write_state") { applyCoreState(message); return; }` (`ACB:1191-1195`); `recording_health` the same (`:1213-1216`). Bools and counters inline compare/assign/emit in `applyCoreState` (`recording_has_dropped_frames`, `:1270-1276`). Rule UIC-4 |
| A Core-owned switch in Settings | Still Mode toggles: `if (apertarControlBridge.applyPhotoLongExposureEnabled(checked)) settingsState.photoLongExposureEnabled = checked` (`SP:2940-2946`). A row with title, description and `TogglePill` (`gyroRecordToggle`, `SP:3562`). Rule QML-8 |
| A choice of values | `InlineDropdownField` "Compression" with `{value,label}` options, `onValueSelected: applyCdngCompression(v)` (`SP:3244-3261`). ActionTile is a verb with a fixed tone (`SP:3640`, `:3650`, `:5416` accent Standby, danger for destructive); no conditional `tone:` in any upstream QML file. Rules QML-23, QML-26 |
| Presets | Two writers with the same `camera*` set: Core `buildCurrentPresetPayload` (`core-upstream App:6663-6690`) and touch `cameraPresetSettings` (`ACB:1118-1150`). One reader, `apply_preset`. Recipe R2 step 10 |
| Timecode | One `bool applyTimecodeMode(displayValue)`: sends `set_timecode_mode value=`, writes UI.conf (`ACB:622-636`). Core sets camera and UI.conf together (`core-upstream App:9424-9436`). The tap changes both (`CPg:1709-1715`). `applyCoreState` copies Core's `timecode_mode` into UI.conf (`ACB:1466-1471`). Labels "Free Run"/"Rec Run" (`SP:3753-3782`) |
| A UI-only preference | `SettingsBridge` READ/WRITE/NOTIFY property backed by UI.conf, constructor read, `pollExternalSettings`, presets; QML assigns `settingsState.<prop> = v`, no socket command. Rules UIC-13, QML-7, recipe R3 steps 1-2 |
| Option lists and caps | Hand copies in App, WCP and both QML pages, identical in `CPg` and `SP` (`CPg:418`, `SP:161`; core-map 4.5). Rule QML-9, recipe R6 step 4. The QML/App tables are the fallback when Core sends no `fps_max` |
| First hardware file | The UI wrote `/home/pi/apertar-hardware.conf` from a commented template when it was missing (`src/DisplayConfigBridge.cpp:41-326`, called at `:587`; second copy `src/Ina219Bridge.cpp:69-342`, `:497`). Core only shows its template |
| Drag in QML | Only the reorder and sidebar popups: `held` flag, `drag.target` on the content item, `Drag.active: held`, `pressAndHoldInterval 260` (`SP:6111-6211`, `:6282-6297`). Settings apply on selection, without timers |

## The target

| Value | Before (port) | After |
| --- | --- | --- |
| Write buffer | `void applyBufferMode`; two tinted ActionTiles | `bool applyBufferMode(value)`, thin; `InlineDropdownField` "Write Buffer" Frames/RAM. Wire unchanged (`value=frames|ram`, an enum). Where it is stored: storage-settings theme |
| cDNG Log | `void applyCdngLog(bool)` sending `auto|off`; tinted ActionTile | `bool applyCdngLog(value)` taking Core's enum `off`/`auto`, thin, like `applyCdngCompression`; `InlineDropdownField` "Log" Off/On next to Compression. Core unchanged. State `cdng_log` unchanged |
| Automatic pre-roll | `void applyStoragePrerollAuto(bool)` sending `value=on|off`; two tinted ActionTiles behind a presence latch | `bool applyStoragePrerollAutoEnabled(bool enabled)` sending `enabled="true"/"false"`; Core reads `enabled` in the C1-I05 form; a TogglePill row like `gyroRecordToggle`; latch deleted. Where it is stored: storage-settings / preroll themes |
| Pre-roll take | `void applyStoragePreroll()` | `bool startStoragePreroll()` (a verb, UIC-10), thin |
| Clip name | `void applyClipNameTemplate` + double apply; `void requestClipNamePreview`; card hidden until `clipNameKnown` | both `bool`, thin; latch deleted; card always shown |
| Controls / media / buffer events | three branches, key-name setter | Core events carry state keys (`controls_errors`, `controls_warnings`, `media_state`, `media_alive`); the three events join the upstream `applyCoreState` list; `setControlsStatus` deleted, inlined as compare/assign/emit |
| Touch preset | 1.6.0 key set | 1.6.0 set + every key Core's writer adds, under Core's names and value words, from members kept in `applyCoreState` |
| Timecode, default | tap and "UI timecode" set the screens only; "File timecode" sets the clips | as 1.6.0: one row "Mode", Free Run / Rec Run, `applyTimecodeMode(v)` with one argument, sets both; tap sets both |
| Timecode, set apart (opt-in) | always apart | a "Files" row: "Same as Mode" (default) / Free Run / Rec Run. Picking a fixed value calls `applyFileTimecodeMode(v)` (`target=files`) and sets UI.conf `fileTimecodeSeparate=true`; while true, the tap and "Mode" change only `settingsState.timecodeMode` (UI-only, QML-7). "Same as Mode" clears the switch and calls `applyTimecodeMode(Mode)` |
| IMX585 lists | 1.6.0 lists | hand copies of Core's per-class tables in `CPg` and `SP`, class from raw bit depth and Clear HDR as `imx585ClassKeyFor` (`WCP`), after the camera-modes theme fixes the sizes |
| fps fallback | 25 in 4K Clear HDR 16-bit | 30, as 1.6.0 (QML and App); 100/120 in the QML IMX585 built-in list as in Core |
| First hardware file | none | Core writes it at first start (hardware-inputs theme). UI: no writer; the INA219 log says no file was found |

Where each value lives and who owns it does not move in this theme: camera settings stay in `camera_settings.conf` (Core), UI preferences in UI.conf (`SettingsBridge`), `[storage]`/`[media]` keys wherever the storage-settings theme puts them. The one new key is UI.conf `fileTimecodeSeparate` (bool, absent = false = 1.6.0 behaviour). No key moves between files, so no take-over of old keys is needed. Every field 1.6.0 publishes stays; the only reply fields that change are inside the port's own `controls` and `media` events, which 1.6.0 does not have.

## Commit plan

"Check here" always includes: `/home/user/build/bin/check_core.sh /home/user/wt/core-work <tag> both tests` (both builds, 17 host tests) for a Core commit, `/home/user/build/bin/check_ui.sh /home/user/wt/ui-work <tag>` for a UI commit, and for a Core commit `smoke_core.sh` against the previous build with the two outputs diffed (no 1.6.0 field gone or retyped). Pi commands use `apertar-cmd` as shorthand for `printf '%s\n' '<json>' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`.

### Bridge idioms

**1. `ui: clip-name, buffer, log and pre-roll invokables return bool`** (Apertar-UI)
- `ACBH:194-200`, `ACB:617-727`: `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto`, `applyClipNameTemplate`, `requestClipNamePreview`, `applyCdngLog` become `bool`. Early returns return `false` after `setLastError`; the end returns `true` or `return sendCoreCommand(...)`.
- Delete the second `applyClipNameState(reply)` and its `QJsonObject reply` in `applyClipNameTemplate` (the reply already passed through `applyCoreMessage`). Delete the post-send assignments of `m_bufferSetting` and `m_cdngLogOn`: the replies carry `buffer_setting` (`App:256`) and `cdng_log` (settings body), which `applyBufferState` / `applyCdngLogState` already apply.
- No wire change; QML ignores the results. About -22 / +12.
- Here: UI build. Pi: Settings > Record, switch Write Buffer and Log; values follow as before.
- Depends on nothing.

**2. `qml: Log is a dropdown next to Compression, sent as Core's off or auto`** (Apertar-UI)
- `ACB`/`ACBH`: `bool applyCdngLog(const QString &value)`: refuse anything but `off`/`auto` with "Invalid Log value.", then `return sendCoreCommand("set_cdng_log", {{"value", value}})`.
- `SP:3463-3492`: replace the ActionTile with `InlineDropdownField { label: "Log"; value: cdngLogOn ? "auto" : "off"; options [{off,"Off"},{auto,"On"}]; fieldEnabled: !recording; onValueSelected: applyCdngLog(v) }`, shaped like Compression (`SP:3244` upstream). Keep the `#9aa5b1` status text.
- Core unchanged: `cdng_log` is an enum in `CaptureSettings`, in `camera_settings.conf` and in state, so `value=` is the upstream form for it (as `set_cdng_compression`).
- About -14 / +18. Here: UI build. Pi: cDNG + Clear HDR, pick Log On, `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"cdng_log":"[a-z]*"'` shows `auto`.
- Depends on 1.

**3. `qml: Write Buffer is a dropdown`** (Apertar-UI)
- `SP:3415-3460`: the two ActionTiles become one `InlineDropdownField { label: "Write Buffer"; value: bufferSetting; options frames/"Frames", ram/"RAM"; fieldEnabled: !recording; onValueSelected: applyBufferMode(v) }`. Status text kept.
- About -20 / +10. Here: UI build. Pi: pick RAM, start and stop a take, `grep '^buffer=' ~/apertar-hardware.conf` (or the file the storage-settings theme names).
- Depends on 1. If storage-settings renames `set_buffer_mode`, only the bridge line changes.

**4. `core: set_storage_preroll takes enabled=true|false`** (Apertar-Core)
- `App:12917-12923`: read `command.string("enabled")` with the C1-I05 test (`== "true" || == "1"`); when absent, read the old `value=` (one release, for a UI from before commit 5). Delete the `tolower` loop and the six-spelling parse.
- `WCP:15843`: the WebUI sends `enabled: value === "On" ? "true" : "false"`; the patch `case "set_storage_preroll"` (`WCP:14030`) reads `enabled`.
- About -6 / +7. Here: both builds, tests; in `--simulate`: `curl -s -XPOST localhost:<port>/api/command -d '{"cmd":"set_storage_preroll","enabled":"true"}'` then `/api/state` shows `storage_preroll_auto` true; the same with `value=on` still works. Headless Chromium: the WebUI switch round-trips.
- Pi: nothing new beyond the WebUI switch.
- Depends on the preroll theme only if it renames the command (then this commit is folded into theirs).

**5. `qml: automatic pre-roll is a toggle row, the pre-roll take a verb`** (Apertar-UI)
- `ACB`: `bool applyStoragePrerollAutoEnabled(bool enabled)` sends `enabled`; rename `applyStoragePreroll` -> `bool startStoragePreroll()`. Delete `storagePrerollAutoKnown` (`ACBH:67`, `:148`, `:256`, `:417`; `ACB:2746-2749`).
- `SP:5600-5640`: the tile calls `startStoragePreroll()`; the On/Off tiles become a title + description + `TogglePill` row copied from `gyroRecordToggle`, `onToggled: apertarControlBridge.applyStoragePrerollAutoEnabled(value)`, `checked: storagePrerollAuto`; drop the `visible:` latch.
- About -45 / +25. Here: UI build. Pi: toggle, then `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"storage_preroll_auto":[a-z]*'`.
- Depends on 4.

**6. `core: set_storage_preroll reads only enabled`** (Apertar-Core)
- `App`: delete the `value=` fallback from commit 4. About -3 / +0. Here: builds, tests, `--simulate` curl with `value=on` is refused with "set_storage_preroll needs enabled=true or enabled=false.".
- Depends on 5 being deployed on the rig.

### One state path

**7. `core: the controls and media events carry the state keys`** (Apertar-Core)
- `App:12352-12354`: the `controls` event writes `controls_errors` / `controls_warnings` instead of `errors` / `warnings`.
- `App:10828-10838` `mediaEventJson`: `media_state` / `media_alive` instead of `state` / `mounted`. The other members (`device`, `fstype`, `free_bytes`, `total_bytes`, `errno`) stay; no bridge reads them in `applyCoreState` (grep: none).
- The `state` rename is required: once the event goes into `applyCoreState` (commit 8), a top-level `state` would be read as the camera state.
- No other reader: the WebUI does not take events (`WCP` has no `EventSource`), `handleTriggerEvent` matches neither event (`App` `handleTriggerEvent`), the UI's preview client ignores them.
- About -4 / +4. Here: builds, tests; `--simulate` with `socat` on the socket shows the new keys after `set_controls` and after a media change; smoke diff shows no 1.6.0 field change (these events are port-only).
- Pi: until commit 8 is deployed, the touch UI's controls badge and media chip follow the get_state poll (1-5 s) instead of the event.
- Depends on nothing.

**8. `ui: controls, media and buffer events go through applyCoreState`** (Apertar-UI)
- `ACB:1328-1349` `applyCoreMessage`: add `controls`, `media`, `buffer` to the upstream `if (event == "standby" || ...)` list; delete the three branches.
- Delete `setControlsStatus` (`ACB:1424-1435`, `ACBH:453`); in `applyCoreState` replace its call (`ACB:1439`) by the inline form of `recording_has_dropped_frames`: `if (state.contains("controls_errors")) { compare both, assign, emit controlsStatusChanged(); }`.
- `setCoreMediaState` stays: it emits the signal `MediaStatusBridge` listens to.
- The buffer event now runs all of `applyCoreState`; every key in it is checked with `contains`, the same cost class as `recording_health` upstream. Core sends it about four times a second during a take at most (`App:11037-11049`).
- About -30 / +12. Here: UI build. Pi: during a take the buffer bar moves; pull the card: NO MEDIA within a second; save a bad pin in Controls: the warning chip appears.
- Depends on 7.

### Presets

**9. `ui: touch presets carry the camera settings Core's presets carry`** (Apertar-UI)
- `ACB::applyCoreState`: keep as plain members (no `Q_PROPERTY`, nothing in QML reads them) the keys not yet kept: `fps_speed_ramp_stretch_audio`, `fps_speed_ramp_after`, `fps_phase_lock`, `hdr_threshold_high`, `hdr_threshold_low`, `hdr_blend`, `hdr_gain_adder`. Already kept: `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `clip_name_template`, `clear_hdr`, `timecode_mode` (as `m_fileTimecodeMode`), `cdng_log`.
- `ACB::cameraPresetSettings` (`ACB:1254-1286`): insert, in Core's order and value words (`App:7848-7872`): `cameraFpsSpeedRamp` (bool), `cameraFpsSpeedRampShutter` `angle|exposure`, `cameraFpsSpeedRampAudio` `real|stretch`, `cameraFpsSpeedRampAfter` `stay|return`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode` `free_run|rec_run`, `cameraClearHdr`, the four `cameraHdr*` numbers, `cameraCdngLog` `off|auto`. Bools and numbers as the JSON types Core's writer uses.
- `cameraConformFps` only if `conform_fps` survives (X-knobs-12 / CC-1-F6 say it does nothing; whichever theme deletes or keeps it adds or skips this one line).
- Loading needs no change: `applyCameraPreset` forwards every `camera*` key.
- About -0 / +40. Here: UI build. Round trip without the touch screen: in `--simulate`, send `apply_preset` over the socket with a JSON made of exactly the keys `cameraPresetSettings` now writes (copy them from the code), then `get_state`: every value matches. Pi: save a preset on the touch screen with Clear HDR 16-bit and Log on, change both, load it: both come back.
- Depends on 2 (Log value words).

### Timecode

**10. `ui: applyTimecodeMode takes one argument and sets both timecodes again`** (Apertar-UI)
- `ACB:750-771`, `ACBH:203`: `bool applyTimecodeMode(const QString &displayValue)` returns to the 1.6.0 body (`ui-upstream ACB:622-636`): send `set_timecode_mode value=` with no target, write UI.conf. Add `bool applyFileTimecodeMode(const QString &displayValue)` that sends `target=files` and nothing else; `m_fileTimecodeMode` follows from the reply's `timecode_mode` through `applyCoreState` (`ACB:1698-1707`), which also settles X-protocol-security-4 against a 1.6.0 Core.
- `CPg:1837-1843`: the tap calls `applyTimecodeMode(nextMode)`, as 1.6.0.
- `SP:3995-4028`: the first row is 1.6.0's verbatim (label "Mode", `applyTimecodeMode(v)`); the second row "Files" calls `applyFileTimecodeMode(v)`.
- Core unchanged (`App:13295`: no target means both).
- About -18 / +16. Here: UI build. `--simulate`: `set_timecode_mode value=rec_run` with no target -> `get_state` `timecode_mode` `rec_run` and UI.conf `timecodeMode=Rec Run` (`grep timecodeMode ~/.config/CinePi/UI.conf` in the sim HOME).
- Pi, stock check: tap the timecode, record a DNG take, `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"timecode_mode":"[a-z_]*"'` shows the new mode, and the clip's TimeCodes start at 00:00:00:00 for Rec Run.
- After this commit the owner's rig loses the UI-only tap until commit 11.
- Depends on nothing.

**11. `ui: a UI.conf switch keeps the file timecode apart from the tap`** (Apertar-UI)
- `SettingsBridge`: `Q_PROPERTY(bool fileTimecodeSeparate ...)`, UI.conf key `fileTimecodeSeparate`, default false, setter copied from `setZebraEnabled`, re-read in `pollExternalSettings`, written and applied in presets (R3 steps 1-2). No Core snapshot, no `set_*_enabled` command: no client but the touch UI uses it, and the WebUI already sets the two timecodes apart with `target`.
- `CPg` `toggleTimecodeMode` and the "Mode" row: when `settingsState.fileTimecodeSeparate`, assign `settingsState.timecodeMode` only (UI-only, QML-7); else call `applyTimecodeMode` as in commit 10.
- `SP` "Files" row: options "Same as Mode", "Free Run", "Rec Run"; value shown `fileTimecodeSeparate ? fileTimecodeMode : "Same as Mode"`. A fixed value: `applyFileTimecodeMode(v)` then `fileTimecodeSeparate = true`. "Same as Mode": `fileTimecodeSeparate = false` then `applyTimecodeMode(settingsState.timecodeMode)`.
- About -4 / +40. Here: UI build. Pi: the owner's workflow: Files = Free Run, tap to Rec Run: screen counts from zero, `timecode_mode` stays `free_run`. A stock camera has no key: behaviour as commit 10.
- Depends on 10. Owner decision 2.

**12. `qml: timecode labels are Free Run and Rec Run again`** (Apertar-UI)
- `SP:21` delete `timecodeChoices`, `SP:1219` delete `timecodeDisplayName`; options become plain `["Free Run", "Rec Run"]` (QML-23); description back to "Timecode behavior" or one clearer fragment without the new names.
- About -14 / +3. Here: UI build. Pi: visual.
- Depends on 11. Owner decision 3 (the rename is offered upstream on its own; Core `2c259b9` and UI `08cefcf` are already isolated).

### Lists and caps

**13. `qml: the IMX585 fps fallback is 1.6.0's again`** (Apertar-UI)
- `CPg:820-822`: `imx585Max = 30.0` for 4K, delete the 25 branch and its comment (reverts `d1efb67`). The table is the fallback for a Core without `fps_max`; mark it with one comment line "fallback for a Core without fps_max; values of 1.6.0, do not edit" (X-state-consistency-5).
- About -2 / +2. Here: UI build; `diff` of the function against `ui-upstream CPg:773-797`: identical. Pi: 4K Clear HDR 16-bit: the fps picker ends at Core's `fps_max` (30), as the WebUI.
- Depends on nothing.

**14. `core: the button fps fallback is 1.6.0's again`** (Apertar-Core)
- `App:1386-1389` `maximumPcfFpsForSettings`: `return 30.0;` and delete the stale comment, as `core-upstream App:1138-1145`. Used only when `fps_max` is 0 (`App:1414`).
- About -2 / +1. Here: builds, tests. Pi: none (dead with this Core).
- Depends on nothing. Coordinate with camera-modes (fps ceilings): the line is theirs if they rewrite the table.

**15. `qml: without iso_max and fps_max, the lossless caps of 1.6.0 apply`** (Apertar-UI)
- `CPg:525-532`: use `controlBridge.isoMax` only when > 0, else `losslessIsoLimitedMode ? 800 : 0`, and no Auto while that fallback applies. `CPg:912-913`: put back `max = Math.min(max, 30.0)` for `losslessImx585Mode` (the empty block). Both run only against a Core without the port's fields.
- About -3 / +5. Here: UI build. Pi: none with the port Core.
- Depends on 13.

**16. `qml: the IMX585 built-in fps list matches Core's`** (Apertar-UI)
- `CPg:923-930`: `imx585Detected ? [24,25,30,50,60,100,120]`, with a comment naming `App builtInFpsSteps`. Capped by `fps_max` as before, so a stock 60 fps mode never offers 100.
- About -1 / +3. Here: UI build. Pi: HD crop mode, fps picker offers 100/120 where `fps_max` allows.
- Depends on 13.

**17. `qml: the IMX585 resolution lists are Core's per-class tables`** (Apertar-UI)
- Both pages, identical (QML-9): replace `imx585Raw12ResolutionOptions` and the two crop lists by four copies keyed s12/s10/h12/h16 of whatever Core's tables are after the camera-modes theme, the class picked from `rawBitDepthValue` and `clearHdrActive` exactly like `WCP imx585ClassKeyFor`. Extra families (2K crop, 4:3, 1:1) join `imx585BaseResolutionOptions` with their crop lists. Each list carries a comment naming `src/camera/Imx585Modes.hpp` and `WCP imx585ClassModes`; `Imx585Modes.hpp` gets one comment naming the QML copies.
- If the camera-modes theme keeps the extended tables only for the forked driver, Core must publish that as one flat state field (their design); the QML lists key on it like `imxNNNDetected`, and with it false the lists are 1.6.0's.
- About -60 / +120 (two pages; mostly data). If the reviewer finds it too long, split into 17a (4K/HD crops and class pick) and 17b (new families).
- Here: UI build. Pi: each class, each family: pick, `get_state` reports the same size; the list highlights the current value.
- Depends on camera-modes (IMX585 1.85:1 crop sizes, stock-driver fallback). Not before.

### Clip names

**18. `qml: clip-name presets are a Pattern dropdown`** (Apertar-UI)
- `CNC:355-375`: the ActionTile Repeater becomes `InlineDropdownField { label: "Pattern"; options: presetList as {value: template, label}; value: currentTemplate; displayValue: matchesNoPreset ? "Custom" : <label> }`.
- About -18 / +12. Here: UI build. Pi: pick each pattern; "Next clip" follows.
- Depends on 1.

**19. `qml: the clip-name card edits by tap only`** (Apertar-UI)
- `CNC`: delete the ghost item (`CNC:578-600`), the `DropArea` and insertion marker (`CNC:392-471` drag parts), `indexAt`, `beginDrag`/`moveDrag`/`endDrag` (`CNC:242-313`), the `drag*` properties (`CNC:39-48`); `ClipNamePill.qml:53-94`: the long-press and `preventStealing` code and its drag signals. Kept: pill row as a `Flow` of tappable pills, palette tap to append, the selection tiles (move left/right, Edit text, Remove), "Next clip".
- About -210 / +5. Here: UI build. Pi: on the touch screen (never tested there): build a pattern with taps only.
- Depends on 18. Owner decision 4: if drag stays, this commit becomes "rebuild drag on the reorderDelegate pattern" instead.

**20. `qml: the clip-name card saves each edit`** (Apertar-UI)
- `CNC:139-170`, `:317-345`: delete `saveTimer`; each edit calls `saveNow()`, which calls `applyClipNameTemplate` (now `bool`; on `false` reload from the bridge). The preview timer stays only if a save per tap is too slow on the Pi (one socket round trip, about the cost of any setting). This fixes the edit lost when a take starts within the 1 s delay.
- About -20 / +6. Here: UI build. Pi: move a pill and press record at once: the take uses the new name.
- Depends on 19.

**21. `qml: the clip-name card keeps tokens it does not know`** (Apertar-UI)
- `CNC:76-93` `parseTemplate`: any `{name}` becomes a token pill; the palette stays the QML list.
- About -2 / +3. Here: UI build. `--simulate`: set `{format}_{iso}_{clip}` with `set_clip_name_template`; a tap-move on the card keeps `{iso}` (Pi or a desktop run of the UI against the sim socket).
- Depends on 19.

**22. `ui: the clip-name card shows without a presence latch`** (Apertar-UI)
- Delete `clipNameKnown` (`ACBH:76`, `:157`, `:434`; `ACB:670-673`) and its use in `SP:2031`. UI and Core ship together after the merge.
- About -10 / +1. Here: UI build.
- Depends on 20.

### First start and the last Core step

**23. `ui: the INA219 log says when no hardware file was found`** (Apertar-UI)
- `src/Ina219Bridge.cpp:262-267`: when no candidate file exists, log "INA219 config: no apertar-hardware.conf found, built-in defaults (bus=.., address=..)" and leave `m_configPath` empty. No UI writer comes back: it would undo what `c9d841f` fixed and trip Core's replaced-by-template check.
- About -3 / +3. Here: UI build. Pi: `journalctl -u apertar-ui -b | grep INA219` on a camera without the file.
- Depends on the hardware-inputs theme's Core first-start writer for the file itself.

**24. `camera: Imx585Modes.hpp names its copies in the WebUI and the touch UI`** (Apertar-Core)
- One comment block above `kS12Modes` naming `WCP imx585ClassModes`, `CPg` and `SP` as hand copies to edit together (R6 step 4). About -0 / +3. Here: builds. Lands right after commit 17.
- Depends on 17.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| Two timecodes (`set_timecode_mode target=ui|files|both`, default both) | Core keeps the optional `target` (App-5-F7). The touch UI uses only no target and `files`; the screen-only change is a UI.conf assignment | An optional argument whose absence gives the old behaviour is the least foreign form; an unmodified client works. It breaks C1-I18 (UI.conf and camera mode always equal) on purpose, and only after the operator chooses it |
| `fileTimecodeSeparate` in UI.conf | R3 steps 1-2 only (touch-only switch) | Needed so the owner's tap stays UI-only "by setting" while a stock camera, with no key, behaves as 1.6.0 |
| Clip-name composer (`ClipNameCard.qml`, `ClipNamePill.qml`) | Its own QML files (not a `Component` in `SP`), tap editing only, one save per edit | 600 lines do not belong inline in a 10 000-line page; upstream has standalone card components (`SystemSectionCard.qml`). No precedent for a template composer at all |
| Core events `controls`, `media`, `buffer` | Kept, but spelled with state keys and read by `applyCoreState` | 1.6.0 has no such events; the shape is that of `media_write_state` and `recording_health` |
| Per-class IMX585 tables | Hand copies (QML-9, R6), no runtime list from Core | Upstream has no mode probe for the UIs (conventions section 5). A bridge call to `list_sensor_modes` would be a second source; offered to the owner as option 5B only |

## For the owner

1. **Log on the wire: enum or switch?** A: keep `value=off|auto` (Core's enum, as `set_cdng_compression`), dropdown in QML. B: `set_cdng_log_enabled enabled=`, Core change and WebUI change. Recommendation A: no Core change, and `auto` leaves room for a fixed depth later. Cost A: commit 2 only.
2. **Timecode tap.** A: 1.6.0 only: tap and Mode set both; the "Files" row sets files apart until the next tap (commit 10 alone). B: A plus the `fileTimecodeSeparate` switch (commit 11) so the rig keeps a UI-only tap. C: keep the port's split as default (stock camera changes behaviour; not mergeable). Recommendation B. Cost: +40 lines and one UI.conf key, documented as new ground.
3. **Labels "Time of Day" / "Clip".** A: back to Free Run / Rec Run in the merge, rename proposed upstream on its own (commit 12). B: keep the rename. Recommendation A; the WebUI part is the webui-state theme's.
4. **Clip-name drag.** A: delete drag, keep tap editing (commit 19, -210 lines). B: rebuild drag on the reorder popup's pattern (`held`, `drag.target`), about -100 / +60, still untested on touch. Recommendation A: the tap tiles already do every edit, and drag was never run on a touch screen.
5. **IMX585 list source.** A: hand copies per class in both QML pages (R6, QML-9). B: the bridge calls `list_sensor_modes` once per sensor and QML uses that list, the hand list as fallback (new ground, about +60 lines, a second source of truth). Recommendation A, after the camera-modes theme.
6. **`preview_tdn` and `media_trim` in presets** (X-state-consistency-14). A: add `cameraPreviewTdn` / `cameraMediaTrim` to both writers and the reader. B: one comment in both writers saying they are deliberately not preset fields. Recommendation B (they are camera-wide switches kept across format changes). Cost: 2 lines.
7. **`set_storage_preroll` name.** A: keep the name, argument `enabled` (commits 4-6). B: rename to `set_storage_preroll_auto_enabled` (upstream `set_<thing>_enabled` form), both clients change. Recommendation A unless the preroll theme renames anyway.

## Risks and what was not determined

- The touch UI cannot be driven here. Every QML change is checked by build only (`check_ui.sh`, QML compiled ahead of time catches unknown properties and types, not behaviour). Each commit names the Pi step.
- Commits 4 and 7 change port-only wire forms. Mixed versions (new Core, older UI) degrade to the 1-5 s get_state poll for controls/media updates (7) and need the `value=` fallback for one release (4, removed by 6). Not determined: whether any script on the owner's rig reads the `media` event's `state`/`mounted`; `grep -rn '"mounted"' ~/` on the Pi settles it.
- Commit 8: the buffer event now runs the whole of `applyCoreState` up to four times a second during a take on the GUI thread. Not measured. On a Pi 4 the cost should stay small (dozens of `contains` checks); `top -H -p $(pidof ApertarUI)` during a take on a Pi 4 settles it. If too high, keep the buffer branch and send only buffer keys through it.
- Commit 9 assumes Core's `apply_preset` accepts bools and numbers as JSON types (it reads them with `command.string` / `command.number`). The `--simulate` round trip settles it before the commit.
- Commit 17 cannot be designed to the row before the camera-modes theme decides the 1.85:1 sizes and the stock-driver fallback (Driver-imx585-F1, CC-1-F1, X-stock-behaviour-4).
- First start: whether the UI starts before Core has written the file on a fresh image. The UI's compiled defaults equal the template's `[display]` (fix-log U1) and `[ina219]` values (`ui-upstream src/Ina219Bridge.cpp:89-92` vs `src/Ina219Bridge.hpp:55-58`), so a race changes nothing visible.
- Pi models: nothing here touches GPU, ISP or I2C paths. The QML lists and caps follow Core's `fps_max`, which carries the per-board limits. The one board-dependent cost is commit 8 on a Pi 4 (above).
- The line estimates are from reading, not from a diff.

## Findings covered

| Finding | Commit |
| --- | --- |
| UI-control-bridge-F1 | 1, 2, 4, 5, 6 |
| UI-control-bridge-F2 | 7, 8 |
| UI-control-bridge-F5 | 10, 11 |
| UI-settings-qml-F1 | 2, 3, 5, 18 |
| UI-settings-qml-F2 | 10, 11, 12 |
| UI-settings-qml-F3 | 19 (owner decision 4), 20 |
| X-state-consistency-1 | 9 |
| X-state-consistency-3 | 17, 24 (after camera-modes) |
| X-commits-ui-drivers-2 | 13, 14 |
| X-stock-behaviour-8 | 10, 11 |
| UI-bridges-F2 | 23 (UI side); the Core writer and the template's `chip=auto` lines are the hardware-inputs theme's |
| UI-bridges-F5 | 1 |
| UI-bridges-F7 | 10 |
| UI-settings-qml-F10 | 10 |
| X-protocol-security-4 | 10 |
| App-5-F2 | 4, 6 (the `*_enabled` names of the four camera switches: not covered, protocol change for both clients, owner decision 7 covers only pre-roll) |
| App-5-F7 | kept as new ground (section above); Pi check in commit 10 |
| UI-control-bridge-F3 | 1 |
| UI-control-bridge-F9 | 5, 22 |
| UI-settings-qml-F8 | 21 |
| UI-settings-qml-F9 | 20 |
| X-state-consistency-4 | 16 |
| X-state-consistency-5 | 13, 14, 15 (the WebUI re-application `WCP:7490-7509`: webui-state theme) |
| UI-camera-qml-F3 | 15 |
| X-stock-behaviour-2 | 23 + hardware-inputs theme |
| X-state-consistency-14 | owner decision 6 |
| WCP-05-F2, WCP-05-F3, X-state-consistency-6 | not covered: WebUI side, webui-state theme |

## Challenge

Read at Apertar-UI `ac1fc28` (`/home/user/wt/ui-work`), Apertar-Core `3650027` (`/home/user/wt/core-work`), upstream `43888e5` / `35dbe67`. Line numbers are from these trees. One Qt behaviour was run here: a 1000 ms `QTimer` that gets `setInterval(1000)` every 250 ms fired 0 times in 3.5 s (Qt 6 on this container, test program in the scratchpad). So `setInterval` on a running timer restarts it.

| Point | What the design says | What the code says, file:line | What must change |
| --- | --- | --- | --- |
| b, c. Commit 8, buffer event into `applyCoreState` | Only cost: "dozens of `contains` checks", up to 4 a second; Pi 4 `top` settles it | `applyCoreState` ends its camera-set block with an unconditional `updateRefreshTimer()` (`ui-work ACB:1621`, added by port `f1edf96`; upstream `applyCoreState` has none). That calls `m_retryTimer.setInterval(...)` (`ACB:1014-1016`), which restarts the poll timer. The buffer event comes every 250 ms during a take and the drain (`core-work App:10995-11049`). The live-value poll is 1000 ms with ISO or WB auto, else 30000 ms (`ACB:17-20`). So during every take the `get_state` poll (`ACB:990-1008`) never fires: the ISO and WB in use stop updating, and so does every value that arrives only by poll | Keep the buffer branch (`ACB:1345-1349`). Upstream precedent for a frequent event with its own branch is `audio_level` (`ui-upstream ACB:1196-1199`). Commit 8 adds only `controls` and `media` to the list. Add a Pi check: during a 4K take with ISO Auto, the green ISO in use changes within 2 s when the light changes |
| a. Commit 8 precedent | "Every event made of state keys goes whole to `applyCoreState`, as in 1.6.0" | 1.6.0 also keeps its own branches: `audio_level`, `timelapse`, `recording` with extra handling (`ui-upstream ACB:1196-1235`). The rule (UIC-4) covers state keys, not how often an event fires | As above. `setControlsStatus` can still go (`ACB:1424-1435`): inline compare/assign/emit is right |
| b, d. Commit 7 interim | Until commit 8 is deployed, controls/media follow "the get_state poll (1-5 s)" | The poll is 30 s unless ISO or WB is auto (`ACB:18`, `:1016`). Between 7 and 8, a pulled card shows NO MEDIA up to 30 s late on the touch UI and HDMI | Land 7 and 8 together (Core and UI ship together, CMD-30). Fix the number in the text |
| b, d. Commits 4, 5, 6 vs other themes | `set_storage_preroll` takes `enabled=`, `value=` fallback for one release, then removed. Owner decision 7 | storage-settings owns this command: its commits 6-7 replace it with `set_storage_preroll_auto_enabled enabled=` and change `applyStoragePrerollAuto` (`design/storage-settings.md:210`, `:219-225`; preroll design says so too, `design/preroll.md:208`). command-plane plans a third name, `set_storage_preroll_enabled` (`design/command-plane.md:214-227`). Three plans for one 25-line block (`core-work App:12917-12944`) | Drop 4 and 6. Commit 5 keeps only what this theme owns: the rename to `startStoragePreroll()`, the TogglePill row, the deleted `storagePrerollAutoKnown` latch (`ACB:2746-2749`, `ACBH:67,148,256,417`). It sends whatever storage-settings 7 defines. Remove owner decision 7 from this page (it is storage-settings' decision 7) |
| b. Commit 1 and command-plane 13; commit 10 and command-plane 16 | Commit 1 makes the six invokables `bool`; commit 10 rewrites `applyTimecodeMode` | command-plane commit 13 is the same change to the same lines (`design/command-plane.md:206-212`). Its commit 16 changes the same `applyTimecodeMode` (`ACB:750-771`) to read `m_fileTimecodeMode` from the reply, and commit 10 here deletes that body | The task gives bridge idioms to this theme. Keep 1 and 10 here. Name the dependency: command-plane drops its 13 and the timecode half of its 16 |
| b, c. Commit 10 leaves out half of 1.6.0's timecode | "returns to the 1.6.0 body"; precedent table cites `applyCoreState` copying `timecode_mode` into UI.conf (`ui-upstream ACB:1466-1471`) | The port deleted that copy (`ui-work ACB:1698-1707` sets only `m_fileTimecodeMode`). Commit 10 does not say whether it comes back. If it comes back without a gate, every `get_state` writes the file mode over UI.conf `timecodeMode`, which ends commit 11's UI-only tap | Commit 10 restores the copy. Commit 11 skips it while the separate switch is on. Say both in the commits |
| c, 3. Commit 10 alone | "After this commit the owner's rig loses the UI-only tap until commit 11" | That is a rig regression between two commits of the same series | Land 10 and 11 in the same push, or put 11's switch in first with the tap unchanged |
| c, 4. Commit 11, the WebUI's split | Switch in UI.conf, SettingsBridge only (R3 steps 1-2). "No Core snapshot ... the WebUI already sets the two timecodes apart with `target`" | The WebUI sends `target=ui` / `target=files` (`core-work WCP:9809-9826`, Core `App:13302-13314`). Then the files and the screens differ, but `fileTimecodeSeparate` stays false. The touch "Files" row shows "Same as Mode" while the files have another mode, and the next tap sets both. R3 has 12 steps, and the steps the design skips are the ones that let Core and the WebUI see the key (`apertar-conventions.md` R3 steps 7, 9, 10) | One writer, where UI.conf `timecodeMode` is already written: Core's `set_timecode_mode` writes `fileTimecodeSeparate=true` for `target=ui|files` and `false` for no target or `both`, in the same `updateSharedUiGeneralSettings` call (`App:13311-13313`, CMD-26). SettingsBridge reads it (R3 steps 1-2, `pollExternalSettings`). Core snapshot line (step 7). Both preset writers carry it (step 10). Otherwise commit 11 brings back X-state-consistency-1: two preset writers with different key sets. About +6 in Core and the same +40 in the UI |
| c, 4. Commit 11 on an existing camera | "No key moves between files, so no take-over of old keys is needed" | On the owner's camera today, UI.conf `timecodeMode` and `camera_settings.conf` timecode differ on purpose (`ACB:762-765`, `App:13307`). With the key absent (= false), the first tap after the update sets both modes. A stock camera always has them equal, because 1.6.0 copies one into the other (`ui-upstream ACB:1466-1471`) | Take-over at Core start, in the shape of upstream's loaders: UI.conf has no `fileTimecodeSeparate` and the two modes differ -> write `true` once and log one line. A stock camera has no difference, so it gets `false` and behaves as 1.6.0 |
| a, g. Commit 13 claim and check | 25 is "wrong against a 1.6.0 Core (30)". Diff against `ui-upstream CPg:773-797`. Pi: the picker ends at `fps_max` (30) | 1.6.0 has no Clear HDR (`grep -c clearHdr` = 0 in `ui-upstream qml/CameraPage.qml` and `core-upstream App`). `clearHdrActive` is never true against it. The 25 branch can fire only against fork main `f60e301` (Clear HDR, no `fps_max`). The function starts at `ui-upstream CPg:733`. The Pi step tests the `fps_max` path (`ui-work CPg:905-906`), not this code | The reason: "dead code that differs from 1.6.0". Pi check: none (or the port UI against a fork-main Core build). Leave out the "do not edit" comment: R6 step 4 says these tables are edited together when a mode is added |
| d. Commits 13 and 15 | Two commits | Both only bring back 1.6.0 lines that run without `fps_max` / `iso_max` (`ui-work CPg:526`, `:912-913`). One idea | One commit: "qml: without fps_max and iso_max the caps are 1.6.0's again" |
| b. Commit 14's sibling | Fix the stale comment at `App:1386` | The same stale text is in CC: "the 16-bit 25 is backendMaximumFps()" (`core-work CC:3378`), while `backendMaximumFps` returns `nullopt` (`CC:3426-3434`). CC's table still gives 25 for Clear HDR without a probe (`CC:3379-3380`) | Name it for camera-modes (fps ceilings). Not this theme's line |
| c, 3, e. Commit 17 on a stock camera | Hand copies of Core's four class tables in both pages, after camera-modes. Owner decision 5 recommends A | camera-modes puts the IMX585 driver back to 3840x2076 / 1920x1038 and lets Core accept them again (`design/camera-modes.md:12`, `:100`, `:197-199`). The 1.6.0 touch lists (`ui-work CPg:418-446`, `SP:161-189`) then match Core again, and X-state-consistency-3's "2076 picked, 2072 reported" goes away. The class tables are advisory: "a row the driver lacks does nothing" (`camera-modes.md:217`). Hand copies would offer 2K crop, 4:3 and 1:1 on the original driver, which a stock camera never showed. camera-modes moves the WebUI to `list_sensor_modes` (`camera-modes.md:179`), so 5A would leave the two UIs on different sources again | Take 17 and 24 out of the series. The touch lists stay 1.6.0's; that is stock-safe and matches Core after camera-modes. The extra families on the touch screen are an owner decision: A, the WebUI only; B, `list_sensor_modes` as camera-modes does for the WebUI, with the 1.6.0 list as fallback. The estimate of -60/+120 also does not hold: about 30-45 sizes per class times four classes times two pages (`core-work WCP:8915-8920`) |
| f, g. Commit 9 risk | "assumes `apply_preset` accepts bools and numbers as JSON types"; to be settled in `--simulate` | Settled in code: the parser keeps a bare value as its text (`core-work src/ipc/ControlProtocol.cpp:192-205`). `command.string` returns `"true"`, which `parseUiSettingsBool` reads; `command.number` runs `stod` on `"1200"` (`:139-161`). Upstream precedent for keeping a value only for the preset: `m_lossyDngRatio` (`ui-upstream ACB:532`, written in `cameraPresetSettings`) | Take it off the risk list; keep the sim round trip as the check. Commit 9 does not depend on commit 2: `m_cdngLogOn ? "auto" : "off"` works today |
| e. Commits 1 and 20, the preview | Commit 1 makes `requestClipNamePreview` `bool`; commit 20 keeps the preview timer "only if a save per tap is too slow" | `set_clip_name_template` replies with `settingsBody`, which carries `clip_name_example` (`core-work App:374`, `:13269-13271`). With a save on each edit the preview command has no job in the touch UI (the WebUI still uses `preview_clip_name`) | Commit 20 decides: delete `previewTimer`, `requestClipNamePreview` and `clipNamePreview` in the touch UI (about -25 more). Commit 1 then leaves `requestClipNamePreview` alone. Pi check for 20: delete the `{clip}` pill; Core puts `_{clip}` back (`App:13260-13271`) and the reply reloads the card at once (`CNC:142-145`). The card must not jump in the middle of an edit |
| f. Mixed-version policy is decided in pieces | 22 deletes `clipNameKnown`, because "UI and Core ship together"; 4/6 keep a `value=` fallback for an older UI; 13/15 keep code for a Core without `fps_max` | Three different answers to one question. CMD-30 (Core and UI ship together) is already cited by storage-settings and command-plane | One sentence at the top of the plan: Core and UI ship together; fallbacks stay only where they are 1.6.0's own code (13/15), never new ones |
| f. Owner list | 7 decisions | 1 (Log as enum) is settled the same way in command-plane (`command-plane.md:293`). 7 belongs to storage-settings. 5 must be asked together with camera-modes (WebUI source). Not on the list: the take-over of the split timecode (commit 11) and whether the touch screen offers the extended IMX585 families at all | Drop 7. Merge 5 with camera-modes' question. Add "the touch UI offers the extended IMX585 families: A no, B through `list_sensor_modes`" |
| a. Precedent citations checked | - | Hold: `ui-upstream ACB:111-141`, `:622-636`, `:736-741`, `:1191-1195`; `SP:2940-2946`, `:3244-3261`, `:3562`; `CPg:1709-1715`; no conditional `tone:` in any upstream `qml/*.qml` (grep empty); `core-upstream App:9424-9437`, `:9482-9486`, `:6663`; `DisplayConfigBridge.cpp:41`, `:587`. Wrong: `CPg:773-797` (the function is at `:733`) | Fix the one citation |

### Verdict

- **Stand (12):** 1, 2, 3, 9, 12, 14, 16, 18, 19, 21, 22, 23. Small notes: 2 can be thin (`return sendCoreCommand`; Core already refuses unknown values, `App:13098-13099`). 9 has no dependency on 2. 12 has no dependency on 11. 22 rests on the one-sentence version policy below.
- **Change (7):**
  - 5: rename, TogglePill row and deleted latch only. The wire form is storage-settings 7.
  - 7: lands with 8. The interim lag is up to 30 s, not 1-5 s.
  - 8: `controls` and `media` join the `applyCoreState` list. The `buffer` branch stays (`audio_level` precedent). Otherwise the poll stops during every take.
  - 10: brings back the `applyCoreState` UI.conf copy, lands with 11, and replaces command-plane 16's timecode half.
  - 11: Core writes `fileTimecodeSeparate` in `set_timecode_mode`. The flag goes into the Core snapshot and both preset writers, and Core takes over an existing split at start.
  - 13: merged with 15. Correct the reason, no Pi check, no "do not edit" comment.
  - 20: deletes the preview path.
- **Dropped (5):**
  - 4 and 6: storage-settings 6-7 own `set_storage_preroll`.
  - 15: folded into 13.
  - 17 and 24: out of the series. The 1.6.0 lists match Core once camera-modes is done. The extra families go to the owner.
- **Missing (2):** (a) One line on the version policy: Core and UI ship together (CMD-30), with no new fallbacks. (b) A coordination note naming which theme lands which lines: command-plane drops its 13 and the timecode part of its 16; storage-settings 7 sets the pre-roll wire form that 5 calls; camera-modes owns the stale `CC:3378` comment and decides the IMX585 list source with owner decision 5.
