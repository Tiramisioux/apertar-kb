# a4-core-writer — Apertar-Core's two raw writers, as facts for an O_DIRECT design

Reader a4 (THEORY A part 4). Source-only; nothing was run. Every line number below was opened and read
(grep anchor, then a sed window). Repos: apertar-core @ f60e301 (main); libcamera(qbc) @ 7e9fef0 used
only for the signal-delivery question (its match to the Pi binary is probable, not confirmed).
Status words: CONFIRMED = read at the cited line; PROBABLE = inferred, reason given; UNKNOWN = not in source.

## 0. Summary for an O_DIRECT designer

- cDNG uncompressed: open(O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0644) → fadvise(SEQUENTIAL) → write(8-byte TIFF
  header) → 34 write()s of a 491,520-byte row-chunk scratch (16-bit 3840x2160) → write(0-3 pad) → write(IFD,
  variable ~KB) → fadvise(DONTNEED) → close. No fsync. Image data starts at file offset 8, IFD is at the tail.
  File size = 16,588,808 + IFD bytes: NOT a 4096 multiple; image start NOT 4096-aligned. The payload itself is
  exactly 4050 pages (2160 rows) / 4125 pages (2200 rows) and every chunk write is a page multiple.
- cDNG lossless: same open, 8-byte zero placeholder, then one write() per JPEG strip (variable size; 17 strips
  for 2160 rows, 18 for 2200), pwrite() the real header at 0, pad, IFD (contains the 8,192-byte
  LinearizationTable in the 12-bit Clear HDR case), DONTNEED, close. Everything after the first strip is
  unaligned.
- MLV: one file per clip, one worker thread; open writes 9 small blocks (816 bytes), then per frame a 32-byte
  VIDF header write + 34 payload chunk writes (+44/64-byte WBAL/DEBG blocks when WB/CCM change). frameSpace=0,
  so payload offsets drift 32 bytes per frame (first payload at 848). Close patches 4 bytes at offset 36.
  No DONTNEED, no fsync: the whole clip sits in page cache until the kernel writes it back.
- All DNG/MLV file I/O runs on the recorder's worker threads (4 workers uncompressed cDNG, 5 lossless, 1 MLV
  on a 4-core Pi), each with its own CdngEncoder and reused std::vector scratch (malloc-aligned, not
  4096-aligned). No posix_memalign/aligned_alloc anywhere in the cDNG or MLV writers (only LossyDngEncoder
  uses posix_memalign 4096).
- The libcamera completion callback thread (the only producer) does per frame: DMA_BUF_IOCTL_SYNC START,
  memcpy of the raw frame into a pooled std::vector (16.6 MB), SYNC END, and in 12-bit cDNG a 65536-entry LUT
  pass over every sample. It sets itself nice -5 once; encoder workers stay at nice 0 (lossless) / +5 (lossy).
  The systemd drop-in only grants LimitNICE=-5; no CPU affinity, RT policy or ionice anywhere.

## 1. Open flags, writes per frame, fadvise/fsync, close, and thread

### 1a. cDNG uncompressed (CdngEncoder::writeDngFile, worker thread)

CONFIRMED, apertar-core/src/cdng/CdngEncoder.cpp@f60e301 unless noted:
- Open: `int openFlags = O_WRONLY | O_CREAT | O_TRUNC;` :1748, `openFlags |= O_CLOEXEC` under `#ifdef O_CLOEXEC`
  :1749-1751, `::open(path.c_str(), openFlags, 0644)` :1753 (only `if (!lossless)` :1752). A borrowed
  `destinationFd >= 0` is used instead when given (reset with `::ftruncate(destinationFd, 0)` + `::lseek` :1262-1264).
- `::posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL)` :1758 immediately after open.
- Write 1: TIFF header, 8 bytes (`std::array<uint8_t, 8> header`, "II", 42, ifdOffset) :1740-1744, written by
  `writeAll(fd, header.data(), header.size())` :1770.
- Writes 2..N: `writeRawPayload(fd, frame, layout)` :1772 → CdngEncoder::writeRawPayload :1861-1910:
  chunk = `std::max(rowBytes, std::min(4 MiB, std::max(256 KiB, rowBytes * 64)))` :1868-1872 ("4u * 1024u * 1024u",
  "256u * 1024u", "rowBytes) * 64u"); scratch from `takePayloadScratch(targetChunkSize)` :1873; rows are
  converted/copied into the scratch (`writeDngRowBytes(frame, layout, src, dst)` :1897) and flushed with
  `writeAll(fd, scratch.data(), bufferedBytes)` :1880 whenever the next row would not fit
  (`bufferedBytes + layout.rowBytes > scratch.size()` :1890), plus a final `flushScratch()` :1906.
  16-bit unpacked rows are a plain `std::memcpy(dst, src, layout.rowBytes)` :1045-1046.
- Write N+1: padding 0..3 zero bytes `if (ok && paddingSize > 0) ok = writeAll(fd, padding.data(), paddingSize)`
  :1774-1775 (`static constexpr std::array<uint8_t, 3> padding` :1746).
- Write N+2: `writeAll(fd, ifdBytes.data(), ifdBytes.size())` :1776-1777 (main IFD + ExifIFD in one buffer).
- `::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` :1779, then `::close(fd)` :1780 (skipped for a borrowed fd),
  `::unlink(path)` on failure :1786-1787. No fsync/fdatasync/O_SYNC/O_DIRECT in the file (grep over
  CdngEncoder.cpp finds only the two posix_fadvise lines :1758, :1779).
- writeAll = loop of `::write(fd, cursor, remaining)` retrying EINTR, EIO on a zero-length write :462-481.
- Layout constants: `constexpr uint32_t tiffHeaderBytes = 8;` :1387, `const uint32_t stripOffset = tiffHeaderBytes;`
  :1388, `ifdOffset64 = align4(stripOffset + payloadByteCount)` :1390, paddingSize = ifdOffset64 - (8 + payload)
  :1392; `align4` = `(value + 3u) & ~3u` :375-378. StripOffsets tag 273 = stripOffset (8) :1536; RowsPerStrip
  278 = frame.height (`rowsPerStrip = lossless ? losslessTileRows() : frame.height` :1243) :1545; StripByteCounts
  279 = payload :1546. ExifIFD is placed at `align4(ifdOffset + mainIfd.bytes.size())` :1639-1640 and appended
  to the same ifdBytes buffer :1658-1660.
- Thread: `encoder.writeDngFile(job.path, job.frame, job.metadata)` is called inside `dngWorkerLoop()`
  apertar-core/src/camera/CameraController.cpp:3806, :3852@f60e301; each worker owns `CdngEncoder encoder;` :3820.

Numbers (CONFIRMED arithmetic from the constants above):
- 16-bit 3840x2160: rowBytes = 3840*2 = 7,680 (prepareUnpackedLayout `frame.width * 2u` for Bits16 :1853-1855;
  PispCompressed1→Bits16 path also `width * 2u` :1826-1829). Payload = 7,680 * 2,160 = 16,588,800 bytes
  = 4,050 * 4,096 exactly. rowBytes*64 = 491,520 (within 256 KiB..4 MiB) → chunk 491,520 bytes = 64 rows
  = 120 pages. 2,160 rows = 33 full chunks (2,112 rows) + 1 chunk of 48 rows = 368,640 bytes (90 pages)
  → 34 payload write()s. Header 8 + payload 16,588,800 = 16,588,808, divisible by 4 → padding 0.
  Per frame: 36 write() calls (1 header + 34 payload + 1 IFD), 2 posix_fadvise, 1 open, 1 close = 40 syscalls.
  File size = 16,588,808 + IFD bytes (IFD size variable, see §5) → 16,588,808 mod 4096 = 8, so the file is a
  4096 multiple only if the IFD happens to be ≡ 4088 mod 4096. Image data at offset 8: not page-aligned.
- 2200-row crop (3840x2200 16-bit): payload 7,680 * 2,200 = 16,896,000 = 4,125 * 4,096 exactly; 34 full chunks
  (2,176 rows) + 1 chunk of 24 rows = 184,320 bytes (45 pages) → 35 payload writes, 37 write() total; file
  = 16,896,008 + IFD.
