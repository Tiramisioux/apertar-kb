# Critique of design-controls v1 (Controls: GPIO dropdown, method assigning, I2C devices): operator lens

2026-10-28, cloud session, critic pass (operator: Patrik at the rig, and a new Apertar user). Read-only on every tree. Nothing
built, nothing run on the Pi. The only file written is this one.

Trees I opened (every `path:line` below is at these commits):

| Short name | File | Tree, commit |
| --- | --- | --- |
| `D` | `design-controls.md` (the design under review; `D:n` = its line n, `D§x` = its section) | this folder |
| `App`, `Web`, `WS`, `HW/` | `src/ApertarCoreApp.cpp`, `src/web/WebControlPage.cpp`, `src/web/WebServer.cpp`, `src/hardware/` | Core `scratchpad/controls/core-tip` `eb9cc39` |
| `UI:` | touch UI repo | `scratchpad/controls/ui-tip` `d8098d0` |
| `Cm ed.html` | Cinemate `src/module/app/templates/settings_editor.html` | `/home/user/tiramisioux/cinemate` `d6cc93e` |
| `sketch` | `sketch/hardware/ActionCatalog.hpp`, `sketch/hardware/HardwareConfigText.hpp` | this folder |
| `SRC`, `HL` | KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`, `lessons/hardware-log.md` | `/home/user/apertar-kb` `e35ffa7` |
| `R1`-`R4` | the reader reports | this folder |

Labels: **CONFIRMED** = I opened the line. **PROBABLE** = derived; the derivation is given. **UNCONFIRMED** = only the Pi (or a
datasheet I did not open) can say. A point taken from a reader report without reopening says so (`R2 §x`).

Design facts I re-checked and that hold: GPIO's single all-lines request (`HW/GpioInput.cpp:554-576`, retry `:642-649`); the
NeoRotary start rule (`HW/NeoRotary4Input.cpp:310-321`); the UI template writer (`UI:src/DisplayConfigBridge.cpp:41-47`,
`:131-135`, `:297-300`); the INA219 hint (`UI:qml/SettingsPage.qml:4526`); the hat watcher reading its config once
(`App:9306-9313`); the browser/native split on `Origin` (`WS:156-161`). All CONFIRMED.

---

## Verdict

The design gets the big things right for an operator: one file he already knows, nothing moved, Save applies without a restart,
comments and unknown keys survive, a validator that names the line and suggests the spelling, pins in use greyed with the reason,
and a DPI diagnosis that would have saved him the evening of 2026-10-23. What it misses is what happens **after** Save on a real
rig, the camera's own screen, and the paths a non-ssh user has.

| Design section | Verdict | Why (one line) |
| --- | --- | --- |
| §0 Short answer | keep, **change** | Add: a Save also applies a pending hand edit (Problem 2); the touch-UI status line is not optional (Problem 5) |
| §1.2 Walkthroughs | **change** | A: DPI-screen check and the HDMI 720x720 follow-up (Problem 7). C: an easy save applies the ssh edit too (Problem 2) |
| §2 Decision (A + reload + catalog) | keep | Keeping the path is right for him: one file, his fix untouched, his tutorials still true |
| §3.1 File, history, `.bak` | **change** | History and `.bak` churn on gyro taps; pin the adopted version (Problem 3) |
| §3.2 Schema, model | keep, **change** | Hat and INA219 have no live status (Problem 8); show effective values (Problem 11) |
| §3.3 Catalog | **change** | Record and toggles are offered on a knob turn; duplicates vanish (Problem 9) |
| §3.4 Store, hand edits, migration | **change** | Template-revert detection and restore (Problem 4); validate at start; old tabs (Problem 12) |
| §3.5 Commands, state | **change** | `dry_run` must carry the restart list; a post-apply result; `Find`; `hardware_input` (Problems 1, 6, 8, 9) |
| §3.6 Live apply vs restart | **change** | "Applied" per section; pending derived from service start times (Problems 3, 6) |
| §3.7 Messages | keep, **change** | Good wording. Add consequences in operator words, fix buttons (Problems 6, 11) |
| §3.8 Ways a change could be lost | **change** | Missing row: an easy save applies an unapplied hand edit (Problem 2) |
| §4.1 Controls panel | keep, **change** | Turn shorthand, Swap, Listen, Undo, "Discard changes" (Problems 9, 13) |
| §4.2 Config panel | **change** | Key-level merge for a stale text; stale banner before Save (Problem 10) |
| §4.3 Two modes | **change** | Easy → Text → Easy must not trap the draft (Problem 10) |
| §4.4 I2C card | keep, **change** | DPI box safety, Find/Use, pre-save probe, PCF8574A (Problems 7, 8) |
| §4.5 Touch UI (T43 optional) | **change** | Status line mandatory and early; template removal early (Problems 4, 5) |
| §5 Catalog, rig | keep | Add PCF8574A addresses (Problem 8) |
| §6 Plan | **change** | Moves listed under "Order", end of this file |
| §7 Tutorials | **change** | T43's own test triggers the template before T43; T39 test 5.3 cannot pick bus 15 in the select |
| §8 Measurements | **change** | Add M2b, M3b, M5b (end of this file) |
| §9 Risks, questions | keep, **change** | Add R16-R19 and Q15-Q22 |

---

## The walkthroughs (what the operator does, what the design shows, where it goes wrong)

Each row points to a Problem below. Where the design is fine, the row says so.

**W1. First start after the update (T36-T38 built, Core restarted by Patrik)**

| Step | Design (cite) | Operator sees | Problem |
| --- | --- | --- | --- |
| Core starts | file adopted in place; first `get_controls` validates (`D:406-410`) | nothing, anywhere, until he opens the WebUI | 12 |
| An old WebUI tab from before the update is still open on the laptop | `POST /api/config` without `X-Apertar-Revision` = last-writer-wins (`D:390-392`) | a Save from that tab overwrites the file with old text | 12 |
| He opens Controls on a fresh image file | red for the image's tally on a PCF8574 at bus 10 · 0x20 with no chip (`Remote I/O error`, `HL:42-43`), INA219 bus 4, "No [cfexpress_hat]" (`D:525`, `D:538`) | a wall of red for hardware he does not own | 12 |
| He taps the gyro sync offset +1 | IMU write through the store: header added on "the first save" (`D:303`, `D:389`), `.bak` and history rotated (`D:385`) | first "save" of his file is a gyro tap, with two new comment lines | 3, 12 |

**W2. Assign the NeoRotary 4's knobs and pushes (easy editor)**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Which knob is "Knob 1"? | rows Knob 1-4 = `encoder0-3` (`D:617`) | no way to find out from the camera | 9 |
| Knob 1 = ISO | two lines, Turn right and Turn left, each with its own `+ action` (`D:600-604`) | 2 menus per knob, 8 for the board; easy to pair ISO up with Shutter down | 9 |
| Knob 3 turns the wrong way | one `invert_direction` for all four (`HW/NeoRotary4Input.cpp:417-418`, `:582`) | cannot reverse one knob | 9 |
| Push 4 = Zebra | dropdown "Monitoring › Zebra on / off" (`D:121`) | fine | — |
| Puts Record on a turn by mistake | catalog lets `capture` run on a turn (sketch `ActionCatalog.hpp:25`, `:33`) | a take starts/stops on every detent | 9 |
| Save | reload in ~1 s, "Connected" (`D:114`) | fine; but he is not told if another module broke | 1 |

**W3. A PCF8574 button**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Fits a PCF8574A module | address select 0x20-0x27 (`D:678`) | his 0x38 is "unknown"; custom hex works | 8 |
| Turns PCF8574 On (file says bus 10) | `[pcf8574]` row On/Off, bus select (`D:675-677`) | if the chip is on bus 1, Save goes through and the row turns red only after | 8 |
| Pin 0 = Photo | PCF block pins 0-7, Press line (`D:617`) | fine | — |
| Tally on PCF pin 7 too | shared expander, three shadow bytes (R2 §2.14, PROBABLE) | no warning | 14 |

**W4. A GPIO tally**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Tally On, GPIO 21, Active high | Outputs card (`D:636-639`) | fine; GPIO 21 greyed for buttons | — |
| "Does it work?" | no test | must record a take to see it | 14 |
| Leaves "Open drain" on (template value on the trigger) | open drain + active high only pulls low (PROBABLE) | LED never lights; no warning | 14 |

**W5. The I2C card when `/dev/i2c-1` is missing (the DPI case)**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Opens I2C devices | red row, "Bus 1 does not exist… DPI overlay on config.txt line 76" (`D:110`, `D:699`) | good: this is the evening of 2026-10-23 in one line | — |
| Copies the command box | `sudo sed -i '76,78 …'`, `sudo reboot` (`D:711-715`) | a user whose DPI panel is his only screen gets a dark camera | 7 |
| After the reboot | `[display]` "unchanged: text-mode only" (`D:115`) | HDMI shows the 720x720 square UI (`SRC:134-143`); nothing tells him why | 7 |
| His `config.txt` has `dtparam=i2c_arm=on,i2c_arm_baudrate=400000` | exact-string match (sketch `HardwareConfigText.hpp:766`) | told to add a line he already has | 7 |
| Camera screen | nothing (T43 optional, `D:717`) | knobs dead, no word on the camera | 5 |

**W6. The encoder answers on the wrong address (strapped to 0x4A, or 0x48 typed)**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Row state | "Not connected" / "Wrong device: 0x48 answered 0x12 … TMP117" (`D:702`) | the right diagnosis | — |
| Finding the board | per-bus Scan (`D:682`) | he scans each bus, reads hex, retypes the address | 8 |
| Moves the hat to bus 1 by mistake | Review = diff + issues only (`D:592`) | saved; Core's card-pull detection silently reads nothing | 8 |

**W7. Text and easy at the same time (laptop text view, phone easy view, gyro page on the camera)**

| Step | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Phone saves a knob | key edits merged (`D:663`) | fine | — |
| Laptop text Save | refused, base changed (`D:664`, `D:547`) | redo by hand, even when the phone touched another section | 10 |
| Gyro tap on the camera (before T43: direct write) | outside change banner, "Not applied" (`D:128`, `D:403`) | "outside Apertar" for Apertar's own screen; Apply offered for nothing | 3 |
| An ssh edit waits "not applied"; phone saves a knob | reload loads the whole file (`D:467-491`) | the ssh edit goes live too; Review showed one line | 2 |
| Easy → Text (peek) → Easy | box holds the dry-run text "unsaved"; Text → Easy blocked (`D:665-666`) | must save or discard to go back | 10 |

**W8. A bad file**

| Case | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| `zebrra` typed over ssh | banner within 2 s, the line, "Did you mean zebra?" (`D:121`, `D:528`) | good | — |
| `bus=1  # header` under `[cfexpress_hat]` | error message (`D:517`) | the I2C card row shows bus 1; Core uses 10 | 11 |
| `[neorotary4]` twice | error "Merge them" (`D:522`) | easy edits land in one of them; which one counts is reader-specific | 11 |
| File moved or deleted, UI restarted | template written with hat on bus 10, NeoRotary off (`UI:src/DisplayConfigBridge.cpp:41-47`, `:297-300`, `:131-135`) | until T43: knobs and hat stop, no message; no "restore" | 4 |

