---
datum: 2026-10-27 21:30:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T32 speed-ramp-every-control
typ: digital anteckning
---

# T32. Speed ramping from every control: a Cinemate-style WebUI block under Format, a ramp-safe touch UI picker, and 25 fps as the ceiling for 4K Clear HDR 16-bit

Status: written 2026-10-27 (cloud session). Patches, applied after T31 on Core `cinemate-port` (`7a545d9` + T31):
`working/patches/0001-camera-cap-4K-Clear-HDR-16-bit-at-25-fps.patch` and
`working/patches/0001-web-speed-ramp-block-in-the-Recording-format-card.patch`. Touch UI patches on Apertar-UI `cinemate-port`
`dc471c1`, in this order: `working/patches/0001-ui-4K-Clear-HDR-16-bit-offers-FPS-up-to-25.patch`,
`working/patches/0001-ui-FPS-picker-sends-only-set_fps-during-a-speed-ramp.patch`. Line numbers are on those trees with the
patches applied, unless marked `@T31` (Core with T31 only) or `@dc471c1` (UI before the patches). Checked in the cloud: host
`g++ -fsyntax-only` of `WebControlPage.cpp`, `node --check` of the page script, and the page driven in Chromium against a mocked
`/api/state` (seven states, the commands each button sends, no console errors, no sideways scroll at 390 px); the whole touch UI built with
Qt 6.4.2 on the host, QML compiled ahead of time. **Not run against Core on the Pi.** `CameraController.cpp` was not compiled
(libcamera).

**You will learn**
- How a WebUI control reaches Core: the page lives in a C++ raw string, `renderSnapshot` redraws it from `/api/state`, a button
  calls `sendCommand`, which posts to `/api/command`.
- Where the FPS ceiling of a mode lives (three places: Core, WebUI, touch UI) and why they must agree.
- Where the selectable FPS values live. They are the same arrays that the speed-ramp targets use.
- How Cinemate lays out the same controls (SHUTTER SYNC, FPS DOUBLE, the ramp stepper) and what was kept.
- Why every FPS control must leave the shutter to Core during a ramp take, and which one did not.

**Risk:** Core rebuild + restart, UI rebuild + restart. No settings change on its own: speed ramping stays off until you press
On, and the touch UI picker behaves as before outside ramp takes. The 25 fps cap moves a persisted 30 fps Clear HDR 16-bit setting to 25 on the next start. Undo: `git revert` the commits, rebuild.
**Time:** 2 h.

## 1. The problem

- T31 made speed ramping work, but only through socket commands (`core.py set_fps_ramp`, `ramp_fps`). Nothing in the WebUI
  shows whether it is on, which shutter policy runs, or lets you start a ramp.
- Every FPS control becomes a ramp control in a cDNG/MLV take once `fps_ramp` is on. Four send FPS to Core: the WebUI pills,
  the PCF pot and the `fps:<n>` / `fps_up` buttons (`ApertarCoreApp.cpp:8623-8630@T31`, `:8812-8816@T31`) send only
  `set_fps`, which T31 handles. The touch UI picker does more. `ApertarControlBridge::applyFps()`
  (`src/ApertarControlBridge.cpp:255-287@dc471c1`) sends `set_fps`, then its own `set_shutter_us` to keep the angle, then
  saves both. In a ramp take with Shutter Sync = Exposure, that second command undoes the policy, and the save makes a ramp
  step your setting (the mistake Cinemate fixed in `ff59dd8`; Core avoids it since T31).
- 4K Clear HDR 16-bit is clean at 25 fps. At 30 it delivers about 28 and drops frames (`working/research-30fps-answer.md`).
  25 is now the accepted maximum (Patrik, 2026-10-27). All three layers still offer 30:

| Layer | Where @T31 / @dc471c1 | 4K Clear HDR 16-bit today |
| --- | --- | --- |
| Core clamp | `CameraController.cpp:2778-2780@T31`, `tableMaximumFpsForResolution` | 30 (25 only before the sensor probe) |
| WebUI FPS pills | `WebControlPage.cpp:4977-4978@T31`, `maximumSupportedFpsForSnapshot` | 30 |
| Touch UI FPS list | `qml/CameraPage.qml:780-781@dc471c1`, `maximumSupportedFpsForResolution` | 30 |

Cinemate puts the ramp controls on its web UI: SHUTTER SYNC and FPS DOUBLE toggles next to FPS LOCK
(`src/module/app/templates/template.html:1832-1841@d6cc93e`). Its FPS steps are an editable list in the settings editor
(`settings_editor.html:1970-1994`). The per-mode FPS ceiling can be overridden there too (`:3835-3850`, `:4256-4320`).

## 2. How this part works

