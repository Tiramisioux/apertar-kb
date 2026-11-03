<!-- Dual sensor, reader report 1 (2026-11-03): how Cinemate does dual sensors, end to end. Written by a read-only research agent on the Mac from git refs (cinemate d6cc93e, cinepi-raw 63a08d5, handbook c99ff77, libcamera cinemate bfe0b76a0, driver bd57617). Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Cinemate dual-sensor feature: code-cited research (read-only)

**Method and legend.** I read all code with `git show` and `git grep` on pinned refs and did not use the working trees. Citations are `file:line@tag`:

| Tag | Source |
|---|---|
| `@M` | cinemate dev `d6cc93e` (`src/module/` implied; `main.py` = `src/main.py`) |
| `@R` | cinepi-raw dev `63a08d5` (`cinepi/` implied unless `core/` or `preview/`) |
| `@H` | handbook `main` `c99ff77` (there is no `dev` branch) |
| `@L` | libcamera fork, branch `cinemate`, `bfe0b76a0` (which build the Pi runs is unknown) |
| `@D` | imx585 driver `bd57617` |
| `@S` | cinemate `efc7690b`, the last commit holding `system-review/` (removed from dev by `54cae555`) |

`development/dual-imx585-no-preview/` is untracked in the parent repo (mtime 2026-08-26) and is not pinned. Labels: **[C]** confirmed in code or log, **[P]** probable, **[U]** unconfirmed, with what would settle it.

## Headline

1. Dual means one `cinepi-raw` process per sensor. The processes share one Redis channel. They are coupled only by the Pi wall clock, a SysV shared-memory segment for preview, and a Redis record gate. [C]
2. Frame sync does **not** happen in dev. `--sync` never reaches libcamera, and the imx585 tuning has no `rpi.sync`. The docs claim sync anyway (`dual-sensors.md:3`, `changelog.md:69`@M). [C]
3. The mid-take "join" gate is very likely dead code (Q3). [P]
4. Dual preview was exercised on hardware on 2026-07-06 only. The record gate, PIP and join have no hardware report, and no test touches them. [C/U]
5. Nothing supervises or restarts a dead `cinepi-raw`. [C]

## Q1 Process model and discovery

- **Detection.** `discover_cameras()` runs `cinepi-raw --list-cameras` with a 10 s / 1 s retry. A regex parses `idx : model [fmt] (path)`, and the repeated ClearHDR block is de-duplicated (`cinepi_multi.py:209-247@M`). [C]
- **Port.** The port comes from the device-tree path: `i2c@88000` is cam0, `i2c@80000` or `i2c@70000` is cam1, and the default is cam0 (`:178-191`). [C]
- **Mode table.** `SensorDetect` probes at construction, plain and with `--hdr sensor`, and keeps the **first** model (`sensor_detect.py:648,2735-2760`; `cinepi_multi.py:1024-1027`). The mode table and the `sensor` key are therefore cam0's. [C]
- **Identity flags.** `--camera <libcamera idx>` selects the device. `--cam-port camN` is the label and is passed twice (`:682-683,793`). [C]
  - Before `f2ddc33c` (2026-07-06) `--camera` was missing. Both processes opened camera 0, and the second died with "device busy".
  - In cinepi-raw the label fills `options_->CamPort()`. If absent it is auto-detected from the camera id, then the device tree, then `"cam"+index` (`cinepi_options.cpp:37-154,408-418,633-650@R`).
- **Start order.** Cameras are sorted by port, and cam0 is primary (`:1007,1053`). `multi = len(cams)>1` (`:1047`). Each process starts, then `sleep(0.5)` (`:1060`).
  - The manager waits up to `_READY_WAIT = 2.0` s (`:70`; a comment says 10 s) for Redis `cinepi_ready_camN`. cinepi-raw writes it after the first `StartCamera` (`cinepi_raw.cpp:159-163@R`).
  - On timeout it only warns. The wait loop is duplicated (`:1062-1093`). [C]
- **Supervision.** There is none.
  - `CinePiProcess.run` only logs the exit (`:294-318`). Nothing in `main.py` or `mediator.py` restarts a process. [C]
  - Inside cinepi-raw, a 3 s frame timeout restarts the camera (`cinepi_raw.cpp:390-401@R`). An exception exits with -1 (`:493-497`).
  - Operator `restart camera` runs `stop_all()` then `start_all()` (`cinepi_controller.py:4014`). `stop_all` terminates each process in turn, escalating to kill after 5 s, and clears `cinepi_ready_*` (`:929-935,1329-1341`).
  - The Pi-4 clamp `cam._port="cam0"` is a no-op, because `port` is a read-only property (`:1004` vs `:178`).

