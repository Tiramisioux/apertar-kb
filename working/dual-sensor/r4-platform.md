<!-- Dual sensor, reader report 4 (2026-11-03): the platform: libcamera with two cameras (back end, one process or two), where the tuning file is chosen, rpi.sync, the driver sync modes, bandwidth, CM5. Written by a read-only research agent on the Mac from git refs (libcamera apertar 6b0b49f3 on base 7e9fef0b, Cinemate libcamera bfe0b76a0, driver apertar e5b74d3 and cinemate-port cd548ef, Core 31d5418) and three public web pages. Written before r5: its cam1 I2C node and carrier lines are superseded there. Frozen: do not edit; corrections go in design-dual-sensor.md and its verification table. -->

# Dual-IMX585 on Pi 5 / CM5: platform facts (read-only research)

**Legend.** [C] confirmed in code/data. [P] probable. [U] unconfirmed (settling step given). [M] measured. [E] estimate. [W] public web page read through the fetch tool (summary, not verbatim).
Cites: `L` = Apertar/libcamera `apertar`@6b0b49f3 (base 7e9fef0b). `CL` = Cinemate libcamera `cinemate`@bfe0b76a0. `D` = imx585 driver `apertar`@e5b74d3. `D2` = driver `origin/cinemate-port`@cd548ef. `C` = Apertar-Core `drop-frames`@31d5418. `KB` = apertar-kb working tree (file:line).
The Pi runs the base 7e9fef0b from /usr/local; the fork's two commits live only in the private `~/opt/libcamera-apertar` (KB fork-log.md:195-206, working/handoff-T26-T30.md:21).
No dual-camera measurement exists anywhere in the KB or Cinemate docs, so every dual number below is an [E].

## Q1. Two cameras, the back end (BE), one process vs two

**Fork's own commits** (`git log 7e9fef0b..apertar`): `889567ab` (`QBC_RAW_STATS_ROW_STEP`) and `6b0b49f3` (`QBC_RAW_CPU_WORKER=1`). The SW raw stats, CcmpUnwrap and QBC are Will Whang's base. The CPU-cached heap buffers are Core's (`C:CameraController.cpp:8675-8682`), not libcamera's.

**How a camera gets a BE [C].**
- `pipelineFactoryMatch` re-runs `match()` until it returns false (`L:src/libcamera/camera_manager.cpp:154-168`).
- `PipelineHandlerPiSP::match` (`L:.../pisp/pisp.cpp:1153-1237`) loops `numCfeDevices = 2` (:1155). Each pass acquires one `rp1-cfe` media device (:1168) and one `pispbe` media device with 8 nodes (:1175-1184). `acquireMediaDevice` skips devices already busy (`pipeline_handler.cpp:136-149`, `device_enumerator.cpp:348-363`). Camera k therefore pairs CFE k with BE node group k.
- Each camera has its own `PiSPCameraData` with private libpisp FrontEnd/BackEnd objects (:1215-1218).
- Kernel [C per KB, kernel source not on this Mac]: `PISPBE_NUM_NODE_GROUPS 2`, one shared `job_queue`, one running/queued pair. The two groups time-share one engine, so there is no extra BE throughput (`working/research-30fps/q2-pipelining.md:99`).
- [U] on the Pi: `ls /dev/media*` must show 2 `rp1-cfe` and 2 `pispbe`. Without a second `pispbe`, camera 2 fails with "Unable to acquire ISP instance" (:1186-1189).
- Acquire: `PipelineHandler::acquire` does `lockf(F_TLOCK)` on all media devices of that handler (`pipeline_handler.cpp:171-191`, `media_device.cpp:144-153`). Process A can hold (CFE0, BE0) while B holds (CFE1, BE1). Maximum 2 cameras.
- One `CameraManager` per process (`camera_manager.cpp:309-311`).
- In one process both cameras' pipeline code runs on the single CameraManager thread (`pipeline_base.h:119-123`). Each camera has its own IPA thread (`module_ipa_proxy.cpp.tmpl:49,95`).

