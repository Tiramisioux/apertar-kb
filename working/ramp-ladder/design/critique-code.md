# Critique of plan-v1 (T34 mode ladder): code feasibility

2026-10-27, critic pass. Read-only on every tree. One host command was run: `g++ -fsyntax-only` of `CameraController.cpp` with
`-DAPERTARCORE_HAS_LIBCAMERA=0` (writes no files). Nothing else was built or run. Nothing ran on the Pi.

Trees (all citations are at these commits):

| Short name | Tree | Commit |
| --- | --- | --- |
| `CC`, `App`, `Web`, `Types`, `CP`, `GAI` | `scratchpad/tip-core` (`src/camera/CameraController.cpp`, `src/ApertarCoreApp.cpp`, `src/web/WebControlPage.cpp`, `include/apertar/core/Types.hpp`, `src/ipc/ControlProtocol.cpp`, `src/hardware/GroveAnalogInput.cpp`) | `119d0bb` (= `6ae70b5` + T31 `5f38585` + T32 `cba1963`, `119d0bb`) |
| `CB`, `QML`, `SP` | `scratchpad/verify2/home/ApertarUI` (`src/ApertarControlBridge.cpp`, `qml/CameraPage.qml`, `qml/SettingsPage.qml`) | `34499f1` |
| KB | `scratchpad/verify3` | `8b655da` |
| patches, research | `scratchpad/apertar-kb-speed-ramp-2026-10-27/kb/working/` | export, no git |

Labels: **CONFIRMED** = I opened the line. **PROBABLE** = derived; the derivation is given. **UNCONFIRMED** = only the Pi can say.

Spot check of the plan's own citations: 24 lines checked (gates `CC:9047-9050`, `:9526-9529`, `:9562-9565`; `CC:2784`;
`CC:10291`; `CC:10322-10337`; `CC:8947-8975`; `CC:10254`; `Web:2546`, `:5027`, `:8761-8846`, `:9291-9326`, `:11800`;
`App:9321`, `:9329`, `:9681`, `:4285`, `:6972`; `CB:1035-1052`; `QML:503`, `:808`, `:1214-1222`, `:1373-1376`, `:1557-1559`).
All match. The designer's facts F1-F15 hold. The problems below are about what the plan *does* with them.

---

## Verdict

| Plan section | Verdict | One line |
| --- | --- | --- |
| §0 Short answer | change | Recommendation stands. Sizes are about 1.5x low (Problem 1) |
| §1.1 Where it lives | keep | |
| §1.2 Mode Ladder card | change | Ramp-ready as one checkbox, not an fps select (Problem 11). Drop the JS copy of the rules (Problem 10) |
| §1.3 Validation | change | Core only, with a `dry_run` the WebUI renders (Problem 10) |
| §1.4 Touch UI | change | Must also disable five mode controls, not only show a tag (Problem 5) |
| §1.5 Picking an FPS | keep | Add: the touch screen freezes for the switch (Problem 5) |
| §1.6 Files on the card | change | Drop the `# mode=` header line (Problem 9) |
| §1.7 Refusals and notices | change | Drop the `notice` field (Problem 8) |
| §2.1 Facts | keep | All CONFIRMED again |
| §2.2 Design A | keep, with fixes | One reconfigure per change, never "apply then align" (Problem 3); pot (Problem 4) |
| §2.3 Design R | keep, simplify | Boolean (Problem 11) |
| §2.4 Design B | keep as deferred T35 | Replace the raw-pool item with the cached-heap item (Problem 6). B is 700-1,100 CC lines, none host-checkable |
| §2.5 Design B0 | drop | It is what Patrik does by hand with A. No code, no tutorial |
| §2.6-2.7 Comparison, recommendation | keep | A + R first is right |
| §3.1 Data model | change | Move structs and logic to a pure header (Problem 2) |
| §3.2 Chooser | keep | Goes into the pure header |
| §3.3 Storage | keep | `mode_ladder.conf` is right. UI.conf CONFIRMED wrong place (below) |
| §3.4 Build maximum | keep | Add: it also caps HD and the 3840 crops at 50 (Missing 5) |
| §3.5 Commands | change | `dry_run`; no `notice`; rung separator vs shell (Problem 13) |
| §3.6 State fields | change | `fps_max` must not shrink at record start for the pot (Problem 4) |
| §3.7 How the UIs learn | change | PCF pot (Problem 4) |
| §4 Part 1 (T33a) | keep | Honest size |
| §4 Part 2 (Core) | change | Problems 2, 3, 8, 9; add `setStillExposureMode` |
| §4 Part 3 (WebUI) | change | Problem 10 |
| §4 Part 4 (touch UI) | change | Problem 5; 4.6 is not "no change" |
| §4 Part 5 (B) | keep | Deferred |
| §5 Measurements | change | M1 and M3 need changes (Problems 7, 12); add M8 (Missing 2) |
| §6 Risks | change | Add pot remap, cached-heap fallback, back-end limit at 50 fps |

