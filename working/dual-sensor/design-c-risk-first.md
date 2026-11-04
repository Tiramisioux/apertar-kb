<!-- Dual sensor, design panel (2026-11-04), design c: lens "risk-first". One of three independent designs written read-only from r1-r5 and the code (Core 31d5418, UI c153c33, Cinemate d6cc93e) before the claim check was in. Judged in design-merged-v1.md. Frozen: do not edit; what was taken over is in design-dual-sensor.md and changes-from-critique.md. -->

# Dual sensor: design, risk first

2026-11-04, read-only. Refs: `App`=`src/ApertarCoreApp.cpp`, `CC`=`src/camera/CameraController.cpp`, `WCP`=`src/web/WebControlPage.cpp`, other bare paths Core, all @31d5418; `UI:` @c153c33; `L:` libcamera @6b0b49f3; `drv:` imx585 @cd548ef. Every cited line was read tonight; unlabelled code claims are CONFIRMED.

## 0. The three load-bearing claims, re-checked

| Claim | Code, verdict |
| --- | --- |
| One hook catches every command: socket, WebUI and buttons all call `handleCommand` | `App:8299`, `:8322`, `:10083` → `:12173` (lock `:12182`). CONFIRMED |
| Start-at-T changes one value: the gate already is "first frame with SensorTimestamp ≥ start" | set `CC:7631`, `:7649`; test `CC:9072`, plus FrameDuration within max(500 µs, 2 %) (`:9073`). CONFIRMED |
| A second Core touches cam0 before it picks a camera, and exits without one | pick `CC:7262-7265`; probe: WDR on the first `imx585` subdev, then managers (`CC:7043-7056`); WDR `:7239`; exit 1 (`src/main.cpp:108`); every manager start sets HBLANK=min on every sensor (`L:src/libcamera/sensor/camera_sensor_legacy.cpp:292`), with no cross-process lock before acquire (`L:src/libcamera/pipeline_handler.cpp:143`, `:175`). CONFIRMED; effect on a streaming sensor UNCONFIRMED (T55) |

**Role swap**: `--simulate` records without a camera (`CC:11847-11857`; setters PROBABLE): a simulated primary plus a secondary on cam0 tests the plumbing on one sensor.

## 1. Architecture

The primary keeps today's unit, env and config, and takes cam0 when present.

| Item | Secondary |
| --- | --- |
| Unit | `apertar-core-cam1.service`, shipped disabled: the live unit's lines (r5) plus `After=apertar-core.service`, `ExecCondition=apertar-camera-present $APERTAR_CAMERA`, `ExecStartPre=apertar-wait-primary-idle`, `RestartSec=5`, `SyslogIdentifier=apertar-core-cam1` |
| Env | `APERTAR_CAMERA=cam1` (`i2c@70000` in the id, r5), `APERTAR_ROLE=secondary`, `APERTAR_WEB_PORT=8001`, `APERTAR_SOCKET_PATH=/tmp/apertar-core-cam1.sock`, mapped by the script to `--camera`, `--secondary`, `--web-port` (today only `--socket`, `--media`: `scripts/start-apertar-core.sh:44`); `APERTAR_STORAGE_PREROLL=0`, `APERTAR_MEDIA_TRIM=0`, `APERTAR_SENSOR_PROBE=0` (`CC:7159`) |
| Config | `XDG_CONFIG_HOME=/home/pi/.config-cam1` (UI.conf, camera_settings.conf, ladder, store: `App:519`, `CC:403`, `:416`, `src/hardware/HardwareConfigStore.cpp:127`); `APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf` with `[storage] buffer=frames` |

Primary only: inputs, outputs, tally (lit while either records), audio, gyro, media, system, pre-roll, trim, clock, boot config, idle standby, T, grid, relay, resync, UI.conf. `--secondary` switches these off in code where config cannot (r2 Q6); its `handleWebCommand` (`App:8317`) takes reads only, so :8001 is a view and an MJPEG source. A dead-man ends its take 5 s after the primary's last `ping` (`App:12330`; the UI never pings).