**Fork state in ONE process [C].**
- No mutable statics in `pisp/`, `src/ipa/rpi`, `common` (only function-local const tables and load-time registries).
- `RawCpuWorker` (pisp.cpp:737, member :1026), `RawStatsProducer`, `CcmpUnwrap` and `QbcRemosaic` (:1034-1049) are per-camera members. Nothing breaks.
- Caveats: the two env knobs are process-wide (pisp.cpp:878, raw_stats.cpp:39). A worker thread is created per enumerated camera, used or not. SW stats read black level and metering weights from a hard-coded `/usr/local/share/libcamera/ipa/rpi/pisp/<model>.json`, ignoring the tuning env (`tuning_helpers.cpp:18-21`).
- CPU work scales linearly, and only for 16-bit Clear HDR (swap + SW stats, pisp.cpp:1740-1750, 1811-1845). SDR 12/10-bit has none. Measured ~17 ms/frame/camera while recording at 30 fps, inline (KB lessons/hardware-log.md:184-193) [M].
- One process, inline passes, two HDR16 cameras: ~34 ms of a 40 ms period on one thread [E]. Needs the worker or two processes.

**Cross-process hazard [C code, effect U].**
- Every `CameraManager::start()` runs sensor `init()` on every sensor it enumerates, acquired or not. The IMX585 driver has one source pad (`D:imx585.c:2629-2631`), so this is `CameraSensorLegacy` [P]; the Raw class does the same (`camera_sensor_raw.cpp:540-549`).
- It clears HFLIP/VFLIP (`camera_sensor_legacy.cpp:213-218`; EBUSY while streaming, `D:2288-2291`), writes HBLANK = minimum (:288-296) and test pattern off (:298).
- Core `reconfigure()` is `stop(); start()` with a new CameraManager (`C:CameraController.cpp:7452-7458, 7247`). Every mode change in process B therefore rewrites HBLANK on A's streaming sensor.
- A's IPA re-sends HBLANK every frame (`ipa_base.cpp:1874-1875`), so the predicted effect is 1-3 frames of wrong line length (period, exposure, phase). No per-camera enumeration filter exists in this tree. Test M2.

**Core single-camera assumptions [C].**
- First non-USB camera (`C:CameraController.cpp:7262-7265`).
- The WDR/HDR knobs and the mode probe use the first `imx585` subdev (:6875-6892, 6925, 6960, 7040-7149). A streaming sensor returns EBUSY on WDR (grabbed control, `D:2288-2291`). Only `resetStoppedSensorTiming` matches by of_node (:8118-8130).
- The tuning env is process-wide (:1421-1430).
- Core has zero use of `rpi::Sync*`.
- Media actions (trim, pre-roll, format) are per-process [U].
- RAM-mode queues each take ~1.4 GB on a 4 GB board [M budget, KB dng-chain-feasibility.md §1]; two processes over-commit. Use `buffer=frames`.

**Cinemate.**
- Same `match()` (`CL:pisp.cpp:872-958`). Its `pisp/` dir is a lone pisp.cpp with no SW raw passes.
- Installer default ref is `cinemate` (`cinemate-install.sh:94-95`), tip bfe0b76a0 = v0.5.0+rpt20250429+24. Current HEAD e23826dcf is cinemate + 1 (imx283 vc4 tuning).
- Ships dual as one `cinepi-raw` per sensor with `--cam-port` and `--sync server|client` (`cinepi_multi.py:791-797`, `docs/dual-sensors.md:3`). The driver authors say "CineMate ships dual-imx585 rigs" (`D2:4669`).

## Q2. Where the tuning file is chosen

- Per camera, when it is registered at `CameraManager::start()`: `registerCamera` -> `loadIPA` -> `ipa_->configurationFile(model + ".json")` (`L:pipeline_base.cpp:875, 1206-1221`; `_mono` suffix :1216-1218) [C].
- `ipaConfigurationFile` first reads env `LIBCAMERA_RPI_TUNING_FILE` (name built from IPA module `rpi/pisp`, `ipa_proxy.cpp:41-48`). Otherwise it searches `ipa.config_paths`, then install dirs, for `<model>.json`. No config-file key exists (`runtime_configuration.rst:141`).
- Effect: one value per CameraManager start for every camera it enumerates, and frozen until the manager restarts (Core restarts it, `C:7296-7329`). One process cannot give two cameras two custom tunings. With the env unset, each camera takes its own `<model>.json`, so mixed models work.
- Cinemate is the same (`CL:ipa_proxy.cpp:115`; cinepi-raw `core/options.cpp:232-233` setenv).

