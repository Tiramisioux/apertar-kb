# C8: code style, comments, documentation and commits of the original developer

Scope: Apertar-Studio 1.6.0 only (`/home/user/wt/core-upstream` = `upstream-1.6.0` `35dbe67`,
`/home/user/wt/ui-upstream` = `upstream-1.6.0` `43888e5`). The port appears only in section 9, as contrast.
All line references are `@upstream-1.6.0` unless marked otherwise. All claims **confirmed** (read or counted
in code) unless labelled.

Sample: 43 files measured or read. Core: `ApertarCoreApp.cpp/.hpp`, `CameraController.cpp/.hpp`,
`WebControlPage.cpp`, `main.cpp`, `ipc/ControlServer.cpp`, `ipc/ControlProtocol.cpp`, `hardware/GpioInput.cpp/.hpp`,
`hardware/TriggerOutput.cpp`, `hardware/Mpu6050RecordingSession.cpp/.hpp`, `util/SettingsFile.hpp`,
`cdng/CdngEncoder.cpp`, `prores/ProresEncoder.cpp/.hpp`, `audio/AudioRecordingSession.cpp`,
`color/ColorProfileConfig.cpp`, `lossydng/LossyJpeg12.cpp`, `lossydng/LossyDngEncoder.hpp`, `include/apertar/core/Types.hpp`,
`web/WebServer.cpp`, `scripts/start-apertar-core.sh`, `README.md`, `CMakeLists.txt`. UI: `main.cpp`,
`SettingsBridge.cpp/.hpp`, `ApertarControlBridge.cpp/.hpp`, `WifiBridge.cpp/.hpp`, `dngdecoder.cpp`, `cliplistmodel.cpp`,
`playbackcontroller.cpp`, `CfeAutomounter.cpp`, `qml/Main.qml`, `CameraPage.qml`, `SettingsPage.qml`, `RecordButton.qml`,
`StatusChip.qml`, `ClipBrowserPage.qml`, `run_pi_direct.sh`, `sync_pi_runtime.sh`, `wait_for_ui_core_start.sh`,
`finish_plymouth_handoff.sh`, `README.md`, `third_party/liblj92/README.apertar.md`, `CMakeLists.txt`.
Whole-tree counts by `grep` over all `git ls-files` sources (Core 84 C++ files; UI 69 C++ files, 33 QML files),
excluding `build/`, `mesa-minimal/`, `third_party/`.

---

## 1. Layout: indentation, braces, line length

| Measure | Core | UI C++ | QML | Shell |
| --- | --- | --- | --- | --- |
| Indent | 4 spaces, 0 tab lines in 19 files | 4 spaces, 0 tabs | 4 spaces; 52 tab lines in `CameraPage.qml`, 79 in `SettingsPage.qml` (stray) | 4 spaces |
| Function body brace | own line: 1117 vs 16 same-line (all `.cpp` minus WCP) | own line 1064 vs 1 | n/a (`{` at end of line, 0 lone `{`) | `name() {` same line |
| Class brace | `class X {` same line: 58 vs 0 | `class X : public QObject` then `{` own line: 29 vs 6 | n/a | n/a |
| Control flow | `if (...) {` same line; unbraced one-statement bodies are the majority: 2524 unbraced vs 1986 braced (Core), 1489 vs 1172 (UI) | same | same in JS | `if [[ ]]; then` |
| `} else` | 325 `} else` vs 207 `else` on own line after unbraced body | | | |
| `&` / `*` binding | to the name: `const std::string &name` 868 vs 0 | 924 vs 0 | | |
| Line length | no hard limit. App code mostly under 100; `CameraController.cpp` 309 lines > 100, max 186. `ApertarCoreApp.cpp:9216` is one 2400-char line (the `"commands":[...]` list) | `SettingsBridge.hpp` 53 lines > 100 (one `Q_PROPERTY` per line) | `SettingsPage.qml` 657 lines > 100, max 369 | max 132 |
| Formatter config | none: no `.clang-format`, no `.editorconfig` in either repo (`ls -a` of both roots) | | | |

Evidence:
- `src/ipc/ControlServer.cpp:15-36@upstream-1.6.0` function brace on own line, unbraced `if` bodies, `while (...) {`.
- `src/camera/CameraController.hpp:17@upstream-1.6.0` `class CameraController {`.
- `src/SettingsBridge.hpp:13-14@upstream-1.6.0` `class SettingsBridge : public QObject` / `{`.

Switch: `case` at the same indent as `switch`, one-line cases aligned: `src/prores/ProresEncoder.cpp:102-107`.

## 2. Naming

| Thing | Core | UI | Evidence |
| --- | --- | --- | --- |
| Types | PascalCase | PascalCase | `CameraController.hpp:17`, `SettingsBridge.hpp:13` |
| Functions / methods | camelCase, verb first: `setIso`, `startRecording`, `persistSettingsLocked` | camelCase | `CameraController.hpp:39-82` |
| Must-hold-mutex helpers | suffix `Locked` | n/a | `CameraController.hpp:92,96` `applySettingsLocked`, `setErrorLocked` |
| Members | trailing underscore, 30 of 52 headers declare them, 0 `m_` anywhere in Core | `m_` prefix, 27 of 34 headers; 0 trailing-underscore members. The 7 without are plain-struct/C-API headers | Core `ApertarCoreApp.hpp:110-113` `options_`, `camera_`; `CameraController.hpp:107,119` `mutex_`, `lastError_`. UI `SettingsBridge.hpp:489-491` `m_presetStatusText`; `ApertarControlBridge.hpp:325` |
| Constants | `kCamelCase` (128 `constexpr k...`) ; 11 plain camelCase local `constexpr`; 0 `UPPER_CASE` | `kCamelCase` 116 vs 1 | `ApertarCoreApp.cpp:60-64` `kWebPreviewMaxWidth` |
| Enums | `enum class` (25) with PascalCase values | | `ProresEncoder.cpp:102-105` `Profile::Proxy` |
| Files | `PascalCase.hpp/.cpp`, path mirrors module (`hardware/`, `camera/`, `cdng/`, `prores/`). C codec files `.h` (`lossydng/LossyJpeg12.h`, `fastent.h`) | `PascalCase.hpp/.cpp` for bridges; older lowercase `.h/.cpp` (`cliplistmodel`, `dngdecoder`, `playbackcontroller`, `rawframe`, `tiffhelper`, `cdngimageprovider`) | `ls src` in both |
| QML files | n/a | PascalCase component per file, `id: root` on the root item | `StatusChip.qml:3-4`; `grep id:` gives `root` first in each file |
| Socket commands, JSON keys, conf keys | `snake_case`: `set_iso`, `record_start`, `cdng_compression=` | | `ApertarCoreApp.cpp:9216`; `CameraController.cpp:760-777` |
| Env knobs | `APERTAR_<AREA>_<NAME>`: 43 distinct in Core, 16 in UI | | `LossyDngEncoder.cpp:100` `"APERTAR_LOSSYDNG_WRITER_BYTES"` |
| Shell | `UPPER_CASE` variables with `${APERTAR_X:-default}`, `snake_case` functions | | `start-apertar-core.sh:4-6`; `wait_for_ui_core_start.sh:13` `monotonic_milliseconds()` |
| Legacy names kept | QSettings org `"CinePi"`, `~/.config/CinePi/UI.conf` | `m_settings("CinePi", "UI")` | `ApertarCoreApp.cpp:344-347`; `SettingsBridge.cpp:287`; `ApertarControlBridge.cpp:118`. Never renamed: renaming would orphan users' settings |

## 3. Language idioms

