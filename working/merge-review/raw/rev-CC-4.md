# Review CC-4: CameraController.cpp, CameraSession (port lines 7391-9614)

Stage 2 (review). Port = `@cinemate-port` `01f170c`, `/home/user/Apertar-Core`. Upstream = `@upstream-1.6.0`, `/home/user/wt/core-upstream`.
Fork main = `@main`, `/home/user/wt/core-main`. Diff read whole: `/home/user/build/review/diffs/CC.part04.diff` (1363 lines).
Yardstick: `raw/conv-core-camera.md` (rule ids S*, I*, N*, R*, section 5.*). `apertar-conventions.md` does not exist yet.

Scope note (same as inventory): the HINT (controller setters, sanitising, ISO limits, ladder) is not this slice. The slice is the
`CameraSession` middle and end. Setters and the sanitiser body are other units; only their call sites are here.

## Findings

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| CC-4-F1 | DNG copy worker gets the request back through a set-once `setRequestRelease`, not a per-frame release closure | mismatch | major | yes |
| CC-4-F2 | Colour IMX585 lost the auto sensor-config fallback for raw12 crop sizes | removed-upstream-behaviour | major | yes |
| CC-4-F3 | Storage pre-roll fps bypasses the sanitiser and re-pins FrameDurationLimits per request | mismatch | major | yes |
| CC-4-F4 | Dead back-end fps cap wrapper (`applyBackendCap` + `backendMaximumFps` always `nullopt`) | slop | minor | yes |
| CC-4-F5 | Internal vocabulary in comments (T31, hardware-log date, qbc, Cinemate, kb path) | slop | minor | no |
| CC-4-F6 | Phase lock: servo shape fits, socket telemetry does not | new-ground | minor | yes |
| CC-4-F7 | Speed ramp: frame index by count, fps free during a take, external `rubberband` | new-ground | minor | yes |
| CC-4-F8 | IMX585 and IMX283 exact-mode checks duplicate the PISP_COMP1 bit-depth logic | duplication | minor | no |
| CC-4-F9 | Raw buffer count evaluated three times per configure from live media state; no board-aware cap | pi-compat | minor | unknown |
| CC-4-F10 | `syncfs` at every stop reverses N10 "clip frames are not synced" | new-ground | minor | yes |
| CC-4-F11 | Two real-time scheduling knobs for one A/B (`APERTAR_RT`, `APERTAR_RT_CAPTURE_PRIORITY`) | slop | minor | yes |
| CC-4-F12 | Session data members declared in the public section | mismatch | nit | no |

### CC-4-F1 Request hand-off to the DNG copy worker (mismatch, major)

Port, confirmed:
- `CameraController.cpp:8731-8739@cinemate-port`, after `makeRequests`:
  `recorder_.setRequestRelease([this](libcamera::Request *request) { std::shared_lock settingsLock(sessionSettingsMutex_); if (!running_.load()) return; requeueRequest(request); }, max(1, rawCameraBufferCount(clearHdr) - 2));`
  and `recorder_.setFrameQueued([this](int64_t ts, int64_t dur) { audioRecorder_.observeVideoFrame(...); });`
- `CameraController.cpp:5032-5041@cinemate-port` `struct PendingCopy { libcamera::Request *request = nullptr; int syncFd = -1; ... }`: the recorder class
  stores a libcamera type and calls back into the session by pointer (`releaseHeldRequest`, `:5151-5162`).
- `recordRawFrame` `:9498-9516` fills `PendingCopy` and calls `recorder_.enqueueCopy`.

Upstream, confirmed: a recorder that holds a camera buffer gets a per-frame closure in its enqueue call and never sees a `Request`:
- ProRes `CameraController.cpp:7419-7425@upstream-1.6.0`
  `proresRecorder_.enqueueFrame(..., [this, request, cachedFd] { if (cachedFd >= 0) syncCpuReadBuffer(cachedFd, false); requeueRequest(request); });`
- H.264 `:7456-7465` `const auto releaseRequest = [this, request]() { requeueRequest(request); }; h264Recorder_.enqueueFrame(..., releaseRequest);`
  and the job field `:3937` `std::function<void()> release;`.
- ProRes queue capacity derives from the camera buffer count at take start (`ProresRecorder.cpp:60-65`), not from a setter on the session.
- The ProRes lambda takes no session lock; `requeueRequest` itself checks `running_ && camera_` (`:6563`).

Why it matters: the original developer already solved "recorder holds the buffer, gives it back" twice, the same way. A third shape
(set-once callback typed on `libcamera::Request *`, plus a second set-once callback for audio) reads as a different author's framework.

Rework (Apertar way):
1. `DngRecordingQueue::enqueueCopy(PendingCopy copy, std::function<void()> release)`; `PendingCopy` loses `request`, gains `std::function<void()> release`.
2. In `recordRawFrame` build the closure like ProRes: `[this, request] { requeueRequest(request); }` (the dma-buf END sync already sits in the worker).
3. Pass the hold limit at take start: `startAtFolder(..., maxHeldRequests)` computed once in `startRecording`, or derive it inside the queue from the buffer count the way ProRes does.
4. Delete `setRequestRelease`, `setFrameQueued`, `releaseRequest_`, `frameQueued_`. Report the audio frame from the same per-frame closure set (a second `std::function<void()> queued` in `PendingCopy`, called after `enqueue` accepts), or keep `observeVideoFrame` on the completion thread at hand-over as ProRes does (`:7428-7430`).
5. Drop the `shared_lock` in the release unless a reason is written down; upstream's ProRes release has none.
Risk: request lifetime at reconfigure. `stop()` joins the recorder before `requests_.clear()` (`:7505-7527`), so a per-frame closure is as safe as the current one.

