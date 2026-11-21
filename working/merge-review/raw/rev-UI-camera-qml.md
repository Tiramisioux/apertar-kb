# Review: UI-camera-qml (stage 2)

Refs: port = `cinemate-port` `7ea9afc`, upstream = `upstream-1.6.0` (`/home/user/wt/ui-upstream`, `/home/user/wt/core-upstream`).
Scope: `diffs/UI-CameraPage.part01.diff` (complete, ends at file end), diff of `StatusChip.qml`, `TopDropdownStat.qml`,
`ExternalMonitorWindow.qml` (EMW), `AudioMeterOverlay.qml`, `DroppedFrameWarning.qml`. Port line numbers are from
`git show cinemate-port:qml/<file>`. No `apertar-conventions.md` yet; the `conv-*` pages cover Core only, so the yardstick
here is the upstream QML read directly.

## Verdict in one paragraph

The unit is mostly written the upstream way: hand-written helper functions at column 0 in `CameraPage.qml` (as
`availableFpsOptions` upstream `CameraPage.qml:802@upstream-1.6.0`), Core ceilings read as scalar bridge properties
(as `controlBridge.h264MaxFps`, upstream `ApertarControlBridge.hpp:39`), monitoring switches as `settingsBridge` /
`UI.conf` keys, extra state added as one more branch of the existing ternary chains in `StatusChip.qml` and EMW. No
socket or HTTP change in these files. What a maintainer would trip over: ticket numbers and stale "green" comments,
one feature (buffer bar) written twice where upstream shares a small component, the safety-stop "not a take" rule
applied to the pill and button but not to the frame, timecode and audio outline, and the loss of upstream's lossless
ISO/FPS fallbacks when the UI meets a Core that does not send `iso_max` / `fps_max`.

## Findings

| Id | Cat | Sev | Title |
| --- | --- | --- | --- |
| F1 | slop | minor | Ticket numbers and personal/date notes in code comments |
| F2 | slop | minor | Stale "green" comments: the convention is italics |
| F3 | protocol | minor | Lossless ISO and IMX585 lossless FPS caps lost against a Core without `iso_max`/`fps_max` |
| F4 | removed-upstream-behaviour | minor | ISO Auto now offered in lossless modes; lossless fallback 800 -> 1600 |
| F5 | mismatch | minor | Buffer bar written twice (StatusChip and EMW pill) |
| F6 | bug | minor | Safety-stop flush: pill says READY, frame/red timecode/audio outline still say recording |
| F7 | removed-upstream-behaviour | minor | HDMI timecode turns red while recording by default (upstream: always white) |
| F8 | duplication | minor | `isoOnAddedCap` and built-in ISO list repeated in EMW; raw-format test differs |
| F9 | slop | nit | Empty `if` block with a comment in `fpsCeiling()` |
| F10 | slop | nit | `ControlsWarning.qml` and `DroppedFrameWarning.qml` not in `qml.qrc` |

### F1 slop, minor: ticket numbers and history in comments
- Port: `CameraPage.qml:518` "T33: the lists come from UI.conf", `:544` "(Patrik, 2026-10-28)", `:710` "(HDMI 50 min, Core 37 min, 2026-10-27)", `:858` "Request 24:", `:4339` "Recording frame (request 25)"; `EMW:1427` "request 25"; `TopDropdownStat.qml:11`, `:100` "(T33)"; `ControlsWarning.qml:3` "T45:".
- Upstream: comments state what the code does, no ticket ids (e.g. `CameraPage.qml:2563@upstream-1.6.0` "Interactive still controls must sit above previewTouchArea (z: 25)").
- Rework: delete the ids, names and dates; keep the one-line "what". For `:710` keep "16-bit = 2 bytes a pixel".

### F2 slop, minor: stale "green"
- Port: `CameraPage.qml:523` "the ceiling added in green", `:859` "(camera-set, green)", `:889` "camera-set (green)", `TopDropdownStat.qml:100` "green when the camera added it". Code renders italics (`TopDropdownStat.qml` `font.italic: optionCameraSet`), since `35b31f6`.
- Rework: replace "green" with "italic" in four comments.

