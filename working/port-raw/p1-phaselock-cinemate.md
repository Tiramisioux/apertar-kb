# p1-phaselock-cinemate — Cinemate's frame-rate phase lock, read from source

Reader scope: Cinemate side of the phase lock (cinepi-raw + cinemate + libcamera forks + handbook).
Commits read: cinepi-raw @63a08d5, cinemate @d6cc93e, cinemate-handbook @c99ff77,
libcamera(cinemate) @bfe0b76, libcamera(qbc) @7e9fef0, apertar-core @f60e301 (only for the
"inputs Apertar must supply" section). Every line cited was opened and read. Status tags:
CONFIRMED (source line), PROBABLE (reasoned, says why), UNKNOWN (reason given).

---

## 1. The control law, in words and numbers

All of the law lives in one pure header, `cinepi/phase_lock_core.hpp` (166 lines), called once
per frame by the controller. CONFIRMED.

**Inputs per step** (cinepi-raw/cinepi/phase_lock_core.hpp:66-68@63a08d5): `enabled` (runtime
flag), `roleClient` (this process is the `--sync` client), `isRecording`, `targetFps` (operator's
nominal fps), `refTsNs` (per-frame reference timestamp in ns).

**Parameters** (phase_lock_core.hpp:27-32): `kp = 0.06`, `ki = 0.0015`, `deadbandUs = 6.0`,
`clampUs = 150.0`. Only kp/ki/deadband are runtime-tunable (Redis `pll_kp`, `pll_ki`,
`pll_deadband_us`; cinepi_state.hpp:57-59); clampUs is a compile-time constant.

**State** (phase_lock_core.hpp:34-44): `active`, `integral` (us), `targetFps`, `baseDurUs`
(1e6/target), `reqDurUs` (float requested duration), `t0Ns` (datum), `lastTsNs` (gap detect),
`frameCount` (frames since datum), `lastDurUs` (last integer duration pushed, -1 = none).

**Result** (phase_lock_core.hpp:46-54): `active`, `releasedLock`, `rearmed`, `servoRan`,
`setControls`, `durUs`, `phaseErrUs`.

**Step order** (one frame):

1. Release if `!enabled || roleClient` (:75-80) or `target <= 1.0` (:83-88): `active=false`,
   `lastTsNs=0`, return `releasedLock`. No control is pushed.
2. `dt = refTsNs - lastTsNs` only when already active and lastTsNs != 0, else 0; then
   `lastTsNs = refTsNs`; `periodNs = 1e9/target` (:90-92).
3. `bigGap = active && dt > 1.5*periodNs`; `forceRearm = bigGap && !isRecording` (:96-97).
4. **Re-arm** when not active, or `|target - state.targetFps| > 1e-6` (fps changed), or
   `forceRearm` (:99-111): set target, `baseDurUs = reqDurUs = 1e6/target`, `integral=0`,
   `t0Ns = refTsNs`, `frameCount=0`, `lastDurUs=-1`, `active=true`; return `rearmed` with **no
   servo and no control push**.
5. **Recording-mode gap absorption** (:113-118): if `bigGap` (and we got here, so recording):
   `missed = floor((dt + 0.5*periodNs)/periodNs)` (round-to-nearest frame count);
   if `missed > 1` then `frameCount += missed-1`. Comment: "drop burst (absorb the missed frames
   so phase doesn't spike)".
6. `frameCount++`; `idealNs = frameCount * 1e9/targetFps`; `elapsedNs = refTsNs - t0Ns`;
   `phaseErrUs = (elapsedNs - idealNs) * 1e-3` (:120-125). Sign: `phaseErr > 0` means the
   sensor is slow/behind → shorten the duration; `< 0` fast/ahead → lengthen.
7. **Preview-only safety re-arm** (:130-139): if `!isRecording && |phaseErrUs| > 0.5e6/targetFps`
   (half a frame in us), reset `reqDurUs=baseDurUs`, `integral=0`, `t0Ns=refTsNs`,
   `frameCount=0`, `lastDurUs=-1`, return `rearmed` (no servo). While recording a large error is
   "genuine drift; track it".
8. **PI servo, held inside the deadband** (:144-150): only if `|phaseErrUs| > deadbandUs`:
   `integral += phaseErrUs`; anti-windup `iClamp = clampUs / max(ki, 1e-9)` and
   `integral = clamp(integral, -iClamp, +iClamp)`;
   `reqDurUs = baseDurUs - (kp*phaseErrUs + ki*integral)`;
   `reqDurUs = clamp(reqDurUs, baseDurUs - clampUs, baseDurUs + clampUs)`.
   Inside the deadband nothing changes (no integral walk, no new request).
9. **Integer-us rounding + push-on-change** (:152-163): `durUs = lround(reqDurUs)`; `servoRan=true`;
   `setControls = (durUs != lastDurUs)` and then `lastDurUs = durUs`. Comment: this rounding "is
   where the integer-VBLANK quantisation becomes the sigma-delta dither, and it caps control
   traffic to actual line flips".

**What is pushed and when** (cinepi-raw/cinepi/cinepi_controller.cpp:1243-1250@63a08d5): only
when `res.setControls`, a `FrameDurationLimits` span `{durUs, durUs}` (min == max) goes through
`app_->SetControls(cl)`. Telemetry (`pll_phase_err_us` rounded, `pll_req_dur_us`) is written
only when `res.servoRan` (:1252-1263).

**Target source** (cinepi_controller.cpp:1232-1236): `fps_user` string fetched every frame inside
process()'s single pipelined Redis round trip (:688-700) and parsed; if absent, the previous
target is reused. Hence an operator fps change re-arms the lock the next frame (step 4).

**Role suppression** (cinepi_controller.cpp:1237-1240): `roleClient = (options_->sync == 2)`;
passed to the core, which releases on the client so libcamera `rpi.sync` owns that sensor's
VBLANK (phase_lock_core.hpp:72-74; header comment cinepi_controller.hpp:108-115). Runs on a lone
sensor (`--sync` off) and on the dual master (`--sync server`).

**Recording flag**: `is_recording_` is the controller's own state, set by the `rec` Redis handler
on the subscriber thread (cinepi_controller.cpp:779-791).

Derived numbers (arithmetic from the constants above, PROBABLE as interpretation): clamp ±150 us
per frame = ±3750 ppm pull range at 25 fps (150/40000), ±3600 ppm at 24 fps; maximum phase
slew at the clamp = 3.75 ms per second at 25 fps — consistent with the commit messages' "186 ms
took ~54 s to bleed" (e74e3e4) and "169 ms ... ~47 s" (4537153).

## 2. The reference clock

**Where the reference comes from** — `CinePIController::process()`:

- `info.ts` is the SensorTimestamp, ns since boot (cinepi_controller.cpp:584 comment).
- Preferred: `completed_request->metadata.get(controls::FrameWallClock)`; the code comment says
  "FrameWallClock is µs since epoch" and does `epoch_ns = *wc * 1000` (:590-594). CONFIRMED.