- 12-bit Clear HDR uncompressed (codes repacked to 12-bit): rowBytes = packedRowBytes(3840, 12) = 5,760
  (`(width * bits + 7) / 8` :80-83; prepareUnpackedLayout non-16 branch :1856); payload 12,441,600 bytes
  = 3,037.5 pages (NOT a page multiple). Chunk 5,760*64 = 368,640 (90 pages); 33 full + 48 rows = 276,480
  (67.5 pages) → 34 payload writes.

### 1b. cDNG lossless (same function, `lossless` branch)

CONFIRMED, CdngEncoder.cpp@f60e301:
- Open in the lossless branch: `::open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644)` :1272-1273.
- Write 1: `const std::array<uint8_t, 8> placeholder{}` zero header via writeAll :1276-1278 ("Failed to reserve DNG header").
- Per strip/tile: `jpegEncoder_.begin(tileWidth, rowsPerStrip, ...)` :1303-1304, rows appended one at a time
  (`jpegEncoder_.appendRow(target)` :1324/:1329), short last strip padded by re-appending the last row
  `for (uint32_t row = rows; row < rowsPerStrip; ++row) jpegEncoder_.appendRow(jpegSamples_.data())` :1337-1339,
  `const auto &jpeg = jpegEncoder_.finish();` :1340, `stripOffsets.push_back(checkedTiffOffset(8u + payloadByteCount))`
  :1343, `stripByteCounts.push_back(... jpeg.size())` :1344, `writeAll(output.fd, jpeg.data(), jpeg.size())` :1346
  — one write() per strip of variable size; `payloadByteCount += jpeg.size()` :1351.
- rowsPerStrip = `losslessTileRows()` :1243 → APERTAR_CDNG_TILE_ROWS env, default 128, clamp 16..1024 :52-66
  ("return 128u"). tileWidth = width if `frame.width % 16 == 0` else two columns `((frame.width / 2u + 15u) & ~15u)`
  :1246-1247 (3840 % 16 == 0 → one column).
- After the strips: `posix_fadvise(SEQUENTIAL)` :1758 (on the already-open fd), real 8-byte header via
  `::pwrite(fd, header.data() + written, header.size() - written, written)` at offset 0 :1761-1768, then the
  same padding write :1774-1775, IFD write :1777, `POSIX_FADV_DONTNEED` :1779, close :1780.
- Tiles are declared with TileWidth 322 / TileLength 323 / TileOffsets 324 / TileByteCounts 325 :1539-1543;
  Compression 7 :1363. The IFD carries `stripOffsets.size()` LONGs each for 324 and 325 :1542-1543.
- 12-bit Clear HDR adds LinearizationTable 0xC618 with `metadata.linearizationTable.size()` SHORTs :1586-1588;
  the table is `ccmp::expansionTable()` (4096 entries) set in CameraController.cpp:3280-3282@f60e301 when
  `clearHdrStoresCodes12(settings) && sensorFamily == SensorFamily::Imx585`; ClearHdrCcmp.hpp:61-65@f60e301
  (`std::array<uint16_t, 4096>`) → 8,192 bytes in the IFD tail.

Numbers: 3840x2160 → 2160 = 16*128 + 112 → 17 strips (last one padded to 128 rows), 1 column;
write() calls = 1 placeholder + 17 strips + 1 pwrite header + 0/1 padding + 1 IFD = 20–21 per frame.
3840x2200 → 2200 = 17*128 + 24 → 18 strips, 21–22 calls. Strip sizes variable (entropy coded), so strip 2
onward and the IFD are at arbitrary byte offsets.

### 1c. MLV (MlvEncoder, single worker thread)

CONFIRMED, apertar-core/src/mlv/MlvEncoder.cpp@f60e301:
- Open: `int openFlags = O_WRONLY | O_CREAT | O_TRUNC;` :964, `|= O_CLOEXEC` :965-967, `fd_ = ::open(path.c_str(),
  openFlags, 0644)` :968; `::posix_fadvise(fd_, 0, 0, POSIX_FADV_SEQUENTIAL)` :981; then nine block writes in
  order: writeFileHeader(0), writeVersionBlock, writeClockBlocks (RTCI + INFO), writeIdentityBlock,
  writeRawInfoBlock, writePreviewColorBlock, writeExposureBlock, writeWhiteBalanceBlock :982-989.
  Block sizes: MLVI `kFileHeaderSize = 52` :34; VERS `blockSize = 36` :1117; RTCI `std::array<uint8_t,44>` :1092;
  INFO `std::array<uint8_t,272>` :1105; IDNT `16 + 32 + 4 + 32` = 84 :1133; RAWI `16 + 4 + kRawInfoStructSize(160)`
  = 180 :38-39; DEBG/APCM preview colour `std::array<uint8_t, 64>` :1265; EXPO `16+4+4+4+4+8` = 40 :1208;
  WBAL `16 + 28` = 44 :1230. Sum = 816 bytes, 9 write() calls at open.
- Per frame (`MlvEncoder::writeFrame` :1003-1045): optional DEBG (64 B) only when the CCM changed
  (`if (previewColorWritten_ && ccm == lastPreviewCcm_) return;` :1260); optional WBAL (44 B) only when
  kelvin/gains changed :1010-1013; then the VIDF header `std::array<uint8_t, kVidfHeaderSize> header` with
  `kVidfHeaderSize = 32` :40, :1020, `blockSize64 = kVidfHeaderSize + payloadBytes` :1016, `writer.le32(0); // frameSpace`
  :1030, written with writeBytesOrThrow :1033; then `writeRawPayload(frame)` :1035 → MlvEncoder::writeRawPayload
  :862-946 with the identical chunk rule (`4u * 1024u * 1024u`, `256u * 1024u`, `rowBytes) * 64u` :869-873),
  `payloadScratch_` member resized only if smaller :874-875, flush `writeAll(fd_, payloadScratch_.data(), bufferedBytes)`
  :884, 16-bit rows `std::memcpy(dst, src, rawLayout_.rowBytes)` :918-919, final `flushScratch()` :946.
- Close (`MlvEncoder::close` :1047-1062): `patchFrameCount()` → `::lseek(fd_, kFileHeaderVideoFrameCountOffset(36), SEEK_SET)`
  :35, :1282, 4-byte writeAll :1285-1287, `::lseek(fd_, 0, SEEK_END)` :1289, then `::close(fd_)` :1059.
  No POSIX_FADV_DONTNEED and no fsync anywhere in MlvEncoder.cpp (grep: only :981 posix_fadvise).
- writeAll is the same `::write` loop :62-79.
- Thread: `mlvWorkerLoop()` opens the file on first job (`encoder.open(job.path, ...)` CameraController.cpp:3938-3941)
  and writes every frame (`encoder.writeFrame` :3943); the file is closed when the loop returns and the
  stack `MlvEncoder encoder;` :3913 is destroyed (`MlvEncoder::~MlvEncoder() { close(); }` MlvEncoder.cpp:827-830).

Numbers (16-bit 3840x2160): VIDF block = 32 + 16,588,800 = 16,588,832 bytes; frame N's header is at
816 + N*16,588,832 and its payload at 848 + N*16,588,832, i.e. payload offset mod 4096 = (848 + 32*N) mod 4096,
drifting 32 bytes per frame. Per frame 35 write() calls minimum (1 header + 34 chunks); 36–37 when WBAL/DEBG
are emitted. frameSpace is always 0, so no padding exists to realign.

## 2. Memory: allocation, reuse, alignment, per-frame allocations

CONFIRMED, apertar-core/src/camera/CameraController.cpp@f60e301:
- Raw copy: `std::vector<uint8_t> rawCopy = recorder_.acquireRawBuffer(rawSize);` :7268. acquireRawBuffer
  :3657-3681 picks the smallest pooled vector whose `capacity() >= size` from `rawPool_` (`std::vector<std::vector<uint8_t>>`
  :4034); on a miss it returns `std::vector<uint8_t>(size)` :3669 — value-initialised, i.e. a zero-fill of the full
  frame size before the memcpy (PROBABLE cost note: ~16.6 MB memset per pool miss). Reuse: the worker calls
  `recycleRawBuffer(std::move(job.rawBytes))` after the write (:3873 DNG, :3953 MLV); recycle keeps at most
  `preferredRawPoolSize()` = `std::min(maxQueuedFrames_, std::max<size_t>(workerCount_ + 2u, 4u))` :3992-3995
  buffers, refuses buffers > 1.5x the expected size and a byte cap of expected*count :3977-3990.
  Pi 5 (4 threads): uncompressed cDNG pool = min(12, 6) = 6; lossless = min(24, 7) = 7; MLV = min(12, 4) = 4.
