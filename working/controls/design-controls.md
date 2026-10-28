# Controls: Cinemate's GPIO dropdown and method assigning, Apertar style. How it works, what to build, what to measure first (v2)

**v2**, 2026-10-28, cloud session, designer pass after the two critiques (`critique-code.md`, `critique-operator.md`). Every
critic point was checked against the code before it was accepted. Point by point, with the evidence:
`changes-from-critique.md`. v1 is kept as `design-controls-v1.md` and its sketch as `sketch-v1/`. Read-only on every
repository. Nothing ran on the Pi.

Run on the host here:

- **Sketch v2: 78 of 78 checks pass** (v1: 51). Files: `sketch/hardware/ActionCatalog.hpp`, `sketch/hardware/HardwareConfigText.hpp`
  and `sketch/controls_test.cpp`, built with g++ 13.3, `-std=c++20 -Wall -Wextra -Werror`. The new checks:
  - every case the code critic reproduced (D1-D6);
  - the operator cases that live in the text model (9, 10, 11, 14);
  - App's number parser, both analog-target copies and the trigger-event parser, compared token by token with
    read-only copies extracted from Core `eb9cc39` (`sketch/make_old2.sh`);
  - a dispatcher coverage check that reads App's source;
  - the generated `config.txt` command, run twice with GNU sed on a copy.
- The critic's two probe programs (`critic-build/t_events.cpp`, `t_ids.cpp`), rebuilt against the v2 sketch:
  - `events=recording_start;still` is kept whole;
  - the duplicate `d10` reads `eject`, as `GpioInput` does;
  - an INA219 with no `bus=` is reported;
  - adding a line above old errors gives 0 new errors.
- `g++ -std=c++20 -fsyntax-only -Isrc -Iinclude` on Core `eb9cc39`: `ApertarCoreApp.cpp`, `GpioInput.cpp`, `NeoRotary4Input.cpp`,
  `Pcf8574Input.cpp`, `Mpu6050RecordingSession.cpp`: 0 errors each (v1 run; the code critic reran it with libcamera headers
  too, also 0).
- 56 tutor anchors and 39 plan search strings checked here. Each occurs once at the line given (`anchors.txt`, `search.txt` in this
  folder).