### CC-4-F2 Colour IMX585 auto fallback removed (removed-upstream-behaviour, major)

Upstream `CameraController.cpp:5993-5996@upstream-1.6.0` (same at `@main:6325-6328`):
```
const bool allowAutoSensorConfigFallback = monochromeSensor_ || sensorFamily_ == SensorFamily::Imx294 ||
                                           sensorFamily_ == SensorFamily::Imx577 ||
                                           (sensorFamily_ == SensorFamily::Imx585 &&
                                            isImx585Raw12CropResolution(sanitized.resolution));
```
Port `:8295-8296@cinemate-port`: the IMX585 clause is gone. New block `:8485-8530` then refuses any colour IMX585 candidate whose raw size,
bit depth or `ScalerCropMaximum` differs from the `Imx585Modes.hpp` row. Commit `caa0153`: "Colour IMX585 configures explicitly only and
refuses a mode the driver adjusted". Tested: desk only.

Upstream lists nine 3840-wide raw12 crop sizes (`isImx585Raw12CropResolution`, `:385-396@upstream-1.6.0`) for which the explicit
config may fail and the auto config is accepted. **Probable**: with the Apertar baseline driver (`imx585-v4l2-driver` `origin/apertar`
`e5b74d3`), which the port's Core must still run on, these sizes now fail to configure ("libcamera rejected camera configurations").
Settle: on a Pi with the `origin/apertar` driver, `set_resolution` 3840x1744 12-bit and read `ApertarCore camera configured` / the rejection log.

Rework: restore the upstream clause; run the new exact-mode check only when `useExplicitSensorConfig` is true (the explicit path is where a
driver-adjusted mode is a defect). With the port driver nothing changes; with the old driver the old fallback still works. Effort S.

### CC-4-F3 Storage pre-roll side channel (mismatch, major)

Port, confirmed:
- `applyControls` `:7574-7576`: after `sanitizeSettingsForSensor`, `if (prerollFps > 0.0) sanitized.fps = prerollFps;` with the comment
  "the sensor's own maximum, past the lossless-JPEG and ladder caps the sanitiser applies". `settings_ = sanitized` then stores it.
- `requeueRequest` `:9074-9079`: a second `FrameDurationLimits {p, p}` on every request from `prerollPinUs_`.
- 8 atomics and 6 accessors (`:7822-7897`, members `:10327-10340`), `stop()` resets `setPrerollFps(0.0)` (`:7505`).
- Controller side (outside slice) calls `setPrerollFps(target)` before `applySettingsLocked(next, false, commit=false)` (`:12090`) and then
  busy-waits `waitForFramePeriod` up to 1 s with `mutex_` held.

Upstream, confirmed:
- S15/I2: the sanitise chain is the only place limits are applied; the session reads back effective values (`CC:2707-2744`, `CC:8713-8715`). No path writes a value past it.
- S10: `controlsForSettings` already sets `FrameDurationLimits {d, d}` for video (`:2022-2031@upstream-1.6.0`
  `const int64_t frameDurationRange[2] = { frameDurationUs, maximumFrameDurationUs };`, max = d unless photo mode). A per-request override
  after the merge exists once, for bracket shots (`:6519-6526`).
- Measuring the medium is `runMediaSpeedTest` in `App` (`ApertarCoreApp.cpp:9008-9012@upstream-1.6.0`), not inside the session.

Why it matters: the operator can never record faster than the sanitised maximum, so measuring the card above it measures a take nobody can
shoot, and it needs the only sanitiser bypass in the file plus a second frame-duration pin.

Rework: pre-roll at the sanitised ceiling (`maximumFpsForSettings`, which already folds in the lossless cap), applied through the normal
`applySettingsLocked`. Delete `prerollFpsOverride_`, `prerollPinUs_`, `setPrerollFps`, the override in `applyControls`, the pin in
`requeueRequest` and the reset in `stop()`. Keep the frame/timestamp measurement (`prerollMeasuring_`, `prerollFrames_`, first/last) as
the only session state. Effort M.

### CC-4-F4 Dead back-end cap wrapper (slop, minor)

Port `:8634-8639`: `fpsceiling::applyBackendCap(maximumSupportedFpsForResolution(...), backendMaximumFps(effectiveSettings, sensorFamily_))`.
`backendMaximumFps` (`:3426-3434@cinemate-port`) is `(void)settings; (void)sensorFamily; return std::nullopt;` with a history comment
"Removed (User, 2026-11-03) ... (KB working/research-30fps-answer.md ...)". Same wrapper in `prerollMaximumFps` `:3486-3491` and at `:3470`.
Fork main `:6589-6592@main` is the plain call. Rework: revert the slice call to the `@main` form; delete `backendMaximumFps` and
`fpsceiling::applyBackendCap`; keep `FpsCeiling.hpp` only for the helpers still used. Effort S.

