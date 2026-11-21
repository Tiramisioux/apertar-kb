# Review: Boot-config (stage 2)

| Item | Value |
| --- | --- |
| Refs | `@port` = Core `cinemate-port` `01f170c`, UI `7ea9afc`. `@up` = `upstream-1.6.0` (Core `35dbe67`, UI `43888e5`) |
| Short names | `BCT` = `src/hardware/BootConfigText.hpp`; `App`, `WCP` as in BRIEF; helper = `scripts/apertar-boot-config`; `SAB` = UI `src/SystemActionBridge.cpp` |
| Read completely | BCT (1355), helper (71), sudoers (4), `tools/boot_config_helper_test.sh` (33), README l.179-211, App l.3500-3846, l.9160-9215, l.14586-14591, UI `41ff827`. `tools/boot_config_test.cpp`: head, fixture, all `check(` lines |
| Yardstick | `apertar-conventions.md` rule ids. Cross-refs: `rev-App-1.md` F3-F12, F18; `rev-WCP-10.md` F1-F3; `sweep-board-support.md` X-3, X-4, X-6, X-11 |
| Labels | confirmed unless marked |

## 1. Summary

The feature is deliberate and carefully argued (BCT header l.2-28, KB `architecture/config.md` 7.1, nine commits with
`Tested:` lines, two host tests). Its core idea fits Apertar: edit config.txt in place by commenting and uncommenting
the image's own lines, keep every other byte, keep a `.bak`. Upstream does the same for `apertar-hardware.conf` (HW-8).

What would make the original developer stop:

1. A second write channel beside `/api/command`: `POST /api/boot-config` injects `"cmd"` into the body, carries HTTP
   status codes, tests the `Origin` header and runs under its own `bootConfigMutex` (CMD-1, CMD-3, WEB-3, WEB-6).
2. A root helper of a new shape (POSIX sh in Core `scripts/`, sudoers in Core `config/`, content on stdin, no
   `timeout`) and three write routes, where upstream has one: `sudo -n install` (PLT-4, PLT-5, PLT-6).
3. A free-text `text` field that writes any config.txt as root from the LAN (C1 intent 9).
4. Size: a 1355-line header-only engine that also does LCS diffs, wire JSON, managed-line marks and fps labels.
5. It ignores the image's own sensor mechanism (`include camera-selection.txt`, which upstream UI treats as
   authoritative).

No protocol break: an unmodified UI or Core keeps working (section 5).

## 2. Findings

| Id | Sev | Cat | Title | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | major | mismatch | Own POST route with cmd injection, HTTP status, Origin test, own mutex | yes |
| F2 | major | mismatch | Root helper of a new shape plus three write routes; upstream has one `sudo -n install` | yes |
| F3 | major | security | `text` field: any config.txt as root from any LAN client | yes |
| F4 | major | new-ground | 1355-line header-only engine; scope beyond the card | yes |
| F5 | major | mismatch | `include camera-selection.txt` invisible; image's sensor mechanism bypassed (probable) | unknown |
| F6 | minor | mismatch | Engine in `src/hardware/` writes wire JSON with its own `jsonString`; nested replies | no |
| F7 | minor | removed-upstream-behaviour | Touch UI fan mode now fails without Core | yes |
| F8 | minor | bug | Fan mode refused on a config.txt without `[pi5]`/`[pi4]`/`[all]` once the helper is installed | no |
| F9 | minor | pi-compat | Board model: unknown board = Pi 5; `[pi3]` matches Zero 2 W; Pi 3 gets the Pi 5 link list | no |
| F10 | minor | duplication | Two config.txt readers with two filter rules (`hwconf::parseConfigTxt` vs `bootconf`); `boolFieldValue` | no |
| F11 | minor | bug | Sensor list lacks IMX283 although the port supports it | no |
| F12 | minor | mismatch | Operator sentences: install commands, wire field names, wrong advice when helper exists without sudoers | no |
| F13 | minor | slop | Header essay with Cinemate history, banners, per-field comments, non-ASCII label glyphs, `#!/bin/sh` | no |
| F14 | minor | new-ground | Host tests `tools/boot_config_test.cpp`, `tools/boot_config_helper_test.sh` | yes |
| F15 | nit | slop | README lists socket commands; commits authored "Claude", `claude/*` merge | no |

### F1. Own POST route outside `/api/command` (major, mismatch)

- Port: `App:9170-9196 @port`:
  `payload.insert(brace + 1, empty ? "\"cmd\":\"set_boot_config\"" : "\"cmd\":\"set_boot_config\",");`, then
  `parseControlCommand(payload)`, revision from header `x-apertar-revision`, `request.headers.count("origin") > 0`
  as "browser", `bootConfigSet(...)` called directly. `BootConfigReply { int status; std::string body; }`
  (`App:3761-3764`) returns 200/400/403/409/500. `bootConfigSet` locks `bootConfigMutex()` (`App:3512-3517`, `:3785`),
  not `commandMutex_`. The socket path `App:14589-14590` drops the status: `return bootConfigSet(...).body;`.
  WCP side: `fetch("/api/boot-config", { method: "POST", headers, body: JSON.stringify(body) })` (`WCP:20009`).
- Apertar way: `handleWebCommand` = `parseControlCommand(payload)` -> `handleCommand` (`App:7085-7091 @up`); the page
  uses `sendCommand` via `POST /api/command` (WEB-3); one lock (CMD-3); routes do no header work (WEB-6, security is
  in `WebServer::allowedBrowserOrigin`, `src/web/WebServer.cpp:156-171 @up`). Upstream writes the same file from
  inside `handleCommand`: `if (command.name == "set_fan_mode") { ... applyFanMode(*value, &errorMessage) ... }`
  (`App:10568-10577 @up`).
- Why: two ways into one setter, a second error channel (HTTP status), an `old_page` rule upstream never needed
  (CMD-30: Core and page ship together), a per-feature mutex.
- Rework: delete `POST /api/boot-config`, `BootConfigReply`, the `Origin` test and `bootConfigMutex()`.
  `get_boot_config` / `set_boot_config` become ordinary blocks returning `okReply` / `errorReply` strings; `revision`
  and `dry_run` stay as flat command fields. `bootConfigPost` in WCP becomes `sendCommand({ cmd: "set_boot_config", ... })`.
  Keep `GET /api/boot-config` as a read route (precedent `GET /api/config`, `App:7168-7173 @up`). Same as App-1 F4.

### F2. Root helper of a new shape, three write routes (major, mismatch)

