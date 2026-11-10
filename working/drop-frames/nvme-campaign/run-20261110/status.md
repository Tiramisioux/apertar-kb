NIGHT OVER (stopped by SIGTERM): safe to read; report report-S2-S4-S5.md
RESTORE OK
liveness: heartbeat 46 s old; runner pid 7223; night S2,S4,S5 started 21:06
take: -
progress: 2 takes this night (27 in the campaign), 4 GB this night, 1328 GB in all of a 10000 GB budget
card: A936B442006AC2 ; free 162 GB; smart temp 34 C, written 61856466 units, critical_warning 0
voids 0, audio faults 0 this night

## Arms

- 4kHDR16: S4={'27': 'stop'}, best=27, edge=28, top=30; cells 27:carried 28:out
- 4kHDR16/lossless+log: preroll=ok: 5.0 s at 30 fps (measured 27.7), 136 frames, 1.4 GB written and deleted; cells 25:out 26:out

## Last 10 takes

| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pf5000_fps28_20261110-111943 | S2 | 28.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps30_20261110-112434 | S2 | 30.0 | 180 | drop | 2.0 | 2 | 1.7 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112502 | S2 | 25.0 | 180 | drop | 4.0 | 1 | 3.7 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112603 | S2 | 25.0 | 180 | drop | 5.0 | 2 | 4.8 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112643 | S2 | 25.0 | 180 | drop | 5.0 | 2 | 4.7 | 0 | 0 |  | drop |
| pf5000_fps28_20261110-112723 | S2 | 28.0 | 180 | drop | 159.7 | 4 | 159.2 | 0 | 0 |  | drop |
| pf5000_fps42_20261110-113219 | S2 | 42.0 | 60 | record_start_failed | 0.0 | 4 | 0.0 | 0 | 0 |  | stop |
| pf5000_fps27_20261110-113435 | S4 | 27.0 | 60 | record_start_failed | 0.0 | 4 | 0.0 | 0 | 0 |  | stop |
| pf5000_fps26_20261110-210700 | S2 | 26.0 | 180 | drop | 6.0 | 1 | 5.7 | 0 | 0 |  | drop |
| pf5000_fps26_20261110-210741 | S2 | 26.0 | 180 | drop | 10.0 | 4 | 9.8 | 0 | 0 |  | drop |

## Decisions (tail)

    2026-11-10 21:06:23 [S2,S4,S5] night S2,S4,S5 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 166 GB; Core pid 6958; drop-in checked; timers-mask rc=0; smart temp 33 C
    2026-11-10 21:06:23 [S2,S4,S5] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 30 fps (measured 30.0), 59 frames, 1.0 GB written and deleted)
    2026-11-10 21:06:23 [S2,S4,S5] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261110-210623-baseline-S2_S4_S5
    2026-11-10 21:06:39 [S2,S4,S5] 4kHDR16: walk ends, best carried fps 27 (cells 27:carried 28:out)
    2026-11-10 21:07:00 [S2,S4,S5] 4kHDR16/lossless+log: pre-roll ok: 5.0 s at 30 fps (measured 27.7), 136 frames, 1.4 GB written and deleted, above 25.0: walked
    2026-11-10 21:07:41 [S2,S4,S5] S2 walk 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000 at 26 fps, 180 s: drop (6.0 s, dropped 1, first drop 5.7, gap 0, boundary 0)
    2026-11-10 21:08:26 [S2,S4,S5] S2 walk 4kHDR16_lossless_log1_tdn0_lock0_trim1_web1_fpf5000 at 26 fps, 180 s: drop (10.0 s, dropped 4, first drop 9.8, gap 0, boundary 0)
    2026-11-10 21:08:26 [S2,S4,S5] 4kHDR16/lossless+log: walk ends, best carried fps None (cells 25:out 26:out)
    2026-11-10 21:09:07 [S2,S4,S5] RESTORE OK