### CC-4-F5 Internal vocabulary in comments (slop, minor)

Confirmed `@cinemate-port`: `:8902` "(T31)", `:9451` "Speed ramping (T31)", `:8907` "Cinemate kept them as live keys", `:9063`
"the qbc libcamera's IMX585 helper", `:9066` "hardware-log 2026-10-26", `:9068` "as on Cinemate's libcamera", `:9112`
"(kb working/dng-chain, V/H15)", `:8167` "CineMate Log". Upstream I19: comments state a constraint, no ticket numbers, no dates
(`CC:6927-6928@upstream-1.6.0`). Rework: keep the constraint, drop the reference. Example for `:9063-9068`: "A range, not a single
value: a single-value pin makes the IMX585 helper re-choose the line length, which steps the exposure." Effort S.

### CC-4-F6 Phase lock (new-ground, minor, keep + simplify)

No upstream precedent: upstream fps is a static pin in `controlsForSettings`. Shape: `FramePhaseLock.hpp` (158 lines, header-only, pure,
plain numbers) follows S4; the hook `stepFramePhaseLock` is a session member (S3); the per-request override after the merge follows the
bracket precedent (`:6519-6526@upstream-1.6.0`); the gain knobs are env vars read once (I9, read-once lambda precedent
`CdngEncoder.cpp:51-65`); log lines start `ApertarCore phase-lock:` (I6); off by default (`Types.hpp:138`). Weighed: commit `80ddac1`
gives the reason (crystal drift vs audio clock) and the libcamera behaviour that forced `{d, d+1}` (`f4a1393`).
Simplify: five state fields `fps_phase_lock_{active,err_us,dur_us,pushes,saturated}` (`App:9460-9464`) put servo internals in the socket
API, which upstream keeps out (section 5.12 "Frame counts or queue depth in the socket API"; only a boolean leaves Core, 5.7). Keep
`fps_phase_lock_active`; the stop line already prints `max_abs_err_us` and `duration_pushes` (`:7790-7792`). Desk-tested only.

### CC-4-F7 Speed ramp (new-ground, minor, keep behind flag + simplify)

- `recordRawFrame` `:9455` `nextFrameIndex(timestampUs, countOnly=settings_.fpsSpeedRamp)`. Upstream 5.5: "The DNG frame index comes
  from the sensor timestamp, so a dropped frame leaves a gap in the file numbers" (`CC:3518-3526@upstream-1.6.0`). With ramp on, a capture-gap
  drop no longer leaves a gap (queue-full drops still do: the index is taken before `hasCapacityForFrame`). Off by default (`Types.hpp:143`).
- `applyControls` `:7589-7593` `noteFpsChange` runs because fps may change during a take. Upstream N5 refuses it with
  "Stop recording before changing FPS so video and audio keep the same timeline." (`CC:7745@upstream-1.6.0`). The gate change is in the setter (other unit).
- `stopRecording` `:7805` `launchAudioStretch()` forks a detached shell `nice -n 15 rubberband ...` (`:9939`, quoted with `shellQuote`).
  S23: few external dependencies; this one is an undeclared runtime tool, labelled experimental in its own log line.
Weighed: `faa2958` tested on the Pi (C0030-C0032). Verdict: keep the ramp behind `fps_speed_ramp`; drop the stretched WAV from Core
(or ship it as an offline script) and say in the handoff that a ramp take numbers frames by count.

### CC-4-F8 Two exact-mode blocks (duplication, minor)

`:8485-8529` (colour IMX585) and `:8531-8559` (IMX283) each re-derive the raw depth with `formatToRawView`, each carry the
"Pi 5 turns CSI2P into PISP_COMP1, reports 16 bits" exception, each write their own rejection-log line. Upstream puts the readout check
for three sensors in one block with one condition (`:6162-6183@upstream-1.6.0`, `invalidReadout` ternary). Rework: one block
`if (includeRawStream && (Imx585 && !mono || Imx283))` with one helper `rawModeAdjustment(candidateConfig, rawStreamIndex, rawSize,
sensorMode.bitDepth)` returning the reason string; the IMX585 crop-maximum test stays as the one sensor-specific line. Also: binning is
taken from the table (`imx585Row->binned`) here and from properties (`binningFromProperties`, `:8582`) a few lines later; use `sensorBinning_`.

### CC-4-F9 Raw buffer count (pi-compat, minor)

`rawCameraBufferCount(clearHdr)` (`:1458`) is called at `:8381` (buffers), `:8848` (requests) and `:8736` (hold limit) in one configure.
It reads the media tune and media extra for the configured root each time; a mount event between calls gives three different numbers
(probable, the watcher runs on another thread). Clear HDR base is 8; media tune and env allow up to 16 raw buffers, with no board check.
Upstream warns about "large RAW buffers on memory-constrained VC4 boards" (`:6001-6002@upstream-1.6.0`) and keeps 4 (`kConfiguredBufferCount`, `:1023`).
At 4K 16-bit (about 17 MB a frame) 16 buffers are about 270 MB of CMA. Unconfirmed on Pi 4/CM4: settle with
`APERTAR_RAW_CAMERA_BUFFERS=16` + Clear HDR 4K on a Pi 4 and read the allocation log.
Rework: compute once in `configureAndStart` into a member (`rawBufferCount_`) and use it in `makeRequests` and the hold limit; cap the
default by `recordingCapabilities()` like `h264CameraBufferCount` (`:1124-1128@upstream-1.6.0`).

