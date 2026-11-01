# Apertar vs cinemate: the two DNG write chains, the residual drops, and what to change (research answer)

Written 2026-11-01 in a cloud session (Claude Code) for Patrik. Sources: Apertar-Core `drop-frames` `92d0970` (= `claude/adoring-euler-n8zi0j`),
Apertar-UI `drop-frames` `e061be8`, cinemate `main` `4990afc` (full history, 2192 commits), cinepi-raw `main` `63a08d5` (408 commits),
cinemate-handbook `c99ff77`, this KB at `1899e8d` (hardware log 2026-10-26 to 2026-11-01, `working/drop-frames/README.md`,
`working/storage-answer.md`, `working/research-30fps/`), Linux v6.12 source (mm, fs/exfat, block, drivers/nvme), upstream libcamera `c682979`.
Method: nine reader reports, three syntheses, one adversarial verifier per load-bearing claim, a review of the code changes, a completeness
critic; all in `working/dng-chain/` (`STATUS.md` is the index). Nothing ran on the Pi. Labels: **confirmed** (read in source or measured in a
log), **probable** (inferred, reason given), **unconfirmed** (the command that settles it is named).

Code changed in this session: nine commits on Apertar-Core `claude/adoring-euler-n8zi0j` (seven changes, a review-fix commit and a per-thread
real-time knob; patch backup and a clean eight-commit series in `working/dng-chain/patches/`), each behind a knob so the A/B matrix keeps
working; all reviewed, none has run on the Pi. Section 5 lists them. Draft PR: <https://github.com/Tiramisioux/Apertar-Core/pull/3>
(head `6ef0ddc`, base `drop-frames`).

## 0. Short answer

1. **Both of the operator's residual cases lose frames before Core's writers, not in storage.** The only 4K 50 fps SDR measurement (T34 M3,
   2026-10-28) wrote 525 MB/s with the write queue never above 3 of 12 and still lost 12 % of frames as steady single-frame capture gaps,
   unchanged when the raw buffers went from 4 to 8. The 4K 25 fps Clear HDR 16-bit losses since the trim fix are all capture gaps too (A2; the
   four short takes of 2026-10-31), with the queue at 1 to 2 of 12. A capture gap is a sensor frame the CFE never delivered because no raw buffer
   was queued at its start, which happens when libcamera's serial per-frame cycle (IPA, PiSP back end, Core's completion callback) runs longer than
   the frame period. No writer-side change in the drop-frames build (Log, the RAM buffer, trim, the sync policy, mount options) can touch that
   class. Two cautions: the 50 fps measurement is from build `4d5fdd1` and has never been repeated, and on the drop-frames build the 2026-11-01
   pre-roll ran 3840x2160 at 60 fps for two seconds with zero skips (115 frames at a measured 60.0 fps), so the cycle there was at most 17 ms in
   that mode; the first 50 fps test is therefore a repeat, not a fix. **confirmed** for the counters; the cycle mechanism is **probable** (measured
   at 30 fps Clear HDR in October, inferred at 50 fps).
2. **The one candidate difference that bears on the serial cycle is the tuning file, not the write chain.** cinemate's installer (since May 2026)
   replaces libcamera's `imx585.json` with a five-algorithm file that has no `rpi.denoise` block, so a cinemate camera installed from `main` runs its
   PiSP back end without temporal denoise (TDN). TDN reads and writes a full-frame reference at the raw format inside the serial back-end stage:
   about 29 MB per 4K SDR frame with TDN against 10.6 without, 57.6 against 20.0 in Clear HDR 16-bit. Two cautions: the operator's own colour cinemate
   rig ran the fork's full tuning with TDN on at its last documented state (handbook 2026-08-31), so TDN may not be what separated the stacks when
   he shot with cinemate; and "largest removable term" assumes the back-end time scales with its bytes, which was never measured (one data point at
   30 fps). Apertar's `imx585_clearHDR.json` is in no repository but almost certainly carries `tdn` (no PiSP tuning of that class lacks it). A
   tuning copy without the `tdn` blocks, selected with `set_tuning_file` (the `APERTAR_TUNING_FILE` variable is dead: Core overrides it at start,
   kb upstream-issues #10), is a no-build test and the cheapest lever for both cases. **confirmed** for cinemate's installer and libcamera's rule;
   the effect is **probable**; the Apertar tuning content is **unconfirmed** (one grep on the Pi settles it).
3. **cinemate's "no drops" in these cases has no counted record anywhere.** Its only quantified clean 4K 16-bit 25 fps record is eight 10-second
   takes with Log 12 on and the medium unstated; its only multi-minute 16-bit soak stalled (mono rig, NTFS over FUSE); cinepi-raw had a one-day
   regression with 208 drop events at 4K 16-bit on 2026-09-15; nothing at 4K 50 fps exists, and cinemate's own May 2026 profile table (shipped in
   3.3.1, removed in August) rated 4K 12-bit at 38 fps as the sustainable no-drop rate on a CFE/NVMe exFAT drive, 40 on ext4, 25 on a USB SSD.
   cinepi-raw also moves twice Core's CFE bytes into memory in SDR (a 16-bit container where Core uses PiSP COMP1; the CSI-2 link bytes are the
   same). **confirmed** (absence in docs, handbook, both histories; uncounted operator confirmations exist).
