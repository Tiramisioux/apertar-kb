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

### Evening 3 (2026-11-04)

| take id | test | arm or cell | start (time) | start MemFree (MB) | lost per minute (min 1 / 2 / 3) | total lost / enqueued | whole-take deltas (pgsteal_kswapd / pgscan_direct / allocstall_movable / pageoutrun / kswapd_low_wmark_hit_quickly / pgmajfault / pswpin) | G1 IPC and cycles | peak NVMe write latency (ms per write) | CSI-2 VC0 OVLF total / seconds with OVLF > 0 | PSI memory some total delta (us) | drive fill and NVMe temp before / after | valid or void |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e3-warm-P1 | evening 3 warm-up (unscored) | N (TDN on) | 01:28:14 | 514 | 7 / 23 / 24 | 54 / 4453 | 61025 / 0 / 0 / 217 / 55 / 0 / 0 | IPC 1.44, cycles 803M/s | 34.27 ms (s 182, 233 writes); within 0-180 s: 13.14 ms (s 153, 1983 writes) | 11 / 11 | 14492 | 2.4G (1 %) 36 C / 72G (8 %) 49 C | unscored |
| e3-u1-P1 | evening 3 TDN block unit 1 P1 | N (TDN on) | 01:42:27 | 472 | 17 / 26 / 15 | 58 / 4448 | 64320 / 0 / 0 / 296 / 97 / 0 / 0 | IPC 1.43, cycles 809M/s | 36.58 ms (s 182, 225 writes); within 0-180 s: 15.01 ms (s 141, 2172 writes) | 5 / 5 | 15733 | 2.4G (1 %) 40 C / 72G (8 %) 52 C | valid |
| e3-u1-P2 | evening 3 TDN block unit 1 P2 | N (TDN on) | 01:46:14 | 666 | 6 / 19 / 14 | 39 / 4468 | 51059 / 0 / 0 / 364 / 116 / 0 / 0 | IPC 1.44, cycles 809M/s | 41.44 ms (s 182, 237 writes); within 0-180 s: 15.96 ms (s 97, 2052 writes) | 6 / 6 | 19752 | 72G (8 %) 48 C / 141G (16 %) 60 C | valid |
| e3-u2-P1 | evening 3 TDN block unit 2 P1 | F (TDN off) | 02:02:32 | 562 | 0 / 1 / 0 | 1 / 4512 | 68544 / 0 / 0 / 400 / 98 / 0 / 0 | IPC 1.58, cycles 744M/s | 47.04 ms (s 182, 171 writes); within 0-180 s: 16.77 ms (s 137, 1655 writes) | 0 / 0 | 21246 | 2.4G (1 %) 40 C / 73G (8 %) 62 C | valid |
| e3-u2-P2 | evening 3 TDN block unit 2 P2 | F (TDN off) | 02:06:18 | 734 | 0 / 0 / 0 | 0 / 4511 | 50560 / 0 / 0 / 288 / 70 / 0 / 0 | IPC 1.58, cycles 744M/s | 94.89 ms (s 182, 81 writes); within 0-180 s: 13.45 ms (s 86, 2065 writes) | 0 / 0 | 18045 | 73G (8 %) 54 C / 143G (16 %) 61 C | valid |
| e3-u3-P1 | evening 3 TDN block unit 3 P1 (void unit) | F (TDN off) | 02:22:42 | 447 | 0 / 1 / 0 | 1 / 4512 | 66880 / 0 / 0 / 400 / 111 / 0 / 0 | IPC 1.56, cycles 751M/s | 48.16 ms (s 182, 152 writes); within 0-180 s: 12.01 ms (s 137, 2018 writes) | 0 / 0 | 16257 | 2.4G (1 %) 40 C / 73G (8 %) 56 C | void (NVMe 40.85 C at the unit start) |
| e3-u3-P2 | evening 3 TDN block unit 3 P2 (void unit) | F (TDN off) | 02:26:29 | 770 | 0 / 0 / 0 | 0 / 4512 | 47744 / 0 / 0 / 337 / 73 / 0 / 0 | IPC 1.57, cycles 748M/s | 35.28 ms (s 182, 222 writes); within 0-180 s: 13.55 ms (s 43, 2064 writes) | 1 / 1 | 13733 | 73G (8 %) 50 C / 143G (16 %) 63 C | void (NVMe 40.85 C at the unit start) |
| e3-u3r-P1 | evening 3 TDN block unit 3 repeat (u3r) P1 | F (TDN off) | 02:43:34 | 448 | 0 / 1 / 1 | 2 / 4509 | 65088 / 0 / 0 / 429 / 163 / 0 / 0 | IPC 1.57, cycles 749M/s | 17.65 ms (s 181, 1565 writes); within 0-180 s: 12.90 ms (s 140, 1989 writes) | 0 / 0 | 21201 | 2.4G (1 %) 40 C / 73G (8 %) 60 C | valid |
| e3-u3r-P2 | evening 3 TDN block unit 3 repeat (u3r) P2 | F (TDN off) | 02:47:20 | 766 | 0 / 0 / 0 | 0 / 4513 | 47616 / 0 / 0 / 368 / 67 / 0 / 0 | IPC 1.56, cycles 752M/s | 79.69 ms (s 183, 157 writes); within 0-180 s: 15.03 ms (s 106, 2021 writes) | 0 / 0 | 15669 | 73G (8 %) 56 C / 143G (16 %) 63 C | valid |
| e3-u4-P1 | evening 3 TDN block unit 4 P1 | N (TDN on) | 03:03:51 | 441 | 36 / 40 / 39 | 115 / 4391 | 58624 / 0 / 0 / 323 / 157 / 0 / 0 | IPC 1.42, cycles 803M/s | 26.15 ms (s 182, 279 writes); within 0-180 s: 13.26 ms (s 174, 2006 writes) | 10 / 10 | 21006 | 2.4G (1 %) 40 C / 71G (8 %) 61 C | valid |
| e3-u4-P2 | evening 3 TDN block unit 4 P2 | N (TDN on) | 03:07:39 | 1224 | 28 / 40 / 47 (+1 after 180 s) | 116 / 4389 | 20732 / 0 / 0 / 278 / 43 / 0 / 0 | IPC 1.42, cycles 804M/s | 31.77 ms (s 182, 222 writes); within 0-180 s: 15.02 ms (s 31, 2010 writes) | 13 / 12 | 32795 | 71G (8 %) 56 C / 139G (15 %) 61 C | valid |
| e3-u27-P1 | evening 3 27-fps unit P1 | F (TDN off), 27 fps | 03:23:31 | 432 | 0 / 1 / 0 | 1 / 4874 | 289526 / 0 / 0 / 724 / 444 / 0 / 0 | IPC 1.48, cycles 857M/s | 33.53 ms (s 182, 232 writes); within 0-180 s: 17.41 ms (s 163, 2732 writes) | 0 / 0 | 425517 | 2.4G (1 %) 40 C / 78G (9 %) 63 C | valid |
| e3-u27-P2 | evening 3 27-fps unit P2 | F (TDN off), 27 fps | 03:27:18 | 681 | 0 / 0 / 1 | 1 / 4876 | 776402 / 0 / 0 / 1073 / 477 / 9 / 0 | IPC 1.39, cycles 913M/s | 24.49 ms (s 128, 3052 writes); within 0-180 s: 24.49 ms (s 128, 3052 writes) | 0 / 0 | 1861328 | 78G (9 %) 57 C / 154G (17 %) 65 C | valid |
| e3-s26-P1 | evening 3 sweep 26 fps | F (TDN off), 26 fps | 03:44:51 | 673 | 0 / 0 / 0 | 0 / 4693 | 153408 / 0 / 0 / 360 / 158 / 0 / 0 | IPC 1.50, cycles 817M/s | 24.26 ms (s 182, 333 writes); within 0-180 s: 21.20 ms (s 166, 2905 writes) | 0 / 0 | 217295 | 2.4G (1 %) 39 C / 76G (9 %) 62 C | valid |
| e3-s28-P1 | evening 3 sweep 28 fps | F (TDN off), 28 fps | 03:57:56 | 422 | 2 / 0 / 3 | 5 / 5054 | 576309 / 0 / 0 / 922 / 455 / 0 / 0 | IPC 1.44, cycles 916M/s | 35.30 ms (s 183, 230 writes); within 0-180 s: 21.73 ms (s 155, 3553 writes) | 0 / 0 | 1066241 | 2.4G (1 %) 40 C / 81G (9 %) 63 C | valid |

Note (evening 3): the first line of each P2 1 Hz log still carries the previous take's final `dropped=` (the counter resets a second later); the minute counts use 0 as the baseline when the first line is above the second. Computed by `w6_rows.py` (in `raw-2026-11-04.tgz`); target 2 rows follow.
