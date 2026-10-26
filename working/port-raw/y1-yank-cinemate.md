# y1-yank-cinemate — Media yank, Cinemate side

Reader: source investigation for porting "robustness to an accidentally yanked recording drive" to Apertar-Core.
Commits read: cinemate @d6cc93e (dev), cinepi-raw @63a08d5 (dev), cinemate-handbook @c99ff77. Nothing was run on hardware; every claim is CONFIRMED (from a line opened and read), PROBABLE (reasoned from read code, reason given) or UNKNOWN.

Citation form: `repo/path:line@commit`. All cinemate cites are @d6cc93e, cinepi-raw @63a08d5, handbook @c99ff77 unless stated.

---

## 0. Components and their roles (orientation)

| Component | Runs as | Role in a yank |
|---|---|---|
| `services/storage-automount/storage-automount.py` (systemd `storage-automount.service`, root, `Before=cinemate-autostart.service`, `Restart=always`, `RestartSec=5`, `Nice=-10`) | root | Owns `/media/RAW`; reacts to udev add/change/remove, CFE-hat I2C buttons, NVMe controller state, and a 3 s statvfs watchdog; lazy-unmounts and promotes standbys. `cinemate/services/storage-automount/storage-automount.service:5-13@d6cc93e`, `...storage-automount.py:1219-1230@d6cc93e` (thread start-up). |
| `src/module/ssd_monitor.py` `SSDMonitor` (inside cinemate, user `pi`) | pi | Watches `/media/RAW` (`os.path.ismount` + `statvfs`), publishes `is_mounted`/`storage_*`/`space_left` to Redis, emits `mount_event`/`unmount_event`/`space_event`, lazy-unmounts on yank errno, implements GUI/CLI mount/unmount/erase/format and the eject-intent flag. |
| `src/module/cinepi_controller.py` | pi | Record start gate (mounted + space), RAM/buffer watchdog auto-stop, restarts cinepi-raw on storage-profile change (on mount event). **Does not subscribe to `unmount_event`.** |
| `src/module/redis_listener.py` | pi | Consumes cinepi-raw `cp_stats` (`writeFailures`, `droppedFrames`, `framesInFlight`, `bufferSize`), raises live DROP warning, computes post-take verdict. |
| `src/module/simple_gui.py` | pi | SYS row storage box (SSD/NVME/CFE + filesystem), minutes/space-left, DROP box + purple flash. |
| cinepi-raw (`cinepi/cinepi_raw.cpp`, `cinepi_controller.hpp`, `dng_encoder.cpp`, `utils.cpp`) | pi, `chrt -f 70` etc. | Creates the clip folder on the record edge, writes DNGs from disk worker threads, counts `write_failures_`, never stops a take because of disk errors. |

---

## Q1. Timeline of a yank during a take

### 1.1 Detection paths

**(a) udev `remove` → storage-automount (fastest, root).**
`_udev_worker()` monitors `subsystem="block"` (`storage-automount.py:869-872@d6cc93e`). On `action == "remove"` for a partition or disk it calls `_on_block_removed(devnode)` then `_clear_eject_flags_for(devnode, "device removed")` (`:913-919`). `_on_block_removed` collects the devnode and every partition of it from `_mounts` and `_raw_pool`; if the device is a RAW pool member or the active RAW it calls `_handle_raw_gone`, otherwise `_unmount` (`:772-786`). `_handle_raw_gone` unregisters the device, clears its failed-cooldown so an immediate reconnect retries (`:764`), `_unmount`s it, and if it was the active drive sets `_active_raw = None` and calls `_promote_next()` (`:759-770`). `_unmount` pops the bookkeeping and issues a **non-blocking** `Popen(["umount","-l", mount_path])` because "umount can block for 30+ seconds" (`:513-528`, comment `:527`); it deliberately does not scan or rmdir the mountpoint ("Directory scans can block on yanked or erroring media", `:530-531`); then `_restore_sysctls()` which only restores when no managed mounts remain (`:351-363`).

**(b) statvfs on the mount root, two independent pollers.**
- storage-automount `_sanity_watchdog()` statvfs's every managed mount every **3 s** (`:835-864`, `time.sleep(3)` at `:864`); on an errno in `YANK_ERRNOS` (`{EIO, ENOENT, ENODEV, ENOTCONN, ESTALE}`, `:97-103`) it logs "device yanked, unmounting" and calls `_handle_raw_gone` for RAW devices or a direct `umount -l` for others (`:845-859`); SD card (`/dev/mmcblk*`) mounts are skipped because "statvfs can block for 30+ seconds on bad SD card mounts" (`:839-843`). The same loop then runs `_safety_net_promote()` (`:863`).
- cinemate `SSDMonitor._update_space_left()` statvfs's `/media/RAW` at most every `space_interval` = **1.0 s** (`ssd_monitor.py:95-100` ctor defaults, throttle `:782-783`, statvfs `:786`); on `OSError` it logs "statvfs failed" and calls `_handle_storage_error(exc, action="check free space on")` (`:807-811`). `main.py:708@d6cc93e` constructs `SSDMonitor(redis_controller=...)` with defaults, so poll_interval = space_interval = 1.0 s, space_delta = 0.1 GB.

**(c) Mount table check.** `SSDMonitor._check_mount_status()` calls `os.path.ismount(/media/RAW)` on every wake (`:322-343`); wakes come from `monitor.poll(self._poll_int)` on a pyudev netlink monitor filtered to `block` — "event or timeout, we resync" (`:297-312`, poll at `:308`), i.e. at most 1 s latency and immediately on any block-device udev event; without pyudev a plain 1 s poll loop (`:314-317`). If `ismount` flips to False while `_is_mounted` → `_handle_unmount()` (`:327-328`). PROBABLE: Python's `os.path.ismount` returns False when `stat()` raises (it swallows OSError), so on a dead mount this path may fire before the statvfs path does — not verified on hardware.

**(d) iterdir/stat/rglob errno during recording-folder scans.** `get_latest_recording_infos()` (called by the post-take analysis, `redis_listener.py:1672@d6cc93e`) routes `OSError` from `iterdir` (`ssd_monitor.py:1275-1280`, action "scan"), `stat` (`:1284-1289`, "inspect recordings on") and `rglob` (`:1320-1333`, "count files on") through `_handle_storage_error`; a root-level failure returns `[]` ("Genuine storage loss (root-level failure) — stop scanning", `:1327`).

**(e) NVMe controller state.** storage-automount `_nvme_watchdog()` reads `/sys/block/<root>/device/state` every **0.5 s**; `"dead"` → "NVMe controller dead ... lazy unmount" → `_handle_raw_gone`/`_unmount` (`:813-833`, check `:825`, sleep `:833`).

**(f) CFE hat latch.** `_cfe_hat_worker()` polls the hat's I2C controller at `0x34` every **0.05 s** (`:925-1105`, sleep `:1105`). Bit 0 = insert latch, bit 1 = eject button. Latch opened ("REMOVED", `:1001`) → pre-emptive unmount of every mounted `/dev/nvme*` via `_handle_raw_gone` (RAW) or `umount -l`, then PCIe unbind of `1000110000.pcie`, LED off, sysctl restore (`:1000-1021`); it skips `_purge_stale_mountpoints()` because `os.path.ismount` "can block for 30+ seconds on stale mounts, freezing button detection" (`:1022-1023`). Eject button released ("EJECTING", `:1092`) → `umount -l` everything, `_active_raw = None`, PCIe unbind (`:1091-1104`). Note this is the hat's *button*, not a surprise card pull: a card pulled with the latch closed is only seen by (a)/(b)/(e).

