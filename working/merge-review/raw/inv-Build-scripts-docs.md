# Inventory: Build-scripts-docs (stage 1, no judgement)

Refs: port = `cinemate-port` 01f170c, base = `origin/main` f60e301, upstream = `upstream-1.6.0`.
Scope diff: 15 files, +480/-3 (README +90, Types.hpp +95, ApertarCoreApp.hpp +153, 6 new config files, start script +24, CMake +8/-2, ControlServer +4/-1, WebServer +3).
`.gitignore` and `src/main.cpp`: no diff. Outside the diff but referenced by it: `scripts/apertar-boot-config`, `scripts/apertar-media-trim`, `scripts/apertar-media-tune`, `scripts/apertar-tune` (all new), `third_party/liblj92/lj92.{c,h}`.

## 1. File-by-file

| File | Change | Commits |
| --- | --- | --- |
| CMakeLists.txt | `LANGUAGES C CXX`; adds `src/playback/PlaybackFrames.cpp`, `third_party/liblj92/lj92.c`, `src/hardware/{HardwareConfigStore,GpioChipInfo,I2cProbe}.cpp`; `third_party/liblj92` in `APERTARCORE_PRIVATE_INCLUDE_DIRS`. No test target, no `enable_testing`. | 1af26c8, 3526e4b, 166cc4d, 0a98868 |
| scripts/start-apertar-core.sh | `APERTAR_RT=1` block: builds `PREFIX` array `chrt -f $APERTAR_RT_PRIORITY(70)`, `ionice -c2 -n0`, `taskset -c $APERTAR_RT_CPUS(1-3; empty = no pin)`; probes `chrt -f N /bin/true`, falls back to normal start with a stderr line; `exec ${PREFIX[@]+...} $CORE_BIN`. Comment names Cinemate `src/module/cinepi_multi.py run()` and "the A/B in the kb decides whether it stays". | c57c284 |
| config/apertar-core-capture-priority.conf | upstream file (`LimitNICE=-5`) gains `LimitRTPRIO=80` plus 3 comment lines. | c57c284 (+6ef0ddc) |
| config/apertar-boot-config.sudoers | new; `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-boot-config ""` | dda1713 |
| config/apertar-media-trim.sudoers | new; `pi ... NOPASSWD: /usr/local/libexec/apertar-media-trim` (any args; helper validates) | d44b177 |
| config/apertar-media.sudoers | new; `pi ... NOPASSWD: /usr/local/libexec/apertar-media-tune` (any args) | 26da30e |
| config/apertar-media.tmpfiles.conf | new; `d /run/apertar-media 0755 pi pi`, `.../eject 0755 pi pi`, `.../tune 0755 root root` | 26da30e |
| config/apertar-media-tune.conf | new, 54 lines; INI template for write-path knobs; sections `[default] [exfat] [ext4]`; keys dontneed, writeback, sync_ms, raw_buffers, kernel_tune, workers, queue, extra_raw_buffers. Defaults shipped: dontneed=sync, writeback=on, sync_ms=1000, raw_buffers=8, kernel_tune=off, exfat/ext4 workers=4 queue=12 extra_raw_buffers=0. | 2edc6d0 |
| scripts/apertar-boot-config | new root helper (sh, 71 lines): config.txt from stdin to `/boot/firmware/config.txt`; max 64 KiB, no NUL, needs `[pi5]`/`[pi4]`/`[all]` header; backup `config.txt.apertar.bak`; tmp + sync + rename; exit 0/1/2/3. | dda1713 |
| scripts/apertar-media-trim | new root helper (sh, 90 lines): `fstrim` of one mount under `/media/`; exit 0/1/2/3/4; 20 s limit; whole-disk name logic for nvme/sd/mmcblk. | d44b177 |
| scripts/apertar-media-tune | new root helper (sh, 112 lines): `apply|restore <rootdisk> <class> <fs>`; writes vm.dirty_bytes, dirty_background, block scheduler, nr_requests, rq_affinity, nvme_core `default_ps_max_latency_us`; originals saved in `/run/apertar-media/tune/`. Table per class (pi-nvme, usb-uas, usb-storage, sd-card, other) "taken from Cinemate's storage-automount table; T29 measures them before they are trusted". | 26da30e |
| scripts/apertar-tune | new CLI (python3, 487 lines): show/set/unset/clear/init for `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf`; "does no resolution of its own: Core is the source of truth". | 46d0e8c |
| src/ipc/ControlServer.cpp | `kMaxRequestLineBytes = 1024*1024`; request line limit 64 KiB -> 1 MiB (client dropped silently above it). | 5395fa4 |
| src/web/WebServer.cpp | `reasonPhrase`: 206, 409, 416 added. | f91fafa (409), 1af26c8 (206, 416) |
| include/apertar/core/Types.hpp | +`<vector>`; `enum class CdngLog {Off, Auto}`; `toString`, `cdngLogFromString` (accepts off/auto/on/12/10/8), `cdngLogStoredBits`, `cdngLogAvailable`, `cdngLogBits`; 25 new `CaptureSettings` members (list in 3). | 80ddac1, faa2958, 8175273, 646a194, d7ff071, ca7b7c2, 6d217c7, 0041ba0, e16033e, 62c1711, d44b177, 014a2bf, ce0bd90, e625c68 |
| src/ApertarCoreApp.hpp | +includes `util/MediaProfile.hpp`, `util/StoragePreroll.hpp`, `<map>`, `<sys/types.h>`; fwd decl `hwconf::Document`; ~30 new private methods and ~60 members (list in 4). | 438a342, 26da30e, f91fafa, a37a902, f5a61b8, 4d80a35, 166cc4d, 0a98868, dcf09ee, d44b177, ce0bd90, ba0658d |
| third_party/liblj92/{LICENSE, README.apertar.md, lj92.c (1275), lj92.h (112)} | new vendored lossless-JPEG decoder from cgohlke/imagecodecs `07b0383...`, MIT; one local fix (zero difference category shift by -1 in `nextdiff`). README says "used to decode lossless JPEG tiles in the UI and independently verify the Apertar encoder; recording uses Apertar's tile encoder". fork-log: "the touch UI's file, byte-identical" (UI has `third_party/liblj92` too, upstream UI has one). | 1af26c8 |
| README.md | +90 lines, 5 new subsections under "Hardware Controls" (after `run_script`): Boot Config, Trim the recording drive, Preview temporal denoise, Split clips, Write-path knobs (14-row env table). Upstream README has no env-var table and no root-helper install text. | 496817f, 3b87d99, d44b177, e625c68, d7dd337, 9ec37b5, ba0658d, 2edc6d0, c57c284, 6ef0ddc, 0ed07ea, adac040, fb557e9, 766aba8 |
| tools/ (20 files) | see 6. | many |

