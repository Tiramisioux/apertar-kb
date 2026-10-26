---
datum: 2026-10-26 04:15:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T23 requests-follow-buffers
typ: digital anteckning
---

# T23. One libcamera request per raw buffer, 8 buffers in Clear HDR, a warm raw pool

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-camera-one-libcamera-request-per-raw-buffer-8-buffer.patch` is the reference, not compiled). Needs T22's baseline numbers. Builds **M7** (the sensor path) and the libcamera request loop.

**You will learn**
- How Core turns buffers into libcamera requests, and why the "8 buffers" experiment never used buffers 4-8.
- Where the raw copy pool lives and why every take started with six 16.6 MB zero-fills on the completion thread.
- The journal lines that prove how many buffers the camera really has.

**Risk:** Core rebuild and restart only. Memory: 8 × 16.9 MB raw + 8 × 1.4 MB preview ≈ 146 MB extra while Clear HDR is on. Undo: `git checkout -- src/camera/CameraController.cpp`, rebuild, or set `APERTAR_RAW_CAMERA_BUFFERS=4` in the service environment. **Time:** 1.5 h.

## 1. The problem

`working/clearhdr-design.md` (2026-10-26): "Change (a), 8 raw + preview buffers in Clear HDR: no effect". The journal said `RAW buffers: CPU-cached heap=... count=8`, yet the loss pattern did not move. Also: "3 of 4 first takes after a (re)configure were lossy, later ones clean".

Expected: more buffers = more slack for the CFE. Reality: only three requests circulated, so the CFE never saw more than two queued frames whatever the count.

## 2. How this part works

A libcamera `Request` carries one buffer per stream. Core allocates N buffers per stream, then **creates requests and attaches buffer i to request i** (`CC:6788-6831`, `makeRequests`). Only requests reach the camera; a buffer without a request is just memory.

```
 configure(): previewConfig.bufferCount = N, rawConfig.bufferCount = N      (CC:6411-6444)
 allocate():  N preview + N raw buffers (raw from the CPU-cached heap)      (CC:6650-6668)
 makeRequests(): requestCount = min(N, kActiveRequestCount = 3)             (CC:1048, CC:6796-6798)   <-- the cap
 start():     queue the 3 requests                                           (CC:6700-6708)
 requestComplete(): ... copy ... requeueRequest()                            (CC:6915-7008)
```

With 3 requests: one is inside libcamera's byte swap and stats, one is in Core's callback (copy), and the CFE has at most **one** queued. The kernel refuses the next frame as soon as any of its nodes has nothing queued (T22 §2).

The raw copy pool (`DngRecordingQueue`): `acquireRawBuffer` (`CC:3657`) reuses vectors from `rawPool_`; `recycleRawBuffer` (`CC:3970`) puts them back, up to `preferredRawPoolSize()` = workers + 2 (`CC:3992`). But `stop()` clears the pool (`CC:3596-3598`), so every take starts cold: the first ~6 frames each allocate and zero-fill 16.6 MB **on libcamera's completion thread** (`std::vector<uint8_t>(size)` at `CC:3670`).

Reading assignments: `CC:6788-6831`, `CC:3657-3680`, `CC:3970-3995`, `CC:3594-3600`.

## 3. Find it yourself

**3.1 How many requests does a Clear HDR session really queue?** (Pi, read-only)

```bash
grep -n 'kActiveRequestCount' /home/pi/ApertarCore/src/camera/CameraController.cpp      # the constant and its one use
grep -n 'requestCount = std::min' /home/pi/ApertarCore/src/camera/CameraController.cpp
```

Prediction: a constant 3 and a `std::min` that caps requests at it. How many of the 4 (or 8) buffers can the CFE hold while Core copies one and libcamera swaps one?

> [!tip]- Answer
> Two of three requests are busy in software; the CFE holds one. With 8 buffers the answer was identical, because `requestCount` was still 3 (`CC:6796-6800`). The 8-buffer test measured nothing about buffers.

**3.2 What happens to the pool when a take stops?** (Pi)

```bash
grep -n 'rawPool_.clear()' /home/pi/ApertarCore/src/camera/CameraController.cpp
grep -n 'std::vector<uint8_t>(size)' /home/pi/ApertarCore/src/camera/CameraController.cpp
```

Prediction: cleared in `stop()`; a fresh allocation whenever the pool is empty. Which thread runs `acquireRawBuffer`?

> [!tip]- Answer
> `recordRawFrame` (`CC:7268`), i.e. libcamera's completion thread. A fresh 16.6 MB vector means 4050 page faults and a memset there, on each of the first ~6 frames of every take.

**3.3 Baseline.** Keep T22's "16-bit take" rows (25 and 30 fps) and the `has no buffer` count. You compare against them in §5.

## 4. Make the change

All in `/home/pi/ApertarCore/src/camera/CameraController.cpp`. Lines are at `f60e301`; the search string finds them if they moved.

**4.1 Name the Clear HDR buffer count** (`CC:1047-1048`, search `kActiveRequestCount = 3`)

Replace the two constants with:

```cpp
constexpr unsigned int kConfiguredBufferCount = 4;
// Clear HDR raw is unpacked 16-bit (16.9 MB per buffer on the CPU-cached heap).
// libcamera's thread holds one buffer for its byte swap and stats, the completion
// callback holds one for the copy, so the CFE needs more than two left to queue.
constexpr unsigned int kClearHdrBufferCount = 8;
```

Why: `kActiveRequestCount` disappears on purpose; a request count that differs from the buffer count is the bug.

**Check:** `grep -c kActiveRequestCount src/camera/CameraController.cpp` → 1 for now (the use at `makeRequests`, fixed in 4.3).

**4.2 A helper with an env override** (after `proresCameraBufferCount()`, `CC:1154-1158`, search `APERTAR_PRORES_CAMERA_BUFFERS`)

```cpp
// Raw (cDNG/MLV) camera buffers. Every buffer is attached to its own libcamera
// request, so this is also the number of requests in flight.
unsigned int rawCameraBufferCount(bool clearHdr)
{
    return unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS",
                            clearHdr ? kClearHdrBufferCount : kConfiguredBufferCount, 3, 16);
}
```

Why: the same pattern the H.264 and ProRes paths use; the env var lets you A/B without rebuilding (`Environment=APERTAR_RAW_CAMERA_BUFFERS=4` in a `systemctl edit apertar-core` drop-in).

**4.3 Buffers and requests from the same number** (`CC:6411-6413`, search `: kConfiguredBufferCount;` and `CC:6796-6797`, search `: kActiveRequestCount;`)

In `configure`:

```cpp
                const unsigned int configuredBufferCount = proresMode ? proresCameraBufferCount() : processedYuvMode
                    ? h264CameraBufferCount()
                    : rawCameraBufferCount(sanitized.clearHdr);
