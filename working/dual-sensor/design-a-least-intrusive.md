<!-- Dual sensor, design panel (2026-11-04), design a: lens "least-intrusive". One of three independent designs written read-only from r1-r5 and the code (Core 31d5418, UI c153c33, Cinemate d6cc93e) before the claim check was in. Judged in design-merged-v1.md. Frozen: do not edit; what was taken over is in design-dual-sensor.md and changes-from-critique.md. -->

# Dual sensor: design, least-intrusive lens (2026-11-04)

Two apertar-core processes: cam0 is the primary, cam1 the secondary. The primary stays the only door and forwards to cam1 (§2). Without a cam1 Core nothing changes.

Refs: unprefixed paths are Core @31d5418 (App = src/ApertarCoreApp.cpp, CC = src/camera/CameraController.cpp, WCP = src/web/WebControlPage.cpp); `U:` = Apertar-UI @c153c33; `M:` = cinemate @d6cc93e; r1-r5 are the reports beside this file (r5 wins over r4). Refs without a label are CONFIRMED.

## Re-checked claims (CONFIRMED)

1. The socket, the WebUI, hardware actions and idle standby all reach `handleCommand` (App:12173), at App:8299, 8322, 10083 and 8281.
2. A take's first frame is the first with `SensorTimestamp/1000 >= recordingStartBootUs_` (CC:9072). That value is set to "now" at CC:7631 and CC:7649.
3. "Recording" already covers more than cam0's camera. get_state, web state and the toggles use `isRecording() || soundRecording` (App:12503, 9272, 10547, 10555). The Sound Recorder publishes its own `recording` event (App:10033, 10045).

## 1. Architecture

| | Primary (cam0) | Secondary (cam1) |
| --- | --- | --- |
| Unit | `apertar-core.service`, unchanged | new `config/apertar-core-cam1.service` |
| Camera | first non-USB camera as today (CC:7262-7265); cam0 wins when two exist | `--camera cam1` |
| Socket | `/tmp/apertar-core.sock` | `/tmp/apertar-core-cam1.sock` via `APERTAR_SOCKET_PATH` (scripts/start-apertar-core.sh:6) |
| Web | :8000 | :8001 via `--web-port` (src/main.cpp:68): cam1's MJPEG; read-only |
| Config | ~/.config | `XDG_CONFIG_HOME=/home/pi/.config-cam1`: its own camera_settings.conf, mode_ladder.conf and UI.conf (CC:401-425, App:517-524) |
| Media | /media/RAW | the same; folder names end in `_cam1` |

- The new unit copies the live unit's limits and `LIBCAMERA_LOG_LEVELS` (r5). It adds `After=`, `PartOf=`, `WantedBy=apertar-core.service` and `RestartSec=5`. Its `ExecStartPre` waits until the primary's socket exists. The primary binds that socket only after its camera opens (App:8034, 8056).
- The start script gets `"$@"`, which is missing at scripts/start-apertar-core.sh:44. The unit then runs `start-apertar-core.sh --camera cam1 --web-port 8001` and keeps the script's tuning and RT logic.
- `--camera cam0|cam1` finds the port's I2C node through `/proc/device-tree/__symbols__/i2c_csi_dsi0|1`. Here cam1 is `rp1/i2c@70000` (r5); the same rule works on a Pi 5 (PROBABLE). Any other value is matched as a substring of the camera id.

**Role.** A Core started with `--camera` set to anything but `cam0` is a secondary. One flag turns these off on cam1:

| Off on cam1 | Site |
| --- | --- |
| trigger, PCF8574, NeoRotary4, GPIO, power button, Grove, tally, controls worker; INA219 and IMU reads | App:8080-8096, 8125, 9302, 9663 |
| trim and pre-roll threads; idle standby | App:8006, 8010, 8269-8281 |
| commands outside the allowlist (§2); all web commands on :8001 | top of `handleCommand` |
| audio, gyro and sound-only in `record_start` | App:14216 |

