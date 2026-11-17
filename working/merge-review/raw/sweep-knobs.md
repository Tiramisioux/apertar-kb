# Sweep X1: every knob the port adds

Whole-port sweep for one kind of problem: environment variables, config keys, runtime files, root helpers.
Read-only. Written 2026-11-17.

| Ref | Meaning |
| --- | --- |
| `@port` | Core `cinemate-port` `01f170c`, UI `cinemate-port` `7ea9afc` |
| `@up` | `upstream-1.6.0` (Core `35dbe67`, UI `43888e5`), read in `/home/user/wt/*-upstream` |
| `@main` | fork `origin/main` (Core `f60e301`, UI `4415a55`) |
| `@04fe197` | Core improvement branch `claude/awesome-pasteur-qzsiow` (the chip fix) |
| `App`, `CC`, `WCP` | `src/ApertarCoreApp.cpp`, `src/camera/CameraController.cpp`, `src/web/WebControlPage.cpp` |

A line number without a ref is `@port`. Labels: **confirmed** (read in code), **probable**, **unconfirmed**.

## 1. Result in short

| Kind | Original Apertar 1.6.0 | The port adds | Verdict count |
| --- | --- | --- | --- |
| Env vars, Core | 47 (44 read by the binary, 3 by the start script). None in `README.md` | 42 (39 binary, 3 start script) | remove 27, fold 1, developer-only 14 |
| Env vars, UI | 33 | 1 | developer-only 1 |
| `apertar-hardware.conf` | 19 sections | 3 sections (`[media]`, `[camera]`, `[gpio_switches]`), 7 `[storage]` keys, gesture keys, `remoteN`, 2 dead keys, 4 changed `[display]` defaults | keep wiring keys; fold 8; remove 6; revert 4 defaults |
| `camera_settings.conf` | 33 keys (38 `@main`) | 12 keys | keep 10, remove 1, retarget 1 |
| `UI.conf` `[General]` | 56 keys Core reads | 18 keys | keep 18 |
| Config files | 5 for Core (`apertar-hardware.conf`, `camera_settings.conf`, `UI.conf`, `apertar-color-profiles.conf`, `/home/pi/.apertar-tuning`) | 3 (`~/apertar-media-tune.conf`, its `/run` override, `mode_ladder.conf`) | fold 3 |
| State, cache and marker files | 1 cache, 6 `/run` markers | 3 state files, 2 backups, 1 cache folder, 2 `/run` folders, 1 clip marker, 2 sidecars | remove the 2 `/run` folders; the rest stays with its feature |
| Root helpers | 2 C++ helpers and 1 wait script, all in the UI repo, sudoers with every argument listed | 3 shell helpers and 3 sudoers files in Core, 1 `tmpfiles.d` file, 1 CLI tool, `LimitRTPRIO=80` | remove 1 chain, fold 2 |
| Driver parameters | - | imx585: 1 module param, 1 overlay param. imx283: 2 module params, 1 overlay param | see section 9 |

The three things that matter most:

1. **Knobs whose default changes a stock camera** (section 11, X-knobs-2 to 5): the display fallback, the automatic
   storage pre-roll, temporal denoise off for H.264 and ProRes too, the record gate.
2. **One setting, several ways to set it** (X-knobs-6, 7, 8): write-path tuning has four layers; five storage
   switches have an env var, a hardware-file key, a socket command and a UI switch each.
3. **Experiment leftovers** (X-knobs-9, 10, 11, 12): 27 env vars, one root helper chain that never ran, one flag
   file nobody reads, one setting nothing uses.

The owner's request (GPIO chip back on the Controls card) is done on the improvement branch (`04fe197`).
Two small things are still open there: X-knobs-1.

## 2. Method

| Step | Command |
| --- | --- |
| Env names per tree | `git -C <repo> grep -hoE '\b(APERTAR\|QBC\|QRAW\|CINEMATE\|CINEPI)_[A-Z0-9_]+\b' <ref> -- .`, then `comm` between `cinemate-port`, `origin/main`, `upstream-1.6.0` |
| Read sites | `grep -rnE '"APERTAR_[A-Z0-9_]+"' src`; `getenv`, `qgetenv`, `qEnvironmentVariable*`, `unsignedEnvValue`, `boolEnvValue`, `tuningOverride`, shell `${APERTAR_...}` |
| First commit of a name | `git log --reverse -S'<name>' --format='%h %ad %s' upstream-1.6.0..cinemate-port` |
| Hardware-file keys | the template (`App:5031-5191`), `HardwareConfigText.hpp:46-69` (sections) and `:451-480` (`knownKey`), `BufferBudget.hpp:150-195`, `StoragePreroll.hpp:46-88`, `CC:2941-2981`, `GpioInput.cpp:255-420` |
| `camera_settings.conf` keys | keys written by `writeCaptureSettings` (`CC:742@up`, `CC:761@main`, `CC:936@port`), `comm` |
| `UI.conf` keys | `key == "..."` branches of `readSharedUiSettings` (`App:1641@up`, `App:1983@port`), `comm` |
| Files | path literals in `src` (`/run/`, `/tmp/`, `.cache`, `.config`, `/home/pi/`, `/boot/`, `*.conf`, `*.json`), `comm` against upstream |
| Helpers | `ls scripts config` in both trees; `grep -rn 'sudo'`; UI `systemd/` |
| KB status | `grep -rn '<name>' /home/user/apertar-kb --include=*.md`; values used: `grep -rhoE '<name>=[A-Za-z0-9._-]+'` |
| One compile check | a scratch copy of `ControlsModel.hpp` with the chip lines back, `g++ -std=c++20`, printed `peripheralSettingsJson` and `checkEdits` (section 11) |

`QBC_*`: no hit in any tree. `raw/conv-core-command-plane.md` and `raw/conv-core-camera.md` were used as the yardstick
(rules C1-S07, C1-R2, C1-R3, C2-R5).

## 3. What original Apertar has (the measuring stick)

### 3.1 Environment variables

| Group | Count | Names | Purpose |
| --- | --- | --- | --- |
| Paths | 6 | `APERTAR_HARDWARE_CONFIG`, `APERTAR_COLOR_PROFILE_CONFIG`, `APERTAR_DEFAULT_TUNING_DIR`, `APERTAR_MEDIA_ROOT`, `APERTAR_H264_LIBAV_PLUGIN`, `APERTAR_PRORES_PLUGIN` | Where a file, folder or plugin is |
| Set by Core for itself | 1 | `APERTAR_SENSOR_TUNING_FILE` | Hand-over to the colour code (`CC:1114-1120@up`) |
| H.264 bench | 17 | `APERTAR_H264_{ENCODER,PRESET,TUNE,CRF,QP,BITRATE,MAXRATE,BUFSIZE,X264_PARAMS,BACKEND,THREADS,PIPE_BYTES,QUEUE_FRAMES,SIZE,CAMERA_BUFFERS,KEEP_RAW_STREAM,SINGLE_STREAM}` | Encoder tuning (`CC:4333-4467@up`) |
| ProRes bench | 10 | `APERTAR_PRORES_{CAMERA_BUFFERS,CACHED_DMABUF,THREADS,CSC_THREADS,ODIRECT,WRITEBACK,WRITER_THREAD,WRITER_QUEUE,WRITER_QUEUE_MB,WRITER_SLOW_MS}` | Encoder and writer tuning (`ProresEncoder.cpp:831-1203@up`) |
| cDNG / lossy DNG bench | 10 | `APERTAR_CDNG_{QUEUE_FRAMES,WORKERS,WORKER_NICE,TILE_ROWS,PROFILE_DETAIL}`, `APERTAR_LOSSYDNG_{WORKERS,WRITER_BYTES,ASYNCWRITE}`, `QRAW_LOSSYDNG_ASYNCWRITE` (old name), `APERTAR_RAW_CACHED_DMABUF` | Queue, workers, buffers (`CC:3330-3359@up`) |
| Start script | 3 | `APERTAR_CORE_BIN`, `APERTAR_SOCKET_PATH`, `APERTAR_TUNING_FILE` | `scripts/start-apertar-core.sh:4-17@up` |
| UI and its scripts | 33 | sockets, ready files, DRM device, runtime mirror, `APERTAR_PREVIEW_FORCE_{CPU,EGL,PLANAR}`, two helper test modes | Process wiring and display selection |

Facts that set the rule (all **confirmed**):

| Fact | Evidence |
| --- | --- |
| No env var is in the README | `grep -c APERTAR_ README.md` = 0 `@up` (Core and UI) |
| No env var has a twin in a config file, a socket command or a UI control | none of the 47 names appears in `App` command code or in `WCP@up` |
| An env var is a bench knob or a path. It is read with `unsignedEnvValue` / `boolEnvValue` | `CC:1027`, `CC:1041@up` |
| A bench knob can also come from a file, for sweeps without a restart | `tuningOverride()`: environment first, then `/home/pi/.apertar-tuning`, `NAME=VALUE` per line, re-read at clip open (`src/prores/ProresEncoder.cpp:770-813@up`, comment "BENCH TUNING OVERRIDE") |
| Launch options are the documented process switches | README "Launch Options": `--socket`, `--media`, `--web-bind`, `--web-port`, `--simulate` (`README.md:248-259@up`) |

### 3.2 Files

| File | Owner | What goes in it |
| --- | --- | --- |
| `/home/pi/apertar-hardware.conf` | each hardware class parses its own section (C1-S07) | Wiring: buses, addresses, pins, actions per pin, display geometry, mount path |
| `~/.config/apertar-core/camera_settings.conf` | `CameraController` | Every camera setting a `set_*` command changes, per record-format profile (`CC:742-778@up`) |
| `~/.config/CinePi/UI.conf` `[General]` | touch UI, Core `App` | Monitoring aids and UI preferences (`App:1641-1813@up`) |
| `/home/pi/apertar-color-profiles.conf` | `ColorProfileConfig.cpp` | Colour matrices, hand-made |
| `/home/pi/.apertar-tuning` | `ProresEncoder.cpp` | Bench overrides, absent in production |
| `~/.cache/apertar-prores/<profile>.json` | `ProresIspProfile.cpp:228-230@up` | Derived tuning, a cache |
| `/run/apertar-ui/*`, `/run/apertar-cfe/ready`, `/run/apertar-standby-*`, `/run/apertar-network/*` | UI, helpers | Runtime markers |

Per-mode limits are code, not config: the lossless ISO cap is a literal (`settings.iso = std::min<uint32_t>(settings.iso, 800u);`
`CC:2483@up`), the fps limits are a table (`maximumSupportedFpsForResolution`, `CC:2629@up`).

### 3.3 Privileged helpers

| Item | Where | Form |
| --- | --- | --- |
| `apertar-standby-low-power`, `apertar-standby-usb` | UI repo, C++ (`src/StandbyLowPower.cpp`, `src/StandbyUsbPower.cpp`, `CMakeLists.txt:152-154@up`) | Called by Core as `timeout 6s sudo -n /usr/local/libexec/...` (`App:1544-1549@up`) |
| Their sudoers rules | UI repo `systemd/*.sudoers@up` | Every allowed argument is written out: `... apertar-standby-usb off, ... apertar-standby-usb on` |
| One-line root actions | Core calls the tool itself | `sudo -n install -m 644 <tmp> /boot/firmware/config.txt` (`App:3157@up`), `sudo -n blockdev --flushbufs` (`App:3353@up`), `sudo -n mount` (`App:3623@up`), `sudo -n systemctl`, `sudo -n timedatectl` |
| Core `config/` | 1 file | systemd drop-in `apertar-core-capture-priority.conf`: `LimitNICE=-5`, comment "Permit only a bounded, non-real-time boost" |
| Install text in the README | none | The Apertar image carries the units and rules |

