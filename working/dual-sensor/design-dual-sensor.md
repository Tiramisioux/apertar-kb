# Dual sensor on Apertar: design (v2.1, 2026-11-04)

Two IMX585 on one Apertar: two Cores, one picture and one REC button, frames on one grid by the phase lock.
This is the plan. Its sources are in this folder:
- the reader reports r1-r6c and their claim check (`claim-check.md`, 82 claims);
- the sync synthesis and its critique;
- the panel's three designs, the merged v1 and its critique.

Every change from a critique is listed in `changes-from-critique.md`, and so is every change from the verification
pass (its §5: six reviewers, 70 findings, each re-checked in code) and from the re-check of this draft (its §6: five
reviewers, 59 findings). Nothing ran or changed on the Pi except the read-only reads in r5.

**Refs.** Core `drop-frames` 31d5418 (what the Pi ran when the plan began): `App` = src/ApertarCoreApp.cpp, `CC` =
src/camera/CameraController.cpp, `FPL` = src/camera/FramePhaseLock.hpp, `RC` = src/audio/RecordingClock.hpp, `WCP` =
src/web/WebControlPage.cpp. UI c153c33: `EMW` = qml/ExternalMonitorWindow.qml, `PWR` = src/PreviewWindowRenderer.cpp,
`CB` = src/ApertarControlBridge.cpp. libcamera `apertar` 6b0b49f3 (the Pi's base 7e9fef0b has the same helpers). Driver
`DRV` = imx585.c@cd548ef (what the Pi runs). Cinemate d6cc93e, cinepi-raw 63a08d5. Claim ids (L2, X7, U9, …) are in
`claim-check.md`; S1-S14 in `sync-critique.md`; P1-P25 in `critique-merged-v1.md`.

The Pi now runs Core `9b5ea14` (`drop-frames`, not in the Mac clone). Its diff from 31d5418 touches only the WebUI
(WCP), the controls (ControlsModel.hpp, HardwareConfigText.hpp) and a `test_input` command; nothing in capture or
record. The refs stay at 31d5418, so re-grep each anchor on the Pi tree before editing: App and WCP line numbers may
have moved.

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
   - The cost: with the preview on Cam 1 or PiP Cam 1, every press, the camera's own button included, records cam1
     only, with no WAV in v1. The HDMI status pill and the REC label say so.
   - The primary picks one start slot and one clip number for both cameras: cam1's folder is cam0's name plus `_cam1`.
   - One WAV, in cam0's folder.
   - Both cameras start on the same frame slot and stop on the same slot.
   - If cam1 is missing, offline, refused, lost or in standby, cam0 rolls alone and the pill says why. A press that
     asks for cam1 alone (NEXT TAKE CAM1, `cameras=cam1`) is refused instead of recording cam0.
   - While cam1 is still writing, or applying a change, REC is refused for a moment, a cam0-only press too while cam1
     is busy (§6.1).
6. **Sync: the existing phase lock, on one absolute grid.** Each Core locks its frames to slots k·T on the kernel clock
   both read (SensorTimestamp), so no message is needed between them. Three more changes make it work:
   - the lock's frame-length pushes change VBLANK only: pin `{d, d+1}` instead of `{d, d}`;
   - an even-VMAX quantiser smooths the 14.8 µs steps;
   - the driver rewrites SHR when VBLANK changes.

   The same changes fix T27's flicker on one sensor, so they are tested first.
7. **Accuracy (ESTIMATE):** about 30-46 µs maximum between the sensors in the model, about 10 µs RMS; test 2.2
   allows 55 µs. That is under 0.2 % of a 25 fps frame, and it does not grow with take length.
8. **Platform rules:**
   - Both overlays get one link frequency and 4 lanes, because the driver's mode table is module-wide (D1b). Use 891
     MHz on both; cam1's line must say so, since the overlay default is 720 (X3). The fallback, 720 MHz on both,
     caps 4K Clear HDR 16-bit at 25.000 fps on both sensors (§2).
   - Never start or reconfigure either Core while a camera records: each manager start writes HBLANK on the other
     sensor (L2). The one exception is a primary restarted or crashed during a cam1 take, which starts at once
     (§3.4): with cam1's lock off and HBLANK ≠ 0 (24 fps, for example), one frame of that take runs short and dark at
     min_hmax (L3), and the phase steps.
   - v1 runs both cameras in one mode. 2× 4K Clear HDR 16-bit will not fit; 2× 1080p and 2× 4K SDR 12-bit lossless are
     the targets (r4 Q5).
9. **Steps T56-T70.** Everything up to T67 runs with the one sensor on the rig today: the T56 measurements, the lock
   fix and the T27 retake (T57-T58), then the plumbing against a simulated cam1. T57 comes first, because the relay's
   live skew and the one-slot start use its grid. T68 needs the second sensor.
10. **Size:** about 2,600 lines (Core ~1,900 with the WebUI, UI ~430 plus ~150 for the optional touch UI, driver ~10,
    KB simulator ~150) and about 83 hours. The API grows by 23 names and 4 files, plus one test-only env (§8).

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
| cam1's overlay line names 891 MHz itself: `dtoverlay=imx585,link-frequency=891000000` | the overlay default is 720 (X3). 891 MHz streams with a "DPHY datarate out of range" warning (hardware-log.md:963). If cam1 logs CSI-2 errors, move **both** to 720. **The cost of 720:** HMAX 660 (DRV:293), an 8.889 µs line and a 17.78 µs VMAX quantum. The module-wide table then caps 4K Clear HDR 16-bit at 25.000 fps, and 4K SDR 12-bit and 1080p binned at 50.000 fps, on both sensors, cam0 included. At those rates the lock can only lengthen frames, so 25 fps Clear HDR (the Part 1 condition) and 50 fps lock only if the sensor runs fast against the grid clock, as Clear HDR 30 fps at 891 MHz (§7.5). Clear HDR 30 fps is gone. The dual targets at 25 fps (2× 1080p, 2× 4K SDR 12-bit) keep 2× headroom. The §7.5 figures are for 891 MHz | CONFIRMED; cam1 at 891 UNCONFIRMED |
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
    part of the libcamera camera id (r5, CONFIRMED on the Pi).
  - Any other value names the I2C node itself: the `/proc/device-tree` node whose path ends in it. Its port is the
    `__symbols__` entry that resolves to that node, and its camera is the one whose id contains the node.
    `--camera i2c@88000` therefore runs a test secondary on cam0's sensor, with cam0 as its port. A value that matches
    no node exits 0, like a missing sensor.
  - Both pick sites change: the session (CC:7262-7265) and the probe (CC:7063-7066).
  - The primary prefers cam0's port, else today's rule, so a one-sensor rig on cam1 keeps working.
  - The secondary takes its own port or exits. It never falls back to `front()`.
  - If cam1's acquire fails with EBUSY (a dead cam0 let the primary take cam1, P16), the secondary logs one line and
    exits 0.
- **Subdevs:** `openImx585Subdev` (CC:6875-6892) takes the first imx585 subdev. Resolve the Core's I2C node once (the
  `__symbols__` lookup for cam0 and cam1, the node itself for a node value) and give it to `openImx585Subdev`, which
  then returns the imx585 subdev whose `of_node` lies under that node. Its users all follow:
  - `setSensorWideDynamicRange` (CC:6927);
  - `writeImx585ExtControl` (CC:6962), called through `applyImx585HdrControls` at CC:7241, 11563 and 12527;
  - `probeSensorModes` (CC:7043);
  - `imx585SubdevPresent` (CC:6896).

  `resetStoppedSensorTiming` (CC:8118-8130) is the model for the `of_node` comparison. Without this, whichever Core's
  sensor is listed second fails every start while the other streams (C-new1).
- **Identity in state:** `camera_id` (`camera->id()`) and `camera_port` in get_state and the settings event (C11). The
  clip-name `{cam}` comes from the port, not the hard-wired "cam0" (CC:1148).
- **No sensor on the port:** in `main()`, before `app.start()`, the secondary looks in sysfs for a sensor subdev whose
  `of_node` lies under its I2C node (the same node as the subdevs above).
  - When config.txt names a sensor on the port (BootConfigText.hpp:474-545), a boot may not have probed it yet, so the
    secondary looks again every 0.5 s for up to 20 s.
  - If there is still none, or config.txt has no line for the port (then at once), it logs one line and exits 0.
  - The check must come first: `start()` runs the low-power restore and starts threads before the camera
    (App:7985-8034), and a failed start exits 1 (src/main.cpp:108-111), which `Restart=on-failure` would loop (P25).
  - No libcamera call is made, so cam0 is never touched. `--simulate` skips the check.
  - The primary waits the same way for cam0's subdev, when config.txt names one, before it falls back to today's rule
    (the camera pick above). A slow probe on a dual rig then does not hand cam1's sensor to the primary.

### 3.3 The secondary's role gate

| Off on the secondary | Where |
| --- | --- |
| trigger, PCF8574, NeoRotary4, GPIO buttons, Grove, power button, tally, controls worker | App:8080-8101, 8124-8125 |
| the idle-standby timer in the supervisor loop; the loop itself and its recording-failure check (App:8263-8266) stay on | App:8267-8282 (P1) |
| the photo-mode restore at start, which reads UI.conf. In its place the secondary forces photo mode, long exposure and bracketing off, so a stale `camera_settings.conf` in `.config-cam1` cannot leave cam1 in photo mode | App:8042-8054 (P1) |
| `apply_preset`'s photo keys (photoModeEnabled, photoLongExposureEnabled, photoBracketingEnabled, photoBracketingEv): ignored completely, with no presetSettings change and no UI.conf write. Every other UI.conf write too (`standbyTimeoutSeconds` and the rest). The other camera keys apply. The relay's strip (§4.4) is the second guard | App:13772-13786, 13996; 13978, 13981-14071 (P1) |
| low-power restores at start, stop and wake; standby's machine-wide steps | App:7985-7997, 8163-8172, 12294-12304; 12270-12287 (P13) |
| INA219 and IMU reads in `/api/state` | App:9302, 9663 |
| audio, gyro and sound-only in `record_start` | App:14216-14262 |
| the stop `syncfs`: replaced by an fsync of its own files | CC:4744 (P6, C-new3) |
| every command outside the allowlist (§4.2): "cam1 takes commands from the primary." | top of `handleCommand` |
| every POST on :8001: /api/command, /api/config, the preset routes, media delete, boot config and its parse (9 branches at 31d5418). One gate reply, returned before any route logic: HTTP 403, "cam1 takes commands from the primary." | App:9180, 8588, 8861, 8909, 8946, 8972, 9054, 9136, 9166 (P12) |

Kept: the hardware-file adopt and `refreshBufferRequest()` (App:8104-8122), which read `buffer=frames`.

At start the secondary logs one line that names its role and what is off, e.g. "role secondary: standby restores
off, inputs off, audio off". T60 checks that line.

### 3.4 Unit, start order, install

