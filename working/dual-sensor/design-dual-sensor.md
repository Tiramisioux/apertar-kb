# Dual sensor on Apertar: design (v2, 2026-11-04)

Two IMX585 on one Apertar: two Cores, one picture and one REC button, frames on one grid by the phase lock.
This is the plan. Its sources are in this folder:
- the reader reports r1-r6c and their claim check (`claim-check.md`, 82 claims);
- the sync synthesis and its critique;
- the panel's three designs, the merged v1 and its critique.

Every change from a critique is listed in `changes-from-critique.md`. Nothing ran or changed on the Pi except the
read-only reads in r5.

**Refs.** Core `drop-frames` 31d5418 (what the Pi runs): `App` = src/ApertarCoreApp.cpp, `CC` =
src/camera/CameraController.cpp, `FPL` = src/camera/FramePhaseLock.hpp, `RC` = src/audio/RecordingClock.hpp, `WCP` =
src/web/WebControlPage.cpp. UI c153c33: `EMW` = qml/ExternalMonitorWindow.qml, `PWR` = src/PreviewWindowRenderer.cpp,
`CB` = src/ApertarControlBridge.cpp. libcamera `apertar` 6b0b49f3 (the Pi's base 7e9fef0b has the same helpers). Driver
`DRV` = imx585.c@cd548ef (what the Pi runs). Cinemate d6cc93e, cinepi-raw 63a08d5. Claim ids (L2, X7, U9, …) are in
`claim-check.md`; S1-S14 in `sync-critique.md`; P1-P25 in `critique-merged-v1.md`.

**Labels.** CONFIRMED (read in code at the ref, or read on the Pi in r5), PROBABLE, UNCONFIRMED. Numbers: MEASURED (on
the rig, from the KB) or ESTIMATE (a host model in `sim/`).

## 0 The decision in brief

1. **Two Core processes, one per sensor.** The primary runs cam0; the secondary runs cam1 with `--camera cam1`.
   - libcamera allows one CameraManager per process (camera_manager.cpp:309-311, L6), and the tuning file is per
     process (L4).
   - Every reconfigure restarts the manager (CC:7452-7457). In one process a mode change on one camera would stop the other.
   - Cinemate made the same choice (r1, M1). One process would be weeks of refactor (R9); two are about ten targeted changes.
2. **The primary is the only door.** The UI, the WebUI and the hardware keep talking to the primary alone. A wrapper
   around `handleCommand` forwards the camera settings to the secondary through a new `ControlClient`, the client twin
   of ControlServer. The secondary refuses everything else. With no cam1 configured, the rig behaves as today.
3. **Three fixes come first, because a second Core cannot run without them:**
   - pick the camera by port;
   - bind the WDR / Clear HDR writes to the Core's own sensor (today the first imx585 subdev in readdir order: a
     second Core fails with EBUSY or flips the other sensor's Clear HDR, C4, X-new1);
   - give the secondary its own socket, web port, config dir and hardware file, with the hardware, standby, audio,
     trim and pre-roll off.
4. **Display:** one setting, `previewSource` = Both (default), Cam 0, Cam 1, PiP Cam 0, PiP Cam 1. It copies the
   externalMonitorMode quartet: UI.conf key, Core command, state field, WebUI select.
   - HDMI (ExternalMonitorWindow) gets a second preview client, item and renderer on cam1's socket.
   - The WebUI gets a second `<img>` on :8001.
   - cam1 views fall back to cam0 while cam1 has no frame.
5. **Recording:** follow the preview (Cinemate's default) unless `recordBothCamerasEnabled` is on, with a per-take
   override `cameras=`.
   - The primary picks one start slot and one clip number for both cameras: cam1's folder is cam0's name plus `_cam1`.
   - One WAV, in cam0's folder.
   - Both cameras start on the same frame slot and stop on the same slot.
6. **Sync: the existing phase lock, on one absolute grid.** Each Core locks its frames to slots k·T on the kernel clock
   both read (SensorTimestamp), so no message is needed between them. Three more changes make it work:
   - the lock's frame-length pushes change VBLANK only: pin `{d, d+1}` instead of `{d, d}`;
   - an even-VMAX quantiser smooths the 14.8 µs steps;
   - the driver rewrites SHR when VBLANK changes.

   The same changes fix T27's flicker on one sensor, so they are tested first.
7. **Accuracy (ESTIMATE):** 30-55 µs maximum between the sensors, about 10 µs RMS. That is under 0.2 % of a 25 fps
   frame, and it does not grow with take length.
8. **Platform rules:**
   - Both overlays get one link frequency and 4 lanes, because the driver's mode table is module-wide (D1b). Use 891
     MHz on both; cam1's line must say so, since the overlay default is 720 (X3).
   - Never start or reconfigure either Core while a camera records: each manager start writes HBLANK on the other
     sensor (L2).
   - v1 runs both cameras in one mode. 2× 4K Clear HDR 16-bit will not fit; 2× 1080p and 2× 4K SDR 12-bit lossless are
     the targets (r4 Q5).
9. **Steps T56-T70.** Everything up to T67 runs with the one sensor on the rig today: the T56 measurements, the lock
   fix and the T27 retake (T57-T58), then the plumbing against a simulated cam1. T68 needs the second sensor.
10. **Size:** about 2,200 lines (Core ~1,500 with the WebUI, UI ~400 plus ~150 for the optional touch UI, driver ~10,
    KB simulator ~150) and about 70 hours. The API grows by 14 names (§8).

## 1 What Cinemate does, and what we take

Cinemate's dual feature (r1; re-checked M1-M12):
- **Process model:** one `cinepi-raw` per sensor (`--camera idx --cam-port camN`). Both share the Redis channel
  `cp_controls`, and every shared key goes to both processes.
- **HDMI composite:** the secondary copies a lores I420 frame into SysV shm `CIND`. The primary composites
  `both|cam0|cam1|pip_cam0|pip_cam1`: PiP inset 0.28, lower right, margin 0.03, falling back to cam0.
- **Recording:** a record gate `record_cams` with `record_policy` `follow_preview` or `always_both`. Folders end in
  `_camN`. Each process writes its own WAV through dsnoop.
- **Weaknesses:**
  - Sync is not real: `--sync` only gates the phase lock and cam1 free-runs (M6).
  - The mid-take join is dead code (M7).
  - Nothing supervises the processes (M12).
  - It has no hardware report beyond one preview run (M8).
  - Dual broke silently for 8 months when `--camera` was dropped (M-new1).

| Take | Leave |
| --- | --- |
| One process per sensor; the port label (`cam0`/`cam1`) names folders and keys | Redis fan-out: Apertar's primary relays instead (the socket is its one entry, U-new1) |
| The five preview sources, the PiP geometry, the cam0 fallback | The shm compositor: Apertar's UI already draws dma-bufs and can draw two (U3, U4) |
| Record policy follow-preview / always-both, plus a per-take override | Per-process clip names and TC anchors (M4, M10): Apertar's primary hands out one name and one slot |
| Two MJPEG streams laid out by the browser | Per-process WAVs: one WAV, the primary's |
| An explicit camera selector, refusing a wrong port | The mid-take join (M7) |

## 2 Platform rules

| Rule | Why | Label |
| --- | --- | --- |
| Two processes can each own one camera | PiSP pairs the k-th free CFE with the k-th free BE in each process, in the same order, and `acquire` lockf()s only that pair (L1). The second BE is `media3` (r5). If a pass registers no camera, the next camera's handler holds all four devices (L-new1): keep cam0 registerable in both processes | CONFIRMED in code; the two-process run is UNCONFIRMED |
| Same link frequency and lane count on both overlays | `supported_modes[]` and `supported_10bit_modes[]` are module-wide and rewritten from the caller's link and lanes (D1a-c). At 891 MHz on cd548ef, different modes and SDR/HDR per sensor are safe | CONFIRMED |
| cam1's overlay line names 891 MHz itself: `dtoverlay=imx585,link-frequency=891000000` | the overlay default is 720 (X3). 891 MHz streams with a "DPHY datarate out of range" warning (hardware-log.md:963). If cam1 logs CSI-2 errors, move **both** to 720 | CONFIRMED; cam1 at 891 UNCONFIRMED |
| Any CameraManager start writes HBLANK = minimum on every sensor it enumerates | `CameraSensorLegacy::init` (camera_sensor_legacy.cpp:288-296), at every Core start, wake, reconfigure and every `rpicam` call (L2). The owner's IPA restores it at the next frame start: one frame at min_hmax and a lasting phase step (L3). It is a no-op while HBLANK is 0, which it is when the lock pins VBLANK-only (§7.3); it is a 5.0 ms step at 24 fps on the lattice (L3) | CONFIRMED in code; MEASURED: no |
| Flips and Clear HDR are grabbed while streaming; HBLANK, VBLANK, exposure and the HDR knobs are not | DRV:4207-4209 (D2a). A Core writing to the wrong subdev changes the other sensor live | CONFIRMED |
| One regulator powers both sensors | `cam1_reg` → `/cam0_reg`, GPIO 34 (r5). Neither sensor can be power-cycled alone | CONFIRMED |
| Bandwidth | One RP1 link, one SDRAM, one PiSP engine (two node groups, time-shared), one Gen 3 ×1 exFAT NVMe (r5). 2× 4K SDR 12-bit uncompressed (622 MB/s) equals the 4K50 load that already drops 12-18.5 % (MEASURED, hardware-log.md:953-959). 2× 4K HDR16 (830 MB/s) is out. Plausible: 2× 1080p, 4K lossless + 1080p (v2: per-camera modes), 2× 4K SDR 12 lossless (marginal) | ESTIMATE (r4 Q5) |
| RAM | 4 GB. Two RAM-mode queues could each budget half of it (X-new5): cam1 always runs `buffer=frames` | CONFIRMED (budget rule) |
| `rpi.sync` is no option here | no tuning has the block (r5); its multicast has no route without the Ethernet cable and `lo` has no MULTICAST (r5); its corrections go through the same lattice (S13) | CONFIRMED |

## 3 Architecture: two Cores

### 3.1 Roles and options

| | Primary | Secondary |
| --- | --- | --- |
| Unit | `apertar-core.service`, unchanged | new `apertar-core-cam1.service` |
| Camera | `--camera` absent or `cam0` | `--camera cam1` (env `APERTAR_CAMERA=cam1`) |
| Socket, web | `/tmp/apertar-core.sock`, :8000 | `/tmp/apertar-core-cam1.sock`, :8001: MJPEG and reads; every POST refused |
| Config | as today | `XDG_CONFIG_HOME=/home/pi/.config-cam1` (own camera_settings.conf, mode_ladder.conf, UI.conf, hardware-state notes: C5); `APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf` (`[storage] buffer=frames`, `[imu]` and `[ina219]` `enabled=false`, inputs `enabled=false`: C6) |
| Env | as today | `APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0` (C7, P14) |

- **Start options.** `scripts/start-apertar-core.sh` maps env to flags (:6) and passes only `--socket` and `--media`
  (:44). Two more env vars copy that pattern: `APERTAR_CAMERA` → `--camera`, `APERTAR_WEB_PORT` → `--web-port`
  (`--web-port` exists: src/main.cpp:32-37, 68-82). With neither set, the command line is today's.
- **Role.** `--camera` with any value but `cam0` makes the Core a secondary. There is no separate role flag, because the
  port already says it and a second name could contradict it (design-merged-v1 §3).

### 3.2 Camera by port, subdev by of_node (preconditions)

- **Camera pick:**
  - `cam0`/`cam1` resolve through `/proc/device-tree/__symbols__/i2c_csi_dsi0|1` to `rp1/i2c@88000|70000`, which is
    part of the libcamera camera id (r5, CONFIRMED on the Pi). Any other value is a substring of the id:
    `--camera i2c@88000` runs a test secondary on cam0's sensor.
  - Both pick sites change: the session (CC:7262-7265) and the probe (CC:7063-7066).
  - The primary prefers cam0's port, else today's rule, so a one-sensor rig on cam1 keeps working.
  - The secondary takes its own port or exits. It never falls back to `front()`.
  - If cam1's acquire fails with EBUSY (a dead cam0 let the primary take cam1, P16), the secondary logs one line and
    exits 0.
- **Subdevs:** `openImx585Subdev` (CC:6875-6892) takes the first imx585 subdev. WDR (CC:6925), the ext-control writes
  (CC:6960), the probe (CC:7039) and the session-start WDR write (CC:7239) all use it. Match the subdev's `of_node` to
  the camera id, as `resetStoppedSensorTiming` already does (CC:8118-8130). Without this, whichever Core's sensor is
  listed second fails every start while the other streams (C-new1).
- **Identity in state:** `camera_id` (`camera->id()`) and `camera_port` in get_state and the settings event (C11). The
  clip-name `{cam}` comes from the port, not the hard-wired "cam0" (CC:1148).
- **No sensor on the port:** in `main()`, before `app.start()`, the secondary looks in sysfs for a sensor subdev whose
  `of_node` lies under its port's I2C node.
  - If there is none, it logs one line and exits 0. The check must come first: `start()` runs the low-power restore and
    starts threads before the camera (App:7985-8034), and a failed start exits 1 (src/main.cpp:108-111), which
    `Restart=on-failure` would loop (P25).
  - No libcamera call is made, so cam0 is never touched. `--simulate` skips the check.

### 3.3 The secondary's role gate

| Off on the secondary | Where |
| --- | --- |
| trigger, PCF8574, NeoRotary4, GPIO buttons, Grove, power button, tally, controls worker | App:8080-8101, 8124-8125 |
| idle-standby loop | App:8253-8285 (P1) |
| photo-mode restore at start | App:8042-8048 (P1) |
| low-power restores at start, stop and wake; standby's machine-wide steps | App:7985-7997, 8163-8172, 12294-12304; 12270-12287 (P13) |
| INA219 and IMU reads in `/api/state` | App:9302, 9663 |
| audio, gyro and sound-only in `record_start` | App:14216-14262 |
| the stop `syncfs`: replaced by an fsync of its own files | CC:4744 (P6, C-new3) |
| every command outside the allowlist (§4.2): "cam1 takes commands from the primary." | top of `handleCommand` |
| every POST on :8001: /api/command, /api/config, the preset routes, media delete, boot config | App:9180, 8588, 8861, 8909, 8946, 8972, 9054, 9136 (P12) |

Kept: the hardware-file adopt and `refreshBufferRequest()` (App:8104-8122), which read `buffer=frames`.

### 3.4 Unit, start order, install

```
# /etc/systemd/system/apertar-core-cam1.service: the live unit (r5) without the wait-ui ExecStartPre
[Unit]
After=apertar-core.service
PartOf=apertar-core.service
[Service]
ExecStart=/home/pi/start-apertar-core.sh
Restart=on-failure
RestartSec=5
LimitNICE=-5
LimitRTPRIO=80
Environment=LIBCAMERA_LOG_LEVELS=IPARPI:ERROR
Environment=APERTAR_CAMERA=cam1 APERTAR_SOCKET_PATH=/tmp/apertar-core-cam1.sock APERTAR_WEB_PORT=8001
Environment=XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf
Environment=APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0
SyslogIdentifier=apertar-core-cam1
[Install]
WantedBy=apertar-core.service
```

- The live unit's full text is UNCONFIRMED: only r5's summary is known. Read `systemctl cat apertar-core` again before
  writing this.
- `APERTAR_RT` and `APERTAR_RT_CPUS` are as on the primary (the script's chrt 70 and taskset 1-3), until T69 measures
  both Cores.
- **Start order (P10).** Before its first camera start, the secondary waits up to 30 s for the primary's socket to
  accept a connection, then waits until the primary is *idle* (§4.3), then starts.
  - The primary does the same towards cam1 while cam1 reports recording, so a restarted primary does not stomp a
    cam1-only take.
  - The rule rules out two probes at the same time and the min_vmax race (D1b).
- **Install:** Patrik copies the unit and runs `sudo systemctl daemon-reload` and `sudo systemctl enable
  apertar-core-cam1`.
  - With no sensor on cam1, a boot leaves the unit `inactive` (exit 0), not `failed`.

## 4 Control path: the primary relays

### 4.1 ControlClient

`src/ipc/ControlClient.{hpp,cpp}` is new: the client half of ControlServer. It runs in the primary on its own
thread, with a FIFO.

- **Linking:**
  - It links only when cam1 is configured: config.txt names a cam1 sensor (BootConfigText.hpp:474-480, 512-540), or
    the cam1 socket *accepts a connection* (for tests; a stale socket file does not count, P23).
  - It refuses to link to its own socket (same inode).
- **Reading:** it reads all the time. cam1 sends every line to every client (ControlServer.cpp:175-196) and drops a
  client that falls behind (R7).
  - It closes every fd it receives, using `recvmsg`.
  - It keeps the `recording`, `buffer`, `media_write_state` and `preview_frame` events (timestamps, for §7.6) and skips
    the rest (P4).
- **Replies:** it matches replies by id. One small helper reads a number, bool or string by key and skips nested values,
  because the flat parser stops at the first `}` (P15, R6).
- **Polling and liveness:** it polls cam1's `get_state` every second.
  - cam1 is `offline` only on EOF or a failed connect. A slow reply means `busy`: cam1's get_state waits behind its own
    command lock (P22).
  - Commands sent while cam1 is offline are dropped. The resync on relink catches up.
- **Locks:** it never takes `commandMutex_`. The one wait under it is a cam1-only `record_start`, at most 1 s, like the
  220 ms audio sleep.
- **The hook:**
  - Today's `handleCommand` body (App:12173) becomes `handleCommandLocal`. A wrapper keeps the old name, so its four
    callers (App:8281, 8299, 8322, 10083) do not change.
  - After a local ok, the wrapper queues "both" commands for cam1. `record_start` and `record_stop` coordinate inside
    their own branches (§6).

### 4.2 Command classes

| Class | Commands |
| --- | --- |
| Both: forwarded after the primary's ok | `set_iso(_auto)`, `set_shutter_*`, `set_exposure_*`, `set_wb(_auto)`, `set_fps`, `set_resolution`, `set_record_format`, `set_cdng_*`, `set_lossy_dng_ratio`, `set_prores_*`, `set_tuning_file`, `set_raw_bit_depth`, `set_clear_hdr`, `set_hdr_*`, `set_h264_resolution`, `set_timecode_mode`, `set_conform_fps`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_af_*`, `set_mode_ladder`, `apply_preset` (camera keys only, §4.4), `enter_standby`, `wake` |
| Coordinated | `record_start`, `record_stop` (§6) |
| Each its own | `get_state`, `ping`, `help`, `list_*`, `get_mode_ladder`, `preview_subscribe`, `preview_clip_name` |
| Primary only | UI.conf keys (display, aids, `previewSource`, `recordBothCamerasEnabled`), audio, photo, timelapse, clip template, buffer mode, media, boot config, time and zone, fan, power, IMU, controls, `storage_preroll`, `user_activity` |

- One list is both the forward list and cam1's allowlist: a new command stays refused on cam1 until someone adds it.
- The secondary also accepts `record_start`, `record_stop`, and the read commands above.

### 4.3 Take-state rules and "idle"

**Idle**, for both Cores (P2), means the camera is Ready and none of these is true:
- `recording`;
- `storage_preroll_active` (a pre-roll is a real take at a raised fps, CC:11908-11956);
- `timelapse_active` or `still_exposure_active`;
- `media_writes_pending`;
- photo mode.

The compare, the resync and both Cores' start waits use this one test. The compare does not run in photo mode.

| State | The primary accepts | Sent to cam1 |
| --- | --- | --- |
| Both idle | as today | every "both" command |
| Both record | as today: each Core's own take gates refuse reconfigures (CC:10514-10520, 10561-10600, 11196, 11490-11495, 11759-11766, 12484-12490) | every "both" command |
| cam0 records alone | as today | nothing during the take; one resync after it |
| cam1 records alone, or applies a change | reads, the exposure setters, display keys, `record_stop`; anything else: "CAM1 is recording." or "CAM1 is applying a change. One moment." (the "One moment." pattern, App:12198, 12203) | the exposure setters |

- **Busy window (P5):** cam1 counts as busy from the moment the relay sends it a reconfigure-type command (resolution,
  format, Clear HDR, bit depth, an fps that may change the ladder rung, `apply_preset`) or `wake`, until the reply.
  - The reason: each of these is a manager start on cam1, and so an HBLANK write on cam0's sensor (L2).
  - In that window `record_start` refuses, and a bounded time later cam1 is dropped from the take.
- **Rig busy (P7):** `cam1RecordingActive()` is true when `cam1.state == recording`. It copies `soundRecordingActive()`
  (App:9971-9974) and joins it at every site where the rig counts as busy:
  - tally (8100, 11965), idle standby (8271), web gates (8983, 9065), state (9272, 12503);
  - REC toggles (10546, 10555), pre-roll (11087), playback (11304), trim (11432);
  - `recordingGateActive()` (11879).
- **Writes pending:** the media gate (12212-12221), standby (12263) and the delete gates (8990, 9072) also refuse while
  cam1 has writes pending (P4).

### 4.4 Presets and resync

**What cam1 gets (P1, R5):**
- only the camera keys that `apply_preset` parses into `presetSettings`, flattened (presets nest under `settings`,
  App:7685; flatten as WCP:18615-18620);
- minus `photoModeEnabled`, `photoLongExposureEnabled` and `cameraClipNameTemplate`;
- none of the UI.conf keys that `apply_preset` writes (App:13994-14071: `standbyTimeoutSeconds`, `photoModeEnabled`
  and the rest), because they would turn cam1's idle timer or photo mode on;
- then `set_mode_ladder`, which presets lack.

This applies to user presets and to the resync alike.

**When to resync:** one resync runs at the next moment both cameras are idle, after any of:
- a (re)link;
- a non-ok reply to a forwarded command (that reply also sets `cam1.message`, P8);
- a take cam1 sat out;
- a forwarded `set_record_format` or `apply_preset` (each Core restores its own per-format profile, CC:11213-11239);
- a difference found by the compare.

**The compare:** every second, it checks every field the resync sets in `settingsBody` (App:298-356), skipping
auto ISO, shutter and WB. It compares the resulting state, not the commands sent (R4).

**The mode ladder:** cam1 follows the primary's resulting mode, and its own ladder stays off.

### 4.5 cam1's state

New in get_state and `/api/state`:
- `cam1` = `{state, message, recording_dropped_frames, locked, skew_us}`. It is absent when cam1 is not configured.
- `record_cameras` = `cam0`, `cam1`, `both`, or `none` in Sound Recorder mode (P19): for the running take, else for the
  next one.

| `cam1.state` | Meaning |
| --- | --- |
| `not_found` | configured, no sensor on the port (the primary runs the same sysfs check) |
| `offline` | no link |
| `busy` | applying a forwarded change |
| `ready` | in the next take |
| `idle` | sits out the next take |
| `recording` | in the running take |
| `writing` | writes pending |
| `refused` | `message` says why |
| `lost` | left a running take: link down, or its own buffer safety stop |
| `standby` | in standby |

- **HDMI:** no second control bridge (U9). CB polls the primary at 1 s while `cam1` exists (CB:1010-1017) and parses
  `cam1` and `record_cameras`.
- **WebUI:** it reads `snapshot.cam1` from :8000. A fetch to :8001 gets 403 (WebServer.cpp:159-173, 373-376; U10).

### 4.6 Failures

| Situation | What Patrik sees (HDMI and WebUI) | What one REC press does |
| --- | --- | --- |
| cam1 not configured | today's screens | records cam0, as today |
| configured, no sensor found | amber `CAM1 NOT FOUND`; cam1 views show cam0 | records cam0; the pill blinks if the policy wanted cam1 |
| cam1 Core crashed or restarting | amber `CAM1 OFFLINE`; views fall back | records cam0. cam1 restarts only when the primary is idle |
| cam1 applying a change | white `CAM1 BUSY` | refused for a moment: "CAM1 is applying a change. One moment." |
| cam1 still writing the last take | `CAM1 WRITING` | refused: "Wait for CAM1 to finish writing to media." |
| cam1 refuses REC | amber `CAM1 REFUSED` and the reason until the stop | cam0 rolls; cam1 never joins mid-take |
| cam1 lost mid-take | amber `CAM1 LOST` and the reason; its frames so far stay on the card | cam0 keeps rolling. In a cam1-only take the tally goes off and `recording` turns false (P7) |
| cam0's buffer safety stop | as today | stops both (it runs `handleCommand("record_stop")`, App:11038-11042) |
| cam0 refuses | one error, as today | nothing starts |
| cam0 fails to start after cam1 was told | one error | cam1 gets `record_stop` (the orphan stop below); an empty cam1 folder may remain |
| card nearly full | REMAINING counts down for both | under 1 GiB free, each Core refuses (App:11337-11341) |

- **Orphan stop:** if cam1 records while the primary has no take that includes it (after a relink, or a cam0 fault),
  the primary sends `record_stop`.
- **Standby:** on relink during the primary's standby, cam1 gets `enter_standby` (P13).

## 5 Display

### 5.1 The setting

It copies the `externalMonitorMode` quartet. Every site follows (U8):

| End | Sites copied |
| --- | --- |
| Core | normaliser App:863-869, snapshot :1870-1873, reader :2040-2047, preset :7767-7773 and apply :14027, state `ui.external_monitor_mode` :9617, command :13267-13278 (strict check :13273-13274), help :12496 |
| UI | SettingsBridge.hpp:47-50, .cpp:360-366, 547-550, 1074-1092, 2165-2168, 2257-2260; SettingsPage.qml:2450-2491 (optional, touch) |
| WebUI | WCP:5272, 18897, 20329, 14129, 6444, 15502, 15560, 10889-10890, 18646 |

- UI.conf `previewSource`: `Both` (default), `Cam 0`, `Cam 1`, `PiP Cam 0`, `PiP Cam 1`. The labels are strict, like
  the quartet's: `pip_cam0` is refused.
- Command `set_preview_source`; state `ui.preview_source`. Not in presets in v1.
- The primary writes UI.conf and the UI follows the file. No socket event is needed (r3 Q3).
- With no cam1 configured, the select is not shown and the second picture does not exist.

### 5.2 HDMI: ExternalMonitorWindow

The rig's HDMI picture is EMW, because `hdmi_external_only` defaults to true (DisplayConfigBridge.cpp:294, 354-357;
K3). The rig's value is from the KB note of 2026-11-01. The UI's startup line (main.cpp:281) confirms it.

**Pieces:**

| Piece | Change |
| --- | --- |
| Preview client | One more `ApertarPreviewSocketClient` (beside main.cpp:291) on the explicit cam1 path, only while `cam1` exists. All four bare `connectToCore()` calls mean cam0 (U2, X12), so the standby wiring (main.cpp:335-350, EMW:321-330) passes the path too. `recordingChanged` reaches it too (main.cpp:351-352, P18) |
| Liveness | cam1 has a signal while the client's `frameCounter` (hpp:21) moved in the last second (a 500 ms QML timer) |
| Second item | `externalPreviewItem1` beside EMW:404-428, with its own objectName (U7). Its renderer is made in `ensureWindow` after the first (ExternalMonitorManager.cpp:231-238), so it survives the rebuild on wake (U6) and draws on top |
| Renderer, two lines | (1) `render()` returns early for a hidden item: today only `scheduleWindowUpdate` checks (PWR:347), while `render()` imports first (2407). (2) `syncState` sets `m_resetPreviewState` when the bridge changes (410-426); otherwise a swapped pane keeps the other camera's last frame (U-new7) |
| Transforms | Both panes keep the display transforms: LUT, desqueeze, SMPTE, rotation, aspect. Only the aids (zebra, peaking, false colour, greyscale) and the guides stay on the main pane (P17) |

**Layouts at 1920×1080:**

| Source | Main pane (aids) | Second pane (on top) | cam1 without a frame for 1 s, or offline |
| --- | --- | --- | --- |
| Cam 0 | cam0 full screen (today) | hidden | as today |
| Cam 1 | cam1 full screen, CAM1 tag | hidden | cam0 full screen; amber "CAM1 NO SIGNAL · SHOWING CAM0" |
| Both | cam0, left 960×540 | cam1, right 960×540 | right pane black, "CAM1 NO SIGNAL" |
| PiP Cam 0 | cam0 full screen | cam1 inset, 0.28 of the width, lower right, margins 0.03 | no inset |
| PiP Cam 1 | cam1 full screen (bridges swapped) | cam0 inset | as Cam 1 |

- Both panes and the inset get 2 px white frames. Both adds a 4 px divider and pane tags, and turns off guides, centre
  marker and level.
- The inset's height follows the frame (U-new6).
- In PiP, REMAINING (EMW:1218-1224) moves above the inset (U7).
- Each pane's frame turns red while its camera records (one frame today, EMW:1427-1435).
- A CAM1 pill sits beside the status pill (EMW:1085), built from DroppedFrameWarning (EMW:1181-1186). It shows
  `CAM1 <STATE>` and cam1's drops:
  - red while recording;
  - amber when something is wrong, blinking while a take that wants cam1 runs without it;
  - white when ready, grey when idle.
- The HUD keeps cam0's values: the settings are mirrored.
- **Photo mode and timelapse run on cam0 only (P11).** cam1 sources then show cam0, tagged "PHOTO · CAM0".

```
Both (not to scale)                     PiP Cam 0
+----------------------------------+    +----------------------------------+
| 25 FPS  ISO 800  180  5600K      |    | 25 FPS  ISO 800  180  5600K      |
|+---------------++---------------+|    |CAM0                              |
||CAM0           ||CAM1           ||    |            cam0, aids            |
||   cam0, aids  ||   cam1        ||    |                    REMAINING x2  |
||   red = REC   ||   red = REC   ||    |                    41 MIN        |
|+---------------++---------------+|    |                    +-----------+ |
|      [REC]  [CAM1 REC 0]         |    |  [REC][CAM1 REC 0] |CAM1  cam1 | |
| RESOLUTION  10:42:31:07  REMAIN. |    | RES  10:42:31:07   +-----------+ |
| 3856x2180               x2 41 MIN|    +----------------------------------+
+----------------------------------+
```

**Cost.** The preview fill follows pixels, not sources: Both at 1080p is about half of one full-screen draw, and PiP
adds about 8 % (r3 Q2). New is a second dma-buf import and up to twice the redraws on the GUI thread (basic render
loop). The two-line `isVisible` guard and the recording fps cap on both clients bound it. T65 and T66 measure the drops.

### 5.3 WebUI

- **The picture:** `<img id="previewStream1">` loads `http://<location.hostname>:8001/preview.mjpeg?stream=n`, without
  `crossorigin`.
  - An image request sends no Origin, so it passes Core's check (U11; browser side PROBABLE).
  - It drops its `src` while hidden (WCP:12047-12053), since MJPEG encodes only while viewed (App:9735).
  - Aids stay on cam0: a cross-origin image taints the canvas (r3 Q6).
- **Layouts:** CSS per source. Both is side by side, stacked below 700 px; PiP is a 28 % inset with 3 % margins.
  Tags, red frames and NO SIGNAL work as on the HDMI.
- **The setting:** the read-only "Preview source" row of the Live preview card (WCP:5229-5232) becomes a select while
  `cam1` exists.
- **Recording controls:**
  - "Record both cameras" pills beside Record Audio (WCP:5477, 16163-16169).
  - NEXT TAKE pills (Auto, CAM0, CAM1, Both) next to REC. They send `cameras` with this page's REC press and reset
    after the stop. Hardware buttons follow the policy.
  - The REC label names what one press records: "REC BOTH", "REC CAM0", "REC CAM1 · NO AUDIO", or "REC SOUND" in
    Sound Recorder mode. It shows "STOP" while either camera records.
- **cam1 status:** a CAM1 badge from `snapshot.cam1`, with its sync line (§7.6).
- **Test hook:** `?cam1port=8000` (JavaScript only) points the second picture at cam0's own stream.
- **The :8001 page:** cam1's full WebUI, read-only, because its POSTs are refused (§3.3).

## 6 Recording

### 6.1 Which cameras

The first match wins:
1. `cameras` on `record_start` (`cam0`, `cam1`, `both`).
2. `recordBothCamerasEnabled` (UI.conf, default false; copies `recordAudioEnabled`, App:2086-2087; command
   `set_record_both_cameras_enabled` through `handleUiToggle`, App:12886-12899): both.
3. The effective preview: Both gives both; Cam 0 and PiP Cam 0 give cam0; Cam 1 and PiP Cam 1 give cam1. While cam1
   is not ready, cam1 sources count as Cam 0.

**Not-ready cam1:** a cam1 that is not ready is dropped from the take. cam0 rolls, and the pill says why (also for an
explicit `cameras=both`, P21c).

**Excluded:** photos and timelapse run on cam0 only (P11). Sound Recorder mode records sound and no camera, so
`record_cameras` is `none` and an explicit `cameras` is refused there (P19).

### 6.2 Start and stop on one slot

**A take without cam1 starts exactly as today**, with "now" and no lead (P3).

**A take with cam1 starts in the `record_start` branch**, after the gates (App:12196-12231) and the trim wait
(12225-12228), before the audio sleep (14297):
1. **The slot.** The primary picks k0 = ceil((now + lead) / T) on the grid of §7.2 and `start_us` = (k0 − ½)·T, in
   the SensorTimestamp domain (CLOCK_MONOTONIC, S3).
   - The lead is 500 ms until T56 measures the record-start latency.
   - It covers the audio sleep, the folder and writers, and cam1's command path (R1).
2. **One clip number** for both names: the lowest number free under both (CC:1182-1197).
   - cam1's name uses `{cam}` = `cam1` if the template has `{cam}` (ClipName.hpp:31-33). Otherwise it is cam0's name +
     `_cam1`: the default template `{format}_{date}_{clip}` (ClipName.hpp:23) has no `{cam}`.
3. **The relay** sends cam1 `record_start cameras=cam1 start_us=… clip_name=… tc_offset_us=… audio_enabled=false
   gyro_enabled=false sound_only=false` and does not wait.
4. **cam0** starts with the same `start_us` and its own name.
5. **Both Cores** set `recordingStartBootUs_ = start_us` instead of now (CC:7631, 7649). The gate's test
   `SensorTimestamp/1000 >= recordingStartBootUs_` (CC:9072) then records slot k0 first on both (PROBABLE: the boundary
   sits mid-slot and |e| ≤ 50 µs).
   - With `clip_name` given, the folder is made with an exclusive `create_directory` (CC:7543-7544).
6. **Report.** Each Core replies and logs `first_slot`, its first frame's slot.
   - If a Core opens its gate after `start_us` has passed, it starts on its next frame. The take keeps both cameras, and
     the journal, the pill and the reply give the offset in frames ("CAM1 started 2 frames late").
   - Post-production pairs the clips by `first_slot`.

**Stop (both cameras in the take).**
- The primary picks k1 = ceil((now + stop lead) / T) and sends `record_stop stop_us = (k1 − ½)·T` to cam1 first, then
  stops locally with the same value. The stop lead is 100 ms until T56 measures it.
- Each Core records frames with ts < `stop_us` and waits up to 3T for the first frame past it before it finalises
  (CC:7664-7671). Both clips then hold exactly slots k0 to k1−1 (R-new1).
- A cam0-only stop is as today.

**The frame index:** no change (CC:4639-4646). While both are locked, `llround(elapsed·fps)` gives k − k0, so a dropped
frame leaves the same hole index in both clips (PROBABLE).

### 6.3 Audio, timecode, names

- **Audio:** one WAV, the primary's, in cam0's folder (M5). It is trimmed to cam0's frame 0, which is cam1's frame 0
  on the grid (AudioRecordingSession.cpp:612-640). A cam1-only take has no audio in v1.
- **Timecode:**
  - In a take with both cameras and the lock locked, each frame's timecode comes from its slot time t_k plus the
    primary's `tc_offset_us`, passed on `record_start`. This needs a `RecordingClock(offsetUs)` constructor beside
    RC:36-41.
  - FreeRun timecode is then identical for each index on both clips, and jitter can never repeat or skip a number. The
    first-frame timecode of MLV, H.264 and ProRes follows the same rule.
  - Otherwise timecode is today's: equal unless a bin edge falls between the two first exposures (R3).
  - A time-zone change needs both Cores restarted (R-new5).
- **DNG identity:** both cameras write the same model and serial tags (CC:3800-3842). In v1, only the folder tells the
  clips apart (P21d).

### 6.4 Time left and drops

- **Time left divides by the camera count in `record_cameras`:**
  - WebUI: App:9376-9385, 9553;
  - HDMI REMAINING: MediaStatusBridge.cpp:381-383 multiplies its rate by the count, or it reads about 2× too long (U12).
- **Drops:** cam1's dropped frames show in the CAM1 pill, in `cam1.recording_dropped_frames` and in `journalctl -u
  apertar-core-cam1`.

## 7 Sync: the phase lock on one grid

### 7.1 Why the shipped lock cannot do it

`arm()` sets the datum to its own first frame (`originNs = referenceNs`, FPL:149), and the error is measured from it
(FPL:106-108). So two locked Cores share a rate, not a phase. Their offset is frozen at a random value in [0, T): 0-40 ms
at 25 fps. It is drawn again at every re-arm: an fps change (CC:7490-7496), a stop or reconfigure, a ramp grace, a
preview gap (S1).

Cinemate's law is the same (phase_lock_core.hpp:104, 120-125@63a08d5), so removing its role gate would not help (S2).

### 7.2 The grid

- **Clock:** `SensorTimestamp`, taken by the CFE at frame start in the kernel. Both processes read the same clock:
  CLOCK_MONOTONIC, equal to BOOTTIME on a Pi that never suspends (S3; kernel side PROBABLE).
  - Not FrameWallClock: it is a per-camera fit of the REALTIME offset (pipeline_base.h:181). Both fits estimate the
    same offset, but each adds its own fit noise (S13).
- **Period:** the exact rational of `recordingFrameRate(fps)` (RC:13-19): 25 gives 25000/1000, 23.976 gives 24000/1001.
  Use the same T for the grid, the frame index and the timecode (sync-critique "Missing" 9).
- **Slot and error:** k = round(ts·num / (10⁹·den)) and e = ts − k·10⁹·den/num, which lies in (−T/2, T/2]. Use
  `__int128` arithmetic.
- **Origin:** 0 by definition. The same fps gives the same grid in both Cores, so only `set_fps` and the mode need
  mirroring, and a restarted Core rejoins the grid by itself.
- **One lock, no new key.** When `fps_phase_lock` is on, the lock always uses the absolute grid. For one camera the grid
  is just which phase it locks to, and the same change is T27's fix. The key, the command and the default (off) stay
  as they are.

### 7.3 The actuator

T27 MEASURED the cause of the flicker (hardware-log.md:246-293):
- `{d, d}` pins make libcamera's IMX585 helper pick a new (VMAX, HMAX) point on its lattice. 40001 µs became 581 ×
  5112 instead of 550 × 5400.
- The 60 s take with the lock on had 10 holes and band steps of up to 8.9 %.
- In a model, 299 of 300 one-µs steps change HMAX (S4).
- For two sensors each lock would pick its own HMAX, so their row times would differ (L-new3).

| Fix | Where | What | Status |
| --- | --- | --- | --- |
| **A: VBLANK-only pins** | lock pin CC:8948; pre-roll pin CC:8955; the base pin CC:2404-2415 *whenever the lock is on* (S8) | `{d, d+1}`: min ≠ max takes the helper's base path (cam_helper_imx585.cpp:126-132), which floors to whole lines and keeps HBLANK 0 (cam_helper.cpp:87, 96-97, 120-121). No libcamera change. HBLANK stays 0, so a foreign HBLANK = min write is a no-op (§2) | CONFIRMED in code |
| **Q: even-VMAX quantiser** | FPL:127-139 | carry the remainder: q = r + carry; V = 2·round(q / 2H); carry = q − V·H; push d = ceil((V + ½)·H). This gives the exact mean period and exact FrameDuration metadata. The half line matters: a whole-µs pin on a line boundary can floor to V−1 in double arithmetic (S6). H = (width + HBLANK) / PIXEL_RATE comes from the camera's own subdev, matched by of_node (§3.2) | design |
| **E: driver rewrites SHR on VBLANK** | DRV:3506-3524 | after the VMAX write, also write `shr = (vmax − exposure) & ~1U`, mirroring :3478-3487. Today an unchanged exposure is not re-sent, so every 2-line push moves the integration by 14.8 µs: 0.074 % at 20 ms, 1.5 % at 1 ms (S5). Also move the four per-frame `dev_info` lines (:3495, :3499, :3518, :3536) to `dev_dbg`. Option: bracket VMAX and SHR with the sensor's register hold, if the datasheet confirms it (no hold is used today, S5) | CONFIRMED (cause); fix: design |
| saturation check | CC:8841-8842 | match `echoed[0]` against `recentPhaseLockPins_`. Today it requires [0] == [1]. At a mode's top fps, `{d, d+1}` can collapse to min == max (ipa_base.cpp:1788-1792); the check must expect that (S4) | design |

**Steps:** at 891 MHz a line is 7.407 µs and the VMAX quantum is 2 lines, 14.815 µs (D5b; 17.78 µs at 720 MHz).
Clear HDR's VMAX parity is UNCONFIRMED (S6). If it needs multiples of 4, the quantum is 29.6 µs; test 1.9 settles it.

### 7.4 The loop

- **Steady state:** the shipped PI is unchanged (FPL:119-124: kp 0.06, ki 0.0015, deadband 6 µs, clamp 150 µs). A 15 µs
  deadband doubled the skew in the model.
- **Acquisition, in preview only:** when not locked and |e| > 1 ms:
  - lengthen one request by (−e − Σ in-flight (V_i·H − T)) mod T, rounded to an even VMAX;
  - then hold the servo for D + 2 frames.

  In the model, |e| falls below 50 µs within about 13 frames (0.5 s) at D = 11. The PI alone needs 230-350 frames
  (10-14 s), with 1.7-2.8 ms of overshoot (X-new2).
- **Never stretch while recording.** A stretch of s advances the time index by s/T (CC:4642-4645). Above T/2 it leaves
  a phantom hole and breaks slot = index + k0 (S9). In a take only the PI acts: 5-10 s, about 2 ms of overshoot.
- **`arm()`** resets the integral, the request and `lastPushed`, never the grid. The gap counting and the half-frame
  re-arm (FPL:88-117) are no longer needed.
- **Additions:**
  - anti-windup by conditional integration;
  - a `locked` state: |e| ≤ 100 µs for 25 frames;
  - a per-frame trace `slot ts err V` behind `APERTAR_PHASE_LOCK_LOG` (CC:8856).
- **Dead time D:** the CC comment predicts N+2 / N+3 frames (CC:9628-9635). MEASURED `lag_frames=7` at 1080p SDR on
  exFAT (hardware-log.md:496), with N = 6 PROBABLE. Clear HDR: D ≈ 11 (ESTIMATE, N = 10). T56 measures it.

### 7.5 Accuracy (ESTIMATE)

The numbers come from the host models in `sim/` (`synth/more_sim.py`, re-run tonight). The model uses the shipped law,
dead time D, Gaussian frame-start jitter σ = 3-10 µs per sensor, the 2-line step and Q.

| Mode (891 MHz) | D | One sensor vs grid, max / RMS (µs) | Between the sensors, max / p99 / RMS (µs) | VMAX pushes per 1000 frames |
| --- | --- | --- | --- | --- |
| 4K SDR 12-bit 25 fps | 7 | 14-22 / 5-10 | 30-36 / 20-31 / 8-12 | ~100 |
| 4K Clear HDR 16-bit 25 fps | ≈11 | 18-33 / 8-13 | 45-46 / 31 / 12-13 | 86-109 |
| 24 fps (Q alternates 5624/5626) | 11 | 24-28 / 7-8 | 36-41 / 26-28 / 10-11 | ~900 (each a 2-line step, harmless after fix E) |
| 50 fps SDR | 7 | 21-23 / 7-8 | 35-38 / 24-26 / 10 | ~107 |
| Clear HDR 30 fps (the mode's maximum) | | saturates: the lock can only lengthen frames. It locks only if this sensor runs fast against the Pi's crystal (sync-critique "Missing" 8) | no sync otherwise | |

**What the figures mean:**
- At 50 µs the skew is 6.75 lines, 0.125 % of a frame, 99.75 % exposure overlap at 1/50 s, and 0.19 px for a pan of
  one frame width per second. It does not grow with take length.
- Unsynced, the drift is Δ·t: 0.9 ms per 10 min at 1.5 ppm, 18 ms at 30 ppm.
- The sensor's ppm against the Pi is UNCONFIRMED: the logged endpoints do not give the KB's 1.5 ppm (r6b).

**Not in the budget:**
- coupling between the two CFE frame-start interrupts. If one CPU serves both, the order flips frame to frame: a bias
  plus a bimodal skew (sync-critique "Missing" 1). Test 2.2 looks for two peaks. Giving the two interrupts separate CPUs
  would be a system setting for Patrik.
- a constant CFE latency difference;
- a varying D (frame skips shift the request-to-frame mapping);
- the 1 µs timestamp quantisation.

### 7.6 Interactions

| Event | With the grid lock |
| --- | --- |
| fps change (mirrored) | release, a grace of max(10, N+6) frames (CC:9636-9645), then arm on the new grid and stretch in preview (~0.5 s). Both Cores land on the same grid without a message |
| T31 speed ramp | released for the ramp; the two ramps are not slot-aligned and the cameras are not synced during the ramp. Allowed in two-camera takes; refused in cam1-only takes (cam1 busy, §4.3; P20). v2 could tie ramp steps to slots. Ramp pins are still `{d, d}` and hop HMAX: that is a T31 matter |
| Reconfigure (Clear HDR, format, colour profile, ladder rung) | the stream restarts with a random phase and re-acquires. `locked` is false meanwhile; a take then starts unsynced and says so |
| Stills | photo mode releases the lock (CC:8789). A still in video mode skips the pin (CC:8937-8947), and the lock re-acquires after it. Stills are cam0 only |
| Storage pre-roll | primary only, with `{p, p+1}` |
| Core restart mid-shoot | the restarted Core waits for idle (§3.4), then re-acquires the same grid on its own in about 1.5 s. Its HBLANK write lands on a sensor at HBLANK 0, so it is a no-op |
| Audio | unchanged: everything is on the same kernel clock, and the video now follows it exactly |
| NTP | a slew affects both locks equally and raises the push rate; a step moves only REALTIME, so only the per-take timecode offset |
| Live check | the relay already reads cam1's `preview_frame` `timestamp_us` (App:14513). The primary pairs it with its own frames by slot and publishes `cam1.skew_us` (median of the last second) and `cam1.locked`. The CAM1 pill shows "SYNC 12 µs" or "NOT SYNCED" |

Rule: when two Cores run, both run the lock, or the take is unsynced and says so. The lock's default stays off. Patrik
switches it on once; the setting is forwarded and saved in both Cores.

**Alternatives kept in reserve:**
- **Hold policy:** align in preview, no pushes in the take. It works at 25/30/50/60 fps, or at 24 fps by holding the
  lattice's exact 625 × 4950 point (S10). The cost is drift Δ·t, and at 24 fps HBLANK ≠ 0 during the take. Use it if
  Part 1 shows a cost from VBLANK pushes.
- **Hardware XVS:** cam1 as `internal-follower`, wired to cam0. It gives sub-line accuracy, for row-exact stereo. Whether
  the Waveshare board routes XVS is UNCONFIRMED, and whether the leader drives XVS is unsettled (S14: the driver's
  comments contradict each other).
- **libcamera "sticky HMAX":** later, only if exact lock-off rates at a fixed HMAX are wanted.

## 8 API delta

| Kind | New | Copies |
| --- | --- | --- |
| Core option | `--camera` | `--socket`, `--web-port` (src/main.cpp:32-37) |
| Script env | `APERTAR_CAMERA`, `APERTAR_WEB_PORT` | `APERTAR_SOCKET_PATH` (start-apertar-core.sh:6) |
| UI.conf | `previewSource` | `externalMonitorMode` |
| UI.conf | `recordBothCamerasEnabled` | `recordAudioEnabled` |
| Commands | `set_preview_source`, `set_record_both_cameras_enabled` | `set_external_monitor_mode`, `handleUiToggle` |
| State | `ui.preview_source`, `ui.record_both_cameras_enabled`, `cam1`, `record_cameras`, `camera_id`, `camera_port`, `fps_phase_lock_locked` (plus the existing lock telemetry, App:9426-9430, in get_state) | `ui.external_monitor_mode` (App:9617), `ui.record_audio_enabled` (:9637) |
| `record_start` fields | `cameras`, `start_us`, `clip_name`, `tc_offset_us` (reply: `first_slot`) | `audio_enabled` (App:14228-14233), `preview_clip_name` (:12803) |
| `record_stop` field | `stop_us` | |
| Files | `apertar-core-cam1.service`, `~/apertar-hardware-cam1.conf`, `~/.config-cam1/` | |

There is no new key for the grid lock, no role flag and no new action in v1.

## 9 Steps T56-T70

The numbers start at T56: playback used T46-T54, and T55 is the Clear HDR 16-bit preview tutorial.

Each step leaves the single-camera rig working. Its last check is always "with no cam1 configured, a take, Clear HDR
and the WebUI behave as before". Steps T57-T58 (the lock) and T59-T67 (the plumbing) do not depend on each other.
Patrik runs every sudo, restart, reboot and take. The work happens on a local branch on the Pi (§12, Q24).

| Step | What | Files | Check (prediction) | 1 sensor | Size |
| --- | --- | --- | --- | --- | --- |
| **T56** Measure first | no code (§10 Part 0) | none | the numbers that set the lead, D, σ, and whether a syncfs or a second writer costs a take frames | yes | 0 lines, 3 h |
| **T57** The lock on one grid | grid error, Q, stretch, anti-windup, `locked`, trace; pins A; saturation check; lock state in get_state; the KB simulator gains dead time, jitter, the 2-line step, Q, a grid case and a sensor pair | FPL, CC:8770-8861, 8934-8958, 2404-2415; App (state); `working/tools/phase_lock_sim.cpp` | host: the simulator's checks pass, the new cases match `sim/`. Pi 1.1, 1.2, 1.5, 1.8 | yes | 300 lines (Core ~150, simulator ~150), 7 h |
| **T58** Driver SHR, then the T27 retake | fix E and `dev_dbg` | imx585.c (driver branch), DKMS rebuild | Pi 1.3, 1.4, 1.6, 1.7, 1.9 | yes | 10 lines, 3 h |
| **T59** Camera by port, subdev by of_node | `--camera`, the env vars in the start script, the pick at both sites, the no-sensor exit in `main()`, of_node for WDR, knobs and probe, `camera_id`/`camera_port`, `{cam}` from the port | src/main.cpp, App.hpp, CC.cpp/.hpp, scripts/start-apertar-core.sh | no env: the same "Registered camera" line, take and Clear HDR as before. `APERTAR_CAMERA=cam1`: exit 0 in under 1 s with no libcamera line, cam0 undisturbed | yes | 100 lines, 3 h |
| **T60** The secondary's role and unit | the role gate (§3.3), the allowlist, POST refusal, the start wait, the unit, the hardware file | App.cpp/.hpp, CC (syncfs), config/apertar-core-cam1.service, config/apertar-hardware-cam1.conf | primary stopped, `--camera i2c@88000` with the test line below: no trigger, GPIO, PCF or power-button lines; the "controls:" line names the cam1 file; `format_media` and the 7 POST routes refused; MJPEG on :8001 works; with the standby flag files present, no restore is logged; a preset with `standbyTimeoutSeconds=60` and `photoModeEnabled=true` leaves cam1's UI.conf unchanged and cam1 awake after 2 min. After install: a boot leaves the unit `inactive` (exit 0); a primary restart does not loop | yes | 150 lines, 4 h |
| **T61** The relay | ControlClient, the wrapper, command classes, idle, busy window, presets and resync, the compare, `cam1` state, orphan stop, live skew | src/ipc/ControlClient.hpp/.cpp (new), App.cpp/.hpp, CMakeLists.txt | with the simulated cam1 (below): setters land in under 1 s; `offline` only after cam1 exits; resync after a restart and after a sat-out take; `storage_preroll` on the primary never changes cam1's fps; `set_resolution` then REC within 1 s is refused "One moment."; a symlink to the primary's socket is refused; with no cam1 configured, nothing changes | yes | 450 lines, 10 h |
| **T62** Start and stop on one slot | `start_us`, `stop_us`, `clip_name`, `tc_offset_us`, `first_slot`; exclusive mkdir; timecode from the slot | App.cpp, CC.cpp/.hpp (7507, 7631, 7649, 7664-7671, 9261-9265), RecordingClock.hpp | primary alone: `start_us` = now + 500 ms gives a first frame in [T, T + one period); `stop_us` gives the exact frame count; without the fields, frame 0 is within one period of the press, as today; a hand-made `<next>_cam1` folder makes the take skip that number | yes | 100 lines, 4 h |
| **T63** The preview-source setting | the quartet (§5.1). It comes before T64, whose follow-the-preview policy reads it | App.cpp, SettingsBridge.cpp/.hpp, WCP | the five labels round-trip through UI.conf, `ui.preview_source`, SettingsBridge and the select; `pip_cam0` is refused | yes | 120 lines, 4 h |
| **T64** Take coordination | which cameras, `recordBothCamerasEnabled`, `record_cameras`, the cam1-only take (Sound Recorder pattern), `cam1RecordingActive()` at every busy site, the writes-pending and busy refusals, failures, Sound Recorder and photo rules, time left in Core | App.cpp/.hpp | with the simulated cam1: policy, override, `record_cameras`; a cam1-only take lights the tally; cam1 killed mid-take shows `lost`, cam0 rolls, the tally goes off in a cam1-only take; orphan stop after a primary restart | yes | 250 lines, 7 h |
| **T65** The second picture | second client (explicit path at all sites, `setRecording`), item, renderer in `ensureWindow`, the two renderer lines, CB parses `cam1` | UI: src/main.cpp, CB, PWR, ExternalMonitorManager.cpp/.hpp, EMW | no cam1: journal and drops as before. Through a symlink to the primary's socket, cam0's frames fill the second item (every client gets every frame, ControlServer.cpp:175-196); a 3-minute take with both clients drawing: drops compared with T56 | yes | 150 lines, 5 h |
| **T66** HDMI layouts | five sources, frames, divider, tags, CAM1 pill, REMAINING move, no-signal states, the photo rule, transforms on both panes, REMAINING × camera count | EMW, MediaStatusBridge.cpp | all five sources through the symlink; fallback within 1 s against the simulated cam1, which sends no frames | yes | 220 lines, 6 h |
| **T67** WebUI | second `<img>`, layouts, select, pills, NEXT TAKE, REC label, CAM1 badge, test hook | WCP, App.cpp | `?cam1port=8000` on a laptop and a phone: layouts at 390 px and landscape, pills, REC label, badge; the stream stops while hidden | yes | 200 lines, 5 h |
| **T68** The second IMX585 | Patrik: sensor on the MIPI1 connector, config.txt line, reboot, enable the cam1 unit | config.txt | §10 Part 2: enumeration, M1, M2, sync 2.1, 2.2, 2.4 | no | 0 lines, 3 h |
| **T69** Dual takes | fixes only | as found | §10 Part 2: the combo ladder (M5), 2.3, every policy and source, drops per camera, the WebUI in Both during a take (P24), boot order (cam1's "Registered camera" after the primary's socket bind) | no | 0-20 lines, 4 h |
| **T70** Touch UI (optional) | CameraPage panes, Settings rows | CameraPage.qml, SettingsPage.qml | it builds; there is no touch screen to try it | build only | 150 lines, 4 h |

**Test lines (P9).** Reuse these exact lines; anything shorter can steal the primary's socket or write its config.
`--simulate` accepts takes (CC:11847-11857) but never has writes pending (CC:12331-12335), so that check waits for T69.

```
# simulated cam1 (T61-T66), next to the running primary
XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf \
APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0 \
/home/pi/ApertarCore-build/apertar-core --simulate --camera cam1 \
  --socket /tmp/apertar-core-cam1.sock --web-port 8001 --media /media/RAW

# real secondary on cam0's sensor (T60), with the primary STOPPED
XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf \
APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0 \
/home/pi/ApertarCore-build/apertar-core --camera i2c@88000 \
  --socket /tmp/apertar-core-cam1.sock --web-port 8001 --media /media/RAW
```

## 10 Verification on the Pi, with predictions

### Part 0: measure first (T56, no code, no take running unless stated)

| # | What | Prediction | Decides |
| --- | --- | --- | --- |
| 0.1 | Read-only: `systemctl cat apertar-core`, `v4l2-ctl --list-devices`, the "Registered camera" line, `id` | as r5: one `rp1-cfe`, two `pispbe`; the live unit's full text | the cam1 unit's text |
| 0.2 | Frame-interval log: a Python socket client records `preview_frame` `timestamp_us` (every client gets them) in preview, lock off, 25 fps and 24 fps | σ of the interval a few µs (UNCONFIRMED); 40000 / 41667 µs means | σ in the model |
| 0.3 | HBLANK stomp: with 0.2 logging at **24 fps** (lattice HMAX 625), run `rpicam-hello --list-cameras` ten times, 3 s apart. Read `v4l2-ctl --get-ctrl=horizontal_blanking` before | hblank 524 before. One interval of about 36.7 ms (5.0 ms short) per call, then 41.7 ms again; the phase steps by 5 ms each time. At 25 fps: no effect (hblank already 0, L-new2) | the rule "no manager start during a take" |
| 0.4 | Dead time D in Clear HDR: lock on (today's lattice lock), step `set_fps` 25 → 24.99, count frames until the interval moves | 11-12 frames (ESTIMATE); 7 at 1080p SDR (MEASURED) | D in the model |
| 0.5 | `sync -f /media/RAW` during a 4K Clear HDR take, three times | some queue drops (CC:4314-4318 records 782 in 3 min from a syncfs in the take) | the secondary's fsync rule |
| 0.6 | A second writer: `fio --rw=write --bs=1M --direct=1 --rate=150m` (a lossless 4K stream) to a second folder during a 3-minute take | drops rise above the baseline (ESTIMATE) | whether 2× 4K lossless is worth trying |
| 0.7 | `record_start` latency × 10: press to first frame (journal) and press to the reply | 0.3-0.8 s with audio on (PROBABLE) | the start lead |
| 0.8 | Core RSS in preview and in a take | | the RAM budget for two Cores |

### Part 1: one sensor (T57-T58)

Conditions as C0102/C0103: 4K Clear HDR 16-bit, 25 fps, ISO 800, 20000 µs, 4000 K, static scene. The trace from T57
gives per-frame slot, ts, err and V.

| # | Test | Prediction | Settles |
| --- | --- | --- | --- |
| 1.1 | Grid lock as a meter (`APERTAR_PHASE_LOCK_DEADBAND_US=100000`); `v4l2-ctl --get-ctrl=horizontal_blanking,vertical_blanking` after 1 s, at 25 and 24.99 fps | hblank 0; vblank 3200 at 25 fps, 3202 or 3204 at 24.99 fps (the lattice gave 217/2912 and 308/2802, MEASURED) | fix A |
| 1.2 | Lock off, fixed pin: interval spread; then one step | σ a few µs; D ≈ 11 | the model |
| 1.3 | 24 fps, lock on, 1 ms shutter; band step in the centre; `dmesg \| grep -c imx585` per take | before E: alternating steps of about 1.5 % and one log line per push. After E: under 0.1 %, about 0 lines | fix E |
| 1.4 | 60 s take, lock off; then 60 s, grid lock on (E + A + Q) | no holes in either. Band step with the lock about as without (max ≤ 0.3 %). hblank 0 throughout. VMAX changes on 8-25 % of frames. Against the grid: max ≤ 40 µs, p99 ≤ 25 µs, RMS ≈ 10 µs | any holes: hold policy. Twice the error: re-measure D and σ |
| 1.5 | Acquisition: toggle the lock; 25 → 24 → 25 fps in preview | under 50 µs within about 13 frames | the stretch |
| 1.6 | 10-minute take (T27 step 5.2, never run) | the error does not grow; 0 holes; WAV length = frame count | long takes |
| 1.7 | During a timesyncd slew, every 10 s: REALTIME − BOOTTIME and BOOTTIME − RAW | the first constant to ±2 µs, the second moves at the slew rate | the KB dispute (p2-phaselock-core.md:64) |
| 1.8 | Restart Core and let it re-lock | the same bounds on the same absolute grid | rejoining without messages |
| 1.9 | Clear HDR VMAX parity: pin a duration that gives VMAX 5402; measure the period | 40014.8 µs if 2-line steps hold; 40029.6 µs if Clear HDR needs 4 | the Clear HDR quantum |
| 1.10 | 24 fps during an fps-change grace: read HBLANK | 0 with the base pin VBLANK-only (S8) | fix A on the base pin |

### Part 2: two sensors (T68-T69)

| # | Test | Prediction |
| --- | --- | --- |
| 2.0 | Enumeration after the cam1 line and a reboot: `v4l2-ctl --list-devices`; the journal; `dmesg \| grep imx585`; CSI-2 error counters (`rp1_cfe.track_csi2_errors=1` is on) | two `rp1-cfe`; "Registered camera …i2c@70000… ISP device /dev/media3" in both Cores' journals; both sensors "internal-leader"; no CSI-2 errors at 891 MHz (else 720 on both) |
| M1 | Core stopped: two `rpicam-vid` at 25 fps, 3 min, (a) 2× 4K SDR 12, (b) 2× 4K HDR16, with `LIBCAMERA_LOG_FILE` per camera; `working/tools/libcam_stages.py` | BE median per camera (a) 11-16 ms, (b) 15-22 ms (ESTIMATE). Above 20 ms in preview alone, 2× 4K recording is not viable |
| M2 | The stomp with two sensors at 24 fps, lock off: restart cam1's Core during cam0's preview | one short interval on cam0 per start (0.3's size). With the lock on in both: none |
| 2.1 | Both locks off, 10 minutes, per-frame ts from both | s_k = tsA − tsB drifts linearly at Δ ppm, |Δ| ≤ 50 ppm (ESTIMATE). Δ decides whether the hold policy is usable |
| 2.2 | Both on the grid lock, pairs by slot | histogram of s_k: max ≤ 55 µs, p99 ≤ 40 µs, RMS ≤ 15 µs; median = the CFE bias (expect |b| < 10 µs); flat over 30 minutes; hblank 0 on both. Two peaks or a gap at 0: interrupt coupling (§7.5) |
| 2.3 | A take with `start_us` and `stop_us` | both clips: the same `first_slot`, the same frame count, the same timecode at each index; one WAV in cam0's folder |
| 2.4 | Restart cam1's Core in preview | cam0 shows no phase step and hblank stays 0; cam1 is locked within about 1.5 s |
| 2.5 | Optional: scope both XVS pins (first check that the leader drives XVS at all, S14) | agrees with s_k within the CFE jitter |
| M5 | 3-minute takes ×3 per combo, `buffer=frames` on cam1, in this order: 2× 1080p, 2× 4K SDR 12 lossless, 2× 4K SDR 12 uncompressed | loss under 0.5 %, 2-10 %, over 10 % (ESTIMATE, r4) |

## 11 Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| 1 | A manager start costs a running take a frame at min_hmax and a phase step (L2, L3) | VBLANK-only pins keep HBLANK 0 while the lock is on; both Cores wait for idle before starting; the busy window; no restarts during takes; 0.3 and M2 measure it. If M2 shows a cost that matters: a libcamera-fork patch that skips the HBLANK write when another process holds the media lock, or one CameraManager kept across reconfigures (sync-critique "Missing" 3) |
| 2 | First-match subdevs send cam1's WDR to cam0 (C4) | of_node binding in T59, before any second Core runs |
| 3 | Load: one RP1 link, one SDRAM, one BE engine, 4 GB | T56 proxies, M1, M5; cam1 on frames; v1 one mode for both; 2× 4K HDR16 out |
| 4 | One NVMe and a syncfs per stop (CC:4744) | the secondary fsyncs its own files; both stop on one slot; 0.5 and 0.6 measure it |
| 5 | Settings drift between the Cores | compare every field each second; resync when idle; refusals set `cam1.message` |
| 6 | A take silently records one camera | state words, CAM1 pill, REC label; a journal line per take on both Cores |
| 7 | The VBLANK-only lock costs holes or exposure steps | fix E first; test 1.4; the hold policy as fallback |
| 8 | The model misses interrupt coupling or a varying D | test 2.2 histogram; CPU affinity as a system fix |
| 9 | GUI-thread cost of a second import and draw | the `isVisible` guard; second client only while `cam1` exists; the recording fps cap on both; drops compared in T65/T66 |
| 10 | One driver mode table | 891 MHz written on both lines; 720 on both if cam1 logs CSI errors |

## 12 Questions for Patrik, with defaults

| # | Question | Default |
| --- | --- | --- |
| Q1 | Record policy | follow the preview, as Cinemate. With the preview on Cam 1, the next take records cam1 only; the REC label says so. Alternative: `recordBothCamerasEnabled` on |
| Q2 | Preview default | Both |
| Q3 | cam1 not ready or refusing at REC | cam0 rolls alone; the pill says why |
| Q4 | Audio | one WAV, cam0's; none in cam1-only takes in v1 |
| Q5 | Link frequency | 891 MHz on both; 720 on both if cam1 logs CSI errors |
| Q6 | Per-camera resolution or format (4K + 1080p) | identical in v1; v2 |
| Q7 | Settings during a cam1-only take | exposure only |
| Q8 | The :8001 page | read-only |
| Q9 | NEXT TAKE also steers the hardware REC button | no: WebUI presses only |
| Q10 | Sync tolerance | the software grid, about 50 µs. XVS wiring only for row-exact stereo |
| Q11 | Lock in takes: track or hold | track |
| Q12 | Driver fix E on the driver branch (you run the DKMS rebuild) | yes |
| Q13 | Speed ramps in two-camera takes | allowed, unsynced during the ramp; refused in cam1-only takes |
| Q14 | Clear HDR 30 fps in dual (cannot lock, unless the sensor runs fast) | allowed, flagged "NOT SYNCED" |
| Q15 | Mode ladder in dual | cam1 follows the primary's resulting mode; its own ladder off |
| Q16 | Timecode from the slot (identical on both clips) | yes |
| Q17 | Presets carry `recordBothCamerasEnabled` | yes, like `recordAudioEnabled` |
| Q18 | A hardware button that cycles the preview source | not in v1 (the WebUI select covers it) |
| Q19 | DNG serial and camera label per camera | unchanged in v1; the `_cam1` folder tells them apart |
| Q20 | Which physical connector is MIPI1 on the Waveshare board | read the silkscreen; else plug, boot, read which I2C node registers |
| Q21 | The second sensor's model | a second IMX585 (every setting stays valid on both) |
| Q22 | timesyncd on shoots | fine: it raises the push rate during slews, not the skew |
| Q23 | The lock on in dual | you switch it on once; it is forwarded and saved in both |
| Q24 | Branch | a local branch `dual-sensor` on the Pi, cut from what the Pi runs when T57 starts (today `drop-frames` 31d5418), never pushed until you merge it |
| Q25 | Who types | tutorials per Rule 1 (you type, Claude tutors), unless you say "you do this one", as for T31-T34 and T47-T51 |

## 13 Verification table: what the design rests on

| Claim | Where used | Verdict | Source |
| --- | --- | --- | --- |
| Two processes each own one camera (CFE k + BE k, lockf per handler) | §2, §3 | CONFIRMED in code; run UNCONFIRMED | L1, M-C9 note |
| A manager start writes HBLANK = min on every sensor; the IPA restores it at the next frame | §2, §3.4, §7.6 | CONFIRMED in code | L2, L3, S7 |
| One frame at min_hmax; a 5.0 ms step at 24 fps on the lattice; none at HBLANK 0 | §2, test 0.3 | ESTIMATE (model) | L3, S8 |
| Driver mode tables module-wide; link and lanes must match; Clear HDR may differ at 891 MHz | §2 | CONFIRMED | D1a-c |
| cam1's overlay defaults to 720 MHz | §2, T68 | CONFIRMED | X3, D4 |
| VMAX is forced even: 14.815 µs steps at 891 MHz | §7.3 | CONFIRMED | D5b (refuted r4's "one line") |
| The driver does not rewrite SHR on VBLANK | §7.3 | CONFIRMED | D-new1, S5 |
| `{d, d+1}` takes the base helper path; `{d, d}` the lattice | §7.3 | CONFIRMED; emulation reproduces the T27 readbacks | S4, `sim/lattice_sim.py check` |
| The base pin re-engages the lattice in every release unless it is VBLANK-only too | §7.3 | CONFIRMED | S8 |
| The shipped lock anchors at arm; two locks share only a rate | §7.1 | CONFIRMED | S1, S2, R8 |
| SensorTimestamp is one clock for both processes | §7.2 | CONFIRMED (libcamera); kernel PROBABLE | S3, M9 |
| The first recorded frame is the first with ts ≥ recordingStartBootUs_ | §6.2 | CONFIRMED | R2 |
| A mid-take stretch leaves a phantom index hole (not the FrameDuration test) | §7.4 | CONFIRMED | S9 |
| Core's WDR/knob writes go to the first imx585 in readdir order | §3.2 | CONFIRMED | C4, C-new1, X-new1 |
| The socket path is unlinked then bound; a web-port failure exits 1 | §3.1, test lines | CONFIRMED | C1, C2 |
| XDG_CONFIG_HOME moves camera_settings, mode_ladder, UI.conf and the store notes together | §3.1 | CONFIRMED (not the hardware file, presets, ProRes cache) | C5, X11 |
| Pre-roll and trim env switches exist; pre-roll thread and power button need code | §3.3 | CONFIRMED | C7, C8 |
| apply_preset writes UI.conf keys (standby, photo mode) | §4.4 | CONFIRMED | P1, R5 |
| Every client gets every broadcast, preview fds included | §4.1, T65 | CONFIRMED | R7, U-new1 |
| The flat parser stops at the first `}` | §4.1 | CONFIRMED | R6, P15 |
| An `<img>` from :8000 loads :8001's MJPEG; a fetch gets 403 | §5.3 | CONFIRMED (Core); browser PROBABLE | U10, U11 |
| A bridge swap keeps the old frame; `render()` ignores visibility | §5.2 | CONFIRMED | U5, U-new7 |
| The HDMI picture is EMW (`hdmi_external_only` default true) | §5.2 | CONFIRMED (default); rig value PROBABLE | U6, K3 |
| Cinemate's sync is not real; its join is dead code | §1 | CONFIRMED | M6, M7 |
| Accuracy 30-55 µs between sensors | §7.5 | ESTIMATE (uncorrelated jitter only) | S12, `sim/` |