## 2. Operator-visible features touching this unit

| Feature | What the operator gets | Files in scope |
| --- | --- | --- |
| Boot Config card (System pane) | edit sensor per connector, link frequency, RP1 overclock, I2C/I2S/SPI/audio, display (HDMI/Waveshare/Hyperpixel), "Edit file" text mode, dry-run diff, read-back refusal, `.bak`; root helper | README, apertar-boot-config(.sudoers) |
| Drive trim | Core trims recording drive after delete (>= 1 GiB), after pre-roll clip delete, at mount; `APERTAR_MEDIA_TRIM=0` off; WebUI Performance switch | README, apertar-media-trim(.sudoers), App.hpp, Types.hpp `mediaTrimEnabled` |
| Media tuning file | per-medium write-path knobs in `~/apertar-media-tune.conf` + RAM override, edited with `apertar-tune`; journal line "ApertarCore media tune:" | config/apertar-media-tune.conf, apertar-tune, README table |
| Kernel tune of drive | dirty pages, scheduler, queue via root helper (`kernel_tune`, `APERTAR_MEDIA_TUNE=1`), off by default | apertar-media-tune, apertar-media.sudoers, tmpfiles |
| RT scheduling A/B | `APERTAR_RT=1` whole process SCHED_FIFO 70 on cores 1-3; `APERTAR_RT_CAPTURE_PRIORITY=N` completion thread only | start script, capture-priority.conf, README |
| Preview TDN switch | "Preview temporal denoise" off by default; tuning copy in `~/.cache/apertar-core/tuning/<name>_notdn.json`; `preview_tdn` | README, Types.hpp `previewTdn` |
| Split clips + merge worker | `[storage] frames_per_folder`, `part_NNN/`, `.parts`, auto flatten while idle, `flatten_clip.py` | README, App.hpp, tools |
| CineMate Log | `cdng_log` off/auto, stored depth one step down | Types.hpp |
| Speed ramp, conform fps, fps phase lock, mode ladder, Clear HDR ISO/WB hold, clip name template, stretched WAV | settings/state fields | Types.hpp |
| Controls card backend | hardware file store, GPIO/I2C peripherals, Listen, apply without restart | CMake sources, App.hpp |
| Frame-by-number playback + downloads yield | `/api/media/frame`, 409 hold, 206/416 | CMake, WebServer.cpp, liblj92 |
| Media fault handling, storage pre-roll, buffer events/safety stop | watcher thread, pre-roll thread, 90 % stop | App.hpp |
| 1 MiB socket line | `set_controls`/config text fits | ControlServer.cpp |
| Web preview cap while recording | `APERTAR_WEB_PREVIEW_RECORDING_FPS` | README only (code outside scope) |

