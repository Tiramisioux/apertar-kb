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