```
# /etc/systemd/system/apertar-core-cam1.service: the live unit (r5) without the wait-ui ExecStartPre
# No PartOf=: a primary restart leaves cam1 and its take alone (start order below)
[Unit]
After=apertar-core.service
[Service]
User=pi
WorkingDirectory=<as in the live unit, test 0.1>
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

- The live unit's full text is UNCONFIRMED: only r5's summary is known. T56 test 0.1 (`systemctl cat apertar-core`)
  supplies the remaining lines, `WorkingDirectory=` among them, before this file is written.
- **Real-time:** both Cores run without `APERTAR_RT`, like the live primary. If T69 wants RT, use the per-thread
  `APERTAR_RT_CAPTURE_PRIORITY` on each Core (CC:8988-8992), never the script's whole-process chrt on two Cores, and
  put the two capture threads and the two CFE interrupts on different CPUs.
- **Start order (P10).** Before its first camera start, the secondary waits up to 30 s for the primary's socket to
  accept a connection, then waits until the primary is *idle* (§4.3), then starts.
  - A take whose `record_cameras` is `cam1` does not count against idle here. cam0 is not recording then, and a
    secondary still waiting to start cannot be in that take, so on its link the primary ends the take ("cam1 back
    without its take", §4.6) instead of the take running on with nothing recording.
  - If the socket does not accept within 30 s, the secondary logs one line and starts without the idle wait: idle
    cannot be checked then. Hand-run with the primary stopped (T60), its camera starts about 30 s after launch.
  - The rule rules out two probes at the same time and the min_vmax race (D1b).
  - A restarted primary does not wait for cam1: `App::start` keeps today's order. Its manager start writes HBLANK =
    min on cam1's sensor (L2). That is a no-op while cam1's lock pins VBLANK-only (HBLANK 0, §7.3); with cam1's lock off
    it can cost cam1 one frame at min_hmax and a phase step. On link it adopts a running cam1 take (§4.6).
  - So that a restarted primary does not touch the card under a cam1 take, `App::start` starts the ControlClient
    before `runMediaTrim` and `runMediaWatcher` (App:8003-8013). Before both, it sets a "cam1 unknown" flag whenever
    config.txt names a cam1 sensor or the cam1 socket path exists; it does not wait for the relay's first connect,
    which runs on the relay thread. The flag holds `mediaTrimMayRun()` (App:11430) and makes the Start pre-roll's
    guard skip (App:11218) until cam1 answers its first get_state, or until 2 s of failed connects of any kind
    (refused, or no socket file). The REC toggles do not read it. With neither, the flag is never set.
  - After that first get_state, `cam1RecordingActive()` holds the trim while cam1 records, and the writes-pending
    rule while it drains (§4.3). The Start pre-roll waits up to 2 min for a held trim before its guard
    (App:11190-11201), so after a restart into a cam1 take it usually runs after the STOP, behind the trim.
- **Deploy and tests name both units.** After a Core build: `sudo systemctl restart apertar-core apertar-core-cam1`.
  Before r4-M1's `rpicam` runs, which need both sensors free: `sudo systemctl stop apertar-core apertar-core-cam1`.
- **Install (Patrik), in this order:**
  1. copy `scripts/start-apertar-core.sh` to `/home/pi/start-apertar-core.sh` and check with `cmp`; `grep
     APERTAR_CAMERA /home/pi/start-apertar-core.sh` must match, since today's script ignores `APERTAR_CAMERA` and
     `APERTAR_WEB_PORT`;
  2. copy `config/apertar-hardware-cam1.conf` to `/home/pi/apertar-hardware-cam1.conf`;
  3. `mkdir /home/pi/.config-cam1`;
  4. copy the unit, then `sudo systemctl daemon-reload` and `sudo systemctl enable apertar-core-cam1`.

  With no sensor on cam1, a boot leaves the unit `inactive` (exit 0), not `failed`.

## 4 Control path: the primary relays

### 4.1 ControlClient

`src/ipc/ControlClient.{hpp,cpp}` is new: the client half of ControlServer. It runs in the primary on its own
thread, with a FIFO.

- **Linking:**
  - It links only when cam1 is configured: config.txt names a cam1 sensor (BootConfigText.hpp:474-480, 512-540), or
    the cam1 socket *accepts a connection* (for tests; a stale socket file does not count, P23).
  - It refuses to link to its own socket (same inode). Such a socket still counts as configured: cam1 is present in
    state, as `offline`. The symlink tests in T61, T65 and T66 rely on this.
  - Once cam1's socket has accepted, cam1 stays configured until the primary restarts. The link decides cam1's state
    before the sysfs check does (§4.5).
- **Reading:** it reads all the time. cam1 sends every line to every client (ControlServer.cpp:175-196) and drops a
  client that falls behind (R7).
  - It closes every fd it receives, using `recvmsg`. The `preview_frame` lines carry none; only the buffer
    registration sends fds (`broadcastWithFds`).
  - It keeps the `recording`, `buffer`, `media_write_state` and `preview_frame` events (timestamps, for §7.6) and skips
    the rest (P4).
- **Replies:** it matches replies by id. One small helper reads a number, bool or string by key and skips nested values,
  because the flat parser stops at the first `}` (P15, R6).
- **Polling and liveness:** it polls cam1's `get_state` every second.
  - cam1 is `offline` only on EOF or a failed connect. A slow reply keeps the last state and never means offline:
    cam1's get_state waits behind its own command lock (P22). §4.5 says what a slow reply reads as during a stop.
  - It logs one line when the link goes down and one when it relinks.
  - A command that cannot be sent while cam1 is offline is dropped, and the resync on relink catches up. Setters
    still queued or unanswered when the link drops are dropped too, so the pending count returns to 0. A `record_stop`
    is the exception: it becomes a pending stop (§4.6).
- **Start:** `App::start` starts the ControlClient before the media trim and watcher threads (§3.4).
- **Locks:** the relay thread never takes `commandMutex_`. Its socket I/O never calls a CameraController accessor that
  takes the controller's `mutex_`, because the local stop holds that lock through its drain, for seconds
  (CC:12264-12280).
  - The idle inputs, the take state and its clip_name come from flags the command thread publishes, with the
    lock-free `rawTakeActive()` and `prerollActive()`. After each command the command thread also publishes the
    primary's `settingsBody`, which the compare reads (§4.4).
  - In a take with cam1, the command thread publishes the starting take (the clip_name it sends cam1, verbatim, and
    the take's cameras) before it reads the pending count and before the relay sends cam1's `record_start` (§6.2
    step 3). It withdraws it on any later refusal of the take, and on a failed cam0 start (§4.6).
  - Three bounded waits run on the command thread under `commandMutex_`, like the 220 ms audio sleep: the busy wait
    (at most 1 s, §4.3), a cam1-only `record_start` (at most 1 s, §6.2), and `record_stop`'s wait until the relay
    has written cam1's stop (at most the stop lead minus 2T, §6.2).
- **The hook:**
  - Today's `handleCommand` body (App:12173) becomes `handleCommandLocal`, without its lock. A wrapper keeps the old
    name, so its four callers (App:8281, 8299, 8322, 10083) do not change.
  - The wrapper runs `handleReadOnlyHardwareCommand` and `abortSafetyStopFlushForRecord` first, as today
    (App:12175-12180), then takes `commandMutex_` and calls `handleCommandLocal`.
  - On an ok reply to a "both" command, it bumps the pending count (§4.5) and queues the forward before it unlocks.
    A REC press that waited on the lock then sees cam1 busy. Counting before the lock is wrong: a REC press holding
    the lock would then wait on a setter queued behind it.
  - The relay's own setters count too (§4.3). It bumps the count first, then re-reads the published take; if a take
    is starting, it takes the count back and tries again at the next idle moment. Because the `record_start` branch
    publishes its take before it reads the count, a press and a resync step can never both go ahead.
  - `record_start` and `record_stop` coordinate inside their own branches (§6).

### 4.2 Command classes

| Class | Commands |
| --- | --- |
| Both: forwarded after the primary's ok | `set_iso(_auto)`, `set_shutter_*`, `set_exposure_*`, `set_wb(_auto)`, `set_fps`, `set_resolution`, `set_record_format`, `set_cdng_*`, `set_lossy_dng_ratio`, `set_prores_*`, `set_tuning_file`, `set_raw_bit_depth`, `set_clear_hdr`, `set_hdr_*`, `set_h264_resolution`, `set_timecode_mode`, `set_conform_fps`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_af_*`, `set_mode_ladder` (both Cores run one ladder, §4.4), `apply_preset` (camera keys only, §4.4), `enter_standby` (only when the primary's reply has `"standby":true`, and without `idle_timeout`), `wake` |
| Coordinated | `record_start`, `record_stop` (§6) |
| Each its own | `get_state`, `ping`, `help`, `list_*`, `get_mode_ladder`, `preview_subscribe`, `preview_clip_name` |
| Primary only | UI.conf keys (display, aids, `previewSource`, `recordBothCamerasEnabled`), audio, photo, timelapse, clip template, buffer mode, media, boot config, time and zone, fan, power, IMU, controls, `storage_preroll`, `user_activity` |

- One list is both the forward list and cam1's allowlist: a new command stays refused on cam1 until someone adds it.
- The exposure setters, which §4.3 lets through during a cam1-only take or a busy cam1, are `set_iso(_auto)`,
  `set_shutter_*`, `set_exposure_*` and `set_wb(_auto)`, as in v1. `set_af_*` and `set_hdr_*` are not among them.
- The secondary also accepts `record_start`, `record_stop`, and the read commands above.

### 4.3 Take-state rules and "idle"

**Idle**, for both Cores (P2), means the camera is Ready and none of these is true:
- `recording`;
- `storage_preroll_active` (a pre-roll is a real take at a raised fps, CC:11908-11956);
- `timelapse_active` or `still_exposure_active`;
- `media_writes_pending`;
- photo mode.

For cam1, idle also needs the pending count at 0: nothing the relay sent cam1 is queued or in flight (§4.5). The
compare, the resync and the secondary's start wait use this one test; a restarted primary does not wait (§3.4). The
compare does not run in photo mode.

| State | The primary accepts | Sent to cam1 |
| --- | --- | --- |
| Both idle | as today | every "both" command |
| Both record | as today: each Core's own take gates refuse reconfigures (CC:10514-10520, 10561-10600, 11196, 11490-11495, 11759-11766, 12484-12490) | every "both" command |
| cam0 records alone | as today | nothing during the take; one resync after it |
| cam1 records alone | reads, the exposure setters (§4.2), display keys, `user_activity`, `record_stop`; anything else, any `record_start` included: "CAM1 is recording." | the exposure setters |
| cam1 busy, not recording | reads, the exposure setters, display keys, `user_activity`, `record_stop`; anything else, any `record_start` included (a cam0-only one too), after the 1 s wait below: "CAM1 is applying a change. One moment." (the "One moment." pattern, App:12198, 12203) | the exposure setters, behind the setter in flight |

- **Busy window (P5):** cam1 counts as busy while the pending count is above 0. The count covers every setter sent to
  cam1, from queueing to reply: the wrapper's forwards (§4.1), the resync's three steps (§4.4), and the relink's
  `wake` and `enter_standby` (§4.6). Reads, `record_start` and `record_stop` never count; an unanswered stop reads
  `writing` instead (§4.5).
  - A setter that does not reconfigure replies within milliseconds. A reconfigure-type command (resolution, format,
    Clear HDR, bit depth, tuning file, an fps that moves the ladder rung, `apply_preset`) or `wake` holds cam1 busy for
    a manager start, and so for an HBLANK write on cam0's sensor (L2).
  - In that window a `record_start`, or a command the table refuses, first waits up to 1 s for cam1's reply, so a
    quick setter in flight costs nothing. If cam1 is still busy, it is refused with "CAM1 is applying a change. One
    moment." So cam0 never starts during a manager start the relay asked for (a secondary's own start comes before its
    link, §3.4).
  - `record_stop` never waits on the count: a STOP from the button or the WebUI, and cam0's buffer safety stop, stop
    at once.
  - After 10 s of busy, a `record_start` rolls without cam1: cam0 alone, with the pill saying why (§6.1). A press that
    asks for cam1 alone (NEXT TAKE CAM1, `cameras=cam1`) is refused instead.
  - The wait runs on the command thread under `commandMutex_`, signalled by the relay thread, which never takes that
    lock (§4.1).
- **Rig busy (P7):** `cam1RecordingActive()` is true when cam1's take state is `recording` (§4.5), whatever the
  pending count. It copies `soundRecordingActive()` (App:9971-9974) and joins it at every site where the rig counts as
  busy:
  - the tally LED's initial value (8100, 11965), idle standby (8271), web gates (8983, 9065), state (9272, 12503);
  - REC toggles (10546, 10555), pre-roll (11087), playback (11304), trim (11432);
  - `recordingGateActive()` (11879).
- **Tally and events in a cam1-only take (P7):** the primary does what `startSoundRecording` and `stopSoundRecording`
  do (App:10031-10034, 10044-10045): `syncRecordingTracking`, and a `recording` event with `active:true` when cam1
  starts and `active:false` when it stops or leaves the take (its own safety or failure stop). `handleTriggerEvent`
  (App:14465-14473) then drives the tally LED and the RecordingStart pulse, as for any take.
  - A link drop does not end the take. The take state stays `recording` (shown as `lost`, "link down", §4.5), so the
    tally stays on and the next press is a STOP. That STOP ends the take state at once (tally off) and keeps cam1's
    stop as a pending stop (§4.6).
  - A rejoin sends no new event. An adopt (§4.6) sends a `recording` event with `"adopted":true`, as the
    `sound_only` field is added (App:10031-10034), and `handleTriggerEvent` skips the RecordingStart pulse for it.
- **Writes pending:** the media gate (12212-12221), standby (12263), the delete gates (8990, 9072) and the trim
  (11432) also refuse while cam1 has writes pending or reads `writing` (an unanswered `record_stop`, §4.5) (P4). Both
  Cores write one NVMe, and the trim runs only while nothing uses the medium (App:11393-11396). A held trim also holds
  the Start pre-roll behind it (App:11190-11201).

### 4.4 Presets and resync

**What cam1 gets (P1, R5):**
- only the camera keys that `apply_preset` parses into `presetSettings`, flattened (presets nest under `settings`,
  App:7685; flatten as WCP:18615-18620);
- minus the photo keys and the clip template, which are the primary's: `photoModeEnabled`,
  `photoLongExposureEnabled`, `photoBracketingEnabled`, `photoBracketingEv` and `cameraClipNameTemplate`;
- `timecodeMode` goes as `cameraTimecodeMode`, with its value mapped as App:13975-13977 maps it: `rec_run` when
  `normalizeTimecodeModeValue` (App:556-562) reads "Rec Run", otherwise `free_run`, because App:13893-13896 accepts
  only those two. It is dropped when the preset has `cameraTimecodeMode`;
- none of the UI.conf keys that `apply_preset` writes (App:13776-13786, 13978, 13981-14071: `standbyTimeoutSeconds`,
  `photoModeEnabled` and the rest), because they would turn cam1's idle timer or photo mode on. The secondary also
  skips those writes itself (§3.3).

This applies to user presets and to the resync alike.

**The resync** brings cam1 to the primary's settings in up to three steps, each sent whatever the reply to the one
before:
1. `set_mode_ladder` with the primary's `resolutions`, `enabled` and `ramp_ready` (presets lack them), only when
   cam1's `get_mode_ladder` differs from the primary's. It is skipped while the primary's ladder is on but inactive in
   a processed format (ProRes, H.264): cam1 refuses an enabled ladder there (CC:10954-10956), and each refusal would
   schedule the same resync again. If cam1 refuses it for another reason, it is sent once more after step 2.
2. `apply_preset` with the camera keys above. While the primary reports `ladder_active` or `ladder_override`
   (App:312-316), it carries no mode keys (`cameraResolution*`, `cameraRawBitDepth`, `cameraClearHdr`): the ladder
   picks cam1's mode, and cam1's ladder check would refuse the primary's.
3. `set_clear_hdr` with the primary's `clear_hdr`, when the primary has `ladder_override` true and cam1 does not.

A refusal inside the resync sets `cam1.message` but schedules no resync by itself. After 3 resyncs in a row with no
passing compare between them, the relay treats cam1 as `refused` for takes, and no trigger below schedules a resync
until a compare passes, cam1 answers ok to a forwarded change, or the link comes back. The compare keeps running, and
a passing compare ends `refused`. So a resync that cannot converge ends, and stops costing manager starts.

**An override that outlives its process.** `ladderOverride_` is not saved (CC.hpp:245), but the mode it set is, and no
ladder rewrite runs at start. After a one-Core restart under an override, the two Cores would then disagree on
`ladder_override` for good: step 2 never touches the flag, and step 3's `set_clear_hdr` with the value cam1 already has
returns before it sets the override (CC:11524-11532). So `CameraController::start` (CC:10417, T61) sets
`ladderOverride_` when the ladder is active and a ladder rewrite of the started settings (`ladderRewriteLocked`,
CC:10744) would change the mode. Both Cores then report the override, and on the one-sensor rig get_state stops
showing an active ladder whose rung is not the running mode after such a restart.

