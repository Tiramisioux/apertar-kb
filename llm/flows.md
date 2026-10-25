# Flows: hop-by-hop traces

What happens, process by process, when the operator does something. Research 2026-10-25 (desk, from code). Entry point: [README.md](README.md).

| Repo | Local HEAD | Cite as | Note |
| --- | --- | --- | --- |
| `~/Documents/Apertar/Apertar-Core` | `ed400ba` | `upstream-1.6.0` | `git diff upstream-1.6.0 HEAD` = `.gitignore` + one mode bit. `src/` identical |
| `~/Documents/Apertar/Apertar-UI` | `29ed99b` | `upstream-1.6.0` | `git diff upstream-1.6.0 HEAD -- src qml CMakeLists.txt` = empty (only a mode bit on `run_pi_direct.sh`) |
| `~/Documents/Apertar/imx585-v4l2-driver` | `e5b74d3` (branch `apertar`) | `e5b74d3` | 21-entry `supported_modes[]` with aspect crops. **Not** the `main` layout that `apertar-kb/architecture/drivers.md` describes |

Conventions:
- `Core/` = `Apertar-Core/`, `UI/` = `Apertar-UI/`, `drv/` = `imx585-v4l2-driver/`.
- `App` = `Core/src/ApertarCoreApp.cpp`. `CC` = `Core/src/camera/CameraController.cpp`. `CB` = `UI/src/ApertarControlBridge.cpp`. `WCP` = `Core/src/web/WebControlPage.cpp`.
- Every line number came from `grep -n` at the HEADs above.
- **Anchor** = a string to `grep -rnF` when lines move. Anchors were checked with `grep -rF -c`; count is 1 unless the row says otherwise.
- Status words follow the KB rule: **confirmed** (seen in code), **probable**, **unconfirmed** (+ the command that settles it).

## A. Traces

### A1. ISO tap on the touch screen → AnalogueGain → disk → `settings` event → UI and WebUI

