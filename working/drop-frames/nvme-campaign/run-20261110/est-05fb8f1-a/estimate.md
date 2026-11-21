# Estimator campaign: sustained fps estimates

Run `nvme-20261110`; drive Corsair MP600 Mini (sustained 596 MB/s, stored profile). Estimates at the reference levers (TDN off, lock off, WebUI on, audio on, aids on); every lever state is in `estimate-table.csv`.

| spec | top | probed limit | how | estimate | limited by | note |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16:cdng:lj | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kHDR16:cdng:lj:log | 30.0 | 29.99 | measured | 29 | encoder |  |
| 2kHDR16:cdng:unc | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kHDR16:cdng:unc:log | 30.0 | 29.99 | measured | 29 | encoder |  |
| 2kHDR16:mlv | 30.0 | 30.0 | at least | 30 | sensor |  |
| 2kP:prores:422 | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kP:prores:hq | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kP:prores:lt | 60.0 | 59.95 | measured | 57 | back end | back end: gaps at 60 fps (measured) |
| 2kP:prores:proxy | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:cdng:lj | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:cdng:unc | 60.0 | 60.0 | at least | 60 | sensor |  |
| 2kSDR12:lossydng:3to1 | 60.0 | 60.0 | measured | 60 | sensor |  |
| 2kSDR12:lossydng:5to1 | 60.0 | 60.0 | measured | 60 | sensor |  |
| 2kSDR12:mlv | 60.0 | 59.99 | measured | 58 | storage |  |
| 4kHDR12:cdng:lj | 30.0 | 30.015 | measured | 28 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR12:cdng:unc | 30.0 | 26.235 | measured | 25 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR12:mlv | 30.0 | 24.79 | measured | 24 | back end | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:lj | 30.0 | 14.76 | measured | 14 | encoder | back end: gaps at 30 fps (measured); cell out at 25 fps (measured) |
| 4kHDR16:cdng:lj:log | 30.0 | 29.9 | measured | 24 | measured cell | back end: gaps at 30 fps (measured); cell out at 25 fps (measured) |
| 4kHDR16:cdng:unc | 30.0 | 29.37 | measured | 27 | measured cell | back end: gaps at 30 fps (measured); cell out at 28 fps (measured) |
| 4kHDR16:cdng:unc:log | 30.0 | 25.71 | measured | 24 | back end | back end: gaps at 28 fps (measured); cell out at 28 fps (measured) |
| 4kHDR16:mlv | 30.0 | 27.66 | measured | 26 | back end | back end: gaps at 30 fps (measured) |
| 4kP:h264:1920x1080 | 60.0 | 60.0 | at least | 60 | sensor |  |
| 4kP:h264:2560x1440 | 60.0 | 47.28 | measured | 45 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:422 | 60.0 | 41.455 | measured | 40 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq | 60.0 | 28.58 | measured | 27 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq:arri_logc4 | 60.0 | 43.09 | measured | 41 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:lt | 60.0 | 44.355000000000004 | measured | 43 | encoder | back end: gaps at 60 fps (measured) |
| 4kP:prores:proxy | 60.0 | 47.315 | measured | 45 | encoder | back end: gaps at 60 fps (measured) |
| 4kSDR10:cdng:lj | 60.0 | 46.47 | measured | 45 | encoder |  |
| 4kSDR10:cdng:unc | 60.0 | 45.175 | measured | 43 | back end | back end: gaps at 60 fps (measured) |
| 4kSDR10:lossydng:3to1 | 60.0 | 41.1 | measured | 39 | encoder |  |
| 4kSDR10:lossydng:5to1 | 60.0 | 44.38 | measured | 43 | encoder |  |
| 4kSDR10:mlv | 60.0 | 10.945 | measured | 10 | storage |  |
| 4kSDR12:cdng:lj | 60.0 | 41.525000000000006 | measured | 40 | encoder |  |
| 4kSDR12:cdng:unc | 60.0 | 40.68 | measured | 39 | back end | back end: gaps at 60 fps (measured) |
| 4kSDR12:lossydng:3to1 | 60.0 | 38.44 | measured | 37 | encoder |  |
| 4kSDR12:lossydng:5to1 | 60.0 | 43.01 | measured | 41 | encoder |  |
| 4kSDR12:mlv | 60.0 | 25.865000000000002 | measured | 25 | storage |  |
| crop4k3SDR12:cdng:lj | 60.54 | 58.73 | measured | 56 | encoder |  |
| crop4k3SDR12:cdng:unc | 60.54 | 53.17 | measured | 51 | storage |  |
| crop4k3SDR12:mlv | 60.54 | 36.12 | measured | 35 | storage |  |

## Lever effects (P2, main effects; enc/stor on log capacity, be on gaps per minute)

- be (n=16, SE 12.975): aids -46.956, audio +4.029, lock +31.466, tdn +287.756, web +8.716
  - two-way interactions above SE: tdnxlock +25.226, tdnxaids -38.721, lockxweb +13.241, lockxaudio -23.246, webxaudio +18.004, webxaids -29.486
- be2 (n=16, SE 12.975): aids -57.775, audio +13.653, lock +24.180, tdn +288.357, web +39.152
  - two-way interactions above SE: tdnxweb +24.428, tdnxaids -48.040, lockxweb +27.545, lockxaids -28.158, webxaudio -13.433, webxaids -24.955, audioxaids +17.810
- enc (n=16, SE 0.011): aids -0.059, audio -0.043, lock -0.005, tdn +0.249, web -0.013
  - two-way interactions above SE: tdnxweb +0.014, tdnxaudio +0.021, tdnxaids -0.062
- stor (n=16, SE 0.011): aids +0.011, audio +0.094, lock +0.122, tdn +0.321, web +0.027
  - two-way interactions above SE: tdnxlock +0.091, tdnxweb -0.014, tdnxaudio +0.119, tdnxaids -0.016, lockxaudio -0.101, webxaids -0.109

## Validation (P3)

- {'n': 12, 'clean_at_p': '6 of 12', 'out_at_p+1': '5 of 6'}
- success (pre-registered): clean at p in >= 10 of 12, out at p+1 in >= 8 of 12

## Ladder check (P4)

- 25 fps: rung 1 expected, skip setup_mismatch log_applied=True
- 26 fps: rung 1 expected, skip setup_mismatch log_applied=True
- 27 fps: rung 1 expected, skip setup_mismatch log_applied=True
