# Inventory: HW-config-text-store (stage 1, no judging)

Refs: port = `cinemate-port` `01f170c` (`/home/user/Apertar-Core`), upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`).
Labels: confirmed = read in code.

## 1. Files in scope

| File | Lines | Role | State vs upstream |
| --- | --- | --- | --- |
| `src/hardware/HardwareConfigText.hpp` | 1141 | header-only, namespace `apertar::hwconf`, pure (no I/O): line parser, section/key alias tables, key edits, per-key merge, line diff, validator, config.txt parser, DPI commands, text-to-edits | new file |
| `src/hardware/HardwareConfigStore.hpp` | 134 | class `hardware::HardwareConfigStore`, `StoreFlags`, `StoreResult`, `HistoryEntry`, `StoreInfo`, `ReplacedInfo`, singleton `configStore()` | new file |
| `src/hardware/HardwareConfigStore.cpp` | 505 | the writer: mutex + file lock, stat-keyed cache, revision, merge, history, atomic write, state file, replaced-by-default check, adopt | new file |
| `src/hardware/ControlsModel.hpp` | (not in scope) | namespace `hwconf` too: `controlRows`, `sectionOn`, `remoteOnly`, `peripheralSettingsJson`, `modelJson` | new file, other unit |
| `src/hardware/ActionCatalog.hpp` | (not in scope) | `normalizeToken`, `canonicalAction`, `classify` used by the validator | new file, other unit (`916c1dd`) |
| `src/util/SettingsFile.hpp` | unchanged | `QtIniLock`, `atomicWrite` reused by the store | upstream code, 0 diff (confirmed: no port commit touches it) |

## 2. Commits that wrote this unit (fork-log.md status)

| Commit | Subject | fork-log status / tests |
| --- | --- | --- |
| `3526e4b` | T37 part 1: HardwareConfigText + HardwareConfigStore, "the one writer" (fork-log.md:106) | fork-only; local branch `controls` on the Pi since 2026-10-29. Sketch host-tested in KB (`working/controls/sketch/controls_test.cpp`, 78 checks, not in the Core tree) |
| `c509e9f` | T37 part 2: IMU config writes go through the store (fork-log.md:107) | fork-only; no test recorded |
| `f5a61b8` | T37 part 3: `get_controls`, `set_controls`, `errorReplyBody`, read-only hardware commands before the command lock (fork-log.md:108) | fork-only |
| `4d80a35` | T37 part 4: validate at start, adopted version pinned, `controls_errors`/`controls_warnings` in state, default template fixed | fork-only |
| `5395fa4` | T38 part 1: `GET/POST /api/config` through the store, revision, 409/400, socket line limit 64 KiB to 1 MiB | fork-only |
| `effb804` | T38 part 2: Config page sends `X-Apertar-Revision`, shows issues with line numbers | fork-only |
| `014fa22` | T38 part 3: file replaced by a default is detected; `set_controls restore=true` | fork-only |
| `7af9f13` | T38 part 5: Core default template = HDMI 1080p (`landscape_large`, `hdmi_external_only=true`) | fork-only |
| `0a98868`, `c140c4f`, `c34f844` | T44: gesture suffixes `_single/_double/_triple/_hold`, `[gpio_switches]`, CFexpress hat; added `splitGesture`, `canonicalEncoderKey`, `pinList`, `knownKey` indexed keys | fork-only |
| `dcf09ee` | T39/T40/T42: apply without restart, `scan_i2c`, `test_output`, Listen, history | fork-only |
| `d44b177` | drop-frames: `[storage] buffer`, `[media] preroll` validator rules, `bufferbudget`/`storagepreroll` includes in the header | offer after Pi tests (fork-log.md:138); not run on the camera as of 2026-11-01 |
| `9b5ea14` | `remote<N>` keys in `[gpio_buttons]`, DPI-held pins | fork-only; Pi only, built 2026-11-04 |
| `d7dd337`, `ba0658d` | `[storage] frames_per_folder`, `clip_merge` set through the store | fork-only; on GitHub `cinemate-port` |
| UI `c9d841f`, `7c41a27` | touch UI stops writing a default file; display fallback = HDMI 1080p | see UI repo |

Tests in Core tree that touch this unit: `tools/storage_buffer_conf_test.cpp`, `tools/storage_preroll_test.cpp` (call `hwconf::parse`/`validate` for the buffer/preroll rules only). No test for the store (merge, history, lock, replacedByDefault) or the edit/diff functions in the Core tree (confirmed by `grep -ln hwconf tools/*`). The 78-check `controls_test.cpp` lives only in the KB.

## 3. Features (operator visible)

| Feature | What the operator gets | Commits |
| --- | --- | --- |
| One writer of `apertar-hardware.conf` | every save (Config page, socket, IMU, storage switches) is serialised, validated, atomically written | `3526e4b`, `c509e9f` |
| Stale-save protection | page names the revision it loaded; a changed file gives 409 and keeps the text in the box | `5395fa4`, `effb804` |
| Per-key merge | stale save merges when only values changed; key clash is `conflict`; text save that merged needs `confirm_merge` | `3526e4b`, `f5a61b8` |
| Validator with line numbers | Config page lists errors/warnings (junk lines, duplicate keys, bus missing, GPIO claimed twice, DPI holds pins, unknown action, inline comments, PCF shared) | `3526e4b`, `0a98868` |
| Save blocked on new errors only | a hand-edited file with old errors is not locked out; `force` overrides | `3526e4b` |
| History + Undo | last 20 replaced versions in `~/.config/apertar-core/hardware-history/`, pinned "Before Controls"; IMU taps coalesced 10 min | `3526e4b`, `dcf09ee` |
| Replaced-by-default detection and restore | file missing/empty or starting like the touch UI template is reported; `set_controls restore=true` | `014fa22` |
| Hand-edit guard | refuses a write while an editor is saving (mtime under 1 s, unsettled stat) | `3526e4b` |
| Script paths are ssh-only | a save that changes `[run_script] path*` is refused (`script_paths`) | `3526e4b` |
| Easy-mode key editing | `set.<section>.<key>=`, `unset.` via `set_controls`; known-key whitelist; sections flagged `easy=false` text-only | `f5a61b8`, `07afbc6` |
| Controls page model | peripherals, model rows, DPI lines, I2C buses from the saved file | `f5a61b8`, `166cc4d`, `0a98868` |
| Apply without restart | controls worker restarts changed driver groups (waits during a take) | `dcf09ee` |
| I2C scan, Listen, test output/input | `scan_i2c`, `controls_last_input`, `test_output`, `test_input` | `dcf09ee` |
| Storage switches | `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll` write `[storage]`/`[media]` through the store (`trusted`) | `d44b177`, `d7dd337`, `ba0658d` |
| IMU calibration/orientation writes | `writeHardwareConfigValues` via store, `by=imu` | `c509e9f` |
| DPI helper commands | `dpiCommands` builds sudo sed/cp/reboot lines for the I2C card | `3526e4b`, `9b5ea14` |

## 4. Commands, routes, events, state, config, env, disk, UI

| Kind | Name | Where (@cinemate-port) | Status vs upstream |
| --- | --- | --- | --- |
| socket | `get_controls` | ApertarCoreApp.cpp:12420 (read-only, answers before command lock, see :12418/:12561) | new |
| socket | `set_controls` (`base`, `text`, `restore`, `set.*`, `unset.*`, `dry_run`, `force`, `confirm_merge`, `by`) | :12763 | new |
| socket | `controls_history` (`name=` returns text) | :12458 | new |
| socket | `controls_last_input` | :12476 | new |
| socket | `scan_i2c` (`bus`) | :12486 | new |
| socket | `list_actions`, `test_input`, `test_output` | :12534, :12565, :12745 | new (ActionCatalog unit) |
| socket | `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll` | :12829, :12857, :12900 | new; each repeats the same store.edit block (about 25 lines x4) |
| socket | `help` list extended | :12930 | changed |
| HTTP | `GET /api/config` | :8613, `buildHardwareConfigFileJson` :6181 | upstream route (upstream ApertarCoreApp.cpp:7168), extended in place: adds `revision`, `boot_copy`; reads through store |
| HTTP | `POST /api/config` | :8620 | upstream route (upstream :7175 + `saveHardwareConfigFile` :5323), rewritten: header `X-Apertar-Revision`, 409 `old_page`, `merge_review`, 400 with `issues`, `new_errors`, `conflicts`; `saveHardwareConfigFile` removed from the route |
| HTTP header | request `X-Apertar-Revision` | WebControlPage.cpp:18922, :20007 | new |
| HTTP reply fields | `revision`, `written`, `errors`, `issues`, `code` | :8650 | new fields on an upstream reply |
| socket line limit | 64 KiB to 1 MiB | `src/ipc/ControlServer.cpp:16` | changed (commit `5395fa4`) |
| state | `controls_errors`, `controls_warnings` | :9458, :12947 (get_state) | new |
| event | `{"event":"controls","applied","groups","errors","warnings"}` | :12346 | new |
| config keys (read by validator/editor) | all sections in `kSections` (21): network, run_script, ina219, pcf8574, trigger_output, recording_indicator, neorotary4, gpio_buttons, gpio_encoders, gpio_switches, grove_analog, camera, imu, mpu6050, bmi160, bmi270, icm42688p, gyro, cfexpress_hat, storage, media, display | Text.hpp:46-69 | table is new; most sections existed upstream |
| config keys, new | `[gpio_buttons] d<N>_single/_double/_triple/_hold`, `remote<N>`; `[gpio_encoders] encoder<N>_*`; `[gpio_switches] switch<N>_pins/_on/_off/_position0..2`; `[storage] buffer, frames_per_folder, clip_merge`; `[media] preroll`; `[neorotary4] encoder<N>_single..hold, invert_direction, reset_on_start, max_events_per_poll, hold_ms, double_ms` | Text.hpp:456-482 | new keys (readers elsewhere) |
| alias normalisation | writer writes one spelling (`bus`, `address`, `poll_ms`, `chip`, `d<N>`, `pin<N>`, `a<N>`, `target`, `line`); aliases read, never written | Text.hpp:158-208 | new; upstream readers each carry own alias tests |
| env var | `APERTAR_HARDWARE_CONFIG` (path), `XDG_CONFIG_HOME`, `HOME` | Store.cpp:118-132 | `APERTAR_HARDWARE_CONFIG` upstream; notes-dir env new |
| file on disk | `~/.config/apertar-core/hardware-state.conf` (`written_revision/at/by`) | Store.cpp:406 | new |
| file on disk | `~/.config/apertar-core/hardware-last-written.conf` | Store.cpp:377 | new |
| file on disk | `~/.config/apertar-core/hardware-history/<YYYYmmdd-HHMMSS>-h<16hex>-<by>.conf`, `adopted-<rev>.conf` | Store.cpp:386, :451 | new |
| file on disk | `<file>.bak` (copy of replaced text, WebUI/socket saves only) | Store.cpp:357 | upstream had `.bak` (saveHardwareConfigFile) |
| file on disk | `<file>.lock` via `QtIniLock` | Store.cpp:259 | upstream lock class reused |
| file mode | new file chmod 0644 | Store.cpp:373 | new |
| UI element | Config page: Controls card, text editor with line numbers, Check, diff, history, Undo, banner for replaced file | WebControlPage.cpp (outside this unit; commits `effb804`, `8be1ab5`, `f5fe41b`) | new |
| UI element (touch UI) | none added by this unit; `DisplayConfigBridge`/`Ina219Bridge` lose `ensureDefaultHardwareConfigFile` (-280/-302 lines), fallback becomes 1920x1080 landscape_large, hdmi_external_only=true | Apertar-UI `c9d841f`, `7c41a27` | removed/changed upstream behaviour |

## 5. Original code modified by this unit

| Region (@upstream-1.6.0) | Where (@cinemate-port) | Change | Kind |
| --- | --- | --- | --- |
| `saveHardwareConfigFile` (upstream ApertarCoreApp.cpp:5323-5382: size/NUL/empty checks, copy to `.bak`, write `.tmp`, rename) | `checkHardwareConfigText` :6218 keeps the three checks; write moved into `HardwareConfigStore::saveLocked` | function split, write path replaced | rewritten + moved |
| `GET /api/config` (upstream :7168) | :8613 | same route, body from store, adds revision | extended in place |
| `POST /api/config` (upstream :7175) | :8620 | new revision protocol, merge, validation, apply wake | rewritten |
| `buildHardwareConfigFileJson` | :6181 | reads `store.info()`; adds `revision`, `boot_copy`; boot copy fallback | extended in place |
| `defaultHardwareConfigTemplate` (upstream :4290-: 720x720 square, hdmi_external_only=false) | port: 1920x1080 `landscape_large`, `hdmi_external_only=true` | content change | behaviour-changed |
| `Mpu6050RecordingSession.cpp` `writeHardwareConfigValue`/`updateImuBiasConfig` (read file, edit lines, write `.tmp`, remove-then-rename) | :611-650 | ~240 lines replaced by `store.edit(..., by "imu", trusted)`; signatures lose the `configPath` parameter | rewritten, signature changed (callers only in the same file: confirmed by grep) |
| `ApertarCoreApp::start` | :8117, :8132-8160 | added applied-text snapshot, seen callbacks, validate+adopt+replaced check at start, controls worker thread | extended in place |
| `ApertarCoreApp::stop` | :8190 | joins controls worker before drivers | extended in place |
| `handleCommand` | :12418-12930 | read-only hardware commands answered before the lock; new `if (command.name == ...)` blocks | extended in place + moved (new pre-lock path) |
| `ApertarCoreApp.cpp:276-281` ctor | uses `configStore().currentText()` for `bufferbudget`/`storagepreroll` | new readers of the text | extended in place |
| `src/ipc/ControlServer.cpp` | line limit 1 MiB | constant | behaviour-changed |
| Other hardware readers (`GpioInput`, `Pcf8574Input`, `NeoRotary4Input`, `GroveAnalogInput`, `TriggerOutput`, `RecordingIndicatorOutput`) | still use their own `hardwareConfigCandidatePaths()` and parse their own section (no `configStore()` use; confirmed by grep) | not changed by this unit (large diffs from other commits) | n/a |

## 6. New abstractions

| Name | Files | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| namespace `hwconf` (header-only) | HardwareConfigText.hpp | line-preserving parse, canonical names, edits, merge, diff, validator | none for a shared parser; every hardware class and `saveHardwareConfigFile` handle their own text (upstream ApertarCoreApp.cpp:4251, per-reader `hardwareConfigCandidatePaths()` in each `*.cpp`) | App, Store, Mpu6050, ControlsModel, two tools tests |
| `kSections[]` / `SectionInfo` / `ValueRule` | Text.hpp:27-69 | table of 21 sections: aliases, comment rule, default bus, on-by-default, easy flag | none (each reader hard-codes) | validator, edits, ControlsModel |
| `hwconf::Edit`, `Conflict`, `Issue`, `Facts`, `BootFacts` | Text.hpp | edit/merge/validate vocabulary | none | store, App |
| `HardwareConfigStore` class + `configStore()` singleton | Store.hpp/.cpp | single writer, revision, history, adopt, replaced-by-default | `saveHardwareConfigFile` free function + `QtIniLock` (settingsFile) | App, Mpu6050 |
| `StoreFlags`, `StoreResult` (code strings: locked, being_written, stale, conflict, edits, errors, script_paths, backup, write) | Store.hpp | result protocol | upstream `errorReply(id, text)` plus `bool` + out-string | App handlers |
| revision `h<16 hex>` FNV-1a | Text.hpp:318 | optimistic concurrency token | none | `/api/config`, socket |
| history dir, state file, last-written file, adopted pin | Store.cpp | undo and replaced detection | upstream keeps a single `.bak` | store |
| controls worker thread (`runControlsWorker`, `applyHardwareText`) | ApertarCoreApp.cpp:12240-12340 | apply file changes per driver group | none; upstream reads sections at start only | App (outside this unit, caused by it) |
| `hardwareConfigFacts()` | ApertarCoreApp.cpp:4965 | scans `/dev/i2c-N`, config.txt DPI lines | none | validator |
| `controlsIssuesJson` / `controlsConflictsJson` / `errorReplyBody` | ApertarCoreApp.cpp:4980-5030 | JSON arrays of objects in replies | upstream replies are flat scalar JSON (`okReply(id, "\"k\":v")`) | App |
| `hwconf::dpiCommands`, `parseConfigTxt` | Text.hpp:1040-1101 | second parser for `/boot/firmware/config.txt` | upstream has none in the hardware file path; BootConfigText.hpp (other unit) also parses config.txt | validator, Boot card |

## 7. Removed, narrowed or hidden (versus upstream)

| What | Where | Effect |
| --- | --- | --- |
| `saveHardwareConfigFile` | upstream :5323 | gone; saves are refused for stale base, new errors, changed `[run_script]` paths (before: any text up to the size limit saved) |
| Last-writer-wins POST | `/api/config` | browsers without `X-Apertar-Revision` get 409 `old_page`; only header-less scripts keep last-writer-wins |
| IMU own writer and its `configPath` argument | Mpu6050RecordingSession.cpp | IMU now writes `~/apertar-hardware.conf` (store path), not "whichever file the loader found" (the candidate list incl. `/boot/firmware`); comment says so |
| IMU write comment/format behaviour | same | old code wrote a normalised `lines` list; new edit keeps other bytes; an inline comment on an edited key moves to its own line |
| Touch UI default file creation | Apertar-UI `Ina219Bridge.cpp`, `DisplayConfigBridge.cpp` | `ensureDefaultHardwareConfigFile` removed; missing file stays missing until Core/Config saves |
| `[run_script]` paths over browser | store | ssh only |
| `[storage]`, `[media]`, `[network]`, `[camera]`, `[display]`, `[run_script]` per-key easy edit | `SectionInfo.easy=false` for network, run_script, camera, storage, media, display | text mode only via `set_controls`; storage/media switches use `trusted` to bypass |
| Duplicate sections/keys, junk lines, key above first section | validator | become errors (blocks a save that adds one; file with old ones still saves) |
| `.bak` | kept, but only when `flags.backup` (WebUI and socket); IMU none | same as upstream for WebUI |
| Config candidates `/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf` | store | store ignores them; only `defaultPath()` (env or `/home/pi/...`). Readers still search all four (confirmed in each reader) so a file that lives only in /boot is read by drivers but the Config page shows `boot_copy` and first save writes to /home/pi |

## 8. Board assumptions

| Assumption | Where | Note |
| --- | --- | --- |
| Hardware file at `/home/pi/apertar-hardware.conf` | Store.cpp:122; same as upstream | user `pi` hard-coded |
| Notes dir `~/.config/apertar-core` (HOME of the Core process) | Store.cpp:125-132 | systemd unit user decides |
| `/dev/i2c-N` enumeration for bus existence; `facts.known` false when none exist | App.cpp:4965 | no bus list = no bus check |
| Default buses per device: ina219 4, pcf8574 1, neorotary4 1, grove_analog 1, cfexpress_hat 10 | Text.hpp:49-65 | mirrors the readers' defaults; Pi 5 numbering (CFE hat on bus 10 = RP1/pcie mux). INA219 bus 4 |
| GPIO 2/3 are SDA/SCL of I2C bus 1; "while the bus exists" | Text.hpp:866 | Pi 40-pin header convention (Pi 4 and Pi 5) |
| BCM pin range 0..27 for switch pins | Text.hpp:700, :869 | 40-pin header |
| DPI overlay holds GPIO 0-27 | Text.hpp:869-871 | HyperPixel style |
| config.txt at `/boot/firmware/config.txt` with `[pi5]`/`[all]` filters; only these apply | Text.hpp:1051, :1097 | Pi 5 only filter (a `[pi4]` line is ignored); sed/cp/reboot with `sudo` |
| NeoRotary4 0x49, PCF8574 0x20, Grove ADC 0x04, CFE hat 0x34, INA219 0x40, IMX585/283 0x1a, MPU 0x68/0x69 | App.cpp:12480-12520 (scan_i2c guess table), :12441-12445 | address table |
| Units `apertar-ui-direct`, `apertar-cfe-automounter`, `apertar-network` | App.cpp:12185 | systemd unit names |
| Section group "CFexpress hat" covers `[storage]` and starts `cfeHatGeneration_` | App.cpp:12179 | CFE hat / PCIe NVMe; mount `/media/RAW`, `pcie_controller=1000110000.pcie` in default template (RP1/Pi 5 PCIe address) |
| Python NVMe reinsert helper stops on junk lines (configparser) | Text.hpp:757-767 | rules written for the Core Python helper (also upstream, ApertarCoreApp.cpp:3408) |
| RAM size, core count, fan, gpiochip numbering | none in this unit | `chip` key only canonicalised; `gpiochip` alias to `chip` (Text.hpp:172) |

## 9. Notes for stage 2 (facts only)

- Size: 1780 lines new in `src/hardware/`; upstream equivalent was about 60 lines (`saveHardwareConfigFile`) plus per-reader parsing.
- Every consumer outside the unit that parses its own section still bypasses the store for reads (6 driver files, 4 path helpers duplicated per upstream).
- Four socket handlers (`set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll`) repeat one store.edit + worker-wake block; `set_controls` and `POST /api/config` repeat the post-write block (`controlsErrors_`, `controlsWarnings_`, `wakeControlsWorker`).
- `hwconf::Facts` pulls `/dev` and `/boot/firmware/config.txt` through `hardwareConfigFacts()` in App.cpp; the header itself stays I/O-free.
- No unit test in the Core tree for the store or the edit/merge/diff functions.