### CC-4-F10 `syncfs` at stop (new-ground, minor, keep + document)

`stopRecording` `:7813-7814` `recorder_.syncToMedium()` (`syncfs` on the clip folder, `:4795-4809`); commit `4ce382e` also adds a 1/s sync
thread during the take (other unit). Upstream N10: "Clip frames are not synced, for throughput" (`AtomicStillFile.hpp:31-32`). Weighed:
commit gives the reason (C0105 lost after a card pull, 30 s dirty expiry). Keep the stop-time sync (it runs after the frames, not per
frame); state the intent change in the handoff. Built, not tested on the Pi.

### CC-4-F11 Two RT knobs (slop, minor)

The slice's `APERTAR_RT_CAPTURE_PRIORITY` (`:9113`) follows R5/I9 (`unsignedEnvValue(name, 0, 0, 99)`, one log line, off by default) and the
per-thread shape of upstream's nice -5 boost (`:6592-6600@upstream-1.6.0`). The older `APERTAR_RT=1` whole-process `chrt` in
`scripts/start-apertar-core.sh:20-39` and `README.md:354` is the same experiment in a second shape. README documenting knobs runs against N11.
Rework: keep the thread knob, remove `APERTAR_RT` from the start script and README (other unit).

### CC-4-F12 Public data members (nit)

`:8180-8188` `mutable std::mutex activeTuningMutex_; std::string activeTuningFile_;` sit between public accessors. Upstream keeps session data
members in the private block at the end (`:7499-7575@upstream-1.6.0`). Move them there.

## Abstraction verdicts (inventory section 5)

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `FramePhaseLock`, `PhaseLockStatus` | keep | Header-only pure logic, S4 shape. Trim the status to `active` for the socket (F6) |
| `stepFramePhaseLock` + phase-lock members | keep | Session member hook, per-request override has the bracket precedent. Strip slop comments (F5) |
| Pre-roll session API (`PrerollMeasure`, `setPrerollFps`, 8 atomics, `waitForFramePeriod`) | simplify | Remove the sanitiser bypass and the pin (F3); keep the measurement |
| New `DngRecordingQueue` API (`setRequestRelease`, `setFrameQueued`, `enqueueCopy`, `PendingCopy`) | rework-to-upstream-pattern | Per-frame release closure as ProRes/H.264 (F1) |
| `MediaFault`, `recordingFault()`, `setMediumDead`, `stop(bool)` | keep | Feeds the upstream latch path (`checkRecordingFailure`, 5.6); `src/util` tiny shared type like `RecordingFailure.hpp` (S6) |
| `MediaProfile`, `cachedMediaSnapshotOrProbe` | simplify | Used here only as a hint at take start; the media tuning file behind it is a recorder-tuning config file, absent by design upstream (N11, 5.12). Judge in its own unit |
| `fpsceiling` | simplify | `applyBackendCap` + `backendMaximumFps` are dead (F4) |
| `apertar::imx585` tables, `Imx283Modes.hpp` | keep | Precedent for a mode table in code: `kImx477Modes` (`:2309-2335@upstream-1.6.0`); 62 and 57 modes do not fit predicates. Header-only per S4 |
| `SensorBinning`, `binningFromProperties` | keep | Small, logged in the configured line (I7). Use it in the IMX585 check (F8) |
| `activeTuningFile_` + mutex, `loadablePath` | keep | Derived tuning has precedent (`ProresIspProfile`, N13). Move members private (F12) |
| Ramp state and helpers | simplify | Keep behind the flag; drop the shelled `rubberband` stretch (F7) |
| `timed` lambda + `stageTimes` in `stopRecording` | keep | Logs only on a dead medium, one line (I7) |

## What conforms (for the handoff)

- `stopRecording(bool mediumGone)` is reached through the upstream supervisor `checkRecordingFailure` (`:12135-12150`), keeps the stop order
  of 5.5 for the recorders, and only adds one line on a dead medium.
- `measuredAnalogueGain()` (`:8152-8161`) copies `measuredWhiteBalance()` exactly: same mutex, same `#else` stub (I18).
- New sensor quirks sit where R1 step 11 puts them: inside the candidate loop after `camera_->configure`, with the same
  `rejectionLog << ... "-bit " << "raw-stream=on "` format (`:8519-8524`, upstream `:6170-6178`).
- `rawCameraBufferCount` is shaped like `h264CameraBufferCount` / `proresCameraBufferCount` (env override via `unsignedEnvValue`, bounds).
- `APERTAR_RT_CAPTURE_PRIORITY` follows R5 and I9; the nice -5 fallback and its comment are kept.
- `sanitizeSettingsForSensor(..., monochromeSensor_)` changed at all five call sites in one commit.
- `syncCpuReadBuffer` delegates to a free helper with identical behaviour.
- Every new accessor has the `#if APERTARCORE_HAS_LIBCAMERA ... #else` neutral stub (I18).
- Log lines keep the `ApertarCore <area>: key=value` form (I6), new warnings are rate limited `n == 1 || n % 30 == 0` (I8, `drop[copy-slot]`).
- Preview TDN: derived tuning copy, never the user's file, same idea as the ProRes ISP derivative (N13).

