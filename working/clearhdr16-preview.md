# 16-bit Clear HDR preview: flicker and distortion (2026-11-03)

Question (Patrik): why does the 4K 16-bit Clear HDR preview flicker and show distortions when Cinemate's is calm on the
same rig, and is it fixable in Apertar?

Answer: **yes, fixable in Apertar**: every candidate cause sits in something Apertar owns (the `_clearHDR` tuning file,
UI settings or shader, a drop-in, the Tiramisioux libcamera fork). **Which cause dominates is unconfirmed**: nobody has yet
classified the symptom. Tutorial T55 does that with existing switches, then fixes the stage it finds (Obsidian
`20261103234000 CINEMATE APERTAR T55 clearhdr16-steady-preview`).

Stack: Core `31d5418` on the Pi (its line numbers equal `4b14a79` for everything cited here), UI `c153c33`, libcamera
`v0.7.1+qbcfork.20260522-7-7e9fef0b` in `/usr/local`, driver `cd548ef`, tuning `imx585_clearHDR.json` md5 `f53de0fe87cd8a44a8f8e203ddb6839d`.
Method: workflow `wf_aa954f3f-46b` (7 causes, each with an investigator, a mechanism verifier and a fix verifier; a
completeness critic; 3 more causes with verifiers: 28 agents), then a read-only Pi check by the main session.

## 1. Verdicts

| # | Cause | Verdict | Evidence | Fix, if it is the one |
| --- | --- | --- | --- | --- |
| H1 | Adaptive ISP (CE every frame unfiltered, ALSC every 12 frames) on the CPU stats | unlikely | **confirmed** mechanism: no `lo_*`/`hi_*` keys in the file, so libcamera's defaults apply (lo 0.01/0.015/500, hi 0.95/0.95/2000, `contrast.cpp:41-57@7e9fef0`); RawStats replaces the histogram (`raw_stats.cpp:292-296@7e9fef0`); CE's range is bounded, near inert at 16-bit levels | `ce_enable 0` and/or no `rpi.alsc` in `imx585_clearHDR.json` |
| H2 | HG/LG merge clamps below 65535 | real, **not a flicker** | Cinemate measured 47808-55381 at 4K, 35968 at HD; Apertar's merge defaults equal Cinemate's (`Types.hpp:201-204@4b14a79`), Apertar's own clamp **unmeasured**; computed render (255,233,255) at 55381, neutral whites end near 241 | a preview-stage highlight whitening (as Cinemate); not a gamma knee (it also renders stills and 12-bit) |
| H3 | Denoise / sharpen | unlikely | same parameters as SDR; only 16-bit-specific part: TDN buffers take the CFE format, u16 (`pisp.cpp:1717-1719@7e9fef0`) | drop `"tdn"` (`denoise.cpp:55@7e9fef0`) |
| H4 | Preview delivery late under memory load | **possible**, recording-only | measured: back end 10-11 ms idle, 20-44 ms recording, 200-260 ms queue (`drop-frames/tests-2026-11/findings-2026-11-03.md:11-22`); 16-bit ~118 MB per frame camera-side vs SDR ~33 MB | drop TDN; the fork's `QBC_RAW_STATS_ROW_STEP`; no test cap |
| H5 | Preview slot integrity | refuted | mode-independent; the UI copies into its FBO | none |
| H6 | Geometry / black level | refuted | crop and black match; the preview crop is buffer rows ~20-2178 (`pipeline_base.cpp:1390-1402@7e9fef0`) | none |
| H7 | UI aids (peaking, zebra) | **possible** | peaking on noise **unmeasured**; zebra blink refuted for today's scene (raw peak 18406, nothing near the clamp) | zebra 90 %, peaking 0.20 or off (existing settings) |
| R2a | HDMI scan-out underrun | unlikely | no `underrun` kernel line this boot (**unconfirmed** that the 2712 HVS logs one); HVS arbiter at maximum priority (`vc4_hvs.c`, rpi-6.12.y) | cut bytes (TDN) |
| R2b | Short CSI-2 frame byte-swapped into noise | refuted as the flicker | the swap has no status or `bytesused` check (`pisp.cpp:1961-1979@7e9fef0`): a real hazard, never observed; OVLF only in 3.5 % of recording seconds, LEN/UNMATCHED 0 | fork: skip the swap on short frames |
| R2c | Frame-duration pushes | refuted | phase lock off, 0 pushes; 25 fps is exact on the lattice (HMAX 550 x VMAX 5400) | keep the lock off |

