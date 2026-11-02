# Co-factors the 2026-11-01 session did not weigh, and the A0 puzzle

Inspection report, written 2026-11-02 from the desk (no Pi). Part of the independent check of the page-cache claim; the
other half (verdict, A/B design, kernel mechanism) is `night-2026-11-01.md` section 8. This file covers the six task items:
A0 against 2026-11-01, the 1782 Mbps CSI-2 link, CPU0's interrupts, the WebUI and touch-UI preview feeds, the drive, and
a ranking with one test each. Everything read: Core `drop-frames` @ `adac040` (`git -C /home/user/Apertar-Core`), UI
`drop-frames` @ `c13b846` (`/home/user/tiramisioux/apertar-ui`), kernel `rpi-6.12.y` @ `5bd564a`
(`/home/user/tiramisioux/kernel-rpi`; `mm/`, `drivers/media/platform/raspberrypi/rp1_cfe/`, `drivers/pci/controller/`,
`drivers/mfd/rp1.c`, `kernel/irq/`, `drivers/dma-buf/heaps/` fetched for this report), the imx585 driver `cinemate-port`
@ `cd548ef` (`/home/user/tiramisioux/imx585-v4l2-driver`, cloned for this report), cinemate `storage-automount.py`,
cinepi-raw `dng_encoder.cpp`, the handbook entry of 2026-08-27, and the KB (hardware log, night report, takes, scripts).

Status words: **confirmed** (read in source, or measured on the Pi and recorded), **measured** (numbers real, reading not
agreed), **probable** (inferred; the reason is given), **unconfirmed** (the measurement that settles it is named),
**refuted**.

## 0. What a decision-maker needs (summary)

1. **The night report's answer to "why was A0 clean" (item 7: early in the boot, empty cache) is refuted by its own
   record.** The hardware log says the touch UI had been running since 01:04:19 and A0 ran at 08:30 (`hardware-log.md:925-926`),
   so A0 came at least 7.4 hours into its boot, after the overnight drive test had pushed terabytes through the page cache.
   What A0 and the clean #69 share is not boot age but **being the first take of a freshly started Core process**
   (`hardware-log.md:739-740`: the matrix restarted Core before A0). Section 8's row "first take of a boot" needs the same
   correction. A1 and A2 were also first takes of a restarted Core (`hardware-log.md:759-761`: environment read back from
   the unit per arm), so "first take" alone does not protect either (A2 lost 10 %).
2. **Every 2026-11-01 take, writer and sync alike, ran the RAM write buffer** (`queue_budget=1.40-1.70 GB` on every
   `recording stats` line, `takes-2026-11-01.raw.txt`), a mode that did not exist at A0 (`d44b177`). It is not the
   writer/sync discriminator, but it is a difference from A0 that nobody has switched off. From those budgets,
   `MemAvailable` at take start was 3.2-3.5 GB in **every** take, writer or sync (probable, formula in 1.4): the arms
   differed in `MemFree` (what is free without reclaim), not in what the kernel counted as available.
3. **Between A0 and 2026-11-01 four things changed under the same `writer` mode**: Core (`a40112a` -> `64bbbaa`: warm raw
   pool kept through the take, one 16.9 MB `write()`, RAM buffer, pre-roll, trim, web-preview cap, RT knob), the UI
   (`ea44bd7` -> `c13b846`, 14 commits), the **imx585 driver** (`24172e6` -> `cd548ef` on 2026-11-01, 3,637 lines
   changed, new mode tables; `hardware-log.md:899-906`), and the drive state (A0 trimmed and cooled to 34 C; 11-01 trimmed,
   not cooled, four back-to-back takes). The 10-31 short takes lost frames on the **old** driver (with the WebUI open), so
   the driver is not necessary for losses, but no Clear HDR 16-bit 25 fps take has ever been run with today's Core and the
   old driver, or today's driver and the old Core. **One test splits "clean then, losing now" from "within-boot drift":**
   today's full stack in `writer` mode as the first 10-minute take after a reboot, with A0's protocol (1.5, test T1).
4. **The CSI-2 link at 1782 Mbps cannot cause a memory- or UI-correlated single-frame loss by itself**: the receiver
   programs the 1500 Mbps calibration bin and keeps streaming (`dphy.c:99-128`); link errors show as `csi2_errors`
   discards (LEN/UNMATCHED) and are independent of what the CPUs do. A receiver **FIFO overflow** (OVLF) is the one
   link-side counter that *would* correlate with memory-bus load. The counter exists (`csi2.c:175-258`), needs
   `rp1_cfe.track_csi2_errors=1` at boot, resets on read, and has never been read during a losing take (last read 2026-10-26,
   all zero under `dd` loads). A control test at 1440 Mbps (720 MHz, in spec) is possible: the driver's table gives 4K
   Clear HDR 16-bit exactly 25.0 fps there (zero margin), nothing lower reaches 25.
5. **The rp1-cfe interrupt (154) cannot be moved off CPU0 from user space, and the write may not be safe**: RP1 interrupts
   are MSI-X children whose affinity call is forwarded to the PCIe MSI domain (`rp1.c:144-157`), which is declared
   `MSI_FLAG_NO_AFFINITY` with no `irq_set_affinity` on its bottom chip (`pcie-brcmstb.c:664-674, 720-724`); the forwarding
   call dereferences that missing handler (`kernel/irq/msi.c:663-670`). Do **not** write `/proc/irq/154/smp_affinity`. The
   same applies to the USB and I2C lines and, probably, to the NVMe completion queues (never counted in the record). What
   can move: the v3d GIC lines (done, no gain), libcamera's thread (`taskset`), and the NeoRotary poll (unplug or disable).