- Port: `writeBootConfigText` (`App:3533-3611`): (1) direct write when `access(W_OK)` (only true for the
  `APERTAR_BOOT_CONFIG` copy or Core as root), own temp + `fsyncPath` + rename; (2)
  `runShellCommandCapture("sudo -n " + shellQuote(kBootConfigHelper) + " < " + shellQuote(staged))`; (3)
  `sudo -n install -m 644` of the backup and of the staged file. Helper: `#!/bin/sh`, reads stdin, fixed `DEST`,
  in Core `scripts/`; sudoers `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-boot-config ""` in Core `config/`.
- Apertar way: fan mode = one route, `"sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath)`
  (`App:3155-3158 @up`). Root helpers (PLT-4) are Qt-free C++ in `UI/src/`, sudoers in `UI/systemd/` pinning verbs:
  `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-standby-usb off, /usr/local/libexec/apertar-standby-usb on`;
  called as `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (`App:1541-1545 @up`).
  Core holds only `config/` + `scripts/start-apertar-core.sh` (PLT-6, conventions 5 "Root helpers inside the Core repo").
  Atomic write exists: `settingsFile::atomicWrite` (`src/util/SettingsFile.hpp:36-55 @up`).
- Why: README itself says the helper is optional ("Without it, Core falls back to `sudo -n install`, as the fan mode
  always has", `README.md:207 @port`). On the stock image the upstream route already works. The helper is a fourth
  install step, a second file-replacing tool and a content-carrying root interface (F3).
- Rework: one route, upstream's. `writeBootConfigText` = stage text in temp, `sudo -n install -m 644 <dest> <dest>.apertar.bak`,
  `sudo -n install -m 644 <tmp> <dest>`, "<Action> needs sudo permission." on denial (PLT-5). Delete the helper,
  its sudoers, `tools/boot_config_helper_test.sh`, the direct branch, `fsyncPath`, the README install block. If the
  owner wants a narrow helper later: C++ in `UI/src/`, PLT-4 shape, `timeout`. Covers App-1 F10, F11.

### F3. Free text to config.txt as root from the LAN (major, security)

- Port: `const std::optional<std::string> edited = command.string("text");` -> `applyRequest(edited ? *edited : text, ...)`
  -> `writeBootConfigText(result.text, ...)` (`App:3804-3836`). Checks: not empty, <= 64 KiB, no NUL
  (`BCT:1133-1139`), and the helper's `[pi5]|[pi4]|[all]` grep (helper l.51). Any `kernel=`, `os_prefix=`,
  `initramfs`, overlay or `dtparam` passes.
- Apertar way: C1 intent 9 "never a path from the WebUI or config"; `// Fixed executable and arguments only; never
  accept paths from WebUI/config.` (`App:1543 @up`). Upstream's root write of config.txt carries only the generated fan
  block (`fanModeBlock`, `App:3042 @up`). The free-text editor upstream is for `apertar-hardware.conf`, written as pi
  (`saveHardwareConfigFile`, `App:5323-5385 @up`).
- Rework: drop `text` (Edit file, Use This Text, `lineChanges`, `displayDiffers`, `textProblem`, `/api/boot-config/parse`).
  Only lines generated from validated fields reach the file. Same as App-1 F7; WCP-10 F3 drops the editor UI.

### F4. Engine size and scope (major, new-ground)

- Port: `BCT` 1355 lines, header-only, `apertar::bootconf`: board model and filters (l.76-129), sensor and link tables
  with Mbps and 4K-fps labels (l.133-207), display table, line parser, `Document`, `Editor` class with insert/tail
  bookkeeping (l.698-764), `applyRequest` (l.810-1125, 315 lines), LCS `lineChanges` (l.1164-1212), `stateJson` /
  `changesJson` / `jsonString` (l.1225-1340), FNV-1a `revisionOf`. Plus App `l.3651-3846` (195 lines) and about 730 lines
  of WCP JS.
- Apertar way: no precedent for config.txt beyond the fan block (`fanModeBlock` / `stripManagedFanBlock` /
  `detectManagedFanMode`, `App:3042-3117 @up`). Header-only modules upstream are small (`hardware/ButtonActionList.hpp`
  121 lines, `camera/DefaultTuningSelection.hpp`); logic with size is a `.hpp/.cpp` pair listed in `add_executable`
  (HW-23, PLT-1). In-place editing that keeps comments is the upstream rule for programmatic writes (HW-8).
- Deliberate: yes. BCT l.8-13 weighs Cinemate's fenced block against the image's "uncomment the dtoverlay for your
  sensor" comments and picks in-place edits so "a saved file is still the Apertar layout, line for line".
- Verdict: simplify. Keep the in-place approach (a managed block as App-1 F6 proposes would have to comment out the
  image's `[pi5]` sensor lines anyway, or two sensors load). Cut to: parse, `readState`, `applyRequest` with read-back,
  sensor / link / toggles / RP1 / display. Drop with F3: `lineChanges`, `displayDiffers`, `textProblem`, `managed`.
  Drop the label decoration (`mbpsPerLane`, `fps4k`, `linkOptionLabel`): Hz list only. Move JSON to App (F6).
  Make it `src/hardware/BootConfig.{hpp,cpp}`, `.cpp` listed in CMake. Expected size: about 600-700 lines.
- Risk of rework: the read-back refusal is the safety net; keep its tests while cutting.

### F5. `include camera-selection.txt` invisible (major, mismatch, probable)

- Port: `lineFrom` returns no key for a line without `=` (`BCT:292-293`), so `include camera-selection.txt` is never
  seen. The fixture keeps the image's comment: `#IMPORTANT! If your camera module doesn't get detected by the script,
  remove the "include camera-selection.txt" line` (`tools/boot_config_test.cpp:56`); the include line itself is gone
  from the dev Pi's file.
- Apertar way: `// Apertar's camera-selection file is authoritative ...`
  `scanBinaryFileForSensorToken(QStringLiteral("/boot/firmware/camera-selection.txt"), 4096)` (UI
  `src/DeviceInfoBridge.cpp:213-215 @up`). The image selects the sensor through that included file.
- Failing input (probable, no stock file here): fresh Apertar-Beta 1.6.0 file with `include camera-selection.txt`
  in `[pi5]` and all sensor lines commented. Card shows cam0 "none"; choosing IMX585 uncomments a line in config.txt;
  the included file still loads its sensor: two overlays on one port. Read-back passes, because it does not see the include.
