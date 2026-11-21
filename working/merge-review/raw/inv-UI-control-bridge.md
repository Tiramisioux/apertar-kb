# Inventory: UI-control-bridge (stage 1 of 3, no judgement)

Unit: `Apertar-UI/src/ApertarControlBridge.cpp`, port diff `origin/main` (`4415a55`) -> `cinemate-port` (`7ea9afc`).
Scope file: `/home/user/build/review/diffs/UI-ControlBridge.part01.diff` (708 lines, 12 hunks). It is the whole `.cpp` diff:
`git diff --minimal -U10 origin/main cinemate-port -- src/ApertarControlBridge.cpp` is byte-identical but for one trailing blank line.
The header `src/ApertarControlBridge.hpp` (+141 / -1) was read as well, because the properties and invokables are declared there.

Short names: `B.cpp` = `src/ApertarControlBridge.cpp`, `B.hpp` = `src/ApertarControlBridge.hpp`, `Core:App` =
`Apertar-Core/src/ApertarCoreApp.cpp`, `Core:CC` = `Apertar-Core/src/camera/CameraController.cpp`.
Refs: `@port` = `cinemate-port`, `@main` = fork `origin/main`, `@up` = `upstream-1.6.0`.
Every row is **confirmed** (read in code at the ref given) unless it says probable or unconfirmed.

## 0. Size

| Measure | @up | @main | @port | Port adds |
| --- | --- | --- | --- | --- |
| `B.cpp` lines | 2460 | 2490 | 2862 | +380 / -8 |
| `B.hpp` lines | 326 | 332 | 472 | +141 / -1 |
| `Q_PROPERTY` | 43 | 44 | 76 | 32 |
| `Q_INVOKABLE` | 35 | 36 | 42 | 6 new, 1 signature changed |
| `Q_INVOKABLE void` | 2 | 2 | 8 | all 6 new ones return void |
| Signals | 42 | 43 | 62 | 19 |
| Data members added | | | | 39 |
| Private functions added | | | | 6 |
| Socket commands sent (regex count of `sendCoreCommand(...)` names plus `get_state`, `user_activity`) | 41 | 42 | 48 | 6 new, 2 with a new argument |
| JSON keys read from Core (regex count of `.value(QStringLiteral(..))` / `.contains(..)`, plus 4 key-name arguments at the port) | 74 | 75 | 112 | 37 |
| Event names in `applyCoreMessage` | 14 | 14 | 17 | 3 new, 1 extended |
| Port commits that touch the unit | | | 11 | |

What fork `main` already added on top of upstream in this file (not the port): `applyClearHdr`, `setClearHdrValue`,
`clear_hdr` state key, 16-bit in the bit-depth parser, `set_clear_hdr` in the long-timeout list (`git diff upstream-1.6.0 origin/main`,
commit `4415a55`). The port does not modify any of those lines; they appear in the diff as context only.
All 8 removed lines are upstream-original code.

The UI at `cinemate-port` compiles on this machine (`/home/user/build/ui-port.log`: `[119/167] ... ApertarControlBridge.cpp.o`, `build rc=0`).

## 1. Hunk map

| # | Hunk | Function @port | Added lines @port | Commit | Feature (section 2) |
| --- | --- | --- | --- | --- | --- |
| 1 | `-9,20 +9,22` | file-scope constants | `B.cpp:19-20` | `f1edf96` | F3 |
| 2a | `-263,40 +265,55` | `applyFps` | `B.cpp:275-281` | `ec9f109` | F2 |
| 2b | same | `applyIso` | `B.cpp:302-309` | `f1edf96` | F4 |
| 3a | `-591,33 +608,131` | `applyStoragePreroll`, `applyStoragePrerollAuto` (new) | `B.cpp:618-630` | `841d0ed` | F12 |
| 3b | same | `applyClipNameTemplate`, `requestClipNamePreview`, `applyClipNameState` (new) | `B.cpp:632-684` | `606f137` | F13 |
| 3c | same | `applyBufferMode` (new) | `B.cpp:686-701` | `841d0ed` | F10 |
| 3d | same | `applyCdngLog` (new) | `B.cpp:716-727` | `841d0ed` | F11 |
| 4 | `-625,33 +740,40` | `applyTimecodeMode` | `B.cpp:750-769` (-5 / +12) | `7029db1` | F7 |
| 5 | `-884,21 +1006,21` | `updateRefreshTimer` | `B.cpp:1016` (-1 / +1) | `f1edf96` | F3 |
| 6a | `-1200,27 +1322,45` | `applyCoreMessage`: `controls` branch | `B.cpp:1332-1335` | `ea44bd7` | F8 |
| 6b | same | `applyCoreMessage`: `media` branch | `B.cpp:1336-1340` | `160898c` | F1 |
| 6c | same | `applyCoreMessage`: `buffer` branch | `B.cpp:1345-1349` | `841d0ed`, `68e1a41` (line 1347) | F9, F12, F14 |
| 6d | same | `applyCoreMessage`: `recording` branch | `B.cpp:1353-1356` | `ec9f109` | F2 |
| 7a | `-1265,36 +1405,63` | `setCoreMediaState` (new) | `B.cpp:1415-1422` | `160898c` | F1 |
| 7b | same | `setControlsStatus` (new) | `B.cpp:1424-1435` | `ea44bd7` | F8 |
| 7c | same | `applyCoreState` head | `B.cpp:1439` (`ea44bd7`), `:1440-1442` (`160898c`), `:1457` (`68e1a41`) | | F8, F1, F14 |
| 8 | `-1334,20 +1501,26` | `applyCoreState` | `B.cpp:1511-1515` | `ec9f109` | F2 |
| 9 | `-1399,20 +1572,62` | `applyCoreState` | `B.cpp:1582-1622` | `f1edf96` (28 lines), `7840438` (7), `c716dec` (4), `ed0d7b5` (3) | F3, F4, F5, F6 |
| 10 | `-1478,22 +1693,25` | `applyCoreState` timecode block | `B.cpp:1703-1707` (-2 / +5) | `7029db1` | F7 |
| 11 | `-1504,20 +1722,23` | `applyCoreState` | `B.cpp:1732-1733` (`841d0ed`), `:1734` (`606f137`) | | F9-F13 |
| 12a | `-2421,20 +2642,171` | `applyRecordingDroppedFrames` (new) | `B.cpp:2652-2662` | `68e1a41` | F14 |
| 12b | same | `applyBufferState` (new) | `B.cpp:2664-2767` | `841d0ed` | F9, F10, F12 |
| 12c | same | `applyCdngLogState` (new) | `B.cpp:2769-2801` | `841d0ed` | F11 |

Blame totals over the 380 added lines: `841d0ed` 189, `606f137` 55, `f1edf96` 39, `ea44bd7` 18, `ec9f109` 17, `7029db1` 17,
`160898c` 17, `68e1a41` 14, `7840438` 7, `c716dec` 4, `ed0d7b5` 3.

## 2. Operator-visible features that touch this unit

