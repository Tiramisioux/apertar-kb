# Critique of plan-v1 (T34 mode ladder): operator and post-production lens

2026-10-27, cloud session, critic pass. Read-only on every tree. Nothing built, nothing run on the Pi.

Trees I opened for this critique (every `path:line` below is at these commits):

| Short name | Tree | Commit |
| --- | --- | --- |
| `CC`, `App`, `Web`, `RC` | Core `scratchpad/tip-core`: `src/camera/CameraController.cpp`, `src/ApertarCoreApp.cpp`, `src/web/WebControlPage.cpp`, `include/apertar/core/RecordingCapabilities.hpp` | `119d0bb` (= `3c4f07d` + T31 + T32) |
| `GAI` | `src/hardware/GroveAnalogInput.cpp` | same |
| `QML`, `SP`, `CB` | Apertar-UI `scratchpad/verify2/home/ApertarUI`: `qml/CameraPage.qml`, `qml/SettingsPage.qml`, `src/ApertarControlBridge.cpp` | `34499f1` |
| cinemate | cinemate repository (`d6cc93e`) | `d6cc93e` |
| `HL` | KB `scratchpad/verify3/lessons/hardware-log.md` | `8b655da` |
| KB export | `scratchpad/apertar-kb-speed-ramp-2026-10-27/kb/...` (T31/T32 tutorials, `working/ramp-answer.md`, `working/ramp-ladder/*`) | no git; export of 2026-10-27 |

Labels: **CONFIRMED** = I opened the line. **PROBABLE** = derived; the derivation is given. **UNCONFIRMED** = only the Pi can say.

I re-checked these plan facts and they hold: F2/F3 (`CC:6293-6356`, `:6358-6370`), F5 (`CC:10322-10337`), F6
(`CC:2784`), F7 (`CC:2781-2782`), F8 (`CC:2559-2580`), F13 (`QML:1373-1376`, `:1557-1559`), F14 (`CB:1035-1052`), F15
(`src/ipc/ControlProtocol.cpp:120-124`), "no `clear_hdr` merge" (`Web:8761-8846`), poll 1 s (`Web:11800`). The 16-bit Clear HDR
DNG is cropped to 3840x2160 (`CC:2347-2350`, `:2988-3004`), so both rungs really keep the frame size. CONFIRMED.

---

## Verdict

