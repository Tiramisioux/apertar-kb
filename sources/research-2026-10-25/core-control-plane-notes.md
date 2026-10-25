# Apertar Core control-plane notes (socket, commands, state, persistence, web, UI bridge, ready files)

Read-only research. I edited nothing and ran no git commands. The only file write was a pair of temp files in my scratchpad. I also briefly wrote and then deleted `/tmp/claude-help.txt`.

**Path abbreviations used below.** Expand them for the KB.

| Abbrev | Repo-relative path |
|---|---|
| `App` | `Apertar-Core/src/ApertarCoreApp.cpp` |
| `AppH` | `Apertar-Core/src/ApertarCoreApp.hpp` |
| `CC` | `Apertar-Core/src/camera/CameraController.cpp` |
| `CS` | `Apertar-Core/src/ipc/ControlServer.cpp` |
| `CP` | `Apertar-Core/src/ipc/ControlProtocol.cpp` |
| `WS` | `Apertar-Core/src/web/WebServer.cpp` |
| `WCP` | `Apertar-Core/src/web/WebControlPage.cpp` |
| `Types` | `Apertar-Core/include/apertar/core/Types.hpp` |
| `RC` | `Apertar-Core/include/apertar/core/RecordingCapabilities.hpp` |
| `CB` | `Apertar-UI/src/ApertarControlBridge.cpp` |
| `PSC` | `Apertar-UI/src/ApertarPreviewSocketClient.cpp` |

---

## 1. Unix socket control protocol

### 1.1 Transport and lifecycle
- **Default path** `/tmp/apertar-core.sock`, set at `AppH:33`. CLI `--socket PATH` at `Apertar-Core/src/main.cpp:56-58`, usage text at `main.cpp:32`.
  - Launcher `Apertar-Core/scripts/start-apertar-core.sh:6` uses env `APERTAR_SOCKET_PATH` (default same) and execs `--socket "$SOCKET_PATH" --media "$MEDIA_ROOT"` (`:21`).
- **Socket type**: `AF_UNIX`, `SOCK_STREAM` (`CS:105`).
  - Any stale path is `unlink`ed before `bind` (`CS:121`). Listen backlog is 8 (`CS:130`). The path is unlinked again on stop (`CS:166-169`).
  - No chmod and no `SO_PEERCRED` check. Access is whatever the process umask gives. Exact mode is UNCONFIRMED.
- **Start order** in `App:6801-6903`:
  1. Standby recovery (`6807-6819`)
  2. Preview publisher thread (`6821-6825`)
  3. MJPEG encoder thread, only if web port ≠ 0 (`6827-6836`)
  4. `camera_.start()` (`6838`)
  5. Still settings re-applied from `UI.conf` (`6845-6857`)
  6. `controlServer_.start()` (`6859`)
  7. Web server start (`6869-6879`)
  8. Hardware inputs start
  9. `{"event":"camera_state","state":"ready"}` (`6901`)
  - **Consequence**: the socket only exists after the camera has started. If the camera fails, Core exits with code 1 (`main.cpp:108-111`).
- **Stop** (`App:6905-6941`): publishes `camera_state` `"stopping"` (`6913`), then stops inputs, camera, MJPEG, preview publisher, web server, control server.

### 1.2 Framing
- **Requests**: newline-delimited single-line JSON objects.
  - `clientLoop` reads 512-byte chunks (`CS:239-242`), splits on `\n` (`CS:248`), drops `\r` (`CS:260`).
  - A line over 64 KiB silently closes the connection, with no error reply (`CS:261-262`).
- **Replies and events**: newline-terminated. `sendLine` appends `\n` (`CS:17-19`).
  - One reply can contain **several lines**: the reply object, then any events collected while the command ran (`App:7055-7083`, append loop at `7077-7080`).
- **Request shape**: `{"cmd":"<name>","id":<int>, ...flat params}`.
  - `cmd` is required (`CP:220-226`). `id` is optional and numeric (`CP:228-229`). Default id is -1 (`Apertar-Core/src/ipc/ControlProtocol.hpp:10`).
- **Reply shape**:
  - OK: `{"ok":true[,"id":N][,...body]}` (`App:108-118`).
  - Error: `{"ok":false[,"id":N],"error":"..."}` (`App:120-128`).
  - `id` is only echoed when it is ≥ 0, so the UI's `id:-2` user_activity gets no id back.
  - A parse error replies `errorReply(-1, …)` with no id (`App:7057-7059`).
  - Unknown command: `"Unknown command: <name>"` (`App:10821`).
- **Event shape**: `{"event":"<name>", ...}`. Events never carry `ok` or `id`.

### 1.3 The parser is flat, not real JSON (`CP:164-233`)
- Only a single flat object is accepted. Every value is stored as a **raw string** in `std::map<string,string>` (`Apertar-Core/src/ipc/ControlProtocol.hpp:12`).
- String values are fully unescaped, including `\uXXXX` and surrogate pairs (`CP:62-118`).
- Bare values (numbers, `true`, `null`) are taken verbatim up to `,` or `}` (`CP:120-135`).
  - **Nested objects and arrays are unsupported.** For example `[1,2]` breaks at the comma.
- `number()` uses `std::stod` and rejects trailing junk (`CP:139-154`).
- Booleans are compared as strings, `"true"` or `"1"`, in the handlers.
- `escapeJson` (`CP:235-252`) only escapes `" \ \b \f \n \r \t`. Other control characters below 0x20 pass through, which can produce invalid JSON.
  - Duplicate: `CC:95-134` has its own `escapeJson` that also escapes `<0x20` as `\u00XX`.

### 1.4 Clients and threading (`CS`)
- One accept thread (`CS:139`, `195-234`). Each client gets a **detached thread** (`CS:215-227`).
- At most 32 concurrent workers. Extra connections are accepted and then closed silently (`CS:208-209`).
- The handler runs on the client's thread. Commands are **serialized globally** by `commandMutex_` (`App:9093`).
- **Writes**: every client has a `writeMutex` (`Apertar-Core/src/ipc/ControlServer.hpp:37`). All sends use `MSG_NOSIGNAL|MSG_DONTWAIT` (`CS:25`, `73`).
  - A client whose buffer is full, or that takes a partial write, is **disconnected** (`CS:176-177`, `190-191`, `254-256`).
  - Comment at `CS:24`: "Never let a stalled preview client block camera event delivery".
- `broadcast()` (`CS:172-179`) and `broadcastWithFds()` (`CS:186-193`) go to **every** connected client. There is no subscription filter.

### 1.5 Event delivery: push, not poll
- `publishEvent` (`App:10823-10852`) first runs `handleTriggerEvent` (LED and trigger outputs, `App:10854-10889`).
- These events are **always broadcast immediately** (`App:10829-10840`):
  - `settings`, `recording_health`, `standby`, `still_exposure`, `media_write_state`, `photo_write_error`, `timelapse_progress`
  - `hardware_action` with `standby_power_wake`, `standby_power_sleep` or `power_button_press`
  - Comment: settings "must also reach the separate HDMI process".
- Every other event, published while a socket command is in flight (`collectingCommandEvents_`), is **appended to that requester's reply only** (`App:10842-10848`). Otherwise it is broadcast.
- Web commands (`handleWebCommand`, `App:7085-7091`) and hardware or idle-standby commands do not collect, so their events are broadcast.
- Events that bypass `publishEvent` and broadcast directly:
  - `prepare_recording`, followed by a 220 ms sleep (`App:10692`, `10705`)
  - `photo_capture` for single shots (`App:10728-10732`)

**All events, with emitters:**

| Event | Fields | Emitter |
|---|---|---|
| `camera_state` | `state`: "ready" / "stopping" | `App:6901`, `App:6913` |
| `settings` | full settings, same fields as settingsBody (§3.2) | `CC:136-191` via `emitSettingsEventLocked` `CC:8777-8784` |
| `recording` | `active`, `recording_has_dropped_frames`, `error` | `CC:8786-8796` (calls at `CC:8262`, `8515`, `8532`) |
| `recording` (sound-only) | `active`, `sound_only:true`, `folder` (start only) | `App:8394`, `App:8406` |
| `recording_health` | `recording_has_dropped_frames` | `CC:7580-7584` |
| `audio_level` | `input_level` 0–100 | `CC:7588-7595`; sound recorder `App:8383` |
| `standby` | `standby` bool | `CC:7688`, `CC:7707` |
| `still_exposure` | `still_exposure_active`, `still_exposure_remaining_seconds` | `CC:7566-7574` |
| `media_write_state` | `media_writes_pending`, `media_write_revision` | `CC:7555-7562` |
| `photo_write_error` | `photo_write_error` | `CC:5248`, `CC:7029` |
| `photo_capture` | none | `CC:7177` (bursts, `notifyCapture` = count>1 at `CC:5762`); `App:10730` (single shot) |
| `timelapse` | `active`, `interval_seconds`, `folder` | `CC:8798-8822` |
| `timelapse_frame` | `index` | `CC:8824-8832` |
| `timelapse_progress` | `timelapse_shot_count` | `CC:8440-8445` |
| `prepare_recording` | none | `App:10692`, `App:10705` |
| `hardware_action` | `action` (`zoom_toggle`, `still_mode`, `settings`, `clip_browser`, `quick_menu`, toggle names, power-button actions) | `App:8476`, `8612`, `8619`, `8623`, `8667`, `8904`, `8950` |
| `preview_buffer` / `preview_frame` | see §1.6 | `App:10891-10944` |

