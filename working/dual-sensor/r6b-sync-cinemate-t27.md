<!-- Dual sensor, reader report 6b (2026-11-03/04): the phase-lock deep-dive, lens B: Cinemate's phase lock (cinepi-raw phase_lock_core.hpp), the KB's T27 record and an accuracy budget. Written by a read-only research agent on the Mac (cinepi-raw 63a08d5, Cinemate libcamera bfe0b76a, libcamera 6b0b49f3, driver cd548ef, Core 31d5418, cinemate d6cc93e, KB). Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Dual-sensor sync, lens B: Cinemate's phase lock and the T27 record (read-only, 2026-11-03)

**How I read the sources.** I read every ref with `git show` and `git grep`, and the KB and Obsidian files as plain files.

| Ref | Branch / role |
|---|---|
| cinepi-raw `63a08d5` | dev |
| Cinemate libcamera `bfe0b76a` | cinemate |
| Apertar libcamera `6b0b49f3` | apertar. It contains `7e9fef0` and `4cff971`: both `merge-base --is-ancestor` checks are true |
| driver `cd548ef` | cinemate-port |
| Apertar-Core `31d5418` | drop-frames |
| cinemate `d6cc93e` | — |
| handbook `c99ff77` | — |

**Labels.**
- **CONFIRMED**: seen in code, a log or a commit body.
- **PROBABLE**: inferred; the reason is given.
- **UNCONFIRMED**: not settled; I say what would settle it.
- **MEASURED**: a number from the KB or a commit body.
- **ESTIMATE**: my arithmetic or a scratch host simulation (sources listed at the end of B4).

---

## B1 Cinemate's lock (`cinepi/phase_lock_core.hpp`, read whole, plus `cinepi_controller.cpp`, @63a08d5)

