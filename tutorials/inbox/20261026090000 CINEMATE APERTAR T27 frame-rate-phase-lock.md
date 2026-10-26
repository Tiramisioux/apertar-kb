---
datum: 2026-10-26 09:00:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T27 frame-rate-phase-lock
typ: digital anteckning
---

# T27. The optional frame-rate phase lock: measure the cadence, simulate the servo, then switch it on

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-camera-frame-rate-phase-lock-off-by-default-fps_phas.patch` is the reference, Core `9e6df59`, not compiled on a Pi; the pure servo header passes `working/tools/phase_lock_sim.cpp` on the host; amended after the critic pass with env gains, saturation detection, state telemetry and a pin that reads no settings). Needs T23–T25 applied (the patch sits on top of them). Line numbers are at `9e6df59`, the tree right after this patch; later patches shift them, the grep anchors do not. Answer: `working/phaselock-answer.md`. Builds **M7** (sensor path), the libcamera control merge, and the audio/video clock story.

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
 completion thread:  requestComplete()  -> metadata (SensorTimestamp, FrameDuration, FrameDurationLimits echo)
                         -> stepFramePhaseLock(request)          CC:7051   (new)
                              gains from APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US at arm   CC:7068-7081
                              phase error = ts - (origin + k/fps)  on CLOCK_BOOTTIME
                              PI servo (kp 0.06, ki 0.0015), deadband 6 us, clamp +/-150 us
                              request = round(nominal - correction)  -> whole microseconds
                              saturation: echoed limits != any of the last 4 pins -> one log line   CC:7105-7122
                         -> requeueRequest(request)               CC:7183
                              ... photo-mode merges ...
                              if phaseLockDurationUs_ && !photoBusy: set FrameDurationLimits {d, d}   CC:7229-7234
                              camera_->queueRequest(request)      CC:7275
 state:              phaseLockStatus() CC:7133 -> CameraController CC:9422 -> /api/state fps_phase_lock_{active,err_us,dur_us,pushes,saturated}  App:7857-7861
```

The sensor can only realise whole lines (≈11 µs at 4K/25 fps), so a request of 40 003 µs becomes 40 007 and 40 002 becomes 39 996: the servo's integer requests alternate between the two and the **average** lands on nominal. That is a first-order sigma-delta; the instantaneous error stays inside the deadband. Cinemate's first version was pure-integral and oscillated to the clamp (`85d0326`); the P term is the damping.

Reference clock: Cinemate uses `FrameWallClock` (wall time, "= the audio clock" in cinepi-raw). Core stamps audio on CLOCK_BOOTTIME (`src/audio/TimestampedAudioCapture.cpp:195-228`) and `SensorTimestamp` is BOOTTIME too (kernel `ktime_get_ns()`, `rp1_cfe/cfe.c:692`), so Core's reference is `SensorTimestamp` and **the audio path does not change**; `finalizeWav`'s resampler keeps correcting the ALSA crystal (`AudioRecordingSession.cpp:526-531`).

Gap policy, the part Cinemate needed three Pi rounds for (`e74e3e4`, `3b3ff60`, `4537153`): in preview a gap > 1.5 frames (a mode switch) re-arms the datum; while recording a gap is a real drop and the missed frames are counted so the phase does not jump; in preview a leaked error > half a frame re-arms too. The reasons, so you do not simplify them away: a reconfigure stall is *not* a whole number of frames, so absorbing it leaves a fractional residual that the clamp-limited loop bleeds off at ~3 ms per second — recordings started 90–169 ms behind until preview re-armed instead (`3b3ff60`); and the lock runs in preview at all so that a take starts already locked (`d038556`). Pure integral control oscillated to the clamp on the first Pi test; the proportional term is the damping (`85d0326`).

The pin reads no `settings_`: `requeueRequest` is also reached from the ProRes and H.264 release paths without the session-settings lock, so `applyControls` clears the pin under `controlsMutex_` whenever fps, the switch or photo mode changes (`CC:6046-6050`) and the pin's presence is the only condition left.

Reading assignments: `src/camera/FramePhaseLock.hpp` (all), `CC:7051-7143`, `CC:7222-7236`, `CC:6043-6051`, `CC:6207-6214`, `p2-phaselock-core.md` §3 and §5, `working/port-raw/critic.md` items P1–P9.

