# s1-storage-cinemate — Storage media optimisation, Cinemate side

Reader: source investigation for porting per-media raw-writing optimisation to Apertar-Core.
Repos read: cinemate @ d6cc93e (dev), cinepi-raw @ 63a08d5 (dev), cinemate-handbook @ c99ff77.
Nothing was run on a camera. Every line number below was obtained by grep -n and the window was read.

Status legend: CONFIRMED = line opened and read; PROBABLE = inferred, reason given; UNKNOWN = not in the sources read.

---

## 0. Architecture in one paragraph (CONFIRMED)

Two cooperating processes decide how Cinemate writes to media:

1. `storage-automount.service` (root, `User=root`, `Before=cinemate-autostart.service`, `Nice=-10`; cinemate/services/storage-automount/storage-automount.service:5,15,30@d6cc93e). It reacts to udev block events, classifies the *connection type* of the device (`cfe_nvme` / `usb_nvme` / `usb_ssd` / `nvme_hat` / `other`), mounts by label (`RAW` -> `/media/RAW`, anything else -> `/media/<LABEL>`), and applies per-device block-queue tuning plus global VM dirty-page cushions for the active RAW target only (storage-automount.py:108-157, 238-266, 285-382).
2. `SSDMonitor` inside cinemate (unprivileged `pi`; cinemate/src/module/ssd_monitor.py:78-152@d6cc93e). It watches `/media/RAW`, derives a *GUI device type* (`SSD` / `NVMe` / `CFE` / `Unknown`), detects the *filesystem*, picks a *recorder profile by filesystem* (storage_profiles.py), publishes it to Redis, and `cinepi_multi.py` turns the profile into cinepi-raw launch flags (`--encode-workers`, `--disk-workers`, `--encode-affinity`, `--disk-affinity`, `--encode-nice`, `--disk-nice`, `--buffer-count`).

Note the split: **media class** (connection) drives kernel-level tuning (needs root); **filesystem** drives the user-space writer topology (workers, affinity, buffer count). The GUI device-type label is a third, independent classification. Nothing in the recorder profile depends on the media class, and nothing in the kernel tuning depends on the filesystem except the ext4 mount string.

---

## 1. Device classification and filesystem detection

### 1a. storage-automount `_classify_media` (CONFIRMED)

cinemate/services/storage-automount/storage-automount.py:238-266@d6cc93e.
Input: `pyudev.Devices.from_device_file(ctx, devnode)` (:241); failure -> `"other"` (:243).
Rules, in order:
- devnode starts with `/dev/nvme` -> walk `device.ancestors`; any ancestor with `subsystem == "usb"` -> `usb_nvme` (:246-250); otherwise `nvme_hat` (:255). The comment at :252-255 says CFE HAT is *not* distinguished here ("CFE will be detected via I2C"); so in practice **`cfe_nvme` is never returned by `_classify_media`** — a CFexpress card behind the hat classifies as `nvme_hat`. The `cfe_nvme` profile entry exists (:109-116) but is unreachable from this function. (CONFIRMED from the function text; whether anything else assigns `cfe_nvme` — grep of the file found no other producer — PROBABLE that the profile is dead.)
- any USB ancestor -> read udev prop `ID_USB_DRIVER` (:260); `uas` -> `usb_nvme` (:262-263, comment "Treat UAS as potentially NVMe-backed"), else `usb_ssd` (:264).
- else `other` (:266).

Filesystem: `_get_filesystem_info` (:212-236) runs `blkid -s LABEL -o value` and `blkid -s TYPE -o value`, 5 retries with 0.5 s delay for udev settle (:212, :229-234). Returns `(label|None, fstype|None)`.

Outputs of the classification (what it changes):
- mount options: `_mount_options(fstype, kind)` (:343-349): ext4 -> the media profile's `ext4_opts`; `ntfs`/`ntfs3`/`exfat`/`vfat` -> `FS_MOUNT_PROFILES[fstype]["opts"]` (:161-166); anything else -> `"rw,noatime"` (:349).
- block queue: `_apply_block_tuning` (:285-307) writes `/sys/block/<root>/queue/scheduler` (:294), `rq_affinity` (:299), `nr_requests` (:304) from the profile.
- NVMe power: `_apply_nvme_power_tuning` (:309-317) writes `/sys/module/nvme_core/parameters/default_ps_max_latency_us` (fallback `/sys/module/nvme/...`), value from profile `nvme_ps_latency_us`; if not writable logs a hint to add `nvme_core.default_ps_max_latency_us=<v>` to cmdline.txt (:317).
- sysctl cushions: `_apply_sysctl_cushions` (:319-341) — see §5.
- Gate: `_apply_media_tuning` (:365-382) applies block tuning to every drive but sysctl + NVMe power **only when `mount_path == RAW_ACTIVE_PATH`** (:376), i.e. `/media/RAW`. Reason in docstring :367-374 and commit c8f06c9 (2026-06-09): previously any mounted USB stick re-applied global cushions for its own profile and silently overrode the recorder drive's tuning.
- Not changed by this classification: recorder profile, buffer count, GUI label (those come from SSDMonitor).

### 1b. SSDMonitor `_detect_device_type` (CONFIRMED)

cinemate/src/module/ssd_monitor.py:482-547@d6cc93e. Returns `'SSD' | 'CFE' | 'NVMe' | 'Unknown'` (:486).
Inputs: device name from `findmnt --noheadings --output SOURCE /media/RAW` (:437-446); root block device derived by stripping `pN` for nvme or trailing digits otherwise (:491-498); `/sys/block/<root>/device/uevent` text lowercased (:500-504); `os.path.realpath("/sys/block/<root>/device")` (:507-508); and `self._cfe_hat_present` from an I2C probe.
Rules in order:
- `"/usb/" in realpath` or `driver=usb-storage` or `driver=uas` in uevent -> `SSD` (:511-514).
- `"1000110000.pcie" in realpath` -> `CFE` if hat present else `NVMe` (:516-521). Comment :516-519: this is the Pi 5 PCIe bridge, where both a CFE card and a plain NVMe appear; the I2C probe is what tells them apart.
- `driver=nvme` / `pci_driver=nvme` / `nvme` in uevent -> `CFE` if hat else `NVMe` (:524-527).
- `driver=ahci` / `sata` / `class=0x0106` -> `SSD` (:530-533).
- name heuristics: `nvme*` -> CFE/NVMe; `sd*`/`usb*` -> SSD (:536-540); else `Unknown` (:544).

CFE HAT probe `_detect_cfe_hat` (:243-268): `smbus.SMBus(1).read_byte(0x34)` — any reply means present (:257-262). The docstring :246-255 records the removed fallback (existence of `/sys/bus/platform/drivers/brcm-pcie/1000110000.pcie`, bound on every Pi 5) that labelled every plain NVMe as CFE; handbook entry 2026-09-05 (cinemate-handbook/lessons/hardware-log.md:1610-1642@c99ff77) is the hardware record, fix commit `888093c2` per :1634.

Filesystem `_detect_filesystem_type` (:448-466): `findmnt --noheadings --output FSTYPE /media/RAW` (:450-454), normalised through `normalize_storage_filesystem`; fallback `blkid -s TYPE -o value` with `fresh=True` (:460-464); else `"unknown"` (:466). Mount options `_detect_mount_options` (:468-480): `findmnt --output OPTIONS`.