| ID | Feature | What the operator gets | Commits | Bridge side @port |
| --- | --- | --- | --- | --- |
| F1 | Core media state on the touch UI | Status says MEDIA REMOVED or MEDIA ERROR and the media counts as not mounted (`setMediaMounted(false)`, `src/MediaStatusBridge.cpp:1249`; the record paths test `mediaBridge.mediaMounted`, `qml/CameraPage.qml:3971-3991`) when Core reports the card gone although the mount table still lists it | `160898c` | `media` event `B.cpp:1336-1340`; `media_state` / `media_alive` `:1440-1442`; signal `coreMediaStateChanged` `B.hpp:268`; wired in `src/main.cpp:318-319` to `MediaStatusBridge::setCoreMediaState` (`src/MediaStatusBridge.cpp:288-297`, `:1245-1257`) |
| F2 | Speed-ramp take: FPS picker sends only `set_fps` | In a cDNG or MLV take with speed ramping on, an FPS change from the touch UI is a ramp step: the UI no longer overrides Core's shutter policy or saves the ramp rate as the setting | `ec9f109` | `applyFps` guard `B.cpp:275-281`; `fps_speed_ramp`, `sound_recording` `:1511-1515`; `sound_only` of the `recording` event `:1353-1356` |
| F3 | Values in use, and marking of values the camera decides | With auto ISO or auto WB the readout shows the gain or Kelvin in use; values Core holds (Clear HDR hold, ramp-driven shutter angle) are marked on the touch screen and the HDMI overlay | `f1edf96`, `7840438` (QML rendering later changed green -> italic by `35b31f6`, no bridge change) | `B.cpp:1582-1622`; 1 s `get_state` poll while auto, `:19-20`, `:1016`; properties `isoInUse`, `whiteBalanceInUse`, `isoSetByCamera`, `whiteBalanceSetByCamera`, `shutterSetByCamera` |
| F4 | ISO ceiling and ISO Lock | The ISO list greys values above Core's ceiling for the mode; while auto ISO runs, "Lock" freezes the gain in use | `f1edf96` | `applyIso("Lock")` `B.cpp:302-309`; `iso_max` `:1591-1592`; property `isoMax` |
| F5 | FPS ceiling from Core | The FPS picker greys rates above Core's ceiling | `ed0d7b5` | `fps_max` `B.cpp:1593-1594`; property `fpsMax` |
| F6 | Mode Ladder indicator | Settings > Format: Compression is disabled and labelled "(set by Mode Ladder)" while the ladder is active | `c716dec` | `ladder_active` `B.cpp:1589-1590`; property `ladderActive` |
| F7 | UI timecode and file timecode set apart | Settings > Timecode has "UI timecode" and "File timecode"; the tap on the camera screen changes the UI one only | `7029db1` (labels renamed in QML by `08cefcf`) | `applyTimecodeMode(value, target)` `B.cpp:750-771`; `timecode_mode` -> `fileTimecodeMode` `:1698-1708` |
| F8 | Controls status | Camera page chip "Controls: N errors"; Settings > Info > Controls card with counts and the WebUI address (read-only) | `ea44bd7` | `controls` event `B.cpp:1332-1335`; `controls_errors` / `controls_warnings` `:1439`; `setControlsStatus` `:1424-1435` |
| F9 | Write-buffer bar and safety stop | REC/READY pill can show the write-buffer level; when Core ends a take at its buffer limit the pill shows the buffer emptying and a dialog says the clip is complete | `841d0ed` (QML follow-ups `4959513`, `96a7aa4` do not touch the bridge) | `buffer` event `B.cpp:1345-1349`; `applyBufferState` `:2664-2725`; signal `bufferSafetyStopped(message)` `:2722` |
| F10 | Write Buffer mode | Settings > Record: "Frames" / "RAM" buttons and a note | `841d0ed` | `applyBufferMode` `B.cpp:686-701`; `buffer_setting`, `buffer_note` `:2676-2691` |
| F11 | Log storage for cDNG | Settings > Record: Log On/Off; "Log" on the format line when applied; minutes left follow the stored bits | `841d0ed` | `applyCdngLog` `B.cpp:716-727`; `applyCdngLogState` `:2769-2801` |
| F12 | Storage pre-roll | "Storage Pre-roll" button, "Automatic pre-roll" On/Off, last-result text; blue PRE-ROLL pill and the pre-roll frame rate while it runs | `841d0ed` | `applyStoragePreroll` `B.cpp:618-622`; `applyStoragePrerollAuto` `:624-630`; `storage_preroll_*` `:2726-2766` |
| F13 | Clip names | Settings > Record > Clip Names: template built from pills, preview of the next clip name | `606f137` | `applyClipNameTemplate` `B.cpp:632-642`; `requestClipNamePreview` `:644-658`; `applyClipNameState` `:660-684` |
| F14 | Dropped-frames count | The dropped-frames chip shows the number instead of "!" (touch UI and HDMI) | `68e1a41` | `applyRecordingDroppedFrames` `B.cpp:2652-2662`, called at `:1347` and `:1457` |

## 3. Socket commands

No HTTP route in this unit. Socket path and env `APERTAR_CONTROL_SOCKET` are unchanged (`B.cpp:1168`, `:1805` @port).

| Invokable @port | Command | Arguments | Core handler @port | What the bridge does with the reply | Status |
| --- | --- | --- | --- | --- | --- |
| `applyStoragePreroll()` `B.cpp:618` | `storage_preroll` | none | `Core:App:14603` | nothing; a refusal reaches `lastError` | new command |
| `applyStoragePrerollAuto(bool)` `B.cpp:624` | `set_storage_preroll` | `value=on\|off` | `Core:App:12900` | nothing of its own ("No optimistic update") | new command |
| `applyClipNameTemplate(QString)` `B.cpp:632` | `set_clip_name_template` | `value=<template>` | `Core:App:13241` | `applyClipNameState(reply)` | new command |
| `requestClipNamePreview(QString)` `B.cpp:644` | `preview_clip_name` | `value=<template>` | `Core:App:13258` | reply key `example` -> `clipNamePreview` | new command |
| `applyBufferMode(QString)` `B.cpp:686` | `set_buffer_mode` | `value=frames\|ram` (checked in the bridge first) | `Core:App:12829` | sets `m_bufferSetting` | new command |
| `applyCdngLog(bool)` `B.cpp:716` | `set_cdng_log` | `value=auto\|off` | `Core:App:13079` | sets `m_cdngLogOn` | new command |
| `applyIso("Lock")` `B.cpp:303-308` | `set_iso_auto` | `enabled="false"` | `Core:App:12995-13001` (upstream handler takes no argument, `Core:App:9269-9273` @up) | `saveCurrentCameraSettings()` | upstream command, new argument |
| `applyTimecodeMode(v, target)` `B.cpp:750` | `set_timecode_mode` | `value`, `target=ui\|files\|both` | `Core:App:13279-13300` (upstream: no target, always sets the camera mode and `UI.conf`, `Core:App:9424-9437` @up) | see section 9 row 4 | upstream command, new argument |
| `applyFps` `B.cpp:257` | `set_fps`, then `set_shutter_us` | unchanged | `Core:App:13003`, `:13012` | in a ramp take the second command is not sent | behaviour changed |
| `refreshFromCore` `B.cpp:990` | `get_state` | unchanged | `Core:App:12932` | interval 1 s while auto ISO or auto WB, else 30 s | cadence changed |