| Aspect | cam0 / primary | cam1 / secondary |
|---|---|---|
| Sync flag | `--sync server` | `--sync client` (`:791-797`) |
| Post-process file | `/home/pi/post-processing{idx}.dual.json`, `role:primary` | same file pattern, `role:secondary`. Both files hold `sharedContext`, `mjpegPreview.port = 8000+idx`, and `dualHdmiPreview{role, pipScale, pipMargin, pipCorner}` (`:375-408,644-653`) |
| Preview flags | `--nopreview -p 94,50,fw-188,fh-100` (`:805-806`). Only the stage touches DRM | identical flags. The stage only publishes to shm |
| Per-camera values | tuning, geometry, `--unique-camera-model`, `--log-encode` and lores size come from its own model and `sensors.<port>` (`:616,638-650,656-658,868-925`) | same, from its own model |

- **Identical on both processes.**
  - `--mode W:H:bits:P` uses the shared `sensor_mode` index, looked up in each camera's own model table (`:565-575`).
  - `--hdr sensor` follows the shared `hdr` key. `--zoom`, `--max-pixel-rate` and `--buffer-count` are shared.
  - Recorder worker pools and affinity are shared, and both processes get `chrt -f 70`, `ionice` and `taskset -c 1-3` (`:297-312`). [C]
  - Nothing scales for two processes.
- **Phase lock.** cinemate never passes `--phase-lock`. The Redis key `fps_phase_lock` is seeded once from the first `sensors.camN.phase_lock` found (`cinepi_controller.py:128-138`). [C]
- **Settings.** `sensors.cam0|cam1.{geometry.{rotate_180,horizontal_flip,vertical_flip}, output.hdmi_port, override_camera_name, camera_name, phase_lock, tuning_file_override.{enabled,path}, log_encode}`. Rig-wide keys are `sensors.record_policy` (`follow_preview` or `always_both`), `raw_buffer_count` and `database_file` (`config_loader.py:529-566`). They are looked up by `cam.port` (`cinepi_multi.py:289-291`). [C]
- **Shipped default trap.** `settings.jsonc:464@M` ships `default_hdmi_source:"cam0"`, while code and docs say `both` (`config_loader.py:787`; `settings-json.md:421`). With `follow_preview`, a shipped dual rig previews and **records cam0 only** until the preview is `both`. [C]

## Q2 Control over Redis

- **Channel.** Both processes subscribe to the same `cp_controls` channel (`cinepi_controller.hpp:31`, `.cpp:1188@R`). The handler map is keyed by the published key name (`.cpp:770+`).
- **Writes.** cinemate's `set_value` does `SET` plus `PUBLISH cp_controls <key>`, with same-value dedup (`redis_controller.py:329-370@M`). There are **no** per-camera control keys (no `iso_cam1`). [C]

| Class | Keys |
|---|---|
| Shared. Every process applies them (`cinepi_state.hpp:21-59`; `cinepi_controller.cpp:180-194,770-1154@R`) | `iso, awb, cg_rb, shutter_a, shutter_s, fps, width, height, bit_depth, packing, mode, lores_width/height, compress, thumbnail(_size), zoom, hdr_threshold_low/high, hdr_blend, hdr_gain_adder, fps_phase_lock, pll_*, is_recording, cam_init`. Also `record_cams` (read on edges) and `hdmi_preview_source` (polled by the primary only) |
| Launch-time shared (cinemate side) | `hdr`, `log_encode_request` (resolved per camera), `anamorphic_factor`, `audio_capture_gain_db` |
| Per-camera outputs | `cinepi_ready_camN`, `timestamp_camN`, `tc_camN` and the `cameraPort` field in `cp_stats` (`cinepi_controller.cpp:648-676@R`); `last_dng_camN` and `log_encode_camN` (written by cinemate: `cinepi_multi.py:334,925`); the `cameras` JSON |