```
 WebControlPage.cpp: static const char page[] = R"APERTAR(<!DOCTYPE html> ... )APERTAR";   (the whole WebUI)
     |
 browser: fetchState() -> GET /api/state -> ApertarCoreApp::buildWebStateJson()   (fps, fps_ramp, fps_ramp_keep_exposure,
     |                                                                              fps_ramp_stepping, fps_take_base, clear_hdr, raw_bit_depth)
 renderSnapshot(snapshot)
     |  fpsOptions = availableFpsOptionsForSnapshot(snapshot)  = fpsPresets cut at maximumSupportedFpsForSnapshot()
     |  buildOptionButtons("fpsOptions", ...)                    the FPS pills
     |  renderSpeedRamp(snapshot, fpsOptions)                    the new block, same list
     v
 click -> sendCommand({cmd: "ramp_fps", to: 50, seconds: 5})
     |      applyCommandSnapshotPatch(): redraw at once from the payload, before Core answers
     v
 POST /api/command -> ApertarCoreApp::handleCommand -> startFpsRamp() -> camera_.setFps() each step
                                                        |
                                    sanitizeSettingsForSensor(): fps = min(fps, maximumSupportedFpsForResolution())
                                                        = min(tableMaximumFpsForResolution(), sensor probe)
```

Two lists decide what you can pick, and both live in code:

| What | WebUI | Touch UI |
| --- | --- | --- |
| Selectable FPS values | `fpsPresets`, `WebControlPage.cpp:4071` | `presets` in `availableFpsOptions()`, `qml/CameraPage.qml:809-813` |
| Cut at the mode's ceiling | `maximumSupportedFpsForSnapshot()`, `:4962` | `maximumSupportedFpsForResolution()`, `:738` |

The Speed Ramp targets are the WebUI list without the current rate. To ramp from below 24 fps, add values to both preset
lists (for example `12.000, 15.000, 18.000, 20.000`). That also adds them to the FPS pills. Core accepts anything above 0 up to the
mode's ceiling.

Reading assignments: `WebControlPage.cpp:9291-9326` (`sendCommand`), `:9328-9348` (`buildOptionButtons`), `:9509-9550`
(`renderSnapshot`'s first lines), `:5027-5054` (`availableFpsOptionsForSnapshot`); `CameraController.cpp:2736-2834` (the
table and the probe), `:2835-2880` (the sanitiser); `ApertarCoreApp.cpp:9882-9903` (the two T31 commands).

## 3. Find it yourself

Run these before the change, on the Pi with T31 applied.

**3.1 Where are the selectable values?**

```bash
grep -n 'const fpsPresets' ~/ApertarCore/src/web/WebControlPage.cpp                  # the WebUI list
grep -n "fpsOptions" ~/ApertarUI/qml/CameraPage.qml                                  # where the touch UI uses its list
grep -n -A6 'function availableFpsOptions()' ~/ApertarUI/qml/CameraPage.qml           # and where the list is
```

> [!tip]- Answer
> WebUI: one line, `const fpsPresets = [24.000, 25.000, 30.000, ... 280.000];` (`:4039@T31`).
> Touch UI: `fpsOptions` at `:503` (the property), `:663-665` (`maximumSelectableFps()` takes its last entry) and `:2918` (the
> picker); the array itself is in `availableFpsOptions()` at `:808-812@dc471c1`: one list for IMX477, one for IMX577, and
> `[24.000, 25.000, 30.000, 50.000, 60.000]` for everything else, including the IMX585.
> The two lists differ: the WebUI offers 35, 40 and 45, the touch UI does not.

**3.2 What does each layer allow at 4K Clear HDR 16-bit?**

```bash
grep -n -A3 'normalized.width == 3840 && normalized.height == 2160' ~/ApertarCore/src/camera/CameraController.cpp | head -5   # Core
grep -n -A2 '(width === 3856 && height === 2180) || (width === 3840 && height === 2160)' ~/ApertarCore/src/web/WebControlPage.cpp | head -4   # WebUI
grep -n -A1 'resolutionValue === "3856x2180" || resolutionValue === "3840x2160"' ~/ApertarUI/qml/CameraPage.qml | head -4   # touch UI
```

> [!tip]- Answer
> Core: `return clearHdr && !sensorLimitKnown ? 25.0 : 30.0;`. Once the sensor probe knows the mode (it does on your Pi: link
> 891 MHz), Clear HDR gets 30. WebUI and touch UI: `30.0`, with no Clear HDR or bit-depth test at all.

**3.3 What does a WebUI FPS pill send?** Open the WebUI in a desktop browser, open the developer tools on the Network tab, and
press an FPS pill.

> [!tip]- Answer
> `POST /api/command` with `{"cmd":"set_fps","value":25}` (`WebControlPage.cpp:9910-9916@T31`). The Speed Ramp block uses the same
> path with `set_fps_ramp` and `ramp_fps`.

