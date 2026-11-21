# Inventory: UI-camera-qml (stage 1, no judging)

Refs: port = `cinemate-port` `7ea9afc`, upstream = `upstream-1.6.0`, merge target = `origin/main` `4415a55`.
Scope read: `diffs/UI-CameraPage.part01.diff` (671 lines, `qml/CameraPage.qml`, +133 / -34 approx) and the diff of
`StatusChip.qml`, `TopDropdownStat.qml`, `ExternalMonitorWindow.qml`, `AudioMeterOverlay.qml`, `DroppedFrameWarning.qml`
(186 +, 41 -). Upstream structure: `llm/ui-map.md` 1.2 (`CameraPage.qml` 4160 lines; option lists `:484-523`, FPS tables
`:646-828`, top stats `:2848-3561`, bottom `:3563`).
Status/test text below is quoted from `fork-log.md` and commit messages. It is intent, not proof.

## 1. Commits that wrote this unit

| Commit | Subject | Files in scope | fork-log status / test |
| --- | --- | --- | --- |
| `68e1a41` | dropped-frames chip shows the number | CameraPage, DroppedFrameWarning, ExternalMonitorWindow | fork-log:241 fork-only, GitHub `drop-frames`, Pi. Msg: "Tested: desk only (needs Core's recording_dropped_frames)" |
| `e061be8` | audio meter outline red only while recording | CameraPage, ExternalMonitorWindow | no fork-log row. Msg has no Tested line |
| `5697b54` | faint red outline on audio meter, with a switch | AudioMeterOverlay, CameraPage, ExternalMonitorWindow (+SettingsPage, SettingsBridge) | no fork-log row. No Tested line |
| `841d0ed` | drop-frames (7 commits squashed): buffer bar, safety-stop pill, Frames/RAM, Log, storage pre-roll | CameraPage, StatusChip, ExternalMonitorWindow (+Settings, bridges) | fork-log:240 fork-only, GitHub `drop-frames`, Pi. No test statement |
| `4959513` | pills READY green while buffer empties | StatusChip, ExternalMonitorWindow | in fork-log:240 text only. No Tested line |
| `96a7aa4` | record button and pill during safety-stop flush | CameraPage, ExternalMonitorWindow | in fork-log:240 text only. No Tested line |
| `ea44bd7` | T45 Controls chip on camera page, read-only Controls card | CameraPage (+ new `ControlsWarning.qml`, CMake, Settings, bridge) | fork-log:214 fork-only. No test statement |
| `7029db1` | UI timecode vs file timecode; tap changes UI one | CameraPage (1 line, +Settings, bridge) | fork-log:204 "Pi only; building 2026-10-29, not tested" |
| `35b31f6` | system-decided values in italics (replaces green) | TopDropdownStat, ExternalMonitorWindow | fork-log:216 "built 2026-10-28" |
| `682a186` | ISO Auto offered everywhere but Clear HDR | CameraPage | fork-log:217 "built 2026-10-28" |
| `7840438` | auto values white; cap green only when camera added it | CameraPage, ExternalMonitorWindow | fork-log:218 "built 2026-10-28" |
| `da2a9b5` | recording frame and red timecode switches | CameraPage, ExternalMonitorWindow (+Settings, bridge) | fork-log:219 "tested 2026-10-28 (Patrik)" |
| `b4591dc` | lossless ISO fallback 1600, as Core | CameraPage | fork-log:220 "tested 2026-10-28 (Patrik)" |
| `1a691a9` | resolution line back to "16-bit" | CameraPage, ExternalMonitorWindow | fork-log:221 "tested (Patrik)" |
| `ed0d7b5` | T33 pickers from value lists, greyed above ceiling | CameraPage, TopDropdownStat (+bridges) | fork-log:222 "tested 2026-10-28 (Patrik)" |
| `2475626` | resolution line "16 b" (reverted by `1a691a9`) | CameraPage, ExternalMonitorWindow | fork-log:223 "built 2026-10-28". Net effect zero |
| `1367b7f` | bit depth and Clear HDR on resolution line | CameraPage, ExternalMonitorWindow | fork-log:224 "tested 2026-10-28 (Patrik)" |
| `f1edf96` | camera-set values green, ISO list from `iso_max`, Lock | CameraPage, ExternalMonitorWindow, TopDropdownStat (+bridge, DisplayConfigBridge) | fork-log:225 "tested 2026-10-28 (Patrik: works well)". Msg: "Tested: desk only". Green later replaced by italics (`35b31f6`) |
| `d1efb67` | 4K Clear HDR 16-bit FPS up to 25 (T32) | CameraPage | fork-log:227 "tested 2026-10-28 (Patrik)". Msg: "not built here" |
| `2d27c46` | 16-bit counts as 16 bits in frame-size estimate | CameraPage | fork-log:234 "done (Patrik, 2026-10-27)" |

