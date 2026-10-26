# Apertar vs Cinemate: the optional frame-rate phase lock

Written 2026-10-26 (cloud session) from `cinepi-raw@63a08d5` (`cinepi/phase_lock_core.hpp`, `cinepi_controller.cpp`,
`tests/phase_lock_core_test.cpp`), `cinemate@d6cc93e`, `libcamera(qbc)@7e9fef0` and `libcamera(cinemate)@bfe0b76`,
`apertar-core@f60e301` (patched at `2a6f114`), the reader reports `working/port-raw/p1-phaselock-cinemate.md` and
`p2-phaselock-core.md`, and the history pass in `working/cinemate-lessons.md` §2–3. Nothing ran on a Pi.
CONFIRMED = read in source; PROBABLE = inferred, reason given; UNKNOWN = not established.
Patch: `working/patches/0001-camera-frame-rate-phase-lock-off-by-default-fps_phas.patch` (Core `2a6f114`,
not compiled; the pure header is host-simulated by `working/tools/phase_lock_sim.cpp`). Tutorial T27.

## 1. Verdicts

| Question | Answer | Status |
|---|---|---|
| What does Cinemate's lock do | per frame: phase error = arrival time − (datum + k/fps) on a reference clock; PI servo kp 0.06, ki 0.0015, deadband 6 µs, clamp ±150 µs; integer-µs request to `FrameDurationLimits {d,d}` pushed only when it changes; the integer rounding is a first-order sigma-delta over adjacent line counts | CONFIRMED (p1 §1) |
| Measured result on Cinemate hardware | imx585 mode0 25 fps: +1066 ppm → −9 ppm; 2–3 line dither (±12 µs); 0.03 % exposure variation; 0 drops (`55562b6`) | CONFIRMED (commit) |
| Reference clock | Cinemate: `FrameWallClock` (REALTIME, de-jittered) "= the audio clock" (`5b4b209`). Core: `SensorTimestamp` (BOOTTIME), because Core's audio is stamped on BOOTTIME (`TimestampedAudioCapture.cpp:195-228`) | CONFIRMED (p2 §3) |
| Audio change needed in Core | **No.** The lock disciplines the picture to the clock the audio is already measured against; `finalizeWav`'s resampler keeps correcting the ALSA crystal (20–2000 ppm) | CONFIRMED (p2 §3, §5) |
| Default | Cinemate on, standalone cinepi-raw off (`0b8e947`). Core: off until T27 has measured it on the rig | decision |
| Gains | same four numbers; host simulation of the Core header reproduces 0.00 ppm mean, 13.9 µs max error, 3 adjacent requests from a +1066 ppm sensor (`phase_lock_sim.cpp`, 17 checks pass) | CONFIRMED (host) |
| Hazard specific to Core | the qbc libcamera's IMX585 `getBlanking` lattice search (`4cff971`, after the 20260522 tag) may re-choose HMAX per microsecond of requested duration; Cinemate's first commit says an HMAX-stretching patch once produced a broken 4K image (`bf717fa`). Whether the rig's libcamera binary has the lattice is UNKNOWN; T27 §3 measures `HBLANK`/`FrameDuration` with two pinned durations 1 µs apart before enabling | PROBABLE |

## 2. Where the frame cadence error comes from, and what the lock changes

- The sensor realises a frame period as whole lines of its own 74.25 MHz crystal (IMX585); the Pi stamps
  `SensorTimestamp` from `ktime_get_ns()` at CSI-2 frame start (`rp1_cfe/cfe.c:692`). Even when the line
  count makes 24.000 fps exact on the sensor clock, the two crystals differ by tens of ppm, sign unknown
  (p2 §4). Core today (CONFIRMED, p2 §5): a slow sensor makes `nextFrameIndex` skip an index (a numbering
  hole with no real drop) after 0.5/e frames (30 ppm → first hole after ~11.6 min at 24 fps) and rolls the
  WAV one frame longer; a fast sensor keeps indices consecutive but audio drifts e × clip length against
  the picture (30 ppm × 1 h = 108 ms). Neither is logged.
- With the lock referenced to BOOTTIME: cadence error bounded by the clamp (150 µs = 0.0036 of a 24 fps
  period), no index holes, WAV length = N × nominal, A/V long-term drift from the sensor crystal removed;
  the ALSA crystal remains the resampler's job (p2 §5).
- Cinemate's three mode-switch iterations (`e74e3e4`, `3b3ff60`, `4537153`): a 186 ms reconfigure stall
  leaked into the accumulator and recordings started −90 / −169 ms behind; the final policy (preview gap
  > 1.5 frames re-arms; recording gap absorbed as missed frames; preview half-frame backstop) is in the
  Core header and exercised by the simulation. T27 §5 repeats their failing case on the Pi: switch mode,
  record within 2 s, read the first frames' phase error.