## 4. Make the change

**4.1 Core: 25 fps for 4K Clear HDR 16-bit** — `src/camera/CameraController.cpp:2778-2785`, in `tableMaximumFpsForResolution`,
search `Clear HDR doubles VMAX`. Turn the one-line `if` into a block:

```cpp
        if (normalized.width == 3840 && normalized.height == 2160) {
            // Clear HDR 16-bit: 25 fps is the accepted ceiling. At 30 the back end
            // delivers about 28 and drops frames (KB working/research-30fps-answer.md).
            if (clearHdr && normalizeRawBitDepth(rawBitDepth) == 16)
                return 25.0;
            // Clear HDR doubles VMAX: 30 fps at link 891 MHz, 25 at the driver's default 720 MHz.
            return clearHdr && !sensorLimitKnown ? 25.0 : 30.0;
        }
```

Why here: `maximumSupportedFpsForResolution()` (`:2799`) takes the smaller of this table and the sensor probe, so 25 wins.
`sanitizeSettingsForSensor()` (`:2877`) then clamps every `set_fps`, every `ramp_fps` step and the setting loaded at start.
`normalizeRawBitDepth()` is defined at `:256`, above this function.
**Check:** `grep -c 'normalizeRawBitDepth(rawBitDepth) == 16' src/camera/CameraController.cpp` → 1.

**4.2 WebUI: the same ceiling** — `src/web/WebControlPage.cpp:5011-5013`, in `maximumSupportedFpsForSnapshot`, the first IMX585
`if`:

```js
        // Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution().
        if ((width === 3856 && height === 2180) || (width === 3840 && height === 2160))
          return snapshot.clear_hdr && Number(snapshot.raw_bit_depth) === 16 ? 25.0 : 30.0;
```

`snapshot.raw_bit_depth` arrives as a number (`mergeCameraStateFields` and `/api/state` both use numbers).
**Check:** `grep -c 'Number(snapshot.raw_bit_depth) === 16 ? 25.0' src/web/WebControlPage.cpp` → 1.

**4.3 Touch UI: the same ceiling** (Apertar-UI) — `qml/CameraPage.qml:780-782`, in `maximumSupportedFpsForResolution`:

```qml
        // Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution().
        if (resolutionValue === "3856x2180" || resolutionValue === "3840x2160")
            imx585Max = root.clearHdrActive && root.rawBitDepthValue === "16-bit" ? 25.0 : 30.0
```

`clearHdrActive` (`:454`) and `rawBitDepthValue` (`:357`, formatted `"16-bit"` by `ApertarControlBridge.cpp:1760`) already exist.
**Check:** `grep -c 'rawBitDepthValue === "16-bit" ? 25.0' qml/CameraPage.qml` → 1.

**4.4 The block's HTML** — `WebControlPage.cpp:2918-2951`. In the "Recording format" card, right after the Bit Depth pills
(search `id="settingsRawBitDepthOptions"`) and before the card's closing `</div>`. It reuses the card's own classes, so it looks
like the Bit Depth block above it:

```html
              <div class="settings-card-head compact-head">
                <div>
                  <h3 class="settings-card-title">Speed Ramp</h3>
                  <p class="settings-card-copy" id="settingsSpeedRampNote">Change FPS during a CinemaDNG or MLV take.</p>
                </div>
                <div class="online-pill" id="settingsSpeedRampValue">Off</div>
              </div>
              <div class="pill-grid" id="settingsSpeedRampOptions"></div>
              <div class="field-stack">
                <span class="input-label">Shutter Sync</span>
                <div class="pill-grid" id="settingsSpeedRampShutterOptions"></div>
                <p class="settings-card-copy">Angle keeps the motion blur. Exposure keeps the brightness.</p>
              </div>
              <div class="settings-field-grid">
                <label class="field-stack">
                  <span class="input-label">Ramp to</span>
                  <select class="settings-select" id="settingsSpeedRampTargetSelect"></select>
                </label>
                <label class="field-stack">
                  <span class="input-label">Over</span>
                  <select class="settings-select" id="settingsSpeedRampSecondsSelect">
                    <option value="0">Cut</option>
                    <option value="1">1 s</option>
                    <option value="2">2 s</option>
                    <option value="5" selected>5 s</option>
                    <option value="10">10 s</option>
                    <option value="20">20 s</option>
                  </select>
                </label>
              </div>
              <div class="pill-grid three-col" id="settingsSpeedRampActions"></div>
              <p class="settings-card-copy" id="settingsSpeedRampRange"></p>
```

What each part is, against Cinemate:

