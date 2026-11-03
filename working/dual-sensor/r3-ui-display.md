<!-- Dual sensor, reader report 3 (2026-11-03): the touch UI, the HDMI monitor window and the WebUI preview. Written by a read-only research agent on the Mac from git refs (UI c153c33, Core 31d5418, both drop-frames = what the Pi runs). Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Dual-sensor UI research (read-only)

**Refs.** `U:` = Apertar-UI@c153c33, `C:` = Apertar-Core@31d5418, `K:` = apertar-kb@cf95cce, `CM:` / `CR:` = cinemate@d6cc93e / cinepi-raw@63a08d5 (both `dev`, read via `git grep HEAD`). Example: `U:src/main.cpp:291` = `src/main.cpp:291@c153c33`. All lines were re-grepped on `drop-frames`. KB line numbers are stale: Core `WebControlPage.cpp` is now 20 539 lines, `ApertarCoreApp.cpp` 14 628, UI `CameraPage.qml` 4 349. Labels: CONFIRMED (read in code), PROBABLE (inference), UNCONFIRMED.

**Read these four first**
1. **The HDMI picture on the rig is `ExternalMonitorWindow.qml` (EMW), not CameraPage.** `DisplayConfigBridge` now defaults `hdmi_external_only=true` (`U:src/DisplayConfigBridge.cpp:294,354-357`), which hides the main window (`U:src/main.cpp:432-433`). K says the rig runs it (`K:working/drop-frames/night-2026-11-01.md:242`). CONFIRMED (default), PROBABLE (rig value today). Display modes must go into EMW first.
2. **The WebUI cross-port problem is not only CORS.** Core answers 403 to any request whose `Origin` differs from `http://<Host>` (`C:src/web/WebServer.cpp:159-173,373-376`). An `<img>` to :8001 sends no Origin and works. A `fetch` to :8001 is refused by Core itself, before CORS matters.
3. **`PreviewWindowRenderer::render()` ignores item visibility** (only `scheduleWindowUpdate` checks, `U:src/PreviewWindowRenderer.cpp:347`). Qt also runs the two renderers' slots in connection order, which decides PiP z-order. Details in Q2.
4. **KB trap #13 is stale.** `ensureValidFpsSelection` and `ensureValidResolutionSelection` return immediately when a control bridge exists (`U:qml/CameraPage.qml:1483-1486,1667-1669`; same at upstream-1.6.0). CONFIRMED.

## Q1 Connection to Core

- **Creation (CONFIRMED).** Stack objects in `main()`: preview client `U:src/main.cpp:291`, control bridge `:302`. Context properties `apertarPreviewBridge` `:378` and `apertarControlBridge` `:392`; monitor-only process `:134-135,147-148`. The only registered QML type is `CameraPreviewItem` (`:274`). `Main.qml` passes the bridges to CameraPage as properties (`U:qml/Main.qml:496-517`). EMW and SettingsPage use bare globals. EMW is created from the same engine context (`U:src/ExternalMonitorManager.cpp:194-195`), so new context properties reach it.
- **Preview client path (CONFIRMED).** It is a parameter, `connectToCore(path="/tmp/apertar-core.sock")` (`U:src/ApertarPreviewSocketClient.hpp:31`), stored in `m_socketPath` and reused by the 1 s single-shot reconnect (`...Client.cpp:16-22,50-54,138-144`). It ignores `APERTAR_CONTROL_SOCKET`. A second instance needs no class change.
  - Trap: the four argument-less `connectToCore()` calls (`U:qml/Main.qml:207`, `U:qml/ExternalMonitorWindow.qml:328`, `U:src/main.cpp:228,348`) would send a copy-pasted second client to cam0's socket.
- **Control bridge path (CONFIRMED).** Env `APERTAR_CONTROL_SOCKET`, read at each use, no member: `U:src/ApertarControlBridge.cpp:1168` (command sockets) and `:1805` (event socket). `MediaStatusBridge.cpp:23`, `AudioDeviceBridge.cpp:347` and `SystemActionBridge.cpp:71` read the same env and should stay on cam0.
  - A second instance needs a `socketPath` constructor argument (about 6 lines).
  - Every instance writes `camera/*` placeholder keys to UI.conf on each apply (`:1019-1146`). cam1 would overwrite cam0's cached values, so give it a prefix or skip it.
