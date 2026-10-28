# R1: Cinemate's GPIO dropdown and method assignment, read as a reference to port

Reader report for the Apertar "controls" project. It describes what Cinemate does. It does not
design the Apertar version. Other readers cover Apertar Core, the touch UI and the KB.

**Trees read (read only):**

| Tree | Commit | Short name used below |
| --- | --- | --- |
| `/home/user/tiramisioux/cinemate` (branch `dev`) | `d6cc93e` | paths are relative to the repo; every Cinemate citation is `@d6cc93e` |
| `/home/user/tiramisioux/cinemate-handbook` | `c99ff77` | `HB:` |
| `/home/user/apertar-kb` | `c15e422` | `KB:` |
| Apertar Core at the cinemate-port tip | `eb9cc39` | `Core:` (cited only to place Cinemate's ideas) |

**Labels:** CONFIRMED means I opened the line(s) cited. PROBABLE means derived, and the
derivation is stated. UNCONFIRMED means not checked. "SIM" means I ran the code on the host
with `gpiozero` stubbed out, with no files written (see 3.3). Shorthand: `ed.html` =
`src/module/app/templates/settings_editor.html`, `ed.py` = `src/module/app/settings_editor.py`.

---

## 0. The short version

- **Cinemate has no drag-and-drop for controls.** You assign a GPIO pin or an encoder with a
  `<select>` dropdown that greys out pins already in use and asks you to confirm a remap. The
  only drag-and-drop on the page reorders the "value step" chips (`arrays.*.steps`, e.g. ISO
  stops). CONFIRMED: `draggable` appears only in `makeChipDraggable`, `ed.html:4893-4901`. A
  grep for drag handlers finds only chips and the playback scrubber (`ed.html:4893-4924`,
  `:5828-5844`).
- **Assigning a method** works as one row per control: a pin picker, then one line per
  gesture. Each line has a "gesture" dropdown (Press / Single click / … / Hold), a "command"
  dropdown grouped like the CLI, an argument control generated from a spec, and a pencil
  button that switches the line to a free-text `method args…` field. CONFIRMED:
  `ed.html:3173-3206`, `:7001-7036`, `:7084-7130`, `:7135-7195`.
- **The config file is one JSONC file**, `/home/pi/cinemate/settings.jsonc`, and it is the same
  file as the git-tracked `settings.jsonc` at the repo root. Five things write it: the web
  editor, the recovery console, the operator in `nano`, Upload followed by Save, and git
  itself. Defaults are filled in by code (`config_loader._apply_settings_defaults`). A
  `settings.schema.json` exists, but nothing validates against it at runtime. CONFIRMED:
  `src/module/config_loader.py:17`, `:501`, `:801-830`. No `jsonschema`/`validate(` import
  exists under `src/` (grep).
- **Saving restarts all of Cinemate** through systemd. Nothing applies live. Saving
  config.txt reboots the Pi. CONFIRMED: `ed.py:799-806`, `src/module/cinepi_controller.py:4018-4072`,
  `ed.py:950-972`.
- **Methods are resolved by name** with `getattr(cinepi_controller, name)(*args)`. There is no
  arity check, no lock and no catalogue check at runtime. CONFIRMED:
  `src/module/gpio_input.py:536-547`, `src/module/i2c/quad_rotary_controller.py:115-119`.
- **The quad rotary board is hard-wired in the driver** to `board.SCL/board.SDA` (bus 1) and
  address `0x49`. The editor has no bus, address, poll or enable field. This is exactly the
  part Patrik's NeoRotary fix needs, and Cinemate has nothing to port for it. CONFIRMED:
  `src/module/i2c/quad_rotary_controller.py:204`, `:213`, `ed.html:2389-2399`.
- **The advanced editing worth copying is not on the settings page.** It is the recovery
  console's raw textarea editor (`:8080/edit/settings`). It validates through a three-rung
  ladder, keeps a backup, offers optional restart, and puts config.txt changes behind
  confirm-or-revert. On the settings page itself the "raw file" drawer is read-only.
  CONFIRMED: `services/cinemate-recovery/cinemate-recovery.py:380-458`, `:952-967`,
  `:1037-1060`, `ed.html:3008`, `:4610-4613`.
- **Six defects to avoid copying**, found while reading (details in 3.3):
  - The editor writes `"None"` strings that crash the two-way-switch, three-way-switch and
    GPIO-encoder handlers (SIM).
  - A pure pin remap does not enable Save.
  - Pins outside the offered list (0, 1, 14, 15) are silently dropped on save.
  - A GPIO encoder's `pull_up`, `debounce_time` and `enabled` are overwritten on save.
  - Numeric chip order that you drag is re-sorted on the next load.
  - The quad driver applies at most one step per 100 ms poll.

---

## 1. The settings editor UI (`ed.html`, 8297 lines)

### 1.1 Page frame

| Element | What it does | Cite |
| --- | --- | --- |
| Page tabs | `config` (config.txt), `i2c`, `lens`, `settings` (settings.jsonc, the default), `playback`, `raw` | CONFIRMED `ed.html:1487-1494` |
| Rail ("Physical controls" group) | `#controls`, `#pots`, `#quadrotary`, `#gpio`, `#oled` | CONFIRMED `ed.html:1456-1463` |
| Top bar | Search box; **raw-file button** labelled `settings.jsonc` (opens a drawer); **Revert** (load stock defaults, not saved); **Download**; **Upload** (load a file into the form, not saved); dirty pill "N unsaved"; **Save changes** | CONFIRMED `ed.html:1396-1411` |
| Pages with no file (`raw`, `playback`, `i2c`, `lens`) | hide Save, Revert, Download, Upload and the raw button | CONFIRMED `ed.html:7265-7279` |
| Copy | UI strings come from `resources/gui-text/*.md` through a Jinja `t('key')` global, read once at blueprint registration | CONFIRMED `ed.py:215-234`, e.g. `resources/gui-text/07-settings-physical-controls.md:10-17` |

### 1.2 GPIO IN (`#controls`): rows, add and remove

- **Markup:** an empty `<div class="cards" id="controlsList">` plus four add buttons:
  `+ Add button`, `+ Add 2-way switch`, `+ Add 3-way switch`, `+ Add rotary encoder`.
  CONFIRMED `ed.html:2251-2266`.
- **Rows** are built in JS, one `.actionrow` per control, carrying
  `data-control-type` ∈ {`button`,`switch2`,`switch3`,`rotary`} and a `data-prefix`
  (`hwctl-N`, a page-local counter). Every element id inside the row derives from that prefix.
  CONFIRMED `ed.html:3144-3146`, `:3354-3365`.
- **Row layout:** a heading strip (`GPIO | Action | Command`), the pin picker, the gestures
  block, and a "Remove" button. CONFIRMED `ed.html:3261-3274`, `:3354-3365`.
- **Add:** each button appends a `build*Row(null)` and marks the list dirty. A new row has no
  pin, plus default gestures: button `{press:'None'}`, 2-way `{on:'None',off:'None'}`,
  3-way `{s0,s1,s2:'None'}`, rotary `{rpress:'None'}`. CONFIRMED `ed.html:3392`, `:3407`,
  `:3424`, `:3490`, `:3517-3532`.
- **Remove:** a confirm modal ("Remove this button? This deletes it from the settings file on
  the next save."), then `row.remove()` and a refresh of every pin picker. CONFIRMED
  `ed.html:3294-3310`.
- **Population:** on load, the list is rebuilt from `hardware_controls.buttons`, then
  `two_way_switches`, `three_way_switches` and `rotary_encoders`, in that order. So on screen
  the rows are grouped by type, not in file order across types. CONFIRMED `ed.html:5179-5188`.
- **What the page cannot show:** `combined_actions` (a "hold button A + press button B" chord).
  It is copied through from the last load untouched. CONFIRMED `ed.html:3731`, comment
  `:3140-3143`.

### 1.3 How a pin is picked (`.gpio-select`)

| Aspect | Behaviour | Cite |
| --- | --- | --- |
| Pins offered | `GPIO_PINS = [2,3,4,5,6,7,8,9,10,11,12,13,16,17,18,19,20,21,22,23,24,25,26,27]`, BCM numbers, shown as `GPIO n` with `None` first | CONFIRMED `ed.html:6876`, `:6887-6898` |
| Pins never offered | 0, 1 (HAT ID EEPROM), 14, 15 (UART) | CONFIRMED (absent from the list above); the reason is PROBABLE (standard Pi usage, not stated in the code) |
| Reserved | `RESERVED_GPIOS = { 18: 'the slate tone' }`: always shown as taken for a new pick | CONFIRMED `ed.html:6877`, `:6878-6886` |
| Used-pin exclusion | One registry over **every** `.gpio-select` on the page, so GPIO IN and GPIO OUT rows exclude each other. A pin in use is `disabled` and labelled `GPIO n — in use (<role>)`. The row's own pin stays selectable | CONFIRMED `ed.html:6878-6898` |
| Multi-pin controls | A 3-way switch has three selects (`pin 1/2/3`). A rotary has three (`CLK`, `DT`, `BTN`). Each one claims a pin in the same registry | CONFIRMED `ed.html:3412-3426`, `:3472-3481` |
| Changing a pin | A confirm modal: "Move a button to GPIO 26? GPIO 7 will be freed up." / "Unassign … It stops responding until you give it a pin again." On cancel the old value comes back. On OK all pickers refresh and the row gets class `unassigned` if the new pin is `none` | CONFIRMED `ed.html:6906-6928`, modal `:6850-6874` |
| A row with no pin | **Silently left out of the save**: no error, the row just disappears from the file | CONFIRMED `ed.html:3691`, `:3702`, `:3713`, `:5367` |
| I2C pins | GPIO 2 and 3 are offered, although the quad rotary, OLED and Grove HAT all use bus 1 on those pins. Nothing reserves them when an I2C device is enabled | CONFIRMED (list `ed.html:6876`; bus `src/module/app/hardware_probe.py:52`) |

### 1.4 Gestures per control

The gesture sets are data, so one row widget serves every control type.

```js
// ed.html:3312-3344 (verbatim, abridged)
var BUTTON_GESTURE_SPECS = [
  { key: 'press',  field: 'press_action',        label: 'Press' },
  { key: 'single', field: 'single_click_action', label: 'Single click' },
  { key: 'double', field: 'double_click_action', label: 'Double click' },
  { key: 'triple', field: 'triple_click_action', label: 'Triple click' },
  { key: 'hold',   field: 'hold_action',         label: 'Hold' } ];
var SWITCH2_GESTURE_SPECS = [ {key:'on', field:'state_on_action', label:'On'}, {key:'off', field:'state_off_action', label:'Off'} ];
var SWITCH3_GESTURE_SPECS = [ {key:'s0', field:'state_0_action', label:'Position 1'}, ... 's2' 'Position 3' ];
var ROTARY_GESTURE_SPECS  = [ {key:'rpress', field:'__press', label:'Button press'}, {key:'rhold', field:'__hold', label:'Button hold'},
                              {key:'cw', field:'__cw', label:'Rotate CW'}, {key:'ccw', field:'__ccw', label:'Rotate CCW'} ];
var GESTURE_SPEC_SETS = { button: ..., switch2: ..., switch3: ..., rotary: ..., encoder: BUTTON_GESTURE_SPECS };
```

| Control | Gestures in the UI | What the runtime supports | Cite |
| --- | --- | --- | --- |
| Button | Press, Single, Double, Triple, Hold | the same five, plus `combined_actions` chords | CONFIRMED `ed.html:3312-3318`; `src/module/gpio_input.py:349-377`, `:477-516` |
| 2-way switch | On, Off | On/Off, and the action for the current position **also fires once at startup** | CONFIRMED `ed.html:3319-3322`; `src/module/gpio_input.py:589-611` |
| 3-way switch | Position 1-3 | position = index of the first pressed pin, `-1` if none; fires at startup | CONFIRMED `ed.html:3323-3327`; `src/module/gpio_input.py:653-686` |
| GPIO rotary encoder | Button press, Button hold, Rotate CW, Rotate CCW, plus **Reverse** and **Wrap around** toggles | the runtime also accepts single, double and triple on `button_actions`. **The UI cannot show these and drops them on save** | CONFIRMED `ed.html:3328-3333`, `:3714-3722`; schema `settings.schema.json` (`rotary_encoders.items.button_actions`) |
| Quad encoder (I2C) | Turn (a setting name), Reverse, Wrap, and the full button set | same | CONFIRMED `ed.html:3599-3669`; `src/module/i2c/quad_rotary_controller.py:24-124` |

**Gesture line mechanics** (CONFIRMED):
- Each gesture line has a `g-name-select` dropdown, so a configured command can be **re-keyed**
  to another gesture in place. Gestures already used by sibling lines are disabled in that
  dropdown (`ed.html:3173-3206`, `:3231-3259`).
- A "+ Add" select styled as a link offers the gestures not yet used. It is handled by one
  delegated listener on `#app` (`ed.html:3208-3223`, `:7212-7227`).
- Each gesture line has an `×` remove button (`ed.html:3150-3171`).
- A missing gesture is **omitted** from the JSON, except `press_action`, which is always
  written (`"None"` if absent) (`ed.html:3124-3137`).

**Timing that the UI does not show** (CONFIRMED in code; also stated in
`docs/hardware-controls.md:51-57`):

| | GPIO `SmartButton` | Quad `I2CButton` |
| --- | --- | --- |
| Press | fires immediately on press (`gpio_input.py:375`) | fires immediately on press (`quad_rotary_controller.py:43`) |
| Hold | 3 s timer (`:373`) | 3 s timer (`:44`) |
| Click evaluation | 0.5 s after release (`:406`) | 0.5 s after release (`:58`) |
| Long press that suppresses clicks | **0.5 s** (`:362`, `:394-397`) | only after the 3 s hold fires (`:76-79`, `:53`) |
| Press **and** single click both configured | both fire (press now, single 0.5 s later) | both fire |
| Auto-invert | at init, if the pin reads pressed the button is flagged `inverse` (`:310-314`) | no |
| Gating | while another GPIO button is held, this button's own actions are ignored, so chords work (`:519`, `:552-553`) | no |

PROBABLE: a 1-2 s press is "no click" on a GPIO button but a "single click" on a quad button
(derived from the two rows above). Any port should make one rule for both.

### 1.5 The action (command) dropdown

**Where the list comes from.** There are two hand-maintained copies.
- Python: `ACTION_METHODS` in `ed.py:124-212`.
- JS: `ACTION_METHODS` in `ed.html:6938-6997`.

The JS comment says "keep the two in step" (`ed.html:6930-6937`). A test checks that both
copies name real `CinePiController` methods: `_test/test_action_catalogues_agree.py:1-13`,
`:52-60` (CONFIRMED). The test's docstring records the lesson: "Two copies in exact agreement
is not evidence they are right; it is evidence they were copied." Both copies once agreed on
`set_log`, which does not exist.

**Entry shape** (verbatim):

```python
# ed.py:126-127, :184-185
{"group": "ISO", "value": "set_iso", "label": "Set ISO", "no_arg": "required",
 "arg": {"type": "select", "options": [100, 200, 400, 640, 800, 1200, 1600, 2500, 3200]}},
{"group": "Storage", "value": "format_drive", "label": "Format drive", "no_arg": "required",
 "arg": {"type": "select", "options": ["exfat", "ext4", "ntfs"]}},
```

- **Groups:** Record, ISO, Shutter, Frame rate, White balance, ClearHDR, CineMate Log,
  Thumbnail, Zoom/anamorphic, Resolution/preview, Storage, Sensor, Lens (Pinefeat), Locks,
  System. The rendering is `<optgroup>` per group, with "No action" first. CONFIRMED
  `ed.html:6938-6997`, `:7001-7036`.
- **`no_arg`** records what a blank argument does, worked out by reading each method body:
  - `cycle`: blank steps through the list.
  - `toggle`: blank inverts the flag.
  - `required`: blank raises `TypeError`. For `format_drive`, blank silently formats as exFAT.
  CONFIRMED `ed.py:105-121`; commit `d4fb2da` (2026-08-26).
- **Argument control types:**
  - `select` (with optional `suffix` such as `°`, `K`, `×`).
  - `toggle01` (offers 0/1).
  - `number` (min, max, step, placeholder, and a persistent hint "— blank cycles" or
    "— required").
  The blank option's text depends on `noArg`: "Cycle through the list", "Toggle on / off" or
  "Needs a value —". A required argument left blank gets class `needs-value`, shown in the
  danger colour. CONFIRMED `ed.html:7079-7130`.
- **Value steps:** with `cycle`, a blank argument steps through `arrays.<name>.steps`, the chips
  edited in `#steps`. The pane note says so (`resources/gui-text/07-settings-physical-controls.md:17`).
  The argument `select`'s options are a **fixed list inside the catalogue**, not the operator's
  chips. For example `set_iso` offers 100…3200 whatever `arrays.iso.steps` holds. CONFIRMED
  `ed.py:127`. PROBABLE drift risk: the chip list and the argument list can disagree.
- **Unknown methods survive:** a method in the file that is not in the catalogue is added as
  `"<name> (custom)"` and kept selected. The same rule applies to a quad `setting_name`.
  CONFIRMED `ed.html:7028-7032`, `:3636-3642`.
- **Pencil (advanced) mode:** swaps the line for a text input holding `method arg arg`. On
  change it splits on whitespace: the first word becomes the method (it **defaults to `rec`
  if empty**) and the rest become args. A list icon returns to the dropdown. CONFIRMED
  `ed.html:7168-7194` (`parts[0] || 'rec'` at `:7189`).
- **Typing of args:** `actionFromSlot` turns each whitespace-separated token into a number if
  it parses, otherwise keeps it as a string. CONFIRMED `ed.html:3103-3117`.
- **Greying:** `GET /settings-editor/api/actions` returns each entry plus `available` (whether
  the method exists on the running controller) and `greyed`/`grey_reason`. Only the Lens group
  is ever greyed, when lens control is not effective. The page reads only `greyed`; options
  stay selectable and the reason goes into the optgroup label for phones. **`available` is
  computed but never used by the page.** CONFIRMED `ed.py:1068-1105`, `ed.html:7044-7077`;
  the test's docstring says the same (`_test/test_action_catalogues_agree.py:10-12`).
- **Destructive actions bind without any guard:** `erase_drive`, `format_drive`, `reboot` and
  `safe_shutdown` are ordinary entries for a button. `/api/v1/cmd`, by contrast, blocks
  `reboot`, `shutdown`, `erase` and `format` unless `allow_destructive` is set. CONFIRMED
  `ed.py:180-185`, `:209-211`; `src/module/app/api.py:30`, `:112-114`.

### 1.6 Value-step chips: the only drag and drop

- **Markup:**
  `<div class="steplist" data-chip-path="arrays.iso.steps" data-chip-type="number" data-chip-original="[...]">`,
  holding `<span class="step-chip">100<button data-remove>×</button></span>` per value and a
  final `<input class="step-add">`. CONFIRMED `ed.html:1914-1925`.
- **Interaction:** chips are `draggable`. On `dragover` the dragged chip is inserted before
  the chip nearest the cursor's x position. Enter in the add field appends a chip. `×`
  removes one. CONFIRMED `ed.html:4893-4953`.
- **Save:** `buildState` reads chips in DOM order (`ed.html:3788-3796`). The order is "meant"
  to be the operator's: `sortChipContainer` became a no-op in `3d44e84` (2026-09-20),
  `ed.html:4887-4891`.
- **Trap:** `populateChipContainer` still **sorts numeric arrays on load** (added in `99f81c9`,
  2026-09-05, `ed.html:5121-5131`). PROBABLE consequence: a dragged order saves, but the next
  page load shows it sorted, and the next unrelated save writes it sorted. The two commits
  were never reconciled (dates from `git log -S`).
- **Free stepping:** with "free" on, the chips render as a range `lo → hi`, the middle chips
  muted, using visual order only (`ed.html:4980-5025`).
- **Not draggable:** controls, pins and gestures. Nothing in the GPIO panes is dragged.

### 1.7 Quad rotary (`#quadrotary`)

- **Markup:** a header, a hardware note, `#encodersList` and `+ Add encoder`. **Nothing
  else: no bus, no address, no "enabled" switch, no poll rate.** CONFIRMED `ed.html:2389-2399`.
- **Row** (`buildEncoderRow`, CONFIRMED `ed.html:3599-3669`):
  - A picker `None | Encoder 0..3`. Taken encoders show "— in use", and a change asks for
    confirmation (`:3556-3597`).
  - A **Turn** line: a select over `ENCODER_TURN_SETTINGS` (iso, shutter_a, fps, wb,
    resolution, zoom, shutter_a_nom, hdr_threshold_low/high, hdr_blend, hdr_gain_adder),
    plus "Nothing". Turning calls `inc_<setting>`/`dec_<setting>`; there is no free method
    choice for CW/CCW, unlike the GPIO encoder (`:3534-3553`).
  - **Reverse** and **Wrap around** toggles.
  - The push button's gestures (the full button set).
- `+ Add encoder` takes the lowest free index. With four configured it toasts "All four
  encoders are already configured". CONFIRMED `ed.html:3676-3682`.
- **Save shape:** `encoders` is a sparse object keyed `"0".."3"`. `enabled` is carried from
  the last load. An absent value becomes `true` in JS, but the loader always supplies it with
  default `false`, so the JS fallback never fires on a normal load. CONFIRMED
  `ed.html:3734-3756`, `src/module/config_loader.py:813-819`; the "never fires" part is
  PROBABLE (GET runs `load_settings`, which applies defaults, `ed.py:518-531`).
- **Server side:** `encoders` is an editor-owned subtree, taken **as sent** rather than merged,
  so a deleted encoder stays deleted. CONFIRMED `ed.py:595-597`, `:632-633`; test
  `_test/test_settings_editor_preserves_unrendered_keys.py:158`.

### 1.8 GPIO OUT (`#gpio`)

- **Rows:** `Output` pin picker (same registry) plus one line, "While rec", with a select
  `REC tally` | `REC tone`. A tone row also shows "at [Hz] Hz", one global frequency shared
  by every tone row. CONFIRMED `ed.html:5238-5306`.
- **Save:**
  - `hardware_outputs.rec_out_pin[]` (tally pins) and `hardware_outputs.rec_tone.pin[]`.
  - `frequency_hz` comes from the row field.
  - `duty_cycle` and `pwm_pin` have no field and are carried from the last load.
  CONFIRMED `ed.html:5361-5391`.
- **"Drop a frame for the relay" card** (`rec_tone.relay_drop_frames`) is shown only while
  some row is a tone row. CONFIRMED `ed.html:2415-2425`, `:5228-5236`.
- **Runtime:** tally pins are plain lgpio levels. Tone uses hardware PWM on 18/19 (the
  channel mapping differs on Pi 5) and falls back to software PWM `tx_pwm`. CONFIRMED
  `src/module/gpio_output.py:15-75`, `:79-127`.
- **Reservation:** output pins (tally + tone, or `pwm_pin` if no tone pin) are reserved, and
  inputs on them are skipped with a warning at startup. CONFIRMED
  `src/main.py:956-974`, `src/module/gpio_input.py:58-63`.

### 1.9 The I2C page (`#i2cbus`, tab "i2c hardware")

- **Content:** a list of device cards, then three clock cards (system time, RTC time, "Sync
  RTC" button). No Save: this page is diagnostic only. CONFIRMED `ed.html:2830-2866`,
  `:7265-7279`.
- **Source:** `GET /settings-editor/api/hardware` probes per request, polled every 30 s while
  the tab is open. CONFIRMED `ed.py:1725-1759`, `ed.html:7523-7546`.
- **Device table** (data, not code):
  - Grove `0x08`, quad rotary `0x49`, RTC `0x68`, all bus 1.
  - OLED `0x3C`/`0x3D`, reported as "SSD1306 or SSD1309".
  - Lens adapter `0x0d` on a camera bus.
  - CFE Hat `0x34`.
  CONFIRMED `src/module/app/hardware_probe.py:52`, `:79-106`, `:435-482`.
- **Probes:**
  - A one-byte read for most devices.
  - For the seesaw: write STATUS/HW_ID, wait 8 ms, read one byte, and accept only `0x55` or
    `0x87`.
  - When the quad driver says "connected", its answer is used (`driver-confirmed`) and no bus
    traffic is issued.
  CONFIRMED `hardware_probe.py:184-283`.
- **Card text:** each card shows `Found at 0x49 on i2c-1` or `Not found. Looked for 0x49 on
  i2c-1 (<errno hint>)`. A second line shows the driver state (connected since…, lost at…:
  error, never connected). CONFIRMED `ed.html:7320-7437`.
- **Presence dims the settings panes but keeps their values:** with no Grove, quad or OLED on
  the bus, that pane is dimmed with "These … assignments are kept and will apply when one is
  attached." CONFIRMED `ed.html:7488-7521`.
- **I2C on/off is a config.txt matter:** the `config` tab has an I2C toggle that writes
  `dtparam=i2c_arm=on` inside Cinemate's fenced block. Saving config.txt reboots.
  CONFIRMED `src/module/app/boot_config.py:92-97`, `ed.html:2752-2756`, `ed.py:924-972`.
  The installer also runs `raspi-config nonint do_i2c 0` and adds `i2c-dev` (CONFIRMED
  `cinemate-install.sh:1385-1392`).
- **No bus selection anywhere:** the pane only ever looks at bus 1 (and the camera bus for the
  lens). CONFIRMED `hardware_probe.py:52`, comment `:36-39`.

### 1.10 Potentiometers (`#pots`): a mock-up

- The eight channel `<select>`s are hardcoded HTML with **no `data-path` and no JS**. The pane
  neither reads nor writes `input_peripherals.pots`. CONFIRMED `ed.html:2268-2290`; commit
  `7de3065` body ("documented as the mock-up it is").
- The free-stepping toggles in that pane are real (`data-path`), but they sit beside fake
  channel menus.

### 1.11 Search

- **Mechanism:** case-insensitive substring match over each `.card`/`.actionrow`/`.cliprow`'s
  `data-search` attribute plus its text. Non-matches get `is-hidden`, and empty groups are
  hidden. CONFIRMED `ed.html:7955-7967`, `:7257-7264`.
- **GPIO rows** carry `data-search` such as `'button gpio'` or
  `'rotary encoder gpio clk dt'` (`ed.html:3394`, `:3509`).
- **"GPIO 13" in the placeholder** works because each pin `<option>`'s text is part of
  `textContent`. PROBABLE (derived: `card.textContent` includes option text).

### 1.12 Client-side validation (all of it)

| What is checked | How | Cite |
| --- | --- | --- |
| Pin conflicts in the editor | disabled options plus confirm | CONFIRMED `ed.html:6878-6928` |
| Encoder index conflicts | same | CONFIRMED `ed.html:3556-3597` |
| Gesture duplicates within a control | disabled options | CONFIRMED `ed.html:3231-3259` |
| Required argument left blank | red marking only; **save still allowed** | CONFIRMED `ed.html:7097` |
| Number range | HTML `min`/`max`, not enforced on save | CONFIRMED `ed.html:7116-7121` |
| Tone Hz > 0 | reverts an invalid value | CONFIRMED `ed.html:5286-5294` |
| Method name exists | **not checked** (only the advisory `greyed` flag; `available` unused) | CONFIRMED `ed.html:7060-7077` |
| JSON schema | **not used** | CONFIRMED (no validator import under `src/`) |

### 1.13 How a save is applied

```
Save -> buildState() -> PUT /settings-editor/api/settings (JSON)
     -> _merge_saved_settings(disk, payload)      dicts merge, lists/scalars replace, editor-owned subtrees replace
     -> _apply_settings_defaults(...)             setdefault fills every missing section
     -> backup to <dir>/.settings-backups/settings.jsonc.<stamp>.bak (keep 10)
     -> _render_settings(): jsonc_edit.apply_updates() rewrites only changed value spans;
        a structural change (key added/removed, array resized) falls back to json.dumps() and the
        response says comments were lost and names the backup
     -> tmp file + os.replace (atomic)
     -> threading.Timer(0.4, restart_cinemate)    systemd-run ... systemctl restart cinemate-autostart
```

- **Steps** CONFIRMED: `ed.html:5522-5552`; `ed.py:713-826` (merge `:745`, backup `:774`,
  render `:775`, replace `:781`, restart `:799-806`, message `:808-816`);
  `src/module/sensor_settings.py:53-54`, `:92-125`; `src/module/jsonc_edit.py:1-20`;
  `src/module/cinepi_controller.py:4018-4072`.
- **Not live:** controls are constructed once in `run_application()` (`ComponentInitializer`,
  `src/main.py:970-974`; quad `:1129-1133`). A change takes effect only through the full
  restart. CONFIRMED.
- **Adding or removing any GPIO row resizes an array**, which is a structural change. PROBABLE
  consequence (derived from `jsonc_edit.py:14-18`): every such save rewrites the whole file
  and loses its comments, with a message saying so.
- **Revert** (`GET /api/settings/default`) and **Upload** (`POST /api/settings/parse`, a
  JSONC parse plus defaults, no write) only fill the form. **Download** serialises
  `buildState()` client-side, as plain JSON without comments. CONFIRMED `ed.html:5555-5617`,
  `ed.py:534-561`.
- **The client also merges:** `buildState()` starts from a deep copy of the last loaded
  settings, so keys with no control travel with the save. CONFIRMED `ed.html:3758-3773`.

### 1.14 Raw / advanced editing, as it really exists

| Surface | Edits? | Validation | Apply | Cite |
| --- | --- | --- | --- | --- |
| Settings page drawer (button `settings.jsonc`, tabs `settings.jsonc`/`config.txt`) | **No**: a read-only `<pre>` showing `JSON.stringify(buildState())` (what Save would write, without comments), plus Copy. Can highlight a line | n/a | n/a | CONFIRMED `ed.html:2996-3012`, `:4609-4613`, `:6757-6811` |
| Per-gesture pencil | one action as `method args` free text | none | with Save | CONFIRMED `ed.html:7168-7194` |
| Upload a file | whole file, form-filled | server JSONC parse plus defaults | with Save | CONFIRMED `ed.py:544-561` |
| `editsettings` shell alias | `sudo nano /home/pi/cinemate/settings.jsonc` | at next start, `load_settings` raises `SettingsLoadError` with line, column and context | restart | CONFIRMED `docs/installation-steps.md:673`; `src/module/config_loader.py:958-1018` |
| Recovery console `:8080/edit/settings` (own root service, stdlib only, survives a broken Cinemate) | full textarea | ladder: rung 1 runs Cinemate's own `load_settings` in a subprocess; rung 2 is a JSONC parse; rung 3 writes "UNVALIDATED" (fail open) | Save, or Save and restart; backup first | CONFIRMED `services/cinemate-recovery/cinemate-recovery.py:1-27`, `:364-458`, `:952-967`, `:1037-1060` |
| Recovery console `/edit/config` (config.txt) | textarea, off unless `system.recovery.allow_config_txt` | — | "Save and arm revert": unconfirmed within `config_confirm_timeout_s` (300 s), it restores the backup and reboots | CONFIRMED `cinemate-recovery.py:72-82`, `:468-545`, `:969-995` |

---

## 2. Backend

### 2.1 The config file

| Item | Value | Cite |
| --- | --- | --- |
| Path | `/home/pi/cinemate/settings.jsonc` (one constant, `DEFAULT_SETTINGS_PATH`; the recovery console keeps its own copy on purpose) | CONFIRMED `src/module/config_loader.py:10-17`; `cinemate-recovery.py:65` |
| Relation to git | the repo is cloned to `/home/pi/cinemate`, so the **live file is the git-tracked `settings.jsonc`** at the repo root. Per-sensor `settings_*.jsonc` and `.settings-backups/` are git-ignored | CONFIRMED `git ls-files settings.jsonc`; `.gitignore:209-216`, `:234` |
| Format | JSONC: `//` and `/* */` comments, trailing commas; length-preserving strip so errors keep line and column | CONFIRMED `src/module/config_loader.py:948-956` |
| Stock template | `resources/settings/settings_default.jsonc` (Revert and the fallback when the file is missing); `settings_komodo.jsonc` is a partial example rig | CONFIRMED `ed.py:81-85`; `resources/settings/settings_komodo.jsonc:1-12` |
| Schema | `settings.schema.json`, `additionalProperties:false` throughout; referenced by `"$schema"` and by tests only | CONFIRMED `resources/settings/settings_default.jsonc:2`; HB `working/changing-a-control.md:57-61` |
| Sections (since `2fcdcc3`, 2026-08-16) | `hardware_controls` (direct GPIO inputs), `input_peripherals` (pots, `quad_rotary_controller`), `hardware_outputs` (direct GPIO outputs), `output_peripherals` (OLED) | CONFIRMED commit `2fcdcc3` message; `config_loader.py:801-841` |

**A real example** (verbatim, `resources/settings/settings_default.jsonc:225-331`, abridged
with `…`):

```jsonc
"hardware_controls": {
  "buttons": [
    { "pin": 7,  "pull_up": true,  "debounce_time": 0.1, "press_action": { "method": "rec" } },
    { "pin": 10, "pull_up": true,  "debounce_time": 0.1, "press_action": { "method": "rec" } },
    { "pin": 13, "pull_up": false, "debounce_time": 0.1,
      "press_action": "None",
      "single_click_action": { "method": "set_resolution" },
      "double_click_action": { "method": "restart_cinemate" },
      "triple_click_action": { "method": "reboot" },
      "hold_action": { "method": "toggle_mount" } }
  ],
  "two_way_switches": [
    { "pin": 24, "state_on_action": { "method": "set_zoom", "args": [2] },
                 "state_off_action": { "method": "set_zoom", "args": [1] } }, …
  ],
  "rotary_encoders": [
    { "enabled": true, "clk_pin": 9, "dt_pin": 11, "button_pin": 10,
      "pull_up": true, "debounce_time": 0.05,
      "button_actions":  { "press_action": { "method": "set_iso_lock" }, "hold_action": "None" },
      "encoder_actions": { "rotate_clockwise": { "method": "inc_iso" },
                           "rotate_counterclockwise": { "method": "dec_iso" } } }
  ]
},
"input_peripherals": {
  "pots": [ { "channel": "None", "setting": "iso" }, … ],
  "quad_rotary_controller": {
    "enabled": true,
    "encoders": {
      "0": { "setting_name": "iso", "button": { "press_action": { "method": "set_zoom" },
                                                "hold_action": { "method": "safe_shutdown" } } },
      "3": { "setting_name": "wb",  "button": { "press_action": "None",
                                                "single_click_action": { "method": "set_resolution" }, … } }
    }
  }
},
"hardware_outputs": {
  "rec_out_pin": [21],
  "rec_tone": { "pin": [18], "frequency_hz": 1000, "duty_cycle": 50, "relay_drop_frames": false }
}
```

A `combined_actions` entry exists only in the Komodo example (verbatim,
`resources/settings/settings_komodo.jsonc:103-110`):

```jsonc
"combined_actions": [ { "hold_button_pin": 24, "action_button_pin": 26,
                        "action_type": "press", "action": { "method": "set_resolution" } } ]
```

**The action value grammar** (schema `definitions.action`, CONFIRMED in
`settings.schema.json`) is either the string `"None"`/`"none"` or
`{ "method": "<CinePiController method>", "args": [ … ] }`.

**The live file and the stock file both carry the GPIO10 collision:** button `pin: 10`
alongside an enabled encoder `button_pin: 10`. CONFIRMED `settings.jsonc:487`, `:520`, `:523`;
`resources/settings/settings_default.jsonc:234`, `:264`, `:267`. The comment above the
encoder in `settings.jsonc` still says it ships `"enabled": false`, which is no longer true
(CONFIRMED `settings.jsonc:515-520`). See 3.1.

### 2.2 Who writes the file

| Writer | How | Cite |
| --- | --- | --- |
| Web settings editor | PUT, merged, defaults filled, surgical or full rewrite, backup, restart | CONFIRMED §1.13 |
| Per-sensor save | writes `settings_<camera>.jsonc` and deletes the camera's legacy entries from `settings.jsonc` | CONFIRMED `ed.py:751-770` |
| Recovery console | raw text, ladder-validated, backup | CONFIRMED `cinemate-recovery.py:1037-1060` |
| Operator | `editsettings` (nano) | CONFIRMED `docs/installation-steps.md:673` |
| Git | `git pull` on the camera updates the tracked file | PROBABLE (derived: tracked file at the live path) |

### 2.3 Defaults and migration

- **`_apply_settings_defaults()`** uses `setdefault` for every section the code uses.
  CONFIRMED `config_loader.py:801-830`:
  - empty lists for `buttons`, `two_way_switches`, `three_way_switches`,
    `rotary_encoders` and `combined_actions`;
  - `quad_rotary_controller {enabled:false, encoders:{}}`;
  - `pwm_pin 19`, `rec_out_pin [6,21]`;
  - `rec_tone {pin:[], frequency_hz:1000, duty_cycle:50, relay_drop_frames:false}`.
- **Default clash, `rec_out_pin`:** the loader defaults to `[6,21]` while the stock file
  holds `[21]` (`settings_default.jsonc:324`). CONFIRMED. PROBABLE consequence: deleting the
  key by hand brings back pin 6.
- **Legacy key migration:** `rec_tone_config()` reads the nested `rec_tone` and falls back to
  the pre-`c171975e` flat keys `rec_tone_pin` etc. This exists because the rename was missed
  in `main.py` for weeks: every tone setting silently used its hardcoded default. CONFIRMED
  `config_loader.py:446-475`; commit `d6a9e14`.
- **The schema restructures broke files twice** (`c171975` 8 sections, `2fcdcc3` 10
  sections, both marked `!` = breaking). CONFIRMED commit subjects (git log on
  `gpio_input.py`).
- **Missing file:** `load_settings` logs a warning and uses built-in defaults. **Unparseable
  file:** raises `SettingsLoadError` with line, column, context and a recommended fix.
  CONFIRMED `config_loader.py:958-1018`.

### 2.4 Validation that does exist (all at startup or in tests)

| Check | When | Effect | Cite |
| --- | --- | --- | --- |
| Duplicate input pins | startup, `ComponentInitializer._claim_pin` | the later claimant is **skipped** with a warning naming both entries; multi-pin controls claim all or nothing | CONFIRMED `gpio_input.py:32-49`, `:117-138`, `:166-182`; commit `5912cc4` |
| Input on a reserved output pin | startup | skipped with a warning | CONFIRMED `gpio_input.py:58-63`, `:97-102`, `:203-208` |
| Quad `setting_name` | constructor | `parameters.get(name, source=…)` logs a WARNING for an unknown name | CONFIRMED `quad_rotary_controller.py:136-139`; commit `74c33ec` |
| `"method"` strings in the **shipped** files | CI test | fails with path and name | CONFIRMED HB `orientation/the-traps.md:36-48`; `_test/test_settings_method_names_resolve.py:1-36` |
| Editor catalogue against the controller | CI test | fails | CONFIRMED `_test/test_action_catalogues_agree.py` |
| The operator's own file on a camera | **never** | a typo is a silent no-op button (an error log line at press time) | CONFIRMED HB `orientation/the-traps.md:43-48`; `gpio_input.py:548-549` |

### 2.5 How methods are resolved and called

- **Dispatch is `getattr(controller, name)(*args)`**, with the args list from JSON as given
  (numbers stay numbers, strings stay strings). No arity check, no type coercion, no lock.
  CONFIRMED:
  - `gpio_input.py:536-547` (SmartButton);
  - `:616-627` (SimpleSwitch);
  - `:668-675` (ThreeWaySwitch);
  - `:711-735` (RotaryEncoder);
  - `quad_rotary_controller.py:109-124` (I2CButton).
- **`wrap` keyword:** passed only if the method's signature declares `wrap` (`inspect`).
  Otherwise, if wrap is on, an info log line. CONFIRMED `gpio_input.py:721-735`,
  `quad_rotary_controller.py:309-330`; commit `0604e02`.
- **Quad Turn:** resolves `inc_<setting>`/`dec_<setting>` by name. CONFIRMED
  `quad_rotary_controller.py:309-313`.
- **No-op strings:** `""`, `none`, `null` (any case) on SmartButton and I2CButton. **Not on
  SimpleSwitch, ThreeWaySwitch or RotaryEncoder**, which call `.get` on the value (see 3.3).
  CONFIRMED `gpio_input.py:556-567` against `:617-619`, `:670-671`, `:712-714`.
- **Error handling per class:**
  - SmartButton catches only `TypeError` and logs "does not support the provided args"
    (`gpio_input.py:542-547`). The hold path catches nothing (`:333-341`).
  - I2CButton catches every exception (`quad_rotary_controller.py:117-122`).
  - RotaryEncoder and ThreeWaySwitch catch nothing (`gpio_input.py:672-673`, `:735`).
  CONFIRMED.
- **Two namespaces exist for the same actions.** GPIO and the quad board use **controller
  method names** (`set_iso`). The CLI, serial and `/api/v1/cmd` use a **command table** of
  spaced words (`"set iso"` → `set_iso`, typed `int`). Different table, different argument
  coercion. CONFIRMED `src/module/cli_commands.py:47-120`, `:223-345`.
- **GPIO bypasses the dispatch lock.** CLI, serial and HTTP serialise on
  `CommandExecutor._dispatch_lock`; GPIO, encoders, pots and the quad board do not. Already a
  hardware-confirmed failure (F-285: a moving pot starved CLI `set iso`). CONFIRMED HB
  `orientation/the-traps.md:19-27`; `cli_commands.py:31`, `:310-345`.
- **The editor's own comment is wrong.** It calls `/api/v1/cmd` "the same dispatcher as the
  CLI, serial and GPIO paths" (`ed.html:3031-3032`), but GPIO does not use it. CONFIRMED by
  the two citations above.

### 2.6 Runtime classes, summarised

| Class | Library | Notable | Cite |
| --- | --- | --- | --- |
| `ComponentInitializer` | — | built once at startup; order is buttons, then 2-way, then 3-way, then encoders, so an earlier type wins a pin conflict; a disabled encoder (`enabled:false`) is skipped | CONFIRMED `gpio_input.py:51-229` |
| `SmartButton` | gpiozero `Button(pin, pull_up, bounce_time)` | timings and gating in §1.4; `combined_actions` evaluated on every press and release | CONFIRMED `gpio_input.py:272-567` |
| `SimpleSwitch` | gpiozero `Button`, **pull_up=True, debounce 0.1, both fixed** (the config cannot set them) | sleeps 0.5 s at init, then fires the current state's action | CONFIRMED `gpio_input.py:568-611`, call site `:114-116` |
| `ThreeWaySwitch` | `Button(pin, pull_up=None, active_state=False)`, which needs external pull resistors | position `-1` when no pin is active | CONFIRMED `gpio_input.py:652-686`; "external pulls" PROBABLE (gpiozero semantics of `pull_up=None`) |
| `RotaryEncoder` | gpiozero `RotaryEncoder(a=clk, b=dt)` | Reverse swaps the two handlers | CONFIRMED `gpio_input.py:688-743` |
| `QuadRotaryController` | Blinka `busio.I2C(board.SCL, board.SDA)`, seesaw at **`0x49` hardcoded**, `reset=False`; encoders 0-3; switches on seesaw pins `(12,14,17,9)`; NeoPixel pin 18 × 4 | a 10 Hz thread; reconnects every 5 s only if it was ever connected; logs a never-present board once; ignores turns and presses while `controller.startup`; **calls `inc_`/`dec_` once per poll whatever the detent count** | CONFIRMED `quad_rotary_controller.py:127-341` (once-per-poll: `:277-283`, `:313-320`) |
| `GPIOOutput` + `rpi_gpio_wrapper` | `lgpio.gpiochip_open(0)`; tone uses `rpi_hardware_pwm` on 18/19 or `tx_pwm` | channel 2/3 on Pi 5, 0/1 on older boards | CONFIRMED `src/module/rpi_gpio_wrapper.py:24-28`; `gpio_output.py:30-61` |

### 2.7 `/api/v1/cmd` and `events.py`

- **`/api/v1/cmd`** (GET `?c=` or POST text/plain), CONFIRMED
  `src/module/app/api.py:84-122`, `:153-169`:
  - optional `X-Cinemate-Token`;
  - blocks `reboot`/`shutdown`/`erase`/`format` unless `allow_destructive`;
  - per-client rate limit;
  - then `CommandExecutor.handle_received_data(line)`;
  - responses `ok …` / `err unknown command|bad argument|missing argument|busy|blocked`;
  - `/api/v1/commands` lists the table with argument types.
- **The editor and the API token:** the editor uses `/api/v1/cmd` only for live commands
  (`apiCmd`, `ed.html:3033-3040`), and embeds the token into the page HTML (`ed.py:442`). The
  editor blueprint itself has **no auth** (no `before_request` in `ed.py`, grep): anyone on
  the hotspot can save settings, which restarts the camera. CONFIRMED.
- **`events.py`** is Socket.IO push only: an initial snapshot and Redis-change fan-out. It has
  no control handlers ("Control moved to POST /api/v1/cmd"). The effects of GPIO actions reach
  browsers only through Redis changes. CONFIRMED `src/module/app/main/events.py:6-13`,
  `:127-160`, `:167-172`.

---

## 3. Lessons from history

### 3.1 From git (`git -C cinemate log` on the files above)

| Commit (date) | What broke or changed | Lesson for a port |
| --- | --- | --- |
| `14b4958` (2026-08-25) B11.5 | The GPIO panes were fixed HTML for 3 buttons and 2 switches. Edits to `hardware_controls`/quad/outputs **never saved** (overwritten from the last load). `pwm_pin`/`rec_out_pin`/`rec_tone.pin` had no `data-path`, so the defaults reset them on every save. A `"None"` action round-tripped as `rec`. Buttons always saved `pull_up=true` | Build rows generically from data. Round-trip-test every key, including "no action". |
| `d4fb2da` (2026-08-26) | The blank-argument label "(none — toggle)" was wrong for 15 of 28 commands. `format_drive` with a blank argument formats as exFAT | Give each method an explicit `no_arg` semantic; mark required arguments. |
| `c06da0a` (2026-08-26) | Gesture re-key dropdown, "+ Add", quad rows rebuilt dynamically, `inc_resolution`/`dec_resolution` added so an encoder can cycle modes | The row and gesture model as it stands today. |
| `5912cc4` (2026-08-29) | Two entries on GPIO10 aborted startup with `GPIOPinInUse`, naming neither entry. Triggered by a **one-click editor toggle** | Detect conflicts in the editor **and** in the loader; name both claimants; skip rather than crash. |
| HB `lessons/hardware-log.md:893-935` | The same save also turned `log_encode: false` into the string `"true"`/`"false"` because the control was typed `string` | Type every field. |
| HB `lessons/hardware-log.md:1393-1416` | The GPIO10 collision became **live in the stock config** after a rig port (`a80bfbb9`). The skip path is desk-verified only | Stock configs need the same conflict check as user configs. |
| `7de3065` (2026-09-15) | The page **was** the file: any key without a control was dropped on save, which turned 12-bit ClearHDR back on. Fixed with a server merge plus client seeding. Quad `enabled:true` had been hardcoded | A page is a view of the file; merge on save; carry unknown keys; list editor-owned subtrees explicitly. |
| `e11dd68` (2026-08-23) | Every save deleted all 75 comments. Fixed with a surgical span rewrite; a structural change still loses them, **and says so** | Keep hand-written comments; never lose them silently. |
| `d6a9e14` (2026-09-02) | After a key rename, `main.py` read the old flat keys, so the tone pin, frequency and relay setting had never worked. `[hidden]` was beaten by an author `display` rule | Readers and writers of a key must move together; test at the consumer. |
| `9113e73` (2026-09-05) | Tone pitch moved into the row; `duty_cycle` lost its field, so it is now carried through | Every key without a field must be carried through explicitly. |
| `0e3246a` (2026-09-05) | An absent quad board was re-probed every 5 s forever, flooding the log | Log absence once; retry only for a board that was seen. |
| `fb2ef16` (2026-09-20) | The reconnect leaked an `busio.I2C` handle per attempt; `reset=True` reset a live board; driver state exposed as `state()` | Expose driver state for the UI; do not reset a live device. |
| `d66c91f` (2026-09-20) | A missing `import contextlib` made every reconnect raise `NameError`, so a dropped board never came back. Caught by a test that had been failing on `dev` | Run the tests. |
| `0604e02` (2026-09-20) | Reverse/Wrap added. Wrap goes only to methods declaring `wrap`. wb/zoom/resolution **now clamp** on an encoder with Wrap off (a behaviour change scoped to that encoder) | Per-encoder options; signature-checked kwargs. |
| HB `lessons/hardware-log.md:3253-3299` and `working/probing-i2c-peripherals.md:12-24` | The I2C pane called a working seesaw "missing" about half the time: a bare receive-byte NACKs, so use a register read and require a known HW id (`0x55`/`0x87`) | Probe a seesaw by register read; prefer the driver's own state; report provenance. |
| `5d90696` (2026-10-05) | Lens actions are greyed with a reason but stay assignable (a rig is wired before the adapter arrives) | Advisory greying, never removal. |

### 3.2 From the handbook

- **Adding a controller method** means five edits: method, CLI table, **both** editor
  catalogues, docs, settings strings. A forgotten one is a silent no-op button. CONFIRMED HB
  `working/changing-a-control.md:21-53`.
- **Traps:**
  - Two dispatch paths, only one serialised (#2).
  - Actions are dispatched by name, so a typo is silence (#3); the operator's own file is
    never checked.
  CONFIRMED HB `orientation/the-traps.md:19-48`.
- **Probing peripherals:**
  - Never use a driver's init to probe; drivers are not reachable from requests anyway.
  - Scope the bus: `0x34` is the CFE hat on bus 1 but the StarlightEye IR-cut filter on the
    camera buses.
  - Report provenance (probed, configured, driver).
  - Act-then-verify for RTC sync.
  CONFIRMED HB `working/probing-i2c-peripherals.md:46-63`, `:83-99`, `:101-122`, `:128-138`.
- **Lesson:** "The cheapest primitive can fail to ask the question at all." CONFIRMED HB
  `lessons/what-the-pi-taught-us.md:245-257`.

### 3.3 Defects found while reading for this report (none recorded in the handbook)

| # | Defect | Evidence | Label |
| --- | --- | --- | --- |
| D1 | **The editor writes `"None"` where three handlers expect a dict.** `actionFromSlot` returns `"None"` for an empty or removed gesture. A new 2-way switch saves `state_on/off_action: "None"`. The GPIO encoder always writes all four keys. `SimpleSwitch.execute_action("None")`, `RotaryEncoder._dispatch("None")` and `ThreeWaySwitch.on_switch_change` all raise `AttributeError: 'str' object has no attribute 'get'`. SmartButton handles it correctly | `ed.html:3103-3107`, `:3407`, `:3698`, `:3719-3720`; `gpio_input.py:617-619`, `:670-671`, `:712-714`. SIM: stubbed gpiozero, `SimpleSwitch(..., {"state_off_action":"None"})` raised at construction; RotaryEncoder CCW and ThreeWaySwitch raised the same; SmartButton was fine | Handler crash CONFIRMED (SIM). **Boot crash** PROBABLE: SimpleSwitch fires its startup state in `__init__`, which runs inside `ComponentInitializer` with no try (`src/main.py:970`), and `main()` reports "CineMate crashed during startup" (`src/main.py:1320-1329`); and the editor would then be down too, because `create_app` runs after it (`src/main.py:1138`) |
| D2 | **A pure pin remap does not enable Save.** The pin-change confirm callback refreshes the pickers and the drawer but never calls `markDirty` (the encoder picker does). Pin selects have no `data-path`, so the generic dirty listener skips them | `ed.html:6916-6924` vs `:3585-3592`; listener `:4746-4749`; Save disabled while `dirtyEls` is empty `:4617-4626` | PROBABLE |
| D3 | **Pins outside `GPIO_PINS` vanish on save.** Komodo's encoder uses `button_pin: 1`. The picker has no option for 1, so the browser selects `None`; save then omits `button_pin` (and drops a button or switch row entirely) | `resources/settings/settings_komodo.jsonc:88`; `ed.html:6887-6898`, `:3722`, `:3691` | PROBABLE (HTML select falls back to the first option when none is `selected`) |
| D4 | **The GPIO encoder loses `pull_up`, `debounce_time`, `enabled` and single/double/triple** on any save. The builder hardcodes `enabled:true, pull_up:true, debounce_time:0.05` and writes only press/hold. Buttons carry `pull_up`/`debounce` through `data-` attributes; encoders do not. Komodo's `pull_up:false` would flip; a disabled encoder would be re-enabled, which is the GPIO10 crash path | `ed.html:3713-3722` vs `:3395-3399`; `settings_komodo.jsonc:55-60` | CONFIRMED (code); consequence PROBABLE |
| D5 | **Numeric chip drag order is undone on the next load** | §1.6 | PROBABLE |
| D6 | **The quad driver applies one step per 100 ms poll whatever the size of the turn** (`change` is used only for its sign), so a fast spin loses detents | `quad_rotary_controller.py:277-283`, `:313-320`, `:341` | CONFIRMED (code); consequence PROBABLE |
| D7 | The pencil field defaults an empty method to `rec` | `ed.html:7189` | CONFIRMED |
| D8 | Loader default `rec_out_pin [6,21]` vs stock `[21]` | §2.3 | CONFIRMED |

---

## 4. What is worth porting and what is Cinemate-specific

### 4.1 Worth porting (concepts), with an Apertar-style note

Apertar's side is only glanced at here: its hardware file is INI-style
`~/apertar-hardware.conf` with sections such as `[gpio]`/`[gpio_buttons]`,
`[pcf8574]`/`[pcf8574_buttons]`, `[neorotary4]`, `[recording_indicator]` and
`[cfexpress_hat]`. CONFIRMED (section names only):
- Core `src/hardware/GpioInput.cpp:407`;
- Core `Pcf8574Input.cpp:346`;
- Core `NeoRotary4Input.cpp:383`;
- Core `RecordingIndicatorOutput.cpp:293`, `:317`;
- Core `src/ApertarCoreApp.cpp:3440-3442`;
- Core `src/hardware/ButtonActionList.hpp:1-121` (Apertar actions are tokens, at most 6 per
  button).

The notes column below is PROBABLE design guidance derived from this report, not a verified
fact about Apertar.

| Cinemate idea | Where | Port note |
| --- | --- | --- |
| One row per physical control: pin picker, then gesture lines (gesture select, command select, argument, pencil) | §1.2-1.5 | The core of "the easy dropdown". Gesture sets as data (`GESTURE_SPEC_SETS`) generalise to PCF8574 channels and NeoRotary channels. |
| One occupancy registry for every pin picker on the page, plus confirm-to-remap | §1.3 | Extend the registry key to `(chip, line)`: Pi GPIO, each PCF8574 at each address, each NeoRotary channel. Reserve GPIO 2/3 while an I2C device is enabled on bus 1, and the DPI pins while DPI overlays are active. |
| Action catalogue with `group`, `label`, `no_arg`, `arg` spec; unknown names kept as "(custom)" | §1.5 | Generate it from **one** source (the Apertar API) instead of two hand copies; use an `available` flag for real (Cinemate computes it and ignores it). |
| Advisory greying with a reason (option stays selectable) | §1.5 | Same for actions whose hardware is absent. |
| Page = view of the file: client seeds from the last load, server merges over disk, editor-owned subtrees listed | §1.13 | Essential once a **system-controlled file** has hand-editable parts: unknown keys and comments must survive. |
| Comment-preserving rewrite; say so out loud if impossible; backup with retention; atomic replace | §1.13 | Apertar's INI is line-oriented, so a span rewrite is easier than JSONC. |
| Startup guards: duplicate pins skipped naming both entries; reserved outputs; unknown names logged | §2.4 | Put the same check in the editor (block Save) **and** in Core's loader (skip, never crash). |
| Recovery console raw editor: ladder validation using the real loader, backup, optional restart, confirm-or-revert for boot files | §1.14 | The model for "manual editing for advanced users": an editable raw view, validated server-side by the same parser Core uses. Per house rules Patrik edits `config.txt` himself, so only the settings half applies. |
| Hardware page: presence per device with provenance (probed / driver / configured), seesaw register-read probe, absent hardware dims settings but keeps them | §1.9 | Directly relevant to the NeoRotary/CFE case. Add what Cinemate lacks: a bus column, a list of existing `/dev/i2c-*`, and a "bus missing" diagnosis (KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §3.2). |
| `no_arg` semantics, required-argument marking | §1.5 | Applies to any Apertar action with a parameter. |
| Gesture grammar Press/Single/Double/Triple/Hold, plus Reverse/Wrap per encoder | §1.4 | Unify the two timing models Cinemate has (GPIO 0.5 s long press vs quad 3 s), and show the timings in the UI. |

### 4.2 Cinemate-specific (do not port as is)

| Item | Why |
| --- | --- |
| `CinePiController` method names as the action vocabulary, and the CLI's second namespace | Apertar has its own API and action tokens (`ButtonActionList.hpp`). Port the **shape**, not the names. |
| One giant `settings.jsonc` that is also the git-tracked repo file | A system file should not live in the source tree. |
| Flask/Jinja page, `t()` copy from `resources/gui-text/*.md`, the 8300-line single template | Implementation detail. The external copy file is a nice idea but optional. |
| Restart-whole-app-to-apply via `systemd-run` | Apertar may be able to reload only the hardware inputs. Decide separately. |
| Grove pots pane | A mock-up even in Cinemate. |
| `rec_tone` PWM on 18/19, `pwm_pin`, OLED | Cinemate hardware. Apertar has `RecordingIndicatorOutput`/`TriggerOutput` instead. |
| Quad rotary hardcoded to bus 1 / `0x49`, polled at 10 Hz with no options | This is **the gap** for Patrik's fix. Apertar's `[neorotary4] enabled bus address` (and `poll_ms`, KB source §5) already go further. The editor must expose those, not copy Cinemate. |
| Editor without auth, API token embedded in the page | Do not copy. |
| `combined_actions` with no UI | Either give it a UI or leave it out. |

### 4.3 What Patrik's fix needs that Cinemate never had (PROBABLE, derived from §1.7, §1.9, §2.6 and KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §3-§5)

1. Per-device **bus** and **address** fields (`[cfexpress_hat] bus=1`,
   `[neorotary4] enabled=true bus=1 address=0x49`), with the bus chosen from the buses that
   actually exist.
2. A diagnosis of **why a bus is missing**: `/dev/i2c-1` absent while GPIO 2/3 are DPI
   functions. Report it as text for Patrik to act on in config.txt; never write it.
3. A seesaw HW-id probe on the configured bus and address (Cinemate's
   `_seesaw_present`, `hardware_probe.py:208-242`, is the reference), shown next to the
   driver's own connected state.
4. A two-masters warning when the hat answers on two buses (KB source §4 step 4).

---

## 5. Open points (UNCONFIRMED)

- Whether D1 crashes a real camera at boot. It needs a Pi with a 2-way switch saved from the
  editor with an empty side, in that position at boot.
- Whether the GPIO10 skip path boots clean on hardware (HB says desk-verified only,
  `lessons/hardware-log.md:1405-1412`).
- Whether the seesaw NACK rate is contention with the driver's 10 Hz polling or intrinsic
  (HB `lessons/hardware-log.md:3291-3294`).
- `lgpio.gpiochip_open(0)` on the Pi 5 kernel in use (`rpi_gpio_wrapper.py:27`): not checked
  against the Apertar image.
