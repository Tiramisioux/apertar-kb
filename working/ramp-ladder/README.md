# Speed ramp project: requirements, status, next steps (cloud session, 2026-10-27)

One project on Core `cinemate-port` (`7a545d9`) and Apertar-UI `cinemate-port` (`dc471c1`): ramp FPS during takes from every
control, set the selectable values in the settings, and climb a mode ladder from the lowest FPS to 50. Nothing is pushed.
Everything finished is a patch in `working/patches/` with a tutorial in `tutorials/inbox/`. The unfinished parts are below,
with the decisions taken so far.

## 1. What Patrik asked for (2026-10-27, in order)

1. Ramp from the lowest possible FPS up to 50, switching sensor mode at threshold values, keeping the resolution.
2. The selectable FPS values stay as code arrays for now; point him to them. Done: §4.
3. "Come up with a plan, critique it, present how the system would work, how to implement it, and a tutorial."
4. A Cinemate-inspired section in the WebUI settings for speed ramping, by expanding the Format section. Done: T32.
5. **25 fps is the accepted maximum for 4K Clear HDR 16-bit.** Done: T32 (Core's clamp and its PCF pot/button list, the WebUI
   and the touch UI all stop at 25).
6. **His use case:** 25 fps is the first threshold. Above it, 4K Clear HDR 16-bit switches to 4K SDR 12-bit, up to 50. 50 is the
   maximum, set in the settings for this build.
7. Set the arrays for ISO, shutter angle, FPS and WB Cinemate-style, adapted to the Apertar style. Not started: §3.1.
8. Speed ramping must work during takes in this project. Done for every FPS control: T31 + T32 (§2).
9. **Ladder editor:** drag and drop the activated modes in hierarchical order, with optional threshold values, and a toggle switch
   from which point the system honours the thresholds. Not started: §3.2.
10. **Keep the WebUI "Camera settings" pane** (FPS / ISO / shutter-angle pills, `WebControlPage.cpp:2538-2560`). It fronts the
    selectable values and works as a quick-access menu in the field. §3.1 feeds it; it is not replaced.

11. **(2026-10-28) Least API change.** T31 on the Pi is `76094a9`: switch `set_fps_speed_ramp enabled= [shutter=angle|exposure]`,
    state `fps_speed_ramp`, `fps_speed_ramp_keep_exposure`; no `ramp_fps` stepper. T32's "Ramp to … over …" steps with `set_fps`
    from the page.
12. **(2026-10-28) System-controlled values are green** in the WebUI and the touch UI (auto ISO, a shutter the ramp rescales or
    clamps, the FPS restored at stop, later the ladder's mode). Neither UI has this convention yet.
13. **(2026-10-28) Auto on the ISO dial**, at its lowest position, when the operator changes ISO.
14. **(2026-10-28) Clear HDR log spam.** Candidate: the driver's `Update minimum HMAX: base= lane_scale= hdr_scale=` (186 lines
    this boot, one per mode set); to confirm with Patrik.
15. **(2026-10-28) Open question:** must H.264 refuse ramping? See the answer in the session; decision pending.

16. **(2026-10-28) Auto ISO: lock or off, in the ISO array and the API.** Proposal (least API): `set_iso_auto [enabled=true|false]`
    (the `set_fps_phase_lock` pattern); `false` locks at the live gain (`measuredAnalogueGain_`, `CC:7704`); `set_iso value=N` stays
    "off at N". While `iso_auto`, the state's existing `"iso"` reports the live gain (today the set value, `App:8018`), shown green.
    In T33 the ISO array gets Auto as its lowest entry, so the dial's lowest position is Auto (request 13).
17. **(2026-10-28) Clear HDR guard.** In Clear HDR, auto ISO and auto WB are off, with an info message. Entering Clear HDR with
    either on: they hold the value they had at that moment. Back to SDR: they return to auto.

## 2. Done (patches and tutorials in this export)