### F3 protocol, minor: caps lost with an original Core
- Port `CameraPage.qml:525-532`: `const maximum = root.controlBridge ? root.controlBridge.isoMax : (root.losslessIsoLimitedMode ? 1600 : 0)`. On the device `controlBridge` is always set (`Main.qml` passes `apertarControlBridge`), so the lossless fallback is dead code; with a Core that sends no `iso_max` the bridge value is 0 and no ISO cap applies.
- Port `fpsCeiling()` `:904-916`: `if (root.losslessImx585Mode) { // Core's fps_max carries ... }` - the fallback path (reached only when `fpsMax` is 0) no longer caps IMX585 lossless at 30.
- Upstream: `CameraPage.qml:511-513@upstream-1.6.0` `losslessIsoLimitedMode ? ["100","200","400","800"] : ["Auto", ...]`; `availableFpsOptions` `:815` `if (root.losslessImx585Mode) max = Math.min(max, 30.0)`. Upstream Core clamps silently: `CameraController.cpp:2483-2490@upstream-1.6.0` `settings.iso = std::min<uint32_t>(settings.iso, 800u); settings.isoAuto = false; ... imx585 ? 30.0`.
- Failing input: port UI + upstream Core, IMX585, cDNG lossless. Picker offers Auto, 1600..51200 and 50/60 fps; Core silently corrects to 800 / 30.
- Rework: `const maximum = root.controlBridge && root.controlBridge.isoMax > 0 ? root.controlBridge.isoMax : (root.losslessIsoLimitedMode ? 800 : 0)` (value of the Core actually met); in `fpsCeiling()` restore `if (root.losslessImx585Mode) max = Math.min(max, 30.0)` in the fallback branch (it runs only when `fpsMax` is 0). Same for Auto: hide it when the fallback cap is in use.

### F4 removed-upstream-behaviour, minor: Auto in lossless, 800 -> 1600
- Port `:528-532`: Auto dropped only for `clearHdrActive` (commit `682a186` "Core keeps auto ISO in IMX585 lossless now"); `b4591dc` "Core's lossless ISO cap is 1600 now".
- Upstream: no Auto and max 800 in lossless (UI `:511-513`, WebUI `WebControlPage.cpp:5025`, Core `:2483-2484`).
- Deliberate: yes, tied to Core changes in the CC unit. Acceptable only if the Core change is accepted; the commit message must say why lossless can now run auto gain to 1600 (thermal/compression headroom). Covered with F3 rework for old Core.

### F5 mismatch, minor: buffer bar written twice
- Port: `StatusChip.qml:95-119` and `EMW:1104-1137` - the same clipped `Item` + inner `Rectangle` copy of the pill shape, the same `drainOnly` rule, the same colours, 150 ms animation.
- Upstream way: a pill decoration that both screens show is one small component used twice: `DroppedFrameWarning` at `CameraPage.qml:2569@upstream-1.6.0` and `ExternalMonitorWindow.qml:1103@upstream-1.6.0`.
- Rework: new `qml/StatusPillBufferBar.qml` (Item; props `fill`, `drain`, `pillRadius`, `inset`), used inside `StatusChip` and the EMW pill; register in `CMakeLists.txt`. Keep the inline EMW pill itself (upstream keeps it separate from `StatusChip`).

### F6 bug, minor: flush rule applied in only half the places
- Port: pill `recording: root.recording && !root.bufferFlushing` (`CameraPage` StatusChip), RecordButton `recording: root.recording && !root.bufferFlushing`, EMW `pillRecordingActive`. Not applied: recording frame `:4347` `visible: root.recording && ...`, timecode `:3924`, audio outline `:3896`, `:4093`; EMW frame `:1433`, timecode `:1208`, audio border `~:993` (all use `recordingActive`).
- Failing input: buffer safety stop with Frame Buffer Bar and Recording Frame on. Pill green READY, red frame and red timecode still on until Core clears `recording`.
- Rework: one derived property per window (`readonly property bool takeActive: root.recording && !root.bufferFlushing` in CameraPage; EMW already has `pillRecordingActive`, rename `takeActive`) and use it for pill, button, frame, timecode and outline.

### F7 removed-upstream-behaviour, minor: HDMI timecode colour
- Port `EMW:1208` `color: root.recordingActive && (!settingsBridge || settingsBridge.recordingRedTimecodeEnabled) ? "#ff4d4d" : "white"`.
- Upstream `ExternalMonitorWindow.qml:1129@upstream-1.6.0` `color: "white"`; only the touch timecode went red (`CameraPage.qml:3747@upstream-1.6.0`).
- Rework: if the switch is to stay, leave the HDMI default as upstream (white) and make the HDMI red its own decision, or state the HDMI change in the commit message. Not a blocker; the original developer will see a default change on the client monitor.

