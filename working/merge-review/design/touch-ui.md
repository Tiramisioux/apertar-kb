# The touch UI: bridge idioms, presets, timecode, first start: plan

Read at Apertar-UI `work/improve` `ac1fc28` (`/home/user/wt/ui-work`) and Apertar-Core `work/improve` `0d13a6f` (`/home/user/wt/core-work`), against `upstream-1.6.0` (`/home/user/wt/ui-upstream` `43888e5`, `/home/user/wt/core-upstream` `35dbe67`) and fork main (`/home/user/wt/ui-main` `4415a55`, `/home/user/wt/core-main` `f60e301`). This is the final plan: the first design, corrected after the challenge (last section).

**Version policy (one sentence for the whole plan):** Core and UI ship together (CMD-30, `README.md:306`); no commit adds a fallback for a mixed Core/UI pair, and the only fallbacks kept are fork main's own lines (commit 15).

## In short

- Today: six new bridge invokables return `void`; two send booleans as `value=on|off` and `value=auto|off`. Core's `controls` and `media` events take a second route into the bridge, with their own key spellings and a setter that takes key names. Three choices (Write Buffer, Log, automatic pre-roll) and the clip-name presets are ActionTiles whose accent colour flips like a radio button.
- Touch presets do not save the settings the port added. The timecode tap and the Settings first row no longer change the timecode written into clips. A dead fallback still caps 4K Clear HDR 16-bit at 25 fps. Nothing writes the first hardware file.
- Target: command invokables return `bool` (UIC-9). Every event made of state keys and sent now and then goes whole to `applyCoreState`, as in 1.6.0; the frequent `buffer` event keeps its own branch, as 1.6.0's `audio_level`. A choice is a TogglePill or an InlineDropdownField. Both preset writers carry the same keys. `applyTimecodeMode(v)` has one argument and sets both timecodes, as in 1.6.0; the file timecode stays apart only after the operator sets it apart, and Core records that in UI.conf `fileTimecodeSeparate`.
- The touch IMX585 resolution lists stay 1.6.0's: once camera-modes restores 3840x2076 / 1920x1038 they match Core again. Whether the touch screen offers the extra IMX585 families goes to the owner. The first-start file is written by Core (hardware-inputs theme); the UI only stops naming a file that does not exist.
- 23 commits: 18 in Apertar-UI, 5 in Apertar-Core. About -460 / +230 lines. The largest is the deletion of the clip-name drag layer (-210).

## How it works in the port today

Paths: `ACB` = `Apertar-UI/src/ApertarControlBridge.cpp`, `ACBH` = its `.hpp`, `SB` = `src/SettingsBridge.cpp`, `SP` = `qml/SettingsPage.qml`, `CPg` = `qml/CameraPage.qml`, `CNC` = `qml/ClipNameCard.qml`, `App` = `Apertar-Core/src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `CC` = `src/camera/CameraController.cpp`. "GUI thread" = the Qt main thread; the bridge blocks it on each command for at most 3 s (UIC-16). Core commands run under `commandMutex_` in `handleCommand`. Every command reply passes through `applyCoreMessage` (`ACB:1208`) and, because it has `ok`, through `applyCoreState` (`ACB:1411-1412`).

### Bridge invokables and their wire form

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Write buffer `frames`/`ram` | QML `applyBufferMode(v)`, `void`, then sets `m_bufferSetting` itself (`ACB:686-700`); Core `set_buffer_mode value=` (`App:12846`), reply carries `bufferSettingMembers()` with `buffer_setting` (`App:12868-12869`, `:252-256`) | Core recorder at the next take; `applyBufferState` from `applyCoreState` (`ACB:1732`) | GUI thread; command lock, then the hardware-config store | `apertar-hardware.conf [storage] buffer=` (storage-settings theme) | two ActionTiles, accent on the chosen one (`SP:3430-3449`) |
| cDNG Log `off`/`auto` | `applyCdngLog(bool)`, `void`, sends `value=auto|off` (`ACB:716-727`); Core `cdngLogFromString` refuses unknown values (`App:13098-13099`) | `CC` per take; state `cdng_log` -> `applyCdngLogState` (`ACB:1733`) | GUI thread; command lock | `camera_settings.conf` | one ActionTile On/Off, accent when on (`SP:3476-3482`) |
| Automatic pre-roll | `applyStoragePrerollAuto(bool)`, `void`, `value=on|off` (`ACB:624-630`) | state `storage_preroll_auto` -> `ACB:2736-2749`, which also latches `storagePrerollAutoKnown`; member default `true` (`ACBH:416`) although Core's default is now off (`0977dd6`) | as above | storage-settings theme | On / Off ActionTiles behind the latch (`SP:5611-5640`) |
| Storage pre-roll take | `applyStoragePreroll()`, `void` (`ACB:618-622`) | preroll theme | as above | none | ActionTile (`SP:5605`) |
| Clip-name template | `CNC` 1 s `saveTimer` -> `applyClipNameTemplate`, `void`, applies the reply a second time (`ACB:632-641`) | reply `settingsBody` carries `clip_name_template` and `clip_name_example` (`App:374`, `:13269-13271`) -> `applyClipNameState` (`ACB:1734`), which latches `clipNameKnown` (`ACB:670-673`) | GUI thread; command lock | `camera_settings.conf` | `CNC` (601 lines) + `ClipNamePill.qml` (115), card hidden until `clipNameKnown` (`SP:2031`) |
| Clip-name preview | `CNC` 350 ms `previewTimer` -> `requestClipNamePreview`, `void` (`ACB:643-657`) | `clipNamePreview`, read only by the "Next clip" line (`CNC:515-516`) | GUI thread | none | `CNC` |

### The second state path and the poll

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Controls counts | `controls` event spells them `errors`/`warnings` (`App:12352-12354`); state spells them `controls_errors`/`controls_warnings` (`App:9462`, `:12963`) | event branch `setControlsStatus(message,"errors","warnings")` (`ACB:1332-1335`); `applyCoreState` -> `setControlsStatus(state,"controls_errors",...)` (`ACB:1439`); the setter takes key names (`ACB:1424-1435`) | Core controls worker -> `publishEvent` (`App:14893-14915`); event socket on the GUI thread | none | `ControlsWarning.qml` |
| Media state | `media` event spells `state`/`mounted` (`App:10827-10838`); state spells `media_state`/`media_alive` (`App:9559-9560`, `:12977-12978`) | event branch `setCoreMediaState(state, mounted)` (`ACB:1336-1340`); `applyCoreState` (`ACB:1440-1442`); signal to `MediaStatusBridge` | Core media watcher (`App:10915`) | none | media chip, NO MEDIA |
| Buffer fill | `buffer` event = `bufferMembers` + `recording_dropped_frames` (`App:10843-10847`), every change while a take runs or the queue drains, at most 4 a second (`App:10990-11049`) | own branch: `applyBufferState` + `applyRecordingDroppedFrames` (`ACB:1344-1349`); `applyCoreState` calls the same two | Core buffer thread | none | buffer bar, dropped-frames chip |
| `get_state` poll | `m_retryTimer`, 1000 ms while ISO or WB is auto, else 30000 ms (`ACB:17-20`, `:1010-1017`) | `refreshFromCore` (`ACB:990-1008`): ISO and WB in use, and every value that only the poll brings | GUI thread | none | ISO/WB in use |
| Poll restart | `applyCoreState` calls `updateRefreshTimer()` unconditionally (`ACB:1621`, port `f1edf96`); `setInterval` on a running `QTimer` restarts it (challenger's Qt 6 test: reset every 250 ms, 0 shots in 3.5 s). 1.6.0's `applyCoreState` has no such call; 1.6.0 calls it on connection changes and command replies only (`ui-upstream ACB:125-145`, `:1585`) | every event routed into `applyCoreState` restarts the poll | GUI thread | none | - |

### Presets

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Touch preset, camera part | `ACB::cameraPresetSettings` (`ACB:1254-1286`), byte-identical to 1.6.0; merged into `SB::serializeCurrentSettings` | load: `applyCameraPreset` forwards every `camera*` key and `timecodeMode` to Core `apply_preset` | GUI thread; command lock | preset JSON written by the touch UI | Settings > Presets |
| WebUI preset | `buildCurrentPresetPayload` (`App:7701`; camera keys `App:7846-7887`) adds `cameraFpsSpeedRamp*`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraConformFps`, `cameraClearHdr`, `cameraHdr*` (4), `cameraCdngLog` | `apply_preset` (`App:14339-14395`); `timecodeMode` alone also sets the files' mode unless `cameraTimecodeMode` is present (`App:14444-14449`) | HTTP thread, command lock | preset JSON written by Core | WebUI preset library |
| Wire types | bare JSON `true` / `1200` | the parser keeps a bare value as its text (`src/ipc/ControlProtocol.cpp:192-205`); `command.string` gives `"true"`, `command.number` runs `stod` (`:139-161`) | - | - | - |

