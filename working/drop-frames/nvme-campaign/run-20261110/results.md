# Long-take campaign results

Pi: Raspberry Pi Compute Module 5 Lite Rev 1.0 | Core e298d4a cdng: log a frame-index jump, and count them in the recording stats | drive: None | started 2026-11-10 03:32:04

Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: probable / unconfirmed, never confirmed.
Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.

| mode | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | ab_clean | 60.0 | 0 |  |  | 56.75 | 46.85 (46.85) | 45.3 | 2556 | 2.8 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | stopped_by_signal | 50.5 | 0 |  |  | 56.75 | 48.85 (48.85) | 41.7 | 2575 | 5.1 |  | stopped by SIGTERM after 51 s: not a result |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | pass_3min | 180.1 | 0 |  |  | 57.3 | 64.85 (64.85) | 60.5 | 2496 | 13.5 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | drop | 136.1 | 1 | 135.8 | capture-gap:1 | 58.4 | 68.85 (68.85) | 80.5 | 2355 | 19.9 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | drop | 153.2 | 1 | 152.8 | capture-gap:1 | 58.4 | 70.85 (70.85) | 75.3 | 2316 | 27.0 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | off | off | off | on | on | 27.0 | pass_3min | 180.2 | 0 |  |  | 57.85 | 71.85 (72.85) | 75.9 | 2397 | 35.1 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 27.0 | void | 300.3 | 0 |  |  | 57.85 | 73.85 (73.85) | 61.0 | 2203 | 48.6 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 27.0 | void | 300.3 | 0 |  |  | 58.95 | 75.85 (75.85) | 57.1 | 2297 | 62.1 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | pass_capped_20s | 20.0 | 0 |  |  | 52.35 | 36.85 (36.85) | 41.3 | 3022 | 63.0 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 27.0 | pass_5min | 300.2 | 0 |  |  | 57.85 | 60.85 (61.85) | 38.8 | 2927 | 75.6 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | pass_3min | 180.1 | 0 |  |  | 57.85 | 67.85 (67.85) | 39.4 | 2881 | 84.0 |  |  |
| 4kHDR16 | unc | on | off | off | on | on | 28.0 | drop | 5.0 | 1 | 4.8 | capture-gap:1 | 58.4 | 55.85 (55.85) | 69.9 | 2902 | 84.2 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | on | off | off | on | on | 28.0 | drop | 5.0 | 2 | 4.8 | capture-gap:1 | 57.3 | 53.85 (53.85) | 69.9 | 2890 | 84.3 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | pass_3min | 180.1 | 0 |  |  | 57.85 | 69.85 (69.85) | 57.5 | 2978 | 92.7 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | buffer_full | 138.6 | 0 |  | buffer_full:1 | 55.1 | 69.85 (71.85) | 43.8 | 2949 | 96.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 80/12 frames, stopped after 139 s) |
| 4kHDR16 | unc | off | off | off | on | off | 28.0 | pass_3min | 180.2 | 0 |  |  | 57.3 | 72.85 (73.85) | 67.7 | 2824 | 93.8 |  |  |
| 4kHDR16 | unc | off | off | off | on | off | 28.0 | pass_3min | 180.2 | 0 |  |  | 57.85 | 72.85 (73.85) | 74.6 | 2835 | 95.8 |  |  |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | pass_3min | 180.2 | 0 |  |  | 57.3 | 73.85 (73.85) | 81.8 | 2813 | 97.1 |  |  |
| 4kHDR16 | unc | on | off | off | on | on | 30.0 | drop | 2.0 | 2 | 1.7 | capture-gap:1 | 54.0 | 64.85 (65.85) | 72.5 | 2675 | 89.1 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | off | on | off | on | on | 25.0 | drop | 4.0 | 1 | 3.7 | capture-gap:1 | 54.0 | 57.85 (57.85) | 43.4 | 2863 | 89.2 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); TDN on adds back-end load (row 7); WebUI client adds preview load |
| 4kHDR16 | lossless | on | off | off | on | on | 25.0 | drop | 5.0 | 2 | 4.8 | capture-gap:1 | 57.3 | 54.85 (54.85) | 88.7 | 2753 | 89.4 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | lossless | on | off | off | on | on | 25.0 | drop | 5.0 | 2 | 4.7 | capture-gap:1 | 57.3 | 52.85 (52.85) | 91.9 | 2865 | 89.5 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | unc | off | off | off | on | on | 28.0 | drop | 159.7 | 4 | 159.2 | capture-gap:1 | 57.3 | 67.85 (69.85) | 75.2 | 2504 | 96.8 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kSDR12 | unc | off | off | off | on | on | 42.0 | record_start_failed | 0.0 | 4 | 0.0 |  |  |  (55.85) |  |  |  |  | The previous take's writers are still blocked on the removed medium (1). Try again in a moment. |
| 4kHDR16 | unc | off | off | off | on | on | 27.0 | record_start_failed | 0.0 | 4 | 0.0 |  |  |  (62.85) |  |  |  |  | The previous take's writers are still blocked on the removed medium (1). Try again in a moment. |
| 4kHDR16 | lossless | on | off | off | on | on | 26.0 | drop | 6.0 | 1 | 5.7 | capture-gap:1 | 56.75 | 33.85 (33.85) | 84.2 | 2908 | 83.5 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |
| 4kHDR16 | lossless | on | off | off | on | on | 26.0 | drop | 10.0 | 4 | 9.8 | capture-gap:1 | 55.65 | 34.85 (34.85) | 89.4 | 2753 | 83.8 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); WebUI client adds preview load |

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
| 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | pass_3min | 3.0 |
| 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf200 | 28.0 | pass_capped_20s | 0.3 |
| 4kHDR16_unc_log0_tdn0_lock0_trim1_web0_fpf5000 | 28.0 | pass_3min | 3.0 |
