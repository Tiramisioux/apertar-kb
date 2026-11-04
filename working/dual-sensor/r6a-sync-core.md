<!-- Dual sensor, reader report 6a (2026-11-03/04): the phase-lock deep-dive, lens A: Apertar Core's FramePhaseLock, its integration in CameraController, what a shared grid and start alignment need. Written by a read-only research agent on the Mac (Core 31d5418, libcamera 6b0b49f3 / 7e9fef0b, driver cd548ef, cinepi-raw 63a08d5, KB). Its model sources are in sim/ (plsim/). Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Apertar Core frame-rate phase lock: what two-sensor sync needs (A1–A5)

**Main finding.** The phase lock as shipped can't line up two sensors. Each Core process locks to a grid that starts at its own first frame after arming, so two locked cameras keep a fixed offset of anywhere between 0 and 40 ms at 25 fps. The fix:
- **Lock:** each process steers to the nearest slot of one fixed grid on the shared clock.
- **Actuator:** the frame-length nudges must change VBLANK only, not HMAX.
- **Timing:** the lock must allow for the 7–11 frames before a nudge takes effect.
- **Take:** the record start and stop rule, the frame numbering and the timecode must come from that same grid.

**Legend.** Code refs are `path:line@sha`, with these abbreviations:
- Core `drop-frames` @31d5418: `FPL` = src/camera/FramePhaseLock.hpp, `CC` = src/camera/CameraController.cpp, `App` = src/ApertarCoreApp.cpp, `RC` = src/audio/RecordingClock.hpp, `CDNG` = src/cdng/CdngEncoder.cpp, `MLV` = src/mlv/MlvEncoder.cpp, `Types` = include/apertar/core/Types.hpp.
- `LC` = libcamera at apertar 6b0b49f3. Where marked @7e9fef0, that is the installed base; the `cam_helper*.cpp` files are identical between the two (`git diff --stat` is empty).
- `DRV` = imx585.c@cd548ef. This is `origin/cinemate-port`; the local branch named `cinemate-port` points at 24172e6.
- `CR` = cinepi-raw @63a08d5. `KB` = apertar-kb plain files.
- Labels: [C] confirmed, [P] probable, [U] unconfirmed. **M** = measured, **E** = estimate.

The E numbers come from a scratch model I wrote. It uses the shipped header (copied with `git show`), a 7.407 µs line (HMAX 550 at 74.25 MHz), the qbc lattice copied from the KB simulator, a VBLANK-only realisation (floor to lines, then VMAX rounded down to even), a dead time of D frames, and |N(0,σ)| interrupt-latency jitter.

## A1. FramePhaseLock.hpp (156 lines, last changed in 80ddac1)

| Item | Code | Behaviour | |
|---|---|---|---|
| Call | `FPL:79` `step(enabled, recording, fps, referenceNs)`, called at `CC:8812-8813` | `referenceNs` = `SensorTimestamp` ns of each completed request (`CC:8775`) | C |
| Reference clock | `FPL:21-24`, `CC:8770-8772`, log line `ref=boottime` `CC:8830` | Kernel `ktime_get_ns()` taken at CSI-2 frame start. This is CLOCK_MONOTONIC, which equals BOOTTIME on a Pi that never suspends. libcamera passes it through unchanged (`LC v4l2_videodevice.cpp:1899`, `LC pisp.cpp:2237-2240`). Core never reads `FrameWallClock` (grep: 0 hits) | C (the kernel line is from KB p2-phaselock-core.md:39; I did not re-read the kernel) |
| Period | `FPL:87` | `1e9/fps` as a double, from `settings_.fps`. It is not the rational rate from `RC:13-19` | C |
| Datum | `FPL:143-153` | At every (re)arm: `originNs` = that frame's own timestamp, `frames=0`, request = nominal, integral = 0, `lastPushed=-1`. Nothing is requested on the arm frame | C |
| **Error** | `FPL:106-108` | `e_us = ((ts − originNs) − frames·T)/1000`. e > 0 means the frame is late, so the next request is shorter | C |
| Grid type | `FPL:22-24` ("only differences are used, so the epoch does not matter"); the KB simulator's case 5 tests exactly this | **Anchored at arm time.** It is not an absolute grid and it has nothing to do with the "pin". Cinemate's lock is the same (datum `t0Ns`: `CR cinepi/phase_lock_core.hpp:104-105,120-125`) | C |
| Servo | `FPL:119-124` | If \|e\| > deadband: I = clamp(I+e, ±clamp/ki), then req = clamp(nominal − (kp·e + ki·I), nominal ± clamp). Otherwise the current request is held | C |
| Gains | `FPL:35-40` | kp 0.06, ki 0.0015 per frame, deadband 6 µs, clamp ±150 µs. The integral limit is ±1e5 µs·frame (ki·I ≤ 150 µs). No anti-windup beyond that clamp | C |
| Gains from env | `CC:8792-8810` | `APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US`, values > 0 only. The table is function-static, so it is read **once per process** at the first arm (the KB says "at arm") | C |
| Actuator | `FPL:127-139`; `CC:8854-8855`, `CC:8934-8952` | Whole-µs `FrameDurationLimits {d,d}`. It is set on every requeued request while a pin exists, after all other control merges, and is skipped while a still owns the exposure. The push counter rises only when d changes | C |
| Re-arm | `FPL:95-99`, `FPL:112-117` | First frame or enable; fps change > 1e-6; in preview, a gap > 1.5T or \|e\| > T/2 | C |
| Gaps while recording | `FPL:101-106` | slots = round(gap/T), frames += slots−1. No re-arm and no half-frame backstop | C |
| Release | `FPL:67-71`, `FPL:82-85` | When disabled or fps ≤ 1 | C |

