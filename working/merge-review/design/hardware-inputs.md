# Hardware file, inputs and the Controls page: plan

Read at Core `/home/user/wt/core-work` `0d13a6f` (hardware files unchanged since `d1dcdee`; fix log C1 `04fe197` and C2 `7dc6f7a` included), UI `/home/user/wt/ui-work` `ac1fc28`, upstream `upstream-1.6.0` (`35dbe67` / `43888e5`). Port line numbers are `@0d13a6f` unless marked; upstream ones `@upstream-1.6.0`. This page is the plan to implement. It replaces the first design and the challenge; what the challenge changed is in the last section.

## In short

- Today the port's hardware-file store refuses a whole-file save when the checker (`hwconf`) finds a new "error", even where the readers accept the file. It refuses any change of a `[run_script]` path, and that refusal also hits Undo and restore.
- A button that reads pressed when its input starts is inverted for the rest of the session. A press that wakes the camera from Standby is still counted, so a click or Hold fires after the wake.
- Nothing writes a first hardware file. The template Core shows has no `chip=`, no input tuning, no `[mpu6050]`, and it holds six live keys the port invented (`[storage] buffer*`, `[camera] clear_hdr_iso_max_*`).
- `hwconf` holds a second copy of every reader's rules in one 1 210-line header, with one alias map shared by all sections. The copies have already drifted from the readers.
- Target: the whole-file save behaves as in 1.6.0 (three sanity checks, then write; the checker's findings are reported, never block). Key edits from the Controls page keep their check. The browser writes the whole file again, `[run_script]` included.
- Inputs: a press held at start is ignored until it is released, as in 1.6.0. Polarity comes only from `active_low`. A wake press is consumed, the way the power button does it. Switches are left as they are (owner question 7).
- Core writes its own template once, when no hardware file exists anywhere and no record of one exists. The template carries every section the 1.6.0 touch UI wrote, and no live port key.
- `hwconf` stays, as an advisory checker for the Controls page. It moves into a `.cpp`, copies each reader's whole alias chain per section, drops its dead `config.txt` parser and its capture-pipeline includes.
- 23 Core commits (commit 12 only on an owner answer). No UI commit.

## How it works in the port today

The hardware file is `~/apertar-hardware.conf` (or `$APERTAR_HARDWARE_CONFIG`). Each input class reads its own section at `start()`. In the port, every writer goes through one store object (`HardwareConfigStore`), and a checker (`hwconf::validate`) models what each reader accepts.

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Whole file text | `HardwareConfigStore::saveLocked` `src/hardware/HardwareConfigStore.cpp:248-383`, called by POST `/api/config` `src/ApertarCoreApp.cpp:8624-8680`, `set_controls text=` `App:12780-12840`, IMU writes `src/hardware/Mpu6050RecordingSession.cpp:607-633`, storage switches `App:12850-12930` | Each reader's `loadConfig` at `start()` (e.g. `src/hardware/GpioInput.cpp:300-360`, `Pcf8574Input.cpp:270-282`); the controls worker polls the file every 2 s `App:12250-12276` and restarts changed groups | Web thread (POST); command thread under `commandMutex_` (`set_controls`); store `mutex_`, then the file lock `QtIniLock` `HardwareConfigStore.cpp:252-265` | `~/apertar-hardware.conf`, `.bak` on WebUI saves `:357` | Config textarea `src/web/WebControlPage.cpp:18979`; Controls page cards |
| Upstream sanity checks (empty, 256 KiB, NUL) | `checkHardwareConfigText` `App:6235-6255` (`kMaxEditableHardwareConfigBytes` `App:107`) | POST `/api/config` only `App:8628`; `set_controls text=` and `restore=true` skip them | web thread | - | toast |
| Save refused on new checker errors | `saveLocked` `HardwareConfigStore.cpp:336-342` (`newErrors`, `flags.force`); POST never sets `force` `App:8646-8648` | WebUI shows `new_errors` `WCP:19017-19022`; Check says "Save is refused until the errors are fixed." `WCP:18879` | under store `mutex_` | nothing is written | Config issue box, 400 reply |
| `[run_script] path*` guard | `scriptPaths()` `HardwareConfigStore.cpp:34-42`, check `:330-335` | every replace and edit: Config save, Undo (`set_controls text=<history>` `WCP:18659`), `restore=true` `App:12786-12796` | store `mutex_` | nothing is written | "Script paths are changed over ssh, not here." |
| Stale text merge | `textToEdits` `src/hardware/HardwareConfigText.hpp:1175-1208`, `saveLocked:282-310`, `needsReview` `:344-348` | no in-tree client sends `confirm_merge` (only `App:12808` names it; `apertar-kb/working/tools/core.py` is a generic field sender with no code for it) | store `mutex_` | - | 409 `merge_review` `App:8649-8660` |
| Revision header | page sends `X-Apertar-Revision` `WCP:18993`; Core refuses a browser without one `App:8634-8641` | `saveLocked` base | web thread | - | 409 `old_page` |
| "Being written" detection | `settledLocked` `HardwareConfigStore.cpp:198-209`: refuses a file Core did not write that is under 1 s old, else sleeps 100 ms under `mutex_` and stats again | every save | store `mutex_` | - | 409 `being_written` |
| Writer name in the state note | `writeStateLocked` `HardwareConfigStore.cpp:406-414` writes `by` raw (`by` from the command field `App:12813`, `:12856`, `:12896`, `:12930`) | store constructor, last line wins | store `mutex_` | `~/.config/apertar-core/hardware-state.conf` | - |
| Checker findings | `hwconf::validate` `HardwareConfigText.hpp:768-1081`, `newErrors` `:1084-1096` | App start `App:8140-8160`, `get_controls` `App:12428-12436`, every save (`HardwareConfigStore.cpp:324`) | start thread, web/command threads; counts into atomics `controlsErrors_` / `controlsWarnings_` | not saved | state `controls_errors` / `controls_warnings`; touch chip on errors only `UI qml/CameraPage.qml:2718`; Settings line shows warnings `UI qml/SettingsPage.qml:6471-6474`; Config and Controls issue boxes |
| Key aliases | one map for all sections `canonicalKey` `HardwareConfigText.hpp:158-208`, global lines `:169-172` (`channel`/`i2c_bus`/`bus_number`/`pcf_bus` -> `bus`, `addr`/`pcf_address` -> `address`, `poll_interval_ms`, `gpiochip`/`gpio_chip`); `bias` -> `pull` only in `[gpio_buttons]` `:188` | `parse()` names every key with it; `applyEdit`, `validate` | - | - | wrong bus in checker messages (`Pcf8574Input.cpp:273` takes no `pcf_bus`; `Mpu6050RecordingSession.cpp:762` takes no `channel`) |
| Keys an edit may set | `knownKey` `HardwareConfigText.hpp:451-482`, `checkEdits` `:485-500` | `set_controls set.<s>.<k>=` | command thread | - | `[gpio_encoders]` refuses `chip`, `pull`, `active_low`, `poll_ms`, `debounce_ms` with "not a key ... that Apertar reads" although the reader reads them (`GpioInput.cpp:342-355`); outputs refuse `active_low` and `pin` (`TriggerOutput.cpp:309-310`, `:325`); `hold_ms` / `double_ms` accepted, nobody reads them |
| Shared GPIO keys | the reader keeps the later line of `chip`, `active_low`, `pull`/`bias`, `poll_ms`, `debounce_ms` across `[gpio_buttons]` and `[gpio_encoders]` (`GpioInput.cpp:342-355`; same in upstream `GpioInput.cpp:431-440`) | Controls card shows and writes them in `[gpio_buttons]` only (`src/hardware/ControlsModel.hpp:259-266`, `effectiveValue` `:316`) | - | - | checker warns only for `chip` (`gpio_chip_shared` `HardwareConfigText.hpp:932-938`) |
| DPI and I2C facts | `hardwareConfigFacts` `App:4966-4982` with `hwconf::parseConfigTxt` `HardwareConfigText.hpp:1098-1149` (`[all]` and `[pi5]` only, on every board) | `validate` pin rules (C1 limits them to the header chip) | caller's thread | - | `gpio_dpi` findings |
| `[storage]` / `[media]` value checks | `validate` branches `HardwareConfigText.hpp:829-845`, includes `util/BufferBudget.hpp`, `util/StoragePreroll.hpp` `:5-6`; tested by `tools/storage_preroll_test.cpp:31-42` and `tools/storage_buffer_conf_test.cpp` (`bufferIssues`) | - | - | - | issues |
| Default template | `defaultHardwareConfigTemplate` `App:5035-5226` (720x720 since C2): `[gpio] enabled=false`, `[gpio_encoders] enabled=false`, no `chip=`, `[imu] enabled=false`, no `[mpu6050]`; live port keys `[storage] buffer=frames`, `buffer_ram_fraction=0.6`, `buffer_ram_floor_mb=512`, `buffer_ram_max_fraction=0.5` (`:5058-5061`), `[camera] clear_hdr_iso_max_12bit=720`, `clear_hdr_iso_max_16bit=1585` (`:5082-5083`); readers default to the same numbers (`CameraController.cpp:2937-2940`, `util/BufferBudget.hpp:33-35`) | GET `/api/config` shows it when no file and no `/boot` copy `App:6193-6206` | web thread | never written | Config textarea, "Not saved yet" |
| First-start file | nobody: UI `c9d841f` deleted both writers (upstream `UI src/DisplayConfigBridge.cpp:41-326`, `:587`; `src/Ina219Bridge.cpp:69-342`, `:497`) | - | - | no file on a fresh camera | UI runs on compiled defaults; `INA219 config: using defaults in /home/pi/apertar-hardware.conf` (`UI src/Ina219Bridge.cpp:263-267`) |
| "Replaced" detection and restore | `replacedByDefault` `HardwareConfigStore.cpp:416-449` against `hardware-last-written.conf`, else `adopted-*.conf`; `adopt()` `:451-463` runs at start `App:8148` | start log `App:8153-8155`; `set_controls restore=true`; Controls message | store `mutex_` | `~/.config/apertar-core/hardware-last-written.conf`, `hardware-history/`, `hardware-state.conf` | journal; Controls page |
| GPIO button polarity at start | first sample sets `button.inverted = level` `GpioInput.cpp:620-629` | `pressed = level != inverted` `:631` | GpioInput's thread, state local to `run()`; rebuilt at every reopen | not saved | one journal line |
| PCF8574 polarity at start | `invertedMask` `Pcf8574Input.cpp:424-433`, reset on reopen `:411`; the first sample seeds stable state `:437-441` | `pressedMask = levelMask ^ invertedMask` `:435` | Pcf8574Input's thread | not saved | journal line |
| NeoRotary push held at start | `heldAtStartMask` `NeoRotary4Input.cpp:544`, `:608-630`: skipped until released | - | its thread | - | - |
| Standby wake press | `handleHardwareInputAction` `App:10304-10325`: in Standby a press dispatches `wake` and returns; the wake runs synchronously on the input thread (`dispatchHardwareInputCommand` `App:10121-10130`, `wake` `App:12700-12731`) | the input class does not learn of it: `emitAction` is void `GpioInput.cpp:565-570`; `ButtonGesture` counts the press `src/hardware/ButtonGesture.hpp:21-53` | input thread -> App under `hardwareInputSequenceMutex_` | - | a later Single/Double/Hold runs with the camera awake |
| GPIO switch in Standby | switches go through the same `emitAction` (`GpioInput.cpp:666`, `:680`) and the button callback (`App:7983`, `buttonPress=true`) | App wakes; the new position counts as stable and is never applied | GpioInput's thread | - | a switch flipped in Standby wakes the camera |

## How original Apertar does this kind of thing

| Problem | Upstream precedent |
| --- | --- |
| Whole-file save from the browser | `saveHardwareConfigFile` `App:5323-5386`: non-empty, at most 256 KiB, no NUL (`:5325-5341`), `.bak`, `.tmp` + rename. No validation. POST `/api/config` `App:7175-7193` replies `path`, `display_path`, `backup_path`, `backup_display_path`. The browser writes the whole file, `[run_script]` included. WebUI is for a trusted LAN (WEB-6) |
| What happens to a value a reader does not like | The reader keeps its default silently and ignores unknown keys; only mapping errors, unknown actions and script problems are logged (HW-12; `GpioInput.cpp:441-445`; `App:8954`) |
| Key aliases | Flat `key == "a" \|\| key == "b"` chains in each reader, per section (HW-11): `Pcf8574Input.cpp:366-371`, `GpioInput.cpp:431-440`; `pcf_bus` / `pcf_address` only in `TriggerOutput.cpp:320-323` and `RecordingIndicatorOutput.cpp:359-362`. No shared INI parser |
| Shared GPIO keys | One `Config` for both sections; the later line wins (`GpioInput.cpp:405-440`). The 1.6.0 touch UI file wrote them in both (`UI src/DisplayConfigBridge.cpp:156-183`), so `poll_ms=3` and `debounce_ms=40` from `[gpio_encoders]` win there |
| A programmatic key edit | `writeHardwareConfigValue` re-enters the section at every header of that name and rewrites the key in each copy, `.tmp` + rename (`Mpu6050RecordingSession.cpp:620-668`, HW-8) |
| Button polarity | Stated by the operator per section with `active_low` (`GpioInput.cpp:433-434`, `Pcf8574Input.cpp:378`). The first sample seeds observed and stable state (`GpioInput.cpp:693-697`, `Pcf8574Input.cpp:500-504`): a button held at start fires nothing, its release fires nothing, the next press fires |
| Wake press | The power button's callback returns bool; on true the gesture is consumed: `gesture.consume(); // A wake press cannot seed another sleep.` (`StandbyPowerButtonInput.hpp:8`, `StandbyPowerButtonInput.cpp:66-71`, `PowerButtonGesture.hpp:31-32`). Buttons fire on press only, so a wake press had no follow-up (`GpioInput.cpp:703-708`); App wakes and returns (`App:8642-8656`); the template says "a button press wakes only" (`App:4360`); HW-5 "In Standby a press only wakes and is consumed; rotation never wakes" |
| Default hardware file | Three hand-kept templates (HW-7). Core only shows its template when the file is missing (`App:4291-4404`, `:5297`). The touch UI writes its own, larger template to `/home/pi/apertar-hardware.conf` at every start when that path is missing (`UI src/DisplayConfigBridge.cpp:41-326`, call `:587`; copy in `UI src/Ina219Bridge.cpp:69-342`, `:497`): `[network]`, `[run_script]`, `[ina219]`, `[pcf8574]` with tuning and `pin0..7=none`, both outputs, `[neorotary4]` with tuning and mappings, `[gpio_buttons]` with `chip=auto active_low=true pull=up poll_ms=12 debounce_ms=60 d5=capture d6=eject`, `[gpio_encoders]` with the shared keys and `encoder0_*` on GPIO 5/6/13, `[grove_analog]` with tuning and `a0`/`a1`, `[imu] enabled=true` with the driver comment, `[mpu6050] enabled=true`, `[bmi160]`, `[bmi270]`, `[icm42688p]` (`enabled=false`), `[cfexpress_hat]`, `[storage]`, `[display]` with `ui_rotation` |
| Core writing its own file at start | `CameraController` writes `camera_settings.conf` at every start, in `--simulate` too (`CameraController.cpp:7646`, `persistSettingsLocked`, no simulate gate) |
| IMU probing when enabled | Every WebUI state build reads a live IMU sample (`imuStatusBody(true)` `App:8028`), so an enabled IMU section probes its bus on each `/api/state`. Same in the port (`App:9706`, `Mpu6050RecordingSession.cpp:1015-1054`) |
| Board-dependent `config.txt` reading | None in the hardware path. The port's own `BootConfigText` (`src/hardware/BootConfigText.hpp:84-120`, `readState` `:512-556`) is board-aware and already used by the Boot Config card (`App:3653-3693`). A machine without a device tree reads as a Pi 5 (`BootConfigText.hpp:94-95`) |
| Small helper headers | Only small header-only files sit next to their owner (`src/hardware/ButtonActionList.hpp`); every `.cpp` is listed by name (HW-23) |

## The target

Who validates what:

- The readers stay the authority (HW-12). Nothing new is refused at load.
- App enforces what upstream enforced on a whole-file save: non-empty, 256 KiB, no NUL. Every whole-file door gets these checks (POST `/api/config`, `set_controls text=`, `restore=true`), in App where 1.6.0 has them, before the store sees the text. A stale base is refused, not merged.
- `hwconf::validate` is advisory for whole-file saves: the file is written and the findings come back in the ok reply. For key edits from the Controls page (`set_controls set.<s>.<k>=`), a new error still refuses the edit, because the page writes keys the operator did not type. `force=true` stays for socket clients and applies to key edits only.
- `hwconf` keeps parse, join, applyEdit, diff, validate and the per-section key list. Its aliases are per section and copy each reader's whole chain, with the reader line cited. It reads `config.txt` through `BootConfigText` with the board. It no longer judges `[storage]` / `[media]` values.

What the browser may change: the whole file, as in 1.6.0, `[run_script]` paths included (owner question 1). Key edits: what the readers read, except the five shared GPIO keys in `[gpio_encoders]`, which are refused with a message naming `[gpio_buttons]`.

How inputs treat a press:

- At start, and at every reopen, a GPIO or PCF8574 button reads its level, seeds its state from it, and ignores a press already held until it is released. This is upstream's rule, written the way NeoRotary already does it in the port.
- Polarity comes from `active_low` (section-wide) only, as in 1.6.0.
- A button press that wakes the camera from Standby is consumed: no Single, Double, Triple or Hold follows from it. A second press after the wake is a new press and fires its Press action, as in 1.6.0.
- Switches keep today's behaviour (a switch flipped in Standby wakes the camera). The rule is owner question 7.

Default file: Core's `defaultHardwareConfigTemplate()` is the one default. It holds every section the 1.6.0 touch UI wrote, with its values, except: the GPIO button and encoder examples (they claim GPIO 5 and 6 twice) are comments, `[gpio_encoders]` gets no shared keys (a comment points to `[gpio_buttons]`), `pin0..7=none` is left out (the reader's default), `[display]` stays as C2 left it (touch-ui owns it). Keys the port invented are comments. Core writes the template through the store at start, only when no hardware file exists at any candidate path and the store has no record of an earlier file. Otherwise nothing changes: the missing/restore path stays.

