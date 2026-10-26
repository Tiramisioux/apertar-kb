# critic — completeness gaps in the Core vs Cinemate raw-path comparison

Scope: the original questions A/B/C checked against the verified findings of readers a1-a4, b1-b3, c1-c2
(files in this directory). Listed here: sub-questions still unanswered, answered as UNKNOWN without a usable
reason/pointer, or answered without a source citation. Each gap is at most two sentences plus a "where" line.
Every file/line anchor below was opened or grepped on 2026-10-26 at the stated checkouts (apertar-core f60e301,
cinepi-raw 63a08d5, cinemate d6cc93e, cinemate-handbook c99ff77, libcamera(cinemate) bfe0b76, libcamera(qbc) 7e9fef0,
kernel-rpi 5bd564a sparse checkout: files outside drivers/media/platform/raspberrypi/rp1_cfe are read with
`git -C /home/user/tiramisioux/kernel-rpi show HEAD:<path>`). The critic does not answer the questions.

## A. Writer, kernel tuning, Cinemate history, O_DIRECT design facts

**G1. Which filesystem is on Apertar's /media/RAW is never established, although it decides O_DIRECT support and
alignment and whether the Cinemate exFAT/NTFS evidence transfers.** No reader states it; the task gives only the path.
Where: apertar-core/src/ApertarCoreApp.cpp:10647 (`command.string("filesystem").value_or("exfat")`, Core's format
command default), :2023-2050 (`isMountedPath` :2023 and `mountedDeviceForPath` :2040 parse the `/proc/mounts` type field, :2026/:2043), :3546-3557
(embedded python `get_filesystem_type` branches ntfs/ext4/exfat); apertar-kb/llm/core-map.md and architecture/ui.md
(grep -i exfat) for any statement about the rig; on the Pi only `findmnt /media/RAW` settles it.

**G2. The kernel-side effect of Core's per-frame `posix_fadvise(POSIX_FADV_DONTNEED)` (does it start async
writeback of each 16.6 MB DNG immediately, unlike cinepi-raw's SEQUENTIAL-only path) was not examined.** This is the
one syscall that differs between the two buffered writers and is a candidate Open-A/B mechanism.
Where: kernel-rpi `git show HEAD:mm/fadvise.c` :108-130 (case POSIX_FADV_DONTNEED :113, `__filemap_fdatawrite_range(...,
WB_SYNC_NONE)` :114-115, `invalidate_mapping_pages` comment :126); apertar-core/src/cdng/CdngEncoder.cpp:1779 and
src/lossydng/LossyDngEncoder.cpp:82; cinepi-raw/cinepi/dng_encoder.cpp:2356 (SEQUENTIAL only).

**G3. The stock `vm.dirty_*` values that Cinemate's cushions replace are stated from memory ("PROBABLE kernel
defaults 20/10/500/3000", a2 A10 #3) with no citation.** They are citable from the kernel tree already on disk;
Pi OS sysctl.d overrides remain unknowable locally and should be said so explicitly.
Where: kernel-rpi `git show HEAD:mm/page-writeback.c` :74 (`dirty_background_ratio = 10`), :91 (`vm_dirty_ratio = 20`),
:102 (`dirty_writeback_interval = 5 * 100`), :109 (`dirty_expire_interval = 30 * 100`).

**G4. The claims that `irqaffinity=` does not move managed NVMe queue IRQs and that `isolcpus=managed_irq` keeps them
off CPU 3 (a2 F14 "kernel-knowledge caveats, not from source") are uncited.** They bear on whether Cinemate's
`rq_affinity=2` and `irqaffinity=0-2` do anything for NVMe completions.
Where: kernel-rpi `git show HEAD:Documentation/admin-guide/kernel-parameters.txt` :2399 (`irqaffinity=`) and :2436
(`isolcpus=`, managed_irq flag text); `git show HEAD:kernel/irq/manage.c` (grep -n -i managed, 18 hits).