**(g) Journal.** `SSDMonitor._journal_loop()` (`:1362-1431`) that would parse storage-automount log lines ("Mounted /dev", "Unmounted /dev", "state=dead") exists but its thread creation is commented out (`:139-144`) — CONFIRMED dead code; the `stop()` docstring says so too (`:154-161`). So **no journal path is live**.

### 1.2 What `_handle_storage_error` does (cinemate's single yank funnel)
`ssd_monitor.py:731-771@d6cc93e`: return False unless `exc.errno in YANK_ERRNOS` (`:738`); return False if `exc.filename` is strictly inside the mount (`:748-750`, see Q3); return False if `ENOENT` and the mount point is still a mountpoint (`:755-756`); else log "RAW drive became unavailable while trying to <action>" (`:758-763`) and, if `_is_mounted`, `_force_lazy_unmount(mount_path)` then `_handle_unmount()` (`:765-767`). `_force_lazy_unmount` loops up to **20 × (`sudo umount -l` + 0.2 s sleep)** = ≤ 4 s until `os.path.ismount` is False (`:549-563`).

### 1.3 What `_handle_unmount` does (Redis/GUI state)
`:391-434`: clears `_unreadable_dirs` (`:394`); writes Redis `storage_type="none"`, `storage_filesystem=NO_STORAGE_FILESYSTEM`, `storage_mount_options=""`, `storage_recorder_profile=DEFAULT_RECORDER_PROFILE`, `is_mounted="0"`, `space_left="0"`, `write_speed_to_drive="0"` (`:396-404`); if device type was CFE, writes `0x00` to I2C `0x34` to switch the hat LED off, ignoring OSError "HAT already gone" (`:407-417`); resets all cached state (`:420-432`); emits `unmount_event` (`:431`).

**Who listens to `unmount_event`: nobody.** `grep -rn unmount_event src/` finds only `ssd_monitor.py` itself. `mount_event` has two subscribers: `cinepi_controller.py:239` (`_handle_storage_mount_event`, `:2144-2147`: refresh fps max, update steps, maybe restart cinepi-raw for storage profile) and `storage_preroll.py:59` (`_handle_mount_event`, `:173-183`: schedule pre-roll warm-up). CONFIRMED.

### 1.4 Does cinemate stop the take? No.
- `cinepi_controller.start_recording()` gates on `ssd_monitor.is_mounted == True and ssd_monitor.get_space_left` (`cinepi_controller.py:2352@d6cc93e`), else logs "No disk." (`:2364`). Nothing re-checks `is_mounted` during a take: the only running watchdog is `_recording_worker` (`:4279-4308`) which stops on cinepi-raw RAM-buffer fill ≥ `BUFFER_LIMIT_PERCENT` = **90 %** (`:361`, check `:4288-4295`) or system RAM ≥ `RAM_LIMIT_PERCENT` = **80 %** (`:357`, check `:4298-4303`), polled every **0.25 s** (`:4306`). `_auto_stop_recording` writes `memory_alert=<pct>`, cancels timers and flips `is_recording=0` directly because `stop_recording()` would join the watchdog's own thread (`:4310-4328`).
- So after a yank the take continues from cinemate's point of view until the operator stops it, or the watchdog trips, or cinepi-raw's own pool exhaustion stops it (Q4).

### 1.5 What cinepi-raw does meanwhile
- Each DNG is `open(O_WRONLY|O_CREAT|O_TRUNC, 0644)` → `posix_fadvise(SEQUENTIAL)` → one `write()` → `close()` on a disk worker (`cinepi-raw/cinepi/dng_encoder.cpp:2352-2378@63a08d5`). Open failure, short/failed write, and a `close()` error (only when the write looked OK, so a frame is not double-counted) each `write_failures_.fetch_add(1)` (`:2361-2385`); the frame's in-flight count is released and its pooled buffer returned regardless (`:2389-2398`). **No stop, no retry, no unlink.** `grep unlink|remove` over `dng_encoder.cpp` finds nothing.
- Published every frame as `writeFailures` in the `cp_stats` JSON (`cinepi/cinepi_controller.cpp:643@63a08d5`), reset per clip in `resetFrameCount()` (`dng_encoder.hpp:142`).
- After the lazy unmount the mount is gone from `/proc/mounts`; `disk_mounted()` (`utils.cpp:34-36`, substring `strstr` match of `/media/RAW` over `/proc/mounts`, `:9-32`, `:22`) becomes false. Then: (i) every `open()` fails (parent clip dir no longer exists under the empty `/media/RAW`) → one write failure per frame, pool permits recycle, nothing fills — PROBABLE (errno not verified on hardware); (ii) `triggerRec()` returns 0 before doing anything while `!disk_mounted(options_)` (`cinepi_controller.hpp:212-215`) — see the stop-edge pitfall in Q7.
- If instead the device keeps I/O hung (no fast errno), disk workers block in `write()`, encode workers block on `ram_cv_.wait(... ram_buffers_ < max_ram_buffers_)` (`dng_encoder.cpp:2172-2176`), `framesInFlight`/`bufferSize` climb, and either cinemate's 90 % watchdog or cinepi-raw's own `buffer_full()` (`ram_buffers_ + 2 >= max_ram_buffers_`, `dng_encoder.hpp:258-262`) → `controller.setRecording(false)` + "RAM pool exhausted — recording stopped" (`cinepi_raw.cpp:442-451`) ends the take. `setRecording` is a plain flag on `CinePIState` (`cinepi_state.hpp:67-69`), **not** published to Redis; cinemate would still show `is_recording=1` until its own watchdog trips or the operator stops. PROBABLE ordering: with `BUFFER_LIMIT_PERCENT` 90 % of `buffer_size` cinemate trips before cinepi-raw's `+2` margin.

### 1.6 Latency summary (numbers from source)
| Step | Latency |
|---|---|
| udev remove → storage-automount `umount -l` issued | immediate (event-driven, `:913-919`) |
| statvfs watchdog (storage-automount) | ≤ 3 s (`:864`) |
| NVMe `state=dead` watchdog | ≤ 0.5 s (`:833`) |
| CFE latch poll | 0.05 s (`:1105`) |
| SSDMonitor resync | ≤ 1.0 s poll, or immediate on any block udev event (`:95-100`, `:308`) |
| SSDMonitor statvfs throttle | 1.0 s (`:782-783`) |
| SSDMonitor lazy-unmount retry loop | ≤ 20 × 0.2 s = 4 s (`:549-563`) |
| Promotion wait for `/media/RAW` to free | ≤ 2.0 s in 0.1 s steps (`storage-automount.py:665-677`, `:673`) |
| `_failed_devices` cooldown | 30 s (`:423-433`, `:425`), cleared on removal (`:764`), bypassed on promotion (`force=True`, `:711-712`) |
| `blkid` settle retries on add | 5 × 0.5 s (`:212-236`); CFE path 3 × 0.3 s (`:1066`, `:1078`) |
| CFE PCIe bind → enumeration wait | 0.5 s after bind + 0.8 s (`:962-965`, `:1040`) |