### F8 duplication, minor
- `isoOnAddedCap` in `CameraPage.qml:534` and `EMW:102`; EMW repeats the built-in ISO list inline (`EMW:107`) and does not filter bad values as `valueSteps` does.
- Raw-format test: CameraPage `rawRecordFormat` uses `processedVideoRecordFormat`; EMW uses `recordingFormatValue !== "H.264"`.
- Pre-roll FPS format: CameraPage `formatFpsValue`, EMW `toFixed(3)` (`EMW:98`).
- Upstream already pairs CameraPage/EMW labels by hand (ui-map 4 "CameraPage vs ExternalMonitorWindow labels"), so the copy itself follows upstream practice. Rework: make the two copies textually identical and add these rows to ui-map 4. Better: the bridge exposes `isoOnAddedCap` (it already has `isoMax` and `isoSteps` is in `UI.conf`), both windows read it.

### F9 slop, nit
- `fpsCeiling()` `:912-913` `if (root.losslessImx585Mode) { // ... no fixed cap here } else if ...`. Folded into F3 rework.

### F10 slop, nit
- `CMakeLists.txt:40-41@cinemate-port` lists `DroppedFrameWarning.qml` and `ControlsWarning.qml`; `qml.qrc` has neither. Upstream trap (ui-map 4, last rows); the port repeats it with the new file. Add both to `qml.qrc` or leave as upstream and note it.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `valueSteps`, `cappedValueEntries`, `fpsOptionEntries`, `fpsCeiling`, `shutterAngleEntries`, `flickerFreeShutterAngles` | keep | Hand-written column-0 helpers next to upstream `availableFpsOptions`; same style. Core has the C++ twins (`pcfIsoOptions`, `pcfShutterAngleOptions` `ApertarCoreApp.cpp:1574-1593@cinemate-port`) as upstream already had `pcfIsoOptions` `:1279@upstream-1.6.0`. Fix comments (F1, F2) |
| Option object `{value, enabled, cameraSet}` in `TopDropdownStat` | keep | Strings still work; smallest widening of a generic upstream component; delegate reads it in three readonly props |
| `cameraSet` / italic convention (`valueItalic`) | keep | New ground, weighed (green tried in `f1edf96`, replaced in `35b31f6`, fork-log:216). Document once for the original developer |
| `displayValue` on `TopDropdownStat` | keep | Needed to show auto's value while the selection stays "Auto"; one property |
| `bufferFlushing` / `pillRecordingActive` / `drainOnly` / `draining` / `prerollOnly` | simplify | One "take active" property per window, used everywhere (F6); chip-internal derived props are fine |
| Buffer bar Item+Rectangle x2 | rework-to-upstream-pattern | One shared QML component, as `DroppedFrameWarning` (F5) |
| `ControlsWarning.qml` | keep | Same shape as `DroppedFrameWarning.qml`; drop "T45" comment |
| `builtIn*Steps` arrays in QML | keep | Upstream keeps option lists in QML too (`:492`, `:511`, `:3007@upstream-1.6.0`); same values as Core `builtIn*Steps` |
| Recording-frame Rectangle x2 (z 10000) | keep | Small, switch default off; fix gating (F6) |

## Conforms

- Core ceilings as scalar bridge properties `isoMax`, `fpsMax`, like upstream `h264MaxFps` (`ApertarControlBridge.hpp:39@upstream-1.6.0`).
- Monitoring switches (`frameBufferBarEnabled`, `recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled`) live in `settingsBridge` / `UI.conf`, as upstream aids.
- New pill states are one more branch in the existing ternary chains (`StatusChip.qml` `stateFill`, `dotFill`, `chipLabel`, width; EMW `externalStatus*`).
- New Core events handled in the existing `Connections { target: root.controlBridge }` with `root.showRecordWarning(...)`, like `onRecordingFailed`.
- `DroppedFrameWarning.count` and `AudioMeterOverlay.soundRecorded` extend upstream components with one property, back-compatible defaults.
- Clear HDR 16-bit 25 fps added in place in `maximumSupportedFpsForResolution`, with the Core function named.
- `estimatedFrameSizeMB` / `currentRawBitDepthNumber` extended in place.
- No socket command, HTTP route or env var added here.

## Skeptic

