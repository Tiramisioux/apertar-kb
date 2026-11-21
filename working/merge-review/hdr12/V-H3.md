# V-H3. Skeptic check: "4K 12-bit Clear HDR drops frames at every fps because of two extra CPU passes"

Refs: Core `01f170c` (cinemate-port), libcamera `apertar` `6b0b49f`, KB journals of 2026-11-11 (Core `7e6e2a3`).
Host bench: `/home/user/build/hdr12-numeric/v-h3/bench.cpp`.

## Verdict

**Not a cause of "strange output". The mechanism as written is refuted in its two halves; the drop asymmetry is real.**

| Part of H3 | Result | Label |
| --- | --- | --- |
| 12-bit drops more than 16-bit at 26-29 fps | Holds (16-bit 27 carried, 12-bit none) | confirmed (KB journals) |
| "drops at every fps" | At 30 fps 16-bit drops too (cDNG 119, MLV 57 in 60 s). At 25 fps 12-bit lost 1 frame in 13 s and 2 in 93 s. The default fps (24, `Types.hpp:134@01f170c`) was never measured | weakened |
| libcamera unwrap is a pass "16-bit lacks" | Wrong: the unwrap **replaces** the 16-bit endian swap on the same thread; both modes run the SW stats pass | refuted (code) |
| Core re-compression on the copy worker limits | Not shown: 0 copy-slot drops in all 17 HDR12 journals; every loss is `drop[capture-gap]`; MLV 12-bit has no Core pass and still drops at 30 at a rate like MLV 16-bit | refuted as necessary (code + journals) |
| "MLV buffer full in 9 s" supports a CPU cause | Wrong kind: a buffer-full stop (disk/writer), not drops; MLV 12-bit stores 16-bit linear, same bytes as 16-bit; 16-bit MLV at 30 also filled the buffer | refuted as support |
| Drops show as black flashes in the WebUI viewer | Holds | confirmed (code) |

## 1. libcamera: the unwrap replaces a pass, it does not add one

| Mode | Pipeline (CameraManager) thread per raw frame | Evidence @6b0b49f |
| --- | --- | --- |
| 16-bit Clear HDR | NEON `rev16` endian swap over the frame, then `RawStatsProducer::process` | flag set only when the sensor mbus is 16 bpp: `pisp.cpp:1744-1750`; swap inline in `cfeBufferDequeue` `:2206-2224`; stats producer for 14/16-bit `:1813-1820` |
| 12-bit Clear HDR | no swap (12 bpp); `CcmpUnwrap::process` over the frame, then the same stats | `:1821-1844` (imx585, 12 bpp, `initCcmpUnwrap()`); `processRawStats` unwrap + stats `:3099-3106`; called synchronously `:2262-2266` |

- Both modes run one full-frame rewrite plus the stats walk on the same thread, synchronously unless `QBC_RAW_CPU_WORKER=1` (`:878-890`, `:2250-2256`). Confirmed.
- The cost difference is unwrap minus swap. The swap is hand NEON (`:397-416`); the unwrap is NEON load/store with a scalar 4096-entry lookup (`ccmp_unwrap.cpp:143-165`). Host bench (x86, not a Pi number): rev16 0.77 ms, unwrap 3.50 ms, memcpy 1.28 ms, Core's 65536-entry compress 4.75 ms per 3840x2160 frame. So the unwrap is dearer than the swap by a few ms on the Pi: probable. The KB's own arithmetic puts it "~7 ms, the same order as the swap it replaces" (`working/compare-raw/b3-core-completion.md:218`, probable, never measured).
- On fork main, Core's LUT ran on this same completion thread (`b3-core-completion.md:45`: 16-bit ~22 ms, 12-bit ~30 ms + unwrap at 30 fps). The port moved it to the copy worker (fc7eb16/351a3ee, G3-F5). The H3 picture of "two passes on the hot thread" describes main better than the port.

## 2. Core: the re-compression runs after the camera buffer is given back

