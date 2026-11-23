# config.txt and libcamera files

## config.txt

Nothing changes on a stock camera. The Boot Config card in the WebUI edits these lines, if the owner wants:

- the sensor overlay per connector (`dtoverlay=imx585,cam0` and so on)
- the IMX477 / IMX585 link frequency
- `dtoverlay=rp1-clk-333mhz` (RP1 overclock, Pi 5 only)
- `dtparam=i2c_arm`, `i2s`, `spi`, `audio`
- the DPI display overlays

The card needs the root helper (see [root-helpers.md](root-helpers.md)). It keeps a backup: `config.txt.apertar.bak`.

A second sensor needs a second overlay line for cam1, then a reboot.

## Sensor drivers

The port runs with the original IMX585 and IMX283 drivers. The owner's rig uses his own driver branches. Those are separate repos and are not needed for a stock camera.

## libcamera pipeline config (optional)

`APERTAR_PIPELINE_CONFIG` names a YAML file for the Raspberry Pi pipeline handler, for example a deeper front-end queue. Give the full path. The repo ships no such file. The owner's rig uses `/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml`.

## Tuning files

Unchanged from 1.6.0. Core does not edit them. With preview temporal denoise switched off, Core writes a copy without `tdn` to `~/.cache/apertar-core/tuning/` and loads that copy.
