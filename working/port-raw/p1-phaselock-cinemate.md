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