| Plan section | Verdict | Why (one line) |
| --- | --- | --- |
| §0 Short answer | **change** | Say plainly that ramp takes never use rung 1 under A + R, and that "no frames lost" excludes storage drops at 50 fps (Problems 1, 3) |
| §1.1 Where it lives | **change** | Ramp-ready belongs in the T32 Speed Ramp block, not the ladder card (Problem 6) |
| §1.2 Mode Ladder card | keep, **change** | Keep rows, drag, Up/Down, thresholds, toggle. Fix the redraw guard (Problem 10). Drop the per-rung "Enabled" box (Remove + pool does it) |
| §1.3 Validation | keep | Add the preset rule (Problem 8) |
| §1.4 Touch UI | **change** | Show the class in words and the take ceiling, not "R1/2" (Problem 2). Disable mode items, do not refuse silently (Problem 9) |
| §1.5 Picking / ramping | keep, **change** | In-take cap = the rung's ceiling, not the mode's (Problem 11) |
| §1.6 Files on the card | keep | A + R: one clip, one WAV, one `FrameRate`. Correct |
| §1.7 Refusals | keep, **change** | Presets (Problem 8). The `notice` reply field is optional; the pot never sees it |
| §2.1 Facts | keep | Re-checked; they hold |
| §2.2 A | keep, **change** | Cost table misses the off-project base rate (Problem 14) |
| §2.3 R | keep the idea, **change** | Arming and display (Problems 1, 2, 6) |
| §2.4 B | keep as deferred T35 | Add: B leaves the tail of a 24 → 50 → 24 shot in the other look (Problem 15) |
| §2.5 B0 | **drop** | Patrik can judge the look change with M6 (two takes by hand). No code needed |
| §2.6 Comparison | **change** | Add rows: base FrameRate, storage at 50, look of head vs tail |
| §2.7 Recommendation | keep A + R, **change** | "Lossy rung 2: design unchanged" is wrong (Problem 7). Add M0 first (Problem 4) |
| §3.1 Rung identity | keep | Core identity (3840x2160 for both classes) is right |
| §3.2 Chooser | keep, **change** | Move to a libcamera-free file with a host test (Problem 13). Cap rule (Problem 11) |
| §3.3 Storage | keep | `mode_ladder.conf` is defensible. Add one table "where each setting lives" (Missing) |
| §3.4 Build max | keep | `max_fps` is also the safety knob if M3 fails |
| §3.5 Commands | keep | |
| §3.6 State fields | **change** | `fps_max` must not shrink the pot's list in a take (Problem 5). Fewer `ladder_*` fields |
| §3.7 How the UIs learn | **change** | PCF row (Problem 5) |
| §4 Part 1 (T33a) | keep, **change** | 1.12 only (Problem 5) |
| §4 Part 2 (Core) | **change** | Split logic out of `CC` (Problem 13); 2.10 presets (Problem 8) |
| §4 Part 3 (WebUI) | **change** | Redraw guard, ramp-ready location, target select, pill tint (Problems 2, 6, 10) |
| §4 Part 4 (touch UI) | **change** | 4.4 text, 4.5 widen to Clear HDR and bit depth (Problems 2, 9) |
| §4 Part 5 (B) | keep as notes | |
| §5 Measurements | **change** | Add M0; M3 as a ramp take at shoot-day drive fill; M5 latency; M6 exposure (Problems 3, 4, 12, 17) |
| §6 Risks / questions | keep, **change** | Add hidden drops, untested T31, pot remap, R arming question |

---

## Problems

Ordered by harm on set or in the edit.

### 1. Ramp-ready is armed by a switch Patrik will leave on. Every take then silently loses Clear HDR.

- **What:** R chooses with `target = (fps_ramp && rampReach > 0) ? max(fps, rampReach) : fps` (plan §3.2). `fps_ramp` is a
  persisted, per-format setting (writer `CC:809`, reader `CC:735`; CONFIRMED). T31 tells him "Once on, every fps control ramps a
  running take" (T31 tutorial line 19, KB export). So Speed Ramp is a mode he leaves on, not a per-take arm.
- **Evidence:** the above, plus Problem 2: the touch screen does not show the class at all.
- **Consequence:** with Speed Ramp on and ramp-ready set, every take, including plain 24 fps takes with no ramp, is SDR 12-bit.
  He finds out in Resolve. PROBABLE (from the rule plus the display gap).
- **Fix:**
  1. Show the class in words on both UIs, amber when ramp-ready picked it (Problem 2). This is required, not optional.
  2. Make ramp-ready its own switch in the Speed Ramp block, default Off. "On" means "this camera is set up for ramp shots".
  3. Ask Patrik (new Q9): sticky (stays on until he turns it off) or one-shot (clears after each take, then Core re-aligns
     after the drain, Cinemate `ff59dd8` "settle only after the drain"). One-shot is safer: forgetting to arm is visible on set
     (the ramp stops at 25); forgetting to disarm is not.

### 2. The touch screen never says which class is running. "R1/2" adds a number, not the look.

- **What:** the main FORMAT line shows the resolution and the compression only: value `root.resolution`, sub
  "Uncompressed"/"MLV RAW"/… (`QML:519-526`, InfoLine `QML:3606-3610`; CONFIRMED). "4K Clear HDR" appears only inside the quick
  menu (`QML:3235`). The plan adds "R1/2 · Uncompressed" (§1.4).
