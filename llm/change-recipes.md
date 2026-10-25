# Change recipes: touch these places

For each common change: the files in order, what to rebuild and restart, how to verify, and the trap that makes it "do nothing". Research 2026-10-25 (desk). None of these recipes has been walked on the Pi yet: mark a recipe **confirmed** once it has. Entry point: [README.md](README.md). Lists that must change together: [core-map.md](core-map.md) §4, [ui-map.md](ui-map.md) §4.

| Repo | Local HEAD | Cite as | Note |
| --- | --- | --- | --- |
| `~/Documents/Apertar/Apertar-Core` | `ed400ba` | `upstream-1.6.0` | `git diff upstream-1.6.0 HEAD` = `.gitignore` + one mode bit. `src/` identical |
| `~/Documents/Apertar/Apertar-UI` | `29ed99b` | `upstream-1.6.0` | `git diff upstream-1.6.0 HEAD -- src qml CMakeLists.txt` = empty (only a mode bit on `run_pi_direct.sh`) |
| `~/Documents/Apertar/imx585-v4l2-driver` | `e5b74d3` (branch `apertar`) | `e5b74d3` | 21-entry `supported_modes[]` with aspect crops. **Not** the `main` layout that `apertar-kb/architecture/drivers.md` describes |

Conventions:
- `Core/` = `Apertar-Core/`, `UI/` = `Apertar-UI/`, `drv/` = `imx585-v4l2-driver/`.
- `App` = `Core/src/ApertarCoreApp.cpp`. `CC` = `Core/src/camera/CameraController.cpp`. `CB` = `UI/src/ApertarControlBridge.cpp`. `WCP` = `Core/src/web/WebControlPage.cpp`.
- Every line number came from `grep -n` at the HEADs above.
- **Anchor** = a string to `grep -rnF` when lines move. Anchors were checked with `grep -rF -c`; count is 1 unless the row says otherwise.
- Status words follow the KB rule: **confirmed** (seen in code), **probable**, **unconfirmed** (+ the command that settles it).

## B. Change recipes

Build/restart (from `apertar-kb/architecture/build.md`):

| Binary | Rebuild on Pi | Restart |
| --- | --- | --- |
| Core (incl. WebUI HTML/JS) | `cmake --build /home/pi/ApertarCore-build -j2` | `sudo systemctl restart apertar-core` |
| UI (incl. all QML) | `cmake --build /home/pi/ApertarUI/build -j2` | `sudo systemctl restart apertar-ui-direct` |
| CFE automounter | UI build, then `sudo install -m 755 -o root -g root build/apertar-cfe-automounter /usr/local/libexec/` | `sudo systemctl restart apertar-cfe-automounter` |
| Driver | `cd ~/drivers/imx585-v4l2-driver && ./setup.sh` | `sudo reboot` |

Quick socket test without the UI (no `Origin` header passes the WebUI check, `Core/src/web/WebServer.cpp:161`):
`curl -s -X POST http://apertar.local:8000/api/command -d '{"cmd":"ping"}'` → `{"ok":true,"pong":true}`.

### B1. Add a new socket command

| Step | Place | path:line (pattern) | Anchor |
| --- | --- | --- | --- |
| 1 | Core handler | New `if (command.name == "my_cmd")` in `handleCommand`, near `ping` `App:9212-9213`. Reply with `okReply`/`errorReply` (`App:108-128`) | `if (command.name == "ping")` |
| 2 | Core gates | If it captures or touches media, add it to the gates `App:9095-9117`, `:9208-9211` | — |
| 3 | Core help | Append to the `help` string `App:9216` | `"\"commands\":[\"get_state\"` |
| 4 | Core build + restart | Test with `curl … -d '{"cmd":"my_cmd"}'` | — |
| 5 | UI bridge | `Q_INVOKABLE bool myCmd(...)` in `UI/src/ApertarControlBridge.hpp:98-141`; body `return sendCoreCommand("my_cmd", {...})` (pattern `CB:1108-1111`). If slow, add to the reconfigure timeout list `CB:1016-1028` | `bool ApertarControlBridge::applyExposureCompensation` |
| 6 | QML | `apertarControlBridge.myCmd()` (global), or `root.controlBridge.myCmd()` on CameraPage | — |
| 7 | UI build + restart | — | — |
| 8 | WebUI (optional) | `sendCommand({cmd:"my_cmd"})` (`WCP:9109`); patch case in `applyCommandSnapshotPatch` (`WCP:8678`) | `async function sendCommand(payload)` |

