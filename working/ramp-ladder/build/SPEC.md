# T33 + T34 implementation spec (cloud, 2026-10-28)

This spec is the contract between the Core, WebUI and touch UI work. Where it differs from
`../ladder-design/design-T34.md`, **this spec wins**. It records the layout decisions Patrik made in the mockup after the
design was written.

`S` = `/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad`.

## 0. Trees, files, checks

| What | Where |
| --- | --- |
| Core work tree | `S/t34/core`: detached HEAD `be6775d` = GitHub `cinemate-port` `3c4f07d` + T31 + T32 patches (post-audit). Same content as the design's `119d0bb`, except a 16-line audit fix in `ApertarCoreApp.cpp`; the design's line numbers are close, so search for its strings |
| Touch UI work tree | `S/t34/ui`: detached HEAD `9a6fc7d` = Apertar-UI `dc471c1` + the two T32 UI patches (the design's `34499f1` plus a small audit fix) |
| Design (code sites, search strings, semantics) | `S/ladder-design/design-T34.md`: §3 (data, commands, state, refusals), §4 (file-by-file plan, code for `ladderStatesLocked`, `ladderRewriteLocked` and the `setFps` lines) |
| Approved mockups | `S/ladder-mock/project/Main.dc.html` (WebUI Settings > Record: Mode Ladder, Speed Ramp, Activated sensor modes) and `Quick.dc.html` (WebUI Camera settings card). A small template language: `{{ x }}` bindings, `<sc-for>`, `<sc-if>`; behaviour is in the `Component` class (`renderVals`, `legal`, `normalize`, `spans`, `setThrAt`, `cropOf`, `sizeMB`). Live: https://claude.ai/artifact/YKbhhk8aMUS8sxEWa6UfRL |
| Pure ladder logic (**done, tested**) | `S/t34/core/src/camera/ModeLadder.hpp`; test `S/t34/mode_ladder_test.cpp` (52 checks). Build: `g++ -std=c++20 -Wall -Wextra -Werror -IS/t34/core/src S/t34/mode_ladder_test.cpp -o /tmp/mlt && /tmp/mlt`. Its API and JSON are the protocol. You may add small helpers; do not change existing names or JSON keys. If something is wrong in it, fix it, add a test, and say so in your report |
| Core host check | `S/t34/hostcheck-core.sh [tree]`: `g++ -fsyntax-only -Wall -Wextra` of `CameraController.cpp`, `ApertarCoreApp.cpp`, `WebControlPage.cpp` **with libcamera headers** (generated from libcamera-apertar `6b0b49f3`). It must report `errors=0 warnings=0`. This is new: `CameraController.cpp` can now be compiled here |
| WebUI script check | Extract the page between `R"APERTAR(` and `)APERTAR"` in `src/web/WebControlPage.cpp`, take the inline `<script>` text and run `node --check` on it |
| WebUI drive | `S/webtest/server.js` is the T32 mock of `/`, `/api/state`, `/api/command` (port 8765, serves `page.html`). Copy it to `S/t34/webtest/` and extend it; Playwright + Chromium are installed (`require('playwright')`, `chromium.launch()`) |
| Touch UI build | `ninja -C S/t34/ui-build` (configured with Qt 6.4.2 on `S/t34/ui`) |

Rules for everyone:
- Match the surrounding code: naming, comment density (short comments, only where the code does not say it), idioms. No
  drive-by refactors.
- Do not `git commit`, `git push` or touch any other repository, unless your task says to commit.
- Patrik's style for user-facing text: short, plain sentences; "resolution", never "rung", in anything a user reads;
  "Clear HDR" in names ("4K Clear HDR 16-bit") and **"ClearHDR"** in the compact class tag ("ClearHDR16", "SDR12").
- No illegal values: a UI never sends something Core would refuse when the UI can know it in advance.

## 1. What changed since design-T34.md

1. **No Ramp-ready (design R is dropped).** Remove everything about `ramp_ready` / `ladder_ramp_ready` / "RAMP": the chooser
   target is always the requested FPS. `setFpsRamp` needs no ladder rewrite. `mode_ladder.conf` no longer writes
   `ramp_ready`; an old file's key is ignored.
2. **Compression per resolution.** A rung = sensor mode + compression + optional "Up to (fps)". Compression keys are the WebUI
   Compression select's values: `none` (cDNG uncompressed), `lossless_jpeg` (cDNG lossless JPEG), `lossy_3to1`,
   `lossy_5to1` (`RecordingFormat::LossyDng`, `LossyDngRatio::R3`/`R5`). cDNG and lossy DNG share one settings profile
   (`settingsProfileFormat`), so switching between them inside the ladder keeps ISO, shutter, WB. In **MLV** (always
   uncompressed) the ladder still works, but the compression of each resolution is ignored (`compression_applies:false`).
   Lossy DNG cannot record Clear HDR (`unsupportedRecordingSettings`), lossless JPEG on IMX585 is capped at 30 fps and ISO 800
   (`enforceLosslessCaptureLimits`), and both compressions need Pi 5-class hardware.
3. **"Resolution N"** everywhere a user reads it; numbered 1, 2, 3 down the list, always sequential.
4. **Running line**, the same text on every screen: `Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed`
   (`ladder::runningText`). Crop-in modes add ` crop in` after the size; non-16:9 modes add the aspect after the class
   (`SDR12 2.39:1`). In MLV the last part is `MLV`.
5. **Validation is strict** (errors refuse a save): empty, more than 8, a repeated mode, not a mode of this sensor, a
   resolution that cannot record in its compression, "Up to" above the mode's ceiling, "Up to" not above the resolutions
   above, a resolution that would never be used. Warnings: the look changes between two resolutions (`Above 25 fps: Clear HDR
   16-bit → SDR 12-bit. ...`) plus Core's format notes (§2.6).
6. **Crop diagrams** come from the sensor probe's crop rectangles (`SensorMode::crop`, libcamera `ScalerCropMaximum`, text
   `(x, y)/WxH`), not from guesses. "CROP IN" is shown only when the window is narrower than the readout area.
