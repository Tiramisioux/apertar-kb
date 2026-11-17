# Coding map check: the 17 boxes (const N), the legend and the band names

Slice: every entry of `const N` (`index.html:293-350`): title, sub, path, what, code, tip and the one `up` override.
Plus the legend (`index.html:213-224`, with the line toggles it builds from `LINES` / `GROUPS`, `:278-291`) and the
band names (`:447`).
Map: `/home/user/apertar-coding-map/index.html` at `bff7bd5`. Read-only. `index.html` was not edited.

| Mode | Tree | Ref |
| --- | --- | --- |
| official | `/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream` | `@upstream-1.6.0` (Core `35dbe67`, UI `43888e5`) |
| fork | `/home/user/Apertar-Core`, `/home/user/Apertar-UI` | `@cinemate-port` (Core `01f170c`, UI `7ea9afc`) |

Short names: `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`,
`CS` = `src/ipc/ControlServer.cpp` (Core); `CB` = `src/ApertarControlBridge.cpp`, `PWR` = `src/PreviewWindowRenderer.cpp` (UI).
Line pairs are written `upstream / fork`. Status words: **confirmed** = read in code, **probable** = inferred.

How a field is shown (`index.html:539-559`, `render`): only `code` and `tip` go through `val()`. `title`, `path` and
`what` are printed as written in both modes. An `up:{what:...}` or `up:{path:...}` is ignored today. So a corrected
`what` below is worded to be true in both modes. Where the two modes really differ, the exact pair is given too; it
needs `render` to read `val(it,"what")`.

## Result

17 boxes. 107 fields checked, each in both modes: 87 box fields, 9 legend lines, 5 line-toggle texts, 6 band names.
**18 discrepancies: 4 wrong, 14 imprecise.** No box needs `fork:true`. Three boxes need a new `up` override
(WEBPAGE.tip, DISK.tip, BRIDGE.code).

No box text went stale after the commits the map names for the fork (Core `f4a1393`, UI `7029db1`). Every fork-mode
error below was already false at those commits (checked with `git show f4a1393:...` / `git show 7029db1:...`).

| # | Item | Mode | Severity | One line |
| --- | --- | --- | --- | --- |
| D1 | `N.RENDER.tip` | both | wrong | The WebUI has its own aids (a WebGL shader in `WebControlPage.cpp`). "The WebUI picture has none" is false |
| D2 | `N.DISK.tip` | fork | wrong | The fork's Core refuses `record_start` with no mount or under 1 GB free (`mediaGateError`) |
| D3 | `N.WEBPAGE.tip` | fork | wrong | The file has 20 963 lines on the fork, not "about 12k" |
| D4 | `N.RECS.path` (with `code`) | both | wrong | The code line is in `src/camera/CameraController.cpp`, not in the four folders the path names |
| D5 | `N.RECS.what` | both | imprecise | One encoder per format, not one recorder: `DngRecordingQueue` serves cDNG, lossy DNG and MLV |
| D6 | `N.HWIN.up.tip` | official | imprecise | A new action does not have to go into each normaliser. It needs a branch in `handleSingleHardwareInputAction` |
| D7 | `N.HWIN.tip` | fork | imprecise | "each *Input.cpp" is three of the five `*Input.cpp` files |
| D8 | `N.HWIN.what` | fork | imprecise | The fork's GPIO thread waits for edge events. Only the I2C drivers poll |
| D9 | `N.BTN.what` | fork | imprecise | Same as D8: "Core polls them" is not true for GPIO on the fork |
| D10 | `N.BRIDGE.tip` | both | imprecise | The 10 s class is missing: commands that reconfigure wait up to 10 s, not 3 s |
| D11 | `N.BRIDGE.code` | fork | imprecise | The fork's `applyIso` has a third path: "Lock" sends `set_iso_auto` with `enabled=false` |
| D12 | `N.HUB.what` | fork | imprecise | Six hardware commands answer before `commandMutex_` is taken; five sit in another function |
| D13 | `N.HUB.tip` | both | imprecise | `llm/core-map.md` is in the `apertar-kb` repo, not in Apertar-Core |
| D14 | `N.CAM.what` | both | imprecise | A format change reconfigures only for H.264/ProRes or a size/bit-depth change. Fork: fps can reconfigure (Mode Ladder) |
| D15 | `N.CAM.tip` | both | imprecise | The 25 ms run from the first unsaved change, not from the last one |
| D16 | `N.SENSOR.tip` | both | imprecise | "About one frame" is when the controls leave Core. The picture changes some frames later (probable) |
| D17 | `N.PUB.tip` | both | imprecise | A socket client that stops reading is disconnected, it does not "skip frames" |
| D18 | legend, `index.html:221` | fork | imprecise | The SENSOR pill counts branch `apertar` (`FORKDATA.SENSOR.branch`), the legend says `cinemate-port` |

## D1. `N.RENDER.tip`: the WebUI draws its own aids (confirmed, both modes)

Map (`index.html:342`): `The aids exist only here. The WebUI picture has none.`

| What | upstream / fork | Line |
| --- | --- | --- |
| A canvas over the MJPEG picture | `WCP:2461` / `WCP:4434` | `<canvas class="preview-processed-canvas" id="previewProcessedCanvas"></canvas>` |
| When it is used | `WCP:7865-7877` / `WCP:13052-13064` | `return !!uiState.false_color_enabled \|\| !!uiState.zebra_enabled \|\| !!uiState.grayscale_enabled \|\| !!uiState.focus_peaking_enabled;` |
| The shader, in the page's JS | `WCP:7953` / `WCP:13140` | `"uniform int uZebraEnabled;",` |
| Zebra in the browser | `WCP:8043` / `WCP:13230` | `"  if (uZebraEnabled == 1 && zebraMetric >= uZebraThreshold) {",` |
| Drawn per frame | `WCP:8337`, `:8396` / `WCP:13524`, `:13583` | `function renderProcessedPreviewFrameWebGl(canvas, preview, snapshot, now) {` |

The WebUI also has SMPTE bars and the false-colour legend (`WCP:7824-7841` upstream). It does not apply the LUT: no
`lut` in `WCP:7822-8560` upstream or `WCP:13000-13760` fork. The touch renderer does (`PWR:879-880`,
`if (uLutPreviewEnabled == 1) outColor.rgb = applyPreviewLut(outColor.rgb);`).
Second opinion: `apertar-kb/llm/core-map.md:221` ("WebGL preview processing (peaking, zebra, false colour, ...)").

Corrected field text: `The WebUI draws its own copy of zebra, peaking, false colour and greyscale in the browser: a WebGL shader inside WebControlPage.cpp. A change to an aid goes into both files. The LUT is drawn only here.`

```
    tip:"The WebUI draws its own copy of zebra, peaking, false colour and greyscale in the browser: a WebGL shader inside WebControlPage.cpp. A change to an aid goes into both files. The LUT is drawn only here."},
```

## D2. `N.DISK.tip`: the fork checks the mount and the free space (confirmed, fork)

