# R2: the lever inventory for the unsupervised NVMe drop-frame campaign

Written 2026-11-08 from the KB at `/home/user/apertar-kb` (HEAD `b4fea20`). Every number carries the KB's own label
(**confirmed** = read in code or on the Pi; **measured** = counted on the owner's camera; **probable** = inferred, reason
given; **unconfirmed** = not established; **derived** = arithmetic from measured values; **estimated** = a model). Labels are
copied, never upgraded. Owner's own measurements come first; CineMate and web figures are marked as such.

Rig (fixed): Pi 5 / CM5 4 GB, IMX585 at 891 MHz, Corsair MP600 Mini 1 TB (FW `ERFM11.1`), exFAT 128 KiB clusters on
`/media/RAW`, PCIe Gen 3 x1, libcamera qbc `7e9fef0`, driver `cd548ef` (`working/dng-chain-feasibility.md:3-5`;
`working/drop-frames/tests-2026-11/preregistration.md:585-596`). The state the Pi was left in on 2026-11-04 ~21:00: Core
`9b5ea14` running, mode 4K Clear HDR 16-bit 25 fps uncompressed cDNG, **ladder off**, tuning automatic, `buffer=ram`,
`compaction_proactiveness` 20, link 891 MHz, no `/run` drop-in, drive holding `warm.bin` and User's
`cDNG_26_11_04_20322419_C0001`, smart-log `critical_warning` 0, 3 % used, Pi left on (`preregistration.md:778-786`).

## 0. Two facts the campaign design must start from

1. **The binary on disk is not the binary that runs.** The running Core is the campaign build `9b5ea14` (branch renamed
   `drop-frames-campaign` on the Pi), but on 2026-11-04 21:29 the Pi's checkout was switched to the clean `drop-frames`
   (= `cinemate-port` `a344376`) and **built into `~/ApertarCore-build`**, which is what `/home/pi/start-apertar-core.sh`
   starts (`APERTAR_CORE_BIN` default `/home/pi/ApertarCore-build/apertar-core`, `architecture/config.md:431`). So the next
   `systemctl restart apertar-core`, `apertar-b1-arm sync`, `apertar-e4-helper disarm` or reboot brings up `a344376`, not
   `9b5ea14` (`working/handoff-drop-frames-tier2.md:94-98`; `fork-log.md:150`; confirmed as a KB statement, not re-read on
   the Pi). The two binaries have different lever sets (section 1). The first act of the campaign is to decide the binary and,
   if `9b5ea14` is wanted, `git switch drop-frames-campaign` + `cmake --build ~/ApertarCore-build -j2` **before any take**
   (`working/drop-frames/README.md:220`: never during a take).
2. **Root access for an unsupervised run exists only through the two helpers Patrik installed**, and he was asked to remove
   them: `/etc/sudoers.d/apertar-e4` allows exactly `apertar-e4-helper arm|disarm|compact0|compact-restore|smartlog|status|
   reboot|poweroff` and `apertar-b1-arm sync|sync --trace-buffer|save|restore` (`working/tools/drop-frames-2026-11-01/
   e4-sudoers:4-17`; removal line `e4-install.txt:13`; "User removes them" `handoff-drop-frames-tier2.md:92-93`). Whether
   they are still installed is **unconfirmed** (`sudo -n /usr/local/libexec/apertar-e4-helper status` settles it). Every
   lever marked "sudo" below is reachable unsupervised only through those exact words, or through a new helper Patrik
   reviews and installs first.

## 1. Which binary has which lever