7. **Speed Ramp in the WebUI is one switch**, "Allow speed ramping" (`set_fps_ramp`), explained as FPS change during
   recording. The T32 block's Shutter Sync, Ramp to, Over and the ×2/Ramp/Return actions leave the WebUI (Core's
   `ramp_fps` command stays).
8. **Activate ladder** is a switch that takes effect at once (`set_mode_ladder enabled=...`); the list of resolutions is
   a draft saved with **Save ladder** (`set_mode_ladder rungs=...`).

## 2. Core

### 2.1 T33 (separate commit, before T34): the build maximum

As design §4 Part 0, rows 0.1-0.13, with these decisions:
- `apertar-hardware.conf` gets a `[camera]` block in `defaultHardwareConfigTemplate()`:
  ```
  [camera]
  # Highest FPS this build records, in every mode and format (H.264 too). Empty or 0: no build limit.
  max_fps=
  ```
  `cameraMaxFpsFromHardwareConfig()` reads the first existing candidate file like `loadCfeHatConfig()` does; accepts a
  number 0 < v ≤ 280 (decimals allowed, inline `#` comment stripped); anything else = 0 (no limit).
- `CameraController::setBuildMaximumFps(double)` stores it (`std::atomic<double>` next to the probe globals) and, outside a
  take, re-sanitises the current settings once (lower FPS if needed; never a reconfigure just for this unless the sanitiser
  changes the mode). Applied before `camera_.start(...)` and after a successful Config save of the hardware file.
- `maximumSupportedFpsForResolution()` returns `min(…, buildMax)` when buildMax > 0. Also apply the build maximum in
  `sanitizeSettingsForSensor` for `SensorFamily::Unknown` (simulate) so `--simulate` shows it, and to H.264.
- IMX585 4K SDR: `sensorLimitKnown ? 60.0 : 30.0` (the probe's real maximum then wins through the existing `min`). Clear HDR
  unchanged (16-bit 25, 12-bit 30 with the probe).
- New derived field `CaptureSettings::fpsMax` (not persisted): the highest FPS `set_fps` accepts **outside a take** = the
  sanitiser's ceiling for the current settings at 280 requested. (T34 changes it to the ladder ceiling while the ladder is
  active.) Filled in `settings()` and `emitSettingsEventLocked()`; written as `"fps_max"` by all three JSON writers
  (`settingsEvent` in CC, `settingsBody` and `buildWebStateJson` in App).