Trees (every `path:line` below is at these commits unless marked):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `App`, `App.hpp` | `src/ApertarCoreApp.cpp`, `.hpp` | Core `scratchpad/controls/core-tip` `eb9cc39` = Patrik's GitHub `cinemate-port` tip |
| `Web`, `WS`, `CS` | `src/web/WebControlPage.cpp`, `src/web/WebServer.cpp`, `src/ipc/ControlServer.cpp` | same |
| `HW/` | `src/hardware/` | same |
| `SF`, `CP` | `src/util/SettingsFile.hpp`, `src/ipc/ControlProtocol.cpp` | same |
| `UI:` | touch UI repo (`ApertarUI`, automounter, network helper, standby helpers) | `scratchpad/controls/ui-tip` `d8098d0` = GitHub `cinemate-port` tip |
| `Cm:` | Cinemate | `/home/user/tiramisioux/cinemate` `d6cc93e` |
| `SRC`, `HL`, `TIDX`, `TUT`, `tutorial.py`, `core.py` | KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`, `lessons/hardware-log.md`, `tutorials/README.md`, `llm/tutoring.md`, `tutorials/tutorial.py`, `working/tools/core.py` | KB `/home/user/apertar-kb` `d1d6a96` (these files are unchanged since v1's `e35ffa7`) |
| `R1`-`R4`, `CC`, `CO` | the reader reports; `critique-code.md`, `critique-operator.md` | this folder |
| `sketch` | `sketch/hardware/*.hpp`, `sketch/controls_test.cpp`, `sketch/make_old*.sh` | this folder (host-tested here) |

Labels: **CONFIRMED** = I opened the line (or ran the command) on the tree above. **PROBABLE** = derived; the derivation is given.
**UNCONFIRMED** = not checked, or only the Pi can settle it. A claim taken from a reader report or a critique without reopening
says so (`R2 §x`, `CO P7`).

Tutorial numbers. T33-T35 are taken by the ramp and ladder work. v2 has ten tutorials where v1 had eight; the v1 → v2 mapping
is in `changes-from-critique.md` §0.

| Number | What | Repo |
| --- | --- | --- |
| T36 | One vocabulary: `ActionCatalog.hpp` replaces the three `normalizeSingleAction` copies, the two analog-target copies and the trigger-event list; `list_actions` | Core |
| T37 | Core owns `~/apertar-hardware.conf`: text model, validator, one store for the process (lock, revision, history, stable-file check); `get_controls`, `set_controls text=`; the IMU writers through it; validated at every start | Core |
| T38 | No silent overwrites: `/api/config` through the store (409 for a stale or old page); the touch UI stops writing its template; "replaced by a default" detection with Restore; socket limit 1 MiB | Core + UI (2 deletions) + 1 WebUI function |
| T39 | Save and it works: the reload worker (only the changed driver group, never in a take), the driver status snapshot, per-key merge, `apply_controls`, outside edits, pending restarts | Core |
| T40 | I2C devices: buses, `config.txt` facts, probe / scan / Find, the DPI box; WebUI **Controls** panel part 1 (file card and I2C card); the touch UI's warning chip | Core + WebUI + UI |
| T41 | The easy editor, inputs: rows, pin pickers, gesture lines, Turn adjusts, action chips you drag to reorder | WebUI (+ a small Core model) |
| T42 | Listen, outputs and review: which control moved, the Outputs card, a plain-words Review, Undo last save, the after-save check | Core (driver callbacks) + WebUI |
| T43 | The text editor for advanced users: the **Config** panel with line numbers, Check and Fix, a diff before Save, stale-text merge, history | WebUI (+ Core history) |
| T44 | Hold and double press on every button source (`ButtonGesture.hpp`) | Core + WebUI |
| T45 | Touch UI, optional: a read-only Controls card and the gyro page through Core | UI repo |

`tutorial.py` finds a note by `T` + two digits (T34 design §0), so no `T37a`. T36-T39 come first because everything else writes
through them. **T40 is the first that changes what Patrik sees.** It is his NeoRotary fix done by the software, and it puts a
warning on the camera's own screen.

---

## 0. Short answer

1. **The system-controlled file is the existing `~/apertar-hardware.conf`.** It stays where 15 readers in 4 processes look.
   What is new:
   - Core becomes its only writer, through one store for the whole process (`hardware::configStore()`). App and the IMU code
     both call it.
   - The store has a lock, a revision, atomic writes, a history and a schema with a validator.
   - Core's notes about the file go in `~/.config/apertar-core/`.
2. **Moving or splitting the file is rejected**, as in v1: a move needs every reader in two repos changed, and a split puts the
   hat's bus and the encoder's bus in two files.
   - v2 adds one step: the touch UI stops writing its template when the file is missing (T38, two deletions). Until then,
     that template is the one thing that silently undoes the NeoRotary fix (`bus=10`, NeoRotary off).
3. **Format:** the INI the readers already parse.
   - **Each section is read with its own reader's comment rule** (v2). The trigger and the tally cut a comment only after a
     space. The inputs and the IMU cut at the first `#` or `;`. The hat's and the INA219's integers take no comment at all.
     A quoted script path may contain `;`.
   - Core writes canonical names, never a comment after a value, and changes only the lines it edits.
   - The two-line header comment is added only on a save from the WebUI.
4. **Two editors, one file.**
   - Easy mode sends key edits that Core merges per key.
   - Text mode sends the whole file. In v2 a stale text save is **merged too** when it changed only values, after a review
     (Q17); otherwise it is refused as before.
   - Hand edits over ssh are kept and announced, but never applied on the side: a save that would restart a driver whose
     section has an unapplied hand edit asks for **Save and apply both**.
5. **Live apply, asynchronous.**
   - A save only queues the reload; no command waits for it (otherwise the lock graph has a cycle, `CC A3`).
   - The worker restarts **only the driver group whose sections changed**. The groups are: GPIO buttons, encoders, PCF8574,
     trigger and tally together (they share pins); NeoRotary 4; Grove ADC.
   - It stops all of them first, then joins (about 1 s at worst, not 4 s).
   - It waits while a take runs, and re-syncs the tally under `commandMutex_`.
   - IMU, `[display]`, `[network]`, `[run_script]` and `[storage]` changes restart nothing in Core.
6. **Status you can trust.**
   - The worker owns a status snapshot per module: connected, error with its text, off, or no actions, each with "since 21:14".
   - The state builders read only that snapshot, never a driver's config from another thread (`CC A1`, a data race).
   - After each apply the WebUI compares before and after. A module that broke gets a red banner naming what it carries:
     "Pi GPIO buttons stopped: GPIO 15 is busy. Record (GPIO 10) and Eject (GPIO 6) do nothing now. [Undo last save]".
7. **Other processes:** the automounter, the touch UI and the network helper still need a restart.
   - Each "still to do" is worked out from facts: the service's start time against the time its sections changed. It clears
     by itself.
   - It is said in operator words, with the `sudo` line for ssh and the existing **Restart Camera** button (Q16).
8. **API:**
   - `get_controls`, `set_controls` (with `dry_run`: diff, issues, the hand edits it would apply, the apply plan),
     `apply_controls`, `list_actions`, `scan_i2c`, `probe_device`, `find_device`, `controls_history`.
   - The read-only hardware commands run before `commandMutex_`, so a scan never blocks a button.
   - Refusals carry their issues and conflicts.
   - The socket's 64 KiB line limit goes to 1 MiB (it silently dropped any large text save, `CC C1`).
9. **One vocabulary**, for the action names, analog targets, trigger events and tally tokens.
   - Host tests show it matches today's code: identical on 355 + 44 + 51 tokens, numbers identical except `inf`/`nan`, and a
     dispatcher coverage check.
   - The behaviour stays in App's dispatcher. A new action is a catalog line **plus** a dispatcher branch, and the coverage
     test fails until both exist (v1's "one line each" was wrong).
10. **WebUI.** A new **Controls** panel in the WebUI's own style:
    - *File card:* state, Discard changes, Undo last save, and a first-open summary.
    - *I2C devices:*
      - buses labelled by number, and **Find** (look for this device on every bus);
      - hat and INA219 status;
      - a DPI box that **asks** whether a DPI screen is in use before it shows the commands. The commands name the overlays
        and back up `config.txt` with a timestamp. The box also gives an undo, and the HDMI 720x720 follow-up.
    - *Inputs:* a **Turn adjusts** select per knob, Swap, **Listen**, action chips dragged to reorder, the file key under each
      line, and what Core really reads.
    - *Outputs:* a test hint and a polarity warning.
    - **Config** stays the text view, with Check, Fix, a diff, stale merge and history.
11. **Touch UI.** A warning chip on the camera screen is part of T40, not optional. It shows when a module is in error, a
    restart is pending or the file has errors. It names the WebUI address from `DeviceInfoBridge.ipAddress`. The full card and
    the gyro page through Core stay optional (T45).
12. **Measure first** (§8, all read-only as `pi`). v1's seesaw ID loop is removed: interleaved with Core's polling it can fire
    phantom knob turns (`CC H1`, PROBABLE). M2b, M3b and M5b are new.
    - Questions only Patrik can answer: Q1, Q2, Q4, Q7, Q16, Q17.
    - **Minimum path:** T36-T40 give his fix done by software, status on both screens, and a file nothing overwrites. T41-T45
      are the editor and its extras.

---

## 1. How the system works today

### 1.1 Where things are (operator)

| Surface | What you get today | Cite |
| --- | --- | --- |
| `~/apertar-hardware.conf` over ssh | Everything. About 19 sections, aliases, comments. No check: an unknown action is a silent button; a bad bus is a silent device | `R2 §1.4`; unknown action logged only at press, `App:9147` CONFIRMED |
| WebUI Settings → **Config** | One raw textarea. Reload and Save. Save keeps one `.bak`, then writes `.tmp` and renames. It checks only "not empty, ≤ 256 KiB, no NUL". It reloads nothing: "may need ApertarCore or the UI restarted" | `Web:3840-3872`, `App:5463-5526`, `App:66` CONFIRMED |
| WebUI Record → Gyro | IMU driver, orientation, sync, level, calibration, through Core commands that rewrite single keys. **One write per tap** of the sync-offset buttons; "set level" is 5 writes, "clear level" 4 | `Web:11010-11016`; `HW/Mpu6050RecordingSession.cpp:1335-1368`, `:1370-1380` CONFIRMED |
| Touch UI | Nothing for buttons, knobs, buses or the hat. The INA219 card says "Check /home/pi/apertar-hardware.conf and INA219 wiring". The gyro page writes the file itself, one write per ±1 tap | `UI:qml/SettingsPage.qml:4526`, `:3713-3720`; `UI:src/GyroConfigBridge.cpp:1577` CONFIRMED |
| Journal | The only place a driver error shows, e.g. `NeoRotary4 input: /dev/i2c-1: No such file or directory`, retried every second. The hat's card state too (`hat_card=`) | `HW/NeoRotary4Input.cpp:614-638`; `App:9344` CONFIRMED; `lastError()` read only for trigger and LED at start (`App:7026-7041`) |
| `config.txt` | Patrik's, by hand (house rule). The DPI overlays that take GPIO 0-27 live there | `SRC §3.2`; rule `R4 R2` |

### 1.2 Operator view: five walkthroughs

**A. The NeoRotary fix (2026-10-23), today and after T40**

| Step | Today (`SRC §4`, `HL` 2026-10-23) | After T40 |
| --- | --- | --- |
| Symptom | Knobs dead; nothing on screen | Touch screen: an amber chip "Controls: NeoRotary 4 not connected. WebUI → Controls · 10.42.0.1:8000". WebUI Controls → I2C devices, NeoRotary row, red: "Bus 1 does not exist on this Pi (buses: 10, 13, 14, 15). GPIO 2/3 are held by the DPI overlays vc4-kms-DPI-4inch, waveshare-4dpi, waveshare-touch-4dpi (config.txt lines 76-78)." The address shown is whatever `DeviceInfoBridge.ipAddress` reports (the hotspot's own address is UNCONFIRMED) |
| Find why | `i2cdetect -l`, `pinctrl get 2,3`, reading the hat schematic (an evening) | The same row's box asks first: "Does this camera use a DPI screen (a panel on the GPIO header)?" **Yes** → "Then bus 1 stays gone. Feed the hat's Qwiic hub 3.3 V and use bus 10 with poll 50 ms (KB SRC §5)", and no commands. **No, HDMI only** → the commands (§4.4) |
| Commands for you | — | `sudo cp …config.txt …config.txt.20261028-211403`, a `sed` that comments out those three overlay names (safe to run twice), `sudo reboot`. Plus the undo, and the after-reboot note about HDMI. Apertar never edits `config.txt` |
| After the reboot | `i2cdetect -y 1` shows `34` and `49` | Bus select now offers 1, 10, 13, 14. **Find** on the NeoRotary row: "bus 1 · 0x49: NeoRotary 4 (seesaw ID 0x87). [Use bus 1 · 0x49]" |
| Point the config at bus 1 | ssh, type `[cfexpress_hat] bus=1`, `[neorotary4] enabled=true bus=1 address=0x49` | Hat row: bus 1 (Find shows it answering). NeoRotary row: On, bus 1. **Review**: "Hat: bus 10 → 1 (answers). NeoRotary 4: on, bus 1 (answers)." **Save** |
| Make it work | Reboot, or restart Core, UI and automounter (Patrik) | Core restarts the NeoRotary driver and the hat watcher in about a second: "Applied 21:14. NeoRotary 4 connected." The file card shows "Still to do: restart the camera (or the automounter) so automount uses bus 1. Until then automount still looks at bus 10. [Restart Camera] or `sudo systemctl restart apertar-cfe-automounter`". It clears itself after the restart |
| Side effect: HDMI became the 720x720 main screen | `[display]` keys by hand, UI restart | The DPI box's after-reboot note: "The touch UI moves to HDMI at 720x720. In Config set `[display] hdmi_external_only=true` (as before), or `ui_width=1920 ui_height=1080 ui_layout=landscape_large`, then restart the UI (SRC §4.5)", with a link that opens Config at `[display]` |

**B. Remap knob 4's press to zebra, and give knob 2 to shutter (planned T05, `TUT:81`)**

| | Today | After T41-T42 |
| --- | --- | --- |
| Which knob is which | Count on the board | Inputs → NeoRotary 4 → **Listen**, turn the knob: its row lights for 2 s |
| Knob 2 = shutter | `encoder1_cw=shutter_up`, `encoder1_ccw=shutter_down` over ssh | Knob 2 → **Turn adjusts: Shutter** (one select; it writes the up/down pair). **Swap** flips the direction of that knob only |
| Press = zebra | `encoder3_press=zebra`. A typo (`zebrra`) is silent until you press, then a journal line | Press: dropdown "Monitoring › Zebra on / off". Typed in the pencil field, `zebrra` is red: "Unknown action 'zebrra'. Did you mean zebra?" |
| Review | — | "Knob 2 turn: ISO → Shutter. Knob 4 press: Resolution → Zebra." The INI diff sits under "Show file diff" |
| Apply | Core restart (Patrik) | Save. "Applied 21:14 in 0.4 s. NeoRotary 4 connected." |

**C. A hand edit over ssh while the WebUI page is open**

| | Today | After T39 |
| --- | --- | --- |
| Patrik types `d6=standby` under `[gpio_buttons]` in nano, to try later | — | After two equal stats, 1 s apart, the journal says `ApertarCore controls: ~/apertar-hardware.conf changed outside Apertar (h4b1…): [gpio_buttons] changed; 0 errors; not applied`. Banner on both panels: "[gpio_buttons] changed outside Apertar at 21:14. Not applied. [Apply] [Show changes]" |
| Meanwhile the phone saves a knob | Config textarea: Save overwrites the ssh edit; the `.bak` keeps one copy (`R3 §4.1` hazard 1) | The knob save restarts only the NeoRotary driver: merged, saved, applied. The `d6` edit stays unapplied, and the banner stays |
| The phone saves a GPIO button too | lost update | The dry run says "This save also applies the change made outside Apertar at 21:14: `+d6=standby`". The button reads **Save and apply both** (`adopt_outside=true`) |
| The page saves the same key | lost update | Refused: "gpio_buttons.d6 changed since you loaded it: you saw eject, the file now says standby (outside Apertar, 21:14). [Keep mine] [Take the file's]". The other draft changes are kept |
| The touch UI's gyro page changes the orientation (before T45) | — | Not an "outside, not applied" banner: "[mpu6050] changed outside Core at 21:16 (probably the touch UI's gyro page): applies at the next take." No Apply button |

**D. A save that breaks every GPIO button (`CO P1`)**

| | Today | After T42 |
| --- | --- | --- |
| He adds a button on a pin an overlay holds | The next Core start fails the single all-lines GPIO request; Record (GPIO 10) and Eject (GPIO 6) die with it, silently (`HW/GpioInput.cpp:554-576`, `:642-649`) | The validator warns first if it knows the pin (I2C, DPI, UART 14/15 advisory, kernel consumers from M5). If the kernel refuses anyway, the after-save check turns Card 1 red: "Pi GPIO buttons stopped: /dev/gpiochip0 request failed: Device or resource busy. Record (GPIO 10) and Eject (GPIO 6) do nothing now. [Undo last save]". The touch chip says "GPIO buttons off" |

**E. First start after the update (`CO W1`, `P12`)**

| | After T37-T38 |
| --- | --- |
| Core starts | The file is validated at once. One journal line (`ApertarCore controls: ~/apertar-hardware.conf h…: 0 errors, 2 warnings (INA219 bus 4 missing; …); adopted, nothing changed`), and `controls_errors`/`controls_warnings` in state. The file as found is pinned in history as "Before Controls" and never pruned |
| A WebUI tab from before the update saves Config | `POST /api/config` has an `Origin` but no `X-Apertar-Revision` → 409: "Apertar was updated: reload this page. Your text stays in the box." Scripts without an `Origin` keep working |
| He taps the gyro sync offset | The store writes the one key. No header comment, no `.bak` rotation. History coalesces taps within 10 minutes into one entry |
| He opens Controls the first time | A sheet: "Apertar checked your file. Nothing was changed. 1 device is on but cannot answer: INA219 (bus 4 does not exist). [Turn it off] [Keep]". Absent hardware is mentioned only when it is enabled or answers somewhere |

### 1.3 Code view

**Read path.** Each reader builds the candidate list `$APERTAR_HARDWARE_CONFIG` → `/home/pi/…` → `/boot/firmware/…` →
`/boot/…` (`App:4293-4311` CONFIRMED). Two rules decide which file it takes (`R2 §1.1`; CONFIRMED for the hat at
`App:4552-4598`, which returns after the first existing file, and for NeoRotary4 at `HW/NeoRotary4Input.cpp:355-444`):

- the first file that exists, for INA219, the hat, trigger, LED, IMU, the Python helper and the automounter;
- the first file that has the section, for GPIO, PCF8574, NeoRotary4 and Grove.

**How each reader ends a value (v2; this is the fact v1 got wrong in the sketch, `CC D1`):**

| Reader | Rule | Cite (CONFIRMED) |
| --- | --- | --- |
| GPIO, PCF8574, NeoRotary4, Grove | the whole line is cut at the first `#` or `;` | `HW/GpioInput.cpp:399-401`, `HW/Pcf8574Input.cpp:338`, `HW/NeoRotary4Input.cpp:375-377`, `HW/GroveAnalogInput.cpp:268` |
| Trigger, tally | only a `#` or `;` at the start or after whitespace; `events` then splits on `,` `;` `\|` `+` | `HW/TriggerOutput.cpp:56-66`, `:152-156`; `HW/RecordingIndicatorOutput.cpp:53-63` |
| IMU | first `#` or `;` anywhere (critic said "after whitespace": not so) | `HW/Mpu6050RecordingSession.cpp:209-221` |
| Core's hat and INA219 readers | integers: none (`bus=1 # x` fails → default); `enabled=`: first mark; a header must end in `]` | `App:4448-4467`, `App:4469-4482`, `App:4512`, `App:4568` |
| Core's Python helper (each eject) | `configparser`: no inline comments; `int()` failure → default; duplicate, junk or key-above-section raise past `except OSError` | `App:3445-3496` |
| Automounter (root) | first `#` or `;`, then strips `"…"` | `UI:src/CfeAutomounter.cpp:66-77` |
| `[run_script]` | a quoted path ends at its quote; else the first `#` or `;` | `HW/HardwareScriptRunner.cpp:70-79` |

So `bus=1  # x` under `[cfexpress_hat]` means bus 10 for Core's watcher and Python helper, and bus 1 for the automounter.

**Defaults when the file says nothing (v2, `CC D4`):** INA219 is **on, bus 4, even with no `[ina219]` section**
(`App:4281-4285`, loader `App:4492-4545`). A `[pcf8574]`, `[neorotary4]` or `[grove_analog]` header alone turns the device on
(`HW/Pcf8574Input.cpp:348-349`, `HW/NeoRotary4Input.cpp:386-390`, `HW/GroveAnalogInput.cpp:279-280`), default bus 1. The hat
watcher is off without the section and on with it (`App:4568-4571`), default bus 10. The automounter is on by default
(`R3 §1.2`).

| When | Who reads | Cite |
| --- | --- | --- |
| Core start | trigger → PCF8574 → NeoRotary4 → GPIO → (power button) → Grove → LED, then the LED state is re-synced | `App:7026-7044` CONFIRMED |
| First `/api/state` | INA219, once for the process (`static const` in a free function in the anonymous namespace) | `App:4693-4695`; namespace `App:59`-`App:6919` CONFIRMED |
| Media watcher start | the hat (`[cfexpress_hat]`), into a non-copyable `CfeHatReader` | `App:9310-9311`; `src/util/CfeHat.hpp:32-33` CONFIRMED |
| Each eject | Core's embedded Python reinsert helper | `App:3466-3496` CONFIRMED |
| Each use | IMU (each take, each `/api/state`), `[run_script]` (each press, from `editableHardwareConfigPath()`) | `R2 §1.3`; `App:8840-8843` CONFIRMED |
| Process start | UI: `[display]`, `[ina219]`, `[imu]`, `[network]`. Network helper: `[network]`. Automounter (root): `[cfexpress_hat]`, `[storage]` | `R3 §1.2`; `UI:src/CfeAutomounter.cpp:786-802` CONFIRMED |

**Write paths today** (no shared lock, no version):

| Writer | How | Cite |
| --- | --- | --- |
| `POST /api/config` | whole text, `.bak`, `<file>.tmp`, rename, no fsync | `App:5463-5526`, `App:7321-7341` CONFIRMED |
| IMU commands | single key per call, `<file>.tmp` + rename; on a failed rename it **removes the real file** and renames again. It writes `config.configPath`, which can be a `/boot` copy. Level set = 5 calls, clear = 4 | `HW/Mpu6050RecordingSession.cpp:604-713`, `:700-705`, `:1296-1300`, `:1363-1379` CONFIRMED |
| UI gyro page | single key, `QSaveFile`, one write per tap | `UI:src/GyroConfigBridge.cpp:1577`; `UI:qml/SettingsPage.qml:3713-3720` CONFIRMED |
| UI template writers | the whole template, two different texts, both starting `# Apertar hardware configuration` / `# Primary location: …`, only when `/home/pi/apertar-hardware.conf` is missing; return value unused | `UI:src/DisplayConfigBridge.cpp:41-58`, call `:587`; `UI:src/Ina219Bridge.cpp:69-86`, call `:497` CONFIRMED |

**Action path today.**

1. A driver thread sees a debounced press edge (`HW/GpioInput.cpp:690-710` CONFIRMED) and calls `handleHardwareInputAction`
   (`App:8808-8836` CONFIRMED).
   - That takes `hardwareInputSequenceMutex_`, then loops over the mapping's actions (at most 6, `HW/ButtonActionList.hpp:14`).
   - Duplicate tokens were already dropped silently by the parser (`HW/ButtonActionList.hpp:103-104` CONFIRMED).
   - In standby a press only wakes, and a turn does nothing (`App:8820-8826` CONFIRMED).
2. `handleSingleHardwareInputAction` (`App:8838-9148`) turns each action into socket commands. This is an if-chain:
   - quoted literals (`action == "zebra"`);
   - step families through `pcfSettingStepMode(action, "iso")` (`App:1052-1062`);
   - number families through `parseHardwareActionNumber`;
   - script slots.

   Each goes through `dispatchHardwareInputCommand` (`App:8636-8644`) → `handleCommand`, which takes `commandMutex_` on its
   first line (`App:9485` CONFIRMED).
3. Unknown actions end at `App:9147`.

**Threads and locks the reload must respect (v2, CONFIRMED unless marked):**

| Fact | Cite |
| --- | --- |
| Every input `start()` is `stop(); config_ = loadConfig(); …`. `enabled()` and `configPath()` read `config_` with no lock | `HW/NeoRotary4Input.cpp:310-347`, `HW/GpioInput.cpp:329-365`, same in PCF8574 and Grove |
| Inputs: `std::atomic<bool> running_`; `stop()` is `if (!running_.exchange(false)) return; join()` | `HW/NeoRotary4Input.hpp:66`, `HW/NeoRotary4Input.cpp:331-337` |
| Outputs: `bool running_` under `stateMutex_`; `TriggerOutput::stop()` drives the output inactive; the LED ignores setters while stopped | `HW/TriggerOutput.hpp:85-89`, `HW/TriggerOutput.cpp:429-447`; `HW/RecordingIndicatorOutput.hpp:77-80`, `HW/RecordingIndicatorOutput.cpp:491-499` |
| An input in its retry loop keeps running and sleeps 1 s per try; `lastError_` is cleared only after a good open, never in `start()` | `HW/NeoRotary4Input.cpp:631-640`; `HW/GpioInput.cpp:642-679`; `HW/Pcf8574Input.cpp:483-486`; `HW/GroveAnalogInput.cpp:446-452` |
| Each start: NeoRotary throws away accumulated movement; Grove with `emit_on_start` re-sends every knob position (`set_iso`, `set_fps`, …); PCF8574 writes `0xff` to the chip; the trigger copies the live byte | `HW/NeoRotary4Input.cpp:643-647`; `HW/GroveAnalogInput.cpp:465-469`; `HW/Pcf8574Input.cpp:416`, `:426-430`; `HW/TriggerOutput.cpp:640-644` |
| GPIO asks the kernel for all its lines in one request; one busy line fails the lot | `HW/GpioInput.cpp:554-576` |
| NeoRotary: an enabled board with no actions does not start; an unmapped turn is dropped; an unmapped press never reaches App | `HW/NeoRotary4Input.cpp:317-321`, `:658-665`; `App:8810-8811` |
| The tally learns of a take only through events (`handleTriggerEvent`) | `App:11322-11340` |
| Socket requests set a global "collect events into this reply" flag before `handleCommand`; web commands never do | `App:7201-7237`, `App:11310-11316` |
| The socket server drops a client whose request line reaches 64 KiB, with no reply | `CS:261` |
| `errorReply` writes only `"error"`; the WebUI's `sendCommand` throws with that text and re-renders the camera snapshot | `App:122-130`; `Web:9148-9180` |
| `WebServer` has no reason phrase for 409 (`default: return "OK"`) | `WS:59-73` |
| The camera getters are already called without `commandMutex_` (the web state builder) | `App:7857-7866` |

**What Cinemate does** (from R1, reopened where cited). Cinemate edits one JSONC file, with one row per control: a pin
`<select>` that greys out pins in use, then gesture lines (Press, Single, Double, Triple, Hold), each with a grouped method
dropdown, an argument control and a pencil (`R1 §1.2-1.5`). Its quad rotary row has one **Turn** select per knob
(`Cm:src/module/app/templates/settings_editor.html:3541`, `CO P9`). Its remap confirm is in plain words ("Move … to GPIO 26?
GPIO 7 will be freed up.", `:6915`), and its I2C pane gives "connected since / lost at" (`:7379-7385`). Its save:

1. merge over the file on disk;
2. fill defaults;
3. keep 10 backups;
4. rewrite comments surgically;
5. replace atomically;
6. **restart the whole app** (`R1 §1.13`).

Its only drag and drop reorders value-step chips (`:4893-4901`, CONFIRMED by `CC §3`). The quad rotary is hard-wired to bus 1
and `0x49` (`R1 §0`), so **the part Patrik's fix needs has nothing to port in Cinemate**.

---

## 2. The decision

### 2.1 Facts every design must respect

v1's F1-F23 stand, with three corrections (F9, F13, F23). F24-F40 are new; each one was opened here.

| # | Fact | Label, source |
| --- | --- | --- |
| F1 | One file, about 15 readers in Core, the UI, the network helper and the root automounter, with about 10 hand-copied candidate lists | CONFIRMED `App:4293-4311`; `R3 §4.3` |
| F2 | The **control** sections are read only by Core. The **shared** ones: `ina219` (Core + UI), `imu` and drivers (Core + UI), `cfexpress_hat` and `storage` (Core, Core's Python, automounter), `display` (UI), `network` (UI + helper) | CONFIRMED `R3 §1.2`; spot-checked |
| F3 | The UI writes a full template when `/home/pi/apertar-hardware.conf` is missing, with `[cfexpress_hat] bus=10` and `[neorotary4] enabled=false`. Two different template texts, same first two lines | CONFIRMED `UI:src/DisplayConfigBridge.cpp:41-58`, `:131-135`, `:297-300`; `UI:src/Ina219Bridge.cpp:69-86` |
| F4 | A rename-based writer replaces a symlink with a regular file | PROBABLE (POSIX `rename`) |
| F5 | Read once: the drivers at Core start, INA219 `static const`, the hat at watcher start | CONFIRMED `App:7026-7043`, `:4695`, `:9310` |
| F6 | Every driver's `start()` is `stop()` + `loadConfig()` + a new thread; `stop()` joins the thread | CONFIRMED `HW/NeoRotary4Input.cpp:310-337` |
| F7 | `handleCommand` holds `commandMutex_`; driver callbacks reach `handleCommand`; so a reload run inside a command, or a command that waits for a reload, can deadlock on `join()` | CONFIRMED lines `App:9485`, `:8636-8644`, `:8818-8819`; deadlock PROBABLE |
| F8 | No writer locks or checks a version. The IMU writer removes the live file on a failed rename. Two Core writers share `<file>.tmp` | CONFIRMED `App:5510`, `HW/Mpu6050RecordingSession.cpp:687`, `:700-705` |
| F9 (v2) | Readers disagree on comments: the table in §1.3. Core's Python helper catches only `OSError`, so a duplicate key or section, a junk line or a key above the first section stops it; an unreadable integer silently becomes the default | CONFIRMED (code, `App:3445-3478`); Python behaviour PROBABLE (`configparser` defaults) |
| F10 | Three identical `normalizeSingleAction` copies. Unknown names pass through and are logged only at press | CONFIRMED (sketch test, 355 tokens); `App:9147` |
| F11 | Inputs know only "pressed": one press edge, up to 6 actions, `standby` skipped for turns | CONFIRMED `HW/GpioInput.cpp:690-710`, `HW/ButtonActionList.hpp:14`, `App:8832` |
| F12 | New gesture keys (`d10_hold`, `pin3_double`, `encoder2_hold`) are ignored by today's parsers | CONFIRMED `HW/GpioInput.cpp:209-236`, `HW/Pcf8574Input.cpp:108-138`, `HW/NeoRotary4Input.cpp:424-436` |
| F13 (v2) | Driver state is invisible, and reading it is not free. `lastError()` is mutex-guarded and cleared after a good open, but never in `start()`. `enabled()`/`configPath()` race with `start()`'s `config_ =`. "Running" ≠ "connected" (the retry loop runs) | CONFIRMED `HW/NeoRotary4Input.cpp:339-352`, `:631-640` |
| F14 | Protocol: a flat map of scalar fields; a quoted string may hold `\n`. A bare `null` becomes the text "null". `core.py` turns all-digit values into numbers | CONFIRMED `CP:120-135`, `:180-204`; `core.py:8` |
| F15 | HTTP request ≤ 1 MiB; file ≤ 256 KiB | CONFIRMED `WS:23`, `App:66` |
| F16 | The WebUI has no authentication. `[run_script]` paths run Bash as Core's user | CONFIRMED `R2 §4`; `HW/HardwareScriptRunner.cpp:207-240` |
| F17 | One instance of each driver; each `Config` holds one bus and address | CONFIRMED `App.hpp:121-128` |
| F18 | A seesaw is identified by a register read (HW ID `0x87`), not an ACK. `0x48` (TMP117) answers `0x12` | CONFIRMED `SRC §3.5`; `HW/NeoRotary4Input.cpp:494-514` |
| F19 | DPI overlays hold GPIO 0-27, including 2/3, whether or not a panel is attached; nothing in Apertar writes or reads the overlay lines | CONFIRMED `SRC §3.2`; `R3 §3.3` |
| F20 | Core has the cooperative write primitives: `settingsFile::atomicWrite` (unique temp, mode kept, fsync, rename, dir fsync) and `QtIniLock` (QLockFile-compatible; **gives up after 2 s**, then `operator bool` is false) | CONFIRMED `SF:36-58`, `:59-88` |
| F21 | Core already reads `/boot/firmware/config.txt` read-only (the fan block) | `R4 §2.2 D2` |
| F22 | Every Core file this project touches syntax-checks on the host | CONFIRMED (run here and by `CC §1`) |
| F23 (v2) | An event published while a **socket** command is being handled goes into that command's reply, whatever thread published it, unless `publishEvent` whitelists it. Web commands never collect | CONFIRMED `App:7207-7221`, `:7231-7237`, `:11288-11319` |
| F24 | Each reader has its own comment rule (§1.3 table) | CONFIRMED |
| F25 | Socket request lines are capped at 64 KiB; the client is dropped without a reply | CONFIRMED `CS:261` |
| F26 | A refusal can carry only `"error"`; the WebUI helper drops anything else and re-renders the camera snapshot | CONFIRMED `App:122-130`, `Web:9148-9180` |
| F27 | Every command, read-only ones included, runs under `commandMutex_`, and every hardware button goes through `handleCommand` | CONFIRMED `App:9485`, `:8636-8644` |
| F28 | Outputs keep `running_` as a plain bool under `stateMutex_` | CONFIRMED `HW/TriggerOutput.hpp:89`, `HW/RecordingIndicatorOutput.hpp:80` |
| F29 | Stopping the drivers one after another waits out each one's current 1 s retry sleep (up to about 4 s with bus 1 missing and three I2C inputs enabled) | CONFIRMED (lines in §1.3); the total PROBABLE |
| F30 | IMU multi-key commands are several store writes; the WebUI and the touch UI write once per tap | CONFIRMED §1.1 |
| F31 | A driver restart has side effects: knob movement lost, Grove re-emits, PCF8574 `0xff`, trigger output dropped to inactive | CONFIRMED §1.3 |
| F32 | GPIO is all or nothing: one busy line stops every GPIO button | CONFIRMED `HW/GpioInput.cpp:554-576` |
| F33 | INA219 is on by default on bus 4 even with no section; a section header alone turns PCF8574, NeoRotary4 and Grove on | CONFIRMED §1.3 |
| F34 | Core reads the seesaw in two transactions: select, `usleep(8000)`, read. Foreign traffic in between can make Core read the wrong register, and a large bogus delta fires up to 8 turn actions | CONFIRMED `HW/NeoRotary4Input.cpp:557-584`, `.hpp:56`, `:658-662`; the collision PROBABLE |
| F35 | A DPI overlay creates a connector that reports `connected` with no panel attached | `SRC §4.5` (KB, observed on the rig); whether its `modes` file is empty without a panel: UNCONFIRMED, probably not (the panel timings come from the overlay) |
| F36 | The hat's card state is only in the journal; the INA219's only as missing values | CONFIRMED `App:9344`; grep `hat_card`: journal only |
| F37 | `tutorial.py` runs a curl check only for `SAFE_CORE_CMDS` (`ping`, `help`, `get_state`, `get_media_test_state`, `audio_capabilities`, `list_sensor_modes`) and refuses `/api/config` | CONFIRMED `tutorial.py:48-49`, `:188-193` |
| F38 | The touch UI knows the camera's address: `DeviceInfoBridge.ipAddress`; its camera page has a small warning-chip pattern (`DroppedFrameWarning`) | CONFIRMED `UI:src/DeviceInfoBridge.hpp:16`; `UI:qml/CameraPage.qml:2612-2620` |
| F39 | Core can read a command's output (`runShellCommandCapture`) | CONFIRMED `App:1533` |
| F40 | The WebUI has a **Restart Camera** button (`restart_system` → reboot) | CONFIRMED `Web:3664`, `App:11267-11272` |

### 2.2 Options: where the system-controlled file lives

Unchanged from v1. Both critics agree, and nothing in the critiques changes the counts.

| | **A: keep `~/apertar-hardware.conf`, Core owns writes** | B: split: control sections to `~/.config/apertar-core/controls.conf`, shared ones stay | C: move all to `~/.config/apertar-core/hardware.conf` |
| --- | --- | --- | --- |
| Readers to change | 0 | 6 Core loaders + their candidate lists | about 15 in 2 repos, both Python copies, the root automounter (reinstall: Patrik) |
| Patrik's fix | one file, as it is | two files: the hat's bus in the old one, the NeoRotary's in the new one | moved. The old file must go, and then F3 writes it back with `bus=10` |
| The UI template (F3) | removed in T38 | writes control sections nobody reads into the old file | regenerates the old file, which shadows the new one for readers that were not changed |
| Hand editing | the file he knows | two files | a new file |
| "System-controlled" | Core is the only writer once T38's UI change is built (the touch UI's gyro page writes `[imu]`/drivers until T45) | full for `controls.conf` | full |
| Migration | none: adopted in place, pinned in history | 8 sections moved | everything |
| Risk | low | medium | high |

A symlink from the old path to a new file is rejected too: the renames turn it into a regular file (F4).

### 2.3 Options: applying a change, and the action vocabulary

| Applying | Today: restart Core (Patrik) | v1: reload all six drivers | **v2: reload the changed group, asynchronously** | Cinemate: restart everything |
| --- | --- | --- | --- | --- |
| What runs it | `sudo systemctl restart apertar-core` | the worker, every save | the worker, only for sections that changed, never during a take | `systemd-run … restart` |
| A gyro tap | — | restarts six drivers (`CC A4`) | restarts nothing | restarts the app |
| A knob change | restart | all six restart; GPIO buttons dead up to ~4 s | the NeoRotary restarts; the buttons keep working | restart |
| A hand edit not yet applied | applied at restart | applied by any save, unseen (`CO P2`) | applied only with **Save and apply both** | applied |
| Deadlock risk | none | `set_controls` waiting on the worker (`CC A3`) | none: no handler waits on the worker | n/a |

The vocabulary decision is unchanged: one header (`ButtonActionList.hpp`, `PowerButtonGesture.hpp` and `FramePhaseLock.hpp`
are the pattern). The header unifies names and lists, not behaviour. The dispatcher stays an if-chain, kept honest by a
coverage test (§3.3).

### 2.4 Recommendation

Build **A + reload per group + catalog**, as T36-T45.

| Patrik's request | This design |
| --- | --- |
| "port the gpio dropdown (and method assigning) from Cinemate" | T41: a row per control, a dropdown per gesture, Cinemate's one-select **Turn** for knobs ("Turn adjusts"), argument controls, a pencil field, pins in use greyed. Hold and double press in T44 |
| "in the most Apertar like style" | Pure logic in headers with host tests; flat socket commands; settings cards, pills and selects; `atomicWrite` + `QtIniLock`; driver work on a worker, never inside a command |
| "with the functionality of Apertar api" | Every editor action is a socket command; every action a button runs is the same `handleCommand` the WebUI uses (M1 "one front door", `R4 R8`) |
| "a system controlled config file" | `~/apertar-hardware.conf`, written only through Core's store, validated by each reader's own rules, versioned, with history; the touch UI stops writing it (T38) |
| "the hardware (i2c expanders etc) Apertar is currently using" | §5: PCF8574 (and PCF8574A addresses), NeoRotary 4, Grove ADC, INA219, IMU, CFE hat, GPIO buttons and encoders, tally, trigger, power button |
| "the setting of i2c channels … to make my fix … work" | T40's I2C card: bus by number, Find, probe by ID, the DPI box that asks first, `config.txt` commands for him to run |
| "easy dropdown/drag and drop … and the manual editing for advanced users" | Two panels, one file, one revision, merge rules (§4.3). Drag reorders the actions of one gesture; moving one to another gesture is × then + (`CO` budget note) |

### 2.5 What each measurement would change (details in §8)

| Result | Then |
| --- | --- |
| M1: the live file has aliases, inline comments or duplicates | Expected. T37's validator lists them and nothing is rewritten. A duplicate section blocks easy edits to it until merged (§3.7). A duplicate or junk line already kills the Python reinsert helper at each eject: fix by hand first |
| M1: a `/boot/firmware/apertar-hardware.conf` exists | `get_controls` reports which sections come from it. If `~` is missing, the first save starts from the `/boot` text (§3.4) |
| M2: a unit sets `APERTAR_HARDWARE_CONFIG` | The store writes that path (`editableHardwareConfigPath()`, `App:4313-4318`); readers without the variable keep reading `/home/pi`. Document it in T37 |
| M2b: `pi` cannot read the units' start times | "Still to do" falls back to remembering the change until Core sees the service restart once (§3.6) |
| M3: `/sys/class/i2c-adapter/i2c-N/name` and `device` | The bus labels by number (§4.4). They are UNCONFIRMED until then |
| M3b: what DRM shows for DPI | Only information in the DPI box; the box asks Patrik either way (F35) |
| M4: the hat answers on bus 10 too | Two-masters text shown (JP3/JP4) |
| M5: `gpioinfo` marks GPIO 2/3 or 14/15 used | Pin reservations come from the kernel; otherwise from `/dev/i2c-1`, `config.txt` and the UART lines (M5b) |
| M6: `pi` cannot read the journal | The WebUI status is the only witness; the tutorials' journal checks are Patrik's (`sudo`) |
| M8 (after T39): a reload takes longer than 1.2 s | Something else blocks a stop: the journal's per-stop lines show which |

---

## 3. Data model, file, commands, state

### 3.1 The file

- **Name and place:** `~/apertar-hardware.conf` = `editableHardwareConfigPath()` (env var, else `/home/pi/…`,
  `App:4313-4318` CONFIRMED). The store always writes this path, also for the IMU commands, which today write whichever file
  their loader found (`CC B4`). Core never writes `/boot` copies; it reports them.
- **Core's notes about it:** `~/.config/apertar-core/` (same XDG rule as `camera_settings.conf`, `src/camera/CameraController.cpp:355-366` CONFIRMED):
  - `hardware-history/<YYYYmmdd-HHMMSS>-<revision>-<by>.conf`: the versions before each save.
    - One entry per WebUI save, `core.py` save, Apply or outside change.
    - IMU writes from the same source within 10 minutes share one entry (`CO P3`).
    - 20 kept, plus `adopted-<revision>.conf`, the file as Core found it at its first start after T37. That one is labelled
      "Before Controls" and never pruned.
  - `hardware-state.conf`: `written_revision=`, `written_at=`, `written_by=`, and per section group `changed_at_mono=` with
    `boot_id=` (for the pending restarts, §3.6).
- `~/apertar-hardware.conf.bak` is still written, but only by WebUI and `core.py` saves, so it keeps meaning "before my last
  save" (the toast names it, `R3 §3.1`).
- **Format (what Core writes; it reads everything it reads today):**
  - Sections `[name]` in lower case, canonical spelling (§3.2). A new section goes at its place in the canonical order, above
    the comment block of the next header (sketch check 10, D6).
  - One `key=value` per line, no spaces around `=`, no quotes, canonical key names, booleans `true`/`false`, addresses
    `0x49`, action groups `iso200,fps24`.
  - **Never a comment after a value.** When Core edits a line that has one, the comment moves to its own line above.
  - Never a key above the first section. Never two copies of a key or a section.
  - Comments, blank lines, unknown keys and unknown sections are kept byte for byte. Only edited lines change. CRLF and a
    missing final newline survive (sketch check 3). A text save from a browser textarea arrives as LF; the validator warns
    about CRLF so the diff is no surprise (`CC G3`).
  - On the first **WebUI** save (never on an IMU write) Core adds two comment lines at the top, if absent:
    ```ini
    # Apertar hardware configuration. ApertarCore validates and writes this file: WebUI Settings > Controls,
    # or Settings > Config for the text. Hand edits are kept; put comments on their own lines.
    ```
- **Revision:** `h` + 16 hex digits of FNV-1a 64 of the bytes. The `h` stops `core.py` turning it into a number.
  `h0000000000000000` means "no file" (`CC F2`; sketch: not the empty file's revision).

**Where each thing lives** (for backup and debugging, `CO` Missing 6):

| What | Where | Written by |
| --- | --- | --- |
| Hardware and controls | `~/apertar-hardware.conf` | Core's store; you, over ssh |
| Its versions | `~/.config/apertar-core/hardware-history/` | Core |
| Who wrote it last, what is applied | `~/.config/apertar-core/hardware-state.conf` | Core |
| Camera settings | `~/.config/apertar-core/camera_settings.conf` | Core |
| Operator preferences, T35 value lists | `UI.conf` (touch UI) | touch UI |
| Firmware, overlays, buses | `/boot/firmware/config.txt` | you only |

### 3.2 The schema (one table in `HardwareConfigText.hpp`, `kSections`)

v2 adds three things to each section in the table: the reader's comment rule, the default bus, and whether the section is on
by default. Each row's "Easy" column says whether `set.<section>.<key>` may write it; the others are text mode only.

| Section (aliases read) | Keys easy mode writes (`knownKey`) | Comment rule; default bus; on by default | Easy | After a save |
| --- | --- | --- | --- | --- |
| `[gpio_buttons]` (`gpio`, `grove_digital`, `grove_buttons`) | `enabled`, `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms`, `dN` (BCM 0-63); T44: `dN_hold`, `dN_double`, `hold_ms`, `double_ms` | first mark; —; off | yes | reload group G |
| `[gpio_encoders]` (`grove_encoders`) | `enabled`, `encoderK_a`, `_b`, `_press_gpio`, `_cw`, `_ccw`, `_press`, `_invert`, `_steps_per_event` (K 0-7); T44: `_hold`, `_double`. Timing keys only in `[gpio_buttons]` | first mark; —; off | yes | group G |
| `[pcf8574]` (`pcf8574_buttons`) | `enabled`, `bus`, `address`, `poll_ms`, `debounce_ms`, `active_low`, `pinN` (0-7); T44: `pinN_hold`, `_double` | first mark; 1; **on with the header** | yes | group G (trigger and tally inherit its bus) |
| `[neorotary4]` (`neo_rotary4`, `neo_rotary_4`) | `enabled`, `bus`, `address`, `poll_ms`, `debounce_ms`, `invert_direction`, `reset_on_start`, `max_events_per_poll`, `encoderK_cw`, `_ccw`, `_press` (K 0-3); T44: `_hold`, `_double` | first mark; 1; **on with the header** | yes | group N |
| `[grove_analog]` (`grove_adc`, `analog_controls`) | `enabled`, `bus`, `address`, `poll_ms`, `deadband`, `emit_on_start`, `aN` and its `_min`, `_max`, `_step`, `_deadband`, `_invert`, `_mode`, `_presets`. `channel=` is the **bus** | first mark; 1; **on with the header** | yes | group A |
| `[recording_indicator]` (`rec_indicator`, `record_led`, `recording_led`, `tally_led`) | `enabled`, `target`, `chip`, `line`, `pcf_pin`, `bus`, `address`, `active_high`, `open_drain` | **after a space**; —; off | yes | group G + LED re-sync |
| `[trigger_output]` (`trigger`, `capture_trigger`, `hotshoe`) | the same + `pulse_ms`, `events` | **after a space**; —; off | yes | group G |
| `[cfexpress_hat]` | `enabled`, `bus`, `address` | integers: none; 10; on with the header (Core), on without (automounter) | yes | hat watcher re-made; automounter **restart (Patrik)** |
| `[ina219]` | `enabled`, `bus`, `address` | integers: none; **4; on even without the section** | yes | Core: cache reload; UI: restart |
| `[imu]` + `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`, `[gyro]` | `[imu]`: `enabled`, `driver`; drivers: `enabled`, `bus`, `address`, `orientation`. Calibration keys only through the IMU commands | first mark; auto-probe; on | yes | Core: next use; UI: restart |
| `[storage]` | — | none (Python); — | text | automounter restart |
| `[display]`, `[network]` | — | UI's QSettings | text | UI / helper restart |
| `[run_script]` | — (**not writable from the browser**, Q2) | quotes; — | text | next press |
| `[camera]` (T33, not on the tip) | — | — | text | T33's hook, moved into the store (R10) |

**The controls model** (`ControlsModel.hpp`, built by Core from the parsed text; the WebUI never parses INI):

| Thing | Kinds | Gestures | Resource it claims |
| --- | --- | --- | --- |
| Input | GPIO button; GPIO quadrature encoder; PCF8574 pin; NeoRotary 4 knob (0-3); Grove analog channel (0-7) | button and pin: `press` (+ `hold`, `double` in T44); encoder and knob: `turn` (= `cw` + `ccw`, shown as one "Turn adjusts" select when they are a pair), `cw`, `ccw`, `press`; analog: a target and its range | `gpio:N`; `pcf:<bus>:<addr>:<pin>`; `neo:<bus>:<addr>:<k>`; `grove:<bus>:<addr>:<n>` |
| Output | Tally (`recording_indicator`), Trigger (`trigger_output`), on GPIO or a PCF8574 pin | — | `gpio:N` or `pcf:…` |
| Device | the I2C devices of §5 | — | `i2c:<bus>:<addr>` |
| Fixed | Pi 5 power button: press = shutdown card, double = standby, any press in standby = wake | — | read-only row (`HW/PowerButtonGesture.hpp:6-39`) |
| Reserved | GPIO 2/3 while `/dev/i2c-1` exists; GPIO 0-27 under an active DPI overlay; GPIO 0/1 (HAT ID EEPROM, advisory); **GPIO 14/15 (UART, advisory; a hard reservation when `enable_uart` or a UART overlay is on, M5b)**; lines another consumer holds (`gpioinfo`, M5) | — | greyed in every picker with the reason |

Every row and every line carries:

- `key` and `line`, the file key and its line number, shown under the gesture in small mono (`encoder3_press · line 31`);
- `value`, what the file says;
- `effective`, what Core's reader uses (`effectiveValue`). It differs when the reader cannot read the line: `bus=1 # x` under
  `[cfexpress_hat]` has value `1` and effective `10 (default)`. The row shows it in red (`CO P11`; sketch check 10);
- `issues`, the validator's issues for that section and key (v2: `Issue` carries `section` and `key`).

A section that appears twice is **locked** in the easy view: "Merge the two [neorotary4] copies in Config first (lines 14 and
16)", with a jump (`CC D2`, `CO P11`).

**An action value** is what the file holds today: a comma list of up to 6 tokens, each a catalog name (`iso_up`) or a
parameterised token (`iso800`, `fps24`, `wb5600`, `shutter180`, `shutter1/48`, `shutter2s`, `ev-1`, `resolution3840x2160`,
`run_script2`). No new grammar.

### 3.3 The vocabulary (`src/hardware/ActionCatalog.hpp`, T36)

One table, `kSpecs[]` (52 entries), plus three lists that today live in more than one place:

| In the header | Replaces | Host test (sketch) |
| --- | --- | --- |
| `canonicalAction(token)` | the three `normalizeSingleAction` copies (`HW/GpioInput.cpp:108-202`, `HW/Pcf8574Input.cpp:140-242`, `HW/NeoRotary4Input.cpp:121-215`) | identical on 355 tokens |
| `canonicalAnalogTarget(token)`, `kAnalogTargets` | `App:8588-8610` and `HW/GroveAnalogInput.cpp:125-145` | identical to Grove's on 44 tokens; to App's except `none`/`off`/`disabled`, which App never receives (Grove maps them to no target first) |
| `canonicalTriggerEvent(token)`, `kTriggerEvents` (id, label, aliases) | `HW/TriggerOutput.cpp:130-150` | identical on 51 tokens |
| `isOutputAction` (already in `ButtonActionList.hpp:57-61`) | `HW/RecordingIndicatorOutput.cpp:118-129` (`isRecordingIndicatorAction` calls it) | — |
| `suffixAfter`, `numberAfter` | `App:1374-1402` + `parseDoubleValue` `App:914-929` | identical on 20 tokens × 4 prefix sets, except `inf`/`nan`, which the header refuses (App's `std::stod` accepts them). Out-of-range is refused by both |
| `classify(token)` → `{known, id, value, note}` | nothing: unknown names are found only at press | 13 cases |
| `isStepping(id)`, `warnOnTurn(id)` | — | the `_up`/`_down` families step; `capture`, `record_toggle`, `photo`, `timelapse`, `still_mode`, `eject` warn on a turn |
| `catalogJson()` | — | `stepping`, `analog_targets`, `trigger_events` present |

**Dispatcher coverage test (v2, `CC E1`).** It reads `App`, finds `handleSingleHardwareInputAction`, and checks two things:

- every `kSpecs` id has a branch there: a quoted literal, a `pcfSettingStepMode(action, "<family>")`, a number family, or the
  script slot;
- every `action == "x"` literal there is a catalog id.

Today: passes (sketch check 11). A catalog entry without a branch would be "known" to the validator yet ignored at press, and
the test fails until both exist.

`list_actions` reply. Core adds the value lists from the functions the cycles already use (`App:1174-1353`, so T35's value
lists flow through).

```json
{"ok":true,"actions":[{"id":"iso_up","group":"ISO","label":"ISO up","button":true,"rotation":true,"ui":false,"stepping":true},
  {"id":"capture","group":"Record","label":"Record or photo (main button)","button":true,"rotation":true,"ui":false,"stepping":false}, …],
 "values":{"iso":[100,…,51200],"shutter_angle":[11.25,…,360],"shutter_speed":[24,…,1000],"wb":[2500,…,8000],
           "fps":[25,33,50],"resolution":["3840x2160","1920x1080"]},
 "values_for":"IMX585 · 3840x2160 · Clear HDR off",
 "gestures":{"button":["press"],"encoder":["turn","cw","ccw","press"],"analog":["target"]},
 "analog_targets":["iso","fps",…],"trigger_events":[{"id":"recording_start","label":"Record start"},…],
 "max_per_mapping":6}
```

- `fps` and `resolution` depend on the sensor mode (`App:1098-1286`). The page labels them "for the current mode" and fetches
  `list_actions` again when `/api/state`'s sensor, resolution or Clear HDR changes (`CC E3`).
- T44 adds `"hold","double"` to `gestures`.
- A new action is **one catalog line and one dispatcher branch** (Q10).

### 3.4 Who writes, how, and what happens to hand edits

**One writer: `HardwareConfigStore`**, reached as `apertar::hardware::configStore()`. It is a function-local static in
`src/hardware/HardwareConfigStore.cpp`, so App and the IMU code share it (`CC B4`).

| Step | What | Why |
| --- | --- | --- |
| 1 | `std::mutex` in the store, then `settingsFile::QtIniLock(path)`. If the lock is not taken within its 2 s, refuse: "Another program is writing the file; try again." | in-process writers serialise; the touch UI can join with `QLockFile` (T45). `CC F3` |
| 2 | Read the current text; compute its revision. **Stable-file check**: if the revision is not one Core wrote, and the mtime is less than 1 s old, or two stats 100 ms apart differ in size, mtime or inode, refuse: "The file is being written (an editor is saving it); try again in a second." The WebUI retries once by itself | `nano` rewrites in place; merging into a half-written text then renaming over it would orphan the inode nano is writing (`CC F1`) |
| 3 | Base. Text mode: `base == current`, or (v2) `textToEdits(baseText, text)` gives key edits with no `conflicts`: then merge as easy mode, but only as a `dry_run` the page must confirm ("Merged with the gyro change of 21:16. Review the result.") (Q17). Key edits: `checkEdits` (duplicated section, unknown key, text-only section), then `conflicts(baseText, current, edits)` must be empty. The base text comes from a cache of revisions Core served or wrote, then from the history | §4.3; sketch check 10 |
| 4 | Outside edits: if the save restarts a driver group whose sections differ between the applied text and the current file, refuse unless `adopt_outside=true`. The dry run returns them as `outside_diff` | an unrelated save must not apply a hand edit unseen (`CC A4c`, `CO P2`) |
| 5 | New text = `applyEdits(current, edits)` (or the sent text) | line-preserving |
| 6 | `validate(new, facts)`; refuse if `newErrors(validate(current), validate(new))` is not empty. Issue ids are `rule|section|key|detail`, never line numbers (`CC D3`). With `adopt_outside`, errors in the adopted lines also need `force=true` | old errors do not lock the editor out |
| 7 | `[run_script]` paths unchanged, or refuse (Q2) | F16 |
| 8 | History entry (coalescing IMU writes), `.bak` only for WebUI / `core.py` saves | `CO P3` |
| 9 | Record `expected_revision = revision(new)` under the store mutex, **then** `settingsFile::atomicWrite(path, new)` | the worker classifies under the same mutex, so it never calls Core's own write "outside" (`CC A7`) |
| 10 | Write `hardware-state.conf`; release the lock; queue the reload of the changed groups; return revision, diff, issues, `apply` | no command waits for the worker (`CC A3`) |

The IMU code calls the store's key-edit path (`by: imu`). Each command makes **one** call:

- level set: 5 keys;
- level clear: 4 keys;
- calibration: 3 bias keys.

That removes the shared `.tmp` name and the remove-then-rename (F8).

`POST /api/config` goes through the store too, with the base from `X-Apertar-Revision` (`WS:96-111` lower-cases header names:
read `x-apertar-revision`).

- **A POST with an `Origin` header but no revision gets 409**: "Apertar was updated: reload this page. Your text stays in the
  box." That is an old tab (`CO P12`). `allowedBrowserOrigin` already tells browsers from native clients (`WS:156-170`).
- A POST with no `Origin` (a script) keeps today's last-writer-wins.

**Hand edits over ssh.**

1. Nothing applies by itself (Q3). A half-saved `nano` buffer is never applied.
2. The controls worker (§3.6) stats the file every 2 s.
   - The stat key is size, mtime, inode and ctime: a rename changes the inode (`CC A7`).
   - A new revision Core did not write is announced only after two equal stats (`CO 16d`):
     - the journal gets one line, with one more line per issue;
     - `controls` is published with `by:"outside"` and the changed sections;
     - state gets `controls_outside` (true only if a **reload section** changed) and `controls_outside_sections`.
3. The banner names the sections and when each one takes effect:
   - "[gpio_buttons] changed outside Apertar at 21:14. Not applied. [Apply] [Show changes]";
   - "[mpu6050] changed outside Core at 21:16 (probably the touch UI's gyro page): applies at the next take."
     No Apply button for sections read on use.
4. **Apply** (`apply_controls base=<rev>`) reloads the changed groups. With errors in them, Apply needs `force=true` and says
   which lines Core will skip. Core's next start applies everything, as today.

**Migration: adoption in place.**

- **At every Core start** the file is validated:
  - one journal summary line;
  - `controls_errors` and `controls_warnings` in state, so the touch chip can say so (`CO P12`).
- At the first start after T37, the file as found is copied to `hardware-history/adopted-<rev>.conf`.
- The first WebUI save writes the changed keys plus the 2-line header.
- Alias spellings stay until that key is edited; then that line is written canonical (sketch check 4: `gpio10=capture` in
  `[gpio]` becomes `d10=record_toggle` in place, with no second `[gpio_buttons]`).
- `/boot` copies are reported and never written.
  - If a section is missing in `~/…` and present in `/boot/…`, the four section-scanning readers take it from `/boot`, and the
    model says so.
  - **If `~/apertar-hardware.conf` does not exist but a `/boot` copy does, the first save starts from the `/boot` text and
    shows the diff** (`CC F2`). A save from an empty template would shadow every `/boot` section for the seven
    first-existing-file readers.

**Replaced by a default (v2, `CO P4`).** At start and on every stat, Card 1 turns red when the history holds a later
Core-written version and either:

- the file is missing or empty, or
- it lacks Core's header line while the version Core last wrote had it.

The card says "This file was replaced (it now starts like the touch UI's default: hat on bus 10, NeoRotary off). Your last
saved version is from 21:14. [Restore it]". The template text is recognised by the UI's first two lines (F3). Restore =
`set_controls text=<that version> base=<current>`, shown as a diff first. After T38's UI change is built this should never
fire; it is the net for `mv` instead of `cp`, an old UI binary, or a test.

**How the other processes keep working.** Same path, same syntax. Core's writer obeys every rule the strictest reader needs
(§1.3). The rename is atomic and the file is never absent. The owner stays `pi` and the mode is kept (`SF:44-46`). Patrik's
`[cfexpress_hat] bus=1` and `[neorotary4] enabled=true bus=1 address=0x49` are never touched unless he edits them.

### 3.5 Commands

| Command | Fields | OK reply | Refused |
| --- | --- | --- | --- |
| `get_controls` | `base` (optional: also the diff `base → current`) | `"controls":{revision, path, display_path, exists, modified_text, written_by, written_at, outside, outside_sections[], text, issues[], model{…}, system{…}, status[], applied{group:revision}, pending[], first_open}` | never |
| `set_controls` | `base` (required; `h000…` for "no file") and either `text` or any number of `set.<section>.<key>=<value>` / `unset.<section>.<key>=true` / `unset.<section>=true`; `dry_run=true`; `adopt_outside=true`; `force=true` | `revision`, `diff`, `summary[]` (plain words, §4.1), `issues[]`, `apply:{core:"queued"\|"none", groups[], restart:[{who, why, consequence, command}]}`. With `dry_run`: the same, plus `text`, `conflicts[]`, `outside_diff`, `merged:true` when a stale text was merged; nothing written | §3.7 |
| `apply_controls` | `base` (the revision you saw), `force=true` | `apply:{…}`; "Nothing to apply: Core already runs h…." | in a take (queued instead, see §3.6); `base` ≠ current ("Reload first"); errors without `force` |
| `list_actions` | none | §3.3 | never |
| `scan_i2c` | `bus`; `all=true` sweeps 0x08-0x77 | `"scan":{bus, exists, label, found:[{address, device, name, id, answer, use:[types]}], busy:[{address, reason}], hint}` | in a take; `all` on a camera bus; a bus that does not exist → ok with `exists:false` and the reason |
| `probe_device` | `type`, `bus`, `address` | `"probe":{found, id, name, detail, source:"driver"\|"bus"}` | in a take; unknown type |
| `find_device` (v2) | `type` | `"find":{hits:[{bus, address, id}], looked:[{bus, addresses}]}`: the type's addresses on every existing bus (camera buses: known addresses only) | in a take |
| `controls_history` (T43) | none | `[{revision, at, by, summary}]` | never |
| `help` | | lists the new names (`App:9633`) | |

**Before the lock (v2, `CC C3`).** `list_actions`, `get_controls`, `controls_history`, `scan_i2c`, `probe_device` and
`find_device` are handled at the top of `handleRequest` (`App:7201`) and `handleWebCommand` (`App:7231`), before
`handleCommand` takes `commandMutex_`.

- They read the camera only through getters the web state builder already calls without that lock (`App:7857-7866`).
- Scans and probes take their own `i2cMutex_` (one at a time), and check the recording gate before each address. A take
  started mid-scan stops the scan.
- `set_controls` and `apply_controls` stay inside `handleCommand`; they only queue work.

**Replies (v2).**

- Refusals use `errorReplyBody(id, message, body)`, a sibling of `errorReply` (`App:122`), so a refusal can carry `issues`,
  `conflicts` and `outside_diff` (`CC C2`).
- The panels use their own `controlsCommand(payload)` fetch, which returns the whole JSON and never touches `state.snapshot`.
- The socket line limit becomes `constexpr size_t kMaxRequestLineBytes = 1024 * 1024;` (`CS:261`), so `core.py
  set_controls text=…` works up to the 256 KiB file limit (`CC C1`).
- `parseEdits` refuses the value `null` (`CP:192-204`; sketch).

Example (T39), from the shell (`text@=` reads a file, a T37 addition to `core.py`):

```bash
python3 -I ~/apertar-kb/working/tools/core.py set_controls base=h3f0c2a91d4e75b18 set.neorotary4.encoder3_press=zebra dry_run=true
python3 -I ~/apertar-kb/working/tools/core.py set_controls base=h3f0c2a91d4e75b18 text@=/home/pi/apertar-hardware.conf dry_run=true
```

**State fields.** Three JSON writers carry state: `buildWebStateJson` (`App:7857`), `get_state` (`App:9636`), and the touch
UI's poll.

| Field | Meaning |
| --- | --- |
| `controls_revision` | the file's revision now (stat-cached) |
| `controls_applied` | `{G:"h…", N:"h…", A:"h…", hat:"h…", ina219:"h…"}`: what each group last loaded |
| `controls_outside`, `controls_outside_sections` | reload sections changed outside Core; their names |
| `controls_errors`, `controls_warnings` | counts from the last validation |
| `controls_pending` | `[{who:"automounter", why:"[cfexpress_hat] bus 10 → 1", consequence:"automount still looks at bus 10", command}]` |
| `hardware_status` | from the worker's snapshot only: `[{module:"neorotary4", state:"connected"\|"error"\|"off"\|"no_actions"\|"absent", detail, bus, address, since:"21:14:03"}, …]`, plus `cfexpress_hat` (from the media watcher) and `ina219` (from its last read) |
| `hardware_last_input` | `{source:"neorotary4", index:3, gesture:"press", seq:118}`: the last control that moved, mapped or not (T42, for **Listen**) |

**Event:** `{"event":"controls","revision":"h…","by":"core"|"outside"|"imu","applied":[groups],"status":[…],"changed":[{module,before,after,detail}],"pending":[…]}`.

- It is published after a save, after a reload, on an outside change, and when the status snapshot changes.
- T39 adds it to `publishEvent`'s whitelist, so it is broadcast and never folded into an unrelated socket reply (F23). The
  touch UI polls `get_state` only every 30 s (`UI:src/ApertarControlBridge.cpp:18`), so its chip lives on this event.

### 3.6 Live apply vs restart

**Groups.** A save restarts only the groups whose sections changed between the applied text and the new text (`CC A4b`):

| Group | Sections | Members (stop all, start in boot order) |
| --- | --- | --- |
| G | `gpio_buttons`, `gpio_encoders`, `pcf8574`, `trigger_output`, `recording_indicator` | trigger, PCF8574, GPIO, LED (they share GPIO lines and the PCF chip, so a tally 21 ↔ button 20 swap needs all stopped first) |
| N | `neorotary4` | NeoRotary 4 |
| A | `grove_analog` | Grove ADC (with `emit_on_start`, it re-sends positions: the reply says so) |
| hat | `cfexpress_hat`, `storage` | the media watcher's `CfeHatReader` is re-made: `std::optional<CfeHatReader> hat; hat.emplace(loadCfeHatConfig());` (`CC B2`) |
| ina219 | `ina219` | a file-scope `std::atomic<uint64_t> gHardwareConfigGeneration` in the anonymous namespace; `readIna219Snapshot` reloads its cached config when it changes (`CC B1`) |
| — | `imu` + drivers, `run_script`, `display`, `network`, `camera` | nothing in Core |

**The controls worker** (`ApertarCoreApp::runControlsWorker`, T39) is one thread started with Core. It waits on a condition
variable with a 2 s timeout:

- on a wake, it reloads the queued groups;
- on a timeout, it stats the file and refreshes the status snapshot (publishing `controls` when a module changes).

**Rule: no command handler ever waits on the worker** (F7).

```cpp
// T39: restart the changed hardware groups here, never inside handleCommand (commandMutex_) and never on a driver
// thread (stop() joins it). A button action in flight finishes first. Nothing here waits for a lock it can
// deadlock on: commandMutex_ is taken only for the LED re-sync, after every join.
void ApertarCoreApp::reloadHardwareGroups(std::set<HardwareGroup> groups)
{
    if (recordingGateActive()) {                    // a take, sound, timelapse or still exposure (CC A5)
        deferReloadUntilIdle(std::move(groups));    // the worker retries when the gate clears; the reply said "after the take"
        return;
    }
    const auto started = std::chrono::steady_clock::now();
    const auto before = statusSnapshot();
    if (groups.count(HardwareGroup::G)) {
        pcf8574Input_.requestStop(); gpioInput_.requestStop();          // two phases: every input leaves its 1 s
        recordingIndicatorOutput_.stop(); triggerOutput_.stop();         // retry sleep at the same time (CC A6)
        pcf8574Input_.stop(); gpioInput_.stop();
    }
    if (groups.count(HardwareGroup::N)) { neoRotary4Input_.requestStop(); neoRotary4Input_.stop(); }
    if (groups.count(HardwareGroup::A)) { groveAnalogInput_.requestStop(); groveAnalogInput_.stop(); }
    // start in boot order (App:7026-7043)
    if (groups.count(HardwareGroup::G)) { startLogged(triggerOutput_, "trigger output"); pcf8574Input_.start(); }
    if (groups.count(HardwareGroup::N)) neoRotary4Input_.start();
    if (groups.count(HardwareGroup::G)) gpioInput_.start();
    if (groups.count(HardwareGroup::A)) groveAnalogInput_.start();
    if (groups.count(HardwareGroup::G)) {
        startLogged(recordingIndicatorOutput_, "recording indicator LED");
        std::lock_guard<std::mutex> commandLock(commandMutex_);        // a record_start publishes under this lock (CC A5)
        recordingIndicatorOutput_.setRecordingActive(camera_.isRecording() || soundRecordingActive());
        recordingIndicatorOutput_.setStillExposureActive(camera_.stillExposureStatus().active);
    }
    if (groups.count(HardwareGroup::Hat)) hatGeneration_.fetch_add(1);
    if (groups.count(HardwareGroup::Ina219)) gHardwareConfigGeneration.fetch_add(1);
    const auto after = refreshStatusSnapshot();     // the only place driver config is read: this thread called start()
    markApplied(groups, hardwareConfig().currentRevision());
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count();
    std::cerr << "ApertarCore controls: applied " << groupNames(groups) << " in " << ms << " ms: " << statusLine(after) << "\n";
    publishEvent(controlsEventJson("core", groups, changedModules(before, after)));
}
```

Driver changes this needs (T39):

| Driver | Change | Why |
| --- | --- | --- |
| GPIO, PCF8574, NeoRotary4, Grove | `void requestStop() { running_.store(false); }`; `stop()` becomes `running_.store(false); if (thread_.joinable()) thread_.join();` (today's `exchange` early return would skip the join after a `requestStop`) | two-phase stop: about 1 s worst case instead of about 4 s (`CC A6`) |
| the same | `std::atomic<bool> connected_` set where `setLastError({})` runs after an open, cleared on close; `bool connected() const` | "connected" is not "running" (`CC A2`) |
| the same | `setLastError({})` at the top of `start()` | an Off driver must not keep its old error (`CC A2`) |
| Trigger, LED | `bool running() const { std::lock_guard l(stateMutex_); return running_; }` | `running_` is a plain bool there (F28) |
| NeoRotary4 | start when enabled even with no actions (`HW/NeoRotary4Input.cpp:317-321` becomes a log line, not a return) | status "connected · no actions" and **Listen** work on a fresh board; R22 |

**The status snapshot (`CC A1`).** After each `start()`, the worker, which is the only caller of `start()`, copies per driver:

- `enabled()`, `configPath()`, bus and address (it reads them on its own thread, so no race);
- `connected()`, `lastError()` (locked) and a `since` time.

It refreshes `connected`/`lastError` every 2 s, and that is how a loose Qwiic cable shows ("lost at 21:20: Remote I/O
error", `CO P8.6`). The hat's state comes from the media watcher: `slot != Unknown` with a last-answer time, kept under
`mediaStateMutex_`. INA219's comes from its last read. The state builders and `get_controls` read only this snapshot, under
`mutable std::mutex controlsMutex_` (`CC B3`).

**After-save check (`CO P1`).** The `controls` event carries `changed:[{module, before, after, detail}]`. A module that went
from connected to error makes Card 1 red: it names what that module carries (from the model: "Record (GPIO 10) and Eject
(GPIO 6)") and offers **Undo last save**. The touch chip says it too.

**Restarts for the other processes**, and how "still to do" clears (`CO P6`):

| Section changed | Core | Others (`pending`, in operator words) |
| --- | --- | --- |
| group G, N, A sections | reload (above) | — |
| `ina219` | cache reload | touch UI: "The camera screen's battery card still reads bus 4 until the UI restarts." `sudo systemctl restart apertar-ui-direct` |
| `cfexpress_hat`, `storage` | watcher re-made; the Python helper reads at each eject | automounter: "Automount still looks at bus 10 until it restarts." `sudo systemctl restart apertar-cfe-automounter` |
| `imu` + drivers | next use | touch UI restart (gyro page) |
| `display` | — | touch UI restart |
| `network` | — | `sudo systemctl restart apertar-network`, and the touch UI |
| `run_script` | next press | — |
| `config.txt` (never written) | — | reboot, after Patrik's edit |

Each pending item is derived, not remembered:

- Core stores, per section group, `CLOCK_MONOTONIC` and `boot_id` at the change (`hardware-state.conf`).
- It reads each unit's `ActiveEnterTimestampMonotonic` with `systemctl show -p ActiveEnterTimestampMonotonic --value <unit>`
  (`runShellCommandCapture`, F39; readable as `pi`: M2b).
- The item clears when the unit started after the change, or when `boot_id` changed (a reboot).
- Every item also offers the existing **Restart Camera** (F40), if Patrik agrees (Q16).
- If M2b says `pi` cannot read the units, the item clears when Core itself restarts after a reboot (`boot_id`).

**Recording gate.** These are refused while a take, a sound recording, a timelapse or a still exposure runs:

- `set_controls` (not `dry_run`);
- `scan_i2c`, `probe_device`, `find_device`.

`apply_controls` in a take, and a reload queued before the take began, are **deferred**: the worker runs them when the gate
clears, and the reply says "Saved. Core applies it when the take ends." (`CC A5`). A take that starts during a reload
(microseconds after the gate check) gets its tally from the re-sync under `commandMutex_`. A button pressed in that window
is lost (about 1 s at most, M8).

### 3.7 Refusals, errors, warnings, messages

**Validator rules** (`validate()`; the reader each rule protects is named in the message). "Sketch" = implemented and checked
here.

| Rule | Kind | Example message | Sketch |
| --- | --- | --- | --- |
| Comment after a value where the reader keeps it: `[ina219]`/`[cfexpress_hat]` integers, `[storage]` | error | `Comment after the value on line 3: Core's cfexpress_hat reader then ignores bus=1 and keeps its default. Put the comment on its own line.` | yes |
| Comment after a value elsewhere (each section's own rule, §1.3) | warning | `Comment after the value on line 12: Apertar's readers handle this differently. Put the comment on its own line.` `events=recording_start;still` is no comment (trigger rule); a `;` inside a quoted script path is none either | yes (v2) |
| Text after `]` on a header | error if it is not a `#`/`;` comment, or in `[ina219]`/`[cfexpress_hat]`/`[storage]`; else warning | `Text after ']' on line 9: Core's cfexpress_hat reader does not see this header, so the keys below it do not count.` | yes |
| Junk line; a key above the first section | error | `Line 4 is not a section, a key=value or a comment: the C++ readers skip it, but Core's NVMe reinsert helper (Python) stops on it.` | yes |
| Indented key | warning | `Line 5 is indented: Python's configparser reads it as part of the line above.` | yes |
| Duplicate section, duplicate key | error | `[neorotary4] appears twice (lines 14 and 16): the C++ readers use the later lines and Core's Python helper may stop on it. Merge them.` | yes |
| `bus` not 0-255, `address` not 0x03-0x77 | error | `address=0x80 on line 30 is not a 7-bit I2C address (0x03-0x77).` | yes |
| Unknown section | warning | `Unknown section [neorotory4] on line 21: no reader uses it. Did you mean [neorotary4]?` | yes |
| A device that is on (by its reader's rule) on a bus that does not exist, using the reader's default bus when the file gives none or an unreadable one | warning | `[ina219] has no usable bus=, so Core uses bus 4, which does not exist on this Pi (buses: 1, 10, 13, 14).` / `[ina219] is not in this file, so Core looks on bus 4 (its default), which does not exist …` (+ the DPI line when the bus is 1) | yes (v2) |
| One GPIO line, two owners | error | `GPIO 21 is used by Trigger output (line 7) and Tally (line 20).` | yes |
| GPIO 2/3 while bus 1 exists; GPIO 0-27 under an active DPI overlay | error | `GPIO 2 is the SDA line of I2C bus 1; button d2 cannot use it while the bus exists.` | yes |
| GPIO 14/15 with the UART on (M5b) | error; advisory without the UART | `GPIO 14 is the UART's TX (enable_uart=1 on config.txt line 12). The GPIO request fails, and every GPIO button stops with it.` | spec |
| Unknown action | error | `Unknown action 'isoo_up' on line 11: Core logs it and does nothing. Did you mean iso_up?` | yes |
| 7+ actions; an empty item; a tally token in a group | error | `Line 12: at most six actions are allowed per mapping; Core drops the whole mapping.` | yes |
| The same action twice in one mapping | warning | `'iso_up' appears twice on line 14: Core runs it once.` | yes (v2) |
| `standby` on a turn; actions after `standby` | warning | `standby on a turn (line 15) never fires: Core skips it for rotations.` | yes / spec |
| Record, photo, timelapse, still mode or eject on a turn | warning | `'capture' on a turn (line 16) runs on every detent: one click starts it, the next stops it. Put it on a press.` | yes (v2) |
| Tally shorthand `dN=recindicatorled` | warning | `The tally shorthand on line 13 loses to an enabled [recording_indicator] section and has no polarity key (T17). Use the section.` | yes |
| Trigger or tally targets the PCF8574 but sits above `[pcf8574]` | warning | `[trigger_output] targets the PCF8574 but comes before [pcf8574] (line 30), so it does not inherit its bus and address.` | yes |
| Buttons and an output on one PCF8574 | warning | `[recording_indicator] and the PCF8574 buttons share the chip at bus 1 0x20: each keeps its own copy of the pin byte, so a save or a press can glitch the other's pins (unconfirmed on hardware).` | yes (v2) |
| Open drain with active high on a GPIO output | warning | `Tally has open drain with active high: the line can only pull low, so an LED from the pin to GND never lights.` | yes (v2) |
| `wb` value outside 2500-8000 | warning | `'wb5k' on line 22: Core clamps 5 K to 2500 K.` | yes |
| Two devices on one bus and address; a configured address a known device holds | error / warning | `[neorotary4] address 0x48 on bus 10 is the StarlightEye's TMP117 (it answers 0x12, not 0x87).` | spec |
| GPIO timing keys in `[gpio_encoders]` | warning | `poll_ms in [gpio_encoders] also sets the buttons' poll (the later section wins). Set it in [gpio_buttons].` | spec |
| `[imu] bus=` / `address=` | warning | `[imu] bus is ignored: the IMU reads bus and address from [mpu6050].` | spec |
| No `[cfexpress_hat]` while the automounter runs | warning, only if the hat answers somewhere (Find) | `No [cfexpress_hat]: the automounter polls bus 10 while Core's media watcher is off.` | spec |
| `%` in `[cfexpress_hat]` or `[storage]` | error | `'%' on line 40: Core's NVMe reinsert helper (Python configparser) stops on it. Remove it.` | spec |
| CRLF line ends | warning | `This file has Windows line ends (CRLF). … a save from the Config panel's text box writes plain line ends.` | yes (v2) |
| A section only in a `/boot` copy | warning | `Core reads [neorotary4] from /boot/firmware/apertar-hardware.conf: this file has none.` | spec |
| An alias spelling | none (kept); rewritten canonical only when that key is edited | — | yes |

**Command refusals and replies.**

| When | Kind | Message |
| --- | --- | --- |
| `set_controls` without `base` | refusal | `set_controls needs base: the revision you loaded with get_controls.` |
| text mode, file changed, not mergeable | refusal | `The file changed since you opened it (by the gyro page, 21:16) and your text changes more than values. Your text is kept. Show changes, or load the new file and redo your edit.` |
| text mode, file changed, mergeable | dry-run reply | `Merged with the gyro change of 21:16. Review the result, then Save.` |
| key edit, same key changed | refusal | `gpio_buttons.d6 changed since you loaded it: you saw eject, the file now says standby (outside Apertar, 21:14).` (with `conflicts[]`: the page shows Keep mine / Take the file's) |
| key edit into a duplicated section | refusal | `[gpio_buttons] appears 2 times (lines 1 and 5). Merge the copies in Settings > Config first: the readers use the later lines.` |
| key not in the schema; text-only section | refusal | `'bogus' is not a key of [neorotary4] that Apertar reads. Use Settings > Config for anything else.` / `[display] is edited in Settings > Config (the text view), not key by key.` |
| an unapplied outside edit in a group this save restarts | refusal | `This save would also apply the change made outside Apertar at 21:14 ([gpio_buttons]: +d6=standby). Review it, then Save and apply both.` |
| the file is being written | refusal | `The file is being written (an editor is saving it); try again in a second.` |
| the lock is held | refusal | `Another program is writing the file; try again.` |
| base unknown and the file changed (Core restarted) | refusal | `The file changed since you loaded it and Apertar no longer has that version. Reload.` |
| new errors | refusal | `Not saved: 1 new error. Line 41: GPIO 3 is the SCL line of I2C bus 1; button d3 cannot use it while the bus exists.` (with `issues[]`) |
| in a take | refusal | `Stop recording before saving controls.` / `Stop the timelapse before saving controls.` |
| `[run_script]` paths | refusal | `Script paths run as pi: change [run_script] over ssh, not from the browser.` |
| edit value with `#`, `;`, a newline, or `null` | refusal | `'set.neorotary4.bus': a value cannot hold # ; or a line break.` / `… is null: send unset.neorotary4.bus=true to remove a key.` |
| unknown section in an edit | refusal | `Unknown section in 'set.neorotory4.bus'.` |
| apply with errors | refusal | `The file has 2 errors (lines 12, 40). Core skips those lines; apply anyway with force=true.` |
| old browser tab | HTTP 409 Conflict | `Apertar was updated: reload this page. Your text stays in the box.` |
| saved | reply | `Saved. Core is applying it.` (then the event: `Applied 21:14 in 0.4 s. NeoRotary 4 connected.`) |
| saved in a take (apply only) | reply | `Saved. Core applies it when the take ends.` |
| saved, others need a restart | reply + card | `Still to do: restart the camera (or the automounter) so automount uses bus 1. Until then automount still looks at bus 10.` |
| reload done | journal + event | `ApertarCore controls: applied N in 412 ms: neorotary4 connected (bus 1 0x49), hat bus 1 answering` |
| a module broke | card + chip | `Pi GPIO buttons stopped: /dev/gpiochip0 request failed: Device or resource busy. Record (GPIO 10) and Eject (GPIO 6) do nothing now. [Undo last save]` |
| scan in a take | refusal | `Stop recording before scanning I2C: a scan adds traffic to the bus.` |
| full scan of a camera bus | refusal | `Bus 10 is the camera's control bus: Apertar checks only known addresses there.` |
| an address a kernel driver holds | scan entry | `0x1a: in use by a kernel driver (the camera sensor); not probed.` (`I2C_SLAVE` returns EBUSY; Core never uses `I2C_SLAVE_FORCE`) |
| an address Core's own driver polls | scan entry | `0x49: NeoRotary 4, Core's driver (connected since 21:14); not probed again.` (never touched: F34) |
| wrong seesaw ID | probe | `0x48 on bus 10 answered 0x12, not 0x87: not a NeoRotary 4. 0x48 is the StarlightEye's TMP117.` |

### 3.8 Ways a change could be lost, and why it cannot

| Case | Why it cannot happen |
| --- | --- |
| Easy save overwrites a hand edit to another key | key edits are applied to the **current** file (sketch check 7) |
| Easy save overwrites a hand edit to the same key | per-key conflict check against the loaded revision |
| An unrelated save applies a hand edit unseen (v2) | `adopt_outside` is required, and Review shows it (§3.4 step 4) |
| Text save overwrites anything | refused unless `base == current`, or merged per key after a review (§4.3) |
| A WebUI save and an IMU calibration at the same moment | one store for the process, one mutex and one lock; no shared `.tmp` |
| A save while `nano` writes the file (v2) | the stable-file check refuses (§3.4 step 2) |
| An old browser tab saves the old page's text (v2) | 409 for a header-less browser POST |
| The file is briefly missing and the UI writes its template | `atomicWrite` renames over the path; the IMU remove-then-rename is gone; T38 removes the UI writers; detection + Restore |
| Twenty gyro taps evict every useful version (v2) | IMU writes coalesce into one history entry; the adopted version is never pruned |
| An unknown key, comment or section is dropped | only edited lines change (round trip byte-identical) |
| A pin outside the picker's list vanishes (Cinemate D3) | the page sends only keys it changed |
| An edit lands in the copy of a duplicated section the readers ignore (v2) | key edits into a duplicated section are refused |
| A large text save over the socket vanishes (v2) | the line limit is 1 MiB |
| The touch UI's gyro page and a Core write race (QSaveFile, no lock) | a window of milliseconds remains until T45; R2 |

---

## 4. The WebUI and the touch UI

### 4.1 Controls panel (T40-T42)

A new nav item **Controls** before **Config** (`Web:2773`), panel meta "Buttons, knobs, I2C devices and outputs", icon
`levels.png` or `config.png` (both exist in `src/web/icons/`). It is built only from Core's `get_controls` and `list_actions`.
It uses the classes the page already has: `.settings-card`, `.settings-card-head`, `.online-pill` (`Web:831`), `.pill-grid`
(`Web:749`), `.settings-select` (`Web:1532`), `.settings-field-grid` (`Web:1494`), `.settings-action-row`, `.subtle-note`, a
`.preset-row`-like row (`Web:1887`).

All Controls code lives in one contiguous block of the page script with its own `controls` state object, so merges with
T33-T35 in the same file stay tractable (`CC G2`). Today the page script is 7,616 lines in one raw string (`Web:7-11657`).
T40 ships the extract-and-`node --check` script as a KB tool.

**Card 1: Controls file** (T40). The head pill reads `Saved 21:14 · WebUI` (hash in a tooltip), `Unsaved: 3 changes`,
`Changed outside` or `Applying…`.

- Path, modified time, who wrote it.
- The outside-change banner, per section (§3.4).
- The red "module stopped" banner (§3.6) and the red "replaced by a default" banner (§3.4).
- Buttons: **Review** (a `dry_run`: plain summary, issues, apply plan, diff under "Show file diff"), **Save**, **Discard
  changes** (not "Revert": in Cinemate, Revert loads stock defaults, `Cm …settings_editor.html:1405`, `CO P13`), **Undo last
  save** (T42: the version before the last WebUI save as a text replace, shown as a diff first), and the link **Edit as
  text**.
- "Still to do" items with their consequence, the `sudo` line to copy, and **Restart Camera** (Q16).
- The first-open sheet (§1.2 E): shown once, when `first_open` is true.

**Card 2: I2C devices** (T40, §4.4).

**Card 3: Inputs** (T41), one block per source. The head shows the source, its bus and address, and the state pill with its
time ("Connected since 21:14").

```
NeoRotary 4 · bus 1 · 0x49                                [Connected since 21:14]  [Listen] [Invert all four knobs]
  Knob 1   Turn adjusts [ISO ▾]                                                            [Swap] [Separate]
           encoder0_cw · encoder0_ccw · lines 31-32
           Press       —                                                    [+ action ▾] [✎]
  Knob 4   Turn adjusts [FPS ▾]                                                            [Swap] [Separate]
           Press       [Resolution ×]                                      [+ action ▾] [✎]
           encoder3_press · line 33
Pi GPIO buttons · chip auto · pull up · active low                        [Connected since 21:14]  [Listen]
  [GPIO 10 ▾]  Press  [Record or photo ×]                                  [+ action ▾] [✎] [Remove]
  [GPIO 6 ▾]   Press  [Eject media ×]                                      [+ action ▾] [✎] [Remove]
  [+ Add button]   [+ Add encoder]
  In standby any press only wakes the camera, and turns do nothing.
PCF8574 · bus 10 · 0x20                                   [Off: mappings kept, they apply when it is on]  (dimmed)
Grove analog · not in this file                                                      [+ Add Grove ADC]
Pi 5 power button: press = shutdown card · double press = standby · in standby any press wakes (not configurable)
```

- **Turn adjusts** (`CO P9`, Cinemate's quad **Turn**). A select of the stepping families (ISO, Shutter, WB, FPS,
  Resolution, EV, Other…). It writes the `_up`/`_down` pair to `cw`/`ccw`.
  - **Swap** exchanges the two tokens for that knob only. The board's `invert_direction` is one key for all four knobs
    (`HW/NeoRotary4Input.cpp:417-418`, `:582`), so its pill is labelled "all four knobs".
  - **Separate** shows today's two lines, Turn right and Turn left, each with its own `+ action`. A file whose `cw`/`ccw`
    are not a pair opens separated. Nothing is lost.
- **`+ action`** (`.settings-select` styled as a button): `<optgroup>` per catalog group.
  - On a turn line, stepping actions come first; the rest sit under "Fires on every detent", and Record, photo and eject are
    marked with the warning.
  - An action the line already holds is disabled (Core keeps duplicates once).
  - A parameterised family ("Set ISO") opens a value select fed by `list_actions.values` ("for the current mode"), with a
    custom number field for WB and FPS.
  - A UI action (`zoom_toggle`, `settings`, …) has the note "needs the touch UI running".
  - A seventh action is not offered.
  - Run script N shows its path from the file, or "not set (set it over ssh)" (`CO P9g`).
- **Action chips:** one chip per action, in the order they run (`standby` ends a group, `App:8834`). `×` removes.
  - **Drag** a chip to reorder it within its line; moving one to another gesture is × there and + here (`CO` budget note).
  - Pointer events with `setPointerCapture` and `pointercancel`, a 44 px handle, `touch-action: none`. The tip has no
    pointer-drag code yet (`CC G1`), so T41 brings a 60-line helper, or uses T34's if that has landed (search
    `setPointerCapture`).
  - Keyboard: a focused chip moves with ←/→.
- **Pin picker:** GPIO 0-27, each `GPIO n`.
  - A pin another row, an output or the system holds is `disabled` and labelled `GPIO 21 · Tally`, `GPIO 2 · I2C bus 1 (SDA)`
    or `GPIO 14 · UART (advisory)`.
  - The row's own pin stays selectable, and a pin in the file but not in the list is shown, not dropped.
  - PCF rows show pins 0-7; NeoRotary rows knobs 1-4 (index 0-3 in the file, shown in the key line).
- **✎ (pencil):** the line's raw value as text. On blur a `dry_run` runs, and the line's issues show under it. Empty means
  unset; it never defaults to anything (Cinemate D7).
- **Effective values:** a line whose reader cannot read it shows what Core uses, in red: "Core reads 10 here (comment after
  the value)". A duplicated section is locked (§3.2).
- **Add / Remove:**
  - A new GPIO button takes no pin until one is picked, and **Save is blocked** until it has one or is removed (`CO 16a`).
  - Remove asks once.
  - **Add a device** writes `enabled=false` unless Find or Probe found it, because a header alone turns PCF8574, NeoRotary
    and Grove on (`CO 16g`).
- **Encoders:** A, B and Press pins (three pickers in the same registry), Invert (pills), Steps per event (select 1-8).
- **Analog channel:** target select (`analog_targets`), Min/Max/Step for the targets that use them, Invert pills,
  Preset/Linear for WB.
- **Listen** (T42): while on, the panel polls `hardware_last_input` with the state poll. The row of the control that moved
  lights for 2 s, mapped or not: NeoRotary knobs and pushes, PCF pins, and the GPIO lines that have a row.

**Card 4: Outputs** (T42). Tally and Trigger, each with:

- Off/On pills; Target pills (GPIO / PCF8574); a line picker (same registry) or a PCF pin select;
- Active high pills, with the wiring hint under them: "GPIO → resistor → LED → GND = Active high" (`HL:36-49`);
- Open drain pills, warning with active high (§3.7).

The Trigger adds Pulse (select: 20, 40, 80, 160, 320 ms) and Events pills from `list_actions.trigger_events`. A PCF output
with its own bus or address says so: "on bus 10 · 0x20 (its own setting; the PCF8574 buttons are on bus 1) [Follow the
PCF8574]". Test hint: "To see it work: take a photo (the tally flashes for 320 ms,
`HW/RecordingIndicatorOutput.cpp:522`; the trigger pulses for its `pulse_ms`), or start and stop a take" (`R2 §2.9`; a
`test_output` command is not built, Q23). A `recindicatorled` shorthand in the file shows as a Tally row with [Convert to a
Tally output].

**Review** (T42) leads with plain words, built by Core from the diff and the catalog labels (`summary[]`):

- `Knob 4 press: Resolution → Zebra. GPIO 6 freed.`
- `Hat: bus 10 → 1.` Then, after the page's own `probe_device` calls for every device whose bus, address or `enabled`
  changed: `answers` or `nothing answers at 0x34 on bus 1 (Save is still allowed)`.
- `After saving: Core applies the knobs now. Then restart the automounter (or the camera).`
- `This save also applies the change made outside Apertar at 21:14: …` (with **Save and apply both**).
- Issues, then **Show file diff**.

**Redraw rule** (T34 lesson): rows are rebuilt only after `get_controls` returns, after Save, Discard or Undo, and after a local
edit. The 1 s `/api/state` poll (`Web:11652`) updates only the state pills, the banners, the applied revisions and Listen, so
typing never loses focus. A stale banner appears as soon as `controls_revision` differs from the page's base (`CO P10`).

### 4.2 Config panel (advanced mode, T43)

The existing panel (`Web:3840-3872`) keeps its place and textarea, and gains:

- A **line-number gutter** (a side column scrolled with the textarea).
- **Check:** a `dry_run` that lists the issues with their line numbers. Clicking one selects that line.
- **Fix** buttons on the mechanical rules, each producing a diff to confirm (`CO P11`):
  - a comment after a value moves to its own line;
  - an indented key is unindented;
  - text after `]` moves to its own line;
  - a duplicate key with an equal value is dropped.
- **Save** opens a diff sheet from the `dry_run` reply (Core's diff; red/green lines), then **Save** confirms.
- **Stale text.** The banner shows from the poll, before Save: "Changed by the gyro page at 21:16 since you opened it."
  - On Save Core tries the per-key merge (Q17). "Merged with the gyro change of 21:16. Review the result."
  - If the merge is not possible: "The file changed … [Show changes] [Load the new file]", and your text stays in the box.
- **History:** a select of the versions, including "Before Controls" ("21:14 · WebUI · knob 4 press: Resolution → Zebra").
  **Load** puts that text in the box as a draft; Save as usual.
- The state pill and the banners are shared with Controls.

### 4.3 Two modes, one file

| Rule | Why |
| --- | --- |
| Both panels send `base`, the revision they loaded | Core can tell what changed under them |
| Easy mode sends key edits; Core merges per key | hand edits to other keys survive |
| Text mode sends the whole text. A stale base is merged per key when only values changed (after a review), else refused | a whole text cannot be merged safely when comments or structure changed |
| A same-key conflict keeps every other draft change and shows both values: **Keep mine** / **Take the file's** | `CO P10` |
| Easy → Text with unsaved edits: the box shows Core's `dry_run` text, marked unsaved. Text → Easy is free while the box still equals that text, and the easy draft is kept | nothing is lost when you peek (`CO P10`) |
| Text → Easy with real text edits: "Save or discard the text first" | the easy model is built from the file, not from a draft |
| Both show the same revision pill and banners | one truth |

### 4.4 The I2C devices card (T40)

One row per device type of §5 that is in the file, plus **Add a device** (a select of the types not present). At phone width
the columns stack (`CO 16c`).

| Column | Content |
| --- | --- |
| Device | name + the section (`NeoRotary 4 · [neorotary4]`) |
| On | Off/On pills (`enabled`, or the reader's default with "on because the section exists") |
| Bus | select of the buses that exist, labelled from a Pi 5 table keyed by bus number and checked against `/sys/class/i2c-adapter/i2c-N/device` (the adapter `name` says "Synopsys DesignWare I2C adapter" for both 1 and 10, `SRC:57-61`, `CC H6`): `1 · Pi header (GPIO 2/3)`, `10 · cam0 connector (camera bus)`, `11 · cam1`. HDMI DDC buses (13, 14) are listed but disabled for devices. A configured bus that does not exist stays selected: `4 · missing`. Labels UNCONFIRMED until M3 |
| Address | select of the type's addresses: PCF8574 `0x20`-`0x27`, **PCF8574A `0x38`-`0x3F`** (datasheet, UNCONFIRMED in the KB), INA219 `0x40`-`0x4F`, NeoRotary `0x49` + `0x4A`-`0x4F` (jumper range: Adafruit documentation, UNCONFIRMED), IMU `0x68`/`0x69`, Grove `0x04`/`0x08`, hat `0x34`; + custom hex |
| State | from `hardware_status`, with times: "Connected since 21:14" / "Lost at 21:20: Remote I/O error" / "Wrong device: 0x48 answered 0x12" / "Off: mappings kept" / "On, no actions mapped" / "Not in this file". The hat: "answering, card in" / "no answer since 21:14". INA219: "reading 12.1 V" / "no answer" |
| Probe / Find | **Probe** this bus and address. **Find**: the type's addresses on every existing bus (camera buses: known addresses only); hits carry **Use bus 1 · 0x4A** (`CO P8`) |

**Scan bus** (per bus): known addresses only on camera buses; `all=true` elsewhere.

- It lists answers named from the known-address table (`R4 §1.3`), with **Use for NeoRotary 4** when an ID proves a type.
- **It skips every address one of Core's drivers holds** and lists it as "Core's driver" (F34, `CC H1`).
- Non-seesaw probes use one combined `I2C_RDWR` transfer.

The probes:

| Device | Probe | Proves |
| --- | --- | --- |
| NeoRotary 4 | seesaw `0x00 0x01`, 10 ms, read 1 byte → `0x87`; only when Core's driver is not running it | ATtiny817 seesaw (`HW/NeoRotary4Input.cpp:494-514`) |
| CFE hat | read byte twice, equal | something answers; card bit 0 (`App:4550-4598`, `src/util/CfeHat.hpp:35-46`) |
| INA219 | register `0x00`, 2 bytes | answers (default `0x399F`: UNCONFIRMED in the KB) |
| IMU | WHO_AM_I `0x75` (MPU6050 `0x68`, ICM42688 `0x47`); BMI160/270 chip ID `0x00` | datasheet values, UNCONFIRMED in the KB (`R4` Q5) |
| PCF8574 / PCF8574A, Grove | read 1 byte | ACK only: no ID register |
| TMP117 (known, not used) | register `0x0F`, 2 bytes → `0x0117` | datasheet, UNCONFIRMED in the KB |

**Conflicts the card explains** (from `R4 §2.2`, each with the evidence Core can read as `pi`):

| Condition | Evidence | Card text |
| --- | --- | --- |
| Bus 1 missing, DPI overlay active | no `/dev/i2c-1`; `config.txt` has uncommented DPI overlays under `[all]`/`[pi5]` (`parseConfigTxt`, sketch checks 9-10) | "Bus 1 does not exist. GPIO 2/3 are taken by the DPI overlays vc4-kms-DPI-4inch, waveshare-4dpi, waveshare-touch-4dpi (config.txt lines 76-78)." Then the question below |
| Bus 1 missing, no `i2c_arm` | no `dtparam=i2c_arm` (or `i2c`) set to on, as a comma-list item, under `[all]`/`[pi5]` | "I2C on the header is off. Add `dtparam=i2c_arm=on` under `[all]` in /boot/firmware/config.txt (sudo nano), then reboot." Shown only when no DPI reason applies |
| Any bus missing | `/dev/i2c-N` absent | "Bus 4 does not exist on this Pi (buses: 1, 10, 13, 14). INA219: pick a bus that exists, or turn it off." |
| Wrong seesaw | ID ≠ `0x87` | "0x48 on bus 10 answered 0x12, not 0x87: not a NeoRotary 4. 0x48 is the StarlightEye's TMP117." |
| Dead hub | the hat answers only on bus 10 and nothing at `0x49` on any bus | "Nothing answers at 0x49. The hat's Qwiic hub needs 3.3 V from its 2x3 header or a Qwiic cable; a ribbon-only hat has a dead hub (SRC §3.4)." |
| Two masters | `0x34` on bus 1 **and** bus 10 | "The hat answers on bus 1 and bus 10. If JP3/JP4 are closed the hat joins the header bus and the camera bus. Unconfirmed: the StarlightEye's own controller may answer at 0x34 on bus 10 (KB R4 Q4)." |
| Device on the camera bus | `bus=10` or `11` | "Bus 10 also carries the sensor's per-frame writes: use poll 50 ms or more." |
| Saved, not applied elsewhere | `pending` | "Still to do: restart the camera (or the automounter) …" |

**The DPI box (v2, `CO P7`; `CC D5`).** Apertar cannot tell a real DPI panel from the overlay alone: the connector reports
`connected` without a panel (F35). So the box asks:

> **Does this camera use a DPI screen (a panel on the GPIO header)?**
> DRM says: `card1-DPI-1 connected, 1 mode` (information only; it says the same without a panel).
> **[Yes, a DPI screen]** → "Then bus 1 stays gone: the DPI screen needs GPIO 2/3. Feed the hat's Qwiic hub 3.3 V and use
> bus 10 with poll 50 ms (KB SRC §5)." No commands.
> **[No, HDMI only]** → the commands, which **you** run (Apertar never edits config.txt):

```bash
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.$(date +%Y%m%d-%H%M%S)
sudo sed -i -E 's/^(dtoverlay=(vc4-kms-DPI-4inch|waveshare-4dpi|waveshare-touch-4dpi)([,[:space:]]|$))/#\1/' /boot/firmware/config.txt
sudo reboot
```

- The `sed` is generated from the overlay names Core found (`dpiCommands`), not from line numbers, which shift when the file
  is edited.
- It is safe to run twice. The sketch runs it with GNU sed on a copy, twice: the three overlays are commented and `imx585` is
  kept.
- It also comments a same-name line under another filter such as `[pi4]`; the box says so. The line numbers stay in the text,
  for reading.
- "**To undo:** copy the backup back (`sudo cp /boot/firmware/config.txt.20261028-211403 /boot/firmware/config.txt`), or with
  a card reader remove the `#` on these lines in config.txt on the boot partition."
- "**After the reboot** the touch UI moves to HDMI at 720x720. In Config set `[display] hdmi_external_only=true` (as before),
  or `ui_width=1920 ui_height=1080 ui_layout=landscape_large`, then restart the UI (SRC §4.5)." [Open Config at [display]]

### 4.5 The touch UI's share

**T40, part of the minimum path (`CO P5`).** A small chip on the camera page, in the `DroppedFrameWarning` pattern
(`UI:qml/CameraPage.qml:2612-2620`; a new `ControlsWarning.qml` in both `APERTAR_QML_FILES` and `qml.qrc`, `R3 §2.4`).

- It is visible when an enabled module is in error, a restart is pending, or the file has errors.
- Tap: one line, "NeoRotary 4: bus 1 missing · Fix in the WebUI: http://<DeviceInfoBridge.ipAddress>:8000 → Settings →
  Controls" (F38). The address is the bridge's, not a hard-coded hotspot address.
- `ApertarControlBridge::applyCoreMessage` (`UI:src/ApertarControlBridge.cpp:1196`) handles the `controls` event. `get_state`'s
  `hardware_status` and counts seed it at connect.
- The INA219 card's hint (`UI:qml/SettingsPage.qml:4526`) becomes "Turn it off or pick its bus in WebUI → Controls".

**T45, optional.**

- **A read-only Controls card** in System (`defaultSystemOrder`, `UI:qml/SettingsPage.qml:813`): one line per device from
  `hardware_status`, the outside-change and pending lines, and the WebUI address. No editing on the camera (Q20).
- **The gyro page through Core:** `GyroConfigBridge`'s writes become the existing `set_imu_*` commands (`R3 §2.3`), so Core
  is the only program writing the file. Its `refresh()` runs on the `controls` event.

### 4.6 On set, with all of it built (`CO`)

| Situation | He does | Screens say |
| --- | --- | --- |
| Before the shoot: knob 4 press → zebra | phone, Controls → NeoRotary → Listen, presses knob 4, its row lights; picks Zebra; Review; Save | WebUI: "Applied 21:14. NeoRotary 4 connected." Touch: nothing (all fine) |
| He saved a bad pin | (same) | WebUI red: "Pi GPIO buttons stopped… Record does nothing. [Undo last save]". Touch chip: "GPIO buttons off" |
| An ssh experiment is left unapplied, then a phone save in the same group | Review | "This save also applies the change made outside Apertar at 20:50: d6=standby. [Save and apply both]" |
| Hat bus changed | Save | Card 1 and touch chip: "Restart the camera (or the automounter) so automount uses bus 1. [Restart Camera]". Clears by itself after the restart |
| A fresh camera with a DPI overlay and no panel | Controls → I2C | "Bus 1 does not exist… Does this camera use a DPI screen?" → No → the commands, the undo, the HDMI note |
| File replaced by the UI default | — | WebUI red: "Replaced … [Restore 21:14]". Touch chip points there |

---

## 5. The hardware catalog (device types the editor offers), with Patrik's rig as the example

| Type (section) | Hardware | Bus/address default in code; on by default | Readers | On Patrik's rig (KB) |
| --- | --- | --- | --- | --- |
| `cfexpress_hat` | RPI5-CFE-Hat controller (CH32V003), card presence and eject | 10 / `0x34`; Core: on with the section; automounter: on without | Core watcher, Core Python, automounter (root) | **bus 1**, `0x34` (`HL:25`) |
| `neorotary4` | Adafruit NeoRotary 4 (seesaw ATtiny817, ID `0x87`), 4 knobs + 4 pushes | 1 / `0x49`; on with the section | Core | **on, bus 1, `0x49`**; knobs ISO, shutter, WB, fps (`TUT:81`; exact tokens: M1) |
| `pcf8574` | PCF8574 (`0x20`-`0x27`) or PCF8574A (`0x38`-`0x3F`, UNCONFIRMED) 8-pin I2C expander | 1 / `0x20`; on with the section | Core | **off, no chip**; the image's file had `bus=10 address=0x20` (`HL:39-43`) |
| `grove_analog` | Grove Base HAT ADC (STM32 `0x04` / MM32 `0x08`), 8 channels | 1 / `0x04`; on with the section | Core | not fitted |
| `ina219` | INA219 power monitor | **4** / `0x40`; **on even without the section** | Core, touch UI | **absent: `/dev/i2c-4` does not exist** (`SRC:80`) → Q7 |
| `imu` + driver | MPU6050/6500, BMI160, BMI270, ICM42688-P | 1 / `0x68` (auto-probes `/dev/i2c-0..32`); on | Core, touch UI | `0x68` on **bus 10**; identity PROBABLE (`R4` Q5) |
| `gpio_buttons`, `gpio_encoders` | Pi GPIO (RP1 chip), buttons and quadrature encoders; all lines in one request | chip auto, pull up, active low; off | Core | buttons on **GPIO 10 and 6**, active low (`HL:44`); actions: M1 |
| `recording_indicator` | Tally LED on GPIO or a PCF pin | line −1 (must be set); off | Core | **GPIO 21, active high** (`HL:36-49`) |
| `trigger_output` | Trigger pulse (hot shoe, flash) | GPIO 17, 80 ms; off | Core | **off** (it held GPIO 21 before) |
| (fixed) | Pi 5 power button | evdev `pwr_button` | Core | built in |
| (known, not configurable) | IMX585 `0x1a` (kernel driver, bus 10); TMP117 `0x48` (StarlightEye, not read by Apertar); StarlightEye CH32V003 (address unknown) | — | — | bus 10 |

The task brief named "PCF8574 0x20 on bus 10" for the rig. The KB says no PCF8574 is fitted: `[pcf8574] enabled=false` after it
logged `Remote I/O error` (`HL:39-43`).

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

On this file with the rig's buses (1, 10, 13, 14) the validator finds no errors (sketch check 8). With `[ina219]` left on bus 4
it gives one warning. **Without an `[ina219]` section it warns too**, since the INA219 is on by default (v2). Before the fix
(buses 10, 13, 14, 15; DPI at lines 76-78) it names the missing bus 1, the DPI overlays, and the buttons and the tally on DPI
pins.

---

## 6. Implementation plan, file by file

Order = build order. Line numbers are at `eb9cc39`/`d8098d0`, and **T33-T35 move them**: use the search string. Every search
string below occurs once in its file at the tip (checked here, `search.txt`).

Risk:

- **low** = a host-tested header, or host-checked (`g++ -fsyntax-only`, `node --check` plus a mocked Chromium run, a Qt host
  build);
- **medium** = threads, locks or a large JS block: host-checked, but its behaviour is seen only on the Pi;
- **high**: none.

Nothing in `CameraController.cpp`.

### T36: one vocabulary

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 36.1 | new `src/hardware/ActionCatalog.hpp` | | `kSpecs[]`, `canonicalAction`, `classify`, `suffixAfter`, `numberAfter` (refuses `inf`/`nan`), `suggestion`, `isStepping`, `warnOnTurn`, `canonicalAnalogTarget` + `kAnalogTargets`, `canonicalTriggerEvent` + `kTriggerEvents`, `catalogJson` (sketch, 361 lines) | low |
| 36.2 | KB `working/tools/controls_test.cpp`, `make_old.sh`, `make_old2.sh` | | the sketch's sections 1, 2 and 11 (normalizers, classify, analog targets, trigger events, numbers, dispatcher coverage). Runs against the Pi's tree before 36.3 | low |
| 36.3 | `HW/GpioInput.cpp:108-207`, `HW/Pcf8574Input.cpp:140-247`, `HW/NeoRotary4Input.cpp:121-220` | `std::string normalizeSingleAction(std::string action)` | delete; `normalizeAction` calls `hardware::normalizeButtonMapping(action, hardware::actions::canonicalAction)` | low |
| 36.4 | `HW/GroveAnalogInput.cpp:125-145`; `App:8588-8610` | `std::string normalizeTarget(std::string target)`; `std::string normalizeHardwareAnalogTarget(std::string target)` | both bodies call `actions::canonicalAnalogTarget` | low |
| 36.5 | `HW/TriggerOutput.cpp:130-150` | `std::optional<TriggerOutput::Event> eventFromToken(std::string token)` | maps `actions::canonicalTriggerEvent` to the enum | low |
| 36.6 | `HW/RecordingIndicatorOutput.cpp:118-129` | `bool isRecordingIndicatorAction(const std::string &text)` | `return hardware::isOutputAction(normalizeToken(text));` | low |
| 36.7 | `App:1374-1402` | `std::optional<std::string> hardwareActionSuffix(const std::string &action,` | call the header's `suffixAfter`/`numberAfter` (sketch check 11: same results except `inf`/`nan`) | low |
| 36.8 | `App:9147` | `Hardware input action ignored: unknown action` | add `Did you mean …` from `suggestion()` | low |
| 36.9 | after `App:9612`; `App:9633` | `if (command.name == "list_sensor_modes") {`; `if (command.name == "help")` | `list_actions` (catalog + value lists from `pcfIsoOptions` `App:1311` and its siblings, `values_for`) | low |
| 36.10 | KB `tutorials/tutorial.py:48-49` | `SAFE_CORE_CMDS = {` | add `"list_actions"` (read-only) | low |

### T37: Core owns the file

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 37.1 | new `src/hardware/HardwareConfigText.hpp` | | the sketch: parse with per-section value rules, join, revision (+ absent), schema table, `canonicalKey`, `knownKey`, `checkEdits`, edits, `conflicts`, `textToEdits`, diff, `validate`, `effectiveValue`, `newErrors`, `parseConfigTxt`, `dpiCommands` (sketch, 1,085 lines) | low (78 checks) |
| 37.2 | new `src/hardware/HardwareConfigStore.hpp/.cpp`; `CMakeLists.txt:83-91` | `src/hardware/TriggerOutput.cpp` | `configStore()` (function-local static). `currentText()`, `currentRevision() const` with `mutable` stat cache (size, mtime, inode, ctime) and `mutable std::mutex`. `edit(base, edits, by, flags)`, `replace(base, text, by, flags)`. Stable-file check, lock-timeout refusal, `expected_revision` before the rename, history (20 + adopted, IMU coalescing), `.bak` rule, `hardware-state.conf`, revision cache (8). Uses `SF` `atomicWrite` + `QtIniLock` | low (host test with a temp dir) |
| 37.3 | `HW/Mpu6050RecordingSession.cpp:604-713`, `:715-840`; `:1335-1380`; `:1148` | `bool writeHardwareConfigValue(`; `bool updateImuBiasConfig(`; `bool Mpu6050RecordingSession::setConfiguredLevelReference(std::string *error)`; `if (!updateImuBiasConfig(session.config_.configPath,` | bodies become one `configStore().edit(…, "imu")` call each; level set/clear and calibration as one multi-key edit; the `.tmp` + remove-then-rename code goes; always the editable path | low |
| 37.4 | `App:122-130` | `std::string errorReply(int id, const std::string &message)` | add `errorReplyBody(int id, const std::string &message, const std::string &body)` | low |
| 37.5 | after `App:9612`; help | as 36.9 | `get_controls`, `set_controls` (`text=` only in T37), `dry_run`; recording gate; `[run_script]` gate | low |
| 37.6 | `App:7201`, `App:7231` | `std::string ApertarCoreApp::handleRequest(const std::string &line)`; `std::string ApertarCoreApp::handleWebCommand(const std::string &payload)` | `handleReadOnlyHardwareCommand(command)` before `handleCommand`: `list_actions`, `get_controls` (T40 adds the I2C ones) | low |
| 37.7 | `App:7026-7044` (start) | `syncRecordingTracking(camera_.isRecording());` | validate the file once, log the summary, store the counts; pin the adopted version on the first start | low |
| 37.8 | `App:4333-4446` | `std::string defaultHardwareConfigTemplate()` | header comment, `[neorotary4]` (off), `[gpio_encoders]`, `[grove_analog]`, `[ina219] enabled=false`, `[pcf8574] bus=1`; remove the ignored `[imu] bus/…` keys. The host test validates it | low |
| 37.9 | KB `working/tools/core.py:6-8` | `for arg in sys.argv[2:]:` | `k@=path` sends the file's bytes as a string field (`CC H3`) | low |
| 37.10 | KB `tutorials/tutorial.py` | `SAFE_CORE_CMDS = {` | add `"get_controls"` | low |

### T38: no silent overwrites

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 38.1 | `App:5430-5526` | `std::string buildHardwareConfigFileJson()`; `bool saveHardwareConfigFile(` | both through the store; GET adds `revision` (`h000…` when absent) and starts from the `/boot` text when `~` is missing | low |
| 38.2 | `App:7321-7341` | `if (request.method == "POST" && request.path == "/api/config") {` | read `x-apertar-revision`; `Origin` without it → 409 "Apertar was updated…"; conflict → 409 with the message | low |
| 38.3 | `WS:59-73` | `case 503: return "Service Unavailable";` | add `case 409: return "Conflict";` | low |
| 38.4 | `CS:261` | `if (line.size() >= 64 * 1024)` | `kMaxRequestLineBytes = 1024 * 1024` | low |
| 38.5 | `Web:10372-10401` | `async function saveConfigFile() {` | send `X-Apertar-Revision`; show issues with line numbers; on 409 keep the text | low |
| 38.6 | the store + `get_controls` | | "replaced by a default" detection (§3.4) and `restore` = text replace with diff | low (host test) |
| 38.7 | `UI:src/DisplayConfigBridge.cpp:41-326`, `:587`; `UI:src/Ina219Bridge.cpp:69-342`, `:497` | `bool ensureDefaultHardwareConfigFile()`; `    ensureDefaultHardwareConfigFile();` | delete both writers and both calls (the return value is unused) | low (Qt host build) |

### T39: apply without a restart

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 39.1 | `App.hpp:121-139`, `:187` | `std::mutex commandMutex_;`; `std::thread mediaWatcherThread_;` | `std::thread controlsThread_;`, `mutable std::mutex controlsMutex_;`, `std::condition_variable controlsWake_;`, the queued groups, the deferred flag, `std::map<group, revision> applied_`, the status snapshot, `std::atomic<uint64_t> hatGeneration_`, `std::mutex i2cMutex_` | low |
| 39.2 | after `App:7044`; `App:7058-7066` | `syncRecordingTracking(camera_.isRecording());`; `publishEvent("{\"event\":\"camera_state\",\"state\":\"stopping\"}");` | start the worker after the drivers; stop it first in `stop()` | medium |
| 39.3 | new, after `App:8836` | `void ApertarCoreApp::handleHardwareInputAction(const std::string &action, bool buttonPress)` | `runControlsWorker`, `reloadHardwareGroups` (§3.6), `noticeOutsideChange` (two equal stats), `refreshStatusSnapshot`, `pendingRestarts` (`runShellCommandCapture` + `systemctl show`), `controlsEventJson` | **medium** (threads and order; host syntax-check only) |
| 39.4 | GPIO, PCF8574, NeoRotary4, Grove `.hpp/.cpp` | `if (!running_.exchange(false))`; `setLastError({});` | `requestStop()`; join-always `stop()`; `connected_` atomic; clear `lastError_` in `start()`. NeoRotary4: start without actions (`if (!hasMappedAction(config_.encoders)) {` becomes a log line) | low |
| 39.5 | `HW/TriggerOutput.hpp:89`, `HW/RecordingIndicatorOutput.hpp:80` | `bool running_ = false;` | `bool running() const` under `stateMutex_` | low |
| 39.6 | `App:4693-4695`; namespace scope | `static const Ina219HardwareConfig config = loadIna219HardwareConfig();` | `std::atomic<uint64_t> gHardwareConfigGeneration` at file scope; a mutex-guarded cache reloaded when it changes; the last read's state kept for the status | low |
| 39.7 | `App:9310-9319` | `CfeHatReader hat(hatConfig);`; `const CardPresence slot = hat.cardPresence();` | `std::optional<CfeHatReader>`, re-emplaced when `hatGeneration_` changes; log the new bus; keep "answering since" under `mediaStateMutex_` | medium |
| 39.8 | 37.5's handler | `set_controls` | `set.*`/`unset.*` edits with the per-key merge, `checkEdits`, `adopt_outside`, `apply` + `summary` + `outside_diff` in the reply; `apply_controls` (deferred in a take) | low |
| 39.9 | `App:7857`; the `get_state` body | `std::string ApertarCoreApp::buildWebStateJson() const` | the §3.5 state fields, from the snapshot under `controlsMutex_` | low |
| 39.10 | `App:11301` | `eventJson.find("\"event\":\"media_write_state\"") != std::string::npos \|\|` | whitelist `"event":"controls"` above it (`CC B5`: the `still_exposure` string occurs twice) | low |

### T40: I2C devices, the Controls panel part 1, the touch chip

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 40.1 | new `src/hardware/I2cProbe.hpp/.cpp` | | `listBuses()` (`/dev/i2c-*`, the adapter's `device` link, the Pi 5 label table), `probe(type, bus, address)` (combined `I2C_RDWR`; the seesaw only when its driver is not running), `scan(bus, all, held)`, `find(type, buses, held)`; `I2C_SLAVE` only | low (host compile; behaviour M9) |
| 40.2 | new `src/hardware/SystemFacts.hpp` | | buses + `parseConfigTxt` + DRM connector states (information) + GPIO line info (`GPIO_V2_GET_LINEINFO_IOCTL` on the chip `GpioInput` picks, `HW/GpioInput.cpp:505-537`) + UART lines | low |
| 40.3 | new `src/hardware/ControlsModel.hpp` (devices part) | | `devicesJson(doc, facts, status)`: one entry per device section, effective values, the conflicts of §4.4, `dpiCommands` | low (host test) |
| 40.4 | 37.6's branch | | `scan_i2c`, `probe_device`, `find_device` under `i2cMutex_`, gate per address, skipping driver-held addresses; `get_controls` gains `model.devices`, `system` and `first_open` | low |
| 40.5 | `Web:2773`, `Web:3840`, `Web:4165`, `Web:4240`, `Web:6186` | `data-panel="config" type="button"`; `<section class="settings-panel" data-panel="config">`; `const settingsPanelMeta = {`; `configDirty: false,`; `function setSettingsPanel(panelName) {` | nav item, panel, meta, the `controls` state object, `controlsCommand()`, fetch on open | low |
| 40.6 | same panel | | Card 1 (file, banners, pending with `id="restartSystemButton"`'s action, first-open sheet) + Card 2 (I2C devices, Find/Use, scan sheet, the DPI box) | medium (JS size) |
| 40.7 | KB `working/tools/page_check.sh` | | extract the page script from `Web`, `node --check` it (`CC G2`) | low |
| 40.8 | `UI:qml/CameraPage.qml:2612`; new `UI:qml/ControlsWarning.qml`; `UI:src/ApertarControlBridge.cpp:1196`; `UI:qml/SettingsPage.qml:4526` | `DroppedFrameWarning {`; `void ApertarControlBridge::applyCoreMessage(const QJsonObject &message)`; `? "Check /home/pi/apertar-hardware.conf and INA219 wiring"` | the chip (properties `controlsProblem`, `controlsProblemDetail` on the bridge, from the event and `get_state`), the address from `DeviceInfoBridge.ipAddress`, the INA219 hint | low (Qt host build) |

### T41: the easy editor, inputs

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 41.1 | `ControlsModel.hpp` (inputs) | | `inputsJson(doc, facts)`: rows, gesture lines with key, line, value, effective, issues; turn pairs; occupancy and reservations (UART advisory); locked duplicated sections | low (host test) |
| 41.2 | near `Web:1887` | `.preset-row {` | `.control-row`, `.gesture-line`, `.key-line`, `.action-chip`, `.chip-handle { touch-action: none; min-width: 44px; min-height: 44px; }`, `.action-chip.dragging`, `.control-block.dimmed`; rows wrap at phone width | low |
| 41.3 | the panel | | Card 3: `renderInputRows`, `buildPinPicker` (one registry), `buildActionSelect` (stepping first), `buildTurnSelect`, `swapTurn`, `installChipDrag` (within a line; own helper unless T34's exists), `editsFromDraft`, the pinless-row block | **medium** (≈900 lines of JS; `node --check` + mocked Chromium as T32) |

### T42: Listen, outputs, review, undo

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 42.1 | `HW/NeoRotary4Input.cpp:658`, `:706`; `HW/Pcf8574Input.cpp:518`; `HW/GpioInput.cpp:706` | `const std::string &action = delta > 0`; `emitAction(config_.encoders[encoder].press);`; `emitAction(config_.actions[pin]);`; `if (button.stablePressed)` | a `InputSeen` callback `{source, index, gesture}` called before the "unmapped" checks; App stores it in an atomic `hardware_last_input` | low |
| 42.2 | `ControlsModel.hpp` (outputs, summary) | | `outputsJson`; `summarize(before, after, catalog)` → the plain-words lines | low (host test) |
| 42.3 | the panel | | Card 4 (outputs), Listen, Review (summary, probes of changed devices, apply plan, outside diff), Discard changes, Undo last save, the after-save banner | medium |

### T43: the text editor

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 43.1 | `App` | | `controls_history` (with summaries); `get_controls base=` returns the diff; text-mode merge through `textToEdits`; `fix` edits for the four mechanical rules | low |
| 43.2 | `Web:1562`, `Web:3840-3872`, `Web:10307-10401` | `.config-editor {`; `function updateConfigEditorControls() {` | gutter, Check, Fix, diff sheet, stale banner, merge review, conflict box, history select (with "Before Controls"), shared banners, Easy ↔ Text | medium |
| 43.3 | KB `tutorials/tutorial.py` | `SAFE_CORE_CMDS = {` | add `"controls_history"` | low |

### T44: hold and double press

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 44.1 | new `src/hardware/ButtonGesture.hpp` + KB test | | `update(pressed, nowMs) → {press, hold, double}`. With only `press` mapped: fire on the press edge (today). With `hold` mapped: press fires on release before `hold_ms` (default 800), hold fires once at `hold_ms`. With `double` mapped: press fires `double_ms` (default 350; **per source**) after release if no second press; double fires on the second press edge. Bounce < 80 ms ignored | low (host test) |
| 44.2 | `HW/GpioInput.cpp:706`; `HW/Pcf8574Input.cpp:518`; `HW/NeoRotary4Input.cpp:706` | as 42.1 | per button a `ButtonGesture`, fed every poll; parse `_hold`, `_double`, `hold_ms`, `double_ms` | low (host syntax) |
| 44.3 | catalog, model, Web | | `gestures` in `list_actions`; Hold and Double press lines showing their timings; a **warning** when the Press line holds `capture`, `record_toggle` or `photo`: "Record now starts when you let go (Hold is set)" / "… 0.35 s late (Double press is set)" | low |

### T45: touch UI, optional

| # | File:line | Search string | Change | Risk |
| --- | --- | --- | --- | --- |
| 45.1 | `UI:src/GyroConfigBridge.cpp:1577` and its callers | `bool GyroConfigBridge::writeConfigValue(const QString &sectionName,` | send `set_imu_*` through `ApertarControlBridge`; `refresh()` on the `controls` event | medium |
| 45.2 | `UI:qml/SettingsPage.qml:813` + a new `ControlsStatusCard.qml` (in `APERTAR_QML_FILES` and `qml.qrc`) | `readonly property var defaultSystemOrder: [` | read-only card from `hardware_status` | low (Qt host build) |

### Size (PROBABLE: sketch counts + T32/T34 rates)

| Tutorial | Lines added (removed) | Checked before the Pi |
| --- | --- | --- |
| T36 | ~480 (−340) | all (test + syntax) |
| T37 | ~1,500 (of which ~1,085 the copied header) | all |
| T38 | ~180 (−560 in the UI) | all; Qt host build |
| T39 | ~650 | syntax only for the worker |
| T40 | ~1,500 | Core all; WebUI `node --check` + mock; Qt host build |
| T41 | ~1,100 | same |
| T42 | ~700 | same |
| T43 | ~550 | same |
| T44 | ~550 | all |
| T45 | ~250 | Qt host build |
| **Total** | **~7,450 (−900)** | the WebUI JS and the worker are the parts the Pi must prove |

v1 was ~5,400. The growth is the critics' fixes (~600 in Core) and the operator's additions (~1,450, mostly WebUI). If the budget
must shrink, cut in this order: Fix buttons (T43); Find (keep Probe and Scan); first-open sheet; Listen (T42). The safety parts
(T37-T39) stay whole.

---

## 7. Tutorial outlines (KB format)

Files: `tutorials/inbox/<YYYYMMDDHHMMSS> CINEMATE APERTAR T3x <topic>.md`, frontmatter as in `TIDX` (`datum`,
`kontext: CINEMATE`, `projekt: "#APERTAR"`, `fritext`, `typ: digital anteckning`), ending `#CINEMATE` / `#APERTAR`, a tutor
block above the tags.

Every tutorial: build on the Pi, restart by Patrik, commit on `cinemate-port`, push only when he decides. Undo for all:
`git revert` the commit, and restore `~/apertar-hardware.conf` from `~/.config/apertar-core/hardware-history/` (with `cp`,
never `mv`: §3.4).

### T36. One vocabulary: a header that replaces six copies, and `list_actions` so the WebUI never keeps a seventh

- **Learn:**
  1. why copies drift (M5);
  2. pure logic in a header with a host test that compares against the old code, extracted read-only;
  3. a coverage test that reads the dispatcher;
  4. a socket command that serves data.
- **Risk:** none for the camera: same names, same results; the tests prove it. Core restart. **Time:** 2 h.
- **1 Problem:** add `zebra_toggle` (planned T11, `TUT:87`) and you edit three files. A typo in the file is silent until you
  press.
- **2 How it works:** read `HW/ButtonActionList.hpp:80-119`, `HW/GpioInput.cpp:108-207`, `App:8808-8836`, `App:8838-9148`.
- **3 Find it yourself:**
  - **3.1** `grep -c 'std::string normalizeSingleAction' src/hardware/*.cpp`. Prediction: 1 in each of three files.
    Question: what does an unknown name become? Answer: itself (`:201`), and App ignores it at `:9147`.
  - **3.2** `diff <(sed -n 108,202p src/hardware/GpioInput.cpp) <(sed -n 121,215p src/hardware/NeoRotary4Input.cpp)`.
    Prediction: no differences (checked here and by `CC`).
  - **3.3** `grep -n 'return "focus_peaking_threshold"' src/ApertarCoreApp.cpp src/hardware/GroveAnalogInput.cpp`.
    Prediction: one in each. Question: which one also knows `none`? Answer: Grove's (`:128`).
- **4 Make the change:**

  | Step | What | Check |
  | --- | --- | --- |
  | 4.1 | `ActionCatalog.hpp` (36.1) | `grep -c 'inline std::string canonicalAction'` → 1 |
  | 4.2 | copy the test, run `make_old.sh` and `make_old2.sh`, build, run with the tree path (36.2) | `./controls_test ~/ApertarCore` ends `all ok` |
  | 4.3 | delete the three copies (36.3) | `grep -c normalizeSingleAction src/hardware/NeoRotary4Input.cpp` → 0 |
  | 4.4 | analog targets, trigger events, tally tokens (36.4-36.6) | `grep -c 'canonicalAnalogTarget' src/hardware/GroveAnalogInput.cpp` → 1 |
  | 4.5 | App suffix parsers, suggestion (36.7, 36.8) | `grep -c 'actions::suffixAfter' src/ApertarCoreApp.cpp` → 1 or more |
  | 4.6 | `list_actions` (36.9); host `g++ -fsyntax-only`; `SAFE_CORE_CMDS` (36.10) | `grep -c 'command.name == "list_actions"'` → 1 |

- **5 Build and test:** Pi build, restart (Patrik). `core.py list_actions` lists `iso_up` with `"stepping":true`, and ISO
  values 100 … 51200. Every knob and button works as before (a one-minute walk-through).
- **7 If it went wrong:** a test FAIL line names the token and both results → a missing alias in `kSpecs`. A coverage FAIL
  names the id without a branch.

### T37. Core owns apertar-hardware.conf: one store for the process, each reader's own rules, a validator that names the line

- **Learn:**
  1. why a file several processes read needs one writer, and why "one" means one object in the process (the IMU code is not
     App);
  2. atomic write, lock, revision, stable-file check, and how a lost update happens;
  3. a validator built from what each reader really does, comment rules included.
- **Risk:** a bug in the store could write a wrong file. The host test, the history and `.bak` cover it. The first save shows
  a diff. **Time:** 3 h.
- **1 Problem:** today:
  - four writers, no lock, no version;
  - the IMU writer can delete the file (`HW/Mpu6050RecordingSession.cpp:700-705`);
  - a comment after `bus=1` silently means bus 10 for the hat (`App:4448-4467`), but not for the automounter.
- **3 Find it yourself:**
  - **3.1** `grep -n 'std::filesystem::remove(path, ec);' src/hardware/Mpu6050RecordingSession.cpp` → 2 lines (702, 831).
    Question: what does the UI do at its next start if the second rename fails too? Answer: writes its template, hat on bus
    10 (`UI:src/DisplayConfigBridge.cpp:41-58`).
  - **3.2** Compare the comment rules: `grep -n 'std::string stripInlineComment' src/hardware/*.cpp`. Three files. Question:
    which one keeps `recording_start;still` whole? Answer: the trigger's (`HW/TriggerOutput.cpp:56-66`); the IMU's
    (`HW/Mpu6050RecordingSession.cpp:209`) cuts at the `;`.
  - **3.3** M1 on your file. Prediction: no errors; aliases; maybe the INA219 warning.
- **4 Make the change:**
  1. 37.1: header + test, all ok.
  2. 37.2: the store + its temp-dir test.
  3. 37.3: the IMU writers.
  4. 37.4-37.6: replies and commands.
  5. 37.7: validate at start.
  6. 37.8: the template.
  7. 37.9-37.10: KB tools.

  One check per step.
- **5 Test:**
  - The journal at start shows `ApertarCore controls: … 0 errors`; `core.py get_state` has `controls_errors`.
  - `core.py get_controls` shows `"revision":"h…"` and your file's issues.
  - `core.py set_controls base=<rev> text@=/home/pi/apertar-hardware.conf dry_run=true` → empty diff. (`text="$(cat …)"`
    would drop the final newline and show one change: `CC H3`.)
  - Set the gyro level in the WebUI → **one** new history entry `by imu`, and `.bak` unchanged.
  - With nano open on the file, save it while a `core.py set_controls` runs in a loop → one refusal "being written", no lost
    text.
- **7 If it went wrong:** `Not saved: N new errors` → the message names the line; restore from history (`cp`); `git revert`.

### T38. No more silent overwrites: old tabs, the UI's template, large saves

- **Learn:**
  1. a version header on HTTP, 409, and telling a browser from a script (`Origin`);
  2. why the UI's "create the file if missing" is a revert waiting to happen;
  3. a line limit that drops a client without a word.
- **Risk:** low. Two UI deletions; Patrik rebuilds the UI. **Time:** 1.5 h.
- **3 Find it yourself:**
  - **3.1** `grep -n 'bus=10' ~/ApertarUI/src/DisplayConfigBridge.cpp` → the template's hat line.
  - **3.2** `grep -n '64 \* 1024' src/ipc/ControlServer.cpp` → `:261`. Question: what does a client get back? Answer:
    nothing; the connection closes.
- **4 Make the change:** 38.1-38.7.
- **5 Test:**
  - An old tab: open Config in a tab, build and restart, Save in the old tab → 409 "Apertar was updated", text kept.
  - `mv ~/apertar-hardware.conf ~/x.conf`, restart the UI → no file appears (the card goes red: "replaced", with Restore).
    `mv` it back.
  - A 100 KiB text through `core.py` (a copy with comments) → a reply, not a dropped socket.

### T39. Save and it works: Core restarts only what changed, never inside a command, never during a take

- **Learn:**
  1. the lock graph (F7): why no handler may wait on the worker;
  2. groups, two-phase stop, why a take defers the reload;
  3. why the status must be a snapshot (a data race is undefined behaviour, not "rare");
  4. pending restarts from facts.
- **Risk:** a deadlock would freeze buttons. It is avoided by design, and test 5.2 tries it. **Time:** 3 h.
- **3 Find it yourself:**
  - **3.1** `grep -n 'lock_guard' src/ApertarCoreApp.cpp | sed -n '1,40p'`. Find the three hardware mutexes and who takes
    them in which order.
  - **3.2** Why does `stop()` wait up to a second on a missing bus? (`sleep_for(1000)`, `HW/NeoRotary4Input.cpp:637`.) Add
    up the four inputs.
  - **3.3** `grep -n 'config_ = loadConfig();' src/hardware/*.cpp` and `grep -n 'bool NeoRotary4Input::enabled' -A3
    src/hardware/NeoRotary4Input.cpp`. Question: which thread writes `config_`, which reads it? Answer: the worker writes, the
    web thread would read.
- **4 Make the change:** 39.1-39.10.
- **5 Test:**
  - **5.1** `core.py set_controls base=<rev> set.neorotary4.encoder3_press=zebra` → "Saved. Core is applying it."; the knob 4
    press toggles zebra with no restart; the journal says `controls: applied N in … ms`. GPIO buttons were not restarted (no
    `GPIO input enabled` line).
  - **5.2** Hold a knob turning while saving 10 times (`for i in …`): no freeze, no `Hardware input action failed`.
  - **5.3** Edit `encoder2_cw` over ssh, then save `[gpio_buttons]` from core.py → saved, `encoder2_cw` still not applied.
    Save a NeoRotary key → refused, asking for `adopt_outside=true`.
  - **5.4** Start a take, save a knob change → "applies when the take ends"; stop the take → applied.
  - **5.5** `curl -s 127.0.0.1:8000/api/state` shows `hardware_status` with `neorotary4` `connected` and a `since`.
  - **5.6** Change `[cfexpress_hat] bus` (same value back afterwards) → pending "automounter"; restart it (Patrik) → pending
    clears within 2 s.
- **7:** a reload that never finishes → `journalctl … | grep controls`; the worker logs before each stop.

### T40. I2C devices on both screens: which buses exist, what answers, why bus 1 is missing, what only you do in config.txt

- **Learn:**
  1. the Pi's I2C buses and what creates them;
  2. probing by ID register, not ACK, and never touching a chip a driver polls (F34);
  3. reading `config.txt` without writing it, and why a DPI panel cannot be detected;
  4. a warning on the camera's own screen.
- **Risk:** scans add bus traffic: they are refused in a take, limited to known addresses on the camera bus, and skip
  driver-held addresses. **Time:** 3.5 h.
- **3 Find it yourself:**
  - **3.1** M3 (the bus list, the adapter links) and M4 (`i2cdetect -y 1` with Core stopped, Patrik). Prediction: `34`, `49`.
  - **3.2** `grep -n 'dtoverlay\|dtparam' /boot/firmware/config.txt`: your three commented DPI lines, and how `i2c_arm` is
    written.
- **4 Make the change:** 40.1-40.8.
- **5 Test:**
  - **5.1** Controls → I2C devices on your rig: hat bus 1 answering, NeoRotary connected since …, INA219 "bus 4 does not
    exist" (or off after Q7).
  - **5.2** Scan bus 1 → `0x34`, and `0x49` listed as "Core's driver". Find on the NeoRotary row → bus 1 · 0x49.
  - **5.3** The before-the-fix state without touching `config.txt`: `core.py set_controls … set.neorotary4.bus=15` (the select
    offers only existing buses, `CO 16h`) → red row and the touch chip. Set it back.
  - **5.4** The DPI box from a host run of `parseConfigTxt` on SRC's `config.txt` excerpt (the host test runs the `sed` on a
    copy).

### T41. The easy editor: a row per button or knob, Turn adjusts, a dropdown per gesture, chips you drag, pins already used greyed out

- **Learn:**
  1. a page is a view of a file (Cinemate `7de3065`);
  2. one occupancy registry for every picker;
  3. drag with pointer events plus a non-drag path;
  4. why rows must not redraw from a poll;
  5. showing what the reader really uses.
- **Risk:** WebUI only; the file changes only through `set_controls`. **Time:** 3 h.
- **5 Test:**
  - Knob 2 → Turn adjusts: Shutter (two keys in the diff). Swap it.
  - Drag `fps24` before `iso200` on a PCF pin (the dry run shows the order).
  - Move button d6 to GPIO 21 → disabled ("GPIO 21 · Tally").
  - Add a button and save without a pin → blocked.
  - A phone-width run.

### T42. Listen, outputs and a review in plain words: which control is which, does the tally light, undo in one click

- **Learn:**
  1. a callback that reports input before the mapping decides;
  2. a summary built from a diff and a catalog;
  3. undo as "restore the previous version through the same front door".
- **Test:**
  - Listen, turn knob 3 → its row lights.
  - Tally Active high + Open drain → warning.
  - Review shows "Knob 4 press: Resolution → Zebra".
  - Save a button on a busy pin (M5) → red banner, Undo restores it.

### T43. The text editor for advanced users: line numbers, Check and Fix, a diff before Save, merges, history

- **Test:**
  - Type `bus=1 # x` under `[cfexpress_hat]` → Check: an error at that line, Fix moves the comment.
  - Save → diff → confirm.
  - A gyro tap while typing → the stale banner; Save → "Merged with the gyro change".
  - Edit a comment over ssh meanwhile → the conflict box, Show changes.
  - Restore "Before Controls" from history.

### T44. Hold and double press on every button, knob push and PCF pin

- **Learn:** a gesture state machine fed by polls; why press must wait when hold or double is mapped; sampling limits (the
  NeoRotary push is read about every 70 ms with a 60 ms debounce, so an edge needs about 70-140 ms: `CC I1`, PROBABLE from
  `HW/NeoRotary4Input.cpp:650-711`); a slow command on the poll thread delays the next sample (`CC I2`).
- **Risk:** changes the timing of a button only when you map hold or double on it.
- **Test:**
  - The host test.
  - `d10_hold=standby` → the Record warning shows.
  - A knob push double → `photo`; measure the shortest double the NeoRotary catches, and set `double_ms` for that source.

### T45 (optional). The touch UI: a read-only Controls card, the gyro page through Core

- **Test:**
  - Change the IMU orientation on the touch screen → history shows `by imu`, no outside banner.
  - The card shows the NeoRotary connected.

### Tutor blocks

The anchors were checked here: each string occurs once in its file, at that line, at `eb9cc39` / `d8098d0`. There are no
check pipes. T39-T45 tutor blocks are written with each note, since T36-T38 move App lines by several hundred.

T36:

```
%% tutor
ref core src/hardware/GpioInput.cpp 108 std::string normalizeSingleAction(std::string action)
ref core src/hardware/Pcf8574Input.cpp 140 std::string normalizeSingleAction(std::string action)
ref core src/hardware/NeoRotary4Input.cpp 121 std::string normalizeSingleAction(std::string action)
ref core src/hardware/ButtonActionList.hpp 80 ButtonActionList parseButtonActions(std::string_view text, Normalizer normalize)
ref core src/hardware/ButtonActionList.hpp 57 inline bool isOutputAction(const std::string &action)
ref core src/hardware/RecordingIndicatorOutput.cpp 118 bool isRecordingIndicatorAction(const std::string &text)
ref core src/hardware/GroveAnalogInput.cpp 125 std::string normalizeTarget(std::string target)
ref core src/hardware/TriggerOutput.cpp 130 std::optional<TriggerOutput::Event> eventFromToken(std::string token)
ref core src/ApertarCoreApp.cpp 8588 std::string normalizeHardwareAnalogTarget(std::string target)
ref core src/ApertarCoreApp.cpp 914 std::optional<double> parseDoubleValue(const std::string &value)
ref core src/ApertarCoreApp.cpp 1374 std::optional<std::string> hardwareActionSuffix(const std::string &action,
ref core src/ApertarCoreApp.cpp 1311 std::vector<double> pcfIsoOptions()
ref core src/ApertarCoreApp.cpp 8838 void ApertarCoreApp::handleSingleHardwareInputAction(const std::string &action)
ref core src/ApertarCoreApp.cpp 9147 Hardware input action ignored: unknown action
ref core src/ApertarCoreApp.cpp 9612 if (command.name == "list_sensor_modes") {
ref core src/ApertarCoreApp.cpp 9633 if (command.name == "help")
check 3.1 | grep -c 'std::string normalizeSingleAction(std::string action)' /home/pi/ApertarCore/src/hardware/GpioInput.cpp | ^1$
check 4.1 | grep -c 'inline std::string canonicalAction' /home/pi/ApertarCore/src/hardware/ActionCatalog.hpp | ^1$
check 4.3 | grep -c 'normalizeSingleAction' /home/pi/ApertarCore/src/hardware/NeoRotary4Input.cpp | ^0$
check 4.4 | grep -c 'canonicalAnalogTarget' /home/pi/ApertarCore/src/hardware/GroveAnalogInput.cpp | ^1$
check 4.6 | grep -c 'command.name == "list_actions"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"list_actions"}' | "stepping":true
%%
```

Check 5.1 needs `list_actions` in `SAFE_CORE_CMDS` (step 4.6, `CC H2`). Without it `tutorial.py` refuses the check.

T37:

```
%% tutor
ref core src/ApertarCoreApp.cpp 66 constexpr size_t kMaxEditableHardwareConfigBytes = 256 * 1024;
ref core src/ApertarCoreApp.cpp 4313 std::filesystem::path editableHardwareConfigPath()
ref core src/ApertarCoreApp.cpp 3477 parser.read(config_path)
ref core src/ApertarCoreApp.cpp 4448 std::optional<int> parseConfigInteger(const std::string &text)
ref core src/ApertarCoreApp.cpp 4284 int busNumber = 4;
ref core src/ApertarCoreApp.cpp 122 std::string errorReply(int id, const std::string &message)
ref core src/ApertarCoreApp.cpp 7201 std::string ApertarCoreApp::handleRequest(const std::string &line)
ref core src/ApertarCoreApp.cpp 7231 std::string ApertarCoreApp::handleWebCommand(const std::string &payload)
ref core src/hardware/Mpu6050RecordingSession.cpp 209 std::string stripInlineComment(std::string value)
ref core src/hardware/TriggerOutput.cpp 56 std::string stripInlineComment(std::string value)
ref core src/hardware/Mpu6050RecordingSession.cpp 604 bool writeHardwareConfigValue(const std::filesystem::path &configPath,
ref core src/hardware/Mpu6050RecordingSession.cpp 715 bool updateImuBiasConfig(const std::filesystem::path &configPath,
ref core src/hardware/Mpu6050RecordingSession.cpp 1335 bool Mpu6050RecordingSession::setConfiguredLevelReference(std::string *error)
ref core src/hardware/Mpu6050RecordingSession.cpp 1370 bool Mpu6050RecordingSession::clearConfiguredLevelReference(std::string *error)
ref core src/util/SettingsFile.hpp 36 inline bool atomicWrite(const std::filesystem::path &path, const std::string &data)
ref core src/util/SettingsFile.hpp 59 class QtIniLock {
check 3.1 | grep -c 'std::filesystem::remove(path, ec);' /home/pi/ApertarCore/src/hardware/Mpu6050RecordingSession.cpp | ^2$
check 4.1 | grep -c 'inline std::vector<Issue> validate' /home/pi/ApertarCore/src/hardware/HardwareConfigText.hpp | ^1$
check 4.3 | grep -c 'std::filesystem::remove(path, ec);' /home/pi/ApertarCore/src/hardware/Mpu6050RecordingSession.cpp | ^0$
check 4.4 | grep -c 'command.name == "set_controls"' /home/pi/ApertarCore/src/ApertarCoreApp.cpp | ^1$
check 5.1 | curl -s -m 3 -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"get_controls"}' | "revision":"h[0-9a-f]{16}"
%%
```

T38:

```
%% tutor
ref core src/ApertarCoreApp.cpp 5430 std::string buildHardwareConfigFileJson()
ref core src/ApertarCoreApp.cpp 5463 bool saveHardwareConfigFile(const std::string &text, std::string *backupPath, std::string *errorMessage)
ref core src/ApertarCoreApp.cpp 7321 if (request.method == "POST" && request.path == "/api/config") {
ref core src/web/WebServer.cpp 70 case 503: return "Service Unavailable";
ref core src/web/WebServer.cpp 156 bool allowedBrowserOrigin(const WebServer::Request &request)
ref core src/ipc/ControlServer.cpp 261 if (line.size() >= 64 * 1024)
ref core src/web/WebControlPage.cpp 10372 async function saveConfigFile() {
ref ui src/DisplayConfigBridge.cpp 41 bool ensureDefaultHardwareConfigFile()
ref ui src/DisplayConfigBridge.cpp 587 ensureDefaultHardwareConfigFile();
ref ui src/Ina219Bridge.cpp 69 bool ensureDefaultHardwareConfigFile()
ref ui src/Ina219Bridge.cpp 497 ensureDefaultHardwareConfigFile();
check 3.2 | grep -c '64 \* 1024' /home/pi/ApertarCore/src/ipc/ControlServer.cpp | ^1$
check 4.3 | grep -c 'case 409: return "Conflict";' /home/pi/ApertarCore/src/web/WebServer.cpp | ^1$
check 4.7 | grep -c 'ensureDefaultHardwareConfigFile' /home/pi/ApertarUI/src/DisplayConfigBridge.cpp | ^0$
%%
```

---

## 8. Measurements on the Pi first

All read-only, as `pi`, before any code, unless marked. `K=~/apertar-kb/working/tools`. Lines marked "Patrik" need `sudo`.

**M1. The live file** (decides the host-test fixture, Q8, Q12)

```bash
grep -n '^\[' ~/apertar-hardware.conf                                          # sections and where (R3 U1)
grep -nE '^\s*(d|gpio|pin|bcm|p)[0-9_]|^\s*(encoder|enc|rotary)[0-9]' ~/apertar-hardware.conf   # every mapping (R4 Q9)
grep -nE '^[^#;]*=[^#;]*[^[:space:]#;][[:space:]]*[#;]' ~/apertar-hardware.conf  # comments after values: expect none (a ; inside events= is a separator)
grep -nE '^[[:space:]]+[^#;[:space:]]' ~/apertar-hardware.conf                  # indented keys: expect none
awk -F= '/^\[/{s=$0} /=/ && !/^[[:space:]]*[#;]/{k=s FS $1; if (seen[k]++) print NR": duplicate "k}' ~/apertar-hardware.conf   # expect nothing
grep -c $'\r' ~/apertar-hardware.conf                                           # CRLF lines: expect 0
stat -c '%U:%G %a %i %y %n' ~/apertar-hardware.conf ~/apertar-hardware.conf.bak /home/pi   # owner, mode, inode (R3 U2)
ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf 2>&1      # /boot copies (R3 U3)
diff ~/apertar-hardware.conf.bak ~/apertar-hardware.conf | head -40              # what the last WebUI save changed
head -2 ~/apertar-hardware.conf                                                  # starts like the UI template? (§3.4)
```

**M2. Who reads it, as which user** (R3 U4)

```bash
systemctl show -p User -p Environment apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter
/usr/local/libexec/apertar-cfe-automounter --check-config     # prints the effective hat bus and exits (UI:src/CfeAutomounter.cpp:793-802)
```

**M2b. Can `pi` see service start times** (decides how "still to do" clears, §3.6)

```bash
for u in apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter; do echo "$u $(systemctl show -p ActiveEnterTimestampMonotonic --value $u)"; done
cat /proc/sys/kernel/random/boot_id
```

**M3. Buses and access** (R4 Q12, R3 U6, `CC H6`)

```bash
id; ls -l /dev/i2c-* /dev/gpiochip*
for a in /sys/class/i2c-adapter/i2c-*; do echo "$(basename $a) $(cat $a/name) -> $(readlink -f $a/device)"; done   # labels by number + node
grep -nE '^\s*\[|dtoverlay|dtparam' /boot/firmware/config.txt                         # filters, overlays, i2c lines: readable as pi?
```

**M3b. DRM connectors** (information for the DPI box; after the fix no DPI connector is expected)

```bash
for c in /sys/class/drm/card*-*; do echo "$(basename $c) $(cat $c/status 2>/dev/null) modes=$(wc -l < $c/modes 2>/dev/null)"; done
```

**M4. Devices, the way Core will probe them.** v2 has **no seesaw loop** while Core runs (F34). These reads touch only
addresses Core's drivers do not poll:

```bash
i2ctransfer -y 1 r1@0x34; i2ctransfer -y 1 r1@0x34                                   # hat status twice (0x02 with a card)
i2ctransfer -y 10 r1@0x34                                                            # two masters / R4 Q4: does anything answer here now?
i2cget -y 10 0x68 0x75                                                               # IMU WHO_AM_I (MPU6050 0x68: datasheet)
i2ctransfer -y 10 w1@0x48 0x0f r2@0x48                                               # TMP117 device ID 0x01 0x17 (datasheet)
```

Optional, **with Core stopped** (Patrik: `sudo systemctl stop apertar-core`, then start it again):

```bash
i2cdetect -y 1                                                                       # expect 34 and 49
i2ctransfer -y 1 w2@0x49 0x00 0x01; sleep 0.01; i2ctransfer -y 1 r1@0x49            # seesaw HW ID: expect 0x87
```

The "never probe a chip Core's driver holds" rule does not need this: Core's own open already checks the ID
(`HW/NeoRotary4Input.cpp:494-514`), so "connected" proves `0x87`.

**M5. GPIO line info** (decides where the pin reservations come from; `CC H4`)

```bash
gpiodetect                                                                         # which chip is the RP1 header (number varies by kernel)
{ gpioinfo -c gpiochip0 2>/dev/null || gpioinfo gpiochip0; } | head -40              # libgpiod v2, else v1 (use the chip gpiodetect names)
pinctrl get 2,3,6,10,21                                                            # functions: SDA1/SCL1, inputs, the LED
```

Prediction: 6 and 10 `apertar-gpio-input`, 21 `apertar-rec-led` (as `HL` 2026-10-25). For 2/3: UNCONFIRMED whether they show as
used.

**M5b. UART pins** (decides the 14/15 rule)

```bash
pinctrl get 14,15; grep -nE '^\s*(enable_uart|dtoverlay=uart|dtparam=uart)' /boot/firmware/config.txt
```

**M6. The journal as pi** (`R4` K5)

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'NeoRotary4|PCF8574|GPIO input|recording indicator|trigger output|cfexpress hat|Hardware input' | tail -20
```

If it is empty or "permission denied", `pi` is not in `systemd-journal`, and the journal checks in T37-T40 are Patrik's
(`sudo`).

**After T37. M7:** the host test on the real file (M1's copy as the fixture): expect 0 errors.

**After T39. M8: reload time and safety.**

```bash
for i in 1 2 3; do rev=$(python3 -I $K/core.py get_controls | grep -o '"revision":"h[0-9a-f]*"' | head -1 | cut -d'"' -f4); python3 -I $K/core.py apply_controls base=$rev force=true; sleep 3; done
journalctl -u apertar-core -b --no-pager | grep 'controls: applied' | tail -3       # N ms each; Patrik if K5
```

Prediction: under 200 ms with every bus present; about 1 s (not 4) when drivers sit in their retry sleep.

**After T40. M9:** the WebUI scan of bus 1 and 10 against M4. `0x49` is listed as "Core's driver"; Find finds it.

---

## 9. Risks, questions, what is deliberately not built

### 9.1 Risks

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R1 | Reload deadlock | PROBABLE avoided (no handler waits on the worker; the worker takes `commandMutex_` only after every join) | T39 test 5.2; the journal logs before each stop |
| R2 | The touch UI's gyro page writes with `QSaveFile` and no lock: a Core write in the same milliseconds loses it | PROBABLE, small window | T45 moves the gyro page onto Core commands |
| R3 | `nano` saves in place; Core may hash, or merge into, half a file | PROBABLE | the stable-file check refuses; outside changes are announced after two equal stats |
| R4 | A probe or scan touches a chip Core's driver polls, and Core reads a wrong register (phantom turns) | PROBABLE (two-transaction seesaw read, F34) | driver-held addresses are never touched; M4's loop only with Core stopped |
| R5 | A scan disturbs the camera bus during preview | UNCONFIRMED | known addresses only on camera buses; refused in a take |
| R6 | DPI detection from `config.txt` misses an overlay set elsewhere (`include`, other filters) | PROBABLE | says "unknown" when no rule explains a missing bus |
| R7 | GPIO line info does not mark pinmuxed pins | UNCONFIRMED | M5; the UART rule; the after-save check + Undo |
| R8 | No WebUI auth: anyone on the hotspot can edit controls (as today with the raw editor) | CONFIRMED (F16) | `[run_script]` paths not writable from the browser (Q2) |
| R9 | The hat's bus has three readers; the automounter needs a root restart | CONFIRMED | pending item, derived and self-clearing; Restart Camera |
| R10 | T33 adds `[camera] max_fps` with a hook in `POST /api/config` | CONFIRMED (T34 design §4) | whichever lands second moves the hook into the store's post-save callback |
| R11 | Size: ~7,450 lines over ten tutorials; the WebUI JS is half | PROBABLE | each tutorial ends with a build and a test; the cut order in §6; T36-T40 are useful alone |
| R12 | Hold or double changes when press fires | CONFIRMED by design | only when mapped; the WebUI warns for Record |
| R13 | After a Core restart the revision cache is empty | PROBABLE | the history directory is the second cache |
| R14 | The validator and a reader disagree | PROBABLE | every rule comes from a cited reader line; host tests per rule; v2 already corrected one (`CC D1`) |
| R15 | A save during the 2 s stat window right after a hand edit | PROBABLE | the store re-reads under the lock; the stable-file check |
| R16 | A save makes a module worse (GPIO all-or-nothing) | PROBABLE | after-save check + Undo last save (`CO P1`); Q15 |
| R17 | A save applies a pending hand edit unseen | was PROBABLE in v1 | `adopt_outside` (§3.4) |
| R18 | The DPI commands run on a camera whose screen is DPI | PROBABLE | the box asks first; no detection is trusted (F35) |
| R19 | An old browser tab overwrites the file after the update | PROBABLE | 409 for header-less browser POSTs |
| R20 | A reload's side effects: Grove re-emits positions, PCF8574 `0xff`, trigger inactive, knob movement lost | CONFIRMED (F31) | only changed groups restart; never in a take; the reply says "Grove re-sends its knob positions" |
| R21 | A reload races a take that starts in the same microseconds | PROBABLE, tiny | gate check before the stops; the LED re-sync under `commandMutex_`; a trigger pulse in that window can be missed |
| R22 | An enabled NeoRotary with no actions now polls its bus (it did not start before) | CONFIRMED by design | status "connected · no actions"; turn it off to stop the polling |
| R23 | Pending-restart facts need `systemctl show` as `pi` | UNCONFIRMED (M2b) | fallback to boot_id |

### 9.2 Questions for Patrik

| # | Question | Default in this design |
| --- | --- | --- |
| Q1 | Keep `~/apertar-hardware.conf` as the system-controlled file (Core writes it; its notes in `~/.config/apertar-core/`), or move it (every reader in two repos, an automounter reinstall)? | keep |
| Q2 | `[run_script]` paths: editable from the browser (anyone on the camera's Wi-Fi can then make it run a script), or ssh only? | ssh only |
| Q3 | A hand edit over ssh: apply as soon as Core notices, or only on Apply / next start / Save and apply both? | Apply / start / both |
| Q4 | Hold and double press (T44): wanted? 800 ms hold, 350 ms double (per source after measuring)? Triple click, 2- and 3-position switches, chords: wanted? | T44 yes; the rest not built |
| Q5 | Saving during a take: refuse, or save now and apply after the take? | refuse `set_controls`; an Apply waits for the take's end |
| Q6 | T45 (the read-only card, the gyro page through Core): build it? (The template removal moved to T38 and the warning chip to T40) | after T43 |
| Q7 | INA219: no chip on your rig and bus 4 does not exist. Set `[ina219] enabled=false`? (It is on by default even without the section) | yes, as the first-open sheet's [Turn it off] |
| Q8 | Confirm the d10/d6 actions and the knob tokens (M1). They become the tutorials' example | M1 |
| Q9 | More than one of a device (two PCF8574s, two NeoRotary 4s)? Core runs one of each today (F17) | one |
| Q10 | "Any API command" actions for advanced users? | no: a catalog line + a dispatcher branch each (the coverage test enforces both) |
| Q11 | Numbering T36-T45 as listed, or merge (T38 into T37, T42 into T41)? | as listed |
| Q12 | Copy your live file into the KB as the host-test fixture? | yes, after you read it |
| Q13 | The two-masters and IMU-identity reads in M4: log the results in `hardware-log.md` as facts? | yes, after you confirm |
| Q14 | Nav: a new **Controls** item next to **Config**, or one panel with an Easy/Text switch? | two items |
| Q15 | `GpioInput` requests lines one by one, so one bad pin costs one button, not all? A Core change outside this design | later, its own tutorial; Undo now |
| Q16 | May the "still to do" card show **Restart Camera** (the existing `restart_system`, a reboot you press)? | yes |
| Q17 | A stale text save: merge per key when only values changed (with a review), or always refuse? | merge, with a review |
| Q18 | The DPI box: it asks "does this camera use a DPI screen?" and shows commands only for "No". Enough, or also hide it entirely on cameras without DPI overlays? | ask; shown only when an overlay is active |
| Q19 | The touch chip on the camera page (T40): there, or only in Settings? | camera page, next to the dropped-frame chip |
| Q20 | Remap the four NeoRotary knobs on the camera itself? | no for now; Listen + phone covers it |
| Q21 | Listen needs an enabled NeoRotary to run with no actions (R22). OK? | yes |
| Q22 | History: 20 versions + "Before Controls"; IMU taps coalesce per 10 minutes. OK? | yes |
| Q23 | A `test_output` command (light the tally / fire the trigger for 1 s, refused in a take)? | not built; the Outputs card's hint instead |

### 9.3 Cinemate's defects, and why they cannot happen here

| Cinemate (R1 §3.3) | Here |
| --- | --- |
| D1 `"None"` strings crash three handlers | no "none" object grammar: an empty gesture is `unset`; `null` is refused |
| D2 a pin remap does not enable Save | any draft change is dirty |
| D3 pins outside the list vanish on save | only changed keys are sent; unknown pins are shown, not dropped |
| D4 encoder fields overwritten on save | key edits; untouched keys are never written |
| D5 drag order re-sorted on load | the order is the file's order, never sorted |
| D6 one step per poll | NeoRotary4 fires `min(abs(delta), max_events_per_poll)` (`R2 §2.4`) |
| D7 the pencil defaults to `rec` | empty pencil = unset |
| D8 default clash | one template, validated by the host test; the UI's two templates removed in T38 |
| Two hand-kept catalogues | one header; `list_actions`; a coverage test |
| The editor has no auth and restarts the app | no auth (R8), but no restart: only the changed drivers reload |
| A pinless row is dropped silently (`R1 §1.3`) | Save is blocked until it has a pin |
| GPIO10 collision from a one-click toggle (`R1 §3.1`) | validator error; after-save check + Undo |
| Hold/click timings not shown (`R1 §1.4`) | timings shown; the Record warning |

### 9.4 Not built (and why)

| Item | Why |
| --- | --- |
| Writing `config.txt` (the DPI or `i2c_arm` lines) | house rule: guided text only (§4.4) |
| Detecting a DPI panel | not possible from the overlay alone (F35); the box asks |
| Editing on the touch screen | Q20 |
| Chords, triple click, 2/3-position switches | Q4 |
| A "Tidy" rewrite to canonical spellings | aliases are harmless and rewritten only when edited |
| Drag of an action onto another gesture | × and + do it; fewer mis-drops on a phone (`CO` budget note) |
| `test_output` | Q23 |
| A TMP117 reader (sensor temperature) | not asked; the scan names it |
| A file watcher that applies hand edits | Q3; half-saved files |
| Per-line GPIO requests | Q15 |
| Moving the file | §2.2 |

### 9.5 Sources

- Core `eb9cc39`, touch UI `d8098d0`, Cinemate `d6cc93e`, at the lines above.
- KB `d1d6a96` (unchanged since `e35ffa7` for these files): `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`,
  `lessons/hardware-log.md` (2026-10-23, 2026-10-25), `tutorials/README.md`, `tutorials/tutorial.py`, `llm/tutoring.md` §5,
  `working/tools/core.py`.
- The reader reports R1-R4; the critiques `critique-code.md` and `critique-operator.md`; `changes-from-critique.md` (all in
  this folder).
- The sketch: `sketch/hardware/ActionCatalog.hpp`, `sketch/hardware/HardwareConfigText.hpp`, `sketch/controls_test.cpp`,
  `sketch/make_old.sh` → `old_normalizers.inc`, `sketch/make_old2.sh` → `old_extra.inc`. Build:
  `g++ -std=c++20 -Wall -Wextra -Werror -I. -I<core>/src controls_test.cpp -o controls_test`; run `./controls_test <core>` →
  `all ok: 78 of 78 checks`.
