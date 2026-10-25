---
datum: 2026-10-25 15:29:45
kontext: CINEMATE
projekt: "#APERTAR"
fritext: start-tutorials
typ: digital anteckning
---


# Apertar hardware notes: I2C buses, the CFE hat's Qwiic hub, and the NeoRotary 4

Status: diagnosed and fixed on hardware 2026-10-23 (operator at the rig, desk analysis alongside). After the DPI overlays were disabled and the Pi rebooted, `/dev/i2c-1` appeared and the encoder and hat were found on bus 1 ("now it works"). Entries marked **unconfirmed** need one command on the Pi to close.

Purpose: a reusable record of why a quad encoder (Adafruit NeoRotary 4, product 5752) daisy-chained to the CFE hat was invisible on Apertar although the identical wiring worked on Cinemate, plus what Apertar could change so the next person does not spend an evening on it.

## 1. The rig

| Item | Value | Source |
| --- | --- | --- |
| Board | Raspberry Pi 5 family (`[pi5]` section, `dtparam=pciex1`) | `config.txt` |
| Image | Apertar-Beta 1.6.0 on Raspberry Pi OS Trixie | Apertar-Beta README, release tags |
| Sensor | IMX585 on cam0, `dtoverlay=imx585,cam0,link-frequency=891000000` | `config.txt` line 42 |
| Storage | Will Whang RPI5-CFE-Hat (CFexpress Type B), controller at I2C `0x34` | scan, `~/apertar-hardware.conf` |
| Encoder | Adafruit NeoRotary 4, seesaw ATtiny817, default address `0x49`, chained off one of the hat's Qwiic ports | operator; `seesaw_quadrotary.py` example uses `0x49` |
| Display | HDMI (`dtoverlay=vc4-kms-v3d`). No DPI panel attached, but the DPI overlays were still enabled (see 3.2) | operator, `config.txt` lines 59, 76-78 |
| Other overlays | `rp1-clk-333mhz` (RP1 overclock), `dwc2,dr_mode=host`, `imx477` (line 11, probably another conditional section) | `config.txt` |

Relevant `config.txt` lines as found:

```
dtparam=i2c_arm=on
dtparam=i2c_csi_dsi0=on
dtparam=i2c_csi_dsi1=on
dtparam=pciex1
dtparam=pciex1_gen=3
42:dtoverlay=imx585,cam0,link-frequency=891000000
59:dtoverlay=vc4-kms-v3d
65:dtoverlay=rp1-clk-333mhz
76:dtoverlay=vc4-kms-DPI-4inch
77:dtoverlay=waveshare-4dpi
78:dtoverlay=waveshare-touch-4dpi
```

## 2. Symptom

```
$ i2cdetect -y 1
Error: Could not open file `/dev/i2c-1' or `/dev/i2c/1': No such file or directory

$ i2cdetect -y 10
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
10: -- -- -- -- -- -- -- -- -- -- UU -- -- -- -- --
30: -- -- -- -- 34 -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --

$ i2cdetect -l
i2c-10   Synopsys DesignWare I2C adapter
i2c-13   107d508200.i2c
i2c-14   107d508280.i2c
i2c-15   i2c@0

$ pinctrl get 2,3
 2: a1    pn | hi // GPIO2 = DPI_VSYNC
 3: a1    pn | hi // GPIO3 = DPI_HSYNC
