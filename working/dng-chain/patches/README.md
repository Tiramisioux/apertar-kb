# Patches from the dng-chain research session (2026-11-01)

Made on Apertar-Core `drop-frames` (92d0970) in the cloud session, each behind a knob so the A/B matrix keeps working. They are
pushed as commits on the Core branch `claude/adoring-euler-n8zi0j` (a draft pull request follows). This folder is the backup;
apply with `git am` on 92d0970 if the branch is gone. All were reviewed (`../V/PATCHES.md`): no logic bug; host checks pass.

Two series:

- `./0001..0009`: what is on the branch. Commits 0003 and 0004 carry each other's hunks (0003 holds the free-space trim and the
  mount options, 0004 the pre-roll trim; the messages are right, the split is not); 0008 is the review's fixes, 0009 the per-thread
  real-time knob. The branch was not rewritten because the session could not force-push.
- `clean-series/0001..0008`: the same final tree as eight clean commits (hunks and messages aligned, review fixes folded in).
  Preferred if the branch is ever re-created: `git checkout -b <name> 92d0970 && git am clean-series/*.patch`.

| Change | Knob to restore the old behaviour | Host check |
| --- | --- | --- |
| cdng: unpacked 16-bit and 1-byte 8-bit payloads written straight from the frame (one write(), or writev per row for a padded stride) | `APERTAR_DNG_PAYLOAD_COPY=1`; `APERTAR_DNG_WRITE_ROWS` sets the scratch chunk | `tools/dng_payload_write_test.sh`: byte-identical files on six layouts; 1 write() instead of 36 per 4K 16-bit frame |
| rec: raw copy allocated outside DngRecordingQueue::mutex_; idle pool allocated at take start; pool kept through the take, trimmed at stop (hygiene: expected effect on drops near zero, V/H5) | `APERTAR_RAW_POOL_WARM=0` | syntax check with the libcamera block on |
| media: trim after a free-space jump of 1 GiB or more without a Core delete (touch-UI deletes), and after every pre-roll clip delete (V/H6) | `APERTAR_MEDIA_TRIM=0` (whole feature) | syntax check |
| media: noatime and umask on Core's re-insert (Python watcher) mount | none | syntax check |
| scripts: `APERTAR_RT=1` runs the whole Core process under SCHED_FIFO 70 on cores 1-3 (cinemate's start); an A/B instrument, not a recommendation (V/H15) | off by default | `bash -n`; dry run |
| cdng, rec: `APERTAR_DNG_DONTNEED=writer|sync|off` (also the lossy writer); `dropped_copy_slot` always in the stats line | default `writer` (unchanged) | syntax checks; payload test |
| web: `APERTAR_WEB_PREVIEW_RECORDING_FPS` caps or pauses (0) the WebUI preview while a raw take runs; about 0.2 to 0.5 ms per frame on libcamera's thread (V/H4) | default 30 (unchanged) | syntax checks |
| rec: `APERTAR_RT_CAPTURE_PRIORITY=N` SCHED_FIFO for libcamera's completion thread alone, falling back to nice -5 (the preferred shape of the scheduling A/B, V/H15) | off by default | syntax check with the libcamera block on |

None of these has run on the Pi. First Pi test after a build: a short take, then the 10-minute 4K 25 fps Clear HDR 16-bit take
(linear, then Log) with the WebUI closed and the counters read back (`takes.sh 1 600`), per the answer page's test plan.
