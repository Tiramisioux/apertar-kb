# Inventory: Encoders-audio (stage 1, no judgement)

Refs: port = `cinemate-port` 01f170c in /home/user/Apertar-Core; baseline = `origin/main`; upstream = `upstream-1.6.0` (/home/user/wt/core-upstream).
Diff: 20 files, +1712 / -82. Upstream Core has no `tools/` directory (confirmed: `ls tools` fails in core-upstream).
`BlackLevel.hpp` is NOT new: it exists on origin/main (19 lines, `blackLevelForSampleBits`, `blackLevelCfaIndices`); the port extends it.
`CdngEncoder.cpp/hpp` do not call `LogCurve.hpp`; Log is applied in CameraController (copy worker) and handed over as `metadata.linearizationTable` / `setCdngLog` (outside this unit).

## 1. Features in this unit

| # | Feature | Operator sees | Files (this unit) | Commits | Status per fork-log / commit |
| --- | --- | --- | --- | --- | --- |
| F1 | Direct payload write | Nothing directly; fewer drops under Clear HDR 16-bit (one write per frame, 16.6 MB copy saved at 4K 16-bit) | CdngEncoder.cpp (`rowCopyIsIdentity`, `writevAll`, `writeRowsDirect`, `payloadCopyForced`, `configuredPayloadWriteRows`, chunk cap 4 -> 64 MB), tools/dng_payload_write_test.cpp/.sh | e55557d | kb dng-chain-answer.md:194 row 1; host test byte-identical 6 layouts (e55557d, 766aba8 msg). Not in fork-log by that hash. Pi timing result not recorded here |
| F2 | DONTNEED modes | Nothing; drop behaviour. Env `APERTAR_DNG_DONTNEED=sync|writer|off`, or `dontneed=` in `apertar-media-tune.conf` | CdngEncoder.cpp/hpp (`DngPageCacheDrop`, `dngPageCacheDrop()`), LossyDngEncoder.cpp `writeFile` | 0ed07ea (env, default writer), adac040 (default sync), 2edc6d0 (tune file), 766aba8 (lossy honours it) | fork-log:140,142,157 (`f5ac28b` on Pi); "built on Pi 2026-11-04"; adac040 "not built on the Pi yet" at that time |
| F3 | Log curve in the files | "Log" On/Off in cDNG, lossless JPEG, Lossy DNG; DNG LinearizationTable carries the inverse; UI shows Log applied | LogCurve.hpp (new), LossyDngEncoder.cpp/hpp (`buildLogCompanding`, `setCdngLog`, `log_` branch in `writeDngFile`), tools/log_curve_test.cpp, tools/gen_log_curve.py | d44b177 (one squashed commit, 19 commits in all) | fork-log:138 "Not yet run on the camera" at squash time; host tests only. Equal to cinepi-raw `log_lut.hpp` (comment claim, not verified here) |
| F4 | MLV levels = cDNG levels | MLV RAWI black/white correct at 16-bit (was 200, now ~3200); same black in both formats | BlackLevel.hpp (`encodedWhiteLevel`, `encodedBlackLevel`, `kDefaultSourceBlackLevel`), MlvEncoder.cpp `writeRawInfoBlock`, CdngEncoder.cpp, tools/black_level_test.cpp | 5e9dd1a | host test; no fork-log row by that hash; no camera test recorded |
| F5 | Audio writer thread + deep ring | Fewer audio dropouts/pads under heavy writes; log line `peak_backlog_kb`; raw PCM fsynced each second, survives a pulled card | AudioRecordingSession.cpp/hpp (`writerLoop`, `enqueueWrite`, `writeQueue_`), TimestampedAudioCapture.cpp/hpp (hw params by hand, `bufferUs`/`periodUs`) | 60ce8e9, 0358fcf (default 100 ms), b606c4f (1 s fsync) | fork-log:47 "built 23:04, not tested"; :49 built; :54 pull test 5.02 s raw kept, WAV recovered |
| F6 | Audio drift fit | Fewer wrong WAV resamples; log shows `points=`, `endpoint_ppm=` | AudioRecordingSession.cpp `readerLoop` (sums) and `finalizeWav` (slope) | ebdcd08 | fork-log:55 "C0013 fit -15 ppm (6968 points)" |
| F7 | Audio end/start for out-of-order and ramping takes | WAV length matches a speed-ramped clip | AudioRecordingSession.cpp `observeVideoFrame` (`videoLastBootUs_`, `fpsRamp` -> `byDuration`) | d9f00d4 (earliest/latest), faa2958 (`fpsRamp`) | fork-log:35, :58 tested 2026-10-28 (C0030-C0032) |
| F8 | Speed-ramp timecode | FreeRun timecode counts clip-rate frames from first frame's wall time during a ramp | CdngEncoder.hpp `timecodeWallClockUs`, CdngEncoder.cpp `timeCode(...)` call | faa2958 | tested 2026-10-28 |
| F9 | Clip name templates | Compose folder names ({format},{date},{clip},{cam},{sensor},{res},{fps},{bits},{comp},{log},{text:..}); live example; presets and pills in WebUI | util/ClipName.hpp (new), tools/clip_name_test.cpp. Consumers outside unit: ApertarCoreApp.cpp:13242,13265,14341; CameraController.cpp:700,1108-1195,11842-11865; WebControlPage.cpp:14454 | 014a2bf | fork-log:138 (after d44b177); host test only |
| F10 | Yanked-medium handling in encoders | Recording stops cleanly when the drive is pulled; WAV not finalised, raw PCM kept | LossyDngEncoder (`abandon`, `failures`, `lastErrno`, `abandonWrites`, `diskWriteFailures`, `lastDiskWriteErrno`), MlvEncoder (`abandon`, `lastErrno_`, `errnoFromException`), AudioRecordingSession `stop(bool finalize)` | 438a342, e8bb1b7 (moved MLV abandon to MLV worker, in CC) | fork-log:41,42 "fork-only, built 22:27" |
| F11 | Dropped-frame count | UIs show a running total of dropped frames in place of "!"; pre-roll drops are muted | util/RecordingDropWarning.hpp (`droppedFrames`, `markDropped(n)`, `setMuted`, `reset`) | d44b177 (muted, pre-roll), 64bbbaa (count) | fork-log:139 on Pi |
| F12 | Lossy writer env/telemetry | Error line now `errno=N` | LossyDngEncoder.cpp | 438a342 | as F10 |

