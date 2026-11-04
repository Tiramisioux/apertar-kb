<!-- Dual sensor, sync critique (2026-11-04): an adversarial critic re-read the code behind sync-synthesis.md (Core 31d5418, libcamera 6b0b49f3, driver cd548ef, cinepi-raw 63a08d5) and re-ran its models. Frozen: what was taken over is in design-dual-sensor.md. -->

# Dual sensor: critique of the sync synthesis

## Overall

Sound at its core, but it needs three corrections before Part 1.

CONFIRMED in code:
- Both the shipped law and Cinemate's law anchor phase at the first frame after arm (FramePhaseLock.hpp:149@31d5418; phase_lock_core.hpp:104@63a08d5). Two locks therefore share only a rate, and dropping Cinemate's role gate would not help.
- SensorTimestamp is the one clock both processes share (pisp.cpp:2237@6b0b49f3), and Core already treats it as BOOTTIME. The kernel side is PROBABLE.
- `{d,d}` triggers the qbc lattice and `{d,d+1}` takes the base path (cam_helper_imx585.cpp:130-132). My emulation reproduces the measured readbacks exactly, and 299 of 300 one-µs steps change HMAX.
- The driver never rewrites SHR on a VBLANK change (imx585.c:3506-3523@cd548ef).
- Every CameraManager start writes HBLANK = minimum to every sensor it enumerates, the other Core's streaming sensor included (camera_sensor_legacy.cpp:288-296 plus the PiSP match loop and media-lock semantics).

REFUTED:
1. "A restart's HBLANK write is harmless because the other sensor runs HBLANK 0" is true only while the other Core is grid-locked. Core's `{d,d}` base pin (CC:2406-2415) re-engages the lattice in every release window, so dual mode must make that pin VBLANK-only too.
2. The 24 fps figures for option (b) are wrong. The error is about 178 ppm, not 355, and the frames run fast, so there are no phantom holes but about 107 ms of A/V gain per 10 min. The lattice's exact 625×4950 point is also available to hold.
3. The reason for never stretching mid-take is wrong. The FrameDuration test only guards the first frame; the real cost is a time-index hole that breaks slot = index + k0.

UNCERTAIN:
- The accuracy budget reproduces from the synth scripts, but it assumes independent per-sensor jitter, a constant D and zero CFE bias. Coupling between the two aligned frame-start IRQs is unmodelled.
- XVS output on the leader is unverified because the driver comments contradict each other.
- Clear HDR VMAX parity is unverified.

Recommendation: proceed with Part 1. Ship fix A together with a VBLANK-only base pin, and keep fix E as the prerequisite (consider a register hold). Add three tests:
- an HBLANK readback at 24 fps during an fps-change grace;
- a SensorTimestamp period check at VMAX 5402 in Clear HDR;
- in Part 2, a skew-histogram check for order-dependent bimodality.

## Claims

### S1 · HOLDS

- **Claim.** §1 verdict: the shipped law measures phase from a per-arm origin. Two locked Cores therefore share a rate but hold a random, frozen offset in [0,T), re-drawn at every re-arm (fps change, stop/reconfigure, ramp grace, preview gap).
- **Evidence.** CONFIRMED. src/camera/FramePhaseLock.hpp@31d5418: arm() sets originNs=referenceNs (:149) and frames=0 (:150). The error is (ref−origin) − frames·period (:108), with period = 1e9/fps (:87), which is identical in both processes, so the offset stays frozen. Re-arm happens on the first frame, an fps change or a preview gap (:95-100), and on |e| > T/2 in preview (:112-117). Release paths: src/camera/CameraController.cpp (CC) CC:7490-7494@31d5418 (fps change, lock toggle, photo toggle); CC:8789-8790 (photo mode; ramp grace via inFpsRampGrace, CC:9667-9671); reconfigure = stop()+start() with a new CameraManager (CC:7439-7457, :7247).

### S2 · HOLDS

- **Claim.** Cinemate's law is the same (origin = first frame after arm), so removing its role gate would not align the two sensors.
- **Evidence.** CONFIRMED. cinepi/phase_lock_core.hpp@63a08d5: t0Ns=refTsNs at arm (:99-111, :104); error = (ref−t0) − frameCount·1e9/target (:120-125); the same half-frame preview re-arm (:130-139). 'References FrameWallClock' (:12, :64) names the clock only; there is no epoch-anchored grid. Role gate at :75-80.

### S3 · HOLDS