- **Consequence:** tapping 30 changes HDR 16-bit to SDR 12-bit with one preview blink and no word on the main screen. "R2/2"
  tells him a rung number he has to remember. In a take he also cannot see the ceiling before pressing record.
- **Fix:** FORMAT `sub` = class + in-take ceiling, e.g. `HDR16 · ≤25 · Uncompressed` / `SDR12 · ≤50 · RAMP` (Cinemate
  `2c8cf81`: show a substitution; it tints RES). Same string beside "Frame rate" in the WebUI quick pane (plan 3.7). Tint the
  FPS pills and picker entries that switch class, so a tap's consequence is visible before the tap.

### 3. "No frames are lost" is only true for the switch. R puts every ramp take in the 622 MB/s mode, and in a ramp take a drop leaves no hole.

- **What:** 4K SDR 12-bit at 50 needs ~622 MB/s (plan F9; 3840 × 2160 × 1.5 B × 50, PROBABLE arithmetic, it checks). Measured:
  437 MB/s fio at Gen 2 (`HL:317-321`); at Gen 3, 415 MB/s Clear HDR 25 fps lost 166 and 676 frames in 3-minute takes on a
  77-81 % full drive (`HL:380-384`). A ramp take numbers frames by count (`CC:8018`, `nextFrameIndex(…, countOnly)`
  `CC:3790`), so "drops in a ramp take do not leave numbering holes" (`working/ramp-answer.md:102`, KB export). CONFIRMED lines.
- **Derivation:** the raw queue holds 12 frames (r1 §c) = 149 MB at 12.44 MB. At 437 MB/s in, 622 out, it fills in ~0.8 s.
  PROBABLE.
- **Consequence:** the slow-motion stretch, the reason for the shot, stutters. The folder looks complete. Found in the edit.
- **Fix:** (a) say it in §0 next to "no frames lost"; (b) M3 must be a ramp take (24 → 50 → 24) at the drive fill of a shoot
  day, holding 50 for the longest stretch he plans, plus a steady 60 s; (c) check that a queue-full drop sets
  `recording_has_dropped_frames` (`App:7993`, `:11333`; what sets it is UNCONFIRMED) and that both UIs show it at stop; write
  `# dropped_queue_full=N dropped_gap=N` into `fps-ramp.txt`; (d) until M3 passes, set `max_fps` to what passed (e.g. 40).

### 4. A + R is built on T31 and T32, which have never run on the Pi.

- **What:** README §2: "Nothing ran on the Pi in the cloud session" (`working/ramp-ladder/README.md:37-38`, KB export). T32:
  "Not run against Core on the Pi" (T32 tutorial line 19). `HL` has no ramp entry (grep for "ramp", "T31": none). CONFIRMED.
- **Consequence:** A + R's whole value is "T31 inside rung 2". 750 new lines sit on an unverified base. A T31 defect (grace,
  pairing, WAV end, `FrameRate`) would look like a ladder defect.
- **Fix:** new **M0**, before any T34 code: T31 §5's own test, as a 24 → 50 → 24 ramp take in 3840x2076 SDR 12-bit (Core
  allows 60 there today, no code change), then a Resolve conform check: which `FrameRate` Resolve reads, RecRun TC continuous,
  WAV = real time, the 50 fps stretch plays at half speed. It doubles as M3.

### 5. The PCF pot changes meaning at record start, because `fps_max` changes the list length.

- **What:** plan 1.12 cuts `availablePcfFpsOptions` at `settings.fpsMax`; §3.6 makes `fps_max` the ladder ceiling off-take
  (50) and the running mode's ceiling in a take (25 in rung 1). The pot maps its position by list length:
  `llround(normalized × (count − 1))` (`App:8607-8613`); the handler dispatches `set_fps` when the mapped value differs
  (`App:8682-8689`); an event comes only after a 32-count move (`GAI:473`). CONFIRMED lines.