## 3. Socket commands, routes, state fields, events, config keys, env vars, files, UI

### Socket commands and HTTP routes (named in this scope)

| Item | Kind | Source |
| --- | --- | --- |
| `get_boot_config`, `set_boot_config` (cam0_sensor, cam1_sensor, cam0_link_frequency, cam1_link_frequency, i2c, i2s, spi, audio, rp1, display, dry_run, revision, confirm_display, text) | socket | README |
| `set_preview_tdn enabled=` | socket | README |
| `set_frames_per_folder value=N`, `set_clip_merge enabled=` | socket | README |
| `get_controls`, `set_controls`, `scan_i2c`, `test_output`, `set_media_trim`, `set_buffer_mode` | socket | fork-log rows f5a61b8, dcf09ee, ce0bd90, d44b177 (code outside scope) |
| `GET /api/media/frame`, `/api/media/clip`, `/api/buffer`, `/api/config` (409/400) | HTTP | fork-log; WebServer.cpp only adds status phrases |

### State fields (in scope)

Named in README: `preview_tdn`, `clip_merge_enabled`, `clip_merge_pending`, `clip_merge_active`, `clip_merge_last`.
From Types.hpp comments: `iso_actual`/`isoMeasured`, `isoMax`, `fpsMax`, `fpsTakeMax`, ladder fields (`ladderActive`, `ladderRung`, `ladderRampReady`, `ladderEnabled`, `ladderOverride`, `ladderCount`, `ladderTops`, `ladderText`), `cdngLogApplied`, `clipNameExample`, `playback_hold`, `media_alive`, `controls_errors`, `controls_warnings`.

### CaptureSettings members added (Types.hpp), persisted vs runtime

| Member | Persisted | Note |
| --- | --- | --- |
| `conformFps` 25.0 | yes | "nothing derives from it yet" |
| `fpsPhaseLock` | yes | FramePhaseLock |
| `previewTdn` false | yes (`preview_tdn=`) | |
| `mediaTrimEnabled` true | yes | env `APERTAR_MEDIA_TRIM=0` overrides |
| `fpsSpeedRamp`, `fpsSpeedRampKeepExposure`, `fpsSpeedRampStretchAudio` (true), `fpsSpeedRampReturn` | yes | "T31" in comment |
| `clipNameTemplate` `{format}_{date}_{clip}` | yes | |
| `isoAutoAfterClearHdr`, `whiteBalanceAutoAfterClearHdr` | yes | |
| `cdngLog` (Off/Auto) | yes | legacy "12/10/8/on" parse to Auto |
| `fpsRamp` | transient | |
| `clipNameExample`, `isoMeasured`, `cdngLogApplied`, `isoMax`, `fpsMax`, `fpsTakeMax`, ladder* | runtime, not persisted | |

### Config keys

| Key | File | Source |
| --- | --- | --- |
| `[storage] frames_per_folder` (0, 100..100000), `[storage] clip_merge` (on) | apertar-hardware.conf | README |
| `[storage]` buffer keys (frames/ram queue) | apertar-hardware.conf | tools/storage_buffer_conf_test.cpp |
| `[media]` pre-roll keys | apertar-hardware.conf | tools/storage_preroll_test.cpp |
| `preview_tdn=` | camera_settings.conf | README |
| `dontneed, writeback, sync_ms, raw_buffers, kernel_tune, workers, queue, extra_raw_buffers` | apertar-media-tune.conf (new file, 3rd config file family) | config/apertar-media-tune.conf |

