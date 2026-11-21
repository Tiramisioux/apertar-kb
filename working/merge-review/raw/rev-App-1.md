# Review App-1: `src/ApertarCoreApp.cpp`, port lines 1-4401, against original Apertar

Stage 2 of 3. Input: `diffs/App.part01.diff` (20 hunks), `raw/inv-App-1.md`. Yardstick: `raw/conv-core-command-plane.md` (C1-*),
`raw/conv-core-camera.md` (C2 5.11, R5). No `apertar-conventions.md` yet.

| Item | Value |
| --- | --- |
| Refs | `@port` = `cinemate-port` `01f170c` (`/home/user/Apertar-Core`). `@up` = `upstream-1.6.0` `35dbe67` (`/home/user/wt/core-upstream`) |
| Short names | `App`, `CC`, `WCP` as in BRIEF. `BB` = `src/util/BufferBudget.hpp`, `SP` = `src/util/StoragePreroll.hpp`, `BCT` = `src/hardware/BootConfigText.hpp`, `SF` = `src/util/SettingsFile.hpp` |
| Labels | Every claim **confirmed** (read at the ref) unless marked |

## 1. Findings

| Id | Sev | Cat | Title | Deliberate |
| --- | --- | --- | --- | --- |
| F1 | major | mismatch | Storage/buffer state appended to `settingsBody` only | unknown |
| F2 | major | mismatch | `[storage]`/`[media]` reach the camera through header singletons, not through `CameraController` | no |
| F3 | major | mismatch | Env-var knobs in the command plane, and their state exposed to clients | no |
| F4 | major | mismatch | Boot Config writes through its own HTTP route, outside `/api/command` and `commandMutex_`, with HTTP status codes | yes |
| F5 | major | mismatch | `errorReplyBody`: machine error codes and extra members in error replies | yes |
| F6 | major | new-ground | `apertar::bootconf`: 1355-line header-only config.txt editor, free-text edit from the WebUI | yes |
| F7 | major | security | Unauthenticated LAN route writes arbitrary `config.txt` text as root | yes |
| F8 | minor | mismatch | Boot Config operator sentences carry install commands and wire field names | no |
| F9 | minor | mismatch | Nested replies in Boot Config (`boot_config{state{}}`, `changes[]`, `drm[]`) | yes |
| F10 | minor | duplication | Direct write in `writeBootConfigText` re-implements `settingsFile::atomicWrite` | no |
| F11 | minor | new-ground | Three write routes for config.txt (direct / helper / `sudo install`) | yes |
| F12 | minor | pi-compat | With the helper installed, a fan-mode change fails on a config.txt without `[pi5]`/`[pi4]`/`[all]` | no |
| F13 | minor | new-ground | `abortSafetyStopFlushForRecord` runs before the command lock | yes |
| F14 | minor | new-ground | Eject-intent flag file has no reader in Apertar | yes |
| F15 | minor | removed-upstream-behaviour | FPS step lists now end on the mode's odd ceiling (41.08, 44.17 ...) | yes |
| F16 | minor | slop | Tutorial numbers, KB paths, Cinemate history, banner and run-on comments | no |
| F17 | minor | slop | State fields with no reader | no |
| F18 | minor | mismatch | `boolFieldValue`: a second boolean parser with `on/yes/off/no` | no |
| F19 | nit | slop | Out-of-date comment on the IMX585 Clear HDR 25 fps line | no |
| F20 | nit | mismatch | Second include block after the JPEG `#if`; `util/` headers ahead of public headers | no |
| F21 | nit | slop | `prefixViews` + one-line wrappers around `actions::` | no |

### F1. Storage/buffer state rides in `settingsBody` only (major, mismatch)

- Port: `App:393 @port` `<< "," << bufferSettingMembers();` at the end of `settingsBody`. 14 members (`buffer_setting` ... `clip_merge_env_off`, `App:252-269`). Not in `settingsEvent` (`grep '"buffer_setting"'` in `CC:163-246 @port` = 0). Built with `std::string +` concatenation, three `getenv` per call, for every setter reply (48 call sites).
- Apertar way: C1-S13 "a new camera field is added to all three, at the same position"; violation listed: "a field present in the reply but missing from the event". C1-R4: capture status goes into `get_state` / top of `/api/state`; system telemetry in `"system":{}`. C1-I08: JSON with `std::ostringstream` and `<<` (`App:167-216 @up`).
- Why: a touch-UI client that applies `settings` events and replies (`CB:1257-1261`) sees the buffer fields appear on replies and go stale on events. Every ISO tap now carries pre-roll and merge state, which are not camera settings.
- Rework: remove the line from `settingsBody`. Put the 14 members in `get_state` status keys and in a `/api/state` group (or the existing `buffer` event/`GET /api/buffer`, which already carry them). Write the builder with `ostringstream <<` lines like `imuStatusBody`.

### F2. `[storage]`/`[media]` reach the camera through header-level singletons (major, mismatch)

- Port: `refreshBufferRequest()` `App:273-286` parses the hardware file text three times (`hardware::configStore().currentText()` at 276, 279, 281) and stores results in process-wide atomics defined in headers: `BB:319-333` `inline std::atomic<unsigned> &framesPerFolderRequest() { static std::atomic<unsigned> value{0}; ...}`, `clipMergeRequest()`, `publishBufferRequest`, `SP:224-249`. `CameraController.cpp` reads them (`grep -rln bufferbudget:: src` = App, CC, HardwareConfigText). Called from 7 sites (`App:8034`, `:8145`, `:8664`, `:12811`, `:12850`, `:12890`, `:12924`).
- Apertar way: C1-S07 "A single key of `apertar-hardware.conf`: the hardware class that parses that section"; C1-S19 "Parts talk to App through `std::function` callbacks passed in the constructor ... No part holds a pointer to App"; App hands values to the camera through `camera_.set*` (C1-S01, 49 call sites). Upstream has no header-level mutable shared state (inventory 5.4: `static std::atomic` / `static std::mutex` only in `.cpp` file-private caches, `App:2269 @up`).
- Rework: a plain `struct StorageOptions { std::string buffer; unsigned framesPerFolder; bool clipMerge; ... }` parsed once per refresh by one free function `readStorageOptions(text)` in App's anonymous namespace (or by `CameraController` at take start, as it reads its knobs at take start, C2 5.11). Hand it over with `camera_.setStorageOptions(opts)`; state reads `camera_.storageOptions()`. Delete the atomics in `BB`/`SP` that only carry configuration. The safety-stop live flags may stay as `std::atomic` members of `CameraController` (C1-S18 style), read through a getter.

### F3. Env knobs in the command plane and in the state (major, mismatch)