- **Claim.** §2 clock: SensorTimestamp is the one clock both processes share. It is the CFE frame-start ktime_get_ns() = CLOCK_MONOTONIC, equal to BOOTTIME on a Pi that never suspends. FrameWallClock is per camera, so the grid must be built on SensorTimestamp.
- **Evidence.** CONFIRMED (libcamera/Core). SensorTimestamp = CFE buffer metadata timestamp: src/libcamera/pipeline/rpi/pisp/pisp.cpp:2236-2241@6b0b49f3. It is converted from timeval, so it has 1 µs resolution: v4l2_videodevice.cpp:1899-1900. There is one ClockRecovery per CameraData (pipeline_base.h:181), fitted BOOTTIME→REALTIME (clock_recovery.cpp:118-120). Core already compares ts/1000 with CLOCK_BOOTTIME µs (CC:7631, :7649, :9072@31d5418). PROBABLE (kernel): ktime_get_ns at the frame-start ISR plus TIMESTAMP_MONOTONIC is only KB-cited (working/port-raw/p2-phaselock-core.md:39, cfe.c:692/:714/:1950@5bd564a); no kernel tree was available to re-read. Core has no system-suspend path (git grep for suspend|/sys/power/state in src: none), so BOOTTIME = MONOTONIC holds in practice.
- **Correction.** Minor: the grid is really on CLOCK_MONOTONIC, the SensorTimestamp domain. Say so, and compute start_us and the 'late' check in that domain.

### S4 · HOLDS

- **Claim.** §3: today's {d,d} pin sends every non-standard duration through the qbc lattice (40001 µs → HMAX 581×5112; C: 299 of 300 one-µs steps change HMAX). Pinning {d,d+1} takes the base getBlanking path instead: floor to whole lines, hblank 0, HMAX 550, no libcamera rebuild.
- **Evidence.** CONFIRMED. Gate: src/ipa/rpi/cam_helper/cam_helper_imx585.cpp:126-132@6b0b49f3 returns the base result whenever min≠max. Base path: cam_helper.cpp:87 (lineLength = minLineLength), :96-97 (Duration/Duration truncated to uint32), :120-121. The only other min==max tests in src/ipa/rpi are the imx294/imx492 helpers and ipa_base.cpp:546. Core pins {d,d} at CC:8948 and in the lock-off base pin CC:2406-2415@31d5418. My emulation of cam_helper_imx585.cpp:118-226 reproduces the measured readbacks exactly: 40000→0/3200, 40001→217/2912, 40016→308/2802 (KB lessons/hardware-log.md:250). It also gives an HMAX change on 299 of 300 one-µs steps over 39850-40150 µs, and 298 of 300 over 41516-41816 µs.
- **Correction.** Edge case: applyFrameDurations clamps both ends to the mode limits (ipa_base.cpp:1788-1792). At a mode's top fps, a pin whose d+1 is below the mode minimum collapses to min==max and re-enters the lattice.

### S5 · HOLDS

- **Claim.** Fix E: the driver's VBLANK case writes VMAX only, and an unchanged EXPOSURE never reaches the SHR write. Every VBLANK push therefore moves integration by ΔVMAX (2 lines). Rewriting SHR from the clamped exposure, and moving dev_info at :3495/:3499/:3518/:3536 to dev_dbg, is the fix.
- **Evidence.** CONFIRMED in imx585.c@cd548ef. VBLANK case :3506-3523: vmax = (height+vblank) & ~1 (:3510); modify_range on exposure only clamps (:3512-3516); VMAX is written (:3520); no SHR is written. SHR = (vmax−exposure) & ~1 exists only in the EXPOSURE case (:3478-3487). EXPOSURE is created without EXECUTE_ON_WRITE (:3850-3853; grep finds no flag). The four dev_info calls are where cited. libcamera sends VBLANK and EXPOSURE every frame (ipa_base.cpp:1847-1848@6b0b49f3), and the imx585 delays are exposure/gain/vblank/hblank = 2/2/2/2 (camera_sensor_properties.cpp:389-394), so an SHR rewrite inside the VBLANK handler targets the same frame. PROBABLE: the V4L2 core skips s_ctrl for an unchanged value (kernel code, not read here).
- **Correction.** Add to fix E: the driver uses no register hold anywhere (no REGHOLD/0x3001), so VMAX and SHR go out as two separate CCI writes. Bracket them if the IMX585 hold register applies, or accept a rare one-frame mismatch.

### S6 · HOLDS

