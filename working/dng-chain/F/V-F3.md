# V-F3: verification of F3 (CPU time and DRAM bandwidth), build 6ef0ddc

Verifier V-F3, 2026-11-01. Read-only. Checked against /home/user/Apertar-Core `6ef0ddc` (`CC` = src/camera/CameraController.cpp, `CE` =
src/cdng/CdngEncoder.cpp, `APP` = src/ApertarCoreApp.cpp, `LC` = src/cdng/LogCurve.hpp), upstream libcamera `c682979`
(/home/user/raspberrypi/libcamera), the kb working tree (`HL` = lessons/hardware-log.md, `CHD` = working/clearhdr-design.md), and two web
sources re-opened today. Every derived MB/frame and GB/s figure was recomputed (python, this session). Nothing ran on the Pi.

## 1. Verdict per mode on F3's INSIDE / MARGINAL / OUTSIDE calls

| Mode, dimension | F3 | V-F3 | The one fact that decides it |
| --- | --- | --- | --- |
| (A) 4K SDR 12-bit 50 fps, CPU | INSIDE, 2.3-3.0 of 4 cores, confidence low-medium | **CONFIRMED as stated, with F3's own low confidence** | No per-thread CPU was ever measured in this mode; the only bound is T34 M3 (`HL:586-592`): 44 files/s with `peak_queue` 2-3/12 means the four writers had slack, but that bounds writer CPU only by "< 4 cores". The verdict rests on an untested decode estimate (8-20 ms per DNG). Nothing in the kb contradicts INSIDE; nothing measures it either |
| (A) DRAM average | INSIDE, 4.35 GB/s, margin >= 5.7 GB/s | **CONFIRMED on bytes, WEAKENED on margin** | 87.1 MB/frame reproduces exactly (8.29+29.0+0.04+16.59+8.29+12.44+12.44 = 87.09). But the "10-12 GB/s practical" ceiling is the optimistic end: the only multi-stream figures on the web are STREAM Scale/Triad ~7.2 GB/s and Copy ~9.9 GB/s (snippets, host unreachable), and memset fell to 9.7 GB/s after the Dec-2024 SDRAM tuning (web, #58). Against 7-10 GB/s the margin is 2.6-5.6 GB/s, still INSIDE |
| (B) linear 25 fps, CPU | INSIDE, 1.7-1.8 cores, CameraManager ~20 ms of 40 | **CONFIRMED** | Derived from a real load measurement (`HL:160-164`: 54 % at 26.45 fps, cores 59/44/48/38). F3 picked the lower of two readings of the same thread (54 % PMU run vs 61 % in the T25 pass, `HL:143-144` = 23.5 ms/frame); at 25 fps the thread is 51-59 % of a core, not 50. Still INSIDE |
| (B) linear DRAM | INSIDE, 5.20 GB/s, margin >= 4.8 | **CONFIRMED on bytes, WEAKENED on margin** | 208.2 MB/frame reproduces (208.15). Against 7-10 GB/s practical the margin is 1.8-4.8 GB/s. The decisive measured fact is the one F3 cites: A0 and A1 ran 10 min clean at this load (`HL:736-760`), so the average is inside whatever the ceiling is |
| (B) Log 25 fps, CPU | INSIDE, copy worker 14-25 ms of 40, confidence low | **CONFIRMED, with a note that the LUT estimate is probably high** | `LC:180-184` is a scalar `samples[i] = table[samples[i]]` loop over a 128 KiB table that fits L2; the loads are independent across iterations, so 1-2 ns per lookup (8-17 ms) is a dependent-latency figure, not a throughput figure. 0.5-1 ns (4-8 ms) is at least as plausible. Either way the worker stays under 40 ms. Never timed: the label is right |
| (B) Log DRAM | MARGINAL, 5.83 GB/s (+0.63) | **CONFIRMED** (and stronger against a 7-10 GB/s ceiling: 58-83 % of practical) | +24.9 MB/frame net (+33.18 LUT, -4.15 kernel copy, -4.15 NVMe) = +0.62 GB/s reproduces. The only Log take lost 10 of 117 frames with the WebUI open (`HL:782-783`), n = 1, confounded |
| "Log is a cost, not a lever" | | **CONFIRMED** | Code: the LUT runs on the copy after `releaseHeldRequest` (`CC:4871-4890`), so it cannot shorten the camera hold; the writer then takes the non-identity path (`copy.view.bitDepth` set to 12, `CC:4885`; `rowCopyIsIdentity` false for unpacked 12-bit, `CE:1082-1091`) and packs through the scratch. Log adds a CPU pass and DRAM traffic and removes only NVMe bytes that were never the limit (415 MB/s clean for 10 min) |
| "TDN the largest DRAM term" | | **CONFIRMED as arithmetic, UNVERIFIED as state** | TDN read + write = 2 x 18.73 = 37.46 MB of 208.2 (18 %) in (B), 18.38 of 87.1 (21 %) in (A): the largest single removable term in both tables (next: the swap 33.8 MB, which the L2 fork moves but does not remove). Whether the Pi's tuning has `tdn` is unverified (F3 says so; brief says so) |

## 2. Load-bearing numbers

| # | Claim in F3 | What I found | Label | Where |
| --- | --- | --- | --- | --- |
| 1 | (B) linear 208.2 MB/frame -> 5.20 GB/s at 25 fps | 16.896 + 33.792 + 16.896 + 57.58 + 0.04 + 33.178 + 33.178 + 16.589 = 208.15; x25 = 5.204 GB/s | **confirmed arithmetic**; matches q3 row 32 (208.18 "before L1") | `working/research-30fps/q3-bandwidth.md:321` |
| 2 | (A) 87.1 MB/frame -> 4.35 GB/s at 50 fps (60 fps: 5.22) | 87.09; x50 = 4.355; x60 = 5.226 | **confirmed arithmetic** | this session |
| 3 | Variants: L1 fork 195.5 -> 4.89; TDN off 170.7 -> 4.27 (-0.94); Log 233.0 -> 5.83 (+0.63); spill 6.45; pre-6ef0ddc upper 6.03; (A) TDN off 68.7 -> 3.43; spill 5.60 | 195.48 / 4.887; 170.69 / 4.267 / -0.936; 233.03 / 5.826 / +0.622; 6.448; 6.033; 68.72 / 3.436; 5.599 | **confirmed arithmetic** | this session |
| 4 | (A) "TDN at 16-bit 104.8 -> 5.24" | own table gives 87.1 + (45.6 - 29.0) = 103.7 -> 5.19; 104.8 is R8's delta (101.4 - 83.7 = 17.7) pasted onto F3's base | **minor inconsistency** (0.05 GB/s), not load-bearing | F3 §2.1 (A) variants; `R8.md` §4.1 |
| 5 | Core share (B): rows 6+9+10 = 82.9 MB = 2.07 GB/s, CPU part 66.4 = 1.66 | 82.94 / 2.074; 66.36 / 1.659 | confirmed | this session |
| 6 | Core share (A): 49.8 MB = 2.49 GB/s, CPU part 37.3 = 1.86 | 49.77 / 2.488; 37.32 / 1.866 | confirmed | this session |
| 7 | CFE readout 16,896,000 B; active 16,588,800; file 16,590,340 | `frame_bytes=16896000` at CHD:120 (journal line quoted); 16,590,340 B file at `HL:139`; 3840x2160x2 = 16,588,800 (+1,540 B header/IFD) | confirmed | `CHD:120`, `HL:139` |
| 8 | Measured cycles/frame 25 M -> 36 M, IPC 1.87 -> 1.30, instructions ~47 M and L3 refills 0.57 M unchanged, stall_backend 12 -> 21 %, 54 % busy at 26.45 fps | Table at `HL:157-162` says exactly that; cores 59/44/48/38, "Five other Core threads at 18-20 %", `nr_writeback` ~3 MB at `HL:164` | **confirmed** (F3's "HL:159-162" is within two lines) | `HL:157-164` |
| 9 | BE start->done 13.4 -> 34.6 ms, BE start interval 33.3 -> 36.2 ms, swap 6.1 -> 9.9 ms, stats 5.8 -> 7.1 ms | Stage table at `HL:184-193` says exactly that | **confirmed** (F3's "HL:188-191") | `HL:184-193` |
| 10 | Buffered `dd` 561 MB/s -> 21.71 fps, 19 gaps; O_DIRECT `dd` 759 MB/s -> 25.00, 0 gaps; Core idle, 16-bit Clear HDR; "CHD:125-133" | Table at `working/clearhdr-design.md:127-133` (header at :125), entry "2026-10-26 00:40", Core idle, frames counted from the IPA per-frame line; `taskset -c 3` 572 MB/s 19.34 fps 34 gaps; `taskset -c 0` 555 MB/s 21.71 fps 18 gaps | **confirmed** file and lines. F3's gloss "page-cache copy + writeback + reclaim" is **weakened**: CHD:135 says "Gaps start 0.6-1 s into the write with ~800 MB RAM free, so not reclaim". F3 §2.3's "reclaim active (free 923 -> 157 MB)" for this run is **not in CHD**; those numbers do not appear anywhere in the kb that I could find (grep) | `CHD:124-135` |
| 11 | `rowCopyIsIdentity` true only for unpacked 16-bit and unpacked 8-bit with 1 byte/sample; false for Csi2Packed and PispCompressed1 | Code at `CE:1082-1091`: returns false for Csi2Packed/PispCompressed1, true for Bits16, `unpackedBytesPerSampleForFrame(frame) == 1u` for Bits8, false otherwise. Used at `CE:1992-1993` (`!payloadCopyForced() && rowCopyIsIdentity(frame)` -> `writeRowsDirect`); `writeRowsDirect` is one `write()` when `stride == rowBytes` (`CE:1123-1126`) | **confirmed** | `CE:1082-1091, 1123-1141, 1992-1993@6ef0ddc` |
| 12 | Log 12-bit still copies: the copy worker sets `view.bitDepth = targetBits` (12) on an unpacked 2-byte view, so the writer takes `packDng12Row` through the scratch | `CC:4877-4890`: `applyCdngLogFrame` on `rawData`, then `copy.view.bitDepth = static_cast<RawBitDepth>(log->params.targetBits)`; `writeDngRowBytes` else-branch -> `Csi2RawConverter::packDng12Row` (`CE:1178-1181`) | **confirmed** | `CC:4877-4890@6ef0ddc`, `CE:1143-1183` |
| 13 | SDR COMP1 still copies: `PispCompressed1` -> `unpackPispCompressedRowToPacked12` | `CE:1155-1163`: PispCompressed1 with layout 12-bit -> `unpackPispCompressedRowToPacked12`; identity false (`CE:1084-1085`) | **confirmed** | `CE:1155-1163` |
| 14 | SDR 12-bit raw stream is COMP1 on the CFE (8.29 MB) even for uncompressed cDNG | Core requests `sensorMode.rawPixelFormat` (CSI2P for 12-bit, `CC:8052-8062`); upstream `pisp.cpp:1212-1221@c682979` turns a CSI2-packed request into `PISP1` 16-bit; the TDN/Stitch nodes get the same CFE format (`pisp.cpp:1493-1496`). Fork behaviour not readable; `HL:857-864` confirms COMP1 observed on the camera for SDR lossless, the uncompressed case is inferred from the same rule | **probable** (as F3 labelled it) | `CC:8052-8062@6ef0ddc`, upstream `pisp.cpp:1212-1221, 1493-1496` |
| 15 | Scratch: 64 rows x 7680 = 491,520 B (16-bit), 64 x 5760 = 368,640 B (12-bit packed), 34 writes per 4K frame | `configuredPayloadWriteRows()` default 64 (`CE:105-120`); 2160/64 = 33.75 -> 34; comment at `CE:102-104` says the same | confirmed | `CE:102-120` |
| 16 | Copy worker with Log: 14-25 ms = sync + memcpy 6-8 ms + LUT 8-17 ms | Memcpy + 4 sync walks measured once at "Core copy 4, sync 4" (`CHD:122`, on the camera thread, cached heap, idle-ish) = 8 ms; 16.59 MB at 6.0 GB/s = 2.8 ms idle, 4.0 ms x1.45. LUT: `LC:180-184` scalar loop, 8,294,400 lookups, table 65,536 x 2 B = 128 KiB (fits the 512 KiB L2). 1-2 ns per lookup assumes a dependent-latency chain; the iterations are independent, so throughput-bound 0.5-1 ns (4-8 ms) is at least as likely. Band 10-25 ms; **never measured** | estimated; F3's low confidence is right | `CHD:122`, `LC:180-184` |
| 17 | Hold on the camera request = sync + memcpy only; Log after `releaseHeldRequest`; cap buffers - 2 | `CC:4862-4871`: memcpy, end sync, `releaseHeldRequest(copy.request)`, then the Log block. Cap: `std::max(1, rawCameraBufferCount(clearHdr) - 2)` at `CC:8305-8309` (F3 says `CC:8229`; wrong line, right fact) | confirmed | `CC:4862-4890, 8305-8309` |
| 18 | Pi 5 DRAM: 17 GB/s interface; 512 kB L2 per core; 2 MB L3; 2.4 GHz | bcm2712.adoc: "A 32-bit LPDDR4X memory interface provides up to 17 GB/s of memory bandwidth"; "512 kB per-core L2 caches and a 2 MB shared L3 cache"; "clocked at up to 2.4 GHz" | **web, confirmed** | https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/processors/bcm2712.adoc |
| 19 | CM5 tinymembench memcpy 6012.7 MB/s, memset 12646.0; sbc-bench memcpy 5705 -> 5892, memset 12568 -> 9675 after the Dec-2024 SDRAM/NUMA update | Page says: standard memcpy 6012.7 MB/s; standard memset 12646.0 MB/s; sbc-bench before/after: memcpy 5705.0 -> 5892.4, memset 12567.9 -> 9675.1; DRAM latency 94.9 ns (16 MB) / 110.0 ns (64 MB) | **web, confirmed** | https://github.com/geerlingguy/sbc-reviews/issues/58 |
| 20 | "Practical ceiling 10-12 GB/s for a mixed read/write stream set" | One-core memcpy traffic 12 GB/s and memset 9.7-12.6 GB/s are single-stream figures; the multi-stream figures available are STREAM Scale/Triad ~7.2 GB/s (OpenBenchmarking 2407154, search snippet) and Copy ~9.9 GB/s (2604285, snippet); openbenchmarking.org does not resolve from this session (needs allowing in the network settings). No source supports 12 GB/s for a *mixed* set; **7-10 GB/s** is what the evidence carries | **estimated, optimistic**; weakened | web search 2026-11-01; `V/H8.md` §3.1 |
| 21 | Writers' CPU per DNG (B): 29 ms derived, ~25 ms with the direct path | "Five other Core threads at 18-20 %" (`HL:164`) at 26.45 fps: if 4 are writers, 4 x 0.19 / 26.45 = 28.7 ms; if the copy worker is one of them, F3's attribution holds. q3 row 53 uses all five (36 ms per frame for copy + writers). The -2.8 to -4 ms for the removed scratch memcpy is a model. Nothing measures a writer alone | **derived, attribution probable** (as F3 says) | `HL:164`, `q3-bandwidth.md:342` |
| 22 | Writers' CPU per DNG (A): 25-38 ms, decode 8-20 ms | No measurement exists. M3 (44 files/s, queue 2-3/12, `HL:586-592`) shows the writers kept up but bounds CPU only loosely | **estimated** (as F3 says); the widest band in the report | `HL:586-592` |
| 23 | CameraManager thread (B): ~20 ms per frame at load | PMU run 54 % / 26.45 fps = 20.4 ms (`HL:160-162`); T25 pass 61 % at ~26 fps = 23.5 ms (`HL:143-144`); L1 43 % / 28.5 = 15.1; L2 34 % / 27 = 12.6 (`HL:210, 226`) | confirmed; F3 used the lower reading | `HL:143-144, 160-162, 210, 226` |
| 24 | Scheduling: P(all four cores busy) ~ 4.7 %, slice 2.25 ms, 0.2-0.8 ms expected per frame, tail a few ms (V/H15 §3.2) | 0.59 x 0.44 x 0.48 x 0.38 = 0.0474; V/H15 §3.2 states the same chain (weights 3121/1024, base slice 0.75 x (1 + ilog2 4) = 2.25 ms, 3-4 wake-ups per frame). The independence assumption is the weak point: writer wake-ups are correlated with the copy worker's enqueue, so P(all busy at the CameraManager's wake-up) is higher than the product. Run-queue wait never measured | derived from V/H15; **plausible, unmeasured** | `V/H15.md` §3.2 |
| 25 | `APERTAR_RT_CAPTURE_PRIORITY=N`: SCHED_FIFO on the completion thread alone, falls back to nice -5; `CC:8680-8692` | Code at `CC:8672-8699`: `unsignedEnvValue("APERTAR_RT_CAPTURE_PRIORITY", 0, 0, 99)`, `sched_setscheduler(tid, SCHED_FIFO, &param)`, log line, else `setpriority(PRIO_PROCESS, tid, -5)`. Drop-in `config/apertar-core-capture-priority.conf:3,7` has `LimitNICE=-5`, `LimitRTPRIO=80`. README:294 describes it as "the preferred shape of the scheduling A/B" | confirmed | `CC:8672-8699@6ef0ddc`, `config/apertar-core-capture-priority.conf`, `README.md:294-295` |
| 26 | `APERTAR_RT=1` start-script shape (chrt -f 70, ionice -c2 -n0, taskset -c 1-3) | `scripts/start-apertar-core.sh:25-40` exactly as described | confirmed | `scripts/start-apertar-core.sh:19-40` |
| 27 | Web preview cap 30 fps, `APERTAR_WEB_PREVIEW_RECORDING_FPS`, 0.2-0.5 ms per frame on the completion thread | `APP:78-100`: `kWebPreviewMaxFps = 30.0`, the env parser, the comment "about 0.2 to 0.5 ms per frame measured idle in the kb"; V/H4 §2.2 derives 0.23 ms idle from CHD:97-98 and 0.3-0.5 ms under load as an estimate | confirmed code; the 0.3-0.5 ms is an estimate | `APP:78-100`, `V/H4.md` §2.2 |
| 28 | Cached COMP1 dma-buf (`CC:8196-8200@92d0970`) | `92d0970:CC:8194-8200`: `cachedRaw` when `PispCompressed1` or Clear HDR unpacked, `allocateCachedBuffers` from `/dev/dma_heap/vidbuf_cached` (6ef0ddc: `CC:8277-8280, 8370`) | confirmed | `CC:8194-8200@92d0970` |
| 29 | A0/A1 10 min clean at 25 fps linear; A2 lost 1491; 10-31 short takes 2/9/4/10 with WebUI open, the 10-of-117 one with Log | `HL:736-760` (A0: 15001 frames, `peak_queue=2/12`; A1 15000, `peak_queue=1/12`; A2 13503, `dropped_gap_estimate=1491`); `HL:779-785` (351/2, 263/9, 145/4, 117/10 "that one with Log on") | confirmed | `HL:736-785` |
| 30 | Swap 89 MB (T22), 860-1170 and 1152 -> 1505 MB during T23 takes | `HL:88` "89 MB of swap was in use"; `tutorials/progress/T23.md:18-19` "swap used 860-1170 MB", "swap used 1152->1505 MB" | confirmed | `HL:88`, `T23.md:18-19` |
| 31 | hwcount.py events 0x11, 0x08, 0x24, 0x2a, 0x37, 0x19 | `working/tools/hwcount.py:13-14` lists exactly those | confirmed | `working/tools/hwcount.py:13-14` |

## 3. Errors found

1. **Reclaim attributed to the buffered-`dd` run (unsupported).** F3 §2.1 glosses the 561 MB/s run as "page-cache copy + writeback + reclaim" and §2.3
   says "the 10-26 buffered `dd` with reclaim active (free 923 -> 157 MB) cost CFE frames with Core idle (CHD:131, V/H8 §2 row 4)". CHD:135 says the
   opposite for that run: gaps started 0.6-1 s in "with ~800 MB RAM free, so not reclaim". The 923 -> 157 MB figures are not in CHD and I could not find
   them in the kb. Correction: the measured aggressor is the page-cache write + writeback path, not reclaim; the `DONTNEED=off` "risk arm" argument in
   §2.3 and lever 2 loses its cited support (it may still be true; it is not measured).
2. **Lever 6 mixes gross and net.** "Log costs +33 MB/frame DRAM (+0.83 GB/s)" is the LUT pass alone; F3's own variant table gives the net +24.9 MB
   (+0.62 GB/s) after the smaller kernel copy and NVMe read. The verdict row uses the net GB/s with the gross MB. Correction: +24.9 MB, +0.62 GB/s net
   (+33.2 MB, +0.83 GB/s gross).
3. **(A) "TDN at 16-bit 104.8 -> 5.24"** should be 103.7 -> 5.19 from F3's own table (the 17.7 MB delta is R8's, F3's is 16.6). Not load-bearing.
4. **Wrong line for the held-request cap**: F3 cites `CC:8229`; the `buffers - 2` cap is at `CC:8305-8309`. The fact is right.
5. **The practical DRAM ceiling is overstated.** 10-12 GB/s is built from single-stream memcpy/memset. The multi-stream figures that exist (STREAM
   Scale/Triad ~7.2 GB/s, Copy ~9.9 GB/s, both snippets; memset 9.7 GB/s after the SDRAM tuning the Pi probably runs) support 7-10 GB/s. The averages
   stay below either band, so no verdict flips, but every "margin >= x GB/s" in §1 and §2.4 should read 1.8-4.8 (B linear), 1.2-4.2 (B Log),
   2.6-5.6 (A) against 7-10 GB/s.
6. **CameraManager per-frame cost picks the lower of two readings.** 20.4 ms (PMU run) vs 23.5 ms (T25 safety pass, same build, same mode,
   `HL:143-144`). At 25 fps the thread is 51-59 % of a core. INSIDE either way.
7. **The LUT estimate's model is the wrong one.** 1-2 ns per lookup treats each lookup as a dependent cache-hit latency; `applyTable` has no loop-carried
   dependency, and the 128 KiB table sits in L2. The honest band is 4-17 ms (0.5-2 ns). Does not change the verdict; the "14-25 ms" nearest-actor
   claim becomes "10-25 ms".
8. **Scheduling P(all busy) assumes independent cores.** Writer and copy-worker activity is triggered by the same frame, so the four cores' busy
   intervals are correlated and the product (4.7 %) is a lower bound. V/H15 §3.2 itself notes 10-20 % with the WebUI. The 0.2-0.8 ms expected gain
   should be read as a floor. Unmeasured on the Pi, as F3 says.

No wrong code reading was found: every `path:line` for `CE` and `CC` that I opened says what F3 says it says (rows 11-13, 15, 17, 25-28).

## 4. What the report missed

- Nothing that changes a verdict. Two things it could have used:
  - The T25 safety-pass reading (61 % at ~26 fps, `HL:143-144`) alongside the PMU reading; it would have widened the CameraManager band to 20-24 ms.
  - The kb's own correlated-load point: in the 2026-10-26 stage table, 78 % of BE completions were logged right after a swap/stats run (`HL:192`),
    which is the serial-stage effect F2 owns but also says the completion thread's wake-ups cluster with its own work, which matters for the
    scheduling estimate (error 8).
- The report correctly flags, and I confirm as unverified: which libcamera the Pi runs today (`HL:207, 221` fork vs `HL:248` "system libcamera
  7e9fef0"), the tuning's `tdn` state, the actual thread priorities (no `capture scheduling` journal line is quoted anywhere in the kb), and whether
  the scratch stays cache-resident.
- One point in F3's favour that it under-sells: with the direct path, Core's CPU-side DRAM traffic for (B) linear (66.4 MB/frame) is the same as
  cinepi-raw's (V/H8 §1.6), so the operator's "cinemate did not drop here" cannot be a DRAM-bytes story for linear 16-bit any more; it has to be the
  TDN state, the libcamera build, or the WebUI. That strengthens "TDN the largest term" as the thing to settle first.

## 5. Corrected verdict and margin

| Mode | CPU | DRAM average | Confidence |
| --- | --- | --- | --- |
| (A) 4K SDR 12-bit 50 fps | **INSIDE**, 2.3-3.0 of 4 cores estimated; nearest actor the four writers (COMP1 decode + exFAT at 50 files/s), 25-38 ms CPU per DNG against an 80 ms wall budget each | **INSIDE**, 4.35 GB/s (TDN at COMP1) = 25 % of 17.07, 44-62 % of a 7-10 GB/s practical band; margin 2.6-5.6 GB/s | low-medium: no per-thread CPU and no PMU reading exists in this mode; `top -H` + `hwcount.py` on one 60 s take settles it |
| (B) linear 25 fps | **INSIDE**, 1.7-1.8 cores; CameraManager 20-24 ms of 40 with the system libcamera (12-15 ms with the fork) | **INSIDE**, 5.20 GB/s = 30 % of 17.07, 52-74 % of practical; margin 1.8-4.8 GB/s; A0/A1 ran 10 min clean at exactly this load | medium |
| (B) Log 25 fps | **INSIDE**, 1.9-2.1 cores; copy worker 10-25 ms of 40 (LUT never timed) | **MARGINAL**, 5.83 GB/s net (+0.62 over linear, +0.83 if the 368,640 B scratch spills: 6.45) = 58-83 % of practical, all of the increment a CPU stream over a 16.6 MB copy against a BE measured to stretch 2.6x under exactly such streams; n = 1 Log take, lossy, WebUI open | low |

Log is a cost, not a lever, in this dimension: **confirmed** from code (`CC:4871-4890`, `CE:1082-1091, 1178-1181`). TDN is the largest single
removable DRAM term in both modes: **confirmed arithmetic** (37.46 of 208.2 MB; 18.38 of 87.1 MB), state unverified. The decisive measurement F3 names
(`top -H` per thread + `hwcount.py` on the CameraManager tid, 60 s per mode, WebUI closed then open, with the tuning file, libcamera build and
`capture scheduling` line recorded) is the right one and is unchanged by this verification.