- PCF / `fps_up` / `fps_down` list: `maximumPcfFpsForSettings` uses `settings.fpsMax` when > 0.
- WebUI (same commit): `maximumSupportedFpsForSnapshot` uses `snapshot.fps_max` when > 0; replies merge `fps_max` and
  `clear_hdr` into the snapshot (design 0.12).
- Commit message: `camera: build maximum FPS from apertar-hardware.conf, 4K SDR up to the sensor probe`.

Touch UI T33 (separate UI commit): `fpsMax` property in the bridge (parsed from `fps_max` in `applyCoreState` and the settings
event), and the FPS picker's maximum uses it when > 0 (design 0.13). Commit: `ui: FPS list stops at Core's fps_max`.

### 2.2 T34 data and file

- `CameraController` owns `ladder::Ladder modeLadder_` (under `mutex_`), loaded in the constructor from
  `~/.config/apertar-core/mode_ladder.conf` (`modeLadderPath()`: same XDG rule as `persistedSettingsPath()`), written with
  `settingsFile::atomicWrite` after a successful `setModeLadder`.
- `#include "camera/ModeLadder.hpp"` in `CameraController.hpp`.

### 2.3 Rung states (`ladderStatesLocked(base, ownCompression)`)

For each rung build a probe from `base` (current settings): `photoModeEnabled=false`, the rung's resolution, bit depth and
Clear HDR, `fps=280`, and, **when `ownCompression` is true or the base format is cDNG or lossy DNG**, the rung's compression
(`applyCompression`: none → Cdng+Uncompressed; lossless_jpeg → Cdng+LosslessJpeg; lossy_3to1/5to1 → LossyDng+R3/R5). When
`ownCompression` is false and the base is MLV, the format stays MLV. Then:
- `valid` = the sanitiser keeps the mode (resolution, bits, Clear HDR) in uncompressed cDNG.
- `usable` = valid, the sanitiser keeps mode **and** format/compression, and `unsupportedRecordingSettings(probe)` is null.
  `reason` = that message, or "not a mode of this sensor" style text when not valid.
- `modeCeiling` = the sanitised FPS.
- `crop`, `binning` = from the probed `SensorMode` that matches the rung (Core identity: 3840x2200 16-bit Clear HDR is
  3840x2160; use the existing alias helpers), crop parsed with `ladder::parseCrop`.

`ownCompression=true` is used for validation and the pool (independent of the current format). Runtime choices use
`ownCompression=false` with the current settings, so in MLV the ceilings are MLV's.

Sensor family: `(!simulateCamera_ && session_) ? session_->sensorFamily() : SensorFamily::Unknown` as in the design.

### 2.4 Active, running, rewrite

- Active = `modeLadder_.enabled && !base.photoModeEnabled && base.recordingFormat ∈ {Cdng, LossyDng, Mlv}` and at least one
  usable rung (runtime states).
- `compressionApplies` = base format is Cdng or LossyDng.
- Running rung = `ladder::findRung(modeLadder_, <rung built from settings_>, compressionApplies)`; −1 = off the ladder.
- `ladderRewriteLocked(next)`: never in a take; when active, choose `chooseRung(…, next.fps)`, then put the rung's mode **and,
  when compressionApplies, its compression** into `next`, and `next.fps = min(next.fps, rungCeiling)`. Returns true when the
  mode changed (a reconfigure is needed). A compression-only change needs no reconfigure (as `setCdngCompression`,
  `setRecordingFormat` between cDNG and lossy DNG).
- Apply the rewrite before the single apply in: `setFps` (design A9, with the in-take cap), `setRecordingFormat`,
  `setStillExposureMode` when leaving photo mode, `setModeLadder` (enabled or rungs changed, not in a take: move onto the
  ladder at once), `setBuildMaximumFps`, and a logged guard at `start` (a hand-edited file).
- In a take, nothing is chosen. `set_fps` and every ramp path (`ramp_fps` targets and the T31 stepper) are capped at the
  running rung's ceiling (its "Up to"); the stepper logs
  `fps ramp stopped: 25 fps is the ceiling of resolution 1 (4K Clear HDR 16-bit) in a take`.

### 2.5 Commands (App)

