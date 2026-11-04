<!-- Dual sensor, design panel (2026-11-04): the judge's scores of designs a, b, c, the merged design v1 (base a, with b's operator layer and c's risk layer, and the claim-check fixes), and where the designs disagreed. Critiqued in critique-merged-v1.md. Frozen: do not edit; what was taken over is in design-dual-sensor.md and changes-from-critique.md. -->

## 1. Scores

| Criterion | LI | OF | RF |
| --- | --- | --- | --- |
| (a) Apertar consistency, API economy | **4**: fewest names (12, no env var), and `ControlClient` sits beside ControlServer. But it mirrors buffer mode and the clip template, uses an enum for a two-way policy, and its `"$@"` breaks the script's env-to-flag pattern (scripts/start-apertar-core.sh:6, 44@31d5418) | **3**: `PeerClient` has no src/ipc precedent; adds `APERTAR_DUAL_START_LEAD_MS`, a test-only env var and the field `cams` | **3**: adds `APERTAR_ROLE`/`--secondary`, two helper scripts, a dead-man meaning on `ping` (App:12330@31d5418) and the field `clip` |
| (b) Intrusiveness | **5**: about 1,000 lines in 19 files, the smallest | **3**: about 1,660 lines, plus a camera-less Error mode inside Core | **2**: about 1,700 lines, a 400-line UI step, and a conditional driver and libcamera patch |
| (c) Operator clarity, WebUI + HDMI | **3**: no WebUI override or REC label; REMAINING stays under the inset (EMW:1218-1224@c153c33); Both falls back to cam0 full screen, which hides a dead cam1 | **5**: state words, REC label, NEXT TAKE, a red frame per pane, REMAINING moved, a table per situation | **3**: chip words and Next-take pills, but little HDMI layout detail |
| (d) Risk to takes | **2**: cam1 may run a second RAM queue; no reconfigure gate while cam1 records; setters reach cam1 during takes it sits out; gates blind to cam1; the secondary can restart into a take | **3**: cam1-aware gates and a wait while cam0 records. But "try the camera once" with no sensor is a manager start (claim-check L2), it mirrors buffer mode, and a cam0-first start needs a longer lead | **5**: measures first, refuses reconfigures while either camera records, waits for primary idle, keeps cam1 on frames, uses ExecCondition |
| (e) Testable now with one sensor | **5**: every software step runs with a `--simulate` cam1, a socket symlink and the `--camera` role trick | **4**: most steps run, but its T59 needs a cam1 overlay with no sensor and a reboot (effect of the shared regulator UNCONFIRMED) | **4**: measurements and a role swap run, but its M2 at 25 fps would read "harmless" (claim-check L-new2), and `APERTAR_SENSOR_PROBE=0` is untried |
| (f) Completeness | **3**: misses overlapping takes, cam1-aware gates, cam1's buffer mode and an orphaned cam1 take | **4**: the fullest operator flows; thin on platform measurements and crash cases | **4**: platform items and crash drills; thin on layouts and names |
| Total | 22 | 22 | 21 |

Base: **LI**. It ties OF on points and leads on (a) and (b), which decision 4 ranks first. OF's operator layer and RF's risk layer fill LI's gaps in (c), (d) and (f), and the API grows only to 12 names plus two script env vars.

## 2. Merged design: dual sensor on Apertar, T55 onward

Base LI, plus OF's operator layer, RF's risk layer and the claim-check fixes. Refs: Core `31d5418`, UI `c153c33`, Cinemate `d6cc93e`. App = `src/ApertarCoreApp.cpp`, CC = `src/camera/CameraController.cpp`, WCP = `src/web/WebControlPage.cpp`, CB = `src/ApertarControlBridge.cpp`, EMW = `qml/ExternalMonitorWindow.qml`, PWR = `src/PreviewWindowRenderer.cpp`. Every ref was read tonight and is CONFIRMED unless labelled. "Claim-check X7" = finding X7 of the claim-check report.

**Re-checked tonight: the three claims the design leans on most**

| Claim | Evidence | Label |
| --- | --- | --- |
| One hook sees every command | `handleCommand` has four callers: idle standby App:8281, socket 8299, WebUI 8322, hardware 10083; body 12173, lock 12182; no recursion (@31d5418) | CONFIRMED |
| Start-at-T changes one value | both record paths set `recordingStartBootUs_` to now (CC:7631, 7649@31d5418); the gate passes the first frame with `timestamp/1000 >= recordingStartBootUs_` and a cadence match (CC:9072-9073@31d5418) | CONFIRMED |
| The Sound Recorder already models "the rig records, the camera does not" | `recording = camera \|\| sound` (App:9272, 12503); REC toggles (10546, 10555); `recording` event with `folder` (10033-10034); tally from it (14465-14472) (@31d5418) | CONFIRMED |

