# Inventory: unit "UI-bridges" (stage 1 of 3)

What the port added or changed in the touch UI's C++ bridges, the CFE automounter, the preview socket client,
`main.cpp` and the QML file lists. Facts only. No judgement in this stage.

Labels: **confirmed** = read in code at the ref given. **probable** = inferred, reason stated.
**unconfirmed** = the command that settles it is given. Refs: `@port` = `cinemate-port` `7ea9afc`,
`@main` = `origin/main` `4415a55`, `@up` = `upstream-1.6.0` `43888e5` (UI) / `35dbe67` (Core).
Core refs at the port are against `01f170c`.

## 0. Scope and method

| Item | Value |
| --- | --- |
| Diff | `git -C /home/user/Apertar-UI diff --minimal origin/main cinemate-port -- <15 paths>`, saved as `/home/user/build/review/inv-UI-bridges.diff` (1648 lines, read whole) |
| Size | 15 files, +462 / -696 |
| Files | `src/ApertarControlBridge.hpp` (+141 / -1), `src/SettingsBridge.cpp` (+117), `src/SettingsBridge.hpp` (+42), `src/MediaStatusBridge.cpp` (+23), `src/MediaStatusBridge.hpp` (+6), `src/DisplayConfigBridge.cpp` (+5 / -297), `src/DisplayConfigBridge.hpp` (+4 / -4), `src/Ina219Bridge.cpp` (-280), `src/SystemActionBridge.cpp` (+36 / -103), `src/CfeAutomounter.cpp` (+42 / -11), `src/ApertarPreviewSocketClient.cpp` (+30), `src/ApertarPreviewSocketClient.hpp` (+7), `src/main.cpp` (+4), `CMakeLists.txt` (+3), `qml.qrc` (+2) |
| `@main` vs `@up` in this scope | Only `src/ApertarControlBridge.hpp` differs (+6: `clearHdr`, `applyClearHdr`, commit `4415a55`). Every other scope file is identical at `@main` and `@up` (`git diff --stat upstream-1.6.0 origin/main -- <paths>`), so upstream line numbers hold for `@main` |
| Read for context, not in scope | `src/ApertarControlBridge.cpp` (the commands and state keys behind the header), QML call sites, Core handlers |
| Commits | 19 of the 39 UI port commits touch the scope. 17 have a net effect. `c13b846` and `010f8ad` cancel each other |

## 1. Commits that touch the unit

"Tested" is the commit message's own `Tested:` line. "fork-log" is the row in `/home/user/apertar-kb/fork-log.md`.
Neither is proof of behaviour.

| Commit | Date | Subject | Scope files | Tested (commit message) | fork-log |
| --- | --- | --- | --- | --- | --- |
| `160898c` | 10-26 | ui: follow Core's media state, not only the mount table | `ApertarControlBridge.hpp`, `MediaStatusBridge.{cpp,hpp}`, `main.cpp` | "pi build (see next run)" | `:236` "built 22:55, tested" |
| `dc471c1` | 10-26 | ui: automounter releases a card pulled while mounted | `CfeAutomounter.cpp` | "pi build (see next run)" | `:235` "installed 22:59, tested on the Pi (pull + re-insert, no reboot)" |
| `ec9f109` | 10-27 | ui: FPS picker sends only set_fps during a speed-ramp take | `ApertarControlBridge.hpp` (2 members) | "host build of the whole UI with Qt 6.4.2. Not run on the Pi" | `:226` "tested 2026-10-28 (C0022)" |
| `f1edf96` | 10-28 | ui: values the camera sets are green; ISO list follows iso_max; ISO lock | `ApertarControlBridge.hpp`, `DisplayConfigBridge.cpp` (+6, later removed by `c9d841f`) | "desk only (built on the Pi next)" | `:225` "tested 2026-10-28 (Patrik: works well)" |
| `ed0d7b5` | 10-28 | ui: pickers follow the value lists, greyed above the ceiling (T33) | `ApertarControlBridge.hpp`, `SettingsBridge.{cpp,hpp}` | "desk only" | `:222` "tested 2026-10-28 (Patrik)" |
| `da2a9b5` | 10-28 | ui: recording frame and red timecode switches | `SettingsBridge.{cpp,hpp}` | "desk only" | `:219` "tested 2026-10-28 (Patrik)" |
| `c716dec` | 10-28 | ui: compression is greyed out while the Mode Ladder is active | `ApertarControlBridge.hpp` | "desk only" | `:215` "built 2026-10-28" |
| `7029db1` | 10-29 | ui: UI timecode and file timecode are set apart | `ApertarControlBridge.hpp` | "Pi build pending" | `:204` "building 2026-10-29, not tested" |
| `c9d841f` | 10-29 | ui: stop writing a default hardware file when it is missing (T38, part 4) | `DisplayConfigBridge.cpp`, `Ina219Bridge.cpp` | "desk only (UI build on the Pi not yet run)" | `:211` "fork-only", no test recorded |
| `7c41a27` | 10-29 | ui: HDMI 1080p is the display fallback (T38, part 5) | `DisplayConfigBridge.{cpp,hpp}` | "desk only (UI build on the Pi not yet run)" | `:212` "fork-only", no test recorded |
| `ea44bd7` | 10-30 | ui: a Controls chip on the camera page and a read-only Controls card | `ApertarControlBridge.hpp`, `CMakeLists.txt` | "pi build, qmllint of the new chip; not seen on a touch screen" | `:214` "fork-only" |
| `841d0ed` | 10-31 | drop-frames: buffer bar, safety-stop pill, Frames / RAM, Log and storage pre-roll (7 commits squashed) | `ApertarControlBridge.hpp`, `SettingsBridge.{cpp,hpp}` | "not compiled or run here; the whole branch compiles on the Pi; identifiers were checked by grep. Not yet seen on the screen" | `:240` "compiles on the Pi" |
| `606f137` | 11-01 | drop-frames: Clip names card in Settings > Record | `ApertarControlBridge.hpp`, `CMakeLists.txt`, `qml.qrc` | no `Tested:` line | `:240` "untested by hand" |
| `5697b54` | 11-01 | drop-frames: faint red outline on the audio meter, with a switch | `SettingsBridge.{cpp,hpp}` | no `Tested:` line | no row (`grep 5697b54 fork-log.md` = 0 hits) |
| `41ff827` | 11-01 | ui: the fan mode goes through Core's set_fan_mode | `SystemActionBridge.cpp` | "pi (apertar.local) build only" | `:240` "builds on the Pi, not tried by hand" |
| `68e1a41` | 11-01 | qml: the dropped-frames chip shows the number of dropped frames | `ApertarControlBridge.hpp` | "desk only (needs Core's recording_dropped_frames)" | `:241` "on GitHub drop-frames and the Pi" |
| `c234d77` | 11-01 | ui: APERTAR_UI_PREVIEW_RECORDING_FPS caps the live preview while a take runs | `ApertarPreviewSocketClient.{cpp,hpp}`, `main.cpp` | "desk only" | `:242`. Used on the Pi with `=12` and `=0` (`lessons/hardware-log.md:992-993`) |
| `c13b846` | 11-01 | ui: APERTAR_PREVIEW_PLANE (DRM primary plane) | `CMakeLists.txt` (+5), `main.cpp` (+6) | "desk only" | `:246` reverted |
| `010f8ad` | 11-02 | ui: drop APERTAR_PREVIEW_PLANE | `CMakeLists.txt` (-5), `main.cpp` (-6) | "desk only (revert)" | `:247`. Net effect in scope: none |

Fork-log note for the UI port as a whole: several rows say "not tried on a touch screen (none on the rig)"
(`fork-log.md:205-209`). The rig runs `hdmi_external_only=true` (`lessons/hardware-log.md:995`).

## 2. Features that touch the unit