| Command | Fields | Reply |
| --- | --- | --- |
| `get_mode_ladder` | none | ok, `"mode_ladder":{…}` (`ladder::toJson`) |
| `set_mode_ladder` | `rungs` (string), `enabled` (`"true"`/`"false"`), `dry_run` (`"true"`): any subset | dry run: ok with `mode_ladder` holding the parsed draft's `errors`/`warnings`, never saved, allowed in a take. Save: refused in a take (`Stop recording before changing the Mode Ladder.`); refused with the errors joined by a space when `errors` is not empty (reply still carries `mode_ladder` when the App's error reply format allows extra fields; otherwise the WebUI uses `dry_run` first); ok with `mode_ladder` and the `settingsBody` fields (the camera may have moved to another resolution) |
| `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` | unchanged | refused while the ladder is active: `The Mode Ladder picks the resolution from the FPS. Turn it off in Settings > Record > Mode Ladder to choose by hand.` |
| `set_cdng_compression`, `set_lossy_dng_ratio` | unchanged | refused while active and the format is cDNG or lossy DNG: `The Mode Ladder sets the compression of each resolution. Turn it off in Settings > Record > Mode Ladder to choose by hand.` |
| `set_record_format` | unchanged | allowed; picking cDNG or lossy DNG while active lands on the chosen resolution's compression |
| `apply_preset` | unchanged | design A17/Q10: when active and the preset names a mode that the ladder would not run at the preset's FPS, refuse (`This Favorite records <label> at <fps> fps; the Mode Ladder runs <fps> fps in <label>. Turn the ladder off to load it, or save the Favorite again.`); otherwise the ladder rewrites mode and compression |
| `help` | | lists `get_mode_ladder`, `set_mode_ladder` |

Strings and booleans only in the command fields (as the T31 handlers). Hardware inputs (resolution pot, resolution step) do
nothing while the ladder is active, without the "Hardware input action failed" message (design A16).

`mode_ladder` JSON = `ladder::toJson(Reply)`. Fill `Reply` as: `states` runtime; `active`; `running`; `runningText`
(below); `format` = the key `set_record_format` uses for the current format; `compressionApplies`; `buildMax`; `area` =
`ladder::sensorArea` over all probed crops; `pool` = probed modes mapped to Core identity, deduplicated, sorted (Clear HDR
first, then 4K, crops by height descending, then binned; 16, 12, 10 bits), each with `ceilings`/`reasons` for the four
compressions (`ownCompression` states) and `valid`; `errors`/`warnings` = `ladder::validate` on `ownCompression` states plus
Core's notes (§2.6). With the probe off the pool is empty.

### 2.6 Core's extra warnings (appended to `warnings`)

- In MLV: `MLV records uncompressed: each resolution's compression applies in cDNG and lossy DNG.`
- Any lossless_jpeg resolution on IMX585: `Lossless JPEG caps ISO at 800 on this sensor.`
- A resolution not usable in the current format (runtime state) although valid in its compression:
  `Resolution 2 is skipped in <format>: <reason>`.
- A manual tuning file and a Clear HDR change between resolutions: `A manual tuning file is set; it is used for both
  Clear HDR and SDR.`

### 2.7 State fields (derived, never persisted; all three writers; touch UI event included)

| Field | Meaning |
| --- | --- |
| `fps_max` (T33) | highest FPS `set_fps` accepts outside a take: ladder active → ladder ceiling; else the mode's ceiling |
| `fps_take_max` | highest FPS a take reaches in the current mode: on a resolution → its ceiling; else the mode's ceiling |
| `ladder_enabled` | the Activate ladder switch |
| `ladder_active` | §2.4 |
| `ladder_rung` | 1-based running resolution, 0 = off the ladder |
| `ladder_count` | number of resolutions in the saved ladder |
| `ladder_text` | `runningText` of the running resolution when active and on a resolution; `"Mode Ladder on · the next FPS pick chooses the resolution"` when active and off the ladder; `""` otherwise |
| `ladder_tops` | array: each resolution's runtime ceiling in list order (0 = skipped) when active, `[]` otherwise. The WebUI's FPS pills use it: an FPS belongs to the first resolution whose top ≥ FPS − 0.0005 |

