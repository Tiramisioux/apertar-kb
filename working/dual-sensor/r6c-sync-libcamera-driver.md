<!-- Dual sensor, reader report 6c (2026-11-03/04): the phase-lock deep-dive, lens C: the actuator: libcamera's IMX585 helper and its (VMAX, HMAX) lattice, the driver's VBLANK/HBLANK/EXPOSURE handlers, SensorTimestamp and FrameWallClock, rpi.sync, the smallest VBLANK-only change. Written by a read-only research agent on the Mac (libcamera 6b0b49f3, Cinemate libcamera bfe0b76a0, driver cd548ef, KB). Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Actuator lens: libcamera and the IMX585 driver, for two IMX585 on one CM5

I read the code with `git show <sha>:<path>` and `git grep` only. Nothing was run on a Pi. Each claim carries one of these labels:

- **CONFIRMED**: seen in code, data or a log.
- **PROBABLE**: inferred; the reason is given.
- **UNCONFIRMED**: not established; what would settle it is given.

Numbers are labelled MEASURED (from the rig, through the KB), COMPUTED (from code re-implemented in a model) or ESTIMATE. A COMPUTED number is still an estimate until it is read back on the rig.

| sha | Repository (absolute path) |
|---|---|
| 6b0b49f3 | /Users/patrikeriksson/Documents/Apertar/libcamera, ref `apertar` (v0.7.1-qbcfork.20260522-9). The lattice commit 4cff9712 is an ancestor of the rig's 7e9fef0b, and the helper has not changed since then. |
| bfe0b76a0 | /Users/patrikeriksson/Documents/cinemate/libcamera |
| cd548ef | /Users/patrikeriksson/Documents/Apertar/imx585-v4l2-driver (imx585.c, imx585-overlay.dts) |
| bd57617 | /Users/patrikeriksson/Documents/cinemate/imx585-v4l2-driver (cinemate-7modes) |
| 31d5418 | /Users/patrikeriksson/Documents/Apertar/Apertar-Core (src/camera/CameraController.cpp, src/camera/FramePhaseLock.hpp) |
| 63a08d5 | /Users/patrikeriksson/Documents/cinemate/cinepi-raw |
| KB | /Users/patrikeriksson/Documents/Apertar/apertar-kb (working tree) |

**Models.** Both are in `/private/tmp/claude-502/-Users-patrikeriksson--claude-spares-spare-niESh6/f112d566-1876-4e08-9788-61e89e7de390/scratchpad/` and run with `python3 -I`.
- `lattice_sim.py` re-implements `cam_helper.cpp:82-132`, `cam_helper_imx585.cpp:118-226` and `ipa_base.cpp:1836-1839` (all @6b0b49f3), plus `imx585.c:3478-3544@cd548ef`. It reproduces all three MEASURED rig readbacks exactly.
- `lock_model.py` drives `FramePhaseLock.hpp:79-140@31d5418` with three actuator models.

**Bottom line**
1. **HMAX changes on almost every push today.** Core pins `{d,d}`, and the qbc helper then re-chooses HMAX for nearly every 1 µs change. Over 25 fps Clear HDR, ±150 µs, 299 of 300 one-µs steps change HMAX (COMPUTED). On the rig, 40000 → 40001 moved HMAX from 550 to 581 (MEASURED).
2. **One existing switch keeps HMAX fixed: a range instead of a single value.** The helper only runs its search when min == max (`cam_helper_imx585.cpp:130@6b0b49f3`). If Core pins `{d,d+1}`, only VBLANK changes, as in Cinemate, and libcamera needs no change.
3. **VBLANK-only has two costs.**
   - The driver's VBLANK handler never rewrites SHR. Integration time therefore moves by the change in VMAX (in lines) whenever the exposure value stays the same. This is true for both the Apertar and the Cinemate driver.
   - Each actuator step becomes 2 lines = 14.81 µs. With Core's integer-µs rounding, the model then cycles at ±22–45 µs, against 8–9 µs for the lattice. A staircase-aware quantiser in Core with error feedback brings it back to 8–21 µs (COMPUTED).
4. **Clocks.** SensorTimestamp is one kernel clock that both processes see. FrameWallClock is fitted separately in each process. rpi.sync has no entry in the imx585 tuning files, cannot route multicast on the rig, and its corrections go through the same lattice.
5. **Recommended minimal set:**
   - **E**: rewrite SHR in the driver's VBLANK case, and lower the per-frame `dev_info` to `dev_dbg`.
   - **A**: Core pins `{d,d+1}` for both the lock pin and the pre-roll pin.
   - **Q**: a quantiser onto even VMAX values, with error feedback, in FramePhaseLock.
   - A datum on a shared grid for the two processes.
   - B or C (libcamera changes) can come later.