**W9. What needs a restart, and how he is told**

| Change | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Knob, button, PCF, tally | reload, ~1 s (`D:497`) | fine | — |
| Hat bus | "Still to do (you): sudo systemctl restart apertar-cfe-automounter" (`D:556`) | only after Save; no clearing rule; a sudo line in a browser | 6 |
| INA219, `[display]`, `[network]` | UI restart command (`D:498-502`) | same | 6 |

**W10. The touch UI**

| | Design | Operator sees | Problem |
| --- | --- | --- | --- |
| Knobs dead | T43 read-only card, optional, after T41 (`D:717-721`, `D:1203`) | nothing on the camera through T36-T42 | 5 |
| INA219 card | unchanged: "Check /home/pi/apertar-hardware.conf and INA219 wiring" (`UI:qml/SettingsPage.qml:4526`) | points at a file, not at the editor | 5 |
| Edit on the camera | not built (`D:721-722`) | agreed for the pin matrix; see Q20 for the four knobs | — |

---

## Problems

Ordered by harm on set.

### 1. One Save can switch off every Pi GPIO button, Record included, and the design shows it only as a pill.

- **What:** `GpioInput` asks the kernel for all its lines in one request (`HW/GpioInput.cpp:554-576`). If one line is busy the
  whole request fails; the thread stores the error and retries every second (`:642-649`). CONFIRMED. After T38 every save that
  touches a `gpio_*` section restarts that request (`D:467-491`). The pins the picker greys come from `/dev/i2c-1`, `config.txt`
  and `gpioinfo` (`D:338`); whether `gpioinfo` marks pins muxed by an overlay (UART, SPI, 1-wire) is UNCONFIRMED (`D:1145-1146`,
  risk R7).
