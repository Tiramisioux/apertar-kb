# rev-CC-2: review of `CameraController.cpp`, slice 2

Stage 2 of 3. Slice: `diffs/CC.part02.diff`, new lines 2779-4542 `@cinemate-port` (`01f170c`).
Yardstick: `raw/conv-core-camera.md` (rule ids S, I, N, R, 5.x) and the `core-upstream` worktree (`@up` = `upstream-1.6.0`).
Inventory: `raw/inv-CC-2.md`. Hint "phase lock" does not apply (no phase-lock code here, inventory section 0).

Short names: `CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`.

## 1. Verdict in one table

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| CC-2-F1 | Camera side reads `apertar-hardware.conf` (`[camera]` ISO caps) | mismatch | major | yes |
| CC-2-F2 | Queue re-reads `[storage]` from disk at each take; third copy of the candidate list | mismatch | major | yes |
| CC-2-F3 | Upstream lossless cDNG limits changed (ISO 800->1600, auto ISO kept on IMX585, IMX585 fps 30 -> mode max) | removed-upstream-behaviour | major | yes |
| CC-2-F4 | Lossless IMX585 fps cap lifted from a Pi 5 measurement, no board gate | pi-compat | major | partly |
| CC-2-F5 | Sync thread fsyncs clip frames by default, against upstream intent N10 | new-ground | major | yes |
| CC-2-F6 | Media tuning file feeds per-take writer knobs (`sync_ms`, workers, queue) | mismatch | major | yes |
| CC-2-F7 | Process-wide flush-abort callback registered by the queue | mismatch | major | yes |
| CC-2-F8 | `FrameBufferGauge` is a hidden process-wide singleton | mismatch | minor | yes |
| CC-2-F9 | `stop()` joins copy workers without a bound; they `mkdir` on the medium | bug | major (probable) | no |
| CC-2-F10 | fps ceiling over-built: dead `backendMaximumFps`, `FpsCeiling.hpp`, three read-once env switches | slop | minor | partly |
| CC-2-F11 | Env knobs parsed by hand, read once, logged; not `unsignedEnvValue`/`boolEnvValue` at use | mismatch | minor | no |
| CC-2-F12 | Ticket numbers, names, dates, take ids, KB paths in comments | slop | minor | no |
| CC-2-F13 | Stale comments contradict the code | slop | minor | no |
| CC-2-F14 | Ladder messages as `constexpr` constants with a wrong menu path | mismatch | minor | no |
| CC-2-F15 | Ladder compression compared as strings, not enums | mismatch | minor | no |
| CC-2-F16 | `shellQuote` + `wavSampleRate` exist for a `/bin/sh -c` launch; RIFF only | mismatch / bug | minor | no |
| CC-2-F17 | Uncompressed writer count and queue depth now follow the filesystem | removed-upstream-behaviour | minor | yes |
| CC-2-F18 | `static bool warned` inside a member function | mismatch | nit | no |
| CC-2-F19 | "CineMate Log" product name in Core log text | slop | nit | no |
| CC-2-F20 | `isoForMeasuredGain` comment separated from its function; `buildCdngLogTake` optional round-trip | slop | nit | no |

## 2. Findings

### CC-2-F1 Camera side reads `apertar-hardware.conf` (`[camera]`)

