---
datum: 2026-10-26 09:10:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T28 yanked-media-robustness
typ: digital anteckning
---

# T28. A drive pulled mid-take: detect it on the mount root, stop without touching it, say so

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-media-survive-a-yanked-or-unmounted-recording-drive.patch` is the reference, Core `2715569`). Five of the eleven touched files pass a host syntax check (`MlvEncoder.cpp`, `LossyDngEncoder.cpp`, `AudioRecordingSession.cpp`, `ApertarCoreApp.cpp`, `WebControlPage.cpp`); the three new headers pass `working/tools/media_probe_test.cpp`; `CameraController.cpp` needs libcamera and is not compiled there. Answer: `working/yank-answer.md`. Supersedes the Core half of **T18**; the automounter half stays in the UI repo. Builds **M5** (recorders), **M6** (App/UI contract).

**You will learn**
- What the kernel actually does when a recording drive is pulled (the mount stays listed; `statvfs` on the root fails with a small set of errnos) and why Cinemate tests the mount root and never paths inside it.
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
 media watcher thread (App:9151)        every 1 s idle / 250 ms recording
   probeMediaRoot(/media/RAW)           /proc/mounts exact match  +  statvfs(root)
   -> MediaSnapshot{state: none|mounted|removed|error, device, fstype, free, errno}
   -> on change: journal line, broadcast event {"event":"media",...}
   -> mounted -> removed/none while recording:
        camera_.flagMediaFault("Media removed during recording.", mediumGone=true)
        lock commandMutex_; camera_.checkRecordingFailure()   (the same path a failed write takes)

 recorder worker (CC:3928-3953)          first failed write
   catch std::exception -> classifyMediaException(e) -> MediaFault
   failRecording(mediaFaultMessage(fault, e.what()), fault)
     latch message + class; mediumGone_ if Removed; count queued frames as discarded_on_failure

 supervisor (CC:9370)                    every 1 s and on every command, and from the watcher
   checkRecordingFailure(): error = external message or recorder error
     mediumGone = external flag || recorder fault == Removed
     session_->stopRecording(mediumGone)            CC:6273
       H.264: leave <clip>.mp4.writing      DNG queue: stop(mediumDead) -> lossy abandon, MLV abandon()
       audio: stop(finalize=false)          nothing opens a path on the medium again
   recording event {..., "fault":"media_removed"}; state recording_fault, media_state
```