### 1.6 Preview channel: same socket, DMA-BUF fds over SCM_RIGHTS
- There is **no separate preview socket and no shared memory.** Preview metadata travels as JSON lines on the same control socket. DMA-BUF fds are attached with `sendmsg` + `SCM_RIGHTS` (`CS:37-77`, all fds in one cmsg at `CS:57-69`).
- **Producer** (libcamera completion path), `CC:7248-7372`:
  - First time a request slot is seen: `dup()` the plane fds, build a `PreviewFrameDescriptor{registration=true}` (`CC:7249-7321`).
    - Three-plane case: one fd per plane (`CC:7253-7270`).
    - Single-plane case: one fd plus computed YUV420 plane offsets and pitches (`CC:7271-7315`).
  - Every frame: `{registration=false}` with libcamera-owned fds that are **not** sent (`CC:7324-7372`).
- Descriptor struct: `Types:220-238`. Fields: `fd`, `planeCount`, `planeFds[3]`, `planeOffsets[3]`, `planePitches[3]`, `planeLengths[3]`, `slotIndex`, `frameId`, `width`, `height`, `stride`, `captureWidth`, `captureHeight`, `size`, `fourcc` (default "YUV420"), `timestampUs`, `registration`.
- **Queueing** (`App:6943-6992`):
  - Registrations are cached per slot in `registeredPreviewFrames_`. A dup goes on a FIFO (`6962-6973`).
  - Per-frame markers are **latest-wins** in `pendingPreviewFrame_` (`6975-6987`).
  - Publisher thread: `App:10946-10986`. Registrations are sent before frames (`10960-10966`).
  - fd ownership helpers: `App:218-239` (`closeOwnedPreviewFrame`), `App:241-277` (`duplicatePreviewFrameDescriptor`).
- **Wire format** (`App:10901-10943`):
  - `preview_buffer` (fds attached):
    ```
    {"event":"preview_buffer","slot":S,"frame_id":F,"timestamp_us":T,"width":W,"height":H,"stride":X,
     "capture_width":CW,"capture_height":CH,"size":N,"fourcc":"...",
     "plane_count":<#fds attached>,"layout_plane_count":<1..3>,
     "plane0_offset":..,"plane0_pitch":..,"plane0_length":.., (plane1_*, plane2_*),
     "fd_attached":true}
    ```
    If `planeCount == 0`: `"plane_count":1` only.
  - `preview_frame` (no fds): `{"event":"preview_frame","slot":S,"frame_id":F,"timestamp_us":T}`. Sent for **every** frame to **every** client. There is no throttle on the socket side.
- **`preview_subscribe`** (`App:10796-10799`) calls `enqueueCurrentPreviewRegistrations` (`App:6994-7019`). That re-sends all cached registrations plus the last frame marker, but via **broadcast to all clients**, not just the subscriber.
- Preview publisher and MJPEG encoder are stopped on `enter_standby` (`App:9147-9148`) and restarted on `wake` (`App:9188-9199`).
- **UI consumer** (`PSC`):
  - Raw non-blocking `AF_UNIX` socket plus `QSocketNotifier` (`PSC:46-72`).
  - Sends `{"cmd":"preview_subscribe","id":0}` (`PSC:147`). Retries after 100 ms (`PSC:76-80`) and reconnects every 1 s single-shot (`PSC:16-22`, `116-122`).
  - `recvmsg` with room for 3 fds (`PSC:167-216`). Pending fds are queued and matched to the next `preview_buffer` line by `plane_count` (`PSC:238-271`).
  - Hand-rolled substring JSON scanning (`PSC:569-625`). Oversized buffer (>1 MiB) is dropped (`PSC:227-231`).
  - Handlers: `handlePreviewBuffer` `PSC:352-447`, `handlePreviewFrame` `PSC:449-567`. Struct: `Apertar-UI/src/PreviewFrameInfo.hpp:5-27`.
  - Default path is a hardcoded `"/tmp/apertar-core.sock"` (`Apertar-UI/src/ApertarPreviewSocketClient.hpp:30`). It **ignores `APERTAR_CONTROL_SOCKET`**.
  - Connected from QML (`Apertar-UI/qml/Main.qml:207`, `Apertar-UI/qml/ExternalMonitorWindow.qml:288-290`) and from the monitor-only process (`Apertar-UI/src/main.cpp:228`).
- **`PreviewExposureReference`** (`Apertar-Core/include/apertar/core/PreviewExposureReference.hpp:9-13`):
  - Struct: `decodeCurve` (vector<[x,y]>), `displayCurve`, `toRec709[9]`.
  - JSON (`:14-30`): `{"decode_curve":[[x,y],..],"display_curve":[[x,y],..],"to_rec709":[9]}` or `null`.
  - Carried as `preview_exposure_reference` in settingsBody, the `settings` event and `/api/state`. It is a `shared_ptr` field of `CaptureSettings` and is not persisted (`Types:150`).
  - UI consumer: `Apertar-UI/src/PreviewExposureReference.hpp:8-51` builds a 1024×2 LUT plus a 3×3 matrix. Read at `CB:1263-1269`.
- **Browser preview** is separate: MJPEG over HTTP (§5.3).

---

## 2. Complete socket command list (110 names)
Dispatcher is `ApertarCoreApp::handleCommand`, `App:9091-10822`.

**Pre-dispatch guards:**
- Media-writes-pending blocks `capture_photo`, `record_start`, and `timelapse_start` when not active (`App:9095-9097`).
- Media actions (`format_media`, `eject_media`, `mount_media`, `run_media_speed_test`) are blocked while busy (`App:9098-9107`).
- Speed test running blocks `record_start`, `capture_photo`, `timelapse_start`, `enter_standby` (`App:9108-9110`).
- Standby blocks the capture commands (`App:9208-9211`).
- User-activity timestamp is updated for `user_activity`, `wake`, `set_*`, `capture_photo`, `record_*`, `timelapse_*` (`App:9111-9117`).

**Reply-body key:**
- **SB** = `settingsBody(camera settings)` (`App:167-216`).
- **IMU** = `imuStatusBody(false)` (`App:130-165`).
- **UI.conf** = writes `~/.config/CinePi/UI.conf` `[General]` via `updateSharedUiGeneralSettings` (`App:1850-1935`).

**Sender key:**
- **U** = Apertar-UI sends it (`CB` unless another file is named).
- **W** = WebControlPage sends it (`WCP` line).
- **H** = hardware input mapping sends it (partial list only).

### 2.1 Session, standby, meta
| cmd | params | effect / reply | handler | senders |
|---|---|---|---|---|
| `user_activity` | – | refresh idle timer; `ok` | `App:9118-9119` | U `CB:1179` (raw write, id -2); W `WCP:11512` |
| `set_standby_timeout` | `value` int 0–86400 | UI.conf `standbyTimeoutSeconds`; `{standby_timeout_seconds}` | `App:9120-9128` | W `WCP:11519` |
| `set_standby_usb_power_off` | `enabled` true/false/1/0 | UI.conf `standbyUsbPowerOff`; `{standby_usb_power_off}` | `App:9129-9137` | W `WCP:11527` |
| `enter_standby` | `idle_timeout` (optional) | `camera_.enterStandby()`, stop preview and MJPEG, `sudo` low-power and USB-off helpers; `{standby:true[,warning]}` | `App:9138-9173` | U `CB:1168`; W `WCP:11316`; H `App:8622-8625`, `8653`; idle loop `App:7043-7049` |
| `wake` | – | restore power helpers, restart publisher threads, `wakeFromStandby`; `{standby:false}` | `App:9174-9207` | U `CB:1173`; W `WCP:11316`; H `App:8643-8647` |
| `ping` | – | `{pong:true}` | `App:9212-9213` | none found |
| `help` | – | `{commands:[98 names]}` (incomplete, see §8) | `App:9215-9216` | none found |
| `get_state` | – | state snapshot (§3.1) | `App:9218-9240` | U `CB:864` (event socket) |
| `preview_subscribe` | – | re-broadcast preview registrations; `{preview_subscribed:true}` | `App:10796-10799` | U `PSC:147` |
| `shutdown` | – | `requestShutdown()` (Core exits); `{shutting_down:true}` | `App:10815-10818` | none found |
| `restart_system` | – | `invokeSystemPowerAction("reboot")` (`App:3202`); `{restarting:true}` | `App:10801-10806` | W `WCP:11329` |
| `power_off_system` | – | `"poweroff"`; `{powering_off:true}` | `App:10808-10813` | W `WCP:11341` |

### 2.2 Exposure, white balance, timing (CameraController setters; reply SB)
| cmd | params | CameraController | handler | senders |
|---|---|---|---|---|
| `set_iso` | `value` (50–51200, checked in CC) | `setIso` `CC:7774` | `App:9242-9249` | U `CB:309`; W `WCP:9888` |
| `set_iso_auto` | – | `setIsoAuto` `CC:7788` | `App:9269-9273` | U `CB:294`; W `WCP:9886` |
| `set_exposure_compensation` | `value` finite EV | `CC:7835` | `App:9251-9258` | U `CB:1110`; W `WCP:11392`; H `App:8691-8700` |
| `set_exposure_metering` | `value` centre-weighted / matrix / spot (aliases `average`, `center-weighted`: `Apertar-Core/src/camera/ExposureMetering.hpp:13-16`) | `CC:7851` | `App:9260-9267` | U `CB:1115`; W `WCP:11396` |
| `set_fps` | `value` (0<fps≤280, checked `CC:7748`) | `CC:7741`; preserves shutter angle `CC:7768-7770` | `App:9275-9282` | U `CB:270`; W `WCP:9877`; H |
| `set_shutter_us` | `value` 1..30,000,000 | `CC:7796` | `App:9284-9291` | U `CB:283`, `339`, `368`; W `WCP:9899` |
| `set_shutter_auto` | – | `CC:7827` | `App:9293-9297` | U `CB:321`, `351`; W `WCP:9897` |
| `set_wb` | `kelvin` | `CC:7888` | `App:9299-9306` | U `CB:399`; W `WCP:9912`, `11596` |
| `set_wb_auto` | – | `CC:7906` | `App:9308-9312` | U `CB:384`; W `WCP:9910` |

