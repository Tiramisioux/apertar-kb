<!-- Dual sensor, design panel (2026-11-04), design b: lens "operator-first". One of three independent designs written read-only from r1-r5 and the code (Core 31d5418, UI c153c33, Cinemate d6cc93e) before the claim check was in. Judged in design-merged-v1.md. Frozen: do not edit; what was taken over is in design-dual-sensor.md and changes-from-critique.md. -->

# Dual sensor on Apertar: design, operator first

2026-11-04. Built on r1-r5 (`~/Documents/Apertar/apertar-kb/working/dual-sensor/`). Read-only; nothing ran on the Pi. Every `path:line` is at Core `31d5418`, UI `c153c33` or libcamera `6b0b49f3`. `App`, `CC` and `WCP` are as in `llm/README.md`; `EMW` = `qml/ExternalMonitorWindow.qml`; `CB` = `src/ApertarControlBridge.cpp`. An unmarked ref was opened tonight (CONFIRMED). **(rN)** means reader N opened it.

## 0. Three claims re-checked

| Claim | Result |
|---|---|
| One hook in the primary sees every command, and Core has no outbound client | CONFIRMED. The socket (App:8287-8299), the WebUI (App:8317-8323) and the buttons (App:10078-10087) all call `handleCommand` (App:12173). Core only has listening sockets (ControlServer.cpp:108, WebServer.cpp:197) |
| "First frame with SensorTimestamp ≥ T" is already the record gate | CONFIRMED. CC:9064-9084 tests `timestamp/1000 >= recordingStartBootUs_` and also needs a frame duration within max(500 µs, 2 %). T is set to "now" at CC:7631 and CC:7649 |
| The :8000 page can show :8001's MJPEG in an `<img>`, but it cannot fetch from :8001 | CONFIRMED in code. `allowedBrowserOrigin` (WebServer.cpp:159-173) lets a request with no `Origin` through unless `Sec-Fetch-Site` is `cross-site`. Anything else gets a 403 (:373-376). That the same host on another port counts as same-site is PROBABLE |

## 1. Architecture

| | Primary | Secondary |
|---|---|---|
| Unit | `apertar-core.service`, unchanged | new `config/apertar-core-cam1.service`, same start script |
| Camera | cam0. With no env set it prefers `i2c@88000`, else today's rule | `APERTAR_CAMERA=cam1`: that port or nothing |
| Socket | `/tmp/apertar-core.sock` | `/tmp/apertar-core-cam1.sock` (`APERTAR_SOCKET_PATH`, start-apertar-core.sh:6) |
| Web | :8000 | :8001 (`APERTAR_WEB_PORT`, one new forward at start-apertar-core.sh:44) |
| Config | `~/.config` | `XDG_CONFIG_HOME=/home/pi/.config-cam1` |
| Media | `/media/RAW` | the same card |