**No cam1.**
- If the unit is not enabled, nothing runs.
- If it is enabled but no sensor sits on cam1, the secondary checks sysfs before libcamera starts. It finds no subdev whose `of_node` lies under the port's I2C node, logs one line and exits 0. `Restart=on-failure` does not restart it.
- No second CameraManager ever touches cam0 (r4). The primary and the UI find no cam1 socket.

## 2. Control path

**Mechanism: the primary forwards to cam1's socket** through a new `src/ipc/ControlClient`, the client half of `ControlServer`. Why: every input already meets in the primary's `handleCommand` (claim 1), so one hook covers all of them and no client changes.

ControlClient:
- connects while the cam1 socket exists, checking each second, and never to its own socket (compared by inode);
- drains cam1's broadcasts;
- polls `get_state` each second;
- sends a queue of commands and matches the replies by id.

`handleCommand` becomes a wrapper around the old body. No lock is held across a socket write.

| Runs on | Commands (App:12496) | Primary | cam1 |
| --- | --- | --- | --- |
| both | `set_iso(_auto)`, `set_exposure_*`, `set_fps`, `set_shutter_*`, `set_wb(_auto)`, `set_resolution`, `set_record_format`, `set_cdng_*`, `set_lossy_dng_ratio`, `set_prores_*`, `set_tuning_file`, `set_raw_bit_depth`, `set_clear_hdr`, `set_hdr_*`, `set_h264_resolution`, `set_timecode_mode`, `set_conform_fps`, `set_clip_name_template`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_af_*`, `set_buffer_mode`, `set_mode_ladder`, `apply_preset`, `enter_standby`, `wake` | applies, then forwards | applies |
| both, coordinated | `record_start`, `record_stop` | chooses the cameras, T and the name (§4) | records |
| each its own | `get_state`, `ping`, `help`, `list_*`, `get_mode_ladder`, `preview_subscribe`, `preview_clip_name`, `user_activity` | answers | answers |
| primary only | the rest: UI.conf keys, media, power, system, stills, timelapse, audio, IMU, hardware | as today | refuses: "cam1: send this to the primary" |

One list serves as both the forward list and cam1's allowlist. A new command therefore stays refused on cam1 until someone adds it.

**Resync** is `set_mode_ladder` plus an `apply_preset` built from the primary's `camera*` fields (App:7674-7905, 13721-14090).
- It is sent while no take runs, after any of: the link (re)connects, cam1 refuses a command, or a forwarded `set_record_format` or `apply_preset` (each Core restores its own per-format values, CC:11214-11232).
- `apply_preset` is refused during takes (CC:12487-12490), so a resync waits for the take to end. cam1 never joins a running take.

**cam1's state.**
- HDMI: a second preview client and a second control bridge read cam1's socket (§3).
- WebUI: the primary's `/api/state` gains `cam1`, which is cam1's last `get_state` reply as is. It is absent when cam1 is not linked.
- The browser cannot fetch from :8001 itself: Core answers 403 to a foreign Origin (src/web/WebServer.cpp:159-173, 373-376). An `<img>` still works.

| Refused by | Result |
| --- | --- |
| primary | as today; nothing is forwarded |
| cam1 | the reply stays ok; log `ApertarCore cam1 refused <cmd>: <error>`; resync when idle; "≠ CAM0" shows while fps or resolution differ |
| link down | resync on reconnect |

## 3. Display

**Setting.** It copies the `externalMonitorMode` quartet (App:863, 1871, 2042, 9617, 12496, 13267; U:src/SettingsBridge.hpp:48, .cpp:361, 548, 1074-1091; WCP:5272, 15502, 15560, 20328):
- UI.conf `previewSource` = `Cam 0` (default) | `Cam 1` | `Both` | `PiP Cam 0` | `PiP Cam 1`;
- command `set_preview_source`, state `ui.preview_source`;
- not in presets in v1.

**cam1 live** means the second client's `frameCounter` (U:src/ApertarPreviewSocketClient.hpp:21) moved in the last second. A 500 ms QML timer checks it. Until cam1 is live, every source shows as `Cam 0`, plus a "CAM 1 · NO SIGNAL" chip when another source is set.

**HDMI.** There is a second `CameraPreviewItem` beside `preview` (U:qml/ExternalMonitorWindow.qml:403-428) and a second renderer (U:src/ExternalMonitorManager.cpp:231-238). Renderers draw in connection order, and `render()` ignores visibility (U:src/PreviewWindowRenderer.cpp:2388-2440). So the second item always draws on top, and an item is hidden by giving it size 0.

| Source | `preview` (with aids) | `preview1` (passthrough) |
| --- | --- | --- |
| Cam 0, Cam 1 | full screen, that camera | 0×0 |
| Both | left half, cam0 | right half, cam1; 4 px divider |
| PiP Cam 0 | full screen, cam0 | lower right, 0.28 of the width, margin 0.03, cam1 |
| PiP Cam 1 | full screen, cam1 | same inset, cam0 |

- Switching source swaps the bridges (one cache rebuild, PROBABLE).
- Guides hide in `Both`. The HUD stays as it is.
- One CAM1 chip follows the DroppedFrameWarning pattern (U:qml/ExternalMonitorWindow.qml:1181-1185). It shows REC or READY, drops, NO SIGNAL and "≠ CAM0" from `apertarControlBridge1`.

**WebUI.**
- `<img id="previewStream1">` loads `http://<host>:8001/preview.mjpeg?stream=<n>` only while a source needs it (stop pattern WCP:12047-12053). CSS places it for each source.
- Aids stay on cam0's image, because a cross-origin image taints the canvas (r3).
- Badges read `snapshot.cam1`. NO SIGNAL also shows on `img.onerror`.
- The read-only "Preview source" row (WCP:5229-5231) becomes a select while `cam1` exists.

