---
datum: 2026-10-26 21:00:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T31 speed-ramping
typ: digital anteckning
---

# T31. Speed ramping: change the frame rate inside a cDNG/MLV take, keep one timeline, keep the sound honest

Status: written 2026-10-26, moved to `cinemate-port` 2026-10-27 (cloud session; patch `working/patches/0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch`, which applies with plain `git am` on Core `cinemate-port` `7a545d9`). Line numbers below are on `cinemate-port` with this patch applied, unless marked `@7a545d9` (before the patch). Three steps differ from the first version written for the cloud branch: the session's `recordingBaseFps()` goes in the public section (4.2, 4.4), the WAV end uses the latest frame's duration (4.6), and `fps-ramp.txt` is written inside the timed stop (4.5). Host syntax checks pass for every touched file except `CameraController.cpp` (libcamera). Answer: `working/ramp-answer.md`; reader reports `working/port-raw/r1-ramp-cinemate.md`, `r2-ramp-core.md`, critic `critic-ramp.md` (its nine confirmed gaps are closed in the patch or listed in §7/§8). Builds on T27 (phase lock), T28 (medium gone), T30 (audio clock).

**You will learn**
- Why one `if` is all that stops Core from ramping, and the four places that would then quietly go wrong (frame numbering, WAV end, timecode, `FrameRate`).
- What Cinemate does under a ramp, including two defects you do not want to inherit (a ramp down counted as a drop per frame; a shutter mode that is display-only).
- How a ramped take is one clip at its start rate: count-based numbering, one `FrameRate`, timecode counted at the start rate, a real-time WAV.
- Why the capture-gap estimate and the phase lock must sit out a few frames after every change, and why that number follows the raw buffer count.

**Risk:** Core rebuild and restart; off by default (`fps_ramp` setting). Once on, **every fps control ramps a running take** — the WebUI buttons, the PCF pot, `fps:<n>` hardware actions. Undo: `set_fps_ramp enabled=false`, or `git checkout` the eight files. **Time:** 3 h including three takes.

## 1. The problem

`CameraController::setFps` refuses any change while recording: `CC:8808-8811@7a545d9`, "Stop recording before changing FPS so video and audio keep the same timeline." Below that gate an fps change is already cheap: `applySettingsLocked(next, false)` → `applyControls` writes `pendingControls_` (`CC:6355-6388@7a545d9`) and the next `requeueRequest` carries the new `FrameDurationLimits` (`:7533-7539`); no reconfigure, no buffer reallocation. The sensor follows about N+2 frames later, N being the raw request count (4 on ext4, 6 on exFAT/NTFS, 8-10 with Clear HDR, T23/T29): the control rides the next requeued request behind N-1 queued ones, then `DelayedControls` writes it at a start-of-frame two frames ahead; the first timestamp delta that shows the new period is one frame later again, N+3 (critic K1-K5, ±1).

Remove the `if` and four things break (r2 §2, all confirmed from the lines):

| What | Line @7a545d9 | Under a ramp from B to L |
| --- | --- | --- |
| frame numbering `max(count, elapsed × B)` | `CC:3773-3781` | L < B: every other file number missing (B=48, L=24) |
| WAV end snapped to the B grid | `AudioRecordingSession.cpp:382-384` | end off by 1/B − 1/L (−42 ms at 24→12) |
| timecode from the **live** fps | `CdngEncoder.cpp:331`, `:356`; `metadata.fps = settings.fps` `CC:3289` | RecRun jumps back 5 s at a 24→48 step at frame 240; FreeRun repeats/skips FF |
| `FrameRate` tag from the live fps | `CdngEncoder.cpp:1406-1422` | changes mid-sequence; which frame an NLE samples is unknown |