- The copy: `copyRawBytes(buffer, rawCopy.data(), mapped.data + activeOffsetBytes, rawSize)` :7269 →
  `DMA_BUF_IOCTL_SYNC` START (`DMA_BUF_SYNC_READ | DMA_BUF_SYNC_START`) when `cachedRawBuffers_` is non-empty,
  `std::memcpy(destination, source, size)`, SYNC END :6762-6786. 12-bit cDNG then runs `compressClearHdrFrame`
  in place on the copy :7272-7275 (65536-entry `ccmp::compressionLut()` per sample :1335-1346; ClearHdrCcmp.hpp:69-83).
  Both run on the completion callback thread (recordRawFrame is called from requestComplete :7000).
- Ownership hand-off: `RawFrameView view; view.data = rawCopy.data(); ...` :7280-7291 (non-owning view), then
  `recorder_.enqueue(std::move(rawCopy), view, std::move(metadata))` :7293. The queue element is
  `struct FrameJob { std::vector<uint8_t> rawBytes; RawFrameView frame; CdngEncoder::Metadata metadata; std::string path; }`
  :3727-3732, pushed into `std::deque<FrameJob> queue_` :3706-3711, :4033. The worker re-points
  `job.frame.data = job.rawBytes.data();` :3839 and passes `const RawFrameView &` to the encoder, which never owns it.
- Alignment: everything is `std::vector<uint8_t>` (malloc alignment, 16 bytes on glibc aarch64 — PROBABLE,
  platform knowledge). No `posix_memalign`/`aligned_alloc`/`alignas` in the cDNG or MLV code; the only hit in src/
  is `::posix_memalign(&ptr, 4096, wanted)` in apertar-core/src/lossydng/LossyDngEncoder.cpp:140@f60e301.
- The "assembled DNG" does not exist as one buffer. Per CdngEncoder instance (one per worker, :3820):
  `mutable std::vector<uint8_t> payloadScratch_` (CdngEncoder.hpp:192) reused via takePayloadScratch/recyclePayloadScratch
  (CdngEncoder.cpp:1198-1209; capacity kept, so steady-state no realloc); `mainIfdScratch_` / `exifScratch_`
  (hpp:195-196) reused via takeReusableBytes/recycleReusableBytes :1438-1449, :1714, :1789; the IFD bytes are a
  cached template (`ifdTemplateCache_.bytes` hpp:169, :1680) copied with `ifdBytes.assign(...)` :1715 and patched
  in place (dates, black levels, timecode, ISO...) :1716-1738. Template rebuild only when `templateMatches()`
  fails :1506-1520, :1634 (first frame, or when strings/layout change); initial reserve 16 KiB main + 512 Exif
  :1636, :1651.
- MLV: `std::vector<uint8_t> payloadScratch_` and `std::vector<uint16_t> rowScratch_` members (MlvEncoder.hpp:60-61),
  grown once and kept :874-877.
- Per-frame allocation count (16-bit uncompressed, warm pools, template hit): large = 0 (raw buffer from pool,
  scratch reused). Small = PROBABLE roughly 6–12: `frameFilename()` ostringstream :3785-3793, path concatenation
  :3711, three metadata string assignments in enqueue :3703-3705, `std::string originalDate = dateTimeString(...)`
  CdngEncoder.cpp:1399, `colorProfileForMetadata` result :1401 (holds a `cacheKey` string, hpp:159), plus whatever
  metadataFromRequest copies into the 10 std::string members of CdngEncoder::Metadata (hpp:44, :75-83; the
  default "Blackmagic Micro Cinema Camera" exceeds SSO). Lossless adds two `std::vector<uint32_t>` for strip
  tables :1248-1249. Exact count UNKNOWN without running.

## 3. Threads, queue depth, queue-full behaviour, counters, log formats

CONFIRMED, CameraController.cpp@f60e301 (class DngRecordingQueue :3358):
- Worker count :3432-3456: `normalWorkerCount = std::max(2u, std::min(4u, hardwareThreads))`; lossless
  `unsignedEnvValue("APERTAR_CDNG_WORKERS", defaultLosslessWorkers, 1, 8)` with default
  `hardwareThreads >= 4 ? std::min(8u, hardwareThreads + 1u) : normalWorkerCount` ("One extra lossless worker
  overlaps tile-write and scheduling stalls" :3440-3441); lossy `APERTAR_LOSSYDNG_WORKERS` default
  `std::max(1u, std::min(4u, hardwareThreads))`; MLV `1u`. Pi 5: uncompressed 4, lossless 5, lossy 4, MLV 1.
  unsignedEnvValue clamps to [min, max] :1051-1063.
- Queue depth :3436-3439: `APERTAR_CDNG_QUEUE_FRAMES`, default `compressedDng && hardwareThreads >= 4 ? 24u : 12u`,
  clamp 4..64; member default `size_t maxQueuedFrames_ = 12;` :4029. Pi 5: uncompressed 12, lossless/lossy 24, MLV 12.
- Queue full: `hasCapacityForFrame(frameIndex)` :3637-3655 returns false when `queue_.size() >= maxQueuedFrames_`,
  increments `droppedFrames_`, calls `dropWarning_->markDropped()`, logs
  `"ApertarCore drop[queue-full]: frame=" ... " dropped_total=" ... " queue=" N "/" M` on the 1st and every 30th
  drop :3647-3653. recordRawFrame checks it BEFORE copying ("reject before copying a full RAW frame" :7263-7266).
  enqueue repeats the check :3688-3698. Frames are therefore dropped at the producer, never blocked.
- Counters: `struct Stats { enqueued, written, droppedQueueFull, discardedOnStop, writeFailures, currentQueueDepth,
  peakQueueDepth, maxQueueDepth }` :3361-3370; atomics `enqueuedFrames_`, `writtenFrames_`, `writeFailures_`
  :4009-4011; `++writeFailures_` on an encoder exception in dngWorkerLoop :3857 and mlvWorkerLoop :3948, followed by
  `failRecording(e.what())` which clears the queue :3958-3967.
- Log lines: at stop :3523-3532 `"ApertarCore recording stats: enqueued=" ... " written=" ... " dropped_queue_full="
  ... " discarded_on_stop=" ... " write_failures=" ... " peak_queue=" P "/" M`; lossless adds
  `"ApertarCore lossless timing: jobs=... avg_wall_ms=... avg_thread_cpu_ms=... avg_wait_or_preempt_ms=... max_wall_ms=... estimated_capacity_fps=..."`
  :3543-3552 and `"ApertarCore lossless phases: jobs=... avg_encode_ms=... avg_payload_write_ms=... avg_container_ms=..."`
  :3555-3560. At record start :3461-3480 `"ApertarCore recording clip: <folder> format=... compression=..."` plus for
  lossless ` worker_nice= workers= queue= tile_rows= encoder=quad_single_pass build=release|debug`.
  Capture-side at stopRecording :5998-6002: `"ApertarCore capture stats: dropped_gap_estimate=" ... " requeue_failures=" ...`
  printed only when either counter is non-zero.
- Side observation: `constexpr unsigned int kActiveRequestCount = 3;` :1048 bounds `requestCount` in makeRequests
  :6795-6801 (`std::min(previewBuffers.size(), activeRequestLimit)` then min with raw buffer count), so with
  4 raw + 4 preview buffers only 3 requests are in flight for raw recording (PROBABLE: depends on the
  processedYuvMode branch being false for raw formats, which :6793 implies).

## 4. Process priorities

CONFIRMED:
- apertar-core/config/apertar-core-capture-priority.conf:1-3@f60e301: `[Service]` and `LimitNICE=-5` only
  ("Permit only a bounded, non-real-time boost for the camera callback thread"). No Nice=, CPUAffinity=,
  CPUSchedulingPolicy=, IOSchedulingClass=, or sysctl in the repo (grep for those names over the repo excluding
  .git hits only this file, the README's `systemctl start/stop apertar-core.service` at README.md:232, :238, and
  the comment at CameraController.cpp:6928). No .service unit is in the repo (find *.service → none); CMake installs
  only the binaries (`install(TARGETS apertar-core RUNTIME DESTINATION bin)` CMakeLists.txt:190-195) — the unit
  and the drop-in's installation are UNKNOWN from this repo (they live on the image).
- apertar-core/scripts/start-apertar-core.sh:1-21@f60e301: resolves the binary, media root and socket path from env,
  optionally exports `LIBCAMERA_RPI_TUNING_FILE` :16-18, then `exec "$CORE_BIN" --socket ... --media ...` :21.
  No nice, chrt, taskset, ionice or sysctl.
- In-process: the only priority calls in src/ are two `::setpriority` (grep for setpriority|sched_setscheduler|
  pthread_setschedparam|sched_setaffinity|pthread_setaffinity_np|SCHED_FIFO|SCHED_RR|ioprio|mlockall):
  1) CameraController.cpp:6925-6936 in `requestComplete(libcamera::Request *)`: once (`capturePriorityAdjusted_`),
     `::setpriority(PRIO_PROCESS, tid, -5)` on the calling thread's tid, logging
     `"ApertarCore capture scheduling: thread=" tid " nice=-5"` or `"normal priority retained (" strerror ")"`;
     comment :6928-6929 "LimitNICE=-5 permits this bounded boost without CAP_SYS_NICE. Only this callback thread
     changes priority, not encoder workers."
  2) CameraController.cpp:3809-3818 in dngWorkerLoop: for lossless cDNG and lossy DNG only,
     `APERTAR_CDNG_WORKER_NICE` (0..19) with default 5 for lossy and 0 for lossless; applied via
     `::setpriority(PRIO_PROCESS, gettid, workerNice)` only `if (workerNice > 0)`. Uncompressed cDNG and MLV
     workers never touch priority.
