# Q6: the CSI-2 link (1782 vs 1440 Mbps/lane) and the RP1 clock, for 16-bit Clear HDR 4K at 30 fps

Reader q6-link · trees: imx585-apertar `98b9862`, imx585-v4l2-driver `18c1eb2`, libcamera-qbc `7e9fef0`
(IPA files identical in libcamera-apertar `6b0b49f`: `git diff 7e9fef0 6b0b49f --stat` touches only `pipeline/rpi/pisp/`),
libcamera (cinemate) `bfe0b76`, kernel rpi-6.12.y `5bd564a` (the Pi runs 6.12.75), cinemate `d6cc93e`,
cinemate-handbook `c99ff77`, will127534/rp1-overclock-tool `eace52d` (cloned read-only into the session scratchpad),
github.com/will127534/imx585-v4l2-driver README (web) · 2026-10-26.

Labels: **CONFIRMED** = I opened the line or page and it says so. **PROBABLE** = derived, reasoning given.
**UNCONFIRMED** = needs the Pi or a source I could not reach (datasheets.raspberrypi.com, kernel.org and docs.kernel.org
failed DNS from this container, so the RP1 and PiSP PDFs were not read).

## Short answer

1. **The link does not cause the 30 fps loss.** (PROBABLE, strong.) Frame and row timing come from HMAX/VMAX and the
   74.25 MHz INCK, not from the link. 25 fps runs the same HMAX 550 at the same 1782 Mbps, so it sends the same row bursts,
   and it is clean. Preview at 30 fps is clean too. The gaps follow a throughput deficit (first gap after 27-47 frames,
   then one every 5-9), not random link errors.
2. **1440 Mbps cannot do 30 fps in either driver.** (CONFIRMED arithmetic.) Both tables give HMAX 660 at 720 MHz, and
   74.25e6 / (660 x 4500) = 25.00 fps. At 1782 Mbps it is HMAX 550: 74.25e6 / (550 x 4500) = 30.00 fps. That table is
   built for 12-bit SDR, where the sensor sends one row per HMAX. In Clear HDR a 16-bit row probably fits a 1440 link at
   HMAX 550 (PROBABLE). So "30 fps needs 1782" comes from the driver table, not from link bandwidth.
3. **"CSI-2 counters 0" only rules out receiver FIFO overflow and some packet-header damage.** (CONFIRMED from code.)
   `track_csi2_errors` counts FIFO overflows and four discard types (overflow, length limit, unmatched, inactive). It does
   not count CRC, ECC or SoT errors: the CSI host interrupt is never enabled. In 16-bit mode `csi_dt = 0`, so "unmatched"
   is weakened too. Out of range, the D-PHY only logs an error and programs the 1450-1500 Mbps band; the data still streams.
4. **The RP1 clock only limits the frame rate in software, and on the Apertar Pi that limit does not bind.** (PROBABLE.)
   The qbc IPA stretches the line length to `width / (2 x clk_sys - 20 MPix/s)`, with clk_sys taken from the device-tree
   request. With `dtoverlay=rp1-clk-333mhz` the cap is 646.67 MPix/s, above the driver's 518.4 MPix/s, so 30 fps stays.
   On a stock RP1 the cap would be 380, giving 4500 x 3840 / 380e6 = 45.47 ms, i.e. 21.99 fps. That is Cinemate's
   "21.99 stock" figure: an IPA ceiling, not a recording result. In Clear HDR the sensor probably sends one row per 2 HMAX,
   so the real CSI2-to-FE rate is about 259 MPix/s. That is under even the stock bound, which makes the cap roughly 2x too
   strict for this mode.
5. **A faster RP1 clock would not help recording.** (PROBABLE.) The CFE writes to DRAM over a PCIe Gen2 x4 link: about
   2.0 GB/s raw, against a 0.51 GB/s average and 0.89 GB/s peak demand. Contention happens on the BCM2712 side (DRAM, back
   end, CPU, NVMe on pcie1), and the RP1 clock does not reach there. The Pi probably already runs clk_sys at 333 MHz. The
   kernel caps `clk_sys` at 200 MHz (`max_freq`), and the overlay gets past that only because clk_sys keeps divider 1 when
   pll_sys is raised.

## 1. The 16-bit Clear HDR 3840x2200 mode (brief Q6 a)

### 1.1 What the Apertar driver programs (imx585-apertar @ 98b9862)

| Item | Value | Where (CONFIRMED) |
| --- | --- | --- |
| Lanes | 2 or 4 from DT; overlay default `data-lanes = <1 2 3 4>`; HMAX x2 for 2 lanes | `imx585.c:2502-2507`, `imx585-overlay.dts:11`, `imx585.c:1507` |
| Link options | 297, 360, 445.5, 594, **720 (1440 Mbps)**, **891 (1782 Mbps)**, 1039.5, 1188 MHz; overlay default 720 MHz | `imx585.c:244-275`, `imx585-overlay.dts:77-78` |
| Min HMAX, 4-lane, by link | 1584, 1320, 1100, 792, **660**, **550**, 440, 396 | `imx585.c:277-286` (`HMAX_table_4lane_4K`) |
| HMAX/VMAX clock | `IMX585_PIXEL_RATE` 74,250,000 | `imx585.c:211` |
| Mode entry | width 3840, height 2160 + 2 x 20 = 2200, `min_hmax` 550, `base_vmax` = `IMX585_VMAX_DEFAULT` 2250 | `imx585.c:1194-1220`, `:111` |
| Clear HDR scaling | `hdr_scale = 2` on **VMAX only**; HMAX = table / `hmax_div`, no Clear HDR floor | `imx585.c:1504-1525` |
| Reported pixel rate | `width x 74.25 MHz / min_hmax` ("pixel rate proxy"); HBLANK range 0 .. `0xffff x rate / 74.25 MHz - width` | `imx585.c:1538-1548` |
| HBLANK to HMAX | `HMAX = min_hmax x (width + hblank) / width` (integer divide) | `imx585.c:1678-1689` |
| VMAX/HMAX limits | VMAX 20 bits (`0xfffff`), HMAX 16 bits (`0xffff`) | `imx585.c:109-115` |
| README | 4K 12-bit 4-lane: 50 fps at 1440, 60 at 1782; "For ClearHDR mode the framerate will be half"; "~43.8 FPS @ 4K" without an RP1 overclock | `README.md:110-121` |

Every value below is computed with INCK = 74.25 MHz.

| | 1782 Mbps (891 MHz) | 1440 Mbps (720 MHz) |
| --- | --- | --- |
| HMAX (min) | 550 | 660 |
| Line time 1H = HMAX / 74.25 MHz | 7.407 us | 8.889 us |
| VMAX (min) = 2250 x 2 | 4500 | 4500 |
| Frame time = VMAX x 1H | 33.33 ms | 40.00 ms |
| **Max fps** | **30.00** | **25.00** |
| Driver pixel rate = 3840 x 74.25e6 / HMAX | 518.4 MPix/s | 432.0 MPix/s |
| Output row period, if one row per 2H (PROBABLE, §1.2) | 14.815 us | 17.778 us |
| Active readout = 2200 rows x 2H | 32.59 ms | 39.11 ms |
| Vertical blanking left at the minimum VMAX | 0.74 ms | 0.89 ms |

The time on the wire for one 16-bit row on 4 lanes is computed below (CONFIRMED arithmetic; the D-PHY HS
entry/exit overhead is an assumption).

- Payload: 3840 px x 2 B = 7680 B. A CSI-2 long packet adds a 4 B header and a 2 B CRC: 7686 B in total.
- Per lane: 7686 / 4 = 1921.5 B = 15,372 bits, plus the sync byte. Add roughly 0.2-0.4 us of HS prepare/zero/trail and
  LP-11 per packet (MIPI D-PHY timing, not measured).
- At 1782 Mbps: 15,372 / 1782e6 = **8.63 us** of HS data per row. That is 58 % of a 14.815 us row period (about 61 % with
  the HS overhead).
- At 1440 Mbps with HMAX 660: 15,372 / 1440e6 = **10.68 us**. That is 60 % of 17.778 us.
- At 1440 Mbps with HMAX 550 (the hypothetical 30 fps case): 10.68 / 14.815 = **72 %**, about 75 % with overhead.
- For comparison, 12-bit SDR (one row per H): (4 + 5760 + 2) x 8 / 4 / 1782e6 = 6.47 us of a 7.407 us line (87 %). At
  1440 it is 8.01 us of 8.889 us (90 %).

So the HMAX table works out to "the 12-bit row must fit in 1H". The product HMAX x link MHz stays roughly constant across
the table: 550 x 891 = 490k, 660 x 720 = 475k, 1100 x 445.5 = 490k. (PROBABLE.)

### 1.2 One row per HMAX, or per 2 x HMAX, in Clear HDR? (PROBABLE: per 2H)

Evidence:

- Both drivers double VMAX, not HMAX, in Clear HDR (`imx585.c:1509,1517`@98b9862; `imx585-v4l2-driver/imx585.c:3274,3301`
  @18c1eb2).
- will127534's README says "For ClearHDR mode the framerate will be half" (`README.md:121`).
- Cinemate's driver comment says Clear HDR "always does the dual HG+LG read, so the line readout has a higher minimum (~HMAX
  550 at 4-lane)" (`imx585-v4l2-driver/imx585.c:3305-3313`@18c1eb2).
