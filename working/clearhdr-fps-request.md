# Request for the Mac-side Claude: how Cinemate gets 25 fps in Clear HDR

Written on the Pi 2026-10-25. Comparison material only: logic and numbers, no code copied. Context: `working/clearhdr-design.md`.

## What we see

Apertar-Core, IMX585, 4K, 25 fps requested. Frames written to cDNG in a ~3 s take:

| Mode | Expected | Written |
| --- | --- | --- |
| SDR 12-bit (PiSP COMP1, 8.3 MB/frame) | ~75 | 75 |
| Clear HDR 16-bit (unpacked SRGGB16, 3840x2200, 16.9 MB/frame) | ~75 | 7 |
| Clear HDR 12-bit (unpacked, 3840x2160, 16.6 MB/frame) | ~75 | 2-3 |

Core's journal: `dropped_queue_full=0`, `write_failures=0`, `dropped_gap_estimate` 16+ with gaps of ~560 ms between delivered frames. The frames do not reach Core; the encoder is not the bottleneck. Bench with Core stopped, `rpicam-raw --mode ...:U --segment 1`: 16-bit 33 frames / 1.5 s (~22 fps), 12-bit 9 frames / 1.5 s (~6 fps).

## Our setup (Pi 5)

- `dtoverlay=imx585,cam0,link-frequency=891000000`, `dtoverlay=rp1-clk-333mhz`, `dtparam=pciex1_gen=3`.
- **CMA: 64 MB total, 32 kB free** (in SDR). Core allocates 4 raw buffers from `/dev/dma_heap/vidbuf_cached`; 4 x 16.9 MB = 68 MB in 16-bit, plus libcamera's own. Probable bottleneck, unconfirmed.
- Streams: 1280x720 YUV420 preview + the raw stream, `FrameDurationLimits` 40 ms, manual exposure.
- libcamera `v0.7.1+qbcfork.20260522-7-7e9fef0b` (not Cinemate's fork). It expands the 12-bit mode in software (`CcmpUnwrap::process`, one pass over 8.3 Mpx per frame), which may explain the 6 fps in the 12-bit bench.

## Questions

1. **Memory.** Cinemate's CMA size and how it is set (`cma-` param on `vc4-kms-v3d`, `cma=` on the kernel command line, other). Free CMA while recording 16-bit Clear HDR.
2. **Buffers.** How many raw buffers (and from which heap: CMA dma-heap, `vidbuf_cached`, system) cinepi-raw allocates in 16-bit Clear HDR; libcamera `bufferCount` for the raw and the preview stream.
3. **Streams and format.** Does Cinemate ask for the 16-bit raw unpacked (`RG16`) or PISP_COMP1? Raw-only, or raw + lores/viewfinder, and at what size?
4. **Clocks.** The overclock and link settings that give 25 fps in 16-bit Clear HDR: `rp1-overclock` / `rp1-clk-*`, link frequency, and the libcamera pixel-rate bound commits (`3c7b9ab`, `0413c13` in `Tiramisioux/libcamera`). Measured fps and drops in 16-bit and 12-bit Clear HDR.
5. **Per-frame work.** On which thread cinepi-raw copies or encodes the raw frame (the libcamera request callback, or a worker), and whether it copies the buffer at all before requeueing it.
6. **12-bit.** Cinemate's libcamera has no `CcmpUnwrap`, so its 12-bit frames stay companded (cheap). Any measured fps for 12-bit Clear HDR?