| # | Process | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | UI (QML) | `UI/qml/TopDropdownStat.qml:113` | delegate `onClicked` | Option tapped → `optionSelected(modelData)` (signal declared `:23`) | `onClicked: root.optionSelected(modelData)` |
| 2 | UI (QML) | `UI/qml/CameraPage.qml:2918`, `:2940-2946` | ISO `TopDropdownStat.onOptionSelected` | Calls the bridge. `root.iso = v` only when there is no bridge. Options from `isoOptions` (`:511-513`) | `root.controlBridge.applyIso(v)` |
| 3 | UI (C++) | `CB:291-316` | `ApertarControlBridge::applyIso` | "Auto" → `set_iso_auto`; else `set_iso {value}` | `bool ApertarControlBridge::applyIso` |
| 4 | UI (C++) | `CB:1013-1106` | `sendCoreCommand` | New `QLocalSocket` per command, 350 ms connect, writes `{"cmd":"set_iso","id":N,"value":800}\n`, **blocks the GUI thread** ≤3 s for the matching `id`. Every line read goes through `applyCoreMessage` | `bool ApertarControlBridge::sendCoreCommand` |
| 5 | Core | `Core/src/ipc/ControlServer.cpp:236`, `:252` | `ControlServer::clientLoop` | One thread per client. Splits lines, calls the handler | `const std::string reply = handler_(line);` |
| 6 | Core | `App:7055-7083` | `ApertarCoreApp::handleRequest` | `parseControlCommand` (`Core/src/ipc/ControlProtocol.cpp:164`, flat parser: every value is a string). Sets `collectingCommandEvents_ = true` (`:7063`) | `std::string ApertarCoreApp::handleRequest` |
| 7 | Core | `App:9091-9093` | `handleCommand` | Takes `commandMutex_`. Idle-timer and media gates first | `std::string ApertarCoreApp::handleCommand` |
| 8 | Core | `App:9242-9249` | `handleCommand` branch | `camera_.setIso(value)` → reply `okReply(id, settingsBody(...))` | `if (command.name == "set_iso") {` |
| 9 | Core | `CC:7774-7786` | `CameraController::setIso` | Range 50–51200, sets `iso`, `isoAuto=false`, `applySettingsLocked(next, false)` (no reconfigure) | `bool CameraController::setIso(uint32_t iso)` |
| 10 | Core | `CC:8659-8723` | `applySettingsLocked` | Standby/still/capability checks. `requiresReconfigure` false → `session_->applyControls` (`:8689-8691`) | `bool CameraController::applySettingsLocked` |
| 11 | Core | `CC:5495-5523` | `CameraSession::applyControls` | `sanitizeSettingsForSensor`, then `pendingControls_ = controlsForSettings(...)` under `controlsMutex_` | `pendingControls_ = controlsForSettings(sanitized,` |
| 12 | Core | `CC:2005`, `:2050-2061` | `controlsForSettings` | `AnalogueGainMode = Manual`; `AnalogueGain = max(1, ISO/100)` | `std::max(1.0f, static_cast<float>(settings.iso) / 100.0f)` |
| 13 | Core (libcamera thread) | `CC:6497-6508` | `CameraSession::requeueRequest` | Next requeued request merges `pendingControls_` and clears them. Gain lands one request later | `request->controls().merge(pendingControls_);` |
| 14 | Core | `CC:8718`, `:8725-8732` | `persistSettingsLocked` | Copies into the per-format profile, `captureSettingsPersister().schedule(...)` | `captureSettingsPersister().schedule(settings_` |
| 15 | Core (persister thread) | `CC:793-889` (worker `:855-866`), `CC:780-791` | `CaptureSettingsPersister` → `persistCaptureSettingsNow` | 25 ms debounce, then atomic write of `~/.config/apertar-core/camera_settings.conf` (path `CC:342-353`) | `void persistCaptureSettingsNow` |
| 16 | Core | `CC:742-748` | `writeCaptureSettings` | Writes `iso=800` (and `profile.<format>.iso=`) | `output << prefix << "iso=" << s.iso` |
| 17 | Core | `CC:8720`, `:8777-8784` | `emitSettingsEventLocked` | Builds `settingsEvent` (`CC:136-191`), calls the event callback = `publishEvent` (wired `App:6784`) | `eventCallback_(settingsEvent(settings_));` |
| 18 | Core | `App:10823-10840` | `publishEvent` | `settings` is on the always-broadcast list → `controlServer_.broadcast` to **every** socket client now | `if (eventJson.find("\"event\":\"settings\"") != std::string::npos \|\|` |
| 19 | Core | `Core/src/ipc/ControlServer.cpp:172-179` | `ControlServer::broadcast` | `MSG_DONTWAIT` send; a full client is dropped | `void ControlServer::broadcast(const std::string &line)` |
| 20 | UI (C++) | `CB:122`, `:1570-1589` | `processEventSocketMessages` | Persistent event socket receives the `settings` line | `connect(&m_eventSocket, &QLocalSocket::readyRead` |
| 21 | UI (C++) | `CB:1257-1258` | `applyCoreMessage` | `settings` event **or** any reply with `ok` → `applyCoreState` | `if (event == QStringLiteral("settings") \|\| message.contains(QStringLiteral("ok")))` |
| 22 | UI (C++) | `CB:1371-1375`, setter `CB:2239-2246` | `applyCoreState` → `setIso` | Emits `isoChanged` only on change | `setIso(formatIsoValue(state.value(QStringLiteral("iso"))` |
| 23 | UI (C++) | `CB:310-315`, `CB:973` | back in `applyIso` | After the reply: `setIso`, then `saveCurrentCameraSettings()` writes the UI's **own** `[camera]` cache in `UI.conf` (not used by Core) | `void ApertarControlBridge::saveCurrentCameraSettings` |
| 24 | UI (QML) | `UI/qml/CameraPage.qml:1824`, `:1843-1846` | `Connections.onIsoChanged` | Copies into CameraPage's local `property string iso` (`:341`), which the dropdown shows (`:2931`) | `function onIsoChanged()` |
| 25 | WebUI (browser) | `WCP:11609` | page script | Polls every 1 s | `window.setInterval(() => fetchState(true), 1000);` |
| 26 | Core | `App:7154`, `App:7711`, iso field `App:7861` | `handleWebRequest` → `buildWebStateJson` | Fresh JSON from `camera_.settings()` + UI.conf + device state | `std::string ApertarCoreApp::buildWebStateJson() const` |
| 27 | WebUI (browser) | `WCP:9327`, `:9494`, `:9883` | `renderSnapshot` | ISO label and option buttons | `const isoLabel = snapshot.iso_auto` |

Notes:
- A WebUI ISO change enters at `WCP:9888` (`sendCommand({cmd:"set_iso"…})`) → `POST /api/command` (`App:7637`) → `handleWebCommand` (`App:7085`) → hop 7. It skips hop 6, so its events are broadcast, not collected.
- `settingsBody` (`App:167`), `settingsEvent` (`CC:136`) and `buildWebStateJson` (`App:7835+`) are three hand-written copies of the same fields. **confirmed**.

### A2. Record start/stop: three entry points, one convergence, then the cDNG write path

**Entry paths**