- A 16-bit row needs 8.63 us on a 1782 link but a 1H line lasts 7.407 us. If the sensor sent one row per H, a row could
  not fit on the link at all.

Whatever the exact timing, 2200 rows in 4500 H gives an average row period of 33.33 ms / 2200 = 15.15 us, i.e. an average
of 253 MPix/s, about half the 518.4 MPix/s the driver reports. The Sony datasheet would settle the per-row timing
(UNCONFIRMED). E3 below measures it.

### 1.3 Cinemate's driver (imx585-v4l2-driver @ 18c1eb2): same timing for this mode

- Same link and HMAX tables at 720 and 891 MHz (660 and 550): `imx585.c:288-303`. The 4K 16-bit entry is "unchanged":
  `HMAX_table_4lane_4K_12bit`, `min_vmax` 2250, scaled x2 (`imx585.c:1719-1727`, `:3300-3301`). (CONFIRMED.)
- The one difference is a Clear HDR floor: `IMX585_HMAX_MIN_CLEARHDR 550` (`imx585.c:120-121`), applied as
  `h = max(h, 550 x lane_scale)` (`:3314`). The README explains why: at 2079 Mbps the table's HMAX 440 "loses roughly 94%
  of its rows" in Clear HDR, so Clear HDR runs at 2079 with "exactly the same sensor line timing it uses at 1782"
  (`README.md:233-241`). (CONFIRMED.)
- **The Apertar driver has no such floor** (grep for `HMAX_MIN`: no match). At `link-frequency=1039500000` it would program
  Clear HDR HMAX 440 and advertise 74.25e6 / (440 x 4500) = 37.5 fps, which is the timing Cinemate saw break.
  (CONFIRMED code; the breakage is Cinemate's observation.) This does not affect the Pi today (891 MHz), but it is a trap if
  someone raises the link to "fix" 30 fps.
- The floor matters for Q6: the sensor fails below HMAX 550 in Clear HDR even when the link has spare capacity. So 550 is
  probably the sensor's own Clear HDR limit (two conversions per row), which makes 30 fps the sensor ceiling for 4K Clear HDR
  at VMAX 4500. (PROBABLE.)

## 2. Does 1782 vs 1440 change anything at 30 fps? (brief Q6)

| Question | Answer | Label |
| --- | --- | --- |
| Can 1440 run 30 fps? | No, not in either driver: HMAX 660 gives 25.00 fps. 30 fps would need HMAX 550 at 1440, which the link probably carries (72-75 % of the row period) but which needs a driver change, and the sensor must accept it. | CONFIRMED (driver), PROBABLE (link fit), UNCONFIRMED (sensor) |
| Does the link set the frame period or the readout time? | No. Frame = VMAX x HMAX / INCK; readout = rows x 2H. The link only sets how long each row's burst lasts inside its row period. | CONFIRMED (driver math), PROBABLE (2H) |
| Does the link rate change any CFE software path? | Only one place: `dphy_rate` is set in `cfe.c:1175` and used once, for `hsfreqrange`, in `dphy.c:142`. Nothing else in rp1_cfe reads it. | CONFIRMED (grep `dphy_rate`) |
| Does 25 fps use the same link pattern as 30 fps? | Yes. At 25 fps the IMX585 helper keeps HMAX 550 and sets VMAX 5400: 74.25e6 / 25 = 2,970,000 ticks / 550 = 5400, exact and even, so `getBlanking` stops at the minimum HMAX (`cam_helper_imx585.cpp:126-205`@7e9fef0). KB: "Core runs VMAX 5400 (25 fps)" (`working/clearhdr-design.md:120`). The row bursts are identical; only the vertical blanking grows (0.74 -> 7.41 ms). | CONFIRMED (code + KB) |
| Then can link errors explain loss at 30 but not 25? | Only if errors depended on vertical blanking, and the receiver is idle during blanking. Errors per frame would be the same at 25 and 30 fps, but 25 fps lost 0 frames in every take (brief §3) and preview at 30 fps lost 0 frames. | PROBABLE |
| Does the gap pattern fit link errors? | No. Link errors would be random (Poisson). The observed pattern (exactly one frame, every 5-9 frames, first gap after 27-47 frames) is a steady deficit that first eats the 8-buffer slack (brief §3; hardware-log 2026-10-26 "steady single-frame skip"). | PROBABLE |

## 3. The RP1 D-PHY out of range, and what the CSI-2 counters cover (brief Q6 b)

### 3.1 What out-of-range programming does (CONFIRMED, rpi-6.12.y 5bd564a)

- The link rate is taken from the sensor's `V4L2_CID_LINK_FREQ` x 2. With 891 MHz that gives "Using a link rate of 1782
  Mbps" (`rp1_cfe/cfe.c:1055-1101`; `imx585.c:1959` registers the control).
- `dphy_set_hsfreqrange()` logs `DPHY: Datarate %u Mbps out of range` when the rate is above 1500 (or below 80), but it
  does not return. The lookup loop stops at `ARRAY_SIZE - 1`, so 1782 is programmed with the last bin `{1500, 0b111100}`
  through test code `0x44` (`dphy.c:99-129`). Streaming then continues normally (`dphy.c:131-157`). The table cites "Table
  5-1 on page 65 of dphy databook", which is not public.
- What the band controls inside the Synopsys DW D-PHY (settle counter, CDR/equaliser range) is UNCONFIRMED. The receiver
  runs on silicon margin above 1500. Cinemate's driver README says the same ("streams on silicon margin", `README.md:243-248`
  @18c1eb2).
- Empirical integrity at 1782 on other boards (CONFIRMED as recorded, other hardware):
  - Cinemate's CM5 mono rig was "clean on 16/16 short takes at both clocks" (`cinemate-handbook/lessons/hardware-log.md:958-959`).
  - Its colour rig was "all seven modes clean including 16-bit Clear HDR" (`imx585-v4l2-driver/README.md:250-255`).
  - Apertar's DNGs decode with the expected values (hardware-log 2026-10-26 L2 entry: median 3643 vs 3625).
  - Margin on the Apertar board itself is UNCONFIRMED.

### 3.2 What `rp1_cfe.track_csi2_errors=1` counts (CONFIRMED)

- The parameter (`csi2.c:18-21`) unmasks five CSI2-DMA interrupts at stream start: `IRQ_OVERFLOW`, `DISCARD_OVERFLOW`,
  `DISCARD_LENGTH_LIMIT`, `DISCARD_UNMATCHED`, `DISCARD_INACTIVE` (`csi2.c:49-59`, `:447-451`).
- The ISR then counts `Overflows` and adds the discarded amount per VC for the four discard kinds (`csi2.c:219-259`, `csi2_isr_handle_errors`).
- `csi2_errors` in debugfs prints these counters and **clears them on every read** (`csi2.c:175-217`, reset at `:190-192`).
  An experiment must read once before the take and once after.

It does **not** cover the following (CONFIRMED from code):

- **CSI-2 protocol errors** (ECC, CRC, SoT/SoT-sync, frame sync). Those are flagged by the DW CSI-2 host, whose interrupt
  `MIPICFG_INT_CSI_HOST` (`cfe.c:75`) is never enabled. Only `CSI_DMA` and `PISP_FE` are (`cfe.c:1155`). Payload CRC errors
  therefore pass through silently as pixel damage.
- **FE errors.** `FE_ERROR_STATUS` is read in the FE ISR but only printed in verbose debug (`pisp_fe.c:195-209`).
- **Buffer starvation.** "has no buffer, unable to schedule job" is `cfe_dbg_verbose` (`cfe.c:624`). The T22 record shows
  takes with gaps and all counters 0 (hardware-log 2026-10-26 25 fps entry: dd to tmpfs, 11 intervals > 60 ms). So
  starvation drops do not increment these counters. (PROBABLE: those gaps were starvation.)
- **The 16-bit special case.** The format table uses `csi_dt = 0` "to avoid RP1 HW mismatch for 16-bit modes"
  (`cfe_fmts.h:221-226`, `cfe.c:855-856`), so the channel accepts every data type. The imx585 driver relies on this (the 20
  OB rows arrive with a different DT, `imx585.c:547-557`). A header whose DT bits were corrupted would be accepted rather
  than counted as UNMATCHED. (PROBABLE from those comments; RP1 CSI2 behaviour is undocumented.)

What would still be visible (CONFIRMED code; when it would fire is PROBABLE):

- A lost frame-end short packet leaves `cur_frm` set at the next FS. That triggers
  `WARN("... Orphanded frame at seq %u")`, a dmesg line with a stack trace (`cfe.c:684-686`).
- "Handling missing previous FE interrupt" is debug only (`cfe.c:804`).

**Verdict on "counters 0":** it rules out receiver FIFO overflow, i.e. a CFE that cannot get its writes into memory. It
rules out gross header damage only partly. It says nothing about CRC or SoT errors. The link is exonerated by the timing
argument in §2, not by the counters. (PROBABLE.) Also, the brief's counter reading comes from T22 (25 fps, lossless, dd
load). **No counter reading at 30 fps uncompressed is recorded** (UNCONFIRMED; experiment E2).

## 4. The pixel-rate cap and the RP1 clock (brief Q6 c)

### 4.1 The cap in the libcamera the Pi runs (qbc 7e9fef0; identical in apertar 6b0b49f)

