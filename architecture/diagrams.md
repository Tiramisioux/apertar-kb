# Diagrams: architecture, image path, control path

Mermaid views of [overview.md](overview.md), [core.md](core.md), [ui.md](ui.md) and the traces in
[../llm/flows.md](../llm/flows.md). Refs are against `upstream-1.6.0`, like those pages. The diagrams
leave out detail; follow the links for `path:line`. Renders in Obsidian and on GitHub.

## 1. Processes and channels

```mermaid
flowchart TB
  subgraph HW["Hardware"]
    SENSOR["IMX585 sensor<br/>(imx585 V4L2 driver, DKMS)"]
    CFE["CFE hat<br/>I2C 0x34 buttons + LED, NVMe"]
    INPUTS["PCF8574 / NeoRotary4 /<br/>GPIO buttons / Grove analog"]
    OUTS["Tally / REC LED,<br/>trigger out"]
    INA["INA219 battery"]
    ALSA["ALSA audio in/out"]
    DISP["Touch / HDMI display<br/>(DRM/KMS)"]
  end

  subgraph CORE["apertar-core (apertar-core.service)"]
    LC["libcamera + PiSP<br/>CameraController / CameraSession"]
    REC["Recorders<br/>cDNG, lossy DNG, MLV,<br/>H.264, ProRes, stills, WAV"]
    CMD["handleCommand<br/>(commandMutex_)"]
    CS["ControlServer<br/>/tmp/apertar-core.sock"]
    WEB["Web server :8000<br/>WebUI page + /api/state<br/>+ /api/command + /preview.mjpeg"]
    HWIN["Hardware input threads"]
    PREV["Preview publisher +<br/>MJPEG encoder threads"]
  end

  subgraph UIP["Apertar-UI (apertar-ui-direct.service)"]
    QML["QML pages<br/>CameraPage, SettingsPage"]
    BR["C++ bridges<br/>ApertarControlBridge, SettingsBridge,<br/>MediaStatusBridge, Ina219Bridge"]
    PSC["ApertarPreviewSocketClient"]
    REN["PreviewWindowRenderer<br/>EGL dma-buf import + aid shaders"]
  end

  MON["Apertar-UI monitor-only<br/>(HDMI on another DRM card)"]
  NET["apertar-network-helper<br/>hotspot fallback"]
  AUTO["apertar-cfe-automounter<br/>mount /media/RAW"]
  ROOT["root helpers<br/>apertar-standby-usb / -low-power"]
  BROWSER["Browser (phone / laptop)<br/>WebUI"]

  subgraph FILES["Shared files"]
    UICONF["~/.config/CinePi/UI.conf"]
    HWCONF["~/apertar-hardware.conf"]
    CAMCONF["~/.config/apertar-core/<br/>camera_settings.conf"]
    MEDIA["/media/RAW (NVMe)"]
  end

  SENSOR --> LC
  LC --> REC --> MEDIA
  LC --> PREV
  CS <--> CMD
  WEB <--> CMD
  HWIN --> CMD
  CMD --> LC
  INPUTS -- "I2C / GPIO poll" --> HWIN
  CMD --> OUTS
  ALSA --> REC

  BR <-- "JSON lines + events" --> CS
  PSC <-- "preview fds (SCM_RIGHTS)" --> CS
  PSC --> REN --> DISP
  QML <--> BR
  INA -- "I2C" --> BR

  BROWSER <-- "HTTP :8000" --> WEB

  MON <-- "own socket connections" --> CS
  UIP -- "monitor-state.sock" --> MON
  MON --> DISP

  CFE -- "I2C" --> AUTO --> MEDIA
  CMD -- "sudo -n" --> ROOT
  NET -- "nmcli" --> NM["NetworkManager"]

  CMD <--> UICONF
  BR <--> UICONF
  CMD --> CAMCONF
  HWCONF -.-> CORE
  HWCONF -.-> UIP
  HWCONF -.-> AUTO
```