All 20 are fork-only in the fork-log. None is in upstream. Messages carry Co-Authored-By Claude Opus 5.5 / Sonnet 5.5.
Commit order is not feature order: `35b31f6` (italic) comes after `f1edf96` (green) and replaces it.

## 2. Operator-visible features

| # | Feature | What the camera operator gets | Commits | Files |
| --- | --- | --- | --- | --- |
| F1 | Pickers from value lists (T33) | FPS, ISO, shutter-angle and WB pickers list the operator's own steps (from `UI.conf`, written by Core's `set_value_steps`), not fixed lists. Built-in lists are the fallback | `ed0d7b5` | CameraPage `valueSteps`, `builtIn*Steps`, `wbOptions`, `fpsOptionEntries`; TopDropdownStat |
| F2 | Greyed values above the mode ceiling, camera-added cap | Entries above the mode's ISO or FPS ceiling are shown greyed and not tappable. The ceiling itself is inserted when not in the list, in italics | `ed0d7b5`, `f1edf96` | CameraPage `cappedValueEntries`; TopDropdownStat delegate |
| F3 | Flicker-free shutter angles | When on, angles for 2x mains frequency at the current fps are merged into the angle list (italic when added). Formula 360 x fps x k / (2 x mains) | `ed0d7b5` | CameraPage `flickerFreeShutterAngles`, `shutterAngleEntries` |
| F4 | Italic camera-decided values | ISO, shutter, WB top stats and the HDMI info row show the value in use in italics when the camera decided it (Clear HDR hold, added cap, ramp angle, auto shutter). Auto modes stay plain | `f1edf96`, `35b31f6`, `7840438` | CameraPage, TopDropdownStat `valueItalic`, ExternalMonitorWindow `cameraSet` |
| F5 | Value in use under Auto | ISO and WB stats show the gain/Kelvin auto is using (`displayValue`), picker selection stays "Auto" | `f1edf96` | CameraPage, TopDropdownStat `displayValue`, ExternalMonitorWindow `isoValue`/`wbValue` |
| F6 | ISO Lock, no Auto in Clear HDR, `iso_max` ceiling | ISO list: `Auto` (+`Lock` while auto), none of Auto in Clear HDR; ceiling from `controlBridge.isoMax`, fallback 1600 in lossless modes else 0 | `f1edf96`, `682a186`, `b4591dc` | CameraPage `isoOptions` |
| F7 | FPS ceiling from Core | `controlBridge.fpsMax` replaces QML-side lossless IMX585 30 fps cap; h264 max still applied; 4K Clear HDR 16-bit stops at 25 in the table too | `ed0d7b5`, `d1efb67` | CameraPage `fpsCeiling`, `maximumSupportedFpsForResolution` |
| F8 | Raw detail on the resolution line | "3840x2160 . 16-bit . Clear HDR" for raw takes (touch format box and HDMI RESOLUTION) | `1367b7f`, `2475626`, `1a691a9` | CameraPage `rawResolutionDetail`; ExternalMonitorWindow `resolutionLineValue` |
| F9 | "Log" in format display | " . Log" appended to the compression sub-text (touch) and to `cDNG` (HDMI) when Core applies Log | `841d0ed` | CameraPage `formatDisplaySubtext`; ExternalMonitorWindow `formatInfoValue` |
| F10 | Time-left estimate follows 16-bit and Log | 16-bit counts as 16 bits; Log uses `cdngLogBits`; `updateMediaEstimate()` re-run on `cdngLogChanged` | `2d27c46`, `841d0ed` | CameraPage `currentRawBitDepthNumber`, `estimatedFrameSizeMB`, Connections |
| F11 | Frame buffer bar in the REC pill | Red bar fills the status pill from the left with buffer fill; gated by setting and `bufferMode != "none"` | `841d0ed` | StatusChip, CameraPage, ExternalMonitorWindow pill |
| F12 | Buffer safety-stop pill | After a safety stop the pill is READY green, text and dot hidden, green bar emptying; no WRITING yellow while draining | `841d0ed`, `4959513` | StatusChip `drainOnly`/`draining`; ExternalMonitorWindow `drainOnly` |
| F13 | Record button during flush | While the buffer flushes Core may still report `recording`; the touch pill and button show READY and a press means START. Record button stays enabled | `96a7aa4` | CameraPage `bufferFlushing`, RecordButton bindings, press handler; ExternalMonitorWindow `pillRecordingActive` |
| F14 | Safety-stop popup | `bufferSafetyStopped(message)` opens the record warning "The write buffer was nearly full. The clip is complete." | `841d0ed` | CameraPage Connections |
| F15 | Blue PRE-ROLL pill | While storage pre-roll runs and no take: blue pill, label PRE-ROLL, wider (118). FPS stat shows pre-roll fps in italics, selection unchanged | `841d0ed` | StatusChip `prerollOnly`; CameraPage FPS stat; ExternalMonitorWindow `externalPreroll`, `fpsDisplayValue` |
| F16 | Dropped-frame count | Chip shows the number instead of "!" (pill grows); "!" when Core sends no count; accessible name "N dropped frames" | `68e1a41` | DroppedFrameWarning `count`; CameraPage; ExternalMonitorWindow |
| F17 | Controls chip | `ControlsWarning` item right of the status chip when `controlsErrors > 0`; moves right by the dropped-frame chip's width | `ea44bd7`, `68e1a41` | CameraPage; new `qml/ControlsWarning.qml` (outside this scope's diff) |
| F18 | Audio-recorded outline | Faint red outline `#73fb2c36` on the audio meter while recording with audio; switch default on | `5697b54`, `e061be8` | AudioMeterOverlay `soundRecorded`; CameraPage (2 meters); ExternalMonitorWindow |
| F19 | Red timecode switch | Timecode red only when `recordingRedTimecodeEnabled` (default true) | `da2a9b5` | CameraPage, ExternalMonitorWindow (HDMI timecode was white before, now red while recording) |
| F20 | Recording frame | Red border `#ff4d4d`, z 10000, width max(4, 0.8 % of short side) on touch screen and HDMI while recording; switch default off | `da2a9b5` | CameraPage (end of file), ExternalMonitorWindow (end of file) |
| F21 | UI timecode tap | Tap on timecode calls `applyTimecodeMode(mode, "ui")` | `7029db1` | CameraPage `toggleTimecodeMode` |
| F22 | HDMI state colours | HDMI pill: blue PRE-ROLL fill/border/dot; READY green during safety stop | `841d0ed`, `4959513` | ExternalMonitorWindow |

