# NVMe campaign report: S2 (2026-11-10 04:07:37)

Labels: every number here is measured by the runner on this night unless it says derived. Card A936B442006AC2.

## Takes

| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00_fps28_20261110-033855 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | 60 | ab_clean | 60.0 | 0 |  | 0 | 0 | 135.4 | 2.6 | 46.85 | 27.9 |  | drop |
| 00_fps28_20261110-034030 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | 180 | stopped_by_signal | 50.5 | 0 |  | 0 | 0 | 133.4 | 2.7 | 48.85 | 23.5 |  | stop |
| 00_fps28_20261110-034253 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | 180 | pass_3min | 180.1 | 0 |  | 0 | 0 | 184.3 | 2.8 | 64.85 | 83.6 |  | clean |
| 00_fps28_20261110-034628 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | 300 | drop | 136.1 | 1 | 135.8 | 0 | 0 | 234.4 | 13.0 | 68.85 | 63.1 |  | drop |
| 00_fps28_20261110-034921 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 28.0 | 180 | drop | 153.2 | 1 | 152.8 | 0 | 0 | 233.8 | 11.8 | 70.85 | 71.1 |  | drop |
| 00_fps27_20261110-035230 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 27.0 | 180 | pass_3min | 180.2 | 0 |  | 0 | 0 | 205.5 | 3.1 | 72.85 | 80.7 |  | clean |
| 00_fps27_20261110-035606 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 27.0 | 300 | void | 300.3 | 0 |  | 0 | 0 | 192.4 | 3.3 | 73.85 | 134.5 |  | void |
| 00_fps27_20261110-040141 | S2 | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 | 27.0 | 300 | void | 300.3 | 0 |  | 0 | 0 | 211.0 | 3.5 | 75.85 | 134.5 |  | void |

## Fix checks (whole campaign so far)

- **8ec2f1a, part folder made on the writer**: 1 part boundaries crossed in 6 split takes (21089 frames); 0 drops within 64 frames after a boundary; 0 copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most 1.4 points above its take median (mean 0.47, 3 boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops (night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).
- **e298d4a, frame index jump logged and counted**: 2 index jumps in Core's stats over the campaign; 0 takes had a numbering gap explained by them (0 frames, no picture lost); 2 takes had missing frames NOT explained by index jumps (each is a drop).
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628: missing 1, index_jumps 1, frames 3778
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921: missing 1, index_jumps 1, frames 4252
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921 at frame 4253: skipped 1, dt 71425 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628 at frame 3779: skipped 1, dt 71423 us

## Merges after the long takes (User, 2026-11-10)

| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |
|---|---|---|---|---|---|---|---|

## When does 4K need the split (flat vs split, same mode and fps)

Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core's safety stop or the tier length).

| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |
|---|---|---|---|---|---|---|---|---|---|

## Decisions

    2026-11-10 03:42:38 [S2] night S2 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 948 GB; Core pid 817; drop-in checked; timers-mask rc=0; smart temp 44 C
    2026-11-10 03:42:38 [S2] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 30 fps (measured 30.0), 59 frames, 1.0 GB written and deleted)
    2026-11-10 03:46:28 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 180 s: pass_3min (180.1 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 03:49:20 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 300 s: drop (136.1 s, dropped 1, first drop 135.8, gap 0, boundary 0)
    2026-11-10 03:52:30 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 28 fps, 180 s: drop (153.2 s, dropped 1, first drop 152.8, gap 0, boundary 0)
    2026-11-10 03:56:06 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 180 s: pass_3min (180.2 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 04:01:41 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 300 s: void (300.3 s, dropped 0, first drop , gap 0, boundary 0) void: audio_missing: no "audio capture" line in the take window
    2026-11-10 04:07:16 [S2] S2 walk 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000 at 27 fps, 300 s: void (300.3 s, dropped 0, first drop , gap 0, boundary 0) void: audio_missing: no "audio capture" line in the take window
    2026-11-10 04:07:37 [S2] RESTORE OK