- Port: `APERTAR_WEB_PREVIEW_RECORDING_FPS` (`App:93-106`, comment "the A/B knob ... (kb working/dng-chain, V/H4)"), `APERTAR_CDNG_BUFFER` (`App:276`), `APERTAR_STORAGE_PREROLL` (`App:278`), `APERTAR_CDNG_FRAMES_PER_FOLDER` (`App:266`, `:283`), `APERTAR_CLIP_MERGE` (`App:268`, `:285`), `APERTAR_BOOT_CONFIG` (`App:3507`). Three of them are sent to clients as state: `storage_preroll_auto_env`, `frames_per_folder_env`, `clip_merge_env_off` (`App:262`, `:266`, `:268`), and each env value wins over the matching `apertar-hardware.conf` key that the WebUI edits.
- Apertar way: C1-S24 "`App` reads only `APERTAR_HARDWARE_CONFIG`, `App:4254`"; violation listed: "an environment variable switch in the command plane". C2-R5 step 4 for bench knobs: "Do not add it to `camera_settings.conf`, `apertar-hardware.conf`, the socket API or `README.md`." Upstream knobs live in `CC`/encoders and are read where used (C2 5.11).
- Why: the operator sets a value on the WebUI and a variable in the systemd unit silently wins; the UI then needs `*_env` flags to explain it.
- Rework: choose one home per value. Operator values (`buffer`, `frames_per_folder`, `clip_merge`, `preroll`): the hardware-file key only; drop the four env reads and the three `*_env` state fields. Bench knob (`APERTAR_WEB_PREVIEW_RECORDING_FPS`): delete if the A/B test is done, else move next to the preview code as a C2-R5 knob without state exposure. `APERTAR_BOOT_CONFIG` (test path): replace with a path parameter on the writer, which the host test passes; Core keeps `kBootConfigPath`.

### F4. Boot Config has its own write route outside `/api/command` and the command lock (major, mismatch)

- Port: `App:9170-9196 @port` `POST /api/boot-config`: injects `"cmd":"set_boot_config"` into the body (`payload.insert(brace + 1, ...)`), parses it, reads `X-Apertar-Revision`, decides "browser" by the `Origin` header, calls `bootConfigSet` directly. `BootConfigReply {status, body}` (`App:3761-3764`) carries HTTP status 200/400/403/409/500 back to the socket path too. `bootConfigSet` takes `bootConfigMutex()` (`App:3505-3510`), not `commandMutex_`.
- Apertar way: C1-S09 "The WebUI changes state only through `POST /api/command` with the same JSON command as the socket"; C1-S03 one lock for all commands; C1-S02 flat `if (command.name == ...)` chain in `handleCommand` returning a string; C1-S10 route idiom. Upstream `set_fan_mode` writes the same file from inside `handleCommand` (`App:10568 @up`).
- Rework: `get_boot_config` and `set_boot_config` become two ordinary blocks in `handleCommand` returning `okReply`/`errorReply` strings; delete `BootConfigReply`, `POST /api/boot-config` and the `Origin` test. The WebUI sends `sendCommand({cmd:"set_boot_config", ...})`. Keep the `revision` field as a normal command field. `bootConfigMutex()` becomes unnecessary once both writers run under `commandMutex_`. `GET /api/boot-config` may stay as a read route (precedent `GET /api/config`, `App:7168 @up`), or go through `get_boot_config`. `POST /api/boot-config/parse` (writes nothing): fold into `set_boot_config` with `dry_run` and `text`, or keep as a file-work route like `/api/presets/import`.

### F5. `errorReplyBody`: error codes in replies (major, mismatch)

- Port: `App:173-184` builds `{"ok":false,"error":"...",<body>}`. Used with `"code":"invalid"|"unreadable"|"old_page"|"stale"|"refused"|"confirm_display"|"permission"|"write_failed"` and `"revision"`, `"drm"` (`App:3787-3841`), and in `set_controls`, `/api/config`, `set_buffer_mode`, `set_frames_per_folder`, `set_storage_preroll` (14 sites, inventory 5.1).
- Apertar way: C1-I06 "Replies come only from `okReply` ... and `errorReply(command.id, sentence)`"; C1-I07 violation listed: "Error codes"; C1-N02 "A refusal talks to the operator and is shown as written." `errorReply` `App:120-128 @up`.
- Why: clients branch on `code` instead of showing the sentence; a second error vocabulary grows beside the sentence families of C1 5.3.
- Rework: delete `errorReplyBody`. Stale revision: refuse with a sentence and let the client re-read with `get_boot_config` (it needs the state anyway). Display guard: `set_boot_config` without `confirm_display` answers ok with `"display_changed":true,"written":false`, as `dry_run` does; the card then asks and sends again. Hardware-config issue list: an ok/err sentence plus the existing `GET /api/config` read for details.
- Not a protocol break: unmodified UI ignores extra keys (C1-N11).

### F6. `apertar::bootconf` and the Boot Config feature (major, new-ground)

- Port: `BCT` 1355 lines, header-only, no I/O: parser, board rules, per-port sensor and link frequency, I2C/I2S/SPI/audio, RP1 clock, DPI display, line diff, JSON. App part `App:3651-3841`. Commits `f19b245` `dda1713` `2955ef8` `8a56545` `afa00e8` `496817f` `3b87d99` `b3e7f52` `2a4266e`; host test `tools/boot_config_test.cpp` (73 checks).
- Apertar way: no precedent. Upstream touches config.txt only through the fan block (`fanModeBlock` `App:3042`, `stripManagedFanBlock` `App:3084`, `applyFanMode` `App:3127 @up`). Header-only modules exist upstream but small (`ButtonActionList.hpp` 121 lines); hardware code with I/O is a `.cpp/.hpp` pair (`src/hardware/GpioInput.{hpp,cpp} @up`).
- Deliberate: yes. Nine commits, a review step, a revision check, a display guard, `Tested:` lines (desk only, inventory 2.1).
- Verdict: simplify. Keep the card's fields (sensor per port, link frequency, the four dtparams, fan) as a block managed like the fan block: one `# Apertar managed` section that Core strips and rewrites, which is the upstream shape. Drop the free-text editor (`text` field) or keep it only as a whole-file save like `POST /api/config` (C1-S07 exception). Move the engine to `src/hardware/BootConfig.{hpp,cpp}`. This removes most of the line-diff, review and revision machinery.

### F7. LAN route writes arbitrary config.txt as root (major, security)

- Port: `set_boot_config` with `text` (`App:3804-3812`) + `scripts/apertar-boot-config` run with `sudo -n` from `/etc/sudoers.d/apertar-boot-config` (`pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-boot-config ""`). The helper checks size, NUL and a `[pi5]|[pi4]|[all]` line only (`scripts/apertar-boot-config:39-53`). Any LAN client can set any overlay, `dtparam`, kernel, `initramfs` or `os_prefix`.
- Apertar way: C1-N10 "trusted LAN; origin check, fixed helper command lines"; `App:1543 @up` "Fixed executable and arguments only; never accept paths from WebUI/config."; upstream sudoers pins arguments: `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-standby-usb off, /usr/local/libexec/apertar-standby-usb on` (`Apertar-UI/systemd/apertar-standby-usb.sudoers @up`). Upstream's fan route writes only a generated block.
- Rework: follows F6. Only generated lines from validated fields reach the file; no free text, or free text only when the operator confirms on the touch screen. Note the helper itself is narrower than the upstream `sudo -n install` route; keep it, pinned as is.

### F8. Boot Config sentences (minor, mismatch)

- Port: `App:3605-3607` "Writing config.txt needs root. Install the helper: sudo install -m 0755 -o root -g root ~/ApertarCore/scripts/... then sudo install -m 0440 ..."; `App:3824-3827` "... Send confirm_display=true to save anyway."; `App:3793` "Apertar was updated: reload this page."; `App:3733` "<port>_link_frequency must be a whole number of Hz, or null for the sensor's default."
- Apertar way: C1-I07, one sentence for the operator, no developer detail; upstream fan sentence `App:3164 @up` "Changing the fan mode needs sudo permission." Install steps belong in README (C1-S24 note).
- Rework: "Writing config.txt needs the apertar-boot-config helper." + README section. Drop wire names from sentences.

