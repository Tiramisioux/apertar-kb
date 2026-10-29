# Controls: Patrik's decisions (Q1-Q23, design §9.2)

| Q | Answer | Date |
| --- | --- | --- |
| Q1 | Keep `~/apertar-hardware.conf` as the system-controlled file (Core writes it; its notes in `~/.config/apertar-core/`) | 2026-10-29 |
| Q3 | Hand edit over ssh: not applied on the side; applies on Apply / next start / Save and apply both (design default) | 2026-10-29 |
| Q4 | T44 yes (hold 800 ms, double 350 ms, per source after measuring). Extras wanted: triple click, 2- and 3-position switches, chords. Extras are not in T36-T45: later, own design | 2026-10-29 |
| Q5 | Save during a take: allowed; the file is written now and the drivers apply after the take ends (design changed from "refuse set_controls") | 2026-10-29 |
| Q7 | INA219 stays on by default (no [Turn it off] sheet). Principle: all hardware is autodetected, like Cinemate. A device that is not found is shown as "not found", not as a warning. Rule: detect and show (Core scans the known addresses at start and on demand; the card says found / not found / error; nothing is written automatically). Detect and configure (Core writes the sections itself) is a possible later step | 2026-10-29 |
| Q2 | `[run_script]` paths: ssh only; the browser cannot write them (design default) | 2026-10-29 |
| Q6 | T45 (touch UI read-only card, gyro page through Core): build it, after T43 (design default) | 2026-10-29 |
| Q8 | d10=capture, d6=eject and the four NeoRotary knob mappings (iso, shutter, wb, fps; knob 3 push = resolution) confirmed from the live file as the tutorial examples. IMU is on bus 10 (confirmed by Patrik). Live file already has [ina219] enabled=false | 2026-10-29 |
| Q9 | One of each device type (PCF8574, NeoRotary 4). Different kinds of I2C device run together (already designed: a section and a driver group each) | 2026-10-29 |
| Q10 | Middle option: an "API command" action with a free field, accepting only commands from a fixed allowlist of safe ones. Not in T36-T45; needs its own design pass (allowlist contents, argument validation, take-state rules), after T45 | 2026-10-29 |
| Q11 | Numbering T36-T45 as listed, no merging | 2026-10-29 |
| Q12 | Copy the live file into the KB as the host-test fixture (read by Patrik 2026-10-29, no secrets). Copied when the test needs it (T37); re-diff against the Pi then | 2026-10-29 |
| Q13 | M4 findings (two masters, IMU identity) go into lessons/hardware-log.md as facts, one by one, only after Patrik confirms | 2026-10-29 |
| Q14 | Nav: a new Controls item next to Config (two items); Config stays the text view | 2026-10-29 |
| Q15 | GpioInput requests lines one by one: later, its own tutorial. Until then the red banner + Undo last save | 2026-10-29 |
| Q16 | The "still to do" card may show Restart Camera (existing restart_system, a reboot Patrik presses). To check before T40: whether restart_system is refused during a take | 2026-10-29 |
| Q17 | Stale text save: merge per key when only values changed and no key clashes, shown as a review before saving; otherwise refuse (design default) | 2026-10-29 |
| Q18 | DPI box: asks "does this camera use a DPI screen?", shows commands only for "No"; shown only when an overlay is active (design default) | 2026-10-29 |
| Q19 | Touch warning chip (T40) on the camera page, next to the dropped-frame chip; only visible when something is wrong | 2026-10-29 |
| Q20 | No remapping of the NeoRotary knobs on the camera itself for now; Listen + phone covers it | 2026-10-29 |
| Q21 | An enabled NeoRotary starts and polls even with no actions (so Listen works on a fresh board); status "connected · no actions" (R22) | 2026-10-29 |
| Q22 | History: 20 versions + a pinned "Before Controls"; IMU taps coalesce per 10 minutes (design default) | 2026-10-29 |
| Q23 | No test_output command; the Outputs card shows a hint instead (design default) | 2026-10-29 |

## Notes

- 2026-10-29: the rig has no gyro (IMU) and no MPU6050; the user's build has neither, and the [imu]/[mpu6050] sections are template leftovers. The gyro level, calibration and the touch UI gyro page (T45) cannot be tried on the camera. The file still has [imu] and [mpu6050] enabled on bus 10, and a device at 0x68 answers 0x47; unidentified. The user says the camera uses an older IMX585 module; the chips at 0x34, 0x48 and 0x68 on bus 10 may belong to it (unconfirmed).

- 2026-10-29 (wish): assign scripts to buttons. Today a button can run a script: `d10=run_script1` in the file (catalog group "Scripts": run_script, run_script1..5), and the paths live in `[run_script] path..path5`. The Controls editor (T41) will offer the Scripts actions. The script paths stay ssh-only (Q2). A browser way to pick a script would need its own design, for example a fixed scripts folder to choose from, with no typed path (the middle option noted under Q2 and Q10). Not in T36-T45.
- 2026-10-29: scripts on buttons: chosen from a fixed scripts folder, never a typed path (the user answered "fixed scripts folder"). Folder name, listing, and how the pick is stored are for its own design pass; script paths otherwise stay ssh-only (Q2).
- 2026-10-29: Q14 changed: the Controls card sits at the top of the Config panel, above the text editor; no separate nav item ("they are basically two ways to control the config file").
- 2026-10-29: buttons get Single, Double and Triple click and Hold next to Press, like Cinemate (gpio_input.py): Press fires at once; clicks are counted and fire 0.5 s after the last release; a press held over 0.5 s is no click; Hold fires after 3 s. This replaces Q4's 800/350 ms design, where Press waited.
- 2026-10-29: two-way and three-way switches, like Cinemate: one pin with an on and an off action, or two pins with an action per position; the position is applied at Core start.
- 2026-10-29: the Controls card gets white SVG blueprint sketches of each accessory.
- 2026-10-29: like Cinemate (gpio_input.py check_initial_state): at Core start each button is read once; one that already reads pressed is taken as wired the other way round and inverted (press and release swapped), so 1-0-1 buttons (normally closed: 1 at rest, 0 while pressed) work like any other, with a journal line naming it. Applies to GPIO buttons and PCF pins (level inputs); not the NeoRotary pushes (fixed hardware). Caveat as in Cinemate: a button held down while Core starts is inverted until the next start.
- 2026-10-29: Q14 again, final: two nav items. Controls is for the user controls of the hardware that is there: the GPIO buttons, and each I2C device Core detects (NeoRotary 4, PCF8574, Grove ADC); a device not found shows no rows. Config is the file as text. (Replaces the "Controls on top of Config" entry.)
