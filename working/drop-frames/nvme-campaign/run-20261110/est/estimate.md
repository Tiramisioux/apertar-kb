# Estimator campaign: sustained fps estimates

Run `nvme-20261110`; drive Corsair MP600 Mini (sustained 596 MB/s, stored profile). Estimates at the reference levers (TDN off, lock off, WebUI on, audio on, aids on); every lever state is in `estimate-table.csv`.

| spec | top | probed limit | how | estimate | limited by | note |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16:cdng:unc | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kP:prores:lt | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:cdng:lj | 60.0 | 60.0 | at least | 60 | sensor |  |
| 4kHDR12:cdng:unc | 30.0 | 24.99 | measured | 24 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:lj | 30.0 | 16.03 | measured | 15 | encoder | back end: gaps at 30 fps (measured); cell out at 25 fps (measured) |
| 4kHDR16:cdng:unc | 60.0 | 28.0 | at least | 27 | measured cell | cell out at 28 fps (measured) |
| 4kHDR16:cdng:unc:log | 30.0 | 25.58 | measured | 24 | back end | back end: gaps at 28 fps (measured); cell out at 28 fps (measured) |
| 4kP:h264:1920x1080 | 60.0 | 60.0 | at least | 60 | sensor |  |
| 4kP:prores:hq | 60.0 | 30.05 | measured | 29 | encoder | back end: gaps at 60 fps (measured) |
| 4kSDR12:cdng:unc | 60.0 | 40.58 | measured | 39 | back end | back end: gaps at 60 fps (measured) |
| 4kSDR12:lossydng:3to1 | 60.0 | 38.86 | measured | 37 | encoder |  |
| 4kSDR12:lossydng:5to1 | 60.0 | 42.77 | measured | 41 | encoder |  |
| crop4k3SDR12:lossydng:3to1 | 60.54 | 43.24 | measured | 41 | encoder |  |

## Lever effects (P2, main effects; enc/stor on log capacity, be on gaps per minute)


## Validation (P3)

- {'n': 0, 'clean_at_p': '0 of 0', 'out_at_p+1': '0 of 0'}
- success (pre-registered): clean at p in >= 10 of 12, out at p+1 in >= 8 of 12