Trap: an arg that is a nested object or array silently breaks the flat parser (`Core/src/ipc/ControlProtocol.cpp:120-135`, `:164-233`). Send scalars only. Second trap: only Core rebuilt → UI calls a method that exists only in source; QML reports `TypeError … is not a function` in the UI journal.

### B2. Add a persisted camera setting, shown in UI and WebUI

| Step | Place | path:line (pattern) |
| --- | --- | --- |
| 1 | Field + default | `CaptureSettings`, `Core/include/apertar/core/Types.hpp:124-162` |
| 2 | Clamp | `clampCaptureSettings` `CC:534` |
| 3 | Load | `loadPersistedCaptureSettings` `CC:616`, key parse pattern `CC:657` (`key == "iso"`) |
| 4 | Save | `writeCaptureSettings` `CC:742`, pattern `CC:748` |
| 5 | libcamera control (if any) | `controlsForSettings` `CC:2005`, pattern `CC:2059-2061` |
| 6 | Setter | declare `Core/src/camera/CameraController.hpp:41` pattern; body pattern `setIso` `CC:7774`. Pass `true` to `applySettingsLocked` only if it changes the stream |
| 7 | Command | pattern `App:9242-9249`; add to `help` `App:9216` |
| 8 | Reply + event + web | **three copies**: `settingsBody` `App:167-216`, `settingsEvent` `CC:136-191`, `buildWebStateJson` `App:7835+` (pattern `:7861`) |
| 9 | Presets (optional) | export pattern `App:6664` (`cameraIso`), import pattern `App:10364` |
| 10 | UI property | `Q_PROPERTY` in `UI/src/ApertarControlBridge.hpp:16-58`; read in `applyCoreState` `CB:1261-1555` (pattern `:1371-1375`); invokable (B1 step 5) |
| 11 | QML | bind `apertarControlBridge.x`, or on CameraPage: local copy (`CameraPage.qml:341`) + `Connections` handler (`:1824`, `:1843`) |
| 12 | WebUI | `renderSnapshot` `WCP:9327`; `applyCommandSnapshotPatch` `WCP:8678`; a control calling `sendCommand` |

Rebuild Core + UI. Restart both. Verify: `cat ~/.config/apertar-core/camera_settings.conf | grep x=`; `curl -s http://apertar.local:8000/api/state | python3 -m json.tool | grep x`; restart Core and check the value survives.
Trap: forgetting step 4 → the value works until the next Core restart, then resets. Second trap: settings are stored **per format profile** (`profile.cdng.…`, `CC:8725-8731`), so switching record format can show a different value.

### B3. Add a key to `apertar-hardware.conf`

The file has a parser per binary. "Three separate parsers" = the three binaries that read it: **Core**, **UI**, **CFE automounter**. Inside Core and UI each class has its own copy (about 14 in total, `apertar-kb/architecture/config.md` §1). Core's embedded Python NVMe watcher (`App:3380-3602`) is a fourth reader of `[cfexpress_hat]`.

| Step | Place | path:line |
| --- | --- | --- |
| 1 | Pick the owner | `[display]`/`[ina219]`/`[imu]`/`[network]` → UI; `[pcf8574]`/`[neorotary4]`/`[gpio_*]`/`[trigger_output]`/`[recording_indicator]`/`[run_script]` → Core; `[cfexpress_hat]`/`[storage]` → automounter (+ Python) |
| 2a | Core class | Field + default in the class `Config` (e.g. `Core/src/hardware/NeoRotary4Input.hpp:36-48`); parse `else if (key == "…")` in the loader (e.g. `NeoRotary4Input.cpp:400-422`) |
| 2b | UI | `[display]`: member + CONSTANT `Q_PROPERTY` (`UI/src/DisplayConfigBridge.hpp:9-23`), read in `loadConfiguration` (`UI/src/DisplayConfigBridge.cpp:575-654`, pattern `readConfigDouble(... "zoom_toggle_factor" ...)` `:634-638`) |
| 2c | Automounter | `loadConfig` `UI/src/CfeAutomounter.cpp:131-191` |
| 3 | Templates (all three) | Core WebUI template `App:4291` (`defaultHardwareConfigTemplate`); UI first-run `UI/src/DisplayConfigBridge.cpp:41` (`ensureDefaultHardwareConfigFile`); UI INA219 copy `UI/src/Ina219Bridge.cpp:69` |
| 4 | Rebuild the owner; restart the owner | Core: `apertar-core`; UI: `apertar-ui-direct`; automounter: rebuild UI, **install to `/usr/local/libexec`**, restart `apertar-cfe-automounter` |

