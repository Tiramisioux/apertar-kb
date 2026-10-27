# Q7: what Cinemate records about IMX585 Clear HDR 3840x2200 16-bit at 30 fps

Reader: q7-cinemate (Claude Opus 5.5, cloud subagent), 2026-10-26. Trees, all read-only: cinemate `d6cc93e`, cinemate-handbook
`c99ff77`, cinepi-raw `63a08d5`, Cinemate's libcamera `bfe0b76` (branch `cinemate`), libcamera-apertar `6b0b49f`, libcamera-qbc
`7e9fef0`, imx585-v4l2-driver `18c1eb2` (`cinemate-modes`), imx585-apertar `98b9862`, apertar-core `f60e301` (via `git show` only),
apertar-kb (brief `working/handoff-30fps-clearhdr16.md`, `lessons/hardware-log.md:51-233`, `working/clearhdr-compare-notes.md`).
Web: WebSearch works. WebFetch reached github.com. hackaday.com failed DNS. Labels: CONFIRMED = I opened the line or page;
PROBABLE = derived, reasoning given; UNCONFIRMED = needs the Pi or a source I do not have.

## Short answer

1. **Cinemate's "30.00 fps overclocked, 21.99 stock" is a computed ceiling, not a recorded take.** CONFIRMED. The number is
   `1e6 / FrameDurationLimits.min` after `configure()`, as `cinepi-raw --list-cameras` prints it. The arithmetic reproduces it
   exactly: HMAX 550, VMAX 4500, and the 380 or 580 MPix/s bound (§1). No frames were counted, and no recording medium or preview
   is involved.
2. **Nothing in Cinemate's docs, handbook or git history records a counted 30 fps take in this mode.** CONFIRMED for the trees read.
   Every counted 4K 16-bit record is at 25 fps or at 21 fps. The 25 fps takes are clean after the 2026-09-15 preview fixes. The
   21 fps soak stalled after 15-22 s on NTFS. The handbook says outright that only the *advertised* ceiling was ever observed,
   never sustained capture (`hardware-log.md:392-393@c99ff77`).
3. **Cinemate does no less DRAM work per frame than Apertar** (PROBABLE, §3). It runs the same rev16 swap on libcamera's thread.
   It renders a 1256x720 back-end output every frame. It copies the full 16.9 MB into a pooled buffer before releasing the
   request, then does a buffered `write()`. It skips the software raw stats, but it adds a preview pass that reads about 11 MB of
   the raw. Estimate: about 166 MB per frame for Cinemate against about 158 MB for Apertar L1.
4. **Patrik's "similar limits with Cinemate" is what the code predicts.** PROBABLE. I found no evidence that any Pi 5 setup has
   recorded this mode at 30.00 fps with 0 drops: not Cinemate, not the INNO-MAKER reference stack as Cinemate describes it, not
   will127534's README, and not a web search. CONFIRMED only for the sources listed.
5. **The RP1 overclock is not what separates the two stacks.** CONFIRMED by arithmetic and KB records. Apertar's bound is
   646.7 MPix/s, above the 518.4 needed. Its idle preview already delivers 30.00 fps, so the line-time bound is not binding there.
6. **One real structural difference is worth a take: PiSP COMP1** (PROBABLE). With `--mode 3840:2200:16:P`, cinepi-raw and
   Cinemate's libcamera capture this mode compressed. The capture front end (CFE) then writes 8.45 MB per frame instead of 16.9 MB,
   there is no swap, and the back end reads half the bytes: about 96 MB per frame (-42 %). COMP1 is lossy (step at least 16 codes).
   Apertar's libcamera forces unpacked 16-bit for Clear HDR. A COMP1 take at 30 fps on Cinemate's stack is the cheapest bandwidth
   test that needs no build (Experiment X2).

## 1. (a) What `docs/sensors.md`'s 21.99 / 30.00 is

| Claim | Source | Label |
| --- | --- | --- |
| Mode 4: ClearHDR 3840x2200, 16-bit, all-pixel, "Max FPS" 21.99, "Max FPS overclocked" 30.00, 16.9 MB per DNG | `cinemate/docs/sensors.md:32,38@d6cc93e` | CONFIRMED |
| "Both fps columns are the changelog's measured figures for 3.4.0, taken at the sensor's highest link frequency, 1039.5 MHz. Max FPS is the stock RP1 pixel-rate ceiling (`--max-pixel-rate 380`); overclocked is ... the `rp1-overclock` overlay's 580" | `sensors.md:40-42@d6cc93e`; the same table in `docs/changelog.md:39-49` (3.4.0) | CONFIRMED (that is what the text says) |
| The table first appeared in the 2026-09-04 docs rewrite, not in a measurement commit | `git log -S'21.99' -- docs/` in cinemate: `7cba6fe` (2026-09-04), then `33e4f1c`, `d606429` | CONFIRMED |
| What `--list-cameras` prints per mode is `fps = 1e6 / FrameDurationLimits.min()`, read after `cam->configure()` | `cinepi-raw/core/options.cpp:409-424@63a08d5` | CONFIRMED |
| Cinemate builds its mode table from that listing, run under the same `--max-pixel-rate` as the launch | `cinemate/src/module/sensor_detect.py:2715-2724@d6cc93e` | CONFIRMED |
| Cinemate's own code says the advertised value "is an electrical property and says nothing about what this storage/CPU actually sustain" | `sensor_detect.py:2278-2281@d6cc93e` | CONFIRMED |
| Docs: "Actual achievable FPS without dropped frames depends on your storage device and filesystem, which the sensor's own reported numbers don't account for" | `sensors.md:197@d6cc93e` | CONFIRMED |

**The arithmetic.** It reproduces both numbers from code, which is why I call them computed, not delivered.

- The sensor side (driver `imx585-v4l2-driver/imx585.c@18c1eb2`):
  - The 3840x2200 16-bit entry uses `HMAX_table_4lane_4K_12bit` (`:1720-1728`). That table holds 660 at 720 MHz and 550 at
    891 MHz (`:293-294`).
  - Clear HDR floors HMAX at 550 (`:121`, `:3314`) and sets VMAX = 2250 x `hdr_scale` 2 = 4500 (`:3274`, `:3301`).
  - The driver reports pixel_rate = width x 74.25 MHz / HMAX (`:3382-3386`).
  - At 891 or 1039.5 MHz: line = 550 / 74.25 MHz = 7.407 µs. Frame = 4500 x 7.407 µs = 33.33 ms, so **30.00 fps**. The pixel rate
    needed is 3840 / 7.407 µs = **518.4 MPix/s**.
  - The README confirms the floor: "Clear HDR is floored at HMAX 550 regardless of link rate", so 2079 Mbps runs "exactly the same
    sensor line timing it uses at 1782" (`README.md:236-241`). CONFIRMED.
- The IPA side (`libcamera/src/ipa/rpi/common/ipa_base.cpp:589-610@bfe0b76`): when the sensor's pixel time is shorter than
  `minPixelProcessingTime`, the IPA stretches the line to width x that minimum. The minimum is `1us / LIBCAMERA_RPI_MAX_PIXEL_RATE`
  (`src/ipa/rpi/controller/controller.cpp:116-139, 297-298@bfe0b76`).
  - At 380: line = 3840 / 380 MPix/s = 10.105 µs. Frame = 4500 x 10.105 µs = 45.47 ms, so **21.99 fps**
    (380e6 / (3840 x 4500) = 380e6 / 17.28e6 = 21.991).
  - At 580: 3840 / 580 = 6.62 µs, which is below 7.407, so there is no stretch and the rate stays at 30.00 fps. CONFIRMED.
- Where the 380 and 580 come from: `rp1_regime.py:70-72@d6cc93e` says "Measured on a CM5: stock 200 MHz -> 380 MPix/s, overlay
  -> 580". The overlay asks for 300 MHz and gets 333.33 MHz (`hardware-log.md:286-315`).

**Conditions, medium, preview, frames counted.**

- The number depends only on the driver's HMAX/VMAX and the `--max-pixel-rate` passed in. It does not depend on recording, the
  medium, the preview size or the DNG path. CONFIRMED (§1 arithmetic). No frames are counted when it is produced.
- The changelog says "measured at 1039.5 MHz". PROBABLE that this was read from the mode listing, and possibly not even at that
  link rate:
  - The driver README says 2079 Mbps "has not been re-tested since the blend fix" (`README.md:257-258@18c1eb2`).
  - The 2026-08-31 milestone, the run that made 16-bit work, ran at 891 MHz and says "2079 Mbps/lane was not re-tested after the
    fix" (`hardware-log.md:1108-1111, 1162`).
  - The value would be the same 30.00 at 891 MHz anyway, because of the HMAX floor.
