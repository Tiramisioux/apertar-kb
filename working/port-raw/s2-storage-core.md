# s2-storage-core — Storage media optimisation, Apertar-Core side at f60e301

Reader: source investigation for porting Cinemate's per-media raw-writing optimisation to Apertar-Core.
Repo read: apertar-core, cited `apertar-core/<path>:<line>@f60e301`. The checkout HEAD is `2a6f114`, four commits
past f60e301; every f60e301 line below was read from `git show f60e301:<path>` (ApertarCoreApp.cpp differs from
HEAD only by three inserted lines after :199 and :7894, so its numbers hold at HEAD too; CameraController.cpp and
CdngEncoder.cpp do not). HEAD-only facts are cited `@2a6f114` and flagged. KB pages are cited by path:line; nothing
cited from the KB was verified on the Pi by me. Nothing was run on a camera.

Status legend: CONFIRMED = line opened and read; PROBABLE = inferred, reason given; UNKNOWN = not in the sources read.

---

## 0. One paragraph (CONFIRMED)

Core learns about its media by text: `/proc/mounts` for "is `/media/RAW` mounted and by which device", `lsblk -no LABEL`
for the volume label, and a label/devname lookup table for a display string ("CFExpress Type B" / "NVMe M.2 SSD" /
"External USB"). An `lsblk -P` scan supplies a mountable-drive list with `FSTYPE`, used only to build `mount -t`. The
recorder (`DngRecordingQueue`) is tuned by recording *format* (workers, queue depth, nice, tile rows) via constants and
`APERTAR_*` env vars; nothing in the recorder, the buffer-count choice or the service files reads the filesystem,
transport or any drive property. A fio/dd speed test exists but its result feeds only two display strings. Time-left is a
static bytes-per-pixel model. Boot-time mounting of `/media/RAW` is done outside this repo (a `media-RAW.service`
oneshot and the `apertar-cfe-automounter` daemon, both from the image / Apertar-UI, per the KB).

---

## 1. What Core knows about the mounted media, where computed, where exposed

### 1a. Mount state and device (CONFIRMED)
- `isMountedPath(mountPath)` reads `/proc/mounts` as `device mountedAt type options`, compares the decoded mount point
  with the wanted path; returns bool only (apertar-core/src/ApertarCoreApp.cpp:2023-2038@f60e301).
- `mountedDeviceForPath` does the same scan and returns the decoded device column (:2040-2055). The `type` (filesystem)
  and `options` columns are read into locals and discarded in both functions (:2029-2030, :2046-2047). So Core parses
  the filesystem type and mount options of the live mount every poll and throws them away.
- Media root comes from `--media` (default `/media/RAW`), passed by `scripts/start-apertar-core.sh:5,21@f60e301`
  (`MEDIA_ROOT=${APERTAR_MEDIA_ROOT:-/media/RAW}`); README: "Default: `/media/RAW`" (apertar-core/README.md:253@f60e301).

### 1b. Volume label and the media-type label (CONFIRMED)
- `volumeLabelForDevicePath`: `lsblk -no LABEL <dev>` (:2062-2063); fallback scans `/dev/disk/by-label` for a symlink
  resolving to the device (:2075-2089) (:2057-2092).
- `normalizedVolumeLabel` = upper-cased, trimmed (:1975-1990).
- `mediaTypeLabelForDeviceAndVolumeLabel(device, label)` (:2006-2021): `CFE-RAW` or `RAW` -> "CFExpress Type B";
  `SSD-RAW` or `NVME-RAW` -> "NVMe M.2 SSD"; `USB-RAW` -> "External USB"; else device prefix `/dev/sd` -> "External USB",
  `/dev/nvme` -> "NVMe M.2 SSD"; else `mediaTypeLabelForVolumeLabel` (:1992-2004), whose final fallback is also
  "CFExpress Type B" (:2003). Consequence: an unlabelled SD card (`/dev/mmcblk*`) or any unknown device is shown as
  CFExpress Type B. There is no hardware probe behind this label: no sysfs transport, no udev, no I2C hat check
  (the I2C code exists only in the eject/re-insert Python helper, §3d).
- Exposed as `capture.storage` in `/api/state` (:7973), computed at :7735-7737 ("No Media Mounted" when unmounted).

### 1c. Drive scan (`media_drives`) (CONFIRMED)
- `scanMountableMediaDrives(mountPath, forceRefresh)` (:2275-2399): runs
  `lsblk -P -b -o NAME,PATH,TYPE,SIZE,FSTYPE,LABEL,MODEL,TRAN,RM,RO,MOUNTPOINT,PKNAME` (:2293-2294), result cached 3 s
  (:2286-2290). Filters: skip devices mounted at `/` or `/boot*` and their parents (:2263-2267, :2315-2328); skip
  `RO=1` (:2345); keep `part`, or `disk` with a filesystem (:2347); skip empty `FSTYPE` (:2349); skip anything mounted
  somewhere other than the media root (:2353). The mounted media itself therefore appears in the list with
  `mount_point == /media/RAW`.
- `MediaDriveCandidate` fields: devicePath, displayName (`label|model|path • path • FSTYPE • size`), label, model,
  filesystemType, sizeText, mountPoint (:2236-2245, :2375-2387). `TRAN` and `RM` are requested from lsblk but never
  read (grep for `"TRAN"`/`"RM"` in the file: no hits; only MODEL/LABEL/PATH/TYPE/FSTYPE/SIZE/RO/MOUNTPOINT/PKNAME).
- JSON `media_drives[]`: device_path, display_name, label, model, filesystem_type, size_text, mount_point (:2401-2420),
  emitted at :7938. So the filesystem of the mounted device *is* reachable from `/api/state`, but only inside this
  array, and no Core code consumes it except `mount -t` (§3a).

### 1d. Space, write-pending, drop/health (CONFIRMED)
- Free/total: `std::filesystem::space(nearestExistingPath(mediaRoot))` when mounted (:7792-7808) ->
  `media_free_bytes`, `media_total_bytes`, `media_used_percent` (:7934-7936).
- `media_label` is the mount path string or "Mount /media/RAW to manage media" (:7937). `media_mounted` (:7914).
- `media_writes_pending` / `media_write_revision` (:7862-7863) are *still-photo* write-behind state:
  `CameraSession::mediaWriteStatus()` returns `{hasPendingPhotoCaptures(), mediaWriteRevision_}`
  (apertar-core/src/camera/CameraController.cpp:5744-5748@f60e301). They say nothing about clip writing.
- `recording_error`, `recording_has_dropped_frames` (:7853-7854); `photo_write_error` (:7861).
- The socket `get_state` reply (:9253-9274) carries recording_error, recording_has_dropped_frames,
  media_writes_pending/revision and settings, but **no** media_mounted/space/label; those exist only in `/api/state`
  (`buildWebStateJson`) and in the `mount_media` reply (:10671-10672).

