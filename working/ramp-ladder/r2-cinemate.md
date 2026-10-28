# R2: Cinemate's dynamic resolution, and what it does mid-take

2026-10-27, cloud session (reader R2 of the ramp-ladder workflow). Read-only. Nothing was run on a Pi.

Trees and the commit every citation is at, unless a commit is named in the line:

- `cinemate` = cinemate @ `d6cc93e`
- `cinepi-raw` = cinepi-raw @ `63a08d5`
- `handbook` = cinemate-handbook @ `c99ff77`
- `apertar-core` = Apertar-Core (cloud branch `clearhdr-fixes`) @ `d4ad539`
- `kb` = the KB (cloud copy) @ `34c8706` (Apertar-UI is cited through `kb/llm/ui-map.md` only; the QML source is not here)

Labels: **CONFIRMED** = I opened the line. **PROBABLE** = derived from confirmed lines; the derivation is given. **UNCONFIRMED** = not checked.

## 0. Short answer

1. Cinemate's "dynamic resolution" is a stateless chooser. On every fps change it asks: "which mode, no better than the one the operator selected, can run this fps?" The switch point (threshold) is each mode's `fps_max`. There is no user threshold list, no user ordering and no hysteresis. CONFIRMED (`cinemate/src/module/dynamic_resolution.py:426-502`).
2. The order of the modes is derived, not authored: a "priority" policy (`mode`, `resolution`, `none`) sorts the candidates. The operator controls *which* modes exist (per-mode on/off) and can *lower* a mode's `fps_max` (per-mode fps ceiling). Lowering a ceiling is the only way to move a threshold. CONFIRMED (`cinemate/docs/settings-json.md:344-362`; `cinemate/src/module/sensor_detect.py:2415-2437`).
3. Mid-take, Cinemate pins the ladder to the running class (bit depth + SDR/ClearHDR). A same-class switch is allowed and **splits the take into a new clip folder and a new WAV**, with a frame gap. A class switch is never made mid-take; fps is capped instead and the switch is applied after the take has drained. CONFIRMED (`cinemate/src/module/cinepi_controller.py:904-930, 975-1018`; `cinepi-raw/cinepi/cinepi_raw.cpp:68-76, 365-381`).
4. So mid-take Cinemate always **drops resolution before it changes class**, under every priority, including `resolution`. That is the opposite of Patrik's goal ("keep the resolution"). PROBABLE (§b.1).
5. "FPS free" in Cinemate swaps the click-stop list for a 1-fps sweep from the list's lowest entry to `fps_max`, and `set_fps` stops snapping. Apertar has no toggle, but `set_fps` and `ramp_fps` already accept any value in (0, 280]. The preset arrays Patrik wants to edit are in three places (§d). CONFIRMED.

## (a) How dynamic resolution works, end to end

### a.1 The mode table the ladder walks

