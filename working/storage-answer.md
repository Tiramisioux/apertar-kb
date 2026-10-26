# Apertar vs Cinemate: writing raw to different kinds of storage media

Written 2026-10-26 (cloud session) from `cinemate@d6cc93e` (`services/storage-automount/storage-automount.py`,
`src/module/{ssd_monitor,storage_profiles,storage_preroll}.py`), `cinepi-raw@63a08d5`, `cinemate-handbook@c99ff77`,
`apertar-core` at the `clearhdr-fixes` branch (f60e301 + T23/T24/T25 + phase lock + T28), the reader reports
`working/port-raw/s1-storage-cinemate.md` and `s2-storage-core.md`, and the history pass in `working/cinemate-lessons.md`
§3 and §5. Nothing ran on a Pi. CONFIRMED = read in source; PROBABLE = inferred, reason given; UNKNOWN = not
established. Patches: `0001-media-profile-the-recording-medium-...` (T29, Core `75e9f57`) and `0001-audio-writer-thread-...` (T30, Core
`25397cd`); the pure header passes `working/tools/media_profile_test.cpp`; the audio session passes a host syntax check.

## 1. Verdicts

| Question | Cinemate | Core at f60e301 | Core with the patches |
|---|---|---|---|
| What does the camera know about its drive | connection class from udev ancestry + uevent + I2C hat probe; filesystem from `findmnt`/`blkid`, normalised; both published (s1 §1) | a volume label mapped to a display string; `/proc/mounts` type and options parsed and thrown away twice (s2 §1a-b) | `MediaProfile`: class {pi-nvme, usb-uas, usb-storage, sd-card, other, unknown} from sysfs, filesystem {ext4, exfat, vfat, ntfs, ntfs-fuse, other}; in the clip line, `/api/state` and the `media` event |
| What follows the medium | disk workers 8/2, buffers 8/10, affinity, nice, mount options; kernel: scheduler, `nr_requests`, `rq_affinity`, `vm.dirty_*`, NVMe APST, for the RAW target only (s1 §2, §5) | nothing: workers, queue, nice, buffers depend on the recording *format* only (s2 §4) | uncompressed-cDNG workers (ext4 4, exFAT/NTFS 2), queue depth (12/16), two extra raw camera buffers on FAT-family/NTFS, direct I/O off on FUSE; kernel knobs through a root helper, applied on mount and restored on loss; `noatime` on Core's own mounts |
| Audio under storage load | capture thread never touches disk (writer thread), 2 s ring on the record path, wall-clock reconciliation, SCHED_FIFO on its own core (`ffb61fd`, `5021ba3`, `6ccfabd`, `521dc72`) | reader thread writes `audio_capture.raw` on the medium itself; 100 ms ALSA buffer; discontinuities > 10 ms padded (the reconciliation exists) (lessons §3) | writer thread with a RAM queue between the reader and the raw file; 1 s capture buffer with a 10 ms period on the record path; padding unchanged |
| Pre-roll warm-up | 2 s take at sensor max fps on mount/startup, then deleted; mechanism never stated, never measured (s1 §3) | none | none; T29 measures first-take vs second-take loss before anything is built |
| Sustained numbers on record | 317–334 MB/s 4K 16-bit at 25 fps, 0 drops, queue never past 2 (docs, medium unstated); NTFS-over-FUSE stalls at ~355 MB/s after 15–22 s (handbook) | T22's measurement (Clear HDR drops) | T29 repeats `takes.sh` per medium and filesystem, profile on and forced off |

## 2. Mechanism, numbers over prose

- Core's writer path at HEAD (CONFIRMED): uncompressed cDNG opens `O_DIRECT` (T24) with an `EINVAL` fallback to
  buffered + `DONTNEED`; workers `max(2, min(4, threads))`; queue 12; raw buffers 4, 8 in Clear HDR (T23); the raw
  copy on a worker (T25). None of it reads the medium (s2 §4-5). A FUSE ntfs-3g mount rejects `O_DIRECT` at write
  time, so every take there pays one fallback; exFAT/FAT allocate a directory entry per frame, which is why
  Cinemate found them spikier than ext4 (`a61a589`) and gave them more sensor buffers.