UI.conf locking (the brief asked): no problem for T34. The touch UI writes `camera/*` keys to UI.conf after each pick
(`CB:993-1024`) but only as placeholders ("Cached values are placeholders only. Core owns restart/format restoration",
`CB:906`); nothing reads them back into Core. Core opens and parses UI.conf on every `readSharedUiSettings()` call
(`App:1665-1672`). So keeping the ladder out of UI.conf, and out of the hot `setFps` path, is right. CONFIRMED.

---

## Problems

Ordered by consequence. Each has: what is wrong, evidence, consequence, fix.

### 1. The size is about 1.5x low, and most of the new Core code is in the file that cannot be compiled off the Pi

- **What:** §0 says T34 A + R is about 750 lines (Core ~330, WebUI ~380, touch UI ~40). Part 2 alone lists 22 Core items.
- **Evidence:** T31 had a similar breadth (setting, gate, policy, log, stepper, commands, three JSON writers) and added
  **367 lines to `CC`** and 101 to `App` (count of `+` lines per file in
  `working/patches/0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch`). T32's WebUI block (pills, two selects,
  no drag, no draft state) added 143 lines (`0001-web-speed-ramp-block-in-the-Recording-format-card.patch`). CONFIRMED counts.
- **My estimate for the plan's scope (PROBABLE, item count against those two patches):**

  | Part | Plan | Estimate | What the plan's number leaves out |
  | --- | --- | --- | --- |
  | T33a | ~150 | 120-180 | nothing |
  | Core (Types + CC + App) | ~330 | 600-750 (CC 450-600) | rung-text parser with error messages, nine validation rules, pool mapping and dedup, `mode_ladder` JSON, eight status fields in three writers, three handlers |
  | WebUI | ~380 | 420-550 | the JS copy of the validation rules, draft/dirty guard, three panel copies (3.6-3.8) |
  | Touch UI | ~40 | 100-150 | five mode controls to disable (Problem 5) |
  | **Total** | **~900** | **1,250-1,600** | |

- **Consequence:** Patrik types every line. A 1,500-line change is about three T32-sized tutorials. And 450-600 lines land in
  `CameraController.cpp`, which nobody can compile before the Pi (Problem 2). The first Pi build will fail more than once.
- **Fix:** state the honest size; apply the cuts in "Simplest version" (they bring it to about 1,000 lines, with about 200 in
  `CC`); ship as four tutorials: T33 (build max), T34a (Core + socket, tested with `core.py`), T34b (WebUI editor), T34c
  (touch UI). Each one builds and runs on its own.

### 2. No plan to reduce the compile risk in `CameraController.cpp`

- **What:** the plan says `CC` "cannot be compiled off the Pi" (§2.4, §2.6) and puts all ladder logic there anyway: parser,
  writer, validation, chooser, JSON (items 2.2, 2.4, 2.16, 2.17).