**When to resync:** one resync runs at the next moment both Cores pass the §4.3 idle test, after any of:
- a (re)link;
- a non-ok reply to a forwarded command (that reply also sets `cam1.message`, P8);
- a take cam1 sat out;
- a forwarded `set_record_format` or `apply_preset` (each Core restores its own per-format profile, CC:11213-11239);
- a difference found by the compare.

**The compare:** every second, it checks cam1's `settingsBody` (App:298-379, in its get_state) against the primary's
own, as the command thread last published it (§4.1), on every field the resync sets. It compares the resulting state,
not the commands sent (R4).
- It runs only while both Cores pass the idle test, and only against a cam1 get_state sent after the last forward's
  reply. It resyncs only after two differing compares in a row, so an ordinary setter never triggers one.
- **Compared:** the mode and format fields (`resolution`, `fps`, `conform_fps`, `recording_format`,
  `cdng_compression`, `cdng_log`, `cdng_log_bits`, `lossy_dng_ratio`, `prores_profile`, `prores_color_profile`,
  `cdng_preview_color_profile`, `tuning_file`, `clear_hdr`); `iso`, `shutter_us` and `wb_kelvin` with their auto flags;
  `exposure_compensation` and `exposure_metering` (:325); `fps_phase_lock` and `fps_speed_ramp*`; `hdr_*` (:359-362),
  `raw_bit_depth` (:363), `h264_*` (:364-368), `timecode_mode` (:369), `af_*` (:370-376).
- **The ladder, compared:** its definition (cam1's `get_mode_ladder` rungs, `enabled` and `ramp_ready` against the
  primary's, which the command thread publishes at start and after each ok `set_mode_ladder`), with `ladder_enabled`,
  `ladder_ramp_ready`, `ladder_override` and the rung `ladder_resolution` (:312-316). While the primary's ladder is on
  but inactive in a processed format, the ladder is skipped, as in the resync.
- **Skipped:**
  - the values in use under auto (ISO, shutter, WB);
  - `clip_name_template` and `clip_name_example` (:357-358), `photo_*` (:326-329), `bufferSettingMembers()` (:377);
  - the fields that follow others: `width` and `height` (resolution); `iso_auto_after_clear_hdr` (:320) and
    `wb_auto_after_clear_hdr` (:332), which follow Clear HDR;
  - the measured or derived fields: `iso_actual`, `iso_max`, `fps_max`, `fps_take_max`, the `*_available` flags,
    `exposure_metering_modes` (a sensor capability), `preview_exposure_reference` (:349, CC:7354),
    `cdng_log_applied`, `wb_measured`, `wb_actual_*`, `recording_capabilities`, `ladder_text` (it repeats the rung's
    mode and `fps_take_max`), and the other `ladder_*` fields.

**The mode ladder:** both Cores run the primary's ladder. `set_mode_ladder` is forwarded like any "both" command, and
the resync sends it when cam1's differs. On two IMX585s both ladders then pick the same rung from the same fps, and
the compare catches a rung that differs. A `--simulate` cam1 (SensorFamily::Unknown) has other rung ceilings and
forces auto ISO off in 4K lossless, so T61-T66 run with the ladder off and with manual ISO or a non-lossless format.
T69 checks the shared ladder on the real cam1.

### 4.5 cam1's state

New in get_state and `/api/state`:
- `cam1` = `{state, message, recording_dropped_frames, locked, skew_us}`. It is absent when cam1 is not configured.
  `message` says why for `refused` and `lost`, and also gives a slot offset between the clips ("CAM1 started 2 frames
  late", "CAM1 stopped 1 frame late", §6.2).
- `record_cameras` = `cam0`, `cam1`, `both`, or `none` in Sound Recorder mode (P19): for the running take, else for the
  next one. Whether a ready cam1 is in the next take is read here, not from the state word. It follows the 10 s busy
  drop (§4.3): a busy cam1 stays in it until then.

**Two inputs, one word.** The relay keeps cam1's take state (from cam1's get_state, its events and the link) and,
apart from it, the pending count: setters queued or in flight (§4.3).
- The word in `cam1.state` ranks lost > recording > writing > refused > busy > ready, so `busy` shows only while cam1
  neither records, writes nor stands refused.
- `cam1RecordingActive()`, the tally, the `recording` events and the §4.3 busy sites read only the take state. The
  1 s wait, "One moment." and the 10 s drop read only the count, whatever the word (a `standby` cam1 being woken
  included). They gate `record_start` and the commands §4.3 refuses, never `record_stop`.

**The link decides first.** With a link, the state comes from cam1's get_state; a refused same-inode socket is
`offline`. Only with no link does the sysfs check count.

| `cam1.state` | Meaning |
| --- | --- |
| `not_found` | config.txt names a cam1 sensor, sysfs has none under its port, and there is no link (the secondary has exited 0) |
| `offline` | no link (a refused same-inode socket too, §4.1), except after a drop during a take with cam1, which reads `lost` until the relink |
| `busy` | ready, with the pending count above 0 |
| `ready` | can record; `record_cameras` says whether it is in the next take |
| `recording` | in the running take |
| `writing` | writes pending. A slow poll while cam1's `record_stop` is unanswered, or while its `media_write_state` says pending, also reads `writing` |
| `refused` | `message` says why: a refused REC (until the stop), or 3 resyncs that did not converge (until a compare passes, §4.4) |
| `lost` | cam1 left the running take unasked: an `active:false` the primary sent no stop for (cam1's buffer safety stop, or its failure stop on a write error or a lost medium). The take state ends; the word lasts until the running take stops, then follows cam1's get_state again. Or the link went down during a take with cam1: the take state stays `recording` ("link down", so the tally stays on), and the word lasts until the relink (§4.6). A STOP during the drop ends the take state (tally off, `recording` false, the next press is a REC) and keeps the pending stop; the word stays `lost` |
| `standby` | in standby |

- **HDMI:** no second control bridge (U9). CB polls the primary at 1 s while `cam1` exists (CB:1010-1017) and parses
  `cam1` and `record_cameras`.
- **WebUI:** it reads `snapshot.cam1` from :8000. A fetch to :8001 gets 403 (WebServer.cpp:159-173, 373-376; U10).

### 4.6 Failures

| Situation | What Patrik sees (HDMI and WebUI) | What one REC press does |
| --- | --- | --- |
| cam1 not configured | today's screens | records cam0, as today |
| configured, no sensor found | amber `CAM1 NOT FOUND`; cam1 views show cam0 | records cam0; the pill blinks if the policy wanted cam1 |
| cam1 Core crashed or restarting | amber `CAM1 OFFLINE`; views fall back | records cam0. A restarted cam1 starts its camera only when the primary is idle, where a cam1-only take does not count (§3.4) |
| cam1 applying a change | white `CAM1 BUSY` | any REC press, a cam0-only one too, waits up to 1 s for cam1's reply, then is refused: "CAM1 is applying a change. One moment." After 10 s of busy, cam0 rolls alone; a press that asks for cam1 alone is still refused. STOP never waits |
| cam1 still writing the last take | `CAM1 WRITING` | refused while cam1 is in the take: "Wait for CAM1 to finish writing to media." |
| cam1 refuses REC | amber `CAM1 REFUSED` and the reason until the stop | cam0 rolls; cam1 never joins mid-take. In a cam1-only take the press is refused with cam1's reason, or with "CAM1 did not answer." after 1 s without a reply (§6.2) |
| cam1 leaves the take (its own buffer safety stop or failure stop) | amber `CAM1 LOST` and the reason until the take stops; its frames so far stay on the card | cam0 keeps rolling. In a cam1-only take the tally goes off and `recording` turns false (P7) |
| cam0's buffer safety stop | as today | stops both: cam0 at once, with no lead and no wait; cam1 on the next slot's `stop_us` (§6.2). It runs `handleCommand("record_stop")` through `dispatchHardwareInputCommand` (App:11039-11042, 11066-11068) |
| cam0's recording fails mid-take | one error, as today | cam0 stops and the tally goes off, as today; in a two-camera take cam1 gets the next slot's `stop_us` (§6.2) |
| cam0 refuses | one error, as today | nothing starts |
| cam0 fails to start after cam1 was told | one error | the primary sends cam1 `record_stop` at once, in the same `record_start` branch, withdraws the published take and remembers it as stopped (rule 2 below); an empty cam1 folder may remain |
| the relay link drops mid-take (cam1 alive) | amber `CAM1 LOST`, "link down", until the relink; the tally stays on | both keep recording. On relink cam1 rejoins the take (below), and the gap is logged |
| STOP while the link is down | the tally goes off; `CAM1 LOST`, "link down", until the relink (§4.5) | cam0 stops on its slot. cam1's stop is kept as a pending stop (clip_name, `stop_us`) and sent first on relink: cam1 stops at once and reports "stopped N frames late" |
| the primary restarts or crashes mid-take | the restarted primary shows the adopted take | cam1 keeps recording; the restarted primary adopts it as a cam1-only take (below), so STOP ends it. Until cam1 answers, the restarted primary holds its trim and Start pre-roll (§3.4) |
| cam1 in standby while the primary is awake | `CAM1 STANDBY` | records cam0; the relay sends `wake` (below), and while it is in flight a REC press waits as for `CAM1 BUSY` |
| card nearly full | REMAINING counts down for both | under 1 GiB free, each Core refuses (App:11337-11341) |

- **What the primary remembers:** each take since its own start; for a take with cam1, the clip_name it sent cam1 and
  the `stop_us` once it stopped it; and any pending stop (that clip_name and its `stop_us`). The published running
  take carries the same name (§4.1). These are cam1's verbatim names, never cam0's folder names, and the rules below
  compare cam1's `recording_clip_name` with them.
- **On link or relink, and at each poll that shows cam1 recording outside the running take,** the primary reads cam1's
  `recording_clip_name` (§8) and applies the first rule that fits:
  1. The running take's clip_name: cam1 rejoins. The take state stayed `recording`, so there is no new event and no
     pulse. The coordinated stop ends it on the slot, and the gap is logged.
  2. A take the primary has stopped: a pending stop is sent now (a `stop_us` already past stops at once, §6.2). A stop
     already sent is given until `stop_us` + max(3T, latency) before rule 4 applies.
  3. No take running, and this process has had no take since it started (it restarted or crashed): the primary
     adopts the take as cam1-only (tally, `record_cameras=cam1`, a `recording` event with `"adopted":true` and no
     pulse, §4.3). STOP then ends it.
  4. Otherwise: the orphan stop (`record_stop` at once).
- **cam1 back without its take** (it crashed and restarted while the link was down; its start wait lets it start
  during a cam1-only take, §3.4): on relink, a take state of `recording` whose clip cam1 no longer records ends there,
  as a `lost` (§4.5). In a two-camera take cam0 keeps rolling; in a cam1-only take the take ends, the tally goes off
  and `cam1.message` keeps the reason.
- **Standby:** on link or relink during the primary's standby, cam1 gets `enter_standby` (P13). On link or relink
  while the primary is awake and cam1 reports standby, the primary sends `wake`; this also covers a primary restarted
  during standby.

## 5 Display

### 5.1 The setting

It copies the `externalMonitorMode` quartet. Every site follows (U8):

| End | Sites copied |
| --- | --- |
| Core | normaliser App:863-869, snapshot :1870-1873, reader :2040-2047, state `ui.external_monitor_mode` :9617, command :13267-13278 (strict check :13273-13274), help :12496 |
| UI | SettingsBridge.hpp:47-50, .cpp:360-366, 547-550, 1074-1092; SettingsPage.qml:2450-2491 (optional, touch) |
| WebUI | WCP:5272, 18897, 20329, 14129, 6444, 15502, 15560, 10889-10890 |

The quartet's preset sites are not copied (Core :7767-7773 and :14027, SettingsBridge.cpp:2165-2168 and 2257-2260,
WCP:18646): `previewSource` is neither saved in nor applied from presets in v1.

- UI.conf `previewSource`: `Both` (default), `Cam 0`, `Cam 1`, `PiP Cam 0`, `PiP Cam 1`. The labels are strict, like
  the quartet's: `pip_cam0` is refused.
- Command `set_preview_source`; state `ui.preview_source`.
- The primary writes UI.conf and the UI follows the file. No socket event is needed (r3 Q3).
- With no cam1 configured, the select is not shown and the second picture does not exist.

### 5.2 HDMI: ExternalMonitorWindow

The rig's HDMI picture is EMW, because `hdmi_external_only` defaults to true (DisplayConfigBridge.cpp:294, 354-357;
K3). The rig's value is from the KB note of 2026-11-01. The UI's startup line (main.cpp:281) confirms it.

**Pieces:**

| Piece | Change |
| --- | --- |
| Preview client | One more `ApertarPreviewSocketClient` (beside main.cpp:291) on the explicit cam1 path, only while `cam1` exists. All four bare `connectToCore()` calls mean cam0 (U2, X12), so the standby wiring (main.cpp:335-350, EMW:321-330) passes the path too. `recordingChanged` reaches it too (main.cpp:351-352, P18) |
| Liveness | cam1 has a signal while a new `framesReceived` counter on the client moved in the last second (a 500 ms QML timer). It is bumped right after `frame_id` parses, before the recording cap drops a frame (ApertarPreviewSocketClient.cpp:481-493); `frameCounter` (hpp:21) would stop in a take under `APERTAR_UI_PREVIEW_RECORDING_FPS` and fake a lost signal |
| Second item | `externalPreviewItem1` beside EMW:404-428, with its own objectName (U7). Its renderer is made in `ensureWindow` after the first (ExternalMonitorManager.cpp:231-238), so it survives the rebuild on wake (U6) and draws on top |
| Renderer, two lines | (1) `render()` returns early for a hidden item: today only `scheduleWindowUpdate` checks (PWR:347), while `render()` imports first (2407). (2) `syncState` sets `m_resetPreviewState` when the bridge changes (410-426); otherwise a swapped pane keeps the other camera's last frame (U-new7) |
| Transforms | Both panes keep the display transforms: LUT, desqueeze, SMPTE, rotation, aspect. Only the aids (zebra, peaking, false colour, greyscale) and the guides stay on the main pane (P17) |
| Split DRM | With HDMI on another DRM card, `run_pi_direct.sh` starts a monitor-only process (`APERTAR_MONITOR_ONLY=1`, run_pi_direct.sh:244, 273; `runMonitorOnly`, main.cpp:131-237). It loads the same EMW with its own client and binds its renderer itself (:176-180), not in `ensureWindow`. v1 shows cam0 only there: every EMW use of the cam1 client is guarded with `typeof`, as `gyroConfigBridge` is (EMW:306). The rig has no touch screen, so it PROBABLY never runs that process |