Verify: the class's startup log line (e.g. `PCF8574 input enabled: …`, `Apertar display config: path=… size=…` at `UI/src/main.cpp:280`); `apertar-cfe-automounter --check-config` (`UI/src/CfeAutomounter.cpp:760-771`).
Traps:
- Editing `/boot/firmware/apertar-hardware.conf`: dead once `/home/pi/apertar-hardware.conf` exists (the UI creates it, `DisplayConfigBridge.cpp:587`).
- Inline comments: Core INA219 and the Python helper do not strip them from integers (`bus=4 # x` keeps the default). UI uses `QSettings` INI; inline `#` handling there is **probable** to break values the same way (settle: put `ui_width=1280 # x` and read the startup log).
- Saving in the WebUI (`POST /api/config`) does **not** reload Core inputs. Restart Core.

### B4. Add a hardware button action name

| Step | Place | path:line |
| --- | --- | --- |
| 1 | Normalizers (**three copies**) | `normalizeSingleAction` in `Core/src/hardware/Pcf8574Input.cpp:140`, `GpioInput.cpp:108`, `NeoRotary4Input.cpp:121`. Needed only for aliases: unknown names already pass through unchanged (`NeoRotary4Input.cpp:214`) |
| 2 | Handler | New `if (action == "my_action")` in `handleSingleHardwareInputAction` `App:8660-8955`, **before** the final `unknown action` line (`App:8954`). Use the `dispatch(...)` lambda (`App:8671-8677`) or `toggleSharedUiBoolAction` (`App:8468-8478`) |
| 3 | UI-only actions | `publishEvent("{\"event\":\"hardware_action\",\"action\":\"my_action\"}")` (pattern `App:8949-8951`); handle in `UI/qml/Main.qml:285-332` `onHardwareActionTriggered` (bridge emits at `CB:1251-1255`) |
| 4 | Template comments | action lists in the three templates (B3 step 3) |
| 5 | Map it | e.g. `[pcf8574]` `pin3=my_action`; rebuild + restart Core (and UI for step 3) |

Verify: `sudo journalctl -u apertar-core -f` while pressing. Trap: a typo or a missing branch logs only `Hardware input action ignored: unknown action 'x'.` (`App:8954`). A rotation never fires a `standby` action, and any input in Standby only wakes (`App:8642-8656`).

### B5. Add a `UI.conf`-backed setting the WebUI can also change

| Step | Place | path:line (pattern = zebra) |
| --- | --- | --- |
| 1 | UI property | `Q_PROPERTY` `UI/src/SettingsBridge.hpp:17`; getter/signal `:99`, `:307`; member `:414` |
| 2 | UI load | constructor `UI/src/SettingsBridge.cpp:324` |
| 3 | UI setter | `UI/src/SettingsBridge.cpp:597-607` (keep the `m_externalSettingsSyncing` guard) |
| 4 | UI external sync | `pollExternalSettings` `UI/src/SettingsBridge.cpp:520` |
| 5 | UI presets | export `:2033`, import `:2121` |
| 6 | QML | `SettingsPage.qml` `Component` (copy zebra `:2686-2713`), id in `default*Order` (`:771-826`), branch in `*ComponentForId` (`:2216`); consumer binding (e.g. `CameraPage.qml:1981`) |
| 7 | Core snapshot | field + default `App:1580-1639` (zebra `:1586`); parse `App:1679-1680` |
| 8 | Core command | `handleUiToggle("set_x_enabled", "xEnabled")` near `App:9495`; `help` `App:9216` |
| 9 | Core web state | `buildWebStateJson` pattern `App:7970` |
| 10 | Core presets / hardware toggle (optional) | `App:6578`, `App:10431`; `toggleSharedUiBoolAction` pattern `App:8913` |
| 11 | WebUI | control pattern `WCP:10087`; patch case `WCP:8875`; read `uiState.x_enabled` in render (pattern `WCP:6371`) |