- **Counters are not per camera.** `cp_stats` is a shared channel. `frameCount`, `droppedFrames`, `bufferSize` and `writeFailures` are applied without checking `cameraPort`, so the last writer wins (`redis_listener.py:852-882`). Only the TC keys and the fps samples are split by port (`:885-921,1512-1531`). [C]
- **Two writers of `tc_camN`.** cinepi-raw and the cinemate listener both write it (finding F-202, `FINDINGS.md:45@S`). [C]
- **Launch values come from cam0.** Width, height, mode, packing and lores values are computed from cam0's table (`cinepi_multi.py:1029-1044`; `cinepi_controller.py:2545-2574`). A mixed pair would get cam0's mode string. [P]
- **Identity.** A process knows itself only through `--cam-port`. [C]
- **Mode change, in-place path.** For a same-aspect, same-bit-depth, same-HDR change, cinemate writes the shared keys and then `cam_init=<time_ns>` (`cinepi_controller.py:2526-2592,2711`). Each process reconfigures in place, record-through (`cinepi_controller.cpp:1027@R`; `cinepi_raw.cpp:68-125`). [C]
- **Mode change, relaunch path.** A change of aspect, bit depth or ClearHDR, when not recording, calls `cinepi.restart()` and relaunches **both** processes (`cinepi_controller.py:2762-2842`; `cinepi_multi.py:972`). [C]
- **HDR is rig-wide.** WDR is written on every sensor sub-device (`cinepi_controller.py:1218-1250`; `core/options.cpp:135-173@R`). [C]

## Q3 Recording

- **Gate setup.** `start_recording` publishes `record_cams` **before** it sets `is_recording=1` (`cinepi_controller.py:2353-2358`).
- **`_resolve_record_cams`.** (`:2244-2282`)
  - With a single sensor, the result is that port.
  - An explicit `cam0|cam1|both` override wins.
  - Otherwise it records both if the preview is `both` or `record_policy=always_both`.
  - Otherwise it records the preview's main sensor (`pip_camN` maps to `N`).
- **CLI.** `rec [cam0|cam1|both|dual|a|b|0|1] [s N|f N]` (`cli_commands.py:353-403`). [C]
- **In cinepi-raw.**
  - The `is_recording` handler sets `trigger_=±1` **and** `is_recording_=level` (`cinepi_controller.cpp:781-793@R`).
  - `triggerRec()` calls `recordCamsIncludesSelf()`, which does `GET record_cams`. Empty means true, `"both"` means true, otherwise a substring match on the own port (`.hpp:187-209,223-229`).
  - A sit-out sensor sets `baseline_flag_=1`, returns 0, keeps previewing and opens no folder. [C]
- **Start alignment.** There is none. `is_recording` is a level, and each process reacts on its own next frame, stamping its folder and TC with that frame's wall clock (`cinepi_raw.cpp:411-430`). No start timestamp or frame number is exchanged. [C]
- **Folder naming.** Each process names its own folder `CINEPI_%y-%m-%d_%H%M%S_F%02d_C%05d_<camPort>` (`utils.cpp:38-89@R`). It is not a shared base name. [C]
  - `C` is a per-process counter that starts at 0 and is incremented on every stop (`.hpp:243,301`).
  - The comment "parallel camera" at `utils.cpp:102` is stale.
- **DNG timecode.** TC is wall-clock HH:MM:SS plus `llround(sub_us*fps/1e6)` frames, anchored at the clip's first frame and then advanced by sensor-timestamp deltas (`dng_encoder.cpp:2059-2135`). [C]
  - cam1 has no offset. There is no `camPort` in `dng_encoder.cpp`.
  - Wall clock is `FrameWallClock`, or a cached BOOTTIME-to-REALTIME offset (`cinepi_controller.cpp:590-625`). The per-process anchor bug was fixed in `94102f7`.
  - Whether cam0 and cam1 TCs actually match on a rig is [U]. Compare `tc_cam0` and `tc_cam1`, or DNG TC at the same instant.
- **Mid-take join, cinemate side.** `_union_gate` and `_extend_record_gate_for_preview` run from `set_preview_source` while recording (`cinepi_controller.py:2284-2321,4256-4262`). [C]
- **Mid-take join, cinepi-raw side.** `triggerRec` clause 3 (`.hpp:307-324`) would open a fresh folder named with the join-frame time and the same `C` number, with the TC origin at the join frame. [C]
  - But it requires `!is_recording_`. The subscriber handler already set `is_recording_=true` on the sit-out process at the start edge, and nothing clears it (all writers: `.cpp:792`; `.hpp:225-243,270-322`; `cinepi_raw.cpp:73,373,450`). The branch therefore cannot fire in the normal flow. [P]
  - To settle it: run `rec cam0`, then `set preview both` mid-take, and look for "Gate opened mid-take" (`.hpp:320`) plus a `_cam1` folder.
  - Side effect [P]: after a local "RAM pool exhausted" stop (`cinepi_raw.cpp:448-452`), the same branch can re-open a clip while Redis still says recording.
