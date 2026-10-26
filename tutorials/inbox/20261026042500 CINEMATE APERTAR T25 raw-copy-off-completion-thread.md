---
datum: 2026-10-26 04:25:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T25 raw-copy-off-completion-thread
typ: digital anteckning
---

# T25. Copy raw frames on a recorder worker, not on libcamera's completion thread

Status: written 2026-10-26 (cloud session; reference patch `working/patches/0001-camera-copy-raw-frames-on-a-recorder-worker-not-on-l.patch`, **not compiled**). Needs T23 (requests follow buffers). **T24 is skipped on our build (2026-10-26, uncompressed 25 fps is already clean, so direct I/O has nothing to fix): wherever this note or the patch uses `alignedRawData(rawCopy)` use `rawCopy.data()`, and wherever it asks for `copy.size + kRawCopyAlignment` use `copy.size`; drop the patch's `alignedRawData` hunk.** Builds the request lifecycle (**M7** plus threads).

**You will learn**
- What libcamera's completion thread does per frame in our stack (two full-buffer passes in libcamera, then Core's sync + copy), and why 30 fps does not fit.
- How Core's H.264 path already releases a camera buffer from a worker, and how to do the same for raw.
- The one rule of worker-side release: never hold more requests than the CFE can spare.

**Risk:** Core rebuild + restart; a threading change. Wrong ordering at stop shows as a hang or a crash on `record_stop`/mode change (§7). Undo by `git checkout`. **Time:** 4-6 h, expect two or three build-fix rounds.

## 1. The problem

Recording at 30 fps in Clear HDR loses ~20 % (12-bit lossless 228/291, 16-bit 230/291), libcamera sees ~24 fps while recording and 30.00 idle; the camera thread is 52-72 % busy (`working/sensor-capabilities.md`). The thread is libcamera's pipeline-handler thread. Per 16-bit frame it spends ~7 ms on the `rev16` byte swap and ~7 ms on software statistics (both inside libcamera, `pisp.cpp`), then runs **Core's callback**: dma-buf sync (~4 ms) + a 16.9 MB memcpy (~4 ms) [+ the 12-bit code mapping] before `requeueRequest`. 23 of 33 ms, on the thread that also services every CFE/BE V4L2 event and the next frame's FE config. Cinemate's equivalent thread only posts a message; its copy happens in an encode worker (`cinepi-raw/cinepi/cinepi_recorder.hpp:49-105@63a08d5`).

## 2. How this part works

Today (`CC:6915-7008`, `CC:7189-7287`):

```
 completion thread: metadata -> preview descriptor -> cadence gate -> recordRawFrame():
                    hasCapacity -> acquireRawBuffer -> dmabuf sync START -> memcpy 16.9 MB -> sync END
                    -> (12-bit) compressClearHdrFrame -> recorder_.enqueue(copy) -> requeueRequest(request)
 write workers:     dequeue -> writeDngFile
```

After:

```
 completion thread: metadata -> preview -> gate -> recordRawFrame(): hasCapacity -> recorder_.enqueueCopy({request, source, size, ...}) -> return (NO requeue here)
 copy worker:       dequeue -> acquireRawBuffer -> sync START -> memcpy -> sync END -> release(request) => requeueRequest
                    -> (12-bit) compressClearHdrFrame on the copy -> recorder_.enqueue(copy)
 write workers:     unchanged
```

The pattern already exists in Core: the H.264 recorder takes a `PreviewJob` with a `release` callback and calls it from its copy worker (`CC:4040-4048`, `CC:4367`, `CC:4799-4805`). Raw gets the same shape.

The one rule: a request held by a copy worker is a buffer the CFE cannot fill. With N buffers, hold at most N-2 so two frames are always queued (`kernel rp1_cfe/cfe.c:615-631` skips a frame when any node has nothing queued). A frame that finds no slot is dropped **and its request requeued at once**: a counted drop, not a stall.

