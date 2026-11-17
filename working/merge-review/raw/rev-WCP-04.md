# Review WCP-04 (WebControlPage.cpp new-file lines 7442-8900: FPS/ISO lists, Speed Ramp, Mode Ladder editor, Value Lists, IMX283/IMX585 resolution tables)

Refs: port = `cinemate-port` 01f170c (`P` = `/home/user/Apertar-Core/src/web/WebControlPage.cpp`); upstream = `upstream-1.6.0` 35dbe67 (`U` = `/home/user/wt/core-upstream/src/web/WebControlPage.cpp`); fork main = `/home/user/wt/core-main` f60e301.
Yardstick: no `apertar-conventions.md` yet; rule ids from `raw/conv-core-command-plane.md` (C1-*). All claims confirmed by reading code unless marked.

## Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | major | mismatch | IMX585 resolution pills read the Mode Ladder's `get_mode_ladder` reply (`state.ladderServer.pool`) |
| F2 | minor | mismatch | `ladderRequest()` is a second copy of `sendCommand`'s fetch path; upstream sends read-only queries through `sendCommand` |
| F3 | minor | mismatch | Ladder fetched from inside `renderModeLadder` on every 1 s poll; upstream fetches side data when a panel opens |
| F4 | minor | mismatch | Generic pill builder `buildOptionButtonsInto` hard-wires the Mode Ladder toast (`option.locked` -> `showLadderLockWarning`) |
| F5 | major | new-ground | Mode Ladder editor (~800 lines) re-implements Core's ladder rules in JS; Core already validates (`dry_run`) |
| F6 | minor | bug | Crop diagram and ladder names assume an IMX585 3840x2160 readout for every sensor |
| F7 | minor | slop | Stale and contradictory comments: dry_run / "Save ladder" that do not exist, "no Auto under a ceiling", orphan ISO comment, banners |
| F8 | minor | slop | Ticket numbers and Cinemate references in comments; UI text points the operator to `core.py`, a private dev script |
| F9 | minor | mismatch | Inline SVG icon strings (`ladderIcons`); upstream serves PNG icons from `/icons/` |
| F10 | minor | bug | `ladderCardWriteSpeed` parses the display text `write_speed_result_text` with a regex |
| F11 | minor | pi-compat | Pi 5 measurement "about 69 fps at 4K 12-bit" baked into an operator note |
| F12 | minor | removed-upstream-behaviour | IMX585 resolution list: upstream 2-pill Full HD/4K + fixed crop row replaced by 8 family pills, 1.85:1 sizes renamed 2076->2072 / 1038->1036 |
| F13 | nit | slop | Empty `if` branch holding only a comment in `fpsOptionEntriesForSnapshot` |
| F14 | nit | duplication | `flickerFreeShutterAngles` is a JS copy of Core's maths; `showLadderLockWarning` re-implements `showToast`; `renderValueListsEditor` uses raw `document.createElement` next to the `createDomElement` helper |
| F15 | nit | mismatch | Mode tables encoded as space-separated strings with a `b` suffix (`imx585ClassModes`) or `[fps, "sizes"]` pairs (`imx283Bases`); upstream writes plain string arrays |

### F1 (major, mismatch): resolution pills depend on the Mode Ladder reply

Port:
- `P:8955-8960` `imx585ClassRows`: `const pool = state.ladderServer && Array.isArray(state.ladderServer.pool) ? state.ladderServer.pool : []; if (pool.length > 0) { return pool.filter(...)`. Feeds `imx585ResolutionOptions` (`sensorResolutionOptions`, P:9114-9116), `imx585BaseResolutionOptions`, `imx585CropRatioOptions`, `imx585BaseCommands`.
- `state.ladderServer` is set only by `applyModeLadder` after `get_mode_ladder` (`P:8023-8024`, `P:8038`).
- So the main Recording resolution pills change content when the Mode Ladder reply arrives, and fall back to the JS table before it.

Apertar way:
- Upstream: per-sensor resolution arrays written by hand in JS: `U:5112-5121` `sensorResolutionOptions`, `U:5249-5290` `imx585CropRatioOptionsForSnapshot` / `imx585BaseResolutionOptions`. One source.
- The merge target already has a sensor-probe query: `list_sensor_modes` (`core-main/src/ApertarCoreApp.cpp:9231`, also port `App:12724`) returning `modes[]` with width, height, bit_depth, clear_hdr, binning, max_fps.

Why it matters: two features coupled through a private JS cache; a maintainer changing the ladder reply breaks the resolution pills. Four sources of the same facts (Core tables, JS tables, pool, `fps_max`).

Rework: keep the hand-written JS tables as the one source for pills (upstream pattern), or, if the probe must drive them (mono sensor), fetch `list_sensor_modes` once in `fetchState`-time/start into `state.sensorModes` through `sendCommand` and read that in `imx585ClassRows`. `get_mode_ladder` then carries only the ladder. Delete the `state.ladderServer.pool` read from `imx585ClassRows` and `imx585LadderFamily`.

