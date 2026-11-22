# Measured limits per cell (NVMe, from the take records only)

Source: `results.csv` of the NVMe run folder (310 takes counted). Reference levers: TDN off, phase lock off, WebUI client on, audio on, aids on, split 5000, cDNG. "Longest measured" = the longest duration at which any take of the cell was clean; the fps is the highest clean fps at that duration or longer. The next column lists the higher fps that were tried and how long each stayed clean before its first drop. A take shorter than its tier is not counted for it.

| Mode | Compression | Log | Longest measured clean | Highest clean fps | Higher fps: how long it stayed clean (best of its takes) | Takes behind it |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16 | lossless_jpeg |  | 1 min | 30 | not tried above | 1 clean, 0 failed |
| 2kHDR16 | lossless_jpeg | on | 1 min | 30 | not tried above | 2 clean, 0 failed |
| 2kHDR16 | none |  | 1 min | 30 | not tried above | 7 clean, 0 failed |
| 2kHDR16 | none | on | 1 min | 30 | not tried above | 2 clean, 0 failed |
| 2kP | none |  | 1 min | 60 | not tried above | 6 clean, 1 failed |
| 2kSDR12 | lossless_jpeg |  | 1 min | 60 | not tried above | 8 clean, 0 failed |
| 2kSDR12 | none |  | 1 min | 60 | not tried above | 6 clean, 0 failed |
| 4kHDR12 | lossless_jpeg |  | none clean | - | 30 (shortest failure 60 s) | 3 |
| 4kHDR12 | none |  | none clean | - | 25 (shortest failure 2 s) | 20 |
| 4kHDR16 | lossless_jpeg |  | none clean | - | 25 (shortest failure 7 s) | 11 |
| 4kHDR16 | lossless_jpeg | on | none clean | - | 25 (shortest failure 4 s) | 9 |
| 4kHDR16 | none |  | 5 min | 27 (28 held only 0 min, 1 min, 3 min) | 28: clean 2.7 min, 30: clean 22 s | 16 clean, 17 failed |
| 4kHDR16 | none | on | 5 min | 25 | 28: clean 5 s, 30: clean 2 s | 3 clean, 10 failed |
| 4kP | none |  | 1 min | 60 | not tried above | 7 clean, 19 failed |
| 4kSDR10 | lossless_jpeg |  | none clean | - | 60 (shortest failure 11 s) | 3 |
| 4kSDR10 | none |  | none clean | - | 60 (shortest failure 8 s) | 10 |
| 4kSDR12 | lossless_jpeg |  | 5 min | 43 | 59: clean 13 s, 60: clean 11 s | 8 clean, 6 failed |
| 4kSDR12 | none |  | 15 min | 37 (44 held only 1 min) | 38: clean 13.3 min, 39: clean 12.5 min, 60: clean 16 s | 14 clean, 26 failed |
| crop4k3SDR12 | lossless_jpeg |  | 1 min | 60 | not tried above | 2 clean, 0 failed |
| crop4k3SDR12 | none |  | 1 min | 60 | not tried above | 1 clean, 4 failed |

## Each lever against the reference (same cell, one lever away)

| Mode | Compression | Log | Lever state (tdn, lock, web, audio, aids) | Longest clean | Highest clean fps | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16 | lossless_jpeg | on | TDN lock no web no aids | 3 min | 24 | 1 min, 30 fps |
| 2kP | none |  | TDN no audio no aids | 3 min | 60 | 1 min, 60 fps |
| 2kP | none |  | TDN lock no audio no aids | 3 min | 60 | 1 min, 60 fps |
| 2kSDR12 | lossless_jpeg |  | lock no web no aids | 3 min | 60 | 1 min, 60 fps |
| 2kSDR12 | none |  | TDN no web no audio no aids | 5 min | 60 | 1 min, 60 fps |
| 2kSDR12 | none |  | TDN lock | 5 min | 60 | 1 min, 60 fps |
| 4kHDR16 | none |  | no web no audio | 1 min | 28 | 5 min, 27 fps |
| 4kHDR16 | none |  | no web | 3 min | 28 | 5 min, 27 fps |
| 4kHDR16 | none |  | no audio no aids | 1 min | 28 | 5 min, 27 fps |
| 4kHDR16 | none |  | lock no web no audio no aids | 1 min | 28 | 5 min, 27 fps |
| 4kHDR16 | none |  | lock no web | 1 min | 28 | 5 min, 27 fps |
| 4kHDR16 | none |  | lock no audio | 1 min | 28 | 5 min, 27 fps |
| 4kSDR12 | lossless_jpeg |  | lock no web no audio no aids | 5 min | 44 | 5 min, 43 fps |
