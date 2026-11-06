# Diagrams: architecture, image path, control path

Start with §0. Mermaid views of [overview.md](overview.md), [core.md](core.md), [ui.md](ui.md) and the traces in
[../llm/flows.md](../llm/flows.md). Refs are against `upstream-1.6.0`, like those pages. The diagrams
leave out detail; follow the links for `path:line`. Renders in Obsidian and on GitHub.

## 0. Start here: the coding map

Interactive version (click boxes and arrows, step through flows): https://tiramisioux.github.io/apertar-coding-map/
(public; source and master copy: `~/Documents/Apertar/apertar-coding-map`, GitHub `Tiramisioux/apertar-coding-map`).

One picture for working on the code yourself. Every box names the file you open.

**How to read it**
- 🟩 green box = **Apertar-UI** repo (`~/ApertarUI`), 🟦 blue = **Apertar-Core** repo (`~/ApertarCore`),
  🟪 purple = the **WebUI** (its HTML/JS is a C++ string *inside Core*), ⬜ grey = hardware,
  🟦 cyan cylinder = a file on disk, 🟥 red hexagon = the one place every command passes.
- **Top to bottom** = the order things happen: you → front ends → the hub → camera → picture out → where it ends up. The people are at the top (you act)
  and again at the bottom (you see the picture). Every path starts with its repo.
- **Arrows: colour = what moves, line = how it travels.**

  | Line | Means | Example |
  | --- | --- | --- |
  | thin blue ─── | a command, as a **function call** inside one program | ② `apply*()`, ④ `camera_.set*()` |
  | **thick blue ━━━** | a command as a **message between programs** (socket or HTTP): change both ends, they must agree on the field names | ③ `set_iso` on the socket, `POST /api/command` |
  | thin green dashed ╌╌╌ | new state coming back **inside one program** | ⑦ `Q_PROPERTY` → QML binding |
  | **thick green dashed ╍╍╍** | new state coming back **between programs** | ⑥ `settings` event (Core *pushes* to the UI); `GET /api/state` (the WebUI *asks* every 1 s, so that arrow points at Core) |
  | **very thick orange ━━━** | pictures (heavy data, every frame) | frames → recorders, preview |
  | thin grey dotted ┈┈┈ | settings handed over **through a file**, not a message | `UI.conf` |

  Rule of thumb: a **thick** arrow is where you cross a boundary. That is where a typo in a
  field name fails silently, so check both sides.

```mermaid
%%{init: {"flowchart": {"curve": "basis", "nodeSpacing": 30, "rankSpacing": 55, "padding": 14}, "themeVariables": {"fontSize": "19px"}}}%%
flowchart TB
    TOUCH(["👆 Touch screen"])
    BROWSER(["🌐 Browser"])
    BTN(["🎛️ Buttons / encoders"])

    QML("<b>Screens</b><br/>ApertarUI/qml/<br/>CameraPage.qml")
    BRIDGE("<b>C++ bridge</b><br/>ApertarUI/src/<br/>ApertarControlBridge.cpp")
    WEBPAGE("<b>WebUI page</b><br/>ApertarCore/src/web/<br/>WebControlPage.cpp")
    HWIN("<b>Hardware inputs</b><br/>ApertarCore/src/hardware/<br/>*Input.cpp")

    HUB{{"<b>handleCommand</b><br/>ApertarCore/src/<br/>ApertarCoreApp.cpp"}}

    CAM("<b>Camera</b><br/>ApertarCore/src/camera/<br/>CameraController.cpp")
    SENSOR("<b>📷 IMX585</b><br/>libcamera")

    RECS("<b>Recorders</b><br/>ApertarCore/src/<br/>cdng · mlv · prores · video")
    PUB("<b>Preview out</b><br/>publishPreviewFrame<br/>streamMjpeg")

    DISK[("💾 /media/RAW")]
    UICONF[("📄 UI.conf")]
    RENDER("<b>Preview drawing</b><br/>ApertarUI/src/<br/>PreviewWindowRenderer.cpp")
    SCREEN(["👆 Touch screen<br/>shows the picture"])
    BROWSEROUT(["🌐 Browser<br/>shows the picture"])

  TOUCH -- "① tap" --> QML
  QML -- "② apply*()" --> BRIDGE
  BRIDGE -- "③ socket" --> HUB
  BROWSER -- "① click" --> WEBPAGE
  WEBPAGE -- "③ HTTP POST" --> HUB
  BTN -- "① press" --> HWIN
  HWIN -- "③ dispatch" --> HUB
  HUB -- "④ set*()" --> CAM
  CAM -- "⑤ controls" --> SENSOR

  SENSOR == "frames" ==> RECS
  RECS == "files" ==> DISK
  SENSOR == "frames" ==> PUB
  PUB == "dma-buf" ==> RENDER
  RENDER ==> SCREEN
  PUB == "MJPEG" ==> BROWSEROUT

  CAM -- "⑥ settings event" ---> BRIDGE
  WEBPAGE -- "⑥ asks every 1 s<br/>GET /api/state" ---> HUB
  BRIDGE -- "⑦ binding" ---> QML

  QML -. "touch aids" .-> UICONF
  HUB -. "WebUI aids" .-> UICONF
  UICONF -. "watcher" .-> RENDER

  classDef ui fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:2px
  classDef core fill:#dbeafe,stroke:#2563eb,color:#1e3a8a,stroke-width:2px
  classDef web fill:#f3e8ff,stroke:#9333ea,color:#581c87,stroke-width:2px
  classDef hw fill:#e5e7eb,stroke:#4b5563,color:#111827,stroke-width:2px
  classDef file fill:#cffafe,stroke:#0891b2,color:#164e63,stroke-width:2px
  classDef hub fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:3px
  class QML,BRIDGE,RENDER,TOUCH,SCREEN ui
  class CAM,RECS,PUB,HWIN core
  class WEBPAGE,BROWSER,BROWSEROUT web
  class SENSOR,BTN hw
  class DISK,UICONF file
  class HUB hub

  linkStyle 0,1,3,5,6,7,8 stroke:#2563eb,stroke-width:1.5px
  linkStyle 2,4 stroke:#2563eb,stroke-width:4px
  linkStyle 9,10,11,12,13,14 stroke:#ea580c,stroke-width:7px
  linkStyle 17 stroke:#16a34a,stroke-width:1.5px,stroke-dasharray:8 5
  linkStyle 15,16 stroke:#16a34a,stroke-width:4px,stroke-dasharray:8 5
  linkStyle 18,19,20 stroke:#64748b,stroke-width:1.5px,stroke-dasharray:2 5
```