- **Reconnect (CONFIRMED).**
  - Control: `get_state` poll every 1 s while disconnected, 30 s connected, 1 s with auto ISO/WB (`:17-20,1010-1017`). It is async with a 10 s abort (`:990-1008`).
  - Each `set_*` opens its own socket with a 350 ms connect and 3/8/10/60 s reply timeouts, blocking the GUI thread (`:1148-1242`).
  - Preview: `connected` is true as soon as the AF_UNIX connect succeeds, before any frame (`...Client.cpp:87-92`).
- **Parsing (CONFIRMED).**
  - Control: one real JSON object per line, via `applyCoreMessage` (`:1318-1413`) and `applyCoreState` (`:1437+`).
  - Preview: substring scanning (`:615-655`); only `preview_buffer` and `preview_frame` are handled (`:342-369`); dma-buf fds arrive via `recvmsg` SCM_RIGHTS (`:185-233`).
  - Core broadcasts preview events to every client (`C:src/ApertarCoreApp.cpp:14542-14546`), so each control bridge also JSON-parses its camera's preview lines on the GUI thread (PROBABLE cost).

## Q2 PreviewWindowRenderer

- **Where drawn (CONFIRMED).** `render()` is a DirectConnection slot on `beforeRenderPassRecording` (`U:src/PreviewWindowRenderer.cpp:401-407,2388-2466`). It is GL under the QML scene, window cleared black (`:399`). Border-only Rectangles and the HUD paint over it. Precedent: `U:qml/ExternalMonitorWindow.qml:439-451,1427-1436`.
- **Target rect (CONFIRMED).**
  - It is QML-provided: the item rect mapped to scene × DPR (`:1873-1890`), then centred aspect fit (letterbox/pillarbox, `:52-71`).
  - Aspect is the frame's capture size, overridden by the item's `previewAspectRatio`, multiplied by the anamorphic ratio unless SMPTE, and inverted for ±90° (`:1857-1871`). Source UVs are cropped to that aspect plus zoom/pan (`:81-118`).
  - EMW feeds `previewAspectRatio` from the control bridge's resolution (`U:qml/ExternalMonitorWindow.qml:146,427`).
- **Frames (CONFIRMED).** `previewFrameReady` → `scheduleWindowUpdate` (`:428-444,342-355`). The next render reads `currentPreviewFrame()` (`:446-452,2405`).
- **dma-buf to EGLImage (CONFIRMED).**
  - `ensureImported` (`:1604-1855`) caches in `m_importedBuffers`, keyed by fstat dev/ino (`:462-474`), with 3 dup'd fds per buffer.
  - The image is `DRM_FORMAT_YUV420` BT.709 narrow, bound to `GL_TEXTURE_EXTERNAL_OES` (`:1751-1791`).
  - A layout, sequence-reset or capture-size change wipes the whole cache (`:1630-1639`).
- **Aids (CONFIRMED).**
  - One fragment shader does LUT, false colour, greyscale, zebra and peaking (`:867-911`). The peaking texel is hard-coded 1/1920×1/1080 (`:858`). A passthrough program is used when no aid is on (`:2042-2054,2277-2284`).
  - The touch window uses FBO plus blit, cached by `previewStateChanged` (`:1225-1259,1938-2192`).
  - The HDMI window uses the direct path with no cache (`:2194-2386`, set at `U:src/ExternalMonitorManager.cpp:233-235`), as do the monitor-only process (`U:src/main.cpp:178-180`) and Pi 3.
- **Env knobs (CONFIRMED).** `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}` (`:296-301`). `APERTAR_UI_PREVIEW_RECORDING_FPS` lives in the socket client (`...Client.cpp:26-34,488-498`), fed by `recordingChanged` (`U:src/main.cpp:351-352`). It is process-wide env, so two clients share one cap.
- **Singletons (CONFIRMED by grep).** None. File-scope statics are only GLSL strings (`:681-927`), and the client has one `static constexpr` (`.hpp:49`).
- **Recommendation: two renderer instances.**
  - `setPreviewItem(item)` takes the bridge from `item->bridge` (`:357-426`), so no edits inside the 2.4k-line class.
  - One renderer with two sources needs per-source copies of dozens of members (cache, texture, FBO, last frame, layout state). It would thrash `cleanupImportedBuffers` on every alternation (PROBABLE: each Core has its own frame-id counter).
  - Traps: (a) the visibility check above: hide by size 0 or add `if (!m_item->isVisible()) return;`. (b) Draw order is connection order, so the inset must belong to the later renderer. Use fixed `main` and `inset` item roles and swap the bridge between them for `pip_cam1`; a swap costs one cache rebuild (PROBABLE). (c) `connected` does not mean "has a frame" (Q1). Add `hasFrame` plus a stale watchdog; `currentPreviewFrame()` is cleared only on disconnect. Without a frame, `render()` draws nothing (black, `:2421-2434`).