All six new commands use the default 3000 ms reply timeout: none is in the `reconfigureCommand` list (`B.cpp:1151-1167` @port, list unchanged by the port).
The new invokables block the GUI thread in `sendCoreCommand` like every upstream invokable (`B.cpp:1013-1106` @up).

## 4. Events

| Event | New to Core? | Fields the bridge reads | Handler @port | Core emitter @port | Commit |
| --- | --- | --- | --- | --- | --- |
| `controls` | yes (not in upstream Core) | `errors`, `warnings` | `B.cpp:1332-1335` -> `setControlsStatus` | `Core:App:12346-12348` | `ea44bd7` |
| `media` | yes | `state`, `mounted` | `B.cpp:1336-1340` -> `setCoreMediaState` | `Core:App:10824-10835` | `160898c` |
| `buffer` | yes | all `buffer_*`, `storage_preroll_*`, `recording_dropped_frames` | `B.cpp:1345-1349` -> `applyBufferState`, `applyRecordingDroppedFrames` | `Core:App:10839-10843`, members `:252-269`, `:301-311` | `841d0ed`, `68e1a41` |
| `recording` | upstream event | adds `sound_only` (upstream Core sends it, `Core:App:8394`, `:8406` @up; upstream UI does not read it) | `B.cpp:1353-1356` | `Core:App:10072`, `:10084` | `ec9f109` |
| `recording_health` | upstream event | adds `recording_dropped_frames` through `applyCoreState` | `B.cpp:1457` | `Core:CC:10491-10492` | `68e1a41` |

Upstream Core event names (grep of `event\":\"`, @up): audio_level, camera_state, hardware_action, media_write_state, photo_capture,
photo_write_error, prepare_recording, recording, recording_health, settings, standby, still_exposure, timelapse, timelapse_frame,
timelapse_progress. The port Core adds `buffer`, `controls`, `media`.

Fields of the `buffer` event that the bridge does not read: `buffer_used`, `buffer_capacity`, `buffer_unit`, `buffer_flush_discarded`,
`storage_preroll_auto_env`, `frames_per_folder`, `frames_per_folder_env`, `clip_merge_enabled`, `clip_merge_env_off` (`Core:App:252-269`, `:301-311`).

## 5. State fields read

37 JSON keys are read by the port and not by `main` (33 through `state.value` / `state.contains`, 4 as key-name arguments of `setControlsStatus`).
"New in Core" = the key does not occur in upstream or main Core (`grep` over `ApertarCoreApp.cpp` and `CameraController.cpp`).

