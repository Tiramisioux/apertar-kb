# Patches from the dng-chain research session (2026-11-01)

Made on Apertar-Core `drop-frames` (92d0970) in the cloud session, each behind a knob so the A/B matrix keeps working.
They are also pushed as commits on the Core branch `claude/adoring-euler-n8zi0j` (a draft pull request follows). Kept here as
a backup; apply with `git am` on 92d0970 if the branch is gone.

| Patch | Change | Knob to restore the old behaviour | Host check |
| --- | --- | --- | --- |
| 0001 | cdng: unpacked 16-bit and 1-byte 8-bit payloads written straight from the frame (one write(), or writev per row for a padded stride); the scratch path keeps the other layouts | `APERTAR_DNG_PAYLOAD_COPY=1`; `APERTAR_DNG_WRITE_ROWS` sets the scratch chunk | `tools/dng_payload_write_test.sh`: byte-identical files on six layouts; 1 write() instead of 36 per 4K 16-bit frame |
| 0002 | rec: raw copy allocated outside DngRecordingQueue::mutex_; the idle pool allocated at take start; the pool kept through the take (queue + workers + 2, or the ram budget) and trimmed at stop | `APERTAR_RAW_POOL_WARM=0` | syntax check with the libcamera block on (no new errors) |
| 0003 | media: trim after a free-space jump of 1 GiB or more without a Core delete (touch-UI deletes), and after every pre-roll clip delete | `APERTAR_MEDIA_TRIM=0` (whole feature) | syntax check |
| 0004 | media: noatime and umask on Core's re-insert (Python watcher) mount | none (option strings) | syntax check |
| 0006 | cdng, rec: `APERTAR_DNG_DONTNEED=writer|sync|off` chooses when a written DNG's pages leave the page cache (writer = as before, dirty pages, a cross-CPU LRU drain per frame; sync = after the file's fsync on the sync thread); `dropped_copy_slot` always in the stats line | default `writer` (unchanged) | syntax checks; payload test |
| 0007 | web: `APERTAR_WEB_PREVIEW_RECORDING_FPS` caps or pauses (0) the WebUI live preview while a raw take runs; its downsample runs on libcamera's completion thread | default 30 (unchanged) | syntax checks |
| 0005 | scripts: `APERTAR_RT=1` runs Core under SCHED_FIFO 70 on cores 1-3 with ionice (cinemate's start); LimitRTPRIO=80 in the capture-priority drop-in; README knob table | off by default | `bash -n`; dry run with a stand-in binary |

None of these has run on the Pi. The first Pi test after a build: a short take, then the 10-minute 4K 25 fps Clear HDR 16-bit take
(linear, then Log) with the WebUI closed and the counters read back (`takes.sh 1 600`), per the answer page's test plan.
