# Evening 4, supervised part: results and the measures behind them (2026-11-04, 20:10-21:00)

Mode in every take: 4K Clear HDR 16-bit, uncompressed cDNG to the NVMe (exFAT), WebUI open (User's requirement), the
preview on the TDN-off tuning copy (F) unless noted. Rules and arms: `preregistration.md`, "Tier 2, evening 4" and its
amendments. Raw data: the lead's scratchpad until archived at the end of the night. Claims are labelled.

## Results

| Take | FE Config depth | fps | Ran | Lost (Core) | Late Config buffers: > 2T / > 4T, worst | Replay K2 / K3 / K4 | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| d1 | 4 | 28 | 3 min | 0 / 5,056 | 0 / 0, 70 ms | 0 / 0 / 0 | void (tuning check) |
| d2 | 2 | 28 | 44 s | 2 | 1 / 0, 72 ms | 1 / 0 / 0 | void (stopped by hand) |
| d3 | 2 | 28 | 77 s | 1 | 2 / 0, 97 ms | **1** / 0 / 0 | scored |
| d4 | 4 | 28 | 3 min | **0 / 5,055** | **6** / 0, 138 ms | **4 / 1 / 0** | scored |
| d1r | 4 | 28, then 30 from s 60 | 121 s, stopped on drop | 3 | 9 / 0, 91 ms | 5 / 0 / 0 | void (rate changed mid-take) |
| t1 | 4 | 30 | 119 s, stopped on drop | 3 | 3 / 0, 76 ms | 2 / 0 / 0 | scored |
| t2 | 2 | 30 | 4 s, stopped on drop | 1 | too short to read | - | scored |

T = one frame period (35.7 ms at 28 fps, 33.3 ms at 30). "Replay" = how many frames the take's own Config timings would
have lost at depth 2, 3 and 4 (`be_overlap.py` section 7).

Back end, recording window (`be_overlap.py` sections 1 and 4):

| Take | fps | BE job (S2) median / p90 | Jobs that had to queue | Worst 20 s | Core's write queue peak |
| --- | --- | --- | --- | --- | --- |
| d3 | 28 | 7.1 / 12.0 ms | 0.02 | 0.04 | - |
| d4 | 28 | 7.5 / 12.5 ms | 0.03 | 0.07 | 2 / 12 |
| d1r | 28 -> 30 | 9.8 / 21.4 ms | 0.16 | 0.33 (s 105-125) | 5 / 12 |
| t1 | 30 | 11.9 / 24.7 ms | 0.27 | 0.39 (s 105-125) | 11 / 12 |

NVMe ran 44-66 C across the takes (logged every second, not gated). The two losses with a reading came at 48.9 and 51.9 C.

## What it shows

1. **At 28 fps the remaining single-frame losses are the FE Config queue running dry, and depth 4 removes them**
   (probable, n = 1 + 1). In d3 (depth 2) the frame was lost exactly where a Config buffer came back late and the depth-2
   replay predicts it. d4 (depth 4) had more late buffers (6, worst 138 ms), which would have cost 4 frames at depth 2,
   and lost none. **By the registered rule the 28 fps A/B is Inconclusive**: it needs two clean depth-4 takes and has one
   (d1 and d1r were voided by their checks).
2. **30 fps hits a second limit that the Config queue does not explain** (probable). With depth 4, t1 lost 3 frames in
   about 2 minutes. No Config buffer was later than 4T and no start-of-frame gap was seen, yet the back end slowed: its
   job time rose (median 11.9 against 7.5 ms, p90 24.7 against 12.5), 27 % of its jobs had to queue (3 % at 28 fps),
   and Core's write queue nearly filled (11 of 12). The cause is unconfirmed (memory bandwidth is the first candidate).
   **30 fps is ruled out** with the current measures (User's stop rule).
3. Depth 2 at 30 fps (t2) lost a frame after 4 s, consistent with point 1 but too short to read.
4. Temperature: no relation is visible yet (n too small); the overnight 10-min takes will give the first real spread.

## The measures in place (what makes 4K HDR16 uncompressed run clean at 28 fps here)

1. **TDN off in the preview** (measured on evening 3, the largest effect): the tuning copy
   `/home/pi/Tuning-Files/imx585_clearHDR_notdn.json` (made with `tools/tdn_strip.py`), selected with
   `set_tuning_file path=...`. The ISP back end's job drops from ~37 ms to ~6-8 ms a frame. Spatial denoise stays on. The
   DNGs are raw sensor data and do not change; the preview noise looked acceptable to User (20:26).
2. **FE Config queue depth 4** (tonight, point 1): a copy of libcamera's PiSP pipeline YAML with only
   `"num_cfe_config_queue": 4` changed (`/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml`), given to Core through
   `LIBCAMERA_RPI_CONFIG_FILE`. Tonight it is set by a temporary `/run` systemd drop-in from the test helper and goes away
   at reboot. Making it permanent would need an `/etc` drop-in (not done; User's call). The installed YAML is untouched.
3. Unchanged from earlier evenings: Core's DNG writer with `APERTAR_DNG_DONTNEED=sync`, writeback on, the RAM buffer
   (12 slots), the storage pre-roll at start.

## Not shown yet

- Any 10-minute take or the five-take B6 with these measures (overnight, at 28 fps with depth 4, per the 20:49 amendment).
- A second clean depth-4 take at 28 fps.
- Whether the debug log and trace events tonight's takes run with cost margin themselves (the unlogged take overnight).
