# Hardware log

Append-only. One entry per finding Patrik confirmed on the Pi. Newest at the bottom.

Entry format:

```
## YYYY-MM-DD: <one-line finding>
- Tested: <rig, image/commit, what was run>
- Worked: <what held>
- Did not work: <what failed, or "n/a">
- Why: <the mechanism, with path:line or command output>
- Confirmed by: Patrik, <how: "now it works", a reading, a take>
- Tutorial: <Obsidian note name, if one was written>
```

---

## 2026-10-23: DPI overlays on the stock image remove `/dev/i2c-1` on an HDMI rig

- Tested: Pi 5, Apertar-Beta 1.6.0, IMX585 on cam0, RPI5-CFE-Hat, Adafruit NeoRotary 4 on the hat's
  Qwiic hub, HDMI display (no DPI panel).
- Worked: commenting out `config.txt` lines 76-78 (`vc4-kms-DPI-4inch`, `waveshare-4dpi`,
  `waveshare-touch-4dpi`) and rebooting. `/dev/i2c-1` appeared; hat `0x34` and encoder `0x49`
  found on bus 1; `[cfexpress_hat] bus=1`, `[neorotary4] enabled=true bus=1 address=0x49`.
- Did not work: `dtparam=i2c_arm=on` alone. The DPI overlay claims GPIO 0-27 whether or not a
  panel is attached (`pinctrl get 2,3` showed `DPI_VSYNC`/`DPI_HSYNC`).
- Why: see `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §3.2-3.4. Side effect: with the DPI
  connector gone, HDMI became the main touch-UI screen at the 720x720 `[display]` size
  (`run_pi_direct.sh:138-166` at upstream-1.6.0; the source note says 135-160); fixed via `[display]` keys (§4.5).
- Confirmed by: Patrik at the rig, "now it works".
- Tutorial: `20261025152945 CINEMATE APERTAR start-tutorials` (the format reference).
- Still open: how the hat reaches `i2c-10` (JP3/JP4?), where the IMU is wired, which overlay gives
  `/dev/i2c-4`.

## 2026-10-25: tally LED on GPIO 21 needs the `[recording_indicator]` section, not `d21=recindicatorled`, with Cinemate wiring

- Tested: Pi 5, Apertar-Beta 1.6.0 (Core fork `main` ed400ba), LED wired as on Cinemate: `GPIO21 -> resistor -> LED -> GND`.
- Worked: `[recording_indicator] enabled=true target=gpio line=21 active_high=true`; `[trigger_output] enabled=false`;
  `[pcf8574] enabled=false`; `d21=recindicatorled` removed; Core restarted. Journal: `recording indicator LED enabled:
  target=gpio active_high=true gpio=/dev/gpiochip0 line=21 open_drain=false`; `gpioinfo`: `apertar-rec-led` on line 21.
- Did not work: (1) the image's template `[recording_indicator] enabled=true target=pcf8574 bus=10 address=0x20 pcf_pin=7`
  won over `d21`, and with no chip at `0x20` Core logged `Could not write PCF8574 recording indicator output: Remote I/O error`.
  (2) Setting `[gpio_buttons] active_low=false` does not change the LED; it flips the d10/d6 button inputs (put back to `true`).
- Why: an enabled section returns before the shorthand counts (`RecordingIndicatorOutput.cpp:382-387`); the shorthand
  has no polarity key and inherits `active_high` from a section above it, default `false` (`:320-326`). `[trigger_output]`
  starts first (`ApertarCoreApp.cpp:6881` vs `:6893`) and would hold line 21. Config is read only at Core start.
- Confirmed by: Patrik at the rig, "now it works".
- Tutorial: `20261025193414 CINEMATE APERTAR tally-gpio21-tutorial` (T17, now in `APERTAR/_archive/`).
