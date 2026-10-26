---
datum: 2026-10-26 04:20:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T24 cdng-direct-io
typ: digital anteckning
---

# T24. Write uncompressed cDNG with direct I/O: IFD first, image on a page boundary

Status: written 2026-10-26 (cloud session; reference patch `working/patches/0001-cdng-direct-I-O-for-uncompressed-DNGs-IFD-first-layo.patch`, **not compiled**, build it here step by step). Needs T22 (measurement) and T23 (aligned pool is reused). Builds the writer path (cDNG container, page cache, O_DIRECT).

**You will learn**
- What O_DIRECT requires (offset, length and memory aligned to the block size) and how a DNG can be laid out to satisfy it.
- How Core's cDNG writer builds its IFD once and patches it per frame, and how to add one more patched tag.
- How to prove the page cache is out of the loop (`nr_writeback` flat, CSI-2 counters zero).

**Risk:** Core rebuild + restart. Files written in the new layout are valid TIFF/DNG (IFD at offset 8, strip at a page boundary) and open in any reader. `APERTAR_CDNG_DIRECT_IO=0` restores buffered writes without rebuilding. Lossless cDNG, MLV and stills are untouched. **Time:** 3-4 h.

## 1. The problem

T22's buffered `dd` loses frames; the direct `dd` does not. Core's writer is the buffered one: `open(O_WRONLY|O_CREAT|O_TRUNC)`, 8-byte header, ~34 `write()` calls of 491,520 bytes, 0-3 pad bytes, the IFD, then `posix_fadvise(DONTNEED)`, which starts writeback at once (`Core/src/cdng/CdngEncoder.cpp:1748-1786@f60e301`; `mm/fadvise.c:113-115`). So every DNG is a writeback burst, 25-30 per second.

Expected after this tutorial: a 16-bit take at 25 fps writes 246/246, the CSI-2 counters stay 0 during the take, `nr_writeback` stays near 0.

## 2. How this part works

O_DIRECT rules (Linux): every `write()` must have file offset, byte count and user buffer address aligned to the device's logical block size (512 or 4096). Use 4096 everywhere. The last partial page is written zero-padded and the file is cut with `ftruncate()`, which is a metadata operation and always allowed.

Core's DNG today:

```
offset 0      8 bytes   TIFF header ("II", 42, IFD offset)
offset 8      payload   3840 x 2160 x 2 = 16,588,800 bytes (16-bit)
then          0-3 pad
then          IFD + Exif (~1.3-1.7 KB; +8 KB with a LinearizationTable)
```

Nothing is page aligned and the IFD is last. New layout when direct I/O is on (`ifdFirst`):

```
page 0..k-1   header (8) + IFD + Exif + zero padding, k*4096 bytes      <- one aligned write
page k..      payload, straight from the page-aligned raw copy          <- one aligned write (16-bit 4K is exactly 4050 pages)
tail          last partial page, zero padded, then ftruncate(real size)
```

TIFF allows the IFD anywhere; `StripOffsets` (tag 273) just has to point at the strip. The IFD is built once per clip into a template (`ifdTemplateCache_`, `CdngEncoder.cpp:1627-1710`) and patched per frame (dates, ISO, time code); you will add one more patch: tag 273 gets the page-aligned strip offset once the IFD size is known.

The raw copy must be page aligned for the fast path. `std::vector` cannot promise that, so the copy is over-allocated by one page and the frame starts at the first page boundary inside it (`alignedRawData`). Both the completion thread (producer) and the worker (consumer) use the same helper.

Reading assignments: `CdngEncoder.cpp:1387-1392` (offsets), `:1527-1546` (tag 273 and 279 added to the IFD), `:1676-1735` (template patching), `:1748-1786` (writes), `:1861-1912` (`writeRawPayload` chunking); `CameraController.cpp:7265-7290` (the copy and the `RawFrameView`), `:3843` (`job.frame.data = job.rawBytes.data()`).

## 3. Find it yourself

**3.1 Is any Core DNG a multiple of 4096 bytes?** (Pi, read-only)

```bash
f=$(ls /media/RAW/*/*.dng | head -1); stat -c '%s %n' "$f"; python3 -c "import sys; s=int(sys.argv[1]); print(s % 4096)" $(stat -c %s "$f")
```