- Fallback when FrameWallClock is absent (:597-626): sample `CLOCK_BOOTTIME` and `CLOCK_REALTIME`
  back-to-back **once** (function-static), cache `boot_to_epoch_ns = real - boot`, then
  `epoch_ns = info.ts + boot_to_epoch_ns`. The comment explains why it is not anchored to a
  frame's arrival: that folds process latency into the offset and made cam0/cam1 timecodes differ
  by "one frame ahead/behind" on synced sensors (commit 94102f7, 2026-07-06).
- `updatePhaseLock(epoch_ns, fps_user)` is the last step of process() (:733-737), comment:
  "References the Pi wall clock (FrameWallClock = the audio clock, computed above)".
- The same `epoch_ns/1000` feeds the DNG timecode (`setWallClockTimestamp`, :658; dng_encoder.cpp:165-168).

**Why FrameWallClock was chosen** — commit 5b4b209 (2026-06-15) "role-gate phase lock + reference
Pi wall clock (dual-sensor unify)": "Reference the Pi wall clock (FrameWallClock, de-jittered,
= the audio clock) instead of the raw monotonic SensorTimestamp. Sensor-agnostic and matches the
clock rpi.sync uses, so master-discipline and client-tracking share one domain. epoch_ns is
already computed in process(); pass it to updatePhaseLock." The original bf717fa (2026-06-11)
measured "against the monotonic SensorTimestamp". CONFIRMED (commit messages).

**What libcamera's wallClockRecovery does** (libcamera(cinemate) @bfe0b76, CONFIRMED):

- `ClockRecovery` defaults: `numSamples=100, maxJitter=2000, minSamples=10, errorThreshold=50000`
  (include/libcamera/internal/clock_recovery.h:18-19). Units are whatever the caller feeds; in
  this fork `addSample()` samples CLOCK_BOOTTIME twice around CLOCK_REALTIME, averages the two
  boot readings, and converts to **microseconds** (src/libcamera/clock_recovery.cpp:117-127).
- `addSample(input, output)` (clock_recovery.cpp:139-215): tracks a leaky cumulative error
  `error = 0.95*error + (outputDiff - inputDiff)`, resets the model if `|error| > errorThreshold`
  (wall clock stepped); clamps each new output to `expected ± maxJitter`; updates running
  averages of x, y, x², xy with the count capped at `numSamples` (so old samples fade); fits
  slope/offset by least squares only after `count > minSamples`.
- `getOutput(input)` = `slope*x + offset + x + outputBase` (clock_recovery.cpp:219-228); i.e. a
  de-jittered, slowly re-fitted linear map boot→wall.
- Per frame, the PiSP pipeline calls `wallClockRecovery_.addSample()` then
  `getOutput(sensorTimestamp / 1000)` and sets `controls::FrameWallClock`
  (src/libcamera/pipeline/rpi/pisp/pisp.cpp:1752-1757); an initial sample is taken at start
  (pipeline/rpi/common/pipeline_base.cpp:689-690).

**Unit divergence between the two forks — a port pitfall** (CONFIRMED):
libcamera(qbc) @7e9fef0 passes `getOutput(sensorTimestamp)` in **nanoseconds**
(pisp.cpp:1991-1996), samples in ns (clock_recovery.cpp:121-124), and its control definition says
"Like SensorTimestamp, the timestamp value is expressed in nanoseconds"
(src/libcamera/control_ids_core.yaml:1275-1276). The cinemate fork's yaml (:1269-1281) states no
unit and the pipeline emits µs. cinepi-raw's `* 1000` (cinepi_controller.cpp:594) is correct for
the cinemate fork only. Whether the Pi binary Apertar links matches qbc is PROBABLE per the task
brief; a port must verify FrameWallClock units at runtime rather than assume.

Note on what the tests prove about the reference: `test_reference_magnitude_invariance`
(tests/phase_lock_core_test.cpp:146-168) proves the law is invariant to a constant offset of
epoch magnitude (only int64 differences are used). It does **not** compare BOOTTIME-rate vs
wall-fitted-rate references; whether FrameWallClock's fitted slope ever differs measurably from
raw BOOTTIME on a Pi is UNKNOWN from source (no measurement found in repos or handbook).

## 3. What the tests prove, and the measured numbers

File: cinepi-raw/tests/phase_lock_core_test.cpp@63a08d5 (313 lines; "4624 checks" per commit
28b30cc). Harness: `CHECK` macro, `approx(a,b,tol)`.

**Sensor/VBLANK quantiser model** (:46-56): `lines = lround(reqDurUs / lineUs)`;
`periodUs = lines*lineUs*(1 + biasPpm*1e-6)`; realised period in ns. `runLoop` (:67-90) feeds
`phaseLockStep` with the realised period, records `durUs`, `phaseErrUs`, `periodNs`, and counts
`setControls`.

| Test (line) | Setup | Asserts |
|---|---|---|
| `test_role_gate_client_suppresses` (:94-110) | roleClient=true, 500 frames, isRecording alternating | every step `releasedLock`; never `setControls`; never `active` |
| `test_disabled_suppresses` (:112-121) | enabled=false, 100 frames | released, no output, inactive |
| `test_invalid_target_releases` (:123-130) | target 1.0 and 0.0 | released, inactive |
| `test_first_frame_arms_no_output` (:132-140) | first enabled frame at 24 fps | `rearmed && active && !servoRan && !setControls`; baseDur = 1e6/24; frameCount 0 |
| `test_reference_magnitude_invariance` (:146-168) | line 11 us, bias +350 ppm, 25 fps, 4000 frames, base 0 vs 1778972127858905000 ns | identical `durUs` trace and `phaseErrUs` within 1e-6 |
| `test_convergence_and_dither_average_exact` (:172-198) | 24 fps, line 11 us (41666.67 not a multiple of 11), bias +473 ppm, 6000 frames | (a) max abs phase error after frame 1000 **< 300 us**; (b) mean realised period over frames 2000+ **within 1.0 us of 41666.67 us** (commit 28b30cc reports the actual residual as "within 0.002us"); (c) at least two distinct `durUs` requested (dither present) |
| `test_deadband_holds` (:202-222) | line 10 us (exactly representable), bias 0, 25 fps, 3000 frames | **zero** `setControls` after frame 1500 |
| `test_recording_gap_absorbed_not_rearmed` (:226-241) | 50 recording frames, then a 4-period gap (3 dropped) | `!rearmed`, `servoRan`, `frameCount >= before+3`, abs phase error **< 200 us** |
| `test_preview_gap_rearms` (:244-254) | 50 preview frames then a 5-period gap | `rearmed && !servoRan`, `frameCount == 0` |
| `test_fps_change_rearms` (:256-265) | 25 → 24 fps | `rearmed`; target 24; baseDur = 1e6/24 |
| `test_recording_large_drift_tracked_and_clamped` (:269-294) | recording, sensor 1000 ppm slow, 4000 frames | every `durUs` within `[lround(base-150)-1, lround(base+150)+1]`; never re-armed |

