# Long-take campaign results

Pi: Raspberry Pi Compute Module 5 Lite Rev 1.0 | Core f4a1393 camera: phase lock pins {d, d+1} so the line length stays fixed | drive: KINGSTON SKC3000S512G 476.9G | started 2026-11-06 22:07:50

Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: probable / unconfirmed, never confirmed.
Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.

| bits | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 | unc | off | off | off | on | off | 30.0 | drop | 2.0 | 2 | 1.3 | capture-gap:1 | 58.95 | 28.85 (28.85) | 65.5 | 964 | 0.3 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 29.0 | drop | 3.5 | 3 | 2.7 | capture-gap:1 | 60.05 | 28.85 (29.85) | 56.6 | 972 | 0.5 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 28.0 | drop | 4.5 | 2 | 3.9 | capture-gap:1 | 59.5 | 29.85 (30.85) | 62.2 | 838 | 0.5 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 27.0 | drop | 7.5 | 2 | 7.0 | capture-gap:1 | 59.5 | 30.85 (31.85) | 68.3 | 843 | 0.8 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 26.0 | drop | 23.5 | 1 | 23.0 | capture-gap:1 | 60.05 | 34.85 (35.85) | 57.1 | 834 | 2.2 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 25.0 | drop | 73.6 | 1 | 73.1 | capture-gap:1 | 61.15 | 43.85 (43.85) | 58.6 | 776 | 6.1 |  | capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | unc | off | off | off | on | off | 25 | exhausted |  |  |  |  |  |  () |  |  |  |  |  |
| 16 | lossless | off | off | off | on | off | 30.0 | drop | 1.5 | 3 | 0.9 | capture-gap:1 | 61.7 | 38.85 (39.85) | 95.5 | 659 | 0.2 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | lossless | off | off | off | on | off | 29.0 | drop | 1.5 | 3 | 0.8 | capture-gap:1 | 61.7 | 38.85 (38.85) | 94.9 | 451 | 0.2 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4) |
| 16 | lossless | off | off | off | on | off | 28.0 | drop | 2.0 | 6 | 1.4 | capture-gap:3 | 62.8 | 37.85 (37.85) | 97.1 | 305 | 0.3 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); RAM available low (305 MB) |
| 16 | lossless | off | off | off | on | off | 27.0 | drop | 2.0 | 4 | 1.3 | capture-gap:1 | 61.7 | 36.85 (36.85) | 92.1 | 387 | 0.3 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); RAM available low (387 MB) |
| 16 | lossless | off | off | off | on | off | 26.0 | drop | 2.0 | 4 | 1.5 | capture-gap:1 | 62.8 | 36.85 (36.85) | 97.1 | 311 | 0.3 |  | probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2); capture gap = CFE had no free raw buffer; ISP back end behind (memory bandwidth, recipe section 4); RAM available low (311 MB) |

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