| Control | Command | Cinemate |
| --- | --- | --- |
| Speed Ramp Off / On | `set_fps_ramp enabled` | none: Cinemate always ramps; T31 made it opt-in |
| Shutter Sync Angle / Exposure | `set_fps_ramp shutter=angle\|exposure` | SHUTTER SYNC (`shutter_a_sync`); in Cinemate it only changes the displayed angle, here it changes the exposure the sensor gets |
| Ramp to … over … | `ramp_fps to seconds` | `_ramp_fps`, fixed 0.2 s per fps |
| ×2 → 50 fps / Back → 25 fps | `ramp_fps to=2×base` / `to=base` | FPS DOUBLE (`set_fps_double`) |
| Pill: Off, On · Angle, On · Exposure, Ramping | reads `fps_ramp`, `fps_ramp_keep_exposure`, `fps_ramp_stepping` | the tinted FPS/shutter group |

**Check:** `grep -c 'settingsSpeedRamp' src/web/WebControlPage.cpp` → 8 after this step (17 after 4.8).

**4.5 The render function** — `WebControlPage.cpp:5058-5156`. Insert it just above `function availableIsoOptionsForSnapshot`
(search for it). This is the longest step. Type it in four parts and read each part before you go on.

Part 1, three helpers. Core refuses a mid-take FPS change for H.264, ProRes and stills; the block says so instead of failing.
`recording_format` is `cdng`, `lossydng` or `mlv` for the raw formats (`include/apertar/core/Types.hpp:272-275`).

```js
    // Speed ramp (T31). Cinemate's SHUTTER SYNC, FPS DOUBLE and _ramp_fps as one block.
    // Core refuses an FPS change in a take unless fps_ramp is on and the take is
    // CinemaDNG (any compression) or MLV; fps_ramp itself only changes between takes.
    function speedRampFormatSupported(snapshot) {
      const format = String(snapshot && snapshot.recording_format || "").toLowerCase();
      return !stillCaptureForSnapshot(snapshot) && (format === "cdng" || format === "lossydng" || format === "mlv");
    }

    function speedRampFpsLabel(value) {
      return String(Number(value)) + " fps";
    }

    async function startSpeedRamp(toFps) {
      const seconds = Number(document.getElementById("settingsSpeedRampSecondsSelect").value) || 0;
      try {
        await sendCommand({ cmd: "ramp_fps", to: Number(toFps), seconds });
      } catch (error) {
        showToast(error.message, true);
      }
    }
```

Part 2, the state and the texts. `canRamp` follows Core's own rules (`CameraController::setFps`): outside a take any ramp is
fine; in a take only with ramping on and a raw format; never while the stepper runs.

```js
    function renderSpeedRamp(snapshot, fpsOptions) {
      const enabled = snapshot.fps_ramp === true;
      const keepExposure = snapshot.fps_ramp_keep_exposure === true;
      const stepping = snapshot.fps_ramp_stepping === true;
      const recording = !!snapshot.recording;
      const formatSupported = speedRampFormatSupported(snapshot);
      const takeBase = recording ? Number(snapshot.fps_take_base) || 0 : 0;
      const currentFps = Number(snapshot.fps) || 0;
      // The highest value in the selectable list, as the camera UI's maximumSelectableFps().
      const highestFps = fpsOptions.length > 0 ? Number(fpsOptions[fpsOptions.length - 1]) : currentFps;
      const canRamp = !stepping && (!recording || (enabled && formatSupported));
      const nearly = (a, b) => Math.abs(a - b) < 0.0005;

      setText("settingsSpeedRampValue", !enabled ? "Off" : (stepping ? "Ramping" : (keepExposure ? "On · Exposure" : "On · Angle")));
      setText("settingsSpeedRampNote", !formatSupported
        ? "Works in CinemaDNG and MLV. H.264, ProRes and stills keep one rate per clip."
        : (takeBase > 0 && enabled
          ? "This take runs at " + speedRampFpsLabel(takeBase) + ": every frame is numbered at that rate, so a faster stretch plays as slow motion. Stop returns to it."
          : "Change FPS during a CinemaDNG or MLV take. The clip keeps the rate it started with, so a faster stretch plays as slow motion."));
      setText("settingsSpeedRampRange", "Selectable in this mode: " + speedRampFpsLabel(fpsOptions[0] || currentFps)
        + " to " + speedRampFpsLabel(highestFps) + "." + (recording && !enabled ? " Turn ramping on before the take." : ""));
```

Part 3, the two pill rows. On/Off is greyed out in a take because Core refuses to toggle it then
(`CameraController::setFpsRamp`, "Stop recording before turning FPS ramping on or off."). The shutter policy may change mid-take.