| Item | What the code does | Cite | Label |
|---|---|---|---|
| Call site | Last step of `process()`, once per completed request, on the capture thread: `updatePhaseLock(epoch_ns, fps_user)` | cinepi_controller.cpp:733-737@63a08d5 | CONFIRMED |
| Reference clock | `FrameWallClock` (µs since epoch on this fork) ×1000. Fallback: `SensorTimestamp` (BOOTTIME) plus one cached REALTIME−BOOTTIME offset (fix 94102f7) | cinepi_controller.cpp:589-625@63a08d5 | CONFIRMED |
| Where FrameWallClock comes from | A per-camera `ClockRecovery` least-squares fit from BOOTTIME to REALTIME, so **one model per process**. Apertar's fork has the same structure | p1 §2 (clock_recovery.cpp:139-228, pisp.cpp:1752-1757@bfe0b76); pipeline_base.h:181, pisp.cpp:2236-2241@6b0b49f3 | CONFIRMED |
| **Error definition** | `phaseErrUs = ((ref − t0Ns) − frameCount·1e9/targetFps)·1e-3`. `t0Ns` is the reference timestamp of **the frame that armed the lock**. Positive means late (sensor slow), so the duration is shortened | phase_lock_core.hpp:120-125, t0 set at :104 and :133@63a08d5 | CONFIRMED |
| Absolute grid? | **No. The error is relative to an anchor.** The epoch enters only through int64 differences. A test asserts that an epoch-scale trace equals a boot-relative trace | :122-123; tests/phase_lock_core_test.cpp:142-168@63a08d5 | CONFIRMED |
| Control law | PI, applied only when \|e\| > deadband: `I += e`; anti-windup \|I\| ≤ clamp/ki (= 100 000 µs·frame); `req = base − (kp·e + ki·I)`; `req` clamped to base ±150 µs. Inside the deadband the request is **held**, not reset | :141-150@63a08d5 | CONFIRMED |
| Gains | kp 0.06, ki 0.0015, deadband 6 µs (all three tunable via Redis). Clamp 150 µs is compile-time. That gives ±3750 ppm pull range and at most 3.75 ms/s of phase slew at 25 fps | :27-32; cinepi_state.hpp:56-59@63a08d5 | CONFIRMED (the ppm and slew figures are arithmetic) |
| Output | `durUs = lround(req)`. `FrameDurationLimits {d,d}` is pushed **only when the integer changes**. `SetControls` is one-shot: the pending list is moved onto the next requeued request | :152-162; cinepi_controller.cpp:1242-1250; core/rpicam_app.cpp:1022-1027@63a08d5 | CONFIRMED |
| Nominal | `baseDurUs = 1e6/fps_user`, kept fractional (41666.67 at 24 fps). The `fps` handler's own pin is truncated: `long(1e6/fps)` | :101; cinepi_controller.cpp:968-980@63a08d5 | CONFIRMED |
| **How VBLANK-only is achieved** | **On the libcamera side, not by a cinepi-raw rule.** cinepi-raw only pins min = max. The Cinemate fork's stock `CamHelper::getBlanking` holds the line at `mode_.minLineLength` and stretches HMAX only if `frameLengthLines > maxFrameLength`, which never happens within ±150 µs of a normal fps. That fork has no IMX585 getBlanking override, and never had one in its lineage (p1 verification #18). Exposure stays put because cinepi-raw defaults to manual exposure and gain | cam_helper.cpp:82-132, stretch at :114-118@bfe0b76a; grep finds overrides only for imx477/519/500/708; core/rpicam_app.cpp:825-828@63a08d5 | CONFIRMED |
| Why VBLANK-only was chosen | bf717fa: "so the 4K static failure mode of the getBlanking HMAX-stretch patch cannot recur". The patch itself is not identifiable here: `97f71626` and `ea5abb8b` are objects in neither local fork | bf717fa body | CONFIRMED (the quote) / UNCONFIRMED (which patch) |
| Re-arm (new datum, no servo, no push) | (1) First enabled frame, or the first frame after a release. (2) \|fps_user − target\| > 1e-6. (3) In **preview**, a gap > 1.5 periods. (4) In **preview**, \|e\| > half a frame. A release (disabled, client role, or target ≤ 1 fps) also clears `lastTsNs` | :72-111, :127-139@63a08d5 | CONFIRMED |
| Gaps while recording | A gap > 1.5 P adds round(dt/P) − 1 to `frameCount`, so the datum is kept. A large error is tracked, never reset | :113-118, :127-130@63a08d5 | CONFIRMED |
| Why the gap rules look like this | e74e3e4: a 186 ms stall leaked into the accumulator and took 54 s to bleed off. 3b3ff60: takes started −90 ms behind. 4537153: −169 ms | commit bodies | CONFIRMED |
| Role gate | `roleClient = (options_->sync == 2)` (off=0, server=1, client=2). The step then releases on every frame and never pushes | cinepi_controller.cpp:1237-1240; core/video_options.hpp:244-251; phase_lock_core.hpp:75-80@63a08d5 | CONFIRMED |
| Telemetry | Redis `pll_phase_err_us` (rounded) and `pll_req_dur_us`, SET on every servo frame. **Not per camera**, unlike `timestamp_camN` and `tc_camN`. Nothing in Cinemate reads them | cinepi_controller.cpp:1252-1263 vs :651-653, :676@63a08d5; p1 §6 | CONFIRMED |
| Keys and CLI | `fps_phase_lock` (one shared key), `pll_kp`, `pll_ki`, `pll_deadband_us`, live via `cp_controls`. `--phase-lock` wins at start. `fps_user` and `is_recording` are fetched every frame | cinepi_controller.cpp:400-424, :697-698, :982-996@63a08d5 | CONFIRMED |
| Hardware result | imx585 mode0, 25 fps: "+1066 ppm uncorrected -> -9 ppm … ~2-3 line dither (+/-12us duration, ~0.03% exposure variation), 0 drops, phase error centered at 0". The earlier pure-integral law "railing the clamp (+/-150us) and swinging VBLANK +/-15 lines" | 55562b6, 85d0326 bodies | MEASURED (commit) |
| What the tests model | Quantiser `lround(d/line)`, with the request realised **on the next frame**, i.e. **zero loop latency**. The KB's `phase_lock_sim.cpp` makes the same assumption | tests/phase_lock_core_test.cpp:46-56, :67-90@63a08d5 | CONFIRMED |

## B2 Gate removed, both processes locked: same grid or only the same frequency?

**Answer: only the same frequency. The phase offset between the sensors is arbitrary and then frozen.**

Each process drives its own sensor onto t0ᵢ + k·P, where t0ᵢ is that sensor's own frame at arm time. So tB − tA → (t0B − t0A) mod P, plus the residuals. Nothing in the law couples the two processes, snaps t0 to a grid, or exchanges t0 between them. CONFIRMED by the algebra of phase_lock_core.hpp:104, :120-125, :133@63a08d5.