### F9. Nested Boot Config replies (minor, mismatch)

- Port: `boot_config{path,...,state{...},drm[...],text}` (`App:3701-3706`), `changes[]`, `state{}`, `drm[]` in `set_boot_config` replies.
- Apertar way: C1 5.5: replies flat with a fixed short list of nested values (`recording_capabilities`, `imu`, `modes`, `state` ...). One nested object per topic is precedented (`imuStatusBody` `App:130 @up` = `"imu":{...}`).
- Rework: after F6, `"boot_config":{...}` as one flat object like `imu`; `changes` as a `|`-joined string or dropped; `drm` as a count of connected connectors.

### F10. Direct write duplicates `settingsFile::atomicWrite` (minor, duplication)

- Port: `fsyncPath` `App:3519-3527` and the temp/fsync/rename/dir-fsync block `App:3546-3565`.
- Apertar way: `SF:36-55 @up` `atomicWrite` (temp, `fsync`, `rename`, directory `fsync`).
- Rework: `copy_file` to `.apertar.bak`, then `settingsFile::atomicWrite(dest, text)`. Delete `fsyncPath`.

### F11. Three write routes (minor, new-ground)

- Port: `writeBootConfigText` `App:3533-3610`: direct when writable (only for the `APERTAR_BOOT_CONFIG` copy in practice), helper, then `sudo -n install` with an extra `sudo -n install` of the backup (`App:3595`).
- Apertar way: one route, `sudo -n install -m 644 <tmp> /boot/firmware/config.txt` (`App:3155-3158 @up`).
- Verdict: simplify to helper, then the upstream `sudo -n install` route. The direct route exists for the test path (F3) and goes with it.

### F12. Helper refuses config.txt without a section header (minor, pi-compat)

- Port: helper exits 2 when no `[pi5]|[pi4]|[all]` line (`scripts/apertar-boot-config:51-53`); Core returns that output as the error and does not fall through (`App:3588-3590` "The helper ran and said no ... that is the answer").
- Upstream: fan mode writes any config.txt (`App:3127-3178 @up`).
- Failing input: a config.txt with only `[cm4]`/`[cm5]` sections or none (hand-made images, older Pi 3 images): fan mode worked upstream; with the helper installed it now fails.
- Rework: drop the section check, or accept any non-empty text holding the managed fan block.

### F13. Lock-free abort before the command lock (minor, new-ground)

- Port: `abortSafetyStopFlushForRecord` `App:291-299`, called before `commandMutex_` at `App:12570` and before `hardwareActionMutex_` at `App:10119`. Needed because the safety-stop thread "holds commandMutex_ and the controller mutex" while draining (`App:12567-12569`).
- Apertar way: C1-S03 violation "a command body that runs before the lock". C1-S20: slow work that must not hold the lock is a worker with its own state group.
- Deliberate: yes (comments at both call sites).
- Verdict: keep for now; the cause is in the safety-stop thread (later slice). If that drain stops holding `commandMutex_` (C1-S20), this pre-lock call can move into the `record_start` block.

### F14. Eject-intent flag without a reader (minor, new-ground)

- Port: `writeEjectIntent` before eject (`App:4386-4391`), `clearEjectIntent` after mount (`App:4355`); `src/util/MediaIntent.hpp`; directory from `config/apertar-media.tmpfiles.conf`. Comment "(Cinemate f01b6cd)".
- Reader: none. `grep -rn apertar-media` in Core `src` and `Apertar-UI/src @port` finds only `MediaIntent.hpp`, `MediaTune.hpp` and helper paths. Upstream's automounter is `Apertar-UI/src/CfeAutomounter.cpp @up` and Core's embedded Python watcher; neither reads the flag.
- Verdict: rework. Either the UI's `CfeAutomounter` and the Python watcher check the flag in the same change, or the write/clear and the header go. An install step for a tmpfiles file with no consumer is dead weight.

### F15. FPS lists end on the odd ceiling (minor, removed-upstream-behaviour)

- Port: `selectableValueSteps` `App:1274-1289`: values up to the cap, plus the cap whenever a value lies above it. `availablePcfFpsOptions` `App:1398-1416` uses it.
- Upstream: `App:1159-1167 @up` presets `<= max`; the max is added only when no preset is left (`if (filtered.empty()) filtered.push_back(maxFps);`).
- Effect: IMX477 4144x2176 (max 41.08): upstream dial `24, 25, 30`; port `24, 25, 30, 41.08`. Same for ISO lists cut at `iso_max`.
- Deliberate: yes ("T33 (request 24)" comment). Rework: keep the upstream rule (cap only when the list would be empty), or make "add the ceiling" an operator choice of the value list. Say it in the handoff either way.

### F16. Slop in comments (minor)

| Line `@port` | Text |
| --- | --- |
| `App:88-92` | "the A/B knob for its share of the WebUI-open drops (kb working/dng-chain, V/H4)" |
| `App:243-251` | 9-line comment, one physical line of about 250 characters, two sentences run together |
| `App:1272`, `:1308`, `:1929`, `:1961` | "T33 (request 24)", "Free stepping (T33)", "T33: the operator's value lists", "The T33 fields" |
| `App:1293` | "(Cinemate's two versions use 1 / mains or hz / (fps x k); both are off.)" |
| `App:3651` | banner `// ---- Boot config card (System pane): ... ----` |
| `App:4387-4388` | "(Cinemate f01b6cd)" |

Apertar way: C1-I14 "Comments are rare and state a hazard or a reason ... No ... section banners"; violation listed: "a ticket number, a banner". Upstream `App` has 10 comment lines in 11 025.
Rework: delete ticket, KB and Cinemate references and the banner; cut multi-line notes to the one hazard sentence each.

### F17. State fields with no reader (minor, slop)

`conform_fps`, `ladder_override`, `buffer_used`, `buffer_capacity`, `buffer_unit`, `sensor_binning`, `sensor_binning_source`, `sensor_crop`: 0 hits in `WCP` and touch UI (inventory 3.2). Each costs a line in three serialisers (C1-S13). Rework: drop unless a client in this merge reads it; `sensor_binning*` may stay if `list_sensor_modes` tooling outside the repos uses it (**unconfirmed**: socket clients outside the two repos not checked).

### F18. Second boolean parser (minor, mismatch)

- Port: `boolFieldValue` `App:3709-3718` accepts `true/1/on/yes`, `false/0/off/no`, case-insensitive.
- Apertar way: C1-I05 `*enabled == "true" || *enabled == "1"` by hand; `parseUiSettingsBool` `App:350 @up` (`true/1/false/0`). C1 rough edge 5.
- Rework: use the upstream hand test; reject other text with "<field> must be true or false." as the port already says.

### F19. Out-of-date comment (nit)

`App:1386 @port` "Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution()". `CC:3379-3380 @port` returns 25 for any Clear HDR when the limit is unknown; the 16-bit cap left `backendMaximumFps` in `31d5418` (inventory 8.2). Reword to the fact, or drop.

### F20. Include layout (nit)

`App:2-5` `util/` headers before `<apertar/core/...>`; `App:71-79` a second block (`<csignal>`, `<functional>`, `playback/`, `cdng/`) after the JPEG `#if`. Upstream `App:1-55 @up`: own header, public headers, project headers, std, system, then the `#if` blocks. Rework: merge into the upstream groups.