- At Cinemate's default link (720 MHz, `sensors.md:92`), this mode cannot reach 30 at all. HMAX 660 gives
  74.25e6 / (4500 x 660) = **25.00 fps** with the overclock and 21.99 without it (the bound wins: 10.105 µs > 8.889 µs). PROBABLE
  from the arithmetic. This matches the handbook's "with the overlay active every mode advertises 25.00 fps" at the default link
  (`hardware-log.md:476-479`).
- For Apertar: link 891 MHz and `rp1-clk-333mhz`. Its libcamera computes 333.33 MHz x 2 px/clk - 20 = **646.7 MPix/s**
  (`libcamera-qbc/src/ipa/rpi/controller/controller.cpp:59-64, 135-145@7e9fef0`) and logs it (`working/clearhdr-design.md:88`). That
  is above 518.4, so Cinemate's 21.99 regime does not apply. The KB's idle-preview delivery of 30.00 fps (`hardware-log.md:161`)
  confirms the bound is not binding. CONFIRMED.

## 2. (b) Every Cinemate handbook and architecture entry on 4K 16-bit, 30 fps, overclock, storage, swap and bandwidth

All `cinemate-handbook/lessons/hardware-log.md@c99ff77` unless stated. "CM5" = Cinemate's dev or colour rig (CM5 / CM5 Lite 4 GB,
kernel 6.12.93). The operator's own camera is a Pi 5 (`:1612`).

| Date | Lines | Conditions | What is recorded | Bears on 30 fps 16-bit? |
| --- | --- | --- | --- | --- |
| 08-26 | 286-335 | dev CM5, imx477 | Overlay requests 300 MHz, gets 333.33 MHz. No `assigned-clock-rates` readable, so Cinemate passes the rate in by hand. | Mechanism only. CONFIRMED |
| 08-26 | 337-399 | dev CM5, imx585 mono, overclock on, bare `--list-cameras` (380) | 4K 12-bit advertises 43.80 at 380 against 66.85 at 580 (ratio 0.65520 vs 380/580 = 0.65517). **"Not established: that a take at 66.85 fps actually records cleanly at 580 on this board — only the *advertised* ceiling has been observed, not sustained capture."** (`:392-393`) | Yes: the ceiling is advertised, never counted. CONFIRMED |
| 08-26 | 441-445 | same | "ClearHDR halves each mode's advertised fps ... 3856×2180: 43.8 → ~21.9" at stock. "At 580 ... ≈ 33.4 fps" (older driver). | Advertised only. CONFIRMED |
| 08-26 | 464-482 | mono, 3856x2180 16-bit | With the overlay "every mode advertises 25.00 fps" at the default link. The 16-bit DNGs were a constant fill (6 unique values). | 16-bit capture not working yet. CONFIRMED |
| 08-26 | 700-716 | mono | Hypothesis: the pixel bound is in pixels/s but the CSI2-to-FE FIFO is a byte pipe, so it is "over-stated by 1.33x at 16 bpp". "Not proven." | See §5: Apertar's 0-overflow CSI-2 counters argue against it. PROBABLE |
| 08-27 | 731-822 | mono, links 1188/1440/1782/2079 | The RP1 D-PHY clamps above 1500 Mbps/lane (`dphy.c`) and warns, it does not refuse. 2079 degrades a mode over minutes; 1782 held for about 5 min. | Link margin, not throughput. CONFIRMED |
| 08-27/28 | 945-987 | mono, NTFS (`fuseblk`) on NVMe | "**every 16-bit soak (~355+ MB/s) stalled after ~15–22 s**: the RAM pool (173 frames ≈ 2941 MB) fills and frames stop arriving". 12-bit 21 fps soak (264 MB/s) clean, 2520/2520. "Advertised fps was identical with it on or off at every link rate (21.99 @1440, 30.00 @1782)". Default left at 1440 / stock. | Storage-bound at 21 fps on NTFS. The "identical on/off" line contradicts the arithmetic and the 08-26 entry (see below). CONFIRMED (text) |
| 08-31 | 1106-1170 | colour CM5 Lite, **exFAT NVMe, link 891 MHz, rp1-overclock**, 3840x2200 16-bit | "All seven modes work". dmesg VMAX=4500 HMAX=550. Judged visually; no fps or frame count. | The only record under 30 fps-capable settings, and no rate was counted. CONFIRMED |
| 09-13 | 1830-1892 | operator's camera, 4K 16-bit | The thumbnail added 2,712,960 B per frame (raw strip 16,896,000 B, file 19,609,788 B, +16.1 %). Later replaced by a ~5 KB JPEG (`:2031`). | At 30 fps the thumbnail era wrote 19.6 MB x 30 = 588 MB/s. PROBABLE (arithmetic) |
| 09-14 | 2226-2330 | colour, 25 fps | ClearHDR preview stage (cinepi-raw, CPU): 16-bit 4K in-place **21.9 ms median, 27.7 max**. "Against a 15ms budget and a 40ms frame period". | A per-frame CPU pass that reads the raw. CONFIRMED |
| 09-14 | 2367-2372 | 12-bit HD, 25 fps | Frame period locked at 40 ms even with a 34.7 ms stage (detached thread per request). It "eats headroom ... the original 102-drops-in-20-minutes report". | 12-bit, 25 fps. CONFIRMED |
| 09-15 | cinepi-raw `056b07f` msg; `ccmpPreviewStage.cpp:178-206@63a08d5` | 4K 16-bit, **25 fps** | The clamp measurement "dropped frames in 4K 16-bit — 208 drop events, FPS measured 6.24984 FPS settings 25". Fixed with a sample budget (61,440 samples per frame at 4K). "4K 16-bit did not drop before that build." | The only counted 4K 16-bit drop record, and it is at 25 fps. CONFIRMED |
| 09-15 | 3135-3209 | operator's camera, camera at 25 fps | A stale `config.txt` mtime drops the bound to 380, which "caps 3840×2200 16-bit at **21 fps**". "**The 4K 16-bit frame drops are also resolved**" by `ea53b2c` + `dca6748`. The measurement pass is 0.38 ms per frame. | 25 fps clean after the fixes. No 30 fps. CONFIRMED |

Architecture pages and other files:

- `architecture/cinepi-raw.md:32-55`: the RAM guard is a hard stop. Frame lifecycle: queue, then an encode thread pool, then a
  disk thread pool.
- `architecture/cinemate.md:166-172`: NTFS is "not recommended ... the Linux NTFS driver can drop frames under sustained 4K
  writes".
- `architecture/cinepi-raw.md:313-327` says 16-bit has "no correction in the tree at all". That page is stale against cinepi-raw
  `63a08d5`, which runs `correctHighlightsInPlace` for 16-bit (`ccmpPreviewStage.cpp:385, 607`). CONFIRMED.
- `open-threads.md:358-375`: the camera's `/home/pi/libcamera` has uncommitted edits, including "a live 580 MHz overclock" in
  `controller.cpp` and a ~1008-line `imx585.json` rewrite. So the Cinemate camera does not run exactly `bfe0b76`. CONFIRMED (as
  reported). The effect is UNCONFIRMED.

Topics the brief asked about and Cinemate has no measurement for (CONFIRMED by grep of handbook, docs and `architecture/`):

- The 16-bit endian swap's cost. It appears only as a correctness question (`:511-516`, `:638-642`, `:698`, `:836`).
- libcamera thread time.
- DRAM or memory bandwidth. The only "bandwidth" result is "sustained write bandwidth on NTFS-over-FUSE" (`:978`).
- NVMe vs SSD vs SD for 16-bit 4K at 30 fps.

The storage claims that exist are at 25 fps and mostly predate Clear HDR (12-bit):

- `docs/changelog.md:137-138` (3.3.1): "IMX585 25 fps at 4K to SSD without frame drops" and "switches to HD above 25 fps when an
  SSD is used".
- `changelog.md:21` (3.4.1): vmax cropping "reduces write speed needed ... some of the modes also works with normal SSD at
  25 fps".

**Internal inconsistency, unresolved.** The 08-27/28 entry has "identical on/off: 21.99 @1440, 30.00 @1782". No single bound
gives both numbers for a 3840-wide line:

- 21.99 at 1440 needs the 380 bound.
- 30.00 at 1782 needs a bound of at least 518.4.