| Point | Detail | Label |
|---|---|---|
| Size of the offset | Whatever the free-running streams had at arm. Both processes get the same `fps_phase_lock` publish, but each arms on its own next frame. So the offset lies anywhere within ±P/2 (±20 ms at 25 fps) | Mechanism CONFIRMED; spread PROBABLE (stream start times are uncorrelated) |
| What re-randomises it | A mode reconfigure restarts each stream, and the preview re-arm then freezes the new offset. An fps change re-arms each process on its own frame | PROBABLE |
| Do the two clocks agree? | Both are REALTIME, but through two separate ClockRecovery fits. The disagreement should be µs-scale, small next to the ms-scale offset | PROBABLE. UNCONFIRMED magnitude: log FrameWallClock − SensorTimestamp in both processes |
| Side effect | Both processes write the global `pll_*` keys, so the last writer wins | CONFIRMED |

**What the history says.**

| Source | Text | What it means |
|---|---|---|
| 5b4b209 (2026-06-15) | "the single absolute frame-rate disciplinarian"; "rpi.sync owns that sensor's VBLANK for the relative A->B genlock"; "The server free-runs at FrameDurationLimits and only broadcasts" | The design gives the **rate** to the lock and the **phase** to rpi.sync |
| phase_lock_core.hpp:72-74; cinepi_controller.hpp:108-115@63a08d5 | "relative A->B genlock" vs "absolute Pi-clock discipline" | Same split |
| 6885431 README | "the residual is a bounded sub-frame offset, not an accumulating drift" | Bounded, not zero |
| 0caa9a5 | The client gate stops two controllers fighting over one VBLANK | About conflict, not phase |
| 94102f7 "hardware-synced sensors"; c19e316 "stays genlocked" | Claims of sync | Not supported by the code (r1 Q5) |
| cinemate 0b8e9478, then 4ada7533 / 8e5d940d | "Leave it off on … genlock rigs", then "safe to leave true" | Role-gate rationale only |
| Every source I searched | None says whether two locks would line up in phase | CONFIRMED absence (cinepi-raw log and README, handbook, cinemate docs and log) |

**The relative scheme Cinemate relied on never ran.**
- rpi.sync's client error is its own frame minus the server's frame, rounded to the nearest period. The client corrects one frame when the error is ≥ 50 µs. That aligns the client to the server's grid (sync.cpp:256-274, defaults :49-63@6b0b49f3).
- In Cinemate it never engaged: `CinePIRecorder : RPiCamApp` (cinepi_recorder.hpp:30@63a08d5). `SyncMode` is set only in `RPiCamEncoder` (core/rpicam_encoder.hpp:35-55@63a08d5), and the imx585 tuning has no `rpi.sync` block (r1 Q5).
- In Apertar: `SyncMode` and `SyncReady` have 0 hits in Core @31d5418, and the tuning files have no `rpi.sync` block (r5). CONFIRMED.

**What this did to Cinemate's shipped dual rig (PROBABLE).** cam0 is locked to nominal while cam1 free-runs at the uncorrected quantised rate. The relative drift is then that mode's uncorrected error: at +1066 ppm (mode0, 25 fps) that is about 1.07 ms/s, one frame every ~37 s, 16 frames per 10-minute take.
- Why I think so: the 1066 ppm is far beyond crystal tolerance, so it is quantisation, which is identical on both sensors. Before 2f79397 the static correction factor rode the shared `fps` key to both sensors.
- To settle it: compare `timestamp_cam0` and `timestamp_cam1` over one take with phase_lock on and one with it off.

## B3 The KB's T27 record

**What was measured** (2026-10-26; 4K Clear HDR 16-bit, 25 fps; system libcamera `7e9fef0`, which contains `4cff971`):