| Path | # | file:line | Function | Anchor |
| --- | --- | --- | --- | --- |
| Touch REC | T1 | `UI/qml/RecordButton.qml:182-184` | `MouseArea.onClicked` → `root.clicked()` (not after a long-press) | `onClicked: {` (file-local) |
| | T2 | `UI/qml/CameraPage.qml:3772`, `:3792-3826` | `RecordButton.onClicked`: photo/timelapse branches first; no media → `showNoMediaWarning` (`:1664`); else `requestRecordingState(!recording)` | `root.requestRecordingState(true)` |
| | T3 | `UI/qml/CameraPage.qml:1583-1588` | `requestRecordingState`: suspends the UI audio meter, calls the bridge | `function requestRecordingState(recordingState)` |
| | T4 | `CB:777-815` | `setRecording`: reads audio/gyro keys from `UI.conf` (`soundRecorderEnabled`, `recordAudioEnabled`, …), sends `record_start {…}` / `record_stop` (60 s timeout `CB:1029`) | `recording ? QStringLiteral("record_start") : QStringLiteral("record_stop")` |
| | T5 | socket → `ControlServer::clientLoop` → `handleRequest` → `handleCommand` | as A1 hops 5-7 | — |
| GPIO / PCF8574 / NeoRotary4 button | H1 | `Core/src/hardware/Pcf8574Input.cpp:470-526` | `Pcf8574Input::run`: poll `/dev/i2c-N` every `poll_ms`, debounce, on press `emitAction(config_.actions[pin])` (`:517`) | `emitAction(config_.actions[pin]);` |
| | H1b | `Core/src/hardware/GpioInput.cpp:621`, `:707` | `GpioInput::run` → `emitAction(button.action)` | `void GpioInput::run()` |
| | H2 | `Core/src/hardware/Pcf8574Input.cpp:140-155` (same in `GpioInput.cpp:108`, `NeoRotary4Input.cpp:121`) | `normalizeSingleAction` at config load: `record`/`capture`/`take` → `capture`; `rec`/`record_toggle` → `record_toggle` | `if (action == "record" \|\| action == "capture" \|\|` (3 hits, one per input class) |
| | H3 | `App:6789-6791` | constructor lambdas → `handleHardwareInputAction` | `, pcf8574Input_([this](const std::string &action) { handleHardwareInputAction(action); })` |
| | H4 | `App:8630-8658` | `handleHardwareInputAction`: splits ≤6 actions; in Standby a press only wakes | `void ApertarCoreApp::handleHardwareInputAction` |
| | H5 | `App:8660`, `:8840-8869` | `handleSingleHardwareInputAction`: `capture` = timelapse/still/record by mode; `record_toggle` = start/stop by `camera_.isRecording()` | `if (action == "record_toggle") {` |
| | H6 | `App:8458-8466` | `dispatchHardwareInputCommand`: `id=-1`, calls `handleCommand` on the **poll thread**; failures only to stderr | `std::string ApertarCoreApp::dispatchHardwareInputCommand` |
| WebUI | W1 | `WCP:2525`, `:11351` | `#recordButton` click → `toggleRecord` | `document.getElementById("recordButton").addEventListener("click", toggleRecord);` |
| | W2 | `WCP:10690-10765` | `toggleRecord`: no media → toast; builds the same `record_start` payload as T4 from `uiState` | `async function toggleRecord()` |
| | W3 | `WCP:9109`; `App:7637`, `:7085` | `sendCommand` → `POST /api/command` → `handleWebCommand` | `if (request.method == "POST" && request.path == "/api/command")` |

**Convergence: `handleCommand` (`App:9091`).** All three paths call it. It serialises on `commandMutex_`. Media-pending gate `App:9095-9097`; standby gate `App:9208-9211`.

**Start and write path**

| # | Thread | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| R1 | command | `App:10623-10715` | `record_start` branch | Reads UI.conf + ALSA devices. With audio: broadcast `prepare_recording`, **sleep 220 ms under `commandMutex_`**. Then `camera_.startRecording` | `if (!camera_.startRecording(audioOptions, gyroOptions))` |
| R2 | command | `CC:8219-8263` | `CameraController::startRecording` | State must be Ready; then `session_->startRecording(mediaRoot_, …)`; `emitRecordingEventLocked` (`:8262`) | `bool CameraController::startRecording` |
| R3 | command | `CC:5526-5550` | `CameraSession::startRecording` | `reserveClipFolder` + `create_directories`. **No mount or free-space check** | `clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);` |
| R4 | command | `CC:3646-3676` | `DngRecordingQueue::allocateClipFolder` | `<media>/cDNG_yy-mm-dd_C0001` (first free of 9999). Media root = `--media /media/RAW` (`Core/scripts/start-apertar-core.sh:5`, `:21`) | `const char *formatPrefix = "cDNG_";` |
| R5 | command | `CC:3279-3350`, call `CC:5639` | `DngRecordingQueue::startAtFolder` | Spawns min(8, cores+1) workers (`APERTAR_CDNG_WORKERS`); then frame gate opened (`recordingFramesEnabled_ = true`, `CC:5646`) | `workers_.emplace_back(&DngRecordingQueue::workerLoop, this);` |
| R6 | libcamera | `CC:6579`, call `CC:6664` | `CameraSession::requestComplete` | Per frame: still → preview → `recordProcessedPreviewFrame` / `recordRawFrame` → requeue | `recordRawFrame(request, whiteBalance);` |
| R7 | libcamera | `CC:6853-6956` | `recordRawFrame` | Frame index from sensor timestamp; copy RAW plane into a recycled buffer; `recorder_.enqueue(...)` (`:6954`) | `if (recorder_.enqueue(std::move(rawCopy), view, std::move(metadata)))` |
| R8 | libcamera | `CC:3572-3608` | `DngRecordingQueue::enqueue` | Queue full → drop + `ApertarCore drop[queue-full]` log. Path = `<folder>/<clip>_#########.dng` (`CC:3678-3685`) | `out << std::setw(9) << std::setfill('0') << frameIndex << ".dng";` |
| R9 | DNG worker | `CC:3687-3765` | `workerLoop` → `dngWorkerLoop` | Pops a job, `encoder.writeDngFile`; exception → `failRecording` + `ApertarCore DNG write failed for …` | `encoder.writeDngFile(job.path, job.frame, job.metadata);` |
| R10 | DNG worker | `Core/src/cdng/CdngEncoder.cpp:1209`, `:1271` | `CdngEncoder::writeDngFile` | `open(O_WRONLY\|O_CREAT\|O_TRUNC)`; uncompressed or LJ92 tiles | `: ::open(path.c_str(), O_WRONLY \| O_CREAT \| O_TRUNC \| O_CLOEXEC, 0644);` |
| R11 | command | `App:10854-10868` | `publishEvent` → `handleTriggerEvent` | `recording active:true` → tally LED on + trigger pulse. `recording` is **not** always-broadcast: during a socket command it rides on that reply | `triggerOutput_.pulse(TriggerOutput::Event::RecordingStart);` |