| Idiom | Core count | UI count | Notes |
| --- | --- | --- | --- |
| Standard | C++20 (`CMakeLists.txt:21`) | C++17 (`CMakeLists.txt:4`) | |
| `auto` / `const auto` | 917 / 714 | 202 lines in `.cpp` | `const auto` dominates: `auto` is mostly bound to `const`. `for (const auto &[format, profile] : ...)` `CameraController.cpp:785` |
| `std::optional` | 86 | 10 | parse helpers return `std::optional<int>`: `GpioInput.cpp:78,209,266`; state `CameraController.hpp:117` |
| Lambdas | 98 `[&]`/`[this]` captures | 70 | local helper lambdas named `const auto addTarget = [&](...)`: `ApertarCoreApp.cpp:6076,6536` |
| `std::function` callbacks | 38 | | `CameraController.hpp:19-21` `using EventCallback = std::function<...>` |
| Smart pointers | `unique_ptr` 18, `shared_ptr` 13, raw `new` 34 | Qt parent ownership | pimpl `std::unique_ptr<CameraSession> session_` `CameraController.hpp:133` |
| JSON | hand-written `std::ostringstream` + `escapeJson`; hand-rolled parser `ipc/ControlProtocol.cpp`; no JSON library (`grep nlohmann|rapidjson|boost` = 0) | `QJsonDocument` | `ApertarCoreApp.cpp:108-128` `okReply` / `errorReply` |
| `std::format` | 0 | | uses `ostringstream` (80) and `snprintf` (8) |
| `assert` | 2 | | not used for runtime checks |
| `std::regex` | present, `static const` | | `ApertarCoreApp.cpp:2217` |

### Namespaces and file shape
- Core: every file in `namespace apertar {` (78 of 84; the 6 without are the C codec and the `extern "C"` plugin API
  files). Closing `} // namespace apertar` (55) or `}  // namespace apertar` (8, ProRes files).
- File-local helpers go in an anonymous namespace inside `apertar`: 29 Core files. `ApertarCoreApp.cpp:57-58` opens
  it and `:6779` closes it, so 6 700 lines of free helpers precede the class methods. Same shape:
  `ControlServer.cpp:12-80`, `ProresEncoder.cpp:38-107`.
- UI: no project namespace (3 files with a named namespace); anonymous namespace for helpers in 26 of 69 files.
- `#pragma once` in every header: Core 52/52, UI 34/34, 0 `#ifndef` guards.
- Header-only: 20 Core headers have no `.cpp` (small utilities: `util/SettingsFile.hpp` 119 lines,
  `util/AtomicStillFile.hpp`, `hardware/ButtonActionList.hpp`, `cdng/IfdBuilder.hpp`, but also
  `color/StillSrgbProfile.hpp` 741 lines and `video/NativeV4l2H264Encoder.hpp` 382 lines). Rule: a class with
  state and a thread gets `.hpp` + `.cpp`; free helpers shared by two translation units go header-only with
  `inline`. UI standalone helper executables are a single `.cpp` without header: `CfeAutomounter.cpp`,
  `NetworkHelper.cpp`, `StandbyLowPower.cpp`, `StandbyUsbPower.cpp` (`ui CMakeLists.txt:149-156`).
- No per-file license or copyright header in any source file (`grep Copyright|SPDX` = 0, both repos). One LICENSE
  per repo (GPL text, 339 lines).

### Include order (Core, usually)
1. own header (`"hardware/GpioInput.hpp"`), then project headers by path from `src/` or `<apertar/core/...>`;
2. blank line; C++ standard headers, roughly alphabetical;
3. blank line; POSIX / Linux headers (`<fcntl.h>`, `<linux/gpio.h>`, `<sys/ioctl.h>`, `<unistd.h>`);
4. `extern "C" {` block for libav when needed.

Evidence: `GpioInput.cpp:1-22`, `TriggerOutput.cpp:1-21`, `WebServer.cpp:1-18`, `ProresEncoder.cpp:1-35`.
Exceptions: `ApertarCoreApp.cpp:2-40` mixes `<ifaddrs.h>`, `<net/if.h>` into the std block; `ProresEncoder.cpp:6-27`
is not alphabetical. UI is looser: Qt and std mixed (`SettingsBridge.cpp:1-15`); `ui main.cpp:1-31` puts Qt
first and project headers after.

## 4. Error handling

| Layer | Shape | Evidence |
| --- | --- | --- |
| Low-level file and codec code | throws `std::system_error(errno, std::generic_category(), "Could not ...")` or `std::runtime_error("...")`. 157 `throw` in Core, concentrated in `cdng/` (45), `mlv/` (20), `color/` (32), `util/AtomicStillFile.hpp` (10) | `grep -c throw` per file |
| Hardware / service classes | `bool f(..., std::string *errorMessage)` (58) or `std::string *error` (163 total incl. errorMessage); pointer may be null, checked with `if (errorMessage)` | `GpioInput.hpp:80`, `GpioInput.cpp:534-535,549-550,572-573`; `Mpu6050RecordingSession.hpp:78-82,124-132`; `ApertarCoreApp.hpp:95,98` |
| CameraController | `bool setX(...)`; failure stored with `setErrorLocked`, read via `lastError()` | `CameraController.hpp:39-64,96,86` |
| Command plane | `okReply(id, body)` / `errorReply(id, message)`; exceptions caught at the boundary | `ApertarCoreApp.cpp:108,120`; `ControlServer.cpp:219-221` catches `std::exception` and `...` and logs |
| Plugin C ABI | exception turned into a C error buffer: `catch (const std::exception &e) { message(error, size, e.what()); return 0; }` | `prores/ProresPlugin.cpp:31,44,52` |
| UI | Qt: `bool` returns plus status text properties (`m_presetStatusText`, `m_presetStatusError`); 38 `throw` (decoders) | `SettingsBridge.hpp:299-300,490-491` |

Strength: **usually** (exceptions inside codecs/writers, bool + error string at every component boundary). No
`std::expected`, no error-code enums.

## 5. Logging

- Core: plain `std::cerr`, `'\n'` or `"\n"` (0 `std::endl` in Core), no logging library, no levels, no `syslog`
  (188 `std::cerr` lines; `std::cout` 4). Output goes to the journal via systemd.
- Prefix shapes, by count:

| Shape | Example | Evidence |
| --- | --- | --- |
| `ApertarCore: <call>() failed: <strerror>` (socket plumbing) | `"ApertarCore: bind() failed: "` | `ControlServer.cpp:107,114,124,131,201` |
| `ApertarCore <subject>: key=value key=value` (recording stats, one line per event) | `"ApertarCore recording clip: "` ... `" workers=" " queue="` | `CameraController.cpp:3353-3374`, `:3416`, `:3539` `"ApertarCore drop[queue-full]: frame="` |
| `ApertarCore could not <verb>: <path>` | `"ApertarCore could not persist camera settings: "` | `CameraController.cpp:790`; `ApertarCoreApp.cpp:1863` |
| `<Component> input enabled: chip=... ` / `<Component> input: <error>` (hardware classes name themselves, no `ApertarCore` prefix) | `"GPIO input enabled: chip="`, `"PCF8574 input: "`, `"NeoRotary4 input: "`, `"Grove analog input: "` | `GpioInput.cpp:337,344,618` and the three sibling inputs |
| `Hardware input <what> ignored: ...` with a full stop | `"Hardware input action ignored: unknown action '" << action << "'.\n"` | `ApertarCoreApp.cpp:8605,8637,8893,8954` |
| `Apertar standby: ...` / `Apertar low-power ...` | | `ApertarCoreApp.cpp:6810,6818,9156` |

- UI: `qWarning()` 30, `qInfo()` 30, `qDebug()` 0, `console.log` 0 in QML. Prefix `"Apertar <area>: "`:
  `"Apertar preview: ..."`, `"Apertar network: "`, `"Apertar LUT preview: "`, `"Apertar standby: HDMI blanked..."`.