| Time / build | Test | Result | Source |
|---|---|---|---|
| 21:58, no lock, Core pin 40000 | C0101, 10 min | 15019 frames, 0 holes, 0 dropped, WAV = 15019 frames. So the cadence is within ±33 ppm of 25.000 against BOOTTIME. Audio crystal −15.7 ppm | tutorials/progress/T27.md |
| 22:00, 4ab1057 | HMAX hazard readback | 40000 µs → hblank/vblank 0/3200 (HMAX 550 × VMAX 5400). 40001 → 217/2912 (581 × 5112). 40016 → 308/2802 (594 × 5002): the line gets up to 8 % longer | hardware-log.md:246-258 |
| 22:05-22:09, 80ddac1 → 114bfb9 | Lock on, preview | ±9 µs over 1000 frames (duration 40002-40004, ~65 pushes). Then ±22 µs over 5000 frames, duration 40000-40002 (mostly 40002), one push per 9-10 frames, each one an HMAX switch. A false "saturated" flag was fixed (3a18db0, 114bfb9) | T27.md; hardware-log.md:268-273 |
| 22:10-22:14 | Lock as a meter (deadband 100000), plus BOOTTIME − MONOTONIC_RAW sampled every 10 s | Against BOOTTIME 83 → 42 ppm. BOOTTIME vs RAW 49 → 39 ppm (adjtimex in PLL mode slewing 12.8 ms; timesyncd last offset +22 ms, freq +3.17 ppm). **Sensor vs the raw crystal: 1.2-1.6 ppm, steady, sensor slow** | hardware-log.md:260-277 |
| 22:17 C0102 (off), 22:18 C0103 (on) | 60 s takes; centre band, rows 1040-1104 | Off: 1490 frames, 0 holes, frame-to-frame band step mean 0.017 %, p99 0.058 %, max 0.28 %. On: 1478 frames, **10 holes** (one 80 ms gap), WAV 1488 frames, `max_abs_err_us=199`, 673 pushes, step mean 0.53 %, p99 2.85 %, **max 8.9 %** | hardware-log.md:279-293 |

**A number that does not add up.** The endpoint pairs 83/49 and 42/39 do not subtract to 1.2-1.6 ppm, and the raw series is not in the KB. UNCONFIRMED how 1.2-1.6 was derived. To settle it, re-run the meter with both series logged on one time base.

**Explanations the KB confirmed:**
- The large drift was timesyncd slewing BOOTTIME, not the sensor.
- On the lattice libcamera the lock harms the picture: its pushes change HMAX, the helper's exposure re-fit does not hold the level, and period changes cost frames.

**What the KB rates PROBABLE:** drops kick the phase error, so the servo pushes more; and at 25 fps the sensor needs no lock for A/V.

**Not established: why the re-fit fails to hold the level.** My candidate (UNCONFIRMED):
- VBLANK goes out as a priority write, separate from EXPOSURE and HBLANK (pipeline_base.cpp:884-891@6b0b49f3; all imx585 delays are 2: camera_sensor_properties.cpp:389-394).
- The driver writes VMAX, SHR (= VMAX − exposure) and HMAX as separate I2C writes with no REGHOLD grouping (imx585.c:3478-3543@cd548ef; a grep for REGHOLD is empty).
- So one frame can expose with the new HMAX and the old SHR, or the reverse. The level error is then about the HMAX ratio: +5.6 % (581/550) or +8 % (594/550). The measured max step is 8.9 %.
- To settle it: line the band-level steps up against the frames where HMAX switched.

**Fixes proposed and items left open:**

| Item | Status | Source |
|---|---|---|
| Reference MONOTONIC_RAW or the audio crystal instead of BOOTTIME | Proposed, not built | hardware-log.md:274-275 |
| Raise the deadband to 12 µs ("one line") if flicker shows | Proposed, never run | T27 note §3.3 answer, :139 |
| Lock off by default, and off on this libcamera | Decided | hardware-log.md:292; core.md:596-597 |
| T27 5.2 (10-minute take with the lock on) and 5.3 (mode switch, then record) | Not run | T27 note :17 |
| Locking of the `settings_` writers (critic X6); gains for 8-10 buffers in flight (critic P4) | Open | critic.md |
| A VBLANK-only actuator on the qbc libcamera | Never proposed | — |

**Is Apertar's `FramePhaseLock` a faithful port?** The law is, line for line. The plant and the reference clock are not.

