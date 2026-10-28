# Q4: can the 16-bit endian swap be avoided or fused?

Reader: Q4 swap (research subagent, Claude Opus 5.5) · trees: libcamera-apertar `6b0b49f` (base libcamera-qbc `7e9fef0`),
libcamera (cinemate) `bfe0b76`, libpisp `v1.3.0` (`9ba67e6`), kernel-rpi `rpi-6.12.y` `5bd564a` (sparse; I added
`Documentation/userspace-api/media/v4l`, `Documentation/devicetree/bindings/media`, `mm/gup.c`), imx585-apertar `98b9862`,
imx585-v4l2-driver `18c1eb2`, apertar-core `f60e301` (git show only), cinemate `d6cc93e`, cinemate-handbook `c99ff77`, cinepi-raw
`63a08d5` · date 2026-10-26

Labels: **CONFIRMED** = I opened the line or page and it says so. **PROBABLE** = derived, reasoning given. **UNCONFIRMED** = needs
the Pi or a source I could not open. Code: `repo/path:line@commit`. Web: reachable only through WebFetch on github.com and
raw.githubusercontent.com. `datasheets.raspberrypi.com`, `helpx.adobe.com`, `paulbourke.net`, `docs.kernel.org`,
`patchwork.libcamera.org` and `android.googlesource.com` were blocked (proxy 403 or DNS). Search-engine excerpts of blocked pages are
labelled PROBABLE, never CONFIRMED.

Units: 1 MB = 10^6 B. F = 3840 x 2200 x 2 = 16,896,000 B (whole CFE buffer, stride 7680 = width x 2). A = 3840 x 2160 x 2 =
16,588,800 B (the active area Core copies and writes to the DNG).

## Short answer

1. **No switch removes the swap (CONFIRMED).** The RP1 CSI-2 block has no byte-swap for RAW16. Raspberry Pi's njhollinghurst:
   "an endian-swap was omitted from the hardware pipeline", "`RAW16` cannot be byte-swapped in hardware". The PiSP FE and BE
   image-format word has no byte-order bit. The BE driver accepts only little-endian `S*16`. The IMX585 drivers write no
   byte-order or data-type register, and the Sony register map is not public.
2. **The real data type (0x2E) makes it worse, not better.** Kernel commit `fda4b68` (Naushir Patuck, 2025-07-04) set `csi_dt = 0`
   ("wildcard") for the four Bayer16 formats, to work around a "16-bit mismatch in the hardware" (CONFIRMED). Cinemate's mono rig
   still had `Y16` at 0x2E on 6.12.y and got corrupted 16-bit frames until it patched that entry to 0. Those frames were not just
   byte-swapped. They showed a repeating 16-byte motif (CONFIRMED in the handbook; that the fix alone cured it is PROBABLE).
   Wildcard plus no remap means the wire bytes land in memory unchanged. RAW16 sends the high byte first (PROBABLE), so memory holds
   big-endian samples.
3. **Only the back end needs the swapped full frame (CONFIRMED in code).** The DNG has three free alternatives: Core's T25 copy,
   or Core's row copy into the encoder scratch, could do `rev16` at no extra memory traffic, or Core could write an `MM` DNG. The SW
   stats can apply `vrev16` in registers. The IPA reads only stats.
4. **`MM` DNGs are legal and readable by Adobe and LibRaw.** The DNG SDK's `ReadUncompressed` and LibRaw's `read_shorts` both swap
   16-bit samples from big-endian files (CONFIRMED). Resolve is UNCONFIRMED. `MM` is needed only on a path with **no** CPU copy at
   all. O_DIRECT from a mapped dma-buf fails, because the kernel's page-pinning code (GUP) refuses `VM_PFNMAP` mappings (PROBABLE,
   from `mm/gup.c`).
5. **Savings, per frame, over the four passes that change** (swap or derivative pass, stats read, BE, Core copy; 128.8 MB today):
   - O1, fuse the stats into the swap: **4.2 MB**.
   - O2, skip the 8 rows nobody reads: 0.12 MB.
   - O3, an out-of-place swap that doubles as Core's copy: **37.4 MB**. It needs Q5's no-copy Core.
   - O5, swap and BE on every 2nd frame, with Core's copy swapping the other frames: **47.8 MB**.
   - O4, no full swap; the BE reads a CPU-made half-resolution little-endian Bayer: **59.5 MB**.
   - O4 + no Core copy + `MM` DNG: **92.7 MB**.
6. **Cheapest.** O1 is the cheapest to build: small, libcamera only, and it lets the stats go back to every row at no memory cost.
   But it is too small to fix 30 fps on its own (PROBABLE). The cheapest large saving is O5, if a 15 fps monitor while recording is
   acceptable. Otherwise O4. Run the ablation first (experiment E1: skip the swap, accept a broken preview) to learn whether 33.8 MB
   per frame of swap traffic matters at all.

## 1. Why the data arrives byte-swapped

### 1.1 The wire

| Claim | Label, evidence |
| --- | --- |
| RAW16 is CSI-2 data type 0x2E. It was not defined in CSI-2 v1.3 | CONFIRMED: 6by9 in raspberrypi/libcamera#99 (2023-12-22), "it isn't defined in CSI2 v1.3, but is now defined as 0x2e" (https://github.com/raspberrypi/libcamera/issues/99, opened via WebFetch). The kernel `MIPI_CSI2_DT_RAW16` constant is used at `kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h:286@5bd564a` |
| RAW16 sends bits 15:8 of each pixel first, then bits 7:0 | **PROBABLE.** The MIPI CSI-2 specification is members-only; no public text with the RAW16 byte figure was found (two web searches). Derivation: (1) V4L2 `S*16` is little-endian in memory, "Bytes are stored in memory in little endian order" (`kernel-rpi/Documentation/userspace-api/media/v4l/pixfmt-srggb16.rst:25@5bd564a`). (2) With remap off, the RP1 writes the bytes in arrival order (§1.2). (3) libcamera must `rev16` every sample to get correct values (§1.3), and Patrik verified the swapped DNGs are right ("DNG pixel data in the right byte order (median raw 3643 vs 3625 before)", `apertar-kb/lessons/hardware-log.md:223`). So the first wire byte is the high byte. This matches the CSI-2 convention for packed RAW, high bits first: "Each of the first 4 bytes contain the 8 high order bits of the pixels" (`pixfmt-srggb10p.rst:24-26@5bd564a`) |

### 1.2 What the RP1 CFE does with a 16-bit stream

