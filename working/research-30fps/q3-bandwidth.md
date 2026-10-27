# Q3: DRAM bandwidth budget, Clear HDR 16-bit 3840x2200 at 30 fps

Reader: Q3 bandwidth (research subagent, Claude Opus 5.5) · trees: libcamera-apertar `6b0b49f` (base libcamera-qbc `7e9fef0`),
libpisp `v1.3.0` (`9ba67e6`), kernel-rpi `rpi-6.12.y` `5bd564a` (sparse; widened here with `arch/arm64/include/asm`), apertar-core
`f60e301` only (`git show`), raspberrypi/rpi-eeprom `f54693e` (2026-10-26, `firmware-2712/release-notes.md` only), raspberrypi/documentation
`41e24fb` (2026-10-23, four `.adoc` files) · date 2026-10-26

Labels: **CONFIRMED** = I opened the line or page and it says so. **PROBABLE** = derived, reasoning shown. **UNCONFIRMED** = needs the Pi
or a page I could not open. The session's egress proxy refused forums.raspberrypi.com, jeffgeerling.com, openbenchmarking.org,
raw.githubusercontent.com and datasheets.raspberrypi.com, and WebFetch could not resolve hosts. Every public benchmark figure below
therefore comes from a search-engine summary and is **UNCONFIRMED**. The two Raspberry Pi repositories above came in through the git
proxy, so their text is CONFIRMED. MB = 10^6 B, GB/s = 10^9 B/s. F = 3840 x 2200 x 2 = **16,896,000 B** (readout buffer).
A = 3840 x 2160 x 2 = **16,588,800 B** (DNG payload).

## Short answer

1. **About 195.5 MB per frame = 5.87 GB/s at 30 fps** (PROBABLE, §3): **3.13 GB/s CPU-driven** (swap 33.8 MB, stats 4.2, Core copy
   33.2, page-cache copy 33.2) and **2.73 GB/s DMA-driven** (CFE 16.9, back end 57.6, NVMe 16.6). HDMI UI not included (UNCONFIRMED, 0.3-3 GB/s by mode).
2. That is **34 % of the 17.07 GB/s peak** (CONFIRMED: "up to 17 GB/s") and **49-58 % of reported single-core streaming** (10-12 GB/s r+w,
   UNCONFIRMED). The average does not saturate DRAM. But recording adds +74 % (3.38 -> 5.87 GB/s), and while the back end runs, the
   bursts ask for an estimated 15-20 GB/s (PROBABLE). That fits the measured IPC drop (1.87 -> 1.30) with no change in L3 misses.
3. vb2-exported buffers (TDN, preview, CFE internal) are **non-cacheable** for the CPU. Core's `vidbuf_cached` raw buffers are cacheable,
   and each sync walks the whole 16.9 MB **once per attachment** (2 attachments). That makes 8 walks per frame with L2 and 12 with L1:
   CPU time (≤0.5 ms each, PROBABLE), no extra bytes (CONFIRMED code).
4. **Ranked by bytes:** BE 57.6 (TDN 37.5 of it) > swap 33.8 ≈ Core copy 33.2 ≈ page-cache copy 33.2 > CFE 16.9 ≈ NVMe 16.6 > stats 4.2.
5. **Cheapest single pass to remove: TDN** (tuning-file copy, no build, DNGs unchanged): -37.5 MB/frame, -1.12 GB/s (-19 %). It sits
   inside the serial stage. Next: Core copy or page-cache copy (O_DIRECT, T24), -1.0 GB/s each, both code changes.
   Stats tweaks (≤2.1 MB) are bandwidth-irrelevant.
6. First on the Pi: NUMA/interleave state, HDMI mode, dma-buf inventory, sync cost (§7). Then the dose-response test X1.

## 1. Geometry, allocators and cacheability (what each pass touches)

| Fact | Value | Label, source |
| --- | --- | --- |
| CFE stride | `ALIGN(3840 x 16 / 8, 16)` = 7680 B; sizeimage = height x bpl | CONFIRMED, `kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:78,531-541@5bd564a` |
| libcamera stride | `compute_optimal_stride` aligns to 64 B (7680 already is) | CONFIRMED, `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:259-277@6b0b49f`, `libpisp/src/libpisp/common/pisp_utils.cpp:115-119@v1.3.0` |
| Raw buffer size handed to Core | `frameSize = cfeFormat.planes[0].size` = 7680 x 2200 = **16,896,000 B** | CONFIRMED, `pisp.cpp:1887-1898@6b0b49f`; the Pi logged `frame_bytes=16896000` (`apertar-kb/working/clearhdr-design.md:109`) |
| SW raw stats engaged, no CCMP unwrap at 16-bit | `rawStats_` for `Needs16bitEndianSwap`; `ccmpUnwrap_` only in 12-bit mode | CONFIRMED, `pisp.cpp:1810-1844@6b0b49f` |
| Core's raw buffers | `/dev/dma_heap/vidbuf_cached` first (system heap on Pi 5), `len = frameSize`, 8 of them (T23). Comment at the call: "too slow on the CFE's uncached buffers" | CONFIRMED, `apertar-core/src/camera/CameraController.cpp:6651-6661,6730-6760@f60e301`; journal `CPU-cached heap=... count=8` (KB T23 tutorial). That the symlink points to the system heap is PROBABLE (cinepi-raw comment, Q5) |
| CFE and BE behind IOMMUs | `&csi0`, `&csi1` -> `iommu5` ("HACK for RP1 masters over PCIe"); `pisp_be` -> `iommu2` | CONFIRMED, `kernel-rpi/arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts:244-250`, `bcm2712-ds.dtsi:301-308,386-394@5bd564a` |
| No BCM2712 device is DMA-coherent | no `dma-coherent` property in `bcm2712*.dts*`/`rp1.dtsi` | CONFIRMED (grep, no hit) |
| vb2-exported buffers (CFE internal raw x2, CFE stats/config, TDN x2, stitch x2, preview output) | allocated by `iommu_dma_alloc_remap` (scattered pages) and mmapped with `dma_pgprot` = `pgprot_dmacoherent` = **MT_NORMAL_NC** | CONFIRMED, `drivers/iommu/dma-iommu.c:1695-1708,1732-1740`, `kernel/dma/mapping.c:505-514`, `arch/arm64/include/asm/pgtable.h:694-696@5bd564a`; the CFE/BE queues never enable cache hints (`cfe.c:1944-1952`, `pisp_be.c:1449-1450`) |
| Sync on vb2 exports | `begin/end_cpu_access` return 0: no cache maintenance, nothing to maintain | CONFIRMED, `drivers/media/common/videobuf2/videobuf2-dma-contig.c:427-439,467-468@5bd564a` |
| Sync on system-heap buffers | one `dma_sync_sgtable_for_cpu/device` **per mapped attachment**; for the IOMMU devices that is `arch_sync_dma_*` per sg entry; `DMA_BIDIRECTIONAL` = clean+invalidate, for-CPU = invalidate | CONFIRMED, `drivers/dma-buf/heaps/system_heap.c:159-199`, `dma-iommu.c:1192-1221`, `arch/arm64/mm/dma-mapping.c:15-46@5bd564a` |
| Attachments of a raw buffer | CFE `Output0` and BE `Input` both import it; vb2 keeps the mapping while the same dma-buf returns to the same index, and libcamera imports with 32 slots | CONFIRMED, `videobuf2-core.c:1405-1483`, `libcamera-apertar/.../common/pipeline_base.cpp:958@6b0b49f`; that both attachments stay mapped is PROBABLE |
| CPU mapping of system-heap buffers | `remap_pfn_range` with the default (cacheable) prot; `VM_IO|VM_PFNMAP` | CONFIRMED, `system_heap.c:201-220`, `mm/memory.c:2672@5bd564a` |
| Caches | 512 kB L2 per core, 2 MB shared L3, 64 B lines | CONFIRMED, `bcm2712.dtsi:155-162@5bd564a`, `documentation/.../processors/bcm2712.adoc:5@41e24fb` |

Consequence (PROBABLE): every CPU pass over the raw data runs on cacheable memory and streams to and from DRAM, because 16.9 MB is
much larger than the 2.5 MB of L2 + L3 a core can use. The non-cacheable buffers are touched by the CPU only in small amounts (the
23 kB stats buffer and the web-preview downsample).

## 2. Pass by pass, bytes per frame (L2 build, T25 Core, 30 fps, uncompressed)

