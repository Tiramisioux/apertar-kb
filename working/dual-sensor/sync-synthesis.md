<!-- Dual sensor, sync synthesis (2026-11-04): the phase-lock sync design drawn from r6a, r6b and r6c by a synthesis agent, with its own model cross-check (now in sim/synth/; the scratchpad paths below are where it ran). Reviewed by sync-critique.md: three of its statements are refuted there (the restart-harmless claim, option (b) at 24 fps, the reason for never stretching in a take). Frozen: the corrected version is the sync chapter of design-dual-sensor.md. -->

# Dual-IMX585 frame sync by the phase lock: design (synthesis of A, B, C, 2026-11-04)

**Sources**

- **Code refs:**
  - Core `drop-frames`@31d5418: `FPL` = src/camera/FramePhaseLock.hpp, `CC` = src/camera/CameraController.cpp, `RC` = src/audio/RecordingClock.hpp, `App` = src/ApertarCoreApp.cpp.
  - libcamera `apertar`@6b0b49f3. 4cff971 is an ancestor; I checked this with `merge-base`.
  - `DRV` = imx585.c@cd548ef (origin/cinemate-port).
  - KB = the apertar-kb working tree.
- **Labels:** **C** = confirmed, **P** = probable, **U** = unconfirmed. **M** = measured, **E** = estimate.
- **Model:** my cross-check of the investigators' simulations. It uses:
  - the shipped PI law;
  - a dead time of D frames;
  - Gaussian frame-start jitter σ, quantised to 1 µs;
  - the 2-line VMAX quantum of 14.815 µs.

  The scripts are `grid_sim.py`, `dual_sim.py`, `more_sim.py` and `meas_sim.py` in `/private/tmp/claude-502/-Users-patrikeriksson--claude-spares-spare-niESh6/f112d566-1876-4e08-9788-61e89e7de390/scratchpad/synth/`. Every model number is E.

## 1 Verdict

**As shipped: no.**
- The phase error is measured from the first frame after arming: `originNs = referenceNs` (FPL:149), error at FPL:108.
- So two locked Cores share a rate, not a phase. Their offset is frozen at a random value in [0, T), 0–40 ms at 25 fps.
- The offset is re-drawn at every re-arm: an fps change (CC:7490-7496), stop or reconfigure, the ramp grace (CC:9647-9671). C.
- Cinemate's law is the same (phase_lock_core.hpp:104, :120-125@63a08d5; read by B). Removing its role gate would not help. C.

**Yes, with four changes, and the lock needs no messages between the processes:**
1. **Grid:** measure the error to the nearest slot of one absolute grid, k·T on CLOCK_BOOTTIME, origin 0, with T the exact rational from RC:13-19.
2. **VBLANK-only actuator:** pin `{d, d+1}` instead of `{d, d}` (CC:8948). This skips the qbc lattice (gate at cam_helper_imx585.cpp:130-132@6b0b49f3). C.
3. **Quantiser (Q):** an even-VMAX quantiser with error feedback in FPL.
4. **Driver fix (E):** rewrite SHR when VBLANK changes, and move the per-frame logs to `dev_dbg` (DRV:3506-3524). C.

**Accuracy (E, model, D = 7–11, σ = 3–10 µs)**

| Quantity | Max | p99 | RMS |
|---|---|---|---|
| One sensor, true phase error against the grid | 14–33 µs | — | 6–13 µs |
| Between the two sensors | 30–53 µs | 20–37 µs | 8–14 µs |

The between-sensor figure is 4–7 lines, or about 0.1 % of a 25 fps frame, and it does not grow with take length. Not included yet: a constant difference in interrupt latency between the two CFEs (U).

**Conditions**
- The same mode, link frequency and HMAX on both sensors (550 at 891 MHz).
- The same manual shutter on both.
- fps below the mode's maximum. Clear HDR at 30 fps can only lengthen frames, so it cannot lock.
- Settings mirrored to both Cores, and both `locked` before record.
- Speed ramps are not synchronised in v1.

### 1b Where the investigators disagreed