### 2.3 Format, codec, geometry (reply SB)
| cmd | params | notes | handler | senders |
|---|---|---|---|---|
| `set_resolution` | `width`, `height` | `CC:7711` | `App:9314-9324` | U `CB:417`; W `WCP:5454-5508` |
| `set_record_format` | `value` (normalized at `App:824-844`: cdng / mlv / h264 / lossydng / prores plus aliases) | `CC:7918` | `App:9326-9338` | U `CB:457`, `528`, `535`; W `WCP:5624`, `5628`, `7017`, `9940` |
| `set_cdng_compression` | `value` none / lossless_jpeg | `CC:7973` | `App:9340-9349` | U `CB:537`; W `WCP:5629` |
| `set_lossy_dng_ratio` | `value` (3to1 default; 5 / 5:1 / 5to1 / r5 → R5, `App:859-866`) | `CC:7985` | `App:9351-9358` | U `CB:460`, `530`; W `WCP:5625`, `7021`, `9944` |
| `set_cdng_preview_color_profile` | `value` standard / arri_logc4 / sony_slog3 / davinci_intermediate / p3_d60_linear | `CC:8031` | `App:9360-9367` | U `CB:491`; W `WCP:11406` |
| `set_prores_color_profile` | `value` (same set) | `CC:8014` | `App:9369-9376` | U `CB:482`; W `WCP:11401` |
| `set_prores_profile` | `value` proxy / lt / 422 / hq | `CC:8001` | `App:9378-9386` | U `CB:468`, `508`; W `WCP:7019`, `9942` |
| `set_tuning_file` | `path` | `CC:8044` | `App:9388-9395` | U `CB:565` only |
| `set_raw_bit_depth` | `value`: number (8/10, else 12) or string (`App:868-879`) | `CC:8114` | `App:9397-9410` | U `CB:590`; W `WCP:7031`, `9958` |
| `set_h264_resolution` | `width`, `height` (0,0 = match) | `CC:8150` | `App:9412-9422` | U `CB:610`; W `WCP:5707-5714`, `10939` |
| `set_timecode_mode` | `value`: exactly `"rec_run"` → RecRun, anything else → FreeRun | `CC:8176`; also UI.conf `timecodeMode` "Rec Run"/"Free Run" | `App:9424-9437` | U `CB:630`; W `WCP:7043`, `10023` |
| `set_af_mode` | `value` manual / auto / else continuous (`App:394-402`) | `CC:8184` | `App:9439-9446` | U `CB:646`; W `WCP:7050`, `10031` |
| `set_af_range` | `value` macro / full / else normal (`App:404-412`) | `CC:8192` | `App:9448-9455` | U `CB:662`; W `WCP:7056`, `10039` |
| `set_af_speed` | `value` fast / else normal (`App:414-420`) | `CC:8200` | `App:9457-9464` | U `CB:678`; W `WCP:7059`, `10047` |
| `set_af_window` | `x`, `y`, `width`, `height` (normalized) | `CC:8208` | `App:9466-9476` | U `CB:697`; W `WCP:5890-5891` |

### 2.4 Capture mode, still, timelapse, recording
| cmd | params | effect / reply | handler | senders |
|---|---|---|---|---|
| `set_capture_mode` | `value` clip / still / timelapse | `setStillExposureMode` + UI.conf `photoModeEnabled`, `photoTimelapse`, `photoFormat`, `soundRecorderEnabled`, `lastPhotoTimelapse`; SB + `photo_timelapse`, `photo_format` | `App:9537-9572` | U `CB:733` only |
| `set_photo_mode_enabled` | `enabled` | stop timelapse if false, `setStillExposureMode`, UI.conf; SB | `App:9573-9599` | U `CB:728`; W `WCP:6963`, `9974`; H `App:8900-8905` |
| `set_photo_bracketing_enabled` | `enabled` true/false/1/0 | `applyCapturePreset` + UI.conf; SB | `App:9600-9611` | U `CB:745`; W `WCP:9993` |
| `set_photo_bracketing_ev` | `value` 1/3..3, rounded to 1/3 | same pattern; SB | `App:9612-9622` | U `CB:819`; W `WCP:6976`, `10865` |
| `set_photo_long_exposure_enabled` | `enabled` | same pattern; SB | `App:9623-9639` | U `CB:738`; W `WCP:9985` |
| `set_photo_timer` | `value` Off / 2s / 5s / 10s / 15s / 20s / 25s / 30s (`App:422-430`) | UI.conf `photoTimer`; `{photo_timer}` | `App:9890-9901` | W `WCP:6970`, `10832` |
| `set_photo_burst` | `value` Single / 3 / 5 / 10 Shots (`App:432-438`) | UI.conf; `{photo_burst}` | `App:9903-9914` | W `WCP:6977`, `10866` |
| `set_photo_format` | `value` DNG / JPEG / PNG / TIFF / DNG+X variants | UI.conf; `{photo_format}` | `App:9916-9944` | W `WCP:6967`, `10854` |
| `set_photo_timelapse` | `value` (Off, or 0.1–86400 s, or N m, `App:472-508`), `format` (optional) | stop, or start/retarget timelapse + UI.conf; `{photo_timelapse, photo_format, timelapse_active, interval_seconds} + SB` | `App:9946-9996` | U `CB:721`; W `WCP:6982`, `10849`, `10889`, `10909`, `11385` |
| `timelapse_start` | `value`, `format` (optional) | `startTimelapse` + UI.conf; `{timelapse_active, photo_timelapse, photo_format, interval_seconds}` | `App:10740-10773` | U `CB:763`; W `WCP:10714` |
| `timelapse_stop` | – | `{timelapse_active:false, media_writes_pending, media_write_revision}` | `App:10775-10781` | U `CB:763`; W `WCP:10700` |
| `capture_photo` | `format` (optional), `count` 1–10 (forced to 3 when bracketing) | `camera_.capturePhoto`; `{photo_capture, photo_count, media_writes_pending, media_write_revision}` | `App:10716-10738` | U `CB:829`; W `WCP:9277` |
| `record_start` | `sound_only`, `gyro_enabled`, `audio_enabled`, `audio_monitoring_enabled`, `audio_input_volume`, `audio_output_volume`, `audio_input_device`, `audio_output_device` (all optional; defaults from UI.conf) | sound-only path → `startSoundRecording` (`App:8337-8397`); else `camera_.startRecording` (`CC:8219`); `{recording:true, recording_has_dropped_frames}` or `{recording:true, sound_recording:true}` | `App:10623-10714` | U `CB:810` (args built `CB:777-815`); W `WCP:10757` |
| `record_stop` | – | stop sound recorder or camera; `{recording:false, ...}` | `App:10783-10794` | U `CB:810`; W `WCP:10732` |
| `set_sound_recorder_enabled` | `enabled` | requires an audio input; forces still mode off; UI.conf; SB | `App:9513-9536` | W `WCP:6996`, `10011` |

### 2.5 Shared-UI toggles: `handleUiToggle` (`App:9478-9491`)
- Param: `enabled`. Writes one UI.conf key. **Reply is SB, not the new value.**
- **No event is emitted.** The native UI notices through a file watcher (§4.4).

| cmd | UI.conf key | line | W |
|---|---|---|---|
| `set_focus_peaking_enabled` | focusPeakingEnabled | `App:9493` | `WCP:6868`, `10079` |
| `set_zebra_enabled` | zebraEnabled | `App:9495` | `WCP:6882`, `10087` |
| `set_false_color_enabled` | falseColorEnabled | `App:9497` | `WCP:6893`, `10095` |
| `set_lut_preview_enabled` | lutPreviewEnabled | `App:9499` | `WCP:6904`, `10103` |
| `set_guides_enabled` | guidesEnabled | `App:9501` | `WCP:6921`, `10119` |
| `set_center_marker_enabled` | centerMarkerEnabled | `App:9503` | `WCP:6935`, `10127` |
| `set_grayscale_enabled` | grayscaleEnabled | `App:9505` | `WCP:6946`, `10135` |
| `set_smpte_enabled` | smpteEnabled | `App:9507` | `WCP:6915`, `10111` |
| `set_anamorphic_desqueeze_enabled` | anamorphicDesqueezeEnabled | `App:9509` | `WCP:6952`, `10143` |
| `set_external_monitor_enabled` | externalMonitorEnabled | `App:9511` | `WCP:6851`, `10071` |
| `set_date_time_overlay_enabled` | dateTimeOverlayEnabled | `App:9640` | `WCP:7173`, `10063` |
| `set_record_audio_enabled` | recordAudioEnabled | `App:9642` | `WCP:7070`, `10155` |
| `set_record_gyro_enabled` | recordGyroEnabled | `App:9644` | `WCP:7037`, `9966` |
| `set_live_audio_monitoring_enabled` | liveAudioMonitoringEnabled | `App:9724` | `WCP:7073`, `10163` |
| `set_audio_meter_enabled` | audioMeterEnabled | `App:9726` | `WCP:7076`, `10171`; H `App:8944-8946` |

