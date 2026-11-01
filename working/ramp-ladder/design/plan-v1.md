# T34 mode ladder: design v1 (with the T33 parts it needs: `max_fps`, `fps_max`)

2026-10-27, cloud session, designer pass. Read-only on every tree. Nothing built, nothing run on the Pi.

Trees read (all citations are at these commits unless a line says otherwise):

| Short name | File | Tree and commit |
| --- | --- | --- |
| `CC` | `src/camera/CameraController.cpp` | `scratchpad/tip-core` at `119d0bb` = GitHub `cinemate-port` `3c4f07d` + T31 (`5f38585`) + T32 (`cba1963`, `119d0bb`), local commits |
| `Hdr` | `src/camera/CameraController.hpp` | same |
| `App` | `src/ApertarCoreApp.cpp` | same |
| `Web` | `src/web/WebControlPage.cpp` | same |
| `Types` | `include/apertar/core/Types.hpp` | same |
| `CP` | `src/ipc/ControlProtocol.cpp` | same |
| `QML` | `qml/CameraPage.qml` | `scratchpad/verify2/home/ApertarUI` at `34499f1` = `dc471c1` + the two T32 UI patches |
| `CB`, `CBh` | `src/ApertarControlBridge.cpp` / `.hpp` | same UI tree |
| cinemate, cinepi-raw | | `d6cc93e`, `63a08d5` |
| KB | `lessons/hardware-log.md`, `working/*` | KB copy `scratchpad/verify3` at `8b655da` |
| brief | `working/ramp-ladder/README.md`, `r1-core.md`, `r2-cinemate.md` | `scratchpad/apertar-kb-speed-ramp-2026-10-27/kb` |

Labels: **CONFIRMED** = I opened the line (path:line at the commit above). **PROBABLE** = derived; the derivation is given.
**UNCONFIRMED** = not checked, or only the Pi can settle it.

Tutorial numbers follow the brief (README §3.1 T33 = value lists, §3.2 T34 = ladder). The T32 tutorial still says "Next: the
mode ladder (T33)" (T32 tutorial line 560). That line needs a fix when T34 is written.

---

## 0. Short answer

| Question | Answer |
| --- | --- |
| Recommended design | **A + R**: the ladder switches rungs **between takes** (A), and a **ramp-ready start** (R) makes a Speed Ramp take start in the rung that can reach the ramp's top. Patrik's 24 → 50 ramp then runs in 4K SDR 12-bit from the first frame, with no switch, no hole and no look change inside the take. |
| What A + R cannot do | Switch from Clear HDR 16-bit to SDR 12-bit **inside** one take. Only design B does that, at the cost of a frame hole, a clip split and a visible look change at the switch. |
| When to build B | Only if two Pi measurements say it is worth it: a Clear HDR → SDR reconfigure hole of about 200 ms or less (M1/M2), and Patrik accepts the look change between the two clips in Resolve (M6). B is a separate tutorial (T35). |
| First thing to measure | Whether 4K-wide SDR 12-bit uncompressed runs 50 fps at all on this rig (M3). Without it, rung 2 tops out lower and every design is moot above that. 622 MB/s is needed; Gen 2 measured 437 MB/s. |
| Ladder storage | A new Core-owned file `~/.config/apertar-core/mode_ladder.conf`. Not `UI.conf`, not `apertar-hardware.conf`, not inside the per-format camera profiles (§3.3). |
| Build maximum | `apertar-hardware.conf` `[camera] max_fps=50` (decided). Core clamps every path to it and publishes `fps_max` (§3.4). |
| Size | T33a (ceilings, `max_fps`, `fps_max`): about 150 lines across Core, WebUI and touch UI. T34 A + R: about 750 lines (Core ~330, WebUI ~380, UI ~40). B adds 500-800 lines in `CC`, which cannot be compiled off the Pi. All PROBABLE estimates. |

---

## 1. How it works for the operator

### 1.1 Where it lives

| Surface | What | Why there |
| --- | --- | --- |
| WebUI Settings → Record | New card **Mode Ladder**, right after the Recording format card (which ends at `Web:2951` with the T32 Speed Ramp block) | The ladder is a Record setting; it sits next to Speed Ramp, which it serves. CONFIRMED card end: `Web:2948-2951` (`id="settingsSpeedRampRange"` then `</div>`) |
| WebUI Camera settings pane (quick access) | Unchanged pills (`Web:2538-2560`, `id="fpsOptions"` at `:2546`). The "Frame rate" label gains a rung line, and the pills reach `fps_max` (50 off-take with the ladder on) | Patrik's item 10: the pane stays the field menu. Picking a pill is how he moves across a threshold |
| Touch UI | No editor. A rung tag in the FORMAT line, and the FPS picker reaches `fps_max` | The touch screen is for shooting; editing is a WebUI job (the brief, item 9) |
| Socket | `get_mode_ladder`, `set_mode_ladder`, `set_mode_ladder_enabled` | For `core.py` tests and the tutorial's checks |

### 1.2 The Mode Ladder card

```
+-- Mode Ladder ------------------------------------------ [On . rung 1 of 2] --+
| The FPS picks the sensor mode. Top rung first. Rungs change between takes.      |
| [ Off ] [ On ]                                                                  |
|                                                                                 |
| ::  1  4K 3840x2160 . Clear HDR 16-bit    up to [ 25  ] fps  [x] on   Up Down X |
|        serves: lowest - 25 fps        mode max 25                               |
| ::  2  4K 3840x2160 . SDR 12-bit          up to [     ] fps  [x] on   Up Down X |
|        serves: 25 - 50 fps            empty = mode max 50 (build max_fps)       |
|                                                                                 |
| Add a mode: [ 4K 3840x2076 . SDR 12-bit . max 50          v ] [ Add ]           |
| Speed Ramp takes start in: [ the rung for the current FPS            v ]        |
|                            [ rung 2 (4K SDR 12-bit), so they can reach 50 fps ] |
| Note: rung 1 -> 2 changes Clear HDR to SDR. The look changes between takes.     |
| [ Save ladder ] [ Revert ]                     Ladder ceiling: 50 fps           |
+---------------------------------------------------------------------------------+
```

| Part | Behaviour |
| --- | --- |
| Toggle Off / On | Sends `set_mode_ladder_enabled`. Greyed out during a take. Persists. Turning it on can switch the camera to the rung that serves the current FPS at once (one reconfigure, preview blinks). |
| Rung row | Handle `::`, number, mode label, threshold field, enabled checkbox, Up, Down, Remove. Under it: the range it serves and the mode's ceiling **as Core computes it now** (this format, this compression, the build max). |
| Drag and drop | Pointer events on the handle (mouse, touch and pen through one API). The handle has `touch-action: none`, so a finger drag does not scroll the page. HTML5 drag events are not used: touch browsers do not fire them reliably (PROBABLE, browser behaviour; not tested here). |
| Up / Down | Same move as a drop, one place at a time. The Favorites list already uses Up/Down buttons (`moveFavoriteItem`, `Web:6670-6689`; buttons built in `renderFavoritesPanel`, `Web:7481` onward). CONFIRMED. This is the fallback when dragging is awkward. |
| Threshold | Optional number. Empty = the mode's own ceiling. The ceiling is the highest FPS this rung serves; the next rung starts above it. |
| Enabled | Keeps a rung in the list but skips it (for example an HD fallback rung kept for later). |
| Add a mode | The pool is every probed sensor mode that Core accepts in the current format, minus the ones already in the ladder. From `get_mode_ladder` (§3.5), which maps the probe's raw sizes to Core's own mode identity (3840x2200 → 3840x2160 for 16-bit Clear HDR). |
| Speed Ramp takes start in | Ramp-ready (design R). "the rung for the current FPS" = off. The other entries are the enabled rungs' ceilings ("rung 2 … reach 50 fps"). Stored as `ramp_reach` (fps). |
| Save / Revert | Edits are a local draft. Save sends `set_mode_ladder`. The page polls `/api/state` once a second (`Web:11800`) and `renderSnapshot` rebuilds lists each time (Favorites: `Web:10385`, `innerHTML = ""` in `renderFavoritesPanel`). So the editor must not redraw its rows while a drag runs or while the draft has unsaved changes. CONFIRMED poll and rebuild; the guard is new. |
| During a take | Card read-only with "Stop recording to change the ladder." Core refuses the commands anyway. |

### 1.3 Validation

Core is the authority. The WebUI runs the same rules on the draft for instant feedback.

