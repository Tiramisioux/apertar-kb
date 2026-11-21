NIGHT OVER (stopped_by_signal: stopped by SIGTERM while waiting at the gate): safe to read; report report-EST-05fb8f1-a.md
RESTORE OK
liveness: heartbeat 32 s old; runner pid 7664; night EST-05fb8f1-a started 18:39
take: -
progress: 194 takes this night (334 in the campaign), 3066 GB this night, 8053 GB in all of a 16000 GB budget
card: A936B442006AC2 ; free 445 GB; smart temp 59 C, written 77083680 units, critical_warning 0
voids 0, audio faults 0 this night; STOP: stopped_by_signal: stopped by SIGTERM while waiting at the gate

## Arms

- 4kHDR12: edge=30, top=30; cells 25:out 26:out 27:out 28:out 29:out 30:out
- 4kHDR12@cap-imx283-probe: edge=30, top=25
- 4kHDR16: S4={'25': 'drop at  s ()', '26': 'drop at 621.0 s (drive state (ticks per write 11.89 -> 22.70))', '27': 'drop at 708.1 s (drive state (ticks per write 14.58 -> 23.67))'}, best=27, edge=28, top=30; cells 27:carried 28:out
- 4kHDR16/lossless+log: preroll=ok: 5.0 s at 30 fps (measured 28.7), 138 frames, 1.5 GB written and deleted; cells 25:out 26:out 27:out
- 4kHDR16/lossless@25: ; cells 25:out
- 4kHDR16/unc+log@25: ; cells 25:carried
- 4kSDR12: S4={'37': 'clean', '38': 'drop at  s ()'}, best=38, edge=39, meter_capacity=40.91, s4_pass=37, top=60; cells 38:carried 39:out
- 4kSDR12/lossless: best=43, preroll=ok: 5.0 s at 60 fps (measured 60.0), 299 frames, 1.6 GB written and deleted; cells 43:carried 59:out
- 4kSDR12/lossless@cap-imx283-probe: best=30, preroll=ok: 5.0 s at 30 fps (measured 30.0), 149 frames, 0.9 GB written and deleted; cells 29:carried 30:carried
- 4kSDR12@cap-imx283-probe: best=30, edge=29, meter_capacity=30.0, top=30; cells 29:carried 30:carried

## Last 10 takes

| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| _aids1_fps60_20261121-180944 | EST-05fb8f1-a | 60.0 | 60 | ab_clean | 60.0 | 0 |  | 0 |  |  | drop |
| _aids1_fps28_20261121-181130 | EST-05fb8f1-a | 28.0 | 60 | ab_clean | 60.1 | 0 |  | 0 | 0 |  | drop |
| _aids1_fps30_20261121-181326 | EST-05fb8f1-a | 30.0 | 60 | ab_clean | 60.0 | 0 |  | 0 | 0 |  | drop |
| _aids1_fps28_20261121-181522 | EST-05fb8f1-a | 28.0 | 60 | ab_dropped | 60.1 | 120 | 3.7 | 0 | 0 |  | drop |
| _aids1_fps25_20261121-181658 | EST-05fb8f1-a | 25.0 | 60 | ab_dropped | 60.0 | 87 | 4.8 | 0 | 0 |  | drop |
| _aids1_fps27_20261121-184149 | EST-05fb8f1-a | 27.0 | 900 | drop | 432.3 | 1 | 431.9 | 0 | 0 | 28.8 | drop |
| _aids1_fps26_20261121-185325 | EST-05fb8f1-a | 26.0 | 900 | drop | 788.5 | 1 | 788.0 | 0 | 0 | 93.6 | drop |
| _aids1_fps39_20261121-191034 | EST-05fb8f1-a | 39.0 | 900 | buffer_full | 750.2 | 0 |  | 0 | 0 | 195.0 | drop |
| _aids1_fps38_20261121-192917 | EST-05fb8f1-a | 38.0 | 900 | buffer_full | 268.7 | 0 |  | 0 | 0 | 23.1 | drop |
| _aids1_fps40_20261121-193452 | EST-05fb8f1-a | 40.0 | 900 | stopped_by_signal |  |  |  |  |  |  | stop |

## Decisions (tail)

    2026-11-21 19:09:21 [EST-05fb8f1-a] deleted cDNG_26-11-21_18172201_C0024_cam0: 1407 frames in 0.4 s (cold, budget 0 s)
    2026-11-21 19:09:32 [EST-05fb8f1-a] deleted cDNG_26-11-21_18421310_C0001_cam0: 11669 frames in 10.7 s (warm, budget 0 s)
    2026-11-21 19:27:03 [EST-05fb8f1-a] merge of cDNG_26-11-21_19110216_C0001_cam0: 29045 frames, 6 parts, 195 s (6.71 ms per frame), first ETA error -28.1 %, intact; merge off again: True
    2026-11-21 19:27:03 [EST-05fb8f1-a] EST-05fb8f1-a P6-warm0-t0l0w1a1a1 4kSDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 39 fps, 900 s: buffer_full (750.2 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-21 19:27:03 [EST-05fb8f1-a] EST P6 4kSDR12:cdng:unc at 39 (estimate 39): buffer_full after 750.2 s
    2026-11-21 19:28:13 [EST-05fb8f1-a] deleted cDNG_26-11-21_18534821_C0002_cam0: 20498 frames in 70.1 s (warm, budget 0 s)
    2026-11-21 19:34:51 [EST-05fb8f1-a] merge of cDNG_26-11-21_19294104_C0002_cam0: 10046 frames, 3 parts, 23 s (2.30 ms per frame), first ETA error -43.1 %, intact; merge off again: True
    2026-11-21 19:34:51 [EST-05fb8f1-a] EST-05fb8f1-a P6-warm-1-t0l0w1a1a1 4kSDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 38 fps, 900 s: buffer_full (268.7 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-21 19:34:51 [EST-05fb8f1-a] EST P6 4kSDR12:cdng:unc at 38 (estimate 39): buffer_full after 268.7 s
    2026-11-21 22:43:21 [EST-05fb8f1-a] EST-05fb8f1-a P6-warm0-t0l0w1a1a1 4kSDR12_lossless_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 40 fps, 900 s: stopped_by_signal (None s, dropped None, first drop None, gap None, boundary None)
    2026-11-21 22:43:21 [EST-05fb8f1-a] EST outputs: /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate-table.csv, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate.md, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/selftest.md
    2026-11-21 22:43:48 [EST-05fb8f1-a] RESTORE OK
