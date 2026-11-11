NIGHT OVER (all stages of the night done): safe to read; report report-ARMS.md
RESTORE OK
liveness: heartbeat 12 s old; runner pid 57789; night ARMS started 23:40
take: -
progress: 4 takes this night (44 in the campaign), 154 GB this night, 2172 GB in all of a 10000 GB budget
card: A936B442006AC2 ; free 154 GB; smart temp 56 C, written 63702472 units, critical_warning 0
voids 0, audio faults 0 this night

## Arms

- 4kHDR12: edge=30, top=25
- 4kHDR16: S4={'27': 'stop'}, best=27, edge=28, top=25; cells 27:carried 28:out
- 4kHDR16/lossless+log: preroll=ok: 5.0 s at 25 fps (measured 25.0), 124 frames, 1.2 GB written and deleted; cells 25:out 26:out
- 4kHDR16/lossless@25: ; cells 25:out
- 4kHDR16/unc+log@25: ; cells 25:carried
- 4kSDR12: best=30, edge=29, meter_capacity=30.0, top=30; cells 29:carried 30:carried
- 4kSDR12/lossless: best=30, preroll=ok: 5.0 s at 30 fps (measured 30.0), 149 frames, 0.9 GB written and deleted; cells 29:carried 30:carried

## Last 10 takes

| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pf5000_fps29_20261110-231517 | S2 | 29.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps29_20261110-231853 | S2 | 29.0 | 300 | pass_5min | 300.3 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps30_20261110-232430 | S2 | 30.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps30_20261110-232806 | S2 | 30.0 | 300 | pass_5min | 300.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps29_20261110-233343 | S2 | 29.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps30_20261110-233738 | S2 | 30.0 | 60 | setup_mismatch |  |  |  |  |  |  | stop |
| pf5000_fps25_20261110-234041 | ARMS | 25.0 | 180 | buffer_full | 13.0 | 0 |  | 0 | 0 |  | drop |
| pf5000_fps25_20261110-234129 | ARMS | 25.0 | 180 | buffer_full | 12.5 | 0 |  | 0 | 0 |  | drop |
| pf5000_fps25_20261110-234217 | ARMS | 25.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps25_20261110-234552 | ARMS | 25.0 | 300 | pass_5min | 300.3 | 0 |  | 0 | 0 |  | clean |

## Decisions (tail)

    2026-11-10 23:40:41 [ARMS] night ARMS start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 308 GB; Core pid 621; drop-in checked; timers-mask rc=0; smart temp 65 C
    2026-11-10 23:40:41 [ARMS] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 5.0 s at 30 fps (measured 30.0), 149 frames, 0.9 GB written and deleted)
    2026-11-10 23:40:41 [ARMS] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261110-234041-baseline-ARMS
    2026-11-10 23:41:29 [ARMS] ARMS walk 4kHDR16_lossless_log0_tdn0_lock0_trim1_web1_fpf5000 at 25 fps, 180 s: buffer_full (13.0 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 23:42:16 [ARMS] ARMS walk 4kHDR16_lossless_log0_tdn0_lock0_trim1_web1_fpf5000 at 25 fps, 180 s: buffer_full (12.5 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 23:42:16 [ARMS] ARMS 4kHDR16/lossless@25 at 25 fps: out
    2026-11-10 23:45:52 [ARMS] ARMS walk 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000 at 25 fps, 180 s: pass_3min (180.2 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 23:51:29 [ARMS] ARMS walk 4kHDR16_unc_log1_tdn0_lock0_trim1_web1_fpf5000 at 25 fps, 300 s: pass_5min (300.3 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 23:51:29 [ARMS] ARMS 4kHDR16/unc+log@25 at 25 fps: carried
    2026-11-10 23:51:29 [ARMS] stage ARMS done
    2026-11-10 23:51:51 [ARMS] RESTORE OK
