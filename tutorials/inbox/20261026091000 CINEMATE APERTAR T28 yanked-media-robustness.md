---
datum: 2026-10-26 09:10:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T28 yanked-media-robustness
typ: digital anteckning
---

# T28. A drive pulled mid-take: detect it on the mount root, stop without touching it, say so

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-media-survive-a-yanked-or-unmounted-recording-drive.patch` is the reference, Core `f2fa35b`; amended after the critic pass: device-node and NVMe-state checks in the probe, a cached snapshot for configure and record_start, WebUI on `media_alive`, 1 GiB free-space floor). Line numbers in the text are at `f2fa35b`; the `%% tutor` refs are at `e8bb1b7` (`cinemate-port`, 2026-10-26: patch applied as `438a342` + fix `e8bb1b7`, the MLV abandon hunk had landed in the DNG loop); later patches shift them, the grep anchors do not. Five of the eleven touched files pass a host syntax check (`MlvEncoder.cpp`, `LossyDngEncoder.cpp`, `AudioRecordingSession.cpp`, `ApertarCoreApp.cpp`, `WebControlPage.cpp`); the three new headers pass `working/tools/media_probe_test.cpp`; `CameraController.cpp` needs libcamera and is not compiled there. Answer: `working/yank-answer.md`. Supersedes the Core half of **T18**; the automounter half stays in the UI repo. Builds **M5** (recorders), **M6** (App/UI contract).

**You will learn**
- What the kernel actually does when a recording drive is pulled (the mount stays listed; `statvfs` on the root may fail with a small set of errnos — or keep answering from cached counters, which is why the probe also checks the device node and the NVMe controller state) and why Cinemate tests the mount root and never paths inside it.
- How Core ends a take today (first failed write → latched failure → 1 s supervisor) and the four places where the stop path reopens the dead medium.
- How to turn an errno into a class (`Removed`, `Full`, `ReadOnly`, `Permission`) and route one gate and one event through the existing supervisor instead of adding a parallel mechanism.
- Why a deliberate eject needs an intent flag before `umount`, and why the hardware log of the camera that invented all this contains no pull-during-take entry — yours will be the first.

**Risk:** Core rebuild and restart. One test pulls a drive during a take; use a scratch card with nothing you need, and expect the clip folder to be dirty afterwards (`fsck` it on a Mac). Undo: `git checkout` the eleven files. **Time:** 4 h including the pull tests.

## 1. The problem

`working/yank-answer.md` §1–2. In one line each:
- Core at f60e301 learns of a pull only when a DNG write fails; `media_mounted` keeps saying `true` because `/proc/mounts` still lists the dead mount (`App:2024-2038`).
- The failure message is `strerror`, the queue is cleared uncounted, and the stop path then renames the H.264 temp file, patches the MLV header, drains the lossy writer and reopens `audio_capture.raw` — all on the medium that is gone (`CC:5990-6013@f60e301`, y2 §1.6).
- A lossy-DNG take never stops: the background writer only logs (`LossyDngEncoder.cpp:230-232`).
- `record_start` has no media gate; a take with nothing mounted lands on the SD card (y2 §2).
- Core's own eject has no intent flag; an automounter that treats udev `change` like `add` remounts within a second (Cinemate `f01b6cd`).

## 2. How this part works

```
 media watcher thread (App:9157)        every 1 s idle / 250 ms recording
   probeMediaRoot(/media/RAW)           /proc/mounts exact match  +  /sys/class/block/<part> present?
                                        +  /sys/block/<nvme>/device/state  +  statvfs(root)
   -> MediaSnapshot{state: none|mounted|removed|error, device, fstype, free, errno, node, nvme_state}
   -> updateCachedMediaSnapshot()       configure-time buffer counts and record_start read this, never statvfs
   -> on change: journal line, broadcast event {"event":"media",...}
   -> mounted -> removed/none while recording:
        camera_.flagMediaFault("Media removed during recording.", mediumGone=true)
        lock commandMutex_; camera_.checkRecordingFailure()   (the same path a failed write takes)

 recorder worker (CC:3928-3953)          first failed write
   catch std::exception -> classifyMediaException(e) -> MediaFault
   failRecording(mediaFaultMessage(fault, e.what()), fault)
     latch message + class; mediumGone_ if Removed; count queued frames as discarded_on_failure

 supervisor (CC:9437)                    every 1 s and on every command, and from the watcher
   checkRecordingFailure(): error = external message or recorder error
     mediumGone = external flag || recorder fault == Removed
     session_->stopRecording(mediumGone)            CC:6273
       H.264: leave <clip>.mp4.writing      DNG queue: stop(mediumDead) -> lossy abandon, MLV abandon()
       audio: stop(finalize=false)          nothing opens a path on the medium again
   recording event {..., "fault":"media_removed"}; state recording_fault, media_state