Prediction: no (16,588,808 + IFD ≈ 16,590,100-16,590,500, remainder 1,300-1,700). Why does that matter for O_DIRECT?

> [!tip]- Answer
> The IFD tail is not a page multiple and the image strip starts at byte 8. Neither can be written directly. Moving the IFD first and padding page 0 fixes both; the payload itself (3840 × 2 × 2160) is exactly 4050 pages.

**3.2 Where is `StripOffsets` written?** (Pi)

```bash
grep -n 'ifd.add(273' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp
grep -n 'findIfdTagValueOffset(ifdTemplateCache_.bytes, ifdOffset, exifRelativeOffset, 0x8827, true)' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp
```

Prediction: tag 273 is added with the value `stripOffset` (8) at template build time; other tags are found afterwards by `findIfdTagValueOffset(..., inlineValue=true)` so their 4-byte inline value can be patched per frame. You will do the same for 273 once.

**3.3 Is the raw copy aligned today?** (Pi)

```bash
grep -n 'recorder_.acquireRawBuffer(rawSize)' /home/pi/ApertarCore/src/camera/CameraController.cpp
```

Prediction: a plain `std::vector<uint8_t>(size)`; glibc returns mmap-backed blocks 16 bytes past a page boundary for sizes this large, so `data()` is never page aligned.

## 4. Make the change

Lines at `f60e301` (before T23 lines shift by ~25 in `CameraController.cpp`; use the search strings).

**4.1 Header: the cache knows the layout** (`/home/pi/ApertarCore/src/cdng/CdngEncoder.hpp`)

In `struct MainIfdLayoutCache` after `uint32_t stripByteCount = 0;` (search exactly that):

```cpp
        bool ifdFirst = false;
```

In `struct IfdTemplateCache` after `uint32_t exposureIndexOffset = 0;`:

```cpp
        // IFD-first layout (direct I/O): file offset of the image strip, page aligned.
        uint32_t directStripOffset = 0;
```

After the `writeRawPayload` declaration (search `bool writeRawPayload(int fd`):

```cpp
    // Direct I/O: every write page aligned in offset, length and memory.
    bool writeRawPayloadDirect(int fd, const RawFrameView &frame, const EncodedRawLayout &layout) const;
```

After `mutable IfdTemplateCache ifdTemplateCache_;`:

```cpp
    // Page-aligned scratch for direct I/O (header page and converted rows).
    struct AlignedBytes {
        uint8_t *data = nullptr;
        size_t size = 0;
        AlignedBytes() = default;
        AlignedBytes(const AlignedBytes &) = delete;
        AlignedBytes &operator=(const AlignedBytes &) = delete;
        ~AlignedBytes();
        void ensure(size_t bytes);
    };
    mutable AlignedBytes directScratch_;
    // Set when the filesystem refuses O_DIRECT (EINVAL); later frames fall back to buffered writes.
    mutable bool directIoUnsupported_ = false;
```

**Check:** `grep -c 'directStripOffset\|writeRawPayloadDirect\|AlignedBytes' src/cdng/CdngEncoder.hpp` → 6.

**4.2 Helpers** (`CdngEncoder.cpp`, just above `bool writeAll(int fd, const void *data, size_t size)`; and add `#include <new>` after `#include <cstdlib>` and `#include <iostream>` after `#include <cstring>` — the fallback messages use `std::cerr`, which this file never needed before; the host syntax check caught the missing include on 2026-10-26)

```cpp
// Direct I/O: the kernel requires offset, length and memory aligned to the
// device's logical block size (512 or 4096); 4096 satisfies every device.
constexpr size_t kDirectIoPage = 4096;

bool directIoEnabled()
{
    static const bool enabled = [] {
        const char *value = std::getenv("APERTAR_CDNG_DIRECT_IO");
        return !value || (std::strcmp(value, "0") != 0 && std::strcmp(value, "false") != 0 &&
                          std::strcmp(value, "off") != 0);
    }();
    return enabled;
}

size_t roundUpToPage(size_t value)
{
    return (value + kDirectIoPage - 1) / kDirectIoPage * kDirectIoPage;
}

bool pageAligned(const void *pointer)
{
    return (reinterpret_cast<uintptr_t>(pointer) % kDirectIoPage) == 0;
}
```