### 1. Architecture

Two processes, one binary, one start script.

| | Primary | Secondary |
| --- | --- | --- |
| Role and camera | cam0: `--camera` absent or `cam0` | cam1: any other `--camera`, here `APERTAR_CAMERA=cam1`; no role flag |
| Socket, web | `/tmp/apertar-core.sock`, :8000 | `/tmp/apertar-core-cam1.sock`, :8001, reads and MJPEG only |
| UI.conf, hardware file | as today | its own: `.config-cam1`; buffer frames, IMU and INA219 off |

**Start options.** The script maps env vars to flags (scripts/start-apertar-core.sh:6, 44@31d5418). Two more vars copy that pattern:

```
ARGS=(--socket "$SOCKET_PATH" --media "$MEDIA_ROOT")
[[ -n "${APERTAR_CAMERA:-}" ]] && ARGS+=(--camera "$APERTAR_CAMERA")
[[ -n "${APERTAR_WEB_PORT:-}" ]] && ARGS+=(--web-port "$APERTAR_WEB_PORT")
exec ${PREFIX[@]+"${PREFIX[@]}"} "$CORE_BIN" "${ARGS[@]}"
```

`--web-port` exists (src/main.cpp:32-37@31d5418); `--camera` is new. Without the env vars the command line is the same as today.

**Camera pick.** `cam0`/`cam1` resolve through `/proc/device-tree/__symbols__/i2c_csi_dsi0|1` to `rp1/i2c@88000|70000`, which is part of the camera id (r5, CONFIRMED on the Pi). Any other value is matched as a substring of the id, so `--camera i2c@88000` runs a secondary on cam0's sensor. The primary prefers cam0, else today's rule (CC:7262-7265@31d5418). The secondary takes its own port or exits; it never falls back to `front()`. The probe's camera pick changes the same way (CC:7063-7066).

**Subdevs by of_node.** WDR, the HDR knobs and the probe take the first sensor subdev they find (CC:6875-6892@31d5418). Bind them by of_node, as CC:8124-8130 already does. Otherwise the second Core writes WDR to cam0 and fails with EBUSY (claim-check C4, C-new1).

**No sensor on cam1.** Before any libcamera call, the secondary looks in sysfs for a sensor on its port. If there is none, it logs once and exits 0. Today a failed camera start ends Core with exit 1 (App:8034-8040, src/main.cpp:108-111@31d5418), and `Restart=on-failure` would loop on that. `--simulate` skips the check.

**"cam1 configured".** The primary links to cam1 only when config.txt names a cam1 sensor (`cameras["cam1"].sensor != "none"`, src/hardware/BootConfigText.hpp:474-480, 512-540@31d5418) or the cam1 socket exists (for tests). Otherwise there is no link, no `cam1` field and no UI change, so the rig behaves exactly as today. If the two overlay lines have different link frequencies, the mismatch goes into `cam1.message` (claim-check D1b).

**Start order.** Before camera start, the secondary reads the primary's get_state and waits while it shows `"recording":true`. No primary socket means no take. Each CameraManager start writes HBLANK=min on every sensor, which costs a running take one frame at min_hmax and a phase step (claim-check L2, X7). A Core start runs 3-5 managers (claim-check L6).