### Env vars (all new, none exist upstream scripts/README)

`APERTAR_RT`, `APERTAR_RT_PRIORITY`, `APERTAR_RT_CPUS`, `APERTAR_RT_CAPTURE_PRIORITY`, `APERTAR_DNG_PAYLOAD_COPY`, `APERTAR_DNG_WRITE_ROWS`, `APERTAR_RAW_POOL_WARM`, `APERTAR_DNG_DONTNEED`, `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_CAMERA_BUFFERS`, `APERTAR_WEB_PREVIEW_RECORDING_FPS`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_MEDIA_TUNE`, `APERTAR_MEDIA_TRIM`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_FPS_LIMIT=table` (fork-log), `APERTAR_PLAYBACK_WORKERS` (fork-log), `APERTAR_MEDIA_RUN_DIR` (apertar-tune/media-tune scripts). Upstream start script reads only `APERTAR_TUNING_FILE`, socket and media root.

### Files on disk

| Path | Owner | Purpose |
| --- | --- | --- |
| `/usr/local/libexec/apertar-boot-config`, `-media-trim`, `-media-tune` | root | 3 new helpers; upstream already uses `/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power` (ApertarCoreApp.cpp:1544,1549 @upstream) |
| `/etc/sudoers.d/apertar-boot-config`, `apertar-media-trim`, `apertar-media` | root | 3 new sudoers files |
| `/etc/tmpfiles.d/apertar-media.conf` | root | creates `/run/apertar-media/{eject,tune}` |
| `/run/apertar-media/media-tune.override.conf`, `/run/apertar-media/eject/`, `/run/apertar-media/tune/` | pi / root | RAM state |
| `~/apertar-media-tune.conf` | pi | base tuning |
| `/boot/firmware/config.txt.apertar.bak` | root | backup |
| `~/.cache/apertar-core/tuning/<name>_notdn.json` | pi | tdn-stripped tuning copy |
| `<clip>/part_NNN/`, `<clip>/.parts`, `<clip>_stretched.wav`, `fps-ramp.txt` | pi | take layout |
| `/etc/systemd/system/apertar-core.service.d/` capture-priority drop-in | root | exists upstream, now with `LimitRTPRIO=80` |

### UI elements named

WebUI System pane: Boot Config card (Save & Reboot, Edit file, Use This Text, display confirm); Settings > System > Performance card: "Preview temporal denoise", "Frames per folder", trim switch, clip-merge switch; red buffer bar; Controls card GPIO/Tally; touch UI clip browser reads split clips (UI 7ea9afc).