| Aspect | Cinemate @63a08d5 | Apertar @31d5418 | Label |
|---|---|---|---|
| Gains, deadband, clamp, anti-windup, lround, push-on-change | phase_lock_core.hpp:27-32, :141-162 | FramePhaseLock.hpp:35-40, :119-138: identical | CONFIRMED |
| Error and datum | :120-125, t0 at the arming frame | :108, origin at :149: identical, also relative to an anchor | CONFIRMED |
| Gap and re-arm rules | :90-139 | :88-117: identical | CONFIRMED |
| Role gate | `roleClient` parameter | none (signature :79) | CONFIRMED |
| Reference | FrameWallClock (REALTIME fit) | `SensorTimestamp`, BOOTTIME ns stamped by the kernel (CC:8775, :8813) | CONFIRMED |
| Enable | Redis flag | setting && !photo && fps > 1 && not in the fps-ramp grace (CC:8789-8790) | CONFIRMED |
| Tuning | live Redis keys | env vars, read once per process (`static const`, CC:8795-8809); clamp also via env | CONFIRMED |
| Delivery | one-shot on the next request | pin on every requeued request after all merges; skipped while a still is busy; a later storage pre-roll pin overrides it (CC:8934-8958) | CONFIRMED |
| **Actuator underneath** | stock helper: VBLANK only | **qbc lattice `4cff971`: re-chooses HMAX for every pinned µs** (cam_helper_imx585.cpp:118-226@6b0b49f3) | CONFIRMED (code and readback) |
| Saturation, telemetry | none; Redis `pll_*` | echoed limits checked against the last 16 pins; `/api/state fps_phase_lock_*`; a stats line at stop | CONFIRMED |
| Loop latency | about buffers + 3 ≈ 10-11 frames (`--buffer-count 8`) | Clear HDR 8 buffers (+2 on exFAT and similar) ≈ 11-13 frames (CC:1325-1329, :1449-1460) | PROBABLE (p1 A2, critic P4) |

## B4 Accuracy budget

**Quanta on Apertar's rig** (891 MHz link). CONFIRMED from code: HMAX 550 for the 12-bit, 10-bit and Clear HDR tables (imx585.c:288-294, :305-311, :3313-3314@cd548ef); the clock is 74.25 MHz (:221); VMAX is rounded down to even (:3510). The lattice periods are ESTIMATEs computed with the helper's algorithm, which reproduces all three hardware readbacks exactly.

| fps | Lattice choice | Line time H | VBLANK-only step (2 H at HMAX 550) | Free-run error with the default helper |
|---|---|---|---|---|
| 25 | 550 × 5400, exact | 7.407 µs | 14.815 µs | 0 ppm |
| 24 | 625 × 4950, exact | 8.418 µs | 14.815 µs | −178 ppm (period) |
| 30 | 550 × 4500, exact | 7.407 µs | 14.815 µs | −444 ppm |
| 33 | 600 × 3750, exact | 8.081 µs | 14.815 µs | −222 ppm |
| 50 (SDR) | 550 × 2700, exact | 7.407 µs | 14.815 µs | 0 ppm |

- In Clear HDR one image row is about 2 H (≈14.8 µs). PROBABLE: the VMAX floor doubles in Clear HDR (imx585.c:3274, :3299-3301).
- Cinemate's line was about 11 µs (the test model; 28b30cc says "11us line quantum").

**Residual of one locked sensor.** The model: Apertar's shipped header with a 25 fps plant, loop latency L frames, and Gaussian timestamp jitter σ (σ on the Pi is UNCONFIRMED).
- Validation: lattice, sensor 45 ppm fast against slewed BOOTTIME, L 6-11, σ 2 µs gives max \|err\| 20-30 µs, p99 14-22 µs, one push per 8-10 frames. The MEASURED run was ±22 µs and one push per 9-10 frames.

| Actuator | L | σ | max / p99 \|err\| (µs) | Pushes | HMAX changes | Label |
|---|---|---|---|---|---|---|
| Lattice (installed) | 11 | 0 / 3 | 21.6 / 21.0; 31.2 / 22.5 | 1 per 28 frames; 1 per 7 frames | every push | ESTIMATE (MEASURED ±22 µs) |
| VBLANK-only, 14.8 µs | 1 | 0 | 7.5 / 7.3 (the deadband floor) | 1 per 62 frames | 0 | ESTIMATE |
| VBLANK-only | 6 | 3 | 94 / 68 | 1 per 6 frames | 0 | ESTIMATE |
| VBLANK-only | 11 | 0 / 3 | 107 / 104; 134 / 113 (≈15-18 H) | 1 per 3-4 frames | 0 | ESTIMATE |
| VBLANK-only, retuned (kp 0.01-0.06, ki 5e-5…1.5e-3, deadband 6-15) | 6-11 | 3 | no better than 67-177 max | — | 0 | ESTIMATE |
| Cinemate-like (11.1 µs lines, 1066 ppm fast) | 1 / 6 / 10 | 2 | 23 / 17; 63 / 42; 75 / 63 | 1 per 5 frames | 0 | ESTIMATE |

