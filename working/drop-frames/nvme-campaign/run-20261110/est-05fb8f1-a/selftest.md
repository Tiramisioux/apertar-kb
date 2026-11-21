# Self-test check (plan section 6.4)

P0 alone (+ the drive profile) against the full fit: 12 % within +-1 fps (goal >= 90 %).

| spec | full fit | from P0 | error | how |
| --- | --- | --- | --- | --- |
| 2kHDR16:cdng:lj:log | 29 | None | None | no anchor |
| 2kHDR16:cdng:unc:log | 29 | None | None | no anchor |
| 2kP:prores:lt | 57 | 113 | 56 | derived: ProRes HQ x pixels |
| 2kSDR12:lossydng:3to1 | 60 | 158 | 98 | derived: lossy x bytes |
| 2kSDR12:lossydng:5to1 | 60 | 158 | 98 | derived: lossy x bytes |
| 2kSDR12:mlv | 58 | 185 | 127 | derived: anchor write rate / bytes |
| 4kHDR12:cdng:lj | 28 | None | None | no anchor |
| 4kHDR12:cdng:unc | 25 | 46 | 21 | derived: anchor write rate / bytes |
| 4kHDR12:mlv | 24 | 46 | 22 | derived: anchor write rate / bytes |
| 4kHDR16:cdng:lj | 14 | 15 | 1 | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:lj:log | 28 | None | None | no anchor |
| 4kHDR16:cdng:unc | 28 | 28 | 0 |  |
| 4kHDR16:cdng:unc:log | 24 | 25 | 1 | back end: gaps at 28 fps (measured) |
| 4kHDR16:mlv | 26 | 34 | 8 | derived: anchor write rate / bytes |
| 4kP:h264:2560x1440 | 45 | None | None | no anchor |
| 4kP:prores:422 | 40 | 28 | -12 | derived: ProRes HQ x pixels |
| 4kP:prores:hq | 27 | 28 | 1 | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq:arri_logc4 | 41 | 28 | -13 | derived: ProRes HQ x pixels |
| 4kP:prores:lt | 43 | 28 | -15 | derived: ProRes HQ x pixels |
| 4kP:prores:proxy | 45 | 28 | -17 | derived: ProRes HQ x pixels |
| 4kSDR10:cdng:lj | 45 | None | None | no anchor |
| 4kSDR10:cdng:unc | 43 | 55 | 12 | derived: anchor write rate / bytes |
| 4kSDR10:lossydng:3to1 | 39 | 47 | 8 | derived: lossy x bytes |
| 4kSDR10:lossydng:5to1 | 43 | 47 | 4 | derived: lossy x bytes |
| 4kSDR10:mlv | 10 | 55 | 45 | derived: anchor write rate / bytes |
| 4kSDR12:cdng:lj | 40 | None | None | no anchor |
| 4kSDR12:cdng:unc | 39 | 46 | 7 |  |
| 4kSDR12:lossydng:3to1 | 37 | 39 | 2 |  |
| 4kSDR12:lossydng:5to1 | 41 | 39 | -2 | derived: lossy x bytes |
| 4kSDR12:mlv | 25 | 46 | 21 | derived: anchor write rate / bytes |
| crop4k3SDR12:cdng:lj | 56 | None | None | no anchor |
| crop4k3SDR12:cdng:unc | 51 | 61 | 10 | derived: anchor write rate / bytes |
| crop4k3SDR12:mlv | 35 | 61 | 26 | derived: anchor write rate / bytes |
