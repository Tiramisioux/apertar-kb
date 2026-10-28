# T34 Mode Ladder: how it works, what to build, what to measure first

2026-10-27, cloud session, reviser pass (v2). Built from `plan-v1.md`, `critique-code.md` and `critique-operator.md` in this
folder. Every point where a critic disagreed with the plan was checked against the code (`changes-from-critique.md`). Read-only
on every repository. Nothing was built in a repository and nothing ran on the Pi. One sketch was compiled and run on the host:
`sketch/camera/ModeLadder.hpp` with `sketch/mode_ladder_test.cpp` (g++ 13.3, `-Wall -Wextra -Werror`, 28 checks, all pass).

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `CC`, `Hdr` | `src/camera/CameraController.cpp`, `.hpp` | Core `scratchpad/tip-core` `119d0bb` = GitHub `cinemate-port` `6ae70b5` + T31 `5f38585` + T32 `cba1963`, `119d0bb` |
| `App`, `Web`, `Types`, `CP`, `GAI`, `RC`, `SF` | `src/ApertarCoreApp.cpp`, `src/web/WebControlPage.cpp`, `include/apertar/core/Types.hpp`, `src/ipc/ControlProtocol.cpp`, `src/hardware/GroveAnalogInput.cpp`, `include/apertar/core/RecordingCapabilities.hpp`, `src/util/SettingsFile.hpp` | same |
| `CB`, `CBh`, `QML`, `SP` | `src/ApertarControlBridge.cpp`, `.hpp`, `qml/CameraPage.qml`, `qml/SettingsPage.qml` | Apertar-UI `scratchpad/verify2/home/ApertarUI` `34499f1` = `dc471c1` + the two T32 UI patches |
| `HL`, `TP`, `tools/` | `lessons/hardware-log.md`, `tutorials/tutorial.py`, `working/tools/` | KB `scratchpad/verify3` `8b655da` |
| `RA`, `T31`, `T32`, `Q2P` | `working/ramp-answer.md`, the T31 and T32 notes, `working/research-30fps/q2-pipelining.md` | KB export `scratchpad/apertar-kb-speed-ramp-2026-10-27/kb` (no git) |
| cinemate | | `d6cc93e` |

Labels: **CONFIRMED** = I opened the line (or ran the command) on the tree above. **PROBABLE** = derived; the derivation is given.
**UNCONFIRMED** = not checked, or only the Pi can settle it.

Tutorial numbers used here:

| Number | What | Why |
| --- | --- | --- |
| T33 | Build maximum `max_fps`, one published ceiling `fps_max`, 4K SDR up to the probe | The ladder needs it first. It is the "build max" half of README §3.1 |
| T34 | The mode ladder, in three parts (A Core, B WebUI, C touch UI), each ending in a build and a test | This design |
| T35 | Value lists (ISO, shutter angle, FPS, WB), the rest of README §3.1 | Independent of the ladder |
| later | Design B (class switch inside a take) | Only after M1, M2 and M6 |