### Timecode

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| UI timecode (screens) | tap `toggleTimecodeMode` -> `settingsState.timecodeMode` + `applyTimecodeMode(next,"ui")` (`CPg:1837-1843`); Settings "UI timecode" row (`SP:3998-4013`); the bridge writes UI.conf (`ACB:762-765`); Core writes it again for `target != files` (`App:13309-13314`) | `SB` `timecodeMode` (`SB:372`, poll `:588-595`, inotify `:418-422`); Core `readSharedUiSettings` per use (`App:1983`, key `:2064`) | GUI thread | `UI.conf timecodeMode` | top bar timecode, HDMI |
| File timecode | "File timecode" row -> `applyTimecodeMode(v,"files")` (`SP:4015-4028`); Core `camera_.setTimecodeMode` unless `target=ui` (`App:13295-13316`); WebUI sends `target=ui` or `files` from its two blocks (`WCP:9809-9826`) | state `timecode_mode` -> `m_fileTimecodeMode` only (`ACB:1698-1707`). The port deleted 1.6.0's copy of `timecode_mode` into UI.conf (`ui-upstream ACB:1466-1471`) | GUI thread; command lock | `camera_settings.conf` | Settings row; WebUI two blocks |
| Labels | `timecodeChoices` "Time of Day"/"Clip" (`SP:21`), `timecodeDisplayName` (`SP:1219`) | dropdowns | - | stored values stay "Free Run"/"Rec Run" | Settings, WebUI |