- **Consequence:** he adds a button on a pin some overlay holds. Record (GPIO 10) and Eject (GPIO 6) stop with it. The WebUI pill
  for "Pi GPIO buttons" turns red, but the toast said "Saved". On set he finds out when Record does nothing. PROBABLE (from the
  lines above). Cinemate in the same situation skips only the later claimant and keeps the others (`R1 §2.4`), so here the
  failure is wider than in the editor Patrik is porting from.
- **Fix:**
  1. The WebUI already waits for `controls_applied_revision` (`D:278`). Have it compare each module's state before and after.
     A module that went from connected to error gives a red banner in Card 1 that names what it carries: "Pi GPIO buttons
     stopped: GPIO 15 is busy. Record (GPIO 10) and Eject (GPIO 6) do nothing now. [Undo last save]" (Problem 13).
  2. Core: the `controls` event after a reload carries `changed:[{module, before, after, detail}]`, so the touch UI line
     (Problem 5) can say it too.
  3. Picker: GPIO 14/15 advisory "UART", as 0/1 are. Cinemate never offers 0, 1, 14, 15 (`R1 §1.3`).
  4. Question for Patrik (Q15): `GpioInput` requests per line, so one bad pin costs one button. That is a Core change outside
     this design; until then the Undo is the safety net.

### 2. Any WebUI save also applies a hand edit that was "not applied", and Review does not show it.

- **What:** hand edits apply only on Apply or at the next start (`D:396-404`, Q3). A save's reload restarts the drivers, and each
  `start()` re-reads the whole file (`HW/NeoRotary4Input.cpp:310-313`, F6 `D:204`). CONFIRMED. Key edits go onto the current
  file (`D:568`), and the Review diff is current → new (`D:427`). So the reload carries the hand edit too. PROBABLE.
- **Consequence:** he types `d6=standby` over ssh to try later. From the phone he remaps knob 4 and saves. Review showed one line;
  the camera now goes to standby on d6. Q3's protection is bypassed by any unrelated save.
- **Fix:** when `applied_revision != base`, the `dry_run` reply adds `outside_diff` (applied → current, from the revision cache
  or history). Review shows "This save also applies the change made outside Apertar at 21:14:" with that diff, and the button
  reads **Save and apply both**. Same text on Apply. Add the row to `D§3.8`.

### 3. Gyro taps flood history and `.bak`, and make the file look "not applied" or "changed outside".

- **What:**
  - IMU commands become store key edits (`D:389`). Every store write copies to `.bak` and to history, pruned to 20 (`D:385`).
  - The WebUI sync-offset buttons send one `adjust_imu_sync_offset` per tap (`Web:11013`). The touch UI's ±1 buttons
    (`UI:qml/SettingsPage.qml:3715`, `:3719`) write the file directly per tap until T43. CONFIRMED.
  - Card 1's pill says "Not applied" when the revision differs from `controls_applied_revision` (`D:589`, `D:451`). An IMU
    change is "next use", with no reload (`D:500`).
  - Before T43 each touch-UI gyro write is a revision Core did not write, so the "Changed outside Apertar … Not applied
    [Apply]" banner appears (`D:128`, `D:397-403`). PROBABLE (from the rules).
- **Consequence:** twenty taps on ±1 ms evict every useful version. `.bak` stops meaning "before my last save" (the toast names
  it, `D:292`). After a calibration that is already in effect, the panel says "Not applied" and offers an Apply that restarts
  six drivers for nothing. The "outside" banner fires for Apertar's own screen.
- **Fix:**
  1. History: one version per WebUI save or outside change. IMU writes from the same writer within 10 minutes replace the last
     IMU version. Only WebUI saves rotate `.bak`.
  2. Pin the **adopted** version: the file as Core found it at its first start after T37, labelled "Before Controls", never
     pruned (`D:289` already keeps "the version Core first saw"; say when it is taken and that it is never pruned).
  3. Track "applied" per section group. Only the reload sections (`D:497`) can make the file "Not applied". IMU, `[run_script]`
     and `[storage]` changes never do.
  4. The outside banner names the sections and when each takes effect: "[mpu6050] changed outside Core at 21:14 (probably the
     touch UI's gyro page): applies at the next take." No Apply button when only read-on-use sections changed.

### 4. The silent revert (the UI's template) stays until T43, and T43 is optional and last.

- **What:** when `/home/pi/apertar-hardware.conf` does not exist, the UI writes its template with `[cfexpress_hat] bus=10` and
  `[neorotary4] enabled=false` (`UI:src/DisplayConfigBridge.cpp:41-47`, `:297-300`, `:131-135`). CONFIRMED. Its removal is row
  43.1 (`D:900`), in T43, "optional", "after T41" (`D:717`, `D:1203`). T43's own test, "rename the file, start the UI"
  (`D:1036`), triggers the template on any tree that does not yet have 43.1.
- **Consequence:** a `mv` instead of `cp` when restoring from history, a test, a mistake: the next UI start rewrites the file,
  the knobs and the hat stop, and nothing says so on either screen. PROBABLE (template content and trigger CONFIRMED).
