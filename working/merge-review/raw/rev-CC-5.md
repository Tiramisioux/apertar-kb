# Review CC-5: CameraController.cpp, ramp engine, session members, controller setters (port lines 9732-11567)

Stage 2 (review). Port = `@cinemate-port` `01f170c` (line numbers read from `git show cinemate-port:src/camera/CameraController.cpp`).
Upstream = `@upstream-1.6.0`, `/home/user/wt/core-upstream`. Diff read whole: `/home/user/build/review/diffs/CC.part05.diff` (1469 lines).
Yardstick: `raw/conv-core-camera.md` (rule ids S*, I*, N*, sections 5.*), `raw/conv-core-command-plane.md` (C1-*). `apertar-conventions.md` does not exist yet.

Scope note: as the inventory says, probe, sensor-mode choice and pre-roll appear here only as members and call sites. The slice is the
speed-ramp engine inside `CameraSession`, the Mode Ladder controller methods, and the upstream setters it touches.
Already reported elsewhere and not repeated: speed ramp as a whole (CC-4-F7), `shellQuote`/RF64 (CC-2-F16), `mode_ladder.conf` as a
second file (X-knobs-14, CC-1-F5), `ladder_text` (CC-1-F9), ladder message constants (CC-2-F14), ladder compression strings (CC-2-F15),
pre-roll pinning (CC-4-F3), phase lock (CC-4-F6), IMX585 table duplication (CC-4-F8).

## Findings

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| CC-5-F1 | Mode Ladder state machine spread over nine setters; `ladderOverride_` reset in nine places; a rule keyed to client call order | new-ground | major | yes |
| CC-5-F2 | `applySettingsLocked` gets a third `commit` flag for take-scoped FPS; other setters still persist the mid-ramp rate | mismatch | minor | yes |
| CC-5-F3 | `rampNominalShutterUs_` survives a record-format or still-mode switch: wrong shutter on the next FPS change | bug | minor | no |
| CC-5-F4 | `ladderOverride_` is not persisted: after a restart in a held Clear HDR mode the ladder is active, rung 0, and blocks manual mode | bug | minor (probable) | no |
| CC-5-F5 | `setModeLadder` returns JSON and error through out-parameters and bypasses `setErrorLocked`; dry run inside the setter | mismatch | minor | unknown |
| CC-5-F6 | `setResolution` refuses an IMX585 size the current class lacks; upstream sanitises silently | mismatch | minor | yes |
| CC-5-F7 | Experimental audio stretch on by default, needs `rubberband-cli` that no install step provides, launched by double fork + `sh -c` | new-ground | minor | yes |
| CC-5-F8 | Journal line per ramp setter call and per transition | mismatch | minor | yes |
| CC-5-F9 | Dropped-frame count leaves Core in `recording_health` (upstream: a latch only) | new-ground | minor | yes |
| CC-5-F10 | `configuredMediaRoot()` mutable process-wide global written by `CameraController::start` | mismatch | minor | yes |
| CC-5-F11 | Ticket numbers, other-project names, commit ids and dates in comments; `// ----` banners | slop | minor | no |
| CC-5-F12 | FPS refusal names a socket command and offers ramping to H.264/ProRes operators | mismatch | nit | no |
| CC-5-F13 | `(!simulateCamera_ && session_ && session_->monochromeSensor())` written out at 8 call sites | duplication | nit | no |

### CC-5-F1 Mode Ladder spread over the setters (new-ground, major)

Port, confirmed:
- Refusals added to `setResolution` (`CC:10643-10646`), `setRawBitDepth` (`:11577-11580`), `setRecordingFormat` cDNG<->lossy (`:11322-11327`), `setCdngCompression` (`:11400-11403`), `setLossyDngRatio` (`:11448-11451`), each calling `ladderActiveForLocked(settings_)`, which runs `sanitizeSettingsForSensor` twice per rung (`ladderStatesLocked`, `:10829-10855`).
- `ladderRewriteLocked` called from `setFps` (`:10712`), `restoreFpsAfterRampLocked` (`:10796`), `setStillExposureMode` (`:11258`), `setRecordingFormat` (`:11384`), `setModeLadder` (`:11087`), `applyLadderToPreset` (`:11110`), `setFpsSpeedRamp` (`:11944`).
- `ladderOverride_` written at `:10679`, `:10711`, `:11084`, `:11092`, `:11383`, `:11593`, `:11611`, `:11658`, `:11660`, `:11943`.
- `setRawBitDepth` `:11608-11612`:
  `// ... except the 16-bit that turning Clear HDR on is followed by (the hardware clear_hdr action and the touch UI send it right after set_clear_hdr).`
  `if (!(settings_.clearHdr && requested.rawBitDepth == 16)) ladderOverride_ = false;`
  Core's state now depends on which command a client sends next.

Upstream, confirmed: a mode constraint lives in one place, the sanitise chain (S15), and is applied silently (I2). `setFps` `CC:7740-7770@upstream-1.6.0`
sanitises and applies; `setResolution` `CC:7719-7737` the same. No setter knows about another setter's follow-up command. No precedent for a mode chosen from FPS.