### 1e. Speed-test fields (CONFIRMED)
`write_speed_running`, `write_speed_result_text`, `write_speed_detail_text`, `write_speed_error` (:7947-7964), from a
mutex-protected snapshot (:7756-7772). Texts: result "No Media" / "Testing..." / "Test Failed" / "<n> MB/s"
(0 decimals >= 100, else 1) / "Not Tested" (:3878-3896); detail "Mount /media/RAW to run a media speed test." /
"Running a <MiB> MB direct fio write test (QD32)..." or "... sequential write test..." / error / "Measured with a <MiB>
MB ..." / "Runs a temporary direct write test and removes the file afterwards." (:3898-3929). Note the text prints MiB
as "MB" (:3911).

### 1f. What Core does *not* know (CONFIRMED by absence)
Filesystem as a first-class value (discarded at :2029/:2046), mount options (discarded at :2030/:2047), transport
(TRAN discarded), USB-vs-PCIe ancestry, CFE-hat presence for labelling, logical block size, queue scheduler, drive
serial/identity for remembering a test result, O_DIRECT support. No per-device persistence of anything.

---

## 2. The media speed test (CONFIRMED)

- Command `run_media_speed_test` -> `startMediaSpeedTest` (:10683-10688, :8973-9026). Refused while a test runs
  (:8977-8981), when not mounted ("No media is currently mounted." :8986-8991), or with < 96 MiB free (:8999-9003).
- Size by free MiB: 64 MiB default; >= 160 -> 128; >= 320 -> 256; >= 640 -> 512; >= 1152 -> 1024 (:9006-9014).
  Runs on its own thread (:9024).
- `runMediaSpeedTest` (:9028-9099): temp file `<mediaRoot>/.apertar_write_speed_test.bin` (:9030), removed first.
  fio invocation: `fio --name=write_test --filename=<tmp> --size=<N>M --bs=1M --rw=write --direct=1 --numjobs=1
  --iodepth=32` (:9037-9044). If fio exits non-zero (incl. not installed): dd fallback
  `dd if=/dev/zero of=<tmp> bs=8M count=<N/8> conv=fdatasync status=none` (:9046-9051).
- Parsing: fio `WRITE: bw=... (X MB/s)` regex (:9064-9069), else `bw=X MiB/s` × 1.048576 (:9072-9079), else
  `testMiB / elapsed wall seconds` (:9081-9084) — the wall clock includes process start-up and is the only path dd ever
  takes (the regexes are fio-only), so the dd figure is MiB/s labelled "MB/s".
- Stored in memory only: `mediaSpeedLastUsedFio_`, `mediaSpeedLastBytes_`, `mediaSpeedLastWriteSpeedMBps_` (0 on
  failure), `mediaSpeedError_` (:9092-9098). Not persisted, not keyed by device; survives an eject (only the display
  text switches to "No Media" at :3883-3884). Temp file removed, `sync` (:9089-9090).
- Readers of the result: the two display texts (:7949-7962) and `get_media_test_state` (`running`, `mbps`, `bytes`,
  `used_fio`, `error`; :10675-10682). Grep of `mediaSpeedLastWriteSpeedMBps_`: only :7770, :9097, :10678. It feeds
  **nothing else** — not time-left, not an fps cap, not the recorder.
- Gates: media actions refused while recording / sound recording / timelapse / pending writes / test (:9114-9123);
  `record_start`, `capture_photo`, `timelapse_start`, `enter_standby` refused during a test (:9124-9126).
- PROBABLE (fio semantics, not from the repo): fio's default ioengine on Linux is `psync`; `--iodepth` has no effect on
  synchronous engines, so the "QD32" test is effectively QD1 direct 1 MiB writes — close to what a single buffered-or-
  direct writer thread does, which is arguably the right probe, but the label overstates it.

### 2b. Time-left model (CONFIRMED)
- `estimatedRawBytesPerSecond(settings)` (:4752-4772): ProRes nominal 45e6 / 102e6 / 220e6 / 147e6 bit/s (Proxy / LT / HQ
  / 422) × pixels/(1920·1080) × fps/30 × 1.05 (:4754-4760); H.264 constant 25 Mbit/s = 3.125 MB/s (:4761-4764); raw
  formats: `pixels × 1.5 bytes × max(1,fps) × 1.08` (cDNG) or `× 1.03` (MLV) (:4766-4771). Bit depth (8/10/12/16),
  lossless compression, the lossy 3:1/5:1 ratio and Clear HDR 16-bit are all ignored: 16-bit unpacked is 2 B/px (model
  25 % low), lossless 12-bit is typically well under 1.5 B/px (model high).
- `record_time_left_minutes = free / bps / 60` (:7810-7817); `time_left_percent = minutes/120 × 100` clamped
  (:7826-7828); `time_left_label` is the constant "Current format estimate" (:7942); `record_stills_left` from
  `estimatedStillFrameSizeMiB` (:7818-7824, :4774-4800 uses bits/8 per pixel × 1.08 for stills — the still model does
  honour bit depth, the clip model does not).

---

## 3. mount_media / format_media / eject, who mounts at boot, what runs as root

### 3a. `mount_media` (CONFIRMED)
- Handler :10663-10673 (`device_path` required) -> `mountMediaDeviceAtPath` (:3666-3717): refuses if the root is already
  mounted ("Eject the currently mounted media before mounting another drive." :3671-3675); device must start with `/dev/`
  (:3676-3680); filesystem type is taken from the lsblk scan entry for that device (:3681-3694).
- `mountDeviceAtMediaPath` (:3613-3656): `sudo -n mkdir -p <mount>` (:3618); ntfs -> `-t ntfs3 -o
  uid=1000,gid=1000,umask=0002` (:3625-3627) with fallback `sudo -n mount -t ntfs-3g -o <same>` (:3644-3648);
  exfat / vfat / fat32 / fat / msdos -> `-o uid=1000,gid=1000,umask=0002` (:3628-3630); ext4 and anything else ->
  `sudo -n mount -t <fs> <dev> <mount>` with **no options** (:3632-3637). No `noatime`, `nodiratime`, `commit=`,
  `dmask/fmask` anywhere. Error mapping to "needs sudo permission for mkdir and mount" / "not supported by this Pi
  image" (:3702-3715).

### 3b. `format_media` (CONFIRMED)
- Handler :10646-10654: `filesystem` parameter default `"exfat"` (:10647) -> `formatMediaAtPath` (:3772-3876).
- Offered: exfat, vfat (FAT32), ntfs; `ext4` explicitly refused ("Select exFAT, FAT32, or NTFS before formatting."
  :3777-3781; normaliser :2094-2111 knows ext4 but the formatter rejects it). Display names :2113-2125.
- Steps: `sync` (:3783); device from `/proc/mounts` (:3785); label = current label or `RAW`, sanitised per fs
  (vfat: alnum/space/-/_ upper-cased, 11 chars; exfat 15; ext4 16; ntfs 128; :2171-2196); unmount via
  `udisksctl unmount -b <dev> --no-user-interaction` then `umount <mount>` (:3795-3799); tool located among
  `/usr/sbin|/sbin|/usr/bin|/bin/mkfs.exfat`, `mkfs.vfat|mkdosfs`, `mkfs.ntfs|mkntfs` (:2141-2169).