```

The errno classes (`src/util/MediaFault.hpp`): `EIO ENODEV ENXIO ENOTCONN ESTALE ENOENT` → `Removed` (Cinemate's `YANK_ERRNOS` plus ENXIO); `ENOSPC EDQUOT` → `Full`; `EROFS` → `ReadOnly`; `EACCES EPERM` → `Permission`. Only `Removed` means "do not touch the medium again".

Why `statvfs` is not enough on its own (the critic read the kernel for this): `ext4_statfs` answers from in-memory per-cpu counters and exFAT/FAT cache theirs after the first call, so a pulled drive can keep "answering" until something writes. The probe therefore asks two device-level questions first, the ones Cinemate's udev-remove path and NVMe watchdog ask: is the partition's `/sys/class/block/<name>` node still there (USB: gone the moment the device is removed), and does `/sys/block/<nvme>/device/state` read `dead` (NVMe: only after the controller's I/O timeout, 30–60 s, so a CFE pull is slow to show here and the writer's EIO usually wins). `evaluateMediaProbe` takes both as inputs and is host-tested.

Why the probe has its own thread: `statvfs` on a hung USB device can block for 30 s+; Cinemate skips SD cards in its watchdog for that reason (`storage-automount.py:839-843`). The App's 1 s tick holds `commandMutex_`, so the probe cannot live there (y2 §6.1).

Reading assignments: `src/util/MediaFault.hpp`, `src/util/MediaProbe.hpp` (`evaluateMediaProbe` at `:145`, `probeMediaRoot` `:185`, the cache `:236`), `App:9157-9262`, `CC:4069-4090`, `CC:6273-6300`, `CC:9437-9475`, `working/port-raw/critic.md` items Y1–Y14.

## 3. Find it yourself

**3.1 What does the kernel do when you pull a drive?** (Pi, scratch card, **not recording**)

```bash
grep ' /media/RAW ' /proc/mounts
# pull the card / USB drive now
grep ' /media/RAW ' /proc/mounts; stat -f /media/RAW; echo "errno path: $?"; ls /media/RAW | head -2; dmesg | tail -3
```

First write down the filesystem (`findmnt -no FSTYPE /media/RAW`): the prediction depends on it. Prediction: the mount is still listed; on ext4 `stat -f` may **succeed** (in-memory counters) while `ls` fails; on exFAT/FAT `stat -f` may succeed too; `/sys/class/block/<part>` is gone at once for USB, still present for an NVMe/CFE card until the controller times out. Write down what you see — this is the UNKNOWN the answer could not settle from source, and the reason the probe no longer relies on `statvfs` alone.

> [!tip]- Answer
> "Is it in /proc/mounts" is not "is it here", and neither is "does statvfs answer". The device node is the honest witness for USB; the controller state for NVMe. If something has already run `umount -l`, `stat -f` succeeds again with the SD card's figures: the mount table must agree, which `evaluateMediaProbe` encodes as `None` vs `Mounted` vs `Removed`. On FAT32 note one more thing: a *buffered* `write()` (MLV, H.264, audio) keeps succeeding into the page cache after the pull (`fs/fat` has no shutdown hook), so only the O_DIRECT cDNG writer, the node check or the NVMe state ends such a take.

**3.2 Where does Core end a take today, and what does it touch afterwards?** (Pi, read-only)

```bash
grep -n 'failRecording\|checkRecordingFailure\|session_->stopRecording' ~/ApertarCore/src/camera/CameraController.cpp | head -12
grep -n 'patchFrameCount\|finalizeWav\|std::filesystem::rename(tempPath_\|drainWrites' ~/ApertarCore/src/mlv/MlvEncoder.cpp ~/ApertarCore/src/audio/AudioRecordingSession.cpp ~/ApertarCore/src/camera/CameraController.cpp
```

Prediction: `failRecording` clears the queue; the four finalisers are unconditional.

> [!tip]- Answer
> The take stops, which is better than Cinemate (which keeps writing failures until the operator stops), but it stops *dirty*: every finaliser reopens the medium, and a FUSE/NTFS mount can hang each of them.

**3.3 Does lossy DNG stop at all?** (Pi, read-only)

```bash
sed -n 225,235p ~/ApertarCore/src/lossydng/LossyDngEncoder.cpp
```

> [!tip]- Answer
> A `std::cerr` line and nothing else; the encoder worker already handed the buffer off and sees no error. The patch adds a failure count + last errno to the writer and lets the worker raise it one frame late.

**3.4 Host test of the decision logic** (Mac or Pi, no camera)

```bash
g++ -std=c++20 -Wall -I ~/ApertarCore/src ~/apertar-kb/working/tools/media_probe_test.cpp -o /tmp/media_probe_test && /tmp/media_probe_test | tail -1
```

Prediction: `ALL CHECKS PASSED`. Read the "exact match picks /media/RAW, not /media/RAW1" case: cinepi-raw's `strstr` mount test kept a standby drive "mounted" (y1 Q7 #2).

## 4. Make the change

Eleven files; the patch is the reference. Order:

**4.1 Pure headers** — `src/util/MediaFault.hpp` (errno → class, message, name), `src/util/MediaProbe.hpp` (`findMountEntry`, `rootDiskForDevice`, `evaluateMediaProbe` with the node/NVMe inputs, `probeMediaRoot`, the cached snapshot `updateCachedMediaSnapshot`/`cachedMediaSnapshotOrProbe`), `src/util/MediaIntent.hpp` (eject flag under `$APERTAR_MEDIA_RUN_DIR/eject/`, default `/run/apertar-media`). Run 3.4 against your copies.

**4.2 Recorder latch** — `DngRecordingQueue` (`CC:3399`): `failRecording(error, fault)` records the class, `mediumGone_`, `discardedOnFailureFrames_ += queue_.size()` (`CC:4069`); both catch sites classify (`CC:3949`, `:4055`); lossy check after `writeDngFile` (`CC:3937`); `hasCapacityForFrame` counts `skippedAfterFailure_` (`CC:3713`); `stop(bool mediumDead)` abandons the lossy queue and lets the MLV worker `abandon()` (`CC:3560`, `:4024`); stats line gains `discarded_on_failure= skipped_after_failure= fault=`.

**4.3 Encoders** — `MlvEncoder`: `lastErrno_` set in both catch blocks, `abandon()` (`MlvEncoder.cpp:993`, `:1043`, `:1050`). `LossyDngDiskWriter`: `failures_`, `lastErrno_`, `abandon()`; statics `diskWriteFailures()`, `lastDiskWriteErrno()`, `abandonWrites()` (`LossyDngEncoder.cpp:187`, `:252`, `:398`). `AudioRecordingSession::stop(bool finalize)` (`AudioRecordingSession.cpp:358-380`). H.264 `setMediumDead()` and the `else if` around the rename (`CC:4609`, `:5133`).

**4.4 Session and controller** — `stopRecording(bool mediumGone)` passes the flag to every recorder (`CC:6273-6300`); `recordingFault()` (`CC:6530`); `checkRecordingFailure` reads the external flag and the recorder class, logs `ApertarCore recording failure: fault= medium_gone= message=`, calls `stopRecording(mediumGone)` (`CC:9437`); `flagMediaFault()` and `recordingFaultName()` (`CC:9462`, `:9472`); `recording` event gains `"fault"`.

**4.5 App** — watcher thread start/stop next to the preview thread (`App:6847`, the three failure paths and `stop()`); `runMediaWatcher` (publishes the cache at `App:9163`), `stopMediaWatcher`, `mediaSnapshot`, `mediaGateError` with the 1 GiB floor (`App:9157-9256`); gate in `handleCommand` right after the pending-writes gate (`App:9260`); `media_state`, `media_alive`, `media_device`, `media_fstype`, `recording_fault` in `/api/state` and `get_state`; `"event":"media"` in the always-broadcast list; eject intent in `ejectMediaAtPath` (`App:3734`) and clear in `mountMediaDeviceAtPath` (`App:3700`).

**4.6 WebUI** — `hasMedia` follows `media_alive` when the state has it (so a pull greys the button, not only an eject); record button disabled without media; `MEDIA REMOVED` status (`WebControlPage.cpp`, the three `hasMedia` sites and the status line).

Design note to keep in mind while typing: everything funnels into the *existing* supervisor. The watcher does not stop the take itself; it flags, then calls the same `checkRecordingFailure()` the tick calls. "When this project routes, it wins" (handbook).

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | tail -3
sudo install -d -o $(id -un) -g $(id -gn) /run/apertar-media/eject          # until the automounter/tmpfiles.d creates it
sudo systemctl restart apertar-core
journalctl -u apertar-core -b --no-pager | grep 'ApertarCore media:' | tail -1
curl -s localhost:8000/api/state | grep -o '"media_state":"[a-z]*","media_alive":[a-z]*,"media_device":"[^"]*","media_fstype":"[^"]*"'
```