| # | Feature | What the operator gets | Commits | Scope lines `@port` | Relation to upstream |
| --- | --- | --- | --- | --- | --- |
| F1 | Media state from Core | A pulled card reads as not mounted at once (pill "NO MEDIA") instead of staying READY | `160898c` | `ApertarControlBridge.hpp:267-268`, `:371`, `:455-456`; `MediaStatusBridge.hpp:41-43`, `:139-141`; `MediaStatusBridge.cpp:288-296`, `:1245-1257`; `main.cpp:318-319` | Extends `MediaStatusBridge::updateStatus` in place; adds a bridge-to-bridge signal wired in `main.cpp` |
| F2 | Automounter releases a pulled card | A CFexpress card pulled while mounted is unmounted and its PCIe device removed, so re-inserting mounts it without a reboot | `dc471c1` | `CfeAutomounter.cpp:549-550`, `:714-717`, `:726-761` | Extends the upstream loop in place; two new private methods; the PCIe remove moves out of `unmountPcie` |
| F3 | Speed-ramp aware FPS picker | In a ramp take the FPS picker changes only the rate; Core keeps the shutter policy | `ec9f109` | `ApertarControlBridge.hpp:435-436` (members only; logic in `ApertarControlBridge.cpp:275-280`) | Extends `applyFps` in place |
| F4 | Values the camera sets | ISO / WB show the value in use while auto; held and capped values are marked; ISO "Lock" | `f1edf96` (colour and italics changed later in QML: `7840438`, `35b31f6`) | `ApertarControlBridge.hpp:18-19`, `:23-27`, `:104`, `:108-112`, `:228`, `:437-440`, `:444-448` | Extends the property block in place |
| F5 | Value lists (T33) | FPS / ISO / shutter / WB pickers follow lists stored in `UI.conf`; values above the ceiling are greyed | `ed0d7b5` | `SettingsBridge.hpp:95-101`, `:313-318`, `:409`, `:430`, `:524-529`; `SettingsBridge.cpp:412`, `:586`, `:1767-1796`; `ApertarControlBridge.hpp:20`, `:105`, `:441` | Extends the constructor and `pollExternalSettings` in place; one new private method |
| F6 | Mode Ladder awareness | The Compression field is disabled while the ladder is active | `c716dec` | `ApertarControlBridge.hpp:22`, `:106`, `:442` | Extends the property block in place |
| F7 | Recording frame and red timecode switches | Two switches in Settings > Monitoring: a red frame during a take (default off), red timecode during a take (default on) | `da2a9b5` | `SettingsBridge.hpp:52-53`, `:55`, `:200-201`, `:204-205`, `:369`, `:371`, `:482`, `:484`; `SettingsBridge.cpp:368`, `:370`, `:552`, `:554`, `:1150-1165`, `:1184-1199`, `:2170`, `:2172`, `:2262`, `:2264` | Extends in place, same shape as `dateTimeOverlayEnabled` (`SettingsBridge.cpp:367`, `:546`, `:1123-1138`, `:2060`, `:2148@up`) |
| F8 | UI timecode and file timecode | Settings > Timecode has two choices; the tap on the camera screen changes the on-screen timecode only | `7029db1` | `ApertarControlBridge.hpp:21`, `:107`, `:202-203`, `:245`, `:443` | Changes the signature of an upstream invokable |
| F9 | No default hardware file from the UI | The touch UI no longer creates `/home/pi/apertar-hardware.conf` | `c9d841f` | `DisplayConfigBridge.cpp` (-292 here), `Ina219Bridge.cpp` (-280) | Removes upstream code |
| F10 | HDMI 1080p display fallback | With no file, no `[display]` section or no `hdmi_external_only` key the UI runs as 1920x1080 `landscape_large` with the touch window hidden | `7c41a27` | `DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357`; `DisplayConfigBridge.hpp:52-54`, `:59` | Changes defaults inside upstream code |
| F11 | Controls status | A "Controls: N errors" chip on the camera page and a read-only Controls card in Settings > Info | `ea44bd7` | `ApertarControlBridge.hpp:82-84`, `:163-164`, `:265`, `:451-453`; `CMakeLists.txt:41` | Extends the property block; one new QML file in the build list |
| F12 | Write buffer | Buffer bar in the REC pill, safety-stop dialog, Frames / RAM choice | `841d0ed` (+ `4959513`, `96a7aa4` in QML) | `ApertarControlBridge.hpp:62-64`, `:70-72`, `:143-145`, `:151-153`, `:194`, `:251-253`, `:259-261`, `:277`, `:363`, `:413-414`, `:420-423`; `SettingsBridge.hpp:54`, `:202-203`, `:370`, `:483`; `SettingsBridge.cpp:369`, `:553`, `:1167-1182`, `:2171`, `:2263` | Extends in place; new invokable, new non-NOTIFY signal |
| F13 | Log (cDNG log encoding) | Log On / Off in Settings > Record; "Log" in the format line | `841d0ed` | `ApertarControlBridge.hpp:77-81`, `:158-162`, `:200`, `:262`, `:365`, `:424-429` | Extends in place; new invokable |
| F14 | Storage pre-roll | Blue PRE-ROLL pill while Core runs it; a button and an auto switch in the Media Speed card | `841d0ed` | `ApertarControlBridge.hpp:65-69`, `:146-150`, `:195-196`, `:254-258`, `:415-419` | Extends in place; two new invokables |
| F15 | Clip names | Clip Names card in Settings > Record with a live preview of the next name | `606f137` | `ApertarControlBridge.hpp:73-76`, `:154-157`, `:197-198`, `:263-264`, `:301`, `:430-434`; `CMakeLists.txt:51-52`; `qml.qrc:32-33` | Extends in place; two new invokables; two new QML files |
| F16 | Audio recording outline | A switch for the red outline on the audio meter while sound is recorded (default on) | `5697b54` | `SettingsBridge.hpp:56`, `:206-207`, `:372`, `:485`; `SettingsBridge.cpp:371`, `:555`, `:1201-1216`, `:2173`, `:2265` | Extends in place, same shape as F7 |
| F17 | Fan mode through Core | Same three fan modes; the change now needs a connected Core | `41ff827` | `SystemActionBridge.cpp:14-16`, `:65-97`, `:404-409` | Replaces the UI's own writer with a call to an upstream Core command; adds a second copy of `coreMediaCommand` |
| F18 | Dropped-frames count | The dropped-frames chip shows the number | `68e1a41` | `ApertarControlBridge.hpp:61`, `:142`, `:364`, `:450` | Extends in place |
| F19 | Preview cap while recording | Nothing by default. With the env var set, the touch UI draws fewer preview frames during a take | `c234d77` | `ApertarPreviewSocketClient.hpp:4`, `:35-36`, `:95-98`; `ApertarPreviewSocketClient.cpp:25-43`, `:488-498`; `main.cpp:351-352` | Adds a parallel path beside upstream code, off unless the env var is set |
| - | DRM plane preview | Nothing (added, then reverted) | `c13b846`, `010f8ad` | none left | Net zero |

## 3. Interfaces added or changed

### 3.1 Socket commands sent

Sender lines are in `src/ApertarControlBridge.cpp@port` unless a file is named. "Upstream Core" = a
`command.name == "..."` branch in `ApertarCoreApp.cpp@up`. All **confirmed**.

| Command | Arguments | Sender `@port` | Core handler `@port` | In upstream Core | Feature |
| --- | --- | --- | --- | --- | --- |
| `set_fan_mode` | `value` = `Silent` / `Auto` / `Full Blast` | `SystemActionBridge.cpp:76` (own socket, id `42002`, 8 s) | `ApertarCoreApp.cpp:14592` | yes, `:10568@up`. First use from the touch UI | F17 |
| `set_timecode_mode` | `value`; new `target` = `ui` / `files` / `both` | `:758-759` | `:13279` | command yes (`:9424@up`); `target` is new | F8 |
| `set_iso_auto` | new `enabled=false` (Lock) | `:304` | `:12995` | command yes (`:9269@up`); `enabled` is new | F4 |
| `set_buffer_mode` | `value` = `frames` / `ram` | `:692` | `:12829` | no | F12 |
| `set_cdng_log` | `value` = `auto` / `off` | `:718` | `:13079` | no | F13 |
| `storage_preroll` | none | `:621` | `:14603` | no | F14 |
| `set_storage_preroll` | `value` = `on` / `off` | `:627` | `:12900` | no | F14 |
| `set_clip_name_template` | `value` | `:637` | `:13241` | no | F15 |
| `preview_clip_name` | `value` | `:648` | `:13258` | no | F15 |
| `set_fps` | unchanged; the follow-up `set_shutter_us` is skipped in a ramp take | `:272-280` | `:13003` | yes | F3 |

