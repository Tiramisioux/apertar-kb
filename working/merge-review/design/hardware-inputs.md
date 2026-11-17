# Hardware file, inputs and the Controls page: design

Read at Core `/home/user/wt/core-work` `d1dcdee` (branch `work/improve`, fix log C1 `04fe197` and C2 `7dc6f7a` included), UI `/home/user/wt/ui-work` `ac1fc28`, upstream `upstream-1.6.0` (`35dbe67` / `43888e5`). All port line numbers are `@d1dcdee` unless marked; upstream ones `@upstream-1.6.0`.

## In short

- Today the port's hardware-file store refuses a whole-file save when the checker (`hwconf`) finds a new "error", even where the readers accept the file. It refuses any change of a `[run_script]` path, and that refusal also hits Undo and restore.
- A button that reads pressed when its input starts is inverted for the rest of the session. A press that wakes the camera from Standby is still counted, so a click or Hold fires after the wake.
- Nothing writes a first hardware file. The template Core shows has no `chip=`, no input tuning and no `[mpu6050]`.
- `hwconf` holds a second copy of every reader's rules in one 1 210-line header, with one alias map shared by all sections. The copies have already drifted from the readers.
- Target: the whole-file save behaves as in 1.6.0 (three sanity checks, then write; the checker's findings are reported, never block). Key edits from the Controls page keep their check. The browser writes the whole file again, `[run_script]` included.
- Inputs: a press held at start is ignored until it is released, as in 1.6.0. Polarity comes only from `active_low`. A wake press is consumed, the way the power button does it.
- Core writes its own template once, when no hardware file exists anywhere. The template carries what the 1.6.0 touch UI used to write.
- `hwconf` stays, as an advisory checker for the Controls page. It moves into a `.cpp`, takes its aliases per section and drops its dead `config.txt` parser and its capture-pipeline includes.
- 19 Core commits (one is conditional on an owner answer). No UI commit.

## How it works in the port today

The hardware file is `~/apertar-hardware.conf` (or `$APERTAR_HARDWARE_CONFIG`). Each input class reads its own section at `start()`. In the port, every writer goes through one store object (`HardwareConfigStore`), and a checker (`hwconf::validate`) models what each reader accepts.

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Whole file text | `HardwareConfigStore::saveLocked` `src/hardware/HardwareConfigStore.cpp:248-383`, called by POST `/api/config` `src/ApertarCoreApp.cpp:8624-8680`, `set_controls text=` `App:12780-12840`, IMU writes `src/hardware/Mpu6050RecordingSession.cpp:607-623`, storage switches `App:12850-12930` | Each reader's `loadConfig` at `start()` (e.g. `src/hardware/GpioInput.cpp:300-360`, `Pcf8574Input.cpp:273-276`); the controls worker polls it every 2 s `App:12250-12276` and restarts changed groups `App:12279` | Web thread (POST); command thread under `commandMutex_` (`set_controls`, `App:12592`); store `mutex_` then the file lock `QtIniLock` `HardwareConfigStore.cpp:252-265` (command lock taken at `App:12588`) | `~/apertar-hardware.conf`, `.bak` on WebUI saves `:357` | Config textarea `src/web/WebControlPage.cpp:18979`; Controls page cards |
| Upstream sanity checks (empty, 256 KiB, NUL) | `checkHardwareConfigText` `App:6235-6255` | POST `/api/config` only `App:8628`; `set_controls text=` skips them | web thread | - | toast |
| Save refused on new checker errors | `saveLocked` `HardwareConfigStore.cpp:336-342` (`newErrors`, `flags.force`); POST never sets `force` `App:8646-8648` | WebUI shows `new_errors` `WCP:19017-19022` | under store `mutex_` | nothing is written | Config issue box, 400 reply |
| `[run_script] path*` guard | `scriptPaths()` `HardwareConfigStore.cpp:34-42`, check `:330-335` | every replace and edit: Config save, Undo (`set_controls text=<history>` `WCP:18659`), `restore=true` `App:12786-12796` | store `mutex_` | nothing is written | "Script paths are changed over ssh, not here." |
| Stale text merge | `textToEdits` `src/hardware/HardwareConfigText.hpp:1175-1208`, `saveLocked:282-310`, `needsReview` `:344-348` | no in-tree client sends `confirm_merge` | store `mutex_` | - | 409 `merge_review` `App:8649-8660` |
| Revision header | page sends `X-Apertar-Revision` `WCP:18993`; Core refuses a browser without one `App:8634-8641` | `saveLocked` base | web thread | - | 409 `old_page` |
| Checker findings | `hwconf::validate` `HardwareConfigText.hpp:768-1081`, `newErrors` `:1084-1096` | App start `App:8140-8160`, `get_controls` `App:12428-12436`, every save | start thread, web/command threads; findings counted into atomics `controlsErrors_` / `controlsWarnings_` | not saved | state `controls_errors` / `controls_warnings` `App:9462-9463`, `:12963`; touch chip `UI qml/CameraPage.qml:2711` (`qml/ControlsWarning.qml`); Config and Controls issue boxes |
| Key aliases | one map for all sections `canonicalSection` `HardwareConfigText.hpp:91-102`, `canonicalKey` `:158-208`, global lines `:169-170` (`channel`/`i2c_bus`/`bus_number`/`pcf_bus` -> `bus`, `addr`/`pcf_address` -> `address`) | `parse()` `:258-302` names every key with it; `applyEdit`, `validate` | - | - | wrong bus in checker messages (reader `Pcf8574Input.cpp:273` takes no `pcf_bus`; `Mpu6050RecordingSession.cpp:762` takes no `channel`) |
| Keys an edit may set | `knownKey` `HardwareConfigText.hpp:451-482`, `checkEdits` `:485-500` | `set_controls set.<s>.<k>=` | command thread | - | refusal text; `[gpio_encoders]` refuses `chip`, `pull`, `active_low`, `poll_ms`, `debounce_ms` the reader reads (`GpioInput.cpp:340-355`); accepts `hold_ms`/`double_ms` nobody reads |
| DPI and I2C facts | `hardwareConfigFacts` `App:4966-4982` with `hwconf::parseConfigTxt` `HardwareConfigText.hpp:1109-1149` (`[all]` and `[pi5]` only) | `validate` pin rules (C1 limits them to the header chip) | caller's thread | - | `gpio_dpi` errors |
| `[storage]` / `[media]` value checks | `validate` branches `HardwareConfigText.hpp:828-845`, includes `util/BufferBudget.hpp`, `util/StoragePreroll.hpp` `:5-6` | - | - | - | issues |
| Default template | `defaultHardwareConfigTemplate` `App:5035-5226` (720x720 again since C2): `[gpio] enabled=false`, `[gpio_encoders] enabled=false`, no `chip=`, `[imu] enabled=false`, no `[mpu6050]` | GET `/api/config` shows it when no file and no `/boot` copy `App:6193-6206` | web thread | never written | Config textarea, "Not saved yet" |
| First-start file | nobody: UI `c9d841f` deleted both writers (upstream `UI src/DisplayConfigBridge.cpp:41-326,:587`, `src/Ina219Bridge.cpp:69-342,:497`) | - | - | no file on a fresh camera | UI runs on compiled defaults |
| "Replaced" detection and restore | `replacedByDefault` `HardwareConfigStore.cpp:416-449` against `hardware-last-written.conf` or `adopted-*.conf` | start log `App:8153-8155`; `set_controls restore=true` `App:12786-12796`; Controls message `WCP:18373` | store `mutex_` | `~/.config/apertar-core/hardware-last-written.conf`, `hardware-history/`, `hardware-state.conf` `:386-414` | journal; Controls page |
| GPIO button polarity at start | first sample sets `button.inverted = level` `GpioInput.cpp:620-629` | `pressed = level != inverted` `:631` | GpioInput's own thread, state local to `run()`; rebuilt at every reopen `:752-780` | not saved | one journal line |
| PCF8574 polarity at start | `invertedMask` `src/hardware/Pcf8574Input.cpp:424-433`, reset on reopen `:411` | `pressedMask = levelMask ^ invertedMask` `:435` | Pcf8574Input's thread | not saved | journal line |
| NeoRotary push held at start | `heldAtStartMask` `src/hardware/NeoRotary4Input.cpp:608-630`: skipped until released | - | its thread | - | - |
| Standby wake press | `handleHardwareInputAction` `App:10304-10325`: in Standby a button press dispatches `wake` and returns, under `hardwareInputSequenceMutex_` | the input class does not learn of it: `emitAction` is void `GpioInput.cpp:565-570`; `ButtonGesture` counts the press `src/hardware/ButtonGesture.hpp:21-53` | input thread -> App | - | a later Single/Double/Hold runs with the camera awake |

## How original Apertar does this kind of thing

| Problem | Upstream precedent |
| --- | --- |
| Whole-file save from the browser | `saveHardwareConfigFile` `App:5323-5386`: non-empty, at most 256 KiB, no NUL, `.bak`, `.tmp` + rename. No validation. POST `/api/config` `App:7175-7193` replies `path`, `display_path`, `backup_path`, `backup_display_path`. The browser writes the whole file, `[run_script]` included. WebUI is for a trusted LAN (WEB-6, `WS:156-171`) |
| What happens to a value a reader does not like | The reader keeps its default silently and ignores unknown keys; only mapping errors, unknown actions and script problems are logged at run time (HW-12; `src/hardware/GpioInput.cpp:441-445`; `App:8954` "Hardware input action ignored: unknown action") |
| Key aliases | Flat `key == "a" \|\| key == "b"` chains in each reader, per section (HW-11): `Pcf8574Input.cpp:366-371`, `GpioInput.cpp:431`; `pcf_bus` / `pcf_address` only in `TriggerOutput.cpp:320-323` and `RecordingIndicatorOutput.cpp:359-362`. No shared INI parser (section 5 of the conventions) |
| A programmatic key edit | `writeHardwareConfigValue` re-enters the section at every header of that name and rewrites the key in each copy, `.tmp` + rename (`src/hardware/Mpu6050RecordingSession.cpp:620-668`, HW-8). It writes the file the loader read (`:1297-1300`) |
| Button polarity | Stated by the operator per section with `active_low` (`GpioInput.cpp:433-434`, `Pcf8574Input.cpp:378`). The first sample seeds observed and stable state (`GpioInput.cpp:693-697`, `Pcf8574Input.cpp:500-504`): a button held at start fires nothing, its release fires nothing, the next press fires |
| Wake press | The power button's callback returns bool; on true the gesture is consumed: `gesture.consume(); // A wake press cannot seed another sleep.` (`src/hardware/StandbyPowerButtonInput.hpp:8`, `StandbyPowerButtonInput.cpp:66-71`, `PowerButtonGesture.hpp:31-32`). Buttons fire on press only, so a wake press had no follow-up (`GpioInput.cpp:704-708`); App wakes and returns (`App:8630-8656`); the template says "a button press wakes only" (`App:4360`) |
| Default hardware file | Three hand-kept templates (HW-7). Core only shows its template when the file is missing (`App:4291-4404`, `App:5297`). The touch UI writes its own, larger template to `/home/pi/apertar-hardware.conf` at every start when that path is missing (`UI src/DisplayConfigBridge.cpp:41-326`, call `:587`; copy in `UI src/Ina219Bridge.cpp:69-342`, `:497`). It has `[gpio_buttons] chip=auto active_low=true pull=up poll_ms=12 debounce_ms=60` (`:156-166`), `[gpio_encoders]` with the same keys (`:168-183`), `[imu] enabled=true`, `[mpu6050] enabled=true bus=1 address=0x68 ...` (`:206-232`) |
| Core writing its own file at start | `CameraController` writes `camera_settings.conf` at every start (`src/camera/CameraController.cpp:7646`, `persistSettingsLocked`) |
| Board-dependent `config.txt` reading | None in the hardware path. The port's own `BootConfigText` (`src/hardware/BootConfigText.hpp:84-120`, `readState` `:512-556`) is board-aware and already used by the Boot Config card (`App:3653-3693`) |
| Small helper headers | Only small header-only files sit next to their owner (`src/hardware/ButtonActionList.hpp`); every `.cpp` is listed by name (HW-23) |

## The target

Who validates what:

- The readers stay the authority (HW-12). Nothing new is refused at load.
- The store enforces only what upstream enforced on a whole-file save: non-empty, 256 KiB, no NUL. Every whole-file caller gets these checks, `set_controls text=` included. A stale base is refused, not merged.
- `hwconf::validate` is advisory for whole-file saves: the file is written and the findings come back in the ok reply. For key edits from the Controls page (`set_controls set.<s>.<k>=`), a new error still refuses the edit, because the page writes keys the operator did not type. `force=true` stays for socket clients.
- `hwconf` keeps parse, join, applyEdit, diff, validate and the per-section key list. Its aliases are per section and copy each reader's chain, with the reader line cited. It reads `config.txt` through `BootConfigText` with the board, and it no longer knows about `[storage]` / `[media]` values.

What the browser may change: the whole file, as in 1.6.0, `[run_script]` paths included (subject to owner question 1).

How inputs treat a press:

- At start, and at every reopen, a GPIO or PCF8574 button reads its level, seeds its state from it, and ignores a press already held until it is released. This is upstream's rule, written the way NeoRotary already does it in the port.
- Polarity comes from `active_low` (section-wide) only, as in 1.6.0.
- A press that wakes the camera from Standby is consumed: no Single, Double, Triple or Hold follows from it.

Default file: Core's `defaultHardwareConfigTemplate()` is the one default. It gains `[gpio_buttons]` with `chip=auto`, `active_low`, `pull`, `poll_ms`, `debounce_ms`, plus a comment in `[gpio_encoders]` that these keys are shared, plus `[mpu6050]`. Core writes it through the store at start, only when no hardware file exists at any candidate path and the store has no record of an earlier file. Otherwise nothing changes: the missing/restore path stays.

hwconf: stays new ground, smaller. Split into `.hpp` (types) and `.cpp`, about 150 lines lighter, aliases per section.

| Value | Before (port today) | After | Owner | Set by | Reaches state and UIs |
| --- | --- | --- | --- | --- | --- |
| Whole file from Config page | refused on new checker errors, on `[run_script]` path change, from a browser without the revision header; stale text may merge | written after the three upstream checks; findings returned; stale base refused (409); missing header = current revision | `HardwareConfigStore` | POST `/api/config` (unchanged fields) | ok reply `issues`, `errors` (port fields kept); state `controls_errors` |
| Undo, history restore, `restore=true` | refused when script paths differ | written | store | `set_controls text=` / `restore=true` | as above |
| Key edit (Controls page) | refused on new errors; refuses shared GPIO keys in `[gpio_encoders]`; accepts `hold_ms`/`double_ms`; first copy of a duplicated section only | refused on new errors (unchanged); `knownKey` equals what the readers read; written into every copy of the section | store + `hwconf::knownKey` | `set_controls set.<s>.<k>=` | `get_controls` |
| First write on a `/boot`-only rig | creates a partial `/home/pi` file that hides the `/boot` sections | starts from the `/boot` text, writes `/home/pi` | store | any writer | Config shows the full file |
| Aliases in the checker | one map, global bus/address lines | per section, copied from each reader | `hwconf` (`HardwareConfigText.cpp`) | - | checker messages name the bus the reader uses |
| DPI lines for the pin checks | `[all]` and `[pi5]` only | `BootConfigText` filters for the board (`pi3`/`pi4`/`pi5`/`cm4`/`cm5`/...) | App `hardwareConfigFacts` | - | `gpio_dpi` findings |
| Button held at start | inverted for the session (GPIO, PCF8574); NeoRotary ignored until release | ignored until release on all three | each input class | - | - |
| Normally closed button | auto-detected by being pressed at start | `active_low=false` for the section; per-pin key only if the owner wants it (commit 10) | input class | file | - |
| Wake press from Standby | wakes, then its click or Hold also runs | wakes only | input class + App | - | - |
| Default file content | Core template without `chip=`, input tuning, `[mpu6050]` | template with `[gpio_buttons]` keys, `[gpio_encoders]` shared-key comment, `[mpu6050]` | App `defaultHardwareConfigTemplate` | - | Config textarea when missing |
| Who writes the first file | nobody | Core at start, through the store, once | App `start()` | - | file exists; Config shows it as saved |

Old files: no key moves. A file with `[gpio]` keeps working (every reader takes `[gpio]` as `[gpio_buttons]`, `HardwareConfigText.hpp:55`, `GpioInput.cpp:291`). A file from the 1.6.0 touch UI with `chip=`, `poll_ms=3`, `debounce_ms=40` in `[gpio_encoders]` loads as before and can now be edited key by key. Existing `hardware-history/` and `hardware-state.conf` stay valid.

## Commit plan

All commits are in Apertar-Core. "Check here" uses: `/home/user/build/bin/check_core.sh /home/user/wt/core-work hwin both tests` (both builds and the 17 host tests), then a simulate run:

```bash
D=/tmp/hwin; mkdir -p $D/media $D/cfg
APERTAR_HARDWARE_CONFIG=$D/hw.conf XDG_CONFIG_HOME=$D/cfg HOME=$D \
  /home/user/build/hwin-nolc/apertar-core --simulate --socket $D/core.sock --media $D/media \
  --web-bind 127.0.0.1 --web-port 8765 &
cmd() { curl -s -X POST -H 'Content-Type: application/json' -d "$1" http://127.0.0.1:8765/api/command; }
```

plus `/home/user/build/bin/smoke_core.sh` before and after, diffed, for reply shapes. Every commit keeps the 1.6.0 fields of `/api/config` (GET: `ok path display_path exists size_bytes size_text modified_text text`; POST: `ok path display_path backup_path backup_display_path`) and of `/api/state`.

### 1. hw: a whole-file save writes the file and reports what the checker found

- Repo: Core. Files: `src/hardware/HardwareConfigStore.cpp` `saveLocked`; `HardwareConfigStore.hpp` comment on `StoreFlags::force`.
- What: the `newErrors` refusal (`:336-342`) applies only when `edits` is set. `text` saves compute `issues` and write. `force` is documented as "key edits only". The WebUI already shows issues after a successful save (`WCP:19010-19013`).
- Lines: -3 / +4.
- Check here: save a file the readers accept but the checker flags (`d17=capture` twice in `[gpio_buttons]`): `curl -s -X POST --data-binary @dup.conf http://127.0.0.1:8765/api/config` returns `ok:true` with a `duplicate_key` issue, and the file is written. A key edit that adds an error is still refused: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_buttons.d18":"capture","set.gpio_buttons.d17":"capture"}'`.
- Pi only: none (no hardware path changes).
- Depends on: nothing. Order with command-plane: that theme may later replace `StoreResult.code`; this commit does not touch codes.

### 2. hw: the browser may change [run_script] paths again

- Repo: Core. Files: `HardwareConfigStore.cpp` (delete `scriptPaths()` `:34-42` and the check `:330-335`), `HardwareConfigStore.hpp` (drop `script_paths` from the code list comment).
- What: deleted; nothing added. Undo, history restore and `restore=true` stop failing on path differences. The command that could fire a script from the LAN without a press (`test_input`) already refuses script actions (`d1dcdee`).
- Lines: -16 / +0.
- Check here: POST a text with `path=/home/pi/x.sh` under `[run_script]` -> `ok:true`. Undo after an outside edit of a path -> written.
- Pi only: `P2=run_script1` with a new path, press P2, `journalctl -u apertar-core | grep 'script'` shows the new path.
- Depends on: owner question 1. If the owner keeps "ssh only", this commit becomes: keep the check for `by=webui` text saves, skip it for `by=webui_undo` and `restore=true`, and one README line. About -2 / +8.

### 3. hw: every whole-file save gets the empty, size and binary checks

- Repo: Core. Files: `HardwareConfigStore.cpp` `replace()`; `src/ApertarCoreApp.cpp` POST `/api/config` (`:8628-8633`), delete `checkHardwareConfigText` (`:6235-6255`).
- What moves: the three checks and their three sentences, verbatim from upstream `App:5325-5341`, into `HardwareConfigStore::replace` (refusal code `text`, mapped to 400 as today). Deleted: `checkHardwareConfigText` and its call.
- Lines: -28 / +20.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","text":""}'` -> "Config file cannot be empty.", file untouched. POST `/api/config` with an empty body -> 400 with the same sentence as 1.6.0.
- Pi only: none.
- Depends on: nothing. Commit 15 needs it.

### 4. hw: a whole-file save without a revision header is taken against the current file

- Repo: Core. Files: `App` POST `/api/config` `:8634-8645`.
- What: deleted: the `Origin` branch and its 409 `old_page`. A missing header means base = current revision for every client, as in 1.6.0 (last writer wins with `.bak`). A present header keeps the stale check.
- Lines: -7 / +1.
- Check here: `curl -X POST -H 'Origin: http://127.0.0.1:8765' --data-binary @hw.conf .../api/config` -> 200. With `X-Apertar-Revision: h0123456789abcdef` -> 409.
- Pi only: none.
- Depends on: nothing. Tell webui-state: the page keeps sending the header.

### 5. hw: a stale whole-file save is refused; the merge review is gone

- Repo: Core. Files: `HardwareConfigText.hpp` (delete `textToEdits` `:1175-1208`); `HardwareConfigStore.{hpp,cpp}` (delete `StoreFlags::confirmMerge`, `StoreResult::merged`, `needsReview`, the `textToEdits` branch `:290-297`, `:344-348`); `App` (`confirm_merge` flag `:12808`, `merged` / `needs_review` reply fields `:12833-12834`, the `needsReview` mapping `:8649-8660`); `WCP:19019` drop `"merge_review"`.
- What: a stale text base returns "The file changed since you loaded it. Reload, then change it again." Per-key `conflicts()` for key edits stays.
- Lines: -62 / +3.
- Check here: both builds (the deleted fields are port-only: `smoke_core.sh` diff shows only `merged`, `needs_review` gone from `set_controls`). Simulate: load, edit the file by hand, POST with the old revision -> 409 stale.
- Pi only: none.
- Depends on: command-plane (codes): no conflict, it removes a code they would otherwise have to carry.

### 6. core: the default hardware file template holds the GPIO, encoder and IMU sections

- Repo: Core. File: `App` `defaultHardwareConfigTemplate` `:5035-5226`.
- What moves in (text, from upstream `UI src/DisplayConfigBridge.cpp:156-232`):
  - `[gpio]` becomes `[gpio_buttons]` (the name the 1.6.0 touch UI wrote and the Controls page uses) with `enabled=false`, `chip=auto`, `active_low=true`, `pull=up`, `poll_ms=12`, `debounce_ms=60`, and a comment line: `# chip=auto is the Pi's 40-pin header; another chip by path, for example /dev/gpiochip13.`
  - `[gpio_encoders]` gains the comment `# chip, active_low, pull, poll_ms and debounce_ms are shared with [gpio_buttons]: set them there.` and no keys. Copying `poll_ms=3` / `debounce_ms=40` as the UI did would make them win for the buttons too, because the reader keeps the later line (`GpioInput.cpp:340-355`).
  - The `[gpio_switches]` comment changes to: "chip, pull, active_low and debounce_ms come from [gpio_buttons]."
  - `[mpu6050]` with the UI writer's values (`bus=1`, `address=0x68`, `sample_rate_hz=500`, `gyro_range_dps=1000`, `accel_range_g=8`, `dlpf_hz=98`, `use_fifo=true`, `fifo_batch_samples=24`, `orientation=XYZ`, level and bias keys at 0) and `enabled` as owner question 4 decides (recommended: `enabled=true` in `[imu]` and `[mpu6050]`, as the 1.6.0 file was).
  - `# hotspot_delay_seconds=60` under a `[network]` section, as in the UI writer.
- Lines: -4 / +40.
- Check here: a scratch program running `hwconf::validate` over the new template finds no issue (done for this design: current and proposed template both clean with empty facts). Simulate with no file: GET `/api/config` shows the new text. `get_controls` lists the GPIO card with chip `auto`.
- Pi only: none until commit 7.
- Depends on: C2 (720x720 `[display]`, done). Touch-ui theme: if it restores the UI writer instead (owner question 3), this text is copied into that writer too (HW-7).

### 7. core: Core writes the default hardware file when no copy exists

- Repo: Core. Files: `App` `start()` (before the first reader, after the standby recovery, about `:8025`); `README.md` hardware paragraph.
- What is added: about 12 lines. If no path in `hardwareConfigCandidatePaths()` (`App:4924`) is a regular file, and `~/.config/apertar-core/hardware-last-written.conf` does not exist, and no `hardware-history/adopted-*.conf` exists, then `configStore().replace(kAbsentRevision, defaultHardwareConfigTemplate(), "core", {})`. One journal line: `ApertarCore controls: wrote the default ~/apertar-hardware.conf`. README: "When no hardware file exists, Core writes its template to ~/apertar-hardware.conf at start."
- Why gated so: a file that was moved away on purpose, or lost, leaves a last-written copy behind, so the existing restore path (`replacedByDefault`) handles it and the hazard `c9d841f` removed does not come back. A `/boot` copy counts as a file. The write goes only to the editable path (HW-9).
- Lines: -0 / +16.
- Check here: simulate with an empty `$D`: the file appears with the template text, `hardware-last-written.conf` equals it, GET `/api/config` shows `exists:true`. Second start with the file moved away: no write; the journal says the file was replaced and can be restored. Start with only `$D/cfg/apertar-core/hardware-history/adopted-h....conf`: no write.
- Pi only: on a fresh SD image (or after `mv ~/apertar-hardware.conf ~/hw.keep; mv ~/.config/apertar-core ~/core.keep`), `sudo systemctl restart apertar-core apertar-ui`: the file exists, the touch UI comes up 720x720 square, `journalctl -u apertar-ui | grep INA219` names an existing file. Put the two back afterwards.
- Depends on: 3 (checks in `replace`), 6 (content), owner question 3.

### 8. hw: a button held when its input starts is ignored until it is released

- Repo: Core. Files: `src/hardware/GpioInput.{hpp,cpp}` (`RuntimeButton::inverted` -> `heldAtStart`; `process` `:620-639`); `src/hardware/Pcf8574Input.cpp` (`invertedMask` -> `heldAtStartMask`, `:397-470`).
- What: deleted: the inversion and its journal lines. Added: the NeoRotary rule (`NeoRotary4Input.cpp:608-630`) in the two other button inputs: the first sample seeds observed and stable state (upstream `GpioInput.cpp:693-697`); a button whose first stable state is pressed is skipped by `ButtonGesture` until it reads released. Applies at every reopen too, as upstream re-seeds at reopen (this ends HW-input-classes-F2's polarity half).
- Lines: -24 / +16.
- Check here: both builds; a scratch host program feeding `process()`-equivalent sequences is not possible without the class (state is local to `run()`), so review by reading. `ButtonGesture` is header-only and unchanged.
- Pi only: `[gpio_buttons] enabled=true d17=record_toggle`; hold d17, `sudo systemctl restart apertar-core`, release after "GPIO input enabled" is logged: nothing records. Press once: recording starts; press again: stops. `journalctl -u apertar-core | grep inverted` is empty. Same with a PCF8574 pin. On a Pi 4 and a Pi 5 (chip `pinctrl-bcm2711` / `rp1`); the code path is board-independent.
- Depends on: owner question 2. If the owner's rig has normally closed buttons, commit 10 goes in the same push, before deploying.

### 9. hw: the press that wakes the camera from Standby does nothing else

- Repo: Core. Files: `src/hardware/ButtonGesture.hpp` (add `consume()`); `GpioInput.{hpp,cpp}`, `Pcf8574Input.{hpp,cpp}`, `NeoRotary4Input.{hpp,cpp}` (button callback type and `emitAction`); `src/ApertarCoreApp.{hpp,cpp}` (`handleHardwareInputAction` returns bool; the three constructor lambdas `:7983-7989` return it).
- What is added, shaped like upstream's power button (`StandbyPowerButtonInput.hpp:8`, `.cpp:66-71`):
  - `ButtonGesture::consume()`: `clicks_ = 0; if (down_) { longPress_ = true; holdFired_ = true; }`.
  - A `PressCallback = std::function<bool(const std::string &)>` for the button callback only. Rotation and seen callbacks keep their void type.
  - `emitAction` returns the callback's result (false for an empty action). On true the input calls `gesture.consume()` for that button.
  - `handleHardwareInputAction` returns true exactly when it dispatched `wake` (`App:10316-10322`), false otherwise. `testInputReply` and `handlePowerButtonPress` ignore the result.
  - With only Single or Hold mapped, the wake comes from that gesture; consume then clears what is left of it.
- Lines: -12 / +32.
- Check here: both builds; a scratch host program on `ButtonGesture` (press, consume, release within 500 ms -> no Single; press, consume, hold 3 s -> no Hold). Simulate: `cmd '{"cmd":"enter_standby"}'` then `cmd '{"cmd":"test_input","section":"gpio_buttons","key":"d17"}'` wakes only (this path has no gesture; it shows the return value does not change replies).
- Pi only: `d17=record_toggle`, `d17_hold=standby`, `d17_double=photo`. Enter Standby. Hold d17 3 s: the camera wakes and stays awake (`journalctl -u apertar-core -f` shows one `wake`, no `enter_standby`). Enter Standby, double-click d17: it wakes, no new file under the photos folder. Same on a NeoRotary push and a PCF8574 pin.
- Depends on: 8 (same files; order avoids a merge clash).

### 10. hw: one GPIO or PCF8574 button can be normally closed (only if the owner wants it)

- Repo: Core. Files: `GpioInput.{hpp,cpp}` `loadConfig` (`dN_active_low`), `Pcf8574Input.{hpp,cpp}` (`pinN_active_low`), `HardwareConfigText` `knownKey`, `ControlsModel.hpp` row field, `WCP` one select on the button row.
- What: recipe R11 step 6: a per-pin key next to the section's `active_low`, `parseConfigBool`, no other rule. The kernel flag is per line in the GPIO v2 request (`GPIO_V2_LINE_FLAG_ACTIVE_LOW`, `GpioInput.cpp:519-520`), so GPIO needs one more `attrs` entry; PCF8574 needs a per-pin XOR mask.
- Lines: -2 / +40. Split into Core reader (+25) and page (+15) if done.
- Check here: both builds; Controls page in headless Chromium shows the field and saves `d17_active_low=false`.
- Pi only: a normally closed button on d17 with `d17_active_low=false`: one press records once.
- Depends on: 8; owner question 2. New ground (no per-pin polarity upstream).

### 11. hw: a key edit sets the key in every copy of its section

- Repo: Core. File: `HardwareConfigText.hpp` `applyEdit` Set (`:519-585`).
- What: as upstream `writeHardwareConfigValue` (`Mpu6050RecordingSession.cpp:620-668`): replace the key in each copy of the section; insert a new line only when no copy has it.
- Lines: -6 / +12.
- Check here: key edits from `set_controls` refuse a duplicated section (`checkEdits`), and the trusted writers that skip that check (IMU, storage switches) need the camera or a medium. So: a 10-line scratch program on `hwconf::applyEdits` with `[mpu6050]` twice, both copies holding `gyro_bias_x`; after the edit both hold the new value. Not committed (upstream has no tests, PLT-12).
- Pi only: with `[storage]` twice, `set_buffer_mode` then `grep -n buffer= ~/apertar-hardware.conf` shows the value in both copies.
- Depends on: nothing.

### 12. hw: the first save on a /boot-only rig starts from the /boot file

- Repo: Core. File: `HardwareConfigStore.cpp` `saveLocked` (after `refreshLocked`, `:267-276`).
- What: when the editable file does not exist and `/boot/firmware/apertar-hardware.conf` or `/boot/apertar-hardware.conf` does, `current` starts from that text. The rule already exists for display in `App:6193-6206`; the write still goes to the editable path only (HW-9).
- Lines: -1 / +10.
- Check here: not reachable in the container without a `/boot/firmware` file; run simulate in a scratch mount namespace (`unshare -m` with a bind of `$D/bootfw` on `/boot/firmware`) if root; otherwise read the diff.
- Pi only: move `~/apertar-hardware.conf` to `/boot/firmware/` (and the notes folder aside), restart Core, run Gyro Calibration or `set_buffer_mode`: the new `/home/pi` file holds every section of the `/boot` file plus the edit.
- Depends on: nothing.

### 13. hw: the hardware-state note takes a safe writer name, and the store never sleeps under its lock

- Repo: Core. File: `HardwareConfigStore.cpp` `writeStateLocked` `:406-414` (`safeName(by)`), `settledLocked` `:198-209` (delete the 100 ms sleep and the second stat; the 1 s age check stays).
- Lines: -4 / +1.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_buttons.enabled":"false","by":"x\nwritten_revision=h0"}'` then `cat $D/cfg/apertar-core/hardware-state.conf`: one `written_by=x_written_revision_h0` line.
- Pi only: none.
- Depends on: nothing.

### 14. hw: the pin checks read config.txt through BootConfigText, for every board

- Repo: Core. Files: `HardwareConfigText.hpp` (delete `BootFacts`, `parseConfigTxt`, `dpiCommands` `:1098-1170`); `App` `hardwareConfigFacts` `:4977`; `BootConfigText.hpp:248` comment.
- What: `facts.dpiLines = bootconf::readState(bootconf::parseDocument(text, board), board).displayLines` with `board` from `bootconf::boardFromDeviceTree` as in `bootConfigFacts` (`App:3653-3657`). C1's "DPI and I2C bus 1 rules apply to the header chip only" stays.
- Lines: -76 / +5.
- Check here: both builds; `boot_config_test` passes; simulate with `APERTAR_BOOT_CONFIG`-style path if the route exposes one, else a scratch program over `bootconf::readState` with `[pi4]` and `[cm5]` blocks.
- Pi only: on a Pi 4 with a DPI overlay under `[pi4]`: `get_controls` lists GPIO 0-27 as held; with the overlay only under `[pi5]`: they are free. On a CM5 with `[cm5]`: held.
- Depends on: boot-config-helpers theme (owns `BootConfigText`; if it renames `readState` or `displayLines`, follow it).

### 15. hw: the storage and media value checks run in App, not in the hardware header

- Repo: Core. Files: `HardwareConfigText.hpp` (delete `#include "util/BufferBudget.hpp"`, `"util/StoragePreroll.hpp"` and the two branches `:828-845`); `App`: after each `hwconf::validate` call, append the `bufferConfProblem` / `prerollConfProblem` issues in one App helper next to `refreshBufferRequest`; `tools/storage_buffer_conf_test.cpp`, `tools/storage_preroll_test.cpp` test the two problem functions directly.
- Lines: -20 / +24.
- Check here: both builds; 17 host tests.
- Pi only: none.
- Depends on: storage-settings theme. If it moves `[storage]` buffer keys and `[media]` out of the hardware file first, this commit is only the delete (-20 / +0).

### 16. hw: hwconf moves out of line into HardwareConfigText.cpp

- Repo: Core. Files: `src/hardware/HardwareConfigText.hpp` (types, constants, declarations), new `src/hardware/HardwareConfigText.cpp` (bodies), `CMakeLists.txt` (listed by name after `HardwareConfigStore.cpp`, HW-23), the `// g++` line of the two tools tests (add the `.cpp`).
- What: a move only. `kSections` stays in the header (ControlsModel reads it).
- Lines: about -1 000 / +1 020. Review with `git show --color-moved=dimmed-zebra`.
- Check here: both builds, 17 host tests, `smoke_core.sh` diff empty.
- Pi only: none.
- Depends on: 5, 14, 15 (they delete code first, so less moves).

### 17. hw: hwconf maps key aliases per section, as each reader does

- Repo: Core. File: `HardwareConfigText.cpp` `canonicalKey`.
- What: deleted: the global lines (`:169-170` today). Added: per-section flat chains, each with the reader line it copies:
  - `pcf8574`, `neorotary4`, `grove_analog`, `ina219`, `cfexpress_hat`: `channel`, `i2c_bus` -> `bus`; `addr` -> `address` (`Pcf8574Input.cpp:273-276`, `NeoRotary4Input.cpp:312-315`, `GroveAnalogInput.cpp:281-284`, `App:5285-5288`, `:5338-5341`).
  - `mpu6050`, `bmi160`, `bmi270`, `icm42688p`, `gyro`: `bus_number` -> `bus`; `addr` -> `address` (`Mpu6050RecordingSession.cpp:762-765`).
  - `trigger_output`, `recording_indicator`: `pcf_bus` -> `bus`; `pcf_address` -> `address` (`TriggerOutput.cpp:314-317`, `RecordingIndicatorOutput.cpp:352-355`).
  - `gpio_buttons`, `gpio_encoders`: `gpiochip`, `gpio_chip` -> `chip`; `poll_interval_ms` -> `poll_ms` (`GpioInput.cpp:340-350`).
- A key outside its reader's chain is no longer renamed, so `[pcf8574] pcf_bus=10` shows as a key the reader ignores, which is what happens.
- Lines: -12 / +30.
- Check here: scratch program: `[pcf8574] pcf_bus=10` -> no `bus_missing` for bus 10; `[mpu6050] channel=3` -> not read as bus 3. 17 host tests.
- Pi only: none.
- Depends on: 16.

### 18. hw: set_controls takes the keys the readers read

- Repo: Core. File: `HardwareConfigText.cpp` `knownKey`.
- What: `[gpio_encoders]` accepts `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` (`GpioInput.cpp:340-355`). Both outputs accept `active_low`; `[trigger_output]` accepts `pin` (`TriggerOutput.cpp:310`, `:325`; `RecordingIndicatorOutput.cpp:345`, `:363`). `hold_ms` and `double_ms` are removed (`ButtonGesture.hpp:16-18` fixes the timing in code).
- Lines: -3 / +5.
- Check here: `cmd '{"cmd":"set_controls","base":"<rev>","set.gpio_encoders.poll_ms":"3"}'` -> written, with the existing `gpio_chip_shared`-style finding only for `chip`. `set.gpio_buttons.hold_ms` -> refused.
- Pi only: none.
- Depends on: 16.

### 19. hw: comments in the hardware text store say what the code does

- Repo: Core. Files: `HardwareConfigStore.{hpp,cpp}`, `HardwareConfigText.{hpp,cpp}`, `App` lines touched above (`T37`, `T39`, `T44`, `core.py`, "Patrik", "the text the touch UI used to write" -> "the template the touch UI writes", "(unconfirmed on hardware)" in an operator string).
- Lines: -20 / +12.
- Check here: both builds; `grep -nE 'T[0-9]{2}|core\.py|Patrik|Cinemate' src/hardware/HardwareConfig*` is empty.
- Pi only: none.
- Depends on: 16 (so the comments are edited once, in their final file).

Order rationale: 1-5 restore the 1.6.0 save behaviour first (smallest, most visible). 6-7 give a stock camera its file. 8-10 are the input rules. 11-13 are store bugs. 14-18 reshape `hwconf` once the deletes have shrunk it. 19 is last. The camera works after each: none of them changes a reader's result except 8 and 9, which restore upstream behaviour.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| `HardwareConfigStore`: one writer with revisions, history (20 + adopted), `.bak`, atomic write, file lock, "replaced" detection and `restore=true` | Unchanged apart from the deletes above. Fallible calls still return a `StoreResult` (command-plane decides its error form) | Several writers (Config page, Controls page, IMU, storage switches) share one file; upstream's `saveHardwareConfigFile` shape (checks, `.bak`, `.tmp` + rename) is inside it. The restore path is what allows the touch UI writer to stay deleted. Smaller than upstream's alternative (each writer with its own copy of the write) would not be |
| `hwconf` checker (`HardwareConfigText.{hpp,cpp}`) | Advisory for whole-file saves, blocking only for key edits; per-section alias chains that cite their reader; no `config.txt` parser of its own; no capture-pipeline includes | Upstream has no validator. The Controls page (owner feature) needs to know which pins are taken and what a key means before it writes. The nearest upstream pattern is the per-reader `key ==` chain, so the checker copies that shape and says which reader line it mirrors. It is a deliberate second copy, listed for the original developer like the three templates (HW-7) |
| Core writes the first hardware file | Once, at start, through the store, only when no file and no record of one exist | Upstream writes it from the UI. The port moved ownership of the file to Core (`014fa22`, `c9d841f`); a writer in Core is the smallest way to keep 1.6.0's fresh-camera result without the moved-file hazard. Precedent for a Core-owned file written at start: `camera_settings.conf` (`CameraController.cpp:7646`) |
| Gesture actions (`_single`, `_double`, `_triple`, `_hold`) | Kept; the wake press is consumed (commit 9) | Owner feature; upstream fires Press only. The consume rule makes it obey HW-5 |
| `controls_errors` / `controls_warnings` in state and the touch chip | Kept | HW-22 keeps input health out of state. These count findings about the file, not device health; the chip only says "look at the WebUI". Listed for the owner (question 5) |
| Per-pin `dN_active_low` (only if commit 10 goes in) | One key per pin beside the section key | No per-pin polarity upstream; R11 step 6 is the shape |

## For the owner

1. **`[run_script]` paths from the browser.**
   - Question: may the Config page change them?
   - Options: (a) yes, as 1.6.0 (commit 2 deletes the check); (b) keep "ssh only" (decision Q2) but exempt Undo, history restore and `restore=true`, and say it in the README.
   - Recommendation: (a). The WebUI is a trusted-LAN surface upstream (WEB-6), and since `d1dcdee` a browser can no longer fire a script without a button press.
   - Cost: (a) -16 lines. (b) +8 lines and a rule the original developer has to learn.
2. **Normally closed (1-0-1) buttons.**
   - Question: does any rig need them?
   - Options: (a) no: delete the auto-inversion (commit 8), a whole section can still say `active_low=false`; (b) yes: commit 8 plus a per-pin `dN_active_low` / `pinN_active_low` (commit 10); (c) keep the guess behind an opt-in key.
   - Recommendation: (a), or (b) if the owner's rig has such a button. Before deploying commit 8, run `journalctl -u apertar-core | grep 'taken as inverted'` on the rig: any line means (b).
   - Cost: (b) about +40 lines of new ground. (c) keeps a rule that inverts a held or stuck button for the whole session.
3. **Who writes the first hardware file.**
   - Options: (a) Core, gated (commits 6-7); (b) restore the touch UI's two writers as in 1.6.0 (UI repo, about +590 lines back, and their template must get every port key by hand, HW-7); (c) nobody (today).
   - Recommendation: (a). The touch-ui theme must agree not to restore the UI writers.
   - Cost: (a) +16 lines of new ground. (b) brings back the moved-file hazard `c9d841f` removed and trips Core's own "replaced by the touch UI's default" check.
4. **IMU on or off in the first-start file.**
   - Question: the 1.6.0 touch UI's file had `[imu] enabled=true`, `[mpu6050] enabled=true`; upstream Core's template has `[imu] enabled=false`.
   - Options: (a) on, as a fresh 1.6.0 camera was; (b) off, as Core's template and HW-20 ("accessories ship disabled").
   - Recommendation: (a). It reproduces what a stock camera got. With no IMU fitted, only the Gyro panel's live read probes bus 1 at 0x68, as in 1.6.0.
   - Cost: none in code; two words in the template.
5. **Key edits still refused on new errors, and the touch chip.**
   - Question: should the Controls page's key edits also become advisory? Should the camera page keep its "Controls: N errors" chip?
   - Recommendation: keep both. The page writes keys the operator did not type, so it should not introduce a clash. The chip is the only sign on the camera that the file has a problem.
   - Cost: none.
6. **hwconf's future.**
   - Options: (a) keep it as a second, cited copy (this plan); (b) let each reader parse from text, so the checker calls the readers (touches 8 upstream reader files and their `loadConfig` signatures); (c) drop the checker and with it the Controls page's pin checks.
   - Recommendation: (a) now; (b) only if the original developer asks for it after the merge.

## Risks and what was not determined

- `core-work` is being changed in parallel: HEAD moved from `7dc6f7a` to `d1dcdee` while this was read, and `src/ApertarCoreApp.cpp` line numbers shifted by 4 above line 12 400. Re-grep each anchor before editing.
- Command-plane may replace `StoreResult.code` and the `code` / `new_errors` fields in error replies. Commits 1-5 do not depend on that change, and it does not depend on them.
- Webui-state may move Undo and Check from `set_controls text=` to `/api/config` (WCP-09-F12). Commit 3 makes the checks the same on both doors either way.
- The first-start writer and the touch UI start at the same time at boot. If the UI reads before Core writes, it runs on its compiled defaults, which since U1 equal the template's `[display]`. Not seen on a Pi.
- `$APERTAR_HARDWARE_CONFIG` pointing under `/boot`: commit 7 would write there. Upstream writes the editable path the same way (`App:5343`). Not changed.
- Commit 8 on a rig that relied on auto-inversion: its normally closed buttons fire on release after the update. Check the journal before deploying (owner question 2).
- Commit 9's "consume" when the wake comes from a Single (no Press mapped): the release has already happened, so `consume()` only clears the count. Reasoned, not run.
- Switch positions (`[gpio_switches]`) are still applied at every GpioInput start and reopen, including after each Controls save of the GPIO group (HW-input-classes-F2 switch half, F6). Not designed here: it is a rule about the switches feature, not about button polarity.
- DPI pins: commit 14 fixes which lines count. Whether a 16- or 18-bit DPI mode leaves upper header pins free (WCP-09-F13) needs the overlay pin maps. With commit 1, a false `gpio_dpi` finding no longer blocks a text save; it still blocks a key edit.
- Not run here: anything with real GPIO, I2C or Standby. The scratch check of the template (both versions clean under `hwconf::validate`, empty facts) was run in this container.

## Findings covered

| Finding | Commit |
| --- | --- |
| HW-config-text-store-F1 | 1 |
| HW-config-text-store-F2 | 2 (or its variant, owner question 1) |
| HW-config-text-store-F3 | 16, 17 (validator kept advisory by 1) |
| HW-controls-model-F2 | 8 (10 if the owner wants per-pin polarity) |
| HW-input-classes-F1 | 9 |
| App-2-F2 | 6 |
| UI-bridges-F2 | 7 |
| X-board-support-1 | done by C1 `04fe197`; the remaining key refusals in 18 |
| X-knobs-1 | 18 |
| X-stock-behaviour-2 | 7 |
| HW-config-text-store-F4 | 11 |
| HW-config-text-store-F5 | 3 |
| HW-config-text-store-F6, HW-input-classes-F9 | 12 |
| HW-config-text-store-F7 | 5 |
| HW-config-text-store-F8, App-3-F4 | 4 |
| HW-config-text-store-F10 | 15 |
| HW-config-text-store-F11, F12, App-2-F12, X-board-support-5 | 14 |
| HW-config-text-store-F13 | 19 |
| HW-config-text-store-F15 | 13 |
| HW-controls-model-F1 | done by C1 `04fe197` |
| HW-controls-model-F3 | 18 for the refused keys; not covered: the missing page rows (`open_drain`, `pulse_ms`, `events`, Grove channels) are page content, webui-state |
| HW-controls-model-F4 | 18 |
| HW-input-classes-F2 | 8 for the polarity half; switch half not covered (see Risks) |
| App-2-F11 | kept as new ground (section above); merge review trimmed by 5 |
| App-2-F10 | partly by 7 (a fresh camera gets `[cfexpress_hat] enabled=true` in its file); the reader default is not covered, storage-settings owns the hat watcher |
| HW-config-text-store-F9 | not covered: error codes and issue arrays in error replies belong to command-plane |
| HW-config-text-store-F14 | not covered: storage-settings (the storage switch blocks) |
| HW-controls-model-F7 | not covered: the action-name parser is a separate mechanism (`ActionCatalog`); its blocking effect on text saves ends with 1 |
| HW-controls-model-F5, F6, F8, F9, F10, F11, F12, F14, F15, F16 | not covered: action catalog, Controls JSON and probes, not the save, polarity, wake or default-file mechanism |
| HW-controls-model-F13, HW-input-classes-F3, F4, F5, F7, F8, F10, F11 | not covered: GpioInput loop shape (edge events, lambdas, callbacks, comments); a separate input-loop pass |
| HW-input-classes-F6 | not covered: switches feature rule (see Risks) |
| WCP-09-F13 | not covered: needs DPI overlay pin maps (see Risks) |

## Challenge

Read at Core `/home/user/wt/core-work` `0d13a6f` (hardware files unchanged since `d1dcdee`: `git diff --stat d1dcdee HEAD` touches only README, Types.hpp, CameraController.cpp, WebControlPage.cpp), UI `ac1fc28`, upstream `upstream-1.6.0`. Port lines `@0d13a6f`.

Precedents checked and found as cited: `saveHardwareConfigFile` `App:5323-5386@upstream-1.6.0` (three checks, `.bak`, `.tmp` + rename); POST `/api/config` `App:7175-7193@upstream-1.6.0`; `StandbyPowerButtonInput.hpp:8` / `.cpp:66-71` and `PowerButtonGesture.hpp:31` (`consume()`); upstream GPIO and PCF8574 seed stable state from the first sample (`GpioInput.cpp:693-697`, `Pcf8574Input.cpp:500-504@upstream-1.6.0`) and fire on press only (`GpioInput.cpp:703-708`); `handleHardwareInputAction` Standby branch identical in both trees (`App:8642-8650@upstream-1.6.0`, `App:10316-10323`); `camera_settings.conf` written at start (`CameraController.cpp:7646@upstream-1.6.0`); UI writer content (`UI src/DisplayConfigBridge.cpp:41-326@upstream-1.6.0`).

| Point | What the design says | What the code says (file:line) | What must change |
| --- | --- | --- | --- |
| b, commit 1 | Files: `HardwareConfigStore.cpp` and `.hpp` only. "The WebUI already shows issues after a successful save" | True for Save (`WCP:19010-19013`). But Check, which runs the same text through `set_controls dry_run`, tells the operator "Save is refused until the errors are fixed." (`WCP:18879`). After commit 1 that sentence is false | Add `WCP:18879` to commit 1: "... errors. Save writes the file anyway; the readers skip what they cannot use." (+1 / -1). Also edit the `StoreFlags::force` comment `HardwareConfigStore.hpp:19` |
| c, commit 6 + 7 | Commit 7 writes Core's template on a stock camera. Commit 6 changes only GPIO, encoder, IMU and network text | The template has live port-invented keys: `[storage] buffer=frames`, `buffer_ram_fraction=0.6`, `buffer_ram_floor_mb=512`, `buffer_ram_max_fraction=0.5` (`App:5058-5061`), `[camera] clear_hdr_iso_max_12bit=720`, `clear_hdr_iso_max_16bit=1585` (`App:5082-5083`). Not in fork main (`grep clear_hdr_iso_max /home/user/wt/core-main/src/ApertarCoreApp.cpp` is empty), not in upstream. Readers default to the same numbers (`CameraController.cpp:2937-2940`), so behaviour is the same today. Once written, the file pins them: when camera-modes (Clear HDR caps) or storage-settings (buffer keys) changes a default or moves a key, every camera Core seeded keeps the old value | Commit 6 also turns these six lines into comments (`# buffer=frames`, ...), the way `[media]` already is (`App:5071-5077`). Then the first-start file holds no live port key (requirement 3) and the readers still use their defaults. About -6 / +6 more. Name storage-settings and camera-modes as dependencies of commit 7: commit 7 goes in after their template text is final |
| c, commit 6 | "The template carries what the 1.6.0 touch UI used to write" | Commit 6 carries a subset. Not carried, without a reason given: `[pcf8574] active_low=true poll_ms=40 debounce_ms=60 pin0..7=none`, `[neorotary4] poll_ms debounce_ms invert_direction reset_on_start max_events_per_poll` and the encoder example mappings, `[grove_analog]` tuning and examples, `[bmi160]`, `[bmi270]`, `[icm42688p]` sections, the `[imu]` driver list comment, `[display] ui_rotation=normal` (`UI src/DisplayConfigBridge.cpp:74-99,:131-155,:184-198,:199-205,:234-298,:312-317@upstream-1.6.0`) | Commit 6 lists every section of the UI writer and says per section "carried" or "left out because ...". Minimum to carry: the `[imu]` driver comment and the three IMU sections with `enabled=false` (they document `driver=`), and the PCF8574 tuning keys (the same kind of loss as chip=). `ui_rotation` belongs to touch-ui (name it). Lines then about -10 / +90; still one idea (template text), reviewable as text |
| b, commit 7 | Gate: no candidate file, no `hardware-last-written.conf`, no `adopted-*.conf`. Check with `--simulate` | Order at start: the write would happen at about `App:8025`; `store.adopt()` runs later (`App:8148`) and adopts the template Core just wrote as "Before Controls (as Core first found it)" (`WCP:18642`), which is not what Core found. `saveLocked` creates the parent directory (`HardwareConfigStore.cpp:256`), so a `--simulate` run on a dev machine without `APERTAR_HARDWARE_CONFIG` writes `/home/pi/apertar-hardware.conf` | Skip `adopt()` in the same start when Core wrote the file (one `bool`, +2). Keep the write in `--simulate` (the check needs it) but say in README that simulate writes the file too, or gate it on `!options_.simulateCamera` and test with a scratch program instead. State which |
| g, commit 7 | Pi: restart `apertar-core apertar-ui`; the touch UI comes up 720x720; the INA219 log names an existing file | The UI comes up 720x720 on its compiled defaults with no file (C2, design Risks), so that does not show the file was read. Both units start together, so the INA219 line can come before Core's write | Pi step: `sudo systemctl stop apertar-ui; sudo systemctl restart apertar-core; sleep 5; ls -l ~/apertar-hardware.conf ~/.config/apertar-core/hardware-last-written.conf; journalctl -u apertar-core -b \| grep 'wrote the default'; sudo systemctl start apertar-ui; journalctl -u apertar-ui -b \| grep -i ina219` (the INA219 line names `/home/pi/apertar-hardware.conf`) |
| b, commit 9 | `PressCallback` "for the button callback only" | In `GpioInput` the switches use the same callback: `emitAction(position.positions[...])` (`GpioInput.cpp:666`, `:680`) goes through `actionCallback_` = `handleHardwareInputAction(action)` with `buttonPress=true` (`App:7983`). So a switch flipped in Standby wakes the camera, and its new position is never applied after the wake (the input already counts it as stable). Port-only (upstream has no switches) | Commit 9 leaves switches as they are (they ignore the result) and says so. The rule for a switch in Standby (wake, or ignore like a turn with `buttonPress=false`, then apply the position on wake) goes on the owner's list as question 7. Not designed here |
| g, commit 9 | Pi: Standby, double-click d17 (`d17=record_toggle`, `d17_double=photo`): "it wakes, no new file under the photos folder" | `dispatchHardwareInputCommand` runs the wake synchronously on the input thread (`App:10121-10130`). The second press of the double click is a new press: Press fires `record_toggle` with the camera awake, and its release counts one click (Single). Same in 1.6.0 (second press fires its action) | Expected result in the Pi step: "wakes; no photo; the second press starts a take (as in 1.6.0); stop it". Otherwise the tester reads a correct build as a failure |
| b, commit 15 | App appends `bufferConfProblem` / `prerollConfProblem` issues "after each `hwconf::validate` call"; tests "test the two problem functions directly" | The store calls `hwconf::validate` itself (`HardwareConfigStore.cpp:324`, `:336`): App cannot add issues there without a hook into the store. The tests already test the problem functions (`tools/storage_preroll_test.cpp:22-28`) and also test the validator's `[storage]` / `[media]` issues (`tools/storage_preroll_test.cpp:31-42`, `tools/storage_buffer_conf_test.cpp:15-20` and 16 `bufferIssues` uses): commit 15 as written breaks two host tests | Commit 15 becomes delete-only: drop the two includes and the two branches (`HardwareConfigText.hpp:5-6`, `:829-845`), and in the same commit drop the validator checks from both tests. The readers already keep their default for a bad value (`BufferBudget.hpp:176`, `StoragePreroll.hpp:81`), as HW-12 says. About -45 / +0. Whether the Config page should still name a bad buffer value goes to storage-settings |
| b, commit 17 | Per-section chains: I2C devices `channel`/`i2c_bus`/`addr`; IMU `bus_number`/`addr`; outputs `pcf_bus`/`pcf_address`; GPIO `gpiochip`/`gpio_chip`/`poll_interval_ms` | Deleting the global lines (`HardwareConfigText.hpp:169-172`) also drops aliases the readers do read and the lists leave out: `poll_interval_ms` in `[pcf8574]`, `[neorotary4]`, `[grove_analog]` (`Pcf8574Input.cpp:279`, `NeoRotary4Input.cpp:318`, `GroveAnalogInput.cpp:287`); `chip`/`gpiochip`/`gpio_chip` in both outputs (`TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:340`); `bias` in `[gpio_encoders]` (`GpioInput.cpp:347`; today only the buttons branch maps it, `HardwareConfigText.hpp:188`). The template itself has `gpiochip=auto` in both outputs (`App:5172`, `:5186`): after commit 17 as listed, `set.trigger_output.chip` from the Controls card (`ControlsModel.hpp:272`) no longer finds that line and appends a second `chip=` line | Commit 17 copies each reader's whole `key ==` chain for the keys the checker or `applyEdit` names, and the commit message lists them reader by reader. Check here: a scratch program running `applyEdits` with `set.trigger_output.chip=/dev/gpiochip0` on the template leaves one chip line |
| c, old files and commit 18 | "A file from the 1.6.0 touch UI with `chip=`, `poll_ms=3`, `debounce_ms=40` in `[gpio_encoders]` loads as before and can now be edited key by key." Commit 18 lets `set_controls` set the five shared keys in `[gpio_encoders]` | The reader keeps the later line across both sections (`GpioInput.cpp:340-355`), and the 1.6.0 UI file puts `[gpio_encoders]` after `[gpio_buttons]` (`UI src/DisplayConfigBridge.cpp:156-183@upstream-1.6.0`). The Controls card shows and writes these keys in `[gpio_buttons]` only (`ControlsModel.hpp:259-266`, `effectiveValue` of that section `:316`). On every 1.6.0-written file the card shows debounce 60 and poll 12 while the reader uses 40 and 3, and a card edit of either has no effect. The checker warns for this only for `chip` (`gpio_chip_shared`, `HardwareConfigText.hpp:936-938`). Accepting the keys in `[gpio_encoders]` (commit 18) adds a second way to write the overriding line | Commit 18 keeps refusing the five keys in `[gpio_encoders]`, with the message X-knobs-1 proposes: "Set chip, pull, active_low, poll_ms and debounce_ms in [gpio_buttons]: the encoders share them." It keeps the rest (outputs `active_low` and `pin`; drop `hold_ms`/`double_ms`; nothing sends them, `grep -rn hold_ms src` finds only `knownKey`). New commit 18b (missing): the `gpio_chip_shared` warning covers all five shared keys (one loop over the five names, about -3 / +8), so the card's page shows which line wins |
| d, commit 13 | One commit: safe writer name in `hardware-state.conf`, and no sleep under the store lock | Two ideas. The first is an injection fix (`by` comes from the command field, `App:12813`, also `:12856`, `:12896`, `:12930`, written raw at `HardwareConfigStore.cpp:409-413`). The second changes the "being written" detection: the 100 ms second stat (`:206-208`) is what catches an editor still writing a file older than 1 s | Split: 13a "hw: the hardware-state note takes a safe writer name" (-1 / +1). 13b "hw: the store does not wait 100 ms under its lock" only with a reason the 1 s age check alone is enough; otherwise drop 13b |
| g, commit 14 | Check here: "simulate with `APERTAR_BOOT_CONFIG`-style path if the route exposes one" | `APERTAR_BOOT_CONFIG` exists (`App:3505-3510`). The board comes from `/proc/device-tree` (`App:3655-3656`), which this container does not have, so simulate exercises only the unknown-board case. Today's parser applies `[pi5]` on every board (`HardwareConfigText.hpp:1120`); with `BootConfigText` an unknown board may not | Check here: a scratch program over `bootconf::readState(bootconf::parseDocument(text, board), board)` with an explicit board per case (`pi4`, `pi5`, `cm5`, unknown), plus simulate with `APERTAR_BOOT_CONFIG=$D/config.txt`. State what an unknown board does with `[pi5]` lines |
| c, commit 5 | Deletes the merge review, `confirm_merge`, `merged`, `needs_review`; "no in-tree client sends `confirm_merge`" | True in tree (`grep -rn confirm_merge` finds only `App:12808`). The store's header names "core.py saves" as a writer (`HardwareConfigStore.hpp:2-3`), a client outside these trees | Commit stands. Add one line to the owner's list: does core.py (or any script on the rig) send `confirm_merge` or read `needs_review`? |
| f, owner's list | Question 4: "With no IMU fitted, only the Gyro panel's live read probes bus 1 at 0x68, as in 1.6.0" | Not shown in the design with a file:line | Unconfirmed. Settle with `grep -n "enabled" src/hardware/Mpu6050RecordingSession.cpp` and the callers of its start in `App` before the owner is asked |
| e, commit 3 | The three checks move into `replace()` | `saveLocked` returns ok without writing when `next == current` (`HardwareConfigStore.cpp:325-328`) and handles a stale base first (`:282`) | The checks go at the top of `replace()`, before `saveLocked`, so an empty text is refused whatever the base. `kMaxEditableHardwareConfigBytes` (`App:107`, its only other use is `:6243`) moves with them |

Checked and found sound: commit 2 (the only script guard is `HardwareConfigStore.cpp:34-42,:330-335`; `test_input` refuses scripts, `App:12408-12410`); commit 4 (`App:8634-8641`); commit 8 (PCF8574 already seeds stable state at the first sample, `Pcf8574Input.cpp:437-441`, so without a held-at-start skip the removal alone would fire Press for a held button; the design has the skip; GPIO rebuilds its `RuntimeButton`s at every reopen, `GpioInput.cpp:752-780`); commit 9's callback change builds (all three constructor lambdas are in `App:7983-7989`; `seenCallback_` keeps `ActionCallback`); commit 12 (the GET already shows the `/boot` text, `App:6193-6206`); commit 16 needs the `.cpp` in the two tests' `// g++` lines only while they still include the header (they do: both call `hwconf::parse` / `applyEdits`).

### Verdict

- Stand: 2, 3 (with the placement above), 4, 5 (plus the owner line), 8, 10 (only on the owner's answer), 11, 12, 16, 19.
- Change: 1 (add `WCP:18879`), 6 (comment out the six live port keys; account for every UI-writer section), 7 (dependencies on storage-settings and camera-modes; no adopt of its own write; simulate rule; Pi step), 9 (switches named; Pi expectation for the double click), 13 (split into 13a, 13b with a reason or dropped), 14 (check with an explicit board), 15 (delete-only, tests edited in the same commit), 17 (each reader's whole chain), 18 (keep the refusal with a message naming `[gpio_buttons]`).
- Dropped: none.
- Missing: 18b, the shared-GPIO-key warning for all five keys. Owner's list gains question 7 (a switch in Standby) and the core.py line under commit 5.
