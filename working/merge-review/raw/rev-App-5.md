# Review App-5: ApertarCoreApp.cpp, handleCommand (port lines 12727-14875)

| Item | Value |
| --- | --- |
| Scope | `/home/user/build/review/diffs/App.part05.diff` (901 lines, 16 hunks), read completely |
| Refs | port `@cinemate-port` `01f170c`; upstream `@upstream-1.6.0` `35dbe67` (`handleCommand` at `App:9091`); fork main `@main` `f60e301` |
| Yardstick | `raw/conv-core-command-plane.md` (rule ids `C1-*`), upstream worktree read at each cited line |
| Inventory | `raw/inv-App-5.md` |
| Cross-refs | App-1-F2, App-1-F4, App-1-F5, App-2 (env knobs, `mediaTrimSetting_`), App-2-F11, App-3-F1, App-4 (pre-roll worker, pre-roll default), CC-1-F7, CC-5 (ladder) |

Already judged in other units and not repeated as findings here: `errorReplyBody` (App-1-F5), Boot Config door and `BootConfigReply` (App-1-F4, App-3-F1), `HardwareConfigStore` itself (App-2-F11), `[storage]` parsed twice and header singletons (App-1-F2), env knobs and `mediaTrimSetting_` (App-2), pre-roll worker lock and default (App-4), `mode_ladder.conf` and `setModeLadder` signature (CC-5).

## Findings

| Id | Sev | Category | Title | Deliberate |
| --- | --- | --- | --- | --- |
| App-5-F1 | major | mismatch | Four storage switches write single hardware-file keys through the store, block copied four times | unknown |
| App-5-F2 | minor | mismatch | Five boolean spellings and two argument shapes for on/off commands | no |
| App-5-F3 | minor | bug | `get_state` writes `media_state` twice from two snapshots | no |
| App-5-F4 | minor | duplication | Clip name template parsed in App and again in CC; unused out-parameter | no |
| App-5-F5 | minor | mismatch | `set_value_steps`: selector command, range table inside the branch, nested `ui` reply | yes |
| App-5-F6 | minor | slop | Tutorial codes T33, T34, T39, T42, Q10 in `handleCommand` comments | no |
| App-5-F7 | minor | new-ground | `set_timecode_mode target=` splits UI and file timecode; not run on a Pi | yes |
| App-5-F8 | nit | new-ground | `record_stop` also ends a storage pre-roll; `storage_preroll` is a bare noun | yes |
| App-5-F9 | nit | mismatch | `set_iso_auto` gains a field (`enabled=false` = lock) | yes |

### App-5-F1 [mismatch, major] Storage switches through the hardware store, copied four times

- where: `src/ApertarCoreApp.cpp:12829-12855`, `:12857-12898`, `:12900-12927 @cinemate-port` (`set_buffer_mode`, `set_frames_per_folder`/`set_clip_merge`, `set_storage_preroll`); compare `:13194-13203 @cinemate-port` (`set_media_trim`).
- port way: each block builds `StoreFlags{backup, trusted}`, calls `hardware::configStore().edit(base-or-current, {{Set, "storage"|"media", key, value}}, by, flags, hardwareConfigFacts())`, on failure `errorReplyBody(... "code","revision","issues":[...])`, on write updates `controlsErrors_`/`controlsWarnings_` and `wakeControlsWorker()`, then `refreshBufferRequest()` and replies `revision`, `written`, `apply` plus `bufferSettingMembers()`. The 15-line body is the same in all three blocks. `flags.trusted = true` skips the store's own "text-mode only" rule for `[storage]`/`[media]` (comment at `:12845`, `:12873`, `:12911`). In the same slice, the sibling storage switch `set_media_trim` is a plain camera setter.
- Apertar way: App never edits one key of `apertar-hardware.conf` by itself; the hardware file is saved whole by the WebUI editor (`App:7175-7178 @upstream-1.6.0` `if (!saveHardwareConfigFile(request.body, &backupPath, &errorMessage))`), C1-S07. A recording option that the operator switches from the UI is a camera setting: setter -> `applySettingsLocked` -> `camera_settings.conf` (C1-R2, C1-S15), and its command has the C1-I01 shape, e.g. `App:9269-9273 @upstream-1.6.0`:
  `if (command.name == "set_iso_auto") { return camera_.setIsoAuto() ? okReply(command.id, settingsBody(camera_.settings())) : errorReply(command.id, camera_.lastError()); }`