- **Claim.** Line time and quantum: at the 891 MHz link H = 7.407 µs (HMAX 550), HBLANK min is 0, and the VMAX quantum is 2 lines = 14.815 µs, the same in Clear HDR. Test 1.1 should read hblank 0 / vblank 3200 at 25 fps. A whole-µs pin on a line boundary can floor to V−1 in double arithmetic (P).
- **Evidence.** CONFIRMED in imx585.c@cd548ef. HMAX 550 at LINK_FREQ_891MHZ (:294, :311); Clear HDR floored to 550 (:3313-3314). Pixel-rate proxy = width·74.25 MHz/min_hmax = 518.4 MHz (:3383-3384), so 3840/518.4e6 = 7.407 µs. HBLANK range starts at 0 (:3392). VMAX is floored to even (:3510). Clear HDR doubles min VMAX (:3274, :3301): 4500 lines = 33.33 ms = 30 fps maximum. MEASURED: the 16-bit Clear HDR stream is 3840x2200 and read '0 / 3200' at 25 fps (hardware-log.md:248-250). Computed: libcamera's double line time is 7407.407407407408 ns, 4.4e-13 ns above 200000/27. With it, 40000 µs floors to exactly 5400, but 58 of the whole-µs VMAX values in 2160-16200 floor to V−1 (e.g. 30000 µs → 4049, 120000 µs → 16199). So the push d = ceil((V+½)H) in Q is needed.
- **Correction.** UNCONFIRMED part: whether Clear HDR, which spends 2 VMAX units per row, accepts VMAX ≡ 2 (mod 4). If it needs multiples of 4, the quantum is 29.6 µs. Settle it by measuring the SensorTimestamp period at a pin that gives VMAX 5402.

### S7 · HOLDS

- **Claim.** §2 dual rule: every CameraManager start writes HBLANK = minimum to every sensor it enumerates, including the sensor the other Core is streaming. Reconfigure recreates the manager.
- **Evidence.** CONFIRMED @6b0b49f3. camera_sensor_legacy.cpp:283-296 writes V4L2_CID_HBLANK = minimum, then sets TEST_PATTERN off (:298). The PiSP match() loops over both CFE instances and registers every MEDIA_ENT_F_CAM_SENSOR (pisp.cpp:1155-1235) via CameraSensorFactoryBase::create (pipeline_base.cpp:851). Media devices stay enumerable by other instances by design (media_device.cpp:128-135). The only cross-process lockf is taken at camera acquire (media_device.cpp:144-150, pipeline_handler.cpp:175), and busy() is per process (device_enumerator.cpp:208, :351). Core recreates the manager on every reconfigure (CC:7439-7457, :7247@31d5418). HBLANK minimum is 0 (imx585.c:3392@cd548ef).

### S8 · REFUTED

- **Claim.** §6 'Core restart mid-shoot: its enumeration write of HBLANK is harmless because the other sensor runs HBLANK 0' (with HBLANK at 0 the write is a no-op).
- **Evidence.** The no-op part is PROBABLE. 'The other sensor runs HBLANK 0' holds only while the other Core's lock is engaged in grid mode. Whenever that lock is released, Core's base pin is {d,d}: max = d in video mode (CC:2406-2415@31d5418). The base pin is re-sent through pendingControls_ on every applyControls (CC:7485-7489), and the lock pin is cleared (CC:7492-7493, :8817, :8822). Releases happen on every fps change for max(10, N+6) frames (CC:9644, :8789-8790), in photo mode, during ramps, and whenever the lock is off. On {d,d} at 24 fps, my emulation of cam_helper_imx585.cpp:118-226@6b0b49f3 gives HMAX 625×4950 with hblank 524. A foreign write in that state costs about a 5.0 ms phase step (working/dual-sensor/claim-check.md:37).
- **Correction.** Harmless only while the other Core pins VBLANK-only, or at 25/30/50/60 fps, which are exact at HMAX 550. In dual mode, also make the base pin {d,d+1} (CC:2413). Alternatives: keep the CameraManager across reconfigures, or skip the init write in the fork when another process holds the media lock.

### S9 · REFUTED

- **Claim.** §2 and §4: today's record gate opens at 'now'; the first frame is the first with ts ≥ start and FrameDuration within max(500 µs, T/50); stop closes at once; index = max(counter, llround(elapsed·fps)); one RecordingClock offset per take. §2 adds: 'never stretch while recording; the stretched frame would fail the FrameDuration test (CC:9071-9073)'.
- **Evidence.** The description holds (CONFIRMED @31d5418): now = CLOCK_BOOTTIME µs (CC:7631, :7649); stop clears the gate (CC:7671); index rule at CC:4639-4646; RecordingClock rebuilt per take (CC:7520; src/audio/RecordingClock.hpp:36-41); FreeRun timecode floor at src/cdng/CdngEncoder.cpp:409. The stretch reason does not: the FrameDuration test sits inside `if (waitingForRecordingCadence_)`, and that flag clears on the first accepted frame (CC:9068-9074). No mid-take frame is ever tested.
- **Correction.** The rule is still right, for a different reason. A mid-take stretch of s µs advances the time index by s/T (CC:4642-4645). Once s > T/2 that leaves a phantom hole and breaks the slot = index + k0 identity that §4 relies on. Only at take start would a stretched first candidate be skipped, starting that Core one slot late.