## 4. Table A: environment variables only the port has

43 names: 42 in Core, 1 in the UI. `APERTAR_SENSOR_PROBE` (`CC:7239`) came with fork `main` (`f60e301`), not the port.
"KB" = what the knowledge base says about the knob. "Twin" = the same thing can be set another way.

| # | Variable | Read at | Default; bounds | What it changes | Twin | README | Added by | KB | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `APERTAR_AUDIO_BUFFER_MS` | `src/audio/AudioRecordingSession.cpp:215` | 100; 100..4000 | ALSA capture ring on the record path | - | no | `60ce8e9` | The 1 s ring made the drift figure worse; the comment at `:208-211` says "the old ring is the default again" | **remove** |
| 2 | `APERTAR_BOOT_CONFIG` | `App:3507` | `/boot/firmware/config.txt` | The file the Boot Config card and the fan mode read and write | - | no | `2955ef8` | never set | **developer-only** (a path, like `APERTAR_HARDWARE_CONFIG`) |
| 3 | `APERTAR_CDNG_BUFFER` | `App:276`, `CC:5503` | unset: the file key, else `frames` | Write queue `frames` or `ram` | `[storage] buffer`, `set_buffer_mode`, WebUI, touch UI | no | `d44b177` | - | **remove** (twin) |
| 4 | `APERTAR_CDNG_BUFFER_STOP_PERCENT` | `CC:5515` | unset: the file key, else 90 in ram, 0 in frames; 0 or 50..99 | Safety stop threshold | `[storage] buffer_stop_percent` | no | `d44b177` | `=50` used twice | **developer-only** (drop the file key) |
| 5 | `APERTAR_CDNG_FRAMES_PER_FOLDER` | `App:266`, `App:283`, `CC:4293` | unset: the file key, else 0; 0 or 100..100000 | Frames per `part_NNN` folder | `[storage] frames_per_folder`, `set_frames_per_folder`, WebUI | `:355` | `d7dd337` | NVMe campaign instrument | **remove** (twin) |
| 6 | `APERTAR_CDNG_QUEUE_RAM_FRACTION` | `CC:5535` | 0.6 | Share of `MemAvailable` for the ram queue | `[storage] buffer_ram_fraction` | no | `d44b177` | never set | **developer-only** (drop the file key) |
| 7 | `APERTAR_CDNG_QUEUE_RAM_FLOOR_MB` | `CC:5536` | 512 | Memory kept free | `[storage] buffer_ram_floor_mb` | no | `d44b177` | never set | **developer-only** (drop the file key) |
| 8 | `APERTAR_CDNG_QUEUE_RAM_MAX_FRACTION` | `CC:5537` | 0.5 | Ceiling as a share of `MemTotal` | `[storage] buffer_ram_max_fraction` | no | `d44b177` | never set | **developer-only** (drop the file key) |
| 9 | `APERTAR_CDNG_UNCOMPRESSED_WORKERS` | `CC:4320` | media profile (4 on exFAT and ext4, 2 else); 1..8 | Uncompressed cDNG writer threads | tune file `workers` | no | `26da30e` | "a diagnostic, not a setting" (`working/dng-chain-answer.md` 5.3) | **developer-only** (sibling of `APERTAR_CDNG_WORKERS`, `CC:3343@up`) |
| 10 | `APERTAR_CLIP_MERGE` | `App:268`, `App:285` | unset: the file key, else on | `0` stops the merge worker | `[storage] clip_merge`, `set_clip_merge`, WebUI | `:356` | `ba0658d` | campaign instrument | **remove** (twin) |
| 11 | `APERTAR_DEAD_MEDIUM_STOP_MS` | `CC:4469` | 2000; 100..600000 | How long a stop on a dead drive waits for writers | - | no | `0b1632f` | never set | **remove** (make it a constant) |
| 12 | `APERTAR_DNG_DONTNEED` | `src/cdng/CdngEncoder.cpp:87` | `sync`; `sync`, `writer`, `off` | When a written DNG's pages leave the page cache | tune file `dontneed` | `:348` | `0ed07ea` | `sync` made 4K Clear HDR 16-bit clean (`lessons/hardware-log.md` 2026-11-01); `writer` is what upstream does | **developer-only** |
| 13 | `APERTAR_DNG_PAYLOAD_COPY` | `CdngEncoder.cpp:137` | off | `1` puts every payload through the scratch buffer again | - | `:345` | `e55557d` | restore switch; `tools/dng_payload_write_test.sh` proves the new path byte-identical | **remove** |
| 14 | `APERTAR_DNG_WRITEBACK` | `CC:4718` | on | `sync_file_range` per written DNG | tune file `writeback` | `:349` | `441e42a` | - | **developer-only** (sibling of `APERTAR_PRORES_WRITEBACK`) |
| 15 | `APERTAR_DNG_WRITE_ROWS` | `CdngEncoder.cpp:118` | 64; 1..4096 | Rows per `write()` on the scratch path | - | `:346` | `e55557d` | never set | **developer-only** (sibling of `APERTAR_CDNG_TILE_ROWS`) |
| 16 | `APERTAR_FPS_LIMIT` | `CC:3401` | unset: the startup probe is the limit; `table`: min(table, probe) | Source of the sensor fps ceiling | - | no | `d44b177` | `=table` 7 times | **remove** (restore switch; choose the default) |
| 17 | `APERTAR_FPS_RAMP_GRACE_FRAMES` | `CC:9759` | max(10, requests + 6); 1..200 | Frames ignored by the drop count and the phase lock after an fps change | - | no | `faa2958` | `=200` once | **developer-only** |
| 18 | `APERTAR_IMX283_PROBE_FPS` | `CC:3393` | off | `1`: the IMX283 ceiling is the probe alone, not min(probe, driver floor table) | driver param `crop_vmax` | no | `c48e693` | never set | **remove** (X-knobs-17) |
| 19 | `APERTAR_IMX585_MIN_MODE_WIDTH` | `src/camera/Imx585Modes.hpp:107` | 1280 | Hides sensor modes narrower than N; 0 shows all | - | no | `caa0153` | never set | **remove** (constant) |
| 20 | `APERTAR_LOSSLESS_FPS_LIMIT` | `CC:3120` | unset: the mode's maximum | Caps IMX585 lossless cDNG fps; `30` is the upstream cap (`CC:2485-2486@up`) | - | no | `d44b177` | `=30` once | **remove** (restore switch) |
| 21 | `APERTAR_MEDIA_MIN_FREE_MB` | `App:11379` | 1024 | Free-space floor of the record gate | - | no | `438a342` | never set | **remove** (constant) |
| 22 | `APERTAR_MEDIA_REQUIRE_MOUNT` | `App:11335` | gate on | `0` lets a take start when the media root is not a mount point | `--simulate` | no | `438a342` | `=0` on a dev machine | **fold** into a launch option (X-knobs-5) |
| 23 | `APERTAR_MEDIA_RUN_DIR` | `src/util/MediaIntent.hpp:23`, `scripts/apertar-media-tune:30` | `/run/apertar-media` | Folder of the eject flags and of the root helper's saved values | - | no | `438a342` | never set | **remove** (X-knobs-10, 11) |
| 24 | `APERTAR_MEDIA_SYNC_MS` | `CC:4365` | 1000; 0..60000 | Interval of the fsync thread; 0 = off | tune file `sync_ms` | `:350` | `4ce382e` | - | **developer-only** |
| 25 | `APERTAR_MEDIA_TRIM` | `App:6402` | on | `0` forces the trim off | `media_trim` setting, `set_media_trim`, WebUI | `:305` | `d44b177` | - | **remove** (twin) |
| 26 | `APERTAR_MEDIA_TUNE` | `App:11402` | off | `1` runs the root helper `apertar-media-tune` at mount | tune file `kernel_tune` | `:357` | `26da30e` | the helper was never installed on the rig; "not recommended" as a default | **remove** (X-knobs-10) |
| 27-30 | `APERTAR_PHASE_LOCK_KP`, `_KI`, `_DEADBAND_US`, `_CLAMP_US` | `CC:8918-8921` | 0.06, 0.0015, 6, 150 (`FramePhaseLock.hpp:38-41`) | Servo gains of the phase lock | - | no | `80ddac1` | never set | **remove** (the defaults in `FramePhaseLock.hpp` stay) |
| 31 | `APERTAR_PHASE_LOCK_LOG` | `CC:8971` | off | A trace line every 250 frames | - | no | `80ddac1` | `=1` five times | **developer-only** |
| 32 | `APERTAR_PLAYBACK_WORKERS` | `src/playback/PlaybackFrames.cpp:82` | 2; 1..4 | Decode slots of the WebUI playback | - | no | `1af26c8` | never set | **remove** (constant) |
| 33 | `APERTAR_RAW_CAMERA_BUFFERS` | `CC:1469` | tune file, else 4 (8 in Clear HDR) + filesystem extra; 3..16 | Raw camera buffers, one request each | tune file `raw_buffers`, `extra_raw_buffers` | `:351` | `db17860` | 8, 10, 12 tried; "buffers only delay the first skip" | **developer-only** (sibling of `APERTAR_H264_CAMERA_BUFFERS`, `CC:1127@up`) |
| 34 | `APERTAR_RAW_COPY_WORKERS` | `CC:4386` | 1; 1..2 | Raw copy worker threads | - | no | `351a3ee` | "only if `drop[copy-slot]` ever appears (never has)" (`working/dng-chain/F/F6.md:119`) | **remove** |
| 35 | `APERTAR_RAW_POOL_WARM` | `CC:4897` | on | `0` restores the cold raw pool | - | `:347` | `4abbef0` | "expected effect on drops near zero" | **remove** |
| 36-38 | `APERTAR_RT`, `APERTAR_RT_PRIORITY`, `APERTAR_RT_CPUS` | `scripts/start-apertar-core.sh:26-28` | off; 70; `1-3` | Whole process under `chrt -f`, `ionice -c2 -n0`, `taskset` | - | `:354` | `c57c284` | scheduling ruled out (`hardware-log.md` 2026-11-01); README itself: "not a recommendation" | **remove** |
| 39 | `APERTAR_RT_CAPTURE_PRIORITY` | `CC:9113` | 0 = off; 1..99 | `SCHED_FIFO` for libcamera's completion thread | - | `:353` | `6ef0ddc` | "92 (6.1 %): no effect" (`hardware-log.md:954`) | **remove**, with `LimitRTPRIO=80` |
| 40 | `APERTAR_STORAGE_PREROLL` | `App:278`, `App:11154` | unset: the file key, else on | `0` or `1` forces the automatic pre-roll | `[media] preroll`, `set_storage_preroll`, WebUI, touch UI | no | `d44b177` | - | **remove** (twin) |
| 41 | `APERTAR_WEB_PREVIEW_RECORDING_FPS` | `App:96` | 30; 0..30 | WebUI preview rate while a raw take runs | - | `:352` | `fb557e9` | "a mitigation, not the fix" | **developer-only** |
| 42 | `APERTAR_WRITE_STALL_MS` | `CC:4861` | 5000; 1000..600000 | No write progress this long = drive gone | - | no | `a3ac8da` | never set | **remove** (constant) |
| 43 | `APERTAR_UI_PREVIEW_RECORDING_FPS` (UI) | `Apertar-UI/src/ApertarPreviewSocketClient.cpp:29` | unset = every frame | Touch UI preview frames per second during a take | - | no | UI `c234d77` | "keep as the test instrument, never a default" (`working/drop-frames/inspection-raw/synthesis-draft.md:368`) | **developer-only** |