**Layouts at 1920×1080:**

| Source | Main pane (aids) | Second pane (on top) | cam1 without a frame for 1 s |
| --- | --- | --- | --- |
| Cam 0 | cam0 full screen (today) | hidden | as today |
| Cam 1 | cam1 full screen, CAM1 tag | hidden | cam0 full screen; amber "CAM1 NO SIGNAL · SHOWING CAM0" |
| Both | cam0, left 960×540 | cam1, right 960×540 | right pane black, "CAM1 NO SIGNAL" |
| PiP Cam 0 | cam0 full screen | cam1 inset, 0.28 of the width, lower right, margins 0.03 | no inset |
| PiP Cam 1 | cam1 full screen (bridges swapped) | cam0 inset | as Cam 1 |

- The fallback follows the frames alone; an offline or dead cam1 Core sends none anyway. During the symlink tests in
  T66 the CAM1 pill reads OFFLINE by design (§4.1), while the panes draw cam0's frames.
- Both panes and the inset get 2 px white frames. Both adds a 4 px divider and pane tags, and turns off guides, centre
  marker and level.
- The inset's height follows the frame (U-new6).
- In PiP, REMAINING (EMW:1218-1224) moves above the inset (U7).
- Each pane's frame turns red while its camera records (one frame today, EMW:1427-1435).
- A CAM1 pill sits beside the status pill (EMW:1085), built from DroppedFrameWarning (EMW:1181-1186). It shows
  `CAM1 <STATE>` and cam1's drops:
  - red while recording;
  - amber when something is wrong, blinking while a take that wants cam1 runs without it;
  - white when ready and in the next take, grey when ready but out of it (`record_cameras`).
- **What a press records.** The status pill (EMW:198-200) adds a readout whenever cam0 sits out, or `record_cameras`
  differs from what the operator chose or from the cameras on screen:
  - cam0 sits out, in the next take or the running one: "READY · CAM1 ONLY · NO AUDIO", "REC · CAM1 ONLY · NO AUDIO";
  - the policy wants cam1 (Record both cameras, or a Both, Cam 1 or PiP Cam 1 preview) and the system drops it for any
    §6.1 reason: "READY · CAM0 ONLY · CAM1 OFFLINE" (or LOST, NOT FOUND, REFUSED, STANDBY, BUSY), and "REC · CAM0
    ONLY · …" in a take. For a busy cam1 that readout waits for the 10 s drop, which `record_cameras` follows: until
    then it still names cam1 (a press waits, then gets "One moment."), so the status pill adds nothing and the CAM1
    pill reads BUSY;
  - cam1 is ready but its client has had no frame since it connected (`framesReceived` 0), so the press still records
    cam1 (§6.1): amber "READY · CAM1 ONLY · NO SIGNAL · NO AUDIO" with a Cam 1 preview, "READY · BOTH · CAM1 NO
    SIGNAL" with Both;
  - the counter moved and then stood still for 1 s: the press is refused ("CAM1 has no picture.", §6.1), so the pill
    reads amber "READY · CAM1 NO PICTURE" instead. `record_cameras` does not change.
- **Italics, not colour, for the system's choice.** A readout the system chose (a dropped cam1) is italic. The status
  pill's Text (EMW:1169-1179) gets `font.italic` bound to that condition, the way `cameraSet` works for the HUD items
  (EMW:902); `cameraSet` itself does not reach the pill.
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
loop). The two-line `isVisible` guard and the recording fps cap on both clients bound it. T65 measures the drops.

### 5.3 WebUI

- **The picture:** `<img id="previewStream1">` loads `http://<location.hostname>:8001/preview.mjpeg?stream=n`, without
  `crossorigin`.
  - An image request sends no Origin, so it passes Core's check (U11; browser side PROBABLE).
  - It drops its `src` while its pane is not shown (source Cam 0) and while the playback browser is open, since MJPEG
    encodes only while viewed (App:9735). `pbPauseLive` and `pbResumeLive` (WCP:12047-12059) stop and restart it too,
    with their `removeAttribute("src")` pattern.
  - Aids stay on cam0: a cross-origin image taints the canvas (r3 Q6).
- **Layouts:** CSS per source. Both is side by side, stacked below 700 px; PiP is a 28 % inset with 3 % margins.
  Tags, red frames and NO SIGNAL work as on the HDMI.
- **The setting:** the read-only "Preview source" row of the Live preview card (WCP:5229-5232) becomes a select while
  `cam1` exists.
- **Recording controls:**
  - "Record both cameras" pills beside Record Audio (WCP:5477, 16163-16169).
  - NEXT TAKE pills (Auto, CAM0, CAM1, Both) next to REC. They send `cameras` with this page's REC press and reset
    after the stop. Hardware buttons follow the policy. In Sound Recorder mode the pills are hidden and the page sends
    no `cameras`, which §6.1 refuses there.
  - The REC label names what this page's press records: "REC BOTH", "REC CAM0", "REC CAM1 · NO AUDIO", or "REC
    SOUND" in Sound Recorder mode. It shows "STOP" while either camera records.
  - With a NEXT TAKE pill other than Auto, the label has two lines, because the camera's button still follows the
    policy: "THIS BUTTON: REC BOTH" and, from `record_cameras`, "CAMERA BUTTON: REC CAM1 · NO AUDIO".
  - When the system drops a camera the operator asked for, the label and its "CAMERA BUTTON:" line are italic. The
    `.system-value` class styles only `.badge`, `.settings-summary-value` and `.pill-button` (WCP:850-857), so the
    label's selector (e.g. `.record-label.system-value`) joins the rule at WCP:853-856.
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
   is down (`not_found`, `offline`, `refused`, `lost` or `standby`), cam1 sources count as Cam 0. A `busy` or
   `writing` cam1 keeps them, so the table below applies.

**The cost of the default.** With the preview on Cam 1 or PiP Cam 1, every press, the camera's button included,
records cam1 only, with no WAV in v1 (Cinemate writes one WAV per process). The HDMI status pill and the REC label say
so (§5.2, §5.3); Q1 offers "both always" instead.

**cam1's state at the press**, when the take wants cam1:

| `cam1.state` | The press |
| --- | --- |
| `ready` | records as chosen above. Only if cam1 has sent preview frames since the link and none in the last 1 s (a stalled stream) is it refused: "CAM1 has no picture." The 1 s runs from the later of cam1's last frame and its last reply to a reconfigure-type command or `wake` (§4.3), whose manager start stops the frames for a while. A cam1 that never sent one (the simulated cam1) still records |
| `not_found`, `offline`, `refused`, `lost`, `standby` | cam1 is dropped and cam0 rolls; the pill says why. An explicit `cameras=both` rolls cam0 too (P21c); an explicit `cameras=cam1` is refused ("CAM1 is offline.", etc.) rather than recording cam0 |
| `writing` | refused: "Wait for CAM1 to finish writing to media." |
| `busy` | waits up to 1 s for cam1's reply, then is refused: "CAM1 is applying a change. One moment." After 10 s of busy, cam1 is dropped as above (§4.3) |

A take that does not want cam1 starts whatever cam1's state, except while cam1 is busy or records alone. Then §4.3's
table applies: while cam1 is busy, the press waits up to 1 s, then gets "CAM1 is applying a change. One moment.", and
after 10 s of busy cam0 rolls, so cam0 never starts during cam1's manager start. While cam1 records alone, any
`record_start` is refused with "CAM1 is recording."

**Excluded:** photos and timelapse run on cam0 only (P11). Sound Recorder mode records sound and no camera, so
`record_cameras` is `none` and an explicit `cameras` is refused there (P19).

### 6.2 Start and stop on one slot

**A take without cam1 starts exactly as today**, with "now" and no lead (P3).

**A take with cam1 starts in the `record_start` branch**, after the gates (App:12196-12231) and the trim wait
(12225-12228), before the audio sleep (14297):
1. **The slot.** The primary picks k0 = ceil((now + lead) / T) on the grid of §7.2 and `start_us` = (k0 − ½)·T, in
   the SensorTimestamp domain (CLOCK_MONOTONIC, S3).
   - The lead is max(500 ms, L_start + T, (D+2)·T + L_cam1), with the lock's delay D (§7.4):
     - L_start is the slower Core's time from the slot pick to its armed gate (CC:7631, 7649): the audio sleep, the
       folder and the writers, and on cam1 its command path and FIFO (R1). T56's 0.7 (press to reply) bounds it on
       the primary: 0.3-0.8 s with audio on (PROBABLE).
     - L_cam1 is the time from the slot pick to cam1 setting `takePending_` (step 5), so that a stretch cam1 requests
       just before cannot land in the take. The relay logs it per take (T64 with the simulated cam1, T69 with the real
       one); about 10-80 ms (ESTIMATE).
   - With 0.7's numbers that is about 0.53-0.84 s in Clear HDR (ESTIMATE). T56 runs before T62, so the lead starts
     from its numbers.
2. **One clip number** for both names: the lowest number free under both (CC:1182-1197).
   - cam1's name uses `{cam}` = `cam1` if the template has `{cam}` (ClipName.hpp:31-33). Otherwise it is cam0's name +
     `_cam1`: the default template `{format}_{date}_{clip}` (ClipName.hpp:23) has no `{cam}`.
   - cam1 uses `clip_name` verbatim and never runs it through `parse()` or `nextClipFolderName`. It refuses the take
     unless every character passes `clipname::isNameChar` (ClipName.hpp:39-42), the name has at most
     `kMaxNameChars` + 5 = 105 characters (:25; the 5 are the `_cam1` suffix), and it has no leading or trailing
     separator. A `{cam}` name never exceeds 100, because `cam1` is as long as the worst-case `cam0`
     (ClipName.hpp:180).
3. **The relay** sends cam1 `record_start cameras=cam1 start_us=… clip_name=… tc_offset_us=… audio_enabled=false
   gyro_enabled=false sound_only=false` and does not wait. It stays in the FIFO, behind any setter queued or in
   flight (the 1 s busy wait, §4.3, ran first).
   - Before it sends, the command thread publishes the take as the running take (the clip_name sent cam1 and its
     cameras, §4.1). cam1 reports `recording` as soon as its own start returns, before the audio sleep (App:14297)
     and cam0's start (14301); a poll answered in between then finds cam1's take under rule 1 (§4.6), not as one to
     adopt or stop.
4. **cam0** starts with the same `start_us` and its own name.
5. **Both Cores** set `recordingStartBootUs_ = start_us` instead of now (CC:7631, 7649). The gate (CC:9068-9073)
   opens on the first frame with `SensorTimestamp/1000 >= recordingStartBootUs_` whose FrameDuration is within
   max(500 µs, T/50) of the period. On both Cores that is slot k0 (PROBABLE: the boundary sits mid-slot and |e| ≤
   50 µs).
   - **No stretch once a take is decided.** The lock's notion of recording (CC:8778-8782, 8813) becomes
     `takePending_ || recordingFramesEnabled_`. Today only `recordingFramesEnabled_` counts, and it turns true only at
     the gate, after the audio sleep, so a stretch requested just before could land in the take.
     - `takePending_` is set only on a Core whose own camera records the take. On the primary: in every
       `record_start` that passes the gates and starts cam0 (cam0-only, both, and every camera take on the one-sensor
       rig). Never in a cam1-only or Sound Recorder take: their stop never reaches CC:7671, because `stopRecording`
       returns at once without a take of its own (CC:12266-12268). On cam1: when `start_us` arrives.
     - It is cleared on any later refusal of that take and together with the gate at CC:7671.
   - **A stretch already in flight.** Each Core records the slot its last stretch lands on (the request slot + D). A
     take whose first slot is not past it opens its gate after that slot, and reports the late start like any other
     (step 6). Frame 0 can also slip a slot for reasons outside the lock (missing WB or an unmapped buffer, R-new3);
     the first slot reports that too.
   - With `clip_name` given, the folder is made with an exclusive `create_directory` (CC:7543-7544). If it exists, the
     take is refused.
6. **Report.** Each Core replies at once, as today. The completion thread records the actual first slot:
   - for raw, from the frame index's anchor (`firstFrameTimestampUs_`, CC:4640-4641), so a first frame that fails
     its capacity check or its copy still leaves a first slot;
   - for the processed formats, where frame 0 is enqueued inside `recordProcessedPreviewFrame` (CC:10089): CC:10144-10145
     (ProRes) and CC:10181-10184 (H.264), each with its own counter.

   It goes into get_state as `recording_first_slot` and into the journal. `recording_last_slot` joins it when the gate
   closes: the slot of the last frame the take recorded, k1−1 for an on-time stop. Both are set only in takes with
   `start_us` and kept until the next take starts. A sidecar `slots.txt` in the clip folder, like `fps-ramp.txt`
   (CC:9762), holds the first and last slot, the period as num/den, and the time base (CLOCK_MONOTONIC); it too is
   written only in takes with `start_us`. get_state also carries `recording_clip_name`, the running take's folder name
   (on cam1 the verbatim `clip_name`), which the relink rules read (§4.6).

   A Core that opens its gate after `start_us` has passed starts on its next frame. The take keeps both cameras. The
   relay reads cam1's first slot in its 1 s poll, and `cam1.message`, the pill and the journal give the offset between
   the clips ("CAM1 started 2 frames late"). Post-production pairs the clips by `slots.txt`.

