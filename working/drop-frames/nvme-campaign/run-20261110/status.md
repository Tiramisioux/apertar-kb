NIGHT OVER (all stages of the night done): safe to read; report report-EST-05fb8f1-a.md
RESTORE OK
liveness: heartbeat 3 s old; runner pid 21896; night EST-05fb8f1-a started 19:50
take: -
progress: 243 takes this night (383 in the campaign), 7419 GB this night, 12406 GB in all of a 16000 GB budget
card: A936B442006AC2 ; free 195 GB; smart temp 57 C, written 85392612 units, critical_warning 0
voids 0, audio faults 0 this night

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
| _aids1_fps44_20261123-000455 | EST-05fb8f1-a | 44.0 | 900 | buffer_full | 178.6 | 0 |  | 0 | 0 | 10.0 | drop |
| _aids1_fps40_20261123-001840 | EST-05fb8f1-a | 40.0 | 60 | drop | 1.0 | 7 | 0.7 | 0 | 0 |  | drop |
| _aids1_fps36_20261123-001909 | EST-05fb8f1-a | 36.0 | 60 | drop | 1.0 | 2 | 0.7 | 0 | 0 |  | drop |
| _aids1_fps30_20261123-001937 | EST-05fb8f1-a | 30.0 | 60 | drop | 5.0 | 2 | 4.7 | 0 | 0 |  | drop |
| _aids1_fps37_20261123-002017 | EST-05fb8f1-a | 37.0 | 60 | drop | 2.0 | 7 | 1.7 | 0 | 0 |  | drop |
| _aids1_fps33_20261123-002047 | EST-05fb8f1-a | 33.0 | 60 | drop | 3.0 | 3 | 2.7 | 0 | 0 |  | drop |
| _aids1_fps30_20261123-002117 | EST-05fb8f1-a | 30.0 | 60 | drop | 8.0 | 1 | 7.7 | 0 | 0 |  | drop |
| _aids1_fps24_20261123-002200 | EST-05fb8f1-a | 24.0 | 60 | pass_capped_60s | 60.0 | 0 |  | 0 | 0 |  | clean |
| _aids1_fps24_20261123-002340 | EST-05fb8f1-a | 24.0 | 900 | drop | 711.6 | 3 | 711.2 | 0 | 0 | 63.5 | drop |
| _aids1_fps23_20261123-003936 | EST-05fb8f1-a | 23.0 | 900 | pass_15min | 900.2 | 0 |  | 0 | 0 | 90.8 | clean |

## Decisions (tail)

    2026-11-23 00:37:22 [EST-05fb8f1-a] EST P8 4kHDR16:cdng:unc at 24, 15 min: drop after 711.6 s
    2026-11-23 00:37:22 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0007_23412420: 47 frames in 0.0 s (warm, budget 0 s)
    2026-11-23 00:37:22 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0008_23415322: 74 frames in 0.0 s (warm, budget 0 s)
    2026-11-23 00:37:22 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0009_23422408: 122 frames in 0.0 s (warm, budget 0 s)
    2026-11-23 00:37:26 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0010_23430410: 1440 frames in 4.0 s (warm, budget 0 s)
    2026-11-23 00:38:31 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0011_23443920: 21607 frames in 63.6 s (warm, budget 0 s)
    2026-11-23 00:56:56 [EST-05fb8f1-a] merge of cDNG_26-11-23_C0012_00400002: 20703 frames, 5 parts, 91 s (4.39 ms per frame), first ETA error -27.1 %, intact; merge off again: True
    2026-11-23 00:56:56 [EST-05fb8f1-a] EST-05fb8f1-a P8-long15-t0l0w1a1a1 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 23 fps, 900 s: pass_15min (900.2 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-23 00:56:56 [EST-05fb8f1-a] EST P8 4kHDR16:cdng:unc at 23, 15 min: pass_15min after 900.2 s
    2026-11-23 00:56:56 [EST-05fb8f1-a] EST outputs: /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate-table.csv, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate.md, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/selftest.md
    2026-11-23 00:56:56 [EST-05fb8f1-a] stage EST-05fb8f1-a done
    2026-11-23 00:57:39 [EST-05fb8f1-a] RESTORE OK
