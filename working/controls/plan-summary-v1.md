# Controls project: plan summary (one page)

2026-10-28. Full design: `design-controls.md` (same folder). Core `0296ed1`, touch UI `5aab7e2`, Cinemate `d6cc93e`.
Host-tested sketch: `sketch/` (51 of 51 checks).

## Recommendation

- **The system-controlled file is the existing `~/apertar-hardware.conf`.** Core becomes its writer: one store with a lock
  (QLockFile-compatible), a revision (`h` + 16 hex), atomic writes, `.bak` and 20 versions of history in
  `~/.config/apertar-core/hardware-history/`.
- **No move and no split.** About 15 readers in 4 processes (one of them the root automounter) look at that path. The UI
  rewrites a template there whenever the file is missing (hat `bus=10`, NeoRotary off), which would silently undo the
  NeoRotary fix. Splitting would put the hat's bus and the encoder's bus in different files.
- **Format: the INI the readers already parse.** Core writes canonical names, `true`/`false`, never a comment after a value
  (Core's hat and INA219 readers ignore such a value), never a duplicate. It keeps every other byte: only edited lines change.
- **Two editors, one file:**
  - Easy mode sends key edits (`set.neorotary4.bus=1`). Core merges them per key against the revision the page loaded.
  - Text mode sends the whole file and is refused if the file changed since it was loaded.
  - Hand edits over ssh are kept. Core notices them within 2 s and validates them, but applies them only on Apply or at
    the next start.
- **API (flat socket commands, as Apertar's protocol requires):**
  - Commands: `get_controls`, `set_controls` (with `dry_run`), `apply_controls`, `list_actions`, `scan_i2c`,
    `probe_device`.
  - State fields: `hardware_status` and `controls_revision`.
  - Event: `controls`.
- **One action vocabulary.** `ActionCatalog.hpp` replaces the three identical `normalizeSingleAction` copies (host test:
  identical on 355 tokens). It feeds the validator and `list_actions`, so the WebUI keeps no copy of its own.
- **Live apply.** A Core worker thread restarts the six input and output drivers in boot order, outside `commandMutex_` (no
  deadlock). INA219 and the hat watcher reload too.
  - Still need a restart: the automounter, the touch UI and the network helper. The reply prints the exact `sudo` command
    for you.
  - `config.txt` is never written. Core reads it, says which line holds GPIO 2/3, and prints the commands you would run.
- **WebUI:**
  - New **Controls** panel in the page's own style. Cards: file status; I2C devices (bus from `/dev/i2c-*`, address,
    probe by ID register, scan, the DPI / missing bus / wrong ID / dead hub / two masters explanations); inputs (row per
    button or knob, dropdown per gesture, draggable action chips, pins in use greyed); outputs (tally, trigger).
  - **Config** stays as the text view, with line numbers, Check, diff before Save, conflicts and history.
  - Touch UI: read-only status card (optional, T43).
- **Your rig is the example:**
  - Hat `0x34` and NeoRotary 4 `0x49` on bus 1.
  - IMU `0x68` and TMP117 `0x48` (known, not used) on bus 10.
  - Tally on GPIO 21; buttons on GPIO 10 and 6.
  - PCF8574 `0x20` on bus 10 is in the file but off: no chip is fitted.
  - INA219 bus 4 does not exist.

## Measure first (read-only, as pi; §8)

| | What | Decides |
| --- | --- | --- |
| M1 | the live file: sections, mappings, comments after values, duplicates, owner, `/boot` copies, `.bak` diff | the test fixture, the example |
| M2 | unit users and environment; `apertar-cfe-automounter --check-config` | which path the store writes |
| M3 | `/dev/i2c-*`, adapter names, `config.txt` readable as pi | bus labels, DPI detection |
| M4 | `i2cdetect -y 1`; 20 seesaw ID reads while Core polls; hat on bus 1 and bus 10; IMU WHO_AM_I; TMP117 ID | "driver first" probing; two masters; IMU identity |
| M5 | `gpioinfo`, `pinctrl get 2,3,6,10,21` | where greyed pins come from |
| M6 | journal readable as pi | who runs the journal checks |

## Tutorials

| # | Title | Repo | Time | Checked before the Pi |
| --- | --- | --- | --- | --- |
| T36 | One list of button actions: `ActionCatalog.hpp` replaces three copies; `list_actions` | Core | 1.5 h | all |
| T37 | Core owns apertar-hardware.conf: store, lock, revision, history, validator with line numbers; `get_controls` / `set_controls text=`; IMU writers and `/api/config` through it | Core | 3 h | all |
| T38 | Save and it works: reload worker, key edits merged per key, driver state in `get_state`, `apply_controls`, outside-change notice | Core | 2.5 h | syntax (the worker is Pi-proven) |
| T39 | I2C devices: buses, `config.txt` facts, probes, scan; WebUI Controls panel part 1 (file + I2C devices). Your NeoRotary fix, guided | Core + WebUI | 3 h | Core all; WebUI `node --check` + mock |
| T40 | The easy editor: inputs and outputs cards, pin pickers, gesture dropdowns, draggable action chips | WebUI | 3 h | `node --check` + mock |
| T41 | The text editor: line numbers, Check, diff, conflicts, history | WebUI + Core | 2 h | same |
| T42 | Hold and double press on every button, knob push and PCF pin (`ButtonGesture.hpp`) | Core + WebUI | 2 h | all |
| T43 | Touch UI: read-only Controls card, the two template writers removed, gyro page through Core | UI | 2 h | Qt host build |

Size: about 5,400 lines added, 860 removed. Nothing touches `CameraController.cpp`. Every Core file involved syntax-checks on
the host (run here).

## Your decisions (§9.2)

| # | Question | Default in the design |
| --- | --- | --- |
| Q1 | Keep the path? | yes |
| Q2 | Script paths editable from the browser? | no |
| Q3 | Apply hand edits automatically? | no |
| Q4 | Hold and double press (T42), and the timings? | yes; 800 / 350 ms |
| Q5 | Save during a take? | refuse |
| Q6 | Touch UI changes (T43)? | all three |
| Q7 | Turn off the INA219 on your rig? | yes |
| Q8 | Confirm the d10/d6 and knob mappings | after M1 |
| Q9 | More than one of a device? | no |
| Q10 | "Any API command" actions? | no |
| Q11 | Numbering T36-T43 | as listed |
| Q12 | Your file as the test fixture? | yes |
| Q13 | Log the M4 facts in the hardware log? | yes |
| Q14 | Controls and Config as two nav items? | yes |