- why it matters: the original developer sees socket commands that do file revision bookkeeping, error codes, worker wakes and store bypass flags for what are four ordinary switches; two storage switches of one card persist in two different files (`media_trim` in `camera_settings.conf`, `buffer`/`frames_per_folder`/`clip_merge`/`preroll` in the hardware file).
- rework: as App-2's rework, seen from the command side. Add `cdngBuffer`, `framesPerFolder`, `clipMerge`, `storagePrerollAuto` to `CaptureSettings` (C1-R2 steps 1-10); setters in CC. Each command becomes the C1-I01 block (`set_buffer_mode value=`, `set_frames_per_folder value=`, `set_clip_merge_enabled enabled=`, `set_storage_preroll_enabled enabled=`), reply `settingsBody`. `set_clip_merge` keeps its one extra line `if (enabled) clipMerge("switch");`. Delete the three store-edit blocks, the `trusted` uses, the `[storage] buffer|frames_per_folder|clip_merge` and `[media] preroll` keys (hardware file keeps `mount_path`, `pcie_controller`). Client changes: touch UI `ApertarControlBridge.cpp:627`, `:692`; WCP calls. If the keys must stay in the hardware file: at least one local lambda `saveStorageKey(section, key, value)` (C1-I17) for the three copies.
- rework risk: existing `apertar-hardware.conf` files carry the keys; read them once at start as a migration default. CC reads `[storage]` at take start today (App-1-F2), which this removes.
- effort: M.

### App-5-F2 [mismatch, minor] Boolean parsing and on/off argument shapes

- where: `src/ApertarCoreApp.cpp:12770-12778` (`parseBooleanToken`), `:12867-12871` (strict four-value test), `:12901-12906` (`tolower`, on/off/true/false/1/0), `:14096-14101` (local `boolField`), `:14136`, `:14143` (`parseUiSettingsBool`), `:13194-13216` (`enabled` without `_enabled` name) `@cinemate-port`.
- port way: one slice, five ways to read a boolean; `set_storage_preroll` takes `value=on|off`; `set_media_trim`, `set_preview_tdn`, `set_fps_phase_lock`, `set_fps_speed_ramp` take `enabled` but are not named `_enabled`.
- Apertar way: C1-I05: `const auto enabled = command.string("enabled"); ... *enabled == "true" || *enabled == "1"` (`App:9482-9486 @upstream-1.6.0`, `handleUiToggle`); the strict form only where a wrong value must be refused (`App:9130-9133 @upstream-1.6.0`). C1-I03/C1-I04: boolean argument `enabled`, command `set_<thing>_enabled` (19 upstream; exception `set_standby_usb_power_off`). Presets use `parseUiSettingsBool` (`App:10230+ @upstream-1.6.0`), which the port follows correctly.
- why it matters: each new reader is one more spelling to remember; `set_storage_preroll value=on` is the only on/off command upstream-style clients cannot drive with `enabled=`.
- rework: `set_controls` flags and `set_mode_ladder` use the C1-I05 test (or the strict form when refusal matters); delete the `tolower` loop; rename to `set_storage_preroll_enabled enabled=` (falls out of F1). Naming of the four camera switches: `set_media_trim_enabled`, `set_preview_tdn_enabled`, `set_fps_phase_lock_enabled` is upstream style; fork main already has `set_clear_hdr enabled=` (`App:9447 @main`), so this part is optional and a nit.
- effort: S.

### App-5-F3 [bug, minor] `media_state` twice in `get_state`

- where: `src/ApertarCoreApp.cpp:12944` (`438a342`) and `:12961` (`70e8376`) `@cinemate-port`.
- port way: `<< ",\"media_state\":\"" << mediaSnapshot().stateName()` and, 17 lines later, `<< ",\"media_state\":\"" << mediaState.stateName()` from a snapshot taken at `:12935`. Two snapshots, one key twice.
- Apertar way: C1-R4: one key per status field, same key in `get_state` and `/api/state` (`App:9223-9237`, `App:7836-7856 @upstream-1.6.0`). The port's web state has it once (`App:9555 @cinemate-port`).
- failing input: `{"cmd":"get_state"}` while a card is being yanked: the two values can differ; JSON with duplicate keys is parser-dependent (Qt keeps one).
- rework: delete line `:12944`.
- effort: S.

