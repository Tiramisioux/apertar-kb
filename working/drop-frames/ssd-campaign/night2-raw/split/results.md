# Long-take campaign results

Pi: Raspberry Pi Compute Module 5 Lite Rev 1.0 | Core b755383 web: merge progress bars in the Media card and the Storage tile | drive: None | started 2026-11-09 20:29:07

Temperatures and loads are at the drop (or at the end of a clean take). Causes are estimates: probable / unconfirmed, never confirmed.
Target per take: 30 min, or as long as the drive allows at these settings (pass_drive_full = clean until <6 GiB free). Every take that fills the drive is logged (drive full at s). Lowest fps tried: 25.

| mode | comp | log | tdn | lock | trim | web | fps | outcome | s | dropped | first drop s | kinds | Pi C | NVMe C (peak) | cpu % | RAM avail MB | fill % | drive full at s | cause (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_dropped | 1800.2 | 1 |  |  | 52.35 |  () | 17.2 | 3274 | 36.3 |  | unconfirmed: no counter or context pointed to a cause |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 600.2 | 0 |  |  | 51.8 |  () | 14.8 | 3232 | 12.1 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 600.2 | 0 |  |  | 51.25 |  () | 18.9 | 3181 | 12.1 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 600.2 | 0 |  |  | 51.25 |  () | 19.2 | 3119 | 12.1 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 1800.2 | 0 |  |  | 50.7 |  () | 17.1 | 2994 | 36.3 |  |  |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_dropped | 1800.2 | 3 |  |  | 52.35 |  () | 13.9 | 2916 | 36.3 |  | unconfirmed: no counter or context pointed to a cause |
| 2kSDR12 | unc | off | off | off | on | off | 32.0 | ab_clean | 1800.2 | 0 |  |  | 51.25 |  () | 13.6 | 2885 | 36.3 |  |  |

## Best clean fps per config (first pass while stepping down)

| config | fps | outcome | minutes |
|---|---|---|---|