| Point | A | B | C | What I checked | Who was right |
|---|---|---|---|---|---|
| `{d,d+1}` bypasses the lattice | yes | listed as untested | yes | Gate at cam_helper_imx585.cpp:130-132. The base path floors to whole lines and takes hblank from `minLineLength` (cam_helper.cpp:96-121) | A and C. Confirmed in code; the hardware readback (1.1) is still to do |
| Residual of the shipped law with VBLANK-only steps | 62–116 µs | 104–134 µs; "retuning doesn't help" | 52–107 µs; 13–23 µs with Q | Model: plain floor 67–131 µs; floor + Q 18–33 µs at D 7–11 | All three are right about the plain staircase. **C is right that Q removes the limit cycle**, so B's conclusion that VBLANK-only is too coarse does not hold once Q is in. A's dead-time predictor gave no steady-state gain in the model. The in-flight sum it uses is still needed for acquisition (§2) |
| Skew between sensors, full design | max 39–57 µs | 211–231 µs (no Q) | ±45–100 µs (scaled) | Model: max 30–53 µs | A |
| Common grid or follower | grid | follower | grid | See §2 | A and C |
| REALTIME − BOOTTIME during an NTP slew | constant; KB p2-phaselock-core.md:64 is wrong | — | — | Linux applies the NTP frequency correction to the timekeeper behind both clocks; only MONOTONIC_RAW diverges | A (P; test 1.7 settles it) |
| "Sensor within 1.2–1.6 ppm of the Pi crystal" (KB hardware-log.md:260-267) | used | the logged endpoints (83→42 ppm vs 49→39 ppm) do not subtract to it | used | — | B. The figure is U |
| Dead time | 7–11; 11–12 in Clear HDR | 11–13 | 3–7 modelled | CC:9628-9635 says about N+2 / N+3. Measured `lag_frames=7` at N=6 (KB hardware-log.md:496), i.e. N+1 | D ≈ 11 for Clear HDR on exFAT, N=10 (E) |

## 2 Mechanism

**The grid**
- **Clock:** `SensorTimestamp`. The kernel takes it with `ktime_get_ns()` in each CFE frame-start interrupt (KB p2-phaselock-core.md:39). That is CLOCK_MONOTONIC, the same as BOOTTIME on a Pi that never suspends, and both processes read the same clock.
- **Not FrameWallClock:** libcamera fits one `ClockRecovery` per camera (pipeline_base.h:181@6b0b49f3). C.
- **Period:** (num, den) = `recordingFrameRate(fps)` (RC:13-19), so 25 gives 25000/1000 and 23.976 gives 24000/1001.
- **Slot and error:** k = round(ts·num / (10⁹·den)); slot time t_k = k·10⁹·den/num; e = ts − t_k, which lies in (−T/2, T/2].
- **Arithmetic:** use `__int128`, since ts·num reaches about 10²⁰. Do not use `1e9/fps` (FPL:87): at 23.976 fps it is 41.7 ns per frame off the rational period.
- **How the two Cores agree:** the same fps gives the same T, and the origin is 0 by definition. Only `set_fps` and the mode must be mirrored, through the relay planned in r2.
- **Why the origin is not centred on timecode cells:** that origin would depend on REALTIME, which can step. Timecode is handled in §4 instead.

**The three options**

| | (a) both Cores lock continuously to the grid | (b) align in preview, hold the duration in the take | (c) primary locks, secondary follows the primary's frame times |
|---|---|---|---|
| Messages between processes | none | none | a per-frame timestamp stream; Core has no outbound client today (r2 Q4) |
| Skew | bounded, 30–53 µs max (E) | about 30 µs at the start plus Δ·t, where Δ is the crystal difference between the modules (U) | With a locked primary: no better than (a), because the secondary sees the primary's dither D frames late (P). With a free-running primary (B's variant): about 1.4–1.6× smaller (E) |
| Pushes in a take | 8–25 % of frames at 25 fps; 75–93 % at 24 fps, from the 5624/5626 alternation. Each is ±2 lines and harmless after fix E (P) | none | on the secondary only |
| 24 fps | exact on average, at HMAX 550 | 5625 lines is odd, so a held value is 355 ppm off. That gives about 5 phantom index holes per 10 min (`nextFrameIndex`, CC:4639-4646) | needs one HMAX on both; a lattice primary at 625 next to a VBLANK-only secondary means a libcamera patch |
| Core restart | rejoins the same grid on its own | re-align in preview | a primary restart starts a new phase, and the secondary slews up to T/2 |
| Testable now with one sensor | fully: the error against the absolute grid is each sensor's share of the budget | partly | no |