Not "T34a/b/c": `tutorial.py` finds a note by `T` + two digits (`TP:98`, `re.search(r"\b(T\d\d)\b", path.name)`), so `T34a` is
not found. CONFIRMED. Two old lines need a one-line fix: T32 line 560 ("Next: the mode ladder (T33)") and README §3.1 ("T33:
value lists"). Q12 asks Patrik.

---

## 0. Short answer

1. With the ladder on, the FPS picks the mode: 4K Clear HDR 16-bit up to 25, 4K SDR 12-bit up to 50 (`max_fps=50`), always 3840x2160.
2. Rungs change between takes only (design A): crossing 25 is one reconfigure, a preview blink. In a take the rung's ceiling caps T31.
3. Ramp-ready (default Off, in the Speed Ramp block) starts Speed Ramp takes in the top rung: 20 → 50 → 20 in one mode, no hole.
4. Its price: that whole take is SDR 12-bit. The class is always on screen: `HDR16 · ≤25 · Uncompressed`, `SDR12 · ≤50 · RAMP`.
5. Editor: a WebUI card with drag and drop, Up/Down, optional thresholds, On/Off. Core checks every draft. Touch UI: On/Off and Ramp-ready.
6. Not built: a class switch inside a take (design B: frame hole, clip split, look cut). Deferred until measured.
7. Cost (PROBABLE): T33 ~150 lines; T34 ~1,100 (Core ~620, of it ~270 in `CameraController` that only the Pi compiles; WebUI ~330; UI ~120).
8. The ladder's logic is a libcamera-free header, host-tested here (28 of 28 checks), so most of it is checked before the Pi.
9. Measure first: M0 (T31 has never run on the Pi), M3 (50 fps for 3 min needs ~600 MB/s; Gen 2 gave 437), M1 (how long the blink is).
10. If M3 fails, `max_fps` = the rate that held; the design stays. Your calls: Q1 (is A + R enough), Q9 (Ramp-ready sticky), Q10 (Favorites).

---

## 1. How the system works

### 1.1 Where things are (operator)

| Surface | What you get | Why there |
| --- | --- | --- |
| WebUI Settings → Record, new card **Mode Ladder** right after the Recording format card (`Web:2951`) | On/Off, the rungs (drag handle, label, threshold, Up, Down, Remove), Add a mode, Save, Revert, Core's warnings | Editing is a WebUI job (brief item 9) |
| WebUI Speed Ramp block (T32, `Web:2918-2950`) | New **Ramp-ready** Off/On pills under Speed Ramp Off/On | It is a ramp setting. One control for "the ramp's top", not two (operator critique 6) |
| WebUI Camera settings pane (`Web:2538-2560`) | Same pills. The "Frame rate" line shows `HDR16 · ≤25` / `SDR12 · ≤50`. Pills that would switch class are tinted | Brief item 10: the quick menu stays |
| Touch UI FORMAT line (`QML:519-526`, `:3606-3610`) | `HDR16 · ≤25 · Uncompressed`, `SDR12 · ≤50 · RAMP` | Today it shows resolution and compression only. CONFIRMED |
| Touch UI Settings → Record | Two rows: Mode Ladder On/Off, Ramp-ready On/Off. Resolution, Clear HDR and Bit Depth are greyed while the ladder is on, with one line "Mode Ladder on: the FPS picks the mode" | A way out on the camera (code critique Missing 9) |
| Socket | `get_mode_ladder`, `set_mode_ladder` | `core.py` tests and the tutorial's checks |

### 1.2 Operator view: three walkthroughs

Setup for all three: ladder On with your two rungs, `max_fps=50`, cDNG uncompressed, 180°, Speed Ramp On, Ramp-ready Off unless
the row says otherwise.

20 fps is not in today's lists: the WebUI starts at 24 (`Web:4071`), the touch UI at 24 (`QML:809-813`), the PCF pot at 24
(`App:1178-1181`). CONFIRMED. For these walkthroughs add 20 to the WebUI and touch UI lists (T32 §8 exercise), or use
`core.py set_fps value=20`. T35 makes the lists editable.

**A. Picking 20, 30, 50 outside a take**

| You do | Camera does | Touch FORMAT line | WebUI |
| --- | --- | --- | --- |
| Pick 20 (in rung 1) | FPS change only, no reconfigure | `HDR16 · ≤25 · Uncompressed` | pills 20 … 50, those above 25 tinted |
| Pick 30 | One reconfigure into rung 2. Shutter keeps 180°. Saved, so a restart comes back here | blink, then `SDR12 · ≤50 · Uncompressed` | label `SDR12 · ≤50`, no tint |
| Pick 50 | FPS change only (rung 2 runs 26 … 50) | `SDR12 · ≤50` | |
| Pick 20 again | One reconfigure back to rung 1 | blink, then `HDR16 · ≤25` | |
| Touch the Clear HDR or Resolution item | Nothing: greyed, with "Mode Ladder on: the FPS picks the mode" | | same, greyed |

**B. A ramp take 20 → 50 → 20 with the stepper**

| Step | Ramp-ready Off | Ramp-ready On |
| --- | --- | --- |
| Before record, at 20 | rung 1, `HDR16 · ≤25` on screen | arming it reconfigures once into rung 2 at 20: `SDR12 · ≤50 · RAMP` in amber |
| Record | take base 20 (T31) | take base 20 |
| Ramp to 50 over 5 s | 21 … 25, then the stepper stops. Journal: "fps ramp stopped: 25 fps is the ceiling of ladder rung 1 (4K Clear HDR 16-bit) in a take". The Speed Ramp line says "Ramp to 50 is not possible in this take: HDR16 stops at 25." | 21 … 50, all inside rung 2, no reconfigure |
| Ramp to 20 | 24 … 20 | 49 … 20 |
| Stop | base 20 restored (T31) | base 20 restored. Still rung 2 while Ramp-ready is on (Q9) |
| In the edit | one clip at 20, the 21-25 stretch slightly slow | one clip at 20, the 50 stretch at 0.4× speed. One WAV, real time |
| Ramp-ready Off afterwards | | one reconfigure back to rung 1 at 20 |

The stepper is not special. The PCF pot, `fps_up`/`fps_down`, the WebUI pills and the touch UI picker reach the same
`CameraController::setFps` (pot `App:8682-8689`, buttons `App:8943-8949`, stepper `App:9321`). CONFIRMED.

"No frames lost" means no hole from a mode switch. Storage can still drop frames at 50 fps (about 622 MB/s), and in a ramp take
frames are numbered by count, so a drop leaves **no gap in the file numbers** (`CC:8018`; RA §5). A queue-full drop does set the
dropped-frame flag (`CC:3911-3912`), which the touch UI shows (`QML:2593`). CONFIRMED. M0 and M3 decide whether 50 holds.

**C. The toggle off (and on again)**

| You do | Camera does | Screen |
| --- | --- | --- |
| Mode Ladder Off | No reconfigure. The camera **stays in the last rung** | Touch: "Ladder off. Camera stays in 4K SDR 12-bit." Mode items unlock |
| Pick 20 | FPS change only, still SDR 12-bit | `SDR12 · ≤50` |
| Mode Ladder On | Re-aligns: 20 belongs to rung 1, so one reconfigure | blink, `HDR16 · ≤25` |
| Toggle during a take | Refused: "Stop recording before changing the mode ladder." | WebUI pills greyed in a take |

Your day, tap by tap (from the operator critique, kept):

| Shot | You do | Screen says |
| --- | --- | --- |
| Normal take at 24 | pick 24 | `HDR16 · ≤25 · Uncompressed` |
| Normal take at 50 | pick 50 (one blink) | `SDR12 · ≤50` |
| Ramp shot 24 → 50 → 24 | Ramp-ready On (one blink), record, ramp with the pot, pills or the Speed Ramp block, stop | `SDR12 · ≤50 · RAMP` in amber; dropped-frame flag at stop if storage lost frames |
| Ramp shot without arming | record at 24, ramp | `≤25` was on screen before record; the ramp stops at 25 |

### 1.3 Core view: the same three

**A. Off-take FPS pick** (WebUI pill → `POST /api/command` → `App:9747` `set_fps` → `CameraController::setFps`, `CC:9074`):

| Step | Code (new code marked T34) |
| --- | --- |
| 1 | Not recording, so T31's ramp gate is skipped (`CC:9083-9096`) |
| 2 | T34: `ladderRewriteLocked(requested)` picks the rung for the target. Target = `fps`, or the ladder ceiling when Ramp-ready and `fps_ramp` are both on. Rule: `chooseRung` in `ModeLadder.hpp` (first usable rung whose ceiling reaches the target) |
| 3 | `sanitizeSettingsForSensor` clamps to the rung's mode (`CC:2835-2881`): table, probe, lossless cap, `max_fps` |
| 4a | Same mode: today's `applyFpsStepLocked` → `applySettingsLocked(next, false, true)` → `applyControls` (no reconfigure) → persist and emit (`CC:9121-9158`, `:10287-10352`) |
| 4b | Other mode: the same `applyFpsStepLocked`, given the rung. It keeps the shutter policy (`CC:9127-9145`), logs `ApertarCore mode ladder: 20 -> 30 fps, 4K Clear HDR 16-bit -> 4K SDR 12-bit` and calls `applySettingsLocked(next, true, true)`. A Clear HDR change is `stop()` + `start()` (`CC:10291`, `:6358-6370`): WDR off, other tuning variant, new CameraManager (`CC:6145-6152`). On failure the recovery puts rung 1 back and the reply carries the error (`CC:10322-10333`, commit = true). One apply, one reconfigure |
| 5 | The settings event carries `clear_hdr`, `raw_bit_depth`, `fps` and the T34 fields (§3.6). The WebUI and touch UI redraw |

**B. The ramp take** (`ramp_fps to=50 seconds=5` → `App:9290` stepper thread → `camera_.setFps(x, takeScoped)` per step):

| Step | Ramp-ready Off | Ramp-ready On |
| --- | --- | --- |
| Arm | | `set_mode_ladder ramp_ready=true` → `setModeLadder` → `ladderRewriteLocked(settings_)`: target = ladder ceiling 50 → rung 2 → one `applySettingsLocked(…, true, true)` → `mode_ladder.conf` written → event |
| `record_start` | stepper stopped first (`App` `record_start`), `rampTakeBaseFps_ = 20` (`CC:9831`) | same |
| each step | `setFps` in a take: no rewrite (rungs never change in a take). The sanitiser clamps to the running mode (25); T34 also clamps to the running rung's ceiling (one number per rung). 21 … 25 accepted as T31 steps (`commit = false`, `CC:9118`). Step 26 → 25 = no move → the stepper stops (`App:9327-9331`), with the T34 wording | 21 … 50 accepted, controls only |
| stop | `restoreFpsAfterRampLocked` (`CC:9162-9179`) via `applyFpsStepLocked`, not `setFps`: no ladder, no reconfigure | same; rung 2 stays |

**C. The toggle** (`set_mode_ladder enabled=false|true` → `App` handler → `CameraController::setModeLadder`):

| Step | Off | On |
| --- | --- | --- |
| 1 | Refused in a take | Refused in a take |
| 2 | New ladder in memory; `ladderRewriteLocked` returns false (ladder off) | `ladderRewriteLocked(settings_)`: rung for the current FPS |
| 3 | No apply | If the mode differs: one `applySettingsLocked(…, true, true)`. If that fails, the old ladder is put back in memory and the reply is `ok:false` |
| 4 | `mode_ladder.conf` written, settings event | same |

What never happens:

- No reconfigure inside a take. The three mode setters already refuse in a take (`CC:9047-9050`, `:9526-9529`, `:9562-9565`),
  and `ladderRewriteLocked` returns at once when recording. CONFIRMED gates.
- No "apply, then align". Every function that can land in another rung computes the rung **before** its single apply
  (code critique 3).
- The rollback calls of `applyCapturePreset` (`App:6991`, `:10103`, `:10131`, `:10522`) are never given the ladder. CONFIRMED callers.

---

## 2. The decision

### 2.1 Facts every design must respect

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | Resolution, bit-depth and Clear HDR changes are refused in a take | CONFIRMED `CC:9047-9050`, `:9526-9529`, `:9562-9565` |
| F2 | A Clear HDR change forces a reconfigure; a reconfigure is `stop()` + `start()` | CONFIRMED `CC:10291`, `:6358-6370` |
| F3 | `stop()` stops every recorder and destroys the CameraManager | CONFIRMED `CC:6314-6319`, `:6351-6354` |
| F4 | Recovery after a failed reconfigure runs only with `commit = true` | CONFIRMED `CC:10322-10337` |
| F5 | 4K SDR is capped at 30 in Core; the probe says 60 | CONFIRMED `CC:2784`; probe: KB `working/sensor-capabilities.md:51` |
| F6 | 4K Clear HDR 16-bit is capped at 25 (T32) | CONFIRMED `CC:2781-2782` |
| F7 | Lossless cDNG on the IMX585 is capped at 30; lossy DNG has no Clear HDR | CONFIRMED `CC:2559-2580`; `RC:76-78` |
| F8 | 4K SDR 12-bit at 50 ≈ 622 MB/s; 3840x2076 ≈ 598 MB/s | PROBABLE arithmetic (12.44 / 11.96 MB per frame, `working/ramp-mode-ladder.md` §3) |
| F9 | NVMe: 437 MB/s at Gen 2; 818 MB/s burst at Gen 3; Gen 3 lost 166 and 676 frames in 3-minute Clear HDR takes on a 77-81 % full drive | CONFIRMED `HL:317-322`, `:380-386` |
| F10 | Back end per 4K frame: 13.4 ms idle, 34.6 ms while recording Clear HDR 16-bit. 50 fps leaves 20 ms. SDR gets 4 raw buffers (+2 on exFAT), 80-120 ms of cushion at 50 | CONFIRMED `Q2P:125-127`, `CC:1063`, `:1181-1188`; SDR figure PROBABLE |
| F11 | No Core timing of a reconfigure exists. Cinemate's only figure is ~186 ms, without a manager rebuild | CONFIRMED absence (r2 §b.3) |
| F12 | Cinemate never switches class mid-take | CONFIRMED `cinemate/src/module/cinepi_controller.py:904-930` |
| F13 | Clear HDR raw buffers come from the cached DMA heap (8 × 16.9 MB); when that fails Core logs and falls back to uncached buffers, too slow for Clear HDR | CONFIRMED `CC:1063-1067`, `:7392-7414`, `:7297-7298` |
| F14 | A ramp take numbers frames by count: a drop leaves no file-number gap | CONFIRMED `CC:8018` |
| F15 | The touch UI waits 3 s for `set_fps`, 10 s for reconfigure commands; `applyFps` blocks the GUI thread while it waits | CONFIRMED `CB:1036-1052`, `:1084` |
| F16 | Socket requests carry scalars; a bare value ends at `,` or `}`, a quoted string may hold anything | CONFIRMED `CP:62-124` |
| F17 | Before the session starts the sensor family is Unknown, so no rung ceiling can be computed | CONFIRMED `CC:8833` (default), `:6250` (set in `start`) |

### 2.2 The options

| | A: between takes | A + R: ramp-ready start | B: switch in the take, split the clip | B0: stop, switch, record again |
| --- | --- | --- | --- | --- |
| Ramp 24 → 50 in one take | no, stops at 25 | yes, all SDR 12-bit | yes, HDR then SDR | two takes |
| Frames lost to the mode switch | 0 | 0 | hole × FPS; PROBABLE 0.3-1 s, 8-26 frames at 26 fps. UNCONFIRMED (M1, M2) | 25-100 PROBABLE |
| Storage drops at 50 | possible in takes started above 25 (~622 MB/s, M3) | possible in every ramp take that reaches 50 (M3) | same | same |
| Clip split | no | no | yes (two folders) | two takes, two WAVs |
| Base `FrameRate` of a ramp take | the start rate; a 30 → 50 take is a 30 fps clip in a 24 project | 24 (the start rate, in rung 2) | the start rate | two clips |
| Look of head / tail of 24 → 50 → 24 | HDR / HDR | SDR / SDR | HDR / **SDR** (B never switches back down in a take) | HDR / SDR |
| New failure modes in a take | none | none | many (session split, recovery, timecode, audio) | stop/start |
| Core lines | ~520 | ~620 | +700-1,100 in `CC`, none host-checkable | ~150 |

No single mode avoids the choice: Clear HDR at 4K tops at 30 in the probe (12-bit) and 25 is the accepted 16-bit maximum
(F6, `working/sensor-capabilities.md:51`), so "Clear HDR all the way to 50" does not exist on this sensor. CONFIRMED.

### 2.3 Recommendation

Build **A + R** as T34. B0 is dropped (both critics): it is what you already do by hand with A. B stays a later tutorial.

| Your request | A + R |
| --- | --- |
| 1. Lowest → 50, switching mode at thresholds, keeping the resolution | yes between takes; a Speed Ramp take runs lowest → 50 in one mode. Not a switch inside a take |
| 2. Your ladder, 50 from the build settings | yes (`max_fps=50`, T33) |
| 3. Drag-and-drop editor, optional thresholds, toggle | yes, WebUI. On/Off also on the touch screen |
| 4. Ramping in takes | T31, unchanged, inside the running rung |
| 5. Value lists, Camera settings pane kept | T35; the pane is kept and shows the class |

What changed from plan v1: Ramp-ready is its own switch (not armed by `fps_ramp`), a boolean (not an FPS select), and it lives
in the Speed Ramp block. The class is on screen. The in-take cap is the rung's ceiling. Logic moves to a host-tested header.
No "apply, then align". Two FPS ceilings in the state, so the pot does not change meaning at record start. No `notice` field,
no `# mode=` line, no per-rung Enabled box, no B0. Presets that name another mode are refused.

### 2.4 What each measurement would change

| Result | Then |
| --- | --- |
| M0: T31 misbehaves on the Pi (numbering, `FrameRate`, WAV, Resolve conform) | Fix T31 first. Do not start T34 |
| M3: SDR 12-bit cannot hold 50 for 3 min at shoot-day fill | `max_fps` = the rate that held (rung 2's top). Or Gen 3 if the drops stop. A lossy rung 2 is **not** a number change: lossy DNG is another recording format with its own folder prefix (`CC:4200-4201`), so a per-rung format would be a new design |
| M3: drops with a low queue (`dropped_gap_estimate > 0`, `peak_queue` low) | back-end bound. Try `APERTAR_RAW_CAMERA_BUFFERS=8`; else lower `max_fps` |
| M1: a class switch blinks ≥ ~1 s | keep A + R; add a 300 ms settle before a pot-driven switch; say "Switching mode…" on screen |
| M1/M2: hole ≤ ~200 ms **and** M6: the cut is acceptable **and** you want HDR heads | write B as a later tutorial, as an opt-in on top of A + R |
| M6: HDR16 and SDR12 grade alike at 25 | Ramp-ready costs nothing visible; it could stay on |
| M6: same ISO and shutter differ by more than 1/3 stop | show it at the switch; a per-rung ISO offset later |
| M5: the IPA follows 1-2 fps, but a step lands seconds late | pick a practical floor (Q6); put it in T35's FPS list |
| M8: the cached heap fails after many switches | count the fallback in `get_state`; warn before a Clear HDR take |

---

## 3. Data model, storage, commands, state

### 3.1 A rung, and the pure header

A sensor mode in Core is the triple (resolution, raw bit depth, Clear HDR) in `CaptureSettings` (`Types:124-176`). CONFIRMED.
A rung uses Core's identity: 3840x2160 for both 4K classes, although 16-bit Clear HDR reads 3840x2200 on the wire
(`isImx585HighResolutionAlias`, `CC:394-399`). CONFIRMED.

All ladder logic that needs no camera goes in a new **`src/camera/ModeLadder.hpp`**, next to `FramePhaseLock.hpp`
(included at `CC:1`), `ExposureMetering.hpp` and `StillBracketing.hpp`, the project's pattern for pure logic. CONFIRMED.
The host test goes in the KB as `working/tools/mode_ladder_test.cpp`, in the style of `tools/media_profile_test.cpp`.
`CameraController.cpp` cannot be checked off the Pi: its no-libcamera build fails with 33 errors on the tip, the first at
`CC:6851` (`SensorFamily` not declared). CONFIRMED (run here: `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude
-DAPERTARCORE_HAS_LIBCAMERA=0`).

The tested sketch is `sketch/camera/ModeLadder.hpp` (283 lines). Its parts:

| Part | What | CameraController supplies |
| --- | --- | --- |
| `Rung {width, height, bits, clearHdr, threshold}`; `Ladder {enabled, rampReady, rungs}` | data | |
| `RungState {valid, usable, modeCeiling}` | what Core knows now | `valid`: the sanitiser keeps the mode in uncompressed cDNG. `usable`: it keeps it in the current format and compression. `modeCeiling`: the sanitiser's FPS for the mode at 280 requested |
| `rungCeiling(r, s)` | `threshold > 0 ? min(threshold, modeCeiling) : modeCeiling`; 0 when not usable. One number per rung, in and out of takes | |
| `ladderCeiling(l, s)` | the highest rung ceiling | |
| `chooseRung(l, s, target)` | first usable rung whose ceiling ≥ target − 0.0005; else the usable rung with the highest ceiling; −1 if none | |
| `parseRungs`, `rungsText` | `3840x2160:16:hdr:25,3840x2160:12:sdr` | |
| `validate` | errors and warnings (§3.7) | |
| `label`, `classLabel` | `4K Clear HDR 16-bit`, `HDR16` | |
| `toJson` | the `mode_ladder` reply | the pool |
| `fileText`, `parseFile` | `mode_ladder.conf` | |

The host test covers your ladder (1 → rung 1, 24 → 1, 25 → 1, 25.001 → 2, 50 → 2, 60 → 2), lossless (top 30), lossy (rung 1
unusable → rung 2), Cinemate's invariant from `ff59dd8` ("no reachable request outruns the mode it lands in", 0.5 … 50 in
0.5 steps), the refusals, the warnings, the file round trip, the JSON quoting. CONFIRMED (28 of 28 pass here).

### 3.2 The chooser's rules

- Upper bound inclusive: 25 → rung 1, 25.001 → rung 2. Any rung may run any FPS below its ceiling; the ranges are a preference.
- Target = `fps`, or the ladder ceiling when Ramp-ready **and** `fps_ramp` are both on (R). Leaving Speed Ramp on does not arm R.
- One rule for every FPS path, because every one ends in `CameraController::setFps` (§1.2). Cinemate lesson (r2 "What to avoid" 9).
- The ladder is asked about the FPS that will be commanded, after the rung's clamp (Cinemate `ff59dd8`).
- Active = enabled, not photo mode, a raw video format (cDNG any compression, MLV), at least one usable rung.
- In a take nothing is chosen. The running rung's ceiling caps the request (Q3: the threshold, not the mode's own ceiling).
- Off the ladder (the running mode is not a rung, `ladder_rung = 0`): the next FPS pick moves onto it.

