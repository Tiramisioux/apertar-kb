# Review: unit App-3 (`src/ApertarCoreApp.cpp`, port lines 8408-10674)

Stage 2 of 3. Judges the slice against Apertar 1.6.0. Yardstick: `raw/conv-core-command-plane.md` (rule ids `C1-*`);
`apertar-conventions.md` does not exist yet.

| Item | Value |
| --- | --- |
| Diff | `/home/user/build/review/diffs/App.part03.diff`, all 1327 lines read |
| Port | `/home/user/Apertar-Core` @cinemate-port `01f170c` |
| Upstream | `/home/user/wt/core-upstream` @upstream-1.6.0 `35dbe67` |
| Inventory | `raw/inv-App-3.md` |
| Labels | every claim **confirmed** (read in code) unless marked |

## 1. Verdict in one table

| Id | Title | Category | Severity | Deliberate |
| --- | --- | --- | --- | --- |
| App-3-F1 | `POST /api/boot-config` is a second door for `set_boot_config`; it splices `"cmd"` into the body | mismatch | major | no |
| App-3-F2 | Downloads refused in Standby, timelapse, sound-only recording, speed test, pending writes | removed-upstream-behaviour | major | partly (take: yes; Standby: no) |
| App-3-F3 | `APERTAR_WEB_PREVIEW_RECORDING_FPS`: untested A/B env knob | slop | major | yes (as experiment) |
| App-3-F4 | Revision in a custom header plus `Origin` sniffing (`old_page`) | new-ground | minor | yes |
| App-3-F5 | Hold replies hand-built five times; reply shapes differ between sibling routes | mismatch | minor | no |
| App-3-F6 | Operator sentences carry internal hold tokens | mismatch | minor | no |
| App-3-F7 | Ticket numbers and history narration in comments | slop | minor | no |
| App-3-F8 | Yield window and clock are file-scope singletons, not App members | mismatch | minor | yes (header rebuilds) |
| App-3-F9 | Delete routes set the delete flag after the take check (window for a take during a delete) | bug | minor | no |
| App-3-F10 | `/api/buffer` `recording` means something else than `/api/state` `recording` | protocol | minor | no |
| App-3-F11 | State fragment helpers: two return a leading comma, names do not follow `*Body` | mismatch | nit | no |
| App-3-F12 | `"play_reason":""` constant, read by nobody | slop | nit | no |
| App-3-F13 | `normalizeHardwareAnalogTarget` is now a one-line wrapper | slop | nit | no |

## 2. Findings

### App-3-F1 `POST /api/boot-config` bypasses `/api/command` (mismatch, major)

| Side | Evidence |
| --- | --- |
| Port | `App:9170-9195@cinemate-port`: `payload.insert(brace + 1, empty ? "\"cmd\":\"set_boot_config\"" : "\"cmd\":\"set_boot_config\",");` then `parseControlCommand(payload)` then `bootConfigSet(parsed.command, revision, request.headers.count("origin") > 0)`. Same function the socket command calls: `App:14589` `if (command.name == "set_boot_config") return bootConfigSet(command, command.string("revision"), false).body;` |
| Upstream | `App:7637-7641@upstream-1.6.0` `if (request.method == "POST" && request.path == "/api/command") { ... response.body = handleWebCommand(request.body);`. The fan mode, the only upstream writer of `config.txt`, is a command (`set_fan_mode`) reached from the WebUI through `/api/command` (C1-S09, C1-S01, C1-N01) |
| Effect | Two doors, two behaviours: the HTTP door returns 409/400 statuses and an `old_page` refusal the socket door never gives (`browser` flag). The HTTP door runs outside `handleCommand` and `commandMutex_`; the socket door runs inside it. Rewriting JSON text by `find('{')` is a hack the original developer would refuse |
| Rework | Delete the POST route. WCP sends `{"cmd":"set_boot_config", ..., "revision":"<r>"}` to `/api/command` (the command already reads `revision` as a field). Drop the `browser` parameter of `bootConfigSet`. `GET /api/boot-config` may stay as the read twin of `GET /api/config`, or the WebUI calls `get_boot_config` the same way. `POST /api/boot-config/parse` stays: raw-body file work like `POST /api/presets/import` (`App:7392@upstream-1.6.0`) |
| Effort | S (Core) + S (WCP fetch call) |

### App-3-F2 Downloads refused far beyond "during a take" (removed-upstream-behaviour, major)

| Side | Evidence |
| --- | --- |
| Port | `App:8683-8690`, `App:8812-8819`: `if (const std::string hold = playbackHoldReason(); !hold.empty()) { ... 409`. `playbackHoldFor` (`src/playback/PlaybackHold.hpp`) returns a hold for recording, sound recording, timelapse, the 3 s yield window, pending writes, speed test, **Standby**, media not usable |
| Upstream | `App:7197@upstream-1.6.0` `GET /api/media/download` has no guard at all; `download-selected` `App:7318` likewise. Downloads work in Standby and during a take |
| Deliberate | Commit `a37a902`: "a ZIP or file download is a big read from the card a take writes to" - covers takes only. Standby, timelapse idle intervals and speed test are not named: side effect of reusing the playback hold |
| Why it matters | Standby is where an operator offloads clips from a sleeping camera. The port answers "Playback held: standby. Downloads wait." |
| Rework | Downloads ask a narrower question: one free function `downloadHoldReason()` (or `playbackHoldReason(false)` plus a filter) that holds for recording, sound recording, pending writes and the yield window only; Standby holds only when `standbyUsbPoweredOff_` is true. Keep the stream stop callback. Name the behaviour in README |
| Effort | S |