## 3. Find it yourself

**3.0 Prove the law on your Mac first** (no camera; mirrors Cinemate `28b30cc`, "tests that exercise the shipped code path, not a copy")

```bash
# Mac. The header does not exist in the Core tree until 4.1, so take it from the reference patch into a scratch folder.
KB=~/Documents/Apertar/apertar-kb; S=$(mktemp -d)
(cd "$S" && git init -q && git apply --include='src/camera/FramePhaseLock.hpp' "$KB"/working/patches/0001-camera-frame-rate-phase-lock*.patch)
g++ -std=c++20 -O2 -Wall -I "$S/src/camera" "$KB/working/tools/phase_lock_sim.cpp" -o "$S/phase_lock_sim" && "$S/phase_lock_sim"
```

After 4.1 the same test runs against your own header: `-I ~/Documents/Apertar/Apertar-Core/src/camera` on the Mac, or on the Pi
`g++ ... -I ~/ApertarCore/src/camera ~/apertar-kb/working/tools/phase_lock_sim.cpp`.

Prediction: 22 `[ok]` lines; case 1 ends within 10 ppm with 3 distinct requests and settles from a cold arm in a few hundred frames; case 2 (an exactly-on sensor) shows 0 pushes; case 6 prints the qbc lattice table.

> [!tip]- Answer
> `locked: mean 0.00 ppm, max |err| 13.9 us, pushes 4882, distinct requests 3` — the dither toggles every ~4 frames, like Cinemate's "2–3 line dither". `cold arm: |err| stays < 20 us after frame 157 (6.3 s at 25 fps)`: Cinemate's unit test waits 1000 frames before bounding the error, which is conservative. Case 2 prints `pushes 0`: inside the deadband the servo holds and sends nothing. Note the comment in the test: a 24 fps period (41666.667 µs) *must* dither between 41666 and 41667, so exactness is tested at 25 fps. Case 6 is what step 3.3 is about.

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

Prediction: `hblank` identical, `vblank` differs by one line → VBLANK-only, the default helper. If `hblank` changes, the lattice is active; the simulator's case 6 says what to expect.

> [!tip]- Answer
> The simulator models the lattice from the helper's source (`phase_lock_sim.cpp`, `LatticeSensor`, from `cam_helper_imx585.cpp:95-225`). At 25 fps, 40000 µs is exact (HMAX 550 × VMAX 5400); 40001 becomes HMAX 581 × 5112 = 40000.97 µs and 39999 becomes HMAX 551 × 5390 = 39998.52 µs — so a 1 µs push moves the *line length* by up to 5.6 % and the readback shows `hblank` jumping, not `vblank`. The helper re-fits the exposure time to the new line, so exposure stays put; what changes is the rolling-shutter skew by that 5.6 % on the frames that carry HMAX 581. At 24 fps, 41666 and 41667 both snap to the exact 625 × 4950, so ±1 µs pushes are no-ops there and the servo's ±2 µs requests land at 41665.37 / 41668.15 µs. Under this model the lock still holds (simulated +300 ppm sensor: 0.03 ppm mean, max error 7 µs, a push every ~23 frames, two HMAX values). Decide with a picture: a 1-minute take on a flat grey target with the lock on; if frame-to-frame mean level is stable to 0.1 % and a fast pan shows no skew flicker, proceed; otherwise raise `APERTAR_PHASE_LOCK_DEADBAND_US` to 12 (one line) and note it in `lessons/hardware-log.md`.

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
- `stepFramePhaseLock(libcamera::Request *)` (`CC:7051-7131`): read `SensorTimestamp`; `enabled = settings_.fpsPhaseLock && !photoModeEnabled && fps > 1`; `recording = recordingFramesEnabled_`; at arm, take the gains from `APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US` (`CC:7064-7083`); call `step()`; on `rearmed` clear the pin and log `ApertarCore phase-lock: armed fps= nominal_us= ref=boottime kp= ki= deadband_us= clamp_us=`; on `servoRan` keep the error and compare the IPA's echoed `FrameDurationLimits` with the last four pins — a value never pinned means the IPA clamped it: `phase-lock: saturated echoed_us= requested_us=` once per arm (`CC:7105-7122`); on `pushDuration` set `phaseLockDurationUs_`; every 250 frames with `APERTAR_PHASE_LOCK_LOG=1` print `frames= err_us= dur_us= pushes=`.
- `phaseLockStatus()` (`CC:7133-7143`) returns `{active, errorUs, durationUs, pushes, saturated}` under `controlsMutex_`.
- call the step from `requestComplete` before `requeueRequest` (`CC:7303`).
- in `requeueRequest`, after the photo-mode merges and only when not photo-busy (`CC:7222-7236`): `request->controls().set(controls::FrameDurationLimits, {d, d})` and remember the pin in `recentPhaseLockPins_` (the in-flight depth). No `settings_` read here.
- release on `stop()` (`CC:6040-6041`) and when fps, the switch or photo mode changes in `applyControls` (`CC:6046-6050`); print `ApertarCore phase-lock stats: max_abs_err_us= duration_pushes=` in `stopRecording` (`CC:6207-6214`) and reset telemetry.