### 1.7 Re-insert
- udev `add`/`change` on a partition → `_get_filesystem_info` → label `RAW` → `_add_raw(dev)` (`:889-895`); whole-disk filesystems handled too (`:898-908`); eject-flagged devices are skipped first (`:884-887`).
- `_add_raw` ignores eject-flagged devices (`:743-749`), registers the device, and if no active RAW and `/media/RAW` is free → `_promote_to_active`, else `_mount_standby` at the first free `/media/RAW<n>` (`:750-757`, `:644-660`).
- `_promote_to_active` waits ≤ 2 s for the lingering lazy-unmounted mountpoint, then `mount --move` an already-mounted standby (preserves the open filesystem) or, for FUSE/ntfs-3g where `--move` fails, unmount + fresh `_mount(dev, RAW_ACTIVE_PATH, force=True)` (`:662-715`). `_mount` applies per-device block tuning and, only for `/media/RAW`, the global sysctl dirty cushions + NVMe power tuning (`:365-382`); on mount failure it runs `_auto_repair` (`e2fsck -f -p` accepting rc 0/1/2; `ntfsfix`; `fsck.exfat -a`, `:384-398`) and retries once (`:489-502`), else 30 s cooldown (`:509`).
- SSDMonitor sees `ismount` True → `_handle_mount()` (`:345-389`): re-detects device/type/filesystem/options/recorder profile, forces a space read, publishes Redis keys and `is_mounted="1"`, emits `mount_event` (`:380-385`), schedules an immediate read-only fsck (`_next_fsck_ts = 0`, `:389`). If the device changes *under* a still-mounted `/media/RAW` (promotion via `mount --move`), it re-runs `_handle_mount` because the recorder profile must follow the promoted drive (`:329-342`; handbook `cinemate-handbook/architecture/cinemate.md:149-165@c99ff77`).
- `mount_event` → `cinepi_controller._handle_storage_mount_event` may restart cinepi-raw for a changed storage recorder profile; the restart is deferred while recording or pre-rolling (`cinepi_controller.py:2144-2215`), and → `storage_preroll` warm-up.
- The periodic `_safety_net_promote()` covers out-of-band unmounts (GUI eject/format): if `_active_raw` is set but `/media/RAW` is no longer a mountpoint, it releases the device and drops it from the pool "so we don't immediately re-grab a drive the user deliberately unmounted", then promotes a standby if any (`:788-811`).

---

## Q2. Eject-intent protocol

**Race fixed.** `umount` makes the kernel emit a udev `change` event for the block device; the udev worker routed `add` and `change` identically into `_add_raw()`, so a deliberate GUI/CLI unmount was re-mounted and re-promoted "typically inside a second" — "unmount, wait, pull" was never safe, and `format_drive()` had a window where the partition could be remounted between `umount` and `mkfs`. Source comments: `ssd_monitor.py:55-69@d6cc93e`, `storage-automount.py:54-71@d6cc93e`; commit `f01b6cd 2026-08-26 23:47:02 +0200 fix(storage): make a deliberate unmount actually eject the RAW drive` (observed: "A single isolated unmount, polled every second for ten seconds, never once read as unmounted"; refs F-160, B9.1).

**Flag path.** `${CINEMATE_STORAGE_RUN_DIR:-/run/cinemate-storage}/eject/<devname basename>` e.g. `/run/cinemate-storage/eject/nvme0n1p1` (`ssd_monitor.py:70-72`, `:899-904`; `storage-automount.py:72-73`, `:561-563`). `/run` is tmpfs so no flag survives a reboot (`:1217-1218` comment).

**Who creates the directory.** storage-automount (root) at startup: `_init_eject_dir()` mkdirs it, chowns `EJECT_STATE_DIR` and `EJECT_FLAG_DIR` to `PI_UID:PI_GID` (1000:1000), chmod 0755 (`:541-558`, called `:1219`); the unit is ordered `Before=cinemate-autostart.service` so it exists before cinemate needs it (`.service:5`).

**Who writes/clears.**
- cinemate `unmount_drive()` touches the flag **before** `sync` and `umount` (`:949`, `:952`, `:959`), via `_set_eject_intent()` (`:906-927`): best-effort, logs a warning and proceeds if the device name is unknown or the touch fails.
- cinemate `mount_drive()` unlinks it **only on a successful mount** ("a failed mount leaves the drive ejected, which is the state the operator actually asked for", `:1001-1007`, `_clear_eject_intent` `:929-940`).
- storage-automount clears it on a real udev `remove` (`:916-919`), and `_clear_eject_flags_for` also clears partition flags when a whole-disk removal arrives as `/dev/nvme0n1` while the flag is keyed `nvme0n1p1` (`:587-603`).
- storage-automount honours it in three places: the udev worker skips `add`/`change` for flagged devnodes (`:884-887`), `_add_raw` ignores flagged devices (`:743-749`), `_promote_next` never promotes a flagged candidate (`:731-732`).

**Un-updated component.** Both halves degrade to the old racy behaviour and neither can wedge a drive permanently unmounted: an old cinemate never writes a flag; an old service ignores flags (`storage-automount.py:68-71`, `ssd_monitor.py:63-69`, commit f01b6cd body).

**Also:** `unmount_drive()` falls back to `_force_lazy_unmount` if the clean `umount` fails (EBUSY when cinepi-raw/ffmpeg still has a file open) (`:960-968`); it does not call `_handle_unmount` itself — the next poll's `ismount` check does.

---

## Q3. False-positive guards

1. **EIO inside the volume vs on the mount root.** `_handle_storage_error` returns False when `exc.filename` is a strict sub-path of the mount root (`ssd_monitor.py:748-750`), using `_path_is_inside_mount` — a pure string comparison "so it cannot hang on a dead/stale mount" (`:716-729`). Rationale in the comment (`:740-747`): a corrupt or half-written clip dir, "common on NTFS after a take is interrupted mid-write by a hotswap", must not tear down a healthy mount; genuine loss surfaces on the root via the periodic statvfs. Commit `58fc7c2 2026-06-10 01:26:27 +0200 fix(storage): don't unmount on a corrupt clip dir (NTFS hotswap flap)`: "unmounting a healthy drive. The automounter immediately remounted it, re-hit the same directory, and looped."
2. **Bad-directory memo.** `_unreadable_dirs` (`:117-123`): a clip dir that raised a localized error is remembered, logged once ("Skipping unreadable recording directory"), skipped on later scans, and the scan continues so one bad dir doesn't hide other takes (`:1302-1305`, `:1324-1333`); cleared on unmount so a repaired/re-inserted drive is scanned fresh (`:392-394`).
3. **ENOENT during erase.** `ENOENT` while `os.path.ismount(mount_path)` is still True is not a yank ("a subdirectory deleted mid-scan during an erase", `:752-756`). `erase_drive()` deletes top-level items with parallel `sudo rm -rf` threads (`:1049-1068`) after `sync` and `sudo fuser -km <mount>` (`:1038-1047`), so the scanner can race it.
4. **The remount loop they hit.** Two instances: (a) EIO-on-clip-dir → unmount → automount remount → re-hit (58fc7c2, above); (b) deliberate unmount → kernel `change` event → `_add_raw` remount within ~1 s (f01b6cd, Q2). Guard (a) is the inside-mount test; guard (b) is the eject flag.
5. **Blocking-call avoidance** (storage-automount): `umount -l` via non-blocking `Popen` (`:527-528`); no mountpoint dir scans on unmount (`:530-531`); statvfs watchdog skips `mmcblk` (`:839-843`); CFE worker skips `_purge_stale_mountpoints` (`:1022-1023`); `_mountpoint_in_use` reads `/proc/self/mountinfo`, "never blocks on I/O" (`:631-642`).
6. **`_handle_mount` bails if the first forced space read already failed** (`:354-355`), so a mount that dies immediately never publishes `is_mounted=1`.
7. **Erase refuses while recording or while buffered frames are flushing** (`is_recording=="1"`, `is_writing_buf`/`is_buffering == "1"`, `:1015-1027`).
8. **blkid empty-but-successful probe** (not a yank, but a mount-state false negative they hit): `_blkid_value(fresh=True)` tries `blkid -p`, then `blkid -c /dev/null`, then the cache-backed query, and only a non-empty value counts — because as user `pi` the first two return empty with exit 0 (F-284, `:566-612`; handbook `lessons/hardware-log.md:149-175@c99ff77`, `lessons/what-the-pi-taught-us.md:57-66@c99ff77`).