| Key | Wire type | New in Core | Member -> property | NOTIFY | Read at @port | Core emitter @port (one of) | Commit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `controls_errors` | int | yes | `m_controlsErrors` -> `controlsErrors` | `controlsStatusChanged` | `B.cpp:1439`, `:1428` | `Core:App:9458`, `:12947` | `ea44bd7` |
| `controls_warnings` | int | yes | `m_controlsWarnings` -> `controlsWarnings` | `controlsStatusChanged` | `B.cpp:1439`, `:1429` | `Core:App:9459`, `:12948` | `ea44bd7` |
| `errors`, `warnings` (event `controls`) | int | yes | same members | same | `B.cpp:1333` | `Core:App:12347` | `ea44bd7` |
| `media_state` | string | yes | `m_coreMediaState`, no property | `coreMediaStateChanged(state, alive)` | `B.cpp:1440-1441` | `Core:App:9555`, `:12961` | `160898c` |
| `media_alive` | bool | yes | `m_coreMediaAlive`, no property | same | `B.cpp:1442` | `Core:App:9556`, `:12962` | `160898c` |
| `state`, `mounted` (event `media`) | string, bool | yes | same members | same | `B.cpp:1337-1338` | `Core:App:10827-10828` | `160898c` |
| `fps_speed_ramp` | bool | yes | `m_fpsSpeedRamp`, internal | none | `B.cpp:1511-1512` | `Core:App:369`, `Core:CC:231` | `ec9f109` |
| `sound_recording` | bool | no (`Core:App:7844`, `:9228` @up; unread by upstream UI) | `m_soundRecording`, internal | none | `B.cpp:1514-1515` | same key | `ec9f109` |
| `sound_only` (event `recording`) | bool | no | `m_soundRecording` | none | `B.cpp:1354-1356` | `Core:App:10072` | `ec9f109` |
| `ladder_active` | bool | yes | `m_ladderActive` -> `ladderActive` | `cameraSetValuesChanged` | `B.cpp:1589-1590` | `Core:App:327`, `:9491` | `c716dec` |
| `iso_max` | int | yes | `m_isoMax` -> `isoMax` | `cameraSetValuesChanged` | `B.cpp:1591-1592` | `Core:App:324`, `:9488` | `f1edf96` |
| `fps_max` | number | yes | `m_fpsMax` -> `fpsMax` | `cameraSetValuesChanged` | `B.cpp:1593-1594` | `Core:App:325`, `:9489` | `ed0d7b5` |
| `iso_auto_after_clear_hdr` | bool | yes | `m_isoAutoAfterClearHdr` -> `isoSetByCamera` | `cameraSetValuesChanged` | `B.cpp:1595-1596`, `:1608` | `Core:App:335`, `:9499` | `f1edf96`, `7840438` |
| `wb_auto_after_clear_hdr` | bool | yes | `m_whiteBalanceAutoAfterClearHdr` -> `whiteBalanceSetByCamera` | `cameraSetValuesChanged` | `B.cpp:1597-1598`, `:1609` | `Core:App:347`, `:9507` | `f1edf96`, `7840438` |
| `fps_speed_ramp_keep_exposure` | bool | yes | `m_fpsSpeedRampKeepExposure`; with `m_recording` and `m_fpsSpeedRamp` -> `shutterSetByCamera` | `cameraSetValuesChanged` | `B.cpp:1599-1600`, `:1610` | `Core:App:370`, `:9532` | `f1edf96`, `7840438` |
| `iso_actual` | int | yes | `m_isoInUse` -> `isoInUse` (only while `m_isoAuto`) | `cameraSetValuesChanged` | `B.cpp:1602-1603` | `Core:App:323`, `:9487`, `Core:CC:175` | `f1edf96` |
| `wb_actual_kelvin` | number | no (`Core:App:189`, `:7873` @up; unread by upstream UI) | `m_whiteBalanceInUse` -> `whiteBalanceInUse` (only while `m_whiteBalanceAuto`) | `cameraSetValuesChanged` | `B.cpp:1604-1607` | same key | `f1edf96` |
| `wb_measured` | bool | no (`Core:App:188`, `:7872` @up) | gate for the row above | | `B.cpp:1606` | same key | `f1edf96` |
| `timecode_mode` (upstream key, new meaning) | string | no | `m_fileTimecodeMode` -> `fileTimecodeMode` | `fileTimecodeModeChanged` | `B.cpp:1698-1708` | `Core:App:385`, `:9509` | `7029db1` |
| `recording_dropped_frames` | int | yes | `m_recordingDroppedFrames` -> `recordingDroppedFrames` (clamped 0..999999) | `recordingHealthChanged` (upstream signal, now shared) | `B.cpp:2654-2661` | `Core:App:9457`, `:10842`, `Core:CC:10492`, `:12889` | `68e1a41` |
| `buffer_mode` | string | yes | `m_bufferMode` -> `bufferMode` (`frames`, `ram`, else `none`) | `bufferModeChanged` | `B.cpp:2667-2675` | `Core:App:307` | `841d0ed` |
| `buffer_setting` | string | yes | `m_bufferSetting` -> `bufferSetting` (`frames`, `ram`, else empty) | `bufferSettingChanged` | `B.cpp:2676-2684` | `Core:App:256` | `841d0ed` |
| `buffer_note` | string | yes | `m_bufferNote` -> `bufferNote` | `bufferNoteChanged` | `B.cpp:2685-2691` | `Core:App:256` | `841d0ed` |
| `buffer_fill` | number 0..1 | yes | `m_bufferFill` -> `bufferFill` | `bufferFillChanged` | `B.cpp:2692-2700` | `Core:App:306` | `841d0ed` |
| `buffer_stop_percent` | int | yes | `m_bufferStopPercent` -> `bufferStopPercent` | `bufferStopPercentChanged` | `B.cpp:2701-2708` | `Core:App:258` | `841d0ed` |
| `buffer_safety_stop` | bool | yes | `m_bufferSafetyStop` -> `bufferSafetyStop` | `bufferSafetyStopChanged`, and once `bufferSafetyStopped(message)` | `B.cpp:2709-2725` | `Core:App:257` | `841d0ed` |
| `storage_preroll_active` | bool | yes | `m_storagePrerollActive` -> `storagePrerollActive` | `storagePrerollActiveChanged` | `B.cpp:2726-2735` | `Core:App:260` | `841d0ed` |
| `storage_preroll_auto` | bool | yes | `m_storagePrerollAuto`, `m_storagePrerollAutoKnown` -> `storagePrerollAuto`, `storagePrerollAutoKnown` | `storagePrerollAutoChanged`, `storagePrerollAutoKnownChanged` | `B.cpp:2736-2750` | `Core:App:261` | `841d0ed` |
| `storage_preroll_fps` | number | yes | `m_storagePrerollFps` -> `storagePrerollFps` | `storagePrerollFpsChanged` | `B.cpp:2751-2759` | `Core:App:263` | `841d0ed` |
| `storage_preroll_last` | string | yes | `m_storagePrerollLast` -> `storagePrerollLast` | `storagePrerollLastChanged` | `B.cpp:2760-2766` | `Core:App:264` | `841d0ed` |
| `cdng_log` | string `off` / `auto` | yes | `m_cdngLogOn` -> `cdngLogOn` (anything but `off` = on) | `cdngLogChanged` | `B.cpp:2790-2792` | `Core:App:356`, `:9517` | `841d0ed` |
| `cdng_log_bits` | int | yes | `m_cdngLogBits` -> `cdngLogBits` | `cdngLogChanged` | `B.cpp:2779-2783` | `Core:App:357`, `:9518` | `841d0ed` |
| `cdng_log_available` | bool | yes | `m_cdngLogAvailable` -> `cdngLogAvailable` | `cdngLogChanged` | `B.cpp:2786-2787` | `Core:App:358`, `:9519` | `841d0ed` |
| `cdng_log_applied` | bool | yes | `m_cdngLogApplied` (default true) -> `cdngLogApplied` | `cdngLogChanged` | `B.cpp:2788-2789` | `Core:App:359`, `:9520` | `841d0ed` |
| (derived) | | | `m_cdngLogActive` = available && bits > 0 && applied -> `cdngLogActive` | `cdngLogChanged` | `B.cpp:2793` | | `841d0ed` |
| `clip_name_template` | string | yes | `m_clipNameTemplate`, `m_clipNameKnown` -> `clipNameTemplate`, `clipNameKnown` | `clipNameChanged` | `B.cpp:664-674` | `Core:App:373`, `:9535` | `606f137` |
| `clip_name_example` | string | yes | `m_clipNameExample` -> `clipNameExample` | `clipNameChanged` | `B.cpp:675-681` | `Core:App:374`, `:9536` | `606f137` |
| `example` (reply of `preview_clip_name`) | string | yes | `m_clipNamePreview` -> `clipNamePreview` | `clipNamePreviewChanged` | `B.cpp:653-657` | `Core:App:13266` | `606f137` |

No key that `main` read was dropped (`comm` of the two key sets: empty).

## 6. Header additions (`B.hpp` @port)

| Kind | Names | Lines |
| --- | --- | --- |
| Properties, camera-set group (9) | `isoMax`, `fpsMax`, `fileTimecodeMode`, `ladderActive`, `isoInUse`, `whiteBalanceInUse`, `isoSetByCamera`, `whiteBalanceSetByCamera`, `shutterSetByCamera` | `19-27` |
| Properties, recording group (21) | `recordingDroppedFrames`, `bufferFill`, `bufferMode`, `bufferSafetyStop`, `storagePrerollActive`, `storagePrerollAuto`, `storagePrerollAutoKnown`, `storagePrerollFps`, `storagePrerollLast`, `bufferStopPercent`, `bufferSetting`, `bufferNote`, `clipNameTemplate`, `clipNameExample`, `clipNamePreview`, `clipNameKnown`, `cdngLogActive`, `cdngLogBits`, `cdngLogOn`, `cdngLogAvailable`, `cdngLogApplied` | `61-81` |
| Properties, controls (2) | `controlsErrors`, `controlsWarnings` | `83-84` |
| Getters, inline | one per property | `104-112`, `142-164` |
| Invokables (6 new, all `void`) | `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto`, `applyClipNameTemplate`, `requestClipNamePreview`, `applyCdngLog` | `194-198`, `200` |
| Invokable, signature changed | `bool applyTimecodeMode(const QString &displayValue, const QString &target)`; was one argument (`B.hpp:130` @main, `:127` @up); no default for `target` | `202-203` |
| Signals (19) | `cameraSetValuesChanged`, `fileTimecodeModeChanged`, `bufferFillChanged`, `bufferModeChanged`, `bufferSafetyStopChanged`, `storagePrerollActiveChanged`, `storagePrerollAutoChanged`, `storagePrerollAutoKnownChanged`, `storagePrerollFpsChanged`, `storagePrerollLastChanged`, `bufferStopPercentChanged`, `bufferSettingChanged`, `bufferNoteChanged`, `cdngLogChanged`, `clipNameChanged`, `clipNamePreviewChanged`, `controlsStatusChanged`, `coreMediaStateChanged(const QString &state, bool alive)`, `bufferSafetyStopped(const QString &message)` | `228`, `245`, `251-265`, `268`, `277` |
| Private functions (6) | `applyClipNameState`, `applyBufferState`, `applyRecordingDroppedFrames`, `applyCdngLogState`, `setCoreMediaState`, `setControlsStatus` | `301`, `363-365`, `371`, `453` |
| Data members (39) | see diff | `413-456` |

