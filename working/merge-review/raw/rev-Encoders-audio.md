# Review: Encoders-audio (stage 2)

| Item | Value |
| --- | --- |
| Scope | `src/cdng/CdngEncoder.{cpp,hpp}`, `src/cdng/BlackLevel.hpp`, `src/cdng/LogCurve.hpp` (new), `src/lossydng/*`, `src/mlv/*`, `src/audio/*`, `src/util/RecordingDropWarning.hpp`, `src/util/ClipName.hpp` (new), `tools/{log_curve,clip_name,black_level,dng_payload_write}_test.*`, `tools/gen_log_curve.py` |
| Refs | port `cinemate-port` 01f170c (`@port`); upstream `upstream-1.6.0` 35dbe67 (`@up`) in `/home/user/wt/core-upstream` |
| Yardstick | no `apertar-conventions.md`; rules cited from `conv-core-camera.md` (S/I/N ids, prefixed CAM-), `conv-platform-build.md` (PB-), `conv-style-commits.md` (C8-) |
| Host tests run here | `clip_name_test`, `black_level_test`, `log_curve_test`: all pass. `dng_payload_write_test.sh`: PASS, 6 layouts byte-identical; direct path 45 write + 4 writev vs 120 write on copy path |
| Diff | 12 source files +532/-82, plus 2 new headers and 6 tool files |

## Verdict in one paragraph

The encoder side mostly follows upstream shape: env knobs read in function-local statics with strict parse and clamp
(PB-I1, CAM-I9, CAM-I17), the audio writer is a `std::thread` member with mutex, cv, deque and stop flag (CAM-I16),
the recorder API keeps `stop()` / `error()` (CAM-S16), and the level helpers move into the `BlackLevel.hpp` that
upstream already shares between encoders. Three things do not read as Apertar: the cDNG encoder reads a tuning file
(`apertar-media-tune.conf`) to pick its page-cache policy; the upstream default "drop pages after each DNG write" is
changed for cDNG and silently removed for Lossy DNG; and the comments narrate history, dates, clip ids, tutorial
numbers and Cinemate commit hashes. The Log curve and the clip-name template are new ground in an acceptable shape
(header-only pure logic, CAM-S4) with some trimming.

## Findings

### Encoders-audio-F1 | mismatch | major | DONTNEED policy read from a tuning file inside the encoder

- Port: `src/cdng/CdngEncoder.cpp:84-108@port` `dngPageCacheDrop()`: env `APERTAR_DNG_DONTNEED`, else
  `mediaTuneForConfiguredRoot()` (`util/MediaProfile.hpp:230@port`, reads `/home/pi/apertar-media-tune.conf` and
  `/run/apertar-media/media-tune.override.conf`), else `Sync`. `#include "util/MediaProfile.hpp"` at
  `CdngEncoder.cpp:7@port`. The encoder now prints `ApertarCore media tune: file=absent ...` on first use (seen when
  running `dng_payload_write_test.sh`). Lossy DNG reaches it through `#include "cdng/CdngEncoder.hpp"   // dngPageCacheDrop`
  (`LossyDngEncoder.cpp:3@port`).
- Upstream: encoder knobs are env only, read in a function-local static next to their use:
  `CdngEncoder.cpp:51-66@up` `configuredLosslessTileRows()` (`APERTAR_CDNG_TILE_ROWS`), `:68-77@up`
  `detailedLosslessProfilingEnabled()`; `LossyDngEncoder.cpp:96-108@up` `configuredWriterByteCap()`. No encoder reads a
  file. Rules CAM-I9 ("A tuning config file or socket command for an internal knob" = violation), CAM-N11, PB-I1.
- Why: the original developer would find a second config layer reached from a file-format class. The tune file is
  already judged "rework-to-upstream-pattern" in rev-CC-1/2/3 (MediaTune slice); the encoder is one of its readers.