### S10 · REFUTED

- **Claim.** §2 option (b) at 24 fps: '5625 lines is odd, so a held value is 355 ppm off; about 5 phantom index holes per 10 min (CC:4639-4646)'.
- **Evidence.** 74.25e6/(24·550) = 5625 exactly. The driver floors VMAX to even (imx585.c:3510@cd548ef), and libcamera floors d/H (cam_helper.cpp:96@6b0b49f3). Emulated: a held {41666,41667} gives 5624.91 → 5624, and 41667 → 5625, which the driver floors to 5624. The error is therefore 1 line = 177.8 ppm, and the frames run fast. With fast frames, nextFrameIndex keeps the counter (max(), CC:4644@31d5418), so there are no phantom holes. The lattice already gives exact 24.000 fps: HMAX 625 × 4950 = 3,093,750 ticks (snap at cam_helper_imx585.cpp:160-167; emulated).
- **Correction.** About 178 ppm, not 355. A natural 5624 hold gives 0 phantom holes, but the picture gains about 2.6 frames per 10 min over real time (about 107 ms against the WAV). Only a 5626 hold gives holes, about 2.6 per 10 min. Option (b) could instead hold the lattice's exact 625×4950 point; the same pin gives the same point on both sensors. The cost is HBLANK ≠ 0 during the take.

### S11 · HOLDS

- **Claim.** Dead time: the CC comment predicts about N+2/N+3; lag_frames=7 was measured at N=6 (N+1). So D ≈ 7 for SDR on exFAT and D ≈ 11 for Clear HDR on exFAT (N=10).
- **Evidence.** CONFIRMED: the comment is at CC:9628-9635 and the grace is max(10, N+6) at CC:9644@31d5418. MEASURED: 'lag_frames=7 on all 50 steps' (lessons/hardware-log.md:496; 1080p, exFAT). PROBABLE: N=6 does not appear in that log entry. It is the code default 4 + 2 for exFAT (CC:1325, :1452-1460), and a media-tune raw_buffers value can override it. Clear HDR is 8 + 2 (CC:1329, :1451), but the 2026-10-26 Clear HDR runs logged 8 requests in flight (hardware-log.md:272). D = 11 is an ESTIMATE.
- **Correction.** Label N=6 P, and D(Clear HDR) E until a lag_frames run in Clear HDR exists.

### S12 · UNCERTAIN

- **Claim.** §1/§5 accuracy (E): one sensor max 14-33 µs; between sensors max 30-53, p99 20-37, RMS 8-14 µs, not growing with take length; pushes on 8-25 % of frames at 25 fps and 75-93 % at 24 fps.
- **Evidence.** The numbers reproduce. Re-running scratchpad/synth/more_sim.py gives dual max/p99/RMS of 45.0-46.0 / 30.8-31.4 / 12.2-12.6 µs at 25 fps D11, 35.9-41.3 / 25.9-28.3 / 10.5-11.2 µs at 24 fps D11, and 34.8-38.2 / 24.2-26.3 / 9.6-10.2 µs at 50 fps D7. Pushes are 86-109 per 1000 frames at 25 fps and 896-917 at 24 fps. The model's assumptions limit what this shows: independent Gaussian jitter per sensor (grid_sim.py:22; separate seeds in dual_sim.py:11-12 and more_sim.py:6-7), a constant D (grid_sim.py:15, :47), both sensors starting on the grid (phase0=0.0), and a CFE bias of 0. Nothing couples the two timestamps.
- **Correction.** Treat these as a budget for uncorrelated jitter only. Coupling between the two frame-start IRQs and a variable D are not modelled; test 2.2 decides.

### S13 · HOLDS

- **Claim.** §8 rpi.sync: it would also go through the lattice (getBlanking(min−offset, max−offset)), log an error every frame with {d,d+1}, and correct in one-frame steps of at least 50 µs. It also needs a tuning block and a multicast route the rig does not have.
- **Evidence.** CONFIRMED @6b0b49f3: ipa_base.cpp:1836-1837 subtracts the offset from both ends, so min==max survives and the lattice engages; :546-548 logs an error when min≠max. sync.cpp:53 (default minAdjustment 50 µs), :259-274 (single-frame correction), :167 (wallClock reference). KB working/dual-sensor/r5-pi-hardware.md:26 and :31 (0 'rpi.sync' in the tunings), :30 and :68 (lo has no MULTICAST; no route without eth0).
- **Correction.** Minor: 'references the per-process FrameWallClock' is a weak objection. Every process fits the same system-wide REALTIME−BOOTTIME offset (clock_recovery.cpp:118-120), so the fits agree to within fit noise.