## C1 — Apertar libcamera (6b0b49f3): from FrameDurationLimits to HMAX/VMAX

### C1.1 The chain (all CONFIRMED)

| # | Step | Code | What happens |
|---|---|---|---|
| 1 | Request control | `ipa_base.cpp:1312-1316` | FRAME_DURATION_LIMITS calls `applyFrameDurations` |
| 2 | Clamp and echo | `ipa_base.cpp:1780-1819`: clamp :1788-1792, echo :1795-1797, maximum exposure through `getBlanking` :1805, `sync->setFrameDuration` :1812-1818 | Both limits are clamped to the mode. The clamped `{min,max}` is echoed in metadata. |
| 3 | Per frame | `processStats` `ipa_base.cpp:522-563` | The sync offset is read at :549 (0 without rpi.sync). `applyAGC(…, offset)` runs at :560 and `setDelayedControls` at :562. |
| 4 | Blanking | `ipa_base.cpp:1836-1837` | `getBlanking(exposure, min − offset, max − offset)` |
| 5 | Base helper | `cam_helper.cpp:82-132` | `frameLengthMin = min/minLineLength` with a floor (:96-97). The frame length is clamped to `expLines + 4` within `[fmin, fmax]` (:107-108). The line is stretched only above `maxFrameLength` (:114-118). hblank is taken from `minLineLength`, which gives 0 (:120). Exposure is clipped to frame − 4 lines (:127-129). |
| 6 | IMX585 override | `cam_helper_imx585.cpp:118-226` | Gate :129-132, lattice search :134-217, exposure re-fit :219-223 |
| 7 | Sensor controls | `ipa_base.cpp:1838-1839` (exposure lines), :1847-1849 (VBLANK, EXPOSURE, GAIN), :1874-1875 (HBLANK) | — |
| 8 | Delays | `camera_sensor_properties.cpp:389-394` | All four controls have a delay of 2 frames |
| 9 | Writes | `pipeline_base.cpp:880-891`, :1431-1437; `delayed_controls.cpp:180`, :253-262, :288 | Every pushed control is marked updated. VBLANK is written first, in its own ioctl. The rest go in one batch on the CFE frame-start event. |
| 10 | Driver | `imx585.c:3510`, :3531-3532, :3479@cd548ef | VMAX = (height + vblank) & ~1; HMAX = floor(550 × (w + hblank) / w); SHR = (VMAX − exposure) & ~1 |

### C1.2 The lattice search (`cam_helper_imx585.cpp@6b0b49f3`, CONFIRMED)

- **Gate (:129-132):** `if (minFrameDuration != maxFrameDuration || mode_.maxLineLength <= mode_.minLineLength) return { vblank, hblank };`
- **Search range:**
  - The clock is 74.25 MHz (:135).
  - minHmax = 550, rounded from the minimum line length in ticks (:142).
  - capHmax = min(maxLL, 1.5 × minHmax) = 825 (:143-144).
  - The target is the requested minimum duration in ticks (:145).
- **Snap (:160-167):** if the request is within 1 µs of 1e6 / round(fps), and that exact period is a whole, even number of ticks, the target becomes the exact period. This covers 24/25/30/50/60 and excludes the NTSC rates.
- **Search (:185-202):** for h from 550 to 825, try V ∈ {the even value nearest target/h, that value + 2}, and keep the pair with the smallest |V·h − target|. An exact hit stops the search.
- **Non-exact result (:204-208):** take the lowest HMAX whose error is within halfUs = 37 ticks (:181).
- **Realisation (:215-217):** `hblank = ceil(bestH·w/550) − w` and `vblank = bestV − height`.
- **Exposure re-fit (:219-223):** `expLines = min(exposure / lineLength(newHblank), bestV − 4)`.

### C1.3 Does HMAX change on small pushes? Yes.

MEASURED on the rig in Clear HDR 16-bit at 891 MHz (KB `lessons/hardware-log.md:246-258`):

| Pin (µs) | hblank / vblank | HMAX × VMAX |
|---|---|---|
| 40000 | 0 / 3200 | 550 × 5400 |
| 40001 | 217 / 2912 | 581 × 5112 |
| 40016 | 308 / 2802 | 594 × 5002 |

COMPUTED sweeps over ±150 µs with a 20 ms exposure:

| Mode, nominal | Distinct HMAX | HMAX range | Largest change from nominal | 1-µs steps that change HMAX (median / max, ticks) | FrameDuration metadata − true period | Steady-state exposure error |
|---|---|---|---|---|---|---|
| Clear HDR 16-bit, 40000 (550 × 5400) | 53 | 550–647 | 17.6 % | 299/300 (15 / 92) | 0 to +8.84 µs | −10.5 to +6.7 µs |
| SDR 12-bit, 41666 (625 × 4950, exactly 24 fps) | 64 | 550–823 | 31.7 % | 298/300 (13 / 258) | 0 to +9.56 µs (+3.47 at nominal) | −11.6 to +6.7 µs |
| 1080p binned, 40000 | 68 | 550–783 | 42.4 % | 299/300 (18 / 227) | 0 to +18.4 µs | −15.2 to +5.8 µs |

- In Clear HDR, only 16 of the 301 requests keep HMAX at 550.
- Within ±12 µs of 40000 there are 19 different HMAX values (550–645).
- Request → HMAX: 39996→558, 39997→552, 39998→572, 39999→551, 40000→550, 40001→581, 40002→556, 40003→560, 40004→579.
- The rig's pin sat mostly at 40002 (MEASURED, `hardware-log.md:260-277`), so HMAX hops between 556, 581 and 560.

### C1.4 The exposure re-fit

- **Steady state:** the integration time stays within one line of the request: at most 0.05 % at 20 ms (COMPUTED, above).
- **Digital gain** corrects the line quantisation only in the ISP output (`ipa_base.cpp:1856-1862`), not in RAW/DNG (CONFIRMED).
- **Transition frame** (PROBABLE model): rows reset under the old line time H_old and read out under H_new get an integration error of k·r·ΔH.
  - k = 2 H per row in Clear HDR (PROBABLE, from hdr_scale at `imx585.c:3274` and :3301).
  - For the centre band (rows 1040–1104) the step is about 0.81 × ΔH/H.
  - Estimated steps: 550→581 gives 4.6 %, →594 gives 6.5 %, →610 gives 8.9 %, →645 gives 14.1 % (ESTIMATE).
- **MEASURED** (`hardware-log.md:279-293`):
  - Take C0103, lock on: band step mean 0.53 %, p99 2.85 %, max 8.9 %; 673 pushes, 10 holes, max_abs_err 199 µs.
  - Take C0102, lock off: 0.017 %, 0.058 % and 0.28 %; 0 holes.

### C1.5 Switches that keep HMAX fixed

| Switch | Status |
|---|---|
| min ≠ max (any `{d, d+k}`) | CONFIRMED as the only switch the user can drive (:130) |
| `maxLineLength <= minLineLength` | Not controllable. The driver allows hblank up to 65535 ticks (`imx585.c:3388-3393`). |
| Environment variable or tuning key | None in the helper (:118-226). The `QBC_*` variables (`pisp.cpp:878`, :3152; `raw_stats.cpp:39`) are unrelated to blanking. CONFIRMED. |
| Exposure longer than the maximum frame length | The base helper stretches the line (:114-118); irrelevant at a 180° shutter. |
| ISP minimum pixel time (`ipa_base.cpp:620-639`) | Could raise `minLineLength`, but hblank 0 at 40000 (MEASURED) shows it does not in Clear HDR at 25 fps. |

## C2 — Cinemate's fork (bfe0b76a0): VBLANK only

| Item | Apertar 6b0b49f3 | Cinemate bfe0b76a0 |
|---|---|---|
| IMX585 helper | Overrides `getBlanking` | 71 lines, no override, so VBLANK-only with hblank fixed at 0 / HMAX at the minimum (CONFIRMED) |
| Base `getBlanking` | `cam_helper.cpp:82-132` | Identical (CONFIRMED) |
| `applyAGC` | `ipa_base.cpp:1836-1837`; HBLANK :1874-1875 | `ipa_base.cpp:1693-1694`; :1718-1719 |
| Delays / VBLANK first | `camera_sensor_properties.cpp:389-394`; `pipeline_base.cpp:880-891` | :295-304 (2/2/2/2); `pipeline_base.cpp:824-827` |
| Driver VBLANK handler | `imx585.c:3506-3524@cd548ef`, writes VMAX only | `imx585.c:1449-1467@bd57617`, writes VMAX only: the same stale-SHR issue |
| Lock | Core FramePhaseLock with `{d,d}` | cinepi-raw bf717fa: "VBLANK-only — never touches HMAX/line length…" |

- **Diff of the helpers** (CONFIRMED by diffing the two `git show` outputs). Every hunk is an addition on the Apertar side; nothing was removed or changed:
  - :10-13 includes;
  - :17-19 using-declarations;
  - :27 and :64-83 `getModeSensitivity()`, which returns 1.0;
  - :30-32 the `getBlanking` declaration;
  - :94-225 the lattice comment and body.
  - `frameIntegrationDiff = 4` (:39) is common to both.