No cam1, no process: the unit ships disabled; once enabled, `apertar-camera-present` exits 1 unless sysfs shows an `imx585` under the port's I2C node, so systemd skips the unit instead of restart-looping beside cam0. `--camera` repeats the check before any manager or subdev write. No process, no socket file: nothing relayed, nothing new in the UI or WebUI (PROBABLE, T57).

## 2. Control path

**The primary Core relays**: every entry point already ends in its `handleCommand`, so the UI and WebUI keep one socket and the buttons need nothing.

- A FIFO relay thread (`src/ipc/PeerClient.*`: one AF_UNIX connection and JSON line per command, events skipped, KB trap 8), fed after `handleCommand` returns in its three callers and never under `commandMutex_`, so no UI reply (3 s timeout, `UI:src/ApertarControlBridge.cpp:1165-1167`) waits on cam1.
- A 1 s `ping` + `get_state` poll fills `cam1` in `/api/state` for the WebUI, beside `ui` (`App:9595`): connected, recording, drops, fps, size, clip, error, in_sync.

| Class | Commands | Rule |
| --- | --- | --- |
| Both, live | `set_iso*`, `set_shutter*`, `set_fps`, `set_wb*`, `set_exposure_*`, `set_af_*`, `set_fps_phase_lock`, `set_timecode_mode`, `set_conform_fps`, `set_clip_name_template`; `user_activity`, `enter_standby`, `wake` | after the primary's `ok` (power: always) |
| Both, reconfigure | `set_resolution`, `set_record_format`, `set_raw_bit_depth`, `set_clear_hdr`, `set_hdr_*`, `set_cdng_*`, `set_lossy_dng_ratio`, `set_prores_*`, `set_h264_resolution`, `set_tuning_file`, `apply_preset` | refused while either camera records (risk 1); some already are, per Core (`CC:11270-11271`) |
| Take | `record_start`, `record_stop` | §4 |
| Primary only | the §1 list, plus IMU, buffer, photo, timelapse, ramp, ladder, `set_controls` | cam1 sits out those takes (v1) |
| Secondary only | cam1-only `record_start`, resync, `ping`, grid message | relay only |

cam1 to the UI: a second, read-only `ApertarControlBridge` (path parameter; no `loadPersistedCameraSettings`, `UI:src/ApertarControlBridge.cpp:122`; only invokables write `camera/*`, `:286-843`, `:1298`) for its events (sent to every client, `App:14430`), and a second `ApertarPreviewSocketClient` (`UI:src/ApertarPreviewSocketClient.hpp:31`) for frames, live while the cam1 socket exists.

Resync: when the secondary answers again, the relay sends `apply_preset` with the primary's flat `camera*` keys (`App:13721`), then phase lock, clip template and standby; PROBABLE that this covers every mirrored field (T58).

Refusals. Primary refuses a `set_*`: nothing relayed. Secondary refuses: `cam1.error`, `in_sync=false` (in sync: last relay accepted, fps, size and format equal), so cam1 joins no take. It refuses `record_start`: cam0 records alone, chip `CAM1 NOT RECORDING`. Primary fails after relaying: `record_stop` relayed. A cam1-only take refused: an error (the primary waits ≤ 1 s).

API delta: commands `set_preview_source`, `set_record_both_cameras_enabled`; `record_start` fields `cameras`, `start_us`, `clip`; state `ui.preview_source`, `ui.record_both_cameras_enabled`, `cam1`; UI.conf `previewSource`, `recordBothCamerasEnabled`.

## 3. Display

The setting copies the `externalMonitorMode` quartet (`App:863-869`, `:2042-2043`, `:9617`, `:13267-13278`; `WCP:5272`; `UI:src/SettingsBridge.hpp:48`): UI.conf `previewSource`, `set_preview_source`, `ui.preview_source`; values `Both`, `CAM0`, `CAM1`, `PiP CAM0`, `PiP CAM1` (Cinemate `both|cam0|cam1|pip_cam0|pip_cam1`); default `Both`.