### F2 (minor, mismatch): `ladderRequest`

Port `P:8005-8015`: "get_mode_ladder and dry runs change nothing, so they skip sendCommand's snapshot patching." Own `fetch("/api/command")`, own error throw.
Upstream `U:11100-11113` `refreshAudioCaptureCapabilities`: `const reply = await sendCommand({cmd: "audio_capabilities", device}); state.audioCaptureModes = reply.modes || [];` A read-only query with an array reply goes through `sendCommand`; `applyCommandSnapshotPatch` (`U:8678`) returns false for unknown commands. The only raw fetch upstream is the fire-and-forget `user_activity` ping (`U:11509`).
Rework: `fetchModeLadder` calls `sendCommand({cmd: "get_mode_ladder"})`; delete `ladderRequest`. No dry runs are sent from JS (see F7), so the stated reason does not apply.

### F3 (minor, mismatch): fetch from render

Port `P:8397-8400` in `renderModeLadder` (called for every snapshot): first fetch, retry after 5 s, refetch on `ladder_active` change. Port also fetches on panel open (`P:10111`, `P:10174-10175`), which is the upstream way.
Upstream `U:6162-6167` `setSettingsPanel`: `if (normalized === "presets") fetchPresetLibrary(true); if (normalized === "config" ...) fetchConfigFile(true);` Busy flag `state.configFetchInFlight` (`U:10305`).
The render-driven fetch exists because of F1 (pills need the pool outside the Modes pane). After F1, keep only the panel-open fetch plus the refetch on `ladder_active` change, done in the poll handler, not in a render function.

### F4 (minor, mismatch): ladder hook inside the generic pill builder

Port `P:15029-15053`: `button.disabled = !option.enabled && !option.locked; ... if (option.locked) { showLadderLockWarning(false); return; }`. `normalizeChoiceOptions` gained `system` and `locked` (`P:10446-10447`).
Upstream `U:9146-9166` `buildOptionButtons`: generic, `{value,label,enabled}` only.
`system` (green camera-set value, a CSS class) is a fair generic extension. `locked` makes the shared widget know one feature.
Rework: drop `locked` from `normalizeChoiceOptions`/builder; `ladderLockedOptions` (`P:8478-8480`) keeps options enabled and the call sites wrap `onClick`: `ladderActive ? () => showLadderLockWarning(false) : handler`. Keep `buildOptionButtons(id)` as the upstream wrapper of `buildOptionButtonsInto(element)`.

### F5 (major, new-ground): Mode Ladder editor in JS

About 45 functions, `P:7628-8480`. JS holds the rules: `ladderArranged` (default maxes 25/33/50/+25), `normalizeLadderDraft`, `ladderDraftProblem`, `ladderOrderProblem`, `ladderRowStates`, `ladderSpans`, `ladderCeilingKnown`, `ladderWithMode`, plus the text format `WxH:BITS:hdr|sdr[:FPS[:COMP]]` (`ladderDraftText`, P:7808). Core has `set_mode_ladder` with `dry_run` returning `errors[]` (`App:14095`).
No upstream precedent for a list editor of this size. Nearest: favourites editor `U:7315-7400` (list from state, add/remove/reorder, one command `set_favorites_order` with a joined string, no client-side rule engine), and C1-N01 "Core is the single source of truth ... A feature that works from the WebUI only because its logic sits in JS".
The touch UI also has a ladder (`Apertar-UI` `qml/SettingsPage.qml`, `ApertarControlBridge.cpp` grep "ladder"), so rules now exist in up to three places (unconfirmed whether QML repeats them).
Deliberate: yes (fork-log l.97 "approved design", several follow-up commits 1ef94fe, e472b1b, b8ee23f). Verdict: simplify. Keep the card and the ladder concept. Move arrangement and legality to Core: JS sends the edited list (`set_mode_ladder resolutions=... dry_run=true` on each edit, then the save), shows `errors[]` per row from Core's reply, and Core fills default maxes. Delete `ladderArranged`, `normalizeLadderDraft`, `ladderDraftProblem`, `ladderOrderProblem`, `ladderSpans`, `ladderWithMode` (~250 lines). Keep the row view, crop picture and pool tiles.

### F6 (minor, bug): IMX585 geometry for every sensor

`ladderCropArea = { width: 3840, height: 2160 }` (`P:7642`); `ladderCrop` (`P:7903-7924`) cuts every window to it; `ladderModeName` non-IMX585 path (`P:7696-7710`) calls any 3840-wide mode "4K SDR" and any 1920-wide mode "2K SDR binned".
Failing input: IMX283 pool entry 3840x2160 10-bit, window_w 3840 (a crop of the 5472 sensor) -> `cropIn = 3840 < 3840` false, `whole` true -> "Whole sensor area, no crop." Wrong. IMX283 5.5K (window 5472) -> clipped to 3840, also "Whole sensor area". IMX477 4056 the same. Probable: depends on the probe giving a pool on those sensors.
Rework: take the readout area from the probe (largest pool window) or show the crop picture only on IMX585; name non-IMX585 modes by size.