### App-5-F4 [duplication, minor] Clip name template parsed twice

- where: `src/ApertarCoreApp.cpp:13241-13256`, `:13258-13268` `@cinemate-port`; `src/camera/CameraController.cpp:11835-11854`, `:11856+ @cinemate-port`.
- port way: `set_clip_name_template` calls `apertar::clipname::parse` in App, then `camera_.setClipNameTemplate`, which parses again; `std::string stored` is passed and never read. `preview_clip_name` calls `camera_.previewClipName` (parses) and then parses again in App for `normalized`/`corrected`.
- Apertar way: C1-I12: App checks presence, the CC setter checks the value and reports through `lastError()` (`App:9251-9258 @upstream-1.6.0`; `CC:7835-7849 @upstream-1.6.0`).
- rework: App: presence check, `camera_.setClipNameTemplate(*value)`, reply `settingsBody` plus `corrected` computed by comparing `settings.clipNameTemplate` with `*value` (or CC exposes `clipNameCorrected` as a runtime settings field). `previewClipName` returns normalized template and corrected flag with the example. Drop `stored`.
- effort: S.

### App-5-F5 [mismatch, minor] `set_value_steps` shape

- where: `src/ApertarCoreApp.cpp:14110-14162 @cinemate-port`.
- port way: one command with a `name=` selector writes up to six UI.conf keys; a `static constexpr ListKeys lists[]` range table sits inside the branch; reply `"ui":{` + `valueStepsJson(...)` + `}`.
- Apertar way: C1-I02: one UI.conf value per command, echo `"snake_key":value` (`App:10206-10216 @upstream-1.6.0` `set_sleep_mode`); tables of allowed values live in free functions in the anonymous namespace (C1-S06, C1-I11, e.g. `favoriteCandidateOrder()` `App:727-763`). Nested `ui` exists only in `/api/state` (conv 5.5).
- why it matters: small; the reply duplicates the state's `ui` group and the ranges duplicate other range checks (ISO 50..51200 also in the preset reader).
- verdict: simplify. Move the table to a free `valueStepsKeys(name)` beside `parseValueStepsList`; reply flat (`"iso_steps":"..."` etc. for the chosen list) or `settingsBody`-style `okReply(command.id)` and let the WebUI read `/api/state` next poll (C1-S26). Keep the single command: one per list would be 4 x 3 commands. Remove "T33".
- effort: S.

### App-5-F6 [slop, minor] Tutorial codes in comments

- where: `src/ApertarCoreApp.cpp:12746` (`T42`), `:12810` (`T39`), `:14094` (`T34`), `:14111` (`T33`), `:14529` (`T34 (Q10)`) `@cinemate-port`; also `:12572` (`T47`, head, outside slice). `:13284` "no target: both, as before" narrates history.
- Apertar way: C1-I14: comments are rare and state a hazard or reason; 0 TODO, no ticket ids in `src @upstream-1.6.0`.
- rework: drop the codes, keep the sentence; "as before" -> "no target: both".
- effort: S.

### App-5-F7 [new-ground, minor] UI timecode and file timecode set apart

- where: `src/ApertarCoreApp.cpp:13279-13300`, preset `:14348-14352`, `:14428-14433 @cinemate-port`; commit `909aaa5` ("Tested: desk (page loads, labels); Pi build pending").
- port way: `set_timecode_mode target=both|ui|files`; no target = both. Preset key `cameraTimecodeMode` sets the file copy; legacy `timecodeMode` sets both only when the new key is absent.
- Apertar way: no precedent for the split; C1-I18 keeps camera and UI.conf in step (`App:9424-9436 @upstream-1.6.0` writes both). Unmodified UI sends no target and gets the old result: protocol safe (C1-N11). Preset key naming follows C1-S22.
- verdict: keep (least foreign shape: optional field, old default). Needs a Pi run before merge; the commit says it has not had one. Document for the original developer that the UI.conf `timecodeMode` no longer always equals `timecode_mode`.
- effort: S (test + note).