- Rework: `dngPageCacheDrop()` env only, same body as `configuredLosslessTileRows` (strcmp ladder, unknown -> default,
  one stderr line allowed). Delete the `mediaTuneForConfiguredRoot()` branch and the `MediaProfile.hpp` and
  `<iostream>` includes from `CdngEncoder.cpp` if nothing else needs them. Drop the redundant include in
  `LossyDngEncoder.cpp:3` (its header already includes `cdng/CdngEncoder.hpp`, `LossyDngEncoder.hpp:3@port`).
- Effort S. Deliberate: yes (commit 2edc6d0 "tune file"; drop-frames README:184 `/run` drop-in).

### Encoders-audio-F2 | removed-upstream-behaviour | major | Writer-side DONTNEED default changed; Lossy DNG loses it

- Port: `CdngEncoder.cpp:1897-1898@port` and `LossyDngEncoder.cpp:104-105@port` call
  `posix_fadvise(DONTNEED)` only when the mode is `Writer`. Default is `Sync` (`CdngEncoder.cpp:96@port`). `Sync`
  drops the pages on the port's own per-second sync thread after `fsync` (`CameraController.cpp:4757-4765@port`),
  which only runs while `APERTAR_MEDIA_SYNC_MS > 0` (`CC:4365-4377@port`, default 1000). The Lossy write path does not
  call `noteWrittenFile` (`CC:5279-5290@port`), so Lossy pages are never dropped by default; the comment at
  `LossyDngEncoder.cpp:101-103@port` says so.
- Upstream: unconditional `::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);` after every cDNG
  (`CdngEncoder.cpp:1777@up`) and every Lossy DNG (`LossyDngEncoder.cpp:82@up`). Upstream does not sync clip frames
  during a take (CAM-N10, `CC:4005-4006@up`).
- Why: the measured gain is real for cDNG Clear HDR 16-bit (drop-frames README:163-189: 25 lost of 14998 with `sync`),
  but (a) the default now depends on a port-only sync thread that the CC review proposes to cut back to upstream N10,
  and the kb itself recommends `APERTAR_MEDIA_SYNC_MS` default 0 (drop-frames README:301); with no sync thread `Sync`
  means "never drop" with only a one-time log; (b) Lossy DNG changed default without a measurement.
- Rework: keep the enum, make the fallback explicit: `Sync` without a running sync thread acts as `Writer` (decide at
  take start in `DngRecordingQueue::start` and pass a bool to the writer, not a global). For Lossy, `Sync` acts as
  `Writer` (its write runs on the background `LossyDngDiskWriter`, the drain cost does not hit the camera path). If the
  owner keeps `Sync` as default for cDNG, state it in the handoff with the measurement.
- Effort S-M. Deliberate: yes (0ed07ea, adac040, 766aba8; drop-frames README).

### Encoders-audio-F3 | slop | minor | Comments narrate history, dates, clip ids, tutorial numbers, other projects