| # | Pass | Agent | Read MB | Write MB | Source and label |
| --- | --- | --- | --- | --- | --- |
| 1 | CFE writes the raw (+ 23 kB stats, embedded) | DMA, RP1 over PCIe x4 | ~0 | **16.92** | CONFIRMED size (§1). The stats size 23,200 B is from Q1's simulation |
| 2 | 16-bit endian swap, in place, `ld1/rev16/st1` 16 B per step, (3840+7)/8 steps x 16 B = 7680 B per row x 2200 rows | CPU (worker with L2) | **16.90** | **16.90** | CONFIRMED loop, `pisp.cpp:397-414@6b0b49f`. The store hits the line the load just brought in, so there is no extra fill (PROBABLE) |
| 3 | SW raw stats, row step 4: cell rows 0, 4, 8 ... of 1100, each 2 raw rows x 480 pairs x 16 B | CPU | **4.22** (+ ≤0.53 metering weights) | ~0 | CONFIRMED loop, `raw_stats.cpp:39-41,145-148,205-231,286-292@6b0b49f`. Arithmetic: 275 x 2 x 7680 = 4,224,000. Weights: 275 x 1920 B, only if a weights file loaded (PROBABLE). Data come from DRAM: the swap ends with a clean+invalidate (L1), or row 0 was evicted long before (L2) |
| 4 | PiSP back end: raw tiles (x1.1085 re-read), TDN ref read, TDN write, YUV420 1280x720 out, config | DMA (iommu2) | 18.73 + 18.73 | 18.73 + 1.38 + 0.02 | From Q1 §2 (libpisp v1.3.0 tiler simulation; the TDN overlap is PROBABLE there, lower bound 16.83 each). TDN format = the 16-bit CFE format: CONFIRMED, `pisp.cpp:1901-1905@6b0b49f`. **Total 57.58** |
| 5 | IPA: reads stats, writes BE config | CPU | 0.02 | 0.02 | PROBABLE (struct sizes from Q1). Negligible |
| 6 | Core copy (T25 worker): `DMA_BUF_SYNC_READ` start, `memcpy` of stride x active height, sync end | CPU | **16.59** | **16.59** | f60e301: `copyRawBytes` `CameraController.cpp:6762-6786`, size `:7221-7236` = 7680 x 2160, call `:7268-7269`. The pooled vectors are reused without zero-fill (`:3657-3678,3970-3990`): CONFIRMED. That d9f00d4 keeps this is PROBABLE (brief §2). If the A76 does a read-for-ownership on the destination, add 16.59 read (PROBABLE no, write-streaming; X6 tells) |
| 7 | DNG write: row `memcpy` into a 491,520 B scratch (64 rows), then buffered `write()` = `copy_from_user` into page-cache pages | CPU | **16.59** (scratch re-reads stay in L2/L3) | **16.59** page cache | CONFIRMED, `apertar-core/src/cdng/CdngEncoder.cpp:1861-1909` (chunk = max(256 KiB, 64 rows) ≤ 4 MiB, `:1868-1872`), row copy `:1045`, `::write` `:462-480`, open `O_WRONLY|O_CREAT|O_TRUNC` (no O_DIRECT) `:1748-1753@f60e301`. That the scratch stays cache-resident is PROBABLE (480 kB vs 512 kB L2) |
| 8 | NVMe DMA reads the dirty pages; writeback starts at close via `POSIX_FADV_DONTNEED` | DMA (PCIe x1 gen 3) | **16.59** | 0 | CONFIRMED, `CdngEncoder.cpp:1758,1779@f60e301`, `mm/fadvise.c:113-115@5bd564a` (DONTNEED starts `WB_SYNC_NONE` writeback). The block layer's DMA map adds a cache clean walk over the pages (no extra bytes) |
| 9 | exFAT metadata: dentry set (4 x 32 B), bitmap bits, no FAT chain for contiguous files; `block_write_begin` does no zero-fill for full pages | CPU + DMA | < 0.01 | < 0.01 | PROBABLE, `fs/exfat/inode.c:449-464`, `fs/exfat/dir.c:429@5bd564a`. Note: lookup of a new name scans the whole directory (`dir.c:1045-1072`), O(files) per create. Trivial at 300 files per clip; it grows for long takes |
| 10 | Touch/HDMI UI preview: dma-buf fds over `SCM_RIGHTS`, EGL import, GPU samples the 1.38 MB YUV per drawn frame, then renders and scans out the HDMI framebuffer | GPU + HVS DMA | 1.38 + scanout | framebuffer | Zero-copy path: CONFIRMED in Core (`CameraController.cpp:7567-7712@f60e301`); UI side per `apertar-kb/llm/flows.md:131-146` (KB, not re-read). Display bytes **UNCONFIRMED** (mode unknown, see §4.4) |
| 11 | Web MJPEG preview (only while a browser is connected): nearest downsample 1280x720 -> 640x360 from the **non-cacheable** preview mapping, **on libcamera's completion thread**, then TurboJPEG q75 on another thread | CPU | ≤0.7 | 0.35 | CONFIRMED, `apertar-core/src/ApertarCoreApp.cpp:60-63,6963,8111-8190@f60e301` (comment `:8119`: "This runs on libcamera's completion thread"). Few bytes, but byte-wise uncached reads are slow (PROBABLE). Was a browser open during the takes? UNCONFIRMED |
| 12 | Cache maintenance on the raw buffer: 2 attachments x (start + end) per sync bracket. L1: swap bracket + stats bracket = 8 walks on the CameraManager thread. L2: one bracket = 4 walks on the worker. Core: 4 walks. Each walk = 264,000 line operations (F/64) | CPU (kernel) | 0 extra | 0 extra (cleans write back lines that would be written anyway) | CONFIRMED code (`pisp.cpp:2218-2223,3088-3109,816-833@6b0b49f`, §1). Cost per walk: ≤0.41-0.54 ms (PROBABLE, from the idle CameraManager thread: 41-44 % busy = 13.7-14.7 ms per frame minus 25 M user cycles / 2.4 GHz = 10.4 ms leaves 3.3-4.3 ms of kernel time for 8 walks plus all ioctls; `lessons/hardware-log.md:161`) |

## 3. Totals

Arithmetic (MB per frame):

- CPU = swap 33.792 + stats 4.224 + Core copy 33.178 + DNG/page cache 33.178 + IPA 0.040 = **104.41 MB** (weights +0.53 if loaded).
- DMA = CFE 16.919 + BE 57.584 + NVMe 16.589 = **91.09 MB** (UI/HDMI not included).
- Total = **195.50 MB per frame**.

| Case | MB/frame | x fps | GB/s | Label |
| --- | --- | --- | --- | --- |
| Recording, 30 fps, L1/L2 (row step 4) | 195.50 (CPU 104.41, DMA 91.09) | x 30 | **5.87** (CPU 3.13, DMA 2.73) | PROBABLE |
| Recording, 30 fps, before L1 (row step 1: stats 16.90) | 208.18 | x 30 | 6.25 | PROBABLE |
| Recording, 25 fps (clean in every measured take) | 195.50 | x 25 | 4.89 | PROBABLE |
| Preview only, 30 fps (clean, 30.00 fps): CFE + swap + stats + BE + IPA | 112.56 | x 30 | 3.38 | PROBABLE |
| What recording adds: copy 33.18 + page cache 33.18 + NVMe 16.59 | 82.94 | x 30 | 2.49 (+74 %) | PROBABLE |

Cross-check with Q1: Q1's 163 MB per frame leaves out pass 7, the page-cache copy (33.2 MB). The difference is exactly that pass.
Cross-check with Q5: Q5 counts ~83 MB per frame of recording traffic. That matches the 82.94 above.

## 4. What a Pi 5 sustains

### 4.1 DRAM