- **Stop.** The shared stop edge makes every process do `clip_number_++`, close its folder and call `sound.record_stop()`. cinemate blocks the next take while `is_writing_buf` is set (`cinepi_controller.py:2345-2348`). [C]
- **Audio.**
  - There is no cam-port gating in `cinepi_sound.cpp`, so **every recording process** launches its own `cinepi-audio-capture` writing `<folder>/<folder>.wav` into its own clip folder (`cinepi_sound.cpp:835,844-875,920-949@R`). [C]
  - The ALSA devices are dsnoop (`cinemate-install.sh:1316-1353@M`), so one mic yields two WAVs. That concurrent capture has run on a rig is [U]; check both WAVs are non-empty.
  - The pkill risk: each process's `start()` runs `pkill -f "cinepi-audio-capture.*--discard-output"` and `pkill -f "alsaloop …"` (`cinepi_sound.cpp:615-637,761`). That also kills the other process's idle-VU helper, with no respawn until the next `record_stop` (`:981,1026`). [P]
  - Helpers are otherwise stopped by their own process group (`:695,976`).

## Q4 Preview

**Shared memory**
- **Segment.** SysV key `0x43494E44` ("CIND"), `shmget(..., IPC_CREAT|0600)` (`dualHdmiPreviewStage.cpp:66,178@R`).
- **Struct.** `{volatile u32 seq; u32 width, height; u8 data[1920*1088*3/2]}` is 3,133,452 B (`:80-86`). The frame is a tightly packed I420 lores frame, with stride equal to width.
- **No lock.** The secondary copies the frame, calls `__sync_synchronize()`, then does `seq+1` (`:453-466`). The primary reads in place. `last_seen_seq_` is write-only, so torn frames are possible. [C]
- **No staleness check.** There is no timestamp, so a dead secondary leaves a frozen cam1 pane. [C]
- **Never removed.** The segment is never removed, so an old-size or other-uid segment breaks later runs until reboot (`dual-imx585-no-preview/README.md:244-245`). [P]

**Roles**
- **Per-process.** `Read()` takes the role from the post-process file (`:163-170`). Both roles run `Process()` on the lores YUV420 stream; a non-YUV420 stream disables it (`:583-617`).
- **Primary.** Its `Configure()` zeroes `seq`, creates its own `make_drm_preview` (the core is `--nopreview`) and opens its own Redis connection (`:206-248`).
- **Source switching.** The primary polls `GET hdmi_preview_source` every 15 frames. Unknown values mean `both`. It does not use pub/sub (`:75-77,250-288,473-474`). [C]

**Canvas.** The canvas is `W·panes × H` YUV420 in two dma-heap buffers, reallocated on size change with `drm_->Reset()`. CPU writes are bracketed by `DMA_BUF_IOCTL_SYNC`. It composes into the back buffer, calls `Show`, then swaps. The background is Y=16, C=128 (`:290-338,502-508,576-580`). [C]

| Source | Canvas | Content |
|---|---|---|
| `both` | 2W×H | cam0 at x=0, cam1 at x=W. A 2 px white frame (Y=235) around each pane gives a 4 px centre divider |
| `cam0` | W×H | own frame |
| `cam1` | W×H | shared frame. Falls back to cam0 if no secondary |
| `pip_cam0` / `pip_cam1` | W×H | main pane plus an inset, with a nearest-neighbour downscale and a 2 px frame. Falls back to cam0 until the secondary is valid |

- **PIP inset.** Size is `⌊W·scale⌋&~1` by `⌊H·scale⌋&~1`, with margins `⌊W·m⌋&~1` and `⌊H·m⌋&~1`. It is drawn only if `iw,ih ≥ 2` and `iw+2mx < W` and `ih+2my < H`. The corner is chosen by substring (`right`, `lower` or `bottom`). Defaults are 0.28, 0.03 and `lower_right` (`:516-554`; `config_loader.py:788-792`). [C]
- **Fallback.** `have_secondary = seq≠0 && w==W && h==H` (`:477-488`). Different lores sizes therefore mean permanent fallback to cam0. In `both`, the right half is black while the canvas stays 2W wide. [C]
- **Display.** DRM `Show()` letterboxes the canvas into the `-p` window (`preview/drm_preview.cpp:578-593`). A `drmModeSetPlane` throw is not caught by the stage and likely aborts the process (`README.md` verdict `V-DRM-SETPLANE-ABORT`). [P]