- **Fix:**
  1. Move 43.1 (two deletions in the UI repo) into T37, as a step "Core owns the file, so the UI stops creating it". Low risk.
  2. T37, Core: on start and on every stat, if the file is missing, empty, or its revision equals the UI template's revision
     (hash the template text in the host test), and history holds a later Core-written version, Card 1 turns red: "This file
     was replaced by the touch UI's default (hat on bus 10, NeoRotary off). Your last saved version is from 21:14.
     [Restore it]". Restore = `set_controls text=<that version> base=<current>`, shown as a diff first.

### 5. The camera's own screen still says nothing when the knobs are dead.

- **What:** the symptom that started this project was "knobs dead; nothing on screen" (`D:110`). After T39 only the WebUI shows
  the cause. The touch UI card is T43, optional (`D:717-721`). The INA219 card keeps "Check /home/pi/apertar-hardware.conf and
  INA219 wiring" (`UI:qml/SettingsPage.qml:4526`). CONFIRMED.
- **Consequence:** on set he stands at the touch screen. The fix for the original symptom needs a phone, the hotspot and a URL
  he must remember.
- **Fix:** make one line on the touch UI mandatory and early (in T39, UI repo): when an enabled module is in error, a restart is
  pending, or the file has errors, show "NeoRotary 4: bus 1 missing · WebUI → Controls · http://10.42.0.1:8000". Use the real
  address the network bridge already knows. The data is already planned: `hardware_status` in the touch UI's poll (`D:445`). The
  INA219 hint becomes "Turn it off or pick its bus in WebUI → Controls". The read-only card, the gyro page through Core, and the
  rest of T43 can stay optional.

### 6. "Pending restarts" never clear correctly, speak only sudo, and appear only after Save.

- **What:** `pending[]` exists in `get_controls` and the event (`D:426`, `D:455`). No rule says when an item clears (every use of
  "pending" in `D`: `:426`, `:455`, `:706`, `:720`, `:1186`). The text is "Still to do (you): sudo systemctl restart
  apertar-cfe-automounter" (`D:556`, `D:706`). The `dry_run` reply has no `apply` (`D:427`). CONFIRMED (design text).
- **Consequence:** if pending lives in Core's memory, it survives Patrik restarting the automounter, or a Core restart clears it
  although the automounter still runs the old bus. A user without ssh has a sudo line and no way to act. He learns the cost of a
  change only after saving it.
- **Fix:**
  1. Derive pending from facts. For each reader, compare its service start time (`systemctl show -p ActiveEnterTimestamp
     apertar-cfe-automounter apertar-ui-direct apertar-network`; readable as `pi`: PROBABLE, see M2b) with the history time of
     the last change to its sections. The item then clears by itself.
  2. Name the consequence in operator words: "Until then the hat's buttons and automount still look at bus 10."
  3. Offer one button that covers all of them. The WebUI already has **Restart Camera** (`Web:3664` →
     `restart_system` → reboot, `App:11267-11272`; CONFIRMED). Keep the per-service sudo lines for ssh users. Patrik decides
     whether the card may show it (Q16).
  4. `dry_run` returns `apply` too, so Review says "After saving: Core applies the knobs now. You then restart the
     automounter (or the camera)."

### 7. The DPI box can black out a camera that uses its DPI screen, and leaves the HDMI 720x720 surprise.

- **What:**
  - The card says "Without a DPI panel you can turn them off" and shows `sudo cp …`, `sudo sed -i '76,78 s/^dtoverlay=/#dtoverlay=/'`,
    `sudo reboot` (`D:699`, `D:711-715`). Nothing checks whether a DPI panel is in use.
  - The KB records the side effect of exactly this fix: HDMI becomes the main touch screen at 720x720 (`SRC:134-143`). The
    design keeps `[display]` text-only and calls it "unchanged" (`D:115`).
  - Line numbers are computed when the card is drawn. The backup name `config.txt.bak-apertar` is fixed (`D:712`).
  - `i2c_arm` detection is an exact string match (sketch `HardwareConfigText.hpp:766`). `dtparam=i2c_arm=on,i2c_arm_baudrate=…`
    reads as "off", so the card would also show "Add `dtparam=i2c_arm=on`" (`D:700`). CONFIRMED (sketch); the consequence is
    PROBABLE.
- **Consequence:** a new user whose Waveshare 4" panel is the camera's screen pastes the box and reboots into a dark camera,
  recoverable only with a card reader. Patrik gets the square UI on HDMI and must rediscover SRC §4.5. A line number gone
  stale comments the wrong line. A second run overwrites the first backup.
- **Fix:**
  1. Core reads `/sys/class/drm/card*-DPI-*/status` and `modes` (sysfs, as `pi`: PROBABLE; KB `SRC:136`, `:160`). If a DPI
     connector has modes, a real panel is attached: the box says "A DPI screen is attached. Turning the overlays off turns it
     off. Use bus 10 instead (SRC §5)", and no command is shown. Only "not connected / no modes" shows the commands, behind a
     tick "My camera uses HDMI only".
  2. Build a pattern command from the overlay names found, idempotent, and keep the line numbers as text:
     `sudo sed -i -E 's/^(dtoverlay=(vc4-kms-DPI-4inch|waveshare-4dpi|waveshare-touch-4dpi)(,.*)?)$/#\1/' /boot/firmware/config.txt`.
  3. Use a timestamped backup, `sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.$(date +%Y%m%d-%H%M%S)`, and add an
     undo line: "To undo: copy the backup back, or with a card reader remove the `#` on these lines in config.txt on the boot
     partition."
  4. Add an "after the reboot" line: "The touch UI moves to HDMI at 720x720. In Config set `[display] hdmi_external_only=true`
     (as before) or `ui_width=1920 ui_height=1080 ui_layout=landscape_large`, then restart the UI (`SRC:140-141`)", with a link
     that opens Config at `[display]`.
  5. Parse `dtparam=` as a comma list. When the DPI reason applies, show only that one.

### 8. Wrong bus or wrong address: the card diagnoses but does not lead to the answer, and a Save can move the hat to where it does not answer.