### App-5-F8 [new-ground, nit] `record_stop` ends a pre-roll; `storage_preroll` naming

- where: `src/ApertarCoreApp.cpp:14832-14836`, `:14603-14617 @cinemate-port`.
- port way: `record_stop` during a pre-roll sets `storagePrerollStop_` and replies `"recording":false,"storage_preroll_stopped":true`. The manual command is `storage_preroll` (a noun).
- Apertar way: `record_stop` stops the sound take first, then the camera take (`App:10783-10794 @upstream-1.6.0`) - one stop button for whatever runs; the port's extra branch follows that idea. Action names are `<verb>_<noun>`: `run_media_speed_test` (C1-I04).
- verdict: keep the `record_stop` branch; rename `storage_preroll` to `run_storage_preroll` (touch UI `ApertarControlBridge.cpp:621`, WCP, head gate `App:12591`).
- effort: S.

### App-5-F9 [new-ground, nit] `set_iso_auto enabled=false`

- where: `src/ApertarCoreApp.cpp:12995-13001 @cinemate-port`; `CC:11146-11166 @cinemate-port`; commit `646a194`.
- port way: the auto command takes an optional field; `false` locks at the measured gain.
- Apertar way: the auto variant is its own command without fields (C1-I04; `App:9269`, `:9293`, `:9308 @upstream-1.6.0`). A client could send `set_iso value=<iso_actual>`, but `iso_actual` may be one poll old; doing it in CC under its mutex is the sound place.
- verdict: keep. Commit weighs it ("set_iso value=N stays off at N").

## Abstraction verdicts (inventory section 6)

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `hardware::HardwareConfigStore`, `StoreFlags`, `StoreResult`, `ReplacedInfo` | simplify | Keep for `set_controls` (App-2-F11); remove its use for storage switches (F1), which also removes `flags.trusted` |
| `hwconf::` (`Edit`, `parseEdits`, `validate`) | keep | Header logic; `set.<sec>.<key>` fields are flat strings (C1-I09) and WCP uses them (`WCP:18225`, `:18391`) |
| Controls worker (`wakeControlsWorker`, `controlsErrors_/_Warnings_`) | keep | C1-S20 worker shape; from this slice only the wake calls; with F1 only `set_controls` wakes it |
| `bufferbudget::` | rework-to-upstream-pattern | Shared state per App-1-F2; storage settings to CC (F1) |
| `framepath::` | keep | Pure helper; used for value validation here |
| Clip merge worker, `clipMerge()` | keep | C1-S20 precedent; one call here |
| `storagepreroll::`, `requestStoragePreroll`, `storagePrerollGuard` | keep (logic), simplify (default) | Guard reads like the head gates; default off per App-4 |
| Media watcher / `MediaSnapshot` | keep | Only read in `get_state`; F3 |
| Media trim worker, helper scripts | out of slice | `set_media_trim` itself conforms to C1-I01; `mediaTrimSetting_` copy per App-2 |
| `apertar::clipname::parse` | simplify | One parse, in CC (F4) |
| `ModeLadder.hpp`, `modeLadderJson`/`setModeLadder`/`applyLadderToPreset` | keep | Commands are C1-S02 blocks; preset check before `applyCapturePreset` keeps C1-S22 one-transaction; file and signature per CC-5 |
| `bootconf::`, `bootConfigGet/Set` | simplify | Commands should return `okReply`/`errorReply` strings, not `.body` of a reply struct (App-1-F4, App-3-F1) |
| `errorReplyBody`, `controlsIssuesJson`, `controlsConflictsJson` | rework-to-upstream-pattern | Per App-1-F5; F1 removes three of its call sites here |
| `FormatScope` RAII struct in `format_media` | keep | Covers the early `return errorReply`; small and local (C1-I17 spirit) |
| `hardware::ActionCatalog` | out of slice | Only its command name in `help` |

## Conforms

