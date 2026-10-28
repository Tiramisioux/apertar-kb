# Research: 16-bit Clear HDR 4K at 30 fps (cloud session, 2026-10-26)

Running checkpoint so a lost session does not lose the work. Brief: `../handoff-30fps-clearhdr16.md`.

## Sources used (read-only, in the cloud container)

| Tree | Commit |
| --- | --- |
| libcamera the Pi runs (base) | will127534/libcamera `qbc-pisp-handler` `7e9fef0` |
| libcamera ours | Tiramisioux/libcamera `apertar` `6b0b49f` (= 7e9fef0 + 889567a + 6b0b49f) |
| libpisp | raspberrypi/libpisp `v1.3.0` (`9ba67e6`), the version libcamera-qbc's wrap pins; the Pi's installed copy is unconfirmed |
| kernel | raspberrypi/linux `rpi-6.12.y` `5bd564a` (sparse: rp1_cfe, pisp_be, dma-heaps, rp1, overlays); the Pi runs 6.12.75 |
| IMX585 driver | imx585-v4l2-driver `apertar` `e5b74d3` (+ crop commit `98b9862`); Cinemate's `cinemate-modes` `18c1eb2` |
| Cinemate | cinemate `d6cc93e`, cinemate-handbook `c99ff77`, cinepi-raw `63a08d5`, libcamera (cinemate) `bfe0b76` |
| Apertar-Core | `f60e301` only (the Pi's `d9f00d4` is not available here) |

## Files

- `q1-backend.md` … `q7-cinemate.md`: one reader report per brief §5 question, each with an appended adversarial `## Verification`.
- `critic.md`: contradictions, hypotheses, gaps, draft ranking.
- `../research-30fps-answer.md`: the answer and the ranked experiment list (written last).

## Checkpoints

- 22:05 Workflow `wf_0ca5b6d9-e39` launched (7 readers → 7 verifiers → critic). First lead from the scouting: Cinemate models this mode's
  ceiling on the RP1 clock (`cinemate/docs/sensors.md`: 21.99 fps stock, 30.00 with `dtoverlay=rp1-overclock`;
  `cinemate/src/module/rp1_regime.py`: 380 vs 580 MPix/s, "the PiSP CSI2-to-ISP-FE bottleneck"). Whether the Apertar Pi runs the overlay is
  not recorded anywhere in the KB.
- 22:10 The Apertar Pi already runs an RP1 clock overlay: `dtoverlay=rp1-clk-333mhz` (config.txt line 65,
  `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:38`), and its libcamera logs `RP1_PLL_SYS request=333333333 Hz ... PiSP pixel-rate cap =
  646.667 Mpix/s` (`working/clearhdr-design.md:88`, `working/handoff-clearhdr-buffering.md:29`). 30 fps timing confirmed from dmesg:
  `3840x2200 -> VMAX=4500 HMAX=550` = 74.25 MHz / (4500 x 550) = 30.0 fps at link 891 MHz (`working/clearhdr-design.md:120`). So Cinemate's
  stock-RP1 ceiling (21.99 fps) does not apply; the RP1-clock hypothesis is downgraded unless the overlay also fails to raise the clock that
  the CFE's DMA path uses. NVMe sits on the BCM2712's own PCIe x1 at gen 3 (`dtparam=pciex1_gen=3`, `working/clearhdr-fps-request.md:19`),
  not behind the RP1.
- 22:20 q1 (back end) and q2 (pipelining) reports landed (committed `fd6d477`). Two leads: the BE runs TDN on a full-frame **16-bit
  uncompressed** reference, read and written every frame (37.6 MB/frame, ~1.1 GB/s, preview only); and the hardware BE-done time is
  already in the RPI debug log (`timestamp:` of "Stream ISP Input buffer complete"), which `libcam_stages.py` ignores.
- 22:40 Container restart killed the workflow; readers 3-7 were lost mid-run. 22:43 relaunched as three parallel parts
  (`research-30fps-part.js` in the session scratchpad; the container's 4 CPUs cap each workflow at 2 agents):
  `wf_3a0c5cdc-8af` q3+q4, `wf_3e99fa46-c5e` q5+q6, `wf_cc642a95-791` q7 + verifiers of q1/q2. Critic runs after all three.
- 23:57 All seven reports verified, critic written (`critic.md`), answer written: `../research-30fps-answer.md`. New tool
  `../tools/be_cycle.py` (per-frame S1-S4 split from an RPI:0 log; tested on a synthetic log).