- **Cinemate's HMAX-stretch attempt** gave a "static" 4K image (KB `working/cinemate-lessons.md:40-42`). The failure is MEASURED by Cinemate; its cause is UNCONFIRMED.
- **Cinemate's VBLANK-only result** (commit 55562b6, KB `working/phaselock-answer.md:16`): +1066 ppm became −9 ppm, with "2–3 line dither (±12 µs)" and 0.03 % exposure variation.
  - Whether ±12 µs is a bound on the phase error is UNCONFIRMED.
  - The 0.03 % fits 2-line stale-SHR steps on some frames (PROBABLE).

## C3 — The driver (`imx585.c@cd548ef`)

### Registers and handlers (all CONFIRMED)

| Item | Lines | Facts |
|---|---|---|
| VMAX | :117-119 | 0x3028, 24-bit little-endian, maximum 0xfffff, default 2250 |
| HMAX | :124-125, :120-121 | 0x302c, 16-bit; Clear HDR minimum 550 |
| SHR | :135-138 | 0x3050; minimum 8, or 16 in HDR. Exposure limits :141-144. |
| Clock and link | :221, :254-285, :287-303, :305-320 | `PIXEL_RATE` is 74.25 MHz. The 4K 12-bit HMAX table gives 891 MHz → 550 (:294) and 720 MHz → 660 (:293); the 10-bit table is separate. |
| Framing limits | :3369-3407 | pixel_rate proxy = w × 74.25 MHz / min_hmax (:3382-3386); hblank range (:3388-3393); vblank range = [min_vmax − h, 0xfffff − h] (:3395-3399); exposure range (:3401-3403) |
| EXPOSURE | :3478-3488 | `shr = (imx585->vmax - ctrl->val) & ~1U`, then write SHR |
| ANALOGUE_GAIN | :3499-3500 | `dev_info` on every write |
| VBLANK | :3506-3524 | `vmax = (mode->height + ctrl->val) & ~1U`; re-ranges the exposure; `dev_info` at :3518; writes VMAX only. **No SHR rewrite.** |
| HBLANK | :3525-3544 | `hmax = min_hmax × (w + hblank) / w`; `dev_info` at :3536-3538; writes HMAX |
| Direct SHR/VMAX/HMAX controls | :3563-3586 | — |
| Control creation | :3842-3853 | No flags and no cluster. The v4l2 control core therefore skips `s_ctrl` when a value is unchanged (PROBABLE; the kernel source is not on the Mac). |
| Group hold | — | None: no 0x3001 and no "hold" register anywhere (`git grep` exit 1) |
| Sync modes | :4089-4108, :4192-4196 | Follower: EXTMODE 1, XXS_DRV 0x03, OUTSEL 0x08. Leader: EXTMODE 0, XXS_DRV 0, OUTSEL 0x0A. External: XXS_DRV 0x0F. XMSTA = 0 unless external. The overlay default is internal-leader (`imx585-overlay.dts:67`). |

### Line time per mode at 891 MHz

The arithmetic is COMPUTED from CONFIRMED mode entries.

| Mode (entry) | Size | Minimum HMAX | Pixel-rate proxy | µs per line | One VMAX step (2 lines) | Minimum VMAX | Minimum VBLANK | Maximum fps | Readout (ESTIMATE) |
|---|---|---|---|---|---|---|---|---|---|
| 4K Clear HDR 16-bit (:1719-1728) | 3840×2200 | 550 | 518.4 MHz | 7.4074 | 14.815 µs | 4500 (2250 × hdr_scale, :3301) | 2300 | 30.00 | about 4400 H = 32.6 ms (k = 2, PROBABLE) |
| 4K SDR 12-bit (:1075-1084) | 3840×2160 | 550 | 518.4 MHz | 7.4074 | 14.815 µs | 2250 | 90 | 60.00 | 2160 H = 16.0 ms |
| 1080p 2×2 binned 12-bit (:1065-1074) | 1920×1080 | 550 (4K 12-bit table, hmax_div 1) | 259.2 MHz | 7.4074 | 14.815 µs | 2250 | 1170 | 60.00 | UNCONFIRMED (8 or 16 ms) |

- **Binned mode does not double the frame rate.** All 158 mode entries have hmax_div = 1, so the code does not do what README:121 claims (CONFIRMED).
- **Link frequency.** The overlay default is 720 MHz (`imx585-overlay.dts:77-78`), which gives HMAX 660, 8.889 µs per line and 17.78 µs per VMAX step. The rig runs at 891 MHz (KB `working/dual-sensor/r5-pi-hardware.md`, config.txt:42).
- **Exact rates at HMAX 550** (COMPUTED):
  - 25 fps = 5400 lines, 50 fps = 2700, 30 fps = 4500 and 60 fps = 2250. All are even, so all are exact.
  - 24 fps = 5625 lines, which is odd. Hence the lattice's 625 × 4950, and VBLANK-only must alternate between 5624 and 5626.