All new properties are read-only with NOTIFY, as upstream's 43 are. `coreMediaState` has a signal and members but no `Q_PROPERTY`.

## 7. Config keys, files on disk, env vars

The bridge reads no new file and no new env var. It adds no `UI.conf` key of its own.

| Item | Where | Change |
| --- | --- | --- |
| `UI.conf` `[General] timecodeMode` | `B.cpp:762-765` @port (was `:646-647` @main) | The bridge writes it only for target `ui` or `both` |
| same | `B.cpp:1698-1708` @port (was `:1483-1490` @main with the write at `:1488`, `:1466-1473` @up) | The write from Core's `timecode_mode` state is gone |
| `apertar-hardware.conf` `[storage] buffer` | written by Core for `set_buffer_mode`, `Core:App:12839` @port | The touch UI can now change this key through Core |
| `apertar-hardware.conf` `[media] preroll` | written by Core for `set_storage_preroll`, `Core:App:12913` @port | same |
| `camera_settings.conf` `cdng_log` | Core, `Core:CC:854`, `:959` @port | set through `set_cdng_log` |
| `camera_settings.conf` `clip_name_template` | Core, `Core:CC:899`, `:981` @port | set through `set_clip_name_template` |
| `UI.conf` `[General] frameBufferBarEnabled` | `src/SettingsBridge.cpp:369`, `:1178` @port (SettingsBridge, other unit) | Gates the buffer bar that `bufferFill` feeds |
| env `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL` | read by Core only, `Core:App:276`, `:278` @port | Can override what the two UI switches set; the UI does not read them |
| env `APERTAR_CONTROL_SOCKET` | `B.cpp:1168` @port | unchanged (upstream) |

## 8. UI elements fed by this unit (defined in other units)

| Element | File:line @port | Bridge members used |
| --- | --- | --- |
| ISO stat: value in use, italic when camera-set | `qml/CameraPage.qml:3091-3095`, `qml/TopDropdownStat.qml:10-11`, `:37-39` | `isoInUse`, `isoSetByCamera` |
| ISO option list: ceiling, "Lock" | `qml/CameraPage.qml:522-539` | `isoMax`, `applyIso("Lock")` |
| Shutter stat | `qml/CameraPage.qml:3125-3126` | `shutterSetByCamera` |
| WB stat | `qml/CameraPage.qml:3166-3168` | `whiteBalanceInUse`, `whiteBalanceSetByCamera` |
| FPS stat: pre-roll fps | `qml/CameraPage.qml:3055-3059` | `storagePrerollActive`, `storagePrerollFps` |
| FPS ceiling | `qml/CameraPage.qml:904-906` | `fpsMax` |
| Status pill: buffer bar, drain, PRE-ROLL | `qml/CameraPage.qml:2704-2708`, `qml/StatusChip.qml:11`, `:20-22`, `:102` | `bufferFill`, `bufferMode`, `bufferSafetyStop`, `storagePrerollActive` |
| Record button / pill during a safety-stop flush | `qml/CameraPage.qml:576-578`, `:2694` | `bufferSafetyStop` |
| "Controls: N errors" chip | `qml/CameraPage.qml:2711-2721`, `qml/ControlsWarning.qml` | `controlsErrors` |
| Dropped-frames chip with count | `qml/CameraPage.qml:2723-2733`, `qml/DroppedFrameWarning.qml` | `recordingDroppedFrames` |
| Format line suffix "Log" | `qml/CameraPage.qml:558` | `cdngLogActive` |
| Frame-size estimate | `qml/CameraPage.qml:1012-1015`, `:1960-1962` | `cdngLogActive`, `cdngLogBits`, `cdngLogChanged` |
| Dialog "Recording Stopped ... Write Buffer" | `qml/CameraPage.qml:1964-1967` | `bufferSafetyStopped(message)` |
| Timecode tap | `qml/CameraPage.qml:1837-1843` | `applyTimecodeMode(nextMode, "ui")` |
| Settings > Format: Compression label and enable | `qml/SettingsPage.qml:3398`, `:3408-3409` | `ladderActive` |
| Settings > Record: Write Buffer (Frames / RAM, note) | `qml/SettingsPage.qml:3417-3461` | `bufferSetting`, `bufferMode`, `bufferNote`, `applyBufferMode` |
| Settings > Record: Log (On/Off, note) | `qml/SettingsPage.qml:3463-3495` | `cdngLogAvailable`, `cdngLogOn`, `cdngLogApplied`, `cdngLogBits`, `applyCdngLog` |
| Settings > Timecode: "UI timecode", "File timecode" | `qml/SettingsPage.qml:3998-4028` | `fileTimecodeMode`, `applyTimecodeMode(v, "ui" \| "files")` |
| Settings > Record: Clip Names card | `qml/SettingsPage.qml:2029-2033`, `:4042`; `qml/ClipNameCard.qml:52`, `:139-170`, `:315-337`, `:512-517` | `clipNameKnown`, `clipNameTemplate`, `clipNameExample`, `clipNamePreview`, `applyClipNameTemplate`, `requestClipNamePreview`, `clipNameChanged` |
| Settings > Media Speed: "Storage Pre-roll", "Automatic pre-roll", last result | `qml/SettingsPage.qml:5599-5668` | `storagePrerollActive`, `storagePrerollAutoKnown`, `storagePrerollAuto`, `storagePrerollLast`, `applyStoragePreroll`, `applyStoragePrerollAuto` |
| Settings > Info: Controls card | `qml/SettingsPage.qml:6455-6478` | `controlsErrors`, `controlsWarnings` |
| HDMI overlay: FPS / ISO / SHUTTER / WB items | `qml/ExternalMonitorWindow.qml:96-118`, `:201-207`, `:902` | `storagePrerollActive`, `storagePrerollFps`, `isoMax`, `isoInUse`, `whiteBalanceInUse`, `*SetByCamera` |
| HDMI overlay: format info "Log" | `qml/ExternalMonitorWindow.qml:141-145` | `cdngLogActive` |
| HDMI status pill: PRE-ROLL, buffer bar, drain | `qml/ExternalMonitorWindow.qml:157`, `:188-200`, `:1105-1126` | `storagePrerollActive`, `bufferSafetyStop`, `bufferFill`, `bufferMode` |
| HDMI dropped-frames chip | `qml/ExternalMonitorWindow.qml:1181-1186` | `recordingDroppedFrames` |
| Media status text MEDIA REMOVED / MEDIA ERROR | `src/MediaStatusBridge.cpp:1245-1257` | `coreMediaStateChanged` |

Members with no reader outside the bridge: `bufferStopPercent` (used only for the message text, `B.cpp:2719-2720`).
`controlsWarnings` is read only by the Settings card. Target `"both"` is accepted (`B.cpp:753`) and never sent by QML.