- Kernel side (CONFIRMED from Cinemate's table, PROBABLE as to effect on this rig): with `O_DIRECT` DNGs the page
  cache carries only MLV, H.264, audio and WAV; `vm.dirty_bytes`/`dirty_background_bytes` still bound how much of
  that a yank takes with it and how long a `balance_dirty_pages` stall can get on a USB SSD past its SLC cache
  (`d7a8d2b`: 90 s into a 4K take, figure unmeasured). Cinemate's starting points are in the helper's table.
- Audio (CONFIRMED): the Core reader thread calls `rawStream_.write()` into the clip folder on the medium
  (`AudioRecordingSession.cpp:472` at f60e301) with a 100 ms ALSA buffer (`TimestampedAudioCapture.cpp:189-190`).
  Cinemate's exFAT finding (`ffb61fd`): `write()` blocks for hundreds of ms under DNG pressure, the ring overruns,
  samples are lost; Core would pad the hole with silence (correct length, audible gap) and its whole-take drift
  measurement would see fewer frames per second (lessons §3). The port moves the write to its own thread and
  gives the record path a 1 s buffer while keeping a 10 ms period so the VU meter and `htimestamp` granularity do
  not change.

## 3. What was ported and what was not

Ported as logic: the two-axis classification and the rule that only the recording target gets global knobs
(`c8f06c9`); writer topology and buffer count per filesystem; direct I/O off where the medium cannot take it;
"probes must be able to say no" (`888093c`, `34f8c59`); writer thread and large ring for audio; `noatime`.

Not ported, by decision:
- Pre-roll: no stated mechanism and no measurement anywhere in Cinemate (s1 §3). T29 §5 does the experiment
  (first take after mount vs second) and only then decides.
- Statvfs-delta "write speed": Core already has a real probe (fio/dd) that nothing consumes; T29 wires its result
  into the state as a number and compares it with the estimated bytes/s, nothing more.
- `chrt`/`ionice`/`taskset` for the whole process and CPU isolation kernel args: Core has `LimitNICE=-5` and
  worker nice values; without a measurement showing scheduling as the bottleneck (T22/T25 point at the write
  path) these stay out.
- Standby drives, RAW-label arbitration, fsck on mount: automounter concerns (UI repo).

## 3b. Amendments after the critic pass (2026-10-26)

- The helper also writes `nvme_core.default_ps_max_latency_us = 0` for the Pi-NVMe class (APST exit latency mid-take is a stall; Cinemate sets it for every NVMe class) and saves/restores it like the rest (critic S5).
- The watcher applies the profile and calls the helper only after the loss handling, so a `sudo` round-trip never delays an abort (critic S11).
- Configure-time buffer counts and `record_start` use the watcher's cached snapshot (critic Y8).
- `takes.sh` now prints `write_failures=`, `discarded_on_failure=`, `fault=`, `media_class=`, `media_fs=`, `direct_io=`, the phase-lock stats and the audio writer's peak backlog, so the pass criteria in T27–T30 are measured (critic S7).
- Stated, not changed: Core's own `ProresEncoder.cpp` asserts that the image ships `/etc/sysctl.d/60-apertar-writeback.conf` with `vm.dirty_bytes` 128 MB (critic S2) — the helper's save-once keeps whatever is there and restores to it; T29 §3.1 reads the file. The buffer-count bump is read at configure, so a medium swapped after configure keeps the old count until the next reconfigure or restart (critic S8); the boot mounter's options (`media-RAW.service`/UI automounter) are not Core's and `noatime` reaches only `mount_media` (critic S9). RT priority, CPU affinity and `isolcpus` are deferred, not rejected: T22/T25 point at the write path, and Cinemate's own lesson is that affinity tables need a check before they are safe (`7551a16`); revisit with a measurement of scheduling latency (critic S6).

## 4. Open points and hazards (for T29/T30 to settle)

1. Filesystem on the rig's `/media/RAW` — never recorded (T22 asks for `findmnt`); the profile table is unmeasured
   until `takes.sh` has run per medium with the profile on and `APERTAR_CDNG_UNCOMPRESSED_WORKERS`/`APERTAR_CDNG_QUEUE_FRAMES`
   forced to the old values.
2. Whether exFAT's extra two buffers help or merely cost 34 MB — compare `missing=` and `peak_queue` with
   `APERTAR_RAW_CAMERA_BUFFERS=8` forced.
3. The helper's `dirty_bytes` values matter only for buffered writers now; measure with `writeback_watch.py`
   whether `nr_dirty` ever approaches them during a Clear HDR take.
4. Audio: count `ApertarCore audio discontinuity:` lines per take on exFAT before/after T30; compare
   `measured_drift_ppm` between an idle 2K take and a Clear HDR take (a difference is loss, not clock).
5. USB topology on Pi 5: mic and USB SSD on different xHCI controllers (`lsusb -t`).
6. The buffer-count bump reads the medium at configure time; changing media while the camera is configured keeps
   the old count until the next reconfigure (as in Cinemate, where a profile change restarts the recorder).

## Verification status

The verifier pass for `s1-storage-cinemate.md` and `s2-storage-core.md` had not completed when this was written; the readers' citations in §1–2 are theirs, unverified beyond my own reading of the lines used for the patch.
