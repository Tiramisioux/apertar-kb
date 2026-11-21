# Review: Core clip-split commits (80 commits, 01f170c..05fb8f1)

Read at `clip-split` `05fb8f1` (`/home/user/wt/core-clip`). Yardstick: `apertar-conventions.md`, original Apertar 1.6.0 `/home/user/wt/core-upstream`.
Method: commit messages for intent, the diffs and the tree for behaviour, upstream greps for precedent. Not run: nothing here runs a camera.
Paths are `path:line@clip-split` unless marked `@upstream-1.6.0`.

## Summary

The range is 49 files, +11 900 / -460 lines. Three areas.

| Area | Commits | Size | Stock camera affected? |
| --- | --- | --- | --- |
| Split clips and merge | c9e7707 a8edd38 67ce387 6e340c8 b755383 fe863de 8ec2f1a e298d4a 7e6e2a3 c184b01 | small | Merge is on by default but inert without split clips; split is off (`frames_per_folder` 0). Progress fields added to state. |
| Dual-sensor core, relay, takes | b0b88c5 bd6dd64 60955e4 3e8c131 d67e77f 03f5701 376c958 d45719d f49a980 074cf78 ceac1f9 0aedf4c 50e6ea0 554d468 acb0567 5ce1afb bf16926 01d9232 a77fa27 2c0a667 0d750dd db627f6 dba69a6 0efa391 d13d7d0 57d9f91 b0b13e7 97a8c57 701eb58 3c3ee98 42ed3a5 | about 7 000 lines: `src/ipc/` +3 245, `CameraPort.hpp`, `FramePhaseLock.hpp`, `TakeSlots.hpp`, `DualSensorSettings.hpp`, App +1 459, CC +1 251 | Inert by default (Dual sensor switch off, no cam1). Exceptions below. |
| WebUI | a8edd38 b755383 fe863de f0b70e0 25b73b4 18a2de7 687a863 2c636f4 a52855b 2b98ebe 7671c74 39e0ad9 7a49489 022a637 bb71682 0b47470 4b39193 0c32534 673d16a 6cf20a6 d59cc85 2aced1d 322f611 c1fd02b a3f475e 1421fb6 093b2bb f7cce80 c39f449 24ce143 09903c4 da4f124 25305fd eda9ef1 44d3022 05fb8f1 44c56e4 ef8ca38 cac7962 f56f5e9 40be26a fe863de | +2 881 lines in `WebControlPage.cpp` (now 23 548 lines) | Cards moved, new cards, new meters. |
| Other | 0902ac5 (time-left bar) | small | Yes: `time_left_percent`. |

Protocol check (confirmed): every key written in 1.6.0 `ApertarCoreApp.cpp` and `CameraController.cpp` is still written (script: quoted-key sets, difference empty), and the `commands` list in `help` is a superset (98 in 1.6.0, 139 here). No 1.6.0 reply field is lost. The additions are the problem (CLIP-C-3).

Stock-camera safety: the dual-sensor code is largely inert without a cam1 (confirmed: `dualSensorEnabled` default false `ApertarCoreApp.cpp:1899`; `fpsPhaseLock` default false `Types.hpp:138`; `frames_per_folder` default 0 `BufferBudget.hpp:320`). The exceptions are CLIP-C-2, -8, -9, -10.

Everything else in the area is competent and carefully tested at desk level. The main work for merge-readiness is: one real bug (C-1), one start-script change that touches stock Pi 5 start (C-2), the nested get_state shape (C-3), slop (C-4), and the missing in-repo documentation for the dual-sensor install (C-5).

Build warnings: see CLIP-C-6.

## Final findings