---

## Q4. What cinepi-raw does with a half-written take

- **Files left.** The clip folder `/media/RAW/<folder>/` was created on the record edge (`cinepi_raw.cpp:425`, `utils.cpp:93-106`: `create_clip_folder` returns false if `!disk_mounted`, true if the dir already exists (parallel camera), else `fs::create_directories`). DNGs `<folder>_<9-digit index>.dng` are written whole, one buffered `write()` each (`dng_encoder.cpp:2334-2362`). Whatever reached the drive before the pull stays; frames in `encode_queue_`/`disk_buffer_` at pull time become write failures. The folder, WAV (`cinepi_sound.cpp:835-837@63a08d5` path) and any partially flushed page-cache data are left to the filesystem — on NTFS/exFAT this is the "corrupt clip dir" of Q3.
- **Truncation.** A short `write()` (bytes < size) is counted as a failure but the file is **not removed or truncated back** (`:2361-2368`); `close()` deferred errors (FUSE/ntfs-3g write-back) are counted (`:2370-2378`). So a DNG can be present with the wrong size. CONFIRMED mechanism; frequency UNKNOWN.
- **Counters.** `write_failures_` (atomic, `dng_encoder.hpp:282`), reset per clip (`:142`), published as `writeFailures` (`cinepi_controller.cpp:643`). Distinct from `dropped_frames_`, which counts timecode holes (`raw_elapsed >= 2` → `dropped_frames_ += raw_elapsed - 1`, `dng_encoder.cpp:2131-2135`). The hpp comment states the point: write-stage loss has "NO inter-frame sensor gap, so this is the only live signal for write-stage data loss" (`dng_encoder.hpp:222-231`). Commit `8b705c8 2026-06-10 00:54:43 +0200 feat(recorder): count and publish disk-write failures (writeFailures)`.
- **No stop.** Nothing in `diskThread` or the encoder stops recording on failure; the only encoder-side stop is pool exhaustion (`cinepi_raw.cpp:442-451`). `frames_in_flight_` is decremented on every exit path (`:2389`, alloc-fail `:2188`, dng_save-fail `:2263`), so cinemate's `is_writing_buf` (`framesInFlight > 0 and not is_recording`, `redis_listener.py:962-985`) does clear even when every frame failed.
- **How Cinemate reports it.**
  - Live: `redis_listener` ingests `writeFailures` once the startup race guard clears (`:873-882`); when it exceeds the take's running count it logs "Disk write failure: %d frame(s) could not be written ... Use exFAT or ext4" (`:1075-1098`, `:1085`), sets `drop_frame=1`, pulses the drop relay, and re-arms a 0.5 s reset timer (`:1091-1098`). GUI: purple background + inverse colours while `drop_frame` is live (`simple_gui.py:2140-2153@d6cc93e`), and a `DROP` status box (`:1658-1665`, `:1831-1838`).
  - Post-take (`analyze_frames`, `:1659+`): folders from `ssd_monitor.get_latest_recording_infos()` (`:1672`); files counted by `_stable_dng_count` which skips only `st_size <= 0` (`:1605-1620`, `:1618`) — a short-written DNG with size > 0 counts as present (CONFIRMED mechanism). `write_failures_this_take = max(running count, hw counter)` (`:1899-1902`); verdict "Missing frames: N ... (%d confirmed disk-write failure(s) ...)" when both a shortfall and failures exist (`:1953-1961`); "Frame count low ... confirmed disk-write failure(s)" hint (`:2009-2012`). `drop_frame_during_last_take` is set only on a genuine file shortfall (`:1904-1913`).
  - **If the drive is gone at analysis time**, `get_latest_recording_infos` returns `[]` because `_is_mounted` is False (`ssd_monitor.py:1272-1274`), and the analysis logs "No recent recording folders found — falling back to RAM counter" and uses `framecount` as recorded (`redis_listener.py:1731-1735`) — so the verdict cannot see the loss. PROBABLE consequence: no persistent DROP after a yank, only the live warnings.
- **WAV writer behaviour on yank:** UNKNOWN (cinepi_sound.cpp not investigated beyond paths).

---

## Q5. Record-start gates and the auto-stop

**Gates in `start_recording()`** (`cinepi_controller.py:2323-2364@d6cc93e`):
1. Refuse while the previous take's frames are still flushing (`is_writing_buf` or `is_buffering == "1"`) unless pre-roll is active: "rec ignored – previous take's buffered frames are still flushing to disk" (`:2340-2348`, `_buffered_frames_flushing` `:2217-2224`).
2. `ssd_monitor.is_mounted == True and ssd_monitor.get_space_left` (`:2352`) — note `get_space_left` is a bound method, so this operand is always truthy; the effective gate is `is_mounted` only. CONFIRMED from source (`get_space_left` defined `ssd_monitor.py:1353-1355` as a method). Else "No disk." (`:2364`).
3. No fsck gate: `fsck_status` is written by `_maybe_run_fsck` (`sudo nice -n 19 ionice -c3 fsck -n <dev>`, skipped while recording, NTFS reports "OK ... fsck skipped", 24 h cadence, once right after mount; `ssd_monitor.py:827-875`) and shown as `FSCK_STATUS`; `docs/redis-keys.md:92@d6cc93e` says "cinemate-internal, cinepi-raw never reads it". Nothing gates on it.
4. Then: publish `record_cams`, `is_recording=1`, start the watchdog (`:2353-2361`). `memory_alert` reset to 0 (`:2351`).

**cinepi-raw side gate.** `triggerRec()` returns 0 immediately if `!disk_mounted(options_)` (`cinepi_controller.hpp:212-215`), and `create_clip_folder` returns false if not mounted (`utils.cpp:95-96`); `cinepi_raw.cpp:440` encodes only when `nowRecording && controller.folderOpen`.

**Auto-stop** (`_recording_worker`, `:4279-4308`): primary = cinepi-raw RAM frame buffer fill `buffer/buffer_size` ≥ 90 % (`BUFFER_LIMIT_PERCENT`, `:358-361`; `_buffer_fill_percent` reads Redis `buffer`/`buffer_size`); backstop = `psutil.virtual_memory().percent` ≥ 80 % (`RAM_LIMIT_PERCENT`, `:357`); 4 Hz. `_auto_stop_recording` → `memory_alert=<pct>`, `is_recording=0` (`:4310-4328`). `docs/redis-keys.md:94` documents `memory_alert` as the 80 % trip value.

**Handbook evidence of the pool-fill stop on slow storage:** every 16-bit soak on NTFS (`fuseblk`) NVMe "stalled after ~15–22 s: the RAM pool (173 frames ≈ 2941 MB) fills and frames stop arriving — cleanly, no corruption, no telemetry loss" (`lessons/hardware-log.md:962-967@c99ff77`, entry 2026-08-27/28 at `:945`).

---

## Q6. Lessons recorded