- **Which hardware it models.** The PiSP hardware entry sets `.minPixelProcessingTime = 1.0us / pispPixelRateMpixPerS()`
  (`src/ipa/rpi/controller/controller.cpp:215`). The comment calls the bottleneck "the rate of pixels going from CSI2
  peripheral to ISP-FE (400Mpix/s, plus tiny overheads...)" and notes "a 64kbit data FIFO before the bottleneck"
  (`:192-213`). That comment comes from upstream libcamera commit `27159861` "ipa: rpi: Add hardware line rate constraints"
  (Naushir Patuck, 2024-01-04, present in Cinemate's libcamera history). (CONFIRMED.)
- **How the rate is derived.** `detectPispPixelRateMpixPerS()` reads the *requested* RP1_PLL_SYS (entry 2) and
  PLL_SYS_CORE (entry 0) from `/sys/firmware/devicetree/base/axi/pcie@1000120000/rp1/clocks@18000/assigned-clock-rates`.
  It snaps the request to `core / N` and returns `2 x clk - 20` MPix/s (`:59-68`, `:103-147`). (CONFIRMED.)
  - Stock gives 200 x 2 - 20 = **380**. A rate outside 0.5-4x of stock also falls back to 380 (`:124-135`), and so does a
    missing DT node (logged at Debug only, `:106-110`).
  - 333.33 MHz gives **646.67** ("PiSP pixel-rate cap = ..." at Info, `:139-145`).
  - The code assumes clk_sys = pll_sys ("divider of 1", `:52-54`) and does not read the live clk_sys. (CONFIRMED.)
- **Who uses it.** `IpaBase::setMode` computes `minLineLength = sensor minLineLength / pixelRate`, with sensor
  minLineLength = width + hblank.min (`camera_sensor_raw.cpp:1044` / `camera_sensor_legacy.cpp:927`). If
  `minLineLength / width < minPixelTime`, it raises minLineLength to `minPixelTime x width` and logs "Adjusting mode minimum
  line length ... because of ISP constraints." The minimum frame duration then becomes `minFrameLength x minLineLength`
  (`src/ipa/rpi/common/ipa_base.cpp:612-651`). (CONFIRMED.)
- **No env-var override in qbc.** Zero `MAX_PIXEL_RATE` hits (also verified in `working/compare-raw/c1-probe-compare.md`
  F12). Cinemate's fork does the opposite: no DT read, only `LIBCAMERA_RPI_MAX_PIXEL_RATE`, default 380
  (`libcamera(cinemate)/src/ipa/rpi/controller/controller.cpp:82, 114-141`@bfe0b76). (CONFIRMED.)

Arithmetic for 3840 wide, 16-bit, driver pixel rate 518.4 MPix/s, minLineLength 3840 px (hblank min 0, `imx585.c:1548`):

| Cap (MPix/s) | minPixelTime | Sensor pixel time 1/518.4e6 | Line length used | Min frame = 4500 x line | Max fps |
| --- | --- | --- | --- | --- | --- |
| 380 (stock) | 2.632 ns | 1.929 ns, **binds** | 3840 x 2.632 ns = 10.105 us | 45.47 ms | **21.99** |
| 580 (Cinemate overclock value) | 1.724 ns | does not bind | 7.407 us | 33.33 ms | 30.00 |
| 646.67 (qbc at 333.33 MHz) | 1.546 ns | does not bind | 7.407 us | 33.33 ms | 30.00 |

On a stock RP1 the IPA asks for HBLANK = 10.105 us x 518.4e6 - 3840 = 1398.6 px. The driver turns that into
HMAX = 550 x (3840 + 1399) / 3840 = 750, and 74.25e6 / (750 x 4500) = **22.0 fps**. Keeping 30 fps needs a cap of at least
30 x 4500 x 3840 = 518.4 MPix/s. (CONFIRMED arithmetic. The same numbers are in
`working/compare-raw/c1-probe-compare.md` F13.)

### 4.2 Cinemate's model and documents

- **rp1_regime.py.**
  - It says "The PiSP CSI2-to-ISP-FE bottleneck scales with the RP1 clock" (`cinemate/src/module/rp1_regime.py:3`) and
    sets `PIXEL_RATE_STOCK = 380.0`, `PIXEL_RATE_OVERCLOCKED = 580.0` ("Measured on a CM5", `:70-72`).
  - The regime is decided from an uncommented `dtoverlay=rp1-overclock` line plus a config.txt-mtime-vs-boot guard
    (`:80`, `:154-200`). The live clk_sys is only logged, because "on 6.12.93 `clk_sys` read ~333 MHz in both regimes"
    (`:27-38`).
  - Direction of error: "Over-stating it overruns the FIFO mid-line and corrupts every mode wide enough for this bound to be
    what limits the line time" (`:19-25`).
  - (CONFIRMED.) It models the CSI2-to-FE throughput on the RP1, as the libcamera comment does.
- **Mode table.** docs/sensors.md lists `| 4 | ClearHDR | 3840 x 2200 | 16 | all-pixel | 21.99 | 30.00 | 16.9 |`
  (`docs/sensors.md:38`). The figures are "taken at the sensor's highest link frequency, 1039.5 MHz"; "Max FPS" means
  `--max-pixel-rate 380` and "overclocked" means 580 (`:40-42`; changelog `docs/changelog.md:45-49`). (CONFIRMED.)
  - Both numbers equal the IPA arithmetic in §4.1 to two decimals: at 2079 the Clear HDR floor keeps HMAX 550, so the
    driver pixel rate is again 518.4. They are therefore advertised ceilings (what `--list-cameras` reports), not recording
    results. (PROBABLE.)
  - The 12-bit SDR 4K row fits the same model. HMAX 472 at 2079 gives a driver rate of 3840 x 74.25e6 / 472 = 604 MPix/s.
    A 380 cap pads the line to 10.105 us, so the frame is 2250 x 10.105 us = 22.74 ms, i.e. 43.98 fps; a 580 cap gives
    2250 x 6.621 us = 14.90 ms, i.e. 67.13 fps (`sensors.md:36`: 43.98 / 67.13). (CONFIRMED arithmetic.)
- **Overlay docs.** docs/overclocking.md: the overlay is "installed but off", and both directions need a reboot
  (`:1-16`). The installer's `rp1-overclock` overlay rewrites the whole `assigned-clock-rates` array with RP1_PLL_SYS
  (entry 2) and RP1_CLK_SYS (entry 7) set to 300,000,000 (`cinemate-install.sh:734-792`). docs/config-txt.md marks link
  rates above the RP1 spec as "— over RP1 spec" (`:21-23`). (CONFIRMED.)
- **Handbook** (`cinemate-handbook/lessons/hardware-log.md`@c99ff77):
  - 2026-08-26 (`:286-335`): the 300 MHz overlay request gave `pll_sys` and `clk_sys` both 333333333 and `pll_sys_pri_ph`
    166666666; there was no rp1 node in `/proc/device-tree` on that CM5 6.12.93 (`:300-307`). (CONFIRMED as recorded.)
  - 2026-08-26 (`:340-399`): the ceiling reaches `--list-cameras`. 3856x2180 12-bit went 66.85 -> 43.80 when moving from
    580 to 380 ("the bound constrains *line time*, not frame throughput").
  - 2026-08-27/28 matrix (`:945-985`): "The overclock buys no frame rate here. Advertised fps was identical with it on or off
    at every link rate (21.99 @1440, 30.00 @1782)" (`:969-972`). Recommended default "1440 Mbps / stock clock" (`:985`).
  - **That matrix does not fit the 380/580 model.**
    - At 1440 (HMAX 660, 432 MPix/s) a 580 cap gives 25.00 fps, not 21.99.
    - At 1782 a 380 cap gives 21.99, not 30.00.
    - So the cap in each cell followed something other than the overlay. In the same session `rp1_regime` "passes
      --max-pixel-rate 580 with the overclock overlay commented out" (`:855-857`). The matrix cannot isolate a clock effect.
      (PROBABLE.)
  - 2026-09-15 (`:3135-3175`): a `config.txt` rewrite after boot dropped the regime to 380, which "caps 3840×2200 16-bit at
    **21 fps**".

### 4.3 Reconciling with "preview-only delivers 30.00 fps" on the Apertar Pi

| Explanation | Verdict | Evidence |
| --- | --- | --- |
| The Pi already runs an RP1 clock overlay | **Yes (PROBABLE, nearly CONFIRMED)** | `dtoverlay=rp1-clk-333mhz` at config.txt line 65 (`sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:38`). The KB records the qbc log line "RP1_PLL_SYS request=333333333 Hz ... PiSP pixel-rate cap = 646.667 Mpix/s" (`working/clearhdr-design.md:88`, `working/handoff-clearhdr-buffering.md:29`). The raw journal line is not kept in the KB. |
| The limit is not active in this libcamera | No | The code is unconditional for PiSP (`controller.cpp:215`, `ipa_base.cpp:620-639`). |
| The limit is active but does not bind for this mode | **Yes, because of the overlay** | 646.67 >= 518.4 (§4.1). On a stock RP1 it would bind and give 21.99 fps, so a 30.00 fps preview would be impossible. That 30.00 is itself evidence the cap is >= 518.4. (PROBABLE.) |

`rp1-clk-333mhz` is the name will127534/rp1-overclock-tool installs. The generated overlay "re-specifies every slot to its
current value, modifying only `RP1_PLL_SYS` and `RP1_CLK_SYS`", to 333.33 MHz (`README.md:9-15, 24-38, 159-165`@eace52d).
The tool's tested row is "Pi 5 Model B 8GB | 6.12.75+rpt-rpi-2712 | ... | OK" (`README.md:120-122`), the same kernel
release as the Apertar Pi. It documents two checks: `cat /sys/kernel/debug/clk/clk_sys/clk_rate # expect 333333333`
(`:62`) and `LIBCAMERA_LOG_LEVELS=RPiController:1 rpicam-hello --list-cameras ... | grep RP1_PLL_SYS` (`:68-71`). (CONFIRMED.)

### 4.4 Is the cap physically right for Clear HDR? (PROBABLE: about 2x too strict)

The IPA checks the sensor's *reported* pixel rate, which assumes one row per HMAX (`imx585.c:1538-1540`). If Clear HDR
sends one row per 2H (§1.2):

- **Average rate into CSI2-to-FE:** 3840 / 14.815 us = **259.2 MPix/s**, below the stock 380.
- **Per-row burst at 1782:** 4 x 1782e6 / 16 = **445.5 MPix/s** for 8.62 us.
  - With a stock 380 MPix/s drain, the backlog is 3840 - 380 x 8.62 = 565 px = 9.0 kbit, against the "64kbit data FIFO"
    (`controller.cpp:205-213`).
  - The row drains in 3840 / 380 = 10.1 us, inside the 14.8 us row period.
- **At 2079 Mbps (Cinemate's measurement link):** backlog 1032 px = 16.5 kbit, which also fits.
- **12-bit SDR 4K60** is different. One row per H gives an average of 518 MPix/s, above 380, so the backlog grows row after
  row. There the cap is physically needed, which matches Cinemate's warning in `rp1_regime.py:19-25`.

So a stock RP1 would probably carry 16-bit Clear HDR 4K30 at 1782 Mbps, and the "21.99 fps stock" limit comes from the IPA
model rather than the hardware. This is moot on the Apertar Pi, where the cap is 646.67 and does not bind. Two things are
UNCONFIRMED: the 2H row timing (E3 measures it) and the FIFO behaviour, which is documented only in the libcamera comment.
**Do not over-state the cap on a stock board on the strength of this.** The same cap protects the 12-bit SDR modes.

## 5. Does the RP1 clock govern the CFE's DMA path into DRAM? (brief Q6 d)

What the code says (CONFIRMED, rpi-6.12.y 5bd564a):

- **clk_sys.** Parents xosc / pll_sys, `.max_freq = 200 * MHz`, `CLK_IS_CRITICAL` "Always enabled in hardware"
  (`drivers/clk/clk-rp1.c:1846-1860`).
- **Stock DT.** `RP1_PLL_SYS` 200 MHz (entry 2) and `RP1_CLK_SYS` 200 MHz (entry 7)
  (`arch/arm64/boot/dts/broadcom/rp1.dtsi:30-59`).
- **The CFE's own clock.** The CFE node lists only `RP1_CLK_MIPI0_CFG` at 25 MHz, a configuration clock with `max_freq`
  50 MHz (`rp1.dtsi:1018-1035`, `clk-rp1.c:2052-2062`). The DT names no data-path clock for CSI2/FE, so they run on an
  implicit system clock. The DT lists `RP1_CLK_SYS` as the clock of the i2c/spi peripherals (`rp1.dtsi:168-377`).
- **The kernel refuses clk_sys above 200 MHz.** `rp1_clock_choose_div_and_prate()` returns `calc_rate = 0` for any parent
  choice above `max_freq` ("Prevent overclocks", `clk-rp1.c:1325-1334`). `rp1_clock_determine_rate()` then returns
  `-EINVAL` when no parent works (`:1339-1386`). `of_clk_set_defaults` logs
  `clk: couldn't set %s clk rate to %lu (%d), current rate: %lu` and carries on (`drivers/clk/clk-conf.c:147-151`).

**How the overlay still reaches 333 MHz** (PROBABLE, my reading of the code; it matches the 333333333 that Cinemate and
will127534 measured):

1. The DT order sets `RP1_PLL_SYS` (entry 2) first. pll_sys goes to 1000/3 = 333.33 MHz.
2. clk_sys sits on pll_sys with divider 1 (it was 200/200), so it follows to 333.33 MHz.
3. Entry 7 (`RP1_CLK_SYS` = 333.33 MHz) is refused against the 200 MHz `max_freq`. clk_sys stays at 333.33 MHz.
4. Prediction: dmesg holds "clk: couldn't set clk_sys clk rate to 333333333 (-22), current rate: 333333333".
5. Corollary: an overlay that raised only pll_sys and left entry 7 at 200 MHz would get clk_sys = pll_sys / round(1.667) =
   **166.7 MHz, slower than stock**. Meanwhile qbc, which reads only entry 2, would still report 646.67. Hence E1.

Does clk_sys clock the FE's output DMA, the RP1 AXI fabric and the PCIe endpoint? UNCONFIRMED: the RP1 datasheet was
unreachable. Two indirect sources link the CSI2-to-FE rate to clk_sys:

- qbc's `kPixelsPerClock = 2.0` "CSI2→FE throughput per RP1_CLK_SYS tick" (`controller.cpp:62`) (CONFIRMED that it says so).
- will127534's tool README: "The CSI2→FE pixel-rate ceiling is `2 × RP1_CLK_SYS − 20 Mpix/s`" (`README.md:5-7`).

On top of that, a "sys" clock that is critical and always on is the usual fabric clock. (PROBABLE.)

Why a faster RP1 clock should not help recording anyway (PROBABLE):

- **PCIe has headroom.** RP1 sits on `pcie2`: `max-link-speed = <2>`, `num-lanes = <4>` (`bcm2712.dtsi:526-532`;
  `rp1_target: &pcie2`, `bcm2712-rpi-5-b.dts:124-127`). That is 4 x 5 GT/s x 8/10 = 2.0 GB/s raw per direction, roughly
  1.7-1.8 GB/s after TLP overhead (assumed 128-256 B payloads). The CFE needs 16,896,000 B x 30 = **506.9 MB/s** on average
  and 891 MB/s during row bursts (§6), i.e. 25-50 % of the link. (CONFIRMED arithmetic, assumed overhead.)
- **The RP1 fabric has headroom (assumed width).** Even a 64-bit fabric at the stock 200 MHz moves 1.6 GB/s.
  (UNCONFIRMED width.)
- **Contention is on the BCM2712 side.** NVMe is on `pcie1` (`pciex1: &pcie1`, `bcm2712-rpi.dtsi:227-258`), not behind the
  RP1. The back end runs on a BCM2712 firmware clock (`pisp_be` `clocks = <&firmware_clocks 7>`, `bcm2712-ds.dtsi:386-394`),
  not an RP1 clock. The DRAM contention seen in the PMU (brief §3) is on the BCM2712 side, where RP1 writes wait for the
  memory controller like everything else. Raising the RP1 clock cannot speed up acceptance at the root complex.
- **The CFE is not losing writes.** A CFE that could not drain would overflow the CSI2 FIFO and count `Overflows`. None
  were counted where measured (T22). The 30 fps loss is buffer starvation upstream in libcamera (brief §4, CONFIRMED there).
- `pcie_aspm=off` (boot args, brief §1) also keeps the RP1 link out of L0s/L1 exits, and `pcie2` already has `aspm-no-l0s`.
  That is neutral or slightly helpful for CFE write latency. (PROBABLE.)
- The only RP1-side change that could matter is going **below** stock with a mis-built overlay (the 166.7 MHz case above).
  E1 rules it out.

## 6. Does link speed change the CFE's write burst rate and its sensitivity to contention? (brief Q6 e)

In the PiSP pipeline handler the raw stream does not use the CSI2 memory channel. libcamera enables CSI2 pad 4 -> `pisp-fe`
and disables CSI2 -> `rp1-cfe-csi2_ch0` (`libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:2686-2698`@6b0b49f).
The raw buffer is `Cfe::Output0` (FE output 0, `:1494`, `:1735`). So every pixel passes CSI2 -> FE ->
FE output DMA -> PCIe -> DRAM. (CONFIRMED.) The FE writes at min(link pixel rate, FE throughput) x 2 B/px:

| Case | Link pixel rate during a row (4 lanes / 16 bpp) | FE drain (2 x clk_sys - 20) | DRAM write burst | Burst length per row | Idle per row (2H) | Average at 30 fps |
| --- | --- | --- | --- | --- | --- | --- |
| 1782, clk_sys 333 (Pi today, PROBABLE) | 445.5 MPix/s | 646.7 | **891 MB/s** | 8.62 us | 6.19 us | 506.9 MB/s |
| 1782, stock clk_sys | 445.5 | 380 | ~760 MB/s (FE-limited, FIFO absorbs 565 px) | 10.1 us | 4.7 us | 506.9 MB/s |
| 1440, HMAX 550 (needs a driver change) | 360.0 | either | **720 MB/s** | 10.67 us | 4.15 us | 506.9 MB/s |
| 1440, HMAX 660 (driver today, 25 fps max) | 360.0 | either | 720 MB/s | 10.67 us | 7.11 us | 422.4 MB/s at 25 fps |

(CONFIRMED arithmetic, given 2H rows.)

Sensitivity to contention (PROBABLE):

- **Bytes are the same.** The average write load is identical at every link rate, so the extra DRAM pressure the CFE puts
  on the back end and the CPU does not change.
- **Burst structure is too fine to matter.** A higher burst rate means the CFE's write queue fills faster when DRAM stalls.
  An 8 KiB (64 kbit) CSI2 FIFO covers 8192 / 891 = **9.2 us** of total write stall at 1782, versus 8192 / 720 =
  **11.4 us** at 1440 (+24 %). Buffering further down the FE / AXI / PCIe path adds more (size UNCONFIRMED). The 67 kHz
  burst/idle pattern is far finer than the 13-35 ms back-end jobs and CPU passes it competes with.
- **No overflow has been counted.** The CSI2 counters have never shown one. So no stall has yet outlasted the buffering at
  1782, and lowering the burst rate would buy margin against a failure that is not happening.
- **Same frame and buffer timing.** With 2H rows the readout lasts 32.6 ms at either link rate for HMAX 550, and the CFE
  hands buffers back at the same instants. The link rate changes neither how many frames are in flight nor when
  libcamera's per-frame work starts.

## Experiments this suggests

Patrik runs every `sudo`, restart and `/boot/firmware` step; builds run on the Pi. Ranked by value per effort.

**E1. Settle which RP1 clock regime the Pi is actually in.** No change, read-only, about 2 minutes; Core stopped for the
last step.

```
grep -n '^dtoverlay=\(rp1\|imx585\)' /boot/firmware/config.txt
sudo cat /sys/kernel/debug/clk/pll_sys/clk_rate /sys/kernel/debug/clk/clk_sys/clk_rate /sys/kernel/debug/clk/pll_sys_pri_ph/clk_rate
xxd -g4 /sys/firmware/devicetree/base/axi/pcie@1000120000/rp1/clocks@18000/assigned-clock-rates
cat /boot/firmware/overlays/rp1-clk-333mhz.generated.dts | grep -n -i 'sys'
sudo dmesg | grep -E "couldn't set|rp1-cfe|DPHY|link rate|imx585.*(Link speed|Data lanes|Update minimum HMAX|3840x2200|Framing|HBLANK=)"
journalctl -b -u apertar-core | grep -E 'RP1_PLL_SYS|pixel-rate cap|ISP constraints|IMAGE CORRUPTION'
# Core stopped:
LIBCAMERA_LOG_LEVELS=RPiController:1 rpicam-hello --list-cameras 2>&1 | grep -E 'RP1_PLL_SYS|3840x2200'
```

Predictions:

- pll_sys and clk_sys both 333333333; pll_sys_pri_ph 166666666 (as Cinemate measured, `hardware-log.md:305-306`).
- In the `xxd` dump, entries 2 and 7 (the 3rd and 8th words) are `13de4355` (333,333,333).
- dmesg: one `clk: couldn't set clk_sys clk rate to 333333333 (-22), current rate: 333333333`, "Using a link rate of 1782
  Mbps", "DPHY: Datarate 1782 Mbps out of range", `3840x2200 -> VMAX=4500 HMAX=550`, and, if an HBLANK line is present,
  `HBLANK=0 -> HMAX=550`.
- Journal: `PiSP pixel-rate cap = 646.667 Mpix/s` and no "Adjusting mode minimum line length".
- `--list-cameras`: `3840x2200 [30.00 fps`.

What would rule things out:

- clk_sys = 200000000: the overlay is not applied while qbc still caps at 646.67 from the DT. The 16-bit mode is then
  still probably safe (§4.4), but 12-bit SDR 4K60 is at risk.
- clk_sys = 166666666: entry 7 was left at stock and the RP1 runs below stock. Fix the overlay first.
- No "couldn't set" line while clk_sys = 333 MHz: the Pi's 6.12.75 has no 200 MHz `max_freq` on clk_sys. That only
  changes the mechanism in §5.

`vcgencmd` reports BCM2712 / VideoCore clocks, for example `vcgencmd measure_clock isp` for the back end's clock (firmware
clock 7). It does not report RP1 clocks (PROBABLE). debugfs is the only live RP1 reading.

**E2. CSI-2 and FE error state at 30 fps.** No change, read-only, one take.

```
sudo sh -c 'cat /sys/kernel/debug/rp1-cfe*/csi2_errors'        # read once to clear
sudo sh -c 'grep -E "STATUS|DISCARDS|PANICS" /sys/kernel/debug/rp1-cfe*/csi2_regs; grep -E "ERROR_STATUS|OUTPUT_STATUS" /sys/kernel/debug/rp1-cfe*/pisp_regs'
#   ... one 10 s take at 30 fps, uncompressed, L1 build ...
sudo sh -c 'cat /sys/kernel/debug/rp1-cfe*/csi2_errors'        # counts for the take
sudo sh -c 'grep -E "STATUS|DISCARDS|PANICS" /sys/kernel/debug/rp1-cfe*/csi2_regs; grep -E "ERROR_STATUS|OUTPUT_STATUS" /sys/kernel/debug/rp1-cfe*/pisp_regs'
sudo dmesg | grep -c 'Orphanded frame'
```

- Prediction: `Overflows 0` and every discard count 0, while the take still misses 7-30 frames; `Orphanded frame` count
  0; the LLEV/ULEV panic counters about the same as in a 10 s preview-only window. (Whether the panic counters move at all
  in FE-streaming mode is UNCONFIRMED.)
- Rules the CFE-side explanation out: all zeros.
- Rules it in: non-zero OVLF or `Overflows` in takes with gaps means the CFE cannot write fast enough, so the RP1 path and
  the burst rate (§6) matter. Non-zero UNMATCHED or LEN, or an Orphanded WARN, means link corruption. Then try E4.

**E3. Measure the row timing and whether contention delays the CFE's writes.** No change, read-only. Uses the existing
`LIBCAMERA_LOG_LEVELS=RPI:0` window (5 s preview-only, 5 s recording).

- For each `Stream FE Output0 buffer dequeue, buffer id N, timestamp: T` line (`pisp.cpp:2199-2201`@6b0b49f), compute
  (log-line time - T). T is the FS time (`ktime_get_ns`, `cfe.c:692`, `:714`). Both are CLOCK_MONOTONIC (PROBABLE; sanity
  check: 0 < delta < 70 ms). Take the **minimum** and the 10th percentile, not the median: the median includes waiting for
  a busy CameraManager thread. `working/tools/libcam_stages.py` already parses these lines.
- Prediction, preview-only: minimum ≈ **32.6-33.5 ms** (2200 rows x 14.815 us, plus FE drain and IRQ latency).
- Prediction, recording: minimum within **0.5 ms** of the preview value.
- Rules out the 2H-row model of §1.2 / §4.4: a minimum near 16.3-17 ms (one row per H). That would also mean the stock-RP1
  cap is physically needed.
- Rules in "contention slows the CFE path": a recording minimum more than **1 ms** above preview. That would be the
  CFE/PCIe write path backing up under DRAM load, an early warning even without overflow.

**E4 (optional; aims at an in-spec D-PHY, not at the losses). 1440 Mbps with Clear HDR HMAX 550.**

- Change: a driver patch so that Clear HDR uses HMAX 550 at 720 MHz (Clear HDR row of the table), DKMS build on the Pi.
  Patrik sets `dtoverlay=imx585,cam0,link-frequency=720000000` and reboots.
  - Quick look with no build: at 1440 and 25 fps the IPA runs VMAX 4500 (40 ms / 8.889 us). Writing the direct control,
    `v4l2-ctl -d /dev/v4l-subdevN --set-ctrl=hmax=550` (`imx585.c:1732-1738`), raises the rate to
    74.25e6 / (550 x 4500) = 30.0 fps. The IPA's exposure maths is then off by 550/660, so use this for image integrity only.
- Measure:
  - `dmesg | grep -E "link rate|DPHY"`: expect "Using a link rate of 1440 Mbps" and no out-of-range line.
  - Preview fps over 10 s (the KB's frame-counting tools), plus one DNG checked for OB rows and a scene gradient.
  - One 10 s recording at 30 fps.
- Prediction: 30.00 fps preview, intact frames, and recording losses unchanged (27.6-28.8 fps on L1). That would confirm
  the link plays no part, and give a fully in-spec D-PHY at the same frame rate.
- Ruled out if rows are lost or frames corrupt (as with Cinemate's HMAX 440 at 2079). Then HMAX 660 at 1440 is a sensor
  output constraint, and 1782 stays required for 30 fps.

**E5 (low value; only if E2 or E3 implicate the CFE path). Stock RP1 A/B.**

- Change: comment out `rp1-clk-333mhz` and reboot.
- Problem: qbc then caps at 380 and forces 22 fps, so 30 fps cannot be tested without a libcamera patch: an override such as
  an env var in `pispPixelRateMpixPerS()`, built on the Pi.
- Prediction, per §4.4 and §5: preview still 30.00 fps clean; recording losses the same as with 333 MHz; csi2_errors 0.
- Ruled out if the stock RP1 counts overflows or loses more frames. The RP1 path would then matter and the overclock is
  load-bearing.
- Risk: an over-stated cap corrupts 12-bit SDR 4K60 on a stock RP1 (`rp1_regime.py:19-25`). Use the override only in
  16-bit Clear HDR.

## Unknowns

- **Live clk_sys on the Apertar Pi** (333.33 / 200 / 166.67 MHz) and the overlay's actual entry 7. Settled by E1 (debugfs
  and DT). The KB holds only the qbc log line about the DT *request*.
- **Row timing in Clear HDR** (one row per 2H). Needs the Sony IMX585 datasheet (not available) or E3.
- **Which clock the RP1 CSI2, FE output DMA, AXI fabric and PCIe endpoint use, how wide the fabric is, and how much
  buffering follows the 64 kbit FIFO.** Needs the RP1 peripherals PDF and the PiSP specification, section 6 (both on
  datasheets.raspberrypi.com, unreachable from this container). The rp1-cfe binding says "The PHY and CSI-2 receiver part
  have no public documentation" (torvalds/linux `Documentation/devicetree/bindings/media/raspberrypi,rp1-cfe.yaml`, read
  via github.com).
- **What the DW D-PHY's hsfreqrange band controls, and the Apertar board's eye margin at 1782 Mbps.** No protocol-error
  counter exists in rp1_cfe (CSI host IRQ not enabled), so only image checks or a kernel debug patch could measure it.
- **Whether the Pi's 6.12.75 `clk-rp1.c` matches 5bd564a** (`clk_sys` `max_freq` 200 MHz, the "Prevent overclocks"
  check). E1's dmesg line answers it indirectly.