### What an HMAX change does mid-stream

1. **No group hold** (CONFIRMED). VBLANK is written in its own I2C transaction, and HBLANK, EXPOSURE and GAIN follow in a batch, all on the frame-start event (CONFIRMED). Whether they all land before the sensor latches the same frame is UNCONFIRMED; the datasheet's REGHOLD semantics would settle it.
2. **Line time and readout skew change.** Clear HDR readout is 32.6 ms at HMAX 550, 36.1 ms at 610 and 38.2 ms at 645 (ESTIMATE).
3. **The transition frame gets a row-dependent exposure ramp** (C1.4). This is PROBABLE; the MEASURED 8.9 % maximum matches a 550→610 change.
4. **Stale SHR on VBLANK-only changes.** The integration becomes VMAX_new − SHR_old = exposure + ΔVMAX lines. The code path is CONFIRMED in both drivers; the consequence is PROBABLE (KB `working/port-raw/critic-ramp.md:16`, K6).
   - One 2-line step is 14.8 µs: 0.074 % at a 20 ms exposure and 1.5 % at 1 ms (COMPUTED).
5. **Kernel log load.** Each push of the lattice logs 2–3 kernel lines through `dev_info` (VBLANK, HBLANK, gain), so C0103 produced about 1.3–2k lines (ESTIMATE). Whether this is linked to the holes is UNCONFIRMED.
   - VBLANK-only keeps hblank constant and, at a fixed HMAX, the exposure lines constant. So only VBLANK is written, and its log line remains (CONFIRMED logic).

## C4 — SensorTimestamp and FrameWallClock

| | SensorTimestamp | FrameWallClock |
|---|---|---|
| Source | `ktime_get_ns()` in the rp1-cfe frame-start interrupt (kernel-rpi@5bd564a cfe.c:692, vb2 timestamp :714, `TIMESTAMP_MONOTONIC` :1950). CONFIRMED by the KB (`working/port-raw/p2-phaselock-core.md:39` and verifier row 6); not re-read, because the kernel tree is not on the Mac. | A per-CameraData ClockRecovery fit from BOOTTIME to REALTIME (`pipeline_base.h:181`, first sample `pipeline_base.cpp:717`). In `clock_recovery.cpp`: `addSample` :109-126, fit :197-202, reset on error :153-162, jitter clamp :171-172. Defaults in `clock_recovery.h:18-19`: 100 samples, 2 µs jitter, minimum 10, 50 µs threshold. |
| Path into metadata | `pisp.cpp:2226-2243`, buffer timestamp. `v4l2_videodevice.cpp:1899-1900` builds it as `tv_sec·1e9 + tv_usec·1000`, so it is quantised to 1 µs (CONFIRMED). | `pisp.cpp:2226-2243`, `getOutput(sensor timestamp)` |
| Meaning | Frame start = readout of the first line. It is not the exposure start that `control_ids_core.yaml:778-788` documents (PROBABLE). | A REALTIME estimate of the same instant |
| Clock | MONOTONIC, which equals BOOTTIME when there is no suspend. NTP slews it but never steps it (PROBABLE). | REALTIME, which NTP can step |
| Shared by two processes? | **Yes.** It is one kernel clock, and each CFE instance stamps in its own interrupt handler. The call is CONFIRMED; the interrupt-latency difference between the instances is UNCONFIRMED. | **No, not at the µs level.** There are two independent fits (CONFIRMED). The size of the difference is UNCONFIRMED; the 50 µs reset bounds it. |
| Used by Core | As the lock reference (`CameraController.cpp:8775@31d5418`) | Not at all (`git grep` exit 1) |

## C5 — rpi.sync (6b0b49f3)