### 3.3 Where each setting lives

| Setting | File | Owner | Per recording format? |
| --- | --- | --- | --- |
| `max_fps` (build maximum) | `apertar-hardware.conf` `[camera]` (first existing of `hardwareConfigCandidatePaths()`, `App:4285-4303`) | Core reads, WebUI Config panel edits | no |
| The ladder: `enabled`, `ramp_ready`, `rungs` | new `~/.config/apertar-core/mode_ladder.conf` (same XDG rule as `camera_settings.conf`, `CC:357-368`) | Core only | no: one ladder per camera |
| `fps_ramp`, `fps_ramp_keep_exposure`, mode, FPS | `camera_settings.conf`, `profile.<format>.` keys (`CC:650-663`, `:735-738`, `:809-810`) | Core | yes |
| T35 value lists | `~/.config/CinePi/UI.conf` `[General]` (README §3.1) | Core and touch UI | no |

Why not `UI.conf` for the ladder: Core reparses that file on every `readSharedUiSettings()` (`App:1665-1672`) and the touch
UI's `camera/*` keys there are placeholders only (`CB:906`). The hot `setFps` path must not read a file. CONFIRMED. Why not the
format profiles: `setRecordingFormat` swaps the whole profile (`CC:9351-9364`), so a ladder there would differ between cDNG
and MLV. CONFIRMED.

### 3.4 `mode_ladder.conf`

```ini
# Apertar mode ladder (T34). Core writes this file; edit it in the WebUI (Settings > Record > Mode Ladder).
enabled=true
ramp_ready=false
rungs=3840x2160:16:hdr:25,3840x2160:12:sdr
```

Rung text: `WIDTHxHEIGHT:BITS:hdr|sdr[:FPS]`, rungs joined by `,` (not `;`: a bare `;` ends the shell command when the text
is typed after `core.py`; `core.py` sends the value as a JSON string, `tools/core.py:6-8`, and Core reads a quoted string whole,
`CP:62-118`). CONFIRMED. A broken file loads as "ladder off" (sketch `parseFile`). Written with `settingsFile::atomicWrite`
(`SF:36-58`) after a successful apply, under the controller lock. The fsync is small next to the reconfigure that the same call
holds the lock for.

### 3.5 Commands

| Command | Fields | OK reply | Refused |
| --- | --- | --- | --- |
| `get_mode_ladder` | none | `"mode_ladder":{…}` with the pool | never |
| `set_mode_ladder` | any of `rungs` (string), `enabled`, `ramp_ready` (`true`/`false`), `dry_run` (`true`) | `"mode_ladder":{…}` + `settingsBody` (the camera may have changed rung) | in a take (except `dry_run`); parse errors; §3.7 errors. `dry_run=true` never saves and returns `errors` and `warnings` |
| `set_fps` | unchanged | unchanged; the reply's `fps` is the accepted one | unchanged |
| `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` | unchanged | unchanged | while the ladder is active (§3.7) |
| `apply_preset` | unchanged | unchanged | a Favorite that names a mode the ladder would not pick for its FPS (Q10) |
| `help` | | lists the two new names (`App:9681`) | |

