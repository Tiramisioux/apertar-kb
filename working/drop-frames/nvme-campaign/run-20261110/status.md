NIGHT OVER (stopped_by_signal: stopped by SIGTERM after 1 s: not a result): safe to read; report report-EST-05fb8f1-a.md
RESTORE OK
liveness: heartbeat 7 s old; runner pid 243213; night EST-05fb8f1-a started 17:47
take: -
progress: 171 takes this night (311 in the campaign), 1830 GB this night, 6817 GB in all of a 16000 GB budget
card: A936B442006AC2 ; free 195 GB; smart temp 36 C, written 74651143 units, critical_warning 0
voids 0, audio faults 0 this night; STOP: stopped_by_signal: stopped by SIGTERM after 1 s: not a result

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
| _aids0_fps24_20261121-161421 | EST-05fb8f1-a | 24.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 |  | clean |
| _aids0_fps60_20261121-161754 | EST-05fb8f1-a | 60.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 |  | clean |
| _aids0_fps60_20261121-162130 | EST-05fb8f1-a | 60.0 | 180 | pass_3min | 180.1 | 0 |  | 0 |  |  | clean |
| _aids1_fps23_20261121-162501 | EST-05fb8f1-a | 23.0 | 180 | drop | 5.0 | 1 | 4.8 | 0 | 0 |  | drop |
| _aids1_fps24_20261121-162553 | EST-05fb8f1-a | 24.0 | 180 | drop | 4.0 | 2 | 3.7 | 0 | 0 |  | drop |
| ladder_fps25_20261121-162632 | EST-05fb8f1-a | 25.0 | 60 | needs_human |  |  |  |  |  |  | stop |
| ladder_fps25_20261121-174719 | EST-05fb8f1-a | 25.0 | 60 | setup_mismatch |  |  |  |  |  |  | skip |
| ladder_fps26_20261121-174726 | EST-05fb8f1-a | 26.0 | 60 | setup_mismatch |  |  |  |  |  |  | skip |
| ladder_fps27_20261121-174732 | EST-05fb8f1-a | 27.0 | 60 | setup_mismatch |  |  |  |  |  |  | skip |
| ladder_fps28_20261121-174738 | EST-05fb8f1-a | 28.0 | 60 | stopped_by_signal | 0.5 | 0 |  | 0 | 0 |  | stop |

## Decisions (tail)

    2026-11-21 17:47:19 [EST-05fb8f1-a] night EST-05fb8f1-a start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 195 GB; Core pid 849; drop-in checked; timers-mask rc=0; smart temp 36 C
    2026-11-21 17:47:19 [EST-05fb8f1-a] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 60 fps (measured 60.0), 120 frames, 0.2 GB written and deleted)
    2026-11-21 17:47:19 [EST-05fb8f1-a] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261121-174719-baseline-EST-05fb8f1-a
    2026-11-21 17:47:19 [EST-05fb8f1-a] EST block P4 starts
    2026-11-21 17:47:19 [EST-05fb8f1-a] EST P4: ladder 3840x2160:16:hdr:27:none,3840x2160:12:sdr:40:lossless_jpeg,1920x1080:12:sdr::lossless_jpeg
    2026-11-21 17:47:26 [EST-05fb8f1-a] EST-05fb8f1-a P4-25-rung1 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1_ladder at 25 fps, 60 s: setup_mismatch (None s, dropped None, first drop None, gap None, boundary None)
    2026-11-21 17:47:32 [EST-05fb8f1-a] EST-05fb8f1-a P4-26-rung1 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1_ladder at 26 fps, 60 s: setup_mismatch (None s, dropped None, first drop None, gap None, boundary None)
    2026-11-21 17:47:38 [EST-05fb8f1-a] EST-05fb8f1-a P4-27-rung1 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1_ladder at 27 fps, 60 s: setup_mismatch (None s, dropped None, first drop None, gap None, boundary None)
    2026-11-21 17:47:57 [EST-05fb8f1-a] EST-05fb8f1-a P4-28-rung2 4kSDR12_lossless_log0_tdn0_lock0_trim1_web1_fpf5000_aud1_aids1_ladder at 28 fps, 60 s: stopped_by_signal (0.5 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-21 17:47:57 [EST-05fb8f1-a] EST outputs: /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate-table.csv, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/estimate.md, /home/pi/longtakes/nvme-20261110/est-05fb8f1-a/selftest.md
    2026-11-21 17:48:24 [EST-05fb8f1-a] RESTORE OK