The errno classes (`src/util/MediaFault.hpp`): `EIO ENODEV ENXIO ENOTCONN ESTALE ENOENT` → `Removed` (Cinemate's `YANK_ERRNOS` plus ENXIO); `ENOSPC EDQUOT` → `Full`; `EROFS` → `ReadOnly`; `EACCES EPERM` → `Permission`. Only `Removed` means "do not touch the medium again".

Why the probe has its own thread: `statvfs` on a hung USB device can block for 30 s+; Cinemate skips SD cards in its watchdog for that reason (`storage-automount.py:839-843`). The App's 1 s tick holds `commandMutex_`, so the probe cannot live there (y2 §6.1).

Reading assignments: `src/util/MediaFault.hpp`, `src/util/MediaProbe.hpp` (decision function `evaluateMediaProbe`), `App:9151-9240`, `CC:4069-4090`, `CC:6273-6300`, `CC:9370-9410`.

## 3. Find it yourself

**3.1 What does the kernel do when you pull a drive?** (Pi, scratch card, **not recording**)

```bash
grep ' /media/RAW ' /proc/mounts
# pull the card / USB drive now
grep ' /media/RAW ' /proc/mounts; stat -f /media/RAW; echo "errno path: $?"; ls /media/RAW | head -2; dmesg | tail -3
```

Prediction: the mount is still listed; `stat -f` fails with `Input/output error` or `No such device`; `ls` fails too. Write down the errno text — this is the UNKNOWN the answer could not settle from source.

> [!tip]- Answer
> This is why "is it in /proc/mounts" is not "is it here", and why `isMountedPath()` alone kept `media_mounted` true. If something has already run `umount -l`, `stat -f` succeeds again with the SD card's figures: the mount table must agree, which `evaluateMediaProbe` encodes as `None` vs `Mounted` vs `Removed`.

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

**4.1 Pure headers** — `src/util/MediaFault.hpp` (errno → class, message, name), `src/util/MediaProbe.hpp` (`findMountEntry`, `evaluateMediaProbe`, `probeMediaRoot`), `src/util/MediaIntent.hpp` (eject flag under `$APERTAR_MEDIA_RUN_DIR/eject/`, default `/run/apertar-media`). Run 3.4 against your copies.

**4.2 Recorder latch** — `DngRecordingQueue` (`CC:3399`): `failRecording(error, fault)` records the class, `mediumGone_`, `discardedOnFailureFrames_ += queue_.size()` (`CC:4069`); both catch sites classify (`CC:3949`, `:4055`); lossy check after `writeDngFile` (`CC:3937`); `hasCapacityForFrame` counts `skippedAfterFailure_` (`CC:3713`); `stop(bool mediumDead)` abandons the lossy queue and lets the MLV worker `abandon()` (`CC:3560`, `:4024`); stats line gains `discarded_on_failure= skipped_after_failure= fault=`.

**4.3 Encoders** — `MlvEncoder`: `lastErrno_` set in both catch blocks, `abandon()` (`MlvEncoder.cpp:993`, `:1043`, `:1050`). `LossyDngDiskWriter`: `failures_`, `lastErrno_`, `abandon()`; statics `diskWriteFailures()`, `lastDiskWriteErrno()`, `abandonWrites()` (`LossyDngEncoder.cpp:187`, `:252`, `:398`). `AudioRecordingSession::stop(bool finalize)` (`AudioRecordingSession.cpp:358-380`). H.264 `setMediumDead()` and the `else if` around the rename (`CC:4609`, `:5133`).

**4.4 Session and controller** — `stopRecording(bool mediumGone)` passes the flag to every recorder (`CC:6273-6300`); `recordingFault()` (`CC:6530`); `checkRecordingFailure` reads the external flag and the recorder class, logs `ApertarCore recording failure: fault= medium_gone= message=`, calls `stopRecording(mediumGone)` (`CC:9370`); `flagMediaFault()` and `recordingFaultName()` (`CC:9395`, `:9405`); `recording` event gains `"fault"`.

**4.5 App** — watcher thread start/stop next to the preview thread (`App:6847`, the three failure paths and `stop()`); `runMediaWatcher`, `stopMediaWatcher`, `mediaSnapshot`, `mediaGateError` (`App:9151-9240`); gate in `handleCommand` right after the pending-writes gate (`App:9249`); `media_state`, `media_alive`, `media_device`, `media_fstype`, `recording_fault` in `/api/state` (`App:7932`) and `get_state` (`App:9401`); `"event":"media"` in the always-broadcast list (`App:11047`); eject intent in `ejectMediaAtPath` (`App:3734`) and clear in `mountMediaDeviceAtPath` (`App:3700`).

**4.6 WebUI** — record button disabled without media; `MEDIA REMOVED` status (`WebControlPage.cpp:9838`, `:9523`).

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
1. `ApertarCore media: state=removed ... errno=5` (or 19) within 250 ms of the pull, **or** `DNG write failed ... fault=media_removed errno=5` first — note which won.
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
| the take does not stop within 2 s of the pull | the worker is blocked in `write()` and the watcher's probe is blocked in `statvfs` (a hung device, not a clean removal) | wait for the kernel timeout (30–60 s on USB); note it; this is the "detached finaliser" follow-up in `yank-answer.md` §4.2 |
| `recorder stop time: 12.3s` | a `close()` or `join()` waited on the dead mount | which recorder? the preceding lines say; that finaliser still touches the medium |
| `eject intent not recorded (/run/apertar-media/eject does not exist)` | nobody created the directory | the `install -d` line in §5, or a `tmpfiles.d` rule `d /run/apertar-media/eject 0755 pi pi -` |
| record refused on a dev machine with a plain directory as media root | the gate wants a mount point | `APERTAR_MEDIA_REQUIRE_MOUNT=0` in the service environment |
| `No media mounted` right after a mount | the watcher has not cycled yet | `mediaSnapshot()` probes directly in that case; if it persists, the mount path differs from `--media` |

Undo: `git checkout -- src && git clean -f src/util/Media*.hpp`, rebuild.

## 8. What you learned, going further

- A guard that reads the present cannot defend a write that happens later: the gate and the classification at the write are both needed (handbook).
- Count every frame's fate: written, failed, discarded at the latch, skipped after it. Cinemate's post-take verdict is blind after a pull because it counts files on a drive that is gone.
- Exercise: a detached finaliser for `DngRecordingQueue::stop(true)` (the H.264 recorder already has one), so a hung `close()` never holds `commandMutex_`.
- Automounter half (UI repo): honour `/run/apertar-media/eject/<dev>` on add/change; on the Core `media` event with `state=removed`, run `umount -l`; write a ready file; then T18's "USB remount" becomes `media: state=mounted` for free.

## 9. Sources

- cinemate `src/module/ssd_monitor.py:731-771@d6cc93e` (`_handle_storage_error`), `services/storage-automount/storage-automount.py:835-864` (statvfs watchdog), `:513-531` (non-blocking `umount -l`), `:55-72` (eject flags); cinepi-raw `cinepi/dng_encoder.cpp:2352-2386@63a08d5` (write failures counted, never stopped); commits `8f49468`, `3259da7`, `1e56cb6`, `58fc7c2`, `8b705c8`, `5fbef52`, `34f8c59`, `f01b6cd`, `888093c`.
- `Apertar-Core@2715569`: `src/util/MediaFault.hpp`, `MediaProbe.hpp`, `MediaIntent.hpp`; `CC:3560`, `:3701`, `:3713`, `:3937`, `:3949`, `:4024`, `:4055`, `:4069`, `:4609`, `:5133`, `:6273`, `:6530`, `:9370`, `:9395`, `:9405`; `App:3700`, `:3734`, `:6847`, `:7932`, `:9133-9240`, `:9249`, `:9401`, `:11047`; `MlvEncoder.cpp:993`, `:1043`, `:1050`; `LossyDngEncoder.cpp:187`, `:252`, `:398`; `AudioRecordingSession.cpp:358-380`; `WebControlPage.cpp:9523`, `:9838`.
- `working/yank-answer.md`, `working/port-raw/y1-yank-cinemate.md`, `y2-yank-core.md`, `working/cinemate-lessons.md` §4, `working/tools/media_probe_test.cpp`.

%% tutor
ref core src/util/MediaFault.hpp 25 inline MediaFault classifyMediaErrno(int err)
ref core src/util/MediaProbe.hpp 101 inline MediaSnapshot evaluateMediaProbe(const MountTableEntry &entry, int statvfsErrno,
ref core src/camera/CameraController.cpp 3560 void stop(bool mediumDead = false)
ref core src/camera/CameraController.cpp 3713 bool hasCapacityForFrame(uint64_t frameIndex)
ref core src/camera/CameraController.cpp 3949 const MediaFault fault = classifyMediaException(e);
ref core src/camera/CameraController.cpp 4069 void failRecording(const std::string &error, MediaFault fault = MediaFault::Other)
ref core src/camera/CameraController.cpp 6273 void stopRecording(bool mediumGone = false)
ref core src/camera/CameraController.cpp 9370 bool CameraController::checkRecordingFailure()
ref core src/camera/CameraController.cpp 9395 bool CameraController::flagMediaFault(const std::string &message, bool mediumGone)
ref core src/ApertarCoreApp.cpp 9151 void ApertarCoreApp::runMediaWatcher()
ref core src/ApertarCoreApp.cpp 9215 std::string ApertarCoreApp::mediaGateError() const
ref core src/ApertarCoreApp.cpp 9249 if (const std::string gate = mediaGateError(); !gate.empty())
ref core src/ApertarCoreApp.cpp 3734 if (!writeEjectIntent(devicePath, &intentError))
ref core src/mlv/MlvEncoder.cpp 1050 void MlvEncoder::abandon()
ref core src/lossydng/LossyDngEncoder.cpp 187 void abandon()
ref core src/audio/AudioRecordingSession.cpp 358 void AudioRecordingSession::stop(bool finalize)
check 3.4 | g++ -std=c++20 -I /home/pi/ApertarCore/src /home/pi/apertar-kb/working/tools/media_probe_test.cpp -o /tmp/media_probe_test && /tmp/media_probe_test | tail -1 | ALL CHECKS PASSED
check 4.1 | ls /home/pi/ApertarCore/src/util/MediaFault.hpp /home/pi/ApertarCore/src/util/MediaProbe.hpp /home/pi/ApertarCore/src/util/MediaIntent.hpp | wc -l | ^3$
check 4.2 | grep -c 'classifyMediaException' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 4.4 | grep -c 'flagMediaFault' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[1-9]$
check 4.5 | grep -c 'runMediaWatcher' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[2-9]$
check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'ApertarCore media: state=' | ^[1-9][0-9]*$
check 5.2 | journalctl -u apertar-core -b --no-pager | grep -c 'recording failure: fault=media_removed' | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