**Recommendation: (a).** Keep (b) as a `hold` take policy for 25/30/50/60 fps, in case Part 1 shows a cost from VBLANK pushes.

**Dual rule: when two Cores run, both must run grid mode.**
- A Core that reconfigures stops and recreates its CameraManager (CC:7445-7457).
- `CameraSensorLegacy::init()` then writes HBLANK = minimum to *every* sensor it enumerates, including the other Core's streaming sensor (camera_sensor_legacy.cpp:176, :288-296@6b0b49f3). C.
- With HBLANK already 0 that write is a no-op (P: V4L2 skips unchanged values).
- With the lattice at 24 fps (HMAX 625) the same write is a 5 ms phase step on the other sensor (KB claim-check.md:37).

**Loop in grid mode**
- **Steady state:** the shipped PI unchanged (FPL:119-124): kp 0.06, ki 0.0015, deadband 6 µs, clamp 150 µs. A 15 µs deadband doubled the skew in the model.
- **Acquisition, in preview only:** while not locked and |e| > 1 ms:
  - lengthen one request by (−e − Σ over in-flight frames of (V_i·H − T)) mod T, rounded to an even VMAX;
  - then hold the servo for D+2 frames.

  In the model, |e| falls below 50 µs after 13 frames (0.5 s) at D = 11. The PI alone needs 230–260 frames, with 1.7–2.8 ms of overshoot (A, C).
- **Never stretch while recording.** The stretched frame would fail the FrameDuration test in the record gate (CC:9071-9073).
- **What changes in `arm()`:** it resets the integral, the request and `lastPushed`, never the grid. The gap counting and the half-frame re-arm (FPL:88-117) are no longer needed.
- **Additions:**
  - anti-windup by conditional integration;
  - a `locked` state: |e| ≤ 100 µs for 25 frames.

## 3 Actuator

**The problem**
- **Measured:** `{d,d}` (CC:8948) makes the helper re-choose HMAX. 40001 µs became 581 × 5112 instead of 550 × 5400 (KB hardware-log.md:246-258).
- **Measured:** take C0103, with the lock on, had 10 holes and a band step of up to 8.9 % (KB hardware-log.md:279-293).
- **Computed by C:** 299 of 300 one-µs steps change HMAX.
- **For dual:** each lock would pick its own HMAX, so row times differ by 1.5–5.6 ms at the bottom row (C, E). The foreign-HBLANK write from §2 adds to this.

| Fix | Where | Effect | Risk | Verdict |
|---|---|---|---|---|
| **E** (driver) | DRV:3506-3524: after :3516, write `shr = (vmax − current_exposure) & ~1U`. This is the formula of :3479, using the value clamped at :3512-3513. Move `dev_info` to `dev_dbg` at :3495, :3499, :3518, :3536 | Integration stays fixed when VMAX moves. Today the VBLANK case writes VMAX only, and `applyAGC` re-sends an unchanged EXPOSURE (ipa_base.cpp:1847-1848), which V4L2 skips (P). Each push therefore shifts exposure by 2 lines: 0.074 % at 20 ms, 1.5 % at 1 ms (C, E). At 24 fps that happens on every frame | DKMS rebuild; affects every user of the driver branch | **Prerequisite** |
| **A** (Core) | CC:8948 `{d, d+1}`. Pre-roll CC:8955 `{p, p+1}` (it overrides the lock pin). Saturation check CC:8841-8842: compare `echoed[0]` (today it requires [0] == [1]) | The base `getBlanking` takes frame = floor(min/line) and hblank from `minLineLength`, so HMAX stays at 550. No libcamera rebuild | A 14.8 µs staircase, so Q is needed. The lattice's exact-rate snap (:160-167) is lost while locked. HMAX switches once at arm and release, in preview (625↔550 at 24 fps) | **Yes** |
| **Q** (Core) | FPL:127-139: q = r + carry; V = 2·round(q / 2H); carry = q − V·H; push d = ceil((V + ½)·H) | Exact mean period. FrameDuration metadata (frameLength × line, ipa_base.cpp:1594-1595) becomes exact | Needs the line time H = (w + HBLANK) / PIXEL_RATE from this camera's own subdev, matched by of_node as at CC:8118-8130. The half-line offset matters: V·H is a whole µs when 27 divides V (5400 gives exactly 40000), so a pin on the boundary can floor to V−1 in double arithmetic (P) | **Yes** |
| B: libcamera "sticky HMAX" | cam_helper_imx585.cpp | Exact rates with the lock off at a fixed HMAX | `getBlanking` is const and called from 3 places | Later |
| C: environment opt-out at :130 | libcamera | — | Drops lock-off exactness for the whole process | Fallback |
| No pushes in a take | policy | 0 pushes | 25/30/50/60 fps only | Fallback, as (b) |

