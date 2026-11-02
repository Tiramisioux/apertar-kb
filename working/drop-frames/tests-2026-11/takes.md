# Takes, drop-frames tests 2026-11

One row per take; the 1 Hz logs and console outputs are on the Mac (session scratchpad), not in git. No interpretation here.

| take id | test | arm or cell | start (time) | start MemFree (MB) | lost per minute (min 1 / 2 / 3) | total lost / enqueued | whole-take deltas (pgsteal_kswapd / pgscan_direct / allocstall_movable / pageoutrun / kswapd_low_wmark_hit_quickly / pgmajfault / pswpin) | G1 IPC and cycles | peak NVMe write latency (ms per write) | CSI-2 VC0 OVLF total / seconds with OVLF > 0 | PSI memory some total delta (us) | drive fill and NVMe temp before / after | valid or void |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b1-warmup | B1 block 1 warm-up (unscored) | sync | 19:03:21 | 3022 | 0 / 6 / 11 | 17 / 4489 | 0 / 0 / 0 / 0 / 0 / 0 / 0 | IPC 1.45, cycles 806M/s | 56.86 ms (s 183, 44 writes); within 0-180 s: 14.14 ms (s 158, 2014 writes) | not logged | 46 | 2.4G (1 %) 38 C / 72G (8 %) 51 C | unscored |
| b1-u1-P1 | B1 block 1 unit 1 P1 | writer (unit 1, P1) | 19:14:20 | 622 | 96 / 123 / 136 (+2 after 180 s) | 357 / 4148 | 3713840 / 512 / 1 / 5877 / 2240 / 4 / 0 | missing (console: perf_event_open cycles: No such process) | 35.37 ms (s 182, 232 writes); within 0-180 s: 13.80 ms (s 174, 1957 writes) | 58 / 14 | 6426693 | 2.4G (1 %) 40 C / 67G (8 %) 50 C | valid; G1 missing (tid gone after the mode change) |
| b1-u1-P2 | B1 block 1 unit 1 P2 | writer (unit 1, P2) | 19:18:00 | 346 | 1 / 22 / 27 | 50 / 4457 | 3442560 / 512 / 1 / 4911 / 1912 / 0 / 0 | missing (console: perf_event_open cycles: No such process) | 32.34 ms (s 182, 228 writes); within 0-180 s: 17.64 ms (s 48, 2434 writes) | 54 / 12 | 8423191 | 67G (8 %) 48 C / 136G (15 %) 57 C | valid; G1 missing (tid gone after the mode change) |
| b1-u2-P1 | B1 block 1 unit 2 P1 | writer (unit 2, P1) | 19:34:34 | 621 | 70 / 105 / 103 (+2 after 180 s) | 280 / 4224 | 3755840 / 2048 / 4 / 6505 / 2727 / 0 / 0 | IPC 1.41, cycles 769M/s | 31.22 ms (s 182, 225 writes); within 0-180 s: 15.31 ms (s 158, 1987 writes) | 24 / 7 | 6715682 | 2.4G (1 %) 40 C / 68G (8 %) 51 C | valid; deviation: NVMe 40.85 C at the unit start |
| b1-u2-P2 | B1 block 1 unit 2 P2 | writer (unit 2, P2) | 19:38:18 | 370 | 0 / 16 / 23 (+1 after 180 s) | 40 / 4467 | 3333312 / 1536 / 2 / 5575 / 1934 / 0 / 0 | IPC 1.40, cycles 825M/s | 31.30 ms (s 182, 233 writes); within 0-180 s: 23.21 ms (s 58, 2643 writes) | 51 / 11 | 8261293 | 68G (8 %) 48 C / 138G (15 %) 57 C | valid; deviation: NVMe 40.85 C at the unit start |

Notes on how the columns were computed (all from the files):

- Start MemFree is the console's `mem before` (unit takes) or the given fact (warm-up). Times are the Pi's local time and the console's `start`; the first line of the warm-up log and of the unit 1 logs carries the same second, the unit 2 logs start 3 s (P1) and 2 s (P2) later.
- Lost per minute is the difference of the cumulative `dropped=` counter in the 1 Hz log at 60, 120 and 180 s after its first line; total lost is the last `dropped=` of the log. Enqueued is the console's `enqueued=` (warm-up: the given fact).
- Minute marks are taken on the 1 Hz log (first line + 60, 120, 180 s). The console's own 60/120/180 s reads are a second or two apart from these, so its cumulative `dropped=` and minute deltas differ slightly from the log's (for example b1-u1-P1: log 96 / 219 / 355, console 97 / 220 / 356); the totals agree.
- One line of each 1 Hz log (the 182nd line, index 181) has `dropped=None`; the previous value is used for it. It lies after 180 s and does not touch the minute marks or the totals.
- Whole-take deltas are last minus first line of the 1 Hz log for the unit takes and the warm-up; for the four unit takes they equal the console's `whole take:` line.
- Peak NVMe write latency is the maximum over 1-s intervals of delta `ticks_ms` / delta `writes`, intervals with >= 10 writes only; the second index (0 = first line) and the write count of that interval are in brackets. The first figure covers the whole log; the second only intervals ending at or before 180 s.
- CSI-2: the `vc0=OVLF/LEN/UNMATCHED/INACTIVE` field of each second; the table counts the OVLF number. The warm-up log has no `csi2` field.
- PSI is the delta of `psi some total` between the first and last line of the log.
- Drive fill and temperature are the console's `drive:` (before) and `drive after:` (after) lines; warm-up from the given facts.

### b1-warmup