- Does libcamera's thread get the boost? Core connects with `camera_->requestCompleted.connect(this,
  &CameraSession::requestComplete)` :6698 and CameraSession is not a libcamera::Object (grep finds no
  `libcamera::Object` base). In libcamera(qbc)@7e9fef0 the non-Object connect overload binds with a null Object
  (include/libcamera/base/signal.h:55-62, :75-84 `BoundMethodMember<...>(obj, nullptr, func)`), and
  `activate()` then calls the functor directly on the emitting thread
  (include/libcamera/base/bound_method.h:132-133 `if (!this->object_) return func_(...)`, also :167);
  `Signal::emit` loops the slots synchronously (signal.h:140-148). The emit happens in
  `Camera::requestComplete` (src/libcamera/camera.cpp:1481-1488 `requestCompleted.emit(request)`), called from
  `PipelineHandler::completeRequest` (src/libcamera/pipeline_handler.cpp:584-603). The same structure exists in
  libcamera(cinemate)@bfe0b76 (camera.cpp:1447-1454, pipeline_handler.cpp:548-563). Therefore the nice -5
  lands on the thread that runs the pipeline handler's completion path — CONFIRMED for delivery being
  synchronous in these sources; PROBABLE that this is the same CameraManager thread that performs the
  cfeBufferDequeue rev16 pass (established fact 1), and PROBABLE that the qbc source matches the Pi binary.
  Nothing else (RT class, affinity) is applied to any libcamera thread.

## 5. Facts an O_DIRECT port needs

- Header fixed size: yes, 8 bytes (`tiffHeaderBytes = 8` CdngEncoder.cpp:1387) — but it points at an IFD placed
  AFTER the image (`ifdOffset = align4(8 + payload)` :1390). Image data begins at offset 8 (`stripOffset =
  tiffHeaderBytes` :1388). To write the image with O_DIRECT the layout must change (e.g. IFD first, StripOffsets
  = 4096; TIFF permits any IFD/strip placement — PROBABLE, format knowledge) or the 8-byte head and the IFD tail
  must be written through a separate buffered path (mixing O_DIRECT and buffered I/O on one file is allowed but
  costs cache flushes — PROBABLE, kernel knowledge).
- File size multiples of 4096 (16-bit uncompressed): payload 16,588,800 (2160 rows) and 16,896,000 (2200 rows)
  are both exact page multiples (7,680-byte rows → any row count divisible by 8 is page-aligned), so the only
  unaligned parts are the 8-byte head and the variable IFD tail: total = payload + 8 + IFD. The IFD size is
  variable (ASCII clip/frame names, 54 `ifd.add`/appendAscii statements in :1527-1627, several conditional; six
  9-element SRational matrices = 432 B; 10 Exif entries :1643-1653) — PROBABLE 1.5–3 KiB for 16-bit;
  12-bit Clear HDR adds the 8,192-byte LinearizationTable (:1586-1588, ClearHdrCcmp.hpp:47-65). UNKNOWN exactly
  without running. 12-bit uncompressed payload (12,441,600 B) is 3,037.5 pages, so its tail chunk is unaligned too.
- Chunk writes already page-sized: for 7,680-byte rows the 64-row chunk is 491,520 B = 120 pages and the final
  48-row chunk 368,640 B = 90 pages (2160) / 24-row 184,320 B = 45 pages (2200): the existing chunking could feed
  O_DIRECT unchanged if the scratch were 4096-aligned (it is a std::vector :1873; LossyDngEncoder.cpp:140 shows
  the project already uses posix_memalign 4096 elsewhere) and the file offset started page-aligned.
- Lossless strips are variable-size (`jpeg.size()` :1344-1346) and written one per strip from offset 8 onward;
  the 8-byte header is pwrite()n afterwards (:1763). Every strip boundary and the IFD tail are unaligned: an
  O_DIRECT port must stage strips into an aligned buffer and pad the final write, then truncate/ftruncate or
  write the tail buffered.
- MLV writes many small blocks: 9 blocks (816 B) at open, then per frame a 32-byte VIDF header + 34 chunk
  writes (+44/64-byte WBAL/DEBG blocks), frameSpace = 0 (:1030) so the payload offset drifts 32 B per frame;
  close rewrites 4 bytes at offset 36 (:1282-1287). O_DIRECT needs a staging buffer that assembles
  [VIDF header + frameSpace padding + payload] to a 4096 multiple (MLV's frameSpace field is the format's own
  padding mechanism — PROBABLE, format knowledge; the writer currently emits 0), plus a buffered or RMW path for
  the small header blocks and the frame-count patch.
- Page-cache behaviour today: DNG writers issue POSIX_FADV_DONTNEED after the data write and before close
  (:1779); MLV never does, so a clip's full size stays dirty/cached until kernel writeback.

## Surprises
1. The DNG image strip starts at byte 8 and the IFD is at the end: the file is 8 + 16,588,800 + IFD bytes, never
   page-aligned as a whole, even though the payload is exactly 4,050 pages (CdngEncoder.cpp:1387-1392).
2. There is no assembled-file buffer at all; the payload streams through a 491,520-byte scratch in 34 write()s
   that are already page-multiples (CdngEncoder.cpp:1868-1906).
3. A raw-pool miss allocates `std::vector<uint8_t>(size)` — value-initialised, so a 16.6 MB zero-fill precedes
   the 16.6 MB memcpy on the completion thread (CameraController.cpp:3669, :7268-7269).
4. MLV has no POSIX_FADV_DONTNEED and no fsync; only cDNG drops its pages (MlvEncoder.cpp grep; CdngEncoder.cpp:1779).
5. The nice -5 is applied from inside libcamera's synchronous completion emit, so it boosts libcamera's own
   pipeline/completion thread rather than a Core-owned thread (CameraController.cpp:6925-6936; libcamera(qbc)
   bound_method.h:132-133, camera.cpp:1488).
6. kActiveRequestCount = 3 caps in-flight requests below the 4 allocated buffers (CameraController.cpp:1048, :6795-6801).
7. 12-bit Clear HDR uncompressed cDNG payload is 3,037.5 pages, not a page multiple (5,760-byte rows).

## Unanswered / UNKNOWN
- Exact IFD byte size per mode (depends on clip/frame-name lengths and optional tags); needs a run or a byte count
  of a recorded DNG.
- The installed apertar-core.service unit (Nice=, affinity, IO class): not in the repo; only the LimitNICE drop-in is.
- Whether the Pi's libcamera binary matches libcamera(qbc)@7e9fef0 for the signal-delivery claim (probable only).
- Exact per-frame small-allocation count (needs instrumentation).

## Verification

Adversarial pass over every finding above. Method: each cited file was opened at the cited line on the checkout
(apertar-core @ f60e301, libcamera-qbc @ 7e9fef0, libcamera(cinemate) @ bfe0b76), with `grep -n` anchors and
`sed -n` windows; every byte count was recomputed. Verdicts: CONFIRMED (line exact, content supports the claim,
label honest), CORRECTED (claim stands, citation or detail fixed), REFUTED, UNVERIFIABLE.

### Verdicts per finding

1. **cDNG layout (8-byte header, strip at 8, IFD at tail aligned to 4)** - CONFIRMED.
   `tiffHeaderBytes = 8` / `stripOffset = tiffHeaderBytes` / `ifdOffset64 = align4(...)` at
   apertar-core/src/cdng/CdngEncoder.cpp:1387-1390@f60e301; `align4` at :375-378; `ifd.add(273 ...)` at :1536
   (guarded by `if (!lossless)` at :1535); `exifIfdOffset = ... align4(ifdOffset + mainIfd.bytes.size())` at
   :1639-1640. Recomputed: 8 + 16,588,800 = 16,588,808, which is 8 mod 4096 and 0 mod 4 (pad 0). The
   IFD-first/StripOffsets=4096 remark is correctly labelled probable (format knowledge, not in source).

2. **Uncompressed open/write/close sequence, no fsync** - CONFIRMED.
   `int openFlags = O_WRONLY | O_CREAT | O_TRUNC` :1748, `O_CLOEXEC` under `#ifdef` :1749-1751,
   `::open(path.c_str(), openFlags, 0644)` :1753; `POSIX_FADV_SEQUENTIAL` :1758; header `writeAll` :1770,
   `writeRawPayload` :1772-1773, padding :1774-1775, `ifdBytes` :1776-1777; `POSIX_FADV_DONTNEED` :1779;
   `::close(fd)` :1780; `writeAll` with EINTR retry :462-481. `grep -nE 'fsync|fdatasync|fadvise|O_SYNC|O_DIRECT'`
   over CdngEncoder.cpp returns only :1758 and :1779. Syscall count recomputed: 1 open + 2 fadvise + 1 header +
   34 payload + 1 IFD + 1 close = 40 (pad 0). Two details the reader omitted, neither changes the claim for
   recording: :1753 takes a borrowed `destinationFd` when one is passed, and `::close` is skipped when
   `output.borrowed` (:1780); the only caller that passes an fd is the photo-still path
   (`encoder.writeDngFile(output.path(), dngFrame, dngMetadata, output.fd())`,
   apertar-core/src/camera/CameraController.cpp:5223@f60e301, inside `writeDngStill` with an `AtomicStillFile`),
   while the recording worker passes none (`encoder.writeDngFile(job.path, job.frame, job.metadata)` :3853).
   On any failure the file is unlinked (:1787).