| Fact | Code | Label |
|---|---|---|
| Defaults: group 239.255.255.250, port 10000, a packet every 30 frames, ready after 100 frames, minimum adjustment 50 µs | `sync.cpp:49-53` | CONFIRMED |
| The reference is FrameWallClock in µs (filled at `ipa_base.cpp:1566-1577`) | `sync.cpp:167`, :174 | CONFIRMED |
| Server: estimates the next frame's wall time and sends it every 30 frames; ready countdown | `sync.cpp:189-235` (:200-206, :212-227, :229-233) | CONFIRMED |
| Client: correction from the phase difference (:256-262), dropped below 50 µs (:263-264), applied as `frameDurationOffset` for **one frame** (:274), ready (:277-282) | `sync.cpp` | CONFIRMED |
| The IPA subtracts the offset from both limits in `applyAGC`, so it is the same `getBlanking` call. With `{d,d}` the lattice re-chooses HMAX for the correction frame, and again when the correction ends. | `ipa_base.cpp:549`, :1836-1837 | CONFIRMED |
| An error is logged on **every frame** while sync is active and min ≠ max | `ipa_base.cpp:546-548` | CONFIRMED |
| SyncReady and SyncTimer metadata; SyncFrames `ControlInfo(100, 100000, 1000)` | `ipa_base.cpp:551-553`, :92 | CONFIRMED |
| SyncMode's ControlInfo lists only Off and Client, yet the control handler also accepts Server | `ipa_base.cpp:88-91`, :1501-1512 | CONFIRMED |
| imx585.json and imx585_mono.json have no `"rpi.sync"` block (imx477.json:1269-1271 has one). No algorithm is created, so SYNC_MODE does nothing. | `ipa_base.cpp:1502-1504` | CONFIRMED |
| On the rig there is no multicast route without eth0, and `lo` is not MULTICAST | KB `r5-pi-hardware.md` | MEASURED (KB) |
| Core sets no SyncMode or SyncFrames and reads no SyncReady | `git grep` exit 1 @31d5418 | CONFIRMED |

### A one-frame correction through each path (COMPUTED, 20 ms exposure)

| Offset (µs) | 25 fps Clear HDR, lattice HMAX | 24 fps SDR, lattice HMAX (nominal 625) | VBLANK-only, 25 fps |
|---|---|---|---|
| +50 / −50 | 553 / 555 (+0.55 / +0.91 %) | 561 / 570 (−10.2 / −8.8 %) | −8 / +6 lines (−59.3 / +44.4 µs) |
| +60 / −60 | 564 / 561 | 566 / 585 | −10 / +8 lines |
| +200 / −200 | 597 / 603 (+8.6 / +9.6 %) | 560 / 571 | −28 / +26 lines |

- Over this range, the HMAX change is +0.18 % to +9.64 % at 25 fps and −6.4 % to −11.7 % at 24 fps. Each correction causes two transitions.
- VBLANK-only moves 6–28 lines for offsets of 50–200 µs.
- rpi.sync holds a ±50 µs band. It corrects phase only, never frequency.
- How often it corrects depends on the crystal offset between the two sensors (UNCONFIRMED). For comparison, at the MEASURED sensor-to-Pi offset of 1.2–1.6 ppm, the error would reach 50 µs about every 30–40 s (ESTIMATE).

## C6 — The minimal change for VBLANK-only pushes