- **Derivation:** off-take, list {24, 25, 30, 50}, pot at 0.33 → 25. In a rung-1 take the list is {24, 25}; a nudge past the
  deadband maps 0.35 → index 0 → `set_fps 24` → an unintended ramp step. After stop the reverse. PROBABLE.
- **Consequence:** a touch on the pot during a take changes the speed of the shot.
- **Fix:** the pot and `fps_up/down` use a list that does not change during a take: cut at the ladder ceiling (the off-take
  `fps_max`) and let Core clamp, as it already does (`CC:9105-9113`). Publish that as a second field (`fps_max_ladder`) or
  freeze the list at record start. The touch picker and WebUI pills may keep the in-take cut; they show their items.

### 6. Two controls hold "the ramp's top", and the one he uses falls back silently.

- **What:** the T32 Speed Ramp target lives in the browser only (`state.speedRampTarget`, `Web:4238`, set at `Web:11580`). Its
  list comes from the FPS options; when the target is not in the list, the select shows the highest entry instead
  (`Web:5124-5131`). CONFIRMED. The plan adds a second control, "Speed Ramp takes start in", in the ladder card (§1.2, stored as
  `ramp_reach`). T32 promised the ladder rows go "into this same block" (T32 tutorial line 560).
- **Consequence:** he arms "Ramp to 50", records in rung 1, presses Ramp, and it ramps to 25. The two settings can disagree.
- **Fix:** one control, in the Speed Ramp block: a "Ramp-ready" switch (Problem 1) whose reach is the ladder top. Patrik's
  ladder has one useful reach (50), so the reach select can go. In a take whose ceiling is below the armed target, the select
  shows "50 · not in this take (HDR16 stops at 25)" disabled, never a silent substitute.

### 7. "Rung 2 must be lossy DNG… the ladder design is unchanged" (plan §2.7) is wrong.

- **What:** "Lossy cDNG does not support Clear HDR" (`RC:76-78`). Lossy DNG is its own `RecordingFormat` with its own folder
  prefix (`CC:4200-4201`). The rung is (resolution, bit depth, Clear HDR) only (plan §3.1). Lossless is capped at 30
  (`CC:2559-2580`). CONFIRMED.
- **Consequence:** if M3 fails uncompressed, "lossy rung 2" means a format change between rungs: a new rung field, a profile
  swap (`setRecordingFormat` swaps the whole profile, plan §3.3) and clip folders named `cDNG_3to1_…` next to `cDNG_…`.
  That is a different design, not new numbers.
- **Fix:** correct the §2.7 row. Options in order: lower rung 2's top with `max_fps`; Gen 3 if the drops stop; a format field
  per rung only as its own later tutorial.

### 8. Presets and Favorites are silently overridden by the ladder.

- **What:** plan 2.10 re-aligns after `applyCapturePreset`: "the preset's FPS decides the rung". A preset carries resolution and
  bit depth (`CC:10231-10257`). CONFIRMED.
- **Consequence:** a Favorite "4K SDR12 24 fps" loads as Clear HDR 16-bit at 24. The preset lies.
- **Fix:** with the ladder active, refuse a preset whose mode is not the ladder's choice for its FPS, with a clear message, or
  load it and turn the ladder off (Patrik picks). Never a silent re-align.

### 9. Touch UI: mode controls fail silently; the plan fixes one of three.

- **What:** plan 4.5 adds a warning to `applyResolutionValue` only (`QML:1214`). The quick menu's "4K Clear HDR" item and every
  other resolution item call `applyClearHdr` first (`QML:1242-1250`); the Settings page calls `applyRawBitDepth`
  (`SP:3264`). With 2.7 all three are refused. CONFIRMED paths.
- **Consequence:** a tap does nothing and says nothing.
- **Fix:** while `ladderActive`, grey these items out with one line "Mode Ladder on: the FPS picks the mode" (as the WebUI does in
  plan 3.6). Disabled beats refused.

### 10. The editor's redraw rule contradicts itself; the Part 3 version loses typing focus every second.