3. **Row-streaming through a reused scratch chunk** - CORRECTED (citations only).
   `targetChunkSize` = max(rowBytes, min(4 MiB, max(256 KiB, rowBytes*64))) at CdngEncoder.cpp:1868-1872 and
   `takePayloadScratch(targetChunkSize)` :1873 - exact. `writeAll(fd, scratch.data(), bufferedBytes)` :1880 -
   exact. The flush condition `bufferedBytes + layout.rowBytes > scratch.size()` is at :1888 and
   `writeDngRowBytes(frame, layout, src, dst)` at :1897, so the window is :1888-1897, not :1890-1897. The 16-bit
   `std::memcpy(dst, src, layout.rowBytes)` is at :1045 (branch opens at :1044), not :1045-1046.
   `layout.rowBytes = frame.bitDepth == RawBitDepth::Bits16 ? frame.width * 2u : packedRowBytes(...)` is at
   :1854-1856, not :1853-1855. Numbers recomputed and all correct: 7,680-byte rows; chunk 491,520 B = 64 rows =
   120 pages; 33 in-loop flushes (rows 64..2112) + final 48 rows (368,640 B = 90 pages) = 34 writes; payload
   16,588,800 B = 4,050 pages; 2200 rows: 34 + 1 x 24 rows (184,320 B = 45 pages) = 35 writes, 16,896,000 B =
   4,125 pages; 12-bit: `packedRowBytes` = (width*bits+7)/8 (:79-82) = 5,760, payload 12,441,600 B = 3,037.5
   pages, chunk 368,640 B, 34 writes.

4. **Lossless path (placeholder, strip writes, pwrite header, 128-row strips)** - CORRECTED (one citation).
   Open `O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644` at :1272-1273 (O_CLOEXEC unconditional here, unlike the
   `#ifdef` at :1749), `placeholder` write :1276-1278 - exact. `jpegEncoder_.finish()` :1341,
   `stripOffsets.push_back(checkedTiffOffset(8u + payloadByteCount))` :1343, strip `writeAll` :1346 - inside
   :1340-1351, exact. Padding rows `appendRow` :1338-1339 - exact (a profiling twin at :1334-1335).
   `::pwrite(fd, header.data() + written, ...)` :1764 inside :1761-1768 - exact. `APERTAR_CDNG_TILE_ROWS`,
   `return 128u`, `parsed < 16 || parsed > 1024` at :52-66 - exact. **Wrong citation:** :1243-1247 is the
   `struct OutputFile` RAII block; `rowsPerStrip = lossless ? losslessTileRows() : frame.height` is at :1237 and
   `tileWidth = frame.width % 16 == 0 ? frame.width : ...` at :1240-1241. Tags 322/323/324/325 at :1540-1543 -
   exact. Numbers recomputed: 2160/128 -> 17 strips (16 full + 112 rows padded), 2200/128 -> 18, strip tables
   17 x 4 x 2 = 136 B, 20-21 / 21-22 write syscalls - correct.

5. **12-bit Clear HDR LinearizationTable and LUT remap on the completion thread** - CONFIRMED.
   `clearHdrStoresCodes12(settings) && sensorFamily == SensorFamily::Imx585` :3280 and
   `out.linearizationTable = std::span<const uint16_t>(ccmp::expansionTable())` :3282 (CameraController.cpp);
   `std::array<uint16_t, 4096> &expansionTable()` apertar-core/src/cdng/ClearHdrCcmp.hpp:61-65@f60e301;
   `std::vector<uint16_t> out(65536)` :73 inside `compressionLut()` :69-73; `ifd.add(0xC618, tiff::Short,
   metadata.linearizationTable.size(), ...)` CdngEncoder.cpp:1586-1588; `compressClearHdrFrame(rawCopy.data(),
   rawCopy.size(), ...)` CameraController.cpp:7275 inside :7272-7275 (guarded by `rawInfo.packing ==
   PixelPacking::Unpacked && unpackedBytesPerSample == 2u && bitDepth == Bits12` :7273-7274); `row[x] =
   lut[row[x]]` :1344 inside :1335-1346. Numbers: 4096 x 2 = 8,192 B; 3840 x 2160 = 8,294,400 lookups.