## 3. Interfaces added or changed in this unit

QML-facing bridge properties and settings keys that these files read. The bridges themselves are other units; listed here
as consumed, with where the port defines them (checked in `src/SettingsBridge.cpp`, `src/ApertarControlBridge.cpp` @cinemate-port).

| Kind | Name | Used in | Source / evidence |
| --- | --- | --- | --- |
| Core state field read | `iso_max`, `fps_max` | `controlBridge.isoMax`, `.fpsMax` | ApertarControlBridge.cpp:1592, :1594 |
| Core state field read | `iso_actual`, `wb_actual_kelvin`, Clear HDR flags, ramp shutter policy | `isoInUse`, `whiteBalanceInUse`, `isoSetByCamera`, `whiteBalanceSetByCamera`, `shutterSetByCamera` | commit `f1edf96` msg; `:1607` for WB |
| Core state field read | `recording_dropped_frames` | `recordingDroppedFrames` | commit `68e1a41` msg. **probable** for the name in code; not re-grepped |
| Bridge property (control) | `bufferFill`, `bufferMode` (`"none"` hides bar), `bufferSafetyStop`, `storagePrerollActive`, `storagePrerollFps`, `cdngLogActive`, `cdngLogBits`, `controlsErrors`, `rawBitDepth`, `clearHdr`, `recordingDroppedFrames` | CameraPage, ExternalMonitorWindow | all unconfirmed in Core; names from QML use |
| Bridge signal | `cdngLogChanged`, `bufferSafetyStopped(message)` | CameraPage Connections | new in diff |
| Bridge method signature | `applyTimecodeMode(displayValue, target)` (was 1 arg) | CameraPage:`toggleTimecodeMode` | ApertarControlBridge.cpp:750 |
| Bridge method behaviour | `applyIso("Lock")` -> Core `set_iso_auto enabled=false` | ISO picker | commit `f1edf96` msg |
| Settings property (`settingsBridge`) | `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles`, `mainsHz` | CameraPage, ExternalMonitorWindow (`isoSteps`) | SettingsBridge.cpp:1779-1785, read only: "Core's set_value_steps writes these keys and this bridge follows the file" |
| Settings property | `frameBufferBarEnabled` (default false), `recordingFrameEnabled` (default false), `recordingRedTimecodeEnabled` (default true), `audioRecordedOutlineEnabled` (default true) | CameraPage, ExternalMonitorWindow, StatusChip via CameraPage | SettingsBridge.cpp:368-371, setters :1157-1212; written to `m_settings`, synced in/out of preset export :2170-2173, :2262-2265 |
| `UI.conf` keys | `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`, `flickerFreeShutterAngles`, `mainsHz`, `frameBufferBarEnabled`, `recordingFrameEnabled`, `recordingRedTimecodeEnabled`, `audioRecordedOutlineEnabled` | | the QSettings store; file name `UI.conf` per KB, not re-checked |
| QML component property | `StatusChip`: `storagePreroll`, `bufferFill`, `bufferBarVisible`, `bufferDrain`; derived `prerollOnly`, `drainOnly`, `draining` | | StatusChip.qml |
| QML component property | `TopDropdownStat`: `displayValue`, `valueItalic`; options may be string or `{value, enabled, cameraSet}` | | TopDropdownStat.qml |
| QML component property | `AudioMeterOverlay.soundRecorded`; `DroppedFrameWarning.count` | | |
| UI element (new) | buffer bar (Item+Rectangle) in StatusChip and again in HDMI pill; `ControlsWarning`; recording-frame Rectangle x2; `droppedFrameWarning` id | | |
| HTTP route / socket command / env var / file on disk | none in these files | | |

