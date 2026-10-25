# Diagnosing a problem

The method, then the first commands. Every diagnosis becomes a tutorial (see `tutorials/README.md`).

## Method

1. **State the symptom exactly.** What you did, what you saw, what you expected.
2. **Check what is known.** `lessons/hardware-log.md`, `lessons/upstream-issues.md`, `sources/`.
3. **Form a belief and a prediction before running anything.** "If the DPI overlay holds GPIO 2/3,
   `pinctrl get 2,3` shows DPI_VSYNC/HSYNC." A command without a prediction teaches nothing.
4. **Run the smallest check that can prove it wrong.** Read-only first.
5. **Verdict:** confirmed / contradicted / still unknown, and the next check.
6. **Patrik confirms the interpretation**, then the finding goes into `lessons/hardware-log.md`.

## First look

User `pi` is not in `systemd-journal`, so `journalctl` needs `sudo` (Pi, 2026-10-25). One-time fix that also lets Claude read logs over SSH: `sudo usermod -aG systemd-journal pi`, then log in again.

```bash
systemctl --no-pager status apertar-core apertar-ui-direct apertar-cfe-automounter apertar-network
sudo journalctl -u apertar-core -b --no-pager | tail -100
sudo journalctl -u apertar-ui-direct -b --no-pager | tail -100
dmesg | grep -iE 'imx|cfe|rp1|i2c|nvme' | tail -40
grep -nE '^(dtoverlay|dtparam)' /boot/firmware/config.txt
cat ~/apertar-hardware.conf
free -h; vcgencmd measure_temp; vcgencmd get_throttled
```

## By area

| Area | Look at |
| --- | --- |
| Camera won't start / wrong mode | Core journal (`Selected sensor format`), `cam --list-cameras`, `dtoverlay` lines, `architecture/drivers.md` |
| I2C devices missing (encoder, hat, INA219) | `i2cdetect -l`, `i2cdetect -y <bus>`, `pinctrl get 2,3`. Seesaw probe in `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §3.5 |
| Display wrong size / wrong screen | UI journal line `Apertar display config:`, `[display]` in `apertar-hardware.conf`, connectors in `/sys/class/drm/*/status` |
| Recording drops / storage | `/media/RAW` mount (`findmnt /media/RAW`), automounter journal, write speed of the medium |
| WebUI | `curl -s http://apertar.local:8000/ | head`; it is served by Core |
| Core state | the Unix socket `/tmp/apertar-core.sock`, commands in `architecture/core.md` |

## Pi facts (2026-10-25)

| Item | Value |
| --- | --- |
| Board | Raspberry Pi 5, 4 GB, 4 cores |
| OS | Debian 13 trixie, kernel `6.12.75+rpt-rpi-2712` |
| libcamera | `0.7.1+rpt20260609-1` (dev package) |
| Image | Apertar-Beta 1.6.0 |
| Host | `apertar.local` (192.168.2.2 on the Mac's network at setup), ssh alias `apertar` |