6. **MLV writer** - CORRECTED (two block-size citations).
   `openFlags = O_WRONLY | O_CREAT | O_TRUNC` apertar-core/src/mlv/MlvEncoder.cpp:964@f60e301, `::open(...,
   0644)` :968; `POSIX_FADV_SEQUENTIAL` :981 then `writeFileHeader(0)` ... `writeWhiteBalanceBlock(metadata)`
   :982-989; `kFileHeaderSize = 52` :34, `kFileHeaderVideoFrameCountOffset = 36` :35, `kRawInfoStructSize = 160`
   :38, `kRawInfoBlockSize = 16 + 4 + kRawInfoStructSize` :39 (= 180), `kVidfHeaderSize = 32` :40;
   `blockSize64 = kVidfHeaderSize + payloadBytes` :1016, `writer.le32(0); // frameSpace` :1030, VIDF header
   write :1033, `writeRawPayload(frame)` :1035; `targetChunkSize` :869-872 and `writeAll(fd_,
   payloadScratch_.data(), bufferedBytes)` :884 - exact; `if (previewColorWritten_ && ccm == lastPreviewCcm_)`
   :1260; `::close(fd_)` :1059. `patchFrameCount` spans :1282-1290: `lseek(..., SEEK_SET)` :1282, 4-byte
   `writeAll` :1287, `lseek(fd_, 0, SEEK_END)` :1290 - the reader's :1282-1289 stops one line short.
   Block sizes: RTCI `std::array<uint8_t,44> rtc` :1090 (fourcc + `le32(rtc.size())` :1092, as cited); INFO
   `std::array<uint8_t,272> info` is at :1107 (fourcc/size :1109), **not :1105**; VERS `blockSize = 36` :1117;
   IDNT `16 + 32 + 4 + 32` = 84 :1133; EXPO `16 + 4 + 4 + 4 + 4 + 8` = 40 :1208; WBAL `16 + 28` = 44 :1230;
   DEBG `std::array<uint8_t, 64>` :1265. Sum 52+36+44+272+84+180+64+40+44 = 816 - correct. Nine header writes
   confirmed as nine `writeBytesOrThrow(fd_, ...)` calls at :1083, :1098, :1110, :1128, :1144, :1202, :1225,
   :1245, :1275. 16-bit MLV rowBytes = `frame.width * 2u` (:853-854 in `prepareRawLayout`), flush condition
   `bufferedBytes + rawLayout_.rowBytes > payloadScratch_.size()` :891. VIDF block 32 + 16,588,800 =
   16,588,832 B; 16,588,832 mod 4096 = 32, so the 32 B/frame drift and the 848 first-payload offset are correct;
   35 write() per frame (1 + 34) correct. `grep -nE 'fsync|fdatasync|fadvise'` over MlvEncoder.cpp: only :981.