**A cam1-only take** (`record_cameras` = `cam1`) runs steps 1-3 and cam1's side of steps 5-6, and skips step 4: the
primary starts no camera and sets no `takePending_`.
- The press waits up to 1 s for cam1's reply (§4.1). On ok, the take state becomes `recording`, the tally and the
  `recording` event follow (§4.3), and the press replies ok.
- On a refusal, the press is refused with cam1's reason, and the published take is withdrawn. With no reply within
  1 s it is refused with "CAM1 did not answer.", and cam1 is sent `record_stop` with the take's `start_us` as its
  `stop_us`, so a start that arrives late stops at once. The primary remembers that take as stopped, so rule 2 covers
  it (§4.6); a short cam1 folder may remain, as when cam0 fails to start.
- The stop is the two-camera stop below without the local stop call: k1, `stop_us`, the same lead and wait, and a
  pending stop while the link is down. The take state, the tally and the `active:false` event end at cam1's reply or
  its `recording` event, or at once when the stop becomes a pending stop.

**Stop (both cameras in the take).**
- The primary picks k1 = ceil((now + stop lead) / T) and sends `record_stop stop_us = (k1 − ½)·T` to cam1 first, ahead
  of anything queued in the relay's FIFO. It waits until the relay has written that line, then stops locally with the
  same value.
  - The wait is bounded at the stop lead minus 2T. Since `stop_us` is at least the stop lead − T/2 away, a line
    written in time leaves cam1 at least 1.5 T to arm its stop.
  - The stop lead is max(100 ms, 3T) until T56 measures the stop latency, then 0.7's stop press to last frame (the
    drain comes after it) plus 3T.
  - A wait that runs out still stops cam0 with the same `stop_us`. A cam1 that gets its line late stops at once and
    reports it ("CAM1 stopped N frames late", below).
  - With the link down, cam1's stop becomes a pending stop with the same `stop_us` (§4.6), and cam0 stops on its slot
    without the wait.
- `stop_us` travels App:14387 → CC:12264/12278 → CC:7664 (and the .hpp). The gate (CC:9064-9081) requeues every frame
  with ts ≥ `stop_us` and wakes the stopper.
- `stopRecording` waits on a condition variable, without holding `recordingFrameMutex_`, until the gate has seen a frame
  at or after `stop_us`, or CLOCK_MONOTONIC passes `stop_us` + max(3T, the measured completion latency). Only then does
  it close the gate (CC:7671) and finalise. Both clips then hold slots k0 to k1−1 (R-new1).
- A Core that gets a `stop_us` already past stops at once. It logs "stopped N frames late" in its journal and writes
  its real last slot in `slots.txt` and `recording_last_slot`. After a two-camera stop the relay reads cam1's
  `recording_last_slot` at its next poll; past k1−1, the primary sets `cam1.message` to "CAM1 stopped N frames late",
  which the pill and the journal show.
- **Safety stops.** The buffer safety stop arrives as a plain `record_stop` (App:11066-11068), so the branch tells it
  apart by `bufferbudget::safetyStopState().active` (CC:4943), read the way CC:12274 reads it. Then cam0 stops at
  once, with no lead and no wait, and cam1 gets the next slot's `stop_us`.
- **Failure stops.** A write error or a lost medium never passes through `record_stop`: `checkRecordingFailure()`
  ends the take at four sites (App:8265, 10883, 11216, 12195). One helper replaces each `if
  (camera_.checkRecordingFailure()) syncRecordingTracking(false);`. In a two-camera take it also queues cam1's
  `record_stop` for the next slot. The tally goes off at once, as today: `checkRecordingFailure()` has already sent
  cam0's `active:false` (CC:12289-12311), and `handleTriggerEvent` acts on it (App:14465-14473).
- A cam0-only stop is as today; a cam1-only stop is above.