No HTTP route is used by this unit.

### 3.2 Events consumed

| Event | Fields read | Reader `ApertarControlBridge.cpp@port` | Emitted by Core `@port` | In upstream Core | Feature |
| --- | --- | --- | --- | --- | --- |
| `media` | `state`, `mounted` | `:1336-1339` | `ApertarCoreApp.cpp:10827` | no | F1 |
| `buffer` | the `buffer_*` and `storage_preroll_*` fields, `recording_dropped_frames` | `:1345-1348` | `:10841` | no | F12, F14, F18 |
| `controls` | `errors`, `warnings` | `:1332-1334` | `:12346` | no | F11 |
| `recording` | new read: `sound_only` with `active` | `:1351-1357` | upstream event | yes | F3 |

### 3.3 Core state fields read (get_state, command replies, `settings` event)

| Field | Property or member | Reader `ApertarControlBridge.cpp@port` | In upstream Core | Feature |
| --- | --- | --- | --- | --- |
| `media_state`, `media_alive` | `coreMediaStateChanged(state, alive)` | `:1440-1442` | no | F1 |
| `fps_speed_ramp` | `m_fpsSpeedRamp` | `:1511-1512` | no | F3 |
| `sound_recording` | `m_soundRecording` | `:1514-1515` | yes (field exists `@up`; the UI did not read it) | F3 |
| `iso_max` | `isoMax` | `:1591-1592` | no | F4 |
| `iso_actual` | `isoInUse` | `:1602-1603` | no | F4 |
| `wb_actual_kelvin`, `wb_measured` | `whiteBalanceInUse` | `:1604-1607` | yes (fields exist `@up`; the UI did not read them) | F4 |
| `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` | `isoSetByCamera`, `whiteBalanceSetByCamera` | `:1595-1598`, `:1608-1609` | no | F4 |
| `fps_speed_ramp_keep_exposure` | `shutterSetByCamera` (with `recording` and `fps_speed_ramp`) | `:1599-1600`, `:1610` | no | F4 |
| `fps_max` | `fpsMax` | `:1593-1594` | no | F5 |
| `ladder_active` | `ladderActive` | `:1589-1590` | no | F6 |
| `timecode_mode` | `fileTimecodeMode`. Upstream wrote `UI.conf` `timecodeMode` from it (`:1466-1473@up`) | `:1698-1706` | yes | F8 |
| `controls_errors`, `controls_warnings` | `controlsErrors`, `controlsWarnings` | `:1439` | no | F11 |
| `buffer_mode`, `buffer_setting`, `buffer_note`, `buffer_fill`, `buffer_stop_percent`, `buffer_safety_stop` | `bufferMode`, `bufferSetting`, `bufferNote`, `bufferFill`, `bufferStopPercent`, `bufferSafetyStop` | `:2667-2725` | no | F12 |
| `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` | `cdngLogOn`, `cdngLogBits`, `cdngLogAvailable`, `cdngLogApplied`, `cdngLogActive` | `:2769-2801` | no | F13 |
| `storage_preroll_active`, `storage_preroll_auto`, `storage_preroll_fps`, `storage_preroll_last` | `storagePrerollActive`, `storagePrerollAuto` (+ `storagePrerollAutoKnown`), `storagePrerollFps`, `storagePrerollLast` | `:2726-2766` | no | F14 |
| `clip_name_template`, `clip_name_example`; reply field `example` | `clipNameTemplate` (+ `clipNameKnown`), `clipNameExample`, `clipNamePreview` | `:660-684`, `:653-657` | no | F15 |
| `recording_dropped_frames` | `recordingDroppedFrames` | `:2652-2662` | no | F18 |

### 3.4 `ApertarControlBridge.hpp`: counts

| Item | `@up` | `@main` | `@port` | Added by the port |
| --- | --- | --- | --- | --- |
| `Q_PROPERTY` | 43 | 44 | 76 | 32, all read-only with NOTIFY |
| Signals | 42 | 43 | 62 | 19 |
| `Q_INVOKABLE` | 35 | 36 | 42 | 6 new, 1 changed signature |
| Private methods | - | - | - | 6: `applyClipNameState` `:301`, `applyBufferState` `:363`, `applyRecordingDroppedFrames` `:364`, `applyCdngLogState` `:365`, `setCoreMediaState` `:371`, `setControlsStatus` `:453` |
| Members | - | - | - | 39 (inside `:413-456`) |

| New or changed invokable `@port` | Returns | Note |
| --- | --- | --- |
| `applyBufferMode(QString)` `:194` | `void` | |
| `applyStoragePreroll()` `:195` | `void` | |
| `applyStoragePrerollAuto(bool)` `:196` | `void` | |
| `applyClipNameTemplate(QString)` `:197` | `void` | |
| `requestClipNamePreview(QString)` `:198` | `void` | |
| `applyCdngLog(bool)` `:200` | `void` | |
| `applyTimecodeMode(QString, QString target)` `:203` | `bool` | was `applyTimecodeMode(QString)` (`:127@up`). No default for `target` |

Fact: every upstream `apply*` invokable returns `bool` (`ApertarControlBridge.hpp:111-141@up`); the only `void`
invokables upstream are `notifyUserActivity` `:100` and `refresh` `:110`. **confirmed**

NOTIFY grouping: `cameraSetValuesChanged` serves 8 properties, `cdngLogChanged` 5, `clipNameChanged` 3,
`controlsStatusChanged` 2. Upstream precedent for a shared NOTIFY: `recordingCapabilitiesChanged` serves 6
(`ApertarControlBridge.hpp:34-39@up`). **confirmed**

Other bridge headers:

| Header | `Q_PROPERTY` `@up` | `@port` | Added |
| --- | --- | --- | --- |
| `SettingsBridge.hpp` | 71 | 81 | 4 READ + WRITE switches (`:53-56`), 6 read-only value-list properties sharing `valueStepsChanged` (`:96-101`) |
| `MediaStatusBridge.hpp` | 21 | 21 | none; one public method `setCoreMediaState` (`:43`) |
| `DisplayConfigBridge.hpp` | 15 | 15 | none; four member defaults changed |
| `ApertarPreviewSocketClient.hpp` | 3 | 3 | none; one public method `setRecording` (`:36`) |

### 3.5 Config keys