4. **The write chains are now structurally similar; where they differ, Apertar is mostly ahead on storage and behind on CPU hygiene.** Apertar
   trims the drive (cinemate never does), fsyncs for pull-safety, bounds its hold on camera buffers, and halves the SDR link bytes. It pays three
   full copies of every 16-bit frame against cinepi-raw's two, 43 syscalls per DNG against 4, a cross-CPU LRU drain per frame from a
   `POSIX_FADV_DONTNEED` that frees nothing, and it runs its writers at nice 0 and its capture callback at nice -5 where cinepi-raw runs SCHED_FIFO 70
   pinned to cores 1 to 3. Each of these is now fixed or switchable (section 5). One suspected item fell in verification: the 16.6 MB zero-fill the
   copy worker did under the queue mutex can only delay libcamera's thread when the copy worker is already most of a frame behind, which no take has
   shown; it is fixed as hygiene, not as a cause. **confirmed** from source.
5. **The kb's reading of run A2 ("the per-frame writeback hint keeps the CFE from stalling") does not hold.** Core's writer calls
   `POSIX_FADV_DONTNEED` after every DNG, and in Linux 6.12 that call itself starts the file's writeback before failing to free the still-dirty
   pages and running `lru_add_drain_all()` on every CPU. A2 removed only a redundant `sync_file_range`; its 10 % capture loss is one unexplained run
   whose WebUI state was never recorded, and whose `missing=0` beside 1491 gaps means the speed-ramp setting was probably on (frame numbering counts
   frames only in that mode), an unrecorded confounder of the whole A0 to A2 matrix. Plan row 2 (no in-take sync by default) was dropped on that run.
   **confirmed** from the kernel source.
6. **Did the campaign make recording better?** Yes for the drive-state failure (queue-full bursts after about 0.9 TB without a trim: 71 synthetic
   runs plus one Core take each on an untrimmed and a trimmed drive), with one hole: clip deletes made from the touch UI never reach Core, so no
   trim followed them (fixed in this session); and the gain is by inference, since the trim-after-delete path was never run across a full drive
   pass. For the two named cases the build is unmeasured: on `d44b177` and later there is no 4K 25 fps Clear HDR 16-bit take at all (the four short
   lossy takes and the clean 3-minute lossless take of 2026-10-31 ran on the pre-squash builds of that evening) and no 4K 50 fps take. **confirmed**.