Map (`index.html:347`): `Core checks neither the mount nor free space before recording. With nothing mounted, files land on the SD card.`

True for official: `record_start` (`App:10623-10713@upstream-1.6.0`) goes straight to `camera_.startRecording` (`App:10709`);
`CC:8219-8263` and `CC:5548-5549` (`clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);`
`std::filesystem::create_directories(clipFolder);`) have no mount or space check.

False for the fork:

| What | Line `@cinemate-port` |
| --- | --- |
| The gate in `handleCommand` | `App:12596-12599`: `if (command.name == "capture_photo" \|\| command.name == "record_start" \|\| (command.name == "timelapse_start" && !camera_.timelapseActive())) {` `if (const std::string gate = mediaGateError(); !gate.empty())` `return errorReply(command.id, gate);` |
| No mount | `App:11374`: `return "No media mounted at " + options_.mediaRoot + ".";` |
| Free space | `App:11378-11382`: `uint64_t minFreeMiB = 1024;` ... `return "Media is full (" + std::to_string(snapshot.freeBytes / (1024 * 1024)) + " MB free).";` |
| Its own comment | `App:11327-11329`: `// The record gate: mounted, alive and not full. One gate in handleCommand covers` `// the socket, the WebUI and the hardware buttons.` |

Already there at `f4a1393` (`App:12245` in that commit).

Corrected field text (fork as written, official through `up`):

```
    tip:"On this fork Core refuses record_start when nothing is mounted at /media/RAW, the card was pulled or less than 1 GB is free, and the reply says why (mediaGateError, fork only).",up:{tip:"Core checks neither the mount nor free space before recording. With nothing mounted, files land on the SD card."}},
```

## D3. `N.WEBPAGE.tip`: 21k lines on the fork (confirmed, fork)

Map (`index.html:307`): `... The file is about 12k lines: grep for an anchor, never read it whole.`

`wc -l src/web/WebControlPage.cpp`: 11 618 `@upstream-1.6.0`, 20 963 `@cinemate-port` (last line of the string:
`WCP:20959`, `)APERTAR";`). At the map's own fork commit `f4a1393` it was 20 893.

```
    tip:"A WebUI change needs a Core rebuild and a Core restart. The file is about 21k lines: grep for an anchor, never read it whole.",up:{tip:"A WebUI change needs a Core rebuild and a Core restart. The file is about 12k lines: grep for an anchor, never read it whole."}},
```

## D4. `N.RECS.path` and `N.RECS.code`: the line lives in CameraController.cpp (confirmed, both modes)

Map (`index.html:335-337`): path `~/ApertarCore/src/cdng/, src/mlv/, src/prores/, src/video/`, code
`encoder.writeDngFile(job.path, job.frame, job.metadata);`

`grep -rnF 'encoder.writeDngFile(job.path, job.frame, job.metadata);' src` gives one hit per tree:
`CC:3744@upstream-1.6.0` / `CC:5291@cinemate-port`, inside `DngRecordingQueue::dngWorkerLoop` (`CC:3697` / `CC:5231`).
None of the four folders holds it. The queue-full log of the tip is in the same class (`CC:3539`, `:3583` / `CC:4827`, `:4982`).

| Lives in | upstream / fork |
| --- | --- |
| `class DngRecordingQueue` (queue, worker threads, cDNG + lossy DNG + MLV) | `CC:3249` / `CC:4189` |
| `class H264PreviewRecorder` | `CC:3930` / `CC:5648` |
| `class ProresRecorder` | `src/prores/ProresRecorder.hpp:16` in both |
| Encoders | `src/cdng/CdngEncoder.cpp:1209` / `:1328` (`void CdngEncoder::writeDngFile`), `src/lossydng/LossyDngEncoder.cpp`, `src/mlv/MlvEncoder.cpp`, `src/prores/ProresEncoder.cpp`, `src/video/*H264*` |

`src/lossydng/` is missing from the path although `what` names lossy DNG.

Corrected `path` (keeps the code line):

```
path:COREP+"src/cdng/, src/lossydng/, src/mlv/, src/prores/, src/video/ (encoders) + src/camera/CameraController.cpp (DngRecordingQueue: the queue and its worker threads)",
```

Alternative that keeps the path as it is: change the code line to one that is in `src/cdng/`,
`void CdngEncoder::writeDngFile(const std::string &path,` (`src/cdng/CdngEncoder.cpp:1209` / `:1328`).

## D5. `N.RECS.what`: one encoder per format, three recorders (confirmed, both modes)

Map (`index.html:336`): `One recorder per format: cDNG and lossy DNG (frame by frame, worker threads), MLV, H.264, ProRes. ...`

`DngRecordingQueue::workerLoop` serves three formats (`CC:3687-3694` / `CC:5221-5228`):
`if (recordingFormat_ == RecordingFormat::Mlv) { mlvWorkerLoop(); return; }` `dngWorkerLoop();`. The lossy encoder is
picked inside the same loop (`CC:3742` / `CC:5280`, `lossyEncoder->writeDngFile(job.path, job.frame, job.metadata);`).
So there are three recorder classes (D4 table) and five encoders.

Corrected field text:

```
    what:"One encoder per format, each in its own folder: cDNG, lossy DNG, MLV, H.264, ProRes. The queue and the worker threads that call them are in CameraController.cpp: DngRecordingQueue writes cDNG and lossy DNG frame by frame, and MLV. Audio is a WAV beside the clip.",
```

## D6. `N.HWIN.up.tip`: where a new action goes on official Apertar (confirmed, official)

Map (`index.html:311`, `up.tip`): `Action names are normalised in each *Input.cpp (normalizeSingleAction), so a new action goes into each one. The hardware file is read once at start: restart Core after a change.`

| Fact `@upstream-1.6.0` | Line |
| --- | --- |
| `normalizeSingleAction` exists in three files | `src/hardware/GpioInput.cpp:108`, `NeoRotary4Input.cpp:121`, `Pcf8574Input.cpp:140` |
| Not in the other two `*Input.cpp` | `GroveAnalogInput.cpp` (analog targets, no actions), `StandbyPowerButtonInput.cpp`: no hit |
| A name the table does not know passes through | `GpioInput.cpp:201`, `NeoRotary4Input.cpp:214`, `Pcf8574Input.cpp:241`: `return action;` |
| What an action does | `App:8660`: `void ApertarCoreApp::handleSingleHardwareInputAction(const std::string &action)`, one `if (action == "...")` per action, ends at `App:8954`: `"Hardware input action ignored: unknown action '"` |
| A shipped action that is in no normaliser | `App:8687`: `if (action == "ev_up" \|\| action == "ev_down") {`; `grep -rn 'ev_up' src/hardware` = no hit |