**Stop and flush**

| # | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- |
| S1 | `App:10783-10794` | `record_stop` branch | Sound-only → `stopSoundRecording`. Else `camera_.stopRecording()`, `syncRecordingTracking(false)` (`App:8310`) | `if (!camera_.stopRecording())` |
| S2 | `CC:8502-8517` | `CameraController::stopRecording` | State → Ready; `session_->stopRecording()`; `emitRecordingEventLocked` | `bool CameraController::stopRecording()` |
| S3 | `CC:5658-5680` | `CameraSession::stopRecording` | Close frame gate first, then gyro → H.264 → `recorder_.stop()` → ProRes → audio (WAV built here) | `// Close the frame gate before finalizing audio` |
| S4 | `CC:3390-3425` | `DngRecordingQueue::stop` | `stopping_=true`, notify, **join workers**. Workers exit only when the queue is empty (`CC:3720-3727`), so queued frames are written. Logs `ApertarCore recording stats: enqueued= written= dropped_queue_full=…` | `void stop()` (file-local, `CC:3390`) |
| S5 | `CB:1029` | UI side | Waits up to 60 s for the reply; the GUI is frozen meanwhile | `QStringLiteral("record_stop") ? 60000` |

Observation: `discardedOnStopFrames_` is only ever reset (`CC:3304`), never incremented (grep). The `discarded_on_stop=` stat is always 0. **confirmed in code**.

### A3. WebUI zebra toggle → Core → `UI.conf` → UI file watch → QML → shader

| # | Process | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | Browser | `WCP:10087` | zebra option handler | `sendCommand({cmd:"set_zebra_enabled", enabled:"true"})` | `await sendCommand({ cmd: "set_zebra_enabled"` |
| 2 | Browser | `WCP:8875-8876` | `applyCommandSnapshotPatch` | Optimistic `uiState.zebra_enabled` | `case "set_zebra_enabled":` |
| 3 | Core | `App:7637` → `App:7085` → `App:9091` | `/api/command` → `handleWebCommand` → `handleCommand` | — | `std::string ApertarCoreApp::handleWebCommand` |
| 4 | Core | `App:9478-9491`, `:9495` | `handleUiToggle` lambda | Needs `enabled`; maps to key `zebraEnabled`; replies `settingsBody` | `if (const auto reply = handleUiToggle("set_zebra_enabled", "zebraEnabled"))` |
| 5 | Core | `App:1850-1935`, path `App:341-348` | `updateSharedUiGeneralSettings` | Qt-compatible lock (`QtIniLock`, `Core/src/util/SettingsFile.hpp:59-118`); line-edit `[General]`; tmp+fsync+rename | `return settingsFile::atomicWrite(path, output.str());` |
| — | Core | — | — | **No event is emitted.** The UI learns only from the file | — |
| 6 | UI | `UI/src/SettingsBridge.cpp:411-431` | constructor | `QFileSystemWatcher::fileChanged` → `pollExternalSettings` + re-add watch paths (rename breaks inotify); fallback 10 s timer | `m_settingsFileSize = -1; // Reconcile` |
| 7 | UI | `UI/src/SettingsBridge.cpp:502-520` | `pollExternalSettings` | mtime/size changed → `m_externalSettingsSyncing=true`, `m_settings.sync()`, re-read each key | `setZebraEnabled(m_settings.value(QStringLiteral("zebraEnabled"), m_zebraEnabled).toBool());` |
| 8 | UI | `UI/src/SettingsBridge.cpp:597-607` | `setZebraEnabled` | Skips write-back while syncing; emits `zebraEnabledChanged` | `if (!m_externalSettingsSyncing) m_settings.setValue("zebraEnabled", value);` |
| 9 | UI (QML) | `UI/qml/Main.qml:501`; `UI/qml/CameraPage.qml:1981` | binding | `settingsState: settingsBridge`; `CameraPreviewItem.zebraEnabled` bound to it | `zebraEnabled: root.settingsState ? root.settingsState.zebraEnabled : false` |
| 10 | UI (C++) | `UI/src/CameraPreviewItem.cpp:52-60` | `setZebraEnabled` | Emits, requests a window update | `void CameraPreviewItem::setZebraEnabled` |
| 11 | UI (render) | `UI/src/PreviewWindowRenderer.cpp:1892`, `:1907`, `:2100` | `currentPreviewState` → uniform | `uZebraEnabled=1` | `state.zebraEnabled = m_item->zebraEnabled();` |
| 12 | UI (GLSL) | `UI/src/PreviewWindowRenderer.cpp:896` | fragment shader | Stripes where luma ≥ threshold | `if (uZebraEnabled == 1 && exposureLuma >= uZebraThreshold)` |
| 13 | Browser | `App:7970` (via `readSharedUiSettings`, `App:1641`, key `:1679-1680`) | `buildWebStateJson` | Next 1 s poll confirms `zebra_enabled` from the file | `<< ",\"zebra_enabled\":" << (uiSettings.zebraEnabled` |

