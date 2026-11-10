NIGHT OVER (a second void this night (audio_missing: no "audio capture" line in the take window)): safe to read; report report-S2.md
RESTORE OK
liveness: heartbeat 1 s old; runner pid 39588; night S2 started 03:42
take: -
progress: 8 takes this night (8 in the campaign), 619 GB this night, 619 GB in all of a 10000 GB budget
card: A936B442006AC2 ; free 379 GB; smart temp 65 C, written 60199731 units, critical_warning 0
voids 2, audio faults 0 this night; STOP: a second void this night (audio_missing: no "audio capture" line in the take window)

## Arms

- 4kHDR16: edge=28, top=30; cells 28:out

## Last 10 takes

| take | stage | fps | tier | outcome | s | dropped | first drop | gap | boundary | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pf5000_fps28_20261110-033855 | S2 | 28.0 | 60 | ab_clean | 60.0 | 0 |  | 0 | 0 |  | drop |
| pf5000_fps28_20261110-034030 | S2 | 28.0 | 180 | stopped_by_signal | 50.5 | 0 |  | 0 | 0 |  | stop |
| pf5000_fps28_20261110-034253 | S2 | 28.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps28_20261110-034628 | S2 | 28.0 | 300 | drop | 136.1 | 1 | 135.8 | 0 | 0 |  | drop |
| pf5000_fps28_20261110-034921 | S2 | 28.0 | 180 | drop | 153.2 | 1 | 152.8 | 0 | 0 |  | drop |
| pf5000_fps27_20261110-035230 | S2 | 27.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 |  | clean |
| pf5000_fps27_20261110-035606 | S2 | 27.0 | 300 | void | 300.3 | 0 |  | 0 | 0 |  | void |
| pf5000_fps27_20261110-040141 | S2 | 27.0 | 300 | void | 300.3 | 0 |  | 0 | 0 |  | void |

## Decisions (tail)

    2026-11-10 03:42:38 [S2] night S2 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 948 GB; Core pid 817; drop-in checked; timers-mask rc=0; smart temp 44 C
    2026-11-10 03:42:38 [S2] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 30 fps (measured 30.0), 59 frames, 1.0 GB written and deleted)
    2026-11-10 03:46:28 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 180 s: pass_3min (180.1 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 03:49:20 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 300 s: drop (136.1 s, dropped 1, first drop 135.8, gap 0, boundary 0)
    2026-11-10 03:52:30 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 180 s: drop (153.2 s, dropped 1, first drop 152.8, gap 0, boundary 0)
    2026-11-10 03:56:06 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 180 s: pass_3min (180.2 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 04:01:41 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 300 s: void (300.3 s, dropped 0, first drop , gap 0, boundary 0) void: audio_missing: no "audio capture" line in the take window
    2026-11-10 04:07:16 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 300 s: void (300.3 s, dropped 0, first drop , gap 0, boundary 0) void: audio_missing: no "audio capture" line in the take window
    2026-11-10 04:07:37 [S2] RESTORE OK
