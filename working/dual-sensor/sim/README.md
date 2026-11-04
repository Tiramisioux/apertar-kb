# Dual sensor: host models behind the sync numbers

Written on the Mac by the agents of 2026-11-03/04 (phase-lock deep-dive and claim check). They are scratch
models, not repo code: every number they print is an **estimate** until the rig measures it (design
`../design-dual-sensor.md` §7). Nothing here runs on the Pi.

| File | Written by | What it models | Run |
| --- | --- | --- | --- |
| `lattice_sim.py` | claim check (libcamera) | libcamera's `getBlanking` (base and IMX585 lattice, `cam_helper.cpp:82-132`, `cam_helper_imx585.cpp:118-226`@6b0b49f3) and the driver's VBLANK/HBLANK/EXPOSURE handlers (`imx585.c:3478-3544`@cd548ef) | `python3 lattice_sim.py check`: reproduces the T27 readbacks 40000 → hb 0 / vb 3200, 40001 → 217 / 2912, 40016 → 308 / 2802 (hardware-log.md:246-258). Also `modes`, `sweep <mode> <nominal_us> <span> <exp_us>`, `list <mode> <lo> <hi> <exp_us> lattice\|range` |
| `lock_model.py` | claim check (Core) | the shipped `FramePhaseLock` law on three actuators (ideal, floor = pin `{d,d+1}`, sigma-delta = floor + quantiser) against a grid: pull-in time and overshoot | `python3 lock_model.py` |
| `synth/grid_sim.py` (+ `_m` variant with a measured-error path) | sync synthesis | one sensor locked to the absolute grid k·T: dead time D, frame-start jitter σ, even-VMAX step 14.815 µs, actuators A, A+Q, A+Q+S | imported by the three below |
| `synth/more_sim.py`, `dual_sim.py`, `meas_sim.py` | sync synthesis | the accuracy tables of `../sync-synthesis.md` §5: single and dual max / p99 / RMS, pushes per 1000 frames, per fps, D and σ | run **from `synth/`** (they import `grid_sim` from `.`): `python3 more_sim.py` (~1 s) |
| `plsim/dual_model.cpp` and the files that include it (`deadtime*.cpp`, `dual_comp.cpp`, `pullin2.cpp`) | sync investigator A | the shipped law and a nearest-slot grid variant, VBLANK-only or lattice realisation, D in flight, per-sensor crystal error and jitter; dead-time compensation and pull-in variants | `c++ -std=c++17 -O2 -o /tmp/x dual_model.cpp` (each file builds alone) |
| `plsim/dualsim.cpp`, `tune.cpp`, `hold.cpp`, `modes.cpp` | sync investigators B/C | two sensors at 4K 25 fps; gains versus limit cycle; an rpi.sync-style sample-and-hold follower; mode line times | same build line |
| `plsim/FramePhaseLock.hpp` | copy | Core's header at `drop-frames` 31d5418, copied with `git show` so the C++ models build. It drifts once Core changes: re-copy before trusting a model against new code | |

Assumptions they share, and that the rig must check: constant dead time D, independent Gaussian jitter per sensor,
no coupling between the two CFE frame-start interrupts, no CFE bias, no frame drops (sync-critique.md S12 and "Missing"
1, 7).
