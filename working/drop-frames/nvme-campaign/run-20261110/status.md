NIGHT OVER (record_start_failed: The previous take's writers are still blocked on the removed medium (1). Try again in a moment.): safe to read; report report-S4-S5.md
RESTORE OK
liveness: heartbeat 51 s old; runner pid 51985; night S4,S5 started 11:34
take: -
progress: 1 takes this night (25 in the campaign), 0 GB this night, 1324 GB in all of a 10000 GB budget
card: A936B442006AC2 ; free 166 GB; smart temp 62 C, written 61846794 units, critical_warning 0
voids 0, audio faults 0 this night; STOP: record_start_failed: The previous take's writers are still blocked on the removed medium (1). Try again in a moment.

## Arms

- 4kHDR16: S4={'27': 'stop'}, best=27, edge=28, top=30; cells 27:carried 28:out
- 4kHDR16/lossless+log: preroll=ok: 5.0 s at 30 fps (measured 26.6), 125 frames, 1.5 GB written and deleted; cells 25:out

## Last 10 takes

| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pf5000_fps28_20261110-111023 | S2 | 28.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps28_20261110-111502 | S2 | 28.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps28_20261110-111943 | S2 | 28.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps30_20261110-112434 | S2 | 30.0 | 180 | drop | 2.0 | 2 | 1.7 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112502 | S2 | 25.0 | 180 | drop | 4.0 | 1 | 3.7 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112603 | S2 | 25.0 | 180 | drop | 5.0 | 2 | 4.8 | 0 | 0 |  | drop |
| pf5000_fps25_20261110-112643 | S2 | 25.0 | 180 | drop | 5.0 | 2 | 4.7 | 0 | 0 |  | drop |
| pf5000_fps28_20261110-112723 | S2 | 28.0 | 180 | drop | 159.7 | 4 | 159.2 | 0 | 0 |  | drop |
| pf5000_fps42_20261110-113219 | S2 | 42.0 | 60 | record_start_failed | 0.0 | 4 | 0.0 | 0 | 0 |  | stop |
| pf5000_fps27_20261110-113435 | S4 | 27.0 | 60 | record_start_failed | 0.0 | 4 | 0.0 | 0 | 0 |  | stop |

## Decisions (tail)

    2026-11-10 11:34:35 [S4,S5] night S4,S5 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 166 GB; Core pid 820; drop-in checked; timers-mask rc=0; smart temp 63 C
    2026-11-10 11:34:35 [S4,S5] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 5.0 s at 30 fps (measured 26.6), 125 frames, 1.5 GB written and deleted)
    2026-11-10 11:34:35 [S4,S5] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261110-113435-baseline-S4_S5
    2026-11-10 11:34:35 [S4,S5] GO-S4 found (unconditional): unconditional
    2026-11-10 11:35:01 [S4,S5] S4 warmup 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 60 s: record_start_failed (0.0 s, dropped 4, first drop 0.0, gap 0, boundary 0)
    2026-11-10 11:35:23 [S4,S5] RESTORE OK