## 9. Original code modified

"Original" = present at `@main`; every region below is also upstream-original (line numbers at `@up` in brackets).

| # | Region | Where | Change | Kind |
| --- | --- | --- | --- | --- |
| 1 | Poll interval constants | `B.cpp:17-18` @main [`:17-18`] -> `:17-20` @port | Third constant `kLiveValuePollIntervalMs = 1000` | extended-in-place |
| 2 | `applyFps` | `B.cpp:255-289` @main [`:255-289`] -> `:257-298` @port | After `set_fps` succeeds: `if (m_recording && !m_soundRecording && m_fpsSpeedRamp) return true;`. Skips `setFps`, the `set_shutter_us` that keeps the angle, and `saveCurrentCameraSettings` | behaviour-changed |
| 3 | `applyIso` | `B.cpp:291-316` @main [`:291-316`] -> `:300-335` @port | New first branch for the display value `"Lock"` | extended-in-place |
| 4 | `applyTimecodeMode` | `B.cpp:635-649` @main [`:622-636`] -> `:750-771` @port; `B.hpp:130` @main -> `:202-203` @port | Second parameter `target`; target validated; sent to Core; `UI.conf` write only when target is not `files`; `m_fileTimecodeMode` set when target is not `ui` | rewritten |
| 5 | `updateRefreshTimer` | `B.cpp:888-895` @main [`:875-882`] -> `:1010-1017` @port | Steady-state interval is 1 s while `m_isoAuto \|\| m_whiteBalanceAuto`, else 30 s | behaviour-changed |
| 6 | `applyCoreMessage` event chain | `B.cpp:1196-1273` @main [`:1182-1259`] -> `:1318-1413` @port | Three new `if (event == ...) { ...; return; }` branches: `controls`, `media`, `buffer` | extended-in-place |
| 7 | `applyCoreMessage`, `recording` branch | `B.cpp:1215-1225` @main [`:1201-1211`] -> `:1351-1365` @port | Reads `sound_only` into `m_soundRecording` between `applyCoreState(message)` and `setRecordingState` | extended-in-place |
| 8 | `applyCoreState`, head | `B.cpp:1275-1290` @main [`:1261-1276`] -> `:1437-1457` @port | `setControlsStatus(...)` and the `media_state` block before the first upstream key; `applyRecordingDroppedFrames(state)` after the dropped-frames flag | extended-in-place |
| 9 | `applyCoreState`, auto flags | `B.cpp:1337-1342` @main [`:1323-1328`] -> `:1504-1515` @port | `fps_speed_ramp`, `sound_recording` | extended-in-place |
| 10 | `applyCoreState`, after the WB block | `B.cpp:1401-1407` @main [`:1387-1393`] -> `:1582-1622` @port | 41-line block for the camera-set values; ends with `updateRefreshTimer()`, so the timer interval is now set on every state pass | extended-in-place |
| 11 | `applyCoreState`, timecode block | `B.cpp:1483-1490` @main [`:1466-1473`] -> `:1698-1708` @port | `m_settings.setValue("timecodeMode", ...)` and `m_settings.sync()` removed; sets `m_fileTimecodeMode` and emits instead | rewritten |
| 12 | `applyCoreState`, after `recording` | `B.cpp:1512-1513` @main [`:1495-1496`] -> `:1730-1734` @port | Calls `applyBufferState`, `applyCdngLogState`, `applyClipNameState` | extended-in-place |
| 13 | Invokable area | between `applyRawBitDepth` and `applyH264Resolution`, `B.cpp:576-614` @main -> `:593-729` @port | Seven functions inserted (six invokables and `applyClipNameState`), around fork main's `applyClearHdr` | extended-in-place |
| 14 | Setter area | between `setAutofocusWindowValue` and `setRecordingState`, `B.cpp:2422-2431` @main [`:2392-2401`] -> `:2643-2803` @port | Three state mappers inserted among the upstream setters | extended-in-place |
| 15 | Signal `recordingHealthChanged` | `B.hpp:175` @main [`:171`]; emitted `B.cpp:1454` and now `:2660` @port | Also the NOTIFY of `recordingDroppedFrames`; fires on count changes carried by `buffer` events | extended-in-place |
| 16 | `src/main.cpp` wiring | `src/main.cpp:318-319` @port | One `connect` of `coreMediaStateChanged` to `MediaStatusBridge::setCoreMediaState`, beside the upstream wiring block | extended-in-place |

Not touched by the port: `sendCoreCommand`, `refreshFromCore`, `ensureEventSocketConnected`, `processEventSocketMessages`,
`loadPersistedCameraSettings`, `saveCurrentCameraSettings`, all `parse*` / `format*` helpers, the constructor.

## 10. New abstractions and what upstream uses for the same job

