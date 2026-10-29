# Controls: Cinemate's GPIO dropdown and method assigning, Apertar style. How it works, what to build, what to measure first

2026-10-28, cloud session, designer pass (v1). Built from the four reader reports in this folder (`r1-cinemate-gpio.md`,
`r2-apertar-core-hw.md`, `r3-apertar-readers-ui.md`, `r4-kb-hardware.md`). Every point the design rests on was reopened in the
code at the commits below. Read-only on every repository. Nothing ran on the Pi. Run on the host here:

- The sketch `sketch/hardware/ActionCatalog.hpp` + `sketch/hardware/HardwareConfigText.hpp` with `sketch/controls_test.cpp`
  (g++ 13.3, `-std=c++20 -Wall -Wextra -Werror`): **51 of 51 checks pass**. The test compiles the three real
  `normalizeSingleAction` copies from Core `0296ed1` (extracted read-only by `sketch/make_old.sh`) and compares them with the
  new catalog on 355 tokens.
- `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude` on Core `0296ed1`: `ApertarCoreApp.cpp`, `GpioInput.cpp`,
  `NeoRotary4Input.cpp`, `Pcf8574Input.cpp`, `Mpu6050RecordingSession.cpp`: **0 errors each**. So, unlike T34, every Core file
  this project touches can be checked on the host before the Pi.

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `App`, `App.hpp` | `src/ApertarCoreApp.cpp`, `.hpp` | Core `scratchpad/controls/core-tip` `0296ed1` = Patrik's GitHub `cinemate-port` tip |
| `Web` | `src/web/WebControlPage.cpp` | same |
| `HW/` | `src/hardware/` | same |
| `SF`, `CP` | `src/util/SettingsFile.hpp`, `src/ipc/ControlProtocol.cpp` | same |
| `UI:` | touch UI repo (`ApertarUI`, automounter, network helper, standby helpers) | `scratchpad/controls/ui-tip` `5aab7e2` = GitHub `cinemate-port` tip |
| `Cm:` | Cinemate | `/home/user/tiramisioux/cinemate` `d6cc93e` |
| `SRC`, `HL`, `TIDX`, `TUT` | KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`, `lessons/hardware-log.md`, `tutorials/README.md`, `llm/tutoring.md` | KB `/home/user/apertar-kb` `b47f700` |
| `R1`-`R4` | the reader reports | this folder |
| `sketch` | `sketch/hardware/*.hpp`, `sketch/controls_test.cpp` | this folder (host-tested here) |

Labels: **CONFIRMED** = I opened the line (or ran the command) on the tree above. **PROBABLE** = derived; the derivation is given.
**UNCONFIRMED** = not checked, or only the Pi can settle it. A claim taken from a reader report without reopening says so (`R2 §x`).

Tutorial numbers used here (T33-T35 are taken by the ramp and ladder work):

| Number | What | Repo |
| --- | --- | --- |
| T36 | One action vocabulary: `ActionCatalog.hpp` replaces the three `normalizeSingleAction` copies; `list_actions` | Core |
| T37 | Core owns `~/apertar-hardware.conf`: text model, validator, store (lock, revision, history); `get_controls`, `set_controls text=` | Core (+ 1 WebUI function) |
| T38 | Apply without a restart: reload worker, key edits with a per-key merge, driver state in `get_state`, `apply_controls` | Core |
| T39 | I2C devices: buses, `config.txt` facts, probes, scan; WebUI **Controls** panel part 1 (status + I2C devices card) | Core + WebUI |
| T40 | The easy editor: inputs and outputs cards (rows, pin pickers, gesture lines, action chips, drag and drop) | WebUI (+ a small Core model) |
| T41 | The text editor for advanced users: the **Config** panel with line numbers, Check, diff, conflicts, history | WebUI (+ Core history) |
| T42 | Hold and double press on every button source (`ButtonGesture.hpp`) | Core + WebUI |
| T43 | Touch UI: read-only Controls card, the two template writers removed, the gyro page through Core | UI repo |

`tutorial.py` finds a note by `T` + two digits (T34 design §0), so no `T36a`. T36-T38 come first because everything else
writes through them. T39 is the first that changes what Patrik sees, and it is his NeoRotary fix done by the software.

---

## 0. Short answer

1. **The system-controlled file is the existing `~/apertar-hardware.conf`.** It stays where 15 readers in 4 processes look.
   What is new: Core becomes its writer (one function, a lock, a revision, atomic writes, a history), and it has a schema and
   a validator. Core's own notes about the file go in `~/.config/apertar-core/` (history, last written revision).
2. **Moving or splitting the file is rejected.** A move needs every reader changed in two repos, plus a root automounter
   reinstall. The UI regenerates the old path from its template whenever it is missing, with `bus=10` and `enabled=false`,
   which silently undoes the NeoRotary fix. A split puts the hat's bus and the encoder's bus in two different files.
3. **Format:** the INI the readers already parse. One key per line, comments kept. Core writes canonical names and
   `true`/`false`. Core never writes a comment after a value (Core's hat and INA219 readers then ignore the value). An edit
   rewrites only the lines it changes (sketch: byte-identical round trip, 51 checks).
4. **Two editors, one file.** Easy mode sends key edits (`set.neorotary4.bus=1`). Core merges them per key against the
   revision the page loaded, so a hand edit to another key survives. Text mode sends the whole file and is refused if the file
   changed since it was loaded. Hand edits over ssh are kept: within 2 s Core notices, validates and says so, but applies
   them only on **Apply** or at the next start.
5. **API:** `get_controls`, `set_controls` (with `dry_run`), `apply_controls`, `list_actions`, `scan_i2c`, `probe_device`.
   Plus `hardware_status` and `controls_revision` in `get_state` and `/api/state`, and a `controls` event. All flat scalar
   fields, as the protocol requires (`CP:163-230`).
6. **One action vocabulary.** `src/hardware/ActionCatalog.hpp` replaces the three hand-copied `normalizeSingleAction`
   functions (host test: identical on 355 tokens). Validation and `list_actions` (labels, groups, argument value lists taken
   from Core's own preset lists) read the same table. The WebUI never keeps a fourth copy.
7. **Live apply.** After a save, a Core worker thread restarts the six input and output drivers in boot order. It runs
   outside `commandMutex_`, so a button action in flight cannot deadlock it. The INA219 and the hat watcher reload too. The
   automounter, touch UI and network helper still need a restart, and the reply prints the exact command for Patrik.
8. **WebUI.** A new **Controls** panel in the WebUI's own style (settings cards, pills, selects):
   - *I2C devices*: a bus select fed from `/dev/i2c-*`, address, Probe and Scan, and guided text for what only Patrik does in
     `config.txt`.
   - *Inputs*: one row per button or knob, one dropdown per gesture, action chips you drag to reorder, pins already in use
     greyed out.
   - *Outputs*: tally and trigger.

   The existing **Config** panel becomes the advanced text view, with line numbers, Check, a diff before Save and history.
9. **Cinemate has no drag and drop for controls** (only for value chips, `R1 §0`). The drag here is Apertar's own (T34's
   pointer-event pattern), always with a dropdown alternative. Cinemate's six editor defects are avoided by construction
   (§9.3).
10. **Measure first** (§8, all read-only as `pi`): the live file, which buses and IDs answer on bus 1, a seesaw ID read while
    Core polls the chip, and GPIO line info. Questions only you can answer: Q1 (keep the path), Q2 (script paths from the
    browser), Q4 (hold and double press), Q7 (INA219 off).

---

## 1. How the system works today

### 1.1 Where things are (operator)

| Surface | What you get today | Cite |
| --- | --- | --- |
| `~/apertar-hardware.conf` over ssh | Everything. About 19 sections, aliases, comments. No check: an unknown action is a silent button; a bad bus is a silent device | `R2 §1.4`; unknown action logged only at press, `App:9147` CONFIRMED |
| WebUI Settings → **Config** | One raw textarea. Reload and Save. Save keeps one `.bak`, then writes `.tmp` and renames. It checks only "not empty, ≤ 256 KiB, no NUL". It reloads nothing: "may need ApertarCore or the UI restarted" | `Web:3840-3872`, `App:5463-5526`, `App:66` CONFIRMED |
| WebUI Record → Gyro | IMU driver, orientation, sync, level, calibration, through Core commands that rewrite single keys | `R2 §4`; `App:10112-10189` CONFIRMED (`set_imu_driver` at `:10112`) |
| Touch UI | Nothing for buttons, knobs, buses or the hat. The INA219 card says "Check /home/pi/apertar-hardware.conf". The gyro page writes the file itself | `R3 §2.1-2.2`; `UI:qml/SettingsPage.qml:4507-4526` |
| Journal | The only place a driver error shows, e.g. `NeoRotary4 input: /dev/i2c-1: No such file or directory`, retried every second | `HW/NeoRotary4Input.cpp:614-622`, `:635-638` CONFIRMED; `lastError()` read only for trigger and LED at start, `App:7026-7041` CONFIRMED (grep) |
| `config.txt` | Patrik's, by hand (house rule). The DPI overlays that take GPIO 0-27 live there | `SRC §3.2`; rule `R4 R2` |

### 1.2 Operator view: three walkthroughs

**A. The NeoRotary fix (2026-10-23), today and after this project**

| Step | Today (`SRC §4`, `HL` 2026-10-23) | After T39 |
| --- | --- | --- |
| Symptom | knobs dead; nothing on screen | Controls → I2C devices, NeoRotary 4 row, red: "Bus 1 does not exist on this Pi (buses: 10, 13, 14, 15). GPIO 2/3 are held by the DPI overlay on config.txt line 76." |
| Find why | `i2cdetect -l`, `pinctrl get 2,3`, reading the hat schematic (an evening) | the same row's guide box: the three `dtoverlay` lines with their numbers, and the exact commands for you: `sudo cp …config.txt …config.txt.bak`, `sudo sed -i '76,78 s/^dtoverlay=/#dtoverlay=/' /boot/firmware/config.txt`, `sudo reboot`. Apertar never edits `config.txt` |
| After the reboot | `i2cdetect -y 1` shows `34` and `49` | Bus select now offers 1, 10, 13, 14. **Scan bus 1**: `0x34 CFE hat (answered 0x02)`, `0x49 NeoRotary 4 (seesaw ID 0x87)` |
| Point the config at bus 1 | ssh, type `[cfexpress_hat] bus=1`, `[neorotary4] enabled=true bus=1 address=0x49` | Hat row: bus select 1. NeoRotary row: On, bus 1. **Save** shows a 3-line diff |
| Make it work | reboot, or restart Core, UI and automounter (Patrik) | Core restarts its drivers in about a second; NeoRotary row: "Connected". The reply lists one thing left for you: `sudo systemctl restart apertar-cfe-automounter` (it reads the hat's bus only at start) |
| Side effect: HDMI became the 720x720 main screen | `[display]` keys by hand, UI restart | unchanged: `[display]` is text-mode only (§4.2) |

**B. Remap knob 4's press to zebra (planned T05, `TUT:81`)**

| | Today | After T40 |
| --- | --- | --- |
| Edit | `encoder3_press=zebra` over ssh. A typo (`zebrra`) is silent until you press, then a journal line | Inputs → NeoRotary 4 → Knob 4 → Press: dropdown "Monitoring › Zebra on / off". Typed in the pencil field, `zebrra` is red: "Unknown action 'zebrra'. Did you mean zebra?" |
| Apply | Core restart (Patrik) | Save, live in about a second |

**C. A hand edit over ssh while the WebUI page is open**

| | Today | After T38 |
| --- | --- | --- |
| Patrik types `bus=10` under `[cfexpress_hat]` in nano | — | Within 2 s: journal `ApertarCore controls: ~/apertar-hardware.conf changed outside Apertar (h4b1…): 0 errors, 0 warnings; not applied`. Both panels show a banner: "Changed outside Apertar at 21:14. Not applied. [Apply] [Show changes]" |
| Meanwhile the page saves a knob change | Config textarea: Save overwrites the ssh edit; the `.bak` keeps one copy (`R3 §4.1` hazard 1) | Easy mode: merged. Both changes are in the file. Text mode: refused, "The file changed since you opened it (outside Apertar, 21:14). Your text is kept. [Show changes] [Load the new file]" |
| The page saves the hat's bus too | lost update | refused: "cfexpress_hat.bus changed since you loaded it: you saw 1, the file now says 10 (outside Apertar, 21:14). Reload to see it." (sketch check 7) |

### 1.3 Code view: the same three

**Read path today.** Each reader builds the candidate list `$APERTAR_HARDWARE_CONFIG` → `/home/pi/…` → `/boot/firmware/…` →
`/boot/…` (`App:4293-4311` CONFIRMED). Two rules decide which file it takes (`R2 §1.1`, CONFIRMED for the hat at
`App:4556-4596`, which returns after the first existing file, and for NeoRotary4 at `HW/NeoRotary4Input.cpp:355-444`):

- the first file that exists, for INA219, the hat, trigger, LED, IMU, the Python helper and the automounter;
- the first file that has the section, for GPIO, PCF8574, NeoRotary4 and Grove.

| When | Who reads | Cite |
| --- | --- | --- |
| Core start | trigger → PCF8574 → NeoRotary4 → GPIO → (power button) → Grove → LED, then the LED state is re-synced | `App:7026-7043` CONFIRMED |
| First `/api/state` | INA219, once for the process (`static const`) | `App:4695` CONFIRMED |
| Media watcher start | the hat (`[cfexpress_hat]`) | `App:9310` CONFIRMED |
| Each eject | Core's embedded Python reinsert helper reads the whole file with `configparser` and catches only `OSError` | `App:3426-3495`, `parser.read` `:3477` CONFIRMED |
| Each use | IMU (each take, each `/api/state`), `[run_script]` (each press) | `R2 §1.3` |
| Process start | UI: `[display]`, `[ina219]`, `[imu]`, `[network]`. Network helper: `[network]`. Automounter (root): `[cfexpress_hat]`, `[storage]` | `R3 §1.2`; `UI:src/CfeAutomounter.cpp:786-802` CONFIRMED |

**Write paths today** (no shared lock, no version):

| Writer | How | Cite |
| --- | --- | --- |
| `POST /api/config` | whole text, `.bak`, `<file>.tmp`, rename, no fsync | `App:5463-5526`, `App:7321-7341` CONFIRMED |
| IMU commands | single key, `<file>.tmp` + rename. If the rename fails it **removes the real file** and renames again | `HW/Mpu6050RecordingSession.cpp:604-713`, `:700-705`; multi-key `:715-840` CONFIRMED |
| UI gyro page | single key, `QSaveFile` | `UI:src/GyroConfigBridge.cpp:1577` CONFIRMED (signature) |
| UI template writers | the whole template, only when `/home/pi/apertar-hardware.conf` is missing | `UI:src/DisplayConfigBridge.cpp:41-47`, call `:587`; `UI:src/Ina219Bridge.cpp:69`, `:497` CONFIRMED |

**Action path today.**

1. A driver thread sees a debounced press edge (`HW/GpioInput.cpp:690-710` CONFIRMED) and calls
   `handleHardwareInputAction` (`App:8808-8836` CONFIRMED). That takes `hardwareInputSequenceMutex_`, then loops over the
   mapping's actions (at most 6, `HW/ButtonActionList.hpp:14`). The loop skips `standby` for turns and stops once the camera
   is in standby.
2. `handleSingleHardwareInputAction` (`App:8838-9148` CONFIRMED) turns each action into socket commands. It goes through
   `dispatchHardwareInputCommand` (`App:8636-8644`), which calls `handleCommand`, which takes `commandMutex_`
   (`App:9483-9485` CONFIRMED).
3. Unknown actions end at `App:9147` (`Hardware input action ignored: unknown action`).

The alias lists live three times: `HW/GpioInput.cpp:108-202`, `HW/Pcf8574Input.cpp:140-242`, `HW/NeoRotary4Input.cpp:121-215`
(CONFIRMED: the sketch test compiles all three and finds them identical).

### 1.4 What Cinemate does (from R1, reopened where cited)

Cinemate edits one JSONC file (`settings.jsonc`, the git-tracked file). One row per control: a pin `<select>` that greys out
pins in use, then gesture lines (Press, Single, Double, Triple, Hold), each with a method dropdown grouped like the CLI, an
argument control from a spec, and a pencil for free text (`R1 §1.2-1.5`). Its save path:

1. Merge over the file on disk.
2. Fill defaults.
3. Keep 10 backups.
4. Rewrite comments surgically.
5. Atomic replace.
6. **Restart the whole app** (`R1 §1.13`).

The hardware page probes bus 1 only, with a seesaw register-read check (`R1 §1.9`). Advanced editing worth copying lives in the
recovery console: a raw textarea validated by the real loader, a backup, and confirm-or-revert for `config.txt` (`R1 §1.14`).
The quad rotary is hard-wired to bus 1 and `0x49` (`R1 §0`), so **the part Patrik's fix needs has nothing to port in
Cinemate**: bus, address and the "why is the bus missing" diagnosis are Apertar's to design.

---

## 2. The decision

### 2.1 Facts every design must respect

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | One file, about 15 readers in Core, the UI, the network helper and the root automounter, with about 10 hand-copied candidate lists | CONFIRMED `App:4293-4311`; `R3 §4.3` (10 places listed) |
| F2 | The **control** sections (`gpio_buttons`, `gpio_encoders`, `pcf8574`, `neorotary4`, `grove_analog`, `trigger_output`, `recording_indicator`, `run_script`) are read only by Core. The **shared** ones: `ina219` (Core + UI), `imu` and drivers (Core + UI), `cfexpress_hat` and `storage` (Core, Core's Python, automounter), `display` (UI), `network` (UI + helper) | CONFIRMED `R3 §1.2` table; spot-checked `UI:src/DisplayConfigBridge.cpp:584-592`, `UI:src/CfeAutomounter.cpp:100-146` |
| F3 | The UI writes a full template to `/home/pi/apertar-hardware.conf` when that path is missing. It ignores the env var and writes `[cfexpress_hat] bus=10` and `[neorotary4] enabled=false` | CONFIRMED `UI:src/DisplayConfigBridge.cpp:41-47`, `:131-135`, `:297-300` |
| F4 | A rename-based writer replaces a symlink with a regular file | PROBABLE (POSIX `rename`) |
| F5 | Read once: the drivers at Core start, INA219 `static const`, the hat at watcher start | CONFIRMED `App:7026-7043`, `:4695`, `:9310` |
| F6 | Every driver's `start()` is `stop()` + `loadConfig()` + a new thread; `stop()` joins the thread | CONFIRMED `HW/NeoRotary4Input.cpp:310-337`; others `R2 §5.2` |
| F7 | `handleCommand` holds `commandMutex_`. Driver callbacks reach `handleCommand`. So a reload run inside a command, or on a driver thread, can deadlock on `join()` | CONFIRMED lines `App:9485`, `:8636-8644`, `:8818-8819`; deadlock PROBABLE |
| F8 | No writer locks or checks a version. The IMU writer removes the live file on a failed rename. Two Core writers share `<file>.tmp` | CONFIRMED `App:5510`, `HW/Mpu6050RecordingSession.cpp:687`, `:700-705` |
| F9 | Readers disagree. Core's hat and INA219 readers do not strip a comment after an integer (`bus=1  # x` → default 10, `App:4580` CONFIRMED). Core's Python helper uses `configparser` and catches only `OSError` (`App:3477-3478` CONFIRMED): a duplicate key or section anywhere, a junk line, or a key above the first section stops it | CONFIRMED (code); Python behaviour PROBABLE (`configparser` defaults) |
| F10 | Three identical `normalizeSingleAction` copies. Unknown names pass through and are logged only at press | CONFIRMED (sketch test, 355 tokens); `App:9147` |
| F11 | Inputs know only "pressed": one press edge, up to 6 actions, `standby` skipped for turns | CONFIRMED `HW/GpioInput.cpp:690-710`, `HW/ButtonActionList.hpp:14`, `App:8832` |
| F12 | New gesture keys (`d10_hold`, `pin3_double`, `encoder2_hold`) are ignored by today's parsers. GPIO needs only digits after the prefix; PCF the same; NeoRotary's field is not matched | CONFIRMED `HW/GpioInput.cpp:209-236`, `HW/Pcf8574Input.cpp:108-138`, `HW/NeoRotary4Input.cpp:355-444` |
| F13 | Driver state is invisible: `enabled()`, `configPath()`, `lastError()` exist; `lastError` is cleared after a good open, so it is live status | CONFIRMED `HW/NeoRotary4Input.cpp:614-640`; unread `App:7026-7041` |
| F14 | Protocol: a flat map of scalar fields; a quoted string may hold `\n` (JSON escapes). `core.py` turns all-digit values into numbers | CONFIRMED `CP:66-118`, `:163-230`; `working/tools/core.py:8` |
| F15 | Request ≤ 1 MiB; file ≤ 256 KiB | CONFIRMED `src/web/WebServer.cpp:23`, `App:66` |
| F16 | The WebUI has no authentication. `[run_script]` paths run Bash as Core's user | CONFIRMED `R2 §4` (`WebServer.cpp:156-170`); `HW/HardwareScriptRunner.cpp:207-240` (`R2 §1.4`) |
| F17 | One instance of each driver; each `Config` holds one bus and address | CONFIRMED `App.hpp:121-128` |
| F18 | A seesaw is identified by a register read (HW ID `0x87`), not an ACK. `0x48` (TMP117) answers `0x12` | CONFIRMED `SRC §3.5`; `HW/NeoRotary4Input.cpp:494-514` |
| F19 | DPI overlays hold GPIO 0-27, including 2/3, whether or not a panel is attached; nothing in Apertar writes or reads the overlay lines | CONFIRMED `SRC §3.2`; `R3 §3.3` (grep) |
| F20 | Core already has the cooperative write primitives: `settingsFile::atomicWrite` (unique temp, keeps the mode, fsync, rename, dir fsync) and `QtIniLock` (QLockFile-compatible) | CONFIRMED `SF:36-58`, `:59-118` |
| F21 | Core already reads `/boot/firmware/config.txt` read-only (the fan block) | `R4 §2.2 D2` (`App:3104-3125`) |
| F22 | Every Core file this project touches syntax-checks on the host without libcamera | CONFIRMED (run here, 5 files, 0 errors) |
| F23 | An event published while a command is running goes only into that command's reply, unless `publishEvent` whitelists it; outside commands every event is broadcast | CONFIRMED `App:11289-11319` |

### 2.2 Options: where the system-controlled file lives

| | **A: keep `~/apertar-hardware.conf`, Core owns writes** | B: split: control sections to `~/.config/apertar-core/controls.conf`, shared ones stay | C: move all to `~/.config/apertar-core/hardware.conf` |
| --- | --- | --- | --- |
| Readers to change | 0 | 6 Core loaders + their candidate lists | about 15 in 2 repos, both Python copies, the root automounter (reinstall: Patrik) |
| Patrik's fix | one file, as it is | two files: the hat's bus in the old one, the NeoRotary's in the new one | moved. The old file must go, and then F3 writes it back with `bus=10` |
| The UI template (F3) | writes the old path only if missing; T43 removes it | writes control sections nobody reads into the old file | regenerates the old file, which shadows the new one for readers that were not changed |
| Hand editing | the file he knows | two files | a new file |
| Advanced view | one text | two tabs | one text |
| "System-controlled" | Core is the only program writing control sections (the UI still writes `[imu]` until T43) | full for `controls.conf` | full |
| Migration | none: adopted in place | 8 sections moved, both readable during the change | everything |
| Risk | low | medium | high |

Also checked and rejected: a symlink from the old path to a new file. Core's two writers and `QSaveFile` rename over the path, so
the symlink would become a regular file and the copies would fork without notice (F4; `R3 §4.3` point 3).

### 2.3 Options: applying a change, and the action vocabulary

| Applying | Today: restart Core (Patrik) | **Reload in Core** | Cinemate: restart everything |
| --- | --- | --- | --- |
| What runs it | `sudo systemctl restart apertar-core` | a Core worker thread: stop all six drivers, start them in boot order | `systemd-run … restart` |
| Camera interrupted | yes (session restart) | no | yes |
| House rule | Patrik | Core, no sudo | sudo |
| Risk | none new | deadlock if done inside a command (F7); avoided by the worker | n/a |

| Vocabulary | Keep three copies + a fourth in JS | **One header used by drivers, App, validator and `list_actions`** | Generate from a data file at build time |
| --- | --- | --- | --- |
| Copies | 4 (plus template comments) | 1 | 1, plus a generator to maintain |
| Host-testable | no | yes (done: 355 tokens identical) | yes |
| Fits Apertar | no (M5 "copies", `R4 R7`) | yes: `ButtonActionList.hpp`, `PowerButtonGesture.hpp`, `FramePhaseLock.hpp` are the pattern | no build-time codegen in Core today |

### 2.4 Recommendation

Build **A + reload + catalog**, as T36-T43.

| Patrik's request | This design |
| --- | --- |
| "port the gpio dropdown (and method assigning) from Cinemate" | Easy mode (T40): a row per control, a dropdown per gesture, argument controls from a spec, a pencil field, pins in use greyed out. Hold and double press come in T42 |
| "in the most Apertar like style" | Pure logic in headers with host tests; flat socket commands; settings cards, pills and selects in the WebUI; `atomicWrite` + `QtIniLock` |
| "with the functionality of Apertar api" | Every editor action is a socket command (`get_controls`, `set_controls`, …); every action a button runs is the same `handleCommand` the WebUI uses (M1 "one front door", `R4 R8`) |
| "a system controlled config file" | `~/apertar-hardware.conf`, written only through Core's store, validated, versioned, with history (§3.4) |
| "the hardware (i2c expanders etc) Apertar is currently using" | The catalog of §5: PCF8574, NeoRotary 4, Grove ADC, INA219, IMU, CFE hat, GPIO buttons and encoders, tally, trigger, power button |
| "the setting of i2c channels … to make my fix … work" | The I2C devices card (T39): bus from the buses that exist, address, probe with ID check, why a bus is missing, guided `config.txt` text (§4.4) |
| "easy dropdown/drag and drop … and the manual editing for advanced users" | Two panels, one file, one revision, merge rules (§4.3) |

### 2.5 What each measurement would change (details in §8)

| Result | Then |
| --- | --- |
| M1: the live file has aliases, inline comments or duplicates | expected; T37's validator lists them and nothing is rewritten. If it has a duplicate or junk line, Core's Python reinsert helper already dies at each eject today: fix it by hand first |
| M1: a `/boot/firmware/apertar-hardware.conf` exists | `get_controls` reports which sections come from it (§3.4); tell Patrik before T37 |
| M2: a unit sets `APERTAR_HARDWARE_CONFIG` | the store writes that path (it uses `editableHardwareConfigPath()`, `App:4313-4318`); the readers without the variable keep reading `/home/pi` → document it in T37 |
| M4: the seesaw ID read while Core polls is wrong in some tries | `probe_device` never probes a chip Core's driver holds; it reports the driver's state (`source: driver`) |
| M5: `gpioinfo` marks GPIO 2/3 used with I2C1 on | the pin reservations come from the kernel; otherwise from `/dev/i2c-1` existing plus `config.txt` |
| M6: `pi` cannot read the journal | the WebUI status (T38) is the only witness; the tutorials' journal checks need `sudo` (Patrik) |
| M8 (after T38): a reload takes longer than 2 s | expected only when a driver sits in its 1 s retry sleep; the WebUI waits for `controls_applied_revision` instead of a timer |

---

## 3. Data model, file, commands, state

### 3.1 The file

- **Name and place:** `~/apertar-hardware.conf` = `editableHardwareConfigPath()` (env var, else `/home/pi/…`,
  `App:4313-4318` CONFIRMED). Core never writes `/boot` copies; it reports them.
- **Core's notes about it:** `~/.config/apertar-core/` (same XDG rule as `camera_settings.conf`, `src/camera/CameraController.cpp:355-366` CONFIRMED):
  - `hardware-history/<YYYYmmdd-HHMMSS>-<revision>.conf`: the last 20 versions Core wrote, plus the version Core first saw;
  - `hardware-state.conf`: `written_revision=`, `written_at=`, `written_by=` (webui-easy, webui-text, imu, core.py).

  `~/apertar-hardware.conf.bak` is still written (the version before the last save): the WebUI toast and the KB's image notes
  name it (`R3 §3.1`).
- **Format (what Core writes; it reads everything it reads today):**
  - Sections `[name]` in lower case, canonical spelling (table §3.2). A new section goes at its place in the canonical order:
    `[pcf8574]` before `[trigger_output]` and `[recording_indicator]`, which inherit its bus.
  - One `key=value` per line, no spaces around `=`, no quotes, canonical key names, booleans `true`/`false`, addresses
    `0x49`, action groups `iso200,fps24` without spaces.
  - **Never a comment after a value.** When Core edits a line that has one, the comment moves to its own line above (sketch
    check 6). Never a key above the first section. Never two copies of a key or a section.
  - Comments, blank lines, unknown keys and unknown sections are kept byte for byte. Only edited lines change (sketch check
    3: byte-identical round trip, CRLF and a missing final newline included).
  - On the first save Core adds two comment lines at the top, if absent:
    ```ini
    # Apertar hardware configuration. ApertarCore validates and writes this file: WebUI Settings > Controls,
    # or Settings > Config for the text. Hand edits are kept; put comments on their own lines.
    ```
- **Revision:** `h` + 16 hex digits of FNV-1a 64 of the bytes. The `h` stops `core.py` turning it into a number (F14).
  Sketch check 3.

### 3.2 The schema (one table in `HardwareConfigText.hpp`: canonical names, aliases read, who reads, how it applies)

| Section (aliases read) | Keys Core writes | Readers | After a save |
| --- | --- | --- | --- |
| `[gpio_buttons]` (`gpio`, `grove_digital`, `grove_buttons`) | `enabled`, `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms`, `dN` (BCM 0-63); T42: `dN_hold`, `dN_double`, `hold_ms`, `double_ms`. Aliases read: `gpioN`, `pinN`, `bcmN`, `grove_dN`, `d_N`, `…_action`, `gpiochip`, `bias`, `poll_interval_ms` | Core `GpioInput` | reload |
| `[gpio_encoders]` (`grove_encoders`) | `enabled`, `encoderK_a`, `_b`, `_press_gpio`, `_cw`, `_ccw`, `_press`, `_invert`, `_steps_per_event` (K 0-7); T42: `encoderK_hold`, `_double`. The shared timing keys are written only in `[gpio_buttons]` (the later section wins for both, `R2 §1.4`) | Core `GpioInput` | reload |
| `[pcf8574]` (`pcf8574_buttons`) | `enabled`, `bus`, `address`, `poll_ms`, `debounce_ms`, `active_low`, `pinN` (0-7); T42: `pinN_hold`, `_double` | Core; bus and address inherited by trigger and tally | reload |
| `[neorotary4]` (`neo_rotary4`, `neo_rotary_4`) | `enabled`, `bus`, `address`, `poll_ms`, `debounce_ms`, `invert_direction`, `reset_on_start`, `max_events_per_poll`, `encoderK_cw`, `_ccw`, `_press` (K 0-3); T42: `encoderK_hold`, `_double` | Core | reload |
| `[grove_analog]` (`grove_adc`, `analog_controls`) | `enabled`, `bus`, `address`, `poll_ms`, `deadband`, `emit_on_start`, `aN`, `aN_min`, `_max`, `_step`, `_deadband`, `_invert`, `_mode`, `_presets`. Here `channel=` is the **bus** and `channelN=` an input (sketch check 3) | Core | reload |
| `[recording_indicator]` (`rec_indicator`, `record_led`, `recording_led`, `tally_led`) | `enabled`, `target`, `chip`, `line`, `pcf_pin`, `bus`, `address`, `active_high`, `open_drain` | Core | reload + LED re-sync |
| `[trigger_output]` (`trigger`, `capture_trigger`, `hotshoe`) | the same + `pulse_ms`, `events` | Core | reload |
| `[cfexpress_hat]` | `enabled`, `bus`, `address` | Core watcher, Core's Python helper (each eject), automounter (root) | Core: reload; automounter: **restart (Patrik)** |
| `[storage]` | `mount_path`, `pcie_controller` | Core's Python helper, automounter | automounter restart |
| `[ina219]` | `enabled`, `bus`, `address` | Core, touch UI | Core: reload; UI: restart |
| `[imu]` + `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`, `[gyro]` | as today. `bus`, `address`, `enabled` and `driver` from the I2C card; calibration keys from the Gyro page and commands | Core (each use), touch UI | Core: next use; UI: restart |
| `[display]`, `[network]` | as today (text mode only) | touch UI; network helper | UI / helper restart |
| `[run_script]` | `path`, `path2`…`path5` | Core (each press) | next press; **not writable from the browser** (Q2) |
| `[camera]` (T33, not on the tip) | `max_fps` | Core | T33's save hook, moved into the store (§6, risk R10) |

**The controls model** (built by Core in `ControlsModel.hpp`, T39-T40, from the parsed text; the WebUI never parses INI):

| Thing | Kinds | Gestures | Resource it claims |
| --- | --- | --- | --- |
| Input | GPIO button; GPIO quadrature encoder; PCF8574 pin; NeoRotary 4 knob (0-3); Grove analog channel (0-7) | button and pin: `press` (+ `hold`, `double` in T42); encoder and knob: `cw`, `ccw`, `press` (+ `hold`, `double`); analog: a target and its range | `gpio:N`; `pcf:<bus>:<addr>:<pin>`; `neo:<bus>:<addr>:<k>`; `grove:<bus>:<addr>:<n>` |
| Output | Tally (`recording_indicator`), Trigger (`trigger_output`), on GPIO or a PCF8574 pin | — | `gpio:N` or `pcf:…` |
| Device | the I2C devices of §5 | — | `i2c:<bus>:<addr>` |
| Fixed | Pi 5 power button: press = shutdown card, double = standby, any press in standby = wake | — | read-only row (`HW/PowerButtonGesture.hpp:6-39`) |
| Reserved | GPIO 2/3 while `/dev/i2c-1` exists; GPIO 0-27 under an active DPI overlay; GPIO 0/1 (HAT ID EEPROM, advisory); lines another consumer holds (`gpioinfo`, M5) | — | greyed in every picker with the reason |

**An action value** is what the file holds today: a comma list of up to 6 tokens, each a catalog name (`iso_up`) or a
parameterised token (`iso800`, `fps24`, `wb5600`, `shutter180`, `shutter1/48`, `shutter2s`, `ev-1`, `resolution3840x2160`,
`run_script2`). No new grammar.

### 3.3 The action vocabulary (`src/hardware/ActionCatalog.hpp`, T36)

One table, `kSpecs[]`, with 52 entries in the sketch. Each entry has: id, group, label, every alias the old normalizers
accept, the sources it is valid for (`standby` is button-only), a `ui` flag (handled by the touch UI through a
`hardware_action` event), and for parameterised families the argument type and the file form (`iso{}`). Functions:

| Function | Replaces | Sketch check |
| --- | --- | --- |
| `canonicalAction(token)` | the three `normalizeSingleAction` copies | 1: identical to all three on 355 tokens (every alias, upper case, padded, `none`, LED tokens, unknown names, scripts) |
| `classify(token)` → `{known, id, value, note}` | nothing today: unknown names are found only at press | 2: `iso200`, `fps23.976`, `ev-1`, `wb5k` ("Core clamps 5 K to 2500 K"), `shutter1/48`, `shutter180` ("an angle in video; 1/x s in photo mode or timelapse"), `shutter2s`, `resolution4056x2280`; `isoo_up` unknown, suggestion `iso_up` |
| `suffixAfter`, `numberAfter` | `App:1374-1402` (`hardwareActionSuffix`, `parseHardwareActionNumber`): App calls the header, so the validator and the dispatcher share one parser | 2 |
| `catalogJson()` | — | 2 |

`list_actions` reply (Core adds the value lists from the functions the cycles already use, `App:1174-1353`, so T35's value
lists flow through):

```json
{"ok":true,"actions":[{"id":"capture","group":"Record","label":"Record or photo (main button)","button":true,"rotation":true,"ui":false},
  {"id":"iso_value","group":"ISO","label":"Set ISO","button":true,"rotation":true,"ui":false,"token":"iso{}","arg":"iso"}, …],
 "values":{"iso":[100,200,400,800,1600,3200,6400,12800,25600,51200],"shutter_angle":[11.25,…,360],"shutter_speed":[24,…,1000],
           "wb":[2500,…,8000],"fps":[25,33,50],"resolution":["3840x2160","1920x1080"]},
 "gestures":{"button":["press"],"encoder":["cw","ccw","press"],"analog":["target"]},
 "analog_targets":["iso","fps","resolution","wb","shutter","focus_peaking_threshold","zebra_threshold","input_volume",
                   "headphone_volume","camera_controls_opacity"],
 "max_per_mapping":6}
```

T42 adds `"hold","double"` to `gestures`. A WebUI that loaded the catalog shows exactly what Core supports, no more.

### 3.4 Who writes, how, and what happens to hand edits

**One writer: `HardwareConfigStore` (`src/hardware/HardwareConfigStore.hpp/.cpp`, T37).**

| Step | What | Why |
| --- | --- | --- |
| 1 | `std::mutex` in the store, then `settingsFile::QtIniLock(path)` (`~/apertar-hardware.conf.lock`, QLockFile-compatible) | in-process writers serialise; the touch UI can join later with `QLockFile` (T43) |
| 2 | read the current text; compute its revision | the base for every check |
| 3 | text mode: `base == current` or refuse. Key edits: `conflicts(baseText, current, edits)` must be empty (base text from a cache of the revisions Core served or wrote, then from the history directory) | §4.3 |
| 4 | new text = `applyEdits(current, edits)` (or the sent text) | line-preserving |
| 5 | `validate(new, facts)`; refuse if `newErrors(validate(current), validate(new))` is not empty | a hand-edited file with old errors does not lock the editor out (sketch check 8) |
| 6 | `[run_script]` paths unchanged, or refuse (Q2) | F16 |
| 7 | copy current to `.bak` and to `hardware-history/`, prune to 20 | undo |
| 8 | `settingsFile::atomicWrite(path, new)`: unique temp, keeps the mode, fsync, rename, dir fsync | readers never see half a file; the path never goes missing, so F3 never fires |
| 9 | write `hardware-state.conf`; release the lock; return the revision, the diff, the issues | — |

The IMU commands (`writeHardwareConfigValue`, `updateImuBiasConfig`) become one-line calls into the store's key-edit path.
That removes the shared `.tmp` name and the remove-then-rename (F8). `POST /api/config` goes through the store too: it is
validated and locked, with the base taken from an `X-Apertar-Revision` header (the page sends it from T37). Without the header
it is last-writer-wins, as today, for old scripts.

**Hand edits over ssh: what happens.**

1. Nothing applies by itself. This is today's "read once" behaviour, and it means a half-saved `nano` buffer is never applied.
2. The controls worker (§3.6) stats the file every 2 s. On a new revision that Core did not write:
   - the journal gets `ApertarCore controls: ~/apertar-hardware.conf changed outside Apertar (h…): N errors, M warnings; not
     applied`, plus one line per issue with its line number;
   - Core publishes `controls` with `by:"outside"`;
   - `/api/state` shows `controls_outside:true`.
3. The WebUI shows the banner of §1.2 C, with the issues at their line numbers.
4. **Apply** (`apply_controls base=<rev>`) reloads. With errors present, Apply needs `force=true` and says which lines Core
   will skip. Core's next start applies it, as today.

**Migration: adoption in place.** No move, no rewrite on upgrade.

- T37's first `get_controls` validates the live file. The journal and the WebUI list what they find; nothing changes until a
  save.
- The first save writes the changed keys plus the 2-line header.
- Alias spellings stay until that key is edited; then that line is written canonical (sketch check 4: `gpio10=capture` in
  `[gpio]` becomes `d10=record_toggle` in place, with no second `[gpio_buttons]`).
- A `/boot` copy is reported and never written. If a section is missing in `~/…` and present in `/boot/…`, the four
  section-scanning readers take it from `/boot` (`R3 §3.4`), and the model says so: "Core reads `[neorotary4]` from
  /boot/firmware/apertar-hardware.conf".

**How the other processes keep working.** Same path, same syntax. Core's writer obeys every rule the strictest reader needs
(§3.1; `R3 §4.4`). The rename is atomic and the file is never absent. The owner stays `pi` (Core runs as `pi`) and the mode is
kept (`SF:44-46`). Patrik's `[cfexpress_hat] bus=1` and `[neorotary4] enabled=true bus=1 address=0x49` are never touched unless
he edits them.

### 3.5 Commands

| Command | Fields | OK reply | Refused |
| --- | --- | --- | --- |
| `get_controls` | `base` (optional: also return the diff `base → current`) | `"controls":{revision, path, display_path, exists, modified_text, written_by, outside, text, issues[], model{…}, system{…}, status[], applied_revision, pending[]}` | never |
| `set_controls` | `base` (required) and either `text` or any number of `set.<section>.<key>=<value>` / `unset.<section>.<key>=true` / `unset.<section>=true`; `dry_run=true`; `apply=false` | `revision`, `diff`, `issues[]`, `apply:{core:"reloading"\|"none", restart:[{who, why, command}]}`. With `dry_run`: `text`, `diff`, `issues`, `conflicts`, nothing written | §3.7: no base; changed (text); conflict (keys); new errors; in a take; `[run_script]` paths (Q2); value holding `#`, `;` or a newline; unknown section; > 256 KiB, NUL, empty |
| `apply_controls` | `base` (the revision you saw), `force=true` | `apply:{…}`. With nothing new it answers `Nothing to apply: Core already runs h….`; `force=true` reloads anyway | in a take; `base` ≠ current ("Reload first"); errors without `force` |
| `list_actions` | none | §3.3 | never |
| `scan_i2c` | `bus`; `all=true` sweeps 0x08-0x77 | `"scan":{bus, exists, label, found:[{address, device, name, id, answer, source}], busy:[{address, reason}], hint}` | in a take; `all` on a camera bus; bus missing → ok with `exists:false` and the reason (§4.4) |
| `probe_device` | `type`, `bus`, `address` | `"probe":{found, id, name, detail, source:"driver"\|"bus"}` | in a take; unknown type |
| `controls_history` (T41) | none | `[{revision, at, by}]` | never |
| `help` | | lists the new names (`App:9633`) | |

Example (T38), from the shell:

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_controls base=h3f0c2a91d4e75b18 set.neorotary4.encoder3_press=zebra dry_run=true
```

`set.*` field names travel as JSON keys and the protocol keeps any key (`CP:181-204` CONFIRMED). The edits are a map, so they
are order-free; Core sorts them by section order and puts `enabled`, `target`, `bus`, `address` first in a new section (sketch
check 5).

**State fields** (all three JSON writers that carry state: `buildWebStateJson` `App:7857`, `get_state` `App:9636`, and the
touch UI's poll):

| Field | Meaning |
| --- | --- |
| `controls_revision` | the file's revision now (stat-cached; rehashed only when mtime or size changes) |
| `controls_applied_revision` | the revision the drivers last loaded |
| `controls_outside` | the file changed and Core did not write it |
| `hardware_status` | `[{module:"neorotary4", state:"connected"\|"error"\|"off"\|"idle"\|"absent", detail:"/dev/i2c-1: No such file or directory", bus:1, address:"0x49"}, …]` from `enabled()`, `lastError()` and a new `running()` per driver |

**Event:** `{"event":"controls","revision":"h…","by":"core"\|"outside","applied":true\|false,"status":[…],"pending":[…]}`, after
a save, after a reload and on an outside change. T38 adds it to `publishEvent`'s whitelist, so the one published inside
`set_controls` also reaches the touch UI (F23).

### 3.6 Live apply vs restart

The **controls worker** (`ApertarCoreApp::runControlsWorker`, T38) is one thread started with Core. It waits on a condition
variable with a 2 s timeout. On a wake it reloads; on a timeout it stats the file. It holds no App mutex while it works (F7).

```cpp
// T38: restart the hardware drivers here, never inside handleCommand (commandMutex_) and never on a driver
// thread (stop() joins it). A button action in flight finishes first; nothing here waits for a lock.
void ApertarCoreApp::reloadHardwareDrivers()
{
    const auto started = std::chrono::steady_clock::now();
    const std::string revision = hardwareConfig_.currentRevision();
    recordingIndicatorOutput_.stop();   // free every line first, so a swap (tally 21 <-> button 20) works
    groveAnalogInput_.stop();
    gpioInput_.stop();
    neoRotary4Input_.stop();
    pcf8574Input_.stop();
    triggerOutput_.stop();
    if (!triggerOutput_.start() && !triggerOutput_.lastError().empty())        // boot order, App:7026-7043
        std::cerr << "ApertarCore trigger output disabled: " << triggerOutput_.lastError() << "\n";
    pcf8574Input_.start();
    neoRotary4Input_.start();
    gpioInput_.start();
    groveAnalogInput_.start();
    if (!recordingIndicatorOutput_.start() && !recordingIndicatorOutput_.lastError().empty())
        std::cerr << "ApertarCore recording indicator LED disabled: " << recordingIndicatorOutput_.lastError() << "\n";
    recordingIndicatorOutput_.setRecordingActive(camera_.isRecording() || soundRecordingActive());
    recordingIndicatorOutput_.setStillExposureActive(camera_.stillExposureStatus().active);
    hardwareConfigGeneration_.fetch_add(1);   // INA219 and the hat watcher reload on their next use
    appliedRevision_ = revision;
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count();
    std::cerr << "ApertarCore controls: applied " << revision << " in " << ms << " ms: " << hardwareStatusLine() << "\n";
    publishEvent(controlsEventJson("core", true));
}
```

| Section changed | Core | Others (the reply's `restart` list, for Patrik) |
| --- | --- | --- |
| `gpio_*`, `pcf8574`, `neorotary4`, `grove_analog`, `trigger_output`, `recording_indicator` | reload (above) | — |
| `ina219` | `readIna219Snapshot` reloads when the generation changes (the `static const` at `App:4695` becomes a mutex-guarded cache) | touch UI: `sudo systemctl restart apertar-ui-direct` |
| `cfexpress_hat`, `storage` | the media watcher rebuilds its `CfeHatReader` when the generation changes (`App:9310`); the Python helper reads at each eject | automounter: `sudo systemctl restart apertar-cfe-automounter` |
| `imu` + drivers | next use (as today) | touch UI restart |
| `display` | — | touch UI restart |
| `network` | — | `sudo systemctl restart apertar-network`, and the touch UI |
| `run_script` | next press | — |
| `config.txt` (never written) | — | reboot, after Patrik's edit |

Recording gate: `set_controls` (not `dry_run`), `apply_controls`, `scan_i2c` and `probe_device` are refused while a take, a
sound recording, a timelapse or a still exposure runs. A take started during a reload is fine: the LED is re-synced at the
end, and a button pressed in that window is lost (up to about 1 s, M8).

### 3.7 Refusals, errors, warnings, messages

**Validator rules** (`validate()`; the reader each rule protects is named in the message). "Sketch" = implemented and checked
here.

| Rule | Kind | Example message | Sketch |
| --- | --- | --- | --- |
| Comment after a value in `[ina219]`, `[cfexpress_hat]`, `[storage]` | error | `Comment after the value on line 3: Core's cfexpress_hat reader then ignores bus=1 and keeps its default. Put the comment on its own line.` | yes |
| Comment after a value elsewhere | warning | `Comment after the value on line 12: Apertar's readers handle this differently. Put the comment on its own line.` In `[trigger_output]`/`[recording_indicator]` a `;` with no space before it is a list separator (`HW/TriggerOutput.cpp:56-66`), not a comment; Core writes `,` | yes (the separator case: spec) |
| Text after `]` on a header | error | `Text after ']' on line 9: Core's hat and INA219 readers do not see this header.` | yes |
| Junk line; a key above the first section | error | `Line 4 is not a section, a key=value or a comment: the C++ readers skip it, but Core's NVMe reinsert helper (Python) stops on it.` | yes |
| Indented key | warning | `Line 5 is indented: Python's configparser reads it as part of the line above.` | yes |
| Duplicate section, duplicate key | error | `[neorotary4] appears twice (lines 14 and 16): the readers disagree on which one counts. Merge them.` | yes |
| `bus` not 0-255, `address` not 0x03-0x77 | error | `address=0x80 on line 30 is not a 7-bit I2C address (0x03-0x77).` | yes |
| Unknown section | warning | `Unknown section [neorotory4] on line 21: no reader uses it. Did you mean [neorotary4]?` | yes |
| Enabled device on a bus that does not exist | warning | `[ina219] bus 4 does not exist on this Pi (buses: 1, 10, 13, 14). The device stays silent until the bus exists or you pick another one.` (+ the DPI line when the bus is 1) | yes |
| One GPIO line, two owners (buttons, encoder pins, tally, trigger) | error | `GPIO 21 is used by Trigger output (line 7) and Tally (line 20).` (trigger starts first and gets it, `App:7026`) | yes |
| GPIO 2/3 while bus 1 exists; GPIO 0-27 under an active DPI overlay | error | `GPIO 2 is the SDA line of I2C bus 1; button d2 cannot use it while the bus exists.` | yes |
| Unknown action | error | `Unknown action 'isoo_up' on line 11: Core logs it and does nothing. Did you mean iso_up?` | yes |
| 7+ actions; an empty item; a tally token in a group | error | `Line 12: at most six actions are allowed per mapping; Core drops the whole mapping.` | yes |
| `standby` on a turn | warning | `standby on a turn (line 15) never fires: Core skips it for rotations.` | yes |
| `standby` not last in a group | warning | `Actions after standby on line 18 never run (App:8834).` | spec |
| Tally shorthand `dN=recindicatorled` | warning | `The tally shorthand on line 13 loses to an enabled [recording_indicator] section and has no polarity key (T17). Use the section.` | yes |
| Trigger or tally targets the PCF8574 but sits above `[pcf8574]` | warning | `[trigger_output] targets the PCF8574 but comes before [pcf8574] (line 30), so it does not inherit its bus and address.` | yes |
| `wb` value outside 2500-8000 | warning | `'wb5k' on line 22: Core clamps 5 K to 2500 K.` | yes |
| Two devices on one bus and address; a configured address that a known device holds | error / warning | `[neorotary4] address 0x48 on bus 10 is the StarlightEye's TMP117 (it answers 0x12, not 0x87).` | spec |
| GPIO timing keys in `[gpio_encoders]` | warning | `poll_ms in [gpio_encoders] also sets the buttons' poll (the later section wins). Set it in [gpio_buttons].` | spec |
| `[imu] bus=` / `address=` | warning | `[imu] bus is ignored: the IMU reads bus and address from [mpu6050].` | spec |
| No `[cfexpress_hat]` section | warning | `No [cfexpress_hat]: the automounter polls bus 10 while Core's media watcher is off. Add the section.` | spec |
| A section only in a `/boot` copy | warning | `Core reads [neorotary4] from /boot/firmware/apertar-hardware.conf: this file has none.` | spec |
| An alias spelling | none (kept); rewritten canonical only when that key is edited | — | yes (check 4) |

**Command refusals and replies.**

| When | Kind | Message |
| --- | --- | --- |
| `set_controls` without `base` | refusal | `set_controls needs base: the revision you loaded with get_controls.` |
| text mode, file changed | refusal | `The file changed since you opened it (outside Apertar, 21:14). Your text is kept. Show changes, or load the new file and redo your edit.` |
| key edit, same key changed | refusal | `cfexpress_hat.bus changed since you loaded it: you saw 1, the file now says 10 (outside Apertar, 21:14). Reload to see it.` |
| base unknown and the file changed (Core restarted) | refusal | `The file changed since you loaded it and Apertar no longer has that version. Reload.` |
| new errors | refusal | `Not saved: 1 new error. Line 41: GPIO 3 is the SCL line of I2C bus 1; button d3 cannot use it while the bus exists.` |
| in a take | refusal | `Stop recording before saving controls.` / `Stop the timelapse before saving controls.` |
| `[run_script]` paths | refusal | `Script paths run as pi: change [run_script] over ssh, not from the browser.` |
| edit value with `#`, `;` or a newline | refusal | `'set.neorotary4.bus': a value cannot hold # ; or a line break.` |
| unknown section in an edit | refusal | `Unknown section in 'set.neorotory4.bus'.` |
| apply with errors | refusal | `The file has 2 errors (lines 12, 40). Core skips those lines; apply anyway with force=true.` |
| saved, others need a restart | reply | `Saved; Core applied it. Still to do (you): sudo systemctl restart apertar-cfe-automounter. The automounter reads [cfexpress_hat] only at start.` |
| reload done | journal + event | `ApertarCore controls: applied h3f0c… in 412 ms: neorotary4 connected (bus 1 0x49), gpio connected (6, 10), pcf8574 off, tally gpio 21, trigger off` |
| scan in a take | refusal | `Stop recording before scanning I2C: a scan adds traffic to the bus.` |
| full scan of a camera bus | refusal | `Bus 10 is the camera's control bus: Apertar checks only known addresses there.` |
| an address a kernel driver holds | scan entry | `0x1a: in use by a kernel driver (the camera sensor); not probed.` (`I2C_SLAVE` returns EBUSY; Core never uses `I2C_SLAVE_FORCE`) |
| probe of a chip Core's driver runs | probe | `NeoRotary 4 at 0x49 on bus 1: connected (Core's driver; not probed again).` |
| wrong seesaw ID | probe | `0x48 on bus 10 answered 0x12, not 0x87: not a NeoRotary 4. 0x48 is the StarlightEye's TMP117.` |

### 3.8 Ways a change could be lost, and why it cannot

| Case | Why it cannot happen |
| --- | --- |
| Easy save overwrites a hand edit to another key | key edits are applied to the **current** file (sketch check 7) |
| Easy save overwrites a hand edit to the same key | per-key conflict check against the loaded revision |
| Text save overwrites anything | refused unless `base == current` |
| A WebUI save and an IMU calibration at the same moment | both go through the store's mutex and lock; no shared `.tmp` |
| The file is briefly missing and the UI writes its template | `atomicWrite` renames over the path; the IMU remove-then-rename is gone |
| An unknown key, comment or section is dropped | only edited lines change (round trip byte-identical) |
| A pin outside the picker's list vanishes (Cinemate D3) | the page sends only keys it changed; a pin it cannot show is shown as "GPIO 1 (HAT EEPROM)", not dropped |
| The touch UI's gyro page and a Core write race (QSaveFile, no lock) | a window of milliseconds remains until T43; risk R2 |

---

## 4. The WebUI and the touch UI

### 4.1 Controls panel (easy mode, T39-T40)

A new nav item **Controls** before **Config** (`Web:2773`), panel meta "Buttons, knobs, I2C devices and outputs", icon
`levels.png` or `config.png` (both exist in `src/web/icons/`). Built only from Core's `get_controls` and `list_actions`. Four
cards, in the classes the page already has: `.settings-card`, `.settings-card-head`, `.online-pill` (`Web:831`),
`.pill-grid` (`Web:749`), `.settings-select` (`Web:1532`), `.settings-field-grid` (`Web:1494`), `.settings-action-row`,
`.subtle-note`, a `.preset-row`-like row (`Web:1887`).

**Card 1: Controls file** (head pill: `Saved h3f0c` / `Unsaved: 3 changes` / `Changed outside` / `Not applied`)

- Path, modified time, written by. Banner for an outside change: **Apply**, **Show changes**.
- Buttons: **Review** (a `dry_run`: diff and issues in a sheet), **Save**, **Revert**, and the link **Edit as text** to the
  Config panel.
- Pending restarts, each with the command to copy.

**Card 2: I2C devices** (§4.4)

**Card 3: Inputs**, one block per source (head: the source, its bus and address, the driver's state pill):

```
NeoRotary 4 · bus 1 · 0x49                                            [Connected]
  Knob 1   Turn right  [ISO up ×]                               [+ action ▾] [✎]
           Turn left   [ISO down ×]                             [+ action ▾] [✎]
           Press       —                                        [+ action ▾] [✎]
  Knob 2 …
Pi GPIO buttons · chip auto · pull up · active low                    [Connected]
  [GPIO 10 ▾]  Press  [Record or photo ×]                       [+ action ▾] [✎] [Remove]
  [GPIO 6 ▾]   Press  [Eject media ×]                           [+ action ▾] [✎] [Remove]
  [+ Add button]   [+ Add encoder]
PCF8574 · bus 10 · 0x20                                                     [Off]
Grove analog · not in this file                                       [+ Add Grove ADC]
Pi 5 power button: press = shutdown card · double press = standby · in standby any press wakes (not configurable)
```

- **Pin picker** (`.settings-select`): GPIO 0-27, each `GPIO n`. A pin another row, an output or the system holds is
  `disabled` and labelled `GPIO 21 · Tally` or `GPIO 2 · I2C bus 1 (SDA)`. The row's own pin stays selectable. A pin in the
  file but not in the list is shown, not dropped. PCF rows show pins 0-7; NeoRotary rows knobs 1-4 (index 0-3 in the file).
- **Gesture lines:** Press (buttons, pins); Turn right, Turn left, Press (knobs, encoders). T42 adds **Hold** and **Double
  press**, but only when `list_actions.gestures` lists them.
- **Action chips:** one chip per action, in the order they run (the order matters: `standby` ends a group, `App:8834`). `×`
  removes. **Drag** a chip to reorder it in its line, or onto another line to move it. Pointer events with
  `setPointerCapture` and `pointercancel`, a 44 px handle, `touch-action: none` (T34 B6 pattern). Keyboard: a focused chip
  moves with ←/→.
- **+ action** (`.settings-select` styled as a button): `<optgroup>` per catalog group, labels from the catalog. A
  parameterised family ("Set ISO") opens a value select fed by `list_actions.values`, with a custom number field for WB and
  FPS. The chip then reads `ISO 800` and the file gets `iso800`. A UI action (`zoom_toggle`, `settings`, …) has the note
  "needs the touch UI running". A seventh action is not offered ("at most 6").
- **✎ (pencil):** the line's raw value (`iso800,fps24`) as text. On blur a `dry_run` runs, and the line's issues show under
  it. Empty means unset; it never defaults to anything (Cinemate D7).
- **Add / Remove:** a new GPIO button takes no pin until one is picked. Remove asks once ("Remove the button on GPIO 6? It
  stops working when you save."). Cinemate D2 cannot happen: any change marks the draft dirty.
- **Encoders:** A, B and Press pins (three pickers in the same registry), Invert (pills), Steps per event (select 1-8).
- **Analog channel:** target select (`analog_targets`), Min/Max/Step for the targets that use them, Invert pills, Preset/Linear
  for WB.

**Card 4: Outputs.** Tally and Trigger, each with: Off/On pills; Target pills (GPIO / PCF8574); a line picker (same registry)
or a PCF pin select; Active high pills; Open drain pills. The Trigger adds Pulse (select: 20, 40, 80, 160, 320 ms) and Events
pills (Record start, Photo, Timelapse start, Timelapse frame). A `recindicatorled` shorthand in the file shows as a Tally row
with "From the d21 shorthand: [Convert to a Tally output]".

**Redraw rule** (T34 lesson): rows are rebuilt only after `get_controls` returns, after Save or Revert, and after a local edit.
The 1 s `/api/state` poll updates only the state pills, the outside-change banner and the applied revision, so typing never
loses focus.

### 4.2 Config panel (advanced mode, T41)

The existing panel (`Web:3840-3872`) keeps its place and textarea, and gains:

- A **line-number gutter** (a side column scrolled with the textarea).
- **Check:** a `dry_run` that lists the issues with their line numbers. Clicking one selects that line.
- **Save** opens a diff sheet from the `dry_run` reply (Core's diff; red/green lines), then **Save** confirms.
- **Conflicts:** "The file changed since you opened it … [Show changes] [Load the new file]". *Show changes* asks
  `get_controls base=<rev>` for the diff from your base to the current file. Your text stays in the box.
- **History:** a select of the last 20 versions ("21:14 · by WebUI easy · h3f0c"). **Load** puts that text in the box as a
  draft; Save as usual.
- The state pill and the outside-change banner are shared with Controls.

### 4.3 Two modes, one file

| Rule | Why |
| --- | --- |
| Both panels send `base`, the revision they loaded | Core can tell what changed under them |
| Easy mode sends key edits; Core merges per key | hand edits to other keys survive |
| Text mode sends the whole text; refused if the file changed | a whole text cannot be merged safely |
| Easy → Text with unsaved edits: the box shows Core's `dry_run` text (edits applied), marked unsaved | nothing is lost when you switch |
| Text → Easy with unsaved text: "Save or discard the text first" | the easy model is built from the file, not from a draft |
| Both show the same revision pill and banner | one truth |

### 4.4 The I2C devices card

One row per device type of §5 that is in the file, plus **Add a device** (a select of the types not present):

| Column | Content |
| --- | --- |
| Device | name + the section (`NeoRotary 4 · [neorotary4]`) |
| On | Off/On pills (`enabled`) |
| Bus | select of the buses that exist, labelled: `1 · Pi header (GPIO 2/3)`, `10 · cam0 connector (camera bus)`, `11 · cam1`, `13`/`14 · HDMI DDC`. A configured bus that does not exist stays selected: `4 · missing` |
| Address | select of the type's addresses (PCF8574 `0x20`-`0x27`, INA219 `0x40`-`0x4F`, NeoRotary `0x49` + `0x4A`-`0x4F`, IMU `0x68`/`0x69`, Grove `0x04`/`0x08`, hat `0x34`) + custom hex |
| State | `hardware_status`: Connected / Not connected: *driver error* / Wrong device: *ID* / Off / No actions mapped / Not in this file |
| Probe | `probe_device` → found, ID, name, source (driver or bus) |

**Scan bus** (per bus): known addresses only on camera buses; `all=true` elsewhere. It lists answers named from the
known-address table (`R4 §1.3`) and tells you what each ID read proves. The probes are register reads, as Core's drivers do
them:

| Device | Probe | Proves |
| --- | --- | --- |
| NeoRotary 4 | seesaw `0x00 0x01`, 10 ms, read 1 byte → `0x87` | ATtiny817 seesaw (`HW/NeoRotary4Input.cpp:494-514`) |
| CFE hat | read byte twice, equal | something answers; card bit 0 (`App:4550-4598`, `src/util/CfeHat.hpp:35-46`) |
| INA219 | register `0x00`, 2 bytes | answers (default `0x399F`: UNCONFIRMED w.r.t. the KB) |
| IMU | WHO_AM_I `0x75` (MPU6050 `0x68`, ICM42688 `0x47`); BMI160/270 chip ID `0x00` | datasheet values, UNCONFIRMED in the KB (M4, `R4` Q5) |
| PCF8574, Grove | read 1 byte | ACK only: no ID register |
| TMP117 (known, not used) | register `0x0F`, 2 bytes → `0x0117` | datasheet, UNCONFIRMED in the KB |

**Conflicts the card explains** (from `R4 §2.2`, each with the evidence Core can read as `pi`):

| Condition | Evidence | Card text |
| --- | --- | --- |
| Bus 1 missing, DPI overlay active | no `/dev/i2c-1`; `config.txt` has uncommented `dtoverlay=vc4-kms-DPI-*`, `waveshare-*dpi*` or `hyperpixel*` that apply to a Pi 5 (`[all]`/`[pi5]`, sketch check 9) | "Bus 1 does not exist. GPIO 2/3 are taken by the DPI overlay on /boot/firmware/config.txt lines 76-78 (vc4-kms-DPI-4inch, waveshare-4dpi, waveshare-touch-4dpi). Without a DPI panel you can turn them off. **You** run this; Apertar never edits config.txt:" + the box below. "With a DPI panel in use, bus 1 stays gone: feed the hat's Qwiic hub 3.3 V and use bus 10 with poll 50 ms (KB SRC §5)." |
| Bus 1 missing, no `i2c_arm` | no `dtparam=i2c_arm=on` under `[all]`/`[pi5]` | "I2C on the header is off. Add `dtparam=i2c_arm=on` under `[all]` in /boot/firmware/config.txt (sudo nano), then reboot. Appending at the end lands under the last filter." |
| Any bus missing | `/dev/i2c-N` absent | "Bus 4 does not exist on this Pi (buses: 1, 10, 13, 14). INA219: pick a bus that exists, or turn it off." |
| Wrong seesaw | ID ≠ `0x87` | "0x48 on bus 10 answered 0x12, not 0x87: not a NeoRotary 4. 0x48 is the StarlightEye's TMP117." |
| Dead hub | the hat answers only on bus 10 and nothing at `0x49` on any bus | "Nothing answers at 0x49. The hat's Qwiic hub needs 3.3 V from its 2x3 header or a Qwiic cable; a ribbon-only hat has a dead hub (SRC §3.4)." |
| Two masters | `0x34` on bus 1 **and** bus 10 | "The hat answers on bus 1 and bus 10. If JP3/JP4 are closed the hat joins the header bus and the camera bus. Unconfirmed: the StarlightEye's own controller may answer at 0x34 on bus 10 (KB R4 Q4)." |
| Device on the camera bus | `bus=10` or `11` | "Bus 10 also carries the sensor's per-frame writes: use poll 50 ms or more." |
| Saved, not applied elsewhere | `pending` | "Still to do (you): sudo systemctl restart apertar-cfe-automounter" |

The command box is generated from the line numbers Core found. Contiguous lines become one `sed` range; otherwise one `-e`
per line. It always starts with a backup:

```bash
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.bak-apertar
sudo sed -i '76,78 s/^dtoverlay=/#dtoverlay=/' /boot/firmware/config.txt
sudo reboot
```

### 4.5 The touch UI's share (T43, optional)

- **A read-only Controls card** in System (`defaultSystemOrder`, `UI:qml/SettingsPage.qml:813`): one line per device from
  `hardware_status` ("NeoRotary 4 · bus 1 · connected"), the outside-change and pending lines, and "Edit in the WebUI:
  http://<camera>:8000 → Settings → Controls". No editing on the camera: a 720x720 touch screen is the wrong place for a pin
  matrix, and every edit path would need the same merge rules.
- **The two template writers removed** (`UI:src/DisplayConfigBridge.cpp:41`, `UI:src/Ina219Bridge.cpp:69`). A missing file
  then means code defaults everywhere, and the WebUI shows Core's one template. That ends three disagreeing templates (`R2
  §1.5`) and the F3 revert hazard.
- **The gyro page through Core:** `GyroConfigBridge`'s writes become the existing `set_imu_*` commands (`R3 §2.3`), so Core
  is the only program writing the file. Its `refresh()` runs on the `controls` event (broadcast since T38, F23).

---

## 5. The hardware catalog (device types the editor offers), with Patrik's rig as the example

| Type (section) | Hardware | Bus/address default in code | Readers | On Patrik's rig (KB) |
| --- | --- | --- | --- | --- |
| `cfexpress_hat` | RPI5-CFE-Hat controller (CH32V003), card presence and eject | 10 / `0x34` (automounter: on by default; Core watcher: off without the section) | Core watcher, Core Python, automounter (root) | **bus 1**, `0x34` (`HL:25`) |
| `neorotary4` | Adafruit NeoRotary 4 (seesaw ATtiny817, ID `0x87`), 4 knobs + 4 pushes | 1 / `0x49` | Core | **on, bus 1, `0x49`**; knobs ISO, shutter, WB, fps (`TUT:81`; exact tokens: M1) |
| `pcf8574` | PCF8574 8-pin I2C expander (buttons; tally/trigger target) | 1 / `0x20` | Core | **off, no chip**; the image's file had `bus=10 address=0x20` (`HL:39-43`) |
| `grove_analog` | Grove Base HAT ADC (STM32 `0x04` / MM32 `0x08`), 8 channels | 1 / `0x04` | Core | not fitted |
| `ina219` | INA219 power monitor | **4** / `0x40` | Core, touch UI | **absent: `/dev/i2c-4` does not exist** (`SRC:80`) → Q7 |
| `imu` + driver | MPU6050/6500, BMI160, BMI270, ICM42688-P | 1 / `0x68` (auto-probes `/dev/i2c-0..32`) | Core, touch UI | `0x68` on **bus 10**; identity PROBABLE (`R4` Q5, M4) |
| `gpio_buttons`, `gpio_encoders` | Pi GPIO (RP1 chip), buttons and quadrature encoders | chip auto, pull up, active low | Core | buttons on **GPIO 10 and 6**, active low (`HL:44`); actions: M1 |
| `recording_indicator` | Tally LED on GPIO or a PCF pin | line −1 (must be set) | Core | **GPIO 21, active high** (`HL:36-49`) |
| `trigger_output` | Trigger pulse (hot shoe, flash) | GPIO 17, 80 ms | Core | **off** (it held GPIO 21 before) |
| (fixed) | Pi 5 power button | evdev `pwr_button` | Core | built in |
| (known, not configurable) | IMX585 `0x1a` (kernel driver, bus 10); TMP117 `0x48` (StarlightEye, not read by Apertar); StarlightEye CH32V003 (address unknown) | — | — | bus 10 |

The task brief named "PCF8574 0x20 on bus 10" for the rig. The KB says no PCF8574 is fitted: `[pcf8574] enabled=false` after it
logged `Remote I/O error` (`HL:39-43`). `bus=10 address=0x20` is the image file's value. The example keeps it, off.

**The example file the tutorials and the host test use.** It is shaped like the rig from KB facts; it is **not** the live file
(M1 replaces it with the real one):

```ini
# Apertar hardware configuration. ApertarCore validates and writes this file: WebUI Settings > Controls,
# or Settings > Config for the text. Hand edits are kept; put comments on their own lines.

[ina219]
enabled=false

[pcf8574]
enabled=false
bus=10
address=0x20

[trigger_output]
enabled=false

[recording_indicator]
enabled=true
target=gpio
line=21
active_high=true

[neorotary4]
enabled=true
bus=1
address=0x49
encoder0_cw=iso_up
encoder0_ccw=iso_down
encoder1_cw=shutter_up
encoder1_ccw=shutter_down
encoder2_cw=wb_up
encoder2_ccw=wb_down
encoder3_cw=fps_up
encoder3_ccw=fps_down
encoder3_press=resolution

[gpio_buttons]
enabled=true
active_low=true
d10=capture
d6=eject

[imu]
enabled=true
driver=mpu6050

[mpu6050]
bus=10
address=0x68

[cfexpress_hat]
enabled=true
bus=1
address=0x34

[storage]
mount_path=/media/RAW
```

On this file with the rig's buses (1, 10, 13, 14) the validator finds no errors (sketch check 8). It finds one warning only if
`[ina219]` stays enabled on bus 4. Before the fix (buses 10, 13, 14, 15; DPI at lines 76-78) it names the missing bus 1, the
DPI line, and the buttons and the tally on DPI pins (sketch check 8).

---

## 6. Implementation plan, file by file

Order = build order. Line numbers are at `0296ed1`/`5aab7e2`. **T33-T35 move them**: use the search string. Risk: **low** =
host-tested header, or host-checked (`g++ -fsyntax-only`, `node --check` plus a mocked Chromium run, a Qt host build).
**Medium** = threads, locks or a large JS block, host-checked but its behaviour seen only on the Pi. **High**: none. Nothing in
`CameraController.cpp`.

### T36: one action vocabulary

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 36.1 | new `src/hardware/ActionCatalog.hpp` | | `kSpecs[]`, `canonicalAction`, `classify`, `suffixAfter`, `numberAfter`, `suggestion`, `catalogJson` (sketch, 295 lines) | low |
| 36.2 | KB `working/tools/action_catalog_test.cpp` + `make_old.sh` | | the sketch's section 1-2 checks; runs against the Pi's tree before 36.3 | low |
| 36.3 | `HW/GpioInput.cpp:108-207`, `HW/Pcf8574Input.cpp:140-247`, `HW/NeoRotary4Input.cpp:121-220` | `std::string normalizeSingleAction(std::string action)` | delete; `normalizeAction` calls `hardware::normalizeButtonMapping(action, hardware::actions::canonicalAction)` | low |
| 36.4 | `App:1374-1402` | `std::optional<std::string> hardwareActionSuffix(const std::string &action,` | call the header's `suffixAfter`/`numberAfter` (same results; sketch check 2) | low |
| 36.5 | `App:9147` | `Hardware input action ignored: unknown action` | add `Did you mean …` from `suggestion()` | low |
| 36.6 | after `App:9612` (`list_sensor_modes` block); `App:9633` | `if (command.name == "list_sensor_modes") {`; `if (command.name == "help")` | `list_actions` handler (catalog + value lists from `pcfIsoOptions` `App:1311` and its siblings, FPS and resolution lists for the current sensor); add to help | low |

### T37: Core owns the file

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 37.1 | new `src/hardware/HardwareConfigText.hpp` | | the sketch: parse, join, revision, schema table, `canonicalKey`, edits, conflicts, diff, `validate`, `newErrors`, `parseConfigTxt` (773 lines) | low (51 checks) |
| 37.2 | new `src/hardware/HardwareConfigStore.hpp/.cpp`; `CMakeLists.txt:83-91` | `src/hardware/TriggerOutput.cpp` | `currentText()`, `currentRevision()` (stat-cached), `edit(base, edits, by)`, `replace(base, text, by)`, history (20), `hardware-state.conf`, revision cache (8); uses `SF` `atomicWrite` + `QtIniLock` | low (host test with a temp dir) |
| 37.3 | `App:5430-5526` | `std::string buildHardwareConfigFileJson()`; `bool saveHardwareConfigFile(` | both through the store; GET adds `revision`; POST takes `X-Apertar-Revision`; issues in the error reply | low |
| 37.4 | `App:7321-7341` | `if (request.method == "POST" && request.path == "/api/config") {` | read the header; 409 with the conflict message | low |
| 37.5 | `HW/Mpu6050RecordingSession.cpp:604-713`, `:715-840` | `bool writeHardwareConfigValue(`; `bool updateImuBiasConfig(` | bodies become store key edits (`by: imu`); the `.tmp` + remove-then-rename code goes | low |
| 37.6 | after `App:9612`; help | as 36.6 | `get_controls`, `set_controls` (`text=` only in T37), `dry_run`; recording gate; `[run_script]` gate | low |
| 37.7 | `App:4333-4446` | `std::string defaultHardwareConfigTemplate()` | add the header comment, `[neorotary4]` (off), `[gpio_encoders]`, `[grove_analog]`; `[pcf8574] bus=1` and remove the ignored `[imu] bus/…` keys (R2 §1.5). The text is checked by `validate()` in the host test | low |
| 37.8 | `Web:10372-10401` | `async function saveConfigFile() {` | send `X-Apertar-Revision`; show the issues with line numbers in the toast; on 409 keep the text | low |

### T38: apply without a restart

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 38.1 | `App.hpp:121-139`, `:187` | `std::mutex commandMutex_;`; `std::thread mediaWatcherThread_;` | `HardwareConfigStore hardwareConfig_;`, `std::thread controlsThread_;`, `std::mutex controlsMutex_;`, `std::condition_variable controlsWake_;`, `bool controlsReloadWanted_`, `std::string appliedRevision_`, `std::atomic<uint64_t> hardwareConfigGeneration_` | low |
| 38.2 | after `App:7043`; `App:7050-7066` | `syncRecordingTracking(camera_.isRecording());`; `pcf8574Input_.stop();` | start the worker after the drivers; stop it first in `stop()` | medium |
| 38.3 | new, after `App:8836` | `void ApertarCoreApp::handleSingleHardwareInputAction(` | `runControlsWorker`, `reloadHardwareDrivers` (§3.6 code), `noticeOutsideChange`, `hardwareStatusJson`, `controlsEventJson` | **medium** (thread and order; host syntax-check only) |
| 38.4 | each driver `.hpp` (`HW/NeoRotary4Input.hpp:20-25` and the five others) | `std::string lastError() const;` | `bool running() const { return running_; }` | low |
| 38.5 | `App:4693-4695` | `static const Ina219HardwareConfig config = loadIna219HardwareConfig();` | a mutex-guarded cache reloaded when `hardwareConfigGeneration_` changes | low |
| 38.6 | `App:9306-9313` | `const CfeHatConfig hatConfig = loadCfeHatConfig();` | rebuild `CfeHatReader` in the loop when the generation changes; log the new bus | medium |
| 38.7 | 37.6's handler | `set_controls` | `set.*`/`unset.*` edits with the per-key merge; `apply_controls`; `apply` in the reply with the restart list per changed section | low |
| 38.8 | `App:7857`; the `get_state` body | `std::string ApertarCoreApp::buildWebStateJson() const` | `controls_revision`, `controls_applied_revision`, `controls_outside`, `hardware_status` | low |
| 38.9 | `App:11289-11308` | `eventJson.find("\"event\":\"still_exposure\"")` | whitelist `"event":"controls"` (F23) | low |

### T39: I2C devices + the Controls panel, part 1

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 39.1 | new `src/hardware/I2cProbe.hpp/.cpp` | | `listBuses()` (`/dev/i2c-*`, `/sys/class/i2c-adapter/i2c-N/name`, labels), `probe(type, bus, address)` with the register reads of §4.4, `scan(bus, all)`; `I2C_SLAVE` only (EBUSY = kernel driver); 10 ms between select and read | low (host compile; behaviour on the Pi: M9) |
| 39.2 | new `src/hardware/SystemFacts.hpp` | | buses + `parseConfigTxt` + GPIO line info (`GPIO_V2_GET_LINEINFO_IOCTL` on the chip `GpioInput` picks, `HW/GpioInput.cpp:505-537`) | low |
| 39.3 | new `src/hardware/ControlsModel.hpp` (devices part) | | `devicesJson(doc, facts, status)`: one entry per device section, with the conflicts of §4.4 | low (host test) |
| 39.4 | App handlers | as 36.6 | `scan_i2c`, `probe_device` (driver state first: never probe a chip Core's driver holds); `get_controls` gains `model.devices` and `system` | low |
| 39.5 | `Web:2773`, `Web:3840`, `Web:4165`, `Web:4240`, `Web:6185-6206` | `data-panel="config" type="button"`; `<section class="settings-panel" data-panel="config">`; `const settingsPanelMeta = {`; `configDirty: false,`; `function setSettingsPanel(panelName) {` | nav item, panel, meta, state (`controlsServer`, `controlsDraft`, `controlsDirty`, `controlsDrag`), fetch on open | low |
| 39.6 | same panel | | Card 1 (file) + Card 2 (I2C devices), scan sheet, guided box with copy buttons | medium (JS size) |

### T40: the easy editor

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 40.1 | `ControlsModel.hpp` (inputs and outputs) | | `controlsJson(doc, facts)`: rows, gestures with key and line, occupancy and reservations | low (host test) |
| 40.2 | near `Web:1887` | `.preset-row {` | `.control-row`, `.gesture-line`, `.action-chip`, `.chip-handle { touch-action: none; min-width: 44px; min-height: 44px; }`, `.action-chip.dragging`, `.gesture-line.drop-target`; rows wrap at phone width | low |
| 40.3 | the panel | | Card 3 (inputs) + Card 4 (outputs): `renderControlRows`, `buildPinPicker` (one registry), `buildActionSelect` (from `list_actions`), `installChipDrag`, `editsFromDraft`, `reviewControls` (dry run), `saveControls` | **medium** (≈900 lines of JS; `node --check` + mocked Chromium as T32) |

### T41: the text editor

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 41.1 | `App` | | `controls_history`; `get_controls base=` returns the diff | low |
| 41.2 | `Web:1562`, `Web:3840-3872`, `Web:10307-10401` | `.config-editor {`; `function updateConfigEditorControls() {` | gutter, Check, diff sheet, conflict box, history select, shared banner | medium |

### T42: hold and double press

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 42.1 | new `src/hardware/ButtonGesture.hpp` + KB test | | `update(pressed, nowMs) → {press, hold, double}`. With only `press` mapped: fire on the press edge (today). With `hold` mapped: press fires on release before `hold_ms` (default 800), hold fires once at `hold_ms`. With `double` mapped: press fires `double_ms` (default 350) after release if no second press; double fires on the second press edge. Bounce < 80 ms ignored (as `HW/PowerButtonGesture.hpp`) | low (host test) |
| 42.2 | `HW/GpioInput.cpp:690-710`; `HW/Pcf8574Input.cpp:505-521`; `HW/NeoRotary4Input.cpp:680-709` | `if (button.stablePressed)`; `emitAction(config_.actions[pin]);`; `emitAction(config_.encoders[encoder].press);` | per button a `ButtonGesture`, fed every poll; parse `_hold`, `_double`, `hold_ms`, `double_ms` | low (host syntax) |
| 42.3 | catalog, model, Web | | `gestures` in `list_actions`; Hold and Double press lines; the note "Press now fires on release, because Hold is set" | low |

### T43: touch UI (UI repo)

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 43.1 | `UI:src/DisplayConfigBridge.cpp:41-326`, `:587`; `UI:src/Ina219Bridge.cpp:69-342`, `:497` | `bool ensureDefaultHardwareConfigFile()`; `    ensureDefaultHardwareConfigFile();` | delete both writers and calls | low |
| 43.2 | `UI:src/GyroConfigBridge.cpp:1577` and its callers | `bool GyroConfigBridge::writeConfigValue(const QString &sectionName,` | send `set_imu_*` through `ApertarControlBridge`; `refresh()` on the `controls` event | medium |
| 43.3 | `UI:qml/SettingsPage.qml:813` + a new `ControlsStatusCard.qml` (in both `APERTAR_QML_FILES` and `qml.qrc`, `R3 §2.4`) | `readonly property var defaultSystemOrder: [` | read-only card from `hardware_status` | low (Qt host build) |

### Size (PROBABLE: sketch counts + T32/T34 rates)

| Tutorial | Lines added (removed) | Checked before the Pi |
| --- | --- | --- |
| T36 | ~380 (−300) | all (test + syntax) |
| T37 | ~1,200 | all |
| T38 | ~350 | syntax only for the worker |
| T39 | ~1,100 | Core all; WebUI `node --check` + mock |
| T40 | ~1,150 | same |
| T41 | ~430 | same |
| T42 | ~500 | all |
| T43 | ~300 (−560) | Qt host build |
| **Total** | **~5,400 (−860)** | the WebUI JS and the worker are the parts the Pi must prove |

---

## 7. Tutorial outlines (KB format)

Files: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T3x <topic>.md`, frontmatter as in `TIDX` (`datum`,
`kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext`, `typ: digital anteckning`), ending `#CINEMATE` / `#APERTAR`, a tutor
block above the tags. Every tutorial: build on the Pi, restart by Patrik, commit on `cinemate-port`, push only when he decides.
Undo for all: `git revert` the commit, and restore `~/apertar-hardware.conf` from `~/.config/apertar-core/hardware-history/`.

### T36. One list of button actions: a header that replaces three copies, and `list_actions` so the WebUI never keeps a fourth

- **Learn:** (1) why three identical copies are a bug waiting to happen (M5); (2) pure logic in a header with a host test that
  compares against the old code; (3) a socket command that serves data instead of acting. **Risk:** none for the camera:
  same names, same results (the test proves it). Core restart. **Time:** 1.5 h.
- **1 Problem:** add `zebra_toggle` (planned T11, `TUT:87`) and you edit three files. A typo in the file is silent until you
  press.
- **2 How it works:** read `HW/ButtonActionList.hpp:80-119`, `HW/GpioInput.cpp:108-207`, `App:8808-8836`, `App:8838-9148`.
- **3 Find it yourself:**
  - **3.1** `grep -c 'std::string normalizeSingleAction' src/hardware/*.cpp`. Prediction: 1 in each of three files. Question:
    what does an unknown name become? Answer: itself (`:201`), and App ignores it at `:9147`.
  - **3.2** `diff <(sed -n 108,202p src/hardware/GpioInput.cpp) <(sed -n 121,215p src/hardware/NeoRotary4Input.cpp)`.
    Prediction: no differences (checked here). The PCF8574 copy (`:140-242`) differs only in line wrapping.
- **4 Make the change:**

  | Step | What | Check |
  | --- | --- | --- |
  | 4.1 | `ActionCatalog.hpp` (36.1) | `grep -c 'inline std::string canonicalAction'` → 1 |
  | 4.2 | copy the test, run `make_old.sh`, build, run (36.2) | `./action_catalog_test` ends `all ok` |
  | 4.3 | delete the three copies (36.3) | `grep -c normalizeSingleAction src/hardware/NeoRotary4Input.cpp` → 0 |
  | 4.4 | App suffix parsers (36.4, 36.5) | `grep -c 'actions::suffixAfter' src/ApertarCoreApp.cpp` → 1 or more |
  | 4.5 | `list_actions` (36.6); host `g++ -fsyntax-only` | `grep -c 'command.name == "list_actions"'` → 1 |

- **5 Build and test:** Pi build, restart (Patrik). `core.py list_actions` lists `iso_value` with ISO values 100 … 51200. Every
  knob and button works as before (a one-minute walk-through).
- **7 If it went wrong:** a test FAIL line names the token and both results → a missing alias in `kSpecs`.

### T37. Core owns apertar-hardware.conf: one writer with a lock, a revision and a history, a validator that names the line

- **Learn:** (1) why a file several processes read needs one writer; (2) atomic write, lock, revision, and why a "lost update"
  happens; (3) a validator built from what each reader really does. **Risk:** a bug in the store could write a wrong file.
  The host test and `.bak` + history cover it; the first save shows a diff. **Time:** 3 h.
- **1 Problem:** today four writers, no lock, no version; the IMU writer can delete the file (`HW/Mpu6050RecordingSession.cpp:700-705`);
  a comment after `bus=1` silently means bus 10 for the hat (`App:4580`).
- **3 Find it yourself:**
  - **3.1** `grep -n 'remove(path, ec)' src/hardware/Mpu6050RecordingSession.cpp` → 2 lines. Question: what does the UI do at
    its next start if the second rename fails too? Answer: writes its template, hat on bus 10 (`UI:src/DisplayConfigBridge.cpp:41-47`).
  - **3.2** M1 on your file. Prediction: no errors; aliases; maybe the INA219 warning.
  - **3.3** In a copy (`APERTAR_HARDWARE_CONFIG` is not needed: just a scratch file and the host test), write `bus=1 # x` under
    `[cfexpress_hat]`. Question: which readers ignore it? Answer: Core's C++ and both Python copies; the automounter strips the
    comment.
- **4 Make the change:** 37.1 (header + test: all ok) → 37.2 (store + temp-dir test) → 37.3-37.4 (`/api/config`) → 37.5 (IMU
  writers) → 37.6 (commands) → 37.7 (template) → 37.8 (page). One check per step.
- **5 Test:**
  - `core.py get_controls` shows `"revision":"h…"` and your file's issues.
  - `core.py set_controls base=<rev> text="$(cat ~/apertar-hardware.conf)" dry_run=true` → empty diff.
  - Calibrate the gyro in the WebUI → `~/.config/apertar-core/hardware-history/` gains a version `by imu`.
  - Edit with nano, then save in the Config panel with the old text → refused, your text kept.
- **7 If it went wrong:** `Not saved: N new errors` → the message names the line; restore from history; `git revert`.

### T38. Save and it works: Core restarts its drivers itself, merges edits per key, and shows each driver's state

- **Learn:** (1) why the reload must run on its own thread (F7: draw the lock graph); (2) stop all, then start in boot order;
  (3) a merge per key. **Risk:** a deadlock would freeze buttons. It is avoided by design; test 5.2 tries it. **Time:** 2.5 h.
- **3 Find it yourself:** **3.1** `grep -n 'lock_guard' src/ApertarCoreApp.cpp | sed -n '1,40p'`. Find the three hardware
  mutexes and who takes them in which order. **3.2** Why does `stop()` wait up to a second on a missing bus? (the retry
  `sleep_for(1000)`, `HW/NeoRotary4Input.cpp:636-637`).
- **4 Make the change:** 38.1-38.8.
- **5 Test:**
  - **5.1** `core.py set_controls base=<rev> set.neorotary4.encoder3_press=zebra` → knob 4 press toggles zebra with no restart;
    journal `controls: applied … in N ms`.
  - **5.2** Hold a knob turning while saving 10 times (`for i in …`): no freeze, no `Hardware input action failed`.
  - **5.3** Edit `encoder2_cw` over ssh, then save a different key from core.py with the old base: both kept. Edit the same
    key: refused with both values.
  - **5.4** `curl -s 127.0.0.1:8000/api/state` shows `hardware_status` with `neorotary4` `connected`.
- **7:** a reload that never finishes → `journalctl … | grep controls`; the worker logs before each stop.

### T39. I2C devices in the WebUI: which buses exist, what answers, why bus 1 is missing, and what only you can do in config.txt

- **Learn:** (1) the Pi's I2C buses and what creates them; (2) probing by ID register, not ACK (seesaw); (3) never probing a
  chip a driver holds; (4) reading `config.txt` without writing it. **Risk:** scans add bus traffic: they are refused in a take
  and limited to known addresses on the camera bus. **Time:** 3 h.
- **3 Find it yourself:**
  - **3.1** M3 and M4 (the bus list, `i2cdetect -y 1`, the seesaw ID loop). Prediction: `34`, `49`; ID `0x87` most of the
    time, sometimes not, while Core polls.
  - **3.2** `grep -n 'dtoverlay' /boot/firmware/config.txt`: your three commented DPI lines.
- **4 Make the change:** 39.1-39.6.
- **5 Test:**
  - **5.1** Controls → I2C devices on your rig: hat bus 1 connected, NeoRotary connected, INA219 "bus 4 does not exist".
  - **5.2** Scan bus 1 and bus 10.
  - **5.3** The before-the-fix state, without touching `config.txt`: set NeoRotary to bus 15 (a bus that does not exist) →
    red row, "bus 15 does not exist". Set it back.
  - **5.4** The DPI text from a host run of `parseConfigTxt` on SRC's `config.txt` excerpt (the host test does it).

### T40. The easy editor: a row per button or knob, a dropdown per gesture, action chips you can drag, pins already used greyed out

- **Learn:** (1) a page is a view of a file (Cinemate `7de3065`); (2) one occupancy registry for every picker; (3) drag with
  pointer events plus a non-drag path; (4) why rows must not redraw from a poll. **Risk:** WebUI only; the file changes only
  through `set_controls`. **Time:** 3 h.
- **5 Test:**
  - Remap knob 4 press by dropdown.
  - Drag `fps24` before `iso200` on a PCF pin (a dry run shows the order).
  - Move button d6 to GPIO 21 → disabled ("GPIO 21 · Tally").
  - A phone-width run; Review shows a diff; Save applies.

### T41. The text editor for advanced users: line numbers, Check, a diff before Save, conflicts, history

- **Test:** type `bus=1 # x` under `[cfexpress_hat]` → Check: error at that line. Save → diff → confirm. Edit over ssh
  meanwhile → conflict box, Show changes. Restore yesterday's version from history.

### T42. Hold and double press on every button, knob push and PCF pin

- **Learn:** a gesture state machine fed by polls; why press must wait when hold or double is mapped. **Risk:** changes the
  timing of a button only when you map hold or double on it. **Test:** host test; `d10_hold=standby`; knob push double →
  `photo`; the WebUI note about press on release.

### T43. The touch UI: a read-only Controls card, no second template, the gyro page through Core

- **Test:**
  - Rename the file, start the UI: no template appears; rename back.
  - Change the IMU orientation on the touch screen → history shows `by imu`.
  - The card shows the NeoRotary connected.

### Tutor blocks (anchors checked here: each string occurs once in its file at `0296ed1` / `5aab7e2`; no check pipes)

T36:

```
%% tutor
ref core src/hardware/GpioInput.cpp 108 std::string normalizeSingleAction(std::string action)
ref core src/hardware/Pcf8574Input.cpp 140 std::string normalizeSingleAction(std::string action)
ref core src/hardware/NeoRotary4Input.cpp 121 std::string normalizeSingleAction(std::string action)
ref core src/hardware/ButtonActionList.hpp 80 ButtonActionList parseButtonActions(std::string_view text, Normalizer normalize)
ref core src/ApertarCoreApp.cpp 1374 std::optional<std::string> hardwareActionSuffix(const std::string &action,
ref core src/ApertarCoreApp.cpp 1311 std::vector<double> pcfIsoOptions()
ref core src/ApertarCoreApp.cpp 8838 void ApertarCoreApp::handleSingleHardwareInputAction(const std::string &action)
ref core src/ApertarCoreApp.cpp 9147 Hardware input action ignored: unknown action
ref core src/ApertarCoreApp.cpp 9612 if (command.name == "list_sensor_modes") {
ref core src/ApertarCoreApp.cpp 9633 if (command.name == "help")
check 3.1 | grep -c 'std::string normalizeSingleAction(std::string action)' /home/pi/ApertarCore/src/hardware/GpioInput.cpp | ^1$
check 4.1 | grep -c 'inline std::string canonicalAction' /home/pi/ApertarCore/src/hardware/ActionCatalog.hpp | ^1$
check 4.3 | grep -c 'normalizeSingleAction' /home/pi/ApertarCore/src/hardware/NeoRotary4Input.cpp | ^0$
check 4.5 | grep -c 'command.name == "list_actions"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"list_actions"}' | "id":"iso_value"
%%
```

T37:

```
%% tutor
ref core src/ApertarCoreApp.cpp 66 constexpr size_t kMaxEditableHardwareConfigBytes = 256 * 1024;
ref core src/ApertarCoreApp.cpp 4313 std::filesystem::path editableHardwareConfigPath()
ref core src/ApertarCoreApp.cpp 3477 parser.read(config_path)
ref core src/ApertarCoreApp.cpp 5430 std::string buildHardwareConfigFileJson()
ref core src/ApertarCoreApp.cpp 5463 bool saveHardwareConfigFile(const std::string &text, std::string *backupPath, std::string *errorMessage)
ref core src/ApertarCoreApp.cpp 7321 if (request.method == "POST" && request.path == "/api/config") {
ref core src/hardware/Mpu6050RecordingSession.cpp 604 bool writeHardwareConfigValue(const std::filesystem::path &configPath,
ref core src/hardware/Mpu6050RecordingSession.cpp 715 bool updateImuBiasConfig(const std::filesystem::path &configPath,
ref core src/util/SettingsFile.hpp 36 inline bool atomicWrite(const std::filesystem::path &path, const std::string &data)
ref core src/util/SettingsFile.hpp 59 class QtIniLock {
ref core src/web/WebControlPage.cpp 10372 async function saveConfigFile() {
ref ui src/DisplayConfigBridge.cpp 41 bool ensureDefaultHardwareConfigFile()
check 3.1 | grep -c 'std::filesystem::remove(path, ec);' /home/pi/ApertarCore/src/hardware/Mpu6050RecordingSession.cpp | ^2$
check 4.1 | grep -c 'inline std::vector<Issue> validate' /home/pi/ApertarCore/src/hardware/HardwareConfigText.hpp | ^1$
check 4.5 | grep -c 'std::filesystem::remove(path, ec);' /home/pi/ApertarCore/src/hardware/Mpu6050RecordingSession.cpp | ^0$
check 4.6 | grep -c 'command.name == "set_controls"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "revision":"h[0-9a-f]{16}"
%%
```

T38-T43 tutor blocks are written with each note: T36/T37 move App lines by several hundred.

---

## 8. Measurements on the Pi first

All read-only, as `pi`, before any code. `K=~/apertar-kb/working/tools`. Lines marked "Patrik" need `sudo`.

**M1. The live file** (decides the host-test fixture, Q8, Q12)

```bash
grep -n '^\[' ~/apertar-hardware.conf                                          # sections and where (R3 U1)
grep -nE '^\s*(d|gpio|pin|bcm|p)[0-9_]|^\s*(encoder|enc|rotary)[0-9]' ~/apertar-hardware.conf   # every mapping (R4 Q9)
grep -nE '^[^#;]*=[^#;]*[^[:space:]#;][[:space:]]*[#;]' ~/apertar-hardware.conf  # comments after values: expect none (a ; inside events= is a separator)
grep -nE '^[[:space:]]+[^#;[:space:]]' ~/apertar-hardware.conf                  # indented keys: expect none
awk -F= '/^\[/{s=$0} /=/ && !/^[[:space:]]*[#;]/{k=s FS $1; if (seen[k]++) print NR": duplicate "k}' ~/apertar-hardware.conf   # expect nothing
stat -c '%U:%G %a %y %n' ~/apertar-hardware.conf ~/apertar-hardware.conf.bak /home/pi   # owner and mode (R3 U2)
ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf 2>&1      # /boot copies (R3 U3)
diff ~/apertar-hardware.conf.bak ~/apertar-hardware.conf | head -40              # what the last WebUI save changed
```

**M2. Who reads it, as which user** (R3 U4)

```bash
systemctl show -p User -p Environment apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter
/usr/local/libexec/apertar-cfe-automounter --check-config     # prints the effective hat bus and exits (UI:src/CfeAutomounter.cpp:793-802)
```

**M3. Buses and access** (R4 Q12, R3 U6)

```bash
id; ls -l /dev/i2c-* /dev/gpiochip*
for a in /sys/class/i2c-adapter/i2c-*; do echo "$(basename $a) $(cat $a/name)"; done   # labels for the bus select
grep -nE '^\s*\[|dtoverlay|dtparam=i2c' /boot/firmware/config.txt                     # filters, overlays, i2c lines: readable as pi?
```

**M4. Devices, the way Core will probe them**

```bash
i2cdetect -y 1                                                                       # expect 34 and 49
for i in $(seq 20); do i2ctransfer -y 1 w2@0x49 0x00 0x01; sleep 0.01; i2ctransfer -y 1 r1@0x49; done | sort | uniq -c   # 0x87 how often while Core polls?
i2ctransfer -y 1 r1@0x34; i2ctransfer -y 1 r1@0x34                                   # hat status twice (0x02 with a card)
i2ctransfer -y 10 r1@0x34                                                            # two masters / R4 Q4: does anything answer here now?
i2cget -y 10 0x68 0x75                                                               # IMU WHO_AM_I (MPU6050 0x68: datasheet)
i2ctransfer -y 10 w1@0x48 0x0f r2@0x48                                               # TMP117 device ID 0x01 0x17 (datasheet)
```

Prediction: `0x87` in most tries, but not all, because Core's driver interleaves its own select-sleep-read
(`HW/NeoRotary4Input.cpp:559-570`). Decides `probe_device`'s "driver first" rule (§2.5).

**M5. GPIO line info** (decides where the pin reservations come from)

```bash
gpioinfo gpiochip0 2>/dev/null | head -30 || gpioinfo -c gpiochip0 | head -30   # libgpiod v1 or v2
pinctrl get 2,3,6,10,21                                                          # functions: SDA1/SCL1, inputs, the LED
```

Prediction: 6 and 10 `apertar-gpio-input`, 21 `apertar-rec-led` (as `HL` 2026-10-25). For 2/3: UNCONFIRMED whether they show as
used.

**M6. The journal as pi** (`R4` K5)

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'NeoRotary4|PCF8574|GPIO input|recording indicator|trigger output|cfexpress hat|Hardware input' | tail -20
```

If it is empty or "permission denied", `pi` is not in `systemd-journal`. Then the journal checks in T37-T39 are Patrik's (`sudo`).

**After T37. M7:** the host test on the real file (M1's copy as the fixture): expect 0 errors.

**After T38. M8: reload time and safety.**

```bash
for i in 1 2 3; do python3 -I $K/core.py get_controls >/dev/null; python3 -I $K/core.py apply_controls base=$(python3 -I $K/core.py get_controls | grep -o '"revision":"h[0-9a-f]*"' | cut -d'"' -f4) force=true; sleep 3; done
journalctl -u apertar-core -b --no-pager | grep 'controls: applied' | tail -3       # N ms each; Patrik if K5
```

Prediction: under 200 ms with every bus present; about 1 s when a driver sits in its retry sleep.

**After T39. M9:** the WebUI scan of bus 1 and 10 against M4; `probe_device type=neorotary4 bus=1 address=0x49` says `source:
driver`.

---

## 9. Risks, questions, what is deliberately not built

### 9.1 Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Reload deadlock: a driver thread joined while it waits for a lock the reloader holds | PROBABLE avoided (the worker holds no App mutex) | T38 test 5.2; the journal logs before each stop |
| R2 | The touch UI's gyro page writes with `QSaveFile` and no lock: a Core write in the same milliseconds loses it | PROBABLE, small window | T43 moves the gyro page onto Core commands |
| R3 | `nano` saves in place; Core may hash half a file | PROBABLE | nothing applies by itself; the next stat sees the final file |
| R4 | A probe of a chip Core's driver polls reads the wrong ID | PROBABLE (two-transaction seesaw read) | driver state first (M4) |
| R5 | A scan disturbs the camera bus during preview | UNCONFIRMED | known addresses only on camera buses; refused in a take |
| R6 | DPI detection from `config.txt` misses an overlay set elsewhere (`include`, other filters) | PROBABLE | says "unknown" when no rule explains a missing bus |
| R7 | GPIO line info does not mark pinmuxed pins | UNCONFIRMED | M5; fallback to `/dev/i2c-1` + `config.txt` |
| R8 | No WebUI auth: anyone on the hotspot can edit controls (as today with the raw editor) | CONFIRMED (F16) | `[run_script]` paths not writable from the browser (Q2); keep the camera on a trusted network |
| R9 | The hat's bus has three readers; the automounter needs a root restart | CONFIRMED | the reply prints the command; T39's card shows "pending" |
| R10 | T33 adds `[camera] max_fps` with a hook in `POST /api/config` (T33 row 0.6) | CONFIRMED (T34 design §4) | whichever lands second moves the hook into the store's post-save callback; `[camera]` is already in the schema |
| R11 | Size: ~5,400 lines over eight tutorials; the WebUI JS is half of it | PROBABLE | each tutorial ends with a build and a test; the panels are independent |
| R12 | Hold or double changes when press fires on that button | CONFIRMED by design | only when mapped; the WebUI says so |
| R13 | After a Core restart the revision cache is empty; an old easy-mode base is refused if the file changed | PROBABLE | the history directory is the second cache |
| R14 | The validator and a reader disagree | PROBABLE | every rule comes from a cited reader line; host tests per rule |
| R15 | A save during the 2 s stat window right after a hand edit | PROBABLE | the store re-reads under the lock, so the merge is against the real current text |

### 9.2 Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Keep `~/apertar-hardware.conf` as the system-controlled file (Core writes it; its notes in `~/.config/apertar-core/`), or move it (§2.2 C: every reader in two repos, an automounter reinstall)? | keep |
| Q2 | `[run_script]` paths: editable from the browser (anyone on the camera's Wi-Fi can then make it run a script), or ssh only? | ssh only |
| Q3 | A hand edit over ssh: apply as soon as Core notices, or only on Apply / next start? | only on Apply / start |
| Q4 | Hold and double press (T42): wanted? Timings 800 ms hold, 350 ms double? Triple click, 2- and 3-position switches, chords (Cinemate has them): wanted? | T42 yes; the rest not built |
| Q5 | Saving during a take: refuse, or save now and apply after the take? | refuse |
| Q6 | Touch UI (T43): the read-only card, removing the UI's two templates, the gyro page through Core: all three, some, none? | all three, after T41 |
| Q7 | INA219: no chip on your rig and bus 4 does not exist. Set `[ina219] enabled=false` (ends the warning and the touch UI's "INA219 Unavailable")? | yes, as a T39 exercise |
| Q8 | Confirm the d10/d6 actions and the knob tokens (M1). They become the tutorials' example | M1 |
| Q9 | More than one of a device (two PCF8574s, two NeoRotary 4s)? Core runs one of each today (F17) | one; the schema can grow `[pcf8574_2]` later |
| Q10 | "Any API command" actions for advanced users (`cmd:set_fps_ramp enabled=true`), destructive ones blocked? | no: add catalog entries instead (one line each after T36) |
| Q11 | Numbering T36-T43 as listed, or merge (T40+T41, or T39 into T40)? | as listed |
| Q12 | Copy your live file into the KB as the host-test fixture? It holds no secrets: Wi-Fi passwords live in UI.conf | yes, after you read it |
| Q13 | The two-masters and IMU-identity reads in M4: log the results in `hardware-log.md` as facts? | yes, after you confirm |
| Q14 | Nav: a new **Controls** item next to **Config** (text), or one panel with an Easy/Text switch? | two items: Config stays where you know it |

### 9.3 Cinemate's defects, and why they cannot happen here

| Cinemate (R1 §3.3) | Here |
| --- | --- |
| D1 `"None"` strings crash three handlers | no "none" object grammar: an empty gesture is `unset`, or `none` for fixed channels, which every reader drops (`HW/ButtonActionList.hpp:102`) |
| D2 a pin remap does not enable Save | any draft change is dirty |
| D3 pins outside the list vanish on save | only changed keys are sent; unknown pins are shown, not dropped |
| D4 encoder fields overwritten on save | key edits; untouched keys are never written |
| D5 drag order re-sorted on load | the order is the file's order, never sorted |
| D6 one step per poll | NeoRotary4 fires `min(abs(delta), max_events_per_poll)` (`R2 §2.4`) |
| D7 the pencil defaults to `rec` | empty pencil = unset |
| D8 default clash | one template, validated by the host test |
| Two hand-kept catalogues | one header; `list_actions` |
| The editor has no auth and restarts the app | no auth (R8), but no restart: only the drivers reload |

### 9.4 Not built (and why)

| Item | Why |
| --- | --- |
| Writing `config.txt` (the DPI or `i2c_arm` lines) | house rule: guided text only (§4.4). The fan block's writers already break the rule (`R3 §3.3`); not extended |
| Editing on the touch screen | §4.5 |
| Chords, triple click, 2/3-position switches | Q4 |
| A "Tidy" rewrite to canonical spellings | aliases are harmless and rewritten only when edited; later, as a diff-first T41 exercise |
| A TMP117 reader (sensor temperature) | not asked; the scan names it |
| A file watcher that applies hand edits | Q3; half-saved files |
| Moving the file | §2.2 |

### 9.5 Sources

- Core `0296ed1`, touch UI `5aab7e2`, Cinemate `d6cc93e`, at the lines above.
- KB `b47f700`: `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`, `lessons/hardware-log.md` (2026-10-23, 2026-10-25),
  `tutorials/README.md`, `llm/tutoring.md` §5.
- The reader reports R1-R4 (this folder).
- The sketch: `sketch/hardware/ActionCatalog.hpp`, `sketch/hardware/HardwareConfigText.hpp`, `sketch/controls_test.cpp`,
  `sketch/make_old.sh`, `sketch/old_normalizers.inc`. Build:
  `g++ -std=c++20 -Wall -Wextra -Werror -I. -I<core>/src controls_test.cpp -o controls_test`, run → `all ok: 51 of 51 checks`.