Who sets them: nobody but a developer, through a systemd drop-in with `Environment=`. No operator setting is among them.
The README documents 16 of them (13 rows at `README.md:345-357`, and `APERTAR_MEDIA_TRIM` at `:305`), which upstream never does.

Three more env knobs lived only inside the UI history: `APERTAR_PREVIEW_PLANE`, `APERTAR_PREVIEW_PEAKING`,
`APERTAR_PREVIEW_DIRECT` (added `c13b846`, `a51c95e`, `4724007`, `322d329`; dropped `010f8ad`, `c153c33`, `b333343`,
`1c7a3ad`). Net change: none (`PreviewWindowRenderer.cpp` is not in `git diff --stat origin/main cinemate-port`). X-knobs-18.

## 5. Table B: `apertar-hardware.conf`

| Section, key | Reader | Default | What it is | Who sets it | Command / UI | README | Added by | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `[storage] buffer` | `src/util/BufferBudget.hpp:178`; used in `CC:5505` (`planQueueBuffer`) | `frames` | Write queue: 12 frames, or a RAM budget | operator | `set_buffer_mode` (`App:12829`); WebUI; touch UI | no | `d44b177` | **fold** into `camera_settings.conf` (X-knobs-7) |
| `[storage] buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction` | `BufferBudget.hpp:180-186` | 0.6, 512, 0.5 | RAM budget numbers | developer | text only | no | `d44b177` | **remove** the keys; the env vars 6-8 stay as bench knobs |
| `[storage] buffer_stop_percent` | `BufferBudget.hpp:184` | 90 in ram, off in frames | Safety stop | developer | text only | no | `d44b177` | **remove** the key; env var 4 stays |
| `[storage] frames_per_folder` | `BufferBudget.hpp:188` | 0 | Frames per `part_NNN` folder | operator | `set_frames_per_folder` (`App:12857`); WebUI | yes | `d7dd337` | **fold** (X-knobs-7) |
| `[storage] clip_merge` | `BufferBudget.hpp:190` | on | Merge split clips when idle | operator | `set_clip_merge` (`App:12857`); WebUI | yes | `ba0658d` | **fold** (X-knobs-7) |
| `[media] preroll` (new section) | `src/util/StoragePreroll.hpp:83`; `App:11152` | **on** | Automatic 2 s test take at Core start, card insert, after a format | operator | `set_storage_preroll` (`App:12900`); WebUI; touch UI | no | `d44b177` | **fold**, and default off (X-knobs-3) |
| `[media] preroll_seconds` | `StoragePreroll.hpp:85` | 2; 1..10 | Length of that take | developer | text only | no | `d44b177` | **fold** |
| `[camera] clear_hdr_iso_max_12bit`, `clear_hdr_iso_max_16bit` (new section) | `CC:2941-2981` (`loadCameraSection`), own parser | 720, 1585; 0 = no cap | Highest ISO in Clear HDR | developer | text only; Core restart | no | `8175273` | **fold** into code constants (X-knobs-13) |
| `[gpio_switches]` (new section): `enabled`, `switchN_pins`, `switchN_on`, `switchN_off`, `switchN_position0..2` | `src/hardware/GpioInput.cpp:311-338` | off | Two- and three-way switches | rig builder | `set_controls`; WebUI Controls | no | `c34f844` | **keep** (wiring, in the wiring file) |
| `[gpio_buttons] dN_single`, `_double`, `_triple`, `_hold` | `GpioInput.cpp:358-381` | none | Click and hold actions | rig builder | `set_controls`; WebUI Controls | no | `0a98868` | **keep** |
| `[gpio_encoders] encoderN_single` ... `_hold` | `GpioInput.cpp:403-410` | none | The same for an encoder's push | rig builder | `set_controls` | no | `c140c4f` | **keep** |
| `[pcf8574] pinN_single` ... `_hold`; `[neorotary4] encoderN_single` ... `_hold` | `src/hardware/Pcf8574Input.cpp:458`, `NeoRotary4Input.cpp:634` | none | The same | rig builder | `set_controls` | no | `c140c4f` | **keep** |
| `[gpio_buttons] remoteN` (+ the four gesture keys) | `src/hardware/ControlsModel.hpp:142-149`; `GpioInput` skips it (no pin) | none | A button that exists only in the WebUI's Remote controls | operator | `set_controls`; WebUI | no | `9b5ea14` | **fold**: not GPIO; it works with `[gpio_buttons] enabled=false` too. Own section, for example `[remote_buttons]` |
| `hold_ms`, `double_ms` in `[gpio_buttons]`, `[pcf8574]`, `[neorotary4]` | **nobody**. Accepted by `knownKey` (`src/hardware/HardwareConfigText.hpp:457`, `:466`, `:470`). The times are constants (`src/hardware/ButtonGesture.hpp:16-18`) | - | Nothing | - | `set_controls` writes them | no | `3526e4b` | **remove** (X-knobs-12) |
| `[gpio_buttons] chip`, `poll_ms` (upstream keys) | `GpioInput.cpp:343-349`; `GpioInput.cpp:431@up` | `auto`, 12 | GPIO chip, poll interval | rig builder | text; off the Controls card since `c140c4f`; back in `04fe197` | no | - | **keep** (X-knobs-1) |
| `[display] ui_width`, `ui_height`, `ui_layout`, `hdmi_external_only` (upstream keys, **defaults changed**) | template `App:5089-5098`; `Apertar-UI/src/DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357`; `DisplayConfigBridge.hpp:52-59` | 1920, 1080, `landscape_large`, `true` (upstream: 720, 720, `square`, `false`) | Fallback when the file or the keys are missing | - | - | no | Core `7af9f13`, UI `7c41a27` | **revert** (X-knobs-2) |
| Template only | `App:5112-5158` | - | `[imu]` shows `sync_mode` instead of bus, address, ranges; `[pcf8574] bus` 10 to 1; `[neorotary4]`, `[gpio_encoders]`, `[grove_analog]` shown | - | - | - | several | file reviewers |

## 6. Table C: `camera_settings.conf`

Port adds 12 keys (`writeCaptureSettings`, `CC:936-986`). All go through `CaptureSettings` (`include/apertar/core/Types.hpp`), the upstream place (C1-R2).
The operator sets them, through the command and the UI named in the row. None is in the README except `preview_tdn` (`README.md:315-325`).

| Key | Default | What it changes | Command | WebUI / touch UI | Preset key | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `cdng_log` | `off` | CineMate Log curve in cDNG and lossy DNG | `set_cdng_log` | yes / yes | `cameraCdngLog` | keep |
| `clip_name_template` | `{format}_{date}_{clip}` (the old names) | Clip folder and file names | `set_clip_name_template` | yes / yes | `cameraClipNameTemplate` | keep |
| `conform_fps` | 25 | **Nothing** ("Nothing derives from it yet", `Types.hpp`; commit `d7ff071`) | `set_conform_fps` (`App:13270`) | no / no | `cameraConformFps` | **remove** (X-knobs-12) |
| `fps_phase_lock` | false | Closed-loop frame cadence | `set_fps_phase_lock` | yes / no | `cameraFpsPhaseLock` | keep |
| `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`, `fps_speed_ramp_after` | false, false, `stay` | FPS may change during a take | `set_fps_speed_ramp` | yes / no | `cameraFpsSpeedRamp*` | keep |
| `fps_speed_ramp_stretch_audio` | **true** | After a ramped take Core runs `nice -n 15 rubberband ...` (`CC:9978`). Needs the `rubberband-cli` package; not in the README | `set_fps_speed_ramp` | yes / no | `cameraFpsSpeedRampAudio` | keep, default false (the code calls it "Experimental") |
| `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` | false | Memory flags: "Clear HDR stopped auto ISO; SDR turns it back on" | none | - | - | keep (state, not a knob) |
| `media_trim` | **true** | Core runs `fstrim` through a root helper after deletes and at mount | `set_media_trim` (`App:13194`) | yes / no | - | keep |
| `preview_tdn` | **false** | Strips temporal denoise from the tuning libcamera loads, **for every record format** (`CC:7308-7318`, `CC:7412`) | `set_preview_tdn` (`App:13205`) | yes / no | - | **retarget** (X-knobs-4) |

Format note (**confirmed**): upstream writes booleans as `0` / `1` (`output << prefix << "iso_auto=" << s.isoAuto`, `CC:749@up`).
The port writes six of its booleans as `true` / `false` (`fps_phase_lock`, `preview_tdn`, `media_trim`, the three ramp
switches, `CC:974-979`) and two as `0` / `1` (`CC:945`, `CC:956`). The reader takes both. `clear_hdr=true|false` started it `@main`.

## 7. Table D: `UI.conf` `[General]`

18 keys, read in `readSharedUiSettings` (`App:1983-2196`), written by the touch UI's `QSettings` and by `set_value_steps`
and the toggle commands. This is the upstream place for monitoring aids and UI preferences (C1-N12, C1-R3). All **keep**.

| Keys | Default | What |
| --- | --- | --- |
| `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps` | empty = the built-in lists | Value lists of the pickers |
| `isoFree`, `shutterAngleFree`, `fpsFree`, `wbFree` + `*FreeIncrement` | false; 100, 1, 1, 100 | Free stepping instead of a list |
| `flickerFreeShutterAngles`, `mainsHz` | false, 50 | Flicker-free angles in the list |
| `recordingFrameEnabled`, `frameBufferBarEnabled` | false, false | Red frame while recording; buffer bar |
| `recordingRedTimecodeEnabled` | **true** | Red timecode while recording. Upstream has it fixed on the camera page (`qml/CameraPage.qml:3747@up`); new on the HDMI monitor (`qml/ExternalMonitorWindow.qml:1208`) |
| `audioRecordedOutlineEnabled` | **true** | New: a faint red outline on the audio meter while sound is recorded |

The two default-on switches change what a stock screen shows. Small; listed for the stock-behaviour sweep.

## 8. Table E: files the port reads or writes at run time