- **CSI-2 and FE counters at 30 fps uncompressed.** Never read; E2.
- **Whether the IMX585 accepts HMAX 550 at the 1440 Mbps data-rate setting in Clear HDR.** E4.
- **Cinemate's 2026-08-27/28 rate matrix** (21.99 @1440, 30.00 @1782, "identical" with or without the overlay) cannot be
  explained by the 380/580 model as recorded. Which cap each cell actually used is not recorded.

## Verification

Verifier: adversarial pass on the text above, 2026-10-26. I re-opened every cited line in the trees named in the header
(imx585-apertar `98b9862`, imx585-v4l2-driver `18c1eb2`, libcamera-qbc `7e9fef0`, libcamera-apertar `6b0b49f` via `git show`,
libcamera (cinemate) `bfe0b76` via `git show`, kernel-rpi `5bd564a`, cinemate `d6cc93e`, cinemate-handbook `c99ff77`,
apertar-core `f60e301` via `git show`), re-cloned will127534/rp1-overclock-tool read-only (HEAD `eace52d`, same as the reader),
and re-did every arithmetic step. datasheets.raspberrypi.com and cnx-software.com did not resolve from this container either,
so the RP1 and PiSP PDFs remain unread. Verdicts: CONFIRMED (holds; for a claim the reader labelled PROBABLE, "as PROBABLE"
means the reasoning holds and the label is honest), CORRECTED, REFUTED, UNVERIFIABLE (needs the Pi or an unreachable source).