- Shell: `printf 'Apertar <component>: <message>: %s\n' "$X" >&2; exit 1`
  (`sync_pi_runtime.sh:12-14`, `wait_for_ui_core_start.sh:7-9`), or `echo "ApertarCore binary not found ...: $CORE_BIN" >&2`
  (`start-apertar-core.sh:9-11`).
- Strength: **usually**. Exceptions: two Core prefixes coexist (`ApertarCore:` vs `ApertarCore ` vs `Apertar `), and the
  hardware inputs use their own component name. No debug-level chatter: logs are startup facts, per-take stat lines
  and failures.

## 6. Comments

### Density (comment lines per 1000 non-blank lines)

| File / area | per 1000 |
| --- | --- |
| `src/ApertarCoreApp.cpp` | 10.9 |
| `src/camera/CameraController.cpp` | 13.7 |
| `src/ipc/ControlServer.cpp` | 7.9 |
| `src/hardware/GpioInput.cpp` | 9.0 |
| `ui src/SettingsBridge.cpp` | 6.5 |
| `ui qml/SettingsPage.qml` | 0.1 (1 comment in 8 732 lines) |
| `ui qml/CameraPage.qml` | 9.6 |
| `src/web/WebControlPage.cpp` | 0.3 |
| Core by directory: ipc 7, web 7, include 7, cdng 10, mlv 10, audio 11, camera 13, color 16, hardware 19, video 28, util 31 | |
| **outliers**: `src/prores` 363, `src/lossydng` 213 | |
| Whole UI (C++ + QML) | 6.9 (314 / 45 829) |
| Whole Core excluding WCP | 53 (2133 / 40 266), of which prores + lossydng are 1644 |

Two registers, then.

**Register A, application code (all of Core outside prores/lossydng, all of UI):** sparse `//` one- or two-line
comments, present tense, about an invariant, a hazard or a hardware fact; never what the next line does.
Typical words: "never", "must", "must not", "only", "keep".
- `ControlServer.cpp:25` `// Never let a stalled preview client block camera event delivery.`
- `ApertarCoreApp.cpp:1543` `// Fixed executable and arguments only; never accept paths from WebUI/config.`
- `ApertarCoreApp.cpp:8103-8104` `// This runs on libcamera's completion thread. Camera stop/reconfigure holds` / `// the control mutex while waiting for that thread, so never query it here.`
- `CameraController.cpp:726` `// Retired locked gains must not survive as an invisible manual mode.`
- `CameraController.cpp:3084-3086` explains libcamera fork renames, with one concrete example.
- `CameraController.cpp:5663-5664`, `:6001-6002` (memory on VC4 boards), `:2952-2954`.

**Register B, codec modules (`prores/`, `lossydng/`):** long `/* ... */` blocks with `*` gutters, banner headings
(`/* ---- NAME THE FRAME THREADS ---- */`), CAPITALS for emphasis, measured numbers, and references to the
developer's own notes that are not in the repo: `ZEROCOPY-HOLD.md §5.3` (`ProresEncoder.cpp:69`),
`WRITER-THREAD.md` (`:1583`), `PRORES-FINDINGS.md` (`:1609`, `ProresEncoder.hpp:41,264`), `bench/dct_bench2.c`
(`LossyJpeg12.cpp:9`), a reference file `/media/RAW/BMD Example.dng` (`LossyJpeg12.cpp:4`). It narrates design
rationale ("deliberately NOT", "TWO GUARDS, both load-bearing", `ProresEncoder.cpp:77-83`) and occasionally
history ("It is no longer what we ENCODE with", `LossyJpeg12.cpp:19`; "0 restores the old open/write/close",
`LossyDngEncoder.cpp:324`). This register exists only in these two directories (6 files).

Other comment facts:
- Doc comments: 0 `///`, 0 `/**`, 0 `@brief` in either repo. Headers are uncommented (`Types.hpp`,
  `ApertarCoreApp.hpp`, `CameraController.hpp`, `SettingsBridge.hpp`, `GpioInput.hpp`: 0 comment lines each);
  exception `LossyDngEncoder.hpp:12-13`, `ProresEncoder.hpp`.
- TODO / FIXME / XXX / HACK: **0** in both repos (the only hits are `mkstemp` templates `SettingsFile.hpp:41`,
  `AtomicStillFile.hpp:36`). Strength **always** (`grep -rnE 'TODO|FIXME|XXX|HACK'` over src, qml, include,
  scripts, config, shell, CMake).
- Dead code: 0 `#if 0`, 0 commented-out statements (`grep` for `// foo(...);`, `// if `, `// return` in both repos).
  Strength **always**.
- No ticket, issue or version numbers in comments. `R3`/`R5` hits are enum values `LossyDngRatio::R3`
  (`LossyDngEncoder.hpp:16`). No external project or commit hashes in code comments; the only "CinePi" strings are
  legacy settings paths, and cinepi-raw / cinepi-gui are credited in the README only.
- Spelling: mixed British and American ("Colour" in README headings and `CameraController.cpp:6011`, "colour IDs"
  `ProresEncoder.cpp:686`; "color" in identifiers and most UI text; "optimised", "quantise" in lossydng).

## 7. User-facing strings

| Where | Style | Counted evidence |
| --- | --- | --- |
| Core `errorReply` messages | full sentence, sentence case, ends with a full stop: 191 of 196 literal messages; the 5 without end in `": "` + detail | `ApertarCoreApp.cpp:7565,7624,9179,9185,10820` |
| Missing-argument errors | `"<command> requires <field>."` with the snake_case command name | `"set_iso requires value."`, `"set_resolution requires width and height."` (about 40 such) |
| Busy refusals | imperative, tells the operator what to do first | `"Stop recording before deleting media."`; UI `SettingsPage.qml:3742` `"Stop recording or timelapse before calibration."` |
| Generic | one stock message reused | `"Could not update shared UI settings."` 36 times |
| QML `title:` | Title Case noun phrase, 49 of 49 | `SettingsPage.qml:2392` `"External Monitor"`, `:2657` `"Focus Peaking"` |
| QML `description:` | sentence-case fragment, usually no full stop (38 of 43) | `:2394` `"Send a clean preview feed to HDMI"`, `:2659` `"Highlight in-focus edges"` |
| Buttons / dialogs | Title Case, short: `"Cancel"` 14, `"OK"` 10, `"Apply"`, `"Format Media"`, `"Eject Media"`, `"Shutdown System?"` | grep counts |
| Status chips, HUD headers | ALL CAPS: `"REC"`, `"READY"`, `"WRITING"`, `"NO MEDIA"`, `"FRAME RATE"`, `"REMAINING"` | `StatusChip.qml:48-49` |
| Empty-state help | full sentences, concrete paths, ends with the action | `SettingsPage.qml:2528` `"No .cube LUTs found yet.\nAdd files to /home/pi/LUTs or media /LUTs, then tap Refresh."` |
| Translation | none: 0 `qsTr` in 33 QML files | |

## 8. Magic numbers and duplicated lists (the rough edges)

- QML: colours and sizes are literals in place, no theme singleton (`grep 'pragma Singleton'` = 0).
  `SettingsPage.qml` has 136 `"#rrggbb"` literals; `"#151515"` 38 times, `"#171717"` 37 across files.
  `StatusChip.qml:22-49` nests four-level ternaries of `fadedColor(0x8d, 0x0f, 0x0f, 0.66)`.
- Duplicated JS: 22 function names defined in both `CameraPage.qml` and `SettingsPage.qml` (for example
  `estimatedBatteryPercent` `CameraPage.qml:271` and `SettingsPage.qml:1529`), 11 shared by `CameraPage.qml` and
  `ExternalMonitorWindow.qml`.