| Claim | Label, evidence |
| --- | --- |
| All four Bayer16 entries carry `.csi_dt = 0, /* Avoid RP1 HW mismatch for 16-bit modes. */`. Mono `Y16` still carries `MIPI_CSI2_DT_RAW16` | CONFIRMED `cfe_fmts.h:196-227` (Bayer16) and `:282-289` (Y16, `csi_dt` at `:286`) `@5bd564a` |
| The commit that set 0 is `fda4b68`, "drivers: media: cfe: Workaround for 16-bit mismatch in the hardware" (naushir, 2025-07-04). Body: "Set the data type for 16-bit modes to 0 (wildcard) to workarond the 16-bit mismatch in hardware. We also need to suppress the warning about DT == 0 on start stream in these cases." Before it, the four entries were `MIPI_CSI2_DT_RAW16` | CONFIRMED: https://github.com/raspberrypi/linux/commits/rpi-6.12.y/drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h and https://github.com/raspberrypi/linux/commit/fda4b68 (WebFetch). The shallow local clone cannot show it |
| One week earlier, `274049e` (naushir, 2025-06-27), "Avoid unpack operation for 16-bit formats": "The unpack operation is redundant for 16-bit sensor formats, don't set the hardware to do it". This is the `fmt->depth != 16 &&` guard on `CSI2_MODE_REMAP` | CONFIRMED: https://github.com/raspberrypi/linux/commit/274049e and `cfe.c:889-893@5bd564a` |
| Why: njhollinghurst (2025-06-26, libcamera#99): "the better fix is to turn off the "Remap" function in the hardware, only when `MIPI_CSI2_DT_RAW16` is requested, because that is the specific case that misbehaves"; "Remapping to 16-bit LE is controlled by the requested DT, not the actual DT seen on the wire in the 'wildcard' case"; "`RAW16` cannot be byte-swapped in hardware; also remapping must not be enabled"; "compression and ISP-FE statistics will also be unavailable for `RAW16` and `RAW14`". Earlier (2024-02-29): "For RP1 ... it was supposed to be supported, but an endian-swap was omitted from the hardware pipeline" | CONFIRMED (issue page via WebFetch; the tool returns quoted fragments, so wording may be partly cut, not altered) |
| The data type actually programmed comes from the sensor's `get_frame_desc`, or from `cfe_fmt->csi_dt` if the sensor has none. It goes into bits 12:7 of `CSI2_CH_CTRL` | CONFIRMED `csi2.c:326-347` (fallback, `*dt = cfe_fmt->csi_dt` at `:346`), `:351-384` (`-ENOIOCTLCMD` falls back at `:368`), `:430` (`set_field(&ctrl, dt, DT_MASK)`), `DT_MASK` = bits 12:7 at `:102` `@5bd564a` |
| The IMX585 drivers implement no `get_frame_desc`. So the fallback runs and the programmed DT is 0 | CONFIRMED: `imx585-apertar/imx585.c:2458-2466@98b9862` (pad ops: `enum_mbus_code, get_fmt, set_fmt, get_selection, enum_frame_size, enable_streams, disable_streams`). Same in `imx585-v4l2-driver/imx585.c@18c1eb2` (grep: no `frame_desc`) |
| Apertar's raw path is CSI-2 to FE (`CSI2_MODE_FE_STREAMING`) to `fe_image0`. No remap or compression is applied in that mode. The CSI-2-to-memory path (`is_csi2_node`) would be `CSI2_MODE_NORMAL` for 16-bit (no repack) | CONFIRMED `cfe.c:839-872` (FE mode, `CSI2_MODE_FE_STREAMING` at `:868`; `WARN_ON(fmt->depth != 16 && !fmt->csi_dt)` at `:858`), `:874-912` (CSI-2 node: remap skipped when `depth == 16`, `:890-893`) `@5bd564a`. The FE link and node are from Q1 (`pisp.cpp:1366,2686-2697@6b0b49f`) |
| The channel-control register as the driver knows it: DMA_EN (0), mode (2:1), FORCE (3), AUTO_ARM (4), VC (6:5), DT (12:7), IRQ enables (17:13), LC (27:18), FLUSH_FE (28), PACK_LINE (29), PACK_BYTES (30). Modes are NORMAL, REMAP, COMPRESSED, FE_STREAMING. **No byte-swap bit or mode** | CONFIRMED `csi2.c:89-103`, `csi2.h:23-26@5bd564a`. Bit 31 and the other unlisted bits are undefined in the driver. Whether they do anything is UNCONFIRMED: "The PHY and CSI-2 receiver part have no public documentation" (upstream binding, https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/media/raspberrypi,rp1-cfe.yaml). Given njhollinghurst's statement, a hidden swap bit is very unlikely (PROBABLE) |
| With DT = 0 the CFE takes every packet type on the VC. That is why the IMX585 16-bit mode carries 20 OB rows (the sensor appears to send them with another DT) and the buffer is 2200 rows | CONFIRMED as the drivers' own explanation: `imx585-apertar/imx585.c:547-551,784-790@98b9862` ("likely because the CFE accepts every CSI2 DT when csi_dt=0 and the sensor uses a different DT for OB"). Cinemate's patch note: "with csi_dt = 0 the CFE accepts every CSI-2 data type ... mono 16-bit will start capturing the sensor's 20-row optical-black prepend that csi_dt = MIPI_CSI2_DT_RAW16 was silently discarding" (`cinemate/scripts/rp1-cfe-y16-csi-dt0.patch@d6cc93e`). That the OB rows use a different DT is PROBABLE |

Net (PROBABLE): the wire bytes reach memory in arrival order, high byte first. Every 16-bit word is therefore byte-reversed against
the little-endian layout the FE pixel blocks, the BE and V4L2 expect. libcamera-qbc's IPA says the same: "the CFE→FE input is
big-endian (omitted byte-swap in CSI2AXI) while FE pixel blocks assume little-endian, so any non-trivial FE pixel processing
corrupts the data" (`libcamera-apertar/src/ipa/rpi/pisp/pisp.cpp:699-706@6b0b49f`, CONFIRMED text).

### 1.3 What libcamera does

| Claim | Label, evidence |
| --- | --- |
| The flag is "Needs16bitEndianSwap: Indicates that the input stream needs a software 16-bit endian conversion to be applied before ISP processing". It came in `332b04ce` (Naushir Patuck, 2025-01-13): "These are to workaround hardware restrictions in the CFE hardware" | CONFIRMED `libcamera-apertar/src/libcamera/pipeline/rpi/common/rpi_stream.h:85-89@6b0b49f`; `git show 332b04ce` |
| It is set whenever the sensor bus format is 16 bpp, with no other condition, and logs "statistics will not be correct". There is no environment variable or config switch | CONFIRMED `pisp.cpp:1740-1750@6b0b49f`. The Cinemate fork adds one exemption, PISP_COMP1 CFE output (`libcamera/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1455-1459@bfe0b76`, commit `bcdd7e1`; see `working/compare-raw/b2-libcamera-16bit.md` Q6) |
| The raw buffer Core receives **is** the CFE buffer. With a raw stream requested, `cfe_[Cfe::Output0]` is the app's stream (`External`), and the BE input is that same buffer | CONFIRMED `pisp.cpp:1734-1737` (External), `:2750-2757` (`prepareBe` queues `cfe_[Cfe::Output0]` buffer on `isp_[Isp::Input]`) `@6b0b49f` |
| `do16BitEndianSwap`: per row, `count = (width+7)/8` iterations of NEON `ld1 {v1.16b}` / `rev16 v1.16b` / `st1 #16`, **in place**, aarch64 only. At width 3840: (3840+7)/8 = 480 iterations x 16 B = 7,680 B = the whole stride; 2,200 rows means 1,056,000 iterations. It reads F = 16.9 MB and writes F = 16.9 MB per frame | CONFIRMED `pisp.cpp:397-416@6b0b49f`; arithmetic shown |
| Where it runs: in `cfeBufferDequeue`, between `dmabufSyncStart/End` (RW), on the pipeline thread (L1); or in `RawCpuWorker::process`, swap then stats under one sync pair, when `QBC_RAW_CPU_WORKER` is on (L2) | CONFIRMED `pisp.cpp:2205-2224` (thread), `:2114-2150` (`submitRawCpuJob`, `work.swap16` at `:2129`), `:814-831` (worker: swap `:817-818`, stats `:820-829`), sync helpers `:320-339` (`DMA_BUF_SYNC_START/END | DMA_BUF_SYNC_RW`) `@6b0b49f` |
| The SW stats read the swapped buffer as little-endian `uint16x8_t` (`vld1q_u16`). With `QBC_RAW_STATS_ROW_STEP=4` they read 2 of every 8 rows: 1100 row pairs / 4 = 275 pairs = 550 rows x 7,680 B = **4.22 MB** per frame | CONFIRMED `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/raw_stats.cpp:31-42` (row step), `:205-307` (loop, loads at `:233-234`) `@6b0b49f`; arithmetic shown |
| Measured cost (brief §3, before L1/L2): swap 6.1 ms idle, 9.9 ms recording. That is 33.8 MB / 6.1 ms = 5.5 GB/s and 33.8 / 9.9 = 3.4 GB/s. At 30 fps the swap alone moves 33.79 x 30 = **1.01 GB/s** | CONFIRMED figures (`apertar-kb/lessons/hardware-log.md:188`, handoff:52); arithmetic shown |
| The PMU agrees with this byte model. Before L1 the CameraManager thread took 0.57 M L3 refills per frame (`hardware-log.md:161-162`). Swap read (16.9) + stats read at row step 1 (16.9) = 33.8 MB = 528 k lines of 64 B, against 570 k measured | PROBABLE (assumes event 0x2A counts 64-B DRAM line fills attributable to the thread) |

## 2. Sensor side: can the IMX585 send the other byte order or another data type?

| Claim | Label, evidence |
| --- | --- |
| The 16-bit Clear HDR mode is `common_clearHDR_mode` (WDMODE 0x10, COMBI_EN 0x02, thresholds, CCMP slopes) plus `mode_4k_regs_16bit` (ADDMODE, ADBIT, MDBIT 0x01 overridden, window crop to 2180 rows). At stream start the driver writes `CCMP_EN = 0` and `MDBIT (0x3023) = 0x03` ("16-bit: linear") | CONFIRMED `imx585-apertar/imx585.c:484-519`, `:747-753`, `:2252-2261@98b9862` |
| Neither driver writes a byte-order, data-type or MIPI-format register. The register defines cover mode select, XMSTA, sync, INCK, data rate, binning, window, lane mode, VMAX/HMAX, SHR, HDR thresholds/CCMP, BLKLEVEL, gain, flip and TPG only | CONFIRMED (absence) `imx585-apertar/imx585.c:51-190@98b9862` (defines), grep for `endian|swap|byte|DT_|data type` in both drivers: only the OB/DT comments above |
| Whether the IMX585 has such a register | UNCONFIRMED. Sony's register map is under NDA, and no public datasheet excerpt names one (web search: Leopard/FRAMOS module datasheets only). In libcamera#99 naushir asked "Are you able to do an endian swap in the sensor itself?" (2024-02-29); no answer is recorded in the thread (WebFetch summary) |
| Even with one, another DT would not help. The receiver's RAW16 path has no swap. A RAW8 label at double width would be stored byte for byte in the same order. A RAW14 label would invoke an unpacker that cannot make 16 bits ("`RAW14` cannot be remapped to 16 bits") | PROBABLE (follows from §1.2) |
| The only sensor-side way to drop the swap is a different mode: 12-bit Clear HDR with CCMP sets no swap flag (`bitsPerPixel == 16` only). But that records companded 12-bit, not 16-bit linear, and libcamera-qbc still forces the CFE to unpacked u16 for WDR | CONFIRMED `pisp.cpp:1745` (flag only at 16 bpp), `:1785-1798` (WDR detect), `:1853-1874` (unpacked u16 forced) `@6b0b49f`. Out of scope for "16-bit uncompressed" |

## 3. Receiver side: CFE, FE and the data type

| Claim | Label, evidence |
| --- | --- |
| FE input config is `streaming`, `format` (a `pisp_image_format_config`), `axi`, `holdoff`. **No byte order** | CONFIRMED `libpisp/src/libpisp/frontend/pisp_fe_config.h:84-92@v1.3.0` |
| libcamera programs FE input = `PISP_IMAGE_FORMAT_BPS_16`, streaming, output 0 = the 16-bit image. The "14-bit bodge" (width x 14/16) shows the same trick of describing bytes as something else; for 16-bit there is nothing to gain | CONFIRMED `pisp.cpp:2391-2449` (`:2409-2415`) `@6b0b49f` |
| FE decompand is a 65-entry PWL LUT. A byte swap of a 16-bit value has 256 discontinuities and cannot be expressed in it. The FE downscaler, compressor, BLA, DPC and stats all see swapped values | CONFIRMED LUT size `pisp_fe_config.h:107-112@v1.3.0`; "cannot be expressed" PROBABLE (arithmetic of a PWL). The IPA no-ops the FE blocks for this reason (`ipa/rpi/pisp/pisp.cpp:697-726@6b0b49f`) |
| A downscaled preview Bayer from FE output 1 is therefore impossible at RAW16 (Q1 reached the same conclusion) | CONFIRMED (njhollinghurst: compression and FE statistics unavailable for RAW16). That downscale fails the same way is PROBABLE |
| Restoring DT 0x2E for Bayer16 would **break** the data, not fix the byte order. The hardware's DT-keyed remap for RAW16 "misbehaves" and "RAW16 cannot be byte-swapped in hardware". Cinemate's mono rig is the field test: `Y16` kept 0x2E in 6.12.y, and every 16-bit take carried "a repeating 16-byte motif = PiSP COMP1-style compressed blocks in a buffer labeled/consumed as uncompressed R16, additionally scrambled by libcamera's 16-bit endian swap". After the `Y16 csi_dt=0` patch: "correct frames now in all modes ... no repeating motif" | CONFIRMED: statements (libcamera#99) and the observation (`cinemate-handbook/lessons/hardware-log.md:834-843`, `:865-885@c99ff77`; patch `cinemate/scripts/rp1-cfe-y16-csi-dt0.patch@d6cc93e`). PROBABLE that DT 0 was the cure: the night entry changed the kernel patch, the sensor driver and two app branches together. PROBABLE that Bayer16 behaves like Y16 (same CSI-2 block, same DT) |
| The only upside of 0x2E would be dropping the 20 OB rows: 20 x 7,680 = 153,600 B, 0.9 % of every pass | CONFIRMED arithmetic; the drop is CONFIRMED for Y16 by Cinemate's patch note, PROBABLE for Bayer16 |
| What "16-bit mismatch" means at register level | UNCONFIRMED. naushir asked (2025-06-26) "Should we be using the 14-bit id `MIPI_CSI2_DT_RAW14` for the 16-bit mode?" njhollinghurst's footnote on RAW14 reads "it might be possible if the camera could change its DT to 0x2E, but that's incompatible with the current fix". That suggests the RP1 decodes 0x2D/0x2E inconsistently. Speculation, not a finding |

## 4. Back end side: can the PiSP BE read big-endian samples?

| Claim | Label, evidence |
| --- | --- |
| `pisp_image_format` bits: BPS 8/10/12/16, planarity, sampling, `ORDER_NORMAL/ORDER_SWAPPED`, shift 0-8, BPP_32, X_VALUE, compression modes, HOG, integral, wallpaper, three-channel. **No byte-order flag** | CONFIRMED `libpisp/src/libpisp/common/pisp_common.h:39-95@v1.3.0` |
| `ORDER_SWAPPED` is component order (NV21 vs NV12, UYVY vs YUYV, NV61), not byte order | CONFIRMED `libpisp/src/libpisp/common/pisp_utils.cpp:230-241@v1.3.0` |
| BE input format libcamera uses: `BPS_16 + UNCOMPRESSED` | CONFIRMED (Q1: `pisp.cpp:166-169,2510-2517@6b0b49f`) |
| The kernel BE driver lists only `V4L2_PIX_FMT_S{RGGB,BGGR,GRBG,GBRG}16` for 16-bit Bayer, which V4L2 defines as little-endian | CONFIRMED `kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be_formats.h:337-375@5bd564a`; `pixfmt-srggb16.rst:25` |
| Raspberry Pi: "there is no HW mechanism to endian swap directly in the ISP pipeline" and "we only deal with little endian for 16-bits" | CONFIRMED (naushir, 2024-02-29, libcamera#99) |
| No BE block can undo it. DPC, GEQ, TDN and SDN run before any LUT (`PISP_BE_BAYER_ENABLE_*` order, `pisp_be_config.h:35-57@v1.3.0`), and the BE tonemap comes after BLC/WBG | PROBABLE |

## 5. Who actually needs little-endian samples?

| Consumer of the raw buffer | Needs LE in memory? | Label, evidence |
| --- | --- | --- |
| PiSP BE (preview) | **Yes, full frame**: rows 4..2195 (crop rows 20..2179 +/- 16 rows of context, Q1) = 2192 of 2200 rows | CONFIRMED §4; rows from Q1 (`q1-backend.md:105-112`) |
| SW raw stats (`RawStatsProducer`) | No. One `vrev16q_u8` after each `vld1q_u16` would read BE data directly (same bytes, one extra instruction per 16 B) | CONFIRMED loads at `raw_stats.cpp:233-234@6b0b49f`; the change is PROBABLE (simple) |
| IPA (AGC/AWB) | No raw access: it reads the stats buffer | CONFIRMED (stats replace the CFE buffer, `pisp.cpp:2120-2150@6b0b49f`) |
| CFE hardware stats | Already wrong at 16-bit and overwritten by the SW stats | CONFIRMED `pisp.cpp:1801-1820@6b0b49f` |
| Core (DNG) | Only through `copyRawBytes` (a plain `memcpy` of the active area), then the encoder's per-row `memcpy` into a scratch chunk (16-bit branch). No other Core reader of the raw buffer | CONFIRMED `apertar-core/src/camera/CameraController.cpp:6779-6785` (copy), `:7269,7446` (the only two call sites), `src/cdng/CdngEncoder.cpp:1044-1045` (row copy), `:1861-1909` (scratch chunk = 7,680 x 64 = 491,520 B) `@f60e301`. The Pi runs `d9f00d4` (T25 moves the copy to a recorder worker); that the encoder row copy is unchanged there is UNCONFIRMED |

**So once the DNG stops needing the swap, the BE is the only consumer left.** That is the whole question. Either the BE keeps
getting a full-resolution little-endian frame (and the swap stays, possibly fused), or the BE is given something else.

## 6. Options, with bytes per frame

The table counts only the passes that change between options: the swap or derivative pass, the stats read, the BE (57.6 MB/frame,
Q1 `q1-backend.md:26`), and Core's T25 copy (r A + w A = 33.18 MB). These are constant across options and left out: the CFE write
(16.9), the page-cache write of the DNG and the NVMe DMA. Today (L1/L2, row step 4): 33.79 + 4.22 + 57.6 + 33.18 = **128.79
MB/frame**.

| # | Option | Swap / derivative | Stats read | BE | Core copy | Sum | **Saved / frame** | at 30 fps | Work needed | Label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Today | 33.79 | 4.22 | 57.6 | 33.18 | 128.79 | 0 | 0 | none | CONFIRMED code; BE figure from Q1 |
| O1 | Stats fused into the swap (stats on the swapped rows, from registers or from a hot L2 band) | 33.79 | 0 | 57.6 | 33.18 | 124.57 | **4.22** (16.9 at row step 1) | 127 MB/s | small libcamera patch (worker) | PROBABLE |
| O2 | Swap only rows 4..2195 (skip 8 rows nobody reads) | 33.67 | 4.22 | 57.6 | 33.18 | 128.67 | 0.12 | 3.7 MB/s | trivial; stats must skip the same rows | CONFIRMED arithmetic: 8 x 7,680 x 2 = 122,880 B |
| O3 | Out-of-place swap from an internal CFE buffer into the app's raw buffer, so the swap **is** the copy; Core writes the DNG from it, no T25 copy (+ O1) | 33.79 | 0 | 57.6 | 0 | 91.39 | **37.40** | 1.12 GB/s | large libcamera patch (separate CFE pool) + Core no-copy (Q5) | PROBABLE |
| O5 | BE (and swap) every 2nd frame; other frames delivered unswapped with a flag, and Core's copy does `rev16` (free); stats on unswapped frames use `vrev16` in registers | 16.90 avg | 2.11 avg | 28.8 avg | 33.18 | 80.99 | **47.80** | 1.43 GB/s | medium libcamera patch (skip BE on a frame) + small Core patch; monitor at 15 fps while recording | PROBABLE |
| O4 | No full-frame swap. One CPU pass reads F, writes a 1920x1100 little-endian Bayer (2x2 same-colour bin) and computes the stats; the BE reads that; Core's copy does `rev16` (free), DNG stays `II` | 16.90 r + 4.22 w = 21.12 | 0 | 15.0 | 33.18 | 69.30 | **59.49** | 1.78 GB/s | large libcamera patch (BE input pool + format + geometry) | PROBABLE (BE 15.0 MB = Q1 case E, `q1-backend.md:203`) |
| O4d | O4, but the derivative keeps every 2nd row pair (vertical decimation): reads 550 pairs x 2 x 7,680 = 8.45 MB | 12.67 | 0 | 15.0 | 33.18 | 60.85 | **67.94** | 2.04 GB/s | as O4; preview aliases vertically | PROBABLE |
| O6 | `MM` DNG alone (libcamera still swaps) | 33.79 | 4.22 | 57.6 | 33.18 | 128.79 | 0 | 0 | Core IFD writer in big-endian | CONFIRMED (nothing changes) |
| O4+Q5 | O4, no Core copy, DNG written by buffered `write()` straight from the unswapped camera buffer as **`MM`** | 21.12 | 0 | 15.0 | 0 | 36.12 | **92.67** | 2.78 GB/s | O4 + Q5 + `MM` IFD writer | PROBABLE |

Arithmetic for O5: per pair of frames, 33.79 (swap with fused stats) + 4.22 (stats on the other frame) + 57.6 (one BE) +
2 x 33.18 = 161.97, so 80.99 per frame and 128.79 - 80.99 = 47.80 saved. For comparison, the brief's "TDN off" (Q1) saves 37.6 MB
without touching the swap.

### 6.1 O1: fuse the stats into the swap

- The stats already walk row pairs of the same buffer. In L2 they run on the same worker right after the whole-frame swap
  (`pisp.cpp:814-831@6b0b49f`). By then the first rows are long gone from the 2 MB L3, so the stats re-read 4.22 MB from DRAM
  (PROBABLE; Pi 5 cache sizes of 512 KB L2 per core and 2 MB shared L3 come from Raspberry Pi's product brief, not opened here).
- Two shapes. (a) Inside the swap loop, for row pairs with `cr % step == 0`, feed the swapped registers to the stats
  accumulators: zero extra loads. (b) Swap a band of 64 rows (64 x 7,680 = 491,520 B, inside L2), then run the stats on that band
  before moving on. (b) keeps `RawStatsProducer` almost unchanged; it needs an "accumulate band / finalise" split of `process()`
  (`raw_stats.cpp:133-316@6b0b49f`). PROBABLE.
- Bonus: the stats can go back to row step 1 at no DRAM cost (L1's AE/AWB quality concern, `hardware-log.md:212-213`). Only the
  compute remains: the stats were ~5.8 ms per frame idle at step 1 (handoff:52), against a swap that is memory-bound. PROBABLE.
- The task's description is right: a fused pass reads and writes every row. It does that already, because it is the swap.

### 6.2 Fusing the swap into Core's copy

- Core copies every DNG byte twice (T25 `memcpy`, then the per-row `memcpy` into the encoder scratch; §5). Either copy can do
  `ld1 / rev16 / st1` instead of a plain copy at the same byte count. A `rev16` is one extra NEON op per 16 B in a memory-bound loop
  (PROBABLE).
- On its own this saves nothing, because the BE still needs the swapped buffer. It becomes the free DNG half of O4 and O5.

### 6.3 Big-endian (`MM`) DNG

| Claim | Label, evidence |
| --- | --- |
| The DNG spec allows either byte order and requires readers to support both: "DNG readers are required to support either byte order, even for files from a particular camera model. Writers can write either byte order, whichever is easier and/or faster for the writer." | PROBABLE: search-engine excerpt of Adobe's DNG 1.6.0.0 specification (https://paulbourke.net/dataformats/dng/dng_spec_1_6_0_0.pdf); that host and helpx.adobe.com were blocked here, so not opened. TIFF 6.0 ("All baseline TIFF readers must support both byte orders") also only as a search excerpt |
| Adobe DNG SDK (the reader behind ACR/Lightroom) swaps 16-bit samples of an opposite-order file: in `ReadUncompressed`, `else if (bitDepth == 16)` ... `stream.Get (...)`; `if (stream.SwapBytes ()) DoSwapBytes16 (...)` | CONFIRMED in the 1.7.0.0 SDK mirror https://raw.githubusercontent.com/emmcb/adobe-dng-sdk/master/dng_sdk/source/dng_read_image.cpp (WebFetch). That ACR ships this code path is PROBABLE |
| LibRaw (darktable, RawTherapee and many others): `packed_dng_load_raw` uses `read_shorts` for `tiff_bps == 16`, and `read_shorts` swaps when the file order differs from the host (`if ((order == 0x4949) == (ntohs(0x1234) == 0x1234)) libraw_swab(...)`) | CONFIRMED https://raw.githubusercontent.com/LibRaw/LibRaw/master/src/decoders/dng.cpp and `.../src/utils/read_utils.cpp` (WebFetch) |
| DaVinci Resolve with an `MM` CinemaDNG sequence | UNCONFIRMED (closed source; no public statement found). Desk test E5 |
| Core writes `II` and host-order IFD values (`memcpy` of native values), so `MM` needs every IFD value written big-endian, not just the header | CONFIRMED `apertar-core/src/cdng/CdngEncoder.cpp:1740-1744`, `src/cdng/IfdBuilder.hpp:36@f60e301`. cinepi-raw is the same (`cinepi/dng_encoder.cpp:1138@63a08d5`, `"II"`) |
| `MM` matters only when no CPU pass touches the DNG data. The no-copy route cannot use O_DIRECT from the camera buffer: dma-heap mappings are `VM_IO | VM_PFNMAP` and the kernel's page-pinning code (GUP) returns `-EFAULT` for them. So the remaining copy is the kernel's page-cache copy, which cannot swap, and the file must be `MM` | CONFIRMED `kernel-rpi/drivers/dma-buf/heaps/cma_heap.c:185`, `mm/gup.c:1277-1278@5bd564a`. That direct I/O pins through that check is PROBABLE (standard dio path, not opened). Which heap Core allocates from is UNCONFIRMED (system heap `remap_pfn_range` gives the same flags, PROBABLE) |

### 6.4 O3: make the swap the copy

Today one buffer serves the CFE, the BE and the app. If the CFE wrote into an internal pool and the swap wrote out of place into
the app's raw buffer, three things would change. The CFE buffer would go back to the CFE about 10 ms after dequeue instead of after
BE done + request completion + Core's copy. The BE would read the app buffer (it already does today). Core could hold that buffer for
its DNG without a copy, which is Q5's idea minus its CFE-starvation risk. Saving: Core's 33.18 MB copy, plus 4.22 with O1. Without
the Core change it saves nothing. A large libcamera change: the RPi pipeline routes `External` raw straight onto
`cfe_[Cfe::Output0]` (`pisp.cpp:1734-1737@6b0b49f`). All PROBABLE.

### 6.5 O4 / O5: give the BE less

- **O4** is Q1's "half-size Bayer made by the CPU" (`q1-backend.md:203`), with one change: the pass that makes it replaces the swap
  instead of adding to it. That pass reads the frame once, writes 4.22 MB and computes the stats. The full-resolution swap is
  gone, and Core's copy swaps the DNG for free. The raw buffer can also complete as soon as that pass is done, not after the BE
  (Q1). Preview: 1920x1080 Bayer into a 1280x720 output, which is enough for monitoring (PROBABLE). Cost: a second BE input pool and
  format, TDN buffers at 1920x1100, and a 1920-wide output crop/scale (Q1/Q2 owners).
- **O5** keeps full-resolution rendering but only for every 2nd frame while recording. It needs the pipeline to complete a request
  without a BE run (Q1/Q2: "Running the BE every Nth frame ... needs libcamera patches") and a per-frame "swapped" flag in the request
  metadata for Core. All DNGs stay `II`.
- **"Swap only the rows the BE needs"** (O2) is worthless: the BE needs 2192 of 2200 rows.

### 6.6 Ranking

| Rank | Option | Saved / frame | Cost | Why |
| --- | --- | --- | --- | --- |
| 1 (do first) | E1 ablation: skip the swap in a test build | 33.8 MB (test only) | trivial build | Says whether the swap's traffic matters at all (PROBABLE value) |
| 2 | O1 stats fused into the swap | 4.2 MB (16.9 at step 1) | small | Cheapest to build, no behaviour change, restores full stats. Too small to fix 30 fps alone (PROBABLE) |
| 3 | O5 BE every 2nd frame + Core-side swap | 47.8 MB | medium | Best saving per unit of work if a 15 fps monitor while recording is acceptable (Patrik's call) |
| 4 | O4 half-resolution BE input | 59.5 MB (67.9 decimated) | large | Biggest saving that keeps a 30 fps monitor; also shrinks the BE itself |
| 5 | O3 swap-as-copy | 37.4 MB | large, tied to Q5 | Only together with Q5 |
| - | DT 0x2E, a sensor swap register, a BE/FE byte-order flag | 0 | n/a | Not available (§1-§4) |

## Experiments this suggests

Patrik runs anything needing sudo, restarts or `/boot/firmware`; builds run on the Pi. Use 30 fps, 3840x2160 Clear HDR 16-bit,
uncompressed, manual ISO/shutter/WB as in C0089-C0100, 3 takes x 10 s with `working/tools/takes.sh 3 10`. With 3 takes per
setting, only differences beyond the observed spread (7-20 missing for L1, 14-31 for L2) count.

**E0. Confirm the receiver programming on the Pi (read-only, sudo, no build).**
- Change: none. While Core streams 16-bit Clear HDR, Patrik runs
  `sudo sh -c 'for f in /sys/kernel/debug/rp1-cfe:*/csi2_regs; do echo $f; grep CSI2_CH_CTRL $f; done'`.
- For each nonzero `CSI2_CH_CTRL(n)` value v, decode `DT = (v >> 7) & 0x3f` and `mode = (v >> 1) & 3`.
- Prediction: one channel with mode 3 (FE streaming) and DT 0. That confirms the Pi's 6.12.75 kernel carries `fda4b68`/`274049e`
  and that the sensor gives no frame descriptor.
- Ruled out if: DT = 0x2E. Then the Pi kernel predates the workaround, and §1.2's account of this Pi is wrong.

**E1. Ablation: how much does the swap's traffic cost? (needs a test build).**
- Change: a libcamera-apertar build with a test-only env var `QBC_SKIP_SWAP16=1`. It skips the `do16BitEndianSwap` calls at
  `pisp.cpp:2219-2220` and `:817-818`. Do not clear the flag at `:1744-1746`, because the stats producer is keyed on it
  (`:1812-1816`). Run with `QBC_RAW_CPU_WORKER=1` (L2), so the pipeline thread is idle either way and only memory traffic changes.
- Accepted side effects: the preview is garbage, the stats are garbage (exposure is manual), and the DNGs are byte-swapped. The BE
  moves the same bytes on garbage content (PROBABLE).
- Measurement:
  - `takes.sh 3 10`: missing frames and delivered fps.
  - One `LIBCAMERA_LOG_LEVELS=RPI:0` window through `libcam_stages.py`: BE start->done and the BE start interval. Include the
    hardware BE-done `timestamp:` of "Stream ISP Input buffer complete" (README 22:20 lead).
  - `hwcount.py <pid> <worker tid> 10` on the raw-CPU worker thread. The worker is the busiest unnamed thread in
    `ps -L -o tid,comm,pcpu -p $(pidof apertar-core)`.
- Prediction, if memory contention from the CPU passes limits 30 fps: missing per take falls from 14-31 (L2) to <= 5, delivery
  rises to >= 29.5 fps, and BE start->done falls by >= 3 ms. Worker `l3d_refill` per frame falls from about 330 k to about 66 k
  (21.1 MB to 4.2 MB at 64 B per line).
- Ruled out if: missing per take stays >= 14 and delivery <= 28.2 fps. Then the swap's 1.01 GB/s is not the binding cost. O3/O4/O5
  are not worth building for the swap's sake (O4 might still pay off for its BE reduction; compare with Q1's TDN-off).

**E2. O1 fused stats (needs a build).**
- Change: in `RawCpuWorker::process` (`pisp.cpp:814-831@6b0b49f`), swap in bands of 64 rows and run the stats on each band right
  after swapping it, with a split `RawStatsProducer::process`. Keep `QBC_RAW_STATS_ROW_STEP=4`, then repeat at 1.
- Measurement: `hwcount.py` on the worker tid while recording, `l3d_refill` divided by delivered frames per second; worker busy
  share from `ps -L`; `takes.sh 3 10`.
- Prediction: refills per frame fall from about 330 k ((16.9 + 4.2) MB / 64 B) to about 264 k (16.9 MB / 64 B), -20 %. Worker
  time per frame falls by about 1-2 ms. Row step 1 then costs no more refills than step 4. Missing frames: no change beyond the take
  spread (PROBABLE; the saving is 127 MB/s).
- Ruled out if: refills per frame fall by < 30 k. Then the stats rows were already cache-resident and O1 saves only compute.

**E3. Upper bound for "give the BE less" before writing O4/O5 (no libcamera build beyond E1's).**
- Change: E1's build plus Q1's TDN-off tuning file (a copy of `imx585.json` without the `tdn` blocks, loaded through the existing
  drop-in; Patrik edits the drop-in).
- Measurement: as E1.
- Prediction: this removes 33.8 + 37.6 = 71.4 MB/frame, more than O4 (59.5) and O5 (47.8). If this combination is not clean
  (0-2 missing per take, >= 29.9 fps), neither O4 nor O5 will be.
- Ruled out if: E3 is clean but E1 alone is not. Then the BE side is the lever and Q1's TDN-off is the cheaper first step. If E1
  alone is clean, then O5/O3 (or a cheaper swap) suffice.

**E4. O5 prototype (only if E1 or E3 is positive; needs a libcamera and a Core build).**
- Change: libcamera runs the swap and the BE only on even CFE sequence numbers while a "recording" control is set. Odd frames
  complete without an ISP output and carry a "not swapped" metadata flag. Core's `copyRawBytes` does `rev16` for flagged frames.
- Measurement: `takes.sh 3 10`. Byte-order check as in L2: median raw of a flagged-frame DNG against an unflagged neighbour in the
  same static scene, which must agree within ~1 % (cf. 3643 vs 3625, `hardware-log.md:223`).
- Prediction: 0-3 missing per take at 30 fps; preview at 15 fps while recording.
- Ruled out if: missing >= 7 per take. Then halving the BE + swap load is not enough, and the limit is elsewhere (CFE write, NVMe,
  Core's copy).

**E5. `MM` DNG reader acceptance (desk, on the Mac, no Pi).**
- Change: convert 24 consecutive DNGs of an existing take (for example C0095) to big-endian with a small script. The script
  rewrites the header `MM\0*`, every IFD entry in big-endian per type, and byte-swaps the 16-bit strip data.
- Measurement: open the folder in DaVinci Resolve as a CinemaDNG clip, and single frames in Adobe Camera Raw / Lightroom and
  darktable or RawTherapee. Compare with the `II` originals (identical render, same pixel median).
- Prediction: ACR/Lightroom and the LibRaw-based tools render identically (both readers swap 16-bit samples, §6.3). Resolve
  unknown.
- Ruled out if: Resolve rejects the files or shows noise. Then `MM` is unusable for Patrik's workflow, the O4+Q5 row is closed,
  and the DNG must be swapped in a Core-side copy (O4/O5 as written).

## Unknowns

- The MIPI CSI-2 RAW16 byte figure (members-only specification). The high-byte-first conclusion is derived (§1.1).
- The RP1 CSI-2 register map: no public documentation. Whether bit 31 or other undocumented `CH_CTRL` bits do anything. Raspberry
  Pi's statement makes a swap bit very unlikely.
- What the "16-bit mismatch" is at hardware level, and whether a sensor that labels RAW16 with another DT could use the remap
  path. This is speculation from naushir's and njhollinghurst's 2025-06-26 comments.
- The IMX585 register map (Sony NDA): any data-type or byte-order register.
- The Pi's kernel: whether 6.12.75+rpt carries `fda4b68` and `274049e` (E0 settles it).
- Resolve's support for `MM` CinemaDNG (E5).
- Core `d9f00d4`: the exact T25 copy (whole buffer or active area; done here with `memcpy`?), whether the encoder still row-copies
  into a scratch chunk, and which dma-heap Core allocates from. Only f60e301 was available.
- How strongly the BE slows per GB/s of competing traffic (E1/E3), and the Pi 5's usable DRAM bandwidth under this mix (Q3).
- Whether the Pi's libpisp is v1.3.0 (Q1 X0). It does not affect this report: no libpisp version adds a byte-order flag that I
  know of, but that is UNCONFIRMED.
- The cost of the per-pass `DMA_BUF_IOCTL_SYNC` cache maintenance over 16.9 MB (`cma_heap.c:121-135@5bd564a` syncs each mapped
  attachment). Fusing passes removes sync pairs as well as bytes. The size of that win is UNCONFIRMED (needs `perf` with kernel
  symbols on the Pi).

## Web sources used

- https://github.com/raspberrypi/libcamera/issues/99: "Handling of 16-bit bayer Endianness" (schoolpost, 2023-12-22; IMX585).
  Statements by njhollinghurst (2024-02-29, 2025-06-26), naushir (2024-02-29, 2025-06-26) and 6by9 (2023-12-22), quoted above.
- https://github.com/raspberrypi/linux/commits/rpi-6.12.y/drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h and `.../cfe.c`:
  history; `fda4b68` (2025-07-04), `274049e` (2025-06-27), `3e4bd95` and `6ed0306` (2025-03-25).
- https://github.com/raspberrypi/linux/commit/fda4b68 and https://github.com/raspberrypi/linux/commit/274049e: messages and diffs.
- https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/media/raspberrypi,rp1-cfe.yaml: "The PHY
  and CSI-2 receiver part have no public documentation."
- https://raw.githubusercontent.com/emmcb/adobe-dng-sdk/master/dng_sdk/source/dng_read_image.cpp: DNG SDK 1.7.0.0 mirror,
  `ReadUncompressed` 16-bit swap.
- https://raw.githubusercontent.com/LibRaw/LibRaw/master/src/decoders/dng.cpp and `.../src/utils/read_utils.cpp`: `read_shorts`
  swap.
- Search excerpt only (host blocked): Adobe DNG 1.6.0.0 specification, https://paulbourke.net/dataformats/dng/dng_spec_1_6_0_0.pdf.

## Verification

Verifier: adversarial check of Q4 (Claude Opus 5.5), 2026-10-26. I opened every cited line in the trees named in the header, at the
cited commits (working trees confirmed at `6b0b49f`, `7e9fef0`, `bfe0b76`, `v1.3.0`/`9ba67e6`, `5bd564a`, `98b9862`, `18c1eb2`,
`d6cc93e`, `c99ff77`, `63a08d5`; Core via `git show f60e301:<path>`), and re-fetched the web pages with WebFetch. Verdicts:
CONFIRMED (holds as labelled), CORRECTED (holds, but a cite or detail is wrong; right one given), REFUTED (evidence against),
UNVERIFIABLE (needs the Pi or a page not reachable here). All arithmetic was redone; 1 MB = 10^6 B.

| # | Claim (section) | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | RAW16 = DT 0x2E, "isn't defined in CSI2 v1.3" (6by9, 2023-12-22); kernel constant used at cfe_fmts.h:286 (§1.1) | CONFIRMED | https://github.com/raspberrypi/libcamera/issues/99 (quote present); `kernel-rpi/include/media/mipi-csi2.h:43@5bd564a` (`0x2e`); `cfe_fmts.h:286@5bd564a` |
| 2 | Wire sends bits 15:8 first, derived (§1.1) | CONFIRMED (stays PROBABLE) | Premises open as cited: `pixfmt-srggb16.rst:25`, `pixfmt-srggb10p.rst:24-26@5bd564a`, `apertar-kb/lessons/hardware-log.md:223`. No public spec text found here either |
| 3 | Bayer16 entries `.csi_dt = 0` with the RP1 comment; Y16 keeps `MIPI_CSI2_DT_RAW16` (§1.2) | CONFIRMED | `kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h:200,208,216,224` (entries 196-227), Y16 `:283-289`, `csi_dt` `:286@5bd564a` |
| 4 | `fda4b68` title/body, naushir, 2025-07-04, RAW16 -> 0 in 4 entries (§1.2) | CONFIRMED | https://github.com/raspberrypi/linux/commit/fda4b68 (body quoted exactly; diff: cfe.c WARN_ON change + 4 csi_dt lines); date from https://github.com/raspberrypi/linux/commits/rpi-6.12.y/drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h |
| 5 | `274049e` (2025-06-27) adds `fmt->depth != 16 &&` to the REMAP condition (§1.2) | CONFIRMED | https://github.com/raspberrypi/linux/commit/274049e; date on the cfe.c history page; `rp1_cfe/cfe.c:890-894@5bd564a` (comment :890, condition :891, REMAP :894; the cited :889-893 is one line early) |
| 6 | njhollinghurst 2025-06-26 and 2024-02-29 quotes (§1.2) | CONFIRMED | issue #99 via WebFetch: all five quoted fragments present, plus "(meanwhile for `MIPI_CSI2_DT_RAW14` it simply doesn't work)" |
| 7 | DT comes from `get_frame_desc`, else `cfe_fmt->csi_dt`; written to CH_CTRL bits 12:7 (§1.2) | CONFIRMED | `rp1_cfe/csi2.c:326-349` (`*dt = cfe_fmt->csi_dt` :346), `:366-370` (`-ENOIOCTLCMD` -> fallback), `:429-431`, `DT_MASK` :102 `@5bd564a` |
| 8 | IMX585 drivers implement no `get_frame_desc` (§1.2) | CONFIRMED | `imx585-apertar/imx585.c:2458-2466@98b9862`; grep `frame_desc` empty in `imx585-v4l2-driver/imx585.c@18c1eb2` |
| 9 | Raw path CSI-2 -> FE (`CSI2_MODE_FE_STREAMING`) -> `fe_image0`; FE link and node at `pisp.cpp:1366,2686-2697` (§1.2) | CORRECTED | Path holds: `cfe.c:839-872`, `:868`, `:858@5bd564a`; `pisp.cpp:2686-2697@6b0b49f`. But `fe_image0` is `pisp.cpp:1364`; `:1366` is `rp1-cfe-fe_stats` |
| 10 | CH_CTRL fields as listed, modes NORMAL/REMAP/COMPRESSED/FE_STREAMING, no swap bit; receiver undocumented (§1.2) | CONFIRMED | `csi2.c:89-103`, `csi2.h:22-27@5bd564a`; https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/media/raspberrypi,rp1-cfe.yaml ("The PHY and CSI-2 receiver part have no public documentation.") |
| 11 | DT 0 lets the 20 OB rows through; buffer 2200 rows (drivers' own explanation) (§1.2) | CONFIRMED | `imx585-apertar/imx585.c:547-554,785-789@98b9862`; `cinemate/scripts/rp1-cfe-y16-csi-dt0.patch@d6cc93e` (note quoted correctly) |
| 12 | IPA comment: CFE->FE input big-endian, FE blocks assume LE (§1.2) | CONFIRMED | `libcamera-apertar/src/ipa/rpi/pisp/pisp.cpp:699-706@6b0b49f` |
| 13 | `Needs16bitEndianSwap` doc text; added in `332b04ce` (Naushir, 2025-01-13) (§1.3) | CONFIRMED | `rpi_stream.h:85-89@6b0b49f`; `git show 332b04ce` (author date Mon Jan 13 2025, body as quoted) |
| 14 | Flag set whenever sensor bus is 16 bpp, warning text, no switch; Cinemate's COMP1 exemption (§1.3) | CONFIRMED | `pisp.cpp:1744-1750@6b0b49f`; `libcamera/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1455-1459@bfe0b76`; `git log -1 bcdd7e1` |
| 15 | Core's raw buffer is the CFE buffer and the BE input (§1.3) | CONFIRMED | `pisp.cpp:1735-1736` (External), `:2750-2757` (`isp_[Isp::Input].queueBuffer(cfe_[Cfe::Output0] buffer)`) `@6b0b49f` |
| 16 | `do16BitEndianSwap`: per row (w+7)/8 x 16 B, in place, aarch64 only; 480 x 16 = 7,680 B; 480 x 2200 = 1,056,000 iterations; r F + w F (§1.3) | CONFIRMED | `pisp.cpp:397-417@6b0b49f`; arithmetic redone |
| 17 | Where it runs: dequeue `:2205-2224`; `submitRawCpuJob` `:2114-2150`, `swap16` `:2129`; worker `:814-831`, swap `:817-818`, stats `:820-829`; sync helpers `:320-339` (§1.3) | CORRECTED (line nits) | `pisp.cpp@6b0b49f`: `submitRawCpuJob` is `:2115-2148`; `process()` `:814-834`; stats block `:822-832`; helpers `:320-343`. `:2129`, `:817-818`, `:2205-2224` exact |
| 18 | SW stats load `vld1q_u16` on the swapped buffer; row step 4 reads 1100/4 = 275 pairs = 550 rows x 7,680 = 4,224,000 B (§1.3) | CONFIRMED | `raw_stats.cpp:32-43` (env var), `:205-303` (loop), `:233-234` (loads) `@6b0b49f`; each pair loop covers 480 x 16 B = the whole row; arithmetic redone |
| 19 | Swap 6.1 / 9.9 ms -> 33.79 MB / 6.1 ms = 5.5 GB/s, / 9.9 ms = 3.4 GB/s; 33.79 x 30 = 1.01 GB/s (§1.3) | CORRECTED (detail) | Figures `hardware-log.md:188`, handoff:52; arithmetic holds (5.54, 3.41, 1.014). But the logged stage is the whole "CFE image dequeue handler", which also runs two `DMA_BUF_IOCTL_SYNC` calls (`pisp.cpp:2218,2223@6b0b49f`) that do cache maintenance per mapped attachment (`cma_heap.c:132-136,153-157`, `system_heap.c:159-173@5bd564a`). So the loop's rate is at least 5.5 GB/s, not equal to it |
| 20 | PMU: 0.57 M L3 refills/frame vs 33.792e6 / 64 = 528,000 lines (§1.3) | CONFIRMED (stays PROBABLE) | `hardware-log.md:161-162`; arithmetic redone; `working/tools/hwcount.py:14` (`l3d_refill` = 0x2a, user space only) |
| 21 | 16-bit Clear HDR mode: `common_clearHDR_mode` + `mode_4k_regs_16bit`; at stream start CCMP_EN = 0, MDBIT 0x03 (§2) | CONFIRMED | `imx585-apertar/imx585.c:484-519`, `:747-753`, `:2252-2261@98b9862` |
| 22 | Neither driver writes a byte-order/DT/MIPI-format register (§2) | CONFIRMED | grep `-i "endian\|swap\|frame_desc\|datatype"` on both `imx585.c`: no register hits; register block `imx585.c:51-188@98b9862` (lane mode `:106` is the only MIPI-side define) |
| 23 | Sensor register unknown; naushir's "endian swap in the sensor itself?" unanswered (§2) | CONFIRMED | issue #99: no answer visible (14 collapsed items not loadable, so "none recorded" is as far as it goes) |
| 24 | Another DT label would not help (§2) | CONFIRMED (stays PROBABLE) | Consistent with njhollinghurst: "RAW14 cannot be remapped to 16 bits", RAW14 "simply doesn't work" (issue #99) |
| 25 | 12-bit CCMP sets no swap; WDR detection; unpacked u16 forced (§2) | CONFIRMED | `pisp.cpp:1745`, `:1785-1798`, `:1853-1874@6b0b49f` |
| 26 | FE input config has no byte-order field (§3) | CONFIRMED | `libpisp/src/libpisp/frontend/pisp_fe_config.h:84-92@v1.3.0` |
| 27 | FE input forced to `BPS_16`, streaming; 14-bit bodge (§3) | CONFIRMED | `pisp.cpp:2391-2449` (`configureCfe`), `:2409-2415@6b0b49f` |
| 28 | Decompand is a 65-entry LUT; a byte swap "has 256 discontinuities" (§3) | CORRECTED (detail) | `pisp_fe_config.h:107-112@v1.3.0`. swap(x) drops at x = 256k for k = 1..255: **255** discontinuities in 0..65535. Conclusion (not a 64-segment PWL) holds |
| 29 | No FE output-1 downscaled Bayer at RAW16 (§3) | CONFIRMED | njhollinghurst (FE stats/compression unavailable); `ipa pisp.cpp:703-704@6b0b49f` lists Downscale among blocks to no-op |
| 30 | Restoring 0x2E breaks data; Cinemate Y16 motif; fixed after csi_dt=0 patch plus other changes (§3) | CONFIRMED | `cinemate-handbook/lessons/hardware-log.md:834-842`, `:865-885@c99ff77` (fix stack at :867-871 includes driver and app branches, so "DT 0 alone cured it" stays PROBABLE) |
| 31 | OB rows: 20 x 7,680 = 153,600 B = 0.9 % of a pass (§3) | CONFIRMED | 153,600 / 16,896,000 = 0.909 % |
| 32 | "16-bit mismatch" unknown at register level; naushir RAW14 question and footnote (§3) | CONFIRMED | issue #99 quotes present |
| 33 | `pisp_image_format` has no byte-order flag (§4) | CONFIRMED | `libpisp/src/libpisp/common/pisp_common.h:39-95@v1.3.0` |
| 34 | `ORDER_SWAPPED` is component order (§4) | CONFIRMED | `pisp_utils.cpp:230-241@v1.3.0` (NV21, UYVY, NV61) |
| 35 | BE input format `BPS_16 + UNCOMPRESSED` (§4) | CONFIRMED | `pisp.cpp:166-169@6b0b49f` (`:2510-2517` is only the decompress branch for compressed input) |
| 36 | BE driver's 16-bit Bayer = `S*16`, LE per V4L2 (§4) | CONFIRMED | `pisp_be/pisp_be_formats.h:335-375@5bd564a`; `pixfmt-srggb16.rst:25` |
| 37 | naushir: no HW endian swap in the ISP; "we only deal with little endian for 16-bits" (§4) | CONFIRMED | issue #99, 2024-02-29 |
| 38 | No BE block can undo the swap (§4) | CONFIRMED (stays PROBABLE) | `pisp_be_config.h:34-58@v1.3.0`; enum bit order is not proof of pipeline order, so PROBABLE is the right label |
| 39 | BE reads rows 4..2195 = 2192 rows (§5) | CONFIRMED | `q1-backend.md:105,112` |
| 40 | Stats could read BE data with one `vrev16q_u8` per load (§5) | CONFIRMED (change PROBABLE) | `raw_stats.cpp:233-234@6b0b49f` |
| 41 | IPA has no raw access, reads the stats buffer (§5) | CONFIRMED | stats buffer = `cfe_[Cfe::Stats]`: `pisp.cpp:2133-2140`, `:3072-3106@6b0b49f` |
| 42 | CFE HW stats wrong at 16-bit and overwritten by SW stats (§5) | CONFIRMED | `pisp.cpp:1800-1819`, `raw_stats.cpp:305-309@6b0b49f` (memset + overwrite) |
| 43 | Core reads the raw buffer only via `copyRawBytes` (memcpy of active area), then the encoder's per-row memcpy into a 491,520 B scratch (§5) | CONFIRMED | `apertar-core` `git show f60e301:src/camera/CameraController.cpp` :6779-6786, :7269, :7446; only two `mappedRawBuffers_` lookups (:7218, :7389); `src/cdng/CdngEncoder.cpp:1044-1045`, `:1868-1872` (max(7680, min(4 MiB, max(256 KiB, 7680 x 64))) = 491,520), `:1887-1897@f60e301` |
| 44 | Today: 33.79 + 4.22 + 57.6 + 33.18 = 128.79 MB/frame (§6) | CONFIRMED | 2 x 16,896,000 = 33.792; 4.224; 57.6 (`q1-backend.md:26`); 2 x 16,588,800 = 33.178; sum 128.794 |
| 45 | O1 saves 4.22 MB (16.9 at step 1), 124.57, 127 MB/s (§6) | CONFIRMED | 128.79 - 4.22 = 124.57; 4.224 x 30 = 126.7 MB/s |
| 46 | O2 saves 8 x 7,680 x 2 = 122,880 B, 3.7 MB/s (§6) | CONFIRMED | 0.12288 x 30 = 3.69 MB/s |
| 47 | O3 saves 37.40, 1.12 GB/s (§6) | CONFIRMED (arithmetic) | 33.79 + 57.6 = 91.39; 128.79 - 91.39 = 37.40; x 30 = 1.122. Memory cost of the internal pool not costed (see Missed) |
| 48 | O5: per pair 33.79 + 4.22 + 57.6 + 66.36 = 161.97 -> 80.99/frame, saves 47.80, 1.43 GB/s (§6) | CONFIRMED | redone: 161.97 / 2 = 80.985; 128.79 - 80.99 = 47.80; x 30 = 1.434 |
| 49 | O4: 16.90 + 4.22 = 21.12; + 15.0 + 33.18 = 69.30; saves 59.49, 1.78 GB/s (§6) | CONFIRMED | 1920 x 1100 x 2 = 4,224,000; Q1 case E 15.005 (`q1-backend.md:203,285,341`) |
| 50 | O4d: 550 x 2 x 7,680 = 8.45; 12.67; 60.85; saves 67.94, 2.04 GB/s (§6) | CONFIRMED | redone |
| 51 | O6 (`MM` alone) saves 0 (§6) | CONFIRMED | nothing in the four columns changes |
| 52 | O4+Q5 needs an **`MM`** DNG to reach 36.12 MB / 92.67 saved (§6 table; §6.3 "the file must be `MM`") | **REFUTED** | Core's encoder copies every DNG row into a 491,520 B scratch before `write()` (`CdngEncoder.cpp:1044-1045,1887-1897@f60e301`). That copy survives "no T25 copy", can `rev16` at the same byte count (the report's own §6.2), and its writes stay in the 512 KB L2. Dropping it to write straight from the camera buffer saves no DRAM bytes: `copy_from_user` then reads the camera buffer instead of the scratch. So 36.12 / 92.67 is reachable with an `II` DNG. `MM` only matters on a path where no CPU touches the payload (O_DIRECT; see #60 and Missed) |
| 53 | L2 runs stats right after the whole-frame swap; Pi 5 L2 512 KB/core, L3 2 MB (§6.1) | CONFIRMED (cache sizes stay PROBABLE) | `pisp.cpp:814-834@6b0b49f`; product-brief text reproduced in https://docs.zephyrproject.org/latest/boards/raspberrypi/rpi_5/doc/index.html (search excerpt; raspberrypi.com not opened) |
| 54 | Band of 64 rows = 491,520 B fits L2; 32 row pairs, divisible by step 4 (§6.1) | CONFIRMED | arithmetic |
| 55 | Fused stats can return to row step 1 at no DRAM cost; stats ~5.8 ms compute (§6.1) | CONFIRMED (stays PROBABLE) | handoff:52; 16.9 MB / 5.8 ms = 2.9 GB/s, below the swap's >= 5.5 GB/s, so the stats are compute-bound, as claimed |
| 56 | DNG spec: readers must support both byte orders (§6.3) | UNVERIFIABLE | Spec hosts blocked here too (helpx.adobe.com DNS); search did not return the sentence. PRONOM lists big- and little-endian DNG signatures (https://pronom.nationalarchives.gov.uk/fmt/438). PROBABLE stands |
| 57 | DNG SDK `ReadUncompressed` 16-bit: `if (stream.SwapBytes ()) DoSwapBytes16 (...)`; mirror is SDK 1.7.0.0 (§6.3) | CONFIRMED | https://raw.githubusercontent.com/emmcb/adobe-dng-sdk/master/dng_sdk/source/dng_read_image.cpp; https://github.com/emmcb/adobe-dng-sdk README ("mirror to the Adobe DNG SDK version 1.7.0.0") |
| 58 | LibRaw `packed_dng_load_raw` -> `read_shorts` swaps on order mismatch; "LibRaw (darktable, RawTherapee and many others)" (§6.3) | CORRECTED | Code CONFIRMED (https://raw.githubusercontent.com/LibRaw/LibRaw/master/src/decoders/dng.cpp, `.../src/utils/read_utils.cpp`; condition true exactly when file and host order differ). Attribution wrong: darktable reads raw with RawSpeed, RawTherapee with its own dcraw-derived decoder (pixls.us threads and darktable 4.4 manual via search excerpts; docs.darktable.org DNS-blocked, so PROBABLE). E5 should test each of them, not count them as LibRaw |
| 59 | Core writes `II`, IFD values host-order; cinepi-raw `"II"` (§6.3) | CONFIRMED | `CdngEncoder.cpp:1740-1744` (header), `:1732-1735` (`putLe16/putLe32`), `IfdBuilder.hpp:36@f60e301`; `cinepi-raw/cinepi/dng_encoder.cpp:1138@63a08d5` |
| 60 | O_DIRECT from the mapped camera buffer fails (dma-heap mmap = `VM_IO|VM_PFNMAP`, GUP `-EFAULT`); which heap Core uses is UNCONFIRMED; system heap gives the same flags (PROBABLE) (§6.3, Short answer 4) | CORRECTED | Flags and GUP CONFIRMED: `cma_heap.c:185`, `mm/gup.c:1277-1278@5bd564a`; system heap CONFIRMED too: `system_heap.c:212` (`remap_pfn_range`) -> `mm/memory.c:2672` (`VM_IO | VM_PFNMAP`) `@5bd564a`. Heap is visible at f60e301: Clear HDR raw uses `/dev/dma_heap/vidbuf_cached`, else `linux,cma` (`CameraController.cpp:6652-6658,6736`), default on. Default CMA is 64 MB (`bcm2712.dtsi:182@5bd564a`) < 8 x 16.9 = 135 MB, so PROBABLY the system heap. But "the no-copy route cannot use O_DIRECT" holds only for dma-heap buffers: see Missed 1 (udmabuf) |
| 61 | O3: swap-as-copy, CFE buffer back ~10 ms after dequeue, routing at `pisp.cpp:1734-1737` (§6.4) | CONFIRMED (stays PROBABLE) | `pisp.cpp:1735-1736@6b0b49f` |
| 62 | O4/O5 need libcamera patches; "Running the BE every Nth frame ... needs libcamera patches" (§6.5) | CONFIRMED | `q1-backend.md:38-40,199,203` |
| 63 | O2 worthless: BE needs 2192 of 2200 rows (§6.5) | CONFIRMED | #39 |
| 64 | E0 command, decode `DT = (v >> 7) & 0x3f`, `mode = (v >> 1) & 3`, FE streaming = 3 | CONFIRMED | debugfs dir `rp1-cfe:<dev>` (`cfe.c:2337-2339`), file `csi2_regs` (`csi2.c:579`), line format `CSI2_CH_CTRL(n)` (`csi2.c:141,154`), masks `csi2.c:100,102` (`CH_MODE_MASK` 2:1, `DT_MASK` 12:7), `csi2.h:26@5bd564a` |
| 65 | E1 skip points `:2219-2220`, `:817-818`; keep flag `:1744-1746` because stats keyed at `:1812-1816`; worker refills 330 k -> 66 k | CONFIRMED | `pisp.cpp@6b0b49f` (keying at `:1813-1815`); 21.12e6 / 64 = 330,000, 4.224e6 / 64 = 66,000. Nuance: in L2 the IPA waits for the worker (`cfeJobReady`, `pisp.cpp:1105-1111,3116`), so the ablation also shortens a serial wait; "only memory traffic changes" is not strictly true |
| 66 | E2: 330 k -> 264 k refills (-20 %) | CONFIRMED | 16.896e6 / 64 = 264,000; 66 / 330 = 20 % |
| 67 | E3 removes 33.8 + 37.6 = 71.4 MB > O4 59.5, O5 47.8; "If this combination is not clean, neither O4 nor O5 will be" | **REFUTED** (inference; arithmetic CONFIRMED) | E3 tests bytes only. It still runs the BE once per frame on 3840 x 2192 px. O5 halves the BE runs (66.7 ms budget per run). O4 feeds the BE 1920 x 1100 = 2.11 Mpx instead of 8.42 Mpx (4x fewer) and lets the raw buffer complete before the BE. If BE time per run or the serial IPA+BE cycle binds (the brief's 36.2 ms start interval), E3 can fail while O4/O5 succeed. PROBABLE |
| 68 | E4: flagged vs unflagged median agree within ~1 % (cf. 3643 vs 3625) | CONFIRMED | `hardware-log.md:223`; (3643 - 3625) / 3625 = 0.50 % |
| 69 | Unknown: whether 6.12.75+rpt carries `fda4b68`/`274049e` | CORRECTED -> PROBABLE yes | Upstream 6.12.75 was announced 2026-03-04 (https://lwn.net/Articles/1061212/), eight months after `fda4b68` (2025-07-04) on rpi-6.12.y. This Pi's driver already sees the OB rows that DT 0 lets through (`imx585-apertar/imx585.c:547-551,785-789`). Settles with `uname -v` plus E0; E0 is confirmatory only |
| 70 | Pi's libpisp version does not matter for Q4 | UNVERIFIABLE | Needs `pkg-config --modversion libpisp` on the Pi; no newer libpisp opened here |
| 71 | Resolve and `MM` CinemaDNG | UNVERIFIABLE | Closed source; desk test E5 |
| 72 | Short answer 1: no switch removes the swap for 16-bit uncompressed | CONFIRMED | #3-#10, #22, #26, #33-#37. Only swap-free 16-bit path: lossy COMP1 (Missed 2) |

**Counts:** 72 claims checked: **60 CONFIRMED**, **7 CORRECTED** (#9, #17, #19, #28, #58, #60, #69), **2 REFUTED** (#52, #67), **3
UNVERIFIABLE** (#56, #70, #71). Every arithmetic step in §1.3, §3, §6 and the experiments reproduces.

### Corrections that change substance

1. **`MM` is not needed for O4+Q5 (#52).** Core's encoder already copies each row into a 491,520 B scratch
   (`CdngEncoder.cpp:1044-1045,1887-1897@f60e301`). That copy can do `rev16` at the same DRAM cost, so the 92.67 MB/frame saving holds
   with an `II` DNG. E5 (Resolve with `MM`) leaves the critical path. It matters only on a path where no CPU touches the payload
   (Missed 1).
2. **E3 is not an upper bound for O4/O5 (#67).** It removes bytes but keeps one full-resolution BE run per frame. O5 halves the runs,
   and O4 quarters the BE's pixels and frees the raw buffer early. "E3 not clean -> neither O4 nor O5" is wrong whenever BE time per run
   or the serial IPA+BE cycle binds, which is the brief's leading hypothesis. Read a failed E3 as "bandwidth alone is not the lever",
   not as "O4/O5 are dead". O5 stays a live candidate after a failed E3 or a failed E1.
3. **The O_DIRECT conclusion depends on the allocator (#60).** It is right for both dma-heaps (cma and system are both `VM_PFNMAP`,
   now CONFIRMED), and Core's heap is visible at f60e301 (`vidbuf_cached`, else `linux,cma`). It is not a property of a no-copy path
   in general (Missed 1).
4. **Minor, ranking-neutral:** the swap stage time includes two dma-buf syncs, so 5.5 GB/s is a lower bound (#19). The Pi kernel
   almost certainly has the workaround (#69), so E0 is confirmatory. darktable and RawTherapee are not LibRaw (#58).

### Missed

1. **udmabuf + O_DIRECT, a true zero-copy DNG path (PROBABLE).** `CONFIG_UDMABUF=y` (`arch/arm64/configs/bcm2712_defconfig:1496@5bd564a`).
   The CFE and the BE sit behind IOMMUs (`bcm2712-rpi-5-b.dts:244-250`, `bcm2712-ds.dtsi:387-393@5bd564a`), so memfd pages need not be
   contiguous. Core already hands libcamera its own dma-buf fds (`CameraController.cpp:6729-6760@f60e301`). Core could write the payload
   with O_DIRECT through the memfd's ordinary shmem mapping, where GUP works; the `VM_PFNMAP` check applies only to the dma-buf mmap
   (`udmabuf.c:71`). exFAT supports direct I/O (`hardware-log.md`, 2026-10-26 exFAT entry). Alignment works out:
   A = 16,588,800 = 32,400 x 512, and the active offset is 20 x 7,680 = 153,600 = 300 x 512. Only the DNG strip offset needs padding to a
   block boundary.
   - Saving against today: the T25 copy (r A + w A), the encoder's re-read (r A) and the page-cache write (w A), so 4 x 16.59 =
     **66.4 MB/frame (1.99 GB/s)**. That is larger than any row in §6 except O4/O4d/O4+Q5, and it does not touch the BE.
   - This is the one path where the DNG byte order really matters: keep libcamera's in-place swap (`II`), or use `MM` with O4.
   - Costs: Core holds the camera buffer until the NVMe write completes (Q5's CFE-starvation risk), and udmabuf's dma-buf sync semantics
     need checking.
2. **COMP1 is the only swap-free 16-bit path, and the report never names it.** Cinemate's fork skips the swap for a PISP_COMP1 CFE
   output (`libcamera/.../pisp.cpp:1449-1459@bfe0b76`, `bcdd7e1`), and `cinepi-raw/core/rpicam_app.cpp:132@63a08d5` maps `16:P` to it.
   It is lossy (8 bpp, "16/32/64 quantisation steps" per `bcdd7e1`), closed in libcamera-qbc for WDR (`pisp.cpp:1846-1874@6b0b49f`), and
   at odds with njhollinghurst's "compression ... unavailable for RAW16". Out of scope for "16-bit uncompressed", but it belongs in §6 as
   a rejected option (`working/compare-raw/b2-libcamera-16bit.md` Q6 already lists it).
3. **O3's memory cost is not counted.** A second CFE pool of N x 16.9 MB (N = 4: 67.6 MB) comes on top of Core's 8 x 16.9 = 135 MB raw
   buffers, 2 TDN buffers and the preview buffers, on a 4 GB Pi whose default CMA is 64 MB (`bcm2712.dtsi:182`). It works only through
   the IOMMU-backed system heap (PROBABLE).
4. **Read-only checks that settle the heap and kernel questions:** `ls -l /dev/dma_heap/`; `grep -i cma /proc/meminfo`;
   `journalctl -u apertar-core -b | grep -E "CPU-cached heap|cached DMA allocation unavailable"` (log lines at
   `CameraController.cpp:6752,6758@f60e301`; that d9f00d4 keeps them is UNCONFIRMED); `uname -v`; `pkg-config --modversion libpisp`.