## 4. Recording

**Policy** (same quartet): UI.conf `recordCameras` = `Both` (default) | `Follow Preview`; command `set_record_cameras`; state `ui.record_cameras`. The WebUI select shows only while cam1 is linked.

**Override:** a `record_start` field `cameras=cam0|cam1|both`.

**Which cameras record**, as in Cinemate (M:src/module/cinepi_controller.py:2244):
- the override, if given;
- else both, if the policy is `Both`;
- else the main camera of the effective source (both for `Both`).

cam1 drops out when it is not linked or not Ready. A cam1-only take is then refused.

| Item | Rule |
| --- | --- |
| Start | the primary picks T = now + lead (500 ms at first, then measured), half a period off the frame grid. It sends cam1 `record_start start_us=T clip_name=<name>`, then starts itself. Both set `recordingStartBootUs_ = T` (CC:7631, 7649), so CC:9072 keeps the first frame ≥ T. A late start is logged in frames. A `start_us` sent to the primary sets T |
| Names | cam0 as today (src/util/ClipName.hpp:23). cam1's name is the template rendered with `{cam}` = cam1 (CC:1148), plus `_cam1` when the template has no `{cam}`. The clip number skips N when cam1's folder N exists (CC:1189-1192) |
| cam1-only take | the primary speaks for the take, as it does for the Sound Recorder: it publishes `recording` with `folder` (App:10033 pattern). `recording` = camera, sound or cam1 (App:12503, 9272, 10547, 10555). The tally follows |
| Stop | forward to cam1 first, then stop locally |
| Refusal | cam0's gates refuse first (App:12196-12231). If cam0 fails after cam1 was told, cam1 gets `record_stop`. If cam1 refuses, cam0 records, a line is logged and the chip stays READY. cam0's buffer safety stop is a `record_stop` (App:11038-11042), so it stops cam1 too and the takes stay paired |
| Audio | cam0 only, as today; none for cam1-only takes |
| Timecode | `timecode_mode` is mirrored. FreeRun is each frame's wall time through the Core's own `recordingClock_` (CC:7520, 9263). It matches unless a TC frame edge falls between the two exposures (risk 4). RecRun matches when both start on the same frame |
| Time left | web: free space ÷ (rate × cameras) (App:9376-9384); HDMI REMAINING is halved while linked (approximate) |
| Drops | counted per Core: the HUD for cam0; for cam1 the CAM1 chip, `cam1.recording_dropped_frames` and `journalctl -u apertar-core-cam1` |