- `list_sensor_modes`: two fields appended in the existing `<<` chain (`App:12735-12736`), C1-I08.
- `set_cdng_log`, `set_media_trim`, `set_preview_tdn`, `set_fps_phase_lock`, `set_fps_speed_ramp`, `set_conform_fps`: C1-I01 setter shape, `settingsBody` reply, `lastError()`; ranges in CC (`CC:11807` conform FPS), C1-I12.
- Four new UI toggles: one `handleUiToggle` line each (`App:13505-13512`), plus snapshot (`App:1904`, `:2094`), web `ui` group (`App:9663`), preset writer (`App:7786`) and reader (`App:14453`) - C1-R3 complete.
- Preset keys: camelCase `camera<Name>`, writer `App:7844-7868` and reader `App:14276-14373` in step, "Invalid preset <thing>." sentences, local lambda `readHdrKnob` (C1-S22, C1-I17).
- `help` literal lists every new command (C1-R1 step 8).
- `get_state` new status keys also in `/api/state` (`App:9457-9586`), C1-R4.
- `record_start`/`record_stop` replies add `recording_dropped_frames` next to the upstream flag (C1-N05).
- `publishEvent`: new event names added to the substring broadcast list (C1-S12, C1-R4).
- `test_output`: C1-R1 shape, take guard on the first lines, operator sentences.
- `set_timecode_mode` and `set_iso_auto`: no new field = upstream behaviour (C1-N11).
- `storage_preroll` added to the head gate (`App:12588-12592`), C1-R1 step 4.

## Protocol

No break for an unmodified upstream UI or WebUI: all changed commands keep their old meaning without the new fields; new state keys are ignored by old clients (C1-N11). Command input stays flat (C1-I09). Replies with arrays (`issues`, `conflicts`) are App-1-F5.

## Commands used

`git -C /home/user/Apertar-Core blame -s -L 12935,12965 cinemate-port -- src/ApertarCoreApp.cpp`; `git show -s 646a194 909aaa5 b0e90ad dcf09ee`; `sed -n 9091,9125p`, `9265,9320p`, `9424,9440p`, `7170,7195p`, `9478,9490p`, `10783,10800p` on upstream `App`; `grep -n` on port `App`, `CC`, `WCP`, `ApertarControlBridge.cpp`.

## Skeptic

| id | verdict | why |
| --- | --- | --- |
| App-5-F1 | corrected | Port code confirmed (`App:12827-12927 @cinemate-port`). But the stated Apertar way is wrong: upstream operator commands DO persist single hardware-file keys - `set_imu_driver`/`set_imu_orientation`/`set_imu_sync_offset` call `Mpu6050RecordingSession::setConfiguredDriver(...)` which runs `writeHardwareConfigValue(path,"imu","driver",...)` (`App:9646-9655`, `src/hardware/Mpu6050RecordingSession.cpp:604`, `:1295-1300 @upstream-1.6.0`). The mismatch is the shape (store machinery inline, copied three times, `flags.trusted` bypass, worker wake, array reply), not the file. The "move to camera_settings.conf" rework also misses that `[storage]` keeps `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent` next to `buffer` (KB `architecture/config.md:115`, `working/drop-frames/README.md:73-74`), and env overrides read per take; splitting `buffer` from its tuning keys is worse. Rework now = the owner-function pattern. |
| App-5-F2 | corrected | Upstream itself uses `parseUiSettingsBool(*value,false)` on command arguments in `apply_preset` through a local lambda `addBoolUpdate` (`App:10231-10237`, `:10282-10287 @upstream-1.6.0`), and `parseBooleanToken` is an upstream helper (`App:2936 @upstream-1.6.0`). So `set_value_steps`, the `set_mode_ladder` `boolField` lambda and `set_controls restore=` have precedent. What survives: the `set_storage_preroll` tolower loop with `value=on|off`, and the four camera switches named without `_enabled`. |
| App-5-F3 | stands | `App:12944` and `App:12961 @cinemate-port` both write `"media_state"`, from `mediaSnapshot()` and from `mediaState`. |
| App-5-F4 | stands | `App:13245-13253` parses then calls `CC:11835-11854` which parses again; `stored` unread; `setClipNameTemplate` has no other caller (`CameraController.hpp:92`), so the out-parameter can go from the signature too. `preview_clip_name` parses twice (`App:13261-13267`, `CC:11856-11860`). |
| App-5-F5 | corrected | Confirmed. Upstream's `set_favorites_order` replies an array (`App:10227 @upstream-1.6.0`), so a list in the reply has precedent; the nested `ui` object does not. The ranges are duplicated in the UI.conf snapshot reader too (`App:2160 @cinemate-port` `parseValueStepsList(value, 50.0, 51200.0)`), so the free table must serve both. |
| App-5-F6 | stands | `T42` `App:12746`, `T39` `:12810`, `T34` `:14094`, `T33` `:14111`, `T34 (Q10)` `:14529`, "as before" `:13285 @cinemate-port`. |
| App-5-F7 | stands | `909aaa5` body confirms intent, old default and "Pi build pending"; upstream writes both (`App:9424-9436 @upstream-1.6.0`). |
| App-5-F8 | corrected | Confirmed. The closer upstream name is `<noun>_start` (`record_start`, `timelapse_start`, `App` upstream command list), since `record_stop` is its stop; `run_media_speed_test` is the one-shot form. Either rename is fine; `storage_preroll_start` reads closest. |
| App-5-F9 | stands | `App:12995-13001`, commit `646a194` weighs `set_iso value=N`. |