**Convergence time**: not asserted explicitly. The convergence test ignores the first 1000
frames (~42 s at 24 fps) for the error bound and the first 2000 (~83 s) for the average, so
"converged within 1000 frames" is the implicit bound (PROBABLE as interpretation of :182,:189).

**Residual ppm**: the assertion bound is 1 us/41666.67 us ≈ 24 ppm; the reported actual
0.002 us ≈ 0.05 ppm (28b30cc). On hardware: "+1066 ppm uncorrected -> -9 ppm locked (120x)"
on imx585 mode0 @25 fps (commit 55562b6; same figures in cinepi_controller.hpp:354-355).
With the earlier pure-integral law the average still locked to "-15 ppm (from +1066)" but
"railing the clamp (+/-150us) and swinging VBLANK +/-15 lines" (commit 85d0326).

**Dither amplitude**: "~2-3 line dither (+/-12us duration, ~0.03% exposure variation), 0 drops,
phase error centered at 0" (55562b6). The ~125 ppm figure: "beating the ~half-line (~125 ppm)
floor of a single fixed correction factor" (bf717fa; cinepi_controller.cpp:1211-1212).

**Behaviour on drops/reconfigure** (commit messages, CONFIRMED): e74e3e4 — imx585 mode1/24 fps
measured **-1394 ppm**; a ~186 ms reconfigure stall leaked as a phantom error that the
clamp-limited loop took ~54 s to bleed. 3b3ff60 — recording still started -90 ms off because a
stall is not an integer number of frames; policy split: preview >1.5-frame gap → re-arm,
recording → absorb. 4537153 — still -169 ms from sub-1.5-frame gap bursts (~47 s to bleed);
added the preview-only half-frame safety re-arm.

**Former static correction factors** (what the lock replaced; cinemate commit 2f79397^
`src/module/sensor_correction_factors.py`): imx585 mode0 24 fps 0.9994 (−600 ppm), mode1 24 fps
0.9980 (−2000 ppm), 25 fps 1.0 "exact after will127534/libcamera getBlanking patch"; imx283
mode1 25 fps 0.9990 (−1000 ppm). Removed 2026-06-16 as "superseded by phase lock" ("Pi-verified
dead-on, 0 drops, on imx283 + imx585").

**Handbook**: `lessons/hardware-log.md` has no phase-lock, sigma-delta or audio-sync entry (grep
empty); its dated entries run 2026-09-21 (:41) to 2026-10-07 (:3900), i.e. after the June work.
`open-threads.md` has no relevant hit. Documented facts elsewhere: architecture/redis-contract.md:38-46
(four keys, one shared `fps_phase_lock`, dates 2026-06-11), :59-60 and
lessons/what-the-pi-taught-us.md:38-39 (two per-frame telemetry keys with zero consumer — they are
live on hardware), architecture/cinemate.md:193-199, working/testing.md:34 (the core is
unit-tested). No before/after drift measurement exists in the handbook: UNKNOWN beyond the commit
figures above.

## 4. Audio: timestamps, alignment, and "FrameWallClock = the audio clock"

**Capture helper** (cinepi-raw/cinepi/cinepi_audio_capture.cpp@63a08d5): ALSA `snd_pcm_readi`
loop, period 10 ms, 1 s ring buffer on the record path (:465-468), real-time priority (:531-534).
At trigger it prints `<TS_START:...>` and `<TS_FIRST_BUFFER_B:...>` from **CLOCK_MONOTONIC** and
`<TS_AUDIO_START_REALTIME:...>` from **CLOCK_REALTIME** (:536-542; tags are `sec.nsec`, :112-116);
`<TS_FIRST_BUFFER_A:...>` after the first successful read (:637-640). Samples themselves carry no
timestamps. A running wall-clock anchor (`steady_clock`) reconciles frames written vs elapsed time
on every read; a shortfall > `periodFrames/4` (~5.3 ms at 48 kHz) is padded with silence (capped
at 5 s) so "the WAV stays locked to wall-clock length" (:599-669).

**Alignment to video** (cinepi/cinepi_sound.cpp@63a08d5): the parent parses the tags
(:1215-1227, `extractTime` → ns :639-648). After the take: `vts_start/vts_end` are the encoder's
logged video timestamps (:1334-1338), which are **SensorTimestamp (CLOCK_BOOTTIME ns)** —
cinepi_recorder.hpp:86-87 reads `controls::SensorTimestamp` and :100 calls `log_ts`.
`audio_marker_ns = min(TS_FIRST_BUFFER_B, TS_FIRST_BUFFER_A)` else `TS_START`
(`chooseAudioStartTimestamp`, :112-126, used :1358-1361). `start_delta_seconds = audio_start -
video_start` (:1369-1376; a fixed `AUDIO_CAPTURE_LATENCY_MS` bias is subtracted only when the
REALTIME marker is missing). The WAV **metadata** timecode is derived from
`TS_AUDIO_START_REALTIME` via `buildMetadataFromWallclockNs` ("audio-start" source, :1405-1420);
`start_delta` is also expressed as frames/samples for the log (:1510-1518). ffmpeg then writes
BEXT `time_reference`/`timecode` with **`-c:a copy`** — the PCM is never resampled or shifted
(:1526-1538). So: the WAV start is matched to the first frame through metadata (time_reference +
timecode), not by moving samples.

Clock-domain note (PROBABLE): the audio marker is CLOCK_MONOTONIC and the video timestamps are
CLOCK_BOOTTIME; they are compared without conversion (:1369-1376). They coincide unless the Pi
has suspended, which is why this works in practice; a port should use one clock for both.

**No resampling**: commit 7398b62 (2026-06-03) removed the "ADC clock correction (ppm)
subsystem" after clap-delta tests showed the RØDE NTG ADC "is ~0 ppm"; earlier 1130/1797 ppm
estimates "were fitting bracketing noise", and "Applying +1797 ppm was itself the source of the
late drift"; residual 4K errors were storage-contention sample loss, fixed by the writer thread
and reconciliation. "The ffmpeg metadata pass stays; it now always uses -c:a copy." CONFIRMED.

**Did the audio path change when the phase lock arrived?** No. `git log` on cinepi_sound.cpp,
cinepi_sound.hpp and cinepi_audio_capture.cpp between 2026-06-10 and 2026-07-10 is empty; the
audio rework (SCHED_FIFO, writer thread, wall-clock reconciliation, tolerance tuning to
periodFrames/4) landed 2026-06-02..06-06, the phase lock 2026-06-11..06-15. CONFIRMED.

**"FrameWallClock = the audio clock"** (cinepi_controller.cpp:734, :1206; hpp:108-110; commit
5b4b209): the meaning is that both the video reference (FrameWallClock, a fit of BOOTTIME onto
CLOCK_REALTIME) and the WAV's metadata start (CLOCK_REALTIME `TS_AUDIO_START_REALTIME`) are in
the Pi's real-time clock domain, and the WAV length is reconciled to elapsed real time. The audio
samples are not clocked by FrameWallClock — the ADC runs on the USB device's crystal; the
statement is about the timebase of start/duration, not sample clocking. PROBABLE (interpretation
of the cited code and comments; nothing in source stamps samples with FrameWallClock).

## 5. Interaction with libcamera (AGC, exposure, VBLANK vs HMAX)

**How controls reach libcamera in cinepi-raw** (core/rpicam_app.cpp@63a08d5): `SetControls`
merges into a pending `controls_` list under `control_mutex_` — "applied to the next StartCamera
or request" (:1097-1106). In `queueRequest` (:975-1032) the list is **moved** onto the request
being re-queued (`request->controls() = std::move(controls_)`, :1022-1024) and then
`camera_->queueRequest`. So each pushed `FrameDurationLimits` rides exactly one request (the next
one re-queued after the completed request is released) and the list empties; it is a per-request,
one-shot control, not a persistent setting. CONFIRMED.

**IPA side** (libcamera(cinemate) src/ipa/rpi/common/ipa_base.cpp@bfe0b76): per request,
`FRAME_DURATION_LIMITS` calls `applyFrameDurations(min, max)` (:1186-1190). That clamps to the
mode's limits, republishes the validated limits in metadata, computes the max exposure the AGC may
use via `helper_->getBlanking(maxExposureTime, min, max)` and calls `agc->setMaxExposureTime`
(:1638-1667; comment "This will only be applied once AGC recalculations occur"). In `applyAGC`
(:1691-1702) `getBlanking` "might clip exposure time to the fps limits", then writes
`V4L2_CID_VBLANK` and `V4L2_CID_EXPOSURE`.

**VBLANK-only quantisation** (src/ipa/rpi/cam_helper/cam_helper.cpp:82-126): `frameLengthMin/Max
= duration / minLineLength` (integer lines); `vblank = frameLengthLines - height`; the **line
length (HMAX) is stretched only if `frameLengthLines > mode.maxFrameLength`**. For a ±150 us
request around nominal that branch is never reached, so the lock changes VBLANK only — matching
the controller comment "VBLANK-only: never touches HMAX, so the 4K line-length failure mode cannot
recur" (cinepi_controller.cpp:1213-1214; bf717fa: "the 4K static failure mode of the getBlanking
HMAX-stretch patch"). No imx585-specific `getBlanking` override exists at bfe0b76 (grep found only
imx477/imx519/imx708/imx500 helpers), so the "will127534 getBlanking patch" the old
docs/fps-correction.md credited for exact 25 fps is not in the current fork — PROBABLE that it
was reverted (the bf717fa message calls its failure mode "static", and the handbook's 2026-08-26
HMAX entries, hardware-log.md:598-660, discuss a separate driver HMAX bug and retract a patch).