hwconf: stays new ground, smaller. Split into `.hpp` (types) and `.cpp`, about 150 lines lighter, aliases per section.

| Value | Before (port today) | After | Owner | Set by | Reaches state and UIs |
| --- | --- | --- | --- | --- | --- |
| Whole file from Config page | refused on new checker errors, on `[run_script]` path change, from a browser without the revision header; stale text may merge | written after the three upstream checks; findings returned; stale base refused (409); missing header = current revision | App checks, `HardwareConfigStore` writes | POST `/api/config` (unchanged fields) | ok reply `issues`, `errors` (port fields kept); state `controls_errors` |
| Check button text | "Save is refused until the errors are fixed." | "Save writes the file anyway; the readers skip what they cannot use." | WebUI | - | Config issue box |
| Undo, history restore, `restore=true` | refused when script paths differ; no empty/size/NUL check | written after the three checks | App + store | `set_controls text=` / `restore=true` | as above |
| Key edit (Controls page) | refused on new errors; refuses shared GPIO keys in `[gpio_encoders]` with "not a key Apertar reads"; refuses outputs' `active_low`/`pin`; accepts `hold_ms`/`double_ms`; first copy of a duplicated section only | refused on new errors (unchanged); shared keys in `[gpio_encoders]` refused with "Set chip, pull, active_low, poll_ms and debounce_ms in [gpio_buttons]: the encoders share them."; outputs' `active_low`/`pin` accepted; `hold_ms`/`double_ms` refused; written into every copy | store + `hwconf::knownKey` | `set_controls set.<s>.<k>=` | `get_controls` |
| Shared GPIO key set in both sections | warning for `chip` only | warning for each of the five keys, naming the line that wins | `hwconf::validate` | - | Config and Controls issue boxes; Settings warning count |
| First write on a `/boot`-only rig | creates a partial `/home/pi` file that hides the `/boot` sections | starts from the `/boot` text, writes `/home/pi` | store | any writer | Config shows the full file |
| Aliases in the checker | one map, global bus/address lines | per section, each reader's whole chain | `hwconf` (`HardwareConfigText.cpp`) | - | checker messages name the bus the reader uses |
| DPI lines for the pin checks | `[all]` and `[pi5]` on every board | `BootConfigText` filters for the board (`pi3`/`pi4`/`pi5`/`cm4`/`cm5`/...); no device tree reads as Pi 5, as today | App `hardwareConfigFacts` | - | `gpio_dpi` findings |
| Button held at start | inverted for the session (GPIO, PCF8574); NeoRotary ignored until release | ignored until release on all three | each input class | - | - |
| Normally closed button | auto-detected by being pressed at start | `active_low=false` for the section; per-pin key only if the owner wants it (commit 12) | input class | file | - |
| Wake press from Standby | wakes, then its click or Hold also runs | wakes only | input class + App | - | - |
| Default file content | Core template without `chip=`, input tuning, `[mpu6050]`; six live port keys | every 1.6.0 touch UI section; port keys commented | App `defaultHardwareConfigTemplate` | - | Config textarea when missing |
| Who writes the first file | nobody | Core at start, through the store, once; `adopt()` skipped that start | App `start()` | - | file exists; Config shows it as saved |