**HDMI GUI (`simple_gui.py`).**
- It draws two columns (CAM0 and CAM1), per-camera clip names and per-camera LOG badges.
- It draws **no** guide box; the stage draws the frames inside the video.
- It runs on fbdev while the composite uses a DRM plane (`:653-673,875-888,1305-1339,2245-2252`@M). [C]

**Web GUI.**
- The browser pulls two MJPEG servers directly: `#stream` from `:8000/stream` and `#stream-cam1` from `:8001/stream`. Over HTTPS it uses the proxy `/preview/<cam>/stream` (`routes.py:21-110`; `template.html:1032-1033,1105`).
- The MJPEG port is `8000 + libcamera index`.
- Buttons `#preview-cam0-btn`, `#preview-cam1-btn` and `#preview-combined-btn` send `set preview X` via `/api/v1/cmd` (`template.html:1027-1031,1506-1524`; `api.py:103-120`).
- Dual layout and PIP are CSS with a fixed 28 % / 2.5 %. They ignore `hdmi_display.preview.pip` (`:513-525`). [C]

## Q5 Sync

- **`--sync` handling.** `--sync off|server|client` is parsed by the stock `VideoOptions` into `options_->sync` (`core/video_options.hpp:164-165,244-251@R`). Its only consumer is the phase-lock role gate: `roleClient = (sync==2)` (`cinepi_controller.cpp:1237`), after which `phaseLockStep` releases the lock (`phase_lock_core.hpp:75-80`). [C]
- **No libcamera sync.**
  - Only `core/rpicam_encoder.hpp:35-44,52-55` sets `controls::rpi::SyncMode` and drops frames until `SyncReady`.
  - `CinePIRecorder` derives from `RPiCamApp`, not `RPiCamEncoder`. Its `StartEncoder` and `EncodeBuffer` have neither (`cinepi_recorder.hpp:30,39-44,49-106`).
  - There is no other use of `SyncMode|SyncReady|SyncFrames|SyncTimer` in cinepi-raw. [C]
  - `dual-imx585-no-preview/README.md:242` reached the same conclusion independently.
  - cinepi-raw never waits for `SyncReady`.
  - The client is also not phase-locked, so cam1 free-runs. [C/P]
- **`rpi.sync` in libcamera.** `SyncMode` takes effect only if the tuning JSON contains `"rpi.sync":{}` (`ipa_base.cpp:1362-1389@L`).
  - pisp `imx477.json:1186-1189` has the block. pisp `imx585.json`, `imx585_mono.json` and `imx283.json` do not, and neither do cinemate's `resources/tuning_files`. [C]
  - It is a software scheme: UDP multicast `239.255.255.250:10000` every 30 frames, "ready" after 100 frames, and the client trims frame length when the error is ≥50 µs, all in the `FrameWallClock` domain (`sync.cpp:49-66,189-282@L`).
  - Stock libcamera lacks `FrameWallClock`; the fork supplies it (`pisp.cpp:1757@L`).
- **Commit `5b4b209`.** It is a **cinepi-raw** commit (2026-06-15) that touches only `cinepi_controller.{cpp,hpp}` and is on dev. It is not a cinemate commit. It does both things the Apertar note says: the phase-lock reference is the `FrameWallClock` epoch (`cinepi_controller.cpp:590-594,737@R`), and the lock is suppressed on the `--sync` client. [C]
- **Hardware sync.** There is no use of imx585 `sony,sync-mode` or XVS in cinemate or cinepi-raw. [C]
  - The driver supports `internal-leader` (the default), `internal-follower` and `external` (`imx585-overlay.dts:67,127`; `imx585.c:2379-2416@D`).
  - `overlay_line_for` emits only `model,port[,mono][,ccmp][,link-frequency]` (`boot_config.py:180-211@M`).
  - A default dual imx585 rig therefore has two free-running leaders.
- **To settle whether sync ever engaged.** [U] Run with `LIBCAMERA_LOG_LEVELS=IPARPI:INFO,RPiSync:DEBUG` and look for "Sync mode set to …". Or compare the cam0 and cam1 `timestamp_camN` drift.

## Q6 `subdev_binding.hpp`