Add them to `CaptureSettings` as derived members next to `fpsMax` (`fpsTakeMax`, `ladderEnabled`, `ladderActive`,
`ladderRung`, `ladderCount`, `ladderText`, `ladderTops` as `std::vector<double>`), filled by `fillLadderFieldsLocked(out)`.

## 3. WebUI (`src/web/WebControlPage.cpp`, T34 part)

Build exactly what the two mockups show, with the page's own classes (`settings-card`, `settings-card-head`,
`settings-card-title`, `settings-card-copy`, `online-pill`, `pill-grid`, `settings-select`, `field-stack`, `input-label`)
and colours (`:root` tokens). New CSS goes next to the related rules, one small block; rows wrap at phone width (390 px,
no horizontal scroll).

**Settings > Record panel**, after the Recording format card, in this order:

1. **Mode Ladder card** (Main.dc.html section `ladderTitle`):
   - head: title "Mode Ladder", copy "Switches resolution automatically when you change FPS. Each resolution runs up to its
     FPS limit, then the next one takes over.", status pill (`On · 2 resolutions` / `Off`).
   - "Activate ladder" row with a switch (`role="switch"`, `aria-checked`), sends `set_mode_ladder enabled=true|false`
     at once; disabled with a note while recording or when no resolution is saved.
   - "Running now" box: caps label, bold line = `ladder_text` (ladder off: `3840×2160 · ClearHDR16 · Uncompressed (ladder
     off)` built from the snapshot), note "Same line on the camera screen (FORMAT) and next to Frame rate in Camera
     settings.", crop graphic 160×98 on the right, no caption.
   - "During a take" note (mockup text).
   - "Resolutions, first one first" list: one row per resolution: drag handle, numbered badge (one colour for all, #4ade80),
     crop diagram 78×48, name, meta (`3840×2160 · 16:9 · 16-bit · Clear HDR`), crop description, range text
     (`Lowest FPS up to 25 fps` / `Above 25 up to 50 fps`), problem text in red; on the right "Up to (fps)" number input
     (placeholder = ceiling, min = from+1, max = ceiling, "Ceiling N (why)" under it) and the Compression select (the four
     options; lossy options disabled with "(not for Clear HDR)" for Clear HDR modes) with its note, "≈ N MB per frame" and
     "≈ N MB/s at N fps"; up/down/remove buttons (44 px). Between rows the transition line (`Above 25 fps: …`).
   - Draft line + Revert + **Save ladder** (disabled while clean or while Core's dry run reports errors).
   - FPS coverage bar 1 … build maximum (`build_max`, else the ladder ceiling), segments numbered, ticks, gap text, caption
     `Build maximum 50 fps · apertar-hardware.conf, [camera] max_fps`.
2. **Speed Ramp card**: title, copy "Change the frame rate during recording. The clip keeps the rate it started at, so the
   faster parts play back as slow motion.", switch "Allow speed ramping" → `set_fps_ramp enabled=true|false` (keep the
   current `keep_exposure`). Disabled with a short note in H.264, ProRes and photo mode, and while recording if Core refuses
   (Core's error as a toast). Remove the T32 Speed Ramp block from the Recording format card (markup, CSS, JS, listeners,
   state keys) except what the Camera settings card still uses.
3. **Activated sensor modes card**: copy "From the sensor probe at start: N modes on this <SENSOR>. Add the ones you want on
   the ladder. Ceilings are Core's, capped at the build maximum."; filters (group: All, Clear HDR, 4K, Crop, 2K; bit depth:
   All, 16, 12, 10); grid of pool entries with crop diagram, name, meta (`… · up to N fps · crop in · N MB/frame`) and an Add
   button (disabled with a reason when already in the ladder, at 8, or invalid). Probe off: "Sensor probe off: add modes
   with core.py (set_mode_ladder rungs=…)."

Names (as the mockup): `4K Clear HDR 16-bit`, `4K SDR 12-bit`, crops `2.39:1, 12-bit`, `2K binned 12-bit`, `2K 2.39:1,
12-bit` (3840 wide = crop family; 1920 wide = 2K; aspect from width/height to two decimals; 16:9 = `4K`/`2K binned`).