## 5. Sync slot

Both Cores run `stepFramePhaseLock` (CC:8773-8861, called at CC:9047), because `fps_phase_lock` is a mirrored camera setting. Both read SensorTimestamp on the same kernel's CLOCK_BOOTTIME (src/camera/FramePhaseLock.hpp:21-24). Today each lock takes its datum from its own first frame (:95-100, 143-153). Two locked Cores therefore keep a constant skew of up to one frame (r2). The servo team chooses the grid, A or B below.

| Servo needs | Given |
| --- | --- |
| both Cores locked | `set_fps_phase_lock` is forwarded; `cameraFpsPhaseLock` is in the resync |
| one period | fps is mirrored, including a `set_fps` during a take (speed ramp) |
| one origin | A: origin 0 on BOOTTIME, grid at k·period, no message. B: the primary adds `origin_ns` to a forwarded `set_fps_phase_lock` after each re-arm (+1 field) |
| start rule | `start_us` = T, picked by the primary half a period off the grid; both Cores apply the CC:9072 test |
| fps and shutter together | forwarded within milliseconds and merged at each Core's next requeue (CC:8863-8873), so within one frame (PROBABLE). Changing on the same frame would need an `at_us` field |
| telemetry | `fps_phase_lock_*` (App:9426-9430) in both `/api/state` |
| watch | the preview re-arm when the error exceeds half a frame (FramePhaseLock.hpp:112-117) works against a shared grid |

## 6. Steps

| Step | Changes (files) | Check | 1 sensor | Size |
| --- | --- | --- | --- | --- |
| T55 | `--camera`; pick the camera by port (CC:7063-7066, 7262-7265), cam0 first; `openImx585Subdev` matches `of_node` as CC:8118-8130 does, at its four callers; sysfs pre-check, skipped with `--simulate` (main.cpp, App.hpp, App.cpp, CC.cpp, CC.hpp) | journal names `i2c@88000`; a take and the Clear HDR toggle work as before; `--camera cam1` exits 0 with one line and the primary is undisturbed | yes | 65 lines, 2.5 h |
| T56 | role gates, allowlist, `{cam}`, `clip_name`, `_cam1` (App.cpp, CC.cpp); unit file; `"$@"` in the script | with the primary stopped, `--camera i2c@88000` runs a secondary on cam0: no driver lines, `format_media` refused, `_cam1` folder, no WAV, tally dark | yes | 100 lines, 3 h |
| T57 | ControlClient (new .hpp and .cpp), wrapper, resync, `cam1` in web state (App.hpp, App.cpp, CMakeLists.txt) | the primary plus `XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_SOCKET_PATH=/tmp/apertar-core-cam1.sock start-apertar-core.sh --simulate --camera cam1 --web-port 8001`: WebUI changes reach cam1's `get_state` within 1 s; restarting cam1 triggers a resync; `/api/state` has `cam1`; a symlink to the primary's socket is not linked | yes | 210 lines, 6 h |
| T58 | take coordination, `recordCameras` quartet, the three fields, T, cam1-only takes, stop, number skip, time left (App.cpp, CC.cpp, CC.hpp, WCP) | without cam1: as before. With the simulated cam1: policy, override, cam1-only take. On the real cam0: `start_us` = uptime + 1 s gives a first frame ≥ T and < T + 1 period | yes | 185 lines, 6 h |
| T59 | `previewSource` quartet; UI: socket-path constructor for the bridge, second client, second bridge, second renderer (App.cpp, WCP; U: main.cpp, ApertarControlBridge.hpp/.cpp, ExternalMonitorManager.hpp/.cpp, SettingsBridge.hpp/.cpp) | the select round-trips; the UI journal stays quiet without cam1 | yes | 120 lines, 4 h |
| T60 | layouts, fallback, CAM1 chip, REMAINING (ExternalMonitorWindow.qml) | with `/tmp/apertar-core-cam1.sock` symlinked to the primary's socket: all five layouts; remove the link: fallback within 1 s; a 3-min 4K HDR16 take in `Both` and in `Cam 0` drops the same | yes | 150 lines, 5 h |
| T61 | WebUI layouts, badges, selects shown only while linked (WCP) | T57's simulated cam1: select, badges, CSS, NO SIGNAL | yes, but no cam1 picture | 140 lines, 4 h |
| T62 | second IMX585: overlay line, r5's checks, M1, M2; timing re-write if M2 shows it is needed (CC.cpp) | journal line `Registered camera ... i2c@70000 ... /dev/media3`; cam0's frame duration unchanged after cam1 starts | no | 0-30 lines, 3 h |
| T63 | acceptance, fixes only | M5 order; first frames ≥ T on both; TC; WAV; drops per camera | no | 20 lines, 4 h |
| T64 (optional, last) | second item on CameraPage, two Settings rows (CameraPage.qml, SettingsPage.qml) | cannot be tried | no | 120 lines, 4 h |