- Port: `CC:2933-2984 @port` `struct CameraSection` / `loadCameraSection()` opens the hardware file and parses `[camera] clear_hdr_iso_max_12bit|16bit`; `cameraSection()` caches it (`CC:3009-3014`); template keys `App:5078-5079 @port`.
- Apertar way: S22 "The camera side never reads `apertar-hardware.conf`" (0 hits in `src/camera` `@up`). Limits that depend on sensor and format are literals in the sanitiser: `settings.iso = std::min<uint32_t>(settings.iso, 800u);` `CC:2483 @up` (5.14 "lossless caps"). Bench overrides are env vars (N11, R5).
- Why: the two values are driver facts (gain code 57 / 80 of the port's imx585 driver, comment `CC:2935-2940`), not operator choices. The parser is a new INI dialect (deletes all whitespace, stops at the first file even when `[camera]` is missing; upstream `GpioInput::loadConfig` goes on, `GpioInput.cpp:498-499 @up`).
- Rework: `constexpr uint32_t kClearHdrMaxIso12 = 720; kClearHdrMaxIso16 = 1585;` next to `kLosslessMaxIso`; `clearHdrIsoCap` returns them. If a bench override is wanted: `unsignedEnvValue("APERTAR_CLEAR_HDR_ISO_MAX_12", 720, 0, 51200)` at use (R5). Delete `CameraSection`, `loadCameraSection`, `cameraSection`, the `[camera]` block of the template (`App:5074-5079`) and its README text. Effort S. Risk: an operator who edited the keys loses them (none recorded).

### CC-2-F2 `loadBufferConf` re-reads `[storage]` per take

- Port: `CC:2986-3007` reads the whole hardware file from disk, hands it to `bufferbudget::parseBufferConf`; used `CC:4297` (frames per folder) and `CC:5505` (RAM plan, slice CC-3). The App already parses the same text from its store (`App:272-282 @port` `refreshBufferRequest`). The six-line candidate list is copied here twice (`CC:2945-2950`, `CC:2991-2996`); upstream has it once, `hardwareConfigCandidatePaths()` `GpioInput.cpp:60-76 @up`.
- Apertar way: S22; per-take options that are not camera settings travel from the App into `startRecording` as a struct: `GyroRecordingOptions` (`Types.hpp:199 @up`, filled `App:10633 @up`, taken `CC.hpp:78 @up`, 5.14).
- Rework: add `struct StorageRecordingOptions { uint32_t framesPerFolder = 0; /* buffer mode, ram fraction ... */ };` in `Types.hpp`; App fills it from its `configStore()` parse at `record_start`; `startRecording(..., storageOptions)` -> `DngRecordingQueue::startAtFolder`. Delete `loadBufferConf` and both copied candidate lists. Effort M. Also consider N11: the commit (`d7dd337`) says frames-per-folder exists for an NVMe A/B campaign, i.e. a bench knob; the Apertar form is env only (`APERTAR_CDNG_FRAMES_PER_FOLDER`, which already exists), no hardware-file key, no socket command.

### CC-2-F3 Upstream lossless cDNG limits changed

- Upstream `CC:2470-2491 @up`: `iso <= 800`, `isoAuto = false`, IMX585 fps `30.0`.
- Port `CC:3098-3158`: `kLosslessMaxIso = 1600` ("on Patrik's request"), `isoAuto` kept on the IMX585 ("Other sensors are unchecked", "unverified" per `fork-log.md:85`), IMX585 fps = mode maximum unless `APERTAR_LOSSLESS_FPS_LIMIT` (default 30 is gone).
- Why: three product-policy defaults of the original developer changed in one place, comments say "a policy, not a limit". The split into `losslessCaptureLimited` / `losslessMaximumFps` is fine; the values are the issue.
- Rework: keep upstream defaults (800, manual ISO, 30) in `enforceLosslessCaptureLimits`; offer the relaxed values as bench knobs per R5 (`APERTAR_LOSSLESS_MAX_ISO`, `APERTAR_LOSSLESS_IMX585_FPS`, read with `unsignedEnvValue` at use), or put the change in its own commit with the measurements for the original developer to accept. Effort S.

### CC-2-F4 Lossless fps cap lifted without a board gate

- Port `CC:3132-3144`: "measured lossless encoder capacity at 4K 12-bit is ~69 fps, so 30 was a policy". Measured on Pi 5 / CM5 only (inventory section 7 #9; no Pi 4 rig in the KB).
- Apertar way: board differences go through `recordingCapabilities()` (`include/apertar/core/RecordingCapabilities.hpp:18-51 @up`, bcm2712 vs bcm2711).
- Failing input: Pi 4, IMX585, lossless cDNG 4K, fps 60 -> sanitiser allows 60 (probe value); the 4-core A72 cannot encode that; drops. Probable (no Pi 4 test).
- Rework: if F3's relaxation stays, gate it on the Pi 5-class flag from `recordingCapabilities()`; else 30.

### CC-2-F5 Sync thread fsyncs clip frames by default

- Port `CC:4353-4369`: `syncMs` default 1000; a `syncLoop` thread fsyncs written DNGs and the folder every second (commits `4ce382e`, `5b68f1f`).
- Apertar way: N10 "Clip frames are not synced, for throughput"; `AtomicStillFile.hpp:31-32 @up`: "Keep this out of the continuous recording path: syncing each video frame would destroy throughput."
- Deliberate: yes, with evidence (pull test C0011 258/281 frames, `fork-log.md:53`; the syncfs variant cost 782 drops, comment `CC:4357`).
- Verdict: new ground that contradicts a stated upstream intent. Keep only as opt-in: default `APERTAR_MEDIA_SYNC_MS` 0, or keep the default and write it up for the original developer as a deliberate departure with the numbers. The shape (one extra worker counted by `spawnWorker`, value printed on the clip line) conforms to I16 and R5.

### CC-2-F6 Media tuning file feeds writer knobs

- Port `CC:4364-4365`: `mediaTuneForConfiguredRoot()` reads `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf` (`MediaTune.hpp:27-28`) for `sync_ms`; `mediaProfile_.writer.workers/queueFrames` (`CC:4321`, `CC:4327`) from the profile and file.
- Apertar way: N11 "Internal tuning stays out of the files the operator edits. Knobs are undocumented environment variables"; 5.12 "A config file or config section for recorder tuning" is absent by design.
- Rework: delete `MediaTune.hpp` and its tmpfiles/override path; keep the env knobs (`APERTAR_MEDIA_SYNC_MS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES`). Keep `MediaProfile` only if the per-filesystem defaults are measured (F17). Effort M (touches App and helper scripts outside this slice).

### CC-2-F7 Process-wide flush-abort callback

- Port: `registerFlushAbort()` in `startAtFolder` (`CC:4271`), `unregisterFlushAbort()` in the destructor (`CC:4211`); registry is a global `std::function` + mutex in `BufferBudget.hpp:239-252`, called from `handleCommand` to bypass the controller lock.
- Apertar way: the App reaches the queue only through `CameraController` methods; cross-thread signals are objects owned by the controller and passed to the queue (`RecordingDropWarning` `CC.hpp:113 @up`, ctor `CC:3251 @up`).
- Rework: `CameraController::abortFlush()` sets an `std::atomic<bool>` member of a controller-owned object that the queue got by pointer (same as `dropWarning_`); `handleCommand` calls the method. Delete the registry from `BufferBudget.hpp`. Effort M.

### CC-2-F8 `FrameBufferGauge` singleton

- Port `CC:4169-4186`: five atomics behind `frameBufferGauge()` function-local static, written by the queue, read by `frameBufferStatus()`.
- Apertar way: function-local statics are for process-lifetime one-offs (I17: `captureSettingsPersister`, `cachedPiSerial`); per-take shared state is a controller-owned object passed by pointer (`RecordingDropWarning`). Queue depth in the socket API is absent upstream (5.12, N3).
- Verdict: the feature is new ground (buffer bar); the reason (controller mutex held during drain) is sound. Rework the shape: `FrameBufferGauge bufferGauge_` member of `CameraController`, passed to `DngRecordingQueue(RecordingDropWarning*, FrameBufferGauge*)`. Effort S.

### CC-2-F9 Unbounded join of copy workers on a dead medium

- `stop()` calls `stopCopyWorkers()` (`CC:4453`) before the bounded wait; `stopCopyWorkers` joins `copyThreads_` unconditionally (`CC:5164-5174`). Copy workers call `enqueue` -> `ensurePartFolder` -> `::mkdir` on the medium (`CC:4959-4974`). Copy threads are not counted by `spawnWorker` (`CC:4387-4388`).
- Failing input: `frames_per_folder=1000`, card pulled while a copy worker crosses a part boundary; `mkdir` blocks until the NVMe timeout; `stop(true)` hangs in `join` with the controller and command locks held, which F19 (`0b1632f`) was built to prevent. Probable (depends on the kernel blocking `mkdir`).
- Rework: create part folders on a writer (which the bounded stop handles), or start copy threads through `spawnWorker` and stop them inside the bounded wait. Effort S.

### CC-2-F10 fps ceiling over-built

- `backendMaximumFps` (`CC:3425-3434`) returns `nullopt` for every input, casts both args to `void`, 3 call sites; `fpsceiling::applyBackendCap` exists only for it. `FpsCeiling.hpp` holds four one-line functions. Two env switches only reproduce earlier states: `APERTAR_FPS_LIMIT=table` (fork-main behaviour) and `APERTAR_IMX283_PROBE_FPS`.
- Apertar way: inline arithmetic in the function (`probed ? std::min(table, *probed) : table` `CC:2769 @main`; `settings.fps = std::min(settings.fps, maximumFps)` `CC:2490 @up`); S4 headers hold real pure logic, not wrappers of `std::min`.
- Rework: delete `backendMaximumFps`, `applyBackendCap`, `fpsLimitTableOnly`, `imx283ProbeFpsOnly`, `FpsCeiling.hpp`, `tools/fps_ceiling_test.cpp`; write `return probed && *probed > 0 ? (sensorFamily == SensorFamily::Imx283 ? std::min(table, *probed) : *probed) : table;`. Effort S.

### CC-2-F11 Env knobs not in the upstream form

- `losslessFpsOverride()` (`CC:3117-3130`: own `strtod` parser in `FpsCeiling.hpp`, read-once static, logs to stderr), `fpsLimitTableOnly()` (`CC:3398-3408`: string compare to "table", logs), `APERTAR_CDNG_FRAMES_PER_FOLDER` (`CC:4293-4296`: own parser, logs a bad value).
- Apertar way: I9 / R5: `unsignedEnvValue(name, default, min, max)` / `boolEnvValue` at the point of use (`CC:1027-1061 @up`, use `CC:3329-3330 @up`); a malformed value falls back silently; the effective value goes on the take-start line.
- Conforms already: `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_COPY_WORKERS`, `APERTAR_DEAD_MEDIUM_STOP_MS` use `unsignedEnvValue`.
- Rework: same helpers at use; drop the log lines; print effective values on the clip line. Effort S.

### CC-2-F12 Internal references in comments

- `CC:3025` and `CC:3070` "Patrik's rule", `CC:3034` "T34", `CC:3098-3099` "temp 753f181 ... C0013", `CC:3154` "(Patrik, 2026-10-28)", `CC:3428-3430` "(User, 2026-11-03)" and two KB paths, `CC:4318` "T29 measures", `CC:4357` "C0005, 2026-10-26".
- Apertar way: I19 (no ticket numbers, no author or date; one to three lines saying why).
- Rework: rewrite each as the constraint only, or delete. Effort S.

### CC-2-F13 Stale comments

- `CC:3378` "the 16-bit 25 is backendMaximumFps()": no such cap any more (`CC:3431-3433`).
- `CC:3481-3485` "only the named back-end cap kept": none exists.
- `CC:4317-4319` "exFAT/NTFS get 2": `MediaProfile.hpp:140-142` gives exFAT 4.
- Rework: fix with F10 and F17.

### CC-2-F14 Ladder messages

- `CC:3061-3067` `constexpr const char *kLadderOwnsMode/kLadderOwnsCompression`, text "Settings > Record > Mode Ladder"; the card is in the WebUI `modes` pane (`WCP:5151-5166`, per inventory, probable).
- Apertar way: I1 / I5: one inline sentence per `setErrorLocked(...)` (`CC:7715 @up`); no `k...` message constants and no menu paths in upstream errors.
- Rework: inline the sentence at each setter, without the path ("Turn off the Mode Ladder to choose the resolution by hand."). Effort S.

### CC-2-F15 Ladder compression as strings

- `CC:3037-3049`: `ladder::effectiveCompression(rung)` returns `"lossy_3to1"`, `"lossy_5to1"`, `"none"`, compared as strings.
- Apertar way: formats and sub-options are enums in `Types.hpp` with `toString`/`fromString` at the edge (R3 step 1; `CdngCompression`, `LossyDngRatio`).
- Rework: `ladder::Rung` stores `RecordingFormat` + `CdngCompression` + `LossyDngRatio`; parse strings once where the ladder is loaded. Effort S-M (ModeLadder.hpp).

### CC-2-F16 `shellQuote`, `wavSampleRate`

- `CC:2919-2925` `shellQuote` exists because `launchAudioStretch` runs `rubberband` through `/bin/sh -c` with a double fork (`CC:9977-9999`). Upstream `CC` starts its one program, ffmpeg, with `fork` + `execv`, no shell (`CC:4154-4161 @up`). A per-file copy of a helper is itself upstream style (S6), so the copy is not the issue; the shell is.
- `wavSampleRate` (`CC:2896-2917`) accepts `RIFF` only; Core writes `RF64` above 4 GiB (`AudioRecordingSession.cpp:911-912`); upstream's reader accepts both (`App:5806-5808 @up`). Failing input: a ramp take whose WAV passes 4 GiB -> sample rate 0 -> no stretched WAV, one log line. Nit in practice.
- Rework: `execv` with an argv vector, delete `shellQuote`; accept `RF64` in `wavSampleRate`. Effort S.

### CC-2-F17 Writer count and queue depth follow the filesystem

- Upstream `CC:3323-3330 @up`: uncompressed workers `max(2, min(4, threads))`, queue 12.
- Port `CC:4316-4327`: `min(profile workers, format count)`, queue from the profile when the medium is known. Commit `26da30e`: "Cinemate's numbers, not measured here"; fork-log "built, not tested".
- Rework: keep the upstream defaults; keep the env knobs. Restore the profile only with measurements. Effort S.

### CC-2-F18 `static bool warned` in `startAtFolder`

- `CC:4371-4373`. Upstream: `bool warned..._` member (I8, `CC:6858-6861 @up`). Rework: member, or drop the warning. Nit.

### CC-2-F19 "CineMate Log"

- Log text `CC:3985`, `CC:4008`, comment `CC:3963`. Upstream log lines name Apertar concepts only. Rename to "Log" / "cDNG Log". Nit.

### CC-2-F20 Small leftovers

- `CC:2892-2893` comment of `isoForMeasuredGain` sits above `#if` / `wavSampleRate`; the function is at `CC:2928`. Move.
- `CC:4023-4028` `buildCdngLogTake` copies the plan into locals and wraps `plan->params` in an `std::optional` only to dereference it. Use `plan->` directly.

## 3. Checked and not reported

| Item | Why it is fine |
| --- | --- |
| Split `#if APERTARCORE_HAS_LIBCAMERA` guards (`CC:2789`, `2894`, `2986`, `3309`, `3552`, `4168`, `4188`) | I18, N12: Core must build without libcamera |
| IMX283 cases in normaliser, 4K test, fps table, bit depth, crop offsets | Recipe R1 steps 6, 8, 9, 10, 11; `switch (sensorFamily)` in free functions (S11) |
| `enforceClearHdrExposureRules`, `clearHdrIsoCap` called from the sanitiser | Same place and shape as the upstream lossless caps (5.14) |
| `losslessCaptureLimited`, `losslessMaximumFps`, `modeMaximumFps`, `maximumFpsForSettings`, `maximumIsoForSettings` | Extraction so the state can publish the sanitiser's limits; logic unchanged except F3 |
| `dmabufCpuSync` free function | Body moved unchanged from `CameraSession::syncCpuReadBuffer` (`CC:6426-6436 @up`) |
| New `Stats` fields, `recording stats:` and `recording clip:` fields | I16 (counters reset in start, printed in stop), R5 step 3 |
| `spawnWorker`, bounded `stop`, refusal of a new take while stuck writers run | New ground, deliberate (`0b1632f`), fixes a recorded hang; operator sentence I5-conform |
| Protocol | No socket command, route or JSON shape is changed in this slice; new state fields are additive scalars |

## 4. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `CameraSection`, `loadCameraSection`, `cameraSection` | rework-to-upstream-pattern | F1: constants (+ env knob) |
| `loadBufferConf` | rework-to-upstream-pattern | F2: options struct from the App, like `GyroRecordingOptions` |
| `apertar::bufferbudget` | simplify | Pure budget maths fits S4; the process-wide switches and flush registry go (F7) |
| `apertar::fpsceiling` | rework-to-upstream-pattern | F10: inline arithmetic |
| `apertar::imx585` mode tables | keep | Four classes x many rows; closest precedent `kImx477Modes` array `CC:2309 @up`; pure header per S4 |
| `apertar::imx283` mode table | keep | Same |
| `apertar::ladder` | keep | New ground, off by default; F15 for its types |
| `kLadderOwnsMode`, `kLadderOwnsCompression` | simplify | F14: inline sentences |
| `losslessFpsOverride`, `imx283ProbeFpsOnly`, `fpsLimitTableOnly` | rework-to-upstream-pattern | F10, F11 |
| `backendMaximumFps` | rework-to-upstream-pattern | Dead hook; delete (F10) |
| lossless / mode / max fps and ISO helpers | keep | Carry the sanitiser's limits to the state |
| `enforceClearHdrExposureRules`, `applyClearHdrCompression`, `clearHdrIsoCap` | keep | Sanitiser pattern; F1 for the cap source, F12 for comments |
| `CdngLogPlan`, `planCdngLog`, `buildCdngLogTake` | keep | One test shared by take and state; F20 nit |
| `apertar::cdnglog` | keep | S4 pure maths header |
| `FrameBufferGauge`, `frameBufferGauge()` | rework-to-upstream-pattern | F8: controller-owned object passed by pointer |
| Flush-abort registry | rework-to-upstream-pattern | F7 |
| `spawnWorker` | keep | Needed by the bounded stop; small |
| Sync thread | simplify | F5: opt-in or documented departure |
| Copy workers | keep | Deliberate, measured (`351a3ee`); callback still never waits (N2). Fix F9 |
| `dmabufCpuSync` | keep | Moved upstream code |
| `MediaProfile`, `MediaTune`, `MediaFault` | simplify | `MediaFault` keep; `MediaTune` file goes (F6); `MediaProfile` defaults only with measurements (F17) |
| `apertar::framepath` | simplify | Keep the folder logic; knob env-only (F2) |
| `wavSampleRate` | simplify | Accept RF64 (F16) |
| `shellQuote` | rework-to-upstream-pattern | `execv` without a shell (F16) |
| Host tests in `tools/` | keep | Not built by CMake; S24 says upstream has none, decide once for the whole port, not per unit |

## 5. Conforms well

- IMX283 added along recipe R1, case by case in existing switches (`CC:2809-2814`, `2858-2859`, `3332-3339`, `3447`, `3665-3735`).
- Build without libcamera by splitting the one guard, signatures kept (I18, N12).
- Clear HDR exposure rules live in `sanitizeSettingsForSensor`, the upstream place for limits (5.14).
- Effective values of new knobs on the `recording clip:` line, new counters on `recording stats:` (R5, I16).
- New per-take knobs `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_COPY_WORKERS`, `APERTAR_DEAD_MEDIUM_STOP_MS` use `unsignedEnvValue` with bounds (I9).
- The raw copy hand-off keeps N2: the completion thread never waits; a frame without a slot is dropped and counted.
- The `record_start` refusal while stuck writers run is an operator sentence that says what to do (I5).

## Skeptic

Stage 3. Every finding re-read on both sides (`/home/user/Apertar-Core` @ `01f170c`, `/home/user/wt/core-upstream` @ `upstream-1.6.0`).

| Id | Verdict | Why |
| --- | --- | --- |
| CC-2-F1 | corrected | Core claim confirmed (`CC:2933-2984`, `App:5074-5079 @port`; 0 hits in `core-main`). Sub-claim "stops at the first file even when `[camera]` is missing" dropped: upstream `loadIna219HardwareConfig` does the same (`App:4455-4505 @up`, `return config;` after the first file). |
| CC-2-F2 | corrected | Two routes confirmed: App already publishes `framesPerFolderRequest()` from `configStore()` (`App:281-283 @port`) and the queue re-reads the file (`CC:4297`). Claim "upstream has the path list once" is wrong: upstream copies `hardwareConfigCandidatePaths()` into 5 files (`GpioInput.cpp:60`, `NeoRotary4Input.cpp:73`, `TriggerOutput.cpp:73`, `GroveAnalogInput.cpp:57`, `App:4251 @up`), per S6. The issue is two inline copies in one file on the camera side. |
| CC-2-F3 | stands | `CC:3098-3158 @port` vs `CC:2470-2491 @up` confirmed; commits and `fork-log.md:80,85` confirm deliberate, auto ISO "unverified". |
| CC-2-F4 | dropped | Failing input cannot happen: lossless cDNG is already Pi 5-class only. `RecordingCapabilities.hpp:26` gives `rawCompression` only for `bcm2712`; `supportedRecordingSettings` forces `Uncompressed` otherwise (`:87`), `unsupportedRecordingSettings` refuses (`:71-75`), same @port. |
| CC-2-F5 | corrected | Code confirmed (`CC:4353-4369`). Severity major -> minor, rework changed: the sync is carefully considered and measured (`fork-log.md:51-53`: C0007 clean, C0011 258/281 readable after a pull; syncfs variant rejected after 782 drops). Making it opt-in loses the pull-safety feature. Keep, document as a deliberate departure from N10. |
| CC-2-F6 | stands | `MediaTune.hpp:27-28`, `CC:4364-4365 @port`; 5.12/N11 confirmed. |
| CC-2-F7 | corrected | Confirmed (`BufferBudget.hpp:236-252`, `CC:4211`, `4271`, `4594`, `App:291-299`, `10119`, `12570`). Rework must stay lock-free on the controller (the drain holds `CameraController` mutex and `commandMutex_`, comment `App:286-288`). Same pattern extends to `safetyStopState()` (`BufferBudget.hpp:231-235`) and the `framesPerFolderRequest`/`clipMergeRequest` atomics; fix together. |
| CC-2-F8 | stands | `CC:4169-4186`, written in `startAtFolder`/`stop`; I17 confirmed. |
| CC-2-F9 | stands | `stopCopyWorkers` plain join (`CC:5164-5174`) called before the bounded wait (`CC:4453`); `ensurePartFolder` `::mkdir` under `partMutex_` on the copy thread (`CC:4959-4974`). Placement on the copy side is deliberate (`d7dd337`: "never a writer"); the hang was not considered. Default `frames_per_folder=0` keeps it off. |
| CC-2-F10 | stands | `backendMaximumFps` returns `nullopt` (`CC:3426-3434`), 4 call sites (`CC:3470`, `3488-3490`, `8634-8639`); `FpsCeiling.hpp` confirmed; cap removed by `31d5418`. |
| CC-2-F11 | corrected | Severity minor -> nit. Upstream has a read-once static with its own `strtoul` parser: `configuredLosslessTileRows()` `CdngEncoder.cpp:52-66 @up`. The real gap is inside `CC`: upstream uses `unsignedEnvValue`/`boolEnvValue` at use there, and knobs do not print their own stderr lines. |
| CC-2-F12 | stands | All eight lines read @port. |
| CC-2-F13 | stands | `CC:3378`, `CC:3481-3485` stale (no cap in `backendMaximumFps`); `CC:4317` "exFAT/NTFS get 2" vs `MediaProfile.hpp:142` exFAT `{4, 12, 0, true}`. |
| CC-2-F14 | corrected | Wrong path now confirmed, not probable: WebUI nav has `Record` and `Modes` (`WCP:4746-4753`), the card is in `data-panel="modes"` (`WCP:5151`, title `5166`). Constants used 7 times in `CC`. |
| CC-2-F15 | corrected | Strings are validated where the ladder is parsed (`knownCompression`, `ModeLadder.hpp:29`), so a typo is possible only in code literals. Added: `Rung` already stores `CdngLog` as an enum (`ModeLadder.hpp:26`), so the struct is half enum, half string. |
| CC-2-F16 | corrected | Shell half dropped: upstream App has its own `shellQuote` (`App:1482 @up`) and runs shell commands through `popen` (`App:1501-1505 @up`), so a quoted `/bin/sh` launch has precedent. RF64 bug stays (`CC:2899-2900 @port` vs `App:5806 @up`; `AudioRecordingSession.cpp:773`). Needs a WAV over 4 GiB on a ramp take: severity nit, category bug. |
| CC-2-F17 | corrected | ext4 and exFAT now equal the upstream default (4 workers, queue 12; exFAT reverted after C0106 drops, `MediaProfile.hpp:140-142`). The change is only on vfat/NTFS/ntfs-fuse (2 workers, queue 16, +2 raw buffers) and `Other` (2 workers; `known()` is true for `Other`, `MediaProfile.hpp:160`). |
| CC-2-F18 | stands | `CC:4371-4373 @port`; member flag precedent `warnedMissingWhiteBalance_` `CC:6858-6861 @up`. |
| CC-2-F19 | stands | `CC:3963`, `3985`, `4008`; also in `ModeLadder.hpp:26` comment. |
| CC-2-F20 | stands | `CC:2892-2893` vs function at `CC:2928`; `CC:4023-4028` optional round-trip. |

## Final findings

### CC-2-F1 [mismatch, major] Camera side reads `apertar-hardware.conf` (`[camera]` Clear HDR ISO caps)
- where: `src/camera/CameraController.cpp:2933-2984@cinemate-port`; `src/camera/CameraController.cpp:3009-3023@cinemate-port`; `src/ApertarCoreApp.cpp:5074-5079@cinemate-port`
- port: `struct CameraSection` + `loadCameraSection()` parse `[camera] clear_hdr_iso_max_12bit/16bit` from the hardware file with an own INI dialect (strips all whitespace); cached in a function-local static (`cameraSection()`); the template ships the keys.
- apertar way: S22: the camera side never reads `apertar-hardware.conf` (0 hits in `src/camera @upstream-1.6.0`). Sensor/format limits are literals in the sanitiser: `settings.iso = std::min<uint32_t>(settings.iso, 800u);` `CC:2483@upstream-1.6.0` (5.14). Bench overrides are env vars (N11, R5).
- why it matters: driver facts (gain codes 57 / 80 of the port's imx585 driver) become operator config, and a hardware-file parser appears inside `CameraController`. The original developer reads it as a layer violation.
- rework: `constexpr uint32_t kClearHdrMaxIso12 = 720, kClearHdrMaxIso16 = 1585;` next to `kLosslessMaxIso`; `clearHdrIsoCap` returns them. Bench override if wanted: `unsignedEnvValue("APERTAR_CLEAR_HDR_ISO_MAX_12", 720, 0, 51200)` at use. Delete `CameraSection`, `loadCameraSection`, `cameraSection`, the `[camera]` template block in App and its README text.
- effort: S. deliberate: yes (`8175273` describes the `[camera]` keys).

### CC-2-F2 [mismatch, major] `DngRecordingQueue` re-reads `[storage]` from disk at each take
- where: `src/camera/CameraController.cpp:2986-3007@cinemate-port`; `src/camera/CameraController.cpp:4285-4313@cinemate-port`; `src/camera/CameraController.cpp:2945-2950@cinemate-port`; `src/camera/CameraController.cpp:2991-2996@cinemate-port`; `src/ApertarCoreApp.cpp:272-284@cinemate-port`
- port: `loadBufferConf()` opens the hardware file and hands it to `bufferbudget::parseBufferConf` at each take (frames_per_folder here, RAM plan in CC-3). The App already parses the same text from `configStore()` and publishes `framesPerFolderRequest()` (`App:281-283`), which the queue does not use. The candidate list is written inline twice in `CC`.
- apertar way: S22. Per-take options that are not camera settings go from the App into `startRecording` as a struct: `GyroRecordingOptions` (`Types.hpp:199`, `App:10633`, `CameraController.hpp:78 @upstream-1.6.0`; 5.14). Bench knobs are env-only (N11, R5). (Per-file copies of `hardwareConfigCandidatePaths()` are upstream style, 5 copies @upstream-1.6.0; the problem is that the camera side reads the file at all.)
- why it matters: `[storage]` reaches the recorder by two routes that can disagree; the camera side gains file I/O.
- rework: add `StorageRecordingOptions` (framesPerFolder, buffer mode and fractions) to `Types.hpp`. App fills it from `configStore()` at `record_start`; `startRecording` passes it to `DngRecordingQueue::startAtFolder`. Delete `loadBufferConf` and both inline path lists. Because `d7dd337` calls frames_per_folder an A/B campaign knob, consider dropping the `[storage]` key and `set_frames_per_folder` and keeping `APERTAR_CDNG_FRAMES_PER_FOLDER` only.
- effort: M. deliberate: yes (`d7dd337`, `d44b177`: "read at each take so a Config save applies").

### CC-2-F3 [removed-upstream-behaviour, major] Upstream lossless cDNG limits changed (ISO 800->1600, auto ISO kept on IMX585, IMX585 fps 30 -> mode max)
- where: `src/camera/CameraController.cpp:3098-3158@cinemate-port`
- port: `kLosslessMaxIso = 1600` ("on Patrik's request"); `isoAuto` forced off only for non-IMX585 ("Other sensors are unchecked"); IMX585 fps = mode maximum unless `APERTAR_LOSSLESS_FPS_LIMIT`.
- apertar way: `enforceLosslessCaptureLimits` `CC:2470-2491@upstream-1.6.0`: `std::min<uint32_t>(settings.iso, 800u)`; `settings.isoAuto = false`; IMX585 `maximumFps` 30.0.
- why it matters: three product-policy defaults of the original developer change silently inside a refactor; the auto-ISO part is recorded as unverified (`fork-log.md:85`).
- rework: keep 800 / manual ISO / 30 as defaults in `enforceLosslessCaptureLimits`. Expose the relaxed values as R5 bench knobs (`unsignedEnvValue` at use), or move the change into its own commit with the measurements for the original developer to accept.
- effort: S. deliberate: yes (`2f43ecc`, `b5b787e`, `d44b177`).

### CC-2-F5 [new-ground, minor] Sync thread fsyncs clip frames once a second by default
- where: `src/camera/CameraController.cpp:4353-4369@cinemate-port`
- port: `APERTAR_MEDIA_SYNC_MS` default 1000 (or the media tune file); `syncLoop` fsyncs the DNGs written in the last tick and the clip folder, run via `spawnWorker`; `sync_ms=` on the clip line.
- apertar way: N10: clip frames are not synced, for throughput. `AtomicStillFile.hpp:31-32@upstream-1.6.0`: "Keep this out of the continuous recording path: syncing each video frame would destroy throughput."
- why it matters: reverses an intent upstream wrote in a comment; the original developer will ask about throughput on slower media.
- rework: keep (carefully considered, measured: C0007 3 min clean, C0011 258/281 frames readable after a pull, syncfs variant rejected after 782 drops; `fork-log.md:51-53`). Document it for the original developer as a deliberate departure from N10 with those numbers. Its default moves to env-only with F6.
- effort: S. deliberate: yes (`4ce382e`, `5b68f1f`, `7d9dd60`).

### CC-2-F6 [mismatch, major] Media tuning file feeds per-take recorder knobs
- where: `src/camera/CameraController.cpp:4316-4327@cinemate-port`; `src/camera/CameraController.cpp:4364-4365@cinemate-port`; `src/util/MediaTune.hpp:27-28@cinemate-port`
- port: `mediaTuneForConfiguredRoot()` reads `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf` for `sync_ms`; `mediaProfile_.writer` (workers, queueFrames) takes file values and changes writer defaults.
- apertar way: N11: internal tuning stays out of files; knobs are undocumented env vars. 5.12 lists "a config file or config section for recorder tuning" as deliberately absent. Precedent `APERTAR_CDNG_QUEUE_FRAMES` `CC:3329-3330@upstream-1.6.0`.
- why it matters: a second tuning channel (file, override, tmpfiles, root helper) beside the env knobs upstream uses only.
- rework: delete `MediaTune.hpp`, the override path and the tmpfiles/helper wiring. Keep `APERTAR_MEDIA_SYNC_MS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES` as the only overrides.
- effort: M. deliberate: yes (`26da30e`, `2edc6d0`, `ebdcd08`).

### CC-2-F7 [mismatch, major] Process-wide flush-abort callback registered by the queue
- where: `src/camera/CameraController.cpp:4211@cinemate-port`; `src/camera/CameraController.cpp:4271@cinemate-port`; `src/camera/CameraController.cpp:4594@cinemate-port`; `src/util/BufferBudget.hpp:231-252@cinemate-port`; `src/ApertarCoreApp.cpp:286-299@cinemate-port`
- port: `startAtFolder` registers a global `std::function` in `BufferBudget.hpp`, the destructor unregisters it; `handleCommand` calls `abortSafetyStopFlush()` on `record_start` before any lock, bypassing `CameraController`. `safetyStopState()` is a further process-wide singleton written by the queue and read by the App.
- apertar way: the App reaches the queue only through `CameraController` methods. Cross-thread signals are controller-owned objects passed to the queue by pointer: `RecordingDropWarning` (`CameraController.hpp:113`, queue ctor `CC:3251 @upstream-1.6.0`).
- why it matters: a hidden global path from the command plane into a recorder; a maintainer will not find it by reading `CameraController`.
- rework: `CameraController::abortFlush()` that takes no controller mutex (the drain holds it) and sets an atomic in a controller-owned object the queue holds by pointer (like `dropWarning_`); the queue's drain loop checks it. `handleCommand` calls that method. Delete the registry; move `safetyStopState` into the same controller-owned object.
- effort: M. deliberate: yes (`c5db8b2`).

### CC-2-F8 [mismatch, minor] `FrameBufferGauge` is a hidden function-local singleton
- where: `src/camera/CameraController.cpp:4169-4186@cinemate-port`; `src/camera/CameraController.cpp:4269@cinemate-port`
- port: five atomics behind a `frameBufferGauge()` static, written by the queue, read by `frameBufferStatus()` without the controller mutex.
- apertar way: I17 uses function-local statics only for process-lifetime one-offs (`captureSettingsPersister` `CC:885-889`, `cachedPiSerial` `CC:2990-2994 @upstream-1.6.0`). Per-take shared state is controller-owned and passed by pointer (`RecordingDropWarning`). Queue depth in the API is absent upstream (5.12, N3).
- why it matters: the feature is new ground with a sound reason (mutex held during drain), but its shape hides the dependency.
- rework: make `FrameBufferGauge` a member of `CameraController`, pass it to `DngRecordingQueue(RecordingDropWarning*, FrameBufferGauge*)`; `frameBufferStatus` reads the member lock-free.
- effort: S. deliberate: yes (comment `CC:4170-4172`).

### CC-2-F9 [bug, major] `stop()` joins copy workers without a bound; copy workers `mkdir` part folders on the medium
- where: `src/camera/CameraController.cpp:4453@cinemate-port`; `src/camera/CameraController.cpp:5164-5174@cinemate-port`; `src/camera/CameraController.cpp:4959-4974@cinemate-port`; `src/camera/CameraController.cpp:4386-4388@cinemate-port`
- port: `stop()` calls `stopCopyWorkers()` (plain `join`) before the bounded writer wait. Copy threads start with `copyThreads_.emplace_back`, not `spawnWorker`. `enqueue()` on the copy thread calls `ensurePartFolder()` -> `::mkdir` on the medium under `partMutex_`.
- apertar way: no precedent (upstream copies on the completion thread and joins writers unconditionally, `CC:3405-3408@upstream-1.6.0`).
- why it matters: failing input: `frames_per_folder=1000`, card pulled while a copy worker crosses a part boundary; `mkdir` blocks until the NVMe timeout and `stop(true)` hangs in `join` with the controller and command locks held, the hang `0b1632f` set out to remove. Probable (depends on the kernel blocking `mkdir`); off by default (`frames_per_folder=0`).
- rework: create part folders on a writer thread (covered by the bounded stop), or start copy threads through `spawnWorker` and stop them inside the bounded wait.
- effort: S. deliberate: no (copy-side placement is deliberate per `d7dd337`, the unbounded join is not).

### CC-2-F10 [slop, minor] fps ceiling over-built: dead `backendMaximumFps`, `FpsCeiling.hpp` wrappers, experiment env switches
- where: `src/camera/CameraController.cpp:3389-3434@cinemate-port`; `src/camera/CameraController.cpp:3464-3491@cinemate-port`; `src/camera/CameraController.cpp:8634-8639@cinemate-port`; `src/camera/FpsCeiling.hpp:10-47@cinemate-port`
- port: `backendMaximumFps` returns `nullopt` for every input (4 call sites); `applyBackendCap`, `resolveSensorMaxFps`, `losslessImx585Fps` are one-line `std::min` wrappers in their own header with a host test. `APERTAR_FPS_LIMIT=table` and `APERTAR_IMX283_PROBE_FPS` reproduce earlier behaviour.
- apertar way: inline arithmetic: `probed ? std::min(table, *probed) : table` (`CC:2769@main`); `settings.fps = std::min(settings.fps, maximumFps)` `CC:2490@upstream-1.6.0`. S4 headers hold real pure logic.
- why it matters: dead hooks and experiment toggles; a reader traces four layers to find one `min()`.
- rework: delete `backendMaximumFps`, `applyBackendCap`, `fpsLimitTableOnly`, `imx283ProbeFpsOnly`, `FpsCeiling.hpp`, `tools/fps_ceiling_test.cpp`. Write the probe-vs-table choice inline in `maximumSupportedFpsForResolution` (IMX283 keeps min with the floor table).
- effort: S. deliberate: unknown (the 25 fps cap was removed by `31d5418`, the hook left).

### CC-2-F11 [mismatch, nit] New env knobs in `CC` parsed by hand, read once, logged
- where: `src/camera/CameraController.cpp:3115-3130@cinemate-port`; `src/camera/CameraController.cpp:3397-3408@cinemate-port`; `src/camera/CameraController.cpp:4293-4297@cinemate-port`
- port: `losslessFpsOverride` (`strtod` parser, read-once static, stderr), `fpsLimitTableOnly` (string compare, read-once, stderr), `APERTAR_CDNG_FRAMES_PER_FOLDER` (own parser, stderr on a bad value).
- apertar way: in `CC`, I9/R5: `unsignedEnvValue(name, default, min, max)` / `boolEnvValue` at use (`CC:1027-1061`, use `CC:3329-3330 @upstream-1.6.0`); a malformed value falls back silently; effective value on the take-start line. (A read-once hand-parsed knob exists upstream in `CdngEncoder.cpp:52-66`, so this is a style gap inside `CC`, not a missing rule.)
- why it matters: each port knob has its own parse and log style inside one file.
- rework: use `unsignedEnvValue`/`boolEnvValue` at use; drop the extra log lines; print effective values on the `recording clip:` line. Mostly disappears with F10.
- effort: S. deliberate: no.

### CC-2-F12 [slop, minor] Ticket numbers, names, dates, take ids and KB paths in comments
- where: `src/camera/CameraController.cpp:3025@cinemate-port`; `:3034`; `:3070`; `:3098-3099`; `:3154`; `:3428-3430`; `:4318`; `:4357`
- port: "Patrik's rule (2026-10-28 ...)", "T34", "temp 753f181 ... C0013", "(Patrik, 2026-10-28)", "(User, 2026-11-03)" plus KB paths, "T29 measures", "C0005, 2026-10-26".
- apertar way: I19: comments are rare and say why in 1-3 lines; no ticket numbers, author or date (`CC:6927-6928@upstream-1.6.0`).
- why it matters: the references mean nothing to the original developer; the comments read as a history log.
- rework: rewrite each as the constraint only, or delete.
- effort: S. deliberate: no.

### CC-2-F13 [slop, minor] Stale comments contradict the code
- where: `src/camera/CameraController.cpp:3378@cinemate-port`; `:3481-3485`; `:4317-4319`
- port: "the 16-bit 25 is backendMaximumFps()" (no such cap); "only the named back-end cap kept" (none exists); "exFAT/NTFS get 2" (`MediaProfile.hpp:142` gives exFAT 4).
- apertar way: I19: comments state a current constraint.
- why it matters: they mislead the next reader.
- rework: fix with F10 and F17.
- effort: S. deliberate: no.

### CC-2-F14 [mismatch, minor] Ladder refusal texts as `constexpr` constants with a wrong menu path
- where: `src/camera/CameraController.cpp:3061-3067@cinemate-port`
- port: `kLadderOwnsMode` / `kLadderOwnsCompression` (7 uses) tell the operator "Settings > Record > Mode Ladder"; the WebUI card is under Settings > Modes (`WCP:4750-4753`, `data-panel="modes"` `WCP:5151`, title `WCP:5166 @cinemate-port`; confirmed).
- apertar way: I1/I5: one inline sentence per `setErrorLocked(...)`, e.g. "Resolution changes are blocked while recording." `CC:7715@upstream-1.6.0`; no message constants, no menu paths.
- why it matters: foreign style, and the text sends the operator to the wrong place.
- rework: inline one sentence at each setter without a path, e.g. "Turn off the Mode Ladder to choose the resolution by hand."
- effort: S. deliberate: no.

### CC-2-F15 [mismatch, minor] Ladder compression handled as strings, not enums
- where: `src/camera/CameraController.cpp:3034-3049@cinemate-port`; `src/camera/ModeLadder.hpp:17-44@cinemate-port`
- port: `applyRungFormat` compares `ladder::effectiveCompression(rung)` to "lossy_3to1", "lossy_5to1", "none". `Rung::compression` is a string, while `Rung::cdngLog` is already an enum.
- apertar way: format sub-options are enums in `Types.hpp` with `toString`/`fromString` at the edge (R3 step 1: `CdngCompression`, `LossyDngRatio`).
- why it matters: stringly-typed internals in `CC`; file input is validated (`knownCompression`, `ModeLadder.hpp:29`), but a typo in a code literal compiles and falls through to lossless.
- rework: `ladder::Rung` stores `RecordingFormat` + `CdngCompression` + `LossyDngRatio`; parse strings once where the ladder is loaded or set.
- effort: M. deliberate: no.

### CC-2-F16 [bug, nit] `wavSampleRate` rejects RF64
- where: `src/camera/CameraController.cpp:2894-2917@cinemate-port`
- port: accepts a `RIFF` header only.
- apertar way: upstream's WAV reader accepts `RIFF` and `RF64` (`App:5806@upstream-1.6.0`); Core writes RF64 above 4 GiB (`AudioRecordingSession.cpp:773`).
- why it matters: failing input: a speed-ramp take whose WAV passes 4 GiB gives sample rate 0, so no stretched WAV is made (one log line).
- rework: accept `RF64` as well.
- effort: S. deliberate: no.

### CC-2-F17 [removed-upstream-behaviour, minor] Uncompressed cDNG writer count and queue depth follow the filesystem on vfat/NTFS/other
- where: `src/camera/CameraController.cpp:4316-4327@cinemate-port`; `src/util/MediaProfile.hpp:136-150@cinemate-port`
- port: `normalWorkerCount` = env, else `min(profile workers, format count)`; uncompressed queue = profile `queueFrames` when the medium is known. ext4 and exFAT give 4/12 (same as upstream); vfat, NTFS, ntfs-fuse give 2 workers / queue 16 / +2 raw buffers; `Other` gives 2 workers.
- apertar way: `CC:3323-3330@upstream-1.6.0`: `max(2, min(4, threads))` workers, queue 12, env overrides only.
- why it matters: an upstream default changes on numbers the commit calls "Cinemate's numbers, not measured here" (`26da30e`); exFAT already had to be reverted after drops (C0106).
- rework: keep the upstream defaults and the env knobs; delete the per-filesystem table (or keep it only with Apertar measurements per filesystem).
- effort: S. deliberate: yes (`26da30e`).

### CC-2-F18 [mismatch, nit] `static bool warned` inside a member function
- where: `src/camera/CameraController.cpp:4371-4373@cinemate-port`
- port: function-local static inside `DngRecordingQueue::startAtFolder`.
- apertar way: I8: one-off warnings use a `bool warned..._` member (`warnedMissingWhiteBalance_` `CC:6858-6861@upstream-1.6.0`).
- why it matters: small style break.
- rework: member flag, or drop the warning.
- effort: S. deliberate: no.

### CC-2-F19 [slop, nit] "CineMate Log" product name in Core log text
- where: `src/camera/CameraController.cpp:3963@cinemate-port`; `:3985`; `:4008`
- port: "ApertarCore CineMate Log: ...".
- apertar way: log lines name Apertar concepts only ("ApertarCore recording clip:" `CC:3353@upstream-1.6.0`).
- why it matters: a foreign product name in the operator journal.
- rework: rename to "cDNG Log" or "Log".
- effort: S. deliberate: no.

### CC-2-F20 [slop, nit] Detached `isoForMeasuredGain` comment; optional round-trip in `buildCdngLogTake`
- where: `src/camera/CameraController.cpp:2892-2893@cinemate-port`; `src/camera/CameraController.cpp:4023-4028@cinemate-port`
- port: the comment sits above `#if`/`wavSampleRate`, the function is at `CC:2928`; the plan is copied into locals and `plan->params` is wrapped in `std::optional` only to be dereferenced.
- apertar way: no precedent.
- why it matters: leftovers from edits.
- rework: move the comment; use `plan->` directly.
- effort: S. deliberate: no.