- Port lines: `CdngEncoder.hpp:13-16@port` ("as before 2026-11-01", "See the kb, working/dng-chain");
  `CdngEncoder.hpp:44@port` and `AudioRecordingSession.cpp:382@port` ("T31"); `CdngEncoder.cpp:132@port` ("the old
  path", "the A/B knob"); `CdngEncoder.cpp:1987@port` ("cinepi-raw's one write per frame");
  `AudioRecordingSession.cpp:207-211@port` ("+1339 to -201 ppm ... (2026-10-26) ... the old ring is the default again");
  `:588-590@port` ("2026-10-26/27"); `:750-753@port` ("C0011, 2026-10-26"); `AudioRecordingSession.hpp:73-76@port`
  ("Cinemate ffb61fd"); `TimestampedAudioCapture.cpp:195-199@port` ("Cinemate 5021ba3"); `ClipName.hpp:10@port`
  ("also in apertar-kb"); `LogCurve.hpp:18,63@port` (cinepi-raw).
- Upstream: one-to-three-line present-tense why-notes; no ticket numbers, dates, other project hashes (C8-S8, C8-S9,
  CAM-I19, C8 section 13). Codec islands keep long rationale but as facts (`LossyDngEncoder.cpp:322-324@up`).
- Rework: rewrite each as an invariant. Examples: audio ring "The ring absorbs storage stalls; the period sets meter and
  timestamp granularity."; drift fit "Slope of the per-block fit: an end stamp can be a period off."; raw fsync
  "Synced once a second so a pulled card keeps the PCM written so far." Move measurements and hashes to the kb or the
  commit message.
- Effort S. Deliberate: no (style).

### Encoders-audio-F4 | slop | minor | "CineMate Log" product name inside Core

- Port: `LogCurve.hpp:13,48@port` (`describe()` returns `"CineMate Log ..."`, logged at `CC:4041@port`),
  `LossyDngEncoder.cpp:51@port`, `LossyDngEncoder.hpp:24@port`; outside the unit the same name in `CC`, `ModeLadder.hpp`,
  `WCP:9783`.
- Upstream: code never names another project; credits live in `README.md:308-311@up` (C8 section 13).
- Rework: call it "Log" in code and log lines (`apertar::cdnglog` stays); one README credit line for the curve's origin.
  Drop "Same curve as cinepi-raw ... share one look" or keep it as one neutral sentence ("matches cinepi-raw log_lut.hpp
  16->12 and 12->10") if the owner wants the compatibility claim (unverified here).
- Effort S. Deliberate: unknown.

### Encoders-audio-F5 | mismatch | minor | Audio writer queue is unbounded and allocates per block

- Port: `AudioRecordingSession.cpp:734-745@port` `enqueueWrite`: `std::vector<char> block(size)` per 1024-frame block,
  pushed to `writeQueue_` without limit; only a one-time log at 16 MB (`:768-771@port`). Pads allocate the whole gap.
- Upstream: the one background writer in the encoders is bounded and recycles buffers: `LossyDngEncoder.cpp:96-108@up`
  `configuredWriterByteCap()` (`APERTAR_LOSSYDNG_WRITER_BYTES`, default 512 MB) and `give()` back to a pool. CAM-N2
  "queues are bounded".
- Why: audio rate is low (about 0.3 MB/s at 48 kHz 24-bit stereo), so a stall would need minutes to hurt; still a
  foreign shape next to the bounded Lossy writer.
- Rework: cap `queuedWriteBytes_` (`APERTAR_AUDIO_WRITER_BYTES`, default e.g. 64 MB, read like
  `configuredWriterByteCap`); on overflow set `failure_` "Audio capture write stalled." and stop queueing. Optional:
  reuse a small free list of 1024-frame blocks.
- Effort S. Deliberate: yes for the thread (cinemate-lessons section 3 deliverable 2), no for the missing cap.

### Encoders-audio-F6 | new-ground | minor | Clip name template: right idea, over-built token set, placed in util

- Port: `src/util/ClipName.hpp@port` (296 lines): 19 tokens + `{text:..}`. `{cam}` is always `cam0`
  (`CC:1160@port` "one camera per Apertar"); `{model}` is always derived from the constant `Metadata{}.model`
  (`CC:1162-1165@port`); `{date_}` equals `{yy}_{mm}_{dd}`. Default template `{format}_{date}_{clip}` reproduces upstream
  names byte for byte (`clip_name_test` passes). One allocator is kept (`reserveClipFolder` -> `nextClipFolderName`,
  `CC:7642@port`, `CC:1192-1200@port`), consistent with CAM-S17.
- Upstream: names built inline in the one allocator: `CC:3646-3673@up` (`formatPrefix` switch, `put_time("%y-%m-%d")`,
  `_C%04d` loop). Pure logic lives in header-only files named after the concept under the area that uses it
  (`src/camera/StillBracketing.hpp`, `ScalerCropGeometry.hpp`, CAM-S4); `src/util/` holds latches and the settings writer
  only (CAM-S6).
- Verdict: keep the feature and the header-only shape (nested namespace allowed, CAM-I22). Simplify: drop `{cam}`,
  `{model}`, `{date_}`; move the file to `src/camera/ClipName.hpp`; drop "also in apertar-kb".
- Effort S. Deliberate: yes (014a2bf, fork-log:138).

### Encoders-audio-F7 | new-ground | minor | `LossyDngEncoder::setCdngLog` takes raw pointers with a lifetime contract

- Port: `LossyDngEncoder.hpp:24-30@port` stores `const cdnglog::Params *`, `const cdnglog::Tables *`; caller
  `CC:5250@port` passes `&cdngLog_->params, &cdngLog_->tables` from a `std::shared_ptr<const CdngLogTake>`;
  `cachedLog_` compares pointer identity (`LossyDngEncoder.cpp:905@port`).
- Upstream: encoder options are values: `setRatio(LossyDngRatio)` (`LossyDngEncoder.hpp@up`), `invalidateTables()`.
- Rework: `void setLog(std::optional<cdnglog::Params> params)`; the encoder builds and caches its own tables
  (`cdnglog::buildTables`, under 70 k entries) and compares params by value. Or hold the `shared_ptr<const CdngLogTake>`.
- Effort S. Deliberate: unknown.

### Encoders-audio-F8 | new-ground | minor | Drift fit still resamples anywhere in 20..2000 ppm

- Port: `AudioRecordingSession.cpp:486-498@port` accumulates a least-squares fit per block, padded gaps added to
  `fitFrames_`; `finalizeWav` `:588-605@port` applies the slope when >= 100 points and 20..2000 ppm, logs the endpoint
  figure.
- Upstream: endpoint ratio `availableFrames * 1e6 / capturedDurationUs` with the same window (`finalizeWav@up`).
- KB: cinemate-lessons section 3, deliverable 3: a whole-take estimate "cannot tell clock drift from sample loss";
  recommends a per-device ppm with a tight clamp.
- Verdict: keep (same place, same window, less noise than two endpoints; tested: fork-log:55, -15 ppm on 6968 points).
  Silent under-delivery still bends the slope. Either narrow the window (e.g. 20..300 ppm) or say in the handoff that it
  is the upstream method with a better estimator.
- Effort S. Deliberate: yes (ebdcd08).

### Encoders-audio-F9 | bug | minor | After a writer failure the WAV counts bytes that were never written (probable)

- Port: `readerLoop` adds `capturedBytes_ += bytesRead` after `enqueueWrite` (`AudioRecordingSession.cpp:534-536@port`);
  the writer drops blocks once `writeFailed_` is set (`:772-779@port`). `stop()` with `finalize=true` (any failure other
  than "medium gone") runs `finalizeWav` with `availableFrames = capturedBytes_ / blockAlign` (`:585@port`); short reads
  of the raw file decode as 0 (`:688-692@port`).
- Upstream: `capturedBytes_` grows only after a successful `rawStream_.write` (reader writes inline).
- Failing input: ENOSPC on the raw file with 2 s of backlog queued -> WAV 2 s longer than the PCM, tail silence, take
  stops anyway via `failure_`.
- Rework: count `writtenBytes_` in the writer and use it in `finalizeWav`, or skip finalisation when `writeFailed_`.
- Effort S. Deliberate: no.

### Encoders-audio-F10 | new-ground | nit | ALSA hw params by hand; env ring knob left after the 1 s experiment

- Port: `TimestampedAudioCapture.cpp:192-219@port` replaces `snd_pcm_set_params(..., 100000)` (`:189-190@up`) with
  explicit hw params; ring `bufferUs`, period `periodUs` default 100 ms / 10 ms (`.hpp:27-28@port`).
  `APERTAR_AUDIO_BUFFER_MS` 100..4000, default 100 (`AudioRecordingSession.cpp:212-219@port`). The 1 s default was
  tried and reverted (comment and commit 0358fcf).
- Effect: period 25 ms -> 10 ms on every `open()` caller, also the idle meter path, through the default args.
- Verdict: keep (independent ring/period is a sound reason; ALSA stays dlopened, CAM-S18; knob shape follows PB-I1).
  Trim the comments (F3). Mention the period change in the handoff.
- Effort S. Deliberate: yes.

### Encoders-audio-F11 | new-ground | nit | Dropped-frame running total in `RecordingDropWarning`

- Port: `RecordingDropWarning.hpp:11-27@port` adds `droppedFrames()`, `markDropped(n)`, `setMuted`. The latch and the
  one-shot `changed_(true)` stay; the count is read into state (`CC:12889@port`).
- Upstream: `RecordingDropWarning.hpp:9@up` "notify once, not once per frame"; README:299 "reported rather than
  hidden". conv CAM-N3 lists "a per-frame drop counter in the UI" as a violation.
- Verdict: keep. Notification is still once per clip; the count is a polled scalar, not a per-frame event. Tell the
  developer this is a deliberate departure from the "!" only display (64bbbaa).
- Effort none. Deliberate: yes.

### Encoders-audio-F12 | removed-upstream-behaviour | nit | MLV declares different levels than 1.6.0 at 12/16-bit

- Port: `MlvEncoder.cpp:1152-1157@port` uses `encodedBlackLevel` / `encodedWhiteLevel` with
  `blackLevelsOnContainerScale`.
- Upstream: `MlvEncoder.cpp:159-175@up` scales black only for 8 and 10 bit, so a 16-bit MLV declares black 200 while
  the cDNG of the same take declares about 3200 (`blackLevelForSampleBits`, `BlackLevel.hpp:12-19@up`).
- Verdict: keep; it is a fix of an upstream inconsistency using upstream's own shared header. State it in the handoff
  (MLV files from 1.6.0 and from the port differ at 12/16-bit). Host test `black_level_test` passes.
- Effort none. Deliberate: yes (5e9dd1a).

### Encoders-audio-F13 | slop | nit | Knob names, include order

- `APERTAR_DNG_WRITE_ROWS`, `APERTAR_DNG_PAYLOAD_COPY` (`CdngEncoder.cpp:118,137@port`) sit next to upstream
  `APERTAR_CDNG_TILE_ROWS`, `APERTAR_CDNG_PROFILE_DETAIL` (`CdngEncoder.cpp:55,72@up`): area should be `CDNG` (C8-S3).
  `APERTAR_DNG_DONTNEED` is shared with Lossy, `DNG` is defensible there.
- `MlvEncoder.cpp:1@port` includes `util/MediaFault.hpp` before its own header (CAM-I21: own header first,
  `MlvEncoder.cpp:1-18@up`).
- Effort S. Deliberate: no.

### Encoders-audio-F14 | new-ground | nit | `tools/` host tests and a Python golden generator

- Port: four `*_test.cpp`, one `.sh`, `gen_log_curve.py` (prints golden values to paste into `log_curve_test.cpp`).
  Not in CMake. `log_curve_test.cpp:3-6@port` also tests `ClearHdrCcmp.hpp`, `ModeLadder.hpp`, `Types.hpp`.
- Upstream: no tests, no `tools/` (CAM-S24, PB-S13).
- Verdict: keep, decided once for the whole port (rev-CC-2, rev-CC-3, rev-App-4 say keep). Simplify: drop
  `gen_log_curve.py` (a second implementation of `LogCurve.hpp` in another language) or keep it only in the kb; the
  golden values in the test are enough. `dng_payload_write_test.sh` uses `#!/bin/sh` and `[ ]` (C8-S15 asks bash,
  `[[ ]]`) - nit.
- Effort S. Deliberate: yes.

## Abstraction verdicts (inventory section 4)

| Name | Verdict | Reason |
| --- | --- | --- |
| `apertar::cdnglog` (`LogCurve.hpp`) | keep | Header-only pure logic, std only, one nested namespace (CAM-S4, CAM-I22). Log is a recording encoding with the inverse in LinearizationTable, not a monitoring look baked into RAW (CAM-N13 holds). Rename "CineMate Log" (F4); lossy hookup by value (F7) |
| `apertar::clipname` (`ClipName.hpp`) | simplify | Feature and shape fine, single allocator kept (CAM-S17); trim constant/redundant tokens, move to `src/camera/` (F6) |
| `DngPageCacheDrop` + `dngPageCacheDrop()` | rework-to-upstream-pattern | Env-only function-local static like `configuredLosslessTileRows`; no tune file (F1); explicit fallback when no sync thread, Lossy keeps writer drop (F2) |
| `writeRowsDirect`, `writevAll`, `rowCopyIsIdentity` | keep | Anonymous-namespace helpers in the encoder, A/B env knob like upstream `APERTAR_LOSSYDNG_ASYNCWRITE` (`LossyDngEncoder.cpp:322-328@up`); byte-identical output verified here. Rename knobs to `APERTAR_CDNG_*` (F13) |
| Shared level helpers in `BlackLevel.hpp` | keep | Upstream already shares `blackLevelForSampleBits` in this header; the port removes two private copies and fixes MLV (F12) |
| Audio writer thread + `writeQueue_` | keep, simplify | CAM-I16 shape; add a byte cap (F5); count written bytes (F9) |
| Drift fit accumulators | keep | Better estimator in the same place and window; document the limit (F8) |
| Host test tools | keep | Off the build; one decision for the whole port; drop the Python generator (F14) |

## Conforms (say so in the handoff)

- Env knobs `APERTAR_DNG_WRITE_ROWS`, `APERTAR_DNG_PAYLOAD_COPY`, `APERTAR_AUDIO_BUFFER_MS` are read in function-local
  statics with strict parse, range clamp and silent fallback (`CdngEncoder.cpp:115-142@port`; PB-I1, CAM-I9, CAM-I17),
  and are not in the README.
- Audio writer thread: `std::thread` member, one mutex, cv, `std::deque`, stop flag, peak counter printed at stop
  (`AudioRecordingSession.hpp:73-85@port`; CAM-I16, CAM-I7).
- Recorder surface kept: `stop(bool finalize = true)` and `open(..., bufferUs = 100000, periodUs = 10000)` are call
  compatible; `error()` unchanged (CAM-S16).
- Encoder errors stay exceptions caught at the worker (`MlvEncoder::writeFrame` catch stores `lastErrno_`;
  CAM-I4); Lossy writer failures surface on the next frame as a `system_error` so a dead medium stops a Lossy take
  (`CC:5284-5289@port`; CAM-N4).
- Log lines keep the `ApertarCore <area>: key=value` form (`audio writer: peak_backlog_kb=`, `audio clock: ...
  points= endpoint_ppm=`; CAM-I6).
- `timecodeWallClockUs` is one more scalar in `CdngEncoder::Metadata`, default 0 = old behaviour.
- ALSA stays dlopened; five more symbols added to the existing X-macro list (CAM-S18).
- Speed-ramp audio end and out-of-order frames handled inside `observeVideoFrame` under the existing `syncMutex_`.
- No socket, HTTP, event or config change in this unit's files (protocol: none).
- No Pi-model assumption in these files (writev, IOV_MAX, posix_fadvise, fsync are plain Linux).

## Open points not settled here

| Point | Command |
| --- | --- |
| Lossy DNG + Log on 12-bit Clear HDR: `setCdngLog` applies only when `srcBits == log->sourceBits`; composed tables have `sourceBits = 16`. Does `cdng_log_applied` report true while the lossy file is square-root? | `grep -n cdngLogAvailable src/camera/CameraController.cpp`; read `buildCdngLogTake` `CC:3963-4045@port` |
| Log curve equal to cinepi-raw `log_lut.hpp` | diff the constants against `/home/user/tiramisioux/cinepi-raw/src/.../log_lut.hpp` |
