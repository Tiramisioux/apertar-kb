# Measured limits per cell (NVMe, from the take records only)

Source: `results.csv` of the NVMe run folder (353 takes counted). Reference levers: TDN off, phase lock off, WebUI client on, audio on, aids on, split 5000, cDNG. "Longest measured" = the longest duration at which any take of the cell was clean; the fps is the highest clean fps at that duration or longer. The next column lists the higher fps that were tried and how long each stayed clean before its first drop. A take shorter than its tier is not counted for it.

| Mode | Compression | Log | Longest measured clean | Highest clean fps | Higher fps: how long it stayed clean (best of its takes) | Takes behind it |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16 | lossless_jpeg |  | 1 min | 30 | not tried above | 1 clean, 0 failed |
| 2kHDR16 | lossless_jpeg | on | 1 min | 30 | not tried above | 2 clean, 0 failed |
| 2kHDR16 | none |  | 1 min | 30 | not tried above | 7 clean, 0 failed |
| 2kHDR16 | none | on | 1 min | 30 | not tried above | 2 clean, 0 failed |
| 2kP | prores-422 |  | 1 min | 60 | not tried above | 1 clean, 0 failed |
| 2kP | prores-hq |  | 1 min | 60 | not tried above | 2 clean, 0 failed |
| 2kP | prores-lt |  | 1 min | 60 | not tried above | 1 clean, 1 failed |
| 2kP | prores-proxy |  | 1 min | 60 | not tried above | 2 clean, 0 failed |
| 2kSDR12 | lossless_jpeg |  | 1 min | 60 | not tried above | 8 clean, 0 failed |
| 2kSDR12 | lossydng-3to1 |  | 1 min | 60 | not tried above | 1 clean, 0 failed |
| 2kSDR12 | lossydng-5to1 |  | 1 min | 60 | not tried above | 1 clean, 0 failed |
| 2kSDR12 | none |  | 1 min | 60 | not tried above | 4 clean, 0 failed |
| 4kHDR12 | lossless_jpeg |  | none clean | - | 30 (shortest failure 60 s) | 3 |
| 4kHDR12 | none |  | 15 min | 24 | 25: clean 1.5 min, 26: clean 8 s, 27: clean 5 s, 28: clean 3 s | 2 clean, 23 failed |
| 4kHDR16 | lossless_jpeg |  | none clean | - | 25 (shortest failure 7 s) | 11 |
| 4kHDR16 | lossless_jpeg | on | 30 min | 14 | 25: clean 5 s, 26: clean 10 s, 27: clean 4 s, 30: clean 2 s | 3 clean, 9 failed |
| 4kHDR16 | none |  | 15 min | 23 (28 held only 0 min, 1 min, 3 min) | 24: clean 11.9 min, 25: clean 12.6 min, 26: clean 13.1 min, 27: clean 11.8 min | 18 clean, 18 failed |
| 4kHDR16 | none | on | 30 min | 25 | 28: clean 5 s, 30: clean 2 s | 6 clean, 10 failed |
| 4kP | h264-1920x1080 |  | 1 min | 60 | not tried above | 7 clean, 0 failed |
| 4kP | h264-2560x1440 |  | 15 min | 35 | 40: clean 1 s, 44: clean 1 s, 45: clean 1 s, 60: clean 1 s | 2 clean, 5 failed |
| 4kP | prores-422 |  | none clean | - | 60 (shortest failure 60 s) | 3 |
| 4kP | prores-hq |  | 15 min | 26 | 27: clean 12 s, 60: clean 1 s | 1 clean, 9 failed |
| 4kP | prores-hq-arri_logc4 | on | 15 min | 32 | 36: clean 3 s, 40: clean 1 s, 41: clean 1 s, 60: clean 1 s | 2 clean, 6 failed |
| 4kP | prores-lt |  | none clean | - | 60 (shortest failure 60 s) | 2 |
| 4kP | prores-proxy |  | none clean | - | 60 (shortest failure 60 s) | 2 |
| 4kSDR10 | lossless_jpeg |  | 1 min | 45 | 60: clean 14 s | 1 clean, 5 failed |
| 4kSDR10 | lossydng-3to1 |  | none clean | - | 60 (shortest failure 8 s) | 2 |
| 4kSDR10 | lossydng-5to1 |  | none clean | - | 60 (shortest failure 10 s) | 2 |
| 4kSDR10 | none |  | none clean | - | 60 (shortest failure 10 s) | 6 |
| 4kSDR12 | lossless_jpeg |  | 15 min | 40 (43 held only 3 min, 5 min) | 59: clean 13 s, 60: clean 11 s | 10 clean, 7 failed |
| 4kSDR12 | lossless_jpeg | on | none clean | - | 30 (shortest failure 1 s) | 3 |
| 4kSDR12 | lossydng-3to1 |  | 30 min | 37 | 60: clean 14 s | 3 clean, 7 failed |
| 4kSDR12 | lossydng-5to1 |  | none clean | - | 60 (shortest failure 8 s) | 2 |
| 4kSDR12 | none |  | 15 min | 37 (44 held only 1 min) | 38: clean 13.3 min, 39: clean 12.5 min, 60: clean 16 s | 14 clean, 18 failed |
| 4kSDR12 | none | on | none clean | - | 30 (shortest failure 2 s) | 3 |
| crop4k3SDR12 | lossless_jpeg |  | 1 min | 60 | not tried above | 2 clean, 0 failed |
| crop4k3SDR12 | lossydng-3to1 |  | none clean | - | 60 (shortest failure 28 s) | 1 |
| crop4k3SDR12 | lossydng-5to1 |  | 1 min | 60 | not tried above | 1 clean, 0 failed |
| crop4k3SDR12 | none |  | none clean | - | 60 (shortest failure 13 s) | 3 |

## Each lever against the reference (same cell, one lever away)

| Mode | Compression | Log | Lever state (tdn, lock, web, audio, aids) | Longest clean | Highest clean fps | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| 2kHDR16 | lossless_jpeg | on | TDN lock no web no aids | 3 min | 24 | 1 min, 30 fps |
| 2kP | prores-422 |  | TDN no audio no aids | 3 min | 60 | 1 min, 60 fps |
| 2kP | prores-proxy |  | TDN lock no audio no aids | 3 min | 60 | 1 min, 60 fps |
| 2kSDR12 | lossless_jpeg |  | lock no web no aids | 3 min | 60 | 1 min, 60 fps |
| 2kSDR12 | lossydng-5to1 |  | TDN lock | 5 min | 60 | 1 min, 60 fps |
| 2kSDR12 | none |  | TDN no web no audio no aids | 5 min | 60 | 1 min, 60 fps |
| 4kHDR16 | none |  | no web no audio | 1 min | 28 | 15 min, 23 fps |
| 4kHDR16 | none |  | no web | 3 min | 28 | 15 min, 23 fps |
| 4kHDR16 | none |  | no audio no aids | 1 min | 28 | 15 min, 23 fps |
| 4kHDR16 | none |  | lock no web no audio no aids | 1 min | 28 | 15 min, 23 fps |
| 4kHDR16 | none |  | lock no web | 1 min | 28 | 15 min, 23 fps |
| 4kHDR16 | none |  | lock no audio | 1 min | 28 | 15 min, 23 fps |
| 4kSDR12 | lossless_jpeg |  | lock no web no audio no aids | 5 min | 44 | 15 min, 40 fps |