6. **The WebUI preview is a genuine completion-thread cost** (the 1280x720 -> 640x360 downsample runs on libcamera's thread,
   `ApertarCoreApp.cpp:9730-9820`; the JPEG encode is on its own thread, `:9833-9880`); the touch UI's feed is not: after a
   one-time dma-buf registration per slot, a frame costs the completion thread a 200-byte descriptor hand-off
   (`CameraController.cpp:10024-10072`, `ApertarCoreApp.cpp:8175-8221`), and a dedicated publisher thread sends a ~120-byte
   JSON line non-blocking to each socket client (`:14488-14540`, `ControlServer.cpp:19-36`), dropping a stalled client
   rather than waiting. The scripts' "no client on :8000" rule is right as a confound control.
7. **Drive fill is a weak candidate for #78's tail**: fill losses on this rig have always shown as `queue-full` (2026-10-26,
   77-81 % full: 166-676 queue-full drops), and #78's 18 last-minute losses were capture gaps with `peak_queue=2/12`. Core
   trims at mount, after a delete that frees >= 1 GiB, after a free-space jump and after every pre-roll, never during a take
   (`ApertarCoreApp.cpp:11386-11433, 10856-10861`); the drive was trimmed at 23:13 after #78, so #78 ran 0 -> 97 % full on a
   trim-fresh drive. The one fill mechanism that reaches capture is more allocation per file (exFAT bitmap/FAT reads under
   a tight memory regime), which B3(d)/(e) of section 8 already separates.
8. **Two corrections to section 8**: (a) M6's `rp1_cfe` dynamic-debug line "has no buffer, unable to schedule job" cannot be
   read on this kernel: `dev_dbg` compiles out without `CONFIG_DYNAMIC_DEBUG`, which `bcm2712_defconfig` does not set
   (`cfe.c:56-61`; the 2026-10-26 entry says the same from the Pi); only `csi2_errors` is available without a kernel rebuild.
   (b) "`/proc/irq/154/smp_affinity`" as a cheap test is not available (point 5). Also: the `vm.min_free_kbytes` 64 MiB of
   take #80 is **not** CineMate's: `storage-automount.py:319-335` sets only `dirty_*`; Core's helper sets only `dirty_*` too
   (`scripts/apertar-media-tune:80-104`). It is Apertar's own knob and the one most likely to matter (section 8, B3).

## 1. A0 (2026-10-30) against 2026-11-01

### 1.1 What A0 was (record)