The 08-26 entry records 25.00 at the default link with the overlay on. PROBABLE that the on/off cells did not get the bound they
were labelled with. Candidates are the `rp1_regime` mtime guard added that day (`b769e94`), and `clk_sys` reading 333 MHz in both
regimes (`hardware-log.md:855-857`, `rp1_regime.py:27-38`). Either way, "the overclock buys no frame rate here" (`:969-972`) is not
evidence about this mode's delivery.

## 3. (c) Per-frame work: Cinemate (cinepi-raw `63a08d5` + libcamera `bfe0b76`) against Apertar (Core `d9f00d4` + libcamera `6b0b49f`)

| Per-frame step | Cinemate | Apertar (brief §2/§8, KB) |
| --- | --- | --- |
| Raw format asked for | `--mode W:H:16:U` (imx585 packing `U`: `sensor_detect.py:55`, `resources/sensors.json` imx585 `"packing": "U"`, `cinepi_multi.py:684`). `16:U` maps to `SBGGR16`, `16:P` to `BGGR_PISP_COMP1` (`cinepi-raw/core/rpicam_app.cpp:122-132`). CONFIRMED. The comment calling 16:U "experimental ... FE writes garbage" (`:129-130`, July) is stale: the 08-27/08-31 entries record real 16-bit data on U. PROBABLE | Unpacked u16, forced for Clear HDR, "Override any packed/compressed format the user or the auto-pick chose" (`libcamera-apertar/.../pisp.cpp:1770-1776, 1854-1873@6b0b49f`). CONFIRMED |
| rev16 swap | In `cfeBufferDequeue` on the pipeline (CameraManager) thread, between `dmabufSyncStart/End`. Skipped only for PISP1 (`libcamera/.../pisp.cpp:1449-1459, 1723-1739@bfe0b76`; commit `bcdd7e17`). CONFIRMED | Same swap. L1: on the thread. L2: on a worker (`pisp.cpp:818, 878, 2220@6b0b49f`). CONFIRMED |
| SW raw stats | **None** (no `RawStats`/`processRawStats` anywhere in `src/` at `bfe0b76`). The handler warns "statistics will not be correct. You must use manual camera settings" (`pisp.cpp:1460-1462@bfe0b76`). Cinemate always passes `--shutter 20000` and `--awbgains` (`cinepi_multi.py:694, 703`). CONFIRMED | `processRawStats` (`pisp.cpp:2265, 3069@6b0b49f`), every 4th row pair on the Pi (`QBC_RAW_STATS_ROW_STEP=4`, brief §8). CONFIRMED |
| Back-end (ISP) output | One output: stream 0 `VideoRecording` YUV420, aliased to lores when a raw stream exists. Size = `--lores-width/height` = **1256x720** for 3840x2200 (`rpicam_app.cpp:614-677`, `hardware-log.md:1876-1877`). It is rendered every frame, in preview and while recording, and feeds HDMI (DRM), `ccmpPreview`, the MJPEG web preview and the DNG thumbnail. CONFIRMED (code). Exact BE cost: Q1 | About 1280x720 preview (brief §5 Q1). Number of BE outputs: Q1 |
| CPU post-processing (detached thread per request) | `ccmpPreview` is enabled for 16-bit Clear HDR (`ccmpPreviewStage.cpp:263-266, 385, 414`). Per frame it does a `BufferReadSync` of the raw, a 61,440-sample clamp measurement, and `correctHighlightsInPlace`: one Bayer quad per 1256x720 output pixel over 720 row pairs (`ccmp_preview.hpp:445-480, 607-611`). CONFIRMED. Bytes: 1440 of 2200 rows, every 64 B line touched (output pitch 3.06 px = 6.1 B), so 1440 x 7680 B = **11.1 MB read**. PROBABLE | None in Core's completion path (KB `clearhdr-compare-notes.md:67`, f60e301). PROBABLE for d9f00d4 |
| DNG assembly / copy | Encode worker: `dng_save` `write_pod`s each 7680 B row from the camera buffer into a pooled `posix_memalign` buffer, so **a full 16.9 MB memcpy** (`dng_encoder.cpp:1425-1433, 2172-2243`; `ifd_builder.hpp:173-181`). It also builds a colour-JPEG thumbnail from lores. The request is released only after this (`input_done_callback_` at `dng_encoder.cpp:2303-2307`, then `cinepi_recorder.hpp:158-174`). CONFIRMED. So the brief's "cinepi-raw writes DNGs straight from the camera buffer (no copy)" holds only for the completion thread. The DRAM copy is the same as Core T25's | T25 worker: dma-buf sync + 16.9 MB memcpy, then requeue (brief §2). CONFIRMED (brief) |
| Disk write | Disk worker: `open(O_WRONLY|O_CREAT|O_TRUNC)`, `POSIX_FADV_SEQUENTIAL`, one `write()` of the whole DNG, "standard buffered IO instead of O_DIRECT" (`dng_encoder.cpp:2351-2362`). No DONTNEED. CONFIRMED | Buffered. At f60e301: rows memcpy'd through a scratch of max(7680, min(4 MiB, max(256 KiB, 64 rows))) = 491,520 B (cache-sized), then `write()`, then `POSIX_FADV_DONTNEED` before close (`apertar-core src/cdng/CdngEncoder.cpp:1023-1045, 1860-1912, 1779@f60e301`). CONFIRMED for f60e301. UNCONFIRMED for d9f00d4 |
| Raw buffers | `--buffer-count`: exFAT **10**, ext4 8, default 8. The video/lores stream gets the same count (`storage_profiles.py:32-93`, `cinepi_multi.py:845-866`, `rpicam_app.cpp:629-631, 657`). CONFIRMED | 8 (T23). More buffers only delay the first gap; they do not change the per-frame deficit. PROBABLE |
| Scheduling | Whole process `chrt -f 70`, `ionice -c2 -n0`, `taskset -c 1-3` (`cinepi_multi.py:294-311`). The installer isolates the last core for audio (`cinemate-install.sh:1262-1275`). Encode workers nice -10 on CPUs 1-2, disk workers nice -5 (`storage_profiles.py:74-83`). CONFIRMED | No SCHED_FIFO, no affinity, nice only (KB `cinemate-lessons.md:77`, f60e301). UNCONFIRMED for d9f00d4 |
| Pipeline serialisation | `tryRunPipeline` runs only when `state_ == Idle` (`pisp.cpp:2312-2316@bfe0b76`). CONFIRMED | Same gate (`pisp.cpp:3112-3117@6b0b49f`). CONFIRMED |
| IPA rate limit | Hard-coded `controllerMinFrameDuration = 1.0s / 30.0` (`ipa_base.cpp:56, 451@bfe0b76`), so the algorithms run every frame at 30 fps | Configurable `controller_min_frame_duration_us` (`pipeline_base.cpp:1200-1201`, `ipa_base.cpp:476-480@6b0b49f`), default 33,333 µs |
| Tuning | `imx585.json` has `rpi.hdr` (Off cadence [0]) and TDN in `rpi.denoise` (`libcamera/src/ipa/rpi/pisp/data/imx585.json@bfe0b76`). cinepi-raw asks for `cdn_fast` (`rpicam_app.cpp:703`). CONFIRMED | Same algorithm list minus `rpi.hdr`, also with TDN (`libcamera-apertar/.../imx585.json`). CONFIRMED |

**Bytes per frame.** Frame = 3840 x 2200 x 2 = 16,896,000 B = 16.9 MB. COMP1 = 1 B/px = 8.45 MB. Assumption for all of it: every
pass misses the 2 MB L3 because 16.9 MB is far larger (PROBABLE). The back-end read is taken as one full Bayer read plus its YUV
write; Q1 owns the real figure.

| Pass | Cinemate 16:U | Apertar L1 | Cinemate 16:P (COMP1) |
| --- | --- | --- | --- |
| CFE write | 16.9 | 16.9 | 8.45 |
| rev16 swap (read + write) | 33.8 | 33.8 | 0 |
| SW raw stats (1/4 of the rows) | 0 | 4.2 | 0 |
| Back end read + YUV write | 16.9 + 1.36 = 18.3 | 16.9 + 1.38 = 18.3 | 8.45 + 1.36 = 9.8 |
| Preview correction read | 11.1 | 0 | 0 (stage disabled for COMP1: `ccmpPreviewStage.cpp:103-115`. PROBABLE) |
| Copy into the recorder (read + write) | 33.8 | 33.8 | 8.45 + 16.9 = 25.35 (decode on write) |
| Thumbnail (lores read) | 1.36 | 0 | 1.36 |
| Buffered `write()` (read + page-cache write) | 33.8 | 33.8 | 33.8 |
| NVMe DMA read | 16.9 | 16.9 | 16.9 |
| **Total per frame** | **165.8 MB** | **157.7 MB** | **95.7 MB** |
| x 30 fps | 4.97 GB/s | 4.73 GB/s | 2.87 GB/s |