Judgement: the pure part (`ModeLadder.hpp`, header-only `inline` functions, nested namespace) follows S4/I22 and is the right shape. The controller
part is foreign: one feature adds a gate to five setters, a rewrite to seven, and a flag with ten writes and a client-order exception. The original
developer would have to learn the override rules to change any setter. Deliberate: `09256a7` ("User changed his mind (2026-10-28): an active Mode
Ladder blocks manual resolution changes") and `d44b177` ("Clear HDR over the Mode Ladder").

Rework (simplify, keep the feature):
1. One gate: a `const char *ladderRefusal(const CaptureSettings &current, const CaptureSettings &next)` free helper (beside `unsupportedRecordingSettings`, S14 pattern) that returns `kLadderOwnsMode`/`kLadderOwnsCompression` when `next` differs from `current` in a field the ladder owns; called once in `applySettingsLocked` for non-ladder callers. The five setter refusals go.
2. One rewrite: `applySettingsLocked` calls `ladderRewriteLocked(next)` when not recording and fps/format/photo flag changed. The seven call sites go.
3. Override as a value, not bookkeeping: set in `setClearHdr`, cleared in `applySettingsLocked` when `next.fps`, `next.resolution` or `next.recordingFormat` differ from `settings_` (bit depth excluded, so the touch UI's follow-up 16-bit no longer needs a special case). Drop the `setRawBitDepth` exception.
Risk: rung changes and override rollback (`setModeLadder` `:11090-11094`, `setClearHdr` `:11657-11662`) must keep working; host tests of `ModeLadder.hpp` exist, controller paths need a Pi run. Effort M.

### CC-5-F2 `commit` flag on `applySettingsLocked` (mismatch, minor)

Port: `bool CameraController::applySettingsLocked(CaptureSettings nextSettings, bool requiresReconfigure, bool commit)` `CC:12723`; `commit=false`
skips `persistSettingsLocked`, the settings event and the N9 recovery (`:12757`, `:12778`, `:12786-12788`). `applyFpsStepLocked` passes `!rampingTake` and
then emits the event itself (`:10777-10780`), so the flag only means "do not persist". The gap is admitted in `restoreFpsAfterRampLocked` `:10812-10815`:
"another setting may have persisted a mid-ramp value meanwhile, so write the file once more". `setIso` in a ramp take persists the mid-ramp FPS; a crash
before stop leaves it on disk.

Upstream: S8, one commit path, `applySettingsLocked(next, requiresReconfigure)` `CC:8659-8723@upstream-1.6.0`, 27 callers, always persists and emits.

Rework: drop the third parameter. In `persistSettingsLocked` (`CC:12795`), write `rampTakeBaseFps_` for `fps` while `recording_ && rampTakeChanged_`
(one place, covers every setter). `applyFpsStepLocked` then calls the two-argument form; `restoreFpsAfterRampLocked` loses its "write once more" branch.
Effort S.

### CC-5-F3 Keep-exposure nominal survives a format switch (bug, minor)

Port: `rampNominalShutterUs_` is set at the first FPS step in keep-exposure mode (`CC:10751-10752`) and reset only by `setShutterUs` (`:11201`),
`setShutterAuto` (`:11211`), `setFpsSpeedRamp` (`:11936`) and preset load (`:12665`). `setRecordingFormat` loads another profile's `shutterUs`
(`:11356`) and `setStillExposureMode` restores geometry, neither resets it.
Failing input: ramp on, `shutter=exposure`, cDNG shutter 20000 us, `set_fps 30` (nominal = 20000). `set_record_format mlv` whose profile has
shutter 10000 us. `set_fps 25`: `next.shutterUs = min(20000, 40000) = 20000`; the MLV profile's 10000 us is lost.
Rework: reset `rampNominalShutterUs_` wherever a profile replaces `settings_` (setRecordingFormat profile swap, photo/video switch), or store the
nominal per take only (set in `startRecording`, cleared in `restoreFpsAfterRampLocked`). Effort S.

### CC-5-F4 Override lost at restart (bug, minor, probable)

`ladderOverride_` is a plain member (`CameraController.hpp`), never persisted; the constructor loads the ladder after the settings (`CC:10509-10514`)
and does not rewrite. Saved state Clear HDR (held over the ladder) + ladder on: after restart `ladderActiveForLocked` is true (override false), the
mode matches no rung (`ladder_rung=0`), and `set_resolution`/`set_raw_bit_depth` are refused with `kLadderOwnsMode` until an FPS change moves to a rung.
Probable: read from code; settle with a Pi restart test (`get_state` before and after). Rework: with F1's value-shaped override, derive it at load
(`clearHdr` differs from the rung chosen for `fps`), or rewrite once in the constructor. Effort S.

### CC-5-F5 `setModeLadder` signature (mismatch, minor)

Port `CC:11045-11102`: `bool setModeLadder(const std::optional<std::string> &rungs, std::optional<bool> enabled, std::optional<bool> rampReady,
bool dryRun, std::string *json, std::string *error)`; errors go to `*error` (`:11050`, `:11057`, `:11074`, `:11078`, `:11093`), not `setErrorLocked`;
App replies `"mode_ladder":` + json (`App:14093-14107@cinemate-port`).
Upstream: S7, `bool` setters on `CameraController` + `lastError()`; App replies `settingsBody(camera_.settings())` or `camera_.lastError()`
(`App:9242-9249@upstream-1.6.0`); I1 `setErrorLocked("..."); return false;`. Read-only data has its own getter (`sensorModes()`).
Rework: `bool setModeLadder(rungs, enabled, rampReady)` with `setErrorLocked`; a `std::string modeLadderPreviewJson(rungs, enabled, rampReady) const`
for `dry_run` (no state change, so not a setter); App builds the reply from `modeLadderJson()` after a successful set. Effort S.

### CC-5-F6 IMX585 explicit size refused (mismatch, minor)

Port `CC:10656-10664`: `if (!apertar::imx585::find(classFor(current.rawBitDepth, current.clearHdr), ...)) { setErrorLocked(wanted.toString() + " is not a mode of the IMX585 at " ...); return false; }`.
Upstream `CC:7719-7737@upstream-1.6.0`: `validateResolution` refuses only unknown sizes ("Unsupported resolution.", `:8767`); a known size the
sensor cannot run is sanitised and the reply carries the effective value (I2).
Deliberate: `caa0153` "Explicit set_resolution refuses a size the class lacks; bit depth and Clear HDR changes take the nearest row."
Verdict: the sentence is good (I5) and the operator learns why; but it is a second policy beside the sanitiser. Either accept as documented
new behaviour for IMX585 only, or let the sanitiser pick the nearest row as for bit depth and Clear HDR. Effort S. Ask the owner.

### CC-5-F7 Audio stretch (new-ground, minor)

Port: `fpsSpeedRampStretchAudio = true` default (`Types.hpp:149@cinemate-port`); `launchAudioStretch` `CC:9939-10007` builds a `/bin/sh -c` string
(`nice -n 15 rubberband ... && mv ... || { rm ...; echo ...; }; rm -f map`) and double-forks it detached. `git grep -i rubberband cinemate-port` outside
`CC` gives no hit: no install step, README line or dependency check. Commit `ca7b7c2`: "labelled experimental, on by default ... Needs rubberband-cli."
Upstream: one external program, ffmpeg, started with `fork` + `execv(argv)` and a waited child (`CC:4154-4161@upstream-1.6.0`); App also uses
`fork`+`execv` for zip (`App:6227-6258`). No experimental feature ships on by default; N8 says the operator gets a sentence naming what is missing.
Rework: default `false`; `execv` with an argv vector (no shell), rename and cleanup done by a joined `std::thread` member that waits for the child (I16)
or by the parent on the next take; check `rubberband` once when the option is switched on and refuse with a sentence if absent. Effort S-M.

### CC-5-F8 Per-step journal lines (mismatch, minor)

Port: every `set_fps` in a ramp take logs `ApertarCore fps ramp: a -> b fps shutter_us= policy=` (`CC:10772-10775`) and every applied transition logs
`ApertarCore fps ramp: frame= frame_us= delta_us= ... lag_frames=` (`CC:9847-9850`). A dial sweep logs dozens of lines.
Upstream I7: never a line for a setter call or a control change; take start and take stop get one line each (`CC:3353-3374`, `CC:3416-3423@upstream-1.6.0`).
The port already has the stop stats line (`CC:9876-9877`) and `fps-ramp.txt`, which hold the same data.
Rework: drop the setter line; keep the transition line only as a bench aid, rate-limited by I8 (`n == 1 || n % 30 == 0`) or behind the existing grace knob. Effort S.

### CC-5-F9 Drop count published (new-ground, minor)

Port: `recording_health` gains `,"recording_dropped_frames":N` (`CC:10490-10493`); `markDropped(droppedEstimate)` (`CC:10050`).
Upstream: N3 "one warning per clip, not a counter"; 5.12 "Frame counts or queue depth in the socket API: only a boolean leaves Core";
`CC:7580-7584@upstream-1.6.0` sends only `recording_has_dropped_frames`.
Protocol: additive scalar; an original UI ignores it. Deliberate (`64bbbaa`, user asked for the number). Verdict keep, document as a departure from N3.
Effort none.

### CC-5-F10 `configuredMediaRoot()` (mismatch, minor)

Port: `configuredMediaRoot() = mediaRoot;` in `CameraController::start` (`CC:10543`); `inline std::string &configuredMediaRoot()` (`src/util/MediaProfile.hpp:214`),
read by the raw buffer count helpers (`MediaProfile.hpp:224`, `:232`).
Upstream: the media root is a member of the controller (`mediaRoot_`) passed into the session as an argument (`session_->startRecording(mediaRoot_, ...)`);
I17 function-local statics only for one-off process values, not mutable state written from a setter; S25 CC reaches nothing outside itself.
Rework: pass `mediaRoot_` to `CameraSession::start`/`reconfigure` and on to the buffer count helper as a parameter. Fold with CC-3-F1 (process-wide globals). Effort S.

### CC-5-F11 Internal vocabulary (slop, minor)

`CC:9741` `// ---- Speed ramping (T31) ---`; `:9749-9750` "T23/T29"; `:9855` "(T28)"; `:9931` "Experimental (request 19)", "measured 2026-10-28";
`:10402`, `:10415`; `:10642`, `:10712`, `:10760`, `:10823` "T34"; `:10823` `// ---- Mode ladder (T34) ---`; `:10900` "(decision 9)";
`:10726` "(Cinemate ff59dd8: ...)"; `:10737`, `:10748` "Cinemate's shutter_a_sync_mode", "Cinemate's exposure_time_nominal"; `:11322`, `:11384`, `:11258` "T34".
Upstream I19: no ticket numbers, author or date; `grep -c '// ----' CC@upstream-1.6.0` = 0. Rework: delete the tags, dates and Cinemate references; keep the
"why" sentences. Effort S.

### CC-5-F12 FPS refusal text (mismatch, nit)

Port `CC:10692`: "Stop recording before changing FPS, or enable FPS ramping (set_fps_speed_ramp) for cDNG/MLV takes." is shown in H.264/ProRes takes too
(the format check comes after). Upstream `CC:7744@upstream-1.6.0` "Stop recording before changing FPS so video and audio keep the same timeline." I5: no
identifiers. Rework: check format first; keep the upstream sentence for processed formats and ramp-off; for raw takes "... or turn on Speed Ramp." Effort S.

### CC-5-F13 Mono flag expression repeated (duplication, nit)

`(!simulateCamera_ && session_ && session_->monochromeSensor())` at `CC:10655`, `:10669`, `:10713`, `:10797`, `:10840`, `:11599`, `:11644`, `:12861` (and more in the file).
Upstream repeats `(!simulateCamera_ && session_) ? session_->sensorFamily() : SensorFamily::Unknown` per setter (5.13 rough edge), so repetition is upstream
style; a local `const bool monochrome = ...` next to `sensorFamily` in each setter matches it better than an inline expression. Effort S.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `apertar::ladder` / `ModeLadder.hpp` | keep | Pure header-only logic, S4/I22 shape, host-testable. Fix strings to enums (CC-2-F15) and the T34 header (CC-1-F7) |
| `mode_ladder.conf` + `modeLadderPath()` | rework-to-upstream-pattern | S20: camera settings persist only in `camera_settings.conf`. Store `mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_rungs` (one text value, as C1-I09 lists) there, carried across formats like `timecodeMode` (N14). Same as X-knobs-14 |
| `apertar::imx585` tables (`Imx585Modes.hpp`) | keep | 62/62/29/34 modes per class cannot be `switch` cases; judged in CC-1/CC-4 (CC-4-F8 duplication) |
| `imx283ActiveForTransport` / `Imx283Modes.hpp` | keep | New sensor, R1 recipe; outside this slice |
| `FramePhaseLock` | keep | Members only here; CC-4-F6 |
| Speed-ramp engine (`FpsRampEvent`, `noteFpsChange`, `inFpsRampGrace`, `stampFpsRampEvents`, `pairFpsRampEvents`, `writeFpsRampLog`, `rampMutex_`) | simplify | Session members + free logic follows S3; env knob follows I9; trim journal lines (F8) |
| Audio stretch (`PendingAudioStretch`, `launchAudioStretch`, `wavSampleRate`, `shellQuote`) | simplify | Default off, `execv` without shell, dependency check (F7) |
| Pre-roll sampler members | keep | Atomics on the session, I16 counters; logic judged in CC-4-F3 |
| Ladder controller methods (`fillLadderFieldsLocked`, `ladderStatesLocked`, `ladderRewriteLocked`, `ladderActiveForLocked`, `fillRungExtrasLocked`, `modeLadderJsonLocked`, `modeLadderJson`, `setModeLadder`, `applyLadderToPreset`) | simplify | `Locked` suffix and `const` correct (I10, I24); collapse gates and rewrites into `applySettingsLocked` (F1); fix `setModeLadder` signature (F5) |
| `applyFpsStepLocked`, `restoreFpsAfterRampLocked` | simplify | Split of `setFps` is fine; drop the `commit` flag (F2); restore at `stop()` could just persist the base rate |
| `ladderOverride_`, `rampNominalShutterUs_`, `rampTakeBaseFps_`, `rampTakeChanged_` | simplify | Override as a derived value (F1, F4); nominal reset with the profile (F3) |
| `configuredMediaRoot()` | rework-to-upstream-pattern | Pass the media root as an argument (F10) |

## Conforms

- `setCdngLog` (`CC:11409-11435`): own enum, field, setter, command (S13); lock, gate with sentences, `applySettingsLocked` (I1, I5).
- Camera-wide switches carried across format profiles exactly where upstream carries `tuningFile`/`timecodeMode`/`exposureMetering` (`CC:11344-11369@cinemate-port` vs `CC:7945-7951@upstream-1.6.0`, N14).
- `APERTAR_FPS_RAMP_GRACE_FRAMES`: read where used, default, bounds, silent fallback (I9, `CC:9757-9766`).
- Clear HDR refusals of auto ISO/WB and the `set_iso_auto enabled=false` lock: setter gate + sentence (I1, I5); `enabled=` has precedent in `set_clear_hdr enabled=`; the sanitiser holds the rule for loads and presets.
- `#else` branch keeps `settings_`, `sessionSettingsMutex_`, `sensorFamily_` so Core builds without libcamera (I18, `CC:10441-10447`).
- Ramp setter refusals keep N5 by default: `fpsSpeedRamp = false` (`Types.hpp:143`), and H.264/ProRes/stills keep the refusal.
- `setModeLadder` and `setClearHdr` roll back the ladder and override when the apply fails (N9 spirit, `CC:11090-11094`, `:11657-11662`).
- `saveModeLadderLocked` uses `settingsFile::atomicWrite` (I25).
- `get_mode_ladder` reply nests arrays of objects; `list_sensor_modes` `modes` (`App:10042-10048@upstream-1.6.0`) is the precedent; the command input `rungs=` is one text value (C1-I09).
- Speed ramp gates on `rampMutex_` for the event list only; the completion thread never waits for storage (N2).

## Skeptic

Stage 3. Every finding re-read at `@cinemate-port` `01f170c` (`/home/user/Apertar-Core`) and `@upstream-1.6.0` `35dbe67` (`/home/user/wt/core-upstream`).

| Id | Verdict | Why |
| --- | --- | --- |
| CC-5-F1 | corrected | Lines confirmed (5 gates, 7 rewrites, 10 override writes, two sanitiser runs per rung in `ladderStatesLocked` `CC:10829-10855`). But a one-line setter gate `if (...) { setErrorLocked(...); return false; }` is upstream's own gate shape (`setResolution` `if (recording_)` `CC:7714-7717@upstream-1.6.0`, I1), and each rewrite is a one-line helper call like `restoreModeGeometryLocked`; moving them into `applySettingsLocked` would need a caller flag (ladder callers pass a rung) and would break `setFps`, which needs the rewritten FPS before the shutter rescale (`CC:10712-10732`). Not closer to upstream. The 16-bit exception is keyed to a value (`clearHdr && 16`), not to call order. What survives: the override bookkeeping. Severity major -> minor; rework narrowed |
| CC-5-F2 | corrected | Not a mismatch: upstream already has the flag, `bool applySettingsLocked(CaptureSettings, bool requiresReconfigure, bool commit = true)` (`CameraController.hpp:92@upstream-1.6.0`), used by `applyCapturePreset` with `false` and the caller persisting/emitting itself (`CC:8627-8638@upstream-1.6.0`). The port's `applyFpsStepLocked` copies that pattern. `conv-core-camera.md` S8 misquotes the signature. What survives: the mid-ramp FPS can reach the file through another setter during a take; restore at stop repairs it, so only a crash or power loss mid-take keeps it. Category bug, severity nit |
| CC-5-F3 | corrected | Confirmed for `setRecordingFormat` (`next = saved->second` `CC:11356`, no reset). Dropped the still-mode half: `setStillExposureMode` uses `restoreModeGeometryLocked` (`CC:12804-12820`), which restores resolution, bit depth, Clear HDR and fps, not the shutter |
| CC-5-F4 | stands | Constructor `CC:10508-10514` loads the ladder after the settings; no `ladderRewriteLocked` in the constructor or `start` (`grep -n ladderRewriteLocked`); `ladderOverride_` is a plain member (`CameraController.hpp:245-249`). Still probable: needs a Pi restart. Recovery exists (`set_clear_hdr` or an FPS change), so minor is right |
| CC-5-F5 | stands | Signature `CC:11045-11046`, `*error` writes `CC:11050`, `:11057`, `:11093`; upstream `CameraController.hpp` has no `std::string *error` out-parameter at all. Small correction: not the only one; `previewClipName` (`.hpp:95`) and `applyLadderToPreset` (`.hpp:109`) also use `*error`, both port |
| CC-5-F6 | stands | `CC:10656-10664` confirmed; upstream `setResolution` `CC:7719-7737` refuses only via `validateResolution` (`"Unsupported resolution."` `CC:8767`). Owner decision, `caa0153` message says it |
| CC-5-F7 | corrected | Code and default confirmed (`Types.hpp:149` `= true`; `CC:9939-10007`; no `rubberband` outside CC). Correction: upstream does run shell strings (`runShellCommandCapture` `::popen` `App:1501-1505@upstream-1.6.0`), so the shell is not a second launch style in the codebase; the detached double fork with no waiter is. "On by default" is the user's own wish (`ca7b7c2`), so the default is an owner decision, not a rework item |
| CC-5-F8 | stands | `CC:10772-10775` per setter, `CC:9847-9850` per applied transition; upstream I7 has no `std::cerr` in `CC:7609-8489` (setters) |
| CC-5-F9 | stands | `CC:10490-10493` vs `CC:7580-7584@upstream-1.6.0`; `64bbbaa` "the user wants the number" |
| CC-5-F10 | corrected | Confirmed; readers are more than the reviewer listed: `CC:1466-1467`, `CC:4364`, `CC:4718` (inside a function-local static) and `src/cdng/CdngEncoder.cpp:91` (encoder, no controller at hand). Passing a parameter there is effort M. First added in `26da30e` |
| CC-5-F11 | stands | Banner is at `CC:9742` (not 9741); four `// ----` banners in port CC (`:1108`, `:9742`, `:10823`, `:12039`), 0 upstream; 29 lines with T-numbers, Cinemate or "decision" |
| CC-5-F12 | stands | `CC:10691-10697`: the ramp-off message comes before the format check |
| CC-5-F13 | stands | 8 inline copies of `(!simulateCamera_ && session_ && session_->monochromeSensor())` |

## Final findings

### CC-5-F1 [new-ground, minor] Clear HDR ladder override kept by ten scattered writes and a 16-bit exception in setRawBitDepth
- where: `src/camera/CameraController.cpp:10679@cinemate-port`; `:10711`; `:11084`; `:11092`; `:11383`; `:11593`; `:11608-11612`; `:11656-11662`; `:11943`
- port way: `ladderOverride_` (set by `setClearHdr` when the ladder was active) is cleared by hand in `setResolution`, `setFps` (not in a take), `setModeLadder`, `setRecordingFormat`, `setRawBitDepth` (twice) and `setFpsSpeedRamp`, and rolled back in two places. `setRawBitDepth` keeps it for a 16-bit request in Clear HDR because "the hardware clear_hdr action and the touch UI send it right after set_clear_hdr". The five refusal gates (`kLadderOwnsMode`/`kLadderOwnsCompression`) and seven `ladderRewriteLocked` calls are one-line helper calls and are not part of this finding.
- Apertar way: no precedent for a flag that one setter sets and six others clear. Upstream keeps cross-setting rules in values passed through the sanitiser (S15, `setFps` `CC:7740-7770@upstream-1.6.0`), and no setter comment refers to another client's next command.
- why it matters: to change any of six setters the original developer has to know the override rule; the 16-bit exception is explained by client behaviour, not by camera state.
- rework: one helper `void endLadderOverrideLocked(const CaptureSettings &next)` called from `applySettingsLocked` that clears `ladderOverride_` when not recording and `next.fps`, `next.resolution` or `next.recordingFormat` differ from `settings_`. Keep the explicit clears only where no mode value changes (`setModeLadder`, `setFpsSpeedRamp` Ramp-ready) and the set/rollback in `setClearHdr`. Bit depth changes no longer clear it (Clear HDR 16 <-> 12 stays a manual hold), so the `setRawBitDepth` exception and its two writes go. Gates and rewrites stay in the setters.
- rework risk: rollback paths in `setModeLadder` (`:11090-11094`) and `setClearHdr` (`:11657-11662`); needs a Pi check of Clear HDR toggles from the dial and touch UI with the ladder on.
- effort: S. deliberate: yes (`09256a7` ladder blocks manual mode; `d44b177` Clear HDR over the Mode Ladder; fork-log: not yet run on the camera).

### CC-5-F2 [bug, nit] A mid-ramp FPS can be written to camera_settings.conf by another setter during a take
- where: `src/camera/CameraController.cpp:10777-10780@cinemate-port`; `:10812-10815`; `:12795`
- port way: ramp steps call `applySettingsLocked(next, reconfigure, false)` and emit the event themselves, the same pattern as upstream `applyCapturePreset`. Any other setter during the take (`set_iso`, `set_wb`) commits with `persistSettingsLocked`, which writes the current mid-ramp `fps`. `restoreFpsAfterRampLocked` writes the file again at stop.
- Apertar way: `applySettingsLocked(..., bool commit = true)` (`CameraController.hpp:92@upstream-1.6.0`); `applyCapturePreset` passes `false` and persists/emits after (`CC:8627-8638@upstream-1.6.0`). The commit flag itself conforms.
- why it matters: a crash or power loss during a ramp take leaves the mid-ramp FPS as the saved FPS.
- rework: in `persistSettingsLocked`, write `rampTakeBaseFps_` as `fps` while `recording_ && rampTakeChanged_`; then delete the "write once more" branch in `restoreFpsAfterRampLocked`. Keep the `commit` flag.
- effort: S. deliberate: yes for the take-scoped step (`faa2958`); the leak is not.

### CC-5-F3 [bug, minor] rampNominalShutterUs_ survives a record-format switch
- where: `src/camera/CameraController.cpp:10751-10755@cinemate-port`; `:11356`
- port way: the keep-exposure nominal is set at the first FPS step and reset only by `setShutterUs` (`:11201`), `setShutterAuto` (`:11211`), `setFpsSpeedRamp` (`:11936`) and preset load (`:12665`). `setRecordingFormat` replaces settings with the saved profile (`next = saved->second`, `:11356`) without resetting it.
- Apertar way: no precedent.
- why it matters: ramp on, `shutter=exposure`, cDNG shutter 20000 us, `set_fps 30` (nominal 20000); `set_record_format mlv` with a 10000 us profile; `set_fps 25` sets `min(20000, 40000) = 20000`, overwriting the MLV profile's shutter.
- rework: reset `rampNominalShutterUs_ = 0` in `setRecordingFormat` when a saved profile is loaded, or make the nominal take-scoped (set in the take, cleared in `restoreFpsAfterRampLocked`).
- effort: S. deliberate: no.

### CC-5-F4 [bug, minor] ladderOverride_ not persisted: after a restart a held Clear HDR mode sits outside the ladder and manual mode is refused (probable)
- where: `src/camera/CameraController.cpp:10508-10514@cinemate-port`; `src/camera/CameraController.hpp:245-249@cinemate-port`
- port way: the override is a plain member; the constructor loads `mode_ladder.conf` after the settings and neither it nor `start` calls `ladderRewriteLocked`.
- Apertar way: no precedent.
- why it matters: ladder on and Clear HDR held by override, then restart: `ladder_active=true`, `ladder_rung=0`, and `set_resolution`/`set_raw_bit_depth` refused with `kLadderOwnsMode` until an FPS or Clear HDR change. Settle with `get_state` before and after a Core restart on the Pi.
- rework: with F1's value-shaped clear, derive the override at load (Clear HDR mode differs from the rung for `fps` -> override on), or call `ladderRewriteLocked` once at start.
- effort: S. deliberate: no.

### CC-5-F5 [mismatch, minor] setModeLadder returns JSON and error through out-parameters, bypasses setErrorLocked; dry run inside a setter
- where: `src/camera/CameraController.cpp:11045-11102@cinemate-port`; `src/ApertarCoreApp.cpp:14093-14107@cinemate-port`
- port way: `bool setModeLadder(optional rungs, optional enabled, optional rampReady, bool dryRun, std::string *json, std::string *error)`; errors written to `*error`, `lastError_` not set. `previewClipName` and `applyLadderToPreset` (both port) also take `*error`.
- Apertar way: S7/I1 `bool` setters with `setErrorLocked("..."); return false;` and `lastError()`; App replies `settingsBody(camera_.settings())` or `camera_.lastError()` (`App:9242-9249@upstream-1.6.0`); no `std::string *error` parameter in upstream `CameraController.hpp`; read-only data has its own getter (`sensorModes()`).
- why it matters: App needs a special reply path, and the error is not in `lastError()`.
- rework: `bool setModeLadder(rungs, enabled, rampReady)` using `setErrorLocked`; `std::string modeLadderPreviewJson(rungs, enabled, rampReady) const` for `dry_run`; App replies with `modeLadderJson()` + `settingsBody` after success.
- effort: S. deliberate: unknown.

### CC-5-F6 [mismatch, minor] setResolution refuses an IMX585 size the current class lacks; upstream sanitises silently
- where: `src/camera/CameraController.cpp:10656-10664@cinemate-port`
- port way: `apertar::imx585::find(classFor(bits, clearHdr), w, h)` fails -> `setErrorLocked("<size> is not a mode of the IMX585 at N-bit.")`.
- Apertar way: `validateResolution` refuses only unknown sizes (`"Unsupported resolution."`, `CC:8767@upstream-1.6.0`); a known size is sanitised and the reply carries the effective value (I2, `setResolution` `CC:7719-7737`).
- why it matters: a second size policy beside the sanitiser, which still maps bit depth and Clear HDR changes to the nearest row.
- rework: owner decision: either document it as a deliberate IMX585 refusal, or let `sanitizeSettingsForSensor` pick the nearest row as it does for bit depth and Clear HDR.
- effort: S. deliberate: yes (`caa0153`).

### CC-5-F7 [new-ground, minor] Experimental audio stretch needs uninstalled rubberband-cli and is launched as a detached double fork of sh -c
- where: `src/camera/CameraController.cpp:9933-10007@cinemate-port`; `include/apertar/core/Types.hpp:149@cinemate-port`
- port way: `fpsSpeedRampStretchAudio = true` by default; `launchAudioStretch` builds a shell string (`nice`/`rubberband`/`mv`/`rm`/`echo`), double-forks, `setsid`, `execl("/bin/sh", "sh", "-c", ...)`; nobody waits for the grandchild. No install step, README line or dependency check for `rubberband` (`git grep -i rubberband` hits CC only).
- Apertar way: external programs run as waited children: ffmpeg `fork` + `execv(argv)` (`CC:4154-4161@upstream-1.6.0`), zip (`App:6227-6258`), `aplay` `execvp` (`AudioRecordingSession.cpp:287`); shell strings go through `popen` with the result read (`App:1501-1505`). Nothing upstream is detached. N8: the operator gets a sentence naming what is missing.
- why it matters: on a stock install every ramp take with changes logs a rubberband failure and nothing tells the operator; a detached process nobody tracks can outlive a stop or a media unmount.
- rework: launch `rubberband` with `execv` and an argv vector; do the rename and cleanup in a joined `std::thread` member that waits for the child (I16); check for `rubberband` when the option is switched on and refuse with a sentence if it is missing. The default `true` is the user's choice (`ca7b7c2`); keep it unless the owner changes it.
- effort: M. deliberate: yes (`ca7b7c2` "labelled experimental, on by default ... Needs rubberband-cli").

### CC-5-F8 [mismatch, minor] Journal line per ramp setter call and per applied transition
- where: `src/camera/CameraController.cpp:10772-10775@cinemate-port`; `:9847-9850@cinemate-port`
- port way: every `set_fps` in a ramp take logs `fps ramp: a -> b fps shutter_us= policy=`; every applied transition logs `frame= frame_us= delta_us= ... lag_frames= superseded=`.
- Apertar way: I7: no line for a setter call or control change (no `std::cerr` in `CC:7609-8489@upstream-1.6.0`); one line each at take start and stop (`CC:3353-3374`, `CC:3416-3423`).
- why it matters: a dial sweep floods the journal; the same data is in `fps-ramp.txt` and the stop stats line (`CC:9876-9877`).
- rework: delete the setter line; rate-limit the transition line with `n == 1 || n % 30 == 0` (I8) or drop it.
- effort: S. deliberate: yes (`faa2958`; lag_frames sizes the grace window).

### CC-5-F9 [new-ground, minor] Dropped-frame count published in recording_health
- where: `src/camera/CameraController.cpp:10490-10493@cinemate-port`; `:10050@cinemate-port`
- port way: `recording_health` adds `"recording_dropped_frames":N`; `markDropped(count)`.
- Apertar way: N3 "one warning per clip, not a counter"; only `recording_has_dropped_frames` leaves Core (`CC:7580-7584@upstream-1.6.0`).
- why it matters: departs from a stated upstream intent; additive, so unmodified UIs ignore it.
- rework: keep; document it as a deliberate departure from N3.
- effort: S. deliberate: yes (`64bbbaa` "the user wants the number").

### CC-5-F10 [mismatch, minor] configuredMediaRoot() is a mutable process-wide global written by CameraController::start
- where: `src/camera/CameraController.cpp:10543@cinemate-port`; `src/util/MediaProfile.hpp:214-234@cinemate-port`; readers `CC:1466-1467`, `CC:4364`, `CC:4718`, `src/cdng/CdngEncoder.cpp:91`
- port way: `configuredMediaRoot() = mediaRoot;` and the buffer-count and media-tune helpers read the global.
- Apertar way: the media root is the controller member `mediaRoot_`, passed as an argument (`start(const std::string &mediaRoot, ...)` `CC:3268`, `startRecording(mediaRoot, ...)` `CC:5526@upstream-1.6.0`); I17 statics are for one-off process values only.
- why it matters: hidden coupling between the controller, util headers and the encoder; same pattern as CC-3-F1.
- rework: pass `mediaRoot_` into `CameraSession` start/reconfigure and on to `mediaExtraRawBuffersFor(root)` / `mediaTuneFor(root)`; give the encoder its `MediaTune` at construction; delete the global.
- effort: M. deliberate: yes (`26da30e`).

### CC-5-F11 [slop, minor] Ticket numbers, Cinemate references, commit ids and dates in comments; // ---- banners
- where: `src/camera/CameraController.cpp:9742@cinemate-port`; `:9931`; `:10726`; `:10823`; `:10900`; also `:1108`, `:12039` banners
- port way: T31, T34, T23/T29, T28, "request 19", "decision 9", "Cinemate ff59dd8", "Cinemate's shutter_a_sync_mode", "measured 2026-10-28"; four `// ----` banners.
- Apertar way: I19: no ticket numbers, author or date; 0 `// ----` banners in CC@upstream-1.6.0.
- why it matters: the references mean nothing to the original developer.
- rework: delete the tags, dates, commit ids and Cinemate names and the banners; keep the "why" sentences.
- effort: S. deliberate: no.

### CC-5-F12 [mismatch, nit] FPS refusal names a socket command and offers ramping to H.264/ProRes takes
- where: `src/camera/CameraController.cpp:10691-10697@cinemate-port`
- port way: "Stop recording before changing FPS, or enable FPS ramping (set_fps_speed_ramp) for cDNG/MLV takes." shown before the format check.
- Apertar way: "Stop recording before changing FPS so video and audio keep the same timeline." (`CC:7744@upstream-1.6.0`); I5 no identifiers.
- why it matters: an H.264 operator is told to enable a feature that cannot work in H.264.
- rework: check the format first; keep the upstream sentence for processed formats and when ramp is off; for raw takes say "... or turn on Speed Ramp."
- effort: S. deliberate: no.

### CC-5-F13 [duplication, nit] Mono flag expression repeated at each sanitiser call
- where: `src/camera/CameraController.cpp:10655@cinemate-port`; `:10669`; `:10713`; `:10797`; `:10840`; `:11599`; `:11644`; `:12861`
- port way: `(!simulateCamera_ && session_ && session_->monochromeSensor())` inline 8 times.
- Apertar way: upstream computes `sensorFamily` once per setter as a local (`CC:7722-7724@upstream-1.6.0`).
- why it matters: noise in every sanitiser call.
- rework: a local `const bool monochrome = ...` next to `sensorFamily` in each setter.
- effort: S. deliberate: no.