| # | Abstraction | Purpose | Where @port | Upstream equivalent @up |
| --- | --- | --- | --- | --- |
| A1 | State sub-mappers `applyBufferState`, `applyCdngLogState`, `applyClipNameState`, `applyRecordingDroppedFrames` (private, take the JSON object) | Map one feature's keys; callable from `applyCoreState`, from an event branch and from a reply | `B.cpp:660-684`, `:2652-2801`; called `:640`, `:1346-1347`, `:1457`, `:1732-1734` | One function maps every key inline, `applyCoreState` `B.cpp:1261-1555`; one small `set<Name>Value` setter per property does compare, assign, emit, `B.cpp:2230-2460`. No sub-mapper exists |
| A2 | `setControlsStatus(object, errorsKey, warningsKey)` | One setter for the same two counts under two key spellings (event `errors` / `warnings`, state `controls_errors` / `controls_warnings`) | `B.cpp:1424-1435`; calls `:1333`, `:1439` | Events that carry state keys are passed whole to `applyCoreState(message)`: `standby`, `still_exposure`, `timelapse_progress`, `media_write_state` `B.cpp:1191-1195`; `recording_health` `:1213-1216`. No setter takes key names |
| A3 | Relay signal `coreMediaStateChanged(state, alive)` to another bridge | Hand Core's media state to `MediaStatusBridge` | `B.cpp:1415-1422`, `B.hpp:268`, `src/main.cpp:318-319` | Cross-bridge wiring in `main.cpp`: a lambda on a NOTIFY signal that reads the property, `standbyChanged` -> `sleepManager.setStandby(...)` `src/main.cpp:333-343`; or signal to slot, `externalRecordingPreparationRequested` -> `AudioMeterBridge::releaseInputForRecording` `:324-327`. `MediaStatusBridge` also talks to Core on its own socket (`src/MediaStatusBridge.cpp:23`) |
| A4 | Third poll tier `kLiveValuePollIntervalMs` | Keep the gain / Kelvin in use current on screen | `B.cpp:19-20`, `:1014-1016`, `:1621` | Two tiers only: 1 s while disconnected, 30 s steady, `B.cpp:17-18`, `:875-882`. Live values come as events (`audio_level`, `B.cpp:1196-1199`) |
| A5 | "Value in use" and "set by camera" display state (`isoInUse`, `whiteBalanceInUse`, `*SetByCamera`), one group signal `cameraSetValuesChanged` for 8 properties | Show what the camera does beside what the operator chose | `B.cpp:1582-1622`, `B.hpp:19-27` | Auto shows the text "Auto": `setIso("Auto")` `B.cpp:1371-1372`, `setWhiteBalance("Auto")` `:1387-1388`. Group NOTIFY exists: `recordingCapabilitiesChanged` for 6 properties `B.hpp:34-39`, `exposureCompensationChanged` for 3 `B.hpp:22-24`. The in-use / camera-set concept: none |
| A6 | Presence-latched flags `storagePrerollAutoKnown`, `clipNameKnown`, empty `bufferSetting` | Hide a control until Core has sent its field ("older Core never does") | `B.cpp:670-673`, `:2746-2749`, `:2676-2684`; `B.hpp:417`, `:422`, `:430-434` | Capability flags that Core sends: `recording_capabilities` object `B.cpp:1286-1304`, `wb_available` `:1360-1366`, `exposure_compensation_available` `:1331`. No "key was absent" latch |
| A7 | String-or-number tolerant scalar parsing (`raw.isString() ? ... : ...`, lambda `asBool`) | Accept `"true"` / `"1"` / `"on"` strings as well as JSON bools and numbers | `B.cpp:2693-2694`, `:2702-2703`, `:2710-2713`, `:2727-2730`, `:2737-2741`, `:2752-2753`, `:2772-2778`, `:2781-2782` | Typed accessors with a default: `.toBool(m_isoAuto)` `B.cpp:1325`, `.toDouble(...)` `:1330`, `.toInt()` `:1396`. `isString()` is used only in `src/SettingsBridge.cpp:22`, `:59`, `:67` for preset JSON |
| A8 | `target` selector on one invokable (`ui` / `files` / `both`) plus `fileTimecodeMode` | Split one setting into a screen value and a file value | `B.cpp:750-771`, `:1698-1708`, `B.hpp:21`, `:202-203` | One timecode mode, mirrored into `UI.conf`: `B.cpp:622-636`, `:1466-1473` |
| A9 | `void` invokables | Send a command, let the reply or an event bring the state back | `B.hpp:194-198`, `:200` | Every `apply*` returns `bool` and follows: validate, `sendCoreCommand`, set the local property, `saveCurrentCameraSettings`, `return true` (`applyIso` `B.cpp:291-316`). Upstream's only `void` invokables are `notifyUserActivity` and `refresh` (`B.hpp:100`, `:110`) |
| A10 | One-shot operator message signal `bufferSafetyStopped(message)`, text composed in the bridge | Dialog after a safety stop | `B.cpp:2717-2723`, `B.hpp:277` | Same shape exists: `gyroCalibrationFinished(ok, message)` with the text built in the bridge `B.cpp:846-851`; `recordingFailed(error)` `:1208` |

No new class, namespace, header-only module, worker thread or helper script in this unit.

## 11. Removed, narrowed or hidden (things upstream had)

| # | What | Where | Effect |
| --- | --- | --- | --- |
| R1 | One-argument `applyTimecodeMode(displayValue)` | `B.hpp:127`, `B.cpp:622` @up -> two arguments, `B.hpp:202-203` @port | A caller must name a target. The three QML call sites were changed (`qml/CameraPage.qml:1842`, `qml/SettingsPage.qml:4011`, `:4026` @port; upstream `qml/CameraPage.qml:1714`, `qml/SettingsPage.qml:3778`) |
| R2 | Bridge mirror of Core's `timecode_mode` into `UI.conf` `timecodeMode` | `B.cpp:1466-1473` @up -> `:1698-1708` @port | A timecode mode set in Core no longer rewrites the UI's `timecodeMode` through the bridge; only `fileTimecodeMode` (memory) follows. Core still writes the key itself for target `ui` and `both` (`Core:App:13294-13298` @port) |
| R3 | The timecode tap on the camera page changed the camera's timecode mode | upstream `qml/CameraPage.qml:1714` -> `:1837-1843` @port, sends target `ui` | The tap no longer changes the timecode written into clips and audio (QML unit; the mechanism is here) |
| R4 | `applyFps`: keep the shutter angle and save `camera/*` after every FPS change | `B.cpp:273-288` @up -> skipped by `B.cpp:279-280` @port | Not done in a speed-ramp camera take |
| R5 | 30 s steady-state `get_state` poll | `B.cpp:879-881` @up -> `:1014-1016` @port | 1 s while auto ISO or auto WB is on |
| R6 | Compression field enabled whenever not recording and raw compression is supported | upstream `qml/SettingsPage.qml:3257` -> `:3408-3409` @port | Also disabled while `ladderActive` (QML unit; property from here) |
| R7 | "Auto" always in the ISO list outside the lossless-limited mode | upstream `qml/CameraPage.qml:511-513` -> `:525-532` @port | No Auto in Clear HDR; values above `isoMax` greyed (QML unit; `isoMax` from here) |

## 12. Board assumptions

| What | Where |
| --- | --- |
| None found in this unit. The 380 added `.cpp` lines and 141 added `.hpp` lines contain no Pi model, core count, RP1, PCIe, gpiochip, I2C bus, RAM size, fan, device path or `/boot` reference (`grep -i` over the added lines; the only hits are the mode names `"ram"` / `"frames"`) | `B.cpp`, `B.hpp` @port |
| `bufferMode` / `bufferSetting` value `ram`: the bridge relays the string. How much RAM that needs is decided in Core | `B.cpp:686-701`, `:2667-2684` @port |
| Unchanged upstream texts "requires Raspberry Pi 5-class hardware" stay as they were | `B.cpp:439`, `:497`, `:520` @up |

## 13. Commits: what the message and the fork log record

| Commit | Date | Message "Tested:" | `fork-log.md` |
| --- | --- | --- | --- |
| `160898c` | 2026-10-26 | "pi build (see next run)" | `:236` fork-only, on GitHub; "built 22:55, tested" |
| `ec9f109` | 2026-10-27 | "host build of the whole UI with Qt 6.4.2 (QML compiled ahead of time). Not run on the Pi." | `:226` fork-only; "tested 2026-10-28 (C0022)" |
| `f1edf96` | 2026-10-28 | "desk only (built on the Pi next)" | `:225` fork-only; "tested 2026-10-28 (Patrik: works well)" |
| `ed0d7b5` | 2026-10-28 | "desk only (built on the Pi next)" | `:222` fork-only; "tested 2026-10-28 (Patrik)" |
| `7840438` | 2026-10-28 | "desk only (built on the Pi next)" | `:218` fork-only; "built 2026-10-28", no test recorded |
| `c716dec` | 2026-10-28 | "desk only (built on the Pi next)" | `:215` fork-only; "built 2026-10-28", no test recorded |
| `7029db1` | 2026-10-29 | "Pi build pending" | `:204` fork-only, "Pi only; building 2026-10-29, not tested" |
| `ea44bd7` | 2026-10-30 | "pi build, qmllint of the new chip; not seen on a touch screen" | `:214` fork-only, no test recorded |
| `841d0ed` | 2026-10-31 | "not compiled or run here (the Mac cannot build the UI); the whole branch compiles on the Pi; identifiers were checked by grep. Not yet seen on the screen." Squashed from 7 commits | `:240` "offer (with the Core commit)"; "Not compiled on the Mac; compiles on the Pi" |
| `606f137` | 2026-11-01 | no "Tested:" line | `:240` "untested by hand" |
| `68e1a41` | 2026-11-01 | "desk only (needs Core's recording_dropped_frames)" | `:241` fork-only; on GitHub `drop-frames` and the Pi; "was 57b8e43 before a build fix"; no test recorded |