| Tutorial | Patches (apply in this order) | What |
| --- | --- | --- |
| T31 | Core `0001-camera-speed-ramping-FPS-changes-during-cDNG-MLV-tak.patch` | FPS changes inside cDNG/MLV takes behind `fps_speed_ramp` (count-based numbering, one `FrameRate`/timecode base, real-time WAV, shutter policy, grace, `fps-ramp.txt`, `ramp_fps` stepper, which refuses up front in a take it cannot ramp). Rebased onto `cinemate-port` `7a545d9`; three steps differ from the first cloud version (tutorial status line) |
| T32 | Core `0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch`, `0001-web-speed-ramp-block-in-the-Recording-format-card.patch`; UI `0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch`, `0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch` | 25 fps ceiling for 4K Clear HDR 16-bit in Core (clamp and PCF pot/button list), WebUI and touch UI; Speed Ramp block under Bit Depth in Settings → Record → Recording format (On/Off, Shutter Sync Angle/Exposure, Ramp to … over …, ×2, Back); the touch UI picker leaves the shutter to Core in a camera ramp take (not in a sound-only take) |

FPS controls during a take with `fps_speed_ramp` on: WebUI pills and the Speed Ramp block, PCF pot, `fps:<n>`/`fps_up`/`fps_down` buttons
(all `set_fps` or `ramp_fps`), touch UI picker (after T32 4.9). The touch UI's `ensureValidFpsSelection()` returns early with a
bridge (`qml/CameraPage.qml:1557-1558`), so it does not fight a stepper.

Neither is on GitHub `cinemate-port` (`6ae70b5`) yet. Checked in the cloud: every Core patch applies with plain `git am` on `7a545d9` and on the later tip `6ae70b5`, both UI patches on `dc471c1`; host
`g++ -fsyntax-only` of the Core files that do not need libcamera; `node --check` of the WebUI script; the WebUI block driven in
Chromium against a mocked `/api/state`; the whole touch UI built with Qt 6.4.2. `CameraController.cpp` was not compiled
(libcamera). Nothing ran on the Pi in the cloud session.

## 3. Next (not implemented)

### 3.1 T33: value lists (ISO, shutter angle, FPS, WB), Cinemate-style

Today each list exists three times, and the copies already differ:

| List | WebUI (`WebControlPage.cpp`, T32 tree) | Touch UI (`qml/CameraPage.qml`) | Core pots/buttons (`ApertarCoreApp.cpp`, T31 tree) |
| --- | --- | --- | --- |
| FPS | `fpsPresets` `:4071` | `presets` in `availableFpsOptions()` `:808-812@dc471c1` | `availablePcfFpsOptions()` `:1174-1192` |
| ISO | `isoOptions` `:4072` | `isoOptions` (KB `llm/ui-map.md:148`) | `pcfIsoOptions()` `:1303-1306` |
| Shutter angle | `shutterOptions` `:4073` | `shutterOptions` (KB `llm/ui-map.md:148`) | `pcfShutterAngleOptions()` `:1308-1314` |
| WB | `whiteBalanceOptions` `:4075` | WB list (KB `llm/ui-map.md`) | `pcfWhiteBalanceOptions()` |

Core line numbers in this section are on the T31 tree. On the T32 tree those after `:1162` are one higher (the 25 fps cap
adds a comment line in `maximumPcfFpsForSettings`).

Cinemate keeps them in `settings.json` `arrays.{iso,shutter_a,fps,wb}.steps`, edited as chips in the settings editor, with a
"free" toggle and an increment (`cinemate/src/module/app/templates/settings_editor.html:1970-1994@d6cc93e`).

Decided so far (not built):

- **One owner.** Store the lists in the shared Qt settings file that Core and the touch UI already share,
  `~/.config/CinePi/UI.conf`, section `[General]` (`sharedUiSettingsPath()` `ApertarCoreApp.cpp:361-368`; Favorites live
  there as `favoritesOrder`). Keys: `isoSteps`, `shutterAngleSteps`, `fpsSteps`, `wbSteps`. Missing or empty means the
  built-in list.
- **Core** reads them in `readSharedUiSettings()` (`:1665-1837`) and writes them with `updateSharedUiGeneralSettings()`
  (`:1874`, takes the Qt INI lock). It validates the values (numbers, range, sorted, deduplicated), adds a command (for example
  `set_value_steps name=fps values=12,15,24,25,50`) and puts the lists in the state's `ui` object. The PCF pots and the
  `*_up`/`*_down` buttons use them.
