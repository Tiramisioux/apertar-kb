# r1-ramp-cinemate — speed ramping (fps change mid-take), Cinemate side

Reader r1. Commits read: cinemate @d6cc93e, cinepi-raw @63a08d5, cinemate-handbook @c99ff77,
libcamera(cinemate) @bfe0b76, apertar-core @25397cd (clearhdr-fixes; base f60e301). Every cited
line was opened. Tags: CONFIRMED (line read), PROBABLE (inferred, reason given), UNKNOWN.
Abbreviations: CC = cinemate/src/module/cinepi_controller.py, RL = cinemate/src/module/redis_listener.py,
CPC = cinepi-raw/cinepi/cinepi_controller.cpp, DE = cinepi-raw/cinepi/dng_encoder.cpp,
CS = cinepi-raw/cinepi/cinepi_sound.cpp, PLC = cinepi-raw/cinepi/phase_lock_core.hpp,
ACC = apertar-core/src/camera/CameraController.cpp. No code copied; logic described.

---

## 1. Operator path: `set fps` → Redis → cinepi-raw → libcamera

**Entry points.** CLI `set fps <v>` maps to `set_fps(float)` (cinemate/src/module/cli_commands.py:69@d6cc93e). CONFIRMED.
`set_fps_double` (CC:4074-4117) and the "experimental" `_ramp_fps` (CC:4119-4138) both end in `set_fps`. CONFIRMED.
Docs: cinemate/docs/speed-ramping.md:7-25@d6cc93e names all three. CONFIRMED.

**`set_fps(value, update_user_target=True)` (CC:1747-1857@d6cc93e), in order.** CONFIRMED each line:
1. `fps_lock` and not `lock_override` → return (:1756-1758). The only lock; recording is NOT a gate.
2. Writes `fps_user` immediately for the GUI (:1763-1764).
3. Value choice: sync mode 1 or `fps_free` → clamp [1, fps_max] (:1776-1778); else snap to the nearest entry of the dynamic step table (:1780-1785).
4. In-take ceiling `_in_take_fps_ceiling()` (:904-930): returns a cap only when dynamic resolution is enabled, priority != none, recording, and a desired mode exists; the cap is `max_fps_for_context(... restrict_to_family_of=self.sensor_mode)` (:925-930). Applied at :1792-1797; `capped_by_take` remembered.
5. **ff59dd8** rule ("one question, asked about the answer"): `_maybe_apply_dynamic_resolution_for_fps(safe_value)` is called with the fps that will actually be commanded (:1799-1810). Mid-take the ladder is pinned to the running mode's class (`restrict_to_family_of=self.sensor_mode if recording`, :988-1000); a class change that would be needed is deferred (`dynamic_resolution_deferred=True`, :1002-1016); a same-class substitution is a live reconfigure (:1041-1061) — `_resolution_change_needs_restart()` returns False while recording (:2782-2783).
6. `dynamic_resolution_deferred_fps` = the pre-cap request when capped (:1814-1816); `_settle_deferred_dynamic_resolution()` (:2378-2416) re-issues it after the take (called from stop_recording path at :2376), but not while buffered frames are still flushing (:2395-2399).
7. `current_fps` set and **Redis key `fps` written** (:1827-1828). This is the only thing cinepi-raw reads for cadence.
8. Shutter handling (§2), `shutter_angle_actual` + `exposure_time` keys written (:1844-1852). `self.fps = int(round(current_fps))` (:1854).

**Mid-take dynamic-resolution consequence.** A same-class live reconfigure writes `cam_init` (CC:2711) and warns "cinepi-raw will split the recording" (CC:2691-2696). cinepi-raw: `configChanged()` → if recording: stop, close folder, stop sound, advance clip number (cinepi-raw/cinepi/cinepi_raw.cpp:68-76@63a08d5), restart camera, create a new clip folder, restart sound, `resetFrameCount()`, resume (cinepi_raw.cpp:365-375). CONFIRMED. So a ramp that crosses a mode's ceiling inside the pinned class yields **two clip folders and two WAVs**, not one ramped clip.

**`set_fps_double` (CC:4074-4117).** Target = `self.fps*2` (integer fps, :4081); picks a mode via `_select_resolution_mode_for_fps` (:2431-2461, same `choose_resolution` + priority, pinned while recording); if the mode differs and recording → warning + return, no fps change (:4083-4089, :4106-4112). Off-take it switches mode (`set_resolution(..., restart_process=False)`) then clamps to `fps_max` and calls `set_fps` (:4095-4100). Restoring uses `fps_saved`/`sensor_mode_saved`. CONFIRMED. Net: while recording, the double button works only if the doubled rate fits the current mode.

**`_ramp_fps` (CC:4119-4138).** Steps `self.fps` by ±1 with `time.sleep(ramp_up_speed|ramp_down_speed)` = 0.2 s each (:270-271), target `min(fps_temp*2, fps_max)` where `fps_temp` is a constant 24 (:273) — i.e. it ramps to 48 regardless of the current fps. No caller anywhere (grep `_ramp_fps(`: only the definition). CONFIRMED dead/experimental. A 24→48 ramp = 24 steps × 0.2 s = 4.8 s, 24 `fps`+`fps_user` publishes.