### 2.6 Monitoring and UI value settings (UI.conf only; reply echoes the value unless noted)
| cmd | params / accepted values | handler | W |
|---|---|---|---|
| `set_focus_peaking_threshold` | `value` clamped 0–1 | `App:9729-9737` | `WCP:6872`, `11440` |
| `set_focus_peaking_color` | `value` Red / Green / Blue / Yellow / Pink (`App:647-659`) | `App:9739-9750` | `WCP:6875`, `11443` |
| `set_zebra_threshold` | `value` 0–1 | `App:9752-9760` | `WCP:6886`, `11446` |
| `set_false_color_mode` | `value` Exposure Based / Skin Tone / Highlight Priority / Shadow Priority → int 0–3 (`App:703-725`) | `App:9762-9774` | `WCP:6897`, `11449` |
| `set_lut_preview_file` | `value` path or "" (allow-list `App:5634`; dirs `App:5571-5600`, including `/home/pi/LUTs` at `5574`) | `App:9776-9800` | `WCP:6908`, `11452` |
| `set_guides_type` | `value` Thirds / 16:9 / 2.39:1 / 4:3 / 1:1 / Academy 1.37:1 / 5:4 / 9:16 / 14:9 | `App:9802-9813` | `WCP:6925`, `11455` |
| `set_guides_thickness` | `value` 1–4 | `App:9815-9823` | `WCP:6928` |
| `set_center_marker_type` | `value` Circle/Dot / Crosshair | `App:9825-9836` | `WCP:6939` |
| `set_anamorphic_ratio` | `value` 1.33x / 1.5x / 1.8x / 2.0x | `App:9838-9849` | `WCP:6956` |
| `set_external_monitor_mode` | `value` Clean Feed / Assist Feed | `App:9851-9862` | `WCP:6855`, `11431` |
| `set_external_monitor_info_overlay` | `value` On / Off | `App:9864-9875` | `WCP:6858`, `11434` |
| `set_external_monitor_orientation` | `value` Landscape / Upside Down | `App:9877-9888` | `WCP:6861`, `11437` |
| `set_ui_orientation` | `value` Landscape / Left Side / Right Side / Upside Down ("Left"→"Right Side", "Right"→"Left Side", `App:362-371`); **no rejection**; reply SB | `App:9998-10007` | `WCP:7155`, `10804` |
| `set_camera_controls_opacity` | `value` clamped 0.15–1; reply SB | `App:10009-10018` | `WCP:7163`, `10814` |
| `set_camera_controls_mode` | `value` Dark / else Light; reply SB | `App:10020-10029` | `WCP:7166`, `10823` |
| `set_favorites_order` | `value` comma list of ids (`App:727-822`) | `App:10219-10228` | `WCP:6502` |
| `set_sleep_mode` | `value` Off / 1 / 2 / 5 / 10 min | `App:10206-10217` | `WCP:7147`, `11255` |

### 2.7 Audio
| cmd | params | effect | handler | senders |
|---|---|---|---|---|
| `audio_capabilities` | `device` (optional) | refused while recording; `TimestampedAudioCapture::probe`; `{device, modes:[{format,rate,channels}]}` | `App:10031-10050` | U `Apertar-UI/src/AudioDeviceBridge.cpp:330`; W `WCP:11109` |
| `set_audio_capture_options` | `format`, `rate` 0–192000, `channels` | UI.conf `audioSampleFormat`, `audioSampleRate`, `audioChannels`; `{audio_options_saved}` | `App:10052-10074` | W `WCP:11145` |
| `set_audio_input_device` | `value` | resolved against detected devices (`App:2786`, `2610`); UI.conf | `App:10076-10089` | W `WCP:7080`, `11155` |
| `set_audio_output_device` | `value` | same | `App:10091-10102` | W `WCP:7083`, `11165` |
| `set_input_volume` | `value` 0–100 | UI.conf `inputVolume` | `App:10104-10112` | W `WCP:7090`, `11178` |
| `set_headphone_volume` | `value` 0–100 | UI.conf `headphoneVolume` | `App:10114-10122` | W `WCP:7093`, `11192` |

### 2.8 Battery and power UI settings (UI.conf)
| cmd | params | handler | W |
|---|---|---|---|
| `set_battery_type` | `value` V-Mount / NP-F / LP-E6 / USB-C / DC / Custom (`App:571-584`); also rewrites capacity and voltages | `App:10124-10151` | `WCP:7100`, `11212` |
| `set_battery_capacity` | `value` (must fit the type, `App:618-637`) | `App:10153-10165` | `WCP:7103`, `11202` |
| `set_custom_battery_wh` | `value` 10–500 | `App:10167-10176` | `WCP:7109`, `7113`, `11227` |
| `set_custom_battery_voltage` | `full` and/or `empty` (0.5–60) | `App:10178-10204` | `WCP:7121-7130`, `11238` |

### 2.9 IMU and gyro (persist to the `[imu]` section of the hardware config; reply IMU)
| cmd | params | handler | W |
|---|---|---|---|
| `set_imu_driver` | `value` | `App:9646-9655` → `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:1295` | `WCP:10949` |
| `set_imu_orientation` | `value` | `App:9656-9665` → `Mpu6050RecordingSession.cpp:1303` | `WCP:10960` |
| `set_imu_sync_offset` | `value` ms | `App:9666-9675` → `:1322` | none found |
| `adjust_imu_sync_offset` | `delta` ms | `App:9676-9686` | `WCP:10970` |
| `reset_imu_sync_offset` | – | `App:9687-9692` | `WCP:10979` |
| `set_imu_level_reference` | – | `App:9693-9698` → `:1335` | `WCP:10988` |
| `clear_imu_level_reference` | – | `App:9699-9704` → `:1370` | `WCP:10999` |
| `calibrate_gyro` | `seconds` (default 2.5); refused while recording | `App:9705-9722` → `:1035`; reply `{gyro_calibrated, samples, gyro_bias_x/y/z, config_path}` | U `CB:835`; W `WCP:11018` |

### 2.10 System, media, presets
| cmd | params | effect | handler | senders |
|---|---|---|---|---|
| `apply_date_time` | `year`, `month`, `day`, `hour`, `minute`, `time_zone` | `applyDateTimeSettings` `App:3215` (timedatectl / hwclock) | `App:10529-10550` | W `WCP:7204`, `11046` |
| `apply_time_zone` | `time_zone` | `App:3270`; `{time_zone, local_time_input, network_time_synced}` | `App:10552-10566` | W `WCP:11073` |
| `set_fan_mode` | `value` Silent / Auto / Full Blast | rewrites a managed block in `/boot/firmware/config.txt` via `sudo -n install` (`App:3127-3178`, constants `2843-2845`) | `App:10568-10577` | W `WCP:7245`, `11093` |
| `format_media` | `filesystem` (default exfat) | `formatMediaAtPath` `App:3763` | `App:10579-10587` | U `Apertar-UI/src/MediaStatusBridge.cpp:1192` (360 s timeout); W `WCP:11270` |
| `eject_media` | – | `ejectMediaAtPath` `App:3710` | `App:10589-10594` | U `MediaStatusBridge.cpp:1183`; W `WCP:11282` |
| `mount_media` | `device_path` | `mountMediaDeviceAtPath` `App:3657` | `App:10596-10606` | W `WCP:11298` |
| `get_media_test_state` | – | `{running, mbps, bytes, used_fio, error}` | `App:10608-10615` | U `MediaStatusBridge.cpp:1214` |
| `run_media_speed_test` | – | starts thread `App:8957-9083`; `{media_speed_test_started}` | `App:10616-10621` | U `MediaStatusBridge.cpp:1201`; W `WCP:11307` |
| `apply_preset` | flat preset keys (below) | one combined `applyCapturePreset` (`CC:8604-8657`) + UI.conf commit callback; `{applied_preset, state:{SB}}` | `App:10230-10527` | U `CB:1160`; W `WCP:10521` |

**`apply_preset` accepted keys** (`App:10268-10519`):
- `presetName`
- Camera keys:
  - `cameraExposureMetering`, `cameraExposureCompensation` (−3..3)
  - `cameraRecordingFormat`, `cameraTuningFile`
  - `cameraProresColorProfile`, `cameraCdngPreviewColorProfile`, `cameraProresProfile`
  - `cameraCdngCompression` (also `lossy_3to1` / `lossy_5to1`), `cameraLossyDngRatio`
  - `cameraRawBitDepth`
  - `cameraResolutionWidth` + `cameraResolutionHeight`, or `cameraResolution`
  - `cameraH264Resolution`
  - `cameraFps` (≤280), `cameraIso` (Auto or 50–51200)
  - `cameraShutterMode` (speed / angle), `cameraShutterSpeed`, `cameraShutterAngle`
  - `cameraWhiteBalance` (Auto or 1500–12000 K)
  - `cameraAutofocusMode`, `cameraAutofocusRange`, `cameraAutofocusSpeed`
  - `cameraAutofocusWindowX`, `...Y`, `...Width`, `...Height`
- Still keys: `timecodeMode`, `photoModeEnabled`, `photoLongExposureEnabled`, `photoBracketingEnabled`, `photoBracketingEv`
- UI keys:
  - Exposure aids: `zebraEnabled`, `zebraThreshold`, `focusPeakingEnabled`, `focusPeakingThreshold`, `focusPeakingColor`, `grayscaleEnabled`, `smpteEnabled`, `falseColorEnabled`, `falseColorMode`
  - LUT and level: `lutPreviewEnabled`, `lutPreviewFile`, `horizontalLevelEnabled`, `horizontalLevelColor`
  - Framing: `anamorphicDesqueezeEnabled`, `anamorphicRatio`, `guidesEnabled`, `guidesThickness`, `guidesType`, `centerMarkerEnabled`, `centerMarkerType`
  - External monitor: `externalMonitorEnabled`, `externalMonitorMode`, `externalMonitorInfoOverlay`, `externalMonitorOrientation`
  - Interface: `uiOrientation`, `cameraControlsMode`, `cameraControlsOpacity`, `dateTimeOverlayEnabled`
  - Photo: `photoTimer`, `photoBurst`, `photoFormat`, `photoTimelapse`
  - Audio: `soundRecorderEnabled`, `recordAudioEnabled`, `recordGyroEnabled`, `liveAudioMonitoringEnabled`, `audioMeterEnabled`, `inputVolume`, `headphoneVolume`, `audioInputDevice`, `audioOutputDevice`, `audioSampleFormat`, `audioSampleRate`, `audioChannels`
  - Battery: `batteryType`, `batteryCapacity`, `customBatteryWh`, `customBatteryFullVoltage`, `customBatteryEmptyVoltage`, `sleepMode`
  - Layout orders: `monitoringOrder`, `recordOrder`, `audioOrder`, `powerOrder`, `systemOrder`, `wifiOrder`, `infoOrder`, `sidebarOrder`, `favoritesOrder`
  - Standby: `standbyTimeoutSeconds`, `standbyUsbPowerOff`