**4.3 The layout decision and the offsets** (`writeDngFile`)

After `const bool lossless = metadata.compression == CdngCompression::LosslessJpeg;` (`:1235`):

```cpp
    // Direct I/O layout: header and IFD first, the image strip on the next page
    // boundary, so every write is page aligned and the page cache stays out of the
    // way of the CFE (Clear HDR frame drops). Stills (borrowed fd) keep the old layout.
    const bool ifdFirst = !lossless && destinationFd < 0 && directIoEnabled();
```

Replace the offsets block (`:1387-1392`, search `const uint32_t stripOffset = tiffHeaderBytes;`):

```cpp
    constexpr uint32_t tiffHeaderBytes = 8;
    // IFD-first: the strip offset is known only once the IFD size is (patched below).
    uint32_t stripOffset = tiffHeaderBytes;
    const uint32_t stripByteCount = checkedTiffOffset(payloadByteCount);
    const uint64_t ifdOffset64 = ifdFirst ? tiffHeaderBytes
        : align4(static_cast<uint64_t>(stripOffset) + payloadByteCount);
    const uint32_t ifdOffset = checkedTiffOffset(ifdOffset64);
    const size_t paddingSize = ifdFirst ? 0
        : static_cast<size_t>(ifdOffset64 - (static_cast<uint64_t>(stripOffset) + payloadByteCount));
```

Key and comparison: after `key.stripByteCount = stripByteCount;` add `key.ifdFirst = ifdFirst;`; after `left.stripByteCount == right.stripByteCount &&` add `left.ifdFirst == right.ifdFirst &&`.

Why: the template is cached by layout; a buffered and a direct clip must not share one.

**Check:** `grep -c ifdFirst src/cdng/CdngEncoder.cpp` → 7 so far.

**4.4 Patch tag 273 once the IFD size is known** (end of the template-build block, search `ifdTemplateCache_.exposureIndexOffset =`; insert after that two-line statement and before `recycleReusableBytes(mainIfdScratch_, std::vector<uint8_t>{});`)

```cpp
        ifdTemplateCache_.directStripOffset = 0;
        if (ifdFirst) {
            // The IFD is complete, so its size is known: put the image strip on the
            // next page boundary and patch StripOffsets (tag 273) in the template.
            const uint32_t strip = checkedTiffOffset(
                roundUpToPage(static_cast<size_t>(ifdOffset) + ifdTemplateCache_.bytes.size()));
            const uint32_t at = findIfdTagValueOffset(ifdTemplateCache_.bytes, ifdOffset, 0, 273, true);
            putLe32(ifdTemplateCache_.bytes.data() + at, strip);
            ifdTemplateCache_.directStripOffset = strip;
        }
```

And right after the closing brace of that `if (!templateMatches()) { ... }` block:

```cpp
    if (ifdFirst)
        stripOffset = ifdTemplateCache_.directStripOffset;
```

Why it works: the IFD's size does not depend on the value of tag 273 (a 4-byte inline Long), so building with 8 and patching afterwards is exact. The Exif IFD offset (`align4(8 + mainIfdSize)`) is unaffected.

**Check:** `grep -n 'findIfdTagValueOffset(ifdTemplateCache_.bytes, ifdOffset, 0, 273, true)' src/cdng/CdngEncoder.cpp` → one hit.

**4.5 Open and write** (replace the block from `int openFlags = O_WRONLY | O_CREAT | O_TRUNC;` down to and including `::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);`, `:1748-1779`)

