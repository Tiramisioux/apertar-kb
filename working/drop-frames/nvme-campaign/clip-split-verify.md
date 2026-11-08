# Clip split: verification on the Pi (2026-11-08)

Core `clip-split` on the Pi: `ba0658d`, then the two fixes it found, `68516f1` and `01f170c`.
Medium: the NVMe test card A936B442006AC2 (exFAT, `media_class=pi-nvme`). Mode: 4K Clear HDR 16-bit, uncompressed, 25 fps,
ladder off. The WebUI was closed and nothing else ran. Patrik ran the restarts. Everything below is **measured**.

| Step | Check | Result |
| --- | --- | --- |
| 1 | Host tests; Pi build rc 0; restart | pass (before this page) |
| 2 | Defaults: `frames_per_folder` 0, merge on, pending 0; a 20-s take | pass: C0001 flat, 503 DNGs `…000000000`-`…000000502`, WAV in the root, clip line `frames_per_folder=0`, no merge lines |
| 3 | Merge off, `frames_per_folder` 500, a 60-s take (`take3v3.sh 60 split500`) | pass: C0002 `part_000`-`part_003` (500/500/500/3), 1503 = enqueued, `dropped_queue_full` 0, `recording_dropped_frames` 0, `.parts` (`frames_per_folder=500`, `pattern=…_%09d.dng`), WAV in the root. `/api/media`: 1503 frames, 0 missing, audio, playable. Frames 0, 777 and 1502 decode (`/api/media/frame`, 42-62 ms) |
| 4 | `flatten_clip.py` dry run, `--apply`, `--unflatten 500 --apply` | pass: the dry run changed nothing; apply moved 1503 frames in 0.39 s (rename median 0.244 ms, p90 0.422 ms), flat, consecutive 0-1502, `.parts` gone; unflatten restored the 4 parts and `.parts`. Note: `--unflatten` is a dry run without `--apply` too |
| 5 | Merge on, idle | pass: `scan (switch)`, start 11 ms later, `done … files=1503 seconds=0.7 per_file_ms=0.45`; flat, `.parts` gone, pending 0 |
| 6 | `frames_per_folder` 200; a 3-min take, stop, a 60-s take 2 s into the merge | **first run failed, fixed by `68516f1`**: the pause, the take and the resume were right, but C0004 (the take made during the pause) stayed split. Second run (C0006 + C0007): `paused (recording)` 33 ms after `record_start` was sent, at 3589/4503; C0007 dropped 0 frames (1503 = written); `resumed` on stop; `done files=4503 seconds=63.8 per_file_ms=0.72`; then `scan (after pause)`, C0007 `done files=1503 seconds=0.4 per_file_ms=0.24`. Both flat |
| 7 | Restart mid-merge | pass: the merge was paused with `enter_standby` at 1256/1503 of C0004 (the root ended at 1255 and `part_006` began at 1256: the invariant held, `.parts` present). After the restart: `scan (start) pending=2`, C0005 799 files (0.20 ms/file), then C0004 resumed with the remaining 247 (0.45 ms/file); all flat and consecutive. The same restart showed **a second bug, fixed by `01f170c`**: with `clip_merge=off`, the worker started a merge at Core's start and only then saw the switch (moved 0 files: the trim held it). Re-checked after `01f170c`: no merge line at the start with the merge off, and the split clip stayed split |
| 8 | Delete mid-merge (`POST /api/media/delete`) | pass: C0008 (4502 frames, 23 parts) `paused (media delete)` at 1852/4502; delete `ok` in 0.1 s, trim 479 ms; `stopped (deleted)`; folder gone, Core up, pending 0 |
| 9 | `frames_per_folder` 0, a flat take, delete the test clips, restore | pass: C0009 flat (500); test clips C0001-C0009 deleted through the media route; restored to ladder off, 25 fps, Clear HDR 16, uncompressed, `clip_merge=on`, `frames_per_folder=0` |

Merge speed (per_file_ms is the rename time only): 0.10-0.45 ms for 500-1503 files and 0.72 ms for 4503 files. Rename cost
grows with the files already in the root, as the probe predicted (`probe-exfat-dir.md`).

Other notes:
- A 3-min take (C0005) ended itself after 32 s: `recording failure: fault=write_error … ALSA capture: Broken pipe`.
  All 799 frames were written and the merge was off, so the split code is unlikely to be the cause. **unconfirmed**: why ALSA broke.
- This base (`f4a1393`) logs no `dropped_gap_estimate`; the drop checks used `recording_dropped_frames` and enqueued = written.
- An interrupted step-2 run before the NVMe reboot may have left a short `v2flat` clip on the Samsung T7.