| Rule | Kind | Message (example) |
| --- | --- | --- |
| Every rung parses and is a mode of this sensor (size accepted by `validateResolution` `CC:10381-10399`; bit depth kept by `supportedRawBitDepthForSensor` `CC:2808-2833`; Clear HDR only at 3840x2160, `CC:2862-2863`) | refuse | "Rung 2: 3840x2160 SDR 16-bit is not a mode of this sensor." |
| No mode twice | refuse | "Rung 2 repeats rung 1." |
| Written thresholds rise down the list | refuse | "Thresholds must rise: rung 2 (20 fps) is not above rung 1 (25 fps)." |
| At least one rung enabled; at most 8 rungs | refuse | "Turn on at least one rung." |
| Threshold above the mode's ceiling in this format | warn, clamp | "Rung 2 stops at 30 fps in Lossless cDNG." (lossless IMX585 is capped at 30, `CC:2559-2580`, CONFIRMED) |
| A rung whose effective ceiling is not above the rung before it | warn, skipped | "Rung 3 is never used: rung 2 already reaches 50 fps." |
| Size or aspect changes between rungs | warn | "Rung 1 → 2 changes the framing (3840x2160 → 3840x1608)." Patrik's goal is to keep the resolution. |
| Clear HDR ↔ SDR or bit depth changes between rungs | warn | "Rung 1 → 2 changes Clear HDR 16-bit to SDR 12-bit: the look changes." |
| Format has no ladder (H.264, ProRes, stills, timelapse) | info | "Off in H.264: one mode per format." The ladder stays stored; it is just inactive. |

Format-dependent ceilings are warnings, not refusals, so a ladder saved in uncompressed cDNG stays valid after a switch to
Lossless; Core re-evaluates it live.

### 1.4 What the touch UI shows