```js
      buildOptionButtons("settingsSpeedRampOptions", [
        { label: "Off", value: "Off", enabled: !recording },
        { label: "On", value: "On", enabled: !recording },
      ], enabled ? "On" : "Off", async (value) => {
        try {
          await sendCommand({ cmd: "set_fps_ramp", enabled: value === "On" ? "true" : "false" });
        } catch (error) {
          showToast(error.message, true);
        }
      }, 2);

      buildOptionButtons("settingsSpeedRampShutterOptions", [
        { label: "Angle", value: "angle", enabled },
        { label: "Exposure", value: "exposure", enabled },
      ], keepExposure ? "exposure" : "angle", async (value) => {
        try {
          await sendCommand({ cmd: "set_fps_ramp", enabled: "true", shutter: value });
        } catch (error) {
          showToast(error.message, true);
        }
      }, 2);
```

Part 4, the target list and the three actions. `ensureSelectEntries` (`:6386`) only rebuilds the `<select>` when the list
changed. The chosen target is kept in `state.speedRampTarget` (4.8), because the block is redrawn on every state poll.

```js
      // Same list as the FPS pills: edit fpsPresets and both follow.
      const targets = fpsOptions.filter((value) => !nearly(Number(value), currentFps));
      ensureSelectEntries("settingsSpeedRampTargetSelect", targets.map((value) => ({ value, label: speedRampFpsLabel(value) })));
      const targetSelect = document.getElementById("settingsSpeedRampTargetSelect");
      if (targetSelect) {
        if (targets.includes(state.speedRampTarget))
          targetSelect.value = state.speedRampTarget;
        else if (targets.length > 0)
          targetSelect.value = targets[targets.length - 1];
        targetSelect.disabled = !canRamp || targets.length === 0;
      }

      // ×2 doubles the take's start rate (Cinemate's FPS DOUBLE); Back returns to it,
      // or outside a take to the rate before the last ×2.
      const doubleBase = takeBase > 0 ? takeBase : currentFps;
      const doubleFps = doubleBase * 2;
      const backFps = takeBase > 0 ? takeBase : (Number(state.speedRampReturnFps) || 0);
      buildOptionButtons("settingsSpeedRampActions", [
        { label: "Ramp", value: "ramp", enabled: canRamp && targets.length > 0 },
        { label: "×2 → " + speedRampFpsLabel(doubleFps), value: "double", enabled: canRamp && doubleFps <= highestFps + 0.0005 && !nearly(doubleFps, currentFps) },
        { label: backFps > 0 ? "Back → " + speedRampFpsLabel(backFps) : "Back", value: "back", enabled: canRamp && backFps > 0 && !nearly(backFps, currentFps) },
      ], "", async (value) => {
        if (value === "ramp" && targetSelect) {
          await startSpeedRamp(targetSelect.value);
        } else if (value === "double") {
          if (takeBase <= 0)
            state.speedRampReturnFps = currentFps;
          await startSpeedRamp(doubleFps);
        } else if (value === "back") {
          await startSpeedRamp(backFps);
        }
      }, 3);
    }
```

**Check:** `grep -c 'function renderSpeedRamp\|function startSpeedRamp\|function speedRampFormatSupported' src/web/WebControlPage.cpp` → 3.

**4.6 Call it** — `WebControlPage.cpp:10149`, in `renderSnapshot`, right after the `buildOptionButtons("settingsRawBitDepthOptions", …)`
call ends (`}, 3);`) and before `buildOptionButtons("settingsGyroDataOptions"`:

```js
      renderSpeedRamp(snapshot, fpsOptions);
```

`fpsOptions` is already computed at the top of `renderSnapshot` (`:9547`).
**Check:** `grep -c 'renderSpeedRamp(snapshot, fpsOptions);' src/web/WebControlPage.cpp` → 1.

**4.7 Redraw at once after a click** — two places. Without them the pills only change on the next state poll, about
150 ms later.

In `mergeCameraStateFields` (`:8761`), at the end, after the `recording_elapsed_seconds` lines (`:8843-8846`). Command replies
carry the settings JSON, which has the two ramp fields since T31:

```js
      if (typeof source.fps_ramp === "boolean")
        snapshot.fps_ramp = source.fps_ramp;
      if (typeof source.fps_ramp_keep_exposure === "boolean")
        snapshot.fps_ramp_keep_exposure = source.fps_ramp_keep_exposure;
```

In `applyCommandSnapshotPatch` (`:8848`), after `case "set_fps":` (`:8880-8892`):

```js
        case "set_fps_ramp":
          snapshot.fps_ramp = boolValue;
          if (typeof payload.shutter === "string")
            snapshot.fps_ramp_keep_exposure = payload.shutter === "exposure";
          break;
        case "ramp_fps":
          if (isFiniteNumber(payload.to) && !(Number(payload.seconds) > 0))
            snapshot.fps = Number(payload.to);
          else
            snapshot.fps_ramp_stepping = true;
          break;
```

