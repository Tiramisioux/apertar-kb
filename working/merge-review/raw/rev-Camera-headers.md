# Review: unit Camera-headers (stage 2)

Refs: port = `cinemate-port` `01f170c` (Apertar-Core); main = `origin/main` `f60e301`; upstream = `upstream-1.6.0` `35dbe67`.
Yardstick: `raw/conv-core-camera.md` (rule ids S*, I*, N*), `raw/conv-core-command-plane.md` (C1-*). No `apertar-conventions.md` yet.
Read completely: the 7 headers, CC.hpp and Types.hpp diffs vs main, the 4 tests (heads). Read in part: port CC.cpp around every call site
named below; upstream `ProresIspProfile.{hpp,cpp}`, CC.cpp `enforceLosslessCaptureLimits`, `maximumSupportedFpsForResolution`, start path.
Host tests: all four compile with g++ here and print 0 FAIL (confirmed, 2026-11-17).

## 1. Findings

| Id | Sev | Cat | Title | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | major | mismatch | TDN strip brings its own JSON parser, atomic writer and sidecar; upstream already derives tuning files with libyaml + `settingsFile::atomicWrite` | yes |
| F2 | major | bug / removed behaviour | `preview_tdn` defaults to off, and the stripped tuning feeds every ISP output: H.264, ProRes and JPEG/PNG/TIFF stills lose TDN, not only the preview | partly |
| F3 | major | removed-upstream-behaviour | IMX585 lossless cDNG 30 fps cap lifted by default | yes |
| F4 | major | removed-upstream-behaviour | FPS ceiling: probe now wins over the table (4K SDR 30 -> 60) by default | yes |
| F5 | major | mismatch | Mode ladder persists in its own `mode_ladder.conf` instead of `camera_settings.conf` | unknown |
| F6 | minor | mismatch | `Rung::compression` is a free string mixing format and compression; upstream uses the enums | no |
| F7 | minor | mismatch | `setModeLadder` / `applyLadderToPreset` / `setClipNameTemplate` return data through out-params and error strings; upstream setters are `bool` + `lastError()` | no |
| F8 | minor | protocol / mismatch | `get_mode_ladder` / `set_mode_ladder` reply is deeply nested (arrays of objects with sub-objects) | no |
| F9 | minor | mismatch | 9 ladder runtime fields (one a vector, one a UTF-8 display string) added to `CaptureSettings` | no |
| F10 | minor | mismatch / duplication | Sensor tables: own `Size` types, two distance metrics, legacy IMX585 whitelist kept beside the table | no |
| F11 | minor | duplication | Env parsing re-implemented three times instead of `unsignedEnvValue` / `boolEnvValue` | no |
| F12 | minor | slop | T31/T34 numbers in code and in the user's `mode_ladder.conf`; Cinemate narration; stale `{d, d}` comment | no |
| F13 | minor | slop | `conformFps`: persisted, socket command, preset key, no effect ("nothing derives from it yet"), no UI | yes |
| F14 | nit | slop | Compatibility for never-released spellings: `cdng_log` "12/10/8", ladder `log10/log8`, file key `rungs`; enum `CdngLog::Auto` means On | yes |
| F15 | minor | new-ground | `tools/*_test.cpp`: 4 host tests, 3 styles, no build hook; the phase lock (most delicate) has none in the repo | yes |
| F16 | nit | new-ground | `FpsCeiling.hpp`: three one-line functions split out only for a test | yes |

### F1 TDN strip: own JSON parser (mismatch, major)

Port: `src/camera/TuningTdnStrip.hpp:43-249@cinemate-port` a recursive-descent JSON parser (`tdn_detail::Parser`, `Node`, `Member`);
`:350-378` own temp+rename writer; `:380-387`, `:411`, `:446` a `.src` sidecar with size+mtime; cache `$HOME/.cache/apertar-core/tuning`.
451 lines, header-only, includes `DefaultTuningSelection.hpp`.

Upstream does the same kind of thing already, in one function:
`src/color/ProresIspProfile.hpp:7@upstream-1.6.0` "// Writes an internal derived tuning, never the user's selected source file.";
`src/color/ProresIspProfile.cpp:13` `#include <yaml.h>`; edits located by libyaml marks, applied back to front
(`:208-224`, "libyaml marks count Unicode characters; string::replace uses bytes"); cache `$HOME/.cache/apertar-prores/<profile>.json`
(`:230`); rewrite only when content differs: `if (previous!=text && !settingsFile::atomicWrite(path,text))` (`:233`). Called at start
(`CC.cpp:5347-5361@upstream`), `setenv("LIBCAMERA_RPI_TUNING_FILE", ...)`.

Why it matters: the original developer finds two tuning-JSON editors, two cache dirs, two atomic writers. S23 (few deps, but libyaml is the one
already required for this job), S6 (`settingsFile::atomicWrite` is the shared writer).

Rework (pick one):
- A. Smallest: libcamera's PiSP pipeline handler has `"disable_tdn"` (`pisp.cpp:1656`, `data/example.yaml:33` in `tiramisioux/libcamera@6b0b49f`;
  in mainline libcamera too, **probable**). Write a 3-line pipeline config once and `setenv("LIBCAMERA_RPI_CONFIG_FILE", ...)` beside the
  existing `LIBCAMERA_RPI_TUNING_FILE` setenv. Also skips allocating the TDN buffers. Deletes `TuningTdnStrip.hpp` and its test. Check
  first that the env var is not already used by Core.
- B. Keep a derived tuning: add `bool makePreviewTuning(const std::string &source, std::string &destination, std::string &error)` to
  `src/color/ProresIspProfile.cpp` (or a sibling `.cpp` in `src/color/`), reuse its libyaml `algorithm()` / `member()` / `Edit` helpers to cut
  the `tdn` members, write with `settingsFile::atomicWrite` to `$HOME/.cache/apertar-core/...` only when the content changed; drop the sidecar.

