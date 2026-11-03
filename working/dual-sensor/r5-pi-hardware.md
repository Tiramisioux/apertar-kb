# Dual sensor, reader report 5: the Pi's hardware as it is (2026-11-03)

Read on `apertar` at 23:1x on 2026-11-03, a minute after a boot, with no take running (`get_state`: `recording:false`).
Everything here is read-only: `/proc`, `/sys/firmware/devicetree/base`, `config.txt`, `v4l2-ctl --list-devices`, `lsblk`,
`journalctl` (pi is now in `systemd-journal`). Trees on the Pi: Core `31d5418` and UI `c153c33` (both `drop-frames`),
driver `cd548ef` (`cinemate-port`, srcversion `29403D42A3919123B7FA091`), libcamera `v0.7.1+qbcfork.20260522-7-7e9fef0b`.

## Facts (CONFIRMED on the Pi)

| What | Value | How it was read |
| --- | --- | --- |
| Board | Raspberry Pi Compute Module 5 **Lite** Rev 1.0 (`c041a0`), 4 GB RAM, 4 cores, kernel `6.12.75+rpt-rpi-2712` | `/proc/device-tree/model`, `/proc/cpuinfo`, `free`, `uname` |
| Carrier board | **not identifiable by software**: no HAT EEPROM node (`/proc/device-tree/hat` absent). Patrik (2026-11-03): "the waveshare mini" = Waveshare **Mini Base Board (A) for CM5**, `CM5-IO-BASE-A` (variant A PROBABLE: it matches the NVMe on the 16-pin PCIe FFC, the RTC cell and the 40-pin header; a (B) also exists, also dual MIPI) | Patrik; Waveshare product page and wiki (below) |
| Second sensor | **none attached yet** (Patrik, 2026-11-03) | Patrik |
| The one sensor | IMX585 at `0x1a` on `i2c-10` (`10-001a imx585`) | `/sys/bus/i2c/devices/*/name` |
| Its port | **cam0**: DT node `rp1/i2c@88000/imx585@1a`; `i2c@88000` = `__symbols__/i2c_csi_dsi0` = alias `i2c10`; CSI `csi@110000` (`csi0`) `status=okay` | `__symbols__`, `aliases`, node `status` |
| cam1 port | CSI `csi@128000` (`csi1`) `status=disabled`; its I2C `i2c_csi_dsi` = `i2c_csi_dsi1` = `rp1/i2c@70000`, the **same controller as alias `i2c0`** (and `i2c11`); it enumerates as `/dev/i2c-0` | same |
| I2C adapters present | `i2c-0`, `i2c-1`, `i2c-10` (DesignWare), `i2c-13`, `i2c-14` (HDMI DDC). No `i2c-11` | `/sys/bus/i2c/devices` (`i2cdetect` is not installed) |
| Camera power | `__symbols__/cam1_reg` → `/cam0_reg`: **one regulator for both connectors** (GPIO 34, phandle `0x2d`) | `__symbols__`, `/cam0_reg/gpio` |
| Sensor sync mode | `sony,sync-mode = "internal-leader"` on the cam0 sensor node | DT property |
| config.txt (68 lines) | `[pi5]`: `dtparam=i2c_csi_dsi0=on` (l. 33), `dtparam=i2c_csi_dsi1=on` (l. 34), `dtoverlay=imx585,cam0,link-frequency=891000000` (l. 42); `[all]`: `camera_auto_detect=0` (l. 54), `dtoverlay=rp1-clk-333mhz` | `grep -n` |
| Media devices | `media0` = `rp1-cfe` (`1f00110000.csi`, csi0 only), `media1` = HEVC decoder, **`media2` and `media3` = `pispbe`** (two back-end instances) | `/sys/bus/media/devices/*/model`, `v4l2-ctl --list-devices` |
| libcamera binding | `Registered camera /base/axi/pcie@1000120000/rp1/i2c@88000/imx585@1a to CFE device /dev/media0 and ISP device /dev/media2 using PiSP variant BCM2712_D0` | Core journal, this boot |
| Camera id | `/base/axi/pcie@1000120000/rp1/i2c@88000/imx585@1a`: the I2C controller node names the port (`i2c@88000` = cam0, `i2c@70000` = cam1 on this CM5) | same |
| PiSP pixel-rate cap | `RP1_PLL_SYS request=333333333 Hz ... PiSP pixel-rate cap = 646.667 Mpix/s` (qbc fork log line) | same |
| Tuning files | `~/Tuning-Files/defaults-pisp/imx585.json` and `imx585_clearHDR.json`; **neither contains `rpi.sync`** (`grep -c` = 0) | `grep` |
| Storage | NVMe Corsair MP600 MINI 931.5 GB, `nvme0n1p2` exFAT on `/media/RAW`; PCIe link **8.0 GT/s ×1** (Gen 3 ×1). RP1 link 5.0 GT/s ×4 | `lsblk`, `current_link_speed/width` |
| Core unit | `ExecStart=/home/pi/start-apertar-core.sh`, `Restart=on-failure`, drop-ins: `ExecStartPre=/usr/local/libexec/apertar-wait-ui-core-start /run/apertar-ui/core-start-ready 8`, `LimitNICE=-5`, `LimitRTPRIO=80`, `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR` | `systemctl cat apertar-core` |
| Kernel command line (camera/memory parts) | `rp1_cfe.track_csi2_errors=1`, `numa=fake=8`, `numa_policy=interleave`, `iommu_dma_numa_policy=interleave`, `system_heap.max_order=0`, `coherent_pool=1M` | `journalctl -k` |
| Network (read 23:5x, not recording) | `eth0` 192.168.2.2/24 holds the only default route (via 192.168.2.1, DHCP); `wlan0` 10.42.0.1/24 (the camera's own network, no default route); `lo` flags `LOOPBACK,UP,LOWER_UP`, **no `MULTICAST`** | `ip -4 route`, `ip -o link show` |
| `rpi.sync` in the installed tunings | 0 in `/usr/local/share/libcamera/ipa/rpi/pisp/imx585.json` and `imx585_mono.json` too (the `~/Tuning-Files` copies are above) | `grep -c` |
| Tuning file choice | `start-apertar-core.sh` exports `LIBCAMERA_RPI_TUNING_FILE` from `APERTAR_TUNING_FILE` when it is set (l. 16-17) | `grep -n` |

## What Raspberry Pi's documentation says (compute-module page, read 2026-11-03)

- CM5 IO Board: "Two MIPI DSI/CSI-2 combined display/camera FPC connectors (22-pin, 0.5 mm pitch)".
- Camera on CAM1, CM5 only: "Fit two jumpers on J6 per the board's written instructions." (This is what Cinemate's
  `docs/dual-sensors.md` calls "connect the JC GPIO pins".)
- Second camera on CAM0: overlay with the `,cam0` suffix (`dtoverlay=imx477,cam0`); CM4: "Connect the J6 GPIO pins with two
  vertical-orientation jumpers."
- CM4 IO Board: one GPIO serves both regulator aliases, so both cameras share one regulator (the CM5 DT above does the same).
- The page gives no CM5 I2C table; on this CM5 the DT says cam0 = `i2c@88000` (`i2c-10`), cam1 = `i2c@70000` (`i2c-0`).

## The carrier: Waveshare Mini Base Board (A), `CM5-IO-BASE-A` (read 2026-11-03)

Product page (waveshare.com, `cm5-io-base-a.htm`): "4-lane MIPI interface × 2 (22pin 0.5mm FFC connector)", "Dual MIPI
interfaces ... for connecting DSI displays and CSI cameras"; "16PIN PCIe (PCIe Gen2/3 x1)" (no M.2 on the board itself: the
NVMe sits on a PCIe FFC adapter); RTC "Supports CR / ML1220 button cell"; "Raspberry Pi 40PIN GPIO header"; 85 × 56 mm.
Wiki (`waveshare.com/wiki/CM5-IO-BASE-A`): "Support dual MIPI, customers can freely choose CSI or DSI connections"; a
`dtoverlay=<sensor>,cam0` / `dtoverlay=<sensor>,cam1` line per port; "Allow one connection to DSI and one connection to CSI";
test with `libcamera-hello --list-cameras`, `--camera 0`, `--camera 1`. **No jumper, DIP switch or GPIO wiring is mentioned**
(unlike the official CM5 IO Board's J6). The page does not say which connector is MIPI0 / MIPI1 nor show two cameras at once.

So on this board: the second IMX585 goes on the other MIPI connector with `dtoverlay=imx585,link-frequency=891000000`
(cam1, the overlay default) next to the existing `,cam0` line. PROBABLE until cam1 enumerates.

## Interpretation

| Claim | Label |
| --- | --- |
| The SoC side can run two cameras: two PiSP BE instances exist, csi1 exists but is off, both camera I2C dtparams are on | PROBABLE (nothing streamed from csi1 yet) |
| A second IMX585 goes on **cam1** with `dtoverlay=imx585,link-frequency=891000000` (cam1 is the overlay default, no port word) | PROBABLE (`architecture/config.md` boot-editor rule, `architecture/drivers.md` overlay table) |
| Two sensors at `0x1a` do not collide: they are on different controllers (`i2c@88000`, `i2c@70000`) | PROBABLE |
| cam1's I2C reaching the connector depends on the carrier (on a CM5 IO Board: the J6 jumpers) | PROBABLE (documentation) |
| The KB's "possible bug" (the `cam0` overlay parameter retargets only one regulator fragment, `architecture/drivers.md:112`) cannot bite on this CM5: both labels are one node | PROBABLE |
| Two sensors share one power-enable line: one sensor cannot be powered off alone | PROBABLE |
| Both raw streams cross the same RP1 link (×4 Gen 2) and the same SDRAM; both DNG streams go to one Gen 3 ×1 NVMe | CONFIRMED (topology); the load it means is in `r4-platform.md` |
| libcamera's own `rpi.sync` (UDP multicast to 239.255.255.250, no interface chosen, `r4-platform.md` Q3) would leave through `eth0` while a cable is in; without one no route matches 239.255.255.250 (`wlan0` has only 10.42.0.0/24, `lo` is not multicast), so its sends probably fail in the field. The phase lock needs no network | PROBABLE (routes CONFIRMED; the send failure is not tried) |

## Unknown: what Patrik has to tell or check

| Question | How to settle |
| --- | --- |
| ~~Which carrier board?~~ Answered: Waveshare Mini Base Board (A), two 4-lane 22-pin MIPI connectors, no jumpers documented. Still open: which physical connector is MIPI1 (cam1) | the board's silkscreen |
| ~~Is a second sensor at hand?~~ Answered: not yet. Which model will it be (a second IMX585 keeps every setting valid on both)? | Patrik |
| Sync: Patrik (2026-11-03) wants Cinemate's **phase lock** to do it, in software. The IMX585's XVS/XHS hardware sync is then not needed | design §sync |
| Does cam1 enumerate with the overlay added? | after Patrik adds the line and reboots: `cat /sys/bus/i2c/devices/*/name`, `v4l2-ctl --list-devices` (a second `rp1-cfe`), Core journal `Registered camera ... i2c@70000 ... ISP device /dev/media3` |