**Totals for T55-T63**

| Measure | Count |
| --- | --- |
| Files | 19: Core 11, of which 3 new (ControlClient.hpp, ControlClient.cpp, apertar-core-cam1.service); UI 8. T64 adds 2 |
| New names | 12: `--camera`, the unit, `previewSource`, `set_preview_source`, `ui.preview_source`, `recordCameras`, `set_record_cameras`, `ui.record_cameras`, the `record_start` fields `cameras`, `start_us` and `clip_name`, the state field `cam1`. Option B adds `origin_ns` |
| Conventions, not names | cam1 socket path, port 8001, `.config-cam1` |
| New env vars | none |
| Lines and time | about 990-1,020 lines, 37.5 h; T64 adds 120 lines and 4 h |

## 7. Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| 1 | Bandwidth: 2× 4K SDR12 is likely to drop frames; 2× 4K HDR16 is infeasible (r4) | 2× 1080p first, then 4K lossless + 1080p; aids off on cam1; M1, M4, M5 |
| 2 | cam1's CameraManager start rewrites cam0's HBLANK and flips at every boot (r4; M2 tests it) | cam1 starts only when its sensor is present; on link connect the primary re-writes its own timing through its subdev (CC:8135 pattern, UNCONFIRMED) |
| 3 | Settings drift between the Cores | one command list, the resync triggers, "≠ CAM0", T57 |
| 4 | Takes one frame apart: a late start, or a TC frame edge between the exposures (each Core has its own `recordingClock_`, CC:7520) | T half a period off the grid; lateness logged; phase lock; T63 compares first frames and TC |
| 5 | A primary-only path runs in cam1 | allowlist and role gates; T56 journal check |
| 6 | UI cost: a second render, and every client gets every `preview_frame` line | passthrough on `preview1`; the second bridge drops `preview_frame` lines before parsing; T60 A/B |
| 7 | The driver's mode table is process-wide (r4) | identical overlay parameters; Clear HDR mirrored and refused during takes |
| 8 | One exFAT NVMe for two writers; identical DNG camera tags | `_cam1` folders; M4; a per-camera serial tag later |

## 8. Questions for Patrik

| # | Question | Default |
| --- | --- | --- |
| 1 | What should the record policy default be? | `Both` |
| 2 | Store labels or tokens in UI.conf? | labels, with tokens also accepted |
| 3 | What happens when cam1 fails mid-take on its own? | cam0 keeps recording; cam0's safety stop still stops both |
| 4 | Audio for cam1-only takes? | none in v1 |
| 5 | Any way to override per take besides the socket field? | the field only; a WebUI "next take" select later |
| 6 | Link frequency on both overlays? | cam0's 891 MHz; 720 MHz if M1 shows CSI errors (r4) |
| 7 | Align the stops to one frame? | not in v1 |
| 8 | A quick source switch (live-view pills, a hardware action)? | later |