Stop ordering (`CC:5751-5790`): `recordingFramesEnabled_ = false` → `camera_->stop()` → `recorder_.stop()` (joins workers) → `unmapRawBuffers()` → `requests_.clear()`. Copy workers must therefore be joined inside `recorder_.stop()`, before the mapping disappears; a release that fires after `camera_->stop()` must do nothing (`running_` is already false).

Reading assignments: `CC:4040-4048` + `CC:4799-4805` (the H.264 release), `CC:5751-5790` (stop order), `CC:6833-6900` (what `requeueRequest` touches: `controlsMutex_`, `photoCaptureMutex_`, `camera_->queueRequest`, which libcamera documents as callable from any thread).

## 3. Find it yourself

**3.1 Where does the request go back today?** (Pi)

```bash
grep -n 'requeueRequest(request);' /home/pi/ApertarCore/src/camera/CameraController.cpp
grep -n 'if (recordProcessedPreviewFrame(request)) return;' /home/pi/ApertarCore/src/camera/CameraController.cpp
```

Prediction: one call at the end of `requestComplete`, and the H.264 path already returns early when it hands the request to a worker. Raw will do the same.

**3.2 How busy is the thread, really?** (Pi, Core recording at 30 fps in 16-bit)

```bash
P=$(pgrep -x apertar-core); T=$(for t in /proc/$P/task/*; do [ "$(cat $t/comm)" = CameraManager ] && echo ${t##*/}; done | head -1)
python3 -I ~/apertar-kb/working/tools/usample.py $P $T 5          # top symbols on the CameraManager thread
```

