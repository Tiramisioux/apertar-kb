# Apertar vs cinemate: the two DNG write chains, the residual drops, and what to change (research answer)

Written 2026-11-01 in a cloud session (Claude Code) for Patrik. Sources: Apertar-Core `drop-frames` `92d0970` (= `claude/adoring-euler-n8zi0j`),
Apertar-UI `drop-frames` `e061be8`, cinemate `main` `4990afc` (full history, 2192 commits), cinepi-raw `main` `63a08d5` (408 commits),
cinemate-handbook `c99ff77`, this KB at `1899e8d` (hardware log 2026-10-26 to 2026-11-01, `working/drop-frames/README.md`,
`working/storage-answer.md`, `working/research-30fps/`), Linux v6.12 source (mm, fs/exfat, block, drivers/nvme), upstream libcamera `c682979`.
Method: nine reader reports, three syntheses, one adversarial verifier per load-bearing claim, a review of the code changes, a completeness
critic; all in `working/dng-chain/` (`STATUS.md` is the index). Nothing ran on the Pi. Labels: **confirmed** (read in source or measured in a
log), **probable** (inferred, reason given), **unconfirmed** (the command that settles it is named).

Code changed in this session: seven commits on Apertar-Core `claude/adoring-euler-n8zi0j` (patch backup `working/dng-chain/patches/`), each behind a
knob so the A/B matrix keeps working; none has run on the Pi. Section 5 lists them.

## 0. Short answer

1. **Both of the operator's residual cases lose frames before Core's writers, not in storage.** The only 4K 50 fps SDR measurement (T34 M3,
   2026-10-28) wrote 525 MB/s with the write queue never above 3 of 12 and still lost 12 % of frames as steady single-frame capture gaps,
   unchanged with more camera buffers. The 4K 25 fps Clear HDR 16-bit losses since the trim fix are all capture gaps too (A2; the four short
   takes of 2026-10-31), with the queue at 1 to 2 of 12. A capture gap is a sensor frame the CFE never delivered because libcamera's serial
   per-frame cycle (IPA, PiSP back end, completion) ran longer than the frame period. No writer-side change in the drop-frames build (Log, the
   RAM buffer, trim, the sync policy, mount options) can touch that class. **confirmed** for the counters; the cycle mechanism is **probable**
   (measured at 30 fps Clear HDR in October, not yet at 50 fps SDR).
2. **The one structural difference that bears on the serial cycle is the tuning file, not the write chain.** cinemate's installer replaces
   libcamera's `imx585.json` with a five-algorithm file that has no `rpi.denoise` block, so its PiSP back end runs without temporal denoise (TDN).
   TDN reads and writes a full-frame reference at the raw format inside the serial back-end stage: about 29 MB per 4K SDR frame with TDN against
   10.6 without, 57.6 against 20.0 in Clear HDR 16-bit. Apertar's tuning files are in no repository; TDN is probably on. A tuning copy without the
   `tdn` blocks is a no-build test and the cheapest lever for both cases. **confirmed** for cinemate's installer and libcamera's rule; the
   Apertar side is **unconfirmed** (one grep on the Pi settles it).
3. **cinemate's "no drops" in these cases is not written down anywhere.** Its only quantified clean 4K 16-bit 25 fps record is eight 10-second
   takes with Log 12 on and the medium unstated; its only multi-minute 16-bit soak stalled; cinepi-raw itself dropped frames at 4K 16-bit
   until a preview fix on 2026-09-15; nothing at 4K 50 fps exists. cinepi-raw also moves twice Core's link bytes in SDR (a 16-bit container
   where Core uses PiSP COMP1). **confirmed** (absence in docs, handbook, both histories).
4. **The write chains are now structurally similar; where they differ, Apertar is mostly ahead on storage and behind on CPU hygiene.** Apertar
   trims the drive (cinemate never does), fsyncs for pull-safety, bounds its hold on camera buffers, and halves the SDR link bytes. It pays three
   full copies of every 16-bit frame against cinepi-raw's two, 43 syscalls per DNG against 4, a cross-CPU LRU drain per frame from a
   `POSIX_FADV_DONTNEED` that frees nothing, a 16.6 MB zero-fill under the queue mutex that libcamera's thread needs, and it runs everything at
   nice 0 where cinepi-raw runs SCHED_FIFO 70 pinned to cores 1 to 3. Each of these is now fixed or switchable (section 5). **confirmed** from
   source.
