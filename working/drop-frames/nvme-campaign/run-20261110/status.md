NIGHT OVER (fault: fault:   | unconfirmed: no counter or context pointed to a cause): safe to read; report report-EST.md
RESTORE OK
liveness: heartbeat 52 s old; runner pid 241182; night EST started 09:02
take: -
progress: 58 takes this night (137 in the campaign), 330 GB this night, 4975 GB in all of a 16000 GB budget
card: A936B442006AC2 ; free 219 GB; smart temp 44 C, written 69445527 units, critical_warning 0
voids 0, audio faults 0 this night; STOP: fault: fault:   | unconfirmed: no counter or context pointed to a cause

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
| _aids1_fps60_20261111-093849 | EST | 60.0 | 60 | buffer_full | 12.0 | 0 |  | 0 | 0 |  | drop |
| _aids1_fps60_20261111-093936 | EST | 60.0 | 60 | ab_clean | 60.0 | 0 |  | 0 | 0 |  | drop |
| _aids1_fps30_20261111-094115 | EST | 30.0 | 60 | buffer_full | 8.5 | 4 | 2.7 | 0 | 0 |  | drop |
| _aids1_fps60_20261111-094220 | EST | 60.0 | 60 | ab_dropped | 60.1 | 946 | 0.7 | 0 |  |  | drop |
| _aids1_fps30_20261111-094358 | EST | 30.0 | 60 | buffer_full | 9.0 | 8 | 3.7 | 0 |  |  | drop |
| _aids1_fps30_20261111-094501 | EST | 30.0 | 60 | ab_dropped | 60.1 | 428 | 1.7 | 0 | 0 |  | drop |
| _aids1_fps60_20261111-094655 | EST | 60.0 | 60 | ab_clean | 60.0 | 0 |  | 0 |  |  | drop |
| _aids1_fps60_20261111-094833 | EST | 60.0 | 60 | setup_mismatch |  |  |  |  |  |  | skip |
| _aids1_fps60_20261111-094859 | EST | 60.0 | 60 | ab_clean | 60.0 | 0 |  | 0 |  |  | drop |
| _aids1_fps60_20261111-095041 | EST | 60.0 | 60 | fault | 8.0 | 0 |  | 0 |  |  | stop |

## Decisions (tail)

    2026-11-11 09:39:35 [EST] EST P1-cap-t0l0w1a1a1-r1 4kSDR10_lossless_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 60 fps, 60 s: buffer_full (12.0 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-11 09:41:15 [EST] EST P1-cap-t0l0w1a1a1-r1 2kSDR12_lossless_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 60 fps, 60 s: ab_clean (60.0 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-11 09:42:06 [EST] EST P1-cap-t0l0w1a1a1-r1 4kHDR16_lossless_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 30 fps, 60 s: buffer_full (8.5 s, dropped 4, first drop 2.7, gap 0, boundary 0)
    2026-11-11 09:43:40 [EST] EST P1-cap-t0l0w1a1a1-r1 4kP_unc_log0_tdn0_lock0_trim1_web1_prores-hq-arri_logc4_aud1_aids1 at 60 fps, 60 s: ab_dropped (60.1 s, dropped 946, first drop 0.7, gap 0, boundary )
    2026-11-11 09:44:42 [EST] EST P1-cap-t0l0w1a1a1-r1 4kHDR12_unc_log0_tdn0_lock0_trim1_web1_mlv_aud1_aids1 at 30 fps, 60 s: buffer_full (9.0 s, dropped 8, first drop 3.7, gap 0, boundary )
    2026-11-11 09:46:36 [EST] EST P1-cap-t0l0w1a1a1-r1 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1 at 30 fps, 60 s: ab_dropped (60.1 s, dropped 428, first drop 1.7, gap 0, boundary 0)
    2026-11-11 09:48:15 [EST] EST P1-cap-t0l0w1a1a1-r1 2kP_unc_log0_tdn0_lock0_trim1_web1_prores-proxy_aud1_aids1 at 60 fps, 60 s: ab_clean (60.0 s, dropped 0, first drop , gap 0, boundary )
    2026-11-11 09:48:51 [EST] EST P1-cap-t0l0w1a1a1-r1 2kSDR12_unc_log0_tdn0_lock0_trim1_web1_fpf5000_lossydng-5to1_aud1_aids1 at 60 fps, 60 s: setup_mismatch (None s, dropped None, first drop None, gap None, boundary None)
    2026-11-11 09:50:19 [EST] EST P1-cap-t0l0w1a1a1-r1 2kP_unc_log0_tdn0_lock0_trim1_web1_prores-hq_aud1_aids1 at 60 fps, 60 s: ab_clean (60.0 s, dropped 0, first drop , gap 0, boundary )
    2026-11-11 09:51:24 [EST] EST P1-cap-t0l0w1a1a1-r1 4kSDR12_unc_log0_tdn0_lock0_trim1_web1_mlv_aud1_aids1 at 60 fps, 60 s: fault (8.0 s, dropped 0, first drop , gap 0, boundary )
    2026-11-11 09:51:24 [EST] EST outputs: /home/pi/longtakes/nvme-20261110/est/estimate-table.csv, /home/pi/longtakes/nvme-20261110/est/estimate.md, /home/pi/longtakes/nvme-20261110/est/selftest.md
    2026-11-11 09:52:18 [EST] RESTORE OK