---

## 3. State snapshots and every emitted field

### 3.1 `get_state` reply (`App:9218-9240`)
`ok`, `id`, then:
- `state` (offline / starting / ready / standby / recording / error / stopping; `Types:240-252`)
- `standby`
- `recording` (camera OR sound recorder)
- `recording_error`, `recording_has_dropped_frames`, `sound_recording`
- `timelapse_active`, `timelapse_interval_seconds`, `timelapse_shot_count`
- `still_exposure_active`, `still_exposure_remaining_seconds`
- `photo_write_error`, `media_writes_pending`, `media_write_revision`
- `sensor`
- plus all settingsBody fields (§3.2)

Not in `get_state`: shared UI settings, IMU, system telemetry, media info. Those exist only in `/api/state`.

### 3.2 `settingsBody` (`App:167-216`) and `settings` event (`CC:136-191`)
The two field lists are identical, but the code is duplicated. A third copy lives inline in `buildWebStateJson` (§3.3).
- Geometry and exposure: `resolution` ("WxH"), `width`, `height`, `fps` (fixed 3 dp, sticky precision), `iso`, `iso_auto`, `shutter_us`, `shutter_auto`, `exposure_compensation`, `exposure_compensation_available`
- Metering: `exposure_metering`, `exposure_metering_modes[]` (`Apertar-Core/src/camera/ExposureMetering.hpp:28-39`)
- Still: `photo_mode_enabled`, `photo_long_exposure_enabled`, `photo_bracketing_enabled`, `photo_bracketing_ev`
- White balance: `wb_kelvin`, `wb_auto`, `wb_available`, `wb_measured`, `wb_actual_kelvin`, `wb_actual_red_gain`, `wb_actual_blue_gain`
- `recording_capabilities{raw_compression, raw_recording, prores, h264_hardware, h264_max_width, h264_max_height, h264_max_fps}` (`RC:52-62`)
- Codec: `recording_format` (cdng / mlv / h264 / lossydng / prores), `cdng_compression` (none / lossless_jpeg), `lossy_dng_ratio` (3to1 / 5to1), `prores_profile` (hq / 422 / lt / proxy), `prores_color_profile`, `cdng_preview_color_profile`
- `preview_exposure_reference` (object or null)
- `tuning_file`, `raw_bit_depth`, `h264_resolution` ("WxH" or "match"), `h264_width`, `h264_height`
- `timecode_mode` (free_run / rec_run)
- Autofocus: `af_mode`, `af_range`, `af_speed`, `af_window_x`, `af_window_y`, `af_window_w`, `af_window_h`

### 3.3 Web `GET /api/state` (`buildWebStateJson`, `App:7711-8046`; serialized from `7835`)
It has no `ok` field.
- **Top level** (`7835-7900`):
  - `state`, `standby`, `standby_timeout_seconds`, `standby_usb_power_off`, `standby_usb_powered_off`
  - `recording`, `recording_error`, `recording_has_dropped_frames`, `sound_recording`
  - `timelapse_active`, `timelapse_interval_seconds`, `timelapse_shot_count`
  - `still_exposure_active`, `still_exposure_remaining_seconds`, `photo_write_error`, `media_writes_pending`, `media_write_revision`
  - `recording_elapsed_seconds` (`7853`), `timecode_local_ms_of_day`, `backend_name` ("Apertar-Core / libcamera", `7855`), `sensor`
  - Camera settings (the same as SB **except** the `photo_*` fields are not at top level), with `timecode_mode` at `7871`
  - `media_mounted` (`7898`), `network_transport`, `network_host` (`7900`)
- **`system{}`** (`7901-7949`):
  - CPU: `cpu_usage_percent`, `cpu_usage_label`, `cpu_temp_c`, `cpu_temp_percent`, `cpu_temp_label`
  - Power: `power_draw_w`, `power_draw_percent`, `power_draw_label`, `battery_voltage_v`, `battery_current_a`, `battery_percent` (`7914`; fallback formula at `7823`), `battery_label`, `power_sensor_available`
  - Media: `media_free_bytes`, `media_total_bytes`, `media_used_percent`, `media_label` (`7921`), `media_drives[]{device_path, display_name, label, model, filesystem_type, size_text, mount_point}` (`App:2392-2411`)
  - Estimates: `record_time_left_minutes`, `record_stills_left`, `time_left_percent`, `time_left_label`
  - Time: `time_zone`, `time_zone_options[]`, `local_time_input`
  - `fan_mode`
  - Speed test: `write_speed_running`, `write_speed_result_text`, `write_speed_detail_text`, `write_speed_error`
- **`capture{}`** (`7950-7964`): `codec` (`7951-7955`), `sensor`, `storage`, `preview` ("MJPEG preview"), `network`.
- **`ui{}`** (`7965-8021`):
  - `timecode_mode` (`7966`, the UI.conf string "Free Run" / "Rec Run")
  - Exposure aids: `focus_peaking_enabled`, `focus_peaking_threshold`, `focus_peaking_color`, `zebra_enabled`, `zebra_threshold`, `false_color_enabled`, `false_color_mode`, `grayscale_enabled`, `smpte_enabled`
  - LUT: `lut_preview_enabled`, `lut_preview_file`, `lut_preview_options[]`
  - Framing: `anamorphic_desqueeze_enabled`, `anamorphic_ratio`, `guides_enabled`, `guides_type`, `guides_thickness`, `center_marker_enabled`, `center_marker_type`
  - External monitor: `external_monitor_enabled`, `external_monitor_mode`, `external_monitor_info_overlay`, `external_monitor_orientation`
  - Interface: `ui_orientation`, `camera_controls_opacity`, `camera_controls_mode`, `date_time_overlay_enabled`
  - Photo: `photo_mode_enabled`, `photo_long_exposure_enabled`, `photo_bracketing_enabled`, `photo_bracketing_ev` (`7997`), `photo_timer`, `photo_burst`, `photo_format`, `photo_timelapse`
  - Audio: `sound_recorder_enabled`, `record_audio_enabled`, `record_gyro_enabled`, `live_audio_monitoring_enabled`, `audio_meter_enabled`, `audio_input_device`, `audio_output_device`, `audio_sample_format`, `audio_sample_rate`, `audio_channels`, `input_volume`, `headphone_volume`
  - Battery: `battery_type`, `battery_capacity`, `custom_battery_wh`, `custom_battery_full_voltage`, `custom_battery_empty_voltage`, `sleep_mode`
  - `favorites_order[]`
