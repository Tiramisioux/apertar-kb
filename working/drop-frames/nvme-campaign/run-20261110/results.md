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

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
| 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 27.0 | pass_3min | 3.0 |