| Option | Where | Change | Gain | Risks | Verdict |
|---|---|---|---|---|---|
| **A** | `CameraController.cpp:8948@31d5418` (lock pin) and :8955 (pre-roll pin) | Pin `{d, d+1}`. For the pre-roll pin, either `{p, p+1}` or skip it while the lock pin is set. The pre-roll pin is written after the lock pin (:8954-8958 follows :8947-8952), so it overrides it (CONFIRMED). | The gate at :130 returns the base result: HMAX stays at 550, and both sensors get the same line time. No libcamera rebuild. Takes with the lock off keep `{d,d}` (:2406-2415) and the exact 24 fps snap. | (1) The 14.8 µs staircase gives a limit cycle in the model (table below); Q is needed. (2) FrameDuration metadata reads +7.41 µs high when the floor gives an odd frame length. (3) The saturation check (:8841-8842) only looks at echoes where [0] == [1]. It still fires when both limits clamp to the mode minimum, which is its design case, but it misses d < modeMin ≤ d+1. (4) At a 360° shutter, fmax can add 2 lines. (5) Stale SHR; E is needed. (6) HMAX switches once when the lock arms or releases (625 ↔ 550 at 24 fps), in preview. | **Yes, with Q and E** |
| **Q** | `FramePhaseLock.hpp:127-139` (`llround` at :129), or `CameraController.cpp:8854-8855` | Quantise onto even VMAX with error feedback: `q = r + carry; V = 2·round(q / 2H); carry = q − V·H`. Push `d = ceil(V·H)` as `{d, d+1}`. | The model error drops to ±8–21 µs. FrameDuration becomes exact, because V is even. The 24 fps mean is exact (5624/5626). | Needs H for each mode: either (w + hblank) / PIXEL_RATE read from the subdev, or a table (550 / 74.25 MHz at 891 MHz, 660 at 720 MHz). Which source Core can use is UNCONFIRMED. `ceil` must stay less than one line above V·H; the floating-point floor check found 0 mismatches for 8000–200000 µs (COMPUTED). | **Yes** |
| B | `cam_helper_imx585.cpp`: members near :34-40, skip :169-208 near an anchor | Sticky HMAX: keep the anchor's HMAX within about ±250 µs of the anchor; VMAX = the nearest even value | Exact 24 fps with the lock off (625 × 4950), and VBLANK-only pushes (16.84 µs steps) | `getBlanking` is const (`cam_helper.h:82`), so the state must be `mutable`. It is called from three places (`ipa_base.cpp:678`, :1805, :1836@6b0b49f3), so state may only change on the per-frame path. `setCameraMode` is not virtual (`cam_helper.h:73`), so the anchor must be keyed on `mode_`. Needs a libcamera rebuild. A stateless variant has no anchor for NTSC rates. It is still a staircase, so Q is still needed. | Later |
| C | `cam_helper_imx585.cpp:130-132` | Environment opt-out `QBC_IMX585_EXACT_FPS=0`, in the fork's style (`pisp.cpp:878`, :3152; `raw_stats.cpp:39`) | VBLANK-only for the whole process, in one line | Needs a rebuild. It also removes the snap when the lock is off: 24 fps +178 ppm (5624 lines), SDR 30 fps +444 ppm (4498), 23.976/29.97 +112 ppm. 25/50 stay exact; 60 fps and Clear HDR 30 clamp to the mode minimum and stay exact (COMPUTED). Without Q it has the same staircase limit cycle. | Fallback only |
| D | Core | Push only exact even-VMAX multiples under `{d,d}` | — | The lattice still wins: 5 of the 21 even VMAX values from 5380 to 5420 (5384, 5388, 5412, 5414, 5416) cannot be reached at HMAX 550 (COMPUTED) | Reject |
| **E** | `imx585.c:3506-3524@cd548ef`; also `imx585.c:1449-1467@bd57617` | In the VBLANK case, after updating `vmax`, write `SHR = (vmax − exposure->val) & ~1`, clamped (:135-138), in the same ioctl. Change `dev_info` to `dev_dbg` at :3499-3500, :3518 and :3536-3538. Variant E′: set `V4L2_CTRL_FLAG_EXECUTE_ON_WRITE` on EXPOSURE (:3842-3853); this works because `applyAGC` pushes EXPOSURE every frame (`ipa_base.cpp:1847-1849`, `delayed_controls.cpp:180`) (PROBABLE). REGHOLD around the group is optional; its register is UNCONFIRMED. | Integration stays constant across VMAX changes for every VBLANK-only actuator: Core A/Q, Cinemate and rpi.sync. If the batch slips a frame, VMAX and SHR are still consistent (PROBABLE). | Driver rebuild (DKMS). Affects every user of the driver. | **Prerequisite** |

### Lock error by actuator (`lock_model.py`, COMPUTED)

Sensor offsets of 0.5–1066 ppm, no timestamp jitter, maximum / RMS over the last 3000 frames:

| Actuator | 3-frame loop delay | 7-frame loop delay |
|---|---|---|
| 1-µs, like the lattice (today) | 8–9 / 3.6–4.6 µs | 10–13 / 3.1–5.9 µs |
| A alone (floor staircase) | 22–45 / 12.1–23.6 µs | 52–107 / 28.8–43.0 µs |
| A + Q | 8–21 / 4.3–7.7 µs | 13–23 / 5.1–11.4 µs |

- Centring the staircase with a +7 µs pin bias does not help (22–41 µs); the error feedback is what helps.
- The true loop delay is UNCONFIRMED: 2 frames of sensor delay plus the depth of the request queue (KB `critic-ramp.md:16` K5 says about N+2).
- The rig measured ±22 µs with the lattice (`hardware-log.md:260-277`), so the model underestimates the rig by about 2–2.5× (ESTIMATE).

**Recommendation: E, A and Q now, with no libcamera rebuild.** The lattice's exact open-loop rate does not matter while the lock disciplines the mean rate. Use B later if exact rates with a fixed HMAX are wanted with the lock off.

### Cheap tests that would settle the open points

| Test | Settles | Expect |
|---|---|---|
| Re-analyse the C0103 band step against row (top, centre, bottom) | The k·r·ΔH ramp model | Step proportional to row: about 0 at the top, about 2× the centre at the bottom |
| One lock take with `{d,d+1}`, reading `v4l2-ctl --get-ctrl hblank,vblank` | HMAX stays fixed; holes | hblank 0 throughout; band step near C0102 except for 2-line SHR steps |
| A 1 ms shutter with VBLANK-only dither, before and after E | Stale SHR | About ±1.5 % luma steps before E, none after |
| `dmesg \| grep -c imx585` per take; `console=` in `/proc/cmdline`; `/proc/sys/kernel/printk` | Kernel log load from `dev_info` | 2–3 lines per push with the lattice |
| Standard deviation of SensorTimestamp intervals at a fixed pin, lock off | Frame-start interrupt jitter in the precision budget | — |
| `ip route get 239.255.255.250`; `ip link show lo` | Whether rpi.sync can run at all | No route (per KB r5) |
| Two processes on csi0 and csi1 on the same grid: histogram of \|t0(k) − t1(k)\| | The relative budget | — |