7. **The pre-roll has no stated mechanism and no measured effect in either stack.** cinemate's code, docs and eight commits say only "warmed up"
   and "priming"; the handbook has no entry; the kb's COLD/WARM A/B was never run. What a pre-roll can warm on this rig: only the raw copy pool for
   the first quarter second of the first take (the new build does that at every take start anyway); the exFAT allocation bitmap is pinned at mount,
   the CPU governor's boost decays within five seconds, APST is off, and the page cache is dropped per frame. Side effects of Apertar's port: its
   deleted clip (0.69 GB lossless, 0.85 GB Clear HDR 16-bit, 1.5 GB for 4K 12-bit uncompressed at the pre-roll's 60 fps) sat untrimmed below the
   1 GiB threshold in the first two cases and queued a full trim before the first take in the third (fixed in this session: every pre-roll delete
   trims, 0.47 s each); the automatic trigger fires at every remount, so the kb's written COLD arm would run a pre-roll by itself; record is refused
   for three to five seconds at Core start while it runs; in uncompressed 12-bit it exceeds the drive at 60 fps and reports "(N dropped)" every
   time. It cannot address the capture-gap class by any named mechanism. Honest default: the automatic triggers off until the A/B in section 6
   shows a gain. **confirmed** for the absence of evidence.
8. **For USB SSDs nothing is measured.** 415 MB/s (4K 16-bit 25 fps linear) exceeds what a Pi 5 USB 3 port carries; Log (311 MB/s) is marginal
   after a T7's cache; Core's writer settings do not distinguish usb-uas from pi-nvme. **probable** (published figures, no take on this rig).

## 1. The two chains, stage by stage

| Stage | cinemate + cinepi-raw (`4990afc` + `63a08d5`) | Apertar drop-frames (`92d0970`) | Does the difference bear on the drops? |
| --- | --- | --- | --- |
| Sensor link | IMX585, operator's rig at 891 MHz (1782 Mbps/lane) + RP1 overclock; cinemate ships 720 MHz | same link, same overclock | No: identical link, inside the envelope at 4K 50 fps (about 70 % of the link; the sensor line rate is 80 % of the Apertar fork's software pixel-rate cap of 646.7 Mpix/s and 89 % of cinemate's 580); the two libcamera forks cap differently in software, neither cap has been measured against the hardware |
| Raw format on the link | SDR `12:U`: 16-bit container, 16.6 MB per 4K frame; Clear HDR 16:U | SDR `SRGGB12_CSI2P`, which PiSP delivers as COMP1: 8.3 MB (lossy companding; "uncompressed" SDR DNGs carry decoded COMP1 samples); Clear HDR SRGGB16 16.9 MB | Apertar moves half the SDR bytes on the CFE and in the copy |
| Tuning (ISP blocks) | an install from `main` writes an `imx585.json` with five algorithms and no `rpi.denoise` (no TDN/SDN/CDN); the operator's colour rig still ran the fork's full tuning with TDN on 2026-08-31 | `/home/pi/Tuning-Files/defaults-pisp/imx585[_clearHDR].json`, content unknown, almost certainly with TDN | **Probably**: TDN runs inside the serial back-end stage (29.0 vs 10.6 MB per SDR frame; 57.6 vs 20.0 per Clear HDR frame); the time-per-byte scaling is unmeasured |
| libcamera streams | VideoRecording YUV420 1280x720 + Raw | same | No |
| Camera buffers | `--buffer-count` 10 on exFAT (8 ext4) | 8 Clear HDR, 4 SDR on exFAT (+2 only for FAT/NTFS); one request per buffer | Buffers delay the first skip under a steady cycle deficit; T34 M3 was unchanged with 8 |
| Hand-off from libcamera's thread | two dma-buf sync ioctls, a detached thread per frame, a Redis round trip; the buffer is held through `dng_save` on an encode worker | metadata, cadence check, two queue checks, a descriptor to the copy worker; no copy since T25; **plus the WebUI's 640x360 downsample when a browser streams** | Apertar's thread is lighter unless a browser is attached; the downsample is the one per-frame image pass left inside the serial cycle |
| Copies per frame | 2 (one row pass into a pooled aligned buffer with pack/LUT folded in; one `write()`) ≈ 66 MB at 16-bit | 3 (copy worker memcpy; writer row memcpy into a 491,520-byte scratch; kernel copy) ≈ 99.5 MB; 4 with Log | Probable: DRAM contention stretches the memory-bound back end (the kb measured libcamera's thread losing IPC while recording); the byte figures are an upper bound (the scratch is cache-resident) and nothing isolates the third copy |
| Writers and encoders | 4 encode + 2 disk threads on exFAT, pinned to cores 1-2 / 2; `nice` fails EPERM; whole process `chrt -f 70 ionice -c2 -n0 taskset -c 1-3` | 4 writers + 1 copy worker + 1 sync thread, nice 0, unpinned; completion thread nice -5 only if a drop-in nobody installs is present | Unmeasured on either stack; the kb shelved it (plan row 5); now switchable with `APERTAR_RT=1` |
| Write queue | blocking RAM permit, 0.9 x MemAvailable (about 170 frames, 6.8 s on 4 GB); the take ends when the pool is gone | 12 frames (0.48 s), drops when full; optional `ram` mode (1424 MiB measured, about 85 frames) also drops, with a 90 % safety stop | Only the queue-full class; both residual cases lose frames with the queue nearly empty |
| Files and syscalls per frame | 1 DNG; open, fadvise, one write, close (4) + a stdout line | 1 DNG; open, fadvise, 36 writes, `DONTNEED`, close, reopen + `sync_file_range` + close, and the sync thread's fsync (about 46) | Small next to the data, except `DONTNEED` (next row) |
| Page-cache policy | none (its old `DONTNEED` sat before the write; removed 2026-03) | `DONTNEED` after every DNG: starts writeback, cannot free the dirty pages, runs `lru_add_drain_all()` on every CPU; then a redundant `sync_file_range` | Probable coupling to the capture thread (kworker wake-ups on all cores 25 to 50 times a second); now switchable |
| fsync in the take | none | every written cDNG file and the folder once a second (26 a second at 25 fps; none for lossy DNG): on exFAT each writes the dirty metadata buffers of the device, holds the superblock lock across a synchronous directory-entry write that the writers' block mapping waits on, and issues a pre-flush that becomes an NVMe FLUSH only if the drive advertises a volatile write cache (never read on this drive); `syncfs` at stop | No measured cost at 25 fps on the trimmed NVMe (A0 = A1, one run each); it buys pull-safety; a longer interval does not reduce the per-file count |
| Mount options, cluster size | exFAT `uid,gid,dmask=022,fmask=133,rw,noatime`; `mkfs.exfat` default 128 KiB (1 MiB tried for two days, reverted for macOS) | `uid,gid,umask=0002` + `noatime` by the UI automounter (live `findmnt` matches); three secondary mount paths lacked `noatime` (Core's fixed); 128 KiB | No difference between the rigs |
| Kernel knobs | applied by root at every RAW mount: dirty 1 GiB / 256 MiB, writeback 150 cs, scheduler none, nr_requests 512, rq_affinity 2, APST 0 | the same table in `scripts/apertar-media-tune`, opt-in (`APERTAR_MEDIA_TUNE=1`), not installed | Moot for cDNG while `DONTNEED` keeps the dirty set at 3 to 11 MB; APST is already off on the boot line |
| Trim | none (no fstrim, no discard) | fstrim at mount (927 GB in 0.47 s) and after Core deletes of 1 GiB or more; touch-UI deletes and small pre-roll deletes were not covered (fixed in this session) | **Yes**: the only robust cause found in the campaign; Apertar is ahead |
| Pre-roll | 2 s at the sensor maximum at start and at every mount, deleted; no mechanism stated | ported; pins the frame duration; 60.0 fps measured once; deletes 0.7 GB (now trimmed) | Unmeasured on both |
| Stop | no drain, no sync | drains the queue, `syncfs` (62 to 236 ms) | Not a drop mechanism; Apertar is safer on a pull |
| Previews | HDMI zero-copy; MJPEG 1280x720 every frame on a detached thread | HDMI zero-copy (EGL import); MJPEG downsample on libcamera's completion thread, JPEG on its own thread | See hand-off row |
| Drop telemetry | `droppedFrames` (timestamp gaps), `writeFailures`, buffer peak | `drop[queue-full]`, `drop[copy-slot]` (printed only when > 0; fixed), `drop[capture-gap]`, `drop[requeue-failed]`; no sequence numbers read | Both see capture gaps; neither can say who starved the CFE |

Chain facts that corrected the kb: exFAT gets 4 writers, not 2 (`MediaProfile {4,12,0}` since `0358fcf`); Core writes 34 chunked payload writes of
491,520 bytes per 16-bit frame, not one; the raw copy runs on the copy worker, not on libcamera's thread (since `351a3ee`); frame numbering is
time-based with the speed-ramp setting off (a capture gap leaves a hole that `takes.sh` counts as `missing`) and count-based with it on (never a
hole), so T34 M3's `missing=355` equals its gap estimate while A2's `missing=0` beside 1491 gaps says the ramp was on: the kb's finding 7
("`takes.sh` cannot see capture gaps") is wrong as a general rule, and the A0 to A2 matrix probably ran with the ramp on.

## 2. The residual drops

### 2.1 4K Clear HDR 16-bit at 25 fps, with and without Log

| What is established | Status |
| --- | --- |
| Linear (16.6 MB per frame, 415 MB/s) is clean for 10 minutes on a trimmed drive with the WebUI closed: A0, A1 (one take each, `a40112a`), and six earlier long takes; none of them on the shipping build | measured |
| Log brings the frame to 12.45 MB (311 MB/s), 42 % of the measured direct-write rate of the drive; storage is not the limit with or without Log | measured size; arithmetic |
| Every residual loss is a capture gap with the queue at 1 to 2 of 12: A2 (1491 one-frame gaps in 10 min), the four short takes of 2026-10-31 (2 to 10 gaps in the first seconds, WebUI open), C0001 under the old 1 s `syncfs` | measured |
| The recording cycle at 30 fps was 36.2 ms (measured in October), so the margin at 25 fps is a few milliseconds | measured once |

The four short takes lost 2 to 10 frames each with the first gap two to four seconds in, which with the kb's own buffer-slack model means a
steady deficit of 1.3 to 2.7 ms per frame (6 to 20 ms in the Log take), not a constant small cost. The candidates, each with code behind it and
none yet measured on the drop-frames build, in the order to test:

| # | Candidate | Mechanism | Size | Settles with |
| --- | --- | --- | --- | --- |
| 1 | TDN in the tuning | a full-frame read and write inside the serial back-end stage: 37.6 of 57.6 MB per Clear HDR frame; the back end is the stage the kb measured stretching from 13 to 35 ms under recording load | the largest term by bytes; its time-per-byte is unmeasured | grep both tuning files for `tdn`; a copy without it selected with `set_tuning_file`; `be_cycle.py` before and after |
| 2 | The writers' own memory and writeback traffic | the kb saw a buffered `dd` alone cost capture frames while a direct-I/O `dd` did not, and libcamera's thread losing instructions per cycle while recording; Core moves each frame through memory three times (four with Log) and kicks a cross-CPU LRU drain per frame | measured for recording as a whole, never isolated | the direct write path and `APERTAR_DNG_DONTNEED=sync` in the new build; later the kb's O_DIRECT patch (T24) |
| 3 | The first take after a (re)configure or a reboot | three of four first takes were lossy on 2026-10-26; the 2026-10-31 takes came minutes after a reboot | unknown | discard the first take after any reconfigure in every series; compare first and second takes |
| 4 | The WebUI preview open during the take | `captureWebPreviewFrame` downsamples 1280x720 to 640x360 on libcamera's completion thread for every frame when a browser streams; the page also polls state and the buffer | about 0.2 ms per frame idle in the kb's 2026-10-25 profile, 0.3 to 0.5 ms recording: too small alone, real as a contributor | the three-client test (E1); `APERTAR_WEB_PREVIEW_RECORDING_FPS=10` or `0` as the mitigation |
| 5 | Scheduling latency | about 20 nice-0 Core threads plus a thread per HTTP client against a nice -5 completion thread (the drop-in is recorded present on the Pi since 2026-10-25) | tens to hundreds of microseconds expected, about 2 ms tail, only when all four cores are busy | `journalctl -u apertar-core | grep 'capture scheduling'`; `APERTAR_RT_CAPTURE_PRIORITY=70` (per-thread FIFO) A/B |

Removed in verification: the cold raw pool (its allocation runs on the copy worker right after the frame's own callback and ends long before the
next one; fixed as hygiene, not a cause) and exFAT free-space fragmentation (with four concurrent writers every frame file is a FAT chain on every
take; the 2026-10-30 stall stacks were that normal path waiting on a stalled drive).

Log is not a plausible cause by itself: its LUT pass runs on the copy worker after the camera request is released (8 to 17 ms estimated, inside a
40 ms budget), and the one Log take that lost frames had the WebUI open like the lossy non-Log ones. It adds about 33 MB of memory traffic per
frame, which the direct write path takes back; whether that traffic matters is candidate 2.

### 2.2 4K 50 fps SDR 12-bit

| What is established | Status |
| --- | --- |
| T34 M3 (2026-10-28, `4d5fdd1`, 3840x2076, two 60 s takes, untrimmed drive at 78 to 82 %): 2632 and 2616 of about 2980 frames; every loss a steady single-frame capture gap (dt 40 ms); queue-full 0; peak queue 2 to 3 of 12; write failures 0; unchanged when the raw buffers went from 4 to 8 (CFE pools of 6 and 10 with libcamera's two internal buffers); 1080p50 clean; 525 MB/s written | measured |
| On the drop-frames build the only faster datum is the 2026-11-01 pre-roll: 3840x2160 12-bit lossless at a pinned 60 fps for 2 s, 115 frames, measured 60.0 fps from the sensor timestamps, so zero skips and a mean cycle of at most 17 ms in that mode | measured once, 2 s |
| cinemate has no counted 4K 50 fps take; its 43.98 and "up to 50 fps" figures are `--list-cameras` ceilings; version 3.3.1 switched 4K above 25 fps to HD on SSD | confirmed (absence) |
| The link (70 %) and the Apertar fork's software pixel-rate cap at 333 MHz (the sensor line rate is 80 % of it) are inside their envelopes; the link is identical on both rigs, the two libcamera forks cap the pixel rate differently (646.7 vs 580 Mpix/s); the sensor ceiling at 891 MHz is 60 fps | arithmetic |

Reading: in T34 M3 a serial cycle of about 22.7 ms against a 20 ms period (44 fps delivered), the same signature the kb measured for Clear HDR at
30 fps. Scaled from the one measured back-end time, the SDR cycle with TDN on COMP1 input would be 19 to 23 ms, without TDN 8 to 11 ms
(**probable**, and in tension with the pre-roll's 17 ms bound on the new build, so the estimate or the build differs). Nothing in the
drop-frames build changes this case by design, but whether it still reproduces there is an open measurement: Log does not apply to the COMP1 stream, the RAM buffer never engages at 3 of 12, trim cannot create
frames the CFE skipped. If the capture side is fixed, uncompressed 4K 50 fps (622 MB/s at 3840x2160) sits at 85 % of the drive's once-measured
direct-write rate (733 MB/s) and above the 525 MB/s delivered so far (a floor set by the capture loss, not a drive ceiling); 10-bit (518 MB/s) or
Lossless JPEG (300 to 455 MB/s, CPU-tight) are the storage-side ways to fit; 60 fps (746 MB/s) does not fit. No counted take backs this
marginality yet.

## 3. Did the drop-frames changes make recording better?

| Change | Effect on drops | Evidence |
| --- | --- | --- |
| Trim at mount and after big deletes | Removes the drive-state stall (18 to 77 % lost after about 0.9 TB without a trim; a hung controller once); by inference: fstrim cures the stall and Core runs fstrim at mount; the trim-after-delete path was never run across a full drive pass | 71 synthetic runs; A0 clean on a trimmed drive, 31 % lost on a never-trimmed one |
| Log | 25 % smaller files; no route to the capture-gap class | one frame measured; one short take |
| RAM buffer and safety stop | A cushion for drive stalls (3.4 s instead of 0.5 s) and a clean stop instead of per-frame drops; no route to capture gaps | one safety stop measured |
| fps max from the probe, ladder, UI work | none on drops | |
| Pre-roll | unmeasured | |

So: better for the stall class whenever deletes go through Core; unmeasured for the two named cases on the shipping build. The first Pi test
after a build of this session's branch is a 10-minute 4K 25 fps Clear HDR 16-bit take (linear, then Log) with the WebUI closed and every counter
read back (`takes.sh 1 600`), then the same with the WebUI open.

## 4. The pre-roll

No author of either stack states what it warms; no measurement exists (verified: cinemate's module, docs and eight commits; the handbook; the kb).
What the code makes plausible: only the raw copy pool for the first quarter second of the first take after a reconfigure, which the new build
warms at every take start anyway. Not plausible on this rig: exFAT metadata (the allocation bitmap is pinned in memory at mount and a contiguous
file never touches the FAT), the CPU governor (ondemand, its boost decays within five seconds), the NVMe power state (APST is off on the boot
line; a wake is one latency the 12-frame queue absorbs), the page cache (dropped per frame). It cannot shorten libcamera's per-frame cycle, where
both residual cases lose frames. Side effects of Apertar's port: the deleted clip (0.69 GB lossless, 0.85 GB Clear HDR 16-bit, 1.5 GB for 4K
12-bit uncompressed at 60 fps) sat untrimmed below the 1 GiB threshold in the first two cases and queued a full trim before the first take in
the third (fixed in this session: every pre-roll delete trims, 0.47 s each); the automatic trigger runs at every remount and Core start, so the
project page's COLD arm would run a pre-roll by itself and record is refused for three to five seconds after a start; in uncompressed 12-bit the
60 fps pre-roll exceeds the drive and reports "(N dropped)" every time; in the Clear HDR 16-bit 25 fps case the pre-roll runs at the user's fps,
so there is no gap-counter blind window there (0.24 s in the 50 fps case). The A/B in section 6 (E7) is the only way to answer the question;
until it runs, the honest default is off for the automatic triggers.

## 5. Improvements for Apertar on exFAT and SSDs

### 5.1 Made in this session (Apertar-Core branch `claude/adoring-euler-n8zi0j`, nine commits; `working/dng-chain/patches/`)

| Commit | Change | Knob | Why | Host check |
| --- | --- | --- | --- | --- |
| 1 | Unpacked 16-bit and 1-byte 8-bit payloads are written straight from the frame (one `write()`, or `writev` per row for a padded stride); packed layouts keep the scratch path | `APERTAR_DNG_PAYLOAD_COPY=1` restores; `APERTAR_DNG_WRITE_ROWS` sets the scratch chunk | one full copy of every Clear HDR frame less (0.83 GB/s at 25 fps); 1 write instead of 36 | `tools/dng_payload_write_test.sh`: byte-identical files on six layouts |
| 2 | Raw copies are allocated outside the queue mutex; the idle pool is allocated at take start; the pool is kept through the take and trimmed at stop | `APERTAR_RAW_POOL_WARM=0` restores | hygiene: verification (V/H5) shows the held mutex reaches libcamera's thread only when the copy worker already lags by most of a frame; expected effect on drops near zero | syntax check with the libcamera block on |
| 3 | A trim is requested when the medium gains 1 GiB or more without a Core delete (touch-UI deletes) and after every pre-roll clip delete | `APERTAR_MEDIA_TRIM=0` (whole feature) | the touch-UI hole in the trim coverage | syntax check |
| 4 | Core's re-insert mounter (Python) mounts with `noatime` and `umask=0002` like the other paths | none | consistency | syntax check |
| 5 | `APERTAR_RT=1`: the start script runs Core under SCHED_FIFO 70 on cores 1 to 3 with `ionice -c2 -n0` (cinemate's start); `LimitRTPRIO=80` in the capture-priority drop-in | off by default | plan row 5, now testable | `bash -n`, dry run |
| 6 | `APERTAR_DNG_DONTNEED=writer|sync|off`: when a DNG's pages leave the page cache; `dropped_copy_slot` always in the stats line | default `writer` (unchanged) | the drain-per-frame finding; the hidden counter | syntax checks, payload test |
| 7 | `APERTAR_WEB_PREVIEW_RECORDING_FPS=N` caps or pauses (0) the WebUI preview while a raw take runs, through a lock-free take flag | default 30 (unchanged) | candidate 4 of section 2.1 (0.2 to 0.5 ms per frame: a mitigation, not the fix) | syntax checks |
| 8 | Fixes from the review (`V/PATCHES.md`): the duplicated `dropped_copy_slot` line, a NaN guard in the web-preview parser, the accessor's placement, the lossy writer honouring `APERTAR_DNG_DONTNEED`; the message records that commits 3 and 4 carry each other's hunks | none | review | all host checks |
| 9 | `APERTAR_RT_CAPTURE_PRIORITY=N`: SCHED_FIFO for libcamera's completion thread alone, set from Core, falling back to nice -5 | off by default | the right shape of the scheduling A/B (V/H15): whole-process FIFO lets FIFO writers block the capture thread | syntax check with the libcamera block on |

Defaults changed by the build: the direct write path and the pool policy (both restorable), the trim coverage, the `noatime` strings, the stats
field. Everything else is a knob at its old value. The branch's commits 3 and 4 have their hunks swapped relative to their messages (a split error;
commit 8's message says so); `patches/clean-series/` holds the same tree as eight clean commits for a re-created branch. A force-push of
that series was blocked by the session's permission policy, so the PR carries the additive nine-commit history.

### 5.2 Recommended, not done here

| Item | Why | How |
| --- | --- | --- |
| Tuning copies without `tdn` (SDR and Clear HDR) | the largest candidate term of the serial cycle; a cinemate installed from `main` runs without it | copy `/home/pi/Tuning-Files/defaults-pisp/imx585*.json` without the three `tdn` objects; select with `set_tuning_file` (or the UI's tuning picker; `APERTAR_TUNING_FILE` is dead, Core overrides it at start); later a Core option deriving it like `makeProresIspTuning` |
| Confirm the capture-priority drop-in | no repository installs `config/apertar-core-capture-priority.conf`, but the kb's architecture notes record it present on the Pi (`systemctl cat`, 2026-10-25); the new `LimitRTPRIO=80` line needs a reinstall | `systemctl show apertar-core -p LimitNICE -p LimitRTPRIO` (expect 25 and 80 after the reinstall); `journalctl -u apertar-core -b | grep 'capture scheduling'` |
| Class-aware defaults for USB SSDs | a Pi 5 USB 3 port carries about 300 to 400 MB/s; 415 MB/s linear does not fit; the writer table treats usb-uas like pi-nvme | measure first (section 6, E8); then `ram` mode with the safety stop and Log suggested for Clear HDR 16-bit on USB |
| Exact gap telemetry | Core reads no sequence numbers, so a gap cannot be attributed (CFE skip vs link loss vs Core holding buffers) | read `FrameBuffer::metadata().sequence`; log the longest `requestComplete` and the held-request high-water per take |
| Host memory buffer for the DRAM-less drive (second-order) | `nvme.max_host_mem_size_mb=0` is Raspberry Pi's own device-tree default (after the HMB exhausted the 64 MiB CMA); the drive's minimum is 64 MiB, so only 64 or more does anything (rpi-6.18's 32 MiB default would still give it none); an HMB caches the mapping table and speeds small random reads by a third to a half, not sequential writes; both rigs ran without it; bounded at about 10 ms per fully chained frame, so not a drop mechanism | append `nvme.max_host_mem_size_mb=64` to `cmdline.txt` (the last occurrence wins; the token cannot be removed from the device tree) plus `dtoverlay=vc4-kms-v3d,cma-256`; `dmesg | grep -i 'host memory'`; `CmaFree`; camera and display still start |
| Swap off | cinemate's installer disables it; swap was in use during takes on 2026-10-26 | `dphys-swapfile swapoff`; `vmstat 1` during a take |
| The kb's O_DIRECT patch (T24) rebased onto the copy worker | the only change that removes the page-cache copy and all page-cache work (the `DONTNEED` drain, reclaim); the kb saw a direct-I/O `dd` cost no capture frames where a buffered one did | after E2 and E6; exFAT needs the file extended first (`ftruncate` to the final size, block-aligned IFD-first layout) or direct I/O silently falls back to buffered |

### 5.3 Not recommended

| Item | Why |
| --- | --- |
| `discard` mount option | the 6.12 exfat driver issues one synchronous discard per freed 128 KiB cluster under the bitmap lock and the superblock lock, so a concurrent take's writes block too: about 1.9 million discards for a 15000-frame clip, inside the deleting process; Core's idle fstrim does it in one call (0.47 s measured); a `remount,discard` cannot even enable it on a live exFAT mount |
| Media-tune kernel knobs as a default | the dirty-page cushion is moot while the dirty set is 3 to 11 MB; scheduler none is the NVMe default; APST is off on the boot line; re-test only with `APERTAR_DNG_DONTNEED=off` |
| 1 MiB clusters | 8x fewer allocations per frame, but cinemate reverted it for macOS and the trim alone cured the stall at 128 KiB; with four concurrent writers every frame file is a FAT chain at either cluster size (verified in the 6.12 driver: the 2026-10-30 stall stacks were that normal path waiting on a stalled drive, not fragmentation); a format option to A/B, not a default |
| One writer to keep files contiguous | a single writer would give contiguous files (no FAT chain, no FAT reads), but two writers already lost frames in October (C0106); a diagnostic (`APERTAR_CDNG_UNCOMPRESSED_WORKERS=1` then `filefrag -v`), not a setting |
| More camera buffers as the fix | T34 M3 was unchanged with 8; buffers only delay the first skip of a steady cycle deficit |
| Removing the 1 s fsync by default | it costs a synchronous directory-entry write per file under the superblock lock (26 a second) and a flush only if the drive has a volatile write cache, but no cost was measured (A0 = A1) and it is the pull-safety promise; a longer interval does not reduce the per-file count, only bursts it; decide after a 50 fps measurement with `/sys/block/nvme0n1/stat` flush counts |

## 6. The test plan, in order (every record carries: WebUI clients, speed-ramp setting, trim state, pre-roll state, what else runs on the Pi)

| # | Test | Reads back | Decides |
| --- | --- | --- | --- |
| E0 | Rig state: `journalctl -u apertar-core -b | grep -E 'tuning file|capture scheduling|pixel-rate cap'`; `grep -c '"tdn"' /home/pi/Tuning-Files/defaults-pisp/imx585*.json`; `systemctl show apertar-core -p LimitNICE -p LimitRTPRIO`; `findmnt /media/RAW`; `systemctl is-enabled fstrim.timer`; `nvme id-ctrl /dev/nvme0 | grep -E 'mn|fr|hmpre|hmmin|vwc'`; `cat /sys/block/nvme0n1/queue/write_cache`; `swapon --show`; `get_state` for `fps_speed_ramp` (read before every take; never judge drops from `takes.sh missing` again, use `dropped_gap_estimate` and frames against WAV seconds x fps) | the facts every later reading depends on | which of sections 2.1's candidates apply at all |
| E1 | Three-client test: 60 s 4K 25 fps Clear HDR 16-bit uncompressed with (a) no client, (b) only `curl -sN http://<pi>:8080/preview.mjpeg > /dev/null` attached, (c) the WebUI page open; interleaved three times; the first take after any reconfigure discarded; `ss -tnp` before each; `usample.py` on the CameraManager thread during one (b) | `dropped_gap_estimate`, `dropped_copy_slot`, `peak_queue`; the downsample's share | candidates 3 and 4; (c) lossy but (b) clean = page polling; (a) lossy = environment; then `APERTAR_WEB_PREVIEW_RECORDING_FPS=10` as the mitigation |
| E2 | Three 10-minute takes on the new build, linear, then three with Log, WebUI closed, trimmed drive, ramp off | the four counters, stop `syncfs` ms | whether the shipping build meets "done means" for the first case |
| E3 | A2 twice and A1 once, interleaved, with `/proc/vmstat` and `top -H -b -n1` per second and `ss -tnp` | the capture-gap counter | whether plan row 2 reopens |
| E4 | 50 fps SDR: first a repeat of T34 M3 on the new build (60 s at 3840x2076 and at 3840x2160, uncompressed, trimmed drive, ramp off, WebUI closed, then with a browser), reading `dropped_gap_estimate`, `dropped_copy_slot` and the journal's `camera configured ... packing=` and `RAW buffers` lines; if it still loses frames: preview-only delivery at 50 fps (`ipa_rate.py`, or `storage_preroll` at 50 fps) and one `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` window while recording parsed by `be_cycle.py` | whether the loss reproduces at all; delivered fps idle vs recording; back-end stage time | whether the case is still open and, if so, whether the cycle is back-end bound (then E5) |
| E5 | Tuning copies without `tdn`: `be_cycle.py` and counted 60 s takes at 4K 50 fps SDR and 4K 25 and 30 fps Clear HDR | stage times, delivered fps | candidate 2 |
| E6 | `APERTAR_RT_CAPTURE_PRIORITY=70` (per-thread FIFO; whole-process `APERTAR_RT=1` only as a control) and `APERTAR_DNG_DONTNEED=sync` as separate arms of E1's lossy case; `/proc/<pid>/task/<tid>/schedstat` of the CameraManager thread for the run-queue wait per frame | gaps; wait per frame; `bpftrace` count of `lru_add_drain_all` | candidates 2 and 5 |
| E7 | Pre-roll A/B: `APERTAR_STORAGE_PREROLL=0` in the unit for the whole series (else every restart and remount runs one by itself), Core restarted before every take, three arms interleaved six times: C = record 120 s; P = manual `storage_preroll`, wait for `storage_preroll_active=false` plus 5 s, record; S = a 2 s take at the user's fps, 5 s, record; both operator modes | `drop[capture-gap]` bucketed by seconds since start, `storage_preroll_last`, `media_trim_last_*`, `scaling_cur_freq` for the first 5 s | P differs from C beyond C's spread in at least 5 of 6 pairs and beyond S: an effect of its own; P like S unlike C: a first-take effect; all alike: no effect, default off |
| E8 | USB SSD baseline: `lsusb -t`, `fio --direct=1 --rw=write --bs=1M --size=100G` curve, a 10-minute Log take and a 3-minute linear take | counters, `/sys/block/sdX/stat` | class-aware defaults |
| E9 | Trim acceptance: 10-minute takes with touch-UI deletes between them past one volume pass, no manual trims | `media_trim_last_unix`, `drop[queue-full]`, worst file time | commit 3 |
| E10 | A counted cinemate take of each case on the same rig and card (`droppedFrames`, DNG count vs duration, `findmnt`, the installed tuning's `md5sum`) | a baseline | the operator's comparison |

## 7. The operator's beliefs, checked

| Belief | Verdict |
| --- | --- |
| "cinemate did not drop frames in these cases" | No counted record for either case; cinemate's own May 2026 table put sustainable 4K 12-bit at 38 fps on NVMe exFAT; no 4K 50 fps take exists. Its two candidate edges are the TDN-less tuning of a fresh install (the operator's own rig ran with TDN on 2026-08-31) and real-time scheduling, both now testable on Apertar |
| "Log should help against the drops" | Neutral: it cuts disk bytes by 25 % and adds a copy-worker pass; the residual losses are not storage-bound |
| "Writing and mounting can be optimised further" | Yes, and the write path now has fewer copies and syscalls; but the mount options are already right (`noatime`, 128 KiB clusters, no `discard`), and neither mounting nor writing reaches the capture-gap class |
| "Pre-roll helps" | Unknown; no mechanism names the capture-gap class, the only code-grounded warm-up (the raw pool) is now done at every take start, and the automatic pre-roll carries small costs; the A/B is E7 |
| "The system is better in general" | For the drive-state stall, yes (with the touch-UI hole now closed); for the two named cases, unmeasured on the shipping build |

## 8. Where the detail is

`working/dng-chain/`: `STATUS.md` (index and the 26 firm findings), `R1.md` to `R9.md` (readers), `S1.md` to `S3.md` (syntheses), `M.md`
(the 16 hypotheses), `V/` (one verification per hypothesis, `VERDICTS.md` the summary table, `PATCHES.md` the code review), `patches/` (the
nine commits as patches, and `clean-series/` with the same tree as eight clean commits). Verification outcome: confirmed H3 (DONTNEED and A2),
H6 (touch-UI deletes), H7 (discard), H9 (no cinemate baseline), H10 (pre-roll), H13 (HMB), H16 (unmeasured on the shipping build); plausible with
corrections H1 (50 fps upstream of the writers), H2 (TDN), H8 (copies), H11 (fsync), H12 (envelopes), H15 (scheduling); refuted as causes H4
(WebUI downsample, too small alone), H5 (cold pool), H14 (fragmentation after a volume pass). The project page
`working/drop-frames/README.md` keeps the campaign's own record; this page supersedes its section 5 open questions with section 6 above.