Normalisation (cinemate/src/module/storage_profiles.py@d6cc93e): `SUPPORTED_STORAGE_FILESYSTEMS = ("ext4","exfat","ntfs")` (:8); aliases `ex4`->ext4, `ntfs3`->ntfs, `fuseblk`->ntfs, `""/none/no disk`->none (:20-30); `vfat` deliberately **not** aliased (:25-27, "FAT32 is unsupported for recording and should surface as 'unknown'"); unsupported -> `"unknown"` (:106-110). Commit 0142c5b (2026-06-08) removed a former vfat->exfat alias because a FAT32 drive got the exFAT profile.

`_blkid_value` (:566-613): tries `blkid -p`, then `blkid -c /dev/null`, then plain cached `blkid`; a command must return non-empty to count. Docstring F-284 (:581-593): running as `pi`, `blkid -p` raises Permission denied and `blkid -c /dev/null` exits 0 with empty stdout; the old code stopped there and never reached the cache query, failing LABEL lookup for a whole-disk filesystem with no partition table. Handbook lesson: cinemate-handbook/lessons/what-the-pi-taught-us.md:55-66@c99ff77 ("A tool exiting 0 does not mean it answered").

What each SSDMonitor output changes (`_handle_mount` :345-389):
- `STORAGE_TYPE` = device type lowercased (:359) -> GUI SYS-row box (`SSD`/`NVME`/`CFE`): simple_gui.py:1736-1745 (HDMI), app/templates/template.html:1330-1332 (web).
- `STORAGE_FILESYSTEM` (:360) -> recorder profile at cinepi-raw launch (cinepi_multi.py:812-833), filesystem badge `exFAT`/`NTFS`/`ext4` (simple_gui.py:1747-1755; template.html:1333-1336), fsck policy (§5), and an operator advisory for NTFS logged once per mount (:378-380, text at storage_profiles.py:130-134).
- `STORAGE_MOUNT_OPTIONS` (:361) — published, not consumed by the recorder (docs/redis-keys.md:88).
- `STORAGE_RECORDER_PROFILE` (:362) — name only; `cinepi_multi` re-derives from the filesystem anyway (:816-821).
- `IS_MOUNTED`, `SPACE_LEFT` (:363-364), `WRITE_SPEED_TO_DRIVE` reset to 0 (:367).
- `mount_event.emit(mount_path, device_type, filesystem, profile)` (:383-388) -> StoragePreroll (§3) and `CinePiController._handle_storage_mount_event` (cinepi_controller.py:2144-2147), which refreshes fps_max and schedules a cinepi-raw **restart** if the profile changed (:2161-2214; deferred while recording or during preroll, :2137-2142).
- `_next_fsck_ts = 0` (:389) -> fsck right after mount.
- Device swapped in place behind `/media/RAW` (`mount --move` promotion) is detected by comparing `findmnt SOURCE` each poll and re-running `_handle_mount` (:329-343).

`_redis_set_many` (:229-240) deliberately uses `set_value` per key: a pipeline left the local cache stale and `_build_args` read `"none"` for the filesystem, selecting the wrong profile at launch.

Polling: pyudev monitor on `block` with `poll(poll_interval)`; event or timeout, it resyncs (`_udev_loop` :297-312); `poll_interval = 1.0`, `space_interval = 1.0`, `space_delta_gb = 0.1` (:95-100).

### 1c. Buffer count (CONFIRMED)
`--buffer-count` comes from the *filesystem* profile (`buffer_count`), not the media class: cinepi_multi.py:844-866@d6cc93e; override `sensors.raw_buffer_count` when > 0 (:848-853; default 0 in resources/settings/settings_default.jsonc:19; docs/settings-json.md:594 "Leave at 0; the active storage profile sets the depth"). cinepi-raw's own default is 0 (cinepi-raw/core/options.hpp:199@63a08d5, "Number of in-flight requests (and buffers)").

---

## 2. Recorder profile per filesystem (CONFIRMED)

cinemate/src/module/storage_profiles.py:50-95@d6cc93e, `RECORDER_PROFILES`:

| profile (fs) | label | encode_workers | disk_workers | encode_affinity | disk_affinity | encode_nice | disk_nice | buffer_count |
|---|---|---|---|---|---|---|---|---|
| default (none/unknown) :51-60 | default-safe | 4 | 2 | 1-2 | 2 | -10 | -5 | 8 |
| ext4 :61-73 | ext4-throughput | 4 | 8 | 1-2 | 1-2 | -10 | -5 | 8 |
| exfat :74-83 | exfat-conservative | 4 | 2 | 1-2 | 2 | -10 | -5 | 10 |
| ntfs :84-94 | ntfs-conservative | 4 | 2 | 1-2 | 2 | -10 | -5 | 10 |

Selection: `recorder_profile_name_for_filesystem` (:138-142) — supported fs -> its own profile, anything else -> `default`. `recorder_profile_args` (:156-171) emits the six flags; `--buffer-count` is emitted separately by cinepi_multi (:866).

Stated reasoning:
- buffer_count comment :32-39: libcamera base for video+raw is 6; more buffers absorb transient disk-write latency spikes "that would otherwise starve the sensor and drop a frame"; exFAT/NTFS are "slower / spikier" than ext4 "which has flatter write latency"; each extra buffer costs ~25 MB of CMA at 4K (raw+video share the count), so stay conservative and check `grep Cma /proc/meminfo` before raising. Commit a61a589 (2026-06-01): "Frame drops are disk-write-latency-bound, and exFAT/NTFS produce spikier write+metadata latency than ext4 (FAT/dir-entry churn from a new DNG file every frame), which matches the field observation that ext4 drops less"; values ext4=8, exFAT/NTFS=10, default=8.
- NTFS comment :9-14: Linux NTFS drivers (ntfs-3g/FUSE and in-kernel ntfs3) "fail or short-write under sustained 4K DNG throughput far more readily than exFAT/ext4, losing frames at the write() syscall with no inter-frame timing gap"; cinepi-raw counts them as `writeFailures`. `RECOMMENDED_STORAGE_FILESYSTEMS = ("ext4","exfat")` (:15).
- ext4 gets 8 disk workers (throughput), exFAT/NTFS 2 (conservative). No explicit comment explains why 2 vs 8 beyond the labels; PROBABLE reasoning: FAT/MFT metadata serialises writers so parallel disk workers buy nothing and add contention.
- Audio-core invariant :41-49: `cinepi-audio-capture` pins itself to the last core (N-1, core 3 on a 4-core Pi) at SCHED_FIFO 80; no profile's encode/disk affinity may include that core or capture stalls at launch and the WAV loses sync (garbage start timecode or no WAV). Worker affinity stays within 0-2, "practically 1-2, leaving core 0 for the camera pipeline and IRQs". cinepi-raw strips the audio core as a backstop but profiles must not rely on it. Locked by `_test/test_storage_profiles.py` (tests :53, :65, :77, :83). History: commit 7551a16 (2026-06-07) — ext4/ntfs disk_affinity was "2-3"; ext4 takes recorded garbage WAV start TC (e.g. 00:59:59:24) or no WAV, exFAT (disk "2") stayed in sync. The installer additionally adds `isolcpus=managed_irq,domain,3 nohz_full=3 rcu_nocbs=3 irqaffinity=0-2` on 4-core boards (cinemate/cinemate-install.sh:1256-1278@d6cc93e) and `fsck.mode=skip` (:1281).
- Pi 4 cap: `PI4_MAX_DISK_WORKERS = 4` (:153); comment :149-152: on Pi 4 the xHCI controller is shared by storage and the USB microphone, so many concurrent writers congest the bus and stall ALSA capture; Pi 5 routes NVMe over PCIe and keeps the full count. Applied in `recorder_profile_args(..., is_pi4=...)` (:159-163); test :83-99 asserts ext4 8 -> 4 on Pi 4, exfat stays 2.
- cinepi-raw's own defaults when flags are absent: `encode-workers` 2, `disk-workers` 8, affinities empty, nice unset (cinepi-raw/cinepi/cinepi_options.cpp:206-223@63a08d5). So Cinemate's profiles *raise* encode workers (2->4) and *lower* disk workers for exFAT/NTFS (8->2).