So the normalisers hold aliases only. Listing a name there is upstream's habit (`if (action == "guides") return "guides";`,
`NeoRotary4Input.cpp:162-163`), not a need. The branch in `handleSingleHardwareInputAction` is the need.
Second opinion: `apertar-kb/llm/flows.md:164` ("Unknown names pass through unchanged").
The second sentence is right: the drivers start once (`App:6881-6893`), `GpioInput::start` loads the file there
(`GpioInput.cpp:329-332`, `config_ = loadConfig();`), nothing restarts them.

Corrected `up.tip`: `GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp each hold their own copy of the alias table (normalizeSingleAction); a name they do not list passes through unchanged. What an action does is a branch in handleSingleHardwareInputAction (ApertarCoreApp.cpp), so a new action goes there. The hardware file is read once at start: restart Core after a change.`

## D7. `N.HWIN.tip`: "each *Input.cpp" (confirmed, fork)

Map (`index.html:311`, fork `tip`): `... (fork only; upstream has a copy in each *Input.cpp). ...`

Three of five, see D6. The rest of the fork tip is right: `src/hardware/ActionCatalog.hpp:32` (`kSpecs`), `:123`
(`canonicalAction`), used by all three drivers (`GpioInput.cpp:112-115`, `NeoRotary4Input.cpp:123-126`,
`Pcf8574Input.cpp:142-145`); the controls worker `App:12244` (`runControlsWorker`) and `App:12273`
(`applyHardwareText`, comment `App:12270`: "Restart only the driver groups whose sections changed").

Source line for `index.html:311` (D6 and D7 together):

```
    tip:"On this fork every action name lives in ActionCatalog.hpp (fork only; upstream has a copy in GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp). A saved apertar-hardware.conf applies without a Core restart (fork only): a controls worker restarts just the input group that changed.",up:{tip:"GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp each hold their own copy of the alias table (normalizeSingleAction); a name they do not list passes through unchanged. What an action does is a branch in handleSingleHardwareInputAction (ApertarCoreApp.cpp), so a new action goes there. The hardware file is read once at start: restart Core after a change."}},
```

## D8, D9. `N.HWIN.what`, `N.BTN.what`: GPIO is not polled on the fork (confirmed, fork)

Map: `Poll threads read I2C or GPIO and turn a press or a turn into an action name ...` (`:309`) and
`... Core polls them itself; the UI is not involved.` (`:299`).

Official: all three drivers poll. `GpioInput.cpp:683` (`readLineValues`) then `:740`
(`std::this_thread::sleep_for(std::chrono::milliseconds(config_.pollMs));`), `Pcf8574Input.cpp:523`, `NeoRotary4Input.cpp:711`.

Fork, GPIO only (`src/hardware/GpioInput.cpp@cinemate-port`):

| Line | Text |
| --- | --- |
| `:518` | `request.config.flags \|= GPIO_V2_LINE_FLAG_EDGE_RISING \| GPIO_V2_LINE_FLAG_EDGE_FALLING;` |
| `:735-737` | `// Edge events first, so the thread sleeps until a pin changes, ...` `// A chip that cannot give them (no interrupt behind its lines) is read every poll_ms instead.` `edgeEvents = requestLines(offsets, true, &lineFd, &errorMessage);` |
| `:821-823` | `if (edgeEvents) {` `pollfd ready{lineFd, POLLIN, 0};` `const int count = ::poll(&ready, 1, sleepMs(...));` |

Commit `0c49601` "hw: GPIO buttons and encoders wait for edge events instead of polling" (already in `f4a1393`).
The I2C drivers still poll on the fork (`Pcf8574Input.cpp:471`, `NeoRotary4Input.cpp:647`).

`what` cannot be overridden per mode, so one wording for both:

```
    what:"PCF8574 buttons, NeoRotary4 encoders and GPIO buttons. Core reads them itself; the UI is not involved."},
```

```
    what:"One thread per input driver reads I2C or GPIO and turns a press or a turn into an action name such as iso_up or record_toggle.",
```

## D10. `N.BRIDGE.tip`: three timeouts, not two (confirmed, both modes)

Map (`index.html:315`): `sendCoreCommand blocks the GUI thread until Core replies: up to 3 s, 60 s for record_stop.`

`CB:1029-1031@upstream-1.6.0` / `CB:1165-1167@cinemate-port`:

```
    const int replyTimeoutMs = commandName == QStringLiteral("record_stop") ? 60000
        : commandName == QStringLiteral("calibrate_gyro") ? 8000
        : (reconfigureCommand ? 10000 : 3000);
```

`reconfigureCommand` (`CB:1016-1028` / `CB:1151-1164`): `set_resolution`, `set_capture_mode`, `set_raw_bit_depth`,
`set_record_format`, `set_tuning_file`, the two colour profiles, `set_h264_resolution`, `capture_photo`,
`timelapse_start`, `wake`, `enter_standby`, `apply_preset` (fork adds `set_clear_hdr`).
Second opinion: `apertar-kb/architecture/ui.md:216`.

Corrected field text: `sendCoreCommand blocks the GUI thread until Core replies: up to 3 s, 10 s for a command that reconfigures the camera (set_resolution, set_record_format, …), 60 s for record_stop.`

## D11. `N.BRIDGE.code`: "Lock" on the fork (confirmed, fork)

Map (`index.html:314`): `bool ApertarControlBridge::applyIso(…)       // "Auto" → set_iso_auto, else set_iso`

Official: right (`CB:291-316`). Fork `CB:300-334`: a third branch first, `CB:303-304`:
`if (displayValue == QStringLiteral("Lock")) {` `if (!sendCoreCommand(QStringLiteral("set_iso_auto"), QJsonObject{{QStringLiteral("enabled"), QStringLiteral("false")}}))`.
"Lock" is an option of the fork's ISO dropdown (`qml/CameraPage.qml:531`, `(root.iso === "Auto" ? ["Auto", "Lock"] : ["Auto"])`).
So "else set_iso" is false for one value. Already in `7029db1` (`CB:303`).

```
    code:"bool ApertarControlBridge::applyIso(…)       // \"Auto\" → set_iso_auto, \"Lock\" → set_iso_auto enabled=false, else set_iso\nbool ApertarControlBridge::sendCoreCommand(…)  // one socket per command",
    tip:"...",up:{code:"bool ApertarControlBridge::applyIso(…)       // \"Auto\" → set_iso_auto, else set_iso\nbool ApertarControlBridge::sendCoreCommand(…)  // one socket per command"}},
```

## D12. `N.HUB.what`: six commands answer before the lock on the fork (confirmed, fork)

Map (`index.html:317`): `... One long function, one if-branch per command, guarded by commandMutex_.`

Official: right. `App:9091-9093`: `std::string ApertarCoreApp::handleCommand(const ControlCommand &command)` `{`
`std::lock_guard<std::mutex> commandLock(commandMutex_);`.

Fork `App:12559-12571@cinemate-port`:

```
std::string ApertarCoreApp::handleCommand(const ControlCommand &command)
{
    // The read-only hardware commands answer before the command lock, so a slow one never holds up a button.
    if (const auto reply = handleReadOnlyHardwareCommand(command))
        return *reply;
    // The WebUI's Try and Remote controls: the actions are commands that take the command lock themselves.
    if (command.name == "test_input")
        return testInputReply(command);
    ...
    std::lock_guard<std::mutex> commandLock(commandMutex_);
```