**G5. The O_DIRECT "error handling" and alignment-unit facts asked for in A were not delivered: no reader says what
alignment O_DIRECT actually requires on the rig (logical block size, not 4096), what exFAT or an ntfs-3g/fuseblk mount
returns for O_DIRECT, or how cinepi-raw's dead O_DIRECT encoder handled an open/write failure.** a4 covers Core's
layout and the unaligned head/tail; a1 cites the dead encoder's open flags but not its failure path (no reader
mentions EINVAL or a fallback).
Where: kernel-rpi `git show HEAD:block/fops.c` :38-41 (`blkdev_dio_invalid`, `bdev_logical_block_size`), :373;
`git show HEAD:fs/exfat/inode.c` :492-506 (`exfat_direct_IO` -> `blockdev_direct_IO`); `git show HEAD:fs/fuse/file.c`
:1577-1618 (`fuse_direct_io`, FOPEN_DIRECT_IO); `git -C cinepi-raw show f7bc43e:cinepi/__dng_encoder.cpp` :823-834
(open O_DIRECT :823, write :827-829, commented ftruncate :832, close/free :833-834) and whatever follows a failed write there.

**G6. Whether the storage-automount cushions and block tuning were actually in force during the handbook's recorded
runs (E1 2026-08-27/28, the 2026-09-13/14/15 cost measurements) and which NTFS driver the daemon mounted (ntfs-3g via
fuseblk vs kernel ntfs3) is not stated, so "disk slow" in E1 may be a FUSE property rather than an NVMe one.**
hardware-log.md says `storage-automount` was active (:570) and `/media/RAW` was "NTFS via fuseblk" (:967) but no reader
connects the two.
Where: cinemate/services/storage-automount/storage-automount.py:212-232 (`def _get_filesystem_info` :212, fstype :224-232),
:343-349 (`_mount_options`), :390-392 (ntfsfix repair), :703-705 ("`mount --move` is unsupported for FUSE mounts such as
ntfs-3g"); cinemate-handbook/lessons/hardware-log.md:570, :967, :256-264.

**G7. "Did Cinemate ever record frames-drop-when-the-disk-is-busy and the fix" is answered for the cause of E1 but not
for its fix: nothing says whether the move from NTFS (2026-08-27/28) to exFAT (2026-08-31) was the recorded remedy or
whether a 16-bit multi-minute soak was ever re-run clean.** The per-cell results the entry relies on
(`RATE-MATRIX-RESULTS.md`, `OVERSEER-NOTES-R4.md`) are not in any local repository (find returns nothing), which should
be stated as the reason the fps/drop numbers of those takes are UNKNOWN.
Where: cinemate-handbook/lessons/hardware-log.md:945-987 (E1; deliverable names :951-952), :1065-1072 and :1106-1112
(2026-08-31 colour rig "exFAT NVMe at `/media/RAW`"), grep -n -i 'soak' after :1000; `find cinemate cinemate-handbook
cinepi-raw -iname '*RATE-MATRIX*'`.

**G8. "Upstream O_DIRECT remains UNKNOWN" (a1) carries no reason or pointer.** The local clone names its upstream and
has no other remote, which is the reason to give, and the two commit messages carry no rationale.
Where: cinepi-raw/README.md:5 ("Fork of rpicam-apps that builds upon the rpicam-raw app"); `git -C cinepi-raw remote -v`
(only Tiramisioux/cinepi-raw); `git show -s 9748cd0` ("Initial commit (start fresh)"), `git show -s 1475f78`
("fix dual sensor recording"); cinepi-raw/cinepi/dng_encoder.cpp:2351.

**G9. Core itself contains a buffered-write stimulus of exactly the Open-A kind that no reader checked: the media
speed test runs `fio --direct=1` and falls back to a buffered `dd if=/dev/zero ... conv=fdatasync` when fio is absent,
guarded only by mount and free-space checks.** Whether fio is installed on the Pi and whether the test can run while
the camera streams (or ran during any Open-A take) is unexamined.
Where: apertar-core/src/ApertarCoreApp.cpp:8973-9024 (`startMediaSpeedTest`, guards :8985-9002), :9028-9052
(`runMediaSpeedTest`: fio :9036-9044, dd fallback :9046-9052); grep -n startMediaSpeedTest for the UI call sites.

## B. Buffers, completion path, 16-bit swap and statistics, plan for Core

**G10. Every B finding about "Cinemate's libcamera fork" is about checkout bfe0b76, yet the handbook records that
Cinemate's camera runs a libcamera working tree with uncommitted edits (a live 580 MHz overclock in controller.cpp and a
~1008-line imx585.json rewrite) and that the colour rig was at commit 3c7b9ab on 2026-08-31.** No reader states which
libcamera Cinemate's Pi actually runs or that bfe0b76 may differ from it.
Where: cinemate-handbook/open-threads.md:358-388 ("The Pi's libcamera checkout carries work that exists nowhere else",
table :367-372); lessons/hardware-log.md:1068-1070 ("libcamera cinemate @ 3c7b9ab ... STASHED"); `git -C libcamera
cat-file -t 3c7b9ab` (present) and `git -C libcamera log --oneline 3c7b9ab..bfe0b76 -- src/libcamera/pipeline/rpi`.