Cinemate has no gate (`cinepi_controller.cpp:968-979@63a08d5`) and lives with the consequences: file numbers by count (`dng_encoder.cpp:474`), timecode counted at the start rate (`:2119-2136`) — which makes a ramp **down** register one false dropped frame per frame for the rest of the take, the WAV left in real time (`cinepi_sound.cpp:1527-1538`), and a sync verdict that is simply suppressed when fps changed (`redis_listener.py:604-621`). Its `shutter_a_sync_mode` 0/1 recomputes the displayed angle but never re-sends the exposure (`cinepi_controller.py:1831-1852`; no writer of `shutter_a` in `set_fps`), so the sensor keeps its absolute exposure in both modes (settled from the IPA source: `ipa_base.cpp:851`, `:1638-1667@bfe0b76`). See `working/ramp-answer.md` §1.

## 2. How this part works

```
 operator: set_fps 50 (WebUI button, pot, ramp_fps stepper)
     |
 CameraController::setFps  -- recording? -> fps_ramp on? raw format? else refuse
     |  shutter policy: angle (rescale µs)  |  exposure (leave µs)
     v
 applyControls -> pendingControls_ (FrameDurationLimits + ExposureTime, one request)
     |            noteFpsChange(): grace = N+6 frames of the slower rate, at least 10; event queued
     v
 sensor switches period ~N+2 frames later (programmed), delta shows it at ~N+3
     |
 recordRawFrame (per frame):
     index = count (not elapsed x B)            -> files 0,1,2,... whatever the rate
     metadata.fps = B (start rate)              -> FrameRate tag, RecRun TC = index / B
     timecodeWallClockUs = first wall + index/B -> FreeRun TC counts at B
     FrameDuration within half a step of a request -> "fps ramp: frame=N frame_us=20000 delta_us=... lag_frames=...", event paired
     audio observeVideoFrame(ts, duration)      -> WAV ends at ts + duration (real time)
     trackRecordingCadence, phase lock           -> quiet while in grace
     |
 stop: fps-ramp.txt in the clip folder, "fps ramp stats: changes= base_fps= min_fps= max_fps=",
       then "fps ramp: take ended at 50 fps, restoring 25" (the start rate is persisted; ramp steps never were)
```

The clip is one timeline at B. A segment captured at 2B plays at half speed; that is the feature. The WAV is real time, so sound cannot stay in sync through a slow-motion segment — it is conformed or cut in post, exactly as with any high-speed camera. The grace (N + 6 frames of the slower rate, at least 10, `APERTAR_FPS_RAMP_GRACE_FRAMES` to override) exists because the sensor runs the old period for N+2 frames after the request: the gap estimator would read a ramp up as a drop, and a phase lock armed on the new nominal would bank tens of milliseconds of phase error and sit on its ±150 µs clamp for hundreds of frames.

Reading assignments: `CC:9069-9174` (gate, step helper, restore), `:3785-3791` (`nextFrameIndex`), `:8302-8459` (ramp helpers), `:8013-8038` (frame path), `AudioRecordingSession.cpp:382-388`, `App:9238-9280` (stepper); `working/ramp-answer.md` §2-§3.

## 3. Find it yourself

**3.1 The gate, and what the recorder numbers frames with** (Pi, read-only, before the patch)

```bash
grep -n 'Stop recording before changing FPS' ~/ApertarCore/src/camera/CameraController.cpp
grep -n 'timeIndex = ' ~/ApertarCore/src/camera/CameraController.cpp
```

> [!tip]- Answer
> One line each. `timeIndex` multiplies elapsed time by `settings_.fps` — the **recorder's** copy of the settings, taken at `startAtFolder`, so it is the start rate even if the session's fps moved. That is the term a ramp must drop.

**3.2 Does the WebUI stop you?** (Pi, Core running, preview only) Press a different fps button while recording a 5 s cDNG take.

> [!tip]- Answer
> No UI lock: the toast shows the controller's refusal and the readout snaps back on the next snapshot (`WebControlPage.cpp:9910-9916@7a545d9`). The same for the PCF pot and `fps:<n>` actions (`App:8623-8630@7a545d9`, `:8812-8816@7a545d9`). That is why the port is behind a setting.