| State | FORMAT line `sub` (`QML:522`, InfoLine `QML:3608-3610`) | FPS picker (`QML:2904-2934`, options `QML:503`) |
| --- | --- | --- |
| Ladder off | as today ("Uncompressed") | cut at `fps_max` (the mode's ceiling) |
| On, rung 1 of 2, off-take | "R1/2 · Uncompressed" | 24, 25, 30, 50 (cut at the ladder ceiling 50) |
| On, ramp-ready armed | "R2/2 ramp · Uncompressed" | 24 … 50 |
| On, in a take | the running rung | cut at the running rung's ceiling (25 in rung 1) |
| On, H.264 | as today | as today |

A refused manual mode change (quick-menu resolution) shows the existing warning card with Core's message
(`showRecordWarning` pattern, `QML:1515`). Today `applyResolutionValue` fails silently (`QML:1214-1222`, CONFIRMED).

### 1.5 Picking an FPS or ramping across a threshold

Patrik's ladder: rung 1 = 4K Clear HDR 16-bit up to 25, rung 2 = 4K SDR 12-bit up to 50.

**Outside a take (A and A + R behave the same unless ramp-ready is armed):**

| Action | What Core does | What he sees |
| --- | --- | --- |
| Picks 24 in rung 1 | Plain `set_fps` (no reconfigure) | Nothing else changes |
| Picks 30 or 50 from 25 | One reconfigure to rung 2 with the new FPS, shutter angle kept | Preview blinks for the reconfigure time (UNCONFIRMED, M1); FORMAT "R2/2"; bit depth reads 12-bit, Clear HDR off |
| Picks 25 from 50 | One reconfigure back to rung 1 | Preview blinks; "R1/2" |
| `ramp_fps to=50 seconds=5` from 24 in preview | Steps 25 (rung 1), then 26 switches to rung 2 (one reconfigure, the stepper waits on the controller lock), then 27 … 50 | One blink mid-ramp |
| Pot swept across 25/30 | Each crossing is one reconfigure | Risk: a jittery pot at the boundary reconfigures repeatedly. The pot has a deadband of 32 raw counts (`GroveAnalogInput.hpp:43`, `:58`, CONFIRMED) |
| Speed Ramp turned On with ramp-ready "reach 50" | Re-evaluates: the rung for max(FPS, 50) = rung 2 | Switches to SDR at once, at the current FPS (24 stays 24) |

**Inside a take:**

| Design | Requested FPS within the running rung | Requested FPS above it | At stop |
| --- | --- | --- | --- |
| A | T31 step (no reconfigure, not persisted) | Clamped to the running mode's ceiling. A `ramp_fps` stepper stops with a ladder message (§1.7). Nothing else happens. | T31 restores the take's start rate. The rung did not change. |
| A + R (take started in rung 2 because ramp-ready was armed) | 24 … 50 all inside rung 2 | Clamped at 50 | Back to the start rate, still rung 2 while ramp-ready stays armed |
| B | T31 step | Upward crossing splits the clip: close clip 1, reconfigure, open clip 2 in rung 2, keep stepping. **Never switches back down** in a take: rung 2 can run 24 too, so a ramp down stays in rung 2 (one hole per take, not two) | Restore the start rung and start rate: one reconfigure after the take |

Why the in-take cap is the **mode's** ceiling, not the rung's threshold: a threshold says where the ladder *prefers* the next
rung. In A no switch can happen in a take, so the best the camera can do is stay in the running mode as far as that mode goes.
For Patrik's rung 1 both numbers are 25. Open question Q3.

### 1.6 Files on the card

**A and A + R** (one take, one mode):

```
cDNG_26-10-27_C0007/
    cDNG_26-10-27_C0007_000000000.dng ... (count-based numbering under fps_ramp, T31)
    cDNG_26-10-27_C0007.wav            one real-time WAV (AudioRecordingSession.cpp:251 names it after the clip)
    fps-ramp.txt                       T31 log, plus one new header line: # mode=3840x2160 bits=12 clear_hdr=0
```

Folder naming is unchanged (`allocateClipFolder` `CC:4179-4222`, first free `_C####`). CONFIRMED. The new header line makes
the take's rung visible in the edit without the journal.

**B** (one take, two clips):

```
cDNG_26-10-27_C0007/        clip 1: Clear HDR 16-bit, frames 000000000-000000742
    ...dng, cDNG_26-10-27_C0007.wav (the whole take, real time), fps-ramp.txt (clip 1 events + a split line)
cDNG_26-10-27_C0007_R2/     clip 2: SDR 12-bit, frame numbers continue at 000000743
    ...dng, fps-ramp.txt (clip 2 events; "audio: ../cDNG_26-10-27_C0007/cDNG_26-10-27_C0007.wav offset_us=...")
```

The `_R2` suffix keeps clip 2 out of the `_C####` scan, so the next take is still C0008 (PROBABLE from `CC:4210-4218`, the scan
tests exact names). Split line in `fps-ramp.txt`: `split last_frame=742 first_frame=743 gap_us=... frames_at_rate=...
from=3840x2160/16/hdr to=3840x2160/12/sdr`.

### 1.7 Refusals and notices

| When | Reply / message |
| --- | --- |
| `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` while the ladder is active | "The mode ladder picks the sensor mode from the FPS. Turn it off (Settings → Record → Mode Ladder) to choose a mode by hand." |
| `set_mode_ladder` or `set_mode_ladder_enabled` during a take | "Stop recording before changing the mode ladder." |
| `set_fps` in a take above the running rung (A, A + R) | `ok`, FPS clamped (today's behaviour, `CC:9105-9113`), plus a `notice` field: "Rung 1 (4K Clear HDR 16-bit) stops at 25 fps in a take. The ladder changes rungs between takes; ramp-ready starts ramp takes in rung 2." The WebUI shows `notice` as a toast. |
| `ramp_fps` stepper hits the rung ceiling in a take | Journal: "fps ramp stopped: 25 fps is the ceiling of ladder rung 1 (4K Clear HDR 16-bit) in a take" (today: "… is this mode's limit", `App:9329`) |
| A rung switch off-take fails | `applySettingsLocked` recovery puts the previous mode back and replies with the libcamera error (`CC:10322-10336`, commit = true). CONFIRMED path |
| B: switch fails in a take | Back to the previous rung and continue capped; if that fails too, end the take cleanly with "Rung switch failed; the take ended at frame N." Never a "recording" that writes nothing (r1 Risks 1). |

---

## 2. Designs

### 2.1 Facts every design must respect

| # | Fact | Label and source |
| --- | --- | --- |
| F1 | Resolution, bit-depth and Clear HDR changes are refused during a take | CONFIRMED `CC:9047-9050`, `:9526-9529`, `:9562-9565` |
| F2 | A Clear HDR change always forces a full reconfigure, and a reconfigure is `stop()` + `start()` | CONFIRMED `CC:10291`, `CC:6358-6370` |
| F3 | `stop()` stops every recorder (gyro, H.264, ProRes, raw queue, audio, photo) and destroys the CameraManager | CONFIRMED `CC:6314-6319`, `:6351-6354` |
| F4 | `start()` sets WDR on the sensor subdev and builds a new CameraManager (retry loop) | CONFIRMED `CC:6145-6152` |
| F5 | Recovery after a failed reconfigure only runs with `commit = true`; otherwise state goes to Error | CONFIRMED `CC:10322-10337` |
| F6 | 4K SDR is capped at 30 in Core; the probe says 60 | CONFIRMED `CC:2784` (`return clearHdr && !sensorLimitKnown ? 25.0 : 30.0;`); probe 60: KB `working/sensor-capabilities.md:51` |
| F7 | 4K Clear HDR 16-bit is capped at 25 (T32) | CONFIRMED `CC:2781-2782` |
| F8 | Lossless cDNG on the IMX585 is capped at 30 at every size | CONFIRMED `CC:2559-2580` |
| F9 | 4K SDR 12-bit uncompressed at 50 fps ≈ 622 MB/s | PROBABLE arithmetic, 12.44 MB/frame (`working/ramp-mode-ladder.md` §3) |
| F10 | NVMe: 437 MB/s fio at PCIe Gen 2; 818 MB/s fio burst at Gen 3; Gen 3 is an overclock with a history of NVMe drops; the rig ran Gen 3 again on 2026-10-26/27 | CONFIRMED KB `lessons/hardware-log.md:317-323`, `:383`, `:309-311`, `:463` |
| F11 | No Core measurement of a reconfigure's duration exists. Cinemate's only figure is ~186 ms, inferred from a phase error in preview, without a manager rebuild | CONFIRMED absence (r2 §b.3; I found no timing line in the hardware log) |
| F12 | Cinemate never switches class mid-take: the in-take ceiling is pinned to the running class; a same-class switch splits the clip | CONFIRMED `cinemate/src/module/cinepi_controller.py:904-930`; `cinepi-raw/cinepi/cinepi_raw.cpp:68-76`, `:365-375` |
| F13 | The touch UI does not send `set_fps` or `set_resolution` on its own while the bridge exists | CONFIRMED `QML:1373-1376`, `:1557-1559` (both `return` when `root.controlBridge`). This settles r1 Risks 10 for Core-driven switches |
| F14 | The touch UI waits 3 s for a `set_fps` reply, 10 s for reconfigure commands | CONFIRMED `CB:1035-1052`. A `set_fps` that reconfigures needs the 10 s class |
| F15 | Socket commands carry scalar values only | CONFIRMED `CP:120-124` (a bare value ends at the first `,` or `}`). A ladder must travel as one string |

### 2.2 Design A: switch between takes; in a take the running rung's ceiling caps FPS

**Core, step by step:**

1. `setFps(fps)` off-take, ladder active: compute `target = fps` and the rung that serves it (first enabled rung whose ceiling
   ≥ target, §3.2).
2. Same mode as now → today's path (sanitise, `applyFpsStepLocked`), `CC:9101-9118`.
3. Different mode → `switchRungLocked`: copy `settings_`, set the rung's resolution, bit depth and Clear HDR, FPS =
   min(fps, rung ceiling), shutter by the same policy as `applyFpsStepLocked` (`CC:9127-9145`), then
   `applySettingsLocked(next, true, /*commit=*/true)`: one reconfigure, recovery on failure, persisted (the profile then
   holds a mode and FPS that agree with the ladder). The model for "one complete mode in one reconfigure" already exists:
   `applyCapturePreset` (`CC:10254`, "Apply the complete mode once"). CONFIRMED.
4. In a take: nothing new. The sanitiser clamps to the running mode (`CC:9105-9108`); T31 steps as before.
5. At stop: T31's `restoreFpsAfterRampLocked` (`CC:9162-9180`) restores the start rate through `applyFpsStepLocked`, not
   `setFps`, so no ladder evaluation and no reconfigure. CONFIRMED call chain (`CC:10090`, `:10115`, `:8990`).
6. Re-align (pick the rung for the current FPS) when: the ladder is turned on or saved, a raw format is selected, a preset is
   applied, Core starts, Speed Ramp is toggled (for R).

| Cost | Value |
| --- | --- |
| Frames lost in a take | 0 |
| Clip split | none |
| Look change in a take | none |
| What he loses | A ramp take started at 24 in rung 1 stops at 25 |
| Off-take cost | One reconfigure per threshold crossing (UNCONFIRMED duration, M1) |

**Failure modes:** reconfigure fails → previous mode restored (F5, commit = true). Probe off (`APERTAR_SENSOR_PROBE=0`) → 4K SDR
stays 30 (`CC:2799-2806` uses the table alone), so rung 2 tops at 30 and `fps_max` says 30. A manual tuning file is used as
given, so a class switch keeps the wrong file (`CC:6114-6140`: the `_clearHDR` variant is picked only for automatic tuning);
PROBABLE black or wrong-looking frames; validation should warn.

**Code:** Core ~280 lines, WebUI ~350, touch UI ~40 (PROBABLE).

### 2.3 Design R: ramp-ready start rung (add-on to A; recommended with it)

The ladder chooses with `target = max(fps, ramp_reach)` instead of `fps` when all of these hold: ladder active, Speed Ramp on
(`fps_ramp`), `ramp_reach > 0`, no take running.

| Step | Effect |
| --- | --- |
| Patrik sets "Speed Ramp takes start in: rung 2 … 50 fps" and turns Speed Ramp On | Off-take re-align: rung 2 (SDR 12-bit), FPS stays 24 |
| Record | No reconfigure at record start: the camera is already in rung 2 |
| Ramp 24 → 50 → 24 | T31 steps inside rung 2. One clip, one WAV, count numbering, base 24 |
| Stop | Base 24 restored. Still rung 2 while ramp-ready is armed |
| Speed Ramp Off (or reach "current FPS") | Re-align: 24 fps → rung 1 (Clear HDR 16-bit) |

| Cost | Value |
| --- | --- |
| Frames lost | 0 |
| Look | The whole ramp take is SDR 12-bit. Clear HDR is not used for it |
| Code | +30 lines Core, +40 WebUI (PROBABLE) |

Why not Cinemate's "deferred" switch (apply the held class change after stop): T31 restores the take's start rate at stop
(`CC:9162-9180`), so after a take the operator's target is the start rate, which is in the start rung. There is nothing to
defer.

### 2.4 Design B: switch mid-take with a clip split

**Core, step by step** (new code throughout; none exists today, r1 §h):

1. Trigger: `setFps` in a take, ladder active, `fps_ramp` on, a "split takes" option on, and the requested FPS **above the
   running mode's ceiling**. Upward only.
2. `switchRungInTakeLocked(rung, fps)` in the controller; `commit = false` (not persisted).
3. Session `splitClip(next)`:
   1. Close the frame gate (as `stopRecording` does).
   2. Stop the raw queue for clip 1 (`recorder_.stop()` drains synchronously; up to 12 queued frames). Write clip 1's
      `fps-ramp.txt` **without** clearing the take base (today `writeFpsRampLog` clears it, `CC:8422`).
   3. Stop the camera **only**: split today's `stop()` into `stopCamera()` (camera, buffers, manager, `CC:6293-6312`,
      `:6320-6354`) and `stopRecorders()` (`CC:6314-6319`). Audio and gyro keep running.
   4. `start(next)`: WDR change, new tuning, new CameraManager (F4).
   5. Reopen the raw queue at `<clip>_R2` with the frame index continuing (today `startAtFolder` resets it to 0, r1 §e), same
      base FPS, so RecRun timecode and FreeRun (counted from the first frame at the base, T31) continue.
   6. Re-open the frame gate with the cadence wait and a grace window, so the gap is not counted as drops (r1 Risks 7).
4. Failure: try `start(previous)` and continue capped in the old rung; if that also fails, stop the recorders, finalise the WAV,
   end the take with an error, state Ready or Error. Today a take-scoped reconfigure failure goes straight to Error (F5).
5. At stop: restore the start rung and start rate (one reconfigure after the take).
6. MLV: a new `.MLV` in clip 2 (RAWI/MLVI are written once at open, r1 Risks 15). Works because clips are folders.

| Cost | Value |
| --- | --- |
| Frames lost per switch | hole × FPS. At ~186 ms (Cinemate, no manager rebuild): 5 frames at 26 fps, 9 at 50. Core rebuilds the manager and changes WDR and tuning, and the sequential drain adds ~0.25-0.46 s for 12 frames of 16.9 MB at 437-818 MB/s. PROBABLE total 0.3-1 s, i.e. 8-26 frames at 26 fps. UNCONFIRMED until M1/M2 |
| Clip split | Two folders, frame numbers continue, one WAV in clip 1 |
| Look change | Clear HDR 16-bit → SDR 12-bit at the cut: bit depth, black level, linearisation, tone. Two grades |
| Code | +500-800 lines in `CC` (session split, recorder reopen with an index offset, per-clip ramp log, recovery, restore), +30 `App`, +30 `Web`. `CC` cannot be compiled off the Pi (libcamera) |

**Failure modes:** WDR EBUSY retries (`setSensorWideDynamicRange`, up to 4 × 50 ms, r1 §a.5); buffer allocation for the new mode
in the gap; first frames with the wrong exposure until controls settle (Cinemate saw VMAX exposure after a switch, r2 §b.4;
in Core the controls ride the start request, PROBABLE fine, unmeasured); raw pool buffers too small after an up-switch
(r1 Risks 14); the stepper blocks on the controller lock for the whole split.

Overlapping the drain with the restart (Cinemate stamps each queued frame with its folder, r2 §b.2) shortens the hole but
needs a second raw queue or per-frame folders: more code again.

### 2.5 Design B0: relay take (stop → switch → record), a cheap way to try B's look

When a take's request crosses the rung ceiling, the App stops the take, switches the rung (A's path), starts a new take at the
requested FPS with the first take's base forced, and writes a `ladder-take.txt` linking the two clips.

