# Dual-sensor project: two IMX585 on one Apertar, synced by the phase lock (plan v2, 2026-11-04)

**Patrik's brief (2026-11-03):**
- Port Cinemate's dual-sensor feature to Apertar, display and record modes included, "the least intrusive way, and
  most apertar like", maybe with two instances of Core.
- The rig is a CM5 on a Waveshare Mini Base Board (A).
- No second sensor is attached yet.
- Sync should come from Cinemate's phase lock, "in software".

**Status: planned, nothing built.**
- Read-only research on the Mac from git refs, plus one read-only look at the Pi (`r5-pi-hardware.md`).
- Trees: Core `31d5418` and UI `c153c33` (both `drop-frames`, what the Pi runs), driver `cd548ef` (`cinemate-port`),
  libcamera `6b0b49f3` (the Pi's `7e9fef0b` has the same helpers), Cinemate `d6cc93e`, cinepi-raw `63a08d5`.
- Steps **T56-T70** are reserved here: playback used T46-T54, and T55 is the Clear HDR 16-bit preview tutorial.
  `llm/tutoring.md` §5 notes the reservation. A step gets its row there, and its tutorial, when Patrik starts it
  (Rule 1, or Q25 in the design).

**Start with** `plan-summary.md`, then `design-dual-sensor.md` §0 and §9.

**First step:** T56, measurements only, no code. Of its tests, 0.3 (a camera-manager start's HBLANK disturbance at
24 fps) and 0.4 (dead time in Clear HDR) feed the sync design.

**Main risk:** a camera-manager start in one Core resets the other sensor's line length. The design keeps it harmless
(HBLANK 0 under the lock, no starts during takes); T56 and Part 2 measure it.

| File | What |
| --- | --- |
| `plan-summary.md` | one page: the recommendation, steps T56-T70, the questions to answer first |
| `design-dual-sensor.md` | the design (v2): two Cores, the relay, display, recording, the grid phase lock, platform rules, API delta, steps file by file with checks, Pi tests with predictions, risks, questions with defaults, verification table |
| `changes-from-critique.md` | each point of the two critiques: taken, changed or not taken, and why; the stale KB pages the claim check found |
| `r1-cinemate-dual.md` … `r5-pi-hardware.md` | reader reports: Cinemate's dual feature (r1), Core as one of two processes (r2), the UI, HDMI window and WebUI (r3), libcamera, driver and bandwidth (r4), the Pi's hardware as read on 2026-11-03 (r5) |
| `claim-check.md` | 82 claims from r1-r5 re-read in code by agents that tried to refute them, and 50 new findings (ids L, D, C, R, U, M, X, K) |
| `r6a-sync-core.md`, `r6b-sync-cinemate-t27.md`, `r6c-sync-libcamera-driver.md` | the phase-lock deep-dive: Core's lock, Cinemate's lock and the T27 record, libcamera's IMX585 helper and the driver |
| `sync-synthesis.md`, `sync-critique.md` | the sync design drawn from r6a-c, and its critique (S1-S14; three refutations, fixed in the design's §7) |
| `design-a-least-intrusive.md`, `design-b-operator-first.md`, `design-c-risk-first.md` | the panel's three independent designs |
| `design-merged-v1.md`, `critique-merged-v1.md` | the judge's scores and merged v1, and its critique (P1-P25) |
| `sim/` | host models behind the sync numbers: libcamera's lattice and the driver, the lock on a grid with dead time and jitter, two sensors. `sim/README.md` has the run lines. Estimates until the rig measures |

All files except the design, the summary, this README and the change log are frozen agent reports. Corrections go in
the design.
