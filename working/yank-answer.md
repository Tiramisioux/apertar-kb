# Apertar vs Cinemate: a recording drive pulled or unmounted mid-take

Written 2026-10-26 (cloud session) from `apertar-core@2a6f114` (f60e301 + T23/T24/T25 + phase lock),
`cinemate@d6cc93e`, `cinepi-raw@63a08d5`, `cinemate-handbook@c99ff77`, the reader reports
`working/port-raw/y1-yank-cinemate.md` and `y2-yank-core.md`, and the history/handbook pass in
`working/cinemate-lessons.md` §4. Nothing ran on a Pi. CONFIRMED = read in source; PROBABLE = inferred,
reason given; UNKNOWN = not established. Patch: `working/patches/0001-media-survive-a-yanked-or-unmounted-recording-drive.patch`
(Core `2715569`); tutorial T28.

## 1. Verdicts

| Question | Cinemate | Core at f60e301 | Core with the patch |
|---|---|---|---|
| Who notices a pull | root automounter: udev `remove`, 3 s statvfs on the mount root, 0.5 s NVMe `state=dead`, 50 ms CFE latch; cinemate `SSDMonitor` 1 s `ismount` + statvfs (y1 §1.1) | nobody until a write fails; `/proc/mounts` keeps the dead mount so `media_mounted` stays true (y2 §1.1) | media watcher thread: `/proc/mounts` exact match + statvfs on the root, 1 s idle / 250 ms recording; `media` event + `media_state` |
| Does the take stop | **no** (no `unmount_event` listener); it ends by operator, 90 %/80 % RAM watchdog or pool exhaustion (y1 §1.4) | yes for cDNG/MLV/H.264/ProRes within first failed write + ≤ 1 s; **no** for lossy DNG (async writer only logs) (y2 §1.2) | yes for every format; also when the watcher sees the root die before the next write |
| What the stop touches | nothing deliberate: lazy `umount -l`, writers keep failing (y1 §Q7) | MLV header patch, H.264 rename/copy, lossy drain, WAV finalise all reopen the dead mount (y2 §1.6) | none of those when the medium is gone |
| Loss accounting | `writeFailures` per frame, live; post-take verdict blind if the drive is gone (y1 §Q4) | `write_failures=1` then the queue is cleared uncounted; `discarded_on_stop` never incremented (y2 §1.2, KB #40) | `discarded_on_failure=`, `skipped_after_failure=`, `fault=` in the stats line; `recording_fault` in state |
| Record gate | `is_mounted` only (the space operand is a bound method, always true) (y1 §Q5) | none; a take with no drive lands on the SD card (y2 §2) | mounted + alive + free ≥ 256 MiB, one gate for socket/WebUI/buttons |
| Deliberate eject vs automounter | intent flag `/run/cinemate-storage/eject/<dev>` since `f01b6cd` | none; Core's own NVMe watcher races the UI automounter (KB #20) | `/run/apertar-media/eject/<dev>` written before unmount, cleared on remount or device removal |
| Hardware evidence of a pull during a take | **none** in 84 handbook entries (y1 §Q6) | none | T28 produces the first one |

## 2. Mechanism, numbers over prose

Kernel side (PROBABLE from Cinemate's design and y2; T28 §3 measures it): after a USB or NVMe device is
pulled, the mount stays in `/proc/mounts`; `statvfs` on the mount root returns EIO/ENODEV/ENXIO; the
clip folder's next `open()` fails with EIO or ENOENT; after someone runs `umount -l`, the path is an
empty directory on the SD card and `statvfs` succeeds again with the SD card's numbers — so "statvfs
works" alone is not "the drive is here"; the mount table must agree.

Core at f60e301, timeline of a pull during a cDNG take (CONFIRMED):
1. worker `open()`/`write()` throws `std::system_error` → `++writeFailures_`, `failRecording(e.what())`
   clears the queue (frames lost, uncounted) and stops the workers (`CC:3856-3861`, `:3958-3968` at f60e301);
2. the completion thread keeps offering frames; `hasCapacityForFrame` says no silently (`:3637-3642`);
3. up to 1 s later the App tick calls `checkRecordingFailure()` → `session_->stopRecording()`:
   gyro, H.264 (rename on the dead FS), DNG queue (`drainWrites` for lossy), ProRes, audio (`finalizeWav`
   reopens `audio_capture.raw` on the dead FS) (`:5990-6013`);
4. `recording` event with `error:"Failed to write DNG: ... Input/output error"`; WebUI toasts it on the
   next 1 s poll; `media_mounted` stays `true`.
Lossy DNG: step 1 never happens; the take runs until the operator stops it (`LossyDngEncoder.cpp:230-232`).

With the patch (CONFIRMED from the diff, not run):
- The watcher's probe fails on the mount root → `media` event `{state:"removed", errno:5}` →
  `flagMediaFault("Media removed during recording.", true)` → `checkRecordingFailure()` under
  `commandMutex_` → `stopRecording(mediumGone=true)`. Latency: ≤ 250 ms + the probe itself.
- Or the worker fails first: `classifyMediaException` → `Removed` → `failRecording(msg, Removed)` sets
  `mediumGone_`; `recordingFault()` → `Removed` → the same `stopRecording(true)`.
- `stopRecording(true)`: H.264 leaves `<clip>.mp4.writing`; `DngRecordingQueue::stop(true)` abandons
  the lossy queue (buffers returned) and the MLV worker closes without the header patch; audio closes the
  raw stream and skips `finalizeWav` and the `remove`; nothing else opens a path on the medium.
- Stats line gains `discarded_on_failure= skipped_after_failure= fault=media_removed`.

## 3. What was ported and what was not

Ported as logic: errno set and "mount root, not inside paths" rule (Cinemate `58fc7c2`); detection on
its own thread with no shared lock held during the probe (automounter `_sanity_watchdog`); write failures
counted where they happen and shown live (`8b705c8`/`5fbef52`); eject intent before unmount (`f01b6cd`);
"state changes only on real success" (the watcher publishes what it measured, the gate reads the snapshot).

Not ported, by decision:
- Lazy unmount and standby promotion: need root; Core is unprivileged and should observe mounts, not own
  them (y2 §6.7). The automounter (Apertar-UI repo, not here) is the place; T28 §8 lists the contract
  (ready file, eject flags, `umount -l` on the `media` event).
- "Keep recording and count failures" (cinepi-raw): a take that writes nothing is not a take; Core's
  stop-on-first-failure is kept and made clean.
- Pool-exhaustion stop: Core's queue-full path drops and warns (`drop[queue-full]`), already published
  as `recording_health`.

## 4. Open points and hazards (for T28 to settle)

1. errno sequence on this image for USB vs NVMe (statvfs and open) — UNKNOWN; T28 §3 records it.
2. A `close()` or `join()` stuck on a dead FUSE/NTFS mount can still hold `commandMutex_` for the
   duration of the stop; the watcher no longer adds to that, but the stop itself is not time-bounded.
   T28 §5 reads `ApertarCore recorder stop time:` after the pull. If it exceeds a few seconds on NTFS,
   the next step is a detached finaliser like the H.264 recorder's.
3. The `recording` event is still not in `publishEvent`'s always-broadcast list; while a command collects
   events the HDMI process gets it late (KB #36). The new `media` event is broadcast immediately, so the
   UI can react to the removal even then.
4. ENOENT is classified as removal. Inside Core's recorder that is right (the clip folder it created is
   gone); Cinemate's "ENOENT inside the volume is not a yank" guard concerns its *scans*, which Core does
   not run during a take.
5. `/run/apertar-media/eject` must exist and be writable by the Core user (tmpfiles.d or the automounter);
   until then the flag is skipped with one journal line and the eject behaves as before.
6. Pi 5 USB power: Core's `udisksctl power-off` on non-NVMe eject is unchanged; re-insertion of USB media
   remains manual (`mount_media`) — the automounter half of T18.

## Verification status

An adversarial verifier pass (2026-10-26) is appended to `working/port-raw/y1-yank-cinemate.md` and `y2-yank-core.md`: 0 refuted; corrections are line ranges plus two details folded in here — the MLV payload failure *is* a `std::system_error` that `writeFrame` flattens to text one level below the queue (the patch keeps its errno in `MlvEncoder::lastErrno()`), and the CFE hat byte's bit-0 polarity in Core's Python re-insert watcher is PROBABLE inverted relative to Cinemate's reading (latch open = 1). Cinemate's CFE *eject-button* path lazy-unmounts without promoting (y1 #3).