- **Evidence:**
  - The no-libcamera build switch exists (`CMakeLists.txt:17`, `:135-137`), but it is broken on the tip. `g++ -std=c++20
    -fsyntax-only -Isrc -Iinclude -DAPERTARCORE_HAS_LIBCAMERA=0 src/camera/CameraController.cpp` stops at `CC:6851`
    (`SensorFamily` not declared), `:6734`, `:8933`, `:8954`, `:8964`. CONFIRMED (run here, g++ 13.3). The sanitiser and the
    ceilings sit inside the `#if APERTARCORE_HAS_LIBCAMERA` block `CC:1057-5846`. CONFIRMED. So there is no partial host check.
  - The project already keeps pure logic in libcamera-free headers next to `CC`: `src/camera/FramePhaseLock.hpp` (included at
    `CC:1`), `ExposureMetering.hpp`, `StillBracketing.hpp`, `ScalerCropGeometry.hpp`, with host tests in the KB
    (`verify3/working/tools/phase_lock_sim.cpp`, `media_profile_test.cpp`). CONFIRMED.
- **Consequence:** every typo in about 500 new lines waits for a Pi build. Logic errors in the chooser (inclusive bounds,
  disabled rungs, "else the last rung") show up only as wrong reconfigures on the camera.
- **Fix:** new `src/camera/ModeLadder.hpp`, no libcamera: `LadderRung`, `ModeLadder`, `parseRungs`, `rungsText`,
  `validate(ladder, ceilings[], &errors, &warnings)`, `chooseRung(ladder, ceilings[], targetFps)`, `toJson`. `CC` computes
  `ceilings[i]` (it owns the sanitiser) and passes plain numbers in. Host test `working/tools/mode_ladder_test.cpp` in the
  style of `media_profile_test.cpp`. `CC` keeps only glue: file load/save, the `setFps` hook, refusals, status fill. About
  150-250 lines stay uncompiled instead of 450-600.

### 3. "Apply, then align" makes two camera restarts and a half-applied failure

- **What:** items 2.8 (`setFpsRamp`), 2.9 (`setRecordingFormat`), 2.10 (`applyCapturePreset`) and 2.11 (`start`) call
  `alignToLadderLocked()` after the function's own apply. If the rung differs, `switchRungLocked` reconfigures a second time.
- **Evidence:**
  - `setRecordingFormat` swaps in the whole saved profile and reconfigures when the size or bit depth differs:
    `return applySettingsLocked(next, requiresReconfigure);` `CC:9379`. CONFIRMED.
  - `applyCapturePreset` exists to "Apply the complete mode once" (`CC:10254-10255`). The App also uses it as a **rollback**:
    `camera_.applyCapturePreset(previous)` at `App:10103`, `:10131`, `:10522`, and for the start-up bracketing sync at
    `App:6991`. CONFIRMED.
  - `setFpsRamp` is a controls-only apply today: `return applySettingsLocked(next, false);` `CC:9746`. CONFIRMED.
  - A full restart is `stop()` + `start()` (`CC:6358-6370`). With a log cDNG preview profile, `start()` builds a second
    CameraManager and writes a derived tuning file (`CC:6222-6237`). CONFIRMED.
- **Consequence:**
  - A format switch cDNG → MLV whose profile holds another mode: two restarts, two preview blinks, up to four CameraManagers.
  - Two-phase failure: the first apply commits and persists; the align fails; recovery (commit = true, `CC:10322-10333`)
    puts back the first apply's state and returns false. The reply is `ok:false` while the format (or `fps_ramp`) **did**
    change. The WebUI then reverts its optimistic patch (`Web:9311-9314`) and shows the wrong state until the next poll.
  - A rollback through `applyCapturePreset(previous)` would align and can land in a mode that is not `previous`.