- Duplicated lists: the aspect-ratio list (`"2.39:1"` etc.) 10 times in `CameraPage.qml`, 10 in `SettingsPage.qml`,
  1 in `ExternalMonitorWindow.qml`; the command list is one literal line (`ApertarCoreApp.cpp:9216`).
- Core: named `kConstants` at the top of the anonymous namespace for limits (`ApertarCoreApp.cpp:60-64`), but tuning
  numbers inline where they are used with a why-comment (`CameraController.cpp:3331-3338`).
- Giant files are normal: `ApertarCoreApp.cpp` 11 025, `WebControlPage.cpp` 11 618, `CameraController.cpp` 8 834,
  `SettingsPage.qml` 9 851, `CameraPage.qml` 4 160 lines.
- The UI repo commits its `build/` tree (551 tracked files incl. a stale `CinePiQtPreview_autogen`) and
  `mesa-minimal/`; there is no `.gitignore` in either repo.

These are the house style. A contribution that splits these files, adds a theme singleton or dedupes the lists
without being asked is a mismatch of its own kind.

## 9. Documentation

| Item | Core README (311 lines) | UI README (330 lines) |
| --- | --- | --- |
| Audience | camera builders and operators first | same |
| Headings | Title Case, some as questions: `## What Can It Do?` (:7), `## Which Raspberry Pi Can I Use?` (:60), `## Where Are Recordings Saved?` (:261) | `## At a Glance`, `## Camera Controls` ... |
| Tone | second person, plain, short sentences, honest limits: "A selectable frame rate is not a promise that every recording format or storage device can sustain it." (:20); "cannot prevent every kernel, driver, storage or power failure" (:299) | same |
| Shape | bullet list of capabilities, tables for formats (:24-29), fenced `text`/`ini`/`bash` blocks | same |
| For Developers | one short section: source-of-truth statement, ASCII box diagram, four `socat` examples, `GET /api/state` (:269-299) | 18 lines: diagram, DMA-BUF note, "Board and sensor restrictions must remain enforced in Core as well as reflected in the interface" (:307-324) |
| Closing | `## Recording Safely` bullets with **bold** UI words (:301-306), `## Credits` naming cinepi-raw (:308-311) | Credits naming cinepi-gui |
| Not documented | the socket command list, reply fields, `apertar-hardware.conf` keys beyond three examples (:169-173), the 43 `APERTAR_*` env knobs (0 mentions in Core README), internal architecture, the private `*.md` notes cited in code | the 16 UI env knobs except `-DAPERTAR_QML_AOT` |
| Vendored code | `third_party/liblj92/README.apertar.md:1-11`: source repo, exact commit, licence, why it is here, the one local fix | |

No `docs/` directory, no CHANGELOG, no CONTRIBUTING, no API reference in either repo.

## 10. Commits and releases of the original developer

Author on every commit: "Apertar Studio" (single identity).

Apertar-Studio UI (`git -C /home/user/apertar-studio/apertar-ui log`), 10 commits, all on `main`, 0 merges, 0 tags:

| sha | date | subject | size |
| --- | --- | --- | --- |
| 43888e5 | 2026-10-24 | Update README.md | 1 file +280 -113 |
| 8847105 | 2026-10-23 | Updated to version 1.6.0 | 666 files +1 454 585 -7 257 |
| 16b88ba | 2026-09-04 | Create LICENSE | 1 file |
| 1a34efc | 2026-04-26 | Update README.md | 1 file |
| 43fee74 | 2026-04-26 | Delete widthoptions_- | 1 file |
| 155ed1b | 2026-04-26 | Create FUNDING.yml | 1 file |
| 9f0e2d4 | 2026-04-26 | Update README.md | 1 file |
| f7a587a | 2026-04-26 | Add files via upload | 68 files +16 176 |
| ac2b412 | 2026-04-26 | Add files via upload | 100 files +14 805 |
| 665657c | 2026-04-26 | Initial commit | 1 file |

Apertar-Studio Core: one commit, `35dbe67 2026-10-24 1.6.0 Release`, 137 files +57 127, no body.

Findings:
- Subjects are GitHub web-UI defaults ("Update README.md", "Add files via upload", "Create LICENSE") or a release
  name. 9 of 10 UI commits have committer `GitHub` (web editor / upload). **always**.
- No bodies (0 of 11), no trailers (`Co-authored-by`, `Signed-off-by`: 0). **always**.
- History is linear, no branches, no merges, no tags.
- Releases are cut as one bulk drop of the whole tree ("Updated to version 1.6.0", "1.6.0 Release"), then a README
  rewrite the next day. Development history is not published; feature-level commits do not exist upstream.
- Consequence for reviewers: there is no upstream commit-message convention to match. The upstream form is the
  release drop. What the original developer will actually read is the diff and the README.

## 11. Contrast: the port's conventions (for reviewers only)

Core `origin/main..cinemate-port`: 187 commits, 10 merges (`Merge pull request #3 ... claude/adoring-euler-n8zi0j`,
`Merge imx585-modes: ...`), +36 905 insertions over 177 non-merge commits. UI: 39 commits.

| Trait | Port | Upstream |
| --- | --- | --- |
| Subject | `area: sentence` lower case, median 68 chars, max 149. Areas: web 60, camera 38, core 22, rec 12, media 10, drop-frames 5, hw 4, cdng 4, scripts, audio, `WebUI`, tools, playback, multi-area `rec, web, cdng`. UI: `ui:`, `qml:`, `drop-frames:` | "Update README.md", "1.6.0 Release" |
| Body | `Why:` 151, `What:` 144, `Tested:` 166 of 187 | none |
| Trailers | `Co-Authored-By: Claude Opus 5.5` 108, `Claude Sonnet 5.5` 67, `Claude Fable 5.1` 9 (184 of 187); `Claude-Session:` URL 21. UI 39 of 39 | none |
| Internal numbers | subjects with tutorial numbers: 21 (e.g. `... (T38, part 5)`); added Core code lines naming `T<nn>`: 44 (T34 x30, T31 x14, T47 x13 ...); UI 10 | none |
| KB / campaign refs | in messages ("kb working/dng-chain/V/PATCHES.md", "plan row 5", "V/H15"); 10 added Core lines cite `kb working/...` or `(kb ...)` | private `*.md` names only inside prores/lossydng comments |
| External project refs | 82 added Core lines name Cinemate/CineMate, some with Cinemate commit hashes (`Cinemate f01b6cd`, `Cinemate ffb61fd`) | credits in README only |
| Comment density in added code | Core 76 per 1000 (2109 / 27 632); UI 61 per 1000 (137 / 2229) | Core app code 7-31, UI 7 |
| Branch names | `claude/<adjective>-<name>-<id>` in merge subjects | `main` only |