HDMI: two items in `monitorSurface` (`UI:qml/ExternalMonitorWindow.qml:390`): `main` (`externalPreviewItem`, `:406`) with the aids, and a passthrough `second`. Each gets a `PreviewWindowRenderer` (`UI:src/ExternalMonitorManager.cpp:233`); `second`'s connects last, so it draws on top (r3).

| Mode | main | second |
| --- | --- | --- |
| CAM0 | cam0 full | hidden |
| CAM1 | cam1 full, label | hidden |
| Both | cam0, left half | cam1, right half |
| PiP CAM0 | cam0 full | cam1 inset: 0.28 of the picture width, lower right, margin 0.03, 2 px frame |
| PiP CAM1 | cam1 full | cam0 inset |

Overlays as today, except Both: 2 px white frames, a 4 px divider, pane labels; no guides, centre marker or level. A chip by the status pill: `CAM1 REC`, `READY`, `NO SIGNAL`, `OFFLINE`, `NOT RECORDING` or `ERR`, plus cam1's drops.

Fallback: the preview client gains `hasFrame` (a frame within 1 s; `connected` precedes frames, r3); without it every mode shows CAM0 and the chip says NO SIGNAL or OFFLINE. No cam1 socket: CAM0, no chip, as today. The renderer gains its missing `isVisible()` check (r3).

WebUI: a second `<img>` in `#previewStage` from `http://<host>:8001/preview.mjpeg` (`App:8341`), without `crossorigin`: an image sends no Origin, so Core's guard passes it (`src/web/WebServer.cpp:159-173`; browser side PROBABLE, r3). Layouts as on HDMI; aids stay on cam0 (a cross-origin image taints the canvas, r3). A hidden image drops its `src`, so its Core stops encoding. The select joins the read-only "Preview source" row (`WCP:5230`, `:15413`) while `cam1` exists.

## 4. Recording

| What | Rule |
| --- | --- |
| Policy | UI.conf `recordBothCamerasEnabled` (false: follow preview), `set_record_both_cameras_enabled`, `ui.record_both_cameras_enabled`, as `recordAudioEnabled` (`App:2086`, `:9637`, `:13058`); default false |
| Override | `record_start cameras=cam0\|cam1\|both`, from WebUI "Next take" pills by REC, reset after the take; buttons follow the policy |
| Relay-only | `record_start start_us=<BOOTTIME µs> clip=<n>`, plus the existing `audio_enabled=false gyro_enabled=false` (`App:14228-14233`) |
| Resolve | as Cinemate (r1 Q3): override, always-both, preview Both, else the preview's main camera; cam1 only if connected, in sync and not sitting out; empty means cam0 |
| Start | the primary sets `T=now+lead` (P3, about 0.4 s, UNCONFIRMED), relays it, then starts itself. Both open at the first frame with SensorTimestamp ≥ T (`CC:9072`); a Core late for T opens at its next frame and reports it. With the lock on, T sits half a period before a grid frame, so both take that frame |
| Names | `{cam}` becomes the instance's port (now the literal `"cam0"`, `CC:1148`); the secondary appends `_{cam}` if the template lacks it, as `parse()` appends `_{clip}` (`src/util/ClipName.hpp:210`). Default (`:23`): `cDNG_26-11-04_C0007` and `cDNG_26-11-04_C0007_cam1` in `/media/RAW`. The primary relays the lowest `clip=n` free under both names; cam1 falls back to its own lowest free (`:285-294`) and reports it |
| Audio | primary only (ALSA is exclusive, r2); its WAV starts at the shared first frame |
| Timecode | FreeRun from each frame's wall time on one kernel clock: equal per frame unless the grid sits on a TC frame edge (PROBABLE, T63); RecRun: equal from a shared frame 0 |
| Time left | `estimatedRawBytesPerSecond` (`App:5564`) and `mediaBridge` (`UI:qml/ExternalMonitorWindow.qml:150-152`) × the cameras in the next or running take |
| Stop, toggle | `record_stop` always relayed; both flush at once; the UI waits for the primary only. `record_toggle`, `capture` and the WebUI button test "either records" (own state today, `App:10546`, `:10555`) |
| Refusal | as §2 |
| Drops | per Core: the UI from cam1's bridge, the WebUI from `cam1`; never summed |

