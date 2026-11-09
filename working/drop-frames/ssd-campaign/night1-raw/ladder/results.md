# Long-take campaign results

Pi: Raspberry Pi Compute Module 5 Lite Rev 1.0 | Core c9e7707 media: a Standard clip-name preset with the take's timecode | drive: None | started 2026-11-09 02:54:12

Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: probable / unconfirmed, never confirmed.
Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.

| mode | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2kSDR12 | unc | off | off | off | on | off | 60.0 | buffer_full | 35.0 | 0 |  | buffer_full:1 | 51.8 |  () | 13.1 | 1589 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 502/12 frames, stopped after 35 s) |
| 2kSDR12 | lossless | off | off | off | on | off | 60.0 | ab_clean | 90.1 | 0 |  |  | 57.3 |  () | 32.7 | 1567 | 1.3 |  |  |
| 2kHDR16 | unc | off | off | off | on | off | 30.0 | buffer_full | 20.5 | 0 |  | buffer_full:1 | 49.05 |  () | 5.5 | 1944 | 0.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 134/12 frames, stopped after 20 s) |
| 2kHDR16 | lossless | off | off | off | on | off | 30.0 | ab_clean | 90.1 | 0 |  |  | 57.3 |  () | 59.2 | 1913 | 1.2 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | buffer_full | 89.0 | 0 |  | buffer_full:1 | 52.9 |  () | 10.0 | 1390 | 1.3 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 378/12 frames, stopped after 89 s) |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | buffer_full | 239.6 | 0 |  | buffer_full:1 | 52.35 |  () | 11.3 | 1623 | 4.5 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 221/12 frames, stopped after 240 s) |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 600.3 | 0 |  |  | 54.0 |  () | 27.8 | 1502 | 12.1 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | buffer_full | 303.6 | 0 |  | buffer_full:1 | 53.45 |  () | 13.6 | 1180 | 5.8 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 191/12 frames, stopped after 304 s) |
| 2kSDR12 | unc | off | off | off | on | off | 31.0 | buffer_full | 216.6 | 0 |  | buffer_full:1 | 52.35 |  () | 3.5 | 1124 | 4.0 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 164/12 frames, stopped after 217 s) |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 1800.1 | 0 |  |  | 51.25 |  () | 9.5 | 1182 | 35.9 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 1800.2 | 0 |  |  | 52.35 |  () | 17.3 | 1249 | 36.3 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 1800.5 | 0 |  |  | 55.65 |  () | 35.0 | 1601 | 36.3 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | buffer_full | 1781.4 | 0 |  | buffer_full:1 | 55.65 |  () | 29.5 | 1244 | 35.6 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 199/12 frames, stopped after 1781 s) |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | buffer_full | 1756.0 | 0 |  | buffer_full:1 | 55.1 |  () | 25.8 | 1046 | 35.2 |  | buffer_full:   | probable: the drive fell behind - the write queue filled the RAM buffer to Core's 90 % safety stop (peak queue 101/12 frames, stopped after 1756 s) |

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