```cpp
    int openFlags = O_WRONLY | O_CREAT | O_TRUNC;
#ifdef O_CLOEXEC
    openFlags |= O_CLOEXEC;
#endif
    bool directFd = false;
    if (!lossless) {
        if (destinationFd >= 0) {
            output.fd = destinationFd;
        } else {
            if (ifdFirst && !directIoUnsupported_) {
                output.fd = ::open(path.c_str(), openFlags | O_DIRECT, 0644);
                if (output.fd >= 0) {
                    directFd = true;
                } else if (errno == EINVAL) {
                    directIoUnsupported_ = true;
                    std::cerr << "ApertarCore cDNG direct I/O: not supported on this filesystem, "
                                 "falling back to buffered writes\n";
                }
            }
            if (output.fd < 0)
                output.fd = ::open(path.c_str(), openFlags, 0644);
        }
    }
    const int fd = output.fd;
    if (fd < 0)
        throw std::system_error(errno, std::generic_category(), "Failed to open DNG for writing: " + path);

    if (!directFd)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);
    bool ok = true;
    if (lossless) {
        size_t written = 0;
        while (written < header.size()) {
            const ssize_t n = ::pwrite(fd, header.data() + written, header.size() - written, written);
            if (n < 0 && errno == EINTR)
                continue;
            if (n <= 0) { ok = false; break; }
            written += static_cast<size_t>(n);
        }
    } else if (ifdFirst) {
        // Page 0..: TIFF header, the IFD, zero padding up to the strip offset.
        directScratch_.ensure(stripOffset);
        std::memset(directScratch_.data, 0, stripOffset);
        std::memcpy(directScratch_.data, header.data(), header.size());
        std::memcpy(directScratch_.data + tiffHeaderBytes, ifdBytes.data(), ifdBytes.size());
        ok = writeAll(fd, directScratch_.data, stripOffset);
        if (ok)
            ok = writeRawPayloadDirect(fd, frame, layout);
        // The last page was zero padded: cut the file to its real length.
        if (ok && ::ftruncate(fd, static_cast<off_t>(stripOffset) + static_cast<off_t>(payloadByteCount)) != 0)
            ok = false;
    } else {
        ok = writeAll(fd, header.data(), header.size());
    }
    if (ok && !lossless && !ifdFirst)
        ok = writeRawPayload(fd, frame, layout);
    if (ok && paddingSize > 0)
        ok = writeAll(fd, padding.data(), paddingSize);
    if (ok && !ifdFirst)
        ok = writeAll(fd, ifdBytes.data(), ifdBytes.size());
    int writeErrno = ok ? 0 : errno;
    if (!ok && directFd && writeErrno == EINVAL) {
        // A filesystem that accepted O_DIRECT at open but refuses the writes (FUSE):
        // this frame is lost, the following ones go buffered.
        directIoUnsupported_ = true;
        std::cerr << "ApertarCore cDNG direct I/O: write rejected (EINVAL), falling back to buffered writes\n";
    }
    if (!directFd)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
```

The lines that follow (`if (!output.borrowed && ::close(fd) != 0 && ok)` ...) stay as they are.

**Check:** `grep -c 'O_DIRECT' src/cdng/CdngEncoder.cpp` → 1; `grep -c 'POSIX_FADV_DONTNEED' src/cdng/CdngEncoder.cpp` → 1 (now guarded).

**4.6 The aligned payload writer and the scratch** (before `CdngEncoder::EncodedRawLayout CdngEncoder::preparePackedCsi2Layout(`)