**Check:** `grep -c 'case "set_fps_ramp":\|case "ramp_fps":' src/web/WebControlPage.cpp` → 2.

**4.8 Page state and the listener** — in `const state = {` (`:4236`) add two fields after `snapshot: null,`:

```js
      speedRampTarget: "",
      speedRampReturnFps: 0,
```

Next to the other settings listeners (search `settingsRecordResolutionSelect").addEventListener`, `:11578`), add:

```js
      document.getElementById("settingsSpeedRampTargetSelect").addEventListener("change", (event) => {
        state.speedRampTarget = event.target.value;
      });
```

**Check:** `grep -c 'settingsSpeedRamp' src/web/WebControlPage.cpp` → 17.

**4.9 Touch UI: the picker leaves the shutter to Core in a ramp take** (Apertar-UI) — two places in
`src/ApertarControlBridge.cpp` and one member.

In `src/ApertarControlBridge.hpp:318`, below `bool m_recording = false;`:

```cpp
    bool m_fpsRamp = false; // Core's fps_ramp (T31): FPS may change during a raw take
```

In `applyCoreState` (`:1368-1369`), right after the two `shutter_auto` lines (search `m_shutterAuto = state.value`). Core's
state, its settings events and every command reply carry `fps_ramp` since T31:

```cpp
    if (state.contains(QStringLiteral("fps_ramp")))
        m_fpsRamp = state.value(QStringLiteral("fps_ramp")).toBool(m_fpsRamp);
```

In `applyFps` (`:273-278`), right after the `set_fps` call succeeds and before `setFps(formatFpsValue(fpsValue));`:

```cpp
    // A ramp step in a take (T31): Core applies the shutter policy (angle or
    // exposure) and restores the take's start rate at stop, and sendCoreCommand has
    // already applied its reply. Send nothing more: a set_shutter_us here would undo
    // the exposure policy, and saving would make a take-scoped rate the setting.
    if (m_recording && m_fpsRamp)
        return true;
```

Why this is enough: `sendCoreCommand` runs every message, including the reply, through `applyCoreMessage` (`:1095`), so FPS and
shutter on screen already show what Core set. Outside ramp takes the function runs as before. `ensureValidFpsSelection()`
(`qml/CameraPage.qml:1557-1558`) returns at once when the bridge exists, so the in-between rates of a stepper (26, 27 …) are
not "corrected" by the UI.
**Check:** `grep -c 'm_fpsRamp' src/ApertarControlBridge.cpp` → 2.

**4.10 Host checks before the Pi build** (Mac or Pi). The C++ compiler only sees one long string, so check the JavaScript on
its own too:

```bash
cd ~/ApertarCore
g++ -std=c++20 -fsyntax-only -Isrc -Iinclude src/web/WebControlPage.cpp && echo cpp ok          # the raw string still closes
python3 -c "import re,sys; s=open('src/web/WebControlPage.cpp').read(); a=s.index('R\"APERTAR(')+10; b=s.index(')APERTAR\"',a); open('/tmp/page.js','w').write('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', s[a:b], re.S)))"
node --check /tmp/page.js && echo js ok                                                       # no JS syntax error
```

`node` is on the Mac; on the Pi, skip the last line if `node` is missing.

## 5. Build, deploy, test

Core (Pi; no take running):

```bash
cmake --build /home/pi/ApertarCore-build -j2          # builds Core, including the WebUI page
sudo systemctl restart apertar-core                    # Patrik
```

Touch UI (Pi):

```bash
cmake --build /home/pi/ApertarUI/build -j2            # QML is compiled in: no rebuild, no change
sudo systemctl restart apertar-ui-direct               # Patrik
```

**5.1 The ceiling.** 4K Clear HDR 16-bit:

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_fps value=30          # ask for 30
python3 -I ~/apertar-kb/working/tools/core.py get_state | grep -o '"fps":[0-9.]*'   # Core keeps 25
```

What you see: `"fps":25`. The WebUI FPS pills end at 25, and so does the touch UI picker. Switch Clear HDR off or to 12-bit: 30
comes back in all three.

**5.2 The block.** WebUI → Settings → Record → Recording format, below Bit Depth:

| Mode | You see |
| --- | --- |
| 4K Clear HDR 16-bit, 25 fps, ramp off | pill `Off`; Shutter Sync greyed out; "Selectable in this mode: 24 fps to 25 fps."; `×2 → 50 fps` greyed out |
| On, Exposure | pill `On · Exposure` |
| 2K (1920x1080) 12-bit, 25 fps | "24 fps to 60 fps"; `×2 → 50 fps` active |
| H.264 | "Works in CinemaDNG and MLV. …"; Ramp, ×2 and Back greyed out during a take |

**5.3 One ramp take** (2K cDNG uncompressed, 25 fps, audio on, a clock in frame). Use the block, not `core.py`:

1. Speed Ramp `On`, Shutter Sync `Angle`.
2. Record. The note changes to "This take runs at 25 fps …". On/Off greys out.
3. Over `5 s`, press `×2 → 50 fps`. The pill shows `Ramping`, then `On · Angle` at 50.
4. Press `Back → 25 fps`.
5. Stop.

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp (stats|stopped)' | tail -3   # changes=50 base_fps=25 min_fps=25 max_fps=50
```

