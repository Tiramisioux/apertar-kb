# Self-test check (plan section 6.4)

P0 alone (+ the drive profile) against the full fit: 62 % within +-1 fps (goal >= 90 %).

| spec | full fit | from P0 | error | how |
| --- | --- | --- | --- | --- |
| 4kHDR12:cdng:unc | 24 | 39 | 15 | derived: anchor write rate / bytes |
| 4kHDR16:cdng:lj | 15 | 15 | 0 | back end: gaps at 30 fps (measured) |
| 4kHDR16:cdng:unc:log | 24 | 25 | 1 | back end: gaps at 28 fps (measured) |
| 4kP:prores:hq | 29 | 29 | 0 | back end: gaps at 60 fps (measured) |
| 4kSDR12:cdng:unc | 39 | 39 | 0 | back end: gaps at 60 fps (measured) |
| 4kSDR12:lossydng:3to1 | 37 | 37 | 0 |  |
| 4kSDR12:lossydng:5to1 | 41 | 37 | -4 | derived: lossy x bytes |
| crop4k3SDR12:lossydng:3to1 | 41 | 50 | 9 | derived: lossy x bytes |
