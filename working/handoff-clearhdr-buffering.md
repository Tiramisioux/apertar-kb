# Handoff: Clear HDR frame drops, explore Core's buffering

Prompt for the next Claude session on the Pi (apertar-dev skill). Written 2026-10-25. Paste it as the first message, or say "read `~/apertar-kb/working/handoff-clearhdr-buffering.md` and start".

**Status 2026-10-25 22:55:** steps 1-3 done without instrumentation; cause found in libcamera's CPU passes over CPU-uncached raw buffers. See `clearhdr-design.md`, "Frame drops: cause found". The CMA line under "Ruled out" is corrected there.

---

You are continuing the IMX585 Clear HDR work in Apertar-Core on the Pi (`~/ApertarCore`, branch `main`). Read `~/apertar-kb/llm/README.md`, then `~/apertar-kb/working/clearhdr-design.md` (the whole story, newest sections at the bottom), then this note.

**Way of working in this effort:** Patrik has asked Claude to make the Clear HDR changes directly (not tutorial-first). Confirm that with him at the start. Restarts and anything with `sudo` are his; give him the exact command. Journal access works (`pi` is in `systemd-journal`). Build Core with `cmake --build ~/ApertarCore-build -j2`.

## Goal of this phase

Clear HDR records only a fraction of its frames. Find where they are lost, fix it, and prove it with frame counts. **Measure first; change code only once a measurement points at the cause.**

| Take (4K, 25 fps requested, ~3 s) | Expected | Written |
| --- | --- | --- |
| SDR 12-bit cDNG (PiSP COMP1, 8.3 MB/frame) | ~75 | 75 |
| ProRes HQ 1080p / H.264 1080p30 (4 s) | 96 / 120 | 96 / 120 |
| Clear HDR 16-bit cDNG (unpacked, 3840x2200, 16.9 MB) | ~75 | 7 |
| Clear HDR 12-bit cDNG (unpacked, 3840x2160, 16.6 MB) | ~75 | 0-4 |

Journal after Clear HDR takes: `dropped_queue_full=0`, `write_failures=0`, `peak_queue=1/12` (the encoder is idle), but `ApertarCore drop[capture-gap]: +13 frame(s) estimate dt_us=559996` and `dropped_gap_estimate` 16-18. Written frame numbers repeat across takes: 0, 14, 15, 19. MLV in Clear HDR at 4K is **untested** (earlier MLV tests were SDR 1080p by mistake).

## What is known

- **Ruled out:** CMA (`/dev/dma_heap/vidbuf_cached -> system`, raw buffers are not in CMA); the encoder and disk (queue idle, SDR at 25 fps fine); the sensor exposure/tuning (fixed: `imx585_clearHDR.json`); data format (12- and 16-bit DNGs verified).
- **Pixel-rate bound:** this image's libcamera (`v0.7.1+qbcfork.20260522`) logs `RP1_PLL_SYS ... 333333333 Hz; PiSP pixel-rate cap = 646.667 Mpix/s` (overlay `rp1-clk-333mhz`, link 891 MHz). Cinemate's ceiling of 21.99 fps applies only at the stock 380 Mpix/s bound. **Unconfirmed** here: check the advertised Clear HDR fps with `rpicam-hello --list-cameras` (Core stopped).
- **Bench, Core stopped** (`rpicam-raw --mode ...:U --segment 1`, writes every frame to disk synchronously): 16-bit 33 frames / 1.5 s (~22 fps), 12-bit 9 / 1.5 s (~6 fps). Not a clean ceiling (disk-bound), but far above what Core gets.
- **12-bit mode:** libcamera expands every frame in software (`libcamera::CcmpUnwrap::process`, one pass over 8.3 Mpx on its pipeline thread). Core then maps it back to codes (`compressClearHdrFrame`, another 8.3 Mpx pass, on the completion thread, cDNG only).
- **Cinemate's model** (answer in `clearhdr-design.md`, from cinepi-raw `63a08d5`): 8-10 raw buffers from the system heap, preview count = raw count; no copy on the completion thread; one copy fused with the format work in 4 encode workers, then the camera buffer is requeued; disk writes from a RAM pool. A heavy Clear HDR stage on Cinemate's completion path cost 19-35 ms of a 40 ms frame.