- **Cost (K measured; PROBABLE for dual).**
  - 4K Clear HDR 16-bit 25 fps lost 6-10 % of frames with peaking/zebra on, 1.7 % with peaking off, and about 0 with the UI frozen (`U` commit messages c234d77, a51c95e, 4724007).
  - Later work traced most of it to page-cache pressure. With `APERTAR_DNG_DONTNEED=sync` the original UI lost 0 in 3-minute takes and 25/15 000 in 10 minutes (`K:working/drop-frames/README.md:151-185`). The margin is thin, not zero.
  - UI-side tricks (fast peaking, CPU mask, direct draw, DRM plane) were reverted or parked (`U` c153c33, b333343, 1c7a3ad, 010f8ad).
  - My arithmetic: fill cost follows pixels, not sources. `both` on 1080p is about 1.04 Mpx against 2.07 Mpx for one full-screen draw. PiP adds 0.28² ≈ 8 %.
  - What is new: a second import path, up to double window redraws (each source calls `update()`), and the second Core's own load.
  - Keep aids off the second pane (passthrough) and consider a per-client fps cap.
  - Preview buffers are about 1280x720 (commit messages 4724007, b333343).

## Q3 CameraPage / EMW layout and the closest pattern

- **CameraPage (CONFIRMED).** Preview area `previewContainer` with `CameraPreviewItem preview` filling it (`U:qml/CameraPage.qml:2102-2134`). Overlays by banner:
  - Status: `StatusChip`, `ControlsWarning` and `DroppedFrameWarning` top-left (`:2683-2733`); still-photo chips top-right (`:2735-2877`).
  - Dynamic overlay (`:3004-3008`): top stats `TopDropdownStat` FPS/ISO/SHUTTER/WB, and the quick menu (`:3282`).
  - Bottom stats (`:3738-3833`): FORMAT and MEDIA left, CPU and POWER right. Bottom row: clip button, audio meter, timecode, record (`:3848-3950`).
- **EMW (CONFIRMED).** `monitorSurface` (`U:qml/ExternalMonitorWindow.qml:389-396`) holds `preview` filling it (`:404-428`), then the HUD layer with margin 36 and z 20 (`:819-823`).
  - HUD parts: top info row (`:201-207`), audio meter (`:985`), status pill (`:1085`), dropped-frames chip (`:1181`), timecode (`:1205`), REMAINING (`:1218`).
  - The HUD uses `apertarControlBridge` 53 times.
- **Closest pattern: the `externalMonitor{Mode,InfoOverlay,Orientation}` quartet (CONFIRMED).**
  - UI: `SettingsBridge` Q_PROPERTY (`U:src/SettingsBridge.hpp:47-50`), load `:360-366`, poll `:547-550`, setter `:1074-1092`, preset save/apply `:2165-2168,2257-2260`. Settings row `MonitoringRow` with `SettingsChoice` (`U:qml/SettingsPage.qml:2450-2491`), listed in `defaultMonitoringOrder` (`:786-787`) and the dispatcher (`:2275-2276`). Consumer: `U:qml/ExternalMonitorWindow.qml:48-62`.
  - Core: normaliser (`C:src/ApertarCoreApp.cpp:863-869`), snapshot (`:1870-1873`), reader (`:2040-2047`), preset payload (`:7767-7773`), state `ui.external_monitor_mode` (`:9617`), command (`:13267-13278`), help list (`:12496`).
  - WebUI: select (`C:src/web/WebControlPage.cpp:5272`), wiring `applySelectCommand` (`:18897,20329`), optimistic patch (`:14129`).
- **Storage and sync (CONFIRMED).** The value lives in UI.conf, not Core state and not `camera_settings.conf`.
  - UI change: SettingsBridge writes the file, Core re-reads it on every `/api/state` (`C:...:9293`), and the WebUI sees it within its 1 s poll.
  - WebUI change: Core writes the file (no event), and the UI sees it via file watch with a 10 s fallback poll (`U:src/SettingsBridge.cpp:418-436`). Flow `K:llm/flows.md` A3.