- **Why it exists.** The probe used the first `/dev/v4l-subdevN` exposing "Mode Binning/Mode Crop*". On two sensors both processes bound to the same subdev, so cam1's decompand table and ActiveArea used cam0's values (`subdev_binding.hpp:15-27@R`; `core/driver_mode_metadata.hpp:41-54`). [C]
- **How it maps.** `read_driver_mode_metadata(m, camera_id_hint)` scans subdevs 0..31 and records each candidate's sysfs name (`:239-257,307-420`). Then `choose_subdev_candidate` decides (`subdev_binding.hpp:91-117`):
  - 0 candidates: none found.
  - 1 candidate: use it. The hint is ignored.
  - 2 or more: exact string match of the hint, else AMBIGUOUS. The caller then falls back to ratio-derived binning and logs one stderr line.
  - The hint is `RPiCamApp::CameraId()` (`cinepi_raw.cpp:189-190`; `core/options.cpp:383,434`). [C]
- **Likely gap.** The header assumes `Camera::id()` equals the kernel subdev name (e.g. `imx585 6-001a`). But `--list-cameras` prints the id as a DT path, `/base/axi/pcie@1000120000/rp1/i2c@88000/imx585@1a` (`options.cpp:383`; `_test/test_clearhdr_probe_state.py:210`@M). On a two-imx585 rig it is therefore probably always AMBIGUOUS, which is safe but not a real bind. [P] To settle it, compare `cam->id()` with `/sys/class/video4linux/v4l-subdev*/name`.
- **Not covered.** The ClearHDR live knobs still use the first matching subdev (`cinepi_controller.cpp:79-93`). The WDR write still hits all subdevs. [C]

## Q7 Known problems and lessons

- **Hardware log and open threads.** `lessons/hardware-log.md` has no dual-sensor entry. Line 430@H only notes a rig "rewired (dual → single)" before 2026-08-26, and line 1052 "dual-probe" means mode enumeration. `open-threads.md` has no dual entry. [C]
- **Diagnosis `dual-imx585-no-preview`.**
  - It is a 10-stage SSH ladder written 2026-08-26 for the symptom "dual-imx585 + ClearHDR: nothing on HDMI, resolution changes still work" (`README.md:6-18`).
  - Its status: it was **never run on a live Pi**. `runs/latest/verdict.txt` is `V-UNREACHABLE` at `192.0.2.1`, and the other run directories are same-minute synthetic runs. No root cause and no fix were established. [C]
  - The identical symptom on 2026-08-26 on a single imx585 mono CM5 was a broken CSI cable ("it was the cable"), on a rig that had just been rewired from dual to single (`hardware-log.md:401-462@H`). The dual premise was therefore probably superseded. [P]
  - The harness's dual-only suspects stay untested: a DRM-master race, a WDR cross-write from the secondary's `Options::Parse`, and shm hazards.
  - It recorded real code issues in passing: `--sync` not reaching libcamera, `lores_width` 1273 vs 1272, a `sharedContext` shm key collision (`ftok("/tmp", 0x43494E45)`, with `IPC_RMID` by the first process to exit), and shm never removed (`README.md:242-245`). [C]
- **Pairs and modes run.**
  - imx585 dual ran in 2025-06 (`589b585@R`: "dual sensors now work if imx585 link frequency is not used").
  - There is no evidence of an imx477 pair or a mixed pair on hardware.
  - A mixed pair appears only as a parser fixture (`_test/test_clearhdr_probe_state.py:68-100`@M).
  - The docs example is an imx296 colour + mono pair (`config-txt.md:56-61`@M), which is not evidence of a run. [C absence / U overall]
- **No measured limits.**
  - There are no dual fps or bandwidth measurements anywhere, and no dual-specific caps in code.
  - Each process gets the same `--max-pixel-rate` (380 or 580 MPix/s), the same worker pools (`storage_profiles.py:53-93`) and CPUs 1-3, plus its own CMA buffers.
  - The only hard limits are a 1920×1088 pane in shm and the ports 8000/8001.
  - Whether two 4K ClearHDR sensors sustain is [U]. Settle it with a dual soak watching CFE and drop counters.
- **Maturity.**
  - No test covers `record_cams`, `_resolve_record_cams`, the dual post-process file or the stage. The one exception is `test_no_camera_boot_integration.py`, which covers source resolution.
  - The stage header still says "hardware-untested" (`dualHdmiPreviewStage.cpp:20-21`).
  - `system-review` called the stage "638 LOC that has never run" (`CODE-MAP-cinepi-raw.md:298@S`).

## Q8 Hardware prerequisites

- **config.txt.** One `dtoverlay=<model>,camN[,mono][,ccmp][,link-frequency=N]` line per port, plus a single `camera_auto_detect` where 0 wins if any sensor needs 0 (`boot_config.py:180-211,360-406@M`).
  - The installer supports one sensor only (`cinemate-install.sh:24,1041-1078`).
  - Example: `config-txt.md:56-61`.