`handleReadOnlyHardwareCommand` (`App:12418`) holds `get_controls` (`:12420`), `controls_history` (`:12458`),
`controls_last_input` (`:12476`), `scan_i2c` (`:12486`), `list_actions` (`:12534`). The grep of the tip still lists all of
them. Already in `f4a1393` (`App:12209-12217` there).

One wording true in both modes:

```
    what:"Every command from every entry point ends up here. One long function with one if-branch per command. Every command that changes something runs under commandMutex_.",
```

Exact pair, if `render` learns `val(it,"what")`: fork `... guarded by commandMutex_. Six hardware commands that only read (get_controls, list_actions, …) answer before the lock (fork only).`, `up.what` = today's text.

## D13. `N.HUB.tip`: where `llm/core-map.md` is (confirmed that it is not in Core; probable for the camera path)

Map (`index.html:319`): `... Use the chapter map in llm/core-map.md; never read the file whole.`

The box path is `~/ApertarCore/src/ApertarCoreApp.cpp`. Apertar-Core has no `llm/` folder in either tree
(`ls`: `CMakeLists.txt LICENSE README.md config include scripts src`, fork adds `third_party tools`). The file is
`apertar-kb/llm/core-map.md`; on the camera the KB is `~/apertar-kb` (`apertar-kb/llm/README.md:61-62`, a KB statement,
not checked on a Pi). Its line numbers are against `upstream-1.6.0` (`llm/README.md:53-58`); on the fork only the
anchors hold.

Corrected field text: `List all commands: grep -n 'command.name == "' ApertarCoreApp.cpp. Use the chapter map in the knowledge base (~/apertar-kb/llm/core-map.md); never read the file whole.`

## D14. `N.CAM.what`: what reconfigures (confirmed, both modes; one part fork only)

Map (`index.html:321`): `... ISO, shutter, WB and fps are control-only; resolution, format and bit depth need a full reconfigure.`

| Setting | upstream / fork | Line |
| --- | --- | --- |
| ISO, shutter, WB | `CC:7785`, `:7824`, `:7903` / `CC:11143`, `:11205`, `:11289` | `return applySettingsLocked(next, false);` (right) |
| Resolution, bit depth | `CC:7738`, `:8147` / `CC:10680`, `:11612` | `return applySettingsLocked(next, true);` (right) |
| Format | `CC:7967-7970` / `CC:11387-11390` | `const bool requiresReconfigure = currentUsesProcessedStream \|\| nextUsesProcessedStream \|\| next.resolution.width != settings_.resolution.width \|\| ... \|\| next.rawBitDepth != settings_.rawBitDepth;` |
| fps, official | `CC:7771` | `return applySettingsLocked(next, false);` (right) |
| fps, fork | `CC:10777` | `const bool applied = applySettingsLocked(next, rung != nullptr, commit);` with the comment at `CC:10759`: `// T34: the FPS moved the camera to another rung; one reconfigure applies the whole mode` |

So cDNG to MLV at the same size and bit depth is control-only in both trees; only H.264/ProRes (a processed stream)
or a per-format profile with another size or bit depth reconfigures. On the fork an fps change reconfigures when the
Mode Ladder is on (off by default: `src/camera/ModeLadder.hpp:47`, `bool enabled = false;`).
Second opinion: `apertar-kb/architecture/core.md:363` ("resolution, bit depth, format class, ...").

One wording true in both modes:

```
    what:"Holds the capture settings and talks to libcamera. ISO, shutter and WB are control-only, and fps normally is too. Resolution, bit depth and a switch between RAW and H.264/ProRes need a full reconfigure.",
```

Exact pair, if `render` learns `val(it,"what")`: fork `... ISO, shutter and WB are control-only, and so is fps unless the Mode Ladder moves the camera to another sensor mode (fork only). Resolution, bit depth and a switch between RAW and H.264/ProRes need a full reconfigure.`, `up.what`: `... ISO, shutter, WB and fps are control-only; resolution, bit depth and a switch between RAW and H.264/ProRes need a full reconfigure.`

## D15. `N.CAM.tip`: the 25 ms window (confirmed, both modes, minor)

Map (`index.html:323`): `Settings are also saved to ~/.config/apertar-core/camera_settings.conf, 25 ms after the last change.`

Path right (`CC:346-350` / `CC:421-425`). The wait, `CC:852-856` / `CC:1063-1067` (the class is identical in both trees):

```
            if (!flushRequested_) {
                cv_.wait_for(lock, std::chrono::milliseconds(25), [this]() {
                    return stopRequested_ || flushRequested_;
                });
            }
```

A later `schedule()` only notifies; the predicate stays false, so the deadline is not moved. The file is written
25 ms after the first unsaved change, with the newest values. A change 20 ms after the first is on disk 5 ms later.

Corrected field text: `Settings are also saved to ~/.config/apertar-core/camera_settings.conf, about 25 ms after a change.`

## D16. `N.SENSOR.tip`: one request is not one frame of delay (confirmed in code; the frame count is probable)

Map (`index.html:330`): `New controls land one request after they are set, about one frame.`

| Step | Where | Line |
| --- | --- | --- |
| Controls go into the next request Core hands back | `CC:6505-6506@upstream-1.6.0` / `CC:8986-8987@cinemate-port` | `if (!pendingControls_.empty()) {` `request->controls().merge(pendingControls_);` |
| Requests in flight | `CC:1023` / `CC:1334`, `:1338`, `:1456-1457` | `constexpr unsigned int kConfiguredBufferCount = 4;` (fork: 8 in Clear HDR; `// Every buffer is attached to its own libcamera request, so this is also the number of requests in flight.`) |
| libcamera queues the request at the back | `/home/user/tiramisioux/libcamera` `src/libcamera/pipeline/rpi/common/pipeline_base.cpp:836@6b0b49f` | `data->requestQueue_.push(request);` |
| Its controls reach the IPA when it is at the front | `src/libcamera/pipeline/rpi/pisp/pisp.cpp:3122`, `:3182@6b0b49f` | `Request *request = requestQueue_.front();` ... `params.requestControls = request->controls();` |
| Core itself knows about sensor delays | `CC:6540-6541@upstream-1.6.0` / `CC:9021-9022@cinemate-port` | `// ISP WB and sensor gain have different control delays. Settle` `// both before scheduling the one-request shutter pulse.` |

"One request after they are set" is right for the hand-over to libcamera. The picture changes after the requests
queued ahead of it and the sensor's own control delay. Not measured: this machine has no camera. To settle it on a Pi:
record a short cDNG take, send `set_iso` in the middle, count the frames until the DNG gain tag changes.

Corrected field text (says only what the code shows): `New controls ride on the next request Core hands back to libcamera, so they leave Core within one frame. When the picture changes is up to libcamera and the sensor: other requests are already queued and the sensor applies gain and exposure with its own delay.`