**G11. Question B is posed "at 4K Clear HDR 30 fps", but every Cinemate measurement cited is at 25 fps (2026-09-13/14/15)
or at the 21/21.99 fps cap; the only 30 fps 16-bit takes (the 1782 Mbps cells of 2026-08-27/28) are reported as "clean"
without fps or drop counts.** No reader says that a Cinemate 30 fps 4K Clear HDR recording measurement does not exist
locally.
Where: cinemate-handbook/lessons/hardware-log.md:958-959 ("1782 Mbps ... clean on 16/16 short takes"), :969-970
("30.00 @1782"), :3155 (list-cameras 30 fps vs GUI 21); grep -n -E '30 fps|30\.00' lessons/hardware-log.md.

**G12. The rig behind each cited handbook number is never stated: all measurements are on a CM5 / CM5 Lite 4 GB
(the dated entries: mono imx585 rig for 2026-08-26..30, colour CM5 Lite rig from 2026-08-31; the log is not in date order), not a Pi 5, and the cost tables of 2026-09-13/14 are colour at
25 fps.** Transferability of the 22.2 ms encode and 21.9-27.7 ms preview-stage numbers to Apertar's Pi 5 depends on it.
Where: cinemate-handbook/lessons/hardware-log.md:947 (mono CM5), :1067 and :1108 (colour rig, CM5 Lite 4 GB, 1782 Mbps,
rp1-overclock ON, driver cinemate-7modes @ e9d5759), :2228-2231 ("imx585 colour ... 25 fps"); grep -n '^\*\*Tested:\*\*'.

**G13. "If not, how does it get stats or AE in 16-bit" is answered for AE/AWB (manual) but b2 A3 leaves "other
consumers such as ALSC not traced": which IPA algorithms still run on the unreliable 16-bit hardware statistics on
Cinemate, what they drive in the BE (lores/MJPEG/HDMI preview) and whether any DNG colour tag depends on them.**
Where: libcamera(cinemate)/src/ipa/rpi/pisp/pisp.cpp:353-383 (applyBlackLevel :356, applyWBG :358-, applyContrast :375,
applyCCM :379, applyLensShading :383), :518-641; src/ipa/rpi/common/ipa_base.cpp:491-542 (`processStats` ->
`controller_.process` :510); cinepi-raw/cinepi/dng_encoder.cpp:1660-1665 (ColorMatrix1/2, AsShotNeutral sources).