Launch wrapper (known already, confirmed location): `chrt -f 70`, `ionice -c2 -n0`, `taskset -c 1-3` (cinepi_multi.py:300-310). Note `taskset -c 1-3` includes core 3; the per-worker `--*-affinity` then narrows the DNG workers to 1-2 and the audio helper pins itself to 3.

Profile change at runtime: a mount event with a different filesystem triggers `restart_camera(preview_enabled=True)` (cinepi_controller.py:2193-2208) — the worker topology is a launch-time property of cinepi-raw; the restart is deferred while recording or pre-rolling (:2137-2142, :2166-2175).

---

## 3. Storage pre-roll (CONFIRMED)

Module cinemate/src/module/storage_preroll.py@d6cc93e (502 lines). Docstring :1-6: records a short clip at maximum FPS whenever CineMate starts or new storage is mounted, then removes the clip so the media is "warmed up".

When it runs:
- Startup: `main.py:1168` calls `mark_startup_ready()` after init; `_arm_startup_preroll` sleeps `startup_delay` (1.0 s default, :31) then triggers with `delay=0.0` if media is mounted (:151-171). A mount that arrived before startup finished is deferred and becomes reason `startup-mount` (:173-183, :165-168). History: commit a6536e6 (2026-04-24) "Defer storage preroll until startup is ready".
- Mount: subscribed to `ssd_monitor.mount_event` when `auto_enabled` (:58-59); triggers with `settle_delay` (3.0 s default, :30).
- Manual: CLI `storage preroll` -> `trigger_manual()` with `force=True` (:66-71); web GUI `PREROLL` button (docs/web-gui.md:29).
- Setting: `system.storage.auto_preroll` (default true; resources/settings/settings_default.jsonc:14-16; config_loader.py:234, :522-523; docs/storage-preroll.md:5). Off disables only automatic runs (:110-114). History: 345f1ee (2026-05-26).
- Gate: no camera mode table (`sensor_detect.res_modes` empty) -> automatic run skipped (:116-129; commit 734f7be 2026-09-01). Single-flight via `_active` lock (:131-134).

What it does (`_execute_preroll` :195-303):
1. Abort if not mounted or `IS_RECORDING == "1"` (:196-202).
2. Snapshot: mount-root directory list, `LAST_DNG_CAM0/1`, `RECORDING_TIME`, `RECORDING_TC_REC/TOD`, user fps (`FPS_USER` else `FPS`) and `FPS_MAX` (:206-236).
3. Resolve the **raw sensor hardware max fps** for the current mode via `sensor_detect.get_fps_max(camera, sensor_mode)`, bypassing the dynamic-resolution cap (:233-235, :332-351). Temporarily raise Redis `FPS_MAX` to it (:248), apply fps with `lock_override=True` and `dynamic_resolution_suspended=True` (:249, :353-369). History: f023d92 (2026-06-02) "preroll at sensor max fps"; bb5a065 (2026-05-24) "Defer dynamic resolution until after storage preroll". docs/sensors.md:193: "temporarily suspends dynamic resolution so the mounted media is stress-tested".
4. Set `STORAGE_PREROLL_ACTIVE=1` and `cinepi_controller.set_preroll_active(True)` (:239-242).
5. `start_recording()`, wait `REC==1` (5 s timeout), `sleep(duration)` (**2.0 s** default, :29, :255), `stop_recording()`, wait `REC==0` (5 s), wait `IS_WRITING==0` and `IS_WRITING_BUF==0` (10 s each) (:252-262).
6. finally: restore `FPS_MAX`, re-apply user fps (:269-273); cleanup; restore last-clip/timer keys; clear flag.

Cleanup `_cleanup_preroll` (:411-464): candidate dirs = parent dirs of the new `LAST_DNG_CAM*` values and any new top-level dir on the mount root, excluding baseline dirs and anything whose mtime+1 s predates the run start (:446, :457); `shutil.rmtree` each (:485-491) then remove empty parents up to the mount root (:495-502). `_restore_preroll_state` (:371-392) writes the snapshotted values back (defaults `"None"`, 0.0, `00:00:00:00`) so the deleted take never shows as "latest".

Failure handling: any exception inside the record phase is logged `Storage pre-roll failed` and the finally block still restores state and cleans up (:264-301); cleanup/restore failures are warnings (:282-283, :292-293); `STORAGE_PREROLL_ACTIVE` is reset to 0 at construction in case of a crash mid-preroll (:49-55). All `_wait_for_value` timeouts are tolerated (return False, never raise, :317-327).

Side effects while active: RedisListener suppresses drop/SYNC alerts and final frame-sync analysis (redis_listener.py:565-570, :696, :994-998, :1080-1084); `rec` is ignored (docs/cli-commands.md:23); GUI shows a blue background and hides clip names and recording time (simple_gui.py:1249-1262, :1309-1310, :2131-2156); format is refused while `is_writing_buf`/`is_buffering` are 1 (ssd_monitor.py:1088) — the preroll waits for both to clear before it ends.

Why ("warm-up of what?"): the sources say only "warmed up" / "primed" / "stress-tested" (storage_preroll.py:5; docs/storage-preroll.md:3; docs/settings-json.md:112 "priming the card"; docs/cli-commands.md:199 "so the media is primed for the next real take"; docs/sensors.md:193). No file states a mechanism (SLC cache, allocator, FUSE daemon, page cache, drive power state). UNKNOWN which physical effect is targeted; PROBABLE candidates (reader's inference, not Cinemate's claim): waking an NVMe from a deep APST state, pre-allocating/cluster-chain warmup on exFAT, and surfacing a too-slow drive via the DROP overlay before the real take. The handbook has **no** entry mentioning preroll/pre-roll (grep over lessons/hardware-log.md returned none), so there is no measured before/after evidence for the warm-up.

Git history: `git log -S preroll -- src/module`: e577437 2025-10-22 "Add automatic storage preroll warmup" (origin), a6536e6 2026-04-24, bb5a065 2026-05-24, 345f1ee / fa5dd49 2026-05-26, f023d92 2026-06-02, 734f7be / fdff38f 2026-09-01/02.

---

## 4. Write-speed measurement and time-left estimate (CONFIRMED)