- **What:**
  - Scan is per bus (`D:682`) and Probe per row (`D:680`). There is no "find this device on any bus", although SRC asks for bus
    auto-detect (`SRC:155`). A scan hit has no "use this address".
  - Review is a dry run with diff and issues (`D:592`). It does not probe a bus or address that changed.
  - PCF8574 addresses are 0x20-0x27 (`D:678`). PCF8574A modules answer at 0x38-0x3F: datasheet knowledge, UNCONFIRMED w.r.t.
    the KB.
  - The hat: Core's media watcher logs its bus once (`App:9310-9313`) and card presence only to the journal (`App:9344`). No
    state field carries it (grep `hat_card`: journal only). `hardware_status` comes from the six drivers'
    `enabled/lastError/running` (`D:453`). So the hat row has no live state, and "never probe a chip Core's driver holds"
    (`D:561`) blocks the probe. CONFIRMED (code); the gap is PROBABLE.
- **Consequence:** a NeoRotary strapped to 0x4A shows "Not connected"; he scans, reads hex, retypes. A hat moved to bus 1 by
  mistake saves fine, and Core's card-pull detection during takes (the yank work) then reads nothing, silently. A PCF8574A shows
  as "unknown device at 0x38".
- **Fix:**
  1. **Find** on each device row: probe the type's addresses on every existing bus (camera buses: known addresses only; refused
     in a take). List the hits with **Use bus 1 · 0x4A**.
  2. Scan entries get **Use for NeoRotary 4** (or whichever type the ID proves).
  3. Review probes every device whose `bus`, `address` or `enabled` changed and prints "found / nothing answers" beside the diff.
     If nothing answers, add a warning line; Save stays allowed.
  4. Add the hat row's state from the media watcher (`answering, card in` / `no answer since 21:14`) and INA219's from its last
     read.
  5. Put PCF8574A 0x38-0x3F in the select and the known-address table, labelled UNCONFIRMED until checked on the rig.
  6. Give states a time, as Cinemate does: "connected since 21:14", "lost at 21:20: Remote I/O error" (`Cm ed.html:7379-7385`).
     That is how a loose Qwiic cable shows itself.

### 9. Assigning the knobs: twice the clicks for the common case, unsafe choices on a turn, and no way to tell which knob is which.

- **What:**
  - (a) Each knob has two lines, Turn right and Turn left, each with its own `+ action` (`D:600-604`). Cinemate's quad row has
    one **Turn** select: a setting, mapped to inc/dec (`Cm ed.html:3541`, `R1 §1.7`). CONFIRMED.
  - (b) Every action except `standby` may run on a turn. The default is `sources = Both` (sketch `ActionCatalog.hpp:25`), and
    `capture`, `record_toggle`, `photo`, `timelapse`, `still_mode` (`:33-37`), the monitoring toggles and `eject` keep it. The
    `list_actions` example shows capture `"rotation":true` (`D:361`). CONFIRMED.
  - (c) The NeoRotary has one `invert_direction` for all four knobs (`HW/NeoRotary4Input.cpp:417-418`, `:582`). CONFIRMED.
  - (d) The parser drops duplicate actions in a mapping without a word (`HW/ButtonActionList.hpp:103-104`). The `+ action` menu
    only stops at six (`D:627`). CONFIRMED.
  - (e) The editor says Knob 1-4; the file, the text view and line messages say `encoder0-3` (`D:617`).
  - (f) An unmapped press never reaches App (`App:8810-8811`), an unmapped turn is dropped in the driver
    (`HW/NeoRotary4Input.cpp:663-665`), and a NeoRotary with no action at all does not start (`:317-321`). Nothing publishes
    which control moved. CONFIRMED.
  - (g) Run script 1-5 are offered, but their paths are ssh-only (Q2). An empty `path2` is a silent no-op.
- **Consequence:** pairs get mismatched (cw = ISO up, ccw = Shutter down). A knob mapped to Record starts and stops a take on
  every detent. "Reverse knob 3" cannot be done the way Cinemate users expect. "ISO up, ISO up" (jump two stops) silently becomes
  one. A new user cannot tell which physical knob is Knob 1.
- **Fix:**
  1. Per knob a **Turn adjusts** select (ISO, Shutter, WB, FPS, Resolution, EV, Other…) that writes the `_up`/`_down` pair.
     **Separate actions** splits it into today's two lines, so nothing is lost.
  2. Give the catalog a `stepping` flag. A turn line lists stepping actions first and puts the rest under "Fires on every
     detent". The validator warns for record, photo, timelapse, still mode and eject on a turn.
  3. Add a per-knob **Swap** (swaps the two tokens) and a device-level **Invert** labelled "all four knobs".
  4. `+ action` disables an action the line already holds, and the validator warns on duplicates.
  5. Show the key under each line in small mono (`encoder3_press · line 31`). That bridges to the text view.
  6. **Listen** (T40, small Core change): driver callbacks carry `{source, index, gesture}`, and Core publishes
     `hardware_input` (or `last_input` in state) also for unmapped knobs and pins. The editor highlights that row for 2 s. It
     works for NeoRotary knobs (let the driver run with no actions while Listen is on) and PCF pins. For GPIO it only works on
     rows that already have a pin (only those lines are requested).
  7. Run-script items show the path from the file, or "not set (set it over ssh)".

### 10. Text and easy at the same time: the text editor loses to every unrelated write, and switching modes traps the draft.

- **What:**
  - A text Save is refused when `base != current` (`D:381`, `D:664`). Any IMU write or easy save changes the revision; the reply
    is "Show changes, or load the new file and redo your edit" (`D:547`).
  - Easy → Text puts the dry-run text in the box, "marked unsaved". Text → Easy with unsaved text is blocked (`D:665-666`).
  - A same-key conflict says "Reload to see it" (`D:548`). Whether the other draft changes survive the reload is not said.
  - Staleness is found only at Save.
- **Consequence:** Patrik edits 30 lines in Config, a calibration happens on the camera, and his Save is refused. He copies his
  text out, reloads and redoes it. Peeking at the text from Easy forces a save or a discard of the easy draft.