Old files: no key moves. A file with `[gpio]` keeps working (every reader takes `[gpio]` as `[gpio_buttons]`, `GpioInput.cpp:291`). A file the 1.6.0 touch UI wrote has `poll_ms=3` and `debounce_ms=40` in `[gpio_encoders]` after `[gpio_buttons]`; the reader uses them for the buttons too, as in 1.6.0. After commit 22 the checker reports two warnings on such a file (Settings line "2 warnings"; no camera chip, it counts errors only, `UI qml/CameraPage.qml:2718`), and the Controls card's message tells the operator which line wins. Nothing rewrites those lines. Existing `hardware-history/` and `hardware-state.conf` stay valid; a state note with an injected line is read as today until the next write replaces it.

## Commit plan

All commits are in Apertar-Core. "Check here" uses `/home/user/build/bin/check_core.sh /home/user/wt/core-work hwin both tests` (both builds and the host tests in `tools/`), then a simulate run:

```bash
D=/tmp/hwin; mkdir -p $D/media $D/cfg
APERTAR_HARDWARE_CONFIG=$D/hw.conf APERTAR_BOOT_CONFIG=$D/config.txt XDG_CONFIG_HOME=$D/cfg HOME=$D \
  /home/user/build/hwin-nolc/apertar-core --simulate --socket $D/core.sock --media $D/media \
  --web-bind 127.0.0.1 --web-port 8765 &
cmd() { curl -s -X POST -H 'Content-Type: application/json' -d "$1" http://127.0.0.1:8765/api/command; }
```

plus `/home/user/build/bin/smoke_core.sh` before and after, diffed, for reply shapes. Every commit keeps the 1.6.0 fields of `/api/config` (GET: `ok path display_path exists size_bytes size_text modified_text text`; POST: `ok path display_path backup_path backup_display_path`) and of `/api/state`. Re-grep every anchor before editing: `core-work` moves while other themes land.

### 1. hw: a whole-file save writes the file and reports what the checker found

- Files: `src/hardware/HardwareConfigStore.cpp` `saveLocked`; `HardwareConfigStore.hpp:19` comment on `StoreFlags::force`; `src/web/WebControlPage.cpp:18879`.
- What: the `newErrors` refusal (`:336-342`) applies only when `edits` is set. Text saves compute `issues` and write. `force` is documented as "key edits only: save although the edit adds errors". The Check sentence becomes `". Save writes the file anyway; the readers skip what they cannot use."`. Save already shows issues after a successful write (`WCP:19010-19013`).
- Lines: -4 / +5.
- Check here: save a file the readers accept but the checker flags (`d17=capture` twice in `[gpio_buttons]`): `curl -s -X POST --data-binary @dup.conf http://127.0.0.1:8765/api/config` returns `ok:true` with a `duplicate_key` issue, and the file is written. A key edit that adds an error is still refused: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_buttons.d18":"capture","set.gpio_buttons.d17":"capture"}'`. Headless Chromium: press Check on that file, the issue box ends in the new sentence.
- Pi only: none (no hardware path changes).
- Depends on: nothing. Command-plane may later replace `StoreResult.code`; this commit does not touch codes.

### 2. hw: the browser may change [run_script] paths again

- Files: `HardwareConfigStore.cpp` (delete `scriptPaths()` `:34-42` and the check `:330-335`), `HardwareConfigStore.hpp` (drop `script_paths` from the code list comment).
- What: deleted; nothing added. Undo, history restore and `restore=true` stop failing on path differences. `test_input` already refuses script actions (`d1dcdee`, `App:12408-12410`), so a browser cannot fire a script without a press.
- Lines: -16 / +0.
- Check here: POST a text with `path=/home/pi/x.sh` under `[run_script]` -> `ok:true`. Undo after an outside edit of a path -> written.
- Pi only: `P2=run_script1` with a new path, press P2, `journalctl -u apertar-core | grep script` shows the new path.
- Depends on: owner question 1. If the owner keeps "ssh only", this commit becomes: keep the check for `by=webui` text saves, skip it for `by=webui_undo` and `restore=true`, one README line. About -2 / +8.

### 3. hw: every whole-file save gets the empty, size and binary checks