### F21. `prefixViews` and wrappers (nit)

`App:1640-1655`: `prefixViews` copies `vector<string>` into `vector<string_view>` on every call so the one-line `hardwareActionSuffix` / `parseHardwareActionNumber` can call `actions::suffixAfter` / `numberAfter`. Rework: let `ActionCatalog.hpp` take `const std::vector<std::string> &`, and drop `prefixViews`.

## 2. Verdicts for the inventory's abstractions (inventory section 5)

| # | Name | Verdict | Reason |
| --- | --- | --- | --- |
| 1 | `errorReplyBody` | rework-to-upstream-pattern | F5 |
| 2 | `sensorBinningBody`, `bufferMembers`, `bufferSettingMembers`, `valueStepsJson` | keep (`bufferSettingMembers`: rework) | `*Body`/`json*` fragment builders follow C1-I16 and `imuStatusBody`. `bufferSettingMembers` uses `+` concatenation and sits in `settingsBody` (F1) |
| 3 | `jsonNumberArray` | keep | Twin of `jsonStringArray` (`App:293 @up`) |
| 4 | `refreshBufferRequest` + header singletons | rework-to-upstream-pattern | F2, F3 |
| 5 | `abortSafetyStopFlushForRecord` | keep | F13; revisit with the safety-stop thread |
| 6 | `webPreviewRecordingFps` | simplify | F3: delete or move to a C2-R5 bench knob |
| 7 | Value-step helpers | keep | Extend upstream `pcf*Options` in place; ranges equal the `CC` setter ranges (`CC:7749`, `:7778`, `:7896 @up`); lists in UI.conf per C1-N12. Remove "T33" (F16); revisit the ceiling rule (F15) |
| 8 | `writeBootConfigText` | simplify | F10, F11 |
| 9 | `bootConfigMutex`, `bootConfigPath`, `fsyncPath` | simplify | Mutex unnecessary under `commandMutex_` (F4); path env (F3); `fsyncPath` duplicates `SF` (F10) |
| 10 | `BootConfigReply` | rework-to-upstream-pattern | F4 |
| 11 | `bootConfigFacts`, `drmConnectorsJson`, `bootConfigJson`, `bootConfigRequestFrom`, `boolFieldValue` | simplify | F6, F9, F18 |
| 12 | `apertar::bootconf` | simplify | F6 |
| 13 | `apertar-boot-config` helper + sudoers | keep | Argument-pinned, narrower than upstream's `sudo -n install`; scope it to generated text (F7). Note: upstream helpers are compiled programs in the UI repo; a POSIX sh script in Core is new but readable |
| 14 | `hardware::actions` (`ActionCatalog.hpp`) | keep | Same shape as upstream `hardware/ButtonActionList.hpp` (header-only, `apertar::hardware`, 121 lines @up). Number parse refuses `inf`/`nan` only. F21 for the wrapper |
| 15 | `apertar::hwconf`, `hardware::configStore()` | keep (out of slice) | Only read here (`App:276-281`); judge in the slice that holds the store |
| 16 | `GpioChipInfo` | keep (out of slice) | Shares the scoring copied in `GpioInput.cpp:238-262` and `RecordingIndicatorOutput.cpp:198 @up` (C2 rough edge 4 says per-file copies are the Apertar way; check in its slice) |
| 17 | `probeI2cAddress` | keep (out of slice) | Include only here |
| 18 | `CfeHatReader` | simplify (out of slice) | Second copy of bus/address already in the Python watcher (`App:3391-3395 @up`) |
| 19 | `writeEjectIntent`, `clearEjectIntent` | rework | F14 |
| 20 | Pure-logic headers (`storagepreroll`, `bufferbudget`, `clipname`, `framepath`, `clipmerge`, `playback`) | keep (logic), rework (shared state) | Header-only logic has upstream precedent (`camera/DefaultTuningSelection.hpp`, `cdng/IfdBuilder.hpp`). The mutable singletons inside `BB`/`SP` are F2. Host tests in `tools/` are new ground (upstream has none) |

## 3. What conforms

| Item | Where `@port` | Rule |
| --- | --- | --- |
| 18 UI.conf keys: struct defaults, one `else if (key == "...")` branch each, `parseUiSettingsBool`, clamp on read | `App:1903-1907`, `:1929-1944`, `:2094-2101`, `:2159-2191` | C1-R3 steps 1-2, C1-I12, C1-N12 |
| Value-list ranges equal the camera setter ranges | `App:2159-2165` vs `CC:7749`, `:7778`, `:7896 @up` | C1-I12 |
| 27 new camera fields added to `settingsBody`, `settingsEvent`, `buildWebStateJson` | inventory 3.2 | C1-S13 |
| `jsonNumberArray` next to `jsonStringArray`, same shape | `App:485-496` | C1-I08, C1-I16 |
| `pcfIsoOptions`/`pcfShutterAngleOptions`/`availablePcfResolutionOptions` extended in place; IMX283 and IMX585 rows added to the existing per-sensor tables | `App:1398-1619`, `:1493-1513` | C2 rough edge 2 (sensor tables per layer) |
| `applyFanMode` keeps its validation, its sentences and `bool f(..., std::string *errorMessage)` | `App:3620-3649` | C1-I10 |
| Mount options extended in place; the Python watcher now gets the `umask=0002` the C++ path already had | `App:4208-4212`, `:4279-4286` | - |
| Eject-intent failure only logs with a fixed prefix | `App:4386-4391` | C1-I13 |
| `ActionCatalog.hpp` follows the `ButtonActionList.hpp` header-only shape | `src/hardware/ActionCatalog.hpp` | C1-S06 note |

## 4. Notes for stage 3

- Commit message/content crossed: `04bac89` holds the mount-option lines, `e0fa852` the pre-roll trim (inventory 8.1). Commit clarity, not M1.
- `refreshBufferRequest` parses `[storage]` twice per call (inventory 8.5); goes away with F2.
- Protocol: nothing in this slice breaks an unmodified UI or the flat command parser. New nested replies (F9) and `ladder_tops` (array in `settingsBody`) are additive.

## Skeptic

