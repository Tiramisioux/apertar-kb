# Q5: avoid Apertar-Core's raw copy (zero-copy, O_DIRECT, buffer budget)

Reader q5 (cloud session, Claude Opus 5.5), 2026-10-26. Trees: cinepi-raw `63a08d5`, cinemate `d6cc93e`, libcamera-apertar `6b0b49f`
(= qbc `7e9fef0` + `889567a` + `6b0b49f`), kernel-rpi `rpi-6.12.y` `5bd564a` (sparse; widened here with `mm`, `fs/exfat`, `fs/direct-io.c`,
`block`, `lib`, `drivers/dma-buf`; the Pi runs 6.12.75), Apertar-Core `f60e301` only (via `git show`; the Pi's `d9f00d4` is not here).
Labels: **CONFIRMED** = I opened the line or page and it says so; **PROBABLE** = derived, reasoning given; **UNCONFIRMED** = needs the Pi or a
source I could not open. Units: MB = 10^6 B. 16-bit Clear HDR 4K payload P = 3840 x 2160 x 2 = 16,588,800 B (16.59 MB); readout buffer
R = 3840 x 2200 x 2 = 16,896,000 B (16.9 MB); T = 33.33 ms at 30 fps.

## Short answer

1. **The premise is wrong: cinepi-raw is not zero-copy.** Its encode worker copies every row out of the camera buffer into a pooled
   `posix_memalign` buffer (`dng_save` -> `write_pod` -> `memcpy`), releases the camera buffer, then a disk thread does one **buffered**
   `write()` (no O_DIRECT, ever, in the live writer). Its DRAM traffic per frame is the same ~83 MB as Apertar-Core's (CONFIRMED code, PROBABLE bytes).
2. **O_DIRECT straight from the camera buffer is impossible on this kernel.** Core's raw buffers come from `/dev/dma_heap/vidbuf_cached`
   (system heap on Pi 5) or `linux,cma`; both heaps mmap with `VM_IO|VM_PFNMAP` (`remap_pfn_range` / `vmf_insert_pfn`), and the
   direct-I/O path's `pin_user_pages_fast` rejects such VMAs with `-EFAULT` (CONFIRMED code path). A **buffered** `write()` from the same
   mapping works (`copy_from_user` on present PTEs, CONFIRMED code path).
3. A real zero-copy + O_DIRECT path needs a different allocator: **udmabuf over a memfd** (`CONFIG_UDMABUF=y`; CFE behind `iommu5`,
   BE behind `iommu2`, so scattered pages import) with Core writing from the memfd mapping (PROBABLE; untested).
4. **Buffer budget:** 8 buffers = 2 at the CFE (current + programmed next) + ~1 in libcamera when it keeps up + Core's hold. A 22.6 ms
   O_DIRECT hold costs ~0.7 buffer and leaves ~4.3 of slack (PROBABLE). In today's overload (back end period 34.7-36.2 ms) the loss *rate*
   is set by libcamera, not by Core's hold; a longer hold only moves the first gap ~5 frames earlier (PROBABLE, model checked against the
   measured 27-47-frame first gap).
5. **Best bytes saved per ms of hold: copy + O_DIRECT (T24)**: -33 MB/frame (-1.0 GB/s) with no extra hold and no page cache, and it is the
   only option already backed by a measurement (T22: `dd` O_DIRECT cost no frames, buffered did). Zero-copy + buffered saves the same bytes but
   keeps the page cache and holds longer (dominated). Zero-copy + O_DIRECT via udmabuf saves the most (-66 MB/frame, -2.0 GB/s) for ~+0.5 buffer of hold.

## 1. cinepi-raw's path, end to end (brief Q5 part a)

| Step | Where | What it does | Label |
| --- | --- | --- | --- |
| Allocation | `cinepi-raw/core/rpicam_app.cpp:1141-1162@63a08d5` | every stream's buffers from `dma_heap_.alloc()`, then `mmap(PROT_READ\|PROT_WRITE, MAP_SHARED)` | CONFIRMED |
| Heap | `cinepi-raw/core/dma_heaps.cpp:20-29@63a08d5` | `/dev/dma_heap/vidbuf_cached` first, then `linux,cma`; comment: vidbuf_cached "sym links to ... the system heap (Pi 5)" | CONFIRMED (comment); the link target on a Pi is UNCONFIRMED |
| Count | `core/rpicam_app.cpp:630-632` default 6, `--buffer-count` overrides; raw stream follows stream 0 (`:657`) | Cinemate passes 8 (default, ext4) or **10 (exFAT, NTFS)**: `cinemate/src/module/storage_profiles.py:50-94@d6cc93e`, `cinepi_multi.py:841-866` | CONFIRMED |
| Hand-off | `cinepi/cinepi_recorder.hpp:49-106` | `BufferWriteSync` (DMA_BUF_SYNC_START\|RW, `:68`; END in the destructor at scope exit, `core/buffer_sync.cpp:16-45`), push the `CompletedRequestPtr` (`:103`), pass the **raw pointer** to `EncodeBuffer2` (`:105`) | CONFIRMED |
| Queue | `cinepi/dng_encoder.cpp:455-483` | enqueues `{mem, size, ...}`, no copy | CONFIRMED |
| Encode worker | `dng_encoder.cpp:2013-2037` (FIFO dequeue), `:2171-2176` RAM permit, `:2178-2188` pooled or `posix_memalign(BLOCK_SIZE=4096)` buffer (`:62`), sized `align_up(frame + tail_slack, 1 MiB)` (`:1035-1039`) | | CONFIRMED |
| The copy | `dng_save` `:1116`; 14/16-bit rows "copy verbatim, one active row each" `:1423-1434` via `write_pod` = `std::memcpy` (`cinepi/ifd_builder.hpp:173-181`) | **one full-frame CPU copy camera buffer -> pool buffer** | CONFIRMED |
| Release | `dng_encoder.cpp:2302-2307` `input_done_callback_` -> `encodeBufferDone` pops the request (`cinepi_recorder.hpp:158-172`) -> requeue | camera buffer held until the copy is done, not until disk | CONFIRMED |
| Disk | `dng_encoder.cpp:2314-2400`: comment "Use standard buffered IO instead of O_DIRECT" (`:2351`), `open(O_WRONLY\|O_CREAT\|O_TRUNC)` (`:2352`), `POSIX_FADV_SEQUENTIAL` (`:2356`), **one `write()` of the whole DNG** (`:2360`) | buffered: second copy into the page cache | CONFIRMED |
| History | the copy into a `posix_memalign` buffer is in the initial commit `9748cd0` (`git show 9748cd0:cinepi/dng_encoder.cpp`, lines 719-756); the pool came in `8fe39cc` (2025-10-17) | cinepi-raw never wrote from the camera buffer | CONFIRMED |

**How long cinepi-raw holds a request.** Queue wait for one of 4 encode workers + RAM-permit wait + the `dng_save` copy (+ thumbnail).
Cinemate measured "Encode time per frame 22.2 ms" with no thumbnail for "imx585 4K 16-bit ClearHDR with CineMate Log 12, 25 fps"
(`cinemate/docs/settings-json.md:329-333@d6cc93e`, CONFIRMED); that figure includes the log-curve pass over every sample. For a verbatim
16-bit row copy the hold is probably ~5-8 ms (PROBABLE: one 16.6 MB memcpy, same order as Core's ~4 ms estimate in
`working/clearhdr-compare-notes.md:67`). At the start of each take non-measuring frames wait up to 2 s for the first frame's WhiteLevel
verdict while holding their camera buffers (`dng_encoder.cpp:2219-2233`, CONFIRMED code; effect on drops UNCONFIRMED).

**A caveat if Core copies this pattern.** `encodeBufferDone` pops the *front* of the request queue, "assuming everything is done in order"
(`cinepi_recorder.hpp:158-172`), while 4 encode workers can finish out of order. A worker that finishes frame n+1 first releases frame n's
request while frame n is still being copied (CONFIRMED code; PROBABLE that it rarely bites, because the CFE only overwrites a requeued buffer
one to two frames later).