**G14. "Why does ours need the swap at all" rests on the kernel's `csi_dt = 0` workaround whose introducing commit and
rationale b2 A2 could not read because kernel-rpi is a one-commit clone; a depth-1000 fetch is permitted and would settle
it.** Until then the CSI2AXI/big-endian explanation stays PROBABLE.
Where: `git -C /home/user/tiramisioux/kernel-rpi fetch --depth=1000 origin rpi-6.12.y` then `git log -S 'Avoid RP1 HW
mismatch' -- drivers/media/platform/raspberrypi/rp1_cfe/cfe_fmts.h`; cfe_fmts.h:200/:208/:216/:224 (Bayer16 csi_dt 0),
:286 (Y16 keeps RAW16); cfe.c:854-858, csi2.c:346.

**G15. No reader traces the mechanism that turns a late pipeline thread into the observed single-frame gap: what
rp1-cfe does when a node's dma_queue is empty at frame start, and how libcamera accounts the skipped frame.** This is the
structural link between "two CPU passes on the pipeline thread" / "buffered dd" and "one frame missing every 7-10".
Where: kernel-rpi/drivers/media/platform/raspberrypi/rp1_cfe/cfe.c:615-631 ("has no buffer, unable to schedule job"
:624), :633-660 (`cfe_prepare_next_job`, `job_queued` :635/:711/:812/:1045, `vb.sequence = fs_count - 1` :654),
:551 and :585 (csi2/pisp job scheduling); libcamera(cinemate)/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1837 ("track dropped
frames"), :2329; libcamera(qbc) pisp.cpp:1930-1985 (cfeBufferDequeue, `metadata().sequence` :1985).

**G16. The plan's sizing premise "the CFE needs >= 2 queued requests (one being written, one armed)" (b3 F10) is cited
only to apertar-kb/working/clearhdr-compare-answer.md:123, not to source.** The minimum queue depth follows from the CFE
job scheduler and from how the pipeline handler queues CFE buffers.
Where: kernel-rpi cfe.c:633-660 and :805-815 / :1040-1050 (`!cfe->job_queued && cfe->job_ready`); libcamera(qbc)
src/libcamera/pipeline/rpi/pisp/pisp.cpp (grep -n 'queueBuffer\|cfe_\[' around cfeBufferDequeue :1930) and
src/libcamera/pipeline/rpi/common/rpi_stream.cpp:112 (internal buffers).

**G17. "Preview-buffer cacheability" is left UNKNOWN (b3) although it is derivable from source: Core allocates
previewStream_ through libcamera's FrameBufferAllocator (only raw uses vidbuf_cached), which the RPi pipeline exports
from the V4L2 node's vb2 queue.** It decides whether Core's completion-thread MJPEG downsample reads uncached memory.
Where: apertar-core/src/camera/CameraController.cpp:6650-6661 (`allocator_->allocate(previewStream_)` :6659; cachedRaw
only :6657-6661), :6736 (vidbuf_cached for raw); libcamera(qbc)/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:660-665
(`exportFrameBuffers` -> `dev()->exportBuffers`), rpi_stream.cpp:112; kernel-rpi `git show
HEAD:drivers/media/platform/raspberrypi/pisp_be/pisp_be.c` :1450 (`q->mem_ops = &vb2_dma_contig_memops`) and
rp1_cfe/cfe.c:1947 (same); apertar-core/src/ApertarCoreApp.cpp:8184-8189 (downsampleNearestPlane).

## C. Probe comparison and driver mode metadata

**G18. "At which commit" is answered only for the driver side (b703f46 / 74ed4c6 / 951aeee); the cinepi-raw commits
that added the five-control probe and moved it to core/driver_mode_metadata.hpp, and the cinemate commits that parse
`; binning NxN; mode-crop (l,t)/WxH`, are not dated by any reader.** c2 F1/F2 cite the current code only.
Where: `git -C cinepi-raw log -S 'mode-crop' --format='%h %ad %s' -- core/options.cpp` and `git log --diff-filter=A --
core/driver_mode_metadata.hpp`; `git -C cinemate log -S '_search_labeled_rect' --format='%h %ad %s' -- src/module/sensor_detect.py`
(all return hits).

**G19. cinepi-raw's probe also looks for the optional "Mode Active Left"/"Mode Active Top" pair (imx283 only) and the
handbook has an open thread that the imx585 lacks it and that DNG ActiveArea is verified on the UHD mode only; neither
is cited, so whether an apertar port should expose the Active pair (and drop the 16-bit OB inference) is unaddressed.**
Where: cinemate-handbook/open-threads.md:155-167 ("imx585 does not report its active-picture origin — deferred
2026-09-22"), :169-188 ("DNG `ActiveArea` is verified on the UHD mode only"); cinepi-raw/core/driver_mode_metadata.hpp:96-133,
:355-356; imx585(cinemate-modes)/imx585.c (grep 'Mode Active' = 0 hits).

**G20. The handbook's open thread that nobody confirmed the 16-bit Clear HDR parse fix (0e6899e, 2026-09-25) reached
Cinemate's camera is not cited by c1 F19 (which cites only the test file), so whether Cinemate's camera lists any
16-bit mode today is unaddressed.** It bears on comparing the two probes' outputs on real hardware.
Where: cinemate-handbook/open-threads.md:191-214 (**Evidence** :197-205, **What would settle it** :209-214); cinemate
`git log --oneline | grep 0e6899e`; cinemate/_test/test_clearhdr_16bit_modes_survive_the_probe.py:1-29.

**G21. The "mono" item in C ("anything cinepi-raw does that we miss ... mono") is answered for cinepi-raw's cfa_map /
bayer_formats but Core's side is not stated: whether formatToRawView covers the mono formats, and which cinepi-raw does
not, is left to the reader.** c1 F15 gives only "30-entry table + PISP_COMP1 name match".
Where: apertar-core/src/camera/CameraController.cpp:3126-3190 (`std::array<FormatInfo, 30>` :3138; `BayerPattern::Monochrome`
rows :3139-3144); cinepi-raw/core/options.cpp:38-62 (cfa_map MONO :44, bayer_formats :47-62).

## Appendix — UNKNOWNs that already carry an adequate reason (not counted as gaps)

- libpisp stride alignment and any BE byte-order control: libpisp is not vendored (libcamera*/subprojects/libpisp.wrap only;
  the scratchpad `libpisp` directory holds reader notes, not source); GitHub fetch of raspberrypi/libpisp is not enabled.
- Match of the Pi's libcamera binary ('v0.7.1+qbcfork.20260522') to libcamera(qbc) 7e9fef0 vs tag 33a17ea: hardware only.
- Installed apertar-core.service contents: not in apertar-core (only config/apertar-core-capture-priority.conf:1-3 and
  README.md:232/:238) nor in apertar-kb (grep for apertar-core.service / CPUAffinity / Nice= returns nothing).
- On-hardware durations (CcmpUnwrap, swap, allocation, preview), vidbuf_cached headroom, whether an MJPEG client was
  attached during Open A/B, whether the out-of-order encodeBufferDone pop ever tears a frame: hardware.
- APST write effect and block-queue write success (storage-automount `_write` swallows errors): hardware.
- Date/source of the "102 drops in 20 minutes" report: entered handbook in d1c9822 (2026-09-14) with no origin anywhere.
- Presence of the sysfs assigned-clock-rates path on Apertar's Pi 5; wall-clock cost of Cinemate's two --list-cameras runs;
  whether the P1 WDR transient ever hit Core; whether the sensor honours VST 54 (apertar 1920x1038): hardware.
- Pi OS sysctl.d overrides of the stock dirty values (see G3 for the kernel defaults themselves).

## Method note
Reader files grepped for each candidate term before listing a gap (e.g. 'vidbuf_cached', 'fadvise.c', 'has no buffer',
'open-threads.md:', 'EINVAL', 'speed test', '30.00', 'CM5', '3c7b9ab', '16f8a6c', 'Mode Active'); a candidate was dropped
when a reader already covered it (e.g. cinepi-raw buffers being vidbuf_cached, MLV frameSpace padding, the dead O_DIRECT
encoder's flags, the usb_ssd balance_dirty_pages comment).