```

In `makeRequests`:

```cpp
        // One request per buffer: a buffer without a request can never reach the CFE.
        const size_t activeRequestLimit = processedYuvMode && settings_.recordingFormat == RecordingFormat::Prores ? proresCameraBufferCount()
            : processedYuvMode ? h264CameraBufferCount() : rawCameraBufferCount(settings_.clearHdr);
```

**Check:** `grep -c kActiveRequestCount src/camera/CameraController.cpp` → 0; `grep -c 'rawCameraBufferCount(' src/camera/CameraController.cpp` → 3.

**4.4 Keep the pool across takes** (`CC:3594-3599`, search `rawPool_.clear();`)

Delete the three lines `rawPool_.clear(); pooledRawBytes_ = 0; expectedRawBufferSize_ = 0;` from `stop()` and leave a comment:

```cpp
        queue_.clear();
        // The raw copy pool survives the take: the next take's first frames would
        // otherwise allocate and page in 16.6 MB each on libcamera's completion thread.
        workerCount_ = 0;
```

Why it is safe: within one camera session the frame size is constant, `recycleRawBuffer` still bounds the pool (`CC:3975-3985`), and the whole `DngRecordingQueue` dies with the session on a mode change.

**4.5 Pre-fill the pool when the frame size is known** (two edits)

After `preferredRawPoolSize()` (`CC:3992-3995`, search `size_t preferredRawPoolSize() const`), add a public method (the class is in a `private:` run there, so open `public:` and close it again):

```cpp
public:
    // Pre-fill the raw copy pool once the frame size is known, so no take starts
    // with fresh zero-filled allocations on libcamera's completion thread.
    void reserveRawPool(size_t frameBytes, size_t count)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (frameBytes == 0)
            return;
        expectedRawBufferSize_ = frameBytes;
        while (rawPool_.size() < count) {
            std::vector<uint8_t> buffer(frameBytes);
            pooledRawBytes_ += buffer.capacity();
            rawPool_.push_back(std::move(buffer));
        }
    }

private:
```

In `CameraSession::start()`, right after the raw buffers are mapped (`CC:6666-6667`, search `if (rawStream_ && !mapRawBuffers(error))`):

```cpp
        if (rawStream_ && !processedYuvMode && rawStreamInfo_.valid)
            recorder_.reserveRawPool(activeRawFrameBytes(rawStreamInfo_.stride, rawStreamInfo_.height), 6);
```

Why 6: uncompressed cDNG runs 4 workers + 2 queued (`preferredRawPoolSize`), so six buffers cover the steady state; 6 × 16.6 MB = 100 MB held while the camera is open.

**Check:** `grep -n 'reserveRawPool' src/camera/CameraController.cpp` → the definition and one call.

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | tail -3          # "Built target apertar-core"
sudo systemctl restart apertar-core
journalctl -u apertar-core -b --no-pager | grep -E 'RAW buffers:|camera configured:' | tail -2
```

Expected with Clear HDR on: `RAW buffers: CPU-cached heap=... count=8 frame_bytes=16896000` (16-bit) or `16588800` (12-bit).

Then the measurement from T22, before/after:

```bash
~/apertar-kb/working/tools/takes.sh 3 10            # 25 fps: expect missing=0 on every take if the drops were buffer starvation; unchanged if they are writeback (T24)
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=30
~/apertar-kb/working/tools/takes.sh 3 10            # 30 fps: compare "missing=" with T22's row; count "has no buffer" lines as in T22 4.6
```

Prediction to write down first: does the 25 fps writeback loss change? (It should not; it is not a buffer problem.) Does the 30 fps loss shrink? (Partly: the CFE now has up to 6 queued frames of slack instead of 1.)

What success looks like: `count=8` in the journal, the first take after a reconfigure no longer worse than the later ones, fewer `has no buffer` lines at 30 fps. `free -m` shows ~150 MB less free with Clear HDR on.

## 6. Commit and push

On the Pi:

```bash
git -C ~/ApertarCore add src/camera/CameraController.cpp
git -C ~/ApertarCore commit -m "camera: one libcamera request per raw buffer, 8 buffers in Clear HDR, raw pool kept warm

Only three requests circulated whatever the buffer count, so extra raw
buffers never reached the CFE. Requests now follow the configured count
(APERTAR_RAW_CAMERA_BUFFERS, default 4, 8 in Clear HDR). The raw copy pool
is pre-filled at session start and kept across takes.

Why: Clear HDR 16-bit takes lose single frames; the CFE needs buffers queued
on all four of its nodes and had at most one.
Tested: journal count=8; takes.sh 3 at 25 and 30 fps, numbers in
apertar-kb lessons/hardware-log.md 2026-10-xx."
git -C ~/ApertarCore push -u origin main
~/.claude/skills/apertar-dev/scripts/apertar_status.sh
```

Add the numbers to `lessons/hardware-log.md` and a row to `fork-log.md`.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `error: 'kActiveRequestCount' was not declared` | a use you did not replace | `grep -n kActiveRequestCount`, apply 4.3 |
| `Failed to allocate libcamera frame buffers.` in the journal | the cached heap could not give 8 × 16.9 MB | `grep Cma /proc/meminfo` is irrelevant (system heap); check `free -m`; try `APERTAR_RAW_CAMERA_BUFFERS=6` |
| `reserveRawPool` not found | the method landed in the wrong class | it belongs to `DngRecordingQueue`, next to `preferredRawPoolSize()` |
| camera starts, preview fine, but SDR cDNG at 4K now shows `count=4` and 4 requests | expected: SDR keeps 4 buffers, now with 4 requests instead of 3 | nothing |
| no change at 25 fps | the 25 fps loss is writeback (T22) | T24 |

Undo: `git -C ~/ApertarCore checkout -- src/camera/CameraController.cpp`, rebuild, restart.

## 8. What you learned, going further

- A libcamera buffer only works when it is attached to a request; count requests, not buffers.
- Allocation on a hot thread is a per-take cost you only see in the first second.
- Exercise: log `requests_.size()` once at start (next to `RAW buffers:`), so the journal always states the in-flight count.
- Upstream: `kActiveRequestCount = 3` is in Apertar-Studio `main` too; offer this with the measurement.

## 9. Sources

- `Apertar-Core/src/camera/CameraController.cpp@f60e301`: `:1047-1048`, `:1148-1158`, `:3594-3600`, `:3657-3680`, `:3970-3995`, `:6411-6444`, `:6650-6708`, `:6788-6831`.
- `working/clearhdr-compare-answer.md` §3 (B2, B3); `working/patches/0001-camera-one-libcamera-request-per-raw-buffer-8-buffer.patch`.
- cinepi-raw for comparison: `--buffer-count 8`, 8 requests in flight (`cinepi-raw/core/rpicam_app.cpp:630-658@63a08d5`).

%% tutor
ref core src/camera/CameraController.cpp 1047 constexpr unsigned int kConfiguredBufferCount = 4;
ref core src/camera/CameraController.cpp 1048 constexpr unsigned int kActiveRequestCount = 3;
ref core src/camera/CameraController.cpp 1154 unsigned int proresCameraBufferCount()
ref core src/camera/CameraController.cpp 6411 const unsigned int configuredBufferCount = proresMode ? proresCameraBufferCount() : processedYuvMode
ref core src/camera/CameraController.cpp 6796 const size_t activeRequestLimit = processedYuvMode
ref core src/camera/CameraController.cpp 3596 rawPool_.clear();
ref core src/camera/CameraController.cpp 3992 size_t preferredRawPoolSize() const
ref core src/camera/CameraController.cpp 6666 if (rawStream_ && !mapRawBuffers(error))
ref core src/camera/CameraController.cpp 6788 bool makeRequests(std::string *error)
check 3.1 | grep -c 'kActiveRequestCount' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[0-9]+$
check 4.1 | grep -c 'kClearHdrBufferCount = 8' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.3 | grep -c 'kActiveRequestCount' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^0$
check 4.4 | grep -c 'rawPool_.clear()' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^0$
check 4.5 | grep -c 'reserveRawPool' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 5 | journalctl -u apertar-core -b --no-pager | grep 'RAW buffers:' | tail -1 | count=8
%%

#CINEMATE
#APERTAR