- **What:** §1.2: "must not redraw its rows … while the draft has unsaved changes". Part 3: "redraws the rows only when
  `!state.ladderDrag` and (`state.ladderDirty` or the server copy changed)". The page polls every second (`Web:11800`).
- **Consequence:** with the Part 3 rule, typing a threshold rebuilds the field each second. Patrik types from the tutorial, so
  he gets that version.
- **Fix:** rows redraw on local edit events only. On a poll: redraw only if not dirty, the server copy changed, and no input in
  the card has focus. If the server copy changes while dirty, show "Changed elsewhere. Revert to load it."

### 11. In a take the plan caps at the mode's ceiling, not the rung's. That breaks its own definition.

- **What:** §1.2: "The ceiling is the highest FPS this rung serves". §1.5 / Q3: in a take, cap at the mode's ceiling instead.
- **Consequence:** a rung set "HDR up to 20" (say, because 21-25 drops on his card) runs HDR at 25 in a take. For Patrik's
  ladder both numbers are 25, so no difference today.
- **Fix:** one number per rung everywhere: `ceiling(r) = min(threshold, mode ceiling)`, in and out of takes. Q3 default →
  threshold.

### 12. "From the lowest possible FPS": at 1-5 fps a ramp step lands seconds late, and drop detection is off for ≥ 10 s.

- **What:** T31 grace = `max(10, requests + 6)` frames at the slower rate (`CC:8313-8331`). Control latency ≈ N + 2 frames
  (T31 tutorial line 23; N = 8-10 in Clear HDR). The stepper moves 1 fps per step (`App:9290-9334`). CONFIRMED lines.
- **Derivation:** at 1 fps in rung 1: ~10 s before a step takes effect, ≥ 14 s of grace per step; 1 → 2 is a 2× jump, the case
  T31 says the gap estimator can misread (`working/ramp-answer.md:103`). PROBABLE.
- **Consequence:** the bottom of "lowest → 50" cannot be timed on set.
- **Fix:** M5 also records `lag_frames` and seconds per step at 2, 5 and 12 fps in a take. Pick a practical floor from that
  (Q6). Say it in the tutorial.

### 13. ~330 Core lines go into the one file that cannot compile off the Pi, and the chooser has no test.

- **What:** plan §0: Core ~330 lines, almost all in `CC`. "`CameraController.cpp` was not compiled (libcamera)" (README §2).
  Cinemate guards its ladder with an invariant test (`ff59dd8`; r2 §c: "no reachable request outruns the mode it lands in").
- **Consequence:** Patrik types the parser, validation and chooser blind and finds typos on the Pi.
- **Fix:** `src/camera/ModeLadder.hpp/.cpp`, no libcamera: `LadderRung`, parse/format text, validation, `chooseRung(ceilings,
  target)`. Host `g++` plus a ~30-line test of the `ff59dd8` invariant and of Patrik's ladder (24 → rung 1, 25 → 1, 25.001 → 2,
  60 → 2 at 50). `CC` only calls it and supplies the ceilings.

### 14. A's cost is understated: without R, a ramp take has the wrong base rate for the project.

- **What:** with A alone, rung 2 is reached only by picking > 25 off-take. T31 pins every frame's `FrameRate` and RecRun TC to the
  take's start rate (`working/ramp-answer.md` §3 row 5).
- **Consequence:** a 30 → 50 ramp take is a 30 fps clip in a 24/25 project. Conform per clip. A + R avoids it (base 24 in rung 2).
- **Fix:** add the row to §2.2 and §2.6. It is another reason R is needed, not optional.

### 15. B's comparison misses that B ends the shot in the other look.