## Implications for dual-sensor sync

1. **Both sensors must be VBLANK-only.** Under the lattice, each lock picks its own HMAX every frame.
   - In Clear HDR (about 4400 H of readout, PROBABLE), one tick of HMAX difference shifts the bottom row by 59 µs. The typical 556/581 pair shifts it by 1.48 ms, and 550/645 by 5.6 ms (COMPUTED).
   - With HMAX 550 on both, rows agree to within the crystal difference, for example 0.65 µs at 20 ppm (ESTIMATE).
2. **E is a prerequisite.** Otherwise each sensor's integration moves by ±2 lines, independently, on every VMAX step.
3. **Q (or B + Q) is needed** to keep each sensor's lock about as tight as the lattice: 8–21 µs, against 22–45 µs for A alone (COMPUTED).
4. **Time on SensorTimestamp only.** It is one domain for both processes. Never use FrameWallClock, which is fitted per process, or FrameDuration metadata, which is up to +18.4 µs high under the lattice and +7.41 µs high on odd frame lengths with VBLANK-only.
5. **A shared datum is needed.** `arm()` sets `originNs = referenceNs` (`FramePhaseLock.hpp:149@31d5418`), so two processes lock to an arbitrary relative phase.
   - Use a common grid instead: origin = the nearest k·P on the shared clock, with the same P in both processes (the same fps value; `periodNs` at :87).
   - This needs no IPC, and recording can start on an agreed grid index, which replaces rpi.sync's SyncReady.
6. **Pull-in on a shared grid.**
   - The starting error is at most P/2, which is 20 ms at 25 fps; the preview re-arms only above P/2 (:112-117). The servo can correct at most 150 µs per frame, and the integrator saturates at clamp/ki = 100,000 µs·frame (:120-121).
   - In the model, reaching |e| < 50 µs takes 230–260 frames (9–10 s at 25 fps), with a 1.7–1.9 ms overshoot. From a 2 ms start it takes about 120–140 frames, with 0.43–0.49 ms of overshoot (COMPUTED).
   - Pull in during preview. A one-frame VBLANK phase jump first would cut this to a few frames (PROBABLE). It needs E. Clear HDR can shorten a 40 ms frame by at most 6.67 ms per frame; lengthening is limited only by VMAX 0xfffff.
7. **Precision budget (ESTIMATE).**
   - Per sensor with A + Q: about ±22–50 µs maximum, from the rig's lattice ±22 µs scaled by the model ratio of 1–2.3.
   - Relative between the two sensors: ±45–100 µs at worst, about 6–16 µs RMS, plus the 1 µs timestamp quantum and frame-start interrupt jitter (UNCONFIRMED).
   - A alone: up to ±44–214 µs relative.
   - For scale, ±45 µs is 6 lines, or 0.11 % of a 25 fps frame.
8. **Different shutters.** SensorTimestamp marks the start of readout. To align exposure midpoints, set FS0 − FS1 = (exp0 − exp1) / 2 (PROBABLE).
9. **Latency.** At least 2 frames of sensor delay (`camera_sensor_properties.cpp:389-394`) plus the request queue. Keep the same queue depth in both processes; a longer delay inflates the limit cycle (table in C6).
10. **Do not use rpi.sync.**
    - It has no entry in the imx585 tuning files, and multicast cannot be routed on the rig.
    - It holds only a ±50 µs band, and each correction is a one-frame step: 0.2–11.7 % in HMAX, or 6–28 lines in VMAX.
    - Its reference is FrameWallClock, fitted per process.
    - With `{d,d+1}` it logs an error every frame, and it would fight the Core lock.
11. **The hardware alternative is XVS.** The driver has leader and follower modes (`imx585.c:4089-4108`, :4192-4196; overlay `imx585-overlay.dts:67`). That would give sub-line relative sync (ESTIMATE), with the Core lock running only on the leader.
    - It needs XVS wired between the modules; whether the Waveshare Mini Base Board A routes it is UNCONFIRMED.
    - How the follower handles VMAX and FrameDurationLimits in slave mode is UNCONFIRMED; the datasheet would settle it.
12. **Both processes run the same qbc libcamera.** Any libcamera-side switch (C) must be set in both processes. Option A needs no switch.
13. **Outside this lens:** dual operation needs csi1 enabled; it is disabled today, and cam1 is on i2c@70000 (KB r5).