```cpp
CdngEncoder::AlignedBytes::~AlignedBytes()
{
    std::free(data);
}

void CdngEncoder::AlignedBytes::ensure(size_t bytes)
{
    if (size >= bytes)
        return;
    void *memory = nullptr;
    if (::posix_memalign(&memory, kDirectIoPage, roundUpToPage(bytes)) != 0)
        throw std::bad_alloc();
    std::free(data);
    data = static_cast<uint8_t *>(memory);
    size = roundUpToPage(bytes);
}

bool CdngEncoder::writeRawPayloadDirect(int fd, const RawFrameView &frame, const EncodedRawLayout &layout) const
{
    if (layout.rowBytes == 0 || layout.byteCount == 0) {
        errno = EINVAL;
        return false;
    }
    const size_t total = static_cast<size_t>(layout.byteCount);

    // Fast path: unpacked 16-bit rows are stored verbatim, so write straight from
    // the raw copy when it is page aligned (CameraController aligns it). 3840x2160
    // 16-bit is exactly 4050 pages; other heights leave a tail page.
    const bool rowsVerbatim = frame.packing == PixelPacking::Unpacked && frame.bitDepth == RawBitDepth::Bits16 &&
        layout.packing == PixelPacking::Unpacked && layout.bitDepth == RawBitDepth::Bits16 &&
        layout.rowBytes == frame.stride && frame.size >= total;
    if (rowsVerbatim && pageAligned(frame.data)) {
        const size_t whole = total / kDirectIoPage * kDirectIoPage;
        if (whole > 0 && !writeAll(fd, frame.data, whole))
            return false;
        const size_t tail = total - whole;
        if (tail > 0) {
            directScratch_.ensure(kDirectIoPage);
            std::memset(directScratch_.data, 0, kDirectIoPage);
            std::memcpy(directScratch_.data, frame.data + whole, tail);
            if (!writeAll(fd, directScratch_.data, kDirectIoPage))
                return false;
        }
        return true;
    }

    // General path: convert rows into the aligned scratch, flush whole pages, keep
    // the remainder for the next flush, zero pad the final page.
    const size_t chunk = roundUpToPage(std::max<size_t>(
        static_cast<size_t>(layout.rowBytes),
        std::min<size_t>(4u * 1024u * 1024u,
                         std::max<size_t>(256u * 1024u, static_cast<size_t>(layout.rowBytes) * 64u))));
    directScratch_.ensure(chunk);
    size_t buffered = 0;
    for (uint32_t y = 0; y < frame.height; ++y) {
        if (buffered + layout.rowBytes > chunk) {
            const size_t whole = buffered / kDirectIoPage * kDirectIoPage;
            if (!writeAll(fd, directScratch_.data, whole))
                return false;
            const size_t rest = buffered - whole;
            if (rest > 0)
                std::memmove(directScratch_.data, directScratch_.data + whole, rest);
            buffered = rest;
        }
        const uint8_t *src = frame.data + static_cast<size_t>(y) * frame.stride;
        writeDngRowBytes(frame, layout, src, directScratch_.data + buffered);
        buffered += layout.rowBytes;
    }
    if (buffered > 0) {
        const size_t padded = roundUpToPage(buffered);
        std::memset(directScratch_.data + buffered, 0, padded - buffered);
        if (!writeAll(fd, directScratch_.data, padded))
            return false;
    }
    return true;
}
```

**Check:** `grep -c 'writeRawPayloadDirect' src/cdng/CdngEncoder.cpp` → 2.

**4.7 Page-align the raw copy** (`/home/pi/ApertarCore/src/camera/CameraController.cpp`)

After `activeRawFrameBytes()` (search `size_t activeRawFrameBytes(uint32_t stride, uint32_t activeHeight)`):

```cpp
// Raw copies are over-allocated by one page so the frame can start on a page
// boundary: the cDNG writer then hands the buffer to O_DIRECT writes as it is.
constexpr size_t kRawCopyAlignment = 4096;

uint8_t *alignedRawData(std::vector<uint8_t> &bytes)
{
    const uintptr_t address = reinterpret_cast<uintptr_t>(bytes.data());
    const uintptr_t aligned = (address + kRawCopyAlignment - 1) & ~(static_cast<uintptr_t>(kRawCopyAlignment) - 1);
    return reinterpret_cast<uint8_t *>(aligned);
}
```

In the **recording** worker loops (two places, `dngWorkerLoop` and `mlvWorkerLoop`; search `job.frame.data = job.rawBytes.data();` and change only the two inside `DngRecordingQueue`, not the two in the photo writer):

```cpp
            job.frame.data = alignedRawData(job.rawBytes);
```

In `recordRawFrame` (search `recorder_.acquireRawBuffer(rawSize)`):

```cpp
        std::vector<uint8_t> rawCopy = recorder_.acquireRawBuffer(rawSize + kRawCopyAlignment);
        uint8_t *const rawData = alignedRawData(rawCopy);
        if (!copyRawBytes(buffer, rawData, mapped.data + activeOffsetBytes, rawSize)) {
            dropWarning_.markDropped();
            return;
        }
        if (clearHdrStoresCodes12(settings_) && rawInfo.packing == PixelPacking::Unpacked &&
            rawInfo.unpackedBytesPerSample == 2u && rawInfo.bitDepth == RawBitDepth::Bits12)
            compressClearHdrFrame(rawData, rawSize, rawInfo.width, rawInfo.height, rawInfo.stride);
```