- Files: `src/ApertarCoreApp.cpp` `set_controls` branch (after `if (!text && edits.empty())`, `:12802-12803`).
- What: `if (text && !checkHardwareConfigText(*text, &message)) return errorReply(command.id, message);`. The checks stay in App (`checkHardwareConfigText` `App:6235-6255`, `kMaxEditableHardwareConfigBytes` `:107`), where 1.6.0 has them (`App:5325-5341@upstream-1.6.0`). They run before the store's base and no-change tests (`HardwareConfigStore.cpp:282`, `:325-328`), so an empty text is refused whatever the base, and the text `restore=true` resolves is checked too.
- Lines: -0 / +4.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","text":""}'` -> "Config file cannot be empty.", file untouched; same with a stale base. POST `/api/config` with an empty body -> 400 with the same sentence as 1.6.0 (unchanged).
- Pi only: none.
- Depends on: nothing. Tell webui-state: if Undo and Check move to `/api/config` (WCP-09-F12), both doors already check the same.

### 4. hw: a whole-file save without a revision header is taken against the current file

- Files: `App` POST `/api/config` `:8634-8645`.
- What: deleted: the `Origin` branch and its 409 `old_page`. A missing header means base = current revision for every client, as in 1.6.0 (last writer wins with `.bak`). A present header keeps the stale check.
- Lines: -7 / +1.
- Check here: `curl -X POST -H 'Origin: http://127.0.0.1:8765' --data-binary @hw.conf .../api/config` -> 200. With `X-Apertar-Revision: h0123456789abcdef` -> 409.
- Pi only: none.
- Depends on: nothing. Tell webui-state: the page keeps sending the header.

### 5. hw: a stale whole-file save is refused; the merge review is gone

- Files: `HardwareConfigText.hpp` (delete `textToEdits` `:1175-1208`); `HardwareConfigStore.{hpp,cpp}` (delete `StoreFlags::confirmMerge`, `StoreResult::merged`, `needsReview`, the `textToEdits` branch `:290-297`, `:344-348`); `App` (`confirm_merge` flag `:12808`, `merged` / `needs_review` reply fields `:12833-12834`, the `needsReview` mapping `:8649-8660`, `result.needsReview` in the dry-run text line `:12838`); `WCP:19019` drop `"merge_review"`.
- What: a stale text base returns "The file changed since you loaded it. Reload, then change it again." Per-key `conflicts()` for key edits stays.
- Lines: -62 / +3.
- Check here: both builds (the deleted fields are port-only: `smoke_core.sh` diff shows only `merged`, `needs_review` gone from `set_controls`). Simulate: load, edit the file by hand, POST with the old revision -> 409 `stale`.
- Pi only: none.
- Depends on: command-plane (codes): no conflict, it removes a code they would otherwise carry. Owner line under question 5.

### 6. core: the default hardware file template leaves the write-buffer and Clear HDR keys as comments

- File: `App` `defaultHardwareConfigTemplate` (`:5058-5061`, `:5082-5083`).
- What: the six live lines become comments, the way `[media]` already is (`:5071-5077`): `# buffer=frames`, `# buffer_ram_fraction=0.6`, `# buffer_ram_floor_mb=512`, `# buffer_ram_max_fraction=0.5`, `# clear_hdr_iso_max_12bit=720`, `# clear_hdr_iso_max_16bit=1585`. The readers already use these numbers as defaults (`CameraController.cpp:2937-2940`, `util/BufferBudget.hpp:33-35`), so nothing changes for a camera, and a file Core writes in commit 9 does not pin them.
- Lines: -6 / +6.
- Check here: simulate with no file: GET `/api/config` text has no live `buffer=` or `clear_hdr_iso_max` line; `/api/state` storage and Clear HDR fields equal the run before.
- Pi only: none.
- Depends on: storage-settings and camera-modes may move or delete these keys (Media-buffer-split-F1, CC-2-F1). Whatever they decide, a key the port invented stays a comment in the template. Tell both.

### 7. core: the default hardware file template holds the 1.6.0 touch UI's input and network sections

- File: `App` `defaultHardwareConfigTemplate`.
- What moves in (text, from upstream `UI src/DisplayConfigBridge.cpp:58-205`), section by section:
  - `[network]`: carried (`hotspot_delay_seconds=60` and its two comments; the reader default is 60, `UI src/WifiBridge.cpp:27`).
  - `[pcf8574]`: carried `active_low=true`, `poll_ms=40`, `debounce_ms=60`. Left out: `pin0..7=none` (the reader's default; the Controls page adds a pin line when one is mapped). Port `bus=1` stays (the UI writer's value too).
  - `[neorotary4]`: carried `poll_ms=30`, `debounce_ms=60`, `invert_direction=false`, `reset_on_start=false`, `max_events_per_poll=8` and the twelve `encoderN_cw/ccw/press` mappings (I2C knobs, no pin claim; the reader has no built-in mappings, so a camera that enables the knob gets what a fresh 1.6.0 camera got).
  - `[gpio]` becomes `[gpio_buttons]` (the name the UI writer and the Controls page use) with `enabled=false`, `chip=auto`, `active_low=true`, `pull=up`, `poll_ms=12`, `debounce_ms=60` and the comment `# chip=auto is the Pi's 40-pin header; another chip by path, for example /dev/gpiochip13.` The examples `d5=capture`, `d6=eject` are carried as comments: with `[gpio_encoders]`' example they claim GPIO 5 and 6 twice.
  - `[gpio_encoders]`: the comment `# chip, active_low, pull, poll_ms and debounce_ms are shared with [gpio_buttons]: set them there.`; the `encoder0_*` example (pins 5, 6, 13) as comments. No shared keys: copying `poll_ms=3` / `debounce_ms=40` would make them win for the buttons too (`GpioInput.cpp:342-355`).
  - `[gpio_switches]` comment: "chip, pull, active_low and debounce_ms come from [gpio_buttons]."
  - `[grove_analog]`: carried `poll_ms=80`, `deadband=32`, `emit_on_start=false`, `a0=wb`, `a0_min=2500`, `a0_max=8000`, `a0_step=50`, `a1=iso`, `a1_mode=preset` and the address comment (I2C ADC channels, no pin claim).
  - `[display]`: unchanged here. `ui_rotation=normal` and its comments are touch-ui's (name it there).
- Lines: -3 / +45.
- Check here: a scratch program running `hwconf::validate` over the new template with empty facts finds no issue (run once for the first design on the GPIO part; rerun on the full text). Simulate with no file: GET `/api/config` shows the new text; `get_controls` lists the GPIO card with chip `auto`.
- Pi only: none until commit 9.
- Depends on: 6. Touch-ui: if the owner restores the UI writer instead (question 3), this text is copied into that writer too (HW-7).

### 8. core: the default hardware file template holds the IMU sections

- File: `App` `defaultHardwareConfigTemplate`.
- What moves in (from upstream `UI src/DisplayConfigBridge.cpp:199-298`): the `[imu]` driver comment (`# Current options: driver=mpu6050, bmi160, bmi270, icm42688p.`) and the sync comment; `[mpu6050]` with the UI writer's values and comments (`bus=1`, `address=0x68`, `sample_rate_hz=500`, `gyro_range_dps=1000`, `accel_range_g=8`, `dlpf_hz=98`, `use_fifo=true`, `fifo_batch_samples=24`, `orientation=XYZ`, level, bias, auto-calibrate and readout keys at 0/false); `[bmi160]`, `[bmi270]`, `[icm42688p]` with `enabled=false` as the UI wrote them. `enabled` in `[imu]` and `[mpu6050]` as owner question 4 decides (recommended `true`, as the 1.6.0 file was).
- Lines: -0 / +95. All text; review as text.
- Check here: scratch `hwconf::validate` over the template: no issue. Simulate: `/api/state` `imu.enabled` follows the choice; `imu.bus` is 1, `imu.address` 104.
- Pi only: none until commit 9.
- Depends on: 7 (same function, avoids a clash); owner question 4.

### 9. core: Core writes the default hardware file when no copy exists