Measurement is **not** fio/dd and **not** from cinepi-raw stats. `SSDMonitor._update_space_left` (ssd_monitor.py:773-824@d6cc93e): every `space_interval` (1 s) it calls `os.statvfs(/media/RAW)`; `gb = f_bavail*f_frsize/1024^3`; `write_speed = (last_free_gb - gb) * 1024 / dt` MB/s (:788-795, :793), i.e. **free-space decrease per second**, zero when free space did not shrink. Published to Redis `write_speed_to_drive` as `"%.2f"` (:797-801); reset to 0 on mount/unmount (:367, :403). It therefore reads the *consumption rate*, not the drive's capability, and only while something is being written; during idle it shows 0.

Display: HDMI GUI `values["write_speed"] = f"{...:.0f} MB/s"` (simple_gui.py:1393, :1399), field position :503; the SYS-row speed box is commented out (:1759-1765). Web GUI writes `V.write_speed` into `v-write` (template.html:1639). docs/redis-keys.md:91 "Current write speed in MB/s". OLED can show it (docs/hardware-controls.md:229).

Time-left: simple_gui.py:1378-1396. `mins = space_left_gb*1000 / (file_size_mb * fps * 60)` (:1389), shown as `"<n> MIN"` (:1390); falls back to `"<n> GB"` when `file_size` is 0 or fps unknown (:1391-1392); `"NO DISK"` when unmounted (:1395). `file_size` is a static per-mode model, `compute_frame_size_mb(width, height, bit_depth, compression_ratio=1.0, thumbnail_bytes)` = `((ceil(width*bits/8)*height + thumbnail_bytes) + 1024) / 1.0 / 1e6` (sensor_detect.py:282-296; `DNG_HEADER_OVERHEAD_BYTES = 1024` :94; `DNG_COMPRESSION_RATIO = 1.0` :99 with the note that cinepi-raw writes DNGs uncompressed), recomputed on mode/log/thumbnail changes (cinepi_controller.py:1355-1416). The thumbnail term was added after the 2026-09-13 finding that the embedded IFD1 thumbnail cost 2.7 MB/frame and made minutes-remaining wrong (sensor_detect.py:87-93; handbook hardware-log.md:1830-1860). Nothing uses the measured write speed to predict sustainability or to cap fps.

Live "drive cannot keep up" signal comes from cinepi-raw, not from the speed figure: `writeFailures` counter (cinepi-raw/cinepi/dng_encoder.cpp:2365,2376,2382; published cinepi_controller.cpp:643) consumed at redis_listener.py:873-882; live warning + DROP latch at :1075-1099 ("Disk write failure ... The drive cannot keep up ... Use exFAT or ext4"); post-take verdict attributes missing files to write failures (:1895-1901, :1953-1961, :2009-2013). Commit 5fbef52 (2026-06-10).

---

## 5. fsck / ntfsfix policy, mount options, format defaults (CONFIRMED)

Read-only health check (SSDMonitor `_maybe_run_fsck` :827-875): once right after each mount (`_next_fsck_ts = 0`, :389) and then every 24 h (:863); skipped while `is_recording == "1"` (:831); single-flight lock (:833). Command: `sudo nice -n 19 ionice -c3 fsck -n <devnode>` (:850-851). Result `OK|FAIL <iso-time> | <last line>` to Redis `fsck_status` (:855-858; docs/redis-keys.md:92). **NTFS is skipped** and reported `OK ... fsck skipped (no read-only checker on Linux)` because ntfsfix is repair-only (:840-848).

Repair on mount failure (storage-automount `_auto_repair` :384-400): ext4 -> `e2fsck -f -p` (accept rc 0,1,2) (:387-389); ntfs -> `ntfsfix` (:391-393); exfat -> `fsck.exfat -a` (:395-397); then one mount retry (:490-500). Failed devices get a 30 s cooldown (:425, :444, :509), bypassed on RAW promotion (`force`).

Mount options:
- storage-automount ext4 by media class (`PROFILES[kind]["ext4_opts"]`): `rw,noatime,nodiratime,commit=60` for cfe_nvme/usb_nvme/usb_ssd/nvme_hat (:110, :119, :128, :141); `rw,noatime` for other (:150).
- `FS_MOUNT_PROFILES` (:161-166): ntfs, ntfs3, exfat, vfat all `uid=<PI_UID>,gid=<PI_GID>,dmask=022,fmask=133,rw,noatime` (PI_UID/PI_GID default 1000, :47-48).
- Unknown fs -> `rw,noatime` (:349). The mount is `mount -t <fstype> -o <opts> <dev> <path>` (:468) then `os.chown(mount_path, PI_UID, PI_GID)` (:479).
- SSDMonitor's own (sudo) mount path mirrors this: `EXT4_MOUNT_OPTIONS = "rw,noatime,nodiratime,commit=60"` (ssd_monitor.py:46); ntfs/exfat `uid=1000,gid=1000,dmask=022,fmask=133,rw,noatime`; default `rw,noatime` (:637-642); `sudo mount -t ... -o ...`, 3 retries with `sync; udevadm settle --timeout=5; blkid -g` between (:682-714, :615-635); `sudo chown pi:pi` (:696). Sudoers allows `pi` to run `/bin/mount, /bin/umount, /usr/bin/ntfs-3g, /sbin/mount.ext4` without password (cinemate-install.sh:1946-1947).

Kernel write-smoothing (root, RAW target only; `_apply_sysctl_cushions` :319-341): saves originals once (:321-325), then `vm.dirty_ratio=0`, `vm.dirty_background_ratio=0` (:328-329), `vm.dirty_writeback_centisecs=150` (1.5 s), `vm.dirty_expire_centisecs=3000` (30 s) (:330-331), `vm.dirty_background_bytes` and `vm.dirty_bytes` from the profile (:332-333). Restored when no mounts remain (`_restore_sysctls` :351-363).

`PROFILES` (:108-157):

| kind | ext4_opts | dirty_bytes | dirty_bg_bytes | rq_affinity | scheduler | nr_requests | nvme_ps_latency_us |
|---|---|---|---|---|---|---|---|
| cfe_nvme :109-116 | rw,noatime,nodiratime,commit=60 | 1 GiB | 256 MiB | 2 | none | 512 | 0 |
| usb_nvme :117-125 | same | 512 MiB | 256 MiB | 2 | none | 256 | 0 |
| usb_ssd :126-139 | same | 256 MiB | 128 MiB | 2 | none | 256 | (none) |
| nvme_hat :140-147 | same | 1 GiB | 256 MiB | 2 | none | 512 | 0 |
| other :149-156 | rw,noatime | 256 MiB | 128 MiB | 1 | mq-deadline | 128 | (none) |

usb_ssd rationale (comment :129-133): "a USB SSD's write speed falls off a cliff once its SLC cache is exhausted (~90 s into a 4K take). A large dirty buffer would then fill and block writers in one long balance_dirty_pages stall — a burst of dropped frames. A smaller cushion trades that for shorter, more frequent stalls (smoother)". A log hint is emitted on usb_ssd mount (:338-341): "if frames drop ~90 s in, the SSD cannot sustain the data rate (check NAND type, or use NVMe / a lower fps)". Commit d7a8d2b (2026-06-07) lowered usb_ssd from 512->256 MiB / bg 256->128.