## Not checked here

Setter gates, the sanitiser body, `Imx585Modes.hpp` content, `DngRecordingQueue` internals beyond the hand-off, App state fields: other units.

## Skeptic

Every finding re-read in code on both sides (port `/home/user/Apertar-Core` @cinemate-port, upstream `/home/user/wt/core-upstream` @upstream-1.6.0, fork main `/home/user/wt/core-main` @main).

| id | verdict | why |
| --- | --- | --- |
| CC-4-F1 | corrected | Confirmed (CC:8731-8739, :5049-5062, :5151-5162@cinemate-port vs CC:7419-7425, :7456-7465@upstream-1.6.0). Rework note on the lock fixed: upstream holds `shared_lock sessionSettingsMutex_` around everything the completion callback does (CC:6589@upstream-1.6.0), so the port lock copies that context; the ProRes closure on the encoder thread takes none. Keep the `running_` guard inside the closure. |
| CC-4-F2 | corrected | Confirmed in code (CC:8295-8296@cinemate-port vs CC:5993-5996@upstream-1.6.0, :6325-6328@main); driver effect stays probable. `isImx585Raw12CropResolution` no longer exists in the port, so the rework must restore it or derive the crop test from `Imx585Modes.hpp`. |
| CC-4-F3 | corrected | Override (CC:7574-7576) and per-request pin (CC:9074-9079) confirmed; upstream video `FrameDurationLimits` is `{d, d}` (CC:2022-2031@upstream-1.6.0, max = d when not photo mode). "Only bypass in the file" and "8 atomics / 6 accessors" not verified: dropped. Rework narrowed: pre-roll at sensor max is the stated feature (d44b177, CC:12040-12050); keep it reachable through the sanitiser input, not by writing after it. |
| CC-4-F4 | corrected | Confirmed. Rework also has to touch `tools/fps_ceiling_test.cpp:22-24` and the comment at CC:3378@cinemate-port. |
| CC-4-F5 | corrected | Lines confirmed. The same grep (`T[0-9][0-9]`, `hardware-log`, `kb working`, `Cinemate's`) hits about 30 lines in the file, not six. "CineMate Log" (CC:8167) is a feature name: name it "Log", as the state key `cdng_log` does. |
| CC-4-F6 | stands | Five fields confirmed at ApertarCoreApp.cpp:9460-9464@cinemate-port; upstream sends only the boolean `recording_has_dropped_frames` (ApertarCoreApp.cpp:7843@upstream-1.6.0). |
| CC-4-F7 | corrected | Ramp and stretch confirmed (CC:9938-9984@cinemate-port). Upstream does start external programs (`aplay` via `execvp`, AudioRecordingSession.cpp:287; `popen`, ApertarCoreApp.cpp:1505@upstream-1.6.0); the mismatch is a shell string plus an undeclared package, not the dependency as such. |
| CC-4-F8 | corrected | Duplication confirmed. "Take binning from `sensorBinning_`" dropped: it is set after the check (CC:8582) from the same properties the check tests, so the table binning is the only independent value. |
| CC-4-F9 | corrected | Three calls confirmed (CC:8381, :8736, :8848). The board-cap point is weak: upstream ProRes default (12, env to 32, CC:1130-1134@upstream-1.6.0) is not board-aware either; only H.264 is. Kept as compute-once plus an unconfirmed Pi 4 CMA check. A larger second count is harmless (requests = min with buffers); a smaller one strands buffers. |
| CC-4-F10 | stands | CC:7813-7814@cinemate-port; AtomicStillFile.hpp:31-32@upstream-1.6.0 quoted correctly. |
| CC-4-F11 | stands | Both knobs confirmed (CC:9109-9133, start-apertar-core.sh:20-39, README.md:353-354@cinemate-port). Upstream README has no `APERTAR_` entry at all. |
| CC-4-F12 | stands | `public:` runs CC:7251-8220@cinemate-port; the two members (CC:8186-8187) sit inside it. Upstream CameraSession has no data member before `private:` (CC:5918@upstream-1.6.0). |

## Final findings

