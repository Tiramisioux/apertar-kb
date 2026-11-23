# Review: HW-config-text-store (stage 2)

Refs: port = `cinemate-port` `01f170c` (`/home/user/Apertar-Core`), upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`).
`Text` = `src/hardware/HardwareConfigText.hpp`, `Store` = `src/hardware/HardwareConfigStore.{hpp,cpp}`, `App` = `src/ApertarCoreApp.cpp`,
`WCP` = `src/web/WebControlPage.cpp`. Rule ids: `conv-hardware-config.md` (HW-*) and `conv-core-command-plane.md` (C1-*).
All claims **confirmed** (read in code) unless labelled.

## 1. What upstream does

| Piece | Upstream | Ref @upstream-1.6.0 |
| --- | --- | --- |
| Readers | each class parses its own section with file-local helpers, first candidate file that configures it wins | `GpioInput.cpp:373-502`, `Mpu6050RecordingSession.cpp:851-860` (IMU: first file that opens) |
| WebUI write | `saveHardwareConfigFile`: empty / >256 KiB / NUL refused, `.bak`, `.tmp` + rename, any other text saved | `App:5323-5385`, route `App:7175-7193` |
| WebUI read | `buildHardwareConfigFileJson`, template when missing | `App:5290-5320`, `App:7168-7173` |
| IMU write | one-key line editor, keeps comments and order, replaces the key in every copy of the section, writes the file the loader found | `Mpu6050RecordingSession.cpp:604-713`, callers `:1148`, `:1300`, `:1363` |
| Lock / atomic write for settings | `settingsFile::QtIniLock`, `atomicWrite` (UI.conf) | `src/util/SettingsFile.hpp:36-60` |
| Validation | none; lenient readers (HW-N7) | |

## 2. Findings

| Id | Sev | Category | Title |
| --- | --- | --- | --- |
| F1 | major | removed-upstream-behaviour | Config page save refused on new validator errors; WebUI has no override |
| F2 | major | removed-upstream-behaviour | `[run_script]` paths refused from the browser; also blocks Undo and restore |
| F3 | major | new-ground | `hwconf` is a second, table-driven model of every reader in a 1141-line header; already drifted |
| F4 | minor | bug | Key edit on a duplicated section writes the copy the readers ignore (IMU, storage switches) |
| F5 | minor | bug | `set_controls text=` skips the upstream empty/size/NUL checks: `text=` empty writes an empty file |
| F6 | minor | bug | IMU write on a /boot-only rig creates a partial `/home/pi` file that hides the /boot file from the IMU |
| F7 | minor | new-ground | Store merge-review path (`textToEdits`, `needsReview`, `confirmMerge`) has no in-tree caller |
| F8 | minor | protocol | `POST /api/config` without `X-Apertar-Revision` from a browser: 409 instead of save |
| F9 | minor | mismatch | `StoreResult.code` machine codes and issue arrays in error replies |
| F10 | minor | mismatch | `src/hardware/` header includes capture-pipeline `util/` headers (HW-S8) |
| F11 | minor | duplication | Second config.txt parser + sudo command builder; BootConfigText already has one |
| F12 | minor | pi-compat | `parseConfigTxt` applies only `[all]`/`[pi5]` (same as App-2-F12) |
| F13 | minor | slop | Owner name, T44, out-of-tree `core.py`, history narration, "(unconfirmed on hardware)" in operator text |
| F14 | minor | duplication | Four storage handlers repeat the store.edit block; two copies of the post-write block |
| F15 | nit | bug | `by` written raw into `hardware-state.conf`; 100 ms sleep under the store mutex on each save of a hand-edited file |

### F1 Config page save blocked on new errors (removed-upstream-behaviour, major, deliberate yes)
- Port: `Store.cpp:336-342` refuses when `newErrors` is non-empty and `!flags.force`. `POST /api/config` never sets `force` (`App:8640-8642@cinemate-port`); the page has no "save anyway" (`WCP:18910-18955@cinemate-port`, no `force` in WCP). Error rules include things the C++ readers tolerate: `junk`, `duplicate_key`, `unknown_action` ("Core logs it and does nothing"), `gpio_twice`, `gpio_i2c1`, `address_range`, `header_text` (`Text:756-1009`).
- Upstream: any text that is non-empty, <=256 KiB, NUL-free is saved (`App:5323-5385@upstream-1.6.0`). HW-N7: "Be lenient with the operator's file ... A violation: refusing to start on an unknown key; strict schema validation." HW-N3: the raw textarea is the operator's surface.
- Failing input: page text adds `d17=record_toggle` while `d17` is also `[trigger_output] line=17` default, or a key `foo` above the first section: 400, nothing saved, no override in the browser.
- Deliberate: yes (design-controls.md T37, "Save blocked on new errors only").
- Rework: `HardwareConfigStore::replace` (text path) never blocks on validation; it returns `issues`, the page shows them after a save (the success branch already does, `WCP:18938-18940`). Keep the block for key edits (`edit`, easy mode) only. Delete `newErrors` use in the text path. Effort S.

### F2 `[run_script]` paths ssh-only (removed-upstream-behaviour, major, deliberate yes)
- Port: `Store.cpp:330-335` refuses any save whose non-empty `[run_script] path*` differ ("Script paths are changed over ssh, not here.").
- Upstream: the WebUI writes the whole file, scripts included (`App:7175-7193@upstream-1.6.0`); C1-N10 trusted LAN; HW-N3 lists scripts among the file's operator keys.
- Bug inside it: Undo sends a history version as `set_controls text=` (`WCP:18583-18588@cinemate-port`) and `restore=true` sends the remembered version (`App:12767-12776`); both go through the same check, so a version with other script paths cannot be put back. Failing input: last save had `path1=/home/pi/a.sh`, file replaced by a default without it -> restore refused.
- Deliberate: yes (decisions.md Q2, "ssh only").
- Rework: delete `scriptPaths()` and the check (upstream trust model). If the owner keeps Q2, exempt Undo/restore and say so in the README. Effort S.

### F3 `hwconf` second model of the readers (new-ground, major, verdict simplify, deliberate yes)
- Port: `kSections[]` alias lists, `ValueRule`, default buses, on-defaults (`Text:27-69`); `canonicalSection`, `canonicalKey`, `canonicalEncoderKey` (`Text:91-208`); 1141 lines, all `inline` in a header.
- Upstream: HW-S2 (always) "no shared parser ... A violation: a new HardwareConfig / INI library class all devices call"; HW-I1 "a lookup table/map of aliases, a schema" is the listed violation; aliases live as `key == "a" || key == "b"` in each reader (`Pcf8574Input.cpp:366-371@upstream-1.6.0`). C1-S06 allows a *small* header next to its owner (`PowerButtonGesture.hpp`).
- Drift already present: `canonicalKey` maps `pcf_bus`, `bus_number`, `channel`, `i2c_bus` to `bus` and `pcf_address` to `address` for every section (`Text:169-170`). `Pcf8574Input.cpp:273@cinemate-port` accepts only `bus|channel|i2c_bus`; `Mpu6050RecordingSession.cpp:762@cinemate-port` only `bus|bus_number`. `[pcf8574] pcf_bus=10`: validator checks bus 10, reader uses bus 1. `[mpu6050] channel=3`: validator bus 3, reader ignores it.
- Not a mismatch for the editing core: the readers still parse their own sections (confirmed, no `configStore()` in any driver), and line-preserving edits generalise upstream's IMU editor (HW-S6).
- Rework: (1) split into `HardwareConfigText.hpp` (types) + `.cpp`, add to `CMakeLists.txt` by name (HW-S9); (2) make `canonicalKey` per section only, each branch a flat `key == ...` chain with a comment naming the reader line it mirrors; drop the global alias lines 169-172; (3) keep `parse/join/applyEdit/diff/validate`; validator stays advisory for text (F1). Effort M.

### F4 Edit on duplicated section misses (bug, minor)
- Port: `applyEdit` replaces the key only inside the first copy and stops at the second header (`Text:541-550`, `if (L[i].kind == Kind::Section && i != *firstHeader) break;`). Readers take the later line (`Text:330-331` says so). `checkEdits` refuses duplicates (`Text:491-495`) but `trusted` writes skip it (`Store.cpp:298`, `:312`): IMU (`Mpu6050RecordingSession.cpp:617-619@cinemate-port`) and `set_buffer_mode`/`set_frames_per_folder`/`set_clip_merge`/`set_storage_preroll` (`App:12839`, `:12879`, `:12913`).
- Upstream: `writeHardwareConfigValue` sets `inTargetSection` at every header of that name and rewrites the key in each copy (`Mpu6050RecordingSession.cpp:636-664@upstream-1.6.0`).
- Failing input: `[mpu6050]` twice, the second with `gyro_bias_x=12`; `calibrate_gyro` -> reply ok, first copy gets the new bias, the reader keeps 12. Same for `[storage]` twice and `set_buffer_mode`.
- Rework: in `applyEdit` Set, replace the key in every copy of the section (upstream behaviour); insert only when no copy has it. Effort S.

### F5 `set_controls text=` without the upstream checks (bug, minor)
- Port: `set_controls` passes `text` straight to `replace` (`App:12763-12799@cinemate-port`); `checkHardwareConfigText` runs only in `POST /api/config` (`App:8623`).
- Upstream: the three checks guard every whole-file write (`App:5325-5343@upstream-1.6.0`).
- Failing input: `{"cmd":"set_controls","base":"<current>","text":""}` -> empty file written; next start `replacedByDefault` reports it as missing/empty.
- Rework: move the three checks into `HardwareConfigStore::replace` (one place for every caller) and delete `checkHardwareConfigText`. Effort S.

### F6 IMU write on a /boot-only rig (bug, minor, deliberate yes)
- Port: IMU writes always go to `configStore().path()` (`Mpu6050RecordingSession.cpp:605-623@cinemate-port`, comment "not whichever file the loader found"). The store ignores `/boot` (inventory 7).
- Upstream: writes `config.configPath`, the file the loader read (`Mpu6050RecordingSession.cpp:610`, `:1148`, `:1300@upstream-1.6.0`); IMU `loadConfig` takes the first file that opens (`:854-860`).
- Failing input: only `/boot/firmware/apertar-hardware.conf` exists, with `[imu] enabled=true driver=bmi270`. `calibrate_gyro` creates `/home/pi/apertar-hardware.conf` holding only `[bmi270]` bias keys. Next IMU load opens `/home/pi` first: `[imu]` gone, IMU off/default driver. Config page now shows the partial file instead of `boot_copy`.
- Rework: in `saveLocked`, when the editable file does not exist and a /boot copy does, start `current` from that copy (the rule `buildHardwareConfigFileJson` already applies, `App:6189-6200`). Effort S.

### F7 Merge-review path without in-tree caller (new-ground, minor, verdict simplify)
- Port: `textToEdits` (`Text:1103-1139`), `StoreResult.merged/needsReview`, `StoreFlags.confirmMerge` (`Store.hpp:21`, `:28-29`; `Store.cpp:282-310`, `:344-348`). `POST /api/config` turns `needsReview` into 409 `merge_review` (`App:8644-8649`); WCP never sends `confirm_merge` (grep: 0 hits). Only the out-of-tree `core.py` can complete it.
- Upstream: no precedent; last writer wins.
- Rework: delete `textToEdits`, `merged`, `needsReview`, `confirmMerge`; a stale text save is `stale`. Keep per-key merge for key edits (`conflicts`), which easy mode uses. Effort S.

### F8 409 for a page without the revision header (protocol, minor)
- Port: `App:8630-8636@cinemate-port`: header missing and `Origin` present -> 409 `old_page`. Script without `Origin` keeps last-writer-wins.
- Upstream: no header, always saved (`App:7175@upstream-1.6.0`).
- Effect: only a WebUI tab opened before the update, or another page posting the file. Error reply keeps `ok`/`error`, so an unmodified client shows the sentence.
- Rework: missing header = base is the current revision for every client (upstream behaviour); check the revision only when the header is present. Effort S.

### F9 Codes and arrays in refusals (mismatch, minor)
- Port: `StoreResult.code` (`locked`, `being_written`, `stale`, `conflict`, `edits`, `errors`, `script_paths`, `backup`, `write`, `Store.hpp:30`) and `issues`/`new_errors`/`conflicts` arrays sent with `errorReplyBody` (`App:8650-8654`, `:12801-12806`, `:12841-12843`).
- Upstream: C1-I06 replies only from `okReply`/`errorReply`; C1-I07 "Error codes" is a listed violation; C1-N02 the sentence is shown as written.
- Overlap: App-1 `errorReplyBody` finding. Here: the store needs `code` only for the HTTP status; WCP branches on `code` only to append "Your text stays in the box" (`WCP:18947-18949`).
- Rework: store returns `bool` + `std::string *errorMessage` + `bool stale` (C1-I10); App maps stale to 409; issues go in the ok reply / `get_controls`. Effort M (touches WCP).

### F10 Hardware header includes capture code (mismatch, minor)
- Port: `Text:5-6` includes `util/BufferBudget.hpp`, `util/StoragePreroll.hpp` for the `[storage]`/`[media]` rules (`Text:800-815`); `Store.cpp:3` includes `util/SettingsFile.hpp`.
- Upstream: HW-S8 (always) hardware headers include only hardware headers (`grep '#include "' src/hardware/*@upstream-1.6.0`: hardware only).
- Rework: App appends the `[storage]`/`[media]` issues after `hwconf::validate` (App already owns `refreshBufferRequest`). `SettingsFile.hpp` use is the upstream lock and can stay if the store moves next to its owner App, or is accepted as a util include. Effort S.

### F11 Two config.txt parsers (duplication, minor)
- Port: `Text:1029-1101` `parseConfigTxt`, `dpiCommands` (sudo cp/sed/reboot lines). `BootConfigText.hpp:248@cinemate-port` "Same rule as HardwareConfigText's parseConfigTxt" and has its own `dpiOverlays` (`:497`, `:580`).
- Upstream: no config.txt parsing in the hardware path.
- Rework: delete both from `Text`; `hardwareConfigFacts()` uses `BootConfigText`. Effort S.

### F12 Board filter (pi-compat, minor)
- `Text:1037`, `:1051`: only `[all]`/`[pi5]` apply. `[cm5]`, `[pi4]`, `[cm4]` blocks ignored; `[pi5]` lines applied on Pi 4. Already App-2-F12; fixed by F11 if `BootConfigText` honours the board. HW-N4: auto-detect, no Pi-5-only path.

### F13 Slop (minor)
| Where | Text |
| --- | --- |
| `Text:1082` | "The commands the I2C card shows for Patrik to run" |
| `Text:116` | "Gesture suffixes (T44)" |
| `Text:317`, `Store.hpp:3`, `Store.hpp:20` | `core.py` (not in either tree) |
| `Store.cpp:62` | "the text the touch UI used to write" (history narration) |
| `Text:1006` | operator message "(unconfirmed on hardware)" |
| `App:8117`, `:8136`, `:8662`, `:12796` (callers) | `T37`, `T39`, `T42` |
C1-I14: comments are rare sentences stating a hazard or reason, no ticket numbers. Rework: drop the names and numbers, reword. Effort S.

### F14 Repeated store blocks (duplication, minor)
- `App:12829-12925`: four handlers each build `StoreFlags{backup,trusted}`, call `store.edit`, map the refusal, update `controlsErrors_`/`controlsWarnings_`, wake the worker. `set_controls` and `POST /api/config` repeat the post-write block (`App:8655-8660`, `:12808-12813`).
- C1-I17: a repeated shape becomes a local lambda or one helper. Rework: one member `writeStorageKey(section, key, value, base, by, std::string *error)` and one `afterHardwareWrite(result)`. Effort S.

### F15 Small store edges (bug, nit)
- `writeStateLocked` writes `by` unfiltered (`Store.cpp:410-413`); `by` comes from the client (`App:12796`). `by="x\nwritten_revision=h0"` adds a line that the ctor parses (`Store.cpp:102-115`). History names use `safeName`, the state file does not. Rework: `safeName(by)` there too.
- `settledLocked` sleeps 100 ms holding `mutex_` on every save while the file is not Core's own write (`Store.cpp:198-209`), IMU writes included.

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| namespace `hwconf` | simplify | F3: split .hpp/.cpp, per-reader alias branches, advisory for text |
| `kSections`/`SectionInfo`/`ValueRule` | simplify | F3: a schema table is HW-I1's listed violation; keep only what the editor needs (order, easy flag), comment rules cite the reader |
| `Edit`, `Issue`, `Facts` | keep | small value types for the editor and validator |
| `Conflict` | keep | used by key-edit merge (easy mode) |
| `BootFacts`, `parseConfigTxt`, `dpiCommands` | rework-to-upstream-pattern | F11, F12: one config.txt parser in BootConfigText |
| `textToEdits` | simplify (delete) | F7 |
| `HardwareConfigStore` | keep | several writers (WebUI text, easy mode, IMU, storage switches) need one lock + atomic write; reuses upstream `QtIniLock`/`atomicWrite` |
| `configStore()` function-local static | keep | upstream keeps process-wide state as file statics in the owning `.cpp` (C1-I19, `Mpu6050RecordingSession.hpp:77-82@upstream-1.6.0`); IMU write functions are static and have no App reference. Disagrees with App-4-F6 (member): plumbing a reference into static IMU calls buys nothing |
| `StoreFlags`/`StoreResult` | simplify | drop `confirmMerge`, `merged`, `needsReview` (F7), codes (F9) |
| revision `h<16hex>` | keep | needed for stale detection; small |
| history dir, adopted pin, last-written, state file | keep (history, adopted) / simplify (state + last-written) | Undo and restore stand on history + adopt (`014fa22`, App-2-F11 challenge). `hardware-last-written.conf` repeats the newest written text; state + last-written could be one file |
| controls worker thread | out of unit | contradicts HW-N1 (restart needed); judged in App units |
| `hardwareConfigFacts()` | keep | thin I/O shim keeps the header pure |
| `controlsIssuesJson`/`errorReplyBody` | rework-to-upstream-pattern | F9, App-1 |

## 4. Conforms

- Readers untouched: every driver still parses its own section (HW-S2); the store is not a read path for drivers (inventory 5, confirmed by grep: no `configStore()` in drivers).
- Programmatic edits keep comments, order, indentation (HW-S6), as upstream's IMU editor did (`Text:519-585`).
- Reuses upstream `settingsFile::QtIniLock` and `atomicWrite` unchanged (`Store.cpp:257-260`, `:366`), the UI.conf idiom (C1-S16).
- Writes only the editable path, env or `/home/pi` (HW-S10, `Store.cpp:118-123`); never `/boot`.
- `.bak` kept for WebUI saves (`Store.cpp:357`), as `App:5357@upstream-1.6.0`.
- Upstream routes kept in place, flat `if` in `handleWebRequest` (C1-S10); upstream reply keys `path`, `display_path`, `backup_path`, `backup_display_path` kept (`App:8662-8666`).
- Upstream checks (empty, size, NUL) kept as `checkHardwareConfigText` (`App:6227-6248`).
- `Text` header does no I/O; `Facts` injected.
- Logging `std::cerr` with `ApertarCore controls:` prefix (C1-I13, `App:8150`).
- History file names filtered with `safeName`; `historyText` only serves names from the listing (no path traversal, `Store.cpp:491-497`).
- New file mode 0644 kept.

## Skeptic

Every port line was re-read at `cinemate-port` and every upstream line at `upstream-1.6.0`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Confirmed: `Store.cpp:336-342`, no `force` from `App:8640-8642` or WCP. One correction: `junk`, `key_above`, `duplicate_section` and `duplicate_key` (`Text:758-792`) are grounded in a real upstream reader. That reader is the NVMe helper, which uses Python configparser and catches only OSError (`App:3437-3447@upstream-1.6.0`). Upstream still saved such files. The rework stands; the message should keep naming the helper as a warning. |
| F2 | stands | Confirmed `Store.cpp:34-42,330-335`. Upstream writes the whole file (`App:7175-7193@upstream-1.6.0`). Undo (`WCP:18583-18588`) is refused when an ssh path edit came after the last Core save. Restore is refused when a default dropped the paths. Q2 is in `decisions.md:10`. |
| F3 | stands | Confirmed `Text:27-69`, `Text:169-170` (global `channel/i2c_bus/bus_number/pcf_bus` -> bus, `pcf_address` -> address). Drift confirmed: `Pcf8574Input.cpp:273` takes `bus/channel/i2c_bus` only, and `Mpu6050RecordingSession.cpp:762` takes `bus/bus_number` only. Upstream keeps flat chains per reader: `Pcf8574Input.cpp:366-371`, plus `pcf_bus` only in `TriggerOutput.cpp:320` and `RecordingIndicatorOutput.cpp:359`. |
| F4 | stands | Confirmed `Text:541-550` (`break` at the second header). Upstream `Mpu6050RecordingSession.cpp:634-660@upstream-1.6.0` rewrites the matching key in every copy, because the match branch does not test `wroteKey`. The trusted IMU path is at `Mpu:617`; the storage paths are at `App:12837,12877,12911`. |
| F5 | stands | Confirmed: `set_controls` (`App:12763-12799`) never calls `checkHardwareConfigText` (`App:6227`). `replace` has no empty, size or NUL check. |
| F6 | corrected | Confirmed. The impact is wider than the IMU: every reader takes the first candidate that exists (for example `Pcf8574Input.cpp:230-232`), so all `/boot` sections are hidden. Correction: upstream IMU wrote `config.configPath`, which can be the `/boot` file itself. Upstream did write `/boot` in that case. |
| F7 | stands | `confirm_merge` is parsed only at `App:12791`. It has 0 hits in WCP, in the UI and in tools. POST `/api/config` turns `needsReview` into 409 `merge_review` (`App:8644-8649`), which the page treats like `stale` (`WCP:18948`). |
| F8 | stands | Confirmed `App:8630-8638`. |
| F9 | corrected | Confirmed. WCP branches on `code` in three places, not one: `WCP:18233`, `:18661`, `:18948`. Upstream has no `"code"` member anywhere in `App@upstream-1.6.0` (grep: 0 hits). |
| F10 | stands | Confirmed `Text:5-6`. `BufferBudget.hpp` also pulls `cdng/FramePath.hpp` (`:24`) and holds a function-static `safetyStopState()` (`:231-233`). Upstream `src/hardware/*` quoted includes are hardware-only (grep: 0 others). |
| F11 | corrected | Most of it is dead code. `dpiCommands`, `BootFacts.i2cArm` and `BootFacts.dpiOverlays` have no caller (grep over `src` and `tools`). The only consumer is `App:4976`, which uses `.dpiLines`. `BootConfigText` already has the board-aware filter (`BootConfigText.hpp:102-117`). |
| F12 | corrected | The bug is real (`Text:1051`). The rework was wrong: the board-aware `filterApplies` already exists in `BootConfigText.hpp:102-117`, so the fix is F11 (use BootConfigText) and nothing new is needed. |
| F13 | corrected | Confirmed lines. Added `// T39` at `App:8658` and `App:12811`. Narrowed `Store.cpp:62`: upstream UI really writes that template (`ui-upstream/src/DisplayConfigBridge.cpp:58`, `Ina219Bridge.cpp:86`), so the comment is a valid reason. Only "used to" is port-frame narration. |
| F14 | corrected | Three blocks cover four commands. The claimed drift was wrong: all three storage blocks call `refreshBufferRequest()` unconditionally and wake only on `written` (`App:12844-12849`, `:12884-12889`, `:12918-12923`). The real difference is from `set_controls`/POST, which refresh only on `written`. Per C1-I17 the shape belongs in a local lambda in `handleCommand`. |
| F15 | corrected | The injection is confirmed (`Store.cpp:101-114`: the last line wins). The sleep runs only when the file is over 1 s old and not Core-written (`Store.cpp:198-209`), so the proposed "only when under 1 s old" was backwards. The age check already covers an editor mid-save, so the sleep can go. |

No new findings.

## Final findings

### HW-config-text-store-F1 [removed-upstream-behaviour, major] The Config page's text save is refused on new validator errors, and the WebUI has no override
- where: `src/hardware/HardwareConfigStore.cpp:336-342`, `src/ApertarCoreApp.cpp:8640-8642`, `src/web/WebControlPage.cpp:18910-18955`, `src/hardware/HardwareConfigText.hpp:756-1009` (@cinemate-port)
- port way: `saveLocked` validates the current text and the next text and refuses when `newErrors` is non-empty unless `flags.force` is set. POST `/api/config` never sets `force`, and the page has no "save anyway". Error rules include cases the C++ readers tolerate: `duplicate_key` (the later line wins), `unknown_action`, `gpio_twice`, `address_range`, `header_text`. Some rules (`junk`, `key_above`, `duplicate_section`, `duplicate_key`) guard the Python NVMe helper.
- Apertar way: `saveHardwareConfigFile` saves any text that is non-empty, at most 256 KiB and NUL-free (`src/ApertarCoreApp.cpp:5323-5385@upstream-1.6.0`), even though upstream's own NVMe helper (`App:3437-3447@upstream-1.6.0`, configparser, catches only OSError) would stop on some of them. HW-N7: be lenient with the operator's file. HW-N3: the raw textarea is the operator's surface.
- why it matters: The original developer's Config textarea can no longer save files the readers accept. Example: a button on a pin that is already claimed. The reply is 400, nothing is saved, and the browser offers no way round it.
- rework: In `HardwareConfigStore::saveLocked`, the text path (`replace`) never blocks on validation: write the file, then return the issues. The page already shows issues after a successful save (`WCP:18938-18940`). Keep the warnings that name the NVMe helper. Keep the `newErrors` block only for key edits (`edit()`, easy mode).
- effort: S. deliberate: yes. Evidence: `design-controls.md:562`, `:857` and fork-log "Save blocked on new errors only, force overrides".

### HW-config-text-store-F2 [removed-upstream-behaviour, major] The browser cannot change [run_script] paths, and the same check blocks Undo and restore
- where: `src/hardware/HardwareConfigStore.cpp:34-42`, `:330-335`, `src/web/WebControlPage.cpp:18583-18588`, `src/ApertarCoreApp.cpp:12767-12776` (@cinemate-port)
- port way: Any save whose non-empty `[run_script] path*` keys differ from the current file is refused with "Script paths are changed over ssh, not here." The check also runs for Undo (`set_controls text=<history version>`) and for `restore=true`.
- Apertar way: The WebUI writes the whole file, `[run_script]` included (`src/ApertarCoreApp.cpp:7175-7193@upstream-1.6.0`). C1-N10: the WebUI is for a trusted LAN. HW-N3 lists the scripts among the file's operator keys.
- why it matters: An upstream capability is gone. The check also breaks the port's own recovery. Undo is refused after any ssh path edit made since the last Core save. Restore is refused after a default file dropped the paths.
- rework: Delete `scriptPaths()` and the check in `saveLocked` (the upstream trust model). If the owner keeps decision Q2, exempt Undo and restore and document the rule in the README.
- effort: S. deliberate: yes. Evidence: `working/controls/decisions.md:10` Q2, "[run_script] paths: ssh only".

### HW-config-text-store-F3 [new-ground, major] hwconf is a second, table-driven model of every reader in one 1141-line header, and it has already drifted
- where: `src/hardware/HardwareConfigText.hpp:27-69`, `:157-208`, `:169-170` (@cinemate-port)
- port way: `kSections[]` holds per-section alias strings, a `ValueRule`, a default bus and on-defaults. `canonicalSection`, `canonicalKey` and `canonicalEncoderKey` form one shared alias map. Global lines map `channel/i2c_bus/bus_number/pcf_bus` to `bus` and `addr/pcf_address` to `address` for every section. All of it is inline in one header.
- Apertar way: HW-S2: there is no shared parser, and "a new HardwareConfig / INI library class" is the listed violation. HW-I1: aliases are flat `key ==` chains in each reader (`src/hardware/Pcf8574Input.cpp:366-371@upstream-1.6.0`). `pcf_bus`/`pcf_address` exist only in `TriggerOutput.cpp:320-323` and `RecordingIndicatorOutput.cpp:359-362@upstream-1.6.0`. C1-S06: only small header-only files sit next to their owner.
- why it matters: Every reader's rules exist twice, and they have drifted. `Pcf8574Input.cpp:273@cinemate-port` takes only `bus/channel/i2c_bus`, so for `[pcf8574] pcf_bus=10` the validator checks bus 10 while the reader uses bus 1. `Mpu6050RecordingSession.cpp:762@cinemate-port` takes only `bus/bus_number`, so for `[mpu6050] channel=3` the validator checks bus 3 while the reader ignores the key. Every alias needs two edits.
- rework: Split the header into `HardwareConfigText.hpp` (types) and a `.cpp` registered in CMakeLists (HW-S9). Make `canonicalKey` per section only: each branch is a flat `key ==` chain with a comment citing the reader line it mirrors. Delete the global lines 169-170. Keep parse, join, applyEdit, diff and validate. The validator stays advisory for text saves (F1).
- effort: M. deliberate: yes. Evidence: `design-controls.md` T37, "a validator built from what each reader really does"; risk R14 "validator and a reader disagree" is named there.

### HW-config-text-store-F4 [bug, minor] A key edit on a duplicated section writes the copy the readers ignore
- where: `src/hardware/HardwareConfigText.hpp:541-550`, `src/hardware/HardwareConfigStore.cpp:298`, `:312`, `src/hardware/Mpu6050RecordingSession.cpp:605-623`, `src/ApertarCoreApp.cpp:12829-12925` (@cinemate-port)
- port way: `applyEdit` Set replaces the key only inside the first copy of the section and stops at the second header. The readers use the later line. `checkEdits` refuses duplicates, but trusted writes skip `checkEdits`: IMU calibration and orientation, `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge` and `set_storage_preroll`.
- Apertar way: `writeHardwareConfigValue` re-enters the target section at every header of that name and rewrites the key in each copy (`src/hardware/Mpu6050RecordingSession.cpp:628-668@upstream-1.6.0`).
- why it matters: Take a file with `[mpu6050]` twice, the second copy holding `gyro_bias_x=12`. `calibrate_gyro` replies ok and writes the new bias into the first copy, but the reader keeps 12. The same happens with `[storage]` twice and `set_buffer_mode`. Upstream did not have this bug.
- rework: In `applyEdit` Set, replace the key in every copy of the section, as upstream did. Insert a new line only when no copy has the key.
- effort: S. deliberate: no.

### HW-config-text-store-F5 [bug, minor] set_controls text= skips the upstream empty, size and NUL checks
- where: `src/ApertarCoreApp.cpp:12763-12799`, `:6227-6248` (@cinemate-port)
- port way: `checkHardwareConfigText` runs only in POST `/api/config`. `set_controls` passes `text=` straight to `store.replace`.
- Apertar way: The three checks guard the one whole-file write (`src/ApertarCoreApp.cpp:5325-5343@upstream-1.6.0`).
- why it matters: `{"cmd":"set_controls","base":"<current>","text":""}` writes an empty file. Every reader then falls back to its defaults.
- rework: Move the three checks into `HardwareConfigStore::replace` so every caller gets them, and delete `checkHardwareConfigText`.
- effort: S. deliberate: no.

### HW-config-text-store-F6 [bug, minor] An IMU write on a /boot-only rig creates a partial /home/pi file that hides the /boot file from every reader
- where: `src/hardware/Mpu6050RecordingSession.cpp:605-623`, `src/hardware/HardwareConfigStore.cpp:154-163`, `:276-320` (@cinemate-port)
- port way: IMU writes always go to `configStore().path()`. When that file is absent, the store starts from empty text (`refreshLocked` clears `text_`).
- Apertar way: The IMU writes `config.configPath`, the file the loader read, which can be the `/boot` file (`src/hardware/Mpu6050RecordingSession.cpp:610`, `:1148`, `:1300`, loader `:854-860@upstream-1.6.0`). Every reader takes the first candidate that exists (env -> `/home/pi` -> `/boot/firmware` -> `/boot`).
- why it matters: Take a rig where only `/boot/firmware/apertar-hardware.conf` exists, holding `[imu]`, the buttons and so on. `calibrate_gyro` creates `/home/pi/apertar-hardware.conf` with only the bias keys. On the next start every reader (`Pcf8574Input.cpp:230-232`, the IMU, GPIO and others) opens that file and loses the `/boot` sections. The Config page then shows the partial file instead of `boot_copy`.
- rework: In `saveLocked`, when the editable file does not exist and a `/boot` copy does, start `current` from the `/boot` copy. `buildHardwareConfigFileJson` already applies this rule (`App:6187-6200`). The write still goes only to the editable path (HW-S10).
- effort: S. deliberate: yes. Evidence: the comment at `Mpu6050RecordingSession.cpp:605-606@cinemate-port`, and inventory section 7.

### HW-config-text-store-F7 [new-ground, minor] The text merge-review path has no in-tree caller
- where: `src/hardware/HardwareConfigText.hpp:1103-1139`, `src/hardware/HardwareConfigStore.hpp:21`, `:28-29`, `src/hardware/HardwareConfigStore.cpp:289-310`, `:344-348`, `src/ApertarCoreApp.cpp:8644-8649`, `:12791` (@cinemate-port)
- port way: A stale text save that changed only values becomes key edits (`textToEdits`) and comes back with `needsReview`. Writing it needs `confirm_merge`. No client in the tree sends `confirm_merge`: 0 hits in WCP, the UI and tools. POST `/api/config` turns `needsReview` into 409 `merge_review`, which the page treats like `stale` (`WCP:18948`).
- Apertar way: No precedent. Upstream is last-writer-wins with a `.bak`.
- why it matters: About 60 lines plus flags and reply fields serve a client that is not in the tree. The original developer cannot exercise the path.
- rework: Delete `textToEdits`, `StoreResult.merged/needsReview` and `StoreFlags.confirmMerge`. A stale text save returns stale. Keep the per-key `conflicts()` for easy-mode key edits.
- effort: S. deliberate: yes. Evidence: commit `f5a61b8`, `design-controls.md` T37/T38.

### HW-config-text-store-F8 [protocol, minor] POST /api/config from a browser without X-Apertar-Revision gets a 409
- where: `src/ApertarCoreApp.cpp:8628-8638` (@cinemate-port)
- port way: A missing header with an `Origin` present gives 409 with code `old_page`. A request without `Origin` keeps last-writer-wins.
- Apertar way: There is no header; the request is always saved when sane (`src/ApertarCoreApp.cpp:7175-7193@upstream-1.6.0`).
- why it matters: Only tabs opened before the update, and other pages posting the file, are hit. Behaviour that depends on `Origin` is new and surprising.
- rework: A missing header means base = the current revision for every client (upstream behaviour). Check the revision only when the header is present.
- effort: S. deliberate: yes. Evidence: commit `5395fa4`, comment at `App:8628-8629`.

### HW-config-text-store-F9 [mismatch, minor] StoreResult machine codes and issue arrays in error replies
- where: `src/hardware/HardwareConfigStore.hpp:25-38`, `src/ApertarCoreApp.cpp:8650-8654`, `:12801-12806`, `:12841-12843`, `:12881-12883`, `:12915-12917`, `src/web/WebControlPage.cpp:18233`, `:18661`, `:18948` (@cinemate-port)
- port way: Refusals carry a `code` (locked, being_written, stale, conflict, edits, errors, script_paths, backup, write) plus `issues`, `new_errors` and `conflicts` arrays of objects, all through `errorReplyBody`. WCP branches on `code` in three places to append "stays on the page / in the box".
- Apertar way: C1-I06: replies come only from `okReply`/`errorReply`. C1-I07: "error codes" is a listed violation, and upstream App has 0 `"code"` members. C1-I10: a fallible helper returns bool and writes `std::string *errorMessage` (`saveHardwareConfigFile`, `src/ApertarCoreApp.cpp:5323@upstream-1.6.0`). C1-N02: the sentence is shown as written.
- why it matters: This is a second error protocol next to the operator sentence. The code list and three WCP branches have to stay in step. It overlaps App-1 `errorReplyBody`.
- rework: `saveLocked` returns bool, writes `std::string *errorMessage` and sets a `bool *stale` out-flag. App maps stale to HTTP 409 (and puts the "stays on the page" sentence into the message) and replies with `errorReply`. Issues go only in ok replies and in `get_controls`. Drop the three WCP `code` branches.
- effort: M. deliberate: unknown.

### HW-config-text-store-F10 [mismatch, minor] A src/hardware header includes capture-pipeline util headers
- where: `src/hardware/HardwareConfigText.hpp:5-6`, `:800-815` (@cinemate-port)
- port way: The validator includes `util/BufferBudget.hpp` and `util/StoragePreroll.hpp` to check the `[storage]` and `[media]` values. `BufferBudget.hpp` in turn pulls `cdng/FramePath.hpp` (`:24`) and holds the process-wide `safetyStopState()` (`:231-233`).
- Apertar way: HW-S8: hardware headers include only hardware and standard headers, and the app is reached through callbacks. A grep for quoted includes in `src/hardware/*@upstream-1.6.0` finds hardware headers only.
- why it matters: The hardware layer gains a dependency on capture-pipeline and CinemaDNG code.
- rework: Delete the storage/media branches from `validate()`. App appends the `bufferConfProblem`/`prerollConfProblem` issues after `hwconf::validate`, inside `hardwareConfigFacts`'s caller, next to `refreshBufferRequest`.
- effort: S. deliberate: no.

### HW-config-text-store-F11 [duplication, minor] A second config.txt parser, mostly dead, duplicates BootConfigText
- where: `src/hardware/HardwareConfigText.hpp:1029-1101`, `src/ApertarCoreApp.cpp:4976`, `src/hardware/BootConfigText.hpp:102-117`, `:248` (@cinemate-port)
- port way: hwconf has its own `parseConfigTxt`, `BootFacts` and `dpiCommands` (sudo cp/sed/reboot lines). `dpiCommands`, `BootFacts.i2cArm` and `BootFacts.dpiOverlays` have no caller in `src` or `tools`. The only consumer is `App:4976`, which uses `.dpiLines`. `BootConfigText.hpp:248` says "Same rule as HardwareConfigText's parseConfigTxt".
- Apertar way: No precedent. Upstream has no config.txt parsing in the hardware path.
- why it matters: Two copies of the firmware-filter rules already differ: BootConfigText is board-aware and hwconf is not (F12). Dead code also names a person (F13).
- rework: Delete `parseConfigTxt`, `BootFacts` and `dpiCommands` from HardwareConfigText. `hardwareConfigFacts()` (`App:4976`) takes the DPI line numbers from BootConfigText's parse, which already applies `filterApplies`.
- effort: S. deliberate: no.

### HW-config-text-store-F12 [pi-compat, minor] parseConfigTxt applies only [all] and [pi5] blocks
- where: `src/hardware/HardwareConfigText.hpp:1037`, `:1051` (@cinemate-port)
- port way: `applies = filter == "[all]" || filter == "[pi5]"`.
- Apertar way: HW-N4 / HW-I7: Pi 5 first, Pi 4/3 through auto-detection, and no Pi-5-only path (`src/hardware/GpioInput.cpp:247-253@upstream-1.6.0`). The port's own `BootConfigText::filterApplies` (`BootConfigText.hpp:102-117`) already handles pi5, cm5, pi4, cm4, pi3 and the others.
- why it matters: On a CM5, a DPI overlay under `[cm5]` is missed. On a Pi 4 or CM4, `[pi5]` lines are applied and `[pi4]`/`[cm4]` lines are ignored, so the `gpio_dpi` errors are wrong. With F1 those false errors block saves. This is the same issue as App-2-F12.
- rework: None of its own: F11 replaces this parser with BootConfigText's board-aware one.
- effort: S. deliberate: unknown.

### HW-config-text-store-F13 [slop, minor] Owner name, ticket numbers, an out-of-tree client and history narration in code and operator text
- where: `src/hardware/HardwareConfigText.hpp:1082`, `:116`, `:317`, `:1006`, `src/hardware/HardwareConfigStore.hpp:3`, `:20`, `src/hardware/HardwareConfigStore.cpp:62`, `src/ApertarCoreApp.cpp:8658`, `:12811` (@cinemate-port)
- port way: "The commands the I2C card shows for Patrik to run" (in dead code, F11). "Gesture suffixes (T44)". "// T39". `core.py` is named four times, and it is in neither tree. "the text the touch UI used to write" (the upstream UI still writes it: `ui-upstream/src/DisplayConfigBridge.cpp:58`). The operator message carries "(unconfirmed on hardware)".
- Apertar way: C1-I14: comments are rare sentences stating a hazard or a reason. There are no ticket numbers (0 TODO, 0 `///` in `src@upstream-1.6.0`).
- why it matters: These references mean nothing to the original developer and point at tools he does not have.
- rework: Drop the name and the ticket numbers. Say "socket clients" instead of `core.py`. Reword `Store.cpp:62` to "the template the touch UI writes". Remove the hedge from the operator string.
- effort: S. deliberate: no.

### HW-config-text-store-F14 [duplication, minor] Three storage blocks repeat the store.edit shape, and the post-write block appears twice more
- where: `src/ApertarCoreApp.cpp:12828-12925`, `:8655-8660`, `:12808-12813` (@cinemate-port)
- port way: `set_buffer_mode`, `set_frames_per_folder`/`set_clip_merge` and `set_storage_preroll` each build `StoreFlags{backup,trusted}`, call `store.edit`, map the refusal, update `controlsErrors_`/`controlsWarnings_`, wake the worker when written and always call `refreshBufferRequest`. `set_controls` and POST `/api/config` repeat the post-write block but call `refreshBufferRequest` only when written.
- Apertar way: C1-I17: a shape repeated inside one function becomes a local lambda before its first use (`src/ApertarCoreApp.cpp:9478@upstream-1.6.0`).
- why it matters: Five copies of the post-write step, with two refresh policies, will drift.
- rework: In `handleCommand`, add one local lambda `writeStorageKey(section, key, value)` that returns the refusal reply or an empty string. Add one App helper `afterHardwareWrite(const StoreResult &)` for the post-write block, shared with the web route. Pick one `refreshBufferRequest` policy.
- effort: S. deliberate: no.

### HW-config-text-store-F15 [bug, nit] `by` is written raw into hardware-state.conf, and a 100 ms sleep runs under the store mutex
- where: `src/hardware/HardwareConfigStore.cpp:406-414`, `:101-114`, `:198-209` (@cinemate-port)
- port way: `writeStateLocked` writes the client-supplied `by` unfiltered. The constructor parses `key=value` lines back with the last line winning, so `by="x\nwritten_revision=h0"` injects a revision. `settledLocked` sleeps 100 ms under `mutex_` when the file is over 1 s old and Core did not write it, once per outside edit.
- Apertar way: No precedent. History names already go through `safeName` (`HardwareConfigStore.cpp:54-60@cinemate-port`).
- why it matters: The two paths filter `by` differently, and one stall per outside edit lands on whichever writer comes first, the IMU included.
- rework: Use `safeName(by)` in `writeStateLocked`. Drop the sleep and the second stat: the age check (under 1 s refuses) already covers an editor that is mid-save.
- effort: S. deliberate: no.