No finding added.

## Final findings

### App-5-F1 [mismatch, major] Storage switches inline the hardware-store edit three times in handleCommand

- where: `src/ApertarCoreApp.cpp:12827-12855`, `:12857-12898`, `:12900-12927 @cinemate-port`
- port way: `set_buffer_mode`, `set_frames_per_folder`/`set_clip_merge` (one block), `set_storage_preroll` each build `StoreFlags{backup, trusted=true}`, call `hardware::configStore().edit(base-or-current, {{Set,"storage"|"media",key,value}}, by, flags, hardwareConfigFacts())`, return `errorReplyBody` with `code`/`revision`/`issues` array, update `controlsErrors_`/`controlsWarnings_`, `wakeControlsWorker()`, `refreshBufferRequest()`, and reply `revision`/`written`/`apply` + `bufferSettingMembers()`. `flags.trusted` bypasses the store's text-mode-only rule for `[storage]`/`[media]`.
- Apertar way: an operator command that persists one hardware-file key calls the owning module's setter and stays a C1-I01 block: `if (!Mpu6050RecordingSession::setConfiguredDriver(*value, &errorMessage)) return errorReply(command.id, errorMessage); return okReply(command.id, imuStatusBody(false));` (`src/ApertarCoreApp.cpp:9646-9655 @upstream-1.6.0`); the owner writes the key (`writeHardwareConfigValue(config.configPath, "imu", "driver", ...)`, `src/hardware/Mpu6050RecordingSession.cpp:1295-1300 @upstream-1.6.0`). Whole-file saves go through the WebUI editor (`App:7178 @upstream-1.6.0`).
- why it matters: three copies of store plumbing (revisions, error codes, worker wakes, a bypass flag, array replies) inside four ordinary switches. The original developer sees the `set_controls` machinery where he expects a four-line setter call.
- rework: one owner function next to the buffer/storage code, e.g. `bufferbudget::saveStorageKey(section, key, value, std::string *error)`, which does the store edit with `trusted` (kept inside, with its comment), the controls counts and the worker wake. App blocks become C1-I01: check value, `if (!saveStorageKey("storage","buffer",*value,&error)) return errorReply(command.id, error); refreshBufferRequest(); return okReply(command.id, bufferSettingMembers());` (plus `clipMerge("switch")` for merge on). Drop `revision`/`written`/`issues` from these replies, or keep `revision` only if WCP uses it (check `WCP:14027-14031`). Keys stay in the hardware file: `buffer` belongs with `buffer_ram_*`/`buffer_stop_percent` and the env overrides. Moving them to `camera_settings.conf` is not recommended. Same direction as the App-2 rework.
- effort: M
- deliberate: unknown. Comment `App:12827-12828` says "through the store like set_controls (revision, history, stale and lock refusals)": the store was chosen; the inline copies were not weighed.

### App-5-F2 [mismatch, minor] set_storage_preroll takes value=on|off with its own parse; camera switches lack _enabled