| File | Written by | Read by | What | Upstream precedent | Verdict |
| --- | --- | --- | --- | --- | --- |
| `/home/pi/apertar-media-tune.conf` | `scripts/apertar-tune init`, by hand (template `config/apertar-media-tune.conf`) | `src/util/MediaTune.hpp:27`, `:285-291` | Write-path knobs per medium: `dontneed`, `writeback`, `sync_ms`, `raw_buffers`, `extra_raw_buffers`, `workers`, `queue`, `kernel_tune`; sections `[default]`, `[<fs>]`, `[<class>]`, `[<class>.<fs>]` | `/home/pi/.apertar-tuning` (`ProresEncoder.cpp:770-813@up`) | **fold** (X-knobs-6) |
| `/run/apertar-media/media-tune.override.conf` | `scripts/apertar-tune set/unset/clear` | `MediaTune.hpp:28` | The same keys, for a test night, gone at reboot | the same | **fold** (X-knobs-6) |
| `~/.config/apertar-core/mode_ladder.conf` | `CC:10939-10945` | `CC:10510-10514` | `enabled`, `ramp_ready`, `resolutions` | `camera_settings.conf` in the same folder; `modeLadderPath()` (`CC:404-415`) copies `persistedSettingsPath()` (`CC:417-428`) | **fold** (X-knobs-14) |
| `/run/apertar-media/eject/<device>` | `App:4389` (`writeEjectIntent`), cleared `App:4355`, `App:10917` | **nobody** (no hit for `apertar-media` in `Apertar-UI/src`) | "Do not remount this drive" flag for an automounter | none | **remove**, or write the reader (X-knobs-11) |
| `/run/apertar-media/tune/{queue_*,vm_*,nvme_ps_max_latency}` | root helper `scripts/apertar-media-tune` | the same helper, on restore | Saved kernel values | `/run/apertar-standby-low-power/settings` | **remove** with the helper (X-knobs-10) |
| `~/.config/apertar-core/hardware-state.conf`, `hardware-last-written.conf`, `hardware-history/*.conf` (20 kept, `adopted-<rev>.conf`) | `src/hardware/HardwareConfigStore.cpp:377`, `:388-410`, `:462` | the store | Who wrote the hardware file last, its last text, replaced versions | none (upstream saves with `.tmp` and rename, `App:5343@up`) | internal; stays if the store stays (file reviewers) |
| `<hardware file>.bak` | `HardwareConfigStore.cpp:357` | a person | Previous file on a WebUI save | none | internal |
| `/boot/firmware/config.txt.apertar.bak` | `App:3548`, `scripts/apertar-boot-config`, `App:3595` | a person | Previous `config.txt` | none | keep |
| `~/.cache/apertar-core/tuning/<name>_notdn.json` and `.src` | `src/camera/TuningTdnStrip.hpp:409-411` | libcamera | Tuning copy without `tdn` | `~/.cache/apertar-prores/<profile>.json` (`ProresIspProfile.cpp:230@up`) | keep |
| `<clip>/.parts`, `<clip>/part_NNN/` | `CC:4297-4312` | Core, touch UI (`Apertar-UI/src/ClipFrameFiles.hpp`), `tools/flatten_clip.py` | Split-clip marker and folders | none | with the feature |
| `<clip>/fps-ramp.txt`, `<clip>/<clip>_stretched.wav` | `CC` (ramp), `rubberband` | a person, the editor | Ramp sidecars | upstream sidecars (WAV, `.gcsv`) | with the feature |
| `/tmp/apertar-stretch-<clip>.map`, `/tmp/apertar-boot-config-<pid>.txt` | `CC:9953`, `App:3571` | `rubberband`, the helper | Temporary | `App:3147@up` | keep |
| `*.apertar-preset.json`: 14 new `camera*` keys | preset writer in `App` | `apply_preset` | `cameraCdngLog`, `cameraClipNameTemplate`, `cameraConformFps`, `cameraFpsPhaseLock`, `cameraFpsSpeedRamp`, `...After`, `...Audio`, `...Shutter`, `cameraTimecodeMode`, `cameraClearHdr`, four `cameraHdr*` | the preset file | keep; `cameraConformFps` goes with `conform_fps` |

The media tune template restates the built-in defaults in 9 of its 10 value lines (**confirmed** against
`CdngEncoder.cpp:88-97`, `CC:4365`, `CC:4718`, `src/util/MediaProfile.hpp:140-142`). The one that differs is
`raw_buffers = 8`, which replaces 4 in SDR. The KB calls the values "the current state, not a measured optimum"
(`working/drop-frames/media-tune-file.md`).

## 9. Table F: root helpers, sudoers, units, scripts; Table G: drivers

Who sets these up: the installer (the person who builds the image), with the `sudo install` lines the port's README gives.

| Item | What it does | Called from | Argument check | Verdict |
| --- | --- | --- | --- | --- |
| `scripts/apertar-boot-config` + `config/apertar-boot-config.sudoers` | Replaces `/boot/firmware/config.txt` from stdin, keeps a backup | `App:3580-3592`, second of three write routes: direct (`App:3546-3567`), helper, `sudo -n install` (`App:3595-3598`) | rule pins the path and no arguments | **fold**: one route. Upstream's is `sudo -n install` (`App:3157@up`) (X-knobs-16) |
| `scripts/apertar-media-trim` + `config/apertar-media-trim.sudoers` | `fstrim -v` on a mount under `/media/`, 20 s limit | `App:11484` | rule pins the path only; the script checks the argument | **fold**: `sudo -n fstrim` from Core, as upstream calls `sudo -n blockdev` (`App:3353@up`); or keep it beside the UI's helpers with the argument written into the rule (X-knobs-16) |
| `scripts/apertar-media-tune` + `config/apertar-media.sudoers` | Sets `vm.dirty_*`, block scheduler, `nr_requests`, NVMe APST for the recording drive | `App:11396-11430`, only with `APERTAR_MEDIA_TUNE=1` or `kernel_tune = on` | rule pins the path only; the helper takes `APERTAR_MEDIA_RUN_DIR` from the environment | **remove** (X-knobs-10) |
| `config/apertar-media.tmpfiles.conf` | Creates `/run/apertar-media` (pi), `/eject` (pi), `/tune` (root) | - | - | **remove** with X-knobs-10 and 11; the override file goes with X-knobs-6 |
| `scripts/apertar-tune` (487 lines, Python, not root) | Edits the override file; `show`, `set`, `unset`, `clear`, `init` | a developer | - | **remove** with X-knobs-6 |
| `config/apertar-core-capture-priority.conf`: `LimitRTPRIO=80` added | Allows `SCHED_FIFO` up to 80 | the unit | - | **remove** (X-knobs-9). The upstream comment in the same file says "non-real-time boost" |
| `scripts/start-apertar-core.sh`: the `APERTAR_RT` block (lines 20-41) | `chrt -f 70 ionice -c2 -n0 taskset -c 1-3` | the unit | - | **remove** (X-knobs-9) |
| README install blocks | Three `sudo install` recipes (`README.md:202-203`, `:308-309`, `:354`) | - | - | upstream README has none; move to the image notes |

Drivers (named in the brief; not the centre of this sweep):

| Driver | Knob | Default | Purpose | Verdict |
| --- | --- | --- | --- | --- |
| imx585 | module param `clearhdr_windowed_binning` (`imx585.c:1039-1042`) | off | "WP-585-9 hardware gate only": offers unvalidated 12-bit Clear HDR crops | developer-only test switch; remove when the gate is decided |
| imx585 | overlay param `ccmp` -> `sony,clearhdr-ccmp` (`imx585-overlay.dts:138`, `imx585.c:4641-4643`) | on for colour, opt-in for mono | 12-bit Clear HDR on a mono sensor | keep (an overlay parameter is where upstream puts sensor options: `mono`, `link-frequency`) |
| imx283 | module param `experimental_modes` (`imx283.c:269-270`) | off | 16 unvalidated modes | developer-only |
| imx283 | module param `crop_vmax` (`imx283.c:277-281`) | **1** ("experimental, UNMEASURED") | Per-crop VMAX floor, more fps on vertical crops | X-knobs-17 |
| imx283 | overlay param `link-frequency` (`imx283-overlay.dts:117`) | 720 MHz | The second link rate the driver accepts | keep |
| both | read-only custom controls (5 in imx585, 7 in imx283) | - | Report binning and crop of the mode | not knobs |

## 10. Layering: one thing, how many ways to set it

| Thing | Env | Override file | File key | Setting + command | UI | State fields that exist only to explain the override |
| --- | --- | --- | --- | --- | --- | --- |
| Buffer mode | `APERTAR_CDNG_BUFFER` | - | `[storage] buffer` | `set_buffer_mode` writes the file key | WebUI, touch UI | `buffer_setting`, `buffer_note` |
| Frames per folder | `APERTAR_CDNG_FRAMES_PER_FOLDER` | - | `[storage] frames_per_folder` | `set_frames_per_folder` writes the file key | WebUI | `frames_per_folder_env` (`App:266`) |
| Clip merge | `APERTAR_CLIP_MERGE` | - | `[storage] clip_merge` | `set_clip_merge` writes the file key | WebUI | `clip_merge_env_off` (`App:268`) |
| Pre-roll | `APERTAR_STORAGE_PREROLL` | - | `[media] preroll` | `set_storage_preroll` writes the file key | WebUI, touch UI | `storage_preroll_auto_env` (`App:262`; 7 uses in `WCP`) |
| Trim | `APERTAR_MEDIA_TRIM` | - | - | `media_trim` in `camera_settings.conf`, `set_media_trim` | WebUI | `media_trim_env_off` (`App:9585`) |
| Page-cache drop, writeback, sync interval, raw buffers, writers, queue, kernel tune | 7 env vars | `/run/.../media-tune.override.conf` | `~/apertar-media-tune.conf` | - | - | `tune_override=` in the take line |

Upstream: one way each (section 3.1). Storage switches sit in three stores on the port: `[storage]`, `[media]`,
`camera_settings.conf`.

## 11. Findings

Severity is for the merge into original Apertar. "Deliberate" = the commit or the KB says the port chose it.

### X-knobs-1 (minor, knob, deliberate): GPIO chip on the Controls card. Fixed in `04fe197`; two leftovers

| Fact | Evidence |
| --- | --- |
| `chip` is an upstream key in `[gpio]` / `[gpio_buttons]`, `[gpio_encoders]`, `[trigger_output]`, `[recording_indicator]` | `src/hardware/GpioInput.cpp:431-432@up`, `TriggerOutput.cpp:311@up`, `RecordingIndicatorOutput.cpp:319@up`, `:347@up` |
| The upstream UI first-run template defines it | `chip=auto` in `[gpio_buttons]` and `[gpio_encoders]`: `Apertar-UI/src/DisplayConfigBridge.cpp:161`, `:172@up` |
| The port's readers still read it | `GpioInput.cpp:343-344`, `TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:312`, `:340` |
| The port's Controls card had the field (`166cc4d`) and dropped it with `poll_ms` (`c140c4f`: "The GPIO card's settings drop poll and chip (edge events need neither)") | `src/hardware/ControlsModel.hpp:263`: `// poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither` |
| The port removed the UI template that showed `chip=auto` | UI `c9d841f` |
| Fixed on the improvement branch | `04fe197`: `chip` and `poll_ms` back in `peripheralSettings("gpio_buttons")`, `chip` in the trigger and tally lists, validator and page per chip |

Checked here (scratch copy, `@port` plus the two lines): the lines compile, `peripheralSettingsJson` shows
`{"key":"chip",...,"value":"/dev/gpiochip4","in_file":true}` for a file that says `gpiochip=/dev/gpiochip4`, and the
page draws any `text` setting without a change (`WCP:17738-17746`).

Still open `@04fe197`:

| Leftover | Evidence | Fix |
| --- | --- | --- |
| `set_controls` refuses `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` in `[gpio_encoders]` with "is not a key of [gpio_encoders] that Apertar reads". The reader reads all five there (`GpioInput.cpp:343-355`); the upstream template writes them there (`DisplayConfigBridge.cpp:172-176@up`) | `HardwareConfigText.hpp:460-462@04fe197`; reproduced with `checkEdits` on the scratch build | Add the five names to the `gpio_encoders` branch of `knownKey`, as the `gpio_buttons` branch has them. Or, because the reader keeps one value for both sections (the later line wins, `GpioInput.cpp:343-355`), keep refusing them and say so: "Set chip, pull, active_low, poll_ms and debounce_ms in [gpio_buttons]: the encoders share them." |
| No template shows the key any more. Core's `[gpio]`, `[gpio_encoders]` and `[gpio_switches]` blocks have no `chip=` line (`App:5137-5150`), and the UI template that had it is gone | see above | Add `chip=auto` under `enabled=false` in `[gpio]` and `[gpio_encoders]` of `defaultHardwareConfigTemplate()`, the way `[trigger_output]` and `[recording_indicator]` show `gpiochip=auto` (`App:5168`, `App:5182`) |
| Not run on a Pi with a second GPIO chip | commit message of `04fe197` | `gpiodetect; journalctl -u apertar-core \| grep 'GPIO input'` with an expander |

### X-knobs-2 (blocker, stock-behaviour-change, deliberate): the display fallback is the contributor's HDMI rig