### CC-4-F1 [mismatch, major] DNG copy worker returns requests via set-once `setRequestRelease(libcamera::Request*)` instead of a per-frame release closure
- where: src/camera/CameraController.cpp:8731-8739@cinemate-port ; :5032-5065@cinemate-port ; :5151-5162@cinemate-port ; :9498-9516@cinemate-port
- port way: after `makeRequests` the session installs `recorder_.setRequestRelease([this](libcamera::Request *r){ shared_lock sessionSettingsMutex_; if (!running_) return; requeueRequest(r); }, buffers-2)` and `recorder_.setFrameQueued(...)` (audio observe). `PendingCopy` carries a `libcamera::Request*`; the worker calls back through the stored function.
- Apertar way: a recorder that holds a camera buffer gets a per-frame `std::function<void()>` and never sees a Request: ProRes CC:7419-7425@upstream-1.6.0 `[this, request, cachedFd]{ ... requeueRequest(request); }`; H.264 CC:7456-7465 `releaseRequest = [this, request]{ requeueRequest(request); }`; job field CC:3937 `std::function<void()> release;`. Audio is observed on the completion thread right after the enqueue (CC:7428-7430).
- why it matters: the original developer solved "recorder holds the buffer and gives it back" twice, one way. A third shape (session-wide callbacks typed on `libcamera::Request*`, a second set-once callback for audio, a held-request limit set from outside) reads as another author's framework.
- rework: `DngRecordingQueue::enqueueCopy(PendingCopy, std::function<void()> release)`; `PendingCopy` drops `request`. `recordRawFrame` builds `[this, request]{ if (!running_.load()) return; requeueRequest(request); }`. Pass the hold limit to `startAtFolder`. Delete `setRequestRelease`, `setFrameQueued`, `releaseRequest_`, `frameQueued_`. Audio: a second per-frame closure called when the write queue accepts, or observe at hand-over as ProRes does. The `shared_lock` copies the completion-callback context (CC:6589@upstream-1.6.0 holds it there); keep it only with a one-line reason, the ProRes closure takes none.
- effort: M
- deliberate: yes. 351a3ee: copy moved off the completion thread (6 ms per frame at 30 fps 16-bit Clear HDR). The hand-off shape was not weighed. Desk only.

### CC-4-F2 [removed-upstream-behaviour, major] Colour IMX585 raw12 crop sizes lost the auto sensor-config fallback
- where: src/camera/CameraController.cpp:8295-8296@cinemate-port ; :8485-8530@cinemate-port
- port way: `allowAutoSensorConfigFallback = monochromeSensor_ || Imx294 || Imx577` (IMX585 clause gone, helper `isImx585Raw12CropResolution` deleted). A new block rejects any colour IMX585 candidate whose raw size, bit depth or `ScalerCropMaximum` differs from the `Imx585Modes.hpp` row, for explicit and auto configs alike.
- Apertar way: CC:5993-5996@upstream-1.6.0 (same at CC:6325-6328@main): `|| (sensorFamily_ == SensorFamily::Imx585 && isImx585Raw12CropResolution(sanitized.resolution))`. The 3840-wide crop sizes take the auto config and Core crops in software.
- why it matters: probable: on the Apertar baseline imx585 driver (origin/apertar e5b74d3) the crop sizes no longer configure, so Core works only with the port's driver. To settle: on a Pi with that driver, `set_resolution 3840x1744` 12-bit and read the rejection log.
- rework: restore the clause (restore the helper, or derive "raw12 crop of a native mode" from `Imx585Modes.hpp`). Run the exact-mode rejection only when `useExplicitSensorConfig` is true. Nothing changes with the port driver; the old driver keeps the fallback.
- effort: S
- deliberate: yes. caa0153: "Colour IMX585 configures explicitly only and refuses a mode the driver adjusted". Desk only.

### CC-4-F3 [mismatch, major] Storage pre-roll pushes fps past the sanitiser and re-pins FrameDurationLimits on every request
- where: src/camera/CameraController.cpp:7574-7576@cinemate-port ; :9074-9079@cinemate-port ; :7839-7897@cinemate-port ; :7505@cinemate-port ; :12040-12110@cinemate-port ; :3486-3491@cinemate-port
- port way: `applyControls` sanitises, then `if (prerollFps > 0.0) sanitized.fps = prerollFps;` (comment: "past the lossless-JPEG and ladder caps"). `requeueRequest` sets a second `FrameDurationLimits {p, p}` from `prerollPinUs_` on every request (it also overrides the phase-lock pin). `startStoragePreroll` holds `mutex_` and waits up to 1 s in `waitForFramePeriod`.
- Apertar way: limits come only from the sanitise chain and effective values are read back (CC:2707-2744, :8713-8715@upstream-1.6.0). `controlsForSettings` already pins video to `{d, d}` (CC:2022-2031@upstream-1.6.0: max = d outside photo mode). The only per-request override after the merge is for bracket shots (CC:6515-6530@upstream-1.6.0).
- why it matters: a write after the sanitiser plus a duplicate frame-duration pin. The developer's invariant "settings_ holds what the sanitiser allowed" breaks during a pre-roll.
- rework: carry the pre-roll as an input to the sanitiser (a pre-roll flag on the settings passed to `sanitizeSettingsForSensor`, which then uses `prerollMaximumFps` as the ceiling), applied through the normal `applySettingsLocked`. Suspend the phase lock during a pre-roll so `controlsForSettings` alone sets `{d, d}`. Delete `prerollFpsOverride_`, `prerollPinUs_`, `setPrerollFps`, the override in `applyControls`, the pin in `requeueRequest` and the reset at :7505. Keep the frame/timestamp measurement. If the owner accepts the sanitised ceiling (`maximumFpsForSettings`) as the target, the flag is not needed.
- effort: M
- deliberate: yes. Code comment at CC:12044-12047 states the bypass. d44b177: "Storage pre-roll: a 2 s take at the mode's highest fps".