- where: `src/ApertarCoreApp.cpp:12900-12906`, `:13194-13230 @cinemate-port`
- port way: `set_storage_preroll` lower-cases `value` and accepts on/off/true/false/1/0, the only on/off command with `value=` instead of `enabled=`. `set_media_trim`, `set_preview_tdn`, `set_fps_phase_lock`, `set_fps_speed_ramp` take `enabled=` but are not named `*_enabled`.
- Apertar way: C1-I05 `const bool value = (*enabled == "true" || *enabled == "1");` (`App:9482-9486 @upstream-1.6.0`), strict form where refusal matters (`App:9130-9133 @upstream-1.6.0`); argument `enabled`, command `set_<thing>_enabled`. (`parseUiSettingsBool` on arguments and a local bool lambda have upstream precedent in `apply_preset`, `App:10231-10237 @upstream-1.6.0`, so `set_value_steps` and `set_mode_ladder` are not part of this finding.)
- why it matters: one command breaks the on/off argument shape every client otherwise uses.
- rework: `set_storage_preroll` -> `set_storage_preroll_enabled enabled=` with the strict C1-I05 test; delete the tolower loop; update `ApertarControlBridge.cpp:627` and `WCP:14030`, `:15843`. Optional: rename the four camera switches to `*_enabled` (protocol change for both clients).
- effort: S
- deliberate: no

### App-5-F3 [bug, minor] get_state writes media_state twice from two snapshots

- where: `src/ApertarCoreApp.cpp:12944`, `:12961 @cinemate-port`
- port way: `:12944` streams `"media_state":` from a fresh `mediaSnapshot()`; `:12961` streams it again from `mediaState` taken at `:12935`.
- Apertar way: one key per status field, same key in `get_state` and `/api/state` (C1-R4; `App:9223-9237`, `7836-7856 @upstream-1.6.0`). The port's web state writes it once (`App:9555 @cinemate-port`).
- why it matters: `{"cmd":"get_state"}` while a card is pulled can carry two different values; which wins depends on the client's JSON parser.
- rework: delete line 12944.
- effort: S
- deliberate: no

### App-5-F4 [duplication, minor] Clip name template parsed in App and again in CC; unused out-parameter

- where: `src/ApertarCoreApp.cpp:13241-13268 @cinemate-port`; `src/camera/CameraController.cpp:11835-11866 @cinemate-port`; `src/camera/CameraController.hpp:92`
- port way: `set_clip_name_template` calls `apertar::clipname::parse` in App, then `camera_.setClipNameTemplate`, which parses again; `std::string stored` is passed and never read. `preview_clip_name` calls `camera_.previewClipName` (parses) and parses again in App for `normalized`/`corrected`.
- Apertar way: C1-I12: App checks presence, the CC setter validates and reports via `lastError()` (`App:9251-9258 @upstream-1.6.0`; `CC:7835-7849 @upstream-1.6.0`).
- why it matters: two validation points can drift; the error order differs (App's parse error comes before CC's "while recording" refusal); dead out-parameter.
- rework: App checks presence and calls `camera_.setClipNameTemplate(*value)`; `corrected = settings.clipNameTemplate != *value`. `previewClipName` returns normalized template and corrected flag with the example. Remove the `stored` parameter from the signature (only caller).
- effort: S
- deliberate: no

### App-5-F5 [mismatch, minor] set_value_steps: range table inside the branch, nested ui reply

- where: `src/ApertarCoreApp.cpp:14110-14162 @cinemate-port`; `:2160 @cinemate-port`
- port way: one command with `name=` writes up to six UI.conf keys; a `static constexpr ListKeys` table with ranges sits inside the branch; the snapshot reader repeats the ranges (`parseValueStepsList(value, 50.0, 51200.0)` at `:2160`). Reply is `"ui":{valueStepsJson(...)}`.
- Apertar way: UI.conf commands echo flat keys (`set_sleep_mode` `"sleep_mode":...`, `App:10206-10216`; `set_favorites_order` `"favorites_order":[...]`, `App:10227 @upstream-1.6.0`). Tables of allowed values are free functions in the anonymous namespace (C1-S06, `favoriteCandidateOrder()` `App:727-763 @upstream-1.6.0`). A nested `ui` group exists only in `/api/state`.
- why it matters: the reply duplicates the state's `ui` group; the ranges live in two places.
- rework: move the table to a free `valueStepsKeys(name)` beside `parseValueStepsList` and use it in the snapshot reader too. Reply flat keys of the chosen list (e.g. `"iso_steps":[...],"iso_free":...`) or plain `okReply` (WebUI polls at 1 Hz). Keep one command for the four lists. Remove `T33` (F6).
- effort: S
- deliberate: yes. Commit `b0e90ad` lays out the design (UI.conf keys, one command, "the lists and settings in the web state's ui object and in the reply").