No new socket command, HTTP route or env var in scope. `UI.conf` is read, not written, for the list keys.

## 4. Regions of ORIGINAL code modified

Upstream line numbers from `ui-map.md` 1.2 (@upstream-1.6.0); port line numbers are not given (diff hunks only).

| Region (upstream anchor) | Change | Kind |
| --- | --- | --- |
| `shutterOptions` (`:492`) hard-coded angle list | replaced by `root.shutterAngleEntries()` (photo branch unchanged) | rewritten |
| `isoOptions` (`:511`) two fixed lists (lossless `100-800`, else Auto + 100-51200) | replaced by computed list from steps + `isoMax`; lossless list now 100-1600 by fallback | rewritten; behaviour changed (lossless fallback 800 -> 1600 via `b4591dc`) |
| `fpsOptions` (`:498`) | unchanged line; `availableFpsOptions()` body now derives from `fpsOptionEntries()`; new `fpsPickerOptions` feeds the FPS picker | rewritten function, same name |
| `availableFpsOptions` (`:802`) | preset array and `max` logic split into `fpsCeiling()` + `fpsOptionEntries()` + thin filter. IMX585 lossless 30 cap removed from QML, delegated to Core `fps_max` | rewritten, moved |
| `maximumSupportedFpsForResolution` IMX585 4K (`:733`) | 30 -> 25 when `clearHdrActive` and 16-bit | extended in place |
| `currentRawBitDepthNumber` | added 16-bit branch | extended in place |
| `estimatedFrameSizeMB` (`:896`) | bits overridden by `cdngLogBits` when Log active | extended in place |
| `formatDisplayValue` / `formatDisplaySubtext` (`:514-523`) | resolution + raw detail; " . Log" suffix; ternary parenthesised | extended in place |
| `toggleTimecodeMode` (`:1709`) | second argument "ui" | behaviour changed (Core method signature) |
| `Connections { target: root.controlBridge }` (`:1824-1897`) | two handlers added: `onCdngLogChanged`, `onBufferSafetyStopped` | extended in place |
| `StatusChip` instance (`:2864` area) | `recording` now `&& !bufferFlushing`; four new props | extended in place |
| `DroppedFrameWarning` instance | `id`, `count`; `ControlsWarning` placed before it with margin tied to its width | extended in place |
| FPS / ISO / shutter / WB `TopDropdownStat` (`:2886`, `:2918`, `:2950`, `:2990`) | `displayValue`, `valueItalic`; `options` swapped for computed lists; WB fixed list removed | extended in place |
| `AudioMeterOverlay` instances x2 | `soundRecorded` bound | extended in place |
| Timecode `Text` color (`:~3770`) | red only with switch | behaviour changed (default true keeps upstream) |
| `RecordButton` `enabled`, `recording`, press handler | `bufferFlushing` terms added | behaviour changed |
| End of `Item { id: root }` | `}` moved down, Rectangle appended | extended in place |
| `StatusChip.qml` stateFill/stateBorder/dotFill/chipLabel/width | one more branch each (`prerollOnly`, `draining`) | extended in place |
| `StatusChip.qml` Row | `opacity` bound to `drainOnly` | extended in place |
| `TopDropdownStat.qml` text and delegate | text from `displayValue`, delegate takes object options, `onClicked` passes `optionValue`, comparison uses `optionValue` | extended in place; options contract changed (string or object) |
| `ExternalMonitorWindow.qml` `isoValue`, `wbValue` | prefer `*InUse` | behaviour changed |
| `ExternalMonitorWindow.qml` `externalActiveCapture`, `externalStatus*` | `pillRecordingActive`, `externalPreroll` | extended in place |
| `ExternalMonitorWindow.qml` info list | `cameraSet` per item; italic in value Text | extended in place |
| `ExternalMonitorWindow.qml` HDMI timecode colour | white -> red while recording (switch default true) | behaviour changed vs upstream (upstream HDMI timecode was always white) |
| `DroppedFrameWarning.qml` | width from label; text from count | extended in place |
| `AudioMeterOverlay.qml` | border colour precedence: soundRecorded > muted > default | extended in place |