- **`audio{}`** (`8022-8027`): `input_devices[{id,label}]`, `output_devices[]` (`App:2827-2841`), `has_input_devices`, `has_output_devices`.
- **`imu{}`** (`8028`, `imuStatusBody(true)` at `App:130-165`):
  - Config: `enabled`, `driver`, `driver_label`, `sync_mode`, `bus`, `address`, `address_hex`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation`, `config_path`
  - Sync and level: `sync_offset_ms`, `sync_offset_text`, `level_reference_set`, `level_reference_text`, `level_accel_x_g`, `level_accel_y_g`, `level_accel_z_g`
  - Live sample: `live_available`, `live_status_text`, `accel_x_g`, `accel_y_g`, `accel_z_g`, `gyro_x_dps`, `gyro_y_dps`, `gyro_z_dps`
- **`device{}`** (`8029-8044`): `pi_model`, `serial_number`, `os_version`, `kernel_version`, `uptime_text`, `ip_address`, `hostname`, `ram_total_text`, `ram_available_text`, `ram_used_text`, `system_storage_total_text`, `system_storage_free_text`, `system_storage_mount_point`.
- **Fields emitted twice or from different sources:**
  - `timecode_mode` appears twice. Top level is the camera enum string (`7871`); `ui.timecode_mode` is the UI.conf display string (`7966`).
  - `ui.photo_bracketing_ev` comes from **camera** settings (`7997`), while the other `ui.*` photo fields come from UI.conf.

### 3.4 Other JSON documents
- `/api/media` (`App:7673-7709`): `ok`, `mounted`, `media_root`, `items[{id, kind, category, type, name, size_bytes, size_text, file_count, frame_count, duration_text, fps_text, modified_text, modified_ms, download_url}]`.
- `/api/presets` (`App:7651-7671`): `ok`, `presets[{name, file_name, size_bytes, size_text, modified_text, download_url}]`.
- `/api/config` GET (`App:5290-5321`): `ok`, `path`, `display_path`, `exists`, `size_bytes`, `size_text`, `modified_text`, `text`.

---

## 4. Control-state model, setting flow, persistence

### 4.1 Enums (`Types`)
| Enum | Values | Line |
|---|---|---|
| `CameraState` | Offline, Starting, Ready, Standby, Recording, Error, Stopping | `Types:14-22` |
| `BayerPattern` | | `:24-30` |
| `RawBitDepth` | 8 / 10 / 12 / 16 | `:32-37` |
| `PixelPacking` | Unpacked, Csi2Packed, PispCompressed1 | `:39-43` |
| `RecordingFormat` | Cdng, Mlv, H264, LossyDng, Prores | `:45-51` |
| `CdngCompression` | Uncompressed, LosslessJpeg | `:53-56` |
| `LossyDngRatio` | R3, R5 | `:58-61` |
| `ProresProfile` | HQ, Standard, LT, Proxy | `:63-68` |
| `PhotoCaptureFormat` | Dng, Jpeg, Png, Tiff, DngJpeg, DngPng, DngTiff | `:70-78` |
| `TimecodeMode` | FreeRun, RecRun | `:80-83` |
| `AutofocusMode` / `Range` / `Speed` | | `:85-100` |
| `ProresColorProfile` | Standard, ArriLogC4, SonySLog3, DavinciIntermediate, P3D60Linear | `Apertar-Core/include/apertar/core/ProresColorProfile.hpp:8` |

- Wire strings (`toString`): `Types:240-337`, `ProresColorProfile.hpp:10-19`.
- `LossyDngRatio` uses `toWireValue`: "3to1" / "5to1" (`Types:271-274`).
- `ProresProfile::Standard` maps to "422" (`Types:280`).

### 4.2 Structs
- **`CaptureSettings`** (`Types:124-162`). Defaults: 3840×2160, 24 fps, ISO 800, 20833 µs, 5600 K, Cdng, 12-bit, AF continuous, window 0.25 / 0.25 / 0.5 / 0.5.
  - Runtime-only, never persisted: `exposureCompensationAvailable`, `exposureMeteringModes`, `timelapseExposureLimitUs`, `whiteBalanceAvailable`, `whiteBalanceMeasured`, `previewExposureReference`.
  - Helpers: `usesStillBracketing` (`:164-167`), `activeIspColorProfile` (`:169-176`), `timelapseExposureLimitUs` (`:178-182`).
- `AudioRecordingOptions` `Types:184-197`. `GyroRecordingOptions` `:199-201`. `RawFrameView` `:203-218`.
- **`RecordingCapabilities`** (`RC:11-16`): `rawCompression`, `prores`, `hardwareH264`, `rawRecording`.
  - Derived from devicetree `compatible` (`RC:18-50`). `brcm,bcm2712` (Pi 5) gives `{rawCompression=true, prores=true, hardwareH264=false, rawRecording=true}` (`RC:25-26`).
  - Legacy Pi boards get hardware H.264. `rawRecording` requires a non-legacy board or bcm2711 USB3 (`RC:34`).
  - Validation: `unsupportedRecordingSettings` `RC:64-77`. Coercion: `supportedRecordingSettings` `RC:79-106` (forces 1080p and ≤30 fps H.264 on hardware-H264 boards).
- `SharedUiSettingsSnapshot` (UI.conf model and defaults): `App:1580-1639`. Reader: `readSharedUiSettings` `App:1641-1813`.

### 4.3 Setting-change flow (example `set_iso`)
1. Client writes a line. `ControlServer::clientLoop` (`CS:236-269`) calls the handler, which is `ApertarCoreApp::handleRequest` (`App:7055`).
2. `parseControlCommand` (`CP:164`), then `collectingCommandEvents_ = true` (`App:7061-7065`).
3. `handleCommand` (`App:9091`) takes `commandMutex_` (`9093`) and calls `camera_.setIso` (`CC:7774`).
4. `applySettingsLocked` (`CC:8659-8723`):
   - Busy, capability and standby checks (`8666-8681`).
   - `session_->applyControls` or `reconfigure` (`8682-8710`; reconfigure on mode, ISP-profile or still-mode changes at `8661-8662`).
   - `settings_ = session_->currentSettings()` (`8713-8715`).
5. `persistSettingsLocked` (`CC:8725-8732`) runs `captureSettingsPersister().schedule(...)`. A background thread writes after a 25 ms debounce (`CC:793-889`, wait at `862-866`).
6. `emitSettingsEventLocked` (`CC:8777-8784`) calls `publishEvent` (`App:10823`). `settings` is on the always-broadcast list, so it goes to **all** clients immediately (`App:10829-10840`).
7. Reply `okReply(id, settingsBody)` (`App:9246-9248`) goes back to the requester, with collected non-exempt events appended (`App:7067-7080`).
8. Side channel: `handleTriggerEvent` drives the LED and trigger outputs (`App:10854-10889`).

**Multi-field changes:** `applyCapturePreset` (`CC:8604-8657`) applies everything at once with `commit=false`. It runs the UI.conf commit callback, then persists and emits. On UI-commit failure it reconfigures back to the previous settings (`8641-8656`).

**UI-only settings:** the command calls `updateSharedUiGeneralSettings` (`App:1850-1935`), which takes `QtIniLock` (`Apertar-Core/src/util/SettingsFile.hpp:59-118`, cooperating with Qt's `QLockFile` `<file>.lock`) and writes with `atomicWrite` (tmp + fsync + rename + dir fsync, `SettingsFile.hpp:36-56`).
- Core emits **no event** for these.
- The native UI's `SettingsBridge` watches the file with `QFileSystemWatcher` (`Apertar-UI/src/SettingsBridge.cpp:413-424`).
- The web page sees the change on its next 1 s poll.

### 4.4 Persisted state: where and by whom
| What | File | Read | Write |
|---|---|---|---|
| Camera capture settings: active, plus per-format profiles `profile.{cdng,mlv,h264,prores}.` and `profile.still.` (LossyDng shares the cdng profile, `CC:606-609`) | `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf`, else `$HOME/.config/apertar-core/camera_settings.conf` (`/home/pi/.config/...` for user pi), else `/tmp/apertar-core-camera_settings.conf` (`CC:342-353`) | `loadPersistedCaptureSettings` `CC:616-736`, called in ctor `CC:7598` | `writeCaptureSettings` `CC:738-778`; `persistCaptureSettingsNow` `CC:780-791`; scheduled from `CC:8725-8732` (also `start()` `CC:7646`) |
| Shared UI settings, `[General]` group | `$XDG_CONFIG_HOME/CinePi/UI.conf`, else `~/.config/CinePi/UI.conf`, else `/tmp/CinePi-UI.conf` (`App:341-348`) | `App:1641-1813`, `1815-1848` | `App:1850-1935`. The UI writes the same file via `QSettings("CinePi","UI")` (`CB:119`, `Apertar-UI/src/SettingsBridge.cpp:287`) |
| UI's own placeholder camera cache, `[camera]` group of the same `UI.conf` (`camera/hasSaved`, `camera/fps`, …) | same file | `CB:884-971` | `CB:973-1011`. Comment at `CB:886`: "Core owns restart/format restoration" |
| Hardware config, including the `[imu]` keys | `$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf`; read candidates also `/boot/firmware/apertar-hardware.conf` and `/boot/apertar-hardware.conf` (`App:4246-4276`) | per module | Web `POST /api/config` → `saveHardwareConfigFile` `App:5323-5386` (`.bak` copy + `.tmp` rename, no fsync); IMU commands → `Mpu6050RecordingSession.cpp:686-705` (`.tmp` rename) |
| Presets (`*.apertar-preset.json`) | `$XDG_DATA_HOME/Apertar-UI/presets`, `…/ApertarUI/presets`, `~/.local/share/Apertar-UI/presets`, `~/.local/share/ApertarUI/presets`, `~/.config/CinePi/UI/presets` (`App:5216-5242`; preferred dir `5244-5262`) | `discoverPresetFiles` `App:5408` | save `App:6699-6753` (`atomicWrite` at `6740`); import `App:6466+` (`atomicWrite` at `6509`); delete `App:6755-6777`; name rule `App:5157-5165` |
| Fan mode | `/boot/firmware/config.txt` managed block | `App:3104-3125` | `App:3127-3178` (`sudo -n install`) |
| Colour profiles | `/home/pi/apertar-color-profiles.conf` (`Apertar-Core/src/color/ColorProfileConfig.cpp:236`) | yes | write path UNCONFIRMED |
| Internal ProRes ISP tuning | `Apertar-Core/src/color/ProresIspProfile.cpp:233` (`atomicWrite`) | | |
| Default tuning files | `/home/pi/Tuning-Files/defaults-pisp|defaults-vc4` (`Apertar-Core/src/camera/DefaultTuningSelection.hpp:61-74`; `start-apertar-core.sh:13-18`) | | |

`defaultHardwareConfigPath()` returning `/home/pi/apertar-hardware.conf` is duplicated in **8 places**: `App:4248`, and `Apertar-Core/src/hardware/` `GpioInput.cpp:57`, `GroveAnalogInput.cpp:54`, `Mpu6050RecordingSession.cpp:188`, `NeoRotary4Input.cpp:70`, `Pcf8574Input.cpp:57`, `RecordingIndicatorOutput.cpp:67`, `TriggerOutput.cpp:70`. An embedded Python string at `App:3408` also names it.

---

## 5. Web server

### 5.1 Server (`WS`, header `Apertar-Core/src/web/WebServer.hpp`)
- **Address**: default bind `0.0.0.0`, port **8000** (`AppH:35-36`; CLI `main.cpp:64-82`; port 0 disables it, `App:6869`). IPv4 only (`WS:194`, `206`). `SO_REUSEADDR` (`WS:200-201`). Backlog 16 (`WS:220`).
- **Connections**: thread per connection (`WS:276-287`), max 32 (`WS:271`). `SO_SNDTIMEO` and `SO_RCVTIMEO` are 5 s (`WS:265-267`).
- **Requests**: 10 s request deadline (`WS:304`). Max 1 MiB (`WS:23`). `Transfer-Encoding` is rejected (`WS:332`). Duplicate `content-length`, `host` or `origin` headers → 400 (`WS:109`).
- **Responses**: always `Connection: close` and `Cache-Control: no-store` (`WS:127-140`). Streaming responses send headers without `Content-Length` (`WS:142-154`, `384-387`).
- **Auth: none.** The only gate is `allowedBrowserOrigin` (`WS:156-170`):
  - Reject `Sec-Fetch-Site: cross-site`.
  - No `Origin` header → allowed (CLI and native clients).
  - Otherwise `Origin` must equal `http://<Host>`. Failure → 403 (`WS:370-373`).
  - README warns against exposing port 8000 (`Apertar-Core/README.md:130`).