**The frame index** (CC:4639-4646) is today's time index, `llround(elapsed·fps)`. While both are locked it gives
k − k0, so in DNG and MLV a dropped frame leaves the same hole index in both clips (PROBABLE). ProRes and H.264 number
frames by count with constant pts steps, so there a drop in one clip shifts its later frames by one against the other;
`slots.txt` cannot say where.
- With Speed Ramp on (`fps_speed_ramp`), frames are numbered by count instead (CC:9334). The rule keys on `start_us`:
  a take with it (every take with cam1, a cam1-only one included, and T62's hand-made ones) keeps the time index until
  the first ramp step, is numbered by count after it, and is flagged unsynced from that step (journal, `slots.txt`,
  the pill). The frame where numbering switches goes into `fps-ramp.txt`'s header. Takes without `start_us` stay as
  today. Ramp steps are refused in cam1-only takes (§7.6), so those keep the time index throughout.
- Tests force a gap with a test-only env that discards one frame before the record path (§8, test-only).

**Tally and pulse.** In a two-camera take, the tally and the RecordingStart pulse fire at the press (App:14465-14473),
so they lead frame 0 by up to the lead. Firing the pulse at `start_us` waits for v2.

### 6.3 Audio, timecode, names

- **Audio:** one WAV, the primary's, in cam0's folder (M5). It is trimmed to cam0's frame 0, which is cam1's frame 0
  on the grid (AudioRecordingSession.cpp:612-640). A cam1-only take has no audio in v1.
- **Timecode:**
  - In a take with `tc_offset_us` (every take with cam1, a cam1-only one included, and T62's hand-made ones), each
    frame's timecode comes from its slot time t_k plus the primary's `tc_offset_us`, passed on `record_start`. This
    needs a `RecordingClock(offsetUs)` constructor beside RC:36-41.
  - Each Core can see that field. cam1 cannot tell a two-camera take from a cam1-only one, and `locked` is per Core
    and changes mid-take, so neither decides the timecode; the lock state shows only through the unsynced flag (the
    pill, the journal, `slots.txt`).
  - FreeRun timecode is then identical for each index on both clips, and jitter can never repeat or skip a number.
  - Every format follows. `tc_offset_us` and T go into the ProRes config (ProresRecorder.cpp:78; ProresEncoder.cpp:156,
    1389-1390) and the H.264 config (CC:6170-6185; LibavH264EncoderPlugin.cpp:266-268, 453), which stamp their
    first-frame timecode from the slot. `wallClockTimestampUs` (CC:9261-9265, 9335) becomes t_k + `tc_offset_us`, so
    DNG and MLV follow.
  - In a take without it, timecode is today's.
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
  (9-14 s), with 1.7-2.8 ms of overshoot (X-new2).
- **Never stretch while recording,** counted from `takePending_`, which every take of that Core's own camera sets
  (§6.2 step 5). A stretch
  requested just before can still land up to D frames later; each Core records that slot, and a take does not open
  its gate before it. A stretch of s advances the time index by s/T (CC:4642-4645). Above T/2 it leaves a phantom
  hole and breaks slot = index + k0 (S9). In a take only the PI acts: under 1 ms after about 5-8 s, under 50 µs only
  after 230-350 frames (about 9-14 s at 25 fps, longer at D = 11), with 1.7-2.8 ms of overshoot. `locked` comes after
  that, and the take stays NOT SYNCED until then.
- **`arm()`** resets the integral, the request and `lastPushed`, never the grid. The gap counting and the half-frame
  re-arm (FPL:88-117) are no longer needed.
- **Additions:**
  - anti-windup by conditional integration;
  - a `locked` state: |e| ≤ 100 µs for 25 frames;
  - a per-frame trace `slot ts err V` behind `APERTAR_PHASE_LOCK_LOG`, printed every frame whatever the lock state,
    before the early return for an inactive lock (CC:8814-8820), with err against the grid. Today's line (CC:8856)
    sits after that return and prints nothing with the lock off, which test 1.2 needs.
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
| T31 speed ramp | released for the ramp; the two ramps are not slot-aligned and the cameras are not synced during the ramp. From the first ramp step the frames are numbered by count and the take is flagged unsynced (§6.2). Allowed in two-camera takes; refused in cam1-only takes (cam1 records alone, §4.3: "CAM1 is recording."; P20). v2 could tie ramp steps to slots. Ramp steps carry the base pin: with the lock on, fix A makes them `{d, d+1}` (no HMAX hop, HBLANK 0); with it off they stay `{d, d}` and hop HMAX (T31) |
| Reconfigure (Clear HDR, format, colour profile, ladder rung) | the stream restarts with a random phase and re-acquires. `locked` is false meanwhile; a take then starts unsynced and says so |
| Stills | photo mode releases the lock (CC:8789). A still in video mode skips the pin (CC:8937-8947), and the lock re-acquires after it. Stills are cam0 only |
| Storage pre-roll | primary only, with `{p, p+1}` |
| Core restart mid-shoot | a restarted secondary waits for idle, where a cam1-only take does not count (§3.4); a restarted primary does not, but holds its trim and Start pre-roll until cam1 answers (§3.4). Either re-acquires the same grid on its own in about 1.5 s. Its HBLANK write is a no-op on a sensor whose lock pins VBLANK-only (HBLANK 0); with that sensor's lock off it can cost one frame at min_hmax and a phase step |
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
| State | `ui.preview_source`, `ui.record_both_cameras_enabled`, `cam1` (five sub-fields, §4.5), `record_cameras`, `camera_id`, `camera_port`, `fps_phase_lock_locked`, `recording_first_slot`, `recording_last_slot`, `recording_clip_name` (plus the five existing lock fields, App:9426-9430, added to get_state) | `ui.external_monitor_mode` (App:9617), `ui.record_audio_enabled` (:9637), `recording_dropped_frames` |
| `record_start` fields | `cameras`, `start_us`, `clip_name`, `tc_offset_us`; the reply is today's | `audio_enabled` (App:14231-14233); `clip_name` keeps the name rules of ClipName.hpp |
| `record_stop` field | `stop_us` | `start_us` |
| `recording` event field | `adopted` (a take a restarted primary adopted, §4.6) | `sound_only` (App:10033) |
| Files | `apertar-core-cam1.service`, `~/apertar-hardware-cam1.conf`, `~/.config-cam1/`, and `slots.txt` in the clip folder of a take with `start_us` | `fps-ramp.txt` (CC:9762) |
| Test only | `APERTAR_TEST_DROP_FRAME=n`: discards the take's n-th frame before the record path (T62, test 2.3) | `APERTAR_FPS_RAMP_GRACE_FRAMES` (CC:9634-9638) |

That is 23 new names and 4 files, plus one test-only env. There is no new key for the grid lock, no role flag, no new
event and no new action in v1.

## 9 Steps T56-T70

The numbers start at T56: playback used T46-T54, and T55 is the Clear HDR 16-bit preview tutorial.

Each step leaves the single-camera rig working. Its last check is always "with no cam1 configured, a take, Clear HDR
and the WebUI behave as before".
- **Order.** T57 comes first: T61's live skew and `cam1.locked`, and T62's slot pick and slot timecode, use its grid
  helper (k and e with the rational T) and its `locked` state. T58's driver change depends on no step, but its checks
  (1.3, 1.4, 1.6, 1.9) need T57's pins, quantiser and trace, so T58 runs after T57. T59, T60 and T63 do not depend on
  T57-T58.
- Patrik runs every sudo, restart, reboot and take. The work happens on local, never-pushed `dual-sensor` branches on
  the Pi (§12, Q24).
- **Never send** `format_media`, `eject_media`, a `set_boot_config` without `dry_run`, or a real delete to a Core under
  test. Prove a refusal with a request its own handler would refuse before writing, or one that writes nothing (T60).
- T61-T66 run the simulated cam1 with the Mode Ladder off and with manual ISO or a non-lossless format (§4.4).

| Step | What | Files | Check (prediction) | 1 sensor | Size |
| --- | --- | --- | --- | --- | --- |
| **T56** Measure first | no code (§10 Part 0) | none | the numbers that set the lead, D, σ, and whether a syncfs or a second writer costs a take frames | yes | 0 lines, 3 h |
| **T57** The lock on one grid | grid error, Q, stretch, anti-windup, `locked`, trace; pins A; saturation check; lock state in get_state; the KB simulator gains dead time, jitter, the 2-line step, Q, a grid case and a sensor pair | FPL, CC:8770-8861, 8934-8958, 2404-2415; App (state); `working/tools/phase_lock_sim.cpp` | host: the simulator's checks pass, the new cases match `sim/`. Pi 1.1, 1.2, 1.5, 1.8, 1.10; the trace marks the arm frame | yes | 300 lines (Core ~150, simulator ~150), 7 h |
| **T58** Driver SHR, then the T27 retake | fix E and `dev_dbg` | imx585.c on the driver's local `dual-sensor` branch (not `apertar` or `cinemate-port`); Patrik's DKMS rebuild | Pi 1.3, 1.4, 1.6, 1.9 | yes | 10 lines, 3 h |
| **T59** Camera by port, subdev by of_node | `--camera`, the env vars in the start script, the pick at both sites, the no-sensor exit and its poll in `main()`, the primary's wait for cam0's subdev, the port's I2C node in `openImx585Subdev` and its four users (§3.2), `camera_id`/`camera_port`, `{cam}` from the port | src/main.cpp, App.hpp, CC.cpp/.hpp, scripts/start-apertar-core.sh, config/apertar-hardware-cam1.conf (written here, used from now on) | no env: the same "Registered camera" line, take and Clear HDR as before. First, §3.4's install steps 2-3 run early: the cam1 hardware file (every input, `[imu]` and `[ina219]` with `enabled=false`) at `/home/pi/apertar-hardware-cam1.conf`, and `mkdir /home/pi/.config-cam1`; with the file missing, the readers would fall back to the primary's (App:4908-4925, GpioInput.cpp:64-80). Then the new binary run directly with the T60 test line's env and options, but `--camera cam1` and not `--simulate` (the primary keeps running; the installed start script still ignores `APERTAR_CAMERA`): with no cam1 line in config.txt, exit 0 at once, no libcamera line, cam0 undisturbed. With a cam1 line in config.txt and no sensor: exit 0 after the 20 s poll (checked in T68, after the line is written and before the power-off) | yes | 110 lines, 3 h |
| **T60** The secondary's role and unit | the role gate (§3.3: the preset's photo keys and UI.conf writes, photo mode forced off at start), the start line, the allowlist, the POST gate reply, the start wait and its 30 s timeout, the unit, the hardware file | App.cpp/.hpp, CC (syncfs), config/apertar-core-cam1.service, config/apertar-hardware-cam1.conf (from T59) | primary stopped, `--camera i2c@88000` with the test line below: the no-sensor check passes; the start line "role secondary: standby restores off"; no trigger, GPIO, PCF or power-button lines; the "controls:" line names the cam1 file; the wait line, and the camera starts about 30 s after launch; `set_clear_hdr` on cam1's socket turns WDR on in cam0's subdev (`v4l2-ctl --get-ctrl`); `set_zebra_enabled enabled=true` refused and cam1's UI.conf unchanged; MJPEG on :8001 works. All 9 POST routes on :8001 return exactly HTTP 403 "cam1 takes commands from the primary.", each probed with a request its own handler would refuse before writing, or one that writes nothing: presets/save with no name; presets/import with no file name; presets/delete, media/delete and media/delete-selected naming missing items; /api/config and boot-config/parse with an empty body; boot-config with `"dry_run":true`; /api/command with `set_zebra_enabled`. A preset with `standbyTimeoutSeconds=60` and `photoModeEnabled=true`, sent to cam1's socket, leaves cam1's UI.conf unchanged and cam1 awake after 2 min; cam1's get_state still shows `photo_mode_enabled`, `photo_long_exposure_enabled` and `photo_bracketing_enabled` false, and `grep '^photo_mode_enabled=' /home/pi/.config-cam1/apertar-core/camera_settings.conf` reads 0. After the install (§3.4): the grep of step 1 matched; `systemctl is-enabled apertar-core-cam1` says enabled; after a boot the unit is `inactive` and its journal shows the no-sensor line; after `sudo systemctl restart apertar-core`, `systemctl show apertar-core-cam1 -p NRestarts` is 0 | yes | 160 lines, 4 h |
| **T61** The relay | ControlClient and its start before the trim and watcher threads, the wrapper (its lock order and the pending count), the relay's own setters in the count and their hand-off with a starting take, command classes, idle, the take state, the busy window and its 1 s wait, presets and resync (its three steps, and the 3-resync cap that pauses the triggers), the shared ladder and an override kept across a restart (§4.4), the compare, `cam1` state (`refused` in the ranking), the link-down and relink lines, live skew | src/ipc/ControlClient.hpp/.cpp (new), App.cpp/.hpp, CC.cpp (10417), CMakeLists.txt | with the simulated cam1 (below): setters land in under 1 s; the journal shows the pending count rise at each forward, each resync step and the relink `wake`, and fall at each reply; a simulated cam1 that exits reads `offline`, never `not_found`; resync after a restart and after a sat-out take; with both Cores idle, no resync in a quiet minute; a `set_iso` sent to cam1's socket by hand is undone by the compare's resync within 3 s; with auto ISO and 4K lossless on the primary, which the simulated cam1 cannot follow (it forces auto ISO off there, §4.4), cam1 reads `refused` after 3 resyncs, and the journal shows no 4th until manual ISO lets a compare pass; `set_mode_ladder` reaches cam1 (`get_mode_ladder` matches); a SettingsBridge-style preset with `timecodeMode="Rec Run"` and no `cameraTimecodeMode` gets ok from cam1, and cam1's `timecode_mode` becomes rec_run; `storage_preroll` on the primary never changes cam1's fps; `enter_standby` reaches cam1 only when the primary entered standby; a cam1 left in standby while the primary is awake gets `wake` at the relink; a symlink to the primary's socket is refused, and cam1 shows `offline`; with no cam1 configured, nothing changes | yes | 550 lines, 13 h |
| **T62** Start and stop on one slot | `start_us`, `stop_us` and the stop gate, `clip_name` and its checks, `tc_offset_us`, `takePending_` for every take of the Core's own camera and the stretch-landing slot, `recording_first_slot`/`recording_last_slot`/`recording_clip_name`, `slots.txt`; exclusive mkdir; timecode from the slot in every format; the safety-stop branch (checked in T64, with cam1 in the take); Speed Ramp numbering keyed on `start_us`; `APERTAR_TEST_DROP_FRAME` | App.cpp (14387), CC.cpp/.hpp (4639-4646, 7507, 7631, 7649, 7664-7671, 8778-8782, 9064-9081, 9261-9265, 9334, 9762, 10144-10145, 10181-10184, 12264-12278), RecordingClock.hpp, src/prores/ProresRecorder.cpp, src/prores/ProresEncoder.cpp, src/video/LibavH264EncoderPlugin.cpp | primary alone: `start_us` = now + the lead (§6.2 step 1, from T56's 0.7) gives a first recorded frame with ts in [`start_us`, `start_us` + T), and `slots.txt` names its slot; ProRes and H.264 takes with `start_us` also write `slots.txt` and set `recording_first_slot`; `stop_us` gives the exact frame count; a `stop_us` already past stops at once with "stopped N frames late" in the journal, `slots.txt` and `recording_last_slot`; without the fields, frame 0 is the first frame after the gate arms, and press to frame 0 matches T56's 0.7 numbers (no lead added); with the lock on, `set_fps` and then REC within 0.5 s: the trace shows no stretch after the press; the first-frame timecode of DNG, MLV, H.264 and ProRes is the slot time plus `tc_offset_us`; a `clip_name` with a bad character, or over 105 characters, is refused; with Speed Ramp on and a gap forced by `APERTAR_TEST_DROP_FRAME` before the first ramp step, the index keeps the hole until that step and counts after it, `fps-ramp.txt`'s header names the switch frame, and `slots.txt` flags the take unsynced from it | yes | 200 lines, 7 h |
| **T63** The preview-source setting | the quartet (§5.1). It comes before T64, whose follow-the-preview policy reads it | App.cpp, SettingsBridge.cpp/.hpp, WCP | the five labels round-trip through UI.conf, `ui.preview_source`, SettingsBridge and the select; `pip_cam0` is refused | yes | 120 lines, 4 h |
| **T64** Take coordination | which cameras, `recordBothCamerasEnabled` (presets carry it, Q17), `record_cameras` (with the 10 s busy drop), the cam1-only take (Sound Recorder pattern: its start, its 1 s wait and its stop, §6.2) and its `adopted` event, the published starting take, `cam1RecordingActive()` at every busy site, the writes-pending and busy refusals (the trim included; `record_stop` never waits), the pending stop and the relink rules, the `lost` and `offline` words, the secondary's start wait past a cam1-only take (§3.4), the "cam1 unknown" hold on trim and pre-roll, the stop wait's bound, the safety-stop and failure-stop paths, the per-take L_cam1 log, failures, Sound Recorder and photo rules, time left in Core; KB `working/tools/sock_forward.py` (new, a few lines of python3) | App.cpp/.hpp (7797, 8003-8013, 8265, 10883, 11216, 11218, 11430, 11432, 12195, 14003, 14387, 14465-14473), CC.cpp (1182-1197), WCP (18657); UI: SettingsBridge.cpp/.hpp (2184, 2276, a member like `m_recordAudioEnabled`) | with the simulated cam1: policy, override, `record_cameras`; a hand-made `<next>_cam1` folder makes a two-camera take skip that number; a preset saved from the WebUI with Record both cameras on restores it; with cam1 killed, REC rolls cam0 and `cameras=cam1` is refused; a cam1-only take lights the tally and sends the `recording` events; 20 two-camera and 20 cam1-only takes in a row: none is stopped early or adopted, and the journal gives L_cam1 for each; after a cam1-only take, with the lock on, `set_fps` 25 → 24 → 25 on the primary locks within test 1.5's frame count (the trace shows the stretch); during a cam1-only take, a script that sends `set_iso` every 50 ms and polls get_state every 20 ms never reads `recording` false, `cam1.state` stays `recording`, and one REC press then stops the take. `kill -STOP` the simulated cam1 right after a forwarded `set_iso`: REC is refused with "One moment." for 10 s, then rolls cam0 alone, and STOP stops cam0 at once; `kill -CONT` afterwards. `kill -STOP` it again with nothing in flight: a cam1-only press is refused after 1 s with "CAM1 did not answer." and cam0 does not start; after `kill -CONT`, cam1's late clip stops at once. cam1 killed mid-take shows `lost` ("link down") and cam0 rolls; in a cam1-only take the tally stays on and one press ends the take. In a cam1-only take, kill the simulated cam1 and start it again with the test line: it starts without waiting for the take, links within a few seconds, and the take ends with the tally off. With the simulated cam1 on another socket path behind `sock_forward.py` at `/tmp/apertar-core-cam1.sock`: in a two-camera take, kill the forwarder, press STOP, restart it: `cam1.state` reads `lost` until the relink, cam1 then gets the pending stop ("stopped N frames late"), and the tally stays off; in a cam1-only take, kill the forwarder: the tally stays on, one press stops the take, and cam1 gets the pending stop at the relink. During a cam0 take, a `record_start` sent by hand to cam1's socket under another clip_name gets the orphan stop within 1 s. A primary restarted (by Patrik) during a cam1-only take adopts it: tally on, no RecordingStart pulse, `record_cameras=cam1`, STOP ends it. Neither a "media: trim … result=" nor a "storage preroll: … result=" line appears before the stop; after it, the trim's result line comes first, then the Start pre-roll's (result=ok in a raw format). A take kept running more than about 2 min after the restart shows the pre-roll's result=skipped before the stop instead (its 120 s wait for the held trim, App:11190-11201). With `APERTAR_CDNG_BUFFER_STOP_PERCENT=50` in a drop-in (removed afterwards), cam1 in the take, and cam0 in 4K Clear HDR 16-bit lossless JPEG at 25 fps with manual ISO and the ladder off (the encoder runs at about 17.5 fps, so the buffer fills; drop-frames README row 12): the journal shows "ApertarCore buffer: safety stop at" (App:11063), cam0 stops within one frame of it, and cam1 gets the next slot's `stop_us`. A template without `{cam}` whose cam0 name is 96-100 characters records both cameras. The failure stop waits for T69 | yes | 410 lines, 12 h |
| **T65** The second picture | second client (explicit path at all sites, `setRecording`), the `framesReceived` counter, item, renderer in `ensureWindow`, the two renderer lines, CB parses `cam1` | UI: src/main.cpp (the normal process; split DRM shows cam0 only, §5.2), ApertarPreviewSocketClient.cpp/.hpp, CB, PWR, ExternalMonitorManager.cpp/.hpp, EMW | no cam1: journal and drops as before; every EMW use of the cam1 client sits behind a `typeof` guard (a desk check). Through a symlink to the primary's socket, cam0's frames fill the second item (every client gets every frame, ControlServer.cpp:175-196); `cam1.state` is `offline` in the primary's get_state (or `/api/state` on :8000), and CB logs its parsed cam1 state as offline; with `APERTAR_UI_PREVIEW_RECORDING_FPS=0`, `framesReceived` keeps moving during a take; a 3-minute take with both clients drawing: drops compared with T56 | yes | 155 lines, 5 h |
| **T66** HDMI layouts | five sources, frames, divider, tags, CAM1 pill, the status pill's readouts and their italics (`font.italic` on EMW:1169-1179), REMAINING move, no-signal states, the photo rule, transforms on both panes, REMAINING × camera count | EMW, MediaStatusBridge.cpp | all five sources through the symlink (the CAM1 pill shows OFFLINE by design; the panes draw cam0's frames); through the symlink with the preview on Cam 1, the pill reads an italic "READY · CAM0 ONLY · CAM1 OFFLINE"; with `APERTAR_UI_PREVIEW_RECORDING_FPS=0`, a take in Cam 1 through the symlink keeps the second client's picture in the main pane, with no NO SIGNAL; fallback within 1 s against the simulated cam1, which sends no frames; with the simulated cam1 ready and the preview on Cam 1: the "CAM1 NO SIGNAL · SHOWING CAM0" banner and the amber "READY · CAM1 ONLY · NO SIGNAL · NO AUDIO"; in a cam1-only take against the simulated cam1, the pill reads "REC · CAM1 ONLY …" with NO AUDIO; with a forward held by `kill -STOP` of the simulated cam1 and Record both cameras on, the CAM1 pill reads BUSY and the status pill adds nothing for 10 s, then reads an italic "READY · CAM0 ONLY · CAM1 BUSY"; the NO PICTURE readout waits for T69 (the simulated cam1 sends no frames) | yes | 230 lines, 6 h |
| **T67** WebUI | second `<img>`, layouts, select, pills, NEXT TAKE, REC label and its second line, italics (not green), CAM1 badge, test hook | WCP, App.cpp | with cam1 configured (the symlink, which reads offline, or the simulated cam1) and `?cam1port=8000`, on a laptop and a phone: layouts at 390 px and landscape, pills, REC label, badge; a NEXT TAKE pill set before Sound Recorder mode is turned on is hidden there, and REC SOUND records; with a NEXT TAKE pill set, the label's second line names what the camera's button records; with Record both cameras on and cam1 offline (the symlink), the label reads "REC CAM0" in italics; the stream stops while its pane is hidden and while the playback browser is open | yes | 205 lines, 5 h |
| **T68** The second IMX585 | Patrik, in this order: (1) cam1's line, in the WebUI Boot Config card (Camera 1 sensor IMX585, 891 MHz chosen explicitly) or as `dtoverlay=imx585,link-frequency=891000000` in `[pi5]` beside line 42; then T59's no-sensor check with the poll: `sudo systemctl restart apertar-core-cam1`, and `journalctl -u apertar-core-cam1 -b` shows the 20 s poll and exit 0, the unit ends `inactive`; (2) `sudo poweroff`, then unplug the power; (3) attach the sensor to MIPI1; (4) power on; (5) `systemctl status apertar-core-cam1` is active (T60 enabled the unit), and its "Registered camera" line names i2c@70000 | config.txt | as pi, a get_state on cam1's socket answers (the test line below); §10 Part 2: enumeration 2.0, r4-M1 and r4-M2, sync tests 2.1, 2.2, 2.4 | no | 0 lines, 3 h |
| **T69** Dual takes | fixes only | as found | §10 Part 2: the combo ladder (r4-M5), 2.3, 2.6 (the WebUI in Both during a take, P24), every policy and source, drops per camera, boot order (cam1's "Registered camera" after the primary's socket bind). With the real cam1 and the Mode Ladder off (an active ladder makes the primary refuse `set_resolution` itself): `set_resolution`, then REC at once: refused "CAM1 is applying a change. One moment." if cam1's reconfigure takes over 1 s (PROBABLE), and REC 10 s later records both; a `set_clear_hdr` sent by hand to cam1's socket makes the compare resync, and a REC press right after the journal's resync line, while its `apply_preset` is in flight, waits and gets "One moment." if the reconfigure takes over 1 s; REC refused while cam1 writes, and a delete of a clip that does not exist refused the same way. The shared ladder: with the ladder on, a `set_fps` across a rung boundary gives both Cores the same `ladder_resolution`; then `set_clear_hdr` opposite to the rung's and a cam0-only take: afterwards both report the same `clear_hdr` with `ladder_override` true, after at most one resync. Under that override, restart only the primary, then only cam1: each time both report `ladder_override` true again, no resync loop runs, and cam1 never reads `refused`. The journal's L_cam1 per take sets the lead (§6.2 step 1). Patrik's stall of the primary during a cam1-only take: `P=$(systemctl show -p MainPID --value apertar-core); kill -STOP $P; sleep 30; kill -CONT $P`. If cam1 dropped the stalled client (R7), the primary's journal shows the link-down and relink lines and cam1 rejoins (no new event); if not, nothing is logged and the take goes on. In both, cam1's drops do not grow. A primary restart during a cam1-only take with the lock on: `sudo systemctl restart apertar-core`; `systemctl show apertar-core-cam1 -p MainPID -p ActiveEnterTimestamp` is unchanged, the clip grows, the primary adopts the take, STOP ends it, and cam1's drops do not grow; after STOP, the primary's "media: trim … result=" line follows cam1's "recording stop: synced to the medium" line (CC:4747) in `journalctl -u apertar-core -u apertar-core-cam1`. With the preview on Cam 1, stall cam1 in preview for 5 s (`P=$(systemctl show -p MainPID --value apertar-core-cam1); kill -STOP $P; sleep 5; kill -CONT $P`): during the stall the pill reads amber "READY · CAM1 NO PICTURE" and REC is refused with "CAM1 has no picture."; afterwards REC records cam1. A failure stop, if a hook or a real failure allows | no | 0-20 lines, 4 h |
| **T70** Touch UI (optional) | CameraPage panes, Settings rows | CameraPage.qml, SettingsPage.qml | it builds; there is no touch screen to try it | build only | 150 lines, 4 h |