- **Cinemate's ±12 µs is the per-frame duration dither** (0.03 % of 40 ms), **not a phase or alignment bound.** Its phase residual was never published ("centered at 0"). The unit test only bounds it at < 300 µs, in a model without latency.
- With latency, the residual is set by quantum × latency, not by the deadband.

**Two sensors, L 11, σ 3 µs** (A 1.5 ppm slow; B −1.5, +10 or −30 ppm):

| Scheme | Lattice: \|tB − tA\| max / p99 | VBLANK-only: max / p99 |
|---|---|---|
| Both locked, shared grid datum | 39-45 / 32-33 µs | 211-231 / 187-212 µs (≈0.55 % of a frame) |
| Follower: A free, B servos on tB − tA | 21-29 / 16-23 µs. B changes HMAX every 6-7 frames; A never | 112-134 / 97-122 µs |
| Sample-and-hold follower (rpi.sync pattern: every K = 15-30 frames, threshold 8-15 µs) | — | Δ ≈ 3-8.5 ppm: 25-39 / 15-30. Δ ≈ 31: 52-78 / 41-58. Δ ≈ 98: 120-177 / 106-163 µs |
| Two locks with today's law (separate datums) | the arbitrary offset, up to ±20 ms | same |

All rows are ESTIMATEs. For comparison, rpi.sync's own threshold is 50 µs (sync.cpp:62-63@6b0b49f3, CONFIRMED).