**Unit** `apertar-core-cam1.service` (UNCONFIRMED: built from r5's summary of the live unit; `PartOf` untried). It is the live unit without the wait-ui `ExecStartPre`, which exits at once when there is no screen (wait_for_ui_core_start.sh:30-33@c153c33). It adds these lines (the two `=0` switches turn pre-roll and trim off, claim-check C7):

```
After=apertar-core.service
PartOf=apertar-core.service
Environment=APERTAR_CAMERA=cam1 APERTAR_SOCKET_PATH=/tmp/apertar-core-cam1.sock APERTAR_WEB_PORT=8001
Environment=XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf
Environment=APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0
SyslogIdentifier=apertar-core-cam1
```

**Role gate.** On the secondary, start skips the trigger, inputs, power button and tally (App:8080-8101@31d5418) and the controls worker (8124-8125). It keeps the hardware-file adopt and `refreshBufferRequest()` (8104-8122). Standby skips the machine-wide low-power and USB steps (12270-12287). The secondary has no audio and no IMU.

### 2. Control path

**Relay.** New `src/ipc/ControlClient.{hpp,cpp}`, the client twin of ControlServer, running on its own thread with a FIFO.
- cam1's server sends every line to every client (src/ipc/ControlServer.cpp:175-196@31d5418), and each `preview_subscribe` re-sends the buffer fds (App:14395-14397).
- So the client reads all the time, matches replies by id, closes the fds it receives, and skips every event except `recording`.
- It never takes `commandMutex_` and refuses to link to the primary's own socket (same inode).
- It polls get_state every second.
- Commands sent while cam1 is offline are dropped; the resync on relink catches up.

**Hook.** Today's `handleCommand` body is renamed `handleCommandLocal`. A wrapper keeps the old name, so the four callers do not change. After a local ok, the wrapper queues "both" commands for cam1. record_start and record_stop coordinate inside their own branches (§4). The only wait under `commandMutex_` is a cam1-only record_start, at most 1 s, like the 220 ms audio sleep (App:14297-14300). The relay never takes that lock.

**Command classes**

| Class | Commands |
| --- | --- |
| Both: forwarded after the primary's ok | ISO, shutter, WB, exposure; fps; resolution; format and codec options; tuning; bit depth; Clear HDR and its knobs; h264 resolution; timecode mode; conform fps; phase lock; speed ramp; AF; mode ladder; apply_preset (flattened); enter_standby; wake |
| Primary only | UI.conf keys; audio; photo; timelapse; clip template; buffer mode; media; boot; time; fan; power; IMU; controls; pre-roll; user_activity |

**Take-state rules**

| State | Primary accepts | Sent to cam1 |
| --- | --- | --- |
| Idle | as today | every "both" command |
| Both record | as today; each Core's take gates refuse reconfigures (CC:10514-10520, 10561-10600, 11196, 11490-11495, 11759-11766, 12484-12490@31d5418) | every "both" command |
| cam0 only | as today | nothing during the take; one resync after it (CC:10588-10590) |
| cam1 busy, cam0 not recording | only reads, `set_iso*`, `set_shutter_*`, `set_wb*`, `set_exposure_*`, display keys, record_stop, user_activity; anything else gets "CAM1 is recording." | the exposure setters |

**Busy checks.** A new `cam1RecordingActive()` copies `soundRecordingActive()` (App:9971-9974@31d5418) and joins it at every site where the rig counts as busy:
- tally (8100, 11965)
- idle standby (8271)
- web gates (8983, 9065)
- state (9272, 12503)
- REC toggles (10546, 10555)
- pre-roll (11087), playback (11304), trim (11432)
- `recordingGateActive()` (11879)

The media gate (12212-12221) and standby (12263) also refuse while cam1 has writes pending (`media_writes_pending` in cam1's get_state, 12498-12531).

**State.** Two new fields, in both get_state and /api/state:
- `cam1` = `{state, message, recording_dropped_frames}`. It is absent when cam1 is not configured.
- `record_cameras` = `cam0`, `cam1` or `both`, for the running take, else for the next take.

| `cam1.state` | Meaning |
| --- | --- |
| `offline` | no link |
| `ready` | in the next take |
| `idle` | sits out the next take |
| `recording` | in the running take |
| `writing` | writes pending |
| `refused` | `message` says why |
| `lost` | left a running take: link down, or its own buffer safety stop (App:11038-11042@31d5418) |
| `standby` | in standby |

**Compare and resync.**
- Each poll compares fps, resolution, recording_format, raw bit depth, clear_hdr, and ISO, shutter and WB unless they are auto (settingsBody, App:298-352@31d5418).
- A difference, a (re)link, or the end of a take cam1 sat out triggers one resync, only while both cameras are idle.
- The resync is one flattened apply_preset of the primary's state (presets nest under `settings`), without the clip template, audio and gyro keys. It adds `set_mode_ladder`, which presets lack (claim-check R5). apply_preset already carries `cameraFpsPhaseLock` and `cameraTimecodeMode` (App:13891-13893).
- Compare the resulting state, not the commands sent (claim-check R4): a format switch loads that format's saved profile (CC:11213-11239@31d5418).

**Orphan stop.** If cam1 records while the primary has no take that includes it (after a relink, or after a cam0 fault), the primary sends record_stop.

**Secondary allowlist.**
- Accepted: "both" commands, record_start, record_stop, get_state, ping (App:12330), list_sensor_modes (12333), help (12495), get_mode_ladder (13635), preview_subscribe (14395).
- Anything else gets "cam1 takes commands from the primary."
- :8001 refuses web commands.

**API delta: 12 names, plus two script env vars**

| Kind | New | Copies |
| --- | --- | --- |
| UI.conf | `previewSource`: "Cam 0", "Cam 1", "Both", "PiP Cam 0", "PiP Cam 1"; default Both; strict labels; not in presets in v1 | externalMonitorMode (App:863-869, 1871, 2042-2043, 13267-13278@31d5418) |
| UI.conf | `recordBothCamerasEnabled`, default false | `recordAudioEnabled` (App:2086-2087) |
| Commands | `set_preview_source`, `set_record_both_cameras_enabled` | `set_external_monitor_mode`, `handleUiToggle` (App:12886-12899) |
| State | `ui.preview_source`, `ui.record_both_cameras_enabled`, `cam1`, `record_cameras` | `ui.external_monitor_mode` (App:9617), `ui.record_audio_enabled` (9637) |
| record_start | `cameras`, `start_us`, `clip_name` | `audio_enabled` (App:14228-14233), `preview_clip_name` (12803) |
| Option | `--camera`; env `APERTAR_CAMERA`, `APERTAR_WEB_PORT` | `--socket`, `APERTAR_SOCKET_PATH` |

### 3. Display

**HDMI: EMW**

| Piece | Change |
| --- | --- |
| Preview client | one more `ApertarPreviewSocketClient` (src/main.cpp:291@c153c33) on the explicit cam1 path (ApertarPreviewSocketClient.hpp:31), only while `cam1` exists. The standby wiring (main.cpp:335-350, EMW:321-330) passes the path too, because a bare `connectToCore()` means cam0 (claim-check U2). If its `frameCounter` (hpp:21) is unchanged for 1 s, cam1 has no signal |
| cam1 state | no second control bridge (claim-check U9). CB polls at 1 s while `cam1` exists (CB:1010-1017) and parses `cam1` and `record_cameras` (beside CB:1730-1731) |
| Second item | `externalPreviewItem1` beside EMW:404-428. Its renderer is made in `ensureWindow` after the first (src/ExternalMonitorManager.cpp:231-235), so it survives the rebuild on wake (claim-check U6) and draws on top (PROBABLE) |
| Renderer, one line each | `render()` returns early for a hidden item: today only `scheduleWindowUpdate` checks visibility (PWR:347), yet `render()` imports at 2407. `syncState` sets `m_resetPreviewState` when the bridge changes (410-426); otherwise a swap keeps the old frame (2410-2412) |

**Layouts at 1920×1080**

| Source | Main pane, with aids | Second pane, clean, on top |
| --- | --- | --- |
| Cam 0 | cam0 full screen (today) | hidden |
| Cam 1 | cam1 full screen, CAM1 tag | hidden |
| Both | cam0, left 960×540 | cam1, right 960×540 |
| PiP Cam 0 | cam0 full screen | cam1 inset 538×302, lower right, margins 58/32 px |
| PiP Cam 1 | cam1 full screen (bridges swapped) | cam0 inset |

- The inset is 0.28 of the width. Its height follows the frame's aspect (claim-check U-new6).
- Insets and Both panes get 2 px white frames. Both adds a 4 px divider and pane tags, and turns off guides, centre marker and level.
- No cam1 frame:
  - Cam 1 and PiP Cam 1 show cam0 with an amber "CAM1 NO SIGNAL · SHOWING CAM0".
  - PiP Cam 0 drops the inset.
  - Both keeps a black right pane reading "CAM1 NO SIGNAL", as Cinemate does (r1).
- In PiP, REMAINING moves above the inset (EMW:1218-1224@c153c33).
- Each pane's frame turns red while its camera records (today there is one frame, EMW:1427-1435).
- A CAM1 pill sits by the status pill (EMW:1085-1090), copied from DroppedFrameWarning (EMW:1181-1186). Colours: red recording; amber offline, refused, lost or no signal; white ready; grey idle.
- The HUD keeps cam0's values.

**WebUI: WCP**

- `<img id="previewStream1">` loads `http://<location.hostname>:8001/preview.mjpeg?stream=n` without `crossorigin`. It drops its src while hidden (WCP:12047-12053@31d5418), since MJPEG encodes only while someone views it (App:9735).
- An `<img>` sends no Origin header, so it passes the origin check (src/web/WebServer.cpp:159-173@31d5418; browser side PROBABLE).
- A fetch to :8001 gets 403 (373-376), and a cross-origin image taints canvases. So cam1 state comes from `snapshot.cam1` on :8000, and aids stay on cam0.
- CSS layouts per source. The read-only "Preview source" row (WCP:5229-5232) becomes a select while `cam1` exists.
- "Record both cameras" pills sit beside Record Audio (WCP:5477, 16163-16169).
- Next to REC, NEXT TAKE pills (Auto, CAM0, CAM1, Both) send `cameras` with this page's REC press and reset after the stop.
- The REC label names what one press records ("REC CAM0 + CAM1"). A CAM1 badge shows `snapshot.cam1`.
- Test hook: `?cam1port=8000` (JS only).

### 4. Recording

**Which cameras.** First match wins:
1. `cameras` on record_start.
2. `recordBothCamerasEnabled`: both.
3. The effective preview: Both gives both; Cam 0 and PiP Cam 0 give cam0; Cam 1 and PiP Cam 1 give cam1. Cam1 modes count as Cam 0 while cam1 is not ready.

A cam1 that is not ready is dropped from the take. An explicit `cameras` that names it is refused.

**Start.** This runs in the record_start branch, after the gates (App:12196-12231@31d5418) and before the audio sleep (14297):

1. T = CLOCK_BOOTTIME now + lead (500 ms until T55 measures it). T is set after the primary's trim wait (App:12225-12228), and cam1 has no trim. The lead covers the audio sleep and both start paths (claim-check R1).
2. A new CC helper renders both names from one clip number, the lowest number free under both names (CC:1182-1197; exists lambda 1190-1193).
   - If the template has `{cam}`, cam1's name uses `{cam}`=`cam1` (today `v.cam = "cam0"`, CC:1148).
   - Otherwise cam1's name is cam0's name + `_cam1`. The default template `{format}_{date}_{clip}` has no `{cam}` (src/util/ClipName.hpp:23@31d5418).
3. The relay sends cam1 `record_start start_us=T clip_name=N1 audio_enabled=false gyro_enabled=false sound_only=false`, without waiting for the reply.
4. cam0 starts with T and its name N0 (App:14302).
5. Both Cores set `recordingStartBootUs_ = T` (CC:7631, 7649). When `clip_name` is given, the folder is made with an exclusive `create_directory` instead of `create_directories` (CC:7544).
6. Each Core logs T and its first frame. A start later than T + one period is logged in frames (claim-check R2).

**Failures**

- cam0 fails after cam1 was told: cam1 gets record_stop. An empty cam1 folder may remain.
- cam1 refuses: state `refused` with the reason. cam0 keeps rolling, and cam1 never joins mid-take.
- cam1's link is lost: state `lost`. cam0 keeps rolling; the orphan stop runs on relink.
- cam0's buffer safety stop stops both cameras, because it runs `handleCommand("record_stop")` (App:11038-11042@31d5418).
- cam1's buffer safety stop stops cam1 only (state `lost`, with its reason).

**cam1-only take.** This follows the Sound Recorder pattern. The primary waits up to 1 s for cam1's reply, then publishes `recording` with `active:true` and `folder` (as at App:10033-10034). The tally follows that event (14465-14472). `recording` becomes true when the camera, the Sound Recorder or cam1 records. No audio in v1.

**Stop.** record_stop goes to cam1 first, without waiting, then the primary stops locally (App:14382-14387). The two takes end one relay latency apart (claim-check R-new1). In a cam1-only take, the primary publishes `active:false` at once, as `stopSoundRecording` does (App:10045).

**Timecode.** `set_timecode_mode` is a "both" command. FreeRun timecode matches on both cameras unless a TC bin edge falls between the two first exposures (claim-check R3, PROBABLE). A time-zone change needs both Cores restarted (claim-check R-new5).

**Time left and drops.**
- The web divides time left by the camera count in `record_cameras` (App:9376-9385, 9553).
- The HDMI multiplies the data rate by the camera count (`m_frameSizeMB * m_fps`, src/MediaStatusBridge.cpp:383@c153c33). Without this, REMAINING reads about 2× too long (claim-check U12).
- cam1's drops show in the CAM1 pill, in `cam1.recording_dropped_frames` and in `journalctl -u apertar-core-cam1`.

### 5. Sync slot

Both Cores run their own FramePhaseLock (CC:8773-8861@31d5418) on one grid. Option A puts the grid origin at 0 on CLOCK_BOOTTIME, which both processes read: no message is needed, and the grid survives restarts (claim-check R-new4, X-new3). In option B, the primary sends `origin_ns` with set_fps_phase_lock. `start_us` is the start rule (CC:9072-9073). set_fps reaches cam1 within milliseconds, and each Core merges it at its next requeue (CC:8863-8873); an optional `at_us` field could pin both to the same frame. Limits the servo must respect:
- clamp ±150 µs (src/camera/FramePhaseLock.hpp:39);
- re-arms (:95, :110-117) and `arm()` (:149) must land on the grid;
- the lock stays off until its pushes change VMAX only (claim-check X9);
- a 2-frame actuator delay (D2b);
- 250-350 frames of pull-in (X-new2);
- a push larger than max(500 µs, period/50) during the first-frame wait delays the start (CC:9073).

| Interface | Where | Owner | Status |
| --- | --- | --- | --- |
| `start_us` on record_start | CC:7631, 7649 | this design, T59 | new |
| `fps_phase_lock` on both Cores | "both" class; preset `cameraFpsPhaseLock` (App:13891-13892) | this design, T58 | exists |
| Grid origin | `arm()`, FramePhaseLock.hpp:143-153 | servo team | change |
| `origin_ns` (option B only) | `set_fps_phase_lock`, App:12759 | servo team | new |
| `at_us` on set_fps (optional) | CC:10561-10600 | servo team | new |
| Lock telemetry on the socket | today in /api/state only (App:9426-9430); add to get_state | servo team | add |
| cam1 frame times | `preview_frame` `timestamp_us` (App:14513), already read by the relay | this design | free |

### 6. Steps from T55

| Step | Files | Check | 1 sensor | Size |
| --- | --- | --- | --- | --- |
| T55 measure | none; Patrik runs it | r4 M2 at 24 fps (at 25 fps HBLANK is already minimal, claim-check L-new2); a stray Core start during a take; 4K50 takes as a two-camera load proxy; fio at a second writer's rate during a take; record_start latency ×10; Core memory | yes | 0 lines, 3 h |
| T56 camera by port | src/main.cpp, App.hpp, CC.cpp/.hpp, start script | with no env: the same "Registered camera" line, take and Clear HDR as before. `APERTAR_CAMERA=cam1` exits 0 in under 1 s, before libcamera loads; cam0 undisturbed | yes | 80 lines, 3 h |
| T57 secondary role | App.cpp/.hpp; cam1 unit and hardware file (new) | primary stopped, `--camera i2c@88000`: no trigger, GPIO, PCF or power-button lines; the "controls:" line names the cam1 file (App:8114-8116@31d5418); format_media and :8001 POSTs refused; MJPEG works | yes | 110 lines, 3.5 h |
| T58 relay | src/ipc/ControlClient.hpp/.cpp (new), App.cpp/.hpp, CMakeLists.txt | `--simulate --camera cam1` run by hand (simulate accepts takes, CC:11847-11857@31d5418): setters land in under 1 s; `offline` 2 s after a stop; resync after a restart and after a take; a symlink to the primary's socket is refused; with no cam1, all as today | yes | 350 lines, 9 h |
| T59 start at T | App.cpp, CC.cpp/.hpp | `start_us` = now + 500 ms, primary alone: first frame in [T, T + one period); names unchanged without the new fields; a hand-made `<next>_cam1` folder makes the take skip that number | yes | 60 lines, 3 h |
| T60 preview source | App.cpp, SettingsBridge.cpp/.hpp, WCP | the five labels round-trip through UI.conf, `ui.preview_source`, SettingsBridge and the select; `pip_cam0` is refused | yes | 120 lines, 4 h |
| T61 take coordination | App.cpp/.hpp | with the simulated cam1: policy, override, `record_cameras`; a cam1-only take and its tally; cam1 killed mid-take shows `lost` while cam0 rolls; format_media refused while cam1 writes; orphan stop after a primary restart | yes | 200 lines, 6 h |
| T62 UI plumbing | src/main.cpp, CB, PWR, ExternalMonitorManager, EMW | with no cam1: journal and drops as before. Through the symlink, cam0's frames fill the second item (ControlServer.cpp:175-196@31d5418) | yes | 140 lines, 5 h |
| T63 HDMI layouts | EMW, MediaStatusBridge.cpp, CAM1 pill | all five sources through the symlink; fallback within 1 s with a `--simulate` cam1 (sends no frames, UNCONFIRMED); drops compared against T55 | yes | 220 lines, 6 h |
| T64 WebUI | WCP, App.cpp | `?cam1port=8000` on a laptop and a phone: layouts, pills, REC label, badge; the stream stops while hidden | yes | 200 lines, 5 h |
| T65 second IMX585 | config.txt (Patrik): `dtoverlay=imx585,link-frequency=891000000` | r5's enumeration checks (a second `rp1-cfe`, `i2c@70000` in "Registered camera"); r4 M1; M2 with two sensors; CSI errors | no | 0 lines, 3 h |
| T66 acceptance | fixes only | r4 M5 combo ladder; every policy and source; drops per camera; cam0-cam1 offset | no | 0-20 lines, 4 h |
| T67 touch UI, optional | CameraPage, Settings rows | it builds; there is no touch screen to try it | build only | 150 lines, 4 h |

To T66: about 1,500 lines and 55 h, in about 13 Core files (4 new) and 11 UI files.

### 7. Top 8 risks

| # | Risk | Mitigation |
| --- | --- | --- |
| 1 | Init stomp: a CameraManager start costs a running take one frame at min_hmax and a phase step (claim-check L2, X7) | the secondary starts only while the primary is idle; the sysfs check runs before libcamera; T55 measures at 24 fps; no restarts during takes |
| 2 | First-match subdevs send cam1's WDR to cam0 (claim-check C4) | of_node binding in T56, before any second Core runs; Clear HDR rechecked |
| 3 | Load: one RP1 link, one SDRAM, two BEs, 4 GB RAM. 2× 4K uncompressed likely drops frames; 2× 4K HDR16 is out (r4) | T55 proxies, T65 M1, T66 M5; cam1 on frames buffer; one mode for both cameras in v1 |
| 4 | One Gen 3 ×1 exFAT NVMe for two writers (r5); a syncfs at each stop (CC:4744@31d5418) | T55 fio during a take; time left divided by the camera count; drops shown per camera |
| 5 | Settings drift between the Cores | compare every second; resync while idle; compare state, not commands (claim-check R4) |
| 6 | A take silently records only one camera | state words, CAM1 pill and REC label; a journal line per take on both Cores |
| 7 | One driver mode table: link frequency and lanes must match. cam1's overlay defaults to 720 MHz (claim-check X3), and the Boot config card does not check (BootConfigText.hpp:857-877@31d5418) | 891 MHz set explicitly on cam1's line; `cam1.message` flags a mismatch; 720 on both if CSI errors appear |
| 8 | GUI-thread cost of a second import and draw with the basic render loop | the `isVisible` guard; the second client runs only while `cam1` exists; drops compared in T62 and T63 |

### 8. Questions for Patrik

| Question | Default |
| --- | --- |
| Record policy? | follow the preview, as Cinemate does (config_loader.py:537@d6cc93e) |
| Preview default? | Both, as Cinemate does (config_loader.py:787@d6cc93e) |
| cam1 refuses at REC? | cam0 rolls alone; the CAM1 pill says why |
| Audio in cam1-only takes? | none in v1 |
| Link frequency? | 891 MHz on both; 720 on both if cam1 logs CSI errors |
| Settings allowed during a cam1-only take? | exposure only |
| Per-camera resolution or format? | later; identical in v1 |
| The :8001 page? | read-only |
| Should NEXT TAKE also steer the hardware REC button? | no: WebUI presses only |

## 3. Where the designs disagreed

| Disagreement | Options | Choice | Why (evidence) |
| --- | --- | --- | --- |
| How start options reach Core | `"$@"` (LI); env vars (OF, RF) | env vars mapped to flags | the script maps env to flags and passes no `"$@"` (scripts/start-apertar-core.sh:6, 44@31d5418) |
| Role | from `--camera` (LI); an env var (OF); `--secondary`/`APERTAR_ROLE` (RF) | LI's rule, set through `APERTAR_CAMERA` | the port already implies the role; a second name could contradict it |
| No sensor on cam1 | exit 0 (LI); a camera-less Error mode (OF); ExecCondition (RF) | exit 0 after a sysfs check, in Core | OF's Error mode still tries the camera, which is a manager start (claim-check L2); ExecCondition needs a script and misses hand runs; a failed start exits 1 today (App:8034-8040@31d5418) |
| "cam1 configured" | socket exists (LI, RF); config.txt (OF) | either one | config.txt is the rig's truth (BootConfigText.hpp:512-540@31d5418); the socket lets one-sensor tests run |
| Relay class name | `ControlClient` (LI); `PeerClient` (OF) | `ControlClient` | it is the client twin of src/ipc/ControlServer.cpp |
| Hook | wrapper around `handleCommand` (LI); edits at three callers (RF) | wrapper | there are four callers; RF missed idle standby (App:8281@31d5418) |
| Start order | cam1 first, async (LI, RF); cam0 first, sync (OF) | cam1 async, after the gates and before the 220 ms sleep | cam0's sleep and start then overlap cam1's start (App:14297-14302@31d5418); a sync start needs a longer lead |
| Buffer mode on cam1 | mirrored (LI, OF); primary only (RF) | primary only; cam1 always on frames | two RAM queues would share 4 GB (claim-check X-new5); set_buffer_mode writes the hardware file (App:12438-12460@31d5418) |
| Clip template | forwarded (LI, RF); not forwarded (OF) | not forwarded; the primary sends `clip_name` | one clip number for both names needs one owner (CC:1182-1197@31d5418) |
| user_activity | forwarded (RF); not forwarded (LI) | not forwarded | idle standby is off on cam1 (claim-check C8) |
| Reconfigure gate while either camera records | yes (OF, RF); none (LI) | yes, through the take-state rules | each Core's gates see only its own take (claim-check X-new4) |
| Setters during a take cam1 sits out | forward them (LI); not covered (OF, RF) | hold, then one resync | set_fps outside a take may pick another rung (CC:10588-10590@31d5418) |
| cam1 state on the HDMI | second control bridge (LI, RF); the primary's field (OF) | the primary's field | CB already polls the primary (CB:1010-1017@c153c33; claim-check U9, U-new1) |
| `cam1` contents | raw reply (LI); words (OF); fields (RF) | state word, message, drops | the screens need one word; Patrik needs the reason and the drop count |
| Frame liveness | QML on `frameCounter` (LI); a C++ flag (OF, RF) | QML | `frameCounter` with `frameArrived` already exists (ApertarPreviewSocketClient.hpp:21@c153c33) |
| Hiding a pane | size 0; `isVisible()` | `isVisible()` plus the `syncState` reset | `render()` imports before its empty-rect return (PWR:2407, 2436-2440@c153c33); a bridge swap keeps the old frame (PWR:410-426, 2410-2412) |
| Both with no cam1 frame | cam0 full screen (LI, RF); black right pane (OF, Cinemate) | black pane, "CAM1 NO SIGNAL" | cam0 full screen in Both hides a dead cam1 (r1) |
| Preview default | Cam 0; Both | Both | Cinemate's default (config_loader.py:787@d6cc93e); with no cam1 configured nothing changes |
| Policy default | always both; follow the preview | follow the preview | Cinemate's `record_policy` default (config_loader.py:537@d6cc93e) |
| Policy key type | enum (LI); bool | bool `recordBothCamerasEnabled` | there are two values, and `handleUiToggle` fits (App:12886-12899, 13058@31d5418) |
| Label check | labels or tokens (LI); labels only | labels only | the externalMonitorMode command is strict (App:13273-13274@31d5418) |
| Override field | `cameras`; `cams` (OF) | `cameras` | whole words, like `audio_enabled` (App:14228-14233@31d5418) |
| Clip field | `clip_name`; `clip` (RF) | `clip_name` | matches `preview_clip_name` (App:12803@31d5418) |
| cam1's clip name | `{cam}` in the template; a `_cam1` suffix | `{cam}` if present, else the suffix | `{cam}` is a token (src/util/ClipName.hpp:31-33@31d5418), but the default template lacks it (ClipName.hpp:23) |
| WebUI override | later (LI); pills (OF, RF) | pills | the WebUI is the only control surface (no touch screen) |
| REMAINING position | stays; moves | moves above the inset | it is anchored right and bottom, under the inset (EMW:1218-1224@c153c33; claim-check U7) |
| Secondary wait | for the socket (LI); while the primary records (OF); helper scripts (RF) | while the primary records, in Core; no socket means no take | a manager start during a take stomps it (claim-check L2, X7); no new scripts |
| Crash cover | dead-man on `ping` (RF); orphan stop | orphan stop | `ping` keeps its meaning (App:12330@31d5418); one rule, run at relink and after a cam0 fault |
| Turning trim and pre-roll off | in code (LI); env (RF) | env | the switches already exist (claim-check C7) |
| Sensor probe | keep; `APERTAR_SENSOR_PROBE=0` (RF) | keep | `=0` is untried, and its modes feed CC:3307 and 12441@31d5418 |
| Link frequency | 891 MHz; 720 MHz | 891 set explicitly on both; 720 on both if CSI errors appear | cam1's overlay default is 720 (claim-check X3); the mode table is module-wide (D1b) |
| Measure first | RF's step, at 25 fps; none | T55, at 24 fps | at 25 fps HBLANK is already minimal, so M2 would read "harmless" (claim-check L-new2) |
| HDMI test hook | socket symlink (LI); env var (OF) | symlink | every client gets every frame (src/ipc/ControlServer.cpp:175-196@31d5418); no new name |
| Timecode equality | equal (OF); equal unless a bin edge falls between first exposures (LI, RF) | unless a bin edge | claim-check R3 |