Prediction: `do16BitEndianSwap`/`rev16` and `RawStatsProducer::process` on top, then `memcpy` (Core's copy) and the ioctl (dma-buf sync). After this tutorial the memcpy and ioctl should vanish from this thread.

**3.3 What does the H.264 recorder do with `release`?** (Pi)

```bash
grep -n 'job.release = std::move(releaseCallback);' /home/pi/ApertarCore/src/camera/CameraController.cpp
grep -n 'static void releasePreviewJob' /home/pi/ApertarCore/src/camera/CameraController.cpp
```

> [!tip]- Answer
> `enqueueFrame` stores the callback in the job (`CC:4367`); `releasePreviewJob` runs it from the worker after the copy (`CC:4799-4805`). The callback is `requeueRequest` wrapped by the session. Same idea below.

## 4. Make the change

All in `/home/pi/ApertarCore/src/camera/CameraController.cpp`. Lines at `f60e301` + T23/T24 shifts; use the search strings. The reference patch has every hunk.

**4.1 A dma-buf sync helper both classes can call** (search `static bool syncCpuReadBuffer(int fd, bool begin)`)

`syncCpuReadBuffer` is a static member of `CameraSession`, defined after `DngRecordingQueue`, so the queue cannot call it. Add a free function in the anonymous namespace next to `activeRawFrameBytes` (T24 and its `alignedRawData` are skipped; see the status line):

```cpp
// CPU-cached dma-bufs need a sync before and after the CPU reads them.
bool dmabufCpuSync(int fd, bool begin)
{
    dma_buf_sync sync{};
    sync.flags = DMA_BUF_SYNC_READ | (begin ? DMA_BUF_SYNC_START : DMA_BUF_SYNC_END);
    int ret;
    do { ret = ::ioctl(fd, DMA_BUF_IOCTL_SYNC, &sync); } while (ret < 0 && errno == EINTR);
    if (ret < 0)
        std::cerr << "ApertarCore DMA read sync " << (begin ? "START" : "END")
                  << " failed: " << std::strerror(errno) << "\n";
    return ret == 0;
}
```

and make the member a one-liner: `static bool syncCpuReadBuffer(int fd, bool begin) { return dmabufCpuSync(fd, begin); }`.

**Check:** `grep -c 'DMA_BUF_IOCTL_SYNC' src/camera/CameraController.cpp` → 1.

**4.2 The hand-off API in `DngRecordingQueue`** (after `reserveRawPool` from T23, before the `private:` that follows it)

```cpp
    // A frame handed over by libcamera's completion thread without copying it.
    // The copy worker syncs the dma-buf, copies, gives the request back to the
    // camera through the release callback, then queues the frame for writing.
    struct PendingCopy {
        libcamera::Request *request = nullptr;
        int syncFd = -1;                 // CPU-cached dma-buf to sync around the read, -1 if none
        const uint8_t *source = nullptr; // first active byte of the mapped camera buffer
        size_t size = 0;                 // active frame bytes
        bool mapCodes12 = false;         // Clear HDR 12-bit cDNG: map samples back to codes
        RawFrameView view;               // data/size are filled by the worker
        CdngEncoder::Metadata metadata;
    };

    void setRequestRelease(std::function<void(libcamera::Request *)> release, size_t maxHeldRequests)
    {
        std::lock_guard<std::mutex> lock(copyMutex_);
        releaseRequest_ = std::move(release);
        maxHeldRequests_ = std::max<size_t>(1, maxHeldRequests);
    }

    // Completion-thread side. Returns false when the request was not taken: the
    // caller must requeue it itself. Never blocks, never copies.
    bool enqueueCopy(PendingCopy copy)
    {
        std::lock_guard<std::mutex> lock(copyMutex_);
        if (!active_.load(std::memory_order_acquire) || copyThreads_.empty() || !releaseRequest_)
            return false;
        if (heldRequests_ >= maxHeldRequests_) {
            const uint64_t dropped = droppedNoRequestSlot_.fetch_add(1, std::memory_order_relaxed) + 1;
            if (dropWarning_) dropWarning_->markDropped();
            if (dropped == 1 || (dropped % 30) == 0)
                std::cerr << "ApertarCore drop[copy-slot]: frame=" << copy.metadata.frameIndex
                          << " held=" << heldRequests_ << "/" << maxHeldRequests_
                          << " dropped_total=" << dropped << "\n";
            return false;
        }
        ++heldRequests_;
        copyQueue_.push_back(std::move(copy));
        copyCv_.notify_one();
        return true;
    }
```

Why `active_` and not `stopping_`: `stopping_` belongs to the write queue's `mutex_`; reading it under `copyMutex_` would be a race.

**4.3 The copy worker, release and stop** (right after 4.2, in the `private:` section)

```cpp
    void copyLoop()
    {
        while (true) {
            PendingCopy copy;
            {
                std::unique_lock<std::mutex> lock(copyMutex_);
                copyCv_.wait(lock, [this]() { return copyStopping_ || !copyQueue_.empty(); });
                if (copyQueue_.empty()) {
                    if (copyStopping_)
                        return;
                    continue;
                }
                copy = std::move(copyQueue_.front());
                copyQueue_.pop_front();
            }

            std::vector<uint8_t> rawCopy = acquireRawBuffer(copy.size + kRawCopyAlignment);
            uint8_t *const rawData = alignedRawData(rawCopy);
            const bool copied = copy.syncFd < 0 || dmabufCpuSync(copy.syncFd, true);
            if (copied) {
                std::memcpy(rawData, copy.source, copy.size);
                if (copy.syncFd >= 0)
                    dmabufCpuSync(copy.syncFd, false);
            }
            // The camera buffer is free from here on; everything below works on the copy.
            releaseHeldRequest(copy.request);
            if (!copied) {
                recycleRawBuffer(std::move(rawCopy));
                if (dropWarning_) dropWarning_->markDropped();
                continue;
            }
            if (copy.mapCodes12)
                compressClearHdrFrame(rawData, copy.size, copy.view.width, copy.view.height, copy.view.stride);
            copy.view.data = rawData;
            copy.view.size = copy.size;
            enqueue(std::move(rawCopy), copy.view, std::move(copy.metadata));
        }
    }

    void releaseHeldRequest(libcamera::Request *request)
    {
        std::function<void(libcamera::Request *)> release;
        {
            std::lock_guard<std::mutex> lock(copyMutex_);
            if (heldRequests_ > 0)
                --heldRequests_;
            release = releaseRequest_;
        }
        if (release && request)
            release(request);
    }

    void stopCopyWorkers()
    {
        {
            std::lock_guard<std::mutex> lock(copyMutex_);
            copyStopping_ = true;
        }
        copyCv_.notify_all();
        for (std::thread &worker : copyThreads_) {
            if (worker.joinable())
                worker.join();
        }
        copyThreads_.clear();
        // Frames still waiting for a copy are lost with the take; their requests go back.
        std::deque<PendingCopy> leftover;
        {
            std::lock_guard<std::mutex> lock(copyMutex_);
            leftover.swap(copyQueue_);
        }
        for (PendingCopy &copy : leftover)
            releaseHeldRequest(copy.request);
    }
```

Why the release comes **before** the 12-bit mapping: the mapping works on the copy; the camera buffer is needed by the CFE, not by us.

**4.4 Members** (next to `std::atomic<uint64_t> writeFailures_{0};` in the queue's member list, search `RecordingFailure failure_;` inside `DngRecordingQueue`)

```cpp
    // Copy workers (completion-thread hand-off).
    std::mutex copyMutex_;
    std::condition_variable copyCv_;
    std::deque<PendingCopy> copyQueue_;
    std::vector<std::thread> copyThreads_;
    bool copyStopping_ = false;
    size_t heldRequests_ = 0;
    size_t maxHeldRequests_ = 1;
    std::function<void(libcamera::Request *)> releaseRequest_;
    std::atomic<uint64_t> droppedNoRequestSlot_{0};
```

**4.5 Start and stop with the write workers** (`startAtFolder`, search `workers_.emplace_back(&DngRecordingQueue::workerLoop, this);`; and `stop()`, search `stopping_ = true;` in the queue)

After the write workers are created and before `active_.store(true, ...)`:

```cpp
        {
            std::lock_guard<std::mutex> lock(copyMutex_);
            copyStopping_ = false;
            heldRequests_ = 0;
        }
        droppedNoRequestSlot_.store(0, std::memory_order_relaxed);
        const unsigned int copyWorkers = unsignedEnvValue("APERTAR_RAW_COPY_WORKERS", 1, 1, 2);
        for (unsigned int i = 0; i < copyWorkers; ++i)
            copyThreads_.emplace_back(&DngRecordingQueue::copyLoop, this);
```

In `stop()`, right after `active_.store(false, std::memory_order_release);` and before `stopping_ = true`:

```cpp
        stopCopyWorkers();
```

and after `workers_.clear();`:

```cpp
        if (const uint64_t dropped = droppedNoRequestSlot_.load(std::memory_order_relaxed); dropped > 0)
            std::cerr << "ApertarCore recording stats: dropped_copy_slot=" << dropped << "\n";
```

Why copy workers stop first: their last `enqueue()` calls must land before the write workers drain.

**Check:** `grep -c 'copyLoop\|stopCopyWorkers' src/camera/CameraController.cpp` → 4.

**4.6 The session gives the recorder a way to requeue** (`CameraSession::start()`, search `if (!makeRequests(error))`; insert after the `return false;`)

```cpp
        // Raw frames are copied on a recorder worker; the worker gives the request
        // back here. Hold at most buffers-2 so the CFE always has two queued.
        recorder_.setRequestRelease([this](libcamera::Request *request) {
            std::shared_lock settingsLock(sessionSettingsMutex_);
            if (!running_.load())
                return;
            requeueRequest(request);
        }, static_cast<size_t>(std::max(1, static_cast<int>(rawCameraBufferCount(settings_.clearHdr)) - 2)));
```

Why the shared lock: `requeueRequest` reads `settings_` through `controlsForSettings`; the completion thread holds the same shared lock when it calls it (`CC:6924`).

**4.7 The hand-off itself** (`requestComplete`, search `recordRawFrame(request, whiteBalance);`, and `recordRawFrame`, search `void recordRawFrame(libcamera::Request *request`)

In `requestComplete`:

```cpp
                    if (recordProcessedPreviewFrame(request)) return;
                    if (recordRawFrame(request, whiteBalance)) return;
```

`recordRawFrame` becomes `bool` and every early `return;` becomes `return false;`. Replace everything from `// The completion callback is the only producer.` to the end of the function with:

```cpp
        // The completion callback is the only producer. If workers are already
        // behind, reject before handing over a frame that cannot be queued.
        if (!recorder_.hasCapacityForFrame(frameIndex))
            return false;

        DngRecordingQueue::PendingCopy copy;
        copy.request = request;
        copy.syncFd = cachedRawBuffers_.empty() ? -1 : buffer->planes().front().fd.get();
        copy.source = mapped.data + activeOffsetBytes;
        copy.size = rawSize;
        copy.mapCodes12 = clearHdrStoresCodes12(settings_) && rawInfo.packing == PixelPacking::Unpacked &&
            rawInfo.unpackedBytesPerSample == 2u && rawInfo.bitDepth == RawBitDepth::Bits12;
        copy.view.width = rawInfo.width;
        copy.view.height = rawInfo.height;
        copy.view.stride = rawInfo.stride;
        copy.view.bitDepth = rawInfo.bitDepth;
        copy.view.unpackedBytesPerSample = rawInfo.unpackedBytesPerSample;
        copy.view.sampleBits = settings_.rawBitDepth;
        copy.view.packing = rawInfo.packing;
        copy.view.bayerPattern = rawInfo.pattern;
        copy.view.timestampUs = timestampUs;
        copy.metadata = std::move(metadata);

        if (!recorder_.enqueueCopy(std::move(copy)))
            return false;
        if (frameIndex == 0)
            gyroRecorder_.setVideoStartTimestampUs(static_cast<uint64_t>(std::max<int64_t>(0, timestampUs)), frameIndex);
        audioRecorder_.observeVideoFrame(timestampUs, frameDurationUs);
        return true;
    }
```

`copyRawBytes` stays: the still-photo path uses it.

**Check:** `grep -c 'return;' <(sed -n '/bool recordRawFrame(libcamera::Request/,/void capturePhotoFrame/p' src/camera/CameraController.cpp)` → 0.

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | grep -E 'error|Built target' | head -20
sudo systemctl restart apertar-core
```

First a safety pass (threading): 3 takes at 25 fps, a mode change 12 ↔ 16-bit while idle, a `record_stop` during heavy load, a Clear HDR off/on. No hang, no crash, `journalctl -u apertar-core -b | grep -c 'drop\[copy-slot\]'` is 0 at 25 fps.

Then the numbers:

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=30
P=$(pgrep -x apertar-core); T=$(for t in /proc/$P/task/*; do [ "$(cat $t/comm)" = CameraManager ] && echo ${t##*/}; done | head -1)
python3 -I ~/apertar-kb/working/tools/core.py record_start >/dev/null; python3 -I ~/apertar-kb/working/tools/usample.py $P $T 5; python3 -I ~/apertar-kb/working/tools/core.py record_stop >/dev/null
~/apertar-kb/working/tools/takes.sh 3 10
```

Success: `usample.py` shows no `memcpy`/ioctl share on the CameraManager thread (Core's share ≈ 0 %; the thread falls to ~45 % at 30 fps 16-bit), `takes.sh` at 30 fps writes 291/291 (16-bit uncompressed) with `ipa rate=30.00`, no `has no buffer` lines (T22 4.6), `dropped_copy_slot` absent from the stats line.

If 30 fps is still short, the remaining cost is libcamera's two passes (15 ms): the next step is in our libcamera fork, not Core (compare answer §3, step 4).

## 6. Commit and push

```bash
git -C ~/ApertarCore add src/camera/CameraController.cpp
git -C ~/ApertarCore commit -m "camera: copy raw frames on a recorder worker, not on libcamera's completion thread

Why: at 30 fps the completion thread spent ~23 of 33 ms per frame (libcamera's
swap and stats plus Core's sync and 16.9 MB copy); the CFE then found no buffer
queued. The callback now hands the request to a copy worker that requeues it
after the copy; at most buffers-2 requests are held.
Tested: usample.py (no memcpy on the CameraManager thread), takes.sh 3 at
30 fps, no 'has no buffer' lines."
git -C ~/ApertarCore push -u origin main
~/.claude/skills/apertar-dev/scripts/apertar_status.sh
```

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `return-statement with no value, in function returning 'bool'` | an early `return;` left in `recordRawFrame` | 4.7 |
| `'PendingCopy' was not declared` in `CameraSession` | the struct is private or declared after use | it must be `public` in `DngRecordingQueue` (4.2) |
| record_stop hangs | copy worker waiting on `copyCv_` with `copyStopping_` never set | `stopCopyWorkers()` must run in `stop()` (4.5) |
| crash on mode change | a worker touched the mapping after `unmapRawBuffers()` | `recorder_.stop()` must come before `unmapRawBuffers()` (it does at `CC:5770-5783`); check you did not reorder |
| `drop[copy-slot]` lines at 25 fps | copies slower than frames, or too few buffers | `APERTAR_RAW_COPY_WORKERS=2`; T23's buffer count |
| the preview freezes while recording | requests never returned | `releaseHeldRequest` not called on an error path (4.3) |
| libcamera `queueRequest` error after stop | release fired after `camera_->stop()` | the `running_` guard in 4.6 |

Undo: `git -C ~/ApertarCore checkout -- src/camera/CameraController.cpp`, rebuild.

## 8. What you learned, going further

- A libcamera request is a token: whoever holds it owes the CFE a buffer. Count holders.
- The completion thread should only route; everything with a cost belongs to a worker.
- Exercise: add `held=` to the periodic `capture stats:` line.
- Upstream: this plus T23 is the "copy off the hot path" change Apertar-Studio's main also lacks.

## 9. Sources

- `working/clearhdr-compare-answer.md` §3; `working/patches/0001-camera-copy-raw-frames-on-a-recorder-worker-not-on-l.patch`.
- `Apertar-Core/src/camera/CameraController.cpp@f60e301:4040-4048, 4367, 4799-4805, 5751-5790, 6762-6772, 6833-6900, 6915-7008, 7189-7287`.
- cinepi-raw: `cinepi/cinepi_recorder.hpp:49-105, 158-174@63a08d5`; `core/rpicam_app.cpp:255, 1212-1241`.
- Kernel: `rp1_cfe/cfe.c:615-631@5bd564a`.

%% tutor
ref core src/camera/CameraController.cpp 4817 static void releasePreviewJob(PreviewJob &job)
ref core src/camera/CameraController.cpp 5775 camera_->requestCompleted.disconnect(this, &CameraSession::requestComplete);
ref core src/camera/CameraController.cpp 6781 static bool syncCpuReadBuffer(int fd, bool begin)
ref core src/camera/CameraController.cpp 6853 void requeueRequest(libcamera::Request *request)
ref core src/camera/CameraController.cpp 6935 void requestComplete(libcamera::Request *request)
ref core src/camera/CameraController.cpp 7019 if (recordProcessedPreviewFrame(request)) return;
ref core src/camera/CameraController.cpp 7209 void recordRawFrame(libcamera::Request *request, const WhiteBalanceMeasurement &whiteBalance)
check 3.1 | grep -c 'requeueRequest(request);' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[0-9]+$
check 4.1 | grep -c 'DMA_BUF_IOCTL_SYNC' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.2 | grep -c 'bool enqueueCopy(PendingCopy copy)' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.5 | grep -c 'copyLoop\|stopCopyWorkers' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^4$
check 4.6 | grep -c 'recorder_.setRequestRelease' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.7 | grep -c 'if (recordRawFrame(request, whiteBalance)) return;' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
%%

#CINEMATE
#APERTAR