**How the value reaches the sensor.** cinepi-raw subscribes `CHANNEL_CONTROLS` (CPC:1188) and dispatches by published key name to a handler map (CPC:1158-1166). Handler for `fps` (CONTROL_KEY_FRAMERATE = "fps", cinepi-raw/cinepi/cinepi_state.hpp:30): `framerate_ = stof`, `options_->framerate = framerate_`, builds FrameDurationLimits = {1e6/fps, 1e6/fps} as `long int` (truncating: 24 → 41666 µs), `app_->SetControls(cl)` (CPC:968-979). CONFIRMED. No recording gate; no ExposureTime touched there.
`RPiCamApp::SetControls` merges into `controls_` under `control_mutex_` (cinepi-raw/core/rpicam_app.cpp:1097-1106); `queueRequest` moves `controls_` into the next request's controls (rpicam_app.cpp:1020-1023) — i.e. a control is attached to exactly one request, and the IPA holds it thereafter. CONFIRMED. Per-frame instantaneous `framerate` = 1e9/Δ SensorTimestamp (rpicam_app.cpp:1244-1252) is what cinepi-raw publishes as `framerate` in cp_stats (CPC:637) → cinemate `fps_actual` (RL:1492-1494). CONFIRMED.
Startup: `sync()` reads `fps` with `stoi` (integer!) (CPC:216-218) and seeds `options_->framerate` (CPC:448). CONFIRMED. PROBABLE consequence: a fractional fps written before launch is floored at start, corrected only by the next live `fps` publish (stof).

---

## 2. Shutter policy under a ramp

**Modes.** `shutter_a_sync_mode` 0/1, default 0 (CC:214); toggled by `set_shutter_a_sync_mode` (CC:1528-1546): entering mode 1 stores `exposure_time_nominal = (shutter_angle_nom/360)/current_fps` and switches the angle table to 0.1° free steps (`sync_increment`, :1540-1541, :349); mode 0 rebuilds the flicker-free table (:1543). CONFIRMED.

**Recomputation in `set_fps` (CC:1831-1852).** Mode 0: rebuild dynamic angle steps for the new fps and snap `shutter_angle_actual` to the nearest (:1831-1837) — "keep motion blur". Mode 1: `shutter_angle_actual = round(exposure_time_nominal × fps × 360, 1)`, clamped to [1, 360] (:1839-1842) — "keep exposure time". Then `exposure_time_s = (angle/360)/fps` and both `shutter_angle_actual` and `exposure_time` keys are written (:1844-1852). Same math in `update_fps` (CC:3458-3476). Nominal-angle edits in mode 1 refresh `exposure_time_nominal` (CC:1722-1727, :3228-3230) and `set_shutter_a` does too (CC:3159-3172, the F-shutter-sync-nominal-stale fix). CONFIRMED. Docs text (speed-ramping.md:27-35) matches; the 1–360° clamp wording came from befb2f3 (2026-08-26). CONFIRMED.