**Handbook (`cinemate-handbook@c99ff77`).** The 84 `## ` entries of `lessons/hardware-log.md` contain **no episode of a drive pulled or lost during a take**; the grep for yank/pulled/hotswap/remount/unmount/eject/ntfsfix/fsck/EIO hits only "pulled to the Mac" phrasing and the entries below. Storage-adjacent entries:

| Date | Entry | Cause → fix |
|---|---|---|
| 2026-08-25 | merged-dev verification, F-283/284/286 (`hardware-log.md:149-175`) | "unreliable RAW-volume mount/unmount" was a silently-successful-but-empty `blkid` probe as unprivileged user, not a timeout → `_blkid_value` falls through to the cache-backed query (`ssd_monitor.py:566-612`); also `what-the-pi-taught-us.md:57-66`. |
| 2026-08-26 | RAW pane format-drive checklist (`:248-284`) | format exFAT/ext4/NTFS from browser, remount, "No mount fight with storage-automount.service was observed"; endpoint verifies by observed filesystem not dispatch result. |
| 2026-08-27/28 | RP1 overclock vs storage (`:945-987`) | NTFS fuseblk cannot sustain 16-bit 4K: RAM pool fills in 15–22 s, take stops cleanly; "the real limits are storage". |
| 2026-09-01 | C0 format-drive regression re-check (`:1179-1202`) | still formats and remounts all three filesystems. |
| 2026-09-05 | plain NVMe reported as CFE hat (`:1610-1666`) | PCIe-bridge-present fallback always said yes → `888093c2` consults the I2C `0x34` probe; storage-automount never had the fallback. |
| 2026-09-14 | reference takes gone (`:2306-2313`) | "`/media/RAW` is not an archive." |
| 2026-09-15 | `cp -a` fails on `/media/RAW` (`:3081-3134`) | volume has no ownership model (exFAT/NTFS-shaped). |

`architecture/cinemate.md:149-175@c99ff77` describes the hotswap/standby/promotion/write-failure design in prose. `open-threads.md` has no storage item.

**Git history (the yank lessons live in commit messages, cinemate@d6cc93e):**
- `8f49468 2026-05-11` "Handle yanked storage as a clean unmount" — introduced `_handle_storage_error` (first version of the YANK_ERRNOS funnel; no body).
- `2a49fa1 2026-05-17` "Add storage filesystem recorder profiles" — added `YANK_ERRNOS` to both files, per-filesystem recorder profiles.
- `3259da7 2026-06-09` "multi-drive RAW hotswap with standby + promotion" — root cause of "pull SSD, NVMe/CFE not recognised even after reconnect": `_active_raw` was set even when the mount failed; fixes: active+standby model, promotion from every loss path (udev remove, NVMe dead, statvfs yank, CFE latch) + periodic safety net, cooldown cleared on removal and bypassed on promotion, partition-of-disk matching (no `sda`/`sdaa` false match). "Validated with a 20-assertion local simulation ... Live Pi verification pending."
- `58fc7c2 2026-06-10` "don't unmount on a corrupt clip dir (NTFS hotswap flap)" — see Q3.
- `5fbef52 2026-06-10` (cinemate) + `8b705c8 2026-06-10` (cinepi-raw) — live write-failure warning; NTFS marked not recommended.
- `f01b6cd 2026-08-26` eject intent — see Q2.
- `docs/changelog.md:84@d6cc93e`: "new `hw_write_failures` counter warns live on slow storage; NTFS flagged supported but not recommended"; `:122`: "multi-drive RAW hot-swap with a standby drive and automatic promotion. Default format is exFAT."

---

## Q7. What a port needs

### State machine (as Cinemate effectively implements it, two processes)
```
                 udev add/change (not eject-flagged)
  ABSENT ───────────────────────────────────────▶ MOUNTING (blkid 5×0.5 s, mount, repair+retry, 30 s cooldown on fail)
    ▲                                                   │ success → active (/media/RAW) or standby (/media/RAWn)
    │ udev remove (clears eject flag)                   ▼
    │                                                MOUNTED/ALIVE  ── ssd_monitor: ismount ∧ statvfs OK (1 s)
    │                                                   │
    │   yank: udev remove | statvfs YANK_ERRNO (3 s / 1 s) | nvme state=dead (0.5 s) | CFE latch (0.05 s)
    │                                                   ▼
    │                                                LOST → lazy umount -l (non-blocking) → promote standby (≤2 s wait, mount --move)
    │                                                   │      ssd_monitor: _handle_unmount → Redis none/0 → unmount_event (no listener)
    │                                                   ▼
    └─────────────────────────────────────────────── UNMOUNTED
                                                        ▲
  deliberate eject: flag file → sync → umount (lazy fallback) ─┘  EJECTED = flag present: ignored on add/change, never promoted,
                                                                   cleared by cinemate mount_drive() success or by udev remove
```

### Signals and numbers to carry over
- Yank errno set `{EIO, ENOENT, ENODEV, ENOTCONN, ESTALE}`; test on the **mount root** (statvfs) — errors on paths *inside* the volume are not loss; ENOENT with the root still a mountpoint is not loss.
- Pollers: 1 s mount/space resync with udev wake-up; 3 s root statvfs; 0.5 s NVMe `/sys/block/<dev>/device/state == dead`; 0.05 s CFE latch I2C `0x34` bit0 (insert latch) / bit1 (eject); promotion wait ≤ 2 s; mount cooldown 30 s cleared on removal; `umount -l` retry 20 × 0.2 s; blkid settle 5 × 0.5 s.
- Redis-equivalent state: `is_mounted`, `storage_type`, `storage_filesystem`, `storage_recorder_profile`, `space_left`, `write_speed_to_drive`, `fsck_status`, `memory_alert`, `drop_frame`/`drop_frame_during_last_take`, `writeFailures` per frame.
- Watchdog thresholds: RAM frame buffer ≥ 90 % of pool, system RAM ≥ 80 %, 4 Hz; cinepi-raw pool-full margin `+2` buffers.

### Ordering Cinemate actually does (and what it omits)
1. Detect (udev remove / statvfs errno).
2. Lazy-unmount immediately and non-blockingly (storage-automount `Popen umount -l`; ssd_monitor `sudo umount -l` loop). **Writers are not stopped first**: cinepi-raw keeps encoding and each frame becomes a counted write failure; files are not closed deliberately — the kernel detaches the mount lazily when the last fd closes.
3. Publish `is_mounted=0`/storage none → GUI storage box disappears, minutes-left hidden; live DROP from `writeFailures`.
4. Promote a standby (`mount --move`) so the *next* take has a target.
5. Re-insert → automount → `mount_event` → fps-max refresh, storage-profile restart of cinepi-raw (deferred while recording), pre-roll warm-up, fsck once.
What the known T18 plan adds and Cinemate lacks: an explicit "stop writers → close files → unmount → UI" sequence on loss. In Cinemate the take is **not** stopped by media loss; it ends by operator, 90 %/80 % watchdog, or pool exhaustion.