**3.3 What does a fps change cost the sensor today?** (Pi, preview, phase lock on from T27)

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=50; sleep 3
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=25; sleep 3
journalctl -u apertar-core -b --no-pager | grep -E 'phase-lock: (armed|released)' | tail -4
```

> [!tip]- Answer
> `released` then `armed fps=50 ...` within a frame or two of each command: `applyControls` releases on any fps change (`CC:6376-6380@7a545d9`) and `FramePhaseLock` re-arms on the next frame. After the patch the `armed` line comes N+6 frames later, after the grace.

## 4. Make the change

Port the logic; type it in, do not paste Cinemate. The patch is the reference if a step will not build.

**4.1 Two settings and an audio option** — `include/apertar/core/Types.hpp`: next to `fpsPhaseLock` add `bool fpsRampEnabled = false;` and `bool fpsRampKeepExposure = false;` (`:130-133`); in `AudioRecordingOptions` add `bool fpsRamp = false;` (`:211`). `CameraController.cpp`: `fps_ramp` and `fps_ramp_keep_exposure` in the settings event (`:189-190`), the persister's reader (`:735-738`) and writer (`:809-810`). `ApertarCoreApp.cpp`: the same two keys in both settings JSONs (`:214-215` and the second copy near `:7994`).

**4.2 The gate becomes a policy** — `CameraController::setFps(double fps, bool takeOnly = false)` (`CC:9069-9114`; header `CameraController.hpp:62`): first, when `takeOnly` and no take is running, refuse with "The take ended; FPS ramp stopped." (`:9072-9077`) — the stepper in 4.7 passes `takeOnly` for a ramp it started inside a take, so a step that lands after the take ended is refused instead of persisted. Then compute `rampingTake = recording_ && |fps − settings_.fps| > 1e-4`; if so, refuse unless `settings_.fpsRampEnabled`, and refuse when `isProcessedVideoFormat(settings_.recordingFormat) || settings_.photoModeEnabled` ("FPS ramping works in cDNG and MLV takes only."). Leave the range check, the sanitiser clamp and the no-op path alone — they are what stops a mid-take request above the mode's ceiling from doing anything (Cinemate's `_in_take_fps_ceiling`, `cinepi_controller.py:904-930`). Move the tail of `setFps` into `applyFpsStepLocked(effectiveFps, rampingTake, commit)` (`:8846-8883`): `keepExposure = next.fpsRampEnabled && next.fpsRampKeepExposure` (the policy belongs to ramping; with ramping off every fps change keeps the angle, as before); call `shutterUsForPreservedAngle` only when `!keepExposure`; when keeping the exposure, remember the operator's value in `rampNominalShutterUs_` the first time and set `shutterUs = min(nominal, floor(1e6 / effectiveFps))` — the IPA would shorten a longer exposure silently (`agc_channel.cpp:398`, `:983@7e9fef0`), the setting, the UI and the DNG must agree with the sensor, and a ramp back down must return to the nominal (Cinemate's `exposure_time_nominal`). The nominal resets on a successful `setShutterUs` (after its checks, `:8953`), on `setShutterAuto` (`:8963`), when `setFpsRamp` changes the switch or the policy (`:9466-9467`) and when a preset loads (`applyCapturePreset`, `:9960`). Log one line when `rampingTake` and set `rampTakeChanged_` (`:8871-8877`). `setFps` passes `commit = !rampingTake`: a ramp step is not persisted (Cinemate `ff59dd8`: a take's value must not become the operator's target); the helper emits the settings event itself so the UI still follows (`:8879-8882`). `restoreFpsAfterRampLocked()` (`:8887-8904`) puts the take's start rate back, persisted — and re-persists even when the ramp already came back to the start rate, because another setting changed mid-take may have written a mid-ramp fps (`:8894-8899`) — and is called from `stopRecording` and `checkRecordingFailure` after the session stopped (`:9815`, `:9840`) and from `CameraController::stop()` when Core shuts down during a ramp take, after closing the take like `record_stop` so `fps-ramp.txt` is written (`:8980-8986`); `startRecording` records the base (`:9826`). Add `setFpsRamp(bool enabled, bool keepExposure)` beside `setFpsPhaseLock` (`:9728-9742`) that refuses to toggle `enabled` while recording, and `recordingBaseFps()` (`:9744-9750`), which asks the session's own `recordingBaseFps()`. On this branch the session's private members are private to the controller too (Core `8f7dc39` moved `phaseLockStatus()` to the public section for that reason, instead of a `friend` line), so put the session's `recordingBaseFps()` in its public section right after `phaseLockStatus()` (`:6877`), with the same `#if APERTARCORE_HAS_LIBCAMERA` / `#else return 0.0;` guard. Declare the controller's methods and the two helpers plus the three members in the header (`CameraController.hpp:88`, `:121`, `:128-129`, `:173-177`).