- **Touch UI**: `SettingsBridge` already watches `UI.conf` and reloads on change (`src/SettingsBridge.cpp:413-425`,
  `pollExternalSettings`). Add four list properties next to `favoritesOrder` (`:407`, `:576`, `:1689-1701`) and use them in
  `CameraPage.qml` instead of the constants.
- **WebUI**: a settings card with four chip rows (× to remove, a field to add, Reset), Apertar card style. The option functions
  (`availableFpsOptionsForSnapshot()` and friends) read the lists from the snapshot and fall back to the constants. The
  quick-access "Camera settings" pane (item 10) and the Speed Ramp targets then show his lists.
- **Build maximum** ("50 … set as max in the settings for this particular build"): a new section in the per-build hardware
  config, which the WebUI Config panel already edits (`/api/config`, `ApertarCoreApp.cpp:7262-7289`; template
  `defaultHardwareConfigTemplate()` `:4325`):

  ```ini
  [camera]
  # Highest FPS any control may select on this build (0 = the sensor's own limit).
  max_fps=50
  ```

  Core clamps to it in the sanitiser, and publishes the effective ceiling for the current settings as `fps_max` in the state.
  The UIs cut their lists at `fps_max` instead of keeping their own tables. That also removes the "four copies of the ceiling"
  risk (r1 Risks 9: `CameraController.cpp` table, `maximumPcfFpsForSettings` `App:1162-1171`, WebUI
  `maximumSupportedFpsForSnapshot`, QML `maximumSupportedFpsForResolution`).

Open: Cinemate's "free" stepping (1-fps sweep) and increment. Not asked for explicitly; leave out of T33 unless Patrik wants it.

### 3.2 T34: the mode ladder

> [!note] Design done 2026-10-27: `design/design-T34.md`. It recommends A + R below: rungs change between takes, and an
> opt-in Ramp-ready switch starts a ramp take in the top rung. B is deferred until measured. It also proposes the numbering
> T33 = build max, T34 = ladder, T35 = value lists (its Q12). Mockup of the editor:
> https://claude.ai/artifact/YKbhhk8aMUS8sxEWa6UfRL (private to Patrik).

Patrik's ladder for this build:

| Rung | Mode | FPS range | Ceiling comes from |
| --- | --- | --- | --- |
| 1 | 4K (3840x2160) Clear HDR 16-bit | lowest … 25 | the accepted maximum (T32) |
| 2 | 4K (3840x2160) SDR 12-bit | 25 … 50 | `max_fps=50` (§3.1) |