**Does pinning {d,d} fight the AGC?** In cinepi-raw the question is moot: this fork sets
`ExposureTimeMode` and `AnalogueGainMode` to Manual by default (core/rpicam_app.cpp:825-828),
so exposure is operator-set, and `getBlanking` merely clips it if it exceeds the (dithered) frame
length. With a 1 us duration change the exposure request is unchanged; the sensor frame length
moves by one VBLANK line (~11 us at the tested mode; the test model uses 11 us), hence the
measured "~0.03% exposure variation" (55562b6) — which is the frame-length/duty change, not an
exposure-register change. For an auto-exposure port, the AGC's max exposure follows each
`applyFrameDurations` call (ipa_base.cpp:1663-1667), so AGC and lock do not fight: the lock sets
the frame length, AGC works inside it. CONFIRMED for cinepi-raw's manual case; PROBABLE for the
AGC-on case (reasoned from ipa_base.cpp, not measured).

**Control latency**: libcamera applies sensor controls through `DelayedControls` (pisp.cpp:1746);
cinepi-raw's gains were tuned with its own in-flight depth. The effective loop delay in frames is
UNKNOWN from source; Apertar's 3-requests-in-flight depth may need re-tuning of kp/ki.

## 6. Defaults and knobs

- **cinepi-raw ships off**: `phaseLockEnabled_{false}` (cinepi_controller.hpp:353);
  `cinepi_state.hpp:55` "Off by default."; startup seeds `fps_phase_lock = "0"` when the key is
  absent (cinepi_controller.cpp:407). README row :176: "Off unless set; CineMate enables it per
  camera (phase_lock, default on)".