## 5. Sync slot

Both Cores run `FramePhaseLock` on their own frames (`CC:8773`), on SensorTimestamp in CLOCK_BOOTTIME from one kernel (`src/camera/FramePhaseLock.hpp:21-22`), so no clock transfer is needed. Its datum is the arming frame (`:149`): two Cores now hold two grids with a fixed skew (r2 Q5). The servo's hooks:

| Need | Given |
| --- | --- |
| One grid | A: both derive origin and period from BOOTTIME and the mirrored fps, no message, re-derived after a restart. B: the relay adds the primary's `originNs` to `set_fps_phase_lock`, re-sent at resync |
| Start rule | `start_us` (§4) |
| fps, shutter together | the FIFO, a few ms apart (UNCONFIRMED, T58); an optional `at_us` if frame-exact |
| Headroom | clamp ±150 µs (`:39`) fits the gate's cadence test (`CC:9073`) |
| Readback | `fps_phase_lock_*` are only in `/api/state` (`App:9426-9430`); the poll needs them in `get_state` |

## 6. Steps

One commit per step on the Pi branch; each leaves the single-camera rig as it is. T55 runs before any build, r4's M1 and M2 before the servo (T65, other team) and any real dual take.

| Step | Changes (files) | Gate | 1 sensor; lines, hours |
| --- | --- | --- | --- |
| T55 | No code. M2a: r4's M2 (enumerate ×10 beside a `--save-pts` stream). M2b: a stray `apertar-core --socket /tmp/m2b.sock --web-port 0` (own XDG, trim and pre-roll off) during a take, probe on, then off. P1: 3-min takes at 50 fps (2×25), 4K SDR12 lossless and 1080p. P2: buffered fio at cam1's rate during a take. P3: `record_start` round trip ×10. P4: `MemAvailable`, `CmaFree`, RSS | blips per manager start, drops per proxy, lead, memory: they pick the dual modes and decide T64 | yes; 0, 3 h |
| T56 | `src/main.cpp`; `CC`: id match (`:7262`, `:7063`), subdev by `of_node` for WDR, HDR knobs and probe (as `:8114-8130`), sysfs check first, `{cam}`; `ClipName.hpp` | no flag or `cam0`: same `camera configured:` line, drops ≤ baseline; `cam1`: exits < 1 s before any libcamera line; M2b: no WDR write | yes; 150, 5 h |
| T57 | `App` (role), start script, new unit, two helpers, cam1 conf | no cam1: unit skipped, take unchanged. Secondary on cam0, primary stopped: :8001 MJPEG, media refused, no GPIO, I2C or ALSA opened | yes; 200, 6 h |
| T58 | new `src/ipc/PeerClient.*`; `App`: hook, table, poll, dead-man, resync, `cam1` | role swap: `set_fps` reaches :8001 < 50 ms; settings back < 2 s after a secondary restart; primary killed mid-take, secondary stops < 5 s. No secondary: `set_iso` round trip as today, no `cam1` | yes; 300, 8 h |
| T59 | `App`, `CC`, `CameraController.hpp`: `start_us` | 10 takes with audio, T=now+0.5 s: first frame (`audio sync: video_boot_us=`, r2) in [T, T+1 period) | yes; 40, 3 h |
| T60 | `App`, `CC`: policy, `cameras`, `clip`, resolve, relay-first start, refusals, toggle, tally, time left | role swap: right folders per policy and override; secondary refusal: the primary records, chip shown. No cam1: as today | yes; 250, 8 h |
| T61 | UI `ApertarControlBridge.*`, `ApertarPreviewSocketClient.*`, `PreviewWindowRenderer.cpp`, `SettingsBridge.*`, `ExternalMonitorManager.*`, `main.cpp`, `ExternalMonitorWindow.qml`; Core `set_preview_source` | no cam1: every mode as today, drops ≤ baseline; role swap: five layouts, fallback ≤ 1 s | yes; 400, 12 h |
| T62 | `WCP`: images, selects, Next take | as T61, in a browser | yes; 200, 6 h |
| T63 | cam1 fitted: boot config card adds its line, one link frequency on both (r4: 720 MHz); `i2c-0` free; enumerate (r5); r4's M1, M2, M5; DNG TC equal; crash drills | BE median < 20 ms per camera in preview (r4); drops within T55's prediction | no; 10, 4 h |
| T64 | if T55 or T63 needs it: `drv:imx585.c` per-device mode table; libcamera skips init of a sensor held elsewhere | mixed-HDR take and M2 clean | no; 150, 10 h |
| T66 | `UI:qml/CameraPage.qml`, optional | builds; review | yes; 200, 6 h |