## 5. New abstractions

| Name | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- |
| `valueSteps(list, fallback)`, `cappedValueEntries(steps, cap, format)`, `fpsOptionEntries()`, `fpsCeiling()`, `shutterAngleEntries()`, `flickerFreeShutterAngles()` (CameraPage functions) | build picker entries from list + ceiling | `ui-map` 1.2: option lists are hard-coded readonly properties (`:484-523`), `availableFpsOptions` `:802`. No function builds entries | CameraPage pickers, `availableFpsOptions` |
| Option object `{value, enabled, cameraSet}` | per-option grey/italic state | upstream `options` are plain strings (TopDropdownStat) | TopDropdownStat, CameraPage |
| `cameraSet` flag + italic convention (`valueItalic`) | mark camera-decided values | none | CameraPage, TopDropdownStat, ExternalMonitorWindow |
| `displayValue` on `TopDropdownStat` | text different from selection | none (value is both) | FPS, ISO, WB stats |
| `bufferFlushing` (CameraPage), `pillRecordingActive` (HDMI), `drainOnly`/`draining`/`prerollOnly` (chip) | derived pill/button states over Core `recording` | upstream has `recording` / `writing` only | CameraPage, StatusChip, HDMI |
| Buffer bar Item+Rectangle, duplicated in `StatusChip.qml` and `ExternalMonitorWindow.qml` | clipped copy of the pill shape | none. HDMI pill is inline Rectangle, separate from `StatusChip` (also true upstream) | two copies |
| `ControlsWarning.qml` | Controls error chip | sibling of `DroppedFrameWarning.qml` (same shape of component) | CameraPage |
| `QML root.builtIn*Steps` arrays | built-in defaults duplicated in QML | existing pattern: hard-coded lists + `Core copy` tables in QML (ui-map 1.2 notes copies of Core values) | CameraPage |
| Recording-frame Rectangle at top of z (10000), twice | border overlay | none | CameraPage, HDMI |