Startup order (readiness files, not systemd `After=`): UI loads `Main.qml` → writes
`/run/apertar-ui/core-start-ready` → Core's `ExecStartPre` gate (≤8 s) → Core opens the camera, then
binds the socket, then starts the WebUI and the hardware inputs. See
[overview.md](overview.md#startup-order-and-readiness-files).

## 2. Image data

Two branches leave `requestComplete` for every frame: the preview (touch screen and WebUI) and
the recording. Recording is RAW (DNG/MLV) or processed YUV/RGB (H.264/ProRes), never both.

```mermaid
flowchart LR
  S["IMX585<br/>CSI-2 RAW"] --> ISP["libcamera / PiSP<br/>(Raw + VideoRecording /<br/>Viewfinder streams)"]
  ISP --> RC["CameraSession::requestComplete<br/>(libcamera thread, per frame)"]

  subgraph RECPATH["Recording"]
    direction TB
    RC -- "RAW plane copy" --> DQ["DngRecordingQueue<br/>(queue full → drop)"]
    DQ --> W["DNG workers ×min(8, cores+1)<br/>CdngEncoder / LJ92"]
    W --> DNG["cDNG_yy-mm-dd_C####/<br/>*_#########.dng"]
    RC -- "RAW" --> MLV["MlvEncoder → .MLV"]
    RC -- "RAW (lossy)" --> LDNG["LossyDngEncoder<br/>3:1 / 5:1"]
    RC -- "YUV420" --> H264["H264PreviewRecorder<br/>libx264 (.so) → .mp4"]
    RC -- "RGB48" --> PRO["ProresRecorder<br/>prores_aw (.so) → .mov"]
    RC -- "still request" --> PH["PhotoCaptureWriter<br/>DNG / JPEG / PNG / TIFF"]
    AUD["ALSA capture"] --> WAV["AudioRecordingSession<br/>BWF .wav in clip folder"]
  end

  subgraph PREVPATH["Preview"]
    direction TB
    RC -- "YUV420 dma-buf" --> EPF["enqueuePreviewFrame<br/>(newest frame only)"]
    EPF --> PUB["runPreviewPublisher"]
    PUB -- "preview_buffer (fds once)<br/>preview_frame (slot id)" --> SOCK["/tmp/apertar-core.sock<br/>SCM_RIGHTS, every client"]
    SOCK --> PSC["UI ApertarPreviewSocketClient"]
    PSC --> EGL["PreviewWindowRenderer<br/>eglCreateImageKHR → OES texture<br/>zebra / peaking / false colour / LUT"]
    EGL --> SCREEN["Touch screen<br/>(+ monitor-only UI on HDMI)"]

    EPF -- "only while MJPEG viewers > 0,<br/>≤640x360, rate-limited" --> CAP["captureWebPreviewFrame<br/>(I420 downsample)"]
    CAP --> JPG["runMjpegEncoder<br/>TurboJPEG q75"]
    JPG -- "multipart /preview.mjpeg" --> WEBPV["WebUI preview &lt;img&gt;<br/>in the browser"]
  end

  DNG --> MEDIA[("/media/RAW")]
  MLV --> MEDIA
  LDNG --> MEDIA
  H264 --> MEDIA
  PRO --> MEDIA
  PH --> MEDIA
  WAV --> MEDIA
  MEDIA -. "clip browser / playback" .-> PLAY["UI playback<br/>(cliplistmodel, playbackcontroller)"]
```

Notes:
- The touch preview is zero-copy: the UI renders straight from Core's dma-bufs. The WebUI preview is
  a CPU copy, downsampled and JPEG-encoded in Core, and costs nothing while no browser watches.
- The aids (zebra, peaking, false colour) exist only in the UI's shaders. The WebUI image has none.
- Trace with line refs: [flows.md A4](../llm/flows.md) (preview), A2 (record write path).

## 3. Controls and state

Three entry points (touch UI, WebUI, hardware buttons/encoders) converge on one function,
`handleCommand`. State comes back three different ways: a broadcast `settings` event (UI), a 1 s
poll of `/api/state` (WebUI), and the `UI.conf` file (UI-side settings such as aids).

```mermaid
flowchart TB
  subgraph ENTRY["Entry points"]
    TOUCH["Touch UI<br/>QML → ApertarControlBridge::apply*"]
    WEBUI["WebUI in the browser<br/>sendCommand()"]
    BTN["Buttons / encoders<br/>PCF8574, NeoRotary4, GPIO"]
  end

  TOUCH -- "new QLocalSocket per command<br/>{cmd:set_iso,id,value}<br/>(GUI thread blocks for the reply)" --> CSRV["ControlServer::clientLoop<br/>→ handleRequest"]
  WEBUI -- "POST /api/command" --> HWC["handleWebCommand"]
  BTN -- "poll thread → action name<br/>(iso_up, record_toggle, …)" --> HIA["handleHardwareInputAction<br/>→ dispatchHardwareInputCommand (id=-1)"]

  CSRV --> HC{{"handleCommand<br/>(commandMutex_, standby + media gates)"}}
  HWC --> HC
  HIA --> HC

  HC -- "set_iso / shutter / wb / fps …" --> CC["CameraController::set*<br/>→ applySettingsLocked"]
  CC -- "control-only" --> PEND["pendingControls_ → merged into<br/>next requeued libcamera request"]
  CC -- "resolution / format / bit depth" --> RECONF["reconfigure()<br/>full camera stop + start"]
  HC -- "record_start / record_stop" --> RECCTL["startRecording / stopRecording"]
  RECCTL --> TRIG["Tally LED + trigger pulse"]
  CC --> PERS["CaptureSettingsPersister<br/>→ camera_settings.conf"]
  HC -- "set_zebra_enabled and other aids<br/>(no event emitted)" --> UICONF[("UI.conf")]

  CC -- "emitSettingsEventLocked" --> PUBE["publishEvent"]
  RECCTL --> PUBE
  PUBE -- "broadcast settings / standby / audio_level …" --> EVS["UI m_eventSocket<br/>→ applyCoreMessage → applyCoreState"]
  EVS --> QMLP["QML property bindings<br/>(CameraPage iso, recording, …)"]

  UICONF -- "QFileSystemWatcher" --> SB["UI SettingsBridge<br/>→ QML → shader uniforms"]
  TOUCH -. "touch aids write UI.conf directly<br/>(no socket command)" .-> UICONF

  POLL["WebUI fetchState()<br/>every 1 s"] -- "GET /api/state" --> BWS["buildWebStateJson<br/>camera_.settings() + UI.conf<br/>+ media, network, power"]
  BWS --> RENDER["renderSnapshot<br/>(WebUI labels, buttons)"]
  UICONF --> BWS
```

Notes:
- The WebUI never receives socket events; it only sees changes on its next poll. A touch ISO change
  reaches the browser within about 1 s.
- A WebUI aid toggle reaches the touch screen only through `UI.conf` and the file watcher
  ([flows.md A3](../llm/flows.md)).
- `settingsBody`, `settingsEvent` and `buildWebStateJson` are three hand-written copies of the same
  fields (**confirmed in code**): a new setting has to be added to all three
  ([change-recipes.md](../llm/change-recipes.md)).
- Hardware-input commands run on the poll thread; a failure only reaches stderr.
- This rig has no IMU, so the gyro recorder and the UI level never run here, though the code has them.