### Pitfalls found in source (port must avoid)
1. **Mount gate swallows the stop edge.** cinepi-raw `triggerRec()` returns 0 while `!disk_mounted()` (`cinepi_controller.hpp:212-215`). The Redis `is_recording` handler already flips the shared `is_recording_` flag and sets `trigger_ = -1` (`cinepi_controller.cpp:781-793`; `CinePIController : public CinePIState`, `cinepi_controller.hpp:39`, flag at `cinepi_state.hpp:85`), so encoding does stop on the next frame (`cinepi_raw.cpp:440`), but the stop-edge side effects — `clip_number_++`, `folderOpen=false` (`:236-244`), `sound.record_stop()` (`cinepi_raw.cpp:430-433`) — run only when the trigger is next consumed, i.e. after a drive is mounted again. PROBABLE runtime effect: audio keeps "recording", clip number does not advance until re-mount.
2. **Substring mount test.** `is_mounted()` uses `strstr(line, "/media/RAW")` over `/proc/mounts` (`utils.cpp:22`), so a standby at `/media/RAW1` keeps `disk_mounted()` true after the active drive is gone. PROBABLE false positive.
3. **Promotion mid-take does not re-create the clip folder**: after `mount --move`, `/media/RAW/<folder>/` does not exist on the promoted drive; every `open()` fails until the next record edge (`dng_encoder.cpp:2352`, `:2379-2385`). "recording can continue" (commit 3259da7) means the next take. PROBABLE.
4. **Internal stop is invisible to the controller**: cinepi-raw's pool-exhaustion `setRecording(false)` (`cinepi_raw.cpp:449`) does not publish `is_recording=0` (`cinepi_state.hpp:67-69` is a plain setter); cinemate relies on its own 90 % watchdog.
5. **Post-take verdict blind after a yank**: folder scan returns `[]` when unmounted → RAM-counter fallback (`redis_listener.py:1731-1735`); and a short-written DNG with size > 0 counts as present (`:1618`). A port should record `writeFailures` per take as the authoritative loss figure and size-check files.
6. **Two components lazy-unmount the same path concurrently** (root service and `sudo umount -l` from cinemate); idempotent but worth a single owner.
7. **No `unmount_event` consumer** — the hook exists but nothing stops or marks the take. The port should wire loss → stop writers.
8. **Deliberate unmount vs automount race** needs an ownership token (flag file) written *before* unmounting, cleared on successful remount or physical removal, and honoured by the automounter on add/change and promotion.
9. **Blocking syscalls on dead media**: `os.path.ismount`, directory scans, `umount` and `statvfs` on bad SD mounts can block 30 s+ (`storage-automount.py:527`, `:530-531`, `:839-843`, `:1022-1023`); keep detection paths free of them (read `/proc/self/mountinfo`, use `Popen` for umount, string-only path checks).
10. **Dirty NTFS after a hotswap** produces EIO on one clip dir; treat per-path errors as local, memoise and skip them (`ssd_monitor.py:117-123`, `:748-750`, `:1324-1333`).
11. **Startup/ordering**: eject-flag dir created by the root service `Before=` the app; `/run` tmpfs clears stale flags on reboot.
12. **Record-start gate bug**: `and self.ssd_monitor.get_space_left` tests a bound method, always truthy (`cinepi_controller.py:2352`) — the intended space check is a no-op.

---

## UNKNOWN / not established
- Actual errno sequence seen by cinepi-raw's `open()`/`write()` on a yanked USB vs NVMe device (ENOENT after lazy unmount vs EIO/ENODEV before) — no hardware run or log in the repos.
- Whether cinemate's 90 % watchdog or cinepi-raw's `+2` pool-full margin trips first on a hung device (depends on `bufferSize` semantics; `dng_encoder.hpp:194`, comment `:236`).
- WAV/audio writer behaviour on yank.
- No handbook episode records an actual pull during a take; all yank behaviour above is from code and commit messages (3259da7 explicitly says "Live Pi verification pending").
- The T18 tutorial text was not available; the state names mounted/alive/lost/ejected above are my mapping, not Cinemate's.

---

## Verification

Adversarial verifier pass, 2026-10-26. Method: every cited line opened with `sed -n` / `grep -n` on the read-only checkouts at the stated commits (cinemate `d6cc93e`, cinepi-raw `63a08d5`, cinemate-handbook `c99ff77`); commit bodies read with `git show -s`; nothing run on hardware; no repository modified. Verdicts: CONFIRMED (line and content exact, label honest), CORRECTED (claim stands, citation or wording fixed), REFUTED, UNVERIFIABLE. Line-number corrections below are from `grep -n` anchors, not hand counts.

### Per-finding verdicts