### S14 · UNCERTAIN

- **Claim.** §7 2.5 and §8: the cam0 leader drives XVS/XHS (imx585.c:4097-4102) and cam1 can run as internal-follower (:4089-4096), so a scope on both XVS lines can confirm s_k.
- **Evidence.** The code paths are CONFIRMED (imx585.c:4089-4108@cd548ef). The meaning of the register is not. The same value, 0x30a6=0x00, is commented 'XHS/XVS out' at :4100 and 'XVS_DRV [1:0] Hi-Z' in common_regs at :408. KB working/dual-sensor/claim-check.md:118 already flags this conflict. Without the datasheet, whether the leader actually drives XVS is unverified.
- **Correction.** Mark it UNCONFIRMED. Before test 2.5 or any XVS wiring, scope the leader's XVS pin alone for frame-rate pulses. The datasheet's XXS_DRV bit table settles it.

## Missing from the synthesis

1. Frame-start IRQ coupling (PROBABLE, not modelled). Once the two sensors are locked, both CFE frame-start IRQs arrive within µs of each other. If one CPU serves both, the second timestamp is late by the first handler's run time, and which one comes second flips from frame to frame. Each loop then sees an order-dependent error, a bias plus a bimodal skew, rather than the constant CFE bias b test 2.2 assumes. Test 2.2 should look for two peaks or a gap at zero in s_k; giving the two IRQs separate CPU affinity is a system setting Patrik would change.
2. The base pin stays {d,d} (CC:2406-2415@31d5418), and §9 changes only CC:8948/:8955. In grid mode at 24/23.976/29.97 fps, every release (fps-change grace, ramp, photo mode, lock off) therefore hops HMAX between 550 and 625. Each hop costs a re-acquire, and while it lasts the foreign-HBLANK hazard is back.
3. Re-enumeration on reconfigure (CC:7439-7457, :7247): a format, HDR, colour-profile or ladder-rung change on one Core writes HBLANK on the other Core's sensor. Two mitigations are not discussed: keep one CameraManager per process across reconfigures (where the tuning file allows), or patch camera_sensor_legacy.cpp:288-296@6b0b49f3 in the fork to skip the write when another process holds the media lock.
4. Fix E is not atomic: the driver uses no register hold, so VMAX and SHR are separate CCI writes. The risk is low because both are written just after the frame start, but the design does not analyse it.
5. Clear HDR VMAX parity is unverified. The sensor spends 2 VMAX units per row there (imx585.c:3274, :3301@cd548ef), so if it needs VMAX in multiples of 4 the quantum doubles to 29.6 µs and the whole Clear HDR budget changes.
6. Shared bandwidth: both raw streams cross one RP1 link, both DNG streams go to one Gen 3 ×1 NVMe (r5-pi-hardware.md:27, :67), and both share the PiSP back-end hardware (two instances, r5:22). The drop rate, and with it D variability and index holes, is assumed to be what one sensor sees; at 2 × ~420 MB/s for Clear HDR 16-bit 4K25 that is unlikely.
7. D is not constant in practice: CFE frame skips, drops and back-end contention shift the request-to-frame mapping by ±1. Q's carry and the in-flight sum used by the acquisition stretch both assume a fixed D.
8. 'Clear HDR at 30 fps cannot lock' depends on the crystal's sign. Min VMAX 4500 is exactly 1/30 s on the sensor's clock, so a sensor that runs faster than the Pi can still lock by lengthening frames; a slower one cannot.
9. Mixed period definitions: FPL:87 and the index (CC:4643) use settings_.fps (23.976 as a decimal), while the proposed grid uses 24000/1001. The 1 ppm mismatch is negligible per take, but one T should be used everywhere.
10. Top-fps clamp: applyFrameDurations (ipa_base.cpp:1788-1792@6b0b49f3) can collapse {d,d+1} back to min==max, which re-enters the lattice. That is harmless at exact standard rates, but the new saturation test must expect it.
11. Audio on both Cores: each would sleep 220 ms (src/ApertarCoreApp.cpp:14297-14300@31d5418) and stamp its WAV with its own RecordingClock (AudioRecordingSession.cpp:243), while video timecode takes the primary's tc_offset_us. Decide whether the secondary records audio at all.