rpi.sync would run into the same lattice, because it calls `getBlanking(min − offset, max − offset)` (ipa_base.cpp:1836-1837). C.

## 4 Start/stop alignment and timecode

**Today (C)**
- The record gate opens at "now" (CC:7631, :7649).
- The first frame recorded is the first with ts ≥ that time and a FrameDuration within max(500 µs, T/50) (CC:9068-9075).
- Stop closes the gate immediately (CC:7671).
- The frame index is max(counter, llround((ts − ts0)·fps)) (CC:4639-4646).
- Timecode is ts plus an offset that each process samples once per take (CC:9261-9265; RC:36-41).

**Design**

| Step | Design |
|---|---|
| Choose the start | The coordinator (the primary's relay, r2) picks k0 = ceil((now + lead) / T). It sends `start_us = (k0 − ½)·T` as a string (flat protocol, r2 Q4). The lead is U: the primary sleeps 220 ms for audio (App:14286, :14299), plus the secondary's command path |
| `record_start start_us= take= tc_offset_us=` | Path: App:14216 → CC:11815 → CC:7507. Replace "now" at CC:7631 and :7649 with `start_us`. Each Core refuses if it is not `locked`, or if `start_us` has passed when its gate opens ("late"). Any refusal aborts the pair (r2 open question 8). Reply with `first_slot` |
| First frame | The existing test (CC:9072). The boundary sits mid-slot and \|e\| ≤ 50 µs, so both Cores record slot k0 first (P) |
| Stop | `record_stop stop_us = (k1 − ½)·T`. Frames with ts ≥ `stop_us` are not recorded. `stopRecording` waits up to 3T for the first such frame before CC:7671, so both clips hold exactly slots k0 to k1−1 |
| Index | No change. When locked, llround gives exactly k − k0, so a dropped frame leaves the same hole index in both clips (P) |
| Timecode | In grid mode, pass the slot time t_k (not ts) to `wallClockForSensorTimestamp` (CC:9261-9265), with the primary's `tc_offset_us`. That needs a `RecordingClock(offsetUs)` constructor next to RC:36-41. FreeRun timecode (floor at CdngEncoder.cpp:409) is then identical for each index on both clips, and jitter can never repeat or skip a number. The first-frame timecode in MLV, H.264 and ProRes works the same way |
| Clip names | The clip number comes from the primary, plus a `{cam}` literal; CC:1148 hard-codes "cam0" today (r2) |

## 5 Accuracy budget

All residuals below are E from the model. "Single" is one sensor's true phase error.

| Mode (891 MHz link) | Line time H | VBLANK step | D (frames) | Single max / RMS (µs) | Dual max / p99 / RMS (µs) | Readout |
|---|---|---|---|---|---|---|
| 4K SDR 12-bit 25 fps, exFAT (N=6) | 7.407 µs | 14.815 µs | 7 (M at 1080p) | 14–22 / 5–10 | 30–36 / 20–31 / 8–12 | 16.0 ms |
| 4K Clear HDR 16-bit 25 fps (N=10) | 7.407 µs | 14.815 µs | ≈11 (E) | 18–33 / 8–13 | 40–53 / 26–37 / 10–14 | ≈32.6 ms (P) |
| 24 fps (Q alternates 5624/5626) | 7.407 µs | 14.815 µs | 7–11 | 18–24 / 6–8 | 27–41 / 19–28 / 8–11 | — |
| 50 fps SDR | 7.407 µs | 14.815 µs | 7 | 21–23 / 7–8 | 35–38 / 24–26 / 10 | 16.0 ms |
| Clear HDR 30 fps (the mode's maximum) | — | — | — | saturates (CC:8837-8852) | no sync | — |
| 720 MHz link | 8.889 µs | 17.78 µs | — | about 1.2× (E) | about 1.2× | — |

**Measured references**
- The lattice lock held ±22 µs in preview.
- In a take it reached 199 µs, with drops (KB hardware-log.md:268-286).
- Cinemate's "±12 µs" is per-frame duration dither, not a phase bound (B).

**Drift over 1 / 10 / 30 minutes**
- **(a):** nothing accumulates; the bound is the same at every length. In the model, a 45 ppm NTP slew left the skew unchanged and raised pushes to about 25 % of frames.
- **(b), or no sync:** Δ·t.

| Δ | 1 min | 10 min | 30 min |
|---|---|---|---|
| 1.5 ppm | 0.09 ms | 0.9 ms | 2.7 ms |
| 10 ppm | 0.6 ms | 6 ms | 18 ms |
| 30 ppm | 1.8 ms | 18 ms | 54 ms |

**What the skew means for the rolling shutter**
- With equal HMAX, every row of one sensor is offset from the same row of the other by the same s.
- At 50 µs that is:
  - 6.75 lines, or about 3.4 Clear HDR rows (2 lines per row, P);
  - 0.125 % of a frame;
  - 99.75 % exposure overlap at 1/50 s;
  - 0.19 px for a pan of one frame width per second.
- Unequal HMAX (the lattice) breaks this row by row.

**Not in the budget yet**
- The CFE interrupt-latency difference and its jitter (U).
- 1 µs timestamp quantisation (v4l2_videodevice.cpp:1899-1900, per C).

## 6 Interactions

| Event | Grid design |
|---|---|
| fps change (mirrored to both) | Release, then a grace of max(10, N+6) frames (CC:7490-7496, :9636-9645), then arm on the new grid and stretch in preview (about 0.5 s). Both Cores land on the same new grid without messages |
| T31 speed ramp | The lock is released through the ramp (grace per step). The steps are not tied to slots, so the two ramps are not aligned. In a take, only PI pull-in follows (no stretch): 5–10 s with about 2 ms overshoot. v1: a ramp is an unsynchronised segment. v2: ramp steps tied to slots, ending on the grid. Ramp pins are still `{d,d}` and hop HMAX; that is a T31 issue |
| Clear HDR | 8 buffers, +2 on exFAT (CC:1325-1329, :1449-1461), so D ≈ 11. 30 fps cannot lock |
| Reconfigure (HDR toggle, format, colour profile, ladder rung) | The stream restarts with a random phase and re-acquires. `locked` stays false meanwhile, so record start is refused. Mirror the resulting state, not the command (KB claim-check.md:267-268) |
| Mode ladder | Each process has its own `mode_ladder.conf` (r2), so the two can end up in different modes with different readout skew. In dual: pin the rung, or mirror the primary's |
| Stills | Photo mode releases the lock (CC:8789). A still in video mode skips the pin (CC:8937-8947); the lock re-acquires afterwards. Stills are not synchronised |
| Storage pre-roll | Primary only (r2), with `{p, p+1}` |
| Core restart mid-shoot | The restarted Core re-acquires the same grid on its own, in about 1.5 s (E). Its enumeration write of HBLANK is harmless because the other sensor runs HBLANK 0. The timecode offset and clip number come from the primary at the next take |
| Audio | Unchanged. Everything is on BOOTTIME (KB p2-phaselock-core.md:45, :110), and video now follows BOOTTIME exactly |
| NTP | A slew affects both locks equally. A step only moves REALTIME, which matters only for the one timecode offset per take |

## 7 Verification on the Pi

**Part 1, one sensor (now)**

Conditions match C0102/C0103: 4K Clear HDR 16-bit, 25 fps, ISO 800, 20000 µs, 4000 K, static scene. First add a per-frame `slot ts err V` trace to `APERTAR_PHASE_LOCK_LOG` (CC:8856).

| # | Test | Prediction | Settles |
|---|---|---|---|
| 1.1 | Grid lock as a meter (`APERTAR_PHASE_LOCK_DEADBAND_US=100000`). Read `v4l2-ctl --get-ctrl=horizontal_blanking,vertical_blanking` after `sleep 1`, at 25 fps and at 24.99 fps | hblank 0. vblank 3200 at 25 fps; 3202 or 3204 at 24.99 fps. The lattice gave 217/2912 and 308/2802 (M) | Fix A |
| 1.2 | Lock off, fixed pin: the spread of SensorTimestamp intervals. Then push one step and count frames until the period changes | σ a few µs (U); D = 11 | The model's σ and D |
| 1.3 | 24 fps, lock on, 1 ms shutter, centre band; `dmesg \| grep -c imx585` per take | Before E: alternating steps of about 1.5 %, and one log line per push. After E: under 0.1 %, and about 0 lines | Fix E |
| 1.4 | 60 s take with the lock off, then a 60 s take with the grid lock on (E + A + Q) | No holes in either take. Band step with the lock on about the same as off (mean about 0.02 %, max ≤ 0.3 %). hblank 0 throughout. VMAX changes on 8–25 % of frames. Measured \|e\| against the absolute grid: max ≤ 40 µs, p99 ≤ 25 µs, RMS about 10 µs | Any holes: switch to the `hold` policy. \|e\| more than 2× the prediction: re-measure D and σ |
| 1.5 | Acquisition: toggle the lock, and go 25 → 24 → 25 fps in preview | \|e\| under 50 µs within about 13 frames | The stretch |
| 1.6 | 10-minute take (T27 step 5.2, never run) | \|e\| does not grow; 0 holes; WAV length = frame count | Long takes |
| 1.7 | During a timesyncd slew, every 10 s sample REALTIME − BOOTTIME and BOOTTIME − RAW | The first stays constant to ±2 µs; the second moves at the slew rate | The KB p2:64 dispute |
| 1.8 | Restart Core and let it re-lock | The same \|e\| bounds, on the same absolute grid | Rejoining without messages |

**Part 2, two sensors**

| # | Test | Prediction |
|---|---|---|
| 2.1 | Both locks off, 10 minutes, per-frame ts from both Cores | s_k = tsA − tsB drifts linearly at Δ ppm, with \|Δ\| ≤ 50 ppm (E). Δ decides whether option (b) is usable |
| 2.2 | Both on the grid lock; pair frames by slot k = round(ts/T) | Histogram of s_k: max ≤ 55 µs, p99 ≤ 40 µs, RMS ≤ 15 µs. The median equals the CFE bias b (U; expect \|b\| < 10 µs). Flat over 30 minutes. hblank 0 on both |
| 2.3 | A take with `start_us` and `stop_us` | Both clips: the same first slot, the same frame count, and the same timecode at each index |
| 2.4 | Restart cam1's Core during preview | cam0 shows no phase step and hblank stays 0; cam1 is locked within about 1.5 s |
| 2.5 | Optional: put a scope on both XVS lines (the leader drives XVS, DRV:4097-4102) | Agrees with s_k to within the CFE jitter |

## 8 Alternatives

| Alternative | What it needs | Accuracy | Prefer it when |
|---|---|---|---|
| libcamera `rpi.sync` | Several things, none present: an `rpi.sync` tuning block (none: r5-pi-hardware.md:26, :31); a multicast route (`lo` has no MULTICAST, and there is no route without eth0: r5:30, :68). It also brings drawbacks: it references the per-process FrameWallClock (sync.cpp:167); it makes one-frame corrections of ≥ 50 µs (sync.cpp:53, :259-274) that go through the lattice with `{d,d}`, or log an error every frame with `{d,d+1}` (ipa_base.cpp:546-548); and the client must release Core's lock | a ±50 µs band, phase only | Never on this rig |
| Hardware XVS: cam1 internal-follower (DRV:4089-4096), cam0 leader (the overlay default) | XVS wired between the modules. Whether the Waveshare board routes it is U. Never wire two leaders together (KB claim-check.md:119). How the follower handles VMAX is U; the datasheet settles it | under one line (E) | Row-exact stereo or 3D, or if test 2.2 shows CFE jitter above about 50 µs. The Core lock then runs on the leader only |
| No sync, aligned at start | Grid acquisition in preview, lock off during the take | about 30 µs at start, plus Δ·t | Δ ≤ about 3 ppm and takes ≤ 10 min (≤ 1.8 ms). Seamless only at 25/30/50/60 fps |

## 9 Code changes, smallest first

1. **Driver, DRV imx585.c@cd548ef:** `dev_info` → `dev_dbg` at :3495, :3499, :3518 and :3536. Four lines.
2. **Driver, VBLANK case (:3506-3524):** write SHR after :3516, mirroring :3479-3486. About 6 lines. Patrik runs the DKMS rebuild.
3. **Core pins (CC:8948, :8955):**
   - Pin `{d, d+1}` and `{p, p+1}` in grid mode.
   - In the saturation check (CC:8841-8842), match `echoed[0]` against `recentPhaseLockPins_` (CC:10238).
4. **FramePhaseLock.hpp (pure header):**
   - Add `Tuning::grid` and a `lineNs` argument to `step()` (FPL:79).
   - Rational grid error in `__int128`; `arm()` keeps the grid.
   - Q with a `carryUs` member, plus a `std::array<int32_t,16>` of in-flight VMAX values for the stretch.
   - New fields: `Decision::{stretchUs, frameLines}` and `PhaseLockStatus::{locked, slot}`.
   - Conditional-integration anti-windup.
   - With grid mode off, the code path stays bit-identical, so the KB simulator's 21 checks must still pass.
5. **`stepFramePhaseLock` (CC:8773-8861):**
   - Read `lineNs` from the camera's own subdev: PIXEL_RATE via `VIDIOC_G_EXT_CTRLS`, plus HBLANK, matched by of_node as at CC:8118-8130.
   - Stretch only when not recording.
   - Clear `lastPhaseErrorUs_` on release (CC:8814-8819).
   - Add the per-frame trace.
6. **Settings:**
   - A new key `fps_phase_lock_grid` next to `fps_phase_lock` (read CC:882-883, write :967, default next to Types.hpp:138).
   - `set_fps_phase_lock enabled= grid=` (App:12759-12766).
   - State fields `fps_phase_lock_locked` and `_slot`, added in all four serialisers (r2 Q4).
7. **Record path:** `start_us`, `take`, `tc_offset_us`, `stop_us` and `first_slot` as in §4. Touch points: App:14216, :14377; CC:11815, :7507, :7631, :7649, :7664-7671, :9261-9265; RC:36-41. Add `slot0` and `slots` to the stop stats line (CC:7680-7682).
8. **KB simulator, working/tools/phase_lock_sim.cpp:** add the dead time, jitter, the 2-line step, Q, a grid case (case 5 inverted) and a two-sensor pair.
9. **libcamera fork:** nothing for v1. Option B (sticky HMAX) only if exact lock-off rates at a fixed HMAX are wanted later.

## 10 Open questions for Patrik

1. What tolerance do you need: about 100 µs (software grid), or row-exact (XVS wiring)?
2. Take policy: `track` (pushes during takes, the default) or `hold` (no pushes, 25/30/50/60 fps only)?
3. Is it OK to change the driver (fix E) on Apertar's imx585 branch, with you running the DKMS rebuild?
4. Speed ramps in dual takes: allowed but unsynchronised (v1), forbidden, or tied to slots (v2)?
5. Dual Clear HDR at 30 fps cannot lock. Accept that, or limit dual Clear HDR to 25 fps?
6. Mode ladder in dual: pinned to one rung, or mirrored from the primary?
7. Is XVS routed on the Waveshare Mini Base Board A and on the IMX585 modules?
8. Timecode would come from the grid slot, which sits a constant fraction of a frame off true wall time for each boot. Does that suit the apertar-sync time-of-day workflow?
9. Who picks `start_us`: the primary Core's relay, or the UI talking to both sockets (r2 open question 9)?
10. Is timesyncd running on shoots? It does not hurt sync, but it raises the push rate during slews.