- Commands: `sudo -n mkfs.exfat -n <label> <dev>` (:3819) — no `-c`, so default cluster size (same choice Cinemate makes
  for macOS compatibility, s1 §5); `sudo -n mkfs.vfat -F 32 -n <label> <dev>` (:3822); `sudo -n mkfs.ntfs -f -F -L
  <label> <dev>` (:3825). Then `sync`, `udevadm settle` (:3849-3850), remount via `mountFormattedDeviceAtPath` up to 10
  attempts with 350 ms sleeps (:3852-3861).

### 3c. `eject_media` (CONFIRMED, overlaps y2; listed for the root inventory)
`ejectMediaAtPath` (:3719-3770): `flushMediaPath` = `sync -f <mount>` (fallback `sync`) + `sudo -n blockdev
--flushbufs <dev>` (:3355-3364); `udisksctl unmount -b <dev> --no-user-interaction` (:3734-3736); non-NVMe:
`udisksctl power-off -b <parent>` (:3738-3742, parent via `parentDriveForDevice`); fallback `umount <mount>`
(:3745-3746); NVMe: `detachNvmeController` writes `1` to `/sys/bus/pci/devices/<pci>/remove` via `sudo -n sh -c`
(:3366-3387) and then starts the re-insert watcher (:3748-3752).

### 3d. The embedded Python NVMe re-insert watcher (CONFIRMED)
`startNvmeReinsertWatcherAtPath` (:3389-3611) launches `APERTAR_MEDIA_ROOT=<root> python3 -c '<script>' &` (:3603-3604).
Script: config from `$APERTAR_HARDWARE_CONFIG`, `/home/pi/apertar-hardware.conf`, `/boot/firmware/...`, `/boot/...`
(:3406-3420), sections `[cfexpress_hat] enabled/bus/address` and `[storage] mount_path/pcie_controller` (:3458-3472);
defaults I2C bus 10, addr 0x34, controller `1000110000.pcie` (:3400-3404). Insert state = I2C byte bit0, `0x69` ignored
(:3493-3504); waits for card present then absent then present again (:3582-3594); PCIe reset = unbind/bind
`brcm-pcie`, then `/sys/bus/pci/rescan` (:3564-3575); picks the highest `nvmeXnYpZ` partition (:3515-3534); fs via
`blkid -s TYPE -o value` (:3506-3513); mount: ntfs -> `mount -t ntfs3 -o uid=1000,gid=1000`, ext4 -> plain, exfat ->
`-o uid=1000,gid=1000`, **anything else (vfat!) -> not mounted** (:3545-3562). Privileged calls go through `sudo -n`
unless already root (:3477-3491). Differences from the C++ mount path: no `umask=0002`, no vfat, no ntfs-3g fallback.