- Files: `App` `start()` (after the standby recovery, before the first `refreshBufferRequest()` `:8031` and before any reader; the adopt block `:8148`); `README.md` hardware paragraph.
- What is added: if no path in `hardwareConfigCandidatePaths()` (`App:4924`) is a regular file, and `~/.config/apertar-core/hardware-last-written.conf` does not exist, and no `hardware-history/adopted-*.conf` exists, then `configStore().replace(kAbsentRevision, defaultHardwareConfigTemplate(), "core", {})`, and a local `wroteDefault = result.written`. One journal line: `ApertarCore controls: wrote the default <display path>`. The adopt line becomes `const bool adopted = !wroteDefault && store.adopt();`, so Core's own write is not recorded as "Before Controls (as Core first found it)". The write runs in `--simulate` too, as upstream writes `camera_settings.conf` there (`CameraController.cpp:7646@upstream-1.6.0`). README: "When no hardware file exists, Core writes its template to ~/apertar-hardware.conf ($APERTAR_HARDWARE_CONFIG if set) at start, also with --simulate."
- Why gated so: a file that was moved away on purpose, or lost, leaves a last-written copy behind, so the existing restore path (`replacedByDefault`) handles it and the hazard `c9d841f` removed does not come back. A `/boot` copy counts as a file. The write goes only to the editable path (HW-9).
- Lines: -1 / +18.
- Check here: simulate with an empty `$D`: `$D/hw.conf` appears with the template text, `$D/cfg/apertar-core/hardware-last-written.conf` equals it, no `adopted-*.conf` exists, GET `/api/config` shows `exists:true`. Second start with the file moved away: no write; the journal says the file was replaced and can be restored. Start with only `$D/cfg/apertar-core/hardware-history/adopted-h....conf`: no write.
- Pi only: back up first (`mv ~/apertar-hardware.conf ~/hw.keep; mv ~/.config/apertar-core ~/core.keep`), then `sudo systemctl stop apertar-ui; sudo systemctl restart apertar-core; sleep 5; ls -l ~/apertar-hardware.conf ~/.config/apertar-core/hardware-last-written.conf; journalctl -u apertar-core -b | grep 'wrote the default'; sudo systemctl start apertar-ui; journalctl -u apertar-ui -b | grep 'INA219 config'`. Expect the two files, the journal line, and `INA219 config: /home/pi/apertar-hardware.conf (enabled=true, bus=4, address=0x40)`, not `using defaults in` (`UI src/Ina219Bridge.cpp:253-267`). Put the two back afterwards and restart both units.
- Depends on: 6, 7, 8 (content); owner question 3; touch-ui agrees not to restore the UI writers.

### 10. hw: a button held when its input starts is ignored until it is released

- Files: `src/hardware/GpioInput.{hpp,cpp}` (`RuntimeButton::inverted` -> `heldAtStart`; `process` `:620-639`); `src/hardware/Pcf8574Input.cpp` (`invertedMask` -> `heldAtStartMask`, `:397-470`).
- What: deleted: the inversion and its journal lines. Added: the NeoRotary rule (`NeoRotary4Input.cpp:608-630`) in the two other button inputs: the first sample seeds observed and stable state (upstream `GpioInput.cpp:693-697`); a button whose first stable state is pressed is not fed to `ButtonGesture` until it reads released. PCF8574 already seeds stable state at the first sample (`Pcf8574Input.cpp:437-441`), so without the skip the removal alone would fire Press for a held button. Applies at every reopen too, as upstream re-seeds at reopen (GPIO rebuilds its `RuntimeButton`s, `GpioInput.cpp:752-780`).
- Lines: -24 / +16.
- Check here: both builds; review by reading (state is local to `run()`). `ButtonGesture` is unchanged.
- Pi only: `[gpio_buttons] enabled=true d17=record_toggle`; hold d17, `sudo systemctl restart apertar-core`, release after "GPIO input enabled" is logged: nothing records. Press once: recording starts; press again: stops. `journalctl -u apertar-core | grep inverted` is empty. Same with a PCF8574 pin. On a Pi 4 and a Pi 5 (chip `pinctrl-bcm2711` / `rp1`); the code path is board-independent.
- Depends on: owner question 2. Before deploying on the owner's rig: `journalctl -u apertar-core | grep 'taken as inverted'`; any line means commit 12 goes in the same push.

### 11. hw: the press that wakes the camera from Standby does nothing else

- Files: `src/hardware/ButtonGesture.hpp` (add `consume()`); `GpioInput.{hpp,cpp}`, `Pcf8574Input.{hpp,cpp}`, `NeoRotary4Input.{hpp,cpp}` (button callback type and `emitAction`); `src/ApertarCoreApp.{hpp,cpp}` (`handleHardwareInputAction` returns bool; the constructor lambdas `:7983-7989` return it).
- What is added, shaped like upstream's power button (`StandbyPowerButtonInput.hpp:8`, `.cpp:66-71`):
  - `ButtonGesture::consume()`: `clicks_ = 0; if (down_) { longPress_ = true; holdFired_ = true; }`.
  - A `PressCallback = std::function<bool(const std::string &)>` for the button callback. Rotation and seen callbacks keep their void type.
  - `emitAction` returns the callback's result (false for an empty action). On true a button event calls `gesture.consume()` for that button. The switch calls (`GpioInput.cpp:666`, `:680`) ignore the result: switches behave as today (owner question 7).
  - `handleHardwareInputAction` returns true exactly when it dispatched `wake` (`App:10316-10322`), false otherwise. `testInputReply` and `handlePowerButtonPress` ignore the result.
  - With only Single or Hold mapped, the wake comes from that gesture; consume then clears what is left of it.
- Lines: -12 / +32.
- Check here: both builds; a scratch host program on `ButtonGesture` (press, consume, release within 500 ms -> no Single; press, consume, hold 3 s -> no Hold); not committed (PLT-12). Simulate: `cmd '{"cmd":"enter_standby"}'` then `cmd '{"cmd":"test_input","section":"gpio_buttons","key":"d17"}'` wakes only and the reply is as before.
- Pi only: `d17=record_toggle`, `d17_hold=standby`, `d17_double=photo`. Enter Standby. Hold d17 3 s: the camera wakes and stays awake (`journalctl -u apertar-core -f` shows one `wake`, no `enter_standby`). Enter Standby, double-click d17: it wakes and no new file appears under the photos folder. The second press is a new press after the wake (the wake runs on the input thread, `App:10121-10130`): if it is seen, it starts a take, as in 1.6.0; stop it. A take is expected, a photo is a failure. Same on a NeoRotary push and a PCF8574 pin.
- Depends on: 10 (same files; order avoids a merge clash).

### 12. hw: one GPIO or PCF8574 button can be normally closed (only if the owner wants it)

- Files: `GpioInput.{hpp,cpp}` `loadConfig` (`dN_active_low`), `Pcf8574Input.{hpp,cpp}` (`pinN_active_low`), `HardwareConfigText` `knownKey`, `ControlsModel.hpp` row field, `WCP` one select on the button row.
- What: recipe R11 step 6: a per-pin key next to the section's `active_low`, `parseConfigBool`, no other rule. The kernel flag is per line in the GPIO v2 request (`GPIO_V2_LINE_FLAG_ACTIVE_LOW`, `GpioInput.cpp:519-520`), so GPIO needs one more `attrs` entry; PCF8574 needs a per-pin XOR mask.
- Lines: about -2 / +40. Done as two commits if wanted: Core reader (+25), page (+15).
- Check here: both builds; Controls page in headless Chromium shows the field and saves `d17_active_low=false`.
- Pi only: a normally closed button on d17 with `d17_active_low=false`: one press records once.
- Depends on: 10; owner question 2. New ground (no per-pin polarity upstream).

### 13. hw: a key edit sets the key in every copy of its section

- File: `HardwareConfigText.hpp` `applyEdit` Set (`:519-585`).
- What: as upstream `writeHardwareConfigValue` (`Mpu6050RecordingSession.cpp:620-668@upstream-1.6.0`): replace the key in each copy of the section; insert a new line only when no copy has it.
- Lines: -6 / +12.
- Check here: a 10-line scratch program on `hwconf::applyEdits` with `[mpu6050]` twice, both copies holding `gyro_bias_x`; after the edit both hold the new value. Not committed (PLT-12). (`set_controls` refuses a duplicated section in `checkEdits`; the trusted writers that skip it, IMU and storage switches, need the camera or a medium.)
- Pi only: with `[storage]` twice, `set_buffer_mode` then `grep -n buffer= ~/apertar-hardware.conf` shows the value in both copies.
- Depends on: nothing.

### 14. hw: the first save on a /boot-only rig starts from the /boot file

- File: `HardwareConfigStore.cpp` `saveLocked` (after `refreshLocked`, `:267-276`).
- What: when the editable file does not exist and `/boot/firmware/apertar-hardware.conf` or `/boot/apertar-hardware.conf` does, `current` starts from that text. The rule already exists for display (`App:6193-6206`); the write still goes to the editable path only (HW-9).
- Lines: -1 / +10.
- Check here: run simulate in a scratch mount namespace (`unshare -m` with a bind of `$D/bootfw` on `/boot/firmware`) if root; otherwise read the diff.
- Pi only: move `~/apertar-hardware.conf` to `/boot/firmware/` (and `~/.config/apertar-core` aside), restart Core, run Gyro Calibration or `set_buffer_mode`: the new `/home/pi` file holds every section of the `/boot` file plus the edit. Put both back.
- Depends on: nothing. Note: commit 9 does not write on such a rig (a `/boot` copy counts as a file).

### 15. hw: the hardware-state note takes a safe writer name