**DRAM bytes per frame, cinepi-raw (PROBABLE, no write-allocate reads counted):** copy read P + write P, `write()` read P (pool) + write P
(page cache), NVMe DMA read P = 5 x 16.59 = **82.9 MB/frame**. Same as Core today (section 4). So cinepi-raw is not a model for saving
bandwidth; its advantages are elsewhere (one `write()` per DNG instead of ~37 syscalls, CPU pinning, SCHED_FIFO; see `clearhdr-compare-notes.md:54-56`).

## 2. Can O_DIRECT write straight from the camera mapping? (part b)

### 2.1 Where Core's raw buffers come from

- **Core allocates Clear HDR raw buffers itself**, not through libcamera: `allocateCachedBuffers(rawStream_, ...)` when Clear HDR raw is
  unpacked and `APERTAR_RAW_CACHED_DMABUF` is not 0 (`apertar-core/src/camera/CameraController.cpp:6650-6662@f60e301`), with the comment
  "libcamera byte-swaps it and computes raw stats on the CPU every frame, which is too slow on the CFE's uncached buffers" (`:6652-6653`).
  Heaps tried: `/dev/dma_heap/vidbuf_cached`, then `/dev/dma_heap/linux,cma` (`:6736`), `DMA_HEAP_IOCTL_ALLOC` of `frameSize` per buffer
  (`:6738-6750`). CONFIRMED for f60e301; PROBABLE that `d9f00d4` (T23) keeps this with count 8. The Pi's journal says which heap was used
  (`ApertarCore RAW buffers: CPU-cached heap=... count=...`, printed at `:6751-6753`).
- Mapping: `mmap(nullptr, len, PROT_READ, MAP_SHARED, fd, off)` (`CameraController.cpp:7069@f60e301`). CONFIRMED.
- libcamera imports them: the raw stream is External, so the request's buffer is queued straight to the CFE
  (`libcamera-apertar/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:780-806@6b0b49f`) and the BE input imports the same dma-buf.
  If Core fell back to `FrameBufferAllocator`, libcamera would export V4L2 MMAP buffers from the CFE (`pipeline_base.cpp:660-668`), which use
  `vb2_dma_contig_memops` (`kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:1947@5bd564a`) with coherent (uncached) memory. CONFIRMED.
- Both heaps exist in the Pi 5 kernel config: `CONFIG_DMABUF_HEAPS_SYSTEM=y`, `CONFIG_DMABUF_HEAPS_CMA=y`
  (`arch/arm64/configs/bcm2712_defconfig:1497-1499`); the system heap registers as "system" (`drivers/dma-buf/heaps/system_heap.c:434`).
  The 2712 kernel uses **16 KB pages** (`bcm2712_defconfig:50`, `CONFIG_ARM64_16K_PAGES=y`; CONFIRMED for the defconfig, UNCONFIRMED on the Pi: `getconf PAGESIZE`).

### 2.2 How each mapping is built

| Allocator | mmap implementation | VMA flags | Cache | Label |
| --- | --- | --- | --- | --- |
| system heap | `remap_pfn_range` page by page (`drivers/dma-buf/heaps/system_heap.c:201-221`) | `remap_pfn_range` sets `VM_IO \| VM_PFNMAP \| VM_DONTEXPAND \| VM_DONTDUMP` (`mm/memory.c:2672`) and writes special PTEs (`pte_mkspecial`, `mm/memory.c:2561`) | cached, `vm_page_prot` unchanged; CPU access synced per **attachment** (`system_heap.c:159-178`) | CONFIRMED |
| CMA heap | `vm_flags_set(VM_IO \| VM_PFNMAP \| ...)` + fault handler `vmf_insert_pfn` (`drivers/dma-buf/heaps/cma_heap.c:163-191`) | VM_IO \| VM_PFNMAP | cached | CONFIRMED (this tree no longer uses `vm_insert_page` for CMA) |
| CFE V4L2 export (fallback) | `vb2_dc_mmap` -> `dma_mmap_attrs` (`drivers/media/common/videobuf2/videobuf2-dma-contig.c:275-296`) -> `iommu_dma_mmap`: `vm_map_pages` for remapped IOMMU allocations, else `remap_pfn_range` (`drivers/iommu/dma-iommu.c:1732-1760`); `dma_direct_mmap` -> `remap_pfn_range` (`kernel/dma/direct.c:542-564`) | normal pages possible with the IOMMU path | **uncached** (`dma_pgprot`, non-coherent device: no `dma-coherent` anywhere in the bcm2712/rp1 DT, grep empty) | CONFIRMED code; which branch runs is UNCONFIRMED |
| udmabuf fd itself | `vm_flags_set(VM_PFNMAP ...)` + `vmf_insert_pfn` (`drivers/dma-buf/udmabuf.c:55,62-71`) | VM_PFNMAP | cached | CONFIRMED |
| the **memfd** behind a udmabuf | ordinary shmem mapping | none of the above | cached | PROBABLE (standard shmem) |

There is no in-kernel shortcut: `dma_buf_fops` has no `read_iter`, `splice_read` or `copy_file_range` (`drivers/dma-buf/dma-buf.c:525-533`),
and `dma_buf_mmap_internal` hands the VMA straight to the exporter (`dma-buf.c:147-166`). CONFIRMED.

### 2.3 What O_DIRECT does with such a pointer

1. `exfat_file_write_iter`: for `IOCB_DIRECT`, `pos | iov_iter_alignment(iter)` must be aligned to `i_blocksize` or the device's logical
   block size, else `-EINVAL` (`fs/exfat/file.c:601-609`); then `__generic_file_write_iter` (`file.c:622`). CONFIRMED.
2. `generic_file_direct_write` -> `exfat_direct_IO` -> `blockdev_direct_IO(..., exfat_get_block)` (`mm/filemap.c:4168-4169`,
   `fs/exfat/inode.c:492-506`). CONFIRMED.
3. `dio_refill_pages` -> `iov_iter_extract_pages` (`fs/direct-io.c:166-199`) -> `pin_user_pages_fast` (`lib/iov_iter.c:1796-1821`). CONFIRMED.
4. The lockless fast path bails out on special PTEs (`mm/gup.c:2973`, `pte_special` -> `pte_unmap`), the slow path calls
   `check_vma_flags`, which returns **`-EFAULT` for `VM_IO | VM_PFNMAP`** (`mm/gup.c:1270-1278`). CONFIRMED.
5. On the first refill nothing is mapped yet, so the error comes back without writing (`direct-io.c:174-198`; the ZERO_PAGE branch needs
   `blocks_available`), and `__generic_file_write_iter` returns it without a buffered fallback because `ret < 0` (`mm/filemap.c:4177-4178`).
   PROBABLE (code reading; I did not trace `do_direct_IO` ordering line by line).

**Result: `write()` with `O_DIRECT` from Core's raw mapping (or cinepi-raw's) fails with `EFAULT`.** CONFIRMED as a code path; one smaps
reading on the Pi confirms the flags (experiment E1). This also explains, PROBABLY, why cinepi-raw's dead O_DIRECT trial (`f7bc43e`,
deleted `1475f78`, `clearhdr-compare-notes.md:78`) wrote from its `posix_memalign` pool and not from the camera buffer.