**4.4 The command and the telemetry** — `ApertarCoreApp.cpp`: `set_fps_phase_lock` with `enabled` (`App:9499-9508`), the help list entry, `fps_phase_lock` in both state JSONs (`App:203`, `:7917`); `CameraController::setFpsPhaseLock(bool)` and `phaseLockStatus()` (`CC:9422`); `/api/state` gains `fps_phase_lock_active`, `fps_phase_lock_err_us`, `fps_phase_lock_dur_us`, `fps_phase_lock_pushes`, `fps_phase_lock_saturated` next to `recording_has_dropped_frames` (`App:7857-7861`), so the switch is never shown without the number that would falsify it.

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

Prediction: one `armed fps=25 nominal_us=40000 ref=boottime kp=0.06 ki=0.0015 ...` line within a second; by `frames=250` (10 s; the simulator settles a +1066 ppm sensor in ~160 frames) `err_us` within ±15 and `dur_us` within 39990..40010 on the default helper, or alternating between two or three values 1–2 µs apart on the lattice; `pushes` ≈ 60 on the default helper, ≈ 10 on the lattice. Then:

```bash
curl -s localhost:8000/api/state | grep -o '"fps_phase_lock_[a-z_]*":[^,]*'
```

Prediction: `active:true`, `err_us` a few µs, `dur_us` the current pin, `saturated:false`. A `saturated` line in the journal means the pin hit the mode's limit (the fastest fps of a mode): the servo can only lengthen frames there — lower the fps one step.

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
| `phase-lock: saturated echoed_us=...` every arm | the pinned duration is at the mode's limit (its top fps): the servo can only lengthen frames | record one fps step below the mode maximum, or accept an open loop at the top rate |
| gains need a trial | `APERTAR_PHASE_LOCK_KP=0.04` etc. in the service environment, restart, re-arm | no rebuild; Cinemate kept the same knobs as live keys |
| you doubt the `settings_` reads on the completion thread | the critic (X6) audited only `applyControls` for holding `controlsMutex_` | `grep -n 'settings_ = ' src/camera/CameraController.cpp` and confirm each session writer runs with the camera stopped or under the unique `sessionSettingsMutex_`; the pin itself no longer reads settings |
| still captures take the servo's duration | pin merged before the photo block | the pin belongs after the photo merges (`CC:7263`) and `enabled` must exclude photo mode |

Undo: `set_fps_phase_lock enabled=false` (persisted). Full undo: `git checkout -- include/apertar/core/Types.hpp src/camera src/ApertarCoreApp.cpp`, rebuild.

## 8. What you learned, going further