- **Fix:**
  1. Stale text Save: Core turns base → mine into key edits (it has `canonicalKey`, `applyEdits`, `conflicts`: sketch
     `HardwareConfigText.hpp:125`, `:431`, `:443`) and dry-runs them on the current file. With no shared key and no comment-only
     or structural edit it answers "Merged with the gyro change of 21:16. Review the result." Otherwise it refuses as today. Q17.
  2. Both panels show a stale banner from the 1 s poll as soon as `controls_revision != base`, with who and when, before he
     types more.
  3. Easy → Text → Easy is free while the box still equals the dry-run text. The easy draft is kept.
  4. A same-key conflict keeps every other draft change and shows the row with both values: **Keep mine** / **Take the file's**.

### 11. A bad file in the easy view: the editor shows values the camera does not use.

- **What:**
  - Easy rows are built from the parsed text (`D:330`). `bus=1  # x` under `[cfexpress_hat]` makes Core's reader keep 10
    (`App:4580`, F9 `D:207`; CONFIRMED). The row would show 1. PROBABLE.
  - With duplicate sections (`D:522`) it is unclear which copy an easy edit changes.
  - `Issue` holds `line, error, message, id` (sketch `HardwareConfigText.hpp:518-523`; CONFIRMED). It has no section or key to
    hang an issue on a row, and the dry-run text's line numbers differ from the file's.
- **Consequence:** the I2C card says "Hat · bus 1" while the camera uses bus 10, which is exactly the trap the validator was
  built for. An easy edit lands in the copy of `[neorotary4]` that one reader ignores.
- **Fix:**
  1. A row whose key has a reader-specific error shows the effective value in red: "Core reads 10 here (comment after the
     value)".
  2. A duplicated section locks its rows: "Merge the two [neorotary4] sections in Config first (lines 14 and 16)", with a jump.
  3. Add `section` and `key` to `Issue`.
  4. Add **Fix** buttons for the mechanical rules, each producing a diff to confirm: comment after a value → own line; indented
     key; text after `]`; duplicate key with an equal value.

### 12. First start after the update: the check runs only when someone opens the WebUI, and an old tab can still overwrite.

- **What:**
  - "T37's first `get_controls` validates the live file" (`D:408`).
  - `POST /api/config` without `X-Apertar-Revision` stays last-writer-wins "for old scripts" (`D:390-392`). The server already
    tells browsers from native clients by `Origin` (`WS:156-161`; CONFIRMED).
  - The two-line header is added on "the first save" (`D:303`). Through the store's single path that can be a gyro tap
    (`D:389`). PROBABLE.
  - Warnings such as "No [cfexpress_hat]…" (`D:538`) and INA219 bus 4 (`D:525`) fire for hardware the user may not own.
- **Consequence:**
  - Nothing tells the operator at boot.
  - A tab opened before the update runs the old page (no header). Its Save overwrites the file without a base check: the lost
    update this project exists to stop.
  - On a fresh image file the first look at Controls is a wall of red for absent hardware (the image's tally on a PCF8574 at
    bus 10 · 0x20 with no chip, `Remote I/O error`, `HL:42-43`).
- **Fix:**
  1. Validate at Core start. Log one summary line, and put `controls_errors` and `controls_warnings` in state (the touch UI line
     of Problem 5 uses them).
  2. A `POST /api/config` that has `Origin` but no header gets 409: "Apertar was updated: reload this page. Your text stays in
     the box." Row 37.8 already keeps the text on 409. Header-less native clients keep working.
  3. On the first open, a sheet: "Apertar checked your file. Nothing was changed. 2 devices are on but do not answer: the tally on a
     PCF8574 (bus 10 · 0x20), INA219 (bus 4 does not exist). [Turn them off] [Keep]". Warn about absent hardware only when it is enabled, or
     when it answers somewhere.
  4. Add the header on a WebUI save only.

### 13. Undo and words: "Revert", hashes, and no one-click undo.

- **What:**
  - Card 1 has Review, Save and **Revert** (`D:592`). In Cinemate, Revert loads the stock defaults (`Cm ed.html:1405`, title
    "Load the stock defaults into this form"; CONFIRMED).
  - The pill reads "Saved h3f0c" (`D:589`) and history rows "21:14 · by WebUI easy · h3f0c" (`D:654`).
  - Undo takes four steps: Config → History → Load → Save (`D:654-655`).
- **Consequence:** a Cinemate user expects defaults from Revert, or is afraid to press it. An easy-mode user who broke something
  must go to the text panel to undo it, under the pressure of Problem 1.
- **Fix:**
  1. Rename Revert to **Discard changes**.
  2. Add **Undo last save** in Card 1: it restores the previous version as a text replace, shows the diff, then applies.
  3. The pill reads "Saved 21:14 · WebUI", with the hash in a tooltip.
  4. History rows carry a summary: "knob 4 press: Resolution → Zebra".

### 14. Outputs: no test, a polarity trap, PCF outputs that do not follow the expander.

- **What:**
  - The Outputs card offers On, Target, line, Active high and Open drain (`D:636-639`), and no test.
  - A GPIO output with Open drain can only pull low (`HW/RecordingIndicatorOutput.cpp:645` sets `OPEN_DRAIN`; the level comes
    from `outputPhysicalValue`, `:227-229`). The UI template writes `open_drain=true` for the trigger
    (`UI:src/DisplayConfigBridge.cpp:112`), while the code default is false (`HW/RecordingIndicatorOutput.hpp:42`; trigger per
    `R2 §1.4`). CONFIRMED (code); the electrical outcome is PROBABLE.
  - Trigger and tally inherit `[pcf8574]`'s bus and address unless they set their own (`R2 §1.4`). The image's file had
    `[recording_indicator] … bus=10 address=0x20 pcf_pin=7` (`R3 §1.3`).
  - Buttons, trigger and tally on one PCF8574 each keep a shadow byte (`R2 §2.14`, PROBABLE).
- **Consequence:** wiring a tally, he cannot see it light without recording. "Active high" with "Open drain" left on never
  lights. He moves the PCF row to bus 1 and the tally stays on bus 10.