Format defaults (SSDMonitor `format_drive` :1080-1264):
- refuses while `is_writing_buf` or `is_buffering` is 1 (:1086-1094); default filesystem **exfat** (:1096; docs/cli-commands.md:152 "Defaults to exfat"); only ext4/exfat/ntfs (:1098).
- sets the eject-intent flag so storage-automount does not remount mid-format (:1110-1116), `sync`, `umount` -> `umount -l` retries -> `fuser -km` on mount and device -> `blockdev --flushbufs` -> last lazy attempt (:1118-1166).
- if the partition covers < 90 % of the parent disk, repartitions: `parted mklabel gpt`, `mkpart RAW 0% 100%`, `set 1 msftdata on` (so macOS mounts it), `partprobe` (:1175-1228, :1200, :1215).
- `mkfs.ext4 -F -L RAW` (:1231); `mkfs.exfat -L RAW` with **no `-c`**: default cluster (~256 KB on large drives) is macOS/Windows-compatible, "Forcing 1 MB clusters was tried for write-latency but breaks the macOS exFAT driver on most versions" (:1233-1237); `mkfs.ntfs -Q -F -L RAW` quick format (:1239-1245); 120 s timeout (:1248); settle; remount via `mount_drive(filesystem=fs, device=...)` (:1257-1261).
- Packages: `e2fsprogs ntfs-3g exfatprogs` (cinemate-install.sh:604; docs/installation-steps.md:489).

Label/mount discovery for self-mount: `blkid -s LABEL -o device`, candidates ordered nvme, then sd, then others; first with `LABEL == "RAW"` wins (ssd_monitor.py:648-680). storage-automount mounts any labelled device; RAW arbitration = lowest /dev path active, others standby `/media/RAW1..` (:1153-1156; commit 3259da7 2026-06-09).

---

## 6. Measured evidence in handbook / docs

- Sustained write rates (CONFIRMED, docs): imx585 4K 16-bit ClearHDR + Log 12 at 25 fps measured 2026-09-13: 317.0 MB/s no thumbnail, 317.4 jpeg, 322.7 mono, 334.0 colour; recording time per TB 52.6 / 52.5 / 51.7 / 49.9 min; encode 22.2 / 26.3 / 23.5 / 25.5 ms per frame; "never dropped a frame, never failed a write, and never let the disk queue past two" (cinemate/docs/settings-json.md:329-336@d6cc93e). Media/filesystem for that run: UNKNOWN (not stated in the table; handbook :1065-1110 for the same period mentions "exFAT NVMe" rigs at :1068 and :1109, PROBABLE that it was exFAT on NVMe).
- NTFS-over-FUSE ceiling (CONFIRMED, handbook 2026-08-27/28, hardware-log.md:945-985): 12-bit 21 fps soak ~264 MB/s ran 2520/2520 frames clean; every 16-bit soak (~355+ MB/s) stalled after ~15-22 s as the RAM pool (173 frames ≈ 2941 MB) filled; `/media/RAW` was NTFS via `fuseblk` on NVMe (:964-968). Conclusion at :977-978: the limit is "sustained write bandwidth on NTFS-over-FUSE". Also :570-571 notes a 477 GB NVMe still NTFS from a format test.
- 'ext4 drops less' (CONFIRMED as a stated field observation, not a measurement): commit a61a589 body ("matches the field observation that ext4 drops less"); storage_profiles.py:35-36 ("ext4, which has flatter write latency"). No numbers anywhere.
- SLC-cache cliff (CONFIRMED as a comment, no measurement cited): storage-automount.py:129-133 and :338-341 ("~90 s into a 4K take"); commit d7a8d2b. Handbook grep for SLC/T7/Samsung/cliff: no hits — UNKNOWN whether the 90 s figure was measured on Cinemate hardware.
- Drop behaviour per filesystem (CONFIRMED as statements): storage_profiles.py:9-14 and docs/changelog.md:165, :218 ("exFAT support and filesystem-aware storage profiles ... IMX585 25 fps at 4K to SSD without frame drops" in 3.3.1; "NTFS flagged supported but not recommended (can drop frames under sustained 4K writes)" in 3.4.0). The 3.3.1 note at :219 says dynamic resolution "switches to HD above 25 fps when an SSD is used" — but dynamic_resolution.py contains no storage/ssd reference (grep empty), so this is PROBABLE marketing shorthand for an fps-ceiling mechanism, not a storage-aware rule. docs/sensors.md:197 and docs/troubleshooting.md:12 tell the operator to lower fps or use faster media on DROP.
- Format checklist passes on all three filesystems (CONFIRMED, handbook 2026-08-26 :248-283 and 2026-09-01 :1179-1198); both note the NTFS fstype string (`ntfs`/`ntfs3`/`fuseblk`) was never captured.
- `/media/RAW` has no ownership model (`cp -a` chown fails; exFAT/NTFS-shaped) — handbook 2026-09-15 :3081-3110.
- No handbook evidence exists for: preroll effect, per-media write rates (SD, USB SSD, CFE), exFAT vs ext4 drop counts. All UNKNOWN.
- Media recommendations (CONFIRMED): docs/getting-started.md:46 — SSD (Samsung T7 recommended), NVMe, or CFE Hat; format exFAT, label RAW; ext4 also works; NTFS supported but not recommended. Pi 4/5, 4 GB+ RAM (:25). docs/hardware-controls.md:198 CFE hat: "Format the card exFAT". docs/redis-keys.md:86 lists storage_type values as "NVME, USB, or SD" — stale versus code (`ssd`/`nvme`/`cfe`/`unknown`).

---

## 7. What a port needs

### 7a. Decision table as Cinemate actually implements it

Media class (connection) -> kernel tuning (root):

| class | how detected | dirty_bytes / bg | scheduler | nr_requests | rq_affinity | NVMe APST |
|---|---|---|---|---|---|---|
| NVMe on Pi PCIe (incl. CFE hat) | /dev/nvme*, no USB ancestor | 1 GiB / 256 MiB | none | 512 | 2 | ps_max_latency 0 |
| USB NVMe / UAS bridge | USB ancestor + ID_USB_DRIVER=uas, or /dev/nvme* with USB ancestor | 512 MiB / 256 MiB | none | 256 | 2 | 0 |
| USB SSD (usb-storage) | USB ancestor, driver != uas | 256 MiB / 128 MiB | none | 256 | 2 | — |
| other (SD etc.) | fallback | 256 MiB / 128 MiB | mq-deadline | 128 | 1 | — |
plus `dirty_ratio=0`, `dirty_background_ratio=0`, `writeback_centisecs=150`, `expire_centisecs=3000`, applied only for the recording target.

Filesystem -> writer topology (user space, launch-time):

| fs | encode workers | disk workers | disk affinity | in-flight camera buffers | mount opts |
|---|---|---|---|---|---|
| ext4 | 4 | 8 (4 on Pi 4) | 1-2 | 8 | rw,noatime,nodiratime,commit=60 (rw,noatime for 'other') |
| exFAT | 4 | 2 | 2 | 10 | uid/gid=1000,dmask=022,fmask=133,rw,noatime |
| NTFS | 4 | 2 | 2 | 10 | same as exFAT; advisory logged |
| none/unknown (FAT32 etc.) | 4 | 2 | 2 | 8 | rw,noatime |
Encode affinity always 1-2, encode nice -10, disk nice -5; never touch the last core (audio).

### 7b. Needs root vs. app-side

