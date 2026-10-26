---
datum: 2026-10-26 09:00:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T27 frame-rate-phase-lock
typ: digital anteckning
---

# T27. The optional frame-rate phase lock: measure the cadence, simulate the servo, then switch it on

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-camera-frame-rate-phase-lock-off-by-default-fps_phas.patch` is the reference, not compiled on a Pi; the pure servo header passes `working/tools/phase_lock_sim.cpp` on the host). Needs T23–T25 applied (the patch sits on top of them). Answer: `working/phaselock-answer.md`. Builds **M7** (sensor path), the libcamera control merge, and the audio/video clock story.

**You will learn**
- Why a 24.000 fps sensor is never 24.000 fps against the Pi clock, and what that does to Core's frame numbering and WAV length over a long take.
- How Cinemate's phase lock works (a PI servo whose integer-microsecond requests dither the sensor between two line counts), and how to prove the law on your Mac before touching the camera.
- Which Core clock the lock must be referenced to so that the audio pipeline does not change.
- How to measure cadence correctly (average the intervals, then invert) and what the one Core-specific hazard is (a libcamera lattice search that may move HMAX).

**Risk:** Core rebuild and restart only; the lock is **off by default** and a setting flips it. A wrong request range is clamped by libcamera, not by the sensor. Undo: `set_fps_phase_lock enabled=false`, or `git checkout` the four files. **Time:** 3 h including a 10-minute take.

## 1. The problem

Core pins `FrameDurationLimits {d, d}` once per fps change (`CC:2091-2098`), so the sensor runs free at the nearest whole number of its own lines. Its crystal and the Pi's differ by tens of ppm, sign unknown. Over a take Core's `nextFrameIndex` rounds `(ts - t0) × fps` to pick DNG numbers (`CC:3706-3712`): a slow sensor makes it skip a number (a hole with no real drop, nothing logged) after 0.5/e frames — 30 ppm at 24 fps is one hole every ~11.6 min — and `observeVideoFrame` rolls the WAV a frame longer at the same point. A fast sensor keeps the numbers consecutive but the audio, measured against the Pi clock, drifts e × clip length against the picture: 30 ppm × 1 h = 108 ms.

Cinemate measured its imx585 at **+1066 ppm** on one mode (`cinepi-raw 55562b6`) and locked it to **−9 ppm** with 2–3 lines of dither. Apertar's qbc libcamera already picks exact line counts for 24/25/30/50/60 on the sensor clock (p2 §4), so expect a smaller but non-zero number here. Step 3 measures it.

## 2. How this part works

```
 completion thread:  requestComplete()  -> metadata (SensorTimestamp, FrameDuration)
                         -> stepFramePhaseLock(request)          CC:7147   (new)
                              phase error = ts - (origin + k/fps)  on CLOCK_BOOTTIME
                              PI servo (kp 0.06, ki 0.0015), deadband 6 us, clamp +/-150 us
                              request = round(nominal - correction)  -> whole microseconds
                         -> requeueRequest(request)               CC:7183
                              ... photo-mode merges ...
                              if phaseLockDurationUs_: set FrameDurationLimits {d, d}   CC:7263-7264
                              camera_->queueRequest(request)      CC:7271