## Q3. Frame sync

**Software `rpi.sync` [C].**
- Server broadcasts, clients adjust, one-way (`control_ids_rpi.yaml:74-113`).
- Transport is UDP multicast `239.255.255.250:10000`, with `group`/`port` overridable in the tuning block (`sync.cpp:49-50, 56-57`).
- The server `sendto`s every `sync_period`=30 frames (:212-227). The client uses a non-blocking socket, SO_REUSEADDR, IP_ADD_MEMBERSHIP(INADDR_ANY) and bind (:81-104).
- No IP_MULTICAST_IF/LOOP/TTL is set, so it relies on the default route or loopback. With no network up, send or join probably fails (ENETUNREACH/ENODEV) [P]. Candidate fix: `ip route add 239.255.255.250/32 dev lo` plus multicast on `lo`. Test M3.
- Only the client adjusts. `frameDurationOffset` = nearest-frame-aligned client timestamp minus server timestamp, applied when |c| >= `min_adjustment` (50 us) (:256-274). The IPA subtracts it from min/max FrameDuration for one frame (`ipa_base.cpp:549, 1836-1837`).
- Wall clock is recovered from SOF timestamps (ClockRecovery, 2 us jitter clamp, `pisp.cpp:2236-2241`), so two processes on one host share CLOCK_REALTIME.
- Controls:
  - `SyncMode` Off/Server/Client.
  - `SyncFrames` (100-100000) sets frames until ready, server only. The algorithm default is 100 (`sync.cpp:52`); the control info default is 1000 (`ipa_base.cpp:92`).
  - `SyncReady` stays false until the shared ready time, then true for the session. Applications must discard frames until then (yaml:115-139).
  - `SyncTimer` is int64 us to the ready time, negative after it; the client omits it until its first packet (yaml:141-168; `sync.cpp:277-279`).
  - Fixed fps is required (`ipa_base.cpp:546-548`).
- Required tuning block: `{ "rpi.sync": { } }` appended to `algorithms` (as `pisp/imx477.json:1268-1272`); optional keys group, port, sync_period, ready_frame, min_adjustment (`sync.cpp:56-63`). Without it SyncMode is accepted and silently ignored (`ipa_base.cpp:1502-1504`).
- Imx585 tunings: no copy of Apertar's Pi file is on this Mac. libcamera's `pisp|vc4/data/imx585(.json|_mono.json)` have 0 `rpi.sync` and 3 `tdn` blocks. Cinemate's libcamera copies and all `cinemate/resources/tuning_files/imx585*.json` (every worktree) also have 0, so Cinemate's cam0-server/cam1-client sync is a no-op for IMX585 unless the Pi's file differs [P].
- [U] Pi file: `grep -c rpi.sync` on `/home/pi/Tuning-Files/defaults-pisp/imx585.json` and the /usr/local copy (M0).
- Two processes on one host: yes by code, and the Raspberry Pi docs describe server and client as separate rpicam-vid processes on one Pi [W].
- Accuracy: no figure in the repo. The docs say "several tens of microseconds" for the same sensor model on one Pi, "significantly larger" for mixed models [W]. Code floor: 50 us threshold plus one line (~5-6 us) [E].
- Cinemate's libcamera has the same algorithm, defaults and SyncPayload layout. It pairs a us-based ClockRecovery with a sync.cpp that lacks `/1000` (both self-consistent; `CL:sync.cpp:167` vs `L:sync.cpp:167`). Its SyncFrames range differs.
- Interplay [P]:
  - The IMX585 helper's (VMAX,HMAX) lattice search (`cam_helper_imx585.cpp:118-226`) may re-pick HMAX for a +/-us offset, giving a one-frame line-length blip.
  - Core's `fps_phase_lock` (default off) must stay off on a sync client; Cinemate suppresses it there (`cinepi_controller.hpp:111-113`).
  - Core's lock is a rate lock with a per-process datum (`C:FramePhaseLock.hpp:58, 149`), not a genlock. A shared-grid datum would be a small untested change.