The touch UI's own zebra toggle (`UI/qml/SettingsPage.qml:2706`, `CameraPage.qml:630`) writes `UI.conf` through `SettingsBridge` only; it sends **no** socket command. Same for every aid.

### A4. Preview frame: libcamera buffer → UI screen; and MJPEG → browser

**Touch screen (dma-buf, zero copy)**

| # | Process / thread | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | Core / libcamera | `CC:6579`, `CC:7228` | `requestComplete` → `CameraSession::publishPreviewFrame` | First time per slot: `dup()` plane fds into a *registration* (`CC:7256`, `:7273`, `:7320`). Every frame: small descriptor (`CC:7372`) | `void publishPreviewFrame(libcamera::Request *request)` |
| 2 | Core / libcamera | `App:6786`, `App:6943-6990` | `enqueuePreviewFrame` | Registrations cached + queued. Frames: only the newest pending kept. Also feeds MJPEG (row M1) | `void ApertarCoreApp::enqueuePreviewFrame` |
| 3 | Core / preview thread | `App:6825`, `App:10946-10986` | `runPreviewPublisher` | Drains registrations first, then the latest frame | `void ApertarCoreApp::runPreviewPublisher` |
| 4 | Core / preview thread | `App:10891-10944` | `ApertarCoreApp::publishPreviewFrame` | JSON `preview_buffer` (+fds) or `preview_frame` (slot only) | `controlServer_.broadcastWithFds(out.str(), attachedFds);` |
| 5 | Core | `Core/src/ipc/ControlServer.cpp:37-75`, `:186-192` | `sendLineWithFds` | `SCM_RIGHTS` cmsg, `sendmsg(MSG_DONTWAIT)` to **every** client | `bool sendLineWithFds(int socketFd` |
| 6 | UI (QML) | `UI/qml/Main.qml:207` | `Component.onCompleted` | `apertarPreviewBridge.connectToCore()` | `apertarPreviewBridge.connectToCore()` (4 hits in `qml/`; the one in `Main.qml`) |
| 7 | UI | `UI/src/ApertarPreviewSocketClient.cpp:32`, `:142-165` | `connectToCore`, `requestPreviewSubscription` | Raw AF_UNIX socket; sends `preview_subscribe`. Core replays cached registrations (`App:10796-10799`, `:6994`) | `{\"cmd\":\"preview_subscribe\",\"id\":0}` |
| 8 | UI | `UI/src/ApertarPreviewSocketClient.cpp:167-215` | `readAvailableMessages` | `recvmsg`, collects fds from `SCM_RIGHTS` | `const ssize_t received = ::recvmsg(m_socketFd, &msg, MSG_DONTWAIT);` |
| 9 | UI | `:324`, `:353-451`, `:453-512` | `handleMessage` → `handlePreviewBuffer` / `handlePreviewFrame` | Hand-rolled `"key":` parsing (`:585-625`). Frame looks up its slot → `emit previewFrameReady()` (`:509`) | `void ApertarPreviewSocketClient::handlePreviewFrame` |
| 10 | UI | `UI/src/PreviewWindowRenderer.cpp:428-444`, `:342` | `connectBridgeSignals` → `scheduleWindowUpdate` | DirectConnection; asks Qt for a frame | `connect(apertarBridge, &ApertarPreviewSocketClient::previewFrameReady,` |
| 11 | UI / render | `:405`, `:2388`, `:2407` | `render` (on `beforeRenderPassRecording`) → `ensureImported` | Draws **under** the QML scene | `void PreviewWindowRenderer::render()` |
| 12 | UI / render | `:1604`, `:1703`, `:1769-1771`, `:1785-1790` | `ensureImported` | `eglCreateImageKHR(EGL_LINUX_DMA_BUF_EXT)` → `GL_TEXTURE_EXTERNAL_OES`, cached per dma-buf. Failure logs `eglCreateImageKHR failed` | `EGLImageKHR image = createImage(dpy, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, nullptr, attr.data());` |
| 13 | UI / render | `:2460-2462`, `:2194`, `:1969` | `renderDirectToWindow` / `renderProcessedPreview` | Plain draw, or the aid shaders (zebra, peaking, false colour, LUT) | `void PreviewWindowRenderer::renderDirectToWindow` |