### CC-4-F4 [slop, minor] Dead back-end fps cap wrapper around `maximumSupportedFpsForResolution`
- where: src/camera/CameraController.cpp:8634-8639@cinemate-port ; :3426-3434@cinemate-port ; :3470@cinemate-port ; :3486-3491@cinemate-port ; :3378@cinemate-port ; src/camera/FpsCeiling.hpp:21-25@cinemate-port ; tools/fps_ceiling_test.cpp:22-24@cinemate-port
- port way: `fpsceiling::applyBackendCap(maximumSupportedFpsForResolution(...), backendMaximumFps(...))`; `backendMaximumFps` voids both arguments and returns `nullopt`, with the comment "Removed (User, 2026-11-03) ... KB working/research-30fps-answer.md".
- Apertar way: a plain call, CC:6589-6592@main `const double maxFps = maximumSupportedFpsForResolution(sensorFamily_, effectiveSettings.resolution, effectiveSettings.rawBitDepth, effectiveSettings.clearHdr);`. No history in comments.
- why it matters: dead indirection and a KB-citing history comment in the configure path the developer reads first.
- rework: restore the plain call at :8634, :3470 and in `prerollMaximumFps`. Delete `backendMaximumFps`, `fpsceiling::applyBackendCap`, its two test lines, and the "16-bit 25 is backendMaximumFps()" comment at :3378.
- effort: S
- deliberate: yes. The cap was removed on purpose; the wrapper was left behind.

### CC-4-F5 [slop, minor] Internal vocabulary and history in comments
- where: src/camera/CameraController.cpp:8902, :8907, :9063-9068, :9112, :9451, :8167@cinemate-port (about 30 such lines file-wide: `grep -n "T[0-9][0-9]\b\|hardware-log\|kb working\|KB working\|Cinemate's\|CineMate's"`)
- port way: comments carry "T31", "Cinemate kept them as live keys", "the qbc libcamera's IMX585 helper", "hardware-log 2026-10-26", "as on Cinemate's libcamera", "(kb working/dng-chain, V/H15)", "CineMate Log".
- Apertar way: comments are 1-3 lines stating a constraint, no tickets, dates or authors (CC:6927-6928@upstream-1.6.0).
- why it matters: the original developer has no T-numbers, KB or hardware log; the references point nowhere.
- rework: keep each constraint, drop the reference. For :9063-9068: "A range, not a single value: a single-value pin makes the IMX585 helper re-choose the line length, which steps the exposure." Name the feature "Log", as the `cdng_log` key does.
- effort: S
- deliberate: no

### CC-4-F6 [new-ground, minor] Frame-rate phase lock: servo fits the Apertar shape; socket telemetry does not
- where: src/camera/CameraController.cpp:8887-8971@cinemate-port ; :9054-9070@cinemate-port ; :8204-8219@cinemate-port ; src/camera/FramePhaseLock.hpp@cinemate-port ; src/ApertarCoreApp.cpp:9460-9464@cinemate-port
- port way: header-only PI servo; `stepFramePhaseLock` per frame on the completion thread pins `{d, d+1}` after every merge; gains from env read once; five fields on the socket (`fps_phase_lock_active/err_us/dur_us/pushes/saturated`). Off by default.
- Apertar way: no precedent (upstream fps is a static pin in `controlsForSettings`). The pieces match: header-only pure logic (StillBracketing.hpp), per-request override after the merge (CC:6515-6530@upstream-1.6.0), read-once env (CdngEncoder.cpp:51-65). Upstream sends only booleans for frame health (`recording_has_dropped_frames`, ApertarCoreApp.cpp:7843@upstream-1.6.0).
- why it matters: the shape is acceptable; four internal fields in `get_state` are not.
- rework: keep. Expose only `fps_phase_lock_active`; err/dur/pushes/saturated stay in the existing log lines. Strip comments per F5.
- effort: S
- deliberate: yes. 80ddac1 (crystal drift vs audio clock), f4a1393 (`{d, d+1}` from an observed HMAX change). Desk only.

### CC-4-F7 [new-ground, minor] Speed ramp: frames numbered by count, fps free during a take, shelled rubberband stretch
- where: src/camera/CameraController.cpp:9451-9479@cinemate-port ; :7589-7593@cinemate-port ; :7801-7807@cinemate-port ; :9938-9984@cinemate-port ; :10692@cinemate-port
- port way: with `fpsSpeedRamp` on, `nextFrameIndex(ts, countOnly=true)`, timecode from the frame count, `applyControls` records ramp events, stop writes `fps-ramp.txt` and forks a detached `nice -n 15 rubberband ...` shell string for a stretched WAV (needs `rubberband-cli`, not declared in README or packaging).
- Apertar way: the DNG index comes from the sensor timestamp so a dropped frame leaves a gap (CC:3518-3526@upstream-1.6.0); `setFps` is refused during a take, "Stop recording before changing FPS so video and audio keep the same timeline." (CC:7745@upstream-1.6.0). External programs are started with an argv via `execvp` (`aplay`, AudioRecordingSession.cpp:287@upstream-1.6.0), not a shell string.
- why it matters: with the flag on, two stated upstream intents change (gaps, fixed fps during a take), and Core gains an undeclared runtime dependency started through a shell.
- rework: keep the ramp behind `fps_speed_ramp` (default off) and state both intent changes in the handoff. Move the stretch out of Core (`launchAudioStretch`, `pendingAudioStretch_`) into an offline script reading `fps-ramp.txt`; if it must stay, start it with `fork`/`execvp` and an argv, and declare the package.
- effort: M
- deliberate: yes. faa2958 tested on the Pi (C0030-C0032); ca7b7c2 labels the stretch experimental.

