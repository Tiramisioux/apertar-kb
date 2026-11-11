# Estimator campaign: sustained fps estimates

Run `nvme-20261110`; drive Corsair MP600 Mini (sustained 596 MB/s, stored profile). Estimates at the reference levers (TDN off, lock off, WebUI on, audio on, aids on); every lever state is in `estimate-table.csv`.

| spec | top | probed limit | how | estimate | limited by | note |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16:cdng:lj:log | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kHDR16:cdng:unc | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kHDR16:cdng:unc:log | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kHDR16:mlv | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kP:prores:hq | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kP:prores:lt | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kP:prores:proxy | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:cdng:lj | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:cdng:unc | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:mlv | 60.0 | 60.0 | measured | 60 | sensor |  |
| 4kHDR12:cdng:lj | 30.0 | 30.01 | measured | 28 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR12:cdng:unc | 30.0 | 24.99 | measured | 24 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR12:mlv | 30.0 | 24.55 | measured | 23 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:lj | 30.0 | 16.285 | measured | 15 | encoder | back end: gaps at 30 fps (measured); cell out at 25 fps (measured) |
| 4kHDR16:cdng:lj:log | 30.0 | 30.0 | measured | 24 | measured cell | back end: gaps at 30 fps (measured); cell out at 25 fps (measured) |
| 4kHDR16:cdng:unc | 60.0 | 29.97 | measured | 27 | measured cell | back end: gaps at 30 fps (measured); cell out at 28 fps (measured) |
| 4kHDR16:cdng:unc:log | 30.0 | 25.58 | measured | 24 | back end | back end: gaps at 28 fps (measured); cell out at 28 fps (measured) |
| 4kHDR16:mlv | 30.0 | 28.54 | measured | 27 | back end | back end: gaps at 30 fps (measured) |
| 4kP:h264:1920x1080 | 60.0 | 60.0 | at least | 60 | sensor |  |
| 4kP:prores:422 | 60.0 | 44.87 | measured | 43 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq | 60.0 | 30.325000000000003 | measured | 29 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq:arri_logc4 | 60.0 | 44.16 | measured | 42 | encoder | back end: gaps at 60 fps (measured) |
| 4kSDR10:cdng:lj | 60.0 | 45.17 | measured | 43 | encoder |  |
| 4kSDR10:cdng:unc | 60.0 | 47.24 | measured | 45 | back end | back end: gaps at 60 fps (measured) |
| 4kSDR10:lossydng:3to1 | 60.0 | 36.68 | measured | 35 | encoder |  |
| 4kSDR10:lossydng:5to1 | 60.0 | 45.52 | measured | 44 | encoder |  |
| 4kSDR10:mlv | 60.0 | 11.57 | measured | 11 | storage |  |
| 4kSDR12:cdng:lj | 60.0 | 42.5 | measured | 41 | encoder |  |
| 4kSDR12:cdng:unc | 60.0 | 39.285 | measured | 38 | back end | back end: gaps at 60 fps (measured) |
| 4kSDR12:lossydng:3to1 | 60.0 | 38.84 | measured | 37 | encoder |  |
| 4kSDR12:lossydng:5to1 | 60.0 | 42.77 | measured | 41 | encoder |  |
| crop4k3SDR12:cdng:lj | 60.54 | 55.43 | measured | 53 | encoder |  |
| crop4k3SDR12:lossydng:3to1 | 60.54 | 43.24 | measured | 41 | encoder |  |
| crop4k3SDR12:lossydng:5to1 | 60.54 | 58.93 | measured | 57 | encoder |  |
| crop4k3SDR12:mlv | 60.54 | 36.51 | measured | 35 | storage |  |

## Lever effects (P2, main effects; enc/stor on log capacity, be on gaps per minute)


## Validation (P3)

- {'n': 0, 'clean_at_p': '0 of 0', 'out_at_p+1': '0 of 0'}
- success (pre-registered): clean at p in >= 10 of 12, out at p+1 in >= 8 of 12