Checked at `cinemate-port` (UI `7ea9afc`, Core `01f170c`) against `upstream-1.6.0`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | All nine lines confirmed. One more of the same kind: `qml/SettingsPage.qml:6455@cinemate-port` "T45: read-only" (Settings unit, listed here for the sweep). Upstream `qml/` has no ids or dates (grep) |
| F2 | stands | Four "green" comments confirmed; rendering is `font.italic: optionCameraSet` (`TopDropdownStat.qml:114`), `valueItalic` (`:39`). The "READY green" / "green bar" comments at `CameraPage` safety-stop and `StatusChip` are true colours, not stale |
| F3 | stands | `CameraPage.qml:526` fallback unreachable (`controlBridge` set at `Main.qml:500`); `fpsCeiling()` `:912-913` empty IMX585 branch, upstream `:815@upstream-1.6.0` caps 30. Upstream Core clamps silently (`CameraController.cpp:2483-2490@upstream-1.6.0`). Scenario is port UI on an un-updated Core only, so minor |
| F4 | corrected | Deliberate, confirmed (UI `682a186`, `b4591dc`; Core `CameraController.cpp:3098-3100,3150-3155@cinemate-port`). The UI only follows Core's `iso_max`; the decision is Core's. Severity nit in this unit; the real issue it hides is new F11 |
| F5 | stands | Two copies confirmed (`StatusChip.qml:95-119`, `ExternalMonitorWindow.qml:1104-1137`), differing only in the id they size against. Upstream shares a pill decoration via `DroppedFrameWarning` (`CameraPage.qml:2569`, `ExternalMonitorWindow.qml:1103@upstream-1.6.0`) |
| F6 | stands | Core keeps `recording` true while it drains after its own `record_stop` (`ApertarCoreApp.cpp:11094-11110@cinemate-port`); the port itself gates pill and button on `!bufferFlushing` (`CameraPage.qml:2694,3953`), so the author knew. Frame `:4347`, timecode `:3924`, outline `:3896,4093`, EMW `:1208,1433` are not gated |
| F7 | corrected | Commit `da2a9b5` says "HDMI now follows it too", so deliberate = yes and the change is stated. What is left: the client-monitor default changed (white -> red while recording); nit, carry into the handoff notes |
| F8 | corrected | Drift confirmed (`EMW:102-110`, `EMW:123-124` tests ProRes and H.264 instead of its own `processedVideoRecordFormat` `:137`, `EMW:98` `toFixed(3)`). "Move into ApertarControlBridge" dropped: the steps live in `SettingsBridge`, and the hand-paired copy is the upstream pattern (ui-map 4) |
| F9 | stands | Confirmed; same fix as F3 |
| F10 | stands | Non-AOT builds compile `qml.qrc` (`CMakeLists.txt:200-203@cinemate-port`), and AOT is off by default for cross builds (`:59-63`). Missing from `qml.qrc`: `ControlsWarning.qml` (port), `DroppedFrameWarning.qml` and `InlineChoice.qml` (upstream) |
| F11 | added | Found while checking F4: UI offers ISO Auto in non-IMX585 lossless modes, port Core still forces it off there |

## Final findings

### UI-camera-qml-F1 [slop, minor] Ticket numbers, names and dates in code comments
- where: `qml/CameraPage.qml:518,544,710,858,4339@cinemate-port`; `qml/ExternalMonitorWindow.qml:1427@cinemate-port`; `qml/TopDropdownStat.qml:11,100@cinemate-port`; `qml/ControlsWarning.qml:3@cinemate-port` (also `qml/SettingsPage.qml:6455@cinemate-port`, Settings unit)
- port: comments carry "T33", "T45", "Request 24", "request 25", "(Patrik, 2026-10-28)", "(HDMI 50 min, Core 37 min, 2026-10-27)"
- Apertar way: comments say what the code does, no ids: `qml/CameraPage.qml:2563@upstream-1.6.0` "Interactive still controls must sit above previewTouchArea (z: 25)."; no ids or dates anywhere in upstream `qml/`
- why it matters: the ids mean nothing to the original developer; dated notes tell history, not code
- rework: delete ids, names, dates; keep the one-line "what" (for `:710` keep "16-bit = 2 bytes a pixel")
- effort S; deliberate no

### UI-camera-qml-F2 [slop, minor] Stale "green" comments; the convention is italics
- where: `qml/CameraPage.qml:523,859,889@cinemate-port`; `qml/TopDropdownStat.qml:100@cinemate-port`
- port: comments say camera-set values are green; code renders italics (`TopDropdownStat.qml:39,114`), since `35b31f6`
- Apertar way: no precedent
- why it matters: comments contradict the rendering
- rework: "green" -> "italic" in the four comments (leave the safety-stop "READY green" comments, they are true)
- effort S; deliberate no