## D17. `N.PUB.tip`: a slow socket reader is dropped (confirmed, both modes)

Map (`index.html:334`): `Only the newest frame is kept. A slow reader skips frames instead of queueing them.`

Right for the two hand-offs inside Core: `App:6977-6986` / `App:8241-8250` (`pendingPreviewFrame_ = std::move(frame);`
replaces the one waiting frame) and the MJPEG stream (`App:8288` / `App:9966`, `jpegBytes = latestMjpegFrame_;`).

Not right for a socket client. `CS:24-29@upstream-1.6.0` / `CS:27-32@cinemate-port`:

```
        // Never let a stalled preview client block camera event delivery.
        const ssize_t written = ::send(fd, data, remaining, MSG_NOSIGNAL | MSG_DONTWAIT);
        ...
        if (written <= 0)
            return false;
```

and `CS:190-191` / `CS:193-194`: `if (client->closed || !sendLineWithFds(client->fd, line, fds))` `removeClient(client);`.
Lines for a slow client queue in the socket buffer; when it is full the client is shut down.

Corrected field text: `Only the newest frame is kept, so the publisher and a slow browser skip frames instead of queueing them. A socket client that stops reading is disconnected: Core never waits for a reader.`

## D18. Legend line 221: which branch the pills count (confirmed, fork)

Map (`index.html:221`): `N commits that are Tiramisioux dev-fork only (branch cinemate-port)`

`FORKDATA.SENSOR` (`index.html:420`): `"repo": "imx585-v4l2-driver", "count": 1, ... "branch": "apertar"`. The panel of that
box says "branch apertar" (`forkSection`, `:533-537`). So one pill is not on `cinemate-port`.
In the repos the driver's port work is on `cinemate-port` too: `/home/user/imx585-v4l2-driver` `cinemate-port` `cd548ef`
is 55 commits ahead of `origin/apertar` `e5b74d3` (`git log --oneline origin/apertar..cinemate-port | wc -l`).

Two ways to make it true. Either `FORKDATA.SENSOR` follows the driver's `cinemate-port` (then the legend stays), or:

```
<span class="swatch forklegend"><span class="forktag" style="margin:0">fork · N</span>N commits that are Tiramisioux dev-fork only (branch <code>cinemate-port</code>; the imx585 driver: branch <code>apertar</code>)</span>
```

## Checked and correct

Every code literal was found with `grep -nF` in the file its box names, in both trees (RECS is D4):

| Box | Literal | upstream | fork |
| --- | --- | --- | --- |
| BROWSER | `http://apertar.local:8000` | Core `README.md:125`; port `src/ApertarCoreApp.hpp:36` | `src/ApertarCoreApp.hpp:42` |
| QML | `root.controlBridge.applyIso(v)` | UI `qml/CameraPage.qml:2942` | `qml/CameraPage.qml:3104` |
| WEBPAGE | `window.setInterval(() => fetchState(true), 1000);` | `WCP:11609` | `WCP:20954` |
| HWIN | `rotationCallback_(action);` | `src/hardware/NeoRotary4Input.cpp:664` | `:584` |
| BRIDGE | `bool ApertarControlBridge::applyIso(` / `::sendCoreCommand(` | `CB:291`, `CB:1013` | `CB:300`, `CB:1148` |
| HUB | `if (command.name == "set_iso") {` | `App:9242` | `App:12968` |
| CAM | `std::max(1.0f, static_cast<float>(settings.iso) / 100.0f)` in `controlsForSettings` | `CC:2060` (function `CC:2005`) | `CC:2453` (`CC:2398`) |
| UICONF | `zebraEnabled` in `[General]` | UI `src/SettingsBridge.cpp:603`; Core `App:1901` | `:613`; `App:2284` |
| PUB | `controlServer_.broadcastWithFds(out.str(), attachedFds);` | `App:10940` | `App:14998` |
| RENDER | `if (uZebraEnabled == 1 && exposureLuma >= uZebraThreshold)` | `PWR:896` | `PWR:896` (file identical) |

| Box | Statement | Result | Evidence (upstream / fork) |
| --- | --- | --- | --- |
| TOUCH | ISO on the camera page, 800 is an option | right in both | UI `qml/CameraPage.qml:511-513` / `:519`, `:525-532` |
| BROWSER | Core serves the WebUI on port 8000 | right in both | `src/main.cpp:35`, `ApertarCoreApp.hpp:36` / `:42` |
| BTN | The three input kinds; Core reads them, not the UI | right (wording: D9) | `App:6886-6888` / drivers started by Core only |
| QML | A tapped option calls a C++ bridge method | right in both | `qml/Main.qml:500` (`controlBridge: apertarControlBridge`), UI `src/main.cpp:388` / `:392` |
| QML.tip | QML is compiled into the binary | right in both | `CMakeLists.txt:8`, `:184-199` / `:187-202`; `src/main.cpp:397` / `:401` (`qrc:/qml/Main.qml`) |
| WEBPAGE | One C++ string; POST for commands; state every second | right in both | `WCP:7` (`static const char page[] = R"APERTAR(`), `WCP:9123-9124` / `:14430-14431`, `WCP:11609` / `:20954` |
| HWIN.tip (fork) | ActionCatalog.hpp holds the names; a saved file applies without a restart | right (wording: D7) | `src/hardware/ActionCatalog.hpp:32`, `:123`; `App:12244`, `:12273` |
| HWIN.up.tip | The hardware file is read once at start | right | `App:6881-6893@upstream-1.6.0` |
| BRIDGE | One JSON command, waits for the reply; events become Qt properties; one socket per command | right in both | `CB:1034-1035` / `CB:1170-1171` (`QLocalSocket socket;`), `CB:122` / `CB:124`, `CB:2239-2246` / `CB:2481-2488` |
| HUB | Every entry point ends in `handleCommand` | right in both | callers `App:7049`, `:7067`, `:7090`, `:8462` / `App:8313`, `:8331`, `:8354`, `:10122` |
| HUB.tip | The grep lists the commands | right in both | 106 / 143 hits |
| CAM | ISO to AnalogueGain in `controlsForSettings`; file path | right in both | `CC:2059-2060` / `CC:2452-2453`; `CC:350` / `CC:425` |
| UICONF | Path, `[General]`, who writes, who watches, no event | right in both | UI `src/SettingsBridge.cpp:287` (`m_settings("CinePi", "UI")`), `:413-431` / `:418-436`; Core `App:346` / `App:538`, `App:1850-1935` / `App:2233`; no event in `handleUiToggle` `App:9478-9491` / `App:13341-13354` |
| SENSOR | IMX585, libcamera, PiSP; path | right for the rig the map describes | driver path from `apertar-kb/llm/README.md:61-62` (probable) |
| PUB | Two outputs; both functions are in `ApertarCoreApp.cpp` | right in both | `App:10891`, `:8262` / `App:14949`, `:9940` |
| RECS.tip | Queue full: frame dropped, `ApertarCore drop[queue-full]` | right in both (fork default buffer mode `frames`) | `CC:3539`, `:3583` / `CC:4827`, `:4982`; `CC:5502` (`then the default (frames)`) |
| RECS | Audio is a WAV beside the clip | right in both | `src/audio/AudioRecordingSession.cpp:235` / `:251` |
| RENDER | dma-buf to GPU texture, under the QML scene, four aids as shaders | right in both | `PWR:405`, `:1769`, `:879-904` |
| BROWSEROUT | At most 640x360, only while watched | right in both | `App:60-61`, `:8100` / `App:84-85`, `:9774` |
| DISK | `/media/RAW`, mounted by `apertar-cfe-automounter` | right in both | UI `src/CfeAutomounter.cpp:109`, `:619` / `:621`; `CMakeLists.txt:149-160` / `:152-163` |
| DISK.tip (official) | No mount or space check in Core | right | D2 |
| SCREEN | DRM/KMS, no window manager | right in both | UI `run_pi_direct.sh:207-208` (`QT_QPA_PLATFORM=eglfs`, `eglfs_kms`), identical in both trees |