## 2. Confirmed in code or on the Pi (new or corrected)

- **Cinemate's 16-bit byte-swaps too** (corrects an agent's "Cinemate never swaps"): imx585 `packing: "U"` gives
  `--mode 3840:2200:16:U` and SBGGR16 (`cinepi-raw core/rpicam_app.cpp:118-136@63a08d5`). What Cinemate lacks: the
  RawStats pass, TDN, CE, ALSC, the aids; its HDMI is a DRM plane that holds each buffer until the next one.
- **The WebUI draws its own aids** in the browser (WebGL) from the same UI settings (`WebControlPage.cpp:12962-12973@31d5418`).
  An "HDMI against WebUI" comparison needs the aids off.
- **The two zebra rules differ**, both upstream 1.6.0 code: the WebUI tests `max(r,g,b)` when the level is ≥ 0.95
  (`WebControlPage.cpp:13136-13140`), the UI shader tests Rec.601 luma only (`PreviewWindowRenderer.cpp:896@c153c33`).
  `lessons/upstream-issues.md` #45.
- **`set_tuning_file`** (`CameraController.cpp:11374-11442`): refused while recording; stop + start; saved. A picked file
  is used as given in **every** mode (`:7222`), so SDR keeps it until `set_tuning_file ""`. An unchanged path returns
  early without a reload. Every start makes a new CameraManager (`:7247`), so any mode switch re-reads an edited file.
- **A log preview profile is not a CE-only test**: `makeProresIspTuning` sets `ce_enable 0` (`ProresIspProfile.cpp:197`)
  but also replaces the gamma curve and the CCM.
- **`imx585_clearHDR.json`** (134888 bytes): 13 blocks. `rpi.alsc` has no tables (`omega 1.3`, `n_iter 100`,
  `luminance_strength 0.8`), so it is adaptive only; `rpi.denoise` has `tdn` in all three modes.
- **Default search path**: `~/Tuning-Files/defaults-pisp`, `~/Tuning-Files/defaults`, `/usr/local/share/libcamera/ipa/rpi/pisp`,
  `/usr/share/…` (`DefaultTuningSelection.hpp:65-76@31d5418`). `~/Tuning-Files` itself is not searched.
- **12-bit Clear HDR also runs RawStats on the CPU** (CCMP linearisation in the stats), without the byte swap
  (`pisp.cpp:1627-1660@7e9fef0`).

## 3. Pi state, 2026-11-03 23:30 (read-only)

- Rebooted 22:28 (journal boot 0). The `/run` test drop-in `zz-preview-fps.conf` (`APERTAR_UI_PREVIEW_RECORDING_FPS=12`)
  is gone; UI drop-ins: `cursor.conf` only. Core: `/etc` drop-ins `apertar-ui-start-gate`, `capture-priority`,
  `libcamera-log`; env `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR`. **Every take before the reboot ran with the 12 fps HDMI cap.**
- `/api/state`: SDR 1920x1080, 25 fps (Patrik switched modes 23:17-23:29); phase lock off, 0 pushes; `fps_speed_ramp`
  true (acts only on an fps change during a take); ladder off; `tuning_file ""`; HDR 4095/0/5/1; peaking on 0.12 Green;
  zebra on 0.95; external monitor "Assist Feed", info overlay on.
- Displays: HDMI-A-1 1920x1080, HDMI-A-2 disconnected; `hdmi_external_only=true`. `config.txt`:
  `dtoverlay=imx585,cam0,link-frequency=891000000`.
- `pi` is in `systemd-journal` now: `journalctl` works without sudo.
- Suspected UI dmabuf import leak (an agent's code reading: ~24 fds per configure): **not seen**. The UI held 81 fds,
  48 of them dmabuf, after 15 camera configures this boot.

## 4. Open

- The symptom class: T55 §3 (Clean Feed, WebUI, idle against take, 12- against 16-bit, 4K against 1080p).
- Whether a tuning without `tdn` also lowers recording drops (the lever in `dng-chain-feasibility.md:53`, unmeasured).
- Apertar's own clamp level (H2); the 16-bit preview's noise at the texel level (H7 peaking).
- Raw workflow output: session scratchpad `wf.json` (not kept in the KB).
