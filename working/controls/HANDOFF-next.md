# Controls (T36-T45): where it stands, 2026-10-30

Branch `controls` (local, Pi + Mac; not on GitHub). Core `8be1ab5`, UI `ea44bd7`. Built and running on the Pi
(Core and UI restarted 2026-10-30 01:00; 0 errors, 0 warnings; UI QML loads clean).

## Built
- T36 vocabulary, T37 store/validator, T38 no silent overwrites: done, confirmed on the camera earlier.
- T44: Single/Double/Triple click and Hold (Cinemate timing) on GPIO buttons, PCF pins, NeoRotary pushes, GPIO encoder
  pushes; 1-0-1 inversion at start (GPIO, PCF). GPIO on kernel edge events (CONFIRMED: `edges=both` in gpioinfo).
- `[gpio_switches]`: two-way (`switchN_pins=17`, `_off`/`_on` = Position 0/1) and three-way (`switchN_pins=22,23`,
  `_position0..2`), applied at Core start. UNCONFIRMED on hardware (no switch on the rig).
- T39: controls worker applies saves and outside edits per driver group, deferred during a take. UNCONFIRMED live.
- T40: Scan per bus, DPI note, CFexpress hat card (CONFIRMED: detected on bus 1 at 0x34 with the drive line).
- T41: rows, pin pickers, gesture dropdowns, + Add action, Turn adjusts, multi-action chips.
- T42: Listen, review list, Undo last save, tally/trigger cards with Test. UNCONFIRMED live.
- T43: line numbers, Check, diff before Save, history picker.
- T45: touch chip "Controls: N errors" and Settings > Info > Controls card. Not seen (no touch screen).

## Not built
Fix (auto-repair) in the text editor; the gyro page through Core (45.1); chip drag on touch; pending restarts survive a
Core restart (in memory only); clicks on GPIO switches (positions only).

## To test next (needs hands on the camera)
1. Adafruit rotary 0: + Add action, Double click -> Take a photo, Save; no restart; double push takes a photo; journal
   "applied: restarted NeoRotary 4".
2. Listen, then press GPIO 10: its row lights.  3. Undo last save.  4. Scan bus 1: 0x34 and 0x49 (Core).
5. Tally card Test: the LED blinks.  6. GPIO 10 press still starts recording; double press (if mapped) takes a photo.
Record confirmed results in `lessons/hardware-log.md`.

## Tests (desk)
`working/tools/controls_test.cpp` (host, 120/121; D5 is GNU sed, Mac only), `controls_page_test.js` (Chrome mock, 60/60).

## Known, not ours
qmllint: duplicate id `wifiKeyArea` in `SettingsPage.qml` (Wi-Fi section).