### UI-camera-qml-F3 [protocol, minor] Lossless ISO and IMX585 lossless FPS caps lost against a Core without iso_max/fps_max
- where: `qml/CameraPage.qml:525-532@cinemate-port`; `qml/CameraPage.qml:904-916@cinemate-port`
- port: `const maximum = root.controlBridge ? root.controlBridge.isoMax : (root.losslessIsoLimitedMode ? 1600 : 0)`; `controlBridge` is always set (`Main.qml:500`), so the fallback is dead and `isoMax` 0 means no cap. `fpsCeiling()` has an empty `if (root.losslessImx585Mode) { }` in the fallback path
- Apertar way: `qml/CameraPage.qml:511-513@upstream-1.6.0` lossless list `["100","200","400","800"]`, no Auto; `:815` `if (root.losslessImx585Mode) max = Math.min(max, 30.0)`; Core clamps silently `src/camera/CameraController.cpp:2483-2490@upstream-1.6.0`
- why it matters: port UI on an un-updated Core, IMX585 lossless cDNG: offers Auto, ISO 1600-51200 and 50/60 fps; Core silently corrects
- rework: `isoOptions`: use `controlBridge.isoMax` only when > 0, else `losslessIsoLimitedMode ? 800 : 0`, and drop Auto while that fallback applies. `fpsCeiling()`: restore `max = Math.min(max, 30.0)` for `losslessImx585Mode` in the fallback branch (runs only when `fpsMax` is 0)
- effort S; deliberate no (`b4591dc` set the dead fallback to 1600 "as Core" without noticing it is unreachable)

### UI-camera-qml-F4 [removed-upstream-behaviour, nit] ISO Auto in IMX585 lossless; lossless ISO ceiling 800 -> 1600
- where: `qml/CameraPage.qml:525-532@cinemate-port` (decision in Core: `src/camera/CameraController.cpp:3098-3100,3150-3155@cinemate-port`)
- port: Auto dropped only in Clear HDR; lossless ceiling follows Core's `iso_max` (1600)
- Apertar way: no Auto, max 800 in lossless: `qml/CameraPage.qml:511-513@upstream-1.6.0`, `src/web/WebControlPage.cpp:5025@upstream-1.6.0`, `src/camera/CameraController.cpp:2483-2484@upstream-1.6.0`
- why it matters: changes a limit the original developer set in three places
- rework: none in the UI beyond F3/F11 (following `iso_max` is the right pattern). Keep it with the Core change (CC unit) and give the measured reason in the commit and handoff, without names or dates
- effort S; deliberate yes (UI `682a186` "Core keeps auto ISO in IMX585 lossless now", `b4591dc` "Core's lossless ISO cap is 1600 now")

### UI-camera-qml-F5 [mismatch, minor] Buffer bar written twice (StatusChip and HDMI pill)
- where: `qml/StatusChip.qml:95-119@cinemate-port`; `qml/ExternalMonitorWindow.qml:1104-1137@cinemate-port`
- port: the same clipped `Item` + inner `Rectangle` copy of the pill shape, `drainOnly` colour rule, 0.85 opacity, 150 ms animation, pasted into both files
- Apertar way: a pill decoration on both screens is one small component used twice: `DroppedFrameWarning` at `qml/CameraPage.qml:2569@upstream-1.6.0` and `qml/ExternalMonitorWindow.qml:1103@upstream-1.6.0`
- why it matters: the copies drift
- rework: add `qml/StatusPillBufferBar.qml` (props `fill`, `drain`, `inset`, `pillRadius`), use it inside `StatusChip` and the EMW pill; register in `CMakeLists.txt` and `qml.qrc`. Keep the EMW pill inline as upstream
- effort S; deliberate no

### UI-camera-qml-F6 [bug, minor] Safety-stop flush: pill says READY while frame, red timecode and audio outline still show recording
- where: `qml/CameraPage.qml:4347,3924,3896,4093@cinemate-port`; `qml/ExternalMonitorWindow.qml:1208,1433@cinemate-port`
- port: `bufferFlushing` / `pillRecordingActive` gate the pill and record button only (`CameraPage.qml:2694,3953`, `EMW:157`); frame, timecode and outline use `root.recording` / `recordingActive`. Core keeps recording true while it drains after its own `record_stop` (`src/ApertarCoreApp.cpp:11094-11110@cinemate-port`)
- Apertar way: no precedent
- why it matters: buffer safety stop with Recording Frame on: green READY pill, but red frame and red timecode stay until Core clears recording
- rework: one `readonly property bool takeActive: root.recording && !root.bufferFlushing` in CameraPage; rename EMW `pillRecordingActive` to `takeActive`; use it for pill, button, frame, timecode and audio outline
- effort S; deliberate no