### CLIP-C-1 get_state writes the clip-merge block twice
- Category: bug (protocol output, stock camera)
- Severity: major
- Where: `src/ApertarCoreApp.cpp:14045` and `:14047`@clip-split (commit 6e340c8).
- What the port does: `get_state` keeps the existing `<< clipMergeStateJson()` before `settingsBody(...)` and 6e340c8 appended a second one after it. Every `clip_merge_*` key (now 9 keys) appears twice in the socket `get_state` reply, on every camera. The duplicated block is in the diff as one context line plus one added line (`git show 6e340c8 -- src/ApertarCoreApp.cpp`, last hunk). Confirmed.
- The Apertar way: one writer per field; `get_state` = status keys + `settingsBody` (CMD-11). 1.6.0 has no `clip_merge_*` keys at all.
- Why it matters: duplicate keys in one JSON object. Qt and Python take the last one, other readers the first, the relay's `jsonkeys::find` the first. They agree today only because the two copies are equal.
- Fix: delete line 14047 (`<< clipMergeStateJson()` after `settingsBody`). Keep the one at 14045.
- Effort: S

### CLIP-C-2 The start script exports a rig-specific libcamera pipeline config on every start
- Category: stock-behaviour change; Pi-model risk
- Severity: major
- Where: `scripts/start-apertar-core.sh:20-26`@clip-split (commit b0b88c5).
- What the port does: if `/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml` exists and `LIBCAMERA_RPI_CONFIG_FILE` is unset, the script exports it for the primary as well as for cam1. The yaml sets the front-end queue depth to 4 (comment: "the live Core runs with FE queue depth 4, drop-frames recipe row 8"). The commit message says "exported unless set", and that "with neither env the command line is today's". The code says otherwise: no env is needed, the file's presence is enough.
- The Apertar way: the script maps `APERTAR_*` env to libcamera env only when the user sets it (`APERTAR_TUNING_FILE` -> `LIBCAMERA_RPI_TUNING_FILE`, `start-apertar-core.sh:16-18`@clip-split; same at `@upstream-1.6.0`). Tuning files are looked up in `/home/pi/Tuning-Files/defaults-pisp|vc4` (conventions line 374), never the pipeline dir. Bench knobs follow R8: `APERTAR_<AREA>_<KNOB>`, default off.
- Why it matters: a camera that has that file in `Tuning-Files/pipeline/` (any copy of Patrik's rig) silently gets a different libcamera queue depth and memory use. The file is `pisp-` named: on a Pi 4 / CM4 (vc4 pipeline) libcamera reads the file's `target` and probably ignores or warns (unconfirmed: `LIBCAMERA_LOG_LEVELS=RPI:DEBUG` on a Pi 4 with the file settles it). It is also not dual-sensor related: the depth applies to a single sensor.
- Fix: delete the block. If the depth is wanted, add `APERTAR_PIPELINE_CONFIG` (path, unset = nothing) mapped to `LIBCAMERA_RPI_CONFIG_FILE` exactly like `APERTAR_TUNING_FILE`, and set it in the cam1 unit or in the rig's own environment. Correct the b0b88c5 message accordingly.
- Effort: S

### CLIP-C-3 The socket get_state gains nested objects on every camera; a second JSON reader exists to read them
- Category: mismatch (CMD-8, CMD-9, CMD-11); protocol change
- Severity: major
- Where: `src/ApertarCoreApp.cpp:14048-14049` (`"ui":{...}` and `cam1StateMembers`); `src/ipc/Cam1State.hpp:150-158` (`"cam1":{...,"settings":{...}}`); `src/ipc/JsonKeys.hpp:1-8,168-176`@clip-split (commits 60955e4, f49a980).
- What the port does:
  - `get_state` now always carries `"ui":{dual_sensor_enabled, preview_source, hdmi1_source, preview_wipe, ..., cam1_mode}` (60955e4: "a ui object in the socket get_state"). Stock cameras too. Nothing reads it: `grep -rn 'preview_source\|dual_sensor_enabled'` in `/home/user/wt/ui-port/{src,qml}` = 0, and Core's own relay does not read `"ui"`.
  - With a cam1 configured it adds a nested `"cam1":{...,"settings":{...}}` object.
  - Because of the nesting the relay cannot use the flat parser (`ControlProtocol.cpp`), so `JsonKeys.hpp` is a second hand-written JSON reader. Its `run(obj, firstKey, lastKey)` cuts cam1's `settingsBody` out of cam1's reply by member order, and `cam1EstimatedBytesPerSecond` relies on "the first width/height is `resolution`'s" (`ApertarCoreApp.cpp` near 5822, comment in 3c3ee98).
- The Apertar way: `get_state` is flat; groups (`system`, `ui`, ...) live in `/api/state` only; UI.conf values stay out of `get_state` (CMD-11, `@upstream-1.6.0` `ApertarCoreApp.cpp:7965` is `/api/state`, and the upstream `get_state` block has no nested value: confirmed by reading the block). Flat scalars everywhere (brief, CMD-9).
- Why it matters: any client that reads `get_state` as a flat line (a Cinemate-side script, a shell tool) sees a shape it never had, on a stock camera, for a field no one reads. The member-order coupling in `jsonkeys::run` breaks silently when someone adds a field to `settingsBody`'s neighbourhood.
- Fix: (1) remove `"ui":{}` from `get_state` (keep it in `/api/state`): S. (2) For `cam1`, either keep the object but only in `/api/state` (the WebUI's reader) and give `get_state` flat keys `cam1_state`, `cam1_message`, `cam1_locked`, `cam1_skew_us`: M; the touch UI repo needs its reader matched. (3) If the nesting stays as a recorded decision (design P15/R6), say so in the handoff note and add a test that pins the key order `jsonkeys::run` depends on. Do (1) now; (2) or (3) after the UI side is known.
- Effort: S for (1), M for (2)

### CLIP-C-4 About 230 added comment lines name internal documents, ticket numbers and rig history
- Category: slop
- Severity: major (it is what the original developer reads first)
- Where: grep over added lines of `git diff 01f170c..HEAD -- src include tools config scripts ':!src/web/WebControlPage.cpp'`: 233 lines match `T[0-9]{2}`, `P[0-9]{2}`, `design 6.2`, `design §4.1`, `amendment A1/A2`, `R6`. The WebUI adds more (`T61`, `T63`, `T67`, `design §5.3` in HTML comments). Examples:
  - `config/apertar-core-cam1.service:1` "the live unit (T56 0.1)"; `config/apertar-hardware-cam1.conf:30` "buffer=frames (design 3.1, C6) ... (5000 in /home/pi/apertar-hardware.conf on 2026-11-11)".
  - `src/util/TakeSlots.hpp:106` "(design 6.2) ... T64"; `src/util/DualSensorSettings.hpp:2` "(design §5.1, §6.1, §4.4; T63)".
  - `src/ApertarCoreApp.cpp:8299ff` "(design 3.4)", "(design 4.1 Locks, 4.4)", "(amendment A1)".
  - `src/camera/Imx283Modes.hpp` header: "the build on the rig since 2026-11-10".
  - `src/ApertarCoreApp.hpp`: "(KB clip-merge-progress-plan.md)", "(P7)", "(T62)".
  - `README.md:333,356`: "the NVMe campaign's A/B and collect step", "Apertar-UI `7ea9afc` (local branch `clip-split`)".
  - Ten header comments say "host-tested (xxx_test.cpp)" (see C-7).
- The Apertar way: comments say what the code does and why, in the code's own terms; no ticket or work-package numbers (STY card, conventions section 7); the commit message carries history.
- Why it matters: `design 6.2` points to a document that is not in the repo; T and P numbers mean nothing to the original developer.
- Fix: one sweep. Replace each reference with the rule itself in one sentence (for example "the take starts on the slot boundary so both Cores stamp the same frame" instead of "(design 6.2 step 1)"). Drop dates, branch names, commit hashes and file names of notes. Mechanical: `grep -nE '\bT[0-9]{2}[a-z]?\b|\bP[0-9]{2}\b|design[ -]?[0-9§]|amendment A[0-9]|§[0-9]'` must return nothing at the end.
- Effort: M

### CLIP-C-5 The dual-sensor install is not in the repo: unit points to a script that is not there; no README rows
- Category: mismatch (CMD-23, R14), docs
- Severity: major
- Where: `config/apertar-core-cam1.service:9-17`, `config/apertar-hardware-cam1.conf`, `README.md` (no `--camera`, `APERTAR_CAMERA`, `APERTAR_WEB_PORT`, port 8001, cam1 service); commits b0b88c5, bd6dd64.
- What the port does:
  - The unit runs `ExecStart=/home/pi/start-apertar-core-ds.sh` and `APERTAR_CORE_BIN=/home/pi/ApertarCore-ds-build/apertar-core`. `start-apertar-core-ds.sh` is not in the repo (`grep -rn start-apertar-core-ds` finds only the unit; the repo script is `scripts/start-apertar-core.sh`, which now handles `APERTAR_CAMERA` itself). The paths are Patrik's rig. The unit file's own comment says it is "the live unit without the wait-ui ExecStartPre".
  - The hardware file hard-codes `frames_per_folder=5000`, a copy of one rig's primary setting.
  - The README does not say that `--camera`, the second service, the second hardware file and port 8001 exist.
- The Apertar way: a launch option is an `Options` member, a `main` branch, a usage line and a README row (CMD-23, always). Install of an optional unit is manual and says so in the README (R14 row 6). Upstream ships `config/` files for helpers only.
- Why it matters: following the repo alone, cam1 cannot be installed. A reader sees rig paths as product.
- Fix: `ExecStart=/home/pi/ApertarCore/scripts/start-apertar-core.sh` (the path the primary unit uses, check it) and `APERTAR_CORE_BIN` removed; drop `frames_per_folder` from the cam1 hardware file (default 0 is wrong for cam1 only if the primary splits: say that in one comment line, or read the primary's value); delete the "live unit" comment; add one README section "Second sensor (Pi 5 / CM5)": install the two files, `Dual sensor` switch, what the secondary refuses, ports 8000/8001, the sockets.
- Effort: S for the unit and hardware file, M with the README

### CLIP-C-6 Build warnings: 165 `-Wpedantic` for `__int128`, and what is left
- Category: bug-class (build)
- Severity: minor
- Where: `src/audio/RecordingClock.hpp:48-56` (`slotTimeOfBootUs`, 9 warnings per translation unit, 10 units = 90 warnings in the log) and `src/util/TakeSlots.hpp:70-91` (`slotOfUs`, `boundaryUs`, `ceilSlotUs`; 3 units); `CMakeLists.txt:155,175,186` sets `-Wall -Wextra -Wpedantic` for the core and both plugins.
- Cause (confirmed): ISO C++ has no `__int128`, and `-Wpedantic` warns at every declaration and every `static_cast<__int128>`: 'for q', 'for r', 'for type name' and so on. `src/camera/FramePhaseLock.hpp:42` already has the accepted form, `__extension__ typedef __int128 PhaseLockInt128;`, which gives no warning (the log has none from that file). `grep -rn __int128 src` finds only these three files. `core-upstream/src` has none.
- Minimal fix: one tiny header `src/util/Int128.hpp` with `__extension__ typedef __int128 Int128;` in `namespace apertar`, include it from the three files, and replace `__int128` and `static_cast<__int128>` by `Int128`. Or, with no new file, `#include "camera/FramePhaseLock.hpp"`-independent: put the same one-line typedef at the top of `RecordingClock.hpp` and `TakeSlots.hpp` guarded by the same name. Re-grep the log: the 165 lines go to 0 (the 5 remaining warnings are not from this range, see below).
- Portability note (probable): `__int128` does not exist on 32-bit ARM compilers, so a 32-bit Raspberry Pi OS build fails here as it already does in `FramePhaseLock.hpp`. Apertar targets 64-bit (Pi 5 needs it); if Pi 3 / Pi 4 on 32-bit OS is meant to build, replace the four `mulDiv` sites by a small `mulDivRound(a, b, c)` helper using `unsigned long long` pieces. Settled by `aarch64-linux-gnu` vs `arm-linux-gnueabihf` compile of `tools/frame_phase_lock_test.cpp`.
- Other five warnings in `merge-nolc.build.log` (not `__int128`): `convertPlanarYuv420ToRgb` unused (`ApertarCoreApp.cpp:4887`), `allocatePhotoBasePath` unused (`CameraController.cpp:1332`), unused parameters `mediumGone` / `basePathOverride` in the no-libcamera stubs, `ignoring return value of write` in `StandbyPowerButtonInput.cpp:26`. The first four names are in `@upstream-1.6.0` as well (grep count 2 and 6), so they are not from this range (probable). Fix each with `(void)x;` or `[[maybe_unused]]`; not part of the clip work.
- Effort: S

### CLIP-C-7 Ten header comments claim host tests that are not in the repo
- Category: slop / completeness
- Severity: minor
- Where: `src/camera/CameraPort.hpp:8` (`camera_port_test.cpp`), `src/ipc/JsonKeys.hpp:2` (`json_keys_test.cpp`), `Resync.hpp`, `TakePlan.hpp`, `Skew.hpp`, `PrimaryWait.hpp`, `CommandClasses.hpp`, `Cam1State.hpp`, `Cam1Names.hpp`, `util/TakeSlots.hpp:4`. `ls tools/` has none of them; only `frame_phase_lock_test.cpp`, `mode_ladder_test.cpp`, `boot_config_test.cpp`, `clip_name_test.cpp` were extended in this range.
- The Apertar way: upstream Core has no test target (PLT-12); this fork already keeps `tools/*_test.cpp`, built by hand with `c++`.
- Why it matters: a reader looks for the tests, finds none, and cannot tell if the logic was tested. The commits say "host checks (92 pass)".
- Fix: either add the ten test files (they exist on the author's side per the messages) or remove the claim. Prefer adding, they are the only check on the slot arithmetic and the resync rules.
- Effort: S (remove claim) / M (add files)

### CLIP-C-8 `time_left_percent` and `time_left_label` change meaning on a stock camera
- Category: stock-behaviour change; protocol (value change)
- Severity: minor
- Where: `src/ApertarCoreApp.cpp:9628-9640` and `timeLeftEstimateLabel` (~5720)@clip-split (commit 0902ac5); `@upstream-1.6.0` `ApertarCoreApp.cpp:7817`: `timeLeftPercent = clamp(recordTimeLeftMinutes / 120.0 * 100, 0, 100)`.
- What the port does: the percent is now time left over the card's whole recording time in the current mode; the label reads `<format> estimate (card: 2 h 10 min)` instead of `(bar: 2 h)`. User request recorded in the message.
- The Apertar way: a field keeps its 1.6.0 meaning; a changed behaviour that Patrik decided is kept, but off by default where it changes a stock camera.
- Why it matters: any 1.6.0 client that draws the bar from `time_left_percent` (only the WebUI does in this tree) sees a different scale. The new scale is arguably the better one; it is a display value, a setting would be heavy.
- Fix: keep the behaviour (recorded decision). Name it in the handoff list of stock-visible changes. No code change. If the original developer objects: a new field `time_left_card_percent` and the old one untouched (S).
- Effort: S

### CLIP-C-9 Stock Pi 5 start path changes when a second I2C node exists in the device tree
- Category: stock-behaviour change; Pi-model risk
- Severity: minor
- Where: `src/camera/CameraController.cpp` `waitForCam0Subdev`, `pickCamera`, `recordOpenedCamera`, `probeSensorModesOnce`, `subdevScopeNode`; `src/camera/CameraPort.hpp:100-140`@clip-split (commit b0b88c5).
- What the port does, for the primary with no `--camera`:
  1. Subdev look-ups are limited to cam0's I2C node when a sensor subdev is there (else everywhere, as before). Camera pick prefers the camera under cam0's node.
  2. If `config.txt` names a sensor on cam0 and no subdev appears under cam0's node, camera start waits up to 20 s (`waitForCam0Subdev`).
  3. If `config.txt` names cam0 but another port's camera opens, camera settings are not saved (`noPersist`).
  4. `probeSensorModesOnce` marks the probe done only when it found modes: an empty probe is repeated at every camera start (was: once per process).
- The Apertar way: a stock camera behaves as 1.6.0.
- Why it matters: (1) is a fix, (4) can repeat a CameraManager start plus a WDR write at every start on a sensor whose mode list is empty. (2) adds a 20 s start delay to a Pi 5 whose cam0 overlay is in `config.txt` but whose sensor is unplugged. On Pi 4, CM4 and Pi 3 the code is inert if the device tree has no `i2c_csi_dsi0` symbol (Pi 4 has `i2c_csi_dsi`; unconfirmed: `ls /proc/device-tree/__symbols__ | grep csi` on a Pi 4 settles it); then `resolve("cam0")` is invalid and every path falls back to today's.
- Fix: cap (2) at the secondary only, or 3 s for the primary; make (4) retry at most once per process. Record (1) and (3) as intended.
- Effort: S

### CLIP-C-10 Relay machinery runs on every primary Core, also with no second sensor
- Category: stock-behaviour (cost); mismatch (CMD-1 placement, CMD-2/3 shape)
- Severity: minor
- Where: `src/ApertarCoreApp.cpp:8298-8330` (`startCam1Client` always starts the thread), `ControlClient.cpp:272-285`, `:27-29` (wakes every 100 ms, a tick every 1 s that stats `UI.conf`), `ApertarCoreApp.cpp:16203` (`noteRelayEvent` runs three `find` calls over every published event), `:13328-13380` (`handleCommand` wrapper), `:16277` (`noteRelayFrame` per preview frame)@clip-split.
- The Apertar way: App owns threads as members and starts them when needed (CMD-19); `handleCommand` is one chain under one lock (CMD-2, CMD-3); `src/ipc/` holds the parser and socket server only (CMD-1). New ground: the relay (client socket to a sibling Core, forward queue, resync), recorded in the design and well separated through callbacks (`ControlClient::Options`, CMD-18).
- Why it matters: for a stock camera this is 10 wake-ups per second forever, a `stat` per second and a scan of every event, for a feature that is off. Small, but on a Pi 3 / Pi 4 every wake-up counts, and the original developer will read the thread list. About 3 200 lines of policy (`Resync`, `TakePlan`, `Cam1State`, `CommandClasses`, `Skew`, `PrimaryWait`, `Cam1Names`, `JsonKeys`, `ControlClient`) sit in `src/ipc/`, whose role is the parser and server.
- Fix: (a) start the client only while the Dual sensor switch is on (the switch is a UI.conf toggle read by the 1 Hz loop; start/stop there); (b) in `noteRelayEvent` test `eventJson.compare(0, 18, "{\"event\":\"recor")` style prefix before the finds, or return when `!cam1Client_.configured()`; (c) move the relay and its helpers to `src/dual/` and list that directory in CMake next to its area, and say in the handoff note why `handleCommand` has a wrapper. (c) is optional; the design is a recorded decision.
- Effort: S for (a)(b), M for (c)

### CLIP-C-11 Plugin ABI bump 2 to 3 for ProRes and H.264
- Category: protocol; Pi-model (packaging) risk
- Severity: minor
- Where: `src/prores/ProresPluginApi.hpp` (`kApertarProresAbi = 3`), `src/video/LibavH264PluginApi.hpp` (`kApertarLibavH264PluginAbi = 3`)@clip-split (commit ceac1f9); `@upstream-1.6.0` both are 2.
- What the port does: adds `tcOffsetUs`, `tcPeriodNum`, `tcPeriodDen` to both plugin configs, so the timecode of a slotted take is the slot time. Zero period = today's timecode (confirmed `RecordingClock.hpp:68-76`).
- The Apertar way: C ABI header plus ABI symbol for module plugins (CAM-15, CAM-16); a layout change bumps the number. This follows it.
- Why it matters: an old plugin `.so` next to a new core, or the reverse, gives "incompatible libav H.264 plugin ABI" and ProRes / H.264 stay off. Core and plugins build in one CMake run, so only a hand-copied binary is at risk.
- Fix: none in code. One line in the handoff note: the plugins must be rebuilt and installed with the core.
- Effort: S

### CLIP-C-12 WebUI: cards moved on stock cameras, Dual Sensor card always shown
- Category: stock-behaviour change (layout); decision recorded
- Severity: minor
- Where: `src/web/WebControlPage.cpp:6845ff` (`settingsDualSensorCard`, greyed by CSS `.dual-off` at `:2329`), commits 2b98ebe (Controls above System; the phase lock moved from Settings > Record to the Dual Sensor card), 2c636f4 (Speed Ramp under the frame rates), 687a863 (audio meter, `/api/buffer` poll every 250 ms during takes while Record audio is on), f0b70e0, 25b73b4.
- The Apertar way: the page is one string, pills via `buildOptionButtons` (WEB-15). The port follows it. On/Off two-pill grids send `enabled: "true"/"false"`: `set_clip_merge` sends the JS boolean `enabled: value === "On"` (`WebControlPage.cpp`, a8edd38), `set_dual_sensor_enabled` the string. Mixed.
- Why it matters: the card layout of a one-sensor camera changed in four places, as the owner asked ("User wants"); the phase-lock switch is reachable only through a card titled Dual Sensor on a one-sensor camera (the message says "the phase lock usable" while greyed: confirmed by CSS selector only, check by opening the page with no cam1).
- Fix: keep the decisions. Send `enabled` as a string in `set_clip_merge` for consistency (S). In the handoff list name the four moved items. If the owner wants a clean stock page, hide the card when `camera_port`/config names no cam1 and leave only the phase lock row in Record: M.
- Effort: S

### CLIP-C-13 Merge progress: cost and stale comments
- Category: bug-class (minor) / slop
- Severity: minor
- Where: `src/ApertarCoreApp.cpp` `countSplitClip` (6e340c8) and `runBufferEvents` (`:11618-11632`); `src/playback/ClipFrames.hpp` `readRoot(true)` (67ce387); `src/camera/CameraController.cpp:5757-5758`@clip-split.
- What the port does and what is wrong:
  1. `countSplitClip` lists the clip root and the first and last part folder of every split clip at every scan. On exFAT a part of 5 000 entries and a root of up to 45 000 entries are slow listings, and the scan can run right after a take. Unconfirmed whether it blocks a take start (the worker pauses at take start, but a listing already running is not interrupted): measure with a 45 000-frame clip on a USB SSD.
  2. `ClipFrames.hpp` re-lists the root once more when a clip has parts. The comment says "a split clip's root holds a few entries until the merge, so the second read is cheap where it matters". During a merge the root grows to the whole clip, so the second read is a second full listing exactly then.
  3. `CameraController.cpp:5757-5758` still says the part folders are made "on the copy side ... never by a writer", but 8ec2f1a moved `ensurePartFolder` into the writer loop (`:5448`). The comment is wrong now.
  4. `runBufferEvents` builds `clipMergeStateJson()` (lock, loop, string) at every pass of the loop to compare with the last one; it can compare a version counter instead.
- Fix: correct comment 3 and 2 (S); a `clipMergeRevision_` atomic bumped where the state changes, compared in `runBufferEvents` (S); for 1 keep the scan counting lazily (count only when the merge is on and the clip is next) (M).
- Effort: S to M

### CLIP-C-14 Relay robustness: unbounded forward queue; a signal waits up to 20 s; wrong clock name
- Category: bug (minor)
- Severity: minor
- Where: `src/ipc/ControlClient.cpp:233-262` (`enqueueLocked`: no cap on `queue_` while linked), `src/main.cpp:114-127` (the secondary's no-sensor poll, `secondaryHasSensor(..., 20000, 500, ...)` takes no stop callback), `src/camera/CameraController.cpp` `waitForStopSlot` comment "CLOCK_MONOTONIC has passed stopUs" while the code uses `CLOCK_BOOTTIME`@clip-split.
- What happens: (1) a rotary knob forwarding `set_iso` steps to a stuck cam1 grows the queue until the 10 s busy drop; the drop is in the busy verdict, not in the queue. (2) SIGTERM during the poll sets the pipe flag only; the process exits after the poll (at most 20 s, then the wait loop sees the flag and returns 0), so `systemctl stop` is slow, not wrong. (3) comment only.
- Fix: cap the queue (coalesce a repeated setter of the same name: keep the last) (S); give `secondaryHasSensor` the same `stop` lambda that `waitForPrimaryIdle` takes (S); fix the comment (S).
- Effort: S

### CLIP-C-15 Eight "Dual view" actions and a pill row appear on stock cameras' action list
- Category: stock-behaviour change (catalog); nit
- Severity: nit
- Where: `src/hardware/ActionCatalog.hpp` (+16 lines: `preview_wipe_up`, `preview_wipe_down`, `preview_opacity_up/down`, `preview_stack`, `preview_wipe_direction`, `preview_view`, `preview_swap`)@clip-split (commit acb0567).
- What the port does: new catalog rows with alias lists such as `swap`, `stack`, `wipe+`, `opacity_`, and two new control families `preview_wipe`, `preview_opacity`. Entries are visible in the Remote-controls picker on a camera with one sensor.
- The Apertar way: R11 (catalog row, aliases, comma lists). This follows it. Upstream has no alias named `swap` or `stack` (grep `@upstream-1.6.0 ActionCatalog.hpp` empty for both: not run exhaustively; probable).
- Why it matters: only clutter in the picker for a one-sensor camera; short aliases such as `swap` could collide with a future action.
- Fix: none required; if wanted, hide the "Dual view" group when cam1 is not configured (S).
- Effort: S

### CLIP-C-16 Commit messages carry the rig history
- Category: slop (commits)
- Severity: nit
- Where: the 80 commit bodies, for example 8ec2f1a ("SSD night 2 (2026-11-09, Samsung T7, exFAT over USB ..."), 7e6e2a3 ("NVMe campaign 2026-11-10 ..."), c9e7707, 42ed3a5 (a 90-line body with "design 7.1-7.4", "fix A", "reviewers' scenarios"); 82 `Co-Authored-By` lines name a model.
- The Apertar way: a commit says what changed and why in the code's terms (STY section 7 card). The commit-clarity step of the campaign handles the rewrite.
- Fix: for the merge, squash by area and rewrite the bodies to what-and-why, keeping the measured numbers that justify a value (the 6-frame-period mkdir stall of 8ec2f1a is a good reason and should stay, without the date and the drive name).
- Effort: M

### Bugs and risks checked, no finding
- Merge default on, split default off: a stock camera merges nothing (`BufferBudget.hpp:320-334`, confirmed).
- `get_state` and `/api/state` lose no 1.6.0 key (script, confirmed above).
- Phase lock rewrite (42ed3a5) is gated by `fpsPhaseLock` (default false); the base-pin changes use `vblankOnlyPins_ = fpsPhaseLock && !photoMode` (`CameraController.cpp:7873`, `:9302`). A lock-off per-frame trace and stretch bookkeeping run only under `APERTAR_PHASE_LOCK_LOG` (`:8767`). Unconfirmed: that no per-frame cost is added to the lock-off hot path on a Pi 3 / Pi 4; `perf` on a take at 4K 24 fps would settle it.
- `clip_name` from a client is validated to name characters, no separator at either end, 100 chars (`ClipName.hpp:319-327`): no path traversal.
- The web handler for the secondary refuses every POST with 403; GETs stay; CAM1's picture loads from `:8001` as an `<img>` (no Origin header); no `innerHTML` with Core text in the added page code (the five `innerHTML = ""` are clears).
- 8ec2f1a (mkdir on the writer, not the copy worker) and 7e6e2a3 (keep `stopping_` while writers left behind still run) are real fixes with a measured cause; keep.
