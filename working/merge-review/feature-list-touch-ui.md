# Feature list: Touch UI and HDMI monitor

Area: what the cinemate port added to the Qt 6 / QML touch UI and the HDMI monitor window of original Apertar 1.6.0 (`Apertar-UI`).
Sources: inventories UI-bridges, UI-control-bridge, UI-settings-qml, UI-camera-qml, `raw/FEATURES.json`, `fork-log.md`, commit messages. Names of properties, keys, commands and env vars were re-checked by grep in `/home/user/Apertar-UI` @cinemate-port `7ea9afc` and `/home/user/Apertar-Core` @cinemate-port `01f170c`.

"Stock camera" = a camera running `cinemate-port` with no config edits. Already done on the improvement branch (`/home/user/wt/core-work`), do not list as open: the GPIO chip setting is back on the Controls page and its checks are per chip (`04fe197`). Nothing else in this area is fixed yet.

Relation words: extends in place / beside upstream / replaces upstream / new area. "Desk" = built or read, no screen. "Pi" = run on the camera. Every "tested" below is what the commit message or fork-log says, not proof (BRIEF rule 5). Property names are from `ApertarControlBridge.hpp` and `SettingsBridge.hpp`.

## Table

| # | Feature | Default for a stock camera | Relation to 1.6.0 | Tested |
| --- | --- | --- | --- | --- |
| 1 | Pickers from the operator's value lists, greyed above the mode ceiling (FPS, ISO, shutter angle, WB) | on; built-in lists unless `UI.conf` has steps; ceiling greying on | replaces the hard-coded lists | Patrik 2026-10-28 (4 of 5 commits); `682a186` built only |
| 2 | Values the camera decides: value in use, italics, ISO Lock | on | extends in place + new display convention | `f1edf96` Patrik 2026-10-28; `7840438`, `35b31f6` built only |
| 3 | Recording indicators: red frame, red timecode, audio outline (touch and HDMI) | frame off, red timecode on, outline on | extends in place | frame and red timecode Patrik 2026-10-28; outline not recorded |
| 4 | Status pill: write-buffer bar, safety-stop drain, blue PRE-ROLL, "Recording Stopped" dialog | pill states appear when Core reports them; bar switch off | extends in place + new area | none: "not yet seen on the screen" |
| 5 | Raw readout: bit depth and Clear HDR on the resolution line, Log marker, time left from stored bits | on | extends in place | Patrik 2026-10-27/28 (3 of 5 commits) |
| 6 | Preview cap while recording (`APERTAR_UI_PREVIEW_RECORDING_FPS`) | off (env var unset) | beside upstream | Pi, hardware log only |

Left to other areas (one line each at the end).

## 1. Pickers from the operator's value lists, greyed above the mode ceiling

- **Operator gets:** the FPS, ISO, shutter-angle and white-balance pickers list the operator's own steps, grey (not tappable) every value above the ceiling Core reports for the current mode, and add the ceiling itself in italics when it is not in the list. Auto ISO is not offered in Clear HDR.
- **How used:** open any of the four stats on the camera page. The lists come from `UI.conf` (edited on the WebUI Value Lists card); the touch UI only reads them. HDMI shows the values, it has no pickers.
- **Commands / routes:** none new. `get_state` fields read: `fps_max`, `iso_max` (`ApertarControlBridge.cpp:1591-1594`). Core side: `set_value_steps` (`App:14110`) writes the lists.
- **State fields / properties:** `fps_max` -> `fpsMax`, `iso_max` -> `isoMax`; `SettingsBridge` read-only lists `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles`, `mainsHz`. An option is now a string or `{value, enabled, cameraSet}` (`TopDropdownStat.qml:99-104`).
- **Config keys:** `UI.conf [General]` `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles` (default false), `mainsHz` (default 50). Read in `SettingsBridge::reloadValueSteps` (`SettingsBridge.cpp:1780-1785`). Env vars: none.
- **Touches in 1.6.0:** `CameraPage.qml` `shutterOptions`, `isoOptions`, `availableFpsOptions` and the fixed WB list are rewritten as computed entries through new `valueSteps`, `cappedValueEntries`, `shutterAngleEntries`, `fpsCeiling`, `fpsOptionEntries` (`CameraPage.qml:848-938`); `TopDropdownStat` options change from plain strings to objects; `SettingsBridge` constructor and `pollExternalSettings` gain a reload. The IMX585 lossless 30 fps cap leaves QML and is read from Core's `fps_max`. Relation: replaces upstream lists.
- **Needs:** a Core of the same build that sends `fps_max` and `iso_max` (camera-modes list item 7). With an older Core the QML fallbacks apply: ISO 100-1600 and no FPS cap.
- **Tested:** `ed0d7b5` "desk only (built on the Pi next)", fork-log:222 tested 2026-10-28 (Patrik); `b4591dc` and `d1efb67` tested (Patrik); `682a186` built 2026-10-28 only.
- **Commits:** `ed0d7b5` `f1edf96` `682a186` `b4591dc` `d1efb67`.
- **For development:** to add a picker value, edit the list builder, not an options array; a plain string option still works. The same ceiling rule exists in Core (`App:1408`, `App:1573`) and in QML (`maximumSupportedFpsForResolution`, IMX585 4K Clear HDR 16-bit = 25 fps in `CameraPage.qml:822`); change both.

