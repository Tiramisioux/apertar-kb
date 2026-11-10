# NVMe campaign report: S1, S2 (2026-11-10 03:38:29)

Labels: every number here is measured by the runner on this night unless it says derived. Card A936B442006AC2.

## Takes

| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Fix checks (whole campaign so far)

- **8ec2f1a, part folder made on the writer**: 0 part boundaries crossed in 0 split takes (0 frames); 0 drops within 64 frames after a boundary; 0 copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most None points above its take median (mean None, 0 boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops (night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).
- **e298d4a, frame index jump logged and counted**: 0 index jumps in Core's stats over the campaign; 0 takes had a numbering gap explained by them (0 frames, no picture lost); 0 takes had missing frames NOT explained by index jumps (each is a drop).

## Merges after the long takes (User, 2026-11-10)

| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |
|---|---|---|---|---|---|---|---|

## When does 4K need the split (flat vs split, same mode and fps)

Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core's safety stop or the tier length).

| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |
|---|---|---|---|---|---|---|---|---|---|

## Decisions

    2026-11-10 03:32:07 [S1,S2] night S1,S2 start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 1000 GB; Core pid 817; drop-in checked; timers-mask rc=0; smart temp 36 C
    2026-11-10 03:32:07 [S1,S2] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 30 fps (measured 30.0), 59 frames, 1.0 GB written and deleted)
    2026-11-10 03:33:24 [S1,S2] S1 direct60 write: 60.0 GB in 77 s = 780 MB/s (min 10-s window 627 MB/s), NVMe max 44 C; file deleted
    2026-11-10 03:33:31 [S1,S2] S1 matrix default: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:33:38 [S1,S2] S1 matrix --workers 1: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:33:45 [S1,S2] S1 matrix --prealloc: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:33:51 [S1,S2] S1 matrix --fsync none: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:33:57 [S1,S2] S1 matrix --direct: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:34:06 [S1,S2] S1 matrix --subdir 5000: folder removed (the drive keeps the written clusters until a trim: Core trims only after its own deletes)
    2026-11-10 03:35:07 [S1,S2] S1 state60 write: 47.9 GB in 62 s = 777 MB/s (min 10-s window 596 MB/s), NVMe max 47 C; file deleted
    2026-11-10 03:35:07 [S1,S2] stage S1 done
    2026-11-10 03:38:29 [S1,S2] RESTORE OK