| | Original | Port |
| --- | --- | --- |
| Fallback size, layout | 720 x 720, `square` (`DisplayConfigBridge.cpp:14-15@up`, `:579@up`; `.hpp:52@up`) | 1920 x 1080, `landscape_large` (`DisplayConfigBridge.cpp:11-12`, `:289`; `.hpp:52-54`) |
| Fallback `hdmi_external_only` | `false` (`:584@up`, `:649@up`) | `true` (`:294`, `:357`; `.hpp:59`) |
| Core template `[display]` | 720, 720, `square`, `false` (`App:4320-4329@up`) | 1920, 1080, `landscape_large`, `true` (`App:5089-5098`) |
| File missing | the UI writes a template first (`ensureDefaultHardwareConfigFile`, `:41@up`, `:587@up`) | nothing is written (UI `c9d841f`) |

Commits: Core `7af9f13`, UI `7c41a27` ("HDMI 1080p is the display fallback", T38 part 5).
Consequence (**confirmed** in code): with `hdmi_external_only` the main window is hidden (`window->hide()`,
`Apertar-UI/src/main.cpp:428-429@up`). A stock Apertar with its built-in screen and no `[display]` keys then shows
no touch UI (**probable** for the dark panel; needs the panel: delete the keys, restart `apertar-ui-direct`).
Fix: put the four values back in the five places. The HDMI rig keeps its own values in its own `apertar-hardware.conf`:

```ini
[display]
ui_width=1920
ui_height=1080
ui_layout=landscape_large
hdmi_external_only=true
```

### X-knobs-3 (major, stock-behaviour-change, deliberate): the storage pre-roll runs by itself

`[media] preroll` defaults to on (`return conf.automatic.value_or(true);`, `src/util/StoragePreroll.hpp:98`; template comment
`# preroll=on`, `App:5070`). Core then records a 2 s take at the sensor's maximum fps and deletes it at every Core start,
card insert and format (`App:10957`, `App:14631`). Upstream has no pre-roll.

| KB says | Where |
| --- | --- |
| "No author of either stack states what it warms; no measurement exists" | `working/dng-chain-answer.md` section 4 |
| "record is refused for three to five seconds after a start"; 0.7 to 1.5 GB written and deleted each time | the same |
| "until it runs [the A/B], the honest default is off for the automatic triggers" | the same |
| The port's own rule before it was built: "a setting (`storage_preroll`, default off at first), never a hidden step" | `working/drop-frames/README.md:341` |

Fix: `value_or(false)`, the template comment `# preroll=off`, and the README gains one line. The manual
`storage_preroll` command stays.

### X-knobs-4 (major, stock-behaviour-change, default deliberate, reach probably not): `preview_tdn=false` also takes temporal denoise out of H.264 and ProRes

`bool previewTdn = false;` (`include/apertar/core/Types.hpp:139`). The strip runs for every format:

```cpp
        const auto loadablePath = [&](const std::string &path) {
            activePath = path;
            if (!settings.previewTdn) {                       // CC:7311: no test of the record format
                std::string note;
                activePath = tuning::previewTuningPath(path, tuningPipeline, note);
```

and the ProRes colour tuning is derived from the stripped file (`makeProresIspTuning(activePath, ...)`, `CC:7412`).
For raw formats the ISP picture is the preview. For H.264 and ProRes it is the recording. So a stock camera
records H.264 and ProRes without temporal denoise after the merge, and a tuning file the user picked is stripped
too. The README says "The recorded DNGs ... do not change either way" and is silent about the other two formats
(`README.md:317`).
Fix, upstream style (one test in the existing lambda with upstream's own helper `isProcessedVideoFormat`,
`CC:221@up`, `CC:280`; no new knob):

```cpp
            if (!settings.previewTdn && !isProcessedVideoFormat(settings.recordingFormat) && !settings.photoModeEnabled) {
```

Photo mode is left out too: JPEG, PNG and TIFF stills are made from the ISP picture (`encodeProcessedJpeg`, `CC:2095`).
Or keep upstream behaviour everywhere: `bool previewTdn = true;`.
On the Pi: `journalctl -u apertar-core | grep 'tuning file'` in ProRes must end in `preview_tdn=on` or show the
unstripped path.

### X-knobs-5 (major, stock-behaviour-change, deliberate): a plain folder as media root is refused; the way out is an env var nobody documents

| | Original | Port |
| --- | --- | --- |
| `record_start`, `capture_photo`, `timelapse_start` with `--media <folder>` that is not a mount point | allowed. Only the Sound Recorder needs mounted media (`App:8351@up`). README: "An existing folder by itself does not prove that an external drive is mounted there" (a warning, `README.md:246@up`) | refused: "No media mounted at <root>." (`App:12596-12600`, `App:11359-11384`) |
| Free space | no floor | refused under 1024 MiB (`App:11378-11382`) |
| Way out | - | `--simulate`, or `APERTAR_MEDIA_REQUIRE_MOUNT=0` (`App:11335`); `APERTAR_MEDIA_MIN_FREE_MB` (`App:11379`). Neither is in the README |

The gate has a reason (a take with no drive lands on the SD card). The opt-out is in the wrong place.
Fix: a launch option beside `--media` (`src/main.cpp`, `ApertarCoreApp::Options`, README "Launch Options"):

| Option | Purpose |
| --- | --- |
| `--allow-unmounted-media` | Record into `--media PATH` even when it is not a mount point. For a development machine or an SD-card rig. |

`mediaGateBypassed()` returns `options_.simulateCamera || options_.allowUnmountedMedia`. Drop both env vars; the
floor becomes `constexpr uint64_t kMinFreeMiB = 1024;`.

### X-knobs-6 (major, duplication, deliberate): a second bench-tuning mechanism beside upstream's `.apertar-tuning`

The port's write-path knobs resolve through four layers: env var, `/run/apertar-media/media-tune.override.conf`,
`/home/pi/apertar-media-tune.conf`, built-in default (`src/util/MediaTune.hpp:8-15`). It brings its own INI parser
(318 lines), a CLI (`scripts/apertar-tune`, 487 lines), a template, a `tmpfiles.d` entry and a README section
(`README.md:337-341`). The owner asked for the file on 2026-11-02 (`working/drop-frames/media-tune-file.md`).