### App-3-F3 `APERTAR_WEB_PREVIEW_RECORDING_FPS` (slop, major)

| Side | Evidence |
| --- | --- |
| Port | `App:89-105`: `std::getenv("APERTAR_WEB_PREVIEW_RECORDING_FPS")`; comment "this is the A/B knob ... (kb working/dng-chain, V/H4)". Used `App:9778-9784`. Commit `fb557e9`: "Not run on the Pi: the two-take test ... decides whether the knob is needed" |
| Upstream | `App:62@upstream-1.6.0` `constexpr double kWebPreviewMaxFps = 30.0;`, `App:8105-8106` uses it. Core reads one env var, `APERTAR_HARDWARE_CONFIG` (`App:4254`); launch options are `Options` + `main` flags (C1-S24) |
| Also | State exposes env knobs to the UI: `media_trim_env_off` (`App:9549`), `clip_merge_env_off`, `frames_per_folder_env` (via `clipMergeStateJson` callers). The env vars themselves live in other units (`APERTAR_MEDIA_TRIM`, `APERTAR_CLIP_MERGE`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_MEDIA_REQUIRE_MOUNT`, `APERTAR_BOOT_CONFIG`, `APERTAR_PLAYBACK_WORKERS`) |
| Rework | Run the two-take test. If the knob is not needed, delete `webPreviewRecordingFps()` and the `rawTakeActive()` branch. If it is, make it a fixed lower rate during a raw take (no knob), or an `Options` field with a `--web-preview-recording-fps` flag, usage line and README row. Drop the `*_env_off` / `*_env` state members with their env vars (see `raw/sweep-knobs.md`) |
| Effort | S |

### App-3-F4 Revision header and `Origin` sniffing (new-ground, minor, simplify)

| Side | Evidence |
| --- | --- |
| Port | `App:8633-8641`: `request.headers.find("x-apertar-revision")`; `if (revisionHeader == request.headers.end() && request.headers.count("origin"))` -> 409 `"code":"old_page"`. Same in `bootConfigSet` (`App:3790-3791`) |
| Upstream | Route parameters travel in the query string (`queryParameterValue(request.query, "name")`, `App:7440@upstream-1.6.0`) or the path tail; no custom request header anywhere (5.7 of C1). Core and WebUI ship together, no version handshake (C1-N11) |
| Verdict | The revision check itself is worth keeping (stops a tab overwriting a newer file). The header and the Origin heuristic are foreign. `old_page` exists only for a tab opened before an update, which C1-N11 says is not a case Core handles |
| Rework | `POST /api/config?revision=<r>`; missing revision = last-writer-wins for every caller (as upstream), present and stale = 409 `stale`. Delete the `origin` branch here and in `bootConfigSet` |
| Deliberate | yes: commit `5395fa4` explains the stale-tab case |
| Effort | S (Core + one WCP fetch) |

### App-3-F5 Hold replies hand-built five times (mismatch, minor)

| Side | Evidence |
| --- | --- |
| Port | `App:8499` and `App:8529` (`/api/media/frame`), `App:8569` (`/api/media/file`), `App:8687`, `App:8816` (downloads): `"{\"ok\":false,\"error\":\"Playback held: " + hold + ".\",\"hold\":\"" + hold + "\"}"`. `/api/media/clip` 409 (`App:8460`) uses `errorReply` without `hold`. Busy: `"{\"ok\":false,\"busy\":true}"` (`App:8532`) has no `error` key. `/api/media/frame` 404 `"gone":true` hand-built (`App:8506`) |
| Upstream | C1-I06: replies only via `okReply` / `errorReply`; HTTP file routes reuse them with id -1 (`App:7188`, `App:7647@upstream-1.6.0`). "A reply built without the helpers ... an error without the error key" is the named violation |
| Rework | One free function `std::string playbackHoldReply(const std::string &hold)` returning `errorReplyBody(-1, holdSentence(hold), "\"hold\":\"" + hold + "\"")` (`errorReplyBody` already exists, `App:173`); call it from all six sites including `/api/media/clip`. Busy: `errorReplyBody(-1, "The viewer is busy. Try again.", "\"busy\":true")`. Gone: `errorReplyBody(-1, "This clip was removed.", "\"gone\":true")` |
| Effort | S |

### App-3-F6 Operator sentences with internal tokens (mismatch, minor)

| Side | Evidence |
| --- | --- |
| Port | `"Playback held: " + hold + ". Downloads wait."` shows `media_test`, `writing`, `standby`, `media` to the operator (`App:8687`, `App:8816`). `"Recording. Downloads wait until the take ends."` |
| Upstream | C1-I07, C1-N02: one sentence that says what to do; families "Stop <activity> before <action>." ("Stop recording before deleting media.", `App:7514@upstream-1.6.0`), "Wait for <thing> ..." ("Wait for the media speed test to finish first.", `App:9110`) |
| Rework | `holdSentence(hold)` next to F5's helper: recording -> "Stop recording before downloading media."; writing -> "Wait for the current capture to finish writing to media."; media_test -> "Wait for the media speed test to finish first."; standby -> "Wake the camera before ..."; media -> "Mount media first." |
| Effort | S |

### App-3-F7 Ticket numbers and narration in comments (slop, minor)

| Where (@cinemate-port) | Text |
| --- | --- |
| `App:8476` | `// T48: one picture of a cDNG clip ...` |
| `App:8551` | `// T51: a take's WAV ...` |
| `App:8663` | `wakeControlsWorker();   // T39: ...` |
| `App:9254` | `// T47: in a hold the list answers from the cache` |
| `App:9318` | `(T20 Step 4)` |
| `App:9362` | `// T47: the hold rule ...` |
| `App:10182`, `App:10469` | `// T34: the ladder picks the resolution` |
| `App:10482` | `(request 13)` |
| `App:89-92` | "(kb working/dng-chain, V/H4)" |
| `src/playback/PlaybackHold.hpp:3-25` | "design sketch v2 (not in any repository)", "critic M8", line numbers into `CameraController.cpp` and `ApertarCoreApp.cpp` |

Upstream C1-I14: 10 comment lines in 11 025, each a hazard or reason, no ticket numbers. Rework: delete the tags and
references; keep a sentence where it states a hazard (the hold-before-read rule, the completion-thread rule). Effort S.

### App-3-F8 Yield window as file-scope singletons (mismatch, minor)

| Side | Evidence |
| --- | --- |
| Port | `App:6335-6352`: `playbackNowMs()`, `playback::PlaybackYield &playbackYield() { static playback::PlaybackYield yield; ...}`, `bool playbackYieldActive()`. Comment: "File scope, so the header does not pull in the readers". Written by `handleCommand` and the media watcher, read by stream writers |
| Upstream | C1-S18: cross-thread flags are `std::atomic<T> name_{init};` members of App; C1-S19: parts receive `std::function` callbacks from App (`App:6783-6792@upstream-1.6.0`) |
| Rework | `#include "playback/PlaybackHold.hpp"` in `ApertarCoreApp.hpp` (header-only, `<atomic>` + `<cstdint>`, cheap) and add `playback::PlaybackYield playbackYield_;` next to the media group. Stream functions take `const std::function<bool()> &stop`; the routes pass `[this] { return playbackYield_.active(playbackNowMs()); }`. `clipFactsCache()` may stay a function-local static (C1-I19 precedent) |
| Effort | S-M |

### App-3-F9 Delete flag set after the take check (bug, minor)

`App:9016-9029@cinemate-port`: the route checks `camera_.isRecording() || ...` and `mediaWritesPending()`, then constructs
`MediaDeleteScope deleteScope(mediaDeleteActive_)`. `handleCommand` refuses `record_start` with "Deleting media. One moment."
(`App:12587`) only once the flag is set. Failing input: `record_start` (button or socket) arrives between `App:9016` and `App:9029`
(probable: a window of microseconds plus the `mediaWritesPending()` call, which waits on the camera mutex) -> the take starts and the
delete runs during it. Same at `App:9099-9112`. Upstream had no flag (same race, `App:7514@upstream-1.6.0`), so this is a hole in the
new guarantee, not a regression. Rework: construct the scope first, then the two checks. Effort S.

### App-3-F10 `/api/buffer` `recording` (protocol, minor)

`App:8419-8427`: `"recording":` is `buffer.recording && !safetyStopState().active`. In `/api/state` `"recording"` is
`camera_.isRecording() || soundRecording` (`App:9454`, upstream `App:7841`). Same key, different meaning on two routes of one page.
Rework: name it `buffer_recording` (or `buffer_active`) inside `bufferMembers`. The route itself: keep (new-ground, fits C1-S10
route idiom; upstream's only poll is 1 Hz `/api/state`, a 4 Hz bar needs a cheap route).

### App-3-F11 State fragment helpers (mismatch, nit)

`mediaTrimStateJson()` (`App:11598`) and `clipMergeStateJson()` (`App:11922`) return text that starts with `,`; used as
`<< mediaTrimStateJson()` (`App:9583`). `bufferMembers`, `sensorBinningBody` are used as `"," << x`. Upstream: `"," << exposureMeteringJson(settings)`
(`App:7867@upstream-1.6.0`); C1-I16 fragment builders end in `Body` or start with `json`. Rework: no leading comma; rename
`mediaTrimBody()`, `clipMergeBody()`, `bufferBody()`, `valueStepsBody()`; call with `"," <<`. Effort S.

### App-3-F12 Dead `play_reason` (slop, nit)

`App:9285` (and `clipInfoJson` `App:7359`): `"play_reason":""` constant; `grep play_reason src/web/WebControlPage.cpp` = 0. Delete.

### App-3-F13 `normalizeHardwareAnalogTarget` wrapper (slop, nit)

`App:10088-10091`: body is `return hardware::actions::canonicalAnalogTarget(target);`. Keep the catalog (it removes upstream's
three `normalizeSingleAction` copies, commit `916c1dd`); call `canonicalAnalogTarget` at the one call site (`App:10155`) and delete the wrapper,
or keep the upstream name and say so. Effort S.

## 3. Checked and not reported

| Item | Why not |
| --- | --- |
| New camera members in `/api/state` (`conform_fps`, `ladder_*`, `iso_max`, `cdng_log*`, `fps_speed_ramp*`, ...) | Present in `settingsBody` (App) and `settingsEvent` (CC) too: grep count 2 in App, 1 in CC per key. Follows C1-S13. Runtime-only `tuning_file_active`, `sensor_binning*` are web-only, like upstream's web-only status keys |
| Analog and step value lists from UI.conf (`isoSteps`, `fpsSteps`, `wbSteps`, `shutterAngleSteps`, free flags) | Read with `readSharedUiSettings()` before each action (5.9), dispatched as commands (C1-S11). Option lists never empty: `selectableValueSteps` adds the cap when the list would be empty (`App:1274-1289`) |
| `clear_hdr` action | Two `dispatch` calls, refusal logged with the upstream prefix "Hardware input action ignored:" (C1-I13); sensor by name substring as upstream `availablePcfResolutionOptions` does |
| ISO step without Auto in Clear HDR | Follows the port's `CameraController::setIsoAuto` refusal (`CC:11167-11169`); that camera rule belongs to unit CC |
| Delete routes refuse during pending writes (409) | Same rule as upstream gate 1 (C1-N04) applied to delete |
| `/api/media/file` path safety | name must end `.wav`, no `/`, `\`, `..`, NUL; `symlink_status` must be a regular file; folder from upstream `resolveMediaLibraryPath`. Read-only, same trust level as upstream downloads (C1-N10) |
| `abortSafetyStopFlushForRecord` in `dispatchHardwareInputCommand` and in `handleCommand` | Needed twice: the button path takes `hardwareActionMutex_` first, which the drain holds (comment `App:10119`). Second call is a no-op |
| HTTP changes vs original touch UI | Upstream Apertar-UI has no `/api/` call (`grep -rn "/api/"` = 0). `/api/state` changes are additive; `time_left_label` text and the tenth-floor of `record_time_left_minutes` change values only |

## 4. Abstractions (inventory section 6)

| Name | Verdict | Reason |
| --- | --- | --- |
| `playback::` module | keep | No upstream precedent (Core had no playback); routes that use it follow the route idiom. Strip F7 narration from the headers |
| `playback::PlaybackYield` | rework-to-upstream-pattern | Concept sound (lock-free stop); storage should be an App member, F8 |
| `HoldSignals` / `playbackHoldFor` | keep | Small pure function; one rule for routes and state. Downloads need a narrower rule (F2) |
| `ClipFactsCache` / `clipFactsCache()` | keep | Function-local static cache matches C1-I19 |
| `playbackYield()`, `playbackYieldActive()`, `playbackNowMs()` | rework-to-upstream-pattern | F8 |
| `DecodeSlots` | keep | Bounded decode memory; its env knob `APERTAR_PLAYBACK_WORKERS` falls under F3 |
| `third_party/liblj92/` | keep | Same decoder as the upstream UI's `third_party/`; judged in Playback unit |
| `hardware::HardwareConfigStore` | keep | Route side conforms except F4; the store itself is judged in App-2 / hardware units |
| `hwconf::` | keep | Not used in this slice beyond `controlsIssuesJson`; judged elsewhere |
| `bootconf::` | keep | Parse route conforms as file work; size judged elsewhere |
| `BootConfigReply`, `bootConfigGet` / `bootConfigSet` | simplify | Exists only to serve two doors; with F1 the socket command is the only writer and the struct can go (return a reply string as every command does) |
| `hardware::actions::` (`ActionCatalog.hpp`) | keep | Replaces three upstream copies; F13 wrapper aside |
| `bufferbudget::` | simplify | Used here through the global `safetyStopState()`; F10 key; judged in its unit |
| `storagepreroll::`, `util/ClipName.hpp` | keep | Not used in this slice |
| `MediaDeleteScope` | keep | Same gate shape as upstream C1-S04; fix order (F9) |
| `MediaSnapshot`, `MediaProfile` | keep | Used read-only here; judged in media-watcher unit |
| trim, clip-merge, controls, safety-stop threads | keep | Not judged in this slice; the route calls (`wakeControlsWorker`, `waitForClipMerge`, `trimMediaAfterDelete`) are one line each |
| helper scripts via `sudo -n` | keep | Upstream already runs `sudo -n install` for `config.txt` (`App:3157@upstream-1.6.0`); security of the new helpers judged in their unit |
| `errorReplyBody` | keep | Natural extension of `errorReply`; use it for all hand-built error bodies (F5) |
| `bufferMembers`, `sensorBinningBody`, `valueStepsJson`, `mediaTrimStateJson`, `clipMergeStateJson` | simplify | Rename and drop leading comma (F11) |

## 5. What conforms

| Item | Pointer |
| --- | --- |
| All new routes sit in the one flat `if (request.method == ... && request.path == ...)` chain before `/api/command`; each declares its own `Response`, sets the JSON content type, returns | `App:8419-9213`; C1-S10, 5.7 |
| Parameters in the query string via `queryParameterValue`; ids resolved through upstream `resolveMediaLibraryPath` | `App:8443-8446`, `App:8570`; 5.7 |
| Streaming uses upstream `Response::streaming` / `streamWriter`; the stop callback is an extra argument, not a new framework | `App:8604-8607`, `App:8742` |
| Delete routes add guards in place with operator sentences reused from upstream ("Wait for the current capture to finish writing to media.") | `App:9022-9027`; C1-N04, C1-I07 |
| Hardware inputs still only build commands and call `dispatchHardwareInputCommand` | `App:10160-10566`; C1-S11 |
| New camera state fields added in all three serialisers in the `<<` chain | `App:9465-9505`; C1-S13 |
| UI.conf recording-indicator switches added inside `"ui":{}` only | `App:9663-9666`; C1-S14 |
| JSON by hand, `escapeJson` on free text, `(x ? "true" : "false")` | throughout; C1-I08 |
| Logging: `std::cerr`, fixed prefix, failure only ("Hardware input action ignored: ...") | `App:10456`, `App:10684-10686`; C1-I13 |
| Completion-thread rule respected: `rawTakeActive()` is one atomic load | `CC:12554-12557`; C1-N09 |

## Skeptic

Every finding re-read on both sides (`/home/user/Apertar-Core` at `cinemate-port`, `/home/user/wt/core-upstream` at `upstream-1.6.0`).

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Port lines confirmed (body splice `App:9174-9182`, two callers of `bootConfigSet` `App:9192`, `App:14589`). But "the WebUI changes state only via /api/command" is false: upstream `POST /api/config` writes `apertar-hardware.conf` as a file route outside `handleCommand` (`App:7175-7195@upstream-1.6.0`), and presets/save, presets/delete, media/delete are POST routes too (`:7440`, `:7477`, `:7503`). A file route is not foreign; the two doors with different rules plus the JSON text splice are. Severity major -> minor. WCP never reads the HTTP status (`result.httpStatus` set at `WCP:20011`, read nowhere; the card branches on `result.code`, `WCP:20329`), so `/api/command` (always 200) loses nothing. |
| F2 | corrected | Guard confirmed (`App:8683-8689`, `:8812-8818`). Timelapse is a take: upstream itself treats it as one in the delete guard (`camera_.isRecording() \|\| soundRecordingActive() \|\| camera_.timelapseActive()`, `App:7514@upstream-1.6.0`). The speed test is a card benchmark a download would skew. The real loss against upstream is Standby (and the `media` hold, which only replaces upstream's 404). Severity major -> minor. Added: WebUI downloads are anchor clicks (`WCP:12089`, `:12917`), so a 409 shows no toast; the operator sees a failed browser download. |
| F3 | corrected | Knob confirmed (`App:89-105`, used `App:9779`). The README row already exists (`README.md:352`); the knob is one of about ten `APERTAR_*` env reads the port added to App (`App:266-285`, `:6402`, `:11335`, `:11379`, `:11402`), so this is one instance of the port-wide knob pattern, not a lone leftover. Severity major -> minor. Rework drops "add a README row". |
| F4 | corrected | Header confirmed (`App:8633-8641`, `WCP:18922`, `:20007`). The Origin test is not foreign: upstream `WebServer.cpp:160-161@upstream-1.6.0` uses exactly that rule ("Native clients/CLI have no Origin."). What stays new: the revision in a custom header instead of the query string, and the `old_page` refusal. |
| F5 | stands | Five hand-built hold bodies confirmed (`App:8460`, `:8499`, `:8529`, `:8569`, `:8687`, `:8816`); busy and gone bodies without `errorReply` (`App:8506`, `:8532`). `errorReplyBody` already exists in the port (`App:173`). |
| F6 | corrected | Strings confirmed, but the WebUI never shows them: the Clip Viewer maps the `hold` token to its own sentences (`pbvHoldText`, `WCP:12156-12162`) and downloads are anchor navigations. Only scripts and a raw JSON page see them. Severity minor -> nit. |
| F7 | stands | All tags confirmed at the cited lines; 46 `T<nn>` matches in App; upstream App has 10 full-line comments. |
| F8 | corrected | Confirmed (`App:6335-6352`). Upstream does keep mutable function-local statics, but only for caches (`App:2269-2272`, `:2788-2790@upstream-1.6.0`); cross-thread control flags are App members (`ApertarCoreApp.hpp` atomics). `clipFactsCache()` matches the cache precedent; the yield window does not. Effort M -> S: the stream functions already take a callable (`App:8522`, `:8608`, `:8742`, `:8767`, `:8799`, `:8856`), only the storage moves. |
| F9 | corrected | Race confirmed (`App:9015-9029`, `:9099-9112`, check at `App:12587`). The proposed reorder does not close it: `record_start` can pass its flag check at `App:12587` before the route sets the flag and still be starting (recording not yet true) when the route checks. `handleCommand` holds `commandMutex_` for the whole command (`App:12570`), so the route must take that lock around its checks and the scope construction. |
| F10 | corrected | Mismatch confirmed, but the key is not in `bufferMembers` (`App:301-311`); the route appends it (`App:8424`). Reader: `WCP:16514` (`payload.recording`). Rework moved there. |
| F11 | corrected | Leading comma confirmed (`App:11594-11601`, `:11918-11924`). The rename is not upstream style: upstream names fragments `*Json` as well (`exposureMeteringJson`, `App:7867@upstream-1.6.0`) and `*Body` (`settingsBody`, `:167`). Only the comma convention stays. |
| F12 | stands | Two writers (`App:7359`, `:9285`), no reader in WCP or Apertar-UI; only the KB design page names it. |
| F13 | dropped | The wrapper keeps the upstream function name and its upstream call site (`App:8410`, `:8495@upstream-1.6.0` vs port `App:10088`, `:10155`), so the original developer finds his function where he left it with the alias table moved out. Removing it is diff churn, not a move toward upstream. |

## Final findings

### App-3-F1 [mismatch, minor] POST /api/boot-config is a second door for set_boot_config; splices "cmd" into the body
- **where:** `src/ApertarCoreApp.cpp:9170-9195@cinemate-port`; `src/ApertarCoreApp.cpp:14589@cinemate-port`; `src/ApertarCoreApp.cpp:3775-3800@cinemate-port`; `src/web/WebControlPage.cpp:20004-20017@cinemate-port`
- **port way:** The route finds the first `{` in the body, inserts `"cmd":"set_boot_config"`, runs `parseControlCommand` and calls `bootConfigSet(parsed.command, revision, request.headers.count("origin") > 0)` outside `handleCommand` / `commandMutex_` (it holds `bootConfigMutex()`). The socket command `set_boot_config` calls the same function with `browser=false`. Same write, two doors, different rules (`old_page` only on the route, revision from header or field).
- **Apertar way:** A file writer may be a route (upstream `POST /api/config`, `src/ApertarCoreApp.cpp:7175-7195@upstream-1.6.0`) or a command (`set_fan_mode`, `:10568`, reached through `POST /api/command` -> `handleWebCommand` -> `handleCommand`, `:7085-7091`, `:7637-7641`), but each is one door, and no route rewrites a JSON body into a command.
- **why it matters:** The text splice is a hack the original developer would refuse; two doors with different refusal rules for one file are the spaghetti the owner wants gone.
- **rework:** Delete the `POST /api/boot-config` route. In WCP `bootConfigPost`, send `{"cmd":"set_boot_config",...,"revision":r}` to `/api/command`; the command already reads `revision` as a field and the card branches on `result.code` only (`result.httpStatus` is set at `WCP:20011` and read nowhere). Drop the `browser` parameter from `bootConfigSet` (see F4). `GET /api/boot-config` stays as the read twin of `GET /api/config`; `POST /api/boot-config/parse` stays as a raw-body file route like `presets/import`. With one caller, `BootConfigReply` can become a plain reply string.
- **effort:** S
- **deliberate:** no. Commit `2955ef8` and `architecture/config.md` section 7.1 describe both doors but never weigh `/api/command`.

### App-3-F2 [removed-upstream-behaviour, minor] Downloads refused in Standby (and without media), not only during a take
- **where:** `src/ApertarCoreApp.cpp:8683-8690@cinemate-port`; `src/ApertarCoreApp.cpp:8812-8819@cinemate-port`; `src/playback/PlaybackHold.hpp:56-66@cinemate-port`
- **port way:** Both download routes return 409 whenever `playbackHoldReason()` is non-empty. That rule was written for playback and covers recording, sound, timelapse, the yield window, pending writes, the speed test, Standby and media not usable.
- **Apertar way:** `GET /api/media/download` (`src/ApertarCoreApp.cpp:7197@upstream-1.6.0`) and `download-selected` (`:7318`) have no guard; downloads work in Standby. Upstream counts timelapse as a take (`:7514`), so holding a download for recording, sound, timelapse, writes and the speed test is consistent with commit `a37a902`'s stated reason.
- **why it matters:** An operator who offloads clips from a sleeping camera gets 409 "Playback held: standby. Downloads wait." The WebUI starts downloads with an anchor click (`WCP:12089`, `:12917`), so the refusal shows only as a failed browser download, after the toast "Preparing ... for download."
- **rework:** Give the download routes their own rule: `downloadHoldReason()` = recording, sound, timelapse, yield window, pending writes, speed test; Standby only when `standbyUsbPoweredOff_` is true; no `media` hold (the route's own 404 covers missing media). Keep the stream stop callback. One README sentence on the take rule.
- **effort:** S
- **deliberate:** unknown. Commit `a37a902` and fork-log row `a37a902` justify the hold during a take only ("a big read from the card a take writes to"); Standby is not mentioned.

### App-3-F3 [slop, minor] APERTAR_WEB_PREVIEW_RECORDING_FPS env knob left from an experiment
- **where:** `src/ApertarCoreApp.cpp:89-105@cinemate-port`; `src/ApertarCoreApp.cpp:9778-9784@cinemate-port`; `src/ApertarCoreApp.cpp:9583-9586@cinemate-port`; `README.md:352@cinemate-port`
- **port way:** `std::getenv` in a static lambda; the comment calls it "the A/B knob" and cites KB research ids. Default 30 equals the old fixed rate. It is one of about ten `APERTAR_*` env reads the port added to App (`App:266-285`, `:6402`, `:11335`, `:11379`, `:11402`); state also exposes `media_trim_env_off` and `clip_merge_env_off`. It has a README row.
- **Apertar way:** `constexpr double kWebPreviewMaxFps = 30.0` (`src/ApertarCoreApp.cpp:62@upstream-1.6.0`), used at `:8105`. Core reads one env var of its own, `APERTAR_HARDWARE_CONFIG` (`:4254`). Process options are `Options` plus main flags (C1-S24).
- **why it matters:** An experiment's knob that changes nothing by default, never run on the Pi (commit `fb557e9`: "Not run on the Pi"), in a code base with no env knobs.
- **rework:** Run the two-take test. If the knob is not needed, delete `webPreviewRecordingFps()`, the `rawTakeActive` branch and the README row. If it is needed, use a fixed reduced rate during raw takes, or an `Options` field with a `--flag` and a usage line. Treat the `*_env_off` state members with the port-wide knob sweep.
- **effort:** S
- **deliberate:** yes. Commit `fb557e9` calls it a knob whose need a Pi test still has to decide.

### App-3-F4 [new-ground, minor] Revision in an X-Apertar-Revision header, plus an old_page refusal
- **where:** `src/ApertarCoreApp.cpp:8633-8641@cinemate-port`; `src/ApertarCoreApp.cpp:9190-9193@cinemate-port`; `src/ApertarCoreApp.cpp:3790-3791@cinemate-port`; `src/web/WebControlPage.cpp:18922@cinemate-port`; `src/web/WebControlPage.cpp:20007@cinemate-port`
- **port way:** A custom request header carries the revision. A request with an `Origin` header and no revision gets 409 `old_page`; a request without `Origin` keeps last-writer-wins.
- **Apertar way:** Route parameters travel in the query string (`queryParameterValue(request.query, "name")`, `src/ApertarCoreApp.cpp:7440@upstream-1.6.0`). The Origin-means-browser rule itself is upstream's (`src/web/WebServer.cpp:160-161@upstream-1.6.0`, "Native clients/CLI have no Origin."). Core and page ship together; there is no page-version concept (C1-N11).
- **why it matters:** The revision check is worth keeping. The header is a second parameter channel next to the query string; `old_page` is a page-version concept upstream does not have.
- **rework:** `POST /api/config?revision=r` (and, with F1, a `revision` field in `set_boot_config`). Stale revision -> 409 `stale`. Keep `old_page` only if the owner wants the stale-tab guard; it can stay on upstream's Origin rule. Drop the header reads.
- **effort:** S
- **deliberate:** yes. Commit `5395fa4` explains the stale-tab case.

### App-3-F5 [mismatch, minor] 409 hold replies hand-built at five sites; sibling routes differ; busy and gone replies without error key
- **where:** `src/ApertarCoreApp.cpp:8460@cinemate-port`; `:8499`; `:8506`; `:8529`; `:8532`; `:8569`; `:8687`; `:8816`
- **port way:** `"{\"ok\":false,\"error\":\"Playback held: " + hold + ...` string-built at five sites; the `/api/media/clip` 409 (`:8460`) uses `errorReply` and has no `hold` member; busy is `{"ok":false,"busy":true}` and gone is `{"ok":false,"error":...,"gone":true}`, both hand-built.
- **Apertar way:** Replies come only from `okReply` / `errorReply`, reused with id -1 in HTTP routes (`src/ApertarCoreApp.cpp:7188`, `:7647@upstream-1.6.0`; C1-I06). The port already has `errorReplyBody` for extra members (`App:173@cinemate-port`).
- **why it matters:** Duplicated reply text with inconsistent shapes; a client that shows `result.error` gets nothing for busy.
- **rework:** A free function `playbackHoldReply(hold)` returning `errorReplyBody(-1, holdSentence(hold), "\"hold\":\"" + hold + "\"")`, used at all six hold sites including `/api/media/clip`. Busy and gone through `errorReplyBody` with an operator sentence plus `"busy":true` / `"gone":true`.
- **effort:** S
- **deliberate:** no

### App-3-F6 [mismatch, nit] Hold sentences carry internal hold tokens
- **where:** `src/ApertarCoreApp.cpp:8687@cinemate-port`; `:8816`; `:8499`
- **port way:** "Playback held: media_test. Downloads wait."; "Recording. Downloads wait until the take ends."
- **Apertar way:** An error is one operator sentence: "Stop recording before deleting media." (`src/ApertarCoreApp.cpp:7514@upstream-1.6.0`), "Wait for the media speed test to finish first." (`:9110`), "Wake the camera before capturing." (`:9211`). C1-I07, C1-N02.
- **why it matters:** Small: the WebUI never shows these strings (the Clip Viewer maps the token itself, `pbvHoldText`, `WCP:12156-12162`; downloads are anchor clicks). Scripts and a raw JSON page see internal identifiers.
- **rework:** `holdSentence(hold)` next to the F5 helper, in upstream's families: recording -> "Stop recording before downloading media.", writing -> "Wait for the current capture to finish writing to media.", media_test -> "Wait for the media speed test to finish first.", standby -> "Wake the camera first.", media -> "Mount media first."
- **effort:** S
- **deliberate:** no

### App-3-F7 [slop, minor] Ticket numbers and history narration in comments
- **where:** `src/ApertarCoreApp.cpp:8476@cinemate-port`; `:8551`; `:8663`; `:9254`; `:9318`; `:9362`; `:10182`; `:10469`; `:10482`; `:89-92`; `:6335`; `src/playback/PlaybackHold.hpp:3-25@cinemate-port`
- **port way:** Comments carry T48, T51, T39, T47, T20 Step 4, T34, "request 13", KB research ids, "design sketch v2 (not in any repository)", "critic M8" and line numbers into other files (46 `T<nn>` matches in App).
- **Apertar way:** 10 full-line comments in the 11 025-line upstream App, each a hazard or a reason, no ticket numbers (C1-I14; e.g. `src/ApertarCoreApp.cpp:8103-8104@upstream-1.6.0`).
- **why it matters:** The references mean nothing to the original developer; the line numbers go stale.
- **rework:** Delete the tags and references. Keep one sentence where a hazard is stated: hold before read; no lock on the completion thread; why the yield window exists.
- **effort:** S
- **deliberate:** no

### App-3-F8 [mismatch, minor] Playback yield window is a file-scope singleton
- **where:** `src/ApertarCoreApp.cpp:6335-6352@cinemate-port`
- **port way:** `static PlaybackYield` in `playbackYield()`, plus free functions `playbackYieldActive()` and `playbackNowMs()`. `handleCommand` (`App:12582`) and the media watcher (`:10915`, `:10976`, `:11264`) write it; stream writers and state builders read it. Stated reason: avoid header rebuilds.
- **Apertar way:** Cross-thread control flags are `std::atomic` members of App in `ApertarCoreApp.hpp` (C1-S18); parts receive `std::function` callbacks from App (`src/ApertarCoreApp.cpp:6783-6792@upstream-1.6.0`; C1-S19). Function-local statics exist upstream only as caches (`:2269-2272`, `:2788-2790`), which is what `clipFactsCache()` is.
- **why it matters:** Hidden control state outside the App object, unlike every other state group.
- **rework:** Member `playback::PlaybackYield playbackYield_` in `ApertarCoreApp.hpp` (`PlaybackHold.hpp` pulls only `<atomic>` and `<cstdint>`). The streams already take a callable (`App:8522`, `:8608`, `:8742`, `:8767`, `:8799`, `:8856`); pass `[this]{ return playbackYield_.active(playbackNowMs()); }`. `clipFactsCache()` stays.
- **effort:** S
- **deliberate:** yes. Comment at `App:6335-6336`: "File scope, so the header does not pull in the readers".

### App-3-F9 [bug, minor] Delete gate is not atomic with record_start
- **where:** `src/ApertarCoreApp.cpp:9015-9029@cinemate-port`; `src/ApertarCoreApp.cpp:9099-9112@cinemate-port`; `src/ApertarCoreApp.cpp:12570@cinemate-port`; `src/ApertarCoreApp.cpp:12587@cinemate-port`
- **port way:** The delete routes check `isRecording` / sound / timelapse and `mediaWritesPending`, then construct `MediaDeleteScope`. `handleCommand` refuses `record_start` with "Deleting media. One moment." only if the flag is already set when it reaches `App:12587`. The routes do not take `commandMutex_`.
- **Apertar way:** Upstream had no flag and the same race (`src/ApertarCoreApp.cpp:7514@upstream-1.6.0`), so this is a hole in the port's new guarantee, not a regression. Upstream's serialisation tool is `commandMutex_`, held by `handleCommand` for the whole command.
- **why it matters:** `record_start` passes the flag check, the route then checks `isRecording` before the start has set it, sees false, and deletes during the take's start. Reordering the scope first does not close this window.
- **rework:** In both delete routes, take `std::lock_guard` on `commandMutex_` around the recording / pending-writes checks and the `MediaDeleteScope` construction (hold the scope in a `std::optional` declared before the lock block), then release the lock before the delete itself. A running `record_start` then either has finished (recording is true, refuse) or has not reached its check (it sees the flag).
- **effort:** S
- **deliberate:** no

### App-3-F10 [protocol, minor] /api/buffer "recording" differs from /api/state "recording"
- **where:** `src/ApertarCoreApp.cpp:8423-8424@cinemate-port`; `src/ApertarCoreApp.cpp:9454@cinemate-port`; `src/web/WebControlPage.cpp:16514@cinemate-port`
- **port way:** `/api/buffer` appends `recording = buffer.recording && !safetyStopState().active` in the route; `/api/state` sends `recording = camera_.isRecording() || soundRecording`.
- **Apertar way:** One key has one meaning across state copies (C1-S13; `/api/state` `recording` at `src/ApertarCoreApp.cpp:7841@upstream-1.6.0`).
- **why it matters:** A page that reads both routes sees the same key disagree (sound-only take, safety stop).
- **rework:** Rename the key in the `/api/buffer` route to `buffer_recording` (or `buffer_active`) and the reader at `WCP:16514`. Keep the 4 Hz route.
- **effort:** S
- **deliberate:** no

### App-3-F11 [mismatch, nit] State fragment helpers return a leading comma
- **where:** `src/ApertarCoreApp.cpp:11593-11602@cinemate-port`; `src/ApertarCoreApp.cpp:11917-11925@cinemate-port`; `src/ApertarCoreApp.cpp:9583-9586@cinemate-port`
- **port way:** `mediaTrimStateJson()` and `clipMergeStateJson()` return text that starts with `,`; next to them `bufferMembers` is used as `"," << bufferMembers(...)`.
- **Apertar way:** Fragments carry no separator; the caller writes it: `"," << exposureMeteringJson(settings)` (`src/ApertarCoreApp.cpp:7867@upstream-1.6.0`), `"," << imuStatusBody(true)` (`:8028`). Upstream names fragments both `*Json` and `*Body`, so the names can stay.
- **why it matters:** Two conventions inside one `<<` chain.
- **rework:** Drop the leading comma in both functions and write `<< "," << mediaTrimStateJson()` / `<< "," << clipMergeStateJson()` at their callers.
- **effort:** S
- **deliberate:** no

### App-3-F12 [slop, nit] Constant "play_reason":"" read by nobody
- **where:** `src/ApertarCoreApp.cpp:9285@cinemate-port`; `src/ApertarCoreApp.cpp:7359@cinemate-port`
- **port way:** Every list item and clip info carries an empty `play_reason`; no reader in `WebControlPage.cpp` or Apertar-UI (only the KB design page `working/playback/design-playback.md:588` plans one).
- **Apertar way:** no precedent
- **why it matters:** Dead protocol field.
- **rework:** Delete it at both sites.
- **effort:** S
- **deliberate:** no
