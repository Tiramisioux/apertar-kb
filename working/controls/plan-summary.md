# Controls project: plan summary (one page, v2)

2026-10-28. Full design: `design-controls.md` (**v2**, same folder). What changed after the two critiques, point by point:
`changes-from-critique.md`. v1 is kept as `design-controls-v1.md` / `plan-summary-v1.md`. Core `0296ed1`, touch UI `5aab7e2`,
Cinemate `d6cc93e`. Host-tested sketch: `sketch/`, **78 of 78 checks** (v1: 51).

## Recommendation

- **The system-controlled file is the existing `~/apertar-hardware.conf`.**
  - Core becomes its only writer through **one store for the whole process**. App and the IMU code share it.
  - The store has a lock (QLockFile-compatible), a revision (`h` + 16 hex), atomic writes and a stable-file check (it never
    merges into a file nano is still writing).
  - History lives in `~/.config/apertar-core/hardware-history/`: 20 versions, gyro taps coalesced, and "Before Controls"
    pinned.
- **No move and no split.** About 15 readers in 4 processes look at that path.
  - The touch UI's "write a template if the file is missing" is removed early (T38): it is what silently undoes your
    NeoRotary fix (hat `bus=10`, NeoRotary off).
  - If it ever happens anyway, the WebUI says so and offers **Restore**.
- **Format: the INI the readers already parse, read with each reader's own comment rule.** Core writes canonical names, never
  a comment after a value, never a duplicate, and changes only the lines it edits.
- **Two editors, one file:**
  - Easy mode sends key edits that Core merges per key.
  - Text mode sends the whole file. If the file changed meanwhile and you changed only values, Core merges it too, after a
    review (Q17); otherwise it refuses and keeps your text.
  - Hand edits over ssh are kept and announced per section. An unrelated save never applies them behind your back: you get
    **Save and apply both**.
- **Live apply:**
  - A save restarts only the drivers whose sections changed (GPIO/PCF/tally/trigger as one group; NeoRotary; Grove), in
    about a second.
  - It never runs during a take: the reload is deferred until the take ends.
  - No command waits for it, which avoids the lock cycle the code critic found.
  - Gyro, display, network and script changes restart nothing.