- `OPTIONS` → 204 with no CORS headers (`App:7095-7100`).
- The path is not percent-decoded, except for preset file names.

### 5.2 Routes (`handleWebRequest`, `App:7093-7649`)
| Method + path | Purpose | Lines |
|---|---|---|
| `OPTIONS *` | 204 | `App:7095` |
| `GET /`, `/index.html` | embedded SPA `webControlPageHtml()` (`WCP`, ~11.6k lines) | `App:7102` |
| `GET /preview.mjpeg` | `multipart/x-mixed-replace; boundary=frame`, streamed by `streamMjpeg` (503 if built without JPEG) | `App:7109-7122` |
| `GET /icons/<name>` | PNG from `src/web/icons` (search dirs `App:2420-2441`); rejects `/`, `\`, `..` | `App:7124-7152` |
| `GET /api/state` | `buildWebStateJson` | `App:7154` |
| `GET /api/media` | `buildMediaLibraryJson` | `App:7161` |
| `GET /api/config` | hardware config text and metadata | `App:7168` |
| `POST /api/config` | save hardware config (body = file text) | `App:7175-7195` |
| `GET /api/media/download?kind=folder|still&id=` | folder → streamed zip (needs `zip`, `App:6210`, `6215`); single still → file stream (`App:6193`); grouped still → zip | `App:7197-7316` |
| `GET /api/media/download-selected?item=<kind>:<id>&…` | zip of the selection (`App:5517-5548`) | `App:7318-7358` |
| `GET /api/presets` | list | `App:7360` |
| `GET /api/presets/download/<file>` | preset JSON as attachment | `App:7367-7390` |
| `POST /api/presets/import?name=`, `/api/presets/import/<name>`, or header `X-Preset-Filename` | body = preset JSON | `App:7392-7438` |
| `POST /api/presets/save?name=` | save current camera settings as a preset | `App:7440-7475` |
| `POST /api/presets/delete?file=` | delete a preset | `App:7477-7501` |
| `POST /api/media/delete?kind&id` | `remove_all` a folder or delete a still group; refused while recording or timelapse | `App:7503-7573` |
| `POST /api/media/delete-selected?item=…` | batch delete | `App:7575-7635` |
| `POST /api/command` | body = one command JSON → `handleWebCommand` → **the same `handleCommand` dispatcher** (no event collection) | `App:7637-7642`, `7085-7091` |
| anything else | 404 (GET/POST) or 405 | `App:7645-7649` |

### 5.3 MJPEG pipeline
- Constants: max 640×360, 30 fps, quality 75 (`App:60-63`).
- `updateWebPreviewRegistration` mmaps each preview DMA-BUF slot (`App:8048-8093`).
- `captureWebPreviewFrame` (`App:8095-8192`) runs **on the libcamera completion thread**, only while viewers are connected (`App:6950-6952`). It nearest-downsamples to I420 (`App:3999-4013`, `downsampleNearestPlane`).
- `runMjpegEncoder` encodes the latest pending frame (`App:8194-8236`).
- `streamMjpeg` sends `--frame` parts and counts viewers (`App:8262-8308`).

### 5.4 Web page client behaviour (`WCP`)
- Polls `GET /api/state` every **1 s** (`WCP:11609`, fetch at `10224`).
- Commands go through `sendCommand` (`WCP:9110-9145`): POST `/api/command`, then a re-poll after 80–140 ms.
- Activity pings `user_activity` throttled to 1 s (`WCP:11504-11515`).
- Preview: `<img src="/preview.mjpeg?stream=<nonce>">` (`WCP:8563`).
- Never sends: `set_tuning_file`, `set_capture_mode`, `get_state`, `preview_subscribe`, `get_media_test_state`, `ping`, `help`, `shutdown`, `set_imu_sync_offset`.

---

## 6. UI side: `ApertarControlBridge` and other socket users

### 6.1 Connection model
- **Persistent event socket** `m_eventSocket` (`QLocalSocket`), path from `$APERTAR_CONTROL_SOCKET`, default `/tmp/apertar-core.sock` (`CB:1557-1568`).
  - Set up in the constructor `CB:117-147`. Connected → clear error and `refreshFromCore` (`CB:123-127`). Disconnected or error → `setConnected(false)` (`CB:128-141`).
  - Used for events and `get_state` polling. `processEventSocketMessages` (`CB:1570-1589`) runs `applyCoreMessage` on every line, including every `preview_frame`, which is ignored.
- **Polling** (`m_retryTimer` calls `refreshFromCore`, `CB:143-146`):
  - 1000 ms while disconnected, 30000 ms steady state (`CB:17-18`, `875-882`).
  - `get_state` is sent async with an id. A 10 s timeout calls `m_eventSocket.abort()` (`CB:855-873`). Only one is in flight at a time (`CB:858`).
- **Commands use a NEW short-lived `QLocalSocket` per command** (`sendCoreCommand`, `CB:1013-1106`). This is **synchronous on the GUI thread**:
  - Connect timeout 350 ms (`CB:1015`), write wait 500 ms (`CB:1053`).
  - Reply timeout 3 s by default, 10 s for reconfigure-type commands (list at `CB:1016-1028`), 8 s for `calibrate_gyro`, **60 s for `record_stop`**.
  - Each received line goes through `applyCoreMessage` until the matching `id` arrives (`CB:1058-1092`).
- Reconnect: `ensureEventSocketConnected` is called from every poll (`CB:857`) and on command connect failure (`CB:1037`).
- **Two UI processes each create a bridge plus a preview client**: main UI `Apertar-UI/src/main.cpp:291`, `302`; monitor-only `runMonitorOnly` `Apertar-UI/src/main.cpp:130-135`. That makes at least 4 persistent Core clients, plus transient per-command sockets.

### 6.2 Commands sent by the UI (all repos)
- **`CB`**:
  - Exposure: `set_fps` 270 (followed by `set_shutter_us` 283, `CB:255-289`), `set_iso_auto` 294, `set_iso` 309, `set_shutter_auto` 321/351, `set_shutter_us` 339/368, `set_wb_auto` 384, `set_wb` 399
  - Format: `set_resolution` 417, `set_record_format` 457/528/535, `set_lossy_dng_ratio` 460/530, `set_prores_profile` 468/508, `set_prores_color_profile` 482, `set_cdng_preview_color_profile` 491, `set_cdng_compression` 537, `set_tuning_file` 565, `set_raw_bit_depth` 590, `set_h264_resolution` 610, `set_timecode_mode` 630
  - Autofocus: `set_af_mode` 646, `set_af_range` 662, `set_af_speed` 678, `set_af_window` 697
  - Still and capture: `set_photo_timelapse` 721, `set_photo_mode_enabled` 728, `set_capture_mode` 733, `set_photo_long_exposure_enabled` 738, `set_photo_bracketing_enabled` 745, `timelapse_start`/`timelapse_stop` 763, `record_start`/`record_stop` 810, `set_photo_bracketing_ev` 819, `capture_photo` 829, `calibrate_gyro` 835
  - Other: `get_state` 864, `set_exposure_compensation` 1110, `set_exposure_metering` 1115, `apply_preset` 1160 (keys built at `CB:1118-1150`), `enter_standby` 1168, `wake` 1173, `user_activity` 1179
- **`PSC:147`**: `preview_subscribe`.
- **`Apertar-UI/src/MediaStatusBridge.cpp`**: its own blocking helper `coreMediaCommand` (`:21-44`, fixed id 42001) sends `eject_media` (`:1183`, 60 s), `format_media` (`:1192`, 360 s), `run_media_speed_test` (`:1201`), `get_media_test_state` (`:1214`).
- **`Apertar-UI/src/AudioDeviceBridge.cpp:317-348`**: async `audio_capabilities` with `id` 1 and a 4 s timeout.
- Everything else (focus peaking, zebra, guides, battery, audio devices, volumes and so on) is written by the native UI **directly into UI.conf** through `SettingsBridge`/`QSettings`, not over the socket.
- UI-to-UI channel, not Core: `/tmp/apertar-ui-monitor-state.sock` (`Apertar-UI/src/ExternalMonitorRuntimeBridge.cpp:14-20`), set to `$RUNTIME_BASE/monitor-state.sock` (`Apertar-UI/run_pi_direct.sh:219`).

### 6.3 Messages the UI consumes (`CB:1182-1259`, `1261-1555`)
- Handled events: `photo_write_error`, `standby`, `still_exposure`, `timelapse_progress`, `media_write_state`, `audio_level`, `recording`, `recording_health`, `timelapse`, `timelapse_frame`, `photo_capture`, `prepare_recording`, `hardware_action`, `settings`. Any message containing `ok` is passed to `applyCoreState`.
- **Not handled**: `camera_state`.
- `applyCoreState` also reads `capture.sensor` (web-only shape) and `photo_timelapse` / `photo_format` (reply-only fields).

---

## 7. Ready, PID and status files
- **Core writes no ready, PID or status file.** A grep of `Apertar-Core/src` found none. The socket appearing after camera start is the only readiness signal (§1.1).
- Core **reads** these marker directories:
  - `/run/apertar-standby-low-power/settings` and `/run/apertar-standby-usb/ports`, used for crash recovery at start and stop and on wake (`App:6807-6819`, `6931-6940`, `9176-9187`).
  - They are created by the sudo helpers `/usr/local/libexec/apertar-standby-low-power` and `apertar-standby-usb` (invoked at `App:1541-1550`; built from `Apertar-UI/src/StandbyLowPower.cpp:17` and `Apertar-UI/src/StandbyUsbPower.cpp:23`, targets at `Apertar-UI/CMakeLists.txt:150-155`).
- **`Apertar-UI/wait_for_ui_core_start.sh`**:
  - Arguments: `READY_FILE` (default `/run/apertar-ui/core-start-ready`, `:5`) and `TIMEOUT` (default 8 s, `:6`).
  - Exits 0 immediately when no DRM connector is `connected` (`$APERTAR_DRM_SYSFS` or `/sys/class/drm/card*-*/status`, writeback ignored, `:21-33`), or when the file already exists (`:35-38`).
  - Otherwise polls every 25 ms until the deadline (`:40-52`). On timeout it **still exits 0** with a warning (`:54-56`). It never blocks failure, it only delays.
- **Who writes the file**:
  - UI `main.cpp:405-420` writes `ready\n` to `$APERTAR_CORE_START_READY_FILE` right after `Main.qml` loads.
  - Headless path: `Apertar-UI/run_pi_direct.sh:170-175` creates it immediately.
  - Separate UI first-frame marker: `$APERTAR_UI_READY_FILE` (`main.cpp:463-480`); default `${XDG_RUNTIME_DIR:-/tmp}/main-ui-ready` (`run_pi_direct.sh:79-81`, `220`); plus `headless-ready`.
- **Same script, other consumer**: `Apertar-UI/systemd/apertar-network-start-gate.conf:4` runs `ExecStartPre=-/usr/local/libexec/apertar-wait-ui-core-start /run/apertar-ui/main-ui-ready 8`, gating networking on the main-ui-ready marker.
  - `Apertar-UI/finish_plymouth_handoff.sh:5-28` waits for `main-ui-ready` or `headless-ready` (20 s), then runs `plymouth quit --retain-splash`.
- UNCONFIRMED:
  - The `apertar-core.service` unit is not in any of these repos (Core, UI, Beta, D1), so I could not confirm that it runs `ExecStartPre=…apertar-wait-ui-core-start /run/apertar-ui/core-start-ready`.
  - No repo script installs `wait_for_ui_core_start.sh` as `/usr/local/libexec/apertar-wait-ui-core-start`.

---

## 8. Bugs, inconsistencies, duplicate paths

### 8.1 Event collection
1. **Event collection is global, not per request** (`App:7061-7082`, `10842-10848`).
   - `collectingCommandEvents_` is set **before** `commandMutex_` is taken (`9093`). While client A's command runs, client B's `handleRequest` clears `pendingCommandEvents_`, deleting A's events. A then resets the flag, so B's events get broadcast instead.
   - Any asynchronous event from a camera thread during a command (`audio_level`, `timelapse_frame`, `photo_capture`, `timelapse`, `recording`) lands in the requester's reply instead of going to all clients.
2. **The `recording` and `timelapse` start/stop events are not on the always-broadcast list.** When the main UI starts recording over the socket, the event reaches only that UI's short-lived command socket.
   - Other clients (the HDMI monitor process, the main UI's own event socket) only learn on the next poll (up to 30 s).
   - Mitigation (UNCONFIRMED whether sufficient): the UI relays `recordingActive` over its own monitor-state socket (`Apertar-UI/src/ExternalMonitorRuntimeBridge.cpp:148-173`).
   - Web-initiated recordings are broadcast.

### 8.2 Socket and preview
3. **`preview_subscribe` broadcasts fds to all clients** (`App:10796-10799` → `6994-7019` → `10937-10938`). Every short-lived command socket and the bridge's event socket also receive SCM_RIGHTS fds they never read with `recvmsg`. The kernel discards them, but it is wasted dup/send work.
4. **`preview_frame` is broadcast to every client at full frame rate** (`App:10941`). Each bridge JSON-parses these lines on the GUI thread (`CB:1570-1589`).
   - Any client that does not drain its socket gets disconnected by the non-blocking send (`CS:25-29`).
5. **Long commands starve `get_state`.** `commandMutex_` serializes everything, including `format_media` (UI waits up to 360 s) and `record_stop`. The UI's async `get_state` times out after 10 s and **aborts the event socket** (`CB:867-872`). Likely shows "Timed out waiting for ApertarCore status" during long operations. UNCONFIRMED on hardware.
6. **The UI blocks the GUI thread** in `sendCoreCommand` with `waitForReadyRead` loops for up to 60 s on `record_stop` (`CB:1026`, `1058-1097`).
7. **The preview client ignores `APERTAR_CONTROL_SOCKET`.** It hardcodes `/tmp/apertar-core.sock` (`Apertar-UI/src/ApertarPreviewSocketClient.hpp:30`). The control bridge, media bridge and audio bridge honour the env var.
   - If Core runs on another `--socket` (`start-apertar-core.sh:6`), the preview breaks while control keeps working.
8. Dead UI path: `PSC:526-567` handles `preview_frame` with `fd_attached:true`, but Core only attaches fds to `preview_buffer` (`App:10913-10936`).

### 8.3 Help list and command surface
9. **The `help` list is stale.** It is missing 12 implemented commands: `apply_preset`, `audio_capabilities`, `enter_standby`, `get_media_test_state`, `help`, `ping`, `set_audio_capture_options`, `set_capture_mode`, `set_standby_timeout`, `set_standby_usb_power_off`, `user_activity`, `wake`. It lists 98 of the 110 (`App:9216`).
10. **The web exposes `shutdown`, `restart_system`, `power_off_system`, `format_media`, media delete and config overwrite with no authentication.** The only gate is the same-origin check (`WS:156-170`), and requests without an `Origin` header pass.

### 8.4 Inconsistent value handling
11. **`set_timecode_mode` accepts only the exact string `"rec_run"`**; anything else, including "Rec Run", becomes FreeRun (`App:9429`). `apply_preset` uses the lenient `normalizeTimecodeModeValue` (`App:380-386`, used at `10401-10405`). Both UI and web send `rec_run`/`free_run`, so it works today.
12. **Normalizers accept anything** for `set_ui_orientation` (→ Landscape), `set_camera_controls_mode` (→ Light) and `set_raw_bit_depth` numeric (16 → 12). There is no error (`App:362-371`, `388-392`, `9400-9401`).
    - Other `set_*` commands do reject, via `trimAscii(*value) != normalized`.
13. `apply_preset` has unreachable error paths. `addBoolUpdate` always returns true, so "Invalid preset bracketing toggle" never fires (`App:10232-10238`, `10287-10288`).
    - `standbyTimeoutSeconds` and the `*Order` keys are written without validation (`App:10514-10517`), unlike `set_standby_timeout`'s 0–86400 integer check.
14. The `apply_preset` reply puts an **object** in `"state"` (`App:10525-10526`), while `get_state` uses a string. The UI's `applyCoreState` treats `"state"` as a string for standby detection (`CB:1305-1308`). It evaluates to `standby=false`; harmless but inconsistent.
15. **The UI toggle commands reply with camera settingsBody, not the toggled value** (`App:9490`), and emit no event.

### 8.5 Web state errors
16. **`/api/state` `capture.codec` mislabels formats** (`App:7951-7955`). `LossyDng` falls through to "MLV RAW", and ProRes is always "ProRes 422" whatever the profile.
17. `/api/state` hardcodes defaults that ignore configuration:
    - `media_label` says "/media/RAW" even when `--media` differs (`App:7921`).
    - The battery-percent fallback `(V-10)/6.8` ignores the configured battery type and voltages (`App:7823`).
18. `/api/state` mixes sources (§3.3): `timecode_mode` twice from two sources, and `ui.photo_bracketing_ev` from camera settings.

### 8.6 Duplicated code
19. **Three hand-written copies of the settings serializer**: `settingsBody` (`App:167-216`), `settingsEvent` (`CC:136-191`), inline web state (`App:7856-7897`). Two `escapeJson` implementations (`CP:235`, `CC:95`).
20. **Duplicate persistence of camera settings**: Core's `camera_settings.conf` and the UI's `[camera]` group in UI.conf (`CB:973-1011`). The UI copy is labelled placeholder-only (`CB:886`) but is rewritten after every setter.
21. **`applyFps` in the UI sends `set_fps` and then `set_shutter_us`** (`CB:269-289`). The comment there claims Core's reply carries the old shutter time, but Core now preserves the angle itself (`CC:7768-7770`), so the second command is redundant (an extra round trip).

### 8.7 Concurrency gaps in the web handlers
22. **Several web handlers bypass `commandMutex_`**: media delete, delete-selected, config save, preset save and import (`App:7175-7635`). Media delete checks `isRecording()` but not `mediaWritesPending()` or a running speed test, unlike the socket media commands (`App:9098-9107`).
    - IMU writes and `/api/config` both use `<path>.tmp` (`Mpu6050RecordingSession.cpp:686`, `App:5374`) without a shared lock, so concurrent writes could collide.
23. `saveHardwareConfigFile` is not durable (no fsync, `App:5372-5384`), unlike `settingsFile::atomicWrite`.
24. The preset download `Content-Disposition` interpolates the decoded file name unescaped (`App:7382-7385`). `isSafePresetFileName` (`App:5157-5165`) does not forbid `"`, CR or LF. The file must already exist, so the risk is low.

### 8.8 Smaller items
25. The web icons search dirs reference `../ApertarCore/src/web/icons` (`App:2424-2429`), but the repo directory is `Apertar-Core`. It works only via cwd or the `exeDir/../src/web/icons` candidates. UNCONFIRMED on the image.
26. `/api/state` at 1 Hz per browser tab shells out to `lsblk` (`App:2284-2285`, `2054`) and runs `arecord -l` / `aplay -l` (cached 2 s, `App:2786-2803`).
    - `wait()` also re-reads UI.conf every second (`App:7037`).
27. **`ControlServer` refuses connections silently.** At the 32-client cap it closes the connection with no message (`CS:208-209`). A request line over 64 KiB is dropped and the connection closed, with no reply (`CS:261-262`).
28. `get_state` calls `stillExposureStatus()` twice (`App:9230-9231`). This is cosmetic, but the two values come from separate reads.
