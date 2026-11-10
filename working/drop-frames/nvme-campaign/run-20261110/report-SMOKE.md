# NVMe campaign report: SMOKE (2026-11-10 10:45:55)

Labels: every number here is measured by the runner on this night unless it says derived. Card A936B442006AC2.

## Takes

| take | stage | arm | fps | tier s | outcome | s | dropped | first drop s | numbering gap | boundary drops | Core CPU avg | buffer peak % | nvme max C | GB | merge s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00_fps28_20261110-104437 | SMOKE | 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf200 | 28.0 | 900 | pass_capped_20s | 20.0 | 0 |  | 0 | 0 | 124.0 | 2.2 | 36.85 | 9.3 | 0.1 | clean |

## Fix checks (whole campaign so far)

- **8ec2f1a, part folder made on the writer**: 3 part boundaries crossed in 7 split takes (21648 frames); 0 drops within 64 frames after a boundary; 0 copy-slot drops in all. The buffer around a boundary (1 s before to 3 s after) rose at most 1.4 points above its take median (mean 0.5, 5 boundaries). Expectation if the fix holds: 0 boundary drops, 0 copy-slot drops (night 2 on the old binary: 3 copy-slot drops at 1 of ~40 boundaries).
- **e298d4a, frame index jump logged and counted**: 2 index jumps in Core's stats over the campaign; 0 takes had a numbering gap explained by them (0 frames, no picture lost); 2 takes had missing frames NOT explained by index jumps (each is a drop).
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628: missing 1, index_jumps 1, frames 3778
  - 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921: missing 1, index_jumps 1, frames 4252
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034921 at frame 4253: skipped 1, dt 71425 us
  - jump in 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf5000_fps28_20261110-034628 at frame 3779: skipped 1, dt 71423 us

## Merges after the long takes (User, 2026-11-10)

| take | clip | frames | parts | merge s | ms per frame | first ETA error % | intact |
|---|---|---|---|---|---|---|---|
| 00_fps28_20261110-104437 | cDNG_26-11-10_10450114_C0001 | 559 | 3 | 0.1 | 0.179 | None | 1 |

Model (T7 night 2, derived): 0.1 ms + 0.32 us x files already in the main folder per frame; 45,001 frames in 342 s.

## When does 4K need the split (flat vs split, same mode and fps)

Directory walk share of the frame period, derived: s(t) = 5 x c x fps^2 x t (c in s per entry; flat folder); a split at N caps it at 5 x c x N x fps. The flat control runs past its first drop (to Core's safety stop or the tier length).

| mode | fps | variant | take | outcome | s | first drop s | c ns/entry (CPU slope) | Core CPU min 1 -> last | buffer % last 5 min |
|---|---|---|---|---|---|---|---|---|---|
| 4kHDR16 | 28.0 | split 200 | 00_fps28_20261110-104437 | pass_capped_20s | 20.0 |  |  | None -> 136.5 | 0.1 |

## Deletes (media route)

- cDNG_26-11-10_10450114_C0001: 559 frames, 0 parts, warm, budget 0 s, took 0.2 s

## Decisions

    2026-11-10 10:44:37 [SMOKE] night SMOKE start: card Corsair MP600 MINI A936B442006AC2 fw ERFM11.1, free 379 GB; Core pid 820; drop-in checked; timers-mask rc=0; smart temp 31 C
    2026-11-10 10:44:37 [SMOKE] fixed state: ladder False, merge False, frames_per_folder 5000, speed ramp False, pre-roll True (ok: 2.0 s at 30 fps (measured 30.0), 59 frames, 1.0 GB written and deleted)
    2026-11-10 10:44:37 [SMOKE] audio baseline: record_audio_enabled=True audio_input_device='hw:2,0' input_devices=['hw:2,0'] -> /home/pi/longtakes/nvme-20261110/audio-forensics/20261110-104437-baseline-SMOKE
    2026-11-10 10:45:33 [SMOKE] merge of cDNG_26-11-10_10450114_C0001: 559 frames, 3 parts, 0 s (0.18 ms per frame), first ETA error None %, intact; merge off again: True
    2026-11-10 10:45:33 [SMOKE] SMOKE smoke 4kHDR16_unc_log0_tdn0_lock0_trim1_web1_fpf200 at 28 fps, 20 s: pass_capped_20s (20.0 s, dropped 0, first drop , gap 0, boundary 0)
    2026-11-10 10:45:33 [SMOKE] SMOKE: pass_capped_20s, 559 frames, buffer peak 2.2 %, index_jumps 0, boundaries 2, merge 0.1 s ok=1
    2026-11-10 10:45:34 [SMOKE] deleted cDNG_26-11-10_10450114_C0001: 559 frames in 0.2 s (warm, budget 0 s)
    2026-11-10 10:45:34 [SMOKE] SMOKE: delete of its clip: ok
    2026-11-10 10:45:34 [SMOKE] stage SMOKE done
    2026-11-10 10:45:55 [SMOKE] RESTORE OK