| # | Finding | Verdict | What the source shows |
|---|---|---|---|
| 1 | Journal detection is dead code | **CORRECTED** (lines) | The commented-out thread block is `cinemate/src/module/ssd_monitor.py:141-146@d6cc93e` (header comment :141, `# self._jthread = threading.Thread(` :142, `.start()` :145, log :146), not :139-144 (:139 closes the live `_thread`, :140 is blank). `stop()` docstring :154-163 says so at :157-159. `_journal_loop` :1362-1431 exact. Claim stands. |
| 2 | Shared YANK_ERRNOS set | **CONFIRMED** | `ssd_monitor.py:47-53` and `services/storage-automount/storage-automount.py:97-103`: identical five-member sets `{EIO, ENOENT, ENODEV, getattr ENOTCONN, getattr ESTALE}`. |
| 3 | storage-automount detection paths all lazy-unmount and promote | **CORRECTED** (one over-generalisation) | Every line exact: udev remove `:913-919`; `_sanity_watchdog` `:835-864` (`time.sleep(3)` :864, `_safety_net_promote()` :862); `_nvme_watchdog` `:813-833` (`state == "dead"` :825, `time.sleep(0.5)` :833); `_cfe_hat_worker` `:925-1105` (REMOVED :1001, `time.sleep(0.05)` :1105); `_unmount` Popen `:528`; `_handle_raw_gone` `:759-769`. But the CFE **eject-button** path `:1091-1104` lazy-unmounts every mount, unregisters every pool member, sets `_active_raw = None` and powers PCIe down **without** promoting (deliberate eject). Latch-open `:1001-1021`, udev remove, NVMe dead and statvfs do promote via `_handle_raw_gone`. |
| 4 | SSDMonitor 1 s resync, statvfs throttle, funnel, 20 x 0.2 s lazy unmount | **CONFIRMED** | ctor defaults `:95-100`; `monitor.poll(self._poll_int)` `:308`; `os.path.ismount` `:323`; throttle `:782-783`; `os.statvfs` `:786`; "statvfs failed" `:807` -> `_handle_storage_error` `:808`; `_force_lazy_unmount` `:549-563` (`retries: int = 20` :549, `time.sleep(0.2)` :562); `main.py:708` constructs with defaults. |
| 5 | unmount_event has no subscriber; Redis none/0; LED off | **CONFIRMED** | `grep -rn unmount_event src/` -> `ssd_monitor.py:133` (creation) and `:431` (emit) only. `mount_event.subscribe` at `cinepi_controller.py:239` and `storage_preroll.py:59`. `_handle_unmount` `:391-432`: keys `:396-405`, `smbus.SMBus(1).write_byte(0x34, 0x00)` `:407-411`, emit `:431`. |
| 6 | 90 % buffer / 80 % RAM / 4 Hz watchdog | **CONFIRMED** | `RAM_LIMIT_PERCENT = 80` `cinepi_controller.py:357`, `BUFFER_LIMIT_PERCENT = 90` `:361`; `_recording_worker` `:4279-4308` (buffer check :4290-4296, RAM :4299-4304, `time.sleep(0.25)` :4306); `_auto_stop_recording` `:4310-4327` (memory_alert :4321, is_recording 0 :4325). |
| 7 | Disk worker counts open/short-write/close as write_failures_, never stops/unlinks | **CONFIRMED** | `cinepi-raw/cinepi/dng_encoder.cpp:2352` open, `:2360` write, `:2363-2368` short-write count, `:2374-2378` close-error count only when `write_ok`, `:2380-2385` open-fail count, `:2389` in-flight release, `:2392-2398` buffer + permit release. `grep unlink\|remove\|truncate` over the file: no hits. `writeFailures` published `cinepi_controller.cpp:643`; reset `dng_encoder.hpp:142`; comment `:222-231`. Nit: the alloc-fail in-flight decrement is `:2187`, not :2188. |
| 8 | No TC gap for write loss; live tier -> purple flash / DROP box, 0.5 s timer | **CONFIRMED** | `if (raw_elapsed >= 2) dropped_frames_ += raw_elapsed - 1` `dng_encoder.cpp:2134-2135`; `redis_listener.py:873-882` ingest; `:1080-1098` warning, `DROP_FRAME` set `:1092`, `threading.Timer(0.5, ...)` `:1097`; `simple_gui.py:2151-2153` purple + inverse; DROP box `:1658-1666`, `:1831-1839`, gated on `drop_frame_latched` = live pulse OR `drop_frame_during_last_take` (`:1086-1089`), so it does show during the live pulse. |
| 9 | Post-take verdict skips only st_size <= 0; RAM-counter fallback when drive gone | **CORRECTED** (helper name) | The `st.st_size <= 0` skip is in `_scan_dngs_once` (`redis_listener.py:1618`), which `_stable_dng_count` (`:1636-1657`) calls; the reader attributed it to `_stable_dng_count`. Rest exact: `:1672` folder fetch; `ssd_monitor.py:1271-1273` returns `[]` when unmounted (log :1272); "falling back to RAM counter" `:1733`, `recorded_frames_total = int(self.framecount or 0)` `:1734`; `write_failures_this_take = max(...)` `:1899-1902`; verdict `:1953-1961`; low-count hint `:2009-2012`; `drop_frame_during_last_take` only on shortfall `:1904-1913`. |
| 10 | Eject-intent protocol | **CORRECTED** (one line) | `not _is_eject_flagged(d)` is `storage-automount.py:733` (comment :731-732). All else exact: `ssd_monitor.py:55-72`; `_set_eject_intent()` `:949` before `sync` `:952` and `umount` `:960`; `_clear_eject_intent(raw_dev)` only on success `:1002-1007`; `storage-automount.py:54-73`; `_init_eject_dir` `:541-558` (chown 1000:1000, chmod 0755) called `:1219`, tmpfs comment `:1217-1218`; `_clear_eject_flags_for` `:587-603`; udev skip `:886-888`; `_add_raw` skip `:742-748`; `.service:5 Before=cinemate-autostart.service`. Commit `f01b6cd` body line 4 "polled every second for ten seconds, never once read as unmounted" and refs F-160 / B9.1 confirmed. |
| 11 | False-positive guards (inside-mount, ENOENT+ismount, memoised bad dirs) | **CORRECTED** (lines) | `_unreadable_dirs` is declared `ssd_monitor.py:125` with comment `:120-124` (not :117-123); "Skipping unreadable recording directory" is `:1335-1336` inside the rglob except-block `:1326-1338` (not :1302-1333); "Genuine storage loss (root-level failure)" comment is `:1328`. `_path_is_inside_mount` `:716-729`, comment `:740-747`, checks `:748-750` and `:756`, clear-on-unmount `:394` exact. Commit `58fc7c2` body lines 6-7 "healthy drive. The automounter immediately remounted it, re-hit the same directory, and looped." confirmed. |
| 12 | Record gate is is_mounted only; no fsck gate; read-only fsck 24 h | **CONFIRMED** | `if self.ssd_monitor.is_mounted == True and self.ssd_monitor.get_space_left:` `cinepi_controller.py:2352`; `get_space_left` is a method `ssd_monitor.py:1353-1355` -> bound-method operand, always truthy; "No disk." `:2364`; flush gate `:2346-2349`, `_buffered_frames_flushing` `:2217-2224`; fsck cmd `["sudo","nice","-n","19","ionice","-c3","fsck","-n",devnode]` `:850-851`, skip while recording `:831-832`, NTFS skip `:843-848`, 24 h `:863`; `docs/redis-keys.md:92` "cinepi-raw never reads it". |
| 13 | Re-insert path and numbers | **CORRECTED** (lines) | `_add_raw` `:741-756`; `_handle_raw_gone` `:759-769`, cooldown clear `:765` (reader :764); `_safety_net_promote` `:788-807`. Numbers exact: `retries: int = 5, delay: float = 0.5` `:212`; cooldown `< 30` `:424`, `30 - ...` `:428`; `_failed_devices[dev] = time.time()` `:509`; `_auto_repair` `:384-398` (`e2fsck -f -p` rc in (0,1,2), `ntfsfix`, `fsck.exfat -a`); `waited < 2.0` / `time.sleep(0.1)` `:673-675`; `mount --move` `:685`; FUSE fallback `:703-708`; `force=True` `:711`; CFE `retries=3, delay=0.3` `:1066`, `:1078`; `time.sleep(0.5)` after PCIe bind `:965`, `time.sleep(0.8)` `:1040`. `ssd_monitor.py:329-343` device-changed re-sync; `_handle_mount` `:345-389` (bails on failed forced space read `:354-356`, emit `:380-385`, `_next_fsck_ts = 0` `:389`); `cinepi_controller.py:2144-2215`; `storage_preroll.py:173-183`. |
| 14 | triggerRec mount gate defers the stop edge | **CONFIRMED** (mechanism; 'probable' honest for runtime effect) | `cinepi_controller.hpp:211-215` (`if (!disk_mounted(options_)) return 0;` :214-215); stop-edge side effects `:236-244`; Redis handler `cinepi_controller.cpp:781-793` (`is_recording_ = level` :792); `class CinePIController : public CinePIState` `:39`; `bool is_recording_` `cinepi_state.hpp:85`; main loop `controller.isRecording()` `cinepi_raw.cpp:437`, `nowRecording && controller.folderOpen` `:440`, `sound.record_stop()` `:433`. See A4: the edge can be lost outright. |
| 15 | strstr mount test; promotion does not re-create clip folder | **CONFIRMED** (mechanism) | `strstr(line, mount_point)` `utils.cpp:22` in `is_mounted` `:9-32`; `disk_mounted` `:34-36`; `create_clip_folder` `:93-106` is called only on the start edge (`cinepi_raw.cpp:425`) and the resolution-reconfigure resume (`:367`); the disk worker builds the path from `options_->folder` (`dng_encoder.cpp:2334-2341`). "recording can continue" is in commit `3259da7`'s body (lines 9-10). |
| 16 | cinepi-raw pool-exhaustion stop is unpublished; encode workers block on permit | **CONFIRMED** (ordering settled as PROBABLE in A2) | `cinepi_raw.cpp:442-452` (`buffer_full()` :442, `!justStarted` exemption :447, `controller.setRecording(false)` :449, warn :451); `ram_buffers_ + 2 >= max_ram_buffers_` `dng_encoder.hpp:261`; plain setter `cinepi_state.hpp:67-69`; `ram_cv_.wait(... ram_buffers_ < max_ram_buffers_)` `dng_encoder.cpp:2174`; handbook `hardware-log.md:963-965` "the RAM pool (173 frames ~ 2941 MB) fills". |
| 17 | Blocking-call avoidance comments | **CONFIRMED** | `storage-automount.py:527-528`, `:530-531`, `:839-841`, `:1022-1023`, `:631-642` all exact. |
| 18 | Handbook has no pulled-media episode; yank lessons live in commits | **CONFIRMED** | 84 `## ` entries / 3906 lines. Grep `yank|pulled|hotswap|hot-swap|remount|unmount|eject|ntfsfix|fsck|stale mount|EIO` over `hardware-log.md` and `open-threads.md`: only "pulled to the Mac"-type hits, the 2026-08-25 blkid entry (`:149-175`), the format-drive checks and one unrelated `EREMOTEIO` i2c row (`:3279`). Entry headers confirmed `:149` (08-25), `:248` (08-26), `:945` (08-27/28), `:1179` (09-01), `:1610` (09-05), `:3081` (09-15); "`/media/RAW` is not an archive" `:2313`; `architecture/cinemate.md:149-175`, `what-the-pi-taught-us.md:57-66`, `changelog.md:84`, `:122` exact. git: `-S YANK_ERRNOS` -> `2a49fa1 2026-05-17`; `-S _handle_storage_error` -> `8f49468 2026-05-11`; `-S EJECT_FLAG_DIR` -> `f01b6cd 2026-08-26`; `58fc7c2 2026-06-10 01:26`; `3259da7 2026-06-09 20:39` (body: "_active_raw is now only set on a real successful mount", "recognised even after reconnect", "no sda/sdaa", "20-assertion local simulation ... Live Pi verification pending"); `5fbef52 2026-06-10 00:54:43` and cinepi-raw `8b705c8 2026-06-10 00:54:43`. |