- **Fix:**
  1. A test line that needs no code: "Test: take a photo (a 320 ms flash), or start and stop a take" (`R2 §2.9`). Optionally a
     `test_output target=tally ms=1000` command, refused in a take.
  2. A validator warning: "Open drain with active high: this line can only pull low; an LED from the pin to GND will not
     light." Add the wiring hint under the pills: "GPIO → resistor → LED → GND = Active high" (`HL:36-49`).
  3. A PCF output with its own bus or address shows "on bus 10 · 0x20 (its own setting; the PCF8574 inputs are on bus 1)
     [Follow the PCF8574]".
  4. Warn when buttons and an output share one PCF8574 (unconfirmed on hardware, R4 Q10).

### 15. Hold and double press (T42) delay Record without saying so plainly. Lower harm (opt-in).

- **What:** with Hold mapped, Press fires on release; with Double mapped, Press waits 350 ms (`D:892`). The WebUI note says
  "Press now fires on release, because Hold is set" (`D:894`).
- **Consequence:** a Record button with Hold mapped starts the take when he lets go; with Double mapped it starts 0.35 s late.
  That matters for a slate and for a long press.
- **Fix:** when the Press line holds capture, record_toggle or photo, the note becomes a warning: "Record now starts when you
  let go (Hold is set)." Show `hold_ms` and `double_ms` next to the gesture names. Cinemate never showed its timings and had two
  models (`R1 §1.4`).

### 16. Small things

| # | What | Fix |
| --- | --- | --- |
| a | A new GPIO button "takes no pin until one is picked" (`D:630`). What Save does with it is not said. Cinemate drops such a row silently (`R1 §1.3`) | Block Save: "Pick a pin for the new button, or remove it" |
| b | HDMI DDC buses 13/14 are offered as device buses (`D:677`) | Show them, disabled for devices, labelled |
| c | The I2C devices table has six columns (`D:673-680`) | Stacked rows at phone width |
| d | nano writes in place, so Core may hash half a file (`D:1180`) and flash a banner of false errors | Announce an outside change only after two equal stats |
| e | Devices that are Off keep their mappings (`enabled` only), but the rows are not dimmed | Dim them and say "kept; applies when turned on" (Cinemate `Cm ed.html:7494-7498`) |
| f | In standby any press only wakes and turns do nothing (`App:8820-8826`) | One line in the Inputs card |
| g | For PCF8574, NeoRotary and Grove a section alone enables the device (`R2 §1.4`) | **Add a device** writes `enabled=false` unless Find or Probe found it |
| h | T39 test 5.3 sets NeoRotary to bus 15, but the select lists only existing buses (`D:677`, `D:1007`) | Do it with `core.py set_controls` or in Config |

---

## Cinemate's editor: what users liked, what tripped them, and where this design stands

| Cinemate (R1, reopened where cited) | Liked / tripped | This design | Gap → fix |
| --- | --- | --- | --- |
| Row per control, gesture lines, grouped command menu, argument from a spec, pencil | liked | same (`D:615-629`) | — |
| Pins in use greyed with the role | liked | same, plus I2C/DPI reasons (`D:615-616`) | add UART 14/15 (Problem 1) |
| Remap confirm in plain words: "Move … to GPIO 26? GPIO 7 will be freed up." (`Cm ed.html:6915`) | liked | Review shows an INI diff (`D:592`) | Review leads with a plain summary: "Knob 4 press: Resolution → Zebra. GPIO 6 freed." Diff under "Show file diff" |
| Quad **Turn** = one select (`Cm ed.html:3541`) | liked: simple | two menus per knob | **Turn adjusts** shorthand (Problem 9) |
| I2C page: "Not found. Looked for …" (`Cm ed.html:7326`), driver "connected since / lost at" (`:7379-7385`) | liked | state without time; no hat state | times; hat and INA219 status (Problem 8) |
| Absent hardware: panes dimmed, "assignments are kept and will apply when one is attached" (`Cm ed.html:7494-7498`) | liked | Off keeps mappings; no dimming | 16e |
| Comments kept; says so when it cannot | liked | never lost (`D:301-302`) | — |
| Full app restart on every Save (`R1 §1.13`) | tripped (camera blinks) | drivers reload in ~1 s | pending restarts for the others (Problem 6) |
| GPIO10 collision from a one-click toggle; later claimant skipped (`R1 §3.1`, `§2.4`) | tripped | validator error; but GPIO is all-or-nothing here | post-apply check + Undo (Problem 1) |
| "Revert" = stock defaults (`Cm ed.html:1405`) | ambiguous | "Revert" = discard draft | rename (Problem 13) |
| Hold/click timings not shown; two models (`R1 §1.4`) | tripped | one model (T42) | show timings; Record warning (Problem 15) |
| Pinless row silently dropped (`R1 §1.3`) | tripped | unspecified | 16a |
| D1-D8 (None strings, remap not dirty, pins vanish, encoder fields overwritten, drag order resorted, one step per poll, pencil → rec, default clash) | tripped | avoided by construction (`D§9.3`) | D8 only fully when the UI templates go: move 43.1 early (Problem 4) |
| Recovery console: raw editor checked by the real loader, backups | liked | Config panel with Check, diff, history | merge on stale text (Problem 10); restore from history in Controls (Problem 4) |
| Search box | liked on a long page | none | not needed at ~20 rows |

---

## Missing

| # | What | Why it matters |
| --- | --- | --- |
| 1 | A post-apply result in the WebUI and on the camera (Problem 1) | Today's "Saved" can mean "Record is dead" |
| 2 | **Listen**: identify a physical control (Problem 9) | Knob numbering, PCF wiring and "is it wired at all" are the first questions at the rig |
| 3 | **Find** a device on any bus, and **Use** from a scan (Problem 8) | The wrong-address case ends in retyping hex today |
| 4 | **Undo last save** and **Restore** from the Controls panel (Problems 4, 13) | Undo must be one click where the damage was done |
| 5 | Plain-words change summary in Review | The INI diff is for Patrik; a new user reads "Knob 4 press: Resolution → Zebra" |
| 6 | "Where each thing lives" table in T37 | `~/apertar-hardware.conf` (hardware), `~/.config/apertar-core/hardware-history/` (versions), `hardware-state.conf` (who wrote), `UI.conf` (operator prefs, T35 value lists), `config.txt` (his). Five homes; one table for backup and debugging |
| 7 | An on-set sheet (below) | The design describes Core paths; the operator needs the screens |