- The ladder walks `sensor_detect.res_modes`: the *filtered* table. Filters: `k_steps` (sizes in K), `bit_depths`, the ClearHDR switches (`imx585_clear_hdr_12bit` off, `_16bit` on by default), per-camera `enabled_modes`, `aspect_ratios`, `min_mode_width`. CONFIRMED (`cinemate/settings.jsonc:255-335`; filter loop `cinemate/src/module/sensor_detect.py:2501-2530`; `res_modes` assignment `:2909-2914`).
- So "select the modes I want, Cinemate-style" already means "these are the only rungs the ladder may use". The settings editor has a per-mode table with an enable switch per mode ("Keep at least one recording mode enabled", `cinemate/src/module/app/templates/settings_editor.html:4300`). CONFIRMED. History: `9dfe1e1`, `9e0ed32`, `40f11c3` (PR #200, 2026-09-19).
- Each mode's `fps_max` comes from `cinepi-raw --list-cameras` and is truncated to an integer at parse (`int(float(...))`, `cinemate/src/module/sensor_detect.py:1156`). CONFIRMED.
- A `custom_modes` entry matching a detected mode **overrides its `fps_max`** (F-298). Lowering is the intended use; raising logs a warning. The detected value is kept as `fps_max_detected`. CONFIRMED (`cinemate/src/module/sensor_detect.py:2278-2286, 2415-2437`). The settings editor shows it as "Per-mode fps ceilings": an fps field per mode, titled "User ceiling; blank uses sensor maximum" (`settings_editor.html:4256-4320`, title `:4286`; doc `cinemate/docs/settings-json.md:344-362`). Saving restarts Cinemate. CONFIRMED.

### a.2 The chooser (`dynamic_resolution.py`)

- **Two axes per mode.** Class = `(hdr, bit_depth)` (`mode_family`, `:298-308`), ranked HDR over SDR, then more bits over fewer (`_family_rank`, `:311-318`). Size = frame area (`_mode_area`, `:154-159`). CONFIRMED.
- **Candidates** (`_candidate_modes`, `:344-410`). A mode is a candidate only if: area ≤ the desired mode's area (`:382`); and either it is in the pinned class (`:384-386`) or, with no pin, its class is not richer than the desired one (`:387-391`). Priority `none` pins to the desired mode's own class, but only when the caller has not already pinned another class: "a caller's pin ... no policy may override it" (`:371-377`). Then a geometry rule (WP-CM-5): if the desired mode carries crop geometry, a candidate must have the same aspect within 0.02 and the same full-frame-or-windowed character (`:392-408`, tolerance `:165`). A sensor that reports no crop metadata skips this rule (`_mode_geometry`, `:237-249`). CONFIRMED.
- **Choice** (`choose_resolution`, `:426-502`). Keep candidates whose `fps_max ≥ fps` (`:465-470`). If the desired mode is among them, return it, no substitution (`:474-481`). Otherwise return the maximum under the priority's sort key (`:489`). Keys (`_ladder_key`, `:321-341`): `mode` and `none` sort by `(hdr, bit_depth, area, fps_max, -mode)`; `resolution` sorts by `(area, hdr, bit_depth, fps_max, -mode)`. The result carries `dynamic_active` (any substitution) and `mode_class_changed` (`:94-104`, `:492-502`). CONFIRMED.
- **Ceiling** (`max_fps_for_context`, `:505-551`): the highest `fps_max` among the *same* candidate set, so the fps dial cannot offer a rate nothing can serve. CONFIRMED.
- **Default policy** is `mode` (`:64-68`). Its imx585 ladder from 16-bit ClearHDR 4K is 16-bit 4K → 16-bit HD → 4K SDR → HD SDR; `resolution` gives 16-bit 4K → 4K SDR → HD SDR (`:21-35`; doc `cinemate/docs/sensors.md:162-170`). CONFIRMED.

What this means for thresholds. PROBABLE, from the lines above:

- The switch up happens at the first fps above the current rung's `fps_max`. The switch back happens at the first fps at or below the desired mode's `fps_max`. The same number both ways: no hysteresis, no dwell. The chooser holds no state between calls.
- The switch is lazy. The camera stays in the selected mode as long as that mode can run the fps. That matches Patrik's "keep the resolution as long as possible", but only along the order the policy produces.

### a.3 The controller (`cinepi_controller.py`)

State (`:164-191`): `dynamic_resolution_enabled`, `_priority`, `_desired_mode` (what the operator selected), `_active` (a substitute is on screen), `_suspended` (storage pre-roll), `_deferred` (a class change was held back by a take), `_deferred_fps` (the operator's target when a take cap stood in for it). CONFIRMED.

Startup (`:282-312`, `:696-743`): enabled and priority read Redis first, then `settings.jsonc`, then the default. The desired mode is restored only if a substitute was active; otherwise it becomes the mode on screen. CONFIRMED.

`set_fps(value)` (`:1747-1857`), in order. CONFIRMED unless marked:

1. `fps_lock` gate (`:1756-1758`). Publish the request as `fps_user` at once for the GUI (`:1763-1764`).
2. Ceiling = stored `fps_max` (`:1773`). With dynamic resolution on, that is the ladder ceiling, not the running mode's (`_refresh_fps_max`, `:956-973`, `_dynamic_context_fps_max` `:895-902`).
3. Free stepping or shutter-sync mode: clamp to `[1, fps_max]`, no snapping (`:1776-1778`). Otherwise snap to the nearest entry of the step table (`:1779-1785`).
4. Mid-take: cap to `_in_take_fps_ceiling()` (`:1793-1797`, function `:904-930`): the ladder ceiling with the class pinned to the running mode.
5. Ask the ladder about the fps that will actually be commanded (`:1799-1808`, rule from `ff59dd8`). `_maybe_apply_dynamic_resolution_for_fps` (`:1020-1059`) calls the chooser (`:975-1018`), which pins the class mid-take (`:997`) and, mid-take, asks a second, unpinned question to set `_deferred` when the two answers differ (`:999-1016`).
6. Remember the pre-cap target if a take cap was applied (`:1814-1816`).
7. Write `fps` to Redis (`:1828`) and recompute shutter angle or exposure (`:1831-1852`).

Applying a mode (`_apply_resolution_mode`, `:2672-2748`). CONFIRMED:

- Publish the new mode's Redis keys first: `sensor_mode`, `width`, `height`, `bit_depth`, `hdr`, `packing`, `mode` string, lores size (`_publish_resolution_gui_state`, `:2526-2592`).
- `_pace_resolution_change` (`:1994-2012`): sleep until at least **0.25 s idle / 2.0 s recording** has passed since the last switch (`:233-234`). Then sleep 0.12 s (`:2709`, constant `:39`).
- Write `cam_init` (`:2711`). cinepi-raw's handler only sets `cameraInit_` (`cinepi-raw/cinepi/cinepi_controller.cpp:1027-1030`); the main loop reconfigures on the next pass (`cinepi_raw.cpp:68`).
- Relaunch cinepi-raw only when the class or aspect changes, and never while recording (`_resolution_change_needs_restart`, `:2762-2815`; recording returns False at `:2782`).
- When the new stream is up (the `Raw stream: WxH` log line, or a 2.5 s fallback timer), force-republish shutter, ISO, WB gains and zoom (`_notify_resolution_switch_complete` `:1944-1959`, `_reapply_camera_controls` `:1961-1992`, keys `:54-59`).

PROBABLE, from the call chain above: the whole switch runs synchronously inside `set_fps`. A mid-take switch therefore holds the caller for up to 2.0 s + 0.12 s before the new fps is even written (`:1828` runs after `:1808` returns).

PROBABLE ordering hazard: on a ramp *down* across a threshold, the mode switch (back to the slower, larger mode) is published before the lower fps. For one reconfigure the sensor is asked for the old, higher fps in a mode that cannot run it; libcamera clamps the frame duration. One step (1 fps at the default increment) for the first frames. Not observed anywhere.

Other entry points. CONFIRMED:

- `set_resolution(n)` makes `n` the desired mode, then asks the ladder for the current fps (`:2817-2844`). `switch_resolution` steps from the desired mode, not the substitute (`:2459-2500`).
- `set_fps_double` uses the same chooser and policy (`_select_resolution_mode_for_fps`, `:2431-2456`) but **refuses any mode change while recording** (`:4083-4090`, `:4104-4110`). That is stricter than `set_fps`, which allows a same-class switch mid-take. An inconsistency (PROBABLE, by comparing the two).
- `_ramp_fps` (`:4119-4136`) steps ±1 fps every 0.2 s through `set_fps` and has no caller (kb `working/ramp-answer.md` §1.1, already verified).
- Toggling the feature or the priority re-derives `fps_max` and the step table (`:771-822`, `:824-877`). Switching it on adopts the mode on screen as the desired mode (`0ce2208`).
- Storage pre-roll and the startup `set_fps` run with dynamic resolution suspended (`:387-409`; doc `cinemate/docs/sensors.md:193`).

### a.4 User-facing surface

| Surface | What | Citation |
| --- | --- | --- |
| `settings.jsonc` | `image_capture.dynamic_resolution` (bool, default true), `image_capture.dynamic_resolution_priority` (`mode`/`resolution`/`none`, default `mode`), `k_steps`, `bit_depths`, `hdr.*` switches; `arrays.fps` `{steps: [25, 33, 50], free: false, free_increment: 1}` | `cinemate/settings.jsonc:191-195, 255-294` CONFIRMED |
| Schema | descriptions of the two keys; `enabled_modes` item shape (width, height, bit_depth, hdr, crop) | `cinemate/settings.schema.json:435-470` CONFIRMED |
| Settings editor | toggle `f-dynres`, select `f-dynres-priority`; per-mode enable table; per-mode fps ceiling field | `settings_editor.html:2039-2044, 4256-4320` CONFIRMED |
| Web GUI | "DYN RES" toggle, priority select in the experiment drawer | `cinemate/src/module/app/templates/template.html:1842, 2299-2301` CONFIRMED |
| CLI | `set dynamic resolution [0/1]`, `set dynamic resolution priority [mode/resolution/none]` (bare toggles / cycles) | `cinemate/src/module/cli_commands.py:133-137`; `cinemate/docs/cli-commands.md:102-104` CONFIRMED |
| Redis | `dynamic_resolution_enabled`, `_active`, `_desired_mode`, `_priority` | `cinemate/docs/redis-keys.md:39-42` CONFIRMED |
| Indicator | RES readout turns green while a substitute is held | `cinemate/docs/sensors.md:195`; `cinemate/docs/simple-gui.md:22` CONFIRMED |

There is **no** user list of rungs, no user order and no per-rung threshold separate from the mode's ceiling. CONFIRMED by absence in the settings and schema keys read above.

## (b) What happens mid-take

### b.1 The in-take pin

- While recording, the chooser is pinned to the class of the mode actually running (`cinepi_controller.py:997`), and so is the fps ceiling (`:904-930`). A class change is held back (`_deferred`, `:999-1016`). CONFIRMED.
- After stop, `_settle_deferred_dynamic_resolution` (`:2378-2417`) applies the held change, but only once the take's RAM buffer has drained (`:2393-2398`), and it goes to the operator's pre-cap target, not the cap (`:2402-2410`). CONFIRMED.
- Reason given: bit depth is part of `--mode` and ClearHDR is the `--hdr sensor` launch flag, so a class change relaunches cinepi-raw, and a relaunch ends the take (`dynamic_resolution.py:38-44`; commit `3d12870`). CONFIRMED.
- Tests: class change held back (`cinemate/_test/test_dynamic_resolution_priority.py:164-173`); same-class substitution still happens mid-take, 16-bit 4K → 16-bit HD at 40 fps (`:175-182`); the ceiling shrinks to the running class, 40 instead of 87 (`:184-200`). CONFIRMED.
- **Mid-take, every priority drops resolution first.** PROBABLE, from `_candidate_modes` with the pin (`:384-386`) plus `choose_resolution` (`:465-489`): with the class pinned, the only candidates are smaller modes of the same class. Under `resolution` priority, off-take 16-bit 4K at 30 fps would go to 4K SDR; mid-take it goes to 16-bit HD, splits the clip, and sets `_deferred` so 4K SDR is applied after stop.

### b.2 A same-class switch mid-take, in cinepi-raw

The main loop checks `controller.configChanged()` once per frame (`cinepi-raw/cinepi/cinepi_raw.cpp:68`). If recording, in this order. CONFIRMED:

1. Log "splitting current recording before camera restart" (`:72`). `setRecording(false)`, `folderOpen = false` (`:73-74`).
2. `sound.record_stop()` (`:75`): SIGTERM to the audio helper's process group (`cinepi-raw/cinepi/cinepi_sound.cpp:966-983`).
3. `advanceClipNumber()` (`:76`; `cinepi_state.hpp:79-81`).
4. `StopCamera`, `Teardown`, `ConfigureVideo`, crop controls (`:78-121`), `StartCamera` (`:123`). Re-read sensor binning and active area from the driver, reset the encoder (`:124-362`).
5. `create_clip_folder(options, clipNumber)` (`:367`), then `sound.record_start()` (`:370`), `resetFrameCount()` (`:371`), `reset_encoder()` (`:372`), `setRecording(true)` (`:373`).

Consequences:

- **Frame numbers restart at 0** in the new clip: `resetFrameCount` sets `index_ = 0` (`cinepi-raw/cinepi/dng_encoder.hpp:118-124`). CONFIRMED.
- **Frames still in the queue keep their old folder.** Each queued frame carries the folder it was captured for (`dng_encoder.cpp:465-477`; introduced in `a6437b5`, 2026-05-22). CONFIRMED.
- **Timecode and FrameRate restart per clip.** `resetFrameCount` clears `tc_origin_set_` (`dng_encoder.hpp:123`). The first frame of the new clip re-captures the wall-clock origin and sets the SMPTE base from the configured rate at that moment (`dng_encoder.cpp:2059-2119`). So clip 2's base is the fps at the split, not the take's start rate. CONFIRMED lines; the consequence for a ramp is PROBABLE.
- **The split clip's folder name uses `gettimeofday`, not the sensor clock.** The take-start path passes the sensor wall clock so "the folder FXX equals ... the DNG TC origin" (`cinepi_raw.cpp:421-425`). The split path passes nothing (`:367`), so `generate_filename` falls back to `gettimeofday()` (`cinepi-raw/cinepi/utils.cpp:37-50`). PROBABLE: the clip-2 folder name, and the WAV's fallback timecode parsed from it (`cinepi_sound.cpp:419-460, 817-821`), can disagree with clip 2's DNG timecode by the reconfigure delay.
- **Audio: one WAV per clip, with a gap.** The old WAV ends at the SIGTERM (step 2). The new WAV starts asynchronously after `StartCamera` (`cinepi_sound.cpp:835-878`, "audio starts asynchronously" `:878`). PROBABLE: the audio gap is at least the reconfigure stall plus the helper's start-up time. Not measured.

The Cinemate side follows the split. CONFIRMED:

- `cam_init` opens a "reconfigure pending" window and suspends sync and drop warnings (`cinemate/src/module/redis_listener.py:1464-1466`, `:381-391`).
- When cinepi-raw's frame count drops back, the listener closes the window, records the pause interval, and keeps a **logical frame count** that continues across clips (`:394-422`, `:436-452`).
- Expected frames exclude pause time (`_active_seconds_between`, `:340-351`). For a take that ended up in several folders, the final analysis uses "on-disk totals" plus index holes (`:1834-1840`, from `c715878`).

PROBABLE, from `:1834-1840`: expected = recorded + holes, so **frames lost in the stall are never counted as dropped**. The verdict is "in sync" by construction.

### b.3 How long a reconfigure stalls

| Source | What it says | Label |
| --- | --- | --- |
| `cinepi-raw` `e74e3e4` (2026-06-13) | "a camera reconfigure stall (~186ms) leaked into the phase accumulator", imx585 mode1, 24 fps, multi-sensor matrix. The number is the size of the phantom phase error, not a timed gap. | CONFIRMED (commit body) |
| `cinepi-raw` `3b3ff60` (06-13) | after absorbing whole missed frames, takes still started at −90 ms: the stall "isn't an integer number of frames", and "sub-1.8-frame reconfigure gaps slipped under the threshold". | CONFIRMED |
| `cinepi-raw` `4537153` (06-14) | −169 ms: "the mode-switch reconfigure arrived as a burst of sub-1.5-frame gaps". | CONFIRMED |
| Cinemate pacing | 2.0 s minimum between recording-time switches (`:234`); first 3.5 s (`c715878`), cut to 2.0 s in `e2589c4` ("make resolution preview reconnect snappier"). No measurement in either body. | CONFIRMED |
| Handbook hardware log | no timed mid-take split. Searched for "reconfigure", "split", "stall", "186", "segment", "clip folder". It records only that a same-aspect live reconfigure loads without relaunch or timeouts (`handbook/lessons/hardware-log.md:447-448`). | CONFIRMED (absence) |

So ~186 ms is one number, from a preview reconfigure, inferred from a phase error. It is not a mid-take measurement. Read it as "a few hundred ms, arriving as several short gaps, not one clean hole". PROBABLE.

### b.4 Controls after the switch

- A mode switch resets the sensor exposure to VMAX while Redis still holds the old `shutter_a`; re-sending the same value was swallowed by a same-value dedup. Found on hardware (`handbook/lessons/hardware-log.md:796-799`). Fixed by force-republishing shutter, ISO and WB gains on switch *completion*, not at `cam_init`, because cinepi-raw defers the reconfigure and an early republish would be reset again (`cinemate` `f884716`, 2026-08-27). Zoom joined later with a cinepi-raw dedup reset (`cinepi-raw` `b15cc0c`; key list `cinepi_controller.py:54-59`). CONFIRMED.
- PROBABLE: between `StartCamera` and the completion republish, the first frames of the new clip can carry the VMAX exposure. Cinemate never measured that window.

## (c) Bugs and lessons in the history

| Commit (date) | What went wrong | Rule it produced |
| --- | --- | --- |
| `d7b21b5` (2026-08-25), F-286 | Tie-break on `(area, fps_max)` made imx477 4056x3040 12-bit unreachable: a sustainable request for it returned the 10-bit twin. | An explicit, sustainable request for the desired mode is honoured as is (`dynamic_resolution.py:474-481`). |
| `e878438` (08-25) | Among eligible substitutes, the faster one won, dropping bit depth for fps nobody asked for. | Rank quality above spare fps headroom; fps only breaks the last tie. |
| `72de2b9` (08-25) | `dynamic_resolution_enabled` was hard-coded True; reaching the sensor's top mode needed a source patch. | Every automatic behaviour needs an off switch that persists. |
| `2c8cf81` (09-06) | A substitution could trade 12-bit for 10-bit at the same size; `set_fps_double` used its own family-blind picker; toggling the feature left `fps_max` and the step table stale; the web GUI showed a substitute in the same white as a choice. | Family = `(hdr, bit_depth)`; substitution changes resolution only; one chooser for every caller; re-derive the ceiling and the step table on every toggle; show a substitution. |
| `3d12870` (09-07) | Confined to its class, a 16-bit ClearHDR 4K selection capped at 40 fps with the 87 fps HD SDR mode unreachable. | A ladder over the whole table, with a policy for which axis goes first. Crossing a class relaunches cinepi-raw, so mid-take the ladder and the ceiling are pinned to the running class, and the held change is applied after stop. The ceiling reads the same candidate set as the chooser. |
| `ff59dd8` (09-07) | (1) The ladder was asked about the *requested* fps, then the value was capped: 87 fps commanded in a mode whose ceiling is 21; mid-take, a ramp to 60 was capped to 40 with no switch. (2) A take cap was kept as the new target. (3) Review found: `none` discarded the caller's pin and returned a 16-bit mode while 12-bit SDR ran, with no relaunch, so DNG metadata lied; the settle relaunched cinepi-raw mid-drain and truncated the clip; `set fps double` ignored the policy. | Ask the ladder about the fps you will actually command. A take-scoped cap is not the operator's target. A caller's pin outranks every policy. Settle only after the drain. Every caller passes the policy. Invariant test: no reachable request outruns the mode it lands in (`_test/test_dynamic_resolution_priority.py:273`). |
| `0ce2208` (09-07) | Hardware: a stale `desired_mode = 0` in Redis would, on enabling, have dropped a 16-bit 4K camera to SDR on the next fps change. | On an off→on transition, adopt the mode on screen as the desired mode. |
| `112b5c8` (09-20), WP-CM-5 | A windowed crop and a full or binned mode of similar area were interchangeable: the camera could reframe mid-shoot. | A substitute must keep aspect (±0.02) and full-or-windowed character; otherwise cap fps. |
| `a6437b5` (cinepi-raw, 05-22), `7e6cd6b`, `c715878`, `e2589c4` (cinemate, 05-22/23) | cinepi-raw had refused mode changes while recording. | Split instead: new clip folder, new WAV, frame count from 0; each queued frame keeps its own folder; the listener tracks segments; recording-time switches are paced (3.5 s, then 2.0 s). |
| `f884716` (08-27), `b15cc0c` | Settings silently not re-applied after a switch (dedup). | Re-apply camera controls on switch completion. |
| `e74e3e4`, `3b3ff60`, `4537153` (cinepi-raw, 06-13/14) | A reconfigure stall leaked into the phase lock; takes started 90-186 ms off. | In preview, a gap re-arms the lock; in recording, gaps are absorbed as missed frames; preview backstop at half a frame. |
| Hardware log 2026-08-26 (`handbook/lessons/hardware-log.md:441-446, 477-479`) | At stock clock, a 25 fps request silently swapped a selected 4K ClearHDR mode for its HD sibling; it looked like "4K modes are not loading". | Logged as a UX defect; the green RES indicator (`2c8cf81`) is the answer. |
| Hardware log 2026-08-26 (`:800-801`) and 2026-09-15 (`:3136-3140`) | `set resolution N` was remapped by dynamic resolution; a request was recorded as `desired_mode = 6` while the camera stayed elsewhere. | Turn it off for mode matrices; say when the requested mode is not the one running. |

Stale text found: `_resolution_change_needs_restart` says "we never split a running take" (`cinepi_controller.py:2779`), but a same-class switch mid-take does split it (`cinepi_raw.cpp:68-76`). The sentence means "never relaunch mid-take". CONFIRMED both lines.

## (d) "FPS free"

Cinemate. CONFIRMED:

- Config: `arrays.fps = {steps: [25, 33, 50], free: false, free_increment: 1}` (`cinemate/settings.jsonc:191-195`), read at `cinepi_controller.py:335, 350`.
- Off: the step table is `arrays.fps.steps` (`_rebuild_fps_steps`, `:1090-1101`). Entries above `fps_max` are replaced by `fps_max` (`:1103-1124`). `set_fps` snaps to the nearest entry (`:1779-1785`).
- On: the step table is `free_stepping_steps(lowest entry, fps_max, increment)` (`:1091-1098`; `cinemate/src/module/parameters.py:53-87`). The list's top entry never raises the ceiling. `set_fps` no longer snaps: it clamps to `[1, fps_max]` (`:1776-1778`). Shutter-sync mode has the same effect.
- With dynamic resolution on, `fps_max` is the ladder ceiling, so the free sweep runs up to the fastest rung and crosses every threshold one increment at a time (PROBABLE, from `:956-973` and `:1091-1098`).
- Floor: 1 fps (`:1777`). Surfaces: `set fps free [0/1]` (`cinemate/docs/cli-commands.md:131`), web GUI "FREE STEPPING" (`cinemate/docs/web-gui.md:27`), settings editor (`cinemate/docs/settings-json.md:149-151`).

Apertar. CONFIRMED unless marked:

- No `fps_free` toggle. `CameraController::setFps` accepts any value in (0, 280] (`apertar-core/src/camera/CameraController.cpp:8822-8825`; settings load `:574-575`), then the sensor sanitiser clamps it (`:8827-8832`). The control socket's `set_fps value=<any>` (`apertar-core/src/ApertarCoreApp.cpp:9598`) and `ramp_fps {to, seconds}` (`:9800`, stepper `:9172-9220`) are already "free".
- The preset arrays, where Patrik edits the selectable values:
  - WebUI: `const fpsPresets = [24, 25, 30, 35, 40, 45, 50, 60, 70, ..., 240, 280]` (`apertar-core/src/web/WebControlPage.cpp:4039`). For any sensor other than imx477/577 it is cut to ≤ 60 (`:4993-4996`), then to the snapshot's maximum.
  - Hardware dial (PCF): `availablePcfFpsOptions` presets `{24, 25, 30, 50, 60}` (`{..., 100}` for imx477/577), filtered by `maximumPcfFpsForSettings` (`apertar-core/src/ApertarCoreApp.cpp:1163-1181`).
  - Touch UI: `fpsOptions`, `qml/CameraPage.qml:498`, filtered by `availableFpsOptions` `:802`. UNCONFIRMED (from `kb/llm/ui-map.md:148, 151`; the QML is not here).
- No array has a value below 24. A ramp "from the lowest possible fps" cannot start from a preset today. It needs a low entry added to an array, or a `set_fps` from the WebUI/socket before `ramp_fps`. PROBABLE (from the three arrays).

## Port to Apertar

### What to copy as logic

1. **Choose the mode for the fps you will command, after every clamp** (`ff59dd8`). In Core, that means the ladder lookup sits after `sanitizeSettingsForSensor`, not before.
2. **One function for the choice and the ceiling** (`max_fps_for_context` reads the same candidates as `choose_resolution`). The UIs' fps limit must come from the ladder, or the dial offers rates nothing can serve.
3. **A take-scoped value is not the operator's target** (`ff59dd8`). T31 already does this for ramp steps; the mode switched to mid-take must also not be persisted, and stop must restore the start mode with the start rate.
4. **A caller's pin outranks the policy** (`ff59dd8`). If Core pins anything for a take (for example "no Clear HDR change"), no code path may hand back a mode outside it.
5. **Honour the desired mode whenever it can run the fps** (`d7b21b5`). In a ramp, the take's start mode is the desired mode; the ladder only walks down from it and returns to it.
6. **Never hand back a richer mode than the start mode** (`2c8cf81`, `3d12870`). With a ladder that starts at the top rung, this is automatic.
7. **Stamp every frame with its clip at capture time** (`a6437b5`). Frames still encoding when the switch happens must land in the old clip.
8. **Re-apply exposure, gain, WB and crop after the reconfigure, on completion** (`f884716`, `b15cc0c`).
9. **Keep a logical frame count across clips and record the stall as an interval** (`redis_listener.py:394-422`). But also write the lost time to `fps-ramp.txt` (Cinemate does not report it; §b.2).
10. **Settle a held change only after the buffer has drained** (`ff59dd8`).
11. **Show a substitution** (green RES, `2c8cf81`). For a ramp: the mode on screen must say it is a ladder rung.

### What to avoid

1. **Implicit thresholds.** Cinemate's switch point is the mode's `fps_max`. Patrik wants authored thresholds. And Core's table (4K at 30) disagrees with the probe (4K SDR to 60) (task facts; kb `working/ramp-mode-ladder.md` §1), so "the mode's ceiling" is not even one number on Apertar. Use an explicit array: rung = mode, threshold = the highest fps that rung serves. It is the same idea as Cinemate's per-mode fps ceiling, but it belongs to the ladder, not to the mode.
2. **A derived order.** Cinemate's order comes from a policy sort. Patrik wants to order the rungs himself. A code/config array in order is simpler, and the "never richer" and "same shape" checks become validation of the array at load, not a runtime search.
3. **No hysteresis.** The chooser is stateless. A dial or pot that jitters across a threshold switches every time, and mid-take each switch is a split. Core's `ramp_fps` stepper is monotonic, so the risk is the manual dial. Either switch only in the ramp's direction, or require the fps to move a margin past the threshold.
4. **Synchronous sleeps in the fps path.** Cinemate sleeps up to 2.12 s inside `set_fps` (`:1994-2012`, `:2709`). Core's stepper thread waits on a condition variable so stop can interrupt it (`ApertarCoreApp.cpp:9196-9201`). A switch must not block that thread for seconds.
5. **Mid-take "drop resolution first".** Under the pin, every Cinemate policy drops to HD before it changes class (§b.1). That is the opposite of "keep the resolution".
6. **Per-clip timecode and FrameRate from the rate at the split** (`dng_encoder.cpp:2059-2119`). T31 uses one base per take, the start rate. Keep that across clips.
7. **Split-clip naming from `gettimeofday`** (`cinepi_raw.cpp:367`). Name the next clip from the first frame's sensor time, as the take start does.
8. **Counting the stall as "in sync".** Write the gap (time and the frames it represents at the current rate) to the ramp log.
9. **Refusing in one path and allowing in another.** Cinemate's `set_fps_double` refuses a mid-take switch that `set_fps` makes (§a.3). Core should have one rule for `set_fps`, `ramp_fps` and the dial.

### Where Cinemate's behaviour conflicts with one continuous ramp shot

1. **The split is a hole in the shot.** About 186 ms per switch, maybe more, arriving as a burst (§b.3). At 30 fps that is about 6 frames; at 50 fps about 9 (PROBABLE arithmetic). In a ramp, the switch happens mid-action, and the hole is a jump cut after conform.
2. **The format changes at the switch.** Clear HDR 16-bit to 4K SDR 12-bit changes bit depth, black level and linearisation. Two clips must be graded to match. That is unavoidable for any class switch, in Cinemate or Core (task facts).
3. **Cinemate forbids exactly the switch Patrik needs.** Its rule caps fps at the class ceiling mid-take and applies the class change after stop (§b.1). Its reason is a process relaunch. Core switches modes by a full camera reconfigure, not a process relaunch (task facts), so the reason does not carry over. The DNG format change does. PROBABLE.
4. **Ramping back down crosses the threshold again.** Cinemate returns to the desired mode at the same threshold (§a.2): a second split, a second hole. A ramp 24 → 50 → 24 across one threshold gives three clips. PROBABLE.
5. **Audio breaks at each split.** One WAV per clip, restarted asynchronously (§b.2). T31's take-long, real-time WAV would be lost. Audio does not depend on the sensor mode, so one WAV across the take is the better rule for Core. Recommendation, not checked against Core's audio code.
6. **Pacing fights a stepper.** A 2.0 s minimum between recording-time switches (§a.3) stalls a stepper that moves 1 fps every 0.1-0.2 s.
7. **Exposure after the switch.** Until the completion republish, the new clip's first frames can carry the wrong exposure (§b.4). With a shutter policy of angle or exposure (T31), Core must re-apply its own ramp exposure right after `StartCamera`.
8. **Framing.** WP-CM-5 forbids substituting a crop for a full-frame mode (§c). Patrik's ladder C (4K → 3840-wide crop) is exactly such a substitution. In Cinemate it would be refused and fps capped. On Apertar it is allowed only because the operator authors the ladder; the reframing must then be visible on screen and in the ramp log.