| Feature | `drop-frames-campaign` `9b5ea14` (running) | clean `drop-frames` = `cinemate-port` `a344376` (built, not run) | Source |
| --- | --- | --- | --- |
| `APERTAR_DNG_DONTNEED` env, default `sync` | yes (`adac040`) | yes (`f5ac28b`) | `fork-log.md:138,155` |
| `~/apertar-media-tune.conf` + `/run` override + `scripts/apertar-tune` | yes (`2edc6d0`, `46d0e8c`; running since 2026-11-02 23:1x, journal `media tune:` lines seen 11-03) | **not among its four commits: probable absent** (`apertar-tune` would change nothing) | `fork-log.md:140-141,150-157`; `preregistration.md:204-206` |
| Trim | automatic, `APERTAR_MEDIA_TRIM=0` to disable (env only) | automatic, plus socket `set_media_trim` (`00f2327`), WebUI Performance card | `fork-log.md:154`; `README.md:59` |
| Log (`set_cdng_log`) | yes (`d44b177`) | **probable absent** | `fork-log.md:136`; section 1 lineage |
| `[storage] buffer=ram|frames`, safety stop, buffer bar | yes | **probable absent** (original 12-frame queue only) | same |
| Storage pre-roll (`[media] preroll`) | yes (runs at every Core start) | **absent** ("pre-roll parts left out") | `fork-log.md:154` |
| `recording_dropped_frames` in `get_state` (what `take3v3.sh` stop-on-drop reads) | yes (`64bbbaa`) | **probable absent** | `fork-log.md:136-137`; `take3v3.sh:32,88` |
| fps max from the sensor probe (4K SDR 60), `APERTAR_FPS_LIMIT=table`, `APERTAR_LOSSLESS_FPS_LIMIT` | yes (`d44b177`) | **probable absent**: table rule `min(table, probe)` gives 4K SDR 30 | `README.md:51,65,75`; `lessons/hardware-log.md:826-835` |
| HDR16 4K fps ceiling | 30 (`31d5418` removed the 25-fps back-end cap; `fps_max` 30 measured 2026-11-04) | **probable 25** (`b5847c7` cap on `cinemate-port`; `adac040` alone caps at 25, `tier1-prep-2026-11-03.md:212`) | `fork-log.md:145`; `tier1-prep-2026-11-03.md:209-213` |
| TDN off | tuning copy via `set_tuning_file` only | `set_preview_tdn` (`6bd002b`): Core strips `tdn` from the resolved tuning into `~/.cache/apertar-core/tuning`; **default off = TDN stripped by default**; state `preview_tdn`, `tuning_file_active` | `fork-log.md:156` |
| Phase lock `set_fps_phase_lock` (default off) | yes (`80ddac1`) | yes, plus the WebUI Performance card (`a344376`) | `fork-log.md:35,157` |
| `APERTAR_WEB_PREVIEW_RECORDING_FPS`, `APERTAR_RT_CAPTURE_PRIORITY` | yes (PRs #3-#5 via `dd00206`) | **probable absent** (not named in the four commits) | `fork-log.md:136`; `working/dng-chain/patches/README.md:21-24` |
| Speed ramp, Mode Ladder, Clear HDR exposure rules, Controls/GPIO | yes | yes (`controls` lineage) | `fork-log.md:103-129` |

A quick discriminator over the socket: `get_state` carrying `cdng_log` = campaign binary; carrying `preview_tdn` = clean
binary (field names from `README.md:60` and `fork-log.md:156`; **probable** as a test, not yet run).

## 2. The lever table

Columns: how it is switched (and whether it needs sudo, a Core restart, or a camera reconfigure); the measured or probable
effect on dropped frames with its source; interactions; cost in bytes written or risk. "Drop-in" = a systemd
`Environment=` file under `/run/systemd/system/apertar-core.service.d/` (tmpfs, gone at reboot) or `/etc/...` (permanent);
both need root. "socket" = `python3 -I working/tools/core.py <cmd> key=value` as pi, no sudo.

### 2a. Storage tuning (the write path)

| Lever | What it does | Switch; sudo / restart / reconfigure | Measured or probable effect (source, label) | Interactions | Cost |
| --- | --- | --- | --- | --- | --- |
| `dontneed` = `sync` / `writer` / `off` | When a written DNG's pages leave the page cache: `writer` right after the write (pages still dirty: frees nothing, a cross-CPU LRU drain per frame), `sync` on the once-a-second sync thread after the file's `fsync` (cDNG only), `off` never (`working/dng-chain/patches/0008-...patch:46`, the Core README row) | file key `[default] dontneed=` in `~/apertar-media-tune.conf` or `scripts/apertar-tune set dontneed=X` (override, pi, no sudo); env `APERTAR_DNG_DONTNEED` wins (drop-in, sudo). **Read once per process: Core restart** (`architecture/config.md:404,409`) | **B1, measured, p = 1/36**: per-unit lost (P1 + P2, 3 + 3 min) writer 407, 320, 252, 232 vs sync 48, 108, 73, 80; manipulation check passed (`preregistration.md:111-116`). `off` never run ("the risk arm": hands the pages to kswapd, `dng-chain-feasibility.md:257`) | `sync` needs the sync thread (`sync_ms` > 0) (`lessons/hardware-log.md:1040`); lossy DNG has no sync thread and behaves as `off` (patch row above; `inspection-2026-11-02.md:468-472`) | no bytes. `sync` holds ~415-622 MB more page cache for ~1 s (`dng-chain-feasibility.md:257`, estimated) |
| `writeback` on/off | per-DNG `sync_file_range` right after the write (`architecture/core.md:11.2 table`) | file key / `APERTAR_DNG_WRITEBACK`; once per process: restart | **A2, measured, one 10-min run**: off = 1491 one-frame capture gaps (13,503 of ~15,000) with the queue at 1/12; A1 (on, sync 0) clean (`hardware-log.md:757-777`) | precondition for every arm | none; off = known bad |
| `sync_ms` 0-60000 | the 1 s `fsync` of each DNG finished that second, then the folder; `syncfs` at stop stays (`core.md` §11.2) | file key / `APERTAR_MEDIA_SYNC_MS`; **read at each take start** (`config.md:411`): no restart for the file/override key | A1 (`=0`): 15,000 / 15,000, 0 in every counter on a trimmed drive (measured, one run, `hardware-log.md:757-764`) | must stay > 0 under `dontneed=sync`; pull-safety (a pulled card keeps all but ~1 s) | none |
| `raw_buffers` 3-16 (absolute) | CFE raw buffers = libcamera requests in flight (T23: one request per buffer) | file key / `APERTAR_RAW_CAMERA_BUFFERS`; read at each camera configure (`config.md:412`): a reconfigure or restart. The `/etc` drop-in `zz-ladder-buffers.conf` that pinned 8 is gone: Core's environ held only `LIBCAMERA_LOG_LEVELS` at the 11-04 restores (`handoff-drop-frames-tier1.md:182`; `preregistration.md:778-780`), so the file's 8 rules (probable) | 8 vs 4: 5 of 5 vs 4 of 5 short 25-fps takes clean (T23, measured, `recipe.md:43`). **16: worse**, 26 + 123 lost vs the 8-buffer reference 2 + 108, user space holds ~11.5 of 16, losses without CFE starvation (measured, n = 1 unit, `preregistration.md:190-215`). 12: 10.5 % lost, no effect (11-01, under `writer`, `hardware-log.md:997`). M3 at 50 fps: 355 vs 358 lost at 4 vs 8 (measured, `hardware-log.md:591-594`) | every lost frame in B1 was CFE raw-buffer starvation (`findings-2026-11-02.md:7-29`); more buffers only fill up behind a slow back end | +16.9 MB cached heap per buffer; no bytes |
| `extra_raw_buffers` 0-8 | media-profile extra buffers (+2 on FAT/NTFS, 0 on exFAT/ext4) | file key only; media change (remount/restart) | never measured on this NVMe exFAT rig (`working/storage-answer.md:68-69` open point 2) | adds to `raw_buffers` | as above |
| `workers` 1-8 (uncompressed cDNG) | writer threads; exFAT profile 4 | file key / `APERTAR_CDNG_UNCOMPRESSED_WORKERS`; media change | "writer count did not matter" in the synthetic set (measured, `README.md:45` finding 4); T29's 2 writers / queue 16 / +2 buffers lost 166 in 3 min (C0106) on a 77-81 %-full card (confounded) (`fork-log.md:47`; `recipe.md:47`) | lossless uses min(8, cores+1) = 5, lossy 4 at nice +5 (`working/compare-raw/a4-core-writer.md:192-193,239-240`) | none |
| `queue` 4-64 frames | the write queue cap in `frames` mode (12 uncompressed = ~0.5 s at 16.9 MB; 24 lossless/lossy) | file key / `APERTAR_CDNG_QUEUE_FRAMES`; media change | A3 (64) never run; "a bigger queue cannot help capture gaps: the frames are lost before the queue" (`hardware-log.md:771-773`). Clean takes peak 2/12; the 30-fps t1 reached 11/12 (`findings-evening4-supervised-2026-11-04.md:29`) | superseded by the byte budget in `buffer=ram` | RAM |
| `kernel_tune` on/off (`apertar-media-tune` helper) | root helper applied at mount: `vm.dirty_bytes`/`dirty_background_bytes` cushion, scheduler none, `nr_requests`, `rq_affinity`, NVMe APST 0 (`README.md:249`; `storage-answer.md:58`) | file key / `APERTAR_MEDIA_TUNE=1`; **the helper is not installed** (`config.md:459`; `fork-log.md:44`): installing it is sudo + a sudoers rule; the sysctls can also be set by hand (sudo) | T22: dirty knobs no difference (lossless-encoder-bound takes, `hardware-log.md:64-95`, measured). Take #80: `sync` + `vm.dirty_bytes` 1 GiB, `dirty_background_bytes` 256 MiB, `min_free_kbytes` 64 MiB on an **empty** drive: 0 / 15,025, kswapd 0 (measured; two things changed at once, `night-2026-11-01.md:42`). B3's cells never run under `sync` (`preregistration.md` B3 table empty). APST and ASPM were already off by boot args on 2026-10-26 (`hardware-log.md:296-297`) | reclaim is a co-factor, not the cause (`findings-2026-11-03.md:61`) | none in bytes; `/proc/sys` values vanish at reboot |
| `[storage] buffer=ram` / `frames` + safety stop | `ram`: byte-budget queue 0.6 x MemAvailable - 512 MiB, cap 0.5 x MemTotal (measured budget 1,424 MiB on this board); take ends itself (clean stop) at `buffer_stop_percent` 90 % (`README.md:63-64`; `hardware-log.md:871-875`) | socket `set_buffer_mode value=ram|frames` (edits the `[storage]` key, read at each take start, no sudo); env `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_BUFFER_STOP_PERCENT` win (`config.md:115-119,445,449`) | **not a cure for capture gaps**: `frames` 590 + 181 lost vs the ram reference 2 + 108, back end at 40-44 ms in both (measured, n = 1, `preregistration.md:298-313`); cushion 3.2 s against a complete stall vs 0.64 s in frames mode (derived, `dng-chain-feasibility.md:262`); first real safety stop fired at 1289 of 1424 MiB, flush ~3 s (measured) | in `ram` mode an encoder-bound arm (lossless HDR16) ends itself after ~19 s instead of dropping for the whole take (`README.md:52`): the wear limiter for bad arms. Current state `ram` (restore list) | ~1.4 GiB RAM / CMA headroom; campaign binary only |
| Media trim | Core trims `/media/RAW` at mount, after a Core delete batch >= 1 GiB, after a free-space jump >= 1 GiB (touch-UI deletes), after each pre-roll delete; never in a take; `record_start` waits <= 2 s for a running trim then ends it (`README.md:59`; `working/dng-chain/patches/README.md:19`) | always on; `APERTAR_MEDIA_TRIM=0` (drop-in, sudo) on `9b5ea14`; socket `set_media_trim` only on `a344376`. Manual `sudo fstrim -v /media/RAW` | untrimmed drive stalls after ~0.9 TB written: 18-77 % lost, one controller hang; trim before every run 12 of 12 clean; 927 GB trimmed in 0.47 s (measured, `hardware-log.md:701-734,813-818`) | with "no clearing after every take" the allocation cursor approaches one pass of the volume inside the 30-min series (section 3); a trim after the last big delete and before the long takes is the precondition (state `media_trim_last_unix`). **No undelete after a trim** | none in bytes; FTL erase work is the drive's own |
| Storage pre-roll (`[media] preroll`) | a 2 s take at the mode's maximum fps through the real write path, deleted, trim requested: at Core start, card insert, once after a format, or manual `storage_preroll` (`README.md:72`) | socket `set_storage_preroll` edits the key, read at each request (no restart, no sudo); env `APERTAR_STORAGE_PREROLL=0|1` beats the file (drop-in, sudo); `preroll_seconds` 1-10 (`config.md:125-126`) | warm-vs-cold A/B never run (`README.md:303-335`, step 0b). Measured: SDR12 lossless pre-roll 60.0 fps, 115 frames, 688 MB written and deleted (`hardware-log.md:842-856`); it is also the source of `estimated_capacity_fps` for lossless (HDR16 16.84, SDR12 48.13 at 33 fps) (`findings-2026-11-03.md:47`; `findings-2026-11-04.md:64`) | `e3-unit.sh:19-21` waits up to 10 min for the pre-roll journal line and exits NOT STARTED without it: switching the pre-roll off breaks the unit loop as written. The feasibility A0 protocol asks `APERTAR_STORAGE_PREROLL=0` for a series ("every restart runs a 60 fps burst with its own drops", `dng-chain-feasibility.md:200`) | **~0.7-1.0 GB written and deleted per Core restart** (0.7 GB measured at 60 fps SDR12 lossless; HDR16 at 30 fps x 2 s x 16.6 MB ~ 1.0 GB, derived). Campaign binary only |
| O_DIRECT for the DNG writer | no page-cache copy, no `DONTNEED`, no writeback path | **in no running binary**: T24 skipped (`working/handoff-T26-T30.md:12,70`); the KB patch `working/patches/0001-cdng-direct-I-O-...patch` "208 insertions, never compiled" (`dng-chain-feasibility.md:264`); `26da30e` ported T29 "without its direct-I/O step (needs T24)" (`fork-log.md:44`). The `2a6f114` tree that opened `O_DIRECT` (`working/port-raw/s2-storage-core.md:4-7,226-228`) was a 2026-10-26 scratch checkout, not the Pi's branch (probable) | the only writer-side lever with an isolating measurement: Core idle at 25 fps, buffered `dd` 561 MB/s = 19 capture gaps, `oflag=direct` 759 MB/s = 0; "memory traffic alone costs frames; direct I/O does not" (measured, `hardware-log.md:69-87`; `working/clearhdr-design.md:127-135` per feasibility) | named as an untried 30-fps lever (`recipe.md:68-70`; `handoff-drop-frames-tier2.md:101`) | code + build; a take must never overlap the build |
| `APERTAR_RT_CAPTURE_PRIORITY=N` | SCHED_FIFO on libcamera's completion thread alone, falls back to nice -5; needs `LimitRTPRIO=80` (the capture-priority drop-in carries `LimitNICE=-5` and `LimitRTPRIO=80` at `31d5418`, `working/dual-sensor/claim-check.md:622-624`; installed per `architecture/build.md:96`, LimitRTPRIO probable) | drop-in (sudo) + restart; journal `capture scheduling: ... SCHED_FIFO priority=N` | FIFO 40 on 11-01: 92 lost (6.1 %) against 6-10 % baseline, no effect (measured, under `writer` pressure, `hardware-log.md:954`) | whole-process `APERTAR_RT=1` is the wrong shape (equal-priority FIFO writers can block the capture thread, patch README row `0008...patch:52`) | risk: RT throttling if a thread spins; campaign binary only (probable) |
| `APERTAR_WEB_PREVIEW_RECORDING_FPS=N` (default 30, 0 = pause) | caps or pauses the browser MJPEG preview while a raw take runs; the downsample runs on libcamera's completion thread (`0008...patch:51`) | drop-in (sudo) + restart | 0.2-0.5 ms per frame measured in October on an old build (patch row; `dng-chain-feasibility.md:250`); never A/B'd as a take on this rig (B.4 of the feasibility plan not run) | see WebUI (2f) | none; campaign binary only (probable) |
| The media-tune file and `/run` override | one readable place for the write-path knobs per medium; precedence env > override > base file > default; `[<class>.<fs>]` > `[<fs>]` > `[<class>]` > `[default]`; Core logs `media tune: file=... override=...` once per process and every `recording clip:` line ends `tune_override=yes|no` (`config.md:394-416`) | `scripts/apertar-tune show|set|unset|clear|init` as pi; the override lives in `/run/apertar-media/media-tune.override.conf` (never `/dev/shm`: logind deletes pi's files there, `findings-2026-11-03.md:39-41`); restore = `apertar-tune clear` + Core restart (`media-tune-file.md:45-47`) | the values written on 11-02 are B1's state, only `dontneed=sync` is test-backed (`media-tune-file.md:36-43`) | the campaign binary reads it; the clean binary does not (probable) | none |

### 2b. Compression

| Lever | What it does | Switch | Measured or probable effect | Interactions | Cost |
| --- | --- | --- | --- | --- | --- |
| `set_cdng_compression value=none` (uncompressed) | the raw CFE frame written as is: 4K HDR16 one DNG = 16,590,340 B (measured, `working/dng-chain/R5.md:15` citing hardware-log:820), raw buffer 16,896,000 B (`findings-2026-11-02.md:10`); SDR12 12,443,140 B (`dng-chain-feasibility.md:362`) | socket; reconfigure; **refused while the Mode Ladder is active** (`hardware-log.md:635-636`) | the only HDR16 compression that records clean: 25 fps 10 min clean three times (C0101, A0, A1) and 27 fps clean in 3-min takes with TDN off; 28 fps clean only with D4; 30 fps lost 3 in 2 min (measured, `recipe.md:7-9`; `findings-evening4-supervised-2026-11-04.md:9-17`) | the ladder's HDR16 rung should read uncompressed (`recipe.md:81-82`) | **415 MB/s at 25 fps, ~498 at 30** (derived; section 3) |
| `set_cdng_compression value=lossless_jpeg` | LJ92 SOF3, 128-row tiles, 5 workers (`core.md` §6) | socket; reconfigure; refused under the ladder | **HDR16: eliminated before the campaign starts**: encoder capacity ~17.5 fps (`estimated_capacity_fps` 17.2-17.8; 281 ms a frame, 109 ms of it waiting), so a 25-fps take fills the RAM buffer and the safety stop ends it after ~19 s (measured, `README.md:52`); 24 fps in frames mode: 19 queue drops in 6.5 s (`hardware-log.md:627`); O2 "drops frames" (`observations-2026-11-04.md:12,22-25`); pre-roll estimate 16.84 fps (`findings-2026-11-03.md:47`). **SDR12: the strongest arm on record**: 10 min at 33 fps 0 / 19,851 (84 ms CPU per frame, 2.81 cores), pre-roll capacity 48.13 fps at 33; O3 ~42 fps clean, compression unconfirmed (`findings-2026-11-04.md:54-65`; `observations-2026-11-04.md:13,26-31`); 27 s at 30 fps 0 lost, `estimated_capacity_fps` 62.9 (`README.md:185`); "43-66 fps" over the evening (`night-2026-11-01.md:197-198`) | lossless forces manual ISO, cap 1600 (`architecture/core.md:595`). In SDR the raw transport is PiSP COMP1 (1 B/px, sensor-side lossy companding): the owner kept it ("half the bandwidth; it is what makes 60 fps possible", `hardware-log.md:861-864`) | SDR12 lossless ~5.98 MB/frame (pre-roll 688 MB / 115 frames, derived) = ~197 MB/s at 33 fps; t2a filled 15 % in 10 min vs 25 % uncompressed (`findings-2026-11-04.md:56-57`). HDR16 lossless file size: unmeasured |
| Lossy DNG 3:1 / 5:1 (`set_record_format value=lossydng` + `set_lossy_dng_ratio value=3to1|5to1`) | `LossyDngEncoder`, async writer, 4 workers at nice +5, queue 24 (`core.md` §6; `compare-raw/a4-core-writer.md:192-196,239-240`) | socket; reconfigure; both refused under the ladder (`hardware-log.md:635`) | **SDR only**: lossy is refused in every Clear HDR mode (`fork-log.md:24` `e1c10cd`; `inspection-2026-11-02.md:468-469`). **Encoder capacity and file size never measured** (B-lossy never run, "read `estimated_capacity_fps` first", `inspection-2026-11-02.md:469`; `working/port-raw/critic-ramp.md:81` "lossy DNG throughput UNKNOWN"); the ladder switch 30 fps -> SDR12 lossy 3:1 works (confirmed, `hardware-log.md:634-636`) | **write errors are only logged and never fail the take** (`architecture/core.md:426`; `lessons/upstream-issues.md:46` #39): a lossy take must be judged by counting files against fps x seconds; no sync thread, so `dontneed` behaves as `off` and the files get no pull-safety fsync (`inspection-2026-11-02.md:469-472`) | nominal 1/3 and 1/5 of 12.4 MB = ~4.1 / ~2.5 MB per frame (estimated from the ratio, unmeasured) |

### 2c. Log (`set_cdng_log value=off|auto`; legacy `12|10|8` read as On)

| Item | Fact | Source, label |
| --- | --- | --- |
| What | one step down through a mu-law curve, inverse table as the DNG `LinearizationTable`; 16 -> 12 in cDNG uncompressed and lossless JPEG; one On/Off button (WebUI Recording format card, touch UI Settings > Record); state `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied`; the format label says "· Log" | `README.md:60`, read from code |
| Where it applies | **Clear HDR 16-bit only**: Log's copy worker maps only unpacked 2-byte streams; SDR lossless (and SDR generally, COMP1) records linear with `cdng_log_applied=false` and the journal line `CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear`; owner's decision: no Log for SDR | `hardware-log.md:857-869`, measured; `README.md:106-112` |
| Switch | socket, no sudo; carried across formats; a reconfigure is not stated | `README.md:60` |
| Bytes | one Log frame 12,451,344 B against ~16.6 MB linear: -25 %; 311 MB/s at 25 fps (560 GB per 30 min) against 415 MB/s (747 GB) | `hardware-log.md:818-820` measured; `dng-chain-feasibility.md:15-16,261` derived |
| The one measured take | 117 frames, 10 capture gaps, WebUI open, pre-squash build, minutes after a reboot, uncontrolled; the worst gap rate of its evening (6.9 ms/frame after the first gap) | `hardware-log.md:779-796` measured; `dng-chain-feasibility.md:44-49` |
| Mechanism | neutral on the serial cycle by construction (LUT on the copy worker after the request is released) but +0.62 GB/s DRAM net and +4-17 ms on the single copy worker; "Log is a cost in every dimension but storage" | `dng-chain-feasibility.md:220-228` code-confirmed / derived / estimated |
| Why it is still a 30-fps candidate | the 30-fps limit is a second limit behind the FE Config queue: the back end slows and Core's queue nearly fills (11/12); memory bandwidth at ~510 MB/s is the first suspect, and Log is the untried byte-reducing lever | `recipe.md:63-70` probable; `handoff-drop-frames-tier2.md:101` |
| Opposite risk | evening 2 measured that memory traffic alone slows the back end (two `dd` to `/dev/null`: BE 10.9 -> 95 ms, >half the frames lost in take mode); Log adds DRAM traffic while it removes NVMe traffic: the sign of its net effect is **unconfirmed** until a counted take exists | `preregistration.md:316-333` measured |
| Status | not opened in Resolve; no Log take longer than ~5 s; campaign binary only | `README.md:60,134` |

### 2d. TDN (preview temporal denoise)

| Item | Fact | Source, label |
| --- | --- | --- |
| What TDN costs | the ISP back end reads and writes a full 16-bit reference per frame (~37.6 of ~57.6 MB per frame, libpisp simulation): BE job ~37 ms at 25 fps, longer than the 40 ms frame leaves after the next frame's 16-bit swap; TDN off: 5.9 ms | `findings-2026-11-04.md:11-28` measured; `tier1-prep-2026-11-03.md:14-18` probable |
| Effect | block NFFN (die 4): N lost 58 + 39 and 115 + 116, F 1 + 0 and 2 + 0; queued share 0.91 -> 0.00; exact permutation p = 1/6 on both statistics (one block, complete separation): **probable**; raised the clean ceiling from 25 to 27 fps (3-min takes); onset at 28 (5 lost) without D4 | `findings-2026-11-04.md:11-50` |
| Switch on `9b5ea14` | `set_tuning_file path=/home/pi/Tuning-Files/imx585_clearHDR_notdn.json` (socket; **camera restart 45-110 ms**; refused while recording, in Standby, with stills pending; persisted in `~/.config/apertar-core/camera_settings.conf`, survives Core restarts and reboots; back with `path=`); copy = `defaults-pisp/imx585_clearHDR.json` (134,888 B, md5 `f53de0fe...`) minus its 3 `tdn` blocks by `working/tools/tdn_strip.py` (134,482 B, md5 `98d98f2e...`) | `tier1-prep-2026-11-03.md:60-98`; `preregistration.md:597-603` |
| Read-back | `tuning_file` in `get_state`; journal `ApertarCore tuning file: ... (custom, pisp)`; positive check `bayer_enables & 0x140 == 0` in the BE config dump (`LIBCAMERA_RPI_PISP_CONFIG_DUMP`, a drop-in = sudo; written at each configure, read only a dump of the take's 3840-wide 16-bit input) | `preregistration.md:410-422` measured |
| Trap | **a chosen file is used as given in every mode**: with the copy selected, SDR12 takes run on the Clear HDR tuning (noisier preview, different rendering): restore `path=` before SDR takes and before handing back; a non-Standard preview colour profile makes libcamera load a derived `~/.cache/apertar-prores/<profile>.json` that keeps `rpi.denoise` | `tier1-prep-2026-11-03.md:92-98` confirmed |
| Preview cost | SDN takes `deviation_no_tdn` 3.2 / `strength_no_tdn` 0.75; UI CPU per frame -20 to -24 %; owner judged the noise acceptable on 11-04 20:26; DNGs are the CFE buffer and do not change | `findings-2026-11-04.md:31-33`; `findings-evening4-supervised-2026-11-04.md:50-53` |
| Z (no denoise) | `imx585_clearHDR_nodenoise.json` (md5 `7250056e...`, `tdn,sdn,cdn` stripped); dump `0x45040d` confirms all three off; look done, **no scored take** | `preregistration.md:597-603,632-635` |
| Switch on `a344376` | `set_preview_tdn` (`TuningTdnStrip.hpp`; strip test byte-identical to the evening-3 copy); **default off = TDN stripped unless `set_preview_tdn enabled=true`**; applies to the resolved tuning, so to SDR's `imx585.json` as well; not yet run on the camera | `fork-log.md:156` |
| SDR tuning | SDR12 loads `defaults-pisp/imx585.json`; whether it carries `tdn` blocks was never grepped (probable, strongly: every PiSP IMX585 tuning of that size class carries three); at 33 fps with it the BE job is 9.6-12.9 ms, far under the ~29.5 ms threshold (no 16-bit swap, no software stats), so TDN is not SDR's limiter at 33 | `tier1-prep-2026-11-03.md:14-18`; `dng-chain-feasibility.md:376-377`; `findings-2026-11-04.md:56-63` |
| O1 caveat | the owner's 10-min 25-fps take with the WebUI open ran with **TDN on** and lost 1 (Core's count), unlogged; every N unit (58-116 lost per 3 min) ran with the RPi debug log and trace events, A0 (TDN on, clean) without: **unconfirmed hypothesis that the instrumentation costs the TDN-on margin** | `observations-2026-11-04.md:51-61` |
| Never | `disable_tdn` in the pipeline YAML (TdnOutput enabled with 0 buffers; `pispbe_prepare_job` abandons every job: a stall); never edit `defaults-pisp` | `tier1-prep-2026-11-03.md:54-58` |

### 2e. The frame-rate phase lock (`set_fps_phase_lock enabled=true|false`)

| Item | Fact | Source, label |
| --- | --- | --- |
| What | per-frame PI servo on `FrameDurationLimits` referenced to BOOTTIME (CineMate's lock); persisted, carried across formats, carried by presets; state `fps_phase_lock`, `fps_phase_lock_active/err_us/dur_us/pushes/saturated`; env `APERTAR_PHASE_LOCK_LOG/_KP/_KI/_DEADBAND_US/_CLAMP_US` | `working/phaselock-answer.md:41-53,76-79`; `config.md:462` |
| Switch | socket, no restart, no sudo; on `a344376` also the WebUI Performance card | `fork-log.md:35,61,157` |
| T27 measurement | sensor free-running within **1.2-1.6 ppm** of the Pi's raw crystal; the lock holds to BOOTTIME and so follows NTP slews (tens of ppm); C0102 lock off: 1490 frames, 0 holes, band flicker max 0.28 %; C0103 lock on: 1478 frames, **10 holes** (`dropped_gap_estimate=10`), `max_abs_err_us=199`, `duration_pushes=673`, band step **max 8.9 %** (visible flicker); each push re-chooses HMAX on this libcamera's lattice | `hardware-log.md:246-293` confirmed / measured |
| Verdict | "the lock harms the picture ... period changes cost frames"; decision off (default); "the sensor needs no lock at 25 fps" (probable) | `hardware-log.md:279-293`; `architecture/core.md:596-597` |
| Worth a take? | by the owner's own measurement, no: it is the one lever with a measured **negative** effect and no measured benefit. Its only campaign use is a read-back: `fps_phase_lock` must be `false` before every take (presets can flip it; none are to be loaded). One exploratory 3-min take would be predicted to stop on its first drop under the stop rule | this reader's reading of the above |

### 2f. WebUI on/off and the touch UI state

| Item | Fact | Source, label |
| --- | --- | --- |
| How `take3v3.sh` decides | `TAKE_WEBUI=refuse` (default): no established client on `:8000` or the take does not start; `require`: >= 1 client or it does not start; clients counted with `ss -tnH state established '( sport = :8000 )'`, printed per minute | `take3v3.sh:19-20,66-71,98` |
| What a client costs in Core | per tab per second `/api/state` shells out to `lsblk`, scans ALSA, re-reads UI.conf and reprograms the INA219; the MJPEG thread (640x360, <= 30 fps, JPEG q75) runs only while `/preview.mjpeg` has viewers; the downsample sits on libcamera's completion thread (0.2-0.5 ms per frame, old-build measurement) | `architecture/core.md:349`; `0008...patch:51` |
| Measured | 11-01, 60-s takes under `writer`: touch UI running + WebUI closed 6.9 %, + one tab open 9.1 %, UI stopped 0 ("the open WebUI adds about 2 %") (`hardware-log.md:907-931` measured; `README.md:47` finding 6). 2026-10-31: four short takes with the WebUI open all lost frames, uncontrolled (`hardware-log.md:779-795`). Evening 3: WebUI closed in every take. Evening 4: WebUI open in every take (owner's requirement), d4 28 fps D4 F **0 / 5,055** (`findings-evening4-supervised-2026-11-04.md:3,14`). O1: 10 min 25 fps, WebUI open, TDN on, 1 lost (`observations-2026-11-04.md:51-57`). A 10-min open-vs-closed pair was never run (feasibility B.4) | as cited |
| The Mac stand-in | `working/tools/webui_client.py`: GET `/api/state` every 1 s on one keep-alive connection and the `/preview.mjpeg` stream read and discarded, reconnecting after a close or 5 s silence (a real browser's `<img>` does not reconnect after a Core restart); read-only (no `/api/command`, the page's `user_activity` POST deliberately not mirrored); status line every 10 s; run under `caffeinate` on the Mac | `webui_client.py:1-37`; `preregistration.md:621-627` |
| Switching "off" | no client (close the tab, stop the stand-in); `--web-port 0` disables the server but needs a change to `/home/pi/start-apertar-core.sh` (not done; not recommended) | `architecture/core.md:43` |
| Touch UI aids | `~/.config/CinePi/UI.conf` `focusPeakingEnabled`, `zebraEnabled`, `audioMeterEnabled` (printed by `take3v3.sh` "aids:"); socket toggles `set_focus_peaking_enabled`, `set_zebra_enabled`, `set_audio_meter_enabled enabled=`; the UI preview is the 1280x720 YUV and the aids are GPU shaders on it, never on the raw | `take3v3.sh:55`; `core.md` UI.conf toggles; `tier2-plan-2026-11-04.md:26-28` |
| Touch UI preview cap | `APERTAR_UI_PREVIEW_RECORDING_FPS=N|0` on `apertar-ui-direct` (a drop-in = sudo, UI restart). Under `writer`: `=0` 0 lost, `=12` 2.9 %, UI stopped 0, peaking most of the GPU cost (`hardware-log.md:977-1000` measured). Under `sync`: preview off 0 + 0, 12 fps 4 + 330, full 2 + 108: **not monotone, the UI preview is not the lever under `sync`** (`preregistration.md:277-290`; `findings-2026-11-03.md:30-31`). With TDN off the full preview with peaking and zebra on is clean at 25-27 fps | as cited |
| Reading for the campaign | the owner's target requires the aids on and (since 11-04) the WebUI open: these are states to record and hold constant, not levers to switch off; the stand-in is what makes "WebUI on" reproducible across Core restarts | `preregistration.md:612-614`; `handoff-drop-frames-tier1.md:38-39` |

### 2g. FE Config queue depth 4, compaction, 16 buffers, link frequency

| Lever | What / how | Measured or probable effect | Cost / caveats |
| --- | --- | --- | --- |
| **FE Config queue depth 4** | libcamera keeps `num_cfe_config_queue` = 2 Config buffers in flight; a copy of the installed PiSP pipeline YAML with only `"num_cfe_config_queue": 4` changed (`/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml`, md5 `88929ca3...`; D2 = `pisp-depth2.yaml`, md5 `c1e0c3e9...`, byte-identical to `/usr/local/share/libcamera/pipeline/rpi/pisp/example.yaml`) selected by `LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml` in a Core drop-in; the YAML is copied as pi before every Core start that has the drop-in; read once at camera open: **Core restart, drop-in = sudo** (`apertar-e4-helper arm` writes it together with the debug-log, log-file and dump lines; `disarm` removes it and restarts) | mechanism: all 11 TDN-off losses of evening 3 were FE Config starvation during kcompactd bursts every ~32.8 s; the depth-2 replay reproduces every loss and predicts 0 at depth 3-4 (measured / probable, `tier2-plan-2026-11-04.md:12-21`). A/B at 28 fps, F, WebUI open: D2 d3 lost 1 at 77 s where the replay predicts it; D4 d4 **0 / 5,055** with 6 late Config buffers (worst 138 ms) that would have cost 4 frames at depth 2; **probable, n = 1 + 1, Inconclusive by the registered rule** (a second clean D4 take is missing). At 30 fps D4 t1 lost 3 at 119 s with no Config later than 4T and Core's queue at 11/12: a second limit, 30 fps ruled out with the current measures (`findings-evening4-supervised-2026-11-04.md:9-45`) | zero memory, zero bytes; no log line states the depth (the md5 is the check); works with either Core binary (libcamera config); permanent = an `/etc` drop-in, not done (`findings-evening4-supervised-2026-11-04.md:54-57`). The helper's `arm` also turns on the RPi debug log and trace events, whose own cost is the unconfirmed O1 hypothesis: a depth-4 arm **without** the log needs a drop-in that carries only `LIBCAMERA_RPI_CONFIG_FILE` (new helper text for Patrik to review) |
| `vm.compaction_proactiveness=0` | sysctl (sudo; `apertar-e4-helper compact0` saves the old value to `/run/e4-compact.orig`, `compact-restore` writes it back; default 20) | the registered fallback if a D4 take lost with `L > 4T`; **never triggered, untested** (`preregistration.md:773`); rationale: the ~33-s kcompactd bursts stretch the 16-bit swap (association measured, cause probable, `tier2-plan-2026-11-04.md:19-21`) | no bytes; unknown effect on fragmentation over 30 min (on 11-01 `buddyinfo` showed no free order-8 block and CmaFree 0-0.8 MB, `README.md:205`) |
| 16 raw buffers | `apertar-tune set raw_buffers=16` + restart | worse: 26 + 123 lost, losses without CFE starvation (measured, n = 1; 2a) | eliminated |
| Link frequency 891 vs 720 MHz | `dtoverlay=imx585,...,link-frequency=` in `config.txt` through the Boot Config card / `set_boot_config` (root helper `apertar-boot-config` + sudoers) and a reboot (`config.md` §7.1) | the CFE logs `DPHY: Datarate 1782 Mbps out of range` at every stream start (`hardware-log.md:963`); the link was ruled out for the evening-3 losses (measured, `tier2-plan-2026-11-04.md:22-23`) and for the 11-01 losses (clean with the UI stopped and at 1080p); the 1440 Mbps control cell was conditional on CSI OVLF correlating, which it did not (`inspection-2026-11-02.md:445-446`; `findings-2026-11-02.md:29-30`). 720 MHz would cap HDR16 at 25.000 fps and 4K SDR at 50.000 (driver tables, confirmed, `working/dual-sensor/claim-check.md:519`) | not a campaign lever: it cannot help 28-30 fps and costs a reboot |

### 2h. Mode Ladder, `fps_max`, `set_fps`

| Item | Fact | Source, label |
| --- | --- | --- |
| Ladder must be off for a take | an active ladder refuses `set_cdng_compression`, `set_lossy_dng_ratio`, cDNG<->lossy `set_record_format`, `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr`; with it on, `set_fps` picks the rung (one reconfigure) and a take is capped at `fps_take_max` | `hardware-log.md:609-612,634-636,647-648` confirmed; `fork-log.md:90-93` |
| How the script does it | `set_mode_ladder enabled=false`, 3 s, `set_fps`, `set_clear_hdr`, `set_raw_bit_depth`, `set_cdng_compression`, then **`set_fps` again** ("a mode change can clamp the frame rate: set it again"), then the `mode:` line from `get_state` (width, height, fps, clear_hdr, raw_bit_depth, recording_format, cdng_compression, tuning_file) with the asked values beside it; at the end `set_mode_ladder enabled=true` + `set_fps 30` ("restored") | `take3v3.sh:60-65,109` |
| Restore target | the script restores the ladder **on** at 30 fps, but the Pi was handed back on 11-04 with the ladder **off** at 25 fps HDR16 uncompressed (`preregistration.md:778-782`); the last recorded ladder: rung 1 ClearHDR16 <= 30 lossless (asks more than the ~17.5-fps encoder), rung 2 SDR12 <= 50 uncompressed (`handoff-drop-frames-tier1.md:184-185,194-195`; `findings-2026-11-03.md:45-47`): the restore target is the owner's call, read back before and after | as cited |
| `fps_max` per mode (probe, confirmed on the Pi 2026-10-26, 42 modes) | SDR 10/12-bit 3840x2160 **60** fps; 3840-wide crops 62.85-85.66; 1920x752-1080 60-85.66; Clear HDR 12-bit 3840x2160 **30**; Clear HDR 16-bit 3840x2200 **30** | `working/sensor-capabilities.md:51`; `README.md:51` |
| On `9b5ea14` | HDR16 4K `fps_max` 30 (measured 2026-11-04); HDR16 height crops 31.9-42.4 fps; "4K Clear HDR 16-bit tops out at 27 fps on the Pi" (owner, 11-03) | `fork-log.md:145` |
| Crop modes on record | 4K crops 3840x{2076, 2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504} (`architecture/drivers.md:141`); 1.85:1 crops 3840x2072 / 1920x1036 added by Core `900d282`, present at 10 and 12 bit after driver `cd548ef` (`hardware-log.md:899-903`). **The only counted crop take**: M3 3840x2076 SDR12 uncompressed 50 fps, 2 x 60 s, lost 12 % as steady single-frame capture gaps, queue 2-3/12, on build `4d5fdd1`, untrimmed drive 78-82 % full (`hardware-log.md:582-595` measured; cycle 22.7 ms derived, `dng-chain-feasibility.md:100-101`). No crop take on any later build. A crop writes fewer rows (2076: -3.9 %) | as cited |
| `set_fps value=` | keeps the shutter angle; refused while recording unless the speed ramp is on; Core truncates the pin to whole µs; **with `fps_speed_ramp` on, any `set_fps` from any UI changes the rate inside a take**: d1r was voided when the rate went 28 -> 30 mid-take (`policy=angle`, so the ramp was on during evening 4: probable); read `fps_speed_ramp` in `get_state` and send `set_fps_speed_ramp enabled=false` before the campaign (`architecture/core.md:176`; `hardware-log.md:256`; `preregistration.md:743-751`; `architecture/core.md:611`) | as cited |
| fps read-back | a controls-only fps change does not reach the sensor at once; measure fps from the sensor timestamps / the take's cycle, never from the request (the pre-roll lesson); the `mode:` line's first `fps=` is the manipulation check | `hardware-log.md:851`; `preregistration.md:410-412` |

## 3. Bytes per take (derived; the wear and fill arithmetic the plan needs)

Per-frame sizes: HDR16 uncompressed 16.59 MB (measured file), HDR16 Log 12.45 MB (measured file), SDR12 uncompressed 12.44 MB
(measured), SDR12 lossless ~5.98 MB (one scene, pre-roll), lossy 3:1 / 5:1 ~4.1 / ~2.5 MB (estimated from the ratio), HDR16
lossless unmeasured. Drive 932 GB (`README.md:179`). The recipe's rule: keep the drive well below ~75 % (~700 GB) (`recipe.md:47`,
probable mechanism); take #78 lost 18 of its 25 frames in the last minute at 97 % full (`README.md:176-181`, probable).

| Mode | MB/s | 3 min | 5 min | 15 min | 30 min | 30-min files |
| --- | --- | --- | --- | --- | --- | --- |
| HDR16 uncompressed 25 fps | 415 | 75 GB | 125 GB | 373 GB | **747 GB (80 %)** | 45,000 |
| HDR16 uncompressed 28 fps | 465 | 84 GB | 139 GB | 418 GB | **836 GB (90 %)** | 50,400 |
| HDR16 uncompressed 30 fps | 498 | 90 GB | 149 GB | 448 GB | **896 GB (96 %)** | 54,000 |
| HDR16 Log 25 / 30 fps | 311 / 374 | 56 / 67 GB | 93 / 112 GB | 280 / 336 GB | 560 / 672 GB | 45,000 / 54,000 |
| SDR12 uncompressed 33 / 42 fps | 410 / 523 | 74 / 94 GB | 123 / 157 GB | 369 / 470 GB | 738 / 940 GB | 59,400 / 75,600 |
| SDR12 lossless 33 / 42 / 50 fps | ~197 / ~251 / ~299 | 36 / 45 / 54 GB | 59 / 75 / 90 GB | 178 / 226 / 269 GB | 355 / 452 / 538 GB | 59,400 / 75,600 / 90,000 |

Consequences for the lever choice (this reader's reading): a 30-min HDR16 uncompressed take at >= 28 fps does not fit under
the 75 % rule on this 1 TB drive at all, and at 25 fps only on an empty, trimmed drive; Log (if it proves neutral on drops)
is the only HDR16 lever that makes 30 min at 30 fps fit under 75 %. The exFAT create scan is estimated at 12-38 ms per file by
the 30,000th file in one folder (unmeasured constant; A0/A1 clean at 15,000 files, t2a/t2b at 19,851/19,857): a 30-min take
at 25 fps has 45,000 files in one folder, beyond any measured count (`dng-chain-feasibility.md:75,132-136`). Thermal: HDR16
25 fps 10 min took the NVMe 34 -> 54 C; SDR12 uncompressed 33 fps 10 min reached 72 C; warning threshold 82.9 C; evening 4
ran at 44-66 C with the gate removed; nothing longer than 10 min is measured (`hardware-log.md:745`; `findings-2026-11-04.md:57`;
`findings-evening4-supervised-2026-11-04.md:31`). Wear so far: `percentage_used` 3 % and 25.28 TB written on 2026-11-01,
+1.34 TB on 11-02, 29.01 TB after evening 3 (+1.55 TB), 3 % used after evening 4 (`night-2026-11-01.md:106`;
`findings-2026-11-02.md:70-71`; `handoff-drop-frames-tier1.md:185-186`; `preregistration.md:783-784`). The drive's TBW rating
is not in the KB.

## 4. Levers the record already settles (do not spend takes on them)

| Lever | Why it is out | Source |
| --- | --- | --- |
| HDR16 lossless JPEG at >= 18 fps | encoder ~17.5 fps; safety stop after ~19 s at 25 fps; queue overflow in 6.5 s at 24 | `README.md:52`; `hardware-log.md:627` (measured) |
| Phase lock on | 10 holes per 60 s and 8.9 % flicker, sensor within 1.5 ppm anyway | `hardware-log.md:260-293` (measured) |
| 16 raw buffers | worse, and losses without CFE starvation | `preregistration.md:190-215` (measured, n = 1) |
| `buffer=frames` as a cure | 590 + 181 lost, back end unchanged | `preregistration.md:298-313` (measured, n = 1) |
| `APERTAR_DNG_DONTNEED=writer` | B1 p = 1/36 against it | `preregistration.md:111-116` (measured) |
| `APERTAR_DNG_WRITEBACK=0` | A2: 1491 gaps in 10 min | `hardware-log.md:765-777` (measured, one run) |
| periodic `syncfs` | 782 queue drops + 12 gaps in 3 min | `architecture/core.md:571`; `fork-log.md:48-49` (measured) |
| UI preview throttling as a lever under `sync` | dose-response not monotone | `preregistration.md:277-290` (measured) |
| 720 MHz link | caps HDR16 at 25 and SDR at 50; the link is not the loss path | `claim-check.md:519`; `tier2-plan-2026-11-04.md:22-23` |
| `kernel_tune=on` as a switch | the helper is not installed: the key does nothing until root installs it | `config.md:459`; `fork-log.md:44` |
| Lossy in Clear HDR, Log in SDR | refused / records linear | `fork-log.md:24`; `hardware-log.md:857-869` |
| `APERTAR_RT_CAPTURE_PRIORITY` | no effect measured (under `writer`); an untested belt at best | `hardware-log.md:954` |

Open levers that are cheap in bytes and still unmeasured: D4 at 25 fps over 10-30 min; a second clean D4 at 28 fps; Log on
HDR16 with TDN off and D4; `compaction_proactiveness=0`; lossy 3:1 / 5:1 capacity (one short take each); WebUI open vs
closed as a 10-min pair; `dontneed=off`; the no-log depth-4 arm (instrumentation cost).

## 5. What the Opus thread must not do

Rules of the campaign that still hold, plus the traps this inventory found (sources: `handoff-drop-frames-tier1.md:124-148`,
`handoff-drop-frames-tier2.md:66-76`, `tier1-prep-2026-11-03.md:54-58,92-98`, `handoff-drop-frames-fable.md:59-71`, the
e4 helpers' headers, and sections 0-2 above).

1. **Never restart Core (or reboot, or run `apertar-b1-arm sync`, `apertar-e4-helper disarm`) without knowing that
   `~/ApertarCore-build` currently holds the clean `a344376`.** Decide the binary first; rebuild `9b5ea14` if the campaign
   needs Log, `buffer=ram`, the pre-roll, `recording_dropped_frames`, the media-tune file or 28-30 fps HDR16. Check the
   running binary after every restart (section 1's `get_state` discriminator, and the journal's tuning and `media tune:` lines).
2. **Never record while a build runs, and never build while a take runs** (`take3v3.sh` refuses on `cc1plus|gmake|cmake`;
   another session compiled during two takes on 11-01 and invalidated them).
3. **Never `disable_tdn` in the pipeline YAML; never edit the installed YAML or anything in `defaults-pisp`; copies only**
   (`/home/pi/Tuning-Files/...`), and a Z or F arm counts only with the dump's positive check.
4. **Never run sudo yourself and never widen the sudoers file**: Patrik installs every root helper from exact, reviewed text;
   the installed helpers allow only the listed words. A no-log depth-4 drop-in, a sysctl, an `/etc` drop-in, an `fstrim`, a
   format, a reboot: each is his step or his helper.
5. **Never delete with a glob**; delete only a take's own clip folder, read from its `recording clip:` line, and never the
   owner's clips (`cDNG_26_11_04_20322419_C0001` is kept on his instruction) or `warm.bin` without asking. Every delete >= 1 GiB
   triggers a trim, after which nothing is recoverable.
6. **Never write anything but takes to `/media/RAW`**: logs, overrides and traces go to `/run/apertar-media`; never `/dev/shm`.
7. **Never run `dontneed=writer`, `writeback=off`, `sync_ms=0` together with `dontneed=sync`, a periodic `syncfs`, or the
   phase lock in a scored take**; read `fps_phase_lock`, `fps_speed_ramp`, `ladder_enabled`, `tuning_file`, `buffer_setting`,
   `cdng_log` and `media_trim_last_unix` from `get_state` before every take and write them into the take record.
8. **Never judge drops by `takes.sh missing`** (the numbering hides capture gaps, and with the ramp on it hides everything):
   use `recording_dropped_frames` / `dropped_gap_estimate`, `dropped_queue_full`, `dropped_copy_slot`, frames written against
   fps x seconds, and for lossy DNG the file count (its write errors never fail the take).
9. **Never trust the requested fps**: send `set_fps` after the mode commands as well, read the `mode:` line, and void a take
   whose mode differs; never touch the camera, the touch UI or the WebUI during a take (d1r was voided by a mid-take rate change).
10. **Never run with the ladder on, never load or save presets** (they carry the tuning file, the phase lock and the ramp).
11. **Never leave the TDN-off copy selected into an SDR take or when handing the Pi back**: `set_tuning_file path=` and read it
    back (`ST`, `J`, the settings file); keep the preview colour profile Standard or check the derived `.cache` tuning.
12. **Never leave state behind**: every `/run` drop-in, the `/run` YAML, the override (`apertar-tune clear`), tracefs events and
    `buffer_size_kb`, `compaction_proactiveness`, the ladder, the mode, the tuning, read back against the restore list
    (`preregistration.md:64-92`), then `smartlog`.
13. **Never run anything else on the Pi during a take**: no ssh journal queries, no worker ssh, no second WebUI (one stand-in
    only, the browser tab closed), no two unit loops; copy the `/run` logs off before the next Core restart (the libcamera log
    restarts with each Core process; a `b1-trace-*` file left behind blocks the unit loop).
14. **Never pull the card while mounted, never hot-unplug the NeoRotary, never write `/proc/irq/*/smp_affinity` for RP1
    interrupts** (two evening-2 voids came from card swaps; the unit loop checks the serial `A936B442006AC2` and `warm.bin`).
15. **Never change a rule after seeing data, never upgrade a label, decide voids from the checks alone** before any analysis.
16. **Never let a take start when Core is `error`, `media_state` is not mounted, a delete or trim is running, or the pre-roll
    has not finished** (Core refuses most of these; the loop waits for the pre-roll line and would wait 10 min and give up if
    the pre-roll were switched off: adjust the loop before switching it off).
17. **Never fill past the plan's ceiling** (section 3): a 30-min HDR16 uncompressed take at >= 28 fps cannot run under the
    75 % rule on this drive; budget the fill before the series, not after a loss, and never format without the owner.
18. **Never spend bytes on the settled levers of section 4**; a lossless HDR16 or phase-lock take is a predicted failure.
19. **Never push Core or UI, never push the KB without the owner's OK, never put passwords or tokens into the KB**; commits
    `<area>: <imperative>` with Why / What / Tested, "User" not names.
20. **Stop the night** (record_stop, restore, push what you have, power off) on: a `set_tuning_file` error, Core `error`, a
    second void, smart-log `critical_warning != 0`, a take script that died (send `record_stop` at once), anything outside the
    registered plan.

## 6. Open questions this inventory leaves for the plan

1. Which binary runs the campaign (section 0.1), and if `9b5ea14`: who rebuilds it, when (never near a take), and how the
   running binary is verified after each restart.
2. Are the e4 helpers still installed (section 0.2)? Without them nothing that needs root can run unsupervised.
3. Was `fps_speed_ramp` on during evening 4 (d1r ramped `policy=angle`)? It must read false before the first take.
4. The ladder's restore target (off at 25 fps as handed back on 11-04, or on with the owner's rungs).
5. Does `defaults-pisp/imx585.json` carry `tdn`? (`grep -c '"tdn"'`, probable yes; decides whether TDN off is a lever for the
   SDR arms at all; measured SDR BE margin at 33 fps says it is not needed there.)
6. Lossy 3:1 / 5:1: encoder capacity, file size, and whether the async writer dropped files (never measured).
7. Log: one counted take of any length; with TDN off and D4; the sign of its net effect on the 30-fps back-end limit; Resolve.
8. D4: a second clean 3-min take at 28 fps; D4 at 25 fps over 10-30 min (B6 never ran); does the RPi debug log + tracefs
   that every scored take carried cost margin (O1 vs the N units)?
9. 30-min capacity: fill (section 3), the exFAT file count beyond 19,857 files, thermal beyond 10 min at >= 400 MB/s.
10. `compaction_proactiveness=0`, `dontneed=off`, the kernel-tune sysctls under `sync` on a non-empty drive (take #80's
    confound), extra raw buffers on exFAT: all untested.
11. Whether the Mac stand-in equals a browser's load (the page's `user_activity` POST is not mirrored) and whether "WebUI open"
    costs anything at all with TDN off (a 10-min pair was never run).
12. The drive's TBW rating and pSLC size (not in the KB; the web reader's question).

## 7. Sources read

`architecture/config.md` (§2.4, §7.1, §8.1), `architecture/core.md` (§2-6, §11), `architecture/drivers.md:139-141`,
`working/drop-frames/README.md`, `recipe.md`, `media-tune-file.md`, `night-2026-11-01.md:1-60,140-200`,
`inspection-2026-11-02.md:445-480,520-535`, `tests-2026-11/{tier1-prep-2026-11-03,tier2-plan-2026-11-04,preregistration,
findings-2026-11-02,findings-2026-11-03,findings-2026-11-04,findings-evening4-supervised-2026-11-04,observations-2026-11-04,
takes}.md`, `working/handoff-drop-frames-{tier1,tier2,fable}.md`, `working/storage-answer.md`, `working/phaselock-answer.md`,
`working/dng-chain-feasibility.md` (§0-4, §6-7), `working/sensor-capabilities.md:40-54`, `fork-log.md`,
`lessons/hardware-log.md:55-100,240-300,575-650,700-1044`, `lessons/upstream-issues.md:46-53`,
`working/tools/core.py`, `working/tools/webui_client.py`, `working/tools/drop-frames-2026-11-01/{take3v3.sh,take_logger.py,
b1-arm.sh,e3-unit.sh,e4-helper.sh,e4-install.txt,e4-sudoers}`, `working/dng-chain/patches/README.md`,
`working/dng-chain/patches/0008-rec-web-cdng-fixes-...patch:46-52`, `working/handoff-T26-T30.md:12,70`,
`working/port-raw/s2-storage-core.md:4-7,223-228`, `working/compare-raw/a4-core-writer.md:192-196,239-240`,
`working/dual-sensor/claim-check.md:519,622-624`. Nothing ran on the camera or on any network host.