5. **The kb's reading of run A2 ("the per-frame writeback hint keeps the CFE from stalling") does not hold.** Core's writer calls
   `POSIX_FADV_DONTNEED` after every DNG, and in Linux 6.12 that call itself starts the file's writeback before failing to free the still-dirty
   pages and running `lru_add_drain_all()` on every CPU. A2 removed only a redundant `sync_file_range`; its 10 % capture loss is one unexplained run
   whose WebUI state was never recorded. Plan row 2 (no in-take sync by default) was dropped on that run. **confirmed** from the kernel source.
6. **Did the campaign make recording better?** Yes for the drive-state failure (queue-full bursts after about 0.9 TB without a trim: 71 synthetic
   runs plus one Core take each on an untrimmed and a trimmed drive), with one hole: clip deletes made from the touch UI never reach Core, so no
   trim followed them (fixed in this session). For the two named cases the build is unmeasured: no take longer than about 14 s of 4K 25 fps Clear
   HDR 16-bit and no 4K 50 fps take exists on `d44b177` or later. **confirmed**.
7. **The pre-roll has no stated mechanism and no measured effect in either stack.** cinemate's code and commits say only "warmed up"; the kb's
   COLD/WARM A/B was never run. Code-grounded side effects of Apertar's port: the deleted 0.7 GB sat untrimmed below the 1 GiB threshold (fixed in
   this session: every pre-roll delete trims), a pre-roll over 1 GiB queued a full trim right before the take, and the gap counter is blind for
   about half a second after each fps change. Honest default: leave it on only if the A/B in section 6 shows a gain; it cannot address the
   capture-gap class by any named mechanism. **confirmed** for the absence of evidence.
8. **For USB SSDs nothing is measured.** 415 MB/s (4K 16-bit 25 fps linear) exceeds what a Pi 5 USB 3 port carries; Log (311 MB/s) is marginal
   after a T7's cache; Core's writer settings do not distinguish usb-uas from pi-nvme. **probable** (published figures, no take on this rig).

## 1. The two chains, stage by stage