7. **All file I/O on DngRecordingQueue workers; MLV opened on first job, closed by destructor** - CORRECTED
   (window ends). `void dngWorkerLoop()` :3806, `CdngEncoder encoder;` :3820, `encoder.writeDngFile(job.path,
   job.frame, job.metadata)` :3853 (reader's window :3806-3852 ends one line early). `void mlvWorkerLoop()`
   :3914, `MlvEncoder encoder;` :3916, `encoder.open(job.path, settings_, job.frame, job.metadata, &mlvError)`
   :3940, `encoder.writeFrame(job.frame, job.metadata, &mlvError)` :3944 (reader's :3913-3943 is off by one
   at both ends). `MlvEncoder::~MlvEncoder() { close(); }` MlvEncoder.cpp:827-830 - exact; the loop has no
   explicit close after it (:3952-3956), so the destructor of the function-local encoder is indeed what closes
   the file when the worker returns. `workers_.emplace_back(&DngRecordingQueue::workerLoop, this)` :3459 -
   exact.

8. **Raw copy from a vector pool; miss = zero-filled vector; pool cap min(maxQueued, max(workers+2,4))** -
   CONFIRMED. `std::vector<uint8_t> rawCopy = recorder_.acquireRawBuffer(rawSize)` :7268, `copyRawBytes(buffer,
   rawCopy.data(), ...)` :7269; `return std::vector<uint8_t>(size)` :3670 inside `acquireRawBuffer` :3657-3679
   (the reader's surprise cites :3669; the return is :3670); `buffer.resize(size)` :3677; `recycleRawBuffer`
   :3970-3990 and `preferredRawPoolSize()` returning `std::min(maxQueuedFrames_, std::max<size_t>(workerCount_ +
   2u, 4u))` :3992-3995; `recycleRawBuffer(std::move(job.rawBytes))` :3873; `DMA_BUF_IOCTL_SYNC` :6767 and
   `std::memcpy(destination, source, size)` :6784 inside :6762-6786; `::posix_memalign(&ptr, 4096, wanted)`
   apertar-core/src/lossydng/LossyDngEncoder.cpp:140@f60e301. `grep -rnE 'posix_memalign|aligned_alloc|
   memalign|alignas|align_val_t' src/ include/` hits only that line. Pool sizes recomputed: uncompressed
   min(12, max(6,4)) = 6; lossless min(24, max(7,4)) = 7; MLV min(12, max(3,4)) = 4; (lossy, not stated by the
   reader: min(24, max(6,4)) = 6). The 16-byte malloc alignment remark is correctly labelled probable.

9. **No whole-file buffer; reused scratch; cached IFD template patched in place** - CORRECTED (one line).
   `mutable std::vector<uint8_t> payloadScratch_` ... `mainIfdScratch_` ... `exifScratch_` ...
   `IfdTemplateCache ifdTemplateCache_` apertar-core/src/cdng/CdngEncoder.hpp:192-200@f60e301 (inside the cited
   :186-200); `takePayloadScratch` :1198-1203 / `recyclePayloadScratch` :1205-1209; `takeReusableBytes`
   :1438-1444 / `recycleReusableBytes` :1446-1449; `templateMatches` :1506-1520 with `return !lossless &&
   ifdTemplateCache_.valid` at :1508 (the reader's note says :1508 - exact; my first count said 1507, grep
   confirms 1508); `std::max<size_t>(16 * 1024, mainIfdLayoutCache_.mainIfdSize)` :1636; `ifdBytes.assign(
   ifdTemplateCache_.bytes...)` :1714, `patchFixedAscii` :1715-1718, `putLe16(... exifIsoShortOffset ...)`
   :1731 inside :1714-1738. `IfdBuilder::buildAt` apertar-core/src/cdng/IfdBuilder.hpp:113-154@f60e301 -
   exact.

10. **6-12 small per-frame heap allocations (probable)** - CORRECTED (two citations), label honest.
    `frameFilename` with `std::ostringstream` and `std::setw(9) << std::setfill('0') << frameIndex << ".dng"`
    :3787-3793 - inside the cited :3785-3793. The path concatenation `folderPathString_ + "/" + frameName` is
    at :3713, outside the cited :3700-3711 (metadata string assignments :3705-3707 are inside). `const
    std::string originalDate = dateTimeString(wallClock)` is at :1398, not inside :1399-1401
    (`colorProfileForMetadata(metadata)` :1401 is). `make = "Apertar"` ... `uniqueCameraModel = "Blackmagic
    Micro Cinema Camera"` CdngEncoder.hpp:75-77 inside :75-83 - exact. `struct FrameJob { std::vector<uint8_t>
    rawBytes; RawFrameView frame; CdngEncoder::Metadata metadata; std::string path; }` :3727-3732 - exact.
    "Probable" is the right label; the count is not derivable from source.

11. **Worker and queue sizing** - CONFIRMED. `normalWorkerCount = std::max(2u, std::min(4u, hardwareThreads))`
    :3433; `defaultQueueFrames = compressedDng && hardwareThreads >= 4 ? 24u : 12u` :3437;
    `unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64)` :3438-3439;
    `defaultLosslessWorkers = hardwareThreads >= 4 ? std::min(8u, hardwareThreads + 1u) : normalWorkerCount`
    :3442-3444; `defaultLossyWorkers = std::max(1u, std::min(4u, hardwareThreads))` :3448;
    `RecordingFormat::Mlv ? 1u` :3449-3450, `APERTAR_CDNG_WORKERS ... 1, 8` :3452, `APERTAR_LOSSYDNG_WORKERS ...
    1, 8` :3454 - all inside :3432-3456. `workerCount_ = 0` :4028, `maxQueuedFrames_ = 12` :4029;
    `unsignedEnvValue(...)` :1051-1063. Pi 5 numbers (4 threads) recomputed: 4/12, 5/24, 4/24, 1/12 - correct.

12. **Queue-full: drop before copy, counter, 'drop[queue-full]' log on 1st and every 30th** - CONFIRMED.
    `hasCapacityForFrame` :3637-3655 with `queue_.size() < maxQueuedFrames_` :3642, `++droppedFrames_` :3645,
    `droppedFrames_ == 1 || (droppedFrames_ % 30) == 0` :3647, `"ApertarCore drop[queue-full]: frame="` :3648;
    comment `reject before copying a full RAW frame that cannot be queued` :7263-7264 and `if
    (!recorder_.hasCapacityForFrame(frameIndex)) return;` :7265-7266; the repeated check in `enqueue`
    :3688-3698 - exact.

13. **Counters and log formats** - CONFIRMED. `struct Stats { enqueued ... maxQueueDepth }` :3361-3370;
    `"ApertarCore recording stats: "` :3525 with `enqueued=`, `written=`, `dropped_queue_full=`,
    `discarded_on_stop=`, `write_failures=`, `peak_queue=` :3526-3531 inside :3523-3532; `++writeFailures_;`
    :3857, `failRecording(e.what())` :3858, `"ApertarCore DNG write failed for "` :3859 inside :3855-3860;
    MLV twin :3948-3950 inside :3946-3950; `"ApertarCore capture stats: "` with `dropped_gap_estimate=` and
    `requeue_failures=` :5999-6001, printed only when either is non-zero (:5998); `"ApertarCore lossless
    timing: jobs="` :3543 and `"ApertarCore lossless phases: jobs="` :3555; `"ApertarCore recording clip: "`
    :3461 with `worker_nice=` :3468, `workers=` :3469, `queue=` :3470, `tile_rows=` :3471,
    `encoder=quad_single_pass` :3472. `failRecording` clears the queue and sets `stopping_` (:3958-3967).

14. **Process priority configuration: only LimitNICE=-5** - CONFIRMED.
    apertar-core/config/apertar-core-capture-priority.conf:1-3@f60e301 is `[Service]`, a comment, `LimitNICE=-5`;
    apertar-core/scripts/start-apertar-core.sh:16-21@f60e301 exports `LIBCAMERA_RPI_TUNING_FILE` when set and
    `exec "$CORE_BIN" --socket ... --media ...` with no nice/taskset/chrt/ionice; `install(TARGETS apertar-core
    RUNTIME DESTINATION bin)` apertar-core/CMakeLists.txt:190@f60e301 and the two plugin installs :191-196,
    nothing for config/; `sudo systemctl start apertar-core.service` apertar-core/README.md:232@f60e301 (and
    `stop` :238); `find` for `*.service`/`*.timer` outside .git returns nothing; `grep -rnE 'Nice=|CPUAffinity|
    IOSchedulingClass|CPUSchedulingPolicy|LimitRTPRIO|LimitNICE'` hits only the drop-in and the comment at
    CameraController.cpp:6928. Nothing in the repo references the drop-in file by name either.

15. **In-process priorities: nice -5 on the callback thread, APERTAR_CDNG_WORKER_NICE for lossless/lossy
    workers only** - CONFIRMED. `if (!capturePriorityAdjusted_)` :6926, comment `LimitNICE=-5 permits this
    bounded boost without CAP_SYS_NICE.` :6928, `Only this callback thread changes priority, not encoder
    workers.` :6929, `::setpriority(PRIO_PROCESS, static_cast<id_t>(tid), -5)` :6931, `"ApertarCore capture
    scheduling: thread="` :6932 - all inside :6925-6936. Worker side: the `#if defined(__linux__)` block
    :3808-3819 applies only when lossless cDNG or lossy DNG (:3811-3813), `defaultNice = ... LossyDng ? 5u :
    0u` :3814, `unsignedEnvValue("APERTAR_CDNG_WORKER_NICE", defaultNice, 0, 19)` :3815, `if (workerNice > 0)
    ::setpriority(PRIO_PROCESS, gettid, workerNice)` :3816-3817 - inside the cited :3809-3818.
    `grep -rnE 'setpriority|sched_setscheduler|pthread_setschedparam|sched_setaffinity|pthread_setaffinity_np|
    SCHED_FIFO|SCHED_RR|ioprio|mlockall' src/ include/` returns exactly :3817 and :6931.

16. **nice -5 lands on libcamera's emitting thread (synchronous Signal delivery to a non-Object receiver)** -
    CORRECTED (wrong overload cited; mechanism and conclusion stand; "probable" label is right for the Pi
    binary). `camera_->requestCompleted.connect(this, &CameraSession::requestComplete)` CameraController.cpp:6698
    - exact. The receiver is `class CameraController::CameraSession {` :5547 with no base class, and
    `grep -rnE 'libcamera::Object|libcamera/base/object'` over src/ finds nothing, so the non-Object path is
    CONFIRMED from Core's source. But `&CameraSession::requestComplete` is a member-function pointer, which is
    not `std::is_invocable_v<Func, Args...>`, so the overload the reader cites
    (libcamera(qbc)/include/libcamera/base/signal.h:75-84@7e9fef0, `BoundMethodFunctor ... (obj, nullptr,
    func)`) is SFINAE-excluded; the overload actually selected is `connect(T *obj, R (T::*func)(Args...))` for
    `!std::is_base_of<Object, T>::value`, which creates `BoundMethodMember<T, R, Args...>(obj, nullptr, func)`
    at signal.h:55-62@7e9fef0. Its `activate` is `BoundMethodMember::activate` at
    libcamera(qbc)/include/libcamera/base/bound_method.h:165-170@7e9fef0: `if (!this->object_) { T *obj = ...;
    return (obj->*func_)(...); }` - the same direct, synchronous call the reader described from the Functor
    variant at :132-133. `Signal::emit` iterating `slots()` and calling `activate(args...)` signal.h:140-148 -
    exact. `Camera::requestComplete` ... `requestCompleted.emit(request)` libcamera(qbc)/src/libcamera/
    camera.cpp:1481-1488 - exact; `PipelineHandler::completeRequest` ... `camera->requestComplete(req)`
    libcamera(qbc)/src/libcamera/pipeline_handler.cpp:584-599 - exact, and its doc comment at :582 reads
    `\context This function shall be called from the CameraManager thread.`, which supports (as source
    documentation, not a runtime observation) the reader's "probable" that the boosted thread is the
    CameraManager thread. libcamera(cinemate)/src/libcamera/camera.cpp:1447-1454@bfe0b76 - exact. Whether the
    Pi's binary matches 7e9fef0 remains PROBABLE, as the reader says.

17. **MLV leaves pages in the page cache (no DONTNEED, no fsync)** - CONFIRMED. MlvEncoder.cpp:981 is the only
    fadvise in the file; CdngEncoder.cpp:1779 is the only DONTNEED in either writer.

18. **kActiveRequestCount = 3 caps in-flight requests** - CONFIRMED (upgrade from probable).
    `constexpr unsigned int kActiveRequestCount = 3;` :1048 (and `kConfiguredBufferCount = 4` :1047); in
    `makeRequests`, `processedYuvMode = !settings_.photoModeEnabled && isProcessedVideoFormat(settings_.
    recordingFormat)` :6795, `activeRequestLimit = ... : processedYuvMode ? h264CameraBufferCount() :
    kActiveRequestCount` :6796-6797, `requestCount = std::min<size_t>(previewBuffers.size(),
    activeRequestLimit)` :6798, `std::min(requestCount, rawBuffers->size())` :6800. The reader's doubt is
    settled: `bool isProcessedVideoFormat(RecordingFormat format)` returns `format == RecordingFormat::H264 ||
    format == RecordingFormat::Prores` (CameraController.cpp:227-230), so for cDNG/MLV the limit is 3 of the 4
    allocated raw and preview buffers.

19. **IFD size unknown without a run** - CONFIRMED as an honest UNKNOWN; narrowed below (Added, item 7).
    54 `ifd.add`/`appendAscii` statements in :1527-1627 (recounted with grep: 54); `exifIfd.add(0x829A ...)`
    :1643 through `exifIfd.add(0xA003 ...)` :1653 (10 entries); `IfdBuilder::buildAt` IfdBuilder.hpp:113-154
    with `count * sizeof(Entry)` :122 (`Entry` is 12 bytes: `uint16_t tag; uint16_t type; uint32_t count;
    uint32_t value;` under `#pragma pack`, :73-78), `align(buffer, 4)` before and after each out-of-line value
    :138-141.

### Numbers recomputed (all agree with the reader unless noted)

- 16-bit 3840x2160: rowBytes 7,680; payload 16,588,800 B = 4,050 pages; strip offset 8; IFD offset 16,588,808
  (8 mod 4096); 34 payload writes of 491,520 B (x33) + 368,640 B; 40 syscalls per DNG.
- 3840x2200: payload 16,896,000 B = 4,125 pages; 35 payload writes (34 x 491,520 + 184,320).
- 12-bit uncompressed: rowBytes 5,760; payload 12,441,600 B = 3,037.5 pages; chunk 368,640 B; 34 writes; IFD
  offset 12,441,608 (pad 0).
- Lossless 128-row strips: 17 strips at 2160 rows, 18 at 2200; 136 B of strip tables for 17 strips.
- MLV: 816 B of header blocks in 9 writes; VIDF block 16,588,832 B; frame N header at 816 + N x 16,588,832;
  payload offset drifts 32 B per frame; 35 writes per frame.
- Pools (Pi 5): uncompressed 6, lossless 7, lossy 6, MLV 4 raw buffers; workers/queue 4/12, 5/24, 4/24, 1/12.
- LinearizationTable 8,192 B; 8,294,400 LUT lookups per 3840x2160 frame.

### Added (facts the reader missed or left open, settled from source)

1. **The raw-buffer pool is emptied at every stop**: `rawPool_.clear(); pooledRawBytes_ = 0;
   expectedRawBufferSize_ = 0;` inside `stop()` at apertar-core/src/camera/CameraController.cpp:3596-3598@f60e301.
   So every clip starts cold: until workers have recycled buffers, each new frame takes the
   `return std::vector<uint8_t>(size)` miss path (:3670), i.e. a fresh 16.6 MB zero-filled allocation plus the
   16.6 MB memcpy on the completion thread - at least the first `preferredRawPoolSize()` frames (6 for
   uncompressed cDNG), more if workers lag. A frame rejected inside `enqueue` (:3688-3698) also destroys its
   by-value `rawBytes` instead of recycling it, so the next frame pays a zero-filled allocation again.
2. **The uncompressed payload scratch is zero-filled every frame**: `recyclePayloadScratch` does
   `bytes.clear()` (CdngEncoder.cpp:1207) and `takePayloadScratch` does `bytes.resize(size)` on that
   zero-length vector (:1201), which value-initialises `targetChunkSize` bytes - 491,520 B of memset per
   16-bit frame on the worker thread (small, but an O_DIRECT staging buffer would want to avoid it). The MLV
   writer avoids this: `if (payloadScratch_.size() < targetChunkSize) payloadScratch_.resize(...)`
   (MlvEncoder.cpp:873-874).
3. **12-bit uncompressed cDNG is a pack pass, not a memcpy**: an Unpacked frame goes through
   `prepareRawLayout` -> `prepareUnpackedLayout` (CdngEncoder.cpp:1186-1196, 1849-1859), and `writeDngRowBytes`
   takes the final `else` branch `Csi2RawConverter::packDng12Row(src16, dst, frame.width)` (:1054-1060). So in
   12-bit Clear HDR cDNG the samples are touched twice: the 65,536-entry LUT on the completion thread
   (:1335-1346 via :7275) and the 16->12-bit pack on the worker.
4. **The borrowed-fd path is the photo-still path only**: `encoder.writeDngFile(output.path(), dngFrame,
   dngMetadata, output.fd())` CameraController.cpp:5223 inside `writeDngStill` (`AtomicStillFile output(
   finalPath)` :5222); the recording worker calls `encoder.writeDngFile(job.path, job.frame, job.metadata)`
   :3853 with the default fd, so the open flags in finding 2 are the ones recording uses.
5. **Signal-delivery overload**: see verdict 16 - the selected overload is signal.h:55-62 and the direct call is
   bound_method.h:165-170 (libcamera(qbc)@7e9fef0); `class CameraController::CameraSession {` has no base
   (CameraController.cpp:5547) and src/ never includes libcamera/base/object.h. pipeline_handler.cpp:582
   documents `completeRequest` as CameraManager-thread context.
6. **kActiveRequestCount applies to raw formats**: `isProcessedVideoFormat` is H264 or ProRes only
   (CameraController.cpp:227-230), settling the reader's "probable" on finding 18.
7. **IFD size, PROBABLE estimate from the entry list** (CdngEncoder.cpp:1527-1627, 1643-1653; IfdBuilder.hpp
   :113-154; string sources: clip folder `cDNG_yy-mm-dd_C0001` = 19 chars from `prefix << formatPrefix <<
   put_time("%y-%m-%d")` and `"_C" << setw(4)` at CameraController.cpp:3773-3778 with `clipName_ =
   folderPath_.filename().string()` :3423; frame name = clip + "_" + 9 digits + ".dng" = 33 chars :3787-3793;
   date `strftime "%Y:%m:%d %H:%M:%S"` = 19 chars, CdngEncoder.cpp dateTimeString; `make "Apertar"`, `model
   "Apertar D1"`, `software "ApertarCore"`, `uniqueCameraModel "Blackmagic Micro Cinema Camera"`
   CdngEncoder.hpp:75-78; `out.serial = cameraSerial` :3261 and `out.cameraLabel = cachedCameraLabel()` :3289
   are runtime values). For a colour 16-bit uncompressed frame with no forward matrices
   (`hasForwardMatrix1/2 = false` by default, CdngEncoder.hpp:61,67), no serial, no cameraLabel: 45 main
   entries -> directory 2 + 45 x 12 + 4 = 546 B, +2 alignment, out-of-line data 20+20+36+8+12+12+20+32+20
   (ASCII) + 32 (BlackLevel 4 Rationals) + 4 x 72 (ColorMatrix1/2, CameraCalibration1/2) + 24 + 24
   (AnalogBalance, AsShotNeutral) + 8 (BaselineExposure) + 20 (DateTimeOriginal) + 8 (TimeCodes) + 8
   (FrameRate) = 592 B -> main IFD 1,140 B; Exif IFD 10 entries -> 126 + 2 + 36 = 164 B; tail = 1,304 B.
   A 16-hex-char serial adds 32 B (1,336), each forward matrix adds 84 B, the 12-bit LinearizationTable adds
   12 + 8,192 = 8,204 B, and the lossless variant swaps 3 inline entries for 4 (two of them 68 B tables for
   17 strips: +12 entry bytes, +136 data). So a 16-bit 3840x2160 uncompressed DNG is about
   16,590,112-16,590,500 B (1,312-1,700 mod 4096), never a 4096 multiple; the IFD would have to be exactly
   4,088 mod 4096 for that, which no combination of these fields produces. UNKNOWN remains only for the exact
   byte (serial/cameraLabel lengths and profile flags are runtime).
8. **Lossless open uses O_CLOEXEC unconditionally** (CdngEncoder.cpp:1273) while the uncompressed path guards it
   with `#ifdef O_CLOEXEC` (:1749-1751); the MLV path guards it too (MlvEncoder.cpp:965-967). No effect on
   Linux.

### Unanswered items: status after verification

- Exact IFD byte size: narrowed to a formula and a ~1.3-1.7 KiB estimate (Added 7); exact value still needs a
  recorded file (serial/cameraLabel lengths, forward-matrix flags are runtime).
- Installed apertar-core.service contents: still UNKNOWN; the README (:232, :238) only starts/stops the unit and
  nothing in the repo installs or templates it.
- Pi binary vs libcamera(qbc)@7e9fef0: still PROBABLE; both libcamera trees read here deliver the signal
  synchronously, and the qbc tree documents the completion path as CameraManager-thread context (:582).
- Per-frame small allocation count: still needs instrumentation; the sources of the allocations the reader
  listed are confirmed (CameraController.cpp:3787-3793, :3705-3707, :3713; CdngEncoder.cpp:1398, :1401).

### Verdict summary

19 findings: 12 CONFIRMED, 7 CORRECTED (3: window/line offsets; 4: :1243-1247 should be :1237-1241; 6: INFO
block at :1107 not :1105, patchFrameCount window :1282-1290; 7: windows end one line early; 9: none material
(note confirmed at :1508); 10: :3713 and :1398 outside the cited windows; 16: Functor overload cited where the
Member overload signal.h:55-62 / bound_method.h:165-170 is the one selected), 0 REFUTED, 0 UNVERIFIABLE. Every
recomputed number agrees with the reader. Status labels were honest throughout; finding 18 can be upgraded from
probable to confirmed.