Crop diagram (Cinemate `cropDiagram` look): frame border `1px solid #8a8a8a`, background `#131210`; window `2px solid
#90ee90`, fill `rgba(120,220,150,.13)` (`.08` when it is the whole area), placed from `crop` relative to `sensor_area`
(fallback when `crop` is null: centred, size × binning, or the size as is); tag `CROP IN` (amber `#fbbf24`, top left) only
when `crop_in`. No aspect-ratio text inside the graphic.

File size: MB per frame = width × height × bits / 8 / 1e6 × (none 1, lossless ≈ 0.6, lossy 1/3, 1/5); "≈" for the
estimates; MB/s at the resolution's top FPS. If the snapshot carries a measured media write speed (look for it; the media
speed test exists), colour the MB/s amber and add `above N MB/s (card)` when higher; otherwise no storage claim.

Legal values: the editor normalises and checks as the mockup's `normalize`/`legal`/`setThrAt` do (clamp "Up to" into
[from+1, ceiling]; equal to the ceiling = empty), using the pool's `ceilings[compression]` (min with `build_max`), and
refuses a change that would make the ladder illegal (notice line, red). It also asks Core (`set_mode_ladder dry_run=true
rungs=…`, debounced ~300 ms) and shows Core's `errors` and `warnings`.

Redraw rule (design §4 Part B): rows are rebuilt only after `get_mode_ladder` returns, after Save/Revert and after a local
edit; the 1 s poll never rebuilds rows (typing in a threshold keeps focus). Fetch `get_mode_ladder` when the Record panel
opens and after a save. Drag and drop with pointer events (`setPointerCapture`, `pointercancel`), keyboard-free arrows too.

**Camera settings card** (Quick.dc.html):
- head: pill `Resolution ladder on` (green) when `ladder_active`.
- Frame rate topline right: `ladder_text`; while a `set_fps` that changes the resolution is in flight:
  `Switching to Resolution N…` (amber).
- FPS pills: when `ladder_active`, a second line `Resolution k` from `ladder_tops`; pills in another resolution than the
  running one get a dashed amber border; the pill maximum is `recording ? fps_take_max : fps_max`. After a reply whose `fps`
  is below the requested one, a toast `Resolution 1 (ClearHDR16) stops at 25 fps in a take.`
- Resolution section stays last, with the Apertar labels (`4K Clear HDR`, `4K`, …); when `ladder_active` the note
  `Resolution ladder on: set by the frame rate` and the pills disabled (running one highlighted, others dimmed). Same for
  the Crop mode block.

**Recording format card**: Resolution and Crop selects, Bit Depth pills and the Compression select are disabled while
`ladder_active` (compression only in cDNG/lossy DNG), with one line `Mode Ladder on: the FPS picks the resolution and
compression.`

State merge: `fps_max`, `fps_take_max`, `ladder_*` from `/api/state` and from command replies (as T32 merges
`fps_ramp_keep_exposure`).

## 4. Touch UI (`S/t34/ui`, T34 part)

Design §4 Part C, minus Ramp-ready, with these fields: bridge properties `fpsTakeMax`, `ladderEnabled`, `ladderActive`,
`ladderRung`, `ladderCount`, `ladderText` (one `ladderChanged` signal), parsed from state and the settings event.
- FORMAT line on the camera screen (`formatDisplaySubtext`): `ladderText` when non-empty.
- FPS picker maximum: `recording ? fpsTakeMax : fpsMax`.
- Resolution, bit depth and Clear HDR controls (camera page and settings page): disabled while `ladderActive`, with the
  caption `Mode Ladder on: the FPS picks the resolution.`; the apply functions guard and show the warning.
- Settings page: one row "Mode Ladder" On/Off (`Q_INVOKABLE applyModeLadderEnabled(bool)` → `set_mode_ladder
  enabled=…`); disabled with `Set up the ladder in the WebUI (Settings > Record > Mode Ladder).` when `ladderCount` is 0.
- `set_fps` and `set_mode_ladder` join the 10 s reply-timeout list (both may reconfigure).
- `applyFps`: show the accepted FPS from the reply; on refusal `showRecordWarning("FPS Not Changed", lastError, …)`.
- Commit: `ui: Mode Ladder, its line on the FORMAT row, mode controls follow the ladder`.

## 5. Not in this work

Value lists (T35), design B (switching inside a take), Ramp-ready.
