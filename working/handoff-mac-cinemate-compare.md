# Prompt: compare Apertar and Cinemate on Clear HDR frame drops, 30 fps and the sensor probe

For a Claude or Fable session on the Mac with the Cinemate sources. Written on the Pi 2026-10-26. Paste the part below the line as the first message, after `apertar_publish.sh` has pushed Core `f60e301` and the KB has been pulled.

Write the answer to `~/apertar-kb/working/clearhdr-compare-answer.md`. Two models may answer the same prompt; if a file exists, write `clearhdr-compare-answer-<model>.md` instead of overwriting it.

---

You are comparing two camera stacks on the same hardware to find why one drops frames. You have the source of both; you cannot run the camera. Every claim you make is either **confirmed from source** (with `repo/path:line` at a named commit), **probable**, or **unknown**. A measurement can only be done on the Pi; when one would settle a question, describe it exactly so the Pi session can run it.

**Rule from the earlier answer, still valid: port the logic, do not copy Cinemate's code.** Describe mechanisms and numbers, not code.

## The two stacks

| | Apertar (ours) | Cinemate (reference) |
| --- | --- | --- |
| App | `Apertar-Core` fork, `main` at `f60e301` (C++, one process: capture, encode, write, WebUI) | `cinepi-raw` (`dev`, last read `63a08d5`) + `cinemate` (Python, `dev`) |
| libcamera | `v0.7.1+qbcfork.20260522` (not Cinemate's fork) | `Tiramisioux/libcamera`, branch `cinemate` |
| Driver | `imx585-v4l2-driver` branch `apertar` `e5b74d3` | branch `cinemate-7modes` / `cinemate-modes` |
| Pi | Pi 5 4 GB, link 891 MHz, `dtoverlay=rp1-clk-333mhz`, NVMe on PCIe x1 gen 3, raw to `/media/RAW` (ext4?) | per Cinemate docs |

Read first: `~/apertar-kb/llm/README.md` (how to find code in Core), then `~/apertar-kb/working/clearhdr-design.md` from "Frame drops: cause found" to the end, then `~/apertar-kb/working/sensor-capabilities.md`. Tools used on the Pi are in `~/apertar-kb/working/tools/` (`usample.py` = user-space sampler via `perf_event_open`; `ipa_rate.py` counts frames from the IPA's per-frame log line).

## What is established on the Pi (2026-10-25/26)

1. **Fixed (`94ac68d`):** Clear HDR recorded ~4 fps because libcamera (our fork) does two CPU passes per 16-bit frame on its pipeline thread, an in-place `rev16` byte swap in `PiSPCameraData::cfeBufferDequeue` and `RawStatsProducer::process`, and Core's unpacked raw buffers were the CFE's CPU-uncached ones. Cached heap buffers: 25 fps delivered, ~7 ms per pass. 12-bit mode has `CcmpUnwrap::process` instead of the swap.
2. **Fixed (`f60e301`):** startup sensor probe in Core (both WDR states, `configure()` per mode, `FrameDurationLimits`), 42 modes in 63 ms; Clear HDR 4K 30 fps at idle confirmed (VMAX 4500, 30.00 fps into libcamera).
3. **Open A, confirmed trigger:** at 25 fps, some 16-bit takes lose 25-36 of 250 frames (single-frame gaps every 7-10 frames). With Core **idle**, a buffered `dd` write (561 MB/s via the page cache) reproduces it (21.7 fps), pinned to any CPU; `dd oflag=direct` at 759 MB/s does not (25.00 fps). 8 raw buffers instead of 4 changed nothing. No swap, no direct reclaim, 2.4 GHz, < 60 C. All RP1 IRQs (`rp1-cfe`, `pispbe`, eth0, an i2c bus with 4.9 M IRQs, usb 7.5 M) are on CPU0. Core writes each DNG with buffered `open`/`write` and `posix_fadvise(DONTNEED)` before `close` (`src/cdng/CdngEncoder.cpp:1748-1779`, lossless `:1273`; MLV `src/mlv/MlvEncoder.cpp:949-968`).
4. **Open B:** recording at 30 fps loses ~20 % in both modes (12-bit lossless 228/291 though it writes only ~130 MB/s; 16-bit uncompressed 230/291). libcamera sees ~24 fps while recording, 30.00 at idle. Camera thread while recording: 72 % (12-bit), 52 % (16-bit). Core copies the whole raw frame on libcamera's completion thread (`CameraController.cpp`, `recordRawFrame`, anchor `copyRawBytes(buffer, rawCopy.data()`) and, in 12-bit cDNG, maps samples back to codes there too (`compressClearHdrFrame(rawCopy`); 4 raw + 4 preview buffers.
5. **Open C:** this driver reports `ScalerCropMaximum` = `(0, 0)/<mode size>` for every mode, so crop modes for the menus cannot come from the probe yet.

## Theories and what to compare

**A. Page-cache writeback starves the CFE (probable).** Mechanism unknown (IOMMU or fabric contention from 4 KB-page writeback, IRQ latency on CPU0, something else). Answer from Cinemate's source and image:
- How cinepi-raw writes DNG/MLV files: `O_DIRECT`? write size and alignment? one file per frame? a RAM pool and a dedicated writer thread (the earlier answer said "disk writes from a RAM pool")? `fsync`/`sync_file_range`/`fadvise`?
- Does Cinemate's install/image tune the kernel for this: `vm.dirty_*`, IO scheduler, NVMe queue settings, IRQ affinity (moving `rp1-cfe` or others off CPU0), CPU isolation, `nice`/RT priority of the capture thread, filesystem mount options? Look in the installer, `make-release-image.sh`, systemd units, `config.txt` tabs, `cinemate-handbook/lessons/hardware-log.md`.
- Did Cinemate ever record "frames drop when the disk is busy" or similar, and the fix?
- Propose the concrete `O_DIRECT` design for Core's two writers (alignment, the DNG header/IFD, the unaligned tail, error handling), and the Pi measurement that proves it (the `dd` comparison plus `takes.sh` batches).

**B. 30 fps: work on libcamera's completion thread and the buffer loop (probable).** Answer:
- In cinepi-raw at 4K Clear HDR 30 fps: which thread copies the raw frame, how many raw and preview buffers, and when the buffer goes back to libcamera. Per-frame time budget they measured.
- Does Cinemate's libcamera fork also byte-swap 16-bit unpacked raw in software (`rev16`, stream flag bit 5 in `cfeBufferDequeue`) and compute raw statistics in software for 16-bit? If not, how does it get stats or AE in 16-bit, and why does ours need the swap at all (CFE endianness, a config bit)? This is ~15 ms of our 33 ms frame.
- Propose the plan for Core: move the copy (and the 12-bit code mapping) to recorder workers, buffer counts, and what to measure after each step.

**C. Sensor probe and crop modes.** Compare our probe (`probeSensorModes` in `CameraController.cpp`, next to `applyImx585HdrControls`) with cinepi-raw `core/options.cpp` `print_modes`:
- Anything cinepi-raw does that we miss (pixel-rate env `LIBCAMERA_RPI_MAX_PIXEL_RATE`, retries, mono, packing, `validate()` adjustments)?
- `read_driver_mode_metadata` (`core/driver_mode_metadata.hpp`): what does the `cinemate-modes` driver expose per mode (crop rectangle, active area, binning), through which interface, at which commit? Does the `apertar` branch driver have it? If not, what is the smallest driver change that would give Core real crop rectangles?

## Deliverable

One markdown file as named above, in this shape:

1. A short table: theory, verdict (confirmed from source / probable / unknown / ruled out), the one-line reason.
2. Per theory: what Cinemate does (with `repo/path:line@commit`), what Apertar does (`path:line@f60e301`), the difference that matters, the proposed change for Apertar, and the Pi measurement that would confirm it.
3. Anything surprising you found that was not asked.

Keep it short; numbers over prose. No code copied from Cinemate.