### F7 (minor, slop): stale comments

- `P:7628-7633` "asks Core about the draft (dry_run) and saves it with Save ladder." JS sends no dry_run (grep `dry_run` in P: only this comment and other cards) and there is no Save button: edits auto-save after 200 ms (`commitLadderDraft`, `P:8072-8086`).
- `P:7565-7567` "no Auto under a ceiling or in Clear HDR" vs code `P:8665` `const autoAllowed = !(snapshot && snapshot.clear_hdr);` (Auto allowed under the lossless ceiling since b5b787e).
- `P:7626-7627`: orphan copy of the ISO comment directly above the `// ---- Mode Ladder (T34) ---` banner; the function it describes is 1030 lines lower.
- Banners `// ---- Mode Ladder (T34) ---`, `// ---- IMX585 resolutions ---`. C1-I14: comments state a hazard or reason; no banners, no ticket numbers.
Rework: delete the orphan, fix the two wrong comments, drop the banners.

### F8 (minor, slop): ticket numbers, Cinemate references, `core.py`

- Comments: "Speed ramp (T31)" `P:7516`, "T33:" `P:7568`, "Request 24:" `P:7576`, "(T34)" `P:7628`, "(T33)" `P:8482`; "as in Cinemate" `P:7566`, "Cinemate's cropDiagram" `P:7900`, "as Cinemate's crop list" `P:8266`. Meaningless to the original developer (BRIEF vocabulary; C1-I14).
- Operator text `P:8263`: "Sensor probe off: add modes with core.py (set_mode_ladder resolutions=…)." `core.py` exists in neither repo (find over Core upstream and port: none); it is the contributor's dev script (`apertar-kb/working/mac-driven-loop.md:21`).
Rework: remove ticket and Cinemate words; text "Sensor probe off: no modes to activate."

### F9 (minor, mismatch): inline SVG icons

Port `P:7644-7650` `ladderIcons` (5 SVG strings set via `innerHTML`).
Upstream: 0 `<svg` in U; icons are PNG files: `U:2448` `<img class="icon-image" src="/icons/folder.png" alt="">`, CSS `url('/icons/camera.png')` `U:616`.
Rework: add PNGs to the icon set served at `/icons/` or use text glyphs (the port already uses "×" in value chips, `P:8547`).

### F10 (minor, bug): card speed from display text

`P:7944-7949`: `/^([0-9.]+) MB\/s$/.exec(String(systemState.write_speed_result_text || ""))`. `write_speed_result_text` is built for display by `writeSpeedResultText(...)` (upstream `App:7932-7936`). Any wording change silently sets the speed to 0 (warning gone). Rework (C1-R4): Core adds `write_speed_mbps` (number, from `mediaSpeedLastWriteSpeedMBps`) to the system state; JS reads that.

### F11 (minor, pi-compat): Pi 5 number in UI text

`P:8178-8180`: "Above 30 fps the lossless encoder runs close to its limit (about 69 fps measured at 4K 12-bit): watch the buffer bar." A four-core Pi 5 measurement; on Pi 4 / CM4 the limit is lower (unconfirmed, no measurement in KB checked). Rework: drop the number, keep "watch the buffer bar", or let Core publish the encoder limit.

### F12 (minor, removed-upstream-behaviour): IMX585 resolution choice