## 3. How the port sits in Core (CONFIRMED from the diff)

- `src/camera/FramePhaseLock.hpp` (147 lines): pure state machine, `step(enabled, recording, fps, referenceNs)`
  → `Decision{active, rearmed, servoRan, pushDuration, durationUs, phaseErrorUs}`; telemetry `maxAbsErrorUs`,
  `pushes`. Same four constants as Cinemate; whole-µs requests; first-order dither by rounding.
- `CameraSession::stepFramePhaseLock` (`CC:7147`) runs on libcamera's completion thread after the metadata
  read, before `requeueRequest` (`:7336`); the pin `FrameDurationLimits {d,d}` is merged in `requeueRequest`
  after the photo-mode merges (`:7263-7264`), so a still capture's long exposure wins.
- Re-arm on fps or switch change (`applyControls`, `:6123-6126`), release at `stop()` (`:6040`); stats at
  record stop `ApertarCore phase-lock stats: max_abs_err_us= duration_pushes=` (`:6289-6292`); trace every
  250 frames with `APERTAR_PHASE_LOCK_LOG=1` (`:7176-7180`).
- Setting `fpsPhaseLock` (persisted, `Types.hpp:127`), command `set_fps_phase_lock enabled=true|false`
  (`App:9631`), state field `fps_phase_lock` (`App:203`, `:7913`).
- Not referenced to `FrameWallClock`: Core never reads it (grep); choosing it would add NTP slew into every
  BOOTTIME-based consumer (p2 §3). No `--sync` role gate: Core drives one sensor.
- Consumers of `FrameDuration` metadata checked for Cinemate's half-integer hazard (`3c6477e`): only the gap
  estimator's nominal (`trackRecordingCadence`, tolerant to ±150 µs) and the WAV end model's fallback when
  fps is unknown; DNG FrameRate (0xC764), DNG/MLV timecode and MLV fps come from `settings.fps`. No change.

## 4. Lessons from Cinemate's history folded in (see `cinemate-lessons.md` §2)

| Lesson | Where it lands |
|---|---|
| Pure header + tests that run the shipped code (`28b30cc`) | `phase_lock_sim.cpp` includes the shipped header; T27 §3.0 runs it on the Mac/Pi before any camera step |
| PI not I (`85d0326`) | header |
| Pre-converge in preview (`d038556`) | header; T27 checks `rearmed` only at the first frame after a switch |
| Gap policy, three iterations | header; T27 §5.3 reproduces the failing case |
| Average intervals then invert (`b029d7f`) | T27's measurement script computes 1/mean(dt) |
| Log values, not conclusions; add the number that would falsify the fix | stats line carries `max_abs_err_us` (grows if the lock fails) |
| No per-frame telemetry nobody reads (handbook) | stats at stop + env-gated trace |
| A default is a claim; read back the value the hardware receives | T27 §3.2 reads `FrameDuration` metadata and `HBLANK`, not the request |
| "Phase lock" supersedes static correction tables (`2f79397`) | Core had none; its rounding heuristics become exact |

## 5. Open points for T27 to settle on the Pi

1. Does the rig's libcamera realise a 1 µs duration change as a VBLANK step (line count) or as an HMAX
   re-choice (line length)? Readback: `v4l2-ctl -d /dev/v4l-subdev0 --get-ctrl hblank,vblank` with two pinned
   durations. If HMAX moves, measure rolling-shutter skew and exposure stability before enabling.
2. Sensor-vs-Pi crystal offset (sign and ppm) at the rig's 24/25 fps modes: from the first measurement step.
3. `max_abs_err_us` over a 10-minute take: expect ≤ ~15 µs; `duration_pushes` roughly every 4–5 frames.
4. `ApertarCore audio clock: measured_drift_ppm=` unchanged by the lock (it is the ALSA crystal).
5. Mode switch then record: first-frame `phaseErrorUs` within the deadband after the preview re-arm.

## Verification status

An adversarial verifier pass (2026-10-26) is appended to `working/port-raw/p1-phaselock-cinemate.md` and `p2-phaselock-core.md`: p1 20 claims, p2 20 claims, 0 refuted, 7+9 corrected for line numbers or wording only. One p2 caveat is already met by the patch: the pin in `requeueRequest` reads `settings_.photoModeEnabled` under `controlsMutex_` (`CC:7262-7265`), the lock `applyControls` writes settings under; `requeueRequest` is also reached from the ProRes and H.264 release paths without the settings lock.