| # | claim | verdict | evidence |
| --- | --- | --- | --- |
| 1 | IPA files identical between qbc and apertar | CONFIRMED | `git diff --stat 7e9fef0 6b0b49f` touches only `pipeline/rpi/pisp/{pisp.cpp,raw_stats.cpp,raw_stats.h}` |
| 2 | 2 or 4 lanes from DT, overlay `<1 2 3 4>`, HMAX x2 for 2 lanes; link list 297-1188 MHz; overlay default 720 MHz | CONFIRMED | imx585-apertar/imx585.c:243-275, 1506-1507, 2502-2507@98b9862; imx585-overlay.dts:11, 77-78@98b9862 |
| 3 | `HMAX_table_4lane_4K` 1584...396; INCK 74.25 MHz; VMAX 20-bit, HMAX 16-bit | CONFIRMED | imx585.c:278-287 (reader: 277-286), :211, :109-115@98b9862 |
| 4 | 16-bit mode 3840x2200, min_hmax 550, base_vmax 2250; `hdr_scale` on VMAX only; no Clear HDR floor | CONFIRMED | imx585.c:1194-1215, :111, :1503-1524@98b9862; `grep HMAX_MIN` no hit |
| 5 | Pixel rate = width x 74.25e6 / min_hmax; HBLANK 0..max; HMAX = min_hmax x (w+hblank)/w | CONFIRMED | imx585.c:1538-1548, 1678-1689@98b9862 |
| 6 | README: 50/60 fps at 1440/1782, "ClearHDR ... half", "~43.8 FPS @ 4K" | CONFIRMED | imx585-apertar/README.md:110-121@98b9862 |
| 7 | Timing table: 550/74.25e6 = 7.407 us, 660/74.25e6 = 8.889 us; x4500 = 33.33/40.00 ms = 30.00/25.00 fps; 3840x74.25e6/550 = 518.4, /660 = 432.0 MPix/s; 2200 x 14.815 us = 32.59 ms, 2200 x 17.778 us = 39.11 ms; blanking 0.74/0.89 ms | CONFIRMED | arithmetic re-done |
| 8 | Wire time: 7686 B/4 = 1921.5 B = 15,372 bit; /1782e6 = 8.63 us (58 % of 14.815); /1440e6 = 10.68 us (60 % of 17.778; 72 % of 14.815); 12-bit 11,532 bit: 6.47 us (87 %), 8.01 us (90 %) | CONFIRMED | arithmetic re-done |
| 9 | HMAX x link MHz roughly constant (490k, 475k, 490k) | CONFIRMED | 1584x297 = 470k, 1320x360 = 475k, 792x594 = 470k, 440x1039.5 = 457k: full spread 457-490k |
| 10 | Clear HDR sends one row per 2H | UNVERIFIABLE | needs the Sony datasheet or E3; PROBABLE label honest; supported by commit c0f5404 ("dual HG+LG read", imx585-v4l2-driver) |
| 11 | Average 33.33 ms / 2200 = 15.15 us, 253 MPix/s | CONFIRMED | 3840 x 2200 x 30 = 253.4e6 |
| 12 | Cinemate driver: same 660/550 entries, 16-bit entry "unchanged", VMAX x2, Clear HDR floor 550 x lane_scale | CONFIRMED | imx585-v4l2-driver/imx585.c:120-121, 287-303, 1719-1727, 3274, 3301, 3305-3314@18c1eb2 |
| 13 | "at 2079 Mbps the table's HMAX 440 'loses roughly 94% of its rows'" | CORRECTED | README.md:233-238@18c1eb2 says the *old* table's 440; the current table entry at 2079 is 472 (imx585.c:297-302) and the code comment (:3307-3311) and commit c0f5404 put the ~94 % loss at 472. Substance (Clear HDR fails below ~550) unchanged |
| 14 | Apertar driver at 1039.5 MHz would "advertise 74.25e6/(440x4500) = 37.5 fps" | CORRECTED | driver arithmetic right, but driver rate 3840x74.25e6/440 = 648.0 MPix/s > qbc cap 646.67, so the IPA pads: 3840/646.67e6 = 5.938 us x 4500 = 26.72 ms, i.e. ~37.42 fps advertised. Trap warning stands |
| 15 | HMAX 550 is the sensor's own Clear HDR limit | CONFIRMED (as PROBABLE) | strengthened: c0f5404 (Will Whang) calls RAW12 at 2079/HMAX 472 "verified-clean" while Clear HDR at 472 loses ~94 % of rows on the same link, so the failure is not the D-PHY |
| 16 | 1440 Mbps cannot do 30 fps in either driver | CONFIRMED | 660 in both tables; Cinemate floor max(660, 550) = 660; 74.25e6/(660x4500) = 25.00 |
| 17 | `dphy_rate` set once, used once for hsfreqrange | CONFIRMED | kernel-rpi rp1_cfe/cfe.c:1175, dphy.c:142@5bd564a; grep shows no other reader |
| 18 | 25 fps keeps HMAX 550, VMAX 5400; blanking 0.74 -> 7.41 ms | CONFIRMED | 74.25e6/25 = 2,970,000 = 5400 x 550, so `bestErr` = 0 and the search loop never runs (libcamera-qbc/src/ipa/rpi/cam_helper/cam_helper_imx585.cpp:169-185@7e9fef0); KB working/clearhdr-design.md:120; (5400 - 4400) x 7.407 us = 7.41 ms |
| 19 | Link errors cannot explain loss at 30 but not 25 or preview | CONFIRMED (as PROBABLE) | brief §3 (preview 30.00 fps, 0 gaps; 25 fps 0 missing); see Missed 1 |
| 20 | Gap pattern is a steady deficit, not random errors | CONFIRMED (as PROBABLE) | lessons/hardware-log.md 2026-10-26 "steady single-frame skip" entry |
| 21 | Link rate = LINK_FREQ x 2, "Using a link rate of %lld Mbps" at info level | CONFIRMED | cfe.c:62, 1093-1101@5bd564a; imx585.c:1958-1962@98b9862 |
| 22 | Out of range: `dev_err`, no return, last bin {1500, 0b111100} via test code 0x44, streaming continues | CONFIRMED | dphy.c:16-17, 33, 99-129, 131-157@5bd564a |
| 23 | What the band controls; eye margin on the Apertar board | UNVERIFIABLE | DW D-PHY databook not public; needs the Pi |
| 24 | Cinemate 1782 clean: 16/16 short takes; colour rig all seven modes | CONFIRMED | cinemate-handbook/lessons/hardware-log.md:958-959@c99ff77; imx585-v4l2-driver/README.md:250-255@18c1eb2 |
| 25 | Apertar DNG median 3643 vs 3625 as link-integrity evidence | CORRECTED | the L2 log entry records it as a byte-order check; a median cannot reveal sparse payload damage. Weak evidence only |
| 26 | `track_csi2_errors`: five IRQs unmasked at stream start; ISR counts Overflows and per-VC discards; `csi2_errors` clears on read | CONFIRMED | csi2.c:18-21, 49-59, 183-194, 219-259, 447-451@5bd564a; file exists only with the parameter, :581-583 |
| 27 | No ECC/CRC/SoT counters: CSI host IRQ never enabled, only CSI_DMA and PISP_FE | CONFIRMED | cfe.c:74-76, 1155@5bd564a; `MIPICFG_INT_CSI_HOST` has no other use in rp1_cfe |
| 28 | "Payload CRC errors therefore pass through silently as pixel damage" (under "CONFIRMED from code") | CORRECTED | the code only shows they are not counted; what the undocumented DW host does with a bad packet is PROBABLE at best |
| 29 | FE_ERROR_STATUS only in verbose debug; "has no buffer" only `cfe_dbg_verbose` | CONFIRMED | pisp_fe.c:202-209; cfe.c:56-60, 623-626@5bd564a |
| 30 | Starvation drops do not increment the counters | CONFIRMED (as PROBABLE) | hardware-log T22 table: dd tmpfs 11 intervals > 60 ms, counters all 0 |
| 31 | `csi_dt = 0` for 16-bit, so every DT is accepted; UNMATCHED weakened | CONFIRMED | cfe_fmts.h:200-226, cfe.c:854-858@5bd564a; imx585 has no `get_frame_desc`, so the `csi_dt` fallback is what gets programmed (csi2.c:345-346, 366-370, 429-431). OB-row DT is the driver author's "likely" (imx585.c:547-551@98b9862) |
| 32 | "A lost frame-end short packet leaves `cur_frm` set at the next FS. That triggers WARN ... Orphanded frame" | REFUTED | cfe.c:793-807@5bd564a: when FS arrives with FS_INT set and FE_INT clear, the ISR first calls `cfe_eof_isr_handler()` (:723-736), which returns `cur_frm` as `VB2_BUF_STATE_DONE` and sets it NULL; only then does the FS handler run, so the WARN at :684 does not fire. The only trace is the `cfe_dbg` at :804. A frame merged by a lost FE is delivered as good |
| 33 | "Handling missing previous FE interrupt" is debug only | CONFIRMED | cfe.c:61, 804@5bd564a |
| 34 | No counter reading at 30 fps uncompressed | CONFIRMED | brief §3 cites T22 only; the 30 fps hardware-log entries carry no counter reading |
| 35 | PiSP entry `1.0us / pispPixelRateMpixPerS()`; comment "400Mpix/s ... 380", "64kbit data FIFO"; upstream 27159861 (Naushir Patuck, 2024-01-04) | CONFIRMED | libcamera-qbc/src/ipa/rpi/controller/controller.cpp:191-215@7e9fef0; `git log -1 27159861` in libcamera (cinemate) |
| 36 | DT entries 2 and 0, snap to core/N, 2 x clk - 20; fallbacks (Debug if missing, Warning outside 0.5-4x); Info "PiSP pixel-rate cap"; clk_sys assumed = pll_sys | CONFIRMED | controller.cpp:52-54, 59-68, 103-147@7e9fef0 |
| 37 | `IpaBase::setMode` pads minLineLength; minLineLength = width + hblank.min | CONFIRMED | ipa_base.cpp:612-651@7e9fef0; camera_sensor_raw.cpp:1043-1044, camera_sensor_legacy.cpp:926-927@7e9fef0 |
| 38 | No env override in qbc; Cinemate env `LIBCAMERA_RPI_MAX_PIXEL_RATE`, default 380 | CONFIRMED | grep `MAX_PIXEL_RATE` in qbc src: 0 hits; libcamera(cinemate)/src/ipa/rpi/controller/controller.cpp:82, 114-141@bfe0b76 |
| 39 | Cap table: 1/380e6 = 2.632 ns, x3840 = 10.105 us, x4500 = 45.47 ms = 21.99 fps; 580 -> 6.621 us, 646.67 -> 5.938 us, both < 7.407 us; HBLANK = 10.105 x 518.4 - 3840 = 1398.6; HMAX = 550 x 5239/3840 = 750.4 -> 750; 74.25e6/(750x4500) = 22.0; 30 x 4500 x 3840 = 518.4e6 | CONFIRMED | arithmetic re-done |
| 40 | rp1_regime.py: "scales with the RP1 clock", 380/580 "Measured on a CM5", overlay line + mtime guard, clk_sys log-only, direction of error | CONFIRMED | cinemate/src/module/rp1_regime.py:3, 19-25, 27-38, 70-72, 80, 154-200@d6cc93e |
| 41 | sensors.md row `21.99 / 30.00 / 16.9` at 1039.5 MHz, 380/580 | CONFIRMED | cinemate/docs/sensors.md:38, 40-42; docs/changelog.md:45-49@d6cc93e |
| 42 | Those figures are advertised ceilings, not recording results | CONFIRMED (as PROBABLE) | same arithmetic as #39; handbook :392-393 "only the *advertised* ceiling has been observed" |
| 43 | 12-bit SDR: 3840x74.25e6/472 = 604 MPix/s; 2250 x 10.105 us = 22.74 ms = 43.98 fps; 2250 x 6.621 us = 14.90 ms = 67.13 fps | CONFIRMED | arithmetic re-done; sensors.md:36 |
| 44 | Overlay "installed but off", reboot both ways; installer sets entries 2 and 7 to 300 MHz; "over RP1 spec" | CONFIRMED | docs/overclocking.md:13-16; cinemate-install.sh:734-791; docs/config-txt.md:23@d6cc93e |
| 45 | Handbook 2026-08-26: pll_sys/clk_sys 333333333, pri_ph 166666666, no rp1 node; 66.85 -> 43.80 | CONFIRMED | cinemate-handbook/lessons/hardware-log.md:286-307, 353-361, 374@c99ff77 |
| 46 | Matrix: "The overclock buys no frame rate ... (21.99 @1440, 30.00 @1782)"; default "1440 Mbps / stock clock" | CONFIRMED | hardware-log.md:969-971, 985-986@c99ff77 |
| 47 | Matrix does not fit the 380/580 model; cannot isolate a clock effect | CONFIRMED (as PROBABLE) | 1440 at 580: 8.889 us > 6.621 us, 25.00 fps; 1782 at 380: 21.99. Note: the cited misclassification (:855-857) would give 580 everywhere, i.e. 25.00 @1440, so it does not explain the 21.99 cell either; :3155 records another unexplained 30 fps `--list-cameras` at a 380 regime |
| 48 | 2026-09-15: config.txt rewrite after boot -> 380 -> "21 fps" | CONFIRMED | hardware-log.md:3135-3168@c99ff77 |
| 49 | Pi runs `dtoverlay=rp1-clk-333mhz` (config.txt line 65); qbc logged 646.667 | CONFIRMED | KB sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:38; working/clearhdr-design.md:88; working/handoff-clearhdr-buffering.md:29 |
| 50 | The limit is unconditional for PiSP; a 30.00 fps preview implies cap >= 518.4 | CONFIRMED | controller.cpp:215, ipa_base.cpp:620-639@7e9fef0; at 380 the minimum frame is 45.47 ms |
| 51 | rp1-overclock-tool: formula, 333.33 MHz grid point, regenerates every slot changing only PLL_SYS/CLK_SYS, tested on 6.12.75, two verification commands | CONFIRMED | rp1-overclock-tool/README.md:5-15, 24-38, 62, 68-71, 120-122, 159-165@eace52d; default 333333333 at generate_dtbo.py:233, install.sh:33, 38 |
| 52 | §4.4: 3840/14.815 us = 259.2 MPix/s; 4 x 1782e6/16 = 445.5 MPix/s for 8.62 us; backlog 3840 - 380 x 8.62 = 565 px = 9.0 kbit; drain 10.1 us; at 2079: 7.39 us, 1032 px = 16.5 kbit | CONFIRMED | arithmetic re-done; the FIFO itself is documented only in controller.cpp:205-213 |
| 53 | clk_sys parents xosc/pll_sys, `max_freq` 200 MHz, CLK_IS_CRITICAL; stock DT entries 2 and 7 at 200 MHz; CFE lists only MIPI0_CFG 25 MHz (max 50 MHz); i2c/spi on CLK_SYS | CONFIRMED | drivers/clk/clk-rp1.c:1846-1860, 2052-2063; arch/arm64/boot/dts/broadcom/rp1.dtsi:30-59, 168-377, 1018-1035@5bd564a |
| 54 | clk_sys above 200 MHz refused with -EINVAL; clk-conf logs "couldn't set" and carries on | CONFIRMED | re-traced: xosc gives div 0 for a 333 MHz request (clk-rp1.c:1079-1080), pll_sys gives 333.33 > max (:1333-1334), so best_rate 0 -> -EINVAL (:1390-1391); clk-conf.c:147-151@5bd564a |
| 55 | Overlay reaches 333 MHz because clk_sys follows pll_sys with div 1; dmesg will show "couldn't set clk_sys ... (-22), current rate: 333333333" | UNVERIFIABLE | needs the Pi's dmesg; consistent with Cinemate's 300 MHz request reading 333333333 for both clocks (hardware-log.md:305-306@c99ff77) |
| 56 | Overlay leaving entry 7 at 200 MHz gives clk_sys 166.7 MHz while qbc still reports 646.67 | CONFIRMED | clk_sys has no fractional divider, so div = nearest(333.33/200) = 2 (clk-rp1.c:1086-1092), 166.67 <= 200; qbc reads entries 0 and 2 only (controller.cpp:115-117) |
| 57 | Which clock drives RP1 CSI2/FE output DMA/AXI/PCIe endpoint | UNVERIFIABLE | RP1 datasheet unreachable; indirect sources (controller.cpp:62; tool README.md:5-7) CONFIRMED to say what the reader quotes |
| 58 | RP1 on pcie2 Gen2 x4: 4 x 5 GT/s x 8/10 = 2.0 GB/s; 16,896,000 B x 30 = 506.9 MB/s; burst 445.5 x 2 = 891 MB/s; 25-50 % | CONFIRMED | bcm2712.dtsi:526-532; bcm2712-rpi-5-b.dts:124-127@5bd564a; arithmetic re-done (effective RP1 PCIe write throughput UNVERIFIABLE) |
| 59 | RP1 fabric 64-bit at 200 MHz = 1.6 GB/s | UNVERIFIABLE | arithmetic right (8 B x 200e6); width unknown |
| 60 | NVMe on pcie1; BE on firmware clock 7; pcie2 `aspm-no-l0s` | CONFIRMED | bcm2712-rpi.dtsi:258 (`pciex1: &pcie1`); bcm2712-ds.dtsi:386-394; bcm2712-rpi-5-b.dts:125@5bd564a |
| 61 | The CFE is not losing writes (no overflow counted) | CONFIRMED (as PROBABLE) | only evidence is T22 at 25 fps; report itself flags this |
| 62 | Raw path CSI2 pad -> pisp-fe, CSI2 ch0 disabled, raw = Cfe::Output0 | CONFIRMED | libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:2686-2698, 1493-1494, 1735-1737@6b0b49f |
| 63 | §6 table: 445.5/646.7 -> 891 MB/s, 8.62 us, idle 6.19 us; stock 760 MB/s, 10.1 us, 4.7 us; 1440: 360 MPix/s, 720 MB/s, 10.67 us, idle 4.15 / 7.11 us; 422.4 MB/s at 25 fps; FIFO 8192/891 = 9.2 us vs 8192/720 = 11.4 us (+24 %); 1/14.815 us = 67.5 kHz | CONFIRMED | arithmetic re-done |
| 64 | E1: entries 2 and 7 read `13de4355` | CONFIRMED | 0x13DE4355 = 333,333,333; DT cells are big-endian so `xxd -g4` prints them in that order |
| 65 | E1-E5 predictions (dmesg lines, clk rates, deltas, fps) | UNVERIFIABLE | need the Pi |
| 66 | E2: grep for the STATUS, DISCARDS and PANICS lines of `csi2_regs` before/after a take | CORRECTED | with `track_csi2_errors=1` the ISR writes 0 to each DISCARDS register it reports (csi2.c:246-247) and writes CSI2_STATUS back to clear it (:270), so those lines read 0 regardless; only `csi2_errors` and the LLEV/ULEV PANICS lines carry information |
| 67 | E3: parse "Stream FE Output0 buffer dequeue, buffer id N, timestamp: T"; `libcam_stages.py` "already parses these lines" | CORRECTED | the stream is named "CFE Image" (pisp.cpp:1378@6b0b49f), so the line is "Stream CFE Image buffer dequeue, buffer id N, timestamp: T" (:2199-2201); `working/tools/libcam_stages.py:13` matches that line but captures only the id, not T, so E3 needs a one-line regex change |
| 68 | E3: T is the FS time from `ktime_get_ns`, CLOCK_MONOTONIC | CONFIRMED | cfe.c:692, 700-701, 714@5bd564a; for the FE Output0 node the SOF comes from the FE ISR (pisp_fe.c:211-215) |
| 69 | E4: direct `HMAX` control; 40 ms / 8.889 us = 4500; 74.25e6/(550x4500) = 30.0 | CONFIRMED | imx585.c:42, 1732-1738, 1914-1922@98b9862; arithmetic re-done |
| 70 | `vcgencmd measure_clock isp` reads the BE clock | CONFIRMED (as PROBABLE) | pisp_be `clocks = <&firmware_clocks 7>` (bcm2712-ds.dtsi:390); firmware clock 7 = ISP is standard but not shown in this tree |
| 71 | rp1-cfe binding: "The PHY and CSI-2 receiver part have no public documentation" | CONFIRMED | https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/media/raspberrypi,rp1-cfe.yaml |
| 72 | kernel `5bd564a` is "close" to the Pi's 6.12.75; whether clk-rp1.c matches is unknown | CORRECTED | 5bd564a is 6.12.114 (`git show 5bd564a:Makefile`, SUBLEVEL 114), not close. But all six clk-rp1.c commits on rpi-6.12.y date from 2025-03-25 (https://github.com/raspberrypi/linux/commits/rpi-6.12.y/drivers/clk/clk-rp1.c), so the Pi's 6.12.75 very probably has the same `max_freq` / "Prevent overclocks" code (PROBABLE). That settles one of the report's unknowns |