Rebuild Core + UI, restart both. Verify: toggle in the WebUI, then `grep xEnabled ~/.config/CinePi/UI.conf`, and watch the touch screen change within ~1 s.
Trap: the key string must be byte-identical in `SettingsBridge` (QSettings key) and Core (`"xEnabled"`). A mismatch writes a second key and nothing changes. Second trap: skipping step 4 → the WebUI change appears on the touch screen only after a UI restart.

### B6. Add a resolution / sensor mode (driver → Core → UI)

| Step | Layer | Place | path:line |
| --- | --- | --- | --- |
| 1 | Driver regs | New `mode_WxH_regs_12bit[]` with `IMX585_WIN_CROP_REGS(vst, height)` | pattern `drv/imx585.c:586-592`; macro `:563-574` |
| 2 | Driver table | New `supported_modes[]` entry (`width`, `height`, `hmax_div`, `base_vmax`, `crop`, `reg_list`) | pattern `drv/imx585.c:1006-1020`; table `:794` |
| 3 | Driver routing | **Fix the hard-coded indices**: `*num_modes = 20` (two places) and `&supported_modes[10]`, `&supported_modes[20]` in `get_mode_table` | `drv/imx585.c:1376-1440`; comment `:780-792` |
| 4 | Driver build | `./setup.sh`, reboot. Check sizes: `v4l2-ctl -d /dev/v4l-subdevN --list-subdev-framesizes pad=0,code=0x3012` (0x3012 = SRGGB12_1X12; N **unconfirmed**, find with `v4l2-ctl --list-devices`) | `drv/setup.sh`, `drv/dkms.conf` |
| 5 | Core size set | Add to `isImx585Raw12CropResolution` (4K-width) or `isImx585FullHdCropResolution` (1920-width) | `CC:385-396`, `CC:366-377` |
| 6 | Core checks | `sensorModeForRequestedResolution` `CC:2244-2262`; `normalizedResolutionForSensor` `CC:2404-2414`; max fps `CC:2669-2676`; lossless caps `CC:2470-2491`; `validateResolution` `CC:8750-8768` (all use the step-5 helpers, so usually no edit) | — |
| 7 | UI lists | `imx585Raw12ResolutionOptions` + labelled list `UI/qml/CameraPage.qml:418-443`; aspect helpers `:778-786`, `:959-1005`, `:1025-1036`, `:1322-1336`; `UI/qml/SettingsPage.qml:151-160` | — |
| 8 | WebUI lists | `WCP:5120`, `:5174-5180`, `:5254-5268`, `:5298-5312`, `:5372-5384`, `:4982` | — |
| 9 | Rebuild Core + UI, restart | — | — |

Verify: select it; Core log `ApertarCore camera configured: … stream=WxH` (`CC:6264`); a recorded DNG has that size.
Trap: `v4l2_find_nearest_size` never fails (`drv/imx585.c:2103`). If the driver lacks the mode, libcamera gets the nearest one and Core may still log success with a different `stream=`. Check `stream=` every time. Also **unconfirmed** which driver tree is installed on the Pi (KB `drivers.md` says `qbc-pisp-handler` + local mod): `dkms status; git -C ~/drivers/imx585-v4l2-driver log --oneline -1`.

### B7. Change a QML layout only

| Step | Place |
| --- | --- |
| 1 | Edit `UI/qml/*.qml`. New file → add to `APERTAR_QML_FILES` (`UI/CMakeLists.txt:19-52`) **and** `UI/qml.qrc` |
| 2 | `cmake --build /home/pi/ApertarUI/build -j2` |
| 3 | `sudo systemctl restart apertar-ui-direct` |

Verify: look at the screen; `sudo journalctl -u apertar-ui-direct -b | grep -i 'qml\|error'`.
Trap: QML is AOT-compiled into the binary (`UI/CMakeLists.txt:184-196`). Editing the `.qml` and restarting without a rebuild does nothing. Second trap: size flags differ per file (`standardLandscapeLayout` means different things in `Main.qml:43` and `SettingsPage.qml:23`), so a change can apply on one layout only. Test with the rig's `[display] ui_layout`.