### F2 `preview_tdn` default off reaches recordings (bug, major)

`Types.hpp@cinemate-port` `bool previewTdn = false; // ... Off (default) is much faster; the raw DNGs never change.`
`CC.cpp:7308-7326@cinemate-port`: `loadablePath()` hands `previewTuningPath()` output to `applyProcessTuningFile` for every start, whatever
`recordingFormat` and `photoModeEnabled` are. The tuning file drives the whole ISP, and H.264 and ProRes record ISP outputs
(conv-core-camera 5.4: VideoRecording YUV / RGB48 streams). Processed stills (JPEG/PNG/TIFF) also come from the ISP.
Failing input: fresh settings, `set_record_format h264` (or `prores`), record: the file is encoded from an ISP without temporal denoise;
upstream records with the tuning's TDN. Code path confirmed; the visible noise change is probable.
Also a changed default against upstream: upstream preview always runs the tuning as given.
Rework: default `previewTdn = true` (upstream behaviour) and/or apply the strip only when the take is RAW (`!isProcessedVideoFormat(...)`
and not photo mode); rename to what it is (it is an ISP setting), correct the comment.

### F3 IMX585 lossless 30 fps cap lifted (removed-upstream-behaviour, major)

Upstream `CC.cpp:2470-2490@upstream-1.6.0` `enforceLosslessCaptureLimits`: `const double maximumFps = imx585 ? 30.0 : ...`.
Port `CC.cpp:3134-3142@cinemate-port`: `imx585 ? fpsceiling::losslessImx585Fps(modeMaximumFps(...), losslessFpsOverride())`; comment
"the measured lossless encoder capacity at 4K 12-bit is ~69 fps, so 30 was a policy, not a limit". Restore only by env
`APERTAR_LOSSLESS_FPS_LIMIT=30`. KB `dng-chain-answer.md:156` says 60 fps lossless does not fit storage. Fork-log: not run on the camera.
Rework: keep 30 as the default; let `APERTAR_LOSSLESS_FPS_LIMIT=<n>` raise it (I9 knob for bench work). Removes the need for
`losslessImx585Fps` as a policy flip.

### F4 Probe wins over the table (removed-upstream-behaviour, major)

Upstream: hard-coded tables, `validate()` last word (N7); IMX585 4K = 30 (`CC.cpp:2669-2671@upstream`). Main `f60e301` added the probe as
`min(table, probed)`; its message: "SDR limits unchanged (the probe only lowers them)" and "Recording at 30 fps still loses ~20 %".
Port `FpsCeiling.hpp:14-19`: probe wins, `APERTAR_FPS_LIMIT=table` restores; `CC.cpp:3397-3423@cinemate-port`.
Effect: 4K SDR offered up to 60 fps by default, untested on the camera (inventory feature 1).
Rework: keep main's `min(table, probed)` default; raise individual table rows where the new driver and takes prove it; an opt-in knob
`APERTAR_FPS_LIMIT=probe` for bench work. Then `resolveSensorMaxFps` is one `std::min` and FpsCeiling.hpp can fold back into CC.cpp (F16).

### F5 `mode_ladder.conf` (mismatch, major)

Port: `ModeLadder.hpp:316-342` `fileText` / `parseFile`; path `CC.cpp:404-414@cinemate-port`; own writer `saveModeLadderLocked`.
Upstream S20: camera settings persist in `~/.config/apertar-core/camera_settings.conf`, `key=value`, written only by Core through the
debounced persister (`CC.cpp:742-889@upstream`), global keys copied across format profiles like `tuning_file` (N14, `CC.cpp:7939-7955`).
Rework: three global keys `mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_resolutions` (the existing comma text) in the
`else if (key == ...)` chain (I15) and the writer; hold them in `CaptureSettings` like `tuningFile` and keep them across format switches
in the block at `CC.cpp:11340-11370@cinemate-port`. Delete `fileText`, `parseFile`, the path function, the `rungs` legacy key.

### F6 `Rung::compression` string (mismatch, minor)

`ModeLadder.hpp:22-25`, `:29-32`, `:41-44`: `std::string compression` = "" | "none" | "lossless_jpeg" | "lossy_3to1" | "lossy_5to1".
Upstream S13/I11: each sub-option is an enum (`CdngCompression`, `LossyDngRatio`, `RecordingFormat`, `Types.hpp:45-68@upstream`) with
`toString` / `toWireValue`. Rework: `std::optional<RecordingFormat> format; CdngCompression cdngCompression; LossyDngRatio lossyDngRatio;`
(or one small enum `RungRecord { Default, Uncompressed, Lossless, Lossy3, Lossy5 }`), parse with the existing wire words.

### F7 Out-param setters (mismatch, minor)

`CC.hpp@cinemate-port`: `setModeLadder(optional<string>, optional<bool>, optional<bool>, bool dryRun, string *json, string *error)`,
`applyLadderToPreset(CaptureSettings &, bool, string *error) const`, `setClipNameTemplate(const string &, string *stored)`.
Upstream S7/I1: `bool set...(value)`, error via `lastError()`, App replies `settingsBody(camera_.settings())` (`CC.hpp:39-63@upstream`).
Rework: `bool setModeLadder(const std::string &resolutions, bool enabled, bool rampReady)` + `bool validateModeLadder(...)` for the dry run,
errors via `setErrorLocked`, App builds the reply with `camera_.modeLadderJson()`; drop `*stored` (the normalised template is in settings).

### F8 Nested ladder reply (protocol, minor)