Stage 3. Every finding re-read on both sides: port `/home/user/Apertar-Core` `01f170c`, upstream `/home/user/wt/core-upstream` `35dbe67`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Placement confirmed (`App:393`, not in `settingsEvent`). "Fields go stale on events" is wrong: `CB:2664-2690` `applyBufferState` tests `state.contains(...)` before each field and the `buffer` event (`App:10841`, handled `CB:1344-1347`) carries the same members, so nothing goes stale. `CB:1257-1261` is `cameraPresetSettings`, wrong cite. What stands: the C1-S13 rule "field in the reply but not in the event", 14 non-camera members on every setter reply. `get_state` gets them only through `settingsBody` (`App:12964`), so the rework must add them to `get_state` explicitly, next to `clipMergeStateJson()` (`App:12963`). Severity major -> minor |
| F2 | corrected | `CameraController` does not read the config atomics. `framesPerFolderRequest`/`clipMergeRequest`/`prerollAutomatic` are read by App only (`App:261-267`, `:11004`, `:11703`, `:11749`, `:12891`). CC parses `[storage]` itself at take start through its own file search (`CC:2989-3005` `loadBufferConf`, used at `CC:4297`, `:5505`). So `[storage]` has two parsers (App and CC), against C1-S07. The header singletons that do cross App/CC are `safetyStopState`, `bufferSettingStorage`, `flushAbortFunction` and the global `safetyStopHook` std::function that App sets (`App:7988`) and CC calls (`CC:5018`), against C1-S19 (callbacks in the constructor). Upstream precedent for process-wide state exists but sits in the owning class's `.cpp` behind static members (`Mpu6050RecordingSession.hpp:77-82 @up`). Rework rewritten accordingly |
| F3 | stands | All six reads confirmed (`App:96`, `:266`, `:268`, `:276`, `:278`, `:283`, `:285`, `:3507`); env wins in `requestedBufferMode`/`requestedFramesPerFolder`/`requestedClipMerge` (`BB:303-330`). Upstream App reads only `APERTAR_HARDWARE_CONFIG` (`App:4254`, `:4273 @up`) |
| F4 | corrected | Mechanism confirmed (`App:9170-9196`, `bootConfigMutex` `App:3512`, socket path `App:14586-14590` runs under `commandMutex_`, HTTP path does not). Half of the Apertar way was missing: upstream has a file-save route outside `/api/command` with its own HTTP status, `POST /api/config` (`App:7175-7195 @up`, status 400, `errorReply(-1, ...)`), and C1-S09 lists "hardware config" file work as an allowed route. So the route itself is precedented; the mismatch is a structured field command served twice (body rewritten with an injected `"cmd"`), the `X-Apertar-Revision` header, the `Origin` test, 403/409 codes and the second mutex. Upstream `/api/config` has no revision or 409: the commit's "as /api/config" refers to the port's own `/api/config` change (`WCP:18922 @port`) |
| F5 | stands | 14 call sites plus the definition (`grep -c` = 15). Upstream has no `"code"` key in any reply. Introduced in `f5a61b8` |
| F6 | corrected | Facts confirmed (1355 lines, 9 commits, `boot_config_test.cpp` 427 lines). "Header-only modules upstream are small" overstated: `camera/DefaultTuningSelection.hpp` 207 lines, `color/StillSrgbProfile.hpp` 741 (a data table). Rework risk added: a managed block appended at the end cannot switch off a `dtoverlay=imx...` line earlier in the file (config.txt loads every overlay line) or an earlier `camera_auto_detect=1`; `f19b245` edits in place for that reason. So the sensor lines still need an in-place comment/uncomment; the rest (dtparams, RP1 clock, link frequency) fits a block |
| F7 | corrected | Confirmed: the helper checks size, NUL, a section line only (`scripts/apertar-boot-config:39-53`); `text` reaches it from the socket and both HTTP paths. Context added: C1-N10 is a trusted-LAN model, and upstream already lets a LAN client save arbitrary text into `apertar-hardware.conf` (`POST /api/config @up`); the new part is root-owned, boot-critical content. Severity major kept: a bad save leaves the Pi unbootable until the card is edited elsewhere |
| F8 | stands | Sentences confirmed at `App:3605-3607`, `:3824-3827`, `:3733`. The install sentence never reaches the fan mode (`applyFanMode` maps `denied` to the upstream sentence, `App:3645-3647`); it reaches the Boot Config card only |
| F9 | stands | `App:3701-3706`, `:3817-3822` confirmed |
| F10 | dropped | Folded into F11: the duplicated temp/fsync/rename code lives only in the direct route, which F11 removes |
| F11 | corrected | Confirmed (`App:3546-3610`). The direct route also fires when Core runs as root, not only for the test copy. F10's duplication is part of this finding |
| F12 | stands | `fanModeBlock` (`App:3425-3447`) adds no section header, so a file without `[pi5]/[pi4]/[all]` stays without one and the helper exits 2 (`scripts/apertar-boot-config:51-53`); `App:3588-3590` returns that without falling through. Upstream `applyFanMode` (`App:3127-3178 @up`) has no such check |
| F13 | stands | `App:12570`, `:10119` confirmed. Note for the next slice: two more pre-lock bodies sit right above (`handleReadOnlyHardwareCommand` `App:12562`, `test_input` `App:12565`), from `f5a61b8` |
| F14 | stands | No reader in Core `src` or `Apertar-UI/src` (`CfeAutomounter.cpp` has no flag). Third call site added: `clearEjectIntent` at `App:10917`. `config/apertar-media.tmpfiles.conf` also creates `/run/apertar-media/tune`, so only its `eject` line goes |
| F15 | stands | `App:1272-1289` vs `App:1159-1167 @up` confirmed |
| F16 | stands | All quoted lines confirmed. 307 `//` lines in the port's App vs 10 upstream (whole file, not only this slice) |
| F17 | stands | `git grep` over both repos at HEAD: the 8 keys appear only in their serialisers (`App`, `CC`); no WCP, UI, tools, scripts or README reader |
| F18 | stands | `App:3709-3718` vs `parseUiSettingsBool` `App:350-357 @up`. 3 callers in Boot Config |
| F19 | corrected | More than a comment: `App:1386-1389` caps only 16-bit Clear HDR at 25, while CC's table caps any Clear HDR at 25 when the sensor limit is unknown and never caps 16-bit by itself (`CC:3376-3380`, `31d5418`). The fallback (used when `fps_max` is 0) and its comment both disagree with CC. Severity nit -> minor |
| F20 | stands | `App:2-5`, `:71-79` vs `App:1-55 @up` |
| F21 | dropped | `ActionCatalog.hpp` uses the same `suffixAfter`/`numberAfter` for its own validator with brace lists (`ActionCatalog.hpp:196` `numberAfter(token, {"evm", "ev"})`); one shared parser for validator and dispatcher is reasonable, and switching it to `vector<std::string>` would allocate on every brace list. A 3-line adapter is not worth a finding |

## Final findings

### App-1-F1 [mismatch, minor] Storage/buffer state appended to settingsBody, not to settingsEvent
- where: `src/ApertarCoreApp.cpp:393@cinemate-port`; `src/ApertarCoreApp.cpp:252-269@cinemate-port`; `src/ApertarCoreApp.cpp:12963-12964@cinemate-port`
- port: `settingsBody` ends with `<< "," << bufferSettingMembers();`: 14 buffer/pre-roll/merge members built with `std::string +` and 3 `getenv` per call, on every setter reply and in `get_state`. `settingsEvent` (`CC:163-246`) carries none. The touch UI is not hurt (`applyBufferState` `CB:2664` tests `contains`, and the `buffer` event `App:10841` carries the same members).
- apertar way: C1-S13: camera fields in `settingsBody` (`App:167-216@upstream-1.6.0`), `settingsEvent` (`CC:136-187@upstream-1.6.0`) and `buildWebStateJson` at the same position; listed violation "a field present in the reply but missing from the event". Non-camera status sits in `get_state` before `settingsBody`. C1-I08: `ostringstream <<` chains (`imuStatusBody` `App:130@upstream-1.6.0`).
- why it matters: every ISO tap carries pre-roll and merge state; the reply/event key sets diverge, which the original developer keeps equal by hand.
- rework: delete the line from `settingsBody`; add `<< "," << bufferSettingMembers()` to the `get_state` body next to `clipMergeStateJson()`; `bufferMembers` (web state, `buffer` event, `GET /api/buffer`) keeps it. Rewrite `bufferSettingMembers` as an `ostringstream <<` chain.
- effort: S. deliberate: unknown.