- Rework: in `readState`, an applying uncommented `include` sets `editable = false` for the camera rows with one
  sentence ("config.txt includes camera-selection.txt: the sensor comes from that file."), the same shape as
  `state.problem` (`BCT:616-622`). Settle: `grep -n '^include' /boot/firmware/config.txt` on a fresh image.
  Same as sweep-board-support X-3.

### F6. Engine writes wire JSON (minor, mismatch)

- Port: `jsonString` (`BCT:1225-1246`) re-implements `escapeJson`; `stateJson` builds nested `board{}`, `cameras{}`,
  `toggles{}`, `rp1{}`, `display{overlays[],lines[]}`, `candidates{}`, `sensors[{link{options[]}}]`, `displays[]`,
  `warnings[]`, `managed[]`. App adds `drm[]` (`App:3676-3688`) and `changes[]`.
- Apertar way: replies are built in App with `std::ostringstream` and `escapeJson` (CMD-9, `App:108-128 @up`);
  `src/hardware/` has no wire knowledge (HW-6). One nested object per topic is precedented (`"imu":{...}`,
  `imuStatusBody` `App:130 @up`).
- Rework: move serialisation to App as `bootConfigBody(state)` with `escapeJson`; one `"boot_config":{...}` object of
  scalars plus the fixed option lists the page needs; option labels on the page side (WEB-8 duplicates lists by hand).
  `drm[]` -> count of connected DPI connectors. App-1 F9.

### F7. Touch UI fan mode now needs Core (minor, removed-upstream-behaviour)

- Port: UI `41ff827` deletes `fanModeBlock`, `stripManagedFanBlock`, the `QTemporaryFile` and
  `invokePrivilegedCommand("install", ...)`; adds `coreFanModeCommand` (`QLocalSocket`, id 42002, 8 s). Socket down:
  "Connect to Apertar Core before changing the fan mode."
- Apertar way: each process carries its own fan writer (PLT-11: `App:3042` vs `UI/src/SystemActionBridge.cpp:64 @up`,
  violation listed: "a shared library refactor of these copies"). Upstream UI changes the fan mode with Core stopped.
- Deliberate: yes (commit body: "a fan change could race a Boot Config save").
- Verdict: keep if the owner accepts the dependency; the race reason holds while Core edits other lines of the
  same file. The client copy itself follows UIC-3 (`MediaStatusBridge.cpp:20-42 @up`, id 42001) and UIC-16 (bounded).
  Say it in the handoff. Not tried by hand on the Pi (commit: "build only").

### F8. Fan mode refused without a section header (minor, bug)

- Port: helper `if ! grep -Eq '^[[:space:]]*\[(pi5|pi4|all)\]' "$TMP"; then ... exit 2` (l.51-54); Core returns the
  helper's text and does not fall through (`App:3586-3592`); `applyFanMode` uses this writer (`App:3643`).
- Upstream: `applyFanMode` writes any non-empty config.txt (`App:3127-3165 @up`).
- Failing input: helper installed, config.txt with only `[cm4]`/`[cm5]` or no section; Silent fan mode -> error
  "apertar-boot-config: input has no [pi5], [pi4] or [all] section ...". Works on 1.6.0. Goes away with F2.

### F9. Board model (minor, pi-compat)

- Port: `if (!board.detected) board.family = "pi5";` (`BCT:95`); `filterApplies("pi3")` is true for every BCM2837/2710
  board, Zero 2 W included (`BCT:93`, `:114`); `linkOptionsFor` trims only for `pi4` (`BCT:186`), so Pi 3 / Zero 2 W
  get IMX477 up to 972 MHz. App reads only `/proc/device-tree/compatible` (`App:3656`).
- Apertar way: `pipelineFromCompatible` returns `Unknown` for an unknown board; reader tries
  `/sys/firmware/devicetree/base/compatible` then `/proc/device-tree/compatible` (`src/camera/DefaultTuningSelection.hpp:18-50 @up`, PLT-3).
- Rework: unknown board -> `editable = false` with a sentence (keep "Pi 5" only for the test copy); `pi02` excluded
  from `pi3`; link list limited to `pi5` family, others get the overlay default only; read compatible with upstream's
  two-path order. Sweep-board-support X-4, X-6.

### F10. Two config.txt readers (minor, duplication)

- Port: `facts.dpiLines = hwconf::parseConfigTxt(readTextFileRaw(bootConfigPath())).dpiLines;` (`App:4976`), filter
  `[all]`/`[pi5]` only (`src/hardware/HardwareConfigText.hpp:1040` ff.); `bootconf::isDpiOverlay` says
  "Same rule as HardwareConfigText's parseConfigTxt" (`BCT:248`) but `bootconf` knows the board. `boolFieldValue`
  (`App:3708-3717`) adds `on/yes/off/no`.
- Apertar way: per-class copies of small helpers are accepted (HW-2, rough edges), but one file read with two filter
  rules gives two answers on a Pi 4 (sweep X-5). Booleans: lenient `== "true" || == "1"` (rough edges, `App:9486 @up`).
- Rework: Controls validator takes `bootconf::readState(...).displayLines` with the detected board; delete the DPI part
  of `parseConfigTxt`. `boolFieldValue` -> the upstream lenient test.

### F11. IMX283 missing from the sensor list (minor, bug)

- Port: `// The sensors Core has handling for (CameraController detectSensorFamily: imx577, imx477, imx294, imx585).`
  (`BCT:151`); list l.162-171 has no `imx283`. The port supports IMX283 (`src/camera/CameraController.cpp:660-675 @port`).
- Failing input: cam0 `dtoverlay=imx283,cam0`. Card shows "imx283" as an unlisted sensor; switching to IMX585 and back
  is impossible from the card.
- Rework: add `{"imx283", "imx283", "IMX283", false, 0, 0, {}}`; drop the comment (it goes stale with each sensor).

### F12. Operator sentences (minor, mismatch)

- Port: "Writing config.txt needs root. Install the helper: sudo install -m 0755 -o root -g root ~/ApertarCore/scripts/... then sudo install -m 0440 ..." (`App:3605-3608`);
  "... Send confirm_display=true to save anyway." (`App:3824-3827`); "<port>_link_frequency must be a whole number of Hz, or null ..." (`App:3733`).
  The install advice also appears when the helper is installed but its sudoers file is missing (helper refused by sudo
  -> fallback -> "password" -> same advice).
- Apertar way: one sentence for the operator, "<Action> needs sudo permission." (`App:3164 @up`, PLT-5, STY-10);
  install steps in README.
