# Long-take campaign results

Pi: Raspberry Pi Compute Module 5 Lite Rev 1.0 | Core f4a1393 camera: phase lock pins {d, d+1} so the line length stays fixed | drive: None | started 2026-11-07 03:29:24

Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: probable / unconfirmed, never confirmed.
Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.

| mode | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4kSDR12 | unc | off | off | off | on | off | 60.0 | buffer_full | 17.0 | 0 |  | buffer_full:1 | 53.45 |  () | 5.1 | 1704 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 146/12 frames, stopped after 17 s) |
| 4kSDR12 | unc | off | off | off | on | off | 59.0 | buffer_full | 16.5 | 0 |  | buffer_full:1 | 52.9 |  () | 39.3 | 1799 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 145/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 58.0 | buffer_full | 16.5 | 0 |  | buffer_full:1 | 53.45 |  () | 4.6 | 1610 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 139/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 56.0 | buffer_full | 15.0 | 0 |  | buffer_full:1 | 53.45 |  () | 7.0 | 1501 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 127/12 frames, stopped after 15 s) |
| 4kSDR12 | unc | off | off | off | on | off | 55.0 | buffer_full | 15.5 | 0 |  | buffer_full:1 | 52.9 |  () | 7.4 | 1629 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 133/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 54.0 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 52.9 |  () | 13.1 | 1570 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 117/12 frames, stopped after 13 s) |
| 4kSDR12 | unc | off | off | off | on | off | 52.0 | buffer_full | 15.0 | 0 |  | buffer_full:1 | 52.9 |  () | 21.4 | 1626 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 120/12 frames, stopped after 15 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25.0 | buffer_full | 19.0 | 0 |  | buffer_full:1 | 50.7 |  () | 11.8 | 1487 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 117/12 frames, stopped after 19 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25.0 | buffer_full | 19.0 | 0 |  | buffer_full:1 | 51.25 |  () | 13.7 | 1394 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 110/12 frames, stopped after 19 s) |
| 4kSDR12 | unc | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | data rate at 25 fps (311 MB/s) is at or above 311 MB/s, where the drive already filled its RAM buffer |
| 4kSDR10 | unc | off | off | off | on | off | 29.0 | buffer_full | 17.0 | 0 |  | buffer_full:1 | 49.6 |  () | 5.6 | 1307 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 112/12 frames, stopped after 17 s) |
| 4kSDR10 | unc | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | ruled out in theory: in that take the drive wrote the equivalent of 14.2 fps, well below the 25 fps floor, so no take of this config can survive 5 min |
| 2kSDR12 | unc | off | off | off | on | off | 60.0 | buffer_full | 43.0 | 0 |  | buffer_full:1 | 51.25 |  () | 11.7 | 1629 | 0.8 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 544/12 frames, stopped after 43 s) |
| 2kSDR12 | unc | off | off | off | on | off | 47.0 | buffer_full | 74.0 | 0 |  | buffer_full:1 | 52.35 |  () | 9.1 | 1560 | 1.4 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 512/12 frames, stopped after 74 s) |
| 2kSDR12 | unc | off | off | off | on | off | 44.0 | buffer_full | 46.0 | 0 |  | buffer_full:1 | 51.8 |  () | 11.7 | 1325 | 0.7 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 352/12 frames, stopped after 46 s) |
| 2kSDR12 | unc | off | off | off | on | off | 38.0 | buffer_full | 73.5 | 0 |  | buffer_full:1 | 53.45 |  () | 17.0 | 1383 | 1.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 410/12 frames, stopped after 74 s) |
| 2kSDR12 | unc | off | off | off | on | off | 35.0 | pass_5min | 300.1 | 0 |  |  | 53.45 |  () | 18.9 | 1422 | 6.6 |  |  |
| 2kSDR10 | unc | off | off | off | on | off | 44.0 | pass_5min | 300.1 | 0 |  |  | 55.65 |  () | 22.8 | 2032 | 6.9 |  |  |
| 2kHDR16 | unc | off | off | off | on | off | 27.0 | pass_5min | 300.1 | 0 |  |  | 54.0 |  () | 15.8 | 1837 | 6.8 |  |  |
| 2kHDR12 | unc | off | off | off | on | off | 30.0 | pass_5min | 300.1 | 0 |  |  | 54.0 |  () | 16.3 | 1754 | 5.7 |  |  |
| 4kHDR12 | unc | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | data rate at 25 fps (311 MB/s) is at or above 118 MB/s, where the drive already filled its RAM buffer |
| 4kSDR12 | lossless | off | off | off | on | off | 27.0 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 52.9 |  () | 26.3 | 1530 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 87/24 frames, stopped after 13 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kSDR12 | lossless | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | ruled out in theory: in that take the drive wrote the equivalent of 15.6 fps, well below the 25 fps floor, so no take of this config can survive 5 min |
| 4kSDR12 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | data rate at 25 fps (311 MB/s) is at or above 118 MB/s, where the drive already filled its RAM buffer |
| 4kSDR12 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): web |
| 4kSDR12 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): lock |
| 4kSDR12 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): tdn |
| 4kSDR12 | unc | on | off | off | on | off | 27.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 33.0 | buffer_full | 10.5 | 0 |  | buffer_full:1 | 54.0 |  () | 35.3 | 1398 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 78/24 frames, stopped after 10 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kSDR10 | lossless | off | off | off | on | off | 25.0 | pass_5min | 300.2 | 0 |  |  | 54.55 |  () | 46.9 | 1673 | 6.5 |  |  |
| 4kSDR10 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | data rate at 25 fps (259 MB/s) is at or above 118 MB/s, where the drive already filled its RAM buffer |
| 4kSDR10 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): web |
| 4kSDR10 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): lock |
| 4kSDR10 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): tdn |
| 4kSDR10 | unc | on | off | off | on | off | 33.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  |  |
| 2kSDR12 | lossless | off | off | off | on | off | 60.0 | pass_5min | 300.2 | 0 |  |  | 56.75 |  () | 44.9 | 2389 | 4.7 |  |  |
| 2kSDR12 | unc | off | off | off | off | off | 37.0 | pass_5min | 300.1 | 0 |  |  | 54.55 |  () | 20.6 | 2500 | 7.0 |  |  |
| 2kSDR12 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): web |
| 2kSDR12 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): lock |
| 2kSDR12 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | cannot affect a storage limit (baseline stopped by): tdn |
| 2kSDR12 | unc | on | off | off | on | off | 60.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  |  |
| 2kSDR10 | lossless | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 19.5 | 0 |  | buffer_full:1 | 52.35 |  () | 23.8 | 1483 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 112/12 frames, stopped after 20 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 11.5 | 0 |  | buffer_full:1 | 51.8 |  () | 11.7 | 1685 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 81/12 frames, stopped after 12 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 16.0 | 0 |  | buffer_full:1 | 51.25 |  () | 14.4 | 1566 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 107/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 18.5 | 0 |  | buffer_full:1 | 51.8 |  () | 7.5 | 1418 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 107/24 frames, stopped after 18 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 18.0 | 0 |  | buffer_full:1 | 50.15 |  () | 7.3 | 1485 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 99/48 frames, stopped after 18 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 16.0 | 0 |  | buffer_full:1 | 50.7 |  () | 13.7 | 1708 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 87/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 15.5 | 0 |  | buffer_full:1 | 51.8 |  () | 18.3 | 1298 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 89/12 frames, stopped after 16 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 51.25 |  () | 13.6 | 1346 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 69/12 frames, stopped after 11 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 12.0 | 0 |  | buffer_full:1 | 49.6 |  () | 6.5 | 1352 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 71/12 frames, stopped after 12 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 12.5 | 0 |  | buffer_full:1 | 51.25 |  () | 9.0 | 1466 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 86/12 frames, stopped after 12 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 13.5 | 0 |  | buffer_full:1 | 50.15 |  () | 6.5 | 1328 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 84/12 frames, stopped after 14 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 14.5 | 0 |  | buffer_full:1 | 49.6 |  () | 24.4 | 1455 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 87/24 frames, stopped after 14 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 49.05 |  () | 10.5 | 1332 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 82/48 frames, stopped after 13 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 12.5 | 0 |  | buffer_full:1 | 51.8 |  () | 6.6 | 1312 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 82/12 frames, stopped after 12 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 51.25 |  () | 8.3 | 1258 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 63/12 frames, stopped after 9 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 52.9 |  () | 16.8 | 1140 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 57/12 frames, stopped after 9 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 10.0 | 0 |  | buffer_full:1 | 49.05 |  () | 15.3 | 1235 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 56/12 frames, stopped after 10 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 10.0 | 0 |  | buffer_full:1 | 50.7 |  () | 8.4 | 1109 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 56/12 frames, stopped after 10 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 10.0 | 0 |  | buffer_full:1 | 51.25 |  () | 5.9 | 1271 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 67/12 frames, stopped after 10 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 10.0 | 0 |  | buffer_full:1 | 49.6 |  () | 16.0 | 1209 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 61/24 frames, stopped after 10 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 49.05 |  () | 8.3 | 1258 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 59/48 frames, stopped after 9 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 12.5 | 0 |  | buffer_full:1 | 50.15 |  () | 14.4 | 1123 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 60/12 frames, stopped after 12 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 7.0 | 0 |  | buffer_full:1 | 49.6 |  () | 6.4 | 1060 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 41/12 frames, stopped after 7 s) |
| 4kSDR12 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 50.7 |  () | 4.5 | 1166 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 69/12 frames, stopped after 11 s) |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 47.0 | 1326 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.2 |  () | 46.0 | 1664 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 46.2 | 1710 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 49.5 | 1686 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.2 |  () | 46.2 | 1802 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 48.5 | 1842 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 55.65 |  () | 46.0 | 1615 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 45.9 | 1828 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 54.55 |  () | 45.7 | 1951 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 59.5 |  () | 50.5 | 1755 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 52.0 | 1931 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 47.7 | 1996 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 47.5 | 1911 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 48.5 | 1956 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.85 |  () | 49.0 | 1883 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.85 |  () | 46.4 | 1959 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 48.7 | 1975 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 55.65 |  () | 44.7 | 1909 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.3 |  () | 49.2 | 1861 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 57.85 |  () | 46.2 | 1780 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 58.4 |  () | 49.0 | 1834 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 49.4 | 1934 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 58.95 |  () | 47.5 | 1831 | 2.7 |  |  |
| 4kSDR10 | lossless | off | off | off | on | off | 26 | ab_clean | 120.1 | 0 |  |  | 56.75 |  () | 48.0 | 1860 | 2.7 |  |  |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.5 | 0 |  | buffer_full:1 | 52.35 |  () | 15.9 | 1243 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 79/12 frames, stopped after 14 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 52.35 |  () | 9.8 | 1293 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 75/12 frames, stopped after 13 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 10.5 | 0 |  | buffer_full:1 | 52.9 |  () | 13.0 | 1177 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 62/12 frames, stopped after 10 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.5 | 0 |  | buffer_full:1 | 51.8 |  () | 14.0 | 1219 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 76/24 frames, stopped after 14 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 9.5 | 0 |  | buffer_full:1 | 50.7 |  () | 14.3 | 1150 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 54/48 frames, stopped after 10 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 51.25 |  () | 17.2 | 1075 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 50/12 frames, stopped after 9 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 51.25 |  () | 17.5 | 1170 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 52/12 frames, stopped after 9 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 10.0 | 0 |  | buffer_full:1 | 51.8 |  () | 11.6 | 1491 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 54/12 frames, stopped after 10 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 50.7 |  () | 15.6 | 1185 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 64/12 frames, stopped after 11 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 8.5 | 0 |  | buffer_full:1 | 49.05 |  () | 16.0 | 1161 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 49/12 frames, stopped after 8 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 9.0 | 0 |  | buffer_full:1 | 49.6 |  () | 19.8 | 1121 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 49/12 frames, stopped after 9 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 50.7 |  () | 12.7 | 1366 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 75/24 frames, stopped after 13 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.5 | 0 |  | buffer_full:1 | 49.6 |  () | 24.1 | 1264 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 80/48 frames, stopped after 14 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 13.0 | 0 |  | buffer_full:1 | 49.6 |  () | 21.7 | 1213 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 76/12 frames, stopped after 13 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 49.05 |  () | 10.3 | 1263 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 65/12 frames, stopped after 11 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 50.15 |  () | 16.2 | 1316 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 65/12 frames, stopped after 11 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 49.6 |  () | 16.7 | 1227 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 65/12 frames, stopped after 11 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 8.5 | 0 |  | buffer_full:1 | 49.05 |  () | 11.5 | 1120 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 51/12 frames, stopped after 8 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 12.5 | 0 |  | buffer_full:1 | 47.95 |  () | 21.4 | 1388 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 77/12 frames, stopped after 12 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.0 | 0 |  | buffer_full:1 | 49.6 |  () | 10.7 | 1273 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 66/24 frames, stopped after 11 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.5 | 0 |  | buffer_full:1 | 49.05 |  () | 13.6 | 1182 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 66/48 frames, stopped after 12 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 10.5 | 0 |  | buffer_full:1 | 50.15 |  () | 18.4 | 1253 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 63/12 frames, stopped after 10 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 11.5 | 0 |  | buffer_full:1 | 49.05 |  () | 16.8 | 1211 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 65/12 frames, stopped after 12 s) |
| 4kSDR10 | unc | off | off | off | on | off | 25 | buffer_full | 10.5 | 0 |  | buffer_full:1 | 50.15 |  () | 10.1 | 1295 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 62/12 frames, stopped after 10 s) |
| 4kSDR12 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,trim did not help on its own |
| 4kSDR12 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,web did not help on its own |
| 4kSDR12 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock did not help on its own |
| 4kSDR12 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,tdn did not help on its own |
| 4kSDR12 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log did not help on its own |
| 4kSDR12 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: trim,web did not help on its own |
| 4kSDR12 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim did not help on its own |
| 4kSDR12 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 4kSDR12 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim did not help on its own |
| 4kSDR12 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 4kSDR12 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 4kSDR12 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim did not help on its own |
| 4kSDR12 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 4kSDR12 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 4kSDR12 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 4kSDR12 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,trim,web did not help on its own |
| 4kSDR12 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,trim did not help on its own |
| 4kSDR12 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,web did not help on its own |
| 4kSDR12 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,tdn,trim did not help on its own |
| 4kSDR12 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,tdn,web did not help on its own |
| 4kSDR12 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,tdn did not help on its own |
| 4kSDR12 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,trim did not help on its own |
| 4kSDR12 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,web did not help on its own |
| 4kSDR12 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log did not help on its own |
| 4kSDR12 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,tdn did not help on its own |
| 4kSDR12 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim,web did not help on its own |
| 4kSDR12 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim,web did not help on its own |
| 4kSDR12 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim did not help on its own |
| 4kSDR12 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 4kSDR12 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim,web did not help on its own |
| 4kSDR12 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim did not help on its own |
| 4kSDR12 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 4kSDR12 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim did not help on its own |
| 4kSDR12 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 4kSDR12 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 4kSDR12 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,trim,web did not help on its own |
| 4kSDR12 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,tdn,trim,web did not help on its own |
| 4kSDR12 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,tdn,trim did not help on its own |
| 4kSDR12 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,tdn,web did not help on its own |
| 4kSDR12 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,trim,web did not help on its own |
| 4kSDR12 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,trim did not help on its own |
| 4kSDR12 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,web did not help on its own |
| 4kSDR12 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,tdn,trim did not help on its own |
| 4kSDR12 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,tdn,web did not help on its own |
| 4kSDR12 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,tdn did not help on its own |
| 4kSDR12 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim,web did not help on its own |
| 4kSDR12 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim,web did not help on its own |
| 4kSDR12 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim,web did not help on its own |
| 4kSDR12 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim did not help on its own |
| 4kSDR12 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 4kSDR12 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,tdn,trim,web did not help on its own |
| 4kSDR12 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,trim,web did not help on its own |
| 4kSDR12 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,log,tdn,trim,web did not help on its own |
| 4kSDR12 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,tdn,trim did not help on its own |
| 4kSDR12 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,tdn,web did not help on its own |
| 4kSDR12 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim,web did not help on its own |
| 4kSDR12 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: comp,lock,log,tdn,trim,web did not help on its own |
| 4kSDR10 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: trim did not help on its own |
| 4kSDR10 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: web did not help on its own |
| 4kSDR10 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock did not help on its own |
| 4kSDR10 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn did not help on its own |
| 4kSDR10 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log did not help on its own |
| 4kSDR10 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: trim,web did not help on its own |
| 4kSDR10 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim did not help on its own |
| 4kSDR10 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 4kSDR10 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim did not help on its own |
| 4kSDR10 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 4kSDR10 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 4kSDR10 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim did not help on its own |
| 4kSDR10 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 4kSDR10 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 4kSDR10 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 4kSDR10 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: trim,web did not help on its own |
| 4kSDR10 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim did not help on its own |
| 4kSDR10 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 4kSDR10 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim did not help on its own |
| 4kSDR10 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 4kSDR10 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 4kSDR10 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim did not help on its own |
| 4kSDR10 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 4kSDR10 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 4kSDR10 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 4kSDR10 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim,web did not help on its own |
| 4kSDR10 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim,web did not help on its own |
| 4kSDR10 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim did not help on its own |
| 4kSDR10 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 4kSDR10 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim,web did not help on its own |
| 4kSDR10 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim did not help on its own |
| 4kSDR10 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 4kSDR10 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim did not help on its own |
| 4kSDR10 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 4kSDR10 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 4kSDR10 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,trim,web did not help on its own |
| 4kSDR10 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,trim,web did not help on its own |
| 4kSDR10 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim did not help on its own |
| 4kSDR10 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 4kSDR10 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,trim,web did not help on its own |
| 4kSDR10 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim did not help on its own |
| 4kSDR10 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 4kSDR10 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim did not help on its own |
| 4kSDR10 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 4kSDR10 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 4kSDR10 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim,web did not help on its own |
| 4kSDR10 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim,web did not help on its own |
| 4kSDR10 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim,web did not help on its own |
| 4kSDR10 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim did not help on its own |
| 4kSDR10 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 4kSDR10 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,trim,web did not help on its own |
| 4kSDR10 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,trim,web did not help on its own |
| 4kSDR10 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,trim,web did not help on its own |
| 4kSDR10 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim did not help on its own |
| 4kSDR10 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 4kSDR10 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim,web did not help on its own |
| 4kSDR10 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,trim,web did not help on its own |
| 2kSDR12 | lossless | off | off | off | off | off | 60.0 | pass_5min | 300.2 | 0 |  |  | 57.85 |  () | 46.0 | 1856 | 4.7 |  |  |
| 2kSDR12 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: web did not help on its own |
| 2kSDR12 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock did not help on its own |
| 2kSDR12 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn did not help on its own |
| 2kSDR12 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log did not help on its own |
| 2kSDR12 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: web did not help on its own |
| 2kSDR12 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock did not help on its own |
| 2kSDR12 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 2kSDR12 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn did not help on its own |
| 2kSDR12 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 2kSDR12 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 2kSDR12 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log did not help on its own |
| 2kSDR12 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 2kSDR12 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 2kSDR12 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 2kSDR12 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: web did not help on its own |
| 2kSDR12 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock did not help on its own |
| 2kSDR12 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 2kSDR12 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn did not help on its own |
| 2kSDR12 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 2kSDR12 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 2kSDR12 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log did not help on its own |
| 2kSDR12 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 2kSDR12 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 2kSDR12 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 2kSDR12 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 2kSDR12 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 2kSDR12 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 2kSDR12 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 2kSDR12 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 2kSDR12 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 2kSDR12 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 2kSDR12 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 2kSDR12 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 2kSDR12 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 2kSDR12 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,web did not help on its own |
| 2kSDR12 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: tdn,web did not help on its own |
| 2kSDR12 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn did not help on its own |
| 2kSDR12 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 2kSDR12 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,web did not help on its own |
| 2kSDR12 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log did not help on its own |
| 2kSDR12 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 2kSDR12 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn did not help on its own |
| 2kSDR12 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 2kSDR12 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 2kSDR12 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 2kSDR12 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 2kSDR12 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 2kSDR12 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 2kSDR12 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 2kSDR12 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,tdn,web did not help on its own |
| 2kSDR12 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,web did not help on its own |
| 2kSDR12 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: log,tdn,web did not help on its own |
| 2kSDR12 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn did not help on its own |
| 2kSDR12 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 2kSDR12 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 2kSDR12 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | combination skipped: lock,log,tdn,web did not help on its own |
| 2kSDR10 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kSDR10 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR16 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 2kHDR12 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | off | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | off | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | off | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | on | on | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | off | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | off | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | off | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | on | off | off |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | on | on | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | unc | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kHDR12 | lossless | on | on | on | off | on |  | pruned |  |  |  |  |  |  () |  |  |  |  | baseline already clean at the highest fps the storage allows: nothing to improve |
| 4kSDR10 | lossless | off | off | off | on | off | 25.0 | buffer_full | 258.7 | 0 |  | buffer_full:1 | 57.85 |  () | 48.7 | 1268 | 5.5 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 78/24 frames, stopped after 259 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 60.0 | buffer_full | 597.9 | 0 |  | buffer_full:1 | 58.4 |  () | 57.8 | 1436 | 9.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 319/24 frames, stopped after 598 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 59.0 | buffer_full | 592.8 | 0 |  | buffer_full:1 | 56.2 |  () | 54.7 | 1211 | 9.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 262/24 frames, stopped after 593 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 58.0 | buffer_full | 436.8 | 0 |  | buffer_full:1 | 55.65 |  () | 63.8 | 1278 | 6.4 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 263/24 frames, stopped after 437 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 57.0 | buffer_full | 333.2 | 0 |  | buffer_full:1 | 56.75 |  () | 39.1 | 1171 | 4.8 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 208/24 frames, stopped after 333 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 56.0 | buffer_full | 426.3 | 0 |  | buffer_full:1 | 56.2 |  () | 35.1 | 1190 | 6.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 235/24 frames, stopped after 426 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 55.0 | buffer_full | 381.7 | 0 |  | buffer_full:1 | 56.2 |  () | 28.9 | 1144 | 5.3 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 199/24 frames, stopped after 382 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 54.0 | buffer_full | 315.2 | 0 |  | buffer_full:1 | 54.55 |  () | 23.3 | 1222 | 4.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 164/24 frames, stopped after 315 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 53.0 | buffer_full | 379.2 | 0 |  | buffer_full:1 | 56.2 |  () | 18.4 | 1242 | 5.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 187/24 frames, stopped after 379 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 52.0 | buffer_full | 39.0 | 0 |  | buffer_full:1 | 55.1 |  () | 29.6 | 1208 | 0.4 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 205/24 frames, stopped after 39 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 51.0 | buffer_full | 35.0 | 0 |  | buffer_full:1 | 54.0 |  () | 20.3 | 1510 | 0.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 204/24 frames, stopped after 35 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 50.0 | buffer_full | 506.3 | 0 |  | buffer_full:1 | 55.1 |  () | 30.5 | 1368 | 6.4 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 290/24 frames, stopped after 506 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 49.0 | buffer_full | 421.8 | 0 |  | buffer_full:1 | 55.1 |  () | 26.4 | 1105 | 5.2 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 194/24 frames, stopped after 422 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 48.0 | buffer_full | 480.3 | 0 |  | buffer_full:1 | 55.65 |  () | 41.7 | 1415 | 5.9 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 222/24 frames, stopped after 480 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 47.0 | buffer_full | 175.1 | 0 |  | buffer_full:1 | 55.65 |  () | 20.6 | 1106 | 2.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 162/24 frames, stopped after 175 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 46.0 | buffer_full | 497.3 | 0 |  | buffer_full:1 | 53.45 |  () | 37.3 | 1060 | 5.9 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 201/24 frames, stopped after 497 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 45.0 | buffer_full | 548.4 | 0 |  | buffer_full:1 | 56.2 |  () | 24.1 | 1099 | 6.3 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 135/24 frames, stopped after 548 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 44.0 | buffer_full | 74.5 | 0 |  | buffer_full:1 | 54.0 |  () | 8.6 | 1146 | 0.7 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 233/24 frames, stopped after 74 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 43.0 | buffer_full | 42.0 | 0 |  | buffer_full:1 | 53.45 |  () | 16.9 | 1174 | 0.4 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 115/24 frames, stopped after 42 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 42.0 | buffer_full | 33.0 | 0 |  | buffer_full:1 | 52.35 |  () | 16.2 | 1216 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 208/24 frames, stopped after 33 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 41.0 | buffer_full | 46.5 | 0 |  | buffer_full:1 | 53.45 |  () | 15.6 | 1265 | 0.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 277/24 frames, stopped after 46 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 40.0 | buffer_full | 40.5 | 0 |  | buffer_full:1 | 51.8 |  () | 4.1 | 1110 | 0.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 235/24 frames, stopped after 40 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 39.0 | buffer_full | 33.5 | 0 |  | buffer_full:1 | 51.8 |  () | 15.1 | 1085 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 174/24 frames, stopped after 34 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 38.0 | pass_10min | 600.3 | 0 |  |  | 56.75 |  () | 30.3 | 1334 | 6.0 |  |  |
| 2kSDR10 | unc | off | off | off | on | off | 44.0 | buffer_full | 21.0 | 0 |  | buffer_full:1 | 54.0 |  () | 15.8 | 1173 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 245/12 frames, stopped after 21 s) |
| 2kSDR10 | unc | off | off | off | on | off | 43.0 | buffer_full | 43.5 | 0 |  | buffer_full:1 | 52.9 |  () | 8.3 | 1564 | 0.6 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 246/12 frames, stopped after 44 s) |
| 2kSDR10 | unc | off | off | off | on | off | 42.0 | buffer_full | 78.0 | 0 |  | buffer_full:1 | 52.35 |  () | 11.9 | 1556 | 1.4 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 306/12 frames, stopped after 78 s) |
| 2kSDR10 | unc | off | off | off | on | off | 41.0 | buffer_full | 126.6 | 0 |  | buffer_full:1 | 52.35 |  () | 17.5 | 1197 | 2.5 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 202/12 frames, stopped after 127 s) |
| 2kSDR10 | unc | off | off | off | on | off | 40.0 | buffer_full | 89.5 | 0 |  | buffer_full:1 | 52.35 |  () | 13.9 | 1556 | 1.6 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 234/12 frames, stopped after 90 s) |
| 2kSDR10 | unc | off | off | off | on | off | 39.0 | buffer_full | 428.2 | 0 |  | buffer_full:1 | 55.1 |  () | 23.3 | 1520 | 8.5 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 198/12 frames, stopped after 428 s) |
| 2kSDR10 | unc | off | off | off | on | off | 38.0 | pass_10min | 600.3 | 0 |  |  | 55.1 |  () | 36.5 | 1661 | 11.9 |  |  |
| 2kHDR16 | unc | off | off | off | on | off | 27.0 | buffer_full | 58.5 | 0 |  | buffer_full:1 | 51.25 |  () | 20.8 | 1268 | 1.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 142/12 frames, stopped after 58 s) |
| 2kHDR16 | unc | off | off | off | on | off | 26.0 | pass_10min | 600.2 | 0 |  |  | 54.55 |  () | 21.9 | 1468 | 13.1 |  |  |
| 2kHDR12 | unc | off | off | off | on | off | 30.0 | pass_10min | 600.3 | 0 |  |  | 56.2 |  () | 55.1 | 1463 | 11.3 |  |  |
| 2kSDR12 | lossless | off | off | off | on | off | 38.0 | pass_20min | 1200.1 | 0 |  |  | 57.3 |  () | 39.5 | 2012 | 12.0 |  |  |
| 2kSDR10 | unc | off | off | off | on | off | 38.0 | buffer_full | 972.0 | 0 |  | buffer_full:1 | 55.65 |  () | 34.5 | 1547 | 18.9 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 318/12 frames, stopped after 972 s) |
| 2kSDR10 | unc | off | off | off | on | off | 37.0 | pass_20min | 1200.1 | 0 |  |  | 57.85 |  () | 24.5 | 1694 | 23.2 |  |  |
| 2kHDR16 | unc | off | off | off | on | off | 26.0 | pass_20min | 1200.0 | 0 |  |  | 53.45 |  () | 22.2 | 1711 | 26.1 |  |  |
| 2kHDR12 | unc | off | off | off | on | off | 30.0 | buffer_full | 1182.1 | 0 |  | buffer_full:1 | 55.1 |  () | 16.0 | 1661 | 22.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 143/12 frames, stopped after 1182 s) |
| 2kHDR12 | unc | off | off | off | on | off | 29.0 | pass_20min | 1200.1 | 0 |  |  | 57.85 |  () | 35.0 | 1944 | 21.9 |  |  |
| 2kSDR12 | lossless | off | off | off | on | off | 38.0 | buffer_full | 1636.9 | 0 |  | buffer_full:1 | 56.2 |  () | 47.7 | 1492 | 16.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 364/24 frames, stopped after 1637 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 37.0 | buffer_full | 1651.9 | 0 |  | buffer_full:1 | 57.3 |  () | 48.0 | 1389 | 15.9 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 291/24 frames, stopped after 1652 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 36.0 | buffer_full | 1259.2 | 0 |  | buffer_full:1 | 54.0 |  () | 25.5 | 1349 | 13.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 262/24 frames, stopped after 1259 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kSDR10 | lossless | off | off | off | on | off | 25.0 | buffer_full | 12.0 | 0 |  | buffer_full:1 | 52.35 |  () | 21.1 | 1273 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 64/24 frames, stopped after 12 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 33.0 | buffer_full | 177.6 | 0 |  | buffer_full:1 | 54.55 |  () | 18.3 | 1691 | 1.8 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 276/24 frames, stopped after 178 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR12 | lossless | off | off | off | on | off | 27.0 | pass_30min | 1800.4 | 0 |  |  | 57.3 |  () | 49.8 | 1745 | 17.6 |  |  |
| 2kSDR12 | lossless | off | off | off | on | off | 30.0 | pass_30min | 1800.4 | 0 |  |  | 55.65 |  () | 25.2 | 1758 | 18.3 |  |  |
| 2kSDR12 | lossless | off | off | off | on | off | 31.0 | buffer_full | 1701.5 | 0 |  | buffer_full:1 | 53.45 |  () | 50.5 | 1386 | 17.7 |  | buffer_full: Media stopped responding: nothing was written for 5 s. media_removed | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 261/24 frames, stopped after 1702 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 2kSDR10 | unc | off | off | off | on | off | 37.0 | buffer_full | 19.5 | 0 |  | buffer_full:1 | 51.25 |  () | 7.6 | 1074 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 148/12 frames, stopped after 20 s) |
| 2kSDR10 | unc | off | off | off | on | off | 31.0 | pass_30min | 1800.4 | 0 |  |  | 56.75 |  () | 33.2 | 1531 | 29.2 |  |  |
| 2kSDR10 | unc | off | off | off | on | off | 34.0 | buffer_full | 1464.3 | 0 |  | buffer_full:1 | 55.65 |  () | 26.2 | 1668 | 25.8 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 266/12 frames, stopped after 1464 s) |
| 2kSDR10 | unc | off | off | off | on | off | 32.0 | pass_30min | 1800.4 | 0 |  |  | 57.85 |  () | 44.0 | 1757 | 30.2 |  |  |
| 2kSDR10 | unc | off | off | off | on | off | 33.0 | pass_30min | 1800.4 | 0 |  |  | 57.85 |  () | 40.4 | 2428 | 31.2 |  |  |
| 2kHDR16 | unc | off | off | off | on | off | 26.0 | pass_30min | 1800.4 | 0 |  |  | 57.85 |  () | 24.9 | 1871 | 39.3 |  |  |
| 2kHDR12 | unc | off | off | off | on | off | 29.0 | buffer_full | 1409.7 | 0 |  | buffer_full:1 | 56.75 |  () | 23.8 | 1532 | 25.5 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 172/12 frames, stopped after 1410 s) |
| 2kHDR12 | unc | off | off | off | on | off | 25.0 | pass_30min | 1800.4 | 1 |  |  | 57.3 |  () | 26.7 | 1538 | 28.4 |  | unconfirmed: no counter or context pointed to a cause |
| 2kHDR12 | unc | off | off | off | on | off | 27.0 | pass_30min | 1800.4 | 0 |  |  | 57.3 |  () | 42.1 | 1922 | 30.6 |  |  |
| 2kHDR12 | unc | off | off | off | on | off | 28.0 | pass_30min | 1800.4 | 0 |  |  | 57.3 |  () | 40.1 | 2211 | 31.8 |  |  |
| 4kHDR12 | lossless | off | off | off | on | off | 27.0 | buffer_full | 8.0 | 0 |  | buffer_full:1 | 58.4 |  () | 74.9 | 1374 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 54/24 frames, stopped after 8 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | off | off | off | on | off | 26.0 | buffer_full | 5.5 | 0 |  | buffer_full:1 | 58.4 |  () | 57.1 | 1386 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 44/24 frames, stopped after 6 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | off | off | off | on | off | 25.0 | buffer_full | 6.5 | 0 |  | buffer_full:1 | 57.85 |  () | 52.7 | 1477 | 0.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 45/24 frames, stopped after 6 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | off | off | off | on | off | 25 | exhausted |  |  |  |  |  |  () |  |  |  |  |  |
| 4kHDR12 | lossless | on | off | off | on | off | 27.0 | buffer_full | 7.0 | 0 |  | buffer_full:1 | 56.2 |  () | 26.9 | 1365 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 46/24 frames, stopped after 7 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | on | off | off | on | off | 26.0 | buffer_full | 6.0 | 0 |  | buffer_full:1 | 58.4 |  () | 47.0 | 1617 | 0.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 40/24 frames, stopped after 6 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | on | off | off | on | off | 25.0 | buffer_full | 7.5 | 0 |  | buffer_full:1 | 54.55 |  () | 27.7 | 1319 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 42/24 frames, stopped after 8 s); probable: lossless JPEG encoder too slow above ~17.5 fps (recipe row 2) |
| 4kHDR12 | lossless | on | off | off | on | off | 25 | exhausted |  |  |  |  |  |  () |  |  |  |  |  |
| 4kHDR12 | unc | on | off | off | on | off | 27.0 | buffer_full | 6.5 | 0 |  | buffer_full:1 | 55.65 |  () | 14.1 | 1449 | 0.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 49/12 frames, stopped after 6 s) |
| 4kHDR12 | unc | on | off | off | on | off | 26.0 | buffer_full | 5.5 | 0 |  | buffer_full:1 | 55.65 |  () | 23.5 | 1427 | 0.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 40/12 frames, stopped after 6 s) |
| 4kHDR12 | unc | on | off | off | on | off | 25.0 | buffer_full | 8.0 | 0 |  | buffer_full:1 | 55.65 |  () | 28.1 | 1648 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 38/12 frames, stopped after 8 s) |
| 4kHDR12 | unc | on | off | off | on | off | 25 | exhausted |  |  |  |  |  |  () |  |  |  |  |  |
| 4kSDR10 | lossless | on | off | off | on | off | 33.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  | Core: ApertarCore CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear |
| 4kSDR12 | lossless | on | off | off | on | off | 27.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  | Core: ApertarCore CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear |
| 2kSDR12 | lossless | on | off | off | on | off | 60.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  | Core: ApertarCore CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear |
| 2kSDR10 | unc | on | off | off | on | off | 60.0 | skipped_unavailable |  |  |  |  |  |  () |  |  |  |  | Core: ApertarCore CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear |
| 2kHDR16 | unc | on | off | off | on | off | 30.0 | pass_5min | 300.1 | 0 |  |  | 56.2 |  () | 18.6 | 2194 | 5.7 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 30.0 | pass_10min | 600.3 | 0 |  |  | 55.65 |  () | 27.5 | 2118 | 11.4 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 30.0 | pass_20min | 1200.1 | 0 |  |  | 56.2 |  () | 26.5 | 2211 | 22.7 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 30.0 | buffer_full | 1141.1 | 0 |  | buffer_full:1 | 56.2 |  () | 24.4 | 1647 | 21.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 182/12 frames, stopped after 1141 s) |
| 2kHDR16 | unc | on | off | off | on | off | 25.0 | pass_30min | 1800.3 | 0 |  |  | 57.3 |  () | 32.0 | 1576 | 28.4 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 27.0 | pass_30min | 1800.4 | 0 |  |  | 56.75 |  () | 28.2 | 1586 | 30.7 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 28.0 | pass_30min | 1800.5 | 0 |  |  | 58.95 |  () | 36.8 | 1863 | 31.8 |  |  |
| 2kHDR16 | unc | on | off | off | on | off | 29.0 | buffer_full | 1168.1 | 0 |  | buffer_full:1 | 55.1 |  () | 27.7 | 1537 | 21.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 149/12 frames, stopped after 1168 s) |
| 2kHDR12 | unc | on | off | off | on | off | 30.0 | pass_5min | 300.1 | 0 |  |  | 54.55 |  () | 21.1 | 1378 | 5.7 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 30.0 | pass_10min | 600.3 | 0 |  |  | 58.4 |  () | 27.9 | 1930 | 11.3 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 30.0 | buffer_full | 1129.1 | 0 |  | buffer_full:1 | 54.55 |  () | 31.7 | 1576 | 21.1 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 149/12 frames, stopped after 1129 s) |
| 2kHDR12 | unc | on | off | off | on | off | 25.0 | pass_20min | 1200.0 | 1 |  |  | 55.65 |  () | 24.6 | 1352 | 18.9 |  | unconfirmed: no counter or context pointed to a cause |
| 2kHDR12 | unc | on | off | off | on | off | 27.0 | pass_20min | 1200.1 | 0 |  |  | 55.65 |  () | 25.3 | 1300 | 20.4 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 28.0 | pass_20min | 1200.1 | 0 |  |  | 57.3 |  () | 29.1 | 1444 | 21.2 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 29.0 | pass_20min | 1200.1 | 0 |  |  | 56.75 |  () | 18.6 | 1548 | 21.9 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 29.0 | buffer_full | 1667.0 | 0 |  | buffer_full:1 | 55.65 |  () | 23.3 | 2149 | 30.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 137/12 frames, stopped after 1667 s) |
| 2kHDR12 | unc | on | off | off | on | off | 25.0 | pass_30min | 1800.4 | 0 |  |  | 58.4 |  () | 28.4 | 2375 | 28.3 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 27.0 | pass_30min | 1800.0 | 0 |  |  | 57.85 |  () | 37.5 | 2429 | 30.6 |  |  |
| 2kHDR12 | unc | on | off | off | on | off | 28.0 | pass_30min | 1800.4 | 0 |  |  | 57.85 |  () | 28.3 | 2122 | 31.7 |  |  |

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
| 2kSDR12_unc_log0_tdn0_lock0_trim1_web0 | 35.0 | pass_5min | 5.0 |
| 2kSDR10_unc_log0_tdn0_lock0_trim1_web0 | 33.0 | pass_30min | 30.0 |
| 2kHDR16_unc_log0_tdn0_lock0_trim1_web0 | 26.0 | pass_30min | 30.0 |
| 2kHDR12_unc_log0_tdn0_lock0_trim1_web0 | 28.0 | pass_30min | 30.0 |
| 4kSDR10_lossless_log0_tdn0_lock0_trim1_web0 | 25.0 | pass_5min | 5.0 |
| 2kSDR12_lossless_log0_tdn0_lock0_trim1_web0 | 30.0 | pass_30min | 30.0 |
| 2kSDR12_unc_log0_tdn0_lock0_trim0_web0 | 37.0 | pass_5min | 5.0 |
| 2kSDR12_lossless_log0_tdn0_lock0_trim0_web0 | 60.0 | pass_5min | 5.0 |
| 2kHDR16_unc_log1_tdn0_lock0_trim1_web0 | 28.0 | pass_30min | 30.0 |
| 2kHDR12_unc_log1_tdn0_lock0_trim1_web0 | 28.0 | pass_30min | 30.0 |