`ModeLadder.hpp:265-314` builds `{"resolutions":[{...,"ceilings":{...}}],"pool":[...],"errors":[...],"warnings":[...]}`.
Upstream: replies are flat with a fixed short list of nested members (conv-core-command-plane 5.5, C1-I09 for input).
The input side conforms (the list travels as one comma string). Nothing in the original UI or Core parses this reply: no break.
Rework (optional): keep, but document it as the one structured editor reply; or flatten to `resolutions_text`, `errors` / `warnings` as `|`
strings, and per-row data as parallel comma strings. Keep `toJson` next to the type (I12 precedent `recordingCapabilitiesJson`).

### F9 Ladder state in `CaptureSettings` (mismatch, minor)

Types.hpp adds `fpsTakeMax`, `ladderActive`, `ladderRung`, `ladderRampReady`, `ladderEnabled`, `ladderOverride`, `ladderCount`,
`std::vector<double> ladderTops`, `std::string ladderText` (example with "·", "×", "≤"). Upstream S21: runtime fields in
`CaptureSettings` are capabilities (5 fields, `Types.hpp:132-150@upstream`); controller state leaves through its own getter
(`stillExposureStatus()`, `mediaWriteStatus()`, `recordingHasDroppedFrames()`); I13 makes every field cost three serialiser edits.
Rework: `struct ModeLadderStatus` + `modeLadderStatus() const`, serialised by App like `PhaseLockStatus` already is; keep `isoMax`,
`fpsMax`, `isoMeasured` (capability-like) in `CaptureSettings`. Build `ladderText` in the client, ASCII in Core.

### F10 Sensor tables (mismatch / duplication, minor)

Upstream S11/S4: sensor tables are free functions and arrays in CC.cpp (`isImx585*Resolution` `:360-396`, `kImx477Modes` `:2309`),
`Resolution` from Types.hpp. Header-only pure helpers exist (S4), so the headers themselves are acceptable.
Deviations: `imx283::Size` (`Imx283Modes.hpp:19-22`) and `imx585::Size` (`Imx585Modes.hpp:34-38`) beside `Resolution`;
nearest = squared Euclidean in imx283 (`:126-128`), Manhattan in imx585 (`:243-245`); CC.cpp keeps `isImx585LegacyCropResolution`
(`CC.cpp:497-509@cinemate-port`) whose height lists repeat table rows, plus alias functions.
Rework: use `Resolution`; one distance rule; replace the legacy height lists by a table query; keep the alias map (it is client compatibility).

### F11 Env parsing duplicated (duplication, minor)

`Imx585Modes.hpp:105-114` `minModeWidth()` (re-read on every `find`/`offered` through the default argument),
`FpsCeiling.hpp:29-38` `parseLosslessFpsLimit`, `CC.cpp:8909-8922@cinemate-port` phase-lock lambda. Upstream `unsignedEnvValue(name, default,
min, max)` and `boolEnvValue` (`CC.cpp:1027-1061@upstream`), read once in function-local statics (I17).
Rework: `minModeWidth()` = `static const unsigned w = unsignedEnvValue("APERTAR_IMX585_MIN_MODE_WIDTH", 1280, 0, 65535);` in CC.cpp,
passed in as a parameter; add a `doubleEnvValue` beside the two helpers for the fps and phase-lock knobs.

### F12 Slop in comments and user file (slop, minor)

- `ModeLadder.hpp:1` "Mode ladder (T34)"; `:319` `fileText` writes "# Apertar mode ladder (T34)." into the user's config file.
- `Types.hpp` 9 T-numbers (`Speed ramping (T31)`, `Runtime (T34)` x7); `CC.hpp` 4 (`T34`, `T31`). I19: no ticket numbers.
- Cinemate narration: `FramePhaseLock.hpp:18` "as Cinemate's libcamera does"; `Imx283Modes.hpp:1-2` names the fork repo and branch
  `cinemate-port`; `Imx585Modes.hpp:3`, `:16` "as in cinemate"; `CC.cpp:8907-8908` "Cinemate kept them as live keys". "CineMate Log"
  as the Apertar name of the feature (`Types.hpp:59`, `:355`).