- Rework: after F2 the denial sentence is "Writing config.txt needs sudo permission."; the display guard becomes a
  `window.confirm` on the page (WCP-10); drop wire names from sentences. App-1 F8.

### F13. Comments and text style (minor, slop)

- Port: BCT l.2-28 essay: "Ported from Cinemate's settings-editor config.txt tab (cinemate src/module/app/boot_config.py)";
  l.152 "Cinemate's resources/sensors.json: the will127534 IMX585 driver table"; banners `// ---- the board ----`
  (l.42, 74, 131, 255, 472, 626, 1127, 1223) and `App:3651`; trailing comments on nearly every struct field; labels with
  `·` and `—` (`BCT:197-205`); fixture comment with a date (`tools/boot_config_test.cpp:18`). Helper `#!/bin/sh`, `[ ]`.
- Apertar way: STY-8 (rare one-line hazard comments, headers uncommented), STY-9 (no other projects' history),
  STY-16 (`#!/bin/bash`, `set -euo pipefail`, `[[ ]]`). Upstream Core has 2 non-ASCII lines (`•`, `App:2366 @up`).
- Rework: cut the header to two lines (what the file edits, that every other byte is kept); delete banners and
  Cinemate references; keep the one hazard comment at `BCT:950`; ASCII labels. Helper goes with F2.

### F14. Host tests (minor, new-ground)

- Port: `tools/boot_config_test.cpp` (427 lines, about 75 checks, fixture = dev Pi file), `tools/boot_config_helper_test.sh`
  (10 checks). Not in CMake.
- Apertar way: no tests, no test target (PLT-12, conventions 5).
- Deliberate: yes (commit messages, KB).
- Verdict: keep the C++ test out of the build, as now, if the owner keeps `tools/*_test.cpp` for the port as a whole
  (cross-cutting decision). The helper test goes with F2.

### F15. README and commits (nit, slop)

- README `l.211` lists socket commands and fields (STY-14: README stops at CLI flags); `I²C`, `I²S` glyphs.
- Commits `f19b245 dda1713 2955ef8 8a56545 afa00e8 496817f` authored "Claude"; merge `4581a69` of
  `claude/cool-volta-y7fiw7` (STY-15: linear, no `claude/*` merges). For the commit-clarity step.

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `apertar::bootconf` engine (BCT) | simplify | F4: keep in-place edit + read-back; drop diff, text, managed, labels; `.hpp/.cpp` pair |
| Engine JSON (`jsonString`, `stateJson`, `changesJson`) | rework-to-upstream-pattern | F6: App with `escapeJson`, one flat-ish object |
| `bootConfigMutex()` | rework-to-upstream-pattern | F1: `commandMutex_` covers both writers once the route is gone |
| `writeBootConfigText()` | simplify | F2: one `sudo -n install` route plus backup |
| `fsyncPath()` | simplify | F2: deleted with the direct branch; else `settingsFile::atomicWrite` |
| `BootConfigReply{status, body}` | rework-to-upstream-pattern | F1: commands return reply strings |
| `bootConfigGet`, `bootConfigSet` | simplify | F1: bodies of the two `handleCommand` blocks |
| `bootConfigFacts`, `bootConfigRequestFrom` | keep | Small App free helpers in the anonymous namespace, CMD-25 shape |
| `drmConnectorsJson`, `bootConfigJson` | simplify | F6: counts and scalars |
| `boolFieldValue` | rework-to-upstream-pattern | F10: lenient `== "true" \|\| == "1"` |
| `bootConfigPath()` + `APERTAR_BOOT_CONFIG` | simplify | Test hook only; path parameter for the test, `kBootConfigPath` in Core (App-1 F3) |
| Board model (`Board`, `filterApplies`, `boardPorts`) | simplify | F9: unknown = not editable; upstream two-path compatible read |
| Root helper `scripts/apertar-boot-config` | rework-to-upstream-pattern | F2: drop; upstream `sudo -n install`; a future helper in PLT-4 shape |
| `config/apertar-boot-config.sudoers` | rework-to-upstream-pattern | F2: goes with the helper; upstream sudoers live in `UI/systemd/` |
| Host tests | keep | F14: outside the build; owner decision for the port's `tools/` |
| UI `coreFanModeCommand` | keep | F7: UIC-3 private client, bounded; behaviour change noted |

## 4. What conforms

- `set_fan_mode` contract unchanged; `fanModeBlock`, `stripManagedFanBlock`, `detectManagedFanMode`, `kFanBlock*`
  untouched (`App:3622-3649 @port` vs `App:3127 @up`).
- Two flat `if (command.name == ...)` blocks in `handleCommand` (`App:14586-14591`); command appended to the
  `list_commands` line without reformatting (`App:12930`) (CMD-2, rough edges).
- Command fields snake_case, flat strings, booleans as strings (`bootConfigRequestFrom`, CMD-7, CMD-8).
- `GET /api/boot-config` is a read route in the `GET /api/config` shape (WEB-4, WEB-5).
- In-place editing that keeps comments and every other byte, `.bak` beside the file, temp + rename (HW-8; same as
  `saveHardwareConfigFile`, `App:5359 @up`).
- Engine is pure text in / text out, no app or I/O includes (HW-6); `#pragma once`, `namespace apertar::...` (STY-4).
- Log line `ApertarCore boot config: wrote ... via ...` (STY-7).
- Board detection is a pure function of the compatible string, as `pipelineFromCompatible` (PLT-3 shape).
- No new dependency, no JSON library, no test target (CMD-9, PLT-12 spirit).
- UI `41ff827`: private socket client copied from `MediaStatusBridge` (id 42002 next to 42001), bounded 8 s, Core's
  error shown as written (UIC-3, UIC-16, CMD-28).
- Sudoers rule pins the path with no arguments; the helper's destination is fixed (narrower than a wildcard).

## 5. Protocol check

| Pair | Result |
| --- | --- |
| Port Core + upstream UI | works: UI writes the fan block itself with `sudo -n install` (outside `bootConfigMutex`, as upstream) |
| Upstream Core + port UI | works: UI sends `set_fan_mode`, present upstream (`App:10568 @up`) |
| Flat parser | `set_boot_config` fields are flat scalars; `text` is one escaped string (needs the port's 1 MiB socket line) |
| Replies | nested objects/arrays in `boot_config`, `changes`, `drm` (F6); extra `code` key in errors (App-1 F5); not read by any upstream client |

## 6. Not judged here

- WCP card (about 730 JS lines): WCP-03 F2, WCP-10 F1-F3, F8.
- `errorReplyBody` and error codes: App-1 F5.
- Pi behaviour of the write routes: KB 7.1 says the helper path was confirmed on the Pi 2026-11-01 (one IMX585 save);
  fan mode through Core from the touch UI: not tried (commit `41ff827`: "build only").

## Skeptic

All port lines re-read at `@cinemate-port`, upstream lines at `@upstream-1.6.0`, commits with `git show -s`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Port lines confirmed. But a separate POST route that writes a file and returns HTTP 400 is upstream precedent: `POST /api/config` calls `saveHardwareConfigFile(request.body, ...)`, sets `response.status = 400`, and takes no `commandMutex_` (App:7175-7195@up). What is not precedented: the `"cmd":"set_boot_config"` splice into the body to reuse `parseControlCommand`, the `X-Apertar-Revision` header, 403/409 codes, the `origin`-presence test (it is an old-page rule, not a security check), and the same setter reachable two ways. The static `bootConfigMutex()` follows the function-local `static std::mutex cacheMutex` pattern (App:2269@up); it exists only because the route bypasses `commandMutex_`. Severity stays major. |
| F2 | stands | `writeBootConfigText` has three branches (App:3546-3611@port); helper is POSIX sh in Core `scripts/` with sudoers in Core `config/`, no timeout; upstream Core `scripts/` holds only `start-apertar-core.sh`, its root helpers are UI-side with `.sudoers` in UI `systemd/` and are called with `/usr/bin/timeout` (App:1544-1549@up). Fan mode upstream: one `sudo -n install` (App:3155-3158@up). |
| F3 | stands | Confirmed. Context added: upstream WebUI already lets any LAN client do destructive things (`format_media`, `POST /api/config` free text, `[run_script]` paths run as pi), so the trust model is "LAN is trusted"; the difference is root-written free text into the boot file, which upstream never does. Major, not blocker. Commit `3b87d99` is Patrik's: deliberate yes. |
| F4 | stands | 1355 lines confirmed, 8 banners, `Editor`, `applyRequest` at :810, `lineChanges` :1164, `stateJson` :1250, `revisionOf` :1343. Note: the port's `HardwareConfigText.hpp` (1141 lines) is the same header-only shape, so the .hpp/.cpp split is a port-wide question; header-only lets `tools/*_test.cpp` build with plain g++. |
| F5 | stands | `lineFrom` returns no key without `=` (BCT:289-293); fixture keeps the image comment with the include removed (test:56); upstream UI treats `camera-selection.txt` as authoritative (UI DeviceInfoBridge.cpp:213-215@up). Stock image content not in this container: probable. |
| F6 | stands | `jsonString` re-implements `escapeJson`, which upstream declares in `src/ipc/ControlProtocol.hpp:25` and no upstream `src/hardware/` file writes reply JSON. Arrays in replies have precedent in web routes (`/api/media`), so the nesting part is weaker than the second-writer part. Minor. |
| F7 | stands | UI `41ff827` (Patrik, "Tested: ... build only") replaces upstream's `fanModeBlock` + `install` write (UI SystemActionBridge.cpp:64ff@up) with `coreFanModeCommand` (port :66-97). Race is real: upstream already has two unsynchronised writers, the port adds a third editor of the same file. |
| F8 | corrected | Code path confirmed, but the failing input is unrealistic: every Raspberry Pi OS / Apertar config.txt has an `[all]` section, and the card itself refuses a file without `[pi5]`/`[all]` (BCT:616-622). Severity nit. |
| F9 | corrected | `pi5` fallback, `pi3` for bcm2837/2710, `pi02` = `pi3 && "zero 2"`, Pi-4-only trim all confirmed. Dropped the two-path claim: `/proc/device-tree` is a symlink to `/sys/firmware/devicetree/base` on Pi OS, so the order is cosmetic. Zero 2 W filter semantics are from Raspberry Pi docs, not in this container: probable. |
| F10 | stands | `facts.dpiLines = hwconf::parseConfigTxt(...)` (App:4976@port) filters `[all]`/`[pi5]` only (HCT:1037-1048); `isDpiOverlay` copies the name rule with board-aware filters. `boolFieldValue` tri-state confirmed (App:3709-3718); upstream has no bool getter and uses `== "true" \|\| == "1"`. |
| F11 | stands | Sensor table (BCT:151-171) has no imx283; port CC `detectSensorFamily` returns `Imx283` (CC:2569-2570@port); driver ships `imx283-overlay.dts`. |
| F12 | corrected | Install-commands sentence and the wrong advice in the half-installed case confirmed (App:3605-3608: helper refused by sudo prints no `apertar-boot-config:`, falls to `install`, fails on "password", says "Install the helper"). Dropped the "no wire names" part: upstream socket errors name fields too (`"set_fan_mode requires value."`, App:10571@up), so `cam0_link_frequency must be ...` matches. The `confirm_display` sentence is a socket-client message; the page handles it by code. |
| F13 | stands | Cinemate references (BCT:4, :152), 8 `// ----` banners vs 0 in upstream App, 5 non-ASCII lines, `#!/bin/sh` + `[ ]` + `set -u` vs upstream `#!/bin/bash` + `set -euo pipefail` (core scripts/start-apertar-core.sh@up). |
| F14 | stands | Upstream Core has no `tools/` dir; port has 15 `tools/*_test.cpp`, none in CMakeLists.txt. Owner decision for the whole `tools/` set. |
| F15 | stands | Six commits authored "Claude" (`f19b245 dda1713 2955ef8 8a56545 afa00e8 496817f`), merge `4581a69` (Patrik) of `claude/cool-volta-y7fiw7`; README:211 socket paragraph confirmed. |

## Final findings

### Boot-config-F1 [mismatch, major] Own POST /api/boot-config with cmd splice, revision header, 403/409 and an Origin-presence rule; one setter, two entry points
- where: src/ApertarCoreApp.cpp:9170-9196@cinemate-port ; src/ApertarCoreApp.cpp:3512-3517@cinemate-port ; src/ApertarCoreApp.cpp:3761-3764@cinemate-port ; src/ApertarCoreApp.cpp:3775-3836@cinemate-port ; src/ApertarCoreApp.cpp:14586-14590@cinemate-port ; src/web/WebControlPage.cpp:20004-20016@cinemate-port
- port way: route splices `"cmd":"set_boot_config"` into the body, `parseControlCommand`, revision from `x-apertar-revision` header, `browser = request.headers.count("origin") > 0` decides the `old_page` 409; `bootConfigSet()` under `bootConfigMutex()` returns `BootConfigReply{status, body}` with 200/400/403/409/500; socket `set_boot_config` calls the same setter and drops the status. Page uses `fetch("/api/boot-config")` with its own header.
- Apertar way: a file-writing route of its own is precedented: `POST /api/config` -> `saveHardwareConfigFile(request.body, ...)`, 400 on failure, `okReply(-1, ...)` (App:7175-7195@upstream-1.6.0). Commands go `handleWebCommand` -> `parseControlCommand` -> `handleCommand` (App:7085-7091@upstream-1.6.0); the page's fan mode is `sendCommand({ cmd: "set_fan_mode", value })` (WCP:11093@upstream-1.6.0), handled inside `handleCommand` (App:10568-10577@upstream-1.6.0). Origin policy is server-wide in `allowedBrowserOrigin` (src/web/WebServer.cpp:156-171@upstream-1.6.0). No route reads custom headers or returns 403/409.
- why it matters: a parallel command plane for one card: body rewriting, a header protocol, a second error channel and an old-page rule the original developer has nowhere else.
- rework: delete `POST /api/boot-config`, `BootConfigReply`, the Origin test, the header and the 403/409 codes. `get_boot_config` / `set_boot_config` become ordinary `handleCommand` blocks with `okReply` / `errorReply` (then `commandMutex_` serialises them with `set_fan_mode` and `bootConfigMutex()` can go); `revision`, `dry_run`, `confirm_display` stay flat fields. WCP `bootConfigPost` -> `sendCommand({cmd:"set_boot_config", ...})`. A GET read route like `GET /api/config` may stay. Same as rev-App-1 F4, rev-WCP-10 F1.
- effort: M
- deliberate: yes (comment App:9178 "the command parser wants a name, so it gets one"; KB architecture/config.md 7.1 describes the 409/revision design; commit `2955ef8`).

### Boot-config-F2 [mismatch, major] Root helper of a new shape plus three write routes, where upstream has one sudo -n install
- where: src/ApertarCoreApp.cpp:3533-3611@cinemate-port ; scripts/apertar-boot-config:1-71@cinemate-port ; config/apertar-boot-config.sudoers:4@cinemate-port ; README.md:199-207@cinemate-port
- port way: `writeBootConfigText`: direct write when `access(W_OK)` (own temp + `fsyncPath` + rename), else `sudo -n /usr/local/libexec/apertar-boot-config < staged` (POSIX sh, content on stdin, in Core `scripts/`, sudoers `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-boot-config ""` in Core `config/`, no timeout), else `sudo -n install` fallback.
- Apertar way: fan mode: `"sudo -n install -m 644 " + shellQuote(tempPath) + " " + shellQuote(kBootConfigPath)` (App:3155-3158@upstream-1.6.0). Upstream root helpers are verb-pinned, live with UI (`systemd/apertar-standby-usb.sudoers`, `apertar-standby-low-power.sudoers` in Apertar-UI@upstream-1.6.0) and are called `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb <verb>` (App:1544-1549@upstream-1.6.0). Upstream Core `scripts/` holds only `start-apertar-core.sh`.
- why it matters: README itself calls the helper optional ("Without it, Core falls back to `sudo -n install`, as the fan mode always has"); it adds install steps, a content-carrying root interface (F3) and three paths to reason about.
- rework: `writeBootConfigText` = stage temp, `sudo -n install -m 644 <dest> <dest>.apertar.bak`, `sudo -n install -m 644 <tmp> <dest>`, "Writing config.txt needs sudo permission." on denial. Delete `scripts/apertar-boot-config`, `config/apertar-boot-config.sudoers`, `tools/boot_config_helper_test.sh`, the direct branch (keep only what the `APERTAR_BOOT_CONFIG` test path needs, a plain `writeTextFileRaw`), `fsyncPath`, `kBootConfigHelper`, the README install block. A future narrow helper follows the upstream helper shape (UI-side, verb-pinned sudoers, `timeout`).
- effort: S
- deliberate: yes (commit `dda1713` and helper header l.4-15; README l.199-207).

### Boot-config-F3 [security, major] set_boot_config `text` writes any config.txt as root from any LAN client
- where: src/ApertarCoreApp.cpp:3804-3836@cinemate-port ; src/hardware/BootConfigText.hpp:1133-1139@cinemate-port ; scripts/apertar-boot-config:51-54@cinemate-port
- port way: `command.string("text")` -> `applyRequest(edited, ...)` -> `writeBootConfigText` as root. Checks: non-empty, <= 64 KiB, no NUL, one `[pi5]`/`[pi4]`/`[all]` line. `kernel=`, `os_prefix=`, initramfs, any overlay pass.
- Apertar way: "Fixed executable and arguments only; never accept paths from WebUI/config." (App:1543@upstream-1.6.0). Upstream's root write of config.txt carries only the generated fan block (`fanModeBlock`, App:3042@upstream-1.6.0). The free-text editor upstream is for `apertar-hardware.conf`, written as pi (`saveHardwareConfigFile`, App:5323-5385@upstream-1.6.0). Upstream does trust the LAN for destructive acts (`format_media`, `[run_script]` paths), but never with root-written free text.
- why it matters: an unauthenticated LAN request can make the camera unbootable or boot another kernel.
- rework: drop the `text` field and with it Edit file / Use This Text, `lineChanges`, `displayDiffers`, `textProblem`, `POST /api/boot-config/parse`. Only lines generated from validated fields reach the file. View file / Download stay (read only). Same as rev-App-1 F7, rev-WCP-10 F3.
- effort: M
- deliberate: yes (commit `3b87d99`, Patrik; README l.196).

### Boot-config-F4 [new-ground, major] 1355-line header-only engine; scope beyond what the card needs
- where: src/hardware/BootConfigText.hpp:1-1355@cinemate-port ; src/ApertarCoreApp.cpp:3651-3846@cinemate-port
- port way: `apertar::bootconf` header-only: board model, sensor and link tables with Mbps and 4K fps labels, `Document`/`Editor`, 315-line `applyRequest` with read-back, LCS `lineChanges`, `stateJson`/`changesJson`/`jsonString`, FNV-1a `revisionOf`; plus about 195 App lines and about 730 WCP JS lines.
- Apertar way: no config.txt precedent beyond the fan block (`fanModeBlock`/`stripManagedFanBlock`/`detectManagedFanMode`, App:3042-3117@upstream-1.6.0). Header-only modules upstream are small (`src/hardware/ButtonActionList.hpp`, 121 lines, `PowerButtonGesture.hpp`@upstream-1.6.0); larger hardware logic is a .hpp/.cpp pair listed in `add_executable`. In-place edits that keep comments are upstream's own rule for its files.
- why it matters: the original developer must review and maintain a small text-editing framework for one card; most of the size serves the free-text editor and decoration, not the safe edits.
- rework: keep the in-place approach (BCT l.8-13 weighs it against Cinemate's fenced block; a managed block would still have to comment out the image's `[pi5]` sensor lines). Keep parse, readState, applyRequest with read-back for sensor/link/toggles/RP1/display. Drop `lineChanges`, `displayDiffers`, `textProblem`, `managed` (with F3), `mbpsPerLane`/`fps4k`/`linkOptionLabel` (Hz list only); move JSON to App (F6). Make it `src/hardware/BootConfig.{hpp,cpp}` with the .cpp in CMakeLists.txt (decide together with the port's `HardwareConfigText.hpp`, 1141 lines, same shape). Target about 600-700 lines.
- effort: L
- deliberate: yes (BCT header l.2-28; KB architecture/config.md 7.1; working/handoff-boot-config.md).

### Boot-config-F5 [mismatch, major] `include camera-selection.txt` is invisible; the image's sensor mechanism is bypassed
- where: src/hardware/BootConfigText.hpp:289-293@cinemate-port ; src/hardware/BootConfigText.hpp:616-622@cinemate-port ; tools/boot_config_test.cpp:56@cinemate-port
- port way: `lineFrom` returns no key for a line without `=`, so `include camera-selection.txt` never counts; the card writes `dtoverlay=` sensor lines in config.txt itself. The fixture keeps the image comment 'remove the "include camera-selection.txt" line' with the include already removed.
- Apertar way: "Apertar's camera-selection file is authoritative ..." `scanBinaryFileForSensorToken("/boot/firmware/camera-selection.txt", 4096)` (Apertar-UI src/DeviceInfoBridge.cpp:213-215@upstream-1.6.0).
- why it matters: probable on a fresh image: the card shows no sensor; saving IMX585 uncomments a second overlay while the included file still loads one; read-back passes because it does not see the include.
- rework: in readState, an applying uncommented `include` line makes the camera rows read-only with one sentence ("config.txt includes camera-selection.txt: the sensor comes from that file."), same shape as `state.problem`. Settle with `grep -n '^include' /boot/firmware/config.txt` on a fresh Apertar-Beta 1.6.0 image. Same as sweep-board-support X-3.
- effort: S
- deliberate: unknown (no KB note weighs the include).

### Boot-config-F6 [mismatch, minor] Engine in src/hardware writes wire JSON with its own jsonString
- where: src/hardware/BootConfigText.hpp:1225-1340@cinemate-port ; src/ApertarCoreApp.cpp:3676-3706@cinemate-port
- port way: `jsonString` re-implements `escapeJson`; `stateJson` nests `board{}`, `cameras{}`, `toggles{}`, `rp1{}`, `display{overlays[],lines[]}`, `candidates{}`, `sensors[{link{options[]}}]`, `displays[]`, `warnings[]`, `managed[]`; App adds `drm[]` and `changes[]`.
- Apertar way: replies built in App with `std::ostringstream` and `escapeJson` (declared src/ipc/ControlProtocol.hpp:25, used App:108-128@upstream-1.6.0); no upstream `src/hardware/` file writes reply JSON; one nested object per topic is precedented (`imuStatusBody`, App:130@upstream-1.6.0), arrays appear in web-route bodies (`/api/media`).
- why it matters: a second JSON writer, and wire knowledge inside a hardware module.
- rework: move serialisation into App as `bootConfigBody(state)` using `escapeJson`; one `"boot_config":{...}` object, scalars plus the fixed option lists; labels on the page; `drm[]` -> count of connected DPI connectors. rev-App-1 F9.
- effort: M
- deliberate: no

### Boot-config-F7 [removed-upstream-behaviour, minor] Touch UI fan mode now fails when Core is not running
- where: Apertar-UI src/SystemActionBridge.cpp:66-97@cinemate-port (commit 41ff827) ; :406-412@cinemate-port
- port way: UI `41ff827` deletes `fanModeBlock`, `stripManagedFanBlock` and the `install` write; sends `set_fan_mode` over a private `QLocalSocket` (id 42002, 8 s); socket down -> "Connect to Apertar Core before changing the fan mode."
- Apertar way: each process carries its own fan writer (App:3042-3165 vs Apertar-UI src/SystemActionBridge.cpp:64-100@upstream-1.6.0); the touch UI changes the fan mode without Core.
- why it matters: behaviour change the original developer must know of; justified only while Core edits other lines of the same file (a UI write outside Core's lock can overwrite a Boot Config save).
- rework: keep if the owner accepts the dependency; document it in the handoff. Client shape follows upstream's synchronous QLocalSocket bridges (MediaStatusBridge.cpp:20-42@upstream-1.6.0). Verify on the Pi (commit says "build only").
- effort: S
- deliberate: yes (commit body: "a fan change could race a Boot Config save").

### Boot-config-F8 [bug, nit] Helper refuses a config.txt without [pi5]/[pi4]/[all], fan mode included
- where: scripts/apertar-boot-config:51-54@cinemate-port ; src/ApertarCoreApp.cpp:3586-3592@cinemate-port ; src/ApertarCoreApp.cpp:3643@cinemate-port
- port way: helper exits 2 without one of the three headers; Core returns its text and does not fall through; `applyFanMode` uses this writer.
- Apertar way: `applyFanMode` writes any non-empty config.txt (App:3127-3165@upstream-1.6.0).
- why it matters: a regression on paper only: every Raspberry Pi OS / Apertar config.txt has `[all]`.
- rework: goes away with F2. If the helper stays, drop the section check. rev-App-1 F12, sweep-board-support X-11.
- effort: S
- deliberate: no

### Boot-config-F9 [pi-compat, minor] Board model: unknown board read as Pi 5, Zero 2 W counted as pi3, link list trimmed only on Pi 4
- where: src/hardware/BootConfigText.hpp:91-96@cinemate-port ; src/hardware/BootConfigText.hpp:114-116@cinemate-port ; src/hardware/BootConfigText.hpp:182-188@cinemate-port ; src/ApertarCoreApp.cpp:3653-3657@cinemate-port
- port way: `if (!board.detected) board.family = "pi5";`; family `pi3` for every bcm2837/2710, so `[pi3]` lines count on a Zero 2 W; `linkOptionsFor` trims only for `pi4`, a Pi 3 gets the Pi 5 list.
- Apertar way: `pipelineFromCompatible` returns `Unknown` for an unknown board (src/camera/DefaultTuningSelection.hpp:18-31@upstream-1.6.0).
- why it matters: wrong section edited, or a link rate the stock driver may refuse, giving no camera after reboot (probable; firmware filter docs and kernel source not here).
- rework: unknown board -> `editable=false` with a sentence (Pi 5 reading only for the test path); `[pi3]` not applying on Zero 2 W; link list offered only for the pi5 family, the default rate otherwise. sweep-board-support X-4, X-6.
- effort: S
- deliberate: no

### Boot-config-F10 [duplication, minor] Two config.txt readers with two filter rules; second boolean parser
- where: src/ApertarCoreApp.cpp:4976@cinemate-port ; src/hardware/HardwareConfigText.hpp:1037-1070@cinemate-port ; src/hardware/BootConfigText.hpp:248-253@cinemate-port ; src/ApertarCoreApp.cpp:3709-3718@cinemate-port
- port way: Controls validator uses `hwconf::parseConfigTxt` (applies `[all]`/`[pi5]` only); `bootconf::isDpiOverlay` copies its name rule ("Same rule as HardwareConfigText's parseConfigTxt") but uses board-aware filters. `boolFieldValue` accepts on/yes/off/no and returns a tri-state.
- Apertar way: upstream reads each file one way; booleans use `== "true" || == "1"` (App:9486@upstream-1.6.0).
- why it matters: on a Pi 4 the Controls check and the Boot Config card give different DPI answers for the same file.
- rework: Controls validator takes the DPI lines from `bootconf::readState(...)` with the detected board; delete the DPI part of `parseConfigTxt`; `boolFieldValue` -> the upstream test.
- effort: S
- deliberate: no

### Boot-config-F11 [bug, minor] Sensor list lacks IMX283 although the port supports it
- where: src/hardware/BootConfigText.hpp:151-171@cinemate-port
- port way: comment "The sensors Core has handling for (CameraController detectSensorFamily: imx577, imx477, imx294, imx585)"; no imx283 entry.
- Apertar way: hand-copied option lists must follow the sensor support; port `detectSensorFamily` returns `Imx283` (src/camera/CameraController.cpp:2569-2570@cinemate-port); the imx283 driver ships `imx283-overlay.dts`.
- why it matters: failing input: `dtoverlay=imx283,cam0`; the card shows an unlisted sensor and cannot switch to IMX585 and back.
- rework: add `{"imx283","imx283","IMX283",false,0,0,{}}`; fix the comment.
- effort: S
- deliberate: no

### Boot-config-F12 [mismatch, minor] Permission error carries install commands; wrong advice when the helper exists without sudoers
- where: src/ApertarCoreApp.cpp:3602-3608@cinemate-port
- port way: "Writing config.txt needs root. Install the helper: sudo install -m 0755 ... then sudo install -m 0440 ...". Helper installed but sudoers missing: sudo refuses without an `apertar-boot-config:` line, the `install` fallback fails on "password", same "Install the helper" advice.
- Apertar way: "Changing the fan mode needs sudo permission." (App:3164@upstream-1.6.0); install steps live in README. Field names in socket errors are upstream style ("set_fan_mode requires value.", App:10571@upstream-1.6.0), so those stay.
- why it matters: the operator sees shell commands; the advice is wrong in the half-installed case.
- rework: after F2: "Writing config.txt needs sudo permission." rev-App-1 F8.
- effort: S
- deliberate: no

### Boot-config-F13 [slop, minor] Header essay with Cinemate history, section banners, per-field comments, non-ASCII label glyphs, sh-style helper
- where: src/hardware/BootConfigText.hpp:2-28@cinemate-port ; src/hardware/BootConfigText.hpp:42@cinemate-port ; src/hardware/BootConfigText.hpp:151-153@cinemate-port ; src/hardware/BootConfigText.hpp:197-205@cinemate-port ; src/ApertarCoreApp.cpp:3651@cinemate-port ; tools/boot_config_test.cpp:18@cinemate-port ; scripts/apertar-boot-config:1@cinemate-port
- port way: "Ported from Cinemate's settings-editor config.txt tab (cinemate src/module/app/boot_config.py)"; "Cinemate's resources/sensors.json: the will127534 IMX585 driver table"; 8 `// ----` banners in BCT, 1 in App; trailing comment on nearly every field; labels with U+00B7 and U+2014; helper `#!/bin/sh`, `[ ]`, `set -u`.
- Apertar way: rare one-line hazard comments, no other projects' history, no banners in App; `#!/bin/bash` + `set -euo pipefail` (scripts/start-apertar-core.sh@upstream-1.6.0); upstream App has 2 non-ASCII lines (U+2022, App:2366@upstream-1.6.0).
- why it matters: reads as ported Cinemate code in its own documentation register.
- rework: header to two lines; delete banners and Cinemate references; keep the hazard comment at BCT:950; ASCII labels; helper removed with F2.
- effort: S
- deliberate: no

### Boot-config-F14 [new-ground, minor] Host tests for engine and helper
- where: tools/boot_config_test.cpp:1-427@cinemate-port ; tools/boot_config_helper_test.sh:1-33@cinemate-port
- port way: plain g++ test with the dev Pi's file as fixture; sh test of the helper on a scratch copy. Not in CMake.
- Apertar way: upstream Core has no `tools/` dir, no tests, no test target.
- why it matters: new ground; acceptable only as an owner decision for the port's `tools/` as a whole (15 `*_test.cpp`).
- rework: keep the C++ test outside the build if `tools/*_test.cpp` stays for the port; drop the helper test with F2.
- effort: S
- deliberate: yes (commits `f19b245`, `dda1713`; KB 7.1 lists both tests).

### Boot-config-F15 [slop, nit] README lists socket commands; commits authored Claude with a claude/* merge
- where: README.md:211@cinemate-port ; git f19b245 dda1713 2955ef8 8a56545 afa00e8 496817f 4581a69@cinemate-port
- port way: README ends with a list of socket commands and fields; six commits authored "Claude"; `4581a69` merges `claude/cool-volta-y7fiw7`.
- Apertar way: upstream README stops at CLI launch flags; linear history, no `claude/*` merges.
- why it matters: commit and README hygiene for the merge.
- rework: drop the socket-command paragraph; linearise and re-author in the commit-clarity step.
- effort: S
- deliberate: no