Root (Cinemate does these in a systemd service running as root, or via sudoers for mount/umount):
- `/sys/block/<dev>/queue/{scheduler,nr_requests,rq_affinity}`; `/sys/module/nvme_core/parameters/default_ps_max_latency_us` (or cmdline).
- `vm.dirty_*` sysctls (and restoring them).
- `mount -o ...` with per-fs options; `chown` of the mount point; `e2fsck`/`ntfsfix`/`fsck.exfat`; `mkfs.*`, `parted`, `partprobe`, `blockdev`; `fuser -km`; `umount -l`.
- `blkid -p` (raw probe) — unprivileged `blkid` only sees the cache and may return empty with exit 0 (F-284).
- CPU isolation kernel args; `chrt -f` needs CAP_SYS_NICE or an rtprio limit.

App can do itself:
- Classify media from `/sys/block/<root>/device` realpath + `uevent` (strings `/usb/`, `driver=uas`, `driver=usb-storage`, `1000110000.pcie`, `driver=nvme`) and `findmnt --output SOURCE,FSTYPE,OPTIONS <mount>`; CFE hat via I2C 0x34 read.
- Choose worker count, queue depth, affinity, nice, per-frame write strategy, chunking, O_DIRECT, fallocate, fadvise per filesystem; pick in-flight request/buffer count per filesystem (Cinemate: 8 ext4, 10 exFAT/NTFS, ~25 MB CMA each at 4K; check `Cma` in /proc/meminfo).
- Pre-roll: 2 s take at sensor max fps on mount/startup, then delete; gate on no-recording, no-camera; suppress drop warnings and "latest clip" updates during it.
- Consumption-rate "write speed" via statvfs deltas and minutes-left = free / (frame_bytes * fps); a real capability probe (fio/dd) does not exist in Cinemate — a port wanting a true probe must add one.
- Count write failures (short write / open / close errors) in the writer and surface them live; this is Cinemate's only live "drive too slow" signal.
- Count free space in GB and gate recording on `media_mounted`.

### 7c. Pitfalls recorded in the sources
- The PCIe-bridge sysfs node is present on every Pi 5; it is not a CFE-hat probe (handbook 2026-09-05; ssd_monitor.py:246-255).
- `vfat` is FAT32, not exFAT; aliasing it to exFAT picked the wrong profile (commit 0142c5b; storage_profiles.py:25-27).
- NTFS fstype may report as `ntfs`, `ntfs3` or `fuseblk`; normalise all three. ntfsfix is repair-only; `fsck -n` has no NTFS backend. `mount --move` does not work on FUSE mounts (storage-automount.py:703 comment).
- `--disk-affinity` including the audio core broke WAV sync (commit 7551a16); taskset for the whole process must not be the only control.
- Pi 4: storage and USB mic share xHCI; cap disk writers at 4 (storage_profiles.py:149-153).
- A large `dirty_bytes` on a USB SSD turns the SLC-cache cliff into one long `balance_dirty_pages` stall (storage-automount.py:129-133).
- Global sysctls must be applied only for the recording target; any other mount re-applying them overrides the recorder's tuning (commit c8f06c9).
- Redis cache coherence: a pipelined write left the filesystem key stale and the wrong profile was launched (ssd_monitor.py:232-237).
- Unprivileged `blkid -c /dev/null` returns empty + exit 0; require non-empty output before accepting (ssd_monitor.py:581-593).
- exFAT 1 MB clusters break macOS; keep mkfs.exfat defaults (~256 KB) (ssd_monitor.py:1233-1236).
- Worker topology is a launch-time property: changing filesystem at runtime means restarting the recorder, deferred until not recording (cinepi_controller.py:2161-2214).
- An EIO on one corrupt clip directory (NTFS after a hot-swap mid-take) must not be treated as device loss, or the monitor and the automounter loop unmount/remount (ssd_monitor.py:741-750).
- Dirty-page cushions and `commit=60` buy smoothness but lengthen the window of unflushed data on a yank; Cinemate's `expire_centisecs=3000` allows up to 30 s of dirty data (storage-automount.py:331). (Reader's inference from the numbers; Cinemate does not discuss this trade-off.)

---

## Unanswered / UNKNOWN
- Physical mechanism the pre-roll warms (no source states it; no handbook measurement).
- Whether the "~90 s SLC cliff" was measured on Cinemate hardware or taken from general knowledge.
- Media and filesystem used for the 317 MB/s thumbnail-cost measurement.
- Any measured per-media write rate (SD, USB SSD, USB NVMe, CFE) or exFAT-vs-ext4 drop count.
- Whether `cfe_nvme` kernel profile is ever selected (no producer found; PROBABLE dead).
- Which fstype string NTFS reports on the shipped image (handbook twice notes it was not captured).
- Why exFAT/NTFS use exactly 2 disk workers (no comment beyond the "conservative" label).

---

## Verification

Adversarial verifier pass. Every cited file was opened at the cited line on the checkouts (cinemate @ d6cc93e, cinepi-raw @ 63a08d5, cinemate-handbook @ c99ff77; `git status --porcelain` clean on all three). Line numbers were re-derived with `grep -n` and `sed -n`/`cat -n` windows; every number was recomputed from the source expression. Note: the apertar-core checkout is at 2715569, not the f60e301 the task names; this reader cites no apertar-core line, so nothing here is affected.

Verdict key: CONFIRMED = line and content match and the status label is honest; CORRECTED = claim stands but a citation or figure needed fixing (corrected value given); REFUTED = source shows otherwise; UNVERIFIABLE = not decidable from the repos.

### Finding-by-finding