Legend (`:213-224`): the six colour meanings match the `kind` of every box. `~/ApertarUI`: UI `run_pi_direct.sh:5`
(`$HOME/ApertarUI/build/Apertar-UI`). `~/ApertarCore`: Core `scripts/start-apertar-core.sh:4`
(`/home/pi/ApertarCore-build/apertar-core`) with `README.md:206` (`cmake -S . -B ../ApertarCore-build`), and
`apertar-kb/llm/README.md:61-62`. The fork line is hidden in official mode (`:925`). Line toggles ("Commands in",
"State coming back", "Pictures", "Via UI.conf", "thin = inside a program, thick = between") match the `k` of the arrows.

Band names (`:447`): YOU (TOUCH, BROWSER, BTN), FRONT ENDS (QML, WEBPAGE, HWIN), THE HUB (HUB), CAMERA (CAM),
PICTURE OUT (PUB, RECS), WHERE IT ENDS UP (RENDER, BROWSEROUT, DISK, SCREEN). All fit their rows. No error.

Looked at and not reported (true, only incomplete):

- SENSOR names the IMX585 only. Core also handles IMX477/577/294 (`CC:1882-1888@upstream-1.6.0`) and the fork adds
  IMX283 (`CC:2269-2276`). The map describes one rig (footer: "Raspberry Pi 5").
- BTN and HWIN leave out GPIO encoders and the Grove analog input (`src/hardware/GroveAnalogInput.cpp`).
- "the UI is not involved": the UI reads the Pi's own power button (`UI src/PowerButtonBridge.cpp:85`), which is not one
  of the three input kinds the box lists.

## Outside the slice (seen in passing, for the owners of those parts)

| Where | What |
| --- | --- |
| `index.html:660-661`, `:916` (`srcNote`, `SRC.fork.foot`) | Name Core `f4a1393` and UI `7029db1`. `cinemate-port` is at `01f170c` (5 commits later) and `7ea9afc` (22 later) |
| `FORKDATA.SENSOR`, `SRC.fork.foot`, `README.md:27` | The driver's fork branch is given as `apertar`. The port branch is `cinemate-port` (D18) |
| `RECIPES.r4` `up.forget` and the HWIN step's `up.note` | "A new action name goes into all three *Input.cpp files": same root as D6. Needed for aliases only |
| `E.c9.what` | "so the change lands about one frame later": same root as D16 |

## Side note: the GPIO chip key (user request, task "Reinsert the GPIO chip definition in Controls")

The map does not mention the chip anywhere (BTN, HWIN, arrow c6). Facts for whoever touches it:

| Fact | upstream / fork |
| --- | --- |
| Key `chip` (also `gpiochip`, `gpio_chip`) in the GPIO sections, default `auto` | `src/hardware/GpioInput.cpp:431-432` / `:343-344`: `} else if (key == "chip" \|\| key == "gpiochip" \|\| key == "gpio_chip") {` `config.chipPath = trimAscii(value).empty() ? "auto" : trimAscii(value);` |
| Any chip path is used as given | `GpioInput.cpp:507-508` / `:465-466`: `if (config_.chipPath != "auto")` `return requestLinesFromChip(config_.chipPath, ...);` |
| Same key for the trigger and the tally LED | `TriggerOutput.cpp:311` / `:305`, `RecordingIndicatorOutput.cpp:319`, `:347` / `:312`, `:340` |
| The fork's Controls card leaves it out | `src/hardware/ControlsModel.hpp:257-263@cinemate-port`: `};   // poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither` |
| A chip without interrupts is read every `poll_ms` on the fork | `GpioInput.cpp:736-744@cinemate-port` |

If the chip field comes back on the Controls card, HWIN.tip (fork) is the place for one sentence, for example:
`GPIO lines come from the chip named by chip= (default auto = the Pi header), so another gpiochip can be used.`
Not added to the discrepancy list: the map says nothing false about it.

## Recheck

Second checker. Every item re-derived from the code in both trees (`@upstream-1.6.0`: `/home/user/wt/core-upstream`,
`/home/user/wt/ui-upstream`; `@cinemate-port`: `/home/user/Apertar-Core` `01f170c`, `/home/user/Apertar-UI` `7ea9afc`).
`render` (`index.html:539-559`) confirmed: only `code` and `tip` go through `val()`; `path` and `what` print as written.