### What Patrik's day looks like with the fixes

| Situation | He does | Camera does | Screens say |
| --- | --- | --- | --- |
| Before the shoot: knob 4 press → zebra | phone, Controls → NeoRotary → Listen, presses knob 4, row lights; picks Zebra; Review | Review: "Knob 4 press: Resolution → Zebra"; Save; reload ~0.4 s | WebUI: "Applied 21:14. NeoRotary 4 connected." Touch UI: nothing (all fine) |
| He saved a bad pin | (same) | GPIO request fails | WebUI red: "Pi GPIO buttons stopped… Record does nothing. [Undo]". Touch UI line: "GPIO buttons off · WebUI → Controls" |
| ssh experiment left un-applied, then a phone save | Review | — | "This save also applies the change made outside Apertar at 20:50: d6=standby. [Save and apply both]" |
| Hat bus changed | Save | Core applies; automounter still on bus 10 | Card 1 and touch UI: "Restart the camera (or the automounter) so automount uses bus 1. [Restart Camera]". Clears by itself after the restart |
| A fresh camera with a DPI overlay and no panel | Controls → I2C | — | "Bus 1 does not exist… No DPI screen is attached. If your camera uses HDMI only: [commands]. After the reboot the touch UI moves to HDMI…" |
| File replaced by the UI default | — | knobs and hat stop | WebUI red: "Replaced by the touch UI's default… [Restore 21:14]". Touch UI line points there |

---

## Questions to add to `D§9.2`

| # | Question | Proposed default |
| --- | --- | --- |
| Q15 | `GpioInput` requests lines one by one, so one bad pin costs one button, not all (Problem 1)? | later, as its own tutorial; Undo now |
| Q16 | May the pending-restart card show **Restart Camera** (existing `restart_system`)? You press it; it is a reboot | yes |
| Q17 | A stale text Save: merge per key when nothing overlaps, or always refuse (Problem 10)? | merge, with a review |
| Q18 | Move the UI template removal (43.1) into T37 (Problem 4)? | yes |
| Q19 | Touch UI status line: mandatory, in T39 (Problem 5)? | yes; the rest of T43 optional |
| Q20 | Remap the four NeoRotary knobs on the camera (4 × 3 dropdowns with `InlineDropdownField`)? | no for now; Listen + phone covers it |
| Q21 | **Listen** (Problem 9): worth the small change to the three driver callbacks? | yes, in T40 |
| Q22 | History: count only WebUI and outside versions; coalesce gyro writes (Problem 3)? | yes |

## Risks to add to `D§9.1`

| # | Risk | Label | Mitigation |
| --- | --- | --- | --- |
| R16 | A save makes a module worse (GPIO all-or-nothing) | PROBABLE | post-apply compare + Undo (Problem 1) |
| R17 | A save applies a pending hand edit unseen | PROBABLE | `outside_diff` in Review (Problem 2) |
| R18 | The DPI box run on a camera whose screen is DPI | PROBABLE | DRM check; commands only for HDMI-only rigs (Problem 7) |
| R19 | An old browser tab overwrites the file after the update | PROBABLE | 409 for header-less browser POSTs (Problem 12) |

## Measurements to add to `D§8` (read-only, as `pi`)

```bash
# M2b: can pi see service start times (decides how "pending" clears, Problem 6)
systemctl show -p ActiveEnterTimestamp apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter
# M3b: DRM connectors and whether a DPI one has modes (decides the DPI box, Problem 7); empty after the fix is expected
for c in /sys/class/drm/card*-*; do echo "$(basename $c) $(cat $c/status 2>/dev/null) modes=$(wc -l < $c/modes 2>/dev/null)"; done
# M5b: UART pins (decides the 14/15 advisory, Problem 1)
pinctrl get 14,15; grep -nE '^\s*(enable_uart|dtoverlay=uart|dtparam=uart)' /boot/firmware/config.txt
```

Off the Pi: the NeoRotary 4's address-jumper range (the design offers `0x4A-0x4F`, `D:678`) and the PCF8574A range, from the
Adafruit and NXP/TI documentation. UNCONFIRMED until read.

---

## Order (smallest set of moves; the rest of the plan stands)

| Tutorial | Add | Problems |
| --- | --- | --- |
| T37 | UI template removal (43.1); validate at start + counts in state; template/missing/empty detection with Restore; 409 for header-less browser POSTs; pinned adopted version; header on WebUI saves only; history coalescing for IMU writes | 3, 4, 12 |
| T38 | post-apply module compare in the `controls` event; "applied" per section group; `outside_diff` and `apply` in `dry_run`; pending from service start times; outside banner per section | 1, 2, 3, 6 |
| T39 | Find + Use; pre-save probe in Review; hat and INA219 status with times; DRM DPI check, pattern sed, timestamped backup, undo and `[display]` lines; comma-list `dtparam`; PCF8574A; **touch UI status line** (UI repo) | 5, 7, 8 |
| T40 | Turn adjusts, Swap, device Invert; `stepping` flag; duplicates; key under each line; Listen; run-script paths; plain-words Review; Discard / Undo last save; dimmed Off devices; pinless-row block; effective values and Fix buttons | 9, 11, 13, 16 |
| T41 | key-level merge of a stale text; stale banner; Easy ↔ Text without losing the draft | 10 |
| T42 | Record-latency warning; timings shown | 15 |
| T43 | read-only card and gyro page through Core (optional, as designed) | — |

If the line budget must shrink, drop **drag onto another line** (`D:621`) first: keep drag to reorder within a line and use
remove + add to move. It saves code and avoids mis-drops on a phone, and Patrik's "drag and drop" request is still met.