- **Fix:** one helper, `ladderRewriteLocked(CaptureSettings &next)`: if the ladder is active for `next`, set `next`'s
  resolution, bit depth, Clear HDR and FPS from `chooseRung`, and report "mode changed". Call it **before** the single
  `applySettingsLocked` in `setFps` (off-take), `setFpsRamp` (pass `requiresReconfigure = modeChanged`),
  `setRecordingFormat`, `setStillExposureMode` when leaving photo mode (`CC:9283-9294`, missing from 2.7-2.11), and in the
  App's `apply_preset` handler only (`App:10766`, `:11055`), never in the rollback calls. At boot, call it on `settings_`
  before `session_->start` (`CC:8956`): for Patrik's ladder the choice does not need the probe, because an fps above every
  table ceiling falls to "the last usable rung" (§3.2), which is rung 2 either way (PROBABLE from the chooser rule). Keep the
  post-start check only as a guard.

### 4. The PCF FPS pot jumps to another value at record start

- **What:** §3.6 makes `fps_max` drop from the ladder ceiling (50) to the running rung's ceiling (25) at record start.
  Item 1.12 cuts the pot's list at `fps_max`.
- **Evidence:** the pot rebuilds its list on every event and maps by position: `options = availablePcfFpsOptions(...)`,
  `index = analogPresetIndex(event.normalized, options.size())` (`App:8682-8690`), and
  `analogPresetIndex = llround(normalized * (count - 1))` (`App:8607-8613`). An event fires when the raw value moves by the
  deadband (`GAI:473`, default 32). CONFIRMED.
- **Consequence (PROBABLE, arithmetic):** off-take the list is {24, 25, 30, 50}; the knob at 25 sits near 0.33. In a rung 1
  take the list is {24, 25}; 0.33 now maps to index 0 = **24**. A nudge or a noisy read during the take sends `set_fps 24`:
  a T31 ramp step the operator did not ask for. The whole knob travel now covers 24-25. Today (no ladder) the list does not
  change at record start, so this is new.
- **Fix (pick one):** keep `fps_max` stable across a take (the ladder ceiling) and let Core clamp, as it already does
  (`CC:9101-9111`); or have the pot use the ladder ceiling while `fps_max` shrinks for the pickers. The first is simpler and
  also removes items 2.12/2.13's extra settings events.

### 5. Touch UI: five mode controls are left live, and a rung switch freezes the screen

- **What:** Part 4 handles one control (`applyResolutionValue`, 4.5) and says 4.6 needs no change.
- **Evidence:**
  - Mode changes in the touch UI: `QML:1217` (resolution), `QML:1242-1250` (quick resolution; "clearhdr" sends
    `applyClearHdr`, any other size first sends `applyClearHdr(false)`), `SP:636` (resolution), `SP:3179-3188` (Clear HDR in
    the resolution dropdown), `SP:3264` (`applyRawBitDepth`). CONFIRMED. With the ladder on, Core refuses each (2.7); four of
    the five show nothing.
  - `applyFps` is `Q_INVOKABLE` (`CBh:113`) and waits for the reply in a loop on the GUI thread (`CB:1084`). The picker
    ignores its return value (`QML:2926-2929`). CONFIRMED. A rung switch therefore freezes the touch UI for the whole
    reconfigure (UNCONFIRMED duration, M1), and a failed switch is silent.
  - After the reply, `applyFps` sets the display and the shutter from the **requested** FPS, not the accepted one:
    `setFps(formatFpsValue(fpsValue))` `CB:280`, `shutterUsForAngle(preservedAngleValue, fpsValue)` `CB:288`. CONFIRMED.
    Core can accept less (configure-time clamp `CC:7232-7237`).