| Cost | Value |
| --- | --- |
| Frames lost | stop (drain, WAV finalise, sync) + reconfigure + `record_start` (220 ms `prepare_recording` sleep when audio is on, `App` record_start; r1 §e) + cadence wait. PROBABLE 1-2 s |
| Clips | Two takes (C0007, C0008), two WAVs, an audio gap |
| Code | ~150 lines (App + a base-FPS override in `startRecording`) |

It is what Patrik can already do by hand with A (stop, tap 50, record). Not recommended; listed because it lets him judge the
look change on real footage before anyone writes B.

### 2.6 Comparison

| | A | A + R | B | B0 |
| --- | --- | --- | --- | --- |
| Ramp 24 → 50 in one take | no (stops at 25) | yes, all SDR | yes, HDR then SDR | two takes |
| Frames lost in the take | 0 | 0 | 8-26 per switch (PROBABLE) | 25-100 (PROBABLE) |
| Clip split | no | no | yes | yes (two takes) |
| Look change in the take | no | no | yes | yes |
| Clear HDR used for ramp takes | yes, ≤ 25 | no | first segment | first take |
| New failure modes in a take | none | none | many (§2.4) | stop/start path |
| Core lines | ~280 | ~310 | ~800-1100 | ~430 |
| Testable off the Pi | WebUI and App syntax, JS | same | almost nothing | same as A |

### 2.7 Recommendation

**Build A + R as T34.** It meets requirement 1 ("lowest to 50, keep the resolution") and requirement 4 (ramping in takes) with
zero frames lost, and it meets requirement 3 (editor, optional thresholds, toggle) fully. It does not meet the literal
"switch sensor mode at the threshold" **inside** a take; that is B.

Measurements that would change it:

| Result | Changes the plan to |
| --- | --- |
| M3/M4: 4K SDR 12-bit uncompressed cannot hold 50 fps on the rig's link | Rung 2's real top is lower (ladder ceiling = what holds, e.g. 40), or rung 2 must be lossy DNG, or Gen 3. The ladder design is unchanged; Patrik's numbers change |
| M1/M2: Clear HDR → SDR reconfigure hole ≤ ~200 ms **and** M6: he accepts the look jump | Write B as T35 on top of A + R (A + R stays; B is an opt-in "split takes" switch) |
| M1: off-take switch ≥ ~1 s | Keep A + R, but add a settle delay for the pot path and say "switching mode" on screen |
| M6: Clear HDR 16-bit and SDR 12-bit grade to near the same look at 25 fps | R costs nothing visible; consider leaving ramp-ready armed by default |
| M5: the sensor/IPA runs at 1 fps or below | Rung 1 serves "lowest" literally; add low values in T33's lists |

---

## 3. Data model and storage

### 3.1 Identity of a rung

A sensor mode in Core is the triple (resolution, raw bit depth, Clear HDR) in `CaptureSettings`; there is no mode object.
CONFIRMED (`Types:124-176`; `sensorModeForRequestedResolution`, r1 §a). The rung uses Core's identity, not the probe's raw size:
16-bit Clear HDR is 3840x2160 in the settings and 3840x2200 on the wire (`isImx585HighResolutionAlias`, `CC:394-399`,
CONFIRMED).

```cpp
// include/apertar/core/Types.hpp, after CaptureSettings (Types:124)
struct LadderRung {
    Resolution resolution{};    // as CaptureSettings holds it: 3840x2160 for both 4K classes
    uint32_t rawBitDepth = 12;  // 10, 12 or 16
    bool clearHdr = false;
    double thresholdFps = 0.0;  // highest FPS this rung serves; 0 = the mode's own ceiling
    bool enabled = true;
};

struct ModeLadder {
    bool enabled = false;       // the toggle
    double rampReachFps = 0.0;  // ramp-ready (R): 0 = off
    std::vector<LadderRung> rungs;  // first = top of the hierarchy; thresholds rise
};
```

Derived output fields, added to `CaptureSettings` but **never persisted** (same pattern as `exposureCompensationAvailable`,
which `settings()` fills into its copy, `CC:10171-10179`, and `writeCaptureSettings` never writes, `CC:774-819`; CONFIRMED):

```cpp
    double fpsMax = 0.0;            // highest FPS set_fps would accept right now (T33)
    bool ladderEnabled = false;
    bool ladderActive = false;      // enabled and usable now (raw format, video, a usable rung)
    uint32_t ladderRung = 0;        // 1-based rung running now; 0 = none
    uint32_t ladderRungCount = 0;   // enabled, usable rungs
    double ladderRungCeiling = 0.0; // ceiling of the running rung
    bool ladderRampReady = false;   // R chose the rung
    std::string ladderLabel;        // "4K Clear HDR 16-bit"
```

### 3.2 Semantics and the chooser

```
modeCeiling(r) = sanitizeSettingsForSensor(settings_ with r's mode and fps = 280).fps
                 -> table, probe, lossless caps and max_fps in one number (CC:2835-2881)
usable(r)      = r.enabled and the sanitiser kept r's resolution, bit depth and Clear HDR
ceiling(r)     = threshold(r) > 0 ? min(threshold(r), modeCeiling(r)) : modeCeiling(r)
ladderCeiling  = max ceiling(r) over usable rungs
target         = (fps_ramp && rampReach > 0) ? max(fps, rampReach) : fps          (R)
chooseRung(t)  = first usable rung with ceiling(r) >= t - 0.0005, else the last usable rung
```

- Upper bound inclusive: 25 → rung 1, 25.001 → rung 2.
- Any rung can run any FPS below its ceiling; ranges only express preference.
- Same rule for `set_fps`, the stepper, the pot and the buttons, because every one of them ends in `CameraController::setFps`
  (pot and buttons `dispatch("set_fps")`, `App:8682-8689`, `:8943-8949`; stepper `App:9321`). CONFIRMED. One rule for every
  path (Cinemate lesson, r2 "What to avoid" 9).
- Ask the ladder about the FPS that will be commanded, after the rung's clamp (Cinemate `ff59dd8`, r2 port rule 1).

### 3.3 Where the ladder is stored

| Option | For | Against | Verdict |
| --- | --- | --- | --- |
| `camera_settings.conf` (Core, `CC:357-368`) inside `CaptureSettings` | Core owns it; already persisted | It is per format profile (`profile.cdng.`, `profile.mlv.`, `CC:650-663`), and `setRecordingFormat` swaps the whole profile, keeping only tuning, timecode and metering (`CC:9351-9364`). The ladder would differ between cDNG and MLV and vanish on a format switch. The persister rewrites the whole file from the snapshot (`CC:820-830`), so extra top-level keys need persister changes | no |
| `UI.conf` `[General]` (shared, `App:361-368`) | T33 puts the value lists there; Core already reads and writes it with the Qt lock (`App:1666`, `:1874`) | The touch UI never edits or reads the ladder; Core is the only consumer. A second writer (QSettings in the UI) for a Core behaviour key; Core re-parses the file on every read (`readSharedUiSettings` reads the file each call, `App:1666-1672`), which the hot `setFps` path must not do | no |
| `apertar-hardware.conf` | Per build | A text file edited in the Config panel; saving does not reload Core inputs (change-recipes B3 trap); the ladder is an operator choice that changes per shoot, not a build fact | no (max_fps only) |
| **New `~/.config/apertar-core/mode_ladder.conf`** | Core is the single owner; one ladder per camera; atomic write with the existing helper (`settingsFile::atomicWrite`, `src/util/SettingsFile.hpp:36`); same XDG directory as `camera_settings.conf`; no per-profile trap; held in memory, so `setFps` reads no file | One more file to back up | **yes** |

File format (one line per key, so a person can read it; Core rewrites it whole):

