# R4: what the KB knows about Patrik's hardware, the I2C/NeoRotary fix, and controls

Reader report for the controls project ("port the GPIO dropdown and method assigning from Cinemate, Apertar style, with the
Apertar API; a system-controlled config file; the I2C hardware Apertar uses; the I2C channel settings Patrik's NeoRotary fix
needed; dropdown/drag-and-drop for most users and manual editing for advanced users").

Read only. Nothing in the KB, the code trees or Cinemate was edited. The only file written is this one.

## Citation key and labels

All KB paths are relative to `/home/user/apertar-kb` and pinned **@a08da9a** (KB HEAD, clean tree). Abbreviations:

| Short | KB file |
| --- | --- |
| `SRC` | `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` |
| `HL` | `lessons/hardware-log.md` |
| `UPI` | `lessons/upstream-issues.md` (`UPI#n` = row n) |
| `CFN` / `CPN` / `UIN` / `CIN` | `sources/research-2026-10-25/{config-files,core-control-plane,ui-structure,core-internals}-notes.md` |
| `FLOWS` / `REC` / `CMAP` / `UMAP` / `TUT` / `LLM` | `llm/{flows,change-recipes,core-map,ui-map,tutoring,README}.md` |
| `A-CONF` / `A-CORE` / `A-UI` / `A-OV` / `A-DRV` | `architecture/{config,core,ui,overview,drivers}.md` |
| `TIDX` | `tutorials/README.md` |
| `CL` | `working/cinemate-lessons.md` |

Code citations: `Core:` = Apertar Core tree at **@eb9cc39**, `UI:` = Apertar UI tree at **@d8098d0**, `Cm:` = Cinemate at
**@d6cc93e**. The KB's own code refs are against `upstream-1.6.0` (`LLM:53-58`); where I re-opened a line at the tips I say so.

Labels:
- **CONFIRMED** = I opened the cited line. For a KB citation that means "the KB records this"; if the KB itself marks the
  claim probable/unconfirmed, I repeat the KB's status in the text.
- **CONFIRMED@tip** = I also opened the code line at the tip named above.
- **PROBABLE** = derived; the derivation is stated.
- **UNCONFIRMED** = not established in the KB (or anywhere I read); the settling command is given where possible.

Sibling reports already in the KB cover the code side in depth: `working/controls/r1-cinemate-gpio.md` (Cinemate editor) and
`working/controls/r2-apertar-core-hw.md` (Core readers at eb9cc39). This report is the KB view and does not repeat them.

---

## 0. The short version

1. **Patrik's rig** (KB, 2026-10-23 to 10-27): Pi 5 4 GB, Apertar-Beta 1.6.0, IMX585 StarlightEye on cam0 (i2c-10, 0x1a),
   RPI5-CFE-Hat (MCU 0x34, now on **i2c-1**), NeoRotary 4 seesaw (0x49, **i2c-1**, chained off the hat's Qwiic hub), TMP117
   (0x48) and an IMU (0x68) on i2c-10, HDMI display with the DPI overlays commented out, tally LED on GPIO 21, GPIO buttons
   on d10/d6, Pi 5 power button. No PCF8574, no INA219 (its default `/dev/i2c-4` does not exist). CONFIRMED (§1.1).
2. **The fix** was: comment out `config.txt` lines 76-78 (three DPI overlays that held GPIO 0-27), reboot, then
   `[cfexpress_hat] bus=1` and `[neorotary4] enabled=true bus=1 address=0x49`, restart Core/UI/automounter; side effect fixed
   in `[display]`. CONFIRMED (`SRC:122-143`, `HL:19-34`). Every diagnostic step can be done read-only by software; the two
   steps that change the system (`config.txt`, reboot) are Patrik-only by house rule (§2).
3. **Open** (KB): how the hat reached i2c-10, where the IMU is wired, which overlay gives `/dev/i2c-4`, whether JP3/JP4
   bridge buses after the fix (`SRC:173-177`, `SRC:132`). I add two the KB does not list: what else answers at 0x34 on bus 10
   (the StarlightEye also carries a CH32V003), and whether 0x68 is really the MPU6050 (§3).
4. **Constraints** (§4): M4 "read once" (each process parses the file at its own start; no reload), M5 "copies" (three
   action normalisers, three templates, three value-list copies, hardware-action names in Core and QML), Patrik-only
   `config.txt`/sudo/reboots/restarts, `/boot` copies of the config are dead, four unlocked writers, no WebUI auth, driver
   errors only in the journal, and the "a default is a claim" lesson from Cinemate.
5. **KB drift found while reading** (§5): `A-CONF:114` says Core's C++ never reads `[cfexpress_hat]`; at eb9cc39 it does
   (`Core:src/ApertarCoreApp.cpp:4552`, `:9310`). The hat bit-0 polarity `A-CORE:496` calls unconfirmed was settled on
   hardware (`HL:335-337`, `:346-349`). Two KB pages disagree on whether `pi` can read the journal.

---

## 1. Inventory

### 1.1 Patrik's rig (as the KB records it)

| # | Device | Interface / bus | Address / pins | Config (`~/apertar-hardware.conf` unless noted) | Status | Label, cite |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Raspberry Pi 5, 4 GB | — | — | `config.txt` `[pi5]`, `dtparam=pciex1` | working | CONFIRMED `SRC:20`, `HL:66` (4 GB, kernel 6.12.75+rpt-rpi-2712) |
| 2 | Apertar-Beta 1.6.0 image on Raspberry Pi OS Trixie | — | — | — | — | CONFIRMED `SRC:21`, `HL:21` |
| 3 | IMX585 sensor on the StarlightEye camera board | CSI cam0; I2C **i2c-10** (RP1 DesignWare, `i2c_csi_dsi0`) | `0x1a` (`UU`, held by the driver) | `config.txt:42` `dtoverlay=imx585,cam0,link-frequency=891000000` | working | CONFIRMED `SRC:22`, `:36`, `:52`, `:77`; `A-DRV:114` |
| 4 | TMP117 temperature sensor (on the StarlightEye) | i2c-10 | `0x48` | none | present, not read by Apertar | CONFIRMED `SRC:77`, `:82`, `:169`. "Not read": PROBABLE (no KB page names a TMP117 reader; grep of the KB for `0x48` finds only `SRC` and `A-CORE:461`) |
| 5 | StarlightEye IR-filter controller (CH32V003) | not recorded | not recorded | none | unknown | CONFIRMED that the KB names it, `SRC:182`; address UNCONFIRMED (see §3, Q4) |
| 6 | RPI5-CFE-Hat controller (CH32V003, schematic symbol says STM8S003F3P) | **before**: i2c-10; **after the fix**: **i2c-1** through the hat's 2x3 header `J5` and the `TCA9406` translator | `0x34`. Status byte: bit 0 = 1 card out, `0x02` with the card seated; two buttons (bit 0 insert, bit 1 eject, active-low edges; byte `0x69` ignored); LED write | `[cfexpress_hat] bus=1` (address default `0x34`) | working on bus 1 | CONFIRMED `SRC:23`, `:77`, `:103-105`, `:130-131`; `HL:25`, `:335-337`, `:346-349`; `A-UI:404`; `UIN:610` |
| 7 | Hat Qwiic hub `J4`-`J9` (passive, nets `SDA_IN`/`SCL_IN`/`+3V3_IN`), `U4` TCA9406 (OE tied to `+3V3_STB`), `U3` standby 3V3 from the FPC 5 V, `JP1`-`JP4` (open in the design files) | — | JP3 = FPC pin 13 to `SCL`, JP4 = FPC pin 14 to `SDA` | — | hub dead unless `+3V3_IN` comes from the 2x3 header or a Qwiic cable | CONFIRMED `SRC:100-109` |
| 8 | CFexpress card in the hat (NVMe over PCIe x1) | `/dev/nvme0n1p2`, exFAT, `/media/RAW` | PCIe Gen 3 (`config.txt:35-36`); Gen 2 tested, Gen 3 restored 23:07 | `[storage] mount_path`, `pcie_controller` | working; two controller drops, probable cause Gen 3 | CONFIRMED `HL:54`, `:308-311`, `:319-322`, `:380` |
| 9 | Adafruit NeoRotary 4 (product 5752), seesaw ATtiny817 | **i2c-1**, chained off one of the hat's Qwiic ports | `0x49`; seesaw HW ID `0x87`; 4 encoders + 4 push buttons | `[neorotary4] enabled=true bus=1 address=0x49`; knobs = ISO / shutter / WB / fps | working since 2026-10-23 | CONFIRMED `SRC:24`, `:130`; `HL:24-25`; knobs `TUT:81` ("already on, bus 1, knobs = ISO/shutter/WB/fps, Pi 2026-10-25") |
| 10 | IMU, recorded as MPU6050 | i2c-10 | `0x68` | `[imu]` + driver section (live values not in the KB) | seen on the bus; wiring unknown | CONFIRMED `SRC:77`, `:171`, `:176`. Identity PROBABLE only (§3, Q5) |
| 11 | Display: HDMI (`dtoverlay=vc4-kms-v3d`) | DRM `card1-HDMI-A-1`, `-A-2` | — | `config.txt:59`; `[display]` (`ui_width`/`ui_height`/`ui_layout` or `hdmi_external_only`) | working, HDMI is the main touch-UI screen | CONFIRMED `SRC:25`, `:136-143`; `HL:28-30`; `A-OV:151`; `A-UI:357`. Which `[display]` variant Patrik chose: UNCONFIRMED (`HL:30` says only "fixed via `[display]` keys") |
| 12 | DPI overlays `vc4-kms-DPI-4inch`, `waveshare-4dpi`, `waveshare-touch-4dpi` (image default for the Waveshare 4" square panel) | claim GPIO 0-27 (GPIO 2/3 → `DPI_VSYNC`/`DPI_HSYNC`); touch overlay makes bit-banged `i2c-15` | — | `config.txt:76-78` | **commented out** 2026-10-23 | CONFIRMED `SRC:39-41`, `:63-65`, `:79`, `:86-88`; `HL:23-27` |
| 13 | Tally LED (Cinemate wiring `GPIO21 → resistor → LED → GND`) | RP1 gpiochip0 line 21 | GPIO 21, active high | `[recording_indicator] enabled=true target=gpio line=21 active_high=true`; `d21=recindicatorled` removed | working 2026-10-25 | CONFIRMED `HL:36-49`; `tutorials/progress/T17.md:12-16` |
| 14 | Trigger output | was GPIO 21 | — | `[trigger_output] enabled=false` | disabled (it held line 21 before) | CONFIRMED `HL:39`, `:46-47`; `TUT:93` |
| 15 | PCF8574 expander | none fitted | (`0x20` configured) | `[pcf8574] enabled=false` (was enabled with no chip; `Remote I/O error`) | absent | CONFIRMED `HL:39-43`; `tutorials/progress/T17.md:10` |
| 16 | GPIO buttons on BCM 10 and BCM 6 | RP1 gpiochip | `d10`, `d6`, `active_low=true` | `[gpio_buttons]` | PROBABLE configured and enabled: flipping `active_low` "flips the d10/d6 button inputs" (`HL:44`). Their actions are not in the KB (UNCONFIRMED; `grep -n '^d' ~/apertar-hardware.conf`) |
| 17 | Pi 5 on-board power button | evdev device `pwr_button`, `KEY_POWER` | — | none (not configurable) | built in; single press → shutdown-hold card, double → standby, any press in standby → wake | CONFIRMED `A-CORE:456`, `:463` |
| 18 | INA219 power monitor | default `bus=4` | `0x40` | `[ina219]` | **absent**: `/dev/i2c-4` does not exist on this image | CONFIRMED `SRC:80`, `:168` |
| 19 | Other `config.txt` lines | — | — | `rp1-clk-333mhz` (`:65`), `dwc2,dr_mode=host`, `imx477` (line 11, probably another conditional section), `dtparam=i2c_arm=on`, `i2c_csi_dsi0=on`, `i2c_csi_dsi1=on` | as found | CONFIRMED `SRC:26`, `:30-38` |

Bus map on this rig (from `SRC:72-80` plus the fix):

| Bus | What it is | Devices | Label |
| --- | --- | --- | --- |
| `i2c-1` | Pi header I2C on GPIO 2/3 (`dtparam=i2c_arm=on`) | after the fix: `0x34` hat, `0x49` NeoRotary 4 | CONFIRMED `SRC:76`, `:130`; `HL:24-25` |
| `i2c-10` | RP1 controller on the camera connector (`i2c_csi_dsi0`) | `0x1a` IMX585 (UU), `0x48` TMP117, `0x68` IMU; `0x34` before the fix | CONFIRMED `SRC:52-55`, `:77`. Whether `0x34` still answers here after the fix: UNCONFIRMED (`SRC:132`) |
| `i2c-13`, `i2c-14` | BCM2712 internal (HDMI DDC) | none of ours | CONFIRMED `SRC:78` |
| `i2c-15` | `i2c@0`, bit-banged touch bus of `waveshare-touch-4dpi` | nothing | CONFIRMED `SRC:79`. PROBABLE gone since the overlay was commented out (it is created by that overlay) |
| `i2c-4` | Apertar's `[ina219]` default | **absent** | CONFIRMED `SRC:80` |

### 1.2 What Apertar supports in general (devices, sections, defaults)

Code defaults are from the KB (`A-CONF`, `A-CORE:450-459`, `CIN:683-695`); rows I re-opened at the tips say so.

| Device | Owner (process / class) | Section (aliases) | Bus / address default in code | Template values (Core WebUI template / UI first-run template) | Enabled when | Pins / channels | Label, cite |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Adafruit NeoRotary 4 (seesaw quad encoder) | Core `NeoRotary4Input` | `[neorotary4]` (`neo_rotary4`, `neo_rotary_4`) | 1 / `0x49`; poll 30 ms, 8 ms register delay, max 8 events/poll, HW ID must be `0x87` | Core: absent; UI: `enabled=false bus=1 address=0x49`, encoders 0-3 = ISO / shutter / WB / fps (press 3 = resolution) | section present (unless `enabled=false`), ≥1 action | encoders 0-3 `encoderN_{cw,ccw,press}`; seesaw button pins 12, 14, 17, 9 | CONFIRMED `A-CONF:157-169`, `A-CORE:450`, `:461`; CONFIRMED@tip `Core:src/hardware/NeoRotary4Input.hpp:36-48`, `:56` (`delayUs = 8000`), `Core:src/hardware/NeoRotary4Input.cpp:37`, `:503-511`; `UI:src/DisplayConfigBridge.cpp:131-155` |
| PCF8574 8-pin expander (buttons) | Core `Pcf8574Input` | `[pcf8574]` (`pcf8574_buttons`) | 1 / `0x20`; poll 40, debounce 60, active_low | Core: **`bus=10`**; UI: `bus=1`, `enabled=false`, `pin0..7=none` | section present, ≥1 pin action | `pinN`/`pin_N`/`gpioN`/`pN`, N 0-7 | CONFIRMED `A-CONF:125-138`, `:249`; CONFIRMED@tip `Core:src/hardware/Pcf8574Input.hpp:28-34`, `Core:src/ApertarCoreApp.cpp:4396-4405`, `UI:src/DisplayConfigBridge.cpp:74-99` |
| Pi GPIO buttons | Core `GpioInput` (chardev uAPI v2, no libgpiod) | `[gpio_buttons]` (`gpio`, `grove_digital`, `grove_buttons`) | chip `auto` (RP1 preferred), active_low, pull up, poll 12, debounce 60 | Core: `[gpio] enabled=false`; UI: `d5=capture`, `d6=eject`, `enabled=false` | only `enabled=true` | `dN`/`gpioN`/`pinN`/`bcmN`/`grove_dN`, BCM 0-63 | CONFIRMED `A-CONF:140-155`, `A-CORE:442`, `:452`; CONFIRMED@tip `UI:src/DisplayConfigBridge.cpp:156-167` |
| GPIO quadrature encoders | Core `GpioInput` | `[gpio_encoders]` (`grove_encoders`) | steps 4; **shares** chip/active_low/pull/poll/debounce with the buttons (last section wins) | UI: encoder0 a=5 b=6 press_gpio=13, `poll_ms=3`, `debounce_ms=40` (overrides the buttons' 12/60) | only `enabled=true` | `encoderN_{a,b,cw,ccw,press_gpio,press,invert,steps_per_event}`, N 0-7 | CONFIRMED `A-CONF:150-155`, `:254`; `CFN:645`; CONFIRMED@tip `UI:src/DisplayConfigBridge.cpp:168-183` |
| Grove Base HAT ADC (pots, sliders) | Core `GroveAnalogInput` | `[grove_analog]` (`grove_adc`, `analog_controls`) | 1 / `0x04` (`0x08` on MM32 hats); `channel=` is the **bus** alias | UI: `enabled=false`, bus 1 | section present | `aN`/`channelN`/`chN`/`analogN` targets, N 0-7 | CONFIRMED `A-CONF:171-183`; `CFN:656` |
| INA219 power monitor | Core (`ApertarCoreApp`) **and** UI `Ina219Bridge`, both reprogram the chip | `[ina219]` | **4** / `0x40` | 4 / `0x40` in all three templates | `enabled=true` (default) | — | CONFIRMED `A-CONF:94-102`; CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4284`, `:4340-4343`; `UI:src/Ina219Bridge.cpp:45-46` |
| IMU (MPU6050/6500, BMI160, BMI270, ICM42688-P) | Core `Mpu6050RecordingSession` (gyro sidecar) and UI `GyroConfigBridge` (live level), each opening the bus | `[imu]` (4 keys only) + `[mpu6050]`/`[bmi160]`/`[bmi270]`/`[icm42688p]`/`[gyro]` | 1 / `0x68`; **auto-probes `/dev/i2c-0..32` at 0x68/0x69** when the bus fails | Core: `[imu] enabled=false bus=10 …` (keys ignored); UI: `[imu] enabled=true`, `[mpu6050] bus=1` | code default enabled | — | CONFIRMED `A-CONF:205-232`, `:250-251`; `A-CORE:455`; CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4385-4394` |
| CFE hat controller | UI-repo daemon `apertar-cfe-automounter` (root), Core media watcher (fork, T28), Core embedded Python reinsert helper (each eject), UI embedded Python (dead code) | `[cfexpress_hat]`, `[storage]` | **10** / `0x34` (automounter default enabled; Core watcher: off unless the section exists) | 10 / `0x34` in all templates | see left | buttons bits 0/1, LED, status bit 0 | CONFIRMED `A-CONF:104-114`, `A-UI:391-404`, `A-OV:145`; CONFIRMED@tip `UI:src/CfeAutomounter.cpp:38-39`, `Core:src/util/CfeHat.hpp:18-22`, `Core:src/ApertarCoreApp.cpp:4550-4597`, `:9310-9313` |
| Trigger output (hot shoe / flash pulse) | Core `TriggerOutput` | `[trigger_output]` (`trigger`, `capture_trigger`, `hotshoe`) | GPIO17, active low, 80 ms; or PCF pin 0 | `open_drain=true` in templates vs code `false`; `line=17` | `enabled=true` | GPIO line or PCF pin | CONFIRMED `A-CONF:185-199`, `:258`; CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4413-4428` |
| Tally LED | Core `RecordingIndicatorOutput` | `[recording_indicator]` (+4 aliases) or `pinN=`/`dN=recindicatorled` | line −1 / pcf_pin −1 in code | templates `line=17`, `pcf_pin=7`, `enabled=false` | `enabled=true` or an LED alias anywhere (even in a disabled section) | GPIO line or PCF pin | CONFIRMED `A-CONF:201-203`, `:259`; CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4430-4443`, `UI:src/DisplayConfigBridge.cpp:117-130` |
| Pi 5 power button | Core `StandbyPowerButtonInput` (+ UI fallback when Core is down) | none | evdev `pwr_button` | — | always (not `--simulate`) | — | CONFIRMED `A-CORE:456`, `:463`; `UIN:698` |
| User scripts | Core `HardwareScriptRunner` | `[run_script]` `path`, `path1`-`path5` (editable path only) | — | present in Core and UI-Display templates | on a `run_script[N]` action | — | CONFIRMED `A-CONF:116-123` |
| Displays | UI (`run_pi_direct.sh`, `DisplayConfigBridge`) | `[display]` (UI only) | 720x720 square | Core template has a dead `controls_mode` key | — | DPI/DSI/LVDS/eDP = "internal", HDMI = monitor | CONFIRMED `A-UI:347`, `:357`; `CFN:115-129` |
| Sensors | Core camera code | — | IMX585/477/294/577 matched from the camera id | — | — | camera bus i2c-10 on cam0 | CONFIRMED `A-DRV:122` |
| Build maximum FPS (T33, **scratch only**, not on Patrik's tip) | Core | `[camera] max_fps=` | 0 = no limit | proposed for Core's template | — | — | CONFIRMED `working/ramp-ladder/build/SPEC.md:63-70`, `working/ramp-ladder/build/STATUS.md:7-12`; absent at the tip: CONFIRMED@tip (no `[camera]` in `Core:src/ApertarCoreApp.cpp:4333-4448`) |

### 1.3 Known-address table (merged)

| Address | Device | Where | Collides with | Label, cite |
| --- | --- | --- | --- | --- |
| `0x04` (`0x08` MM32) | Grove Base HAT ADC | Apertar default bus 1 | Cinemate's probe expects the Grove hat at `0x08` | CONFIRMED `A-CONF:177`; `Cm:src/module/app/hardware_probe.py:88-93` |
| `0x1a` | IMX585 | i2c-10 (driver, `UU`) | — | CONFIRMED `SRC:166` |
| `0x20` | PCF8574 (Apertar default) | bus 1 in code, 10 in Core's template | trigger and LED outputs share the same expander, each with its own shadow byte (PROBABLE clobbering, unconfirmed on hardware) | CONFIRMED `A-CORE:467`, `:538` |
| `0x34` | RPI5-CFE-Hat controller (CH32V003) | i2c-10 (ribbon) / i2c-1 (header) | possibly the StarlightEye's own CH32V003 (§3, Q4) | CONFIRMED `SRC:167`; collision UNCONFIRMED |
| `0x3C`/`0x3D` | SSD1306/1309 OLED (Cinemate only) | Cinemate bus 1 | — | CONFIRMED `Cm:src/module/app/hardware_probe.py:82-83` |
| `0x40` | INA219 | Apertar default bus 4 | — | CONFIRMED `SRC:168` |
| `0x48` | TMP117 on the StarlightEye | i2c-10 | A seesaw probe here reads `0x12` (temperature high byte, ~36 °C), so `[neorotary4] address=0x48` fails with "unexpected hardware ID 0x12". An ADS1115 also defaults to `0x48`: general datasheet knowledge, **not in the KB and not in Cinemate** (grep 0 hits for `ads1115` in both) | CONFIRMED `SRC:68`, `:82`, `:169`; `A-CORE:461`; ADS1115 UNCONFIRMED w.r.t. the KB |
| `0x49` | NeoRotary 4 (seesaw default) | wherever its hub is powered | TMP117 and ADS1115 can be strapped to `0x48-0x4B` (general datasheet knowledge, not in the KB): an answer at `0x49` is not proof of a seesaw; the `0x87` HW ID is | CONFIRMED `SRC:170`; strap ranges UNCONFIRMED w.r.t. the KB |
| `0x68` (`0x69`) | MPU6050 and the other IMUs | i2c-10 on this rig | Cinemate's probe labels `0x68` "Real-time clock" (DS3231-style RTC) | CONFIRMED `SRC:171`; `Cm:src/module/app/hardware_probe.py:100-104` |

---

## 2. The fix, step by step, and what a system could detect or guide

### 2.1 The exact steps (as done 2026-10-23)

| # | Step | Command / edit | Who may run it | Label, cite |
| --- | --- | --- | --- | --- |
| 0 | Symptom | `i2cdetect -y 1` → `Could not open file /dev/i2c-1`; `i2cdetect -l` lists 10, 13, 14, 15 only; `pinctrl get 2,3` → `DPI_VSYNC`/`DPI_HSYNC`; no `0x49` anywhere; `0x48` answers a seesaw probe with `0x12` | read-only (the KB shows a `$` prompt, so PROBABLE runnable as `pi`) | CONFIRMED `SRC:44-68` |
| 1 | Disable the DPI overlays | `sudo sed -i '76,78 s/^dtoverlay=/#dtoverlay=/' /boot/firmware/config.txt` | **Patrik only** (sudo, `/boot/firmware`) | CONFIRMED `SRC:124-127`; rule `working/handoff-T26-T30.md:36` |
| 2 | Reboot | `sudo reboot` | **Patrik only** | CONFIRMED `SRC:127`, `HL:24` |
| 3 | Verify the bus | `pinctrl get 2,3` shows `SDA1`/`SCL1`; `i2cdetect -y 1` shows `34` and `49` | read-only | CONFIRMED `SRC:130`; result `HL:24-25` |
| 4 | Point the config at bus 1 | `[cfexpress_hat] bus=1`; `[neorotary4] enabled=true bus=1 address=0x49` | Patrik types it (house rule) | CONFIRMED `SRC:131`, `HL:25` |
| 5 | Restart every reader | reboot, or restart Core, the UI and `apertar-cfe-automounter` | **Patrik only** (service restarts) | CONFIRMED `SRC:131`; rule `working/handoff-T26-T30.md:36`. At eb9cc39 the readers of `[cfexpress_hat] bus` are four: Core media watcher (at thread start), Core's embedded Python reinsert helper (each eject), the automounter (daemon start), the UI's embedded Python (dead code) — CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:9310`; others per `A-CONF:104-114`, `UIN:702` |
| 6 | Two-masters check | if `34` also answers on bus 10, or `1a` on bus 1, JP3/JP4 bridge the header bus and the camera bus; open them | hardware change, Patrik | KB: **unconfirmed** on this rig after the fix (`SRC:132`) |
| 7 | Side effect: HDMI became the main touch-UI screen at 720x720 | `[display] ui_width=1920 ui_height=1080 ui_layout=landscape_large`, or `hdmi_external_only=true`; restart the UI | Patrik | CONFIRMED `SRC:134-143`, `HL:28-30` |
| 8 | Confirmation | Patrik at the rig: "now it works" | — | CONFIRMED `HL:31` |

Alternative when a DPI panel is in use (header bus gone for good): feed the hub's `+3V3_IN` with 3.3 V only (never `J5` pin 1 or 3,
those are +5 V; never wire `J5` pins 4/6 to GPIO 2/3), then `[neorotary4] bus=10` and `poll_ms=50` because bus 10 carries the
sensor's per-frame exposure/gain writes. CONFIRMED `SRC:145-150` (KB: not tested on hardware).

### 2.2 Detect and guide: what software can see, and with what

| # | Condition | Read-only signal a system can use | Can it detect? | What it can do | Label, derivation |
| --- | --- | --- | --- | --- | --- |
| D1 | A configured bus does not exist (`[neorotary4] bus=1`, `[ina219] bus=4`) | `stat /dev/i2c-N`; Core's own open error (`NeoRotary4Input input: /dev/i2c-1: No such file or directory`) | **Yes, today**, but only in the journal: `lastError()` has no readers (`UPI#3`, `UPI#38`) | Show "bus N missing" next to the device; list the buses that exist (`/sys/class/i2c-adapter` / `/dev/i2c-*`) | CONFIRMED `A-CORE:444`, `:461`, `:284`; CONFIRMED@tip only trigger/LED errors are read at start (`Core:src/ApertarCoreApp.cpp:7026-7041`) |
| D2 | Why bus 1 is missing: a DPI overlay holds GPIO 2/3 although `dtparam=i2c_arm=on` | parse `/boot/firmware/config.txt` read-only for `dtparam=i2c_arm=on` plus uncommented `dtoverlay=` lines naming DPI (`vc4-kms-DPI-*`, `waveshare-*dpi*`); `pinctrl get 2,3` function names | **Yes**. Core and the UI already read `config.txt` (Core fan block, UI sensor-token scan), so reading it is an existing pattern | One line with the file line number, as `SRC` §6.1 proposes ("bus 1 is unavailable: GPIO 2/3 are taken by the DPI overlay on config.txt line 76"), plus the exact command for Patrik. **Not** an automatic edit (§4 R2) | CONFIRMED `SRC:154`; existing reads `CFN:36` (row 16: Core `App:3104-3125` detect, UI `DeviceInfoBridge.cpp:231` scan). Whether `pinctrl` works as `pi`: PROBABLE (`$` prompt at `SRC:63`); UNCONFIRMED otherwise (`pinctrl get 2,3` as pi) |
| D3 | `i2c_arm` not enabled at all | no `dtparam=i2c_arm=on` line | Yes (same parse) | Guide: add the line, reboot (Patrik) | PROBABLE (same mechanism as D2; Cinemate's installer writes `dtparam=i2c_arm=on`, `SRC:96`) |
| D4 | Which bus the hat is on | read-byte at `0x34` on each existing bus; a sane status byte (not `0x69`) | Yes | Suggest `[cfexpress_hat] bus=`; Cinemate lesson: CFE presence only from the hat's own I2C answer, never from a PCIe node that every Pi 5 has | CONFIRMED `SRC:155` (bus auto-detect proposal); `UIN:610` (`0x69` invalid); `CL:25` |
| D5 | Is `0x49` really a NeoRotary 4 | seesaw HW-ID read in **two** transactions with a few ms between (`w2@0x49 0x00 0x01`, sleep 10 ms, `r1@0x49`): `0x87` = ATtiny817 (NeoRotary 4); `0x55` SAMD09, `0x84-0x89` ATtiny8xx/16xx = another seesaw board; anything else = not a seesaw (`0x12` at `0x48` = TMP117) | **Yes, today**: `NeoRotary4Input::verifyDevice` already does it and words the error ("unexpected hardware ID 0x12 at address 0x48") | Show the read ID and name the likely device from §1.3 | CONFIRMED `SRC:111-120`, `A-CORE:461`; CONFIRMED@tip `Core:src/hardware/NeoRotary4Input.cpp:37`, `:495-511` |
| D6 | Plain `i2cdetect` misses a seesaw | — | — | Never use a receive-byte ACK as seesaw presence; use D5. Cinemate measured a live board NACKing about a third of receive-byte probes | CONFIRMED `SRC:113` |
| D7 | Address conflicts | (a) two sections claim one bus+address (e.g. `[neorotary4] address=0x48` on bus 10 where the TMP117 lives; `[imu]` `0x68` vs an RTC; trigger/LED/buttons on one PCF8574); (b) an address answers but its ID says another device | (a) Yes, from the parsed file alone; (b) Yes where the device has an ID register (seesaw `0x87`; MPU6050 WHO_AM_I) | Validation message per row; the known-address table (§1.3) as the source of names | (a) PROBABLE (derived from §1.2 defaults); PCF sharing CONFIRMED `A-CORE:467`. MPU6050 WHO_AM_I register: general datasheet knowledge, UNCONFIRMED in the KB |
| D8 | INA219 configured on a bus that does not exist (`bus=4` on this image) | D1 | Yes | Core is silent; the UI's settings page says "Check /home/pi/apertar-hardware.conf and INA219 wiring". Offer "disable" or a bus picker. `SRC` §6.2: signature = `0x40` register `0x00` | CONFIRMED `A-CONF:102`, `SRC:155`, `SRC:168` |
| D9 | Hat on the ribbon only → dead Qwiic hub → encoder invisible | indirect only: hat answers on bus 10, nothing at `0x49` on any bus, bus 1 missing or empty | **Partly**: power topology is not visible to software | Guide text: "the hub needs 3.3 V from the 2x3 header or a Qwiic cable" | CONFIRMED mechanism `SRC:104-109`; detectability PROBABLE (no sensor for `+3V3_IN`) |
| D10 | Two masters (JP3/JP4 closed) | `0x34` on bus 1 **and** bus 10, or `0x1a` on bus 1 | Yes, but confounded if another device answers `0x34` on bus 10 (§3, Q4) | Warn; hardware fix only | CONFIRMED rule `SRC:132`; confound UNCONFIRMED |
| D11 | Phantom DPI connector picks the main screen | `/sys/class/drm/*-DPI-*/status` = `connected` with an empty `modes` file | Yes | Log which connector won; `[display] main_connector=` (proposed, does not exist) | CONFIRMED `SRC:136`, `:160`; `A-UI:357`; CONFIRMED@tip the launcher still matches `*-DPI-*` as internal (`UI:run_pi_direct.sh:108`) |
| D12 | Config saved but not applied | file mtime vs each reader's load time; Core logs `media: cfexpress hat on bus=… address=…` at watcher start | Yes | Show "restart needed: Core / UI / automounter" per changed section (M4) | CONFIRMED `A-CONF:404`; CONFIRMED@tip log line `Core:src/ApertarCoreApp.cpp:9312-9313` |
| D13 | A peripheral placed on the camera bus | `bus=10` on cam0 rigs | Yes | Warn and suggest `poll_ms≥50`; scanning bus 10 while streaming is untested | CONFIRMED `SRC:149`; scan risk UNCONFIRMED |

Two cautions the KB supports for any probe or scan feature:
- **Polling cost while recording.** The 2026-10-26 capture gaps listed "the media watcher's 250 ms probe + HAT reads while
  recording" as a candidate (`HL:389-390`); the next entry traced the gaps to the 1 s `syncfs` (sync off → 0 holes,
  `HL:394-407`). So HAT polling is PROBABLY exonerated, but no entry measured an I2C scan during a take. A scan button should
  refuse while recording (PROBABLE, derived).
- **No arbitration between processes.** Core, the UI and the automounter each open `/dev/i2c-N` directly (`A-OV:51`); the
  INA219 is reprogrammed by both Core and the UI (`A-CORE:468`), and `/api/state` reprograms it once per second per browser
  tab (`A-CORE:349`). CONFIRMED.

---

## 3. Open questions

| # | Question | KB status | Settles it | Cite |
| --- | --- | --- | --- | --- |
| Q1 | How did the hat controller reach `i2c-10`? Theory: JP3/JP4 closed onto PCIe FPC pins 13/14 | unconfirmed | look at JP3/JP4 on the board; `i2cdetect -y 1` and `-y 10` after the fix | `SRC:106`, `:175`; `HL:33-34` |
| Q2 | Where is the IMU physically connected (hub, header, camera side)? It is on bus 10 | unconfirmed | trace the wiring; `i2cdetect -y 1` with the IMU on the hub | `SRC:176`; `HL:33-34` |
| Q3 | Which overlay or wiring gives the reference rig a `/dev/i2c-4` for `[ina219]` | unconfirmed | `i2cdetect -l; ls /dev/i2c-*` on a reference image | `SRC:177`; `A-CONF:102`, `:417`; `HL:33-34` |
| Q4 | (new) Is the bus-10 `0x34` the CFE hat at all? The StarlightEye also carries a CH32V003 (IR-filter controller) whose address the KB does not record. If it answers `0x34`, Q1 needs no JP3/JP4 and the two-masters check (step 6) gives a false alarm | not in the KB | `i2cdetect -y 10` after the fix with the hat on bus 1; `i2ctransfer -y 10 r1@0x34` with a CFE card in and out (the hat's byte changes, an IR controller's should not) | PROBABLE, derived from `SRC:105` and `SRC:182` |
| Q5 | (new) Is `0x68` on bus 10 an MPU6050? The KB names it but records no ID read; Cinemate's probe calls `0x68` a real-time clock | not in the KB | `i2cget -y 10 0x68 0x75` (MPU6050 WHO_AM_I, expected `0x68`: datasheet knowledge) | `SRC:77`; `Cm:src/module/app/hardware_probe.py:100-104` |
| Q6 | Two masters after the fix (JP3/JP4) | unconfirmed | `SRC:132` check | `SRC:132` |
| Q7 | Live config provenance: was `~/apertar-hardware.conf` written by the UI template, and is there a `/boot` copy someone expects to be used? | unconfirmed | `grep -n '^\[' ~/apertar-hardware.conf`; `ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf` | `A-CONF:413-414` |
| Q8 | The "image's template" with `[recording_indicator] enabled=true target=pcf8574 bus=10 …` (`HL:42`) matches neither code template at the tips (both `enabled=false target=gpio line=17`). PROBABLE it is the file the image shipped, not a code template | not in the KB | `git -C ~/ApertarCore log -p -- …` is no help; compare a fresh image's file | CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4430-4443`, `UI:src/DisplayConfigBridge.cpp:117-130` |
| Q9 | What actions are mapped to `d10`/`d6` on the rig | not in the KB | `grep -n '^d' ~/apertar-hardware.conf` | `HL:44` |
| Q10 | PCF8574 clobbering when buttons, trigger and LED share one expander | unconfirmed | wire both, record, `i2cget -y <bus> 0x20` | `A-CORE:467`, `:538` |
| Q11 | Current DRM topology (same-card HDMI path, HDMI-A-2 waiting) | unconfirmed | `ls /sys/class/drm`; `journalctl -b -u apertar-ui-direct \| grep 'direct display'` | `A-UI:359` |
| Q12 | Can `pi` run `pinctrl` and open every `/dev/i2c-N` (needed for a non-root probe in Core)? | not in the KB | `id pi`; `pinctrl get 2,3` and `i2cdetect -l` as pi. PROBABLE yes for I2C: Core runs as `pi` and opens `/dev/i2c-1` successfully on this rig | `A-CONF:20`; `HL:24-25` |

---

## 4. Every KB rule that constrains this project

| # | Rule | What it means for the controls project | Label, cite |
| --- | --- | --- | --- |
| R1 | **Patrik types the changes** from tutorials; Claude writes the tutorial first and edits only when he says so | Deliverables are tutorials (T36+) with patches as references | CONFIRMED `TIDX:3-5`, `:39`; `TUT:13-17`; `working/handoff-speed-ramp.md:28-29`; numbering `working/ramp-ladder/build/STATUS.md:19-21` |
| R2 | **Patrik alone** runs `sudo`, service restarts, reboots, `/boot/firmware` edits, systemd drop-ins, DKMS | A "system-controlled config" must not edit `config.txt` itself to free GPIO 2/3; it detects and prints the line and the command (D2). Note the precedent: Core and the UI already rewrite a managed fan block in `config.txt` via `sudo -n install` (`CFN:36`); extending that pattern to overlays would cross this rule | CONFIRMED `working/handoff-T26-T30.md:36`; `working/handoff-speed-ramp.md:30` |
| R3 | **Builds on the Pi**; the Mac cannot build the stack; **nothing is pushed** unless Patrik asks | — | CONFIRMED `LLM:132`; `working/handoff-speed-ramp.md:31` |
| R4 | Claims labelled; every code claim has `path:line` against a named commit; observations separate from conclusions | Design and tutorials cite the tips | CONFIRMED `README.md:47-50` |
| R5 | `hardware-log.md` is append-only and only after Patrik confirms the interpretation | Any new rig fact (Q4, Q5, Q9) needs his confirmation | CONFIRMED `HL:3`; `README.md:51-52`; `TUT:48-51` |
| R6 | **M4 "Read once"**: hardware config is parsed at start, by each process separately. Core inputs/outputs only in `start()`; INA219 a `static const`; IMU and `run_script` re-read on use; UI `[display]` at UI start; automounter at daemon start. No reload command, no file watcher; the WebUI editor saves but reloads nothing | A save must say which owner to restart, or the project adds a reload; restarts are Patrik's in dev (R2) | CONFIRMED `TUT:69`; `LLM:94`, `:109-110`; `A-CONF:42-54`, `:404`; `A-CORE:73`, `:512`; `REC:84` |
| R7 | **M5 "Copies"**: state and option lists are hand-copied. Relevant copies: three `normalizeSingleAction` (`GpioInput`, `Pcf8574Input`, `NeoRotary4Input`); three templates (Core WebUI, UI Display, UI INA219); the candidate-path list in ~8 Core places + 5-6 UI places; hardware action names (Core emit, broadcast whitelist, QML router); step-action value lists (Core PCF tables, WebUI JS, QML); LED alias list (5 places) | A dropdown of actions needs **one** vocabulary that Core serves (e.g. a command), not a fourth hand copy in the WebUI; T11 (`zebra_toggle` alias) is the planned lesson on this | CONFIRMED `TUT:70`, `:87`; `REC:69-77`, `:88-96`; `CMAP:32-33`, `:502-511`; `UMAP:533`; `CPN:501`; `UIN:688-689`; value lists `working/ramp-ladder/README.md:45-52` |
| R8 | **M1 "One front door"**: every control (touch, web, knob) becomes a command into `handleCommand` | A method assignment maps to existing socket commands ("functionality of the Apertar API"); hardware actions run synchronously on the poll thread, so a slow command stalls polling | CONFIRMED `TUT:66`; `LLM:99-100`; `A-CORE:445`; `FLOWS:168-170` |
| R9 | `/boot/firmware/apertar-hardware.conf` is dead once `/home/pi/…` exists, and the UI creates `/home/pi/…` at every start if missing; the WebUI editor and `run_script` read only env or `/home/pi` | The system-controlled file lives at `/home/pi/apertar-hardware.conf` (or `$APERTAR_HARDWARE_CONFIG`) | CONFIRMED `LLM:121`; `A-CONF:30-40`; `REC:82`; `UPI#31` |
| R10 | Two file-selection rules: "first existing file wins" (INA219, trigger, LED, IMU, UI, automounter, Python) vs "first file that has the section" (PCF8574, GPIO, NeoRotary4, Grove) | Split files give different readers different sources; one file is safer | CONFIRMED `A-CONF:38-40`; `CFN:621-626` |
| R11 | Parser differences: inline comments stripped differently (INA219 and Python integers not stripped: `bus=4 # x` is ignored); `enabled`/`disabled` bool words only in some parsers; `[run_script]` and UI QSettings groups case-sensitive; Python `configparser` raises on duplicate keys/sections or `%` | A writer that emits the file must avoid inline comments on values and duplicate keys, and use `true`/`false` | CONFIRMED `A-CONF:56-66`; `CFN:649-665` |
| R12 | Four writers, no shared lock (WebUI save, Core IMU commands, UI gyro page, UI template); WebUI and IMU both use `<path>.tmp`; the WebUI save has no fsync and bypasses `commandMutex_` | A system writer must coexist with the IMU writers (they rewrite `[imu]`/driver sections) | CONFIRMED `A-CONF:403`; `CFN:669-674`; `CPN:663-665` |
| R13 | Template defaults disagree: Core's WebUI template `[pcf8574] bus=10`, `[imu] bus=10` (ignored); UI templates and every parser default bus 1; INA219 4; hat 10. The KB source's §6.6 wording is reversed | One default per peripheral, with the overlay that creates its bus named (`SRC` §6.6, as corrected) | CONFIRMED `A-CONF:249`, `:265-275`; `UPI#2`; CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4388`, `:4405` |
| R14 | Driver state is invisible: input `lastError()`s go only to stderr; `get_state` has no hardware status | The "I2C devices" view needs a new state field or command; until then the journal is the only witness | CONFIRMED `A-CORE:284`, `:444`, `:509`; `UPI#3`, `#38`; `LLM:125` |
| R15 | The WebUI has **no auth**; requests without `Origin` pass; anyone on the LAN can rewrite `apertar-hardware.conf`, including `[run_script]` paths | A config editor reachable from the browser can make the camera run arbitrary scripts; keep the camera on a trusted network or gate the `[run_script]` keys | CONFIRMED `UPI#37`; `A-CORE:324`; `CPN:639` |
| R16 | In Standby any press only wakes and rotations are ignored; a rotation never fires `standby`; an unknown action name only logs `Hardware input action ignored: unknown action` | The editor should validate names against Core's vocabulary before saving | CONFIRMED `REC:96`; `A-CORE:446`; `LLM:131` |
| R17 | Inputs know only "pressed": one action on the debounced press edge, no hold/release/double click (except the fixed power-button double press); ≤6 actions per mapping | Cinemate's gesture columns have no Apertar counterpart yet | CONFIRMED `A-CORE:446`, `:463`; `CIN:685`; details in `working/controls/r2-apertar-core-hw.md` §2 |
| R18 | A take started from a hardware input reached the touch UI only on its 30 s poll (`recording` not broadcast); fixed in the fork `a070e1b` | Hardware-triggered events must be on the broadcast list | CONFIRMED `UPI#43`; `HL:424-428` |
| R19 | Helpers in `/usr/local/libexec` (automounter) are copies: a UI build does not update them; installing needs `sudo install` (Patrik) | Any change to the automounter's `[cfexpress_hat]` parsing needs a Patrik install step | CONFIRMED `LLM:120`; `REC:26`, `:78` |
| R20 | Cinemate lessons that apply: "a default is a claim, not a fact" (six copies of a default, one checked); "a fallback whose failure mode is 'yes' is not a fallback" (CFE only via the `0x34` answer); "duplicated truth must be deleted, or carry a named reason and a check"; "a claim about what the machine does" needs the Pi (5 of 16 source-only predictions were wrong) | Bus defaults and probes must be checked on the Pi; one owner for the action vocabulary and the value lists | CONFIRMED `CL:19`, `:21`, `:25`, `:28` |
| R21 | Value lists (ISO/shutter/FPS/WB) for pots and `*_up`/`*_down` buttons are planned to move to `UI.conf` `[General]` (T35), the build maximum to `apertar-hardware.conf` `[camera] max_fps` (T33, scratch). The split: per-build hardware facts in `apertar-hardware.conf`, operator preferences in `UI.conf` | The GPIO/action editor should follow the same split and not create a third store | CONFIRMED `working/ramp-ladder/README.md:60-89`; `working/handoff-speed-ramp.md:75-81`; `working/ramp-ladder/build/SPEC.md:63-70` |
| R22 | Tutorial `check` lines are read-only (no `set_*`, `sudo`, `>`, `git checkout`); never `git checkout/reset/clean` on the Pi | Tutorials for this project verify by reading files and logs | CONFIRMED `TIDX:83`; `TUT:44` |
| R23 | A distribution image swaps the personal `~/apertar-hardware.conf` for the stock template and restores it after; `config.txt` (DPI overlays disabled on this rig) likewise | The "system-controlled" default file must be what a fresh image gets | CONFIRMED `working/distribution-image.md:46-48` |

Planned tutorials that touch this project (none written yet): T05 remap a NeoRotary knob press (`[neorotary4]`, parser
`NeoRotary4Input.cpp:400-435`, action `App:8913`, M4, Core restart, status planned), T11 `zebra_toggle` alias (three
`normalizeSingleAction`, M5, planned), T13 a knob press that opens the clip browser (UI-only `hardware_action`, planned);
T17 tally LED is the only hardware-controls tutorial done on hardware (confirmed). CONFIRMED `TUT:81`, `:87`, `:89`, `:93`;
`TIDX:103`, `:106`. `tutorials/inbox/` holds only T31 and T32 (no T05/T11/T17 notes); T31's "going further" suggests a
`set_fps_double` toggle on a GPIO button (`tutorials/inbox/20261026210000 CINEMATE APERTAR T31 speed-ramping.md:222`).
CONFIRMED.

---

## 5. KB inconsistencies and drift found while reading

| # | Finding | Label, cite |
| --- | --- | --- |
| K1 | `A-CONF:114` ("The C++ Core never reads these sections", `[cfexpress_hat]`/`[storage]`) is stale for the fork: at eb9cc39 Core's media watcher reads `[cfexpress_hat]` with its own parser (`loadCfeHatConfig`, enabled only when the section exists, default bus 10) | CONFIRMED@tip `Core:src/ApertarCoreApp.cpp:4550-4597`, `:9310-9313`; `Core:src/util/CfeHat.hpp:18-22` |
| K2 | `A-CORE:496` calls the hat's bit-0 polarity unconfirmed; the hardware log shows Core's C++ reader detecting pulls with "bit 0 = card out" (`hat_card=out` on every pull) | CONFIRMED `HL:335-337`, `:346-349`; `working/port-raw/y2-yank-core.md:377` (PROBABLE inversion in the Python helper) |
| K3 | `SRC:159` (§6.6) has the PCF8574 bus defaults reversed; corrected in `A-CONF:265-275` and `UPI#2`. `SRC` is a frozen source, so the correction lives only in the other pages | CONFIRMED |
| K4 | `run_pi_direct.sh` line refs: `SRC:136` says `:135-160`, `HL:30` says `:138-166` at upstream-1.6.0 | CONFIRMED `HL:29-30` |
| K5 | Journal access: `LLM:126` and `UPI#30` say `pi` cannot read the journal; `working/diagnose.md:19` says `pi` is in `systemd-journal` since 2026-10-25. Matters because driver errors are journal-only (R14) | CONFIRMED (both lines opened) |
| K6 | `A-CONF:20` says every unit runs as `User=pi`; `A-OV:145` records the automounter running as root | CONFIRMED (both lines opened) |
| K7 | Line drift between the KB baseline (upstream-1.6.0) and the tips: Core `start()` hardware block `App:6881-6896` → `Core:src/ApertarCoreApp.cpp:7026-7041`; Core template `App:4291` → `:4333`; INA219 default `App:4242` → `:4284`; template `[pcf8574] bus=10` `App:4363` → `:4405`; template `[imu] bus=10` `App:4346` → `:4388` | CONFIRMED@tip (lines opened); KB values CONFIRMED `A-CONF:46`, `:99`, `:249`; `FLOWS:193` |
| K8 | `HL:42` calls the file with `[recording_indicator] enabled=true target=pcf8574 bus=10` "the image's template"; neither code template has those values (Q8) | CONFIRMED@tip; interpretation PROBABLE |

---

## 6. Cinemate lessons file (`CL`), GPIO/I2C content

The file is about phase lock, yank and storage; it has no GPIO-editor or encoder lesson (grep for gpio/i2c/button/encoder/
rotary/seesaw/pcf: only the lines below). CONFIRMED `CL:1-12`.

| Lesson | Relevance here | Cite |
| --- | --- | --- |
| CFE presence only from the hat's own I2C answer at `0x34`; a sysfs node present on every Pi 5 labelled a plain NVMe as CFE (Cinemate `888093c`) | Probes must be able to answer "unknown"; ID registers over ACKs (D4, D5) | CONFIRMED `CL:25` |
| "A default is a claim": six copies of a default, one checked, a week lost | The three templates and per-class defaults (R13) | CONFIRMED `CL:21` |
| "Duplicated truth must be deleted, or carry a named reason and a check"; "one gate in `handleCommand` covers socket, WebUI and buttons" | One action vocabulary and one value-list owner (R7, R21) | CONFIRMED `CL:28` |
| "A tool exiting 0 does not mean it answered" | A probe needs a non-empty, plausible answer (e.g. not `0x69`, not `0x12`) | CONFIRMED `CL:26` |
| "Fail visible, never silent" | Surface `lastError()` (R14) | CONFIRMED `CL:29` |

Outside `CL`, the KB names Cinemate's `hardware_probe.py` as the working reference for per-device probes (`SRC:155`, `:184`):
it probes bus 1 only (`I2C_BUS = 1`), keeps a device table (Grove `0x08`, quad rotary `0x49`, RTC `0x68`, OLED `0x3C`/`0x3D`)
and reads the seesaw HW ID with a delay. CONFIRMED `Cm:src/module/app/hardware_probe.py:52`, `:82-104`, `:208-233`.