The editor he wants: drag and drop the activated sensor modes into order (top rung first), an optional threshold per rung
(empty = the mode's own ceiling), and a toggle switch that makes Core honour the ladder.

Facts that shape it (reader reports in this folder, both cite Core `d4ad539`; find the lines on `cinemate-port` by their
search strings):

1. **Cinemate never switches class mid-take.** Class = bit depth + SDR/Clear HDR. While recording it pins the chooser and the FPS
   ceiling to the running class and applies the switch after stop, once the buffer has drained. A same-class switch mid-take
   splits the take into a new clip folder and WAV, with a frame gap (`r2-cinemate.md` §0, §b.1-b.2). Rung 1 → rung 2 is a class
   switch.
2. **A mid-take switch in Core is a full camera reconfigure.** A Clear HDR change rebuilds the CameraManager and changes the
   tuning (`r1-core.md` Risks 3). `stop()` silently ends every recorder (Risks 1); a failed take-scoped reconfigure leaves the
   camera in Error (Risks 2). Expect a hole of a few hundred ms (Cinemate's only figure is ~186 ms, from a preview reconfigure,
   `r2-cinemate.md` §b.3): about 5-9 frames at 25-50 fps, and a new clip whose DNGs change bit depth, black level and look.
3. **4K SDR is capped at 30 in Core** although the probe allows 60 (`tableMaximumFpsForResolution`; `r1-core.md` "What a
   ladder implementation must touch" item 1). Rung 2 needs that cap lifted to the probe, then clamped by `max_fps`.
4. **Storage.** 4K 12-bit uncompressed at 50 fps is about 622 MB/s. The NVMe measured 437 MB/s on PCIe Gen 2
   (`lessons/hardware-log.md`, 2026-10-26). Lossless cDNG on the IMX585 is capped at 30 at every size (`r1-core.md` Risks 8).
   So rung 2 at 50 needs lossy DNG or a faster link. Unmeasured.
5. **The touch UI does not fight a Core-driven FPS change** (§2), but a Core-driven resolution or bit-depth change mid-take has
   not been checked against the UI's other `ensureValid…` paths (`r1-core.md` Risks 10).

Two designs to critique before building:

- **A. Between takes (Cinemate's rule).** With the toggle on, an FPS request outside a take picks the rung that serves it (≤25 →
  rung 1, >25 → rung 2). In a take the FPS ceiling is the running rung's. Simple and safe, but a ramp take started in rung 1
  stops at 25.
- **B. Mid-take switch with a clip split.** Crossing a threshold in a take closes the clip, reconfigures, and opens the next clip:
  one WAV across the take, the take's start rate as the base, the gap written to `fps-ramp.txt`, the switch not persisted,
  and the start rung restored at stop. It needs a new session split that does not use `stop()`, a recovery path, and the
  16 touch points listed in `r1-core.md` "What a ladder implementation must touch". Large, and `CameraController.cpp` cannot
  be compiled off the Pi.

Recommendation to test first: A, plus a "ramp-ready" start. When the toggle is on and a ramp target above 25 is armed, the take
starts in rung 2 and ramps 1 … 50 without a switch. B only if the hole and the look change are acceptable in the edit.

UI notes for the editor: the WebUI has no drag and drop yet. Favorites reorder with ↑/↓ buttons (`moveFavoriteItem`,
`WebControlPage.cpp:6670-6689`, T32 tree). Use pointer events for dragging (touch screens do not fire HTML5 drag events) and
keep ↑/↓ as the fallback. The list of activated modes comes from Core's `list_sensor_modes` (`ApertarCoreApp.cpp:9618`, T31
tree).

## 4. Where the selectable FPS values are (item 2)

- WebUI: `fpsPresets`, `src/web/WebControlPage.cpp:4039` before T32, `:4071` after.
- Touch UI: `availableFpsOptions()`, `qml/CameraPage.qml:807-832@dc471c1`, presets at `:808-812`. `fpsOptions` (`:503`) is
  the property the picker uses (`:2918`); `maximumSelectableFps()` (`:662-666`) takes its last entry.
- Core pots and buttons: `availablePcfFpsOptions()`, `src/ApertarCoreApp.cpp:1174-1192` (T31 tree), presets at `:1178-1181`.

## 5. Files in this folder

- `../ramp-mode-ladder.md`: the first assessment (ceilings, ladders A-D, costs, measurements).
- `r1-core.md`: every Core code path a ladder touches, with risks (reader report, Core `d4ad539`).
- `r2-cinemate.md`: Cinemate's dynamic resolution and what it does mid-take (reader report, cinemate `d6cc93e`).
- `design/design-T34.md`: the ladder design (A + R), measurements first, data model, implementation plan, tutorial outline,
  open questions Q1-Q12. `design/changes-from-critique.md`: what the critics changed. `design/plan-v1.md`,
  `design/critique-code.md`, `design/critique-operator.md`: the steps before it. `design/sketch/`: `ModeLadder.hpp` (no
  libcamera) and its host test (`g++ -std=c++20 -Isketch sketch/mode_ladder_test.cpp`, 28 checks).

Names: since 2026-10-28 the switch is `fps_speed_ramp` / `set_fps_speed_ramp` / `fpsSpeedRamp` (as `fps_phase_lock`). `r1-core.md`,
`r2-cinemate.md`, `../ramp-answer.md`, `../port-raw/` and `design/` files other than `design-T34.md` keep the old names (`fps_ramp`, `set_fps_ramp`, `fpsRampEnabled`).