The per-pass sums, as computed (PROBABLE):

- Cinemate 16:U: 16.9 + 33.8 + 18.3 + 11.1 + 33.8 + 1.36 + 33.8 + 16.9 = 165.8 MB.
- Apertar L1: 16.9 + 33.8 + 4.2 + 18.3 + 33.8 + 33.8 + 16.9 = 157.7 MB.
- Cinemate 16:P: 8.45 + 9.8 + 25.35 + 1.36 + 33.8 + 16.9 = 95.7 MB, which is 42 % below Cinemate 16:U (1 - 95.7 / 165.8).

Conclusion: by DRAM traffic, Cinemate is about 5 % heavier than Apertar L1, not lighter. PROBABLE.

## 4. (d) Cinemate's own frame-drop accounting, recorded results, and git history

**Counters** (CONFIRMED in code):

- `droppedFrames` counts sensor-timestamp holes in the encoder: `dropped_frames_ += raw_elapsed - 1` when the gap is at least two
  frame periods (`dng_encoder.cpp:2124-2135`). It is published on `cp_stats` (`cinepi_controller.cpp:642`) and read by
  `redis_listener.py:862-872`. `writeFailures` counts failed writes (`:874-880`).
- `analyze_frames` compares the DNGs on disk with the theoretical count after a take (`redis_listener.py:1659-1980`).
- `cinepi-raw` logs `Frame Drop!!!!! FPS measured: ... FPS settings: ...` for any frame interval more than 1 fps off the setting
  (`cinepi_recorder.hpp:94-97`). This only runs while recording (`cinepi_raw.cpp:437-454`).
- Together these are the counters that Apertar's `dropped_gap_estimate` and DNG-index method correspond to.

**Recorded results for this mode at 30 fps:** none in the handbook, docs, tests or commit messages (grep of `30 fps`, `30fps`,
`fps 30` and related strings; the only hits are the advertised-ceiling lines above and one unit test with `requested_fps=30` in
`_test/test_dynamic_resolution.py:255`). CONFIRMED for these trees. Patrik's observation is not written down anywhere I can see.
UNCONFIRMED.

**Git history** (`git log --all -i --grep` and `-S`, CONFIRMED):

| Repo | Commit | What it says |
| --- | --- | --- |
| libcamera (cinemate) | `614ce18c` 08-21 | `minPixelProcessingTime` 1/380 changed to 1/580 ("to work with rp1-overclock") |
| libcamera (cinemate) | `0413c135`, `3c7b9abd` 08-26 | Bound first derived from the RP1 clock, then taken from `LIBCAMERA_RPI_MAX_PIXEL_RATE` |
| libcamera (cinemate) | `bcdd7e17` 07-14 | No swap for PISP-compressed CFE buffers. "The working INNO-MAKER reference stack proves the COMP1 route: its 16-bit DNGs carry COMP1's magnitude-dependent 16/32/64 quantisation steps" |
| cinepi-raw | `da418ed` 07-14 | 16:P mapped to `BGGR_PISP_COMP1`. "Our attempt to force unpacked SBGGR16 produced FE garbage" (later fixed, §3) |
| cinepi-raw | `bd39389` 08-26 | `--max-pixel-rate` passed through to the IPA |
| cinepi-raw | `056b07f`, `ea53b2c`, `dca6748`, `03cffd0` 09-15 | 4K 16-bit drops at 25 fps traced to the preview stage, then fixed |
| cinemate | `5243b91`, `24a3968`, `dc65493`, `b769e94`, `2657eff` 08-26 to 09-15 | RP1 regime decided in Cinemate and passed down; mtime guard; image-build timestamp fix |
| cinemate | `31126f2`, `a61a589` 05-31, 06-01 (KB `cinemate-lessons.md:118`) | Raw buffers per filesystem: "frame drops are disk-write-latency-bound" |

No commit in any of the three repos mentions swap cost, memory or DRAM bandwidth, or a 16-bit 4K take at 30 fps (grep for
`bandwidth|rev16|endian|DRAM|30 fps|30fps`). CONFIRMED.

## 5. (e) Is there evidence that any Pi 5 setup records this mode at 30.00 fps with 0 drops?

**No.** CONFIRMED for every source read. In detail:

- Cinemate's 30.00 is a configure-time ceiling (§1).
- Cinemate's only counted 4K 16-bit takes are at 25 fps or below (§2).
- Its handbook says outright that sustained capture at the advertised ceiling was never observed (`:392-393`).
- will127534's driver README gives frame-rate tables only, plus "without overclocking RP1 ... limited to ~43.8 FPS @ 4K" and
  "For ClearHDR mode the framerate will be half" (`imx585-v4l2-driver/README.md:110-121@18c1eb2`;
  https://github.com/will127534/imx585-v4l2-driver, fetched: no recorded takes).
- The StarlightEye page (https://github.com/will127534/StarlightEye, fetched) states no frame rates.
- The INNO-MAKER stack is known only through Cinemate's commit messages (COMP1 forensics, no fps). UNCONFIRMED.
- A web search ("IMX585 Clear HDR 16-bit 4K 30 fps Raspberry Pi 5 recording frame drops") found only a Hackaday piece (2026-03-19,
  https://hackaday.com/2026/03/19/recording-hdr-video-with-a-raspberry-pi/) that I could not open (DNS). Its search summary gives
  no frame rate. UNCONFIRMED.

**What differs between Cinemate and Apertar, and whether it could matter at 30 fps:**

| Difference | Cinemate | Apertar | Could it explain a 30 vs 28 fps gap? |
| --- | --- | --- | --- |
| RP1 bound | 380 / 580 | 646.7 | No. Apertar's is higher, and idle preview is already 30.00 (§1). CONFIRMED |
| Link | default 720 MHz (25 fps max). 891 on the colour rig | 891 MHz | Same timing at 891 (HMAX 550). The out-of-spec D-PHY affects margin, not throughput: Apertar's CSI-2 counters read 0 (brief §3). PROBABLE |
| Preview size | 1256x720, one BE output | about 1280x720 | Negligible (1.36 vs 1.38 MB written). PROBABLE |
| SW raw stats | none | 1/4 of the rows (4.2 MB read, about 5.8-7.1 ms) | Cinemate saves this but pays 11.1 MB in `ccmpPreview` instead. Net neutral in DRAM. PROBABLE |
| Copy | yes (encode worker) | yes (T25 worker) | Same traffic. CONFIRMED (code) |
| Filesystem | exFAT or ext4 profiles | exFAT | ext4 lowers write latency spikes (`a61a589`). Apertar's losses are single regular gaps, not bursts, so storage latency is unlikely (KB `hardware-log.md:165-170`). PROBABLE |
| Scheduling | SCHED_FIFO 70, CPUs 1-3, whole process | nice only | Could cut wakeup latency for libcamera's thread. Small, because Apertar's thread is 34-43 % busy (brief §3). PROBABLE. Test X3 |
| COMP1 option | possible (16:P) | blocked in libcamera (WDR forces u16) | **Yes, if the limit is memory bandwidth in CFE + swap + BE**: -42 % bytes. PROBABLE. Test X2 |

## Experiments this suggests

Ordered by what they settle per unit of effort. Patrik runs anything that needs `sudo`, a restart or `/boot/firmware`. Builds
happen on the Pi.

**X1. Count Cinemate's own 30 fps delivery in this mode.** No build; it turns "similar limits" into a number.

- **Change:** on the Cinemate camera (or the Apertar Pi booted from a Cinemate card), set 3840x2200 16-bit Clear HDR, link 891 MHz,
  `rp1-overclock` on (rebooted after the change, see the mtime guard), dynamic resolution off, 30 fps, exFAT NVMe. Shoot 3 takes of
  10 s with the Pi otherwise idle.
- **Measure (read-only):**
  - `ps -o args= -C cinepi-raw` to record `--mode`, `--max-pixel-rate`, `--buffer-count` and `--lores-*`.
  - `journalctl -u cinemate-autostart --since -2min | grep -c 'Frame Drop'` per take.
  - `ls /media/RAW/<clip>/*.dng | wc -l` against 10 x 30 = 300.
  - `timeout 12 redis-cli subscribe cp_stats | grep -o '"droppedFrames" : [0-9]*' | tail -1`.
- **Prediction:** 27-29 fps delivered (8-30 missing per 10 s take), single-frame holes every 5-9 frames. Reason: per-frame DRAM
  traffic of about 166 MB, against about 158 MB for Apertar L1, which delivers 27.6-28.8 fps.
- **Ruled out by:** 0 holes and 300 DNGs in 3 of 3 takes. Something in Cinemate's stack would then be decisive: SCHED_FIFO,
  affinity, no SW stats, the older libcamera, or the uncommitted Pi edits (`open-threads.md:369`). Diff them one at a time
  against Apertar.

**X2. COMP1 as a bandwidth discriminator on Cinemate's stack.** No build.

- **Change:** as X1, but launch with `--mode 3840:2200:16:P`. Either set imx585 `"packing": "P"` in Cinemate's
  `resources/sensors.json` and restart Cinemate, or run `cinepi-raw` by hand with Cinemate stopped and the same arguments as X1
  except `:P`. This gives `BGGR_PISP_COMP1` with no swap (`rpicam_app.cpp:132`, `pisp.cpp:1455-1459@bfe0b76`).
- **Measure:** as X1, plus confirm the configure line shows a PISP-compressed CFE format (`journalctl` with cinepi-raw `--verbose`,
  or the stream log line `Raw stream: ... : <pixelFormat>` from `cinepi_raw.cpp:127`).
- **Prediction:** if the 30 fps loss is DRAM bandwidth in CFE + swap + BE, removing about 70 MB per frame
  (165.8 - 95.7) gives 30.00 fps with 0 holes in 3 of 3 takes.
- **Ruled out by:** 5 or more holes per 10 s take, with the per-frame loss no better than X1. Bytes through CFE and BE would then
  not be the limit, and the BE's fixed per-job cost or the serial pipeline is next (Q1/Q2).
- **Caveats:**
  - COMP1 is lossy. The finest dequantisation step is 16 codes (`dng_pack.hpp:289-297@63a08d5`), which costs the shadow precision
    Clear HDR exists for, so treat this as a diagnostic, not a fix.
  - It also disables `ccmpPreview` (about 11 MB less), which confounds the comparison slightly.
  - 16:P has no hardware-log record on Cinemate's colour rig. Check pixel data before trusting a result
    (`hardware-log.md:786-790`: exposure response, not frame statistics).
- **If X2 is clean:** the Apertar equivalent needs a libcamera change. The forced-u16 block at `pisp.cpp:1854-1873@6b0b49f` would
  have to allow PISP1 for 16-bit WDR when the app asks for it and raw stats are off. Core already decodes COMP1 to 16-bit
  (`CdngEncoder.cpp:1035-1042@f60e301`).

**X3. Cinemate's scheduling for Apertar-Core.** No build.

- **Change:** Patrik adds `CPUSchedulingPolicy=fifo`, `CPUSchedulingPriority=70`, `CPUAffinity=1-3` and
  `IOSchedulingClass=best-effort` / `IOSchedulingPriority=0` to a drop-in for `apertar-core.service`, matching
  `cinepi_multi.py:298-310`. Keep L1 (row step 4, worker off), then restart.
- **Measure:** `working/tools/takes.sh 3 10` at 30 fps, then `missing`, `dropped_gap_estimate` and fps per take. Verify with
  `chrt -p $(pgrep -f apertar-core)` and `taskset -cp <pid>`.
- **Prediction:** at most +0.5 fps (missing 7-20 becomes 5-15), because the thread is not saturated and the limit is memory.
- **Ruled out by:** 0 missing in 3 of 3 takes would mean wakeup latency was the limit. No change at all confirms scheduling is
  irrelevant.
- **Risk:** SCHED_FIFO 70 on a busy process can starve CPU 1-3 housekeeping. Cinemate runs it this way.

**X4. Run the IPA every other frame.** No build. Cinemate cannot do this; Apertar's libcamera can.

- **Change:** `LIBCAMERA_RPI_CONFIG_FILE` pointing to a YAML with `version: 1.0`, `target: pisp`, `pipeline_handler:
  {controller_min_frame_duration_us: 66666}` (`pipeline_base.cpp:1184-1201@6b0b49f`). ISO, shutter and WB stay manual. If Core
  already sets this variable, merge into its file (UNCONFIRMED whether it does).
- **Measure:** takes as X3, plus one `LIBCAMERA_LOG_LEVELS=RPI:0` window for back end start -> start interval.
- **Prediction:** the IPA runs its algorithms on alternate frames (`ipa_base.cpp:476-492`). Any IPA time on the serial path halves.
  Expect at most +0.3 fps unless the IPA is several ms per frame.
- **Ruled out by:** an unchanged BE start interval (36 ms) means IPA time is not on the critical path.

**X5 (optional, heavier).** Frame size as the independent variable, using Cinemate's windowed RAW16 modes.

- **Change:** load the `cinemate-modes` driver and record its 3840x1648 RAW16 crop at 30 fps (`imx585.c` RAW16 family; the probe
  fixture shows `3840x1648 [29.00 fps]` at 380, `_test/test_clearhdr_16bit_modes_survive_the_probe.py:67`). The Apertar driver has
  only full 3840x2200 16-bit (`imx585-apertar/imx585.c:1196-1217`).
- **Prediction:** 3840 x 1648 x 2 = 12.66 MB per frame (-25 %). If the cycle scales with bytes, 36.2 ms x 0.75 = 27.1 ms, under
  33.3 ms, so 0 missing.
- **Ruled out by:** still losing frames at -25 % bytes. A fixed per-frame cost dominates.

## Unknowns

- **What Patrik saw with Cinemate:** fps, link, overclock state, packing, filesystem, take length and counts. None is recorded.
  X1 settles it.
- **What the Cinemate camera actually runs:** its libcamera carries uncommitted edits (580 in `controller.cpp`, a rewritten
  `imx585.json`), so `bfe0b76` is not exactly what runs (`open-threads.md:358-375`). It needs `git -C /home/pi/libcamera diff --stat`
  on that camera.
- **Hardware match:** whether the Cinemate rigs (CM5 / CM5 Lite 4 GB) have the same DRAM bandwidth under this mix as the Apertar
  Pi 5 4 GB. Not established anywhere.
- **Core's write path on the Pi:** whether `d9f00d4` keeps `f60e301`'s chunked write plus `POSIX_FADV_DONTNEED`, and its
  scheduling. The code is not available here.
- **COMP1 quality:** the image cost of COMP1 for Clear HDR 16-bit, and whether 16:P works at all on the colour sensor in Clear HDR
  on Cinemate's stack. There is no hardware-log record, only INNO-MAKER forensics in commit messages.
- **Real back-end bytes and time:** whether TDN and the YUV path read more than one Bayer frame. Q1 owns this.
- **The 08-27/28 on/off cells:** whether they were a bound mix-up (§2). It does not affect Apertar.

## Verification

Verifier: adversarial pass (Claude Opus 5.5 subagent), 2026-10-26. Every cited line was re-opened in the working trees (all at the
cited commits, clean) or with `git show f60e301:<path>` for apertar-core; URLs re-fetched. Arithmetic re-done with `python3`.
Verdicts: CONFIRMED / CORRECTED (holds, but cite, label or detail wrong) / REFUTED / UNVERIFIABLE (needs the Pi or Patrik).
Repo prefixes: `cm` = cinemate@d6cc93e, `hb` = cinemate-handbook@c99ff77 (`hl` = hb `lessons/hardware-log.md`), `cr` = cinepi-raw@63a08d5,
`lc` = libcamera@bfe0b76 (Cinemate), `la` = libcamera-apertar@6b0b49f, `lq` = libcamera-qbc@7e9fef0, `drv` = imx585-v4l2-driver@18c1eb2,
`kb` = apertar-kb, `k` = kernel-rpi@5bd564a.

| # | Claim (report section) | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | SA1/§1: the 21.99 / 30.00 are a computed ceiling, "CONFIRMED" | CORRECTED (label: PROBABLE, strong) | The arithmetic shows the numbers equal the sensor/bound timing (= `FrameDurationLimits.min`), which a clean delivered take would also show, so it does not by itself prove "not a take". What carries it: no take record anywhere (rows 21, 62), and `drv` README.md:257-258 (2079 Mbps not re-tested after the blend fix) against `cm` docs/changelog.md:49 ("measured at ... 1039.5 MHz") |
| 2 | Mode 4 row: 21.99 / 30.00 / 16.9 MB | CONFIRMED | `cm` docs/sensors.md:32 (header), :38 |
| 3 | "Both fps columns are the changelog's measured figures ..." quote; changelog 3.4.0 table | CONFIRMED | `cm` docs/sensors.md:40-42; docs/changelog.md:39-49 |
| 4 | First appearance in 7cba6fe (09-04), then 33e4f1c, d606429 | CONFIRMED | `git -C cinemate log -S'21.99' -- docs/`; 7cba6fe adds it to docs/changelog.md |
| 5 | `--list-cameras` fps = 1e6 / FrameDurationLimits.min after configure | CORRECTED (lines) | `cr` core/options.cpp:410-425 (configure :418, fps :424-425), not 409-424 |
| 6 | Probe runs under the launch's `--max-pixel-rate` | CONFIRMED | `cm` src/module/sensor_detect.py:2716-2723 |
| 7 | "electrical property ..." and sensors.md:197 quotes | CONFIRMED | sensor_detect.py:2279-2281; sensors.md:197 |
| 8 | 4K RAW16 entry uses HMAX_table_4lane_4K_12bit, 660 at 720 MHz, 550 at 891 MHz | CONFIRMED | `drv` imx585.c:1720-1727, 288-294 |
| 9 | Clear HDR floor HMAX 550; VMAX = 2250 x 2 = 4500 | CONFIRMED | `drv` imx585.c:121, 3274, 3301, 3314 |
| 10 | pixel_rate = width x 74.25 MHz / HMAX | CONFIRMED | `drv` imx585.c:221 (74250000), 3382-3386 |
| 11 | 550 / 74.25 MHz = 7.407 µs; x 4500 = 33.33 ms = 30.00 fps; 518.4 MPix/s needed | CONFIRMED | Re-done: 74.25e6 / (4500 x 550) = 30.000; 3840 x 74.25e6 / 550 = 518.4e6 |
| 12 | README: "floored at HMAX 550 regardless of link rate" | CONFIRMED | `drv` README.md:236-241 |
| 13 | IPA stretches the line to width x minPixelProcessingTime, minimum = 1us / env rate | CONFIRMED | `lc` src/ipa/rpi/common/ipa_base.cpp:589-609; src/ipa/rpi/controller/controller.cpp:116-139, 297-298 |
| 14 | 380 gives 45.47 ms = 21.99 fps; 580 gives 6.62 µs < 7.407, so 30.00 | CONFIRMED | 380e6 / (3840 x 4500) = 21.991; 3840 / 580e6 = 6.62 µs |
| 15 | 380 / 580 "Measured on a CM5"; overlay asks 300 MHz, gets 333.33 | CONFIRMED | `cm` src/module/rp1_regime.py:70-72; `hl`:286-315 |
| 16 | 2079 not re-tested after the fix; 08-31 milestone ran at 891 MHz | CONFIRMED | `drv` README.md:257-258; `hl`:1108-1111, 1162 |
| 17 | Default link 720 MHz: HMAX 660 gives 25.00 fps with the overclock, 21.99 without | CONFIRMED | `cm` docs/sensors.md:92; 74.25e6 / (4500 x 660) = 25.00; 10.105 µs > 8.889 µs |
| 18 | Apertar bound = 646.7 MPix/s, "CONFIRMED"; idle 30.00 fps shows it is not binding | CORRECTED (label) | The formula is CONFIRMED (333.33 x 2 - 20 = 646.67, `lq` controller.cpp:59-64, 135-145). The value on the Pi is PROBABLE: `kb` working/clearhdr-design.md:88 itself says **Probable**, and working/compare-raw/c1-probe-compare.md:127 says no log line was captured. "Bound >= 518.4" is CONFIRMED by `kb` lessons/hardware-log.md:161 (30.00 fps idle) |
| 19 | 08-26 :286-335 row (no assigned-clock-rates, rate passed by hand) | CONFIRMED | `hl`:286-335 |
| 20 | 08-26: 43.80 at 380 vs 66.85 at 580; ratio 0.65520 vs 0.65517 | CONFIRMED | `hl`:347-363; 43.80 / 66.85 = 0.65520, 380 / 580 = 0.65517 |
| 21 | SA2 / §5: "the handbook says outright that only the advertised ceiling was ever observed, never sustained capture" (:392-393) | CORRECTED (scope) | The line is about 3856x2180 **12-bit SDR at 66.85 fps** on the mono dev CM5, 2026-08-26 (`hl`:340-349, 392-393). It says nothing about 16-bit Clear HDR at 30 fps. The conclusion (no counted 30 fps take) still holds, by absence (row 62) |
| 22 | 08-26: Clear HDR halves fps; ~33.4 at 580 (older driver) | CONFIRMED | `hl`:441-446 |
| 23 | 08-26: "every mode advertises 25.00 fps"; 16-bit DNGs are a constant fill of 6 values | CONFIRMED | `hl`:476-479, 492 |
| 24 | 08-26: byte-pipe hypothesis (1.33x at 16 bpp), "Not proven" | CONFIRMED | `hl`:704-709 |
| 25 | 08-27: D-PHY clamps above 1500 Mbps; 2079 degrades; 1782 held ~5 min | CONFIRMED | `hl`:742-766 |
| 26 | 08-27/28: 16-bit soak stalls after 15-22 s on NTFS; 12-bit 21 fps 2520/2520; "identical on/off" text | CONFIRMED (text) | `hl`:959-972. "21 fps" for the 16-bit soak is PROBABLE: 355 MB/s / 16.9 MB = 21.0 |
| 27 | The on/off cells contradict the arithmetic | CONFIRMED | Holds for the driver that entry used too: `drv` `origin/innomaker-v1.0`:imx585.c:281-287 has the same 660 / 550 table. Candidate cause dated: a stock board was handed 580 at 19:52:46 (`hl`:855-857); the fixes `cm` dc65493 landed 2026-08-27 20:55 and b769e94 at 21:33 |
| 28 | 08-31: colour CM5 Lite, exFAT, 891 MHz, overclock on, VMAX 4500 / HMAX 550, judged visually | CONFIRMED | `hl`:1106-1162 |
| 29 | 09-13: thumbnail adds 2,712,960 B (+16.1 %); 588 MB/s at 30 fps | CONFIRMED | `hl`:1848-1856; 2,712,960 / 16,896,000 = 16.06 %; 19,609,788 B x 30 = 588.3 MB/s |
| 30 | 09-14: 16-bit 4K stage 21.9 ms median, 27.7 max | CONFIRMED | `hl`:2244-2247. Note: measured on `feature/clearhdr12-preview-clean` before ea53b2c, so it is not the cost of the 63a08d5 stage |
| 31 | 09-14: frame period locked at 40 ms; detached thread per request | CONFIRMED | `hl`:2367-2372 |
| 32 | 09-15 `056b07f`: drops "Fixed with a sample budget" | REFUTED (the fix) | The quote (208 drop events, "6.24984 FPS settings 25") is CONFIRMED (`cr` 056b07f message). But `cr` 03cffd0 says "The sample-budget fix landed ... 0.38 ms/frame ... and 4K 16-bit still drops". What cleared the drops was ea53b2c ("16-bit no longer renders", which removes a second full-frame CPU render) plus dca6748 (`hl`:3184-3196) |
| 33 | 09-15: "the 25 fps takes are clean after the fixes" | CORRECTED (detail) | `hl`:3184: "operator-confirmed in the same sitting". No frame count is recorded, so this is not a counted record |
| 34 | RAM guard is a hard stop; NTFS not recommended | CONFIRMED | `hb` architecture/cinepi-raw.md:32-55; architecture/cinemate.md:166-172 |
| 35 | architecture/cinepi-raw.md:313-327 ("no correction" for 16-bit) is stale | CONFIRMED | `cr` cinepi/ccmpPreviewStage.cpp:385, 607 |
| 36 | The Pi's libcamera has uncommitted edits (580 in controller.cpp, ~1008-line imx585.json) | CONFIRMED (as reported) | `hb` open-threads.md:358-375 says the counts are "reported, not measured" |
| 37 | No handbook measurement of swap cost, thread time, DRAM bandwidth, or NVMe/SSD/SD at 30 fps | CONFIRMED | grep of `hb`; swap appears only as a correctness question (`hl`:511-516, 638-642, 698, 835-837) |
| 38 | Storage claims at 25 fps: changelog 3.3.1 / 3.4.1 | CONFIRMED | `cm` docs/changelog.md:21, 137-138 |
| 39 | Cinemate asks for 16:U; 16:U maps to SBGGR16, 16:P to BGGR_PISP_COMP1 | CONFIRMED | `cm` sensor_detect.py:55; resources/sensors.json (imx585 "U"); cinepi_multi.py:684; `cr` core/rpicam_app.cpp:130-132 |
| 40 | Apertar forces unpacked u16 for Clear HDR | CONFIRMED | `la` pisp.cpp:1771-1776, 1854-1873 |
| 41 | Cinemate's swap runs in cfeBufferDequeue on the pipeline thread and is skipped for PISP1 | CONFIRMED | `lc` pisp.cpp:1448-1459, 1723-1739 |
| 42 | Apertar's swap: on the thread (L1), on a worker (L2) | CONFIRMED | `la` pisp.cpp:818, 878, 2220 |
| 43 | Cinemate has no SW raw stats; "always passes `--shutter 20000` and `--awbgains`" | CORRECTED (detail) | No `RawStats` in `lc` src/; warning at `lc` pisp.cpp:1460-1462. `--awbgains` is passed only for a colour sensor (`cm` cinepi_multi.py:702-703) |
| 44 | Apertar runs processRawStats with row step 4 | CONFIRMED | `la` pisp.cpp:2265, 3069; brief §8 |
| 45 | One BE output: 1256x720 YUV420, aliased to lores, rendered every frame | CONFIRMED (stream setup) | `cr` rpicam_app.cpp:614-677; ShowPreview(lores) at cinepi/cinepi_raw.cpp:462. The MJPEG and thumbnail consumers were not re-opened |
| 46 | ccmpPreview is on for 16-bit: BufferReadSync of the raw, clamp measurement, correctHighlightsInPlace | CONFIRMED | `cr` ccmpPreviewStage.cpp:263-266, 385, 414, 554, 592, 607 |
| 47 | ccmpPreview reads ~11.1 MB of raw per frame | CONFIRMED (arithmetic); PROBABLE as DRAM bytes | srcRow snaps to an even row and reads sy and sy+1, so 720 x 2 = 1440 distinct rows. Column pitch 3840 / 1256 = 3.06 px = 6.1 B < 64 B line, so every line is touched: 1440 x 7680 = 11.06 MB (`cr` ccmp_preview.hpp:445-480, 607-631) |
| 48 | COMP1 disables ccmpPreview (report label: PROBABLE) | CONFIRMED by code | `cr` ccmpPreviewStage.cpp:103-115 (format list), 302-309 (refuses any other format) |
| 49 | Encode worker memcpy's 16.9 MB row by row into a pool buffer; the request is released only after that | CONFIRMED | `cr` dng_encoder.cpp:1424-1433, 2172-2243, 2303-2304; ifd_builder.hpp:173-181; cinepi_recorder.hpp:158-174 |
| 50 | One buffered `write()`, POSIX_FADV_SEQUENTIAL, no DONTNEED | CONFIRMED | `cr` dng_encoder.cpp:2351-2362 |
| 51 | Core f60e301: 491,520 B scratch, then `write()`, then DONTNEED | CONFIRMED | `git show f60e301:src/cdng/CdngEncoder.cpp`:1861-1911, 1779; max(7680, min(4 MiB, max(256 KiB, 64 x 7680))) = 491,520 |
| 52 | Buffer counts: exFAT 10, ext4 8, default 8; video stream gets the same count | CONFIRMED | `cm` storage_profiles.py:50-93; cinepi_multi.py:845-866; `cr` rpicam_app.cpp:629-631, 657 |
| 53 | Scheduling: FIFO 70, ionice, taskset 1-3; CPU 3 isolated; workers nice -10 / -5 | CORRECTED (detail) | The configuration is CONFIRMED (`cm` cinepi_multi.py:294-311; cinemate-install.sh:1262-1275). But the disk-worker nice fails with EPERM on the rig (`hb` open-threads.md:340-356), and nice is moot under SCHED_FIFO |
| 54 | The same `state_ == Idle` gate in both stacks | CONFIRMED | `lc` pisp.cpp:2311-2315; `la` pisp.cpp:3112-3117 |
| 55 | IPA rate limit: hard-coded 1/30 s (Cinemate) vs configurable, default 33,333 µs (Apertar) | CONFIRMED | `lc` ipa_base.cpp:56, 451; `la` pipeline_base.cpp:40, 1200-1201; ipa_base.cpp:476-480 |
| 56 | Tuning: TDN in both, `rpi.hdr` only in Cinemate's; cinepi-raw asks for `cdn_fast` | CORRECTED (detail) | The JSONs are CONFIRMED (python parse of both imx585.json). `cdn_fast` applies only when `--denoise` is "auto" (`cr` rpicam_app.cpp:703) |
| 57 | Per-pass sums 165.8 / 157.7 / 95.7 MB; -42 %; x30; Cinemate +5 % | CONFIRMED (arithmetic) | 165.84 / 157.67 / 95.64; 1 - 95.64 / 165.84 = 42.3 %; 165.84 / 157.67 = 1.052; x30 = 4.98 / 4.73 / 2.87 GB/s |
| 58 | Back end = one Bayer read plus its YUV write | CORRECTED (substance) | TDN runs in both stacks, and its buffers use the CFE format (16-bit unpacked, uncompressed), so each frame adds a TDN read and a TDN write of 16.9 MB each (PROBABLE). Code: `lc` pisp.cpp:1478-1480, 2072-2088, 2268-2272; `la` pisp.cpp:1901-1903, 2565-2581, 2759-2763; IPA `lc` src/ipa/rpi/pisp/pisp.cpp:394-396, 715-722; `lc` denoise.cpp:44 (`tdnEnable = contains("tdn")`); `k` pisp_be.c:409-436. Re-done totals: Cinemate 16:U 199.6, Apertar L1 191.5, Cinemate 16:P 112.5 MB (x30 = 5.99 / 5.74 / 3.38 GB/s). COMP1 then cuts 43.6 %, and Cinemate is +4.3 % over Apertar |
| 59 | Thumbnail reads 1.36 MB of lores per frame | CORRECTED (minor) | `thumbnail_size` 2 gives a 314x180 JPEG (`hl`:2004, 2031). The sampled read is about 1/4 of the lores rows, ~0.34 MB (PROBABLE). Totals fall by ~1 MB |
| 60 | droppedFrames (sensor-timestamp holes), writeFailures, analyze_frames | CONFIRMED | `cr` dng_encoder.cpp:2127-2135; cinepi_controller.cpp:642 (`toStyledString`, :691, so the X1 grep pattern matches); `cm` redis_listener.py:862-880, 1659 |
| 61 | "Frame Drop!!!!!" is logged for an interval > 1 fps off, only while recording | CONFIRMED | `cr` cinepi_recorder.hpp:92-97; cinepi_raw.cpp:437-454 |
| 62 | No recorded 30 fps result; "the only hits" are the ceiling lines and one unit test | CORRECTED (detail) | Substance CONFIRMED. More 30.00 fps listing fixtures exist (`cm` _test/test_sensor_mode_geometry.py:43-46, 77, 79; _test/test_clearhdr_16bit_modes_survive_the_probe.py:65). All are advertised listings, not takes |
| 63 | Git-history table (17 commits: messages and dates) | CONFIRMED | Opened `lc` 614ce18c, 0413c135, 3c7b9abd, bcdd7e17; `cr` da418ed, bd39389, 056b07f, ea53b2c, dca6748, 03cffd0; `cm` 5243b91, 24a3968, dc65493, b769e94, 2657eff, 31126f2, a61a589 |
| 64 | No commit mentions swap cost, DRAM bandwidth, or a 16-bit 4K take at 30 fps | CONFIRMED | `git log --all -i -E --grep` in cm, cr, lc, hb. The hits are storage bandwidth (`cm` ba9f792, 4a83428; `cr` 12657d1, c9b2c5f), endian correctness (bcdd7e17, `cm` 906ad5e) and an imx477 mode (`cm` cb187c9) |
| 65 | will127534 README and StarlightEye: no recorded takes | CONFIRMED | https://github.com/will127534/imx585-v4l2-driver ("limited to ~43.8 FPS @ 4K", "ClearHDR ... half", no counted take); https://github.com/will127534/StarlightEye (no fps), both fetched 2026-10-26 |
| 66 | Hackaday 2026-03-19 cannot be opened; its summary gives no fps | CONFIRMED | WebFetch fails again (ENOTFOUND hackaday.com). The WebSearch summary of https://hackaday.com/2026/03/19/recording-hdr-video-with-a-raspberry-pi/ states no frame rate; https://lwn.net/Articles/1033252/ also failed DNS |
| 67 | An out-of-spec D-PHY affects margin, not throughput (CSI-2 counters 0) | CONFIRMED (stays PROBABLE) | brief §3; `hl`:742-766 |
| 68 | "Single regular gaps, so storage latency is unlikely" | CORRECTED (caveat) | `cm` 31126f2 attributes **single**-frame holes to brief disk or encode stalls. What argues for a steady rate deficit is the 5-9 frame regularity and the late first gap (`kb` hardware-log.md:165-170), not the gaps being single |
| 69 | X2: removing ~70 MB per frame gives 30.00 fps if bandwidth is the limit, so X2 is "a bandwidth discriminator" | CORRECTED (substance) | With TDN the removed bytes are 87.1 MB, not 70.2. COMP1 also removes the swap from Cinemate's serial pipeline thread (`lc` pisp.cpp:1723-1739; 9.9 ms per frame under load, `kb` hardware-log.md:188), and L1 showed that thread time mattered. A clean X2 therefore cannot separate bandwidth from thread time |
| 70 | X1 is ruled out by "0 holes and 300 DNGs" | CORRECTED (detail) | 10 s takes hold ~287 frames (brief §3). Use droppedFrames = 0, zero `Frame Drop` lines and contiguous DNG indices instead |
| 71 | X3 predicts at most +0.5 fps | CORRECTED (missed risk) | Under SCHED_FIFO at one priority there is no time slicing. A recorder memcpy worker at FIFO 70 can hold a core for a whole 16.9 MB copy and delay the CameraManager thread, so delivery can go **down** (PROBABLE). Measure the per-thread policy with `ps -L -o tid,cls,rtprio,psr,comm -p <pid>` |
| 72 | X4 YAML needs `version: 1.0`, `target: pisp`, `pipeline_handler.controller_min_frame_duration_us` | CONFIRMED | `la` pipeline_base.cpp:1177-1182, 1200-1201; pisp.cpp:1644-1649 (target checked) |
| 73 | X5: 3840x1648 = 12.66 MB (-25 %), 36.2 x 0.75 = 27.1 ms; fixture shows 29.00 fps; Apertar has only the full RAW16 mode | CONFIRMED | 3840 x 1648 x 2 = 12,656,640 B; 1 - 12.657 / 16.896 = 25.1 %; `cm` _test/test_clearhdr_16bit_modes_survive_the_probe.py:67; `drv` imx585.c:1836-1837; imx585-apertar imx585.c:1196-1217@98b9862 |
| 74 | COMP1 is lossy; the finest step is 16 codes | CONFIRMED | `cr` cinepi/dng_pack.hpp:289-290 (mode 0: 16 x q) |
| 75 | 16:P has no hardware-log record on the colour rig; Core already decodes COMP1 to 16-bit | CONFIRMED | grep `hl`: COMP1 appears only as a hypothesis (:652-657); apertar-core f60e301 CdngEncoder.cpp:1035-1042 |
| 76 | The operator's camera is a Pi 5 | CONFIRMED | `hl`:1612 |
| 77 | What Patrik saw with Cinemate (fps, link, packing, filesystem) | UNVERIFIABLE | Not written down in any tree. Needs Patrik or X1 |
| 78 | Effect of the camera's uncommitted libcamera edits | UNVERIFIABLE | On that camera: `git -C /home/pi/libcamera diff --stat` |
| 79 | Core d9f00d4's write path and scheduling | UNVERIFIABLE | Code not here. On the Pi: `git -C <core> show d9f00d4:src/cdng/CdngEncoder.cpp \| grep -n DONTNEED`; `ps -L -o tid,cls,ni,psr,comm -p $(pgrep -o apertar-core)` |

**Counts:** 79 claims: 60 CONFIRMED, 15 CORRECTED, 1 REFUTED, 3 UNVERIFIABLE.

### Corrections that change substance

1. **The byte budget leaves out temporal denoise (row 58).**
   - Both stacks enable TDN from the tuning file, and the pipeline sets the TDN buffers to the CFE format, which is 16-bit
     uncompressed here. So the back end probably reads and writes one more full frame each per frame (+33.8 MB). PROBABLE.
   - Re-done totals: Cinemate 16:U 199.6 MB, Apertar L1 191.5 MB, Cinemate 16:P 112.5 MB per frame. At 30 fps that is 5.99 / 5.74 /
     3.38 GB/s. COMP1 then cuts 43.6 %.
   - The ranking (Cinemate slightly heavier than Apertar, +4.3 %) does not change. The absolute numbers that Q3 would compare
     against Pi 5 DRAM bandwidth are 21 % low.
   - Read-only check on the Pi: start Core with `LIBCAMERA_LOG_LEVELS=IPARPI:0` and count `TDN: exposure` lines
     (`lc` src/ipa/rpi/pisp/pisp.cpp:702 debug line). Any lines mean TDN is on.
2. **X2 is not a clean bandwidth discriminator (row 69), and it is not the cheapest no-build bandwidth test.**
   - COMP1 removes ~87 MB per frame and, in the same step, ~10 ms per frame of serial swap on Cinemate's pipeline thread. A clean
     result cannot tell the two apart.
   - A cheaper and lossless lever exists on Apertar's own stack: `disable_tdn: true` (see Missed 1).
3. **SA2 and §5 over-read `hl`:392-393 (row 21).** That line is about 12-bit SDR at 66.85 fps. "No counted 30 fps 16-bit take
   exists" rests on absence of evidence, not on that quote.
4. **The 09-15 4K 16-bit drops were not fixed by the sample budget (row 32).**
   - cinepi-raw 03cffd0 records that the drops persisted after it. ea53b2c fixed them by removing a second full-frame CPU render.
   - This is Cinemate's own evidence that one extra CPU pass over the 4K raw costs frames even at 25 fps. That supports the brief's
     memory-traffic and serial-work reading more than the report says.
5. **The headline label is too strong (row 1).** "Computed ceiling, not a recorded take" is PROBABLE (strong), not CONFIRMED. The
   arithmetic only shows the figures equal the sensor and bound timing, which a clean take would also deliver.

### Missed

1. **`disable_tdn` experiment (no build, lossless).**
   - Change: add `disable_tdn: true` to the same `LIBCAMERA_RPI_CONFIG_FILE` YAML as X4 (`la` pisp.cpp:1656; with no TDN buffers
     queued, the kernel clears the TDN enables, `k` pisp_be.c:409-436).
   - Expected saving: about 33.8 MB per frame, 17.6 % of Apertar L1's 191.5 MB, plus the back end's TDN work.
   - Measure: the journal line "TDN disabled by user config", then `takes.sh 3 10` at 30 fps.
   - Prediction: if the back end is memory-bound, BE start->done falls and fewer frames go missing. It is ruled out by unchanged
     missing counts and an unchanged 36 ms BE period.
   - Ranking: above X2 for Apertar, since it needs no stack swap and no lossy format.
2. **The X2 confound (Correction 2).** Pair X2 with a Cinemate 16:U run (X1). Separating thread time from bytes needs Apertar's L2
   worker or `disable_tdn` as well; X2 alone cannot do it.
3. **16:P validity on rpi-6.12.y.**
   - The Bayer 16-bit CFE entries use `csi_dt = 0` (`k` cfe_fmts.h:200-226).
   - The CSI2 channel then runs in COMPRESSED mode with DT 0 (`k` cfe.c:884-900, where `WARN_ON(!fmt->csi_dt)` fires). It is not
     established that the hardware compresses correctly decoded 16-bit samples there. UNCONFIRMED.
   - X2 timing stays usable even with garbage pixels. Image conclusions need the exposure-response check (`hl`:786-790).
4. **SCHED_FIFO starvation risk in X3 (row 71).** Same-priority FIFO workers are not time-sliced, so X3 could lower delivery.
5. **Cinemate's disk-worker nice levels are inert on the rig (row 53).** They fail with EPERM and are overridden by `chrt -f 70`,
   so the "Scheduling" difference between the stacks is FIFO plus affinity only.