**Test lines (P9).** Reuse these exact lines; anything shorter can steal the primary's socket or write its config.
`--simulate` accepts takes (CC:11847-11857) but never has writes pending (CC:12331-12335), so that check waits for T69.

```
# simulated cam1 (T61-T66), next to the running primary
XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf \
APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0 \
/home/pi/ApertarCore-build/apertar-core --simulate --camera cam1 \
  --socket /tmp/apertar-core-cam1.sock --web-port 8001 --media /media/RAW

# real secondary on cam0's sensor (T60), with the primary STOPPED; its camera starts after the 30 s wait
XDG_CONFIG_HOME=/home/pi/.config-cam1 APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf \
APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0 APERTAR_MEDIA_TUNE=0 \
/home/pi/ApertarCore-build/apertar-core --camera i2c@88000 \
  --socket /tmp/apertar-core-cam1.sock --web-port 8001 --media /media/RAW

# get_state from cam1's socket, as pi (core.py's socket path is fixed, core.py:17); the first line may be an event
python3 -c 'import socket; s = socket.socket(socket.AF_UNIX); s.connect("/tmp/apertar-core-cam1.sock"); s.sendall(b"{\"cmd\":\"get_state\"}\n"); print(s.recv(4096)[:300])'
```

## 10 Verification on the Pi, with predictions

### Part 0: measure first (T56, no code, no take running unless stated)

0.3, 0.5 and 0.6 load or disturb a take on purpose: Patrik runs them, on test takes only.