- **Platform notes.** Pi 5 has two 4-lane ports and needs kernel 6.12.93+rpt (`raspberry-pi-models.md:7,9`). On CM4, cam0 is 2-lane and cam1 is 4-lane, and CineMate "only ever drives cam0" on Pi 4 and CM4 (`cef168.py:539`).
- **CM carrier jumpers.** `dual-sensors.md:47-48` says "connect the JC GPIO pins" per the Raspberry Pi docs. `raspberry-pi-models.md:25` calls it "camera jumpers (J6 on the official IO board)". Whether "JC" means J6 is [U]. [C quote]
- **I²C buses.** [C]
  - Pi 5: cam0 is i2c-6 (`rp1/i2c@88000`) and cam1 is i2c-4 (`i2c@80000`) (`ir_filter.py:9-12`).
  - CM5IO: cam0 is i2c-6 and cam1 is i2c-0 (`i2c@70000`) (`lens/cef168.py:544-551,622-624`).
  - CM4: cam0 is bus 0 (`working/the-lens-adapter.md:21@H`).

## Q9 Command surface

- **Same dispatcher.** CLI, serial and `POST /api/v1/cmd` share one dispatcher.
- **Preview.** `set preview [both|cam0|cam1|cam0+cam1|pip_cam0|pip|pip0|pip_cam1|pip1|a|b|0|1|2]` cycles both → cam0 → cam1 → pip_cam0 → pip_cam1 (`cli_commands.py:190`; `cinepi_controller.py:4215-4262`).
- **Record.** `rec [cam0|cam1|both|dual] [s|f n]` (`cli_commands.py:353-403`).
- **Hardware buttons.** The GPIO action catalog offers `set_preview_source` (cycle, or one of five values) and `rec` (policy-based). There is **no** GPIO action for `rec camN` (`settings_editor.py:125,176-177`). [C]
- **Web.** Three-button switcher, an expander "HDMI PREVIEW" select, and tap-to-record (`template.html:1026-1031,2125-2129,2296-2297`).
- **Settings editor, Camera 1 card.**
  - It exposes rotate_180, HDMI port, phase_lock, tuning override, log, and `record_policy`.
  - It does **not** expose the flips or the name. A save resets `sensors.cam1.{horizontal_flip,vertical_flip,override_camera_name,camera_name}` (`settings_editor.html:1750-1810`; `settings-json.md:95-99`; `hardware-log.md:2112-2117@H`). [C]
  - PIP scale and margin are file-only. The Boot-config pane writes the cam0 and cam1 overlays.

## Q10 History

The cinemate dev branch has 2229 commits, about 31 of them dual-ish. cinepi-raw dev has 408, about 14 dual-ish.

| Date | Commit (M / R) | Meaning |
|---|---|---|
| 2025-06-14 | `73bf5437` / `70aac7b`, `1475f78` | first "fix dual sensor recording" |
| 2025-06-23 | `589b585`@R | dual works "if imx585 link frequency is not used" |
| 2025-07-03 | `91975e88` | rec-flag debounce for alternating frame counts |
| 2025-07-20 | `31ae9373` / `c74c820` | per-camera wall-clock TC |
| 2026-06-04 | `566c3b2e`, `9bf6274b` | per-camera settings under `cam0/cam1` |
| 2026-06-15 | `5b4b209`@R | phase-lock role gate and wall-clock reference |
| 2026-06-21 | `fb6a9a31` | route TC by `cameraPort` |
| 2026-07-06 | `6953d512`, `b346ce99`, `f2ddc33c` / `5072543`, `db1fbad`, `94102f7`, `cb4a30c`, `7cc9c25` | dual stage, `--camera` fix, TC offset fix, dma-buf sync, double buffering |
| 2026-07-07/08 | `a7440443`, `79002866` / `c19e316`, `87e6fee` | record gate, PIP, join |
| 2026-08-25 | `cbfa6e23` | `record_policy` naming |
| 2026-09-19 | `950b611b` … `fec70bd7` | web live-view switcher |
| 2026-09-20..26 | `0242e5a`, `4c451e1`, `3ac26de`@R | subdev binding |

- **Assessment.** It is a prototype built in a 3-day July 2026 sprint on a 2025 base.
- **Evidence of hardware use.** The dma-buf "static" and "drifting bands" fixes of 2026-07-06 show that day's hardware run.
- **No hardware reports.** I found none for the record gate or the join.
- **Code since.** The stage has not changed since 2026-07-07 apart from subdev-probe edits.
- **Gate caveat.** No commit message claims a hardware test of the record gate or the join.