- Stale: `FramePhaseLock.hpp:48` "send FrameDurationLimits {d, d}", but the controller pins `{d, d+1}` (`CC.cpp:9069@cinemate-port`,
  and the header's own line 17). The overview comment (`:9-26`) sits above `PhaseLockStatus`, not above `FramePhaseLock`.

### F13 `conformFps` (slop, minor)

`Types.hpp` "nothing derives from it yet"; persisted (`CC.cpp:696-697`), `set_conform_fps` (`App:13270`), state keys, preset key
(`WCP:19111` only in the preset key list); 0 hits in Apertar-UI. Rework: remove the field, command, state keys and preset key until a
feature uses it.

### F14 Never-released compatibility (slop, nit)

`cdngLogFromString` maps "on", "12", "10", "8" to `Auto`; ladder parses `log10`, `log8`; `parseFile` reads `rungs`. These spellings never
shipped in Apertar. `CdngLog { Off, Auto }` has two values and `Auto` means On. Rework: `enum class CdngLog { Off, On }` (wire "off"/"on"),
drop the legacy spellings.

### F15 Host tests (new-ground, minor)

Upstream S24: no tests, no `tools/`. Port: `tools/*_test.cpp`, built by hand from a comment, three check styles (`check()`, `CHECK` macro,
`expectStrip`). `imx283_modes_test.cpp` types the 57-row table a second time. The phase-lock simulator lives in the KB
(`working/tools/phase_lock_sim.cpp`), not in the repo. Verdict: simplify. One folder `tests/`, one tiny check helper, one opt-in CMake
option `APERTARCORE_BUILD_TESTS` (OFF), a one-line README note; add the phase-lock test or drop the claim; delete the TDN test if F1-A.

### F16 FpsCeiling.hpp (new-ground, nit)

Three functions of one to four lines; header exists so the test can include them. After F4/F3 rework the rules are `std::min` calls;
fold them back next to `maximumSupportedFpsForResolution` in CC.cpp (S3/S4: most pure logic lives in CC).

## 2. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `apertar::fpsceiling` | simplify | F4/F3 restore upstream defaults; the rest is `std::min`; fold into CC.cpp |
| `FramePhaseLock` + `PhaseLockStatus` | keep | New ground, off by default, pure state machine in a small header like `src/audio/RecordingClock.hpp` (S4); status getter matches `stillExposureStatus()`. Fix comments (F12), env via helpers (F11), put its test in the repo (F15). Deliberate: `working/phaselock-answer.md` |
| `apertar::imx585` | keep (align) | Table-driven facts in a pure header is acceptable (S4); use `Resolution`, one distance rule, drop the duplicated legacy lists in CC.cpp (F10) |
| `apertar::imx283` | keep (align) | Same as imx585; a new sensor family has to live somewhere and upstream's `switch (SensorFamily)` call sites are kept |
| `apertar::ladder` | rework-to-upstream-pattern | Keep pure logic (chooser, validator, text form); persistence into `camera_settings.conf` (F5), enums for compression (F6), `bool` setter + `lastError` (F7), status getter instead of 9 `CaptureSettings` fields (F9) |
| `NativeScalerCrop` + `activeAreaScalerCrop` | keep | Same file, same shape as `centered*ScalerCrop`, no hard-coded native coordinates |
| `apertar::tuning` TDN strip (`Parser/Node/Member`, `TdnStripResult`) | rework-to-upstream-pattern | Upstream derives tuning with libyaml + `settingsFile::atomicWrite` (`ProresIspProfile.cpp`); or use libcamera `disable_tdn` (F1); default and scope (F2) |
| `CdngLog` + 5 free functions | simplify | Enum + `toString` in Types.hpp is the upstream pattern (I11); two values `Off/On`, drop legacy spellings (F14) |
| `FrameBufferStatus`, `StoragePrerollResult` | keep | Nested result structs in CC.hpp, like `MediaWriteStatus` / `StillExposureStatus` |
| `SensorBinning` (+ `SensorMode::binning/binningSource`) | simplify | Fields repeated in two structs; `binningSource` a string where upstream uses an enum + `toString` (I11). nit |
| `tools/*_test.cpp` | simplify | F15 |

## 3. Conforms

- `ScalerCropGeometry.hpp`: the addition sits beside the two upstream functions, same signature style, `std::optional` failure, 28 lines (S4).
- No libcamera include in any new header; CC.hpp still includes only project headers and std (S1).
- `CdngLog` enum + `toString(CdngLog)` at the bottom of Types.hpp, `cdngLogFromString` in the header with `bool` return (I11, its
  `parseProresColorProfile` exception).
- New settings as `CaptureSettings` member initialisers (I14); `isoMax`, `fpsMax`, `isoMeasured` as commented runtime fields (S21).
- `AudioRecordingOptions::fpsRamp`: per-take input in the option struct (S19).
- New `bool set...` setters (`setCdngLog`, `setFpsPhaseLock`, `setPreviewTdn`, `setMediaTrimEnabled`, `setConformFps`) on the one class
  under one mutex; private helpers end in `Locked` (S7, I10). `setPreviewTdn` follows I1 and N5 (gate while recording, no-change path,
  `applySettingsLocked(next, true)`, `CC.cpp:11900-11916@cinemate-port`).
- Env knobs named `APERTAR_<AREA>_<KNOB>`, read once into function-local statics, one log line when set (I9, I17).
- Mode-ladder command input is flat, the list travels as one comma string (C1-I09).
- Phase lock off by default; the servo is pure and does no I/O.
- Nothing of the original CC.hpp or Types.hpp was removed; `setIsoAuto(bool enabled = true)` keeps old callers and old clients working.

## Skeptic

Stage 3, 2026-11-17. Every finding re-read in code at `cinemate-port` `01f170c`, `upstream-1.6.0` `35dbe67`, `origin/main` `f60e301`,
`tiramisioux/libcamera@6b0b49f`, plus the commit messages and KB pages named.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Port and upstream code confirmed. Option A is withdrawn: `disable_tdn` stalls the back end (`pisp.cpp:1659-1663@6b0b49f` erases `TdnInput` twice, `TdnOutput` keeps 0 buffers; KB `research-30fps-answer.md:78`, `dng-chain/F/V-F2.md:36`, all handoffs say "never `disable_tdn`"). "Nothing in the KB weighs libyaml" is wrong: KB `dng-chain/F/F6.md:243` (3a) and `V-F6.md:36` (row 7) proposed exactly the libyaml derivation modelled on `makeProresIspTuning`; the port wrote its own parser instead. Only option B remains |
| F2 | stands | Confirmed: `Types.hpp:139` default false; `CC.cpp:7308-7326` strips for every start; also `CC.cpp:7411` builds the ProRes/log derived tuning from `activePath`, i.e. from the stripped copy. Commit `e625c68` and the KB only mention DNGs |
| F3 | corrected | Code confirmed. The cited evidence is wrong: `dng-chain-answer.md:156` "60 fps (746 MB/s) does not fit" is 4K 12-bit uncompressed, not lossless; the KB has one 2 s 4K 60 fps lossless pre-roll with 0 skips (`dng-chain-answer.md:30`). Still an upstream product limit changed by default with one 2 s datum |
| F4 | stands | Confirmed: `FpsCeiling.hpp:14-19`, `CC.cpp:3397-3423`; upstream table 30 (`CC.cpp:2669-2671@upstream-1.6.0`); main `f60e301` "SDR limits unchanged (the probe only lowers them)"; 4K 12-bit uncompressed at 60 does not fit the drive (`dng-chain-answer.md:156`) |
| F5 | corrected | Code confirmed. Deliberate is yes, not unknown: `ramp-ladder/design/design-T34.md:280-293` (3.3) weighed UI.conf and the per-format profile keys and chose a new file; it did not weigh camera-wide keys in `camera_settings.conf`, the way the port itself already carries `previewTdn`, `cdngLog`, `clipNameTemplate` across profiles (`CC.cpp:11338-11372`). "Presets do not see it" is half wrong: `applyLadderToPreset` consults the ladder |
| F6 | stands | `ModeLadder.hpp:22-44` confirmed; upstream enums `Types.hpp:45-68@upstream-1.6.0` |
| F7 | corrected | `setClipNameTemplate` already reports errors through `setErrorLocked` (`CC.cpp:11835-11854`); only its `*stored` out-param is redundant. The `*error` channel is in `setModeLadder`, `applyLadderToPreset` and `previewClipName` (`CC.hpp:100-109`). `modeLadderJson()` already exists |
| F8 | dropped | Upstream replies already carry arrays of objects (`modes`, `App:10042-10048@upstream-1.6.0`, conv-core-command-plane 5.5); input is flat. The proposed rework was "keep it" or a flattening that reads worse. Nothing to change |
| F9 | corrected | Upstream `CaptureSettings` is not capabilities only: `whiteBalanceMeasured`, `previewExposureReference`, `timelapseExposureLimitUs` are runtime state (`Types.hpp:139-150@upstream-1.6.0`). Design `design-T34.md:336-345` (3.6) chose this deliberately after `exposureCompensationAvailable`. What stays foreign: the UTF-8 display line `ladderText` and the redundant `ladderCount`. Rework shrinks to that |
| F10 | corrected | Size types and the two distance rules confirmed. The legacy-list part is dropped: `isImx585LegacyCropResolution` is the shape of upstream's own `isImx585FullHdCropResolution` / `isImx585Raw12CropResolution` (`CC.cpp:365-396@upstream-1.6.0`) and keeps what other sensors' validators accept; a table query would change that. Severity nit |
| F11 | stands | Three parsers confirmed (`Imx585Modes.hpp:105-114`, `FpsCeiling.hpp:29-38`, `CC.cpp:8909-8922`); upstream helpers at `CC.cpp:1027-1061@upstream-1.6.0`, also in the port at `CC.cpp:1341-1357` |
| F12 | stands | All quotes confirmed; upstream has no "cinemate" and no T-numbers in `src`/`include`. Add `CC.cpp:9063-9067` ("qbc libcamera", "Cinemate's libcamera") |
| F13 | stands | Only stored, serialised and settable; no reader in `src` (`grep conformFps`), no UI, WebUI only in the preset key list `WCP:19111`. Commit `d7ff071` |
| F14 | stands | `Types.hpp:338-341`, `ModeLadder.hpp:168`, `:337` confirmed; fork main has no `cdng_log` at all |
| F15 | corrected | The four tests are part of a port-wide `tools/` set of 20 test files (`tools/*_test.cpp`, `*.sh`); the home and build hook is a port-wide decision, not this unit's. The IMX283 table repeated in the test is an independent oracle, acceptable. No header claims a phase-lock test; the sim is in the KB (`working/tools/phase_lock_sim.cpp`) |
| F16 | stands | 47 lines, four one-to-four-line functions; nit, after F3/F4 |

## Final findings

### Camera-headers-F1 [mismatch, major] TDN strip: own JSON parser, atomic writer and sidecar where upstream derives tuning files with libyaml
- where: `src/camera/TuningTdnStrip.hpp:43-249@cinemate-port` (parser); `:350-378` (writer); `:380-449` (sidecar, cache path); `tools/tuning_tdn_strip_test.cpp@cinemate-port`
- port way: header-only recursive-descent JSON parser (`tdn_detail::Parser/Node/Member`) cuts `tdn` members by byte offsets; own temp+rename writer; `.src` sidecar with size+mtime; cache `$HOME/.cache/apertar-core/tuning`. 451 lines.
- Apertar way: `src/color/ProresIspProfile.hpp:7@upstream-1.6.0` "Writes an internal derived tuning, never the user's selected source file."; `ProresIspProfile.cpp:13` `#include <yaml.h>`, `algorithm()/member()` lookup `:72-87`, `Edit` byte ranges applied back to front `:89-90`, `:221`; cache `$HOME/.cache/apertar-prores` `:230`; `if (previous!=text && !settingsFile::atomicWrite(path,text))` `:233`.
- why it matters: two tuning-JSON editors, two cache dirs, two atomic writers. 200 lines of parser to maintain beside the libyaml path upstream already requires.
- rework: add `bool makePreviewTuning(const std::string &source, std::string &destination, std::string &error)` to `src/color/ProresIspProfile.cpp` (or a sibling `.cpp` in `src/color/` with the helpers moved to a shared internal header), reusing libyaml `algorithm("rpi.denoise")`, `member()`, `Edit`. Per KB `V-F6.md:36`: replace each `rpi.denoise` mapping node with its content minus `tdn` (one `replace` per node), so no comma surgery. Write with `settingsFile::atomicWrite` only when the content changed; drop the sidecar (the content compare replaces it). Keep `previewTuningPath`'s fall-back-to-source rule and its call site. Delete `TuningTdnStrip.hpp`; turn its test into a check of the new function or delete it. Do not use the pipeline `disable_tdn` option: it stalls the back end (`pisp.cpp:1659-1663@6b0b49f`).
- rework risk: the output is no longer byte-identical to the KB tool's `_notdn` files; check `rpi.denoise` still loads (SDN/CDN take their `*_no_tdn` values, `denoise.cpp:54-69`) on the Pi.
- effort M; deliberate: yes (commit `e625c68`; KB `clearhdr16-preview.md`, `dng-chain-answer.md:35-40` weigh the TDN cost). The KB recommended the libyaml route (`dng-chain/F/F6.md:243` 3a, `V-F6.md:36`); the port did not follow it and no note says why.

### Camera-headers-F2 [bug, major] preview_tdn defaults to off and the stripped tuning reaches H.264/ProRes recordings and processed stills
- where: `include/apertar/core/Types.hpp:139@cinemate-port`; `src/camera/CameraController.cpp:7306-7326@cinemate-port`; `:7411` (`makeProresIspTuning(activePath, ...)`); `src/camera/TuningTdnStrip.hpp:3-6@cinemate-port`
- port way: `bool previewTdn = false; // ... Off (default) is much faster; the raw DNGs never change.` `loadablePath()` hands every camera start the copy without `tdn`, whatever `recordingFormat` or photo mode; the ProRes/log derived tuning is then built from that stripped copy.
- Apertar way: the tuning file as resolved drives every stream (`CC.cpp:5265-5268`, `:5347-5361@upstream-1.6.0`). H.264 and ProRes record ISP outputs (conv-core-camera 5.4), and so do JPEG/PNG/TIFF stills.
- why it matters: fresh settings, `set_record_format h264` or `prores`, record: the file is encoded from an ISP without temporal denoise; upstream records with it. Code path confirmed; visible noise change probable. The header and Types.hpp comments say only monitoring is affected, which is wrong for these formats.
- rework: in `loadablePath`, strip only for RAW takes: `!settings.previewTdn && !isProcessedVideoFormat(settings.recordingFormat) && !settings.photoModeEnabled`; or default `previewTdn = true` (upstream behaviour). Correct both comments. A format switch already restarts the pipeline, so the tuning follows.
- effort S; deliberate: unknown (the default off is deliberate, commit `e625c68`; nothing in commit or KB weighs processed formats).

### Camera-headers-F3 [removed-upstream-behaviour, major] IMX585 lossless cDNG 30 fps cap lifted by default
- where: `src/camera/FpsCeiling.hpp:27-45@cinemate-port`; `src/camera/CameraController.cpp:3115-3142@cinemate-port`
- port way: `losslessImx585Fps` returns the mode's maximum; only `APERTAR_LOSSLESS_FPS_LIMIT=30` restores the cap. Comment: encoder measured ~69 fps, "30 was a policy, not a limit".
- Apertar way: `CC.cpp:2470-2490@upstream-1.6.0` `enforceLosslessCaptureLimits`: `const double maximumFps = imx585 ? 30.0 : ...`, applied in the sanitise chain (I2).
- why it matters: an upstream product limit changes by default. The only on-camera datum is one 2 s 4K 60 fps lossless pre-roll with 0 skips (KB `dng-chain-answer.md:30`); lossless is CPU-tight (`:156`); no counted take at 50/60.
- rework: keep 30.0 as the default in `losslessMaximumFps`/`enforceLosslessCaptureLimits`; `APERTAR_LOSSLESS_FPS_LIMIT=<n>` raises it (within the mode maximum) for bench work (I9, N11). Delete `losslessImx585Fps`. Raise the default only after counted takes.
- effort S; deliberate: yes (commit `d44b177` "Lossless JPEG on the IMX585 is no longer capped at 30 fps"; comment `CC.cpp:3133-3134`).

### Camera-headers-F4 [removed-upstream-behaviour, major] FPS ceiling: the probe beats the hard-coded table by default
- where: `src/camera/FpsCeiling.hpp:12-19@cinemate-port`; `src/camera/CameraController.cpp:3397-3423@cinemate-port`
- port way: `resolveSensorMaxFps` returns the probed value when there is one; the table is a fallback; `APERTAR_FPS_LIMIT=table` restores `min(table, probed)`. 4K SDR rises from 30 to 60.
- Apertar way: hard-coded tables, `validate()` last word (N7); IMX585 3840x2160 = 30.0 (`CC.cpp:2669-2671@upstream-1.6.0`). Fork main `f60e301` added the probe as `min(table, probed)`: "SDR limits unchanged (the probe only lowers them)"; "Recording at 30 fps still loses ~20 %".
- why it matters: operators are offered rates not shown to record without drops; 4K 12-bit uncompressed at 60 fps (746 MB/s) does not fit the drive (KB `dng-chain-answer.md:156`). Fork-log:138: not run as takes.
- rework: keep main's `min(table, probed)` default; raise individual rows in `tableMaximumFpsForResolution` once takes prove them; probe-only as opt-in `APERTAR_FPS_LIMIT=probe`. The IMX283 floor rule stays.
- effort S; deliberate: yes (commit `d44b177` "Max fps: read from the sensor probe at startup (4K SDR 60 ...)").

### Camera-headers-F5 [mismatch, major] Mode ladder persists in its own mode_ladder.conf
- where: `src/camera/ModeLadder.hpp:316-342@cinemate-port`; `src/camera/CameraController.cpp:403-414`, `:10513-10514`, `:10939` (`saveModeLadderLocked`)@cinemate-port; `CameraController.hpp:248` (`modeLadder_`)
- port way: a second Core-written settings file `~/.config/apertar-core/mode_ladder.conf` (`enabled`, `ramp_ready`, `resolutions`, legacy `rungs`), own parser and writer, held in `modeLadder_` outside `CaptureSettings`.
- Apertar way: S20: camera settings in `camera_settings.conf`, key=value, written only by Core through the debounced persister (`CC.cpp:742-889@upstream-1.6.0`); camera-wide keys carried across format profiles (`tuning_file`, `CC.cpp:7939-7955@upstream-1.6.0`), a pattern the port already extends for `previewTdn`, `cdngLog`, `clipNameTemplate` (`CC.cpp:11338-11372@cinemate-port`).
- why it matters: a parallel persistence path the persister and the settings write do not cover; written synchronously under the controller mutex (KB `design/critique-code.md:273`).
- rework: camera-wide keys `mode_ladder_enabled`, `mode_ladder_ramp_ready`, `mode_ladder_resolutions` (the existing comma text) in the `else if (key == ...)` load chain (I15) and the writer; hold them in `CaptureSettings` like `tuningFile`, carried in the block at `CC.cpp:11338-11372`. On first start, read an existing `mode_ladder.conf` once to migrate (the owner's camera has one), then stop reading it. Delete `fileText`, `parseFile` after migration, `modeLadderPath`, `saveModeLadderLocked`, the `rungs` key.
- effort M; deliberate: yes (`ramp-ladder/design/design-T34.md:280-293` rejected UI.conf and per-format profile keys; camera-wide keys in `camera_settings.conf` were not weighed).

### Camera-headers-F6 [mismatch, minor] Rung::compression is a free string mixing record format and compression
- where: `src/camera/ModeLadder.hpp:22-44@cinemate-port`, `:160-166`
- port way: `std::string compression` = "" | none | lossless_jpeg | lossy_3to1 | lossy_5to1, compared as strings; lossy implies LossyDng.
- Apertar way: S13/I11: each sub-option is its own enum (`RecordingFormat`, `CdngCompression`, `LossyDngRatio`, `Types.hpp:45-68@upstream-1.6.0`) with `toString`/`toWireValue`.
- why it matters: string compares through the ladder code; wire words partly duplicate the existing `toString` values.
- rework: a small `enum class RungRecord { Default, Uncompressed, Lossless, Lossy3, Lossy5 }` or `std::optional<RecordingFormat>` + `CdngCompression` + `LossyDngRatio`, parsed from the existing wire words.
- effort S; deliberate: no.

### Camera-headers-F7 [mismatch, minor] Ladder setters and clip-name preview return errors and data through out-params instead of bool + lastError()
- where: `src/camera/CameraController.hpp:92`, `:102-109@cinemate-port` (`setModeLadder`, `applyLadderToPreset`, `setClipNameTemplate`); `CC.cpp:11856` (`previewClipName`)
- port way: `setModeLadder(optional<string>, optional<bool>, optional<bool>, bool dryRun, string *json, string *error)`; `applyLadderToPreset(..., string *error) const`; `previewClipName(value, string *example, string *error) const`; `setClipNameTemplate(value, string *stored)` (errors already via `setErrorLocked`, `CC.cpp:11835-11854`).
- Apertar way: S7/I1: `bool set...(value)`, errors via `setErrorLocked`/`lastError()` (`CC.hpp:85@upstream-1.6.0`); App replies `settingsBody(camera_.settings())`.
- why it matters: a second error channel and a second setter shape on the public surface.
- rework: `bool setModeLadder(const std::string &resolutions, bool enabled, bool rampReady)` + `bool validateModeLadder(...)` for the dry run; errors via `setErrorLocked` (several validation errors joined, the full list stays in `modeLadderJson()`, which already exists); App builds the reply from `camera_.modeLadderJson()`. Drop `*stored` (App reads `camera_.settings().clipNameTemplate`).
- rework risk: `applyLadderToPreset` and `previewClipName` are `const`; `lastError_` needs to be `mutable` or the functions non-const.
- effort S; deliberate: no.

### Camera-headers-F9 [mismatch, minor] Display text and redundant ladder fields in CaptureSettings
- where: `include/apertar/core/Types.hpp:181-189@cinemate-port`
- port way: nine runtime ladder fields in `CaptureSettings`, among them `ladderText` (a UTF-8 display line with "·", "×", "≤") and `ladderCount` (= `ladderTops.size()`), serialised in all three state writers.
- Apertar way: upstream `CaptureSettings` does carry runtime state (`whiteBalanceMeasured`, `previewExposureReference`, `timelapseExposureLimitUs`, `Types.hpp:139-150@upstream-1.6.0`), so numeric ladder state there is in pattern. Upstream Core sends no display sentences; clients build labels (I13: each field costs three serialiser edits).
- why it matters: Core composes non-ASCII UI text; one redundant field in three hand-kept lists.
- rework: drop `ladderText` and `ladderCount`; the WebUI builds the line from `ladder_rung`, `ladder_tops` and the `get_mode_ladder` reply (`WCP:8392`, `:8421`, `:15920` already have the data). Keep the other fields.
- effort S; deliberate: yes (`design-T34.md:336-345` 3.6 chose derived fields after `exposureCompensationAvailable`).

### Camera-headers-F10 [duplication, nit] Sensor tables: own Size types and two nearest-mode metrics
- where: `src/camera/Imx283Modes.hpp:19-22`, `:114-135@cinemate-port`; `src/camera/Imx585Modes.hpp:34-38`, `:236-252@cinemate-port`
- port way: `imx283::Size` and `imx585::Size` beside `Resolution`; nearest mode is squared Euclidean for IMX283, Manhattan for IMX585.
- Apertar way: sensor facts use `Resolution` from `Types.hpp` (`CC.cpp:355-396@upstream-1.6.0`). Pure helper headers are allowed (S4).
- why it matters: three size types and two distance rules for one job.
- rework: use `Resolution` in both headers; one distance rule. Keep `isImx585LegacyCropResolution` and the alias map (upstream shape, other sensors' compatibility).
- effort S; deliberate: no.

### Camera-headers-F11 [duplication, minor] Env-var parsing re-implemented three times
- where: `src/camera/Imx585Modes.hpp:105-114@cinemate-port`; `src/camera/FpsCeiling.hpp:29-38@cinemate-port`; `src/camera/CameraController.cpp:8909-8922@cinemate-port`
- port way: `minModeWidth()` calls getenv/strtoll on every `find`/`offered`/`nearest` through a default argument; `parseLosslessFpsLimit` uses strtod; the phase-lock tuning has its own lambda.
- Apertar way: `unsignedEnvValue(name, default, min, max)` and `boolEnvValue` (`CC.cpp:1027-1061@upstream-1.6.0`, port `:1341-1357`), read once in function-local statics (I9, I17).
- why it matters: three parsers with different rules for one convention; repeated getenv in lookup paths.
- rework: in CC.cpp `static const unsigned w = unsignedEnvValue("APERTAR_IMX585_MIN_MODE_WIDTH", 1280, 0, 65535);`, passed in as a parameter (no default argument reading the environment). Add `doubleEnvValue` beside the two helpers for the lossless limit and the phase-lock gains.
- effort S; deliberate: no.

### Camera-headers-F12 [slop, minor] Ticket numbers, Cinemate narration and a stale comment in code and in the user's config file
- where: `src/camera/ModeLadder.hpp:1`, `:319@cinemate-port`; `include/apertar/core/Types.hpp:141`, `:181-189` (9 x T31/T34); `src/camera/CameraController.hpp:102`, `:180`, `:243`, `:248` (4 x); `src/camera/CameraController.cpp:403`, `:8902`, `:8907-8908`, `:9063-9067@cinemate-port`; `src/camera/FramePhaseLock.hpp:9-26`, `:48@cinemate-port`; `src/camera/Imx283Modes.hpp:1-2`; `src/camera/Imx585Modes.hpp:3`, `:16`
- port way: `fileText` writes "# Apertar mode ladder (T34)." into the user's file; comments name the `cinemate-port` branches, "as Cinemate's libcamera does", "qbc libcamera", "CineMate Log". `Decision::pushDuration` says `{d, d}`; the controller pins `{d, d+1}` (`CC.cpp:9069`, and the header's own line 17). The overview comment sits above `PhaseLockStatus`, not `FramePhaseLock`.
- Apertar way: I19: comments rare, say why, no ticket numbers or history; upstream `src`/`include` mention neither Cinemate nor T-numbers.
- why it matters: internal numbers and another project's history for the original developer; one comment contradicts the code.
- rework: remove T-numbers everywhere, including the `fileText` string (moot if F5 lands). Replace Cinemate/branch references with the driver facts. Fix `{d, d}` to `{d, d+1}`; move the overview above `struct FramePhaseLock`.
- effort S; deliberate: no.

### Camera-headers-F13 [slop, minor] conformFps is persisted and settable but has no effect and no UI
- where: `include/apertar/core/Types.hpp:135-137@cinemate-port`; `src/camera/CameraController.cpp:172`, `:696-697`, `:817-818`, `:942`, `:11354`, `:11364`, `:11806-11812`; `src/ApertarCoreApp.cpp:320`, `:7851`, `:9484`, `:13270`, `:14356`; `src/web/WebControlPage.cpp:19111@cinemate-port`
- port way: "nothing derives from it yet"; `set_conform_fps`, state keys, preset key, persisted key; no reader in `src`, 0 hits in Apertar-UI.
- Apertar way: every upstream setting drives behaviour; no stored placeholder.
- why it matters: dead protocol and persistence surface.
- rework: remove the field, command, state keys, preset key and persisted key until a feature reads it.
- effort S; deliberate: yes (Types.hpp comment; commit `d7ff071`).

### Camera-headers-F14 [slop, nit] Compatibility for spellings that never shipped; CdngLog::Auto means On
- where: `include/apertar/core/Types.hpp:59-62`, `:326-346@cinemate-port`; `src/camera/ModeLadder.hpp:168`, `:337@cinemate-port`
- port way: "on", "12", "10", "8" map to `Auto`; the ladder accepts `log10`/`log8`; the file reads the old key `rungs`.
- Apertar way: I15 keeps retired keys users had. These spellings were never in an Apertar release (fork main has no `cdng_log`).
- why it matters: port-internal history in code; the enum name misleads.
- rework: `enum class CdngLog { Off, On }`, wire `off`/`on` (accept `auto` only if the owner's installed settings hold it). Drop `12/10/8`, `log10/log8`, `rungs`.
- effort S; deliberate: yes.

### Camera-headers-F15 [new-ground, minor] Host tests of this unit: three styles, no build hook; phase-lock simulator only in the KB
- where: `tools/fps_ceiling_test.cpp`, `tools/imx283_modes_test.cpp`, `tools/imx585_modes_test.cpp`, `tools/tuning_tdn_strip_test.cpp@cinemate-port` (4 of the port's 20 `tools/*_test.*`)
- port way: each test built by hand from a comment line, with `check()`, a `CHECK` macro or `expectStrip`. All four compile and pass here.
- Apertar way: no precedent (S24: no tests, no `tools/` upstream).
- why it matters: new infrastructure without a home or a build entry; the most delicate pure logic (`FramePhaseLock`) has its simulator in `apertar-kb/working/tools/phase_lock_sim.cpp`, not beside the header.
- rework: follow the port-wide test decision (one `tests/` folder, one check helper, opt-in `APERTARCORE_BUILD_TESTS` OFF, one README line). For this unit: bring the four into that style, move the phase-lock simulator in as a test, delete `tuning_tdn_strip_test` when F1 lands and `fps_ceiling_test` when F16 lands.
- effort S; deliberate: yes (header comments name their tests; fork-log records runs).

### Camera-headers-F16 [new-ground, nit] FpsCeiling.hpp splits one-line rules into a header for a test
- where: `src/camera/FpsCeiling.hpp:1-47@cinemate-port`
- port way: `namespace apertar::fpsceiling` with `resolveSensorMaxFps`, `applyBackendCap`, `parseLosslessFpsLimit`, `losslessImx585Fps`.
- Apertar way: S3/S4: most pure logic stays in CC.cpp next to its callers (`maximumSupportedFpsForResolution`, `CC.cpp:2629@upstream-1.6.0`).
- why it matters: after F3/F4/F11 the rules are `std::min` calls; a header is over-built.
- rework: fold the remainder into CC.cpp beside `maximumSupportedFpsForResolution`; delete the header and `fps_ceiling_test.cpp`.
- effort S; deliberate: yes.

Dropped: F8 (upstream precedent for arrays of objects in replies).