## 2. Values the camera decides: value in use, italics, ISO Lock

- **Operator gets:** with auto ISO or auto WB, the stat shows the gain or Kelvin the camera uses; a value Core holds or caps (Clear HDR hold, ramp-driven shutter) is shown in italics on the touch screen and the HDMI info row. An ISO "Lock" entry freezes auto ISO at the gain in use.
- **How used:** open the ISO picker while ISO is Auto and tap Lock. Italics appear on their own.
- **Commands / routes:** `set_iso_auto` with a new argument `enabled=false` (`ApertarControlBridge.cpp:304`; Core handler `App:12995`; upstream handler took no argument). `get_state` is polled every 1 s while auto ISO or auto WB is on, otherwise at the slow rate (`kLiveValuePollIntervalMs` / `kSteadyStatePollIntervalMs`, `ApertarControlBridge.cpp:1016`).
- **State fields / properties:** `iso_actual`, `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr`, `fps_speed_ramp_keep_exposure`, `wb_actual_kelvin`, `wb_measured` (the last two exist in upstream Core, the UI newly reads them); properties `isoInUse`, `whiteBalanceInUse`, `isoSetByCamera`, `whiteBalanceSetByCamera`, `shutterSetByCamera`; `TopDropdownStat.displayValue` and `valueItalic`. Config keys, env vars: none.
- **Touches in 1.6.0:** `applyCoreState` (a 41-line block), `applyIso` (new first branch for "Lock"), `updateRefreshTimer` (third interval), `TopDropdownStat.qml`, `CameraPage.qml` stats, HDMI info items in `ExternalMonitorWindow.qml`. Relation: extends in place; the "set by camera" display convention has no upstream counterpart.
- **Needs:** Core of the same build (camera-modes list item 9 owns the Core side).
- **Tested:** `f1edf96` "desk only", fork-log:225 tested 2026-10-28 (Patrik: works well); `7840438` and `35b31f6` built 2026-10-28, no test recorded. The colour changed green -> white -> italic over three commits; bridge comments still say "shown green".
- **Commits:** `f1edf96` `7840438` `35b31f6`.
- **For development:** a new camera-decided value must set both a `...SetByCamera` property in the bridge and `cameraSet` in the HDMI info item; the two windows do not share a component. The 1 s poll is the only live source for ISO and WB in use; an event would replace it.

## 3. Recording indicators: red frame, red timecode, audio outline