## 7. Top risks

| Risk | Mitigation |
| --- | --- |
| 1 Init stomp: every manager start sets HBLANK=min on the other, streaming sensor: 1-3 per Core open (`CC:7246-7247`), 2 per probe (`:7056`), more per reconfigure; r4 predicts 1-3 bad frames each | M2 now; no secondary (re)start in a take; reconfigure refused while either records; probe off on cam1; T64 |
| 2 Wrong-sensor writes: WDR and probe hit the first `imx585` subdev (`CC:7043-7052`, `:7239`) | T56 before any second Core |
| 3 Shared mode table: each mode select (`drv:imx585.c:4465-4466`) rewrites all of the module-wide `supported_modes[]` (`:1064`, loop `:3280`) from that device's lanes, Clear HDR and link frequency (`:3273-3274`, `:3281`); hazard noted at `:4672-4673` | one link frequency, lane count and Clear HDR state on both, so the writes match; no mode change in a take; T64 before mixed HDR |
| 4 BE, DRAM, CMA: one BE engine for both node groups (r4); 2×4K SDR12 uncompressed is the 4K50 load that drops 12-18.5 % (r4) | P1 now, M1 and M5 later; 2×1080p and 4K lossless + 1080p first; cam1 pane passthrough |
| 5 One NVMe, two writers: Gen 3 ×1 exFAT, ≥ 600 MB/s sustained unproven (r4); page-cache pressure caused most UI-era drops (r3) | P2 now; `APERTAR_DNG_DONTNEED` as the primary; time left ×N; warn above 415 MB/s summed (clean for 10 min, r4) |
| 6 One folder for both: no `{cam}` in the default; `{cam}` is "cam0" | T56; no dual take before it |
| 7 Crashes: a restarting secondary stomps cam0's take; a dead primary orphans cam1's; a missing camera loops | wait-primary-idle; dead-man; resync stops orphans; `ExecCondition` |
| 8 4 cores, 4 GB: two worker pools, two RT callbacks, two MJPEG encoders, a second import on the GUI thread; RAM mode over-commits | secondary on frames; cam1 worker cap (`APERTAR_CDNG_WORKERS`); per-thread CPU in P1 and M5; MJPEG only while shown |

## 8. Questions for Patrik (default in brackets)

1. Default preview source? [`Both`; CAM0 without cam1]
2. Default record policy? [follow preview, as Cinemate]
3. cam1 refuses a take? [cam0 records alone, chip shown]
4. Folder names? [cam1 adds `_cam1`; same clip number]
5. Audio for cam1? [none; cam0's WAV serves both]
6. Per-camera ISO, WB, auto modes? [all mirrored in v1]
7. Ramp, ladder, stills, timelapse with cam1? [cam1 sits out in v1]
8. A mode T55 says will drop? [warn, do not refuse]
9. Link frequency once cam1 is fitted? [720 MHz on both, as r4 advises]