- File: `HardwareConfigStore.cpp` `writeStateLocked` `:406-414`: `state_.writtenBy = safeName(by);` (the history names already use `safeName`, `:54-60`).
- Lines: -1 / +1.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_buttons.enabled":"false","by":"x\nwritten_revision=h0"}'` then `cat $D/cfg/apertar-core/hardware-state.conf`: one `written_by=` line, no second `written_revision=` line.
- Pi only: none.
- Depends on: nothing.

### 16. hw: the store does not wait 100 ms under its lock

- File: `HardwareConfigStore.cpp` `settledLocked` `:198-209`: delete the first `statFile()`, the 100 ms sleep and the compare; return true after the age check.
- Why it is safe: an editor that is saving leaves the file's mtime under 1 s old, which the age check (`:204-205`) still refuses. The second stat only adds a writer that pauses more than 1 s between two writes into the same file. nano and vim write in one go (vim by rename). Upstream's whole-file save has no such check at all (`App:5323-5386@upstream-1.6.0`). The sleep holds `mutex_`, so the IMU and every other writer wait behind it.
- Lines: -4 / +1.
- Check here: both builds. Simulate: `touch $D/hw.conf` then a key edit at once -> `being_written`; 2 s later -> written, with no delay in the reply (`time cmd ...`).
- Pi only: none.
- Depends on: nothing.

### 17. hw: the pin checks read config.txt through BootConfigText, for every board

- Files: `HardwareConfigText.hpp` (delete `BootFacts`, `parseConfigTxt`, `dpiCommands` `:1098-1170`); `App` `hardwareConfigFacts` `:4977`; `BootConfigText.hpp:248` comment.
- What: `const bootconf::Board board = bootconf::boardFromDeviceTree(readTextFileRaw("/proc/device-tree/compatible"), readTextFileRaw("/proc/device-tree/model")); facts.dpiLines = bootconf::readState(bootconf::parseDocument(text, board), board).displayLines;`, as `bootConfigFacts` reads the board (`App:3653-3657`). C1's rule "DPI and I2C bus 1 rules apply to the header chip only" stays. A machine with no device tree reads as a Pi 5 (`BootConfigText.hpp:94-95`), so `[pi5]` lines still count there, as today.
- Lines: -76 / +5.
- Check here: both builds; `boot_config_test` passes; a scratch program over `bootconf::readState(bootconf::parseDocument(text, board), board)` with an explicit board per case: `pi4` (DPI overlay under `[pi4]` counts, under `[pi5]` does not), `pi5` (the reverse), `cm5` (`[cm5]` counts), undetected (reads as `pi5`). Simulate with `APERTAR_BOOT_CONFIG=$D/config.txt` holding a DPI overlay under `[all]`: `get_controls` lists GPIO 0-27 as held.
- Pi only: on a Pi 4 with a DPI overlay under `[pi4]`: `get_controls` lists GPIO 0-27 as held; with the overlay only under `[pi5]`: they are free. On a CM5 with `[cm5]`: held.
- Depends on: boot-config-helpers (owns `BootConfigText`; if it renames `readState` or `displayLines`, follow it).

### 18. hw: the hardware checker no longer judges [storage] and [media] values

- Files: `HardwareConfigText.hpp` (delete `#include "util/BufferBudget.hpp"`, `#include "util/StoragePreroll.hpp"` `:5-6` and the two branches `:829-845`); `tools/storage_preroll_test.cpp` (delete the validator block `:31-42` and the `hwconf` include if nothing else uses it); `tools/storage_buffer_conf_test.cpp` (delete `bufferIssues` and its checks; keep the `hwconf::parse` / `applyEdits` checks `:30-32`, `:108-116`).
- What: delete only. The readers already keep their default for a bad value (`BufferBudget.hpp:176`, `StoragePreroll.hpp:81`), as HW-12 says. The problem functions stay tested directly (`storage_preroll_test.cpp:22-28`).
- Lines: about -45 / +0.
- Check here: both builds; the host tests pass.
- Pi only: none.
- Depends on: storage-settings (it may move these keys out of the hardware file; whether the Config page should still name a bad buffer value is theirs).

### 19. hw: hwconf moves out of line into HardwareConfigText.cpp

- Files: `src/hardware/HardwareConfigText.hpp` (types, constants, declarations), new `src/hardware/HardwareConfigText.cpp` (bodies), `CMakeLists.txt` (listed by name after `HardwareConfigStore.cpp`, HW-23), the `// g++` lines of `tools/storage_preroll_test.cpp` and `tools/storage_buffer_conf_test.cpp` if they still include the header after commit 18 (add `src/hardware/HardwareConfigText.cpp`; `check_core.sh` picks sources from that line).
- What: a move only. `kSections` stays in the header (ControlsModel reads it).
- Lines: about -1 000 / +1 020. Review with `git show --color-moved=dimmed-zebra`.
- Check here: both builds, host tests, `smoke_core.sh` diff empty.
- Pi only: none.
- Depends on: 5, 17, 18 (they delete code first, so less moves).

### 20. hw: hwconf maps key aliases per section, as each reader does

- File: `HardwareConfigText.cpp` `canonicalKey`.
- What: deleted: the global lines (`:169-172` today). Added: per-section flat chains that copy each reader's whole chain for the keys the checker or `applyEdit` names, each with the reader line it copies; the commit message lists them reader by reader:
  - `pcf8574`, `neorotary4`, `grove_analog`: `channel`, `i2c_bus` -> `bus`; `addr` -> `address`; `poll_interval_ms` -> `poll_ms` (`Pcf8574Input.cpp:273-279`, `NeoRotary4Input.cpp:312-318`, `GroveAnalogInput.cpp:281-287`).
  - `ina219`, `cfexpress_hat`: `channel`, `i2c_bus` -> `bus`; `addr` -> `address` (`App:5285-5288`, `:5338-5341`).
  - `mpu6050`, `bmi160`, `bmi270`, `icm42688p`: `bus_number` -> `bus`; `addr` -> `address` (`Mpu6050RecordingSession.cpp:762-765`).
  - `trigger_output`, `recording_indicator`: `pcf_bus` -> `bus`; `pcf_address` -> `address`; `gpiochip`, `gpio_chip` -> `chip` (`TriggerOutput.cpp:305`, `:314-317`; `RecordingIndicatorOutput.cpp:340`, `:352-355`), next to the aliases already there.
  - `gpio_buttons`, `gpio_encoders`: `gpiochip`, `gpio_chip` -> `chip`; `poll_interval_ms` -> `poll_ms`; `bias` -> `pull` (`GpioInput.cpp:342-350`; today `bias` maps in the buttons branch only).
- A key outside its reader's chain is no longer renamed, so `[pcf8574] pcf_bus=10` shows as a key the reader ignores, which is what happens.
- Lines: -14 / +34.
- Check here: scratch program: `[pcf8574] pcf_bus=10` -> no `bus_missing` for bus 10; `[mpu6050] channel=3` -> not read as bus 3; `applyEdits` with `set.trigger_output.chip=/dev/gpiochip0` on the template (which has `gpiochip=auto`, `App:5172`, `:5186`) leaves one chip line. Host tests.
- Pi only: none.
- Depends on: 19.

### 21. hw: set_controls takes the keys the readers read

- File: `HardwareConfigText.cpp` `knownKey` and `checkEdits`.
- What: both outputs accept `active_low`; `[trigger_output]` accepts `pin` (`TriggerOutput.cpp:309-310`, `:325`; `RecordingIndicatorOutput.cpp:345`, `:363`). `hold_ms` and `double_ms` are removed from the three lists (`ButtonGesture.hpp:16-18` fixes the timing in code; `grep -rn hold_ms src` finds only `knownKey`). In `[gpio_encoders]`, `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` stay refused, with their own message: "Set chip, pull, active_low, poll_ms and debounce_ms in [gpio_buttons]: the encoders share them." (X-knobs-1). The card writes them in `[gpio_buttons]` only (`ControlsModel.hpp:259-266`), so a second way to write the overriding line is not added.
- Lines: -3 / +6.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_encoders.poll_ms":"3"}'` -> refused with the new sentence; `set.trigger_output.active_low=false` -> written; `set.gpio_buttons.hold_ms=900` -> refused.
- Pi only: none.
- Depends on: 19.

### 22. hw: the checker names every GPIO key the buttons and encoders share