Minutes are 0-60, 60-120 and 120-180 s after the first log line; "after 180 s" is the rest of the log (10 s). Mean NVMe ms/write is delta `ticks_ms` / delta `writes` over the interval. MemFree min is the lowest 1 Hz sample in the interval. CameraManager is tid 2611 (largest run-time delta of the CameraManager threads); its run ms per s is the delta of its run_ns over the interval. This log has no `csi2` field.

| minute | lost in that minute | pgsteal_kswapd delta | pgscan_direct delta | MemFree min (MB) | mean NVMe ms/write | CSI-2 OVLF | CameraManager run ms per s (mean) |
|---|---|---|---|---|---|---|---|
| 1 (0-60 s) | 0 | 0 | 0 | 2114 | 9.24 | - | 436.2 |
| 2 (60-120 s) | 6 | 0 | 0 | 2105 | 9.31 | - | 444.3 |
| 3 (120-180 s) | 11 | 0 | 0 | 1806 | 10.43 | - | 441.3 |
| after 180 s | 0 | 0 | 0 | 2271 | 12.69 | - | 353.9 |

### b1-u1-P1

Minutes are 0-60, 60-120 and 120-180 s after the first log line; "after 180 s" is the rest of the log (9 s). Mean NVMe ms/write is delta `ticks_ms` / delta `writes` over the interval. MemFree min is the lowest 1 Hz sample in the interval. CameraManager is tid 8049 (largest run-time delta of the CameraManager threads); its run ms per s is the delta of its run_ns over the interval.

| minute | lost in that minute | pgsteal_kswapd delta | pgscan_direct delta | MemFree min (MB) | mean NVMe ms/write | CSI-2 OVLF | CameraManager run ms per s (mean) |
|---|---|---|---|---|---|---|---|
| 1 (0-60 s) | 96 | 1337392 | 0 | 40 | 9.37 | 24 | 417.8 |
| 2 (60-120 s) | 123 | 1242944 | 0 | 18 | 9.47 | 14 | 415.2 |
| 3 (120-180 s) | 136 | 1112960 | 512 | 45 | 10.73 | 20 | 411.4 |
| after 180 s | 2 | 20544 | 0 | 216 | 15.26 | 0 | 357.8 |

### b1-u1-P2

Minutes are 0-60, 60-120 and 120-180 s after the first log line; "after 180 s" is the rest of the log (9 s). Mean NVMe ms/write is delta `ticks_ms` / delta `writes` over the interval. MemFree min is the lowest 1 Hz sample in the interval. CameraManager is tid 9839 (largest run-time delta of the CameraManager threads); its run ms per s is the delta of its run_ns over the interval.

| minute | lost in that minute | pgsteal_kswapd delta | pgscan_direct delta | MemFree min (MB) | mean NVMe ms/write | CSI-2 OVLF | CameraManager run ms per s (mean) |
|---|---|---|---|---|---|---|---|
| 1 (0-60 s) | 1 | 1229120 | 512 | 59 | 12.12 | 14 | 449.5 |
| 2 (60-120 s) | 22 | 1134336 | 0 | 32 | 12.43 | 22 | 457.8 |
| 3 (120-180 s) | 27 | 1055104 | 0 | 23 | 12.66 | 18 | 458.0 |
| after 180 s | 0 | 24000 | 0 | 88 | 14.00 | 0 | 333.2 |

### b1-u2-P1

Minutes are 0-60, 60-120 and 120-180 s after the first log line; "after 180 s" is the rest of the log (9 s). Mean NVMe ms/write is delta `ticks_ms` / delta `writes` over the interval. MemFree min is the lowest 1 Hz sample in the interval. CameraManager is tid 17125 (largest run-time delta of the CameraManager threads); its run ms per s is the delta of its run_ns over the interval.

| minute | lost in that minute | pgsteal_kswapd delta | pgscan_direct delta | MemFree min (MB) | mean NVMe ms/write | CSI-2 OVLF | CameraManager run ms per s (mean) |
|---|---|---|---|---|---|---|---|
| 1 (0-60 s) | 70 | 1354048 | 0 | 18 | 9.36 | 17 | 433.1 |
| 2 (60-120 s) | 105 | 1253312 | 1536 | 23 | 9.64 | 4 | 429.3 |
| 3 (120-180 s) | 103 | 1121984 | 512 | 21 | 11.01 | 3 | 426.9 |
| after 180 s | 2 | 26496 | 0 | 86 | 15.36 | 0 | 353.7 |

### b1-u2-P2

Minutes are 0-60, 60-120 and 120-180 s after the first log line; "after 180 s" is the rest of the log (9 s). Mean NVMe ms/write is delta `ticks_ms` / delta `writes` over the interval. MemFree min is the lowest 1 Hz sample in the interval. CameraManager is tid 18961 (largest run-time delta of the CameraManager threads); its run ms per s is the delta of its run_ns over the interval.

| minute | lost in that minute | pgsteal_kswapd delta | pgscan_direct delta | MemFree min (MB) | mean NVMe ms/write | CSI-2 OVLF | CameraManager run ms per s (mean) |
|---|---|---|---|---|---|---|---|
| 1 (0-60 s) | 0 | 1198912 | 1024 | 54 | 12.39 | 21 | 454.3 |
| 2 (60-120 s) | 16 | 1094208 | 512 | 27 | 12.45 | 18 | 460.1 |
| 3 (120-180 s) | 23 | 1016832 | 0 | 44 | 12.88 | 12 | 456.0 |
| after 180 s | 1 | 23360 | 0 | 43 | 14.09 | 0 | 344.3 |