Prose-only citation slips (not in the JSON findings): the component table's `.service:5-13` does not cover `Nice=-10`, which is `.service:30`; the `umount` run in `unmount_drive()` is `:960` (the reader's :959 is the `try:`).

Recomputed numbers: all constants quoted by the reader (1.0 s / 1.0 s / 0.1 GB; 20 x 0.2 s = 4 s; 3 s; 0.5 s; 0.05 s; 2.0 s in 0.1 s steps; 30 s; 5 x 0.5 s; 3 x 0.3 s; 0.5 s + 0.8 s; 90 % / 80 % / 0.25 s; 0.5 s drop timer; 24 h; RAM pool 90 % of free, `dng_encoder.cpp:1079-1082`) match the source.

### Added (settled from source during verification; nothing observed on hardware)

**A1. Which SSDMonitor branch fires first on a dead mount — PROBABLE.** CPython's `posixpath.ismount` (`/usr/lib/python3.13/posixpath.py:190-199` on this host) returns False when `os.lstat(path)` raises OSError. So (i) once storage-automount's `umount -l` has completed, or (ii) when `lstat(/media/RAW)` itself fails with EIO/ENODEV, `_check_mount_status` (`ssd_monitor.py:323-328`) takes the `not mounted_now and self._is_mounted` branch and calls `_handle_unmount()` directly, **without** `_force_lazy_unmount`. Only when the mountpoint still stats OK but `statvfs` fails does the funnel run (`:786` -> `:808` -> `:766` -> `:767`). Both are reached within one poll (<= 1 s, or immediately on the block udev event that wakes `monitor.poll` at `:308`). Caveat: `lstat` on some dead media blocks instead of failing (the hazard `storage-automount.py:1022-1023` documents), in which case the SSDMonitor thread stalls. The hardware errno sequence remains UNKNOWN.

**A2. 90 % watchdog vs cinepi-raw +2 margin — PROBABLE, pool-size dependent.** Inputs: Redis `buffer_size` = `maxRamBuffers()` (`cinepi_controller.cpp:694-696`); Redis `buffer` = max(`bufferSize`, `bufferSizeMax`) where `bufferSize` = `disk_buffer_.size()` (`dng_encoder.hpp:194-196`), set by `redis_listener.py:930-940` per delivered frame, i.e. the **disk-side backlog only**. cinemate trips at disk backlog >= 0.9 x pool (`cinepi_controller.py:4267-4296`, 4 Hz). cinepi-raw trips at `ram_buffers_ + 2 >= pool` (`dng_encoder.hpp:261`), where `ram_buffers_` counts frames holding a permit from before encode (`dng_encoder.cpp:2174-2175`) to after write (`:2394-2398`), so `ram_buffers_` ~ disk backlog + frames mid-encode (N_enc <= encode-worker count). cinemate fires first iff 0.9 x pool < pool - 2 - N_enc, i.e. pool > 20 + 10 x N_enc. With the handbook's 173-frame pool (`hardware-log.md:964`) cinemate's threshold (156 disk-backlog frames) precedes cinepi-raw's (~169-171) by ~13-15 frames ~ 0.6-0.7 s at 21 fps, well above the 0.25 s poll: cinemate stops first on a hung 4K drive. With a small pool (roughly < 40-60 frames, e.g. little free RAM) cinepi-raw's internal stop fires first and, being a plain `setRecording(false)` (`cinepi_state.hpp:67-69`), is invisible to Redis; cinemate's buffer watchdog then never reaches 90 % (encoding stopped), leaving the 80 % system-RAM backstop (probably tripped, since the pool is 90 % of free RAM) or the operator to end the take.

**A3. WAV/audio writer on media loss — PROBABLE.** The WAV is written by an external capture helper launched with `popen2` (`cinepi-raw/cinepi/cinepi_sound.cpp:948-949`) into `<mediaDest>/<folder>/<folder>.wav` (`:835-837`) after `create_directories` (`:837`). cinepi-raw never sees that process's write errors and does not count them; it drains the helper's stdout until the child exits (`:1201-1204`) and on a failed launch logs "continuing take without audio" (`:953`). The WAV-size probe gives up after ~1.5 s if the file never becomes non-empty (`:228-238`, `absentGraceAttempts = 15`). After a yank the helper dies or stalls on its own EIO/ENOENT; the DNG `writeFailures` tier is the only live signal, and the WAV is absent or truncated with no telemetry.

**A4. The deferred stop edge can be lost, not just deferred (extends finding 14) — CONFIRMED mechanism.** `cinepi_controller.cpp:786-789` overwrites `trigger_` on every level change: a `1` arriving while `disk_mounted()` is false replaces the pending `-1`, so the previous take never gets `clip_number_++` / `folderOpen = false` / `sound.record_stop()` (`cinepi_controller.hpp:238-243`, `cinepi_raw.cpp:432-433`). The next start edge (consumed once a drive is mounted) still creates a fresh folder because the name carries a timestamp and sub-second frame (`utils.cpp:81-84`, `CINEPI_%s_F%02d_C%05d_%s`), but the clip counter repeats and `sound.record_start()` runs without a preceding `record_stop()`. Runtime effect not observed.

**A5. Nuance for finding 3.** The CFE eject-button path (`storage-automount.py:1091-1104`) is a deliberate eject and does not promote; only latch-open (`:1001-1021`), udev remove (`:913-919`), NVMe dead (`:825-829`) and statvfs (`:846-851`) promote via `_handle_raw_gone`. Port implication unchanged: deliberate eject is not loss.

### Still UNKNOWN after verification
- Actual errno sequence at cinepi-raw's `open()`/`write()` for USB vs NVMe pulls (no hardware log in any repo).
- Incidence of present-but-short DNGs after a yank (mechanism confirmed at `dng_encoder.cpp:2363-2368`; no counts anywhere).
- T18 tutorial text; the mounted/alive/lost/ejected naming remains the reader's mapping onto Cinemate's two-process behaviour.

### Net effect on "What a port needs"
No item refuted. Two sharpenings: (1) from A1, treat "mountpoint stat fails" and "root statvfs fails" as two distinct loss signals and never block on either; (2) from A2/A4, the port's own stop must be published (unlike cinepi-raw's internal `setRecording(false)`), must not sit behind a media-mounted gate, and must not be overwritable by a later start before it is consumed.