Upstream status (UNCONFIRMED: search-result summaries only, lkml mirrors and lore are not reachable from this container): a 2024 series
"Support direct I/O read and write for memory allocated by dmabuf" was answered by the dma-buf maintainer that direct I/O is intentionally
disabled on dma-bufs (https://lkml.iu.edu/hypermail/linux/kernel/2407.1/03923.html); a 2025 series adds `DMA_BUF_IOCTL_RW_FILE` for the
system heap and refuses buffers that have attachments (https://lkml.rescloud.iu.edu/2505.2/00291.html). Our buffers always have two
attachments (CFE, BE), and 6.12 has neither.

### 2.4 A buffered write from the same mapping works

`generic_perform_write` pre-faults with `fault_in_iov_iter_readable` (`mm/filemap.c:4072`), which is plain `unsafe_get_user` per page
(`mm/gup.c:2230-2255`), and copies with `copy_folio_from_iter_atomic` (`filemap.c:4094`), i.e. `copy_from_user`. Uaccess works on any
present user PTE, PFN-mapped or not (the system heap populates all PTEs at mmap time; the CMA heap faults them in). CONFIRMED code path;
PROBABLE end result (not run). The CPU still reads the buffer, so Core's `DMA_BUF_SYNC_START/END (READ)` stays (`CameraController.cpp:6763-6786`).

### 2.5 The way to a real zero-copy O_DIRECT: udmabuf

- `CONFIG_UDMABUF=y` (`bcm2712_defconfig:1496`); limits: `size_limit_mb = 64` (`udmabuf.c:23`, 16.9 MB fits), memfd must carry
  `F_SEAL_SHRINK` and not `F_SEAL_WRITE` (`udmabuf.c:253-254`); one sg entry per page (`udmabuf.c:127`): 16,896,000 / 16,384 = 1031.25 -> 1,032
  entries per buffer. CPU sync is done once, on udmabuf's own device (`udmabuf.c:205-237`). CONFIRMED.
- libcamera already has the allocation recipe (`libcamera-apertar/src/libcamera/dma_buf_allocator.cpp:132-161@6b0b49f`: memfd with
  `Seal::Shrink`, `UDMABUF_CREATE`), but it closes the memfd; Core needs its own copy of this that keeps the memfd and mmaps **it** (the
  udmabuf fd's own mmap is `VM_PFNMAP`). CONFIRMED code; PROBABLE design.
- Import: the CFE needs DMA-contiguous buffers (`videobuf2-dma-contig.c:717` "contiguous chunk is too small") but sits behind an IOMMU
  (`&csi0`/`&csi1` `iommus = <&iommu5>`, `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts:243-250`), as does the BE (`pisp_be`
  `iommus = <&iommu2>`, `bcm2712-ds.dtsi:386-394`); `CONFIG_BCM2712_IOMMU=y` (`bcm2712_defconfig:1551`). Core's system-heap buffers are already
  non-contiguous and work, so a udmabuf should import the same way. CONFIRMED DT/config; PROBABLE import; UNCONFIRMED in practice.
- O_DIRECT alignment: Core writes from `mapping + stride x activeTopRows`; activeTopRows = ((2200 - 2160) / 2) & ~1 = 20
  (`CameraController.cpp:3016-3026`), so 20 x 7680 = 153,600 B = 300 x 512 = 37.5 x 4096. Aligned for a **512-byte** logical block size,
  not for 4096 (PROBABLE; stride 7680 and the NVMe's logical block size are UNCONFIRMED). The file offset must also be aligned: Core's
  f60e301 layout is 8-byte header + payload + pad + IFD at the end (`CdngEncoder.cpp:1769-1777`), so the payload sits at file offset 8; an
  IFD-first layout with `StripOffsets = 4096` is needed (as T24 plans, `clearhdr-compare-notes.md:51`: 16,588,800 = 4050 x 4096). CONFIRMED arithmetic.
- `/dev/udmabuf` permissions on Raspberry Pi OS: UNCONFIRMED (the sys-mods `99-com.rules` I opened grants `dma_heap` to group video, and
  has no udmabuf line: https://raw.githubusercontent.com/RPi-Distro/raspberrypi-sys-mods/master/etc.armhf/udev/rules.d/99-com.rules). A udev
  rule (Patrik, sudo) may be needed.

## 3. The buffer budget at 30 fps with 8 buffers (part c)

### 3.1 Who holds a raw buffer

- **CFE: two per frame period.** At frame start the driver promotes `next_frm` to `cur_frm` (`rp1_cfe/cfe.c:688-689`) and, if every enabled
  node (image, embedded, stats, config) has a queued buffer, programs the next job at once (`cfe.c:613-644`, `:812-813`); a buffer queued
  later is programmed on arrival (`cfe.c:1034-1050`). So a buffer is held as "next" for ~T (33.3 ms) and as "current" for the readout time.
  CONFIRMED code; readout time UNCONFIRMED (Clear HDR VMAX 4500 at HMAX 550 spans the whole 33.3 ms frame, README 22:10 checkpoint).
- **libcamera's other CFE pools are not the limit:** stats and config 12 each (`pisp.cpp:1629@6b0b49f`), embedded 12 (`pisp.cpp:1286-1293`).
  libcamera also allocates max(2, 4 - 8) = 2 internal raw buffers (`pisp.cpp:1269-1277`), but with an External raw stream they sit in
  `availableBuffers_` (`rpi_stream.cpp:67-73`) and are only queued for requests without a raw buffer (`rpi_stream.cpp:124-161`,
  `queueAllBuffers` skips External streams `:223-229`). Core's requests always carry one, so the CFE pool is exactly Core's 8. CONFIRMED code; PROBABLE for d9f00d4.
- **libcamera pipeline:** one frame at a time (`tryRunPipeline` only when `Idle`, `pisp.cpp:3112-3116`); the raw buffer returns to the app
  only when its request completes (`pipeline_base.cpp:1465-1500, 1525-1545`). CONFIRMED.
- **Core:** T25 holds from `requestComplete` to the end of its worker's copy, at most buffers-2 (brief §2, UNCONFIRMED here).

| Holder | Residence per frame | Buffers = residence / 33.3 ms | Label |
| --- | --- | --- | --- |
| CFE "next" | ~33.3 ms | 1.0 | PROBABLE |
| CFE "current" (readout) | <= 33.3 ms | <= 1.0 | PROBABLE |
| libcamera when it keeps up (preview-only medians: swap 6.1 + stats 5.8 + BE 13.4 ms + IPA, `lessons/hardware-log.md:184-190`) | ~30 ms | ~0.9 | PROBABLE |
| Core, T25 copy (sync ~4 + memcpy ~4 ms, `clearhdr-compare-notes.md:67`, + worker wake) | ~8-10 ms | ~0.3 | PROBABLE |
| Core, O_DIRECT from the camera buffer (P / 733 MB/s = 16,588,800 / 733e6 = 22.6 ms, `hardware-log.md:69`, + exFAT and syscall overhead) | ~25 ms mean | ~0.75 | PROBABLE |
| Core, buffered write from the camera buffer (one 16.6 MB copy into the page cache + exFAT buffer-head work) | ~8-15 ms | ~0.3-0.45 | PROBABLE |

Keeping up: 2 + 0.9 + 0.3 = 3.2 buffers in use, **4.8 slack** today; with an O_DIRECT hold 2 + 0.9 + 0.75 = 3.65, **4.35 slack**, enough
for an NVMe/exFAT stall of 4.35 x 33.3 = ~145 ms. NVMe load at 30 fps: 30 x 16.59 = 498 MB/s = 68 % of the measured 733 MB/s (PROBABLE).

### 3.2 Would holding for the write make today's starvation worse?

Model (PROBABLE): the buffers form a closed loop CFE -> libcamera queue -> BE -> Core -> CFE. When the libcamera stage is slower than the
sensor (period Pp > T), its queue absorbs every spare buffer, the CFE runs out once per (T / (Pp - T)) frames and skips exactly one frame,
and delivery equals 1/Pp whatever the buffer count. Buffer count and Core's hold only set **when the first gap comes**:
first gap ~ slack / ((Pp - T) / T) frames.

Check against the measurements: before L1, 26.45 fps -> Pp = 37.8 ms, deficit (37.8 - 33.3) / 33.3 = 0.135 buffer per frame; 4.8 / 0.135 =
**36 frames**, measured first gap after **27-47** frames (`hardware-log.md:165`). Gaps of exactly one frame every 5-9 frames vs predicted every
1 / 0.135 = 7.4 frames. Both match, so the model holds (PROBABLE).

So, with L1 (27.6-28.8 fps: Pp = 36.2-34.7 ms, deficit 0.087-0.042 per frame), an O_DIRECT hold (+0.45 buffer) moves the first gap
0.45 / 0.087 = ~5 to 0.45 / 0.042 = ~11 frames earlier and adds ~0.45 lost frames per take (5 x 0.087). **Negligible next to what the
bandwidth relief can buy** (section 4), provided Core caps its in-flight writes: if a stall lets Core hold more than 8 - 2 (CFE) - 1 (BE) -
1 (margin) = **4** buffers, it should drop that frame itself (counted as `dropped_queue_full`) rather than starve the CFE. T25's cap of
buffers-2 = 6 is too loose for a write hold (PROBABLE). Cinemate runs 10 buffers on exFAT for this reason ("absorb transient disk-write
latency spikes", `storage_profiles.py:32-38`, CONFIRMED comment).

What does make the starvation worse: anything that slows the libcamera stage. The hold itself does not, the DRAM traffic of the writer does
(IPC on the CameraManager thread 1.87 -> 1.30 while recording, `hardware-log.md:159-164`).

## 4. What each option saves (part d)

### 4.1 Core's current writer (f60e301; PROBABLE that d9f00d4 differs only in where the copy runs)

1. `copyRawBytes`: `DMA_BUF_SYNC_START|READ`, `memcpy` of P from the mapping into a `std::vector`, `SYNC_END` (`CameraController.cpp:6763-6786`),
   called from `recordRawFrame` after the capacity check (`:7265-7269`). Size: stride x 2160 from row 20 (`:7224-7236`, `:3028-3033`).
2. `writeRawPayload`: chunk = max(rowBytes, min(4 MiB, max(256 KiB, 64 x rowBytes))) = max(7680, min(4,194,304, max(262,144, 491,520))) =
   **491,520 B** (`CdngEncoder.cpp:1867-1871`); each 16-bit row is `memcpy`'d into that scratch (`:1044-1045`, `:1887-1899`) and flushed with
   `writeAll` -> `::write` (`:462-480`): 16,588,800 / 491,520 = 33.75 -> **34 payload writes**, plus header, pad and IFD (`:1769-1777`).
3. Buffered open, `POSIX_FADV_SEQUENTIAL` (`:1748-1758`), `POSIX_FADV_DONTNEED` before close (`:1779`). DONTNEED starts async writeback and
   invalidates only pages that are already clean (`mm/fadvise.c:113-160`, `mapping_try_invalidate`), so pages still under writeback stay
   cached and are reclaimed later (CONFIRMED code; PROBABLE effect; E3 measures it).
4. exFAT buffered writes go through `block_write_begin` with buffer heads at the filesystem's sector size (`fs/exfat/inode.c:449-458`,
   `super.c:434` `sb_set_blocksize(sb, logical_sect)`), writeback through `mpage_writepages` (`inode.c:429-435`). With 512-byte sectors and
   16 KB pages that is 32 buffer heads per page, 16,588,800 / 512 = 32,400 per frame (CONFIRMED code; sector size UNCONFIRMED).

Measured CPU: while recording at 30 fps, "Five other Core threads at 18-20 % each" (`hardware-log.md:164`) = ~0.95 core = 0.95 / 26.45 fps
= **~36 ms of CPU per delivered frame**, beside libcamera's thread (CONFIRMED measurement; that these are the cDNG workers is PROBABLE).

### 4.2 Bytes and CPU per option

DRAM bytes per frame, P = 16.59 MB, write-allocate reads not counted (they would add up to P per CPU store stream: UNCONFIRMED whether the
A76 streams these stores without allocating). The 491,520 B scratch is counted as cache-resident (PROBABLE).

| Option | Pixel copies by the CPU | DRAM read | DRAM write | Total / frame | At 30 fps | Saved vs today | Camera buffer hold | Works on 6.12? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Today (f60e301 writer) | 3: memcpy, scratch, page cache | camera P + vector P + NVMe P | vector P + page cache P | 5P = **82.9 MB** | 2.49 GB/s | - | copy, ~8-10 ms | yes |
| cinepi-raw (for reference) | 2: pool, page cache | camera P + pool P + NVMe P | pool P + page cache P | 5P = 82.9 MB | 2.49 GB/s | 0 | copy, ~5-8 ms (+ queue) | yes |
| A. zero-copy + buffered | 1: page cache | camera P + NVMe P | page cache P | 3P = **49.8 MB** | 1.49 GB/s | **33.2 MB, 1.0 GB/s** | `write()`, ~8-15 ms | yes (sec. 2.4) |
| B1. zero-copy + O_DIRECT, heap buffers | 0 | - | - | - | - | - | - | **no, EFAULT** (sec. 2.3) |
| B2. zero-copy + O_DIRECT, udmabuf buffers | 0 | NVMe P | 0 | 1P = **16.6 MB** | 0.50 GB/s | **66.4 MB, 2.0 GB/s** | write, ~25 ms (+ stalls) | PROBABLE, untested |
| C. copy + O_DIRECT (T24) | 1: memcpy into an aligned buffer | camera P + NVMe P | aligned buffer P | 3P = **49.8 MB** | 1.49 GB/s | **33.2 MB, 1.0 GB/s** | copy, ~8-10 ms (as today) | yes (exFAT direct I/O, sec. 2.3 steps 1-2) |

CPU per frame (PROBABLE, scaled from the ~4 ms memcpy / ~4 ms sync estimates and the ~36 ms measured above):

- **A** drops the vector memcpy (~4 ms) and the scratch copy (~3-4 ms), keeps the sync pair (~4 ms), the page-cache copy, exFAT buffer heads,
  writeback and later reclaim. T22 tied exactly this page-cache path to lost frames: idle `dd` buffered 24.63 fps / 3 long intervals vs
  `dd` O_DIRECT 24.99 fps / 0 (`hardware-log.md:69,77-78,87`, CONFIRMED measurement).
- **C** keeps the memcpy and the sync pair (~8 ms on the worker), drops the scratch copy, the page cache, buffer heads, writeback, DONTNEED and
  reclaim; the worker sleeps in the I/O. Expected Core CPU ~10-12 ms per frame instead of ~36 (PROBABLE).
- **B2** drops every CPU pass over the pixels and the sync pair (the CPU never reads them; the NVMe DMA mapping cleans caches itself); expected
  Core CPU ~1-3 ms per frame (header/IFD, syscalls) (PROBABLE).

### 4.3 Which saves the most bytes for the least holding?

| Option | MB saved per frame | Extra hold vs today | MB saved per extra buffer held | Verdict |
| --- | --- | --- | --- | --- |
| C | 33.2 | ~0 | unbounded | **best ratio; do first (T24)** |
| A | 33.2 | +0-0.15 buffer | >= 220 | dominated by C (same bytes, keeps the page cache, holds longer) |
| B2 | 66.4 | +0.45 buffer | ~148 | **most bytes; second step**, needs udmabuf allocation + IFD-first layout + a hold cap |

Placed in the whole budget (PROBABLE): q1 sums ~163 MB/frame with Core counted as 33.8 (copy) + 16.9 (NVMe) (`q1-backend.md:126-130`);
Core's writer actually moves ~83 MB, so the total is ~163 + 33 = **~196 MB/frame (5.9 GB/s)**. C removes 17 % of it, B2 34 %. For scale,
LPDDR4X-4267 on a 32-bit bus peaks at 4267e6 x 4 = 17.1 GB/s; reported STREAM Copy on a Pi 5 is 5.4-7.8 GB/s (UNCONFIRMED: a forum figure
seen only as a search summary, https://discourse.zynthian.org/t/speed-fix-for-pi-5-8gb-memory-about-20-faster/11158). Q3 owns the budget.

Preview-only (no Core copy, no write, no NVMe) already delivers 30.00 fps with 0 gaps (`hardware-log.md:159-162` and brief §3, CONFIRMED). Recording
adds ~83 MB/frame of Core traffic; C removes 33 of the 83 (40 %), B2 removes 66 (80 %; the 16.6 MB NVMe read remains). If loss scales with
the added traffic (a linear guess, PROBABLE at best), C would take today's 7-20 missing per 287 to ~4-12, B2 to ~1-4.

## 5. Notes that matter for the other questions

- **Q4 (swap).** Fusing libcamera's swap into Core's copy is not possible on its own: the BE and the stats need the swapped data, and they
  read the buffer before Core sees it. A swap fused into option C would only work if the BE accepted big-endian input (Q4's question). PROBABLE.
- **Sync cost.** Every `DMA_BUF_IOCTL_SYNC` on a system-heap buffer runs the cache maintenance once per mapped attachment
  (`system_heap.c:170-174`); our raw buffers are attached to the CFE and the BE, so Core's READ sync and libcamera's RW syncs around the swap
  (`pisp.cpp:2218-2223`, helpers `:320-342`) and stats (`:3055-3061`, `:3088-3109`, worker `:816-833`) each walk 16.9 MB twice (PROBABLE:
  whether both attachments stay mapped between frames is UNCONFIRMED). A udmabuf syncs once, on its own device (`udmabuf.c:205-237`).
- **cinepi-raw's 10 buffers on exFAT** (`storage_profiles.py:73-82`) are 2 more than Core's 8; each extra 16.9 MB buffer is 0.5 frame period
  (~33 ms) more tolerance for a stall (PROBABLE). On a 4 GB Pi, 2 x 16.9 MB = 33.8 MB.

## Experiments this suggests

Patrik runs anything with sudo; builds run on the Pi. `PID=$(pidof apertar-core)` below.

**E1. Confirm the mapping flags (read-only, no change).** While Core runs in Clear HDR:
`awk '/dmabuf/{p=1} p&&/^(Size|VmFlags)/{print} /^VmFlags/{p=0}' /proc/$PID/smaps` and `ls -l /dev/dma_heap/`,
`journalctl -u apertar-core -b | grep 'RAW buffers'`, `getconf PAGESIZE`.
Prediction: at least 8 mappings of Size 16,512 kB (16,896,000 B page-aligned by the heap, `drivers/dma-buf/dma-heap.c:85`:
1,032 x 16,384 = 16,908,288 B) whose `VmFlags` contain **`io pf`** (VM_IO, VM_PFNMAP); Core's 8 are PROT_READ (no `wr`); libcamera's own
maps of the same buffers (for the swap) also show `io pf` plus `wr`; `vidbuf_cached -> system`; PAGESIZE 16384.
Rules out section 2.3: a raw mapping without `pf` (then O_DIRECT from it might work and B1 is worth a test).

**E2. Prove the EFAULT (no Core change; a 20-line test program built on the Pi, writes one file to `/media/RAW`).** Allocate one
16,896,000 B buffer from `/dev/dma_heap/vidbuf_cached`, mmap it, `open(O_WRONLY|O_CREAT|O_DIRECT)` a file on `/media/RAW`, `write()` 4096 B
from the mapping; then the same from a `posix_memalign(4096)` buffer. Prediction: first write -1 / **errno 14 (EFAULT)**, second 4096.
Rules out: the first write succeeds.

**E3. Does Core's page-cache path cost reclaim? (read-only, during one normal 10 s 30 fps take.)**
Before and after: `grep -E '^(pgsteal_kswapd|pgsteal_direct|pgscan_kswapd|nr_dirty|nr_writeback) ' /proc/vmstat; grep -E '^(Cached|MemFree)' /proc/meminfo`.
Prediction: one take writes 287 x 16,590,340 = 4.76 GB = 290,600 pages of 16 KB; if DONTNEED misses pages under writeback, `pgsteal_kswapd`
rises by roughly that many (>= 100,000) and kswapd shows CPU in `top -H`. Rules out the reclaim cost: `pgsteal_*` rises by < 10,000 and
Cached stays flat (DONTNEED does drop the pages).

**E4. Identify the 18-20 % threads (read-only, while recording).** `top -H -b -n 3 -d 2 -p $PID` or `ps -L -o tid,comm,pcpu -p $PID`.
Prediction: five cDNG writer threads at 18-20 % each (~36 ms CPU per frame in total). Rules out "Core's writer CPU is large": they turn out
to be preview/web/H.264 threads.

**E5. T24: copy + O_DIRECT (Core change, build on the Pi).** IFD-first DNG (header + IFD in the first 4096 B, StripOffsets 4096), the T25
copy into a `posix_memalign(4096)` buffer, one `O_DIRECT` write of 4096 + 16,588,800 = 16,592,896 B (4051 x 4096), no DONTNEED; cap Core's
in-flight writes at 4. Measure: `working/tools/takes.sh 3 10` at 30 fps uncompressed, `hwcount.py` on the CameraManager thread,
`top -H` on Core, E3's counters; optionally one `LIBCAMERA_LOG_LEVELS=RPI:0` window with `libcam_stages.py`.
Prediction: Core writer CPU from ~0.95 core to <= 0.4; CameraManager IPC from 1.30 back towards 1.5+; missing per take from 7-20 (L1) to
<= 12, delivery >= 28.8 fps; files byte-identical in pixel data (compare with `dng_validate` or a raw hash of the strip). Rules out "Core's
page-cache traffic slows the pipeline": missing and IPC unchanged within take-to-take spread (C0089-C0091 ranged 7-20, so run >= 5 takes).

**E6. Option A vs C, cheaply (only if E5 is ambiguous).** Same build with a switch: payload `write()` straight from the camera mapping
(buffered, no vector copy). Prediction: fewer missing than today but more than E5, and `pgsteal_kswapd` behaves as in E3. Rules out the
page-cache cost: A equals C.

**E7. udmabuf feasibility (read-only first, then a prototype).** Read-only: `ls -l /dev/udmabuf; cat /sys/module/udmabuf/parameters/size_limit_mb;
cat /sys/block/nvme0n1/queue/logical_block_size; cat /sys/block/nvme0n1/queue/dma_alignment`. Prediction: `/dev/udmabuf` exists (built in),
size_limit_mb 64, logical_block_size 512 (then Core's 153,600 B source offset is aligned; with 4096 the payload must start at row 0 of the
buffer or the copy-free path needs a 2-row shift). Prototype: allocate the 8 raw buffers as memfd + `UDMABUF_CREATE` (recipe in libcamera's
`dma_buf_allocator.cpp:132-161`), keep and mmap the memfd, O_DIRECT from it. Prediction: libcamera starts and swaps/stats normally (CFE and BE
import through their IOMMUs), DNGs identical, Core writer CPU <= 0.15 core, missing <= 4 per take if the BE is memory-bound. Rules out B2:
`VIDIOC_QBUF` fails ("contiguous chunk is too small" in dmesg) or the O_DIRECT write from the memfd still returns EFAULT/EINVAL.

## Unknowns

- Whether `d9f00d4` still has f60e301's writer (scratch chunks, DONTNEED, buffered open) and the cached-heap allocation; the T25 hold cap.
  Needs the Mac's `clearhdr-fixes` branch.
- `vidbuf_cached` target, page size, NVMe logical block size, exFAT sector size, `/dev/udmabuf` permissions (E1, E7).
- Whether the CFE and BE import a udmabuf in practice, and whether the BCM2712 IOMMUs add cost with 1,032 x 16 KB entries per buffer (E7).
- The real readout time of a Clear HDR frame (sets whether the CFE holds 1.5 or 2 buffers).
- Whether the A76 store streams in `memcpy` and `copy_from_user` allocate in cache (adds up to P per CPU write stream to every row of the table).
- How many attachments are mapped when Core and libcamera sync (doubles or not the sync cost).
- Pi 5 DRAM bandwidth under this access mix (Q3), and therefore how much of the remaining 1.2-2.4 fps a 33 or 66 MB/frame saving buys.
- Upstream dma-buf direct-I/O work: only search summaries were available here (lore and lkml mirrors unreachable).

## Verification

Verifier (cloud session, Claude Opus 5.5), 2026-10-26. Every cited line was re-opened at the cited commit (`git show f60e301:<path>` for
Core; working trees for cinepi-raw `63a08d5`, cinemate `d6cc93e`, libcamera-apertar `6b0b49f`, kernel-rpi `5bd564a`; `fs/proc` added to the
kernel sparse checkout for the smaps mnemonics). Every number was recomputed. Web: `raw.githubusercontent.com` was reachable; lkml.iu.edu,
lkml.rescloud.iu.edu, lore.kernel.org, lists.linaro.org, discourse.zynthian.org, raspberrypi.com and jeffgeerling.com all failed DNS from this
container, so those claims rest on search-result summaries only. Verdicts: CONFIRMED / CORRECTED / REFUTED / UNVERIFIABLE (needs the Pi or an unreachable page).

| # | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | cinepi-raw is not zero-copy: dng_save memcpys every row into pool memory | CONFIRMED | cinepi-raw/cinepi/dng_encoder.cpp:1423-1434@63a08d5, cinepi/ifd_builder.hpp:173-181@63a08d5 |
| 2 | Buffers from `dma_heap_.alloc` + mmap RW/SHARED; heap order vidbuf_cached then linux,cma, comment "system heap (Pi 5)" | CONFIRMED (Pi link target UNVERIFIABLE) | cinepi-raw/core/rpicam_app.cpp:1141-1162@63a08d5, core/dma_heaps.cpp:20-29@63a08d5 |
| 3 | Count default 6, `--buffer-count` overrides, raw follows stream 0; Cinemate passes 8 or 10 (exFAT/NTFS) | CONFIRMED | rpicam_app.cpp:630-632,657@63a08d5; cinemate/src/module/storage_profiles.py:59,72,82,93@d6cc93e; src/module/cinepi_multi.py:845-866@d6cc93e |
| 4 | Hand-off: BufferWriteSync START\|RW, END in destructor, push request, raw pointer to EncodeBuffer2; enqueue without copy | CONFIRMED | cinepi/cinepi_recorder.hpp:68,103,105@63a08d5; core/buffer_sync.cpp:16-47@63a08d5; dng_encoder.cpp:455-483@63a08d5 |
| 5 | Worker: FIFO dequeue, RAM permit, pooled or posix_memalign(4096), size align_up(frame+slack, 1 MiB) | CONFIRMED | dng_encoder.cpp:2013-2037, 2171-2197, 62, 1035-1039@63a08d5 |
| 6 | Camera buffer released after the copy, before disk | CONFIRMED (lines are 2303-2308, not 2302-2307) | dng_encoder.cpp:2303-2308@63a08d5 |
| 7 | Disk thread: buffered open, FADV_SEQUENTIAL, one write() | CONFIRMED | dng_encoder.cpp:2351-2360@63a08d5 |
| 8 | Copy into posix_memalign since initial commit; pool from 8fe39cc (2025-10-17) | CONFIRMED | `git show 9748cd0:cinepi/dng_encoder.cpp` 719-757; `git show -s 8fe39cc` |
| 9 | Cinemate "22.2 ms" encode, 4K 16-bit Clear HDR, CineMate Log 12, 25 fps | CONFIRMED | cinemate/docs/settings-json.md:329,333@d6cc93e |
| 10 | Non-measuring frames wait up to 2 s for the WhiteLevel verdict while holding camera buffers | CONFIRMED | dng_encoder.cpp:2219-2233 (wait_for 2 s :2222), release only at :2304@63a08d5 |
| 11 | encodeBufferDone pops the front regardless of which worker finished | CONFIRMED | cinepi_recorder.hpp:158-172@63a08d5 |
| 12 | cinepi-raw DRAM traffic = 5P = 82.9 MB/frame, same as Core | CORRECTED (minor) | 5 x 16.5888 = 82.94 MB holds for the verbatim 16-bit path only. Cinemate's measured mode (row 9) writes 12-bit Log: 317.0 MB/s / 25 = 12.68 MB/frame ~ 0.75P (settings-json.md:333). Then copy read P + 4 x 0.75P = 4P = 66.4 MB. Conclusion "not a model for saving bandwidth" stands |
| 13 | Core allocates Clear HDR raw buffers itself from vidbuf_cached / linux,cma; prints heap | CONFIRMED (gate also requires `recordingCapabilities().rawCompression`, :6654) | apertar-core/src/camera/CameraController.cpp:6650-6662, 6729-6760@f60e301 |
| 14 | Core maps PROT_READ, MAP_SHARED | CONFIRMED | CameraController.cpp:7069@f60e301 |
| 15 | External raw stream: request buffer queued straight to the CFE; FrameBufferAllocator fallback exports CFE MMAP (vb2_dma_contig) | CONFIRMED | libcamera-apertar/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:780-809, 660-670@6b0b49f; kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:1947@5bd564a |
| 16 | Heaps built in, system heap named "system", 16 KB pages | CONFIRMED (Pi page size UNVERIFIABLE) | kernel-rpi/arch/arm64/configs/bcm2712_defconfig:50,1497-1499; drivers/dma-buf/heaps/system_heap.c:434@5bd564a |
| 17 | System heap mmap = remap_pfn_range: VM_IO\|VM_PFNMAP, special PTEs, cached; sync per mapped attachment | CONFIRMED | system_heap.c:159-221; mm/memory.c:2561,2672@5bd564a |
| 18 | CMA heap mmap sets VM_IO\|VM_PFNMAP, faults with vmf_insert_pfn | CONFIRMED | drivers/dma-buf/heaps/cma_heap.c:163-191@5bd564a |
| 19 | CFE export mmap chain; uncached; no `dma-coherent` in bcm2712/rp1 DT | CONFIRMED (which branch runs UNVERIFIABLE) | videobuf2-dma-contig.c:275-296; drivers/iommu/dma-iommu.c:1732-1761; kernel/dma/direct.c:542-564; grep of arch/arm64/boot/dts/broadcom/{bcm2712*,rp1*} empty@5bd564a |
| 20 | udmabuf fd's own mmap is VM_PFNMAP + vmf_insert_pfn | CONFIRMED | drivers/dma-buf/udmabuf.c:42-73@5bd564a |
| 21 | dma_buf_fops has no read_iter/splice/copy_file_range; mmap goes to exporter | CONFIRMED | drivers/dma-buf/dma-buf.c:147-166, 525-533@5bd564a |
| 22 | exFAT O_DIRECT: (pos \| iov alignment) must match i_blocksize or bdev LBS, else -EINVAL | CONFIRMED | fs/exfat/file.c:601-609,622@5bd564a |
| 23 | exfat_direct_IO -> blockdev_direct_IO(exfat_get_block) | CONFIRMED (filemap.c:4168-4169 is the call into generic_file_direct_write) | fs/exfat/inode.c:492-506; mm/filemap.c:4168-4169@5bd564a |
| 24 | dio_refill_pages -> iov_iter_extract_pages -> pin_user_pages_fast | CONFIRMED | fs/direct-io.c:166-199; lib/iov_iter.c:1796-1823@5bd564a |
| 25 | GUP fast path bails on special PTEs; check_vma_flags returns -EFAULT for VM_IO\|VM_PFNMAP | CONFIRMED | mm/gup.c:2973-2974, 1270-1278@5bd564a |
| 26 | First refill fails before any block is mapped, error returned, no buffered fallback (report: PROBABLE) | CONFIRMED (upgrade) | fs/direct-io.c:175 (ZERO_PAGE branch needs blocks_available), :915-918 (dio_get_page first in the loop), :1243-1253, :267-273 (EFAULT ignored only if bytes transferred); mm/filemap.c:4177-4178@5bd564a |
| 27 | O_DIRECT write() from Core's (or cinepi-raw's) heap mapping returns EFAULT (B1 impossible) | CONFIRMED as code path (runtime: E2) | rows 17, 18, 22-26 |
| 28 | cinepi-raw's dead O_DIRECT trial wrote from its "posix_memalign pool" | CORRECTED (minor) | Per-frame posix_memalign with BLOCK_SIZE 4096*16, not a pool: `git show f7bc43e:cinepi/__dng_encoder.cpp` lines 38, 779, 823, 829 |
| 29 | Upstream: 2024 dma-buf direct-I/O series rejected as "intentionally disabled"; 2025 DMA_BUF_IOCTL_RW_FILE refuses buffers with attachments | UNVERIFIABLE (pages unreachable; search summaries agree, and add that the 2025 series was also called a "no-go") | URLs as cited; "6.12 has neither" is CONFIRMED: `git show 5bd564a:include/uapi/linux/dma-buf.h` defines only SYNC, SET_NAME, EXPORT/IMPORT_SYNC_FILE |
| 30 | Buffered write from the PFN mapping works (fault_in_readable + copy_folio_from_iter_atomic) | CONFIRMED code (runtime UNVERIFIABLE) | mm/filemap.c:4072,4094; mm/gup.c:2230-2257@5bd564a |
| 31 | udmabuf: =y, size_limit_mb 64, F_SEAL_SHRINK wanted / WRITE denied, one sg entry per page, 16,896,000/16,384 = 1031.25 -> 1032, CPU sync on own device | CONFIRMED | bcm2712_defconfig:1496; udmabuf.c:23,126-130,205-239,253-254@5bd564a |
| 32 | libcamera's udmabuf recipe closes the memfd | CONFIRMED | libcamera-apertar/src/libcamera/dma_buf_allocator.cpp:132-161@6b0b49f |
| 33 | CFE (iommu5) and BE (iommu2) behind IOMMUs; vb2 "contiguous chunk is too small"; "a udmabuf should import the same way" | CONFIRMED DT/config; import PROBABLE; see Missed 1 | arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts:244-250, bcm2712-ds.dtsi:386-394; bcm2712_defconfig:1551; videobuf2-dma-contig.c:717@5bd564a |
| 34 | activeTopRows = ((2200-2160)/2) & ~1 = 20; 20 x 7680 = 153,600 = 300 x 512 = 37.5 x 4096 | CONFIRMED (stride 7680 UNVERIFIABLE) | CameraController.cpp:3016-3026@f60e301 |
| 35 | f60e301 layout: 8-byte header, payload at offset 8, pad, IFD last; 16,588,800 = 4050 x 4096 | CONFIRMED | src/cdng/CdngEncoder.cpp:1740-1777@f60e301 |
| 36 | sys-mods 99-com.rules grants dma_heap to group video, no udmabuf line | CONFIRMED (the file has `SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"` and no vidbuf_cached or udmabuf line) | https://raw.githubusercontent.com/RPi-Distro/raspberrypi-sys-mods/master/etc.armhf/udev/rules.d/99-com.rules |
| 37 | CFE holds "next" and "current"; next job programmed at SOF or on queue | CONFIRMED | rp1_cfe/cfe.c:613-644, 688-689, 711, 812-813, 1028-1050@5bd564a |
| 38 | Stats/config 12, embedded 12; internal raw max(2, 4-8) = 2, unused when every request carries a raw buffer | CONFIRMED (4u-8u as int = -4, max = 2) | pisp.cpp:1270-1295, 1629@6b0b49f; rpi_stream.cpp:67-73, 124-161, 223-229@6b0b49f |
| 39 | One frame at a time (Idle only); raw buffer returns at request completion | CONFIRMED | pisp.cpp:3112-3117; pipeline_base.cpp:1465-1500, 1525-1542@6b0b49f |
| 40 | Residence table; 2 + 0.9 + 0.3 = 3.2 (slack 4.8); 2 + 0.9 + 0.75 = 3.65 (slack 4.35); 4.35 x 33.3 = 145 ms | CONFIRMED arithmetic (inputs PROBABLE; 6.1+5.8+13.4 = 25.3 ms + IPA, hardware-log.md:187-190; 9/33.3 = 0.27; 25/33.3 = 0.75) | lessons/hardware-log.md:187-190 |
| 41 | NVMe load 30 x 16.59 = 498 MB/s = 68 % of 733 MB/s; O_DIRECT hold 16,588,800/733e6 = 22.6 ms | CONFIRMED arithmetic (497.7/733 = 67.9 %; with T22's other run, 759 MB/s, 21.9 ms) | hardware-log.md:69; tutorials/inbox/...T22 clearhdr-drops-measure.md:37 |
| 42 | Closed-loop model: 26.45 fps -> 37.8 ms, deficit 0.135, first gap 4.8/0.135 = 36 (measured 27-47), gap every 7.4 (measured 5-9) | CONFIRMED arithmetic; model PROBABLE and stronger than stated (see Missed 2) | hardware-log.md:162,165-166 |
| 43 | With L1 (34.7-36.2 ms, deficit 0.042-0.087), +0.45 buffer hold moves first gap 5-11 frames earlier, ~0.45 frames more lost | CONFIRMED arithmetic (0.45/0.087 = 5.2, 0.45/0.0417 = 10.8, 5.2 x 0.087 = 0.45) | hardware-log.md:209-210 |
| 44 | Hold cap 8-2-1-1 = 4; T25's buffers-2 = 6 too loose for a write hold | CONFIRMED arithmetic (cap from brief §2, code not here) | handoff-30fps-clearhdr16.md:29-31 |
| 45 | Cinemate: 10 buffers on exFAT "absorb transient disk-write latency spikes" | CONFIRMED | storage_profiles.py:32-35@d6cc93e |
| 46 | Core writer: copyRawBytes; chunk max(7680, min(4 MiB, max(256 KiB, 491,520))) = 491,520; 16,588,800/491,520 = 33.75 -> 34 writes | CONFIRMED | CameraController.cpp:6762-6786, 7224-7236, 7265-7269@f60e301; CdngEncoder.cpp:462-483, 1044-1045, 1861-1909@f60e301 |
| 47 | DONTNEED starts async writeback, invalidates only clean pages | CONFIRMED | mm/fadvise.c:113-160@5bd564a |
| 48 | exFAT buffer heads at fs sector size; 16,384/512 = 32 per page, 16,588,800/512 = 32,400 per frame | CONFIRMED (blocksize = max(device LBS, exFAT sector), set only when larger: super.c:430-434) | fs/exfat/inode.c:429-436, 449-458; fs/exfat/super.c:430-434@5bd564a |
| 49 | 5 Core threads x 18-20 % = 0.95 core; 0.95/26.45 = 36 ms CPU per frame | CONFIRMED (measurement and arithmetic, 35.9 ms; thread identity PROBABLE) | hardware-log.md:164 |
| 50 | Bytes table: today/cinepi 5P = 82.9 MB (2.49 GB/s); A and C 3P = 49.8 (1.49); B2 1P = 16.6 (0.50); saved 33.2 (1.0 GB/s) / 66.4 (2.0 GB/s) | CONFIRMED arithmetic (82.94 x 30 = 2.488; 49.77 x 30 = 1.493; 16.59 x 30 = 0.498) | report §4.2 |
| 51 | T22: buffered dd cost frames, O_DIRECT dd did not | CONFIRMED, and stronger than cited: the earlier pair is 561 MB/s buffered -> 21.71 fps, 19 gaps vs 759 MB/s direct -> 25.00 fps, 0 gaps, both to `/media/RAW/x` (exFAT), so exFAT O_DIRECT is already shown in practice | hardware-log.md:69,77-78,87; tutorials/inbox/20261026041000 ... T22 clearhdr-drops-measure.md:36-37; working/handoff-mac-cinemate-compare.md:28 |
| 52 | Ratio table: C unbounded, A 33.2/0.15 = 221, B2 66.4/0.45 = 148 | CONFIRMED arithmetic | report §4.3 |
| 53 | Whole budget 163 - 50.7 + 82.9 = ~196 MB/frame (5.9 GB/s); C 17 %, B2 34 % | CONFIRMED arithmetic (195.4 MB; 5.86 GB/s; 16.9 %; 34.0 %) | working/research-30fps/q1-backend.md:127-128 |
| 54 | LPDDR4X-4267 x 4 B = 17.1 GB/s peak | UNVERIFIABLE spec (raspberrypi.com unreachable); arithmetic correct (17.07 GB/s) | - |
| 55 | Pi 5 STREAM Copy 5.4-7.8 GB/s | UNVERIFIABLE (page unreachable). Search summary: 5,384 -> 7,792 MB/s are one 8 GB Pi 5 before / after `SDRAM_BANKLOW=1`, i.e. a firmware setting, not a spread | https://discourse.zynthian.org/t/speed-fix-for-pi-5-8gb-memory-about-20-faster/11158 (summary only) |
| 56 | Preview only: 30.00 fps, 0 gaps | CONFIRMED | hardware-log.md:161; handoff-30fps-clearhdr16.md:43 |
| 57 | Linear guess: C takes 7-20 missing to ~4-12, B2 to ~1-4 | CORRECTED | Arithmetic right (x0.6, x0.2), but it contradicts the report's own §3.2 model, which predicts missing ~ N x deficit - slack. That model reproduces L1 exactly: 287 x 0.0417 - 4.8 = 7.2, 287 x 0.0453 - 4.8 = 8.2, 287 x 0.087 - 4.8 = 20.2 vs measured 7/8/20 (hardware-log.md:209-210). With the same "excess period scales with Core traffic" assumption (excess 1.39-2.90 ms over 33.33): C -> 34.16-35.07 ms, deficit 0.025-0.052, **2.4-10.2** missing per take; B2 -> 33.61-33.91 ms, deficit 0.0083-0.0174, **0-0.2** per 10 s take but still one gap every 57-120 frames in a long take |
| 58 | Swap cannot be fused into Core's copy (BE and stats read the buffer first) | CONFIRMED | pisp.cpp:2218-2223 (swap in the CFE dequeue path, before the BE)@6b0b49f |
| 59 | Each DMA_BUF sync walks every mapped attachment | CONFIRMED code ("twice" UNVERIFIABLE) | system_heap.c:170-174, 191-195@5bd564a |
| 60 | cinepi-raw's 10 buffers: "each extra 16.9 MB buffer is 0.5 frame period (~33 ms)"; 2 x 16.9 = 33.8 MB | CORRECTED | One buffer = one frame period = 33.3 ms at 30 fps (2 extra = 66.7 ms). Cinemate's count also sizes the video/lores stream, "~25 MB of CMA at 4K" per buffer (storage_profiles.py:36-37), so ~50 MB there; 33.8 MB is right for Core's raw-only buffers. Exfat profile is storage_profiles.py:74-83, not 73-82 |
| 61 | E1: Size 16,512 kB (PAGE_ALIGN: 1032 x 16,384 = 16,908,288 B); VmFlags `io pf`, no `wr` for Core | CONFIRMED | drivers/dma-buf/dma-heap.c:85; fs/proc/task_mmu.c:942,946,950,952@5bd564a ("wr", "mw", "pf", "io") |
| 62 | E3: 287 x 16,590,340 = 4.76 GB = 290,600 pages of 16 KB | CONFIRMED (4,761,427,580 B / 16,384 = 290,614) | - |
| 63 | E5: 4096 + 16,588,800 = 16,592,896 = 4051 x 4096 | CONFIRMED | - |
| 64 | E7: with 4096-byte LBS "a 2-row shift" makes the source aligned | CORRECTED | 7680 = 2^9 x 15, so rows must be a multiple of 8 (8 x 7680 = 61,440 = 15 x 4096). Top row 18 or 22 gives 138,240 or 168,960 B = 33.75 or 41.25 x 4096 (unaligned); top row 16 or 24 (a **4-row** shift) is needed |
| 65 | vidbuf_cached target, page size, NVMe LBS, exFAT sector size, stride on the Pi | UNVERIFIABLE | E1/E7 commands as given |
| 66 | Per-option CPU (A keeps sync + page cache; C ~10-12 ms; B2 ~1-3 ms) | UNVERIFIABLE (PROBABLE reasoning; E4/E5) | - |

Counts: 66 claims. CONFIRMED 56, CORRECTED 5 (#12, #28, #57, #60, #64), REFUTED 0, UNVERIFIABLE 5 (#29, #54, #55, #65, #66).
One label upgraded (#26, PROBABLE -> CONFIRMED), which makes B1's "impossible" verdict fully code-backed.

### Corrections that change substance

- **#57, loss predictions.** The report's own closed-loop model, not a linear guess, should set the predictions: it fits all three L1 takes to
  within 0.2 frames. Under it, C gives about 2-10 missing per 10 s take and B2 about 0, but neither is shown to reach a zero deficit. With
  ~4.8 buffers of slack, a 10 s take hides any per-frame deficit below 4.8 / 287 = 0.0167 (period < 33.9 ms). E5 and E7 therefore cannot
  falsify "still losing frames" with 10 s takes. Use takes of 60 s or more and report the steady-state gap interval: 1/deficit frames.
- **#64, E7 alignment.** For a 4096-byte logical block, the zero-copy source needs a top-row offset that is a multiple of 8 (16 or 24), not
  a 2-row shift. That changes the crop by 4 rows or needs an IFD-first file whose strip starts 4 rows earlier.
- **#60.** One extra buffer is one frame period (33.3 ms), not half. Cinemate's 2 extra buffers give 66.7 ms of stall tolerance and cost
  ~50 MB of CMA, because the count also sizes the video stream.
- (#12 and #28 are minor and leave the conclusions as they are.)

### Missed

1. **udmabuf moves the cost to the IOMMU, on the stage most likely to be the bottleneck.** The system heap allocates order-8 then order-4
   chunks (4 MB / 256 KB with 16 KB pages; drivers/dma-buf/heaps/system_heap.c:47-55@5bd564a, whose comment says this reduces IOMMU TLB
   pressure). The BCM2712 IOMMU tags its PTEs as big, super or huge pages only when `iova | pa | bytes` is aligned
   (drivers/iommu/bcm2712-iommu.c:264, 318-323@5bd564a). A udmabuf gives 1,032 separate 16 KB entries (udmabuf.c:126-128), so the CFE and
   the back end (the probable limit after L2) would read through many more IOMMU TLB entries (PROBABLE mechanism; the cost is
   UNVERIFIABLE). B2 should stay second, and only on condition: E7 must include a `LIBCAMERA_LOG_LEVELS=RPI:0` window and fall if BE
   start->done rises compared with heap buffers.
2. **The §3.2 model is stronger than the report claims.** missing ~ 287 x deficit - 4.8 reproduces C0089-C0091 (7/8/20). That supports
   "the hold only moves the first gap", and it also means that "0 lost frames" is a statement about the period (< 33.33 ms), never about a
   10 s count (see #57).
3. **exFAT O_DIRECT already works on this Pi.** T22's `dd ... of=/media/RAW/x oflag=direct` ran at 759 MB/s with 0 gaps, against 561 MB/s
   buffered at 21.71 fps with 19 gaps (T22 tutorial:36-37). This is a stronger, file-level case for C than the 733/24.63 pair the report cites.
4. **`/dev/udmabuf` is probably root-only.** The misc device is registered without `.mode` (udmabuf.c:503-507@5bd564a), and sys-mods has no
   rule for it (#36). Core (uid 1000) needs a udev rule from Patrik first. Read-only check: `ls -l /dev/udmabuf`.
5. **Firmware memory tuning.** The 5.4-7.8 GB/s STREAM spread is reportedly `SDRAM_BANKLOW` off/on (UNCONFIRMED, search summary). The
   report's ~5.9 GB/s budget sits above the untuned figure. Read-only: `sudo rpi-eeprom-config | grep -i sdram; vcgencmd bootloader_version`
   (Patrik). The result sets how much C's 1.0 GB/s or B2's 2.0 GB/s buys.

Net: the ranking holds and gets stronger. C (T24: copy + O_DIRECT, IFD-first) stays first: the code and the T22 measurement back it, and it
needs no new allocator. B2 drops to "second, only if E7 shows no BE slowdown".