**What the "pin" is.** A pin is the per-request min = max range `FrameDurationLimits {d,d}`.
- **Core's own pin** is the truncated `int64(1e6/fps)` that `controlsForSettings` sets (`CC:2404-2415`). The requests in flight at arm time carry it.
- **The 16-deep history** `recentPhaseLockPins_` (`CC:10235-10239`, commit 3a18db0) is seeded with Core's pin at arm (`CC:8821-8828`, commit 114bfb9). It is used **only** for saturation detection: an echoed `{x,x}` (`LC ipa_base.cpp:1795-1797@7e9fef0`) that matches none of the last 16 pins prints one `saturated` line per arm (`CC:8837-8852`).
- **Why 16:** requests in flight = raw buffers (`CC:1447-1461`). That is 4 in SDR or 8 in Clear HDR (`CC:1325`, `CC:1329`), +2 on exFAT (the Pi's NVMe), and at most 16 via env.

The pin plays no part in the error or the grid. [C]

**T27 numbers and loop delay.**
- **M** (all on the lattice libcamera, 4K Clear HDR 16-bit, 25 fps):
  - Preview with the lock on: \|e\| ≤ 22 µs over 5000 frames, a push every 9–10 frames (KB lessons/hardware-log.md:269-270).
  - 60 s take with the lock on: 10 holes, max_abs_err_us 199, 673 pushes, frame-to-frame band step up to 8.9 % (lock off: 0.28 %) (:281-288).
  - Delay from request to the first frame at the new period: 7 frames, measured at 1080p SDR on exFAT with N = 6 (:496).
- **E** (scratch model, shipped header, D = frames of dead time):
  - Lattice, D 7–11: max \|e\| 18–26 µs, with 3–4 different HMAX values. This matches the measured ±22 µs.
  - VBLANK-only (quantum of 2 lines = 14.8 µs): D=1 gives 23 µs. D=7–11 gives **62–116 µs**, with 110–325 pushes per 1000 frames.
  - The KB simulator applies each push to the next frame (D=1), so it under-states this.

## A2. Integration in CameraController

| Concern | Where | |
|---|---|---|
| Timestamp read and servo step | `stepFramePhaseLock` `CC:8770-8861`, on the completion thread, called at `CC:9047` before preview, photo and the record gate | C |
| Lock enabled when | `CC:8789-8790`: `fpsPhaseLock && !photoMode && fps > 1 && !inFpsRampGrace(ts)` | C |
| `recording` input | `recordingFramesEnabled_` (`CC:8778-8782`): the record gate, not the controller's `recording_` | C |
| Duration push | `requeueRequest` `CC:8934-8952`. The storage pre-roll pin is set **after** it and wins (`CC:8953-8958`) | C |
| fps change | `applyControls` `CC:7490-7496` releases the lock. `noteFpsChange` `CC:9647-9665` sets a grace of max(10, N+6) frames of the slower rate (`CC:9636-9645`). The first frame after the grace arms a **new datum** | C |
| T31 speed ramp | Each step goes through `applyFpsStepLocked(commit=false)` (`CC:10611-10658`), so it is released and given a grace. With steps closer together than the grace, the lock stays released for the whole ramp. `restoreFpsAfterRampLocked` (`CC:10663`) re-arms once more | C |
| Reconfigure | Clear HDR toggle (`CC:12559`), photo mode or colour profile (`CC:12557-12558`), ladder rung (`CC:10637-10655`), photo override at record start (`CC:7514-7515`). `stop()` releases (`CC:7400-7405`); the first frame after the restart arms | C |
| Clear HDR | 8 buffers (+2 on exFAT), so the dead time is about N+2 programmed / N+3 visible (`CC:9628-9633`). **E:** 11–12 frames. At the driver's maximum fps (31d5418) the lock can only lengthen frames (the saturated flag) | C / E |
| Storage pre-roll | fps override `CC:7475-7477` causes a re-arm at the maximum fps, but its pin overrides the lock. `stop()` clears it (`CC:7406`). It blocks `record_start` (`CC:11825-11828`) | C |
| Record start / stop | `CameraSession::startRecording` does not touch the lock, so the datum from preview carries into the take. Stop prints `phase-lock stats` and resets the telemetry (`CC:7678-7684`) | C |
| State | `PhaseLockStatus` `FPL:26-32` → `CC:8090-8100` → `CC:12470-12475` → `/api/state` fields `fps_phase_lock_active/_err_us/_dur_us/_pushes/_saturated` (`App:9266`, `App:9426-9430`). `err_us` goes stale after a release (`CC:8814-8819`). `active` means armed, not converged | C |
| Logs | armed `CC:8829-8832`, released `CC:8815-8816`, saturated `CC:8849-8850`, a trace every 250 frames with `APERTAR_PHASE_LOCK_LOG=1` (`CC:8856-8860`) | C |
| Command and persistence | `set_fps_phase_lock enabled=true\|1` (`App:12759-12766`, listed at `App:12496`) → `CC:11751-11757` → `applySettingsLocked(next,false)` with commit = true (hpp:174) → `persistSettingsLocked` (`CC:12621`, `CC:12627-12634`). File key `fps_phase_lock` (write `CC:967`, read `CC:882-883`) in `$XDG_CONFIG_HOME` or `~/.config/apertar-core/camera_settings.conf` (`CC:414-425`). One switch for every format profile (`CC:11222-11242`). Preset key `cameraFpsPhaseLock` (`App:13891-13892`), UI export (`App:7826`), settings JSON (`CC:227`, `App:352`, `App:9494`). Default off (`Types:138`). The WebUI (`src/web`) and Apertar-UI@c153c33 have no control for it (grep: 0 hits) | C |

## A3. What must change so two Core processes lock to one grid

**Shared clock and shared instant**

| Question | Answer | |
|---|---|---|
| One clock domain? | Yes. Both CFE interrupt handlers stamp with the same kernel clock, and libcamera adds no per-process transform (`LC pisp.cpp:2237-2240`). `FrameWallClock` *is* per process: one `ClockRecovery` per CameraData (`LC pipeline_base.h:181`), fitted from samples taken at each dequeue (`LC pisp.cpp:2236`, `LC clock_recovery.cpp:139-210`). Keep `SensorTimestamp`, which is the opposite of Cinemate's 5b4b209 | C |
| Same physical instant? | It is the frame-start packet of each sensor's own CSI port. For identical sensor, mode, link frequency and HMAX, the delay from internal V-sync to that packet should be the same on both | P |
| Breaks if | **HMAX differs.** The lattice turns 40001 µs into HMAX 581 instead of 550 (KB hardware-log.md:248-253), so the last row of a 2200-line frame is read **about 0.9 ms** later on one sensor (E). Also if the modes differ, or if auto-exposure gives different shutters (readout aligned, exposures not) | P / E |
| Timestamp error | Interrupt latency of each CFE; possibly serialised when both frame starts coincide | U. Settle: leader mode drives the XVS output (`DRV imx585.c:4096-4102`); put both XVS pins on a scope and compare with errA − errB |

**Per-process anchors (the Apertar equivalents of Cinemate's 94102f7 lesson)**

| Anchor | Code | Effect with two processes |
|---|---|---|
| Lock datum = the first frame after (re)arm | `FPL:143-153`, `FPL:95-99`, `FPL:112-117` | Constant skew, uniform in [0, T). **The main blocker** |
| Every release and re-arm path | `CC:7400-7405`, `CC:7490-7494`, `CC:8786-8790`, `CC:9647-9671` | Each fps, mode, pre-roll or ramp change re-randomises the phase independently in each process. An origin pushed in from outside would be lost at the next `arm()` |
| Start of take = "now" per process | `CC:7631`, `CC:7649` | Start slots differ by the command skew |
| Index 0 = the clip's own first frame | `CC:4639-4646`, `CC:4231-4232` | Indices match only with the same start slot |
| `RecordingClock` offset, sampled per take per process | `RC:36-41`, `CC:7520` | Differs by read jitter (no outlier guard), or by a clock step that falls between the two samples |
| First-frame anchors in ramp, MLV, H.264, ProRes | `CC:9349-9352`, `MLV:961-963`, `MLV:1098-1102`, `LibavH264EncoderPlugin.cpp:266-271`, `ProresEncoder.cpp:1387-1391` | Correct only with the same start slot and the same offset |
| Clip folder name and number | `CC:5132-5135`, `CC:7543` | `now()` per process; lowest free C#### on a shared root (race). DNG model and serial are identical for both cameras (`CC:4048-4062`) |

**Minimum change set (fits the current code)**
1. **`FPL` grid mode.**
   - Error to the *nearest slot*: `k = round((ts−origin)/T)`, `e = ts − origin − k·T` in exact integer ns, |e| ≤ T/2. Use int128 for rational periods.
   - Default origin **0 on CLOCK_BOOTTIME**.
   - Period from the rational `recordingFrameRate` (`RC:13-19`). Why: with an absolute origin, k is around 10⁶–10⁷, so a 1 ppm difference in T would be a phase disagreement of tens of ms.
   - In grid mode, `arm()` resets only the integral, the request and `lastPushed`, never the grid. Drop the gap counting and the half-frame backstop (`FPL:88-117`), since nearest-slot error doesn't need them.
   - Keep the arm-anchored path as the single-sensor default.
2. **Acquisition** (preview only). When \|e\| > ~1 ms, lengthen *one* request by `(−e) mod T` and hold the servo for D+2 frames. Never do this while recording: a stretched frame would be a hole in the take. Reset the integral, add anti-windup (conditional integration at the clamp), and add a `locked` state (\|e\| < L for M frames).
3. **Dead-time compensation.** Steer on the *predicted* arrival: e plus the sum, over the requests in flight, of (realised duration − T).
   - The realised durations come from a line-quantum model, which can be learned from the per-frame `FrameDuration` (`CC:10219-10227`).
   - The in-flight pins are in `recentPhaseLockPins_` (`CC:10238`).
   - Compensating with the *requested* values instead does not help (model).
4. **VBLANK-only actuator.**
   - The lattice runs only when min == max (`LC cam_helper_imx585.cpp:129-132@7e9fef0`). Pinning `{d, d+δ}` with δ ≥ 1 µs at `CC:8948` should send the request to the default `getBlanking`: HMAX stays at the mode minimum and frame length = floor(min/line) (`LC cam_helper.cpp:82-120@7e9fef0`).
   - The driver then rounds VMAX down to even (`DRV imx585.c:3510`), giving a 2-line step of 14.8 µs.
   - The saturation check would need adapting: today it requires the echo to have min == max (`CC:8842`).
   - [P] Settle with the T27 3.3 readback: pin {40001, 40002} at 4K Clear HDR 25 fps and check that hblank stays 0. The alternative is a patch on the libcamera fork.
5. **Both processes run the same servo.** No Cinemate-style client release (`CR phase_lock_core.hpp:72-80`).
6. **Telemetry.** Add `fps_phase_lock_slot`, `_locked`, `_origin_ns` and `_period`, and clear `err_us` on release. With a common grid, **skew = errA − errB** comes for free.

**Options for the common origin**

| Option | Changes | Trade-off |
|---|---|---|
| **G0: origin 0 on BOOTTIME** (recommended) | Points 1–6 only; the lock needs no IPC | Both sensors follow NTP slews. M: 40–80 ppm right after a correction (KB hardware-log.md:265-268). This is harmless once the actuator is VBLANK-only |
| Gp: origin sent by the primary | A runtime-only `origin_ns` on `set_fps_phase_lock` (not persisted, because BOOTTIME restarts at each boot) | The primary can place frames in the middle of a TC cell; adds IPC and state |
| L: leader / follower | The follower steers to the leader's published timestamps (shared memory); the leader free-runs | One actuator and no NTP chasing; needs IPC with latency handling |

**E (scratch model, 25 fps, VBLANK-only, D 7–11)**

| Case | Result |
|---|---|
| Pull-in from ±19 ms, shipped PI law on the grid | Below 1 ms after 4.7–5.3 s; overshoot **2.0–2.8 ms**; within 250 µs after 7.6–8.6 s |
| With anti-windup | Overshoot 0.4–0.9 ms |
| With the one-frame stretch | Within 250 µs after **D+4 frames (0.4–0.6 s)** |
| Steady state, with quantisation-aware compensation | ±20 µs (otherwise ±115 µs); ±35–52 µs at 42–83 ppm of slew |
| **Dual skew**, full design, crystals −1.5 to ±50 ppm | **max 39–57 µs, p99 34–45 µs** (σ 2–10 µs) |
| Dual skew, without compensation | max 160–200 µs |

## A4. Record start and stop alignment, numbering, timecode

**First frame today** [C]:
1. `record_start` runs (`App:14216-14308`). With audio on, it first broadcasts `prepare_recording` and sleeps 220 ms (`App:14297-14300`).
2. `CameraSession::startRecording` (`CC:7507-7650`) samples `RecordingClock` (`CC:7520`), reserves the clip folder (`CC:7543`), then starts audio and the writers.
3. The gate opens: `recordingStartBootUs_ = BOOTTIME now` and `waitingForRecordingCadence_ = true` (`CC:7631`, `CC:7649`).
4. In `requestComplete` (`CC:9064-9081`), the first frame recorded is the first with `ts/1000 ≥ recordingStartBootUs_` **and** a `FrameDuration` within max(500 µs, T/50) of nominal. Earlier frames are requeued.

**Where the "start at T" rule goes.** That gate already *is* "first frame with SensorTimestamp ≥ T". The bracketing pre-trigger uses the same pattern (`CC:8915-8919`, `CC:9422-9423`).
- Pass the primary's T through `record_start` → `CameraController::startRecording` (`CC:11815`) → `CameraSession::startRecording`, replacing "now" at `CC:7631` and `CC:7649`.
- Reply "late" if now > T − margin.
- Choose T = origin + (k + ½)·T on the common grid.
- Require both cameras `locked` and not in acquisition (a stretched frame fails the duration test).
- The margin must cover the slower process's setup [U: measure].

**Stop.** There is no rule today: the gate closes at once (`CC:7671`). The mirror rule: frames with ts ≥ T_stop are not recorded. Close the gate on the first such frame and make `stopRecording` wait for it (bounded) before the audio endpoint is fixed (`CC:7669-7670`).

**Numbering and timecode sources**

| Item | Source | Same on both clips only if |
|---|---|---|
| DNG file name, MLV VIDF frame number | `nextFrameIndex` = max(counter, llround((ts−ts0)·fps/1e6)) (`CC:4639-4646`, `CC:5138-5144`, `MLV:1007-1010`). Ramp takes count frames only (`CC:9334`) | Same start slot. In ramp takes, a drop shifts every later index |
| CDNG Time of Day TC (FreeRun) | Per frame: `ts_us + offset` (`CC:9261-9265`, `CC:9335`), frame = floor(fraction of second × fps) (`CDNG:400-417`, called at `CDNG:1511-1518`) | Same offset, and no TC-cell boundary between the two timestamps |
| CDNG Clip TC (RecRun) | `frameIndex` (`CDNG:382-397`) | Same start slot |
| MLV, H.264, ProRes TC | First frame's wall time (`MLV:1098-1102`, `RC:50-61`). MLV RecRun is always `00:00:00:00` (`RC:53`) | Same start slot and offset |

**Offset caveat** [P]. On Linux, NTP slews are frequency adjustments applied to the clock behind both MONOTONIC/BOOTTIME and REALTIME, so REALTIME − BOOTTIME only moves on clock steps. If so:
- The two processes' offsets agree to within read jitter.
- KB p2-phaselock-core.md:64 ("changes at the slew rate") is wrong.
- Settle: sample REALTIME − BOOTTIME every 10 s during an active slew.

Even so, the cell boundaries keep a fixed position relative to the grid for a whole boot. **E:** about 0.3 % of boots put frames within ±60 µs of a boundary, which gives repeated or skipped TC numbers and a one-frame offset between the cameras for every take on that boot.

**Fix.** Derive the index from the slot (k − k_start). Derive Time of Day TC from the *ideal* slot time plus **one** offset passed by the primary. Take clip names from a take id the primary sends, not from `now()`.

## A5. The KB simulator, working/tools/phase_lock_sim.cpp

**What it does.** It includes the shipped header (`:12`, build line `:3`) and has 21 checks.
- **Sensor models:** whole lines rounded up (`:21-30`; libcamera actually rounds *down*, `LC cam_helper.cpp:96`), plus the qbc lattice (`:74-112`).
- **Cases:** convergence from +1066 ppm and cold settle (`:127-164`), deadband (`:166-181`), gap policy (`:183-204`), re-arm, release and backstop (`:206-224`), epoch invariance (`:226-244`), lattice (`:246-276`).
- **Missing:** dead time (each push lands on the next frame, `:50-53`), timestamp jitter, NTP slew, the 2-line VBLANK step, and a second sensor.

**Can it do dual? Yes, if you add:**
1. Two sensors with their own crystal error (±1.5 to ±50 ppm) and a random start phase, on a shared clock with a common slew profile.
2. A request FIFO of D = N+1..N+2 frames (7 measured; 11–12 in Clear HDR).
3. A VBLANK model: floor, then even, 14.8 µs step.
4. Independent |N|-shaped interrupt jitter with outliers.
5. The grid lock variant: nearest slot, acquisition, anti-windup, dead-time compensation.
6. Metrics: true per-slot skew, pull-in time and overshoot, HMAX values per sensor, the start-slot check for T_start, and TC equality with per-process vs shared offsets.
7. **Case 5 inverted for grid mode:** an origin shifted by a fraction of a period must change the target.

My scratch files, ready to fold in, are in `/private/tmp/claude-502/-Users-patrikeriksson--claude-spares-spare-niESh6/f112d566-1876-4e08-9788-61e89e7de390/scratchpad/plsim/`: `dual_model.cpp`, `pullin2.cpp`, `deadtime_q.cpp`, `dual_comp.cpp` and the copied `FramePhaseLock.hpp`.

## Implications for dual-sensor sync
1. The shipped lock fixes each sensor's *rate*, not the *phase between sensors*. Two locked Cores keep a constant random skew of 0–40 ms at 25 fps, reset by every fps change, reconfigure, pre-roll or ramp [C].
2. **Lock:** nearest-slot error on origin 0 of CLOCK_BOOTTIME, with a rational period and a grid that survives every re-arm. This needs no IPC. Keep arm-anchored mode as the single-sensor default.
3. **Actuator first:** the lattice's HMAX changes cause flicker and drops (M) and about 0.9 ms of row-time mismatch between sensors (E). Try `{d, d+δ}` pins (no libcamera change) before patching the fork [P].
4. **Loop:** with D = 7–11 frames and a 14.8 µs step, the dead time needs predictive compensation, plus acquisition by one-frame stretch in preview only, plus anti-windup. Expected skew is under about 60 µs (E, scratch model).
5. **Reference:** stay on `SensorTimestamp`. Never use `FrameWallClock` (per-process fit). Both sensors will follow the same NTP slews.
6. **Take:** the primary sends T_start and T_stop at mid-slot into the existing gate (`CC:9068-9075`); both cameras must report `locked` first. Index and timecode come from the slot plus one shared offset. Each camera's clip name and DNG serial must say which camera it is (`CC:4048-4062`, `CC:5132-5135`).
7. **Rig rules:**
   - Identical mode, HMAX and manual exposure on both cameras.
   - fps below the mode's maximum (saturation).
   - Ramps are unsynced; the grid re-locks after them.
   - Every `set_*` and the lock switch mirrored to both processes (separate settings files, `CC:414-425`).
8. **Validate:** compare errA − errB with an XVS scope (leader mode drives XVS, `DRV imx585.c:4096-4102`).
9. **KB fixes needed:**
   - p2-phaselock-core.md:64 (REALTIME − BOOTTIME under slew) [P].
   - The gains are read once per process, not at every arm (`CC:8795`).
   - The simulator's dead-time-free model under-states the VBLANK-only limit cycle by about 5×.