| File | Key | Access by this unit | Default | Where `@port` | Feature |
| --- | --- | --- | --- | --- | --- |
| `UI.conf` `[General]` | `recordingFrameEnabled` | read + write | `false` | `SettingsBridge.cpp:368`, `:1161` | F7 |
| `UI.conf` `[General]` | `recordingRedTimecodeEnabled` | read + write | `true` | `:370`, `:1195` | F7 |
| `UI.conf` `[General]` | `frameBufferBarEnabled` | read + write | `false` | `:369`, `:1178` | F12 |
| `UI.conf` `[General]` | `audioRecordedOutlineEnabled` | read + write | `true` | `:371`, `:1212` | F16 |
| `UI.conf` `[General]` | `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps` | read only (Core's `set_value_steps` writes them) | empty = built-in list | `:1780-1783` | F5 |
| `UI.conf` `[General]` | `flickerFreeShutterAngles` | read only | `false` | `:1784` | F5 |
| `UI.conf` `[General]` | `mainsHz` | read only | `50` (only `60` is the other value) | `:1785` | F5 |
| `UI.conf` `[General]` | `timecodeMode` (upstream key) | written by `applyTimecodeMode` only when `target != files`; no longer written from Core's `timecode_mode` | - | `ApertarControlBridge.cpp:762-765`, `:1698-1706` | F8 |
| Preset JSON (UI part) | `recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled` | serialised and applied | - | `SettingsBridge.cpp:2170-2173`, `:2262-2265` | F7, F12, F16 |
| `apertar-hardware.conf` `[display]` | `ui_width`, `ui_height` | fallback 720 -> 1920, 720 -> 1080 | | `DisplayConfigBridge.cpp:11-12` | F10 |
| `apertar-hardware.conf` `[display]` | `ui_layout` | start value `square` -> `landscape_large`; with a file the layout is still derived from the size when the key is absent (`:320-326`) | | `:289` | F10 |
| `apertar-hardware.conf` `[display]` | `hdmi_external_only` | fallback `false` -> `true` (start value and missing-key fallback) | | `:294`, `:354-357` | F10 |
| `apertar-hardware.conf` | the whole default template | no longer written by the UI | | removed | F9 |
| `/boot/firmware/config.txt` | `# BEGIN/END APERTAR FAN MODE` block | read only now (`refreshFanMode`, `SystemActionBridge.cpp:605-615`); the write went to Core | | `:404-409` | F17 |

The four value-list keys and the two flicker keys are not written into presets by this unit. **confirmed**
(`SettingsBridge.cpp:2170-2173` adds only the four switches.)

Core side of the four switches, for reference: `handleUiToggle("set_recording_frame_enabled", ...)` and three
siblings (`ApertarCoreApp.cpp:13505-13511@port`). The touch UI does not send them; it writes `UI.conf`.

### 3.6 Environment variables

| Variable | Read at `@port` | Meaning | Upstream |
| --- | --- | --- | --- |
| `APERTAR_UI_PREVIEW_RECORDING_FPS` | `ApertarPreviewSocketClient.cpp:29` | `N` = at most N preview frames a second reach the renderer while a take runs; `0` = hold the last frame; unset = every frame | new. The only env var the UI port reads in addition (17 names read `@port`, 16 `@up`). `APERTAR_WEB_PREVIEW_RECORDING_FPS` appears in a comment only (`:26`) |
| `APERTAR_CONTROL_SOCKET` | new read site `SystemActionBridge.cpp:71` | socket path for `set_fan_mode` | existing (4 read sites `@up`, 5 `@port`) |

### 3.7 Files on disk

| File | Change | Where |
| --- | --- | --- |
| `/home/pi/apertar-hardware.conf` | The UI no longer creates it (section 5) | `DisplayConfigBridge.cpp`, `Ina219Bridge.cpp` |
| `/boot/firmware/config.txt` | The UI no longer writes it (no temp file, no `sudo -n install`) | `SystemActionBridge.cpp:392-413@port` vs `:419-480@up` |
| `/media/RAW` mount | Lazy unmount (`umount2(..., MNT_DETACH)`) on a pull | `CfeAutomounter.cpp:737@port` |
| `/sys/bus/pci/devices/<addr>/remove` | Now also written on a pull, not only on eject | `CfeAutomounter.cpp:755-757@port` |
| `/usr/local/libexec/apertar-cfe-automounter` | Installed copy must be replaced by hand; a build does not update it (`llm/README.md:124`). On the Pi it was replaced, backup `.bak-1.6.0` (`architecture/ui.md:459`). **unconfirmed** here: `ls -l /usr/local/libexec/apertar-cfe-automounter*` on the Pi | |
| `qml/ControlsWarning.qml`, `qml/ClipNameCard.qml`, `qml/ClipNamePill.qml` | New files registered in the build lists (their content belongs to the QML unit) | `CMakeLists.txt:41`, `:51-52`; `qml.qrc:32-33` |

### 3.8 UI elements bound to this unit's new members

QML is another unit. These are the anchors that read or call the members above, `@port`.

| Element | Where | Bridge member |
| --- | --- | --- |
| Settings > Monitoring rows "Recording Frame", "Frame Buffer Bar", "Red Timecode", "Audio Recording Outline" | `SettingsPage.qml:2937`, `:2955`, `:2973`, `:2991` | `settingsBridge.recordingFrameEnabled`, `.frameBufferBarEnabled`, `.recordingRedTimecodeEnabled`, `.audioRecordedOutlineEnabled` |
| Red frame, red timecode, audio meter outline | `CameraPage.qml:4347`, `:3924`, `:3897`, `:4094`; `ExternalMonitorWindow.qml:1434`, `:1208`, `:994` | same |
| Compression field disabled, "(set by Mode Ladder)" | `SettingsPage.qml:3398`, `:3409` | `ladderActive` |
| "Write Buffer" Frames / RAM tiles and note | `SettingsPage.qml:3417-3460` | `bufferSetting`, `bufferMode`, `bufferNote`, `applyBufferMode` |
| "Log" On / Off tile and note | `SettingsPage.qml:3462-3492` | `cdngLogAvailable`, `cdngLogOn`, `cdngLogApplied`, `cdngLogBits`, `applyCdngLog` |
| Timecode card: "UI timecode", "File timecode" | `SettingsPage.qml:3990-4026` | `applyTimecodeMode(v, "ui")` `:4011`, `applyTimecodeMode(v, "files")` `:4026`, `fileTimecodeMode` `:4018` |
| Tap on the timecode box | `CameraPage.qml:1842` | `applyTimecodeMode(nextMode, "ui")` |
| "Clip Names" card | `SettingsPage.qml:4037`, gate `:2031`; `ClipNameCard.qml:52-516` | `clipNameKnown`, `clipNameTemplate`, `clipNameExample`, `clipNamePreview`, `applyClipNameTemplate` `:169`, `requestClipNamePreview` `:335` |
| "Storage Pre-roll" button, auto switch, last result | `SettingsPage.qml:5601-5663` | `applyStoragePreroll` `:5605`, `storagePrerollAutoKnown` `:5611`, `applyStoragePrerollAuto` `:5628`, `:5635`, `storagePrerollLast` |
| "Thermal" card (fan mode) | `SettingsPage.qml:5678`, `:5725`, `:1793-1803` | `systemActionBridge.applyFanMode`. QML unchanged by the port |
| Settings > Info "Controls" card | `SettingsPage.qml:6456-6476` | `controlsErrors`, `controlsWarnings` |
| "Controls: N errors" chip | `CameraPage.qml:2711-2721` (`ControlsWarning`) | `controlsErrors` |
| Dropped-frames chip with a number | `CameraPage.qml:2723-2733`; `ExternalMonitorWindow.qml:1185` | `recordingDroppedFrames` |
| Buffer bar, drain state, PRE-ROLL pill | `CameraPage.qml:2704-2708`; `StatusChip.qml:102`; `ExternalMonitorWindow.qml:1106-1122` | `bufferFill`, `bufferMode`, `bufferSafetyStop`, `storagePrerollActive` |
| "Recording Stopped" dialog after a safety stop | `CameraPage.qml:1964-1967` | signal `bufferSafetyStopped(message)` |
| Pre-roll fps shown in place of the operator's fps | `CameraPage.qml:3057-3059`; `ExternalMonitorWindow.qml:96-98` | `storagePrerollFps` |
| ISO / WB value in use, camera-set marks | `CameraPage.qml:3092-3093`, `:3126`, `:3167-3168`; `ExternalMonitorWindow.qml:103-116`, `:204-206` | `isoInUse`, `whiteBalanceInUse`, `isoSetByCamera`, `shutterSetByCamera`, `whiteBalanceSetByCamera` |
| Picker lists and ceilings | `CameraPage.qml:526-540`, `:891-894`, `:905-906`, `:924` | `isoMax`, `fpsMax`, `settingsBridge.isoSteps`, `.wbSteps`, `.shutterAngleSteps`, `.fpsSteps`, `.flickerFreeShutterAngles`, `.mainsHz` |
| "Log" in the format display, minutes left | `CameraPage.qml:558`, `:1014-1015`; `ExternalMonitorWindow.qml:145` | `cdngLogActive`, `cdngLogBits` |

## 4. Original code that was modified

Line refs: old side `@up` (= `@main` for every file but the control bridge header), new side `@port`.
Kinds: extended-in-place, rewritten, removed, moved, behaviour-changed. All **confirmed**.

| # | Region | Old `@up` | New `@port` | Change | Kind | Commit |
| --- | --- | --- | --- | --- | --- | --- |
| U1 | `DisplayConfigBridge.cpp` includes | `:3`, `:5`, `:8` | gone | `QDir`, `QSaveFile`, `QTextStream` removed with the writer | removed | `c9d841f` |
| U2 | `ensureDefaultHardwareConfigFile()` in `DisplayConfigBridge.cpp` | `:41-326` | gone | The 286-line template writer removed | removed | `c9d841f` (extended by `f1edf96` first: `[camera]` section, +6 lines) |
| U3 | `DisplayConfigBridge::loadConfiguration`, the call | `:587` | gone | `ensureDefaultHardwareConfigFile();` removed | removed | `c9d841f` |
| U4 | `kDefaultUiWidth` / `kDefaultUiHeight` | `:14-15` (720, 720) | `:11-12` (1920, 1080) | Fallback size | behaviour-changed | `7c41a27` |
| U5 | `loadConfiguration` start values | `:579` `"square"`, `:584` `false` | `:289` `"landscape_large"`, `:294` `true` | Values used when no file is found | behaviour-changed | `7c41a27` |
| U6 | `readConfigBool(... "hdmi_external_only" ..., false)` | `:646-649` | `:354-357` (`true`) | Fallback when a file exists but has no such key | behaviour-changed | `7c41a27` |
| U7 | `DisplayConfigBridge.hpp` member defaults | `:52-54`, `:59` | `:52-54`, `:59` | 720 / 720 / `square` / `false` -> 1920 / 1080 / `landscape_large` / `true` | behaviour-changed | `7c41a27` |
| U8 | `Ina219Bridge.cpp` includes | `:3`, `:6`, `:8` | gone | `QDir`, `QSaveFile`, `QTextStream` removed | removed | `c9d841f` |
| U9 | `ensureDefaultHardwareConfigFile()` in `Ina219Bridge.cpp` | `:69-342` | gone | The second template writer removed | removed | `c9d841f` |
| U10 | `Ina219Bridge::loadConfiguration`, the call | `:497` | gone | removed | removed | `c9d841f` |
| U11 | `SystemActionBridge.cpp` includes | `:12` `<cstring>`, `:18` `<QTemporaryFile>` | `:14-16` add `QJsonDocument`, `QJsonObject`, `QLocalSocket` | | extended-in-place | `41ff827` |
| U12 | `fanModeBlock()` | `:64-104` | gone | The fan `dtparam` block builder removed. The same text is in Core (`ApertarCoreApp.cpp:3042@up`, `:3425-3464@port`, values identical) | removed | `41ff827` |
| U13 | `stripManagedFanBlock()` | `:106-124` | gone | removed | removed | `41ff827` |
| U14 | `SystemActionBridge::applyFanMode` write path | `:431-476` (read config.txt, rebuild, temp file, `sudo -n install -m 644`) | `:404-409` (`coreFanModeCommand`) | The write goes to Core's `set_fan_mode`. Validation of the mode name and `setFanMode()` stay | rewritten | `41ff827` |
| U15 | `Automounter::run` loop | `:544-553` | `:544-555` | New edge: `!lastInsert && insert && m_mounted` -> `handleSurpriseRemoval()` | extended-in-place | `dc471c1` |
| U16 | `Automounter::unmountPcie`, PCIe remove | `:712-723` inline | `:714-717` calls `removePcieDevice(device)` (`:748-761`) | Same steps, now a method shared with the pull path | moved | `dc471c1` |
| U17 | `MediaStatusBridge::updateStatus` | `:1232-1234` | `:1242-1257` | Early return before `QStorageInfo` when Core says `removed` or `error` and not alive | extended-in-place | `160898c` |
| U18 | `MediaStatusBridge` API | `.hpp:40` | `.hpp:41-43`, `.cpp:288-296` | New public slot-like method `setCoreMediaState` | extended-in-place | `160898c` |
| U19 | `main.cpp` bridge wiring | after `:317` | `:318-319` | `coreMediaStateChanged` -> `mediaBridge.setCoreMediaState` (normal mode only) | extended-in-place | `160898c` |
| U20 | `main.cpp` bridge wiring | after `:348` | `:351-352` | `recordingChanged` -> `apertarPreviewBridge.setRecording` (normal mode only) | extended-in-place | `c234d77` |
| U21 | `ApertarPreviewSocketClient` constructor | `:24` | `:25-35` | Reads `APERTAR_UI_PREVIEW_RECORDING_FPS`, logs it | extended-in-place | `c234d77` |
| U22 | `ApertarPreviewSocketClient::handlePreviewFrame` | `:453-470` | `:488-498` | Drops a frame over the cap before the slot lookup and before `emit frameArrived()` | extended-in-place (behaviour change only with the env var set) | `c234d77` |
| U23 | `SettingsBridge` constructor key load | `:367` | `:368-371`, `:412` | Four keys loaded; `reloadValueSteps()` | extended-in-place | `da2a9b5`, `841d0ed`, `5697b54`, `ed0d7b5` |
| U24 | `SettingsBridge::pollExternalSettings` | `:546`, `:576` | `:552-555`, `:586` | Four keys re-read; `reloadValueSteps()` | extended-in-place | same |
| U25 | `SettingsBridge::serializeCurrentSettings` / `applySettingsObject` | `:2060`, `:2148` | `:2170-2173`, `:2262-2265` | Four keys in the preset | extended-in-place | `da2a9b5`, `841d0ed`, `5697b54` |
| U26 | `ApertarControlBridge::applyTimecodeMode` signature | `.hpp:127` one argument | `.hpp:203` two arguments | The one-argument form no longer exists. Both QML callers pass a target | behaviour-changed | `7029db1` |
| U27 | `ApertarControlBridge.hpp` property, public, signal and private blocks | `:16-58`, `:60-144`, `:145-193`, `:194-326` | `:16-93`, `:95-220`, `:221-290`, `:291-472` | 32 properties, 19 signals, 6 invokables, 6 private methods, 39 members added | extended-in-place | 10 commits (section 1) |
| U28 | `CMakeLists.txt` `APERTAR_QML_FILES` | `:19-52` | `:19-55` | +3 entries | extended-in-place | `ea44bd7`, `606f137` |
| U29 | `qml.qrc` | 31 entries | 33 entries | +2 entries (`ControlsWarning.qml` is not added) | extended-in-place | `606f137` |

## 5. What went from `DisplayConfigBridge.cpp` (-297) and `Ina219Bridge.cpp` (-280)

### 5.1 The lines

| File | Lines removed | What |
| --- | --- | --- |
| `DisplayConfigBridge.cpp` | 3 | includes `QDir`, `QSaveFile`, `QTextStream` |
| | 287 | `ensureDefaultHardwareConfigFile()` (`:41-326@up` plus a blank line): creates `/home/pi/apertar-hardware.conf` from a built-in template if the file does not exist |
| | 2 | the call in `loadConfiguration` (`:587@up`) |
| | 5 | five default lines replaced (U4-U6); +5 on the other side |
| `Ina219Bridge.cpp` | 3 | the same three includes |
| | 275 | a second `ensureDefaultHardwareConfigFile()` (`:69-342@up`) with its own template |
| | 2 | the call in `loadConfiguration` (`:497@up`) |

### 5.2 The two templates (`@up`)

| Section | `DisplayConfigBridge` template | `Ina219Bridge` template |
| --- | --- | --- |
| `[network] hotspot_delay_seconds=60` | yes | no |
| `[run_script] path=` .. `path5=` | yes | no |
| `[ina219] enabled=true bus=4 address=0x40` | yes | yes |
| `[pcf8574] enabled=false bus=1 address=0x20 ... pin0..pin7=none`, with the list of action names as comments | yes | yes |
| `[trigger_output] ... gpiochip=auto line=17 ...` | yes (`:101-116`, chip `:110`) | yes (chip `:129`) |
| `[recording_indicator] ... gpiochip=auto line=17 ...` | yes (chip `:123`) | yes (chip `:142`) |
| `[neorotary4] enabled=false bus=1 address=0x49 ... encoder0..3 actions` | yes | yes |
| `[gpio_buttons] enabled=false chip=auto ... d5=capture d6=eject` | yes (`:156-167`, chip `:161`) | yes (chip `:180`) |
| `[gpio_encoders] enabled=false chip=auto ... encoder0_a=5 encoder0_b=6 ...` | yes (chip `:172`) | yes (chip `:191`) |
| `[grove_analog] enabled=false bus=1 address=0x04 ...` | yes | yes |
| `[imu] enabled=true driver=mpu6050 sync_mode=free_run sync_offset_ms=0` | yes | yes |
| `[mpu6050] enabled=true bus=1 address=0x68 ...`, `[bmi160]`, `[bmi270]`, `[icm42688p]` | yes | yes |
| `[cfexpress_hat] enabled=true bus=10 address=0x34` | yes (`:299`) | yes (`:318`) |
| `[storage] mount_path=/media/RAW pcie_controller=1000110000.pcie` | yes (`:303`) | yes (`:322`) |
| `[display] ui_width=720 ui_height=720 ui_layout=square ui_rotation=normal controls_opacity=1.0 windowed=false hdmi_external_only=false` | yes (`:314-323`), plus `zoom_toggle_factor=4.0` | yes (`:333-339`), no `zoom_toggle_factor` |

### 5.3 Behaviours of original Apertar that went with it

| # | Upstream behaviour | Evidence `@up` | At the port | Label |
| --- | --- | --- | --- | --- |
| B1 | The UI creates `/home/pi/apertar-hardware.conf` at start when it is missing. It is the only automatic creator: upstream Core uses its own template only as the text the WebUI Config editor shows for a missing file (`Core:ApertarCoreApp.cpp:5297@up`), and neither repo ships the file | `DisplayConfigBridge.cpp:41-58`, `:587`; `Ina219Bridge.cpp:69-86`, `:497`; `main.cpp:278`, `:298`, `:133` (monitor-only too) | Nothing creates the file at start. Core's store does not create it either (`Core:hardware/HardwareConfigStore.hpp:76@port`: `currentText()` is `""` when absent; the template is used only for the editor, `Core:ApertarCoreApp.cpp:6188-6202@port`) | **confirmed** |
| B2 | A deleted or moved file comes back as the full template at the next UI start | same | It stays missing. Core offers a restore of the last version it knew (`get_controls` `replaced`, `set_controls restore=true`, `fork-log.md:112`) | **confirmed** for the UI side |
| B3 | The file on disk documents every section, the action names and example pins for someone editing by hand | template text, 5.2 | Not on disk until a save through the WebUI. The WebUI editor shows Core's template (or a `/boot` copy) for a missing file (`Core:ApertarCoreApp.cpp:6188-6202@port`). Core's template is shorter (no pin lists, no `[gpio_buttons]` keys) | **confirmed** |
| B4 | First start shows the touch UI as 720x720 `square` on the main screen | `DisplayConfigBridge.cpp:314-323`, `:14-15`, `:579`, `:584`; `main.cpp:428-459` | First start (no file) is 1920x1080 `landscape_large` with the main window hidden (`main.cpp:432-433@port`). The monitor window (`ExternalMonitorWindow.qml`, no touch controls) takes the first HDMI screen, else the primary screen (`ExternalMonitorManager.cpp:128-141@port`) | **confirmed** in code, not seen on hardware |
| B5 | `/boot/firmware/apertar-hardware.conf` and `/boot/apertar-hardware.conf` are dead after the first UI start (`llm/README.md:125`) | candidates `DisplayConfigBridge.cpp:25-39` | Both stay live for as long as `/home/pi/apertar-hardware.conf` is absent. The candidate list is unchanged (`:22-36@port`) | **confirmed** |
| B6 | Readers other than the display see the same values with or without the file: the built-in defaults equal the template for INA219 (`Ina219Bridge.cpp:45-46`: bus 4, 0x40, enabled), the automounter (`CfeAutomounter.cpp:38-39`, `:109-110`: bus 10, 0x34, `/media/RAW`, `1000110000.pcie`) and Core's `enabled` flags (IMU `true`, the rest `false`, `Core:hardware/*.hpp`) | | So `c9d841f` alone changes no reader default. `7c41a27` is what changes the display. Other keys were not compared one by one | **probable** (enabled flags and the listed defaults read; the rest: `diff` each reader's defaults against 5.2) |
| B7 | `Ina219Bridge` logs "using defaults in /home/pi/apertar-hardware.conf" only when creating the file failed | `Ina219Bridge.cpp:542-547` | Logged on every start without a file; the path names a file that does not exist (`Ina219Bridge.cpp:262-267@port`) | **confirmed** |