- File: `HardwareConfigText.cpp` `validate` (the `gpio_chip_shared` block `:932-938` today).
- What: the block becomes one loop over `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` (the names after commit 20's aliases, so `bias` and `gpiochip` count). When `[gpio_encoders]` sets one and `[gpio_buttons]` does not, or sets another value, one warning `gpio_shared`: "The GPIO buttons, encoders and switches share <key>, and Core takes the line further down the file (line N). Keep one, in [gpio_buttons]." The chip check that follows stays.
- Lines: -6 / +10.
- Check here: scratch `validate` on the 1.6.0 touch UI file text (`UI src/DisplayConfigBridge.cpp:156-183@upstream-1.6.0`): two warnings, `poll_ms` (line of `poll_ms=3`) and `debounce_ms`; no error. On Core's template: none.
- Pi only: none.
- Depends on: 20.

### 23. hw: comments in the hardware text store say what the code does

- Files: `HardwareConfigStore.{hpp,cpp}`, `HardwareConfigText.{hpp,cpp}`, `App` lines touched above (`T37`, `T39`, `T44`, `core.py`, "Patrik", "the text the touch UI used to write" -> "the template the touch UI wrote in 1.6.0", "(unconfirmed on hardware)" in an operator string).
- Lines: -20 / +12.
- Check here: both builds; `grep -nE 'T[0-9]{2}|core\.py|Patrik|Cinemate' src/hardware/HardwareConfig*` is empty.
- Pi only: none.
- Depends on: 19 (so the comments are edited once, in their final file).

Order rationale: 1-5 restore the 1.6.0 save behaviour first (smallest, most visible). 6-9 give a stock camera its file, content before writer. 10-12 are the input rules. 13-16 are store bugs. 17-22 reshape `hwconf` once the deletes have shrunk it. 23 is last. The camera works after each: no commit changes a reader's result except 10 and 11, which restore upstream behaviour, and 9, which only acts on a camera with no file.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| `HardwareConfigStore`: one writer with revisions, history (20 + adopted), `.bak`, atomic write, file lock, "replaced" detection and `restore=true` | Unchanged apart from the deletes above. Fallible calls still return a `StoreResult` (command-plane decides its error form) | Several writers (Config page, Controls page, IMU, storage switches) share one file; upstream's `saveHardwareConfigFile` shape (`.bak`, `.tmp` + rename) is inside it, and the sanity checks stay in App. The restore path is what allows the touch UI writer to stay deleted |
| `hwconf` checker (`HardwareConfigText.{hpp,cpp}`) | Advisory for whole-file saves, blocking only for key edits; per-section alias chains that cite their reader; no `config.txt` parser of its own; no capture-pipeline includes | Upstream has no validator. The Controls page (owner feature) needs to know which pins are taken and what a key means before it writes. The nearest upstream pattern is the per-reader `key ==` chain, so the checker copies that shape and says which reader line it mirrors. It is a deliberate second copy, listed for the original developer like the three templates (HW-7) |
| Core writes the first hardware file | Once, at start, through the store, only when no file and no record of one exist; not adopted as "Before Controls" | Upstream writes it from the UI. The port moved ownership of the file to Core (`014fa22`, `c9d841f`); a writer in Core is the smallest way to keep 1.6.0's fresh-camera result without the moved-file hazard. Precedent for a Core-owned file written at start: `camera_settings.conf` (`CameraController.cpp:7646@upstream-1.6.0`) |
| Gesture actions (`_single`, `_double`, `_triple`, `_hold`) | Kept; the wake press is consumed (commit 11) | Owner feature; upstream fires Press only. The consume rule makes it obey HW-5 |
| GPIO switches (`[gpio_switches]`) | Kept as today, including a wake from Standby | Port-only; the Standby rule is owner question 7 |
| `controls_errors` / `controls_warnings` in state and the touch chip | Kept | HW-22 keeps input health out of state. These count findings about the file, not device health; the chip only says "look at the WebUI". Owner question 5 |
| Per-pin `dN_active_low` (only if commit 12 goes in) | One key per pin beside the section key | No per-pin polarity upstream; R11 step 6 is the shape |

## For the owner

1. **`[run_script]` paths from the browser.**
   - Question: may the Config page change them?
   - Options: (a) yes, as 1.6.0 (commit 2 deletes the check); (b) keep "ssh only" (decision Q2) but exempt Undo, history restore and `restore=true`, and say it in the README.
   - Recommendation: (a). The WebUI is a trusted-LAN surface upstream (WEB-6), and since `d1dcdee` a browser can no longer fire a script without a button press.
   - Cost: (a) -16 lines. (b) +8 lines and a rule the original developer has to learn.
2. **Normally closed (1-0-1) buttons.**
   - Question: does any rig need them?
   - Options: (a) no: delete the auto-inversion (commit 10), a whole section can still say `active_low=false`; (b) yes: commit 10 plus a per-pin `dN_active_low` / `pinN_active_low` (commit 12); (c) keep the guess behind an opt-in key.
   - Recommendation: (a), or (b) if the owner's rig has such a button. Before deploying commit 10, run `journalctl -u apertar-core | grep 'taken as inverted'` on the rig: any line means (b).
   - Cost: (b) about +40 lines of new ground. (c) keeps a rule that inverts a held or stuck button for the whole session.
3. **Who writes the first hardware file.**
   - Options: (a) Core, gated (commits 6-9); (b) restore the touch UI's two writers as in 1.6.0 (UI repo, about +590 lines back, and their template must get every port key by hand, HW-7); (c) nobody (today).
   - Recommendation: (a). The touch-ui theme must agree not to restore the UI writers.
   - Cost: (a) +18 lines of new ground plus template text. (b) brings back the moved-file hazard `c9d841f` removed.
4. **IMU on or off in the first-start file.**
   - Question: the 1.6.0 touch UI's file had `[imu] enabled=true`, `[mpu6050] enabled=true`; upstream Core's template has `[imu] enabled=false`.
   - Options: (a) on, as a fresh 1.6.0 camera was; (b) off, as Core's template and HW-20 ("accessories ship disabled").
   - Recommendation: (a). It reproduces what a stock camera got. Effect with no IMU fitted, as in 1.6.0: every WebUI state build tries a live read on bus 1 at 0x68 (`App:9706`, `Mpu6050RecordingSession.cpp:1015-1054`; upstream `App:8028`) and shows "Waiting for MPU-6050"; a take writes a `.gcsv` only when Record Gyro Data is on. A rig with another chip at 0x68 on bus 1 (an RTC) gets that probe too.
   - Cost: none in code; two words in the template.
5. **Key edits still refused on new errors, the touch chip, and the merge review.**
   - Question: should the Controls page's key edits also become advisory? Should the camera page keep its "Controls: N errors" chip? Does any script of yours send `confirm_merge=true` or read `needs_review` (commit 5 removes both; `apertar-kb/working/tools/core.py` passes fields through and has no code for them)?
   - Recommendation: keep the refusal and the chip. The page writes keys the operator did not type, so it should not introduce a clash. The chip is the only sign on the camera that the file has an error. Remove the merge review unless a script of yours uses it.
   - Cost: none.
6. **hwconf's future.**
   - Options: (a) keep it as a second, cited copy (this plan); (b) let each reader parse from text, so the checker calls the readers (touches 8 upstream reader files and their `loadConfig` signatures); (c) drop the checker and with it the Controls page's pin checks.
   - Recommendation: (a) now; (b) only if the original developer asks for it after the merge.
7. **A GPIO switch moved while the camera is in Standby.**
   - Today: it wakes the camera (it uses the button callback, `GpioInput.cpp:666`, `:680`; `App:7983`), and its new position is never applied after the wake.
   - Options: (a) leave it; (b) treat it like a turn (HW-5: rotation never wakes): ignore it in Standby and apply the position at wake; (c) wake and apply.
   - Recommendation: decide before a switch rig ships; not designed here. (b) needs GpioInput to re-emit the stable positions after a wake, new ground.

## Risks and what was not determined

- `core-work` is being changed in parallel: HEAD moved from `7dc6f7a` via `d1dcdee` to `0d13a6f` while this was read. Re-grep each anchor before editing.
- Command-plane may replace `StoreResult.code` and the `code` / `new_errors` fields in error replies. Commits 1-5 do not depend on that change, and it does not depend on them.
- Webui-state may move Undo and Check from `set_controls text=` to `/api/config` (WCP-09-F12). After commit 3 both doors run the same checks.
- Boot order: the unit files are not in either tree, so whether `apertar-ui` starts after `apertar-core` is not known. If the UI reads before Core's first write, it runs that boot on its compiled defaults (equal to the template's `[display]` since C2) and logs `using defaults in`. Not seen on a Pi; the commit 9 Pi step avoids the race by stopping the UI first. To settle: `systemctl cat apertar-ui | grep -E 'After|Requires'` on the Pi.
- `$APERTAR_HARDWARE_CONFIG` pointing under `/boot`: commit 9 would write there. Upstream writes the editable path the same way (`App:5343@upstream-1.6.0`). Not changed.
- `--simulate` on a dev machine without `APERTAR_HARDWARE_CONFIG` writes `/home/pi/apertar-hardware.conf` (the store creates the folder, `HardwareConfigStore.cpp:256`) if the user may. README says so.
- After commit 9, the "starts like the touch UI's default" reason in `replacedByDefault` (`HardwareConfigStore.cpp:438`, header test `:63-67`) never fires for a file that began as Core's template, because Core's template starts with the same two lines. "Missing or empty" still fires. With the UI writer deleted, only an old UI build could produce that case.
- Commit 10 on a rig that relied on auto-inversion: its normally closed buttons fire on release after the update. Check the journal before deploying (owner question 2).
- Commit 11's "consume" when the wake comes from a Single (no Press mapped): the release has already happened, so `consume()` only clears the count. Reasoned, not run. Whether the second press of a double click is seen after the wake depends on how long the wake takes and on the GPIO edge queue; the Pi step accepts either.
- Switch positions (`[gpio_switches]`) are still applied at every GpioInput start and reopen, including after each Controls save of the GPIO group (HW-input-classes-F2 switch half, F6). Not designed here: a rule about the switches feature, with question 7.
- DPI pins: commit 17 fixes which lines count. Whether a 16- or 18-bit DPI mode leaves upper header pins free (WCP-09-F13) needs the overlay pin maps. After commit 1, a false `gpio_dpi` finding no longer blocks a text save; it still blocks a key edit.
- Commit 7's NeoRotary and Grove mappings are live in the template, as the 1.6.0 file had them. With the sections off they do nothing; the Controls page lists them as assigned. The scratch `validate` run over the final template text is still to be done when commit 7 is written.
- Not run here: anything with real GPIO, I2C or Standby. The scratch check of the GPIO part of the template (clean under `hwconf::validate`, empty facts) was run in this container for the first design.