- **Consequence:** Patrik taps "4K Clear HDR" on the touch screen with the ladder on and nothing happens, with no message.
- **Fix:** one `ladderActive` property gates `enabled` on those five controls, with a one-line caption ("Mode Ladder on: the
  FPS picks the mode"), like WebUI 3.6. Show `showRecordWarning` when `applyFps` returns false (pattern `QML:1515`). Take the
  accepted FPS from `fpsReply` for the display and the shutter. Budget 100-150 lines, not 40.

### 6. Memory: the plan lists a pool risk that the tip already fixed, and misses the silent heap fallback

- **What:** §2.4 lists "raw pool buffers too small after an up-switch (r1 Risks 14)". r1 read `d4ad539`.
- **Evidence:**
  - On the tip the pool is cleared at every configure: `recorder_.clearRawPool();` `CC:7294` ("The pool survives takes, so the
    camera session calls this when it is (re)configured", `CC:3975-3976`). There is no `reserveRawPool`. Patrik's switch goes
    to smaller frames anyway (16.9 MB Clear HDR 16-bit to 12.4 MB SDR 12-bit). CONFIRMED.
  - The real allocation risk: Clear HDR raw buffers come from `/dev/dma_heap/vidbuf_cached`, then `linux,cma`
    (`CC:7392-7413`, 8 x 16.9 MB, `CC:1063-1067`). If that fails, Core logs "cached DMA allocation unavailable; using
    libcamera buffers" (`CC:7414`) and carries on with uncached buffers, which the code itself calls too slow for Clear HDR
    (`CC:7297-7298`). CONFIRMED. Whether the heap fragments after many 135 MB free/allocate cycles is UNCONFIRMED; the KB
    has no CMA headroom figure (`verify3/working/compare-raw/b3-core-completion.md:86`, "UNKNOWN").
- **Consequence:** this hits **design A too**: every off-take switch back to rung 1 reallocates 135 MB. A pot sweep or a
  preview `ramp_fps` does it repeatedly. The failure is silent: Clear HDR takes then drop frames.
- **Fix:** replace the §2.4 item; add R13 to §6 and M8 to §5 (Missing 2). Optional code: count the fallback and show it in
  `get_state`.

### 7. Rung 2 at 50 fps may fail on the back end, not only on storage; M3 is too short to say

- **What:** F9/F10 and R1 treat 50 fps as a storage question. M3 predicts "At Gen 3: files=3000 missing=0".
- **Evidence:**
  - Back end per 4K frame: 13.4 ms idle, 34.6 ms start-to-done while recording 4K 16-bit (`research-30fps/q2-pipelining.md:125-127`).
    50 fps leaves 20 ms. CONFIRMED figures; their transfer to SDR 12-bit is PROBABLE (same pixel count, no byte swap).
  - SDR gets 4 raw buffers (+2 on exFAT) (`CC:1063`, `:1181-1188`): 80-120 ms of cushion at 50 fps. Clear HDR got 8 because
    two buffers were not enough (`CC:1064-1066`). CONFIRMED.
  - No 4K SDR take above 30 fps is in the KB. At Gen 3, 425 MB/s on a 77-81 % full drive dropped frames from 95-140 s
    (`verify3/lessons/hardware-log.md:380-386`). CONFIRMED.
- **Consequence:** a 60 s M3 on an empty drive can pass and still say nothing about a 3-minute take at 622 MB/s.
- **Fix:** M3 at 180 s; record drive fill (`df`), PCIe gen and `be_cycle.py` output; if `dropped_gap_estimate > 0` with a low
  queue, repeat with `APERTAR_RAW_CAMERA_BUFFERS=8` (`CC:1188`). Write the prediction as "unknown; storage-bound at Gen 2,
  possibly back-end-bound at Gen 3".

### 8. The `notice` field races with the stepper

- **What:** items 2.14/2.17/2.21 store a `lastNotice_` in the controller and read it back with `takeNotice()` after
  `set_fps`.
- **Evidence:** the stepper calls `camera_.setFps(...)` from its own thread (`App:9321`) without the command lock that
  `handleCommand` takes (`App:9532`). CONFIRMED. Two callers share one slot.
- **Consequence:** a notice set by a stepper step can be returned to an unrelated `set_fps` reply, or lost. Small, but it is
  new shared state in `CC` for a toast.
- **Fix:** drop it. The reply already carries the clamped `fps`, and the WebUI shows it. If a toast is wanted, the App
  handler can compare requested and accepted FPS after the call (no controller state, App-only).

### 9. The `# mode=` line in `fps-ramp.txt` appears only in takes that ramped

- **Evidence:** `writeFpsRampLog` returns before writing when no change happened: `if (events.empty()) return;` `CC:8424`.
  CONFIRMED. It is a session method (Item 2.15 would add session code, the area where T31 hit the `private:` compile error,
  ramp-answer §7).
- **Consequence:** "makes the take's rung visible without the journal" holds only for ramped takes. The DNG tags already
  carry bit depth and black level.
- **Fix:** drop 2.15.

### 10. The validation rules exist twice

- **What:** §1.3 "The WebUI runs the same rules on the draft".
- **Evidence:** R9 in the plan itself: four copies of the ceiling table drift (`App:1162-1165` still says 30 for 4K Clear HDR
  16-bit, while `CC:2781-2782` says 25). CONFIRMED.
- **Consequence:** about 70-100 JS lines and a fifth copy of mode knowledge (ceilings, Clear HDR sizes, lossless caps).
- **Fix:** `set_mode_ladder ... dry_run=true` returns `errors` and `warnings` without saving. The editor sends it (debounced)
  on each draft change and renders Core's text.

### 11. Ramp-ready as an FPS value is more state than the job needs

- **What:** `ramp_reach` (fps) with a select listing each rung's ceiling (§1.2, §3.3).
- **Consequence:** it must be re-validated whenever rungs or ceilings change (format, compression, `max_fps`), and it needs
  its own select, storage and checks.
- **Fix:** `ramp_ready=true|false`: "Speed Ramp takes start in the top rung". For Patrik's ladder that is the only useful
  value. The chooser becomes `target = ramp_ready && fps_ramp ? ladderCeiling : fps`.

### 12. M1 times the wrong switch and hides the biggest cost driver

- **Evidence:** M1 times HDR16 → SDR12 and SDR12 → HDR12; the step back to 16-bit (`set_raw_bit_depth value=16`) is not
  timed, but the ladder's way down is SDR12 → HDR16 in one apply. A log cDNG preview profile doubles the CameraManager build
  and writes a tuning file on every start (`CC:6222-6237`). The `core.py` reply returns when `configureAndStart` has queued
  requests, before the first frame. CONFIRMED (code); timings UNCONFIRMED.
- **Fix:** time all three commands; print `cdng_preview_color_profile` first; run once with Standard and once with Patrik's
  usual profile; treat M1 as a lower bound and M2 as the frame gap.

### 13. The rung text uses `;`, which the shell treats as "end of command"

- **Evidence:** `core.py` takes `key=value` from argv (`verify3/working/tools/core.py:6-8`). Typed unquoted,
  `core.py set_mode_ladder rungs=3840x2160:16:hdr:25:on;3840x2160:12:sdr::on` runs `3840x2160:12:sdr::on` as a second
  command. Core's own parser is fine with `;` inside a quoted string (`CP:62-115`). CONFIRMED.
- **Fix:** use `,` between rungs (plain in bash; `core.py` JSON-quotes strings, so Core reads it whole), or quote every
  example in the tutorial.

---

## Missing

| # | What | Why it matters | Label |
| --- | --- | --- | --- |
| 1 | A host test for the chooser and parser (Problem 2) | Only way to test the ladder's logic before the Pi | CONFIRMED pattern exists |
| 2 | **M8, soak:** 30 alternating rung switches in preview, then `journalctl ... | grep -c 'cached DMA allocation unavailable'` and `grep -i cma /proc/meminfo` before and after; then a 30 s Clear HDR 16-bit take, check `missing=` | Problem 6; the fallback is silent | UNCONFIRMED risk |
| 3 | Re-align when leaving photo mode (`setStillExposureMode`, `CC:9283-9294`) | A ladder saved while in photo mode is not applied until the next FPS pick | CONFIRMED gap |
| 4 | Probe-off pool. `sensorModes()` returns the probe list (`CC:10191-10195`), empty with `APERTAR_SENSOR_PROBE=0` | "Add a mode" is empty; fall back to Core's own IMX585 list (`validateResolution`, `CC:10381-10399`) | CONFIRMED |
| 5 | `max_fps=50` also caps 1080p, the 1920 and 3840 crops (60 today, `CC:2786-2790`) and H.264 at 50 | Patrik loses 60 fps everywhere on this build; say it in T33 | CONFIRMED consequence |
| 6 | Tutorial numbers. T32 tutorial line 560 calls the ladder T33; the brief calls it T34 and the value lists T33; the plan adds "T33a" | Fix before writing; Patrik files by number | CONFIRMED |
| 7 | PCF resolution pot with the ladder on: every pot event logs "Hardware input action failed" (`App:8631-8639`, `:8692-8700`) | Skip the dispatch in the App when `ladderActive` (two lines) | CONFIRMED path |
| 8 | Where `mode_ladder.conf` is written: `atomicWrite` fsyncs the file and the directory (`src/util/SettingsFile.hpp:36-58`) under the controller mutex | Rare, but blocks every camera call for an SD-card fsync; copy the text, unlock, then write | CONFIRMED, minor |
| 9 | A touch-UI path to turn the ladder off | If Patrik is away from the WebUI, every mode control is greyed with no way out on the camera | design gap |

---

## Simplest version that still does what Patrik asked

What Patrik asked, and what this version gives:

| Ask | Delivered | Not delivered |
| --- | --- | --- |
| 1. Lowest → 50, switching mode at thresholds, same resolution | Thresholds switch the mode between takes; a Speed Ramp take runs lowest → 50 in one mode (ramp-ready) | A class switch inside a take (that is B, T35) |
| 2. His ladder, 50 from the build settings | `max_fps=50`, two rungs | |
| 3. Drag-and-drop editor, optional thresholds, toggle | Yes, in the WebUI | No editor on the touch screen |
| 4. Ramping during takes | T31, unchanged | |
| 5. Value lists | Separate tutorial (unchanged plan) | |

Steps, in build order:

1. **T33 (build max).** Plan Part 1 as written, with one change: `fps_max` = the ladder ceiling while the ladder is active,
   in and out of takes (Problem 4); Core clamps in a take as it does today. About 150 lines.
2. **Measure before T34:** M3 (180 s, drive fill, `be_cycle.py`) and M1 (all three transitions, real preview profile). If M3
   fails at Gen 3, rung 2's top is what holds; the design does not change.
3. **T34a (Core).** `src/camera/ModeLadder.hpp` (pure) + host test. In `CC`: load/save `mode_ladder.conf`; one
   `ladderRewriteLocked(next)` used before the single apply in `setFps` (off-take), `setFpsRamp`, `setRecordingFormat`,
   `setStillExposureMode` (leaving photo) and the App's `apply_preset`; refuse `set_resolution`, `set_raw_bit_depth`,
   `set_clear_hdr` while active; `ramp_ready` boolean; status fields `ladder_active`, `ladder_rung`, `ladder_rungs` in the
   three writers; commands `get_mode_ladder`, `set_mode_ladder` (with `dry_run`), `set_mode_ladder_enabled`. No `notice`, no
   ramp-log header, no B0. About 450 lines, of which about 200 in `CC`. Test with `core.py` only.
4. **T34b (WebUI).** The card: toggle, rows (handle, label, threshold, enabled, Up/Down/Remove), add select, ramp-ready
   checkbox, Save/Revert, pointer-event drag with the draft guard; render Core's `dry_run` text; disable the mode controls
   (3.6). About 300-350 lines. Test with `node --check` and the mocked Chromium run, as T32.
5. **T34c (touch UI).** `fpsMax`, `ladderActive`, `ladderRung`; gate the five mode controls; rung tag; `set_fps` in the 10 s
   class; warning on a failed pick; accepted FPS for display and shutter. About 100-120 lines.
6. **After the build:** M7 and M8 (soak).

Total about 1,000-1,100 lines in four tutorials, about 200 of them uncompiled until the Pi (PROBABLE estimate, same method
as Problem 1).