- **Why not the others.**
  - Aid toggles are bools whose consumer is the shader.
  - The Controls chip is read-only Core state (`U:qml/ControlsWarning.qml`, `CameraPage.qml:2711-2721`); good for a read-only "CAM1 no signal" chip.
  - Mode Ladder: the UI only has a `ladderActive` flag (`U:src/ApertarControlBridge.hpp:22`). The WebUI `quickLadderPill` is read-only (`C:...:4485`), and the state lives in Core.

## Q4 Automatic UI-to-Core commands

| Send | Trigger | With two Cores |
|---|---|---|
| `set_fps` / `set_resolution` | `ensureValid*` | none, no-ops (finding 4) |
| `user_activity` | any input (`U:src/main.cpp:332-333`; `ApertarControlBridge.cpp:1312-1316`) | send to both. Each Core runs its own idle-to-standby timer (`C:src/ApertarCoreApp.cpp:8269-8282,12229-12236`), so otherwise cam1 idles into standby alone |
| `get_state` | timer | one per bridge |
| `enter_standby` / `wake` | Settings button (`U:qml/SettingsPage.qml:5764`), power button (`Main.qml:272`) | both. Standby fan-out follows bridge 0 only (`main.cpp:335-350`; EMW `:321-330`) |
| `record_stop` / `timelapse_stop` | photo-mode change (`U:qml/CameraPage.qml:1878-1889`) | both |
| `record_start` / `record_stop`, `capture_photo`, `timelapse_*` | user taps | per record policy. `record_start` carries audio and gyro args from UI.conf (`ApertarControlBridge.cpp:912-943`), so only cam0 may get them. `record_stop` blocks up to 60 s on the GUI thread, once per Core |
| `eject_media`, `format_media`, speed test; `set_fan_mode` | user | cam0 (`MediaStatusBridge.cpp:1193-1224`, `SystemActionBridge.cpp:66-97`) |

`hardware_action` events are routed from bridge 0 only (`Main.qml:285-290`). All CONFIRMED.

## Q5 Per-camera status

- **CameraPage:** FPS/ISO/SHUTTER/WB; REC/READY/PRE-ROLL/NO MEDIA/WRITING pill with buffer bar (`CameraPage.qml:2686-2709`); dropped-frames chip with count (`:2723-2733`, `DroppedFrameWarning.qml:5-6`); FORMAT; MEDIA time left; UI-computed timecode; audio meter (`:3887,4077`).
- **HDMI:** the same, plus a resolution line with bit depth and Clear HDR (`EMW:125-129`).
- **Sensor name:** `sensorName` feeds only sensor-specific lists and Settings > Info; it is not shown on the camera page.
- **Minimal per camera for v1:** tag `CAM n` plus `sensorName`, `resolution` and `fps`, REC/READY pill, dropped count, and `connected` (no-signal state). All are properties of a second bridge (`U:src/ApertarControlBridge.hpp:16,37,54,59-64,92`).
- **Keep cam0-only:** ISO/shutter/WB/format, audio meter, CPU/POWER.
- **Time left must combine both data rates.** `MediaStatusBridge` multiplies a single `frameSizeMB × fps` set by CameraPage (`U:src/MediaStatusBridge.cpp:381-383`). Its mount path is hard-coded `/media/RAW` (`.hpp:142`).

## Q6 WebUI (Core)

- **Preview markup (CONFIRMED).**
  - `#previewStage` has CSS `aspect-ratio` from cam0's resolution (`C:src/web/WebControlPage.cpp:309-315,9261-9276`).
  - It holds `<img id="previewStream">` with `object-fit: cover` (`:4406,317-325`), a `previewProcessedCanvas` for aids (`:4407`), badges (`:4448-4457`), a centre overlay (`:4459`) and the footer with timecode and record (`:4466`).
  - `installPreviewStream` sets `src="/preview.mjpeg?stream=n"` (`:13656-13683`).
  - `pbPauseLive` removes `src` to stop the stream (`:12047-12053`).
- **State and commands (CONFIRMED).**
  - `setInterval(fetchState, 1000)` on `fetch("/api/state")` (`:20530,16238`).
  - Commands are `sendCommand` → POST `/api/command`, with an optimistic patch (`:14326-14361`).
  - All URLs are relative same-origin; no absolute URL is ever built.