**Browser (MJPEG)**

| # | Thread | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| M0 | browser | `WCP:8563` | `installPreviewStream` | `<img src="/preview.mjpeg?stream=<nonce>">` | `preview.src = "/preview.mjpeg?stream=" + state.previewStreamNonce;` |
| M1 | web client | `App:7109-7121`, `App:8262-8300` | `/preview.mjpeg` → `streamMjpeg` | `mjpegClientCount_++`; sends `--frame` parts as new JPEGs appear | `void ApertarCoreApp::streamMjpeg(int clientFd)` |
| M2 | libcamera | `App:6951-6952`, `App:8048`, `App:8095-8192` | `enqueuePreviewFrame` → `captureWebPreviewFrame` | Only while viewers > 0. Rate-limited to `kWebPreviewMaxFps`, nearest-downsamples the mmap'd slot to ≤640x360 I420 (`App:60-63`) | `void ApertarCoreApp::captureWebPreviewFrame` |
| M3 | MJPEG thread | `App:6834`, `App:8194-8236`, `App:4123` | `runMjpegEncoder` → `encodeYuv420ToJpeg` | TurboJPEG q75, swaps into `latestMjpegFrame_`, `notify_all` | `void ApertarCoreApp::runMjpegEncoder()` |

### A5. NeoRotary4 encoder turn → I2C → action name → setting change

| # | Thread | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | Core start | `App:6887` | `start()` | `neoRotary4Input_.start()` reads the config **once** | `neoRotary4Input_.start();` |
| 2 | Core start | `Core/src/hardware/NeoRotary4Input.cpp:400-435`, `:222-256` | config loader | `[neorotary4]` keys: `bus` (default 1, `.hpp:39`), `address` (0x49, `.hpp:40`). `encoder0_cw=` / `encoder0_ccw=` / `encoder0_press=` (prefix `encoder`/`enc`/`rotary`, index 0-3) | `config.encoders[*encoder].clockwise = normalized;` |
| 3 | Core start | `NeoRotary4Input.cpp:121-215`, `:217-219` | `normalizeSingleAction` / `normalizeAction` | `iso_next`/`iso_plus` → `iso_up`, etc. Unknown names pass through unchanged | `std::string normalizeAction(std::string action)` (3 hits, one per input class) |
| 4 | poll thread | `NeoRotary4Input.cpp:624-667` | `NeoRotary4Input::run` | Every `poll_ms`: for each encoder read delta; sign picks cw/ccw action; repeat ≤`max_events_per_poll` | `void NeoRotary4Input::run()` |
| 5 | poll thread | `NeoRotary4Input.cpp:559-584` | `readRegister` / `readEncoderDelta` | Write `{0x11, 0x40\|i}`, `read()` 4 bytes big-endian (seesaw); `invert_direction` flips sign | `static_cast<uint8_t>(kEncoderDelta \| encoder)` |
| 6 | poll thread | `NeoRotary4Input.cpp:664` | `rotationCallback_(action)` | Wired at `App:6790-6791` to `handleHardwareInputAction(action, false)` | `rotationCallback_(action);` |
| 7 | poll thread | `App:8630-8658` | `handleHardwareInputAction` | `buttonPress=false`: ignored in Standby; `standby` actions skipped | `void ApertarCoreApp::handleHardwareInputAction` |
| 8 | poll thread | `App:8789-8800`; helpers `App:1030-1041`, `App:1279-1282` | `handleSingleHardwareInputAction` | `iso_up/iso_down` step through `Auto, 100…51200` (nearest preset) → `dispatch("set_iso", …)` | `if (const auto mode = pcfSettingStepMode(action, "iso")) {` |
| 9 | poll thread | `App:8458-8466` | `dispatchHardwareInputCommand` | `handleCommand` → A1 hops 8-19. Reply discarded (logged on failure) | `Hardware input action failed: ` |
| 10 | UI | A1 hops 20-24 | — | Touch screen ISO updates from the broadcast `settings` event | — |