## 2. Socket commands, HTTP routes, state fields, events, config keys, env vars, files, UI

Nothing in this unit's files defines a command, route, event or UI element. Items that belong to the features above, defined elsewhere, are listed for traceability.

| Kind | Name | Defined where (port) | Feature |
| --- | --- | --- | --- |
| socket cmd | `set_cdng_log value=off|on` | ApertarCoreApp.cpp:13081 | F3 |
| socket cmd | `set_clip_name_template value=` (reply adds `corrected`, `example`) | ApertarCoreApp.cpp:13241 | F9 |
| socket cmd | `preview_clip_name value=` (reply `example`,`template`,`corrected`) | ApertarCoreApp.cpp:13262 | F9 |
| preset key | `cameraClipNameTemplate` | ApertarCoreApp.cpp:14340 | F9 |
| state field | `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` | CameraController.cpp:207-210 | F3 |
| state field | `clip_name_template` (+ runtime `clipNameExample`, not persisted) | CameraController.cpp:235; Types.hpp:156-157 | F9 |
| state field | `recording_dropped_frames` | CameraController.cpp:12889 (also record replies, recording events, `buffer` event) | F11 |
| config key | `camera_settings.conf`: `cdng_log`, `clip_name_template` | CameraController.cpp:854,899,959,981 | F3, F9 |
| config file | `~/apertar-media-tune.conf` key `dontneed=writer|off|(sync)`; override under `/run/apertar-media` (`/dev/shm` per fork-log:142) | util/MediaProfile.hpp:230 `mediaTuneForConfiguredRoot()` read from CdngEncoder.cpp:91 | F2 |
| env var | `APERTAR_DNG_DONTNEED` = `sync` (default) / `writer` / `1` / `off` / `0` / `false` | CdngEncoder.cpp:87 | F2 |
| env var | `APERTAR_DNG_WRITE_ROWS` (1..4096, default 64) | CdngEncoder.cpp:118 | F1 |
| env var | `APERTAR_DNG_PAYLOAD_COPY` (non-0/false/off forces scratch path) | CdngEncoder.cpp:137 | F1 |
| env var | `APERTAR_AUDIO_BUFFER_MS` (100..4000, default 100) | AudioRecordingSession.cpp:215 | F5 |
| env var (outside unit, same chain) | `APERTAR_MEDIA_SYNC_MS`, `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_TUNE`, `APERTAR_MEDIA_TRIM` | CameraController.cpp:4374,4718; README.md:345-350 | F2 |
| file on disk | `audio_capture.raw` now fsynced once per second by the writer thread (opened O_RDONLY for fsync, rawPath_) | AudioRecordingSession.cpp:777 | F5 |
| file on disk | `fps-ramp.txt` (outside unit) | CameraController | F7/F8 |
| log lines (stderr) | `ApertarCore audio writer: peak_backlog_kb=`, `backlog above 16 MB`, `audio capture: buffer_frames= period_frames= requested_ms=`, `audio clock: measured_drift_ppm= points= endpoint_ppm= correction=`, `audio: medium gone, WAV not finalised`, `cdng: APERTAR_DNG_DONTNEED=X is not sync|writer|off`, `MLV: medium gone`, `LossyDng write failed ... errno=N` | respective files | F5, F6, F2, F10 |
| UI element | none in unit. WebUI clip-name pill composer (WebControlPage.cpp:14454, HTML5 drag and drop); Log On/Off control; dropped-frame count in UIs | outside unit | F9, F3, F11 |
| test tools | `tools/log_curve_test.cpp` (also covers `cdngLogBits`, `CdngLog` parse, `ModeLadder` log fields, `ClearHdrCcmp.hpp`, all outside unit), `gen_log_curve.py` (prints golden table, paste into test), `clip_name_test.cpp`, `black_level_test.cpp`, `dng_payload_write_test.cpp` + `.sh` (g++ with `-lyaml`, optional `strace -c`) | tools/ | F1,F3,F4,F9 |
| build | tests are not in CMakeLists (grep found none); each file carries its own `g++` line in a header comment | tools/*.cpp | all |

## 3. Original code modified

| Region | Where (baseline) | Change | Kind |
| --- | --- | --- | --- |
| `kDngBlackLevel = 200` constant | CdngEncoder.cpp:40 | removed; `kDefaultSourceBlackLevel` in BlackLevel.hpp | moved |
| `whiteLevel()` | CdngEncoder.cpp:89 | removed; `encodedWhiteLevel()` in BlackLevel.hpp | moved |
| `blackLevelForEncodedDepth()` | CdngEncoder.cpp:~113 | removed; `encodedBlackLevel()` in BlackLevel.hpp | moved |
| anon namespace in CdngEncoder.cpp | CdngEncoder.cpp:~76 | split by a public `dngPageCacheDrop()` between two anon blocks (`} // namespace` ... `namespace {`) | moved |
| `writeDngFile` DONTNEED call | CdngEncoder.cpp:1777 (upstream `posix_fadvise(DONTNEED)` after write, unconditional) | now only when mode == Writer; default Sync means no call on the writer | behaviour-changed |
| `writeRawPayload` | CdngEncoder.cpp | early return `writeRowsDirect` for identity layouts; scratch chunk cap 4 MB -> 64 MB; rows per chunk 64 (fixed) -> `APERTAR_DNG_WRITE_ROWS` | extended-in-place, behaviour-changed (chunk cap) |
| timecode call | CdngEncoder.cpp:1517 | uses `timecodeWallClockUs` when non-zero | extended-in-place |
| `Metadata` struct | CdngEncoder.hpp:46 | new field `timecodeWallClockUs` | extended-in-place |
| LossyDng `writeFile` | LossyDngEncoder.cpp:82 | DONTNEED gated by `dngPageCacheDrop()` (header now includes CdngEncoder.hpp for it); `errno` kept in a variable and logged | behaviour-changed |
| `LossyDngDiskWriter` | LossyDngEncoder.cpp | new `abandon()`, `failures()`, `lastErrno()`, atomics | extended-in-place |
| `LossyDngEncoder::writeDngFile` | LossyDngEncoder.cpp:~450 | Log branch: `outputBits`, `lutBits`, `black`, `white`, table rebuild condition (`cachedLog_`), inverse table rescale skipped, `blackLevels` filled with log black instead of 0 | extended-in-place (parallel path beside square-root) |
| MLV black/white | MlvEncoder.cpp:~162 and `writeRawInfoBlock` | local `whiteLevel`/`blackLevelForEncodedDepth` removed; uses shared helpers. Old MLV scaled only 8/10-bit, so 16-bit declared 200; new scales every depth by `white/4095` and honours `blackLevelsOnContainerScale` | rewritten, behaviour-changed |
| MLV `open`/`writeFrame` catch | MlvEncoder.cpp:976,1026 | store `lastErrno_`; new `abandon()` | extended-in-place |
| `RecordingDropWarning` | RecordingDropWarning.hpp | latch kept (`dropped()`, `markDropped`, `reset`); `markDropped(frames=1)` signature, running total, mute flag. Muted `markDropped` returns before latching | extended-in-place, behaviour-changed (mute) |
| Audio capture open | AudioRecordingSession.cpp:267, TimestampedAudioCapture.cpp:189 | upstream `snd_pcm_set_params(..., latency 100000)` replaced with manual hw params (period 10 ms, buffer `bufferUs`); 5 more ALSA symbols dlsym'd | rewritten |
| `TimestampedAudioCapture::open` signature | .hpp:27 | two default args `bufferUs=100000, periodUs=10000` | extended-in-place |
| Audio raw write | AudioRecordingSession.cpp readerLoop | direct `rawStream_.write` (and 4096-byte zero loop for pads) replaced by `enqueueWrite` to a queue; failure detected via `writeFailed_` | rewritten |
| `observeVideoFrame` | AudioRecordingSession.cpp:369 | `videoEndBootUs_` recomputed from latest frame each call (was `max` of running ends); tracks first/last/duration; ramp branch | rewritten |
| `AudioRecordingSession::stop` | AudioRecordingSession.cpp:392 | `stop(bool finalize=true)`; joins writer thread; skips WAV and raw delete when `!finalize` | extended-in-place |
| `finalizeWav` drift | AudioRecordingSession.cpp:585 | endpoint ratio replaced by least-squares slope; endpoint kept for the log; needs >=100 points; same 20..2000 ppm window | rewritten |
| `resetState` | AudioRecordingSession.cpp:819 | resets new fields | extended-in-place |
| discontinuity padding | AudioRecordingSession.cpp:~485 | pads queued via `enqueueWrite(nullptr,n)`, also counted in fit (`fitFrames_ += gap/blockAlign`) | rewritten |

## 4. New abstractions

| Name | What | Files | Upstream equivalent for the same job | Used by |
| --- | --- | --- | --- | --- |
| `apertar::cdnglog` (Params, PairConstants, Tables, encode/decode, `buildComposed`, `containerTable`, `applyTable`) | header-only Log curve, std-only, mu-law plus footroom, 3 pairs (16->12, 12->10, 10->8) | cdng/LogCurve.hpp (205 lines) | none: upstream has only the square-root companding in `LossyDngEncoder::buildCompanding` and the CCMP (Clear HDR) table `cdng/ClearHdrCcmp.hpp` (fork main, not upstream). New ground | CameraController (copy worker, `CdngLogTake`), LossyDngEncoder |
| `apertar::clipname` (Parsed, Part, Values, `parse`, `expand`, `nextClipNumber`, `sanitize`, `tokenNames`) | template grammar with tokens, validation, 100-char rule, "Timelapse" prefix reserved | util/ClipName.hpp (296 lines) | upstream builds the name inline: `prefix << formatPrefix << put_time("%y-%m-%d")` then `_C%04d` loop in CameraController.cpp:3665-3669 (and for Still/Timelapse/Audio at :943,:986, ApertarCoreApp.cpp:1459) | App, CameraController, WebUI |
| `DngPageCacheDrop` enum + `dngPageCacheDrop()` | process-wide cached choice from env, then media-tune file | CdngEncoder.hpp/cpp | upstream: unconditional `posix_fadvise(DONTNEED)` at CdngEncoder.cpp:1777 and LossyDng :82; env knobs by `std::getenv` in function-local static (`APERTAR_CDNG_TILE_ROWS`:55, `APERTAR_CDNG_PROFILE_DETAIL`:72) | CdngEncoder, LossyDngEncoder, CameraController sync thread |
| `writeRowsDirect`, `writevAll`, `rowCopyIsIdentity` | zero-copy payload write | CdngEncoder.cpp (anon) | upstream: scratch buffer path only (`takePayloadScratch`) | `writeRawPayload` |
| Shared level helpers (`encodedBlackLevel`, `encodedWhiteLevel`, `kDefaultSourceBlackLevel`) | one source for cDNG and MLV | cdng/BlackLevel.hpp | upstream: two private copies, one in each .cpp (CdngEncoder.cpp:89,113; MlvEncoder.cpp:162,~170) | cDNG, MLV, CameraController:4002 |
| Audio writer thread + `writeQueue_` (deque of vectors, mutex, cv) + `writeFailed_` | unbounded RAM queue between reader and `rawStream_`, 1 s fsync, 16 MB backlog log only (no cap) | AudioRecordingSession.cpp/hpp | upstream: reader writes straight to `rawStream_`. Worker-thread precedents upstream: `LossyDngDiskWriter` (LossyDngEncoder.cpp:252, bounded by `APERTAR_LOSSYDNG_WRITER_BYTES`), ProRes writer (`APERTAR_PRORES_WRITER_THREAD/QUEUE`) | AudioRecordingSession |
| Drift fit accumulators (`fitSumT_` etc., 4 doubles, 3 counters) | running least-squares | AudioRecordingSession.hpp | upstream: endpoint ratio `availableFrames / capturedDurationUs` | `finalizeWav` |
| Test tools | host tests with `check()` macros, golden table generator | tools/* | none (upstream has no tests, no tools dir) | manual `g++` |

## 5. Removed, narrowed or hidden relative to upstream

| What | Where | Effect |
| --- | --- | --- |
| Writer-side `posix_fadvise(DONTNEED)` by default | CdngEncoder.cpp:1897; LossyDng :104 | default is `sync`: cDNG relies on the sync thread (CameraController.cpp:4761, needs `APERTAR_MEDIA_SYNC_MS > 0`; CC:4374 warns otherwise). Lossy DNG has no sync thread, so by default Lossy DNG never drops its pages (same as `off`) |
| MLV 16-bit black 200 | MlvEncoder.cpp | declared level changes (now ~3200 at 16-bit); old MLV files differ |
| Fixed 4 MB scratch write cap | CdngEncoder.cpp | up to 64 MB per write call when rows setting is raised; default 64 rows still gives about 4 MB at 16-bit 4K? (rowBytes x 64: 491,520 B, so the cap is no longer binding) |
| Audio ring 100 ms via `snd_pcm_set_params` | TimestampedAudioCapture.cpp | replaced by hand-set params; probe/idle path default args unchanged (100 ms, 10 ms period; set_params used latency 100 ms with period = latency/4 = 25 ms, so the default period shrank 25 -> 10 ms) |
| Audio `stop()` always finalised | AudioRecordingSession | now optional; raw PCM left on a dead medium |
| Endpoint-ratio drift as the applied value | finalizeWav | fit slope applied; endpoint only logged. cinemate-lessons section 3: Cinemate retired whole-take ratio ("cannot tell clock drift from sample loss"); the port keeps resampling with a fit and kb's recommendation (per-device ppm, tight clamp) is not what was built |
| Immediate drop flag during pre-roll | RecordingDropWarning | muted, not latched |
| Nothing removed from the public API of the encoders | | all new members are additive; `stop()` and `open()` keep call-compatible signatures through default args |

## 6. Board assumptions in this unit

| Assumption | Where | Note |
| --- | --- | --- |
| Pi 5 / CM5 only | none found in the unit's files | no `/proc/device-tree`, gpiochip, I2C bus, RP1, PCIe, fan, RAM-size or core-count constants in these 20 files (grep not run on non-scope callers) |
| Core count | none here | `64 MB` and 64-row defaults are not tied to RAM size |
| Throughput figures in comments | CdngEncoder.cpp comment "16.6 MB at 4K 16-bit, the Clear HDR case"; dng-chain-answer "0.83 GB/s at 25 fps" | Pi 5 + NVMe/exFAT measurements; behaviour is generic Linux |
| ALSA | `libasound` via dlopen; hw params `set_*_near`; ring and period requests | board independent; USB mic assumed (ring 100 ms default chosen on a USB mic, "RØDE" in kb) |
| Linux-specific calls | `writev`, `IOV_MAX`, `posix_fadvise`, `memfd_create` (existing), `fsync` on a re-opened O_RDONLY fd | fine on any Linux; fsync of re-opened file works because data was `flush`ed first |
| 12-bit reference scale | `blackLevelForSampleBits` scales by `white/4095` | sensor-agnostic, assumes metadata black on 12-bit scale unless `blackLevelsOnContainerScale`; Log pairs fixed to 16/12/10 source bits; constants `kPairs` tuned for IMX585 16-bit (black 3200) in the golden tests |
| Test script | `dng_payload_write_test.sh` needs `libyaml` (`-lyaml`) and writes under `${TMPDIR:-/tmp}` | host only |

## 7. Open points the stage-2 reviewer should check (not judged here)

| Point | Evidence |
| --- | --- |
| `LogCurve.hpp` comment says same curve as cinepi-raw `cinepi/log_lut.hpp`; the 10->8 pair has no cinepi spec (derived) | LogCurve.hpp:30-31 |
| `tools/log_curve_test.cpp` depends on files outside this unit (`cdngLogBits`, `CdngLog`, `ModeLadder`, `ClearHdrCcmp`) | log_curve_test.cpp:3-6 |
| `writeRowsDirect` assumes `frame.stride >= rowBytes`; no check | CdngEncoder.cpp writeRowsDirect |
| Audio queue has no size cap, only a log at 16 MB | AudioRecordingSession.cpp writerLoop |
| Drift fit is guarded to 20..2000 ppm and >=100 points; padded gaps feed the fit as zero-length-time samples | finalizeWav, readerLoop |
| `MlvEncoder.cpp` now includes `util/MediaFault.hpp` (outside unit) for `errnoFromException` | MlvEncoder.cpp:1 |
| `CdngEncoder.cpp` now includes `util/MediaProfile.hpp` and `<iostream>` (media tuning layer) so the encoder reads a config file at first use | CdngEncoder.cpp:7,21,91 |
| Commit trail: F2 spread over 5 commits (0ed07ea, adac040, 766aba8, 2edc6d0 plus `f5ac28b` squash on Pi); F3 and F11 live inside the 19-commit `d44b177` | git log above |
| Clip names: upstream names Still/Timelapse/Audio folders inline; template applies to clips only (Timelapse prefix reserved) | ClipName.hpp parse |