Three full messages read: `d7dd337` (cdng part folders: Why with measured numbers and a KB path, What as one dense
paragraph naming files, commands and state keys, Tested "desk ... pi (apertar.local) build ... rc 0",
Opus trailer), `6ef0ddc` (SCHED_FIFO knob: Why cites "plan row 5", "V/H15"; Tested "Not run on the Pi"; Fable
trailer + `Claude-Session`), `766aba8` ("fixes from the review of the seven commits above", admits two commits carry
each other's hunks and that "the branch is not rewritten here").

Port code style itself (indent, braces, `_` members) follows upstream (0 `m_` members added to Core); the
differences are comments, commit metadata and internal references.

---

## 12. Style card (one page)

**C++ (Core and UI)**
1. 4 spaces, no tabs. Function body `{` on its own line; `if/for/while/switch (...) {` on the same line;
   one-statement bodies may go unbraced. `&`/`*` bind to the name.
2. Core class `class X {`; UI QObject class `class X : public QObject` then `{` on its own line.
3. Core members end in `_`; UI members start with `m_`. Never mix within a repo.
4. Types PascalCase, functions camelCase verb-first, constants `kCamelCase`, `enum class` with PascalCase values.
   A method that needs the mutex held ends in `Locked`.
5. Core: everything inside `namespace apertar {`, file-local helpers in `namespace {` ... `} // namespace`.
   UI: no project namespace, helpers in `namespace {`.
6. `#pragma once`. Own header first, project headers, blank, std, blank, POSIX.
7. Prefer `const auto`, `std::optional` for "maybe parsed", named `[&]` lambdas for local helpers.
   No new libraries for JSON or logging: Core JSON is `ostringstream` + `escapeJson`, replies through `okReply` / `errorReply`.
8. Errors: codec and file writers may throw `std::system_error` / `std::runtime_error`; anything a caller outside the
   module sees is `bool` + `std::string *errorMessage` (nullable) or `setErrorLocked` + `lastError()`.
9. Logs: `std::cerr << "ApertarCore <subject>: " << ... << '\n';` for Core-level events, `"<Component> input: "` in
   hardware classes, `key=value` pairs for stats on one line. UI: `qWarning()/qInfo() << "Apertar <area>: "`.
   No debug spam, no `std::endl`.
10. Settings / commands / JSON / conf keys `snake_case`; env knobs `APERTAR_<AREA>_<NAME>`.
11. No license header per file. No Doxygen. Headers uncommented.

**Comments**
12. Few. One or two lines, present tense, saying why or what must never happen ("never", "must not", "only").
13. Long rationale blocks only where the code is a codec or a measured performance trade-off, and then they state
    the measurement and the invariant, not who asked or when.
14. No TODO/FIXME, no commented-out code, no `#if 0`.

**QML**
15. One component per PascalCase file, `id: root`, `property` declarations first, `readonly property` for derived
    values, `function camelCase()` with `var`, no semicolons, colours and sizes as literals.
16. No `qsTr`. Titles Title Case; descriptions short sentence-case fragments without a full stop; status chips ALL CAPS;
    error and help text full sentences ending with what to do.

**Shell**
17. `#!/bin/bash`, `set -euo pipefail` (or `set -u` for gate scripts), `UPPER_CASE` vars defaulting from
    `${APERTAR_X:-...}`, `[[ ]]`, errors `printf 'Apertar <component>: ...: %s\n' "$X" >&2; exit 1`.

**Docs**
18. README is for the camera builder: Title Case headings, second person, honest limits, one short For Developers
    section. Vendored code gets a `README.apertar.md` with source commit, licence and local changes.

**Commits**
19. Upstream has no message convention beyond release drops. Give the original developer reviewable diffs and a
    README change; keep messages plain and self-contained.

## 13. What a contribution must NOT bring

| Do not bring | Why (evidence) |
| --- | --- |
| Tutorial / work-package numbers in code comments or user strings (`T33`, `T38 part 5`, `Q21`, `WP-585-9`) | 0 such numbers anywhere upstream (section 6). Port adds 44 Core + 10 UI lines |
| Citations of the contributor's KB, campaigns, plan rows (`kb working/dng-chain`, `V/H4`, `plan row 5`, "the NVMe campaign") | upstream cites only its own private notes, in codec files only; KB paths are meaningless and unreachable for the original developer |
| Cinemate commit hashes and "as Cinemate does" narration in comments | upstream code never names another project; credits live in README (`README.md:308-311`) |
| History narration ("previously", "the old X", "changed in the review", "for now") in application code | upstream app-code comments state invariants only (section 6 register A). Register B history notes stay in codecs |
| AI co-author trailers and `Claude-Session:` URLs | 0 trailers in 11 upstream commits; recommend dropping them from the merged history, unless the owner decides otherwise for attribution (owner's call, not a style rule) |
| `claude/<random>` branch names and merge commits of them | upstream history is linear, `main` only |
| Commit messages that cite reviews of other commits or admit misplaced hunks ("the split is not right") | fix the history instead; upstream publishes clean drops |
| TODO / FIXME / commented-out code | 0 upstream |
| Doxygen or long header comments on app classes | 0 upstream |
| A logging framework, JSON library, theme singleton, `qsTr`, or file splits / dedup of existing lists not asked for | upstream uses `std::cerr`, hand JSON, inline literals, giant files (section 8) |
| Renaming legacy `CinePi` settings paths | live user data (`ApertarCoreApp.cpp:344-347`) |
| README knob tables for every `APERTAR_*` env var | upstream documents 0 of its 43 Core knobs in README; put a knob in README only when an operator needs it |
| Comment density several times upstream's (port 76/1000 vs app code 7-31/1000) | trim to invariants |

## Recipe: write a change the Apertar way (style)

1. Put the code in the existing owner file (often a giant one); new module only for a new codec or hardware class,
   as `src/<area>/PascalCase.hpp/.cpp` inside `namespace apertar` (`src/hardware/GpioInput.hpp:1`, `.cpp:1-26`).
2. Helpers in the file's anonymous namespace (`ApertarCoreApp.cpp:58-6779`), constants as `kName` at its top (`:60-64`).
3. Members `name_` (Core, `CameraController.hpp:107-133`) or `m_name` (UI, `SettingsBridge.hpp:489-491`).
4. Boundary errors as `bool` + `std::string *errorMessage` (`GpioInput.cpp:534-535`); command errors as
   `errorReply(command.id, "<command> requires value.")` (`ApertarCoreApp.cpp:120`).
5. One log line per event, `std::cerr << "ApertarCore <subject>: " ... << '\n'` (`CameraController.cpp:790,3353`).
6. One or two comment lines only where an invariant is not obvious (`ControlServer.cpp:25`, `ApertarCoreApp.cpp:8103-8104`).
7. UI text: Title Case title, short description, full-sentence help (`SettingsPage.qml:2392-2394,2528`).
8. README: add the operator-visible fact to the matching user section (`README.md:157-177` style); no knob tables.
9. Commit: plain subject, no internal numbers, no AI trailers, linear history.

## Challenge

Challenger pass against `/home/user/wt/core-upstream` and `/home/user/wt/ui-upstream` (both `upstream-1.6.0`). All lines `@upstream-1.6.0`. Note: upstream `src/ApertarCoreApp.cpp` is 11 025 lines, `CameraController.cpp` 8 834, `WebControlPage.cpp` 11 618 (the 15 083 / 12 931 / 20 963 in BRIEF are the port sizes).

| Rule | Verdict | Counter-example / reason |
| --- | --- | --- |
| C8-S1 | holds as usually; name exceptions | Codec island `src/lossydng/` is K&R C style: `fastent.h:30 static inline int magcat_fast(int v) {`, `LossyJpeg12.cpp:99 lj12_ctx *lj12_ctx_create(void) {`. Stray tab-indented lines in UI: `src/Ina219Bridge.cpp:89-92` (235 lines), `src/DisplayConfigBridge.cpp` (229), `qml/SettingsPage.qml:4714` (79), `qml/CameraPage.qml` (52). Core app code has 0 tab-indented lines (grep `^\t`). UI anonymous namespace brace on own line: `src/Ina219Bridge.cpp:23-24`, `src/CfeAutomounter.cpp:36` (`namespace` newline `{`) |
| C8-S2 | holds (always), clarify scope | No `m_` in Core, no `name_` in UI (grep). Scope: private class members only. Plain structs use bare camelCase fields: `src/ipc/ControlProtocol.hpp:9-12` (`int id = -1; std::string name;`). UI lowercase legacy files also use `m_`: `src/cliplistmodel.h:83-86` |
| C8-S3 | holds as usually; add exceptions | `src/lossydng/LossyDngEncoder.cpp:327 std::getenv("QRAW_LOSSYDNG_ASYNCWRITE")` is the only env knob not `APERTAR_*` (other 43 are `APERTAR_*`). lossydng uses snake_case C functions (`LossyJpeg12.cpp:99,104,125`). Macros are UPPER_CASE: `src/audio/TimestampedAudioCapture.cpp:14,32,45`, `src/mlv/MlvEncoder.cpp:25 APERTAR_MLV_HAS_NEON` |
| C8-S4 | weaken: "every header uses #pragma once" is wrong as stated | Core `.h` codec headers use include guards: `src/lossydng/fastent.h:17-18 #ifndef FASTENT_H`, `src/lossydng/LossyJpeg12.h:20-21` (all 52 `.hpp` + all 7 UI `.h` use `#pragma once`). Core files outside `namespace apertar`: `src/main.cpp`, `src/lossydng/LossyJpeg12.cpp`, `src/prores/ProresPlugin.cpp`, `src/prores/ProresPluginApi.hpp`, `src/video/LibavH264EncoderPlugin.cpp`, `src/video/LibavH264PluginApi.hpp` (plugin C ABIs and codec). UI has named module namespaces for free-function groups: `src/VideoPlayback.hpp:13 namespace VideoPlayback {`, `src/StandbyLowPower.cpp:13 namespace lowPower {`, `src/StandbyUsbPower.cpp:16 namespace standbyUsb {` |
| C8-S5 | weaken to usually with looser wording | std vs POSIX split is not kept: `src/ApertarCoreApp.cpp:24 <ifaddrs.h>`, `:29 <net/if.h>` sorted among std headers; `src/audio/AudioRecordingSession.cpp:12 <fcntl.h>`, `:18-19 <sys/wait.h> <unistd.h>` mixed in; `src/audio/TimestampedAudioCapture.cpp:1-10` no blank line, unqualified project includes, `<alsa/asoundlib.h>` before `<algorithm>`. What holds: own header first, project headers next, blank line, system headers. UI variant: own header, blank, Qt headers, blank, std, blank, POSIX (`src/Ina219Bridge.cpp:1-21`) |
| C8-S6 | holds as usually | `std::error_code` appears only as the out-param of `std::filesystem` calls (`src/util/SettingsFile.hpp:38`, `src/ApertarCoreApp.cpp:317`, UI `src/CfeAutomounter.cpp:314`), never as a return type. 0 `std::expected`, 0 `enum class *Error/*Result/*Status` in Core. Throws concentrate in codecs/writers (CdngEncoder 29, MlvEncoder 20, ProresIspProfile 16, ColorProfileConfig 16, LosslessJpegEncoder 16) |
| C8-S7 | Core: holds (usually); UI: weaken | Core: 0 `std::endl`; one `std::fprintf(stderr, ...)` at `src/video/LibavH264EncoderPlugin.cpp:245` (plugin process); `std::cout` only in `src/main.cpp:29,122,124` (startup banner/help). Core prefixes not all `ApertarCore`: `"Invalid web port:"`, `"Hardware input mapping ignored:"`, `"Apertar standby:"`. UI: `src/CfeAutomounter.cpp` uses `std::cerr`/`std::cout` with `std::endl` (21 hits, e.g. `:249`, `:469`) and prefix `CFE automounter:`; `src/StandbyLowPower.cpp:116,142` bare `std::cout << "restored "`; `src/PreviewWindowRenderer.cpp:496,989,1254` `qWarning()` without `Apertar` prefix. 0 `qDebug`, 0 `qCritical` in UI |
| C8-S8 | holds as usually; add exceptions | 0 runs of 3+ `//` lines in `ApertarCoreApp.cpp`, `CameraController.cpp`, `GpioInput.cpp`, `ControlServer.cpp`, `SettingsBridge.cpp`, `SettingsPage.qml`, `CameraPage.qml` (awk scan). Exceptions: banner comments `src/PreviewWindowRenderer.cpp:805-866` (`// ------`, with emoji `// 🎬 HIGHLIGHT PRIORITY` at `:832`) and trailing what-comments `:835 // hard clip`; `qml/CameraPage.qml:2546-2547 // ===== // STATUS CHIP`; codec block comments (`src/lossydng/fastent.h:1-16`, `src/prores/*`); 3-line comment in `scripts/start-apertar-core.sh:13-15` |
| C8-S9 | holds (always) | Re-grepped: `\b(TODO|FIXME|XXX|HACK)\b` 0 hits in src/include/scripts/config/CMake (Core) and src/qml/scripts/*.sh/CMake (UI); `#if 0` 0; `///`, `/**`, `@brief` 0; commented-out-call pattern 0. Non-ASCII exists (`ApertarCoreApp.cpp:2366` `" • "` in a display string, `fastent.h` em dash, `PreviewWindowRenderer.cpp:832` emoji) but that is not covered by this rule |
| C8-S10 | holds as usually | 191/196 `errorReply` literals end in `.`; the other 5 are concatenations (`ApertarCoreApp.cpp:7565,7624,9179,9185,10820` `"... : " + detail`). Command-name messages start lowercase (`:9245 "set_iso requires value."`). Sentence-case labels exist: `qml/DisplayCalibrationPanel.qml:30 "Apply calibration"`, labels `"Clip mode"`, `"Still mode"`, `"No favorites yet"`. 5 of 43 `description:` literals end with `.` (e.g. `"Record IMU motion data and calibrate Gyroflow sync."`). `qsTr` 0 |
| C8-S11 | holds (always) for "do not refactor unasked"; nuance | Giant files and inline literals confirmed (0 `pragma Singleton`). But a list shared across QML files was once extracted to a `.pragma library` JS module: `qml/TimelapseIntervals.js:1`, imported by `CameraPage.qml:3`, `SettingsPage.qml:4`, `TimelapseIntervalDialog.qml:3`, `TimelapseIntervalPicker.qml:2`, listed at `CMakeLists.txt:25`. So: leave existing duplication alone; a new list shared by several QML files may follow this one precedent (see C8-M3) |
| C8-S12 | holds as usually; refine | Core README does carry one reference table: `README.md:248-257` "Launch Options" (6 CLI flags) and four `socat` command examples in For Developers (`:290-295`), not a full command list. UI README mentions one `APERTAR_*` (CMake option `-DAPERTAR_QML_AOT=ON`, `README.md:251`). Ceiling: CLI launch flags and a handful of examples; no env-knob or full command tables |
| C8-S13 | holds (once) | `third_party/` exists only in UI (`third_party/liblj92/{LICENSE,README.apertar.md,lj92.c,lj92.h}`). Core `src/lossydng/` is first-party-looking codec code with no provenance file and a reference to another implementation (`fastent.h:3 "Drop-in replacements for ... in src/lossy_jpeg12.c"`), so the rule applies to trees declared vendored only |
| C8-S14 | holds (always) for the history facts; nuance on subjects | UI log at `upstream-1.6.0`: 10 commits, all author `Apertar Studio`, subjects are GitHub web defaults (`Add files via upload`, `Update README.md`, `Create LICENSE`, `Create FUNDING.yml`, `Delete widthoptions_-`) plus `Updated to version 1.6.0`; 0 bodies. Core: `35dbe67 1.6.0 Release`, 0 body. So "release drops" plus README web edits; there is no message convention to imitate. Dropping AI trailers is the owner's decision (BRIEF), not an upstream rule |
| C8-S15 | weaken: printf prefix is UI-only | Core `scripts/start-apertar-core.sh:9` uses `echo "ApertarCore binary not found ..." >&2` (no `Apertar <component>:` printf). UI: all 4 scripts `#!/bin/bash`; `set -euo pipefail` in `run_pi_direct.sh:3`, `sync_pi_runtime.sh:3`; `set -u` in `finish_plymouth_handoff.sh:3`, `wait_for_ui_core_start.sh:3`; snake_case functions `run_pi_direct.sh:83-338`, `sync_pi_runtime.sh:41`; `[[ ]]` everywhere |

### Missed rules

| Id | Kind | Rule | Evidence |
| --- | --- | --- | --- |
| C8-M1 | structure | Codec islands (`src/lossydng/`, `src/prores/`) keep their own C-flavoured register: include guards, `/* */` block comments with long rationale, snake_case functions, K&R braces. Do not normalise them, and do not carry that register into app code | `src/lossydng/fastent.h:1-18,30`; `src/lossydng/LossyJpeg12.h:1-21`; `src/lossydng/LossyJpeg12.cpp:99-150`; block comments in `src/prores/ProresEncoder.cpp`, `ProresColor.cpp`, `ProresRepair.cpp` |
| C8-M2 | idiom | UI C++ classes exposed to QML are named `<Area>Bridge` in `PascalCase.cpp/.hpp`; the older playback group is lowercase `.h/.cpp` (`cliplistmodel`, `dngdecoder`, `playbackcontroller`, `rawframe`, `tiffhelper`, `cdngimageprovider`) and stays that way. New UI classes take the PascalCase `.hpp` form | `src/SettingsBridge.hpp`, `src/WifiBridge.hpp`, `src/Ina219Bridge.hpp`, `src/GyroConfigBridge.hpp` (15 `*Bridge` pairs in `src/`); legacy `src/cliplistmodel.h:1`, `CMakeLists.txt:110-127` |
| C8-M3 | structure | When a fixed list is needed by several QML files, put it in a `.pragma library` JS file under `qml/`, import it `as <Name>`, and list it in `CMakeLists.txt` | once: `qml/TimelapseIntervals.js:1-4`, imports at `qml/CameraPage.qml:3`, `qml/SettingsPage.qml:4`, `qml/TimelapseIntervalDialog.qml:3`, `qml/TimelapseIntervalPicker.qml:2`; `CMakeLists.txt:25` |
| C8-M4 | idiom | Plain public data structs in Core use bare camelCase fields with in-class defaults; the trailing underscore is only for private class state | `src/ipc/ControlProtocol.hpp:9-12` (`int id = -1; std::string name;`) vs `src/camera/CameraController.hpp:107-133` |
| C8-M5 | idiom | UI headers include Qt headers as their own group between the own header and std headers | `src/Ina219Bridge.cpp:1-21`; `src/VideoPlayback.hpp:1-10` |

## Final rules

All evidence `@upstream-1.6.0`; Core = `/home/user/wt/core-upstream`, UI = `/home/user/wt/ui-upstream`.

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| C8-S1 | idiom | Indent with 4 spaces; function-body brace on its own line; if/for/while/switch braces on the same line; unbraced one-statement bodies allowed | usually (exceptions: `src/lossydng/` K&R C; stray tabs in UI `Ina219Bridge.cpp:89`, `DisplayConfigBridge.cpp`, `SettingsPage.qml:4714`, `CameraPage.qml`) | Core `src/ipc/ControlServer.cpp:15-36`; UI `src/SettingsBridge.cpp` (1064 own-line vs 1 same-line); Core 1117 vs 16 | `void f() {` in app code, 2-space or tab indentation in new code |
| C8-S2 | idiom | Private class members: `name_` in Core, `m_name` in UI; never mix within a repo | always (grep: 0 `m_` in Core, 0 `name_` in UI) | Core `src/camera/CameraController.hpp:107-133`; UI `src/SettingsBridge.hpp:489-491`, `src/cliplistmodel.h:83-86` | `m_state` in a Core class, `state_` in a UI bridge |
| C8-S3 | idiom | Constants `kCamelCase`, types PascalCase, functions camelCase verb-first, `...Locked` for methods needing the held mutex; snake_case for commands, JSON and conf keys; env knobs `APERTAR_<AREA>_<NAME>`; macros UPPER_CASE | usually (exceptions: `QRAW_LOSSYDNG_ASYNCWRITE` at `src/lossydng/LossyDngEncoder.cpp:327`; snake_case C functions in `src/lossydng/`) | Core `src/ApertarCoreApp.cpp:60-64`; `src/camera/CameraController.hpp:92,96`; `src/camera/CameraController.cpp:760-777`; 43 `APERTAR_*` knobs | `MAX_WIDTH` constant, `setFpsInternal` instead of `...Locked`, `CINEMATE_*` or camelCase env var |
| C8-S4 | structure | Core app code lives in `namespace apertar` with file helpers in an anonymous namespace inside it; plugin C ABIs, `main.cpp` and codec C sit outside. UI has no project namespace: anonymous namespaces for helpers, named module namespaces for free-function groups. `.hpp` headers use `#pragma once`; C `.h` codec headers use include guards | usually (exceptions listed) | Core `src/ApertarCoreApp.cpp:57-58,6779`; `src/ipc/ControlServer.cpp:12-80`; outside: `src/main.cpp`, `src/prores/ProresPluginApi.hpp`, `src/video/LibavH264PluginApi.hpp`; guards `src/lossydng/fastent.h:17`, `LossyJpeg12.h:20`; UI `src/VideoPlayback.hpp:13`, `src/StandbyLowPower.cpp:13` | New Core class outside `namespace apertar`; `#ifndef` guard in a new `.hpp`; a `namespace apertar` added to UI |
| C8-S5 | idiom | Includes: own header first, then project headers, blank line, then system headers (std, POSIX, `extern "C"` libav). UI: own header, Qt group, std group, POSIX group | usually (std/POSIX split not kept in `src/ApertarCoreApp.cpp:24,29`, `src/audio/AudioRecordingSession.cpp:12,18`; `src/audio/TimestampedAudioCapture.cpp:1-10` unordered) | Core `src/hardware/GpioInput.cpp:1-22`, `src/web/WebServer.cpp:1-18`, `src/prores/ProresEncoder.cpp:1-35`, `src/hardware/Mpu6050RecordingSession.cpp:1-26`; UI `src/Ina219Bridge.cpp:1-21` | System headers before the own header; reorder-only churn in existing files |
| C8-S6 | idiom | Codecs and writers throw `std::runtime_error`/`std::system_error`; component boundaries return `bool` plus nullable `std::string *error`, or `setErrorLocked` + `lastError()`; commands reply `okReply`/`errorReply`. No `std::expected`, no error enums; `std::error_code` only as a `std::filesystem` out-param | usually | Core `src/hardware/GpioInput.cpp:534-535`; `src/hardware/Mpu6050RecordingSession.hpp:78-82`; `src/ApertarCoreApp.cpp:108,120`; throws in `src/cdng/CdngEncoder.cpp` (29), `src/mlv/MlvEncoder.cpp` (20); `src/util/SettingsFile.hpp:38` | `Result<T, Error>` type, `enum class GpioError`, exceptions escaping a command handler |
| C8-S7 | idiom | Core logs with `std::cerr << ... << '\n'` (never `std::endl`, no logging library), one line per event, `ApertarCore <subject>: ` or `<Component> input: ` prefix, key=value pairs. UI Qt code uses `qWarning()`/`qInfo()` (never `qDebug`) with `Apertar <area>: ` | Core usually (exceptions `src/main.cpp:122` cout banner, `src/video/LibavH264EncoderPlugin.cpp:245` fprintf, prefixes like `"Invalid web port:"`); UI usually (exceptions `src/CfeAutomounter.cpp:249,469` cerr/cout + `std::endl`, `src/StandbyLowPower.cpp:116`, `src/PreviewWindowRenderer.cpp:989` no prefix) | Core `src/ipc/ControlServer.cpp:107`; `src/camera/CameraController.cpp:3353-3374`; `src/hardware/GpioInput.cpp:344,618`; UI 30 `qWarning` + 30 `qInfo`, 0 `qDebug` | `spdlog`, `std::endl` in Core, multi-line log dumps, `qDebug()` in UI |
| C8-S8 | idiom | App code comments: one or two lines, present tense, an invariant or hazard (never/must/only), not narration of the next line | usually (exceptions: banners and `// hard clip` in `src/PreviewWindowRenderer.cpp:805-866`, `qml/CameraPage.qml:2546`; codec block comments, see C8-M1) | Core `src/ipc/ControlServer.cpp:25`; `src/ApertarCoreApp.cpp:8103-8104`; `src/camera/CameraController.cpp:726`; 0 runs of 3+ comment lines in the main app files | Paragraph comments, history narration, "Now we ..." comments |
| C8-S9 | intent | No TODO/FIXME/XXX/HACK, commented-out code, `#if 0`, Doxygen, ticket numbers or other projects' commit hashes in source | always (grep both trees: 0 hits apart from mkstemp `XXXXXX` templates) | Core `src/util/SettingsFile.hpp:41`, `src/util/AtomicStillFile.hpp:36` (only `XXXXXX` hits); `#if 0` 0; `///`/`/**`/`@brief` 0 | `// TODO(T33)`, `/** @brief */`, `// see cinemate abc1234` |
| C8-S10 | intent | Operator-facing errors are full sentences ending in `.` and say what to do; command errors start with the snake_case command name; settings titles and buttons Title Case, descriptions short sentence case usually without `.`, status chips ALL CAPS; no `qsTr` | usually (sentence-case labels `qml/DisplayCalibrationPanel.qml:30 "Apply calibration"`, `"Clip mode"`; 5/43 descriptions end in `.`) | Core `src/ApertarCoreApp.cpp` 191/196 `errorReply` end in `.`, `:9245`; UI `qml/SettingsPage.qml:2392-2394`; `qml/StatusChip.qml:48-49`; `qsTr` 0 | `"error: invalid value"`, `"failed"`, lowercase titles, `qsTr("...")` |
| C8-S11 | structure | Keep the rough edges: giant owner files, inline QML colour/size literals with no theme singleton, duplicated helpers and lists, hand-written JSON, legacy `CinePi` settings paths. Do not refactor unasked | always (no refactor precedent; one new shared list was extracted, see C8-M3) | UI `qml/CameraPage.qml:271` vs `qml/SettingsPage.qml:1529` duplicate `estimatedBatteryPercent`; Core `src/ApertarCoreApp.cpp:344-347,5228` `CinePi`, `:9216` command list; `pragma Singleton` 0; `nlohmann|rapidjson|boost` 0 | `Theme.qml` singleton, splitting `ApertarCoreApp.cpp`, JSON library, renaming `CinePi` paths |
| C8-S12 | intent | README is for the camera builder and operator: Title Case headings (some questions), second person, honest limits, one short For Developers section. Reference tables stop at CLI launch flags; no env-knob or full command tables | usually | Core `README.md:7,60,261` headings, `:248-257` Launch Options, `:269-301` For Developers with 4 socket examples, `:299` limits; UI `README.md:307-324`; 0 of 43 `APERTAR_*` env knobs in Core README | A table of every `APERTAR_*` knob or every socket command, developer-internal sections |
| C8-S13 | structure | Vendored code gets a `README.apertar.md` beside it: source repo, exact commit, licence, purpose, every local fix | once | UI `third_party/liblj92/README.apertar.md:1-11`; only `third_party/` tree in either repo | Copied code with no provenance file, or provenance in commit messages only |
| C8-S14 | intent | Upstream history is linear on `main`, single author, plain subjects (GitHub web defaults or `1.6.0 Release`), no bodies, no trailers, no tags. Merged work should be plain, self-contained and linear, without internal ticket numbers or `claude/*` merge commits; AI trailers are the owner's call | always (for the facts) | UI `git log upstream-1.6.0`: 10 commits, 0 merges, 0 bodies (`8847105 Updated to version 1.6.0`, `f7a587a Add files via upload`); Core `35dbe67 1.6.0 Release`, 0 body | Merge commits of `claude/...` branches, subjects with `T33`/`WP-585-9`, multi-paragraph bodies citing reviews |
| C8-S15 | idiom | Shell scripts: `#!/bin/bash`, `set -euo pipefail` (`set -u` for gate/handoff scripts), UPPER_CASE vars defaulting from `${APERTAR_X:-...}`, `[[ ]]`, snake_case functions, errors to stderr then `exit 1`. UI scripts print errors as `printf 'Apertar <component>: ...' >&2`; the Core script uses `echo "ApertarCore ..." >&2` | usually | Core `scripts/start-apertar-core.sh:1-11`; UI `sync_pi_runtime.sh:3-14`, `wait_for_ui_core_start.sh:3-13`, `run_pi_direct.sh:3,83-338`, `finish_plymouth_handoff.sh:3,10` | `#!/bin/sh`, no `set -u`, `[ ]` tests, camelCase functions, errors on stdout |
| C8-M1 | structure | Codec islands (`src/lossydng/`, `src/prores/`) keep their own C-flavoured register (include guards, block comments with rationale, snake_case, K&R). Do not normalise them; do not bring that register into app code | always (both codec dirs; app code has 0 block comments) | Core `src/lossydng/fastent.h:1-18,30`; `src/lossydng/LossyJpeg12.h:1-21`; `src/lossydng/LossyJpeg12.cpp:99-150`; block comments only in `src/lossydng/*`, `src/prores/*` | Reformatting `fastent.h`, or `/* ... */` essays in `CameraController.cpp` |
| C8-M2 | idiom | UI C++ classes exposed to QML are `<Area>Bridge` in `PascalCase.cpp/.hpp`; the lowercase playback group (`cliplistmodel.h` etc.) is legacy and stays as is | usually (exceptions: lowercase playback files, `CfeAutomounter`, `SleepManager`, `MlvReader`) | UI `src/SettingsBridge.hpp`, `src/WifiBridge.hpp`, `src/Ina219Bridge.hpp`, `src/GyroConfigBridge.hpp` (15 `*Bridge` pairs); legacy `src/cliplistmodel.h:1`, `CMakeLists.txt:110-127` | New `lensmanager.h`, or renaming `cliplistmodel.h` |
| C8-M3 | structure | A fixed list needed by several QML files goes in a `.pragma library` JS file under `qml/`, imported `as <Name>` and listed in `CMakeLists.txt` | once | UI `qml/TimelapseIntervals.js:1-4`; `qml/CameraPage.qml:3`, `qml/SettingsPage.qml:4`, `qml/TimelapseIntervalDialog.qml:3`, `qml/TimelapseIntervalPicker.qml:2`; `CMakeLists.txt:25` | A new C++ singleton or Theme module for a static list; copying a new list into 4 QML files |
| C8-M4 | idiom | Plain public data structs in Core use bare camelCase fields with in-class defaults; trailing `_` is only for private class state | usually | Core `src/ipc/ControlProtocol.hpp:9-12`; vs `src/camera/CameraController.hpp:107-133` | `struct Foo { int id_; }` or private `int count;` in a class |
| C8-M5 | idiom | UI sources group includes as own header, Qt headers, std headers, POSIX headers, blank line between groups | usually | UI `src/Ina219Bridge.cpp:1-21`; `src/VideoPlayback.hpp:1-10` | Qt and std headers interleaved in new UI files |