Config example (Core restart needed): `[neorotary4]` / `enabled=true` / `bus=<rig bus>` / `encoder0_cw=iso_up` / `encoder0_ccw=iso_down`. Startup log: `NeoRotary4 input enabled: /dev/i2c-N address=0x49 …`. Errors: `NeoRotary4Input input: …` (only in the journal). The UI's template ships `enabled=false`, `bus=1` (`UI/src/DisplayConfigBridge.cpp:131-143`).

### A6. Boot: who reads which config, and resolution → driver mode

**Config readers at startup**

| Order | Reader | File | Where | When re-read |
| --- | --- | --- | --- | --- |
| 0 | Firmware / kernel | `/boot/firmware/config.txt` `dtoverlay=imx585,…` → loads `imx585.ko` (DKMS) | `drv/imx585-overlay.dts`; `drv/dkms.postinst` | reboot |
| 1 | UI `DisplayConfigBridge` (constructed `UI/src/main.cpp:278-289`) | `apertar-hardware.conf` `[display]`. **Writes the full template to `/home/pi/apertar-hardware.conf` if missing** (`UI/src/DisplayConfigBridge.cpp:41`, `:587`) | `DisplayConfigBridge::loadConfiguration`, `:575-654` | UI restart |
| 1 | UI `SettingsBridge` | `~/.config/CinePi/UI.conf` | `UI/src/SettingsBridge.cpp:287`, `:324` | inotify + 10 s poll |
| 1 | UI `Ina219Bridge` | `[ina219]` (bus 4) | `UI/src/Ina219Bridge.cpp:45-48` | 5 s after start |
| 1 | UI `GyroConfigBridge` | `[imu]` | `UI/src/GyroConfigBridge.cpp:193-207` | on demand |
| 1 | UI / network helper `WifiBridge` | `[network]` (env or `/home/pi` only) | `UI/src/WifiBridge.cpp:19-35` | ctor |
| 1 | `apertar-cfe-automounter` | `[cfexpress_hat]`, `[storage]` | `UI/src/CfeAutomounter.cpp:114-131` (`loadConfig`) | daemon start |
| 2 | Core `ExecStartPre` | waits ≤8 s for `/run/apertar-ui/core-start-ready` (written `UI/src/main.cpp:405-420`) | `UI/wait_for_ui_core_start.sh` | — |
| 3 | `start-apertar-core.sh` | env → `--socket /tmp/apertar-core.sock --media /media/RAW` | `Core/scripts/start-apertar-core.sh:4-6`, `:21`; flags `Core/src/main.cpp:56-62` | — |
| 4 | Core `CameraController` ctor | `~/.config/apertar-core/camera_settings.conf` | `CC:7577`, `CC:7598` → `loadPersistedCaptureSettings` `CC:616` | Core restart |
| 5 | Core `CameraSession::start` | tuning preselect from `/home/pi/Tuning-Files/defaults-pisp` | `CC:5254`, `CC:5270`; `Core/src/camera/DefaultTuningSelection.hpp` | each camera open |
| 6 | Core `start()` | `UI.conf` (still mode, long exposure, timelapse, bracketing) | `App:6845-6857` | most commands, 1 s tick |
| 7 | Core `start()` | `apertar-hardware.conf`: trigger, PCF8574, NeoRotary4, GPIO, Grove, tally LED, each with its **own parser** | `App:6881-6896` | **Core restart only** |

**Resolution setting → driver mode (IMX585, 3840x2076 example)**