| # | Verdict | Why |
| --- | --- | --- |
| D1 | stands | WebUI shader has `uZebraEnabled`, `uFocusPeakingEnabled`, `uGrayscaleEnabled`, `uFalseColorEnabled` uniforms, no LUT uniform (`WCP:7951-7974@upstream-1.6.0`); `previewProcessingEnabled` `WCP:7865-7877` / `WCP:13052-13064`. LUT only in `PWR:879` |
| D2 | stands | `mediaGateError` `App:11359@cinemate-port`, gate `App:12596-12599`, "No media mounted at" `:11374`, 1024 MiB floor `:11378`. `mediaRoot = "/media/RAW"` `ApertarCoreApp.hpp:40`. No `mediaGateError` upstream |
| D3 | stands | `wc -l`: 11 618 upstream, 20 963 fork |
| D4 | corrected differently | Fact confirmed (`CC:3744` / `CC:5291`, no hit in the four folders). Path shortened |
| D5 | corrected differently | Fact confirmed (`mlvWorkerLoop();` `CC:3690` / `CC:5224`). The first correction implied the ProRes recorder is in `CameraController.cpp` too; it is `src/prores/ProresRecorder.cpp`. Reworded |
| D6 | stands | `normalizeSingleAction` is an alias table that ends `return action;` (`GpioInput.cpp:201`, `NeoRotary4Input.cpp:214`, `Pcf8574Input.cpp:241`); behaviour in `handleSingleHardwareInputAction` `App:8660`, unknown name logged `App:8954` |
| D7 | stands | Three of five `*Input.cpp` hold the copy (`GroveAnalogInput.cpp`, `StandbyPowerButtonInput.cpp` do not). Rest of fork tip right: `ActionCatalog.hpp:123` `canonicalAction`, used by the three drivers (`GpioInput.cpp:114`, `NeoRotary4Input.cpp:125`, `Pcf8574Input.cpp:144`); `runControlsWorker` `App:12244`, comment `App:12270` |
| D8 | corrected differently | Fact confirmed (`GpioInput.cpp:517-518`, `:735-737`, `:821-823@cinemate-port`). "One thread per input driver" not verified; "Input threads" used instead |
| D9 | stands | Same evidence as D8 |
| D10 | stands | `CB:1029-1031` / `CB:1165-1167`; `reconfigureCommand` holds `set_resolution`, `set_record_format` (`CB:1016-1028@upstream-1.6.0`) |
| D11 | stands | Fork `CB:303-304`: `if (displayValue == QStringLiteral("Lock")) {` then `set_iso_auto` with `enabled=false`. Upstream `CB:291` has no Lock |
| D12 | stands | Fork `App:12559-12571`: `handleReadOnlyHardwareCommand` (get_controls, controls_history, controls_last_input, scan_i2c, list_actions, `App:12418`) and `test_input` before `std::lock_guard<std::mutex> commandLock(commandMutex_);` |
| D13 | stands | No `llm/` in either Core tree; the file is `apertar-kb/llm/core-map.md`; on the Pi the KB is `~/apertar-kb` (`apertar-kb/llm/README.md:61-62`, KB statement) |
| D14 | stands | `requiresReconfigure` `CC:7964-7969@upstream-1.6.0`; `setFps` `applySettingsLocked(next, false)` upstream; fork `CC:10777` `applySettingsLocked(next, rung != nullptr, commit)`, ladder off by default `ModeLadder.hpp:47` |
| D15 | stands | `cv_.wait_for(lock, std::chrono::milliseconds(25), ...)` with predicate on `stopRequested_ \|\| flushRequested_` (`CC:852-855@upstream-1.6.0`); a later change does not move the deadline |
| D16 | stands | Controls merged in `requeueRequest` (`CC:6497-6508@upstream-1.6.0`); that request goes to the back behind the others in flight (`kConfiguredBufferCount = 4`, `CC:1023`). "About one frame" for the picture is not what the code gives |
| D17 | stands | `sendLine` uses `MSG_DONTWAIT`, `written <= 0` -> `return false` (`CS:25-29@upstream-1.6.0`, `CS:28-32@cinemate-port`); caller `removeClient(client)` (`CS:190-191` / `CS:193-194`) |
| D18 | stands | `FORKDATA.SENSOR.branch` = `"apertar"` (`index.html:420`); legend says `cinemate-port`. Driver `cinemate-port` is 55 commits past `origin/apertar` `e5b74d3` |

## Final discrepancies

All 18 stand (3 with a reworded correction). Exact replacement text per field.

1. **N.RENDER.tip**, both, wrong.
   Map: `The aids exist only here. The WebUI picture has none.`
   Code: `src/web/WebControlPage.cpp:8043@upstream-1.6.0` / `:13230@cinemate-port`: `"  if (uZebraEnabled == 1 && zebraMetric >= uZebraThreshold) {",`
   Corrected: `The WebUI draws its own copy of zebra, peaking, false colour and greyscale in the browser: a WebGL shader inside WebControlPage.cpp. A change to an aid goes into both files. The LUT is drawn only here.`

2. **N.DISK.tip**, fork, wrong.
   Map: `Core checks neither the mount nor free space before recording. With nothing mounted, files land on the SD card.`
   Code: `src/ApertarCoreApp.cpp:12598@cinemate-port`: `if (const std::string gate = mediaGateError(); !gate.empty())`; `:11374`: `return "No media mounted at " + options_.mediaRoot + ".";`
   Corrected: `tip:"On this fork Core refuses record_start when nothing is mounted at /media/RAW, the card was pulled or less than 1 GB is free, and the reply says why (mediaGateError, fork only).",up:{tip:"Core checks neither the mount nor free space before recording. With nothing mounted, files land on the SD card."}`

3. **N.WEBPAGE.tip**, fork, stale.
   Map: `... The file is about 12k lines: grep for an anchor, never read it whole.`
   Code: `wc -l src/web/WebControlPage.cpp` = 20963 `@cinemate-port` (11618 `@upstream-1.6.0`).
   Corrected: `tip:"A WebUI change needs a Core rebuild and a Core restart. The file is about 21k lines: grep for an anchor, never read it whole.",up:{tip:"A WebUI change needs a Core rebuild and a Core restart. The file is about 12k lines: grep for an anchor, never read it whole."}`

4. **N.RECS.path**, both, wrong.
   Map: `~/ApertarCore/src/cdng/, src/mlv/, src/prores/, src/video/`
   Code: `src/camera/CameraController.cpp:3744@upstream-1.6.0` / `:5291@cinemate-port`: `encoder.writeDngFile(job.path, job.frame, job.metadata);` (no hit in src/cdng, src/mlv, src/prores, src/video)
   Corrected: `path:COREP+"src/camera/CameraController.cpp (DngRecordingQueue) + encoders in src/cdng/, src/lossydng/, src/mlv/, src/prores/, src/video/",`

5. **N.RECS.what**, both, imprecise.
   Map: `One recorder per format: cDNG and lossy DNG (frame by frame, worker threads), MLV, H.264, ProRes. Audio is a WAV beside the clip.`
   Code: `src/camera/CameraController.cpp:3690@upstream-1.6.0` / `:5224@cinemate-port`: `mlvWorkerLoop();` inside `DngRecordingQueue::workerLoop`
   Corrected: `One encoder per format, each in its own folder: cDNG, lossy DNG, MLV, H.264, ProRes. DngRecordingQueue in CameraController.cpp runs the worker threads for cDNG, lossy DNG and MLV. Audio is a WAV beside the clip.`

6. **N.HWIN.up.tip**, official, imprecise.
   Map: `Action names are normalised in each *Input.cpp (normalizeSingleAction), so a new action goes into each one. The hardware file is read once at start: restart Core after a change.`
   Code: `src/hardware/GpioInput.cpp:201@upstream-1.6.0`: `return action;` (unknown names pass through); `src/ApertarCoreApp.cpp:8660@upstream-1.6.0`: `void ApertarCoreApp::handleSingleHardwareInputAction(const std::string &action)`
   Corrected: `GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp each hold their own copy of the alias table (normalizeSingleAction); a name they do not list passes through unchanged. What an action does is a branch in handleSingleHardwareInputAction (ApertarCoreApp.cpp), so a new action goes there. The hardware file is read once at start: restart Core after a change.`