The rest of the take is judged as in T31 §5.1-§5.2 (`fps-ramp.txt`, `FrameRate`, Resolve).

**5.4 Touch UI picker in a ramp take.** Shutter Sync `Exposure`, 2K cDNG at 25 fps, 180°. Record, pick 50 on the touch UI
FPS picker, then 25, then stop.

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'fps ramp: 25 -> 50|fps ramp: 50 -> 25|set_shutter_us' | tail -4
```

What you see: two `fps ramp:` request lines and no `set_shutter_us` from the UI during the take. The shutter readout stays at
20 ms (Exposure keeps it; at 50 fps the angle reads 360°). After stop, the picker shows 25 again. Repeat with `Angle`: the
shutter readout halves at 50 and the angle stays 180°.

**5.5 Phone.** Open the WebUI on the phone: the block fits the width; the three actions wrap to two columns.

## 6. Commit

Core, two commits on `cinemate-port` (messages as in the two patches):

```bash
git -C ~/ApertarCore add src/camera/CameraController.cpp src/web/WebControlPage.cpp   # only the 4.1 and 4.2 hunks: git add -p
git -C ~/ApertarCore commit                                                        # "camera: cap 4K Clear HDR 16-bit at 25 fps"
git -C ~/ApertarCore add src/web/WebControlPage.cpp
git -C ~/ApertarCore commit                                                        # "web: speed-ramp block in the Recording format card"
git -C ~/ApertarUI add qml/CameraPage.qml
git -C ~/ApertarUI commit                                                          # "ui: 4K Clear HDR 16-bit offers FPS up to 25"
git -C ~/ApertarUI add src/ApertarControlBridge.cpp src/ApertarControlBridge.hpp
git -C ~/ApertarUI commit                                                          # "ui: FPS picker sends only set_fps during a speed-ramp take"
```

Add fork-log rows for the four commits. Pushing follows `working/mac-driven-loop.md` and happens only when you decide.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| WebUI blank, console says `Unexpected token` | a JS typo in 4.5-4.8 | run the 4.9 `node --check`; it names the line in `/tmp/page.js` |
| Build error `unterminated raw string` | `)APERTAR"` was typed into the page | the page must not contain that sequence; remove it |
| No Speed Ramp block | 4.4 placed outside the Recording format card | it goes before the card's closing `</div>`, after `settingsRawBitDepthOptions` |
| Block shows, pills empty | 4.6 missing or after a `return` | `renderSpeedRamp(snapshot, fpsOptions);` right after the bit-depth buttons |
| `Stop recording before turning FPS ramping on or off.` toast | pressed On/Off in a take | expected: turn it on before the take |
| `FPS ramping works in cDNG and MLV takes only.` toast | ramp pressed during an H.264/ProRes take | expected; the buttons should be grey, so check `speedRampFormatSupported` |
| Core still accepts 30 in Clear HDR 16-bit | 4.1 not built, or `rawBitDepth` is not 16 | `get_state` → `raw_bit_depth`; rebuild Core |
| WebUI shows 30, Core keeps 25 | 4.2 missing | the pill snaps back to 25 on the next poll; add 4.2 |
| Touch UI shows 30 | 4.3 not built (QML needs the UI build) | `cmake --build /home/pi/ApertarUI/build -j2`, restart |
| Exposure policy, but the shutter rescales when you use the touch UI picker | 4.9 missing, or the UI not rebuilt | `grep -c m_fpsRamp src/ApertarControlBridge.cpp` → 2; rebuild the UI |
| `Ramp to` jumps back to the highest value | the target equals the current rate, so it left the list | expected; pick another value |

Undo: `git revert` the two Core commits and the two UI commits, rebuild both. A Clear HDR 16-bit setting stays at 25 until you set it.

## 8. What you learned, going further

- A WebUI control is three things in one file: HTML in the raw string, a render function fed by `/api/state`, and a
  `sendCommand` call that Core answers. The optimistic patch makes the click feel instant; the next poll corrects it.
- One ceiling, three copies. Core is the authority, because its sanitiser clamps whatever arrives. The two UIs only decide what
  they offer. When they disagree, a pill snaps back.