```ini
# Apertar mode ladder (T34). Core writes this file. Edit it in the WebUI: Settings > Record > Mode Ladder.
enabled=true
ramp_reach=50
rungs=3840x2160:16:hdr:25:on;3840x2160:12:sdr::on
```

Rung text: `<width>x<height>:<bits>:<hdr|sdr>:<threshold or empty>:<on|off>`, rungs joined by `;`. The same text is the
`rungs` value of `set_mode_ladder` (F15: one scalar string).

### 3.4 The build maximum (T33 part)

```ini
# apertar-hardware.conf
[camera]
# Highest FPS any control may select on this build (0 = the sensor's own limit).
max_fps=50
```

| Where | What |
| --- | --- |
| Read | App, at start (before `camera_.start`, `App:6972`) and after a successful `POST /api/config` save (`App:7314-7336`), using the first existing file of `hardwareConfigCandidatePaths()` (`App:4285-4303`), the same rule as `TriggerOutput::loadConfig` (first file wins). Strip inline `#` comments (change-recipes B3 trap) |
| Apply | `CameraController::setBuildMaximumFps(double)` stores it in a file-scope `std::atomic<double>` next to the probe globals (`CC:2718-2721`). `maximumSupportedFpsForResolution` (`CC:2799-2806`) returns `min(…, buildMax)` when > 0. That one function feeds the sanitiser (`CC:2868`) and the configure-time clamp (`CC:7232-7237`), so every path follows. If the running FPS is above the new value, re-sanitise once |
| Template | `defaultHardwareConfigTemplate()` (`App:4325`) gains the `[camera]` block. The UI's first-run copy (`DisplayConfigBridge.cpp:41`, change-recipes B3) may get it too; a missing key means 0 = no build cap |

### 3.5 Commands

| Command | Fields | OK reply | Refusals |
| --- | --- | --- | --- |
| `get_mode_ladder` | none | `"mode_ladder":{...}` (below) | none |
| `set_mode_ladder` | `rungs` (string, required), `ramp_reach` (number, optional, 0 = off) | `"mode_ladder":{...}` + `settingsBody` (the camera may have switched rung) | in a take; parse, mode, duplicate, rising-threshold, no-enabled-rung errors (§1.3) |
| `set_mode_ladder_enabled` | `enabled` (`true`/`false`) | `settingsBody` + `"mode_ladder":{...}` | in a take |
| `set_fps` (changed) | as today | as today, plus `"notice":"..."` when a take clamped the request at the rung ceiling | as today |
| `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` (changed) | as today | as today | ladder active (§1.7) |
| `help` | | lists the three new names (`App:9680-9681`) | |

`mode_ladder` object (Core may nest arrays in replies; only requests must be flat):

```json
{"enabled":true,"active":true,"note":"","ramp_reach":50,"ceiling":50,"running_rung":1,
 "rungs":[
  {"index":1,"width":3840,"height":2160,"raw_bit_depth":16,"clear_hdr":true,"label":"4K Clear HDR 16-bit",
   "threshold":25,"enabled":true,"mode_ceiling":25,"ceiling":25,"from_fps":0,"usable":true,"note":""},
  {"index":2,"width":3840,"height":2160,"raw_bit_depth":12,"clear_hdr":false,"label":"4K SDR 12-bit",
   "threshold":0,"enabled":true,"mode_ceiling":50,"ceiling":50,"from_fps":25,"usable":true,"note":""}],
 "pool":[{"width":3840,"height":2160,"raw_bit_depth":12,"clear_hdr":false,"label":"4K SDR 12-bit",
          "sensor_max_fps":60,"mode_ceiling":50,"in_ladder":true}, ...],
 "warnings":["Rung 1 -> 2 changes Clear HDR 16-bit to SDR 12-bit: the look changes."]}
```

The pool comes from `CameraController::sensorModes()` (`CC:10191-10195`, the probe list that `list_sensor_modes` prints,
`App:9659-9678`), mapped to Core's identity and deduplicated, each with Core's ceiling in the current format. CONFIRMED
sources; the mapping is new.

### 3.6 State fields

Written in all three JSON writers, because each feeds a different client (r1 §f; CONFIRMED writers):