### Lists, caps, first start

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| IMX585 sizes | Core per class S12/S10/H12/H16 (`src/camera/Imx585Modes.hpp`); Core rewrites 2076 -> 2072, 1038 -> 1036 (`CC:441-450`); camera-modes puts 2076/1038 back and moves the WebUI to `list_sensor_modes` (`design/camera-modes.md:12`, `:100`, `:179`) | touch lists are 1.6.0's (`CPg:418-446`, `SP:161-189`) | QML | `camera_settings.conf resolution=` | after camera-modes the 1.6.0 lists match the original driver (`camera-modes.md:83`) |
| IMX585 fps fallback | QML 25 for 4K Clear HDR 16-bit (`CPg:820-822`, `d1efb67`); App the same (`App:1385-1389`) | used only when `fps_max` is 0 (`CPg:905-906`; `App:1414`). The port Core always sends `fps_max`; 1.6.0 has no Clear HDR (`grep -ci clearhdr ui-upstream/qml/CameraPage.qml` = 0), so the 25 branch runs only against a fork-main Core (Clear HDR, no `fps_max`) | QML / command lock | none | dead code that differs from fork main (`ui-main CPg:780-781`: 30) |
| Lossless caps without `iso_max`/`fps_max` | `isoOptions` uses `isoMax` whenever a bridge exists, else 1600 (`CPg:525-532`); the IMX585 lossless fps cap is an empty block (`CPg:912-913`) | only against a Core without the port fields | QML | none | fork main: 800 list and 30 fps (`ui-upstream CPg:511-513`, `:815-816`) |
| IMX585 built-in fps list | QML `{24,25,30,50,60}` (`CPg:923-930`, 1.6.0's); Core `{24,25,30,50,60,100,120}` (`App:1398-1406`, port `caa0153`; 1.6.0 Core has no built-in list, and the 1.6.0 WebUI cuts its list at 60 for every sensor but the IMX477, `core-upstream WCP:4995-4996`) | fps pickers when UI.conf has no `fpsSteps`; values above `fps_max` are greyed (`CPg:860-872`) | QML | - | WebUI offers 100/120, touch does not |
| First hardware file | nobody since UI `c9d841f`; Core shows `defaultHardwareConfigTemplate()` in the editor | `Ina219Bridge` uses compiled defaults and logs "using defaults in /home/pi/apertar-hardware.conf" (`src/Ina219Bridge.cpp:262-267`), a file that does not exist | UI start | absent | journal |

## How original Apertar does this kind of thing

| Kind | Precedent (`@upstream-1.6.0`) |
| --- | --- |
| Invokables return `bool` | `ui-upstream ACBH:111-141`; only `notifyUserActivity()` and `refresh()` are `void` (`:100`, `:110`). Thin form `bool applyCaptureMode(mode) { return sendCoreCommand(...); }` (`ACB:731-734`). UIC-9 |
| Enum on the wire | `applyCdngCompression(const QString &value)` sends `value=` (`ACB:516-535`); Core refuses an unknown value (`core-upstream App:9340-9346`) |
| Boolean on the wire | `applyPhotoLongExposureEnabled(bool enabled)` sends `enabled="true"/"false"` (`ACB:736-741`); Core tests `== "true" || == "1"` (`core-upstream App:9482-9486`). UIC-12, CMD-8 |
| An event made of state keys | `if (event == "standby" || ... || "media_write_state") { applyCoreState(message); return; }` (`ACB:1191-1195`); `recording_health` likewise (`:1213-1216`). Bools and counters inline compare/assign/emit (`recording_has_dropped_frames`). UIC-4 |
| A frequent event | `audio_level` keeps its own one-line branch (`ACB:1196-1199`) |
| Poll interval | `updateRefreshTimer()` on socket state changes and after command replies (`ACB:125-145`, `:1041-1104`, `:1585`); never inside `applyCoreState` |
| A switch in Settings | `if (apertarControlBridge.applyPhotoLongExposureEnabled(checked)) settingsState.photoLongExposureEnabled = checked` (`SP:2940-2946`); row with title, description, `TogglePill` (`gyroRecordToggle`, `SP:3562`). QML-8 |
| A choice of values | `InlineDropdownField` "Compression" with `{value,label}` options, `onValueSelected: applyCdngCompression(v)` (`SP:3244-3261`). ActionTile is a verb with a fixed tone (`SP:3640`, `:3650`, `:5416`); no conditional `tone:` in any upstream QML file. QML-23, QML-26 |
| Presets | Two writers, same `camera*` set: Core `buildCurrentPresetPayload` (`core-upstream App:6663-6690`) and touch `cameraPresetSettings` (`ACB:1118-1150`). One reader, `apply_preset`. A value kept only for the preset: `m_lossyDngRatio` (`ACB:532`). R2 step 10 |
| Timecode | `bool applyTimecodeMode(displayValue)`: `set_timecode_mode value=`, writes UI.conf (`ACB:622-636`). Core sets camera and UI.conf together (`core-upstream App:9424-9436`, CMD-26). The tap changes both (`CPg:1709-1715`). `applyCoreState` copies Core's `timecode_mode` into UI.conf (`ACB:1466-1471`) |
| A UI.conf key Core writes | `set_timecode_mode` writes `timecodeMode` through `updateSharedUiGeneralSettings` (`core-upstream App:9433-9435`); snapshot member, parse branch, preset writer/reader (R3 steps 7, 10: `zebraEnabled`, `core-work App:1871`, `:2022`, `:7757`, `:14452`) |
| Start-time reconcile between UI.conf and camera settings | after `camera_.start`, before the control server listens: `stillSettings = readSharedUiSettings()` and the camera follows UI.conf (`core-upstream App:6845-6857`, `controlServer_.start` `:6859`; port `App:8077-8092`). Old values taken over in the loader: `wb_locked` (`core-upstream CC:625`, `:682`, `:727`) |
| A UI-only preference | `SettingsBridge` READ/WRITE/NOTIFY property backed by UI.conf, constructor read, `pollExternalSettings`, presets; QML assigns `settingsState.<prop> = v`. UIC-13, QML-7, R3 steps 1-2 |
| Option lists and caps | Hand copies, identical in `CPg` and `SP` (QML-9, R6 step 4). QML/App tables are the fallback when Core sends no `fps_max` (`ui-upstream CPg:733-800`, `core-upstream App:1138-1145`) |
| First hardware file | The UI wrote it from a template (`src/DisplayConfigBridge.cpp:41-326`, `:587`; `src/Ina219Bridge.cpp:69-342`, `:497`). Core only shows its template |
| Drag in QML | Only the reorder and sidebar popups: `held`, `drag.target`, `Drag.active: held`, `pressAndHoldInterval 260` (`SP:6111-6211`, `:6282-6297`). Settings apply on selection, without timers |

## The target

| Value | Before (port) | After |
| --- | --- | --- |
| Write buffer | `void`; two tinted ActionTiles | `bool applyBufferMode(value)`, thin; `InlineDropdownField` "Write Buffer". Wire unchanged (an enum). Storage: storage-settings |
| cDNG Log | `void applyCdngLog(bool)`; tinted ActionTile | `bool applyCdngLog(const QString &value)`, thin (Core refuses unknown values); `InlineDropdownField` "Log" Off/On. Core and state unchanged (settled the same way in command-plane, `design/command-plane.md:293`) |
| Automatic pre-roll | `void`, `value=on|off`, two tinted ActionTiles behind a latch | wire form and command name: storage-settings 6-7. Here: a TogglePill row, latch deleted, member default `false` |
| Pre-roll take | `void applyStoragePreroll()` | `bool startStoragePreroll()` (a verb, UIC-10), thin |
| Clip name | `void` + double apply; preview command and two timers; latch | `bool applyClipNameTemplate`, one save per edit; preview path deleted (the save reply carries `clip_name_example`); latch deleted |
| Controls / media events | own branches, key-name setter | Core events carry state keys; both join the 1.6.0 `applyCoreState` list; `setControlsStatus` inlined |
| Buffer event | own branch | unchanged (frequent event, `audio_level` precedent) |
| Poll restart | every event in `applyCoreState` restarts the poll | only a change of ISO or WB auto resets the interval |
| Touch preset | 1.6.0 key set | 1.6.0 set + every key Core's writer adds, under Core's names and value words; `fileTimecodeSeparate` in both writers |
| Timecode, default | tap and first row set the screens only | as 1.6.0: one row "Mode", `applyTimecodeMode(v)`, sets both; the tap sets both; `applyCoreState` copies Core's mode into UI.conf |
| Timecode, set apart | always apart | after the operator picks a fixed "Files" value (touch) or sends `target=ui|files` (WebUI): Core writes UI.conf `fileTimecodeSeparate=true`; while true, the tap and "Mode" are UI-only (QML-7) and the UI.conf copy is skipped. "Same as Mode" sends no target; Core writes `false` |
| IMX585 lists | 1.6.0 lists | unchanged (match Core after camera-modes); extra families: owner decision 4 |
| fps fallback, lossless caps | 25 in 4K Clear HDR 16-bit; no IMX585 lossless cap; ISO 1600 | fork main's lines (30, 30, 800) |
| IMX585 built-in fps list | QML to 60, Core to 120 | both to 60, as 1.6.0's lists; 100/120 through the operator's FPS steps (owner decision 5) |
| First hardware file | none | Core writes it (hardware-inputs). UI: the INA219 log says no file was found |

Where each value lives does not move: camera settings stay in `camera_settings.conf` (Core), UI preferences in UI.conf, `[storage]`/`[media]` keys wherever storage-settings puts them.

The one new key is UI.conf `fileTimecodeSeparate` (bool, absent = false = 1.6.0 behaviour). Writers: Core's `set_timecode_mode` (one writer for the meaning, beside `timecodeMode`, CMD-26) and the touch preset apply (R3 step 2, as every UI.conf toggle). Take-over of existing cameras: at every Core start, before the control server listens (the shape of `core-upstream App:6845-6857`), when `fileTimecodeSeparate` is false and UI.conf `timecodeMode` differs from `camera_settings.conf`'s mode, Core writes `true` once and logs one line. A 1.6.0 camera always has the two equal (1.6.0 copies one into the other, `ui-upstream ACB:1466-1471`), so it gets no key. Every field 1.6.0 publishes stays with its type; the only reply fields that change are inside the port's own `controls` and `media` events and the port's `fps_steps` list values.

## Commit plan

"Check here" always includes: `/home/user/build/bin/check_core.sh /home/user/wt/core-work <tag> both tests` (both builds, 17 host tests) for a Core commit, plus `smoke_core.sh` against the previous build with the two outputs diffed (no 1.6.0 field gone or retyped); `/home/user/build/bin/check_ui.sh /home/user/wt/ui-work <tag>` for a UI commit. Pi commands use `apertar-cmd` for `printf '%s\n' '<json>' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`.

Coordination with other themes:
- command-plane drops its commit 13 (= commit 1 here), the `startStoragePreroll` rename in its 15 (commit 4 here) and the timecode half of its 16 (commit 12 here replaces that body; the file mode follows the reply through `applyCoreState`).
- storage-settings 6-7 own `set_storage_preroll` and its wire form (`set_storage_preroll_auto_enabled enabled=`); commit 4 here calls what storage-settings 7 leaves and lands after it.
- camera-modes owns the IMX585 sizes, the stale `CC:3378` comment ("the 16-bit 25 is backendMaximumFps()", while `backendMaximumFps` returns `nullopt`, `CC:3426-3434`) and the fps ceilings; owner decision 4 is asked together with camera-modes' WebUI list source.
- hardware-inputs owns the Core first-start writer; this plan does not restore the UI writers (`design/hardware-inputs.md:165`, `:319`).

### Bridge idioms

**1. `ui: clip-name, buffer, log and pre-roll invokables return bool`** (Apertar-UI)
- `ACBH:194-200`, `ACB:618-727`: `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto`, `applyClipNameTemplate`, `applyCdngLog` become `bool`. Early returns return `false` after `setLastError`; the rest is `return sendCoreCommand(...)`. `requestClipNamePreview` is left alone (commit 20 deletes it).
- Delete the second `applyClipNameState(reply)` and its `QJsonObject reply` in `applyClipNameTemplate`. Delete the post-send assignments of `m_bufferSetting` and `m_cdngLogOn`: the replies carry `buffer_setting` (`App:12868-12869`) and `cdng_log` (`settingsBody`), which `applyCoreState` applies (`ACB:1732-1733`).
- No wire change; QML ignores the results. About -20 / +10.
- Here: UI build. Pi: Settings > Record, switch Write Buffer and Log; the tiles follow as before.
- Depends on nothing.

**2. `qml: Log is a dropdown next to Compression, sent as Core's off or auto`** (Apertar-UI)
- `ACB`/`ACBH`: `bool applyCdngLog(const QString &value) { return sendCoreCommand("set_cdng_log", {{"value", value}}); }`; Core refuses anything else (`App:13098-13099`).
- `SP:3463-3492`: the ActionTile becomes `InlineDropdownField { label: "Log"; value: cdngLogOn ? "auto" : "off"; options [{off,"Off"},{auto,"On"}]; fieldEnabled: !recording; onValueSelected: applyCdngLog(v) }`, shaped like Compression (`ui-upstream SP:3244-3261`). The `#9aa5b1` status text stays.
- About -16 / +14. Here: UI build. Pi: cDNG + Clear HDR, pick Log On, `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"cdng_log":"[a-z]*"'` shows `auto`.
- Depends on 1.

**3. `qml: Write Buffer is a dropdown`** (Apertar-UI)
- `SP:3415-3460`: the two ActionTiles become one `InlineDropdownField { label: "Write Buffer"; value: bufferSetting; options frames/"Frames", ram/"RAM"; fieldEnabled: !recording; onValueSelected: applyBufferMode(v) }`. Status text kept.
- About -20 / +10. Here: UI build. Pi: pick RAM, start and stop a take, `grep '^buffer=' ~/apertar-hardware.conf` (or the file storage-settings names).
- Depends on 1. If storage-settings renames `set_buffer_mode`, only the bridge line changes.

**4. `qml: automatic pre-roll is a toggle row, the pre-roll take a verb`** (Apertar-UI)
- `ACB`: rename `applyStoragePreroll` -> `bool startStoragePreroll()` (UIC-10). Delete `storagePrerollAutoKnown` (`ACBH:67`, `:148`, `:256`, `:417`; `ACB:2746-2749`); `m_storagePrerollAuto` defaults to `false`, Core's default (`ACBH:416`).
- `SP:5600-5640`: the tile calls `startStoragePreroll()`; the On/Off tiles become a title + description + `TogglePill` row copied from `gyroRecordToggle`, `checked: storagePrerollAuto`, `onToggled:` the switch invokable as storage-settings 7 leaves it (`applyStoragePrerollAuto(value)`); drop the `visible:` latch.
- No Core change here. About -40 / +20. Here: UI build. Pi: toggle, then `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"storage_preroll_auto":[a-z]*'` follows; the Storage Pre-roll tile still starts a take.
- Depends on 1 and storage-settings 7 (lands after it).

### One state path

**5. `ui: only the ISO and WB auto keys reset the get_state poll`** (Apertar-UI)
- `ACB:1621`: delete the unconditional `updateRefreshTimer()` in `applyCoreState`. Call it inside the two branches that change the interval's inputs, after `m_isoAuto = ...` (`ACB:1506`) and `m_whiteBalanceAuto = ...` (`ACB:1545`). 1.6.0 has no call in `applyCoreState`; the reply path keeps its own (`ACB:1221`, `:1226`, `:1823`).
- Fixes today's starvation by `timelapse_progress` (one event per shot, `CC:12375`) and keeps commit 7 safe. About -1 / +2.
- Here: UI build. Pi: ISO Auto, start a 1 s timelapse in Still Mode; the green ISO in use changes within 2 s when the light changes.
- Depends on nothing.

**6. `core: the controls and media events carry the state keys`** (Apertar-Core)
- `App:12352-12354`: the `controls` event writes `controls_errors` / `controls_warnings` instead of `errors` / `warnings`.
- `App:10827-10838` `mediaEventJson`: `media_state` / `media_alive` instead of `state` / `mounted`. The other members stay; `applyCoreState` reads none of them. The `state` rename is required: `applyCoreState` reads a top-level `state` as standby (`ACB:1486-1489`).
- No other reader: the WebUI takes no events (no `EventSource` in `WCP`), `handleTriggerEvent` matches neither, the preview socket client ignores them, `grep -rn '"mounted"' Apertar-UI/src Apertar-UI/qml` finds only `ACB:1338`.
- About -4 / +4. Here: builds, tests; `--simulate` with `socat` on the socket shows the new keys after `set_controls` and after `mount_media`; smoke diff: no 1.6.0 field changed (these events are port-only).
- Lands in the same push as 7 (Core and UI ship together). Between the two, the touch UI would see a pulled card up to 30 s late (the steady poll, `ACB:18`).
- Depends on nothing.

**7. `ui: controls and media events go through applyCoreState`** (Apertar-UI)
- `ACB:1328-1340` `applyCoreMessage`: add `controls` and `media` to the 1.6.0 `if (event == "standby" || ...)` list; delete their two branches. The `buffer` branch (`ACB:1345-1349`) stays, as `audio_level`.
- Delete `setControlsStatus` (`ACB:1424-1435`, `ACBH:453`); in `applyCoreState` replace its call (`ACB:1439`) by the inline form of `recording_has_dropped_frames`: `if (state.contains("controls_errors")) { compare both, assign, emit controlsStatusChanged(); }`. `setCoreMediaState` stays: it emits the signal `MediaStatusBridge` listens to.
- About -22 / +8. Here: UI build. Pi: pull the card: NO MEDIA within a second on the touch screen and the HDMI monitor; save a bad pin in Controls: the warning chip appears; during a 4K take with ISO Auto the ISO in use still moves.
- Depends on 5, 6.

### Presets

**8. `ui: touch presets carry the camera settings Core's presets carry`** (Apertar-UI)
- `ACB::applyCoreState`: keep as plain members (no `Q_PROPERTY`, as `m_lossyDngRatio`) the keys not yet kept: `fps_speed_ramp_stretch_audio`, `fps_speed_ramp_after`, `fps_phase_lock`, `hdr_threshold_high`, `hdr_threshold_low`, `hdr_blend`, `hdr_gain_adder`. Already kept: `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `clip_name_template`, `clear_hdr`, `timecode_mode`, `cdng_log`.
- `ACB::cameraPresetSettings` (`ACB:1254-1286`): insert in Core's order and value words (`App:7848-7872`): `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter` `angle|exposure`, `cameraFpsSpeedRampAudio` `real|stretch`, `cameraFpsSpeedRampAfter` `stay|return`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode` `free_run|rec_run`, `cameraClearHdr`, the four `cameraHdr*`, `cameraCdngLog` `off|auto` (`m_cdngLogOn ? "auto" : "off"`). Bools and numbers as JSON types; Core's parser reads them as text (`ControlProtocol.cpp:192-205`).
- `cameraConformFps` only if `conform_fps` survives (whichever theme decides adds or skips this line).
- Loading needs no change: `applyCameraPreset` forwards every `camera*` key.
- About -0 / +40. Here: UI build; in `--simulate`, send `apply_preset` over the socket with exactly the keys `cameraPresetSettings` now writes (copied from the code), then `get_state`: every value matches. Pi: save a touch preset with Clear HDR 16-bit and Log On, change both, load it: both come back.
- Depends on nothing.

### Timecode

**9. `core: set_timecode_mode records in UI.conf whether the file timecode is set apart`** (Apertar-Core)
- `SharedUiSettingsSnapshot` (`App:1871` area): `bool fileTimecodeSeparate = false;`; parse branch `else if (key == "fileTimecodeSeparate")` with `parseUiSettingsBool` (`App:2022` form).
- `set_timecode_mode` (`App:13295-13316`): `target=ui|files` adds `{"fileTimecodeSeparate","true"}` to the existing `updateSharedUiGeneralSettings` call (for `files`, a call of its own with that one pair); no target or `both` adds `{"fileTimecodeSeparate","false"}` only when the snapshot holds `true`, so a camera that never sets the timecodes apart gets no new key.
- Presets: writer `addBoolFromMap("fileTimecodeSeparate", uiSnapshot.fileTimecodeSeparate)` (`App:7757` form), reader `addBoolUpdate("fileTimecodeSeparate")` (`App:14452` form).
- No new command, no state field. The port UI keeps working unchanged (it ignores the key). About -0 / +12.
- Here: builds, tests; `--simulate` with a scratch HOME: `set_timecode_mode value=rec_run target=ui` -> `grep fileTimecodeSeparate ~/.config/CinePi/UI.conf` shows `true`; then no target -> `false`; on a fresh HOME, no-target calls leave no key. Smoke diff: no field change.
- Depends on nothing.

**10. `core: a split timecode on an existing camera is taken over at start`** (Apertar-Core)
- `App:8077-8091` (after `camera_.start`, before `controlServer_.start`): with the `stillSettings` snapshot already read there, when `!fileTimecodeSeparate` and `timecodeMode` differs from `camera_.settings().timecodeMode`, write `fileTimecodeSeparate=true` and log `ApertarCore timecode: UI and file timecode differ, kept apart (fileTimecodeSeparate=true)`.
- About -0 / +6. Here: builds, tests; `--simulate`: write UI.conf `timecodeMode=Rec Run` with Core's mode Free Run, start: the key and the log line appear; equal modes: no key.
- Pi (owner's camera): `journalctl -u apertar-core -b | grep 'ApertarCore timecode'` after the update.
- Depends on 9.

**11. `ui: SettingsBridge reads fileTimecodeSeparate`** (Apertar-UI)
- R3 steps 1-2 copied from `zebraEnabled`: `Q_PROPERTY(bool fileTimecodeSeparate READ ... WRITE ... NOTIFY ...)`, constructor read (default false), setter copied from `setZebraEnabled`, re-read in `pollExternalSettings`, in `serializeCurrentSettings` and `applySettingsObject`.
- No QML reads it yet: no behaviour change. About -0 / +25. Here: UI build.
- Depends on nothing (reads what commit 9 writes).

**12. `ui: the timecode tap and Mode set both timecodes again unless the file timecode is set apart`** (Apertar-UI)
- `ACB:750-771`, `ACBH:203`: `bool applyTimecodeMode(const QString &displayValue)` is the 1.6.0 body again (`ui-upstream ACB:622-636`). New `bool applyFileTimecodeMode(const QString &displayValue)`: parse, `return sendCoreCommand("set_timecode_mode", {{"value", normalized}, {"target", "files"}})`; `m_fileTimecodeMode` follows from the reply through `applyCoreState`.
- `ACB:1698-1707`: keep `m_fileTimecodeMode` and bring back 1.6.0's copy of Core's mode into UI.conf (`ui-upstream ACB:1466-1471`), after `m_settings.sync()` and only while `!m_settings.value("fileTimecodeSeparate", false).toBool()`.
- `CPg:1837-1843`: the tap is the 1.6.0 body (`ui-upstream CPg:1709-1715`) with the bridge call under `if (!settingsState.fileTimecodeSeparate)`; set apart, it is a UI-only assignment (QML-7).
- `SP:3998-4028`: the first row uses the same rule; the second row calls `applyFileTimecodeMode(v)`.
- Core unchanged. About -20 / +26.
- Here: UI build; `--simulate`: `set_timecode_mode value=rec_run` with no target -> `get_state` `timecode_mode` `rec_run`, UI.conf `timecodeMode=Rec Run`, no `fileTimecodeSeparate` key.
- Pi, stock camera (no key): tap the timecode, record a DNG take: `apertar-cmd '{"cmd":"get_state","id":1}' | grep -o '"timecode_mode":"[a-z_]*"'` shows the new mode and the clip's TimeCode starts at 00:00:00:00 for Rec Run. Owner's camera (key true after 10 or after the port UI's own taps): files at Free Run, tap to Rec Run: screen counts from zero, `timecode_mode` stays `free_run`.
- Depends on 9, 10, 11 (deployed together; then the owner's camera keeps its UI-only tap).

**13. `qml: the timecode card has Mode and Files, Files starts at Same as Mode`** (Apertar-UI)
- `SP:3998-4028`: first row label "Mode" (1.6.0). Second row label "Files", options "Same as Mode", "Free Run", "Rec Run"; value `settingsState.fileTimecodeSeparate ? fileTimecodeMode : "Same as Mode"`. A fixed value: `applyFileTimecodeMode(v)` (Core writes `true`). "Same as Mode": `applyTimecodeMode(settingsState.timecodeMode)` (Core writes `false`). The row follows through SB's file watcher (`SB:418-422`), also after a WebUI split.
- About -8 / +14. Here: UI build. Pi: pick Files = Free Run, then Same as Mode: `grep fileTimecodeSeparate ~/.config/CinePi/UI.conf` goes `true`, then `false`; a WebUI `target=files` change shows the fixed value in the touch row.
- Depends on 12. Owner decision 1.

**14. `qml: timecode labels are Free Run and Rec Run again`** (Apertar-UI)
- `SP:21` delete `timecodeChoices`, `SP:1219` delete `timecodeDisplayName`; the Mode options become plain `["Free Run", "Rec Run"]` (QML-23); description back to "Timecode behavior" or one clearer fragment without the new names.
- About -14 / +3. Here: UI build. Pi: visual.
- Depends on nothing (independent of 13). Owner decision 2 (the rename is offered upstream on its own; Core `2c259b9` and UI `08cefcf` are already isolated).

### Lists and caps

**15. `qml: without fps_max and iso_max the touch caps are fork main's again`** (Apertar-UI)
- `CPg:820-822`: `imx585Max = 30.0` for 4K; delete the 25 branch and its comment (reverts `d1efb67`).
- `CPg:525-532`: `isoMax` only when > 0, else `losslessIsoLimitedMode ? 800 : 0`, no Auto while that fallback applies (fork main `ui-main CPg:516-518`). `CPg:912-913`: put back `max = Math.min(max, 30.0)` for `losslessImx585Mode` (`ui-upstream CPg:815-816`).
- Reason: dead with the port Core, and different from the merge target's lines. No "do not edit" comment: R6 step 4 edits these tables with every new mode.
- About -5 / +5. Here: UI build; `diff` of `maximumSupportedFpsForResolution` against `ui-main qml/CameraPage.qml:738` is empty. Pi: none (runs only against a Core without `fps_max`).
- Depends on nothing.

**16. `core: the button fps fallback is 1.6.0's again`** (Apertar-Core)
- `App:1385-1389` `maximumPcfFpsForSettings`: `return 30.0;` and delete the stale comment, as `core-upstream App:1138-1145`. Used only when `fps_max` is 0 (`App:1414`).
- About -2 / +1. Here: builds, tests. Pi: none.
- Depends on nothing. If camera-modes rewrites this table, the line is theirs.

**17. `core: the IMX585 built-in fps list ends at 60, as 1.6.0's lists`** (Apertar-Core)
- `App:1401-1402`: delete the IMX585 branch of `builtInFpsSteps` (and its comment); the IMX585 falls to `{24,25,30,50,60}`, which equals the touch list (`CPg:923-930`) and 1.6.0's WebUI cut (`core-upstream WCP:4995-4996`). No QML change.
- The owner's rig gets 100/120 back by setting: FPS steps (UI.conf `fpsSteps`, shared by both UIs, `App:1968`).
- About -2 / +0. Here: builds, tests; `--simulate` `get_state` `"ui"` `fps_steps` for an IMX585 name has no 100. Pi: the operator adds 100 and 120 to FPS steps; in an HD crop mode both pickers offer them where `fps_max` allows.
- Depends on nothing. Owner decision 5.

### Clip names

**18. `qml: clip-name presets are a Pattern dropdown`** (Apertar-UI)
- `CNC:355-375`: the ActionTile Repeater becomes `InlineDropdownField { label: "Pattern"; options: presetList as {value: template, label}; value: currentTemplate; displayValue: matchesNoPreset ? "Custom" : <label> }`.
- About -18 / +12. Here: UI build. Pi: pick each pattern; "Next clip" follows.
- Depends on 1.

**19. `qml: the clip-name card edits by tap only`** (Apertar-UI)
- `CNC`: delete the ghost item (`CNC:578-600`), the `DropArea` and insertion marker (drag parts of `CNC:392-471`), `indexAt`, `beginDrag`/`moveDrag`/`endDrag` (`CNC:242-313`), the `drag*` properties (`CNC:39-48`) and the `dragActive` test in `syncFromBridge`; `ClipNamePill.qml:53-94`: long-press, `preventStealing` and the drag signals. Kept: pills in a `Flow`, palette tap to append, the selection tiles (move left/right, Edit text, Remove), "Next clip".
- About -210 / +5. Here: UI build. Pi: on the touch screen, build a pattern with taps only.
- Depends on 18. Owner decision 3: if drag stays, this commit becomes "rebuild drag on the reorderDelegate pattern".

**20. `ui: the clip-name card saves each edit, without a preview command`** (Apertar-UI)
- `CNC:150-158`, `:330-343`: delete `saveTimer` and `previewTimer`; `changed()` calls `saveNow()`; the recording handler (`CNC:320-326`) loses its timer stops. "Next clip" shows `clipNameExample` (`CNC:515-516`), which every save reply carries (`App:374`).
- `ACB`/`ACBH`: delete `requestClipNamePreview`, `clipNamePreview`, `m_clipNamePreview`, `clipNamePreviewChanged`. Core's `preview_clip_name` stays for the WebUI.
- Fixes the edit lost when a take starts within the 1 s delay.
- About -45 / +5. Here: UI build. Pi: move a pill and press record at once: the take uses the new name. Delete the `{clip}` pill: `saveNow` puts `_{clip}` back before the send (`CNC:162-167`), so the card does not jump.
- Depends on 1, 19.

**21. `qml: the clip-name card keeps tokens it does not know`** (Apertar-UI)
- `CNC:76-93` `parseTemplate`: any `{name}` becomes a token pill; the palette stays the QML list.
- About -2 / +3. Here: UI build. Pi: the WebUI sets a template with a token the touch palette lacks; a tap edit on the touch card keeps it.
- Depends on nothing.

**22. `ui: the clip-name card shows without a presence latch`** (Apertar-UI)
- Delete `clipNameKnown` (`ACBH:76`, `:157`, `:434`; `ACB:670-673`) and its use in `SP:2031` (version policy above).
- About -10 / +1. Here: UI build. Pi: the card is there at start.
- Depends on 20.

### First start

**23. `ui: the INA219 log says when no hardware file was found`** (Apertar-UI)
- `src/Ina219Bridge.cpp:262-267`: when no candidate file exists, log "INA219 config: no apertar-hardware.conf found, built-in defaults (bus=.., address=..)" and leave `m_configPath` empty. No UI writer comes back.
- About -3 / +3. Here: UI build. Pi: on a camera without the file, `journalctl -u apertar-ui -b | grep INA219`.
- Depends on nothing; the file itself comes from the hardware-inputs theme's Core writer.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| Two timecodes (`set_timecode_mode target=ui|files|both`, default both) | Core keeps the optional `target` (App-5-F7). The touch UI sends no target or `files`; a screen-only change is a UI.conf assignment | An optional argument whose absence gives the old behaviour; an unmodified client works. It breaks C1-I18 (UI.conf and camera mode equal) on purpose, only after the operator chooses it |
| UI.conf `fileTimecodeSeparate` | Written by Core in `set_timecode_mode`, beside `timecodeMode`; snapshot member, both preset writers and the reader (R3 steps 1-2, 7, 10); taken over at start; no command, no state field, no WebUI control | It lets a stock camera, with no key, behave as 1.6.0, keeps the owner's UI-only tap by setting, and keeps the WebUI's split visible to the touch UI |
| Clip-name composer (`ClipNameCard.qml`, `ClipNamePill.qml`) | Own QML files, tap editing only, one save per edit | No precedent for a template composer; upstream has standalone card components (`SystemSectionCard.qml`) |
| Core events `controls`, `media`, `buffer` | Kept; `controls` and `media` spelled with state keys and read by `applyCoreState`; `buffer` with its own branch | 1.6.0 has no such events; shapes of `media_write_state` and `audio_level` |

## For the owner

1. **Timecode tap.** A: 1.6.0 only (commits 12-13 without 9-11; the tap always sets both). B: A plus `fileTimecodeSeparate` (commits 9-13): the tap is UI-only once the files are set apart, and your camera is taken over at start. C: keep the port's split as default (a stock camera changes behaviour; not mergeable). Recommendation B. Cost: about +18 Core, +40 UI, one UI.conf key, documented as new ground. If your two modes are equal on the day of the update, pick a fixed "Files" value once.
2. **Labels "Time of Day" / "Clip".** A: back to Free Run / Rec Run (commit 14), rename proposed upstream on its own. B: keep. Recommendation A; the WebUI half is webui-state's.
3. **Clip-name drag.** A: delete drag, keep tap editing (commit 19, -210). B: rebuild drag on the reorder popup's pattern, about -100 / +60, still untested on touch. Recommendation A.
4. **Extra IMX585 families on the touch screen** (2K crop, 4:3, 1:1; asked together with camera-modes' WebUI list source). A: no; the touch lists stay 1.6.0's and the WebUI offers the rest. B: the bridge calls `list_sensor_modes` once per sensor, as camera-modes does for the WebUI, with the 1.6.0 list as fallback (new ground, about +60 UI lines). Recommendation A for the merge; B as a later, separate change. Hand copies of the class tables are not offered: they would show modes the original driver lacks and leave the two UIs on different sources.
5. **IMX585 built-in fps list.** A: the touch list gains 100/120 as Core's (stock cameras then show two greyed values in every IMX585 picker). B: Core's list ends at 60 again (commit 17), you add 100 and 120 to FPS steps. Recommendation B: a stock camera's lists stay 1.6.0's in both UIs, your rig gets them by setting.
6. **`preview_tdn` and `media_trim` in presets** (X-state-consistency-14). A: add them to both writers and the reader. B: one comment in both writers saying they are deliberately not preset fields. Recommendation B (camera-wide switches). Cost: 2 lines.

## Risks and what was not determined

- The touch UI cannot be driven here. Every QML change is checked by build only (QML compiled ahead of time catches unknown properties, not behaviour). Each commit names the Pi step.
- Commit 5: the interval now changes only on `iso_auto`/`wb_auto` keys and on command replies. Not determined without the camera: whether any other path flips `m_isoAuto` without such a key (`ACB:314`, `:329`, `:404`, `:419` are the command invokables, whose replies call `updateRefreshTimer()` themselves). Pi check in commit 5.
- Commit 6: whether any script on the owner's rig reads the `media` event's `state`/`mounted`. `grep -rn '"mounted"' ~/ 2>/dev/null` on the Pi settles it.
- Commit 10: a UI.conf without a `timecodeMode` line reads as Free Run, so a camera with no UI.conf line and Core on Rec Run gets the switch. 1.6.0 never leaves that state (both writers write both), so it can only come from a hand-edited file.
- Commit 12: the UI.conf copy runs `m_settings.sync()` on each `get_state` reply (1 s with ISO/WB auto). QSettings re-reads only a changed file; cost not measured on a Pi 4. `top -H -p $(pidof ApertarUI)` during ISO Auto settles it.
- Commit 20: one socket round trip per tap (at most 3 s on the GUI thread, UIC-16) and one `camera_settings.conf` write per edit by Core's persister. Not measured; a fast series of taps on the Pi shows whether the card lags.
- First start: the UI may start before Core has written the file on a fresh image. The UI's compiled defaults equal the template's `[display]` and `[ina219]` values, so a race changes nothing visible; the INA219 line then says no file (commit 23).
- Pi models: nothing here touches GPU, ISP or I2C paths. Caps follow Core's `fps_max`, which carries per-board limits. Commit 7 adds nothing per frame; the buffer event keeps its small branch.
- Line estimates are from reading, not from a diff.

## Findings covered

| Finding | Commit |
| --- | --- |
| UI-control-bridge-F1 | 1, 2, 4 (the pre-roll wire form: storage-settings 6-7) |
| UI-control-bridge-F2 | 6, 7 (buffer branch kept, see the challenge table) |
| UI-control-bridge-F5 | 12, 13 |
| UI-settings-qml-F1 | 2, 3, 4, 18 |
| UI-settings-qml-F2 | 12, 13, 14 |
| UI-settings-qml-F3 | 19 (owner decision 3), 20 |
| X-state-consistency-1 | 8, 9 |
| X-state-consistency-3 | not a touch-UI commit: the 1.6.0 lists match Core after camera-modes; extra families owner decision 4 |
| X-commits-ui-drivers-2 | 15, 16 (the CC comment: camera-modes) |
| X-stock-behaviour-8 | 9-13 |
| UI-bridges-F2 | 23 (UI side); the Core writer and template: hardware-inputs |
| UI-bridges-F5, UI-control-bridge-F3 | 1 |
| UI-bridges-F7, UI-settings-qml-F10, X-protocol-security-4 | 12 |
| App-5-F2 | pre-roll name: storage-settings; the four camera switches: command-plane (owner list there) |
| App-5-F7 | new ground (section above); Pi check in 12 |
| UI-control-bridge-F9 | 4, 22 |
| UI-settings-qml-F8 | 21 |
| UI-settings-qml-F9 | 20 |
| X-state-consistency-4 | 17 (owner decision 5) |
| X-state-consistency-5 | 15, 16 (the WebUI re-application `WCP:7490-7509`: webui-state) |
| UI-camera-qml-F3 | 15 |
| X-stock-behaviour-2 | 23 + hardware-inputs |
| X-state-consistency-14 | owner decision 6 |
| WCP-05-F2, WCP-05-F3, X-state-consistency-6 | not covered: WebUI side, webui-state |

## What the challenge changed

Each row was checked in the code by the final reader.

| Point | Decision | Why |
| --- | --- | --- |
| Commit 8: buffer event into `applyCoreState` stops the poll | Challenger right. Buffer branch kept (commit 7); and commit 5 added | `ui-work ACB:1621` calls `updateRefreshTimer()` unconditionally, `ACB:1014` `setInterval` restarts the timer; buffer events every 250 ms (`App:10995-11049`). 1.6.0 has no call there (`ui-upstream ACB:875-882`, calls at `:125-145`, `:1585`). The same restart already starves the poll on `timelapse_progress` (`CC:12375`), so commit 5 moves the call into the `iso_auto`/`wb_auto` branches (`ACB:1506`, `:1545`) |
| Commit 8 precedent "every event goes whole" | Challenger right | 1.6.0 keeps `audio_level` in its own branch (`ui-upstream ACB:1196-1199`); UIC-4 is about state keys |
| Commit 7 interim lag 1-5 s | Challenger right; 6 and 7 ship in one push | Steady poll 30000 ms (`ACB:18`, `:1016`) |
| Commits 4, 5, 6 vs storage-settings and command-plane | Challenger right. 4 and 6 dropped; old 5 is now 4 (rename, toggle row, latch) | storage-settings 6-7 replace `set_storage_preroll` (`design/storage-settings.md:205-225`); command-plane 14-15 plan another name (`design/command-plane.md:214-227`). Added: the member default becomes `false` (`ACBH:416` is `true`, Core default off since `0977dd6`) |
| Commit 1 = command-plane 13; commit 10 vs command-plane 16 | Challenger right | Same lines (`command-plane.md:206-212`, `:229-232`). Bridge idioms are this theme's; coordination list names what command-plane drops |
| Commit 10 left out 1.6.0's UI.conf copy | Challenger right | `ui-upstream ACB:1466-1471` copies; `ui-work ACB:1698-1707` does not. Commit 12 restores it, gated on `fileTimecodeSeparate` |
| Commit 10 alone loses the rig's UI-only tap | Challenger right, solved by order | Core writes the key (9), takes over the rig (10), SB reads it (11) before the tap changes (12); and the port UI's own `target=ui` taps already set it once 9 is deployed |
| Commit 11's UI-only key misses the WebUI split and the presets | Challenger right | WebUI sends `target` (`WCP:9809-9826`); Core is the one writer for the meaning, next to `timecodeMode` (`App:13309-13314`). Snapshot member and both preset writers (R3 steps 7, 10). Narrowed: `false` is written only over a `true`, so a stock UI.conf gets no key; no `"ui":{}` state field (no reader needs it) |
| Commit 11 take-over on existing cameras | Challenger right; shape chosen | At start, before the control server, beside the still-mode reconcile (`core-upstream App:6845-6857`; port `App:8077-8092`). Commit 10 |
| Commit 13 reason and Pi check | Challenger right | 1.6.0 has no Clear HDR (`grep -ci clearhdr` = 0 in `ui-upstream qml/CameraPage.qml`); branch runs only against fork main Core. Reason: differs from fork main (`ui-main CPg:780-781`). No Pi check; no "do not edit" comment |
| Commits 13 and 15 one idea | Challenger right; merged into 15 | Both bring back fork-main lines used only without `fps_max`/`iso_max` |
| Stale comment in CC | Challenger right; camera-modes' line | `CC:3378` vs `backendMaximumFps` `CC:3426-3434` |
| Commits 17 and 24 | Challenger right; dropped | camera-modes restores 2076/1038 (`camera-modes.md:83`, `:100`); hand copies would offer modes the original driver lacks; camera-modes moves the WebUI to `list_sensor_modes` (`:179`). Owner decision 4 |
| Commit 9 risk (JSON types) | Challenger right; taken off the risk list, no dependency on 2 | `ControlProtocol.cpp:192-205`, `:139-161` |
| Commits 1 and 20, preview path | Challenger right | Save reply carries `clip_name_example` (`App:374`, `:13269-13271`); commit 20 deletes the preview path, commit 1 leaves it. Pi check corrected: `saveNow` adds `_{clip}` itself (`CNC:162-167`) |
| Mixed-version policy in three answers | Challenger right | One sentence at the top (CMD-30) |
| Owner list | Partly right | Log-enum question removed (settled, `command-plane.md:293`), pre-roll name removed (storage-settings'), list question asked with camera-modes and reworded (no hand-copy option). The challenger's "take-over" question is not an owner decision: it is commit 10 |
| Precedent citation `CPg:773-797` | Challenger right | Function at `ui-upstream CPg:733` |
| Commit 16 (not challenged): touch list gains 100/120 | Changed by the final reader | Adding them shows two greyed values in every IMX585 picker of a stock camera (`CPg:860-872` greys values above `fps_max`); 1.6.0's lists end at 60 (`core-upstream WCP:4995-4996`, `ui-upstream CPg:803-807`). Now commit 17 deletes Core's IMX585 branch; the rig uses FPS steps. Owner decision 5 |

## Checked against the owner's recorded decisions

Audit 2026-11-21 against `owner-recorded-decisions-a.md` (DA-*), `owner-recorded-decisions-b.md` (DB-*) and their sources (`working/playback/decisions.md` "Note for O10" and the no-touch-screen constraint, `fork-log.md:98`, `:121`, `:191`, `:204`, `:213`, `working/drop-frames/README.md:93-102`, `working/ramp-ladder/design/design-T33.md`, `working/clearhdr16-preview.md:53-64`). Lane commits read at `/home/user/wt/lane-ui1` `ac1fc28..210ffe5` (plan 1 `98d7a1c`, 2 `3b2c98b`, 3 `797180e`, 5 `53e20e0`, 7 `57dd0e8`, 8 `968ff25`, 11 `30961b6`, 12 `477eb11`, 13 `28ea94e`, 14 `10fb9e3`, 15 `210ffe5`). Not made: Core 6, 9, 10, 16, 17; UI 4, 18-23. Rule: a decision stays; where it makes a stock camera behave differently from 1.6.0 it becomes a setting at the 1.6.0 value.

Facts about his camera this audit relies on (all **confirmed** in KB copies):
- `[display] hdmi_external_only=true`, `windowed=false`, 1920x1080 `landscape_large` (`working/tools/controls_fixture_apertar-hardware.conf:296-305`, 2026-11-08). With that key the touch UI's main window is hidden (`ui-work src/main.cpp:432-433` `window->hide()`); the HDMI shows only `ExternalMonitorWindow` ("Assist Feed"). **To look at any Settings or camera-page change he sets `hdmi_external_only=false`, restarts the UI (his command: `sudo systemctl restart apertar-ui`), uses a mouse on the HDMI monitor, and sets it back afterwards.** Below this is called "HDMI look".
- UI.conf `timecodeMode=Rec Run` and Core `timecode_mode` `rec_run` on 2026-11-10/11 (`working/drop-frames/nvme-campaign/run-20261110/audio-forensics/*/UI.conf:70`, `*/api_state.json:69`): his two timecodes are **equal**, so commit 10's take-over writes nothing on his rig.
- UI.conf `fpsSteps=25, 30, 50, 60` (same files, `:33`): his pickers and dials already end at 60. No KB page or fork-log row records 100/120 as his request; they came in `caa0153` ("Adds ... fps steps 100 and 120", desk only). The STATE line "Your rig uses 100 and 120" is not supported.
- HDR knobs on his rig 4095/0/5/1 (`working/clearhdr16-preview.md:61`) = the lane's member defaults.

| commit | touches decision (id, his words) | verdict | what changes in the commit |
| --- | --- | --- | --- |
| 1 (lane `98d7a1c`) | DB-65 / DA-104 "everything back" (Log, RAM buffer, clip names kept) | fine | none. Replies carry `buffer_setting` (`core-work App:12853-12854`), `cdng_log` (`App:356`) and the clip-name keys; `applyCoreState` applies them (`lane ACB:1749-1751`). Look: HDMI look, Settings > Record, switch Write Buffer and Log; or `get_state` over the socket |
| 2 (lane `3b2c98b`) | DB-64 "Log runs in parallel with every compression ... an extra option, never a mode of its own"; DB-62 "the UI says Log is not applied there"; DB-63 one step down | fine | none. A separate "Log" field beside Compression keeps it an extra option; the "Not applied: in SDR ..." and "Stores one step down" text stays. No recorded choice of the ActionTile look (grep of the KB: none). Look: HDMI look, cDNG + Clear HDR, Log On; WebUI shows the same `cdng_log` |
| 3 (lane `797180e`) | DB-65 RAM buffer kept; DB-101 RAM fraction his | fine | none. No recorded choice of the two tiles. Look: HDMI look, cDNG, Write Buffer RAM, then `grep '^buffer=' ~/apertar-hardware.conf` |
| 4 (not made) | preroll audit: command `storage_preroll` keeps its name (`longtakes.py:3197`); pre-roll off by default, his rig turns it on (C5) | fine | none. Only the bridge invokable is renamed; the wire command stays `storage_preroll`. Look: HDMI look; `get_state` `storage_preroll_auto` |
| 5 (lane `53e20e0`) | none | fine | none. Look: WebUI ISO Auto with a 1 s timelapse; the HDMI monitor's ISO readout (external window) moves |
| 6 (Core, not made) | DA-22 "Touch warning chip ... only visible when something is wrong" | fine | none. `longtakes.py:466`, `:1727` read `media_state`/`media_alive` from `get_state`, not from the event; no KB tool reads the event's `state`/`mounted` |
| 7 (lane `57dd0e8`) | DA-22 | fine, only with Core 6 | the lane commit must not be integrated before Core 6: today's `media` event (`{"event":"media","state":...,"mounted":...}`, `core-work App:10808-10809`) would reach `applyCoreState`, whose `state` branch sets `m_standby` from it (`lane ACB:1481-1484`), and NO MEDIA and the chip would wait for the 30 s poll. Look: WebUI Controls, save a bad pin: chip on the HDMI look; `socat` on the socket shows `media_state` |
| 8 (lane `968ff25`) | DA-92 / DB-31 request 21 "`conform_fps`, the project's timeline rate, default 25 ... carried across formats and presets"; DA-76 "a preset's `cameraTimecodeMode` no longer overwrites the UI copy"; DA-93 stretched WAV default on; DA-87 / DB-56 phase lock off | conflict | the lane leaves out `cameraConformFps` "because conform_fps is to be removed"; the storage-settings audit keeps it (DA-92). Add a plain member `double m_conformFps = 25.0` read from state `conform_fps` (`core-work App:9465`) and `result.insert("cameraConformFps", m_conformFps)` after `cameraTimecodeMode`, Core's order (`App:7805-7806`); Core's reader takes 1-120 (`App:14354-14357`). About +4. Defaults `m_fpsSpeedRampStretchAudio=true`, `m_fpsPhaseLock=false` match DA-93, DA-87. Stock: the extra keys carry the camera's own values, so a 1.6.0 preset loads as before. Look: HDMI look, Settings > Presets save and load; `get_state` `conform_fps` |
| 9 (Core, not made) | DA-76 "The timecode the DNGs carry is now its own setting: File timecode ... apart from the UI timecode" | fine for the touch UI; leaves a stock difference in the WebUI | the port WebUI always sends a target (`core-work WCP:16094-16099` Settings, `:11183-11188` Favorites), so with commit 9 a stock camera's first WebUI timecode change sets `fileTimecodeSeparate=true`, and even today its "UI timecode" block changes the screens only, unlike 1.6.0's single control with no target (`core-upstream WCP:10021-10023`, `:7042-7043`). Variant (one more Core commit, WebUI, beside 13): the WebUI card gets the touch card's shape: "Mode" sends no target (target `ui` only while separate), "Files" offers "Same as Mode" / Free Run / Rec Run; the state carries `ui.file_timecode_separate` (bool) beside `ui.timecode_mode` (`core-work App:9616`; 1.6.0 has the `ui` object with `timecode_mode`, `core-upstream App:7966`). About +2 Core, +25 page. Same Favorites block |
| 10 (Core, not made) | DA-76 | fine; does nothing on his rig | his modes are equal (Rec Run / `rec_run`, facts above), so no key is written and after the update his tap sets both. One step for him before the update, in the rig list: Files = Rec Run once (touch, HDMI look) or `apertar-cmd '{"cmd":"set_timecode_mode","value":"rec_run","target":"files","id":1}'` after Core 9. No code change |
| 11 (lane `30961b6`) | DA-76 | fine | none |
| 12 (lane `477eb11`) | DA-76, including "a preset's `cameraTimecodeMode` no longer overwrites the UI copy" | conflict until Core 9 and 10; small fix inside | (a) Integrate only in the same push as Core 9 and 10. Without them UI.conf never holds the key, so on his rig the tap and Mode set the file timecode too, every `get_state` reply copies the file mode over UI.conf `timecodeMode` (`lane ACB:1715-1723`), and a WebUI "UI timecode" change reverts within one poll. (b) `applyCameraPreset` (`lane ACB:1300`) forwards `fileTimecodeSeparate` with `timecodeMode`, and Core 9's reader takes it, so Core writes it before the reply (`App:14539-14543` writes UI.conf before `okReply`). Today the reply's copy runs before `SettingsBridge` applies the preset's key (`SB:2255` then `:2290-2291`), so a split touch preset loaded on an unsplit camera whose screen mode equals the preset's ends with the file mode on the screens. About +1. Look: HDMI external window shows the screen timecode as today (no HDMI look needed); WebUI shows both modes |
| 13 (lane `28ea94e`) | DA-76; DA-71 R1 (the card shows the File timecode the take was recorded with) | fine | none. "Same as Mode" is the 1.6.0 value; a fixed Files value is the operator's switch. Look: HDMI look, Settings > Timecode; `grep fileTimecodeSeparate ~/.config/CinePi/UI.conf` |
| 14 (lane `10fb9e3`) | no recorded decision: the rename `2c259b9` / `08cefcf` carries his author name but no KB row ties it to a request (`fork-log.md:121`, `:213` "fork-only"; no DA/DB row) | needs his answer | none in code. The lane made it ahead of owner decision 2; hold it out of integration until he answers (it is independent of 11-13 and reverts cleanly). Stock: either answer is only shown words. Look: HDMI look, Settings > Timecode |
| 15 (lane `210ffe5`) | DB-15 "The 25 fps cap of 4K Clear HDR 16-bit is lifted to the driver maximum" (replaces DB-12); DA-103 27 fps; DB-17 lossless ISO 1600 | fine | none. The 25 branch goes, as DB-15 asks. The 800 and 30 lines run only without `iso_max`/`fps_max`; Core sends `iso_max` from `maximumIsoForSettings` with `kLosslessMaxIso` (`core-work CC:3169-3175`), so his 1600 stays Core's. DB-17's stock treatment (1600 vs 800) is camera-modes' held item, not this commit. Look: nothing to see with this Core |
| 16 (Core, not made) | DB-15, DA-103 | fine | none. The fallback runs only when `fps_max` is 0 |
| 17 (Core, not made) | DB-37 "the lists live in `~/.config/CinePi/UI.conf` ... `fpsSteps` ... hardware controls step through the same lists" (approved); DB-36 greyed above the ceiling; DB-52 fps max from the probe | fine | none. No recorded decision on 100/120; his own `fpsSteps` ends at 60, so his pickers and dials do not change. 100/120 come back by the approved mechanism (FPS steps). Look: WebUI value lists, `get_state` `fps_steps` |
| 18 (not made) | DA-104 / DB-65 clip names kept; presets `Original`, two time-of-day, `Standard` (`c9e7707`, no request recorded) | fine | none. Look: HDMI look, Settings > Record > Clip names |
| 19 (not made) | DA-104 / DB-65 clip names kept; no recorded decision on drag (the composer's drag came with `014a2bf`/`606f137`; the touch card was never tried, `drop-frames/README.md:102`, `:158`). DA-42 "drag and drop" is the Controls editor, not clip names | needs his answer (owner decision 3, held in STATE) | none. Stock: the card exists only in the port. He can try the touch drag with a mouse on the HDMI look before he answers (QML `MouseArea` drag and press-and-hold take a mouse) |
| 20 (not made) | DA-104 | fine | none. Look: HDMI look, edit then press record from the WebUI |
| 21, 22 (not made) | DA-104 | fine | none |
| 23 (not made) | DA-7 "INA219 stays on by default"; DA-8 "not found ... not as a warning" | fine | none: an info line, not a warning. His file exists (`[ina219] enabled=false`), so his journal does not change |
| New ground: two timecodes, `fileTimecodeSeparate` | DA-76 | fine with commits 9 (WebUI variant), 10, 12 (a, b) | none beyond the rows above |

Plan text corrected by this audit:
- Commit 8's "cameraConformFps only if conform_fps survives": it survives (DA-92), so the line is added.
- "For the owner" 1, last sentence, applies to him: his modes are equal, so he takes the one step of row 10.
- Every "Pi:" line that says "on the touch screen" reads "HDMI look" on his rig (DA-77); the 720x720 touch steps go to the original developer.
- No tutorial or KB tool (`tutorials/`, `working/tools`, `working/drop-frames`) sends `set_timecode_mode`, reads the `media`/`controls` events or a renamed invokable (grep: `longtakes.py` reads `media_state` from `get_state` only).

### Decisions this plan must keep

- File timecode is its own setting (DA-76): `set_timecode_mode target=ui|files|both` stays; the split is on once the operator picks a fixed Files value (UI.conf `fileTimecodeSeparate`), off = 1.6.0. Commit 12 lands only with Core 9 and 10; the WebUI card gets the same Mode / Files shape.
- A preset never puts the file mode over the screens' mode (DA-76): `applyCameraPreset` forwards `fileTimecodeSeparate`.
- `conform_fps` stays and both preset writers carry `cameraConformFps` (DA-92).
- The 25 fps cap of 4K Clear HDR 16-bit stays gone; the driver maximum applies (DB-15, DA-103).
- Lossless ISO 1600 stays Core's `iso_max` (DB-17); the QML 800 line is only the no-`iso_max` fallback.
- FPS lists come from UI.conf `fpsSteps` (DB-37); values above the ceiling greyed (DB-36).
- Log is an extra option next to Compression, its "not applied in SDR" text stays (DB-62, DB-64); RAM buffer stays (DB-65).
- Clip names stay (DA-104); whether the touch card keeps drag is his answer.
- Defaults he chose: stretched WAV on (DA-93), phase lock off (DA-87).
- Pre-roll wire command stays `storage_preroll` (his `longtakes.py`).
- His camera has no touch screen and runs `hdmi_external_only=true` (DA-77): every UI check is an HDMI look with a mouse, the key set back afterwards.

### Open questions a recorded decision already answers

| question | decision | answer |
| --- | --- | --- |
| For the owner 1: timecode tap A / B / C | DA-76 (and the stock rule) | B. Plus the WebUI card in the same shape, the preset forward, and his one Files step (modes equal on his rig) |
| owner-decisions.md 9: restore one timecode (A) or keep the split (B) | DA-76 | Keep the split as an operator setting (this plan's B), not A |
| Commit 8: `cameraConformFps` in or out | DA-92 / DB-31 | In |
| For the owner 5: IMX585 built-in list to 60 or 120 | DB-37 (lists in UI.conf, approved); his `fpsSteps=25, 30, 50, 60` | B (commit 17): nothing recorded asks for 100/120, his lists already end at 60 |
| Commit 15: keep the 25 fps fallback for 4K Clear HDR 16-bit | DB-15 replaces DB-12 | No |
| For the owner 2: labels Time of Day / Clip | none recorded | still his; lane commit 14 held until he answers |
| For the owner 3: clip-name drag | none recorded (DA-42 is the Controls editor) | still his; he can try it with a mouse first |
| For the owner 4, 6 | none recorded | still his |