**What actually reaches the sensor — the gap.** cinepi-raw recomputes ExposureTime only in the `shutter_a` handler (`shutter_speed_ = 1/((framerate_×360)/angle)`, CPC:851-859) or `shutter_speed` handler (:861-868). `set_fps` never writes `shutter_a`: the key is written only by `set_shutter_a` (CC:3146) and `set_shutter_a_nom` (CC:3250) (grep of all cinemate/src: no other writer). `shutter_angle_actual` and `exposure_time` have no cinepi-raw handler (handler map CPC:744-1060: keys are shutter_a/shutter_speed/fps/...; `shutter_angle_actual` is read only by simple_gui.py:916). The helper that would re-push the angle, `update_shutter_angle_for_fps` (CC:1707-1719), has no caller. CONFIRMED.
Consequence (PROBABLE — the three facts above plus libcamera's sticky controls): across any `set fps`, the sensor keeps its **previous absolute ExposureTime** in both modes until the operator next touches the shutter. Mode 0's "constant angle" is therefore a GUI statement; the sensor behaves like mode 1 (constant time). Mode 1 matches by accident. Ramping up, libcamera clamps exposure to the frame length (`frameLengthLines = clamp(exposureLines + frameIntegrationDiff, ...)` and "Limit the exposure to the maximum frame duration requested", libcamera/src/ipa/rpi/cam_helper/cam_helper.cpp:107-108,:123-124@bfe0b76). CONFIRMED (clamp exists); the brightness step the operator sees is UNKNOWN (no hardware log entry found; handbook grep for ramp/mid-take fps: none).

**cinepi-raw on an fps change mid-take:** nothing exposure-related happens (CPC:968-979). CONFIRMED.

---

## 3. What the written files do under a ramp

**DNG FrameRate tag 0xC764.** Per frame, at write time, from `options_->framerate` (live Redis fps as last published; CPC:971), numerator = round(fps×1000), denominator 1000 (DE:1678-1692). CONFIRMED. History: 4c1c66e (2025-07-04) wrote it from per-frame FrameDuration metadata with a `--framerate` fallback (diff: fpsRat[0] = fps + 0.5 — a /1000 bug); **210d0fb** (2026-06-05, "silence all compiler warnings") removed the metadata path and fixed the ×1000 (diff hunk @952-973), reasoning "sensor delivers the nominal rate exactly"; 3c6477e (2026-08-26) made the TC base use the same source. CONFIRMED (bodies read). PROBABLE: the tag follows the ramp with an encode-queue lag — `options_->framerate` is read when the encode worker reaches the frame, not when it was captured (queue depth = RAM buffer; DE:444-475 queues, dng_save reads live), so the first N frames after a step can carry the new rate (N = frames in flight at that moment, UNKNOWN on hardware).
Playback reads the tag from the take's FIRST frame only (cinemate/src/module/app/playback.py:163-180; dng_preview.py:209-221 "the only per-frame fps record on disk") and notes that conform mode plays ramps correctly "with no rate logic" (e0f1cae body). CONFIRMED.

**Timecode.** Clip origin (first frame): `tc_fps_ = lround(options_->framerate)` from the CONFIGURED rate (3c6477e), FrameDuration fallback in µs (07504d0), wall-clock HH:MM:SS plus sub-second frame seed (DE:2062-2121). Later frames: `raw_elapsed = llround(Δts_µs × tc_fps_ / 1e6)`, `tc_frame_count_ += max(1, raw_elapsed)`, `dropped_frames_ += raw_elapsed-1 when ≥ 2` (DE:2126-2136; 7da7ad6 elapsed-µs, dcd2b65 per-frame ts under encode_mutex_, 05eb4a0 unbiased counter). The BCD TC is `tc_frame_count % tc_fps_` etc. (DE:1710-1716). `tc_fps_` is set once per clip (DE:2119) and reset only by `resetFrameCount` (dng_encoder.hpp:123-124). CONFIRMED.
Numbers under a step (tc_fps_ fixed at the start rate):
- 24→48 (ramp up): Δ=20833 µs → raw_elapsed = llround(0.49998) = 0 → +1 per frame. TC advances 48/s against a 24 base: TC runs 2× wall clock, no holes. 25→50: 0.5 → llround = 1, same outcome.
- 48→24 (ramp down): Δ=41667 µs → raw_elapsed = 2 → **+1 droppedFrames per frame for the rest of the take**; TC skips every other count. 50→25 identical.
- Generally false holes whenever Δ×tc_fps_ ≥ 1.5, i.e. new fps ≤ start fps/1.5. CONFIRMED arithmetic from the cited lines; PROBABLE as a hardware prediction.

**File numbering.** `index_++` per queued frame (DE:474), 9-digit suffix (DE:2340-2341); independent of fps. `frameCount` in stats (CPC:640) is the same counter. CONFIRMED. A mid-take class/mode split resets it (cinepi_raw.cpp:371-372).

**WAV.** PCM is never retimed: ffmpeg `-c:a copy` plus BEXT metadata only (CS:1527-1538; log lines "leaving PCM untouched" CS:1386,1393). Metadata frame rate = take-start rate: `takeStartFramerate_` parsed from the clip name at `record_start()` with `configuredFramerate()` (CS:816-820, :291-295), else `nominalTimecodeFramerate(configured)` = round(fps) (CS:149-154, :1407-1410). `time_reference` samples derived from that rate (CS:185-205, :1518-1521). Audio start offset in frames uses the same nominal rate (CS:1511-1515). CONFIRMED. So a ramp leaves the WAV honest in wall time and stamped with the start fps; the DNG TC (frame-count based, §above) diverges from the WAV TC by (frames_actual − fps_start×t) after the step. Dual-sensor/WAV behaviour under a mid-take split: new WAV per clip folder (cinepi_raw.cpp:72-74,:369). CONFIRMED.

**Post-take analysis (RL `analyze_frames`, :1659+).** Expected frames = integral of the fps timeline: segments appended on every `fps`/`fps_user` key change while recording (RL:1452-1460 → `_note_expected_fps_change` :604-621), integrated over active (non-paused) seconds (:642-691; comment "speed ramps are counted" :1831-1833). CONFIRMED. But `_note_expected_fps_change` also calls `_suppress_live_sync_for_current_take("FPS changed during recording")` (:620) which forces `frames_in_sync = ... or sync_warning_suppressed` (:1866-1870) and logs "Skipping frame-sync warning because FPS or resolution changed during this take" (:1985-1988). CONFIRMED. Final tolerance default 1 frame (:102-105). 56bf88c (2026-06-05) made the live latch shortfall-only and frame-limited takes use the requested slot count (body read). CONFIRMED.
Verdict under a ramp: **no false DROP/SYNC verdict** (suppressed), and **no true one either** — a genuine drop in a ramped take is only visible via `missing_frame_count`/`DROP_FRAME_DURING_LAST_TAKE` (:1904-1911, file count vs integrated expectation, still computed) and the log lines :1948-1976. The ramp-down false `droppedFrames` from cinepi-raw feed `drop_frame_count`/`tc_hole_count` (:1915-1924) and, live, Tier-1 drop flashes (RL:1004-1024) once the `user_changing_fps` leeway (max(0.5 s, 2/fps), RL:1153-1169; gate :995-1000) expires — i.e. a 48→24 step produces a drop flash every frame for the remainder of the take. PROBABLE (arithmetic §TC + gate read; not hardware-confirmed). Logged as "TC timing: N late-arrival event(s)... no data lost" when files are all present (:1940-1952). CONFIRMED.

---

## 4. Phase lock interplay

`updatePhaseLock` reads `fps_user` every frame (CPC:1221-1236, hpp:116-119); `phaseLockStep` re-arms whenever `|target − state.targetFps| > 1e-6` (PLC:96-111): new base period, integral 0, datum = this frame, `lastDurUs = -1`, **no control pushed on the re-arm frame** (returns `rearmed`). Next frame: servo runs, `durUs = lround(reqDurUs)` ≠ −1 → pushes FrameDurationLimits (PLC:120-164). Unit test `test_fps_change_rearms` (cinepi-raw/tests/phase_lock_core_test.cpp:256-265). CONFIRMED.
Two writers after a step: the Redis `fps` handler (subscriber thread) pushes the truncated 1e6/fps (24 → 41666), the servo (capture thread) pushes lround(1e6/fps) (→ 41667) one frame later; both go through `SetControls` and the later one lands on the next request (rpicam_app.cpp:1020-1023). PROBABLE ordering (threads not traced); harmless, ±1 µs.
Stepped ramp (`_ramp_fps`, 1 fps per 0.2 s): each step re-arms; at 24–48 fps a 0.2 s step is 5–10 frames, with kp=0.06/ki=0.0015 (PLC:27-32 per p1 report) the loop never converges before the next re-arm; the phase datum is reset 24 times, so the lock contributes nothing during the ramp and re-converges only after the last step. PROBABLE (from the law; no sim run). While recording, a >1.5-period gap is absorbed, not re-armed (PLC:96-97,:113-118) — a ramp DOWN step (Δ = 2 old periods at 48→24) would look like a gap, but the fps change re-arms first, so no phantom "missed" frames are added. CONFIRMED order (:99 before :113).

---

## 5. Git history and handbook

cinemate (`git log --all -S`, bodies read):
- `set_fps_double` present since the earliest reachable history (1bd592d merge, a342e5f "update raw"); 17 touching commits, none ramp-specific except ff59dd8. `_ramp_fps`: only a342e5f/2d5ee76/1bd592d (never changed). CONFIRMED.
- docs/speed-ramping.md: a342e5f, f954b0c (2026-06-23 typo pass), 402e96d, 5ac1665 (2026-08-26: finished the truncated sync-mode sentence, pin 18→16), befb2f3 (2026-08-26: clamp wording 1–360°), 7cba6fe. CONFIRMED.
- `--grep=ramp`: ff59dd8 (2026-09-07, body quotes "ramp to 60 mid-take, nothing in the pinned class serves 60 ... capped to 40 ... in a mode that tops out at 21"), e0f1cae (playback: "speed ramps replay correctly with no rate logic"), 5ac1665, befb2f3, f954b0c. CONFIRMED.
- fps timeline in RL introduced by 8ee9059 (2026-05-18 "Wait for buffered frames before sync check"), touched by 467e8ef, b3659c0. CONFIRMED (git -S fps_timeline).
cinepi-raw: 4c1c66e, 210d0fb, 7da7ad6, 05eb4a0, dcd2b65, 07504d0, 3c6477e as in §3; 3b3ff60 (2026-06-13) "re-arm on preview reconfigures, absorb only recording drops" (the word "ramp" there = convergence ramp, not speed ramp). `--grep=ramp` otherwise hits only ccmp highlight-ramp commits. CONFIRMED.
Handbook @c99ff77: no speed-ramping entry. Relevant: architecture/cinemate.md:129-135 ("a plain `set fps` can now relaunch the recorder" off-take; mid-take the ladder and fps ceiling are pinned to the running class and settle in stop_recording); architecture/cinepi-raw.md:135-144 (per-take snapshots of thumbnail; mid-take reconfigure invalidates buffers). hardware-log.md grep for ramp/mid-take fps: nothing on ramping (only the "ramp" of highlight anchors). apertar-kb grep (speed ramp/ramping/_ramp_fps/set_fps_double): nothing outside port-raw. CONFIRMED.
**Lessons Cinemate recorded (from bodies):** (a) decide the mode for the fps you will actually command, not the one requested (ff59dd8); (b) never let a take-scoped cap become the operator's new target (ff59dd8); (c) derive the TC base from the configured rate, never from measured FrameDuration, and keep DNG/WAV rounding identical (3c6477e, F-253); (d) do TC stepping per frame under one mutex with the frame's own timestamp (dcd2b65); (e) count drops only on ≥2-period gaps and publish the raw counter (05eb4a0); (f) an fps change mid-take must silence the sync verdict rather than mis-report (RL:620, 8ee9059). Not recorded anywhere: that the sensor exposure is not re-derived on an fps change (§2), that the TC base goes stale under a ramp (§3), that `_ramp_fps` targets a constant 24×2.

---

## 6. What a port to Apertar-Core needs (per-clip → per-frame)

Core today refuses `set_fps` while recording: "Stop recording before changing FPS so video and audio keep the same timeline" (ACC:8540-8546@25397cd). CONFIRMED. Off-take, Core already preserves the ANGLE on an fps change (`shutterUsForPreservedAngle`, ACC:200-208, used :8566-8569) — the opposite of what Cinemate's sensor actually does (§2). Per-clip assumptions found, with Cinemate's answer:

| # | Core per-clip assumption (line) | Cinemate's answer | Port needs |
|---|---|---|---|
| 1 | `setFps` gate while recording (ACC:8543-8546) | no gate; only `fps_lock` (CC:1756) | lift the gate for CDNG raw; keep it for ProRes/H.264/MLV (fixed-rate containers: MLV header fps per clip, apertar-core/src/mlv/MlvEncoder.cpp:1092-1093) |
| 2 | FrameDurationLimits from `settings.fps` at applySettings (ACC:2098-2106) | per-publish SetControls, one request (CPC:968-979; rpicam_app.cpp:1020-1023) | push a new {d,d} on the next request only; clear/re-arm the phase-lock pin (ACC:7349-7353) |
| 3 | FramePhaseLock target per clip | re-arm on `fps_user` change (PLC:99-111) | Core's lock already re-arms on `fps − targetFps > 1e-6` (apertar-core/src/camera/FramePhaseLock.hpp:95-98); feed it the live fps |
| 4 | DNG 0xC764 from `metadata.fps = settings.fps` (ACC:3300), per-frame cache keyed on fps (CdngEncoder.cpp:1441-1459, tag :1666) | per frame from live `options_->framerate` (DE:1686-1692) | already per-frame IF `settings.fps` is updated mid-take and the request→metadata path carries the fps current at CAPTURE (Cinemate's is capture-lagged, §3); pass fps with the frame, not from `settings_` at encode time |
| 5 | RecRun TC = frameIndex / lround(metadata.fps) (CdngEncoder.cpp:333-339); FreeRun frame = wall-µs × fps (:359-360) | TC base fixed at clip start, count = frames (+holes) (DE:2119, :2126-2136) | keep a clip-start base (`tcFps` captured once) for RecRun; FreeRun per-frame fps already works; decide and document which; never recompute the base mid-take (Cinemate lesson c) |
| 6 | `nextFrameIndex` hole detection = Δt × `settings_.fps` from the recorder's start snapshot (ACC:3722-3729; snapshot :3441, :5869) | plain `index_++` (DE:474); drops counted separately by Δt×tc_fps_ (DE:2129-2135) and WRONG under ramp-down (§3) | make `fps` in the index/hole formula the per-frame rate (or integrate Δt×fps(t)); otherwise ramp-down produces index holes = Cinemate's false droppedFrames |
| 7 | Audio: `options_.fps = settings.fps` at start (ACC:6212-6213; AudioRecordingSession.cpp:239), video end window and TC in frames at that fps (:373-376, :805-815) | WAV PCM untouched, metadata at start fps (CS:1407-1410, :1527-1538) | keep: WAV stays wall-clock honest; stamp start fps; document that WAV TC ≠ DNG TC after a ramp |
| 8 | Sync verdict / cadence tracker `trackRecordingCadence` with `settings_.fps` (ACC:7705; :7449 tolerance from expected) | integrate an fps timeline; suppress the verdict on any mid-take change (RL:604-621, :1866-1870) | integrate expected frames over fps(t); do NOT suppress — Cinemate's suppression hides real drops (§3) |
| 9 | Exposure policy on fps change: angle preserved (ACC:8566-8569) | GUI: mode 0 angle / mode 1 time; sensor: time preserved by omission (§2) | make it explicit: a `shutter_policy` {angle, time} applied per step, exposure clamped to frame length on ramp-up |
| 10 | Mode/class change while recording | never relaunch mid-take; same-class live reconfigure splits the clip (cinepi_raw.cpp:68-76,:365-375) | refuse fps above the running mode's ceiling mid-take (Cinemate's `_in_take_fps_ceiling`, CC:904-930) rather than splitting |

UNKNOWN (needs the Pi): the on-sensor brightness step per fps step with a stale ExposureTime (§2); the encode-lag N for the FrameRate tag (§3); whether libcamera's IPA accepts a FrameDurationLimits change on a running IMX585 stream without a frame hiccup at every step (p1 report covers single pushes, not 24 consecutive).

---

## Verification

Adversarial verifier. Every cited line below was opened with `git show <commit>:<path> | sed -n` (cinemate d6cc93e, cinepi-raw 63a08d5, handbook c99ff77, libcamera bfe0b76) or `git show 25397cd:<path>` for apertar-core. Note on apertar-core: during this pass the working tree briefly carried an uncommitted T31 ramp patch (CameraController.cpp/CdngEncoder.cpp/AudioRecordingSession.cpp), which moved the reader's ACC line numbers by hundreds of lines; it read clean again before the end. All ACC/Cdng/Audio cites were therefore checked against the commit, not the tree, and they hold at 25397cd. Verdicts: CONFIRMED (line opened, claim holds) / CORRECTED (claim holds, cite or detail wrong — correction given) / REFUTED / UNVERIFIABLE (needs hardware).

### Table

| # | § | Claim / cite | Verdict | Finding |
|---|---|---|---|---|
| 1 | 1 | cli_commands.py:69 `set fps` → `set_fps`, float | CONFIRMED | cinemate/src/module/cli_commands.py:69@d6cc93e |
| 2 | 1 | `set_fps_double` CC:4074-4117 | CONFIRMED | def :4074, closing log :4117 |
| 3 | 1 | `_ramp_fps` CC:4119-4138 | CORRECTED | 4119-4136; :4138 is `def print_settings` |
| 4 | 1 | speed-ramping.md:7-25 names all three | CONFIRMED | :7 controller, :10 `set fps`, :13 `set_fps_double`, :25 `_ramp_fps` |
| 5 | 1 | `set_fps` CC:1747-1857 | CONFIRMED | |
| 6 | 1 | fps_lock the only lock :1756-1758 | CONFIRMED | no `_is_recording()` test in the body; only the in-take ceiling (#9) |
| 7 | 1 | fps_user write :1763-1764 | CONFIRMED | |
| 8 | 1 | value choice :1776-1778 / :1780-1785 | CONFIRMED | |
| 9 | 1 | `_in_take_fps_ceiling` :904-930, four conditions, `restrict_to_family_of` | CONFIRMED | call spans :926-931; applied :1793-1797 (reader :1792 is a comment line) |
| 10 | 1 | ff59dd8 rule: `_maybe_apply_dynamic_resolution_for_fps(safe_value)` :1799-1810 | CONFIRMED | call at :1808 |
| 11 | 1 | pin `restrict_to_family_of=self.sensor_mode if recording` :988-1000 | CONFIRMED | :997 |
| 12 | 1 | deferral :1002-1016 | CONFIRMED | flag at :1010 |
| 13 | 1 | same-class live reconfigure :1041-1061 | CORRECTED | 1041-1058 (`_apply_resolution_mode` :1054-1058); :1060-1061 is the next section header |
| 14 | 1 | `_resolution_change_needs_restart` False while recording :2782-2783 | CONFIRMED | |
| 15 | 1 | `dynamic_resolution_deferred_fps` :1814-1816; settle :2378-2416; called :2376; flush guard :2395-2399 | CONFIRMED | guard is :2394-2399 |
| 16 | 1 | `current_fps` + Redis `fps` :1827-1828 | CONFIRMED | ParameterKey.FPS = "fps" (redis_controller.py:29) |
| 17 | 1 | shutter keys :1844-1852; `self.fps=int(round)` :1854 | CONFIRMED | |
| 18 | 1 | `cam_init` CC:2711; warning CC:2691-2696 | CORRECTED | warning is :2693-2697; :2691 is `return False` |
| 19 | 1 | cinepi_raw.cpp:68-76 split; :365-375 resume | CONFIRMED | record_stop :75, create_clip_folder :367, record_start :370, resetFrameCount :371 |
| 20 | 1 | `set_fps_double`: target :4081; warn+return :4083-4089, :4106-4112; off-take path :4095-4100 | CORRECTED | target `self.fps*2` is :4082; warn+return :4084-4090 and :4106-4110; `set_resolution`/`fps_max`/`min`/`set_fps` :4097-4101. Logic as described. |
| 21 | 1 | `_select_resolution_mode_for_fps` :2431-2461, pinned while recording | CORRECTED | 2431-2457 (:2459 is `switch_resolution`); pin at :2455 |
| 22 | 1 | `_ramp_fps`: ±1 steps, 0.2 s (:270-271), `fps_temp`=24 (:273), target `min(fps_temp*2, fps_max)`, no caller | CONFIRMED | `git grep _ramp_fps d6cc93e -- src`: only the def |
| 23 | 1 | "24 `fps`+`fps_user` publishes" for 24→48 | CORRECTED | each `set_fps` publishes `fps_user` twice (:1764 and :1825, `update_user_target` defaults True) and `fps` once → 72 publishes. PROBABLE extra: non-free mode snaps each +1 to the step table (:1781-1785) and the loop re-reads `self.fps=int(round(...))` (:1854), so a table without consecutive integers can stall the loop. |
| 24 | 1 | CPC:1188 subscribe; :1158-1166 dispatch; cinepi_state.hpp:30 "fps"; handler :968-979 | CONFIRMED | handler is :968-981; `static_cast<long int>(1e6/24)` = 41666 |
| 25 | 1 | rpicam_app.cpp:1097-1106 SetControls; :1020-1023 move into request | CORRECTED | the lock+move is :1022-1025 |
| 26 | 1 | per-frame `framerate` rpicam_app.cpp:1244-1252; CPC:637; RL:1492-1494 → `fps_actual` | CORRECTED | RL path is :893 (`stats_data['framerate']`) → :902 → `_record_framerate_sample` :1484-1489 → windowed mean published at :1529; :1491-1531 is the function, :1492-1494 its docstring |
| 27 | 1 | startup `stoi` CPC:216-218; seed :448 | CONFIRMED | both inside `sync()` (:176-469). Floor consequence stays PROBABLE (stoi("23.976") → 23 by C++ semantics; depends on what cinemate seeds). |
| 28 | 2 | CC:214 default 0; :1528-1546; :1540-1541; :349; :1543 | CONFIRMED | |
| 29 | 2 | recomputation :1831-1837 / :1839-1842 / :1844-1852 | CONFIRMED | |
| 30 | 2 | "same math in `update_fps` (CC:3458-3476)" | CORRECTED | mode 1 identical (:3466-3469); mode 0 sets `shutter_angle_actual = shutter_angle_nom` (:3464), not a nearest-step snap of the current actual |
| 31 | 2 | :1722-1727; :3228-3230; :3159-3172 nominal refresh | CONFIRMED | |
| 32 | 2 | speed-ramping.md:27-35; befb2f3 clamp wording | CONFIRMED | befb2f3 diff: "sensor's limits" → "1–360°" |
| 33 | 2 | CPC:851-859 `shutter_a` handler; :861-868 `shutter_speed` handler | CORRECTED | :861 key is CONTROL_KEY_SHUTTER_SPEED = "shutter_s" (cinepi_state.hpp:28), not `shutter_speed` |
| 34 | 2 | `shutter_a` written only by CC:3146 and CC:3250 | CONFIRMED | `git grep "set_value(ParameterKey.SHUTTER_A.value"`: exactly those two; startup seed via `_read_or_seed` CC:316 is not a runtime writer |
| 35 | 2 | no cinepi-raw handler for `shutter_angle_actual`/`exposure_time`; handler map CPC:744-1060 | CORRECTED | map is :746-1156 (last entry CONTROL_KEY_ZOOM :1071). `git grep` over cinepi/: neither string is a handler key (only a struct field in sharedContextStage.cpp:28,266) |
| 36 | 2 | `shutter_angle_actual` read only by simple_gui.py:916 | CORRECTED | also listed in web_api_settings.py:22 (exported key list) |
| 37 | 2 | `update_shutter_angle_for_fps` (CC:1707-1719) has no caller | CONFIRMED | only the def and a comment at :3151 |
| 38 | 2 | sensor keeps previous absolute ExposureTime across `set fps` (PROBABLE) | CONFIRMED (mechanism) | rpicam_app.cpp:825-828 defaults ExposureTimeMode/AnalogueGainMode to Manual, so ipa_base.cpp:834-851 does not hit the "ignore when auto" branch (:847-848) and stores `setFixedExposureTime`; FRAME_DURATION_LIMITS (:1186-1188) → `applyFrameDurations` (:1638-1667) only moves `agc->setMaxExposureTime`; agc_channel.cpp:392-396 and :1030 clamp `fixedExposureTime_` to [mode min, maxExposureTime_]. Nothing re-derives it. |
| 39 | 2 | cam_helper.cpp:107-108, :123-124 clamp to frame length | CONFIRMED | exposure re-clipped :127-129 |
| 40 | 2 | CPC:968-979 touches nothing exposure-related | CONFIRMED | |
| 41 | 3 | 0xC764 per frame from `options_->framerate`, round(fps×1000)/1000, DE:1678-1692 | CONFIRMED | |
| 42 | 3 | 4c1c66e (2025-07-04) metadata path + fallback, `fps + 0.5` /1000 bug | CONFIRMED | diff: fallback `*framerate + 0.5` over 1000 AND metadata `fps + 0.5` over 1000 — both 1000× too small |
| 43 | 3 | 210d0fb (2026-06-05) removed metadata path, fixed ×1000, hunk @952-973, reasoning "nominal rate exactly" | CONFIRMED | hunk header `@@ -952,20 +953,19 @@`; reasoning is a code comment (DE:1679-1683); the commit message ("silence all compiler warnings") does not mention it — a silent behavioural change |
| 44 | 3 | 3c6477e (2026-08-26) TC base from the same source | CONFIRMED | body cites F-253, WAV/DNG agreement |
| 45 | 3 | tag follows the ramp with encode-queue lag (PROBABLE) | UNVERIFIABLE (N) | structure confirmed: queue push DE:479, `options_->framerate` read in `dng_save` (DE:1686) on the worker; pool bound `max_ram_buffers_` = 90 % MemAvailable / buffer size (DE:1079-1085). N itself needs the Pi. |
| 46 | 3 | playback reads first frame only (playback.py:163-180); dng_preview.py:209-221; e0f1cae body | CONFIRMED | `names[0]` :163, fps :180; body "speed ramps replay correctly with no rate logic at all" |
| 47 | 3 | clip origin DE:2062-2121; later frames :2126-2136; BCD :1710-1716; `tc_fps_` once :2119; reset hpp:123-124 | CONFIRMED | `resetFrameCount` (hpp:118-) clears `tc_origin_set_`, so `tc_fps_` is re-captured at :2119 on the next frame |
| 48 | 3 | 7da7ad6 / dcd2b65 / 05eb4a0 / 07504d0 attributions | CONFIRMED | 2026-05-31 / 06-02 / 06-01 / 06-02; bodies match |
| 49 | 3 | arithmetic 24→48, 25→50, 48→24, 50→25; threshold new ≤ start/1.5 | CONFIRMED | 20833×24/1e6=0.49998→0→+1; 20000×25/1e6=0.5→llround 1; 41667×48/1e6=2.00002→2→dropped+1; 40000×50/1e6=2; `raw_elapsed≥2` ⇔ Δ·tc_fps_ ≥ 1.5e6 µs |
| 50 | 3 | `index_++` DE:474; 9-digit DE:2340-2341; reset cinepi_raw.cpp:371-372 | CONFIRMED | |
| 51 | 3 | "`frameCount` in stats (CPC:640) is the same counter" | CORRECTED | `getFrameCount()` returns `frames_` (dng_encoder.hpp:209-211), set to `encode_item.index` at dequeue (DE:2140): same index, but as of the last frame the encoder stepped — it lags `index_` by the queue depth |
| 52 | 3 | WAV `-c:a copy` CS:1527-1538; log lines :1386, :1393 | CONFIRMED | copy at :1529 |
| 53 | 3 | `takeStartFramerate_` "parsed from the clip name at record_start() with configuredFramerate()" CS:816-820, :291-295 | CORRECTED | record_start :807, parse :817-821 (framerate assigned :821). The folder regex (CS:422-423) yields date/time/frame only; `metadata.framerate = nominalTimecodeFramerate(fallbackFramerate)` (:429, :465) — i.e. round(configured fps at record_start), not a value read from the name. Substance (take-start rate) holds. |
| 54 | 3 | CS:149-154 round; :1407-1410 fallback; :185-205 time_reference; :1518-1521; :1511-1515 | CORRECTED | `time_reference` computed at :1524-1525, not :1518-1521; rest confirmed |
| 55 | 3 | new WAV per clip folder cinepi_raw.cpp:72-74, :369 | CORRECTED | record_stop :75, record_start :370 |
| 56 | 3 | `analyze_frames` :1659; segments on `fps`/`fps_user` :1452-1460 → :604-621; integral :642-691; comment :1831-1833 | CORRECTED | comment "so speed ramps are counted" is :1834-1835 |
| 57 | 3 | `_suppress_live_sync_for_current_take` at :620; `frames_in_sync = ... or sync_warning_suppressed` :1866-1870; log :1985-1988 | CORRECTED | the expression is :1884-1888; :1866-1870 is the "Using FPS %.6f" log. Suppressor body :623-630 also forces Redis FRAMES_IN_SYNC=1 (:630). |
| 58 | 3 | tolerance default 1 :102-105; 56bf88c (2026-06-05) | CONFIRMED | body: shortfall-only latch; frame-limited takes use requested slots |
| 59 | 3 | DROP_FRAME_DURING_LAST_TAKE :1904-1911; `drop_frame_count`/`tc_hole_count` :1915-1924; Tier-1 :1004-1024; gate :995-1000; leeway :1153-1169; "TC timing" :1940-1952; :1948-1976 | CONFIRMED | `hw_dropped_frames` ← stats `droppedFrames` (RL:870-872); the fps-change suppression does not touch `drop_frame`, only the `user_changing_fps` leeway gates it |
| 60 | 3 | 48→24 step ⇒ drop flash every frame for the rest of the take (PROBABLE) | UNVERIFIABLE | arithmetic (#49) + gate (#59) hold; Tier-1 fires once per cp_stats tick in which `droppedFrames` grew, so "every stats tick", not strictly every frame. Hardware not run. |
| 61 | 4 | CPC:1221-1236; hpp:116-119; PLC:96-111 re-arm; no push on re-arm; push next frame PLC:120-164; test :256-265 | CONFIRMED | return at :110 precedes :159-162; CPC:1244-1250 pushes `{durUs,durUs}` on `setControls` |
| 62 | 4 | two writers 41666 (handler) vs 41667 (servo, lround) | CONFIRMED values / PROBABLE order | re-arm sets `reqDurUs=1e6/24`, next frame `lround`→41667, ≠ −1 → push |
| 63 | 4 | kp=0.06, ki=0.0015 PLC:27-32 | CONFIRMED | :28-29 |
| 64 | 4 | 24 re-arms, no convergence during a 0.2 s/step ramp | UNVERIFIABLE | from the law only; not simulated here |
| 65 | 4 | recording gap absorbed PLC:96-97, :113-118; :99 before :113 | CONFIRMED | stronger than stated: `periodNs` uses the NEW target (:92), so at 48→24 the first new-rate frame has dt ≈ 1 new period, not a gap at all |
| 66 | 5 | cinemate commit list / dates / `--grep=ramp` / `-S` results | CONFIRMED | all 14 hashes resolve with the stated dates; 17 commits touch `set_fps_double`; `_ramp_fps` in a342e5f/2d5ee76/1bd592d only; docs log = 6 commits; `--grep=ramp` = 5 |
| 67 | 5 | ff59dd8 body quote; e0f1cae; 5ac1665 (pin 18→16, sentence); befb2f3 | CONFIRMED | |
| 68 | 5 | fps timeline introduced by 8ee9059, touched by 467e8ef, b3659c0 | CONFIRMED | also d6bad6b (dev-notes removal, not RL) |
| 69 | 5 | lesson (f) attributed to "RL:620, 8ee9059" | CORRECTED | `_suppress_live_sync_for_current_take` was introduced by a4d511c (2026-05-24 "Refine dynamic resolution recording behavior"), not 8ee9059 |
| 70 | 5 | cinepi-raw list; 3b3ff60 "ramp" = convergence ramp; other `ramp` hits are ccmp | CONFIRMED | 69878c5, 4cd6a07, 9c20830, 3a39306 |
| 71 | 5 | handbook cinemate.md:129-135; cinepi-raw.md:135-144; hardware-log ramp grep; apertar-kb grep | CONFIRMED | hardware-log hits are highlight/optical-black "ramp" only; KB grep outside port-raw: none |
| 72 | 5 | lessons (a)-(e) | CONFIRMED | ff59dd8, 3c6477e (F-253), dcd2b65, 05eb4a0 bodies |
| 73 | 6 | ACC:8540-8546 gate; :200-208 + :8566-8569 angle preserved | CONFIRMED @25397cd | |
| 74 | 6 | row 1 MlvEncoder.cpp:1092-1093; row 2 ACC:2098-2106, :7349-7353; row 3 FramePhaseLock.hpp:95-98 | CONFIRMED | |
| 75 | 6 | row 4 ACC:3300; CdngEncoder.cpp:1441-1459, :1666; row 5 :333-339, :359-360 | CONFIRMED | |
| 76 | 6 | row 6 ACC:3722-3729; snapshots :3441, :5869 | CONFIRMED | |
| 77 | 6 | row 7 ACC:6212-6213; AudioRecordingSession.cpp:239, :373-376, :805-815 | CONFIRMED | |
| 78 | 6 | row 8 ACC:7705; ":7449 tolerance from expected" | CONFIRMED (note) | :7449 is the cadence-ready gate (`max(500, expected/50)`), not a tolerance inside `trackRecordingCadence` |
| 79 | 6 | header "libcamera(cinemate) @bfe0b76" | CONFIRMED | `rev-parse HEAD` = bfe0b76 |

Counts: CONFIRMED 57 · CORRECTED 19 · REFUTED 0 · UNVERIFIABLE 3 (#45, #60, #64: hardware or simulation). #62 is counted CONFIRMED for the two values; its thread ordering stays PROBABLE.

### Corrections that change substance

1. **#51 frameCount.** `frameCount` in cp_stats is `frames_` = index of the last frame the encoder dequeued (DE:2140), not the live `index_`. Under a ramp it lags by the queue depth — the same lag the reader attributes to the 0xC764 tag (#45). Any port that compares "frames captured" against "frames encoded" must not treat these as one counter.
2. **#53 WAV rate.** The take-start framerate is `round(configured fps at record_start)`; nothing is parsed from the clip name but date/time/frame. Same outcome (start rate), different mechanism — matters if a port expects the rate to be recoverable from the folder name.
3. **#30 update_fps mode 0.** Not "same math": it resets the actual angle to the nominal, not to the nearest step of the current actual.
4. **#23 publish count.** 72 Redis publishes (not 24) for a 24-step ramp; and in non-free mode `_ramp_fps` can stall on a step table without consecutive integers.
5. **#57 cite.** The `frames_in_sync ... or sync_warning_suppressed` expression is RL:1884-1888; the suppressor also writes FRAMES_IN_SYNC=1 to Redis (RL:630), so the GUI is told "in sync" the moment fps changes mid-take.
6. **#69 attribution.** The silence-the-verdict rule came in with a4d511c (dynamic resolution), not 8ee9059.
7. **#43 provenance.** The ×1000 fix and the removal of the per-frame FrameDuration path landed silently inside "silence all compiler warnings" (210d0fb); no commit message records the decision — only the code comment.

Cite-only corrections (logic unchanged): #3, #13, #18, #20, #21, #25, #26, #33, #35, #36, #54, #55, #56.

### Settled unknowns

- **Sensor exposure across a `set fps` (§2, was PROBABLE).** Settled from source (#38): cinepi-raw runs the IPA in manual exposure mode (rpicam_app.cpp:825-828), the IPA stores the last ExposureTime as a fixed value (ipa_base.cpp:851), and a FrameDurationLimits change only re-clamps that fixed value to the new frame's maximum (ipa_base.cpp:1638-1667; agc_channel.cpp:1030). So the sensor holds a **constant absolute exposure time** in both GUI modes. Brightness step the operator sees: **none** on ramp-down; on ramp-up **none** unless `old_exposure × new_fps > 1` (then clamped to frameLength − frameIntegrationDiff, i.e. ≈ log2(old_exposure × new_fps) stops darker). Example: 180° @24 (1/48 s) → 48 fps lands at ≈360°, same brightness; → 96 fps clamps to 1/96 s, ≈1 stop darker. Hardware confirmation of the visible result still open, but the mechanism is no longer inferred.
- **Phase lock at a ramp-down step (§4).** Settled stronger than claimed (#65): the gap test uses the new target's period, so a 48→24 step is not even a `bigGap`; no phantom missed frames either way.
- **Which commit silenced the sync verdict (§5 lesson f).** a4d511c, 2026-05-24.

### Still unknown (needs the Pi)

- Encode-lag N for the 0xC764 tag and for `frameCount` (#45, #51): bounded by `max_ram_buffers_` (DE:1079-1085), otherwise hardware-dependent.
- Whether a 2× FrameDurationLimits step on a running IMX585 stream passes without a frame hiccup (#64 context): source shows the limits are clamped to the mode and applied "once AGC recalculations occur" (ipa_base.cpp:1641); the phase lock already pushes ±1 µs changes every frame on hardware (CPC:1244-1250), but a 2× step is a different test.
- Convergence behaviour over 24 consecutive re-arms (#64): not simulated in this pass.