| Field | `settingsEvent` `CC:141-200` (touch UI push) | `settingsBody` `App:179-235` (every reply, `get_state`) | `buildWebStateJson` `App:7850-` (WebUI poll) |
| --- | --- | --- | --- |
| `fps_max` | yes | yes | yes |
| `ladder_enabled`, `ladder_active`, `ladder_rung`, `ladder_rungs`, `ladder_rung_ceiling`, `ladder_ramp_ready`, `ladder_label` | yes | yes | yes |
| `mode_ladder` (rungs only, no pool) | no | no | yes (the editor's "saved" copy) |

`fps_max`:

| Situation | Value |
| --- | --- |
| Ladder inactive | the running mode's ceiling (`modeCeiling` of the current settings) |
| Ladder active, no take | `ladderCeiling` (50) |
| Ladder active, in a take (A, A + R) | the running mode's ceiling |

They are filled in `CameraController::settings()` (`CC:10171-10179`) and in `emitSettingsEventLocked()` (`CC:10407-10414`),
both already the places where derived fields are set. `startRecording` and `stopRecording` must emit a settings event,
because `fps_max` changes at those two moments while no setting does.

### 3.7 How the UIs learn

| UI | Rung | `fps_max` | Ladder editor data |
| --- | --- | --- | --- |
| Touch UI | `ladder_*` in the `settings` event and in `get_state`, parsed in `applyCoreState` (`CB:1296`) next to `fps_ramp` (`CB:1368-1369`) | same; used in `availableFpsOptions()` like `h264MaxFps` (`QML:815-816`, CONFIRMED pattern) | none |
| WebUI | `/api/state` poll and command replies (`mergeCameraStateFields`, `Web:8761-8846`) | same; `availableFpsOptionsForSnapshot` (`Web:5027-5054`) | `get_mode_ladder` when the Record panel opens and after a save; `mode_ladder` in the poll for changes made elsewhere |
| PCF pot and buttons | n/a | `availablePcfFpsOptions` cuts at `settings.fpsMax` instead of `maximumPcfFpsForSettings` (which returns 30 for 4K even in Clear HDR 16-bit, `App:1162-1165`, CONFIRMED) | n/a |

Today `mergeCameraStateFields` does not merge `clear_hdr` from replies (CONFIRMED: no `source.clear_hdr` in `Web:8761-8846`),
so after a rung switch by `set_fps` the WebUI would show the old class until the next poll. Add it with the new fields.

---

## 4. Implementation plan, file by file

Every item: file, `path:line` on the trees above, a search string for when lines move, the change. Order = build order. Each
part builds and is testable on its own.

### Part 1: T33a, the ceilings (needed by every design)

| # | File and place | Search string | Change |
| --- | --- | --- | --- |
| 1.1 | `CC:2778-2785`, `tableMaximumFpsForResolution` | `Clear HDR doubles VMAX` | Split the last line: Clear HDR keeps `!sensorLimitKnown ? 25 : 30`; SDR becomes `sensorLimitKnown ? 60.0 : 30.0` (the probe then wins through `min`, `CC:2805`). Keep 30 when the probe did not run |
| 1.2 | `CC:2718-2721` | `Filled once by the startup probe` | Add `std::atomic<double> buildMaximumFps{0.0};` |
| 1.3 | `CC:2799-2806`, `maximumSupportedFpsForResolution` | `return probed ? std::min(table, *probed) : table;` | Apply `buildMaximumFps` when > 0 |
| 1.4 | `Hdr:62` area and new body near `setFpsRamp` (`CC:9733`) | `bool setFpsRamp(bool enabled, bool keepExposure);` | `void setBuildMaximumFps(double fps);` stores, then re-sanitises the running FPS once if needed (off-take only) |
| 1.5 | `App:4285-4303` (after) | `std::vector<std::filesystem::path> hardwareConfigCandidatePaths()` | `double cameraMaxFpsFromHardwareConfig()`: first existing file, section `[camera]`, key `max_fps`, inline `#` stripped, clamp 0..280 |
| 1.6 | `App:6972` (before) | `if (!camera_.start(options_.mediaRoot` | `camera_.setBuildMaximumFps(cameraMaxFpsFromHardwareConfig());` and log `ApertarCore build max fps: 50` |
| 1.7 | `App:7317` (after a successful save) | `saveHardwareConfigFile(request.body` | Re-read and apply, so `max_fps` needs no restart |
| 1.8 | `App:4325` | `std::string defaultHardwareConfigTemplate()` | Add the `[camera]` block (§3.4) |
| 1.9 | `Types:124` onward | `struct CaptureSettings {` | Add the derived `fpsMax` (more fields come in 2.1) |
| 1.10 | `CC:10171-10179` and `CC:10407-10414` | `CaptureSettings result = settings_;` / `void CameraController::emitSettingsEventLocked()` | Fill `fpsMax` (sanitise a copy at FPS 280) |
| 1.11 | `CC:189`, `App:215`, `App:8045` | `"fps_ramp\":"` in each writer | Add `fps_max` to the three writers |
| 1.12 | `App:1174-1192`, `availablePcfFpsOptions` | `const double maxFps = maximumPcfFpsForSettings(settings, sensorName);` | Use `settings.fpsMax` when > 0, else the old function |
| 1.13 | `Web:5027-5054`, `availableFpsOptionsForSnapshot` | `let max = maximumSupportedFpsForSnapshot(snapshot);` | Use `snapshot.fps_max` when > 0; keep the old table as the fallback for an older Core |
| 1.14 | `Web:8761-8846`, end of `mergeCameraStateFields` | `snapshot.fps_ramp_keep_exposure = source.fps_ramp_keep_exposure;` | Merge `fps_max` and `clear_hdr` from replies |
| 1.15 | `CBh:39`, `:87`, `:164`, `:318` | `double h264MaxFps() const` | `Q_PROPERTY(double fpsMax READ fpsMax NOTIFY fpsMaxChanged)`, getter, signal, `double m_fpsMax = 0;` |
| 1.16 | `CB:1368-1369` (after) | `state.contains(QStringLiteral("fps_ramp"))` | Parse `fps_max`, emit on change |
| 1.17 | `QML:808-833`, `availableFpsOptions()` | `var max = root.maximumSupportedFpsForResolution(root.resolution)` | `var max = root.controlBridge && root.controlBridge.fpsMax > 0 ? root.controlBridge.fpsMax : root.maximumSupportedFpsForResolution(root.resolution)`; keep the lossless and H.264 `min`s |

Check after Part 1 (Pi): `get_state` shows `"fps_max":50` in 4K SDR 12-bit, `25` in Clear HDR 16-bit; `set_fps value=60` in 4K SDR
leaves 50.

### Part 2: T34 Core (A + R)

| # | File and place | Search string | Change |
| --- | --- | --- | --- |
| 2.1 | `Types:124` onward | `struct CaptureSettings {` | `LadderRung`, `ModeLadder` structs and the derived `ladder*` fields (§3.1) |
| 2.2 | `CC:357-368` (after) | `std::filesystem::path persistedSettingsPath()` | `modeLadderPath()` (same XDG rule, file `mode_ladder.conf`), `loadModeLadder()`, `writeModeLadder()` (via `settingsFile::atomicWrite`), `parseLadderRungs(text, &error)`, `ladderRungsText(rungs)` |
| 2.3 | `CC:8923` (after) | `settings_ = loadPersistedCaptureSettings(formatSettings_, stillSettings_);` | `modeLadder_ = loadModeLadder();` |
| 2.4 | `Hdr:173-177` | `bool rampTakeChanged_ = false;` | Members `ModeLadder modeLadder_;`; private helpers `ladderActiveLocked()`, `ladderTargetFpsLocked(fps)`, `evaluateLadderLocked()` (ceilings, usable, warnings), `chooseRungLocked(target)`, `switchRungLocked(rung, fps)`, `alignToLadderLocked()`, `fillLadderStatusLocked(CaptureSettings &)` |
| 2.5 | `CC:9101` (insert before the sanitise) | `const SensorFamily sensorFamily = (!simulateCamera_ && session_)` (the one inside `setFps`, `:9102`) | Off-take with the ladder active: choose the rung for `ladderTargetFpsLocked(fps)`; if its mode differs, `return switchRungLocked(rung, fps);` |
| 2.6 | new, after `applyFpsStepLocked` (`CC:9121-9160`) | `bool CameraController::applyFpsStepLocked` | `switchRungLocked`: build `next` (rung mode, FPS = min(fps, ceiling), shutter by the same branch as `CC:9127-9145`; better: move that branch into a small helper both call), log `ApertarCore mode ladder: 25 -> 50 fps, rung 1 -> 2 (4K SDR 12-bit)`, `applySettingsLocked(next, true, true)` |
| 2.7 | `CC:9044-9050`, `:9523-9529`, `:9559-9565` | `Resolution changes are blocked while recording.` and the two siblings | After the recording gate: refuse when `ladderActiveLocked()` (§1.7) |
| 2.8 | `CC:9733-9747`, `setFpsRamp` | `next.fpsRampKeepExposure = keepExposure;` | After a successful apply: `alignToLadderLocked()` (R depends on `fps_ramp`) |
| 2.9 | `CC:9327-9380`, `setRecordingFormat` | `return applySettingsLocked(next, requiresReconfigure);` | After success: `alignToLadderLocked()` (a raw profile may come back in another mode) |
| 2.10 | `CC:10231-10285`, `applyCapturePreset` | `persistSettingsLocked();` inside `if (applied)` | Then `alignToLadderLocked()`: the preset's FPS decides the rung |
| 2.11 | `CC:8947-8975`, `start` | `persistSettingsLocked();` (in `start`) | After the session is up (the probe has run, `CC:6145`): `alignToLadderLocked()`. Not before: before the probe 4K SDR reads 30 (`CC:2784`) |
| 2.12 | `CC:9792-9842`, `startRecording` | `rampTakeBaseFps_ = settings_.fps;` | Log `ApertarCore mode ladder: take in rung 2/2 (4K SDR 12-bit), in-take ceiling 50 fps, ramp-ready`; emit a settings event (`fps_max` changes) |
| 2.13 | `CC:10080-10097`, `stopRecording`; `CC:10099-10123`, `checkRecordingFailure` | `restoreFpsAfterRampLocked();` | Emit a settings event after the restore (`fps_max` back to the ladder ceiling) |
| 2.14 | `CC:9105-9113`, `setFps` no-op/clamp path | `if (std::abs(settings_.fps - effectiveFps) < 0.0001) {` | In a take with the ladder active and `fps > effectiveFps`: set a `lastNotice_` the App adds to the reply as `notice` |
| 2.15 | `CC:8409-8460`, `writeFpsRampLog` | `# base_fps=` | One header line `# mode=<WxH> bits=<n> clear_hdr=<0/1>` from the session's own settings |
| 2.16 | `CC:10171-10179`, `:10407-10414` | as 1.10 | `fillLadderStatusLocked` fills the `ladder*` fields |
| 2.17 | `Hdr` public, near `:115` | `std::vector<SensorMode> sensorModes() const;` | `std::string modeLadderJson(bool withPool) const;`, `bool setModeLadder(const std::string &rungs, std::optional<double> reach);`, `bool setModeLadderEnabled(bool);`, `std::string takeNotice();` |
| 2.18 | `CC:141-200` `settingsEvent`; `App:179-235` `settingsBody`; `App:7850-` `buildWebStateJson` | `"fps_ramp\":"` | The `ladder_*` fields in all three; `mode_ladder` (no pool) in the web state only |
| 2.19 | `App:9659` (after `list_sensor_modes`) | `if (command.name == "list_sensor_modes") {` | Handlers `get_mode_ladder`, `set_mode_ladder`, `set_mode_ladder_enabled`; values as strings and numbers only (F15) |
| 2.20 | `App:9680-9681` | `"commands\":[\"get_state\"` | Add the three names |
| 2.21 | `App:9747-9754`, `set_fps` | `if (command.name == "set_fps") {` | Append `,"notice":"..."` when `camera_.takeNotice()` is not empty |
| 2.22 | `App:9322-9330`, stepper | `fps is this mode's limit` | With the ladder active, say "the ceiling of ladder rung N (label) in a take" |

Persistence of the operator's target vs the rung:

| Moment | What is persisted | Why |
| --- | --- | --- |
| Off-take rung switch | the profile gets the rung's mode and the FPS (commit = true) | The pair always agrees with the ladder; a restart comes back in the same rung |
| Ramp step in a take | nothing (T31, `CC:9118`) | Take-scoped |
| Stop | start rate re-persisted (T31, `CC:9162-9180`); the rung did not change (A, A + R) | |
| Ladder edits and toggle | `mode_ladder.conf` only | Separate from the camera profiles |
| B only | the in-take rung is never persisted; stop restores and persists the start rung | Cinemate `ff59dd8` |

### Part 3: WebUI

| # | Place | Search string | Change |
| --- | --- | --- | --- |
| 3.1 | `Web:2951-2953` (between the Recording format card and the next card) | `id="settingsSpeedRampRange"` | New `<div class="settings-card">` "Mode Ladder": head + `online-pill` `settingsModeLadderValue`; pill grid `settingsModeLadderOptions` (Off/On); list `settingsModeLadderList`; add row (`settingsModeLadderAddSelect`, button); select `settingsModeLadderReachSelect`; `settingsModeLadderWarnings`; Save/Revert buttons; `settingsModeLadderNote` |
| 3.2 | CSS near `.preset-row` (`Web:1887-1935`) | `.preset-row {` | `.ladder-row` (reuse the preset row look), `.ladder-handle { touch-action: none; cursor: grab; user-select: none; min-width: 44px; min-height: 44px; }`, `.ladder-row.dragging { opacity: .85; position: relative; z-index: 2; }`, `.ladder-row.drop-target { outline: 2px dashed var(--muted); }`, `.ladder-threshold { width: 6em; }`. Phone width: the row wraps like `.preset-actions` (`flex-wrap: wrap`) |
| 3.3 | `Web:4236`, `const state = {` | `speedRampTarget: "",` (T32) | `ladderServer: null, ladderDraft: null, ladderDirty: false, ladderDrag: null` |
| 3.4 | After `renderSpeedRamp` (`Web:5079`) | `function renderSpeedRamp(snapshot, fpsOptions) {` | `fetchModeLadder()` (`sendCommand({cmd:"get_mode_ladder"})`, keeps the reply in `state.ladderServer`), `ladderDraftFromServer()`, `validateLadderDraft()` (§1.3), `renderModeLadder(snapshot)`, `moveLadderRung(from, to)`, `installLadderDrag(handle, row, index)`, `saveModeLadder()` (`set_mode_ladder` with `rungs` text and `ramp_reach`) |
| 3.5 | `Web:10149` | `renderSpeedRamp(snapshot, fpsOptions);` | `renderModeLadder(snapshot);` |
| 3.6 | `Web:9897` | `setElementDisabled("settingsRecordResolutionSelect", false);` | `!!snapshot.ladder_active`; same for the crop select and the bit-depth pills (`Web:10135-10147`, `enabled:` gets `&& !snapshot.ladder_active`), with the Recording format copy saying "Mode Ladder on: the FPS picks the mode." |
| 3.7 | `Web:10059-10065`, FPS pills | `buildOptionButtons("fpsOptions"` | Keep `set_fps`; after the reply, `if (result.notice) showToast(result.notice)`. The "Frame rate" label (`Web:2544`) shows "Rung 1/2 · above 25 fps: 4K SDR 12-bit" |
| 3.8 | `Web:5079-`, `renderSpeedRamp` note | `setText("settingsSpeedRampNote"` | With the ladder: "This take runs in rung 1 and stops at 25 fps" or "Ramp-ready: takes start in rung 2 so they can reach 50 fps" |
| 3.9 | `Web:8761-8846` | as 1.14 | Merge `ladder_*` fields from replies |
| 3.10 | `Web:8848`, `applyCommandSnapshotPatch` | `case "set_fps_ramp":` (T32) | `case "set_mode_ladder_enabled": snapshot.ladder_enabled = boolValue; break;` |
| 3.11 | Listeners near `Web:11578-11581` | `settingsSpeedRampTargetSelect").addEventListener` | Add, Save, Revert, threshold `input`, enabled `change`, reach `change` (each edits the draft and sets `ladderDirty`) |

Drag sketch (pointer events, one handler set per handle):

```js
    function installLadderDrag(handle, row, index) {
      handle.addEventListener("pointerdown", (event) => {
        if (state.snapshot && state.snapshot.recording) return;
        event.preventDefault();
        handle.setPointerCapture(event.pointerId);
        state.ladderDrag = { from: index, to: index, pointerId: event.pointerId, startY: event.clientY };
        row.classList.add("dragging");
      });
      handle.addEventListener("pointermove", (event) => {
        const drag = state.ladderDrag;
        if (!drag || drag.pointerId !== event.pointerId) return;
        row.style.transform = "translateY(" + (event.clientY - drag.startY) + "px)";
        drag.to = ladderIndexAtY(event.clientY);   // row midpoints from getBoundingClientRect()
        markLadderDropTarget(drag.to);
      });
      const finish = (event) => {
        const drag = state.ladderDrag;
        if (!drag || drag.pointerId !== event.pointerId) return;
        state.ladderDrag = null;
        row.style.transform = "";
        if (event.type === "pointerup" && drag.to !== drag.from)
          moveLadderRung(drag.from, drag.to);       // edits state.ladderDraft, sets ladderDirty, redraws
        else
          renderModeLadder(state.snapshot);
      };
      handle.addEventListener("pointerup", finish);
      handle.addEventListener("pointercancel", finish);
    }
```

`renderModeLadder` redraws the rows only when `!state.ladderDrag` and (`state.ladderDirty` or the server copy changed);
otherwise it only updates the pill, the note and the disabled states. Checks before the Pi: `node --check` of the page script
and a Chromium run against a mocked `/api/state` and `/api/command`, as T32 did.

### Part 4: touch UI

| # | Place | Search string | Change |
| --- | --- | --- | --- |
| 4.1 | `CBh:39` area, `:164`, `:318` | `Q_PROPERTY(double h264MaxFps` | `ladderActive`, `ladderRung`, `ladderRungCount`, `ladderLabel`, `ladderRampReady` with one `ladderChanged` signal and members |
| 4.2 | `CB:1368-1369` (after) | `state.contains(QStringLiteral("fps_ramp"))` | Parse the `ladder_*` fields, emit on change |
| 4.3 | `CB:1035-1048` | `commandName == QStringLiteral("set_clear_hdr") \|\|` | Add `set_fps` to the reconfigure list (10 s instead of 3 s, `CB:1050-1052`): a `set_fps` can now reconfigure |
| 4.4 | `QML:522` | `readonly property string formatDisplaySubtext:` | Prefix `"R" + rung + "/" + count + (rampReady ? " ramp" : "") + " · "` when `controlBridge.ladderActive` |
| 4.5 | `QML:1214-1222` | `function applyResolutionValue(resolutionValue) {` | On failure: `root.showRecordWarning("Mode Ladder On", root.controlBridge.lastError, "Resolution not changed", "Pick an FPS, or turn the ladder off in the WebUI.")` (pattern `QML:1515`) |
| 4.6 | `CB:255-294`, `applyFps` | `const int shutterUs = shutterUsForAngle(preservedAngleValue, fpsValue);` | No change needed: off-take the follow-up `set_shutter_us` keeps the same angle Core already set. Note for the tutorial; check it on the Pi (M7) |

### Part 5: only if B is built later (T35)

`CC`: session split (`stop()` into `stopCamera()` + `stopRecorders()`, `CC:6293-6356`), `recorder_.startAtFolder` with a frame
index offset (r1 §e), `writeFpsRampLog(keepBase)` (`CC:8409-8422`), split line and grace (`noteFpsChange` pattern), recovery,
`restoreRungAfterTakeLocked` next to `restoreFpsAfterRampLocked` (`CC:9162-9180`; callers `:10090`, `:10115`, `:8990`).
`App`: a "split takes" option in `set_mode_ladder`. `Web`: the option and the B wording. The 16 touch points in r1 "What a
ladder implementation must touch" items 5-15 are the checklist.

---

## 5. Measurements on the Pi before building

Shorthand: `K=~/apertar-kb/working/tools`. Core running, preview only unless the step says record. `core.py` turns `true`,
`false` and integers into JSON types and sends everything else as a string; Core's `number()` parses strings too
(`CP` `ControlCommand::number`), so `value=0.5` works.

**M1. How long does a Clear HDR ↔ SDR switch take? (preview, no code change)** Start in 4K Clear HDR 16-bit, 25 fps,
uncompressed cDNG.

```bash
K=~/apertar-kb/working/tools
python3 -I $K/core.py get_state | grep -oE '"(resolution|fps|raw_bit_depth|clear_hdr)":[^,]*'   # 3840x2160, 25, 16, true
for i in 1 2 3; do
  t0=$(date +%s%N); python3 -I $K/core.py set_clear_hdr enabled=false | grep -o '"ok":[a-z]*'; t1=$(date +%s%N)
  echo "HDR16 -> SDR12: $(( (t1 - t0) / 1000000 )) ms"; sleep 4                                   # one reconfigure
  t0=$(date +%s%N); python3 -I $K/core.py set_clear_hdr enabled=true | grep -o '"ok":[a-z]*'; t1=$(date +%s%N)
  echo "SDR12 -> HDR12: $(( (t1 - t0) / 1000000 )) ms"; sleep 4                                   # one reconfigure
  python3 -I $K/core.py set_raw_bit_depth value=16 >/dev/null; sleep 4                              # back to the start
done
journalctl -u apertar-core -b -o short-precise --no-pager | grep -E 'camera configured|tuning variant|recovery' | tail -12
```

Why one command is one switch: `set_clear_hdr enabled=false` from 16-bit Clear HDR sanitises to SDR 12-bit
(`supportedRawBitDepthForSensor`, `CC:2808-2833`) and reconfigures once (`CC:9559-9583`). CONFIRMED code path. Prediction:
several hundred ms, more than Cinemate's 186 ms (manager rebuild, WDR, tuning). Decides: the off-take blink per threshold
crossing, and the lower bound of B's hole.

**M2. The hole in frames, from libcamera's own timestamps (one restart, optional).**

```bash
printf '[Service]\nEnvironment=LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0\nEnvironment=LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log\n' | sudo tee /etc/systemd/system/apertar-core.service.d/zz-ladder-timing.conf   # Patrik; "zz" sorts after libcamera-log.conf, so it wins
sudo systemctl daemon-reload && sudo systemctl restart apertar-core                                  # Patrik
sleep 10; python3 -I ~/apertar-kb/working/tools/core.py set_clear_hdr enabled=false; sleep 3
python3 -I -c "import re;t=[int(m.group(1)) for m in re.finditer(r'Stream CFE Image buffer dequeue, buffer id \d+, timestamp: (\d+)', open('/dev/shm/rpi0.log').read())];d=sorted((b-a)/1e6 for a,b in zip(t,t[1:]));print('frames',len(t),'largest gaps ms',[round(x,1) for x in d[-3:]])"
sudo rm /etc/systemd/system/apertar-core.service.d/zz-ladder-timing.conf && sudo systemctl daemon-reload && sudo systemctl restart apertar-core   # Patrik: undo
```

The regex is the CFE line `be_cycle.py` already parses. The largest gap is the camera-off time between the last frame of the old
mode and the first of the new. Decides B: gap × FPS = frames lost per switch. ≤ ~200 ms → B is worth a prototype if M6 passes.

**M3. Can 4K-wide SDR 12-bit run 50 fps today? (record, no code change; proxy mode 3840x2076, 598 MB/s)**

```bash
K=~/apertar-kb/working/tools
dmesg | grep -E 'link up|CSTS' | tail -3                                   # which PCIe gen, any NVMe drop since boot
python3 -I $K/core.py set_record_format value=cdng
python3 -I $K/core.py set_cdng_compression value=none                     # lossless is capped at 30
python3 -I $K/core.py set_clear_hdr enabled=false
python3 -I $K/core.py set_raw_bit_depth value=12
python3 -I $K/core.py set_resolution width=3840 height=2076              # Core ceiling 60 today, probe 62.85
python3 -I $K/core.py set_fps value=50
python3 -I $K/core.py get_state | grep -oE '"(resolution|fps)":[^,]*'     # 3840x2076, 50
bash $K/takes.sh 1 60                                                     # its 12->16 steps are no-ops in SDR (CC:2808-2833)
```

Prediction at Gen 3: `files=3000 missing=0`, `peak_queue` low. At Gen 2 (437 MB/s): queue fills, `dropped_queue_full` > 0.
Rules: `missing > 0` with `peak_queue=12/12` → storage-bound (link, O_DIRECT T24, or lossy); `dropped_gap_estimate > 0` with a
low queue → pipeline-bound (back end at 20 ms/frame). Decides whether rung 2 can top at 50 on this rig.

**M4. After Part 1: the real 4K SDR 12-bit at 50.** `set_resolution width=3840 height=2160`, `set_fps value=60` → `get_state`
shows 50 (`max_fps`); with `max_fps=0`, 60. Then `bash $K/takes.sh 1 60` at 50. Same rules as M3, 622 MB/s.

**M5. The lowest FPS (preview, then a 10 s take).**

```bash
python3 -I $K/core.py set_fps value=1;   python3 -I $K/core.py get_state | grep -o '"fps":[0-9.]*'   # 1?
python3 -I $K/core.py set_fps value=0.5; python3 -I $K/core.py get_state | grep -o '"fps":[0-9.]*'   # 0.5?
bash $K/takes.sh 1 10                                                     # files= about 5 at 0.5 fps if the sensor follows
```

Core accepts any FPS above 0 (`CC:9097-9100`); whether the IPA honours a 2 s frame is UNCONFIRMED. Decides the bottom of rung 1
and the low entries for T33's lists.

**M6. The look change (two short takes, Resolve).** Same scene with a grey card and a highlight, same ISO and 180°: 5 s in 4K
Clear HDR 16-bit at 25, then `set_clear_hdr enabled=false` and 5 s in 4K SDR 12-bit at 25. Patrik grades both on one timeline.
Decides: whether R (ramp takes all SDR) costs anything he cares about, and whether a mid-take cut (B) is acceptable at all.

**M7. After the build: touch UI and exposure across a switch.** Tap 50 on the touch UI FPS picker in rung 1.

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'mode ladder|camera configured' | tail -4      # one switch line
journalctl -u apertar-ui-direct -b --no-pager | grep -iE 'timeout|error' | tail -5                # no reply timeout (4.3)
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -oE '"(fps|shutter_us|ladder_rung)":[0-9.]*'   # 50, 10000 at 180 deg, 2
```

Decides: whether 4.3 is enough, and whether the shutter angle survives a switch (Cinemate lost exposure after a switch, r2 §b.4).

---

## 6. Risks and open questions

### 6.1 Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Rung 2 at 50 fps is not sustainable: 622 MB/s needed, 437 MB/s at Gen 2; Gen 3 is faster but has NVMe-drop history | PROBABLE (F9, F10) | M3/M4 first. Lower the rung 2 top, use lossy, or choose the link |
| R2 | Lifting the 4K SDR cap (1.1) also lets non-ladder 4K SDR go to 60 | CONFIRMED consequence | `max_fps=50` holds it; say so in T33a |
| R3 | Probe off → 4K SDR stays 30 → ladder top 30 | CONFIRMED (`CC:2799-2806`) | `fps_max` shows it; log a line when a rung's ceiling falls back to the table |
| R4 | Off-take switches cost a preview blink each; a jittery pot reconfigures repeatedly | PROBABLE | M1; pot deadband exists; add a settle delay only if M1 says ≥ 1 s |
| R5 | A manual tuning file survives a class switch | PROBABLE (`CC:6114-6140`) | Validation warns when `tuning_file` is set and the ladder crosses classes |
| R6 | `set_fps` now reconfigures; any client with a short timeout fails (touch UI: 3 s) | CONFIRMED (F14) | 4.3; WebUI has no client timeout (`sendCommand`, `Web:9291-9326`) |
| R7 | Manual mode controls refused while the ladder is on; `takes.sh`'s bit-depth steps are refused too | CONFIRMED consequence of 2.7 | Clear messages; the tutorial says to turn the ladder off for `takes.sh` |
| R8 | The WebUI editor loses a drag or an edit to the 1 s redraw | CONFIRMED redraw pattern (`Web:10385`, `:11800`) | Draft + `ladderDirty` + `ladderDrag` guard (Part 3) |
| R9 | Four copies of the ceiling drift | CONFIRMED (r1 Risks 9) | `fps_max` makes Core the source; the old tables remain only as fallbacks |
| R10 | Lossless cDNG: rung 2 stops at 30 | CONFIRMED (F8) | Shown as a warning and in the ranges |
| R11 | HDMI (ExternalMonitorWindow) shows no rung | UNCONFIRMED where it would go (`formatInfoValue`, `ui-map.md` §4) | Later |
| R12 | B: hole, split, look change, recovery paths that only the Pi can test, `CC` not compilable off the Pi | PROBABLE (§2.4) | Only after M1/M2/M6 |

### 6.2 Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Is A + R enough: a ramp take that goes above 25 is SDR 12-bit from its first frame? Or is a mid-take switch (B) worth a hole of 8-26 frames and a cut between two looks? | A + R; B only after M1/M2/M6 |
| Q2 | While the ladder is on, should manual resolution / bit depth / Clear HDR be refused (proposed), turn the ladder off, or pick the matching rung and move the FPS into its range? | refuse |
| Q3 | In a take, cap at the running mode's ceiling (proposed) or at the rung's threshold when it is lower? | mode ceiling |
| Q4 | Ramp-ready default: off, or "reach the ladder top"? | off (explicit) |
| Q5 | Which link for 50 fps: Gen 2 (stable, 437 MB/s, not enough) or Gen 3 (818 MB/s burst, drop history)? Or lossy DNG for rung 2? | decide after M3 |
| Q6 | How low is "the lowest possible FPS" for him (1, 5, 12)? | decide after M5; values go into T33's lists |
| Q7 | Should the PCF resolution pot be disabled (or turned into a rung selector) while the ladder is on? | refused like any manual mode change |
| Q8 | For B later: is a second clip whose frame numbers continue (not starting at 0) fine in his Resolve workflow? | continue numbering |