**Two free-running sensors** (25 fps; 1 ppm = 1 µs/s; Δ is the sensors' relative crystal error).
- Sensor A: 1.2-1.6 ppm slow against the Pi crystal (MEASURED once, a ~4-minute preview window).
- Sensor B: UNCONFIRMED. It has its own oscillator (PROBABLE); the overlay declares a 24 MHz INCK (imx585-overlay.dts:60-63, :107-112@cd548ef).
- The lattice makes the nominal rates exact on each sensor's own crystal, so relative drift on Apertar is crystal Δ only.

| Δ (ppm) | ms per 10-min take | Time to drift one 14.8 µs step | Time to one frame of slip | 10-min takes per frame |
|---|---|---|---|---|
| 1.5 | 0.9 | 9.9 s | 7.4 h | 44 |
| 3 | 1.8 | 4.9 s | 3.7 h | 22 |
| 10 | 6 | 1.5 s | 67 min | 6.7 |
| 30 | 18 | 0.49 s | 22 min | 2.2 |
| 100 | 60 | 0.15 s | 6.7 min | 0.67 |
| 40-80 (one sensor locked to BOOTTIME during a timesyncd slew) | 24-48 | 0.2-0.4 s | 8-17 min | 0.8-1.7 |
| ~1066 (Cinemate shipped dual, B2) | 640 | 14 ms | 37.5 s | 0.06 |

- These assume the stream runs continuously; a reconfigure re-randomises the offset.
- At 24 fps scale by 1.04; at 50 fps halve.
- Whatever Δ is, the **start offset is random within ±P/2**, so free-running sensors are never frame-synchronised without an alignment step.

**Simulation sources** (scratch, in no repo; folder `/private/tmp/claude-502/-Users-patrikeriksson--claude-spares-spare-niESh6/f112d566-1876-4e08-9788-61e89e7de390/scratchpad/plsim/`):
- `dualsim.cpp`: lattice and VBLANK-only plant, latency, one sensor, grid pair, follower.
- `tune.cpp`: gain and deadband sweep, Cinemate-like case.
- `hold.cpp`: sample-and-hold follower.
- `modes.cpp`: per-fps lattice periods.
- `FramePhaseLock.hpp`: extracted from `31d5418`.

---

## Implications for dual-sensor sync

1. **Two copies of today's law do not sync two sensors.** Cinemate's and Apertar's laws are the same: the error is anchored at the arming frame, so the result is the same rate with a frozen, arbitrary offset of up to ±20 ms. Removing a role gate changes nothing. **The error definition must change.** CONFIRMED.
2. **There are two ways to share a datum.**
   - **(a) Grid.** Set origin = the nearest k·P on CLOCK_BOOTTIME. Both processes read the same kernel clock, so no IPC is needed. Re-arms must snap to the grid, not to "now".
   - **(b) Follower.** B's error = tB − tA,nearest, from A's SensorTimestamps over IPC; A runs no servo. This is rpi.sync's structure (sync.cpp:256-264).
   - Prefer (b) on this rig. A never pushes, so it keeps the exact 550 × 5400. The scheme measures differences, so NTP slew cancels out. It needs a channel carrying A's per-frame BOOTTIME stamps. PROBABLE.
3. **Either way, two of today's rules must change.** The preview "\|e\| > P/2 → re-arm to now" rule (phase_lock_core.hpp:130-139; FramePhaseLock.hpp:112-117) would throw the alignment away. And pull-in happens at the clamp: 20 ms ÷ 150 µs per frame ≈ 133 frames, about 5.3 s plus settling, so alignment must finish in preview before recording. CONFIRMED rule; ESTIMATE timing.
4. **The actuator is the blocker on the installed libcamera.** With `7e9fef0`/`4cff971`, every 1-2 µs push re-chooses HMAX: MEASURED up to +8 % line length, 10 drops and 8.9 % level steps in 60 s. The lock, a follower, and rpi.sync all hit it: rpi.sync's offset goes through `getBlanking(min − off, max − off)` with min = max (ipa_base.cpp:1836-1837; cam_helper_imx585.cpp:130@6b0b49f3). PROBABLE for rpi.sync.
   - Untested ways out: pin `{d, d+1}`, since min ≠ max skips the lattice branch (verify that hblank reads back 0); a fork patch that leaves HMAX alone for a sync owner; REGHOLD grouping in the driver.
5. **VBLANK-only is coarse and slow on this rig.** Steps are 14.815 µs (even VMAX at HMAX 550), and the loop latency is about 11-13 frames (PROBABLE).
   - The shipped per-frame PI then cycles at about ±110-130 µs per sensor and ±210-230 µs between two grid-locked sensors (ESTIMATE). Retuning the gains does not help (ESTIMATE).
   - A sample-and-hold correction every K > L frames, which is how rpi.sync uses its 30-frame period, reaches ±25-40 µs at Δ ≤ ~10 ppm without HMAX changes (ESTIMATE). Above that it needs a rate term, or the latency compensated by counting the pins in flight.
6. **The cost per correction differs by orders of magnitude.**
   - A VBLANK step changes one frame by 0.037 %, plus roughly 2 lines of exposure if SHR is not rewritten (imx585.c:3506-3523; PROBABLE about 0.07 % at 1/50 s). That matches the order of Cinemate's 0.03 %.
   - A lattice step is +5.6-8 % HMAX (MEASURED harm).
7. **Use SensorTimestamp (BOOTTIME) for alignment, not FrameWallClock.** SensorTimestamp is one kernel clock shared by both processes. FrameWallClock comes from one ClockRecovery model per camera (pipeline_base.h:181@6b0b49f3). CONFIRMED.
8. **Absolute locks to BOOTTIME chase the slew.** Two absolute locks to BOOTTIME both follow timesyncd's 40-80 ppm slews (MEASURED). That is harmless for their relative alignment, but means more pushes (more flicker on the lattice). If an absolute grid is wanted, convert to MONOTONIC_RAW per frame (PROBABLE).
9. **Never discipline only one sensor absolutely.** Cinemate's shipped dual drifts by the mode's uncorrected error, about 1 ms/s (PROBABLE). On Apertar a one-sided BOOTTIME lock adds the slew, 40-80 ppm. Identical pins on both sensors mean identical quantisation, so the relative drift is the crystal Δ only. CONFIRMED mechanism.
10. **Measure first, once B is attached.** None of these changes the camera's state:
    - Δ between the sensors: run the meter-mode lock in both processes and compare against MONOTONIC_RAW (the T27 method).
    - Timestamp jitter σ: per-frame SensorTimestamp deltas. At σ = 3 µs the 6 µs deadband makes pushes jitter-driven, about one per 7 frames even at 1.5 ppm (ESTIMATE).
    - Loop latency: frames from a push to the first changed `FrameDuration` in the metadata.
    - These three numbers set K, the deadband and the residual to expect.
11. **Pair and count frames by the nearest k·P**, like rpi.sync's `framePeriodErrors` rounding (sync.cpp:259-260@6b0b49f3), so that a drop on either sensor is never read as a one-period phase error. Today's recording-gap absorb works per process only. CONFIRMED.
12. **Add a per-pair number that could prove the sync wrong.** Use \|tB − tA\| max and p99 per take, plus HMAX switches and drops per sensor. Cinemate's `pll_*` keys are global and unread, and Apertar's `fps_phase_lock_*` is per process. CONFIRMED gap.