**4.3 Count-based numbering** — `DngRecordingQueue::nextFrameIndex(int64_t timestampUs, bool countOnly = false)` (`:3785`): the `timeIndex` term is 0 when `countOnly`. Add `const std::string &folderPathString() const` next to `mediaProfile()` (`:3781`). In `recordRawFrame` pass `/*countOnly=*/settings_.fpsRampEnabled` (`:8013`).

**4.4 The session's ramp bookkeeping** — in `CameraSession`, members after `lastRecordingSensorTimestampUs_` (`:8836-8855`): a `FpsRampEvent {bootUs, frameIndex, fromFps, toFps, shutterUs, applied, seen, appliedFrameIndex, frameUs}`, `rampMutex_`, `rampEvents_`, `rampEventsStamped_`, `rampGraceUntilUs_`, `recordingBaseFps_`, `rampMinFps_`, `rampMaxFps_`, `rampFirstWallClockUs_`, `rampLastTimestampUs_`. Methods before `trackRecordingCadence` (`:8302-8459`):

```cpp
double fpsRampGraceFrames() const                                      // max(10, requests_.size() + 6); APERTAR_FPS_RAMP_GRACE_FRAMES overrides
void noteFpsChange(double fromFps, double toFps, uint32_t shutterUs)   // grace = that many frames of the slower rate, event queued
bool inFpsRampGrace(int64_t sensorTimestampUs)                         // ts < rampGraceUntilUs_
double stampFpsRampEvents(uint64_t frameIndex)                         // stamps queued events, returns recordingBaseFps_
double recordingBaseFps()                                              // public section, after phaseLockStatus() (see 4.2)
void pairFpsRampEvents(uint64_t frameIndex, int64_t frameUs, int64_t timestampUs) // frame within half a step of a request: close it (+ older ones as superseded), one journal line with delta_us and lag_frames
void writeFpsRampLog(bool mediumGone)                                  // stats line; <clip>/fps-ramp.txt unless mediumGone
```

`noteFpsChange` only ever lengthens the grace (`std::max`, `:8325`): a quick small step must not cut short the window an earlier big jump still needs. Keep `rampMutex_` a leaf lock: `noteFpsChange` is called from `applyControls` under the settings and controls mutexes (`:6393-6394`), `inFpsRampGrace` from `stepFramePhaseLock` under `controlsMutex_` (`:7495`) and from `trackRecordingCadence` (`:8466`); never take anything else while holding it. Bound the list outside takes (keep the newest 64 while nothing is stamped) — a pot swept in preview must not grow it all session.

**4.5 Wire the frame path** — `recordRawFrame` after `metadataFromRequest` (`:8023-8038`): when `settings_.fpsRampEnabled`, `metadata.fps = stampFpsRampEvents(frameIndex)`; latch the first frame's wall clock and set `metadata.timecodeWallClockUs = first + llround(frameIndex × 1e6 / metadata.fps)`; when `frameDurationUs > 0`, `pairFpsRampEvents(frameIndex, frameDurationUs, timestampUs)` — a 2 % "did it move" test would miss a 1-fps step above 50 fps (50→51 is 1.96 %), so pair on closeness to the requested period instead, and never earlier than two frames after the change was stamped (`:8376`): `DelayedControls` cannot apply it sooner, and a frame still at an older period that happens to match a newer request would otherwise close the older request as superseded. `trackRecordingCadence`: when in grace, update the last timestamp and return (`:8466-8472`). `stepFramePhaseLock`: `enabled` also requires `!inFpsRampGrace(ts/1000)` (`:7491-7495`). `startRecording`: clear the events, set `recordingBaseFps_`/min/max to `settings.fps`, zero the two completion-thread fields (`:6420-6429`); `resolvedAudioOptions.fpsRamp = settings.fpsRampEnabled && !isProcessedVideoFormat(...)` (`:6470`). `stopRecording`: `writeFpsRampLog(mediumGone);` on its own line right after `timed("raw_ms", [&] { recorder_.stop(mediumGone); });` (`:6590-6591`), so the file is in the clip folder before the sync at stop.