- **The role follows the port.** `APERTAR_CAMERA=cam1` makes a Core the secondary.
  - It skips hardware inputs, the controls worker, tally, trigger, the power button, idle standby, pre-roll, trim, audio, the IMU, the INA219 and the CFE hat.
  - It refuses media, boot, time, fan, restart and power commands (r2's lists).
- **Primary-only duties**: everything in the list above. The primary also runs the relay, picks T and the clip names, publishes the `cam1` state block and does resync.
- **"cam1 configured"** means config.txt has a camera overlay on cam1. The primary reads this at start with `parseDocument` and `portOf` (BootConfigText.hpp:315, 381). This is the "Camera 1 sensor" field in the WebUI Boot config card, so no new key is needed.
- **Not configured**: no relay, no `cam1` block, nothing new on either screen, and the cam1 unit stays disabled. The rig works as it does today.
- **Configured but the camera is missing**: the secondary tries the camera once. Then it stays up in Error and shows the reason.
  - Today Core exits in this case (App:8034-8040).
  - A restart loop would re-run libcamera's sensor init each time, and that init also writes to cam0's sensor (risk 1).
- **Unit settings**:
  - `After=apertar-core.service`, `Restart=on-failure`, `RestartSec=5`.
  - r5's drop-ins.
  - An `ExecStartPre` that waits while cam0 records (a copy of `wait_for_ui_core_start.sh`).

## 2. Control path

**The primary relays.** Every entry point already ends in the primary's `handleCommand`. One hook there covers the WebUI, the UI and the buttons, and both UIs keep talking to one Core.

- A new `src/ipc/PeerClient.{hpp,cpp}`:
  - It does an AF_UNIX connect, sends one line, reads until the reply with our `id`, and times out.
  - It has its own thread and queue, so `commandMutex_` never waits on IO. The one exception is the bounded start wait in §4.
- `handleCommand` becomes a wrapper. It runs today's body. If the reply is `"ok":true` and the command is in the "both" class, it sends the same fields to cam1. cam0 validates and cam1 follows.

| Class | Commands |
|---|---|
| Both, sent after cam0 accepts | every camera setter (exposure, WB, fps, resolution, format, bit depth, HDR, cDNG/ProRes/H.264 options, tuning, timecode, conform, buffer mode, phase lock, speed ramp, AF, ladder), `apply_preset`, `enter_standby`, `wake` |
| Both, coordinated (§4) | `record_start`, `record_stop` |
| Primary only | UI.conf keys (aids, monitor, `previewSource`, `recordBothEnabled`, audio), photo, timelapse, clip template, media, boot, time, fan, restart, power, IMU, controls |
| Secondary only | none. The relay itself sends `get_state` every second and `apply_preset` to resync |

- **cam1's state reaches both screens through the primary.**
  - The relay's 1 s `get_state` poll (App:12498-12530) fills `"cam1":{"state","message","dropped_frames"}` in the primary's `get_state` and `/api/state`.
  - It also fills `"record_cams"`: the cameras the running take records, or the next take will record.
- **`state` is the word the screens print**: `offline`, `not_found`, `ready`, `idle` (not in the next take), `recording`, `writing`, `refused`, `lost` or `standby`.
  - Neither QML nor JS works it out for itself, so the HDMI screen and the WebUI cannot disagree.
- **How the UI gets it**:
  - The UI bridge polls `get_state` every 1 s while `cam1` exists. It already does this for auto ISO/WB (CB:16-19, 1010-1017). No new event is needed.
  - The UI opens cam1's socket only for frames, through a second `ApertarPreviewSocketClient`. Its path argument already exists (`.hpp:31`).
- **Resync**:
  - When cam1 answers again and nothing is recording, the relay sends `apply_preset` built by `buildCurrentPresetPayload` (App:7674, r2). `apply_preset` takes inline fields (App:13721).
  - Each poll also compares the mirrored values, leaving out values in auto. A difference sets `message` (for example "Settings differ: fps") and triggers one resync when idle.
  - So edits made on the :8001 page do not stick.
- **cam1 refuses a mirrored setting**: cam0 keeps the new value. The WebUI shows the toast "CAM1: <reason>", and the CAM1 pill stays amber until a resync matches.
- **Dual-aware gates in the primary**:
  - Media actions (App:12219-12221), standby (App:12256) and setters that reconfigure the camera are refused while cam1 records or writes.
  - `capture` and `record_toggle` (App:10531-10559) stop the take if either camera records.
  - Tally and trigger light when either camera records.

**API delta, complete**

| Kind | Added |
|---|---|
| Commands | `set_preview_source`, `set_record_both_enabled`; optional `cams`, `start_us` and `clip_name` on `record_start` |
| State | `cam1{state,message,dropped_frames}`, `record_cams`, `ui.preview_source`, `ui.record_both_enabled` |
| Settings | UI.conf `previewSource`, `recordBothEnabled` |
| Env | `APERTAR_CAMERA`, `APERTAR_WEB_PORT`, `APERTAR_DUAL_START_LEAD_MS`; test-only `APERTAR_CAM1_PREVIEW_SOCKET` (UI) |

## 3. Display

| Place | Preview source | Record policy |
|---|---|---|
| UI.conf | `previewSource`: `Both` (default), `CAM0`, `CAM1`, `PiP CAM0`, `PiP CAM1`. The normaliser also accepts `both, cam0, cam1, pip_cam0, pip_cam1` | `recordBothEnabled`: `false` = follow the preview (default) |
| Command | `set_preview_source`, a copy of App:13267-13278 | `set_record_both_enabled` through `handleUiToggle` (App:12886, as App:13058) |
| State | `ui.preview_source` (beside App:9617) | `ui.record_both_enabled` |
| WebUI | pill row under the preview; Live preview card row (WCP:5229-5232) | toggle in the External monitor card (WCP:5270-5278) |

- The default `Both` avoids Cinemate's trap: with `cam0` and follow-the-preview, it records cam0 only (r1 Q1).
- One setting drives both screens. With follow-the-preview, a preview press also picks the next take's cameras, and the REC label shows the change at once.

**HDMI** (EMW, 1920x1080; the inset is 536x302, lower right, with margins of 58/32 px):

| Mode | Picture | When cam1 has had no frame for 1 s, or is offline |
|---|---|---|
| CAM0 | as today | as today |
| CAM1 | cam1 full screen | cam0 full screen + amber banner "CAM1 NO SIGNAL · SHOWING CAM0" |
| Both | two 960x540 panes, 2 px white frames, HUD in the black bands | right pane black, "CAM1 NO SIGNAL" |
| PiP CAM0 | cam0 full screen, cam1 inset | cam0 full screen, no inset |
| PiP CAM1 | cam1 full screen, cam0 inset | as CAM1 |

- Every pane has a `CAM0` or `CAM1` tag. A recording camera's pane gets the existing red recording frame (EMW:1434).
- Aids, guides and the centre marker show on the main pane only (r3 Q2, cost).
- The HUD keeps showing cam0's values, since settings are mirrored.
- A CAM1 pill sits beside the status pill (EMW:1086). It shows `CAM1 <STATE>` and cam1's dropped frames.
  - Red: recording.
  - Amber: anything wrong. It blinks while a take that wants cam1 runs without it.
  - White: ready. Grey: idle.
- In PiP, REMAINING (EMW:1219-1285) moves above the inset.

```
Both (not to scale)                     PiP CAM0
+----------------------------------+    +----------------------------------+
| 25 FPS  ISO 800  180  5600K      |    | 25 FPS  ISO 800  180  5600K      |
|+---------------++---------------+|    |CAM0                              |
||CAM0           ||CAM1           ||    |            cam0, aids            |
||   cam0, aids  ||   cam1        ||    |                    REMAINING x2  |
||   red = REC   ||   red = REC   ||    |                    41 MIN        |
|+---------------++---------------+|    |                    +-----------+ |
|      [REC 0]  [CAM1 REC 0]       |    |  [REC 0][CAM1 REC] |CAM1  cam1 | |
| RESOLUTION  10:42:31:07  REMAIN. |    | RES  10:42:31:07   +-----------+ |
| 3856x2180               x2 41 MIN|    +----------------------------------+
+----------------------------------+
```

**WebUI**:
- A second `<img>` loads `http://<location.hostname>:8001/preview.mjpeg?stream=n`, with no `crossorigin`. Its `src` is removed while it is hidden, so cam1 encodes nothing (App:9735).
- Layouts:
  - Both: side by side, or stacked when the page is narrower than 700 px.
  - PiP: a 28 % inset with 3 % margins.
- Aids show on cam0 only, because a cross-origin image taints WebGL (r3 Q6).
- Tags, outlines, pill colours and NO SIGNAL work as on HDMI.
- The REC button names what one press records: "REC BOTH", "REC CAM0" or "REC CAM1 · NO AUDIO". It shows "STOP" while either camera records.

## 4. Recording

For each press, the override wins. If there is none, "always both" applies. Otherwise the effective preview (after any fallback) decides. Only cameras that answer are asked. Photo, timelapse and speed-ramp takes are cam0 only in v1 (Q5).

| Effective preview | follow preview | always both |
|---|---|---|
| Both | cam0 + cam1 | cam0 + cam1 |
| CAM0, PiP CAM0 | cam0 | cam0 + cam1 |
| CAM1, PiP CAM1 | cam1 | cam0 + cam1 |

- **Per-take override**: `record_start {"cams":"cam0|cam1|both"}`.
  - The WebUI shows "NEXT TAKE: AUTO · CAM0 · CAM1 · BOTH" beside REC. It goes back to AUTO after the stop.
  - Hardware buttons always follow the policy.
- **Start**:
  - The primary picks T = now + L (BOOTTIME µs) and the folder name N, and starts cam0 with both.
  - Only if that works does the relay send `record_start {"start_us":T,"clip_name":"N_cam1"}`. The primary waits up to L for the reply.
  - A cam1-only take asks cam1 alone.
  - `start_us` replaces "now" at CC:7631/7649. cam1 has no audio, so it skips the 220 ms sleep (App:14297-14300).
  - A side that is ready only after T starts on its next good frame and logs `late_frames`. The message then reads, for example, "CAM1 started 2 frames late".
- REC and tally light at the press. The first frame comes about L later (measured in T58; PROBABLE 0.5-0.8 s).
- **Names**:
  - cam0 is named as today (`{format}_{date}_{clip}`, ClipName.hpp:23).
  - cam1 is cam0's name + `_cam1`, for example `cDNG_26-11-04_C0007_cam1`.
  - A clip number counts as taken if either name exists (CC:1182-1196).
  - An exclusive `create_directory` replaces `create_directories` (CC:7544).
  - `{cam}` gives the port (CC:1148).
  - The DNG model and serial tags are the same on both cameras (CC:3805-3841, r2), so only the name tells the clips apart.
- **Audio**: there is one WAV, cam0's. It is trimmed to cam0's frame 0 (r2), which is also cam1's frame 0 when both run on one grid. cam1-only takes have no audio in v1.
- **Timecode**: FreeRun (the default) is each frame's wall time from one kernel clock (CC:9261-9265, r2), so it is equal on both. RecRun counts from frame 0 at T, so it is equal when both start on time.
- **Time left**: free space / (n × one camera's data rate), with n taken from `record_cams` (App:9376-9386; MediaStatusBridge.cpp:381-383, r3). It shows as "REMAINING x2 41 MIN".
- **Stop**:
  - `record_stop` goes to cam1 first, then cam0 stops.
  - Nothing waits for cam1 to finish writing; its pill shows WRITING meanwhile.
  - The last frames should be about one frame apart (PROBABLE).
- **Dropped frames**: cam0's chip works as today (EMW:1181-1186). cam1's count shows in its pill and in the WebUI chip.

| Situation | What Patrik sees (HDMI and WebUI) | What one REC press does |
|---|---|---|
| cam1 not configured | today's screens | records cam0, as today |
| configured, camera not found | amber `CAM1 NOT FOUND`; cam1 views fall back to cam0 | records cam0; the pill blinks if the policy wanted cam1 |
| cam1 Core crashed or restarting | amber `CAM1 OFFLINE`; views fall back | records cam0, as above. cam1 restarts after the take |
| cam1 refuses REC | amber `CAM1 REFUSED` and Core's reason until the stop; a WebUI toast | cam0 rolls; the next press stops it. cam1 never joins mid-take |
| cam1 lost mid-take | amber `CAM1 LOST` and the reason; cam1's frames so far stay on the card | cam0 keeps rolling |
| cam0 refuses | one error, as today | nothing starts |
| card nearly full | REMAINING x2 counts down | under 1 GiB free each Core refuses to start (App:11337-11341), cam0 first. If the card fills mid-take (ENOSPC), each writer stops cleanly (MediaFault.hpp:18) |

## 5. Sync slot

Both Cores run their own `FramePhaseLock`. This design gives the servo one clock, the same fps on both, a relay for extra fields and the start rule. The grid can be derived with no messages: origin 0 on CLOCK_BOOTTIME and period 1e9/fps. Or the primary can add `origin_ns` to the mirrored `set_fps_phase_lock`. The servo team chooses.

| Need | What this design gives |
|---|---|
| The lock runs in both | `set_fps_phase_lock` is mirrored; `stepFramePhaseLock` (CC:8773) is unchanged |
| One clock | SensorTimestamp = CLOCK_BOOTTIME (FramePhaseLock.hpp:21-24) |
| One period | `set_fps` is mirrored and compared every second |
| Start | `start_us` = T, chosen by the primary, in both; gate at CC:9064-9084 (T58, T61) |
| fps and shutter change together | relayed at once; each Core merges the change at its next requeue (CC:8871-8873), so within 1-2 frames. An `at_us` field built like `start_us` can be added if exact timing is needed |
| Telemetry | `fps_phase_lock_err_us` and related fields per Core (App:9426-9430); cam1's on :8001 |
| Limits to respect | the ±150 µs clamp (FramePhaseLock.hpp:39); the preview re-arm above half a frame (:110-117), which would drop a shared origin; the lock is off in photo mode and during the ramp grace (CC:8789-8790); the start gate's cadence check (CC:9073) |

## 6. Steps

One commit per step on the local Pi branch. Patrik runs every sudo, restart and take.

| T | Change (files) | Check that proves it | Testable with 1 sensor | Size |
|---|---|---|---|---|
| T55 | Camera by port: `APERTAR_CAMERA` at the pick and the probe (CC:7254-7265, 7062-7067). The IMX585 subdev is found by `of_node` (CC:6875-6960, 7039; pattern CC:8114-8150; r2). `{cam}` gives the port. The secondary's skips. Core | With no env, the camera id and takes are as before. A hand-run cam1 Core says "No camera on cam1", and its journal has no GPIO, I2C or ALSA lines | yes | 150 lines, 5 h |
| T56 | The secondary stays up when its camera fails; the unit; `APERTAR_WEB_PORT`; the wait script. Core | :8001 shows Error. Stomp test: during a cam0 take, start and stop the hand-run cam1 Core 10 times. The take's frame intervals show what each start costs (r4 M2) | yes | 60 lines, 3 h |
| T57 | `clip_name`, shared numbering, exclusive mkdir. Core | Names are as before. A hand-made `_C0004_cam1` folder makes the next take C0005 | yes | 40 lines, 2 h |
| T58 | `start_us` through to CC:7631/7649, plus a `late_frames` log. Core | Takes sent with `curl` at T = now + 800 ms: the first frame falls in [T, T + one period). The audio-sync log is unchanged. 10 takes give L | yes | 30 lines, 3 h |
| T59 | PeerClient, the wrapper, the mirror list, the poll, the `cam1` block, the compare and resync. Core | With Boot config Camera 1 = IMX585 and no sensor attached: `not_found`, and cam0 is unchanged (UNCONFIRMED: shared regulator, r5). Then a hand-run cam1 with `--simulate` (src/main.cpp:52-55, opens no camera): setters reach :8001 within 1 s; stopping it gives `offline` within 2 s; starting it again gives a resync, then `ready` | yes | 250 lines, 7 h |
| T60 | Both setting quartets: Core, UI `SettingsBridge`, WebUI, presets | Values survive restarts. UI.conf, `ui.*` and both screens agree | yes | 150 lines, 4 h |
| T61 | Dual record: the camera choice, the override, T and N, refused/lost, the gates, tally, time left × n. Core, WebUI REC label | With the `--simulate` cam1: REC BOTH gives :8001 `recording:true`. Killing it mid-take: cam0 keeps rolling and cam1 shows `lost`. Format is refused. REMAINING halves | yes | 180 lines, 6 h |
| T62 | WebUI layouts, tags, NO SIGNAL, the CAM1 chip, NEXT TAKE. WCP | `?cam1port=8000` (a JS-only test hook) puts cam0 in both panes, so all five modes can be checked on a laptop and a phone | yes | 200 lines, 5 h |
| T63 | The cam1 preview client, `hasFrame` + a watchdog, an `isVisible()` guard, a second renderer (ExternalMonitorManager.cpp:231-235), `cam1` in the bridge. UI | `APERTAR_CAM1_PREVIEW_SOCKET=/tmp/apertar-core.sock` feeds cam0 into the cam1 slot. 3-min 4K takes with two renderers drop no more frames than the baseline | yes | 150 lines, 5 h |
| T64 | EMW layouts, frames, tags, the pill, banners, the REMAINING move | With the same hook, every mode matches §3. Removing the hook shows the fallbacks | yes | 250 lines, 6 h |
| T65 | Second IMX585 (Patrik): cable, Boot config with cam0's link frequency, reboot, enable the unit | r5's list: `imx585` on `i2c-0`, a second `rp1-cfe`, "Registered camera …i2c@70000…". `scan_i2c` (App:12100) shows no change. Stomp test with two sensors | no | 0 lines, 3 h |
| T66 | Acceptance with the servo on: r4 M5 (2×1080p, 2×4K lossless, 2×4K uncompressed), 3 takes each | Per-camera drops, frame-0 offset and timecode in a KB table | no | 0 lines, 4 h |
| T67 | Optional, last: CameraPage copies EMW | Builds with no QML warnings; cannot be tried (no touch screen) | build only | 200 lines, 4 h |

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | libcamera's sensor init writes flips and HBLANK (camera_sensor_legacy.cpp:205-222, 284-298) on every sensor a manager start enumerates (r4). So one Core's start or reconfigure can cost the other camera's take some frames (UNCONFIRMED) | cam1 opens its camera once and restarts only between cam0 takes. Reconfiguring setters are refused while either camera records. T56 measures it |
| 2 | The camera pick takes the first non-USB camera, else `front()` (CC:7254-7265), so a cam1 Core could take cam0 | Exact port with no fallback (T55); the primary prefers `i2c@88000` |
| 3 | 2×4K uncompressed is about the 4K50 load that drops 12-18 %, and 2×4K HDR16 is infeasible (r4 Q5). Each Core also sizes its RAM buffers without knowing about the other (r2 Q1) | Per-camera drops on screen; frames buffer mode on both; the T66 ladder starts at 2×1080p |
| 4 | A take silently records only one camera | A blinking amber pill until the take ends; the REC label names its cameras |
| 5 | Media actions and record toggles see only their own process (App:12219-12221, 10531-10559) | Dual-aware gates (T61); cam1 refuses media commands (T55) |
| 6 | Settings drift: a refused mirror, an edit on :8001, a stale file after a restart | The 1 s compare, an amber pill, resync |
| 7 | The driver keeps one mutable mode table for both sensors (r4 Q4) | The same `link-frequency` on both overlay lines (T65) |
| 8 | A second import and renderer on the basic render loop (r3 Q2) | The second pane gets no aids; T63 measures the cost first |

## 8. Questions for Patrik

| # | Question | My default |
|---|---|---|
| 1 | If cam1 refuses or dies at REC, should cam0 roll alone? | Yes, with the blinking pill |
| 2 | Keep cam0's clip names unchanged and name cam1's as cam0's + `_cam1`? | Yes |
| 3 | v1 mirrors all settings, so both cameras run the same resolution. Do you need 4K + 1080p soon? | No; per-camera resolution comes later |
| 4 | Is it OK that cam1-only takes have no WAV in v1? | Yes, labelled on the REC button |
| 5 | Photo, timelapse and speed ramp: cam0 only in v1? | Yes; the REC label says CAM0 |
| 6 | Both overlays at 891 MHz as today, or at 720 MHz? (r4: 891 is above the D-PHY's 1500 Mbps/lane) | 891; switch to 720 if cam1 logs CSI errors |
| 7 | Default preview source `Both`? | Yes |
| 8 | Show aids on the second pane too? | No |