| Stage | cinemate + cinepi-raw (`4990afc` + `63a08d5`) | Apertar drop-frames (`92d0970`) | Does the difference bear on the drops? |
| --- | --- | --- | --- |
| Sensor link | IMX585, operator's rig at 891 MHz (1782 Mbps/lane) + RP1 overclock; cinemate ships 720 MHz | same link, same overclock | No: identical, inside the envelope at 4K 50 fps (about 70 % of the link, 80 % of the RP1 pixel rate) |
| Raw format on the link | SDR `12:U`: 16-bit container, 16.6 MB per 4K frame; Clear HDR 16:U | SDR `SRGGB12_CSI2P`, which PiSP delivers as COMP1: 8.3 MB (lossy companding; "uncompressed" SDR DNGs carry decoded COMP1 samples); Clear HDR SRGGB16 16.9 MB | Apertar moves half the SDR bytes on the CFE and in the copy |
| Tuning (ISP blocks) | installer-written `imx585.json` with five algorithms, no `rpi.denoise`: no TDN/SDN/CDN | `/home/pi/Tuning-Files/defaults-pisp/imx585[_clearHDR].json`, content unknown, probably with TDN | **Yes**: TDN runs inside the serial back-end stage (29.0 vs 10.6 MB per SDR frame; 57.6 vs 20.0 per Clear HDR frame) |
| libcamera streams | VideoRecording YUV420 1280x720 + Raw | same | No |
| Camera buffers | `--buffer-count` 10 on exFAT (8 ext4) | 8 Clear HDR, 4 SDR on exFAT (+2 only for FAT/NTFS); one request per buffer | Buffers delay the first skip under a steady cycle deficit; T34 M3 was unchanged with 8 |
| Hand-off from libcamera's thread | two dma-buf sync ioctls, a detached thread per frame, a Redis round trip; the buffer is held through `dng_save` on an encode worker | metadata, cadence check, two queue checks, a descriptor to the copy worker; no copy since T25; **plus the WebUI's 640x360 downsample when a browser streams** | Apertar's thread is lighter unless a browser is attached; the downsample is the one per-frame image pass left inside the serial cycle |
| Copies per frame | 2 (one row pass into a pooled aligned buffer with pack/LUT folded in; one `write()`) ≈ 66 MB at 16-bit | 3 (copy worker memcpy; writer row memcpy into a 491,520-byte scratch; kernel copy) ≈ 99.5 MB; 4 with Log | Probable: DRAM contention stretches the memory-bound back end (the kb measured libcamera's thread losing IPC while recording) |
| Writers and encoders | 4 encode + 2 disk threads on exFAT, pinned to cores 1-2 / 2; `nice` fails EPERM; whole process `chrt -f 70 ionice -c2 -n0 taskset -c 1-3` | 4 writers + 1 copy worker + 1 sync thread, nice 0, unpinned; completion thread nice -5 only if a drop-in nobody installs is present | Unmeasured on either stack; the kb shelved it (plan row 5); now switchable with `APERTAR_RT=1` |
| Write queue | blocking RAM permit, 0.9 x MemAvailable (about 170 frames, 6.8 s on 4 GB); the take ends when the pool is gone | 12 frames (0.48 s), drops when full; optional `ram` mode (1424 MiB measured, about 85 frames) also drops, with a 90 % safety stop | Only the queue-full class; both residual cases lose frames with the queue nearly empty |
| Files and syscalls per frame | 1 DNG; open, fadvise, one write, close (4) + a stdout line | 1 DNG; open, fadvise, 36 writes, `DONTNEED`, close, reopen + `sync_file_range` + close, and the sync thread's fsync (about 46) | Small next to the data, except `DONTNEED` (next row) |
| Page-cache policy | none (its old `DONTNEED` sat before the write; removed 2026-03) | `DONTNEED` after every DNG: starts writeback, cannot free the dirty pages, runs `lru_add_drain_all()` on every CPU; then a redundant `sync_file_range` | Probable coupling to the capture thread (kworker wake-ups on all cores 25 to 50 times a second); now switchable |
| fsync in the take | none | every written file and the folder once a second (= a whole-device metadata flush plus an NVMe FLUSH per file on exFAT: 26 a second at 25 fps); `syncfs` at stop | Measured harmless at 25 fps on the trimmed NVMe (A0 = A1); it buys pull-safety |
| Mount options, cluster size | exFAT `uid,gid,dmask=022,fmask=133,rw,noatime`; `mkfs.exfat` default 128 KiB (1 MiB tried for two days, reverted for macOS) | `uid,gid,umask=0002` + `noatime` by the UI automounter (live `findmnt` matches); three secondary mount paths lacked `noatime` (Core's fixed); 128 KiB | No difference between the rigs |
| Kernel knobs | applied by root at every RAW mount: dirty 1 GiB / 256 MiB, writeback 150 cs, scheduler none, nr_requests 512, rq_affinity 2, APST 0 | the same table in `scripts/apertar-media-tune`, opt-in (`APERTAR_MEDIA_TUNE=1`), not installed | Moot for cDNG while `DONTNEED` keeps the dirty set at 3 to 11 MB; APST is already off on the boot line |
| Trim | none (no fstrim, no discard) | fstrim at mount (927 GB in 0.47 s) and after Core deletes of 1 GiB or more; touch-UI deletes and small pre-roll deletes were not covered (fixed in this session) | **Yes**: the only robust cause found in the campaign; Apertar is ahead |
| Pre-roll | 2 s at the sensor maximum at start and at every mount, deleted; no mechanism stated | ported; pins the frame duration; 60.0 fps measured once; deletes 0.7 GB (now trimmed) | Unmeasured on both |
| Stop | no drain, no sync | drains the queue, `syncfs` (62 to 236 ms) | Not a drop mechanism; Apertar is safer on a pull |
| Previews | HDMI zero-copy; MJPEG 1280x720 every frame on a detached thread | HDMI zero-copy (EGL import); MJPEG downsample on libcamera's completion thread, JPEG on its own thread | See hand-off row |
| Drop telemetry | `droppedFrames` (timestamp gaps), `writeFailures`, buffer peak | `drop[queue-full]`, `drop[copy-slot]` (printed only when > 0; fixed), `drop[capture-gap]`, `drop[requeue-failed]`; no sequence numbers read | Both see capture gaps; neither can say who starved the CFE |

Chain facts that corrected the kb: exFAT gets 4 writers, not 2 (`MediaProfile {4,12,0}` since `0358fcf`); Core writes 34 chunked payload writes of
491,520 bytes per 16-bit frame, not one; the raw copy runs on the copy worker, not on libcamera's thread (since `351a3ee`); `takes.sh`'s
`missing` counts numbering holes only when the speed-ramp setting is off (`nextFrameIndex`), which is why A2 showed `missing=0` and T34 M3 did not.

## 2. The residual drops

### 2.1 4K Clear HDR 16-bit at 25 fps, with and without Log

| What is established | Status |
| --- | --- |
| Linear (16.6 MB per frame, 415 MB/s) is clean for 10 minutes on a trimmed drive with the WebUI closed: A0, A1 (one take each, `a40112a`), and six earlier long takes | measured |
| Log brings the frame to 12.45 MB (311 MB/s), 42 % of the measured direct-write rate of the drive; storage is not the limit with or without Log | measured size; arithmetic |
| Every residual loss is a capture gap with the queue at 1 to 2 of 12: A2 (1491 one-frame gaps in 10 min), the four short takes of 2026-10-31 (2 to 10 gaps in the first seconds, WebUI open), C0001 under the old 1 s `syncfs` | measured |
| The recording cycle at 30 fps was 36.2 ms (measured in October), so the margin at 25 fps is a few milliseconds | measured once |

The candidates, each with code behind it and none yet measured on the drop-frames build, in the order to test:

| # | Candidate | Mechanism | Settles with |
| --- | --- | --- | --- |
| 1 | The WebUI preview open during the take | `captureWebPreviewFrame` downsamples 1280x720 to 640x360 on libcamera's completion thread for every frame when a browser streams; the browser also polls state and the buffer | the two-take test (60 s closed, then open); `APERTAR_WEB_PREVIEW_RECORDING_FPS=0` as the fix |
| 2 | TDN in the tuning | a full-frame read and write inside the serial back-end stage; 37.6 of 57.6 MB per Clear HDR frame | grep the tuning for `tdn`; a copy without it; `be_cycle.py` |
| 3 | Scheduling latency | about 20 nice-0 Core threads plus a thread per HTTP client against a completion thread that is nice -5 only if the drop-in is installed | `journalctl -u apertar-core | grep 'capture scheduling'`; `APERTAR_RT=1` A/B |
| 4 | The per-frame `DONTNEED` drain and the extra copy | kworker wake-ups on every core 25 times a second; 0.83 GB/s of avoidable memory traffic | `APERTAR_DNG_DONTNEED=sync`; the direct write path (default on in the new build) |
| 5 | Cold raw pool at take start | a 16.6 MB zero-fill under the queue mutex that the completion thread takes | fixed in the new build (`APERTAR_RAW_POOL_WARM=0` restores) |

Log is not a plausible cause by itself: its LUT pass runs on the copy worker after the camera request is released (8 to 17 ms estimated, inside a
40 ms budget), and the one Log take that lost frames had the WebUI open like the lossy non-Log ones. It adds about 33 MB of memory traffic per
frame, which the direct write path takes back.

### 2.2 4K 50 fps SDR 12-bit

| What is established | Status |
| --- | --- |
| T34 M3 (2026-10-28, `4d5fdd1`, 3840x2076, two 60 s takes, untrimmed drive at 78 to 82 %): 2632 and 2616 of about 2980 frames; every loss a steady single-frame capture gap (dt 40 ms); queue-full 0; peak queue 2 to 3 of 12; write failures 0; unchanged with 8 raw buffers; 1080p50 clean; 525 MB/s written | measured |
| cinemate has no counted 4K 50 fps take; its 43.98 and "up to 50 fps" figures are `--list-cameras` ceilings; version 3.3.1 switched 4K above 25 fps to HD on SSD | confirmed (absence) |
| The link (70 %) and the RP1 pixel rate at 333 MHz (80 %) are inside their envelopes and identical on both rigs; the sensor ceiling at 891 MHz is 60 fps | arithmetic |

Reading: a serial cycle of about 22.7 ms against a 20 ms period (44 fps delivered), the same signature the kb measured for Clear HDR at 30 fps.
Scaled from the one measured back-end time, the SDR cycle with TDN on COMP1 input is 19 to 23 ms; without TDN 8 to 11 ms (**probable**). Nothing
in the drop-frames build changes this case: Log does not apply to the COMP1 stream, the RAM buffer never engages at 3 of 12, trim cannot create
frames the CFE skipped. If the capture side is fixed, uncompressed 4K 50 fps (622 MB/s at 3840x2160) sits at 85 % of the drive's measured
direct-write rate and above anything sustained so far; 10-bit (518 MB/s) or Lossless JPEG (300 to 455 MB/s, CPU-tight) are the storage-side ways
to fit; 60 fps (746 MB/s) does not fit.

## 3. Did the drop-frames changes make recording better?

| Change | Effect on drops | Evidence |
| --- | --- | --- |
| Trim at mount and after big deletes | Removes the drive-state stall (18 to 77 % lost after about 0.9 TB without a trim; a hung controller once) | 71 synthetic runs; A0 clean on a trimmed drive, 31 % lost on an untrimmed one |
| Log | 25 % smaller files; no route to the capture-gap class | one frame measured; one short take |
| RAM buffer and safety stop | A cushion for drive stalls (3.4 s instead of 0.5 s) and a clean stop instead of per-frame drops; no route to capture gaps | one safety stop measured |
| fps max from the probe, ladder, UI work | none on drops | |
| Pre-roll | unmeasured | |

So: better for the stall class whenever deletes go through Core; unmeasured for the two named cases on the shipping build. The first Pi test
after a build of this session's branch is a 10-minute 4K 25 fps Clear HDR 16-bit take (linear, then Log) with the WebUI closed and every counter
read back (`takes.sh 1 600`), then the same with the WebUI open.

## 4. The pre-roll

No author of either stack states what it warms; no measurement exists. What the code makes plausible: the raw copy pool is warm for the next
take (only without a reconfigure; the new build warms it at every take start anyway) and the exFAT bitmap and directory buffers are cached. What
it cannot do: shorten libcamera's per-frame cycle, which is where both residual cases lose frames. Its side effects in Apertar's port: the deleted
clip (0.7 GB at 4K 25 fps 16-bit or 4K lossless; 1.4 GB at 4K 12-bit 60 fps) sat untrimmed below the 1 GiB threshold (fixed: every pre-roll
delete trims), a pre-roll over 1 GiB queued a full trim right before the take (quick, 0.47 s measured, and `record_start` ends a trim after 2 s),
and the capture-gap counter is blind for max(10, buffers + 6) frames after each fps change. The A/B in section 6 (step 0b of the project page plus
a WARM-then-trim arm) is the only way to answer the question; until it runs, the honest default is off for the automatic triggers.

## 5. Improvements for Apertar on exFAT and SSDs

### 5.1 Made in this session (Apertar-Core branch `claude/adoring-euler-n8zi0j`, seven commits; `working/dng-chain/patches/`)

| Commit | Change | Knob | Why | Host check |
| --- | --- | --- | --- | --- |
| 1 | Unpacked 16-bit and 1-byte 8-bit payloads are written straight from the frame (one `write()`, or `writev` per row for a padded stride); packed layouts keep the scratch path | `APERTAR_DNG_PAYLOAD_COPY=1` restores; `APERTAR_DNG_WRITE_ROWS` sets the scratch chunk | one full copy of every Clear HDR frame less (0.83 GB/s at 25 fps); 1 write instead of 36 | `tools/dng_payload_write_test.sh`: byte-identical files on six layouts |
| 2 | Raw copies are allocated outside the queue mutex; the idle pool is allocated at take start; the pool is kept through the take and trimmed at stop | `APERTAR_RAW_POOL_WARM=0` restores | the one place the writer side could still delay libcamera's thread | syntax check with the libcamera block on |
| 3 | A trim is requested when the medium gains 1 GiB or more without a Core delete (touch-UI deletes) and after every pre-roll clip delete | `APERTAR_MEDIA_TRIM=0` (whole feature) | the touch-UI hole in the trim coverage | syntax check |
| 4 | Core's re-insert mounter (Python) mounts with `noatime` and `umask=0002` like the other paths | none | consistency | syntax check |
| 5 | `APERTAR_RT=1`: the start script runs Core under SCHED_FIFO 70 on cores 1 to 3 with `ionice -c2 -n0` (cinemate's start); `LimitRTPRIO=80` in the capture-priority drop-in | off by default | plan row 5, now testable | `bash -n`, dry run |
| 6 | `APERTAR_DNG_DONTNEED=writer|sync|off`: when a DNG's pages leave the page cache; `dropped_copy_slot` always in the stats line | default `writer` (unchanged) | the drain-per-frame finding; the hidden counter | syntax checks, payload test |
| 7 | `APERTAR_WEB_PREVIEW_RECORDING_FPS=N` caps or pauses (0) the WebUI preview while a raw take runs, through a lock-free take flag | default 30 (unchanged) | candidate 1 of section 2.1 | syntax checks |

Defaults changed by the build: the direct write path and the pool policy (both restorable), the trim coverage, the `noatime` strings. Everything
else is a knob at its old value.

### 5.2 Recommended, not done here

| Item | Why | How |
| --- | --- | --- |
| Tuning copies without `tdn` (SDR and Clear HDR) | the largest term of the serial cycle; cinemate already runs without it | copy `/home/pi/Tuning-Files/defaults-pisp/imx585*.json` without the three `tdn` objects; select with `set_tuning_file` or `APERTAR_TUNING_FILE`; later a Core option deriving it like `makeProresIspTuning` |
| Install the capture-priority drop-in | the nice -5 on the callback thread exists in code only; nothing installs `config/apertar-core-capture-priority.conf` | `sudo install -m 0644 ... /etc/systemd/system/apertar-core.service.d/`; `systemctl show apertar-core -p LimitNICE` |
| Class-aware defaults for USB SSDs | a Pi 5 USB 3 port carries about 300 to 400 MB/s; 415 MB/s linear does not fit; the writer table treats usb-uas like pi-nvme | measure first (section 6, E8); then `ram` mode with the safety stop and Log suggested for Clear HDR 16-bit on USB |
| Exact gap telemetry | Core reads no sequence numbers, so a gap cannot be attributed (CFE skip vs link loss vs Core holding buffers) | read `FrameBuffer::metadata().sequence`; log the longest `requestComplete` and the held-request high-water per take |
| Small HMB for the DRAM-less drive | `nvme.max_host_mem_size_mb=0` is Raspberry Pi's own default (CMA protection); the drive's minimum is 64 MiB; an HMB speeds the small random metadata reads, not sequential writes | `nvme.max_host_mem_size_mb=64` plus `dtoverlay=vc4-kms-v3d,cma-256`; check `dmesg` for "allocated 64 MiB host memory buffer" and `CmaFree` |
| Swap off | cinemate's installer disables it; swap was in use during takes on 2026-10-26 | `dphys-swapfile swapoff`; `vmstat 1` during a take |

### 5.3 Not recommended

| Item | Why |
| --- | --- |
| `discard` mount option | the 6.12 exfat driver issues one synchronous discard per freed 128 KiB cluster under the bitmap lock: about 1.9 million for a 15000-frame clip, inside the deleting process; Core's idle fstrim does it in one call (0.47 s measured) |
| Media-tune kernel knobs as a default | the dirty-page cushion is moot while the dirty set is 3 to 11 MB; scheduler none is the NVMe default; APST is off on the boot line; re-test only with `APERTAR_DNG_DONTNEED=off` |
| 1 MiB clusters | 8x fewer allocations per frame, but cinemate reverted it for macOS and the trim alone cured the stall at 128 KiB; a format option to A/B, not a default |
| More camera buffers as the fix | T34 M3 was unchanged with 8; buffers only delay the first skip of a steady cycle deficit |
| Removing the 1 s fsync by default | it costs one device flush per file (26 a second) but measured harmless (A0 = A1) and it is the pull-safety promise; stretch to 5 s on pi-nvme only after a 50 fps measurement |

## 6. The test plan, in order (every record carries: WebUI clients, speed-ramp setting, trim state, pre-roll state, what else runs on the Pi)

| # | Test | Reads back | Decides |
| --- | --- | --- | --- |
| E0 | Rig state: `journalctl -u apertar-core -b | grep -E 'tuning file|capture scheduling'`; `python3 -I -c` listing `rpi.denoise` keys of both tuning files; `systemctl show apertar-core -p LimitNICE -p LimitRTPRIO`; `findmnt /media/RAW`; `systemctl is-enabled fstrim.timer`; `nvme id-ctrl /dev/nvme0 | grep -E 'mn|fr|hmpre|hmmin'`; `swapon --show` | the facts every later reading depends on | which of sections 2.1's candidates apply at all |
| E1 | Two-take test: 60 s 4K 25 fps Clear HDR 16-bit uncompressed with every browser tab closed, then with the WebUI open and left alone; three pairs; `ss -tnp` during each | `dropped_gap_estimate`, `dropped_copy_slot`, `peak_queue` | candidate 1; then `APERTAR_WEB_PREVIEW_RECORDING_FPS=0` as the fix |
| E2 | Three 10-minute takes on the new build, linear, then three with Log, WebUI closed, trimmed drive, ramp off | the four counters, stop `syncfs` ms | whether the shipping build meets "done means" for the first case |
| E3 | A2 twice and A1 once, interleaved, with `/proc/vmstat` and `top -H -b -n1` per second and `ss -tnp` | the capture-gap counter | whether plan row 2 reopens |
| E4 | 50 fps SDR: preview-only delivery at 50 fps (`ipa_rate.py`); one `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` window while recording parsed by `be_cycle.py`; a counted 60 s take at 3840x2160 on a trimmed drive | delivered fps idle vs recording; back-end stage time | whether the cycle is back-end bound (then E5) |
| E5 | Tuning copies without `tdn`: `be_cycle.py` and counted 60 s takes at 4K 50 fps SDR and 4K 25 and 30 fps Clear HDR | stage times, delivered fps | candidate 2 |
| E6 | `APERTAR_RT=1` and `APERTAR_DNG_DONTNEED=sync` as separate arms of E1's open case | gaps; `bpftrace` count of `lru_add_drain_all` | candidates 3 and 4 |
| E7 | Pre-roll A/B: step 0b of the project page (COLD, WARM, SECOND) plus a WARM-then-trim arm, six pairs | the first 30 s of each counter | section 4 |
| E8 | USB SSD baseline: `lsusb -t`, `fio --direct=1 --rw=write --bs=1M --size=100G` curve, a 10-minute Log take and a 3-minute linear take | counters, `/sys/block/sdX/stat` | class-aware defaults |
| E9 | Trim acceptance: 10-minute takes with touch-UI deletes between them past one volume pass, no manual trims | `media_trim_last_unix`, `drop[queue-full]`, worst file time | commit 3 |
| E10 | A counted cinemate take of each case on the same rig and card (`droppedFrames`, DNG count vs duration, `findmnt`, the installed tuning's `md5sum`) | a baseline | the operator's comparison |

## 7. The operator's beliefs, checked

| Belief | Verdict |
| --- | --- |
| "cinemate did not drop frames in these cases" | Unrecorded for both cases; cinepi-raw dropped at 4K 16-bit until 2026-09-15; no 4K 50 fps take exists. Its two real edges are the TDN-less tuning and real-time scheduling, both now testable on Apertar |
| "Log should help against the drops" | Neutral: it cuts disk bytes by 25 % and adds a copy-worker pass; the residual losses are not storage-bound |
| "Writing and mounting can be optimised further" | Yes, and the write path now has fewer copies and syscalls; but the mount options are already right (`noatime`, 128 KiB clusters, no `discard`), and neither mounting nor writing reaches the capture-gap class |
| "Pre-roll helps" | Unknown; no mechanism names the capture-gap class; the A/B is E7 |
| "The system is better in general" | For the drive-state stall, yes (with the touch-UI hole now closed); for the two named cases, unmeasured on the shipping build |

## 8. Where the detail is

`working/dng-chain/`: `STATUS.md` (index and the 26 firm findings), `R1.md` to `R9.md` (readers), `S1.md` to `S3.md` (syntheses), `M.md`
(the 16 hypotheses), `V/` (verifications), `patches/` (the seven commits as patches with their table). The project page
`working/drop-frames/README.md` keeps the campaign's own record; this page supersedes its section 5 open questions with section 6 above.