and a few lines down:

```cpp
        RawFrameView view;
        view.data = rawData;
        view.size = rawSize;
```

If you did T23, the pre-fill becomes `activeRawFrameBytes(...) + kRawCopyAlignment`.

**Check:** `grep -c 'alignedRawData' src/camera/CameraController.cpp` → 4 (definition, two worker sites, one producer site).

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | grep -E 'error|Built target' | head
sudo systemctl restart apertar-core
```

A take, then prove the layout and the effect:

```bash
~/apertar-kb/working/tools/take.sh                                   # 16-bit, 25 fps, uncompressed cDNG
f=$(ls -t /media/RAW/*/*.dng | head -1)
python3 - "$f" <<'PY'
import struct, sys
b = open(sys.argv[1], 'rb').read(64 * 1024)
assert b[:4] == b'II*\x00', 'not little-endian TIFF'
ifd = struct.unpack_from('<I', b, 4)[0]
n = struct.unpack_from('<H', b, ifd)[0]
tags = {struct.unpack_from('<H', b, ifd + 2 + 12 * i)[0]: struct.unpack_from('<I', b, ifd + 2 + 12 * i + 8)[0] for i in range(n)}
import os; size = os.path.getsize(sys.argv[1])
print('ifd at', ifd, 'StripOffsets', tags[273], 'page aligned:', tags[273] % 4096 == 0, 'StripByteCounts', tags[279], 'file', size, 'tail ok:', tags[273] + tags[279] == size)
PY
```

Expected: `ifd at 8 StripOffsets 4096 page aligned: True StripByteCounts 16588800 file 16592896 tail ok: True` (4096 + 16,588,800). Then open the DNG in your usual converter: it must look identical to a buffered one.

The measurement (T22 routine):

```bash
python3 -I ~/apertar-kb/working/tools/writeback_watch.py 15 0.1 > /tmp/wb_take.txt &    # terminal A
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors > /dev/null                            # terminal B, zero
~/apertar-kb/working/tools/takes.sh 5 10                                                 # 16-bit uncompressed, 25 fps
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors
awk 'NR>1 && $3>1 {c++} END {print "samples with writeback >1 MB:", c+0}' /tmp/wb_take.txt
```

Success: 5/5 takes `missing=0`, `ipa rate=25.00/s intervals>60ms=0`, counters 0, writeback samples ≈ 0. Then the A/B: `sudo systemctl edit apertar-core` → `[Service] Environment=APERTAR_CDNG_DIRECT_IO=0`, restart, `takes.sh 5` again: the old loss should be back. Remove the drop-in afterwards.

Then 30 fps: `core.py set_fps value=30` and `takes.sh 3`. Prediction: better than T23 alone but not clean; the rest is T25.

## 6. Commit and push

```bash
git -C ~/ApertarCore add src/cdng/CdngEncoder.cpp src/cdng/CdngEncoder.hpp src/camera/CameraController.cpp
git -C ~/ApertarCore commit -m "cdng: direct I/O for uncompressed DNGs, IFD-first layout, page-aligned raw copies

Why: buffered writes plus fadvise(DONTNEED) made every DNG a 16.6 MB
writeback burst; page-cache writeback is what drops Clear HDR frames at
the CFE (T22 counters). O_DIRECT needs page alignment, so the header and
IFD fill page 0, StripOffsets points at page 1, the raw copy is page
aligned, and the padded last page is cut with ftruncate.
Tested: takes.sh 5 at 25 fps 16-bit: 5/5 clean, csi2_errors 0,
nr_writeback flat; APERTAR_CDNG_DIRECT_IO=0 brings the loss back."
git -C ~/ApertarCore push -u origin main
~/.claude/skills/apertar-dev/scripts/apertar_status.sh
```

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `Failed to open DNG for writing` with `Invalid argument` and no fallback line | the fallback only catches EINVAL on `open`; a different errno | paste the journal line; `findmnt /media/RAW` |
| `cDNG direct I/O: write rejected (EINVAL)` once, then buffered | FUSE/ntfs-3g media: no direct I/O there | expected; the frame was lost once |
| every frame fails, `write_failures=` grows | a write that is not page aligned (a converted-row path with a wrong chunk) | `APERTAR_CDNG_DIRECT_IO=0` to record; then check `chunk % 4096` and the tail logic in 4.6 |
| DNG opens but is shifted/garbled | `StripOffsets` not patched (tag 273 not found or the cache key missed `ifdFirst`) | run the Python check in §5: `StripOffsets` must equal the first page boundary after the IFD |
| 12-bit Clear HDR cDNG slow | it takes the general path (16→12 pack) through the scratch, as before | expected; the fast path is 16-bit storage only |
| compile error about `AlignedBytes` copy | `CdngEncoder` is copied somewhere new | it is constructed by value only in the worker loops; do not copy it |

Undo: `git -C ~/ApertarCore checkout -- src/cdng src/camera/CameraController.cpp`, rebuild; or just `APERTAR_CDNG_DIRECT_IO=0`.

## 8. What you learned, going further

- Direct I/O is an alignment contract, and a container format can be laid out to meet it.
- `fadvise(DONTNEED)` is not "free the cache"; it is "write it back now".
- Exercises: (1) the lossless writer: stage strips in `directScratch_`, flush whole pages, write page 0 last; (2) MLV: an aligned staging ring and VIDF `frameSpace` to page-align frame data (`MlvEncoder.cpp:1020-1033`).
- Upstream: both the layout and the measurement are worth offering; cinepi-raw never shipped O_DIRECT (a four-day trial in June 2025 was deleted).

## 9. Sources

- `working/clearhdr-compare-answer.md` §2; `working/patches/0001-cdng-direct-I-O-for-uncompressed-DNGs-IFD-first-layo.patch`.
- `Apertar-Core/src/cdng/CdngEncoder.cpp@f60e301:1235, 1387-1392, 1458, 1485, 1536, 1627-1710, 1748-1786, 1861-1912`; `src/cdng/CdngEncoder.hpp:156-190`; `src/camera/CameraController.cpp:3028-3034, 3843, 7265-7290`.
- Kernel: `mm/fadvise.c:113-115`, `fs/exfat/inode.c:492-506` @ `5bd564a`.

%% tutor
ref core src/cdng/CdngEncoder.hpp 156 struct IfdTemplateCache {
ref core src/cdng/CdngEncoder.cpp 1235 const bool lossless = metadata.compression == CdngCompression::LosslessJpeg;
ref core src/cdng/CdngEncoder.cpp 1388 const uint32_t stripOffset = tiffHeaderBytes;
ref core src/cdng/CdngEncoder.cpp 1458 key.stripByteCount = stripByteCount;
ref core src/cdng/CdngEncoder.cpp 1748 int openFlags = O_WRONLY | O_CREAT | O_TRUNC;
ref core src/cdng/CdngEncoder.cpp 1779 ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
ref core src/cdng/CdngEncoder.cpp 1861 bool CdngEncoder::writeRawPayload(int fd, const RawFrameView &frame, const EncodedRawLayout &layout) const
ref core src/camera/CameraController.cpp 3039 size_t activeRawFrameBytes(uint32_t stride, uint32_t activeHeight)
ref core src/camera/CameraController.cpp 7288 std::vector<uint8_t> rawCopy = recorder_.acquireRawBuffer(rawSize);
check 3.2 | grep -c 'ifd.add(273' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp | ^1$
check 4.1 | grep -c 'directStripOffset\|writeRawPayloadDirect\|AlignedBytes' /home/pi/ApertarCore/src/cdng/CdngEncoder.hpp | ^6$
check 4.4 | grep -c 'findIfdTagValueOffset(ifdTemplateCache_.bytes, ifdOffset, 0, 273, true)' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp | ^1$
check 4.5 | grep -c 'O_DIRECT' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp | ^1$
check 4.6 | grep -c 'writeRawPayloadDirect' /home/pi/ApertarCore/src/cdng/CdngEncoder.cpp | ^2$
check 4.7 | grep -c 'alignedRawData' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^4$
%%

#CINEMATE
#APERTAR