`mode_ladder` object (from the sketch's `toJson`):

```json
{"enabled":true,"ramp_ready":false,"rungs_text":"3840x2160:16:hdr:25,3840x2160:12:sdr","ceiling":50,"running_rung":1,
 "rungs":[{"width":3840,"height":2160,"bits":16,"clear_hdr":true,"label":"4K Clear HDR 16-bit","class":"HDR16",
           "usable":true,"mode_ceiling":25,"threshold":25,"ceiling":25,"from":0},
          {"width":3840,"height":2160,"bits":12,"clear_hdr":false,"label":"4K SDR 12-bit","class":"SDR12",
           "usable":true,"mode_ceiling":50,"threshold":0,"ceiling":50,"from":25}],
 "pool":[{"width":3840,"height":2076,"bits":12,"clear_hdr":false,"label":"3840x2076 SDR 12-bit","class":"SDR12",
          "usable":true,"mode_ceiling":50}],
 "errors":[],"warnings":["Rung 1 -> 2 changes 4K Clear HDR 16-bit to 4K SDR 12-bit: the look changes between takes."]}
```

The pool = the probe's modes (`CameraController::sensorModes()`, `CC:10191-10195`), mapped to Core's identity, deduplicated,
each with its state in the current format. With `APERTAR_SENSOR_PROBE=0` the pool is empty; the editor then says "Sensor probe
off: add modes with core.py" (rungs still validate through the sanitiser). No second mode list.

### 3.6 State fields

Five derived fields, never persisted (the pattern of `exposureCompensationAvailable`, filled in `settings()` `CC:10171-10179`
and `emitSettingsEventLocked()` `CC:10407-10414`, never written by the persister). In all three JSON writers: `settingsEvent`
(`CC:141-200`, touch UI push), `settingsBody` (`App:179-235`, replies and `get_state`), `buildWebStateJson` (`App:7850-`,
WebUI poll). CONFIRMED writers.

| Field | Meaning | Patrik's ladder |
| --- | --- | --- |
| `fps_max` (T33) | highest FPS `set_fps` accepts **outside** a take. Ladder active: the ladder ceiling. Else the mode's ceiling | 50 in both rungs, in and out of takes |
| `fps_take_max` (T34) | highest FPS a take in the current mode reaches. On a rung: its ceiling. Else the mode's ceiling | 25 in rung 1, 50 in rung 2 |
| `ladder_active` | §3.2 | true |
| `ladder_rung` | 1-based running rung, 0 = the mode is not a rung | 1 or 2 |
| `ladder_ramp_ready` | R is choosing (Ramp-ready and `fps_ramp` on, ladder active) | |

Neither ceiling changes at record start (the mode does not change then), so no new settings events are needed at
`startRecording`/`stopRecording` (they emit recording events only, `CC:9840`, `:10095`). CONFIRMED.

| Who | Uses |
| --- | --- |
| PCF pot and `fps_up`/`fps_down` | `fps_max`: the list does not change at record start, so the knob keeps its meaning. In a rung-1 take a turn to 50 is clamped to 25 by Core, as today (`CC:9105-9113`) |
| WebUI pills, Speed Ramp targets, touch UI picker | `recording ? fps_take_max : fps_max` |
| FORMAT line, WebUI "Frame rate" line | class from `clear_hdr` + `raw_bit_depth` (both UIs already have them: `QML:357`, `:454`; Web snapshot), `≤` `fps_take_max`, `RAMP` from `ladder_ramp_ready` |
| Mode controls | greyed while `ladder_active` |

### 3.7 Refusals, warnings, messages

| When | Kind | Message |
| --- | --- | --- |
| A rung does not parse | error | `"3840x2160:14:sdr": size, bits (10, 12, 16) or hdr\|sdr not understood.` |
| A rung is not a mode of this sensor | error | `Rung 2: 4K SDR 16-bit is not a mode of this sensor.` |
| A mode twice | error | `Rung 2 repeats rung 1.` |
| Written thresholds do not rise | error | `Thresholds must rise down the list: Rung 2 (20 fps) is not above rung 1 (25 fps).` |
| More than 8 rungs; none at all | error | `At most 8 rungs.` / `Add at least one rung.` |
| A rung cannot run in this format | warning, skipped | `Rung 1 (4K Clear HDR 16-bit) cannot run in this format; it is skipped.` (lossy DNG, `RC:76-78`) |
| Threshold above the mode's ceiling here | warning | `Rung 2 stops at 30 fps here, not 50.` (lossless) |
| A rung that adds nothing | warning | `Rung 3 is never used: an earlier rung already reaches 50 fps.` |
| Class or size changes between rungs | warning | `Rung 1 -> 2 changes 4K Clear HDR 16-bit to 4K SDR 12-bit: the look changes between takes.` |
| A manual tuning file and a class change (CC adds it) | warning | `A manual tuning file is set; it is used for both classes.` (`CC:6114-6140`) |
| `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` while active | refusal | `The Mode Ladder picks the sensor mode from the FPS. Turn it off (Settings > Record > Mode Ladder) to choose a mode by hand.` |
| `set_mode_ladder` in a take | refusal | `Stop recording before changing the mode ladder.` |
| A Favorite that names another mode | refusal | `This Favorite records 4K SDR 12-bit at 24 fps; the Mode Ladder runs 24 fps in 4K Clear HDR 16-bit. Turn the ladder off to load it, or save the Favorite again.` |
| The stepper hits the rung ceiling in a take | journal | `fps ramp stopped: 25 fps is the ceiling of ladder rung 1 (4K Clear HDR 16-bit) in a take` |
| A pill click clamped in a take | WebUI toast, from the reply | `Rung 1 (HDR16) stops at 25 fps in a take.` The WebUI compares requested and accepted FPS; no Core field |
| An off-take rung switch fails | reply error | libcamera's error; recovery kept the old rung (F4) |

### 3.8 Ways it could look half-done, and why they cannot

| Case | Why it cannot happen |
| --- | --- |
| A format switch with a profile in another mode: two restarts | `setRecordingFormat` rewrites `next` before its one `applySettingsLocked` (`CC:9379`) |
| `ok:false` after the first half of a change stuck | no function applies twice; `setModeLadder` restores the old ladder when its single apply fails |
| A rollback lands in a different mode | the ladder is only in the App's `apply_preset` handler, never inside `applyCapturePreset` |
| The pot changes speed at record start | `fps_max` does not change then |

---

## 4. Implementation plan, file by file

Order = build order. Line numbers are on the tip trees above. **T33 moves them**; use the search string. Risk: **high** = in
`CameraController.cpp` (no host compile) and on a path every FPS change takes; **medium** = `CameraController.cpp`, rarely
taken path; **low** = host-checkable (header with its test, `ApertarCoreApp.cpp` with `g++ -fsyntax-only`, the WebUI with
`node --check`, the touch UI with a Qt build).

### Part 0: T33, the ceilings (prerequisite; the plan's Part 1, accepted by both critics, with one change)

| # | File:line @`119d0bb` | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 0.1 | `CC:2784` | `Clear HDR doubles VMAX` | SDR: `sensorLimitKnown ? 60.0 : 30.0`; Clear HDR unchanged | medium |
| 0.2 | `CC:2718-2721` | `Filled once by the startup probe` | `std::atomic<double> buildMaximumFps{0.0};` (`<atomic>` already at `CC:32`) | medium |
| 0.3 | `CC:2805` | `return probed ? std::min(table, *probed) : table;` | `min(…, buildMaximumFps)` when > 0 | medium |
| 0.4 | `Hdr:88`, new body after `setFpsRamp` (`CC:9733`) | `bool setFpsRamp(bool enabled, bool keepExposure);` | `void setBuildMaximumFps(double)`; off-take re-sanitise once | medium |
| 0.5 | after `App:4303` | `std::vector<std::filesystem::path> hardwareConfigCandidatePaths()` | `cameraMaxFpsFromHardwareConfig()`: first existing file, `[camera]`, `max_fps`, inline `#` stripped, 0..280 | low |
| 0.6 | before `App:6972`; after `App:7317` | `if (!camera_.start(options_.mediaRoot`; `saveHardwareConfigFile(request.body` | apply at start and after a Config save | low |
| 0.7 | `App:4325` | `std::string defaultHardwareConfigTemplate()` | `[camera]` block | low |
| 0.8 | `Types:133` (after) | `bool fpsRampKeepExposure = false;` | `double fpsMax = 0.0;` (derived) | low |
| 0.9 | `CC:10171-10179`, `:10407-10414` | `CaptureSettings result = settings_;`, `void CameraController::emitSettingsEventLocked()` | fill `fpsMax` = sanitiser at 280 | medium |
| 0.10 | `CC:189`, `App:215`, `App:8045` | `"fps_ramp\":"` | `fps_max` in the three writers | low (CC line trivial) |
| 0.11 | `App:1183` | `const double maxFps = maximumPcfFpsForSettings(settings, sensorName);` | use `settings.fpsMax` when > 0. **Changed from plan v1:** `fps_max` is the off-take value and does not change at record start (critiques 4 / 5) | low |
| 0.12 | `Web:5032`, `Web:8845` | `let max = maximumSupportedFpsForSnapshot(snapshot);`, `snapshot.fps_ramp_keep_exposure = source.fps_ramp_keep_exposure;` | use `snapshot.fps_max`; merge `fps_max` and `clear_hdr` from replies (today no `clear_hdr` merge, CONFIRMED) | low |
| 0.13 | `CBh:39`, `:87`, `:284`; `CB:1368`; `QML:814` | `Q_PROPERTY(double h264MaxFps`, `if (state.contains(QStringLiteral("fps_ramp")))`, `var max = root.maximumSupportedFpsForResolution(root.resolution)` | `fpsMax` property, parse, use | low |

T33 must say: `max_fps=50` also caps 1080p and the 3840 and 1920 crops (60 today, `CC:2786-2790`) and H.264 at 50. CONFIRMED
consequence (code critique Missing 5).

Check after T33 (Pi): `get_state` shows `"fps_max":50` in 4K SDR 12-bit and `25` in 4K Clear HDR 16-bit; `set_fps value=60` in
4K SDR leaves 50.

### Part A: T34 Core

| # | File:line @`119d0bb` | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| A1 | new `src/camera/ModeLadder.hpp` | | types, `rungCeiling`, `ladderCeiling`, `chooseRung` (sketch lines 1-87) | low (host test §2-3) |
| A2 | same | | `parseRungs`, `number`, `rungsText` | low (test §1) |
| A3 | same | | `validate` | low (test §4) |
| A4 | same; KB `working/tools/mode_ladder_test.cpp` | | `PoolEntry`, `toJson`, `fileText`, `parseFile`; the test file | low (test §5-6) |
| A5 | `Types:133` (after) | `bool fpsRampKeepExposure = false;` | derived `double fpsTakeMax = 0.0; bool ladderActive = false; uint32_t ladderRung = 0; bool ladderRampReady = false;` | low |
| A6 | `Hdr:5`; `Hdr:88`; `Hdr:115`; `Hdr:177` | `#include "util/RecordingDropWarning.hpp"`, `bool setFpsRamp(`, `std::vector<SensorMode> sensorModes() const;`, `bool rampTakeChanged_ = false;` | `#include "camera/ModeLadder.hpp"`; public `setModeLadder(…)`, `modeLadderJson()`, `applyLadderToPreset(CaptureSettings &, bool namesMode)`; private `ladder::Ladder modeLadder_;`, the five helpers of A8; `applyFpsStepLocked` gains `const CaptureSettings *rung = nullptr` | low (App's host check sees the header) |
| A7 | after `CC:368`; `CC:8923` | `std::filesystem::path persistedSettingsPath()`; `settings_ = loadPersistedCaptureSettings(formatSettings_, stillSettings_);` | `modeLadderPath()` (same XDG rule, `mode_ladder.conf`); load with `ladder::parseFile` in the constructor | medium |
| A8 | new, after `restoreFpsAfterRampLocked` (`CC:9179`) | `void CameraController::restoreFpsAfterRampLocked()` | `ladderStatesLocked(base)`, `ladderActiveForLocked(base)`, `ladderRewriteLocked(next)`, `fillLadderFieldsLocked(out)`, `ladderLabel(settings)`. Code below | **high** |
| A9 | `CC:9105-9118`; `CC:9121-9158` | `CaptureSettings requested = settings_;` inside `setFps`; `bool CameraController::applyFpsStepLocked(` | rewrite before the sanitiser; in-take rung cap; `applyFpsStepLocked(…, rung)` reconfigures into the rung. Code below | **high** |
| A10 | after `CC:9050`, `:9529`, `:9565` | `Resolution changes are blocked while recording.` and the two siblings | `if (ladderActiveForLocked(settings_)) { setErrorLocked(kLadderOwnsMode); return false; }` | low |
| A11 | `CC:9743-9746`; `CC:9371-9379`; `CC:9283`/`:9294`; `CC:8961-8972` | `next.fpsRampKeepExposure = keepExposure;`; `next = supportedRecordingSettings(next);` in `setRecordingFormat`; `restoreModeGeometryLocked(next);` in `setStillExposureMode`; `settings_ = session_->currentSettings();` in `start` | one rewrite before each single apply: `setFpsRamp` (`requiresReconfigure = changed`), `setRecordingFormat`, `setStillExposureMode` when leaving photo mode (code critique Missing 3); `start`: a guard after the session is up, logged, rare (a hand-edited file) | medium |
| A12 | new, before `applyCapturePreset` (`CC:10231`) | `bool CameraController::applyCapturePreset(` | `setModeLadder`, `modeLadderJson`, `applyLadderToPreset`, the pool from `sensorModes()` | medium |
| A13 | `CC:10174-10177`; `CC:10409-10411`; `CC:189-190` | `CaptureSettings result = settings_;`; `settings_.exposureCompensationAvailable = simulateCamera_`; `"fps_ramp\":"` | `fillLadderFieldsLocked(result)` / `(settings_)`; the five fields in `settingsEvent` | low |
| A14 | after `App:9659`; `App:9681` | `if (command.name == "list_sensor_modes") {`; `\"set_fps_ramp\",\"ramp_fps\",` | handlers `get_mode_ladder`, `set_mode_ladder` (strings and booleans only, F16); help list | low |
| A15 | `App:215-216`, `App:8045-8046` | `"fps_ramp_keep_exposure\":"` (twice) | `fps_take_max`, `ladder_active`, `ladder_rung`, `ladder_ramp_ready` | low |
| A16 | `App:8692`, `App:8951`; `App:9329` | `if (target == "resolution") {`; `fps is this mode's limit` | resolution pot and step: return when `cameraSettings.ladderActive` (no "Hardware input action failed" spam, code critique Missing 7); stepper wording with the ladder | low |
| A17 | before `App:11055` | `if (!camera_.applyCapturePreset(presetSettings, [&] {` | `namesMode` = `cameraRawBitDepth`, `cameraResolutionWidth` or `cameraResolution` present (`App:10871-10886`); `if (!camera_.applyLadderToPreset(presetSettings, namesMode)) return errorReply(…)` | low |

The two high-risk steps, as code to type (A8 and A9; names as on the tip):

```cpp
// T34: what the ladder knows about each rung, in the format and compression of `base`.
std::vector<ladder::RungState> CameraController::ladderStatesLocked(const CaptureSettings &base) const
{
    const SensorFamily family = (!simulateCamera_ && session_) ? session_->sensorFamily() : SensorFamily::Unknown;
    const auto keeps = [&](CaptureSettings probe, const ladder::Rung &rung) {
        probe.photoModeEnabled = false;
        probe.resolution = Resolution{ rung.width, rung.height };
        probe.rawBitDepth = rung.bits;
        probe.clearHdr = rung.clearHdr;
        probe.fps = 280.0;                                   // ask for the most; the sanitiser answers the ceiling
        const CaptureSettings kept = sanitizeSettingsForSensor(probe, family);
        const bool same = kept.resolution.width == rung.width && kept.resolution.height == rung.height &&
            kept.rawBitDepth == rung.bits && kept.clearHdr == rung.clearHdr && !unsupportedRecordingSettings(kept);
        return std::make_pair(same, kept.fps);
    };
    std::vector<ladder::RungState> states;
    for (const auto &rung : modeLadder_.rungs) {
        CaptureSettings reference = base;                    // uncompressed cDNG: a mode of this sensor at all?
        reference.recordingFormat = RecordingFormat::Cdng;
        reference.cdngCompression = CdngCompression::Uncompressed;
        const bool valid = keeps(reference, rung).first;
        const auto [usable, ceiling] = keeps(base, rung);
        states.push_back({ valid, valid && usable, ceiling });
    }
    return states;
}

// T34: put the rung for next's FPS (or the top rung when ramp-ready) into next, before the caller's
// one apply. True when that changes next's mode. Never in a take: rungs change between takes.
bool CameraController::ladderRewriteLocked(CaptureSettings &next) const
{
    if (recording_ || !ladderActiveForLocked(next))
        return false;
    const auto states = ladderStatesLocked(next);
    const bool rampReady = modeLadder_.rampReady && next.fpsRampEnabled;
    const double target = rampReady ? ladder::ladderCeiling(modeLadder_, states) : next.fps;
    const int index = ladder::chooseRung(modeLadder_, states, target);
    if (index < 0)
        return false;
    const ladder::Rung &rung = modeLadder_.rungs[static_cast<size_t>(index)];
    const bool changed = next.resolution.width != rung.width || next.resolution.height != rung.height ||
        next.rawBitDepth != rung.bits || next.clearHdr != rung.clearHdr;
    next.resolution = Resolution{ rung.width, rung.height };
    next.rawBitDepth = rung.bits;
    next.clearHdr = rung.clearHdr;
    next.fps = std::min(next.fps, ladder::rungCeiling(rung, states[static_cast<size_t>(index)]));
    return changed;
}
```

`ladderActiveForLocked(base)` = `modeLadder_.enabled && !base.photoModeEnabled && !isProcessedVideoFormat(base.recordingFormat)
&& chooseRung(modeLadder_, ladderStatesLocked(base), 0.0) >= 0`. `fillLadderFieldsLocked(out)`: the mode ceiling (sanitiser at
280) into `fpsMax` and `fpsTakeMax`; when active, `fpsMax` = ladder ceiling, and the rung that matches `settings_` gives
`ladderRung` and `fpsTakeMax`; `ladderRampReady` = `rampReady && settings_.fpsRampEnabled`.

In `setFps` (`CC:9105-9118`), the T34 lines:

```cpp
    CaptureSettings requested = settings_;
    requested.fps = fps;
    const bool rungChange = ladderRewriteLocked(requested);  // T34: outside a take the FPS picks the rung
    requested = sanitizeSettingsForSensor(requested, sensorFamily);
    double effectiveFps = requested.fps;
    if (recording_ && ladderActiveForLocked(settings_)) {   // T34: one ceiling per rung, also in a take
        CaptureSettings fields = settings_;
        fillLadderFieldsLocked(fields);
        if (fields.ladderRung > 0)
            effectiveFps = std::min(effectiveFps, fields.fpsTakeMax);
    }

    if (!rungChange && std::abs(settings_.fps - effectiveFps) < 0.0001) {
        lastError_.clear();
        emitSettingsEventLocked();
        return true;
    }
    return applyFpsStepLocked(effectiveFps, rampingTake, /*commit=*/!rampingTake, rungChange ? &requested : nullptr);
```

In `applyFpsStepLocked`, after `next.fps = effectiveFps;` (`CC:9146`): when `rung` is set, copy its resolution, bit depth and
Clear HDR into `next`, log the ladder line, and call `applySettingsLocked(next, rung != nullptr, commit)` instead of
`(next, false, commit)` (`CC:9154`). The shutter policy above it stays as it is.

**Gate A** (§5 of the tutorial): host test passes; `g++ -fsyntax-only` of `ApertarCoreApp.cpp` passes; Pi build; `core.py`
checks: `set_mode_ladder rungs=… dry_run=true` returns your warning, `set_fps value=30` moves to rung 2 (`get_state`:
`"clear_hdr":false`, `"ladder_rung":2`), `set_clear_hdr enabled=true` is refused, a take at 24 in rung 1 with `ramp_fps to=50`
stops at 25.

### Part B: T34 WebUI

| # | File:line @`119d0bb` | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| B1 | after `Web:2951` | `<p class="settings-card-copy" id="settingsSpeedRampRange"></p>` then `</div>` | new `<div class="settings-card">` Mode Ladder: head + `online-pill` `settingsModeLadderValue`; pills `settingsModeLadderOptions` (Off/On); list `settingsModeLadderList`; add row `settingsModeLadderAddSelect` + button; `settingsModeLadderWarnings`; Save / Revert; `settingsModeLadderNote` | low |
| B2 | after `Web:2926` | `<div class="pill-grid" id="settingsSpeedRampOptions"></div>` | Ramp-ready label + pills `settingsSpeedRampReadyOptions` + copy "Speed Ramp takes start in the top rung, so they can reach N fps." | low |
| B3 | near `Web:1887` | `.preset-row {` | `.ladder-row` (preset row look), `.ladder-handle { touch-action: none; cursor: grab; user-select: none; min-width: 44px; min-height: 44px; }`, `.ladder-row.dragging`, `.ladder-row.drop-target`, `.ladder-threshold { width: 6em; }`, `.pill-switch` (amber outline); rows wrap at phone width | low |
| B4 | `Web:4239` | `speedRampReturnFps: 0,` | `ladderServer: null, ladderDraft: null, ladderDirty: false, ladderDrag: null, ladderCheckTimer: 0,` | low |
| B5 | after `renderSpeedRamp` ends (`Web:5079-5156`) | `function renderSpeedRamp(snapshot, fpsOptions) {` | `fetchModeLadder()`, `renderModeLadder(snapshot)`, `renderLadderRows()`, `moveLadderRung(from, to)`, `checkLadderDraft()` (debounced `dry_run`, shows Core's `errors`/`warnings`), `saveModeLadder()` | low |
| B6 | same place | | `installLadderDrag(handle, row, index)`: pointer events with `setPointerCapture`, `pointercancel` (plan v1 sketch, kept) | low |
| B7 | `Web:5032` | `let max = maximumSupportedFpsForSnapshot(snapshot);` (T33 changed it) | `max = snapshot.recording ? snapshot.fps_take_max : snapshot.fps_max` when > 0 | low |
| B8 | `Web:2544`; `Web:10059-10065` | `<span>Frame rate</span>`; `buildOptionButtons("fpsOptions"` | class line (`HDR16 · ≤25`); tint pills above `fps_take_max` off-take with the ladder on; while a switching `set_fps` runs, the line says "Switching to 4K SDR 12-bit…"; after the reply, a toast when the accepted FPS is below the requested one | low |
| B9 | `Web:9897-9898`; `Web:10102`; `Web:10135-10138` | `setElementDisabled("settingsRecordResolutionSelect", false);`; `buildOptionButtons("resolutionOptions"`; `buildOptionButtons("settingsRawBitDepthOptions"` | disabled while `snapshot.ladder_active`, copy "Mode Ladder on: the FPS picks the mode." | low |
| B10 | `Web:5098`; `Web:8845`; `Web:8880` | `setText("settingsSpeedRampRange"`; `snapshot.fps_ramp_keep_exposure = source.fps_ramp_keep_exposure;`; `case "set_fps_ramp":` | the "Ramp to 50 is not possible in this take" line; merge the four T34 fields; `case "set_mode_ladder":` optimistic patch of `ladder_ramp_ready`/`ladder_active` | low |
| B11 | `Web:10149`; `Web:11579` | `renderSpeedRamp(snapshot, fpsOptions);`; `settingsSpeedRampTargetSelect").addEventListener` | `renderModeLadder(snapshot);`; listeners for Add, Save, Revert, threshold `input`, Ramp-ready | low |

The redraw rule (operator critique 10, fixed): the rows are rebuilt **only** after `fetchModeLadder` returns, after Save or
Revert, and after a local edit (move, add, remove, threshold). The 1 s poll (`Web:11800`) never rebuilds rows; it only updates
the pill, the note, the disabled states and Ramp-ready. So typing a threshold never loses focus. The draft is refetched when
the Record panel opens and after a save. Two browsers editing at once: last Save wins (single operator; Q not needed).

**Gate B**: `node --check` of the page script and the Chromium run against a mocked `/api/state` and `/api/command`, as T32
(seven states plus: drag a rung, type a threshold, a refused save). Then the Pi.

### Part C: T34 touch UI

| # | File:line @`34499f1` | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| C1 | `CBh:39`, `:87`, `:149`, `:318`; `CB:1368-1369` | `Q_PROPERTY(double h264MaxFps`, `double h264MaxFps() const`, `void fpsChanged();`, `bool m_fpsRamp = false;`, `m_fpsRamp = state.value(QStringLiteral("fps_ramp"))` | properties `fpsTakeMax`, `ladderActive`, `ladderRampReady` with one `ladderChanged` signal; parse in `applyCoreState` | low |
| C2 | `CB:1036-1049` | `commandName == QStringLiteral("apply_preset");` | add `set_fps` and `set_mode_ladder` to the 10 s list: both can reconfigure now (F15) | low |
| C3 | `CB:280`, `:288` | `setFps(formatFpsValue(fpsValue));` | use the accepted FPS from `fpsReply` (`fpsReply.value("fps")`) for the display and the shutter (code critique 5) | low |
| C4 | new `Q_INVOKABLE` next to `applyFps` (`CBh:113`) | `Q_INVOKABLE bool applyFps(const QString &displayValue);` | `applyModeLadderSwitch(const QString &name, bool on)`: `set_mode_ladder {name: "true" or "false"}` | low |
| C5 | `QML:522-526` | `readonly property string formatDisplaySubtext:` | prefix `HDR16 · ≤25 · ` from `clearHdrActive`, `rawBitDepthValue`, `fpsTakeMax`; `· RAMP` when `ladderRampReady`; amber via the InfoLine's colour when R is on | low |
| C6 | `QML:814` | `var max = root.maximumSupportedFpsForResolution(root.resolution)` (T33 changed it) | `recording ? fpsTakeMax : fpsMax` | low |
| C7 | `QML:1214`, `QML:1242`; `SP:633`; `SP:3162`, `SP:3237` | `function applyResolutionValue(resolutionValue) {`, `function applyQuickResolution(resolutionValue) {`, `function applyRecordResolutionValue(resolutionValue) {`, `InlineDropdownField {` (resolution, bit depth) | guard + `showRecordWarning` (`QML:1515` pattern) in the three functions; `fieldEnabled: … && !ladderActive` on the two fields; one caption | low |
| C8 | `SP:3237` area | `label: root.proresClipFormat ? "Profile" : "Bit Depth"` | two rows: Mode Ladder On/Off, Ramp-ready On/Off (C4); "Ladder off. Camera stays in 4K SDR 12-bit." after Off | low |
| C9 | `QML:2926-2929` | `root.controlBridge.applyFps(v)` | when it returns false: `showRecordWarning("FPS Not Changed", lastError, …)` | low |

Known and kept: a rung switch from the touch picker freezes the touch screen until the reply, because `applyFps` waits on the
GUI thread (`CB:1084`). `set_clear_hdr` from the touch UI does the same today. CONFIRMED. M7 measures how long.

**Gate C**: the whole touch UI built with Qt on the host (as T32), then the Pi: M7.

### Size (PROBABLE, counted like the critics: T31 added 367 lines to `CC`, T32's WebUI block 143)

| Part | Lines | Compiled before the Pi? |
| --- | --- | --- |
| T33 | ~150 | all but ~40 in `CC` |
| A: `ModeLadder.hpp` + test | 283 + 86 (sketch, CONFIRMED count) | yes, host test |
| A: `CC` + `Hdr` | ~270 | **no** |
| A: `Types` + `App` | ~80 | yes (`g++ -fsyntax-only`) |
| B: WebUI | ~330 | `node --check` + mocked Chromium |
| C: touch UI | ~120 | Qt host build |
| **T34 total** | **~1,100** (+86 test) | ~270 lines wait for the Pi |

A separate fix of the no-libcamera build (33 errors on the tip) would let those 270 lines be syntax-checked on the host too.
Not part of T34; worth its own small task.

---

## 5. Tutorial T34 outline (KB format)

File: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T34 mode-ladder.md`. Frontmatter as in `tutorials/README.md`
(`datum`, `kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext: T34 mode-ladder`, `typ: digital anteckning`). Ends with
`#CINEMATE` and `#APERTAR`.

### 0. Header

- Title: **T34. The mode ladder: the FPS picks the sensor mode, 4K Clear HDR 16-bit up to 25 and 4K SDR 12-bit up to 50, and
  Speed Ramp takes that start in the top rung**
- Status line: written; needs T31, T32 and T33 applied; refs at Core `119d0bb` / UI `34499f1` (run `tutorial.py refs T34`
  after T33, lines move). Host test passed in the cloud; `CameraController.cpp` not compiled (libcamera).
- **You will learn**: (1) why a mode switch is a full restart of the camera and why it never happens in a take; (2) how to put
  pure logic in a header you can test on any computer; (3) why every function that changes the mode must choose the rung before
  its one apply; (4) how a UI list can change meaning under a knob (the pot), and how two ceilings avoid it.
- **Risk**: Core and UI rebuild and restart. Off by default: nothing changes until you turn the ladder on. A wrong rung costs
  one reconfigure; the recovery keeps the old mode. Undo: `core.py set_mode_ladder enabled=false`, or delete
  `~/.config/apertar-core/mode_ladder.conf`, or `git revert`. **Time:** 3 sessions: Part A 3 h, Part B 2 h, Part C 1.5 h.

### 1. The problem

- Today one mode per take, and you choose it by hand. Your shot: 24 → 50 → 24 at 4K. Clear HDR 16-bit stops at 25 (T32).
- Show: `core.py set_fps value=30` in 4K Clear HDR 16-bit → `"fps":25`. Show the probe: `core.py list_sensor_modes | grep 3840x2160`
  (SDR 60, Clear HDR 30). T33 already lets 4K SDR follow the probe, clamped by `max_fps=50`, so 50 exists, but only in SDR.
- Expected after T34: pick 30 → SDR 12-bit at 30; Ramp-ready → the whole ramp in SDR 12-bit.

### 2. How this part works

Diagram (text): FPS request → `setFps` → (off-take) `ladderRewriteLocked` → `chooseRung` (header) → sanitiser → same mode:
controls only / other mode: one reconfigure. In a take: the rung's ceiling caps, T31 steps.

Reading assignments: `CC:9074-9158` (`setFps`, `applyFpsStepLocked`), `CC:10287-10352` (`applySettingsLocked`, the recovery),
`CC:2799-2806` and `:2835-2881` (ceilings, sanitiser), `CC:9327-9380` (`setRecordingFormat` swaps the whole profile),
`App:8607-8613` and `:8682-8690` (the pot maps by list position), `App:9290-9337` (the stepper stops at a limit). Name the
Cinemate lessons: `ff59dd8` (choose for the FPS you will command; a take's value is not your target), `2c8cf81` (show a
substitution; re-derive the ceiling on every toggle).

### 3. Find it yourself (Pi, before the change)

**3.1 Where is a mode chosen today?** `grep -n 'Resolution changes are blocked\|Raw bit depth changes are blocked\|Clear HDR changes are blocked' ~/ApertarCore/src/camera/CameraController.cpp`.
Prediction: three lines, one per mode setter (ten setters in all say "blocked while recording"). Question: why does nothing pick
a mode from the FPS? Answer: no code does; a mode is three settings (`Types:124-176`).

**3.2 What does a class switch cost?** Run M1 (§6, preview only). Prediction: several hundred ms per switch. Question: what
does `start()` rebuild? Answer: the CameraManager, the WDR state and the tuning (`CC:6145-6152`, `:6222-6237`).

**3.3 What stops a ramp in a take?** `grep -n "fps is this mode's limit" ~/ApertarCore/src/ApertarCoreApp.cpp`. Question: what
makes the stepper stop? Answer: the accepted FPS did not move (`App:9327-9331`).

**3.4 Why would the pot jump?** `grep -n -A3 'size_t analogPresetIndex' ~/ApertarCore/src/ApertarCoreApp.cpp`. Question: the
list {24, 25, 30, 50} becomes {24, 25}; where does a knob at one third land? Answer: on 24 (`llround(0.33 × 1)` = 0).

**3.5 Which modes could be rungs?** `python3 -I ~/apertar-kb/working/tools/core.py list_sensor_modes`. Question: why does the
16-bit Clear HDR mode say 3840x2200? Answer: the readout is taller; Core crops to 3840x2160 (`CC:394-399`, `:2860-2863`).

### 4. Make the change

Part A, Core (build gate after 4.17):

| Step | What (plan row) | **Check** (one each) |
| --- | --- | --- |
| **4.1** | `ModeLadder.hpp` part 1: types, ceilings, chooser (A1) | `grep -c 'inline int chooseRung' src/camera/ModeLadder.hpp` → 1 |
| **4.2** | part 2: parse and print (A2) | `grep -c 'inline bool parseRungs' …` → 1 |
| **4.3** | part 3: validate (A3) | `grep -c 'inline void validate' …` → 1 |
| **4.4** | part 4: reply, file; copy the test to `~/apertar-kb/working/tools/` and run it (A4) | `./mode_ladder_test` ends `all ok` |
| **4.5** | `Types.hpp` derived fields (A5) | `grep -c 'bool ladderActive = false;' include/apertar/core/Types.hpp` → 1 |
| **4.6** | header (A6) | `grep -c 'ladder::Ladder modeLadder_;' src/camera/CameraController.hpp` → 1 |
| **4.7** | file path and load (A7) | `grep -c 'mode_ladder.conf' src/camera/CameraController.cpp` → 3 (XDG, home and temp branches, as `persistedSettingsPath`) |
| **4.8** | the helpers (A8) **risky** | `grep -c 'bool CameraController::ladderRewriteLocked' …` → 1 |
| **4.9** | `setFps` and `applyFpsStepLocked` (A9) **risky** | `grep -c 'ladderRewriteLocked(requested)' …` → 1 |
| **4.10** | refusals (A10) | `grep -c 'kLadderOwnsMode' …` → 4 |
| **4.11** | one rewrite before each apply (A11) | `grep -c 'ladderRewriteLocked(' …` → 6 (definition, `setFps`, four here; 8 after 4.12) |
| **4.12** | `setModeLadder`, JSON, presets (A12) | `grep -c 'bool CameraController::setModeLadder' …` → 1 |
| **4.13** | fill the fields, settings event (A13) | `grep -c 'fps_take_max' src/camera/CameraController.cpp` → 1 |
| **4.14** | App handlers and help (A14) | `grep -c 'command.name == "set_mode_ladder"' src/ApertarCoreApp.cpp` → 1 |
| **4.15** | App state fields (A15) | `grep -c 'ladder_ramp_ready' src/ApertarCoreApp.cpp` → 2 |
| **4.16** | pot, step, stepper wording (A16) | `grep -c 'cameraSettings.ladderActive' src/ApertarCoreApp.cpp` → 2 |
| **4.17** | presets (A17); host check `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude src/ApertarCoreApp.cpp` | `grep -c 'applyLadderToPreset' src/ApertarCoreApp.cpp` → 1 |

Part B, WebUI (build gate after 4.27; every Check on `src/web/WebControlPage.cpp`):

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| **4.18** | the Mode Ladder card HTML (B1) | `grep -c 'id="settingsModeLadderList"'` → 1 |
| **4.19** | Ramp-ready pills in the Speed Ramp block (B2) | `grep -c 'id="settingsSpeedRampReadyOptions"'` → 1 |
| **4.20** | CSS (B3) | `grep -c '.ladder-handle {'` → 1 |
| **4.21** | page state (B4) | `grep -c 'ladderDraft: null,'` → 1 |
| **4.22** | render, rows, moves, dry run, save (B5) | `grep -c 'function renderModeLadder\|function checkLadderDraft\|function saveModeLadder'` → 3 |
| **4.23** | drag with pointer events (B6) | `grep -c 'function installLadderDrag'` → 1 |
| **4.24** | the two ceilings (B7) | `grep -c 'fps_take_max'` → 1 or more |
| **4.25** | class line, tint, toast (B8) | `grep -c 'id="fpsClassLabel"'` → 1 |
| **4.26** | greyed mode controls (B9) | `grep -c 'Mode Ladder on: the FPS picks the mode.'` → 1 or more |
| **4.27** | Speed Ramp line, merges, listeners (B10, B11); then T32 4.10's `node --check` | `grep -c 'case "set_mode_ladder":'` → 1 |

Part C, touch UI (build gate after 4.36; paths under `~/ApertarUI`):

| Step | What (plan row) | **Check** |
| --- | --- | --- |
| **4.28** | bridge properties and parsing (C1) | `grep -c 'm_ladderActive' src/ApertarControlBridge.hpp` → 1 |
| **4.29** | 10 s reply time for `set_fps` and `set_mode_ladder` (C2) | `grep -c 'commandName == QStringLiteral("set_mode_ladder")' src/ApertarControlBridge.cpp` → 1 |
| **4.30** | accepted FPS from the reply (C3) | `grep -c 'fpsReply.value(QStringLiteral("fps"))' src/ApertarControlBridge.cpp` → 1 |
| **4.31** | `applyModeLadderSwitch` (C4) | `grep -c 'applyModeLadderSwitch' src/ApertarControlBridge.hpp` → 1 |
| **4.32** | FORMAT line (C5) | `grep -c 'ladderRampReady' qml/CameraPage.qml` → 1 or more |
| **4.33** | picker cut in a take (C6) | `grep -c 'fpsTakeMax' qml/CameraPage.qml` → 2 or more (4.32 and here) |
| **4.34** | greyed mode controls (C7) | `grep -c 'Mode Ladder on: the FPS picks the mode' qml/SettingsPage.qml` → 1 or more |
| **4.35** | Settings rows (C8) | `grep -c 'applyModeLadderSwitch(' qml/SettingsPage.qml` → 2 |
| **4.36** | warning on a failed pick (C9) | `grep -c '"FPS Not Changed"' qml/CameraPage.qml` → 1 |

### 5. Build, deploy, test

- **5.1 Gate A** (Core): build, restart (Patrik), then `core.py`: `set_mode_ladder rungs=3840x2160:16:hdr:25,3840x2160:12:sdr
  dry_run=true` → one warning; the same without `dry_run` plus `enabled=true`; `set_fps value=24` → `"ladder_rung":1`;
  `set_fps value=30` → `"clear_hdr":false,"raw_bit_depth":12,"ladder_rung":2` and one `mode ladder:` journal line;
  `set_clear_hdr enabled=true` → the refusal; a take at 24 in rung 1 with `ramp_fps to=50 seconds=5` → stops at 25 with the
  ladder wording; `set_mode_ladder ramp_ready=true` → rung 2 at 24; a take with `ramp_fps to=50` → 50.
- **5.2 Gate B** (WebUI): the card, drag on the phone, a threshold typed while the poll runs (focus stays), Save, a refused save
  (falling thresholds), the class line, the tint, greyed resolution and bit depth.
- **5.3 Gate C** (touch UI): FORMAT line in both rungs and with RAMP; picker cut in a take; greyed items with the caption; the
  two Settings rows; M7.
- **5.4 The shot**: your 24 → 50 → 24 ramp with Ramp-ready, judged as in T31 §5.1-5.2 (one clip, `FrameRate` 24, WAV real
  time, slow-motion stretch), plus `dropped_queue_full=0`.

### 6. Commit

Core, three commits on `cinemate-port`: "camera: mode ladder logic in a libcamera-free header" (`ModeLadder.hpp`), "camera: the
FPS picks the sensor mode between takes (mode ladder)" (CC, Hdr, Types, App), "web: Mode Ladder card and Ramp-ready". UI: "ui:
mode ladder state, class on the FORMAT line, mode controls greyed". KB: `working/tools/mode_ladder_test.cpp`. Fork-log rows.
Push only when you decide.

### 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `mode_ladder_test` FAIL lines | a typo in 4.1-4.4 | the failing line names the rule |
| Pi build error in `CameraController.cpp` | expected risk: not compiled before the Pi | the error names the line; most likely a member name in A8/A9 |
| `set_fps value=30` stays in Clear HDR | ladder off, or the probe off (4K SDR then tops at 30, F5) | `get_mode_ladder`; `journalctl -u apertar-core -b \| grep 'sensor probe'` |
| Two blinks for one format switch | a rewrite after an apply | 4.11: the rewrite goes **before** `applySettingsLocked` |
| Pot jumps at record start | the pot uses `fps_take_max` | 0.11: the pot uses `fps_max` |
| Typing a threshold loses focus | rows redrawn from the poll | 4.22: rows redraw only on fetch, save, revert and local edits |
| Touch screen freezes ~1 s on a pick | a rung switch (known, F15) | M7 measures it |
| `cached DMA allocation unavailable` after many switches | heap fragmented (M8) | restart Core before a Clear HDR take; report it |
| Undo | | `core.py set_mode_ladder enabled=false`; `git revert`; delete `mode_ladder.conf` |

### 8. What you learned, going further

- A mode is three settings; a class switch is a full camera restart; Core never does it in a take.
- Pure logic in a header can be tested anywhere; the camera file supplies numbers.
- One apply per change. Choose first, apply once.
- Exercise: add a third rung `3840x2076:12:sdr` above 50 with `max_fps=0` and see the warning "never used" go away.
- Further: design B (switch in the take) after M1/M2/M6; the no-libcamera build fix.

### 9. Sources

Core `119d0bb` and UI `34499f1` lines as in §4; `sketch/camera/ModeLadder.hpp`; cinemate `d6cc93e`
`src/module/dynamic_resolution.py:426-502`, `cinepi_controller.py:904-930`; KB `lessons/hardware-log.md`, `working/ramp-answer.md`,
`working/ramp-ladder/*`.

### Tutor block (anchors checked here: each string occurs once in its file at `119d0bb` / `34499f1`)

`tutorial.py` splits a check on ` | ` and keeps it only with exactly three fields (`TP:119-123`), so no check below pipes
one command into another. (T32's own `check 5.1` has four fields and is skipped; worth a one-line fix in the T32 note.)

```
%% tutor
ref core src/camera/CameraController.cpp 9074 bool CameraController::setFps(double fps, bool takeOnly)
ref core src/camera/CameraController.cpp 9121 bool CameraController::applyFpsStepLocked(double effectiveFps, bool rampingTake, bool commit)
ref core src/camera/CameraController.cpp 9048 setErrorLocked("Resolution changes are blocked while recording.");
ref core src/camera/CameraController.cpp 9527 setErrorLocked("Raw bit depth changes are blocked while recording.");
ref core src/camera/CameraController.cpp 9563 setErrorLocked("Clear HDR changes are blocked while recording.");
ref core src/camera/CameraController.cpp 9745 next.fpsRampKeepExposure = keepExposure;
ref core src/camera/CameraController.cpp 9379 return applySettingsLocked(next, requiresReconfigure);
ref core src/camera/CameraController.cpp 9294 return applySettingsLocked(next, photoMode != settings_.photoModeEnabled);
ref core src/camera/CameraController.cpp 8956 if (!simulateCamera_ && !session_->start(settings_, &lastError_)) {
ref core src/camera/CameraController.cpp 8923 settings_ = loadPersistedCaptureSettings(formatSettings_, stillSettings_);
ref core src/camera/CameraController.cpp 357 std::filesystem::path persistedSettingsPath()
ref core src/camera/CameraController.cpp 10171 CaptureSettings CameraController::settings() const
ref core src/camera/CameraController.cpp 10407 void CameraController::emitSettingsEventLocked()
ref core src/camera/CameraController.cpp 10191 std::vector<CameraController::SensorMode> CameraController::sensorModes() const
ref core src/camera/CameraController.hpp 88 bool setFpsRamp(bool enabled, bool keepExposure);
ref core src/camera/CameraController.hpp 177 bool rampTakeChanged_ = false;
ref core include/apertar/core/Types.hpp 133 bool fpsRampKeepExposure = false;
ref core src/ApertarCoreApp.cpp 1183 const double maxFps = maximumPcfFpsForSettings(settings, sensorName);
ref core src/ApertarCoreApp.cpp 8682 if (target == "fps") {
ref core src/ApertarCoreApp.cpp 9329 fps is this mode's limit
ref core src/ApertarCoreApp.cpp 9659 if (command.name == "list_sensor_modes") {
ref core src/ApertarCoreApp.cpp 9681 \"set_fps_ramp\",\"ramp_fps\",
ref core src/ApertarCoreApp.cpp 10805 CaptureSettings presetSettings = camera_.settings();
ref core src/ApertarCoreApp.cpp 11055 if (!camera_.applyCapturePreset(presetSettings, [&] {
ref core src/web/WebControlPage.cpp 2950 <p class="settings-card-copy" id="settingsSpeedRampRange"></p>
ref core src/web/WebControlPage.cpp 2926 <div class="pill-grid" id="settingsSpeedRampOptions"></div>
ref core src/web/WebControlPage.cpp 1887 .preset-row {
ref core src/web/WebControlPage.cpp 4239 speedRampReturnFps: 0,
ref core src/web/WebControlPage.cpp 5079 function renderSpeedRamp(snapshot, fpsOptions) {
ref core src/web/WebControlPage.cpp 5032 let max = maximumSupportedFpsForSnapshot(snapshot);
ref core src/web/WebControlPage.cpp 2544 <span>Frame rate</span>
ref core src/web/WebControlPage.cpp 10059 buildOptionButtons("fpsOptions"
ref core src/web/WebControlPage.cpp 9897 setElementDisabled("settingsRecordResolutionSelect", false);
ref core src/web/WebControlPage.cpp 8845 snapshot.fps_ramp_keep_exposure = source.fps_ramp_keep_exposure;
ref core src/web/WebControlPage.cpp 10149 renderSpeedRamp(snapshot, fpsOptions);
ref core src/web/WebControlPage.cpp 11579 settingsSpeedRampTargetSelect").addEventListener
ref ui src/ApertarControlBridge.cpp 280 setFps(formatFpsValue(fpsValue));
ref ui src/ApertarControlBridge.cpp 1049 commandName == QStringLiteral("apply_preset");
ref ui src/ApertarControlBridge.cpp 1368 if (state.contains(QStringLiteral("fps_ramp")))
ref ui src/ApertarControlBridge.hpp 318 bool m_fpsRamp = false;
ref ui src/ApertarControlBridge.hpp 113 Q_INVOKABLE bool applyFps(const QString &displayValue);
ref ui qml/CameraPage.qml 522 readonly property string formatDisplaySubtext:
ref ui qml/CameraPage.qml 1214 function applyResolutionValue(resolutionValue) {
ref ui qml/CameraPage.qml 1242 function applyQuickResolution(resolutionValue) {
ref ui qml/CameraPage.qml 2928 root.controlBridge.applyFps(v)
ref ui qml/SettingsPage.qml 633 function applyRecordResolutionValue(resolutionValue) {
ref ui qml/SettingsPage.qml 3239 label: root.proresClipFormat ? "Profile" : "Bit Depth"
check 3.1 | grep -c 'Resolution changes are blocked\|Raw bit depth changes are blocked\|Clear HDR changes are blocked' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^3$
check 3.3 | grep -c "fps is this mode's limit" /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.1 | grep -c 'inline int chooseRung' /home/pi/ApertarCore/src/camera/ModeLadder.hpp | ^1$
check 4.2 | grep -c 'inline bool parseRungs' /home/pi/ApertarCore/src/camera/ModeLadder.hpp | ^1$
check 4.3 | grep -c 'inline void validate' /home/pi/ApertarCore/src/camera/ModeLadder.hpp | ^1$
check 4.4 | grep -c 'inline std::string fileText' /home/pi/ApertarCore/src/camera/ModeLadder.hpp | ^1$
check 4.5 | grep -c 'bool ladderActive = false;' /home/pi/ApertarCore/include/apertar/core/Types.hpp | ^1$
check 4.6 | grep -c 'ladder::Ladder modeLadder_;' /home/pi/ApertarCore/src/camera/CameraController.hpp | ^1$
check 4.8 | grep -c 'bool CameraController::ladderRewriteLocked' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.9 | grep -c 'ladderRewriteLocked(requested)' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.12 | grep -c 'bool CameraController::setModeLadder' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.14 | grep -c 'command.name == "set_mode_ladder"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.17 | grep -c 'applyLadderToPreset' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 4.18 | grep -c 'id="settingsModeLadderList"' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^1$
check 4.23 | grep -c 'function installLadderDrag' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^1$
check 4.28 | grep -c 'm_ladderActive' /home/pi/ApertarUI/src/ApertarControlBridge.hpp | ^1$
check 4.32 | grep -c 'ladderRampReady' /home/pi/ApertarUI/qml/CameraPage.qml | ^[1-9]
check 4.33 | grep -c 'fpsTakeMax' /home/pi/ApertarUI/qml/CameraPage.qml | ^([2-9]|[1-9][0-9])$
check 4.36 | grep -c '"FPS Not Changed"' /home/pi/ApertarUI/qml/CameraPage.qml | ^1$
check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | "ladder_rung":[12]
%%
```

---

## 6. Measurements on the Pi first

Shorthand `K=~/apertar-kb/working/tools`. Core running. Lines marked "Patrik" need `sudo`. Order: M0, M3, M1, M6, M5 before any
T34 code; M2 optional; M4 after T33; M7, M8 after T34.

**M0. T31 on the Pi, as a ladder-sized ramp take, plus a Resolve conform** (no code change; 3840x2076 SDR 12-bit is allowed 60
today, `CC:2786-2787`; 598 MB/s at 50)

```bash
K=~/apertar-kb/working/tools
df -h /media/RAW | tail -1                                  # drive fill: test at the fill of a shoot day (HL:386)
dmesg | grep -E 'link up' | tail -1                         # 5.0 GT/s = Gen 2, 8.0 GT/s = Gen 3
python3 -I $K/core.py set_record_format value=cdng
python3 -I $K/core.py set_cdng_compression value=none       # lossless is capped at 30 (CC:2559-2580)
python3 -I $K/core.py set_clear_hdr enabled=false
python3 -I $K/core.py set_raw_bit_depth value=12
python3 -I $K/core.py set_resolution width=3840 height=2076
python3 -I $K/core.py set_fps_ramp enabled=true shutter=angle
python3 -I $K/core.py set_fps value=24
python3 -I $K/core.py get_state | grep -oE '"(resolution|fps|raw_bit_depth|clear_hdr|fps_ramp)":[^,]*'   # 3840x2076, 24, 12, false, true
T1=$(date '+%F %T'); python3 -I $K/core.py record_start
sleep 10; python3 -I $K/core.py ramp_fps to=50 seconds=5    # 26 steps up
sleep 65; python3 -I $K/core.py ramp_fps to=24 seconds=5    # 60 s at 50: the longest stretch you plan (Q11)
sleep 15; python3 -I $K/core.py record_stop
sleep 6; journalctl -u apertar-core --since "$T1" --no-pager | grep -E 'recording clip|fps ramp (stats|stopped)|dropped_queue_full|drop\[(queue-full|capture-gap)\]' | tail -8
```

Prediction: `changes=52 base_fps=24 min_fps=24 max_fps=50`. Drops at 50: UNCONFIRMED; at Gen 2 the 12-frame queue (~143 MB) fills
in about 0.9 s at 598 out and 437 in (PROBABLE arithmetic), so expect `drop[queue-full]` lines. Then in the clip folder:
`exiftool -FrameRate -TimeCodes` on the first, a middle and the last DNG (24 everywhere), `fps-ramp.txt` with 52 lines, and
Resolve: import at 24, one clip, the 50 stretch at about half speed, the WAV real time, RecRun TC continuous. Write the result
into `lessons/hardware-log.md`. Decides: whether T31 is a base to build on.

**M3. Can SDR 12-bit hold 50 for 3 minutes?** (no code change, 3840x2076; after T33 repeat at 3840x2160 = M4)

```bash
python3 -I $K/core.py set_fps_ramp enabled=false            # elapsed-time numbering again: a drop leaves a hole (CC:8018)
python3 -I $K/core.py set_fps value=50
bash $K/takes.sh 1 180                                      # pass: files=9000 missing=0, dropped_queue_full absent
```

Rules: `missing > 0` with `peak_queue=12/12` → storage-bound (Gen 2, drive fill); `dropped_gap_estimate > 0` with a low queue
→ back-end-bound (F10). For the second case, once with more camera buffers:

```bash
printf '[Service]\nEnvironment=APERTAR_RAW_CAMERA_BUFFERS=8\n' | sudo tee /etc/systemd/system/apertar-core.service.d/zz-ladder-buffers.conf   # Patrik
sudo systemctl daemon-reload && sudo systemctl restart apertar-core                                                                        # Patrik
bash $K/takes.sh 1 180
sudo rm /etc/systemd/system/apertar-core.service.d/zz-ladder-buffers.conf && sudo systemctl daemon-reload && sudo systemctl restart apertar-core   # Patrik: undo
```

Prediction: "unknown; storage-bound at Gen 2, possibly back-end-bound at Gen 3". Decides `max_fps`.

**M1. How long does a class switch blink?** (preview only)

```bash
python3 -I $K/core.py get_state | grep -oE '"cdng_preview_color_profile":"[^"]*"'   # Standard = one CameraManager; a log profile = two (CC:6222-6237)
python3 -I $K/core.py set_resolution width=3840 height=2160
python3 -I $K/core.py set_clear_hdr enabled=true; python3 -I $K/core.py set_raw_bit_depth value=16; python3 -I $K/core.py set_fps value=25
t() { a=$(date +%s%N); python3 -I $K/core.py "$@" | grep -o '"ok":[a-z]*'; echo "$1 $2: $(( ($(date +%s%N) - a) / 1000000 )) ms"; }
for i in 1 2 3; do
  t get_state                                   # the round trip alone (Python start-up included): subtract it
  t set_clear_hdr enabled=false; sleep 4        # HDR16 -> SDR12, the ladder's way up
  t set_clear_hdr enabled=true;  sleep 4        # SDR12 -> HDR12
  t set_raw_bit_depth value=16;  sleep 4        # HDR12 -> HDR16
done
journalctl -u apertar-core -b -o short-precise --no-pager | grep -E 'camera configured|tuning|recovery' | tail -12
```

Run it once with the Standard preview profile and once with the profile you shoot with. The ladder's way down (SDR12 → HDR16)
is one apply after T34; M7 times it with `set_fps`. The reply returns when requests are queued, before the first frame, so this
is a lower bound. Prediction: several hundred ms. Decides: the blink, a pot settle delay, and B's floor.

**M2 (optional). The hole in frames from libcamera's timestamps.** As plan v1 §5 M2 (a `zz-ladder-timing.conf` drop-in with
`LIBCAMERA_LOG_LEVELS=RPI:0`, one `set_clear_hdr enabled=false`, the largest gap between CFE timestamps, undo). Decides B only.

**M6. Look and exposure** (two takes by hand). Grey card and a highlight, ISO 800, 180°, 25 fps: 5 s in 4K Clear HDR 16-bit,
then `set_clear_hdr enabled=false` and 5 s in 4K SDR 12-bit. In Resolve, one timeline: the grey card level (% of white) and
where the highlight clips, in both. Decides: whether Ramp-ready (ramp takes all SDR) costs anything you care about (Q11), and
whether the UI must warn of a level change at the switch (ISO maps to the same gain in both classes, `CC:2141-2143`).

**M5. The lowest FPS and how late a step lands there** (preview, then one take)

```bash
python3 -I $K/core.py set_fps value=1; python3 -I $K/core.py get_state | grep -o '"fps":[0-9.]*'     # 1?
python3 -I $K/core.py set_fps_ramp enabled=true shutter=angle; python3 -I $K/core.py set_fps value=2
T1=$(date '+%F %T'); python3 -I $K/core.py record_start; sleep 20
python3 -I $K/core.py set_fps value=5; sleep 20; python3 -I $K/core.py set_fps value=12; sleep 10
python3 -I $K/core.py record_stop; sleep 6
journalctl -u apertar-core --since "$T1" --no-pager | grep -E 'fps ramp: (frame=|[0-9.]+ ->)' | tail -6   # lag_frames per change
```

Core accepts any FPS above 0 (`CC:9097-9100`); whether the IPA follows 1-2 fps is UNCONFIRMED. A step lands about N+2 frames
late (T31 line 23; N = 4-10), so about 3-6 s at 2 fps (PROBABLE). Decides Q6 and the low values in T35.

**M4 (after T33).** `set_resolution width=3840 height=2160`, `set_clear_hdr enabled=false`, `set_fps value=60` → `get_state`
shows 50; then M3 at 3840x2160 (622 MB/s).

**M7 (after T34). Touch picker across a switch.** Tap 50 on the touch UI picker in rung 1.

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'mode ladder|camera configured' | tail -4      # one ladder line
journalctl -u apertar-ui-direct -b --no-pager | grep -iE 'timeout|error' | tail -5               # no reply timeout (C2)
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -oE '"(fps|shutter_us|iso|ladder_rung)":[0-9.]*'   # 50, 10000 at 180°, ISO kept, 2
```

Then read ISO and WB from the first DNGs of a take after a switch (`exiftool -ISO -AsShotNeutral`), not only `shutter_us`
(Cinemate `f884716` lost controls after a switch; in Core they ride the start request, PROBABLE fine).

**M8 (after T34). Soak: does the cached heap survive many switches?**

```bash
grep -iE 'cma' /proc/meminfo                                                   # before
for i in $(seq 1 15); do python3 -I $K/core.py set_fps value=30 >/dev/null; sleep 3; python3 -I $K/core.py set_fps value=24 >/dev/null; sleep 3; done
grep -iE 'cma' /proc/meminfo                                                   # after
journalctl -u apertar-core -b --no-pager | grep -c 'cached DMA allocation unavailable'   # 0 is the pass (CC:7414)
bash $K/takes.sh 1 30                                                          # then a Clear HDR 16-bit take: missing=0
```

(`takes.sh` steps bit depth 12 → 16 before each take; with the ladder on those steps are refused and silent, which is fine
here because the ladder already put rung 1 in place at 24.)

---

## 7. Risks, open questions, rejected critic points

### 7.1 Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Rung 2 at 50 not sustainable (storage at Gen 2; drive fill at Gen 3; maybe the back end) | PROBABLE (F8-F10) | M0, M3 first; `max_fps` = what held |
| R2 | Drops in a ramp take leave no file-number gap | CONFIRMED (F14) | dropped-frame flag at stop (`CC:3911-3912`, `QML:2593`); M0 reads the journal counters |
| R3 | T31/T32 have never run on the Pi; a T31 defect would look like a ladder defect | CONFIRMED (README §2) | M0 before any T34 code |
| R4 | ~270 lines in `CameraController.cpp/.hpp` only compile on the Pi | CONFIRMED (33 errors in the no-libcamera build) | logic in the host-tested header; the CC glue is short and given as code (§4) |
| R5 | Each switch back to rung 1 reallocates 8 × 16.9 MB cached buffers; a fragmented heap falls back silently to slow buffers | CONFIRMED path, effect UNCONFIRMED (F13) | M8; count the fallback later if M8 fails |
| R6 | Lifting the 4K SDR cap also lets 4K SDR go to 60 without the ladder; `max_fps=50` also caps HD and crops | CONFIRMED | T33 says so |
| R7 | Probe off → 4K SDR stays 30 → ladder top 30, empty pool | CONFIRMED (`CC:2799-2806`, `:10191-10195`) | `fps_max` shows it; the editor says "Sensor probe off" |
| R8 | A manual tuning file is used for both classes | PROBABLE (`CC:6114-6140`) | validation warning |
| R9 | A touch rung switch freezes the touch screen for the reconfigure | CONFIRMED (F15) | M7; same as today's Clear HDR item |
| R10 | Ramp-ready left on: every take SDR 12-bit | PROBABLE | own switch, default Off; amber `SDR12 · ≤50 · RAMP`; Q9 |
| R11 | A pot parked near a boundary flips on a touch: a double blink off-take | PROBABLE (`GAI:473`, deadband 32) | 300 ms settle only if M1 shows a long blink |
| R12 | HDMI monitor shows no class | UNCONFIRMED where (`formatInfoValue`, `ui-map.md` §4) | later; the class string can be reused |
| R13 | B (later): hole, split, look cut, recovery only testable on the Pi | PROBABLE | only after M1/M2/M6 |

### 7.2 Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Is A + R enough: a ramp take that goes above 25 is SDR 12-bit from its first frame? | yes; B later only if M1/M2/M6 say so |
| Q2 | While the ladder is on, refuse manual resolution / bit depth / Clear HDR (greyed in both UIs)? | yes |
| Q3 | In a take, cap at the rung's threshold (one number per rung) or at the mode's own ceiling when the threshold is lower? | threshold |
| Q5 | Link for 50: Gen 2 (stable, 437 MB/s) or Gen 3 (818 MB/s burst, drop history)? | after M3 |
| Q6 | How low is "the lowest possible FPS" (1, 2, 5, 12)? | after M5; into T35's FPS list |
| Q9 | Ramp-ready: sticky until you turn it off, or for one take (clears at stop, then one reconfigure back after the drain)? | sticky. One take only adds a reconfigure (135 MB reallocation, R5) after every ramp take and a second apply at stop; say if you want it, it is about 15 lines |
| Q10 | A Favorite that names a mode the ladder would not pick for its FPS: refuse, or load it and turn the ladder off? | refuse with the message (§3.7). A Favorite with an FPS only follows the ladder |
| Q11 | Is a ramp shot in SDR 12-bit inside a Clear HDR 16-bit scene acceptable in the grade? How long do you hold 50? | M6 and M0 decide |
| Q12 | Numbering: T33 = build max, T34 = ladder, T35 = value lists (README §3.1 called the lists T33)? Or split T34's parts into T34/T35/T36? | T33/T34/T35 as in the header table |

Plan v1 questions no longer open: Q4 (Ramp-ready default) became Q9; Q7 (PCF resolution pot) is decided: ignored while the
ladder is on (A16); Q8 (frame numbering in a split clip) belongs to design B.

### 7.3 Critic points rejected or changed, and why

| Critic point | Decision | Why (evidence) |
| --- | --- | --- |
| Code 3: at boot, rewrite `settings_` before `session_->start` | rejected | Before the session starts the sensor family is Unknown (`CC:8833`, set at `:6250`), so the sanitiser cannot give a rung ceiling; and before the probe a 4K SDR rung reads 30, so a ladder with a crop rung would choose differently. A post-start guard stays, logged; it only fires after a hand edit, because every off-take switch is persisted |
| Code 3: call the rewrite in the App's `apply_preset` | changed | A Favorite that names a mode is refused instead (operator 8: a silent rewrite makes the Favorite lie). A Favorite with an FPS only is rewritten. Both before `applyCapturePreset`, never in its rollbacks |
| Code 4: keep `fps_max` = ladder ceiling in takes, for all UIs | changed | The pot uses `fps_max` (stable). The pickers use `fps_take_max` in a take (operator 5), so they never offer a value Core will clamp. Neither changes at record start, so no new events |
| Code 6: optional fallback counter in `get_state` | deferred | M8's journal grep answers it first |
| Code Missing 4: a static fallback mode list when the probe is off | rejected | A sixth copy of mode knowledge. The editor says "Sensor probe off"; rungs typed with `core.py` still validate |
| Code Missing 8: write `mode_ladder.conf` outside the controller lock | rejected | The same call holds the lock for a reconfigure of hundreds of ms; the fsync is small next to it, and it happens only on Save |
| Code 1: four tutorials | changed | T33 + one T34 in three parts with build gates; `tutorial.py` needs two-digit IDs (`TP:98`). Q12 offers the split |
| Operator 1: Ramp-ready one take only by default | changed to a question | Sticky is the default (Q9): one take only costs a reconfigure after every ramp take. The class is on screen in amber either way |
| Operator 2: tint the touch picker entries that switch class | deferred | `TopDropdownStat` options are plain strings (`QML:2919`); the FORMAT line shows `≤25` before the tap. The WebUI pills are tinted |
| Operator 3(c): `# dropped_queue_full=N dropped_gap=N` in `fps-ramp.txt` | rejected | Checked: a queue-full drop already sets the dropped flag (`CC:3911-3912`) shown at stop (`QML:2593`), and the recorder stop line prints the counters (`CC:3678`). It would be session code that runs only in ramped takes (`CC:8424`) |
| Operator 6: show "50 · not in this take" as a disabled entry in the target select | changed | A line under the block says it ("Ramp to 50 is not possible in this take: HDR16 stops at 25."). Same information, no change to `ensureSelectEntries` |
| Operator 10: "Changed elsewhere. Revert to load it." | rejected | The poll no longer carries the ladder, so rows never redraw from it; one operator, last Save wins |
| Operator Missing 4: a PCF action to arm Ramp-ready | deferred | The touch Settings rows give a way on the camera body; a hardware action can follow |
| Operator Missing 5: HDMI class string | deferred | R12 |
| Operator 16: hysteresis | deferred, as plan R4 | only if M1 shows a long blink |