| # | Claim (short) | Verdict | Notes / corrected citation |
|---|---|---|---|
| 1 | Two-process split: root storage-automount classifies connection type + kernel tuning; unprivileged SSDMonitor classifies GUI type, detects filesystem, selects recorder profile -> cinepi-raw flags | CONFIRMED | storage-automount.py:238-266, .service:5,15,30, ssd_monitor.py:345-389, cinepi_multi.py:812-866 all match. `_detect_device_type` body is :482-543 (reader's 547 is the trailing blank/comment). |
| 2 | `_classify_media` rules; `cfe_nvme` never produced | CONFIRMED, and the PROBABLE upgraded to CONFIRMED | :246-250 usb_nvme, :255 nvme_hat, :260-264 uas/usb_ssd, :266 other. `grep -rn cfe_nvme` over the whole cinemate tree hits only the PROFILES key (:109) and the docstring (:239); `kind` is assigned once, at :448, from `_classify_media`. The I2C hat code (`_cfe_hat_worker` :925-962, `_cfe_hat_init` :1163-1182) only drives the hat LED (`write_byte 0x01/0x00`) and binds/unbinds `1000110000.pcie`; it never touches `kind`. The `cfe_nvme` profile is dead code. |
| 3 | SSDMonitor device-type rules, I2C 0x34 probe, removed PCIe-bridge fallback | CONFIRMED (line-ends trimmed) | Rules :511-514 / :520-521 / :524-527 / :530-533 / :536-539; `return "Unknown"` is :543 (not :544). `_detect_cfe_hat` is :243-267 (not 268); `read_byte(0x34)` :259. Handbook :1610-1642 matches, fix commit `888093c` dated 2026-09-05 23:03. |
| 4 | Filesystem detection and normalisation; vfat not aliased | CONFIRMED (one prose cite corrected) | ssd_monitor :450-454 findmnt, :460-464 blkid fallback, :466 unknown; storage_profiles :8, :15, :20-30, :25-27, :106-110 match. Prose cite "F-284 note :581-593" is wrong: the F-284 paragraph is ssd_monitor.py:574-586 (`F-284:` at :574). Commit 0142c5b dated 2026-06-08 00:32 confirmed. |
| 5 | Recorder profile values; cinepi-raw defaults 2 encode / 8 disk | CONFIRMED | Table values re-read at storage_profiles.py:51-60, :61-73, :74-83, :84-94 exactly as stated; `recorder_profile_args` :156-171; cinepi_options.cpp `default_value(2)` :207, `default_value(8)` :210, affinities `implicit_value("")` :213/:216, nice no default :218-223. Buffer comment "~25 MB of CMA" :36-37, "libcamera's base ... is 6" :33. |
| 6 | Audio-core invariant, 2-3 -> 1-2/2 fix, tests, isolcpus tokens | CONFIRMED | :41-49 comment, :66-69 and :89 "Was 2-3"; tests at _test/test_storage_profiles.py:53, :65, :77, :83; cinemate-install.sh comment :1257-1265, tokens :1271-1276 (`isolcpus=managed_irq,domain,3`, `nohz_full=3`, `rcu_nocbs=3`, `irqaffinity=0-2`), `fsck.mode=skip` :1281. Commit 7551a16 2026-06-07 13:59 body matches the garbage-TC claim (`00:59:59:24`). |
| 7 | Pi 4 cap = 4 (shared xHCI) | CONFIRMED | :149-153 comment+constant, :159-163 application, test :83-99 asserts 8->4 and exfat stays 2. |
| 8 | Profile change needs cinepi-raw restart, deferred while recording/preroll | CONFIRMED | cinepi_controller.py `_storage_profile_restart_allowed` :2137-2142, `_handle_storage_mount_event` :2144-2147, defer log :2168-2176, `restart_camera(preview_enabled=True)` :2206. |
| 9 | Pre-roll mechanics and numbers | CONFIRMED | storage_preroll.py defaults :29-31 (2.0 / 3.0 / 1.0), `_execute_preroll` :195-303, waits :253 (REC 5 s), :258, :261-262 (10 s each), cleanup :411-464 with `st_mtime + 1 < start_ts` at :446 and :457, `_remove_tree` :485-502, restore :371-392, flag reset :49-55. main.py constructs at :948-954, `mark_startup_ready()` :1168. docs/storage-preroll.md :1-21 five-step text matches. |
| 10 | No source states what the pre-roll warms | CONFIRMED (UNKNOWN label honest) | :1-6 "warmed up"; docs/sensors.md:193 "stress-tested"; settings-json.md:112 "priming the card"; cli-commands.md:199 "primed". `grep -rni 'preroll\|pre-roll' cinemate-handbook/lessons/` returns nothing. Commit bodies of e577437 (2025-10-22), 345f1ee and fa5dd49 are empty, so the origin commit states no purpose either. |
| 11 | Write speed = statvfs free-space delta, not fio/dd/cinepi-raw | CONFIRMED (one prose line off) | ssd_monitor.py:786-795, formula `delta_gb * 1024 / delta_t` :793; publish :799-802; `space_interval=1.0`, `space_delta_gb=0.1` :99-100. Reset-to-0 on unmount is :405 (reader wrote :403). simple_gui :1393/:1399 "MB/s", speed box commented out :1758-1766; template.html:1639 `v-write`. |
| 12 | Minutes-left formula and static frame-size model | CONFIRMED (recomputed) | simple_gui.py:1389 `(space_left*1000)/(file_size*fps*60)`, :1390 "MIN", :1392 "GB", :1395 "NO DISK". sensor_detect.py:94 `DNG_HEADER_OVERHEAD_BYTES = 1024`, :99 `DNG_COMPRESSION_RATIO = 1.0`, `compute_frame_size_mb` :282-296 = `((w*bits+7)//8 * h + thumb + 1024)/ratio/1e6`. `_recompute_file_size` :1355-1416. |
| 13 | `writeFailures` is the only live "too slow" signal | CONFIRMED | dng_encoder.cpp `write_failures_.fetch_add` at :2365 (short write), :2376 (close error), :2382 (open error); cinepi_controller.cpp:643; redis_listener.py :873-882, :1075-1099 (warning text + DROP latch), :1895-1901, :1953-1961, :2009-2013. Commit 5fbef52 2026-06-10 00:54. |
| 14 | fsck -n policy, NTFS skipped, repair chain, 30 s cooldown | CONFIRMED (range end trimmed) | ssd_monitor :831 recording gate, :833 lock, :843-848 NTFS skip, :850-851 `sudo nice -n 19 ionice -c3 fsck -n`, :863 `24*3600`. storage-automount `_auto_repair` is :384-398 (reader 384-400): e2fsck :387-389 rc in (0,1,2), ntfsfix :391-393, fsck.exfat -a :395-397; retry :490-500; cooldown 30 at :425/:429, set at :444/:509. |
| 15 | Mount option strings, chown, SSDMonitor sudo mount path | CORRECTED (one line) | Mount command `cmd = ["mount", "-t", fstype, "-o", opts, ...]` is storage-automount.py:472, not :468 (:468 is `_apply_media_tuning` in the already-mounted branch); `os.chown` :479 correct. Strings at :110/:119/:128/:141 (`rw,noatime,nodiratime,commit=60`), :150 (`rw,noatime`), :161-166 FS_MOUNT_PROFILES, :349 fallback all match. ssd_monitor :46, :637-642, :691 sudo mount, :696 chown pi:pi, retries=3 :682, settle :615-635. Sudoers :1946-1947 match. |
| 16 | Kernel write-smoothing values per class | CONFIRMED (recomputed) | `1 * 1024**3` = 1 GiB, `256 * 1024**2` = 256 MiB, `512 * 1024**2` = 512 MiB, `128 * 1024**2` = 128 MiB at :111-112, :120-121, :134-135, :142-143, :151-152; `150` cs = 1.5 s :330, `3000` cs = 30 s :331; nr_requests 512/256/256/512/128, rq_affinity 2/2/2/2/1, scheduler none x4 + mq-deadline, `nvme_ps_latency_us "0"` only on cfe_nvme/usb_nvme/nvme_hat. Gate `mount_path == RAW_ACTIVE_PATH` :376; `_apply_media_tuning` body is :365-379. Commit c8f06c9 2026-06-09 body matches. |
| 17 | SLC-cache cliff rationale and log hint | CONFIRMED | Comment :129-133, hint :338-341 ("~90 s"). d7a8d2b 2026-06-07 18:32 body: "512 -> 256 MiB, bg 256 -> 128". See *added* below for provenance. |
| 18 | Format defaults | CONFIRMED | :1088-1094 refuse while `is_writing_buf`/`is_buffering`, :1096 `"exfat"` default, :1098 set, :1116 eject intent, :1200 `fill_ratio < 0.9`, :1208/:1211/:1215/:1219 parted/partprobe, :1231 `mkfs.ext4 -F -L RAW`, :1233-1237 exfat no `-c` + macOS comment, :1245 `mkfs.ntfs -Q -F -L RAW`, :1248 `timeout=120`, remount :1259. cli-commands.md:152 "Defaults to `exfat`". |
| 19 | Measured throughput: 317-334 MB/s table; NTFS-over-FUSE stall | CONFIRMED, with a provenance caveat added | settings-json.md table :331-336 and the "never dropped a frame ... never let the disk queue past two" sentence :338 match. Handbook :964-968 matches (~264 MB/s clean, ~355+ MB/s stalls after 15-22 s, pool 173 frames ~2941 MB, "NTFS via `fuseblk` on NVMe"). Caveat: sensor_detect.py:182 says the benchmark is "the entry in cinemate-handbook's hardware log", but no such entry exists at c99ff77 (grep for `317`, `322.7`, `52.6`, `per TB`, `disk queue` over lessons/ is empty; the 2026-09-13 Phase-2 entry :2047-2049 says the per-mode CPU comparison was "Not run, and still open"). The only record of the 317 MB/s run is docs/settings-json.md, added by commit b141a8c (2026-09-13 23:48), whose body does not name the media. |
| 20 | 'ext4 drops less' is an observation; NTFS statements; no per-media table | CORRECTED (citations) | docs/changelog.md is 141 lines; the cited :165 and :218-219 do not exist. Correct lines: changelog.md:84 ("NTFS flagged supported but not recommended (can drop frames under sustained 4K writes)"), :137 ("exFAT support and filesystem-aware storage profiles ... IMX585 25 fps at 4K to SSD without frame drops"), :138 (dynamic resolution "switches to HD above 25 fps when an SSD is used"). docs/getting-started.md is 60 lines; "Samsung T7 recommended" is :25, not :46, and "Pi 4 or 5 ... 4 GB RAM or more" is :4, not :25. storage_profiles.py:9-15 and :35-36 ("flatter write latency") correct; a61a589 body "matches the field observation that ext4 drops less" confirmed. `grep -ni 'storage\|ssd\|nvme\|filesystem' src/module/dynamic_resolution.py` is empty, so the PROBABLE about 3.3.1 wording stands. |
| 21 | Operator display: type box, fs badge, purple+DROP, blue preroll, NO DISK; redis-keys.md stale | CONFIRMED | simple_gui.py :1736-1745 type box, :1747-1755 fs badge (`{"exfat": "exFAT", "ntfs": "NTFS"}` :1749), purple :2152-2153, blue :2155-2156, "DROP" box text :1662; template.html :1330-1336; redis-keys.md:86 "NVME, USB, or SD" versus code `ssd`/`nvme`/`cfe`/`none` (ssd_monitor :359, :397). |

Port-needs numbers (1 GiB/256 MiB; 512/256; 256/128; none/mq-deadline; 512/256/128; rq_affinity 2/1; 150/3000 cs; 4/8/2 workers; 8/10 buffers; ~25 MB CMA; chrt -f 70 / ionice -c2 -n0 / taskset -c 1-3 at cinepi_multi.py:300/:306/:310) all re-read and correct. The reader's "surprises" all hold; surprise 3 (cfe_nvme unreachable) is now CONFIRMED rather than PROBABLE.

### Added (unanswered items settled or narrowed from source)

- **`cfe_nvme` is never selected — CONFIRMED.** Only two occurrences in the tree (PROFILES key storage-automount.py:109, docstring :239); the single `kind =` assignment (:448) comes from `_classify_media`, which returns `nvme_hat` for every non-USB NVMe (:255). The hat I2C code (:925-962, :1163-1182) drives LED and PCIe bind only. A CFexpress card behind the hat gets the `nvme_hat` tuning (identical values anyway: 1 GiB/256 MiB, none, 512, 2, ps 0).
- **NTFS fstype string on the shipped image — PROBABLE `fuseblk`.** Observed once: handbook hardware-log.md:967 "`/media/RAW` is NTFS via `fuseblk` on NVMe" (dev CM5, 2026-08-27/28). Mechanism: the installer installs `ntfs-3g` (cinemate-install.sh:604) and whitelists `/usr/bin/ntfs-3g` in sudoers (:1946); no installer/service line mentions the in-kernel `ntfs3` driver (grep over cinemate-install.sh and services/ finds only the `ntfs3` key in FS_MOUNT_PROFILES :163 and the FUSE comment at :703); storage-automount mounts with `-t <blkid TYPE>` = `ntfs` (:472), which dispatches to `mount.ntfs` = ntfs-3g when installed, and FUSE mounts report `fuseblk`. The two format-checklist entries (:275-277, :1191-1194) say the string was never captured, so this remains PROBABLE, not CONFIRMED.
- **Why exactly 2 disk workers for exFAT/NTFS — UNKNOWN, now with evidence.** The originating commit 2a49fa1 (2026-05-17 23:32, "Add storage filesystem recorder profiles") has an empty body and already carried 4/2 default, 4/8 ext4, 4/2 exfat, 4/2 ntfs (`git show 2a49fa1:src/module/storage_profiles.py` :26, :35, :44, :53). Later commits (a61a589, 7551a16, d7a8d2b, 0142c5b, 5fbef52, c171975) changed affinity, buffers and comments only. No rationale exists in the repo.
- **~90 s SLC cliff provenance — PROBABLE desk research, not a Cinemate measurement.** d7a8d2b's body introduces the change as "the hardening from the research pass"; the handbook has no SLC/T7/Samsung hit and its only "cliff" (:2369) is about a 15 ms render budget. Treat the 90 s as a generic USB-SSD figure.
- **Media/filesystem of the 317-334 MB/s run — still UNKNOWN; pointers narrowed.** The 2026-09-13 session was "the operator's camera" (:2002); the 2026-09-05 entry describes that camera as "an ordinary NVMe in the Pi 5 slot and no CFE Hat" (:1612); the 2026-09-15 entry on the same host (`cinepi`) says `/media/RAW` "is the SSD", its filesystem "was not captured; the behaviour is exFAT/NTFS-shaped and the inference that it is exFAT is unconfirmed" (:3098-3101). The 2026-08-31 entries (:1067-1068, :1108-1109) record `cinepi` as exFAT NVMe. So: NVMe PROBABLE; exFAT PROBABLE; neither stated with the measurement. Also note the dangling reference in sensor_detect.py:182 to a handbook entry that does not exist at c99ff77.
- **Pre-roll mechanism — nothing new.** Origin commit e577437 (2025-10-22) and the two setting commits have empty bodies. UNKNOWN stands.

### Items the port should take from this pass

- Use `nvme_hat`'s values for a CFE card; do not model a separate CFE kernel profile (Cinemate's is unreachable).
- Normalise `fuseblk` -> ntfs and expect it on an ntfs-3g system; if the port ever mounts NTFS with the in-kernel driver it will see `ntfs3` instead and `mount --move` will work there (storage-automount.py:703 documents the FUSE failure).
- Treat the 2-disk-worker figure and the 90 s SLC figure as unexplained defaults, not measured results; the only measured storage numbers in the sources are the ~264 MB/s pass / ~355 MB/s stall on NTFS-over-FUSE (handbook :964-968) and the 317-334 MB/s no-drop table whose media is unstated (settings-json.md:331-338).
- When citing changelog.md and getting-started.md use :84/:137-138 and :4/:25 respectively.