```

No `0x49` on any existing bus. `0x48` answered a seesaw hardware-ID probe with `0x12`, not `0x87`.

## 3. What the evidence says

### 3.1 Bus map on this image

| Bus | What it is | Devices seen |
| --- | --- | --- |
| `i2c-1` | Pi header I2C on GPIO 2/3 (`i2c_arm`) | **absent** (see 3.2) |
| `i2c-10` | RP1 DesignWare controller: the camera-connector bus (`i2c_csi_dsi0`), also reaching the CFE hat | `0x1a` IMX585 (held by the driver, `UU`), `0x34` CFE hat MCU, `0x48` TMP117 on the StarlightEye camera board, `0x68` IMU (MPU6050) |
| `i2c-13`, `i2c-14` | BCM2712 internal (HDMI DDC) | none of ours |
| `i2c-15` | `i2c@0`: the bit-banged touch bus created by `waveshare-touch-4dpi` | nothing attached |
| `i2c-4` | Apertar's default for `[ina219]` | **absent** on this image; which overlay creates it is an open question |

`0x48` is the StarlightEye's TMP117 temperature sensor (TMP117 default address `0x48`; the README lists "Integrated TMP117 temperature sensor"). The `0x12` read back is the temperature register's high byte, about 36 degrees C, which is why it is not a seesaw.

### 3.2 Why `/dev/i2c-1` does not exist: the DPI overlays

Every DPI mode uses GPIO 0-3 for pixel clock, DE, VSYNC and HSYNC, and the Waveshare/HyperPixel overlays claim GPIO 0-27. `pinctrl get 2,3` shows exactly that: `DPI_VSYNC` / `DPI_HSYNC`. The overlay is loaded whether or not a panel is plugged in, so `dtparam=i2c_arm=on` is present in the file but overridden, and the header I2C bus is never created.

Apertar's image ships the three DPI lines enabled by default (Apertar-Beta README: "By default it's configured for the Waveshare 4Inch Square DSI Display"; the lines are `vc4-kms-DPI-4inch`, `waveshare-4dpi`, `waveshare-touch-4dpi`). An HDMI user inherits them and loses GPIO 0-27 without noticing.

### 3.3 Why the same wiring worked on Cinemate

Cinemate uses the header bus for everything I2C and runs HDMI, so GPIO 2/3 are free:

- `cinemate/src/module/app/hardware_probe.py:45`: `I2C_BUS = 1`.
- `cinemate/src/module/i2c/quad_rotary_controller.py:204` and `i2c/i2c_oled.py:70`: `busio.I2C(board.SCL, board.SDA)`, i.e. GPIO 3/2 = `/dev/i2c-1`.
- `cinemate-install.sh:1100`: writes `dtparam=i2c_arm=on`; `:1152`: `dtoverlay=vc4-kms-v3d`; no DPI overlay anywhere in the installer.

On Cinemate the hat sat on the Pi header through its 2x3 header, which supplied the hat's Qwiic side with 3.3 V and bus 1, so the hat's controller and the encoder on the hub were both on bus 1.

### 3.4 How the CFE hat's I2C is actually wired (schematic, `RPI5-CFE-Hat/Schematic.pdf`, 2024-03-23)

- **Qwiic hub**: five 4-pin connectors `J4`-`J9`, all paralleled on nets `SDA_IN`, `SCL_IN`, `+3V3_IN`, `GND`. A passive hub.
- **RPI HAT header `J5`** (2x3, `Conn_02x03_Odd_Even`): sits on the same nets. Its pins land on Pi header pins 1-6 position for position, but KiCad numbers the even pins on the I2C side: J5 pin 2 = `+3V3_IN` (lands on Pi pin 1, 3V3), pin 1 = `+5V` (Pi pin 2), pin 4 = `SDA_IN` (Pi pin 3, GPIO 2), pin 3 = `+5V` (Pi pin 4), pin 6 = `SCL_IN` (Pi pin 5, GPIO 3), pin 5 = `GND` (Pi pin 6). Confirmed against the J5 pad nets in `RPI5-CFE-Hat.kicad_pcb`, the `.kicad_sch` wiring and the PDF (the symbol is drawn mirrored, which is what misleads a quick read).
- **I2C isolation `U4` TCA9406**: a bidirectional level translator between the hub side (`SDA_IN`/`SCL_IN`, `VCCB = +3V3_IN`) and the controller side (`SDA`/`SCL`, `VCCA = +3V3_STB`). `OE` is tied to `+3V3_STB`, so the translator is enabled whenever the hat has standby power, but its hub side only works when `+3V3_IN` is supplied from outside (Qwiic cable or the 2x3 header).
- **Controller**: the hat MCU at `0x34` is on the `SDA`/`SCL` side. The schematic draws `U2` with a KiCad STM8S003F3P symbol, but `bom/BOM_RPI5CFE.xlsx` orders a CH32V003F4P6 in the same TSSOP-20 footprint, the pin usage matches the `Software/I2C_GPIO` firmware pin for pin, and PD1 is labelled `SWIO` (the WCH debug pin). It has always been a CH32V003; there is no STM8 revision.
- **`JP1`-`JP4`**: four open solder jumpers in a row beside the PCIe FPC connector `J1`. FPC pin 13 can be bridged to the MCU's `PCIE_PWR_EN` (JP1) or to the controller-side `SCL` (JP3); FPC pin 14 to the MCU's `PCIE_DET_WAKE` (JP2) or to `SDA` (JP4). The I2C-over-FPC jumpers are JP3 (SCL) and JP4 (SDA); all four are open in the design files. Closing JP3/JP4 puts the hat's controller on whatever bus the Pi exposes on FPC pins 13/14. **Unconfirmed**: that this is how the hat reaches `i2c-10` on this rig; it is the only path that does not go through `SDA_IN`/`SCL_IN`, and those are DPI signals here.
- **Standby power `U3`**: `+3V3_STB` from the FPC's 5 V, so the controller runs with no Qwiic or header connection.

Consequence: with the hat fed only through the ribbon, the controller answers on bus 10 while the Qwiic hub has no 3.3 V and is isolated. A board chained to the hub gets no power and no bus. With the hat on the 2x3 header on this image, the hub is powered but its `SDA_IN`/`SCL_IN` are wired to `DPI_HSYNC`/`DPI_VSYNC`; the translator then forwards sync pulses onto the controller bus, which is the camera bus.

### 3.5 Probing a seesaw correctly

`i2cdetect` can miss a seesaw (Cinemate measured a live board NACKing about a third of receive-byte probes, `hardware_probe.py` comment near `_seesaw_present`). A repeated-start read also returns stale data because the ATtiny needs a few ms after the register select. Use two transactions:

```bash
i2ctransfer -y <bus> w2@0x49 0x00 0x01; sleep 0.01; i2ctransfer -y <bus> r1@0x49
# NeoRotary 4 answers 0x87 (ATtiny817). Other seesaw IDs: 0x55 SAMD09, 0x84-0x89 ATtiny8xx/16xx.
```

Apertar's driver does the same check: `NeoRotary4Input::verifyDevice` expects `kExpectedHardwareId = 0x87` and uses an 8 ms delay in `readRegister` (`apertar-core/src/hardware/NeoRotary4Input.cpp`).

## 4. Resolution for an HDMI rig (no DPI panel)

1. Disable the DPI overlays and reboot:
   ```bash
   sudo sed -i '76,78 s/^dtoverlay=/#dtoverlay=/' /boot/firmware/config.txt
   sudo reboot
   ```
   `dtparam=i2c_arm=on` then takes effect and `/dev/i2c-1` appears on GPIO 2/3.
2. Verify: `pinctrl get 2,3` shows `SDA1`/`SCL1`; `i2cdetect -y 1` shows `34` (hat, through the translator) and `49` (encoder on the hub).
3. `~/apertar-hardware.conf`: `[cfexpress_hat] bus=1`; `[neorotary4] enabled=true bus=1 address=0x49`. Both ApertarCore (embedded automount helper, `ApertarCoreApp.cpp` ~3380) and the UI (`CfeAutomounter.cpp`) read the hat's bus from this file. Reboot or restart both.
4. Two-masters check: if `34` also appears on bus 10, or `1a` appears on bus 1, `JP3`/`JP4` are closed and the translator is bridging the header bus and the camera bus. It worked that way on Cinemate but is two masters on one wire; open `JP3` (SCL) and `JP4` (SDA) to make the hat bus-1 only. **Unconfirmed** on this rig after the fix.

### 4.5 Side effect: the HDMI output changes role

Apertar's launcher (`apertar-ui/run_pi_direct.sh:135-160`) puts the main touch UI on the first connected *internal* connector (`*-DSI-*`, `*-DPI-*`, `*-LVDS-*`, `*-eDP-*`) and uses HDMI only for the external-monitor window. A DPI overlay creates a DPI connector that reports `connected` even with no panel, so before the fix the 720x720 UI was rendered to nothing and HDMI showed the full-size monitor view. With the overlay gone, HDMI is the only connector, becomes the main UI screen, and shows the 720x720 square layout from `[display]`: "HDMI output is not displaying the correct size".

Two fixes, both in `[display]` of `~/apertar-hardware.conf` (keys parsed in `DisplayConfigBridge.cpp:599-648`, layouts listed in its template at `:305-311`), then restart the UI:

- Touch UI on HDMI at native size: `ui_width=1920`, `ui_height=1080`, `ui_layout=landscape_large` (1280x720 pairs with `landscape`, 1024x600 with `landscape_medium`).
- Previous behaviour, HDMI as monitor view only: `hdmi_external_only=true`. `main.cpp:428` hides the main window and `ExternalMonitorManager::externalScreen()` (`:130-138`) takes the HDMI screen even when it is the primary one.

The UI logs the values it loaded: `Apertar display config: path=... size=WxH layout=... hdmi_external_only=...` (`main.cpp:280`).

## 5. Alternatives if the DPI panel is in use

The header bus is gone for good in that case; the encoder must reach bus 10 through the hat's translator.

- Feed `+3V3_IN` with 3.3 V only: one jumper from Pi pin 1 or 17 (3V3) to `J5` pin 2 (the J5 pin that lands on Pi pin 1) or to pin 2 (VCC) of any Qwiic port. Never to `J5` pin 1 or 3: those are the hat's +5V rail. Do **not** connect `J5` pins 4/6 (`SDA_IN`/`SCL_IN`) to Pi pins 3/5 (GPIO 2/3); with the DPI overlay active they are sync lines. Then `[neorotary4] bus=10`, and start at `poll_ms=50` because the bus also carries the sensor's per-frame exposure and gain writes.
- Or move the whole hat to a Qwiic feed on a bus that exists and open `JP3`/`JP4`; on this image no Pi connector exposes bus 10 as Qwiic without an adapter, so this is not practical here.

## 6. What Apertar could change

1. **Do not ship DPI overlays active unless a DPI display is selected.** Or detect the condition: if `/sys/class/gpio` or `pinctrl` reports GPIO 2/3 as DPI while `[neorotary4]`/`[pcf8574]`/`[gpio_*]` name bus 1, log one clear line and show it in the WebUI config tab ("bus 1 is unavailable: GPIO 2/3 are taken by the DPI overlay on config.txt line 76").
2. **Bus auto-detect for I2C peripherals.** When `bus=` is absent, scan `/dev/i2c-*` for the device's signature instead of defaulting to 1: `0x34` read-byte for the hat, seesaw HW-ID `0x87` at `0x49` for the NeoRotary 4, `0x40` register `0x00` for the INA219. Cinemate's `hardware_probe.py` is a working reference for the per-device probes.
3. **Surface driver state.** `NeoRotary4Input::lastError()` (and the other inputs') has no readers; put `enabled`, `configPath`, `lastError` in `get_state` so the WebUI can say "/dev/i2c-1: No such file or directory" instead of silently retrying every second.
4. **A hardware-probe page in the WebUI**: an `i2cdetect`-style view per bus with the known-address table below, plus `pinctrl` for GPIO 2/3 and the active `dtoverlay` lines. Cinemate's settings-editor i2c pane is the model.
5. **Document the hat's power topology** in the hardware section of the README: the Qwiic hub needs `+3V3_IN` from the 2x3 header or a Qwiic cable; a ribbon-only hat has a dead hub; `JP3`/`JP4` bridge buses.
6. **Fix the template defaults that cannot work on a stock Pi 5 image**: `[ina219] bus=4` and `[pcf8574] bus=10` in the UI template vs `bus=1` in the Core template (`DisplayConfigBridge.cpp` and `Ina219Bridge.cpp` carry two copies of the template; `ApertarCoreApp.cpp` a third). One template, one default per peripheral, with a comment naming the overlay that creates the bus.
7. **Do not let a phantom connector choose the main screen.** `run_pi_direct.sh` treats any `connected` DPI connector as the touch panel; a DPI overlay with no panel satisfies that. Either check that a panel driver actually bound (the connector's `modes` file non-empty and an `edid`/panel node) or let `[display]` name the main connector explicitly (`main_connector=HDMI-A-1`), and log which connector won and why.

Known-address table for this ecosystem:

| Address | Device | Bus on this rig |
| --- | --- | --- |
| `0x1a` | IMX585 sensor | 10 |
| `0x34` | RPI5-CFE-Hat controller (CH32V003) | 10 (ribbon) / 1 (header) |
| `0x40` | INA219 power monitor (Apertar default) | not present |
| `0x48` | TMP117 on the StarlightEye camera board | 10 |
| `0x49` | Adafruit NeoRotary 4 (seesaw) | wherever its hub is powered |
| `0x68` | MPU6050 IMU | 10 |

## 7. Open questions

- How does the hat controller reach `i2c-10`? The working theory is `JP3`/`JP4` closed onto PCIe FPC pins 13/14, with the Pi exposing the same RP1 controller on the FPC and on the cam0 connector. A look at `JP3`/`JP4` on the board, and `i2cdetect -y 1` after the reboot, settle it.
- Where is the IMU physically connected (hub, header, or camera-side)? It is on bus 10 today.
- Which overlay or wiring gives Apertar's reference rig a `/dev/i2c-4` for the INA219.

## 8. Sources

- Hat: `github.com/will127534/RPI5-CFE-Hat` (`Schematic.pdf`, `RPI5-CFE-Hat.kicad_sch`, `Software/automount.py` with `i2c_ch = 1`, `i2c_address = 0x34`; `Software/I2C_GPIO/User/main.c` `RXAdderss 0x34 << 1`).
- Camera board: `github.com/will127534/StarlightEye` README (TMP117, CH32V003 IR-filter controller).
- Encoder: `github.com/adafruit/Adafruit_CircuitPython_seesaw/examples/seesaw_quadrotary.py` (`Seesaw(i2c, 0x49)`).
- Cinemate: `src/module/app/hardware_probe.py` (`I2C_BUS = 1`, seesaw register probe), `src/module/i2c/quad_rotary_controller.py`, `cinemate-install.sh` lines 1100 and 1152.
- Apertar: `apertar-core/src/hardware/NeoRotary4Input.cpp` (`loadConfig`, `verifyDevice`, `run`), `apertar-ui/src/DisplayConfigBridge.cpp` and `Ina219Bridge.cpp` (config templates), `apertar-core/src/ApertarCoreApp.cpp` ~3380 (embedded CFE automount helper), Apertar-Beta README (default display lines).
- Pi: `pinctrl get 2,3` and `i2cdetect -l` output above.

#CINEMATE
#APERTAR