- The selectable FPS values are code arrays: `fpsPresets` in the WebUI and `presets` in the touch UI's `availableFpsOptions()`.
  They already differ (35/40/45). Keeping them in step is a choice you make.
- Exercise: add `12.000, 15.000, 18.000, 20.000` to both lists. Then ramp a 4K Clear HDR 16-bit take from 12 to 25 and back.
- Next: the mode ladder (T33). Clear HDR 16-bit up to 25, then 4K SDR 12-bit up to a maximum of 50 set in the settings. Its
  rows go into this same block. Cinemate's equivalents are the Dynamic Resolution card and the per-mode FPS ceiling overrides
  (`settings_editor.html:2038-2045`, `:3835-3850`).

## 9. Sources

- Apertar-Core `cinemate-port` `7a545d9` + T31 + this patch: `CameraController.cpp:2736-2834`, `:2835-2880`, `:256`;
  `WebControlPage.cpp:2918-2951`, `:4071`, `:4236-4239`, `:4962-5054`, `:5058-5156`, `:6386`, `:8761-8846`, `:8848-8895`,
  `:9291-9348`, `:9509-9550`, `:10149`, `:11578-11581`; `ApertarCoreApp.cpp:7248-7253`, `:7731`, `:7805`, `:7947-7948`,
  `:9882-9903`; `include/apertar/core/Types.hpp:272-275`.
- Apertar-UI `cinemate-port` `dc471c1` + these patches: `qml/CameraPage.qml:357`, `:454`, `:503`, `:662-666`, `:738-806`,
  `:808-833`, `:1557-1570`, `:2919`; `src/ApertarControlBridge.cpp:255-294`, `:1033-1110`, `:1365-1369`, `:1756-1761`;
  `src/ApertarControlBridge.hpp:317-318`.
- cinemate `d6cc93e`: `src/module/app/templates/template.html:1799-1841`, `settings_editor.html:1970-1994`, `:2038-2045`,
  `:3835-3850`, `:4256-4320`; `src/module/cinepi_controller.py:4074-4136` (`set_fps_double`, `_ramp_fps`).
- `working/research-30fps-answer.md` (why 25), T31 and `working/ramp-answer.md` (what the commands do).

%% tutor
ref core src/camera/CameraController.cpp 2781 if (clearHdr && normalizeRawBitDepth(rawBitDepth) == 16)
ref core src/web/WebControlPage.cpp 4071 const fpsPresets = [24.000, 25.000, 30.000, 35.000
ref core src/web/WebControlPage.cpp 5013 return snapshot.clear_hdr && Number(snapshot.raw_bit_depth) === 16 ? 25.0 : 30.0;
ref core src/web/WebControlPage.cpp 2921 <h3 class="settings-card-title">Speed Ramp</h3>
ref core src/web/WebControlPage.cpp 5079 function renderSpeedRamp(snapshot, fpsOptions) {
ref core src/web/WebControlPage.cpp 10149 renderSpeedRamp(snapshot, fpsOptions);
ref core src/web/WebControlPage.cpp 8880 case "set_fps_ramp":
ref core src/web/WebControlPage.cpp 9291 async function sendCommand(payload) {
ref ui qml/CameraPage.qml 782 imx585Max = root.clearHdrActive && root.rawBitDepthValue === "16-bit" ? 25.0 : 30.0
ref ui qml/CameraPage.qml 809 var presets = root.imx477Detected
ref ui src/ApertarControlBridge.cpp 277 if (m_recording && m_fpsRamp)
check 3.1 | grep -c 'const fpsPresets' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^1$
check 4.1 | grep -c 'normalizeRawBitDepth(rawBitDepth) == 16' /home/pi/ApertarCore/src/camera/CameraController.cpp | ^1$
check 4.2 | grep -c 'Number(snapshot.raw_bit_depth) === 16 ? 25.0' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^1$
check 4.3 | grep -c 'rawBitDepthValue === "16-bit" ? 25.0' /home/pi/ApertarUI/qml/CameraPage.qml | ^1$
check 4.5 | grep -c 'function renderSpeedRamp\|function startSpeedRamp\|function speedRampFormatSupported' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^3$
check 4.6 | grep -c 'renderSpeedRamp(snapshot, fpsOptions);' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^1$
check 4.7 | grep -c 'case "set_fps_ramp":\|case "ramp_fps":' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^2$
check 4.8 | grep -c 'settingsSpeedRamp' /home/pi/ApertarCore/src/web/WebControlPage.cpp | ^17$
check 4.9 | grep -c 'm_fpsRamp' /home/pi/ApertarUI/src/ApertarControlBridge.cpp | ^2$
check 5.1 | curl -s -m 3 http://127.0.0.1:8000/api/state | grep -o '"fps":[0-9.]*' | "fps":
%%

#CINEMATE
#APERTAR