Messages and the log are intent only. Checked here: the unit compiles on x86_64 with Qt 6.4.2 (section 0). Nothing was run.

## 14. Comments that carry internal vocabulary

| Text | Where @port |
| --- | --- |
| "(T31)" | `B.cpp:275`, `B.hpp:435` |
| "(KB trap 7)" | `B.cpp:2666` |
| "T45:" | `B.hpp:82` |
| "CineMate Log" | `B.hpp:424` |
| "shown green" (QML shows italics since `35b31f6`: `qml/TopDropdownStat.qml:39`, `:114`, `qml/ExternalMonitorWindow.qml:902`) | `B.cpp:1582`, `B.hpp:18` |

## 15. Facts for the later stages (recorded, not judged)

| # | Fact | Evidence @port | Label |
| --- | --- | --- | --- |
| O1 | A reply is applied twice in `applyClipNameTemplate`. `sendCoreCommand` gives every line, the reply included, to `applyCoreMessage` (`B.cpp:1210`); a message with `ok` goes to `applyCoreState` (`:1411-1412`), which calls `applyClipNameState` (`:1734`); then the invokable calls `applyClipNameState(reply)` again (`:640`) | lines cited | confirmed |
| O2 | `applyBufferMode` sets `m_bufferSetting` (`:697-700`) after the reply already brought `buffer_setting` (reply carries `bufferSettingMembers()`, `Core:App:12851-12852`). `applyCdngLog` sets `m_cdngLogOn` (`:723-726`) after the reply's `cdng_log` was applied the same way | lines cited | confirmed |
| O3 | `shutterSetByCamera` reads `m_recording` at `B.cpp:1610` before `setRecordingState` runs at `:1730-1731` in the same pass; in the `recording` event branch `applyCoreState(message)` (`:1352`) runs before `setRecordingState` (`:1357`) | order read in code | confirmed order; effect on screen unconfirmed (needs a ramp take on the Pi) |
| O4 | `updateRefreshTimer()` now runs on every `applyCoreState` pass (`B.cpp:1621`) and calls `QTimer::setInterval` on the running timer (`:1014`) | lines cited | call confirmed; "setInterval restarts a running timer" probable (Qt documents that the timer id changes); settle by reading `QTimer::setInterval` in Qt 6.4.2 `qtimer.cpp`, not on this machine |
| O5 | The tolerant parsing cites "KB trap 7". That trap is about Core's request parser. Core emits these fields as JSON numbers and bools | `Core:App:256-264`, `:306-307`; `apertar-kb/llm/README.md:126` | confirmed |
| O6 | `"Lock"` is compared exactly (`B.cpp:303`); `"Auto"` goes through `isAutoSelection` (trimmed, case-insensitive, `:22-25`) | lines cited | confirmed |
| O7 | The same value has different key names in the event and in the state: `mounted` vs `media_alive`; `errors` / `warnings` vs `controls_errors` / `controls_warnings` | `Core:App:10828` vs `:9556`; `:12347` vs `:9458-9459` | confirmed |
| O8 | The monitor-only process creates its own bridge and no `MediaStatusBridge`; `coreMediaStateChanged` is not connected there | `src/main.cpp:131-155` | confirmed |
| O9 | `setControlsStatus` is declared among the data members, not with the private functions | `B.hpp:453` (data members start at `:373`) vs the private functions at `:292-371` | confirmed |
| O10 | The comment at `B.cpp:19` says the value in use is carried only by `get_state`. Core also puts `iso_actual` in `settingsBody` and in the `settings` event | `Core:App:323`, `Core:CC:175` | emitters confirmed; whether a `settings` event fires when the measured gain moves: unconfirmed (read the callers of the `settings` event emitter in `Core:CC`, found with `grep -n 'settings' Core:CC \| grep event`) |
| O11 | New commands get the 3000 ms reply timeout | `B.cpp:1151-1167` | confirmed |
| O12 | The bridge has grown further on another branch: `origin/clip-split` is 20 commits past `cinemate-port`, +215 / -2 in `B.cpp`, +88 in `B.hpp` (fork log: `framesPerFolder`, `clipMergeEnabled`, `applyFramesPerFolder`, `applyClipMerge`, `clip_merge_*`) | `git log cinemate-port..origin/clip-split`; `fork-log.md:206-210` | confirmed; outside this review's diff |

## 16. Cross-reference for the owner's request to reinsert the GPIO chip definition (outside this unit)

| Fact | Evidence | Label |
| --- | --- | --- |
| This unit has no GPIO or chip code. It carries only the two counts of Core's hardware-file check; the touch UI's Controls card is read-only and points to the WebUI | `grep -i -E 'gpio\|chip' B.cpp B.hpp` @port: no hit; `B.cpp:1424-1439`; `qml/SettingsPage.qml:6455-6478` | confirmed |
| Upstream's UI wrote a first-run `apertar-hardware.conf` with `gpiochip=auto` in `[trigger_output]` and `[recording_indicator]` and `chip=auto` in `[gpio_buttons]` and `[gpio_encoders]` | `src/DisplayConfigBridge.cpp:110`, `:123`, `:161`, `:172` and `src/Ina219Bridge.cpp:129`, `:142`, `:180`, `:191` @up | confirmed |
| The port removed those templates: all 8 chip lines go in `c9d841f` ("stop writing a default hardware file when it is missing"). The port UI tree has no `gpiochip` / `chip=auto` text left | `git show c9d841f` (8 removed, 0 added); `grep -rn -i -E 'gpiochip\|chip *= *auto' src qml` @port: no hit | confirmed |
| Core's hardware classes still parse the key at the port | `Apertar-Core/src/hardware/TriggerOutput.cpp:305`, `GpioInput.cpp:343`, `RecordingIndicatorOutput.cpp:312`, `:340`; alias in `hardware/HardwareConfigText.hpp:172` @port | confirmed |
| Where the port's Controls editor (WebUI, Core config store) shows, hides or drops the chip key | not read here; belongs to the Core and WebUI units | unconfirmed |

## 17. Not covered here

- QML rendering and layout of the elements in section 8 (units UI-CameraPage, UI-SettingsPage and the other QML files).
- `SettingsBridge`, `MediaStatusBridge`, `DisplayConfigBridge`, `Ina219Bridge`, `SystemActionBridge` beyond the lines cited.
- Core behaviour behind the commands in section 3 beyond argument names and reply keys.
- No runtime check: no Pi, no Core process, no touch screen.