- **Operator gets:** during a take the screen edge can show a red frame (default off), the timecode turns red (default on), the audio meter gets a faint red outline when sound is recorded (default on); same on HDMI. Each has a switch in Settings > Monitoring. The HDMI timecode was always white in 1.6.0 and is now red during a take by default.
- **How used:** Settings > Monitoring, rows Recording Frame, Red Timecode, Audio Recording Outline (`SettingsPage.qml:2937-2997`).
- **Commands / routes:** none from the UI. Core mirrors the switches for the WebUI through `handleUiToggle` (controls-system list item 19).
- **State fields / properties:** `SettingsBridge` `recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`; also in the preset JSON.
- **Config keys:** `UI.conf [General]` `recordingFrameEnabled` (false), `recordingRedTimecodeEnabled` (true), `audioRecordedOutlineEnabled` (true) (`SettingsBridge.cpp:368-371`). Env vars: none.
- **Touches in 1.6.0:** the `SettingsBridge` property/load/poll/setter/preset chain, same shape as `dateTimeOverlayEnabled`; Monitoring rows in `SettingsPage.qml`; red frame `CameraPage.qml:4347` and `ExternalMonitorWindow.qml:1434`; red timecode `CameraPage.qml:3924`, `ExternalMonitorWindow.qml:1208`; outline in `AudioMeterOverlay.qml`. Relation: extends in place, in upstream's shape.
- **Needs:** nothing.
- **Tested:** `da2a9b5` fork-log:219 tested 2026-10-28 (Patrik). `5697b54` and `e061be8` (outline): no test line, no fork-log row.
- **Commits:** `da2a9b5` `5697b54` `e061be8`.
- **For development:** these three follow upstream's pattern exactly; a fourth switch is a copy of any of them. The WebUI and Core keep their own copy of the same switches (webui list item 5); a new switch needs both sides.

## 4. Status pill: write-buffer bar, safety-stop drain, blue PRE-ROLL, dialog

- **Operator gets:** an optional bar inside the REC pill shows the write-buffer level. When Core ends a take at its buffer limit the pill turns READY green while the bar empties, the record button can start a new take during the flush, and a dialog says the clip is complete. A blue PRE-ROLL pill and the pre-roll frame rate (in italics on the FPS stat) show while Core runs the storage pre-roll. Same on HDMI.
- **How used:** Settings > Monitoring > Frame Buffer Bar switch (the pill states need no setting).
- **Commands / routes:** none new from the display. Core events read: `buffer` (new, `App` buffer event), plus `get_state` fields below. The buttons that set buffer mode, Log and pre-roll are in the recording list (not here).
- **State fields / properties:** `buffer_fill`, `buffer_mode`, `buffer_safety_stop`, `buffer_stop_percent`, `storage_preroll_active`, `storage_preroll_fps` -> `bufferFill`, `bufferMode`, `bufferSafetyStop`, `storagePrerollActive`, `storagePrerollFps`; signal `bufferSafetyStopped(message)`; derived `bufferFlushing`, `pillRecordingActive`, `prerollOnly`, `drainOnly`. `bufferStopPercent` has no QML reader.
- **Config keys:** `UI.conf [General] frameBufferBarEnabled` (default false). Env vars: none.
- **Touches in 1.6.0:** `StatusChip.qml` (bar, PRE-ROLL label, drain state), the HDMI pill in `ExternalMonitorWindow.qml:157-203,1105-1126`, `CameraPage.qml` record button and `Connections` (`:578`, `:1956-1967`, `:2694`, `:3951-3990`). Relation: extends in place; the derived pill states are a new area beside Core's recording flag. The bar and pill logic are written twice (touch chip, HDMI inline rectangle), because the HDMI pill is already a separate rectangle upstream.
- **Needs:** Core of the same build; RAM buffer mode for a safety stop to occur (recording list items 12, 13). Pre-roll is on automatically in the port, so a stock camera can show the blue pill (recording list item 13).
- **Tested:** none. `841d0ed` "not compiled or run here ... Not yet seen on the screen"; fork-log:240 "compiles on the Pi". `4959513` and `96a7aa4` have no test line.
- **Commits:** `841d0ed` `4959513` `96a7aa4`.
- **For development:** the pill label is a priority chain (PRE-ROLL, REC, WRITING, READY, drain); read `StatusChip.qml:55-60` and the HDMI copy before adding a state, and change both. Core's recording flag stays true during a flush; the UI hides it with `bufferFlushing`.

## 5. Raw readout: resolution line, Log marker, time left

