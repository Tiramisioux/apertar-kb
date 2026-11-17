# Fix list: Touch UI, bridges and QML

Editor's list for the merge review of the cinemate port. Domain: `Apertar-UI` C++ bridges (`src/*.cpp`) and QML (`qml/*.qml`), units UI-bridges, UI-control-bridge, UI-settings-qml, UI-camera-qml, plus the findings of the sweeps stock-behaviour, state-consistency, board-support, protocol-security and commits-ui-drivers that lie in UI files or UI subject. Port refs: UI `cinemate-port` `7ea9afc`, Core `01f170c`. Upstream: `/home/user/wt/ui-upstream`, `/home/user/wt/core-upstream` (`upstream-1.6.0`). Yardstick: `apertar-conventions.md` (rule ids UIC-, QML-, CMD-, STY-). Abbreviations: `ACB` = `src/ApertarControlBridge.cpp`, `SB` = `src/SettingsBridge.cpp`, `CPg` = `qml/CameraPage.qml`, `SP` = `qml/SettingsPage.qml`, `EMW` = `qml/ExternalMonitorWindow.qml`.

## Already done on the improvement branch

Not listed as open. Worktrees `/home/user/wt/ui-work`, `/home/user/wt/core-work`.

| Commit | What | Findings closed |
| --- | --- | --- |
| Core `04fe197` | GPIO chip is a Controls setting again, checks per chip (the touch UI's `ControlsWarning` no longer fires for a file upstream accepts) | X-board-support-1, owner request 16 |
| UI `6a59d83`, Core `7dc6f7a` | Display fallback and Core template are 720x720 / square / `hdmi_external_only=false` again | UI-bridges-F1 (blocker), X-stock-behaviour-1, X-board-support-2 |
| UI `2d9cf94` | Audio meter red outline off by default (Core half: APP-19) | X-stock-behaviour-13 |
| UI `ac1fc28` | HDMI timecode stays white until red timecode is set in UI.conf | UI-camera-qml-F7, X-stock-behaviour-12 |

## Summary

| Id | Title | Kind | Sev | Effort | Rec |
| --- | --- | --- | --- | --- | --- |
| UI-1 | Timecode tap and Settings "Mode" no longer set the files' timecode; upstream names gone | stock | major | M | fix-now |
| UI-2 | Safety-stop flush shows READY while Core still writes the take | bug | major | S | fix-now |
| UI-3 | Touch-UI presets omit every camera setting the port added | removed | major | M | fix-now |
| UI-4 | Nothing writes the first-run apertar-hardware.conf (UI writers deleted) | removed | major | M | ask-owner |
| UI-5 | Touch-UI IMX585 resolution and FPS lists lag Core's tables | mismatch | major | M | fix-now |
| UI-6 | New command invokables return void, send on/off and auto/off, apply a reply twice | mismatch | major | S | fix-now |
| UI-7 | ActionTiles with flipping accent tone used as radio buttons; hand-sized sub-labels | mismatch | major | M | fix-now |
| UI-8 | ClipNameCard: drag-and-drop composer with a hand-placed ghost, untested on touch | new-ground | major | M | ask-owner |
| UI-9 | UI commit series: experiments, churn, ticket numbers, and Core pairs | commit | major | M | fix-later |
| UI-10 | Clip-name card loses an edit at record start and drops unknown tokens | bug | minor | S | fix-now |
| UI-11 | Second state path: controls/media/buffer event branches and a key-name setter | mismatch | minor | M | fix-now |
| UI-12 | Full get_state poll every second while auto ISO or auto WB is on | mismatch | minor | M | fix-now |
| UI-13 | Storage pre-roll inside the Media Speed card; presence latches hide pre-roll and Clip Names | mismatch | minor | S | fix-now |
| UI-14 | ISO Auto offered in lossless modes where Core turns it off | stock | minor | S | fix-now |
| UI-15 | Fallback ceilings: dead ISO fallback, empty FPS block, edited 25 fps cap | slop | minor | S | fix-now |
| UI-16 | APERTAR_UI_PREVIEW_RECORDING_FPS experiment knob kept, and it stalls the Rec Run timecode | knob | minor | S | fix-now |
| UI-17 | ControlsWarning.qml missing from qml.qrc (non-AOT builds) | bug | minor | S | fix-now |
| UI-18 | New Settings items skip icon and favourite registration | mismatch | minor | S | fix-now |
| UI-19 | Settings text states Core settings as fixed values | bug | minor | S | fix-now |
| UI-20 | Ticket ids, names, dates, "CineMate" and stale "green" in comments; missing include | slop | minor | S | fix-now |
| UI-21 | Buffer bar written twice (StatusChip and HDMI pill) | duplication | minor | S | fix-now |
| UI-22 | HDMI window copies of ISO cap, raw-format test and fps formatting drift from CameraPage | duplication | minor | S | fix-later |
| UI-23 | Touch picker and FPS buttons ignore fps_take_max during a ladder take | bug | minor | S | fix-later |
| UI-24 | Core media override never cleared when Core goes away | bug | minor | S | fix-later |
| UI-25 | shutterSetByCamera reads m_recording before the recording state is set | bug | minor | S | fix-later |
| UI-26 | String-or-number tolerant parsing for typed Core fields | slop | minor | S | fix-later |
| UI-27 | Fan mode from the touch UI goes through Core's set_fan_mode | new-ground | nit | S | keep-and-document |

---

## UI-1. Timecode tap and Settings "Mode" no longer set the files' timecode; upstream names gone

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | M | yes | fix-now | UI-control-bridge-F5, UI-settings-qml-F2, UI-settings-qml-F10, UI-bridges-F7, X-stock-behaviour-8, X-protocol-security-4 |

**Where.** `src/ApertarControlBridge.cpp:750-771`, `src/ApertarControlBridge.hpp:202-203`, `qml/CameraPage.qml:1837-1843`, `qml/SettingsPage.qml:3998-4029` (and `timecodeChoices`, `timecodeDisplayName`), all @cinemate-port; Core `src/ApertarCoreApp.cpp:13279-13299@cinemate-port`.

**Problem.** `applyTimecodeMode(displayValue, target)` has a required `target` (ui|files|both). The camera-screen tap and the first Settings dropdown (relabelled "UI timecode") send `"ui"`, which Core applies to the screens only; a new "File timecode" dropdown sends `"files"`. A stock camera after the merge: the operator taps to Rec Run, sees Rec Run, and every DNG, MLV, ProRes, H.264 and WAV keeps Free Run (confirmed in code). The options are shown as "Time of Day" / "Clip", so the original developer's terms "Mode", "Free Run", "Rec Run" disappear. UI.conf `timecodeMode` is written three times (QML `settingsState.timecodeMode`, the bridge, Core).

**Apertar way.** `bool applyTimecodeMode(const QString &displayValue)` sends `set_timecode_mode value=...` and Core sets camera and UI.conf together (`src/ApertarControlBridge.cpp:622-636@upstream-1.6.0`; Core `src/ApertarCoreApp.cpp:9424-9437@upstream-1.6.0`, rule CMD-26). The tap toggles both (`qml/CameraPage.qml:1709-1715@upstream-1.6.0`). Settings: one `InlineDropdownField` label "Mode", options `["Free Run", "Rec Run"]` (`qml/SettingsPage.qml:3753-3782@upstream-1.6.0`). UI-only values are written by plain assignment (QML-7); `apply<Thing>(displayValue)` naming (UIC-10).

**Rework.**
1. `ApertarControlBridge.hpp/.cpp`: restore `Q_INVOKABLE bool applyTimecodeMode(const QString &displayValue)` with the upstream body (send `value` only, no `target`; port Core reads a missing target as both). Delete the `target` parameter and its validation. After the send, set `m_fileTimecodeMode` from the reply's `timecode_mode` (through the same code as `applyCoreState` :1698-1705), not from an argument.
2. `CPg` `toggleTimecodeMode()`: call `applyTimecodeMode(nextMode)`; keep the `settingsState.timecodeMode` assignment, which upstream has too (`qml/CameraPage.qml:1709-1715@upstream-1.6.0`). The function is then byte-identical to upstream. In `ACB::applyTimecodeMode` keep the upstream UI.conf write as upstream has it.
3. `SP` timecode card: restore the upstream dropdown verbatim (label "Mode", `["Free Run", "Rec Run"]`, `applyTimecodeMode(v)`). Delete `timecodeChoices` and `timecodeDisplayName`; put any clearer wording into the card `description`.
4. Only if the owner keeps a separate file timecode (owner decision): add `bool applyFileTimecodeMode(const QString &displayValue)` that sends `target="files"`, and a second dropdown "Files" whose first option "Same as Mode" sends nothing, so the default behaves as 1.6.0. A screen-only change is then `settingsState.timecodeMode = v` with no Core call.
5. Core side stays as APP-45 (keep-and-document): `target` is optional and defaults to both.

**Owner decision.** Keep a separate file timecode at all? Recommendation: no for the merge; restore 1.6.0 (one mode for screens and files). Cost of "no": the Rec Run-continues-from-previous-clip use case moves to a later, separate PR. Cost of "yes": step 4 (one more invokable and dropdown, default "Same as Mode") and a handoff paragraph naming the exception to CMD-26.

**Check here.** `check_ui.sh /home/user/wt/ui-work ui-work`; `grep -n 'applyTimecodeMode' qml/*.qml` shows only one-argument calls; Core `--simulate`: `set_timecode_mode value=rec_run` with no target changes `timecode_mode` and UI.conf.

**Needs the Pi.** Tap the timecode to Rec Run, record 10 s: the DNG/WAV timecode starts at the Rec Run value (`exiftool -TimeCodes` on a frame, `ffprobe` on the WAV bext).

---

## UI-2. Safety-stop flush shows READY while Core still writes the take

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | major | S | yes | fix-now | UI-camera-qml-F6 |

**Where.** `qml/StatusChip.qml:22, :55-62`, `qml/CameraPage.qml:578, :2694, :3953, :3896, :3924, :4093, :4347`, `qml/ExternalMonitorWindow.qml:157, :200, :1208, :1433`, all @cinemate-port; Core `src/ApertarCoreApp.cpp:11094-11110@cinemate-port`.

**Problem.** During a buffer safety stop Core keeps `recording` true while it drains the queue to the card. The port gates only the pill and the record button with `bufferFlushing`/`pillRecordingActive`, and explicitly suppresses WRITING: StatusChip `draining` ("a safety stop is not a take: READY green while the buffer empties", :56) and EMW :200 (`... mediaWritesPending && !bufferSafetyStop ? "WRITING" : "READY"`). Re-checked: so both screens show green READY while frames are still being written (confirmed in QML), while the red frame, red timecode and audio outline still show a take (they read `root.recording`). An operator who trusts READY and cuts power loses the tail of the take (probable).

**Apertar way.** Status words are fixed on both screens: REC red, WRITING amber while writes are pending, READY green only when idle (QML-28; `qml/StatusChip.qml:44-48@upstream-1.6.0`).

**Rework.**
1. `StatusChip.qml`: delete `draining` and its uses in the colour, label and width ternaries; a flush shows WRITING amber like any pending write. Keep `drainOnly` for the bar colour only.
2. `CPg`: add `readonly property bool takeActive: root.recording && !root.bufferFlushing` next to `bufferFlushing` (:578). Pass `writing: root.mediaWritesPending || root.bufferFlushing` to the chip. Use `takeActive` for pill, button, recording frame, timecode colour and audio outline.
3. `EMW`: rename `pillRecordingActive` to `takeActive`; at :200 drop `&& !apertarControlBridge.bufferSafetyStop` and add `|| bufferSafetyStop` to the WRITING test; use `takeActive` at :1208, :1433.
4. Record during the flush is REC-32's (Core discards queued frames); leave the button rule to that item.

**Owner decision.** None.

**Check here.** UI build; read the three ternaries; Core `--simulate` cannot force a safety stop, so the check is a code read.

**Needs the Pi.** Fill the buffer (slow card, 4K 16-bit) until the safety stop: both screens show WRITING amber until Core clears `recording`, then READY; frame and timecode return to idle colours at the stop.

---

## UI-3. Touch-UI presets omit every camera setting the port added

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | major | M | no | fix-now | X-state-consistency-1 |

**Where.** `src/ApertarControlBridge.cpp:1254-1286@cinemate-port` (`cameraPresetSettings`, byte-identical to fork main); `src/SettingsBridge.cpp:2203-2208@cinemate-port`; Core `src/ApertarCoreApp.cpp:7844-7862@cinemate-port` (`buildCurrentPresetPayload`).

**Problem.** The touch UI writes its own preset files from `cameraPresetSettings()`, which the port did not touch. Core's writer (WebUI save) adds `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter/Audio/After`, `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode`, `cameraClearHdr`, `cameraHdrThresholdHigh/Low`, `cameraHdrBlend`, `cameraHdrGainAdder`, `cameraCdngLog` (and `cameraConformFps`, deleted by CAM-18). A preset saved on the touch screen does not hold Clear HDR, Log, speed ramp, phase lock, file timecode or the clip-name template; loading it leaves the current values. The same preset saved from the WebUI restores them (confirmed). The Clear HDR keys were already missing in fork main.

**Apertar way.** Both preset writers carry the same `camera*` set (CMD-22); every UI setting is included in presets (UIC-13).

**Rework.**
1. `ApertarControlBridge.hpp`: add members for the fields `applyCoreState` does not keep yet: `m_fpsSpeedRampStretchAudio`, `m_fpsSpeedRampReturn`, `m_fpsPhaseLock`, `m_hdrThresholdHigh`, `m_hdrThresholdLow`, `m_hdrBlend`, `m_hdrGainAdder` (plain members, no Q_PROPERTY unless QML reads them).
2. `applyCoreState`: read them with `if (state.contains("fps_speed_ramp_stretch_audio")) m_... = state.value(...).toBool(m_...)` next to the existing `fps_speed_ramp` read (:1511), same for `fps_speed_ramp_return`, `fps_phase_lock`, `hdr_*`.
3. `cameraPresetSettings()`: insert the keys under Core's names and value words, after `cameraAutofocusWindowHeight`: `cameraFpsSpeedRamp`, `cameraFpsSpeedRampShutter` ("exposure"/"angle"), `cameraFpsSpeedRampAudio` ("stretch"/"real"), `cameraFpsSpeedRampAfter` ("return"/"stay"), `cameraClipNameTemplate`, `cameraFpsPhaseLock`, `cameraTimecodeMode` (`free_run`/`rec_run` from `m_fileTimecodeMode`), `cameraClearHdr`, `cameraHdrThresholdHigh/Low`, `cameraHdrBlend`, `cameraHdrGainAdder`, `cameraCdngLog`. Skip `cameraConformFps` (CAM-18).
4. Follow the answer to APP-47 for `preview_tdn` and `media_trim` (add to both writers or neither).

**Owner decision.** None here (APP-47 holds the TDN/trim question).

**Check here.** UI build; Core `--simulate` with the UI pointed at its socket (`APERTAR_CONTROL_SOCKET`): save a preset on the touch UI, `diff` its `camera*` keys against a WebUI-saved preset of the same state (only order may differ).

**Needs the Pi.** Save a preset with Clear HDR and Log on, switch both off, load it: both come back.

---

## UI-4. Nothing writes the first-run apertar-hardware.conf (UI writers deleted)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | major | M | yes | ask-owner | UI-bridges-F2, X-stock-behaviour-2 (same item as HW-9 and APP-16) |

**Where.** `src/DisplayConfigBridge.cpp:35-38`, `src/Ina219Bridge.cpp:63-66, :262-267` @cinemate-port (writers removed in UI `c9d841f`); Core `src/ApertarCoreApp.cpp:5081-5151, :6190-6202@cinemate-port`; Core `014fa22` (replaced-file check).

**Problem.** 1.6.0's UI writes a commented template when `/home/pi/apertar-hardware.conf` is missing. The port deleted both UI writers because a file moved away came back as the template and undid a fix. Now a fresh camera gets no file; the WebUI editor shows Core's template and its first save writes it; until then the UI runs on compiled fallbacks (now the 720x720 ones again, 6a59d83). The INA219 log line still names the file as if it existed. The two other editors disagree on the fix: HW-9 restores the UI writer, APP-16 adds a Core first-run writer.

**Apertar way.** `src/DisplayConfigBridge.cpp:41-326, :587@upstream-1.6.0` and `src/Ina219Bridge.cpp:69-342, :497@upstream-1.6.0` write the template at first start; Core only shows its own copy. Three hand-kept templates are a rough edge (section 4).

**Rework.**
1. UI side, whichever answer: do not put the two UI writers back if the answer is Core. Correct the INA219 log line in `Ina219Bridge.cpp` to say the file is missing and Core writes the default.
2. Answer "Core" (recommended): Core `start()` writes `defaultHardwareConfigTemplate()` through `HardwareConfigStore` when no candidate path has a file and no last-written copy exists (APP-16 step 3); the template gains the upstream UI sections (`chip=auto`, input tuning, `[mpu6050]`, APP-16 step 1). Document "Core is the single writer of apertar-hardware.conf" for the original developer.
3. Answer "UI": restore `ensureDefaultHardwareConfigFile()` and the Ina219 writer from upstream-1.6.0, writing only when no candidate path has a file (HW-9 steps). Then Core `014fa22`'s "starts like the touch UI template" check must be relaxed, or every fresh camera reports a replaced file.

**Owner decision.** Who writes the first-run file: Core (one writer, new ground, removes 578 lines of UI template; cost: a Core change and a handoff line) or the UI as in 1.6.0 (cost: the moved-file case returns and Core's replaced-file check flags every fresh install unless changed)? Recommendation: Core. Decide once for HW-9, APP-16 and UI-4.

**Check here.** Core `--simulate` with `HOME` and `APERTAR_HARDWARE_CONFIG` pointed at an empty scratch dir: the file appears with 720x720 / square / false and `chip=auto`; a second start does not rewrite it.

**Needs the Pi.** Fresh image, no hardware file: after first boot the file exists and the touch UI shows on the DPI panel.

---

## UI-5. Touch-UI IMX585 resolution and FPS lists lag Core's tables

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | no | fix-now | X-state-consistency-3, X-state-consistency-4 |

**Where.** `qml/CameraPage.qml:418, :923-930, :1062-1070@cinemate-port`, `qml/SettingsPage.qml:161@cinemate-port`; Core `src/camera/Imx585Modes.hpp@cinemate-port`, `src/camera/CameraController.cpp:442-450, :10648@cinemate-port`, `src/ApertarCoreApp.cpp:1398-1406@cinemate-port` (`builtInFpsSteps`).

**Problem.** Core's IMX585 sizes are now per-class tables (s12/s10/h12/h16, commit caa0153). The touch lists in `CPg` and `SP` are still upstream's: they lack 2880x2160, 2160x2160, 2976x2160, the 2048x* crops, 1440x1080, 1920x1040, and still offer 3840x2076 / 1920x1038, which port Core rewrites to 2072/1036 (so after such a pick the current value is not in the list). The IMX585 built-in FPS fallback lacks Core's 100 and 120. The WebUI and the hardware buttons offer what the touch UI cannot.

**Apertar way.** Per-sensor tables are identical hand copies in `CPg` and `SP` that change together (QML-9; `CPg:362-381`, `SP:78-114@upstream-1.6.0`); option lists copied per UI are a rough edge to extend in place (section 4, R6).

**Rework.**
1. Wait for CAM-1's answer (driver keeps 2072/1036 or goes back to 2076/1038).
2. `CPg:418` and `SP:161`: replace the IMX585 list with Core's class tables, chosen by bit depth and Clear HDR as WCP does; same entries, same order in both files. Use the heights CAM-1 settles.
3. `CPg` FPS fallback for `imx585Detected`: `[24, 25, 30, 50, 60, 100, 120]`, with a one-line comment naming `builtInFpsSteps` in `ApertarCoreApp.cpp` as the source.
4. CAM-22 step 4 adds the comment in `Imx585Modes.hpp` naming `CPg`/`SP` as copies.

**Owner decision.** None here (CAM-1 holds it).

**Check here.** UI build; `diff` the IMX585 arrays of `CPg` and `SP` (identical); compare against `Imx585Modes.hpp` rows by hand.

**Needs the Pi.** IMX585: pick 2048x1080 and 2880x2160 on the touch screen; `get_state` reports the same resolution.

---

## UI-6. New command invokables return void, send on/off and auto/off, apply a reply twice

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | S | no | fix-now | UI-control-bridge-F1, UI-bridges-F5, UI-control-bridge-F3 |

**Where.** `src/ApertarControlBridge.hpp:194-200@cinemate-port`; `src/ApertarControlBridge.cpp:618-727@cinemate-port`; Core `src/ApertarCoreApp.cpp:12901, :13080@cinemate-port`; WebUI senders `src/web/WebControlPage.cpp:15451, :15843@cinemate-port`.

**Problem.** `applyBufferMode`, `applyStoragePreroll`, `applyStoragePrerollAuto(bool on)`, `applyClipNameTemplate`, `applyCdngLog(bool on)` are `Q_INVOKABLE void`. QML cannot tell a refusal. Booleans travel as `value=on|off` and `value=auto|off`. `applyClipNameTemplate` calls `applyClipNameState(reply)` after `sendCoreCommand`, which already applied the reply. `requestClipNamePreview` is a query and may stay void, like `refresh()`.

**Apertar way.** Command invokables return `bool` and set `lastError` (UIC-9, `ACB:257-261@upstream-1.6.0`); thin variants are `return sendCoreCommand(...)` (`ACB:731-734@upstream-1.6.0`); booleans as `enabled="true"/"false"` with `apply<Thing>Enabled(bool enabled)` (UIC-12, CMD-7; `ACB:736-741@upstream-1.6.0`, Core `App:9482, :9514@upstream-1.6.0`); actions are verbs (UIC-10).

**Rework.**
1. Make the five `bool`: `return false` after each `setLastError` or failed send, `return true` at the end, or the body becomes `return sendCoreCommand(...)`.
2. Rename `applyStoragePreroll()` to `startStoragePreroll()`; replace `applyStoragePrerollAuto(bool on)` with `applyStoragePrerollAutoEnabled(bool enabled)` and `applyCdngLog(bool on)` with `applyCdngLogEnabled(bool enabled)`, both sending `enabled="true"/"false"`.
3. Core (Core editor, same release): `set_storage_preroll` and `set_cdng_log` read `enabled` (lenient `== "true" || == "1"`), and the two WebUI senders switch in the same commit.
4. `applyClipNameTemplate`: delete the reply object and `applyClipNameState(reply)`; body is `return sendCoreCommand(...)`.
5. QML: rename the three call sites; the return value may be ignored as upstream does for monitoring toggles, or used as `if (!bridge.applyX(v)) show lastError` (QML-8).

**Owner decision.** None.

**Check here.** UI build; Core `--simulate`: `set_cdng_log enabled=true` and `set_storage_preroll enabled=false` reply ok; WebUI toggles still work in a browser against `--simulate`.

**Needs the Pi.** Nothing beyond the simulate check.

---

## UI-7. ActionTiles with flipping accent tone used as radio buttons; hand-sized sub-labels

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | no | fix-now | UI-settings-qml-F1, UI-settings-qml-F11 |

**Where.** `qml/SettingsPage.qml:3437, :3445` (Write Buffer Frames/RAM), `:3478` (Log), `:5627, :5634` (Automatic pre-roll On/Off), `qml/ClipNameCard.qml:364-371` (presets), sub-labels `SP` diff :526-531, :571-576, :720-725, `ClipNameCard.qml:16-21, :350-355, :512-519`, all @cinemate-port.

**Problem.** Choices are drawn as `ActionTile`s whose `tone` flips to `"accent"` for the selected value. The original developer reads an accent ActionTile as the primary action. Sub-headings are `Text { color: "white"; font.pixelSize: 14 }` with no Inter font and no layout scaling; pill sizes exist only for large/standard layouts.

**Apertar way.** Booleans: title + description + `TogglePill` (`SP:3562` gyroRecordToggle, `:4885@upstream-1.6.0`). Value choice: `InlineDropdownField` with value/label options (Compression `SP:3250@upstream-1.6.0`, QML-23). `ActionTile` is a verb with constant tone; no conditional tone in any upstream QML. Sub-label style "Write Test": `#66ffffff`, Inter Medium, uppercase, letterSpacing 2.0, layout-dependent size (`SP:5224-5230@upstream-1.6.0`; QML-13, QML-16, QML-17).

**Rework.**
1. Write Buffer: one `InlineDropdownField { label: "Write Buffer"; options: [{value:"frames",label:"Frames"},{value:"ram",label:"RAM"}]; onValueSelected: applyBufferMode(v) }` in the Bit Depth/Compression row.
2. Log: a `TogglePill` row (title "Log", description) calling `applyCdngLogEnabled(checked)` (UI-6).
3. Automatic pre-roll: a `TogglePill` row like `gyroRecordToggle`, calling `applyStoragePrerollAutoEnabled(checked)`.
4. ClipNameCard presets: `InlineDropdownField` "Pattern" with `displayValue: "Custom"` when no preset matches.
5. Keep `ActionTile` only for the Storage Pre-roll verb, with constant tone. Keep the `#9aa5b1` 12 px helper texts (they copy the Format card).
6. Remaining sub-labels copy the Write Test style; ClipNameCard pills get compact/medium branches as `qml/ActionTile.qml:14-23` does.

**Owner decision.** None.

**Check here.** UI build; `grep -n 'tone: .*?' qml/*.qml` returns nothing; run the UI on the desk against `--simulate` at 720x720 and 1920x1080 layouts and look at the Record and System sections.

**Needs the Pi.** Touch each new control on the DPI panel.

---

## UI-8. ClipNameCard: drag-and-drop composer with a hand-placed ghost, untested on touch

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | major | M | unknown | ask-owner | UI-settings-qml-F3 |

**Where.** `qml/ClipNameCard.qml:238-313, :392-471, :578-600@cinemate-port`; `qml/ClipNamePill.qml:53-94@cinemate-port`.

**Problem.** 601 + 115 lines: a ListModel parser/serialiser, 350 ms preview and 1000 ms save timers, a ghost `Rectangle` with `Drag.Internal` positioned by hand via `mapToItem`, `DropArea`, insertion marker, `indexAt`, begin/move/endDrag, long-press with `preventStealing = true` plus a 0 ms reset Timer, and off-palette colours `#123d59`, `#e2f6ff`. Never run on a touch screen (fork-log 841d0ed "untested by hand"). The selection tiles (move left/right, Edit text, Remove) already do what drag does, so drag is a second route in a second drag idiom. Not the least foreign shape.

**Apertar way.** No composer upstream. Drag exists only in the reorder and sidebar popups: `held` flag, `drag.target` on the content item, `Drag.active: held`, `pressAndHoldInterval 260`, `preventStealing false`, DelegateModel moves (`SP:6111-6211`, `:6282-6297@upstream-1.6.0`). Fields apply on selection, no timers. Palette QML-16.

**Rework.**
1. Keep: the preset dropdown (UI-7 step 4), the pill row as a `Flow` of tappable chips, tap on a palette token to append, the selection tiles, the "Next clip" line.
2. Delete: ghost, `DropArea`, marker, `indexAt`, `beginDrag/moveDrag/endDrag`, drag signals and long-press code in `ClipNamePill`, the `drag*` properties.
3. Save on each edit (one `applyClipNameTemplate` per change) and drop the 1000 ms save timer; keep a preview request after the save (the reply carries the example).
4. Use palette colours (`#3fd0ff` accent, `#181818` card, `#1affffff` border). About 200 lines less.
5. If the owner keeps drag: rebuild it on the `reorderDelegate` pattern (`held`, `drag.target`), not a hand-positioned ghost.

**Owner decision.** Keep drag-and-drop in the touch clip-name composer, or ship tap-only? Recommendation: tap-only. Cost of tap-only: the WebUI keeps drag, the touch card loses it (every action stays reachable by taps). Cost of keeping: a rebuild on the reorder pattern (M) and a hand test on the panel before merge.

**Check here.** UI build; desk run against `--simulate`: compose, move, remove, and the template in `get_state` follows each tap.

**Needs the Pi.** Compose a name with the finger on the DPI panel; no stuck flickable, no lost taps.

---

## UI-9. UI commit series: experiments, churn, ticket numbers, and Core pairs

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | major | M | no | fix-later | X-commits-ui-drivers-1, X-commits-ui-drivers-4, X-commits-ui-drivers-5, X-commits-ui-drivers-6 |

**Where.** UI `a51c95e`, `322d329`, `4724007`, `c13b846`, `c153c33`, `1c7a3ad`, `b333343`, `010f8ad` (experiments); `f1edf96`, `7840438`, `35b31f6`, `2475626`, `1a691a9`, `b4591dc`, `682a186` (churn); `ed0d7b5`, `c9d841f`, `7c41a27`, `ec9f109`, `ea44bd7`, `841d0ed` (bodies); pairs `41ff827`, `c9d841f`, `7ea9afc`, `841d0ed`, `160898c`.

**Problem.** 39 UI commits: eight preview experiments add and remove about 1 037 lines and net to nothing (`git diff c234d77 c153c33` empty); camera-set marking goes green, white/green, italic in one day; subjects use T33, T38, T31, T45 and the branch prefix `drop-frames:`; several bodies say "not built". Five UI commits need a Core partner and cannot merge alone (41ff827 needs Core 2955ef8 + dda1713 + f19b245; c9d841f needs 4d80a35 + 014fa22; 7ea9afc needs d7dd337; 841d0ed needs d44b177; 160898c needs 70e8376).

**Apertar way.** Linear history, plain self-contained subjects, no internal numbers (STY-15); Core and UI ship together (CMD-30).

**Rework.**
1. Rebuild the UI series from `c234d77`'s parent as the 15-commit clean series in `raw/sweep-commits-ui-drivers.md` section 1.6, leaving the eight experiments out (and dropping `d1efb67`, UI-15).
2. Squash the colour/label churn into one "Value lists and camera-decided values" commit with the final state (italic, "16-bit").
3. Rewrite subjects in plain words; no T-numbers, no branch prefixes; "Tested" lines say what was tested, after the Pi build.
4. Merge each UI commit in the same release as its Core partner, Core first, using the pairing table of the sweep report section 1.1. Include the fix commits of this list in the series.

**Owner decision.** AI trailers (Co-Authored-By, Claude-Session) in the merged series: keep or strip? STY-15 leaves it to the owner. Recommendation: keep Co-Authored-By, strip Claude-Session (a URL the original developer cannot open).

**Check here.** `git diff cinemate-port <clean-branch>` is empty apart from the fix commits; `git log --format=%s` has no `T[0-9]`.

**Needs the Pi.** Build and smoke-run the clean series once before the PR.

---

## UI-10. Clip-name card loses an edit at record start and drops unknown tokens

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | UI-settings-qml-F9, UI-settings-qml-F8 |

**Where.** `qml/ClipNameCard.qml:28-34, :66-93, :156-170, :317-327@cinemate-port`; Core `src/util/ClipName.hpp:29-34@cinemate-port`.

**Problem.** `saveNow` returns while `!editable`; on record start the timers stop and on stop `syncFromBridge(true)` reloads Core's template. Move a pill and press record within 1 s: the edit is silently lost (a setting loss). `parseTemplate` keeps `{x}` only if it is in the QML palette copy, so a template written by a newer Core or the WebUI with a token QML does not know is saved back without it (latent; both lists hold the same 19 tokens today).

**Apertar way.** Settings apply at once (no save timers upstream). Copying Core's lists into QML is upstream practice (QML-9), but the UI must not rewrite values it does not understand (UIC-17: Core owns camera truth).

**Rework.**
1. Save on each edit (UI-8 step 3). If the timer stays: in `onRecordingChanged`, when recording starts, call `saveNow()` with the pending edit before `editable` turns false.
2. `parseTemplate`: keep any `{name}` as a token pill, labelled with the name; the palette remains the QML list.

**Owner decision.** None.

**Check here.** Desk run against `--simulate`: edit, press record within 1 s, stop: `get_state` `clip_name_template` holds the edit. Set `{format}_{foo}_{clip}` via the socket, move a pill: `{foo}` survives.

**Needs the Pi.** None beyond the desk run.

---

## UI-11. Second state path: controls/media/buffer event branches and a key-name setter

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | M | no | fix-now | UI-control-bridge-F2 |

**Where.** `src/ApertarControlBridge.cpp:1332-1349, :1415-1442@cinemate-port`; `src/ApertarControlBridge.hpp:453@cinemate-port`; Core `src/ApertarCoreApp.cpp:12346-12348` vs `:9458-9459`, `:10826-10828` vs `:9555-9556@cinemate-port`.

**Problem.** `applyCoreMessage` handles `controls` with `setControlsStatus(message, "errors", "warnings")`, `media` with `setCoreMediaState(state, mounted)`, `buffer` with `applyBufferState + applyRecordingDroppedFrames`. `applyCoreState` calls the same mappers with `controls_errors/controls_warnings` and `media_state/media_alive`. Core spells each value two ways. A maintainer who adds a key to one path misses the other. Severity minor, not major: upstream also has small dedicated branches (`audio_level`, `timelapse`); the foreign parts are the double spelling and the key-name parameter.

**Apertar way.** Events whose fields are state keys go whole to `applyCoreState` (`if (event == "standby" || ... || event == "media_write_state") { applyCoreState(message); return; }`, `ACB:1191-1195@upstream-1.6.0`; `recording_health` :1213-1216). No setter takes key names (UIC-4).

**Rework.**
1. Core (Core editor): the `controls` event emits `controls_errors`/`controls_warnings`, the `media` event `media_state`/`media_alive`.
2. UI: add `controls`, `media`, `buffer` to the upstream `applyCoreState` event list; delete the three branches.
3. Delete `setControlsStatus`; in `applyCoreState` inline compare/assign/emit for `controls_errors`/`controls_warnings` in the form of `recording_has_dropped_frames` (`ACB:1270-1276@upstream-1.6.0`). `applyBufferState`/`applyRecordingDroppedFrames` already run from `applyCoreState` (:1457, :1732).
4. Fix UI-24 in the same commit (the media path changes here).

**Owner decision.** None.

**Check here.** UI build; desk run against `--simulate`: change Controls (warning chip appears), pull media via a simulated `media` event if `--simulate` supports it, else code read.

**Needs the Pi.** Pull and insert the card: the touch UI media state follows within a second.

---

## UI-12. Full get_state poll every second while auto ISO or auto WB is on

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | M | yes | fix-now | UI-control-bridge-F6, X-protocol-security-8 |

**Where.** `src/ApertarControlBridge.cpp:19-20, :1012-1018, :1621@cinemate-port`; Core `src/camera/CameraController.cpp:175@cinemate-port`.

**Problem.** `kLiveValuePollIntervalMs = 1000`: while `m_isoAuto || m_whiteBalanceAuto` the GUI thread fetches and applies the whole state every second, 30x upstream, and the HDMI process doubles it; each `get_state` takes `commandMutex_`. `updateRefreshTimer()` runs on every state pass. The settings event carries `iso_actual` but fires only on settings changes, so the poll is the only feed.

**Apertar way.** Two tiers: 1 s while disconnected, 30 s steady (`ACB:17-18, :875-882@upstream-1.6.0`). Core pushes a live value as its own small event mapped in one line: `audio_level` (`ACB:1196-1199@upstream-1.6.0`; CMD-17).

**Rework.**
1. Core (Core editor): publish `{"event":"exposure_measured","iso_actual":..,"wb_actual_kelvin":..}` only on change, rate-limited to 1 Hz, from the 1 Hz loop of `wait()` (CMD-21).
2. UI: add `exposure_measured` to the `applyCoreState` event list (UI-11).
3. Delete `kLiveValuePollIntervalMs`, the ternary at :1016 and the `updateRefreshTimer()` call at :1621.

**Owner decision.** None.

**Check here.** UI build; desk run against `--simulate` with `strace -e trace=connect` or a socket log: one `get_state` per 30 s with auto ISO on.

**Needs the Pi.** Auto ISO on, pan from dark to bright: the ISO readout follows within about a second on both screens.

---

## UI-13. Storage pre-roll inside the Media Speed card; presence latches hide pre-roll and Clip Names

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | UI-settings-qml-F5, UI-settings-qml-F4, UI-control-bridge-F9 |

**Where.** `qml/SettingsPage.qml:2029-2031, :5611, :7393@cinemate-port` (and diff :706-776); `src/ApertarControlBridge.cpp:670-673, :2746-2749@cinemate-port`; `src/ApertarControlBridge.hpp:67, :76, :256, :417, :434@cinemate-port`.

**Problem.** Storage pre-roll (tile, Automatic block, three texts) is appended to `systemMediaSpeedComponent`, so a separate feature with its own setting is not reorderable or favouritable. `storagePrerollAutoKnown` and `clipNameKnown` latch true once Core has sent the key "for older Core"; `recordItemVisible()` adds a per-item visibility hook to the section Repeater and hides Clip Names until then, while the reorder popup still lists it.

**Apertar way.** One card per feature, registered in the order arrays, `sectionItemTitle`, `*ComponentForId` (QML-3, QML-4; `SP:798-802, :838-878, :2336@upstream-1.6.0`). Unavailable features keep their card and explain in the description (QML-24; `SP:3039, :3071@upstream-1.6.0`). Feature presence comes from Core flags (`recording_capabilities`, UIC-6), and Core and UI ship together (CMD-30).

**Rework.**
1. New id `storagePreroll` (title "Storage Pre-roll") in `defaultPowerOrder`, `favoriteCandidateOrder`, `sectionItemTitle`, a branch in `powerComponentForId`, and `Component systemStoragePrerollComponent` (`SystemSectionCard`, icon `media-speed.png`) holding the verb tile, the Automatic `TogglePill` row (UI-7) and the last-result text. Remove those parts from the Media Speed card.
2. Delete `storagePrerollAutoKnown`, `clipNameKnown`, their signal and setters, and `recordItemVisible()` with the Loader `visible:` line. Show both cards always.
3. If mixed versions must ever work, Core adds one capability flag to `recording_capabilities`; not needed now.

**Owner decision.** None.

**Check here.** UI build; desk run: System section lists "Storage Pre-roll" as its own card, it can be reordered and favourited; Record section shows Clip Names at once.

**Needs the Pi.** Run Storage Pre-roll from the new card; the last-result text updates.

---

## UI-14. ISO Auto offered in lossless modes where Core turns it off

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | minor | S | yes | fix-now | UI-camera-qml-F11, UI-camera-qml-F4, X-stock-behaviour-10 (UI half) |

**Where.** `qml/CameraPage.qml:524-532@cinemate-port`; Core `src/camera/CameraController.cpp:3098-3100, :3150-3156@cinemate-port`.

**Problem.** The UI drops Auto only in Clear HDR (UI 682a186). Port Core keeps auto ISO in lossless only on the IMX585 and silently turns it off on other sensors. On IMX477/IMX283 in lossless 4K/2K the operator picks Auto and Core switches to manual. Upstream offered no Auto and a maximum of 800 in any lossless mode; the 1600 ceiling and IMX585 auto are Core decisions (CAM-14), and the UI following `iso_max` is the right pattern.

**Apertar way.** Picker and Core agree: `qml/CameraPage.qml:511-513@upstream-1.6.0`, `src/camera/CameraController.cpp:2483-2484@upstream-1.6.0`. Capability from Core, not a UI rule (UIC-6).

**Rework.**
1. Follow CAM-14's answer.
2. If auto ISO stays on the IMX585 in lossless: Core publishes scalar `iso_auto_allowed` in `settingsBody` from the sanitiser's own rule (CAM-14 / REC-4 step 5); `ACB` reads it in `applyCoreState` next to `iso_max` into `m_isoAutoAllowed` (Q_PROPERTY on `cameraSetValuesChanged`); `isoOptions` drops "Auto"/"Lock" when it is false.
3. If CAM-14 restores 1.6.0 (no auto in lossless): `isoOptions` drops Auto when `root.losslessIsoLimitedMode`, as upstream.
4. State the reason for any changed limit in the commit and handoff, without names or dates.

**Owner decision.** None here (CAM-14 holds it).

**Check here.** UI build; desk run against `--simulate` with an IMX477 simulated sensor, lossless 4K: no Auto in the picker.

**Needs the Pi.** IMX477 lossless 4K: ISO picker has no Auto; IMX585 lossless follows CAM-14.

---

## UI-15. Fallback ceilings: dead ISO fallback, empty FPS block, edited 25 fps cap

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-now | UI-camera-qml-F3, UI-camera-qml-F9, X-commits-ui-drivers-2, X-state-consistency-5 (UI half) |

**Where.** `qml/CameraPage.qml:525, :818-822, :904-918@cinemate-port`; UI `d1efb67`, `b4591dc`; Core `src/ApertarCoreApp.cpp:325, :1386@cinemate-port`.

**Problem.** `isoOptions` reads `root.controlBridge ? controlBridge.isoMax : (losslessIsoLimitedMode ? 1600 : 0)`; `controlBridge` is always set (`Main.qml:500`), so the 1600 branch never runs. `fpsCeiling()` returns `fpsMax` when > 0 and otherwise falls back to the old tables, where the port left an empty `if (root.losslessImx585Mode) { // ... }` and added a Clear HDR 16-bit 25 fps cap (d1efb67). Re-checked X-commits-ui-drivers-2: not a live bug. Port Core always sends `fps_max` (`App:325`), so the 25 cap is reached only against a Core without `fps_max`, which CMD-30 rules out; severity drops from major to minor. What remains is edits to a frozen fallback, an empty block and a stale comment, in Core `App:1386` too.

**Apertar way.** `qml/CameraPage.qml:815@upstream-1.6.0`: `if (root.losslessImx585Mode) max = Math.min(max, 30.0)`. Upstream had no `iso_max`. A fallback that is kept is kept as upstream wrote it (STY-12).

**Rework.**
1. `maximumSupportedFpsForResolution`: revert d1efb67 (back to the upstream 30.0 for 3840x2160 / 3856x2180; drop the comment).
2. `fpsCeiling()`: replace the empty block with the upstream line `if (root.losslessImx585Mode) max = Math.min(max, 30.0)`.
3. `isoOptions`: `const maximum = root.controlBridge ? root.controlBridge.isoMax : 0` (drop the dead 1600 branch).
4. Core editor: fix the stale "Clear HDR 16-bit stops at 25" comment at `App:1386`.
5. The WebUI re-application of caps on top of `fps_max` (WCP:7490-7509) is the WCP editor's.

**Owner decision.** None.

**Check here.** `git diff upstream-1.6.0 -- qml/CameraPage.qml` no longer touches `maximumSupportedFpsForResolution`; UI build.

**Needs the Pi.** None.

---

## UI-16. APERTAR_UI_PREVIEW_RECORDING_FPS experiment knob kept, and it stalls the Rec Run timecode

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | minor | S | yes | fix-now | UI-bridges-F4, UI-bridges-F3, X-commits-ui-drivers-3 |

**Where.** `src/ApertarPreviewSocketClient.cpp:25-43, :488-498`, `src/ApertarPreviewSocketClient.hpp:35-36, :95-98`, `src/main.cpp:351-352`, `qml/CameraPage.qml:2038-2045`, all @cinemate-port; UI `c234d77`.

**Problem.** An "A/B knob" (c234d77) throttles preview frames during takes. Frames over the cap return before `emit frameArrived()`, and the Rec Run UI timecode counts `frameArrived`: with `=0` a 10 s take shows 00:00:00:00, with `=12` on 25 fps it runs at half speed (only when the variable is set). The eight sibling experiments were dropped; this one stayed.

**Apertar way.** UI env knobs only select a render path (`APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}`, `src/PreviewWindowRenderer.cpp:296-301@upstream-1.6.0`); R8.

**Rework.**
1. Delete `setRecording`, the four members, the env read and the `main.cpp` connect. Keep them on a test branch if wanted.
2. Same decision as APP-9 for Core's `APERTAR_WEB_PREVIEW_RECORDING_FPS` (deleted there).

**Owner decision.** None (APP-9 already removes the Core twin).

**Check here.** `grep -rn PREVIEW_RECORDING_FPS src` = 0; UI build.

**Needs the Pi.** None.

---

## UI-17. ControlsWarning.qml missing from qml.qrc (non-AOT builds)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | UI-bridges-F8, UI-camera-qml-F10 |

**Where.** `CMakeLists.txt:41@cinemate-port`, `qml.qrc@cinemate-port` (has ClipNameCard/ClipNamePill at :32-33, not ControlsWarning).

**Problem.** With `APERTAR_QML_AOT=OFF` (default when cross-compiling, `CMakeLists.txt:59-64`) the build adds `qml.qrc` and `main.cpp:401` loads `qrc:/qml/Main.qml`; `ControlsWarning {}` in CameraPage then does not resolve (probable; not built non-AOT here). Upstream has the same gap for `DroppedFrameWarning.qml`.

**Apertar way.** A new QML file goes into both lists (QML-14; `CMakeLists.txt:19-52`, `qml.qrc:3-33@upstream-1.6.0`). The upstream gap is a rough edge (section 4).

**Rework.**
1. Add `qml/ControlsWarning.qml` to `qml.qrc` in CMake order (after `DroppedFrameWarning` position).
2. Add the upstream `qml/DroppedFrameWarning.qml` in a separate, labelled commit (it is an upstream bug, STY-12).

**Owner decision.** None.

**Check here.** `cmake -DAPERTAR_QML_AOT=OFF` build in a scratch dir (not the shared one), run `ApertarUI` offscreen against `--simulate`: no "ControlsWarning is not a type" error.

**Needs the Pi.** None.

---

## UI-18. New Settings items skip icon and favourite registration

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | UI-settings-qml-F7 |

**Where.** `qml/SettingsPage.qml` diff :407-477 (4 Monitoring rows), :665-687 (clipNames), :799-822 (controls) @cinemate-port.

**Problem.** The four new Monitoring rows have no `titleIconSource`, no favourite wiring and are not in `favoriteCandidateOrder`; Clip Names has no favourite; Controls has no icon. They behave unlike their neighbours in the Favorites manager and section list.

**Apertar way.** 39 of 42 upstream Components carry `titleIconSource` and `favoriteEnabled`/`favorited`/`onFavoriteToggleRequested` (`monitoringGreyscaleComponent`, `SP:2865-2885@upstream-1.6.0`); QML-4, QML-6.

**Rework.**
1. Add the 4 Monitoring ids and `clipNames` to `favoriteCandidateOrder` (QML) and to Core's `favoriteCandidateOrder()` copy (Core drops unknown ids, CMD-22).
2. Add the three favourite lines to each Component.
3. Give each an existing icon (`record.png`, `timecode.png`, `audio.png`, `media.png`, `config.png`).

**Owner decision.** None.

**Check here.** Desk run: favourite each new item; `set_favorites_order` via Core keeps them.

**Needs the Pi.** None.

---

## UI-19. Settings text states Core settings as fixed values

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | UI-settings-qml-F6 |

**Where.** `qml/SettingsPage.qml` diff :759 and :819 @cinemate-port.

**Problem.** "Records 2 seconds ... Also runs when a card is inserted or formatted." is always shown, but `[media] preroll_seconds` ranges 1..10 and the automatic run is now off by default (Core `0977dd6`, APP-2). "WebUI: http://<ip>:8000, Settings, Controls" ignores `--web-port`.

**Apertar way.** Core lets the operator change both (`StoragePreroll.hpp:17-23@cinemate-port`; `src/main.cpp:35, :68@upstream-1.6.0`); upstream UI never prints the WebUI port. Descriptions are short fragments (QML-29).

**Rework.**
1. Pre-roll text: drop the number and the second sentence; say "Runs on insert and format" only inside the Automatic row when it is on.
2. Controls text: "Edit in the WebUI, Settings, Controls" without the port.

**Owner decision.** None.

**Check here.** Code read.

**Needs the Pi.** None.

---

## UI-20. Ticket ids, names, dates, "CineMate" and stale "green" in comments; missing include

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-now | UI-bridges-F6, UI-control-bridge-F10, UI-camera-qml-F1, UI-camera-qml-F2, UI-settings-qml-F12 |

**Where.** `src/ApertarControlBridge.hpp:18, :82, :424, :435, :453`, `src/ApertarControlBridge.cpp:275, :1582, :2656, :2666`, `src/SettingsBridge.hpp:95`, `src/SettingsBridge.cpp:1767`, `src/ApertarPreviewSocketClient.cpp:26`, `qml/CameraPage.qml:518, :523, :544, :710, :858-859, :889, :4339`, `qml/ExternalMonitorWindow.qml:1427`, `qml/TopDropdownStat.qml:11, :100`, `qml/ControlsWarning.qml:3`, `qml/SettingsPage.qml:6455`, all @cinemate-port.

**Problem.** Comments carry "T31", "T33", "T45", "Request 24", "request 25", "(Patrik, 2026-10-28)", "(HDMI 50 min, Core 37 min, 2026-10-27)", "KB trap 7", "CineMate Log", "older Core", and say camera-set values are "green" though they render in italics since 35b31f6. `std::clamp<qint64>` is used without `#include <algorithm>`.

**Apertar way.** No ticket numbers, names or history in source (STY-9, QML-20); comments are one or two lines of why (STY-8; `ACB:861-862@upstream-1.6.0`).

**Rework.**
1. Delete ids, names and dates; keep the one-line "what". At `CPg:710` keep "16-bit = 2 bytes a pixel".
2. "CineMate Log" -> "cDNG log encoding"; "green" -> "italic" in the four camera-set comments (leave the real "READY green" ones).
3. Add `#include <algorithm>` to `ACB` (std group, STY-5).
4. `setControlsStatus` declaration among members goes with UI-11; "A/B knob" comment goes with UI-16.

**Owner decision.** None.

**Check here.** `grep -nE 'T[0-9]{2}\b|Request [0-9]|CineMate|KB trap|Patrik|2026-' src qml` = 0; UI build.

**Needs the Pi.** None.

---

## UI-21. Buffer bar written twice (StatusChip and HDMI pill)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-now | UI-camera-qml-F5 |

**Where.** `qml/StatusChip.qml:95-119@cinemate-port`; `qml/ExternalMonitorWindow.qml:1104-1137@cinemate-port`.

**Problem.** Both files hold the same clipped Item with an inner Rectangle copy of the pill shape, the `drainOnly` colour rule, 0.85 opacity and a 150 ms animation; they differ only in the id they size against.

**Apertar way.** An element both screens show is one small standalone QML file used by both (QML-11): `DroppedFrameWarning` in `CPg:2569` and `EMW:1103@upstream-1.6.0`.

**Rework.**
1. Add `qml/StatusPillBufferBar.qml` (properties `fill`, `drain`, `inset`, `pillRadius`), with the code from StatusChip.
2. Use it in StatusChip and inside the EMW pill; keep the EMW pill itself inline.
3. Register it in `CMakeLists.txt` and `qml.qrc` (QML-14).

**Owner decision.** None.

**Check here.** UI build; desk run with the buffer bar switch on against `--simulate`.

**Needs the Pi.** HDMI and touch bars look the same during a take.

---

## UI-22. HDMI window copies of ISO cap, raw-format test and fps formatting drift from CameraPage

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | UI-camera-qml-F8 |

**Where.** `qml/CameraPage.qml:534@cinemate-port`; `qml/ExternalMonitorWindow.qml:98, :102-110, :123-124, :137@cinemate-port`.

**Problem.** EMW repeats `isoOnAddedCap` with an inline ISO list and without the `valueSteps` filter; its `rawRecordFormat` tests ProRes and "H.264" instead of using its own `processedVideoRecordFormat`; the pre-roll fps uses `toFixed(3)` instead of `formatFpsValue`. After a one-sided edit the two screens show different values.

**Apertar way.** CameraPage and EMW label code is paired by hand (ui-map section 4); the copy is upstream practice, the drift is not.

**Rework.**
1. Make the EMW copies textually match CameraPage: same `valueSteps` filter, `processedVideoRecordFormat`, `formatFpsValue`.
2. Add these rows to ui-map section 4 ("CameraPage vs ExternalMonitorWindow labels"). Do not move the logic into the bridge.

**Owner decision.** None.

**Check here.** Side-by-side diff of the two functions.

**Needs the Pi.** None.

---

## UI-23. Touch picker and FPS buttons ignore fps_take_max during a ladder take

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | X-state-consistency-2 |

**Where.** `qml/CameraPage.qml:904-906@cinemate-port`; `src/ApertarControlBridge.cpp:1589-1594@cinemate-port`; Core `src/ApertarCoreApp.cpp:1410-1415@cinemate-port`, `src/web/WebControlPage.cpp:7484-7485@cinemate-port`.

**Problem.** In a ladder take Core clamps `set_fps` to `fpsTakeMax` and replies ok. The WebUI cuts its list at `fps_take_max`; the touch picker and the hardware buttons offer values above the rung, and the display snaps back from the reply. Internal inconsistency of new ground (the ladder).

**Apertar way.** Offer only choices Core supports (QML-24); bridge mirrors Core limits as scalar properties (`h264MaxFps`, `ACB.hpp:39@upstream-1.6.0`).

**Rework.**
1. `ACB` `applyCoreState`: read `fps_take_max` next to `fps_max` into `m_fpsTakeMax`, Q_PROPERTY `fpsTakeMax` on `cameraSetValuesChanged`.
2. `CPg` `fpsCeiling()`: when `root.recording && controlBridge.ladderActive && controlBridge.fpsTakeMax > 0` return it, as WCP:7485.
3. Core `availablePcfFpsOptions` (Core editor): use `settings.fpsTakeMax` when the ladder is active and a take runs.

**Owner decision.** None.

**Check here.** Desk run against `--simulate` with a ladder take if `--simulate` runs takes; else code read.

**Needs the Pi.** Ladder take: the picker stops at the rung ceiling.

---

## UI-24. Core media override never cleared when Core goes away

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | UI-bridges-F9 |

**Where.** `src/MediaStatusBridge.cpp:288-296, :1245-1257@cinemate-port`; `src/ApertarControlBridge.cpp:1415-1422, :2840-2853@cinemate-port`.

**Problem.** `updateStatus` returns early with `mediaMounted=false` while Core's last state is removed/error and not alive. `setConnected(false)` does not reset it and `setCoreMediaState` ignores empty states. Pull the card, stop Core, re-insert and let the automounter mount it: the touch UI shows no media until Core returns; `statusText` stays "MEDIA REMOVED".

**Apertar way.** No precedent: upstream uses `QStorageInfo` only (`MediaStatusBridge.cpp:1232-1234@upstream-1.6.0`). Core owns truth only while it is there (UIC-17).

**Rework.**
1. `ApertarControlBridge` on disconnect: clear `m_coreMediaState`, emit `coreMediaStateChanged("", true)`.
2. `MediaStatusBridge::setCoreMediaState`: an empty state clears `m_coreMediaKnown` and resets `statusText`.
3. Do it with UI-11.

**Owner decision.** None.

**Check here.** Desk run: UI against `--simulate`, kill Core: media state falls back to the local probe.

**Needs the Pi.** The pull/stop/insert sequence above.

---

## UI-25. shutterSetByCamera reads m_recording before the recording state is set

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | UI-control-bridge-F8 |

**Where.** `src/ApertarControlBridge.cpp:1352-1357, :1610, :1730-1731@cinemate-port`.

**Problem.** `shutterSet = m_recording && m_fpsSpeedRamp && m_fpsSpeedRampKeepExposure` is computed in `applyCoreState`; the `recording` event calls `applyCoreState(message)` first and `setRecordingState(active)` after, which neither recomputes it nor emits. The italic camera-set mark on the shutter lags one state pass at take start and stays after stop until the next pass (up to 30 s with auto off). Not seen on screen yet.

**Apertar way.** No precedent.

**Rework.**
1. In `setRecordingState`, recompute `m_shutterSetByCamera` and emit `cameraSetValuesChanged` when it changes.

**Owner decision.** None.

**Check here.** Code read; UI build.

**Needs the Pi.** Speed-ramp take with the Exposure policy: the shutter mark turns italic at start and plain at stop.

---

## UI-26. String-or-number tolerant parsing for typed Core fields

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | no | fix-later | UI-control-bridge-F4 |

**Where.** `src/ApertarControlBridge.cpp:2666, :2692-2759, :2768-2783@cinemate-port`.

**Problem.** "Core's flat JSON delivers scalars as strings (KB trap 7); accept numbers too" is followed by six string-or-number / string-or-bool branches and an `asBool` lambda. Core emits these fields typed (`App:257-263, :306`, `CC:207-210@cinemate-port`). About 40 lines of dead generality; the cited trap is about Core's request parser, not its output.

**Apertar way.** Typed accessors with the member as default: `state.value("iso_auto").toBool(m_isoAuto)` (`ACB:1321@upstream-1.6.0`; UIC-4).

**Rework.**
1. Replace each branch with `.toDouble(m_x)` / `.toInt(m_x)` / `.toBool(m_x)`; delete the lambda and the comment.

**Owner decision.** None.

**Check here.** UI build; desk run against `--simulate`: the buffer, clip-name and Log values still appear.

**Needs the Pi.** None.

---

## UI-27. Fan mode from the touch UI goes through Core's set_fan_mode

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | UI-bridges-F11 |

**Where.** `src/SystemActionBridge.cpp:65-97, :404-409@cinemate-port`; UI `41ff827`.

**Problem.** `applyFanMode` sends Core's `set_fan_mode` over a small private synchronous `QLocalSocket` (id 42002, 1 s connect, 8 s reply) instead of writing `config.txt` itself with `sudo -n install`. The fan mode cannot change while Core is down; the operator gets a clear message. It removes a duplicate writer that could race a Boot Config save.

**Apertar way.** Upstream UI wrote `config.txt` itself (`src/SystemActionBridge.cpp:431-476@upstream-1.6.0`), duplicating Core's `applyFanMode` (`App:3127-3175@upstream-1.6.0`), which already has `set_fan_mode`. A bridge with its own long Core operation may keep a small private socket client (UIC-3; copies `MediaStatusBridge.cpp:15-35@upstream-1.6.0`).

**Rework.**
1. Keep. Merge only with its Core partners (UI-9 step 4; APP-4 for the fan-mode helper header problem).
2. Handoff line: "Fan mode is now written by Core only; the touch UI asks Core, and needs Core running."

**Owner decision.** None.

**Check here.** Desk run against `--simulate`: change fan mode, reply ok.

**Needs the Pi.** Change fan mode on the touch UI, reboot, `grep fan /boot/firmware/config.txt` shows the new mode.

---

## Dropped or owned elsewhere

| Finding | Why |
| --- | --- |
| X-protocol-security-3 (ISO Lock does nothing against a 1.6.0 Core) | Mixed install only; Core and UI ship together (CMD-30). Lock works with port Core |
| X-commits-ui-drivers-2 as a live bug | Re-checked: port Core always sends `fps_max` (`App:325`), so the QML 25 fps cap is a fallback only; kept as UI-15 (minor) |
| UI-control-bridge-F7 | Dropped by the unit skeptic: Core's Lock reads the measured gain under its own mutex |
| UI-settings-qml-F13 | Dropped by the unit skeptic: upstream inlines the same popup conditionals |
| UI-bridges-F10 (CfeAutomounter single-sample surprise removal) | Owned by REC-15 (recording list) |
| X-board-support-9 (new cards ignore recording_capabilities) | WebUI and Core: CAM-19 and the WCP editor |
| X-stock-behaviour-10 Core half, X-stock-behaviour-9 | CAM-14 |
| X-state-consistency-5 WebUI half (WCP:7490-7509) | WCP editor |
| UI `apertar::clipframes` namespace | REC-38 |

## What conforms (for the handoff)

- The four new UI.conf switches (`recordingFrameEnabled`, `frameBufferBarEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`) follow recipe R3 exactly: constructor read with inline default, `pollExternalSettings`, guarded setter, presets (`SB:368-371, :552-555, :1150-1216, :2170-2173@cinemate-port`; UIC-13, QML-7). Their rows are `MonitoringRow`s bound to `settingsState`.
- New `ApertarControlBridge` properties are read-only with NOTIFY and share signals (`cameraSetValuesChanged`, `cdngLogChanged`, `clipNameChanged`) as `recordingCapabilitiesChanged` does (`ACB.hpp:34-39@upstream-1.6.0`).
- New Core keys are flat snake_case, read under `state.contains(...)` in `applyCoreState`; every new command goes through `sendCoreCommand` with flat scalar arguments; no new socket path, thread, timer framework or logging (UIC-3, UIC-4, UIC-16).
- Error texts are full sentences through `lastError` ("Invalid write buffer mode."; UIC-9, STY-10).
- Core ceilings reach QML as scalar properties `isoMax`, `fpsMax`, like upstream `h264MaxFps`; no board probing in the UI (UIC-6). The HDMI process gets the new properties for free through its own bridge set (UIC-7).
- `bufferSafetyStopped(QString)` mirrors `recordingFailed(QString)`; new Core events are handled in the existing `Connections { target: root.controlBridge }` with `showRecordWarning(...)` (QML-19, QML-27).
- Cross-bridge wiring is `QObject::connect` in `main()` (UIC-1).
- New Settings ids go through the hand registration chain: order array, `sectionItemTitle`, `*ComponentForId`, one Component each (QML-3, QML-4).
- Compression is greyed while the Mode Ladder is active through `fieldEnabled` and label, the way upstream greys it while recording (QML-24, QML-25).
- The Info Controls card is `SystemSectionCard` + `InfoDataRow`, read-only, pointing to the WebUI for editing; `ControlsWarning.qml` copies `DroppedFrameWarning.qml` (QML-11).
- The clip text input reuses the existing keyboard popup with a purpose flag; the clip-name default `{format}_{date}_{clip}` matches Core `ClipName.hpp:23` and the WebUI, so clip names are unchanged by default.
- New pill states are one more branch in the existing ternary chains of `StatusChip.qml` and EMW; `DroppedFrameWarning.count` and `AudioMeterOverlay.soundRecorded` extend upstream components with one back-compatible property.
- The value-list helpers (`valueSteps`, `cappedValueEntries`, `fpsOptionEntries`, `shutterAngleEntries`) are column-0 JS helpers beside upstream `availableFpsOptions`, with C++ twins in Core as upstream already had `pcfIsoOptions`.
- `MediaStatusBridge::updateStatus` is extended in place with a two-line why-comment.