- **CORS (CONFIRMED).** No CORS headers exist (`C:src/web/WebServer.cpp:130-157`). `OPTIONS` returns a bare 204 (`C:src/ApertarCoreApp.cpp:8327-8332`). Core also refuses cross-origin requests (finding 2).
- **MJPEG cost (CONFIRMED).** Encoding runs only while viewers > 0 (`:9735`), at ≤ 640x360, q75, ≤ 30 fps (`:79-97`). Each Core accepts at most 32 web clients (`WebServer.cpp:274`).
- **Aids on a cross-port `<img>` (CONFIRMED mechanism, PROBABLE browser behaviour).** Aids process the `<img>` through WebGL `texImage2D` (`:13473`) or 2D `getImageData` (`:13564`). A cross-origin image without CORS taints both, so cam1 would be unprocessed.
- **Least intrusive option.**
  - Add a second `<img>` pointing at `location.hostname:<peerPort>/preview.mjpeg` with no `crossorigin` attribute. Remove `src` when hidden.
  - Do CSS panes for `both` and 28 %/3 % absolute positioning for PiP.
  - Show no cam1 badges at first. cam1's own full WebUI at :8001 already works unchanged.
- **Showing cam1 state in the primary page** needs either (i) sibling-origin allow plus `Access-Control-Allow-Origin` and preflight in cam1 Core (small, but loosens the anti-CSRF guard), or (ii) a proxy route in the primary (larger: it needs an HTTP client).

## Q7 UI.conf

- **Sharing (CONFIRMED).**
  - UI: `QSettings("CinePi","UI")` (`U:src/SettingsBridge.cpp:287`); `pollExternalSettings` re-reads every key (`:507-599`).
  - Core: path (`C:src/ApertarCoreApp.cpp:517-524`); `updateSharedUiGeneralSettings` takes a Qt-compatible lock and does an atomic rename, and accepts any key (`:2217-2302`); `readSharedUiSettings` is a whitelist (`:1967`).
  - Two Cores plus the UI share one file safely; the lock exists.
- **Naming (CONFIRMED).** camelCase keys; bools `...Enabled` as "true"/"false"; enums stored as human labels ("Clean Feed", "Thirds") that Core normalises (`:863-869`). WebUI state JSON is snake_case under `ui.*` (`:9595-9640`).
- **A new key fits.** `previewSource` mirrors Cinemate's `hdmi_preview_source` and `set_preview_source` (`CM:docs/redis-keys.md:51`, `docs/cli-commands.md:108`). The edit list is exactly the Q3 quartet.
  - Values are a design call: Apertar-style labels or Cinemate tokens `both|cam0|cam1|pip_cam0|pip_cam1`. The normaliser can accept both plus aliases.
  - Keep inset constants (0.28, lower_right, 0.03) in QML.
- **Owner.** The file is neutral. cam0's Core (:8000) is the practical writer, the UI is the only consumer, and :8001 reads the same value. Show the selector only on the :8000 page.

## Q8 HDMI / display

- **Display config (CONFIRMED).** `DisplayConfigBridge` reads `[display]` once, all properties CONSTANT, from `$APERTAR_HARDWARE_CONFIG` then `/home/pi/...` then `/boot/...` (`U:src/DisplayConfigBridge.cpp:22-36,285-362`). Defaults are 1920x1080, `landscape_large`, `hdmi_external_only=true`.
- **EGLFS (CONFIRMED).**
  - The KMS JSON sets only `device` and `hwcursor:false`; no mode or rotation is forced (`U:run_pi_direct.sh:198-221`).
  - Render loop is `basic`, so GL and socket reads share the GUI thread (`U:src/main.cpp:254-256`).
  - Surface is GLES2, swap interval 1 (`:258-265`).
  - The HDMI window is set to the screen geometry and shown fullscreen (`U:src/ExternalMonitorManager.cpp:250-256`).
  - The actual mode is UNCONFIRMED; read the "direct display" journal line.
- **Two textures (CONFIRMED absence, PROBABLE conclusion).**
  - Two renderers share one window GL context. No limit is visible in the code.
  - Core has no DRM code at all (grep: zero hits in `src` and `CMakeLists.txt`), so there is no DRM master contention.
  - Practical limits are GPU and memory bandwidth, vsync, and 3 dup'd fds per imported buffer × both slot sets.
- **Parked plane work.** `APERTAR_PREVIEW_PLANE` (c13b846) was reverted by 010f8ad and parked on branch `preview-plane` (`K:fork-log.md:187-188`). It rewrote the Qt KMS env and used legacy `drmModeSetPlane`. It is not a base for dual.