Upstream already has the mechanism for this need, written for the same reason ("sweeping one costs a service
restart per arm"): `tuningOverride(name)` reads the environment, then `/home/pi/.apertar-tuning` with the same
`APERTAR_*` names, at clip open (`src/prores/ProresEncoder.cpp:770-813@up`).

| Port | Upstream way |
| --- | --- |
| New key names (`dontneed`, `sync_ms`, ...) beside the env names | One name per knob: the env name |
| `dontneed` and `writeback` are read once per process, so a change needs a restart (`CdngEncoder.cpp:86`, `CC:4718`) | Re-read at clip open: no restart per arm |
| Per-medium sections | Not there. On the port the per-medium values already live in code: `writerSettingsFor()` (`src/util/MediaProfile.hpp:136-150`) |
| Three texts disagree on when the file is read: README "at start and when a take starts", `apertar-tune` "once, at start", `MediaTune.hpp:14` "when a value is needed" | - |
| `MediaTune.hpp:5` names `tools/media_tune_test.cpp`; the file is not in the repo | - |

Fix: move `tuningOverride()` to `src/util/TuningOverride.hpp` (namespace `apertar`), let `unsignedEnvValue` and
`boolEnvValue` (`CC:1341`, `CC:1357`) call it instead of `std::getenv`, read `APERTAR_DNG_DONTNEED` and
`APERTAR_DNG_WRITEBACK` per take. Delete `MediaTune.hpp`, `config/apertar-media-tune.conf`, `scripts/apertar-tune`, the
override file and the README section. Keep `writerSettingsFor()` as the per-medium table. A test night then writes:

```
# /home/pi/.apertar-tuning
APERTAR_MEDIA_SYNC_MS=2000
APERTAR_CDNG_UNCOMPRESSED_WORKERS=1
```

What is given up: per-medium sections in a file. If the owner wants them kept, the file is new architecture and
needs a page for the original developer; then drop at least the override layer and the CLI.

### X-knobs-7 (major, mismatch, deliberate): recording switches are written into the hardware file by commands

`set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge` and `set_storage_preroll` edit one key of
`apertar-hardware.conf` each (`App:12829-12925`, three near-identical 25-line blocks, each also writes
`<file>.bak`). `set_media_trim` and `set_preview_tdn`, added by the same port, store in `camera_settings.conf`
(`App:13194-13212`).

| Rule in original Apertar | Evidence |
| --- | --- |
| A `set_*` command for camera behaviour persists through `CaptureSettings` into `camera_settings.conf` | `set_timecode_mode` (`App:9424@up`) -> `timecode_mode=` (`CC:770@up`); recipe C1-R2 |
| One key of the hardware file belongs to the hardware class that parses its section; `App` does not edit a hardware key by itself | C1-S07 (`raw/conv-core-command-plane.md:56`) |
| The hardware file holds wiring. `[storage]` upstream: `mount_path`, `pcie_controller` | `App:4308-4310@up` |

Fix: five members in `CaptureSettings` beside `mediaTrimEnabled` (`bufferRam`, `framesPerFolder`, `clipMerge`,
`storagePreroll`, `storagePrerollSeconds`), saved in `writeCaptureSettings` after `media_trim=` (`CC:976`), carried
across formats like `mediaTrimEnabled` (`CC:11348-11367`), set through `CameraController` setters shaped like
`setMediaTrimEnabled`. The four commands become four lines each. `parseBufferConf` and `parsePrerollConf` (two more
hand-written INI parsers) and the `[media]` section go. The RAM budget numbers and the stop percent stay as bench
env vars (Table A, 4 and 6-8), not as file keys.

### X-knobs-8 (minor, knob, deliberate): env twins that silently beat a UI switch

`APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_STORAGE_PREROLL`,
`APERTAR_MEDIA_TRIM` each override a setting that has a command and a UI switch (section 10). To keep the UI from
lying, the port added four state fields (`frames_per_folder_env`, `clip_merge_env_off`, `storage_preroll_auto_env`,
`media_trim_env_off`) and page code for them. No upstream env var overrides a setting a UI shows.
Fix: remove the five env vars and the four state fields. A campaign script sends the socket command instead
(`set_clip_merge enabled=false`).

### X-knobs-9 (major, knob, deliberate): experiment leftovers among the env vars

| Group | Names | Why they can go |
| --- | --- | --- |
| Real-time scheduling | `APERTAR_RT`, `APERTAR_RT_PRIORITY`, `APERTAR_RT_CPUS`, `APERTAR_RT_CAPTURE_PRIORITY`, `LimitRTPRIO=80`, the start-script block | Measured: "no effect" (`lessons/hardware-log.md:954`); the entry closes with "Not ... the camera thread's CPU or its scheduling". The drop-in now permits real-time priority under a comment that says "non-real-time" |
| "Restore the old path" | `APERTAR_DNG_PAYLOAD_COPY`, `APERTAR_RAW_POOL_WARM` | Each keeps a dead code path alive. The new paths are the default and have a host test or a "near zero" verdict |
| "Restore the old limit" | `APERTAR_FPS_LIMIT=table`, `APERTAR_LOSSLESS_FPS_LIMIT`, `APERTAR_IMX585_MIN_MODE_WIDTH`, `APERTAR_IMX283_PROBE_FPS` | A switch back to upstream behaviour means the port is not sure of its default. Decide per limit (stock-behaviour sweep), then one path |
| Reverted experiment | `APERTAR_AUDIO_BUFFER_MS` | The default is the old 100 ms again. The hand-written `hw_params` block that came with it (`src/audio/TimestampedAudioCapture.cpp:199-218`) changed the period from 25 ms (`snd_pcm_set_params(..., 100000)`, `:190@up`) to 10 ms |
| Never set in any test the KB records | `APERTAR_WRITE_STALL_MS`, `APERTAR_DEAD_MEDIUM_STOP_MS`, `APERTAR_MEDIA_MIN_FREE_MB`, `APERTAR_PLAYBACK_WORKERS`, the four `APERTAR_PHASE_LOCK_*` gains; `APERTAR_RAW_COPY_WORKERS` (proposed once, "only if `drop[copy-slot]` ever appears (never has)") | Constants |

Fix: delete as listed in Table A (27 names). What stays is 15 bench knobs in upstream's form (C2-R5): env only, read
with `unsignedEnvValue` / `boolEnvValue`, value printed in the take-start line, **not in the README**. Move
`README.md:337-357` ("Write-path knobs for A/B tests") out of the README (X-knobs-15).

### X-knobs-10 (major, security, deliberate): the kernel-tune root helper never ran, and is loose

`scripts/apertar-media-tune`, `config/apertar-media.sudoers`, `/run/apertar-media/tune`, `kernel_tune`, `APERTAR_MEDIA_TUNE`.

| Fact | Evidence |
| --- | --- |
| Off by default; the helper was never installed on the rig, so the switch did nothing in every test | `App:11402-11408`; `working/drop-frames/nvme-campaign/research/R2-lever-inventory.md:206`; `working/drop-frames/nvme-campaign/plan.md:247` |
| The KB lists "Media-tune kernel knobs as a default" under Not recommended | `working/dng-chain-answer.md` 5.3 |
| The helper's own header: "T29 measures them on this rig before they are trusted" | `scripts/apertar-media-tune:11` |
| The sudoers rule pins the path, not the arguments. Upstream's rules list each argument | `config/apertar-media.sudoers:3`; `Apertar-UI/systemd/apertar-standby-usb.sudoers@up` |
| The root helper takes its state folder from the environment | `STATE_DIR="${APERTAR_MEDIA_RUN_DIR:-/run/apertar-media}/tune"`, `scripts/apertar-media-tune:30` |
| The state folder is root's, inside a folder pi owns, so pi can swap it. On `restore` root writes what it finds there into `/proc/sys/vm/*` and `/sys/block/<disk>/queue/*` | `config/apertar-media.tmpfiles.conf:3-5`; `scripts/apertar-media-tune:55-64`, `:99-107` (**probable**: read, not run) |

Fix: remove the chain. If kernel tuning is ever wanted, it is a `sysctl.d` file and a udev rule on the image, not a
helper Core calls.

### X-knobs-11 (minor, slop, deliberate): the eject flag has no reader

Core writes `/run/apertar-media/eject/<device>` before an unmount and removes it later (`src/util/MediaIntent.hpp:28-58`,
`App:4355`, `App:4389`, `App:10917`). "A flag file an automounter honours" (`MediaIntent.hpp:11`). No automounter in
the port reads it: `grep -rn 'apertar-media' Apertar-UI/src` gives nothing; `CfeAutomounter.cpp` knows only
`/run/apertar-cfe/ready`. The KB says so too: "Nothing in any local repo reads it ... Until the automounter half
exists this is bookkeeping" (`working/port-raw/critic.md` Y12).
Fix: either delete `MediaIntent.hpp`'s three flag functions, the `eject` line in the tmpfiles file and
`APERTAR_MEDIA_RUN_DIR`; or write the reader in `Apertar-UI/src/CfeAutomounter.cpp` (skip the mount on an insert
edge while the flag exists) and say in the handoff that Core and the automounter now share `/run/apertar-media`.

### X-knobs-12 (minor, slop, `conform_fps` deliberate): knobs that do nothing

| Knob | Evidence | Fix |
| --- | --- | --- |
| `conform_fps`: setting, `set_conform_fps`, three state lines, preset key `cameraConformFps`. No consumer, no UI | "Nothing derives from it yet" (`Types.hpp`, commit `d7ff071`); `grep -n conformFps CC`: clamp, load, save, copy, set only; 0 hits in `WCP` and in `Apertar-UI` | Remove until something uses it |
| `hold_ms`, `double_ms`: `set_controls` accepts and writes them; no reader | `HardwareConfigText.hpp:457`, `:466`, `:470`; `ButtonGesture.hpp:16-18` has the times as `constexpr`; reproduced: `checkEdits` returns "" for `set.gpio_buttons.hold_ms=1000` | Take both names out of `knownKey`, or read them into `ButtonGesture` |
| `MediaWriterSettings::directIo` | "for T24's direct I/O, which this fork does not carry; unused" (`MediaProfile.hpp:133`) | Remove the member and the fourth value of each table row |

### X-knobs-13 (minor, mismatch, deliberate): ISO caps as a `[camera]` section of the hardware file

`[camera] clear_hdr_iso_max_12bit=720`, `clear_hdr_iso_max_16bit=1585` with a parser of their own in
`CameraController.cpp` (`CC:2941-2981`), read once, no command, no UI. The numbers come from the driver's gain
codes (comment `CC:2934-2937`). Upstream keeps such limits in code (`CC:2483@up`, `CC:2629@up`).
Fix: two `constexpr uint32_t` beside `kLosslessMaxIso` (`CC:3100`), delete `loadCameraSection`, the section and its
template lines (`App:5074-5079`).

### X-knobs-14 (minor, duplication, deliberate): `mode_ladder.conf` beside `camera_settings.conf`

Three keys in a file of their own (`src/camera/ModeLadder.hpp:316-340`), path function copied from the settings
path (`CC:404-415` vs `CC:417-428`).
Fix: three keys in `camera_settings.conf` (`mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_resolutions`),
written once outside the per-format profiles; drop `modeLadderPath()`.

### X-knobs-15 (minor, slop, deliberate): the README documents bench knobs and points to a private knowledge base

`README.md:337-357` lists 15 env vars in 13 rows, with measurements, and four places name "the Apertar knowledge base"
(`:329`, `:341`, and the trim and tdn sections cite dated measurements). Upstream's README names no env var and no
measurement log. It also carries three `sudo install` recipes.
Fix: keep in the README what an operator sets (Boot Config card, trim, preview denoise, split clips). Move the
knob table to a developer page, without KB paths.

### X-knobs-16 (minor, mismatch, deliberate): three write routes for `config.txt`, new shell helpers in Core

`writeBootConfigText` tries a direct write, then `apertar-boot-config`, then `sudo -n install` (`App:3533-3611`).
Upstream has the last one only (`App:3157@up`). The trim goes through a second new helper. Upstream's helpers are
C++ in the UI repo with argument-pinned sudoers (section 3.3).
Fix: one route for `config.txt`: `sudo -n install` with the backup line the port already added (`App:3595`).
Trim: `timeout 20s sudo -n fstrim -v <mount>` from Core. If the original developer prefers helpers for a
locked-down image, both move to where his helpers are and get rules with the arguments written out.

### X-knobs-17 (minor, knob): driver default and Core default cancel each other on the IMX283

The driver enables an "experimental, UNMEASURED" per-crop VMAX floor by default (`crop_vmax = true`,
`imx283.c:277-281`). Core then caps the fps at the driver's `crop_vmax=0` floor table (`imx283::floorFps`,
`src/camera/Imx283Modes.hpp:138`, `CC:3333-3336`) unless `APERTAR_IMX283_PROBE_FPS=1` (`CC:3393`). Two knobs in two
repos, both at the position that undoes the other.
Fix: driver default `crop_vmax = false` (upstream driver behaviour), delete `floorFps` and the env var. Turn the
experiment on in the driver when it is measured.

### X-knobs-18 (nit, commit): eight UI commits add and drop three env knobs

`c13b846`, `a51c95e`, `4724007`, `322d329` add `APERTAR_PREVIEW_PLANE`, `APERTAR_PREVIEW_PEAKING` (two modes),
`APERTAR_PREVIEW_DIRECT`; `010f8ad`, `c153c33`, `b333343`, `1c7a3ad` drop them. Net diff: none. 8 of 39 UI commits.
Fix: leave them out of the merge series.

### X-knobs-19 (nit, mismatch): two boolean spellings in `camera_settings.conf`

Section 6, format note. Fix: write the port's booleans as upstream does (`<< s.member`), keep reading both.

## 12. Verdict list by knob count

| Verdict | Count | Which |
| --- | --- | --- |
| keep (operator setting, upstream place) | 18 `UI.conf` keys; 10 `camera_settings.conf` keys; the wiring keys (`[gpio_switches]`, gesture keys); `chip`, `poll_ms`; 2 driver overlay params | sections 5 to 7, 9 |
| fold | 1 env var (launch option); 5 storage keys and `[media]` into `camera_settings.conf`; `[camera]` into constants; `remoteN` into its own section; 3 config files; 2 helpers | X-knobs-5, 6, 7, 13, 14, 16 |
| remove | 27 env vars; 4 RAM-budget keys and the stop key (the env stays); `hold_ms`, `double_ms`; `conform_fps`; the eject flag; the kernel-tune chain; `apertar-tune`; `LimitRTPRIO`; the `APERTAR_RT` block | X-knobs-8 to 12 |
| developer-only (keep, not in the README) | 15 env vars; 3 driver module params | Table A; section 9 |
| revert a default | 4 `[display]` values; `preroll`; `preview_tdn` scope; `fps_speed_ramp_stretch_audio` | X-knobs-2, 3, 4; section 6 |

## 13. Unconfirmed

| Claim | What settles it |
| --- | --- |
| No unit on the Pi sets one of the 43 env vars in production | `systemctl cat apertar-core apertar-ui-direct; ls /etc/systemd/system/apertar-core.service.d /run/systemd/system/apertar-core.service.d`. The KB names one drop-in, `zz-ladder-buffers.conf` with `APERTAR_RAW_CAMERA_BUFFERS=8` |
| X-knobs-2: the built-in panel stays dark with the new fallback | On a stock Apertar: remove the `[display]` keys, `sudo systemctl restart apertar-ui-direct` |
| X-knobs-4: how much noisier ProRes and H.264 are without `tdn` | Two ProRes takes of a dark scene, `set_preview_tdn enabled=true` and `false` |
| X-knobs-10: the folder swap works as read | Not to be tried on a camera in use; the fix is removal |
| X-knobs-1: the chip field with a real second chip | An I2C expander with a kernel driver, `gpiodetect`, a button on it |

## Skeptic

Second pass, 2026-11-17. Each finding re-read on both sides (`@port` = Core `01f170c` / UI `7ea9afc`, `@up` = `upstream-1.6.0`).

