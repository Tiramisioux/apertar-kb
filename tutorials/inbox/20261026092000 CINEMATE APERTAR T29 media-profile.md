---
datum: 2026-10-26 09:20:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T29 media-profile
typ: digital anteckning
---

# T29. A media profile: let the drive decide the writers, the buffers and the kernel knobs

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-media-profile-the-recording-medium-and-tune-the-writ.patch`, Core `75e9f57`, on top of T28; amended after the critic pass: helper after the abort, APST knob, cached snapshot). Line numbers below are at `75e9f57`, the tree right after this patch; later patches shift them, the grep anchors do not. The pure header passes `working/tools/media_profile_test.cpp`; `ApertarCoreApp.cpp` and `CdngEncoder.cpp` pass a host syntax check; `CameraController.cpp` is not compiled there. Answer: `working/storage-answer.md`. Builds **M5** (recorders), **M7** (buffers), and a first root helper.

**You will learn**
- What Core actually knows about its drive today (a label) and what it throws away (the filesystem it parses from `/proc/mounts` twice).
- Cinemate's two-axis rule: the *connection* decides kernel knobs, the *filesystem* decides the writer topology, and only the recording target gets the global knobs.
- How to classify a block device from sysfs without a fallback that cannot say no.
- How to measure whether any of it matters on your medium before trusting a table.

**Risk:** Core rebuild and restart; the root helper writes `/sys/block/<disk>/queue/*` and `vm.dirty_*` (it saves and restores them; `APERTAR_MEDIA_TUNE=0` disables it, and without the helper installed nothing kernel-side happens). Undo: `git checkout` the files, remove the helper. **Time:** 4 h plus one `takes.sh` batch per medium.

## 1. The problem

`working/storage-answer.md` §1–2. In Core at f60e301: workers, queue depth, nice and camera buffers depend on the recording *format* only (`CC:3433-3455@f60e301`); `/proc/mounts` type and options are read and discarded (`App:2029-2030`, `:2046-2047`); lsblk's `TRAN` is requested and never read (`App:2294`); an unknown device is labelled "CFExpress Type B" (`App:2003`); Core's own `mount_media` passes no `noatime`; nothing writes a block-queue or dirty-page setting. T24's O_DIRECT is on for every medium, including FUSE ntfs-3g where every take pays one `EINVAL` fallback.

Cinemate (s1 §2, §5): ext4 8 disk workers / exFAT-NTFS 2; buffers 8 / 10 (a new directory entry per frame makes FAT spikier, `a61a589`); `vm.dirty_bytes` 1 GiB NVMe / 256 MiB USB SSD (SLC-cache cliff, `d7a8d2b`); `scheduler none`, `nr_requests 512`, `rq_affinity 2`; all of it only for `/media/RAW` (`c8f06c9`). None of those numbers were measured on Apertar's rig.

## 2. How this part works

```
 media watcher (T28)  --mounted-->  detectMediaProfile(snapshot)                      MediaProfile.hpp
                                       class: /sys/class/block/<root>/device realpath + uevent
                                              "/usb" -> usb-uas | usb-storage ; nvme -> pi-nvme ; mmcblk -> sd-card
                                       filesystem: /proc/mounts column 3 -> ext4 | exfat | vfat | ntfs | ntfs-fuse
                                       writer table: workers, queue, +raw buffers, direct I/O
                                    -> journal "ApertarCore media profile: class=.. fs=.. workers=.. queue=.. raw_buffers=+.. direct_io=.."
                                    -> sudo -n /usr/local/libexec/apertar-media-tune apply <root> <class> <fs>   (restore on loss)

 record_start -> CameraSession::startRecording(mediaRoot)
                   recorder_.setMediaProfile(detectMediaProfile(probeMediaRoot(mediaRoot)))      CC:6273
                   DngRecordingQueue::startAtFolder: normalWorkerCount, defaultQueueFrames from the profile  CC:3492
                   worker: encoder.setDirectIoPreferred(profile.writer.directIo)                CC:3922
                   clip line: ... media_class= media_fs= direct_io=                              CC:3538

 configure -> rawCameraBufferCount(clearHdr) + mediaExtraRawBuffersForConfiguredRoot()          CC:1173-1179
```

Precedence everywhere: **environment variable → media profile → the old default**. `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_CDNG_DIRECT_IO`, `APERTAR_RAW_CAMERA_BUFFERS` still win, which is how T29 §5 switches the profile off for the comparison without rebuilding.

The writer table (`MediaProfile.hpp:152-163`) is a *starting point*: ext4 {4 workers, queue 12, +0 buffers, direct}, exFAT/FAT/NTFS {2, 16, +2, direct}, ntfs-fuse {2, 16, +2, buffered}, unknown {2, 12, +0, buffered}. Compressed formats keep their CPU-bound worker counts.

Reading assignments: `src/util/MediaProfile.hpp` (all), `CC:1173-1181`, `CC:3486-3500`, `CC:3920-3923`, `App:9170-9192`, `App:9263-9300`, `scripts/apertar-media-tune`.

## 3. Find it yourself

**3.1 What is `/media/RAW`, really?** (Pi, read-only — T22 asked for this and it was never recorded)

```bash
findmnt -no SOURCE,FSTYPE,OPTIONS /media/RAW                       # which mounter produced these options? (Core's noatime reaches only mount_media)
DEV=$(findmnt -no SOURCE /media/RAW); ROOT=$(lsblk -no PKNAME $DEV); [ -z "$ROOT" ] && ROOT=$(basename $DEV)
readlink -f /sys/class/block/$ROOT/device; cat /sys/class/block/$ROOT/device/uevent | head -5
cat /sys/block/$ROOT/queue/scheduler /sys/block/$ROOT/queue/nr_requests /sys/block/$ROOT/queue/rq_affinity
sysctl vm.dirty_bytes vm.dirty_background_bytes vm.dirty_ratio vm.dirty_background_ratio
cat /etc/sysctl.d/60-apertar-writeback.conf 2>/dev/null                # Core's ProresEncoder.cpp says the image ships this with vm.dirty_bytes 128 MB
cat /sys/module/nvme_core/parameters/default_ps_max_latency_us 2>/dev/null
systemctl cat apertar-core | grep -E 'User=|ExecStart=|Nice=|CPUAffinity=|Environment'   # the sudoers snippet names pi; the env A/B needs the unit to read set-environment
```

Prediction: write down the filesystem and the class you expect before running. Then feed the two sysfs strings to the pure classifier:

```bash
g++ -std=c++20 -Wall -I ~/ApertarCore/src ~/apertar-kb/working/tools/media_profile_test.cpp -o /tmp/media_profile_test && /tmp/media_profile_test | tail -1
```

> [!tip]- Answer
> A CFE card or NVMe in the Pi 5 slot shows a realpath through `1000110000.pcie/.../nvme/nvme0` and `DRIVER=nvme` → `pi-nvme`; a USB SSD shows `/usb` and `DRIVER=uas` (UAS bridge) or `DRIVER=sd` → `usb-uas` / `usb-storage`. The values you printed are what the helper will change and what `restore` returns to: kernel defaults are `mq-deadline`/`none`, `nr_requests` 64–256, `dirty_ratio 20`, `dirty_bytes 0` — unless the image's `60-apertar-writeback.conf` already sets `dirty_bytes` 128 MB, in which case that is the baseline and "reboot restores defaults" means that file. Paste each medium's realpath and uevent into `media_profile_test.cpp` as a case before trusting its class.

**3.2 Where does Core decide workers and queue depth?** (Pi, read-only)

```bash
grep -n 'normalWorkerCount\|defaultQueueFrames\|APERTAR_CDNG_WORKERS' ~/ApertarCore/src/camera/CameraController.cpp | head
grep -n 'mediaRoot\|FSTYPE\|statvfs' ~/ApertarCore/src/camera/CameraController.cpp | grep -v allocate | head
```

> [!tip]- Answer
> Format only; the medium never enters (s2 §4). The second grep shows `mediaRoot` used solely to build the clip folder path.

**3.3 Baseline before the patch** (Pi, the measurement everything else is judged against)

```bash
python3 -I ~/apertar-kb/working/tools/core.py run_media_speed_test; sleep 20; python3 -I ~/apertar-kb/working/tools/core.py get_media_test_state
~/apertar-kb/working/tools/takes.sh 5 20          # 16-bit uncompressed cDNG, 25 fps
```

Record per take: `missing=`, `dropped_queue_full=`, `peak_queue=`, `write_failures=`, plus the speed-test MB/s. Repeat at 30 fps if T22 showed loss there.

## 4. Make the change

**4.1 The profile header** — `src/util/MediaProfile.hpp` as in the patch: enums, `classifyFilesystem` (`rootDiskForDevice` lives in `MediaProbe.hpp` since T28), `classifyMediaClass` (pure), `detectMediaClass` (sysfs), `writerSettingsFor` (the table), `MediaProfile` with `summary()`, `detectMediaProfile(snapshot)`, `configuredMediaRoot()` + `mediaExtraRawBuffersForConfiguredRoot()`. Re-run the host test against your copy.

**4.2 The recorder follows the profile** — `DngRecordingQueue`: member `MediaProfile mediaProfile_` + `setMediaProfile()` (`CC:3719`); `normalWorkerCount` from `APERTAR_CDNG_UNCOMPRESSED_WORKERS` → profile → format (`CC:3492`); `defaultQueueFrames` from the profile for uncompressed formats (`CC:3498`); `encoder.setDirectIoPreferred(...)` in `dngWorkerLoop` (`CC:3922`); the clip line (`CC:3538-3540`). `CameraSession::startRecording`: `recorder_.setMediaProfile(detectMediaProfile(cachedMediaSnapshotOrProbe(mediaRoot)))` before `startAtFolder` (`CC:6274`) — the watcher's cached snapshot, never a fresh `statvfs` under the controller lock. `rawCameraBufferCount` adds `mediaExtraRawBuffersForConfiguredRoot()` (`CC:1173-1181`); `CameraController::start` sets `configuredMediaRoot()` (`CC:8356`).

**4.3 The encoder's preference** — `CdngEncoder`: `setDirectIoPreferred(bool)` + `directIoPreferred_` (`CdngEncoder.hpp:111`, `:221`); `directIoEnabled()` becomes `directIoEnvOverride()` returning `std::optional<bool>` and the decision is `directIoEnvOverride().value_or(directIoPreferred_)` (`CdngEncoder.cpp:471-481`, `:1269`).

**4.4 The App** — watcher: after the loss handling, compute the profile, log it, `applyMediaTuning(profile, true)` / `(previous, false)` (`App:9196-9215`); `mediaProfile()` + `applyMediaTuning()` (`App:9276-9313`); `media_class`, `media_profile` in `/api/state`; `noatime` in `mountDeviceAtMediaPath` (`App:3627-3635`).

**4.5 The root helper** — `scripts/apertar-media-tune` (POSIX sh): per-class table, `apply` saves originals under `/run/apertar-media/tune/` then writes scheduler/nr_requests/rq_affinity, the six `vm.dirty_*` values and, for the Pi-NVMe class, `nvme_core.default_ps_max_latency_us = 0` (APST exit latency mid-take is a stall); `restore` writes them back. The watcher calls it only *after* the loss handling, so a `sudo` round-trip never delays an abort. Install:

```bash
sudo install -m 0755 ~/ApertarCore/scripts/apertar-media-tune /usr/local/libexec/apertar-media-tune
sudo install -m 0440 ~/ApertarCore/config/apertar-media.sudoers /etc/sudoers.d/apertar-media       # edit the user if Core does not run as pi
sudo install -m 0644 ~/ApertarCore/config/apertar-media.tmpfiles.conf /etc/tmpfiles.d/apertar-media.conf && sudo systemd-tmpfiles --create
sudo -n /usr/local/libexec/apertar-media-tune apply nvme0n1 pi-nvme exfat && sudo -n /usr/local/libexec/apertar-media-tune restore nvme0n1 pi-nvme exfat   # dry run by hand
```

Why a helper and not `sudo sysctl` from Core: one fixed path with fixed verbs is the smallest sudoers grant that still lets Core do its job; the helper logs every write, so a mistake is in the journal, not silent.

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | tail -3
sudo systemctl restart apertar-core
journalctl -u apertar-core -b --no-pager | grep -E 'media profile:|media: tuning' | tail -2
cat /sys/block/$ROOT/queue/scheduler; sysctl vm.dirty_bytes
```

Prediction: `ApertarCore media profile: class=<3.1's answer> fs=<3.1's answer> workers=.. queue=.. raw_buffers=+.. direct_io=..` then `media: tuning applied for <root> (<class>)`, and the sysfs values now read the table's.

**5.1 The clip line and the buffer count**

```bash
python3 -I ~/apertar-kb/working/tools/core.py record_start; sleep 5; python3 -I ~/apertar-kb/working/tools/core.py record_stop
journalctl -u apertar-core -b --no-pager | grep -E 'recording clip:|RAW buffers:' | tail -2
```

Prediction: `media_class= media_fs= direct_io=` on the clip line; `RAW buffers: ... count=10` on exFAT in Clear HDR (8 + 2), `count=8` on ext4. The buffer count is read at configure time from the watcher's cached snapshot: a medium swapped after the camera configured keeps the old count until the next reconfigure (toggle bit depth) or restart — Cinemate restarts cinepi-raw on a profile change for the same reason.

**5.2 The comparison** — the same `takes.sh 5 20` as 3.3, three ways, same medium, same mode:

```bash
~/apertar-kb/working/tools/takes.sh 5 20                                                       # profile on
sudo systemctl set-environment APERTAR_CDNG_UNCOMPRESSED_WORKERS=4 APERTAR_CDNG_QUEUE_FRAMES=12 APERTAR_RAW_CAMERA_BUFFERS=8 APERTAR_MEDIA_TUNE=0
sudo systemctl restart apertar-core; ~/apertar-kb/working/tools/takes.sh 5 20                  # profile forced off, kernel untouched
sudo systemctl unset-environment APERTAR_CDNG_UNCOMPRESSED_WORKERS APERTAR_CDNG_QUEUE_FRAMES APERTAR_RAW_CAMERA_BUFFERS; sudo systemctl restart apertar-core
~/apertar-kb/working/tools/takes.sh 5 20                                                       # writers on, kernel still off: separates the two halves
```

Write the prediction down first for each column. Decision rule: adopt the table only where the "on" column beats "off" on `missing=` or `peak_queue`; a column that merely ties means the medium did not need it.

**5.3 The pre-roll question** — Cinemate records and deletes a 2 s take on every mount, mechanism unstated. Test it: eject, remount, record immediately (take A), record again (take B); compare `missing=` and `peak_queue`. Three mount cycles. If A is consistently worse than B, a warm-up is worth building; if not, close the question in `lessons/hardware-log.md`.

**5.4 Yank interaction** — with `dirty_bytes` at 1 GiB on NVMe, how much buffered data (MLV/H.264/audio) can a pull lose? `writeback_watch.py` during an MLV take shows `nr_dirty`; multiply by 4 kB.

## 6. Commit and push

```bash
git -C ~/ApertarCore add src/util/MediaProfile.hpp scripts/apertar-media-tune config/apertar-media.sudoers config/apertar-media.tmpfiles.conf src
git -C ~/ApertarCore commit -m "media: profile the recording medium and tune the writers and the kernel for it

Connection class and filesystem from sysfs and the mount table; uncompressed
cDNG workers, queue depth, direct I/O and camera buffers follow the medium
(env still wins); root helper applies block-queue and vm.dirty_* for the
recording target and restores them. Logic ported from Cinemate's storage
profiles (2a49fa1, a61a589, c8f06c9, d7a8d2b).
Tested: <takes.sh columns>, media profile line, helper apply/restore."
git -C ~/ApertarCore push -u origin main
```

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `media profile: class=other fs=exfat` on a drive you know is USB | sysfs realpath has no `/usb` (a hub or bridge enumerated differently) | paste `readlink -f /sys/class/block/<root>/device` into a new case in `media_profile_test.cpp`, then extend `classifyMediaClass` |
| `tuning helper failed: sudo: a password is required` | sudoers snippet not installed or wrong user | `sudo -l` as the Core user; fix `config/apertar-media.sudoers` |
| `/sys/block/.../queue/scheduler not writable, skipped` | the helper ran unprivileged or the queue is virtual (mmcblk has no `scheduler` on some kernels) | fine: it is logged, not silent |
| `count=10` but `free -m` dropped more than you like | +2 Clear HDR buffers ≈ 34 MB | `APERTAR_RAW_CAMERA_BUFFERS=8` or edit the table |
| direct I/O fallback message on ntfs3 | the kernel ntfs3 driver refused O_DIRECT on this kernel | set `Ntfs` → `directIo=false` in the table; record the kernel version |
| no `media profile:` line at all | the watcher saw no change (profile logs only on change) | `journalctl ... | grep 'media:'` for the mount line; eject/remount to force one |
| `count=8` on exFAT after swapping media | the bump is read at configure time | toggle the bit depth or restart Core |
| `restore` leaves `dirty_bytes` at 128 MB | that was the image's value (`60-apertar-writeback.conf`), saved on the first apply | correct behaviour; the file is the baseline |

Undo: `git checkout -- src scripts config && git clean -f src/util/MediaProfile.hpp`; `sudo rm /usr/local/libexec/apertar-media-tune /etc/sudoers.d/apertar-media`; reboot restores the kernel defaults.

## 8. What you learned, going further

- Two classifications, two consumers; a table nobody measured is a hypothesis, which is why every value has an env override and the comparison in 5.2 exists.
- A root helper with fixed verbs beats a wide sudo rule; logging every write beats a comment saying what it should write.
- Exercise: expose `peak_queue` live in `/api/state` (today only in the stop line) so the operator sees the backlog Cinemate shows as a VU meter (`130b93e`).
- Going further: remember the speed-test result per drive serial (`lsblk -o SERIAL`) and show `measured / estimated` as a sustain margin.

## 9. Sources

- cinemate `services/storage-automount/storage-automount.py:108-157` (profiles), `:238-266` (classify), `:319-341` (sysctl), `:365-382` (gate); `src/module/storage_profiles.py:50-95`, `:149-171`; `src/module/ssd_monitor.py:482-547` (device type); commits `9184c68`, `2a49fa1`, `31126f2`, `a61a589`, `d7a8d2b`, `c8f06c9`, `0142c5b`, `888093c`; handbook `lessons/hardware-log.md:945-985` (NTFS-over-FUSE ceiling), `:1610-1666` (CFE fallback).
- `Apertar-Core@75e9f57`: `src/util/MediaProfile.hpp:79`, `:133`, `:195`; `MediaProbe.hpp:115`; `CC:1173-1181`, `:3492`, `:3498`, `:3538`, `:3719`, `:3922`, `:6274`, `:8356`; `CdngEncoder.hpp:111`, `:221`; `CdngEncoder.cpp:471`, `:1269`; `App:3627-3635`, `:9196-9215`, `:9276-9313`; `scripts/apertar-media-tune`; `config/apertar-media.*`. Critic items S1–S12 in `working/port-raw/critic.md`.
- `working/storage-answer.md`, `working/port-raw/s1-storage-cinemate.md`, `s2-storage-core.md`, `working/cinemate-lessons.md` §5, `working/tools/media_profile_test.cpp`, `takes.sh`, `writeback_watch.py`.

%% tutor
ref core src/util/MediaProbe.hpp 115 inline std::string rootDiskForDevice(const std::string &devicePath)
ref core src/util/MediaProfile.hpp 79 inline MediaClass classifyMediaClass(const std::string &rootDisk, const std::string &deviceRealpath,
ref core src/util/MediaProfile.hpp 133 inline MediaWriterSettings writerSettingsFor(MediaFilesystem filesystem, MediaClass /*mediaClass*/)
ref core src/util/MediaProfile.hpp 195 inline unsigned mediaExtraRawBuffersForConfiguredRoot()
ref core src/camera/CameraController.cpp 1173 unsigned int rawCameraBufferCount(bool clearHdr)
ref core src/camera/CameraController.cpp 3492 const unsigned int normalWorkerCount = unsignedEnvValue("APERTAR_CDNG_UNCOMPRESSED_WORKERS",
ref core src/camera/CameraController.cpp 3538 std::cerr << " media_class=" << mediaClassName(mediaProfile_.mediaClass)
ref core src/camera/CameraController.cpp 3922 encoder.setDirectIoPreferred(!mediaProfile_.known() || mediaProfile_.writer.directIo);
ref core src/camera/CameraController.cpp 6274 recorder_.setMediaProfile(detectMediaProfile(cachedMediaSnapshotOrProbe(mediaRoot)));
ref core src/cdng/CdngEncoder.cpp 1269 const bool ifdFirst = !lossless && destinationFd < 0 && directIoEnvOverride().value_or(directIoPreferred_);
ref core src/ApertarCoreApp.cpp 9286 void ApertarCoreApp::applyMediaTuning(const MediaProfile &profile, bool apply)
ref core src/ApertarCoreApp.cpp 9196 // Only now the profile and the root helper: a sudo round-trip must not
ref core scripts/apertar-media-tune 1 #!/bin/sh
check 3.1 | g++ -std=c++20 -I /home/pi/ApertarCore/src /home/pi/apertar-kb/working/tools/media_profile_test.cpp -o /tmp/media_profile_test && /tmp/media_profile_test | tail -1 | ALL CHECKS PASSED
check 4.1 | grep -c 'writerSettingsFor' /home/pi/ApertarCore/src/util/MediaProfile.hpp | ^[2-9]$
check 4.2 | grep -c 'setMediaProfile' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 4.3 | grep -c 'directIoEnvOverride' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp | ^2$
check 4.5 | test -x /usr/local/libexec/apertar-media-tune && echo installed | installed
check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'ApertarCore media profile:' | ^[1-9][0-9]*$
check 5.1 | journalctl -u apertar-core -b --no-pager | grep 'recording clip:' | tail -1 | media_fs=
%%

#CINEMATE
#APERTAR