- **Operator gets:** the resolution line reads `3840x2160 . 16-bit . Clear HDR` for raw takes; the format sub-text adds `. Log` when Log is applied; minutes left follow the stored bit depth (16-bit counted as 16, Log bits when Log is applied). In 4K Clear HDR 16-bit the FPS list stops at 25.
- **How used:** nothing to do; it is the camera page format box and the HDMI RESOLUTION and format values.
- **Commands / routes:** none. Reads `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` (derived `cdngLogActive`, `cdngLogBits`) and `rawBitDepth`, `clearHdr`.
- **Config keys, env vars:** none.
- **Touches in 1.6.0:** `formatDisplayValue`, `formatDisplaySubtext`, `currentRawBitDepthNumber`, `estimatedFrameSizeMB`, `maximumSupportedFpsForResolution` in `CameraPage.qml` (`:547-553`, `:705-712`, `:822`, `:1014`) and the HDMI format values. Relation: extends in place.
- **Needs:** Core of the same build for the Log fields.
- **Tested:** `1367b7f`, `1a691a9`, `2d27c46` Patrik 2026-10-27/28 (fork-log:221, 224, 234; the HDMI time-left estimate was a third too long before `2d27c46`); `d1efb67` Patrik; `2475626` was reverted by `1a691a9`; the Log part in `841d0ed` untested.
- **Commits:** `1367b7f` `2475626` `1a691a9` `2d27c46` `d1efb67` `841d0ed`.
- **For development:** the frame-size estimate is a second copy of Core's model (`estimatedRawBytesPerSecond`); a new bit depth or mode needs a change here and in Core. `2475626` and `1a691a9` cancel; read the net diff.

## 6. Preview cap while recording

- **Operator gets:** nothing by default. With `APERTAR_UI_PREVIEW_RECORDING_FPS=N` the touch UI draws at most N preview frames a second during a take (0 holds the last frame), to test whether preview work causes capture losses. With the cap set, the on-screen Rec Run timecode counts only shown frames.
- **How used:** set the env var in the UI's service environment; a log line names the cap at start.
- **Commands / routes, state fields, config keys:** none. Env var: `APERTAR_UI_PREVIEW_RECORDING_FPS` (`ApertarPreviewSocketClient.cpp:29`).
- **Touches in 1.6.0:** `ApertarPreviewSocketClient` gets `setRecording` and a frame throttle (`.cpp:25-43,488-498`); one wiring line in `main.cpp:351-352`. Upstream hands every frame to the renderer. Relation: beside upstream, off unless set. Upstream's UI env knobs (`APERTAR_PREVIEW_FORCE_CPU`, `_PLANAR`, `_EGL`, `PreviewWindowRenderer.cpp:296-301`) are the precedent.
- **Needs:** nothing.
- **Tested:** `c234d77` "desk only"; used on the Pi with `=12` and `=0` (`lessons/hardware-log.md:992-993`, fork-log:242).
- **Commits:** `c234d77`.
- **For development:** a measuring knob, not a product feature; decide whether it stays before the merge. It is the UI twin of the web preview cap in the recording list (item 21).

## Left to other areas

| Feature seen in the touch UI | Main home |
| --- | --- |
| Write Buffer Frames / RAM, Log On/Off, Storage Pre-roll button and Auto switch (Settings > Record and Media Speed), dropped-frame count chip, media state from Core (NO MEDIA), speed-ramp FPS picker, automounter release of a pulled card | recording list, items 1, 6, 9, 11, 12, 13 |
| Clip Names card (`ClipNameCard.qml` 601 lines, `ClipNamePill.qml`; keeps a QML copy of Core's token list, reuses the preset popup through `presetPopupPurpose`) | recording list item 10 and webui item 4 |
| UI timecode and File timecode (Time of Day / Clip), `set_timecode_mode target=` | controls-system item 20 and webui item 8 |
| Controls chip and Settings > Info Controls card (`ControlsWarning.qml` is in `CMakeLists.txt:41` but not in `qml.qrc`) | controls-system item 2 |
| Mode Ladder indicator on Compression (`ladder_active`) | camera-modes item 1 |
| Fan mode through Core's `set_fan_mode` | controls-system item 16 |
| No default hardware file from the UI, HDMI 1080p display fallback (`hdmi_external_only` true when missing, touch window hidden) | controls-system item 13 |
| Value Lists writer (`set_value_steps`) and `UI.conf` lists | controls-system item 18 |