## Design essence

1. Run one capture process per sensor: `--camera idx` selects the device and `--cam-port` is the label. The label drives the folder suffix, the `*_camN` keys and the `cameraPort` field in stats.
2. Use one control channel with un-suffixed shared keys that every process applies. Return per-camera data only through suffixed output keys.
3. Compute the mode, size and lores values once, from cam0. This assumes same-model sensors or at least compatible mode tables.
4. Launch cam0 first, stagger by 0.5 s, and wait for a per-camera ready flag. Restart both processes on aspect, bit-depth or HDR changes; otherwise reconfigure in place with a `cam_init` kick. Add the supervision Cinemate lacks.
5. Implement a record gate as one Redis string `record_cams`. Publish it before the record flag. Have each process read it on the record edge, with empty meaning "both", and let sit-out sensors keep previewing.
6. Resolve the policy on the controller side: override, then `always_both`, then preview `both`, then the preview's main sensor.
7. Give each process its own clip folder `CINEPI_<ts>_F<ff>_C<n>_<camN>` and its own WAV. Take the name and TC from the first frame's per-frame wall clock.
8. Derive TC only from a shared wall-clock domain (`FrameWallClock` or a cached BOOTTIME-to-REALTIME offset), never from a per-process anchor.
9. Let exactly one process own the display. The secondary publishes lores I420 into SysV shm (key `CIND`, packed, with a seq counter). The primary composites into a double-buffered, dma-buf-synced canvas.
10. Offer five sources, `both`, `cam0`, `cam1` and the two `pip_*`. The primary polls a Redis key about every 0.5 s. Bake PIP geometry and the role into a generated per-process post-process JSON.
11. Show the web GUI two direct MJPEG servers (port `8000 + idx`) and let the client lay them out. Use the same `set preview` command as the HDMI GUI.
12. For genuine sync, set `SyncMode` in the capture app and ship `rpi.sync` in the tuning. Cinemate does neither. Optionally gate recording on `SyncReady`, which Cinemate also skips.
13. Role-gate the phase-lock servo: absolute wall-clock servo on a lone sensor or the server, none on the client.
14. Bind every V4L2 sub-device access to the process's own sensor, and key stats and counters by camera.

## Pitfalls Cinemate hit

(H) = hit, with commit evidence. (L) = latent, found in this review.

- (H) Missing `--camera` meant the second process lost the device ("busy") (`f2ddc33c`).
- (H) A cached dma-heap canvas without `DMA_BUF_IOCTL_SYNC` showed static (`cb4a30c`). A single canvas gave drifting bands (`7cc9c25`).
- (H) A per-process TC anchor left a fixed one-frame offset between cameras (`94102f7`).
- (H) Alternating frame counts made `rec` flicker (`91975e88`). The listener now ignores a lower non-zero count.
- (H) `tc_camN` had two writers. `cp_stats` needed `cameraPort` (`fb6a9a31`, F-202).
- (H) The sync claim is false in code: `--sync` only flips the phase-lock role, `rpi.sync` is absent from the imx585 tuning, and the client runs undisciplined.
- (L) The mid-take join gate is defeated by the handler pre-setting `is_recording_`.
- (L) The shipped `default_hdmi_source="cam0"` combined with `follow_preview` means dual rigs record cam0 only.
- (L) shm is never removed, so wrong-size or other-uid segments cause `EINVAL`/`EACCES`. The `sharedContext` key is shared by both processes.
- (L) A stale secondary frame is never detected, and the pane sizes must be identical.
- (L) Sub-device cross-binding. The binding hint is probably ambiguous because `Camera::id()` is a DT path. ClearHDR knobs and WDR still hit the first or all subdevs.
- (L) The pattern-based `pkill` in the audio start kills the other process's idle-VU helper.
- (L) `cp_stats` counters, `fps_actual` and the drop and sync analysis are not per camera.
- (L) The ready wait is 2 s and unsupervised. A port-bind failure on 8000+idx kills the process after 10 retries (`mjpegPreviewStage.cpp:250-282`). The port is derived from the libcamera index, not the port label.
- (L) The settings-editor save resets cam1 flip and name keys. A string `log_encode` is truthy (`hardware-log.md:921-928@H`).
- (L) Both processes share the same CPUs, worker pools and CMA with no dual scaling.
- Diagnostic lesson: "black preview, resolution changes still work" on 2026-08-26 was a dead CSI cable, not dual logic.