Upstream: 2 base pills `U:5280-5285` (`Full HD`, `4K`) + fixed crop row of 10 ratios `U:5249-5278` including `3840x2076` / `1920x1038`. Fork main added one `4K Clear HDR` pill (`core-main WCP:5287-5310`).
Port: 8 pills (Full HD binned, 4K, 2K crop, HD crop, each with HDR) `P:8922-8927`, `P:9021-9032`; sizes from pool or class tables; 1.85:1 renamed `3840x2072`/`1920x1036` (aliases `P:9084-9088`), new 2K-crop and 1440x1080 sizes. Requires the port's imx585 driver (inventory 1, commit 900d282 "needs cinemate-port driver"). With the Apertar baseline driver (`origin/apertar` e5b74d3) the 2072/1036 sizes may not exist (unconfirmed: `git -C /home/user/imx585-v4l2-driver grep -n 2072 origin/apertar`).
Rework: none for the shape (it extends fork main's pill model); record the driver dependency in the handoff and keep the 2076->2072 alias only if Core does the same.

### F13 (nit, slop): empty branch

`P:7503-7506`: `if (isLosslessImx585Snapshot(snapshot)) { // comment only } else if (isLosslessFourKSnapshot(snapshot))`. Rework: `if (!isLosslessImx585Snapshot(snapshot) && isLosslessFourKSnapshot(snapshot)) ... else if (isLosslessTwoKSnapshot(...))` and one comment line.

### F14 (nit, duplication)

- `flickerFreeShutterAngles` `P:7590-7601` copies Core's `flickerFreeShutterAngles` (App 1294 per inventory). Core could publish the merged angle list with a flag per angle; acceptable as upstream also mirrors Core tables in JS (`U:4966-5005`).
- `showLadderLockWarning` `P:7982-7993` writes the toast element and timer itself; upstream `showToast` `U:7804`. Rework: give `showToast` an optional link element.
- `renderValueListsEditor` (`P:8500-8657`) uses `document.createElement` + `className` 20 times; upstream helper `createDomElement(tag, class, text)` `U:6555`, used by the ladder code in the same unit.

### F15 (nit, mismatch): mini-format tables

`imx585ClassModes` `P:8915-8920` "1920x1080b 3840x2160 ..." parsed with `split(/[xb]/)`; `imx283Bases` `[[21.401, "5472x3648 ..."]]`. Upstream: plain arrays of "WxH" strings (`U:5112-5121`, `imx477ResolutionOptions`). Rework when touched: arrays of objects or strings, `binned` as a field.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `valueStepsFromSnapshot` / `cappedValueEntries` / `fpsOptionEntriesForSnapshot` | keep | Same shape as upstream `availableFpsOptionsForSnapshot` (`U:4992-5021`): constant list cut at a ceiling; ceiling and list now from Core state (C1-N01). Comments need F7/F8 cleanup |
| Entry objects `{value,label,enabled,system,locked}` | simplify | `system` fine (CSS class); `locked` out of the generic option (F4) |
| `buildOptionButtonsInto` | simplify | Element-taking variant with `buildOptionButtons(id)` as wrapper is fine; remove the ladder hook (F4) |
| Mode Ladder editor | simplify | Rules to Core, JS shows Core's errors (F5) |
| Crop diagram `ladderCrop` / `fillCropFrame` | simplify | Sensor-agnostic area or IMX585-only (F6) |
| `ladderRequest` | rework-to-upstream-pattern | `sendCommand` as `audio_capabilities` (F2) |
| `renderValueListsEditor` with signature + typing guard | keep | Settings in UI.conf through one command with a joined list (C1-R3, C1-I09); signature guard is needed because upstream redraws every second. Use `createDomElement` |
| JS mirrors of Core tables (`imx283Bases`, `imx283ModeOrder`, `imx585ClassModes`, `imx*NormalizedResolution`, ladder default maxes, `flickerFreeShutterAngles`) | simplify | Hand-copied sensor tables are the upstream pattern (`U:4966-5005`, `U:5112-5290`). Drop the second source (pool) for pills (F1) and move default maxes to Core (F5) |
| `imx585Families` / class keys `s12 s10 h12 h16` | keep | Extends fork main's Clear HDR pill (`core-main WCP:5287-5310`); flatten table encoding (F15) |

## Conforms

- All state-changing calls use `sendCommand` with flat payloads: `set_fps_speed_ramp` (`P:7537`), `set_value_steps` (`P:8494`), `set_mode_ladder` (`P:8443`, `P:8463`). Lists travel as one comma string (`values: rest.join(",")`, `P:8555`; ladder text `P:7808`) per C1-I09.
- Error handling `try { await sendCommand } catch { showToast(error.message, true) }` (`P:7535-7541`, `P:8492-8498`) is upstream `dispatchFavoriteCommand` (`U:7307-7313`); Core refusals shown as written (C1-N02).
- Ceilings come from Core state (`fps_max`, `fps_take_max`, `iso_max`), not JS rules: Core is the source (C1-N01). Core's `maximumIsoForSettings` (`CC:3162-3168`) covers the lossless ISO list upstream JS hard-coded (`U:5023-5027`). Note: Core raised that cap 800 -> 1600 (commit 2f43ecc, CC unit), a behaviour change to report there.
- Speed Ramp card: pill rows built with `buildOptionButtons` and DOM ids, like upstream settings cards.
- IMX283 helpers copy the shape of the IMX294 helpers (`imx283CropOptionsForBase` vs `U:5060` `imx294CropOptionsForBase`; `sensorResolutionOptions` branch per sensor).
- Old IMX585 branch of `normalizedResolutionForSnapshot` (`U:5171-5189`) removed, not left dead; replaced by one early return.
- Value list state under `"ui":{}` as arrays: precedent is favourites (`set_favorites_order` stores a string, state returns an array, conv 5.10).
- Panel-open fetch of the ladder (`P:10174-10175`) matches upstream `setSettingsPanel` fetches.

## Skeptic

Checked at port `01f170c`, upstream `35dbe67`, fork main `f60e301`. Every port line below re-read.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Pool read confirmed (P:8955-8960); `list_sensor_modes` (P App:12724, main App:9231) carries width, height, bit_depth, clear_hdr, binning, so the rework loses nothing. Deliberate is **yes**: commit 66b324d "The Mode Ladder's pool decides what exists; the class tables are the fallback". |
| F2 | stands | Own fetch confirmed (P:8005-8015). No dry run is sent from JS (grep `dry_run` in the ladder block: only the comment at P:7632). Upstream `audio_capabilities` goes through `sendCommand` (U:11100). |
| F3 | corrected | Fetch in render confirmed (P:8397-8400), panel-open fetch confirmed (P:10174-10175), upstream panel-open pattern confirmed (U:6162-6167). Only the first fetch exists because of F1; the refetch on `ladder_active` change has its own reason (ceilings change). |
| F4 | corrected | Same hook also in `createFavoritePillGrid` (P:10729-10733). Proposed rework (keep options enabled, wrap onClick) would lose the grey look; rework changed to a generic "disabled-click" callback. |
| F5 | corrected | QML has no ladder rules (only `ladderActive` flag, UI `SettingsPage.qml:3398`, `ApertarControlBridge.hpp:22`), so drift is JS vs Core. Core `validate` (ModeLadder.hpp:206-256) has no quality sort and no default maxes, so "Core assigns default maxes" needs Core work. Concrete drift already exists: "never used" is a Core warning (ModeLadder.hpp:243) but a JS refusal (P:7859-7860). |
| F6 | stands | `ladderCropArea` 3840x2160 (P:7642), clip `Math.min(area.width, ...)` (P:7908-7909), name rules (P:7703-7708) confirmed. Probable on IMX283/IMX477; needs a pool from those sensors. |
| F7 | stands | P:7565-7567 says "no Auto under a ceiling"; `availableIsoOptionsForSnapshot` blocks Auto only on `clear_hdr` (P:8665). P:7632 claims dry_run and "Save ladder"; save is the 200 ms timer (P:8083). P:7626-7627 orphan; banner P:7628. |
| F8 | stands | All strings confirmed; `core.py` is in neither `git ls-files` of Core nor UI. |
| F9 | corrected | Confirmed, but inline SVG is a port-wide pattern: 13 `<svg` in P (also P:4733, 6355-6455, outside this unit), 0 in upstream and fork main. Decide once for the whole page. |
| F10 | stands | Regex on `write_speed_result_text` (P:7947); text built by `writeSpeedResultText` (P App:4541-4559). Works today; reads 0 during "Testing..." and on any wording change. Latent bug. |
| F11 | stands | Text confirmed (P:8180). Gated only on sensor name and lossless, no board check. |
| F12 | corrected | Driver dependency now **confirmed**: Apertar baseline driver has 3840x2076 (`imx585.c:586,1007@origin/apertar`), port driver 3840x2072 (`imx585.c:1122@cinemate-port`). Core aliases too (`migratedImx585CropResolution`, CC:441-449@cinemate-port), so the JS alias matches Core and stays. The issue is the shared driver dependency, which must be documented. |
| F13 | stands | P:7503-7506 confirmed. |
| F14 | stands | Core `flickerFreeShutterAngles` App:1294 confirmed; 18 raw `document.createElement` in P:8484-8660 (not 20); `createDomElement` at P:10676. |
| F15 | stands | P:8915-8920 and P:8756-8770 confirmed; upstream plain arrays. Nit. |

## Final findings

### WCP-04-F1 [mismatch, major] IMX585 resolution pills read the Mode Ladder reply (state.ladderServer.pool)
- where: src/web/WebControlPage.cpp:8955-8960@cinemate-port ; src/web/WebControlPage.cpp:9021-9032@cinemate-port ; src/web/WebControlPage.cpp:8023-8038@cinemate-port ; src/web/WebControlPage.cpp:8912-8914@cinemate-port
- port: `imx585ClassRows` takes sizes from `state.ladderServer.pool` (filled only by `get_mode_ladder` via `applyModeLadder`), else from the JS class tables. Main Recording resolution pills, crop row and `imx585BaseCommands` depend on it.
- apertar way: hand-written per-sensor JS arrays as the one source (src/web/WebControlPage.cpp:5112-5121, 5249-5290@upstream-1.6.0). Merge target already has `list_sensor_modes` (src/ApertarCoreApp.cpp:9231@main; port App:12724) with width, height, bit_depth, clear_hdr, binning.
- why it matters: two features coupled through a private JS cache; a change to the ladder reply breaks the resolution pills; four sources of the same facts (Core tables, JS tables, pool, fps_max).
- rework: delete the pool read in `imx585ClassRows` and `imx585LadderFamily`. Either keep the JS tables only (upstream pattern) or fetch `list_sensor_modes` once through `sendCommand` into `state.sensorModes` and read that (mono sensor keeps working). `get_mode_ladder` carries only the ladder.
- effort: M
- deliberate: yes (commit 66b324d: "The Mode Ladder's pool decides what exists; the class tables are the fallback until it arrives")

### WCP-04-F5 [new-ground, major] Mode Ladder editor re-implements and extends Core's ladder rules in JS
- where: src/web/WebControlPage.cpp:7628-8480@cinemate-port ; src/web/WebControlPage.cpp:7765-7866@cinemate-port ; src/web/WebControlPage.cpp:8047-8086@cinemate-port
- port: about 45 JS functions: `ladderArranged` (quality sort, default maxes 25/33/50/+25), `normalizeLadderDraft`, `ladderDraftProblem`, `ladderOrderProblem`, `ladderRowStates`, `ladderSpans`, `ladderWithMode`, text format `WxH:BITS:hdr|sdr:FPS:COMP`; auto-save 200 ms after each edit. `set_mode_ladder dry_run` (App:14095-14107) is never called from JS. Core `validate` (src/camera/ModeLadder.hpp:206-256) has no sort and no default maxes; JS refuses "never used" while Core only warns (ModeLadder.hpp:243 vs WCP:7859-7860), so the two already disagree.
- apertar way: no precedent of this size. Nearest: favourites editor src/web/WebControlPage.cpp:7315-7400@upstream-1.6.0 (list from state, add/remove, one command with a joined string, no client rule engine). C1-N01: Core is the single source of truth. The port itself uses dry_run elsewhere in the WebUI (set_controls WCP:18795, boot config WCP:20246).
- why it matters: ladder rules live in two places (JS and Core) and already differ; a maintainer must change both. QML is not affected (it only reads `ladderActive`).
- rework: keep the card, rows, crop picture and pool tiles. Move quality order and default maxes into `ModeLadder.hpp` (Core fills an empty threshold by place). On each edit send `set_mode_ladder resolutions=... dry_run=true` and show Core's `errors[]` / `warnings[]` per row; save without dry_run. Delete `ladderArranged`, `ladderDefaultMax`, `normalizeLadderDraft`, `ladderDraftProblem`, `ladderOrderProblem`, `ladderSpans`, `ladderWithMode` (about 250 lines); `ladderRowStates` reads Core's `from` / `ceiling` per resolution.
- effort: L
- deliberate: yes (fork-log l.97 "approved design"; commits 1ef94fe, e472b1b, b8ee23f, 392e812; the first editor 920beb0 did show Core's dry-run messages, later commits dropped them)

### WCP-04-F2 [mismatch, minor] ladderRequest duplicates sendCommand's fetch path
- where: src/web/WebControlPage.cpp:8004-8015@cinemate-port ; src/web/WebControlPage.cpp:8017-8031@cinemate-port
- port: own `fetch("/api/command")` and error throw; comment says `get_mode_ladder` and dry runs skip `sendCommand`'s snapshot patching.
- apertar way: read-only queries go through `sendCommand`: `refreshAudioCaptureCapabilities` "const reply = await sendCommand({cmd: \"audio_capabilities\", device});" src/web/WebControlPage.cpp:11100-11113@upstream-1.6.0; `applyCommandSnapshotPatch` (8678) ignores unknown commands.
- why it matters: second call path for the same route; no dry run is sent from JS, so the stated reason is void.
- rework: `fetchModeLadder` calls `sendCommand({cmd: "get_mode_ladder"})`; delete `ladderRequest`.
- effort: S
- deliberate: yes (comment at P:8004)

### WCP-04-F3 [mismatch, minor] Ladder fetched from inside renderModeLadder on every poll
- where: src/web/WebControlPage.cpp:8394-8400@cinemate-port ; src/web/WebControlPage.cpp:10174-10175@cinemate-port
- port: `renderModeLadder` (called per snapshot, P:16028) starts `fetchModeLadder`: first fetch, 5 s retry, refetch on `ladder_active` change. Port also fetches on panel open.
- apertar way: side data fetched when a panel opens: `setSettingsPanel` "if (normalized === \"presets\") fetchPresetLibrary(true);" src/web/WebControlPage.cpp:6162-6167@upstream-1.6.0, in-flight flag (10305).
- why it matters: network side effect in a render function. The first fetch and retry exist because of F1; the `ladder_active` refetch has its own reason (ceilings change).
- rework: after F1, keep only the panel-open fetch; move the `ladder_active`-change refetch to the state poll handler (and only while the Modes panel is open).
- effort: S
- deliberate: unknown

### WCP-04-F4 [mismatch, minor] Generic pill builders know the Mode Ladder (option.locked -> showLadderLockWarning)
- where: src/web/WebControlPage.cpp:15029-15053@cinemate-port ; src/web/WebControlPage.cpp:10718-10735@cinemate-port ; src/web/WebControlPage.cpp:10446-10447@cinemate-port ; src/web/WebControlPage.cpp:8478-8480@cinemate-port
- port: `buildOptionButtonsInto` and `createFavoritePillGrid`: "button.disabled = !option.enabled && !option.locked; ... if (option.locked) { showLadderLockWarning(false); return; }"; `normalizeChoiceOptions` carries `locked`.
- apertar way: `buildOptionButtons` is generic, `{value,label,enabled}`: src/web/WebControlPage.cpp:9146-9166@upstream-1.6.0.
- why it matters: two shared widgets depend on one feature.
- rework: replace `locked` with a generic optional argument `onDisabledClick` on `buildOptionButtonsInto` / `createFavoritePillGrid` (a disabled pill stays clickable only when it is given); `ladderLockedOptions` sets `enabled:false`; the ladder call sites (P:11161, 15978, 15990) pass `() => showLadderLockWarning(false)`. Keep `system` (CSS class) and the element-taking variant.
- effort: S
- deliberate: unknown (commit 392e812 adds the warning, not the placement)

### WCP-04-F6 [bug, minor] Crop diagram and ladder names assume IMX585 3840x2160 readout for all sensors
- where: src/web/WebControlPage.cpp:7642@cinemate-port ; src/web/WebControlPage.cpp:7903-7924@cinemate-port ; src/web/WebControlPage.cpp:7696-7710@cinemate-port
- port: `ladderCropArea` fixed 3840x2160; windows clipped to it; non-IMX585 names call any 3840-wide mode "4K SDR" and any 1920-wide "2K SDR binned".
- apertar way: no precedent
- why it matters: IMX283 3840x2160 10-bit crop (window_w 3840 of 5472) shows "Whole sensor area, no crop"; 5.5K window clipped to 3840; same for IMX477 4056. Probable, needs a pool from those sensors.
- rework: readout area from the largest pool window, or show the crop picture only on IMX585; name other sensors' modes by size.
- effort: S
- deliberate: no

### WCP-04-F7 [slop, minor] Stale, contradictory and orphan comments; section banners
- where: src/web/WebControlPage.cpp:7628-7633@cinemate-port ; src/web/WebControlPage.cpp:7565-7567@cinemate-port ; src/web/WebControlPage.cpp:7626-7627@cinemate-port ; src/web/WebControlPage.cpp:8665@cinemate-port
- port: comment says the editor "asks Core about the draft (dry_run) and saves it with Save ladder" (no dry_run, no Save button, auto-save at P:8083); "no Auto under a ceiling" while code blocks Auto only in Clear HDR (P:8665); orphan ISO comments above `valueStepsFromSnapshot` and above the ladder banner; "// ---- Mode Ladder (T34) ---" banner.
- apertar way: C1-I14: comments rare, state a hazard or reason; no banners, no ticket numbers (App:10827-10828@upstream-1.6.0).
- why it matters: misleads the next reader about how saving and ISO Auto work.
- rework: delete orphans and banner; rewrite the two wrong comments to match the code.
- effort: S
- deliberate: no

### WCP-04-F8 [slop, minor] Ticket numbers, Cinemate references, and UI text pointing to core.py
- where: src/web/WebControlPage.cpp:7516@cinemate-port ; src/web/WebControlPage.cpp:7566-7576@cinemate-port ; src/web/WebControlPage.cpp:7628@cinemate-port ; src/web/WebControlPage.cpp:7900@cinemate-port ; src/web/WebControlPage.cpp:8263-8266@cinemate-port ; src/web/WebControlPage.cpp:8482@cinemate-port
- port: "(T31)", "T33:", "Request 24:", "(T34)", "as in Cinemate", "Cinemate's cropDiagram", "as Cinemate's crop list"; operator text "Sensor probe off: add modes with core.py (set_mode_ladder resolutions=...)."
- apertar way: C1-I14; `core.py` is in neither repo (`git ls-files`), only apertar-kb/working/mac-driven-loop.md:21.
- why it matters: internal labels meaningless to the original developer; operator told to use a tool they do not have.
- rework: remove ticket and Cinemate words; UI text "Sensor probe off: no modes to activate."
- effort: S
- deliberate: no

### WCP-04-F9 [mismatch, minor] Inline SVG icon strings instead of /icons PNGs
- where: src/web/WebControlPage.cpp:7644-7650@cinemate-port
- port: `ladderIcons`: five SVG strings inserted with innerHTML. Port-wide pattern: 13 `<svg` in the port page (also P:4733, 6355-6455, other units), 0 in upstream and fork main.
- apertar way: icons are files: '<img class="icon-image" src="/icons/folder.png" alt="">' src/web/WebControlPage.cpp:2448@upstream-1.6.0, CSS url('/icons/camera.png') :616.
- why it matters: second icon mechanism in one page.
- rework: one port-wide decision: add PNGs to the /icons set, or text glyphs (port already uses x in chips). Do it for all 13, not only the ladder.
- effort: S
- deliberate: unknown

### WCP-04-F10 [bug, minor] Card write speed parsed from display text with a regex
- where: src/web/WebControlPage.cpp:7945-7949@cinemate-port
- port: `/^([0-9.]+) MB\/s$/.exec(system.write_speed_result_text)`.
- apertar way: `write_speed_result_text` is display text from `writeSpeedResultText(...)` src/ApertarCoreApp.cpp:7932-7936@upstream-1.6.0; new numbers go into state as fields (C1-R4).
- why it matters: reads 0 while the test runs ("Testing...") and after any wording change, which silently removes the card-speed warning. Works today (latent).
- rework: Core adds numeric `write_speed_mbps` (from `mediaSpeedLastWriteSpeedMBps`, App:9349) to system state; JS reads it.
- effort: S
- deliberate: no

### WCP-04-F11 [pi-compat, minor] Board-specific lossless encoder measurement in operator text
- where: src/web/WebControlPage.cpp:8178-8180@cinemate-port
- port: "about 69 fps measured at 4K 12-bit" shown for any IMX585 lossless row above 30 fps, no board check.
- apertar way: no precedent
- why it matters: number is from one board (probably Pi 5); Pi 4/CM4 lower (unconfirmed).
- rework: drop the number, keep "watch the buffer bar", or have Core publish the limit.
- effort: S
- deliberate: no

### WCP-04-F12 [removed-upstream-behaviour, minor] IMX585 resolution choice reshaped; 1.85:1 sizes need the port driver
- where: src/web/WebControlPage.cpp:8922-8927@cinemate-port ; src/web/WebControlPage.cpp:9021-9032@cinemate-port ; src/web/WebControlPage.cpp:9084-9088@cinemate-port
- port: 8 family pills (Full HD binned, 4K, 2K crop, HD crop, each +HDR), sizes from pool or class tables, 3840x2076/1920x1038 aliased to 2072/1036. Core does the same alias (`migratedImx585CropResolution`, src/camera/CameraController.cpp:441-449@cinemate-port).
- apertar way: 2 base pills "Full HD"/"4K" src/web/WebControlPage.cpp:5280-5285@upstream-1.6.0 plus fixed 10-ratio crop row 5249-5278 with 3840x2076/1920x1038; fork main added one "4K Clear HDR" pill (src/web/WebControlPage.cpp:5287-5310@main).
- why it matters: confirmed driver dependency: Apertar baseline driver has 3840x2076 (imx585.c:586,1007@origin/apertar), port driver 3840x2072 (imx585.c:1122@cinemate-port). The port page and Core only work with the cinemate-port driver.
- rework: keep the shape and the alias (it matches Core); document the driver dependency for the original developer, together with the Core-side migration.
- effort: S
- deliberate: yes (commits 66b324d, 900d282)

### WCP-04-F13 [slop, nit] Empty if-branch holding only a comment
- where: src/web/WebControlPage.cpp:7503-7506@cinemate-port
- port: `if (isLosslessImx585Snapshot(snapshot)) { /* comment */ } else if (isLosslessFourKSnapshot(snapshot)) ...`
- apertar way: no precedent
- why it matters: reads as unfinished code.
- rework: `if (!isLosslessImx585Snapshot(snapshot) && isLosslessFourKSnapshot(snapshot)) ...` with one comment line.
- effort: S
- deliberate: no

### WCP-04-F14 [duplication, nit] Small duplications: flicker-free maths, toast, DOM helper
- where: src/web/WebControlPage.cpp:7590-7601@cinemate-port ; src/web/WebControlPage.cpp:7982-7993@cinemate-port ; src/web/WebControlPage.cpp:8484-8657@cinemate-port
- port: JS copy of Core `flickerFreeShutterAngles` (App:1294; Core already merges them in `pcfShutterAngleOptions`, App:1581); `showLadderLockWarning` drives the toast element and timer itself; `renderValueListsEditor` uses raw `document.createElement` 18 times next to `createDomElement` (P:10676).
- apertar way: `showToast` src/web/WebControlPage.cpp:7804@upstream-1.6.0; `createDomElement(tag, class, text)` :6555; JS mirrors of Core tables are accepted upstream (:4966-5005).
- why it matters: minor drift risk and inconsistency in one unit.
- rework: `showToast` with an optional link element; use `createDomElement`; optionally Core publishes the merged angle list.
- effort: S
- deliberate: no

### WCP-04-F15 [mismatch, nit] Mode tables in mini string formats
- where: src/web/WebControlPage.cpp:8915-8920@cinemate-port ; src/web/WebControlPage.cpp:8756-8770@cinemate-port
- port: `imx585ClassModes` "1920x1080b 3840x2160 ..." parsed with `split(/[xb]/)`; `imx283Bases` `[[21.401, "5472x3648 ..."]]`.
- apertar way: plain arrays of "WxH" strings: src/web/WebControlPage.cpp:5112-5121@upstream-1.6.0 (imx477ResolutionOptions).
- why it matters: small private encodings to learn.
- rework: arrays of strings or objects with a `binned` field when touched.
- effort: S
- deliberate: unknown
