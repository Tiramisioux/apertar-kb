# Self-test check (plan section 6.4)

P0 alone (+ the drive profile) against the full fit: 32 % within +-1 fps (goal >= 90 %).

| spec | full fit | from P0 | error | how |
| --- | --- | --- | --- | --- |
| 2kSDR12:mlv | 60 | 157 | 97 | derived: anchor write rate / bytes |
| 4kHDR12:cdng:lj | 28 | None | None | no anchor |
| 4kHDR12:cdng:unc | 24 | 39 | 15 | derived: anchor write rate / bytes |
| 4kHDR12:mlv | 23 | 39 | 16 | derived: anchor write rate / bytes |
| 4kHDR16:cdng:lj | 15 | 15 | 0 | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:lj:log | 28 | None | None | no anchor |
| 4kHDR16:cdng:unc | 28 | 28 | 0 |  |
| 4kHDR16:cdng:unc:log | 24 | 25 | 1 | back end: gaps at 28 fps (measured) |
| 4kHDR16:mlv | 27 | 28 | 1 | derived: anchor write rate / bytes |
| 4kP:prores:422 | 43 | 29 | -14 | derived: ProRes HQ x pixels |
| 4kP:prores:hq | 29 | 29 | 0 | back end: gaps at 60 fps (measured) |
| 4kP:prores:hq:arri_logc4 | 42 | 29 | -13 | derived: ProRes HQ x pixels |
| 4kSDR10:cdng:lj | 43 | None | None | no anchor |
| 4kSDR10:cdng:unc | 45 | 47 | 2 | derived: anchor write rate / bytes |
| 4kSDR10:lossydng:3to1 | 35 | 45 | 10 | derived: lossy x bytes |
| 4kSDR10:lossydng:5to1 | 44 | 45 | 1 | derived: lossy x bytes |
| 4kSDR10:mlv | 11 | 47 | 36 | derived: anchor write rate / bytes |
| 4kSDR12:cdng:lj | 41 | None | None | no anchor |
| 4kSDR12:cdng:unc | 38 | 39 | 1 | back end: gaps at 60 fps (measured) |
| 4kSDR12:lossydng:3to1 | 37 | 37 | 0 |  |
| 4kSDR12:lossydng:5to1 | 41 | 37 | -4 | derived: lossy x bytes |
| crop4k3SDR12:cdng:lj | 53 | None | None | no anchor |
| crop4k3SDR12:lossydng:3to1 | 41 | 50 | 9 | derived: lossy x bytes |
| crop4k3SDR12:lossydng:5to1 | 57 | 50 | -7 | derived: lossy x bytes |
| crop4k3SDR12:mlv | 35 | 52 | 17 | derived: anchor write rate / bytes |