| Id | Verdict | What changed |
| --- | --- | --- |
| X-knobs-1 | **half right, nit** | `knownKey` refuses the five shared keys in `[gpio_encoders]` (`HardwareConfigText.hpp:460-462@04fe197`), confirmed. But `knownKey` is only checked on edits (`HardwareConfigText.hpp:496`), so a stock file with `chip=auto` under `[gpio_encoders]` (upstream UI template, `DisplayConfigBridge.cpp:172@up`) still loads and saves. The template leftover is dropped: upstream Core's own template has no `chip=` in `[gpio]` either, only `gpiochip=auto` in trigger and tally (`App:4380`, `:4394@up`), same as the port (`App:5172`, `:5186@04fe197`). |
| X-knobs-2 | **confirmed, blocker; scope corrected** | Defaults confirmed (`DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357`; `.hpp:52-54`, `:59` vs `:14-15`, `:579`, `:584`, `:649@up`); UI no longer writes a file (`c9d841f`, 0 hits for `ensureDefaultHardwareConfigFile`); main window hidden (`src/main.cpp:432-433@port`, `:428-429@up`). Reach: cameras whose file has explicit `[display]` keys (every camera the upstream UI started, it wrote them) are unaffected. A fresh install, or a file without `[display]` keys, gets a hidden touch UI on a 720x720 panel. Core's template is only shown, not written, when no file exists (`App:6201`). |
| X-knobs-3 | **confirmed, major** | `value_or(true)` at `StoragePreroll.hpp:98`; triggers `App:10946-10958`; KB quotes found (`dng-chain-answer.md:175`, `:183`, `:186`; `drop-frames/README.md:341`). |
| X-knobs-4 | **confirmed, major** | No format test at `CC:7311`; ProRes derived tuning from `activePath` at `CC:7412`; one switch for all profiles (`CC:11348`). Caveat on the fix: the format test only works if a format change restarts the pipeline. `setRecordingFormat` ends in `applySettingsLocked(next, requiresReconfigure)` (`CC:11390`); that the reconfigure re-runs `start()` and so the tuning choice is **probable**, verify before relying on it. |
| X-knobs-5 | **confirmed, downgraded to minor** | Upstream `record_start` has no mount gate (`App:9090-9110@up`), confirmed. But upstream already treats an unmounted root as "no media" elsewhere: media library (`App:7676@up`), format (`App:8970@up`), Sound Recorder (`App:8351@up`). The gate follows upstream's model; what is wrong is the opt-out (an env var) and an undocumented 1024 MiB floor. A stock camera with its drive mounted sees no change. |
| X-knobs-6 | **confirmed, major; owner decision** | `MediaTune.hpp` 318 lines, `scripts/apertar-tune` 487 lines; `tools/media_tune_test.cpp` absent; `dontneed`/`writeback` read once (`CdngEncoder.cpp:86-96`, `CC:4718`). Upstream `tuningOverride` confirmed (`ProresEncoder.cpp:771-813@up`). The owner asked for the file, so removal is his call; the fix stands as the recommendation. |
| X-knobs-7 | **half right, downgraded to minor** | The rule "App does not edit a hardware key; the file holds wiring only" is too strong: upstream commands `set_imu_driver`, `set_imu_orientation`, `set_imu_sync_offset` write one key each into `apertar-hardware.conf` (`App:9646-9655@up` -> `Mpu6050RecordingSession.cpp:1295-1330@up`, `writeHardwareConfigValue`), and `sync_offset_ms` is an operator value. What survives: upstream writes through the class that owns the section; the port's `App` writes `[storage]`/`[media]` itself through its own store, in three copied blocks (`App:12829-12925`), while the same port stores `media_trim`/`preview_tdn` in `camera_settings.conf`. Two stores for one family of switches. |
| X-knobs-8 | **confirmed, minor** | Fields at `App:262`, `:266`, `:268`, `:9585`; 8 uses in `WCP`. |
| X-knobs-9 | **confirmed, major; one evidence fix** | `APERTAR_RT_CAPTURE_PRIORITY`: measured "no effect" (`lessons/hardware-log.md:954`). `APERTAR_RT` (whole process) was never measured; the KB judges it "wrong shape ... control arm only" (`working/dng-chain/F/F3.md:166`, `:195`), and the port's README says "not a recommendation" (`README.md:354`). `LimitRTPRIO=80` added under upstream's "non-real-time" comment, confirmed (`config/apertar-core-capture-priority.conf`). |
| X-knobs-10 | **facts confirmed, security weight overstated; minor** | `APERTAR_MEDIA_RUN_DIR` does not reach the helper: Core calls `sudo -n` (`App:11423`) and sudo's default `env_reset` drops it (**probable**, Debian default). The folder swap is real (`tmpfiles.conf:3-5`: `/run/apertar-media` is pi's, `tune` root's), and `save_once` writes `cat > $STATE_DIR/name` as root (`scripts/apertar-media-tune:50-53`), so pi could also aim a symlink. But pi already runs `sudo -n install`, `mount`, `systemctl` with no listed rule on upstream (`App:3157@up`, `App:3623@up`), so no privilege is gained. The verdict (remove: off by default, never installed, not recommended) stands on its own. |
| X-knobs-11 | **confirmed, minor** | No hit for `apertar-media` in `Apertar-UI/src`, `systemd`, `scripts`. |
| X-knobs-12 | **confirmed, minor** | `conformFps`: clamp, load, save, copy, set, state, preset only; 0 hits in `WCP` and the UI. `hold_ms`/`double_ms` accepted (`HardwareConfigText.hpp:457`, `:466`, `:470`), times are `constexpr` (`ButtonGesture.hpp:16-18`), no other reader. `directIo` unused (`MediaProfile.hpp:133`). |
| X-knobs-13 | **confirmed, minor** | `loadCameraSection` `CC:2943-2981`; upstream literal cap `CC:2483@up`. |
| X-knobs-14 | **downgraded to nit; fix changed** | Upstream `camera_settings.conf` has no block outside the active settings and `profile.*` (`persistCaptureSettingsNow`, `CC:780-791@up`), and its writer is a snapshot persister on its own thread. Folding the ladder in adds a new kind of block and couples two locks. A separate file per concern has upstream precedent (`apertar-color-profiles.conf`, the ProRes cache). What survives: `modeLadderPath()` (`CC:404-415`) copies `persistedSettingsPath()` (`CC:417-428`). |
| X-knobs-15 | **confirmed, minor; one addition** | 0 `APERTAR_` in upstream README; the port has the table and the KB paths (`README.md:329`, `:341`). Also `README.md:333` names a private UI commit and local branch ("Apertar-UI `7ea9afc` (local branch `clip-split`)"). |
| X-knobs-16 | **confirmed, minor** | Three routes `App:3533-3611`; upstream `App:3150-3160@up`. |
| X-knobs-17 | **confirmed, minor** | `crop_vmax = true` (`imx283.c:277`); not in the driver baseline (`git show origin/master:imx283.c`, 0 hits); Core caps at `floorFps` (`CC:3333-3336`) unless `APERTAR_IMX283_PROBE_FPS=1` (`CC:3390-3395`). |
| X-knobs-18 | **confirmed, nit** | All 8 in `origin/main..cinemate-port`; 0 hits for the three names at `cinemate-port`. |
| X-knobs-19 | **confirmed, nit** | `CC:974-979` `true`/`false`; upstream `<< s.member` (`CC:749@up`); `clear_hdr` started it on fork main. |

Nothing serious found beyond the list.

## Final findings

Every surviving finding, corrected. Refs as in the header table.

### X-knobs-2 (blocker, stock-behaviour-change, deliberate): the display fallback is the contributor's HDMI rig
- Where: `Apertar-UI/src/DisplayConfigBridge.cpp:11-12`, `:289`, `:294`, `:357`; `Apertar-UI/src/DisplayConfigBridge.hpp:52-54`, `:59`; `Apertar-Core/src/ApertarCoreApp.cpp:5089-5098`.
- Detail: the UI fallback is 1920x1080, `landscape_large`, `hdmi_external_only=true` (upstream 720x720, `square`, `false`: `DisplayConfigBridge.cpp:14-15`, `:579`, `:584`, `:649@up`). The UI no longer writes a default file (`c9d841f`); upstream did (`ensureDefaultHardwareConfigFile`, `:41`, `:587@up`). With `hdmi_external_only` the main window is hidden (`src/main.cpp:432-433@port`). Reach: a fresh install, or any `apertar-hardware.conf` without `[display]` keys, shows no touch UI on the stock 720x720 panel. Cameras whose file the upstream UI wrote keep their explicit keys and are unaffected. Commits Core `7af9f13`, UI `7c41a27`.
- Fix: put 720, 720, `square`, `false` back in the UI constants, `loadConfiguration`, the header members and Core's template. The HDMI rig keeps `ui_width=1920`, `ui_height=1080`, `ui_layout=landscape_large`, `hdmi_external_only=true` in its own `[display]`. Restoring the first-run file write (`c9d841f`) is a separate call for the UI file reviewer.
- Effort: S.

### X-knobs-3 (major, stock-behaviour-change, deliberate): the storage pre-roll runs by itself
- Where: `src/util/StoragePreroll.hpp:98`; `src/ApertarCoreApp.cpp:5069-5072`, `:10946-10958`, `:11148-11160`.
- Detail: `conf.automatic.value_or(true)`: Core records a 2 s take at the sensor's maximum fps and deletes it at every Core start, card insert and format. Upstream has no pre-roll. The KB: "no measurement exists" and "the honest default is off for the automatic triggers" (`working/dng-chain-answer.md:175`, `:186`); the port's own plan: "a setting (`storage_preroll`, default off at first), never a hidden step" (`working/drop-frames/README.md:341`).
- Fix: `value_or(false)`, template comment `# preroll=off`, one README line. The manual `storage_preroll` command stays.
- Effort: S.

### X-knobs-4 (major, stock-behaviour-change, default deliberate): `preview_tdn=false` also strips temporal denoise from H.264 and ProRes recordings
- Where: `include/apertar/core/Types.hpp:139`; `src/camera/CameraController.cpp:7309-7318`, `:7412`; `README.md:317`.
- Detail: the strip in `loadablePath` has no format test; ProRes colour tuning is derived from the stripped file (`makeProresIspTuning(activePath, ...)`). For H.264 and ProRes the ISP picture is the recording, so a stock camera records them without temporal denoise after the merge, also with a tuning file the user picked. The README speaks of DNGs only.
- Fix: `if (!settings.previewTdn && !isProcessedVideoFormat(settings.recordingFormat) && !settings.photoModeEnabled)` (helper at `CC:280`; upstream has it). Verify that a format change re-runs `start()` (`setRecordingFormat` -> `applySettingsLocked(next, requiresReconfigure)`, `CC:11390`; **probable**). Or `bool previewTdn = true;` (upstream behaviour everywhere).
- Effort: S.

### X-knobs-6 (major, duplication, deliberate): a second bench-tuning mechanism beside upstream's `.apertar-tuning`
- Where: `src/util/MediaTune.hpp` (318 lines); `scripts/apertar-tune` (487 lines); `config/apertar-media-tune.conf`; `config/apertar-media.tmpfiles.conf`; `README.md:337-341`; `src/cdng/CdngEncoder.cpp:86-96`; `CC:4718`.
- Detail: four layers per write-path knob (env, `/run/apertar-media/media-tune.override.conf`, `~/apertar-media-tune.conf`, default), new key names beside the env names, per-medium sections. Upstream's `tuningOverride(name)` already reads env then `/home/pi/.apertar-tuning` with the same `APERTAR_*` names, re-read at clip open, for the same reason (`src/prores/ProresEncoder.cpp:771-813@up`). Port `dontneed`/`writeback` are read once per process, so they still need a restart. Three texts disagree on when the file is read. `MediaTune.hpp:5` names `tools/media_tune_test.cpp`, which does not exist. The owner asked for the file (2026-11-02), so this is his decision.
- Fix: move `tuningOverride()` to `src/util/TuningOverride.hpp`, let `unsignedEnvValue`/`boolEnvValue` (`CC:1341`, `:1357`) call it, read `APERTAR_DNG_DONTNEED`/`APERTAR_DNG_WRITEBACK` per take; delete `MediaTune.hpp`, the template, `apertar-tune`, the override file and the README section; keep `writerSettingsFor()` (`MediaProfile.hpp:136-150`) as the per-medium table. If the owner keeps the file: drop the override layer and the CLI, and document it for the original developer.
- Effort: M.