- **Cinemate turns it on**: `sensors.cam0/cam1.phase_lock` defaults to `true`
  (config_loader.py:556; settings.jsonc:98-100 and :116; docs/settings-json.md:78 "Default on.
  Leave it on, genlocked rigs included"). `CinePIController.__init__` reads the first configured
  camera (cam0 then cam1) and writes **one shared** `fps_phase_lock` key via `set_value`
  (cinepi_controller.py:120-144), which also publishes on cp_controls (redis_controller.py:329-331
  docstring "Write key, publish"). The per-camera shape does not buy per-sensor control
  (handbook architecture/cinemate.md:196-199).
- **Startup precedence** (cinepi_controller.cpp:400-408): explicit `--phase-lock` wins and is
  written back to Redis; else the Redis value; else seed 0.
- **Live update**: contrary to docs/redis-keys.md:23 ("read once at CinePi-raw startup, not
  live"), cinepi-raw subscribes to cp_controls (:1188) and has a live handler for `fps_phase_lock`
  (:982-986) plus `pll_kp`/`pll_ki`/`pll_deadband_us` (:988-996); dispatch GETs the key named in
  the message and calls the handler (:1158-1166). The doc row is stale. CONFIRMED.
- **CLI** `--phase-lock [0|1]`: `std::optional<bool>` (raw_options.hpp:66-68); parser accepts
  `1/on/true`, `0/off/false`, bare flag = 1, and also consumes a following bare `0`/`1` token
  (cinepi_options.cpp:572-585; help text :227-230).
- **Gain keys**: `pll_kp`, `pll_ki`, `pll_deadband_us` read at startup or seeded with the defaults
  (cinepi_controller.cpp:410-424). No key for clampUs.
- **Telemetry keys**: `pll_phase_err_us` (rounded) and `pll_req_dur_us`, SET each servo frame in
  one pipelined round trip (cinepi_controller.cpp:1252-1263). No Cinemate reader (grep empty;
  handbook redis-contract.md:59-60).
- **Nominal fps**: `fps_user`, written by Cinemate `set_fps` (cinepi_controller.py:1762-1763);
  since 2f79397 "the hardware fps == the user fps" (:1765-1767). Cinemate's `fps` handler in
  cinepi-raw pushes `{1e6/fps, 1e6/fps}` truncated to integer us (cinepi_controller.cpp:968-980);
  the lock's `baseDurUs` keeps the fractional value and dithers around it.
- **Changelog**: cinemate docs/changelog.md:97 Version 3.3.2 → :114 "Frame-rate phase lock ...
  pre-converges during preview. On by default."; :115-116 audio capture rework and wall-clock
  embedded timecode shipped in the same release.

## 7. What a port needs

**Minimal state machine** (one struct, one pure function, no I/O — mirror phase_lock_core.hpp):
state {active, integral, targetFps, baseDurUs, reqDurUs, t0Ns, lastTsNs, frameCount, lastDurUs};
per frame: release → gap detect → re-arm (first frame / fps change / preview big gap) → absorb
(recording big gap) → phase error → preview half-frame reset → PI outside deadband with
anti-windup and ±clamp → lround → push only on integer change.

**Numbers**: kp 0.06, ki 0.0015 (per-us error, integral in us), deadband 6 us, clamp ±150 us,
gap threshold 1.5 frames, absorb count round((dt + 0.5 P)/P) − 1, preview safety reset at
|err| > 0.5 frame, fps-change tolerance 1e-6, release when target ≤ 1 fps. Expected behaviour:
bounded |err| < 300 us after ~1000 frames, 2–3 line dither, average exact to sub-ppm; on imx585
mode0 25 fps +1066 → −9 ppm.

**Inputs Apertar must supply**:
1. A per-frame reference timestamp in int64 ns with a stable rate. Options in Apertar today:
   `controls::SensorTimestamp` (CLOCK_BOOTTIME ns; already read at
   apertar-core/src/camera/CameraController.cpp:7239@f60e301) or
   `RecordingClock::wallTime()` (a once-sampled BOOTTIME→REALTIME offset,
   apertar-core/src/audio/RecordingClock.hpp:34-48 — the same scheme as cinepi-raw's fallback).
   Both are offset-equivalent for the law (tests prove offset invariance). If FrameWallClock is
   used, check its unit on the installed libcamera (ns in the qbc fork, µs in the cinemate fork).
2. The operator's nominal fps as a double (`settings.fps`; note Apertar currently truncates
   `1000000.0/fps` to an integer when it builds FrameDurationLimits, :2075-2077 — the lock must keep
   the fractional base).
3. A recording flag (gap policy and safety re-arm differ between preview and recording).
4. An enable flag; Apertar has no `--sync` client role, so `roleClient` is constant false unless a
   genlock feature is added.

**Output path**: on `setControls`, queue `FrameDurationLimits {d, d}` onto the next request.
Apertar's `requeueRequest` already merges a one-shot `pendingControls_` list into
`request->controls()` under `controlsMutex_` (CameraController.cpp:6864-6876) — the exact
analogue of rpicam_app's `queueRequest` move (core/rpicam_app.cpp:1022-1024). Caveat: Apertar's
settings path sets `{frameDurationUs, maximumFrameDurationUs}` with max > min in photo mode
(:2079-2083); while the lock is active it must own both ends (min == max) or the IPA/AGC can
lengthen frames inside the range and the cadence is not pinned.

**Audio**: Apertar already stamps the first audio sample and first video frame in BOOTTIME µs and
writes the WAV header from `wallTime(videoFirstUs)` (AudioRecordingSession.cpp:348-349, :427-428,
:577-578), so no audio change is needed to adopt the lock — same as Cinemate, where the audio path
did not change when the lock arrived. Do not resample audio to chase video (7398b62 lesson).

**Telemetry**: expose phase error (us) and requested duration (us) per servo frame; Cinemate
writes them to Redis with no consumer — a port can surface them in the status/web page instead.

**Pitfalls the tests encode**:
- First enabled frame arms only: no servo, no control push (:132-140).
- Disabled/invalid target must clear `lastTsNs` so re-enabling does not see a giant gap (:75-88).
- Never push unless the integer-us duration changed; a locked loop in the deadband must produce
  zero pushes (:202-222).
- Preview gap > 1.5 frames → re-arm; recording gap → absorb into frameCount, phase error stays
  < 200 us (:226-254). A reconfigure stall is not an integer number of frames: absorbing it leaves
  a residual, which is why preview re-arms instead (3b3ff60).
- Preview |err| > half frame → reset datum; recording never resets (:269-294) — large recording
  error is real drift and must stay clamped at ±150 us and keep tracking.
- fps change re-arms immediately (:256-265).
- Use int64 differences before converting to double; epoch-magnitude timestamps must give the
  identical trace to boot-relative ones (:146-168).
- Pure integral control oscillates and rails the clamp (85d0326): keep the proportional term
  dominant.
- Run the lock in preview too so recording starts already locked (d038556); the operating point
  carries across the preview→record transition.
- Gains were tuned on imx585 mode0 @25 fps with cinepi-raw's control latency; with Apertar's 3
  requests in flight and libcamera's DelayedControls, expect to re-verify kp/ki on hardware
  (UNKNOWN from source).

## Unanswered / UNKNOWN

- Measured drift before/after in the handbook: none exists (hardware-log.md covers 2026-09-21 →
  2026-10-07 only; no phase-lock entry). Only commit-message figures are available.
- Whether FrameWallClock's fitted slope differs measurably from raw CLOCK_BOOTTIME on a Pi (no
  measurement in any repo).
- The effective control latency (frames between a FrameDurationLimits push and the realised
  frame length) in cinepi-raw, and therefore whether the 0.06/0.0015 gains transfer unchanged to
  Apertar's request depth.
- Which libcamera version the Pi binary used by Apertar matches (qbc assumed PROBABLE); this
  decides FrameWallClock's unit.
- Whether the imx585 `getBlanking` override ever existed in this libcamera fork's history (the
  shallow clone's `-S getBlanking` shows only upstream commits); its absence at HEAD is confirmed.

---

## Verification

Adversarial pass over every finding above. Method: each cited file was opened at the cited line
on the checkout at the stated commit (`sed -n` / `grep -n`; apertar-core via
`git show f60e301:<path>` because that working tree is now at 2a6f114). Verdicts:
CONFIRMED (line exact, content supports the claim, label honest), CORRECTED (claim stands but a
citation, number or wording is fixed), REFUTED (source contradicts), UNVERIFIABLE. Numbers were
recomputed. Nothing in any repository was modified except one allowed
`git -C libcamera-qbc fetch --depth=1000 origin qbc-pisp-handler` (depth 123 → 1995) used to
date the FrameWallClock unit change.

### Per-finding verdicts

| # | Finding (short) | Verdict | Notes |
|---|---|---|---|
| 1 | Pure header law; kp 0.06 / ki 0.0015 / deadband 6 us / clamp 150 us; only three Redis-tunable | **CONFIRMED** | phase_lock_core.hpp:27-32, :66-68@63a08d5 exact. cinepi_state.hpp:56-59 holds the four keys, :55 "Off by default." No key exists for clampUs (grep CONTROL_KEY_PLL finds three). |
| 2 | Step order, re-arm rules, absorb, half-frame reset, PI, lround, push-on-change | **CORRECTED (wording)** | All ranges exact (:75-80, :83-88, :90-92, :96-97, :99-111, :113-118, :120-125, :130-139, :144-150, :152-163). The JSON wording "missed = round((dt+0.5P)/P)" is imprecise: :114-115 is `static_cast<uint64_t>((dt + 0.5P)/P)`, i.e. truncation, which equals round-to-nearest of dt/P (the markdown §1 step 5 has it right). Numbers recomputed: 150/40000 = 3750 ppm at 25 fps, 150/41666.67 = 3600 ppm at 24 fps. |
| 3 | Push {durUs,durUs} on setControls; telemetry on servoRan; fps_user per frame; roleClient; is_recording_ | **CORRECTED (citation)** | :1237 roleClient, :1245-1249 dv/SetControls, :1257-1258 the two SETs (lround on phase error) exact; :697-698 `pipe.get("fps_user").get("is_recording")` exact. The rec handler is cinepi_controller.cpp:**781-792** (`is_recording_ = level` at :792), not :779-791. |
| 4 | FrameWallClock preferred (us → ×1000), static BOOTTIME→REALTIME fallback, same epoch_ns to DNG and lock | **CORRECTED (off-by-one)** | `info.ts = ns since boot` comment is :**583** (not :584); `/* FrameWallClock is µs since epoch */` :592 and `* 1'000ULL` :**593** (the "surprises" cite :594). Fallback block :595-626, `REALTIME − BOOTTIME` :612, setWallClockTimestamp :658, comment :734, call :737 — exact. |
| 5 | Why FrameWallClock (5b4b209), bf717fa monotonic, 94102f7 pure offset | **CONFIRMED** | All three commit bodies read; quotes verbatim ("de-jittered, = the audio clock", "matches the clock rpi.sync uses", "one frame ahead/behind"). Dates 2026-06-15, 2026-06-11, 2026-07-06 exact. |
| 6 | ClockRecovery defaults 100/2000/10/50000; 0.95 leaky error; maxJitter clamp; LSQ with count cap; getOutput; PiSP per-frame addSample+getOutput; initial sample | **CONFIRMED** | clock_recovery.h:18-19; clock_recovery.cpp :109 addSample(), :139 addSample(in,out), :219-228 getOutput; pisp.cpp:1752-1757; pipeline_base.cpp:689-690 — all exact @bfe0b76. Nuance: `count_` stops incrementing when `count1 < numSamples_` fails, so it saturates at numSamples−1; the fit updates once `count_ > minSamples_`. |
| 7 | FrameWallClock unit divergence: cinemate fork us, qbc fork ns | **CONFIRMED + settled further** | pisp.cpp:1754 `getOutput(sensorTimestamp / 1000)` and clock_recovery.cpp:121-124 (`/ 1000`) @bfe0b76; qbc pisp.cpp:1993 `getOutput(sensorTimestamp)`, clock_recovery.cpp:121-124 (`1000000000ULL`), control_ids_core.yaml:1275-1276 "expressed in nanoseconds" @7e9fef0 — all exact. See *Added* A1 for the upstream commits that date the change and the fork each camera actually runs. |
| 8 | Eleven tests, sensor model, each assertion, 4624 checks | **CONFIRMED** | tests/phase_lock_core_test.cpp:46-56 model (`lround(dur/lineUs)`, ×(1+ppm)); :94-110, :112-121, :123-130, :132-140, :146-168 (`1778972127858905000LL`), :172-198 (`maxAbsAfter < 300.0`, `approx(avgUs, idealUs, 1.0)`, `hi > lo`), :202-222 (`i > 1500`, `tailPushes == 0`), :226-241 (4-period gap, `>= fcBefore + 3`, `< 200.0`), :244-254 (5-period gap), :256-265, :269-294 (1000e-6 slow, clamp band ±1, never re-armed) — all exact. 28b30cc body says "4624 checks" and "within 0.002us of ideal". |
| 9 | Convergence time only implicit (warm-up 1000 / 2000 frames) | **CONFIRMED (as PROBABLE)** | :182 `for (size_t i = 1000;`, :189 `for (size_t i = 2000;` exact. 1000/24 = 41.7 s, 2000/24 = 83.3 s. Label honest. |
| 10 | Hardware numbers from commits; ~125 ppm floor; former factors | **CONFIRMED** | 55562b6 "+1066 ppm uncorrected -> -9 ppm locked (120x), ~2-3 line dither (+/-12us duration, ~0.03% exposure variation), 0 drops"; 85d0326 "railing the clamp (+/-150us) and swinging VBLANK +/-15 lines ... -15 ppm (from +1066)"; e74e3e4 "-1394 ppm ... ~186ms ... ~54s"; 4537153 "-169ms ... ~47s"; 3b3ff60 "-90ms" and "sub-1.8-frame" — all verbatim. cinepi_controller.cpp:1211-1212 "~half-line (~125 ppm) floor"; hpp:354-355 exact. `git show 2f79397^:src/module/sensor_correction_factors.py` shows imx585 mode0 24: 0.9994, mode1 24: 0.9980, 25: 1.0 "exact after will127534/libcamera getBlanking patch (97f71626)", imx283 mode1 25: 0.9990. Recomputed: 1066/9 ≈ 118× (≈"120x"); 12/40000 = 0.03 %; 186 ms at the 24 fps rail (150 us × 24 = 3.6 ms/s) ≈ 52 s (+P-term tail ≈ 54 s); 169/3.6 ≈ 47 s. Markdown nit: the "VBLANK-only: never touches HMAX" comment is :1212-1213, not :1213-1214. |
| 11 | Handbook has no phase-lock measurement; hardware-log dated 2026-09-21 → 2026-10-07 | **CORRECTED (date range)** | lessons/hardware-log.md is **not in date order**: 80 dated `## 20xx` entries; the earliest is `## 2026-08-23/24` at :115 (also :149 2026-08-25, :178/:203/:248 2026-08-26, :598 2026-08-26 HMAX entry the reader itself cites), the latest `## 2026-10-07` at :3900; :41 is merely the first by line (2026-09-21). The conclusion stands: every entry post-dates the June phase-lock work and none mentions it (grep for phase.lock/pll_/sigma: 0 hits; the 'drift'/'timecode'/'wall.clock' hits at :132, :592, :1596 concern DNG timecode rounding, journal clock jumps and lores write cost). redis-contract.md:38-46 and :59-60, cinemate.md:193-199, what-the-pi-taught-us.md:38-39, testing.md:34 exact. repository-and-tooling-traps.md "phase lock ships off" is :**98**, not :97. |
| 12 | Audio capture timestamps; periodFrames/4 "~5.3 ms"; 10 ms period; 1 s ring; RT priority; 5 s cap | **CORRECTED (number + citation)** | :536-542 (MONOTONIC trigger, REALTIME, three tags), :638 TS_FIRST_BUFFER_A, :605 `maxGapFrames = rate * 5`, :647-669 reconciliation, :466-467 `periodTimeUs = 10000` / 1 s buffer, :533-534 RT elevation — exact. The tolerance constant is at :**611** (cited :599-610 stops one line short). The "~5.3 ms at 48 kHz" is the code comment (:606) and the 8e21f4a subject; it implies the device negotiated **periodFrames = 1024** (1024/4 = 256 frames = 5.33 ms; the earlier /8 "~2.7 ms" and /16 "~1.3 ms" commits agree). With the *requested* 10 ms period (480 frames) the tolerance would be 2.5 ms. periodFrames is whatever `snd_pcm_hw_params_get_period_size` returns (:510-513, fallback 256), so the ms figure is device-dependent; the reader's sentence conflates the two. |
| 13 | vts from SensorTimestamp; audio marker min(B,A) else START; start_delta; REALTIME metadata; -c:a copy; ppm removed 2026-06-03 | **CONFIRMED (one range nit)** | cinepi_recorder.hpp:86-87 SensorTimestamp, :100 `log_ts` exact. cinepi_sound.cpp:112-128 chooseAudioStartTimestamp; :1334-1338 vts; :1358-1361 marker; latency bias only when REALTIME marker missing :1372-1373; the subtraction `start_delta_seconds = ...` is at :**1378** (just past the cited :1334-1376); :1418 `buildMetadataFromWallclockNs(... ts_audio_start_realtime`; :1423 "audio-start"; :1529 `-c:a copy`; :1537 time_reference. 7398b62 body verbatim. Stale comment noted: sound.cpp:1332-1333 still says "ADC clock correction ppm — applies..." although the subsystem is gone. |
| 14 | Audio files untouched 2026-06-10..07-10; rework 06-02..06-06; lock 06-11..06-15 | **CONFIRMED** | `git log --since=2026-06-10 --until=2026-07-10 -- cinepi/cinepi_sound.cpp cinepi/cinepi_audio_capture.cpp cinepi/cinepi_sound.hpp` is empty. audio_capture log: fed2ede 2026-06-02 … 8e21f4a 2026-06-06; sound.cpp last pre-lock change f5973c3 2026-06-04. Lock commits bf717fa 2026-06-11 … 28b30cc 2026-06-15 (plus docs 0caa9a5 06-16, fallback fix 94102f7 07-06). |
| 15 | "FrameWallClock = the audio clock" = shared REALTIME domain; marker MONOTONIC vs video BOOTTIME compared raw | **CONFIRMED (as PROBABLE)** | Comments at cinepi_controller.cpp:734, :1206, hpp:108-110 read; audio_capture.cpp:536-537 MONOTONIC/REALTIME; recorder.hpp:86-87 BOOTTIME; sound.cpp:1372-1378 subtracts them without conversion. Label honest — nothing stamps samples with FrameWallClock. |
| 16 | SetControls pending list; queueRequest moves it; IPA FRAME_DURATION_LIMITS → applyFrameDurations → setMaxExposureTime; applyAGC getBlanking clip; VBLANK-only below maxFrameLength | **CORRECTED (citation)** | rpicam_app.cpp:1097-1106 SetControls ("applied to the next StartCamera or request"), :1022-1024 `request->controls() = std::move(controls_)`, :1027 queueRequest, :975 queueRequest decl — exact. ipa_base.cpp:1186-1190, :1638-1667 (`agc->setMaxExposureTime` :1667), :1691 comment — exact; the `V4L2_CID_VBLANK` / `V4L2_CID_EXPOSURE` writes are at :**1704-1705**, outside the cited :1691-1702. cam_helper.cpp:82-126 getBlanking with the HMAX stretch only `if (frameLengthLines > mode_.maxFrameLength)` — exact. |
| 17 | Manual exposure default in cinepi-raw; AGC-on coexists | **CONFIRMED (as PROBABLE)** | rpicam_app.cpp:825-828 sets ExposureTimeModeManual / AnalogueGainModeManual when unset; ipa_base.cpp:1663-1667 recomputes max exposure per applyFrameDurations. AGC-on behaviour is reasoned, not measured — label honest. |
| 18 | No imx585 getBlanking override at bfe0b76; the will127534 patch "probably reverted" | **CORRECTED (strengthened)** | grep confirms overrides only in cam_helper_imx477/519/708/500 @bfe0b76; cam_helper_imx585.cpp exists but has none. The fork's history is **not** shallow enough to hide it: 1282 commits back to 2023-05-01; cam_helper_imx585.cpp has exactly two commits (64570c7 2025-03-15 "Adding IMX585 + IMX585-mono support", c8af77d 2025-03-15 "remove getDelays in cam_helper") and `git log -S getBlanking -- src/ipa/rpi/cam_helper/cam_helper_imx585.cpp` is empty; `97f71626` and `ea5abb8b` are not objects in this repo. So the override was **never in Tiramisioux/libcamera's lineage**, not reverted from it; the old docs/fps-correction.md:7 (@2f79397^) credits "will127534/libcamera, ea5abb8b", a different lineage. |
| 19 | Defaults and knobs (ships off, Cinemate seeds on, --phase-lock, live handlers, telemetry, changelog) | **CORRECTED (citations)** | hpp:353 `phaseLockEnabled_{false}`; cpp:401-408 precedence with seed `"0"` at :**408** (prose says :407); :410-424 gain keys; :982-996 live handlers; :1161/:1165/:1188 dispatch+subscribe; cinepi_options.cpp:227-230 help, :572-585 parser (bare flag, following 0/1, on/off/true/false); raw_options.hpp:66-68; README.md:176 — all exact. cinemate: cinepi_controller.py:120-144 exact; config_loader.py:556 exact; settings.jsonc cam0 `"phase_lock": true` at :100 (comments :98-99) but cam1 is at :**121**, not :116; docs/settings-json.md:78 exact; docs/redis-keys.md:23 "read once at CinePi-raw startup, not live" exact (and contradicted by cpp:982-986); redis_controller.py:34 key, :329-330 `set_value` docstring "Write key, publish" (the publish statement itself was not opened); changelog.md:97, :114-116 exact; cinepi_controller.py fps_user write is :1763-1764 and the "hardware fps == the user fps" comment :1766-1767 (within the cited :1762-1767). |
| 20 | Apertar inputs: SensorTimestamp read, RecordingClock offset, audio stamps, pendingControls_ merge, truncated 1e6/fps, max>min in photo mode | **CORRECTED (citation)** | @f60e301: CameraController.cpp:7239 SensorTimestamp, :7253 wallClockForSensorTimestamp, :7183-7187 its definition, :2075 `static_cast<int64_t>(1000000.0 / settings.fps)`, :2079-2083 maximumFrameDurationUs/FrameDurationLimits — exact. RecordingClock.hpp:34-48 (constructor averages two BOOTTIME reads around one REALTIME read, same scheme as libcamera addSample()) exact. AudioRecordingSession.cpp:348-349, :427-428, :577-578 exact. **The `pendingControls_` merge is at :6841-6843** (`request->controls().merge(pendingControls_)` :6842) inside `requeueRequest` (:6833) under `controlsMutex_` (:6840); the cited :6864-6876 is a different block (still-preview `controlsForSettings` restore). |
| 21 | Loop latency / gain transfer UNKNOWN | **CONFIRMED as UNKNOWN → now PROBABLE estimate** | pisp.cpp:1746 `delayedCtrls_->get(...)` exact; 55562b6 "Verified on imx585 mode0 @25fps" exact. See *Added* A2 for a source-derived estimate. |
| 22 | Slope-vs-BOOTTIME difference unmeasured; tests prove offset invariance only | **CONFIRMED** | tests :142-168 comment "the loop only uses int64 *differences*" exact. No measurement in any repo. |

### Surprises re-checked

- S1 unit divergence: holds; cite cinepi_controller.cpp:**593** for the `* 1'000ULL`.
- S2 ships off: holds; seed at :**408**; handbook traps line is :**98**.
- S3 live handler vs stale doc row: holds (cpp:982-996 vs redis-keys.md:23).
- S4 MONOTONIC marker vs BOOTTIME video: holds (audio_capture.cpp:536-537; recorder.hpp:86-87; sound.cpp:1372-1378).
- S5 getBlanking override absent: holds and is stronger — never in this fork's history (see #18).
- S6 factor magnitudes: 1−0.9994 = 600 ppm, 1−0.9980 = 2000 ppm, 1−0.9990 = 1000 ppm; clamp pull range 3600–3750 ppm — arithmetic correct.
- S7 handbook dates: **corrected** to 2026-08-23/24 → 2026-10-07 (still all after June).

### Added (settled from source in this pass)

**A1. Which libcamera emits which FrameWallClock unit, dated.** With the qbc clone deepened to
1995 commits: upstream **29a88d85 (Naushir Patuck, 2025-07-08) "libcamera: controls: Use
nanoseconds units for FrameWallClock"** changed the yaml and the RPi pipeline handlers to ns;
**c576b437 (David Plowman, 2025-08-14)** added the `/ 1000` in `ipa/rpi/controller/rpi/sync.cpp`
("Convert from ns into us", qbc sync.cpp:166-167@7e9fef0); **bfd68f78 (Paul Elder, 2025-09-01)**
made `ClockRecovery::addSample()` sample in ns. The cinemate fork (Tiramisioux/libcamera, last
upstream merge 983ffa7 2025-04-22; its sync.cpp:166-167 uses `local.wallClock` directly) predates
all three → **microseconds**; Cinemate's installer clones exactly that fork
(cinemate/cinemate-install.sh:94 `LIBCAMERA_REPO_URL=.../Tiramisioux/libcamera.git`;
docs/installation-steps.md:99 "`cinemate` branch tip — Will Whang's IMX585 fork (base 9d0cdfe5)"),
so cinepi-raw's `* 1000` is correct on a Cinemate Pi. The qbc clone is
`will127534/libcamera` branch `qbc-pisp-handler` → **nanoseconds**. Apertar's README says it builds
against the image's "libcamera and libcamera-base development files" or "a custom libcamera build"
(apertar-core/README.md:186,199@f60e301); any libcamera carrying upstream ≥ 2025-07-08 (every
Raspberry Pi OS libcamera released after that) emits ns. **PROBABLE: an Apertar Pi sees ns.**
A port must still check at runtime (e.g. compare FrameWallClock − SensorTimestamp magnitude to
the REALTIME−BOOTTIME offset).

**A2. Loop latency, estimated from source (PROBABLE).** A request's controls are applied when
the pipeline dispatches that request with a captured frame, not when it is queued:
libcamera(cinemate)/src/libcamera/pipeline/rpi/pisp/pisp.cpp:2353 `params.requestControls =
request->controls()` → :2367 `ipa_->prepareIsp(params)` → src/ipa/rpi/common/ipa_base.cpp:399
`applyControls(params.requestControls)` (qbc: pisp.cpp:2929/:2970, ipa_base.cpp:428, same
mechanism). The AGC result for that frame goes out through `setDelayedControls.emit`
(ipa_base.cpp:527-530) and DelayedControls applies VBLANK with the sensor's delay:
imx585 `vblankDelay = 2` (src/libcamera/sensor/camera_sensor_properties.cpp:298-302; default
table also 2, camera_sensor_legacy.cpp:489-494; pipeline_base.cpp:822-829 wires them). rpicam-apps
queues every buffer at start (cinepi-raw/core/rpicam_app.cpp:923-926) and re-queues each completed
request carrying the pending list (:1022-1027), so a control pushed at frame k rides the request
that is dispatched ≈ buffer-count frames later. With Cinemate's default `--buffer-count 8`
(cinemate/src/module/cinepi_multi.py:845-847) the push→realised-frame delay is ≈ 8 + 1 (AGC on
that frame) + 2 (VBLANK delay) ≈ **10–11 frames**; with Apertar's 3 requests in flight ≈ 3 + 1 + 2
≈ **5–6 frames**. A shorter loop delay gives the same PI gains more phase margin, so kp 0.06 /
ki 0.0015 should be *at least* as stable in Apertar; the exact dispatch order inside the pipeline
queue was not traced, hence PROBABLE. On-camera verification still required.

**A3. The imx585 getBlanking override never existed in Tiramisioux/libcamera** (detail in #18);
the reader's "unanswered" item 5 is settled.

**A4. apertar-core HEAD is ahead of the reader's commit.** HEAD 2a6f114 (2026-10-26, "camera:
frame-rate phase lock, off by default (fps_phase_lock)") already adds
`src/camera/FramePhaseLock.hpp` (147 lines) referenced to SensorTimestamp/CLOCK_BOOTTIME, with
the commit message stating "not compiled here". The reader's §7 "inputs Apertar must supply" is
correct for f60e301 and remains the right baseline for the tutorial; verifying the HEAD port is a
separate task.

### Still UNKNOWN after verification

- Any measured drift before/after in the handbook (none exists; only commit figures).
- Whether FrameWallClock's fitted slope differs measurably from raw CLOCK_BOOTTIME on a Pi.
- The realised ALSA `periodFrames` on Apertar's audio device (the ~5.3 ms tolerance figure is
  device-specific).
- The exact in-pipeline dispatch order that fixes A2's frame counts; and kp/ki behaviour on
  Apertar hardware.