### CC-4-F8 [duplication, minor] IMX585 and IMX283 exact-mode checks duplicate the depth / PISP_COMP1 logic
- where: src/camera/CameraController.cpp:8485-8530@cinemate-port ; :8531-8560@cinemate-port
- port way: two blocks each call `formatToRawView`, each carry the "Pi 5 turns CSI2P into PISP_COMP1, reports 16 bits" exception, each write their own rejection line.
- Apertar way: one readout check for three sensors with one condition, CC:6162-6183@upstream-1.6.0 (`const bool invalidReadout = sensorFamily_ == SensorFamily::Imx294 ? ... : ...;`).
- why it matters: two copies of one Pi 5 quirk drift apart; the next sensor adds a third.
- rework: one block with a helper `rawModeAdjustment(candidateConfig, rawStreamIndex, rawSize, sensorMode.bitDepth)` returning the reason string (empty = exact), used by both sensors; the IMX585 `ScalerCropMaximum` test (binning from the table row, the only independent value at that point) stays as the one sensor-specific line.
- effort: S
- deliberate: no

### CC-4-F9 [pi-compat, minor] Raw buffer count evaluated three times from live media state
- where: src/camera/CameraController.cpp:8381@cinemate-port ; :8736@cinemate-port ; :8848@cinemate-port ; :1458-1471@cinemate-port
- port way: `rawCameraBufferCount(clearHdr)` reads the media tune and media extra on each call (stream buffer count, request count, hold limit). Default 4, 8 in Clear HDR, +2 on exFAT/NTFS; env or media tune up to 16.
- Apertar way: a fixed `kConfiguredBufferCount = 4` (CC:1023@upstream-1.6.0), read once at CC:6081; H.264 picks its default by board (CC:1124-1128). ProRes is not board-aware either (default 12, env to 32).
- why it matters: probable: a mount or tune change between the calls gives a different count; a smaller later count leaves buffers without requests and changes the hold limit. Unconfirmed: CMA for 8-10 x ~17 MB 4K 16-bit buffers on Pi 4/CM4; settle with Clear HDR 4K on a Pi 4.
- rework: compute the count once in `configureAndStart` into `rawBufferCount_`; `makeRequests` and the hold limit read it. Decide the Pi 4 default after the CMA check.
- effort: S
- deliberate: unknown

### CC-4-F10 [new-ground, minor] syncfs at every take stop reverses "clip frames are not synced"
- where: src/camera/CameraController.cpp:7813-7814@cinemate-port ; :4795-4809@cinemate-port
- port way: after a normal stop `recorder_.syncToMedium()` calls `syncfs` on the clip folder and logs the time. A 1/s sync thread also runs during the take (other unit).
- Apertar way: src/util/AtomicStillFile.hpp:31-32@upstream-1.6.0 "Keep this out of the continuous recording path: syncing each video frame would destroy throughput." Clip frames are not synced.
- why it matters: a stated intent changes. The stop-time sync is defensible (one call, after the frames); the developer must be told.
- rework: keep the stop-time sync; state the intent change in the handoff. Judge the 1/s thread in its own unit.
- effort: S
- deliberate: yes. 4ce382e: C0105 lost after a card pull (30 s dirty expiry). Built, not tested.

### CC-4-F11 [slop, minor] Two real-time scheduling knobs for one experiment
- where: src/camera/CameraController.cpp:9109-9133@cinemate-port ; scripts/start-apertar-core.sh:20-39@cinemate-port ; README.md:353-354@cinemate-port
- port way: `APERTAR_RT_CAPTURE_PRIORITY` (SCHED_FIFO for the capture thread only) and `APERTAR_RT=1` (whole process under `chrt`/`ionice`/`taskset` from the start script), both documented in the README.
- Apertar way: a per-thread `nice -5` on the callback thread (CC:6589-6600@upstream-1.6.0). Upstream README documents no `APERTAR_` variable.
- why it matters: leftovers of an A/B test; the thread-only knob follows the Apertar shape, the whole-process one does not.
- rework: keep `APERTAR_RT_CAPTURE_PRIORITY`; remove `APERTAR_RT` from the start script and README (other unit). Strip the kb reference from the comment (F5).
- effort: S
- deliberate: yes. README calls `APERTAR_RT` "an A/B instrument, not a recommendation".

### CC-4-F12 [mismatch, nit] Session data members declared in the public section
- where: src/camera/CameraController.cpp:8186-8187@cinemate-port
- port way: `mutable std::mutex activeTuningMutex_; std::string activeTuningFile_;` between public accessors (`public:` runs :7251-8220).
- Apertar way: CameraSession data members sit in the private block at the end of the class (from CC:5918@upstream-1.6.0).
- why it matters: breaks encapsulation and reading order.
- rework: move both members to the private member block.
- effort: S
- deliberate: no