**4.6 Timecode and audio** — `CdngEncoder.hpp:39`: `uint64_t timecodeWallClockUs = 0;` in `Metadata`; `CdngEncoder.cpp:1400-1401`: `timeCode(metadata, metadata.timecodeWallClockUs ? metadata.timecodeWallClockUs : wallClock)`. `AudioRecordingSession::observeVideoFrame` (`:385-389`): on this branch frames can arrive out of order (`d9f00d4`), so the function keeps the latest frame's time and duration (`videoLastBootUs_`, `videoLastDurationUs_`) and assigns `videoEndBootUs_` directly. Add `const bool byDuration = options_.fpsRamp && videoLastDurationUs_ > 0;` and change the condition to `(options_.fps > 0 && !byDuration)`, so a ramp take takes the existing fallback branch (`videoLastBootUs_ + videoLastDurationUs_`).

**4.7 Commands and the stepper** — `ApertarCoreApp.cpp`: `set_fps_ramp` with `enabled` and optional `shutter` = `angle|exposure` (`:9882-9892`), `ramp_fps` with `to` and optional `seconds` (`:9894-9903`), both in the help list (`:9626`). `startFpsRamp(target, seconds, &error)` (`:9238-9285`): one fps per step on a `std::thread` member, `seconds/steps` apart, each step `camera_.setFps(fps, takeScoped)` where `takeScoped` is whether a take was running when the ramp started (`:9255`, `:9269`); `seconds` is clamped to 0-600 (`:9900`); the wait is a `condition_variable::wait_for` so `stopFpsRamp()` (`:9287-9297`) returns at once; stop at the first refusal and when the accepted fps did not move (the sanitiser clamps at acceptance, so that is the mode's ceiling, not a lag). `stopFpsRamp()` is called before a new ramp (`:9240`), first thing in `record_start` and `record_stop` (`:11107`, `:11268`), wherever `checkRecordingFailure()` ends a take (`:7127`, `:9350`, `:9478`) — a take must start at a settled rate and the controller's restore at stop must not be fought — and in `stop()` after the web and control servers have stopped, so no command can start a new ramp behind the join (`:7021`). State: `fps_ramp_stepping`, `fps_take_base` next to the phase-lock fields (`:7947-7948`). Header: the two methods after `stopMediaWatcher` (`ApertarCoreApp.hpp:104-105`), the thread, mutex, condition variable and two atomics at the end of the class (`:197-202`).

**4.8 Host check before the Pi build** (cloud or laptop with the sources):

```bash
cd ~/ApertarCore && for f in src/ApertarCoreApp.cpp src/audio/AudioRecordingSession.cpp src/cdng/CdngEncoder.cpp src/mlv/MlvEncoder.cpp; do g++ -std=c++20 -fsyntax-only -Isrc -Iinclude $f && echo "$f ok"; done
```

## 5. Build, deploy, test

Build and restart as in T23 §5. Then, 2K cDNG uncompressed at 25 fps, audio on, phase lock on, a clock or a metronome in frame:

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_fps_ramp enabled=true shutter=angle
python3 -I ~/apertar-kb/working/tools/core.py record_start; sleep 10
python3 -I ~/apertar-kb/working/tools/core.py ramp_fps to=50 seconds=5; sleep 10
python3 -I ~/apertar-kb/working/tools/core.py ramp_fps to=25 seconds=5; sleep 10
python3 -I ~/apertar-kb/working/tools/core.py record_stop; sleep 3
journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp|capture stats|phase-lock (stats|armed|released)|audio sync' | tail -60
```

Write down before you look: (1) 50 request lines (`25 -> 26 fps ...`) and up to 50 `frame=` lines with `lag_frames=` about N+2 (6 on ext4, 8 on exFAT, 10-12 with Clear HDR; the stepper's 200 ms steps are 5-10 frames apart, so when two requests collapse into one period change the line says `superseded=1`); (2) `fps ramp stats: changes=50 base_fps=25 min_fps=25 max_fps=50` then `take ended at 25 fps` nothing — the ramp came back to 25 before the stop; stop a take at 50 once and expect `take ended at 50 fps, restoring 25`; (3) `dropped_gap_estimate` the same as a non-ramp take (0 on a good medium); (4) no `drop[capture-gap]` line near the ramps; (5) `phase-lock: released` at the first step up and `armed fps=50` N+6 frames after the last step; (6) `audio sync: ... output_samples=` ≈ 30 s × 48 000; (7) `get_state` after the take shows `fps=25` and the settings file was written once at stop, not 50 times during the take.

**5.1 The clip** — `fps-ramp.txt` in the clip folder: 50 lines `requested_frame applied_frame frame_us seen tc_at_base boot_us from_fps to_fps shutter_us` (`seen=0` marks a period the sensor skipped; `tc_at_base` is where to scrub to on the 25 fps timeline); file numbers contiguous (`ls | wc -l` equals the last number + 1); every DNG's `FrameRate` = 25/1 (`exiftool -FrameRate -TimeCodes <first> <middle> <last>`); RecRun TC = index/25, FreeRun TC counting at 25 from the first frame's time of day. The `lag_frames=` figures are the measurement that sizes the grace: if any exceeds N+5, set `APERTAR_FPS_RAMP_GRACE_FRAMES` above it.

**5.2 In Resolve** — import at 25: one clip, the middle segment at half speed, the clock hand slow; the WAV is 30 s long and drifts out through the slow segment, which is correct. Conform or cut.

**5.3 Shutter policy** — repeat with `shutter=exposure` at 360° (40 ms at 25): the ramp up clamps to 20 ms (`(shutter clamped to the frame)` on the line, half a stop darker, as on Cinemate), the ramp down returns to 40 ms because the nominal was kept. At 180° (20 ms): brightness constant through the ramp, blur halves at 50. With `angle`: blur constant, half a stop darker at 50. Both honest at the sensor (`ExposureTime` rides the same control list as the duration), which Cinemate's mode 0 is not. Auto shutter: neither policy runs; the AGC re-balances gain on its own.

**5.4 MLV** — one 25→50→25 MLV take. Header fps 25, VIDF times real. Does MLV App play it at 25 (slow-motion segment) or at the real cadence? Unknown off the Pi; write the answer into `lessons/hardware-log.md`.

**5.5 Refusals** — `set_fps` during an H.264 take: "FPS ramping works in cDNG and MLV takes only."; `set_fps_ramp` toggled during a take: "Stop recording before turning FPS ramping on or off."; `ramp_fps to=200` on a mode that tops at 60: one `fps ramp stopped: 60 fps is this mode's limit` line and `fps_ramp_stepping` back to false; `record_start` while a stepper runs: the stepper is stopped first, the take starts at the rate reached.

## 6. Commit

```bash
git -C ~/ApertarCore add include/apertar/core/Types.hpp src/camera src/audio src/cdng src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp
git -C ~/ApertarCore commit -m "camera: speed ramping, FPS changes during cDNG/MLV takes behind fps_ramp

Opt-in fps changes during raw takes: count-based numbering, one FrameRate
and timecode base per clip, WAV ended at the last frame's own duration,
explicit shutter policy, grace for the gap estimate and the phase lock,
fps-ramp.txt per take, ramp_fps stepper. Logic ported from Cinemate
(set fps / shutter_a_sync_mode / _ramp_fps); its ramp-down drop defect and
display-only shutter mode are not inherited.
Tested: <counts from 5, Resolve conform, MLV App answer>."
```

Commit on `cinemate-port`; pushing follows `working/mac-driven-loop.md` and happens only when you decide.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `Stop recording before changing FPS, or enable FPS ramping` | the setting is off | `set_fps_ramp enabled=true`; it persists |
| file numbers with holes in a ramp take | `countOnly` not passed at `:8013`, or the setting was toggled mid-take (refused, check the reply) | fix the call; count-based is the whole point |
| `drop[capture-gap]` right at each step | grace too short for this sensor/medium (`fpsRampGraceFrames()` = requests + 6) | `APERTAR_FPS_RAMP_GRACE_FRAMES=20` in the service; compare with the `lag_frames=` you measured |
| `fps-ramp.txt` rows ending `- - - -` | the sensor never reached that period and no later request closed it (a request clamped to the current value is a no-op and never queued, so this should not happen) | note the `from`/`to` and the mode; report |
| `phase-lock stats: max_abs_err_us` large after a ramp | the lock re-armed during the switch | confirm `armed` comes after the last `frame=` line; raise the grace |
| `FrameRate` differs between frames | `metadata.fps` not pinned (`:8024`) | check `stampFpsRampEvents` is called when `fpsRampEnabled` |
| `(shutter clamped to the frame)` in a ramp-up line | keep-exposure asked for more than one frame of exposure | expected; the picture is as bright as the frame allows, as on Cinemate (its IPA does the same silently) |
| WAV short by one slow frame | `fpsRamp` not set on the audio options (`:6470`) | fix; the fallback branch must be taken |
| `fps-ramp.txt` missing after a take with changes | `folderPathString()` empty (MLV path?) or the medium was gone (T28, by design) | check the stats line; it prints even when the file is skipped |
| next take starts at the ramped rate | `restoreFpsAfterRampLocked` not called from your stop path (`:10085`, `:10110`) | check both the normal stop and the medium-gone stop |
| settings file rewritten on every step | `commit` not passed as `!rampingTake` (`:9112`) | fix; the UI event is emitted by the helper instead |

Undo: `set_fps_ramp enabled=false` (persisted). Full undo: `git checkout -- include/apertar/core/Types.hpp src/camera src/audio src/cdng src/ApertarCoreApp.cpp src/ApertarCoreApp.hpp`, rebuild.

## 8. What you learned, going further

- A ramped take is one clip at its start rate; everything that derives time from a rate must use that rate or the frame's own duration, never the live fps.
- The sensor lags a control by the request queue plus two frames; every estimator keyed on the nominal period needs a grace window across the switch, sized from the queue. The alternative, `gap iff delta(n) > 1.5 × FrameDuration(n−1)` (the previous frame's own length), needs no window at all; it rests on the delta spanning the previous frame, which the Pi settles with the `delta_us`/`frame_us` pairs on the `frame=` lines.
- A take-scoped value must not become the operator's target: the ramp steps are not persisted and the start rate comes back at stop. A pot at a preset boundary still ramps a take on every flicker (the `deadband` in `GroveAnalogInput` is the remedy) and keeps the grace armed.
- The sound stays in real time; the picture does not. That is a post-production fact, not a bug.
- Exercise: integrate the per-frame duration instead of counting (r2 §4 option B) so real drops leave holes again in a ramp take; compare the two numberings on a take with a forced drop.
- Going further: a `set_fps_double` toggle on a GPIO button (Cinemate's slow-motion button, `docs/speed-ramping.md:12-21`), mapped to `ramp_fps to=<2×base> seconds=<n>` and back.

## 9. Sources

- cinemate `d6cc93e`: `docs/speed-ramping.md:5-35`, `src/module/cinepi_controller.py:904-930`, `:1747-1857`, `:1528-1546`, `:4074-4136`, `redis_listener.py:604-621`, `:1153-1169`; commits `ff59dd8`, `2c8cf81`, `e0f1cae`.
- cinepi-raw `63a08d5`: `cinepi/cinepi_controller.cpp:968-979`, `:851-868`, `cinepi/dng_encoder.cpp:474`, `:1678-1692`, `:2062-2136`, `cinepi/cinepi_sound.cpp:149-154`, `:1527-1538`; commits `4c1c66e`, `210d0fb`, `3c6477e`, `dcd2b65`, `05eb4a0`.
- libcamera `bfe0b76`: `src/ipa/rpi/cam_helper/cam_helper.cpp:107-108`, `:123-124`.
- Apertar-Core `7a545d9` (before the patch): `CC:8808-8811`, `:3773-3781`, `:6355-6388`, `:7533-7539`, `:3289`, `:8233-8276`, `:1173-1181`, `:7401-7419`, `AudioRecordingSession.cpp:367-386`, `CdngEncoder.cpp:324-365`, `:1404-1422`, `MlvEncoder.cpp:1092-1093`, `:1307-1316`, `WebControlPage.cpp:9910-9916`; libcamera-qbc `7e9fef0`: `agc_channel.cpp:398`, `:983`, `camera_sensor_properties.cpp:389-394`, `delayed_controls.cpp:149-183`, `:232-274`, `pipeline/rpi/pisp/pisp.cpp:2860-2869`; the lines in §4 are on `cinemate-port` with the patch applied.
- `working/ramp-answer.md`, `working/port-raw/r1-ramp-cinemate.md`, `r2-ramp-core.md`, `critic-ramp.md` (K1-K10, Q1-Q26).

%% tutor
ref core include/apertar/core/Types.hpp 130 bool fpsRampEnabled = false;
ref core src/camera/CameraController.cpp 3785 uint64_t nextFrameIndex(int64_t timestampUs, bool countOnly = false)
ref core src/camera/CameraController.cpp 6394 noteFpsChange(settings_.fps, sanitized.fps, sanitized.shutterUs);
ref core src/camera/CameraController.cpp 8013 const uint64_t frameIndex = recorder_.nextFrameIndex(timestampUs, /*countOnly=*/settings_.fpsRampEnabled);
ref core src/camera/CameraController.cpp 8024 metadata.fps = stampFpsRampEvents(frameIndex);
ref core src/camera/CameraController.cpp 8308 double fpsRampGraceFrames() const
ref core src/camera/CameraController.cpp 8319 void noteFpsChange(double fromFps, double toFps, uint32_t shutterUs)
ref core src/camera/CameraController.cpp 8366 void pairFpsRampEvents(uint64_t frameIndex, int64_t frameUs, int64_t timestampUs)
ref core src/camera/CameraController.cpp 8404 void writeFpsRampLog(bool mediumGone)
ref core src/camera/CameraController.cpp 9078 const bool rampingTake = recording_ && std::abs(fps - settings_.fps) > 0.0001;
ref core src/camera/CameraController.cpp 9116 bool CameraController::applyFpsStepLocked(double effectiveFps, bool rampingTake, bool commit)
ref core src/camera/CameraController.cpp 9157 void CameraController::restoreFpsAfterRampLocked()
ref core src/camera/CameraController.cpp 9728 bool CameraController::setFpsRamp(bool enabled, bool keepExposure)
ref core src/audio/AudioRecordingSession.cpp 385 const bool byDuration = options_.fpsRamp && videoLastDurationUs_ > 0;
ref core src/cdng/CdngEncoder.hpp 39 uint64_t timecodeWallClockUs = 0;
ref core src/ApertarCoreApp.cpp 9238 bool ApertarCoreApp::startFpsRamp(double targetFps, double seconds, std::string *error)
ref core src/ApertarCoreApp.cpp 9287 void ApertarCoreApp::stopFpsRamp()
ref core src/ApertarCoreApp.cpp 9882 if (command.name == "set_fps_ramp") {
check 3.1 | grep -c 'Stop recording before changing FPS' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.2 | grep -c 'fpsRampEnabled' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[1-9][0-9]*$
check 4.4 | grep -c 'inFpsRampGrace' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[3-9]$
check 4.2 | grep -c 'restoreFpsAfterRampLocked' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^[3-9]$
check 4.7 | grep -c 'ramp_fps' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^[2-9]$
check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'fps ramp stats:' | ^[1-9][0-9]*$
check 5.1 | find /media -name fps-ramp.txt 2>/dev/null | wc -l | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