## 4. Original code modified

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| CMake project languages | CMakeLists.txt:6 | CXX -> C CXX | extended-in-place |
| Core source list / include dirs | CMakeLists.txt:74-107 | 6 sources + 1 include dir added in the middle of lists | extended-in-place |
| `apertar-core-capture-priority.conf` | whole file | `LimitRTPRIO=80` added; comment "non-real-time boost" now sits beside RT limit | extended-in-place (changes the file's stated policy "only bounded non-real-time") |
| start script exec | scripts/start-apertar-core.sh:44 | `exec "$CORE_BIN"` -> `exec ${PREFIX[@]+...} "$CORE_BIN"` | extended-in-place |
| ControlServer request limit | src/ipc/ControlServer.cpp:~264 | literal 64*1024 -> named constant 1 MiB | behaviour-changed |
| `reasonPhrase` | src/web/WebServer.cpp:61 | 3 cases | extended-in-place |
| `CaptureSettings` struct | Types.hpp | members appended (not reordered) | extended-in-place |
| `ApertarCoreApp` class | ApertarCoreApp.hpp | members/methods appended; `handleCommand` signature untouched; new `handleReadOnlyHardwareCommand` runs before command lock (see below) | extended-in-place + parallel path |
| README "Hardware Controls" | README.md:176 | text inserted after `run_script` paragraph | extended-in-place |

Upstream's boot config write is `sudo -n install -m 644 <tmp> /boot/firmware/config.txt` (ApertarCoreApp.cpp:3157 @upstream); README says the port keeps it as fallback when the helper is missing ("Core falls back to `sudo -n install`, as the fan mode always has").

## 5. New abstractions

| Name | Kind | Files | Upstream equivalent |
| --- | --- | --- | --- |
| `apertar-boot-config` helper + sudoers | root helper, sh | scripts/, config/ | upstream: `sudo -n install` inline in `ApertarCoreApp.cpp:3157`; other helpers exist: `apertar-standby-usb`, `apertar-standby-low-power` in `/usr/local/libexec` (not in repo) |
| `apertar-media-trim`, `apertar-media-tune` helpers | root helpers | scripts/, config/ | none; same libexec+sudoers shape as standby helpers |
| `apertar-tune` | python CLI | scripts/ | none |
| apertar-media-tune.conf (+ RAM override, precedence env > override > file > default) | config format | config/ | upstream: `apertar-hardware.conf` (per class), `camera_settings.conf`, env only for `APERTAR_TUNING_FILE` |
| `apertar-media.tmpfiles.conf` | systemd tmpfiles | config/ | none upstream |
| `HardwareConfigStore` / `HardwareConfigText` | class + header module | src/hardware | upstream: each hardware class parses own section |
| `GpioChipInfo`, `I2cProbe` | classes | src/hardware | none |
| `PlaybackFrames` + `third_party/liblj92` | module + vendored C lib | src/playback, third_party | upstream Core: no `third_party/` tree, no decoder |
| `MediaProfile`, `StoragePreroll`, `BufferBudget`, `ClipMerge`, `FramePath`, `ClipName`, `BlackLevel`, `LogCurve`, `FpsCeiling`, `ModeLadder`, `TuningTdnStrip`, `Imx283Modes`, `Imx585Modes`, `DngTags`, `ClipFrames` | header-only modules | src/ | upstream: logic inside CameraController/App (probable; not checked here) |
| Worker threads in `ApertarCoreApp` | media watcher, buffer event, buffer safety stop, storage pre-roll, media trim, clip merge, controls worker (7) | ApertarCoreApp.hpp | upstream App has no such worker threads in header (check by grep: `std::thread` in upstream hpp, unconfirmed) |
| `handleReadOnlyHardwareCommand` | parallel dispatch before `commandMutex_` | ApertarCoreApp.hpp | upstream: single `handleCommand` under one mutex |
| `CdngLog` enum + 4 free inline functions | enum + helpers in Types.hpp | Types.hpp | upstream Types.hpp holds enums and `toString` only; helpers with rules are new |
| Host tests `tools/*_test.cpp` | test layer | tools/ | none upstream (no tests) |
| Env-var knob layer (20+ vars) | A/B instrument | start script, README | none |

## 6. tools/ and host tests (not in CMake)

Build line is in each file's header comment; none are CMake targets, no `ctest`.

| File | Tests | Build |
| --- | --- | --- |
| black_level_test.cpp | cdng/BlackLevel.hpp | `g++ -std=c++20 -O2 -Wall -Wextra -I src -I include` |
| boot_config_test.cpp | hardware/BootConfigText.hpp | same |
| boot_config_helper_test.sh | scripts/apertar-boot-config on a scratch copy | `sh tools/boot_config_helper_test.sh` |
| buffer_budget_test.cpp | util/BufferBudget.hpp | `-I src` |
| clip_merge_test.cpp | cdng/ClipMerge.hpp | `c++ -std=c++17 -I src` |
| clip_name_test.cpp | util/ClipName.hpp | `-I src -I include` |
| dng_limits_test.cpp | playback/DngTags.hpp | `-I src -I include` |
| dng_payload_write_test.cpp + .sh | CdngEncoder direct write vs scratch copy, byte-identical | `sh tools/dng_payload_write_test.sh` |
| fps_ceiling_test.cpp | camera/FpsCeiling.hpp | `-I src -I include` |
| frame_path_test.cpp | cdng/FramePath.hpp, playback/ClipFrames.hpp | `c++ -std=c++17 -I src` |
| imx283_modes_test.cpp | camera/Imx283Modes.hpp, ScalerCropGeometry | `-I src -I include` |
| imx585_modes_test.cpp | camera/Imx585Modes.hpp | `-I src` |
| log_curve_test.cpp | cdng/LogCurve.hpp, Types.hpp cdngLogBits, ModeLadder | `-I src -I include` |
| media_trim_test.sh | scripts/apertar-media-trim argument paths only | `sh tools/media_trim_test.sh` |
| storage_buffer_conf_test.cpp | HardwareConfigText + BufferBudget | `-I src` |
| storage_preroll_test.cpp | util/StoragePreroll.hpp | `-I src -I include` |
| tuning_tdn_strip_test.cpp | camera/TuningTdnStrip.hpp (needs libyaml, optional golden dir) | `pkg-config --cflags --libs yaml-0.1` |
| flatten_clip.py | operator tool: flatten/unflatten split clips; `python3 -I`, dry run default | not a test |
| gen_log_curve.py | prints Log curve constants and golden block for log_curve_test | not a test |

Only two of these (flatten_clip.py) are operator tools; the rest are tests. `tools/` does not exist upstream.

## 7. Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| "bounded, non-real-time boost only" statement of the unit drop-in | capture-priority.conf | file now also grants RT priority up to 80 (unused unless env set) |
| Request line 64 KiB cap | ControlServer.cpp | raised; per-connection memory bound 16x larger |
| Nothing removed from upstream README, scripts or config | | verified: diff for README/scripts/config shows only additions except one start-script exec line and CMake LANGUAGES line |
| Default behaviours changed in README: DNG page drop `writer` -> `sync` default; TDN off by default (upstream behaviour: ISP default, tdn on); `APERTAR_FPS_LIMIT=table` restores old fps cap | README, fork-log | operator-visible default changes (code outside scope) |

## 8. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| Pi 5 / CM5 `config.txt` with `[pi5]`, `[pi4]`, `[all]` sections; helper refuses text without one | apertar-boot-config:51, README | Pi 4 header tolerated |
| `/boot/firmware/config.txt` path (Bookworm layout) | helper, README | |
| RP1 overclock `dtoverlay=rp1-clk-333mhz` | README | Pi 5 only |
| Four cores: `APERTAR_RT_CPUS` default `1-3` | start script | core 0 left to system |
| Service user `pi`, home `/home/pi` | sudoers, tmpfiles, apertar-tune default base path | hard-coded; upstream sudo helpers also assume pi (unconfirmed) |
| NVMe on PCIe: class `pi-nvme`, `nvme_core default_ps_max_latency_us` | apertar-media-tune | Pi 5 PCIe HAT assumed |
| Drive mounted under `/media/` | apertar-media-trim | |
| Display overlays hold GPIO 0-27 and I2C bus 1 (DPI) | README | gpio/I2C numbering fixed in text |
| Sensors by name (imx477, imx585, imx283) per connector cam0/cam1, "cam1 is overlay default" | README | two connectors = Pi 5 |
| exFAT folder-lock cost measured at 45,000 frames | README | rig-specific measurement |
| RAM size: `ram` write-queue budget (BufferBudget), raw buffers 8 | media-tune.conf, tools | no Pi model switch in scope |
| Fan block in config.txt kept byte for byte | README | fan mode uses same helper |
| gpiochip numbering | GpioChipInfo.cpp (outside scope) | `Reinsert the GPIO chip definition` task #11; not read here |

## 9. fork-log status (statuses recorded, not verified)

| Commit | Recorded status / tests |
| --- | --- |
| 438a342, 26da30e | fork-only; built, "not tested"; helper "added, not installed" |
| f91fafa, 1af26c8, a37a902 | fork-only; Pi tested 2026-10-29 |
| 3526e4b, f5a61b8, 4d80a35, 5395fa4, dcf09ee | fork-only; Pi branch `controls` |
| d44b177 | fork-only; squash of 19 commits |
| adac040 | "fork-only, offer upstream"; not built on the Pi yet |
| 2edc6d0, 46d0e8c | fork-only; built on Pi 2026-11-02, Core not restarted |
| e625c68 | fork-only; Pi only; measured 2026-11-04 |
| 9ec37b5, ba0658d, d7dd337 | fork-only; clip-split branch; "not tried" per row 8ec2f1a |
| c57c284, 6ef0ddc | RT: README says A/B decides; no result recorded in fork-log rows read |
| dda1713, 496817f, 3b87d99 | not found in the fork-log grep (unconfirmed) |
Host tests: run on desk only; none runs on a Pi except those named "Pi tested" above.