```

The sensor can only realise whole lines (≈11 µs at 4K/25 fps), so a request of 40 003 µs becomes 40 007 and 40 002 becomes 39 996: the servo's integer requests alternate between the two and the **average** lands on nominal. That is a first-order sigma-delta; the instantaneous error stays inside the deadband. Cinemate's first version was pure-integral and oscillated to the clamp (`85d0326`); the P term is the damping.

Reference clock: Cinemate uses `FrameWallClock` (wall time, "= the audio clock" in cinepi-raw). Core stamps audio on CLOCK_BOOTTIME (`src/audio/TimestampedAudioCapture.cpp:195-228`) and `SensorTimestamp` is BOOTTIME too (kernel `ktime_get_ns()`, `rp1_cfe/cfe.c:692`), so Core's reference is `SensorTimestamp` and **the audio path does not change**; `finalizeWav`'s resampler keeps correcting the ALSA crystal (`AudioRecordingSession.cpp:526-531`).

Gap policy, the part Cinemate needed three Pi rounds for (`e74e3e4`, `3b3ff60`, `4537153`): in preview a gap > 1.5 frames (a mode switch) re-arms the datum; while recording a gap is a real drop and the missed frames are counted so the phase does not jump; in preview a leaked error > half a frame re-arms too.

Reading assignments: `src/camera/FramePhaseLock.hpp` (all 147 lines), `CC:7147-7181`, `CC:7263-7265`, `CC:6120-6127`, `CC:6286-6293`, `p2-phaselock-core.md` §3 and §5.

## 3. Find it yourself

**3.0 Prove the law on your Mac first** (no camera; mirrors Cinemate `28b30cc`, "tests that exercise the shipped code path, not a copy")

```bash
cd ~/apertar-kb/working/tools
g++ -std=c++20 -O2 -Wall -I ~/ApertarCore/src/camera phase_lock_sim.cpp -o /tmp/phase_lock_sim && /tmp/phase_lock_sim
```

Prediction: 17 `[ok]` lines; case 1 ends within 10 ppm with 3 distinct requests; case 2 (an exactly-on sensor) shows 0 pushes.

> [!tip]- Answer
> `locked: mean 0.00 ppm, max |err| 13.9 us, pushes 4882, distinct requests 3` — the dither toggles every ~4 frames, like Cinemate's "2–3 line dither". Case 2 prints `pushes 0`: inside the deadband the servo holds and sends nothing. Note the comment in the test: a 24 fps period (41666.667 µs) *must* dither between 41666 and 41667, so exactness is tested at 25 fps.

**3.1 Which clock stamps the frames, and which clock stamps the audio?** (Pi, read-only)

```bash
grep -n 'SensorTimestamp' ~/ApertarCore/src/camera/CameraController.cpp | head -5
grep -n 'SND_PCM_TSTAMP_TYPE_MONOTONIC\|CLOCK_BOOTTIME' ~/ApertarCore/src/audio/TimestampedAudioCapture.cpp
grep -rn 'FrameWallClock' ~/ApertarCore/src | wc -l
```

Prediction: the audio converts MONOTONIC to BOOTTIME; Core never reads `FrameWallClock`.

> [!tip]- Answer
> `TimestampedAudioCapture.cpp:195` sets MONOTONIC stamps and `:227-228` adds `BOOTTIME - MONOTONIC`. The count is 0. Both pipelines live on BOOTTIME, which is why the lock is referenced to `SensorTimestamp` and not to wall time (p2 §3). Choosing wall time would import NTP slew into every BOOTTIME consumer.

**3.2 Measure the cadence error you have today** (Pi, 10-minute take, before the patch)

Record a 10-minute cDNG take at your usual 24 or 25 fps, then from the journal and the files:

```bash
# frame interval statistics from the DNG wall-clock stamps are too coarse; use the capture stats and the file count instead
journalctl -u apertar-core -b --no-pager | grep -E 'recording clip:|capture stats:|audio sync:|audio clock:' | tail -4
CLIP=$(journalctl -u apertar-core -b --no-pager | grep 'recording clip:' | tail -1 | sed 's/.*clip: \([^ ]*\).*/\1/')
ls "$CLIP"/*.dng | wc -l
python3 -I - "$CLIP" <<'PY'
import sys, os, re
names = sorted(int(re.search(r'_(\d{6,})\.dng$', f).group(1)) for f in os.listdir(sys.argv[1]) if f.endswith('.dng'))
holes = [b for a, b in zip(names, names[1:]) if b != a + 1]
print("frames", len(names), "index holes", len(holes), holes[:5])
PY
```

Prediction: 0 or a handful of index holes at exactly regular spacing (a slow sensor), or none (a fast one). `audio sync: ... output_samples=` equals `frames × rate / fps` within one frame.

> [!tip]- Answer
> Regularly spaced holes with `dropped_gap_estimate=0` are `nextFrameIndex` rounding, not drops: the sensor is slow by `1/(hole spacing)` ppm. No holes and a 10-minute take means the sensor is exact or fast; the fast case shows up as A/V offset at the end of a long take, not in any log. Write the sign and magnitude down; the lock's job is to make this number 0.

**3.3 Does a 1 µs duration change move VBLANK or HMAX on your libcamera?** (Pi, the Core-specific hazard)

Apertar's libcamera fork may carry an IMX585 `getBlanking` lattice search (`libcamera-qbc 4cff971`, after the 20260522 tag) that re-chooses (VMAX, HMAX) per requested microsecond. Cinemate kept its lock VBLANK-only because an HMAX-stretching patch once broke the 4K image (`bf717fa`). Pin two durations 1 µs apart and read the sensor back:

```bash
git -C ~/libcamera log --oneline | grep -i 'lattice\|getBlanking' | head -3        # is 4cff971 in your tree?
v4l2-ctl --list-subdevs 2>/dev/null; SUB=$(ls /dev/v4l-subdev* | head -1)
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=25
v4l2-ctl -d $SUB --get-ctrl=hblank,vblank
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=24.9994        # 40001 us
v4l2-ctl -d $SUB --get-ctrl=hblank,vblank
```

Prediction: `hblank` identical, `vblank` differs by one line → VBLANK-only, safe. If `hblank` changes, the lattice is active.

> [!tip]- Answer
> With the lattice active the dither changes the line time, i.e. the rolling-shutter skew and the exposure quantum, by a fraction of a percent every few frames. Cinemate's "0.03 % exposure variation" assumes VBLANK-only. Measure before enabling: a 1-minute take with the lock on, a flat grey target, and the frame-to-frame mean level in `tools/dng_inspect.py`-style statistics; if it is stable to 0.1 %, proceed; if not, raise the deadband to 12 µs (one line) in `FramePhaseLock::Tuning` and note the finding in `lessons/hardware-log.md`.

## 4. Make the change

Four files. The patch is the reference; type it in this order.

**4.1 The pure servo** — create `src/camera/FramePhaseLock.hpp` exactly as in the patch (147 lines). Key points to type with understanding, not copy: `Tuning{0.06, 0.0015, 6.0, 150.0}`; `step()` re-arms when `!active`, on an fps change, or on a preview gap > 1.5 periods; absorbs recording gaps into `frames`; applies the PI update only outside the deadband with anti-windup `clampUs / integral`; `durationUs = llround(requestedUs)`; `pushDuration` only when the integer changed.

Re-run step 3.0 against *your* header: `g++ ... -I ~/ApertarCore/src/camera phase_lock_sim.cpp` must still pass 17/17.

**4.2 The setting** — `include/apertar/core/Types.hpp`: in `struct CaptureSettings` after `double fps = 24.0;` add
```cpp
    bool fpsPhaseLock = false; // Closed-loop cadence lock to the Pi clock (FramePhaseLock).
```
`CC:187`, `:731`, `:801`: JSON out, settings-file in, settings-file out for `fps_phase_lock` (three one-liners next to `fps`).

**4.3 The step and the pin** — `CameraSession`:
- members next to the controls state (`CC:8199-8200`): `FramePhaseLock phaseLock_; std::optional<int64_t> phaseLockDurationUs_;` guarded by `controlsMutex_`.
- `stepFramePhaseLock(libcamera::Request *)` (`CC:7147-7181`): read `SensorTimestamp`; `enabled = settings_.fpsPhaseLock && !photoModeEnabled && fps > 1`; `recording = recordingFramesEnabled_`; call `step()`; on `rearmed` clear the pin and log `ApertarCore phase-lock: armed fps= nominal_us= ref=boottime`; on `pushDuration` set `phaseLockDurationUs_`; every 250 frames with `APERTAR_PHASE_LOCK_LOG=1` print `frames= err_us= req_us= pushes=`.
- call it from `requestComplete` before `requeueRequest` (`CC:7336`).
- in `requeueRequest`, after the photo-mode merges and only when not photo-busy (`CC:7263-7265`): `request->controls().set(controls::FrameDurationLimits, {d, d})`.
- release on `stop()` (`CC:6040-6041`) and when fps or the switch changes in `applyControls` (`CC:6123-6126`); print `ApertarCore phase-lock stats: max_abs_err_us= duration_pushes=` in `stopRecording` (`CC:6289-6292`) and reset telemetry.

**4.4 The command** — `ApertarCoreApp.cpp`: `set_fps_phase_lock` with `enabled` (`App:9631-9640`), the help list entry (`App:9389`), `fps_phase_lock` in both state JSONs (`App:203`, `:7913`); `CameraController::setFpsPhaseLock(bool)` (`CC:9027`).

Why the pin goes *after* the photo merges: a still capture's long exposure sets its own `FrameDurationLimits`; the servo must lose that argument, which is also why `enabled` excludes photo mode.

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | tail -3
sudo systemctl restart apertar-core
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -o '"fps_phase_lock":[a-z]*'      # false
```

**5.1 Enable and watch it arm**

```bash
sudo systemctl set-environment APERTAR_PHASE_LOCK_LOG=1 && sudo systemctl restart apertar-core
python3 -I ~/apertar-kb/working/tools/core.py set_fps_phase_lock enabled=true
sleep 20; journalctl -u apertar-core -b --no-pager | grep 'phase-lock' | tail -3
```

Prediction: one `armed fps=25 nominal_us=40000 ref=boottime` line within a second, then `frames=250 err_us=<±15> req_us=<39990..40010> pushes=<~60>`.

**5.2 The 10-minute take, after** — repeat 3.2 with the lock on. Prediction: 0 index holes; `phase-lock stats: max_abs_err_us=` ≤ 20; `duration_pushes` ≈ frames/4; `audio clock: measured_drift_ppm=` unchanged from 3.2 (it is the ALSA crystal, not the sensor); `dropped_gap_estimate=0`.

**5.3 Cinemate's failing case** — switch resolution (a reconfigure), then start recording within 2 s:

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_resolution width=1920 height=1080; sleep 1
python3 -I ~/apertar-kb/working/tools/core.py record_start; sleep 30; python3 -I ~/apertar-kb/working/tools/core.py record_stop
journalctl -u apertar-core -b --no-pager | grep 'phase-lock' | tail -4
```

Prediction: an `armed` line right after the switch (preview re-arm), and `max_abs_err_us` for the take still ≤ 20. Cinemate's first two versions started such takes 90–169 ms behind (`3b3ff60`, `4537153`).

What success looks like: holes gone, max error tens of µs, pushes every few frames, audio drift figure unchanged, no `drop[capture-gap]` lines caused by the lock. Then decide the default: edit `Types.hpp` to `true` only after a week of takes.

## 6. Commit and push

```bash
git -C ~/ApertarCore add include/apertar/core/Types.hpp src/camera/FramePhaseLock.hpp src/camera/CameraController.cpp src/camera/CameraController.hpp src/ApertarCoreApp.cpp
git -C ~/ApertarCore commit -m "camera: frame-rate phase lock, off by default (fps_phase_lock)

PI servo on the accumulated phase error of SensorTimestamp against
origin + k/fps on CLOCK_BOOTTIME; whole-microsecond FrameDurationLimits
requests dither the sensor between adjacent line counts. Referenced to
BOOTTIME because Core's audio is stamped there: no audio change.
Logic ported from Cinemate's phase lock (cinepi-raw bf717fa..4537153).
Tested: <your 3.2 vs 5.2 numbers>, mode-switch case, hblank readback."
git -C ~/ApertarCore push -u origin main
```

Record the before/after cadence numbers and the HBLANK answer in `lessons/hardware-log.md`.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `armed` repeats every few seconds while idle | preview re-arm storm: gaps > 1.5 frames in preview, i.e. the preview itself drops frames | fix the drop first (T22–T25); the lock is a symptom reader here |
| `max_abs_err_us` grows past 150 and stays | the sensor cannot realise the request (clamp reached) or the lattice moved HMAX | check 3.3; compare `FrameDuration` metadata to the request in the 250-frame trace |
| `drop[capture-gap]` lines appear only with the lock on | a request outside the IPA's accepted range got clamped and the frame restarted | look at `ApertarCore camera controls` warnings; raise `clampUs` only after reading the mode's `FrameDurationLimits` range |
| audio drift figure changes with the lock | it should not; something else moved (USB load, mic) | compare two idle 2K takes first |
| still captures take the servo's duration | pin merged before the photo block | the pin belongs after the photo merges (`CC:7263`) and `enabled` must exclude photo mode |

Undo: `set_fps_phase_lock enabled=false` (persisted). Full undo: `git checkout -- include/apertar/core/Types.hpp src/camera src/ApertarCoreApp.cpp`, rebuild.

## 8. What you learned, going further

- Two crystals, one clock to rule them: discipline the picture to the clock the audio is on, and the audio code does not move.
- The integer rounding *is* the dither; a deadband prevents control churn; a clamp bounds the damage.
- Exercise: expose `phaseLock_.maxAbsErrorUs` in `/api/state` next to `fps_phase_lock` so the switch is never shown without the number that would falsify it (Cinemate's `fps_actual` showed 24 for the life of the system, `b029d7f`).
- Going further: a `ApertarCore phase-lock saturated` line once per take when the request hits the clamp.

## 9. Sources

- `cinepi-raw/cinepi/phase_lock_core.hpp@63a08d5` (law), `tests/phase_lock_core_test.cpp` (behaviours), `cinepi_controller.cpp:733-737` (wall clock = audio clock); commits `bf717fa`, `85d0326`, `55562b6`, `d038556`, `e74e3e4`, `3b3ff60`, `4537153`, `5b4b209`, `28b30cc`, `3c6477e`; cinemate `0b8e947`, `2f79397`, `b029d7f`.
- `Apertar-Core@2a6f114`: `src/camera/FramePhaseLock.hpp`; `CC:7147-7181`, `:7263-7265`, `:7336`, `:6040`, `:6123-6126`, `:6289-6292`, `:8199-8200`, `:9027`; `App:203`, `:7913`, `:9631`; `Types.hpp:127`.
- `working/phaselock-answer.md`, `working/port-raw/p1-phaselock-cinemate.md`, `p2-phaselock-core.md`, `working/cinemate-lessons.md` §2–3, `working/tools/phase_lock_sim.cpp`.

%% tutor
ref core src/camera/FramePhaseLock.hpp 70 Decision step(bool enabled, bool recording, double fps, int64_t referenceNs)
ref core src/camera/FramePhaseLock.hpp 81 const bool bigGap = active && sincePrevious > static_cast<int64_t>(1.5 * periodNs);
ref core src/camera/FramePhaseLock.hpp 120 const int64_t durationUs = std::llround(requestedUs);
ref core src/camera/CameraController.cpp 7147 void stepFramePhaseLock(libcamera::Request *request)
ref core src/camera/CameraController.cpp 7263 if (phaseLockDurationUs_ && !photoBusy && !settings_.photoModeEnabled) {
ref core src/camera/CameraController.cpp 7336 stepFramePhaseLock(request);
ref core src/camera/CameraController.cpp 6123 if (std::fabs(settings_.fps - sanitized.fps) > 1e-9 || settings_.fpsPhaseLock != sanitized.fpsPhaseLock ||
ref core src/camera/CameraController.cpp 6290 std::cerr << "ApertarCore phase-lock stats: max_abs_err_us=" << std::lround(phaseLock_.maxAbsErrorUs)
ref core include/apertar/core/Types.hpp 127 bool fpsPhaseLock = false;
ref core src/ApertarCoreApp.cpp 9631 if (command.name == "set_fps_phase_lock") {
ref core src/audio/TimestampedAudioCapture.cpp 195 SND_PCM_TSTAMP_TYPE_MONOTONIC
check 3.0 | g++ -std=c++20 -O2 -I /home/pi/ApertarCore/src/camera /home/pi/apertar-kb/working/tools/phase_lock_sim.cpp -o /tmp/phase_lock_sim && /tmp/phase_lock_sim | tail -1 | ALL CHECKS PASSED
check 3.1 | grep -rc 'FrameWallClock' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^0$
check 4.1 | test -f /home/pi/ApertarCore/src/camera/FramePhaseLock.hpp && grep -c 'struct FramePhaseLock' /home/pi/ApertarCore/src/camera/FramePhaseLock.hpp | ^1$
check 4.2 | grep -c 'bool fpsPhaseLock' /home/pi/ApertarCore/include/apertar/core/Types.hpp | ^1$
check 4.3 | grep -c 'stepFramePhaseLock' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 4.4 | grep -c 'set_fps_phase_lock' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[2-9]$
check 5.1 | journalctl -u apertar-core -b --no-pager | grep -c 'phase-lock: armed' | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