### App-1-F2 [mismatch, major] [storage] parsed twice, live buffer state shared through header singletons and a global hook
- where: `src/ApertarCoreApp.cpp:273-286@cinemate-port`; `src/ApertarCoreApp.cpp:7988@cinemate-port`; `src/util/BufferBudget.hpp:224-333@cinemate-port`; `src/util/StoragePreroll.hpp:224-249@cinemate-port`; `src/camera/CameraController.cpp:2989-3005@cinemate-port`; `src/camera/CameraController.cpp:5018@cinemate-port`
- port: App's `refreshBufferRequest` parses `[storage]` from `hardware::configStore()` (twice per call) into header-level `inline` function-static atomics (`framesPerFolderRequest`, `clipMergeRequest`, `prerollState`, `bufferSettingStorage`), read by App only. CC parses `[storage]` again by itself at take start through its own path search (`loadBufferConf`). App and CC share live state through more header singletons: `safetyStopState`, `bufferSettingStorage` (CC writes, App reads), `flushAbortFunction` (CC registers, App calls) and `safetyStopHook`, a global `std::function` App sets and CC calls.
- apertar way: C1-S07: one owner per `apertar-hardware.conf` key, the class that parses its section. C1-S19: parts reach App through `std::function` callbacks passed in the constructor (`App:6783-6785@upstream-1.6.0`), no globals. Process-wide state upstream sits in the owning class's `.cpp` behind static members (`Mpu6050RecordingSession.hpp:77-82@upstream-1.6.0`); no mutable state in headers.
- why it matters: two parsers of one section can disagree (App's state shows one value, CC records with another after a save); the original developer cannot find who owns `frames_per_folder` or where the safety stop is signalled.
- rework: `CameraController` owns `[storage]`: one `loadBufferConf` using `APERTAR_HARDWARE_CONFIG`/the store, read at start and at `camera_.reloadStorageOptions()` after a hardware-config save (App's 7 `refreshBufferRequest` call sites). App reads `camera_.storageOptions()` and `camera_.bufferSettingStatus()` for state and the merge worker. Safety-stop flags become `std::atomic` members of CC behind a getter; `safetyStopHook` becomes a constructor callback like `eventCallback_`; `abortSafetyStopFlush` becomes `camera_.abortSafetyStopFlush()` taking only the queue's own mutex. Delete the singletons in `BufferBudget.hpp`/`StoragePreroll.hpp`; the pure parse/plan functions stay.
- rework risk: the abort must stay callable without `commandMutex_` (F13); keep it a lock-free member.
- effort: M. deliberate: no.

### App-1-F3 [mismatch, major] Env-var knobs in the command plane, overriding hardware.conf keys and exposed as *_env state
- where: `src/ApertarCoreApp.cpp:88-106@cinemate-port`; `src/ApertarCoreApp.cpp:262-268@cinemate-port`; `src/ApertarCoreApp.cpp:276-285@cinemate-port`; `src/ApertarCoreApp.cpp:3505-3510@cinemate-port`
- port: `APERTAR_WEB_PREVIEW_RECORDING_FPS`, `APERTAR_CDNG_BUFFER`, `APERTAR_STORAGE_PREROLL`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_BOOT_CONFIG` read in App; the env value beats the WebUI-edited hardware-file key (`BufferBudget.hpp:303-330`); `storage_preroll_auto_env`, `frames_per_folder_env`, `clip_merge_env_off` sent to clients.
- apertar way: C1-S24: App reads only `APERTAR_HARDWARE_CONFIG` (`App:4254@upstream-1.6.0`); "an environment variable switch in the command plane" is a listed violation. C2-R5 step 4: bench knobs stay out of `apertar-hardware.conf`, the socket API and README, read where used in CC/encoders (C2 5.11).
- why it matters: a systemd-unit variable silently beats the operator's WebUI choice; the UI needs `*_env` flags to explain it. Experiment knobs left in shipping code.
- rework: operator values: hardware-file key only; drop the four env reads (App and their CC twins at `CC:4293`) and the three `*_env` fields. `APERTAR_WEB_PREVIEW_RECORDING_FPS`: delete, or a C2-R5 knob beside the preview code with no state. `APERTAR_BOOT_CONFIG`: a path parameter on the writer for the host test; Core keeps `kBootConfigPath`.
- effort: S. deliberate: no.

### App-1-F4 [mismatch, major] Boot Config's field command has a second HTTP entry with its own lock, header protocol and 403/409 codes
- where: `src/ApertarCoreApp.cpp:9161-9196@cinemate-port`; `src/ApertarCoreApp.cpp:3512-3516@cinemate-port`; `src/ApertarCoreApp.cpp:3761-3841@cinemate-port`; `src/ApertarCoreApp.cpp:14586-14590@cinemate-port`
- port: `POST /api/boot-config` inserts `"cmd":"set_boot_config"` into the body, reads `X-Apertar-Revision`, treats an `Origin` header as "browser" (refuses without revision), calls `bootConfigSet` without `commandMutex_`; `BootConfigReply{status, body}` returns 200/400/403/409/500. The same function also answers the socket command inside `handleCommand`. Serialised by `bootConfigMutex()`.
- apertar way: C1-S09: field changes go through `POST /api/command` (`App:7637-7641@upstream-1.6.0`); C1-S02/S03: flat chain in `handleCommand` under one `commandMutex_`. Whole-file save routes are precedented: `POST /api/config` (`App:7175-7195@upstream-1.6.0`) with status 400 and `errorReply(-1, ...)`, no revision header, no 409. Upstream `set_fan_mode` writes config.txt from `handleCommand` (`App:10568@upstream-1.6.0`).
- why it matters: a second command path with its own lock and status vocabulary; the original developer's rule that socket, touch UI and WebUI share one dispatcher no longer holds.
- rework: WebUI sends `get_boot_config` / `set_boot_config` through `sendCommand`; both stay ordinary `handleCommand` blocks returning `okReply`/`errorReply`. Delete `BootConfigReply`, `POST /api/boot-config`, the `Origin` test and `bootConfigMutex` (fan mode and Boot Config both run under `commandMutex_`). `revision` is a plain field. `GET /api/boot-config` may stay as a read route; `/api/boot-config/parse` folds into `set_boot_config` `dry_run` with `text`, or stays as a file-work route shaped like `POST /api/config`.
- effort: M. deliberate: yes (`2955ef8` message describes the route, the revision header and the 409).

### App-1-F5 [mismatch, major] errorReplyBody adds machine error codes and extra members to error replies
- where: `src/ApertarCoreApp.cpp:173-184@cinemate-port`; `src/ApertarCoreApp.cpp:3787-3841@cinemate-port`; `src/ApertarCoreApp.cpp:8636@cinemate-port`; `src/ApertarCoreApp.cpp:8653@cinemate-port`; `src/ApertarCoreApp.cpp:12801-12915@cinemate-port`
- port: third reply builder; 14 call sites send `"code":"invalid|unreadable|old_page|stale|refused|confirm_display|permission|write_failed"`, `revision`, `drm`, issue lists with `ok:false` (Boot Config, `set_controls`, `/api/config`, `set_buffer_mode`, `set_frames_per_folder`, `set_storage_preroll`).
- apertar way: C1-I06: replies only via `okReply` and `errorReply(id, sentence)` (`App:108-128@upstream-1.6.0`); C1-I07 lists "Error codes" as a violation; C1-N02: the refusal sentence is shown as written. No `"code"` key anywhere upstream.
- why it matters: clients branch on codes instead of showing sentences; a second error vocabulary grows beside the sentence families.
- rework: delete `errorReplyBody`. Stale revision: a sentence; the client re-reads with `get_boot_config`. Display guard: answer ok with `"display_changed":true,"written":false` (as `dry_run`) and let the card resend with `confirm_display`. Hardware-config issues: a sentence plus the existing `GET /api/config` detail.
- effort: M. deliberate: yes (`f5a61b8` introduces it for `set_controls`; Boot Config uses it throughout).

### App-1-F6 [new-ground, major] apertar::bootconf: 1355-line header-only config.txt editor with free-text edit
- where: `src/hardware/BootConfigText.hpp:1-1355@cinemate-port`; `src/ApertarCoreApp.cpp:3651-3841@cinemate-port`
- port: header-only parser, board rules, per-port sensor and link frequency, dtparams, RP1 clock, DPI display, line diff, JSON; review step, revision check, display guard, whole-file text edit. Edits existing lines in place (`f19b245`).
- apertar way: no precedent. Upstream touches config.txt only through a managed fan block (`fanModeBlock` `App:3042`, `stripManagedFanBlock` `App:3084`, `applyFanMode` `App:3127@upstream-1.6.0`). Code with I/O is a `.hpp/.cpp` pair (`hardware/GpioInput.{hpp,cpp}@upstream-1.6.0`); upstream header-only modules hold pure logic or data up to about 200 lines of logic (`DefaultTuningSelection.hpp` 207, `ButtonActionList.hpp` 121).
- why it matters: largest new subsystem in the slice; the diff, review and revision machinery exists because arbitrary lines are edited.
- rework: drop the free-text edit (or make it a whole-file save shaped like `POST /api/config`). Put dtparams, RP1 clock and link frequency in one Apertar-managed block stripped and rewritten like the fan block. Sensor overlays keep a narrow in-place comment/uncomment of the existing `dtoverlay=imx...` lines and `camera_auto_detect`. Split into `src/hardware/BootConfig.{hpp,cpp}`.
- rework risk: a block appended at the end cannot switch off an earlier sensor overlay or `camera_auto_detect=1` (every overlay line loads); the in-place part for sensors must stay.
- effort: L. deliberate: yes (nine commits `f19b245`..`2a4266e`, host test `tools/boot_config_test.cpp`, `3b87d99` "Why" paragraph).

### App-1-F7 [security, major] LAN client can write arbitrary config.txt text as root
- where: `src/ApertarCoreApp.cpp:3804-3812@cinemate-port`; `scripts/apertar-boot-config:39-53@cinemate-port`; `config/apertar-boot-config.sudoers:4@cinemate-port`
- port: `set_boot_config` with `text` (socket, `/api/command`, `POST /api/boot-config`) goes to a NOPASSWD root helper that checks only size, NUL and a `[pi5]/[pi4]/[all]` line. Any LAN client can set overlays, kernel, initramfs, os_prefix.
- apertar way: C1-N10 trusted LAN with fixed helper command lines; `App:1543@upstream-1.6.0` "Fixed executable and arguments only; never accept paths from WebUI/config."; upstream sudoers pins arguments (`Apertar-UI/systemd/apertar-standby-usb.sudoers@upstream-1.6.0`); the fan route writes only a generated block. Upstream's free-text editor (`POST /api/config`) writes a non-root, non-boot file.
- why it matters: one bad or hostile save leaves the Pi unbootable until the card is fixed on another machine.
- rework: with F6: only generated lines from validated fields reach the file; free-text edit removed or confirmed on the touch screen. Keep the argument-pinned helper.
- effort: M. deliberate: yes (helper header documents the checks; `3b87d99` adds text edit on purpose).

### App-1-F8 [mismatch, minor] Boot Config error sentences carry install commands and wire field names
- where: `src/ApertarCoreApp.cpp:3605-3607@cinemate-port`; `src/ApertarCoreApp.cpp:3824-3827@cinemate-port`; `src/ApertarCoreApp.cpp:3733@cinemate-port`
- port: "Writing config.txt needs root. Install the helper: sudo install -m 0755 ... ~/ApertarCore/scripts/..."; "... Send confirm_display=true to save anyway."; "<port>_link_frequency must be ... or null ...". The fan mode keeps the upstream sentence (`App:3645-3647`).
- apertar way: C1-I07: one operator sentence, no developer detail; upstream "Changing the fan mode needs sudo permission." (`App:3164@upstream-1.6.0`).
- why it matters: operator toasts show shell commands and protocol fields.
- rework: "Writing config.txt needs the apertar-boot-config helper." plus a README install section; remove wire names from sentences.
- effort: S. deliberate: no.

### App-1-F9 [mismatch, minor] Nested Boot Config replies
- where: `src/ApertarCoreApp.cpp:3701-3706@cinemate-port`; `src/ApertarCoreApp.cpp:3817-3822@cinemate-port`
- port: `boot_config{...,state{...},drm[...],text}`, `changes[]`, `state{}`, `drm[]` in replies.
- apertar way: C1 5.5: replies flat with a short fixed list of nested values; one object per topic is precedented (`imuStatusBody` `"imu":{...}`, `App:130@upstream-1.6.0`).
- why it matters: grows the nested-reply list; harder for flat clients.
- rework: after F6, one flat `"boot_config":{...}` object like `imu`; `changes` as a joined string or dropped; `drm` as a connected count.
- effort: S. deliberate: yes (`2955ef8` message lists the reply shape).

### App-1-F11 [new-ground, minor] Three write routes for config.txt, one of them a second atomic-write implementation
- where: `src/ApertarCoreApp.cpp:3519-3610@cinemate-port`
- port: direct write when Core may write (root, or the `APERTAR_BOOT_CONFIG` copy) with its own `fsyncPath` and temp/fsync/rename/dir-fsync; else the root helper; else `sudo -n install` plus an extra `sudo -n install` of the backup (`App:3595`).
- apertar way: one route, `sudo -n install -m 644 <tmp> /boot/firmware/config.txt` (`App:3155-3158@upstream-1.6.0`); atomic writes go through `settingsFile::atomicWrite` (`src/util/SettingsFile.hpp:36-55@upstream-1.6.0`).
- why it matters: three branches to reason about; a second atomic-write implementation beside `SettingsFile.hpp`.
- rework: helper, then the upstream `sudo -n install` route. Drop the direct route and `fsyncPath` with F3's `APERTAR_BOOT_CONFIG`; the host test passes a path to a writer that uses `settingsFile::atomicWrite`.
- effort: S. deliberate: yes (`2955ef8`: "direct when allowed, else the apertar-boot-config helper, else sudo -n install as before").

### App-1-F12 [pi-compat, minor] With the helper installed, fan mode fails on a config.txt without [pi5]/[pi4]/[all]
- where: `scripts/apertar-boot-config:51-53@cinemate-port`; `src/ApertarCoreApp.cpp:3588-3590@cinemate-port`; `src/ApertarCoreApp.cpp:3425-3447@cinemate-port`
- port: helper exits 2 without a `[pi5]/[pi4]/[all]` line; `fanModeBlock` adds none; Core returns the helper's output and does not fall back.
- apertar way: `applyFanMode` writes any config.txt (`App:3127-3178@upstream-1.6.0`).
- why it matters: failing input: a config.txt with only `[cm4]`/`[cm5]` sections or none (hand-made or older images). Fan mode worked upstream, now refused with a helper message.
- rework: drop the section check, or accept any non-empty text that holds the managed block.
- effort: S. deliberate: no.

### App-1-F13 [new-ground, minor] abortSafetyStopFlushForRecord runs before the command lock
- where: `src/ApertarCoreApp.cpp:291-299@cinemate-port`; `src/ApertarCoreApp.cpp:12567-12571@cinemate-port`; `src/ApertarCoreApp.cpp:10119@cinemate-port`
- port: lock-free abort before `commandMutex_` / `hardwareActionMutex_`, because the safety-stop thread holds `commandMutex_` while draining.
- apertar way: C1-S03 lists "a command body that runs before the lock"; C1-S20: slow work that must not hold the lock is its own worker with its own state group.
- why it matters: a carve-out in the one-lock rule; the cause is the drain holding `commandMutex_`.
- rework: keep for now; when the safety-stop drain stops holding `commandMutex_` (later slice, C1-S20), move the abort into the `record_start` block. Judge together with the other pre-lock bodies at `App:12562-12565` (`handleReadOnlyHardwareCommand`, `test_input`).
- effort: M. deliberate: yes (comments at both call sites).

### App-1-F14 [new-ground, minor] Eject-intent flag file has no reader in Apertar
- where: `src/ApertarCoreApp.cpp:4355@cinemate-port`; `src/ApertarCoreApp.cpp:4386-4391@cinemate-port`; `src/ApertarCoreApp.cpp:10917@cinemate-port`; `src/util/MediaIntent.hpp:23-58@cinemate-port`; `config/apertar-media.tmpfiles.conf:4@cinemate-port`
- port: `writeEjectIntent` before eject, `clearEjectIntent` after mount and on removal, `/run/apertar-media/eject/<dev>` from a tmpfiles.d install step; comment cites Cinemate `f01b6cd`.
- apertar way: upstream automounters are `Apertar-UI/src/CfeAutomounter.cpp` and Core's embedded Python watcher (`App:3391+@upstream-1.6.0`); neither has such a flag, and no reader exists in Core `src` or UI `src` at the port.
- why it matters: dead write path plus an install step with no consumer.
- rework: either make `CfeAutomounter` and the Python watcher honour the flag in the same change, or delete `MediaIntent.hpp`, the three calls and the `eject` line of the tmpfiles file (the `tune` line stays).
- effort: S. deliberate: yes (`438a342` ports Cinemate `f01b6cd` on purpose).

### App-1-F15 [removed-upstream-behaviour, minor] FPS/ISO step lists now end on the mode's odd ceiling
- where: `src/ApertarCoreApp.cpp:1272-1289@cinemate-port`; `src/ApertarCoreApp.cpp:1398-1416@cinemate-port`
- port: `selectableValueSteps` appends the cap whenever a value lies above it.
- apertar way: `App:1150-1167@upstream-1.6.0`: presets `<= max`; max added only `if (filtered.empty())`.
- why it matters: IMX477 4144x2176 dial was 24, 25, 30 upstream; now 24, 25, 30, 41.08. Changes button/encoder behaviour without an option.
- rework: restore the upstream rule (cap only when the list is empty), or make "add ceiling" an explicit value-list option; state it in the handoff.
- effort: S. deliberate: yes (comment "T33 (request 24)" at `App:1272`).

### App-1-F16 [slop, minor] Tutorial numbers, KB paths, Cinemate history, banner and run-on comments
- where: `src/ApertarCoreApp.cpp:88-92@cinemate-port`; `:243-251`; `:1272`; `:1293`; `:1308`; `:1929`; `:1961`; `:3651`; `:4387-4388`
- port: "kb working/dng-chain, V/H4", "T33 (request 24)", "Free stepping (T33)", "Cinemate's two versions ... both are off", "(Cinemate f01b6cd)", a `// ---- Boot config card ... ----` banner, a 250-character run-on comment line.
- apertar way: C1-I14: comments rare, one hazard/reason sentence, no banners, no ticket numbers (10 comment lines in `App@upstream-1.6.0`; 307 in the port's App).
- why it matters: internal references mean nothing to the original developer; reads as a narrated history.
- rework: delete ticket/KB/Cinemate references and the banner; cut each note to its one hazard sentence.
- effort: S. deliberate: no.

### App-1-F17 [slop, minor] State fields with no reader
- where: `src/ApertarCoreApp.cpp:224-231@cinemate-port`; `:304-308`; `:320`; `:331`
- port: `conform_fps`, `ladder_override`, `buffer_used`, `buffer_capacity`, `buffer_unit`, `sensor_binning`, `sensor_binning_source`, `sensor_crop`: `git grep` over both repos finds them only in their serialisers (App, CC); no WCP, touch UI, tools, scripts or README reader.
- apertar way: C1-S13: each camera field costs a line in three serialisers; upstream fields all have readers (C1-R4 readers list).
- why it matters: dead protocol surface maintained three times.
- rework: drop unless a client in this merge reads it; ask the owner about external socket tooling for `sensor_binning*` first (unconfirmed).
- effort: S. deliberate: no.

### App-1-F18 [mismatch, minor] boolFieldValue: a second boolean parser accepting on/yes/off/no
- where: `src/ApertarCoreApp.cpp:3709-3718@cinemate-port`
- port: case-insensitive `true/1/on/yes`, `false/0/off/no`; 3 Boot Config callers.
- apertar way: C1-I05 `*enabled == "true" || *enabled == "1"` by hand; `parseUiSettingsBool` `App:350-357@upstream-1.6.0` (`true/1/false/0`).
- why it matters: boolean vocabulary differs per command.
- rework: use the upstream hand test; keep the existing "<field> must be true or false." refusal for other text.
- effort: S. deliberate: no.

### App-1-F19 [bug, minor] IMX585 Clear HDR fallback fps cap and its comment disagree with Core's table
- where: `src/ApertarCoreApp.cpp:1386-1389@cinemate-port`; `src/camera/CameraController.cpp:3376-3380@cinemate-port`
- port: the fallback (used when `fps_max` is 0) caps only 16-bit Clear HDR at 25, "as in Core's tableMaximumFpsForResolution()". CC's table caps any Clear HDR at 25 when the sensor limit is unknown and has no 16-bit cap since `31d5418`.
- apertar way: upstream keeps the App per-sensor fallback equal to CC's table (`App:1150-1167@upstream-1.6.0` with `maximumPcfFpsForSettings`); C1-I14: a comment states a true reason.
- why it matters: while `fps_max` is 0 the dial can offer 30 fps in 12-bit Clear HDR where Core's table says 25 (probable; only on the fallback path), and the comment points the reader at a rule that no longer exists.
- rework: make the condition `settings.clearHdr ? 25.0 : 30.0` like CC's unknown-limit row, and reword or delete the comment.
- effort: S. deliberate: no.

### App-1-F20 [mismatch, nit] Second include block after the JPEG #if; util/ headers ahead of public headers
- where: `src/ApertarCoreApp.cpp:2-5@cinemate-port`; `src/ApertarCoreApp.cpp:71-79@cinemate-port`
- port: `util/` includes before `<apertar/core/...>`; `<csignal>`, `<functional>`, `playback/` and `cdng/` headers in a block after the JPEG `#if`.
- apertar way: `App:1-55@upstream-1.6.0`: own header, public headers, project headers, std, system, then `#if` blocks.
- why it matters: first thing the original developer sees; reads as bolted on.
- rework: merge each include into its upstream group.
- effort: S. deliberate: no.