- Copy worker order @01f170c: `memcpy` `CameraController.cpp:5107`, `releaseHeldRequest(copy.request)` `:5111`, then `compressClearHdrFrame` `:5134-5135`. The compress works on the copy only. Confirmed.
- It can still delay the next queued copy (one worker by default, `APERTAR_RAW_COPY_WORKERS` 1..2, `:4386`), so requests wait longer in `copyQueue_`. If that starved the camera, Core would first log `drop[copy-slot]` once `heldRequests_ >= maxHeldRequests_` (`:5072-5079`; max = buffers - 2, `:8736`; Clear HDR 8 buffers, `:1338`). Confirmed in code.
- Journals (`working/drop-frames/nvme-campaign/run-20261110/journal/4kHDR12_*`): every HDR12 take reports `dropped_copy_slot=0`, writer `peak_queue=2/12` (2/24 lossless), and only `drop[capture-gap]` (`:10042-10057`, sensor-timestamp gaps before Core sees the frame). Confirmed (measured).
- MLV skips the Core pass: `clearHdrStoresCodes12` needs `RecordingFormat::Cdng` (`:1639-1643`), `mapCodes12` gates the compress (`:9491-9492`). MLV 4K 12-bit at 30: 8 gaps in 217 frames; MLV 4K 16-bit at 30: 57 in 795. Same order. So drops at 30 happen without the Core pass, in both depths. Confirmed (n=1 each).

| 4K take, 60 s probe or walk | Frames enqueued | Gap estimate | copy-slot |
| --- | --- | --- | --- |
| HDR12 cDNG unc 30 | 1502 / 1592 | 291 / 200 | 0 |
| HDR12 cDNG lossless 30 | 1630 | 164 | 0 |
| HDR12 MLV 30 (buffer full 7.3 s) | 209 | 8 | 0 |
| HDR16 cDNG unc 30 | 1673 | 119 | 0 |
| HDR16 MLV 30 (buffer full 27 s) | 738 | 57 | 0 |
| HDR16 cDNG unc + Log 30 (Core LUT pass in 16-bit) | 1510 | 284 | 0 |
| HDR12 cDNG unc 25, 13 s / 93 s | 320 / 2320 | 1 / 2 | 0 |
| HDR16 cDNG unc 25, 758 s | 18882 | 0 | 0 |

- The 16-bit Log row is the cleanest A/B for "one extra full-frame LUT on the copy worker": it more than doubles the gaps at 30 (119 -> 284) yet 16-bit + Log carried 25 fps for 3 + 5 min. 12-bit cDNG carries the same kind of pass and also nearly holds 25. So the copy-worker pass costs about 1-3 fps at the edge (probable), but it does not make 25 fps unrecordable and it is not 12-bit only.
- The measured build `7e6e2a3` is 8 commits past `01f170c`; `8ec2f1a` moves part-folder creation off the copy worker. So `01f170c` does at least as much copy-worker work as the measured build. Probable: equal or more drops on `01f170c`.

## 3. Symptom chain

- Index holes: confirmed. `nextFrameIndex` numbers by sensor time (`CameraController.cpp:4679-4687`), so a gap skips a number; the journal logs `frame index jump` (`7e6e2a3` only).
- WebUI Clip Viewer: confirmed. `pbvShowHole` calls `pbvDraw(null)`, which fills `#000` and returns (`WebControlPage.cpp:12393-12400`, `pbvDraw` fill before the `!bitmap` return); the "Frame N dropped" label shows only when paused. During playback a hole is a one-frame black flash.
- Why this is a poor match for "strange output": at 24/25 fps the measured rate is one lost frame per 13-90 s, i.e. a rare one-frame black flash; at 30 fps, where losses are heavy, 16-bit loses frames too, yet 16-bit is reported fine. Probable.

## 4. What is left for the Pi

| Question | Command |
| --- | --- |
| Did the owner's take drop at all, at which fps | `journalctl -b -u apertar-core --no-pager \| grep -E 'recording clip:\|recording stats:\|drop\[\|frame index jump'` after the take; `ls <clip> \| wc -l` against the last index |
| Which thread limits | During a 12-bit and a 16-bit take at 27 fps: `top -H -b -n 5 -p $(pgrep -nx apertar-core)`, compare the libcamera pipeline thread and the copy worker |
| Unwrap off the hot thread helps? | Same 27 fps 12-bit take with `QBC_RAW_CPU_WORKER=1` in the Core drop-in; fewer `capture-gap` lines points at the unwrap |
| Core pass matters? | 12-bit cDNG vs 12-bit MLV at 27 fps, same card state; MLV needs a larger buffer budget to last 60 s |

## 5. Fix

None proposed. No defect is provable from code: the drops are a CPU/throughput edge measured on the rig, not a wrong line. If the Pi test shows the copy worker as the limit, the local change in Core's style is to let Clear HDR 12-bit cDNG start two copy workers by default (`unsignedEnvValue("APERTAR_RAW_COPY_WORKERS", clearHdrStoresCodes12(settings_) ? 2 : 1, 1, 2)` at `CameraController.cpp:4386`), checked by the same journal grep; no host test can show a throughput change. If the pipeline thread limits, the fix is in libcamera (worker on by default for the CCMP path), not in Core.