### UI-camera-qml-F7 [removed-upstream-behaviour, nit] HDMI timecode turns red while recording by default
- where: `qml/ExternalMonitorWindow.qml:1208@cinemate-port`
- port: `color: root.recordingActive && (!settingsBridge || settingsBridge.recordingRedTimecodeEnabled) ? "#ff4d4d" : "white"`; switch default true
- Apertar way: `qml/ExternalMonitorWindow.qml:1129@upstream-1.6.0` `color: "white"`; only the touch timecode red (`qml/CameraPage.qml:3747@upstream-1.6.0`)
- why it matters: the client-monitor default changed
- rework: keep (stated in the commit); list it in the handoff notes as a default change on the HDMI monitor
- effort S; deliberate yes (`da2a9b5`: "HDMI now follows it too")

### UI-camera-qml-F8 [duplication, minor] isoOnAddedCap, built-in ISO list and raw-format test copied into the HDMI window with drift
- where: `qml/CameraPage.qml:534@cinemate-port`; `qml/ExternalMonitorWindow.qml:98,102-110,123-124@cinemate-port`
- port: EMW repeats `isoOnAddedCap` with an inline ISO list and without the `valueSteps` filter; EMW `rawRecordFormat` tests ProRes and "H.264" instead of its own `processedVideoRecordFormat` (`:137`); pre-roll fps `toFixed(3)` instead of `formatFpsValue`
- Apertar way: upstream pairs CameraPage/EMW label code by hand (ui-map 4 "CameraPage vs ExternalMonitorWindow labels"); the copy is the upstream pattern, the drift is not
- why it matters: the two windows show different values after a one-sided edit
- rework: make the EMW copies match CameraPage (same filter, `processedVideoRecordFormat`, same fps formatting) and add the rows to ui-map 4
- effort S; deliberate no

### UI-camera-qml-F9 [slop, nit] Empty if-block with a comment in fpsCeiling()
- where: `qml/CameraPage.qml:912-913@cinemate-port`
- port: `if (root.losslessImx585Mode) { // Core's fps_max carries ... } else if ...`
- Apertar way: `qml/CameraPage.qml:815@upstream-1.6.0` `if (root.losslessImx585Mode) max = Math.min(max, 30.0)`
- why it matters: reads as dead code
- rework: folded into F3
- effort S; deliberate no

### UI-camera-qml-F10 [slop, nit] ControlsWarning.qml in CMakeLists.txt but not in qml.qrc
- where: `CMakeLists.txt:41@cinemate-port`; `qml.qrc@cinemate-port`
- port: new file added to the CMake list only; non-AOT builds (default for cross builds, `CMakeLists.txt:59-63,200-203`) compile `qml.qrc`
- Apertar way: same upstream trap: `DroppedFrameWarning.qml` and `InlineChoice.qml` are in `CMakeLists.txt@upstream-1.6.0` but not in `qml.qrc` (ui-map 4)
- why it matters: a cross (non-AOT) build cannot resolve `ControlsWarning` in CameraPage (probable; unconfirmed by a non-AOT build)
- rework: add `ControlsWarning.qml` to `qml.qrc` (and the two upstream ones, as a separate commit), or leave as upstream and record it
- effort S; deliberate no

### UI-camera-qml-F11 [bug, minor] ISO Auto offered in non-IMX585 lossless modes, where Core still turns it off
- where: `qml/CameraPage.qml:528-532@cinemate-port`; Core `src/camera/CameraController.cpp:3150-3155@cinemate-port`
- port: UI drops Auto only in Clear HDR (`682a186`); port Core keeps auto ISO in lossless only on the IMX585: `if (sensorFamily != SensorFamily::Imx585) settings.isoAuto = false;`
- Apertar way: `qml/CameraPage.qml:511-513@upstream-1.6.0` the picker and Core agree: no Auto in any lossless mode
- why it matters: lossless 4K/2K cDNG on IMX477/IMX283 etc.: operator picks Auto, Core silently sets manual ISO
- rework: in `isoOptions`, also return `entries` without Auto when `(root.losslessFourKMode || root.losslessTwoKMode) && !root.imx585Detected` (or have Core publish an `iso_auto_allowed` scalar and read it, as `isoMax`)
- effort S; deliberate no (`682a186` says "Core keeps auto ISO in IMX585 lossless", the UI change went wider)
