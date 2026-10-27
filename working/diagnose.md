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

User `pi` is in `systemd-journal` (since 2026-10-25), so `journalctl` works without `sudo`.

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
| Low frame rate, a busy thread | `top -H -b -n 2 -p $(pgrep -x apertar-core)`, then `python3 -I working/tools/usample.py <pid> <tid> 5` (no perf/gdb on the image; read-only sampler) |
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

## Pi facts (2026-10-26/27)

| Fact | Check |
| --- | --- |
| The journal persists (`/etc/systemd/journald.conf.d/50-apertar-persistent.conf`, 200 MB); before, `/etc/machine-id` was missing and Raspberry Pi OS's `40-rpi-volatile-storage.conf` kept it in RAM | `journalctl --list-boots` shows more than one boot |
| `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR` drop-in, else the IPA's per-frame "No HDR algorithm" warning rotates Core's lines away in minutes | `systemctl show apertar-core -p Environment` |
| NVMe dropped twice at PCIe Gen 3 (`CSTS=0xffffffff`, 19:35 and 22:29); Gen 2 measured 437 MB/s (16-bit 4K25 needs ~425); now back on Gen 3 (`config.txt.bak-gen3`) | `dmesg \| grep -E 'link up\|CSTS'` |
| A nearly full NVMe (77-81 %) lost frames at 16-bit 4K25 after 40-60 GB; after a format the same take was clean | `df -h /media/RAW` before long takes |
| A crash 2.5 s after a re-insert (PCIe controller reset) at Gen 3 was seen once | `journalctl -b -1 \| tail` after an unplanned reboot |
| Reading the Pi's clock: `CLOCK_BOOTTIME` is slewed by systemd-timesyncd (40-80 ppm right after a correction); compare with `CLOCK_MONOTONIC_RAW` before trusting a ppm figure | `timedatectl timesync-status` |