**What travels on each arrow: one ISO change to 800, followed through the code**

The numbers match the arrows. JSON is shortened with `…`. The full trace with line refs is
[flows.md A1](../llm/flows.md).

| Step | Arrow | Kind | What it looks like in the code |
| --- | --- | --- | --- |
| ① | tap → Screens | touch | `CameraPage.qml`: `root.controlBridge.applyIso(v)` |
| ② | Screens → C++ bridge | function call | `ApertarControlBridge::applyIso("800")` → `sendCoreCommand(...)` |
| ③ | bridge → hub | **Unix socket** `/tmp/apertar-core.sock`, one JSON line | `{"cmd":"set_iso","id":7,"value":"800"}\n` |
| ③ | WebUI → hub | **HTTP** | `POST /api/command` with body `{"cmd":"set_iso","value":"800"}` (`sendCommand(...)` in the page JS) |
| ③ | buttons → hub | function call on the poll thread | `apertar-hardware.conf`: `encoder0_cw=iso_up` → `dispatch("set_iso", …)` |
| hub | inside `handleCommand` | if-branch | `if (command.name == "set_iso") { camera_.setIso(value); … }` |
| ④ | hub → Camera | function call | `CameraController::setIso(800)` → `AnalogueGain = max(1, iso / 100)` = 8.0 |
| ⑤ | Camera → sensor | libcamera control | `request->controls().merge(pendingControls_);` (lands one frame later) |
| ⑥ | Camera → bridge | **socket event**, pushed to every client | `{"event":"settings",…,"iso":800,"iso_auto":false,…}` |
| ⑥ | WebUI → hub | **HTTP poll**, every 1 s | `GET /api/state` → `{…,"iso":800,"iso_auto":false,…}` |
| ⑦ | bridge → Screens | Qt property | `setIso("800")` emits `isoChanged` → QML `function onIsoChanged()` |
| preview | Preview out → UI | **socket + file descriptors** (`SCM_RIGHTS`) | once per buffer: `{"event":"preview_buffer",…}` + fds; then each frame `{"event":"preview_frame","slot":2,…}` |
| preview | Preview out → browser | **HTTP stream** | `<img src="/preview.mjpeg?stream=…">`, multipart JPEG |
| file | anyone → `UI.conf` | **INI file**, file-watched | `[General]` / `zebraEnabled=true` |

Try ③ and ⑥ yourself from the Mac (the same calls the WebUI makes; values are strings because
Core's parser is flat):

```bash
curl -s -m 5 http://apertar.local:8000/api/state | grep -o '"iso":[0-9]*'
```

```bash
curl -s -m 5 -X POST http://apertar.local:8000/api/command -d '{"cmd":"set_iso","value":"800"}'
```

(The second one changes the camera. The note "manual-addendum talk-to-core" has more.)

**Where your change goes** (follow the arrows; each row is one of them)

| You want to… | Touch these, in arrow order | Don't forget |
| --- | --- | --- |
| Add a control on the touch screen for an existing camera setting | `QML` → bridge `apply*()` | The command already exists: grep `command.name == "set_` in `ApertarCoreApp.cpp` |
| Add a new camera setting | `handleCommand` branch → `CameraController::set*` → `controlsForSettings` | State goes back in **three** hand-written copies: `settingsBody`, `settingsEvent`, `buildWebStateJson` ([change-recipes.md](../llm/change-recipes.md)) |
| Show it in the WebUI | `WebControlPage.cpp` (`renderSnapshot`, `sendCommand`) | Core must be rebuilt: the page is compiled into it |
| Map a button or encoder to it | `handleSingleHardwareInputAction` + `normalizeAction` in each `*Input.cpp` | Config is read once: restart Core |
| Change how the preview looks (aid, overlay) | `PreviewWindowRenderer.cpp` shader + `CameraPreviewItem` | Aids live in `UI.conf`, not in Core's state |
| Change what is written to disk | `src/cdng/…` or the recorder in `CameraController.cpp` | Never build while a take runs |

Rebuild after a change: UI `cmake --build ~/ApertarUI/build`, Core `cmake --build ~/ApertarCore-build -j2`,
then restart the matching service ([build.md](build.md#quick-reference)).

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