## Findings covered

| Finding | Commit |
| --- | --- |
| HW-config-text-store-F1 | 1 |
| HW-config-text-store-F2 | 2 (or its variant, owner question 1) |
| HW-config-text-store-F3 | 19, 20 (validator kept advisory by 1) |
| HW-controls-model-F2 | 10 (12 if the owner wants per-pin polarity) |
| HW-input-classes-F1 | 11 |
| App-2-F2 | 7, 8 |
| UI-bridges-F2 | 9 |
| X-board-support-1 | done by C1 `04fe197`; the remaining key refusals in 21, the shared-key warning in 22 |
| X-knobs-1 | 21 (the refusal with its message), 22 |
| X-stock-behaviour-2 | 9, with 6 so no port key is written live |
| HW-config-text-store-F4 | 13 |
| HW-config-text-store-F5 | 3 |
| HW-config-text-store-F6, HW-input-classes-F9 | 14 |
| HW-config-text-store-F7 | 5 |
| HW-config-text-store-F8, App-3-F4 | 4 |
| HW-config-text-store-F10 | 18 |
| HW-config-text-store-F11, F12, App-2-F12, X-board-support-5 | 17 |
| HW-config-text-store-F13 | 23 |
| HW-config-text-store-F15 | 15, 16 |
| HW-controls-model-F1 | done by C1 `04fe197` |
| HW-controls-model-F3 | 21 for the refused keys; not covered: the missing page rows (`open_drain`, `pulse_ms`, `events`, Grove channels) are page content, webui-state |
| HW-controls-model-F4 | 21 |
| HW-input-classes-F2 | 10 for the polarity half; switch half not covered (Risks, question 7) |
| App-2-F11 | kept as new ground (section above); merge review removed by 5 |
| App-2-F10 | partly by 9 (a fresh camera gets `[cfexpress_hat] enabled=true` in its file); the reader default is storage-settings' (hat watcher) |
| App-2-F1 | done by C2 `7dc6f7a` (template `[display]` 720x720) |
| HW-config-text-store-F9 | not covered: error codes and issue arrays in error replies belong to command-plane |
| HW-config-text-store-F14 | not covered: storage-settings (the storage switch blocks) |
| HW-controls-model-F7 | not covered: the action-name parser is a separate mechanism (`ActionCatalog`); its blocking effect on text saves ends with 1 |
| HW-controls-model-F5, F6, F8, F9, F10, F11, F12, F14, F15, F16 | not covered: action catalog, Controls JSON and probes, not the save, polarity, wake or default-file mechanism |
| HW-controls-model-F13, HW-input-classes-F3, F4, F5, F7, F8, F10, F11 | not covered: GpioInput loop shape (edge events, lambdas, callbacks, comments); a separate input-loop pass |
| HW-input-classes-F6 | not covered: switches feature rule (question 7) |
| WCP-09-F13 | not covered: needs DPI overlay pin maps (Risks) |

## What the challenge changed

Each row was checked against the code at `0d13a6f`.

| Point | Decision | Why |
| --- | --- | --- |
| Commit 1 leaves the Check sentence false | Right. `WCP:18879` and `HardwareConfigStore.hpp:19` join commit 1 | `WCP:18879` reads "Save is refused until the errors are fixed." |
| Live port keys in the template would be written onto stock cameras | Right. New commit 6 comments them out. The order dependency is only partly right: once they are comments, commit 9 pins nothing, so storage-settings and camera-modes need only keep them commented | `App:5058-5061`, `:5082-5083`; reader defaults equal (`CameraController.cpp:2937-2940`, `BufferBudget.hpp:33-35`) |
| Template carries only part of the UI writer's file | Right. Commits 7 and 8 account for every section: tuning and I2C mappings carried, GPIO examples as comments (pins 5/6 claimed twice), `pin0..7=none` left out (reader default), `[display]` to touch-ui | `UI src/DisplayConfigBridge.cpp:58-317@upstream-1.6.0` |
| `adopt()` would record Core's own write as "Before Controls" | Right. `adopted = !wroteDefault && store.adopt()` | `App:8148`; `HardwareConfigStore.cpp:451-463` |
| Write in `--simulate` or not | Write it, as upstream writes `camera_settings.conf` in simulate; README says so | `CameraController.cpp:7640-7646@upstream-1.6.0`, no simulate gate |
| Commit 9 (was 7) Pi check cannot show the UI read the file | Right. UI stopped first; expect `INA219 config: /home/pi/...` not `using defaults in` | `UI src/Ina219Bridge.cpp:253-267` |
| Switches share the button callback and wake from Standby | Right. Commit 11 leaves them as they are; owner question 7 | `GpioInput.cpp:666`, `:680`; `App:7983` |
| Double-click Pi expectation | Partly right. The second press is a new press after the wake and may start a take, as in 1.6.0; whether it is seen depends on the wake's length, since the wake blocks the input thread. The test asserts "no photo" only | `App:10121-10130`, `:12700-12731` |
| Commit 15 (now 18) would break two host tests; App cannot add issues inside the store | Right. Delete-only; the tests lose their validator checks in the same commit | `HardwareConfigStore.cpp:324`; `tools/storage_preroll_test.cpp:31-42`; `storage_buffer_conf_test.cpp:15-20` |
| Commit 17 (now 20) drops aliases the readers read | Right. Each reader's whole chain is copied, including `poll_interval_ms` in the I2C inputs, `chip` aliases in the outputs and `bias` in `[gpio_encoders]` | `Pcf8574Input.cpp:279`, `TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:340`, `GpioInput.cpp:347` |
| Old files: the `[gpio_encoders]` shared lines win; the card edits lines that have no effect | Right. Commit 21 keeps refusing the five keys in `[gpio_encoders]` with a message naming `[gpio_buttons]`; new commit 22 warns for all five. Same "later line wins" in 1.6.0, so nothing is rewritten | `GpioInput.cpp:342-355`; upstream `GpioInput.cpp:431-440`; `ControlsModel.hpp:259-266` |
| Commit 13 holds two ideas | Right. Split into 15 and 16. 16 kept, with the reason: a saving editor leaves the file under 1 s old, which the age check still refuses; upstream has no such check | `HardwareConfigStore.cpp:198-209`; `App:5323-5386@upstream-1.6.0` |
| Commit 14 (now 17) check needs an explicit board | Partly right. The scratch program takes the board explicitly. An undetected board reads as Pi 5, so the container's simulate case equals today's rule | `BootConfigText.hpp:94-95` |
| core.py and `confirm_merge` | Partly right. core.py is a generic field sender with no code for either; the owner line asks only about the owner's own scripts (question 5) | `apertar-kb/working/tools/core.py:3` |
| IMU probe claim in question 4 unconfirmed | Right; settled. The probe is every WebUI state build, not only the Gyro panel, in 1.6.0 and the port | `App:9706`; upstream `App:8028`; `Mpu6050RecordingSession.cpp:1015-1054` |
| Commit 3 placement | Partly right. The checks must run before the store's base and no-change tests. They stay in App, where 1.6.0 has them, and are called in the `set_controls` branch after `restore=true` resolves the text: -0 / +4 instead of a move into the store | `App:6235-6255`, `:12780-12803`; `HardwareConfigStore.cpp:282`, `:325-328` |