- Two crystals, one clock to rule them: discipline the picture to the clock the audio is on, and the audio code does not move.
- The integer rounding *is* the dither; a deadband prevents control churn; a clamp bounds the damage.
- Exercise: expose `phaseLock_.maxAbsErrorUs` in `/api/state` next to `fps_phase_lock` so the switch is never shown without the number that would falsify it (Cinemate's `fps_actual` showed 24 for the life of the system, `b029d7f`).
- Going further: a `ApertarCore phase-lock saturated` line once per take when the request hits the clamp.

## 9. Sources

- `cinepi-raw/cinepi/phase_lock_core.hpp@63a08d5` (law), `tests/phase_lock_core_test.cpp` (behaviours), `cinepi_controller.cpp:733-737` (wall clock = audio clock); commits `bf717fa`, `85d0326`, `55562b6`, `d038556`, `e74e3e4`, `3b3ff60`, `4537153`, `5b4b209`, `28b30cc`, `3c6477e`; cinemate `0b8e947`, `2f79397`, `b029d7f`.
- `Apertar-Core@9e6df59`: `src/camera/FramePhaseLock.hpp` (`:26` status struct, `:35` tuning, `:79` step, `:90` gap, `:129` rounding); `CC:7051-7143`, `:7222-7236`, `:7303`, `:6040`, `:6046-6050`, `:6207-6214`, `:9422`; `App:203`, `:7857-7861`, `:7917`, `:9499`; `Types.hpp:127`. Critic items P1–P9 in `working/port-raw/critic.md`.
- `working/phaselock-answer.md`, `working/port-raw/p1-phaselock-cinemate.md`, `p2-phaselock-core.md`, `working/cinemate-lessons.md` §2–3, `working/tools/phase_lock_sim.cpp`.

%% tutor
ref core src/camera/FramePhaseLock.hpp 79 Decision step(bool enabled, bool recording, double fps, int64_t referenceNs)
ref core src/camera/FramePhaseLock.hpp 90 const bool bigGap = active && sincePrevious > static_cast<int64_t>(1.5 * periodNs);
ref core src/camera/FramePhaseLock.hpp 129 const int64_t durationUs = std::llround(requestedUs);
ref core src/camera/CameraController.cpp 7051 void stepFramePhaseLock(libcamera::Request *request)
ref core src/camera/CameraController.cpp 7078 t.proportional = env("APERTAR_PHASE_LOCK_KP", t.proportional);
ref core src/camera/CameraController.cpp 7119 std::cerr << "ApertarCore phase-lock: saturated echoed_us=" << echoedUs
ref core src/camera/CameraController.cpp 7133 PhaseLockStatus phaseLockStatus()
ref core src/camera/CameraController.cpp 7229 if (phaseLockDurationUs_ && !photoBusy) {
ref core src/camera/CameraController.cpp 7303 stepFramePhaseLock(request);
ref core src/camera/CameraController.cpp 6046 if (std::fabs(settings_.fps - sanitized.fps) > 1e-9 || settings_.fpsPhaseLock != sanitized.fpsPhaseLock ||
ref core src/camera/CameraController.cpp 6210 std::cerr << "ApertarCore phase-lock stats: max_abs_err_us=" << std::lround(phaseLock_.maxAbsErrorUs)
ref core src/camera/CameraController.cpp 9422 PhaseLockStatus CameraController::phaseLockStatus() const
ref core include/apertar/core/Types.hpp 127 bool fpsPhaseLock = false;
ref core src/ApertarCoreApp.cpp 7858 << ",\"fps_phase_lock_err_us\":" << jsonNumber(phaseLockStatus.errorUs, 1)
ref core src/ApertarCoreApp.cpp 9499 if (command.name == "set_fps_phase_lock") {
ref core src/audio/TimestampedAudioCapture.cpp 195 SND_PCM_TSTAMP_TYPE_MONOTONIC
check 3.0 | g++ -std=c++20 -O2 -I /home/pi/ApertarCore/src/camera /home/pi/apertar-kb/working/tools/phase_lock_sim.cpp -o /tmp/phase_lock_sim && /tmp/phase_lock_sim | tail -1 | ALL CHECKS PASSED
check 3.1 | grep -rc 'FrameWallClock' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^0$
check 4.1 | test -f /home/pi/ApertarCore/src/camera/FramePhaseLock.hpp && grep -c 'struct FramePhaseLock' /home/pi/ApertarCore/src/camera/FramePhaseLock.hpp | ^1$
check 4.2 | grep -c 'bool fpsPhaseLock' /home/pi/ApertarCore/include/apertar/core/Types.hpp | ^1$
check 4.3 | grep -c 'stepFramePhaseLock' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^2$
check 4.3b | grep -c 'phase-lock: saturated' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.4b | grep -c 'fps_phase_lock_err_us' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.4 | grep -c 'set_fps_phase_lock' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[2-9]$
check 5.1 | journalctl -u apertar-core -b --no-pager | grep -c 'phase-lock: armed' | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