## Core's path (line numbers at `9fa7918`; grep the anchor if they drift)

| What | Where | Anchor |
| --- | --- | --- |
| Raw/preview buffer count, 4 for cDNG/MLV | `CameraController.cpp:1047`, used at `:6281-6314` | `kConfiguredBufferCount = 4` |
| Buffer allocation, log line `RAW buffers: ... count=` | `:6606-6620` | `RAW buffers: ` |
| Completion handler | `:6782` | `void requestComplete(libcamera::Request *request)` |
| **Recording cadence gate** (frames are skipped until `FrameDuration` is within 2 % of 1/fps) | `:6855-6866` | `waitingForRecordingCadence_` |
| Raw copy on the completion thread (whole frame) | `recordRawFrame` `:7056`, copy `:7103-7108` | `copyRawBytes(buffer, rawCopy.data()` |
| Clear HDR 12-bit conversion (completion thread) | right after the copy | `compressClearHdrFrame(rawCopy` |
| Back-pressure and gap statistics | `hasCapacityForFrame` `:3609`, `nextFrameIndex` `:3599`, `capture stats:` `:5869` | `drop[capture-gap]` |
| Requeue | `:6700` | `void requeueRequest(libcamera::Request *request)` |
| Env overrides already present | `APERTAR_CDNG_WORKERS`, `APERTAR_RAW_CACHED_DMABUF`, `APERTAR_H264_CAMERA_BUFFERS`, `APERTAR_PRORES_CAMERA_BUFFERS` | `unsignedEnvValue("APERTAR_` |

## Suggested order

1. **Is the camera delivering 25 fps to Core in Clear HDR when not recording?** Add a temporary counter (completion callbacks per second, max gap between `SensorTimestamp`s, and the reported `FrameDuration`) logged once a second; compare SDR and both Clear HDR modes. If delivery is already low, the loss is upstream of Core (libcamera, `CcmpUnwrap`, the pixel-rate bound).
2. **Check the cadence gate.** Log the first few `FrameDuration` values after `record_start` in Clear HDR. If they sit outside 40 ms ± 2 %, frames are skipped by design. That alone could explain the start gap and the repeating frame numbers.
3. **Time the completion path:** request-complete to requeue per buffer, split into copy, 12-bit conversion and the rest. With 4 buffers at 40 ms there are 160 ms of slack.
4. Only then change code: raise the raw buffer count (8 for Clear HDR), move the copy and the 12-bit conversion off the completion thread into the recorder workers (as Cinemate does), fix the cadence gate if it is the cause. One change at a time, re-measured.
5. Test MLV in Clear HDR (both modes) once frames flow.

Remove temporary instrumentation before committing. Test takes write to `/media/RAW`; old test clips (cDNG C0010-C0035, MLV C0001-C0002, ProRes/H264 C0001, `bench16`, `bench16b`, `bench12`) can be deleted when Patrik agrees.

## Done means

Clear HDR 16-bit and 12-bit at 4K record ≥ 98 % of the frames expected at 25 fps (cDNG lossless, a 10 s take, frame numbers contiguous, `dropped_gap_estimate=0`), SDR unchanged, and the cause written up in `clearhdr-design.md` with confidence labels.

## Housekeeping

- All Clear HDR commits are on GitHub (Core 631721d, e1c10cd, 57c8fb0, 9fa7918; UI 4415a55).
- `~/Tuning-Files/defaults-pisp/imx585_clearHDR.json` is outside git and must go into every image (without it 16-bit Clear HDR records black).
- Open, not this phase: preview ScalerCrop at 16-bit is 3840x2120 instead of 3840x2160; ISO cap (1585) and auto-mode refusal in Clear HDR (workbook Step 6); presets do not carry `clear_hdr`.