### X-knobs-9 (major, knob, deliberate): experiment leftovers among the env vars
- Where: `scripts/start-apertar-core.sh:20-41`; `config/apertar-core-capture-priority.conf`; `CC:9113`, `CC:4897`, `CC:3120`, `CC:3393`, `CC:3401`, `CC:4386`, `CC:4469`, `CC:4861`, `CC:8918-8921`; `src/cdng/CdngEncoder.cpp:137`; `src/camera/Imx585Modes.hpp:107`; `src/playback/PlaybackFrames.cpp:82`; `src/audio/AudioRecordingSession.cpp:215`; `App:11379`.
- Detail: 27 env vars the port adds are restore switches, reverted experiments or never-set constants (Table A). `APERTAR_RT_CAPTURE_PRIORITY` measured "no effect" (`lessons/hardware-log.md:954`); `APERTAR_RT` never measured and judged "wrong shape, control arm only" (`working/dng-chain/F/F3.md:166`). `LimitRTPRIO=80` now sits under upstream's comment "Permit only a bounded, non-real-time boost". Upstream bench knobs are env-only, read with `unsignedEnvValue`/`boolEnvValue`, not in the README.
- Fix: delete the 27 names per Table A, the `APERTAR_RT` block and `LimitRTPRIO`; turn the never-set ones into constants; keep 15 developer-only knobs in upstream's form.
- Effort: M.

### X-knobs-5 (minor, stock-behaviour-change, deliberate): the record gate's opt-out is an undocumented env var
- Where: `src/ApertarCoreApp.cpp:11331-11337`, `:11359-11384`, `:12596-12600`.
- Detail: `record_start`, `capture_photo`, `timelapse_start` are refused when the media root is not a mount point or has under 1024 MiB free. Upstream has no such gate on recording (`App:9090-9110@up`), but already treats an unmounted root as no media for the library, format and Sound Recorder (`App:7676`, `:8970`, `:8351@up`), so the gate fits upstream's model. A stock camera with its drive mounted sees no change. The way out (`APERTAR_MEDIA_REQUIRE_MOUNT=0`, `APERTAR_MEDIA_MIN_FREE_MB`) is in no document.
- Fix: launch option `--allow-unmounted-media` beside `--media` (`src/main.cpp`, `ApertarCoreApp::Options`, README "Launch Options"); `mediaGateBypassed()` returns `options_.simulateCamera || options_.allowUnmountedMedia`; `constexpr uint64_t kMinFreeMiB = 1024;`; drop both env vars.
- Effort: S.

### X-knobs-7 (minor, mismatch, deliberate): storage switches in two stores, edited by `App` itself
- Where: `src/ApertarCoreApp.cpp:12829-12925`; `src/util/BufferBudget.hpp:150-195`; `src/util/StoragePreroll.hpp:46-88`; `App:13194-13212`.
- Detail: `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll` write `[storage]`/`[media]` keys of `apertar-hardware.conf` from `App`, in three copied 25-line blocks, each with a `.bak`. `set_media_trim` and `set_preview_tdn` of the same port store in `camera_settings.conf`. Upstream does write single hardware keys from commands (`set_imu_sync_offset` etc., `Mpu6050RecordingSession.cpp:1295-1330@up`), but through the class that owns the section; no class owns `[storage]`/`[media]` here, and recording behaviour sits in two stores.
- Fix: preferred, five `CaptureSettings` members beside `mediaTrimEnabled` (`bufferRam`, `framesPerFolder`, `clipMerge`, `storagePreroll`, `storagePrerollSeconds`), saved after `media_trim=` (`CC:976`), carried across formats like `mediaTrimEnabled` (`CC:11348-11367`), set through setters shaped like `setMediaTrimEnabled`; `parseBufferConf`, `parsePrerollConf` and `[media]` go. The RAM numbers and stop percent stay as env bench knobs.
- Effort: M.

### X-knobs-8 (minor, knob, deliberate): env twins that silently beat a UI switch
- Where: `App:262`, `:266`, `:268`, `:276`, `:6402`, `:9585`; `CC:5503`; 8 uses in `WCP`.
- Detail: `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_STORAGE_PREROLL`, `APERTAR_MEDIA_TRIM` override settings that have a command and a UI switch; four state fields exist only to explain the override. No upstream env var overrides a setting a UI shows.
- Fix: remove the five env vars and the four fields; a campaign script sends the socket command instead.
- Effort: S.

### X-knobs-10 (minor, security, deliberate): the kernel-tune root helper chain never ran
- Where: `scripts/apertar-media-tune`; `config/apertar-media.sudoers`; `config/apertar-media.tmpfiles.conf:3-5`; `App:11396-11430`.
- Detail: off by default, never installed on the rig, "not recommended" (`working/dng-chain-answer.md` 5.3). The sudoers rule pins the path, not the arguments (upstream lists each, `Apertar-UI/systemd/*.sudoers@up`). The root-owned state folder sits in a pi-owned folder, and `save_once` writes `cat > $STATE_DIR/name` as root, so pi could swap the folder or plant a symlink. No privilege gain in practice: pi already has unrestricted `sudo -n` (upstream relies on it, `App:3157@up`), and `APERTAR_MEDIA_RUN_DIR` is dropped by sudo's `env_reset` (**probable**).
- Fix: remove the helper, its sudoers file, the `tune` line of the tmpfiles file, `kernel_tune`, `APERTAR_MEDIA_TUNE` and `applyMediaTuning`. Kernel tuning, if ever wanted, is a `sysctl.d` file and a udev rule on the image.
- Effort: S.

### X-knobs-11 (minor, slop, deliberate): the eject flag has no reader
- Where: `src/util/MediaIntent.hpp:10-58`; `App:4355`, `:4389`, `:10917`; `config/apertar-media.tmpfiles.conf`.
- Detail: Core writes `/run/apertar-media/eject/<device>` for "an automounter that honours" it; no file in `Apertar-UI` (src, systemd, scripts) or Core reads it.
- Fix: delete the flag functions, the `eject` tmpfiles line and `APERTAR_MEDIA_RUN_DIR`; or write the reader in `Apertar-UI/src/CfeAutomounter.cpp` and document the shared folder.
- Effort: S.

### X-knobs-12 (minor, slop): knobs that do nothing
- Where: `include/apertar/core/Types.hpp:137`; `CC:696-697`, `:818`, `:942`, `:11812`; `App:7851`, `:14356`; `src/hardware/HardwareConfigText.hpp:457`, `:466`, `:470`; `src/hardware/ButtonGesture.hpp:16-18`; `src/util/MediaProfile.hpp:133`.
- Detail: `conform_fps` (setting, `set_conform_fps`, state, preset key) has no consumer and no UI. `hold_ms`/`double_ms` are accepted and written by `set_controls`, but the times are `constexpr`. `MediaWriterSettings::directIo` is "unused".
- Fix: remove `conform_fps` and `cameraConformFps`; take `hold_ms`/`double_ms` out of `knownKey` (or read them into `ButtonGesture`); remove `directIo` and the fourth value of each table row.
- Effort: S.

### X-knobs-13 (minor, mismatch, deliberate): Clear HDR ISO caps as a `[camera]` section of the hardware file
- Where: `CC:2933-2981`; `App:5074-5079`.
- Detail: own parser, read once, no command, no UI; values derived from driver gain codes. Upstream keeps such limits in code (`CC:2483@up`).
- Fix: two `constexpr uint32_t` beside `kLosslessMaxIso` (`CC:3100`); delete `loadCameraSection`, the section and its template lines.
- Effort: S.

### X-knobs-15 (minor, slop, deliberate): the README documents bench knobs, install recipes and private references
- Where: `README.md:202-203`, `:303-310`, `:329`, `:333`, `:337-357`.
- Detail: 15 env vars in 13 rows with measurements, KB paths, three `sudo install` recipes, and a private UI commit and local branch name (`:333`). Upstream README names no env var, no measurement log, no sudoers install.
- Fix: keep what an operator sets (Boot Config card, trim, preview denoise, split clips) without KB paths or commit refs; move the knob table to a developer page; install steps to the image notes.
- Effort: S.

### X-knobs-16 (minor, mismatch, deliberate): three write routes for `config.txt`, new shell helpers in Core
- Where: `App:3530-3611`; `App:11478-11500`; `scripts/apertar-boot-config`, `scripts/apertar-media-trim`, their sudoers files.
- Detail: direct write, then helper, then `sudo -n install`; upstream has the last only (`App:3150-3160@up`). Upstream's root helpers are C++ in the UI repo with argument-pinned sudoers.
- Fix: one route, `sudo -n install` with the backup line (`App:3595`); trim as `timeout 20s sudo -n fstrim -v <mount>`. If a locked-down image is wanted, both helpers move beside the UI's with arguments written into the rules.
- Effort: S.

### X-knobs-17 (minor, knob): IMX283 driver default and Core default cancel each other
- Where: `imx283-v4l2-driver/imx283.c:269-281`; `src/camera/Imx283Modes.hpp:138`; `CC:3333-3336`, `:3390-3395`.
- Detail: the driver enables an "experimental, UNMEASURED" per-crop VMAX floor by default (`crop_vmax = true`, absent in the driver baseline `origin/master`); Core caps fps at the `crop_vmax=0` floor table unless `APERTAR_IMX283_PROBE_FPS=1`.
- Fix: driver default `crop_vmax = false`; delete `floorFps` use and the env var; enable the experiment in the driver once measured.
- Effort: S.

### X-knobs-1 (nit, knob, deliberate): `set_controls` refuses the GPIO keys `[gpio_encoders]` shares
- Where: `src/hardware/HardwareConfigText.hpp:460-462@04fe197`; `src/hardware/GpioInput.cpp:336-355`.
- Detail: the chip setting is back on the Controls card (`04fe197`). `set_controls` still refuses `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` in `[gpio_encoders]`, which the reader reads there (one shared value, later line wins) and the upstream UI template wrote there (`DisplayConfigBridge.cpp:172-176@up`). Only edits are checked (`HardwareConfigText.hpp:496`), so existing files load and save. Not run on a Pi with a second chip.
- Fix: add the five names to the `gpio_encoders` branch of `knownKey`, or keep refusing with the message "Set chip, pull, active_low, poll_ms and debounce_ms in [gpio_buttons]: the encoders share them."
- Effort: S.

### X-knobs-14 (nit, duplication, deliberate): `modeLadderPath()` copies `persistedSettingsPath()`
- Where: `CC:404-415`, `CC:417-428`.
- Detail: the separate `mode_ladder.conf` is acceptable (upstream keeps one file per concern; its `camera_settings.conf` holds only the active block and `profile.*`, written by a snapshot persister, `CC:780-791@up`). The two path functions are the same code with a different file name.
- Fix: one helper for the `apertar-core` config folder (XDG, `HOME`, temp fallback) used by both.
- Effort: S.

### X-knobs-18 (nit, commit): eight UI commits add and drop three env knobs
- Where: UI `c13b846`, `a51c95e`, `4724007`, `322d329`, `010f8ad`, `c153c33`, `b333343`, `1c7a3ad`.
- Detail: `APERTAR_PREVIEW_PLANE`, `APERTAR_PREVIEW_PEAKING`, `APERTAR_PREVIEW_DIRECT` added and dropped; net diff none; 8 of 39 UI commits.
- Fix: leave them out of the merge series.
- Effort: S.

### X-knobs-19 (nit, mismatch): two boolean spellings in `camera_settings.conf`
- Where: `CC:974-979`.
- Detail: six port booleans as `true`/`false`, upstream writes `<< s.member` (`0`/`1`, `CC:749@up`); `clear_hdr` started it on fork main. The reader takes both.
- Fix: write `<< s.member`; keep reading both.
- Effort: S.