- **What:** B "never switches back down in a take" (plan §1.5).
- **Consequence:** a 24 → 50 → 24 shot starts Clear HDR 16-bit and ends SDR 12-bit. The real-speed head and tail need two grades,
  and the cut sits mid-action on top of an 8-26 frame hole (plan's estimate, UNCONFIRMED). Only useful for a one-way ramp the
  editor cuts on anyway.
- **Fix:** say it in §2.4, §2.6 and Q1. It strengthens A + R.

### 16. No hysteresis at the rung boundary off-take (lower harm).

- **What:** in A + R nothing switches in a take, so in-take hysteresis is not needed. CONFIRMED by the design. The stepper is
  monotonic: one reconfigure per crossing. Pot sweeps coalesce, because the pot thread calls the handler inline
  (`GAI:427`) and the handler blocks on the camera while a reconfigure runs: PROBABLE. A pot parked near the 25 / 30 boundary
  (0.5 of travel with four options) can still flip on a touch; the deadband is 32 of 4095 counts (`GAI:473`).
- **Consequence:** occasional double blink in preview. Plan R4 overstates sweeps, understates "parked at the boundary".
- **Fix:** rung switches from hardware inputs apply after the value has been still for ~300 ms. Only if M1 shows a long blink.

### 17. M6 compares the grade but not the exposure.

- **What:** ISO maps to `AnalogueGain = iso / 100` for both classes (`CC:2141-2143`). CONFIRMED. Whether the same ISO and shutter
  give the same mid-grey in Clear HDR 16-bit and SDR 12-bit is UNCONFIRMED.
- **Consequence:** an off-take rung switch may change brightness and highlight headroom at the same settings. He re-exposes on
  set without knowing why.
- **Fix:** M6 records grey-card level (as % of white) and the clip point in both classes at equal ISO/shutter. If they differ by
  more than 1/3 stop, the UI says so at the switch; a per-rung ISO offset is a later option.

---

## Missing

| # | What | Why it matters |
| --- | --- | --- |
| 1 | **M0**: T31 on the Pi plus a Resolve conform of a ramp take (Problem 4) | Everything in A + R depends on it |
| 2 | An on-set sheet: Patrik's two shot types, tap by tap, with what each screen shows (below, last section) | Predictability. The plan describes Core paths, not the operator's day |
| 3 | What "ladder off" leaves | The camera stays in the last rung (off-take switches persist, plan 2.6). Say it in both UIs: "Ladder off. Camera stays in 4K SDR12." |
| 4 | Arming from the camera body | On set he shoots from the touch screen. A touch toggle or a PCF action `ramp_ready` for Problem 1's switch. Today Speed Ramp itself is WebUI-only (no `fps_ramp` control in `QML`; only `CB` reads it) |
| 5 | HDMI monitor | R11 "later". An operator on HDMI sees no class. At least the class string of Problem 2 |
| 6 | "Where each setting lives" table | T33 lists in `UI.conf`, `max_fps` in `apertar-hardware.conf`, the ladder in `mode_ladder.conf`, `fps_ramp` per profile in `camera_settings.conf`. Four homes; one table in the tutorial for backup and debugging |
| 7 | Measurement hygiene | M1: subtract a `get_state` round trip (Python start-up is inside the timing). M3: run at shoot-day drive fill (`HL:386`: the write cache shrinks as the drive fills). M5: latency (Problem 12). M7: read ISO and WB from the first DNGs after a switch, not only `shutter_us` (Cinemate `f884716`: controls lost after a mode switch; in Core they ride the start request, PROBABLE fine) |
| 8 | One-shot R needs a re-align after the drain | If Patrik picks one-shot (Problem 1), stop must re-align once the queue has drained (`ff59dd8`). One blink after a ramp take |
| 9 | Cinemate `2c8cf81` "re-derive the ceiling and the step table on every toggle" | The plan does it through `fps_max`; the tutorial should name the lesson so Patrik knows why the pills change |
| 10 | Ramp-up target pills during a reconfigure | The WebUI patches the snapshot before Core replies (`applyCommandSnapshotPatch(payload, null, true)`, `Web:9302`). For a rung switch the label shows "Rung 1/2" with 50 fps until the reply. Patch `ladder_*` optimistically too, or show "Switching mode…" |

---

## Simplest version that still does what Patrik asked

**Keep A + R. Shrink it. Measure first.**

### Order

| Step | What | Code |
| --- | --- | --- |
| 1 | M0 + M3 on the Pi: T31 ramp take 24 → 50 → 24 in 3840x2076 SDR 12-bit at shoot-day drive fill, Resolve conform. M1/M2 switch time. M6 look and exposure | none |
| 2 | T33a as plan Part 1, except 1.12: the pot list is cut at the ladder ceiling and does not change in a take | ~150 lines (plan's estimate) |
| 3 | `ModeLadder.hpp/.cpp` (pure, host-tested): rung struct, text format, validation, chooser | ~120 + ~30 test |
| 4 | `CC` hooks: `setFps` off-take → chooser → one reconfigure (commit = true); refuse resolution / bit depth / Clear HDR while active; re-align on toggle, save, Speed Ramp, ramp-ready, start; in-take cap = rung ceiling; storage `mode_ladder.conf` | ~120 |
| 5 | WebUI: Mode Ladder card (toggle, rows with handle + Up/Down, threshold, Remove, Add from pool, Save/Revert, warnings). Ramp-ready switch inside the Speed Ramp block. Class string beside "Frame rate"; pills that switch class tinted | ~250 |
| 6 | Touch UI: FORMAT `sub` = class + ceiling; `set_fps` in the 10 s list; mode items disabled while active | ~30 |

PROBABLE line counts; about 700 in all, with ~150 of the Core part testable on the host.

### Dropped from plan-v1

- B0 (design and code).
- The `ramp_reach` select: ramp-ready reaches the ladder top.
- The per-rung "Enabled" checkbox: Remove plus the pool does the same.
- The `notice` reply field and toast (plan 2.14, 2.21, 3.7): the UIs already cut their lists in a take, and the pot cannot show a
  toast. Keep the journal line (plan 2.22).
- Five of the seven `ladder_*` state fields. Keep `fps_max`, `fps_max_ladder` (for the pot), `ladder_active`, `ladder_class`
  (the display string, e.g. `HDR16 ≤25`), `ladder_ramp_ready`. The editor fetches `get_mode_ladder` on open and after Save.

### What Patrik's day looks like with it

| Shot | He does | Camera does | Screen says |
| --- | --- | --- | --- |
| Normal take, 24 | Picks 24 | Rung 1, no switch | `3840x2160` · `HDR16 · ≤25 · Uncompressed` |
| Normal take, 50 | Picks 50 | One reconfigure, blink | `SDR12 · ≤50` (pills above 25 tinted) |
| Ramp shot 24 → 50 → 24 | Speed Ramp On, Ramp-ready On, picks 24 | One reconfigure to SDR12 at 24 | `SDR12 · ≤50 · RAMP` in amber |
| | Record, ramp with pot / pills / Speed Ramp block | T31 steps inside SDR12; one clip, one WAV, base 24 | live FPS; dropped-frame flag at stop if any |
| | Stop | Back to 24; ramp-ready stays (sticky) or clears and re-aligns to HDR16 (one-shot) | `RAMP` amber or `HDR16` again |
| Ramp shot without arming | Record at 24 in rung 1, ramp | Stops at 25 | `≤25` was on screen before record; Speed Ramp block says "50 not in this take" |

### Questions to add to plan §6.2

| # | Question | Proposed default |
| --- | --- | --- |
| Q9 | Ramp-ready: sticky until turned off, or one-shot per take? | one-shot (safer: forgetting is visible on set) |
| Q10 | A Favorite whose mode the ladder would not pick: refuse, or load and turn the ladder off? | refuse with a message |
| Q11 | Is a ramp shot in SDR 12-bit while the rest of the scene is Clear HDR 16-bit acceptable in the grade? (decided by M6) | yes, if M6 shows the grade matches |