## Least-intrusive UI design sketch

**C++ (UI)**
- `ApertarControlBridge(QObject*, QString socketPath={})`: replace the two env reads (`:1168,1805`) and prefix or skip the `camera/*` keys.
- `main.cpp`, only when a cam1 socket is configured: add `apertarPreviewBridge1` and `apertarControlBridge1` beside `:378/:392`. QML guards with `typeof ... !== "undefined"` (K counts 120 existing guards: `K:llm/ui-map.md:575`).
  - Wire `userActivity` to both bridges (`:332`).
  - Wire standby with the explicit cam1 path (`:343-349`; EMW `:321-330`).
  - Wire `recordingChanged` to `setRecording` (`:351-352`).
- Second `PreviewWindowRenderer` in three places:
  - `main.cpp:511-515`
  - `ExternalMonitorManager.cpp:231-238`, plus a member in `ExternalMonitorManager.hpp:41-42` and cleanup at `:221-226,264-278`
  - `main.cpp:176-181` (split-DRM only)
- Client: add `hasFrame` plus watchdog; make `connectToCore()` default to the last path. Renderer: add the `isVisible()` guard.
- `SettingsBridge`: add `previewSource` by copying the `externalMonitorMode` quartet.

**QML (EMW first)**
- Add `externalPreviewItem1` in `monitorSurface`.
- Use a pure-QML `layoutRect(source, role)` with 0.28 / lower_right / 0.03, matching Cinemate (`CR:cinepi/dualHdmiPreviewStage.cpp:118-120`).
- Draw the white frame and centre divider as border-only Rectangles, copying `externalPhotoFramePulse`. Cinemate: frame `CR:...:386-398`, inset frame thickness 2 at `:552`.
- The effective source is the requested one unless `!hasFrame1`, then cam0. Cinemate falls back the same way for cam1 and PiP (`CR:...:481-487`).
- Bind aids only to the main item; the inset stays passthrough.
- Disable guides, centre marker and level overlay unless the source is a single camera.
- HUD stays cam0, plus a compact CAM1 tag built from `StatusChip` and `DroppedFrameWarning`. A `hud` indirection (53 references) is the expensive part; do it only for single-cam1 mode.
- CameraPage later. The touch Settings row is optional (no touch screen).

**Core**
- Add `set_preview_source` as a copy of `:13267-13278`, with the normaliser, snapshot key, `ui.preview_source` in state, help list and optional hardware-action cycle (the `external_monitor` action is at `:10627`).
- Add a peer port (CLI option or state field) for the WebUI.
- `--socket` and `--web-port` already exist (`C:src/main.cpp:32-35,56-82`).

**WebUI**
- Second `<img>` in `#previewStage`, plus a select in the Live preview card's existing read-only "Preview source" row (`:5229-5232`).
- Aids on the cam0 pane only. Stream stop and optimistic patch follow the patterns cited in Q6.

## Open questions

1. **Config.** Is the rig's `hdmi_external_only` still true today (EMW vs CameraPage)? Where does the cam1 socket path live: `apertar-hardware.conf` or env?
2. **cam1 Core.** It always opens the first non-USB libcamera camera (`C:src/camera/CameraController.cpp:7262-7265`) and has no camera-index option. Also unresolved:
   - media root;
   - `camera_settings.conf`;
   - GPIO, rotary and tally ownership (cam1 Core must ignore the hardware conf);
   - ALSA and IMU (cam0 only).
3. **Record policy.** Cinemate's `follow_preview` versus `always_both` (`CM:docs/dual-sensors.md:39-45`). Which Core receives `record_start`? Two blocking `record_stop` waits stall both previews.
4. **Performance.** Re-run the 4K Clear HDR 16-bit 25 fps campaign with `sync`, a second preview and aids off. Decide on a per-client fps cap with data.
5. **WebUI.** CORS plus sibling-origin allow, or a proxy, or neither; which host and port the page uses for the peer.
6. **Stale frames.** What counts as "no frame" for the fallback: disconnect only, or a timeout?
7. **Naming.** UI.conf labels versus Cinemate tokens.
8. **Split-DRM.** Does the monitor-only process need the same additions?
9. **Combined time-left.** The `MediaStatusBridge` redesign for two writers on one drive.
10. **KB.** Fix trap #13, the `hdmi_external_only` default, and the Core line maps.