| Figure | Value | Label, source |
| --- | --- | --- |
| Interface | "A 32-bit LPDDR4X memory interface provides up to 17 GB/s" | CONFIRMED, `raspberrypi/documentation/.../processors/bcm2712.adoc:5@41e24fb`. 4267 MT/s x 4 B = 17.07 GB/s (arithmetic) |
| tinymembench/sbc-bench memcpy | 5.1-5.2 GB/s (CNX 2023 review), 5,530 / 5,370 MB/s (CNX 2024, 2 GB / 8 GB), 6,083 MB/s (sbc.compare, 4 GB), 6,012.7 MB/s (geerlingguy/sbc-reviews#58, CM5). These are copy rates, so DRAM traffic is about 2x = **10.2-12.2 GB/s** | UNCONFIRMED (search summaries: cnx-software.com/2023/11/05/raspberry-pi-5-review-..., cnx-software.com/2024/08/27/comparison-of-raspberry-pi-5-with-2gb-and-8gb-ram-..., sbc.compare/raspberry-pi-5, github.com/geerlingguy/sbc-reviews/issues/58) |
| memset | 11.3-12.8 GB/s (same sources; sbc.compare lists 8.8) | UNCONFIRMED |
| STREAM / RAMspeed | STREAM Copy ~10.2 GB/s, Triad ~11.2 (zbotic.in, low authority); RAMspeed SMP Copy 9.7-10.1 GB/s (openbenchmarking, Pi 5 16 GB) | UNCONFIRMED |
| SDRAM tuning, late 2024 | Bootloader 2024-09-23: `SDRAM_BANKLOW` configurable. 2024-10-10: page-hold/auto-precharge, "~2% improvement with Geekbench 6". 2024-11-05: `system_heap.max_order=0` added when NUMA is on. 2024-12-07: "Enable banklow (and so NUMA) by default ... banklow=1 (2712)". 2025-11-05: adds `iommu_dma_numa_policy=interleave` "for iommu dma kernel allocations". 2026-09-24: SDRAM starts at the high-temperature refresh rate, then adapts to temperature | CONFIRMED, `rpi-eeprom/firmware-2712/release-notes.md:1051-1052,1039-1040,1009-1012,967-970,452-457,82-87@f54693e` |
| Effect of the tuning | 10-20 % at 2.4 GHz overall; NUMA patches "another 5-10 %" (Jeff Geerling, Dec 2024) | UNCONFIRMED (search summary of jeffgeerling.com/blog/2024/raspberry-pi-boosts-pi-5-performance-sdram-tuning) |
| BANKLOW=1 mapping | Address = {bank[3:1], row, bank[0], column}. The bootloader also adds `numa=fake=<n>`. "if NUMA is not available in the kernel then performance will be adversely affected" | CONFIRMED, `documentation/.../raspberry-pi/eeprom-bootloader.adoc:744-778@41e24fb` |
| Kernel support | `CONFIG_NUMA=y`, `CONFIG_NUMA_EMU=y`, 16 K pages; `numa_policy=` and `iommu_dma_numa_policy=` boot parameters exist. Without the latter, IOMMU DMA allocations default to `MPOL_LOCAL` | CONFIRMED, `arch/arm64/configs/bcm2712_defconfig:50,54,96`, `mm/mempolicy.c:3391-3414`, `drivers/iommu/dma-iommu.c:887-924,937-980@5bd564a` |

Reading (PROBABLE): with BANKLOW=1 the three high bank bits pick one of 8 contiguous regions (4 GB / 8 = 512 MB each). `numa=fake=8`
turns each region into a node. An interleave policy then spreads consecutive pages, 16 KB each with `system_heap.max_order=0`, over
all 8 regions and so over all banks. Without NUMA, or for memory that comes from one contiguous range, a buffer sits in one region
and uses only the 2 banks that bank[0] toggles. That lowers bank parallelism when several streams compete.

### 4.2 CMA

- DT default: 64 MB, `alloc-ranges` 0-1 GB, reusable (CONFIRMED, `bcm2712.dtsi:170-186@5bd564a`). The Pi showed "CMA: 64 MB total,
  32 kB free" in SDR (`apertar-kb/working/clearhdr-fps-request.md:20`, a reading from 2026-10-2x; current state UNCONFIRMED).
- In this pipeline, **no camera buffer needs CMA** (PROBABLE). The CFE and BE are behind IOMMUs and allocate scattered pages, and
  Core's raw buffers come from the system heap (§1). CMA placement therefore matters for bank interleaving only if some large camera
  buffer still lands in CMA. A 64 MB region inside one 512 MB bank region would put all of it on 2 banks. `bufinfo` in §7 settles who
  holds the CMA.

### 4.3 The RP1 link (CFE writes) and the NVMe link

| Link | Capacity | Load | Label |
| --- | --- | --- | --- |
| RP1 to BCM2712: PCIe 2.0 x4 (`pcie2`, `max-link-speed = <2>`, `num-lanes = <4>`) | 4 x 5 GT/s x 8/10 = 2.0 GB/s per direction; 1.68 (MPS 128) to 1.83 GB/s (MPS 256) after about 24 B of TLP overhead per packet | CFE 16.92 MB x 30 = 0.51 GB/s average = **28-30 %**. The CSI-2 link caps the burst rate at 4 x 1782 Mbps / 8 = 0.89 GB/s = ≤53 % | Link CONFIRMED (`bcm2712.dtsi:526-532@5bd564a`; `documentation/.../io-controllers/rp1.adoc:17,30@41e24fb`). Efficiency and MPS PROBABLE (Pi `lspci`, §7) |
| NVMe: PCIe x1 (`pcie1`), gen 3 by `dtparam=pciex1_gen=3` | 8 GT/s x 128/130 = 0.985 GB/s raw; `dd` O_DIRECT measured 733 MB/s | 16.59 MB x 30 = 0.50 GB/s = 51 % raw, **68 % of the measured** | CONFIRMED config (`apertar-kb/sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:34-35`; `bcm2712-rpi.dtsi:227`), `lessons/hardware-log.md:78` |

Neither link is near saturation at 30 fps (PROBABLE). The CSI-2 receiver error and overflow counters read 0 in T22, which supports
that the CFE path keeps up.

### 4.4 The display (not in the totals)

The UI runs on HDMI with `vc4-kms-v3d`, and no DPI panel is attached (CONFIRMED, `apertar-kb/sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:25`).
The mode is unknown. Scanout alone costs W x H x 4 B x Hz: 1280x720p60 0.22 GB/s, 1080p60 0.50, 2160p30 1.00, **2160p60 1.99 GB/s**.
If the QML scene redraws per preview frame (30/s), framebuffer writes add 0.11 / 0.25 / 1.00 / 1.00 GB/s. That load is PROBABLE
from Qt EGLFS with swap interval 1, per the KB UI notes. It applies in preview-only too, so it is background load, and it could be
as large as everything Core adds. UNCONFIRMED until the mode is read (§7).

## 5. Comparison and what it explains

| Quantity | Value | Label |
| --- | --- | --- |
| Recording at 30 fps vs theoretical | 5.87 / 17.07 = **34 %** | PROBABLE |
| vs single-core streaming (10.2-12 GB/s) | **49-58 %** | PROBABLE (inputs UNCONFIRMED) |
| Recording adds | +2.49 GB/s (3.38 -> 5.87, +74 %) | PROBABLE |
| CPU pass slowdown measured | swap 6.1 -> 9.9 ms (x1.62; 5.54 -> 3.41 GB/s); CameraManager cycles/frame 25 M -> 36 M at the same instructions and L3 refills (x1.44) | CONFIRMED (`lessons/hardware-log.md:161-162,188`); rates by arithmetic |
| Burst demand while the BE runs (L2) | BE 57.6 MB / ~15 ms ≈ 3.8 GB/s + swap worker 33.8 MB / 10 ms ≈ 3.4 + Core copy at memcpy speed ≈ 5-6 (traffic) + DNG writers ≈ 3-6 + CFE ≤ 0.9 + NVMe ≈ 0.7 → **~15-20 GB/s requested** | PROBABLE (timing overlap assumed, not measured) |

Reading (PROBABLE): this is not a "DRAM full" limit on average. The serial stage (IPA + BE, Q1/Q2) shares DRAM in bursts with three
CPU streams whose combined peak exceeds the practical ceiling. Latency then rises for everyone. The BE has AXI QoS 0 (Q1), so it may
lose more than the CPU. This also explains L2: moving the swap onto a worker made it overlap the BE in time, so the period did not
shrink. Two facts bracket the threshold. 25 fps recording (4.89 GB/s, 40 ms period) is clean, and 30 fps (5.87 GB/s, 33.3 ms) is
not. Taking TDN out (4.74 GB/s, and a 65 % smaller BE) lands below the 25 fps load.

Side observation (PROBABLE, needs the Pi): "Five other Core threads at 18-20 % each" while recording (`lessons/hardware-log.md:164`).
If those are the 5 DNG workers, the arithmetic is 5 x 0.19 core-s/s / 26.45 frames/s = 36 ms of CPU per DNG. Moving 33 MB at ≥3 GB/s
needs only about 11 ms, so the rest would be kernel write-path work, probably buffer-head handling in exFAT's `block_write_begin`
path. That is CPU, not bandwidth, and it runs off the serial chain. The `stime` split (§7) settles it.

## 6. Ranking

| Pass | MB/frame | GB/s @30 | How to remove or shrink | Cost | Label |
| --- | --- | --- | --- | --- | --- |
| BE TDN read + write | 37.46 | 1.12 | tuning-file copy without `tdn` (Q1 X2), or `NoiseReductionMode=Off` | **configuration** (no build); preview only, DNGs unchanged | PROBABLE |
| BE raw read + output | 20.12 | 0.60 | BE every Nth frame, or a smaller BE input (Q1 X4) | libcamera patch | PROBABLE |
| Core copy | 33.18 | 1.00 | buffered write straight from the camera buffer (Q5) | Core code; longer request hold | PROBABLE |
| Page-cache copy | 33.18 | 1.00 | O_DIRECT from Core's copy (T24). O_DIRECT from the camera buffer is impossible: system-heap mmap is `VM_IO|VM_PFNMAP`, GUP returns `-EFAULT` | Core code (aligned buffer, DNG layout with a block-aligned payload) | CONFIRMED (`mm/gup.c:1277-1278`, `mm/memory.c:2672@5bd564a`; Q5 agrees) |
| Copy + page cache together | 66.36 | 1.99 | memfd + udmabuf raw buffers (`CONFIG_UDMABUF=y`), O_DIRECT from the memfd mapping (Q5) | Core code, larger | PROBABLE |
| Swap | 33.79 | 1.01 | needs a byte-swapping source (Q4), or fuse it with Core's copy (read once, write twice: saves 16.9 MB) | libcamera + Core code | PROBABLE |
| CFE write | 16.92 | 0.51 | none (it is the capture) | — | CONFIRMED |
| NVMe read | 16.59 | 0.50 | none (it is the recording) | — | CONFIRMED |
| Raw stats | 4.22 | 0.13 | row step 8 (-2.1), every 2nd frame (-2.1) | config (env) | PROBABLE; bandwidth-irrelevant |
| HDMI scanout + UI render | 0.3-3.0 | — | lower mode, or unplug during takes | configuration | UNCONFIRMED |
| Cache walks (8-12 x 16.9 MB per frame) | 0 bytes | — | fewer sync brackets (L2 already halves libcamera's) | code | PROBABLE |

**Cheapest single pass to remove: TDN** (largest of the configuration-only items, inside the serial stage). Second, by configuration:
the HDMI mode, **if** it reads 4K (unknown). Of the code changes, O_DIRECT (T24) saves 1.0 GB/s with no extra hold and already has a
supporting measurement (T22: `dd` O_DIRECT cost no frames, buffered `dd` did, `lessons/hardware-log.md:75-79`).

## 7. Read-only commands for the Pi (Patrik runs those marked sudo)

- **Fake NUMA / interleave:** `cat /proc/cmdline | tr ' ' '\n' | grep -E 'numa|max_order|iommu_dma'`;
  `ls -d /sys/devices/system/node/node*`; `cat /sys/devices/system/node/node*/meminfo | grep MemTotal`;
  `dmesg | grep -iE 'numa|fake|policy'`; `vcgencmd bootloader_version`; `rpi-eeprom-update` (prints only, unless `-a`);
  `rpi-eeprom-config | grep -i sdram`.
  Expected: `numa=fake=8`, `numa_policy=interleave` (PROBABLE; the release notes speak of "a similar numa interleave"),
  `system_heap.max_order=0`, `iommu_dma_numa_policy=interleave` on a bootloader of 2025-11-05 or later, and 8 node directories.
- **CMA:** `grep -i cma /proc/meminfo`; `dmesg | grep -i cma` (base address and size);
  `xxd /proc/device-tree/reserved-memory/linux,cma/size; xxd /proc/device-tree/reserved-memory/linux,cma/alloc-ranges`.
- **Who holds which buffer (sudo):** `sudo cat /sys/kernel/debug/dma_buf/bufinfo` lists size, exporter and attached devices.
  Expected: 8 buffers of 16,908,288 B (16,896,000 rounded up to 16 KB pages, if the heap page-aligns; PROBABLE) from exporter `system`,
  each attached to the rp1-cfe and pispbe devices, plus vb2 exports. Also `ls -l /dev/dma_heap/` (expect `vidbuf_cached -> system`)
  and `ls /sys/kernel/iommu_groups/*/devices`.
- **Core's own allocation line:** `journalctl -u apertar-core -b | grep -E 'RAW buffers|cached DMA allocation'`.
- **Is the DNG write buffered (sudo, during a short take):**
  `sudo strace -f -e trace=openat,write,pwrite64 -e signal=none -p $(pidof apertar-core) 2>&1 | grep -m 5 -A2 '\.dng'`.
  Expected: `O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC`, no `O_DIRECT`, `write(..., 491520)` chunks. Without strace: Δ`nr_dirtied` in
  `/proc/vmstat` over a 10 s take x 16384 B ≈ 16.6 MB x frames written.
- **Writer CPU, user vs kernel:** `for t in /proc/$(pidof apertar-core)/task/*; do echo "$(cat $t/comm) $(cut -d' ' -f14,15 $t/stat)"; done`, run twice, 10 s apart, during a take.
- **Sync cost (sudo, preview only first; strace slows the process):**
  `sudo timeout 3 strace -f -T -e trace=ioctl -e signal=none -p $(pidof apertar-core) -o /tmp/sync.txt; grep DMA_BUF_IOCTL_SYNC /tmp/sync.txt | sed 's/.*<\(.*\)>/\1/' | sort -n | awk '{a[NR]=$1} END{print NR, a[int(NR/2)], a[int(NR*0.9)]}'`.
- **HDMI mode:** `cat /sys/class/drm/card*-HDMI-A-*/status`; `sudo cat /sys/kernel/debug/dri/*/state | grep -E 'mode|crtc\['`
  (or `kmsprint` if installed).
- **PCIe (sudo):** `sudo lspci -vvv | grep -E '^[0-9a-f]|LnkSta:|DevCtl:|MaxPayload'` (RP1 and NVMe: width, speed, MPS).
- **Counters:** `ls /sys/bus/event_source/devices/` (expect `armv8_cortex_a76` and no DSU, CMN or DMC PMU:
  `CONFIG_ARM_DSU_PMU` is absent from `bcm2712_defconfig`, and `bcm2712.dtsi` has no DSU-PMU node, CONFIRMED by grep);
  `cat /proc/sys/kernel/perf_event_paranoid`; `modinfo raspberrypi_axi_monitor` (`CONFIG_RPI_AXIPERF=m`, `bcm2712_defconfig:1601`).
  The BCM2712 AXI monitor exists but is disabled in DT (`bcm2712-ds.dtsi:93-99`). `dtparam=axiperf=on` enables it
  (`bcm2712-rpi.dtsi:176`; Patrik, config.txt + reboot). It then exposes `/sys/kernel/debug/raspberrypi_axi_monitor/System/data`
  with transactions and wait cycles per bus (ARM, PCIE_01, ARGON_TOP, ...) and a 5-bit source filter
  (`drivers/perf/raspberrypi_axi_monitor.c:215-301,733-734,760-770,805@5bd564a`). Bytes per transaction and the bus-to-block mapping
  are UNCONFIRMED.

## Experiments this suggests

Takes = `working/tools/takes.sh 3 10` at 30 fps, uncompressed, Clear HDR 16-bit, L2 on, unless stated. Patrik does sudo, restarts,
config.txt and drop-ins.

**X0. Facts first (no change, §7).** Prediction: NUMA fake=8 with interleave active; Core's 8 raw buffers from `system` with 2
attachments each; the HDMI mode read. Rule-out and consequence: if `numa=fake` is absent or only 1 node exists, the docs say
performance is "adversely affected". Update the bootloader before any other test (Patrik). If Core's raw buffers are not system-heap
buffers, the CPU passes run uncached, and this budget does not apply.

**X1. Dose-response: does extra memory traffic alone reproduce the loss? (no code; `stress-ng` must be installed, Patrik).**
Preview only at 30 fps (not recording). Inject a controlled stream on core 3:
`taskset -c 3 stress-ng --memrate 1 --memrate-bytes 256M --memrate-rd-mbs R --memrate-wr-mbs R -t 25s` for R = 0, 500, 1000, 1500,
2000 MB/s. The flag names are UNCONFIRMED; check `stress-ng --help | grep memrate`. Measure delivery during each step with
`python3 -I working/tools/ipa_rate.py "<start>" "<end>"`, and the stressor's achieved rate from its own report. Prediction:
recording adds 2.49 GB/s (2.0 of it CPU) and delivers 27.6-28.8 fps. So preview-only stays at 30.00 fps up to about 1.5 GB/s
injected and falls below 29.5 fps between 2.0 and 3.0 GB/s injected (R = 1000-1500). Rule-out: still 30.00 fps with intervals
> 60 ms = 0 at ≥ 4 GB/s injected. Then bandwidth is not the mechanism, and the loss lies in recording-only work on the threads
(Q2, the web preview on the completion thread).

**X2. TDN off (configuration; Q1 X2).** Prediction: total traffic falls by 37.5 MB/frame, from 5.87 to 4.74 GB/s, and missing
frames reach ≤3 per take (delivered ≥ 29.8 fps). Rule-out: ≥7 missing per take (the best L1 result) with a BE time within 15 % of
TDN-on.

**X3. Display load (configuration).** If X0 shows ≥1080p60, record 3 takes with the HDMI output at 1280x720@60, or with the monitor
unplugged if the UI tolerates it. Prediction: from 2160p60, scanout + render fall by about 1.8-2.7 GB/s (1.99 - 0.22 scanout, plus
up to 1.00 - 0.11 render), and the takes become ≤3 missing. From 1080p60, they fall by about 0.3-0.4 GB/s and missing frames drop
by at most a third. Rule-out: no change after a
≥1 GB/s reduction.

**X4. Writer concurrency (configuration).** Core's DNG workers 5 -> 1 (uncompressed only). This limits how many memcpy and
copy_from_user streams overlap the BE. Prediction, if bursts matter: missing frames drop by ≥50 %, with no `drop[queue-full]`
(one buffered writer needs about 6-12 ms per DNG, PROBABLE). Rule-out: missing unchanged, or queue-full drops appear (then the
writer, not bursts, is the limit).

**X5. Sync cost (no change, §7 strace).** Prediction: in preview-only with L2, 2 libcamera syncs per frame (60/s) at 0.2-1.1 ms
each (2 walks per ioctl, bounded by §2 #12). Recording makes them ≥1.3x longer. Rule-out: >2 ms per ioctl. Then cache maintenance
is a first-order cost, and syncing once per frame, or one attachment, becomes a lever (code).

**X6. CPU-side DRAM reads (no change; sudo for system-wide).**
`sudo perf stat -a -e armv8_cortex_a76/l3d_cache_refill/,armv8_cortex_a76/bus_access_rd/,armv8_cortex_a76/bus_access_wr/ -- sleep 10`
in preview-only, and again during a take (`perf` needs installing if absent). Prediction from §2 (CPU reads per frame / 64 B):
preview 21.1 MB x 30 / 64 = 9.9 M refills/s; recording 54.3 MB x 30 / 64 = 25.5 M/s, ±30 % for prefetch. Rule-out: about 41 M/s
recording. That would mean read-for-ownership on the copy destinations (+33 MB/frame), and the budget rises to about 6.9 GB/s.

**X7. O_DIRECT (T24, code).** Prediction: -33.2 MB/frame CPU (5.87 -> 4.87 GB/s; with X2 3.75 GB/s), `nr_dirtied` per take ≈ 0,
missing ≤ half of the L2 result. Rule-out: no change in missing frames, with `nr_dirtied` confirmed near 0.

**Brief §6 ideas, judged on bytes.** Row step 8 or stats every 2nd frame saves 2.1 MB/frame (0.06 GB/s, 1 %): expect no effect.
"Core's copy as a no-op" removes 83 MB/frame, which equals preview-only (already known clean). It is only a sanity check: if it is
*not* clean, recording has a non-bandwidth cost. "tmpfs instead of NVMe" removes only the 0.50 GB/s NVMe read and keeps the
page-cache copy. A 10 s take needs 4.76 GB of RAM (287 x 16.59 MB) on a 4 GB Pi, so only ≤3 s takes fit. Gaps start after 27-47
frames, so such takes are too short to read.

## Unknowns

- The Pi's bootloader date and SDRAM/NUMA state, and therefore the bank interleaving of each buffer class (X0).
- The HDMI mode and how often the UI redraws. The display may be the largest unlisted consumer (X0, X3).
- The practical DRAM ceiling on BCM2712 under mixed CPU + DMA traffic, and how the arbiter treats BE AXI QoS 0 against the
  CPUs, PCIe (RP1, NVMe) and the HVS. No public measurement could be opened. The cited memcpy/STREAM figures are single-core and
  come from search summaries.
- The cost of one cache walk over 16.9 MB on the A76 (bounded at ≤0.54 ms; X5 measures it).
- Whether d9f00d4 copies stride x 2160 like f60e301, and whether a browser (MJPEG) was connected during the takes. That path reads
  uncached memory on libcamera's completion thread.
- The TDN write width, 18.73 vs 16.83 MB (Q1), and whether the A76 write-streams large memcpy destinations (X6).
- The PCIe MPS for RP1 and NVMe (`lspci`), the exFAT cluster size and the NVMe logical block size (`cat /sys/block/nvme0n1/queue/logical_block_size`).
- Bytes per transaction and the bus map of the BCM2712 AXI monitor, which is the only DMA-side counter found.

## Verification

Verifier: adversarial pass (Claude Opus 5.5), 2026-10-26. Every cited line was reopened in the trees named in the header
(`git show f60e301:<path>` for apertar-core; working trees at the cited commits for libcamera-apertar `6b0b49f`, libpisp `v1.3.0`,
kernel-rpi `5bd564a`, raspberrypi/documentation `41e24fb`, rpi-eeprom `f54693e`). This session's WebFetch reached github.com but not
cnx-software.com, sbc.compare, jeffgeerling.com, spec.org or raspberrypi.com. stress-ng's man page was read from a fresh clone
(ColinIanKing/stress-ng `5c930c3`). Verdicts: CONFIRMED (holds; "as PROBABLE" = the reasoning holds and the label stays),
CORRECTED (holds in substance, a detail, cite or number is wrong), REFUTED, UNVERIFIABLE (needs the Pi or a page that did not load).

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | F = 3840 x 2200 x 2 = 16,896,000 B; A = 3840 x 2160 x 2 = 16,588,800 B | CONFIRMED | arithmetic; `apertar-kb/working/clearhdr-design.md:109` (`frame_bytes=16896000`) |
| 2 | CFE bpl = ALIGN(3840 x 16 / 8, 16) = 7680; sizeimage = height x bpl | CONFIRMED | `kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:78,531-541@5bd564a` |
| 3 | libcamera stride aligned to 64 B; 7680 = 120 x 64 is unchanged | CONFIRMED | `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:258-277@6b0b49f`; `libpisp/src/libpisp/common/pisp_utils.cpp:115-119@v1.3.0` |
| 4 | Raw `frameSize = cfeFormat.planes[0].size` is what Core allocates | CONFIRMED | `pisp.cpp:1887-1898@6b0b49f` (`:1897`) |
| 5 | `rawStats_` engages for `Needs16bitEndianSwap`; `ccmpUnwrap_` only at 12-bit | CONFIRMED | `pisp.cpp:1813-1844@6b0b49f` |
| 6 | Core raw buffers: `vidbuf_cached` first, then `linux,cma`; `len = frameSize`; comment "too slow on the CFE's uncached buffers" | CONFIRMED | `apertar-core/src/camera/CameraController.cpp:6652-6658,6736-6760@f60e301`. The symlink to the system heap is a udev rule, not in these trees: stays PROBABLE |
| 7 | csi0/csi1 behind `iommu5` ("HACK for RP1 masters over PCIe"), `pisp_be` behind `iommu2` | CONFIRMED | `kernel-rpi/arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts:244-250`, `bcm2712-ds.dtsi:301-308,386-394@5bd564a` |
| 8 | No `dma-coherent` in `bcm2712*.dts*` or `rp1.dtsi` | CONFIRMED | grep over all 16 files: 0 hits |
| 9 | vb2 exports: `iommu_dma_alloc_remap`, mmapped `MT_NORMAL_NC`; CFE/BE queues set no cache hints | CONFIRMED | `drivers/iommu/dma-iommu.c:1695-1708,1732-1740`, `kernel/dma/mapping.c:505-514`, `arch/arm64/include/asm/pgtable.h:694-696`, `cfe.c:1944-1952`, `pisp_be.c:1449-1450@5bd564a`; neither driver sets `dma_attrs` or `allow_cache_hints` (grep) |
| 10 | vb2-dma-contig `begin/end_cpu_access` return 0 | CONFIRMED | `drivers/media/common/videobuf2/videobuf2-dma-contig.c:427-439@5bd564a` |
| 11 | System heap syncs once per mapped attachment; for-device BIDIRECTIONAL = clean+invalidate, for-CPU = invalidate | CONFIRMED | `drivers/dma-buf/heaps/system_heap.c:159-199`, `dma-iommu.c:1192-1221`, `arch/arm64/mm/dma-mapping.c:15-36@5bd564a`. Detail the report leaves out: in this tree for-device with FROM_DEVICE also invalidates (`:29-31`), so Core's `DMA_BUF_SYNC_READ` END is a walk too (consistent with the report's 4 Core walks) |
| 12 | CFE Output0 and BE Input both attach; vb2 keeps the mapping while the same dma-buf returns; 32 import slots | CONFIRMED (code); both mapped stays PROBABLE | `drivers/media/common/videobuf2/videobuf2-core.c:1421-1483@5bd564a`; `libcamera-apertar/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:958@6b0b49f` (`VIDEO_MAX_FRAME`) |
| 13 | System-heap mmap: `remap_pfn_range`, default (cacheable) prot, `VM_IO\|VM_PFNMAP` | CONFIRMED | `system_heap.c:201-220`, `mm/memory.c:2672@5bd564a` |
| 14 | 512 kB L2 per core, 2 MB L3, 64 B lines | CORRECTED (cite) | the L2 node is `bcm2712.dtsi:115-123@5bd564a`; `:155-162` is only the L3 node. `processors/bcm2712.adoc:5@41e24fb` CONFIRMED |
| 15 | Swap: `ld1/rev16/st1`, (3840+7)/8 = 480 steps x 16 B = 7680 B/row x 2200 rows = 16.90 MB read + 16.90 MB write | CONFIRMED | `pisp.cpp:397-414@6b0b49f`; height is the raw StreamConfiguration's (`:2210`), 2200 rows PROBABLE |
| 16 | The swap store adds no line fill; the stats then re-read from DRAM | CONFIRMED (as PROBABLE), with evidence the report did not use | pre-L1 CameraManager thread: 0.57 M L3 refills per frame (`lessons/hardware-log.md:161`) vs predicted swap 264,000 + row-step-1 stats 264,000 = 528,000 lines (+8 %) |
| 17 | Stats at row step 4: 1100/4 = 275 cell rows x 2 x 7680 = 4,224,000 B; weights 275 x 1920 = 528,000 B | CONFIRMED | `raw_stats.cpp:39-41,145-148,205-231,286-292@6b0b49f`; `raw_stats.h:105` (`std::vector<uint8_t> cellWeight_`) |
| 18 | BE 57.58 MB/frame = 3 x 18.728 + 1.382 + 0.017; TDN nodes take the 16-bit CFE format | CONFIRMED | `pisp.cpp:1901-1905,2565-2582@6b0b49f`; Q1 rows 20-25 (`q1-backend.md:311-316`) |
| 19 | TDN is on during the Pi takes (all TDN numbers rest on it) | UNVERIFIABLE | In Clear HDR with automatic tuning Core loads `<sensor>_clearHDR.json` from `/home/pi/Tuning-Files/defaults-pisp` or `/usr/local/share/libcamera/ipa/rpi/pisp` (`apertar-core/src/camera/DefaultTuningSelection.hpp:65-76,186-199`, `CameraController.cpp:5583-5592@f60e301`), not the `imx585.json` in libcamera-apertar. Pi: `journalctl -u apertar-core -b \| grep -i tuning`, then `grep -c '"tdn"' <that file>`; or Q1 X3 (`LIBCAMERA_RPI_PISP_CONFIG_DUMP`) |
| 20 | Core copy: `DMA_BUF_SYNC_READ` start, `memcpy` of stride x 2160 = 16,588,800 B, sync end | CONFIRMED (f60e301) | `CameraController.cpp:6778-6784,7226-7236,7268-7269@f60e301`; that d9f00d4 keeps it UNVERIFIABLE |
| 21 | Pooled copy vectors are reused without zero-fill | CONFIRMED (steady state) | recycled with their size intact (`:3873,3954,3970-3990`); `resize(size)` to the same size does nothing (`:3678`). A fresh `std::vector(size)` (`:3670-3671`) zero-fills only while the pool of min(12, max(5+2, 4)) = 7 (`:3992-3995`) fills |
| 22 | No read-for-ownership on large `memcpy` destinations | CONFIRMED (as PROBABLE), stronger than stated | tinymembench "standard memcpy : 6012.7 MB/s" (CM5, https://github.com/geerlingguy/sbc-reviews/issues/58) and 4,805.4-6,139.6 MB/s (Pi 5, https://github.com/geerlingguy/sbc-reviews/issues/21). With RFO that would be 3 x 6.0-6.1 = 18.0-18.4 GB/s of DRAM traffic, above the 17.07 GB/s peak |
| 23 | DNG write: scratch = max(7680, min(4 MiB, max(256 KiB, 64 x 7680))) = 491,520 B; buffered `write()`; open flags without `O_DIRECT` | CONFIRMED | `apertar-core/src/cdng/CdngEncoder.cpp:1868-1872,1886-1904,1045,462-480,1748-1753@f60e301` |
| 24 | The 480 kB scratch stays cache-resident | UNVERIFIABLE (weaker than labelled) | 491,520 B against a 512 kB L2 that the 16.6 MB source and page-cache streams pass through too. If it spills: up to +33.2 MB/frame (+1.0 GB/s). X6 cannot tell this from RFO |
| 25 | `POSIX_FADV_DONTNEED` starts `WB_SYNC_NONE` writeback | CONFIRMED | `CdngEncoder.cpp:1779@f60e301` (`:1758` is `FADV_SEQUENTIAL`); `mm/fadvise.c:112-114@5bd564a` |
| 26 | exFAT metadata < 0.01 MB per file; name lookup O(files) | CONFIRMED (as PROBABLE) | `fs/exfat/inode.c:449-464`, `dir.c:429`, `dir.c:1043-1072@5bd564a` |
| 27 | Touch/HDMI preview is zero-copy (fds over `SCM_RIGHTS`, EGL import) | CONFIRMED (Core side) | `CameraController.cpp:7567-7580@f60e301`; `apertar-kb/llm/flows.md:131-146` |
| 28 | Web MJPEG downsample runs on libcamera's completion thread, from the uncached preview mapping | CONFIRMED | `apertar-core/src/ApertarCoreApp.cpp:60-63,6963-6964,8111-8190@f60e301` (comment `:8117-8118`). Whether a browser was open: UNVERIFIABLE |
| 29 | Walks per frame: L1 8 + Core 4 = 12; L2 4 + Core 4 = 8; 16,896,000 / 64 = 264,000 lines per walk | CONFIRMED | `pisp.cpp:816-833,2218-2223,3088-3109@6b0b49f`; `CameraController.cpp:6765-6775,6778-6784@f60e301`. The L2 worker also issues 2 stats-fd syncs that walk nothing (row 10) |
| 30 | Walk cost ≤0.41-0.54 ms: 0.41 x 33.33 = 13.67 ms and 0.44 x 33.33 = 14.67 ms busy; 25 M / 2.4 GHz = 10.42 ms user; 3.25/8 = 0.41, 4.25/8 = 0.53 ms | CORRECTED (cite only) | arithmetic holds. 41 % is `hardware-log.md:161`, 44 % is `:144`; the PMU counts are user-space only (`:156`), which the subtraction needs |
| 31 | CPU 104.41 + DMA 91.09 = 195.50 MB/frame; x 30 = 5.87 GB/s (3.13 / 2.73) | CONFIRMED | 33.792 + 4.224 + 33.178 + 33.178 + 0.040 = 104.412; 16.919 + 57.584 + 16.589 = 91.092; 195.504 x 30 = 5.865 |
| 32 | Before L1 208.18 MB (6.25 GB/s); 25 fps 4.89; preview-only 112.56 (3.38); recording adds 82.94 (2.49, +74 %) | CONFIRMED | 195.504 − 4.224 + 16.896 = 208.176; 195.504 x 25 = 4.888; 16.919 + 33.792 + 4.224 + 57.584 + 0.040 = 112.559 (x 30 = 3.377); 33.178 + 33.178 + 16.589 = 82.945 (x 30 = 2.488); 5.865 / 3.377 = 1.737 |
| 33 | "Q1's 163 MB ... the difference is exactly that pass" | CORRECTED | 195.50 − 163.2 = 32.3 MB, not 33.18. The −0.9 MB residue: Q1 rounds the copy and NVMe to 16.9 MB (2200 rows) and leaves out IPA and CFE stats (`q1-backend.md:317`) |
| 34 | Q5 counts ~83 MB/frame of recording traffic | CONFIRMED | `q5-copy.md:57,218` (5 x 16.59 = 82.9) |
| 35 | "up to 17 GB/s"; 4267 MT/s x 4 B = 17.07 GB/s | CONFIRMED (quote, arithmetic); the 4267 grade PROBABLE | `documentation/asciidoc/computers/processors/bcm2712.adoc:5@41e24fb`; 4267 x 4 = 17,068 MB/s. LPDDR4X-4267 is not in that repo and raspberrypi.com did not resolve |
| 36 | Single-core memcpy 5.1-6.1 GB/s, i.e. 10.2-12.2 GB/s of traffic | CONFIRMED (2 of 5 sources opened) | sbc-reviews #58 6,012.7 MB/s (CM5 4 GB); #21 4,805.4 (2023) to 6,139.6 MB/s (Pi 5). CNX and sbc.compare: UNVERIFIABLE (hosts did not resolve) |
| 37 | memset 11.3-12.8 GB/s | CORRECTED | #58: 12,646.0 MB/s. #21: 9,359.8-13,943.8 MB/s, and 9.36 / 9.42 / 10.02 GB/s in the three runs with the SDRAM/NUMA tuning on. With the tuning the Pi most likely runs, single-core write streaming is ~9.4-10 GB/s |
| 38 | STREAM ~10.2/11.2, RAMspeed 9.7-10.1 GB/s | UNVERIFIABLE | zbotic.in, openbenchmarking.org not opened |
| 39 | Bootloader notes: BANKLOW 2024-09-23, page-hold ~2 % 2024-10-10, `system_heap.max_order=0` 2024-11-05, banklow default 2024-12-07, `iommu_dma_numa_policy=interleave` 2025-11-05, high-temperature refresh 2026-09-24 | CONFIRMED | `rpi-eeprom/firmware-2712/release-notes.md:82-87,452-457,967-970,1009-1012,1039-1040,1051-1052@f54693e` |
| 40 | Geerling: 10-20 % overall, NUMA another 5-10 % | UNVERIFIABLE | jeffgeerling.com did not resolve |
| 41 | BANKLOW=1 = {bank[3:1], row, bank[0], column}; bootloader adds `numa=fake=<n>`; "adversely affected" without NUMA | CONFIRMED | `documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc:744,760,772,775@41e24fb` |
| 42 | `CONFIG_NUMA`, `CONFIG_NUMA_EMU`, 16 K pages; `numa_policy=` and `iommu_dma_numa_policy=` exist; IOMMU DMA default `MPOL_LOCAL` | CONFIRMED | `arch/arm64/configs/bcm2712_defconfig:50,54,96`, `mm/mempolicy.c:3391-3414`, `drivers/iommu/dma-iommu.c:887-933@5bd564a` |
| 43 | 8 regions of 512 MB; without NUMA a buffer sits on the 2 banks that bank[0] toggles | CONFIRMED (as PROBABLE) | follows from row 41. The Pi's `numa=fake` value: UNVERIFIABLE (§7 command) |
| 44 | CMA 64 MB, 0-1 GB, reusable; the Pi read "32 kB free" | CONFIRMED | `bcm2712.dtsi:180-186@5bd564a`; `working/clearhdr-fps-request.md:20`. Note: CmaFree is also low when movable pages (page cache) borrow the reusable region, so that reading does not show camera buffers in CMA |
| 45 | RP1 link 4 x 5 GT/s x 8/10 = 2.0 GB/s; 128/152 x 2.0 = 1.68, 256/280 x 2.0 = 1.83 GB/s; CFE 0.508 GB/s = 28-30 %; CSI-2 4 x 1782 / 8 = 891 MB/s ≤ 53 % | CONFIRMED (link, arithmetic); efficiency PROBABLE | `bcm2712.dtsi:526-532@5bd564a`; `io-controllers/rp1.adoc:17,30@41e24fb` |
| 46 | NVMe x1 gen 3: 8 x 128/130 = 0.985 GB/s; 0.498 / 0.985 = 51 %; 0.498 / 0.733 = 68 % | CORRECTED (cite) | config CONFIRMED (`apertar-kb/sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:34-35`, `bcm2712-rpi.dtsi:227`). 733 MB/s is `hardware-log.md:69`, not `:78` |
| 47 | HDMI with `vc4-kms-v3d`, no DPI panel; scanout 0.22 / 0.50 / 1.00 / 1.99 GB/s; redraw 0.11 / 0.25 / 1.00 / 1.00 | CONFIRMED (setup, arithmetic); mode UNVERIFIABLE | `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:12,25` (the DPI overlays were disabled on 2026-10-23); 1280x720x4x60 = 0.221, 1920x1080x4x60 = 0.498, 3840x2160x4x30 = 0.995, x 60 = 1.991 GB/s |
| 48 | 5.87 / 17.07 = 34 %; vs 10.2-12 GB/s = 49-58 % | CONFIRMED | 34.4 %; 5.865 / 12.0 = 49 %, / 10.2 = 57.5 % (48 % against the report's own 12.2) |
| 49 | Swap 6.1 -> 9.9 ms (x 1.62; 5.54 -> 3.41 GB/s); cycles 25 M -> 36 M (x 1.44) | CONFIRMED | `hardware-log.md:161-162,188`. The handler times include 4 sync walks, so the pass's own rate is higher: 33.8 MB / (6.1 − 1.6 to 2.2 ms) = 7.5-8.7 GB/s idle (PROBABLE) |
| 50 | Burst demand while the BE runs ≈ 15-20 GB/s | CORRECTED | the listed terms sum to 3.8 + 3.4 + 5 + 3 + 0.9 + 0.7 = 16.8 up to 3.8 + 3.4 + 6 + 6 + 0.9 + 0.7 = 20.8 GB/s. A sum of standalone rates is an upper bound, not a measured demand (PROBABLE at most) |
| 51 | L2: "moving the swap onto a worker made it overlap the BE in time, so the period did not shrink" | CORRECTED | under L1 the swap already ran while the BE hardware ran: 78 % of BE completions were logged right after swap/stats work (`hardware-log.md:192,197`). L1 7/8/20 vs L2 27/31/14 overlap (14 < 20), and the log calls 3 takes per setting a weak comparison (`:230`). There may be no L2 effect to explain |
| 52 | 25 fps (4.89 GB/s) is clean, 30 fps (5.87) is not, so TDN-off (4.74) "lands below the 25 fps load" | CORRECTED (reasoning) | this contradicts the report's own "not a DRAM-full limit on average" (§5). 25 fps is clean because the ~36 ms serial cycle fits a 40 ms period (`hardware-log.md:191`). TDN-off helps only if the BE start interval falls below 33.3 ms. The arithmetic (195.50 − 37.46 = 158.04 x 30 = 4.74) holds |
| 53 | 5 x 0.19 / 26.45 = 36 ms CPU per DNG; 33 MB at 3 GB/s = 11 ms | CONFIRMED (arithmetic); attribution PROBABLE | `hardware-log.md:164`. If T25's copy runs on those threads, the bytes per DNG are 66 MB (~22 ms at 3 GB/s), leaving ~14 ms of kernel work, not ~25 ms |
| 54 | Ranking: TDN removal is "configuration (no build)" via a tuning copy "or `NoiseReductionMode=Off`" | CORRECTED | the tuning copy is configuration (`CameraController.cpp:706-707,1104-1145@f60e301`). `NoiseReductionMode=Off` is a Core code change: f60e301 never sets it (`git grep -i NoiseReduction f60e301 -- src`: no hit). It also turns SDN and CDN off (`src/ipa/rpi/pisp/pisp.cpp:557-571`, `src/ipa/rpi/controller/rpi/denoise.cpp:136@6b0b49f`) |
| 55 | TDN removal: −37.46 MB, −1.12 GB/s (−19 %) | CONFIRMED | 2 x 18.728 = 37.46; x 30 = 1.124; / 195.50 = 19.2 %. Q1's simulation gives 37.615 (57.568 − 19.953) |
| 56 | O_DIRECT from the camera buffer is impossible (`VM_IO\|VM_PFNMAP` -> `-EFAULT`) | CONFIRMED | `mm/gup.c:1277-1278`, `mm/memory.c:2672@5bd564a` |
| 57 | memfd + udmabuf, O_DIRECT from the memfd mapping | CONFIRMED (config); route PROBABLE | `bcm2712_defconfig:1496` (`CONFIG_UDMABUF=y`). udmabuf's own mmap is also `VM_PFNMAP` (`drivers/dma-buf/udmabuf.c:62-71@5bd564a`), so the memfd mapping is the right one, as written |
| 58 | Stats tweaks save ≤2.1 MB/frame (0.06 GB/s, ~1 %) | CONFIRMED | 4.224 / 2 = 2.112; x 30 = 0.063; / 5.865 = 1.1 % |
| 59 | `bufinfo`: 16,908,288 B per raw buffer "if the heap page-aligns" | CONFIRMED (code) | `drivers/dma-buf/dma-heap.c:85@5bd564a` (`PAGE_ALIGN`); 16,896,000 / 16,384 = 1031.25 -> 1032 x 16,384 = 16,908,288 |
| 60 | AXI monitor disabled in DT, `dtparam=axiperf=on`, debugfs `System/data`; no DSU PMU | CONFIRMED | `bcm2712-ds.dtsi:93-99`, `bcm2712-rpi.dtsi:176`, `drivers/perf/raspberrypi_axi_monitor.c:215-311,761-775@5bd564a`; DSU grep over defconfig and DT: no hit |
| 61 | X1 flags `--memrate-bytes`, `--memrate-rd-mbs`, `--memrate-wr-mbs` exist | CONFIRMED | `stress-ng.1:6122,6237,6242` at stress-ng `5c930c3`. The Pi's packaged version: UNVERIFIABLE (`stress-ng --help \| grep memrate`) |
| 62 | X1 design: run on core 3; R = 1000-1500 means 2.0-3.0 GB/s injected | CORRECTED | in preview-only, core 3 is the CameraManager thread's core (per-core idle 2/1/2/41 % vs thread 41 %, `hardware-log.md:161,164`), so pinning there adds CPU contention to the test. The default method `all` "iterate[s] over all the below memrate methods" (`stress-ng.1`, memrate-method table): reads and writes take turns. Injected traffic is ~R (reads) to ~2R (cached writes: fill + write-back) at any moment, not a steady 2R. Fix: pin to core 0-2, run one read-method and one write-method instance, and use the rates the stressor reports |
| 63 | X2 "≤3 missing per take (delivered ≥ 29.8 fps)" | CORRECTED | 284 / 287 x 30 = 29.69 fps; 29.8 fps means ≤1.9 missing |
| 64 | X4 "one buffered writer needs about 6-12 ms per DNG" | CORRECTED | contradicts §5 (36 ms CPU per DNG, `hardware-log.md:164`). 36 > 33.3 ms, so going from 5 workers to 1 predicts queue-full drops whatever the burst theory says. Use 2 workers |
| 65 | X5 "2 libcamera syncs per frame (60/s)" with L2 | CORRECTED | the worker issues 4 `DMA_BUF_IOCTL_SYNC` per frame (raw start/end, stats start/end, `pisp.cpp:816-833@6b0b49f`). The stats ones hit a vb2 export and walk nothing (row 10), so the one-liner's median mixes two populations. Split by fd (`strace -y`) |
| 66 | X6: 21.12 x 30 / 64 = 9.9 M/s; 54.30 x 30 / 64 = 25.5 M/s; rule-out 87.48 x 30 / 64 = 41.0 M/s; 228.68 x 30 = 6.86 GB/s | CORRECTED (event names; arithmetic CONFIRMED) | `bus_access_rd` and `bus_access_wr` are not sysfs aliases of the A76 PMU, which has only `bus_access` and `l3d_cache_refill` (`drivers/perf/arm_pmuv3.c:180-260@5bd564a`). Use `armv8_cortex_a76/event=0x60/` and `/event=0x61/`. A rate of 41 M/s would point to scratch spills (row 24) rather than RFO (row 22) |
| 67 | X7: 162.32 x 30 = 4.87 GB/s; with X2 124.86 x 30 = 3.75 GB/s | CONFIRMED | arithmetic |
| 68 | X3: −1.77 to −2.66 GB/s from 2160p60; −0.28 to −0.42 from 1080p60 | CONFIRMED | (1.99 − 0.22) + (0 to 1.00 − 0.11); (0.50 − 0.22) + (0 to 0.25 − 0.11) |
| 69 | tmpfs: 287 x 16.59 = 4.76 GB, so "only ≤3 s takes fit" and they are "too short to read" | REFUTED (conclusion) | the 4.76 GB holds. But a 3 s take is 90 frames. With the first gap after 27-47 frames and one every 5-9 frames after that (`hardware-log.md:165-166`), (90 − 47)/9 + 1 ≈ 5 to (90 − 27)/5 + 1 ≈ 13 gaps are expected: enough to compare with NVMe takes of equal length. A default tmpfs (50 % of RAM, ~2 GB) holds ~120 frames (2,000 / 16.59) |
| 70 | Core's copy as a no-op equals preview-only (−83 MB) | CONFIRMED (as PROBABLE) | brief §6; same traffic as row 32 |
| 71 | BE AXI QoS 0 means it "may lose more than the CPU" | UNVERIFIABLE | the comment is CONFIRMED (`pisp_be.c:1716-1720@5bd564a`). In AXI, a QoS of 0 means "not participating in a QoS scheme", which is not necessarily the lowest priority. No BCM2712 arbiter documentation is available |

**Counts (71 claims):** CONFIRMED 51 (5 of them "as PROBABLE"), CORRECTED 14, REFUTED 1, UNVERIFIABLE 5.

### Corrections that change substance

1. **X1, the report's main mechanism test, is mis-specified (row 62).** Core 3 is the CameraManager thread's core in preview-only, so a loss
   could come from CPU contention, not bandwidth. stress-ng's default `memrate` method alternates reads and writes, so R = 1000-1500 is not
   2.0-3.0 GB/s injected. Pin to core 0-2, run separate read and write instances, and predict against the achieved rate.
2. **X4 cannot test bursts as written (row 64).** The report's own §5 gives ~36 ms of CPU per DNG. One writer then cannot keep up at
   33.3 ms, and the rule-out ("queue-full drops appear") fires for a reason unrelated to bursts. Use 2 workers.
3. **X2's lever and criterion (rows 19, 52, 54, 63).** That TDN is on during the takes is not established for the Pi: Core loads its own
   `<sensor>_clearHDR.json`. Check it, or dump the BE config, before ranking X2 first. The "below the 25 fps load" argument uses average
   GB/s, which the report itself says is not the limit. The test is whether the BE start interval in an `RPI:0` window falls below 33.3 ms.
   `NoiseReductionMode=Off` is a Core change, not configuration. "≤3 missing" means ≥29.69 fps, not 29.8.
4. **The L2 explanation rests on noise (row 51).** The swap overlapped the BE under L1 as well. The L1 and L2 miss counts overlap, so "L2
   overlaps more" should not steer the ranking.
5. **The tmpfs split is feasible (row 69).** 3-4 s takes contain 5-13 gaps. This is the cheapest way to separate the NVMe DMA from the
   page-cache copy, and it should stay on the list.
6. **The write ceiling is lower than quoted (row 37).** With the SDRAM/NUMA tuning, single-core memset is 9.4-10 GB/s. Headroom for a mix
   that is about half writes is therefore smaller than "49-58 %" suggests.

### Missed

- **A calibration already in the log (row 16).** Before L1, the CameraManager thread showed 0.57 M L3 refills per frame against 528,000
  predicted lines (+8 %). That validates the line-level byte model, shows the stats re-read from DRAM after the clean+invalidate, and
  narrows X6's ±30 % band to about ±10 %.
- **No-RFO evidence (row 22).** tinymembench memcpy at 6.0-6.1 GB/s would need ≥18 GB/s with RFO, above the 17.07 GB/s peak. The
  6.9 GB/s branch of X6 can be dropped.
- **The DNG scratch pass is avoidable outright.** For 16-bit, `rowBytes = width x 2 = 7680 = stride`
  (`apertar-core/src/cdng/CdngEncoder.cpp:1853-1855,1045@f60e301`), so the payload is already contiguous in Core's copy. A single
  `write()` from it (Core change, DNG layout unchanged) removes a 16.6 MB memcpy per DNG and any scratch spill (row 24, up to 1.0 GB/s).
- **The swap's slowdown includes cache-maintenance time (row 49).** The 6.1 -> 9.9 ms handler times include 4 sync walks. X5 should run
  before the whole x1.62 is attributed to DRAM contention.
- **Low CmaFree is not evidence of camera buffers in CMA (row 44).** The region is reusable, so page cache can fill it.