| # | What | Prediction | Decides |
| --- | --- | --- | --- |
| 0.1 | Read-only: `systemctl cat apertar-core`, `v4l2-ctl --list-devices`, the "Registered camera" line, `id` | as r5: one `rp1-cfe`, two `pispbe`; the live unit's full text, with its `User=` and `WorkingDirectory=` | the cam1 unit's text |
| 0.2 | Frame-interval log: a Python socket client records `preview_frame` `timestamp_us` (every client gets them) in preview, lock off, 25 fps and 24 fps | σ of the interval a few µs (UNCONFIRMED); 40000 / 41667 µs means | σ in the model |
| 0.3 | HBLANK stomp: with 0.2 logging at **24 fps** (lattice HMAX 625), run `rpicam-hello --list-cameras` ten times, 3 s apart. Read `v4l2-ctl --get-ctrl=horizontal_blanking` before | hblank 524 before. One interval of about 36.7 ms (5.0 ms short) per call, then 41.7 ms again; the phase steps by 5 ms each time. At 25 fps: no effect (hblank already 0, L-new2) | the rule "no manager start during a take" |
| 0.4 | Dead time D in Clear HDR: lock on (today's lattice lock), step `set_fps` 25 → 24.99, count frames until the interval moves | 11-12 frames (ESTIMATE); 7 at 1080p SDR (MEASURED) | D in the model |
| 0.5 | `sync -f /media/RAW` during a 4K Clear HDR take, three times | some queue drops (CC:4314-4318 records 782 in 3 min from a syncfs in the take) | the secondary's fsync rule |
| 0.6 | A second writer (a lossless 4K stream) during a 3-minute take: `command -v fio` first (the KB doubts fio is on the image, port-raw/s2-storage-core.md:380); `mkdir -p /media/RAW/fio-w2`; `fio --name=w2 --directory=/media/RAW/fio-w2 --rw=write --bs=1M --direct=1 --rate=150m --size=28g --runtime=180`; then `rm -r /media/RAW/fio-w2` | drops rise above the baseline (ESTIMATE) | whether 2× 4K lossless is worth trying |
| 0.7 | `record_start` and `record_stop` latency × 10 each: press to first frame (journal) and press to the reply; stop press to the last frame and to the reply | start 0.3-0.8 s with audio on (PROBABLE); stop: unknown | the start and stop leads; the stop wait's completion latency |
| 0.8 | Memory: Patrik's one `grep MemAvailable /proc/meminfo` shortly before STOP of a 3-minute 4K take; after the stop, `grep VmHWM /proc/$(systemctl show -p MainPID --value apertar-core)/status`; both again in preview | ESTIMATE from the write queue (buffer mode, CC:5428-5444): VmHWM is the preview footprint plus the queue's peak depth × about 17 MB per 4K 16-bit frame, and MemAvailable before STOP is lower than in preview by about that peak | a second Core fits if MemAvailable before STOP exceeds one more VmHWM plus 0.5 GB |

### Part 1: one sensor (T57-T58)

Conditions as C0102/C0103: 4K Clear HDR 16-bit, 25 fps, ISO 800, 20000 µs, 4000 K, static scene. The trace from T57
gives per-frame slot, ts, err and V, and marks the arm frame.

**Set-up (Patrik), with its undo.** Each test gets its own drop-in: `sudo systemctl edit apertar-core`, the line under
`[Service]`, then `sudo systemctl restart apertar-core`. The deadband is read once per process, so a drop-in that sets
it turns the lock into a meter for every test run under it.
- For 1.1 only: `Environment=APERTAR_PHASE_LOCK_DEADBAND_US=100000 APERTAR_PHASE_LOCK_LOG=1`. Afterwards remove the
  deadband, restart, and confirm with `systemctl show apertar-core -p Environment -p DropInPaths`.
- For the trace in 1.2, 1.4-1.6 and 1.8: `Environment=APERTAR_PHASE_LOCK_LOG=1` alone, with the deadband at its default
  (6 µs, FPL:38). T57's trace prints with the lock off too (§7.4), which 1.2 needs.
- For 1.10: `Environment=APERTAR_PHASE_LOCK_LOG=1 APERTAR_FPS_RAMP_GRACE_FRAMES=200` (CC:9634-9638).

Remove every line the same way, restart, and confirm with the same `systemctl show` before any real take.

| # | Test | Prediction | Settles |
| --- | --- | --- | --- |
| 1.1 | Grid lock as a meter (deadband 100000, set-up above); `v4l2-ctl --get-ctrl=horizontal_blanking,vertical_blanking` after 1 s, at 25 and 24.99 fps | hblank 0; vblank 3200 at 25 fps, 3202 or 3204 at 24.99 fps (on the lattice T27 read 0/3200 at 40000 µs, 217/2912 at 40001 µs and 308/2802 at 40016 µs, MEASURED; with Q's {40004, 40004} the lattice would read about 203/2930). 25 fps tells fix A apart only through Q: Q's pin is 40004, not 40000, and A without Q reads 0/3200 either way | fix A |
| 1.2 | Lock off, fixed pin: interval spread; then one step | σ a few µs; D ≈ 11 | the model |
| 1.3 | 24 fps, lock on, 1 ms shutter; band step in the centre; `dmesg \| grep -c imx585` per take | before E: alternating steps of about 1.5 % and one log line per push. After E: under 0.1 %, about 0 lines | fix E |
| 1.4 | 60 s take, lock off; then 60 s, grid lock on (E + A + Q), deadband at its default | no holes in either. Band step with the lock about as without (max ≤ 0.3 %). hblank 0 throughout. VMAX changes on 8-25 % of frames. Against the grid: max ≤ 40 µs, p99 ≤ 25 µs, RMS ≈ 10 µs | any holes: hold policy. Twice the error: re-measure D and σ |
| 1.5 | Acquisition: toggle the lock; 25 → 24 → 25 fps in preview | under 50 µs within about 13 frames of the arm: 13 after a lock toggle, and about 27-29 (~1.1 s) after a `set_fps` in Clear HDR, grace included | the stretch |
| 1.6 | 10-minute take (T27 step 5.2, never run) | the error does not grow; 0 holes; WAV length = frame count | long takes |
| 1.7 | Dropped: the rig has no safe way to cause a timesyncd slew on demand. The KB dispute (p2-phaselock-core.md:64) stays open, and Q22 keeps its default | | |
| 1.8 | Restart Core and let it re-lock | the same bounds on the same absolute grid | rejoining without messages |
| 1.9 | Clear HDR VMAX parity: pin a duration that gives VMAX 5402, measure the period; then pin VMAX 5406 | 5402: 40014.8 µs if 2-line steps hold; with a 4-line rule, 40000.0 µs (the sensor truncates to 5400) or 40029.6 µs (it rounds up to 5404). 5406: 40044.4 µs; 40029.6 or 40059.3 µs under a 4-line rule, which tells a truncating sensor from a pin that never applied | the Clear HDR quantum |
| 1.10 | 24 fps during an fps-change grace lengthened to 200 frames (set-up above): read HBLANK inside it | 0 with the base pin VBLANK-only (S8) | fix A on the base pin |

### Part 2: two sensors (T68-T69)

The ids r4-M1, r4-M2 and r4-M5 are r4's measurement plans; bare M ids elsewhere are claim-check claims. With two
sensors, read each sensor's controls on its own subdev: `grep -H . /sys/class/video4linux/v4l-subdev*/name` lists
them ("imx585 10-001a" is cam0, as r5 read; cam1's should be on i2c@70000's bus), then `v4l2-ctl -d <subdev>
--get-ctrl=horizontal_blanking`.

| # | Test | Prediction |
| --- | --- | --- |
| 2.0 | Enumeration after T68's power-on: `v4l2-ctl --list-devices`; the journal; `dmesg \| grep imx585`; CSI-2 error counters (`rp1_cfe.track_csi2_errors=1` is on) | two `rp1-cfe`; "Registered camera …i2c@70000… ISP device /dev/media3" in both Cores' journals; both sensors "internal-leader"; no CSI-2 errors at 891 MHz (else 720 on both, with §2's cost) |
| r4-M1 | Both Cores stopped (`sudo systemctl stop apertar-core apertar-core-cam1`): two `rpicam-vid` at 25 fps, 3 min, (a) 2× 4K SDR 12, (b) 2× 4K HDR16, with `LIBCAMERA_LOG_FILE` per camera; `working/tools/libcam_stages.py` | BE median per camera (a) 11-16 ms, (b) 15-22 ms (ESTIMATE). Above 20 ms in preview alone, 2× 4K recording is not viable |
| r4-M2 | The stomp with two sensors at 24 fps, lock off: restart cam1's Core during cam0's preview | one short interval on cam0 per start (0.3's size). With the lock on in both: none |
| 2.1 | Both locks off, 10 minutes, per-frame ts from both | s_k = tsA − tsB drifts linearly at Δ ppm, \|Δ\| ≤ 50 ppm (ESTIMATE). Δ decides whether the hold policy is usable |
| 2.2 | Both on the grid lock, pairs by slot | histogram of s_k: max ≤ 55 µs, p99 ≤ 40 µs, RMS ≤ 15 µs; median = the CFE bias (expect \|b\| < 10 µs); flat over 30 minutes; hblank 0 on both. Two peaks or a gap at 0: interrupt coupling (§7.5) |
| 2.3 | A take with `start_us` and `stop_us`; then one with Speed Ramp on and a gap forced by `APERTAR_TEST_DROP_FRAME` (a drop-in on both units, removed afterwards) before the first ramp step | both clips: the same first slot in `slots.txt`, the same timecode at each index, one WAV in cam0's folder; the same frame count when neither Core reports late, and a late cam1 shows as "CAM1 stopped N frames late" in `cam1.message`. The ramp take: both clips numbered by slot until the first ramp step, by count after it, and flagged unsynced from it |
| 2.4 | Restart cam1's Core in preview | cam0 shows no phase step and hblank stays 0; cam1 is locked within about 1.5 s |
| 2.5 | Optional: scope both XVS pins (first check that the leader drives XVS at all, S14) | agrees with s_k within the CFE jitter |
| 2.6 | The WebUI in Both during a 3-minute dual take (P24) | drops per camera no higher than in the same take with the page closed (ESTIMATE) |
| r4-M5 | 3-minute takes ×3 per combo, `buffer=frames` on cam1, in this order: 2× 1080p, 2× 4K SDR 12 lossless, 2× 4K SDR 12 uncompressed | loss under 0.5 %, 2-10 %, over 10 % (ESTIMATE, r4) |

## 11 Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| 1 | A manager start costs a running take a frame at min_hmax and a phase step (L2, L3) | VBLANK-only pins keep HBLANK 0 while the lock is on; the secondary waits for idle before starting; the busy window, which a cam0-only press waits for too; no restarts during takes, except a primary restart, which does not wait (§3.4); 0.3 and r4-M2 measure it. If r4-M2 shows a cost that matters: a libcamera-fork patch that skips the HBLANK write when another process holds the media lock, or one CameraManager kept across reconfigures (sync-critique "Missing" 3) |
| 2 | First-match subdevs send cam1's WDR to cam0 (C4) | of_node binding in T59, before any second Core runs |
| 3 | Load: one RP1 link, one SDRAM, one BE engine, 4 GB | T56 proxies, r4-M1, r4-M5; cam1 on frames; v1 one mode for both; 2× 4K HDR16 out |
| 4 | One NVMe and a syncfs per stop (CC:4744) | the secondary fsyncs its own files; both stop on one slot; 0.5 and 0.6 measure it |
| 5 | Settings drift between the Cores, or a resync that never converges | compare every field each second, after two differing compares; resync when idle, in three steps; after 3 resyncs in a row cam1 counts as refused and resyncs pause until a compare passes; an override survives a restart on both Cores (§4.4); refusals set `cam1.message` |
| 6 | A take silently records one camera | state words, CAM1 pill, REC label, the status pill's readouts (CAM1 ONLY, CAM0 ONLY · CAM1 …, NO SIGNAL), italics when the system drops a camera; a journal line per take on both Cores |
| 7 | The VBLANK-only lock costs holes or exposure steps | fix E first; test 1.4; the hold policy as fallback |
| 8 | The model misses interrupt coupling or a varying D | test 2.2 histogram; CPU affinity as a system fix |
| 9 | GUI-thread cost of a second import and draw | the `isVisible` guard; second client only while `cam1` exists; the recording fps cap on both; T65 measures the drops |
| 10 | One driver mode table | 891 MHz written on both lines; 720 on both if cam1 logs CSI errors, which caps 4K Clear HDR 16-bit at 25.000 fps and 4K SDR and 1080p at 50.000 fps on both sensors (§2). At those caps the lock can only lengthen frames, so it locks only if the sensor runs fast against the grid clock, and Clear HDR 30 fps is gone |
| 11 | A link drop or a primary restart leaves cam1 recording a take nobody stops, or adopts one the operator stopped | the take state survives a link drop; a stop that cannot be sent is kept as a pending stop; the relink rules read `recording_clip_name` and adopt only in a process that has had no take (§4.6); T64's forwarder test. One case stays open: a primary restarted between a link-down STOP and the relink (normally less than one poll while cam1 lives) has lost the pending stop, adopts the stopped take, and one STOP ends it again. Keeping pending stops in a file under /run would close it; v1 does not |

## 12 Questions for Patrik, with defaults

| # | Question | Default |
| --- | --- | --- |
| Q1 | Record policy | follow the preview, as Cinemate. The cost: with the preview on Cam 1 or PiP Cam 1, every press, the camera's button included, records cam1 only and no WAV in v1 (Cinemate writes one per process). The HDMI status pill ("READY · CAM1 ONLY · NO AUDIO") and the REC label say so. Alternative: "both always", `recordBothCamerasEnabled` on by default |
| Q2 | Preview default | Both |
| Q3 | cam1 not ready or refusing at REC | missing, offline, refused, lost or in standby: cam0 rolls alone and the pill says why; an explicit `cameras=cam1` is refused. Writing: REC is refused, "Wait for CAM1 to finish writing to media." Busy: any REC press, a cam0-only one too, waits up to 1 s, then is refused "One moment."; after 10 s of busy, cam0 rolls alone, and an explicit `cameras=cam1` is still refused. STOP never waits. While cam1 records alone, any `record_start` is refused: "CAM1 is recording." |
| Q4 | Audio | one WAV, cam0's; none in cam1-only takes in v1 |
| Q5 | Link frequency | 891 MHz on both; 720 on both if cam1 logs CSI errors. At 720 MHz, 4K Clear HDR 16-bit caps at 25.000 fps and 4K SDR and 1080p at 50.000 fps on both sensors, the lock then locks at those rates only if the sensor runs fast, and Clear HDR 30 fps is gone (§2) |
| Q6 | Per-camera resolution or format (4K + 1080p) | identical in v1; v2 |
| Q7 | Settings during a cam1-only take | exposure only: `set_iso(_auto)`, `set_shutter_*`, `set_exposure_*`, `set_wb(_auto)` (§4.2) |
| Q8 | The :8001 page | read-only |
| Q9 | NEXT TAKE also steers the hardware REC button | no: WebUI presses only. The REC label's second line says what the camera's button records |
| Q10 | Sync tolerance | the software grid, about 50 µs. XVS wiring only for row-exact stereo |
| Q11 | Lock in takes: track or hold | track |
| Q12 | Driver fix E (the driver rewrites the shutter, SHR, when VBLANK changes) on the driver's local `dual-sensor` branch, not on `apertar` or `cinemate-port` (you run the DKMS rebuild) | yes |
| Q13 | Speed ramps in two-camera takes | allowed: frames keep the slot index until the first ramp step, then count, and the take is flagged unsynced from that step; refused in cam1-only takes |
| Q14 | Clear HDR 30 fps in dual (cannot lock, unless the sensor runs fast) | allowed, flagged "NOT SYNCED" |
| Q15 | Mode ladder in dual | both Cores run the primary's ladder: `set_mode_ladder` is forwarded, so on two IMX585s both pick the same rung from the same fps |
| Q16 | Timecode from the slot (identical on both clips) | yes |
| Q17 | Presets carry `recordBothCamerasEnabled` | yes, like `recordAudioEnabled` |
| Q18 | A hardware button that cycles the preview source | not in v1 (the WebUI select covers it) |
| Q19 | DNG serial and camera label per camera | unchanged in v1; the `_cam1` folder tells them apart |
| Q20 | Which physical connector is MIPI1 on the Waveshare board | read the silkscreen; else, from power off, plug, boot, and read which I2C node registers |
| Q21 | The second sensor's model | a second IMX585 (every setting stays valid on both) |
| Q22 | timesyncd on shoots | fine: it raises the push rate during slews, not the skew |
| Q23 | The lock on in dual | you switch it on once; it is forwarded and saved in both |
| Q24 | Branch | a local, never-pushed `dual-sensor` branch in each repo on the Pi: Core cut from what the Pi runs when T57 starts (today `drop-frames` 9b5ea14; the refs here are at 31d5418, so re-grep them), UI from c153c33, driver from cd548ef. Nothing is pushed until you merge it |
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
| The first recorded frame is the first with ts/1000 ≥ recordingStartBootUs_ and a FrameDuration within max(500 µs, T/50) of the period (CC:9068-9073) | §6.2 | CONFIRMED; frame 0 can still slip a slot (R-new3) | R2, R-new3 |
| The lock's notion of recording is the gate flag, set only after the audio sleep and the writer start | §6.2, §7.4 | CONFIRMED (CC:8778-8782, 8813; 7631, 7649) | core-refs-5-8#3 |
| A timed stop needs a gate for ts ≥ `stop_us` and a wait: `stopRecording` closes the gate first (CC:7671) | §6.2 | CONFIRMED | R-new1, core-refs-5-8#2 |
| With Speed Ramp on, frames are numbered by count, not by time (CC:9334, 4641-4642) | §6.2, §7.6 | CONFIRMED | red-team#1 |
| ProRes and H.264 enqueue frame 0 at CC:10144-10145 and CC:10181-10184, each with its own counter, and number frames by count | §6.2 | CONFIRMED | refs/F4, red-team/RT-11 |
| A tally for a take Core does not record itself needs the `recording` event; App:8100 and 11965 set only the LED's initial value | §4.3 | CONFIRMED (App:10031-10034, 14465-14473) | core-refs-3-4#8 |
| The UI's recording cap drops a frame before it is counted, so `frameCounter` stops in a take | §5.2 | CONFIRMED (ApertarPreviewSocketClient.cpp:481-493) | ui-lib-drv-math#3 |
| At 720 MHz, 4K Clear HDR 16-bit caps at 25.000 fps, 4K SDR and 1080p at 50.000 fps | §2, Q5 | CONFIRMED (arithmetic from DRV:293, 3301-3314) | X3, ui-lib-drv-math#1 |
| A mid-take stretch leaves a phantom index hole (not the FrameDuration test) | §7.4 | CONFIRMED | S9 |
| Core's WDR/knob writes go to the first imx585 in readdir order | §3.2 | CONFIRMED | C4, C-new1, X-new1 |
| The socket path is unlinked then bound; a web-port failure exits 1 | §3.1, test lines | CONFIRMED | C1, C2 |
| XDG_CONFIG_HOME moves camera_settings, mode_ladder, UI.conf and the store notes together | §3.1 | CONFIRMED (not the hardware file, presets, ProRes cache) | C5, X11 |
| Pre-roll and trim env switches exist; pre-roll thread and power button need code | §3.3 | CONFIRMED | C7, C8 |
| apply_preset writes UI.conf keys (standby, photo mode; App:13996, 13978, 13981-14071), and its photo keys are camera keys too (App:13772-13786) | §3.3, §4.4 | CONFIRMED | P1, R5, core-refs-3-4#10, refs/F1 |
| `timecodeMode` sets the camera timecode when `cameraTimecodeMode` is absent (App:13973-13978); `cameraTimecodeMode` accepts only free_run or rec_run (App:13893-13896) | §4.4 | CONFIRMED | refs/F2 |
| With an enabled ladder, `set_mode_ladder` is refused when no rung can run in the current format (CC:10954-10956) | §4.4 | CONFIRMED | fixes-a/F14 |
| `handleCommand` answers read-only commands and aborts a safety-stop flush before it takes `commandMutex_` (App:12173-12180) | §4.1 | CONFIRMED | red-team/RT-6 |
| The local stop holds the controller's `mutex_` through its drain (CC:12264-12280) | §4.1 | CONFIRMED | red-team/RT-14 |
| `App::start` starts the media trim and watcher threads before the camera and the socket (App:8003-8013, 8034, 8056) | §3.4 | CONFIRMED | red-team/RT-2 |
| The buffer safety stop arrives as a plain `record_stop` (App:11039-11042, 11066-11068); only `safetyStopState().active` tells it apart (CC:4943, 12274). In frames mode it is off unless an env or `buffer_stop_percent` sets it (CC:5432-5441) | §6.2, T62, T64 | CONFIRMED | fixes-b/F5, red-team/RT-13 |
| Failure stops end the take through `checkRecordingFailure()` at four sites, not through `record_stop` (App:8265, 10883, 11216, 12195) | §6.2 | CONFIRMED | refs/F7, red-team/RT-13 |
| Every client gets every broadcast; fds go only with the buffer registration, not with the frame lines | §4.1, T65 | CONFIRMED | R7, U-new1, red-team#3 |
| The flat parser stops at the first `}` | §4.1 | CONFIRMED | R6, P15 |
| An `<img>` from :8000 loads :8001's MJPEG; a fetch gets 403 | §5.3 | CONFIRMED (Core); browser PROBABLE | U10, U11 |
| A bridge swap keeps the old frame; `render()` ignores visibility | §5.2 | CONFIRMED | U5, U-new7 |
| The HDMI picture is EMW (`hdmi_external_only` default true) | §5.2 | CONFIRMED (default); rig value PROBABLE | U6, K3 |
| Cinemate's sync is not real; its join is dead code | §1 | CONFIRMED | M6, M7 |
| Accuracy about 30-46 µs maximum between sensors (test 2.2 allows 55) | §7.5 | ESTIMATE (uncorrelated jitter only) | S12, `sim/` |
| `stopRecording` returns at once without a take of its own (CC:12266-12268), so a cam1-only or Sound Recorder take never reaches the gate's close at CC:7671 | §6.2, §7.4 | CONFIRMED | final/landed-RT4, final/rt-4 |
| A non-manual Start pre-roll waits up to 2 min for a requested trim before its guard (App:11190-11201) | §3.4, §4.3, T64 | CONFIRMED | final/landed-RT2a, final/refs-1 |
| `ladderOverride_` is not saved (CC.hpp:245), and `set_clear_hdr` with an unchanged value returns before it sets the override (CC:11524-11532) | §4.4 | CONFIRMED | final/rt-3 |
| Today's phase-lock log sits after the early return for an inactive lock (CC:8814-8820, 8856) | §7.4, test 1.2 | CONFIRMED | final/cons-17 |
| The frames queue holds 12 frames, 24 for compressed DNG (CC:4285-4290), and 50 is the lowest stop percent (BufferBudget.hpp); 4K Clear HDR 16-bit lossless JPEG encodes at about 17.5 fps | T64 | CONFIRMED (code); MEASURED (encoder, drop-frames README row 12) | final/landed-RT13a, final/refs-3 |
| A missing `APERTAR_HARDWARE_CONFIG` file falls back to the next existing candidate, the primary's (App:4908-4925, GpioInput.cpp:64-80) | T59 | CONFIRMED | final/landed-F13 |