Adjacent fact, outside the scope: `GyroConfigBridge::writeConfigValue` still writes the hardware file from the
UI with `QSaveFile`, and creates a stub (`# Apertar hardware configuration` plus the one section) when the file is
missing (`src/GyroConfigBridge.cpp:1577-1650`, `:363-389@port`; file unchanged by the port). So "the UI no longer
writes the file" holds for the default template only. **confirmed**

## 6. New abstractions

| Name | Kind | Where `@port` | Purpose | Used by | What upstream uses for the same job |
| --- | --- | --- | --- | --- | --- |
| `coreFanModeCommand()` | file-local function | `SystemActionBridge.cpp:65-97` | One synchronous request to Core on its own `QLocalSocket`, fixed id `42002`, 1 s connect, 8 s reply | `applyFanMode` `:406` | `coreMediaCommand()` in `MediaStatusBridge.cpp:20-43@up` (fixed id `42001`, same loop; the port's function is a near copy). Also `ApertarControlBridge::sendCoreCommand` (`ApertarControlBridge.cpp:1013-1106@up`) and the async socket in `AudioDeviceBridge.cpp:327-347@up` |
| `ApertarControlBridge::coreMediaStateChanged` + `MediaStatusBridge::setCoreMediaState` | signal + method, connected in `main.cpp` | `ApertarControlBridge.hpp:268`; `MediaStatusBridge.cpp:288-296`; `main.cpp:318-319` | Core's media watcher state overrides the mount-table poll | F1 | Bridge-to-bridge connects in `main.cpp`, e.g. `externalRecordingPreparationRequested` -> `AudioMeterBridge::releaseInputForRecording` (`main.cpp:324-327@up`), `standbyChanged` -> `mediaBridge.setStandby` (`:335-342@up`) |
| `ApertarPreviewSocketClient::setRecording` + frame throttle | method + 4 members + env knob | `ApertarPreviewSocketClient.cpp:25-43`, `:488-498`; `.hpp:36`, `:95-98` | Drop preview frames over a per-second cap while a take runs | F19 | none: upstream shows every frame. Env knobs exist upstream: `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}` (`PreviewWindowRenderer.cpp:296-301@up`) |
| `SettingsBridge::reloadValueSteps` + six read-only list properties | private method + `Q_PROPERTY` without WRITE | `SettingsBridge.cpp:1767-1796`; `.hpp:95-101` | Follow `UI.conf` keys that only Core writes | F5 | Order lists read with `settingsListValue` (`SettingsBridge.cpp:399-407@up`), all READ + WRITE. Upstream's read-only `SettingsBridge` properties (`lutPreviewOptions`, `tuningFileOptions`, `presetNames`, `presetStatus*`) are not `UI.conf` keys |
| `Automounter::handleSurpriseRemoval` | private method | `CfeAutomounter.cpp:726-746` | Lazy unmount, PCIe remove and LED off when the slot bit says the card left while mounted | F2 | none |
| `Automounter::removePcieDevice` | private method | `CfeAutomounter.cpp:748-761` | PCIe `remove` + `udevadm settle` | eject and pull paths | the same statements inline in `unmountPcie` (`CfeAutomounter.cpp:712-723@up`) |
| Per-feature state appliers `applyBufferState`, `applyCdngLogState`, `applyClipNameState`, `applyRecordingDroppedFrames`, `setControlsStatus` | private methods taking a `QJsonObject` | `ApertarControlBridge.hpp:301`, `:363-365`, `:453`; bodies `ApertarControlBridge.cpp:660-684`, `:1424-1435`, `:2652-2801` | Read one feature's keys from a state object or event and emit the NOTIFY signals | `applyCoreMessage`, `applyCoreState` | Inline `if (state.contains("x")) setX(...)` in `applyCoreState` plus one setter per property (`setFps`, `ApertarControlBridge.cpp:2230-2237@up`) |
| "Known" flags `storagePrerollAutoKnown`, `clipNameKnown`; `bufferSetting == ""`; `m_cdngLogApplied = true` by default | properties and defaults | `ApertarControlBridge.hpp:67`, `:76`, `:417`, `:422`, `:427`, `:434` | Hide a control until Core has sent the key ("older Core never does") | QML gates `SettingsPage.qml:2031`, `:3421`, `:5611` | Capability fields Core sends explicitly: `recording_capabilities.*` -> `rawCompressionSupported`, `proresSupported`, ... (`ApertarControlBridge.hpp:34-39@up`), `wb_available`, `exposureCompensationAvailable` |
| `ControlsWarning.qml`, `ClipNameCard.qml`, `ClipNamePill.qml` | QML components (registration only in this unit) | `CMakeLists.txt:41`, `:51-52`; `qml.qrc:32-33` | Chip and card | `CameraPage.qml:2711`, `SettingsPage.qml:4037` | `DroppedFrameWarning.qml` (chip, in `CMakeLists.txt:40@up`, absent from `qml.qrc@up`); settings cards as inline `Component`s in `SettingsPage.qml` |

No worker thread, no helper script and no new class in this unit.

## 7. Removed, narrowed or hidden

| # | What | Where | Effect | Label |
| --- | --- | --- | --- | --- |
| R1 | Default hardware file writer in the UI, both copies | `DisplayConfigBridge.cpp:41-326@up`, `Ina219Bridge.cpp:69-342@up` | See 5.3 B1-B5 | **confirmed** |
| R2 | The GPIO chip keys in the UI-written file: `chip=auto` under `[gpio_buttons]` and `[gpio_encoders]`, `gpiochip=auto` under `[trigger_output]` and `[recording_indicator]` | `DisplayConfigBridge.cpp:110`, `:123`, `:161`, `:172@up`; `Ina219Bridge.cpp:129`, `:142`, `:180`, `:191@up` | A fresh install no longer gets a file that shows where the GPIO chip is chosen. See section 9 | **confirmed** |
| R3 | Display fallback 720x720 `square`, `hdmi_external_only=false` | U4-U7 | Without a file the touch window is hidden and the layout is `landscape_large`. A file that has `[display]` size keys but no `hdmi_external_only` key now also hides the touch window (upstream's own templates always write the key: `DisplayConfigBridge.cpp:323@up`, `Ina219Bridge.cpp:339@up`, `Core:ApertarCoreApp.cpp:4329@up`) | **confirmed** in code; which rigs have such a file: **unconfirmed** |
| R4 | The UI's own fan-mode writer | U12-U14 | The fan mode cannot be changed from the touch UI while Core is not reachable: "Connect to Apertar Core before changing the fan mode." (`SystemActionBridge.cpp:72-75@port`). Upstream wrote `config.txt` itself. The block text is unchanged (U12) | **confirmed** |
| R5 | `applyTimecodeMode(displayValue)`, one argument | U26 | The tap on the camera screen and the first Settings choice send `target=ui`: Core's file timecode is no longer changed by them (`Core:ApertarCoreApp.cpp:13291@port`: `target != "ui" && !camera_.setTimecodeMode(mode)`). Upstream changed both at once (`ApertarControlBridge.cpp:630-634@up`, `Core:ApertarCoreApp.cpp:9429-9435@up`) | **confirmed** |
| R6 | `UI.conf` `timecodeMode` follows Core's `timecode_mode` | `ApertarControlBridge.cpp:1466-1473@up` | Not written from Core's state any more (`:1698-1706@port`); the field feeds `fileTimecodeMode` | **confirmed** (cpp, outside the scope) |
| R7 | `set_shutter_us` after `set_fps` | `ApertarControlBridge.cpp:255-289@up` | Skipped in a camera take with `fps_speed_ramp` on (`:275-280@port`); also no `saveCurrentCameraSettings()` there | **confirmed** (cpp, outside the scope) |
| R8 | `QStorageInfo` poll while Core says `removed` / `error` | U17 | `freeBytes`, `totalBytes`, remaining time and the media label are not refreshed in that state; `setMediaMounted(false)` and the text are set | **confirmed** |
| R9 | Preview frames while recording, only with the env var set | U22 | Frames over the cap never reach `frameArrived` / `previewFrameReady` | **confirmed** |
| R10 | `[camera]` section in the UI's template | added by `f1edf96`, removed with the writer by `c9d841f` | Lives only in Core's template now (`Core:ApertarCoreApp.cpp:5074-5079@port`) | **confirmed** |

## 8. Board and rig assumptions

| # | Assumption | Where | New in the port? | Label |
| --- | --- | --- | --- | --- |
| A1 | The default rig is an HDMI 1920x1080 monitor with no touch panel in use: `landscape_large`, touch window hidden | `DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357@port`; `DisplayConfigBridge.hpp:52-54`, `:59@port`; effect `main.cpp:432-433@port` | yes (`7c41a27`). Upstream's default was the 720x720 square panel | **confirmed** |
| A2 | Bit 0 of the CFexpress hat's status byte is a level that follows the card in the slot: a rising edge while mounted means "card pulled". Upstream uses only its falling edge, and only while not mounted (`CfeAutomounter.cpp:547@up`) and names the pair "buttons" (`readButtons`, `:402-422@up`) | `CfeAutomounter.cpp:549-550@port` | yes (`dc471c1`) | **confirmed** in code; that the hat's bit is a level on every hat revision: **unconfirmed** (hat schematic or `i2cget -y 10 0x34` while inserting) |
| A3 | "A Pi 5 cannot use a re-inserted NVMe until its PCIe device is removed and rescanned" (comment) | `CfeAutomounter.cpp:726-731@port` | the comment is new; the PCIe handling is upstream's (`brcm-pcie` `:637`, `1000110000.pcie` `:110`, I2C bus 10 `:38`, uid/gid 1000 `:603-605`, all `@port`, unchanged) | **confirmed** |
| A4 | The fan is the Pi 5 fan driven by `dtparam=cooling_fan` and `fan_temp0..3` in `/boot/firmware/config.txt` | read path `SystemActionBridge.cpp:26`, `:605-615@port` | no (upstream). New: the change needs a running Core | **confirmed** |
| A5 | INA219 on I2C bus 4, address 0x40 when no file says otherwise | `Ina219Bridge.cpp:42-43@port` | no (upstream). New: it is the only place that states it, the template is gone | **confirmed** |
| A6 | I2C bus numbers pinned by the removed templates: `[ina219] bus=4`, `[cfexpress_hat] bus=10`, `[pcf8574]`, `[neorotary4]`, `[grove_analog]`, `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]` `bus=1`; GPIO `line=17`, `d5`, `d6`, encoder pins 5 / 6 / 13 | 5.2 | upstream's; no longer written by the UI. The commit message of `c9d841f` says the template ("the CFE hat on bus 10 and the NeoRotary off") did not match the contributor's rig | **confirmed** (text), rig mismatch **probable** (commit message only) |
| A7 | The touch UI's drawing costs capture frames at 4K Clear HDR 16-bit 25 fps on this board; hence the cap knob | commit message of `c234d77`; no board check in code | motivation only | **probable** |
| A8 | `mount_path` `/media/RAW` | `MediaStatusBridge.hpp:142@port` (`m_mountPath`), `CfeAutomounter.cpp:109@port` | no (upstream) | **confirmed** |

Not found in the scope's added lines: any check of the Pi model, core count, RP1, RAM size or gpiochip number.
(`grep -nE 'Pi ?5|CM5|RP1|nproc|gpiochip|MemTotal' <added lines>` hits only the comment in A3.)
The RAM-sized queue behind `bufferMode == "ram"` is Core's; the bridge only shows `buffer_note`.

## 9. GPIO chip keys: cross-reference for the owner's request

The owner asked to bring back the definition of the GPIO chip, because the GPIO lines may sit on another chip
than the Pi header (a microcontroller, an expander). What this unit has to do with it:

| Fact | Evidence | Label |
| --- | --- | --- |
| The only place the UI named the chip was the two removed templates: `chip=auto` under `[gpio_buttons]` and `[gpio_encoders]`, `gpiochip=auto` under `[trigger_output]` and `[recording_indicator]` | `DisplayConfigBridge.cpp:110`, `:123`, `:161`, `:172@up`; `Ina219Bridge.cpp:129`, `:142`, `:180`, `:191@up` | **confirmed** |
| No UI bridge reads a GPIO chip key | `grep -n -i 'chip' src/*Bridge*.cpp src/*Bridge*.hpp src/main.cpp src/CfeAutomounter.cpp@port`: only the IMU chip-id code in `GyroConfigBridge.cpp` | **confirmed** |
| Core still parses `chip`, `gpiochip` and `gpio_chip` | `Core:hardware/GpioInput.cpp:343`, `TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:312`, `:340@port` | **confirmed** |
| Core's default template (shown by the WebUI editor for a missing file) has `gpiochip=auto` only under `[trigger_output]` and `[recording_indicator]`; `[gpio]`, `[gpio_encoders]`, `[gpio_switches]` carry no chip line | `Core:ApertarCoreApp.cpp:5168`, `:5182`, `:5137-5152@port`. Same two lines `@up` (`:4380`, `:4394`); upstream Core's template has no `[gpio_buttons]` keys either | **confirmed** |
| So at upstream a fresh install got the chip lines for buttons and encoders from the UI's template; at the port nothing writes them | B1 | **confirmed** |
| The Controls card leaves the chip out of its settings on purpose | `Core:hardware/ControlsModel.hpp:258-263@port`: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" (commit `c140c4f`) | **confirmed**. Outside this unit: belongs to the Core Controls unit |

## 10. Internal references in code comments (scope files, `@port`)

| Where | Text |
| --- | --- |
| `ApertarControlBridge.hpp:82` | "T45: what Core's validator finds in ~/apertar-hardware.conf ..." |
| `ApertarControlBridge.hpp:435` | "Core's fps_speed_ramp (T31): ..." |
| `SettingsBridge.hpp:95` | "T33: the value lists Core's set_value_steps writes to UI.conf ..." |
| `SettingsBridge.cpp:1767` | "T33: read only here; ..." |
| `ApertarControlBridge.hpp:424` | "CineMate Log (Core: cdng_log_bits, ...)" |
| `ApertarPreviewSocketClient.cpp:26` | "A/B knob like Core's APERTAR_WEB_PREVIEW_RECORDING_FPS" (a port-only Core variable: 0 hits `@up`) |

## 11. Facts for the later stages (no judgement)

| # | Fact | Evidence | Label |
| --- | --- | --- | --- |
| O1 | `MediaStatusBridge.statusText` values "MEDIA REMOVED" / "MEDIA ERROR" have no reader. No QML file reads `mediaBridge.statusText` (`@up` or `@port`), and `ExternalMonitorRuntimeBridge` reads only `mediaMounted` and the remaining texts. The visible effect of F1 is `mediaMounted = false` | `grep -rn 'mediaBridge\.' qml/ \| grep -o 'mediaBridge\.[A-Za-z]*' \| sort -u`; `ExternalMonitorRuntimeBridge.cpp:192-194@port`; `StatusChip.qml:61@port` | **confirmed** |
| O2 | After the removed / error branch the text returns to READY only through `setMediaMounted(true)`. A later Core state without a mount leaves the old text, because `setMediaMounted(false)` returns early | `MediaStatusBridge.cpp:328-345`, `:1247-1257@port` | **confirmed** |
| O3 | `bufferStopPercent` is a `Q_PROPERTY` with no QML reader; C++ uses the member for the dialog text | `grep -rn bufferStopPercent qml/` = 0; `ApertarControlBridge.cpp:2719-2721@port` | **confirmed** |
| O4 | `applyTimecodeMode` accepts `"both"`; no caller passes it | `ApertarControlBridge.cpp:753@port`; callers `CameraPage.qml:1842`, `SettingsPage.qml:4011`, `:4026` | **confirmed** |
| O5 | `qml/ControlsWarning.qml` is in `CMakeLists.txt:41` but not in `qml.qrc`. A non-AOT build (`APERTAR_QML_AOT=OFF`, the default when cross-compiling, `CMakeLists.txt:54-61`) would not ship it. Upstream has the same gap for `DroppedFrameWarning.qml` (`CMakeLists.txt:40@up`). The two ClipName files are in both lists | `grep -c ControlsWarning qml.qrc` = 0 | **confirmed** (not built) |
| O6 | With the cap set, dropped frames return before `emit frameArrived()`. The touch UI's "Rec Run" timecode counts `frameArrived` while recording, so it counts only the shown frames; with `0` it stops | `ApertarPreviewSocketClient.cpp:489-494`, `:538@port`; `CameraPage.qml:2038-2045@port` | **confirmed** in code, not seen on hardware |
| O7 | `setRecording` and `setCoreMediaState` are wired in normal mode only. The monitor-only process builds its own preview client, which reads and logs the env var but never caps | `main.cpp:131-141`, `:318-319`, `:351-352@port` | **confirmed** |
| O8 | Three synchronous Core-request implementations in the UI after the port: `sendCoreCommand`, `coreMediaCommand` (id 42001), `coreFanModeCommand` (id 42002). `set_fan_mode` blocks the GUI thread up to 1 s + 8 s | `SystemActionBridge.cpp:68-72`, `:80-94@port` | **confirmed** |
| O9 | The six new invokables return `void`; errors reach QML through `lastError` only | 3.4; `ApertarControlBridge.cpp:618-727@port` | **confirmed** |
| O10 | `c9d841f` and `7c41a27` were not built on the Pi when committed, and no later row records a test of the no-file start | section 1 | **confirmed** (records only) |
| O11 | `5697b54` has no fork-log row | `grep -c 5697b54 fork-log.md` = 0 | **confirmed** |

## 12. Unconfirmed, and the command that settles each

| Claim | Settle with |
| --- | --- |
| The no-file start shows only the HDMI monitor window on the rig | On the Pi: move the file away, restart `apertar-ui-direct`, read `journalctl -u apertar-ui-direct \| grep 'display config'` |
| A touch-panel rig without `hdmi_external_only` in its file exists | `grep -n hdmi_external_only /home/pi/apertar-hardware.conf` on each rig |
| The hat's bit 0 is a level on every hat revision (A2) | `watch -n0.2 i2cget -y 10 0x34` while inserting and pulling a card |
| The installed automounter is the port's build | `sha256sum /usr/local/libexec/apertar-cfe-automounter ~/ApertarUI/build/apertar-cfe-automounter` |
| Every reader's built-in defaults equal the removed templates' values (B6) | For each section in 5.2: `grep -n '<key>' Apertar-Core/src/hardware/*.hpp Apertar-UI/src/*.cpp` and compare |
| The UI at `@port` builds with `APERTAR_QML_AOT=OFF` (O5) | `cmake -DAPERTAR_QML_AOT=OFF` in a scratch build dir, then load the camera page |