Duplication: ISO ceiling check `isoOnAddedCap` written twice (CameraPage and ExternalMonitorWindow) with the built-in ISO list repeated a third time (inline in HDMI). WB/ISO "in use" fallbacks written twice. Both are copies of Core logic in QML, as upstream already does for FPS tables.

## 6. Removed, narrowed or hidden vs upstream

| What | Where | Effect |
| --- | --- | --- |
| Fixed ISO list `Auto,100..51200` | CameraPage `isoOptions` | replaced by operator list; the built-in list is the fallback. Auto is dropped in Clear HDR |
| Fixed shutter-angle list incl. 11.25 .. 360 | CameraPage | replaced; built-in list drops `"Auto"`-then-list shape to `Auto` + entries. Same angles except built-in list lacks nothing. **Checked**: built-in is the upstream list without `Auto` (added back in function) |
| Fixed WB list | CameraPage | replaced by `wbOptions` from steps |
| `availableFpsOptions()` filtering inline | CameraPage | now via entries; options above ceiling hidden from selectable list, shown greyed in picker |
| IMX585 lossless 30 fps cap in QML | CameraPage `availableFpsOptions` | removed; relies on Core's `fps_max`. With an old Core (no `fps_max`) the cap is gone. `maximumSupportedFpsForResolution` still caps 4K at 30 |
| Lossless ISO list 100-800 | CameraPage `isoOptions` | fallback now 1600 when no bridge `isoMax` and lossless-limited; with bridge `isoMax` it follows Core |
| HDMI `isoValue` / `wbValue` showing the requested value | ExternalMonitorWindow | now shows value in use when Core sends it |
| HDMI "WRITING" yellow during safety-stop flush | pill | hidden (READY green) |
| `REC` pill during safety-stop flush | touch and HDMI | hidden; shown as READY |
| HDMI timecode always white | ExternalMonitorWindow | red while recording by default |
| `TopDropdownStat` string-only options | contract | widened, strings still work |
| 16-bit treated as 12 in size estimate | CameraPage | fixed (extension) |

## 7. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| None in these files for Pi 5 / CM5 / RP1 / PCIe / gpiochip / I2C / RAM / fan | all 6 files | UI-only QML |
| Sensor-specific tables (IMX477, IMX577, IMX294, IMX585) | CameraPage FPS and size helpers | already in upstream; port adds Clear HDR 16-bit 25 fps rule for IMX585 4K, mirroring Core's `tableMaximumFpsForResolution()` |
| Mains frequency 50 or 60 | `settingsState.mainsHz` | region assumption, not board |
| "frame buffer" and "storage pre-roll" depend on Core buffer logic, probably RAM-size dependent | `bufferMode`, `bufferFill` | RAM sizing lives in Core, outside scope |

## 8. Open points for stages 2 and 3

| Point | Why |
| --- | --- |
| Part01 diff only covers CameraPage hunks to the end of file (671 lines, last hunk at the file end). No part02 was read | assumption: the diff is complete (hunk list ends at the recording frame) |
| Names of bridge properties were not grepped for all (`bufferFill`, `cdngLogBits`, ...) | **unconfirmed**; check `src/ApertarControlBridge.hpp` in stage 2 |
| Commit `5697b54` and `e061be8` have no fork-log row and no Tested line | status unrecorded |
| `841d0ed` is a squash of 7 commits; its fork-log row has no test statement | status unrecorded |
| `f1edf96` message says "green", code is italics (`35b31f6`); comments in code say "green" still in `cappedValueEntries` and `TopDropdownStat` ("green when the camera added it", `cameraSet` rendered italic) | stale comments; stage 2 |
| Comments cite internal numbers: "T33", "request 24", "request 25", "Patrik, 2026-10-28" | meaningless to the original developer |
| `2475626` and `1a691a9` cancel each other | commit clarity |
| `ControlsWarning.qml` is a new file outside this diff scope | inventoried by name only |