7. **N.HWIN.tip**, fork, imprecise.
   Map: `... (fork only; upstream has a copy in each *Input.cpp). ...`
   Code: `normalizeSingleAction` only in `src/hardware/GpioInput.cpp:108`, `NeoRotary4Input.cpp:121`, `Pcf8574Input.cpp:140@upstream-1.6.0`; not in `GroveAnalogInput.cpp`, `StandbyPowerButtonInput.cpp`
   Corrected: `On this fork every action name lives in ActionCatalog.hpp (fork only; upstream has a copy in GpioInput.cpp, NeoRotary4Input.cpp and Pcf8574Input.cpp). A saved apertar-hardware.conf applies without a Core restart (fork only): a controls worker restarts just the input group that changed.`

8. **N.HWIN.what**, fork, imprecise.
   Map: `Poll threads read I2C or GPIO and turn a press or a turn into an action name such as iso_up or record_toggle.`
   Code: `src/hardware/GpioInput.cpp:518@cinemate-port`: `request.config.flags |= GPIO_V2_LINE_FLAG_EDGE_RISING | GPIO_V2_LINE_FLAG_EDGE_FALLING;` and `:823` `const int count = ::poll(&ready, 1, sleepMs(toMs(std::chrono::steady_clock::now())));` (waits for edges)
   Corrected: `Input threads read I2C or GPIO and turn a press or a turn into an action name such as iso_up or record_toggle.`

9. **N.BTN.what**, fork, imprecise.
   Map: `PCF8574 buttons, NeoRotary4 encoders and GPIO buttons. Core polls them itself; the UI is not involved.`
   Code: as item 8.
   Corrected: `PCF8574 buttons, NeoRotary4 encoders and GPIO buttons. Core reads them itself; the UI is not involved.`

10. **N.BRIDGE.tip**, both, imprecise.
    Map: `sendCoreCommand blocks the GUI thread until Core replies: up to 3 s, 60 s for record_stop.`
    Code: `src/ApertarControlBridge.cpp:1031@upstream-1.6.0` / `:1167@cinemate-port`: `: (reconfigureCommand ? 10000 : 3000);`
    Corrected: `sendCoreCommand blocks the GUI thread until Core replies: up to 3 s, 10 s for a command that reconfigures the camera (set_resolution, set_record_format, …), 60 s for record_stop.`

11. **N.BRIDGE.code**, fork, imprecise.
    Map: `bool ApertarControlBridge::applyIso(…)       // "Auto" → set_iso_auto, else set_iso`
    Code: `src/ApertarControlBridge.cpp:303@cinemate-port`: `if (displayValue == QStringLiteral("Lock")) {` then `:304` `set_iso_auto` with `enabled` = `false`
    Corrected: `code:"bool ApertarControlBridge::applyIso(…)       // \"Auto\" → set_iso_auto, \"Lock\" → set_iso_auto enabled=false, else set_iso\nbool ApertarControlBridge::sendCoreCommand(…)  // one socket per command",` plus `up:{code:"bool ApertarControlBridge::applyIso(…)       // \"Auto\" → set_iso_auto, else set_iso\nbool ApertarControlBridge::sendCoreCommand(…)  // one socket per command"}` (merge into the box's existing object; BRIDGE has no `up` today)

12. **N.HUB.what**, fork, imprecise.
    Map: `Every command from every entry point ends up here. One long function, one if-branch per command, guarded by commandMutex_.`
    Code: `src/ApertarCoreApp.cpp:12562@cinemate-port`: `if (const auto reply = handleReadOnlyHardwareCommand(command))` before `:12571` `std::lock_guard<std::mutex> commandLock(commandMutex_);`
    Corrected: `Every command from every entry point ends up here. One long function with one if-branch per command. Every command that changes something runs under commandMutex_.`

13. **N.HUB.tip**, both, imprecise.
    Map: `... Use the chapter map in llm/core-map.md; never read the file whole.`
    Code: no `llm/` in Apertar-Core (either tree); file is `apertar-kb/llm/core-map.md`
    Corrected: `List all commands: grep -n 'command.name == "' ApertarCoreApp.cpp. Use the chapter map in the knowledge base (~/apertar-kb/llm/core-map.md); never read the file whole.`

14. **N.CAM.what**, both, imprecise.
    Map: `Holds the capture settings and talks to libcamera. ISO, shutter, WB and fps are control-only; resolution, format and bit depth need a full reconfigure.`
    Code: `src/camera/CameraController.cpp:7967@upstream-1.6.0` / `:11387@cinemate-port`: `const bool requiresReconfigure = currentUsesProcessedStream || nextUsesProcessedStream ||`; fork `:10777`: `const bool applied = applySettingsLocked(next, rung != nullptr, commit);`
    Corrected: `Holds the capture settings and talks to libcamera. ISO, shutter and WB are control-only, and fps normally is too. Resolution, bit depth and a switch between RAW and H.264/ProRes need a full reconfigure.`

15. **N.CAM.tip**, both, imprecise.
    Map: `Settings are also saved to ~/.config/apertar-core/camera_settings.conf, 25 ms after the last change.`
    Code: `src/camera/CameraController.cpp:853@upstream-1.6.0`: `cv_.wait_for(lock, std::chrono::milliseconds(25), [this]() {` (deadline from the first unsaved change)
    Corrected: `Settings are also saved to ~/.config/apertar-core/camera_settings.conf, about 25 ms after a change.`

16. **N.SENSOR.tip**, both, imprecise.
    Map: `New controls land one request after they are set, about one frame.`
    Code: `src/camera/CameraController.cpp:6506@upstream-1.6.0` / `:8987@cinemate-port`: `request->controls().merge(pendingControls_);` inside `requeueRequest`; `:1023` `constexpr unsigned int kConfiguredBufferCount = 4;`
    Corrected: `New controls ride on the next request Core hands back to libcamera, so they leave Core within one frame. When the picture changes is up to libcamera and the sensor: other requests are already queued and the sensor applies gain and exposure with its own delay.`

17. **N.PUB.tip**, both, imprecise.
    Map: `Only the newest frame is kept. A slow reader skips frames instead of queueing them.`
    Code: `src/ipc/ControlServer.cpp:25@upstream-1.6.0` / `:28@cinemate-port`: `const ssize_t written = ::send(fd, data, remaining, MSG_NOSIGNAL | MSG_DONTWAIT);`, then `removeClient(client);` (`:191` / `:194`)
    Corrected: `Only the newest frame is kept, so the publisher and a slow browser skip frames instead of queueing them. A socket client that stops reading is disconnected: Core never waits for a reader.`

18. **Legend, index.html:221**, fork, imprecise.
    Map: `N commits that are Tiramisioux dev-fork only (branch <code>cinemate-port</code>)`
    Code: `index.html:420` `FORKDATA.SENSOR`: `"branch": "apertar"`
    Corrected: `<span class="swatch forklegend"><span class="forktag" style="margin:0">fork · N</span>N commits that are Tiramisioux dev-fork only (branch <code>cinemate-port</code>; the imx585 driver: branch <code>apertar</code>)</span>` (or point FORKDATA.SENSOR at the driver's cinemate-port and keep the legend)