### App-5-F6 [slop, minor] Tutorial codes and history narration in handleCommand comments

- where: `src/ApertarCoreApp.cpp:12746`, `:12810`, `:14094`, `:14111`, `:14529`, `:13285 @cinemate-port`
- port way: `// T42:`, `// T39:`, `// T34:`, `// T33:`, `// T34 (Q10):`, and "no target: both, as before".
- Apertar way: C1-I14: comments rare, state a hazard or a reason; upstream `src` has no ticket ids.
- why it matters: the codes mean nothing to the original developer; "as before" refers to a history he never saw.
- rework: delete the codes, keep the sentences; "as before" -> "no target: both".
- effort: S
- deliberate: no

### App-5-F7 [new-ground, minor] set_timecode_mode target= sets the UI timecode and the file timecode apart; not run on a Pi

- where: `src/ApertarCoreApp.cpp:13279-13300`, `:14348-14352`, `:14428-14433 @cinemate-port`
- port way: optional `target=both|ui|files`, default both. Preset key `cameraTimecodeMode` sets the file copy; legacy `timecodeMode` sets both only when the new key is absent.
- Apertar way: no precedent; upstream writes camera value and UI.conf together (`App:9424-9436 @upstream-1.6.0`), C1-I18. An unmodified client sends no target and gets the old behaviour (C1-N11).
- why it matters: UI.conf `timecodeMode` and camera `timecode_mode` can now differ, which C1-I18 otherwise rules out. Commit `909aaa5`: "Tested: desk (page loads, labels); Pi build pending".
- rework: keep the shape. Run on a Pi before the merge; document the exception to C1-I18 for the original developer.
- effort: S
- deliberate: yes. Commit `909aaa5` explains why and keeps old presets compatible.

### App-5-F8 [new-ground, nit] record_stop also ends a storage pre-roll; manual command named storage_preroll

- where: `src/ApertarCoreApp.cpp:14832-14836`, `:14603-14617`, head gate `:12591 @cinemate-port`
- port way: while a pre-roll runs, `record_stop` sets `storagePrerollStop_` and replies `"recording":false,"storage_preroll_stopped":true`. The manual action is the bare noun `storage_preroll`.
- Apertar way: `record_stop` stops whatever runs, sound take first then camera take (`App:10783-10794 @upstream-1.6.0`). Action names are verb-bearing: `record_start`, `timelapse_start`, `run_media_speed_test` (C1-I04).
- why it matters: only the name is foreign; the `record_stop` branch matches upstream's one-stop-button idea.
- rework: keep the `record_stop` branch. Rename `storage_preroll` to `storage_preroll_start` (pairs with `record_stop` as `timelapse_start`/`timelapse_stop` do) or `run_storage_preroll`; update head gate `App:12591`, `ApertarControlBridge.cpp:621`, WCP, `help`.
- effort: S
- deliberate: yes. Comment at `App:14833` states the intent; the head gate lists the command.

### App-5-F9 [new-ground, nit] set_iso_auto gains an enabled field (false = lock at measured gain)

- where: `src/ApertarCoreApp.cpp:12995-13001 @cinemate-port`; `src/camera/CameraController.cpp:11146-11166 @cinemate-port`
- port way: optional `enabled=`; false turns auto off at the gain measured inside CC.
- Apertar way: auto variants take no fields (`App:9269`, `9293`, `9308 @upstream-1.6.0`), C1-I04. A client could send `set_iso value=<iso_actual>`, but that may be one poll stale.
- why it matters: small protocol extension; no field still means auto on.
- rework: keep; reading the gain under CC's mutex is the sound place.
- effort: S
- deliberate: yes. Commit `646a194` weighs `set_iso value=N` against the lock.