- **Status you can trust.** Per module: connected / error / off / no actions, "since 21:14", "lost at 21:20".
  - The hat and INA219 have status too.
  - After every save the WebUI checks before against after. A module that broke turns red with what it carries ("Record does
    nothing now") and **Undo last save**.
- **Still to do for you** (automounter, touch UI, network helper) is worked out from the services' start times, said in plain
  words, and clears by itself. It offers the `sudo` line or **Restart Camera** (Q16).
- **API (flat socket commands):**
  - Commands: `get_controls`, `set_controls` (with `dry_run`), `apply_controls`, `list_actions`, `scan_i2c`, `probe_device`,
    `find_device`, `controls_history`.
  - Read-only ones run outside the camera's command lock, so a scan never blocks a button.
  - The socket's 64 KiB limit goes to 1 MiB.
- **One vocabulary.** `ActionCatalog.hpp` replaces three action normalizers, two analog-target lists and the trigger-event
  list. It is identical to today's code on 355 + 44 + 51 tokens, and a test checks that every action has a dispatcher branch.
  A new action = one catalog line + one branch.
- **`config.txt` is never written.** Core reads it and says which overlay holds GPIO 2/3. It then **asks whether a DPI screen
  is in use** (it cannot be detected) before it shows the commands for you to run: a timestamped backup, a `sed` by overlay
  name (safe twice), the reboot, an undo, and the HDMI 720x720 follow-up.
- **WebUI:**
  - A new **Controls** panel: file card; I2C devices (bus by number, Find on every bus, Use, scan that never touches a chip
    Core polls); Inputs; Outputs.
  - Inputs: Turn adjusts per knob, Swap, Listen, drag to reorder actions, the file key under each line, what Core really reads.
  - Outputs: test hint, polarity warning.
  - **Config** stays the text view: line numbers, Check, Fix, diff, merge, history.
- **Touch UI:** a warning chip on the camera screen when a module is in error, a restart is pending or the file has errors,
  with the WebUI address (T40). The read-only card and the gyro page through Core are optional (T45).
- **Your rig is the example:** hat `0x34` and NeoRotary 4 `0x49` on bus 1; IMU `0x68` and TMP117 `0x48` on bus 10; tally
  GPIO 21; buttons GPIO 10 and 6; no PCF8574 fitted; INA219 bus 4 does not exist (and the INA219 is on by default even
  without a section: Q7).

## Measure first (read-only, as pi; §8)

| | What | Decides |
| --- | --- | --- |
| M1 | the live file: sections, mappings, comments after values, duplicates, CRLF, owner, inode, `/boot` copies, `.bak` diff | the test fixture, the example |
| M2 / M2b | unit users and environment; `--check-config`; **units' start times readable as pi** | which path the store writes; how "still to do" clears |
| M3 / M3b | `/dev/i2c-*`, adapter names and device links, `config.txt` readable as pi; **DRM connectors** (information) | bus labels, DPI detection |
| M4 | hat on bus 1 and 10, IMU WHO_AM_I, TMP117 ID; the seesaw read **only with Core stopped** (you) | two masters, IMU identity |
| M5 / M5b | `gpiodetect`, `gpioinfo`, `pinctrl get 2,3,6,10,21`; **UART pins 14/15** | where greyed pins come from |
| M6 | journal readable as pi | who runs the journal checks |

## Tutorials

| # | Title | Repo | Time | Checked before the Pi |
| --- | --- | --- | --- | --- |
| T36 | One vocabulary: `ActionCatalog.hpp` replaces six copies; `list_actions` | Core | 2 h | all |
| T37 | Core owns apertar-hardware.conf: one store, each reader's rules, validator, IMU writers through it, checked at every start | Core | 3 h | all |
| T38 | No silent overwrites: `/api/config` with a revision (409 for an old tab), the UI's template writers removed, Restore, socket limit | Core + UI + WebUI | 1.5 h | all; Qt host build |
| T39 | Save and it works: reload only what changed, never in a take, status snapshot, per-key merge, outside edits, still-to-do | Core | 3 h | syntax (the worker is Pi-proven) |
| T40 | I2C devices on both screens: buses, Find, probes, the DPI box; Controls panel part 1; the touch warning chip. **Your fix, done by the software** | Core + WebUI + UI | 3.5 h | Core all; WebUI `node --check` + mock; Qt host build |
| T41 | The easy editor, inputs: rows, pin pickers, Turn adjusts, gesture dropdowns, draggable action chips | WebUI | 3 h | `node --check` + mock |
| T42 | Listen, outputs, a plain-words Review, Undo last save, the after-save check | Core + WebUI | 2.5 h | same |
| T43 | The text editor: line numbers, Check, Fix, diff, stale merge, history | WebUI + Core | 2 h | same |
| T44 | Hold and double press on every button, knob push and PCF pin (`ButtonGesture.hpp`) | Core + WebUI | 2 h | all |
| T45 | Optional: touch UI read-only card, gyro page through Core | UI | 1.5 h | Qt host build |

**Minimum path:** T36-T40. Size: about 7,450 lines added, 900 removed (v1: 5,400). If that is too much, the cut order is: Fix
buttons, Find, the first-open sheet, Listen. The safety tutorials (T37-T39) stay whole. Nothing touches `CameraController.cpp`.

## Your decisions (§9.2)

| # | Question | Default in the design |
| --- | --- | --- |
| Q1 | Keep the path? | yes |
| Q2 | Script paths editable from the browser? | no |
| Q3 | Apply hand edits automatically? | no (Apply, next start, or Save and apply both) |
| Q4 | Hold and double press (T44), and the timings? | yes; 800 / 350 ms, per source after measuring |
| Q5 | Save during a take? | refused; an Apply waits for the take to end |
| Q6 | T45 (read-only card, gyro page through Core)? | after T43 |
| Q7 | Turn off the INA219 on your rig? | yes (first-open sheet) |
| Q8 | Confirm the d10/d6 and knob mappings | after M1 |
| Q9 | More than one of a device? | no |
| Q10 | "Any API command" actions? | no: one catalog line + one dispatcher branch each |
| Q11 | Numbering T36-T45 | as listed |
| Q12 | Your file as the test fixture? | yes |
| Q13 | Log the M4 facts in the hardware log? | yes |
| Q14 | Controls and Config as two nav items? | yes |
| Q15 | GPIO lines requested one by one (one bad pin costs one button)? | later, its own tutorial |
| Q16 | **Restart Camera** in the still-to-do card? | yes |
| Q17 | Merge a stale text save when only values changed? | yes, with a review |
| Q18 | DPI box: ask "DPI screen?" before showing commands | yes, shown only with an active DPI overlay |
| Q19 | The warning chip on the camera page | yes, next to the dropped-frame chip |
| Q20 | Remap the knobs on the camera itself? | no |
| Q21 | NeoRotary runs (polls) when enabled with no actions, so Listen and status work? | yes |
| Q22 | History: 20 versions + "Before Controls", gyro taps coalesced per 10 min | yes |
| Q23 | A `test_output` command for the tally/trigger? | not built; a hint instead |