## Q4. Hardware sync and the driver

- DT property `sony,sync-mode` takes `internal-leader` (default), `internal-follower` or `external` (`D:imx585.c:2566-2573`; `D2:4649-4656`). Overlay param `sync-mode=<str>` is per overlay instance (`imx585-overlay.dts:67, 127`).
- dmesg prints the menu string by enum index. `internal-follower` therefore reads "External Sync Leader Mode" and `external` reads "Follower Mode" (`D:327-337`).
- Registers at stream start (`D:2181-2196, 2277-2278`; `D2:4089-4107, 4192-4193`):

| Mode | EXTMODE 0x30ce | XXS_DRV 0x30a6 | XXS_OUTSEL 0x30a4 | XMSTA 0x3002 |
|---|---|---|---|---|
| leader | 0 | 0x00 (XHS and XVS out) | 0x0A | 0 (start) |
| internal-follower | 1 | 0x03 (XHS out, XVS in) | 0x08 | 0 |
| external | untouched | 0x0F (both in) | 0 | stays 1 (`common_regs` :363) |

- Wiring [W, not in the repo; the driver README points to Will Whang's wiki]:
  - Leader cam0 = default overlay.
  - Follower uses `sync-mode=internal-follower` (XVS only, "minor phase adjustments") or `external` (XVS+XHS, tightest lock).
  - Join XVS (and XHS) with a U.FL coax jumper; `external` also needs the board's "follower" jumper (JP3 on v1.7).
  - A shared clock is not required.
  - The wiki gives no number.
  - [U] pin and jumper names on the StarlightEye: read its schematic.
  - Use either hardware sync or `rpi.sync`, not both.
- Multi-instance safety: both refs have a non-const file-scope `supported_modes[]` (`D:794`; `D2:1064`), rewritten by `imx585_update_hmax()` (`D:1485-1506`; `D2:3271-3346`) from the caller's link frequency, lanes and Clear HDR state. It is called on every set_fmt or WDR change (`D:1514`). The HBLANK-to-HMAX conversion reads it (`D:1665`), and libcamera triggers that every frame.
- `D2:4662-4676` itself says these arrays are "process-wide ... shared by every imx585 instance".
- [C code, U effect] Safe only if both overlays use the same `link-frequency` and lane count, with no simultaneous stream starts in different Clear HDR states. Everything else is per-instance.
- `cam0`: it retargets i2c, csi, clk, the always-on fragment and vana-supply (`imx585-overlay.dts:129-135`) but not `reg_frag` (:36-41), so the 300 ms startup delay stays on `cam1_reg`. Identical in both refs.
- Impact [P]: cam0 works today (KB), and the driver waits 500 ms after reset itself (`D:58`). In dual, cam1_reg gets the delay from both overlays and cam0_reg none. Low risk.

## Q5. Bandwidth and feasibility

**Measured single-sensor facts [M].**
- BE (libcamera log, start to done), 4K HDR16 25 fps:
  - preview alone 10.9 ms (p90 12.3);
  - recording, stable 21-37 ms;
  - recording, saturated 38-44 ms, and a take loses frames once the BE reaches ~40 ms.
  - Sources: `working/drop-frames/tests-2026-11/preregistration.md:236-237, 325-326`; `findings-2026-11-03.md:10-23`.
- Memory load alone (2x `dd`, no recording): BE 10.9 -> 95 ms (p90 148), CFE interval 92 ms (over half the frames lost). SDR12 COMP1: 10.9 -> 23.7 ms, no loss (preregistration.md:325-326).
- Every lost frame is a moment the CFE had no raw buffer, 8 of 8 takes (`findings-2026-11-02.md:7-35`).
- Single-sensor losses:
  - 4K HDR16 25 fps uncompressed: 0-9% per 3-minute take. UI preview off gave 0/0; the full-preview units lost 2/108 here and 48-407 in B1.
  - 4K SDR12 uncompressed 50 fps: 12% (hardware-log.md:582-592) to 18.5% (:958).
  - 4K SDR12 uncompressed 30 fps: 24% in a 5 s take (`working/drop-frames/README.md:201`).
  - 4K HDR16 lossless: the encoder tops out at ~17 fps.
- Clean cases: 4K SDR12 lossless 30 fps (27 s) and 60 fps (2 s pre-roll); 4K HDR16 12.5 fps; 1080p HDR16 25 fps (~104 MB/s); 1080p50 (hardware-log.md:953-959, README.md:184-185).
- Storage:
  - 733-759 MB/s direct `dd` (~4.9 s, in-pSLC);
  - 556-572 buffered;
  - 525 MB/s for 60 s is the most Core has sustained;
  - 415 MB/s ran clean for 10 minutes;
  - 437 MB/s at Gen 2;
  - 818 MB/s fio burst;
  - nothing at or above 600 MB/s for longer than 5 s (hardware-log.md:69, 321, 383; dng-chain-feasibility.md §0).
- Data rates (per frame: MB/s at 25 fps):

| Mode | MB/frame | MB/s at 25 fps |
|---|---|---|
| 4K HDR16 | 16.6 | 415 |
| 4K HDR16 with Log 12 | 12.4 | 311 |
| 4K SDR12 uncompressed | 12.44 | 311 |
| 4K SDR12 lossless | 5.98 (one scene) | 150 |
| 1080p12 binned | 3.1 | 78 [E] |
| CFE raw 4K SDR (COMP1) | 8.3 | 207 |

- RP1 link: the CFE writes over a PCIe Gen 2 x4 link of about 2.0 GB/s (`research-30fps/q6-link.md` #5); the FE pixel-rate cap is 646.7 Mpix/s.

**Dual estimates [E].**
- Basis: BE busy = sum of fps x t_BE (thread-visible time, so an upper bound). DRAM uses the KB model: 195.5 MB/frame for HDR16, 87.1 MB/frame for SDR (q3-bandwidth.md; dng-chain-feasibility.md §1), against 17.07 GB/s peak and 7-12 GB/s practical. CPU from feasibility F3.
- Calibration anchor: 2 x 4K SDR12 uncompressed at 25 fps has the same BE job rate, DRAM bytes and storage as one 4K50 (622 MB/s), which dropped 12-18.5% [M]. Two pipelines relax each camera's serial-cycle budget from 20 ms to 40 ms, so dual could beat the anchor.

| Dual combo (25 fps each) | Storage MB/s | BE busy | DRAM GB/s | CPU cores of 4 | Verdict |
|---|---|---|---|---|---|
| 2x 1080p (12-bit binned or HDR16) | 156-208 | 15-30% | <1.5 | <1 | plausible; anchors clean |
| 4K SDR12 lossless + 1080p (or raw-only 2nd, no BE) | ~230 | 35-74% | ~3 | ~2 | plausible: first target |
| 2x 4K SDR12 lossless | 300 | 55-119% | 4.4 | ~3.2 (encoder alone, 25/62.9 per camera) | marginal |
| 2x 4K SDR12 uncompressed | 622 | 55-119% | 4.35 | 2.3-3.0 | likely drops |
| 4K HDR16 + a second 4K | 415 + 150-311 | >100% | >7 | >3 | likely drops |
| 2x 4K HDR16 | 830 (Log: 622) | 104-195% | 9.8 | 3.4-3.6 | infeasible |

- The BE-busy ranges for the SDR rows run from idle-level job time (10.9 ms) to the 2x`dd` level (23.7 ms).
- Raw-only configuration sets `beEnabled_ = false` (`pisp.cpp:2033, 2377-2385`). A raw-only second camera costs no BE time. A TDN-off tuning copy cuts BE bytes ~65% [E, KB q1-backend.md].

## Q6. CM5 hardware

- Rig:
  - KB says Pi 5 4 GB for 10-23..26, then "CM5 + carrier" (hardware-log.md:621, 650, 900). The carrier is never named [U]; settle with `tr -d '\0' </proc/device-tree/model`.
  - Cam0 only: `dtoverlay=imx585,cam0,link-frequency=891000000` (config.txt:42), `dtparam=i2c_csi_dsi0/1=on`, `rp1-clk-333mhz` (:65), PCIe Gen 3 (KB sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md).
  - i2c-10 = cam0 bus [M]. "11 = cam1" is only a design-note label (`working/controls/design-controls.md:1053`). Cinemate says bus numbers vary (Pi 5 6/4, CM5 by carrier; `cinemate-handbook/working/the-lens-adapter.md:21`) [U]. Settle by DT path (`i2c@88000` / `i2c@80000`).
- "Connect the JC GPIO pins" (Cinemate `docs/dual-sensors.md:48`):
  - The linked Raspberry Pi page names J6, not JC: two vertical jumpers on J6 for CM4, "fit two jumpers on J6" for CM5 (CAM1 steps). CAM0 uses `,cam0`; CAM1 is the default [W].
  - "JC" is probably a typo for J6 [P].
  - It applies only to the official IO boards; the CFexpress hat suggests a Pi-5-style carrier [U].
  - The CM5IO has two 22-pin CAM/DISP connectors; the StarlightEye has a 22-pin FPC [W].
- config.txt for two IMX585 (in `[pi5]`, which covers CM5: `BootConfigText.hpp:91, 107`):
```
camera_auto_detect=0
dtoverlay=imx585,cam0,link-frequency=720000000
dtoverlay=imx585,link-frequency=720000000
dtoverlay=rp1-clk-333mhz        ; [all], already there
; hardware sync: cam0 ",sync-mode=internal-leader" (default), cam1 ",sync-mode=internal-follower"
```
- 891 MHz is above the RP1 D-PHY 1500 Mbps/lane (CFE logs "Datarate 1782 Mbps out of range", hardware-log.md:963). 720 MHz gives 50 fps 4K SDR and 25 fps HDR (driver README:110-121). Use it for dual [P].
- BootConfigText already handles two connectors:
  - `boardPorts` gives {cam0, cam1} (:124-129).
  - Sensor and link are kept per port (:474-499, 628-634).
  - It edits lines in place and refuses two sensors on one port (:909-948, 1105-1106).
  - It does not model `sync-mode`, `2lane` or `always-on`. Unknown tokens survive only when the existing line is reused (:915), so use "Edit file" for them.

## Feasibility verdict

1. The platform allows two simultaneous IMX585 [C]: 2 CFE x 2 BE node groups, per-camera handlers, IPA, tuning and fork state. The BE hardware is shared, so there is no extra BE throughput.
2. Two processes is the right shape (Cinemate, Raspberry Pi docs). Core cannot do it yet: camera selection, subdev lookup, WDR, probe, ports and state files, media singletons [C/U].
3. Operational rule [C code, U effect]: any CameraManager (re)start rewrites HBLANK on the other sensor. Do not reconfigure one Core while the other records until M2 says it is harmless or libcamera's init is patched.
4. No sync works today. `rpi.sync` is absent from every IMX585 tuning (Apertar and Cinemate) and Core never sets SyncMode. A one-line tuning block plus Core controls gives tens of us [W]. Hardware XVS is supported by the driver but needs the wire and a pin check.
5. Driver: identical `link-frequency` and lanes on both overlays (shared mutable mode table); use 720 MHz.
6. Bandwidth: plausible are 2x 1080p and 4K lossless + low-res or raw-only second. 2x 4K SDR12 uncompressed equals the 4K50 aggregate that already drops. 2x 4K HDR16 will not fit (BE, DRAM, CPU and storage all over).
7. The decisive unknown is BE time with two cameras under memory contention. Levers: raw-only second camera, TDN-off tuning, UI preview off, `buffer=frames`.
8. Storage: at or above 600 MB/s sustained is unproven [M gap]; two writers share one exFAT.
9. Hardware: confirm the carrier, both CSI ports and I2C, and J6-type jumpers before ordering anything.
10. Mixed sensors work only with the tuning env unset (or two processes), and sync accuracy is worse [W].

## Measurements to run first

- **M0, read-only, 5 min, nothing recording.**
```
tr -d '\0' </proc/device-tree/model; grep MemTotal /proc/meminfo
v4l2-ctl --list-devices | grep -E '^(pispbe|rp1-cfe)'; ls /dev/media*
rpicam-hello --list-cameras | grep -E '^[0-9] :'
for a in /sys/class/i2c-adapter/i2c-*; do echo $a $(readlink -f $a/device); done | grep -E '88000|80000'
dmesg | grep -E 'imx585|sync-mode|DPHY'; sudo cat /sys/kernel/debug/clk/clk_sys/clk_rate
grep -c '"rpi.sync"' /usr/local/share/libcamera/ipa/rpi/pisp/imx585.json /home/pi/Tuning-Files/defaults-pisp/imx585.json
ip -4 route; ip link show lo
```
  Predictions: 2 `rp1-cfe` + 2 `pispbe`; two imx585 on `i2c@88000` and `i2c@80000`; rpi.sync count 0 and 0; `lo` without MULTICAST; clk_sys 333333333.
- **M1, test, preview only, Core stopped.** Two rpicam-vid at 25 fps, 3 min each, for (a) 2x 4K SDR12 and (b) 2x 4K HDR16. Set `LIBCAMERA_LOG_FILE=/run/apertar-media/camN.log` and `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0`; parse with `working/tools/libcam_stages.py`. Predicted per-camera BE median: (a) 11-16 ms, (b) 15-22 ms [E]. If either exceeds 20 ms with preview alone, 2x 4K recording is not viable. Then repeat with 1 and 2 `dd` loads; single-camera factors were x2.2 (SDR) and x8.7 (HDR16) [M].
- **M2, stomp test.** Camera 0 streaming `rpicam-vid --camera 0 -t 60000 --framerate 25 --mode 3840:2160:12 --nopreview --save-pts a.pts -o /dev/null`. In another shell run `rpicam-hello --list-cameras` ten times, 3 s apart. Flag intervals outside 39.5-40.5 ms in `a.pts`. Prediction: 1-3 off-nominal intervals per enumeration. None means the init writes are harmless.
- **M3, rpi.sync, two processes.** Copy imx585.json adding `{ "rpi.sync": { } }`. Run `LIBCAMERA_RPI_TUNING_FILE=<copy> LIBCAMERA_LOG_LEVELS=RPiSync:DEBUG rpicam-vid --camera 0 --sync server ...` and `--camera 1 --sync client ...` with `--save-pts`. Prediction: "Sync achieved" after ~100 frames (4 s at 25 fps); |pts offset| below ~50 us; without the block, no log lines and an offset of 0-40 ms. Repeat with the network down: expect "Send error! Network is unreachable", fixed by the loopback route.
- **M4, storage, Core stopped.** Two fio jobs (`--bs=1M --direct=1 --rate=311m --runtime=300`, two folders on the card). Prediction: holds 622 MB/s while the pSLC lasts (~100 s); the post-cache rate decides the verdict (E27T about 800 MB/s [W via KB]).
- **M5, acceptance (after Core can pick a camera and its subdev).** 3-minute takes x3 per combo in the order 2x 1080p, 4K lossless + 1080p, 2x 4K lossless, 2x 4K uncompressed. Use `buffer=frames`, the second UI preview off, and the existing `owned_by_drv` trace. Predicted loss: under 0.5%, under 1%, 2-10%, over 10% [E].
- **M6, only if XVS is wired.** Compare SensorTimestamp of both CFEs for 120 s. Prediction: a constant offset within IRQ jitter (tens of us, since all RP1 IRQs sit on CPU0). Finer alignment needs a scope or LED flash.

Housekeeping: I wrote one scratch file (`sync_apertar.h`) to the session scratchpad by mistake. No repo, branch or Pi was touched. Three public web pages were read for [W] items (Will Whang's sync wiki, Raspberry Pi compute-module and camera-software docs).