| Item | A0, 2026-10-30 08:30 | 2026-11-01 #70-#72 (writer) | Source |
| --- | --- | --- | --- |
| Core | `a40112a` (built 01:05) | `64bbbaa` (built 22:46 is `64bbbaa`; `adac040` not built) | `hardware-log.md:738`, night report section 4 |
| `APERTAR_DNG_DONTNEED` | no knob; DONTNEED hard-coded after each write (= `writer`) | `writer` (knob default at `64bbbaa`) | `0ed07ea` message; `CdngEncoder.cpp:1886-1887` |
| Write queue | 12 frames (`APERTAR_CDNG_QUEUE_FRAMES=12`) | **RAM mode**, budget 1.40-1.70 GB (`queue_budget=` on every stats line), `peak_queue=2/12` | `hardware-log.md:740`; `takes-2026-11-01.raw.txt` lines 335-388 |
| Raw camera buffers | 8 | 8 (12 in #41 only; the `zzz-ab-buffers.conf` drop-in must be checked gone) | `hardware-log.md:740`; night report section 5 |
| Sync / writeback | `SYNC_MS=1000`, `WRITEBACK=1` | same | `hardware-log.md:739-740`; `CameraController.cpp:4319-4323, 4662-4666` |
| imx585 driver | `24172e6` (probable: the 11-01 entry records `24172e6` -> `cd548ef`) | `cd548ef` (cinemate-port tables, installed 11-01 before 19:09) | `hardware-log.md:899-906` |
| UI | `ea44bd7` era (the 11-01 entry counts "8 commits since `ea44bd7`") | `c13b846` (14 commits after `ea44bd7`) | `hardware-log.md:926`; `git log ea44bd7..c13b846` |
| Touch UI | running (Patrik confirmed) | running, aids on | `hardware-log.md:925-929` |
| WebUI | closed | closed (checked by the script) | `hardware-log.md:789-790`; `take3.sh` |
| Drive | `fstrim` 917.1 GiB, cooled to 34 C, 0 % full | formatted + trimmed 21:50 (Core trims at mount), not cooled, 4 takes 4 min apart, 0 -> 32 % full | `hardware-log.md:739`; night report sections 2, 5 |
| Pre-roll before the take | none (no pre-roll in `a40112a`) | yes at every Core start (0.7 GB written, deleted, trim requested) | `d44b177`; `04bac89`; takes #68, #73 |
| Boot age | >= 7.4 h (UI process up since 01:04:19; the crash/reboot stamp 01:43-01:45 is marked "Pi clock" and the 10-31 RTC entry says boot clocks were wrong until NTP, so the two stamps cannot both be right on one boot; either way A0 was hours into it) | 5-13 min | `hardware-log.md:925-926, 716-719, 797-811` |
| Take's place in the Core process | first take after a restart (the matrix restarted Core with the defaults) | 2nd-4th take of the 22:27 process (#69 was the first: 1 lost) | `hardware-log.md:739-740`; takes #69-#72 |
| Memory before the take | not recorded (only Dirty 11 MB / Writeback 8 MB peaks) | `MemFree` 275-327 MB; `MemAvailable` ~3.3 GB (derived, 1.4) | `hardware-log.md:745`; night report section 2 |
| Result | 0 of 15,001 in 10 min | 34, 153, 71 of ~4,500 in 3 min | |

### 1.2 The "early in the boot, empty cache" guess (night report item 7): refuted

- At 415 MB/s the ~2.6 GB the page cache can take on this board fills in about 6 s; the first kswapd wake comes when free
  memory crosses the low watermark, about 20 MB on this configuration (1.4), so a take starting at `MemFree` 2.7 GB meets
  reclaim after ~6.5 s and one starting at 300 MB after ~0.7 s. Neither can carry 3-10 minutes. (confirmed arithmetic)
- A0 was not early in its boot (1.1). The record contradicts the guess on the one fact it rests on. (refuted)
- Section 8.1's last row ("A0, A1, A2 ran in that order on one boot: ... the same within-boot drift") stands as an
  observation, but its gloss "first take of a boot" should read "first take of a restarted Core process". A1 was the
  second take of that boot and clean; A2 the third and 10 % lost; on 11-01 the second take (#70) already lost 34. The two
  nights do not agree on *when* the drift starts, only that it exists under `writer`. (measured)

### 1.3 What differs between the first take of a boot/process and the later ones (candidates, each with its check)

| Candidate | Why it could matter | Status | Check (no code; Patrik runs `sudo`) |
| --- | --- | --- | --- |
| Clean page cache left by earlier takes (`MemFree` 300 MB vs 2.7 GB) | only ~6 s of difference (1.2); but reclaim then runs for the whole take either way | probable: not the carrier | M1/M2 of section 8 (`pgscan_direct`, `allocstall_*` per minute) |
| Slab: exFAT inodes/dentries (15,000 files per 10-min take), buffer heads for the FAT and bitmap (FAT ~29 MB, bitmap ~0.9 MB for 7.3 M clusters of 128 KB) | more unreclaimable or slow-to-reclaim memory per take; FAT pages touched move with the allocation pointer | unconfirmed | `grep -E 'Slab|SReclaimable|SUnreclaim|Buffers' /proc/meminfo` and `sudo grep -E 'exfat|buffer_head|dentry' /proc/slabinfo` before each take of B4 |
| Swap: the UI's and Core's cold anonymous pages swapped out during a take, faulted back on the next (2026-10-26 saw 89 MB of swap in use) | a page fault with I/O on the UI render thread or on libcamera's thread is tens of ms | unconfirmed | `pswpin pswpout` deltas (add to `take3v2.sh`'s `KEYS`), `grep VmSwap /proc/$(pidof apertar-core)/status` and the UI pid, `free -m` before each take; `vm.swappiness` |
| Fragmentation (buddyinfo: no order >= 8 free at the end of boot 1; kcompactd 47-232 wakes per take) | high-order allocations (dma-buf system heap tries order 8 then 4: `system_heap.c:43-55`) fall back and trigger `boost_watermark` (+ up to 150 % of high per event, `page_alloc.c:1918-1949`), which wakes kswapd to reclaim and compact | measured present in clean and bad takes alike (night report section 3): not the cause alone | `cat /proc/buddyinfo` per take; `pgsteal_kswapd` while `compact_*` flat vs not |
| Core RSS and the raw pool | `4abbef0` keeps queue+workers+2 copies (frames mode) or the RAM budget's worth through a take, trims to idle at stop (`CameraController.cpp:4862-4871`); glibc arena fragmentation across takes | unconfirmed | `grep -E 'VmRSS|VmHWM' /proc/$(pidof apertar-core)/status` before each take |
| UI RSS | Qt caches, QML images, the dropped-frame chip relayout per drop | unconfirmed, low | same for the UI pid |
| NVMe temperature | A0 cooled to 34 C; back-to-back takes 4 min apart on 11-01 | 2026-10-30 ruled heat out for stalls (65-72 C); a throttling drive shows in the queue first | `cat /sys/class/nvme/nvme0/device/hwmon*/temp1_input` (already in `take3v2.sh`) |
| exFAT allocation pointer / fill | 0 -> 32 % across #69-#72; metadata reads per new cluster run | unconfirmed; fill losses were queue-full historically (section 5) | B3(d) |
| journald | Core's `drop[...]` lines are rate-limited (1st, every 30th, >1); the libcamera per-frame warning is silenced on 11-01 (`LIBCAMERA_LOG_LEVELS=IPARPI:ERROR`, set outside the repo) | not a within-boot variable | n/a |

### 1.4 Derived numbers the record did not state

- **`MemAvailable` at take start, from the RAM budget** (README: budget = 0.6 x MemAvailable - 512 MiB, capped at 0.5 x
  MemTotal; the cap, ~2.1 GB, did not bind): #69 3.48 GB, #70 3.35, #71 3.37, #72 3.31, #74 3.45, #75 3.37, #78 3.23 GB.
  So the kernel counted 3.2-3.5 GB as available in every take; the writer arm had less of it *free* (275-327 MB) and the
  sync arm more (507-788 MB). (probable: formula from the project README; `queue_budget=` values from the raw journal)
- **Watermarks on this board** (`page_alloc.c:6125-6185`): with `min_free_kbytes` 16384 (measured default on the Pi),
  WMARK_MIN = 16 MB, WMARK_LOW = min + max(min/4, 0.1 % of managed) ~ 20 MB, WMARK_HIGH ~ 24 MB, summed over zones. With
  65536: 64 / 80 / 96 MB. `kswapd_low_wmark_hit_quickly` 948-1805 per writer take (night report section 2) means kswapd
  was re-woken that many times before it could sleep (`vmscan.c:7162-7165`): the system sat on the low watermark for the
  whole take. Direct reclaim is throttled only below min/2 (`vmscan.c:6367-6400`), so writers reclaimed freely.
- **Time to first kswapd wake** = (MemFree - 20 MB) / 415 MB/s: #70 0.7 s, #80 6.6 s.
- **A0's boot age** >= 7 h 26 min (01:04:19 -> 08:30). The overnight test before it: 48 + 23 runs x 240 s x ~415 MB/s
  through the page cache with Core stopped (`hardware-log.md:701-734`). Whether that test program called
  `fadvise(DONTNEED)` is unknown (`/home/pi/ab-tests/variant2.py`, not in any repo): `grep -n fadvise /home/pi/ab-tests/variant2.py`.

### 1.5 Which test splits the explanations

| Test | Setup | Reads | Decision |
| --- | --- | --- | --- |
| **T1: A0's protocol on today's stack** | reboot; `fstrim`; drive <= 55 C; `buffer=frames` in `[storage]` (A0 had no RAM mode); `APERTAR_DNG_DONTNEED=writer` via the `/run` drop-in; UI `c13b846` running, aids on; WebUI closed; one 10-min take with `take3v2.sh 600` as the first take of the boot | lost per minute; M2 deltas; `MemFree/Slab/VmSwap` before | **clean**: A0's cleanness was its position (first take of a process/boot) and the regression is the drift, not the code: go to B4 with the extra rows of 1.3. **Losing from minute 1**: something in the code or driver changed the regime: run T2 |
| T2: bisect the stack (only if T1 loses) | same protocol, one change per run, cheapest first: (a) UI `~/ApertarUI-a0` (verify its hash with `git -C ~/ApertarUI-a0 log -1`; expected `ea44bd7`-era); (b) Core `a40112a` built into a second build dir (`cmake -S ~/ApertarCore -B ~/ApertarCore-a0-build` at a worktree of `a40112a`, 20-30 min, never during a take) with today's UI; (c) driver `24172e6` (`git -C ~/drivers/imx585-v4l2-driver checkout 24172e6 && ./setup.sh`, reboot) | as T1 | the first arm that is clean names the side; if none is, the drift is not a code property and T1's "losing from minute 1" was the drift arriving early |
| T3: ram vs frames | `writer`, two 3-min takes interleaved F R F R after a warm-up | lost; `queue_budget` present/absent | a difference >= the writer spread of 11-01 (34-153): the RAM mode is a co-factor to keep in the A/B matrix; otherwise drop it |

## 2. The CSI-2 link at 1782 Mbps (891 MHz x 2)

### 2.1 What the receiver does with an out-of-range rate (confirmed, source)

`dphy.c:99-128`: `dphy_set_hsfreqrange` holds a 39-entry table ending at `{1500, 0b111100}`; for `mbps > 1500` it logs
`DPHY: Datarate %u Mbps out of range` and the lookup loop (`i < ARRAY_SIZE - 1`) falls through to that last bin. The PHY is
therefore programmed with the 1450-1500 Mbps calibration code while the sensor drives 1782 Mbps/lane. The handbook
(`cinemate-handbook/lessons/hardware-log.md:741-749, 761-766, 772-776`) measured the consequence on a CM5: 1440 clean,
**1782 "marginal-but-holding"** through ~5 minutes of sweeps, 2079 truncating rows after minutes; the clamp "costs receiver
margin", and the PHY setting is mode-invariant. The 11-01 Pi logs the warning at every stream start (night report section 3).

### 2.2 Can it cause single-frame losses that correlate with memory/UI load?

- A **link error** (bit errors from reduced margin) shows as a CSI-2 **discard**: LEN (length limit), UNMATCHED (unmatched
  packet), INACTIVE; counted per VC with the data type (`csi2.c:219-258`). Its rate depends on signal integrity (cable, temperature,
  the sensor's PLL), not on what the CPUs or the GPU do. A discarded frame leaves the same timestamp hole as a starved
  CFE (dt = 2 x period), so Core cannot tell them apart (KB `dng-chain/R7.md:15`). **It cannot correlate with memory or UI
  load, so it cannot explain UI-on vs UI-off or writer vs sync.** (confirmed logic)
- A **receiver FIFO overflow** (OVLF: `IRQ_OVERFLOW` and `IRQ_DISCARD_OVERFLOW`, `csi2.c:79-80, 223-224`) happens when the
  CSI-2 write-out to memory cannot keep pace with the incoming lane data. That *is* a memory-bus effect and *would*
  correlate with the UI's GPU traffic and with reclaim-induced bus load. At 1782 Mbps the receiver has less time per byte
  than at 1440, so an overflow, if the fabric is the bottleneck, is more likely at the higher rate. (probable mechanism;
  unconfirmed on this rig: never read during a losing take)
- The 2026-10-26 reading (`hardware-log.md:64-95`): with `rp1_cfe.track_csi2_errors=1`, `csi2_errors` was **all zero** under
  `dd` buffered, direct and tmpfs loads that cost frames; **"not read"** during the takes themselves. So the one measurement
  that could implicate the link was never made in a losing take. Whether the cmdline flag survived the later reboots is
  unknown (`cat /proc/cmdline`).

### 2.3 How to read `csi2_errors` during a losing take (procedure)

- Needs `rp1_cfe.track_csi2_errors=1` on `/boot/firmware/cmdline.txt` and a reboot: the parameter has permission 0
  (`csi2.c:19-20`, load-time only) and the IRQ error mask is written only when it is set (`csi2.c:295-296`).
- The file is `/sys/kernel/debug/rp1-cfe:*/csi2_errors` (`cfe.c:2337-2341`, `csi2.c` debugfs init); **it zeroes the
  counters on every read** (`csi2.c:189-192`), so read it once right before `record_start` (discard that reading), then
  once right after `record_stop`; a mid-take per-minute read is fine as long as every reading is kept and summed.
- Output: `Overflows N`, then a table per VC with `OVLF LEN UNMATCHED INACTIVE`, then `Last DT` per column
  (`csi2.c:196-212`). Reading: `Overflows`/`OVLF` > 0 with the gap count = memory-side starvation at the receiver (a
  genuine co-cause, and the 1440 control test becomes decisive); `LEN`/`UNMATCHED` > 0 = link corruption (lower the rate
  regardless of the memory work); all zero while frames are lost = the loss is behind the receiver (CFE job not scheduled:
  libcamera/Core late), which is where the memory hypothesis lives.
- Also unconditional in `dmesg`: `Orphanded frame at seq N` (`cfe.c:684-686`, a `WARN`) when the CFE sees frame events out
  of order; `sudo dmesg | grep -c Orphanded` before and after a take costs nothing.
- Not available on this kernel: the `cfe_check_job_ready` line "has no buffer, unable to schedule job" (`cfe.c:613-631`) is a
  `dev_dbg` behind `verbose_debug` (`cfe.c:52-61`); `bcm2712_defconfig` has no `CONFIG_DYNAMIC_DEBUG` and the driver's
  Makefile adds no `-DDEBUG`, so the call compiles out (the 2026-10-26 entry already found this on the Pi). Section 8's
  M6 should drop that half.

### 2.4 A lower link frequency for a control test (confirmed table, probable fps)

`imx585.c:255-284` lists link frequencies 297, 360, 445.5, 594, **720**, **891**, 1039.5, 1188 MHz (= 594 .. 2376 Mbps/lane).
The 4-lane 4K 12-bit minimum HMAX per link (`imx585.c:287-302`): 792 at 594 MHz, **660 at 720 MHz, 550 at 891 MHz**. With
the 74.25 MHz pixel clock and the default VMAX 2250: 720 MHz gives a 20.0 ms frame (50 fps SDR), 891 MHz 16.7 ms (60 fps);
Clear HDR halves the rate (driver `README.md:121`), so **4K Clear HDR 16-bit tops out at exactly 25.0 fps at 1440 Mbps**
(probable: table plus the README rule; the probe will print the exact figure) and at 20.8 fps at 1188 Mbps. 1440 is the
only in-spec rate that reaches 25 fps, with no headroom: a 25 fps take sits on the mode's minimum frame duration. Link
payload at 25 fps: 3840 x 2200 x 16 bit x 25 = 3.38 Gbit/s = 59 % of 4 x 1440 Mbps (47 % at 1782), so bandwidth is not
the limit, the sensor's line time is. The handbook's CM5 ran 16-bit Clear HDR clean at 1440 after its Y16 fix
(`handbook hardware-log.md:865-880`).

Control test: `dtparam`/overlay `link-frequency=720000000` in `config.txt`, reboot, confirm `dmesg | grep DPHY` is silent
and the probe lists Clear HDR 16-bit 4K at 25 fps; one 10-min `writer` take with the UI running (the losing
configuration). Clean at 1440 and losing at 1782 under the same memory numbers = the clamped PHY is a co-cause (or the sole
cause); losing at both = the link is out. If the probe gives 24.x at 1440, run the pair at 24 fps instead.

## 3. CPU0's interrupts

### 3.1 Which can move (confirmed, source) and which cannot

| Line | Chip path | Movable from user space? | Source |
| --- | --- | --- | --- |
| rp1-cfe (154), USB (~700/s), I2C bus 1 (~570/s), every other RP1 peripheral | RP1 child irqchip -> PCIe MSI-X vector of the brcmstb controller | **No.** `rp1_irq_set_affinity` forwards to `msi_domain_set_affinity` on the PCIe MSI vector (`rp1.c:144-157`); that domain is created with `MSI_FLAG_NO_AFFINITY` (`pcie-brcmstb.c:671-674`), so its top chip gets no `irq_set_affinity` (`msi.c:835-836`), and its bottom chip has none either (`pcie-brcmstb.c:720-724`); `msi_domain_set_affinity` calls `parent->chip->irq_set_affinity` unconditionally (`msi.c:663-670`). The RP1 chip itself *advertises* the op, so the kernel's user-space guard (`manage.c:173-179`, `proc.c:141`) lets the write through to that call. **A write to `/proc/irq/154/smp_affinity` is at best refused and may oops the kernel: do not try it on the camera.** | as cited |
| All RP1 interrupts together | the controller's single "msi" GIC SPI with a chained handler (`pcie-brcmstb.c:882`, `brcm_pcie_msi_isr` :676-699) | In principle yes (a GIC SPI), but it is hidden from `/proc/interrupts` (chained handler, no counts) and its number must be found first; moving it moves every RP1 interrupt (camera, USB, I2C, Ethernet) to one other CPU | procedure below; **probable**, untested on a Pi 5 |
| NVMe completion queues (`nvme0q*`) | PCI MSI-X on the other brcmstb controller (pcie1) | No, same `MSI_FLAG_NO_AFFINITY`; they all land on the CPU their controller's "msi" SPI targets, CPU0 by default | not in the record: `grep nvme /proc/interrupts` twice 10 s apart during a take gives the rate (expect thousands/s at 415 MB/s with 128 KB requests: unconfirmed) |
| v3d (173, 174) | GIC SPI | yes (the night moved them to CPU2: no gain, #61-#62) | night report section 3 |
| hvs (175) | GIC SPI | the night found "cannot be moved"; reason not recorded | `cat /sys/kernel/irq/175/chip_name` and `dmesg` after the write would say |

Finding the PCIe MSI parent, if ever wanted: `for d in /sys/kernel/irq/*; do [ -z "$(cat $d/actions)" ] && echo "$(basename $d) $(cat $d/chip_name) hwirq=$(cat $d/hwirq)"; done`
lists interrupts without an action (chained parents among them); match the hwirq against the `interrupts` property of
`/proc/device-tree/axi/pcie@120000` (the RP1's controller; `interrupt-names` has "msi"). Then
`echo 2 | sudo tee /proc/irq/<N>/smp_affinity` and watch whether the rp1-cfe counts in `/proc/interrupts` start growing in
the CPU1 column. This is a one-shot experiment with a reboot as the undo.

### 3.2 What a test looks like (the movable parts)

| Test | Command (during a take, no restart) | Reads | Decision |
| --- | --- | --- | --- |
| libcamera's thread off CPU0 | `tid=$(ps -L -o tid,comm -p $(pidof apertar-core) \| awk '$2=="CameraManager"{print $1}'); sudo taskset -pc 1 $tid` (also the IPA thread if present: `comm` begins with `IPA`/`ipa`) | lost per minute vs the same take before; `perf sched timehist -p $tid` if `linux-perf` is installed | gaps gone on CPU1 = CPU0's interrupt load was on the path; unchanged = it was not |
| NeoRotary poll off | unplug the NeoRotary 4 from bus 1 for one take (Core logs the input as disabled), or raise `poll_ms` in `apertar-hardware.conf` to 1000 for the take; confirm with `grep -E 'i2c|1f00074000' /proc/interrupts` twice 10 s apart (expect ~570/s -> ~30/s) | lost | a drop >= the take-to-take spread = the poll costs; the prior is low (microseconds each, no memory interaction) |
| NVMe IRQ rate | `grep nvme /proc/interrupts` at t and t+10 s during a take | completions/s and their CPU column | thousands/s on CPU0 next to rp1-cfe is a co-factor worth one move of the pcie1 "msi" parent (3.1 procedure), nothing more |

Context from 2026-10-26 (`hardware-log.md:153-202`): libcamera's `CameraManager` thread was 40-54 % busy while recording
Clear HDR 16-bit, with IPC falling from 1.87 to 1.30 under recording load (memory contention), and the RPi pipeline runs
one frame at a time through IPA + back end. A 40 ms frame period leaves that thread ~20 ms of slack at 25 fps; an interrupt
storm on its CPU shortens the slack but cannot by itself consume 40 ms. CPU0 placement is therefore a magnitude factor at
most (probable).

## 4. The two preview feeds

### 4.1 WebUI (MJPEG) preview: a per-frame cost on the completion thread while a browser is attached (confirmed)

- Gate: `mjpegClientCount_ > 0` (`ApertarCoreApp.cpp:8184`), incremented per HTTP viewer (`:9906-9910`).
- On libcamera's completion thread (`captureWebPreviewFrame`, `:9730-9830`; the comment at `:9738-9740` says so): a rate
  check (30 fps, or `APERTAR_WEB_PREVIEW_RECORDING_FPS` while a take runs, `:79-97`), then under `mjpegMutex_` three
  nearest-neighbour downsample passes 1280x720 -> 640x360 (`downsampleNearestPlane`, `:9813-9818`) reading the camera's
  preview dma-buf through a CPU mapping (`webPreviewSlots_`, mapped at registration), writing ~350 KB. The KB's profile
  gives 0.2-0.5 ms per frame (`dng-chain/V/H4`, measured on an earlier build: probable for today's).
- On `mjpegThread_` (`runMjpegEncoder`, `:9833-9880`): turbojpeg/libjpeg encode of the 640x360 YUV at quality 75, a few ms
  per frame on one core, up to 30 fps: roughly a tenth of a core (probable, not measured).
- Around it: the browser's state polling (`/api/state`, `/api/buffer`) serialises Core's whole state on the HTTP threads;
  #76 (49 lost in 29 s while the ladder was edited in the WebUI) is that, not the preview.
- The evening's evidence on its cost is inconsistent: +2.1 points at 19:11 vs 19:09, but #61 (open) 14.3 % against #62
  (closed) 18.1 %. So the magnitude is unmeasured; the scripts' refusal to run with a client on `:8000` is the right rule
  as a **confound control**, and nothing in the compared takes (#69-#80, A0) had a client.

### 4.2 Touch UI preview feed: zero-copy, off the completion thread except a descriptor hand-off (confirmed)

- Registration (once per buffer slot, at stream start): `CameraController.cpp:9950-10020` `dup()`s the plane fds and
  sends a `preview_buffer` event with `SCM_RIGHTS` (`ApertarCoreApp.cpp:14488-14540`, `controlServer_.broadcastWithFds`).
- Per frame on the completion thread: `publishPreviewFrame` (`CameraController.cpp:9928-9949, 10024-10072`) fills a
  `PreviewFrameDescriptor` (slot, frame id, timestamp, layout; no `dup`, no syscalls) and calls the callback;
  `enqueuePreviewFrame` (`ApertarCoreApp.cpp:8175-8221`) takes `previewMutex_`, replaces the pending frame (latest-only)
  and notifies. Microseconds.
- Publisher thread (`runPreviewPublisher`, `:14542-14580`): serialises ~120 bytes of JSON per frame and `broadcast`s it to
  every control-socket client (`:14536-14540`; `ControlServer.cpp:175-182`) with `send(..., MSG_DONTWAIT)`; a client whose
  buffer is full is dropped, never waited for (`ControlServer.cpp:27-36`, comment "Never let a stalled preview client block
  camera event delivery").
- UI side: `ApertarPreviewSocketClient.cpp:65` non-blocking stream socket, `:202` `recvmsg(MSG_DONTWAIT)`; the renderer
  imports each slot's dma-buf once (`PreviewWindowRenderer.cpp:1725-1760` re-imports only on a layout change;
  `eglCreateImageKHR(EGL_LINUX_DMA_BUF_EXT)` at `:1834-1900`) and samples it on the GPU per redraw. A CPU fallback
  (`uploadCpuFallbackTexture`, `:1530-1600`: `mmap` + `glTexImage2D` per frame) exists if the import fails: whether it is
  ever active on this rig is unconfirmed (the journal would show the `qWarning` at `:1902`).
- The `buffer` event (dropped-frame count for the chip) is its own thread at 4/s while recording (`runBufferEvents`,
  `ApertarCoreApp.cpp:10946-11010`, interval `:11009`). Not per frame.

So the touch UI's cost to the capture path is not in the feed; it is the GPU/memory-bus work of drawing (the night's
UI-stopped/UI-frozen contrast, `hardware-log.md:945-975`), which is what the memory regime modulates.

## 5. The drive

### 5.1 What Core's trim does and when (confirmed, source)

- Root helper `scripts/apertar-media-trim`: validates the mount point, requires discard support, runs `fstrim -v` with a
  20 s limit (exit codes 0-4).
- Core (`ApertarCoreApp.cpp:11386-11433`): a worker thread; requests coalesce; triggers are `mount`, a Core delete batch
  that frees >= 1 GiB (`trimMediaAfterDelete`, `:11418-11425`), a free-space jump >= 1 GiB between two media-watcher polls
  while idle (`:10856-10861`, covers the touch UI's own deletes), and every pre-roll clip delete (`04bac89`); `mediaTrimMayRun`
  (`:11428-11433`) refuses while recording, during audio, timelapse, pending writes, a delete, a pre-roll, standby or a
  speed test. `APERTAR_MEDIA_TRIM=0` disables it (`:6377-6381`). Measured once: 927 GB in 0.47 s (`hardware-log.md:813-820`).
- Not yet shown: the acceptance test over one full pass of the drive (project README open item 4).

### 5.2 Where fill losses appear, and what that says about #78's tail

- 2026-10-26 (`hardware-log.md:378-392`): at 77-81 % full, 3-min takes lost 166 and 676 frames **to `queue-full`**, the
  queue filling from ~95-140 s; the drive had never been trimmed since the format (later explained by the 0.9 TB finding).
  2026-10-30 (`:701-734`): the stall is the untrimmed drive, not fill; the writers sat in exFAT metadata calls with nothing
  in flight; trimmed, 909 GB of back-to-back writes stayed clean.
- #78 (23:02-23:12): 25 lost, per minute 0,0,3,3,3,3,5,5,7,**25**; `dropped_queue_full=0`, `peak_queue=2/12`, drive 0 -> 97 %
  full on a drive trimmed at 21:50 and after the pre-roll at 22:46. The 18 last-minute losses are **capture gaps with an
  empty queue**. A slowing drive shows in the queue first (four writers, 12 frames of cushion = 0.5 s): nothing in #78
  says the drive slowed. **Fill-as-drive-slowness is a point against, not for.** (measured; reading probable)
- What fill can still do to capture: more work per file on a nearly full exFAT volume (`exfat_alloc_cluster` bitmap scans,
  FAT entry reads via `__bread_gfp`, seen in the 2026-10-30 stack dumps when the drive stalled) = more page allocations
  and more buffer-head churn **inside a memory regime already at the low watermark**. In `sync` mode the regime is
  mild (kswapd 586 k pages in #78 against 3 M per 3 min under `writer`) but not absent; the 3-7 losses in minutes 3-9 of
  #78 rose slowly before the last-minute jump. So fill is a plausible *amplifier* of a residual memory effect, not a cause
  of its own. #80 (empty drive, `min_free_kbytes` 64 MiB, dirty limits) removed both at once, which is why B3(d)/(e) of
  section 8 (full drive with and without a trim, under the #80 knobs) is the right separation. (probable)
- Fill also cuts the drive's own write cache and, on an untrimmed volume, puts writes onto never-trimmed blocks; both
  show as queue growth, which `peak_queue` in the stats line and the per-minute `buffer` level already capture.

### 5.3 Other drive-side items not weighed by the night

- `nvme.max_host_mem_size_mb=0` (the drive asks for 64 MiB of host memory and gets none, `hardware-log.md:725-726`): HMB
  holds the drive's mapping tables; without it some controllers read mapping pages from NAND, slowing random writes; our
  writes are sequential, and the effect would be queue-side. Low prior; one boot without the argument is the test (README
  open item 5).
- A huge `fstrim` right before a take (927 GB at 23:13, then #80 at 23:2x): the device processes the discards internally
  afterwards; a background erase storm would show as write latency (queue), not as capture gaps. #80 was clean anyway.

## 6. Ranking: plausibility as primary cause or required co-cause, with the one test each

| Rank | Co-factor | As primary cause | As required co-cause | Status | The one test |
| --- | --- | --- | --- | --- | --- |
| 1 | **State that builds within a boot/Core process under `writer`** (cache full of clean pages, slab, swap, fragmentation, RSS: 1.3) | high: writer takes drift 1 -> 34 -> 153 within 13 min; A0 -> A1 -> A2 drifted 0, 0, 10 % two days earlier; `sync` takes do not | n/a | measured (drift), mechanism unconfirmed | **B4** of section 8 plus the rows of 1.3 (`Slab`, `SReclaimable`, `pswpin/pswpout`, `VmSwap`, `VmRSS` of Core and UI, `buddyinfo` before each take); M1/M2 per minute. `echo 3 > drop_caches` before the fourth take separates reclaimable state from the rest |
| 2 | **The touch UI's GPU/display work** | no (clean under `sync` with the UI drawing: #74, #75, #80) | yes for `writer` losses (UI stopped or frozen: clean, `hardware-log.md:945-975`) | confirmed as conditional | B8 of section 8 only if losses survive B6 |
| 3 | **Code/driver changes since A0** (Core `a40112a` -> `64bbbaa`, UI `ea44bd7` -> `c13b846`, imx585 `24172e6` -> `cd548ef`, RAM mode) | possible as a magnitude factor (A1 clean after 250 GB on `a40112a`; #70 lost 34 after 74 GB on `64bbbaa`), not demonstrated | possible | unconfirmed | **T1** (1.5): today's stack, `writer`, `buffer=frames`, first 10-min take after a reboot, A0's protocol. Clean = rank 1 carries it; losing from minute 1 = T2 bisect (UI, Core, driver) |
| 4 | **`vm.min_free_kbytes` 16 -> 64 MiB** (Apertar's own knob, not CineMate's) | n/a (a remedy) | the most likely of #80's three changes to matter: it moves kswapd's wake and direct reclaim's onset four-fold for every allocator, where `dirty_bytes` throttles only the writers (`page-writeback.c`) | probable | B3(c) vs B3(b) of section 8 |
| 5 | **Drive fill / exFAT metadata** | low: fill losses were queue-full (2026-10-26), #78's tail was capture-gap with an empty queue | plausible amplifier under a tight regime (5.2) | measured against, mechanism probable | B3(d) (>= 85 % full, trimmed) vs B3(e) (untrimmed) under the #80 knobs |
| 6 | **CPU0 interrupt concentration** (rp1-cfe, NVMe queues, USB, I2C, v3d/hvs; all RP1 and NVMe lines pinned by the kernel) | low: cannot consume 40 ms; v3d moved with no gain | low-moderate as a slack reducer for libcamera's thread | confirmed (pinning), unconfirmed (effect) | `taskset -pc 1 <CameraManager tid>` for one losing take (3.2); never `/proc/irq/154/smp_affinity` |
| 7 | **CSI-2 link at 1782 Mbps** | low: a link error cannot correlate with UI/memory state; the handbook's 1782 "holds" | low-moderate only through receiver FIFO overflow (OVLF), never measured | unconfirmed | `csi2_errors` before/after one losing `writer` take (needs `rp1_cfe.track_csi2_errors=1`, reboot). OVLF > 0 or Overflows > 0: run the 1440 Mbps pair (2.4). All zero: the link is out |
| 8 | **NeoRotary poll** (~570 IRQs/s on CPU0, I2C) | very low | very low | unconfirmed | unplug (or `poll_ms` 1000) for one losing take |
| 9 | **WebUI preview** | n/a in the compared takes (no client) | a confound, not a co-cause | confirmed cost on the completion thread, magnitude unmeasured | keep the "no client" rule; if ever measured, two takes with/without a browser under `sync` |
| 10 | NVMe thermal, HMB=0, post-trim internal GC | very low (all show in the queue first) | | unconfirmed | `peak_queue` and the per-minute buffer level already cover them |

Order for the Pi session (after B0): T1 (it is the A0 protocol and doubles as B1's `writer` warm-up), then B1, B2, B3 as in
section 8, with the 1.3 rows added to every take's readings; T2/T3, the `csi2_errors` read and the `taskset` take only if
losses survive B1-B3.

## 7. Facts for the KB (what this report establishes, by status)

- confirmed (source): rp1-cfe/RP1 interrupts are not user-movable on rpi-6.12.y (`rp1.c:144-157`, `pcie-brcmstb.c:664-674,
  720-724`, `msi.c:663-670, 835-836`); `csi2_errors` semantics (`csi2.c:19-21, 175-258, 295-296`); the "has no buffer" line is
  compiled out (`cfe.c:56-61`, defconfig); D-PHY clamp (`dphy.c:99-128`); Core's touch-UI feed is off the completion thread
  except a descriptor hand-off, the WebUI downsample is on it (`ApertarCoreApp.cpp:8175-8223, 9730-9830, 14488-14580`,
  `CameraController.cpp:9928-10072`); Core's trim triggers and exclusions (`ApertarCoreApp.cpp:10856-10861, 11386-11433`);
  CineMate sets no `min_free_kbytes` (`storage-automount.py:319-335`); the imx585 link table and 4K HMAX per link
  (`imx585.c:255-302`).
- measured (record): RAM mode in every 11-01 take (`queue_budget=` lines); A0's boot age >= 7.4 h (`hardware-log.md:925-926`);
  fill losses of 2026-10-26 were queue-full; #78's tail was capture-gap with `peak_queue=2/12`.
- probable: `MemAvailable` ~3.3 GB at every 11-01 take start (from the budget formula); 4K Clear HDR 16-bit = 25.0 fps at
  1440 Mbps; OVLF as the only link-side counter that could track memory load.
- refuted: "A0 was clean because it was early in the boot".
- unconfirmed, with the measurement named: everything in 1.3's table; the driver's share (T2c); the heap Core's raw buffers
  came from (`journalctl -u apertar-core -b | grep -E 'RAW buffers|cached DMA'`: `allocateCachedBuffers`,
  `CameraController.cpp:8661-8691`, tries `vidbuf_cached` then `linux,cma`, else libcamera's allocator; with CmaTotal 64 MB
  the 8 x 16.9 MB raw buffers cannot be CMA, so the fallback line should be in the journal); the NVMe IRQ rate and CPU.