**Counts:** 72 claims checked. 58 CONFIRMED (8 of them "as PROBABLE": #15, #19, #20, #30, #42, #47, #61, #70), 7 CORRECTED (#13, #14, #25, #28, #66, #67, #72),
1 REFUTED (#32), 6 UNVERIFIABLE (#10, #23, #55, #57, #59, #65).

### Corrections that change substance

1. **#32: the "Orphanded frame" WARN does not detect a lost frame-end packet.** The ISR handles a missing FE before the next
   FS (cfe.c:793-807@5bd564a). It completes the buffer as DONE, so the only trace is a debug line, and the Pi kernel has no
   dynamic debug (hardware-log T22 entry). A lost FS packet also leaves no trace. So E2's "Orphanded WARN means link
   corruption" test cannot fire, and E2's "all zeros rules the CFE side out" holds only for FIFO overflow, not for
   short-packet loss. The report's main conclusion (the link is not the cause) still stands, because it rests on the
   25 fps and preview-at-30 fps controls, not on E2.
2. **#67: E3 as written finds no lines.** The real log line is "Stream CFE Image buffer dequeue ... timestamp: T", and
   `libcam_stages.py` does not capture T. Fix the regex before using E3's prediction (minimum delta 32.6-33.5 ms, or
   16.3-17 ms for one row per H).
3. **#66: E2's `csi2_regs` grep carries no information** for DISCARDS/STATUS while `track_csi2_errors=1`. Use
   `csi2_errors`, the PANICS lines and the raw interrupt status (Missed 3).
4. **#72: the Pi's clk-rp1.c very probably matches.** E1's "no 'couldn't set' line" branch (no 200 MHz cap on 6.12.75) is
   therefore unlikely. A 333 MHz reading without that dmesg line would point at something other than the mechanism in §5.
   (#13, #14, #25 and #28 are wording and precision fixes and do not change conclusions.)

### Missed

1. **The L1 result also rules the link out.** A software-only change (stats on every 4th row pair) cut the loss from 30-46
   to 7/8/20 frames on the same 1782 link (hardware-log L1 entry). Preview-only at 30.00 fps with 0 gaps, on the identical
   link and frame timing, rules it out too. Each is enough on its own, so short answer 1 is nearer CONFIRMED than
   "PROBABLE, strong".
2. **E1, E4 and E5 cannot recover the missing ~2 fps, by the report's own arithmetic.** Take the worst RP1 case, clk_sys
   166.7 MHz. The drain is 2 x 166.7 - 20 = 313 MPix/s. The backlog is 3840 - 313 x 8.62 = 1142 px = 18.3 kbit, under
   64 kbit, and a row drains in 12.3 us, inside 14.8 us. So even that case carries 16-bit Clear HDR at 2H rows. E1 is
   ranked first for its cost, not for its value to the goal. Only E2 and E3 touch the 30 fps loss. E3 may need no new
   capture if the 20:50 `RPI:0` journal (before L1) is still on the Pi.
3. **There is a read-only CSI-2 host signal after all.** The existing debugfs file `rp1-cfe:*/regs` dumps `MIPICFG_INTR`, the
   raw unmasked status, whose bit 2 is `CSI_HOST` (cfe.c:75, 395-409, 2341@5bd564a). Nothing ever clears that bit. If it
   is set after a take, the DW CSI-2 host flagged something. Whether the host's own error masks route ECC/CRC errors to
   that line is UNCONFIRMED. Add `sudo cat /sys/kernel/debug/rp1-cfe*/regs` to E2. The report says only image checks or a
   kernel patch could measure protocol errors.
4. **Commit c0f5404 separates the sensor limit from D-PHY margin.** RAW12 runs clean at 2079/HMAX 472, while Clear HDR
   fails at 472 on the same link. That supports §1.3, and it makes E4 (1440 Mbps with HMAX 550) more plausible from the
   link side. The floor is "~HMAX 550", an approximate figure.
5. **Cinemate saw clk_sys at ~333 MHz with the overlay commented out** on 6.12.93 (rp1_regime.py:27-38@d6cc93e;
   handbook :855-857@c99ff77). In E1, a 333333333 reading alone therefore does not prove the overlay is in effect. Read
   it together with DT entry 7 and the "couldn't set" dmesg line.