Prediction: `ApertarCore media: state=mounted device=/dev/... fstype=exfat free_mb=... errno=0` and the same in the state.

**5.1 The gate** — eject the media from the WebUI, then press record (WebUI and the hardware button):

```bash
python3 -I ~/apertar-kb/working/tools/core.py record_start
```

Prediction: `No media mounted at /media/RAW.` from both paths; the WebUI record button is disabled; status reads `NO MEDIA`.

**5.2 The pull** (scratch card, 16-bit cDNG at 25 fps, record 20 s, then pull; stopwatch in hand):

```bash
journalctl -u apertar-core -f | grep -E 'media:|recording failure|write failed|recording stats|recorder stop time|audio:|H.264:|MLV:' &
python3 -I ~/apertar-kb/working/tools/core.py record_start; sleep 20
# pull the card now; note the time
```

Predictions, written before pulling:
1. USB: `ApertarCore media: state=removed ... node=0` within 250 ms of the pull (the node check), whatever `errno=` says. CFE/NVMe: the writer's `DNG write failed ... fault=media_removed errno=5` very likely wins, and `nvme_state=dead` follows only after the controller timeout (30–60 s); if neither appears within a few seconds the writer is blocked in the kernel until that timeout — note the time. Write down which signal fired first and on which filesystem.
2. `ApertarCore recording failure: fault=media_removed medium_gone=1 message=Media removed during recording.`
3. `recording stats: ... write_failures=1 discarded_on_failure=<queue depth> skipped_after_failure=<a few> fault=media_removed`.
4. `recorder stop time:` absent or < 1 s (nothing waited on the dead medium); `audio: medium gone, WAV not finalised`.
5. WebUI toast `Recording stopped: Media removed during recording.`; status `MEDIA REMOVED`; `/api/state` has `recording_fault:"media_removed"`, `media_state:"removed"`.
6. Reinsert → `media: state=mounted` within 1 s only if an automounter mounts it (the UI's `apertar-cfe-automounter` for the CFE slot); USB media stays `none` until `mount_media`.

Repeat once with lossy DNG 3:1 (prediction 1 becomes "fault=media_removed" one frame after the first failed background write) and once with MLV (`MLV: medium gone, leaving ...`). Then unmount instead of pulling (`sudo umount -l /media/RAW` during a take): prediction `state=none` and `message=Media was unmounted during recording.`

**5.3 Eject intent** — with the media mounted, eject from the WebUI and watch:

```bash
ls /run/apertar-media/eject/; grep ' /media/RAW ' /proc/mounts
```

Prediction: a flag named after the device; the mount does not come back by itself. Mount again from the WebUI: the flag is gone.

Record all six predictions and their outcomes in `lessons/hardware-log.md`: this is the first measured pull-during-take in either project.

## 6. Commit and push

```bash
git -C ~/ApertarCore add src/util/MediaFault.hpp src/util/MediaProbe.hpp src/util/MediaIntent.hpp src
git -C ~/ApertarCore commit -m "media: survive a yanked or unmounted recording drive

Media watcher (mount table + statvfs on the root), errno classes, a stop
path that never reopens a gone medium, counted losses, media event and
state fields, one record gate, eject intent for the automounter.
Logic ported from Cinemate's storage handling (8f49468..f01b6cd).
Tested: pull during cDNG/lossy/MLV takes, umount -l during a take,
eject intent; numbers in apertar-kb lessons/hardware-log.md."
git -C ~/ApertarCore push -u origin main
```

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `state=removed` flaps mounted/removed every second | the drive answers intermittently (bad contact) or a FUSE mount returns EIO on `statvfs` while alive | read `dmesg`; if FUSE, add the fstype to an allow-list in `evaluateMediaProbe` only after confirming the drive is fine |
| the take does not stop within 2 s of a CFE/NVMe pull | the writer is blocked in the kernel until the NVMe I/O timeout; the node is still present and `statvfs` may still answer | wait for `nvme_state=dead` (30–60 s); Cinemate's 50 ms latch poll on the hat's I2C byte is the only faster signal and lives in the automounter half |
| `state=mounted` persists after a USB pull | the partition node is still listed (`ls /sys/class/block/`) — a hub that did not report the removal | `udevadm monitor` while pulling; if no remove event, the port needs the automounter's help |
| FAT32: MLV/H.264/audio keep "writing" after a pull | buffered writes land in the page cache; FAT has no shutdown hook | the node check ends the take; switch the card to exFAT for recording |
| `recorder stop time: 12.3s` | a `close()` or `join()` waited on the dead mount | which recorder? the preceding lines say; that finaliser still touches the medium |
| `eject intent not recorded (/run/apertar-media/eject does not exist)` | nobody created the directory | the `install -d` line in §5, or a `tmpfiles.d` rule `d /run/apertar-media/eject 0755 pi pi -` |
| record refused on a dev machine with a plain directory as media root | the gate wants a mount point | `APERTAR_MEDIA_REQUIRE_MOUNT=0` in the service environment |
| `No media mounted` right after a mount | the watcher has not cycled yet | `mediaSnapshot()` probes directly in that case; if it persists, the mount path differs from `--media` |

Undo: `git checkout -- src && git clean -f src/util/Media*.hpp`, rebuild.

## 8. What you learned, going further

- A guard that reads the present cannot defend a write that happens later: the gate and the classification at the write are both needed (handbook).
- Count every frame's fate: written, failed, discarded at the latch, skipped after it. Cinemate's post-take verdict is blind after a pull because it counts files on a drive that is gone.
- Exercise: a detached finaliser for `DngRecordingQueue::stop(true)` (the H.264 recorder already has one), so a hung `close()` never holds `commandMutex_`.
- Automounter half (UI repo): honour `/run/apertar-media/eject/<dev>` on add/change (nothing consumes the flag yet — until then §5.3 is bookkeeping); on the Core `media` event with `state=removed`, run `umount -l`; write a ready file; then T18's "USB remount" becomes `media: state=mounted` for free.
- Two recorders still touch a dead mount at stop and were left alone on purpose until measured: the gyro session exports its sidecar in `stop()`, and the ProRes recorder finishes its container (critic Y7). If §5.2's `recorder stop time` is long with gyro or ProRes on, those are next.
- The `recording` event is not always-broadcast; a stop that lands while a command is collecting events reaches the HDMI process late (KB #36, critic Y6). The `media` event is, so the UI can react to the removal itself.

## 9. Sources

- cinemate `src/module/ssd_monitor.py:731-771@d6cc93e` (`_handle_storage_error`), `services/storage-automount/storage-automount.py:835-864` (statvfs watchdog), `:513-531` (non-blocking `umount -l`), `:55-72` (eject flags); cinepi-raw `cinepi/dng_encoder.cpp:2352-2386@63a08d5` (write failures counted, never stopped); commits `8f49468`, `3259da7`, `1e56cb6`, `58fc7c2`, `8b705c8`, `5fbef52`, `34f8c59`, `f01b6cd`, `888093c`.
- `Apertar-Core@f2fa35b`: `src/util/MediaFault.hpp:24`, `MediaProbe.hpp:115`, `:145`, `:185`, `:236`, `MediaIntent.hpp`; `CC:3560`, `:3713`, `:3949`, `:4055`, `:4069`, `:6273`, `:6530`, `:9437`, `:9462`, `:9472`; `App:3700`, `:3734`, `:6847`, `:9157-9262`, `:9260`; `MlvEncoder.cpp:993`, `:1043`, `:1050`; `LossyDngEncoder.cpp:187`, `:252`, `:398`; `AudioRecordingSession.cpp:358-380`; `WebControlPage.cpp`. Critic items Y1–Y14 in `working/port-raw/critic.md`.
- `working/yank-answer.md`, `working/port-raw/y1-yank-cinemate.md`, `y2-yank-core.md`, `working/cinemate-lessons.md` §4, `working/tools/media_probe_test.cpp`.

%% tutor
ref core src/util/MediaFault.hpp 24 inline MediaFault classifyMediaErrno(int err)
ref core src/util/MediaProbe.hpp 115 inline std::string rootDiskForDevice(const std::string &devicePath)
ref core src/util/MediaProbe.hpp 145 inline MediaSnapshot evaluateMediaProbe(const MountTableEntry &entry, int statvfsErrno,
ref core src/util/MediaProbe.hpp 185 inline MediaSnapshot probeMediaRoot(const std::string &mountPath)
ref core src/util/MediaProbe.hpp 236 inline MediaSnapshot cachedMediaSnapshotOrProbe(const std::string &mountPath)
ref core src/camera/CameraController.cpp 3547 void stop(bool mediumDead = false)
ref core src/camera/CameraController.cpp 3700 bool hasCapacityForFrame(uint64_t frameIndex)
ref core src/camera/CameraController.cpp 4079 const MediaFault fault = classifyMediaException(e);
ref core src/camera/CameraController.cpp 4199 void failRecording(const std::string &error, MediaFault fault = MediaFault::Other)
ref core src/camera/CameraController.cpp 6302 void stopRecording(bool mediumGone = false)
ref core src/camera/CameraController.cpp 9486 bool CameraController::checkRecordingFailure()
ref core src/camera/CameraController.cpp 9511 bool CameraController::flagMediaFault(const std::string &message, bool mediumGone)
ref core src/ApertarCoreApp.cpp 9169 void ApertarCoreApp::runMediaWatcher()
ref core src/ApertarCoreApp.cpp 9175 updateCachedMediaSnapshot(current);
ref core src/ApertarCoreApp.cpp 9236 std::string ApertarCoreApp::mediaGateError() const
ref core src/ApertarCoreApp.cpp 9272 if (const std::string gate = mediaGateError(); !gate.empty())
ref core src/ApertarCoreApp.cpp 3744 if (!writeEjectIntent(devicePath, &intentError))
ref core src/mlv/MlvEncoder.cpp 1050 void MlvEncoder::abandon()
ref core src/lossydng/LossyDngEncoder.cpp 187 void abandon()
ref core src/audio/AudioRecordingSession.cpp 363 void AudioRecordingSession::stop(bool finalize)
check 3.4 | g++ -std=c++20 -I /home/pi/ApertarCore/src /home/pi/apertar-kb/working/tools/media_probe_test.cpp -o /tmp/media_probe_test && /tmp/media_probe_test | tail -1 | ALL CHECKS PASSED
check 4.1 | ls /home/pi/ApertarCore/src/util/MediaFault.hpp /home/pi/ApertarCore/src/util/MediaProbe.hpp /home/pi/ApertarCore/src/util/MediaIntent.hpp | wc -l | ^3$
check 4.1b | grep -c 'nvmeState == "dead"' /home/pi/ApertarCore/src/util/MediaProbe.hpp | ^1$
check 4.2 | grep -c 'classifyMediaException' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 4.4 | grep -c 'flagMediaFault' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[1-9]$
check 4.5 | grep -c 'runMediaWatcher' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[2-9]$
check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'ApertarCore media: state=' | ^[1-9][0-9]*$
check 5.2 | journalctl -u apertar-core -b --no-pager | grep -c 'recording failure: fault=media_removed' | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