### 3e. Who mounts `/media/RAW` at boot (PROBABLE — KB, not source I opened)
Core never mounts at start; its `start()` only records `mediaRoot_` (CameraController.cpp:7961-7964@f60e301) and
`CameraController::startRecording` does not check the mount or free space (:8699-8734 — only state, unsupported
settings, still-mode and pending-photo gates; the session reserves a clip folder with `create_directories`
:5878-5885, so with nothing mounted clips land on the SD card; README warns "An existing folder by itself does not
prove that an external drive is mounted" :246). Per the KB (Pi observation 2026-10-25): `media-RAW.service` =
`/etc/systemd/system/media-RAW.service`, a oneshot running `/usr/local/bin/mount-raw.sh` ("Mount RAW storage
(NVME-RAW or USB-RAW)"), **in no repo** (apertar-kb/architecture/overview.md:146, :104); `apertar-cfe-automounter`
(root, `/usr/local/libexec`, `After/Wants=media-RAW.service`) built from `Apertar-UI/src/CfeAutomounter.cpp`, mounts
via `mount(2)` — ntfs -> ntfs3, exfat/vfat with uid/gid 1000, ext4 (overview.md:15, :98, :145; ui.md:398-410;
build.md:124, :139). The Apertar-UI repo is not in this checkout, so the automounter's exact option strings are
UNKNOWN here; `mount-raw.sh`'s options are UNKNOWN (file not in any repo). The filesystem actually on the rig's
`/media/RAW` has never been recorded (working/clearhdr-compare-answer.md:57 "never established"; T22 asks for
`findmnt -no FSTYPE,OPTIONS /media/RAW`).

### 3f. What runs as root (CONFIRMED from Core source; sudoers PROBABLE)
Via `sudo -n` from the `apertar-core` process: `mkdir -p`, `mount` (ntfs3 / ntfs-3g / exfat / vfat / ext4), `mkfs.exfat`,
`mkfs.vfat`, `mkfs.ntfs`, `blockdev --flushbufs`, `sh -c 'echo 1 > /sys/bus/pci/devices/<pci>/remove'`; from the
Python helper: `blkid`, `mkdir`, `mount`, `sh -c 'echo <v> > /sys/bus/platform/drivers/brcm-pcie/{unbind,bind}'` and
`/sys/bus/pci/rescan`. Via polkit: `udisksctl unmount` / `power-off`. No sudoers file is in the Core repo
(KB: "Missing from the repo: no sudoers entry covers … `sudo -n mount`/`mkdir` … They must come from the image
(UNCONFIRMED)", apertar-kb/sources/research-2026-10-25/ui-structure-notes.md:595). Service tuning in the repo is only
`config/apertar-core-capture-priority.conf:1-3@f60e301` (`[Service] LimitNICE=-5`, "bounded, non-real-time boost").
No chrt/ionice/taskset, no sysctl, no udev rules in the repo (`config/` and `scripts/` contain only those two files).

---

## 4. Recorder tunables and defaults (CONFIRMED unless marked)

| Knob | Default | Range | Scope | Where |
|---|---|---|---|---|
| `kConfiguredBufferCount` | 4 | const | raw cDNG/MLV camera buffers | CameraController.cpp:1047@f60e301 |
| `kActiveRequestCount` | 3 | const | raw requests in flight | :1048, used :6796-6797 |
| `APERTAR_H264_CAMERA_BUFFERS` | 4 (hw H.264) / 6 (sw) | 3-12 | H.264 | :1148-1152 |
| `APERTAR_PRORES_CAMERA_BUFFERS` | 12 | 8-32 | ProRes | :1154-1158; chosen :6411-6413 |
| `APERTAR_CDNG_QUEUE_FRAMES` | 24 if (lossless cDNG or lossy DNG) and >= 4 threads, else 12 | 4-64 | all raw queue formats | :3434-3439 |
| `APERTAR_CDNG_WORKERS` | min(8, threads+1) = 5 on Pi 5 (>= 4 threads), else max(2,min(4,threads)) | 1-8 | lossless cDNG only | :3440-3444, :3451-3452 |
| `APERTAR_LOSSYDNG_WORKERS` | max(1,min(4,threads)) = 4 | 1-8 | lossy DNG only | :3445-3448, :3453-3454 |
| (no env) `normalWorkerCount` | max(2,min(4,threads)) = 4 | — | uncompressed cDNG | :3433, :3455 |
| (no env) MLV workers | 1 | — | MLV | :3449-3450 |
| `APERTAR_CDNG_WORKER_NICE` | 5 (lossy) / 0 (lossless) | 0-19 | lossless + lossy only; per worker thread `setpriority`; uncompressed/MLV never niced | :3806-3818 |
| `APERTAR_CDNG_TILE_ROWS` | 128 | 16-1024 | lossless tiles | CdngEncoder.cpp:52-67@f60e301 |
| `APERTAR_CDNG_PROFILE_DETAIL` | off | bool | lossless timing detail | CdngEncoder.cpp:69-77 |
| raw copy pool size | min(queueFrames, max(workers+2, 4)) | derived | pool of recycled raw copies; refuses buffers > 1.5× expected | CameraController.cpp:3992-3995, :3970-3990 |
| `APERTAR_RAW_CACHED_DMABUF` | true | bool | CPU-cached raw buffers for PiSP-compressed / Clear HDR | :6654-6658 |
| `APERTAR_PRORES_CACHED_DMABUF` | (read) | bool | ProRes | :6723 |
| `APERTAR_H264_*` | various | — | H.264 encoder: SIZE, KEEP_RAW_STREAM, SINGLE_STREAM, ENCODER, PRESET, TUNE, CRF, QP, BITRATE, MAXRATE, BUFSIZE, X264_PARAMS, BACKEND, THREADS, PIPE_BYTES, QUEUE_FRAMES | :2880, :2944, :2949, :4442-4576 |
| `APERTAR_SENSOR_PROBE` | true | bool | mode probe at start | :5536 |
| `LimitNICE=-5` | — | systemd | the only service-level knob | config/apertar-core-capture-priority.conf:3 |

HEAD-only additions (@2a6f114, not at f60e301): `APERTAR_RAW_CAMERA_BUFFERS` default 4, 8 in Clear HDR
(`kClearHdrBufferCount = 8`), range 3-16, and requests now follow the buffer count (CameraController.cpp:1057,
:1171-1175@2a6f114); raw pool pre-filled with 6 page-aligned buffers at session start (:6879); `APERTAR_RAW_COPY_WORKERS`
1-2, default 1 (:3507); `kRawCopyAlignment = 4096` (:3054); `APERTAR_CDNG_DIRECT_IO` default on
(CdngEncoder.cpp:467-475@2a6f114) with `O_DIRECT` open for uncompressed DNGs (:1803-1805), fallback to buffered on
`EINVAL` at open (:1807-1811) and at write (:1855-1860), `kDirectIoPage = 4096` (:465); DONTNEED only on the buffered
path (:1861-1862). Commit messages (d3c1b17, 6853891, 2f5a880) give the rationale: a 16.6 MB page-cache writeback burst
per DNG drops Clear HDR frames at the CFE; the copy moved off libcamera's completion thread.

- **Per-format: yes.** Workers, queue depth and nice all branch on `recordingFormat_`/`cdngCompression` (:3434-3455,
  :3811-3814). **Per-media: none.** `DngRecordingQueue` touches `mediaRoot` only to build the clip folder path
  (`allocateClipFolder` :3742-3770: `cDNG_`, `cDNG_3to1_`/`cDNG_5to1_`, `MLV_`, `H264_`, `ProRes_` prefixes); grep for
  `mediaRoot`/`FSTYPE`/`statvfs` inside the recorder finds nothing else.
- Write path at f60e301: uncompressed DNG `open(O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0644)` (CdngEncoder.cpp:1748-1753),
  `POSIX_FADV_SEQUENTIAL` (:1758), header + raw payload + padding + IFD through `writeAll` (:1770-1777),
  `POSIX_FADV_DONTNEED` (:1779), close, `unlink` on failure (:1786-1787), any failure throws `Failed to write DNG`
  (:1800-1801). Lossless opens its own fd (:1272-1273) and `pwrite`s the header last (:1760-1768). MLV: same open flags
  (MlvEncoder.cpp:964-968@f60e301), `POSIX_FADV_SEQUENTIAL` (:981), blocks via `writeAll`; **no DONTNEED call exists in
  MlvEncoder.cpp** (grep `fadvise`: only :981) — a correction to the brief's "MLV also DONTNEED".
- Clip log line (:3462-3483): `ApertarCore recording clip: <folder> format=<fmt> compression=<lossless|uncompressed|
  3:1|5:1|none>`; lossless adds ` worker_nice=<env, printed default 0 even though the applied default is 0 too>
  workers=<n> queue=<n> tile_rows=<n> encoder=quad_single_pass build=release|debug`; lossy adds ` workers= queue=
  encoder=quantized_sof3`; uncompressed cDNG and MLV print nothing further. No filesystem, device or media class in the
  line — the first thing a port should add.
- Stats line at stop (:3522-3532): `ApertarCore recording stats: enqueued= written= dropped_queue_full=
  discarded_on_stop= write_failures= peak_queue=<peak>/<max>`; lossless timing/phases lines (:3543-3565); `ApertarCore
  recorder stop time:` when stop > 0.20 s (:3584-3591); session-level `ApertarCore capture stats: dropped_gap_estimate=
  requeue_failures=` (:5998-6003). `takes.sh` greps exactly these tokens (apertar-kb/working/tools/takes.sh:15).

---

## 5. Gaps vs Cinemate (s1 brief) — each CONFIRMED from Core source unless marked

1. **No media class / filesystem detection.** Core: label + devname lookup -> a display string (§1b); lsblk `FSTYPE`
   used only for `mount -t`; `TRAN` discarded; `/proc/mounts` type/options discarded. Cinemate: udev ancestry + uevent
   + I2C hat probe -> class; `findmnt`/`blkid` -> fs, normalised (s1 §1).
2. **No per-media writer settings.** Workers/queue/nice/buffers depend on format only (§4). Cinemate: fs -> disk
   workers 8 (ext4) / 2 (exFAT, NTFS), buffers 8/10, affinity, nice (s1 §2). Core has no CPU affinity at all and no
   negative nice for workers (only `LimitNICE=-5` headroom for the camera thread).
3. **No block-queue / sysctl / NVMe-power tuning.** Nothing in the repo writes `/sys/block/*/queue/*`, `vm.dirty_*` or
   `nvme_core` parameters; service config is one line (§3f). Cinemate: scheduler `none`, `nr_requests` 512/256/128,
   `rq_affinity` 2, `dirty_bytes` 1 GiB/512/256 MiB, `dirty_background_bytes` 256/128 MiB, ratios 0, writeback 150,
   expire 3000, APST 0, applied for the RAW target only (s1 §5).
4. **Mount options.** Core's own mounts: `uid=1000,gid=1000,umask=0002` for exFAT/FAT/NTFS, none for ext4 (§3a); boot
   mount options unknown (§3e). Cinemate: `rw,noatime,nodiratime,commit=60` ext4; `uid,gid,dmask=022,fmask=133,rw,
   noatime` others.
5. **No pre-roll.** grep `preroll|pre-roll` over `src/`: no hits (only "Warm" as a CPU-temperature word at
   ApertarCoreApp.cpp:7923). Cinemate: 2 s take at sensor-max fps on start/mount, then deleted (s1 §3).
6. **Write-failure handling differs in kind.** Core: a DNG/MLV write exception -> `++writeFailures_`, `failRecording`
   (CameraController.cpp:3856-3861, :3947-3952) which sets `failure_`, clears the queue and stops the workers
   (:3958-3968); `checkRecordingFailure` (polled every 1 s in `wait()` App:7032-7045 and on every command App:9110)
   then stops the session and publishes `recording_error` (CC:8990-9005; App:7853, :9261). So **the take is aborted on
   the first failed write**, and the only *live* warning during a take is the per-clip latch `recording_health
   {recording_has_dropped_frames}` (util/RecordingDropWarning.hpp:9-23@f60e301; emitted CC:7919-7923; broadcast
   immediately App:10896-10907), set on queue-full (CC:3645-3646, :3689-3690) or gap drops. Cinemate: counts
   `writeFailures`, keeps recording, shows "drive cannot keep up / use exFAT or ext4" live (s1 §4). Neither has a
   throughput-based early warning.
7. **Time-left model.** Core: 1.5 B/px × fps × 1.08/1.03, ignores bit depth and compression (§2b). Cinemate: bits/8 ×
   px + 1024 + thumbnail, uncompressed only (s1 §4). Both static; neither uses measured write speed.
8. **Speed test.** Core has a real capability probe (fio direct / dd fdatasync) that nothing consumes (§2); Cinemate has
   no probe but publishes consumption rate from statvfs deltas (s1 §4).
9. **Formatting.** Core offers exFAT (default), FAT32, NTFS and refuses ext4 (§3b); Cinemate offers ext4/exFAT/NTFS and
   refuses FAT32 for recording. Core's Python watcher will not mount vfat (§3d) while its C++ path mounts it — a FAT32
   card formatted by Core will not auto-remount after an NVMe eject.
10. **No fsck / repair, no RAW-label arbitration, no mount event.** Core polls `/proc/mounts` on every `/api/state`
    request (:7732) and has no mount-change callback; Cinemate reacts to udev and restarts the recorder on a profile
    change (s1 §1b).
11. **Already ahead of Cinemate at HEAD (not f60e301):** O_DIRECT uncompressed DNGs with automatic EINVAL fallback,
    page-aligned pool, 8 raw buffers in Clear HDR — but all switched by env/format, not by media (§4 HEAD notes).

---

## 6. What a port needs

### 6a. `MediaProfile` (one struct, computed once per mount, re-read at record_start)
Identity: `devicePath` (/dev/nvme0n1p1), `rootDisk` (nvme0n1), `mountPoint`, `label`, `model`, `serial` (lsblk SERIAL —
add to the `-o` list at App:2294), `fsType` (take `/proc/mounts` column 3 at App:2029/:2046 instead of discarding it;
normalise `ntfs3`/`fuseblk` -> ntfs, keep `vfat` distinct), `mountOptions` (column 4), `transport` (lsblk `TRAN`,
already requested :2294), `mediaClass` enum {CfeHat, PiNvme, UsbNvmeUas, UsbStorage, SdCard, Unknown} from
`/sys/block/<root>/device` realpath (`/usb/`, `1000110000.pcie`), `uevent` (`driver=uas|usb-storage|nvme`), `TRAN`,
plus "CFE hat present" from `apertar-hardware.conf [cfexpress_hat]` (parser already embedded at App:3458-3462) or an
I2C read; `logicalBlockSize` (`/sys/block/<root>/queue/logical_block_size`, O_DIRECT alignment); `freeBytes`,
`totalBytes`; `directIoSupported` (tri-state, learned from the HEAD EINVAL fallback); `measuredWriteMBps` +
`measuredAt` + `measuredWith` (fio/dd) keyed by `serial`, persisted next to `camera_settings.conf`.
Derived writer settings: `directIo` (ext4/exFAT yes; ntfs-3g/fuseblk no), `workers` (uncompressed: 4 on ext4, 2 on
exFAT/NTFS — Cinemate's 8/2 pattern scaled to Core's 4-core default), `queueFrames`, `rawCameraBuffers` (8 ext4 / 10
exFAT-NTFS per Cinemate; check `Cma` in `/proc/meminfo`, each Clear HDR buffer ~16.9 MB), `workerNice`, `fadviseDontNeed`
(buffered path only), `expectedBytesPerFrame` for the time-left model. Derived kernel settings: `scheduler`,
`nrRequests`, `rqAffinity`, `dirtyBytes`, `dirtyBackgroundBytes`, `nvmePsMaxLatencyUs` per class (Cinemate's table,
s1 §7a).

### 6b. Where to detect
- A media monitor in `ApertarCoreApp` (there is none today): poll `/proc/mounts` every 1 s (or `poll(POLLPRI)` on it) in
  the existing `wait()` loop next to `checkRecordingFailure` (App:7032-7045); on device change build the profile,
  publish a `media_state` event (the broadcast list at App:10896-10907 is where it must be added), and cache it so
  `buildWebStateJson` stops shelling out to `lsblk -no LABEL` on every `/api/state` (App:7733-7734).
- Re-validate at `record_start`: `CameraController::startRecording` (CC:8699-8734) has no media gate; add
  mounted + free-space + profile checks there, and pass the profile into `DngRecordingQueue::start` (CC:3377-3380)
  where the format-based defaults are chosen (:3432-3455).
- Buffer count is a camera-configure-time property (CC:6411-6413, :6796-6800; HEAD `rawCameraBufferCount`), so a
  profile change that alters it needs the same reconfigure Core already does for settings changes — deferred while
  recording, like Cinemate's restart.

### 6c. How to apply
- Writer: make the HEAD `directIoEnabled()` (CdngEncoder.cpp:467-475@2a6f114) and the open at :1803-1814 read the
  profile first, env second; keep the EINVAL fallback. Buffered path: keep SEQUENTIAL + DONTNEED (f60e301 :1758,
  :1779); consider the same for MLV (MlvEncoder.cpp:981 has only SEQUENTIAL). Workers/queue/nice: replace the constants
  at CC:3433-3455 and :3814 with profile values, env override wins. Log the profile in the clip line (CC:3462-3483):
  `fs= class= direct_io= buffers= mount_opts=`.
- Root helper: Core already uses the `sudo -n /usr/local/libexec/<helper> <fixed args>` pattern with a sudoers file
  (standby helpers, KB architecture/overview.md:49). Add `apertar-media-tune <rootdisk> <class> apply|restore`
  writing exactly: `/sys/block/<root>/queue/scheduler`, `/sys/block/<root>/queue/nr_requests`,
  `/sys/block/<root>/queue/rq_affinity`, `/proc/sys/vm/dirty_bytes`, `/proc/sys/vm/dirty_background_bytes`,
  `/proc/sys/vm/dirty_ratio` (0), `/proc/sys/vm/dirty_background_ratio` (0), `/proc/sys/vm/dirty_writeback_centisecs`
  (150), `/proc/sys/vm/dirty_expire_centisecs` (3000), `/sys/module/nvme_core/parameters/default_ps_max_latency_us`
  (0; fall back to a `cmdline.txt` hint). Save originals on first apply, restore on unmount; apply only for the device
  mounted at the media root (Cinemate's c8f06c9 lesson, s1 §1a). Mount options for Core's own `mount_media`
  (App:3621-3637): add `noatime` everywhere, `nodiratime,commit=60` for ext4, `dmask/fmask` instead of `umask`.
- Trade-off to state in the tutorial: large dirty cushions and `commit=60` lengthen the unflushed window on a yank
  (T18); with O_DIRECT uncompressed DNGs the cushions matter less, the queue depth and buffers matter more.

### 6d. What to show in state
`media_filesystem`, `media_transport`, `media_class`, `media_profile` (name), `media_mount_options`,
`media_direct_io` (active/fallback/off), `write_speed_mbps` (number, not only text) + `write_speed_device` (serial) +
`write_speed_tested_at`, `estimated_bytes_per_second` (fix the model to bits/8 × px × fps × overhead, lossless from
the measured `avg_payload_mib`), `sustain_margin` = measured / estimated, live `write_failures` and
`dropped_queue_full` counters during a take (today only in the stop line), `raw_camera_buffers` in use. Mirror the
media block into the socket `get_state` (App:9253-9274 has none of it) so the native UI sees it too.

### 6e. Measurement that validates it
`apertar-kb/working/tools/takes.sh N [seconds]` (:1-19): N takes, each after a 12 -> 16-bit reconfigure, reading the
clip folder from the `recording clip:` journal line, the `enqueued=`/`dropped_queue_full=`/`dropped_gap_estimate=`/
`peak_queue=` tokens, counting gaps in DNG indices (`missing=`) and the IPA rate. Run it per medium and filesystem
(CFE exFAT, CFE ext4, USB SSD, SD) in 16-bit uncompressed at 25 and 30 fps, once with the profile applied and once
with it forced off (env), plus `run_media_speed_test` before each batch and `findmnt -no FSTYPE,OPTIONS /media/RAW`
in the log. Pass criteria already used by T24: 5/5 takes `missing=0`, `intervals>60ms=0`, `write_failures=0`,
`peak_queue` well below the maximum.

---

## Surprises
- `/proc/mounts` filesystem type and options are parsed and discarded twice (App:2029-2030, :2046-2047).
- lsblk `TRAN` and `RM` are requested but never read (:2294 vs. no consumer).
- The media-type fallback for an unknown device is "CFExpress Type B" (:2003).
- Core's own Python re-insert watcher refuses to mount vfat (:3559-3560) although Core formats FAT32 (:3822).
- The dd fallback speed is MiB per wall second including process start, labelled "MB/s" (:9081-9084, :3892).
- MLV has no `POSIX_FADV_DONTNEED` (MlvEncoder.cpp: only :981 SEQUENTIAL), contrary to the brief.
- The clip model ignores bit depth; the still model does not (:4766-4771 vs :4784-4800).
- Core aborts the take on the first failed write (CC:3856-3861 -> :3958-3968 -> :8990-9005); Cinemate counts and continues.
- The tree is 4 commits past f60e301 and those commits (direct I/O, copy worker, requests=buffers) are the storage
  work the port is about; the per-media layer is still missing at HEAD.

## UNKNOWN
- Mount options used by `media-RAW.service` / `mount-raw.sh` and by `apertar-cfe-automounter` at boot (not in any
  local repo; Apertar-UI not checked out).
- Filesystem currently on the rig's `/media/RAW` (never recorded; `findmnt` needed).
- Which sudoers rules exist on the image for `mount`, `mkdir`, `mkfs.*`, `blockdev`, `sh -c` (not in the Core repo).
- Whether the fio binary is installed on the image (the dd fallback suggests it may not be; KB clearhdr-compare-notes.md:85 raises the same doubt).
- Whether exFAT's `fallocate` support makes per-file preallocation worthwhile on the CFE (not investigated; kernel source not read for this).

## Verification

Adversarial pass, 2026-10-26. Every cited line was opened with `git show f60e301:<path>` (or `2a6f114:`) and read in a window; KB lines with `sed -n`. Repo state at verification time: the Core checkout is on branch `clearhdr-fixes` at **4ea877c** (five commits past f60e301: 2f5a880 buffers, ce723fd direct I/O, 9e06ad6 copy worker, bb85899 phase lock, 4ea877c yank survival) with a dirty working tree; **2a6f114 is a dangling object** (`git branch -a --contains 2a6f114` is empty, the branch was rebuilt by cherry-pick), so the reader's note "Checkout HEAD is 2a6f114" is stale and its `@2a6f114` citations resolve only through `git show`.

### Verdict table

| # | Finding | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Media knowledge text-based; /proc/mounts type+options parsed and discarded | **CONFIRMED** | `App.cpp:2023-2038`, `:2040-2055` (`type`/`options` read at `:2029-2031`, `:2046-2048`, never used); `lsblk -no LABEL` at `:2063`. Addition: `volumeLabelForDevicePath` has a second path, realpath match against `/dev/disk/by-label` (`:2075-2089`). |
| 2 | Type label table, fallback "CFExpress Type B", exposed as capture.storage | **CONFIRMED** | `:1992-2004` (fallback `:2003`), `:2006-2021` (`/dev/sd` `:2016`, `/dev/nvme` `:2018`), `:7735-7737`, `:7973`. Purely string-based; no sysfs/udev/I2C. |
| 3 | lsblk -P scan, 3 s cache, filters, JSON fields, TRAN/RM unused | **CONFIRMED** | `:2293-2294` command; cache `std::chrono::seconds(3)` `:2288`; filters RO `:2345`, type `:2347`, empty FSTYPE `:2349`, system device `:2351` (set built `:2315-2328` from `isSystemMountPoint`), mounted elsewhere `:2353`; struct `:2236-2245`; JSON `:2401-2420`. `grep '"TRAN"\|"RM"'` in App.cpp@f60e301: no consumer. |
| 4 | /api/state media fields; socket get_state has none | **CONFIRMED**, one precision | `media_mounted` is top-level (`:7914`); `media_free_bytes` … `write_speed_error` sit **inside the `system` object** (`:7917-7965`: `:7934-7942`, `:7947-7964`); `media_label` `:7937`; `time_left_percent` = minutes/120 ×100 clamped `:7828`; `media_writes_pending` `:7862-7863` ← `CC:5744-5748` (photo captures); `get_state` `:9253-9274` has no media/space fields. |
| 5 | Speed test sizes, fio/dd commands, parsing, storage, consumers | **CONFIRMED** | `:8986-9014` (96 MiB gate `:9000`; 64/128/256/512/1024 at ≥160/320/640/1152 `:9006-9014`); fio `:9036-9044`; dd `:9048-9051` (also `status=none`); regexes `:9064`, `:9073` (×1.048576 `:9076`); wall fallback `:9081-9084`; stored `:9092-9098`; `get_media_test_state` `:10675-10682`; texts `:3878-3929`. Additions: the timer starts at `:9035` **before** the fio attempt, so a dd fallback's MiB/s includes the failed fio run; `writeSpeedDetailText` labels MiB as "MB" (`:3911`, `:3915`, `:3924`). |
| 6 | fio psync ignores --iodepth → effectively QD1 | **UNVERIFIABLE** (label "probable" is honest) | Not derivable from any local repo. The "(QD32)" strings are at `:3915`, `:3924`. |
| 7 | Time-left model constants; still model honours bit depth | **CORRECTED** (clip model CONFIRMED) | `:4752-4772`: ProRes 45e6/102e6/220e6/147e6 ×px/(1920×1080) ×fps/30 ×1.05 (`:4755-4759`), H.264 25e6/8 (`:4762`), raw px×1.5×fps×1.08\|1.03 (`:4766-4771`); minutes `:7812-7816`. **Correction:** the still-size model honours bit depth only for imx294/imx577/imx477 (`:4784-4818`); for the **IMX585 it returns fixed 12.4 MiB / 3.1 MiB by resolution** (`:4820-4831`), ignoring bit depth too. Recomputed: 3840×2160 at 25 fps cDNG → 335.9 MB/s by the model; a 16-bit Clear HDR payload alone is 2 B/px = 414.7 MB/s, so the model under-estimates 16-bit by ≥19 % before container overhead. |
| 8 | mount_media behaviour and options | **CONFIRMED** | `:10663-10673`; `:3671-3675` refuses when mounted; fs type from forced rescan `:3682-3688`; `sudo -n mkdir -p` `:3618`; ntfs→ntfs3 `:3625-3627`, FAT family `:3628-3629`, options `uid=1000,gid=1000,umask=0002`; ntfs-3g fallback `:3644-3646`; everything else bare `sudo -n mount -t` `:3632-3637`. `grep noatime\|nodiratime\|commit=` App.cpp@f60e301: none. |
| 9 | format_media choices, label limits, commands, remount loop | **CONFIRMED** (quote precision) | default `value_or("exfat")` `:10647`; ext4/empty refused `:3777-3781`; label `:2171-2196` (vfat 11 `:2185`, exfat 15/ext4 16/ntfs 128 `:2190-2192`); unmount `:3795-3799`; commands `:3818-3827` use the **resolved tool path** from `formatFilesystemToolPath` (`:2141-…`, names `:2127-2138`), i.e. `mkfs.exfat -n`, `mkfs.vfat -F 32 -n`, `mkfs.ntfs -f -F -L` as stated; sync+settle `:3849-3850`; 10 attempts × 350 ms `:3853-3861`. |
| 10 | eject_media, NVMe detach, Python re-insert watcher | **CONFIRMED** | `:3719-3770`; flush `:3355-3364` (`sync -f` `:3358`, `blockdev --flushbufs` `:3362`); PCI remove `:3375-3382`; watcher `:3389-3611`; constants `:3400-3404`; `blkid -s TYPE` via sudo `:3508`; `mount_partition` `:3545-3562` (vfat refused by the `else` at `:3559-3560`, no umask); PCIe reset `:3564-3575`; launched detached with `&` `:3603-3604`. |
| 11 | Core never mounts at boot; startRecording has no media gate; boot actors from KB | **CONFIRMED (Core side) / PROBABLE (image side)**, label honest | Mount helpers are called only from `mount_media` (`:10669`), `mountMediaDeviceAtPath` (`:3697`) and the format remount (`:3856`); `CameraController::startRecording` `CC:8690-8735` and the session `startRecording` `CC:5858-5885` check state/settings/photos only, then `reserveClipFolder`+`create_directories` `:5880-5881`. README:246 ✓. KB `overview.md:15`, `:146`, `ui.md:398-410`, `clearhdr-compare-answer.md:57` read as cited. |
| 12 | Root operations inventory; no sudoers/chrt/ionice/taskset/sysctl in repo; LimitNICE=-5 | **CONFIRMED with a material nuance** | `prio.conf:1-3`, `start.sh:5,21`, `:3477-3491`, `ui-structure-notes.md:595` ✓. `git ls-tree f60e301 config scripts` = exactly those two files. **Nuance (see Added A):** `ProresEncoder.cpp:328@f60e301` states the page cache "is bounded system-wide already by `/etc/sysctl.d/60-apertar-writeback.conf`" and `:402` gives `vm.dirty_bytes (128 MB)` — the repo ships no such file, but Core's own source asserts the image has one. |
| 13 | Recorder tunables and defaults | **CONFIRMED values, CORRECTED as incomplete** | All listed values verified: `CC:1047-1048`; H264 4\|6, 3-12 `:1150-1151`; ProRes 12, 8-32 `:1157`; queue 24\|12, 4-64 `:3437-3439`; lossless min(8,threads+1) `:3442-3444` (=5 on 4 cores), lossy max(1,min(4,t)) `:3448` (=4), uncompressed max(2,min(4,t)) `:3433` (=4), MLV 1 `:3449-3455`; nice 5\|0, 0-19, only lossless/lossy `:3811-3817`; tile rows 128, 16-1024 `Cdng.cpp:52-67`; pool min(queue, max(workers+2,4)) `:3994` (→7 lossless, 6 lossy/uncompressed, 4 MLV); `APERTAR_RAW_CACHED_DMABUF` default true `:6657`; `:6411-6413`, `:6796-6797`. **Omitted** (see Added B): the ProRes, lossy-DNG and H.264 *writer* tunables, which are the per-format knobs a media profile would actually drive. |
| 14 | Write path: uncompressed DNG flags/fadvise/unlink/throw; MLV has only SEQUENTIAL | **CONFIRMED, scope narrowed** | `Cdng.cpp:1748-1753`, `:1758`, `:1770-1777`, `:1779`, `:1787`, `:1801`; lossless header via `pwrite` `:1763`. `Mlv.cpp:964-968`, `:981`; `grep fadvise` → only `:981`. **Scope:** this describes uncompressed/lossless cDNG and MLV only; at f60e301 lossy DNG already writes through a separate disk-writer thread by default and ProRes has a direct/buffered arm (Added B, C). |
| 15 | Clip log line fields; stats line; takes.sh tokens | **CORRECTED** | Clip line `CC:3462-3483` and stats `:3525-3532` as stated (stats printed only if a counter is non-zero `:3523-3524`; capture-stats only if gap or requeue > 0 `:5998`). **takes.sh:14-15 greps `recording clip:`, `enqueued=`, `dropped_queue_full=`, `dropped_gap_estimate=`, `peak_queue=` only** — not `written=`, `discarded_on_stop=`, `write_failures=` or `requeue_failures=`. "Exactly these tokens" overstates; `write_failures` is invisible to the current takes.sh. |
| 16 | Take aborted on first failed write; only live warning is recording_health | **CORRECTED (format-dependent)** | Holds for uncompressed/lossless cDNG (`CC:3856-3858`), MLV (`:3947-3949`), and the H.264/ProRes recorder (`:5046-5049` sets `failure_`, deactivates). **Does not hold for lossy DNG with the default async writer** (`APERTAR_LOSSYDNG_ASYNCWRITE` default on, `LossyDngEncoder.cpp:325-328`): the encode worker returns after `submit()` (`:508-511`), `++writtenFrames_` runs (`CC:3855`), and a failed disk write is only logged by the writer thread (`LossyDngEncoder.cpp:230-233`) — no `writeFailures_`, no `failRecording`, the take continues (Cinemate-like). Only `APERTAR_LOSSYDNG_ASYNCWRITE=0` makes it throw (`:512-514`). Precision: the event emitted is `{"event":"recording", …, "error":…}` (`CC:9271-9273`); `recording_error` is the state-field name (`App:7853`, `:9261`). Polling `:7037`/`:7044` and per command `:9110` ✓; latch `RDW.hpp:9-23`, `CC:3646`, `:7919-7923`, broadcast list `App:10896-10907` ✓. |
| 17 | No pre-roll, no block/sysctl tuning, no mount event, no affinity | **CONFIRMED for the repo; qualified for the image** | `git grep -i 'preroll\|pre-roll\|pre_roll' f60e301 -- src`: none; `:7732` per-request `/proc/mounts`; "Warm" only at `:7923`. Image-side sysctl: see Added A (Core's own comment says a writeback sysctl exists on the image). |
| 18 | HEAD additions (direct I/O, raw buffers, pool prefill, copy workers) | **CONFIRMED content; CORRECTED commit** | `Cdng.cpp:465-475@2a6f114` (page 4096, env default on), `:1803-1811` (EINVAL at open), `:1855-1862` (EINVAL at write, DONTNEED only when buffered `:1861-1862`); `CC:1057@2a6f114` (8), `:1171-1175` (3-16), `:3507` (copy workers 1, 1-2), `:6879` (prefill 6). 2a6f114 is **not on any branch**; the same work is on `clearhdr-fixes` (ce723fd, 2f5a880, 9e06ad6, bb85899) and HEAD is 4ea877c. Re-anchor before committing the KB. |
| 19 | Filesystem/transport/block size/identity not known as values; nothing persisted | **CONFIRMED** | `:2029-2030`, `:2294` vs no consumer, `:9092-9098` (single in-memory result, written only at `:9097`, never cleared on eject/mount). |

### Added (settled from source during verification)

**A. The image is probably already sysctl-tuned for writeback — Core's source says so.** `apertar-core/src/prores/ProresEncoder.cpp:326-329@f60e301` (comment): the write stall "is bounded system-wide already by /etc/sysctl.d/60-apertar-writeback.conf"; `:402`: "vm.dirty_bytes (128 MB)". No repo (Core, KB) carries the file; `grep -rl 60-apertar-writeback /home/user/tiramisioux` hits only that source file. Status: PROBABLE on the image, contents UNKNOWN (one `cat /etc/sysctl.d/60-apertar-writeback.conf; sysctl vm.dirty_bytes vm.dirty_background_bytes` on the Pi settles it). This changes gap 5 from "no sysctl tuning" to "a fixed 128 MB dirty_bytes with no per-media class", and it means a port's root helper must read and restore an existing value rather than assume kernel defaults.

**B. Writer tunables the reader's list omits (all f60e301, all per format, none per media):**
- ProRes (`src/prores/ProresEncoder.cpp`): `APERTAR_PRORES_ODIRECT` default **direct** (`:1094-1100`) — this is libavformat's `AVIO_FLAG_DIRECT` (no userspace staging copy), explicitly *not* `O_DIRECT` on the fd (`:213-214`); `APERTAR_PRORES_WRITER_THREAD` default **on** (`:1184-1186`, "the fix for the 4K72 drop cliff" `:1173`); `APERTAR_PRORES_WRITER_QUEUE` default 48 packets (`:429`, 1-512 `:1190`); `APERTAR_PRORES_WRITER_QUEUE_MB` default 96 MiB (`:430`, 8-1024 `:1195`); `APERTAR_PRORES_WRITER_SLOW_MS` default 250 ms (`:443`, `:1203`); `APERTAR_PRORES_WRITEBACK` default **off**, 4-512 MiB window (`:1154-1168`). Per-take log line `ApertarCore ProRes: disk arm=… APERTAR_PRORES_ODIRECT=… writeback=… write arm=…` (`:1208-1215`). On a failed write the writer latches the first error and the next `writeFrame()` returns false into `writeFailures_` (`:404-411`).
- Lossy DNG (`src/lossydng/LossyDngEncoder.cpp`): `APERTAR_LOSSYDNG_ASYNCWRITE` default on (`:325-328`, legacy `QRAW_LOSSYDNG_ASYNCWRITE`); `APERTAR_LOSSYDNG_WRITER_BYTES` byte cap default 512 MiB, minimum 16 MiB (`:97-110`); `submit()` **blocks** the encode worker when queued bytes would exceed the cap (`:166-170`).
- H.264: `APERTAR_H264_PIPE_BYTES` (`CC:4565`), `APERTAR_H264_QUEUE_FRAMES` (`CC:4576`).
- `APERTAR_CDNG_PROFILE_DETAIL` (`Cdng.cpp:72`) is a profiling flag, not a tunable.

**C. A restart-free override channel already exists.** `tuningOverride()` (`ProresEncoder.cpp:787-812@f60e301`) reads the env var, then `/home/pi/.apertar-tuning` as `KEY=VALUE` lines (`#` comments), per clip. Only the ProRes knobs use it today; the cDNG knobs use `unsignedEnvValue`/`getenv` once. A MediaProfile could publish its derived settings through the same file format, or the port could route the cDNG knobs through `tuningOverride` so a tutorial can A/B without a service restart.

**D. The CFE automounter's mount options are partly recorded in the KB.** `apertar-kb/architecture/ui.md:406`: mount via `mount(2)`, ntfs → `ntfs3`, exfat/vfat with uid/gid 1000, ext4 plain, citing `CfeAutomounter.cpp:591-630` (Apertar-UI, not checked out here). PROBABLE; still no `noatime`/`commit=`. `mount-raw.sh` (media-RAW.service) remains UNKNOWN. `working/distribution-image.md` (4787 bytes) contains no `mount`, `/media`, `exfat` or `ext4` text, so it does not answer how `/media/RAW` is mounted on the image.

**E. Measurement gap for the port's validation step.** Because takes.sh does not capture `write_failures=` (finding 15) and lossy-DNG async failures never reach that counter at all (finding 16), the validation recipe in §6e must add `write failed for` (the stderr strings at `CC:3859`, `:3950`, `LossyDngEncoder.cpp:231`) to the journal grep, or the "write_failures=0" pass criterion is vacuous for lossy takes.

### Numbers recomputed
- Lossless workers on 4 threads: min(8, 4+1) = 5; lossy max(1, min(4,4)) = 4; uncompressed max(2, min(4,4)) = 4 — match.
- Raw pool: lossless min(24, max(5+2,4)) = 7; lossy min(24, 6) = 6; uncompressed min(12, 6) = 6; MLV min(12, max(3,4)) = 4.
- Speed-test size steps: 1024 MiB needs ≥1152 MiB free = size + 128 MiB headroom; 512/640, 256/320, 128/160 follow the same +25 % rule; 64 MiB needs 96 (+50 %).
- ProRes 4K HQ 30 fps estimate: 220e6/8 × 4 × 1 × 1.05 = 115.5 MB/s. cDNG 3840×2160 25 fps: 335.9 MB/s (model) vs 414.7 MB/s 16-bit payload (+8 % container ≈ 448 MB/s real).
- time_left 100 % = 120 min (`:7828`).

### Still UNKNOWN after verification
- `/usr/local/bin/mount-raw.sh` mount options; contents of `/etc/sysctl.d/60-apertar-writeback.conf` (existence asserted only by a Core comment); the rig's `/media/RAW` filesystem; image sudoers rules; whether fio is installed; exFAT fallocate value; fio psync/iodepth semantics (no local source).