| # | Layer | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | UI QML | `UI/qml/CameraPage.qml:418-443`, `:1208-1211` | `applyResolutionValue` | Hard-coded IMX585 list + aspect labels → `controlBridge.applyResolution("3840x2076")` | `readonly property var imx585Raw12ResolutionOptions` (2 hits: CameraPage, SettingsPage) |
| 2 | UI C++ | `CB:408-426` | `applyResolution` | `set_resolution {width,height}` (10 s timeout) | `bool ApertarControlBridge::applyResolution` |
| 3 | Core | `App:9314-9324` | `handleCommand` | → `camera_.setResolution` | `if (command.name == "set_resolution") {` |
| 4 | Core | `CC:7711-7738`, `CC:8750-8768` | `setResolution`, `validateResolution` | Refused while recording; must match a known size (`isImx585Raw12CropResolution`, `CC:385-396`); `applySettingsLocked(next, true)` = **reconfigure** | `bool CameraController::setResolution(Resolution resolution)` |
| 5 | Core | `CC:5481` → `CC:5968` | `reconfigure` → `configureAndStart` | Full stop + start incl. CameraManager | `bool configureAndStart(const CaptureSettings &settings, std::string *error)` |
| 6 | Core | `CC:5981-5984`, `CC:2289`, `CC:2205` (IMX585 branch `:2244-2262`) | `sensorModeCandidatesForRequestedResolution` → `sensorModeForRequestedResolution` | Crop sizes pass through as the raw size; 1920/3840 aliases map to 1080p / 4K | `std::vector<SensorModeSelection> sensorModeCandidatesForRequestedResolution` |
| 7 | Core | `CC:6105-6121` | search loop | `rawConfig->size = rawSize`; explicit `sensorConfig->outputSize` + `bitDepth`, then auto; `validate()` + `configure()` | `candidateConfig->sensorConfig->outputSize = rawSize;` |
| 8 | libcamera (rpi/pisp) | not in these repos | pipeline handler | Enumerates sensor sizes through V4L2 `enum_frame_size`, sets the subdev format | — (outside these repos; **unconfirmed** which libcamera build, see KB overview) |
| 9 | Driver | `drv/imx585.c:2071-2091` | `imx585_enum_frame_size` | Lists `get_mode_table()` entries as fixed sizes | `static int imx585_enum_frame_size` |
| 10 | Driver | `drv/imx585.c:1376-1440` | `get_mode_table` | Colour SDR 10/12-bit → `supported_modes[0..19]` (`*num_modes = 20`); Clear HDR 12-bit → `[10]`; 16-bit → `[20]`. Mono similar | `static inline void get_mode_table` |
| 11 | Driver | `drv/imx585.c:2093-2117` | `imx585_set_pad_format` | `v4l2_find_nearest_size` (nearest, never an error) → `imx585_set_framing_limits` (`:1508`) | `static int imx585_set_pad_format` |
| 12 | Driver | `drv/imx585.c:794`, entry `:1006-1020`, regs `:586-592` | `supported_modes[]` | 3840x2076 = entry [11]: `IMX585_WIN_CROP_REGS(54, 2076)` (WINMODE crop, VST 54) | `static const struct cci_reg_sequence mode_3840x2076_regs_12bit[] = {` |
| 13 | Driver | `drv/imx585.c:2138`, `:2204-2209` | `imx585_enable_streams` | Re-picks the mode, writes `mode->reg_list` | `ret = cci_multi_reg_write(imx585->regmap, mode->reg_list.regs,` |
| 14 | Core | `CC:6264-6290` | `configureAndStart` | Log `ApertarCore camera configured: sensor=IMX585 raw=… stream=WxH format=…` | `ApertarCore camera configured: sensor=` |

### A7. Still photo capture

| # | Thread | file:line | Function | What happens | Anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | UI QML | `UI/qml/CameraPage.qml:3792-3810` | `RecordButton.onClicked` (photo mode) | No media → warning; else `beginPhotoCaptureSequence()` (`:1460`) (timer/burst handled in QML) | `root.beginPhotoCaptureSequence()` |
| 2 | UI QML | `UI/qml/CameraPage.qml:1439-1447` | `queueNextPhotoInSequence` | `controlBridge.capturePhoto(format, shots)` | `captureQueued = root.controlBridge.capturePhoto(` |
| 3 | UI C++ | `CB:822-830` | `capturePhoto` | `capture_photo {count, format}` (10 s timeout) | `bool ApertarControlBridge::capturePhoto` |
| 4 | Core | `App:10716-10738` | `capture_photo` branch | Validates count 1-10 (3 with bracketing); `camera_.capturePhoto`; single shot → `photo_capture` event + trigger pulse | `if (command.name == "capture_photo") {` |
| 5 | Core | `CC:8266-8300` | `CameraController::capturePhoto` | → `session_->capturePhoto(mediaRoot_, …)` | `bool CameraController::capturePhoto(PhotoCaptureFormat format, unsigned count)` |
| 6 | Core | `CC:5685-5790`, `CC:924-966` | `CameraSession::capturePhoto` | Reconfigure if no RAW stream; `allocatePhotoBasePath` = `<media>/Photos/Still_yy-mm-dd_C####`; push `PendingPhotoCapture`s | `pendingPhotoCaptures_.insert(pendingPhotoCaptures_.end(),` |
| 7 | libcamera | `CC:6579`, `CC:6958-7178` | `requestComplete` → `capturePhotoFrame` | Matches a frame to the pending shot (timestamp/exposure), copies RAW, `photoWriter_.enqueue` (`:7167`) | `void capturePhotoFrame(libcamera::Request *request` |
| 8 | photo writer | `CC:5018`, `CC:5147-5200`, `CC:5095-5113` | `PhotoCaptureWriter::workerLoop` → `writeDngStill` / rendered JPEG/PNG/TIFF | `AtomicStillFile` = `.writing-XXXXXX` + rename (`Core/src/util/AtomicStillFile.hpp:33`) | `bool writeDngStill(CdngEncoder &encoder` |
| 9 | Core → UI | `CC:5245-5248`; `CB:1184-1189` | drained / error callbacks | `media_write_state`, `photo_write_error` events → `photoCaptureFailed` → CameraPage warning (`CameraPage.qml:1831-1835`) | `emit photoCaptureFailed(m_lastPhotoWriteError);` |

Hardware path: action `photo` (`App:8869-8875`) or `capture` in still mode (`App:8840-8853`) dispatches the same `capture_photo`. WebUI: `beginPhotoCaptureSequence` in `WCP` (called at `WCP:10727`).
