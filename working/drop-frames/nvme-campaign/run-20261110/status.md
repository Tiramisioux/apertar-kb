NIGHT OVER (all stages of the night done): safe to read; report report-EST-05fb8f1-a.md
RESTORE OK
liveness: heartbeat 5 s old; runner pid 105070; night EST-05fb8f1-a started 14:29
take: -
progress: 214 takes this night (354 in the campaign), 4581 GB this night, 9568 GB in all of a 16000 GB budget
card: A936B442006AC2 ; free 637 GB; smart temp 47 C, written 80327876 units, critical_warning 0
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
| _aids1_fps27_20261122-140612 | EST-05fb8f1-a | 27.0 | 900 | drop | 12.0 | 1 | 11.7 | 0 |  |  | drop |
| _aids1_fps26_20261122-140649 | EST-05fb8f1-a | 26.0 | 900 | pass_15min | 900.3 | 0 |  | 0 |  |  | clean |
| _aids1_fps45_20261122-142605 | EST-05fb8f1-a | 45.0 | 900 | drop | 1.5 | 7 | 1.3 | 0 |  |  | drop |
| _aids1_fps44_20261122-142632 | EST-05fb8f1-a | 44.0 | 900 | drop | 1.0 | 2 | 0.8 | 0 |  |  | drop |
| _aids1_fps25_20261122-142911 | EST-05fb8f1-a | 25.0 | 900 | pass_15min | 900.4 | 0 |  | 0 | 0 | 96.4 | clean |
| _aids1_fps24_20261122-145120 | EST-05fb8f1-a | 24.0 | 900 | pass_15min | 900.3 | 0 |  | 0 | 0 | 91.7 | clean |
| _aids1_fps14_20261122-151258 | EST-05fb8f1-a | 14.0 | 900 | pass_15min | 900.1 | 0 |  | 0 | 0 | 28.8 | clean |
| _aids1_fps13_20261122-154038 | EST-05fb8f1-a | 13.0 | 900 | pass_15min | 900.1 | 0 |  | 0 | 0 | 24.2 | clean |
| _aids1_fps41_20261122-155753 | EST-05fb8f1-a | 41.0 | 900 | drop | 1.0 | 4 | 0.8 | 0 |  |  | drop |
| _aids1_fps40_20261122-155819 | EST-05fb8f1-a | 40.0 | 900 | drop | 1.0 | 3 | 0.8 | 0 |  |  | drop |

## Decisions (tail)

    2026-11-22 15:40:38 [EST-05fb8f1-a] cooldown 1: 601 s; NVMe 50.9 -> 40.9 C, Pi 52.9 -> 49.6 C
    2026-11-22 15:56:46 [EST-05fb8f1-a] merge of cDNG_26-11-22_C0001_15410112: 11702 frames, 3 parts, 24 s (2.07 ms per frame), first ETA error -27.1 %, intact; merge off again: True
    2026-11-22 15:56:46 [EST-05fb8f1-a] EST-05fb8f1-a P6-warmfix-t0l0w1a1a1 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 13 fps, 900 s: pass_15min (900.1 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-22 15:56:46 [EST-05fb8f1-a] EST P6b 4kHDR16:cdng:lj:log at 13: pass_15min after 900.1 s
    2026-11-22 15:56:47 [EST-05fb8f1-a] deleted cDNG_26-11-22_C0002_14514417: 21607 frames in 0.9 s (warm, budget 0 s)
    2026-11-22 15:58:19 [EST-05fb8f1-a] EST-05fb8f1-a P6-warmfix-t0l0w1a1a1 4kP_unc_log0_tdn0_lock0_trim1_web1_prores-hq-arri_logc4_aud1_aids1 at 41 fps, 900 s: drop (1.0 s, dropped 4, first drop 0.8, gap 0, boundary )
    2026-11-22 15:58:19 [EST-05fb8f1-a] EST P6b 4kP:prores:hq:arri_logc4 at 41: drop after 1.0 s
    2026-11-22 15:58:40 [EST-05fb8f1-a] EST-05fb8f1-a P6-warmfix-t0l0w1a1a1 4kP_unc_log0_tdn0_lock0_trim1_web1_prores-hq-arri_logc4_aud1_aids1 at 40 fps, 900 s: drop (1.0 s, dropped 3, first drop 0.8, gap 0, boundary )
    2026-11-22 15:58:40 [EST-05fb8f1-a] EST P6b 4kP:prores:hq:arri_logc4 at 40: drop after 1.0 s
    2026-11-22 15:58:40 [EST-05fb8f1-a] EST outputs: /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate-table.csv, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate.md, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/selftest.md
    2026-11-22 15:58:40 [EST-05fb8f1-a] stage EST-05fb8f1-a done
    2026-11-22 15:59:15 [EST-05fb8f1-a] RESTORE OK
